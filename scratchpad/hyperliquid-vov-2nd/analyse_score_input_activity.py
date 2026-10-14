"""Audit whether extra score inputs are available and vary in funded observations."""

import datetime
import json

import nbformat
import numpy as np
import pandas as pd

from score_input_count_experiment import ARTIFACT_DIR, NOTEBOOK, SHORT_PERIOD, LONG_PERIOD, initialise, evaluate, shortlist, recipe
from score_matrix import FEATURES
from score_matrix_analysis import markdown_table
from score_calibration_report import attribution
from tradingstrategy.binance.price import fetch_binance_price


def main():
    """Read retained states and causal feature panels after notebook completion."""
    evaluator, _, candidates, _ = initialise()
    short = pd.read_csv(ARTIFACT_DIR / "2026-results.csv")
    long = pd.read_csv(ARTIFACT_DIR / "Long-results.csv")
    names = shortlist(short, long)
    rows = []
    summaries = []
    for row in candidates:
        name = row["Configuration"]
        if name not in names:
            continue
        run = evaluate(evaluator, row, "2026", keep=True)
        ledger = run["allocation_df"]
        funded = ledger[ledger["Final target (USD)"] > 0].copy()
        dates = np.array([evaluator.panel.date_index[pd.Timestamp(d)] for d in funded.Date])
        pairs = np.array([evaluator.panel.pair_index[int(pid)] for pid in funded["Pair id"]])
        dollars = funded["Final target (USD)"].to_numpy()
        composite = evaluator.panel.score_values(row["Weights"], missing=True, profile=row["Profile"])[dates, pairs]
        summaries.append({"Configuration": name, "Inputs": row["Inputs"], "Funded target rows": len(funded), "Unscored target dollars": float(dollars[~np.isfinite(composite)].sum() / dollars.sum())})
        for feature in np.flatnonzero(row["Weights"]):
            period, metric = FEATURES[feature]
            values = evaluator.panel.cell_scores(feature, missing=True, profile="legacy")
            if row["Family"] == "Blend 46d":
                values = 0.5 * values + 0.5 * evaluator.panel.cell_scores(feature, missing=True, profile="requested")
            values = values[dates, pairs]
            finite = np.isfinite(values)
            observations = pd.DataFrame({"Date": funded.Date.to_numpy(), "Score": values})
            variation = observations.groupby("Date").Score.std()
            rows.append({"Configuration": name, "Feature": f"{period} {metric}", "Coefficient": row["Weights"][feature], "Available target dollars": float(dollars[finite].sum() / dollars.sum()), "At maximum score": float(dollars[finite & (values >= 1 - 1e-12)].sum() / dollars.sum()), "Funded dates with varying score": float(variation.gt(1e-12).mean())})
    signals = pd.DataFrame(rows)
    summary = pd.DataFrame(summaries)
    signals.to_csv(ARTIFACT_DIR / "2026-input-activity.csv", index=False)
    summary.to_csv(ARTIFACT_DIR / "2026-score-availability.csv", index=False)
    long_names = ["Legacy 45d", "Blend 46d"]
    for count in (3, 4):
        for metric in ("CAGR", "Sharpe"):
            name = long[long.Inputs.eq(count)].sort_values(metric, ascending=False).iloc[0].Configuration
            if name not in long_names:
                long_names.append(name)
    lookup = {row["Configuration"]: row for row in candidates}
    long_runs = {name: evaluate(evaluator, lookup[name], "Long", keep=True) for name in long_names}
    market = {symbol: fetch_binance_price(symbol=symbol, start=datetime.datetime(2023, 2, 22))["open"] for symbol in ("BTCUSDT", "ETHUSDT")}
    robust_long, contributors_long, jumps_long, positions_long = attribution(long_runs, market)
    for label, frame in [("Long-robustness", robust_long), ("Long-contributors", contributors_long), ("Long-jumps", jumps_long), ("Long-positions", positions_long)]:
        frame.to_csv(ARTIFACT_DIR / f"{label}.csv", index=False)
    ablations = []
    for name in names:
        original = lookup[name]
        if original["Inputs"] == 2:
            continue
        collapsed = np.array(original["Weights"]).copy()
        core = {"CAGR": FEATURES.index(("1y", "CAGR")), "Sortino": FEATURES.index(("45d compatibility" if original["Family"] == "Legacy 45d" else "46d", "Sortino"))}
        for i, (period, metric) in enumerate(FEATURES):
            if metric in core and i != core[metric]:
                collapsed[core[metric]] += collapsed[i]
                collapsed[i] = 0.0
        if np.array_equal(collapsed, original["Weights"]):
            continue
        control = {**original, "Weights": collapsed.tolist(), "Inputs": int(np.count_nonzero(collapsed)), "Profile": recipe(evaluator.panel, collapsed, original["Family"])}
        for period, frame in [("2026", short), ("Long", long)]:
            metrics = evaluate(evaluator, control, period)
            actual = frame[frame.Configuration.eq(name)].iloc[0]
            ablations.append({"Period": period, "Configuration": name, "Original inputs": original["Inputs"], "Collapsed inputs": control["Inputs"], "Candidate CAGR": actual.CAGR, "Collapsed CAGR": metrics["CAGR"], "Candidate Sharpe": actual.Sharpe, "Collapsed Sharpe": metrics["Sharpe"], "Candidate max DD": actual["Maximum drawdown"], "Collapsed max DD": metrics["Maximum drawdown"]})
    ablations = pd.DataFrame(ablations)
    ablations.to_csv(ARTIFACT_DIR / "metric-mass-ablations.csv", index=False)
    for col in ("Available target dollars", "At maximum score", "Funded dates with varying score", "Coefficient"):
        signals[col] = signals[col].map(lambda v: f"{v:.1%}")
    summary["Unscored target dollars"] = summary["Unscored target dollars"].map(lambda v: f"{v:.1%}")
    section = f"""## Additional-signal availability — {SHORT_PERIOD}

Distinct non-zero coefficients do not guarantee distinct information. This audit measures undefined composite scores and each input's availability, clipping saturation and variation across funded vaults. Dollar fractions use requested final targets, not realised time-weighted exposure. Variation within the funded basket does not measure predictive power or the whole eligible universe.

{markdown_table(summary)}

<details><summary>Per-input activity and clipping — {SHORT_PERIOD}</summary>

Each coefficient is meaningful by design, but a clipped input can be constant across the funded basket. Missing inputs follow the unchanged source unscored behaviour.

{markdown_table(signals)}

</details>
"""

    def ablation_table(period):
        frame = ablations[ablations.Period.eq(period)].drop(columns="Period").copy()
        for col in frame:
            if "CAGR" in col or "DD" in col:
                frame[col] = frame[col].map(lambda v: f"{v:.2%}")
            if "Sharpe" in col:
                frame[col] = frame[col].map(lambda v: f"{v:.2f}")
        return markdown_table(frame)

    section += f"""\n## Does an extra lookback add information? — {SHORT_PERIOD}

Collapse every additional CAGR/Sortino lookback into the original core lookback while preserving total weight on each metric, clipping recipes, sizing and selection. Other metric inputs stay unchanged. These post-selection diagnostic backtests distinguish an extra window from merely changing the CAGR/Sortino balance; they are exploratory and are not a new optimiser.

{ablation_table('2026')}

<details><summary>Same metric-mass controls over full history — {LONG_PERIOD}</summary>

Independent fresh-start runs on the same inputs. Feature counts can remain above two when the original candidate contains an additional metric such as Sharpe.

{ablation_table('Long')}

</details>
"""
    long_columns = ["Configuration", "Best day", "Best day return", "Leading vault", "Leader share of positive vault PnL", "Sharpe with best day zeroed", "Sharpe without leader (fixed ledger)"]
    long_table = robust_long[long_columns].copy()
    for col in ("Best day return", "Leader share of positive vault PnL"):
        long_table[col] = long_table[col].map(lambda v: f"{v:.1%}")
    for col in ("Sharpe with best day zeroed", "Sharpe without leader (fixed ledger)"):
        long_table[col] = long_table[col].map(lambda v: f"{v:.2f}")
    section += f"""\n## Full-history profit concentration — {LONG_PERIOD}

<details><summary>Best-day and leading-vault sensitivities for full-history-selected candidates</summary>

Two-input references and the full-history CAGR/Sharpe leaders at each input count. Position PnL is reconciled to equity; contributor removals retain the original trading ledger and are not exclusion backtests. Full-history curator annotations and BTC/ETH interval context are also saved to CSV.

{markdown_table(long_table)}

</details>
"""
    notebook = nbformat.read(NOTEBOOK, 4)
    notebook.cells = [c for c in notebook.cells if not (c.cell_type == "markdown" and c.source.startswith("## Additional-signal availability"))]
    notebook.cells.append(nbformat.v4.new_markdown_cell(section))
    nbformat.write(notebook, NOTEBOOK)
    report = NOTEBOOK.parent / "06-score-3-4-inputs-analysis.md"
    text = report.read_text().split("## Additional-signal availability")[0]
    report.write_text(text + "\n" + section)
    print(json.dumps({"retained_paths": len(summary), "input_rows": len(signals), "maximum_unscored_target_fraction": float(pd.DataFrame(summaries)["Unscored target dollars"].max())}))


if __name__ == "__main__":
    main()
