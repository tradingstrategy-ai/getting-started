# Grok review of the executed NB42 (grok-4.6, reasoning xhigh, no sandbox, 2026-09-19)

Prompt: the executed notebook (cells and outputs), its heading, the plan with its Outcome, the new modules, the build and heading scripts, the four plan reviews and the three Codex reviews, RESEARCH-RULES.md, the engine pricing excerpts, and the track-history context.

The notebook does the confirmatory job Draft 5 specified: Part 0 path, fill kill-switch, tighter gate at 48 hours, one-day clock as a diagnostic, stop when 19 Aug already sells. H0a/H0b and the 19 Aug stop-rule are established by printed trade objects and by the raw archive, not by assumption. `gate12_2d` is NOT CONFIRMED at −0.17 and worse; `anchor_1d` is REJECT on gate 7. Nothing here is a lead.

The defects that remain are heading compression of the live-fill caveat, a mixed-clock Window A sentence, and two Draft 5 diagnostics that were never built. None of them overturns the backtest result.

## Blocking

None. The PARTIAL CATCH labels, the open-to-close legs, the 19 Aug sell, the stop rules, the two Sharpe series on the full window, and the standing-gate verdicts are supported by the cited cells.

## Material

### 1. The closing live-fill sentence treats “first mark unmoved” as “first intraday move is zero”

**Cell:** 0 (findings 1 and 6, “What this means for the track”); plan Outcome.

H0b is true of the **first archived mark**: cell 34’s close-to-open legs are 0.0000, and cell 30’s raw daily/4-hour tables show 21 Aug open 6.5916 = 20 Aug last mark, 21 May open 11.2669 = 20 May last mark. That is a property of these two vaults’ marks, not of `candle_row()`’s resampler.

It is not true of the morning. Cell 30’s 4-hour path:

| bucket | August | May |
|---|---|---|
| 00:00–04:00 of the collapse day | first 6.5916 → last 5.4127 (**−19.7%**) | first 11.2669 → last 10.7978 (**−4.3%**) |

The heading then writes that the backtest open fill is “optimistic by whatever the first intraday move is — zero on these two days”. That collapses two different facts. If a live `vaultTransfer` decided at 00:00 is filled at the **first** mark, optimism is zero on these dates. If it is filled at a later mark the same morning, cell 30 says the August gap is already large inside the first four-hour bucket. The notebook does not measure which NAV HyperCore would have used.

**Fix:** Keep finding 1 as written (first mark unmoved; crash in the open-to-close leg). Change the closing sentence to: the first archived mark was unchanged; the first four-hour bucket was not; live slippage versus that bucket is unmeasured. Do not say “the first intraday move is zero”.

### 2. Window A compares `anchor_1d` Sharpe on a daily clock to the two-day anchor

**Cell:** 0 (Window A sentence); 41.

Cell 41 records Window A through `run_and_record` (Codex 3’s ledger finding is closed). The same-clock contrast is real: `gate12_2d` Sharpe 2.46 against `anchor` 2.90 on 94 two-day cycles, so the tighter gate loses **without** August.

The heading then puts `anchor_1d` 2.56 next to those numbers and says “the one-day clock is worse there too”. That 2.56 is own-clock Sharpe on 189 daily cycles (`periods_per_year` 365). Draft 5 forbade mixing the two series; H1 on the full window correctly used `cycle_sharpe_on_2d_grid` (cell 39: 1.53 against 2.16). Window A never builds that grid.

**Fix:** Either reindex Window A `anchor_1d` equity onto the Window A two-day timestamps and cite that Sharpe, or drop the 1d number from that sentence. Leave `gate12_2d` 2.46 vs 2.90; that is the Window A result.

### 3. H3 / definition of done: no forced-exit fill table, no lock-up census

**Cell:** missing; 34 only asserts the two collapse holds (62 and 136 days) and prints one two-day in-pool example (`LowRiskCryptoGainer`, 11 Jan).

Draft 5 H3 asked, for every forced (pool-removal) exit in every run: decision, `executed_at`, prices, bar open/close, and a count of forced exits on positions younger than 1 day and 4 days. Definition of done repeats the fill table. The build never produces it.

The collapse sells are past both live lock-ups; that part of H0 is not confused with lock-up. The hole is the one-day book: cell 39’s −$13.3k on 105 in-pool sells is a backtest number, and the pre-registered short example is itself a **2-day** hold the engine filled. Live leader (~1 day) / HLP (~4 day) lock-up is exactly where a daily clock would bite. Gate 7 already rejects `anchor_1d`; the census is not required to reject it. It is required before the heading treats “looking every day cost −$12.5k” as an operator fact rather than an engine fact.

