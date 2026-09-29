import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, INDICATOR_ADDITIONS_PREFILTER, \
    CELL14_REPLACEMENTS_PREFILTER

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

HEADING = """# NB33 - the incumbent and the best leads, side by side, on two windows

**Based on:** [26-backtest-drop-decomposition.ipynb](26-backtest-drop-decomposition.ipynb),
[29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb) and
[32-backtest-return-floor-stability-rank.ipynb](32-backtest-return-floor-stability-rank.ipynb)
for the leads; [02-better-format.ipynb](02-better-format.ipynb) for the anchor. The anchor is
parameter-for-parameter `~/code/strategies/strategy/hyper-ai.py` (v6) with a later
`backtest_end`, verified in [_build/verify-hyperai-window.ipynb](_build/verify-hyperai-window.ipynb).

## What this notebook is

A comparison, not a test. It re-runs the incumbent and every lead the track has produced through
one kernel on one snapshot, on two windows, and puts the equity curves on one chart. Nothing here
is gated, pre-registered or shortlisted; the leads' own robustness checks live in their own
notebooks and are not repeated.

**Window A - the incumbent's own period.** `hyper-ai.py` reports its backtest on 2026-01-01 to
2026-07-10. Every configuration is run on exactly that window so its figures can be set beside
the incumbent's docstring.

**Window B - the full data period.** 2025-08-01 to 2026-09-09, the earliest start the earlier
`hyper-ai` generations used. Before 2026-04 most Hyperliquid vaults were polled roughly weekly,
not daily: the archive holds about 1,300 rows a month across 200 vaults in August 2025 against
300,000 a month across 480 in August 2026. The strategy's daily series is forward-filled across
the gaps, so a stale mark is an exact zero return, and `cagr_score` needs 360 days of history
that only a few dozen vaults had in 2025. The density table and chart below show this; the
metrics on window B must be read with it.

## Configurations

| label | what | source | status there |
|---|---|---|---|
| `anchor` | `hyper-ai.py` as deployed | NB02 | reference |
| `measured_8` | drop the 8 most volatile vaults that HAVE a volatility estimate, then rank as the incumbent | NB26 | best leave-one-vault-out retention in the track |
| `inverse_vol_q10` | drop the least-stable 10% of finite-signal candidates (same family) | NB29 | not the pre-registered centre |
| `floor15` | incumbent composite behind a 15% annualised return floor over 45 days | NB32 | highest Sharpe in its grid; spike on basket size |
| `floor20` | the same with a 20% floor | NB32 | best single-vault survival in the track |
| `drop_30` | drop the 30 lowest `inverse_vol` (21 of them unmeasured) | NB21 | REJECTED - one vault carries 98% of its edge |
| `combo_floor15_measured8` | `floor15` and `measured_8` together | none | NOT a lead - the combination proposed for the next pre-registration, shown for scale |

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "33-research-lead-comparison",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_PREFILTER},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY + INDICATOR_ADDITIONS_PREFILTER,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_PREFILTER)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

cells.append(md("""## Part 0. Provenance, parity, and the two windows"""))
cells.append(code('''import json
import datetime
from pathlib import Path
import plotly.graph_objects as go
from tradeexecutor.statistics.key_metric import calculate_sharpe, calculate_sortino

display(provenance())
display(assert_anchor_parity())
record_anchor()

WINDOW_A = ("A: incumbent period", datetime.datetime(2026, 1, 1), datetime.datetime(2026, 7, 10))
WINDOW_B = ("B: full data period", datetime.datetime(2025, 8, 1), datetime.datetime(2026, 9, 9))
FLOOR_LOOKBACK = 45


def floor_threshold(annual: float, days: int = FLOOR_LOOKBACK) -> float:
    return (1.0 + annual) ** (days / 365.0) - 1.0


#: label -> overrides. Every lead exactly as its source notebook ran it.
CONFIGS = {
    "anchor": {},
    "measured_8": dict(vol_drop_mode="measured_only", vol_matched_drop_count=8),
    "inverse_vol_q10": dict(stability_prefilter_signal="inverse_vol", stability_prefilter_direction="low",
                            stability_prefilter_fraction=0.10, require_scored_candidates=False),
    "floor15": dict(gate_lookback_days=FLOOR_LOOKBACK, gate_threshold=floor_threshold(0.15)),
    "floor20": dict(gate_lookback_days=FLOOR_LOOKBACK, gate_threshold=floor_threshold(0.20)),
    "drop_30": dict(vol_matched_drop_count=30),
    "combo_floor15_measured8": dict(gate_lookback_days=FLOOR_LOOKBACK, gate_threshold=floor_threshold(0.15),
                                    vol_drop_mode="measured_only", vol_matched_drop_count=8),
}
STATUS = {
    "anchor": "reference (= hyper-ai.py)", "measured_8": "lead (NB26)", "inverse_vol_q10": "lead (NB29)",
    "floor15": "lead (NB32)", "floor20": "lead (NB32)", "drop_30": "REJECTED (NB21, one vault)",
    "combo_floor15_measured8": "NOT a lead - proposed combination",
}
print("thresholds:", {k: round(floor_threshold(v), 5) for k, v in (("15%", 0.15), ("20%", 0.20))})
'''))

