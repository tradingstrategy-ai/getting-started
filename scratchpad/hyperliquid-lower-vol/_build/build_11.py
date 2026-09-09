import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB11 - combination, hold-out and close-out

Closes out the [03-smoothing-experiment-plan.md](03-smoothing-experiment-plan.md) track.
Every structural lever (NB04 vol target, NB05 pool cap, NB06 breadth/concentration, NB07 sizing)
and both consistency-selection legs (NB09) were REJECTed on the development window; the only
lead the track produced is NB09's single-point event-concentration penalty diagnostic
(`lambda=0.5`), which improved CAGR, ulcer index and Martin ratio simultaneously but has not been
checked for a plateau. This notebook does three things: checks that plateau, opens the reserved
hold-out once to test the lead where it was never expected to matter on the development window,
and compares against the live book and the full-window candidate
([02-better-format.ipynb](02-better-format.ipynb)) as a labelled case study rather than a gate.

**Based on:** [09-backtest-consistency-selection.ipynb](09-backtest-consistency-selection.ipynb).

## What "combination" means when nothing was Adopted

The plan's combination step assumed at least one Adopt-tier winner from NB04-NB09 to merge. None
cleared the full adoption bar - every structural and sizing lever was REJECTed, and both
consistency-selection legs collapsed. The only candidate worth carrying forward is the
event-concentration penalty, which is Provisional at best (a single lambda, no plateau, no
leave-one-vault-out). This notebook's first step is therefore to check whether it is a genuine
plateau or a spike (NB79's rule) before deciding whether it earns the hold-out at all.

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
cells.append(code("""rows = [anchor_panel]
for lam in (0.25, 0.5, 0.75, 1.0):
    s, e, r = run_variant(f"event_concentration_{lam}", event_concentration_lambda=lam)
    rows.append(panel(f"event_concentration_{lam}", s, e, r, daily(anchor_returns)))

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

cells.append(md("""# Step 2: hold-out

Opened once. `strategy_universe` was loaded only through the development window's
`Parameters.backtest_end`, so it holds no July-September candle data; a second universe is built
here, identical in every criterion, but with price data extended through the hold-out end. The
anchor and, if step 1 found a plateau, the event-concentration penalty at `lambda=0.5` are each run
**fresh** on 2026-07-01 to 2026-09-08 - no January-June positions carried forward, a genuinely new
deployment, per the plan. `required_history_period` still lets indicators see the full prior
history. Regime-split columns in the panel are not meaningful for this window (it sits entirely
inside NB03a's "dense" polling regime and after `REGIME_BREAK`) and are reported as produced
without further comment.
"""))
cells.append(code("""HOLDOUT_KWARGS = dict(backtest_start=HOLDOUT_START.to_pydatetime(), backtest_end=HOLDOUT_END.to_pydatetime())

# Rebuild the universe with price data through the hold-out end. `create_trading_universe` and its
# inputs are already defined by the "Trading universe" cell above; only `backtest_end` changes.
with parameter_overrides(backtest_end=HOLDOUT_END.to_pydatetime()):
    holdout_load_parameters = StrategyParameters.from_class(Parameters)
    holdout_universe_input = CreateTradingUniverseInput(
        execution_context=notebook_execution_context,
        client=client,
        timestamp=None,
        parameters=holdout_load_parameters,
        universe_options=UniverseOptions.from_strategy_parameters_class(Parameters, notebook_execution_context),
        execution_model=None,
    )
    holdout_strategy_universe = create_trading_universe(holdout_universe_input)

# `run_variant` closes over the notebook-global `strategy_universe` by name, resolved at call
# time, so swapping the global here is enough to point every hold-out call at the extended
# universe without touching `run_variant` itself.
_dev_strategy_universe = strategy_universe
strategy_universe = holdout_strategy_universe

anchor_ho_state, anchor_ho_equity, anchor_ho_returns = run_variant("anchor_holdout", **HOLDOUT_KWARGS)
anchor_ho_panel = panel("anchor_holdout", anchor_ho_state, anchor_ho_equity, anchor_ho_returns)

holdout_rows = [anchor_ho_panel]
if is_plateau:
    s, e, r = run_variant("event_concentration_0.5_holdout", event_concentration_lambda=0.5, **HOLDOUT_KWARGS)
    candidate_ho_panel = panel("event_concentration_0.5_holdout", s, e, r, daily(anchor_ho_returns))
    holdout_rows.append(candidate_ho_panel)
    candidate_ho_state = s
else:
    candidate_ho_panel = None
    candidate_ho_state = None
    print("Step 1 did not find a plateau; the event-concentration penalty is not carried to the hold-out. "
          "Only the anchor's hold-out figures are reported, for reference against the development window.")

display(pd.DataFrame(holdout_rows))

# Restore the development-window universe for anything below that might still reference it.
strategy_universe = _dev_strategy_universe
"""))

cells.append(md("""# Step 3: live-book and full-window case study

Diagnostic only, per the plan (fitting a rule to avoid these specific names would be outcome
fitting - NB79 and NB44 both warn against exactly this). Compares the hold-out runs' final basket
against [02-better-format.ipynb](02-better-format.ipynb)'s full-window closing basket (Citadel,
AceVault Hyper01, DOEZOE, Octavious Maximus, Mad Scientists, Sequoia HyperStable - the anchor
configuration run to 2026-09-08) and against the live `hyper-ai` book snapshot from
[PR #60](https://github.com/tradingstrategy-ai/getting-started/pull/60) (open: Octavious, Sequoia,
Citadel, Gucky_4coin, Mad Scientists, DOEZOE).
"""))
cells.append(code("""def closing_basket(state_) -> list[str]:
    return sorted({
        p.pair.base.token_symbol
        for p in state_.portfolio.get_open_positions()
        if not p.pair.is_credit_supply()
    })

FULL_WINDOW_BASKET = {"Citadel", "AceVault Hyper01", "DOEZOE", "Octavious Maximus", "Mad Scientists", "Sequoia HyperStable Yield Optimizer"}
LIVE_BOOK_BASKET = {"Octavious Maximus", "Sequoia HyperStable Yield Optimizer", "Citadel", "Gucky_4coin", "Mad Scientists", "DOEZOE"}
KNOWN_PUMPERS = {"Octavious Maximus", "DOEZOE", "Sequoia HyperStable Yield Optimizer"}
KNOWN_STEADY_DROPPED = {"22Cap", "HYPErQuant"}   # NB07/live-book note: dropped within days despite low beta, low vol

print("Anchor, hold-out-only closing basket:", closing_basket(anchor_ho_state))
if candidate_ho_state is not None:
    print("Candidate (event-concentration 0.5), hold-out-only closing basket:", closing_basket(candidate_ho_state))
    dropped_pumpers = KNOWN_PUMPERS - set(closing_basket(candidate_ho_state))
    print(f"Known BTC-beta pumpers dropped by the candidate vs the anchor's hold-out basket: {dropped_pumpers or 'none'}")
print()
print("For reference (not re-run here): 02-better-format.ipynb full-window basket:", sorted(FULL_WINDOW_BASKET))
print("For reference (not re-run here): live hyper-ai book snapshot (PR #60):", sorted(LIVE_BOOK_BASKET))
print("Known steady vaults the live book dropped within days (PR #60 assessment):", sorted(KNOWN_STEADY_DROPPED))
"""))

cells.append(md("""# Verdict table across the track
"""))
cells.append(code("""verdict_df = pd.DataFrame([
    {"notebook": "NB04 vol target", "lever": "structural", "verdict": "REJECT", "note": "No target passes; already-low-beta anchor has no beta to remove on this window"},
    {"notebook": "NB05 pool cap", "lever": "structural", "verdict": "REJECT", "note": "Tightening the cap worsens both CAGR and ulcer via forced substitution into thinner vaults"},
    {"notebook": "NB06 breadth/concentration", "lever": "structural", "verdict": "REJECT", "note": "Breadth collapses CAGR; 25% concentration a near-miss on beta alone"},
    {"notebook": "NB07 sizing", "lever": "sizing", "verdict": "REJECT", "note": "inverse_ulcer/inverse_downside worsen CAGR and ulcer; beta-group cap mostly a no-op"},
    {"notebook": "NB08 event-concentration penalty", "lever": "selection (penalty)", "verdict": "PROVISIONAL / lead", "note": "Best single result in the track; not a checked plateau until this notebook"},
    {"notebook": "NB09 min_window_sortino", "lever": "selection", "verdict": "REJECT", "note": "Collapses in the sparse regime; screen result did not survive the full backtest"},
    {"notebook": "NB09 positive_window_share", "lever": "selection", "verdict": "REJECT", "note": "Same failure mode, less severe"},
    {"notebook": "NB10 residual CAGR leg", "lever": "selection", "verdict": "NOT BUILT", "note": "Failed NB03b's gate (loses in the sparse regime), confirming NB47"},
])
display(verdict_df)
"""))

write_notebook(cells, TRACK_DIR / "11-backtest-closeout.ipynb")
