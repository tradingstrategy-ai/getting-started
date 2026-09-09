import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB05 - structural: capacity realism before anything else grows

Selection untouched. Sweeps `per_position_cap_of_pool_pct` down from the baseline's 33% through
15%, 10% and 5%. NB84 (waterfall-rc) found the chain's largest wins came from positions of up to
38% of a vault's own TVL and recommended a low single-digit cap; fill-at-NAV makes taking a third
of a small vault's liquidity free in a way live execution would not.

**Based on:** [04-backtest-vol-target.ipynb](04-backtest-vol-target.ipynb) (REJECT; no change
carried forward). Development window (2026-01-01 to 2026-06-30); hold-out reserved.

## Why this comes before breadth

The candidate set grows from roughly 106 to 172 vaults across the full backtest window while
`max_assets_in_portfolio` pins the basket at 6, and NB02 found $87,248 discarded for lack of lit
liquidity at the close. More discarded liquidity does not by itself mean more *safely* deployable
names - the cap that produces that discard is itself unrealistic. The Codex review of this plan
flagged exactly this: widening breadth on top of an unrealistic capacity cap spreads capital into
more untradeable marks rather than genuinely diversifying. The winning cap here becomes the fixed
capacity assumption for every later notebook in this track.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("05-backtest-pool-cap")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness: run the anchor, then the pool-cap sweep.\n"))
cells.append(harness_cell())
cells += integrity_and_audit_cells()

cells.append(md("""# Pool-cap sweep

`per_position_cap_of_pool_pct` at the baseline 33%, then 15%, 10% and 5%. Reports the panel
alongside the per-cycle capacity signals (mean discarded-for-liquidity value, mean count of
positions flagged `capped_by_pool_size`) so the reader sees what each cap actually refuses, not
just what it returns.
"""))
cells.append(code("""import re


def capacity_signals(state_) -> dict:
    discarded, capped_counts = [], []
    for _ts, messages in state_.visualisation.messages.items():
        if not messages:
            continue
        text = "\\n".join(messages)
        m = re.search(r"Discarded allocation because of lack of lit liquidity: ([0-9,]+(?:\\.[0-9]+)?) USD", text)
        if m:
            discarded.append(float(m.group(1).replace(",", "")))
        capped_counts.append(text.count("capped_by_pool_size"))
    return {
        "mean_discarded_liquidity_usd": float(np.mean(discarded)) if discarded else float("nan"),
        "mean_capped_by_pool_size_flags": float(np.mean(capped_counts)) if capped_counts else float("nan"),
    }


rows = [anchor_panel]
capacity_rows = {"anchor": capacity_signals(anchor_state)}
for cap in (0.15, 0.10, 0.05):
    s, e, r = run_variant(f"pool_cap_{cap}", per_position_cap_of_pool_pct=cap)
    rows.append(panel(f"pool_cap_{cap}", s, e, r, daily(anchor_returns)))
    capacity_rows[f"pool_cap_{cap}"] = capacity_signals(s)

sweep_df = pd.DataFrame(rows).set_index("label")
sweep_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in sweep_df.iterrows()
]
display(sweep_df)
display(pd.DataFrame(capacity_rows).T)
"""))

cells.append(md("## Winner and leave-one-vault-out\n"))
cells.append(code("""passing = sweep_df[(sweep_df["passes"]) & (sweep_df.index != "anchor")]
if len(passing):
    winner_label = passing["martin"].idxmax()
    winner_cap = float(winner_label.replace("pool_cap_", ""))
    print(f"Winner: {winner_label} (Martin {passing.loc[winner_label, 'martin']:.3f} vs anchor {anchor_panel['martin']:.3f})")

    worst_vault = largest_contributing_vault(anchor_state)
    s, e, r = run_variant(f"{winner_label}_without_top_vault", per_position_cap_of_pool_pct=winner_cap, masked={worst_vault})
    lovo_panel = panel(f"{winner_label}_without_top_vault", s, e, r, daily(anchor_returns))
    display(pd.DataFrame([sweep_df.loc[winner_label].drop("passes"), lovo_panel]))
    print(f"Leave-one-vault-out (excluding {worst_vault}): still passes constraints = {passes_constraints(lovo_panel, anchor_panel)}")
else:
    winner_label = None
    print("No per_position_cap_of_pool_pct value satisfies the adoption constraints; the baseline 33% cap is kept as the anchor for later notebooks, noted as a known capacity-realism gap.")
"""))

write_notebook(cells, TRACK_DIR / "05-backtest-pool-cap.ipynb")
