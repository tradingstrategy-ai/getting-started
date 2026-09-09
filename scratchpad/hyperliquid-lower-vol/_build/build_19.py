import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE, \
    CELL14_REPLACEMENTS_EVIDENCE

HARNESS_EVIDENCE = (Path(__file__).parent / "harness_evidence.py").read_text()

HEADING = """# NB19 - close-out

The plan's overall verdict, re-run from a single fresh snapshot rather than assembled from three
separate notebooks' own downloads. Every distinct mechanism tried across NB16 (selection), NB17
(sizing) and NB18 (core/satellite) is re-run here - the complete pre-registered family, not only
the centre points - so the family-wise reality check in this notebook is valid.

**Based on:** [16-backtest-evidence-selection.ipynb](16-backtest-evidence-selection.ipynb),
[17-backtest-evidence-sizing.ipynb](17-backtest-evidence-sizing.ipynb),
[18-backtest-core-satellite.ipynb](18-backtest-core-satellite.ipynb). Part of
[14-evidence-weighted-plan.md](14-evidence-weighted-plan.md).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "19-backtest-closeout",
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

cells.append(md("""# The complete pre-registered family

Every distinct override combination tried in NB16, NB17 and NB18, regenerated here rather than
copied by hand, so nothing is silently dropped from the multiplicity check below.
"""))
cells.append(code('''runs = [("anchor", anchor_state, anchor_equity, anchor_returns, anchor_panel)]
run_by_label = {"anchor": runs[0]}
run_family = {}   # label -> "NB16" | "NB17" | "NB18"

def run_and_record(label, family, **overrides):
    SLEEVE_LOG.clear()
    s, e, r = run_variant(label, **overrides)
    p = panel(label, s, e, r, anchor_cycle_returns)
    entry = (label, s, e, r, p)
    runs.append(entry)
    run_by_label[label] = entry
    run_family[label] = family
    return s, e, r, p


# --- NB16: selection (3 scores x 9 runs each = 27, plus 2 cagr_weight duplicates already implied) ---
NB16_SCORES = {
    "sortino_shrunk": dict(selection_score_indicator="sortino_shrunk_score"),
    "evidence_composite_06": dict(selection_score_indicator="evidence_composite", cagr_weight=0.6),
    "evidence_composite_03": dict(selection_score_indicator="evidence_composite", cagr_weight=0.3),
}
for score_name, score_overrides in NB16_SCORES.items():
    common = dict(require_scored_candidates=True, inverse_vol_min_periods=45, **score_overrides)
    prefix = score_name
    run_and_record(f"{prefix}__centre", "NB16", **common)
    neighbours = [
        ("t_cap_2", dict(evidence_t_cap=2.0)), ("t_cap_4", dict(evidence_t_cap=4.0)),
        ("prior_30", dict(evidence_prior_strength=30)), ("prior_90", dict(evidence_prior_strength=90)),
        ("min_events_10", dict(evidence_min_events=10)), ("min_events_30", dict(evidence_min_events=30)),
    ]
    if "cagr_weight" in score_overrides:
        alt_weight = 0.3 if score_overrides["cagr_weight"] == 0.6 else 0.6
        neighbours.append(("cagr_weight_alt", dict(cagr_weight=alt_weight)))
    for label, override in neighbours:
        run_and_record(f"{prefix}__{label}", "NB16", **{**common, **override})
    run_and_record(f"{prefix}__no_shrink", "NB16", **{**common, "evidence_prior_strength": 1})
    run_and_record(f"{prefix}__no_early_vol", "NB16", **{**common, "inverse_vol_min_periods": 90})

# --- NB17: sizing (anchor's incumbent selection throughout, since NB16 had no ADOPT) ---
for method in ("evidence", "blend", "equal"):
    run_and_record(f"sizing_{method}", "NB17", weighting_method=method)
for floor in (0.0, 0.5):
    run_and_record(f"sizing_evidence_floor_{floor}", "NB17", weighting_method="evidence", weight_floor_fraction=floor)

# --- NB18: core/satellite ---
nb18_common = dict(inverse_vol_min_periods=45, core_score_indicator="sortino_shrunk_score")
for fraction in (0.5, 0.7, 0.85, 1.0):
    run_and_record(f"core_{fraction}_n4", "NB18", core_fraction=fraction, core_assets=4, **nb18_common)
run_and_record("core_0.7_n3", "NB18", core_fraction=0.7, core_assets=3, **nb18_common)
run_and_record("core_0.7_n5", "NB18", core_fraction=0.7, core_assets=5, **nb18_common)
run_and_record("core_1.0_n6_no_satellite", "NB18", core_fraction=1.0, core_assets=6, **nb18_common)

print(f"{len(runs) - 1} variant runs completed across the full family "
      f"({sum(1 for v in run_family.values() if v=='NB16')} NB16, "
      f"{sum(1 for v in run_family.values() if v=='NB17')} NB17, "
      f"{sum(1 for v in run_family.values() if v=='NB18')} NB18).")
'''))

cells.append(md("""# Combined verdict table
"""))
cells.append(code('''vt = verdict_table([p for _l, _s, _e, _r, p in runs], anchor_panel, frontier)
vt["family"] = [run_family.get(l, "-") for l in vt.index]
vt["cagr_sacrifice_pp"] = vt["cagr_sacrifice_pp"]
display(vt[["family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta",
            "mean_invested", "cagr_sacrifice_pp", "passes_v2", "failed", "late_ok"]])

any_pass = vt[vt.index != "anchor"]["passes_v2"]
print(f"\\nAny non-anchor run passes v2: {bool(any_pass.any())}")
if any_pass.any():
    print("Passing runs:", list(vt.index[(vt.index != 'anchor') & vt['passes_v2']]))
'''))

cells.append(md("""# Frontier overlay: every run in the plan
"""))
cells.append(code('''fig = px.scatter(
    vt.reset_index(), x="cycle_vol", y="cycle_sharpe", color="family", hover_name="label",
    title="Every backtest run across NB16, NB17 and NB18 against the placebo frontier",
)
fig.add_trace(px.line(frontier.sort_values("cycle_vol"), x="cycle_vol", y="cycle_sharpe").data[0])
fig.show()
'''))

cells.append(md("""# Family-wise reality check