**Fix:** From each run’s pool-removal sells, print the fill fields already used in cell 34, and count `hold_days < 1` and `< 4`. Do not re-label them CATCH/PARTIAL. One cell; not a new plan.

## Minor

### 4. Part 0a does not match the ad-hoc stop table and does not say so

**Cell:** 31; definition of done.

Ad-hoc: 10 of 96 positions breach −10%, 8 winners, +$32.3k. Notebook: 9 trigger, 7 winners, $31.9k. Same qualitative conclusion (a same-day stop is net harmful). Definition of done required reproduction or an explanation of every difference. None is given.

**Fix:** One line naming the missing tenth position or the construction difference (log close-to-close on `archive_daily` vs the ad-hoc read).

### 5. Heading “no empty 4-hour bucket” vs cell 31’s 5.3% on the same window

**Cell:** 0 finding 6; 30; 31.

Cell 30’s displayed 4-hour paths have a mark in every printed bucket, including six consecutive down buckets on 20 May. Cell 31’s `bucket_coverage` on `(collapse − 2d, collapse + 1d)` reports `empty_share` 0.053 (1 of 19) for both vaults — the extra 00:00 bucket on the day **after** the collapse, which `archive_4h`’s resample omits. The collapse path is covered; the two cells look contradictory if you do not notice the endpoint.

**Fix:** Cite cell 30 for the path; say the +1 day coverage function includes one empty endpoint bucket. Do not write “no empty bucket, cell 30” next to cell 31’s 5.3%.

### 6. Dense-period “worst 99% empty” is not evidence that a 4-hour book is impossible

**Cell:** 0 finding 6; 31.

`bucket_coverage` scores the whole dense regime for every name the anchor ever held, including before listing. Mean 5.1% / median 1.4% empty says typical coverage is fine; 99% is compatible with a late-listed name. The two collapse vaults are the coverage that matters for this plan.

**Fix:** Restrict “not shown to be possible for the whole book” or drop it. Report median plus the two collapse windows.

### 7. `_is_async_vault(pair, is_buy=False)` is not printed

**Cell:** 26 / 34; Draft 5 Part 0b.

Printed: `is_async_vault` False, `has_delayed_vault_redemption` False, `settlement_override` hardcoded False. For a **sell**, execution’s `_is_async_vault(..., is_buy=False)` **is** `has_delayed_vault_redemption()`, so the missing call would have been False too. `hypercore_native` is outside `ASYNC_VAULT_FEATURES` and `DELAYED_VAULT_REDEMPTION_FEATURES`. The non-async branch of the predicate is still the one that ran.

**Fix:** Print the execution helper, or state in the cell that for sells it equals `has_delayed_vault_redemption()`.

### 8. Stale robustness bullet on churn

**Cell:** 0, last robustness bullets.

One bullet correctly says in-pool P&L is from the pool log, not NB41’s rank reconstruction (cells 37, 39). A later bullet says “the churn P&L uses the same exit classification as NB41”. For `anchor` and `anchor_1d` the two methods agree (85 / −$854 and 105 / −$13,326); for `gate12_2d` they do not (exact 82 / −$5,558 vs recon 83 / −$5,148). The heading’s numbers are the exact ones.

**Fix:** Delete the NB41 sentence.

### 9. Fire-table prose is one-sided; the table is not

**Cell:** 0 finding 3; 32.

14 pre-decision rows in (−16%, −12%], all with `opened < decision` (the 1 Jan Citadel false fire is gone). One is the 19 Aug collapse. Four meet the writer’s `fwd_30d > 0.2` cut, and two of those are Citadel on 3 and 5 Jan — one holding, identical forwards on sparse marks. The other nine include Mahamor −30% and several Goon Edging rows that would have been **helpful** sells. Finding 3 leads with “one collapse and four winners”. The full table is in the heading, and the caveat that this is the anchor’s book, not `gate12_2d`’s, is correct.

**Fix:** Say 14 fires, one collapse, four rows with +20% 30-day vault forwards (two of them one name), and several losers. Do not let “four winners” carry the why.

### 10. Other Draft 5 deviations that do not change the result