cells.append(md("""## Part 1. How sparse the archive is before 2026

One row per month of the Hyperliquid vault archive: rows, distinct vaults, vaults above the
$7,500 TVL screen, fresh (price-changing) marks, and the median polls per vault per day. Window B
starts where the earlier `hyper-ai` generations started; anything before that is thinner still.
"""))
cells.append(code('''archive = pd.read_parquet(PROVENANCE_PATHS[0], columns=["address", "chain", "share_price", "total_assets"]).reset_index()
archive = archive[archive["chain"] == 9999].copy()
archive["timestamp"] = pd.to_datetime(archive["timestamp"])
archive = archive[archive["timestamp"] >= pd.Timestamp("2025-01-01")]
archive["month"] = archive["timestamp"].dt.to_period("M")
archive["moved"] = archive.groupby("address", observed=True)["share_price"].diff().abs() > 0
rows = []
for month, x in archive.groupby("month"):
    days = max(x["timestamp"].dt.date.nunique(), 1)
    rows.append({"month": str(month), "rows": len(x), "vaults": x["address"].nunique(),
                 "vaults_tvl_ge_7500": x[x["total_assets"] >= 7500]["address"].nunique(),
                 "fresh_marks": int(x["moved"].sum()),
                 "median_polls_per_vault_per_day": float(x.groupby("address", observed=True).size().median() / days)})
density = pd.DataFrame(rows).set_index("month")
display(density)

fig = go.Figure()
fig.add_trace(go.Bar(x=density.index, y=density["fresh_marks"], name="fresh marks / month", opacity=0.6))
fig.add_trace(go.Scatter(x=density.index, y=density["vaults_tvl_ge_7500"], name="vaults above $7,500 TVL",
                         yaxis="y2", mode="lines+markers"))
fig.update_layout(title="Archive density by month: fresh marks (bars, left) and eligible vaults (line, right)",
                  yaxis=dict(title="fresh marks", type="log"), yaxis2=dict(title="vaults", overlaying="y", side="right"),
                  height=420, template="plotly_white")
fig.show()
'''))

cells.append(md("""### An engine assertion at float precision

`get_remaining_cost_basis()` in the strategy cell asserts that its replayed share count matches
the position's to an ABSOLUTE 1e-8. On window B a vault with 118 million shares fails that by
1.3e-8 - the float64 resolution of a number that size. The function is redefined here with a
relative tolerance and is otherwise identical; the strategy cell is shared with every earlier
notebook and is not edited. This did not arise on the track window.
"""))
cells.append(code('''def get_remaining_cost_basis(position) -> float:
    quantity = 0.0
    cost_basis = 0.0
    for trade in sorted(position.get_successful_trades(), key=lambda trade: trade.executed_at):
        trade_quantity = abs(float(trade.get_position_quantity()))
        if trade.is_buy():
            quantity += trade_quantity
            cost_basis += trade_quantity * float(trade.executed_price)
        elif trade.is_sell():
            assert quantity > 0, f"Cannot sell without a cost basis: {trade}"
            sold_quantity = min(trade_quantity, quantity)
            cost_basis *= (quantity - sold_quantity) / quantity
            quantity -= sold_quantity
    held = float(position.get_quantity())
    assert abs(quantity - held) <= 1e-8 * max(1.0, abs(held)), (
        f"Cost-basis quantity mismatch for {position}: {quantity} vs {position.get_quantity()}"
    )
    return cost_basis
'''))

