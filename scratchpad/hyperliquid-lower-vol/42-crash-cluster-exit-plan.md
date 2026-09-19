# Crash exit plan: does the incumbent's exit fill before the gap?

- **Status**: DRAFT 5, EXECUTED 2026-09-19 as [42-backtest-crash-exit.ipynb](42-backtest-crash-exit.ipynb)
  (three Codex review rounds applied). H0a and H0b held as predicted; `gate12_2d` sold on 19
  Aug and is NOT CONFIRMED at -0.17, worse than the incumbent; `anchor_1d` fails H1 and gate 7;
  the one-day gates and the cluster diagnostic were not run by the stop rules. See §Outcome.
  Drafted after four Grok reviews
  ([Draft 1](42-crash-cluster-exit-plan-grok-review.md): "not worth running as written";
  [Draft 2](42-crash-cluster-exit-plan-grok-review-2.md), [Draft 3](42-crash-cluster-exit-plan-grok-review-3.md)
  and [Draft 4](42-crash-cluster-exit-plan-grok-review-4.md): "worth running with the changes";
  the fourth: no blocking finding, "do not do a fifth wording round; apply the five material
  findings, then build"). Draft 5 applies them; see §Review log. Nothing has been run.
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
fire before the gap. **A catch is defined on the fill's VALUATION price**
(`planned_mid_price`, before the redemption fee is taken off; under the engine's default
`candle_timepoint_kind = "open"` and non-async HyperCore pairs this is the decision day's
candle OPEN = the first mark of that UTC day), matched to the decision bar's open: a sell
valued at the open of a bar strictly before the collapse bar caught the gap; at the collapse
bar's open, a partial catch; at or below the collapse bar's close, a miss; anything else,
unclassified and the notebook stops. **"Valued at the open" is not yet "skipped the crash"**:
the -29.6% and -32.2% are last-mark-to-last-mark bars, and whether the first mark of the
collapse day had already moved is a second fact (H0b), measured from the same candle universe.

## What the previous research established, and what this plan does with it

| finding | where | consequence here |
|---|---|---|
| 5 momentum-gate exits made +$25.1k (the vault kept falling after 4 of 5); 85 rank-churn exits, median hold 4 days, net -$0.9k; positions held over 30 days made $37.0k of $36.7k net. | NB41 cell 31 | The exit side is the lever. Admission, ranking and sizing are untouched; NB37 and NB40 closed them. |
| `Realist Capital` (20 Jun - 21 Aug, +$16.9k): daily closes -5.4%, 0%, -8.1%, -2.6%, -14.5%, +2.0%, -29.6% on 15-21 Aug. At the 19 Aug decision the RECONSTRUCTED 14-day gate value at T-1 was -14.5% against a -16% trigger (the 14-day return through 18 Aug; a coincidence of value with the 19 Aug daily close, and Part 0 prints both with timestamps). The next two-day decision is 21 Aug, on which the gate read -27.9% and sold. **Whether the sell was valued at the 21 Aug open (the -29.6% close skipped) or took that close is H0, not a settled fact**: NB41's `vault_return_while_held` and `vault_max_dd_while_held` (-47%) are close-to-close marks through `closed_at`, not the fill. TVL fell with NAV. | NB41 cells 35-36; ad-hoc archive read | The cheap test is `gate_threshold = -0.12` at the incumbent's two-day cadence, which sells on 19 Aug. What it adds over the incumbent depends on H0: the 19 Aug (-14.5%) and 20 Aug (+2.0%) closes if the incumbent already filled at the 21 Aug open; those plus the -29.6% bar only if it did not. |
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
| 0a | Part 0 research (no backtest): the path; gate vs daily close with timestamps; 4-hour coverage; the -12% fire count; the breaker fire count; the first-entry first-strike table | the operator's "how fast" question, and the tighter gate's collateral before it runs | - |
| 1 | `anchor` (2d) | parity against `BASELINE` and splice-inertness, both to 1e-9 on cycle returns | - |
| 0b | **Fill assertion on `anchor`'s trade objects** (needs run 1): H0a (price kind) and H0b (where the crash sits) on the two collapse sells; flags, timestamps and prices on one pre-registered rank-churn sell | whether the incumbent already skipped the collapse closes, and whether the open had already moved | a MISS on either collapse sell under H0a makes every later run DIAGNOSTIC; an UNCLASSIFIED fill stops the notebook until the predicate is understood |
| 2 | `gate12_2d`, `gate10_2d` | H2a at the incumbent's cadence, with -16% (`anchor`) and -10% as the plateau neighbours of -12%; the incremental cycle P&L of 19-21 Aug and 20-21 May against `anchor` | if `gate12_2d` SOLD the August position on the 19 Aug decision, at the price kind H0a measured, the 1d gates and the cluster diagnostic are not run as candidates (the 4-way label is not re-applied to this sell) |
| 3 | `anchor_1d` | H1: is the one-day clock usable at all | diagnostic; `gate12_1d` and `gate10_1d` run only if H1 passes AND run 2 did not sell the August position on 19 Aug |
| 4 | `cluster_1d` (exit a held name whose trailing 3 rows hold 2 or more daily log returns at or below -10%; held names only) | H5, a labelled DIAGNOSTIC of the T-1 point | only if run 2 did not sell the August position on 19 Aug; gate 6 UNEVALUATED by construction |

No breaker run: on a T-1 daily clock a -20% breaker first sees 20 May at the 21 May decision,
which is the decision the incumbent's own gate already sells on (`exit_return_14d` -20.3%), and
first sees August's -29.6% on 22 Aug, after the gap. It cannot beat the incumbent on either
class; Part 0 prints its would-be fire count as a diagnostic and nothing more.

Gate 2 (a full re-simulation) for every run that passes gates 1, 3 and 7. Window A
(2026-01-01 to 2026-07-10: the incumbent's own window, which contains May and NOT August) for
`anchor`, `anchor_1d` and `gate12_2d` - named now, not "the best run"; window A cannot confirm
an August-only effect and the heading says so. The track window (2026-01-01 to 2026-09-08) is
the primary window; the 2025-08-01 start used as "window B" in NB33-NB40 is a different book
on sparse data and is not run here. Nothing is added after these runs are seen.

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

Parity: the two-day `anchor` with `cluster_on = False` reproduces `BASELINE` and, with the
splice present and absent, is identical, both to 1e-9 on cycle returns (standing method rule
4); the same splice identity is asserted on `anchor_1d`.

## Hypotheses, pre-registered

- **H0a (the price kind, Part 0b, the first sentence of the heading).** In this universe a
  HyperCore pair is NOT async (`vault_features` = {hypercore_native}, outside
  `ASYNC_VAULT_FEATURES` and `DELAYED_VAULT_REDEMPTION_FEATURES`), so the engine values a
  redemption at the decision, at the candle OPEN of the decision day (`candle_timepoint_kind =
  "open"`: the `open` column of that date's row in the backtest candle universe = the first
  mark of that UTC day, not necessarily a midnight print), and then takes the redemption fee
  off (`planned_price = planned_mid_price x (1 - fee)`; `executed_price` is fee-dirty).
  Prediction: both collapse sells are PARTIAL catches under the predicate. If either is a MISS,
  no daily-clock rule can do better and every later run is a diagnostic.
- **H0b (where the crash sits).** From the same candle universe, for 21 Aug and 21 May: the
  previous day's close, that day's open, that day's close, and the two legs close-to-open and
  open-to-close. A PARTIAL catch skipped the collapse bar only if the open-to-close leg is the
  crash. Prediction, from the raw archive (to be reproduced from the backtest's own candles):
  the first mark of 21 Aug is 6.5916, the 20 Aug last mark, and the first -19.7% mark update
  came at 03:55; the first mark of 21 May is 11.2669, the 20 May last mark; both crashes sit in
  the open-to-close leg, so the incumbent's open-valued sells never took them. If instead the
  close-to-open leg is the crash on either day, sentence (1) of the heading says so, and a
  `gate12_2d` sell on 19 Aug DID avoid that bar; the definition of done keys off H0b.
- **H2a (the cheap test).** At the 19 Aug two-day decision the reconstructed T-1 gate value
  is -14.5% (the 14-day simple return through 18 Aug, not the 19 Aug daily close, which
  happens to be the same number); -12% and -10% sell on that decision and -16% does not.
  `gate12_2d` therefore sells the August position on 19 Aug, at the price kind H0a measured.
  What it adds over the incumbent is CONDITIONAL on H0a and H0b: if both hold as predicted,
  the 19 Aug (-14.5%) and 20 Aug (+2.0%) closes at about a 0.32 weight - roughly a 4-point
  cycle, reported as the 19-21 Aug cycle P&L on the two-day equity, `anchor` against
  `gate12_2d`; only if H0a is a MISS, or H0b puts the crash in the close-to-open leg, does the
  -29.6% bar enter the increment. Prediction on the standing gates: passes 1, 3,
  7; gate 6 against -16% and -10% is whatever the increment makes it - a spike is likely only if
  H0 fails - and gate 2 may REJECT because the largest contributor is the position moved. Any
  failed standing gate is REJECT and the plan says so before the run. Worst-five cycles with
  and without the 19-21 Aug and 20-21 May date windows are the gate-2 diagnostic; the cycle P&L
  table is the increment. NOT CONFIRMED applies only if every standing gate passes and the
  two-day Sharpe gap is inside 0.25; "do not carry a one-event rule" is an operator prior. A
  heading that says `gate12_2d` avoided the -29.6% bar when H0 held fails the definition of
  done.
- **H2a-collateral.** Part 0 counts, on every two-day decision and every then-held vault, T-1
  `return_gate` in (-16%, -12%] and in (-16%, -10%], with the vault's 5- and 30-day forward
  return. Prediction: 19 Aug is not the only held fire; the others are the tighter gate's
  collateral and their P&L under `gate12_2d` (rank-churn P&L, recovered names sold) is reported.
- **H1 (cadence, diagnostic).** `anchor_1d` on the two-day grid is within 0.25 Sharpe of
  `anchor`, max drawdown no worse by more than 1 percentage point, and
  `churn_pnl_1d >= churn_pnl_anchor - 1000` (USD; rank-exit positions only). Turnover and the
  A6 fee differential reported exactly as A6 defines it (the ratio, applicable only when the
  equity gap exceeds $1,000, otherwise N/A; no local fee gate). Prediction: passes on Sharpe,
  fails or nearly fails on churn.
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
2. **Fill assertion (Part 0b, on run 1's trade objects; the kill-switch).** The trades: the
   incumbent's 21 Aug sell of the August vault, its 21 May sell of the May vault, and the FIRST
   rank-exit sell in calendar order of a position held under four days (pre-registered as that
   rule, so it cannot be chosen). Collapse bars: the 21 Aug and 21 May daily candles. Warning
   bars: 19 Aug and 20 May. For each trade print `get_vault_features()`, `is_async_vault()`,
   `has_delayed_vault_redemption()`, `_is_async_vault(pair, is_buy=False)`, any settlement
   override; the decision timestamp, `executed_at`, `planned_mid_price`, `executed_price` and
   the stored fee; the decision bar's open and close; the collapse bar's open and close; the
   warning bar's open. The valuation price is `planned_mid_price`; `executed_price` is
   `planned_mid_price x (1 - fee)` and is printed beside the fee, never matched. Predicate, in
   this order: if `|mid - decision_bar_open| <= 1e-9 x open` then CATCH if the decision bar is
   strictly before the collapse bar, PARTIAL CATCH if it is the collapse bar, MISS if after;
   else if `mid <= collapse_close x (1 + 1e-9)` or the decision bar is after the collapse bar,
   MISS; else UNCLASSIFIED, fail closed: no catch label, no confirmatory runs, the notebook
   stops until the predicate is understood. The reference open and close are the `open` and
   `close` columns of that date's row in `strategy_universe.data_universe.candles`, never a
   `get_price_with_tolerance()` call (which would be tautological with `planned_mid_price`)
   and never Part 0a's last-mark path; the trade's `market_feed_delay` (or the pricing
   structure's equivalent) is printed, and a non-zero delay means a forward-filled open, which
   the 1e-9 match fails closed on. **If any of the three async flags is true on a collapse
   sell**, the valuation price for the predicate is the settlement mid,
   `executed_price / (1 - stored_fee)`, matched to the bars at `executed_at`, with
   `planned_mid_price` printed as the request; if the flags disagree with each other,
   UNCLASSIFIED. The 4-way label applies ONLY to the two collapse sells on run 1; the
   rank-churn trade gets flags, timestamps and prices, no label; `gate12_2d`'s 19 Aug sell is
   not re-labelled (run 2's stop rule is "sold on the 19 Aug decision at the H0a price kind").
   Only a MISS on a collapse sell demotes later runs; a PARTIAL CATCH is the expected H0a world
   and keeps them. `DEFAULT_VAULT_SETTLEMENT_DELAY` is not the lag. The lock-up assertion (both
   collapse holds, 62 and 136 days, are past the 1-day and 4-day live lock-ups) is printed
   beside H0 so the lock-up table is not read as the gap constraint; "held under four days" for
   the churn trade is `sell decision - opened_at` in calendar time.
2d. **H0b.** For 21 Aug and 21 May, from the candle rows: previous close, open, close, and the
   close-to-open and open-to-close legs. Sentence (1) of the heading states which leg holds
   the crash.
2c. **The breaker fire count.** On every two-day decision, for every then-held vault, the T-1
   daily log return at or below -20%: dates and vaults. A diagnostic; no breaker run exists.
2b. **The -12% fire count.** On every two-day decision, for every then-held vault, T-1
   `return_gate` in (-16%, -12%] and (-16%, -10%]: the dates, the vault, the 5- and 30-day
   forward return. This says whether `gate12_2d` is a one-date intervention or a broad one.
3. Mark coverage per 4-hour bucket for every held vault by regime, and the two collapse paths at
   4 hours. This answers the operator's 4-hour question; it does not lead to a 4-hour backtest.
4. **First-entry first-strike table (diagnostic, gates nothing).** Classified on every UTC
   DAY (not on two-day decisions), at T reading T-1. For every candidate vault, the FIRST day
   on which it enters `first_extreme` (the T-1 last day at or below -20%) and the first on
   which it enters `first_single` (exactly one day at or below -10% in the trailing 3, that
   day the last one, and not extreme); one row per vault per class. By construction the first
   `first_extreme` row is the MORNING AFTER the extreme close (22 Aug for the August vault,
   whose 1-day forward is the aftermath); the skippable August path is `first_single` at 20
   Aug (T-1 last day = 19 Aug -14.5%), whose 2-day forward contains 21 Aug; the skippable May
   path is `first_extreme` at 21 May (T-1 last day = 20 May -23.9%), whose 1-day forward is
   -32.2%. The two classes therefore measure different things and the table says so. Report
   the forward 1- and 2-day log return per class, point estimate and a 30-day date-block
   interval. The every-day classification is an appendix table. Nothing is gated on either;
   the audit retired bounds of this kind, and -10% and -20% were read off the two events, so
   this table is a description, not a test.
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

- The two collapses and three recoveries are five events on one window; every "class" and
  every threshold above was named after seeing them. Nothing in this plan is a non-circular
  test of the cluster shape; Part 0 step 4 describes it, on 126 x ~150 overlapping
  candidate-days.
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

Part 0b decides the notebook. The expected finding is H0a and H0b together: the incumbent's
own gate is valued at the open of the collapse day on both events, and both crashes sit in
the open-to-close leg, so the book never took the -29.6% or the -32.2% bar; it took the days
before. Then `gate12_2d` moves the August exit two days earlier (skipping the -14.5% close),
and the standing gates say what they say about a 4-point cycle - gate 6 is a result, not a
plot. The honest answer to "can we react in a day" is then: **we did not need a faster clock;
the backtest already skipped the collapse closes, and the 14-day gate at 48 hours was two days
early and four points too loose.** If instead H0a is a MISS, or H0b puts a crash in the
close-to-open leg, the constraint is the fill and the heading says so first.

## Definition of done

- Part 0a reproduces the ad-hoc numbers or explains every difference; Part 0b's predicate is
  asserted on three pre-registered trades on run 1's trade objects, with `planned_mid_price`
  matched to the decision bar's open at 1e-9; the -12% and breaker fire counts are printed.
- Runs 1-2 executed; 3 executed as a diagnostic; the 1d gates and the cluster diagnostic
  executed or explicitly not made with the run-2 reason.
- Every heading number cites a cell and comes from the manifest; the two Sharpe series are
  never mixed; standing-gate verdicts for every run; the 19-21 Aug and 20-21 May cycle P&L
  table (`anchor` against `gate12_2d`, two-day equity) as the increment; worst-five with and
  without the two date windows as the gate-2 diagnostic; the fill table (decision,
  `executed_at`, `planned_mid_price`, `executed_price`, fee, bar open/close) for every forced
  exit.
- The heading's order is fixed: (1) H0a and H0b - whether the incumbent's 21 Aug and 21 May
  sells were valued at those days' opens, and whether those opens had already moved; (2)
  whether `gate12_2d` sold the August position on 19 Aug; (3) the incremental cycle P&L
  against the incumbent; (4) the standing gates as measured. A heading that says `gate12_2d`
  avoided the collapse bar when H0b put the crash in the open-to-close leg fails this
  definition; one that says it did not, when H0b put the crash in the close-to-open leg, also
  fails it.
- "Forced exit" in the fill table means a pool-removal sell (the momentum gate, and the cluster
  rule if reached); rank-churn sells are not labelled beyond the one pre-registered example.
- Review applied and logged.

## Review log

- **Draft 4 → Draft 5 (Grok, 2026-09-19; no blocking finding).** Material 1 ("valued at the
  open" is not "skipped the close-to-close crash"): H0 split into H0a (price kind) and H0b
  (which leg holds the crash, from the candle rows), with the archive's first-mark values
  stated as the prediction; the definition of done keys off H0b in both directions. Material 2
  (async flags printed but not used): if any flag is true the predicate's valuation price is
  the settlement mid at `executed_at`; disagreeing flags are UNCLASSIFIED. Material 3 (the
  4-way label is only defined on the collapse-day sells): run 2's stop rule is "sold on 19
  Aug at the H0a price kind"; the label is not re-applied. Material 4 (the first
  `first_extreme` row IS the aftermath): the table is on UTC days, the two skippable paths are
  named as different classes, and the aftermath row is stated, not denied. Material 5 ("What
  I expect" still scripted REJECT on gate 6): removed; gate 6 is a result. Minors: window B
  (a 2025-08-01 start) dropped in favour of the track window; the candle-row reference and
  `market_feed_delay` print; "forced exit" defined; churn hold in calendar time.
- **Draft 3 → Draft 4 (Grok, 2026-09-19).** Blocking 1 (`executed_price` is
  `planned_mid_price x (1 - fee)`, so no fill equals any candle open and the catch predicate
  could never fire; a wide tolerance or "any earlier open" could label a miss a catch; the
  assertion needs trade objects, which only a run has): the predicate is on
  `planned_mid_price` against the DECISION bar's open at 1e-9 relative, with CATCH / PARTIAL /
  MISS / UNCLASSIFIED in a fixed order, fail closed; Part 0b runs after run 1; the churn trade
  is pre-registered by rule; collapse and warning bars are named. Material 2 (under H0
  `gate12_2d` adds the 19 Aug and 20 Aug closes, not the -29.6% bar; the research table
  asserted the H0-false world): the August row is rewritten as conditional, H2a's increment is
  the 19-21 Aug cycle P&L on the two-day equity, the gate-6 prediction is conditional on H0,
  and the heading order is fixed with H0 first. Material 3 (the first-strike table classified
  every day, so aftermath rows were averaged in): first-entry rows per vault per class, the
  every-day table an appendix. Material 4 (no cycle P&L of the two windows): the table is in
  run 2 and the definition of done. Minors: windows A and B dated (A excludes August); "runs
  3-5" fixed; one parity tolerance; the breaker fire count is step 2c; A6 restored to its
  definition; the May warning bar is 20 May; the lock-up assertion sits beside H0.
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

## Outcome, 2026-09-19

- **H0a held, both PARTIAL CATCH.** Non-async HyperCore pairs; both collapse sells valued at
  `planned_mid_price` = the decision day's candle open (6.5916, 11.2669), executed at the
  decision, feed delay zero, `executed_price` = mid x (1 - 10 bps).
- **H0b held: open-to-close on both days.** The candle open equalled the previous close (the
  first mark of each collapse day had not moved); the crash was -29.6% and -32.2% from open
  to close. The incumbent never took either collapse bar.
- **H2a held on the sell and failed on the book.** `gate12_2d` sold the August position on 19
  Aug at the 19 Aug open (every fail-closed check), earning +$5.0k on the 21 Aug cycle against
  the incumbent, and is NOT CONFIRMED at -0.17 cycle Sharpe, passing every standing gate
  (mask 0.85, plateau against -16% and -10%) and worse on CAGR (35.5% against 37.9%),
  Sharpe and drawdown. Its in-pool sells net $-5.6k against the anchor's $-0.9k; the
  pre-decision fire count shows the (-16%, -12%] band catching one collapse and four decisions
  on winners on the way up. The predicted gate-6 question was moot: no spike.
- **H1 failed.** `anchor_1d` on the two-day grid 1.53 against 2.16; in-pool sells
  $-13.3k on 105 positions against $-0.9k on 85; late-period CAGR negative, REJECT
  on gate 7. The one-day gates and the cluster diagnostic were not run (stop rules).
- **The breaker** fires twice on the pre-decision book: on 21 May, the decision the incumbent's
  gate already sells on, and once on a name that then rose. **The first-strike table** is
  descriptive with intervals spanning zero. **4-hour coverage**: 5.1% empty buckets on the
  dense period on average (worst held vault 99%), 83% before April.
- **Answer to the operator.** The crashes are intraday; the backtest's own fills sit at the open
  before them; the incumbent's 14-day gate at 48 hours sold at the last unmoved mark on both
  collapse days. The two pre-registered variants (a four-point tighter gate; a one-day clock)
  are both worse on this window. What the backtest cannot say: a live redemption decided at
  00:00 fills at the vault's next NAV, and the open fill is optimistic by the first intraday
  move - zero on these two days, not zero in general.
