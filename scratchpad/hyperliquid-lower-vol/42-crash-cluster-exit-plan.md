# Crash-cluster exit plan: reacting to a vault's own collapse within a day

- **Status**: DRAFT 1, for review before anything is built. Nothing in this plan has been run.
- **Rules**: [RESEARCH-RULES.md](RESEARCH-RULES.md) as amended by the idiot-gate audit of
  2026-09-16. Standing gates 1, 2, 3 (volatility leg), 6, 7; gates 4, 8, 9 and A6 as diagnostics.
  Verdict vocabulary SHORTLIST / NOT CONFIRMED / NO EFFECT / REJECT / UNEVALUATED / DIAGNOSTIC.
- **Track**: `hyperliquid-lower-vol`, NB42 (research + backtest in one notebook, or NB42 research
  and NB43 backtest if the research part changes a pre-stated family - see §Definition of done).
- **Anchor**: [02-better-format.ipynb](02-better-format.ipynb) = `~/code/strategies/strategy/hyper-ai.py`
  (v6): six names, two-day cycle, `cagr_sortino_weight` ranker, inverse-variance sizing under a
  33% cap, momentum gate = 14-day trailing return at or below -16% removes the name from the
  candidate pool (and so sells it).

## One sentence

The incumbent's worst episodes are not bad picks but good picks collapsing at the end of a long
hold; its exit rule saw the largest collapse coming two days early and waited one more two-day
cycle. This plan tests, on the native one-day data clock, whether a position-level exit that
reacts to a CLUSTER of large down days - not to any single one - cuts those collapses without
cutting the one-off shocks that recover, which the trade record says are the majority.

## What the previous research established, and what this plan does with it

| finding | where | consequence here |
|---|---|---|
| The incumbent's 2026 result is carried by a few long holds exited by the momentum gate: 5 gate exits made +$25.1k with the vault falling further after 4 of the 5; 85 rank-churn exits (median hold 4 days) net -$0.9k; 6 still-open positions +$12.5k. Trades held over 30 days made $37.0k of the $36.7k net. | NB41 cell 31 | The mechanism that earns is "hold a re-ranking winner until its own return breaks", and the rule that protects it is the momentum gate. This plan changes the EXIT side only. Ranking, sizing and the gate itself are untouched unless a family member says so. |
| `Realist Capital` (20 Jun - 21 Aug, +$16.9k, 59% of positive P&L at N = 4) fell -5.4%, 0%, -8.1%, -2.6%, **-14.5%**, +2.0%, **-29.6%** on 15-21 Aug. At the 19 Aug decision the incumbent's own 14-day gate read -14.5% against a -16% trigger; it held one more cycle and took the -29.6% day. The vault's TVL fell in step with its NAV: a real loss, not a stale mark. | NB41 cells 35-36; ad-hoc archive read (to be reproduced in NB42 Part 0) | A slow-motion collapse with two large down days before the worst one. The gate's threshold and cadence, not its information, are what missed it. |
| `pmalt` (5 Jan - 21 May, +$6.4k) fell **-23.9%** then **-32.2%** on 20-21 May after weeks of +/-2-6% days. TVL fell in step. | same | On the DAILY clock a two-day collapse with no warning before day one. |
| The archive carries 17-40 marks a day on these vaults from April 2026: every 4-hour bucket of both collapses holds 2-11 marks, none is empty. At 4 hours `pmalt`'s 20 May is a grind, not a gap: -1.8%, -1.4%, -3.5%, -5.2%, -2.2%, -9.7% - six consecutive down buckets, -10.3% by 12:00 with eight hours of the day to go. `Realist Capital` printed a -10.1% 4-hour bucket at 04:00 on 19 Aug, two days before the -19.7% single-mark gap of 21 Aug. | ad-hoc archive read (to be reproduced in NB42 Part 0) | The daily clock's "no warning" for `pmalt` is an artefact of the clock. A 4-hour decision clock is the one that sees both collapses early; it is a family member, not future work. Its costs - six times the decisions, the redemption settlement lag as the binding constraint, and the forward-fill gotcha in the sparse 2025 period - are what Part A measures. |
| Across the anchor's 96 positions, a same-day stop at -10% would have triggered on 10; **8 of the 10 went on to be winners** (+$32.3k) and 2 losers (-$1.9k). At -15%: 7 triggered, all 7 winners. The recovering cases - `Goon Edging` -23.6% on 6 Feb then flat, `DOEZOE` -23.0% on 7 Sep then +2.3%, `Sequoia` -17.9% then +3.6% - are SINGLE large days with no follow-through. The two collapses have a SECOND large down day within 1-2 days of the first. | ad-hoc archive read (to be reproduced in NB42 Part 0) | A single-day stop is rejected before it is built: it is net-harmful on this record. The candidate signal is the cluster - two qualifying down days inside a short window. |
| Positions with a vault drawdown deeper than 15% while held have a 73% win rate and made $30.1k of the $36.7k; the whole book's win rate is 44%. | NB41 ledger | Deep intra-hold drawdowns are where the money is. Any exit that fires on drawdown depth alone will cut the winners. The rule must fire on the SHAPE of the decline (clustered, accelerating), never on its depth. |
| The engine's redemptions settle asynchronously (`get_vault_settlement_pending_value`, the cost-basis helper's settlement handling); Hyperliquid vaults carry a lock-up after deposit and an epoch for withdrawals. | trade-executor, NB33/35 helpers | "React in one day" is a claim about the DECISION clock. Whether the redemption fills a day later is the engine's model of the vault, and NB42 must report the realised decision-to-settlement lag of every exit it forces, not assume it. |
| "Three separate cadence studies settled on 48 hours" (`hyper-ai.py`, the `cycle_duration` comment); the candle bucket is daily. | hyper-ai.py | A one-day cycle is a RE-TEST of a settled decision, not a free change: it doubles decision count, changes turnover and fees, and breaks parity with the anchor. The anchor at one day is a new baseline and is run first, alone. |
| Rank churn is 89% of trades and nets zero. | NB41 | Doubling the cadence will double the churn's trade count. Turnover, fee differential (A6) and the rank-churn P&L are reported for every run and a one-day book must not lose money on churn. |
| Every earlier lead that changed the ENTRY side (crash filters at 1.0-1.25, quality floors, stability rankers) broke the mechanism at the point where it adds value. | NB37, NB40 | Nothing here touches admission. |

