"""Refresh experiment 04's default 2026 report from completed replay artefacts."""

from pathlib import Path
import argparse
import json

import nbformat
import numpy as np
import pandas as pd


def markdown_table(frame):
    """Render a small Markdown table without requiring the tabulate dependency."""

    def cell(value):
        return str(value).replace("|", "\\|").replace("$", "\\$").replace("\n", " ")

    rows = ["| " + " | ".join(map(cell, frame.columns)) + " |", "| " + " | ".join(["---"] * len(frame.columns)) + " |"]
    rows.extend("| " + " | ".join(map(cell, row)) + " |" for row in frame.itertuples(index=False, name=None))
    return "\n".join(rows)


def distinct_paths(detailed, matrices):
    """Consolidate configurations whose score, sizing and execution rules match."""
    periods = ["1m", "45d compatibility", "46d", "2m", "3m", "4m", "6m", "9m", "1y", "2y"]
    metrics = ["CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar"]
    features = [(p, m) for p in periods for m in metrics]

    def anchor(days):
        w = np.zeros(len(features))
        w[features.index(("1y", "CAGR"))] = 0.6
        w[features.index((days, "Sortino"))] = 0.4
        return w

    controls = {"Original v11": anchor("45d compatibility"), "Exact 360/45 compatibility": anchor("45d compatibility"), "Near-v6 360/46 legacy": anchor("46d")}
    priority = {name: i for i, name in enumerate(["Original v11", "Near-v6 360/46 legacy", "CAGR matrix", "50/50 blend", "60/40 blend", "Dense equal matrix"])}
    frame = detailed.assign(_priority=detailed.Family.map(priority).fillna(99), _mode=detailed.Allocator.ne("parent")).sort_values(["_mode", "_priority"])
    seen = set()
    rows = []
    for _, r in frame.iterrows():
        w = controls.get(r.Family)
        if w is None:
            w = matrices[r.Family]["Weights"]
        profile = r.Profile
        components = matrices.get(r.Family, {}).get("Components")
        if components and len({c["profile"] for c in components}) == 1:
            profile = components[0]["profile"]
        key = (tuple(np.asarray(w).round(10)), profile, int(r.Positions), r.Sizing, bool(r.Missing), r.Allocator)
        if key not in seen:
            seen.add(key)
            rows.append(r.drop(["_priority", "_mode"]))
    return pd.DataFrame(rows).reset_index(drop=True)


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--artefacts", type=Path, default=folder / "_artifacts-matrix-long-v2")
    parser.add_argument("--benchmark-note", default=None)
    args = parser.parse_args()
    artefacts = args.artefacts.resolve()
    path = folder / "04-opt-score-matrix.ipynb"
    notebook = nbformat.read(path, as_version=4)
    code = [c for c in notebook.cells if c.cell_type == "code"]
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type == "error" for c in code for o in c.outputs)
    manifest = json.loads((artefacts / "chart-2026-manifest.json").read_text())
    start, end = [s[:10] for s in manifest["chart_period"]]
    period = f"{start} → {end} (end exclusive, UTC)"
    detailed = pd.read_csv(artefacts / "chart-2026-detailed-results.csv")
    factorial = pd.read_csv(artefacts / "chart-2026-factorial.csv")
    matrices = json.loads((artefacts / "frozen-matrices.json").read_text())
    report = distinct_paths(detailed, matrices)
    robustness = pd.read_csv(artefacts / "chart-2026-robustness.csv")
    information = pd.read_csv(artefacts / "chart-2026-funded-information.csv")
    anchors = pd.read_csv(artefacts / "chart-2026-anchors.csv")
    clipping = pd.read_csv(artefacts / "chart-2026-calmar-clipping.csv")
    compression = pd.read_csv(artefacts / "chart-2026-compression.csv")
    coverage = pd.read_csv(artefacts / "chart-2026-feature-coverage.csv")
    recipes = manifest.get("score_blend_recipes", {})

    def profile_name(profile):
        components = recipes.get(profile)
        if components and len({c["profile"] for c in components}) == 1:
            return components[0]["profile"]
        return " + ".join(f'{c["mass"]:.0%} {c["profile"]}' for c in components) if components else profile

    pct = lambda v: f"{v:.2%}"
    source = detailed[detailed.Family == "Original v11"].iloc[0]
    near = detailed[detailed.Family == "Near-v6 360/46 legacy"].iloc[0]
    best = factorial.sort_values("CAGR", ascending=False).iloc[0]
    improves = factorial[(factorial.CAGR > source.CAGR) & (factorial.Sharpe > source.Sharpe) & (factorial["Maximum drawdown"] >= source["Maximum drawdown"])]
    matches = distinct_paths(improves, matrices) if len(improves) else improves
    insights = [
        f'- **Default period:** every displayed performance result is a fresh {period} replay with ${manifest["initial_cash"]:,.0f} and no inherited positions.',
        f'- **Original v11:** {pct(source.CAGR)} CAGR / {source.Sharpe:.2f} Sharpe / {pct(source["Maximum drawdown"])} max drawdown. Exact 360/45 compatibility reproduces its full equity path and all {int(source.Trades)} trades.',
        f'- **Near-v6 360/46:** {pct(near.CAGR)} CAGR / {near.Sharpe:.2f} Sharpe / {pct(near["Maximum drawdown"])} max drawdown. Its score window differs from the exact control by one day.',
        f'- **Highest observed grid CAGR:** {pct(best.CAGR)} for {best.Family}, {int(best.Positions)} positions, {best.Sizing}, missing={bool(best.Missing)}; Sharpe {best.Sharpe:.2f}, drawdown {pct(best["Maximum drawdown"])}. This grid maximum does not change the frozen strategy settings.',
        f"- **Joint improvements:** {len(matches)} distinct qualifying {'configuration' if len(matches)==1 else 'configurations'} with higher CAGR, higher Sharpe and no worse drawdown than original v11 in 2026. The fitting period overlaps this replay, so these are in-sample observations.",
    ]
    if args.benchmark_note:
        insights.append("- **Repaired-input benchmark:** " + args.benchmark_note)
    correlation_path = artefacts / "chart-2026-feature-correlations.csv"
    if correlation_path.exists():
        correlations = pd.read_csv(correlation_path)
        matched = correlations[(correlations.Representation == "Requested clips") & (correlations["Row metric"] == "CAGR") & (correlations["Column metric"] == "Sharpe") & (correlations["Row lookback"] == correlations["Column lookback"])]
        insights.append(f'- **Feature redundancy:** same-lookback CAGR and Sharpe scores have Spearman correlations of {matched["Spearman rho"].min():.2f}–{matched["Spearman rho"].max():.2f} under requested clipping in 2026. The heatmaps compare raw metrics, clipping and lookbacks with pair counts; these are pooled feature correlations, not evidence of predictive performance.')
    sections = []

    def section(title, description, frame):
        sections.append(f"### {title} — {period}\n\n{description}\n\n{markdown_table(frame)}")

    feature_periods = ["1m", "45d compatibility", "46d", "2m", "3m", "4m", "6m", "9m", "1y", "2y"]
    feature_metrics = ["CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar"]
    features = [(p, m) for p in feature_periods for m in feature_metrics]
    weights = []
    for family, definition in matrices.items():
        active = [(features[i], v) for i, v in enumerate(definition["Weights"]) if v > 0]
        terms = "All 45 searchable cells equally weighted" if family == "Dense equal matrix" else "; ".join(f"{p} {m}: {v:.0%}" for (p, m), v in sorted(active, key=lambda item: -item[1]))
        weights.append({"Family": family, "Clips": profile_name(definition["Profile"]), "Active cells": len(active), "Period / metric weights": terms})
    section("Frozen matrices used in the replay", "Input coefficients were selected on full history and are held fixed for 2026. Identical coefficients with different clipping recipes can produce different scores; these rows are parameters, not performance.", pd.DataFrame(weights))
    view = report[["Family", "Positions", "Sizing", "Missing", "Profile", "Allocator", "Final equity (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Mean cash weight", "Trades"]].copy()
    view["Profile"] = view.Profile.map(profile_name)
    view["Final equity (USD)"] = view["Final equity (USD)"].map(lambda v: f"${v:,.0f}")
    for col in ["CAGR", "Maximum drawdown", "Mean cash weight"]:
        view[col] = view[col].map(pct)
    for col in ["Sharpe", "Sortino"]:
        view[col] = view[col].map(lambda v: f"{v:.2f}")
    section("Strategy performance side by side", "Compare distinct fresh 2026 equity/trade paths using the long-fitted strategy settings. Equivalent named aliases appear once. Drawdown is signed: values nearer zero are better.", view.rename(columns={"Maximum drawdown": "Max DD", "Profile": "Clips"}))
    av = anchors[["Profile", "Sizing", "Missing", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight"]].copy()
    for col in ["CAGR", "Maximum drawdown", "Mean cash weight"]:
        av[col] = av[col].map(pct)
    av["Sharpe"] = av.Sharpe.map(lambda v: f"{v:.2f}")
    section("Explicit 60/40 anchor options", "Hold six positions and ranking at 60% 360-day CAGR plus 40% 46-day Sortino. Compare only clipping profiles, sizing and missing flags in the short replay.", av.rename(columns={"Profile": "Clips", "Maximum drawdown": "Max DD"}))
    cv = coverage[coverage.Period != "45d compatibility"].groupby("Period", sort=False).agg(Coverage=("Coverage", "first"), **{"Undefined ratio within complete windows": ("Undefined raw fraction when complete", "max"), "Flat complete vault-days": ("Flat full windows", "first")}).reset_index()
    for col in ["Coverage", "Undefined ratio within complete windows"]:
        cv[col] = cv[col].map(pct)
    section("Rolling metric availability", "Coverage counts complete positive-price windows across all vaults × replay dates, including dates before a vault has enough history. Undefined ratios use only complete windows as their denominator; flat windows are vault-day counts. Lookback labels are indicator windows, not reporting periods.", cv)
    run_names = report.set_index("Run").apply(lambda r: f"{r.Family} / {r.Allocator}", axis=1).to_dict()
    rv = robustness[robustness.Run.isin(report.Run)][["Run", "Leading vault", "Leading vault profit (USD)", "Leading vault share of positive vault profits", "Best day", "Best day return", "Sharpe with best day set to zero", "Sharpe without leader PnL (fixed ledger)"]].copy()
    rv["Run"] = rv.Run.map(run_names)
    rv["Leading vault profit (USD)"] = rv["Leading vault profit (USD)"].map(lambda v: f"${v:,.0f}")
    for col in ["Leading vault share of positive vault profits", "Best day return"]:
        rv[col] = rv[col].map(pct)
    for col in ["Sharpe with best day set to zero", "Sharpe without leader PnL (fixed ledger)"]:
        rv[col] = rv[col].map(lambda v: f"{v:.2f}")
    section("Profit concentration and return sensitivities", "Identify the leading vault and strongest booked day in each 2026 path. Removing their PnL retains the original trades and is a sensitivity, not a new executable backtest.", rv)
    iv = information[information.Run.isin(report.Run)].copy()
    iv["Run"] = iv.Run.map(run_names)
    for col in iv:
        if "/ target dollars" in col:
            iv[col] = iv[col].map(pct)
    section("Information available when funding positions", "Fractions weight target dollars across 2026 decisions, not realised time-weighted exposure. Unscored funding can occur under missing=True. Original v11 is absent because it has no matrix allocation ledger.", iv.rename(columns={"Unscored target dollars / target dollars": "Unscored funding", "Missing 1y target dollars / target dollars": "Missing 360d history", "Missing 2y target dollars / target dollars": "Missing 2y history", "Flat 1m target dollars / target dollars": "Flat 1m marks"}))
    comp = compression[["Active cells", "CAGR", "Sharpe", "Maximum drawdown", "Within 2026 tolerance"]].copy()
    for col in ["CAGR", "Maximum drawdown"]:
        comp[col] = comp[col].map(pct)
    comp["Sharpe"] = comp.Sharpe.map(lambda v: f"{v:.2f}")
    section("Compression candidates", "Compare completed short-period compression replays at six equal-weight positions and missing=False. The diagnostic tolerance is within one percentage point CAGR and 0.10 Sharpe of the full blend; the frozen compression choice is not reselected.", comp.rename(columns={"Maximum drawdown": "Max DD"}))
    clip = clipping[["Family", "Calmar cap", "CAGR", "Sharpe", "Maximum drawdown"]].copy()
    for col in ["CAGR", "Maximum drawdown"]:
        clip[col] = clip[col].map(pct)
    clip["Sharpe"] = clip.Sharpe.map(lambda v: f"{v:.2f}")
    section("Calmar clipping sensitivity", "Compare caps 3/5/10 using six positions and the frozen sizing, missing flag and score recipe. These matrices have no active Calmar term, so changing the cap cannot alter their score or trade path.", clip.rename(columns={"Maximum drawdown": "Max DD"}))
    residual = robustness["Max attribution residual (USD)"].max()
    findings = "## Key new insights\n\n" + "\n".join(insights) + "\n\n## Summary of results\n\n" + "\n\n".join(sections)
    findings += f'\n\n## Robustness and interpretation\n\nAll {len(code)} code cells completed. The short-period manifest records {len(manifest["evaluations"])} configuration evaluations. Position PnL reconciles to equity minus starting capital, with a largest residual of {residual:.2e} USD. Source scoring, selection and execution rules are unchanged. Full-history fitting and reference artefacts remain available separately.\n\nThe long fitting window includes 2026: this is exploratory in-sample analysis, not independent validation. Frozen families and detailed settings are not reselected using the short-period rankings. Missing history, flat NAV marks, current-universe assumptions and incomplete historical deposit-state data remain limitations.\n'
    findings = findings.replace("$", "\\$")
    # Avoid double escaping amounts already escaped by the Markdown table renderer.
    findings = findings.replace("\\\\$", "\\$")
    notebook.cells[0].source = notebook.cells[0].source.split("## Key new insights", 1)[0] + findings
    nbformat.write(notebook, path)
    (folder / "04-score-matrix-analysis.md").write_text(f"# Experiment 04 — short-period report\n\n[Executed notebook](04-opt-score-matrix.ipynb). Default period: {period}. Coefficients and detailed settings remain frozen from the full-history fit.\n\n" + findings)
    print(f"Refreshed {len(sections)} Markdown tables for {period}; {len(report)} distinct paths.")


if __name__ == "__main__":
    main()
