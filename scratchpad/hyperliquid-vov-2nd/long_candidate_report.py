"""Separate, period-labelled figures and conclusions for NB13 long replays."""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from long_candidate_backtest import ROOT, PERIOD, SHORT


def heading(title, description, period=PERIOD):
    display(Markdown(f"### {title} — {period}\n\n{description}"))


def table(frame):
    formats = {c: ("{:.2%}" if c in ["CAGR", "2026 CAGR", "Maximum drawdown", "Mean cash weight", "Best update", "Worst update", "Top positive profit share"] else "{:.2f}" if "Sharpe" in c else "${:,.0f}" if "(USD)" in c else "{:.1f}" if c == "Excess kurtosis" else "{}") for c in frame}
    style = frame.style.format(formats, na_rep="Unavailable").hide(axis="index")
    for c in ["CAGR", "Sharpe", "Maximum drawdown", "2026 CAGR", "2026 Sharpe"]:
        if c in frame:
            style = style.background_gradient(subset=[c], cmap="RdYlGn")
    display(style)


def figure(data, fig, name, title, description):
    heading(title, description)
    fig.tight_layout()
    path = data["artifact"] / f"{name}.png"
    fig.savefig(path, dpi=115, bbox_inches="tight")
    display(fig)
    plt.close(fig)
    data["figures"].append(str(path))


def shortlist(data, chosen, pool):
    heading("Frozen shortlist", "Select the union of the top five CAGR and top five Sharpe candidates on repaired 2026 data. Fill overlap to ten using the sum of both ranks. The named strategies retain their original rules. Two additional benchmarks are replayed separately.", SHORT)
    table(chosen[["Candidate", "Name", "Origin", "Positions", "CAGR", "Sharpe", "CAGR rank", "Sharpe rank", "Selection reason"]])
    if (data["artifact"] / "selection-audit.json").exists():
        audit = json.loads((data["artifact"] / "selection-audit.json").read_text())
        display(Markdown(f"The additional {audit['additional_NB04_worker_rows']} NB04 factorial/single-feature worker rows were also checked; including them leaves the same ten selected identities."))
    rows = []
    for row in chosen.to_dict("records"):
        if row["Kind"] == "score":
            cfg = data["score_configs"][row["Score name"]]
            from score_matrix import FEATURES

            terms = " + ".join(f"{w:.0%} × {p} {m}" for (p, m), w in zip(FEATURES, cfg["Weights"]) if w)
            clipping = "Legacy CAGR 100% / Sortino3 / Sharpe3" if cfg["Family"] == "Legacy 45d" else "Half legacy + half requested (CAGR50%, Sortino7, Sharpe3)"
            sizing = "Original 90-day inverse variance; source sequential redistribution"
        else:
            p = data["policy_configs"][row["Policy"]]
            terms = "48% CAGR360 + 32% Sortino45 + 10% CAGR180 + 10% Sortino30"
            clipping = "Legacy CAGR100% / Sortino3"
            sizing = f"{p['method']}, L={p['L']}, κ={p['kappa']}; simultaneous cap projection"
        rows.append(dict(Candidate=row["Candidate"], Ranking=terms, Clipping=clipping, Sizing=sizing, Positions=int(row["Positions"])))
    heading("Strategy rules", "Ranking score coefficients, clipping and sizing are separate. All candidates retain missing=True and source selection, entry rank N, exit rank N+2, 33% concentration and pool limits, 98% target allocation and a two-day cycle.")
    display(pd.DataFrame(rows).style.hide(axis="index"))
    heading("Available history and archive provenance", "Use every available positive NAV observation in the pinned repaired publication. The existing 1 March start includes the brief empty lead-in before the first observation. All indicators and permissions keep their original causal handling; missing historical observation clocks are not treated as invented receipts.")
    m = data["manifest"]
    display(pd.DataFrame([{"Item": "Calendar", "Value": PERIOD}, {"Item": "First actual positive NAV", "Value": m["observation_start"]}, {"Item": "Last actual positive NAV day", "Value": m["observation_end"]}, {"Item": "Last observation timestamp", "Value": str(data["daily"].timestamp.max())}, {"Item": "Initial cash", "Value": "$150,000 per strategy"}, {"Item": "Archive SHA256", "Value": m["identity"]["downloads"]["vault_prices"]["sha256"]}, {"Item": "Candidate inventory", "Value": f"{len(pool)} executable strategy rows across NB01–08 and NB12; NB09–11 are feature/snapshot studies"}]).style.hide(axis="index"))


