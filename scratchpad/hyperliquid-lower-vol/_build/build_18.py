import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE, \
    CELL14_REPLACEMENTS_EVIDENCE

HARNESS_EVIDENCE = (Path(__file__).parent / "harness_evidence.py").read_text()

HEADING = """# NB18 - backtest: core and satellite sleeves

If a single score cannot land the trade-off (NB16: REJECT, comprehensively), can an explicit
split? The core sleeve is ranked and sized by `sortino_shrunk_score`; the satellite is the
incumbent selection and sizing; `core_fraction` is the dial. This is also the notebook that
produces the CAGR-against-Sharpe curve the operator asked for, whether or not any point on it
passes rule v2.

**Every row in this notebook is `diagnostic_only = True` unconditionally**: `sortino_shrunk_score`
is being tried here as a bounded sleeve regardless of its NB16 whole-book result - a valid, separate
experiment - so no row here may be reported as ADOPT-eligible from this notebook's own evidence
alone. NB19's close-out re-examines the centre point as a fully independent candidate with its own
plateau and leave-one-vault-out before any ADOPT claim.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) / [16-backtest-evidence-selection.ipynb](16-backtest-evidence-selection.ipynb),
full window (2026-01-01 to 2026-09-08). Part of
[14-evidence-weighted-plan.md](14-evidence-weighted-plan.md).

## What this notebook does

The dial curve varies only `core_fraction` at a fixed `core_assets = 4`: 0.0 (anchor), 0.5, 0.7
(centre), 0.85, 1.0. `core_assets` moved one step either way (3, 5) at `core_fraction = 0.7` is the
plateau check. `core_fraction=1.0, core_assets=6` (no satellite at all) is run once, separately,
and reported alongside the curve rather than as its endpoint - a different structural point
(`satellite_assets = 0`), not part of the fixed-`core_assets=4` curve.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "18-backtest-core-satellite",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_EVIDENCE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_EVIDENCE)
cells.append(md("# Backtest\n\n- Shared harness (anchor), then the evidence-track additions, then the placebo frontier.\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells += integrity_and_audit_cells()

cells.append(md("# Placebo frontier\n\nRebuilt fresh in this notebook (own snapshot).\n"))
cells.append(code('''anchor_cycle_returns, _ = cycle_returns(anchor_equity)
frontier, cyc_returns_by_label = build_placebo_frontier(anchor_cycle_returns)
display(frontier[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer"]])
'''))

cells.append(md("""# Runs

`core_fraction=0.0` is not a real parameter value (`core_fraction=None` is the anchor's own
default and behaviour); it is recorded as a labelled alias of the anchor run so the curve has a
proper zero point.
"""))
cells.append(code('''runs = [("anchor", anchor_state, anchor_equity, anchor_returns, anchor_panel)]
run_by_label = {"anchor": runs[0]}
run_sleeve_log = {}   # label -> {timestamp: {core_ids, satellite_ids, core_fraction_target/realised}}

def run_and_record(label, **overrides):
    SLEEVE_LOG.clear()
    s, e, r = run_variant(label, **overrides)
    p = panel(label, s, e, r, anchor_cycle_returns)
    entry = (label, s, e, r, p)
    runs.append(entry)
    run_by_label[label] = entry
    run_sleeve_log[label] = dict(SLEEVE_LOG)   # snapshot before the next run clears it
    return s, e, r, p


common = dict(inverse_vol_min_periods=45, core_score_indicator="sortino_shrunk_score")

# The dial curve: core_assets fixed at 4, core_fraction swept including both endpoints.
CURVE_FRACTIONS = (0.0, 0.5, 0.7, 0.85, 1.0)
CURVE_LABELS = {}
for fraction in CURVE_FRACTIONS:
    if fraction == 0.0:
        CURVE_LABELS[fraction] = "anchor"
        continue
    label = f"core_{fraction}_n4"
    run_and_record(label, core_fraction=fraction, core_assets=4, **common)
    CURVE_LABELS[fraction] = label

# Plateau around the centre (0.7, 4): core_assets moved one step either way.
run_and_record("core_0.7_n3", core_fraction=0.7, core_assets=3, **common)
run_and_record("core_0.7_n5", core_fraction=0.7, core_assets=5, **common)

# Separate structural point: no satellite at all. Not part of the core_assets=4 curve.
run_and_record("core_1.0_n6_no_satellite", core_fraction=1.0, core_assets=6, **common)

print(f"{len(runs) - 1} variant runs completed.")
'''))

cells.append(md("""# Verdict table

Every row `diagnostic_only = True` per the heading.
"""))
cells.append(code('''vt = verdict_table([p for _l, _s, _e, _r, p in runs], anchor_panel, frontier)
vt["diagnostic_only"] = True
display(vt[["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
            "placebo_ref", "cagr_sacrifice_pp", "late_cagr", "passes_v2", "failed", "late_ok"]])
'''))

cells.append(md("""# The dial curve

