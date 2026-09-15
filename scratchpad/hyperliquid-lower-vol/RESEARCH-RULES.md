# Research rules for the hyperliquid-lower-vol track

Supersedes the anchor-relative adoption rules v1-v4 used in NB03-NB26. Set by the operator on
2026-09-14. Every plan and notebook from NB27 onward uses these.

## Objective

**Maximise cycle Sharpe by selecting stable vaults, not lucky and volatile ones, holding as many
distinct vaults as the Sharpe allows.**

The second clause is not decoration. Portfolio Sharpe is an OUTCOME, and this track has repeatedly
produced good outcomes for bad reasons: `drop_30` reached the highest Sharpe in either batch and
NB26 showed 98% of its edge was one vault; a purely random removal of nine vaults ranks seventh of
57 by Sharpe, ahead of most mechanisms we designed on purpose. A rule that gates only on the
outcome cannot tell those apart from a mechanism that works. So the gates below constrain THREE
things: the outcome, the character of the book that produced it, and whether the selection signal
demonstrably predicts stability at all.

The third clause conflicts with the first in this universe, and the rule says below how that is
resolved. It is stated as a clause rather than a separate objective because the evidence is
unambiguous that wider is worse here.

No return floor. The operator removed it on 2026-09-14 on the grounds that we do not know what
vaults the universe will contain in future, so a floor calibrated to today's opportunity set is
arbitrary. There is no requirement to match or beat
[02-better-format.ipynb](02-better-format.ipynb) on any metric. The anchor is now a REFERENCE
POINT, reported on every table so results stay comparable with NB03-NB26, and it is not a bar.

Metrics are computed on the strategy's own two-day cycle clock, never on a zero-filled daily one.

## What changed, and why it matters

Rules v1-v4 required Sharpe no worse than the anchor's, volatility no worse, a 15% ulcer
improvement, beta below the anchor's and at least 90% of capital deployed. Those five gates
rejected almost everything, and two of them were rejecting candidates the operator would have
accepted.

Dropped: Sharpe non-inferiority, the volatility ceiling, the ulcer-improvement requirement, the
beta ceiling, and the deployment floor. Concentration and cash are both acceptable if they buy
Sharpe.

Also dropped: the 20% CAGR floor. Checked before removing it, across all 57 runs of both
batches: **nothing has high Sharpe and low return.** No run anywhere has Sharpe above 1.8 with
CAGR below 20%. The floor was never binding, so removing it admits nothing it was holding back.

## Four consequences the operator should know

1. **Cash overlays are now out, not in.** They were rejected under v1-v4 by the deployment floor,
   which has gone - but they reduce Sharpe here, so the new objective rejects them on the merits.
   Scaling a book by a constant fraction leaves Sharpe unchanged in theory; this implementation is
   dynamic and de-levers after volatility spikes, which on this data means selling after
   drawdowns. Measured: anchor 2.1598, `target_vol_0.15` 1.8488, `target_vol_0.10` 1.5335, falling
   monotonically as more cash is held.
2. **In this universe Sharpe IS return, so maximising it will not lower volatility.** Across all
   57 runs, cycle Sharpe correlates **+0.985** with CAGR and only **-0.270** with cycle
   volatility. Volatility across every candidate ever built spans a narrow 0.138 to 0.169, while
   CAGR spans -0.23 to 0.49. Selection mechanisms move return; they barely move volatility. The
   only thing in this track that has materially lowered volatility is holding cash - 0.105 at the
   15% target and 0.085 at the 10% - and that lowers Sharpe. **So the operator can have lower
   volatility or higher Sharpe, not both, until a mechanism exists that changes volatility without
   changing deployment.** Nothing tested so far does.
