# Crash exit plan: does the incumbent's exit fill before the gap?

- **Status**: DRAFT 3, 2026-09-19, after two Grok reviews
  ([Draft 1 review](42-crash-cluster-exit-plan-grok-review.md): "not worth running as written";
  [Draft 2 review](42-crash-cluster-exit-plan-grok-review-2.md): "worth running with the
  changes"). Draft 3 applies the second review's two blocking and five material findings; see
  §Review log. Nothing has been run.
- **Rules**: [RESEARCH-RULES.md](RESEARCH-RULES.md) as amended by the idiot-gate audit of
  2026-09-16, with NO local additions to the verdict vocabulary. Standing gates 1, 2, 3
  (volatility leg), 6, 7; gates 4, 8, 9 and A6 as diagnostics. Gate 5 (a selection score must
  predict forward stability) does not apply to a position-level exit; Part 0 step 4 reports the
  forward return after a first strike as a diagnostic table and gates nothing, because a bound
  on 1-5 day forward returns over overlapping candidate-days is the return clause the audit
  retired.
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
cluster rule is run, if at all, as one pre-stated diagnostic of the T-1 point that it cannot
fire before the gap. **A catch is defined on the fill PRICE**, not on the decision or the
executed-at timestamp: a redemption that fills at the open of a bar strictly before the
collapse bar caught the gap; one that fills at or after the collapse bar's close did not.

## What the previous research established, and what this plan does with it

| finding | where | consequence here |
|---|---|---|
| 5 momentum-gate exits made +$25.1k (the vault kept falling after 4 of 5); 85 rank-churn exits, median hold 4 days, net -$0.9k; positions held over 30 days made $37.0k of $36.7k net. | NB41 cell 31 | The exit side is the lever. Admission, ranking and sizing are untouched; NB37 and NB40 closed them. |
| `Realist Capital` (20 Jun - 21 Aug, +$16.9k): daily -5.4%, 0%, -8.1%, -2.6%, -14.5%, +2.0%, -29.6% on 15-21 Aug. At the 19 Aug decision the RECONSTRUCTED 14-day gate value at T-1 was -14.5% against a -16% trigger (a coincidence of value with that day's own return; Part 0 prints both with timestamps). The book held one more two-day cycle and took the -29.6% day. TVL fell with NAV. | NB41 cells 35-36; ad-hoc archive read | This is a gate-threshold miss, not a missing indicator. The cheap test is `gate_threshold = -0.12` at the incumbent's two-day cadence. |
| `pmalt` (5 Jan - 21 May, +$6.4k): daily -23.9% then -32.2% on 20-21 May after weeks of +/-2-6% days; at 4-hour resolution 20 May is six consecutive down buckets (-10.3% by 12:00). | ad-hoc archive read | A different class: no daily warning before day one. On a daily T-1 clock the first decision that sees 20 May is 21 May, which is the decision the incumbent's gate already sells on; no daily rule beats it, and whether day two was taken is a question about the fill price of that sell (Part 0 step 2). |
| A same-day stop at -10% would have fired on 10 of 96 positions; 8 were winners (+$32.3k). Positions whose vault drew down more than 15% while held have a 73% win rate and made $30.1k. | ad-hoc archive read; NB41 ledger | A stop on depth is rejected before it is built. |
| The engine's default settlement delay for an async vault is two days (`DEFAULT_VAULT_SETTLEMENT_DELAY`); whether a HyperCore pair is treated as async depends on its feature flags; live HyperCore leader vaults lock for about a day after deposit and withdrawals are a multi-phase transfer, not an epoch. | trade-executor `backtest_execution.py`, `identifier.py`; Grok review | "React in a day" is a claim about the FILL. If the backtest fills a redemption two days after the decision, a one-day decision clock is theatre; if it fills at the decision, the backtest is optimistic against a live lock-up. Part 0 settles which, before any run, on the fill PRICE of three named trades; H2a and H0 are written on fill price. |
| "Three separate cadence studies settled on 48 hours" (`hyper-ai.py`); the daily candle bucket is native; the raw archive supports 4-hour buckets from April 2026 with no empty bucket during either collapse, but every row-based indicator (CAGR annualisation, Sortino, `inverse_vol` with its daily `VOL_FLOOR`, `minimum_hold_days`, `cycle_returns()` on `.days`) is written for a daily row. | hyper-ai.py; Grok review finding 4 | The 4-hour arm is NOT backtested. Part 0 answers the operator's 4-hour question with mark coverage and the two collapse paths at 4 hours; a 4-hour strategy is a separate plan with a rewritten indicator stack. |

## The runs, in order; stop when a cheaper one answers

Every run is on the daily candle bucket. Two Sharpe series are named and never mixed:
`cycle_sharpe` on the run's own decision clock, used for plateaus WITHIN a cadence; and
`cycle_sharpe_on_2d_grid`, the equity reindexed onto the two-day anchor's decision timestamps
(fail closed on a missing timestamp; spacing 2, periods per year 182.5), used for every
comparison with `anchor` and for the indifference band.

| # | run | what it answers | stop rule |
|---|---|---|---|
| 0 | Part 0 (research, no backtest) | the path; gate vs daily return with timestamps; the FILL-PRICE assertion; the -12% fire count; 4-hour coverage; the first-strike forward table | if the incumbent's own sells fill at or after the collapse bar's close (step 2), every later run is DIAGNOSTIC |
| 1 | `anchor` (2d) | parity against `BASELINE` with the new flags off, to 1e-9 | - |
| 2 | `gate12_2d`, `gate10_2d` | H2a: the August class at the incumbent's cadence, with -16% (`anchor`) and -10% as the plateau neighbours of -12% | if `gate12_2d` catches August on fill price, runs 3-5 are not candidates: the answer is "the 48-hour gate, four points tighter" |
| 3 | `anchor_1d` | H1: is the one-day clock usable at all | diagnostic; 1d gates (`gate12_1d`, `gate10_1d`) run only if H1 passes AND run 2 did not catch August |
| 4 | `cluster_1d` (exit a held name whose trailing 3 rows hold 2 or more daily log returns at or below -10%; held names only) | H5, a labelled DIAGNOSTIC of the T-1 point | only if run 2 did not catch August; gate 6 UNEVALUATED by construction |

No breaker run: on a T-1 daily clock a -20% breaker first sees 20 May at the 21 May decision,
which is the decision the incumbent's own gate already sells on (`exit_return_14d` -20.3%), and
first sees August's -29.6% on 22 Aug, after the gap. It cannot beat the incumbent on either
class; Part 0 prints its would-be fire count as a diagnostic and nothing more.

Gate 2 (a full re-simulation) for every run that passes gates 1, 3 and 7. Windows A and B for
`anchor`, `anchor_1d` and `gate12_2d` - named now, not "the best run". Nothing is added after
these runs are seen.

Thresholds are round numbers fixed here, before Part 0 looks at any histogram: -12% and -10%
for the gate; -10% x 2-in-3 for the cluster diagnostic; -20% for the breaker fire count. The
in-sample percentile each lands on is printed in Part 0 as a diagnostic and sets nothing.

## The mechanism, minimal

1. **Gate threshold** is the incumbent's own `gate_threshold` parameter; no new code.
2. **Cadence** is `cycle_duration = cycle_1d`; no new code. Row-based lookbacks are unchanged
   because the row is still a day.
3. **Cluster** (run 4, diagnostic): new indicator `down_day_count` over `cluster_window` rows
   at `strike_threshold`; a HELD vault with count at least 2 is removed from the pool. Explicit
   `cluster_on` flag. No admission branch, no re-weighting, no breaker component.

Parity: the two-day `anchor` with `cluster_on = False` reproduces `BASELINE` to 1e-5 (standing
method rule 4) and, with the splice present and absent, is identical to 1e-9 on cycle returns;
the same identity is asserted on `anchor_1d`.

## Hypotheses, pre-registered

- **H0 (the fill, Part 0).** In this universe a HyperCore pair is NOT async
  (`vault_features` = {hypercore_native}, outside `ASYNC_VAULT_FEATURES`), so the engine fills a
  redemption at the decision, at the candle OPEN of the decision day (`candle_timepoint_kind =
  "open"`; a vault day-candle's open is its first mark of the day, about the previous day's last
  mark). Prediction: the incumbent's own 21 Aug and 21 May sells filled at the 21 Aug and 21 May
  opens - i.e. the incumbent ALREADY skipped the -29.6% and -32.2% bars, and what it took was
  the days before them. If instead a fill is at or after the collapse bar's close, no daily-clock
  rule can do better and every later run is a diagnostic.
- **H2a (the cheap test).** At the 19 Aug two-day decision the reconstructed T-1 gate value
  is -14.5% (the 14-day simple return through 18 Aug, not the 19 Aug daily return, which
  happens to be the same number); -12% and -10% sell on that decision and -16% does not.
  `gate12_2d` therefore FILLS its August-class exit at the 19 Aug open, skipping the -14.5% and
  -29.6% bars. Prediction on the standing gates: passes 1, 3, 7; **REJECT on gate 6 as a spike
  against -16%** (a ~10-point portfolio day separates -12% from -16% and nothing separates
  -12% from -10%), and possibly REJECT on gate 2 because the largest contributor's collapse is
  what it avoids. Both are REJECT and the plan says so before the run. Worst-five cycles with
  and without the 19-21 Aug and 20-21 May date windows are reported to show WHY, not to soften
  the verdict. NOT CONFIRMED applies only if every standing gate passes and the two-day Sharpe
  gap is inside 0.25; "do not carry a one-event rule" is an operator prior, not a verdict.
- **H2a-collateral.** Part 0 counts, on every two-day decision and every then-held vault, T-1
  `return_gate` in (-16%, -12%] and in (-16%, -10%], with the vault's 5- and 30-day forward
  return. Prediction: 19 Aug is not the only held fire; the others are the tighter gate's
  collateral and their P&L under `gate12_2d` (rank-churn P&L, recovered names sold) is reported.
- **H1 (cadence, diagnostic).** `anchor_1d` on the two-day grid is within 0.25 Sharpe of
  `anchor`, max drawdown no worse by more than 1 percentage point, and
  `churn_pnl_1d >= churn_pnl_anchor - 1000` (USD; rank-exit positions only). Turnover and the
  A6 fee differential reported; a fee gap over $1,000 blocks any SHORTLIST on the one-day
  clock. Prediction: passes on Sharpe, fails or nearly fails on churn.
- **H2b (1d gates, only if reached).** `gate12_1d` with `anchor_1d` and `gate10_1d` as
  neighbours on the own-clock Sharpe. Prediction: no better than 2d, and not reached.
- **H3 (lock-up, diagnostic).** For every forced exit in every run: decision timestamp,
  `executed_at`, `executed_price`, the decision bar's open and close. Count the forced exits on
  positions younger than 1 day and 4 days (the live leader and HLP lock-ups) - the backtest
  fills them, live would not. Assert on the two collapse sells that the hold (62 and 136 days)
  is past both lock-ups, so the lock-up table is not mistaken for the crash constraint.
- **H5 (cluster diagnostic, only if reached).** On a T-1 clock, -10% x 2-in-3 first fires for
  the August vault at the 22 Aug decision, after the gap. Prediction: it fires there and on a
  handful of recovered names; gate 6 UNEVALUATED; DIAGNOSTIC.

## Part 0 - research, before any backtest

1. Reproduce the ad-hoc archive read in a cell: daily log returns (last mark per UTC day) of
   every vault the anchor held, over the hold; the two collapse paths at daily and 4-hour
   resolution; the three recoveries; the single-day-stop table at -10% and -15%. Print the 19
   Aug reconstructed gate value and the 19 Aug daily return separately, with timestamps.
2. **Fill-price assertion (the kill-switch).** On the actual pairs in this universe, printed
   and asserted, for the incumbent's 21 Aug sell of the August vault, its 21 May sell of the May
   vault, and one rank-churn sell of a name held under four days: `get_vault_features()`,
   `is_async_vault()`, `has_delayed_vault_redemption()`, `_is_async_vault(pair, is_buy=False)`,
   any settlement override; the decision timestamp, `executed_at`, `executed_price`; the
   collapse bar's open and close and the warning bar's open. A catch = `executed_price` equals
   the open of a bar strictly before the collapse bar (to the price tolerance of the candle
   feed). A fill at the collapse bar's open is a PARTIAL catch (skipped the gap, took the days
   before), still a candidate, labelled. A fill at or after the collapse bar's close is a miss,
   and then every later run is DIAGNOSTIC. `DEFAULT_VAULT_SETTLEMENT_DELAY` is not the lag; the
   trade record is. This step also prints whether the incumbent's 21 May fill already skipped
   the -32.2% bar, which answers the May class before any new rule is proposed.
2b. **The -12% fire count.** On every two-day decision, for every then-held vault, T-1
   `return_gate` in (-16%, -12%] and (-16%, -10%]: the dates, the vault, the 5- and 30-day
   forward return. This says whether `gate12_2d` is a one-date intervention or a broad one.
3. Mark coverage per 4-hour bucket for every held vault by regime, and the two collapse paths at
   4 hours. This answers the operator's 4-hour question; it does not lead to a 4-hour backtest.
4. **First-strike forward table (diagnostic, gates nothing).** On every candidate-day of the
   track window, at T reading T-1, disjoint classes in this order: `first_extreme` (the last
   day at or below -20%), `first_single` (exactly one day at or below -10% in the trailing 3,
   that day the last one, and not extreme), `neither`. No "cluster" class: two strikes means the
   second is already in T-1, and its forward return is the aftermath, not the gap. Report the
   forward 1- and 2-day log return per class, point estimate and a 30-day date-block interval,
   as a table. Nothing is gated on it; the audit retired bounds of this kind.
5. The in-sample percentile of each fixed threshold among candidate-day daily returns, as a
   diagnostic.

## What is deliberately NOT tested

- A 4-hour backtest. The indicator stack is daily; Part 0 answers the coverage question.
- Strike-one re-weighting, a -7% strike, a 5-row window, quantile-set breakers, a breaker
  run, combinations of the best members. All were in Draft 1 or 2; all were fitted,
  unevaluable, or unable to beat the incumbent's own gate on a T-1 clock; see the reviews.
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

Exactly as in RESEARCH-RULES.md; nothing is added.

## What I expect

Part 0 step 2 decides the notebook. The expected finding is that the incumbent's own gate
already fills at the open of the collapse day on both events - it never held through the
-29.6% or the -32.2% bar; it took the days before. Then `gate12_2d` moves the August exit two
days earlier (skipping -14.5%), is a spike on the gate axis, and is REJECT on gate 6 - the
honest answer to "can we react in a day" being: **we did not need a faster clock; the 14-day
gate at 48 hours was two days early and four points too loose, and tightening it is a
one-event fix that the plateau test rejects.** If instead the fill is at the collapse bar's
close, nothing on a daily clock avoids either collapse and the constraint is the fill, which
this backtest models optimistically against a live lock-up.

## Definition of done

- Part 0 reproduces the ad-hoc numbers or explains every difference; the fill-price
  assertion is asserted on three named trades, not described; the -12% fire count is printed.
- Runs 1-2 executed; 3 executed as a diagnostic; the 1d gates and the cluster diagnostic
  executed or explicitly not made with the run-2 reason.
- Every heading number cites a cell and comes from the manifest; the two Sharpe series are
  never mixed; standing-gate verdicts for every run; worst-five with and without the two date
  windows; the fill table (decision, executed_at, executed_price, bar open/close) for every
  forced exit; the heading states whether the 19 Aug fill was the 19 Aug open.
- Review applied and logged.

## Review log

- **Draft 2 → Draft 3 (Grok, 2026-09-19).** Blocking 1 (the kill-switch scored timestamps, so
  a close fill and an open fill were indistinguishable and a 2-day default delay would have
  aborted the only useful run): a catch is defined on `executed_price` against the collapse
  bar's open and close, asserted on three named trades, with `DEFAULT_VAULT_SETTLEMENT_DELAY`
  explicitly not the lag; H0 states the expected open-fill path. Blocking 2 (the forward
  contrast classified the aftermath, overlapped its classes, and used the retired return-clause
  bound as a kill-switch): replaced by a first-strike forward table with disjoint ordered
  classes that gates nothing. Material 3 ("one-event NOT CONFIRMED" was a local verdict; a
  working save is a gate-6 spike): vocabulary removed; H2a predicts REJECT on gate 6. Material 4
  (the breaker cannot beat the incumbent's 21 May sell on a T-1 clock): breaker run removed,
  fire count printed. Material 5 (stop-when-answered was not applied; `gate20_2d` was not
  -12%'s neighbour): run order rewritten with real stop rules; `gate20_2d` dropped; windows on
  named labels. Material 6 (no fire count): Part 0 step 2b. Material 7 (two Sharpe series):
  `cycle_sharpe` and `cycle_sharpe_on_2d_grid` named and never mixed; parity against BASELINE.
  Minors applied (churn floor as an inequality; H5 wording; lock-up assertion on the two long
  holds; May incumbent fill printed).
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