Block-bootstraps the anchor's own cycle returns to build a null distribution for "how much can
the BEST of this many candidates improve on the anchor's Sharpe by chance alone", matched to the
actual size of the family tried above - not just any single candidate's own significance.
"""))
cells.append(code('''candidate_cycle_returns = {}
for label, s, e, r, p in runs:
    if label == "anchor":
        continue
    cr, ppy = cycle_returns(e)
    candidate_cycle_returns[label] = cr

_, periods_per_year = cycle_returns(anchor_equity)
reality_check = family_wise_reality_check(candidate_cycle_returns, anchor_cycle_returns, periods_per_year)
display(reality_check)
print("\\nA family-wise p-value is not itself a pass/fail gate here - it exists to prevent")
print("overclaiming when nothing individually adopted, and to flag if the family-wise best result")
print("still looks unremarkable against chance even when it happens to be the plan's best number.")
'''))

cells.append(md("""# Equity curves: anchor against the best point of each family
"""))
cells.append(code('''import plotly.graph_objects as go

best_by_family = {}
for family in ("NB16", "NB17", "NB18"):
    sub = vt[vt["family"] == family]
    if len(sub):
        best_by_family[family] = sub["cycle_sharpe"].idxmax()

fig = go.Figure()
fig.add_trace(go.Scatter(x=anchor_equity.index, y=anchor_equity.values, name="anchor", mode="lines"))
for family, label in best_by_family.items():
    eq = run_by_label[label][2]
    fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=f"{family} best: {label}", mode="lines"))
for label, x in (("regime break", "2026-04-01"), ("late period start", "2026-07-01")):
    # add_vline() on a datetime x-axis hits a plotly/pandas incompatibility (its internal
    # annotation-position averaging does integer arithmetic on Timestamps, which current pandas
    # rejects). add_shape() with an explicit x0/x1 is the equivalent, lower-level call that avoids it.
    fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, xref="x", yref="paper", line=dict(dash="dot", color="grey"))
    fig.add_annotation(x=x, y=1, yref="paper", text=label, showarrow=False, yanchor="bottom")
fig.update_layout(title="Anchor against the best-Sharpe point of each family", yaxis_type="log")
fig.show()
print(f"Best point per family: {best_by_family}")
'''))

cells.append(md("""# Prospective shadow specification

Written whether or not there is a winner, per the plan. Since nothing reached ADOPT, this
specifies what WOULD be shadow-run if this plan is extended and a future candidate clears rule v2.
"""))
cells.append(code('''print("""
No candidate in this plan reached ADOPT, so no shadow deployment is scheduled from this notebook.
If this plan is extended and a future candidate clears rule v2 (all seven constraints, plateau,
leave-one-vault-out, late period), the following protocol applies before any live-book change:

1. Freeze the exact parameter override dictionary (printed literally, as NB16_SELECTION_OVERRIDES
   was here) alongside the code commit that produced it.
2. Shadow-run the frozen candidate and an UNCHANGED anchor side by side, on identical decision
   dates, for a minimum of 45 decision cycles (90 days) before any comparison is drawn.
3. Record, for the shadow period specifically: realised deposit availability (can_deposit() at
   each attempted entry), pool-cap fills (whether USDTVLSizeRiskModel ever bound), turnover, and
   redemption fees paid - not just the resulting equity curve.
4. Apply the same rule-v2 thresholds to the shadow period's own panel. A pass at 45 cycles is
   monitoring evidence that the mechanism behaves as backtested, not a deployment proof - the
   window is short relative to this plan's own minimum-detectable-effect calculations (NB03a).
5. The comparator is the anchor's LIVE decisions on the same dates, not a re-run backtest of it -
   a live-vs-shadow comparison is the only one that is actually prospective.
""")
'''))

cells.append(md("""# Overall verdict
"""))
cells.append(code('''winner = None
for label in vt.index:
    if label == "anchor":
        continue
    if bool(vt.loc[label, "passes_v2"]) and bool(vt.loc[label, "late_ok"]):
        winner = label
        break

if winner:
    print(f"ADOPT: {winner}")
    print(f"Family-wise p-value: {reality_check.set_index('metric').loc['Family-wise p-value', 'value']:.3f}")
else:
    print("NOTHING ADOPTED.")
    print()
    print("The dial curve from NB18 is the answer to the operator's original question: this is")
    print("what CAGR buys at each core_fraction setting, and none of it clears the placebo.")
    print()
    best_overall = vt[vt.index != "anchor"].sort_values("cagr", ascending=False).iloc[0]
    print(f"Best CAGR among every candidate tried: {best_overall.name} at {best_overall['cagr']:.2%} "
          f"(anchor: {anchor_panel['cagr']:.2%}), still failing: {best_overall['failed']}")
'''))

write_notebook(cells, TRACK_DIR / "19-backtest-closeout.ipynb")