- Part 0a runs after run 1 because it needs the ledger. Necessary; already noted in the plan.
- Every-vault paths and the labelled “three recoveries” are not printed; the stop table is the substitute.
- `anchor_1d` splice identity is not asserted. `cluster_on` is False; BASELINE/NB40 parity in cell 28 is the load-bearing check.
- BASELINE parity is the harness’s ±1e−5, not 1e−9 on cycle returns; NB40 five-metric 1e−9 is asserted.
- `sold_at_decision_open`’s “held going in” is `hold_days > 0` (56 on 19 Aug), not `opened_at < decision`. Fine on this trade.
- Cell 41 still contains unused `get_remaining_cost_basis`.
- Plan Outcome rounds sparse empty buckets 82.5% → 83% and reports the 21 Aug increment as +$5.0k; the heading’s $6.7k vs $1.7k is the same cycle (cell 36: 6682 vs 1707).

## The seven checks

### 1. Does the notebook do what Draft 5 said?

Yes, in substance, with the holes in Material 3 and Minor 4/10.

| Draft 5 | What ran |
|---|---|
| Run 1 `anchor`, parity, pool logger | Cell 28: BASELINE inert, NB40 five metrics at 1e−9, `pool_2d` identical on 125 cycle returns, 126 decisions |
| Part 0a path, gate vs daily close, coverage, fires, first-strike | Cells 30–32. Collapse positions by rule (one momentum-gate sell on each named date). 19 Aug T-1 gate −14.501% through 18 Aug vs 19 Aug daily log −14.46% |
| Part 0b fill kill-switch | Cell 34. No UNCLASSIFIED, no MISS, later runs stay confirmatory |
| Run 2 `gate12_2d` / `gate10_2d` | Cell 36–37. 19 Aug sell, cycle P&L, standing gates, worst-five, exact churn, A6 |
| Stop if 19 Aug sold | `AUGUST_CAUGHT True` (cell 36) |
| Run 3 `anchor_1d` diagnostic | Cell 39. H1 fails. `RUN_1D_GATES False`, `RUN_CLUSTER False` with the run-2 reason |
| Window A for the three named labels | Cell 41, via `run_and_record` |
| Manifest → heading | Cell 43; `write_heading_42.py` asserts the claims |

Cluster stays off until a labelled diagnostic; `down_day_count` is T-1 by `get_indicator_value` default `index=-1`; no admission branch. Not executed, correctly.

### 2. Fill assertion and 19 Aug stop-rule

**PARTIAL CATCH is established.** Cell 34: `planned_mid_price` equals `decision_bar_open` at the printed precision (6.59162 and 11.266894); `executed_at` equals decision; feed delay `0:00:00`; both async flags false; `executed_price = mid × (1 − 0.001)`. `classify_fill` matches mid to the candle **open** and the bar date to the collapse date → PARTIAL CATCH. `candle_row()` reads `strategy_universe.data_universe.candles` at `date.normalize()` — the daily row timestamped at the start of that UTC day, which is the row `get_price_with_tolerance(kind="open")` hits at 00:00 with zero delay. It is not a tautological pricing-API round-trip.

**Open-to-close is established, and not only by the resampler.** Cell 34’s `crash_leg()` uses those same candle rows (previous close = open, open-to-close −29.6% / −32.2%). Cell 30’s raw parquet, independently resampled, prints the same first/last prices; the 4-hour tables show the first print of the collapse day’s 00:00 bucket equals the last print of the previous 20:00 bucket, with 26 and 36 marks that day. Forward-fill cannot produce a −29.6% open-to-close on a populated day.

**“Every check” on 19 Aug is established.** Cell 36’s `sold_at_decision_open` table is all `True` for `gate12_2d`: sold, not async, zero delay, executed at the decision, `planned_mid_price` 7.468962 = 19 Aug open, held 56 days, T-1 gate −14.5% ≤ −12%. The 4-way CATCH label is not re-applied. Cell 30’s 19 Aug open 7.4690 equals 18 Aug close, so that fill is the same “unmoved open” pattern as H0b.

### 3. Churn from the in-trade pool log

`churn_pnl_exact` is what it claims: still in `candidate_addresses` at the closing decision → in-pool (ranking or sizing); otherwise pool-removal (gate or universe screen). The tighter-gate recheck (`return_gate` at T-1 ≤ that run’s threshold) is the right one-way correction, because `pool_2d` logs the **anchor’s** −16% pool. Unclassified is 0. H1 uses `pool_1d` for the one-day ledger. Exact and reconstructed agree on `anchor` and `anchor_1d`; they disagree on `gate12_2d` (Minor 8). In-pool is a superset of pure rank-exits (a top-N name closed by sizing still counts). On this window that does not change H1.

### 4. Pre-decision fire count

