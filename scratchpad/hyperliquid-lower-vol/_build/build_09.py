import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB09 - selection: consistency scores, plus the deferred NB08 diagnostic

Selection changed for the first time in this track; every structural and sizing lever in
NB04-NB07 was REJECTed and the anchor configuration is otherwise unchanged. Replaces the CAGR+Sortino
composite's second leg with `min_window_sortino` (minimum bounded Sortino across 30/90/180/360
days, strict - NaN if any window lacks history) or `positive_window_share` (share of trailing
rolling-30d returns that were positive), both of which cleared NB03b's precision-at-6 gate in both
polling regimes. Also runs, as a single diagnostic rather than a full sweep, the continuous
residual-event-concentration penalty NB08 was to have swept - `residual_event_concentration`
failed NB03b's gate as a standalone ranker, so per the plan's pre-registered rule NB08 is not
built as its own notebook; this cell exists so that finding is checked once against a working
backtest rather than only against the screen's proxy metric.

**Based on:** [07-backtest-drawdown-sizing.ipynb](07-backtest-drawdown-sizing.ipynb) (REJECT;
anchor sizing unchanged); gates from
[03b-research-feature-screen.ipynb](03b-research-feature-screen.ipynb). Development window
(2026-01-01 to 2026-06-30); hold-out reserved.

**NB10 is not built.** `residual_cagr_score` failed NB03b's gate (loses in the sparse regime,
0.066 vs the incumbent's 0.244), confirming NB47's original verdict under a Martin-ratio
objective, and the plan's pre-registered rule for NB10 is that it runs only if the feature clears
that gate.

## Design notes carried over from the plan

