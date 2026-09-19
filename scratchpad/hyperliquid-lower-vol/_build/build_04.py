import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB04 - structural: portfolio volatility target with cash as a position

Selection untouched. Scales `allocation_pct` each cycle by `min(1, target_vol / ex_ante_vol)`,
where ex-ante vol is a conservative (perfectly-correlated) sum of the selected basket's per-vault
daily sigma weighted by sizing weight. The unused fraction of capital sits in cash rather than
being redistributed among the selected vaults.

**Based on:** [03a-research-data-quality-and-power.ipynb](03a-research-data-quality-and-power.ipynb).
Development window (2026-01-01 to 2026-06-30); hold-out reserved.

## Why this lever first

`allocation_pct = 0.98` forces near-full deployment every cycle. When the 33% concentration cap
binds on the best vault, the overflow has nowhere to go except the next-ranked names - which,
per NB03a, become the BTC-beta pumpers once the hold-out window starts. A volatility target is the
one lever that removes capital from the basket into cash entirely, rather than reshuffling it
between vaults, so it is tried before any change to the ranking itself.

## Adoption rule (from 03-smoothing-experiment-plan.md)

A target passes if, on the development window: CAGR >= 30%, daily volatility no worse than the
anchor's, ulcer index lower than the anchor's, absolute invested-basket BTC beta lower than the
anchor's, and time in market >= 45%. Among passing targets the winner is the one with the highest
Martin ratio (CAGR / ulcer). The winner is then re-run with the largest-contributing vault excluded
from the start (leave-one-vault-out), and its edge over the anchor must survive that.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("04-backtest-vol-target")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness: run the anchor, then the vol-target sweep.\n"))
cells.append(harness_cell())
cells += integrity_and_audit_cells()

cells.append(md("""# Volatility-target sweep

Target annualised portfolio volatility at 10%, 12.5%, 15% (about the anchor's own 15.5%), 17.5%
and 20%.
"""))
cells.append(code("""anchor_cycle_returns, _ = cycle_returns(anchor_equity)
rows = [anchor_panel]
for target in (0.10, 0.125, 0.15, 0.175, 0.20):
    s, e, r = run_variant(f"target_vol_{target}", target_portfolio_vol=target)
    rows.append(panel(f"target_vol_{target}", s, e, r, anchor_cycle_returns))

sweep_df = pd.DataFrame(rows).set_index("label")
sweep_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in sweep_df.iterrows()
]
display(sweep_df)
"""))

cells.append(md("## Winner and leave-one-vault-out\n"))
cells.append(code("""passing = sweep_df[(sweep_df["passes"]) & (sweep_df.index != "anchor")]
if len(passing):
    winner_label = passing["martin"].idxmax()
    winner_target = float(winner_label.replace("target_vol_", ""))
    print(f"Winner: {winner_label} (Martin {passing.loc[winner_label, 'martin']:.3f} vs anchor {anchor_panel['martin']:.3f})")

    worst_vault = largest_contributing_vault(anchor_state)
    s, e, r = run_variant(f"{winner_label}_without_top_vault", target_portfolio_vol=winner_target, masked={worst_vault})
    lovo_panel = panel(f"{winner_label}_without_top_vault", s, e, r, anchor_cycle_returns)
    lovo_df = pd.DataFrame([sweep_df.loc[winner_label], lovo_panel]).drop(columns=["passes"], errors="ignore")
    display(lovo_df)
    lovo_survives = bool(lovo_panel["passes"] if "passes" in lovo_panel else passes_constraints(lovo_panel, anchor_panel))
    print(f"Leave-one-vault-out (excluding {worst_vault}): still passes constraints = {passes_constraints(lovo_panel, anchor_panel)}")
else:
    winner_label = None
    print("No target_portfolio_vol value satisfies the adoption constraints on the development window.")
"""))

write_notebook(cells, TRACK_DIR / "04-backtest-vol-target.ipynb")