3. **No selection mechanism has ever changed concentration, and the two things that do are
   expensive.** Measured across every variant in both batches: mean holdings 6.00, largest
   single weight 33.1-33.2%, Herfindahl 0.242-0.244, 32 to 34 distinct vaults over the window.
   Those numbers are identical to three decimal places whether the mechanism is the drop family,
   complementary selection, the Sortino swap or the anchor itself. Concentration is set by
   `max_assets_in_portfolio = 6` and by inverse-volatility sizing, not by which vaults are chosen.
   The only levers that move it were tested in batch 1 and cost heavily: eight names gives 11.18%
   CAGR and ten names 1.15%, against the anchor's 37.90%; capping position concentration at 0.20
   gives 27.21% and at 0.25 gives 28.78%. **So "as many vaults as possible" is bounded at six
   unless the operator accepts a 9 to 37 point return cost.**
4. **Sharpe is below this window's resolution.** NB03a put the minimum detectable Sharpe
   difference at about 2.50 on 125 two-day cycles. The spread across every candidate ever run is
   roughly 1.5 to 2.7. Ranking runs by Sharpe is therefore ranking on noise, and the new objective
   makes that the explicit selection criterion. **The robustness gates below are now doing all the
   work that the anchor-relative constraints used to do, and they are tightened accordingly.**

## Gates

A candidate is ADOPTED (= admitted to the prospective shadow protocol, never deployed on this
evidence alone) only if every one of these holds. Gates 1-2 are sanity and survival, 3-5 are the
"stable, not lucky" clause of the objective, and 6-8 are the anti-overfitting machinery.

1. **Positive return.** `cagr > 0`. Not a performance bar, a sanity one: Sharpe is not
   meaningful for a losing strategy and the ratio is uninterpretable when the numerator is
   negative.
2. **Single-vault survival.** Re-simulate with the candidate's largest total-P&L contributor
   masked. The masked run must retain at least 70% of the unmasked run's cycle Sharpe, and must
   still satisfy gate 1. The 70% is pre-registered here, before any run: the anchor retains
   roughly 62% of its CAGR under this test and the best candidate retains 49%, so the bar sits
   deliberately above both. This is a GATE, evaluated before the
   plateau, not a closing robustness note. NB26 established that masking one vault takes the
   anchor from 37.90% to 23.90% and takes the best candidate's edge from 11.10 points to 0.22;
   single-name dependence is the binding property of this book.
3. **The book held stable vaults.** Capital-weighted over the realised holdings, the candidate's
   vaults must have had LOWER own realised volatility than the anchor's did, and LOWER own
   event-concentration - the share of each vault's trailing return delivered by its best five
   days, from `residual_event_concentration`. A mechanism that reaches a high portfolio Sharpe
   while holding vaults that are individually more volatile or more spiky than the anchor's has
   not done what the objective asks, whatever its Sharpe.
4. **The result was not luck.** `luck_ratio` at least the anchor's - note it removes the best
   five CYCLES, not the best five days, because `panel()` computes it on the two-day cycle
   clock - and `top5_gross_share` no more
   than the anchor's. Both are already computed by `panel()`. **Note the absolute levels are poor
   for everything including the anchor**: the anchor's `luck_ratio` is 0.1459, meaning removing
   its best five days costs far more than removing five random ones, and its top five positions
   deliver 60.8% of gross profit. Passing this gate means "no worse than the anchor", not "robust".
   Report the absolute values alongside, and do not describe a passing candidate as luck-free.
5. **The selection signal predicts stability, measured outside the backtest.** Before the
   mechanism is backtested, a research notebook must show that its score, read at a decision
   timestamp, rank-correlates positively across candidates with those vaults' REALISED FORWARD
   stability - forward volatility, forward downside deviation and forward event-concentration over
   the following 30 days. Not forward return. If the signal does not predict forward stability,
   the mechanism is not selecting stable vaults and any portfolio Sharpe it achieves is
   incidental. Report Spearman correlations with vault-clustered intervals, and state the sign and
   magnitude in the heading. A mechanism failing this gate is REJECTED without a backtest.
