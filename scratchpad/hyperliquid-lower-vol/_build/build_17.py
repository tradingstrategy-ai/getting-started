import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE, \
    CELL14_REPLACEMENTS_EVIDENCE

HARNESS_EVIDENCE = (Path(__file__).parent / "harness_evidence.py").read_text()

HEADING = """# NB17 - backtest: evidence-weighted sizing

Holding selection fixed, does sizing by evidence of profit (`sortino_shrunk_score`) rather than by
inverse variance improve Sharpe? NB77 found inverse variance hands the biggest slots to a quiet
cohort of small losers; `inverse_ulcer` and `inverse_downside` (NB07, in the earlier
`03-smoothing-experiment-plan.md` track) made that worse. This is the first sizing rule in this
track that can give a quiet *loser* nothing.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) / [16-backtest-evidence-selection.ipynb](16-backtest-evidence-selection.ipynb),
full window (2026-01-01 to 2026-09-08). Part of
[14-evidence-weighted-plan.md](14-evidence-weighted-plan.md).

## What this notebook does

`SELECTION = NB16_SELECTION_OVERRIDES` - copied verbatim from NB16's printed output. NB16 found no
ADOPT, so `SELECTION = {}`: every run below uses the anchor's incumbent selection
(`cagr_sortino_weight`), varying only `weighting_method`. `evidence` sizing is the mechanism under
test; `equal` is the sizing null (if evidence sizing does not beat equal weight, it is not doing
anything); `blend` (inverse-vol times composite) is the existing method closest in spirit. The
centre point is `evidence` with the default `weight_floor_fraction=0.25`; its neighbours are the
floor at 0.0 and 0.5. Every run here is `diagnostic_only = True` since `SELECTION == {}` means the
selection this sizing is layered on was never itself adopted - `sizing_evidence` is judged on
sizing mechanics alone, not eligible for a whole-book ADOPT from this notebook.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "17-backtest-evidence-sizing",
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

cells.append(md("""# Selection to hold fixed

Copied verbatim from [16-backtest-evidence-selection.ipynb](16-backtest-evidence-selection.ipynb)'s
printed `NB16_SELECTION_OVERRIDES` output.
"""))
cells.append(code('''SELECTION = {}   # NB16_WINNER was None; anchor's incumbent selection throughout
DIAGNOSTIC_ONLY = (SELECTION == {})
print(f"SELECTION = {SELECTION}")
print(f"DIAGNOSTIC_ONLY = {DIAGNOSTIC_ONLY}")
'''))

cells.append(md("""# Runs
"""))
cells.append(code('''runs = [("anchor", anchor_state, anchor_equity, anchor_returns, anchor_panel)]
run_by_label = {"anchor": runs[0]}

def run_and_record(label, **overrides):
    s, e, r = run_variant(label, **overrides)
    p = panel(label, s, e, r, anchor_cycle_returns)
    entry = (label, s, e, r, p)
    runs.append(entry)
    run_by_label[label] = entry
    return s, e, r, p


for method in ("evidence", "blend", "equal"):
    run_and_record(f"sizing_{method}", weighting_method=method, **SELECTION)

# Plateau on the floor, for the evidence method only.
for floor in (0.0, 0.5):
    run_and_record(f"sizing_evidence_floor_{floor}", weighting_method="evidence", weight_floor_fraction=floor, **SELECTION)

print(f"{len(runs) - 1} variant runs completed.")
'''))

cells.append(md("""# Verdict table
"""))
cells.append(code('''vt = verdict_table([p for _l, _s, _e, _r, p in runs], anchor_panel, frontier)
vt["diagnostic_only"] = DIAGNOSTIC_ONLY
display(vt[["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
            "placebo_ref", "cagr_sacrifice_pp", "late_cagr", "passes_v2", "diagnostic_only",
            "failed", "late_ok"]])
'''))

cells.append(md("""# Mean realised weight of the largest position per cycle, by method

