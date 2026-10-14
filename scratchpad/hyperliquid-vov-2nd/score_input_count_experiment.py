"""Controlled additions of a third and fourth vault-ranking input."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from tqdm_loggable.auto import tqdm

from precompute_repaired_singletons import create_evaluator
from repaired_data_replay import INPUT_DIR, RUN_ROOT, RESEARCH_DIR
from score_matrix import FEATURES, SEARCH_FEATURES
from score_matrix_blends import register_score_blend
from score_matrix_analysis import markdown_table

ARTIFACT_DIR = RUN_ROOT / "06"
PERIODS = {"Long": (datetime.datetime(2023, 3, 1), datetime.datetime(2026, 10, 5)), "2026": (datetime.datetime(2026, 1, 1), datetime.datetime(2026, 10, 5))}
SHORT_PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
LONG_PERIOD = "2023-03-01 → 2026-10-05 (end exclusive, UTC)"
NOTEBOOK = RESEARCH_DIR / "06-opt-score-3-4-inputs.ipynb"


class SearchParameters:
    """Predeclared support grid; added-input mass is held fixed across cardinalities."""

    #: Number of supports per input count and clipping family.
    iterations = 18
    #: Total coefficient mass assigned to additional inputs.
    added_mass = 0.20


EXTRAS = [("1m", "CAGR"), ("2m", "CAGR"), ("3m", "CAGR"), ("6m", "CAGR"), ("9m", "CAGR"), ("2y", "CAGR"), ("1m", "Sharpe"), ("3m", "Sharpe"), ("6m", "Sharpe"), ("1y", "Sharpe"), ("1m", "Sortino"), ("3m", "Sortino"), ("6m", "Sortino"), ("1y", "Sortino"), ("3m", "Max drawdown"), ("6m", "Max drawdown"), ("3m", "Calmar"), ("6m", "Calmar")]


def matrix(cells):
    """Build a non-negative coefficient vector with a unit sum."""
    weights = np.zeros(len(FEATURES))
    for cell, weight in cells:
        weights[FEATURES.index(cell)] += weight
    assert np.isclose(weights.sum(), 1.0) and (weights >= 0).all()
    return weights


def recipe(panel, weights, family):
    """Preserve the legacy recipe or mix full requested and legacy score maps."""
    if family == "Legacy 45d":
        return "legacy"
    _, profile = register_score_blend(
        panel,
        [
            {"mass": 0.5, "weights": weights, "profile": "requested"},
            {"mass": 0.5, "weights": weights, "profile": "legacy"},
        ],
    )
    return profile


def configurations(panel):
    """Test exactly three/four distinct cells, with no vanishing coefficients."""
    extras = EXTRAS + [FEATURES[i] for i in SEARCH_FEATURES if FEATURES[i] not in EXTRAS + [("1y", "CAGR"), ("46d", "Sortino")]]
    extras = extras[: SearchParameters.iterations]
    assert len(extras) == SearchParameters.iterations
    rows = []
    for family, risk in [("Legacy 45d", "45d compatibility"), ("Blend 46d", "46d")]:
        core = [(("1y", "CAGR"), 0.6), ((risk, "Sortino"), 0.4)]
        weights = matrix(core)
        rows.append({"Configuration": family, "Family": family, "Inputs": 2, "Added inputs": "None", "Weights": weights.tolist(), "Profile": recipe(panel, weights, family), "Support": 0})
        for count in (3, 4):
            supports = set()
            for index, feature in enumerate(extras):
                addition = [feature] if count == 3 else [feature, extras[(index + 7) % len(extras)]]
                assert len(set(addition)) == count - 2
                support = tuple(sorted(addition))
                assert support not in supports
                supports.add(support)
                mass = SearchParameters.added_mass
                cells = [(cell, weight * (1 - mass)) for cell, weight in core]
                cells += [(cell, mass / len(addition)) for cell in addition]
                weights = matrix(cells)
                assert np.count_nonzero(weights) == count
                added = " + ".join(f"{p} {m}" for p, m in addition)
                rows.append({"Configuration": f"{family} / {count} inputs / {added}", "Family": family, "Inputs": count, "Added inputs": added, "Weights": weights.tolist(), "Profile": recipe(panel, weights, family), "Support": index + 1})
    assert len({r["Configuration"] for r in rows}) == len(rows)
    return rows


def initialise(private=False):
    """Verify pinned inputs and prepare a separate result generation."""
    manifest = json.loads((INPUT_DIR / "downloads.json").read_text())
    for name in ("vault_prices", "vault_metadata"):
        entry = manifest[name]
        assert hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    evaluator, parameters, _, source_fingerprint = create_evaluator()
    ARTIFACT_DIR.mkdir(exist_ok=True)
    design_fingerprint = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    fingerprint = hashlib.sha256((source_fingerprint + design_fingerprint).encode()).hexdigest()
    public = ARTIFACT_DIR / fingerprint[:16]
    public.mkdir(exist_ok=True)
    evaluator.folder = (ARTIFACT_DIR / "worker-2026" / fingerprint[:16]) if private else public
    evaluator.folder.mkdir(parents=True, exist_ok=True)
    evaluator.fingerprint = fingerprint
    rows = configurations(evaluator.panel)
    if not private:
        (ARTIFACT_DIR / "design.json").write_text(
            json.dumps(
                {
                    "design_date": "2026-10-08",
                    "fingerprint": fingerprint,
                    "source_fingerprint": source_fingerprint,
                    "inputs": manifest,
                    "supports_per_cardinality_per_family": SearchParameters.iterations,
                    "added_mass": SearchParameters.added_mass,
                    "positions": 6,
                    "sizing": "inverse_variance",
                    "missing": True,
                    "allocator": "parent",
                    "selection": "unchanged v11",
                    "periods": {name: list(map(str, dates)) for name, dates in PERIODS.items()},
                    "configurations": rows,
                    "recipes": evaluator.panel.score_blend_recipes,
                },
                indent=2,
            )
        )
    return evaluator, parameters, rows, public


def evaluate(evaluator, row, period, keep=False):
    """Keep sizing, selection, missingness, costs and initial capital unchanged."""
    return evaluator.run(row["Weights"], *PERIODS[period], n=6, sizing="inverse_variance", missing=True, profile=row["Profile"], keep=keep)


def run_grid(evaluator, rows, period):
    """Save progress after each actual backtest, including both two-input controls."""
    records = []
    print(f"{period}: {len(rows)} configurations; estimated {evaluator.remaining(len(rows)):.1f} minutes.")
    for row in tqdm(rows, desc=f"{period} input-count grid", total=len(rows)):
        metrics = evaluate(evaluator, row, period)
        record = {k: v for k, v in row.items() if k not in ("Weights", "Profile")}
        record.update(metrics)
        records.append(record)
        pd.DataFrame(records).to_csv(ARTIFACT_DIR / f"{period}-results.csv", index=False)
    return pd.DataFrame(records)


def shortlist(short, long):
    """Retain separate descriptive 2026 maxima and full-history-selected candidates."""
    names = ["Legacy 45d", "Blend 46d"]
    for frame in (long, short):
        for count in (3, 4):
            candidates = frame[frame.Inputs.eq(count)]
            for metric in ("CAGR", "Sharpe"):
                name = candidates.sort_values([metric, "Configuration"], ascending=[False, True]).iloc[0].Configuration
                if name not in names:
                    names.append(name)
    return names


def support_table(rows, names):
    """Show real period/metric coefficients rather than counting clip terms as inputs."""
    return pd.DataFrame([{"Configuration": row["Configuration"], "Feature": f"{p} {m}", "Weight": weight} for row in rows if row["Configuration"] in names for (p, m), weight in zip(FEATURES, row["Weights"]) if weight > 0])


def grid_figure(frame, count):
    """Use a common metric colour scale across clipping families."""
    fig = make_subplots(rows=1, cols=3, subplot_titles=["CAGR (%)", "Sharpe", "Max DD (%)"], horizontal_spacing=0.13)
    subset = frame[frame.Inputs.eq(count)].sort_values(["Family", "Support"])
    labels = [f'{r["Family"]} · {r["Support"]:02d}: {r["Added inputs"]}' for _, r in subset.iterrows()]
    for column, metric in enumerate(["CAGR", "Sharpe", "Maximum drawdown"], 1):
        values = subset[metric].to_numpy() * (1 if metric == "Sharpe" else 100)
        fig.add_trace(go.Heatmap(z=values[:, None], y=labels, x=[metric], text=np.array([[f"{v:.2f}"] for v in values]), texttemplate="%{text}", colorscale="RdYlGn", showscale=False), row=1, col=column)
        fig.update_yaxes(autorange="reversed", showticklabels=column == 1, row=1, col=column)
    fig.update_layout(title=f"Exactly {count} scoring inputs: all predeclared supports", width=1650, height=1250, margin=dict(t=110, b=70, l=500, r=40), template="plotly_white")
    return fig


def scatter_figure(frame):
    """Show score cardinality and clipping family without selecting a new strategy."""
    import plotly.express as px

    return px.scatter(frame, x="CAGR", y="Sharpe", color="Inputs", symbol="Family", hover_name="Configuration", hover_data=["Maximum drawdown", "Mean cash weight"], title="Two, three and four-input scores: return versus Sharpe", width=1450, height=650, template="plotly_white").update_xaxes(tickformat=".0%")


def write_findings():
    """Update conclusions only after the completed notebook has saved its outputs."""
    notebook = nbformat.read(NOTEBOOK, 4)
    assert all(c.execution_count is not None for c in notebook.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in notebook.cells if c.cell_type == "code" for o in c.outputs)
    short = pd.read_csv(ARTIFACT_DIR / "2026-results.csv")
    long = pd.read_csv(ARTIFACT_DIR / "Long-results.csv")
    robustness = pd.read_csv(ARTIFACT_DIR / "2026-robustness.csv")
    names = shortlist(short, long)
    view = short.set_index("Configuration").loc[names].reset_index()
    long_view = long.set_index("Configuration").loc[names].reset_index()
    baseline = short[short.Configuration.eq("Legacy 45d")].iloc[0]
    insights = []
    for count in (3, 4):
        data = short[short.Inputs.eq(count)]
        best = data.sort_values("CAGR", ascending=False).iloc[0]
        risk = data.sort_values("Sharpe", ascending=False).iloc[0]
        insights.append(f'- **{count} inputs, highest 2026 CAGR:** {best.Configuration}: {best.CAGR:.2%} CAGR, {best.Sharpe:.2f} Sharpe and {best["Maximum drawdown"]:.2%} drawdown. Highest Sharpe is {risk.Sharpe:.2f} for {risk.Configuration}.')
    joint = short[(short.Inputs > 2) & (short.CAGR > baseline.CAGR) & (short.Sharpe > baseline.Sharpe) & (short["Maximum drawdown"] >= baseline["Maximum drawdown"])]
    columns = ["Configuration", "Inputs", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Trades"]

    def formatted(frame):
        result = frame[columns].copy()
        for col in ("CAGR", "Maximum drawdown", "Mean cash weight"):
            result[col] = result[col].map(lambda value: f"{value:.2%}")
        result["Sharpe"] = result.Sharpe.map(lambda value: f"{value:.2f}")
        return markdown_table(result)

    findings = f"""## Key new insights