`require_scored_candidates` controls whether a vault missing a required window is dropped from
the candidate pool (strict, avoiding NB78's NaN-tolerant failure) or admitted at signal 0
(permissive, run as a diagnostic showing what the strict rule is protecting against).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("09-backtest-consistency-selection")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness: run the anchor, then the consistency-selection sweep.\n"))
cells.append(harness_cell())
cells += integrity_and_audit_cells()

cells.append(md("""# Consistency-selection sweep

Both features that cleared NB03b's gate, each run strict (candidates missing the required
history are dropped) and permissive (admitted at signal 0, as a diagnostic).
"""))
cells.append(code("""anchor_cycle_returns, _ = cycle_returns(anchor_equity)
rows = [anchor_panel]

s, e, r = run_variant("min_sortino_strict", selection_score_indicator="cagr_min_sortino_weight", require_scored_candidates=True)
rows.append(panel("min_sortino_strict", s, e, r, anchor_cycle_returns))

s, e, r = run_variant("min_sortino_permissive", selection_score_indicator="cagr_min_sortino_weight", require_scored_candidates=False)
rows.append(panel("min_sortino_permissive", s, e, r, anchor_cycle_returns))

s, e, r = run_variant("positive_window_strict", selection_score_indicator="cagr_positive_window_weight", require_scored_candidates=True)
rows.append(panel("positive_window_strict", s, e, r, anchor_cycle_returns))

s, e, r = run_variant("positive_window_permissive", selection_score_indicator="cagr_positive_window_weight", require_scored_candidates=False)
rows.append(panel("positive_window_permissive", s, e, r, anchor_cycle_returns))

# `downside_deviation_90` clears the precision-at-6 gate once NB03b is read at live parity; the
# original, look-ahead-contaminated screen denied it a backtest. `cagr_downside_weight` blends the
# bounded inverse-downside score into the composite in place of the Sortino leg.
s, e, r = run_variant("downside_strict", selection_score_indicator="cagr_downside_weight", require_scored_candidates=True)
rows.append(panel("downside_strict", s, e, r, anchor_cycle_returns))

sweep_df = pd.DataFrame(rows).set_index("label")
sweep_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in sweep_df.iterrows()
]
display(sweep_df)
"""))

cells.append(md("""# Pre-registered control: the vol-matched placebo

The plan requires a vol-matched placebo for **any** selection change - NB42's control, which
overturned that notebook's apparent BTC-neutrality edge by showing two thirds of it was generic
de-risking. The first version of this notebook omitted it. Every selection leg above lowers BTC
beta substantially; this asks whether simply dropping the highest-volatility candidates each cycle,
with no view on quality at all, achieves the same risk reduction. If it does, the selection legs'
beta reduction is not selection skill.
"""))
cells.append(code("""placebo_rows = [anchor_panel]
# Finer than the original three points: the first pass found drop=25 satisfying every adoption
# constraint, between a no-op at 10 and a clearly worse 50, so this resolves whether that is a
# plateau or the spike pattern NB79 warns about.
for drop in (10, 15, 20, 25, 30, 35, 50):
    label = f"vol_matched_drop_{drop}"
    s, e, r = run_variant(label, vol_matched_drop_count=drop)
    placebo_rows.append(panel(label, s, e, r, anchor_cycle_returns))

placebo_df = pd.DataFrame(placebo_rows).set_index("label")
display(placebo_df[["cagr", "ulcer", "martin", "cycle_vol", "abs_invested_beta", "mean_invested"]])

selection_betas = sweep_df.loc[
    [i for i in sweep_df.index if i != "anchor"], "abs_invested_beta"
]
print(f"Selection legs reached beta {selection_betas.min():.4f} to {selection_betas.max():.4f}")
print(f"Vol-matched placebos reached beta "
      f"{placebo_df.loc[placebo_df.index != 'anchor', 'abs_invested_beta'].min():.4f} to "
      f"{placebo_df.loc[placebo_df.index != 'anchor', 'abs_invested_beta'].max():.4f}, "
      f"against the anchor's {anchor_panel['abs_invested_beta']:.4f}")
print("If the placebo range covers the selection legs' range, their beta reduction is generic")
print("de-risking rather than selection skill (NB42's finding, re-tested here).")

placebo_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in placebo_df.iterrows()
]
passing_placebos = placebo_df.index[(placebo_df["passes"]) & (placebo_df.index != "anchor")].tolist()
print()
print(f"Placebo settings satisfying every adoption constraint: {passing_placebos or 'none'}")
if passing_placebos:
    counts = [int(l.replace("vol_matched_drop_", "")) for l in passing_placebos]
    contiguous = sorted(counts) == list(range(min(counts), max(counts) + 1, 5))
    print(f"Contiguous run across the swept grid (the NB79 plateau test): {contiguous and len(counts) >= 2}")
    print("A control that was meant to be a null is the only thing in this track to clear the bar.")
    print("Whether that is a plateau or a spike decides how much weight it can carry.")
"""))

cells.append(md("""# Deferred NB08 diagnostic: the residual-event-concentration penalty in isolation

`residual_event_concentration` failed NB03b's screen as a standalone ranker. This checks its cost
as a *penalty* on the incumbent composite instead - the use NB08 was designed for - at a single
pre-registered strength (`lambda=0.5`) rather than the full sweep NB08 would have run, since the
screen already gives a strong prior that this will not help.
"""))
cells.append(code("""s, e, r = run_variant("event_concentration_penalty_0.5", event_concentration_lambda=0.5)
diagnostic_panel = panel("event_concentration_penalty_0.5", s, e, r, anchor_cycle_returns)
display(pd.DataFrame([anchor_panel, diagnostic_panel]))
print(f"Passes constraints: {passes_constraints(diagnostic_panel, anchor_panel)}")
"""))

cells.append(md("## Winner and leave-one-vault-out\n"))
cells.append(code("""passing = sweep_df[(sweep_df["passes"]) & (sweep_df.index != "anchor")]
if len(passing):
    winner_label = passing["martin"].idxmax()
    if "min_sortino" in winner_label:
        score_indicator = "cagr_min_sortino_weight"
    elif "positive_window" in winner_label:
        score_indicator = "cagr_positive_window_weight"
    else:
        score_indicator = "cagr_downside_weight"
    winner_overrides = dict(
        selection_score_indicator=score_indicator,
        require_scored_candidates="strict" in winner_label,
    )
    print(f"Winner: {winner_label} (Martin {passing.loc[winner_label, 'martin']:.3f} vs anchor {anchor_panel['martin']:.3f})")

    worst_vault = largest_contributing_vault(anchor_state)
    s, e, r = run_variant(f"{winner_label}_without_top_vault", masked={worst_vault}, **winner_overrides)
    lovo_panel = panel(f"{winner_label}_without_top_vault", s, e, r, anchor_cycle_returns)
    display(pd.DataFrame([sweep_df.loc[winner_label].drop("passes"), lovo_panel]))
    print(f"Leave-one-vault-out (excluding {worst_vault}): still passes constraints = {passes_constraints(lovo_panel, anchor_panel)}")
else:
    winner_label = None
    winner_overrides = {}
    print("No consistency-selection variant satisfies the adoption constraints on the development window.")
"""))

write_notebook(cells, TRACK_DIR / "09-backtest-consistency-selection.ipynb")
