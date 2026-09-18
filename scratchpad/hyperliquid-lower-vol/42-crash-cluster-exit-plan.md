# Crash exit plan: does the incumbent's exit fill before the gap?

- **Status**: DRAFT 2, 2026-09-18, after Grok review of Draft 1
  ([42-crash-cluster-exit-plan-grok-review.md](42-crash-cluster-exit-plan-grok-review.md),
  `grok-4.6` xhigh: "not worth running as written; worth running with the cuts"). Five blocking
  and nine material findings applied; see §Review log. Nothing has been run.
- **Rules**: [RESEARCH-RULES.md](RESEARCH-RULES.md) as amended by the idiot-gate audit of
  2026-09-16. Standing gates 1, 2, 3 (volatility leg), 6, 7; gates 4, 8, 9 and A6 as diagnostics.
  Gate 5 (a selection score must predict forward stability) does not apply to a position-level
  exit; its substitute here is the universe-wide forward contrast of Part 0 step 4, and a rule
  whose contrast is not positive is not backtested.
- **Track**: `hyperliquid-lower-vol`, NB42.
- **Anchor**: [02-better-format.ipynb](02-better-format.ipynb) = `~/code/strategies/strategy/hyper-ai.py`
  (v6): six names, two-day cycle, `cagr_sortino_weight` ranker, inverse-variance sizing under a
  33% cap, momentum gate = 14-day trailing return at or below -16% removes the name from the
  candidate pool (and so sells it). Every decision reads the previous bar (`index=-1`, T-1).

## One sentence

The incumbent's worst episodes are good picks collapsing at the end of a long hold. Draft 1
proposed a new three-part exit rule read off those collapses; the review showed it was fitted
to five events, could not fire before the gap on a T-1 clock at its own centre, and would be
UNEVALUATED on the plateau by construction. Draft 2 asks the cheaper question first and stops
when it is answered: **does a tighter momentum gate, at the incumbent's own cadence and then at
one day, exit before the collapse, and does the redemption actually fill before the gap?** A
cluster rule is run only if a universe-wide screen says the shape carries information, and then
as one pre-stated specification.

## What the previous research established, and what this plan does with it