6. **Sharpe plateau.** Both pre-registered neighbours must clear gate 1, and the centre's cycle
   Sharpe must be within 0.25 of each neighbour's. This is a FLATNESS test, not a superiority
   test: it rejects a centre that stands above its own neighbours, which is what a spike looks
   like. `drop_30` at 2.747 against `drop_35` at 2.301 fails it by 0.45, correctly.
7. **Sub-period sign.** Positive CAGR in all three segments: sparse (to 2026-03-31), dense (April
   to June) and late (July onwards). A candidate that earns in one regime only has not been shown
   to work.
8. **Diversification no worse than the anchor.** Over the realised holdings: mean holdings count
   at least the anchor's 6.00, largest mean weight no more than its 0.3316, Herfindahl no more
   than its 0.2436, distinct vaults held over the window at least its 33, and `top_vault_pnl_share`
   no more than the anchor's. This is a floor, not a target. Nothing yet built moves any of these,
   so in practice it excludes only mechanisms that make concentration WORSE.
9. **Null.** Beat all draws of the mechanism's own information-destroying null on cycle Sharpe,
   with at least ten draws. The null must preserve the mechanism's structure and destroy only its
   ranking information. **Assert that the draws actually differ and print the count of distinct
   draws** - NB26's null was one draw repeated ten times and the tell, `null_median == null_best`,
   was visible and missed.

## Resolving the conflict between Sharpe and diversification

They trade off directly here and Sharpe cannot arbitrate, because this window's minimum detectable
Sharpe difference is about 2.50 while the entire candidate spread is 1.5 to 2.7. So:

**When two candidates' cycle Sharpe differ by less than 0.25, prefer the more diversified one.**
This is an OPERATOR INDIFFERENCE BAND - a decision policy, pre-registered before any run under
these rules. It is NOT a statistical resolution claim: a minimum detectable difference near 2.50
says this sample is poorly powered for differences far larger than 0.25, and does not identify
0.25 as a boundary between signal and noise. Realised diversification measures also carry
sampling uncertainty despite being computed without a model. Where statistical evidence about a
Sharpe difference is wanted, use the paired bootstrap interval and say so.

"More diversified" means Pareto dominance across the five measures of gate 8: no worse on all
five and strictly better on at least one. If neither candidate dominates, the comparison is
unresolved and both are carried.

Above 0.25 the higher Sharpe wins, and the diversification gate still applies as a floor. A
candidate that buys Sharpe by concentrating further than the anchor is rejected outright rather
than traded off.

## Reported on every row, never gated

`cycle_sharpe`, `cagr`, `cycle_vol`, `ulcer`, `max_dd`, `abs_invested_beta`, `mean_invested`, the
three sub-period CAGRs and ulcers, `luck_ratio`, `top5_gross_share`, `top_vault_pnl_share`,
`lovo_sharpe_retention`, the two capital-weighted held-book character measures from gate 3, and
the five diversification measures from gate 8. Also the anchor's own values, for continuity with NB03-NB26.

Paired block-bootstrap intervals against the anchor are reported for context. They are not a gate,
because the window cannot resolve the differences involved and pretending otherwise was the
mistake constraint 7 made.

## What is retired

- **Constraint 7 in all its forms.** v3 compared against the best observed volatility-matched
  control at or below the candidate's volatility; NB24 found the bar was 2.847, set entirely by
  the `drop_30` spike, which the anchor itself fails at 2.160, and zero of thirteen rows cleared
  it. v4's proposed median fix is not adopted either: with no anchor-relative objective there is
  nothing for it to do. The vol-matched family is still run as a REFERENCE family and reported.
- **The vol-matched family as a "control".** NB21 and NB26 showed 70.9% of its removals at N = 30
  have no volatility estimate at all and that half is exactly inert. Call it the
  data-availability drop family and treat it as a set of candidates, not a placebo.

## Amendments for plan 34, recorded 2026-09-16 before NB34 was built

These are EVIDENCE-INFORMED revisions made after NB28-NB33 exposed defects in the gates as
written. They apply to NB34 onward. Verdicts reached under the original text stand as recorded
and are not revised. See [34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md)
for the evidence behind each.