The overridden `gate_fire_count` holds names with `opened < t` and `closed is None or closed >= t`, weight at the last statistics timestamp **before** t. Cell 32’s 14 rows all satisfy that (Citadel opens 1 Jan, first fire 3 Jan). Interval `(lo, hi]` and T-1 `return_gate` are correct. Heading counts 14 / one collapse / four `fwd_30d > 0.2` match the writer’s cuts; see Minor 9 for the prose.

Breaker: two pre-decision fires, 21 May (the incumbent already sells) and 8 Sep (`DOEZOE`, then +2.3% in five days). It never fires on 20 May or 20 Aug. Correct.

### 5. Sharpe series, Window A, manifest

Full window: `cycle_sharpe` stays on each run’s own clock; H1 and the summary’s “Sharpe on 2d grid” use `sharpe_on_2d_grid` (125 timestamps, no missing, 182.5 periods/year). `gate12_2d` vs `anchor` is same-clock (−0.17). Window A 1d is the exception (Material 2). Manifest is the heading’s only numeric source; `write_heading_42.py` asserts H0, the 19 Aug sell, verdicts, stop rules, and the cited increments. Window A labels are in the manifest.

### 6. Heading numbers vs cells

The cited figures match cells 28–41 (CAGR 35.5% / 37.9%, Sharpe 1.993 / 2.160, mask 0.85, −0.17, 21 Aug $6.7k vs $1.7k, 21 May ~−$1.4k both, churn −$5.6k vs −$0.9k, dense CAGR 38.3% vs 56.3%, 1d grid 1.53 vs 2.16, late CAGR −1.4%, 105 / −$13.3k, Window A 2.90 / 2.46 / 2.56, stop 9/7/$31.9k). Order is H0 → 19 Aug sell → increment → gates. It does **not** say `gate12_2d` avoided the −29.6% bar. NOT CONFIRMED for a worse book inside the 0.25 band is the standing vocabulary; the heading says “wrong side” and “no lead is shortlisted”.

Over-claims are Material 1–2 and Minors 5, 6, 8, 9 — wording, not invented numbers.

### 7. What the operator should take, and what is worth doing next

**Take this as the answer on this engine.**

1. Both named collapses are **intraday after an unmoved open**. The backtest sold at that open. The book took the days before (19 Aug −14.5% close, 20 May −23.9% close), not the −29.6% / −32.2% close-to-close bars. That is why the anchor’s worst-five is −11.0% with or without those cycles, and why the 21 Aug cycle is **+0.9%** for the incumbent (cell 36).
2. A four-point tighter gate at the incumbent cadence does what it was built to do (sells 19 Aug at the 19 Aug open) and is **worse** on the book: NOT CONFIRMED at −0.17, denser-period CAGR 38% vs 56%, in-pool sells −$5.6k vs −$0.9k, and still worse on Window A where August is absent. −16% is not shown to be too loose. Weight into 19 Aug is 6.8%, not the ~32% the plan guessed; the $5k 19–21 Aug increment is a whole-book cycle, not a 10-point save of the −29.6% bar.
3. A one-day clock fails H1 and gate 7 (late CAGR −1.4%). In-pool sells −$13.3k vs −$0.9k. That is a useful negative, not a deployment result (Material 3).
4. A same-day −10% stop still looks net harmful (7 of 9 were winners). A T-1 cluster was correctly not run: it cannot fire before the gap.
5. `measured_8` (+0.21, NOT CONFIRMED) remains the only standing conditionally-positive lead on this track. NB42 adds a negative on the exit side.

**Do not do another in-sample exit search on this window.** 126 decisions still cannot resolve a 0.25 Sharpe gap; this notebook already spent the cheap tests. Do not backtest 4-hour on this indicator stack.

**If anything next, it is not a trade-executor notebook:** which HyperCore NAV a 00:00 `vaultTransfer` actually gets, versus the first mark and versus the first four-hour bucket (Material 1), and how many of this book’s redemptions are younger than the live lock-ups (Material 3). Until that exists, “we already skipped the crash” is a backtest-pricing statement.

## Overall verdict

**The result is worth taking, with the three material caveats above. It is not worth re-running the notebook, and not worth a follow-up in-sample plan.**

Draft 5, as executed, did the thing the earlier drafts were cut down to do: measure the fill, then test the cheaper gate at 48 hours, then stop. H0 held; the cheap test sold on 19 Aug and lost on the book; the one-day clock failed. That is a complete answer to “can we react in a day?” **on this engine**. The heading should stop saying the first intraday move was zero, should not mix Window A clocks, and should not imply the −$12.5k daily-churn figure is live-tradeable until the lock-up census exists. Those are edits and a small diagnostic cell, not a new research programme.