| finding | where | consequence here |
|---|---|---|
| 5 momentum-gate exits made +$25.1k (the vault kept falling after 4 of 5); 85 rank-churn exits, median hold 4 days, net -$0.9k; positions held over 30 days made $37.0k of $36.7k net. | NB41 cell 31 | The exit side is the lever. Admission, ranking and sizing are untouched; NB37 and NB40 closed them. |
| `Realist Capital` (20 Jun - 21 Aug, +$16.9k): daily -5.4%, 0%, -8.1%, -2.6%, -14.5%, +2.0%, -29.6% on 15-21 Aug. At the 19 Aug decision the RECONSTRUCTED 14-day gate value at T-1 was -14.5% against a -16% trigger (a coincidence of value with that day's own return; Part 0 prints both with timestamps). The book held one more two-day cycle and took the -29.6% day. TVL fell with NAV. | NB41 cells 35-36; ad-hoc archive read | This is a gate-threshold miss, not a missing indicator. The cheap test is `gate_threshold = -0.12` at the incumbent's two-day cadence. |
| `pmalt` (5 Jan - 21 May, +$6.4k): daily -23.9% then -32.2% on 20-21 May after weeks of +/-2-6% days; at 4-hour resolution 20 May is six consecutive down buckets (-10.3% by 12:00). | ad-hoc archive read | A different class: no daily warning before day one. On a daily T-1 clock nothing exits before day two; the honest rule for this class is a next-day exit after one extreme day (the breaker), and whether even that helps depends on the fill. |
| A same-day stop at -10% would have fired on 10 of 96 positions; 8 were winners (+$32.3k). Positions whose vault drew down more than 15% while held have a 73% win rate and made $30.1k. | ad-hoc archive read; NB41 ledger | A stop on depth is rejected before it is built. |
| The engine's default settlement delay for an async vault is two days (`DEFAULT_VAULT_SETTLEMENT_DELAY`); whether a HyperCore pair is treated as async depends on its feature flags; live HyperCore leader vaults lock for about a day after deposit and withdrawals are a multi-phase transfer, not an epoch. | trade-executor `backtest_execution.py`, `identifier.py`; Grok review | "React in a day" is a claim about the FILL. If the backtest fills a redemption two days after the decision, a one-day decision clock is theatre; if it fills at the decision, the backtest is optimistic against a live lock-up. Part 0 settles which, before any run, and H2a/H3 are written on fill timestamps. |
| "Three separate cadence studies settled on 48 hours" (`hyper-ai.py`); the daily candle bucket is native; the raw archive supports 4-hour buckets from April 2026 with no empty bucket during either collapse, but every row-based indicator (CAGR annualisation, Sortino, `inverse_vol` with its daily `VOL_FLOOR`, `minimum_hold_days`, `cycle_returns()` on `.days`) is written for a daily row. | hyper-ai.py; Grok review finding 4 | The 4-hour arm is NOT backtested. Part 0 answers the operator's 4-hour question with mark coverage and the two collapse paths at 4 hours; a 4-hour strategy is a separate plan with a rewritten indicator stack. |

## The runs, in order; stop when a cheaper one answers

Every run is on the daily candle bucket. Metrics are on each run's own decision clock, and a
one-day run is ALSO reported on the two-day grid (equity sampled every second day) so its
Sharpe is comparable with the anchor's; the indifference band is applied only between books on
the same clock.

| # | run | what it answers | stop rule |
|---|---|---|---|
| 0 | Part 0 (research, no backtest) | the path, the classes, the fill, the 4-hour coverage | if the fill lag is at or above the gap (step 2), runs 2-5 are DIAGNOSTIC and are not run as candidates |
| 1 | `anchor` (2d), `anchor_1d` | parity; H1 | if H1 fails, `anchor_1d` is the finding and runs 3a and 4-5 at 1d are not run |
| 2 | `gate12_2d` = gate -12% at 2d | H2a: the August class at the incumbent's cadence | - |
| 3a | `gate12_1d`, `gate10_1d` | H2b, with `anchor_1d` (-16%) as the third plateau point | - |
| 3b | `gate20_2d`, `gate10_2d` | the plateau neighbours of -12% at 2d, and -16%'s other neighbour | - |
| 4 | `breaker20_1d`: exit a held name on the next decision after a daily log return at or below -20% | H4: the May class | run only if Part 0 step 4's contrast is positive for the "extreme day" class |
| 5 | `cluster_1d`: exit a held name whose trailing 3 rows hold 2 or more daily log returns at or below -10% (held names only; no admission branch; no strike-one sizing) | H5 | run ONLY if Part 0 step 4's contrast is positive for the cluster class AND runs 2-3 did not already cut the August class |

Gate 2 (a full re-simulation) for `anchor_1d` and every run that passes gates 1, 3 and 7.
Windows A and B for `anchor_1d`, `gate12_2d` and the best run. Nothing is added after these
runs are seen. There is no Part E.

Thresholds are round numbers fixed here, before Part 0 looks at any histogram: -12% and -10%
for the gate (with -16% and -20% as neighbours), -20% for the breaker, -10% x 2-in-3 for the
cluster. The in-sample percentile each one lands on is PRINTED in Part 0 as a diagnostic and
does not set anything.

## The mechanism, minimal

1. **Gate threshold** is the incumbent's own `gate_threshold` parameter; no new code.
2. **Cadence** is `cycle_duration = cycle_1d`; no new code. Row-based lookbacks are unchanged
   because the row is still a day.
3. **Breaker** (run 4): new indicator `last_daily_log_return`; in `decide_trades`, after the
   momentum gate and before ranking, a HELD vault whose value at T-1 is at or below
   `breaker_threshold` is removed from the pool. Explicit `breaker_on` flag; off is off.
4. **Cluster** (run 5): new indicator `down_day_count` over `cluster_window` rows at
   `strike_threshold`; a HELD vault with count at least 2 is removed from the pool. Explicit
   `cluster_on` flag. No admission branch, no re-weighting.

Each new component off is asserted inert on `anchor_1d` (the parity assertion for this
notebook: `anchor_1d` with the splice present equals `anchor_1d` without it, to 1e-9 on the
cycle returns).

## Hypotheses, pre-registered

- **H1 (cadence).** `anchor_1d`, sampled on the two-day grid, is within 0.25 cycle Sharpe of
  `anchor`, no worse on max drawdown by more than 1 percentage point, and its rank-churn P&L
  (positions exited by ranking) is no worse than the anchor's minus $1,000. Turnover and the A6
  fee differential are reported; a fee gap over $1,000 blocks any SHORTLIST on the one-day clock.
  Prediction: passes on Sharpe, fails or nearly fails on churn.
- **H2a (the cheap test).** `gate12_2d` FILLS its exit from the August-class position before
  the collapse day (fill timestamp, not decision timestamp), passes gates 1, 3 and 7, and cuts
  the worst five cycles' sum by a third against `anchor` with the two collapse windows INCLUDED
  and does not cut it by a third with them EXCLUDED. Prediction: the first two hold and the
  worst-five cut is inside the collapse windows only - a one-event rescue, not a general one.
  If H2a passes every standing gate it is a candidate for a one-event NOT CONFIRMED, and the
  plan says now that it may fail gate 2 precisely because the largest contributor's collapse is
  what it avoids; that is a REJECT, not a footnote.
- **H2b.** The same at one day; the plateau on -12% needs -16% (`anchor_1d`) and -10%.
  Prediction: no better than 2d.
- **H3 (fill).** For every forced exit in every run, the realised decision-to-fill lag from the
  trade records. Prediction: the engine fills HyperCore redemptions at the decision (no async
  flag), in which case the backtest is optimistic against a live one-day lock-up on names held
  under a day, and the churn positions (median hold 4 days) are where that bites. The plan
  reports how many forced exits fall inside a live lock-up window under both the 1-day and
  4-day assumption.
- **H4 (breaker).** Fires fewer than 10 times on the track window. Prediction: it fires on the
  May-class day and on two or three single-day shocks that recovered, and nets to inside noise.
- **H5 (cluster).** Only if run: passes gates 1, 3, 7; gate 6 is UNEVALUATED (one specification,
  no pre-stated neighbours) and the verdict is capped at DIAGNOSTIC / NOT CONFIRMED. Prediction:
  on a T-1 clock it does not fire before 21 Aug at -10% (the second strike is the collapse day
  itself) and is therefore a diagnostic of the review's point, not a candidate.

## Part 0 - research, before any backtest

1. Reproduce the ad-hoc archive read in a cell: daily log returns (last mark per UTC day) of
   every vault the anchor held, over the hold; the two collapse paths at daily and 4-hour
   resolution; the three recoveries; the single-day-stop table at -10% and -15%. Print the 19
   Aug reconstructed gate value and the 19 Aug daily return separately, with timestamps.
2. **Fill kill-switch.** From the code and one asserted anchor position: is a HyperCore pair
   async in this backtest (`is_async_vault`, feature flags, overrides); what the settlement
   delay resolves to; the executed-at timestamp of the sell trade against the decision
   timestamp. If the fill lag is at or above the gap between the warning day and the collapse
   day (two days for August, one for May), runs 2-5 cannot avoid the collapse and are run as
   diagnostics only.
3. Mark coverage per 4-hour bucket for every held vault by regime, and the two collapse paths at
   4 hours. This answers the operator's 4-hour question; it does not lead to a 4-hour backtest.
4. **Universe-wide forward contrast (the gate-5 substitute).** On every candidate-day of the
   track window, at T (reading T-1), classify the vault as: cluster (2 or more days at or below
   -10% in the trailing 3), extreme (last day at or below -20%), single strike (exactly one day
   at or below -10% in the trailing 3 and not extreme), or neither. Report the forward 1-, 2-
   and 5-day log return of the vault per class with a 30-day date-block bootstrap interval. A
   class whose forward return is not below "neither" at the interval's upper edge carries no
   exit information and its run (4 or 5) is not made.
5. The in-sample percentile of each fixed threshold among candidate-day daily returns, as a
   diagnostic.

## What is deliberately NOT tested

- A 4-hour backtest. The indicator stack is daily; Part 0 answers the coverage question.
- Strike-one re-weighting, a -7% strike, a 5-row window, quantile-set breakers, combinations
  of the best members. All were in Draft 1; all were fitted or unevaluable; see the review.
- Anything on the admission side.
- Sub-daily reaction in the engine.

## Limitations, stated before the run

- The two collapses and three recoveries are five events on one window; every "class" above
  was named after seeing them. Part 0 step 4 is the only test that is not circular, and it is a
  screen on 126 x ~150 candidate-days with heavy overlap, not an independent sample.
- A rule that avoids the largest contributor's collapse changes the single-vault mask by
  construction (the unmasked run gains, the masked run does not); gate 2 can REJECT a rule for
  working. The plan accepts that.
- The one-day clock doubles decisions; the indifference band and the minimum detectable Sharpe
  difference (about 2.5 on 126 decisions) do not improve materially at 252 overlapping ones.
- The engine's fee discrepancy (44% of redemptions) is only bounded differentially (A6).
- A one-day strategy is a different deployment from the incumbent; a SHORTLIST here would be a
  shortlist for that deployment.

## Verdict vocabulary

As in RESEARCH-RULES.md. "One-event NOT CONFIRMED" is added for a run whose only measurable
gain is inside the two collapse windows (worst-five cut vanishes when they are excluded): it is
recorded, it is not carried without a prospective window.

## What I expect

Part 0 step 2 decides the notebook. If HyperCore redemptions fill at the decision, `gate12_2d`
exits the August position on 19 Aug and the result is a one-event NOT CONFIRMED that probably
fails gate 2. If they fill two days later, nothing on a daily or two-day clock avoids either
collapse, and the answer to the operator's question is "no, not on this engine's fill model;
the live lock-up is the real constraint and the next lever is the redemption clock, which is
outside this backtest".

## Definition of done

- Part 0 reproduces the ad-hoc numbers or explains every difference; the fill kill-switch is
  asserted, not described.
- Runs 1-3b executed; 4 and 5 executed or explicitly not made with the Part 0 reason.
- Every heading number cites a cell and comes from the manifest; standing-gate verdicts for
  every run; worst-five with and without the collapse windows; fill-lag table.
- Review applied and logged.

## Review log

- **Draft 1 → Draft 2 (Grok, 2026-09-18).** Blocking 1 (the -10% x 2-in-3 centre cannot fire
  before the gap on a T-1 clock; the -7% cell was post-hoc): cluster reduced to one pre-stated
  specification, run last and only on a positive universe-wide contrast, verdict capped.
  Blocking 2 (two collapses, two mechanisms): August is tested as a gate-threshold miss at the
  incumbent's cadence first; May as a next-day breaker. Blocking 3 (settlement): Part 0 step 2 is
  a kill-switch and H2a/H3 are on fill timestamps. Blocking 4 (4-hour arm breaks the indicator
  stack and `cycle_returns`): removed; Part 0 answers coverage only. Blocking 5 (two-point axes
  make every Part C cell an endpoint on gate 6): the gate family has three points at each
  cadence; the cluster's gate 6 is declared UNEVALUATED. Material 6 (H4 circular): replaced by
  the universe-wide forward contrast. Material 7 (search size, Part E): cut to at most eight
  runs, no Part E. Material 8 (quantile breaker is look-ahead): round -20%, fixed here. Material
  9 (gate control at the wrong clock): `gate12_2d` first. Material 10 (admission branch):
  removed. Material 11 (gate 2 and the collapse windows): worst-five with and without; gate 2
  failure declared a REJECT. Material 12 (gate 5): exemption and substitute written. Material 13
  (0 as an off state): explicit flags. Material 14 (clocks, churn, fees): two-day-grid sampling
  for one-day runs, churn floor, A6 block. Minor findings applied (gate vs daily return
  conflation; epoch wording; 4-hour hold days moot).