cells.append(md("""## Part 2. Fourteen backtests

Every configuration on both windows. Runs are recorded slim: equity, cycle returns, the panel,
the held set and the largest contributor are kept; the state is released.
"""))
cells.append(code('''RESULTS = {}


def run_cfg(label: str, window, **overrides) -> dict:
    name, start, end = window
    key = (label, name)
    if key in RESULTS:
        return RESULTS[key]
    VOL_DROP_LOG.clear(); COMPLEMENT_LOG.clear(); SLEEVE_LOG.clear(); PREFILTER_LOG.clear()
    state_, equity_, returns_ = run_variant(f"{label} [{name}]", backtest_start=start, backtest_end=end, **overrides)
    rc, ppy = cycle_returns(equity_)
    daily = equity_.resample("1D").last().ffill().pct_change().dropna()
    row = panel(f"{label} [{name}]", state_, equity_, returns_)
    row["daily_sharpe"] = float(daily.mean() / daily.std() * (365 ** 0.5)) if daily.std() > 0 else float("nan")
    row["cumulative_return"] = float(equity_.iloc[-1] / equity_.iloc[0] - 1.0)
    row["final_equity"] = float(equity_.iloc[-1])
    row["cycles"] = int(len(rc))
    row["distinct_vaults"] = len({str(p.pair.pool_address).lower() for p in state_.portfolio.get_all_positions() if not p.is_credit_supply()})
    row["largest_vault"] = largest_contributing_vault(state_)
    entry = {"label": label, "window": name, "overrides": dict(overrides), "equity": equity_,
             "cycle_returns": rc, "periods_per_year": ppy, "panel": row}
    RESULTS[key] = entry
    return entry


for window in (WINDOW_A, WINDOW_B):
    for label, overrides in CONFIGS.items():
        run_cfg(label, window, **overrides)
print(f"{len(RESULTS)} runs recorded")
'''))

cells.append(md("""## Part 3. Window A - the incumbent's period, 2026-01-01 to 2026-07-10

`hyper-ai.py`'s docstring, on an archive downloaded 2026-08-21: cumulative return 27.76%, CAGR
61.72%, daily Sharpe 2.88, max drawdown -4.44%. The anchor row below is the same strategy on this
archive; the difference between the two is the snapshot.
"""))
cells.append(code('''COLUMNS = ["cumulative_return", "cagr", "cycle_sharpe", "daily_sharpe", "cycle_vol", "ulcer", "max_dd",
           "abs_invested_beta", "mean_invested", "luck_ratio", "top5_gross_share", "distinct_vaults", "cycles"]


def table(window_name: str) -> pd.DataFrame:
    frame = pd.DataFrame([RESULTS[(label, window_name)]["panel"] for label in CONFIGS]).set_index("label")
    frame.index = [i.split(" [")[0] for i in frame.index]
    frame.insert(0, "status", [STATUS[i] for i in frame.index])
    return frame


table_a = table(WINDOW_A[0])
pd.set_option("display.width", 260)
display(table_a[["status"] + COLUMNS].round(4))
print("hyper-ai.py docstring, same window, archive 2026-08-21: cumulative 0.2776, CAGR 0.6172, daily Sharpe 2.88, max DD -0.0444")
'''))

cells.append(code('''COLOURS = {"anchor": "#111111", "measured_8": "#1f77b4", "inverse_vol_q10": "#17becf", "floor15": "#2ca02c",
           "floor20": "#98df8a", "drop_30": "#d62728", "combo_floor15_measured8": "#9467bd"}


def equity_figure(window_name: str, title: str, shade=None, vline=None):
    fig = go.Figure()
    for label in CONFIGS:
        e = RESULTS[(label, window_name)]
        curve = e["equity"] / float(e["equity"].iloc[0])
        p = e["panel"]
        fig.add_trace(go.Scatter(
            x=curve.index, y=curve.to_numpy(), mode="lines",
            name=f"{label}  ({p['cumulative_return']*100:+.1f}%, Sharpe {p['cycle_sharpe']:.2f})",
            line=dict(color=COLOURS[label], width=4 if label == "anchor" else 1.8,
                      dash="dot" if label in ("drop_30", "combo_floor15_measured8") else "solid"),
            opacity=1.0 if label == "anchor" else 0.85))
    # Shapes take ISO strings: plotly's annotation helper adds integers to the x value, which a
    # pandas Timestamp refuses.
    if shade is not None:
        fig.add_vrect(x0=pd.Timestamp(shade[0]).isoformat(), x1=pd.Timestamp(shade[1]).isoformat(),
                      fillcolor="#888", opacity=0.08, line_width=0)
        fig.add_annotation(x=pd.Timestamp(shade[0]).isoformat(), y=1.0, yref="paper", text="incumbent's window",
                           showarrow=False, xanchor="left", yanchor="top")
    if vline is not None:
        fig.add_shape(type="line", x0=pd.Timestamp(vline).isoformat(), x1=pd.Timestamp(vline).isoformat(),
                      y0=0, y1=1, yref="paper", line=dict(color="#888", dash="dash"))
        fig.add_annotation(x=pd.Timestamp(vline).isoformat(), y=0.02, yref="paper", text="polling-density break",
                           showarrow=False, xanchor="left")
    fig.update_layout(title=title, height=600, yaxis_title="equity, normalised to 1.0", template="plotly_white",
                      legend=dict(x=0.01, y=0.99))
    fig.show()


equity_figure(WINDOW_A[0], "Window A: the incumbent's period, 2026-01-01 to 2026-07-10 (dotted = rejected / not a lead)")
'''))