- **A1. Gate 5 targets.** Forward volatility and forward downside variation only. Forward event
  concentration is dropped as a TARGET because its measurement is compromised on this archive
  (raw share bounded below by 5/n; path inside unobserved gaps not identifiable) - a narrowing of
  the objective, not a claim that concentration is unpredictable. Simultaneous lower bound of
  zero over the family of 2 x signals screened, shared date-block and vault-cluster resamples,
  complete 30-day forward windows only.
- **A2. Gate 5 return clause: typical-vault return non-inferiority.** Per date, the median
  forward 30-day log NAV return of the retained set minus that of the excluded set at the
  mechanism's own exclusion, averaged over dates, same bootstrap; lower bound must exceed
  -0.005. Protects against "stable because dead" only; the share of retained and excluded
  vaults with forward return below -0.5 log is reported beside it as a diagnostic. Replaces the
  mean-based 5 pp annualised clause of plan 28 Draft 3, whose half-width was 20-60x its margin.
- **A3. Gate 8 tolerance.** `mean_holdings` at least 5.95 rather than at least 6.00: a five-name
  book on no more than one decision in twenty. A policy choice about breadth, stated as one.
- **A4. Gate 3 scope.** The concentration leg's 180-row trailing indicator is not identifiable
  before late September 2026 (mostly forward-filled history), so gate 3 is scored on its
  volatility leg alone, on decisions from 2026-04-01; both concentration indicators are reported
  as diagnostics with coverage. Fewer than 40 evaluable dates means unevaluable, which FAILS.
- **A5. Gate 9 count and scope.** At least nineteen distinct draws (add-one p = 0.05). The null
  permutes finite signal values within each date and so destroys temporal persistence as well
  as ranking; the null runs' turnover and basket persistence are reported beside the centre's,
  and a failure means "did not clear this hurdle", not "selects on no information".
- **A6. Fee differential.** The net signed discrepancy between the engine's stored redemption
  fee and `10% x max(gross - released cost basis, 0) + 10 bps`, candidate minus anchor, must be
  below 0.25 of the candidate-minus-anchor final-equity difference in absolute value for a
  SHORTLIST. Above that the verdict is DIAGNOSTIC.
- **Scope.** Gate 5 is evaluated on decisions on or after 2026-04-01 only; pre-break decisions
  are screened as a diagnostic.
- **Vocabulary.** From plan 34, the passing verdict is SHORTLIST (admission to the frozen
  prospective specification), not ADOPT.

## Standing method rules, unchanged from the previous plans

1. Never select or tune towards a vault by name.
2. Never change a pre-registered threshold after seeing a result. Record a badly placed one and
   leave it. Changing a rule BEFORE a plan runs, with the reason stated, is the legitimate case -
   this file is that.
3. Build notebooks from `_build/build_NN.py`; never hand-edit a code cell. New shared code goes in
   a new module that builds its splice from the existing ones, never by editing
   `blocks_stability.py`, `blocks_evidence.py`, `harness_*.py` or any `cell*_enhanced.py`:
   NB14-NB26 are committed with executed outputs and embed their text.
4. Assert anchor parity against `BASELINE` in every notebook. Any new `decide_trades` branch
   defaults to incumbent behaviour and is proved inert on the anchor path by that assertion.
5. Print the `failed` column in full; write every heading claim from the complete string.
6. Every numeric claim in a heading cites the cell it comes from. A figure in no cell is removed.
7. `runs` / `run_by_label` is the only source for every table.
8. A robustness run that was skipped, failed or never executed cannot produce a passing flag.
9. A surprising null must be shown unreachable, not merely unobserved.
10. A rolling window counts ROWS, not calendar days, unless explicitly resampled.
11. Fail closed on any non-finite required metric and name it in the failure string.
12. At most three notebooks running at once.
13. Every notebook is independently reviewed after its run, and every finding is verified against
    the cited cell before it is applied.
