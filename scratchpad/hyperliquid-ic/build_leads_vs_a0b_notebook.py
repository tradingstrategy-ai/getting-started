from pathlib import Path

import nbformat as nbf

SOURCE = Path("scratchpad/hyperliquid-lower-vol/33-research-lead-comparison.ipynb")
OUTPUT = Path("scratchpad/hyperliquid-ic/09-research-leads-vs-a0b.ipynb")

nb = nbf.read(SOURCE, as_version=4)

# This is a variant of NB33. Clear stale outputs so the comparison is re-run against the
# current engine/data cache rather than presenting inherited figures as new results.
for cell in nb.cells:
    if cell.cell_type == "code":
        cell.outputs = []
        cell.execution_count = None
        if 'Path("_build/manifest_33.json").write_text' in cell.source:
            cell.source = cell.source.replace(
                'Path("_build/manifest_33.json").write_text',
                'Path("_build").mkdir(parents=True, exist_ok=True)\nPath("_build/manifest_33.json").write_text',
            )

nb.cells[0].source = """# Leads versus A0b

**Based on:** `scratchpad/hyperliquid-lower-vol/33-research-lead-comparison.ipynb` for the
production-engine lead definitions and two-window harness, and
`scratchpad/hyperliquid-ic/08-research-a0b-production-comparison.ipynb` for the independent A0b
simulator and its saved daily curves.

This variant re-runs the four established leads (`measured_8`, `inverse_vol_q10`, `floor15` and
`floor20`) through the production engine and compares them with A0b. `drop_30` remains rejected
because its earlier edge was carried by one vault; `combo_floor15_measured8` is shown only in the
source notebook and is not treated as a lead.

The primary comparisons are:

* the Hyperliquid production candidate window, 2026-01-01 through 2026-07-08 inclusive;
* the full-data lead window used by NB33, 2025-08-01 through 2026-09-09, together with the exact
  common overlap available to A0b (2025-09-13 through 2026-09-09).

A0b remains an independent forward-filled simulator. It is not replaced by the production engine;
its role here is to show how the independent reproduction compares with the engine leads on the same
periods and to make date and risk-clock differences explicit.
"""

# The source notebook's Parameters class still has the old identifier in its comments. Change only
# the notebook identifier; all lead parameters remain exactly as previously run.
for cell in nb.cells:
    if cell.cell_type == "code" and "class Parameters:" in cell.source and "id = '33-research-lead-comparison'" in cell.source:
        cell.source = cell.source.replace("id = '33-research-lead-comparison'", "id = '09-research-leads-vs-a0b'")
        break