def report(data, summary, runs, robust, weights, quarters):
    heading("Long-period key metrics", "Ten candidates selected using 2026 results, plus unchanged v11 and regularised90 controls. Every strategy starts with fresh $150,000 on 1 March 2023. These results include the same 2026 selection period and previously searched years; they are not a holdout.")
    ordered = summary.sort_values(["CAGR", "Sharpe"], ascending=False)
    table(ordered[["Candidate", "Name", "Positions", "CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)", "Mean cash weight", "Trades", "2026 CAGR", "2026 Sharpe"]])
    heading("2026 rule replication", "Each shortlisted strategy and benchmark is rerun on the original 2026 interval before long execution. Twenty-four CAGR/Sharpe comparisons must reproduce the saved results within 0.000002; no strategy is reselected after long results.", SHORT)
    parity = pd.read_csv(data["artifact"] / "replication.csv")
    display(parity.groupby("Metric").agg(Checks=("Candidate", "count"), Largest_absolute_difference=("Difference", lambda s: s.abs().max())).style.format({"Largest_absolute_difference": "{:.9f}"}))
    labels = summary.set_index("Candidate").Name
    annual = pd.DataFrame({cid: (1 + r["daily_returns"]).groupby(r["daily_returns"].index.year).prod() - 1 for cid, r in runs.items()}).T.reindex(summary.Candidate)
    annual.index.name = "Candidate"
    annual.columns = [str(y) + (" (partial)" if y in (2023, 2026) else "") for y in annual.columns]
    heading("Returns by calendar year", "Unannualised account returns compound the same recorded daily equity returns. 2023 starts on 1 March and 2026 ends at the last archive valuation. These are returns from carried portfolios, whereas the 2026 reference column above comes from independent fresh-start accounts.")
    display(annual.style.format("{:+.2%}").background_gradient(cmap="RdYlGn", axis=None))
    annual.to_csv(data["artifact"] / "annual-returns.csv")
    for kind, title in [("score", "Earlier score candidates"), ("allocation", "New allocation candidates")]:
        fig, ax = plt.subplots(figsize=(12, 5.5))
        ids = summary[summary.Kind.eq(kind) & summary.Candidate.str.startswith("C")].Candidate.tolist()
        for cid in ids:
            eq = runs[cid]["equity"]
            ax.plot(eq.index, eq / 150000, label=cid, lw=1.5)
        for cid, col in [("B01", "#111827"), ("B02", "#e11d48")]:
            eq = runs[cid]["equity"]
            ax.plot(eq.index, eq / 150000, label=cid + " benchmark", lw=1.8, color=col, ls="--")
        ax.set(title=f"{title}: wealth from $1\n{PERIOD}", xlabel="Date (UTC)", ylabel="Portfolio wealth / initial equity")
        ax.grid(alpha=0.2)
        ax.legend(ncol=3, fontsize=8)
        figure(data, fig, kind + "-equity", title + " equity curves", "Each line starts at the same capital and calendar date. C labels map to the shortlist. B01 is source v11; B02 is focal regularised90. The new methods keep focal ranking but replace sizing and allocation.")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for _, r in summary.iterrows():
        colour = "#2563eb" if r.Kind == "score" else "#ea580c" if r.Candidate.startswith("C") else "#111827"
        ax.scatter(r.CAGR * 100, r.Sharpe, c=colour, s=55)
        offsets = {"C07": (8, 18), "C10": (15, -22), "C08": (-35, -18), "B02": (-42, 12)}
        ax.annotate(r.Candidate, (r.CAGR * 100, r.Sharpe), xytext=offsets.get(r.Candidate, (5, 4)), textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color=colour, lw=0.6) if r.Candidate in offsets else None)
    ax.set(title=f"CAGR and Sharpe; blue earlier, orange new, black benchmarks\n{PERIOD}", xlabel="CAGR (%)", ylabel="Sharpe (365-day annualisation)")
    ax.grid(alpha=0.2)
    figure(data, fig, "cagr-sharpe", "Return and risk-adjusted return", "Compare long-period leaders with the 2026 ordering. Marker colours identify earlier scoring rules, newer sizing rules and benchmarks. Close neighbours are similar realised performances, not independent confirmations.")
    z = quarters.T.reindex(summary.Candidate).to_numpy() * 100
    fig, ax = plt.subplots(figsize=(15, 6))
    limit = max(np.nanmax(np.abs(z)), 1)
    im = ax.imshow(z, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(len(quarters)), [str(x) + ("*" if x == quarters.index[-1] else "") for x in quarters.index], rotation=45, ha="right")
    ax.set_yticks(range(len(summary)), summary.Candidate)
    for i in range(len(summary)):
        for j in range(len(quarters)):
            ax.text(j, i, f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=8, color="white" if abs(z[i, j]) > limit * 0.65 else "#111827")
    ax.set_title(f"Compounded quarterly profit; *partial final quarter\n{PERIOD}")
    fig.colorbar(im, ax=ax, label="Portfolio return (%)")
    figure(data, fig, "quarterly-profit", "Quarterly profit heatmap", "Each cell compounds daily-resampled engine returns for that quarter. Early cash-only quarters are retained. The final quarter contains only the available October days; the first quarter is also partial from the March start.")
    named_union = sorted(set().union(*(set(w.drop(columns=runs[cid]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol).mean().nlargest(8).index) for cid, w in weights.items())))
    palette = {name: plt.get_cmap("tab20")(i % 20) for i, name in enumerate(named_union)}
    palette.update({"Cash": "#e5e7eb", "Other vaults": "#94a3b8"})
    for cid, row in summary.set_index("Candidate").iterrows():
        w = weights[cid]
        eq = runs[cid]["equity"].resample("1D").last().ffill()
        reserve = runs[cid]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        names = w.drop(columns=reserve).mean().nlargest(8).index.tolist()
        others = w.drop(columns=names + [reserve]).sum(axis=1)
        shown = w[names].copy()
        shown["Other vaults"] = others
        shown["Cash"] = w[reserve]
        shown = shown.div(eq, axis=0)
        assert np.allclose(shown.sum(axis=1), 1.0, atol=1e-7)
        fig, ax = plt.subplots(figsize=(12, 5))
        shown.plot.area(ax=ax, linewidth=0, color=[palette[n] for n in shown.columns])
        ax.set(title=f"{cid}: absolute account weights including cash\n{PERIOD}", xlabel="Date (UTC)", ylabel="Fraction of total equity", ylim=(0, 1))
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=7)
        figure(data, fig, cid + "-weights", cid + " absolute asset weights", f"{row.Name}. The eight largest average vault exposures are named; all remaining vaults are grouped. Colours are consistent across strategies; grey indicates cash and Other. Weights sum to the full account. Closed positions are set to zero before causal forward filling.")
    contrasts = []
    ref = summary.set_index("Candidate")
    for cid in ["C07", "C08", "C10"]:
        for baseline in ["C03", "B02"]:
            a, b = ref.loc[cid], ref.loc[baseline]
            contrasts.append({"Candidate": cid, "Reference": baseline, "CAGR difference (pp)": 100 * (a.CAGR - b.CAGR), "Sharpe difference": a.Sharpe - b.Sharpe, "Drawdown difference (pp)": 100 * (a["Maximum drawdown"] - b["Maximum drawdown"]), "Final equity difference (USD)": a["Final equity (USD)"] - b["Final equity (USD)"]})
    heading("Allocation contrasts", "C03 is the original four-input score with source sizing/allocation; B02 uses the same score with regularised90 and simultaneous allocation. Comparing newer estimators with B02 isolates a much smaller change than comparing the whole allocation family with C03.")
    contrasts = pd.DataFrame(contrasts)
    contrasts.to_csv(data["artifact"] / "allocation-contrasts.csv", index=False)
    display(contrasts.style.format({c: "{:+.3f}" for c in contrasts if c not in ["Candidate", "Reference"]}).hide(axis="index"))
    heading("Profit concentration and equity tails", "Largest positive vault contribution, maximum/minimum recorded return and kurtosis quantify concentration. Equity is valued on the source two-day clock, so updates shown on a daily grid can cover multiple days. Zeroing the best update is an influence check on the fixed ledger, not a tradable exclusion backtest.")
    table(robust[["Candidate", "Best update", "Worst update", "Best update date", "Excess kurtosis", "Top vault", "Top positive profit share", "Sharpe with best update zeroed", "PnL residual (USD)"]])
    attrs = pd.read_csv(data["artifact"] / "vault-attribution.csv")
    fig, ax = plt.subplots(figsize=(11, 5))
    top = attrs.groupby("Vault").PnL.sum().nlargest(8).index
    pivot = attrs.pivot(index="Candidate", columns="Vault", values="PnL").reindex(summary.Candidate).fillna(0)
    cols = list(top)
    pivot = pivot.reindex(columns=cols, fill_value=0)
    pivot.plot.bar(ax=ax, stacked=True, colormap="tab20")
    ax.set(title=f"Leading vault PnL by candidate (negative contributions retained)\n{PERIOD}", xlabel="Candidate / benchmark", ylabel="Cash-flow PnL (USD)")
    ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=8)
    figure(data, fig, "vault-contributions", "Leading vault profit contributions", "The eight vaults with greatest aggregate profit across these runs are shown. Trades and valuations are reconciled to equity; profit is aggregated across re-entries. Only these named contributions are plotted, so bars do not equal total account profit.")
    (data["artifact"] / "figure-manifest.json").write_text(json.dumps(data["figures"], indent=2))
    from long_candidate_audit import audit

    actual_mark_audit, tail_influence = audit(data, summary, runs, quarters)
    return findings(data, summary, robust, quarters)


