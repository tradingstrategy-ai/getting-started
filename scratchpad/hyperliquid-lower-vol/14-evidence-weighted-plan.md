# Evidence-weighted allocation plan: prefer vaults with proven consistent profit, accept lower CAGR

- **Status**: EXECUTED (NB14-NB19). **Overall verdict: NOTHING ADOPTED.** All 41 candidates
  tried across selection (NB16), sizing (NB17) and core/satellite sleeves (NB18) fail the
  adoption rule; the family-wise reality check in NB19 gives p = 1.000 (the single best candidate
  across the whole plan still underperforms the anchor's own Sharpe). The nearest misses were
  `sizing_blend` (NB17: 36.42% CAGR, 1.48pp sacrifice, still fails Sharpe/volatility/ulcer) and
  `core_0.7_n3` (NB18: 21.48% CAGR, the only candidate to clear the 20% floor, still fails
  Sharpe/volatility/ulcer). See [19-backtest-closeout.ipynb](19-backtest-closeout.ipynb) for the
  full ranking and the family-wise test.
  Reviewed by Codex CLI (`gpt-5.6-terra`,
  [14-evidence-weighted-plan-codex-review.md](14-evidence-weighted-plan-codex-review.md)) and by an
  independent smoke test of Draft 1's own code
  ([smoke_test_finding.md](_build/smoke_test_finding.md)) before execution. Both are folded in
  below; see "Draft 2 changes" immediately after this status block. `_build/blocks_evidence.py`
  and `_build/harness_evidence.py` are the verified, executed versions of the code in this file -
  it is generated FROM those files, not the other way round, so the two cannot drift.
- **Track**: `hyperliquid-lower-vol`, notebooks NB14-NB19. Continues from
  [03-smoothing-experiment-plan.md](03-smoothing-experiment-plan.md) (NB03a-NB12, nothing adopted)
  and [13-research-age-barrier.ipynb](13-research-age-barrier.ipynb).
- **Baseline to beat**: [02-better-format.ipynb](02-better-format.ipynb), re-run as the anchor in
  every notebook. Full window 2026-01-01 to 2026-09-08, in-sample throughout (the hold-out split
  was retired on 2026-09-09; see the amendment at the top of the NB03 plan).
- **Decision that changes the objective**: the operator has said, in these words, that they would
  rather allocate to vaults that are *consistent in their profit* "even if it means giving out
  CAGR". Every previous notebook was held to a 30% CAGR floor. This plan lowers the floor to 20%
  and ranks by Sharpe. That decision is recorded here **before** any notebook is run so it cannot
  be mistaken for a threshold relaxed after seeing a result.

This file is written to be executed by an agent that has not read the rest of the track. It says
exactly which file to create, which string to replace with which, which `run_variant()` calls to
make, which table to display and how to decide the verdict. Where a design choice is made, the
reason is given once so the executing agent does not re-derive or "improve" it.

## Draft 2 changes

Every change below is tied to a numbered finding in the Codex review or to the smoke-test finding;
the code itself carries the same references in its comments so the two documents cannot drift
apart silently.

- **The admission/ranking score is rewritten.** Draft 1's `sortino_t` mixed an inconsistent
  sample - `n` counted fresh (non-stale) observations, but the mean and downside deviation were
  computed over ALL calendar rows including the stale ones between them (review #1) - and its
  `evidence_t_cap` clip meant a vault at `t = 9.5` on 45 observations scored identically to one at
  `t = 3.0` on 365. A smoke test of exactly this code found the single worst loss in a 75-position
  test run, -$28,990 in 6 days, entered at that maximum score on 45 observations, and the score
  correlated **-0.41** with realised P&L across all positions. `sortino_shrunk_score` replaces it:
  event-time sampling (mean and downside computed on the same fresh-only subsequence counted as
  `n`), an autocorrelation-discounted effective `n`, and shrinkage toward the cross-sectional
  median rather than a bare cap. Re-running the identical smoke test on the new score moved the
  correlation to **+0.11** and the test run's total P&L from -$12,983 to +$13,821 - see
  `_build/smoke_test_finding.md` and the regression check in `_build/verify-plan14-draft2.ipynb`.
- **One score, not two.** Draft 1 screened an unbounded statistic in NB14 but traded a capped one
  in NB16 (review #9) - two different rankings. `sortino_shrunk_score` is bounded to [0, 1] by
  construction and is the only form; NB14 and NB16 use it identically.
- **`expanding_cagr_score` shrinks before bounding, not after** (review #7), so a single catch-up
  mark on a thin sample cannot reach the [0, 1] ceiling and only then be shrunk down.
- **`inverse_vol_early` gates on fresh observation count**, not on `rolling(..., min_periods=...)`,
  which counts stale calendar rows as evidence (review #2 - ironic, since NB13's second barrier
  this function exists to fix is exactly that failure mode). The docstring proves this still
  cannot fire before `inverse_vol` itself does at default parameters; the proof is checked
  empirically (0 violations across 40 sampled vaults) rather than only asserted.
- **Objective reframed as non-inferiority plus a material ulcer improvement, not a Sharpe race**
  (review 3c): constraint 2 changes from "Sharpe strictly greater than the anchor's" to "within
  `SHARPE_NONINFERIORITY_TOL = 0.10` of it", and constraint 4 from "any ulcer improvement" to "at
  least `ULCER_IMPROVEMENT_FRAC = 0.15` relative improvement". Every verdict-table row now reports
  `cagr_sacrifice_pp` explicitly, since that sacrifice - not a fragile Sharpe win - is the
  operator's actual trade-off.
- **The placebo constraint's NaN bug is fixed.** Draft 1's `ref != ref or ...` treated "outside the
  frontier's volatility range" as an automatic PASS (review #6, #15 in the flaws list); it is now a
  FAIL, per the review's explicit recommendation ("mark the candidate not evaluable and failing").
  The frontier itself is now a non-dominated (Pareto) envelope rather than a raw sort-and-interpolate
  over seven points that can include dominated ones (review #8/#9 in the flaws list). The claimed
  `drop_n` mislabelling (review #7 in the flaws list) was checked empirically and did NOT
  reproduce - `pd.DataFrame` column assignment is positional at assignment time and travels with
  its row through a later `.sort_values()` - so that specific point was not applied; the frontier's
  `drop_n` order was re-verified directly in `verify-plan14-draft2.ipynb` (`[60, 50, 40, 30, 20,
  10, 0]` in volatility-ascending order, correctly monotone).
- **A genuine bootstrap of the Sharpe difference** (`bootstrap_sharpe_diff_vs_control`) is added,
  block-resampling the candidate and its nearest-volatility placebo in matched pairs - "paired
  bootstrap CI" was named in Draft 1's prose but never implemented for a Sharpe difference (review
  #10 in the flaws list; `panel()`'s pre-existing bootstrap is a CI on a mean paired *return*
  difference, a different quantity).
- **The core/satellite sleeve reserves hold-protected positions before splitting**, not after
  (review #12): Draft 1 built the satellite sleeve by truncating the incumbent's ranked list to
  `satellite_assets` slots after removing core picks, which could push a hold-protected but
  composite-low-ranked incumbent out entirely. `core_fraction` and `core_assets` are now validated
  at the top of the block (review #14), and realised (post-normalisation) sleeve weights are
  recorded to `state.visualisation.add_calculations()` every cycle (review #13, #24) rather than
  assuming the pre-normalisation target was what was actually held.
- **`hidden_cohort_reach()` reports capital- and days-held-weighted reach**, not only a position
  count share (review #21), and always returns the same schema, including zero positions or a
  missing life cache (review #21), reporting how many held positions could not be matched to the
  cache rather than silently dropping them.
- **A family-wise reality check is added to NB19** (review 3f, and the "Missing ideas" table):
  `family_wise_reality_check()` block-bootstraps the anchor's own returns to build a null
  distribution for "the best of N candidates' Sharpe improvement by chance alone", matched to the
  actual size of the pre-registered candidate family, rather than relying on plateau and
  leave-one-vault-out alone to control for having tried ~25 backtests.
- **NB14's gate is descriptive, not a hard admission bar** (review, flaws #5 and #11): every
  proposed score is backtested in NB16 regardless of its NB14 result; a score that failed the
  screen is run but pre-labelled DIAGNOSTIC and explicitly ineligible for ADOPT. The same rule now
  applies uniformly to NB18 (review #31 in the flaws list: Draft 1 let a core mechanism reach ADOPT
  in NB18 even if NB14 had rejected its underlying score).
- **Not changed, on consideration:** the late period stays a diagnostic sub-period, not a
  re-labelled hold-out (review 3d agrees: "do not re-label July-September as out of sample"); the
  NB19 prospective shadow remains the actual out-of-sample gate. The 0.10 Sharpe-non-inferiority
  tolerance and 0.10 placebo margin are kept as pre-registered practical thresholds per review 3(b)
  and 3(c), reported beside the new bootstrap CIs rather than replaced by them - the review itself
  says a practical margin is reasonable provided it is paired with an uncertainty estimate, which
  it now is.

## Goals

1. **Allocate more to vaults whose consistent profit is evidenced**, and less to vaults whose
   recent return is one BTC move. The two named exemplars are Stratwise Multi-Asset Public and
   Quantitative Market Neutral Strategy - **exemplars of a type, not targets**. A rule is judged on
   the cohort it admits, never on whether it admits those two names (see "Rules for the executing
   agent", item 1).
2. **Accept a lower CAGR**, down to a floor of 20%, in exchange for a higher Sharpe ratio. A
   variant that lowers both CAGR and Sharpe is a scaled-down anchor and is worth nothing: the
   same result is available by holding cash. So Sharpe above the anchor's is a hard constraint,
   not a tie-break.
3. **Do not reward generic de-risking.** NB42 and NB12 both found that "drop the most volatile
   names" reproduces most of what any smarter rule achieved. Every candidate must beat that
   placebo at matched volatility, not just beat the anchor.

## What the track has already established, and what it forces on this design

Numbers below are from [12-research-variant-comparison.ipynb](12-research-variant-comparison.ipynb)
and [13-research-age-barrier.ipynb](13-research-age-barrier.ipynb), full window.

| Finding | Where | Consequence for this plan |
|---|---|---|
| `cagr_lookback_days = 360` acts as an age rule: 225 of 336 universe vaults (67%) can never be scored; the youngest vault the anchor ever bought was 361 days old at entry; all 43 post-2026-04-01 launches are unscorable | NB13 §3 | No re-weighting reaches the target cohort until the fixed window is replaced. Selection change comes first. |
| `inverse_vol` needs 90 observations; under `inverse_variance` a NaN becomes weight 0 | NB13 §3 | A young vault that wins a slot must also be sizeable, so the sizing input needs an early-availability fallback in the same change. |
| The hidden cohort's median life Sharpe is -0.43 against +0.14 for the scorable cohort; only 2 of 32 hidden vaults at tradable size have a Sharpe resolvable at `t > 2` | NB13 §4 | Admitting young vaults by age alone admits junk. Admission must be by *evidence* - a score that rises with both the Sharpe and the number of observations behind it. |
| The hidden cohort's high Sharpes are not NB78's no-down-day signature (down-day share 0.337 vs 0.346) - they are statistically unresolved (median `t` 1.22 vs 2.35) | NB13 §5 | A t-statistic, not a raw Sharpe, is the honest measure of "consistent profit" - but see below: a naive one is not enough on its own. |
| A naive Sharpe/Sortino t-statistic, capped without shrinkage, can score a thin-sample pump at its maximum and correlates *negatively* with realised P&L (-0.41 across 75 positions; single worst loss -$28,990 in 6 days) | Draft-1 smoke test, `_build/smoke_test_finding.md` | The admission score needs cross-sectional shrinkage toward a population prior, not only a cap - see "Draft 2 changes" above. |
| A 90-day CAGR leg loses the dense regime by 4.00 pp of 30-day forward return | NB13 §6 | Shortening the window naively fails. The CAGR leg must be shrunk by evidence, not merely shortened. |
| Every consistency-selection score built so far (`positive_window_share`, `min_window_sortino`, `downside_score`) made the ulcer index *worse* (2.44%, 2.80%, 2.93% vs 1.80%) | NB12 | Those scores reward the absence of noise, not the presence of profit. They are not retried here. |
| `inverse_ulcer` and `inverse_downside` sizing raised invested beta to 0.10 | NB12 | Same lesson for sizing: size by confidence in profit, not by smoothness. |
| Nothing improved cycle Sharpe over the anchor's 2.16 except `vol_matched_drop_30/35` (a spike; fails leave-one-vault-out) and `event_concentration_0.5` (raised volatility) | NB12 | The bar is high and the honest outcome may again be "nothing adopted". The plan must be able to say so. |
| `target_vol_0.15` reaches ulcer 1.34% by holding 23% cash | NB12 | A deployment floor of 90% is needed once the CAGR floor is lowered, or cash overlays win. |
| NB31: either leg of the composite alone is worse on both CAGR and drawdown | NB31 (waterfall-rc) | Keep a CAGR leg, at reduced weight, on the same expanding window. |
| NB03a: the minimum detectable Sharpe difference on this window is large; NB03b's screen has ~8 non-overlapping observations per regime | NB03a/b | Screens are gates to spend a backtest on, not results. Plateau and leave-one-vault-out are mandatory for anything called a winner. |

## Rules for the executing agent

1. **Never select, mask, whitelist or tune towards a vault by name.** Stratwise and QMN appear in
   this file as illustrations of the *type* wanted. If a rule happens to hold them, report it; if it
   does not, do not change the rule until it does. That is outcome fitting and it is the one thing
   the Codex review of the previous plan called out most strongly.
2. **Never change a pre-registered threshold after seeing a result.** The thresholds are in
   "Pre-registered objective and adoption rule". If a threshold turns out to be badly placed,
   write that in the notebook's Robustness section and leave the number alone.
3. **Build every notebook from `_build/`**, with a `build_NN.py` that imports `builder.py`. Never
   edit a code cell inside an `.ipynb` by hand. Headings are written by hand after the run;
   `write_notebook()` preserves a written-up heading on rebuild.
4. **Do not touch the shared blocks that NB03a-NB13 depend on** (`cell6_enhanced.py`,
   `cell10_enhanced.py`, `cell14_enhanced.py`, `harness.py`, `blocks.py`). This plan's additions
   go in two new files, `_build/blocks_evidence.py` and `_build/harness_evidence.py`, and are
   spliced in per notebook through the `extra_replacements` / `extra_source` hooks `builder.py`
   already provides. The exact splice anchors are given below and were verified against the
   current files on 2026-09-09.
5. **Anchor parity is checked in every notebook.** With every new parameter at its default, the
   anchor run must reproduce NB12's anchor row: CAGR 37.90%, ulcer 1.80%, Martin 21.10, cycle
   Sharpe 2.16, 578 trades, final equity $186,746. If it does not, stop and report; do not proceed
   to variants on a drifted anchor.
6. **Run notebooks with the observable runner**, from the repository root:

   ```shell
   cd /Users/moo/code/getting-started
   VIRTUAL_ENV=$PWD/.venv PATH=$PWD/.venv/bin:$PATH TQDM_LOGGABLE_FORCE=stdout \
     .venv/bin/python -m getting_started.jupyter_execute_agent.cli \
     scratchpad/hyperliquid-lower-vol/NN-name.ipynb --timeout=1800
   ```

   (`poetry run` resolves to the wrong virtual environment on this machine; the explicit
   interpreter is the workaround the track has used throughout.) At most three notebooks run
   concurrently.
7. **Every notebook heading has the three sections** the track uses - *Key new insights and what
   did we learn from this experiment?*, *Summary of results*, *Robustness of results* - filled in
   with the actual numbers after the run, in UK English, headings in sentence case. The verdict
   word (ADOPT / REJECT / CONTROL / DIAGNOSTIC) appears in the first insight bullet.
8. **Commit after each notebook**, message `research: NB<NN> <one line>`, and post nothing to
   the PR unless asked.
9. **Backtests are cheap here** (about 15 seconds per variant on the full window), so the cost of
   a run is multiplicity, not compute. Run what the plan says; do not add grid points.

## Pre-registered objective and adoption rule

### Objective

Rank candidates by **cycle Sharpe** (`cycle_sharpe` in the panel: Sharpe of returns on the
strategy's own 2-day clock, as `harness.py` computes it). Not Martin: the ulcer index in Martin's
denominator is path-dependent and NB12 showed it can be halved by the *order* of the same trades.
Not CAGR: the operator has said CAGR is what they will give up. Report `cagr_sacrifice_pp` (the
anchor's CAGR minus the candidate's, in percentage points) on every row: the trade-off itself is
part of the answer, whatever the verdict (review 3c).

### Constraints (all must hold, `passes_constraints_v2` below)

| # | Constraint | Value | Why this value |
|---|---|---|---|
| 1 | CAGR floor | `cagr >= 0.20` | The operator's decision. 20% is a 17.9 pp sacrifice from the anchor and is above every "smooth but dead" variant in NB12 (`assets_10` 1.15%, `min_tvl_100k` -2.41%). |
| 2 | Sharpe non-inferiority | `cycle_sharpe >= anchor cycle_sharpe - 0.10` (i.e. >= 2.06) | Draft 1's "strictly greater than 2.16" was simultaneously too strict an adoption bar (nothing in NB12 cleared it robustly) and too weak a statistical claim (review 3c: a marginal win can be noise). Replaced with non-inferiority within a pre-registered tolerance, paired with a MATERIAL ulcer improvement below - the trade-off is expressed as a real drawdown reduction, not a fragile Sharpe race. |
| 3 | Volatility | `cycle_vol <= anchor cycle_vol` | Unchanged from the NB03 plan. |
| 4 | Ulcer, materially | `ulcer <= anchor ulcer x 0.85` | Draft 1's bare `<` let a trivial difference count as a pass (review: "material ulcer/drawdown improvement" per 3c). At least a 15% relative reduction is required. |
| 5 | Beta | `abs_invested_beta < anchor abs_invested_beta` | Unchanged; invested-basket beta so cash cannot game it. |
| 6 | Deployment | `mean_invested >= 0.90` | Raised from the NB03 plan's 0.45. The old floor was calibrated against a metric that measured cycle cadence; measured correctly the anchor deploys 0.97 and `target_vol_0.15` (0.77) is the cash overlay this must exclude. |
| 7 | Placebo | `cycle_sharpe >= placebo_sharpe_at(cycle_vol) + 0.10` | Goal 3. The placebo frontier is built in NB15 from `vol_matched_drop_count` in {0, 10, 20, 30, 40, 50, 60}, reduced to its non-dominated (Pareto) subset, and the candidate's Sharpe is compared against that envelope linearly interpolated at the candidate's own volatility. Off the envelope's range, the constraint FAILS rather than defaulting to a pass (review: Draft 1's NaN handling did the opposite). 0.10 is a pre-registered practical margin, not a significance claim; `bootstrap_sharpe_diff_vs_control()` against the nearest placebo point is reported beside it. |

### Robustness, required for any ADOPT

- **Plateau.** Every one-step neighbour of the winning parameter point (each parameter moved one
  grid step, others held) must also pass all seven constraints. A point whose neighbours fail is
  a spike, and the NB03 plan's own vol-matched result showed a plateau on one window can be a
  spike on another.
- **Leave-one-vault-out.** Full re-simulation with the largest-contributing vault masked via
  `MASKED_VAULTS` (`run_variant(..., masked={address})`). Must still pass all seven.
- **Late period.** `late_cagr > 0` and `late_ulcer < anchor late_ulcer`. The July-September
  segment is where the anchor earns least (27.20% vs 37.90%); a rule that makes that worse is
  failing exactly where the track's premise says it should help.
- **Hidden-cohort reach.** Report the share of positions opened in vaults younger than 360 days
  at entry, and the count of post-2026-04-01 vaults ever held. This is diagnostic, not a
  constraint - a rule may pass without reaching them - but it is the direct measure of Goal 1
  and must be in every backtest notebook's summary.

### Verdict words

- **ADOPT**: all seven constraints, plateau, leave-one-vault-out and late period all pass.
- **REJECT**: anything else, with the first failing item named.
- **CONTROL**: the placebo frontier itself (NB15); never adopted whatever it scores.
- **DIAGNOSTIC**: a run made to learn something, explicitly ineligible for adoption (e.g. NB16
  run on a score that failed the NB14 gate).

## Shared additions to the build system

Two new files. Nothing in the existing `_build/` files changes.

### `_build/blocks_evidence.py`

```python
"""Evidence-weighted selection track additions (14-evidence-weighted-plan.md), NB14-NB19.

Draft 2. Revised after `14-evidence-weighted-plan-codex-review.md` (gpt-5.6-terra) and
`smoke_test_finding.md` (an independent smoke-test finding: the Draft 1 naive Sortino
t-statistic's realised P&L correlation was -0.41 across a 75-position test run, with the single
worst loss, -$28,990 in 6 days, entered at that statistic's maximum score on 45 observations).

Spliced into the shared cells through builder.py's `extra_replacements` / `extra_source` hooks so
NB03a-NB13 are untouched. Anchors verified against cell6/cell10/cell14_enhanced.py on 2026-09-09.

Changes from Draft 1, each tied to a numbered finding in the Codex review:
- (review #1, #2, smoke test) The admission/ranking score is rewritten as `sortino_shrunk_score`:
  event-time sampling (mean and downside deviation computed on the same fresh-only subsequence
  counted as n, not calendar rows), an autocorrelation-discounted effective n, and cross-sectional
  shrinkage towards the same-day median across all vaults. Replaces `sortino_t`/`sortino_lcb` and
  their separately-capped `_score` variants entirely, so there is one form, used identically by
  the NB14 screen and the NB16 backtest (closing review #9's raw-vs-capped mismatch by
  construction).
- (review #7) `expanding_cagr_score` shrinks the raw annualised return before bounding it to
  [0, 1], not after, so a single catch-up mark cannot reach a materially positive score merely
  because a post-hoc clip is applied last.
- (review #2) `inverse_vol_early` gates on fresh-observation count via `.where()`, not via
  `rolling(..., min_periods=...)`, which counts stale calendar rows as observations. Proof that
  this still cannot fire before `inverse_vol` does at default parameters is in the docstring, and
  is checked again empirically in `verify-plan14-draft2.ipynb`.
"""

#: Appended after the last parameter the NB03 track added (`beta_shrink = 1.0`).
PARAM_ANCHOR = "    beta_shrink = 1.0\n"
PARAM_ADDITIONS_EVIDENCE = PARAM_ANCHOR + '''
    #: --- evidence-weighted selection track additions (see 14-evidence-weighted-plan.md) ---
    #: Calendar-day window the CAGR leg (`expanding_cagr_score`) looks back over. Unlike the
    #: Sortino leg below, this is deliberately calendar-time, not event-time: a return level is
    #: well-defined between two calendar dates regardless of how many stale marks sit between them.
    evidence_max_window_days = 365
    #: Event-count window (not calendar days) the Sortino evidence statistics look back over.
    evidence_max_events = 90
    #: Fewest fresh (mark actually moved, NB57) events before an evidence statistic exists at all.
    evidence_min_events = 20
    #: Fewest of those fresh events that must be down-events, so downside deviation is not
    #: estimated from one or two observed losses.
    evidence_min_down_events = 5
    #: Shrinkage prior strength `k` in `n_eff / (n_eff + k)`. A vault needs `n_eff` well past this
    #: before its own evidence dominates the cross-sectional prior. Plateau-tested at 30, 90.
    evidence_prior_strength = 60
    #: t-equivalent that earns the full [0, 1] evidence sub-score after shrinkage. Plateau-tested
    #: at 2, 4.
    evidence_t_cap = 3.0
    #: Fresh observations at which the expanding CAGR leg is trusted in full; below this it is
    #: shrunk linearly towards zero. Plateau-tested at 90, 270.
    cagr_full_evidence_days = 180
    #: Shortest history the expanding CAGR leg is computed on at all.
    cagr_min_days = 90
    #: `inverse_vol_early` becomes available after this many FRESH observations (not calendar
    #: days). At 90 - the same value as `inverse_vol_window` - it cannot fire before `inverse_vol`
    #: itself does (see the docstring on `inverse_vol_early`), so the anchor is unchanged; NB16
    #: lowers it to 45 so a young vault that wins a slot can be sized (NB13's second barrier).
    inverse_vol_min_periods = 90
    #: NB16 objective (review 3c): Sharpe non-inferiority tolerance against the anchor, and the
    #: minimum RELATIVE ulcer-index improvement required. Both pre-registered; see harness_evidence.py.
    sharpe_noninferiority_tol = 0.10
    ulcer_improvement_frac = 0.15
    #: NB18 two-sleeve structure. None disables it (anchor behaviour). Otherwise the share of the
    #: deployed book given to the evidence-selected core sleeve. Must be in (0, 1].
    core_fraction = None
    #: NB18: number of names in the core sleeve; the satellite gets the remainder of
    #: `max_assets_in_portfolio`. Must be in [1, max_assets_in_portfolio].
    core_assets = 4
    #: NB18: indicator that ranks and sizes the core sleeve.
    core_score_indicator = 'sortino_shrunk_score'
'''

INDICATOR_ADDITIONS_EVIDENCE = '''
#: --- evidence-weighted selection track additions (see 14-evidence-weighted-plan.md) ---


def _event_time_stats(
    close: pd.Series,
    max_events: int,
    min_events: int,
    min_down_events: int,
) -> tuple[pd.Series, pd.Series]:
    """Event-time mean/downside Sortino input and an autocorrelation-discounted effective n.

    NB57: a zero daily return on a Hyperliquid vault mark is almost always a stale poll, not a
    real flat day. This restricts every calculation to the subsequence of days the mark actually
    moved (`fresh_r`), a non-contiguous slice of the calendar index, and rolls over that
    subsequence by EVENT COUNT rather than by calendar day - so the sample used for the mean and
    the downside deviation is exactly the sample counted as `n`. Draft 1's `sortino_t` counted
    fresh events as `n` but computed the mean and downside deviation over calendar rows including
    the stale (zero-return) ones between them, which understates `n` relative to the sample the
    ratio was actually estimated from (review finding #1).

    The lag-1 autocorrelation of the fresh-event series further discounts `n` via
    `n_eff = n / (1 + 2*|rho_1|)`, a truncated Newey-West-style correction: a short, smooth run -
    the shape of a pump before it reverses - produces serially correlated fresh-event returns,
    and should not be treated as that many independent observations.

    Both outputs are reindexed back onto the full calendar index, carrying the last known event
    forward, so `decide_trades` (which reads one calendar bar back, per NB57) always sees the most
    recent evidence rather than NaN on the many stale calendar days between events.
    """
    r = close.pct_change()
    fresh_r = r[r.abs() > 0]
    if len(fresh_r) == 0:
        empty = pd.Series(float('nan'), index=close.index)
        return empty, empty.copy()

    w, min_ev = int(max_events), int(min_events)
    mean_event = fresh_r.rolling(w, min_periods=min_ev).mean()
    downside_event = (fresh_r.clip(upper=0.0) ** 2).rolling(w, min_periods=min_ev).mean() ** 0.5
    down_count = (fresh_r < 0).rolling(w, min_periods=1).sum()
    n_event = fresh_r.rolling(w, min_periods=min_ev).count()

    def _autocorr1(values):
        if len(values) < 5 or np.std(values) == 0:
            return 0.0
        a, b = values[:-1], values[1:]
        if np.std(a) == 0 or np.std(b) == 0:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])

    rho1 = fresh_r.rolling(w, min_periods=min_ev).apply(_autocorr1, raw=True).fillna(0.0).clip(-0.9, 0.9)
    n_eff = n_event / (1.0 + 2.0 * rho1.abs())

    raw_sortino = (mean_event / downside_event.replace(0.0, float('nan'))) * (TRADING_DAYS_PER_YEAR ** 0.5)
    raw_sortino = raw_sortino.where(down_count >= int(min_down_events))

    full_index = close.index
    return raw_sortino.reindex(full_index).ffill(), n_eff.reindex(full_index).ffill()


@indicators.define()
def sortino_raw_event(
    close: pd.Series,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
) -> pd.Series:
    """Event-time annualised Sortino ratio; NaN until the minimum event counts are met."""
    raw, _ = _event_time_stats(close, evidence_max_events, evidence_min_events, evidence_min_down_events)
    return raw


@indicators.define()
def sortino_neff_event(
    close: pd.Series,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
) -> pd.Series:
    """Autocorrelation-discounted effective observation count behind `sortino_raw_event`."""
    _, neff = _event_time_stats(close, evidence_max_events, evidence_min_events, evidence_min_down_events)
    return neff


@indicators.define(dependencies=(sortino_raw_event,), source=IndicatorSource.dependencies_only_universe)
def sortino_cross_sectional_prior(
    dependency_resolver: IndicatorDependencyResolver,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
) -> pd.Series:
    """Cross-sectional median of `sortino_raw_event` across all vaults, per timestamp.

    Same construction as `tvl_inclusion_criteria` (`cell10_enhanced.py`): pull every pair's value
    for this indicator combined into one MultiIndex series, then aggregate by timestamp. The
    shrinkage target for a thinly-observed vault - what a typical vault's Sortino looks like on
    the same day - rather than a fixed constant, so the prior moves with the regime (NB57's
    sparse/dense polling split included).
    """
    series = dependency_resolver.get_indicator_data_pairs_combined(
        sortino_raw_event,
        parameters={
            'evidence_max_events': evidence_max_events,
            'evidence_min_events': evidence_min_events,
            'evidence_min_down_events': evidence_min_down_events,
        },
    )
    return series.groupby(level='timestamp').median()


@indicators.define(
    dependencies=(sortino_raw_event, sortino_neff_event, sortino_cross_sectional_prior),
    source=IndicatorSource.dependencies_only_per_pair,
)
def sortino_shrunk_score(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
    evidence_prior_strength: int = 60,
    evidence_t_cap: float = 3.0,
) -> pd.Series:
    """Bounded [0, 1] evidence score: event-time Sortino, shrunk towards the cross-sectional
    median by `n_eff / (n_eff + evidence_prior_strength)`, then mapped 0..`evidence_t_cap` to 0..1.

    Found in a smoke test of Draft 1 (`smoke_test_finding.md`): a vault at the maximum of the
    unshrunk score, on 45 observations, produced the single worst loss in a 75-position test
    (-$28,990 in 6 days), and the unshrunk score correlated -0.41 with realised P&L across all
    positions. Shrinkage is the structural fix - a thin sample cannot reach the top score however
    extreme its own ratio is, however the cap is set (review finding #1) - regardless of `n_eff`;
    it converges to its own evidence only once `n_eff` grows well past `evidence_prior_strength`.

    NaN wherever `sortino_raw_event` is NaN (fewer than `evidence_min_events` fresh or
    `evidence_min_down_events` down observations) - the NB78 no-down-day protection
    `sortino_score` already has, kept here.
    """
    params = {
        'evidence_max_events': evidence_max_events,
        'evidence_min_events': evidence_min_events,
        'evidence_min_down_events': evidence_min_down_events,
    }
    raw = dependency_resolver.get_indicator_data('sortino_raw_event', pair=pair, parameters=params)
    n_eff = dependency_resolver.get_indicator_data('sortino_neff_event', pair=pair, parameters=params)
    prior = dependency_resolver.get_indicator_data('sortino_cross_sectional_prior', parameters=params)
    prior = prior.reindex(raw.index).ffill()

    k = float(evidence_prior_strength)
    weight_own = n_eff / (n_eff + k)
    shrunk = weight_own * raw.fillna(0.0) + (1.0 - weight_own) * prior.fillna(0.0)
    shrunk = shrunk.where(raw.notna())
    return (shrunk / float(evidence_t_cap)).clip(lower=0.0, upper=1.0)


@indicators.define()
def expanding_cagr_score(
    close: pd.Series,
    evidence_max_window_days: int = 365,
    cagr_min_days: int = 90,
    cagr_full_evidence_days: int = 180,
) -> pd.Series:
    """`cagr_score` on an expanding window, shrunk towards zero while the history is short.

    The window is the last `evidence_max_window_days` or the whole history, whichever is shorter;
    below `cagr_min_days` it is NaN. `shrink = min(1, fresh / cagr_full_evidence_days)` is applied
    to the RAW annualised return BEFORE it is bounded to [0, 1] (review finding #7 on Draft 1:
    applying the shrink after the bound let one large catch-up mark clip to the ceiling first and
    only then be shrunk, which understates how little a thin sample should count for).

    Assumes `close` is one row per day from the vault's first candle with no gaps, which is what
    `TradingStrategyUniverse.create_from_dataset(forward_fill=True)` produces for a vault pair.
    """
    w, min_days = int(evidence_max_window_days), int(cagr_min_days)
    first_price = float(close.iloc[0]) if len(close) else float('nan')
    start = close.shift(w)
    start = start.where(start.notna(), first_price)          # expanding below the cap
    days = pd.Series(np.minimum(np.arange(len(close)), w), index=close.index, dtype=float)
    cagr = (close / start).pow(TRADING_DAYS_PER_YEAR / days.replace(0.0, float('nan'))) - 1.0
    cagr = cagr.where(days >= min_days)
    fresh = (close.pct_change().abs() > 0).astype(float).rolling(w, min_periods=1).sum()
    shrink = (fresh / float(cagr_full_evidence_days)).clip(upper=1.0)
    return ((cagr * shrink) / CAGR_SCORE_CAP).clip(lower=0.0, upper=1.0)


@indicators.define(
    dependencies=(expanding_cagr_score, sortino_shrunk_score),
    source=IndicatorSource.dependencies_only_per_pair,
)
def evidence_composite(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    evidence_max_window_days: int = 365,
    cagr_min_days: int = 90,
    cagr_full_evidence_days: int = 180,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
    evidence_prior_strength: int = 60,
    evidence_t_cap: float = 3.0,
    cagr_weight: float = 0.6,
) -> pd.Series:
    """`cagr_weight x expanding CAGR score + (1 - cagr_weight) x shrunk Sortino score`.

    The incumbent composite with both legs replaced by their evidence-weighted forms. Same
    `cagr_weight` parameter as the incumbent, so NB16's plateau over 0.3 / 0.6 reads directly
    against NB92's 0.6. This is the SAME bounded form used by the NB14 screen (review finding #9:
    Draft 1 screened an unbounded statistic but traded a capped one - two different rankings).
    """
    cagr_component = dependency_resolver.get_indicator_data(
        'expanding_cagr_score', pair=pair,
        parameters={
            'evidence_max_window_days': evidence_max_window_days,
            'cagr_min_days': cagr_min_days,
            'cagr_full_evidence_days': cagr_full_evidence_days,
        },
    )
    sortino_component = dependency_resolver.get_indicator_data(
        'sortino_shrunk_score', pair=pair,
        parameters={
            'evidence_max_events': evidence_max_events,
            'evidence_min_events': evidence_min_events,
            'evidence_min_down_events': evidence_min_down_events,
            'evidence_prior_strength': evidence_prior_strength,
            'evidence_t_cap': evidence_t_cap,
        },
    )
    return cagr_weight * cagr_component + (1.0 - cagr_weight) * sortino_component


@indicators.define()
def inverse_vol_early(
    close: pd.Series,
    inverse_vol_window: int = 90,
    inverse_vol_min_periods: int = 90,
) -> pd.Series:
    """`inverse_vol` that becomes available after `inverse_vol_min_periods` FRESH observations.

    Review finding #2 on Draft 1: `rolling(..., min_periods=...)` counts non-null calendar rows,
    and a stale (repeated) mark's `pct_change()` is a valid zero, not null - so a `min_periods`
    gate on a plain rolling std counts calendar days elapsed, not real observations, which is
    exactly the failure NB13 diagnosed for the incumbent's own fixed windows. This gates on fresh
    count directly via `.where()` instead.

    At the default `inverse_vol_min_periods = inverse_vol_window = 90`: `inverse_vol` (the
    incumbent) requires 90 calendar days of `pct_change()` history regardless of staleness. This
    function requires 90 FRESH observations inside a window of at most 90 calendar days - and
    fresh observations cannot outnumber calendar days elapsed, so it cannot be non-NaN before
    `inverse_vol` is also non-NaN (`decide_trades` only ever reads this as a fallback when
    `inverse_vol` is NaN, so the two cannot both matter at the same cycle). The anchor is
    therefore unchanged at defaults - proved here rather than asserted, and checked again
    empirically in `verify-plan14-draft2.ipynb`.
    """
    r = close.pct_change()
    w = int(inverse_vol_window)
    fresh = (r.abs() > 0).astype(float).rolling(w, min_periods=1).sum()
    vol = r.rolling(w, min_periods=2).std()
    return (1.0 / vol.clip(lower=VOL_FLOOR)).where(fresh >= int(inverse_vol_min_periods))

'''

#: Old -> new replacements for cell 14 (`decide_trades` / `compute_sizing_weights`). Every "old"
#: string must occur exactly once in cell14_enhanced.py; verify-plan14-draft2.ipynb asserts this
#: with `str.count() == 1` before splicing (review finding: Draft 1's plan text claimed this but
#: `builder.cell14()` itself only asserts "in", not "exactly once" - the count check lives in the
#: verification script, not in builder.py, which is shared and out of scope for this plan to edit).
CELL14_REPLACEMENTS_EVIDENCE = {
    # 1. compute_sizing_weights signature: add the evidence map.
    "    correlation_cap: float = 0.0,\n) -> dict[int, float]:\n":
    "    correlation_cap: float = 0.0,\n"
    "    evidence_by_id: dict[int, float] | None = None,\n"
    ") -> dict[int, float]:\n",

    # 2. compute_sizing_weights: the 'evidence' method, inserted before the ValueError.
    '    raise ValueError(f"Unknown weighting method: {method}")\n':
    "    if method == 'evidence':\n"
    "        # NB17: size by evidence of profit (the shrunk Sortino score), not by absence of\n"
    "        # noise. NB77/NB12: inverse variance and inverse ulcer both hand the biggest slots to\n"
    "        # quiet vaults regardless of sign; a quiet loser gets nothing here.\n"
    "        evidence_map = evidence_by_id or {}\n"
    "        raw = {}\n"
    "        for pair_id in selected_pair_ids:\n"
    "            value = evidence_map.get(pair_id, 0.0)\n"
    "            value = 0.0 if value is None or value != value else float(value)\n"
    "            raw[pair_id] = max(value, 0.0)\n"
    "        if sum(raw.values()) <= 0:\n"
    "            return {pair_id: 1.0 for pair_id in selected_pair_ids}\n"
    "        if floor_fraction > 0:\n"
    "            mean_weight = sum(raw.values()) / len(raw)\n"
    "            raw = {pid: max(w, floor_fraction * mean_weight) for pid, w in raw.items()}\n"
    "        return raw\n"
    "\n"
    '    raise ValueError(f"Unknown weighting method: {method}")\n',

    # 3. decide_trades: two new per-vault maps.
    "    beta_by_id = {}\n":
    "    beta_by_id = {}\n"
    "    #: Evidence-weighted track: shrunk Sortino score for sizing (NB17) and the core sleeve (NB18).\n"
    "    evidence_by_id = {}\n"
    "    core_score_by_id = {}\n",

    # 4. decide_trades: inverse_vol early-availability fallback (NB13's second barrier).
    "        inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)\n"
    "        inv_vol_by_id[pair_id] = float(inv_vol) if inv_vol is not None and inv_vol == inv_vol else 0.0\n":
    "        inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)\n"
    "        if inv_vol is None or inv_vol != inv_vol:\n"
    "            # Young vault: fall back to the early-availability estimate. Cannot fire before\n"
    "            # `inverse_vol` itself does at default parameters - see the docstring on\n"
    "            # `inverse_vol_early` - so the anchor path (defaults) is unaffected.\n"
    "            inv_vol = indicators.get_indicator_value('inverse_vol_early', pair=pair)\n"
    "        inv_vol_by_id[pair_id] = float(inv_vol) if inv_vol is not None and inv_vol == inv_vol else 0.0\n",

    # 5. decide_trades: read the evidence statistics next to the beta read.
    "        beta_value = indicators.get_indicator_value('btc_beta', pair=pair)\n":
    "        evidence_value = indicators.get_indicator_value('sortino_shrunk_score', pair=pair)\n"
    "        evidence_by_id[pair_id] = float(evidence_value) if evidence_value is not None and evidence_value == evidence_value else 0.0\n"
    "        core_indicator = str(getattr(parameters, 'core_score_indicator', 'sortino_shrunk_score'))\n"
    "        core_value = evidence_value if core_indicator == 'sortino_shrunk_score' else indicators.get_indicator_value(core_indicator, pair=pair)\n"
    "        core_score_by_id[pair_id] = float(core_value) if core_value is not None and core_value == core_value else float('nan')\n"
    "        beta_value = indicators.get_indicator_value('btc_beta', pair=pair)\n",

    # 6. decide_trades: pass the evidence map into sizing.
    "        correlation_cap=float(getattr(parameters, 'residual_correlation_cap', 0.0)),\n    )\n":
    "        correlation_cap=float(getattr(parameters, 'residual_correlation_cap', 0.0)),\n"
    "        evidence_by_id=evidence_by_id,\n"
    "    )\n",

    # 7. decide_trades: NB18 two-sleeve override, inserted after sizing and before the beta group
    # cap. Reserves minimum-hold-protected incumbents to whichever sleeve they were already
    # assigned last cycle FIRST, before filling remaining slots by rank - review finding: Draft 1
    # built the satellite sleeve by filtering the incumbent's `selected` list down to
    # `satellite_assets` slots AFTER removing core picks, which could push a hold-protected but
    # composite-low-ranked incumbent out of the satellite entirely, defeating hold protection.
    "    # NB07: cap the combined weight share of vaults whose |beta| exceeds the threshold, shrinking\n":
    "    # NB18: two-sleeve allocation. The core sleeve is ranked and sized by evidence of\n"
    "    # consistent profit; the satellite sleeve is the incumbent selection above, sized by the\n"
    "    # incumbent method. `core_fraction` of the deployed book is the PRE-normalisation target\n"
    "    # for the core sleeve; realised sleeve shares (after the concentration cap and pool-cap\n"
    "    # sizing below) are recorded to `state.visualisation` so NB18's attribution is measured,\n"
    "    # not assumed. The incumbent sizing call above still runs (its result is discarded here)\n"
    "    # so the anchor path is byte-identical.\n"
    "    core_fraction = getattr(parameters, 'core_fraction', None)\n"
    "    realised_core_share = None\n"
    "    if core_fraction:\n"
    "        core_fraction = float(core_fraction)\n"
    "        core_assets = int(parameters.core_assets)\n"
    "        assert 0.0 < core_fraction <= 1.0, f\"core_fraction must be in (0, 1]: {core_fraction}\"\n"
    "        assert 1 <= core_assets <= max_assets_in_portfolio, (\n"
    "            f\"core_assets must be in [1, {max_assets_in_portfolio}]: {core_assets}\"\n"
    "        )\n"
    "        satellite_assets = max(max_assets_in_portfolio - core_assets, 0)\n"
    "        pair_by_id = {pid: pair for pid, pair, _signal in candidates}\n"
    "\n"
    "        # Reserve currently-held, hold-protected positions to their PREVIOUS sleeve first, so\n"
    "        # the sleeve split cannot itself evict a position minimum_hold_days protects.\n"
    "        prev_calc = state.visualisation.calculations.get(\n"
    "            max(state.visualisation.calculations) if state.visualisation.calculations else None, {}\n"
    "        ) or {}\n"
    "        prev_core_ids = set(prev_calc.get('core_ids', []))\n"
    "        protected_core = {pid for pid in hold_protected_ids if pid in prev_core_ids}\n"
    "        protected_satellite = {pid for pid in hold_protected_ids if pid not in prev_core_ids}\n"
    "\n"
    "        core_ranked_all = sorted(\n"
    "            [pid for pid, score in core_score_by_id.items() if score == score and pid in pair_by_id],\n"
    "            key=lambda pid: (-core_score_by_id[pid], pid),\n"
    "        )\n"
    "        core_ids = [pid for pid in core_ranked_all if pid in protected_core]\n"
    "        for pid in core_ranked_all:\n"
    "            if len(core_ids) >= core_assets:\n"
    "                break\n"
    "            if pid in core_ids or pid in protected_satellite:\n"
    "                continue\n"
    "            if pid not in held_pair_ids and not input.pricing_model.can_deposit(timestamp, pair_by_id[pid]):\n"
    "                continue\n"
    "            core_ids.append(pid)\n"
    "\n"
    "        satellite_ranked_all = [pid for pid, _pair, _signal in ordered if pid not in core_ids]\n"
    "        satellite_ids = [pid for pid in satellite_ranked_all if pid in protected_satellite]\n"
    "        for pid in satellite_ranked_all:\n"
    "            if len(satellite_ids) >= satellite_assets:\n"
    "                break\n"
    "            if pid in satellite_ids:\n"
    "                continue\n"
    "            if pid not in held_pair_ids and not input.pricing_model.can_deposit(timestamp, pair_by_id[pid]):\n"
    "                continue\n"
    "            satellite_ids.append(pid)\n"
    "\n"
    "        core_weights = compute_sizing_weights(\n"
    "            core_ids, inv_vol_by_id, signal_by_id, method='evidence',\n"
    "            softmax_temperature=float(getattr(parameters, 'softmax_temperature', 0.25)),\n"
    "            evidence_by_id=core_score_by_id,\n"
    "            floor_fraction=float(getattr(parameters, 'weight_floor_fraction', 0.0)),\n"
    "        )\n"
    "        satellite_weights = compute_sizing_weights(\n"
    "            satellite_ids, inv_vol_by_id, signal_by_id, method=str(parameters.weighting_method),\n"
    "            softmax_temperature=float(getattr(parameters, 'softmax_temperature', 0.25)),\n"
    "            weighting_exponent=float(getattr(parameters, 'weighting_exponent', 2.0)),\n"
    "            risk_by_id=risk_by_id, fresh_by_id=fresh_by_id,\n"
    "            min_fresh=float(getattr(parameters, 'min_fresh_observations', 0.0)),\n"
    "            floor_fraction=float(getattr(parameters, 'weight_floor_fraction', 0.0)),\n"
    "            corr_by_id=corr_by_id,\n"
    "            correlation_cap=float(getattr(parameters, 'residual_correlation_cap', 0.0)),\n"
    "            evidence_by_id=evidence_by_id,\n"
    "        )\n"
    "\n"
    "        def _sleeve(weights, fraction):\n"
    "            total = sum(weights.values()) or 1.0\n"
    "            return {pid: fraction * w / total for pid, w in weights.items()}\n"
    "\n"
    "        weight_by_id = {**_sleeve(core_weights, core_fraction), **_sleeve(satellite_weights, 1.0 - core_fraction)}\n"
    "        selected = [(pid, pair_by_id[pid], signal_by_id.get(pid, 0.0)) for pid in core_ids + satellite_ids]\n"
    "        realised_core_share = core_fraction   # overwritten below with the post-normalisation figure\n"
    "\n"
    "    # NB07: cap the combined weight share of vaults whose |beta| exceeds the threshold, shrinking\n",

    # 8. Record realised (post-normalisation) sleeve composition once weights are final, right
    # before `alpha_model.calculate_target_positions()`. Review finding: `core_fraction` was only
    # ever a pre-normalisation target; the concentration cap and pool-cap sizing can move the
    # realised share away from it, and Draft 1 never measured what actually happened.
    "    alpha_model.update_old_weights(state.portfolio, ignore_credit=False)\n"
    "    alpha_model.calculate_target_positions(position_manager)\n":
    "    if core_fraction:\n"
    "        core_realised = sum(\n"
    "            alpha_model.signals[pid].normalised_weight\n"
    "            for pid in core_ids if pid in alpha_model.signals\n"
    "        )\n"
    "        state.visualisation.add_calculations(timestamp, {\n"
    "            'core_ids': list(core_ids),\n"
    "            'satellite_ids': list(satellite_ids),\n"
    "            'core_fraction_target': core_fraction,\n"
    "            'core_fraction_realised': float(core_realised),\n"
    "        })\n"
    "\n"
    "    alpha_model.update_old_weights(state.portfolio, ignore_credit=False)\n"
    "    alpha_model.calculate_target_positions(position_manager)\n",
}
```

Notes for the agent on the cell 14 replacements:

- Replacement 7 references `candidates`, `selected`, `hold_protected_ids`, `held_pair_ids`,
  `risk_by_id`, `fresh_by_id`, `corr_by_id`, `inv_vol_by_id`, `signal_by_id`, `max_assets_in_portfolio`
  and `input` - all of which exist at that point in the current `decide_trades`. It is inserted
  *after* the existing `weight_by_id = compute_sizing_weights(...)` call, which is why the
  incumbent sizing still runs on the anchor path.
- With `core_fraction = None` (default) replacements 7 and 8 are inert; with
  `inverse_vol_min_periods = 90` replacement 4 is inert (proved in the `inverse_vol_early`
  docstring and checked empirically - 0 violations across 40 sampled vaults - in
  `verify-plan14-draft2.ipynb`); with `weighting_method = 'inverse_variance'` replacement 2 is
  inert; the reads in replacement 5 are harmless. This is what makes rule 5 (anchor parity) hold,
  and it was checked, not only argued: `PARITY_OK True` against NB12's exact anchor row in the same
  verification notebook.
- `core_score_by_id` deliberately stores NaN for an unscored vault (not 0.0), so `core_ranked`
  can exclude it; `evidence_by_id` stores 0.0 so the `'evidence'` sizing method gives it no
  weight rather than crashing.
- Replacement 7 asserts `core_fraction` and `core_assets` are in range as soon as `core_fraction`
  is truthy, so a bad grid point (e.g. `core_fraction=1.2`) crashes loudly rather than producing a
  silently-wrong sleeve split. It also reserves whichever pair ids were in the PREVIOUS cycle's
  `core_ids` (read from `state.visualisation.calculations`, the most recent prior entry) to their
  existing sleeve before ranking fills the remaining slots, so the sleeve split itself cannot evict
  a `minimum_hold_days`-protected incumbent - the failure mode Draft 1 had.
- Replacement 8 is inserted right before `alpha_model.calculate_target_positions()`, after
  `alpha_model.normalise_weights()` has already run, so `alpha_model.signals[pid].normalised_weight`
  is the REALISED (post-concentration-cap, post-pool-cap) weight, not the pre-normalisation
  `core_fraction` target - this is what NB18's per-sleeve attribution reads.

### `_build/harness_evidence.py`

Appended to every backtest notebook as its own cell, immediately after the standard
`harness_cell()`. It only *adds* names; nothing in `harness.py` is redefined.

```python
#: Evidence-weighted track additions to the shared harness (14-evidence-weighted-plan.md).
#: Draft 2. Revised after 14-evidence-weighted-plan-codex-review.md. Only *adds* names; nothing
#: in harness.py (already loaded by the time this cell runs) is redefined.
#:
#: The seven pre-registered constraints of adoption rule v2. Do not edit the numbers here; if one
#: is badly placed, say so in the notebook's Robustness section.
CAGR_FLOOR_V2 = 0.20
#: Review 3(c): strictly beating the anchor's Sharpe is both too strict an adoption bar (nothing
#: in NB12 cleared it robustly) and too weak a statistical claim (a marginal win can be noise).
#: Replaced with non-inferiority within a pre-registered tolerance, paired with a MATERIAL ulcer
#: improvement below - the operator's actual trade-off (consistency for CAGR) is expressed as a
#: real drawdown reduction, not as a fragile Sharpe race.
SHARPE_NONINFERIORITY_TOL = 0.10
#: Relative ulcer-index improvement required, not merely "any" improvement (review: Draft 1's bare
#: `<` let a 0.01 percentage-point difference count as a pass).
ULCER_IMPROVEMENT_FRAC = 0.15
INVESTED_FLOOR_V2 = 0.90
PLACEBO_MARGIN = 0.10
PLACEBO_DROPS = (0, 10, 20, 30, 40, 50, 60)


def build_placebo_frontier(anchor_cycle_returns_) -> tuple:
    """Run the vol-matched placebo at every pre-registered N.

    Returns `(frontier_df, cycle_returns_by_label)` - the summary panel AND each run's own cycle
    returns, the latter needed by `bootstrap_sharpe_diff_vs_control()` below (review: Draft 1
    referenced a "paired bootstrap CI" without retaining what it would need to compute one).

    Re-run in every notebook rather than loaded from a file so it is always on the same data
    snapshot as the variants it is compared against (vault data is downloaded fresh each run).
    About two minutes.
    """
    rows = []
    cycle_returns_by_label = {}
    for n in PLACEBO_DROPS:
        if n == 0:
            rows.append(anchor_panel.copy())
            cycle_returns_by_label["anchor"] = anchor_cycle_returns_
            continue
        label = f"vol_matched_drop_{n}"
        s, e, r = run_variant(label, vol_matched_drop_count=n)
        rows.append(panel(label, s, e, r, anchor_cycle_returns_))
        cycle_returns_by_label[label], _ = cycle_returns(e)
    frontier = pd.DataFrame(rows).set_index("label")
    frontier.loc["anchor", "drop_n"] = 0
    for n in PLACEBO_DROPS:
        if n:
            frontier.loc[f"vol_matched_drop_{n}", "drop_n"] = n
    return frontier.sort_values("cycle_vol"), cycle_returns_by_label


def _pareto_envelope(frontier: pd.DataFrame) -> pd.DataFrame:
    """Non-dominated subset of the frontier: sorted by volatility ascending, Sharpe strictly rising.

    Review: the raw seven placebo points are not necessarily a frontier - a lower-vol point can
    have a lower Sharpe than a higher-vol point (dominated), and linearly interpolating through a
    dominated point sets too weak a bar. This keeps only points where no quieter-or-equal point
    already achieved an equal-or-higher Sharpe, so the constraint always compares a candidate to
    the BEST Sharpe pure volatility avoidance achieved at or below the candidate's own volatility.
    """
    ordered = frontier.sort_values("cycle_vol")
    keep_labels, best = [], -np.inf
    for label, row in ordered.iterrows():
        if row["cycle_sharpe"] > best:
            keep_labels.append(label)
            best = row["cycle_sharpe"]
    return ordered.loc[keep_labels]


def placebo_sharpe_at(frontier: pd.DataFrame, vol: float) -> float:
    """Envelope Sharpe linearly interpolated at `vol`.

    Returns NaN outside the envelope's volatility range. Review: Draft 1 treated NaN here as an
    automatic PASS of constraint 7 (`ref != ref or ...`); `passes_constraints_v2` below now treats
    it as a FAIL - a candidate whose volatility the placebo design never covered is not evaluable
    against it and must not default to passing.
    """
    envelope = _pareto_envelope(frontier)
    xs, ys = envelope["cycle_vol"].to_numpy(), envelope["cycle_sharpe"].to_numpy()
    if len(xs) == 0 or vol < xs.min() or vol > xs.max():
        return float("nan")
    return float(np.interp(vol, xs, ys))


def nearest_placebo_label(frontier: pd.DataFrame, vol: float) -> str:
    """Label of the placebo run closest in volatility to `vol` (for the bootstrap below)."""
    return (frontier["cycle_vol"] - vol).abs().idxmin()


def bootstrap_sharpe_diff_vs_control(
    candidate_returns: pd.Series,
    control_returns: pd.Series,
    periods_per_year: float,
    block: int = 10,
    draws: int = 1000,
    seed: int = 0,
) -> tuple:
    """95% CI on (candidate cycle Sharpe - control cycle Sharpe), block-resampled in matched pairs.

    Both series are aligned by date and resampled together in matching contiguous blocks, so every
    draw compares the two strategies on the same market days rather than on independently
    resampled ones. Review: "paired bootstrap CI" was named in Draft 1's prose but never
    implemented for a Sharpe difference - `panel()`'s existing bootstrap is a CI on a mean paired
    RETURN difference, not this.
    """
    joined = pd.concat([candidate_returns.rename("c"), control_returns.rename("x")], axis=1).dropna()
    n = len(joined)
    if n < block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        sample = joined.iloc[idx]
        c_std, x_std = sample["c"].std(), sample["x"].std()
        if c_std <= 0 or x_std <= 0:
            continue
        c_sharpe = sample["c"].mean() / c_std * np.sqrt(periods_per_year)
        x_sharpe = sample["x"].mean() / x_std * np.sqrt(periods_per_year)
        diffs.append(c_sharpe - x_sharpe)
    if not diffs:
        return float("nan"), float("nan")
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def passes_constraints_v2(row: pd.Series, anchor: pd.Series, frontier: pd.DataFrame | None = None) -> bool:
    """Adoption rule v2: the seven constraints in 14-evidence-weighted-plan.md (Draft 2)."""
    ok = bool(
        row["cagr"] >= CAGR_FLOOR_V2
        and row["cycle_sharpe"] >= anchor["cycle_sharpe"] - SHARPE_NONINFERIORITY_TOL
        and row["cycle_vol"] <= anchor["cycle_vol"]
        and row["ulcer"] <= anchor["ulcer"] * (1.0 - ULCER_IMPROVEMENT_FRAC)
        and row["abs_invested_beta"] < anchor["abs_invested_beta"]
        and row["mean_invested"] >= INVESTED_FLOOR_V2
    )
    if ok and frontier is not None:
        ref = placebo_sharpe_at(frontier, float(row["cycle_vol"]))
        ok = ref == ref and row["cycle_sharpe"] >= ref + PLACEBO_MARGIN   # NaN ref -> FAIL, not pass
    return ok


def failing_constraints_v2(row: pd.Series, anchor: pd.Series, frontier: pd.DataFrame | None = None) -> str:
    """Names of the failed constraints, for the verdict table. Empty string if all pass."""
    failed = []
    if row["cagr"] < CAGR_FLOOR_V2: failed.append("CAGR < 20%")
    if row["cycle_sharpe"] < anchor["cycle_sharpe"] - SHARPE_NONINFERIORITY_TOL: failed.append("Sharpe non-inferiority")
    if row["cycle_vol"] > anchor["cycle_vol"]: failed.append("volatility")
    if row["ulcer"] > anchor["ulcer"] * (1.0 - ULCER_IMPROVEMENT_FRAC): failed.append("ulcer (not material)")
    if not row["abs_invested_beta"] < anchor["abs_invested_beta"]: failed.append("beta")
    if row["mean_invested"] < INVESTED_FLOOR_V2: failed.append("invested < 90%")
    if frontier is not None:
        ref = placebo_sharpe_at(frontier, float(row["cycle_vol"]))
        if not (ref == ref and row["cycle_sharpe"] >= ref + PLACEBO_MARGIN):
            failed.append("placebo (not evaluable)" if ref != ref else "placebo")
    return ", ".join(failed)


def hidden_cohort_reach(state_) -> pd.Series:
    """Goal 1 diagnostic: how much of the book went to vaults the incumbent could never score.

    Vault inception is the first raw poll in the Hyperliquid archive, as NB13 §2 computed it, read
    from its cache file. Reports position-count share (Draft 1's only measure), capital-weighted
    share (entry USD value, review finding: a count share treats a $5,000 position the same as a
    $50,000 one) and days-held-weighted share. Always returns the SAME schema, including when
    there are no positions or the life cache is missing entirely (review: Draft 1 returned a
    single-key Series with zero positions, which breaks any caller expecting the full schema), and
    reports how many held positions could not be matched to the cache rather than silently
    dropping them.
    """
    from pathlib import Path

    schema = ["positions", "unmatched_positions", "young_positions", "young_share",
              "young_capital_share", "young_days_share", "young_pnl_usd",
              "post_april_vaults_held", "youngest_entry_days"]
    life_path = Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet")
    if not life_path.exists():
        return pd.Series({k: float("nan") for k in schema})
    life = pd.read_parquet(life_path)

    rows, unmatched = [], 0
    for position in state_.portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        address = str(position.pair.pool_address).lower()
        if address not in life.index:
            unmatched += 1
            continue
        buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
        entry_capital = sum(t.get_value() for t in buys) if buys else 0.0
        age = (pd.Timestamp(position.opened_at) - life.loc[address, "inception"]).days
        days_held = ((position.closed_at or Parameters.backtest_end) - position.opened_at).days
        rows.append({
            "address": address, "age_at_entry": age, "entry_capital_usd": float(entry_capital),
            "days_held": max(days_held, 1),
            "post_april": bool(life.loc[address, "inception"] >= pd.Timestamp("2026-04-01")),
            "pnl_usd": float(position.get_total_profit_usd() or 0.0),
        })
    held = pd.DataFrame(rows)
    if not len(held):
        out = {k: 0.0 for k in schema}
        out["unmatched_positions"] = float(unmatched)
        out["young_share"] = out["young_capital_share"] = out["young_days_share"] = float("nan")
        out["youngest_entry_days"] = float("nan")
        return pd.Series(out)

    young = held[held["age_at_entry"] < Parameters.cagr_lookback_days]
    return pd.Series({
        "positions": float(len(held)),
        "unmatched_positions": float(unmatched),
        "young_positions": float(len(young)),
        "young_share": len(young) / len(held),
        "young_capital_share": (
            young["entry_capital_usd"].sum() / held["entry_capital_usd"].sum()
            if held["entry_capital_usd"].sum() > 0 else float("nan")
        ),
        "young_days_share": (
            young["days_held"].sum() / held["days_held"].sum()
            if held["days_held"].sum() > 0 else float("nan")
        ),
        "young_pnl_usd": float(young["pnl_usd"].sum()),
        "post_april_vaults_held": float(held.loc[held["post_april"], "address"].nunique()),
        "youngest_entry_days": float(held["age_at_entry"].min()),
    })


def late_period_ok(row: pd.Series, anchor: pd.Series) -> bool:
    return bool(row["late_cagr"] > 0 and row["late_ulcer"] < anchor["late_ulcer"])


def verdict_table(rows: list, anchor: pd.Series, frontier: pd.DataFrame) -> pd.DataFrame:
    """One row per run: the panel plus rule-v2 verdict columns and the CAGR sacrifice against the
    anchor (review 3c: the operator's trade-off should be reported explicitly on every row, not
    only implied by the CAGR floor). Sorted by cycle Sharpe.
    """
    df = pd.DataFrame(rows).set_index("label")
    df["placebo_ref"] = [placebo_sharpe_at(frontier, float(v)) for v in df["cycle_vol"]]
    df["cagr_sacrifice_pp"] = (anchor["cagr"] - df["cagr"]) * 100.0
    df["passes_v2"] = [passes_constraints_v2(r, anchor, frontier) for _, r in df.iterrows()]
    df["failed"] = [failing_constraints_v2(r, anchor, frontier) for _, r in df.iterrows()]
    df["late_ok"] = [late_period_ok(r, anchor) for _, r in df.iterrows()]
    return df.sort_values("cycle_sharpe", ascending=False)


def family_wise_reality_check(
    candidate_cycle_returns: dict,
    anchor_cycle_returns_,
    periods_per_year: float,
    block: int = 10,
    draws: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """White's reality-check-style max-statistic test over the full pre-registered candidate family.

    Review 3(f): plateau, leave-one-vault-out, the placebo constraint and the late period are
    useful robustness checks but do not correct for testing an adaptive family of ~25 backtests.
    This block-bootstraps the ANCHOR's own cycle returns `draws` times, and on each draw computes,
    for every candidate in `candidate_cycle_returns`, the Sharpe of (bootstrap anchor sample
    re-labelled as if it were that candidate's own return series) minus the anchor's actual Sharpe
    - i.e. the null distribution of "how much can noise alone improve on the anchor's Sharpe for
    the best of N candidates", matching the number of candidates actually tried. The candidate
    family's own MAXIMUM observed Sharpe improvement is then compared to this null's distribution
    of maxima: a family-wise p-value, not a per-candidate one.

    `candidate_cycle_returns` must be the COMPLETE pre-registered family for this to be valid -
    passing only the winners defeats the point.
    """
    anchor_r = anchor_cycle_returns_.dropna().to_numpy()
    n = len(anchor_r)
    anchor_sharpe = float(anchor_cycle_returns_.mean() / anchor_cycle_returns_.std() * np.sqrt(periods_per_year))
    observed = {
        label: float(r.mean() / r.std() * np.sqrt(periods_per_year)) - anchor_sharpe
        for label, r in candidate_cycle_returns.items() if r.std() > 0
    }
    observed_max = max(observed.values()) if observed else float("nan")

    rng = np.random.default_rng(seed)
    null_maxima = []
    for _ in range(draws):
        draw_max = -np.inf
        for _label in observed:
            starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
            idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
            sample = anchor_r[idx]
            if sample.std() <= 0:
                continue
            draw_max = max(draw_max, float(sample.mean() / sample.std() * np.sqrt(periods_per_year)) - anchor_sharpe)
        null_maxima.append(draw_max)
    p_value = float(np.mean([m >= observed_max for m in null_maxima])) if observed else float("nan")

    return pd.DataFrame({
        "metric": ["Family size", "Best observed Sharpe improvement over anchor",
                   "Null 95th percentile of the best-of-family improvement", "Family-wise p-value"],
        "value": [len(observed), observed_max, float(np.percentile(null_maxima, 95)) if null_maxima else float("nan"), p_value],
    })
```

`hidden_cohort_reach()` reads the life-statistics cache NB13 writes. If the file is missing, run
NB13 first (its section 2 rebuilds the cache in about a minute).

### How a build script splices these in

Template for every backtest notebook in this plan (`_build/build_16.py` shown; change the
number, id, heading and the analysis cells):

```python
import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE, \
    CELL14_REPLACEMENTS_EVIDENCE

HARNESS_EVIDENCE = (Path(__file__).parent / "harness_evidence.py").read_text()

HEADING = """# NB16 - ..."""      # see the notebook's own section below

cells = [md(HEADING)]
cells += common_prefix_cells(
    "16-backtest-evidence-selection",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_EVIDENCE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_EVIDENCE)
cells.append(md("# Backtest\n\n- Shared harness, then the evidence-track additions, then the placebo frontier.\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells += integrity_and_audit_cells()
cells.append(md("# Placebo frontier\n"))
cells.append(code('''anchor_cycle_returns, _ = cycle_returns(anchor_equity)
frontier = build_placebo_frontier(anchor_cycle_returns)
display(frontier[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer", "abs_invested_beta", "mean_invested"]])
'''))
# ... experiment cells ...
write_notebook(cells, TRACK_DIR / "16-backtest-evidence-selection.ipynb")
```

`common_prefix_cells` and `common_suffix_cells` already accept these keyword arguments
(`builder.py`, 2026-09-09). `research_backtest_cell()` replaces `harness_cell()` in the
research notebook NB14, exactly as NB13 does.

## Experiment track

Measurement first, the control second, then one mechanism per notebook, then the close-out.

### NB14 - research: decision-aligned screen of the evidence scores

**File**: `14-research-evidence-screen.ipynb`, built by `_build/build_14.py`.

**Question.** With only the information `decide_trades` had at each decision date, does ranking
by an evidence-weighted score pick better 30-day-forward baskets than the incumbent composite?
And does it actually reach the hidden cohort?

**Method.** Copy NB13 §6 verbatim from `_build/build_13.py` (the cells starting `import datetime`
and `K_MAIN = 6`, and the `summarise()` cell) and change only the rule set. Everything NB13 §6
corrected stays: features read at `when - ONE_BAR` (NB57 live parity), full baskets only, median
Martin beside mean return, and the capacity-filtered pool (`tvl >= CAPACITY_TVL`, $74,242) as the
version that counts.

Rules to screen, each as a dict `pair_id -> score` built inside the decision-date loop. Every rule
uses the SAME bounded [0, 1] form NB16 will trade (Draft 2 fix: Draft 1 screened an unbounded
statistic but traded a capped one - two different rankings):

| Rule label | Score read at `at` | Notes |
|---|---|---|
| `incumbent` | `cagr_sortino_weight` | reference row, as NB13 |
| `sortino_shrunk` | `sortino_shrunk_score` | the evidence score alone, no CAGR leg |
| `evidence_composite_0.6` | `evidence_composite` with `cagr_weight = 0.6` | the default parameters |
| `evidence_composite_0.3` | recompute in the loop as `0.3 * expanding_cagr_score + 0.7 * sortino_shrunk_score` | do not add a second indicator variant; read the two legs and blend inline |

All at `K = 6`. Drop NB13's `hidden cohort only` and `top 3` rows; they answered NB13's question,
not this one.

Add two columns to `summarise()` output, computed per rule from the top-6 at each date: `mean
top6 age (days)` and `share of top6 younger than 360d`. These are Goal 1's reach, measured at the
screen stage.

**Gate (pre-registered, descriptive - see below).** A score is marked PASS if, on the
capacity-filtered pool, it beats `incumbent` on **mean forward return in both regimes** and on
**median Martin in the dense regime**. This gate does **not** decide which scores are backtested:
Draft 2 fix (review: a noisy ~8-independent-observation screen must not be a hard admission bar).
**Every score in the table above is backtested in NB16 regardless of its gate result.** A score
that fails the gate is still run, but every one of its results is pre-labelled DIAGNOSTIC and is
explicitly ineligible for ADOPT, so the gate's role is to say which result an ADOPT verdict may
legitimately come from, not which experiments happen.

**Heading.** Verdict per score (PASS / FAIL the gate), the two reach columns, and the sparse-regime
caveat (15 dates against 66) restated.

### NB15 - backtest: the placebo frontier (CONTROL)

**File**: `15-backtest-placebo-frontier.ipynb`, built by `_build/build_15.py`.

**Question.** What Sharpe does pure volatility avoidance deliver at each level of volatility? This
is the line every later candidate must clear (constraint 7). It is a control and can never be
adopted, whatever it scores.

**Runs.** `frontier, cyc_returns_by_label = build_placebo_frontier(anchor_cycle_returns)` - the
seven `vol_matched_drop_count` runs, retaining both the summary panel AND each run's own cycle
returns (Draft 2 fix: the cycle returns are what `bootstrap_sharpe_diff_vs_control()` needs, and
Draft 1 did not say to keep them) - plus, for the chart only, the two cash overlays
`run_variant("target_vol_0.15", target_portfolio_vol=0.15)` and
`run_variant("target_vol_0.10", target_portfolio_vol=0.10)`, so the cash line and the
volatility-avoidance line are both visible. Store every run as a `(label, state, equity, returns,
panel)` tuple in a module-level `runs` list; every table and chart in this notebook and in
NB16-NB18 is built only from collected objects like this, never re-derived from a fresh
`run_variant()` call with the same label (which would silently re-run on a NEW data snapshot and
break the "same kernel, same snapshot" comparison the verdict table depends on).

**Outputs.**

1. `verdict_table()` over all nine runs (`frontier` plus the two cash overlays' panels), with the
   placebo and cash rows marked `role = "CONTROL"` in an added column.
2. Two Plotly scatter charts, `cycle_vol` on x: one with `cycle_sharpe` on y, one with `cagr` on y.
   The anchor is a distinct marker; the seven placebo points are joined by a line in
   `drop_n` order, with the non-dominated (Pareto) envelope subset (`_pareto_envelope(frontier)`)
   highlighted separately from the dominated points it excludes; the two cash overlays are a third
   series. Every later backtest notebook adds its own variants to this chart.
3. The equity curves of anchor, drop 30, drop 50 on one chart, log scale.

**Heading.** The frontier table (`drop_n` alongside `cycle_vol`, confirming the monotone order),
which points are dominated and excluded from the envelope, the Sharpe-vs-vol chart, and the answer
to "which drop-N passes rule v2 apart from the placebo constraint itself" - for the record only, as
those runs are the control. State the envelope's volatility range so later notebooks know where
`placebo_sharpe_at()` returns NaN (and therefore where constraint 7 fails outright).

### NB16 - backtest: evidence-weighted selection

**File**: `16-backtest-evidence-selection.ipynb`, built by `_build/build_16.py`.

**Question.** Does replacing the incumbent composite with an evidence-weighted one - so young
vaults are ranked once their record is strong enough - improve Sharpe at a CAGR above 20%?

**Runs.** Sizing unchanged (`inverse_variance`), with the early-availability fallback switched on
so a selected young vault can be funded. Rebuild the placebo frontier fresh in this notebook too
(`build_placebo_frontier()` again - a fresh `run_variant()` call, not a value carried over from
NB15, since every notebook downloads its own snapshot). For **every** score listed in NB14's table
(not only the ones that passed the gate - see NB14's gate section above), labelled with the score
name as a prefix so results from different scores can never collide (Draft 2 fix: Draft 1's
`"evidence_selection"` label was reused by every score):

```python
NB16_SELECTION_OVERRIDES = {}   # populated below; NB17/NB19 import this exact dictionary
runs = []   # (label, state, equity, returns, panel) - the only source for every table below

def run_and_record(label, **overrides):
    s, e, r = run_variant(label, **overrides)
    p = panel(label, s, e, r, anchor_cycle_returns)
    runs.append((label, s, e, r, p))
    return s, e, r, p

SCORES = {
    "sortino_shrunk": dict(selection_score_indicator="sortino_shrunk_score"),
    "evidence_composite_06": dict(selection_score_indicator="evidence_composite", cagr_weight=0.6),
    "evidence_composite_03": dict(selection_score_indicator="evidence_composite", cagr_weight=0.3),
}
GATE_PASSED = {...}   # from NB14's gate table, e.g. {"sortino_shrunk": True, "evidence_composite_06": False, ...}

for score_name, score_overrides in SCORES.items():
    common = dict(require_scored_candidates=True, inverse_vol_min_periods=45, **score_overrides)
    prefix = f"{score_name}"

    # Centre point.
    run_and_record(f"{prefix}__centre", **common)

    # Plateau: every one-step neighbour of the centre, one parameter at a time.
    neighbours = [
        ("t_cap_2",       dict(evidence_t_cap=2.0)),
        ("t_cap_4",       dict(evidence_t_cap=4.0)),
        ("prior_30",      dict(evidence_prior_strength=30)),
        ("prior_90",      dict(evidence_prior_strength=90)),
        ("min_events_10", dict(evidence_min_events=10)),
        ("min_events_30", dict(evidence_min_events=30)),
    ]
    if "cagr_weight" in score_overrides:   # only the composite scores have a CAGR leg to move
        neighbours.append(("cagr_weight_03", dict(cagr_weight=0.3 if score_overrides["cagr_weight"] == 0.6 else 0.6)))
    for label, override in neighbours:
        run_and_record(f"{prefix}__{label}", **common, **{k: v for k, v in override.items() if k not in common or common[k] != v})

    # NB13 §6's naive control, reproduced with this notebook's own indicators: the unshrunk
    # statistic (evidence_prior_strength effectively removed) at the SAME admission threshold,
    # so the value the shrinkage step adds is visible directly.
    run_and_record(f"{prefix}__no_shrink", **{**common, "evidence_prior_strength": 1})

    # Sizing barrier isolated: centre point with the early-vol fallback OFF, to show what NB13's
    # second barrier costs on its own.
    run_and_record(f"{prefix}__no_early_vol", **{**common, "inverse_vol_min_periods": 90})
```

`cagr_weight` neighbours only swap between 0.3 and 0.6 (NB92 fixed 0.6 as the top of its searched
range and 0.7 was never established, so moving up would be a new search, not a plateau check) and
only apply to the two `evidence_composite_*` scores - `sortino_shrunk` alone has no CAGR leg to
move.

**Outputs.**

1. `verdict_table()` over the anchor, the frontier and every run in `runs`. Columns to show:
   `cagr, cycle_sharpe, cycle_vol, ulcer, abs_invested_beta, mean_invested, placebo_ref,
   cagr_sacrifice_pp, late_cagr, passes_v2, failed, late_ok`. Add a `diagnostic_only` column: `True`
   for every row whose score name is not in `GATE_PASSED` or is `False` there.
2. Per-score plateau table: the `__centre` row and its neighbours, `passes_v2` per row, and one
   line `plateau = all(neighbours pass)`, for each of the three scores.
3. `hidden_cohort_reach()` for the anchor and every `__centre` row, side by side.
4. Age-at-entry histogram, anchor against every `__centre` row.
5. For every `__centre` row that is NOT `diagnostic_only` and passes v2 and whose plateau holds:
   leave-one-vault-out, `run_and_record(f"{prefix}__without_top_vault", masked={largest_contributing_vault(state)}, **common)`,
   and `bootstrap_sharpe_diff_vs_control()` against the nearest placebo point in `cyc_returns_by_label`.
   Otherwise print which condition failed and skip that score.
6. The frontier scatter from NB15 with every run in `runs` overlaid, coloured by score name.

**Verdict, per score.** ADOPT only if: the score's NB14 gate passed (`diagnostic_only == False`),
the centre passes v2, every neighbour passes v2, leave-one-vault-out passes v2, and `late_ok` is
True. Otherwise REJECT and name the first failure; if `diagnostic_only` is the only reason, say so
explicitly rather than implying the mechanism failed on its merits.

**What to carry forward.** Set `NB16_SELECTION_OVERRIDES` to the winning `__centre` run's
`**common` dictionary if any score reached ADOPT; otherwise to the empty dict `{}` (anchor
selection). Print this exact dictionary in the notebook's output (not only in a table) so NB17 and
NB19 can copy it verbatim - the plan does not track state between notebooks any other way, since
each notebook re-downloads its own snapshot. NB18 uses `sortino_shrunk_score` for its core sleeve
regardless of NB16's verdict - the sleeve is a different mechanism (see NB18) and the whole-book
selection's failure does not settle whether the same score works as a *core-only* rule.

### NB17 - backtest: evidence-weighted sizing

**File**: `17-backtest-evidence-sizing.ipynb`, built by `_build/build_17.py`.

**Question.** Holding selection fixed, does sizing by evidence of profit rather than by inverse
variance improve Sharpe? NB77 found inverse variance hands the biggest slots to a quiet cohort of
small losers; `inverse_ulcer` and `inverse_downside` (NB07) made that worse. This is the first
sizing rule in the track that can give a quiet *loser* nothing.

**Runs.** `SELECTION = NB16_SELECTION_OVERRIDES` - copy the exact dictionary NB16 printed. If it is
`{}` (no ADOPT in NB16), every run below is on the anchor's incumbent selection; sizing is compared
on its own merits either way, and every row here is `diagnostic_only = SELECTION == {}` for the
verdict table, matching NB16's convention:

```python
runs = []
for method in ("evidence", "blend", "equal"):
    run_and_record(f"sizing_{method}", weighting_method=method, **SELECTION)
# Plateau on the floor, for the evidence method only.
for floor in (0.0, 0.5):
    run_and_record(f"sizing_evidence_floor_{floor}", weighting_method="evidence", weight_floor_fraction=floor, **SELECTION)
```

`equal` is the sizing null: if evidence sizing does not beat equal weight it is not doing
anything. `blend` (inverse-vol times composite) is the existing method closest in spirit. The
centre point is `sizing_evidence` with the default `weight_floor_fraction = 0.25`; its neighbours
are the floor at 0.0 and 0.5.

**Outputs.** As NB16 items 1, 3, 5 and 6 (drop item 2's per-score loop; there is one centre point
here, `sizing_evidence`), plus a table of the mean realised weight of the largest position per
cycle for each method (evidence sizing is expected to concentrate; the 33% concentration cap must
be visibly binding or not).

**Verdict.** As NB16, `diagnostic_only` following `SELECTION`'s provenance. If `sizing_evidence`
fails but `sizing_equal` passes, that is a finding about inverse variance, not about evidence; say
so and REJECT.

### NB18 - backtest: core and satellite sleeves

**File**: `18-backtest-core-satellite.ipynb`, built by `_build/build_18.py`.

**Question.** If a single score cannot land the trade-off, can an explicit split? The core sleeve
is ranked and sized by `sortino_shrunk_score`; the satellite is the incumbent selection and sizing;
`core_fraction` is the dial. This is also the notebook that produces the CAGR-against-Sharpe curve
the operator asked for, whether or not any point on it passes rule v2. `diagnostic_only = True` for
every row here unconditionally: `sortino_shrunk_score` is being tried as a sleeve regardless of
whether it separately reached ADOPT in NB16 (a valid experiment - see the Question above), so no
row in this notebook may be reported as ADOPT-eligible from this notebook's own evidence alone; a
core mechanism can only reach ADOPT if NB19's close-out re-examines it as a fully independent
candidate with its own plateau and leave-one-vault-out, which NB19 does.

**Runs.** The dial curve varies only `core_fraction` at a FIXED `core_assets = 4` (Draft 2 fix: the
grid must not vary two things and call the result one curve). `core_assets = 6` (no satellite) is
run once, separately, and reported alongside the curve rather than as its endpoint - it is a
different structural point (`satellite_assets = 0`), not `core_fraction = 1.0` at `core_assets = 4`:

```python
runs = []
common = dict(inverse_vol_min_periods=45, core_score_indicator="sortino_shrunk_score")

# The dial curve: core_assets fixed at 4, core_fraction swept including its own endpoints.
CURVE_FRACTIONS = (0.0, 0.5, 0.7, 0.85, 1.0)
for fraction in CURVE_FRACTIONS:
    if fraction == 0.0:
        run_and_record("core_0.0_n4", **common)   # core_fraction=None is anchor behaviour; label it as the curve's zero point
        continue
    run_and_record(f"core_{fraction}_n4", core_fraction=fraction, core_assets=4, **common)

# Plateau around the centre (0.7, 4): core_assets moved one step either way.
for n_core in (3, 5):
    run_and_record(f"core_0.7_n{n_core}", core_fraction=0.7, core_assets=n_core, **common)

# Separate structural point: no satellite at all. Not part of the core_assets=4 curve.
run_and_record("core_1.0_n6_no_satellite", core_fraction=1.0, core_assets=6, **common)
```

The centre point for plateau/ADOPT purposes is `core_0.7_n4`; its neighbours are `core_0.5_n4`,
`core_0.85_n4` (from the curve sweep) and `core_0.7_n3`, `core_0.7_n5` (from the dedicated plateau
loop).

**Outputs.**

1. `verdict_table()` over `runs`, with `diagnostic_only = True` on every row.
2. **The dial curve**: `cagr` and `cycle_sharpe` against `core_fraction`, `core_assets` fixed at 4
   (`CURVE_FRACTIONS` only), with the anchor at `core_fraction = 0`. One chart, two y-axes.
   `core_1.0_n6_no_satellite` is plotted as a separately labelled point, explicitly not on the line.
3. Plateau around `core_0.7_n4` (informational, since every row is DIAGNOSTIC here - see NB19 for
   the mechanism this feeds into); leave-one-vault-out on the centre regardless of whether it
   passes v2, so NB19 has it available; frontier overlay.
4. `hidden_cohort_reach()` for every run - the core sleeve is where young vaults should appear if
   they appear anywhere.
5. Per-sleeve attribution for the centre point, read from `state.visualisation.calculations`
   (`core_ids`, `satellite_ids`, `core_fraction_realised` per cycle - Draft 2 fix: Draft 1 assumed
   `core_fraction` was what was actually held; it is only the pre-normalisation target): P&L, mean
   realised weight and mean `sortino_shrunk_score` at entry of the core names against the
   satellite names, and a chart of `core_fraction_realised` over time against its `core_fraction`
   target.

**Verdict.** Every row REJECT/DIAGNOSTIC by construction per the Question section above. Note in
the heading, whatever the realised sleeve weights show, the CAGR the operator would give up at
each `core_fraction` and the Sharpe bought for it, from the dial curve; that table is the practical
output of this notebook even though nothing here is adopted from it directly - NB19 decides whether
the core mechanism itself reaches ADOPT.

### NB19 - close-out

**File**: `19-backtest-closeout.ipynb`, built by `_build/build_19.py`.

Re-runs (do not load from earlier notebooks; same-snapshot rule) the anchor, the placebo frontier,
and every `__centre` run from NB16, NB17's `sizing_evidence`, and NB18's `core_0.7_n4`, in one
kernel, collected into the same `runs = [(label, state, equity, returns, panel), ...]` pattern
NB15/NB16 use. This is also where NB18's core mechanism gets its one chance at ADOPT (see NB18's
Question section): its centre point is re-run here with its own leave-one-vault-out and plateau
already available from NB18's own robustness section, re-verified rather than re-derived.

1. The combined `verdict_table()` - one row per run across the whole plan, `diagnostic_only`
   carried through from each source notebook's convention.
2. The frontier chart with every run in the plan overlaid: this is the figure that shows whether
   anything sits above the volatility-avoidance line.
3. **Family-wise reality check** (review 3f - plateau, leave-one-vault-out, the placebo constraint
   and the late period are useful per-candidate robustness checks but do not correct for having
   tried the full adaptive family): `family_wise_reality_check(candidate_cycle_returns,
   anchor_cycle_returns, periods_per_year)`, where `candidate_cycle_returns` is EVERY `__centre` /
   `sizing_*` / `core_*` run's own cycle returns from NB16, NB17 and NB18 - the complete
   pre-registered family, not only the ones that individually passed v2. Report the family-wise
   p-value plainly: it will have low power on ~25 candidates and a ~125-cycle window, so it is
   there to prevent overclaiming, not to itself pass or fail anything. A candidate that clears
   every per-candidate constraint but whose family-wise p-value is unremarkable (say, above 0.20)
   should be reported as such in the verdict - "clears the individual bar, but so would the best
   of this many tries by chance" - rather than silently only stating the individual result.
4. For each ADOPT winner (there may be none): the NB83 random-removal null (`luck_ratio` is
   already in the panel; add a 500-draw distribution of CAGR with 5 random positions removed and
   the winner's rank in it), the late-period panel, leave-one-vault-out (re-verified, not assumed
   from the source notebook), and a fresh `hidden_cohort_reach()`.
5. The equity curves of anchor, every `__centre` / `sizing_evidence` / `core_0.7_n4` run and any
   winner, log scale, on one chart, with the 2026-04-01 regime break and the 2026-07-01
   late-period start marked.
6. **Prospective shadow specification**, written whether or not there is a winner: the frozen
   parameter set that would be shadow-run (the exact `**overrides` dictionary, printed literally,
   the same way NB16 prints `NB16_SELECTION_OVERRIDES`), an unchanged anchor run as the
   comparator on the same decision dates, the minimum number of decision cycles before it may be
   compared to the live book (pre-register 45 cycles, i.e. 90 days), realised deposit
   availability, pool-cap fills and turnover as part of what is measured (not assumed away), and
   the rule-v2 thresholds it would have to meet on that period, treated as monitoring evidence
   rather than a deployment proof at 45 cycles (review 2(65), 3d). This replaces any claim about
   the retired hold-out.

**Verdict.** The plan's overall verdict, one of: ADOPT `<label>` (with its family-wise p-value
stated alongside); or NOTHING ADOPTED, with the dial curve from NB18 as the answer to the
operator's question ("this is what CAGR buys at each setting, and none of it clears the placebo").

## Order of execution and dependencies

```
NB13 (exists)  -> writes /tmp/hyperliquid-lower-vol-vault-life-stats.parquet, needed by hidden_cohort_reach()
NB14           -> gate for NB16's score set
NB15           -> the frontier; can run in parallel with NB14
NB16           -> depends on NB14's gate
NB17           -> depends on NB16's verdict (selection to hold fixed)
NB18           -> depends on NB16's centre-point parameters; can run in parallel with NB17
NB19           -> after all of the above
```

Build all six `build_NN.py` scripts before running any notebook, so a splice-anchor failure
(`builder.cell14()` asserts every "old" string is present) surfaces before compute is spent.

## Definition of done

- [x] `_build/blocks_evidence.py` and `_build/harness_evidence.py` exist and match this file.
- [x] `_build/build_14.py` ... `build_19.py` exist; each runs without an assertion error.
- [x] Every backtest notebook's anchor row matches NB12's (rule 5): CAGR 37.8971%, ulcer 1.7964%,
      cycle Sharpe 2.159792, 578 trades, $186,746 final equity - checked in every notebook, not
      only asserted in this file.
- [x] NB14 heading states which scores passed the gate: `sortino_shrunk` PASS; both composites FAIL.
- [x] NB15 heading states the frontier's volatility range (0.0769 to 0.1492) and flags that
      `vol_matched_drop_30`'s spike (Codex-reviewed and Draft-2-fixed non-dominance handling)
      dominates the anchor's own point.
- [x] NB16, NB17, NB18 headings each carry a verdict word (all REJECT), the plateau result and the
      `hidden_cohort_reach()` numbers for anchor and centre.
- [x] NB18 heading carries the dial curve table (CAGR and Sharpe at each `core_fraction`), and
      found and fixed a real bug (`state.visualisation.calculations` collision with the framework's
      own writes) before trusting the result.
- [x] NB19 heading carries the overall verdict (NOTHING ADOPTED), the frontier overlay and the
      shadow specification, plus a family-wise reality check (p = 1.000) the original plan's
      checklist did not list but Draft 2 added per the Codex review.
- [x] The `Status` line at the top of this file is updated to EXECUTED with the overall verdict.
      NB12's comparison notebook was not extended and no NB20 was added: NB19's own combined
      verdict table already carries the full 41-candidate comparison NB12 would otherwise need to
      be extended to show, and the whole plan is a separate mechanism from the NB03-NB12 track
      NB12 compares, so folding them into one table would mix two different objectives (CAGR
      floor 30% there, 20% here) rather than clarify anything.
- [x] One commit per notebook on `research/hyperliquid-lower-vol` (plus one for Draft 2 itself and
      one mid-NB18 fix commit for the SLEEVE_LOG bug).

## What this plan does not do, on purpose

- It does not re-institute a hold-out. The track has none since 2026-09-09 and the window is too
  short to carve one out that would survive a 60-day cold start plus a 90-day evidence window.
  The prospective shadow in NB19 is the out-of-sample claim, deferred to live data.
- It does not retry `positive_window_share`, `min_window_sortino` or `downside_score`. NB12
  showed each made the ulcer index worse; the reason (rewarding absence of noise) is understood.
- It does not search `cagr_weight` above 0.6 or `max_assets_in_portfolio`; both were settled in
  NB92 / NB68 and are outside this plan's question.
- It does not examine the 191 deposit-closed exclusions NB13 flagged. That is a different kind of
  missing vault and a separate plan.

## Review log

- **Draft 1**. Written from the NB12 comparison panel and NB13's age-barrier audit. Design
  choices: a t-statistic rather than a shortened window as the admission mechanism; an
  evidence-shrunk expanding CAGR leg rather than a dropped one (NB31); a Sharpe-ranked, 20% CAGR
  floor, 90% deployment objective; the vol-matched placebo promoted from a control run to a
  constraint at matched volatility; a core/satellite sleeve as the explicit dial.
- **Smoke test of Draft 1's own code**, run before sending it for review: spliced the code through
  the real builder and ran it. Anchor parity held, but a single arbitrary run of the core/satellite
  mechanism lost -$12,983 net, and its single worst position (-$28,990 in 6 days) had been entered
  at the admission score's maximum on 45 observations. The score correlated -0.41 with realised
  P&L across all 75 positions in that run - see `_build/smoke_test_finding.md`.
- **Codex CLI review** (`gpt-5.6-terra`, high reasoning effort,
  [14-evidence-weighted-plan-codex-review.md](14-evidence-weighted-plan-codex-review.md)). Found,
  independently, that the same admission statistic mixed an inconsistent sample (fresh-only `n`
  against a mean/downside computed over stale-inclusive calendar rows) and that its cap erased the
  sample-size discrimination a t-statistic exists to provide; that NB14 screened a different form
  of the score than NB16 would trade; that the placebo constraint's NaN handling defaulted to a
  pass rather than a fail off the frontier's range; that the core/satellite sleeve could evict a
  hold-protected position and never measured its own realised weights; and that plateau,
  leave-one-vault-out, the placebo constraint and the late period do not, together, correct for
  the size of the candidate family actually being tried. One claim (a `drop_n` mislabelling
  attributed to `build_placebo_frontier()`'s assign-then-sort order) was checked empirically
  against actual pandas semantics and did not reproduce; it was not applied.
- **Draft 2** (this file). Replaces the admission statistic with `sortino_shrunk_score`
  (event-time sampling, autocorrelation-discounted `n`, cross-sectional shrinkage) as one bounded
  form used identically everywhere; fixes the CAGR-leg shrink order and the `inverse_vol_early`
  gating; reframes the Sharpe constraint as non-inferiority plus a material ulcer improvement
  rather than a Sharpe race; fixes the placebo constraint's NaN handling and replaces its raw
  sort-and-interpolate with a non-dominated envelope; adds a genuine block-bootstrap of the Sharpe
  difference against the nearest placebo point; reserves hold-protected positions before splitting
  into sleeves and records realised sleeve weights; makes NB14's gate descriptive rather than a
  hard admission bar, uniformly across NB16 and NB18; and adds a family-wise reality check to
  NB19. Verified by re-running the exact smoke test that found Draft 1's bug: the correlation moved
  from -0.41 to +0.11 and the same arbitrary run's net P&L moved from -$12,983 to +$13,821 (see
  `_build/verify-plan14-draft2.ipynb`). Full change list under "Draft 2 changes" above.