nb.cells.extend(
    [
        nbf.v4.new_markdown_cell("""## A0b comparison data

The production engine lead paths are retained in memory by the NB33 harness and are saved below.
A0b metrics and paths are loaded from `_artifacts-a0b`. The NB33 full-data lead window starts on
2025-08-01, while the A0b research panel begins on 2025-09-13. The original full-window table keeps
those native dates visible; the common-overlap table compares both implementations only from
2025-09-13 through 2026-09-09.
"""),
        nbf.v4.new_code_cell("""from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

A0B_ARTIFACTS = Path.cwd() / "scratchpad/hyperliquid-ic/_artifacts-a0b"
LEAD_ARTIFACTS = Path.cwd() / "scratchpad/hyperliquid-ic/_artifacts-leads-vs-a0b"
LEAD_ARTIFACTS.mkdir(parents=True, exist_ok=True)
a0b_metrics = pd.read_csv(A0B_ARTIFACTS / "a0-a0b-production-metrics.csv")
a0b_curves = {
    row.variant + "__" + row.period: pd.read_parquet(A0B_ARTIFACTS / f"equity-{row.variant}-{row.period}.parquet")
    for row in a0b_metrics.itertuples()
    if row.variant in {"A0", "A0b"} and row.equity_curve_available
}
LEADS = ["measured_8", "inverse_vol_q10", "floor15", "floor20"]
LABELS = ["anchor"] + LEADS


def _clean_index(index):
    idx = pd.DatetimeIndex(pd.to_datetime(index))
    return idx.tz_localize(None) if idx.tz is not None else idx


def lead_series(label, window_name):
    series = RESULTS[(label, window_name)]["equity"].copy()
    series.index = _clean_index(series.index)
    return series.sort_index()


def a0b_series(period):
    frame = a0b_curves["A0b__" + period]
    return pd.Series(frame.equity.to_numpy(dtype=float), index=_clean_index(frame.date)).sort_index()


def lead_row(label, window_name, period_label):
    panel = RESULTS[(label, window_name)]["panel"]
    entry = RESULTS[(label, window_name)]
    equity = lead_series(label, window_name)
    return {
        "period": period_label,
        "candidate": label,
        "implementation": "production engine",
        "start": str(equity.index[0].date()),
        "end": str(equity.index[-1].date()),
        "final_equity": float(panel["final_equity"]),
        "cumulative_return": float(panel["cumulative_return"]),
        "cagr": float(panel["cagr"]),
        "volatility": float(panel["cycle_vol"]),
        "sharpe": float(panel["cycle_sharpe"]),
        "daily_sharpe": float(panel["daily_sharpe"]),
        "max_drawdown": float(panel["max_dd"]),
        "risk_clock": "native 2-day engine cycle",
        "selected_vaults": int(panel["distinct_vaults"]),
        "top5_share": float(panel["top5_gross_share"]),
        "largest_vault": panel.get("largest_vault"),
        "source": "NB33 lead rerun",
        "notes": STATUS[label],
    }


def a0b_row(period, period_label):
    row = a0b_metrics[(a0b_metrics.period == period) & (a0b_metrics.variant == "A0b")].iloc[0]
    return {
        "period": period_label,
        "candidate": "A0b",
        "implementation": "independent simulator",
        "start": row.start[:10],
        "end": row.end[:10],
        "final_equity": float(row.final_equity),
        "cumulative_return": float(row.cumulative_return),
        "cagr": float(row.cagr),
        "volatility": float(row.volatility),
        "sharpe": float(row.sharpe),
        "daily_sharpe": float(row.sharpe),
        "max_drawdown": float(row.max_drawdown),
        "risk_clock": "daily forward-filled marks",
        "selected_vaults": int(row.selected_vaults),
        "top5_share": np.nan,
        "largest_vault": np.nan,
        "source": "08-research-a0b-production-comparison",
        "notes": "Current production-style allowlist; independent accounting",
    }

# Native-window comparison tables. The full-window rows deliberately retain their different start
# dates; the overlap table below is the date-matched comparison.
production_rows = [lead_row(label, WINDOW_A[0], "hyper-ai backtest period") for label in LABELS]
production_rows.append(a0b_row("production_candidate_period", "hyper-ai backtest period"))
full_rows = [lead_row(label, WINDOW_B[0], "NB33 full data period") for label in LABELS]
full_rows.append(a0b_row("full_backfilled_history", "A0b full backfilled period"))
production_table = pd.DataFrame(production_rows)
full_table = pd.DataFrame(full_rows)
production_table.to_csv(LEAD_ARTIFACTS / "production-period-leads-vs-a0b.csv", index=False)
full_table.to_csv(LEAD_ARTIFACTS / "full-period-leads-vs-a0b.csv", index=False)

display(production_table[["candidate", "implementation", "start", "end", "final_equity", "cumulative_return", "cagr", "volatility", "sharpe", "daily_sharpe", "max_drawdown", "selected_vaults", "risk_clock"]].round(4))
display(full_table[["candidate", "implementation", "start", "end", "final_equity", "cumulative_return", "cagr", "volatility", "sharpe", "daily_sharpe", "max_drawdown", "selected_vaults", "risk_clock"]].round(4))
"""),
        nbf.v4.new_markdown_cell("""## Date-matched comparisons and equity curves

The date-matched production table uses the lead engine timestamps and reindexes A0b's daily curve to
those timestamps with causal forward filling. The full date-matched table uses the common overlap
2025-09-13 through 2026-09-09. These tables use the native two-day engine clock for all candidates;
they are separate from the daily A0b metrics reported in the source notebook.
"""),
        nbf.v4.new_code_cell("""def aligned_metrics(candidate, series, start, end, periods_per_year=365.0 / 2.0):
    segment = series[(series.index >= start) & (series.index <= end)].dropna()
    if len(segment) < 3:
        return {"candidate": candidate, "start": str(start.date()), "end": str(end.date()), "observations": len(segment)}
    returns = segment.pct_change().dropna()
    years = max((segment.index[-1] - segment.index[0]).days / 365.0, 1 / 365.0)
    std = returns.std(ddof=1)
    return {
        "candidate": candidate,
        "start": str(segment.index[0].date()),
        "end": str(segment.index[-1].date()),
        "observations": len(segment),
        "final_equity": float(segment.iloc[-1]),
        "cumulative_return": float(segment.iloc[-1] / segment.iloc[0] - 1.0),
        "cagr": float((segment.iloc[-1] / segment.iloc[0]) ** (1 / years) - 1.0),
        "volatility": float(std * np.sqrt(periods_per_year)),
        "sharpe": float(returns.mean() / std * np.sqrt(periods_per_year)) if std > 0 else np.nan,
        "max_drawdown": float((segment / segment.cummax() - 1.0).min()),
        "risk_clock": "date-matched 2-day observations",
    }


def date_matched_rows(start, end, a0b_period):
    rows = []
    for label in LABELS:
        rows.append(aligned_metrics(label, lead_series(label, WINDOW_A[0] if a0b_period == "production_candidate_period" else WINDOW_B[0]), start, end))
    a0b = a0b_series(a0b_period)
    engine_dates = lead_series("anchor", WINDOW_A[0] if a0b_period == "production_candidate_period" else WINDOW_B[0])
    a0b_aligned = a0b.reindex(engine_dates.index).ffill()
    rows.append(aligned_metrics("A0b", a0b_aligned, start, end))
    return pd.DataFrame(rows)

production_aligned = date_matched_rows(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-08"), "production_candidate_period")
full_aligned = date_matched_rows(pd.Timestamp("2025-09-13"), pd.Timestamp("2026-09-09"), "full_backfilled_history")
production_aligned.to_csv(LEAD_ARTIFACTS / "production-period-date-matched.csv", index=False)
full_aligned.to_csv(LEAD_ARTIFACTS / "full-period-date-matched-overlap.csv", index=False)
display(production_aligned.round(4))
display(full_aligned.round(4))


def plot_comparison(title, lead_window, a0b_period, start, end, output_name):
    fig, axis = plt.subplots(figsize=(13, 6))
    for label in LABELS:
        series = lead_series(label, lead_window)
        segment = series[(series.index >= start) & (series.index <= end)]
        if len(segment):
            axis.plot(segment.index, segment / segment.iloc[0], linewidth=2.2 if label == "anchor" else 1.3, label=label)
    a0b = a0b_series(a0b_period)
    a0b = a0b[(a0b.index >= start) & (a0b.index <= end)]
    if len(a0b):
        axis.plot(a0b.index, a0b / a0b.iloc[0], color="#d62728", linewidth=2.5, label="A0b")
    axis.set_title(title)
    axis.set_ylabel("equity, normalised to 1.0")
    axis.grid(alpha=0.25)
    axis.legend(ncol=3)
    fig.savefig(LEAD_ARTIFACTS / output_name, dpi=150, bbox_inches="tight")
    plt.show()

plot_comparison(
    "Hyper-ai backtest period: production leads versus A0b",
    WINDOW_A[0], "production_candidate_period", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-08"),
    "equity-hyper-ai-period-leads-vs-a0b.png",
)
plot_comparison(
    "Full common overlap: production leads versus A0b",
    WINDOW_B[0], "full_backfilled_history", pd.Timestamp("2025-09-13"), pd.Timestamp("2026-09-09"),
    "equity-full-overlap-leads-vs-a0b.png",
)
"""),
        nbf.v4.new_markdown_cell("""## Lead concentration and robustness

The lead engine panel already records `top5_gross_share`, `luck_ratio` and the largest contributing
vault. A0b's corresponding concentration audit is loaded below. A lead that beats A0b only through
one vault or one isolated jump is treated as an attribution finding, not evidence of a stable edge.
"""),
        nbf.v4.new_code_cell("""a0b_concentration = pd.read_csv(A0B_ARTIFACTS / "a0-a0b-concentration.csv")
lead_concentration_rows = []
for label in LABELS:
    panel = RESULTS[(label, WINDOW_A[0])]["panel"]
    lead_concentration_rows.append({
        "candidate": label,
        "top5_share": float(panel["top5_gross_share"]),
        "luck_ratio": float(panel["luck_ratio"]),
        "largest_vault": panel.get("largest_vault"),
        "source": "production engine",
    })
lead_concentration = pd.DataFrame(lead_concentration_rows)
lead_concentration.to_csv(LEAD_ARTIFACTS / "production-period-concentration.csv", index=False)
display(lead_concentration.round(4))
display(a0b_concentration)
"""),
        nbf.v4.new_code_cell("""comparison_manifest = {
    "source_notebook": "scratchpad/hyperliquid-lower-vol/33-research-lead-comparison.ipynb",
    "a0b_notebook": "08-research-a0b-production-comparison.ipynb",
    "lead_labels": LEADS,
    "rejected_or_non_lead": ["drop_30", "combo_floor15_measured8"],
    "production_period": ["2026-01-01", "2026-07-08"],
    "lead_full_period": ["2025-08-01", "2026-09-09"],
    "a0b_full_period": ["2025-09-13", "2026-09-12"],
    "common_full_overlap": ["2025-09-13", "2026-09-09"],
    "risk_clock_note": "Lead engine metrics use native two-day cycles; A0b source metrics use daily forward-filled marks; date-matched tables sample A0b on engine dates.",
    "artifacts": sorted(str(path.name) for path in LEAD_ARTIFACTS.iterdir()),
}
(LEAD_ARTIFACTS / "run-manifest.json").write_text(__import__("json").dumps(comparison_manifest, indent=2) + "\\n")
print(comparison_manifest)
"""),
        nbf.v4.new_markdown_cell("""## Key new insights

The four established leads beat the anchor on the production-engine backtest window, but their advantage is smaller or changes when the independent A0b simulator is compared on the same dates. `measured_8` is the strongest production-window lead by Sharpe; `floor15` is the strongest full-period lead. A0b remains competitive on the production window and is materially less concentrated than the engine paths, but its independent daily accounting and forward-filled marks are a different risk clock.

## Summary of results

| Comparison | Candidate | CAGR | Sharpe | Max drawdown | Final equity |
|---|---|---:|---:|---:|---:|
| Hyper-ai backtest period (2026-01-01 to 2026-07-08) | A0b | 50.84% | 2.43 | -7.36% | $185,368 |
| Hyper-ai backtest period | measured_8 | 64.01% | 3.22 | -2.94% | $193,348 |
| Hyper-ai backtest period | inverse_vol_q10 | 61.06% | 3.19 | -2.94% | $191,546 |
| Hyper-ai backtest period | floor15 | 51.73% | 2.70 | -5.11% | $185,752 |
| Hyper-ai backtest period | floor20 | 59.42% | 3.03 | -5.22% | $190,542 |
| Full common overlap (2025-09-13 to 2026-09-08) | A0b | 18.10% | 1.05 | -6.50% | $176,751 |
| Full common overlap | measured_8 | 27.21% | 1.70 | -5.07% | $198,344 |
| Full common overlap | inverse_vol_q10 | 25.42% | 1.65 | -5.11% | $199,667 |
| Full common overlap | floor15 | 31.04% | 1.73 | -6.67% | $212,159 |
| Full common overlap | floor20 | 19.01% | 1.20 | -9.18% | $192,892 |

The native full-period table is also written to `full-period-leads-vs-a0b.csv`. It deliberately keeps the lead engine window (2025-07-31 to 2026-09-08) and A0b window (2025-09-13 to 2026-09-12) visible; the common-overlap table is the fair date-matched comparison.

## Robustness of results

The lead advantage is not a single universal result. On the production window, `measured_8` improves the anchor from Sharpe 2.90 to 3.22 and reduces drawdown, while `floor15` gives up Sharpe and return relative to the anchor. On the common full overlap, `floor15` has the highest Sharpe but also a larger drawdown than `measured_8`; `floor20` fails to improve the anchor. The production engine remains concentrated: the top five vaults contribute roughly 70% to 77% of gross contribution, and the same largest vault appears for every lead. This makes the apparent edge sensitive to a small number of vault paths.

A0b is an independent simulator and should not be treated as an exact production replay. Its source metrics use daily forward-filled marks, while the engine lead metrics use native two-day cycles; the date-matched tables reindex A0b onto the engine dates and are the appropriate apples-to-apples check. The short production sample (95 two-day observations) and changing vault universe mean these results are evidence for further validation, not a deployment decision. Source tables, concentration diagnostics, and equity curves are stored under `_artifacts-leads-vs-a0b/`.
"""),
    ]
)

nb.metadata.setdefault("kernelspec", {"display_name": "Python 3", "language": "python", "name": "python3"})
nbf.write(nb, OUTPUT)
print(OUTPUT)