## The mechanism

Three components, each a separate parameter with an off state that is proved inert on the anchor
path by the parity assertion. All three read the vault's own daily marks at T-1 exactly as the
momentum gate does (`get_indicator_value` at index -1); nothing reads T.

1. **Cadence.** `cycle_duration` = 1 day (`anchor_1d`) and 4 hours (`anchor_4h`, with
   `candle_time_bucket` = h4 built from the raw marks: last mark per bucket, forward-filled, on
   the same universe). Every other parameter unchanged. Parity with `anchor` (two days) is NOT
   expected; the assertion is that each cadence's anchor with the three components off equals
   the same run with them present. On the 4-hour clock the momentum gate's 14-day window is
   14 x 6 rows and the 90-row volatility window becomes 90 x 6 rows: every row-based lookback is
   scaled so the CALENDAR span is unchanged, and Part 0 asserts the scaled indicators agree with
   the daily ones at midnight to a stated tolerance.
2. **Cluster exit.** New indicator `down_day_count(close, strike_threshold, cluster_window)`: the
   number of rows in the trailing `cluster_window` rows whose per-row log return is at or below
   `strike_threshold`. On the 4-hour clock the row is a bucket, the threshold is scaled by
   sqrt(6) (a -10% daily strike is a -4.1% bucket strike) and the window is 3 x 6 or 5 x 6 rows,
   so the rule asks the same question on both clocks; the 4-hour variant additionally counts
   `consecutive_down_buckets` (runs of 3 or more) as a second strike definition, because that is
   the shape `pmalt` had and a daily rule cannot express. In `decide_trades`, after the momentum gate and before ranking, a HELD
   vault whose count is at least 2 is removed from the candidate pool (sold). A vault not held is
   not admitted while its count is at least 1 (it does not buy into a collapse). Off at
   `strike_threshold = 0`.
3. **Strike-one de-risking.** With `strike_one_weight_factor = f < 1`, a held vault whose count is
   exactly 1 has its sizing weight multiplied by `f` before `normalise_weights`; the freed weight
   is redistributed by the sizer as it does today. Off at `f = 1`. This is the only component that
   touches sizing, and only for flagged names.
4. **Circuit breaker.** A held vault whose LAST daily log return is at or below
   `breaker_threshold` is removed from the pool regardless of anything else. Off at 0. The
   threshold is NOT a number chosen by eye: it is the `breaker_quantile` of the distribution of
   daily log returns over every candidate-day in the pool on the track window, computed in Part 0
   BEFORE any backtest, with the quantile pre-stated here (§Families). The number it resolves to
   is recorded, and is the same for every run.

The momentum gate (14-day, -16%) stays as it is in every run except the gate-threshold family,
which is the comparator: if a tighter gate at one day does what the cluster rule does, the
cluster rule is not needed.

## Families, pre-stated