Evidence sizing is expected to concentrate more than inverse variance; the 33% concentration cap
should be visibly binding if it does.
"""))
cells.append(code('''from collections import defaultdict

def largest_position_weights(state_) -> list:
    """Largest single position's share of total equity, at every cycle it was revalued.

    `state.stats.positions[pid]` is a list of `PositionStatistics` (`.calculated_at`, `.value`)
    per position; `state.stats.portfolio` carries `.total_equity` at the same timestamps. Grouped
    by timestamp rather than assumed aligned by list position, since closed positions stop
    contributing rows.
    """
    equity_by_ts = {s.calculated_at: s.total_equity for s in state_.stats.portfolio if s.total_equity}
    values_by_ts = defaultdict(list)
    for stat_list in state_.stats.positions.values():
        for ps in stat_list:
            values_by_ts[ps.calculated_at].append(ps.value)
    weights = []
    for ts, equity in equity_by_ts.items():
        values = values_by_ts.get(ts)
        if values:
            weights.append(max(values) / equity)
    return weights


concentration_rows = []
for label, state_, _e, _r, _p in runs:
    weights_by_cycle = largest_position_weights(state_)
    concentration_rows.append({
        "label": label,
        "mean_largest_position_weight": float(np.mean(weights_by_cycle)) if weights_by_cycle else float("nan"),
        "max_largest_position_weight": float(np.max(weights_by_cycle)) if weights_by_cycle else float("nan"),
    })
concentration_df = pd.DataFrame(concentration_rows).set_index("label")
display(concentration_df)
print(f"Concentration cap: {Parameters.max_concentration_pct:.0%}")
'''))

cells.append(md("""# Leave-one-vault-out and bootstrap, if the centre passes v2 and the plateau holds
"""))
cells.append(code('''centre_label = "sizing_evidence"
plateau_labels = ["sizing_evidence", "sizing_evidence_floor_0.0", "sizing_evidence_floor_0.5"]

if DIAGNOSTIC_ONLY:
    print(f"{centre_label}: skipped (diagnostic_only - SELECTION was not itself adopted in NB16)")
elif not bool(vt.loc[centre_label, "passes_v2"]):
    print(f"{centre_label}: skipped (centre fails v2: {vt.loc[centre_label, 'failed']})")
elif not bool(vt.loc[plateau_labels, "passes_v2"].all()):
    print(f"{centre_label}: skipped (plateau does not hold)")
else:
    centre_state = run_by_label[centre_label][1]
    top_vault = largest_contributing_vault(centre_state)
    s, e, r, p = run_and_record(f"{centre_label}__without_top_vault", weighting_method="evidence", masked={top_vault}, **SELECTION)
    lovo_ok = bool(passes_constraints_v2(p, anchor_panel, frontier))
    print(f"Leave-one-vault-out (excluding {top_vault}) passes v2 = {lovo_ok}")
    display(p.to_frame().T)

    nearest = nearest_placebo_label(frontier, float(vt.loc[centre_label, "cycle_vol"]))
    candidate_r, periods_per_year = cycle_returns(run_by_label[centre_label][2])
    lo, hi = bootstrap_sharpe_diff_vs_control(candidate_r, cyc_returns_by_label[nearest], periods_per_year)
    print(f"Sharpe advantage over nearest placebo ({nearest}), 95% CI: [{lo:.3f}, {hi:.3f}]")
'''))

cells.append(md("""# Frontier overlay
"""))
cells.append(code('''fig = px.scatter(
    vt.reset_index(), x="cycle_vol", y="cycle_sharpe", hover_name="label",
    title="NB17 sizing variants against the placebo frontier",
)
fig.add_trace(px.line(frontier.sort_values("cycle_vol"), x="cycle_vol", y="cycle_sharpe").data[0])
fig.show()
'''))

cells.append(md("""# Verdict

If `sizing_evidence` fails but `sizing_equal` passes, that is a finding about inverse variance,
not about evidence sizing.
"""))
cells.append(code('''equal_passes = bool(vt.loc["sizing_equal", "passes_v2"])
evidence_passes = bool(vt.loc["sizing_evidence", "passes_v2"])
print(f"sizing_equal passes v2 = {equal_passes}")
print(f"sizing_evidence passes v2 = {evidence_passes}")
if not evidence_passes and equal_passes:
    print("Finding is about inverse variance specifically, not about evidence sizing.")
'''))

write_notebook(cells, TRACK_DIR / "17-backtest-evidence-sizing.ipynb")
