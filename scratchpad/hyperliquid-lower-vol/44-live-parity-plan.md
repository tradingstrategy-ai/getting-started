# Plan 44 - a backtest that behaves like the live hyper-ai executor

- **Status**: DRAFT 2, 2026-09-19, after one Grok review
  ([Draft 1 review](44-live-parity-plan-grok-review.md): "worth running with changes"; four
  blocking findings, five material). Draft 2 applies all of them; see §Review log. The log
  checks L1, L3 (partial), L4, L5 and L6 have been run and their results are in §6 and §9.
  Nothing has been backtested.
- **Notebook to build**: `44-backtest-live-parity.ipynb` (Stage A), from `_build/build_44.py`,
  no hand-edited cells, heading from a manifest with asserted claims. `45-backtest-parity-fixes.ipynb`
  (Stage B) only if Stage A passes its acceptance test.
- **Based on**: [43-research-live-vs-backtest.ipynb](43-research-live-vs-backtest.ipynb), the
  live executor log (`~/hyper-ai.log`, 2026-03-21 to 2026-09-19), the live state snapshot of
  2026-09-19, `~/code/strategies/strategy/hyper-ai.py` (= `hyper-ai-v6.py`), and the annotated
  recommendation list the operator supplied (seven actions; reproduced in §8).

## 1. The question and the acceptance test

The anchor backtest ([02-better-format.ipynb](02-better-format.ipynb)) and the live vault made
the same return on the live dates (+14.3% vs +14.0%, 30 Mar - 8 Sep) on different paths: live
drawdown -16% vs -4.5%; on the only window where the live instance ran the incumbent's logic
(12 Aug - 8 Sep) the anchor made +2.7% while live lost 2.8% (NB43). The books agree on 4.9 of 6
names per decision; the disagreements are at the sixth slot and they churn the two largest
positions, and the weights of the names that remain then differ (Goon Edging 33% live vs 20%).

The question for Stage A: **given what the live executor held and had, does the incumbent's
own `decide_trades` - run in the backtest engine on the backtest's data - make the live
executor's decision?** This is a reconstruction, decision by decision, not a closed-loop
backtest from cash. A configuration that reproduces the live decisions is the parity
configuration; a fix (Stage B) can be evaluated only on a configuration that has one.

**The test is scored on INTENDED books, not on open positions.** The live intended book at a
decision is the set of names given a non-zero new weight in that cycle's "Rebalancing …"
log lines (§9, table L6; six names on every decision from 14 Aug); the live open-position book
carries two-leg withdrawal leftovers (6.75 names on average, up to 9) and is a diagnostic. The
run's intended book is the six names its `decide_trades` selects at that decision.

**Acceptance test for Stage A** (pre-registered, 12 decisions, 12 Aug - 5 Sep, frozen - see §4):
1. Intended-book Jaccard mean >= 0.85 AND exact 6/6 match on at least 8 of 12 decisions,
   reported separately for the two sub-windows 12-22 Aug (6 decisions, the leftover book from
   v1-v4 and the deposit) and 25 Aug - 5 Sep (6 decisions, the aligned week that holds the
   Citadel/AceVault round trips).
2. On decisions where the intended names match 6/6: maximum per-name weight error <= 5 pp and
   top-2 weight within 5 pp of live.
3. Round-trip count (a name dropped from the intended book and re-selected within 4 days)
   equal to live's over the window (live: 2 inside 12 Aug - 5 Sep by the L6 table, Citadel
   27→29 Aug and AceVault 29→31 Aug; Gucky_4coin_2dot5x 31 Aug→5 Sep is outside the 4-day rule;
   the count is computed by rule, names are labels).
4. Every mismatching decision is classed by mechanism (§3) or `unexplained`; more than two
   `unexplained` fails the test whatever the mean.

There is no other pass path. If the test fails, the heading names which mechanisms were tested
and what each moved, and Stage B is not built.

## 2. Facts established so far (each with its source)