| axis | values | centre | notes |
|---|---|---|---|
| cadence | 2d (anchor), 1d, 4h | 1d | Part A; the 4h arm is carried into Part C only if `anchor_4h` passes H1 |
| gate threshold at 1d | -20%, -16%, -12%, -10% | -16% (the incumbent's) | comparator family; plateau on -12% needs -16% and -10% |
| strike threshold | -7%, -10% | -10% | -7% exists because `Realist Capital`'s first down day was -8.1%; that is a post-hoc reason and is declared as one |
| cluster window (rows) | 3, 5 | 3 | |
| strike-one factor | 1.0 (off), 0.5 | 1.0 | |
| breaker quantile | off, 0.5th, 0.2nd percentile of candidate daily returns | off | the quantiles are pre-stated; the thresholds they resolve to are reported in Part 0 |

Every run is at one day except the two-day anchor. Runs:

- Part A (3): `anchor`, `anchor_1d`, `anchor_4h`.
- Part B (3 beyond `anchor_1d`): gate threshold -20%, -12%, -10% at 1d.
- Part C (8 at 1d): cluster exit, strike {-7%, -10%} x window {3, 5} x factor {1.0, 0.5}, gate -16%.
- Part C4 (up to 4 at 4h, only if `anchor_4h` passes H1): the Part C centre translated to the
  4-hour clock, with and without the consecutive-bucket strike, with and without halving.
- Part D (2): breaker alone at the two quantiles, gate -16%, cluster off.
- Part E (up to 3): the best Part C member by cycle Sharpe among those passing gates 1, 3 and 7,
  combined with each breaker quantile and with the best Part B gate. Declared exploratory.
- Gate 2 (a full re-simulation) for `anchor_1d`, the Part B and Part C centres, and the top three
  new runs by Sharpe gap among cheap-gate passes. Windows A and B for `anchor_1d`, the centres and
  the best run.

About 20 runs plus masks and windows. Plateau neighbours: gate threshold along its axis;
cluster runs along the strike axis at fixed window and factor, and along the window axis at
fixed strike and factor; an endpoint with one neighbour is UNEVALUATED on gate 6
(`standing_gates_40`).

## Hypotheses, pre-registered

- **H1 (cadence).** `anchor_1d` is within the indifference band (0.25 cycle Sharpe) of `anchor`
  and no worse on max drawdown by more than 1 percentage point, with turnover no more than 1.6x;
  `anchor_4h` the same against `anchor` with turnover no more than 3x. A cadence that fails H1
  is itself the finding: its Part C members are reported as diagnostics on a broken baseline,
  not as candidates. Prediction: 1d passes, 4h fails on turnover or on the sparse-period
  forward-fill (a 4-hour clock on weekly marks is 42 identical rows per mark).
- **H2 (the gate alone).** No gate threshold at one day both passes the standing gates and
  reduces the worst five cycles' sum by a third or more relative to `anchor_1d`. Prediction: a
  tighter gate exits the collapses earlier AND cuts rank-churn positions it should not, netting
  to inside the band. (If H2 is false, the cheap change is the answer and H3-H4 are moot.)
- **H3 (the cluster rule).** At least one Part C member passes gates 1, 3, 6 and 7 with a worst
  five cycles' sum at least a third smaller than `anchor_1d`'s and cycle Sharpe no worse than
  `anchor_1d` - 0.10. Named-event diagnostics: the run's position in the vault of the 21 Aug
  collapse closes on or before 20 Aug; its position in the vault of the 21 May collapse closes on
  21 May (day two is not avoidable by construction and the plan says so now).
- **H4 (false positives).** The Part C centre closes no more than 3 of the 8 positions the
  ad-hoc analysis identified as "single-day shock, then recovered" before the day they recovered,
  and the P&L it gives up on those is smaller than the P&L it keeps on the two collapses. Both
  sets are identified by RULE (a day at or below the strike threshold with no second such day in
  the window; a second such day in the window), applied to the anchor's ledger in Part 0, not by
  name.
- **H5 (strike-one de-risking).** Halving on strike one is no worse than not halving on cycle
  Sharpe and better on the worst five cycles. Prediction: within noise; reported.
- **H6 (breaker).** The breaker alone fires fewer than 10 times on the track window and changes
  fewer than 5% of decisions; it is a diagnostic unless it moves the worst cycle.

## What is deliberately NOT tested

- Sub-4-hour reaction. The archive would support an hourly clock on the dense period; the
  settlement model, not the data, is the limit, and 4 hours is the finest clock this plan tests.
- Any change to admission, ranking or the cap. NB37 and NB40 closed those.
- Tuning the strike or window after seeing Part C. The families above are the whole search.
- Using the vaults' names. Every diagnostic that mentions an event is computed by the rule that
  defines the event class.

## Limitations, stated before the run

- **The evidence for the cluster shape is two collapses and three recoveries.** That is a
  pattern in five events on one window, found after the fact. H4's rule-based event classes are
  the honest test; even passing, this is a NOT CONFIRMED-class result on 126-252 decisions.
- **Redemption lag.** If the engine models a settlement delay, a one-day or four-hour exit
  decision may fill later; the realised decision-to-settlement lag is reported for every forced
  exit, and the collapse P&L is attributed to the time the redemption FILLED, not the time it
  was decided. On the 4-hour clock this is the binding constraint and Part 0 documents what the
  engine's vault model actually does (lock-up, epoch, async claim) before any 4-hour run.
- **The 4-hour clock on sparse data.** Before April 2026 marks are weekly to every-other-day;
  a 4-hour row grid on that period is forward-filled almost everywhere and every row-based
  indicator sees runs of zeros. The 4-hour arm is scored on the post-break sub-period as its
  primary window and on the full window as a diagnostic, and the plan says so now.
- **Fees and churn.** A one-day cycle doubles the chances to trade; the fee differential (A6) and
  rank-churn P&L are reported; a run that loses its edge to churn is REJECT on gate 1 or 7, or
  NOT CONFIRMED if it merely drifts inside the band.
- **The two-day anchor is the incumbent.** Any SHORTLIST here is a shortlist for a one-day
  strategy, which is a different deployment; the operator decides whether the cadence change is
  acceptable independently of the exit rule.
- **Marks, not fills.** The daily "close" is the last mark before the decision; the vault's own
  NAV can gap 20% between two marks (the 21 Aug collapse had a single -19.7% mark update). A
  rule that reads T-1 cannot see a gap that happens after T-1; the backtest already models this
  correctly and the plan does not claim otherwise.

## Verdict vocabulary

As in RESEARCH-RULES.md. A member that passes every standing gate and beats `anchor_1d` by
more than 0.25 cycle Sharpe is SHORTLIST (for a one-day strategy). Inside the band: NOT
CONFIRMED (conditionally positive) if it also cuts the worst five cycles by a third; NO EFFECT
otherwise. A run whose only improvement is on the named events and not on the rule-defined
event classes is DIAGNOSTIC.

## Experiment track

### NB42 Part 0 - research, before any backtest

1. Reproduce the ad-hoc archive numbers in a cell: the daily log returns of the anchor's held
   vaults over their holds from the raw archive (last mark per UTC day), the two collapse
   sequences at daily AND 4-hour resolution, the three recoveries, and the single-day-stop table
   at -10% and -15%.
1b. Mark coverage per 4-hour bucket for every vault the anchor held, by regime: the share of
   empty buckets before and after 2026-04-01, so the 4-hour arm's forward-fill exposure is a
   number before it runs.
1c. What the engine's vault model does with a redemption decided at a 4-hour boundary:
   lock-up, epoch and claim timing, read from the code and asserted on one position.
2. Define the two event classes by rule and apply them to the anchor's ledger; print the members.
3. Compute the candidate-day daily-return distribution over the track window and resolve the
   breaker quantiles to thresholds.
4. Verify the new indicator against a hand computation on three vaults.
5. Assert that with all components off the one-day run is identical whether or not the splice is
   present (the parity assertion for this notebook).

### NB42 Parts A-E - the runs above, in that order

Summary table, risk panel (NB40's `risk_row`), trade ledger with exit reasons extended with
"cluster exit", "strike-one halved", "breaker" (NB41's `trade_ledger`), settlement-lag table for
forced exits, standing gates with two-sided plateau, windows A and B, manifest.

### Close-out

Heading from the manifest by a generator with asserted claims; Codex review; RESEARCH-RULES.md
gets a note only if the cadence finding (H1) changes what "the anchor" means for later plans.

## What I expect

H1 holds (the one-day anchor is the two-day anchor with more churn, inside the band). H2's
prediction holds (a tighter gate is a wash). H3 is the coin toss: the cluster centre catches the
August collapse a day or two early and gives back some of it on rank-churn names that had two
bad days and recovered. If H3 passes and H4 passes, the result is NOT CONFIRMED (conditionally
positive) - a defensible exit rule for a one-day strategy, worth a prospective window, not a
proven edge. If H3 fails, the record says the collapses are not separable from the recoveries by
price alone, and the next lever is the redemption clock (intraday), which this track cannot test.

## Definition of done

- Part 0 reproduces the ad-hoc numbers to the reported precision or explains every difference.
- Every run in the families above executed; nothing added after Part C is seen except Part E as
  declared.
- Every heading number cites a cell and comes from the manifest.
- Standing-gate verdicts for every run; the rule-based event-class diagnostics for every run.
- Review applied and logged.

## Review log

_Grok review pending._
