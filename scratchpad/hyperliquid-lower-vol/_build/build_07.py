import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB07 - sizing: drawdown-based risk, one family at a time

Selection untouched, all NB04-NB06 structural parameters unchanged (all three were REJECTed on
the development window). Replaces `inverse_variance` sizing with, in turn, `inverse_ulcer`,
`inverse_downside`, and a beta-group cap layered on top of the incumbent sizing. Each risk-based
method requires `min_fresh_observations` (NB03a) fresh marks before trusting the statistic, and
floors any weight at `weight_floor_fraction` of the mean weight so a vault whose risk measure
reads as near-zero cannot swallow the basket.

**Based on:** [06-backtest-breadth-concentration.ipynb](06-backtest-breadth-concentration.ipynb)
(REJECT; anchor configuration unchanged). Development window (2026-01-01 to 2026-06-30); hold-out
reserved.

## Why sizing rather than another structural lever

NB77 (waterfall-rc) found `inverse_variance` hands the largest weights to a quiet cohort of small
losers, because it sizes by *total* volatility rather than a measure that distinguishes harmful
(downside) volatility from harmless (upside) volatility. Ulcer index and downside deviation are
both drawdown-based, so a vault that is volatile only because it goes up in jumps - the NB78
blow-up signature - is not rewarded with a larger position the way `inverse_variance` might.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("07-backtest-drawdown-sizing")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness: run the anchor, then the sizing-family sweep.\n"))
cells.append(harness_cell())
cells += integrity_and_audit_cells()

cells.append(md("""# Sizing-family sweep

`inverse_ulcer` and `inverse_downside` replace `inverse_variance`; the beta-group cap is layered
on top of the incumbent `inverse_variance` sizing rather than replacing it, since it acts on the
already-sized weights.
"""))
cells.append(code("""anchor_cycle_returns, _ = cycle_returns(anchor_equity)
rows = [anchor_panel]

s, e, r = run_variant("inverse_ulcer", weighting_method="inverse_ulcer", sizing_risk_indicator="ulcer_index_180")
rows.append(panel("inverse_ulcer", s, e, r, anchor_cycle_returns))

s, e, r = run_variant("inverse_downside", weighting_method="inverse_downside", sizing_risk_indicator="downside_deviation_90")
rows.append(panel("inverse_downside", s, e, r, anchor_cycle_returns))

# The plan's third sizing family: equal-risk-contribution weights with a residual-correlation cap.
# The first version of this notebook substituted a beta-group cap for it, which turned out to be a
# no-op; this is the family actually specified.
for corr_cap in (0.40, 0.60, 0.80):
    label = f"risk_contribution_corr_{corr_cap}"
    s, e, r = run_variant(label, weighting_method="risk_contribution", residual_correlation_cap=corr_cap)
    rows.append(panel(label, s, e, r, anchor_cycle_returns))

for group_cap in (0.25, 0.40, 0.50):
    s, e, r = run_variant(f"beta_group_cap_{group_cap}", high_beta_group_cap=group_cap)
    rows.append(panel(f"beta_group_cap_{group_cap}", s, e, r, anchor_cycle_returns))

sweep_df = pd.DataFrame(rows).set_index("label")
sweep_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in sweep_df.iterrows()
]
display(sweep_df)
"""))

cells.append(md("""## NB09 preview: does the exponent choice (NB72) carry over?

NB72 (waterfall-rc) found sizing by 1/sigma^2 beats 1/sigma under `inverse_variance`. Repeated
here for whichever of `inverse_ulcer` / `inverse_downside` passes, as a diagnostic rather than a
separate adoption decision - the plan places this check in NB07, not a new notebook.
"""))
cells.append(code("""passing = sweep_df[(sweep_df["passes"]) & (sweep_df.index != "anchor")]
if len(passing):
    winner_label = passing["martin"].idxmax()
    print(f"Winner: {winner_label} (Martin {passing.loc[winner_label, 'martin']:.3f} vs anchor {anchor_panel['martin']:.3f})")

    worst_vault = largest_contributing_vault(anchor_state)
    winner_overrides = {}
    if winner_label == "inverse_ulcer":
        winner_overrides = dict(weighting_method="inverse_ulcer", sizing_risk_indicator="ulcer_index_180")
    elif winner_label == "inverse_downside":
        winner_overrides = dict(weighting_method="inverse_downside", sizing_risk_indicator="downside_deviation_90")
    elif winner_label.startswith("beta_group_cap_"):
        winner_overrides = dict(high_beta_group_cap=float(winner_label.replace("beta_group_cap_", "")))
    elif winner_label.startswith("risk_contribution_corr_"):
        winner_overrides = dict(
            weighting_method="risk_contribution",
            residual_correlation_cap=float(winner_label.replace("risk_contribution_corr_", "")),
        )

    s, e, r = run_variant(f"{winner_label}_without_top_vault", masked={worst_vault}, **winner_overrides)
    lovo_panel = panel(f"{winner_label}_without_top_vault", s, e, r, anchor_cycle_returns)
    display(pd.DataFrame([sweep_df.loc[winner_label].drop("passes"), lovo_panel]))
    print(f"Leave-one-vault-out (excluding {worst_vault}): still passes constraints = {passes_constraints(lovo_panel, anchor_panel)}")
else:
    winner_label = None
    winner_overrides = {}
    print("No sizing family satisfies the adoption constraints on the development window.")
"""))

write_notebook(cells, TRACK_DIR / "07-backtest-drawdown-sizing.ipynb")
