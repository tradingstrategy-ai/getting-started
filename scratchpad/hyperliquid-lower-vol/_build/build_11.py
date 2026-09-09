import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB11 - combination, late-period check and close-out

Closes out the [03-smoothing-experiment-plan.md](03-smoothing-experiment-plan.md) track.
Every structural lever (NB04 vol target, NB05 pool cap, NB06 breadth/concentration, NB07 sizing)
and the consistency-selection legs (NB09) were REJECTed; the only
lead the track produced is NB09's single-point event-concentration penalty diagnostic
(`lambda=0.5`), which improved CAGR, ulcer index and Martin ratio simultaneously but has not been
checked for a plateau. This notebook does three things: checks that plateau, opens the reserved
late period where NB03a predicted the problem actually lives, and compares against the live
book and the full-window candidate
([02-better-format.ipynb](02-better-format.ipynb)) as a labelled case study rather than a gate.

**Based on:** [09-backtest-consistency-selection.ipynb](09-backtest-consistency-selection.ipynb).

## What "combination" means when nothing was Adopted

The plan's combination step assumed at least one Adopt-tier winner from NB04-NB09 to merge. None
cleared the full adoption bar - every structural and sizing lever was REJECTed, and both
consistency-selection legs collapsed. The only candidate worth carrying forward is the
event-concentration penalty, which is Provisional at best (a single lambda, no plateau, no
leave-one-vault-out). This notebook's first step is therefore to check whether it is a genuine
plateau or a spike (NB79's rule) before deciding whether it is carried any further.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("11-backtest-closeout")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Shared harness: run the anchor, then the plateau check.\n"))
cells.append(harness_cell())
cells += integrity_and_audit_cells()

cells.append(md("""# Step 1: is the event-concentration penalty a plateau or a spike?

NB79's rule: a variant is only believed if adjacent parameter values also beat the anchor.
NB09 tested only `lambda=0.5`; this fills in 0.25, 0.75 and 1.0 around it.
"""))
cells.append(code("""anchor_cycle_returns, _ = cycle_returns(anchor_equity)
rows = [anchor_panel]
for lam in (0.25, 0.5, 0.75, 1.0):
    s, e, r = run_variant(f"event_concentration_{lam}", event_concentration_lambda=lam)
    rows.append(panel(f"event_concentration_{lam}", s, e, r, anchor_cycle_returns))

plateau_df = pd.DataFrame(rows).set_index("label")
plateau_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in plateau_df.iterrows()
]
display(plateau_df)

beats_anchor_on_martin = plateau_df["martin"] > anchor_panel["martin"]
is_plateau = beats_anchor_on_martin.loc[["event_concentration_0.25", "event_concentration_0.5", "event_concentration_0.75"]].all()
print(f"Beats anchor's Martin ratio at each lambda: {beats_anchor_on_martin.to_dict()}")
print(f"Plateau across 0.25/0.5/0.75 (the NB79 test): {is_plateau}")
"""))

cells.append(md("""## Step 1b: the vol-matched control, which turned out to be the track's only candidate

NB09 added the vol-matched placebo the plan had pre-registered as a *control* - drop the N
highest-volatility candidates each cycle, with no view on quality at all - to test whether the
consistency legs' beta reduction was selection skill or generic de-risking. It was generic: the
placebo reached the same beta at far better return. But the control also did something the control
was not supposed to do. It satisfied every adoption constraint, at three contiguous settings, which
is a plateau rather than the spike pattern that disqualified the event-concentration penalty.

It is re-run here so this notebook's decision rests on figures computed in the same
kernel, and so the leave-one-vault-out check the adoption rule requires is applied to it.
"""))
cells.append(code("""vol_rows = [anchor_panel]
for drop in (20, 25, 30, 35, 40):
    label = f"vol_matched_drop_{drop}"
    s, e, r = run_variant(label, vol_matched_drop_count=drop)
    vol_rows.append(panel(label, s, e, r, anchor_cycle_returns))

vol_df = pd.DataFrame(vol_rows).set_index("label")
vol_df["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in vol_df.iterrows()
]
display(vol_df)

vol_passing = vol_df.index[(vol_df["passes"]) & (vol_df.index != "anchor")].tolist()
vol_is_plateau = len(vol_passing) >= 3
print(f"Settings satisfying every constraint: {vol_passing or 'none'}")
print(f"Plateau (three or more contiguous settings): {vol_is_plateau}")

if vol_passing:
    vol_winner_label = vol_df.loc[vol_passing, "martin"].idxmax()
    vol_winner_drop = int(vol_winner_label.replace("vol_matched_drop_", ""))
    print(f"Winner by Martin ratio: {vol_winner_label} "
          f"({vol_df.loc[vol_winner_label, 'martin']:.2f} vs anchor {anchor_panel['martin']:.2f})")

    # Leave-one-vault-out, by full re-simulation with the largest contributor unavailable.
    worst_vault = largest_contributing_vault(anchor_state)
    s, e, r = run_variant(f"{vol_winner_label}_without_top_vault",
                          vol_matched_drop_count=vol_winner_drop, masked={worst_vault})
    vol_lovo = panel(f"{vol_winner_label}_without_top_vault", s, e, r, anchor_cycle_returns)
    display(pd.DataFrame([vol_df.loc[vol_winner_label].drop("passes"), vol_lovo]))
    vol_lovo_survives = passes_constraints(vol_lovo, anchor_panel)
    print(f"Leave-one-vault-out (excluding {worst_vault}): still passes = {vol_lovo_survives}")
else:
    vol_winner_label, vol_winner_drop, vol_lovo_survives = None, None, False
"""))

cells.append(md("""# Step 2: the late period, 2026-07-01 to 2026-09-08

**This is no longer a hold-out.** The track originally reserved this period and opened it once,
here. Every notebook now runs the full window, so this period is inside the data every variant was
selected on, and the figures below carry no out-of-sample claim. It is kept as a **sub-period
segment** because NB03a predicted the BTC-beta episode the track targets falls here, and that
prediction is worth checking even in sample.

The anchor and any candidate that cleared the development checks are each run **fresh** on this
period - no earlier positions carried forward - so the comparison is like for like. The universe
already covers the full window, so no second universe is needed.
"""))
cells.append(code("""LATE_KWARGS = dict(backtest_start=LATE_START.to_pydatetime(), backtest_end=LATE_END.to_pydatetime())

anchor_late_state, anchor_late_equity, anchor_late_returns = run_variant("anchor_late", **LATE_KWARGS)
anchor_late_panel = panel("anchor_late", anchor_late_state, anchor_late_equity, anchor_late_returns)
anchor_late_cycle_returns = cycle_returns(anchor_late_equity)[0]

late_rows = [anchor_late_panel]
candidate_late_state = None

if is_plateau:
    s, e, r = run_variant("event_concentration_0.5_late", event_concentration_lambda=0.5, **LATE_KWARGS)
    late_rows.append(panel("event_concentration_0.5_late", s, e, r, anchor_late_cycle_returns))
    candidate_late_state = s
else:
    print("The event-concentration penalty is a spike, not a plateau, so it is not carried forward.")

if vol_winner_label and vol_lovo_survives:
    s, e, r = run_variant(f"{vol_winner_label}_late", vol_matched_drop_count=vol_winner_drop, **LATE_KWARGS)
    late_rows.append(panel(f"{vol_winner_label}_late", s, e, r, anchor_late_cycle_returns))
    candidate_late_state = s
    print(f"{vol_winner_label} cleared both the plateau and leave-one-vault-out checks, so it is "
          f"carried into the late-period comparison.")
elif vol_winner_label:
    print(f"{vol_winner_label} passed the constraints on the full window but failed "
          f"leave-one-vault-out, so it is not carried into the late-period comparison.")

display(pd.DataFrame(late_rows))
"""))

cells.append(md("""# Step 3: live-book and full-window case study

Diagnostic only, per the plan (fitting a rule to avoid these specific names would be outcome
fitting - NB79 and NB44 both warn against exactly this). Compares the late-period runs' final basket
against [02-better-format.ipynb](02-better-format.ipynb)'s full-window closing basket (Citadel,
AceVault Hyper01, DOEZOE, Octavious Maximus, Mad Scientists, Sequoia HyperStable - the anchor
configuration run to 2026-09-08) and against the live `hyper-ai` book snapshot from
[PR #60](https://github.com/tradingstrategy-ai/getting-started/pull/60) (open: Octavious, Sequoia,
Citadel, Gucky_4coin, Mad Scientists, DOEZOE).
"""))
cells.append(code("""#: Pool addresses, not token symbols. The feed truncates vault names to ten characters
#: ("Octavious ", "AceVault H"), so a set comparison against full names silently matches nothing -
#: the first version of this cell would have reported every pumper as dropped.
def closing_basket_addresses(state_) -> set:
    return {
        str(p.pair.pool_address).lower()
        for p in state_.portfolio.get_open_positions()
        if not p.pair.is_credit_supply()
    }


def basket_names(state_) -> list[str]:
    return sorted(
        p.pair.base.token_symbol.strip()
        for p in state_.portfolio.get_open_positions()
        if not p.pair.is_credit_supply()
    )


FULL_WINDOW_NAMES = ["AceVault Hyper01", "Citadel", "DOEZOE", "Mad Scientists", "Octavious Maximus", "Sequoia HyperStable Yield Optimizer"]

#: The three BTC-beta pumpers that motivated this track, keyed by pool address (PR #60).
KNOWN_PUMPERS = {
    "0x45c42fbd450b5506f8dc819d46036630fe75b81e": "Octavious Maximus",
    "0xcae0d1558b70b92ee9fd0acb20cb639c8c28ae69": "DOEZOE",
    "0xebc9865942ab666a57976a7768594b29133cbf53": "Sequoia HyperStable Yield Optimizer",
}
LIVE_BOOK_NAMES = ["Citadel", "DOEZOE", "Gucky_4coin", "Mad Scientists", "Octavious Maximus", "Sequoia HyperStable Yield Optimizer"]
KNOWN_STEADY_DROPPED = ["22Cap", "HYPErQuant"]   # PR #60: dropped within days despite low beta and low vol

anchor_late_addresses = closing_basket_addresses(anchor_late_state)
print("Anchor, late-period closing basket:", basket_names(anchor_late_state))
anchor_pumpers = {name for addr, name in KNOWN_PUMPERS.items() if addr in anchor_late_addresses}
print(f"  of which known BTC-beta pumpers: {sorted(anchor_pumpers) or 'none'} "
      f"({len(anchor_pumpers)} of {len(KNOWN_PUMPERS)})")

if candidate_late_state is not None:
    candidate_addresses = closing_basket_addresses(candidate_late_state)
    print("Candidate, late-period closing basket:", basket_names(candidate_late_state))
    dropped = {name for addr, name in KNOWN_PUMPERS.items() if addr in anchor_late_addresses and addr not in candidate_addresses}
    print(f"  pumpers the candidate dropped that the anchor held: {sorted(dropped) or 'none'}")
else:
    print("  (no candidate cleared its checks, so there is nothing to compare against)")

print()
print("For reference, not re-run here:")
print("  02-better-format.ipynb full-window basket:", sorted(FULL_WINDOW_NAMES))
print("  live hyper-ai book snapshot (PR #60):     ", LIVE_BOOK_NAMES)
print("  steady vaults the live book dropped fast: ", KNOWN_STEADY_DROPPED)
"""))

cells.append(md("""# Verdict table across the track

The event-concentration row is derived from step 1 above rather than asserted, so this table
cannot drift out of step with the plateau result computed in the same notebook.
"""))
cells.append(code("""event_verdict = "ADOPT" if is_plateau else "REJECT (spike, not a plateau)"
best_lambda = plateau_df.loc[plateau_df.index != "anchor", "martin"].idxmax()
event_note = (
    f"Best at {best_lambda} (Martin {plateau_df.loc[best_lambda, 'martin']:.1f} vs anchor "
    f"{anchor_panel['martin']:.1f}), but neighbours fall below the anchor - the NB79 spike pattern"
    if not is_plateau else
    f"Plateau confirmed around {best_lambda}"
)

verdict_df = pd.DataFrame([
    {"notebook": "NB04 vol target", "lever": "structural", "verdict": "REJECT",
     "note": "Every target lowers Martin ratio; lower volatility is bought by holding cash (deployment 61-85% vs 97.5%)"},
    {"notebook": "NB05 pool cap / TVL floor", "lever": "structural", "verdict": "REJECT",
     "note": "Tighter caps and higher TVL floors both cost CAGR through forced substitution into thinner vaults"},
    {"notebook": "NB06 breadth", "lever": "structural", "verdict": "REJECT",
     "note": "Genuinely cuts beta (0.071 -> 0.017) but collapses CAGR to 4-18%"},
    {"notebook": "NB06 concentration", "lever": "structural", "verdict": "REJECT",
     "note": "25% raises CAGR but also beta (0.071 -> 0.099); 20% worse on every axis"},
    {"notebook": "NB07 drawdown sizing", "lever": "sizing", "verdict": "REJECT",
     "note": "inverse_ulcer / inverse_downside worsen CAGR, ulcer and beta together"},
    {"notebook": "NB07 risk contribution", "lever": "sizing", "verdict": "see notebook",
     "note": "Equal-risk-contribution with a residual-correlation cap, the family the plan specified"},
    {"notebook": "NB07 beta-group cap", "lever": "sizing", "verdict": "NO-OP",
     "note": "Identical to the anchor at every threshold - never binds in this window, so untested rather than rejected"},
    {"notebook": "NB08 event-concentration penalty", "lever": "selection (penalty)", "verdict": event_verdict,
     "note": event_note},
    {"notebook": "NB09 consistency legs", "lever": "selection", "verdict": "REJECT",
     "note": "Cut beta hardest of anything tested but collapse in the sparse regime; screen did not survive the backtest"},
    {"notebook": "NB09 vol-matched placebo", "lever": "control", "verdict": "see notebook",
     "note": "Pre-registered NB42 control: does dropping high-volatility names reproduce the selection legs' beta cut?"},
    {"notebook": "NB10 residual CAGR leg", "lever": "selection", "verdict": "NOT BUILT",
     "note": "Failed NB03b's gate at live parity as well as at the original alignment, confirming NB47"},
])
display(verdict_df)
"""))

write_notebook(cells, TRACK_DIR / "11-backtest-closeout.ipynb")