`core_fraction` against CAGR and cycle Sharpe, `core_assets` fixed at 4.
`core_1.0_n6_no_satellite` is plotted separately, explicitly not on the line.
"""))
cells.append(code('''curve_df = vt.loc[[CURVE_LABELS[f] for f in CURVE_FRACTIONS]].copy()
curve_df["core_fraction"] = list(CURVE_FRACTIONS)
display(curve_df[["core_fraction", "cagr", "cycle_sharpe", "cagr_sacrifice_pp", "passes_v2"]])

import plotly.graph_objects as go
fig = go.Figure()
fig.add_trace(go.Scatter(x=curve_df["core_fraction"], y=curve_df["cagr"], name="CAGR", mode="lines+markers", yaxis="y1"))
fig.add_trace(go.Scatter(x=curve_df["core_fraction"], y=curve_df["cycle_sharpe"], name="Cycle Sharpe", mode="lines+markers", yaxis="y2"))
fig.add_trace(go.Scatter(
    x=[1.0], y=[vt.loc["core_1.0_n6_no_satellite", "cagr"]], name="core_1.0_n6 (no satellite, off-curve)",
    mode="markers", marker=dict(symbol="x", size=14, color="red"), yaxis="y1",
))
fig.update_layout(
    title="CAGR and cycle Sharpe against core_fraction (core_assets=4)",
    xaxis_title="core_fraction",
    yaxis=dict(title="CAGR", side="left"),
    yaxis2=dict(title="Cycle Sharpe", side="right", overlaying="y"),
)
fig.show()
'''))

cells.append(md("""# Plateau, leave-one-vault-out and frontier overlay
"""))
cells.append(code('''plateau_labels = ["core_0.7_n4", "core_0.5_n4", "core_0.85_n4", "core_0.7_n3", "core_0.7_n5"]
plateau_holds = bool(vt.loc[plateau_labels, "passes_v2"].all())
print(f"Plateau around core_0.7_n4 holds = {plateau_holds} (informational: every row is diagnostic_only)")
display(vt.loc[plateau_labels, ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "passes_v2", "failed"]])

centre_state = run_by_label["core_0.7_n4"][1]
top_vault = largest_contributing_vault(centre_state)
s, e, r, p = run_and_record("core_0.7_n4__without_top_vault", core_fraction=0.7, core_assets=4, masked={top_vault}, **common)
lovo_ok = bool(passes_constraints_v2(p, anchor_panel, frontier))
print(f"Leave-one-vault-out (excluding {top_vault}) passes v2 = {lovo_ok}")
display(p.to_frame().T)
'''))

cells.append(code('''fig = px.scatter(
    vt.reset_index(), x="cycle_vol", y="cycle_sharpe", hover_name="label",
    title="NB18 core/satellite variants against the placebo frontier",
)
fig.add_trace(px.line(frontier.sort_values("cycle_vol"), x="cycle_vol", y="cycle_sharpe").data[0])
fig.show()
'''))

cells.append(md("""# Hidden-cohort reach, every grid point
"""))
cells.append(code('''reach_rows = {"anchor": hidden_cohort_reach(anchor_state)}
for label, state_, *_ in [(l, s) for l, s, e, r, p in runs if l != "anchor"]:
    reach_rows[label] = hidden_cohort_reach(state_)
display(pd.DataFrame(reach_rows).T)
'''))

cells.append(md("""# Per-sleeve attribution for the centre point

Read from `SLEEVE_LOG` (this track's own per-cycle record - not `state.visualisation.calculations`,
which the trade-executor framework also writes to later in the same cycle and overwrites rather
than merges, silently erasing this data; found by direct inspection and fixed in
`_build/blocks_evidence.py`) - `core_ids`, `satellite_ids` and `core_fraction_realised` per cycle,
captured AFTER `alpha_model.normalise_weights()` runs, so `core_fraction_realised` is the actual
post-concentration-cap, post-pool-cap weight the core sleeve held, not the pre-normalisation
`core_fraction` target.
"""))
cells.append(code('''centre_state = run_by_label["core_0.7_n4"][1]
calc_by_ts = run_sleeve_log["core_0.7_n4"]
realised = pd.Series({ts: c["core_fraction_realised"] for ts, c in calc_by_ts.items()}).sort_index()

fig = go.Figure()
fig.add_trace(go.Scatter(x=realised.index, y=realised.values, name="core_fraction_realised", mode="lines"))
fig.add_hline(y=0.7, line_dash="dash", annotation_text="core_fraction target = 0.7")
fig.update_layout(title="core_0.7_n4: realised vs target core sleeve weight over time", yaxis_title="core sleeve weight")
fig.show()
print(f"Mean realised core weight: {realised.mean():.3f} (target 0.700)")

# Per-sleeve P&L and entry evidence score, from the position records directly.
all_core_ids = set()
for c in calc_by_ts.values():
    all_core_ids.update(c.get("core_ids", []))

sleeve_rows = []
for position in centre_state.portfolio.get_all_positions():
    if position.is_credit_supply():
        continue
    sleeve = "core" if position.pair.internal_id in all_core_ids else "satellite"
    buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
    entry_at = pd.Timestamp(min(t.executed_at for t in buys)) if buys else None
    score_at_entry = float("nan")
    if entry_at is not None:
        series = indicator_data.get_indicator_series("sortino_shrunk_score", pair=position.pair, unlimited=True)
        idx = series.index[series.index <= entry_at - Parameters.candle_time_bucket.to_timedelta()]
        if len(idx):
            score_at_entry = float(series.loc[idx[-1]])
    sleeve_rows.append({
        "sleeve": sleeve, "vault": position.pair.base.token_symbol,
        "pnl_usd": float(position.get_total_profit_usd() or 0.0), "score_at_entry": score_at_entry,
    })
sleeve_df = pd.DataFrame(sleeve_rows)
display(sleeve_df.groupby("sleeve").agg(
    positions=("vault", "count"), total_pnl_usd=("pnl_usd", "sum"), mean_score_at_entry=("score_at_entry", "mean"),
))
'''))

write_notebook(cells, TRACK_DIR / "18-backtest-core-satellite.ipynb")