{chr(10).join(insights)}
- **Joint improvements against original v11:** {len(joint)} of 72 added-input configurations have higher 2026 CAGR and Sharpe with no worse drawdown. This does not establish unseen-time improvement.

## Summary of results

### Selected comparisons — {SHORT_PERIOD}

Two-input controls, the best full-history candidates at each cardinality/objective, and the descriptive 2026 maxima. Every candidate uses six inverse-variance positions and unchanged selection. Equivalent paths can repeat.

{formatted(view)}

<details><summary>Same configurations over full history — {LONG_PERIOD}</summary>

Independent $150,000 starts; this period overlaps 2026 and is not a holdout.

{formatted(long_view)}

</details>

## Robustness of results

All 74 configurations completed both periods. Three-input scores allocate 20% to one additional metric/window; four-input scores allocate 10% to each of two additional cells. Both keep 80% on the same 60/40 CAGR/Sortino core. This tests a predeclared add-on grid, not all combinations or optimal coefficients. Missing additional metrics propagate an unscored composite, as in the source; sparse long-window coverage can therefore change ranking materially. Full-history selections and 2026 maxima are labelled separately, with no claim of independent validation.

Source v11 and its exact two-input matrix match equity and complete trade ledgers in both periods. Position attribution reconciles to initial capital with a maximum residual of {robustness['Attribution residual (USD)'].max():.2e} USD. The notebook reports best days, excess kurtosis, leading-vault concentration, curator annotations and matching BTC/ETH intervals. Fixed-ledger contributor removals are sensitivities, not executable exclusion backtests.
"""
    header = notebook.cells[0].source.split("## Key new insights")[0]
    notebook.cells[0].source = header + findings
    nbformat.write(notebook, NOTEBOOK)
    (RESEARCH_DIR / "06-score-3-4-inputs-analysis.md").write_text("# Experiment 06 — three and four scoring inputs\n\n[Executed notebook](06-opt-score-3-4-inputs.ipynb).\n\n" + findings)
    print(f"Completed {len(short)} short and {len(long)} long configurations; {len(joint)} joint 2026 improvements.")


def precompute_short():
    """Run independent short-period jobs in a private cache, publishing atomically."""
    evaluator, _, rows, public = initialise(private=True)
    for index, row in enumerate(reversed(rows), 1):
        metrics = evaluate(evaluator, row, "2026")
        record = next(reversed(evaluator.records.values()))
        key = record["key"]
        temporary = public / f"{key}.worker.tmp"
        temporary.write_text(json.dumps(metrics, allow_nan=False))
        os.replace(temporary, public / f"{key}.json")
        print(f'{index}/{len(rows)} short: {row["Configuration"]}; CAGR {metrics["CAGR"]:.2%}, Sharpe {metrics["Sharpe"]:.2f}', flush=True)
    (ARTIFACT_DIR / "short-worker-completed.json").write_text(json.dumps({"configurations": len(rows), "engine_calls": evaluator.engine_calls}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--precompute-short", action="store_true")
    parser.add_argument("--write-findings", action="store_true")
    arguments = parser.parse_args()
    if arguments.precompute_short:
        precompute_short()
    elif arguments.write_findings:
        write_findings()
