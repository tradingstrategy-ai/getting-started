import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB06 - structural: breadth, then concentration

Selection untouched, capacity cap unchanged at the baseline 33% (NB05 found every tighter cap
made both return and smoothness worse on the development window, so there is no revised cap to
carry forward). Two sequential sweeps: `max_assets_in_portfolio` at 6, 8, 10 with concentration
held at 33%, then `max_concentration_pct` at 20%, 25%, 33% at whichever breadth wins step 1.

**Based on:** [05-backtest-pool-cap.ipynb](05-backtest-pool-cap.ipynb) (REJECT; 33% cap unchanged).
Development window (2026-01-01 to 2026-06-30); hold-out reserved.

## Why breadth might help here

NB68 (waterfall-rc) found 6 best on CAGR and 8 best on Sharpe/Calmar/drawdown at this bankroll,
with a reproducible hole at 7 - the axis is not monotone. A wider basket dilutes single-vault risk
mechanically (a 4th, 5th and 6th name below the current 6 spreads the same capital thinner), which
is a candidate lever for Goal 2 that does not depend on getting the ranking right.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("06-backtest-breadth-concentration")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness: run the anchor, then breadth, then concentration.\n"))
cells.append(harness_cell())
cells += integrity_and_audit_cells()

cells.append(md("""# Step 1: breadth

`max_assets_in_portfolio` at 6 (anchor), 8, 10, with `max_concentration_pct` held at the baseline
33%. NB68 found a reproducible hole at 7, so this checks for a plateau rather than trusting a
single point.
"""))
cells.append(code("""step1_rows = [anchor_panel]
for n in (8, 10):
    s, e, r = run_variant(f"assets_{n}", max_assets_in_portfolio=n)
    step1_rows.append(panel(f"assets_{n}", s, e, r, daily(anchor_returns)))

step1_df = pd.DataFrame(step1_rows).set_index("label")
step1_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in step1_df.iterrows()
]
display(step1_df)

step1_passing = step1_df[(step1_df["passes"]) & (step1_df.index != "anchor")]
best_n = int(step1_passing["martin"].idxmax().replace("assets_", "")) if len(step1_passing) else 6
print(f"Breadth carried into step 2: max_assets_in_portfolio = {best_n}"
      + ("" if len(step1_passing) else " (no breadth passed; keeping the anchor's 6)"))
"""))

cells.append(md("""# Step 2: concentration

`max_concentration_pct` at 20%, 25%, 33%, at the breadth chosen in step 1.
"""))
cells.append(code("""step2_rows = []
concentrations = (0.20, 0.25, 0.33)
for conc in concentrations:
    label = f"assets_{best_n}_conc_{conc}"
    if best_n == 6 and conc == 0.33:
        duplicate = anchor_panel.copy()
        duplicate["label"] = label
        step2_rows.append(duplicate)
        continue
    s, e, r = run_variant(label, max_assets_in_portfolio=best_n, max_concentration_pct=conc)
    step2_rows.append(panel(label, s, e, r, daily(anchor_returns)))

step2_df = pd.DataFrame(step2_rows).set_index("label")
step2_df["passes"] = [passes_constraints(row, anchor_panel) for _, row in step2_df.iterrows()]
display(step2_df)
"""))

cells.append(md("## Winner and leave-one-vault-out\n"))
cells.append(code("""passing = step2_df[step2_df["passes"]]
if len(passing):
    winner_label = passing["martin"].idxmax()
    winner_conc = float(winner_label.split("_conc_")[1])
    print(f"Winner: {winner_label} (Martin {passing.loc[winner_label, 'martin']:.3f} vs anchor {anchor_panel['martin']:.3f})")

    worst_vault = largest_contributing_vault(anchor_state)
    s, e, r = run_variant(f"{winner_label}_without_top_vault", max_assets_in_portfolio=best_n, max_concentration_pct=winner_conc, masked={worst_vault})
    lovo_panel = panel(f"{winner_label}_without_top_vault", s, e, r, daily(anchor_returns))
    display(pd.DataFrame([step2_df.loc[winner_label].drop("passes"), lovo_panel]))
    print(f"Leave-one-vault-out (excluding {worst_vault}): still passes constraints = {passes_constraints(lovo_panel, anchor_panel)}")
else:
    winner_label = None
    print("No breadth/concentration combination satisfies the adoption constraints on the development window.")
"""))

write_notebook(cells, TRACK_DIR / "06-backtest-breadth-concentration.ipynb")