F1. **The backtest's vault universe drops vaults that are closed to deposits at build time, for
the whole history.** `build_hyperliquid_vault_universe(min_tvl=7500, min_age=0, top_n=9999)`
is called with the default `include_closed_vaults=False`, which excludes every Hypercore vault
whose `deposit_closed_reason` is set in the catalogue *at the moment of the call*
(`tradeexecutor/curator/vault_universe_creation.py:347`). The research notebooks read a cached
universe of 339 vaults written 2026-09-09. The three vaults the live executor held that the
backtest universe lacks - Danny Ocean, Gucky_4coin_2dot5x, HYPErQuantum4 (NB43 cell 35) - all
have continuous marks since 2025, TVL above $7.5k throughout August, and were closed to deposits
when the cache was written (archive `deposits_open`: Danny Ocean "disabled by leader" from
17 Aug; the two others "leader share near minimum" from 29 Aug). They were open when the live
executor bought them. The same builder also drops sub-vaults, `Blacklisted`/`Dangerous` risks,
`malicious`/`broken` flags, unknown protocols and non-USD denominations, and applies the TVL
floor to PEAK TVL as of the call; `include_closed_vaults=True` addresses only the closed rule.

F2. **The live executor rebuilds its universe at every decision, not only at restart.** "Loaded
N vaults from remote vault metadata" appears at every cycle timestamp, N moving 330 → 345 → 341
→ 343 between 12 Aug and 19 Sep; the log prints counts, not addresses (L2 cannot be completed
from the log). The live inclusion set (`Pairs meeting inclusion criteria`, a CURRENT-TVL screen
on that universe) moved 191 → 178. **Live did NOT sell held names when their deposits closed**:
Danny Ocean (closed 17 Aug) was held to 22 Aug; Gucky_4coin_2dot5x (closed 29 Aug) was held on
31 Aug and re-bought 5 Sep. So a per-cycle "drop closed" rule is not what live did; v6 keeps
held names through a closed window (`hyper-ai-v6.py:911-926`) and the catalogue evidently
still listed them.