cells.append(md("""## Part 4. Window B - the full data period, 2025-08-01 to 2026-09-09

Read with Part 1 open. The first five months are on weekly-ish polling with forward-filled gaps;
the last five are on hourly polling. A configuration's window-B figure is one number over two
data regimes, and the sub-period table that follows is the more honest reading.
"""))
cells.append(code('''table_b = table(WINDOW_B[0])
display(table_b[["status"] + COLUMNS].round(4))
equity_figure(WINDOW_B[0], "Window B: full data period, 2025-08-01 to 2026-09-09",
              shade=(WINDOW_A[1], WINDOW_A[2]), vline=pd.Timestamp("2026-04-01"))
'''))

cells.append(md("""## Part 5. Sub-periods of window B

Cumulative return, cycle Sharpe and max drawdown of each window-B run over three periods: before
the incumbent's window (sparse polling, 2025-08-01 to 2025-12-31), the incumbent's window
(2026-01-01 to 2026-07-09), and after it (2026-07-10 to 2026-09-08). Computed from the SAME
window-B equity path, so the book carries across the boundaries - unlike window A, which starts
fresh on 2026-01-01.
"""))
cells.append(code('''PERIODS = [("pre-incumbent, sparse", pd.Timestamp("2025-08-01"), pd.Timestamp("2026-01-01")),
           ("incumbent window", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-10")),
           ("after incumbent window", pd.Timestamp("2026-07-10"), pd.Timestamp("2026-09-09"))]


def period_metrics(entry, start, end) -> dict:
    e = entry["equity"]; seg = e[(e.index >= start) & (e.index < end)]
    if len(seg) < 3:
        return {"cum_return": float("nan"), "sharpe": float("nan"), "max_dd": float("nan"), "cycles": len(seg)}
    r = seg.pct_change().dropna()
    return {"cum_return": float(seg.iloc[-1] / seg.iloc[0] - 1.0),
            "sharpe": float(calculate_sharpe(r, periods=entry["periods_per_year"])) if r.std() > 0 else float("nan"),
            "max_dd": float((seg / seg.cummax() - 1.0).min()), "cycles": int(len(r))}


rows = []
for label in CONFIGS:
    entry = RESULTS[(label, WINDOW_B[0])]
    for name, start, end in PERIODS:
        rows.append({"label": label, "period": name, **period_metrics(entry, start, end)})
periods = pd.DataFrame(rows)
for metric in ("cum_return", "sharpe", "max_dd", "cycles"):
    print(f"\\n=== {metric} by period (window-B path) ===")
    display(periods.pivot(index="label", columns="period", values=metric)
            .reindex(index=list(CONFIGS), columns=[p[0] for p in PERIODS]).round(4))
'''))

cells.append(md("""## Part 6. Paired differences against the anchor, both windows

Context only. Block bootstrap on the cycle-return difference against the same-window anchor.
This window cannot resolve Sharpe differences of the size involved and the intervals say so.
"""))
cells.append(code('''rows = []
for window in (WINDOW_A, WINDOW_B):
    anchor_rc = RESULTS[("anchor", window[0])]["cycle_returns"]
    for label in CONFIGS:
        if label == "anchor":
            continue
        rc = RESULTS[(label, window[0])]["cycle_returns"]
        r = bootstrap_paired_sharpe_diff(rc, anchor_rc, periods_per_year=RESULTS[(label, window[0])]["periods_per_year"], block=10)
        rows.append({"window": window[0], "label": label, "sharpe_diff": r["observed"], "ci_lo": r["lo"], "ci_hi": r["hi"],
                     "excludes_zero": bool(np.isfinite(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0))})
paired = pd.DataFrame(rows)
display(paired.round(4))
'''))

cells.append(code('''manifest = {
    "verdict": "COMPARISON - nothing gated, nothing shortlisted",
    "provenance": provenance().to_dict(orient="records"),
    "windows": {w[0]: [str(w[1].date()), str(w[2].date())] for w in (WINDOW_A, WINDOW_B)},
    "configs": {k: {kk: (float(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in CONFIGS.items()},
    "status": STATUS,
    "hyper_ai_docstring": {"window": "2026-01-03 to 2026-07-08", "archive": "2026-08-21", "cumulative_return": 0.2776,
                           "cagr": 0.6172, "daily_sharpe": 2.88, "max_dd": -0.0444},
    "table_a": table_a[COLUMNS + ["largest_vault"]].round(6).to_dict(orient="index"),
    "table_b": table_b[COLUMNS + ["largest_vault"]].round(6).to_dict(orient="index"),
    "periods": periods.round(6).to_dict(orient="records"),
    "paired": paired.round(6).to_dict(orient="records"),
    "density": density.round(4).to_dict(orient="index"),
}
Path("_build/manifest_33.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_33.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "33-research-lead-comparison.ipynb")
