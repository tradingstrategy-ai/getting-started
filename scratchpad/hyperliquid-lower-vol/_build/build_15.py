import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE

HARNESS_EVIDENCE = (Path(__file__).parent / "harness_evidence.py").read_text()

HEADING = """# NB15 - backtest: the placebo frontier (CONTROL)

No strategy change beyond the pre-registered placebo mechanism. What Sharpe does pure volatility
avoidance (`vol_matched_drop_count`, NB42's pre-registered control) deliver at each level of
volatility? This is the line every later candidate in NB16-NB18 must clear (constraint 7 of the
adoption rule). **It is a control and can never be adopted, whatever it scores.**

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Part of [14-evidence-weighted-plan.md](14-evidence-weighted-plan.md).

## Method

Seven `vol_matched_drop_count` runs (0, 10, 20, 30, 40, 50, 60), reduced to their non-dominated
(Pareto) subset before use - a lower-volatility point that scored a lower Sharpe than a
higher-volatility point is dominated and excluded, so the envelope always represents the BEST
Sharpe pure de-risking achieved at or below a given volatility. Two cash overlays
(`target_portfolio_vol` 0.15 and 0.10) are run for the chart only, so the cash line and the
volatility-avoidance line are visually distinct - constraint 6 (deployment >= 90%) already
excludes cash overlays from adoption regardless of where they sit on this chart.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "15-backtest-placebo-frontier",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_EVIDENCE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE,
)
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness (anchor), then the evidence-track additions.\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells += integrity_and_audit_cells()

cells.append(md("""# The placebo frontier

Seven `vol_matched_drop_count` runs, retaining both the summary panel and each run's own cycle
returns (needed by `bootstrap_sharpe_diff_vs_control()` in NB16-NB18).
"""))
cells.append(code('''anchor_cycle_returns, _ = cycle_returns(anchor_equity)
frontier, cyc_returns_by_label = build_placebo_frontier(anchor_cycle_returns)
frontier["role"] = "CONTROL"
display(frontier[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer", "abs_invested_beta", "mean_invested", "role"]])

envelope = _pareto_envelope(frontier)
dominated = frontier.index.difference(envelope.index)
print(f"Non-dominated (Pareto) envelope: {list(envelope.index)}")
print(f"Dominated, excluded from the envelope: {list(dominated) if len(dominated) else 'none'}")
print(f"Envelope volatility range: {envelope['cycle_vol'].min():.4f} to {envelope['cycle_vol'].max():.4f}")
print("placebo_sharpe_at() returns NaN (constraint 7 FAILS) for any candidate outside this range.")
'''))

cells.append(md("""# Cash overlays, for the chart only

Not part of the placebo frontier and not compared against constraint 7 - shown so the
volatility-avoidance line (selection-preserving) and the cash line (deployment-reducing) are
visibly different mechanisms on the same chart. Both are excluded from adoption by constraint 6
(deployment >= 90%) regardless of where they land here.
"""))
cells.append(code('''runs = [("anchor", anchor_state, anchor_equity, anchor_returns, anchor_panel)]

cash_rows = []
for label, target_vol in (("target_vol_0.15", 0.15), ("target_vol_0.10", 0.10)):
    s, e, r = run_variant(label, target_portfolio_vol=target_vol)
    p = panel(label, s, e, r, anchor_cycle_returns)
    cash_rows.append(p)
    runs.append((label, s, e, r, p))

cash_df = pd.DataFrame(cash_rows).set_index("label")
cash_df["role"] = "CONTROL (cash overlay - excluded from adoption by the deployment floor)"
display(cash_df[["cagr", "cycle_vol", "cycle_sharpe", "ulcer", "mean_invested", "role"]])
'''))

cells.append(md("""# Verdict table and charts
"""))
cells.append(code('''all_rows = [anchor_panel] + [frontier.loc[l].drop("role") for l in frontier.index if l != "anchor"] + cash_rows
vt = verdict_table(all_rows, anchor_panel, frontier)
vt["role"] = ["CONTROL" if l != "anchor" else "anchor" for l in vt.index]
display(vt[["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
            "cagr_sacrifice_pp", "passes_v2", "failed", "role"]])
'''))

cells.append(code('''import plotly.graph_objects as go

def frontier_chart(y_col, y_title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=envelope["cycle_vol"], y=envelope[y_col], mode="lines+markers", name="Non-dominated envelope",
        line=dict(color="steelblue"), text=[f"drop {int(n)}" for n in envelope["drop_n"]],
    ))
    if len(dominated):
        fig.add_trace(go.Scatter(
            x=frontier.loc[dominated, "cycle_vol"], y=frontier.loc[dominated, y_col], mode="markers",
            name="Dominated (excluded)", marker=dict(color="lightgray", symbol="x"),
        ))
    fig.add_trace(go.Scatter(
        x=[anchor_panel["cycle_vol"]], y=[anchor_panel[y_col]], mode="markers", name="Anchor",
        marker=dict(color="black", size=12, symbol="star"),
    ))
    fig.add_trace(go.Scatter(
        x=cash_df["cycle_vol"], y=cash_df[y_col], mode="markers+text", name="Cash overlay (excluded)",
        marker=dict(color="orange", size=10), text=cash_df.index, textposition="top center",
    ))
    fig.update_layout(title=f"{y_title} against cycle volatility", xaxis_title="cycle_vol", yaxis_title=y_col)
    return fig

frontier_chart("cycle_sharpe", "Cycle Sharpe").show()
frontier_chart("cagr", "CAGR").show()
'''))

cells.append(md("""# Equity curves

`build_placebo_frontier()` retains cycle returns and the summary panel but not the full equity
curve, so drop 30 and drop 50 are re-run once each for this chart - cheap (about 15 seconds per
variant on this window, per the plan's rule 9) and the only way to plot the curve itself.
"""))
cells.append(code('''_, equity_drop30, _ = run_variant("vol_matched_drop_30_chart", vol_matched_drop_count=30)
_, equity_drop50, _ = run_variant("vol_matched_drop_50_chart", vol_matched_drop_count=50)

fig = go.Figure()
for label, eq in (("anchor", anchor_equity), ("vol_matched_drop_30", equity_drop30), ("vol_matched_drop_50", equity_drop50)):
    fig.add_trace(go.Scatter(x=eq.index, y=eq.values, mode="lines", name=label))
fig.update_layout(title="Equity curves: anchor vs vol_matched_drop_30 vs vol_matched_drop_50", yaxis_type="log")
fig.show()
'''))

write_notebook(cells, TRACK_DIR / "15-backtest-placebo-frontier.ipynb")