F3. **The live executor reads the T-1 daily row by direct timestamp hit, like the backtest, but
that row is built from a remote parquet that was 3 to 61 hours stale.** `get_indicator_value`
floors the cycle timestamp to the day and reads `ts - 1 day` (`strategy_input.py:463-475`); with
the universe forward-filled to the cycle timestamp every daily row exists, so the direct hit
succeeds and no partial-current-day row is read. What differs is the CONTENT of the T-1 row.
The log's "Vault history freshness summary" gives `filtered_max_timestamp` (the last mark in the
data the live run loaded) per decision (§9, table L1). On 5 of the 18 live decisions the T-1
row was incomplete or stale: 22 Aug (T-1 = 21 Aug, marks to 15:34), 25 Aug (24 Aug to 14:16),
31 Aug (data ended 29 Aug 03:52 - the "30 Aug" row is a forward-fill of a 29 Aug partial),
7 Sep (6 Sep to 20:00), 9 Sep (8 Sep to 17:13). On the others `filtered_max_timestamp` is on
the decision date and T-1 was complete. Per-vault staleness on top ("Vault candle data is stale
(>24h) for 38 vault(s); 307 up to date", 29 Aug). The 27 and 29 Aug decisions - the round
trips - read COMPLETE T-1 rows; those mismatches are not D3.

F4. **Live thresholds are the $150k constants, and they suppressed a trim on almost every
decision.** `individual_rebalance_min_threshold_usd = 75`, `sell_rebalance_min_threshold_usd =
750`, `sync_cash_headroom_usd = 75` are derived from `initial_cash = 150_000` at class creation
(hyper-ai-v6.py:334-356) and do not follow live equity ($30k on 12 Aug, $55k on 27 Aug, $50k
now). L4: 37 "Individual trade size too small" lines since 12 Aug, 32 of them for sells between
$75 and $750 (sum $13.9k, one to three per decision, every decision) - the $750 sell softband,
which at $50k is 1.5% of equity, not the documented 0.5%. The research anchor runs at $100k
(`cell6_enhanced`), so its thresholds are $50 / $500 - a third configuration.

F5. **The sixth slot is what flips, and on the round-trip days it is a vault outside the
backtest universe that takes it.** Log, 27 Aug 16:26: live intended six Sequoia, Octavious,
Buyback Spread Engine, Gucky_4coin_2dot5x, Goon Edging, AceVault; Citadel (held at 32%) to 0.
29 Aug 16:35: Citadel back at 33%, AceVault (34%) to 0. The anchor ranked Citadel 6 of 163 on
27 Aug and AceVault 6 of 161 on 29 Aug (NB43 cell 35), with Gucky_4coin_2dot5x absent from its
universe. Gucky_4coin_2dot5x is in the live intended six on 27, 29 Aug and on 5, 9, 11, 13, 15,
17, 19 Sep (L6).

F6. **Weights differ because the book differs, and because capacity binds.** With Citadel out
on 27 Aug, live Goon Edging went from 19.8% to 33.0% (log: "old weight 0.198499, new weight
0.330000, size diff +$7,078"); the anchor held it at 19.6%. Goon Edging fell 11% in the
following week and cost live 3.2% of equity against the anchor's 1.8% (NB43 cell 41). The same
27 Aug cycle discarded $14.6k of allocation for lack of lit liquidity (`capped_by_pool_size`:
Gucky_4coin_2dot5x's TVL was $7-15k; 33% of it is $2.3-5k, and the position was $3.4k).

F7. **Fill timing is not the cause** of the P&L gap: 89 live fills, net -$365 against the day's
first mark (NB43 cell 43). This says nothing about two-leg settlement leftovers.

F8. **Capacity binds live at $30-55k.** "Discarded allocation because of lack of lit liquidity"
was $0 on 12-16 Aug and $5.6k-$18.4k on 10 of the later decisions (NB43 cell 35). The backtest
applies the same `USDTVLSizeRiskModel(per_position_cap=0.33)` on archived TVL, but no notebook
has logged `alpha_model.size_risk_discarded_value` in a backtest.

F9. **Execution noise is large.** 964 of 1,709 live trades carry no value; 323 are repairs;
zero-value buy/sell batches on 23 Aug and 7 Sep (NB43 cell 31). HyperCore redemptions run as
"up to two protected withdrawal legs", so a closed name can stay open for hours; the live
open-position book had 7-9 names on 20, 22, 25, 31 Aug and 9, 11 Sep while the intended book was
six.

F10. **Cadence and clock.** Daily decisions under v1-v3 until 10 Aug; two-day from 12 Aug on
EVEN August dates (12, 14, …, 22), then 25, 27, 29, 31 Aug, 1, 3, 5, 9, 11, 13, 15, 17, 19 Sep
(no decision on 7 Sep: the 7 Sep 04:08 restart re-ran the 5 Sep cycle's repairs; cycle 113 is
5 Sep, cycle 114 is 9 Sep). The research 2-day grid from 1 Jan falls on ODD August dates, so
NB43's `at_or_before` pairing compared live 12 Aug with backtest 11 Aug (reading 10 Aug) for the
whole first sub-window - a one-day phase error until the 25 Aug restart put both clocks on the
same dates. Decision hour drifted 11:00 → 16:30 → 13:00 → 04:15 UTC with each restart.

F11. **The 12 Aug live book is inherited, not chosen.** Live 12 Aug: equity $30.2k, top signal
22Cap (anchor rank 13 of 173), 2 trades decided, 4 suppressed as too small; the book (22Cap,
Citadel, Danny Ocean, Mad Scientists, Realist Capital, Scared Money) is v1-v4's. A run from
cash on 12 Aug would open six fresh names; live did not. The 19-20 Aug deposit took equity from
$31k to $50k.

## 3. Mechanisms, and how each is represented

| # | Mechanism | Evidence | Representation in Stage A | Prediction (falsifiable) |
|---|---|---|---|---|
| D1 | Universe: closed-now vaults missing from the whole backtest history | F1, F5 | `include_closed_vaults=True` (new cache key); per-date openness stays with the pricing model's `can_deposit` (archive `deposits_open` at or before T, point-in-time). Residual membership differences (risk flags, peak-TVL-as-of-now, metadata misses, listings) are classed `universe_snapshot` and cannot be replayed from the log (counts only) | On 27 and 29 Aug the one-step replay selects Gucky_4coin_2dot5x and drops Citadel / AceVault as live did. If it does not, D1 is not the round-trip mechanism |
| D3 | Stale / partial T-1 row in the live data | F3 | Offline, not in the engine: recompute the four ranking inputs (360-day CAGR, 45-day Sortino, 14-day gate, 90-day inverse vol) from the raw archive for every candidate at each live decision, (a) with marks through the previous UTC midnight (what the backtest's T-1 row contains) and (b) with marks cut at that decision's `filtered_max_timestamp` (what live's T-1 row contained); rank both with the incumbent's composite; score each against the live intended six. Named `stale_row` when (b) matches and (a) does not | Matters on the 5 stale decisions (22, 25, 31 Aug; 7, 9 Sep) and not on 27/29 Aug. If (a) and (b) select the same six on the stale decisions, D3 is dropped |
| D4 | Capital and thresholds | F4, F6, F11 | The one-step replay uses live equity and the live pre-decision book at each decision; thresholds pinned to the live constants ($75 / $750 / $75). A scaled-threshold arm (0.05% / 0.5% of equity) is reported as a sensitivity | Pinned thresholds suppress the same trims L4 lists (32 sells of $75-$750); names unaffected, weights affected by <= 5 pp on matched decisions |
| D5 | Decision clock and phase | F10 | Every run is scored on the live decision's CALENDAR DATE (00:00 that UTC day), never `at_or_before`. The one-step replay decides on that date; the closed-loop arm uses `cycle_1d` with a mask of the live dates | First-order for 12-22 Aug: NB43's 0.33-0.50 Jaccard there is partly the phase error. Re-scored on the calendar date, the anchor's own overlap on 12-22 Aug rises |
| D6 | Capacity | F6, F8 | `size_risk_discarded_value` logged on every run at every decision, beside the live series. A measurement, not an arm; the weight gate applies only on name-matched decisions | Same decisions discard; on 27 Aug the replay discards within 30% of $14.6k |
| D7 | Execution leftovers (two-leg withdrawals, repairs) | F9 | Diagnostic only: count of live open names beyond the intended six per decision, and hours from decision to close. NOT modelled with `DEFAULT_VAULT_SETTLEMENT_DELAY` (2 days, ERC-7540; HyperCore native fills at the decision in the backtest and in minutes to hours live) | Not tested; action 4 is live-executor work |
| D8 | Data revision (live valuation vs archive mark) | archive `hypercore_repair_status = approximated_pnl_nav` on AceVault; L3 partial | Live position value per unit from the log's "valuation updated" lines vs the archive's last mark at that instant, on TRADE-FREE intervals only (a resize changes the unit) | If any ranking input for a rank-5-to-8 candidate differs by enough to change its rank on a decision, that decision is classed `data_revision` |

Dropped from Draft 1: `A8 read_T` (`index=0` in the engine is the complete decision day - a
look-ahead, not a partial-day bound); `A4 pit_drop_closed` (F2: live did not drop held closed
names); `A7 delayed` (wrong delay class). D2 is retired; residual universe membership is
`universe_snapshot`.

The annotation's seven actions map as: action 1 (persist and replay the universe) = D1 as far as
the archive allows, residual `universe_snapshot` - it CANNOT be fully replayed until the live
executor writes per-cycle address lists (action 7 first); action 5 (live NAV, thresholds from
equity) = D4; action 6 (fixed cut-off, no restart decisions) = D3 + D5 - parity REPRODUCES the
restart dates and the stale rows; the fix is on the live side; actions 2 and 3 are Stage B;
actions 4 and 7 are live-executor work.

## 4. Stage A - the one-step replay (`44-backtest-live-parity.ipynb`)

**Window, frozen**: the 12 live decisions from 12 Aug to 5 Sep 2026 (the candle cache ends
9 Sep; the 9-19 Sep decisions, which include the $18k discard and the second AceVault round
trip, are a separate follow-up after a fresh data load and are NOT part of this test).

**Primary arm - one-step replay** (`R`). For each live decision date d:
1. Seed: a backtest over [d - 1 day, d] whose first cycle (d - 1, 00:00) buys the live
   PRE-decision book - the live open positions at the decision instant, at their live USD
   values, from the state snapshot - with `initial_cash` = live total equity at that cycle
   (from the cycle message). Positions fill at the archive's d - 1 open; the value drift to d
   is reported. Names the backtest universe lacks are seeded only if the pit universe has them;
   otherwise the decision is classed `universe_snapshot` before it is scored.
2. Decide: the incumbent's `decide_trades`, unchanged, at d 00:00, reading T-1, with the pit
   universe (D1), pinned thresholds (D4), pool logger and `size_risk_discarded_value` logger on.
3. Score: the selected six vs the live intended six (L6); weights vs live weights; discarded
   allocation vs live; trades generated vs live trades decided; the reasons for each name on one
   side only (rank, gate, universe, closed window, size cap, min-hold).
This is 12 short backtests. Seeding is the engine's own buy at the decision - no new engine
code; if the seed cannot be placed (e.g. the pair is not in the universe) the notebook says so.

**Sensitivity arms on the same one-step design**: `R_scaled` (thresholds 0.05% / 0.5% of live
equity, D4 sensitivity); `R_asis` (the as-is 339 universe: isolates D1); `R_100k` (equity $100k
with the live book scaled up: isolates capital in D6).

**Closed-loop arm** (`C`): only if `R` passes: `cycle_1d` masked to the live dates, seeded once
with the live 12 Aug PRE-decision book at $30.2k, run to 5 Sep with pinned thresholds and the
pit universe. Reported: its own intended-book Jaccard and 6/6 count against live; the equity
path beside the live share price (12 Aug - 5 Sep); round-trip count; the 27 Aug - 5 Sep P&L
share per vault beside NB43 cell 41. The 19-20 Aug deposit is not injected (the engine cannot);
`C` therefore under-sizes after 20 Aug, and its weights are read with that caveat; names are not
affected by the dollar size except through the size cap.

**D3 cell** (offline, independent of the runs): as in §3, for all 12 decisions; output: for each
decision, the six selected by (a) midnight-cut and (b) stale-cut rankings, and the live six,
with the match counts. Requires the archive marks and the log's `filtered_max_timestamp`
(§9, L1), and the incumbent's indicator code applied to a mark series cut at a timestamp.

**Also reported, not gated**: the pit universe on the full track window (1 Jan - 8 Sep) beside
the anchor - CAGR, Sharpe, max drawdown, the single-vault mask, the ledger diff. D1 is a
data-correctness change; if it moves the anchor, the track's anchor changes and that is recorded.
The NB43 overlap table re-scored on calendar dates (D5) is displayed beside NB43's published
0.64 so the two scorers are not confused.

**Stop rule**: the acceptance test in §1, on `R`. Pass → `R`'s configuration (pit universe,
pinned thresholds, live seed) is the parity configuration and Stage B is built on it. Fail →
the heading lists each decision's class (`universe_snapshot`, `stale_row`, `capacity`,
`threshold`, `phase`, `data_revision`, `unexplained`) and Stage B is not built.

## 5. Stage B - the fixes (`45-backtest-parity-fixes.ipynb`)

Only if Stage A passes. Six full-window runs plus replays, not twelve.

Full-window evaluation is on the TRACK configuration ($100k, 2-day grid from 1 Jan, pit
universe) under the standing gates (1 positive return, 2 single-vault mask, 3 held-book
volatility, 6 plateau against the pre-registered neighbours, 7 sub-period sign; gate 5 not
applicable; gate 8 reported as a diagnostic; 0.25 indifference band). The replay evaluation is
DESCRIPTIVE on the closed-loop `C` seeded as in §4: round-trip count, turnover, top-2 weight
persistence, discarded allocation, the 27 Aug - 5 Sep P&L share.

| Arm | Rule | Runs | Targets |
|---|---|---|---|
| `B1 hysteresis` | enter at rank <= 6; an incumbent keeps its slot while rank <= 9; the gate, quarantine and closed-window rules override | centre + neighbours exit-rank 8 and 10 | sixth-slot churn (F5) |
| `B3 capacity-aware` | walk the ranking; skip a candidate whose executable size at the 33% pool cap is below 0.5 × its target; stop at six names (`max_assets_in_portfolio` unchanged) | centre + neighbours 0.25 and 0.75 | discarded allocation and the concentration it causes (F6, F8); expect fewer discarded dollars and a lower top-2 weight, still six names |
| `B1+B3` | both | one run | the 27 Aug event is sixth-slot AND a $14.6k discard |
| `B2 min-hold` | incumbent keeps its slot H days after entry unless the gate fires; H = 4, 6, 8 | replay only (NB40: inert on the full window) | churn by time |
| `B4 thresholds from equity` | buy / sell / headroom = max($5, equity × 0.05% / 0.5% / 0.05%) read at the decision | replay only (already scaled at $100k) | F4 |

Predictions: `B1` and `B3` land inside the band on the full window (NO EFFECT / NOT CONFIRMED)
and the decision on carrying them is the operator's on priors plus the replay; `B1` cuts the
replay's round trips to zero; `B3` cuts discarded dollars by more than half on the 27 Aug and
5 Sep decisions. No name of any vault enters any rule or any verdict.

## 6. Log checks - status

| Check | Status | Result |
|---|---|---|
| L1 data cut per decision | DONE, all decisions | §9 table; 5 of 18 decisions read a stale or partial T-1 row |
| L2 per-cycle universe membership | NOT POSSIBLE from the log (counts only) | residual = `universe_snapshot`; F2 shows live did not drop held closed names |
| L3 live valuation vs archive | PARTIAL | 1,064 four-hourly valuation steps for four vaults: mean abs step difference 0.25 pp, but the largest differences coincide with resizes (the unit changes); the notebook restricts to trade-free intervals |
| L4 suppressed trims | DONE | 32 sells of $75-$750 suppressed since 12 Aug, $13.9k, every decision |
| L5 survivor count | DONE | "Selected survivor signals: 7" = 6 held + 1 closing (29 Aug: signals #1-#7, #7 AceVault at 0) |
| L6 live intended six per decision | DONE | §9 table |

## 7. Out of scope, and why

- Changing the ranker or the sizing rule (NB03-NB42: nothing beat the incumbent inside the
  band on this window).
- Replaying the live period before 12 Aug: three other strategy versions traded it.
- Injecting the Lagoon vault's own deposits and redemptions into a backtest (the engine cannot).
- Replaying the exact live catalogue per cycle (the log has counts, not addresses; action 7
  must come first).
- The hourly remote parquet the live executor loaded (not archived; the research archive is
  the nearest available - D8 bounds the difference).
- An execution state machine and per-cycle diagnostic artefacts (actions 4 and 7): live-executor
  changes, recommended, not testable in a backtest.
- Any statistical claim on the replay: 12 decisions.

## 8. The operator's annotated recommendations (summary, for the reviewer)

1. Persist the eligible universe for every decision and replay that exact snapshot.
2. Rank hysteresis: enter at rank <= 6, exit only below rank 8-10; min hold 4/6/8 days.
3. Capacity-aware selection before choosing six vaults.
4. Lock vaults while deposits/redemptions are pending (execution state machine).
5. Backtest at actual live NAV and scale thresholds from current equity.
6. Fixed UTC data cut-off; no restart-triggered decisions.
7. Record full decision diagnostics; fix the "Selected survivor signals" count.

## 9. Log extracts (the evidence for F3, F5, F10, F11)

**L6 - live intended six (names with non-zero new weight) and closes, per decision.** Weights
are the normalised targets from the log.

| decision (UTC) | intended six (weight) | closed |
|---|---|---|
| 12 Aug 10:57 | 22Cap .33, Citadel .33, Danny Ocean .17, Mad Scientists .09, Realist Capital .04, Scared Money .04 | - |
| 14 Aug 11:06 | Gucky_1coin .33, Citadel .33, Satori .25, Danny Ocean .05, Mad Scientists .03, Realist Capital .01 | Scared Money, 22Cap |
| 16 Aug 11:17 | Gucky_1coin .33, Citadel .33, AceVault .20, Danny Ocean .07, Mad Scientists .05, Realist Capital .02 | Satori |
| 18 Aug 11:32 | Citadel .33, HYPErQuantum4 .15, AceVault .31, Danny Ocean .11, Mad Scientists .08, Realist Capital .02 | Gucky_1coin |
| 20 Aug 11:47 | Citadel .33, AceVault .24, pmalt .14, Goon Edging .11, Danny Ocean .11, Mad Scientists .07 | Realist Capital, HYPErQuantum4 |
| 22 Aug 12:08 | Citadel .33, AceVault .33, Goon Edging .16, Mad Scientists .11, Octavious .06, Sequoia .01 | Realist Capital, Danny Ocean, pmalt |
| 25 Aug 16:17 | Citadel .33, AceVault .33, Goon Edging .20, Octavious .07, Buyback .05, Sequoia .02 | Realist Capital, Mad Scientists |
| 27 Aug 16:25 | Gucky_4coin .06, AceVault .33, Goon Edging .33, Octavious .14, Buyback .10, Sequoia .03 | Citadel |
| 29 Aug 16:33 | Citadel .33, Gucky_4coin .09, Goon Edging .33, Octavious .13, Buyback .10, Sequoia .03 | AceVault |
| 31 Aug 16:39 | Citadel .33, AceVault .33, Goon Edging .20, Octavious .07, Buyback .05, Sequoia .02 | Gucky_4coin |
| 1 Sep 13:0x | (repair cycle; no new intended book in the log) | - |
| 3 Sep 13:04 | Citadel .33, AceVault .33, Mad Scientists .17, Octavious .09, Buyback .06, Sequoia .02 | Goon Edging |
| 5 Sep 13:12 | Citadel .33, Gucky_4coin .07, AceVault .33, Octavious .18, Buyback .07, Sequoia .02 | Mad Scientists |
| 9 Sep 04:17 | Citadel .33, Gucky_4coin .09, Mad Scientists .24, Octavious .25, Sequoia .05, DOEZOE .04 | Buyback, AceVault |
| 11 Sep 04:25 | Citadel .33, Gucky_4coin .09, AceVault .31, Mad Scientists .17, Octavious .07, Buyback .03 | Sequoia, DOEZOE |
| 13 Sep 04:33 | Citadel .33, Gucky_4coin .09, AceVault .30, Mad Scientists .20, Octavious .07, Sequoia .01 | Buyback |
| 15 Sep 04:39 | Citadel .33, Gucky_4coin .09, AceVault .30, Mad Scientists .21, Octavious .06, Sequoia .01 | - |
| 17 Sep 04:43 | Citadel .33, Gucky_4coin .09, AceVault .31, Mad Scientists .21, Octavious .06, DOEZOE .00 | Sequoia |
| 19 Sep 04:47 | Citadel .33, Gucky_4coin .09, Mad Scientists .32, Octavious .20, Sequoia .04, DOEZOE .02 | AceVault |

The 1 Sep entry: the state's cycle list has decisions on 31 Aug 16:39 and 3 Sep 13:04 with
trades executed 1 Sep 13:00-13:03 (the 31 Aug decision's trades, executed after a restart);
the notebook resolves this from the state's cycle messages, and the frozen 12 decisions are
those with a cycle message from 12 Aug to 5 Sep (NB43 cell 35 lists them).

**L1 - the live data cut per decision** (`filtered_max_timestamp` = last mark in the loaded
history; the T-1 row the strategy read is complete only if this is on the decision date).

| decision | filtered_max_timestamp | T-1 row | class |
|---|---|---|---|
| 12 Aug 10:57 | 12 Aug 10:07 | 11 Aug complete | ok |
| 14 Aug 11:06 | 14 Aug 06:39 | 13 Aug complete | ok |
| 16 Aug 11:17 | 16 Aug 10:39 | 15 Aug complete | ok |
| 18 Aug 11:32 | 18 Aug 07:22 | 17 Aug complete | ok |
| 20 Aug 11:47 | 20 Aug 07:25 | 19 Aug complete | ok |
| 22 Aug 12:08 | 21 Aug 15:34 | 21 Aug PARTIAL (to 15:34) | stale_row |
| 25 Aug 16:17 | 24 Aug 14:16 | 24 Aug PARTIAL (to 14:16) | stale_row |
| 27 Aug 16:25 | 27 Aug 11:06 | 26 Aug complete | ok |
| 29 Aug 16:33 | 29 Aug 03:52 | 28 Aug complete | ok |
| 31 Aug 16:39 | 29 Aug 03:52 | 30 Aug = forward-fill of 29 Aug 03:52 | stale_row (61 h) |
| 3 Sep 13:04 | 3 Sep 11:39 | 2 Sep complete | ok |
| 5 Sep 13:12 | 5 Sep 09:50 | 4 Sep complete | ok |
| 9 Sep 04:17 | 8 Sep 17:13 | 8 Sep PARTIAL (to 17:13) | stale_row |
| 11 Sep 04:25 | 11 Sep 00:30 | 10 Sep complete | ok |
| 13 Sep 04:33 | 13 Sep 00:59 | 12 Sep complete | ok |
| 15 Sep 04:39 | 15 Sep 02:56 | 14 Sep complete | ok |
| 17 Sep 04:43 | 17 Sep 01:09 | 16 Sep complete | ok |
| 19 Sep 04:47 | 19 Sep 01:43 | 18 Sep complete | ok |

(The 7 Sep 04:09 restart loaded data to 6 Sep 20:00 but made no decision.)

## Review log

- Draft 1: written 2026-09-19 from NB43, the log and the strategy file. Log checks L1 (one
  decision) and L5 done before sending. Sent to Grok (grok-4.6, reasoning xhigh, no sandbox).
- Draft 1 review ([44-live-parity-plan-grok-review.md](44-live-parity-plan-grok-review.md)):
  "worth running with changes". Applied in Draft 2:
  - Blocking 1 (the acceptance test could pass with the sixth slot wrong, or fail on two-leg
    leftovers): scored on INTENDED books from the log (L6), exact 6/6 rate, split sub-windows,
    weight and top-2 error on matched decisions, round-trip COUNT; the D3 pass path removed.
  - Blocking 2 (a run from cash on 12 Aug is not a replay): the primary arm is a ONE-STEP
    replay seeded with the live pre-decision book and equity at every decision; the closed-loop
    is seeded with the 12 Aug pre-decision book and is secondary.
  - Blocking 3 (D5 is first-order; NB43's clock was phase-shifted for a week; no 7 Sep
    decision): every run scored on the live calendar date; F10 corrected; window frozen at
    12 decisions to 5 Sep.
  - Blocking 4 (D3 asserted): the engine code was read - the live reads T-1 by direct hit, not a
    partial current day; the mechanism is restated as the STALE T-1 row, with the per-decision
    data cut extracted for all 18 decisions (5 stale); `A8` dropped; D3 is an offline probe, not
    a pass path.
  - Material 5 (D1 is a static superset; D2 is not what live did): `include_closed_vaults=True`
    kept as the D1 representation with the residual classed `universe_snapshot`; F2 corrected
    with the evidence that live held closed names; `A4` dropped.
  - Material 6 (names without weights do not answer the operator): weight gate on matched
    decisions; discard logged on every run; capital sensitivity arm.
  - Material 7 (Stage B gate stack and size): six full-window runs on the track configuration;
    `B2` and `B4` replay-only; `B1+B3` pre-registered; `B3`'s prediction rewritten (six names,
    fewer discarded dollars, lower top-2); no named-vault outputs.
  - Material 8 (`A7` used the ERC-7540 delay): dropped; execution leftovers are a count.
  - Material 9 (log checks not run): L1, L4, L5, L6 done and tabulated; L2 shown to be
    impossible from the log; L3 partial with the confound named.
  - Minor 10-14: window frozen; F7 scoped; build process stated; A0 replaced by the calendar-date
    re-score of NB43; D8's 1% replaced by "enough to change a rank at the boundary".