def findings(data, summary, robust, quarters):
    """Write the long-history verdict and update only this experiment's heading."""
    candidates = summary[summary.Candidate.str.startswith("C")]
    c = candidates.nlargest(1, "CAGR").iloc[0]
    s = candidates.nlargest(1, "Sharpe").iloc[0]
    base = summary.set_index("Candidate").loc["B01"]
    regular = summary.set_index("Candidate").loc["B02"]
    tail = pd.read_csv(data["artifact"] / "tail-influence.csv")
    actual = pd.read_csv(data["artifact"] / "actual-mark-tail-audit.csv")
    lines = [
        "# Experiment 13 — long-period candidate replay",
        f"\nPeriod: **{PERIOD}**. Ten frozen 2026 leaders and two benchmarks, each starting with $150,000.",
        "\n## What was examined",
        "\nWhether the ten best repaired-data 2026 CAGR/Sharpe candidates retain strong returns over every available vault backtesting observation. Original scoring, sizing, N, missing behaviour, source selection and allocation methods are preserved.",
        "\n## Hypothesis and method",
        "\nHypothesis: 2026 leaders retain gains against v11 and regularised90 across full history. Select the union of top five by each metric, fill to ten by their equal-weight rank sum. Freeze before long replay. All 24 2026 metric parity checks pass. Include source v11 and focal regularised90 as additional benchmarks.",
        "\n## Results",
        summary[["Candidate", "Name", "CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)", "Mean cash weight", "2026 CAGR", "2026 Sharpe"]].to_markdown(index=False, floatfmt=".6f"),
        "\n## Calendar-year returns",
        pd.read_csv(data["artifact"] / "annual-returns.csv").to_markdown(index=False, floatfmt=".6f"),
        "\n## Key new insights",
        f'\nHighest long CAGR: **{c.Candidate} {c.Name}**, {c.CAGR:.2%}, Sharpe {c.Sharpe:.2f}, drawdown {c["Maximum drawdown"]:.2%}. Highest long Sharpe: **{s.Candidate} {s.Name}**, {s.Sharpe:.2f}, CAGR {s.CAGR:.2%}.',
        f"\nSource v11: {base.CAGR:.2%} CAGR / {base.Sharpe:.2f} Sharpe. Regularised90: {regular.CAGR:.2%} / {regular.Sharpe:.2f}. {int(((candidates.CAGR>base.CAGR)&(candidates.Sharpe>base.Sharpe)).sum())}/10 exceed source v11 on both metrics; {int(((candidates.CAGR>regular.CAGR)&(candidates.Sharpe>regular.Sharpe)).sum())}/10 exceed regularised90 on both.",
        "\n## Robustness of results",
        f'\nThe first actual positive NAV is {data["manifest"]["observation_start"]}, last is {data["manifest"]["observation_end"]}. The 1 March calendar includes the initial empty lead-in. All position PnL reconciles within $1; absolute weights sum to whole account equity. NAV-only forward fill preserves missing leading marks and actual-observation masks. Permission and capacity fields are handled by the unchanged source engine.',
        robust.to_markdown(index=False, floatfmt=".6f"),
        "\nThe largest recorded updates are audited against their vault NAV marks, current curator and BTC/ETH price context. Daily-resampled returns include two-day updates. The concentration table and quarterly heatmap should be considered alongside CAGR. No single removed-day or removed-vault diagnostic represents an executable rebalanced portfolio.",
        "\n## Observation-interval audit",
        actual[actual.Candidate.isin(["C03", "C07", "B01"])].to_markdown(index=False, floatfmt=".6f"),
        "\nThe new allocation family recognises a 15.16% account update on 13 November 2024. This catches weekly marks, including Road to 10 Million (+30.26% NAV), FFLGN (+41.69%) and Delta_01 (+7.26%) since 6 November. BTC/ETH context is measured over those same real mark dates. Late intraday marks can fall after the daily engine label: this preserves the inherited daily-close convention, not a timestamp-faithful execution validation.",
        "\n## Tail influence",
        tail.to_markdown(index=False, floatfmt=".6f"),
        "\n## Allocation contrasts",
        pd.read_csv(data["artifact"] / "allocation-contrasts.csv").to_markdown(index=False, floatfmt=".6f"),
        "\nMost of the long-period allocation-family gain is already present in the regularised90 benchmark: compare C07 directly with B02 before attributing it to the gap estimator. New allocations have worse drawdown and lower Sharpe than the original four-input source candidate, despite greater CAGR. Q4 2024 and sparse valuation timing materially affect the result.",
        "\n## Hypothesis verdict and next leads",
        "\nThe descriptive hypothesis is supported against v11, but there is no consistent allocation-family winner across years. C07 returns 45.86% in 2024 versus C03’s 24.41%; it then trails C03 in 2025 (25.21% versus 29.15%) and carried 2026 (29.41% versus 32.67%). The highest fresh-2026 Sharpe candidate, C04, is not the full-history Sharpe leader. C03 retains the strongest long Sharpe; C07 has the highest CAGR with greater drawdown. The isolated gap-estimator improvement over regularised90 is only about 0.37 percentage points CAGR and 0.02 Sharpe.\n\nRelative performance is descriptive: 2026 selection overlaps the full period and earlier years were already searched. Earlier and new candidates can be compared with the same archive, but this replay does not provide independent confirmation. Early low deployment and changing vault availability depress full-calendar CAGR. Use the quarter/cash plots to distinguish these effects from poor selected-vault performance. Next, freeze a candidate and compare source versus simultaneous allocation on matched selection, then observe genuinely later data.",
    ]
    text = "\n".join(lines) + "\n"
    path = ROOT / "13-long-candidates-findings.md"
    path.write_text(text)
    summary_path = ROOT / "summary.md"
    prior = summary_path.read_text()
    marker = "\n# Experiment 13 — long-period candidate replay"
    prior = prior.split(marker)[0]
    summary_path.write_text(prior.rstrip() + "\n\n" + text)
    import nbformat

    notebook = ROOT / "13-backtest-leading-candidates.ipynb"
    nb = nbformat.read(notebook, as_version=4)
    extra = f"""\n## Key new insights\n\nThe highest long-period CAGR is {c.Candidate}: **{c.CAGR:.2%} CAGR, {c.Sharpe:.2f} Sharpe**, with {c['Maximum drawdown']:.2%} maximum drawdown. Highest long-period Sharpe is {s.Candidate}: **{s.Sharpe:.2f}**, with {s.CAGR:.2%} CAGR. Source v11 returns {base.CAGR:.2%} / {base.Sharpe:.2f}; focal regularised90 returns {regular.CAGR:.2%} / {regular.Sharpe:.2f}.\n\n## Summary of results — {PERIOD}\n\nAll ten shortlisted candidates and both benchmarks completed. All 24 comparisons reproduce their 2026 CAGR and Sharpe. Full-history key metrics, quarterly returns, equity curves, absolute weights and vault/tail attribution appear below.\n\n## Robustness of results\n\nAll position PnL reconciles within $1 and absolute weights sum to equity. Tail updates are checked against actual NAV marks, current curator and BTC/ETH. Daily-resampled engine returns contain two-day valuation changes. The long interval contains the 2026 selection period and previously searched years; this is a historical robustness comparison, not a holdout. Current inventory/guard history and archive publication clocks remain limitations.\n"""
    # The executing kernel's in-memory notebook is saved by its runner; return header for final refresh.
    extra += "\nThe newer allocation family benefits from a 15.16% weekly-mark catch-up update in November 2024; Q4 2024 gains are about 44% versus 16% for the source four-input candidate. Its higher CAGR comes with lower Sharpe and greater drawdown. Most family-level uplift is already present in regularised90; gap sizing adds only a small increment. Actual intraday receipts can be later than their engine daily labels, so executable timing remains unvalidated.\n"
    extra += "\nThe new sizing family wins mainly in 2024 and trails C03 in both 2025 and carried 2026. C07’s incremental improvement over B02 is only about 0.37 percentage points CAGR and 0.02 Sharpe. All ten candidates exceed v11 CAGR and Sharpe over this interval; two exceed the regularised90 benchmark on both.\n"
    data["final_header"] = nb.cells[0].source.split("\n## Key new insights")[0] + extra
    return path
