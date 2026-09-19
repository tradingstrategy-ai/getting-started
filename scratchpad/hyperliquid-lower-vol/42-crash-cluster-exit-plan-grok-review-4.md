# Grok review of plan 42, Draft 4 (grok-4.6, reasoning xhigh, no sandbox, 2026-09-19)

Prompt: Draft 4, the Draft 1-3 reviews, RESEARCH-RULES.md, the incumbent's parameters and decide_trades, the engine's settlement and pricing path, harness.py, and the track-history context document.

Draft 4 is a real fix of the catch field, not a polish pass. The confirmatory notebook is now the right shape: Part 0, then a four-point tighter gate at 48 hours, then stop. The remaining holes are heading traps around what “filled at the open” *means*, and one Draft 3 material fix that was applied to the wrong day.

## 1. Draft 3 findings: real fix or wording?

None of the four Draft 3 findings was only reworded. One was applied to the wrong date.

| Draft 3 | Draft 4 | Real or incomplete |
|---|---|---|
| B1 `executed_price` is fee-dirty; match `planned_mid_price` to the **decision bar’s open** at 1e-9; CATCH / PARTIAL / MISS / UNCLASSIFIED in that order, fail closed; assertion on run 1’s trade objects; churn trade pre-registered by rule | Predicate, field, order, fail-closed, run 1 first, churn-by-rule, named bars | **Real** on the field. Residual: the reference open/close is not pinned to the candle **row**; overnight vs intra-day of the collapse bar is not scored; async flags are printed but do not switch the field (Material 2–4) |
| M2 under H0, `gate12_2d` adds 19–20 Aug, not −29.6%; heading order; do not script a 10-point gate-6 spike | August row conditional; increment is the 19–21 Aug cycle P&L; heading order fixed; H2a’s spike is conditional on H0 | **Real in H2a.** **Undone in What I expect**, which still asserts REJECT on gate 6 in the H0-true world (Material 5) |
| M3 first-strike classified every day, so aftermath was averaged in | “First-entry” rows; every-day table an appendix; “so the 22 Aug aftermath is not a row” | **Applied wrongly.** First entry of `first_extreme` *is* 22 Aug (1d) / 23 Aug (2d). That is the aftermath row they thought they had dropped (Material 6) |
| M4 cycle P&L of the two date windows | Table in run 2 and the definition of done | **Real** |
| Minors (Windows A/B dates; “runs 3–5”; one parity epsilon; breaker as step 2c; A6 restored; May warning bar 20 May; lock-up next to H0) | Applied | **Real.** Window B’s start date is still the data period, not the trade start (Minor) |

## 2. The predicate against the engine’s pricing path

`planned_mid_price` on a vault sell **is** the decision bar’s **open**, not the close, and not a raw mark at the decision timestamp.

The path this track actually runs:

1. `run_backtest_inline` defaults to `TradeRouting.default` (`hyper-ai.py` sets `routing = TradeRouting.default`). That is `GenericPricing` → `EthereumBacktestPairConfigurator` for `vault` / `hypercore_vault` → `BacktestPricing` with the default `candle_timepoint_kind="open"`.
2. `BacktestPricing.get_sell_price` calls `candle_universe.get_price_with_tolerance(..., kind="open")`. That returns the `open` column of the daily candle whose timestamp equals the decision (exact hit), or the previous candle’s open within `data_delay_tolerance` (default 2d). Candles are timestamped at the **start** of the UTC day.
3. Vault daily bars come from `convert_vault_prices_to_candles` → `resample_candles`: `open=first`, `close=last` of that day’s `share_price` marks. So the open is the **first mark in that UTC day**, not the last mark, and not necessarily a mark at 00:00.
4. `create_trade(..., planned_mid_price=price_structure.mid_price)` stores that open.
5. `install_vault_redemption_pricing` wraps `get_sell_price` and replaces `TradePricing.price` with `mid * (1 − fee)`. It **does not** touch `mid_price`.
6. `decide_trades` then sets `planned_price = planned_mid_price * (1 − fee)`. `planned_mid_price` stays the open.
7. For a non-async pair, `simulate_spot` fills immediately: `executed_reserve = planned_quantity * planned_price`, so `executed_price` is the fee-dirty open. `executed_at` equals the decision.

H0’s async claim is the right one to *assert*, not to assume: `hypercore_native` is outside `ASYNC_VAULT_FEATURES` and `DELAYED_VAULT_REDEMPTION_FEATURES`, so `_is_async_vault(pair, is_buy=False)` should be false and `DEFAULT_VAULT_SETTLEMENT_DELAY` unused. If that is true, matching `planned_mid_price` to the decision bar’s open at 1e-9 is the correct test of open-vs-close, and Draft 3’s blocking finding is actually fixed.

It is **not** a test of “did we skip the close-to-close crash.” The −29.6% is last mark 20 Aug → last mark 21 Aug. Filling at 21 Aug open skips that only if the first mark of 21 Aug is still near the 20 Aug close. If the crash is already in the open, PARTIAL CATCH *took* the gap. The plan’s own H0 sentence (“the −29.6% and −32.2% closes were never taken”) equates those two things. They are not the same.

If the pair *is* async, `planned_mid_price` remains the request-time open and `executed_price` is a later settlement mid × (1 − fee). The predicate as written would still print PARTIAL CATCH and let confirmatory runs proceed while P&L took the gap. The flags are printed; they do not switch the field.

## 3. Heading surfaces that can still mislead

- “Filled at the 21 Aug open, so the book never took −29.6%” — true only if the overnight/first-mark leg is small.
- “`gate12_2d` avoided the collapse” when H0 is PARTIAL and the crash was intra-day — forbidden by the definition of done, correctly. The reverse case is not covered: if the crash *is* the 21 Aug open, H0 is still PARTIAL, `gate12_2d` selling on 19 Aug *did* avoid it, and the definition of done would treat that heading as a fail.
- “What I expect” still writes REJECT on gate 6 as the H0-true story. H2a correctly says a spike is likely only if H0 fails. A heading that treats a gate-6 pass as a surprise, or a fail as scripted, is the old local verdict in other clothes.
- First-strike: “extreme days have mild forwards” because the first `first_extreme` row is the morning *after* the extreme close (22 Aug on a 1d grid; 23 Aug on 2d). The plan text says that row is not in the table. It is the table.

## 4. Still not measured (and should be)

1. **Overnight vs intra-day of each collapse bar**: previous-bar close, this-bar open, this-bar close, from the **same** daily candle universe the backtest priced against. This is the missing half of H0.
2. **`market_feed_delay`** on the three asserted trades (0 means exact 00:00 hit; >0 means a ffill open and the 1e-9 open-match should fail closed).
3. **Which clock Part 0 step 4 uses.** On the 2d grid, August never enters `first_single` (at 21 Aug the −14.5% day is not the last day of the T-1 window) and `first_extreme` starts after the gap.

It still does not need a 4h backtest, −7%, strike-one, quantile breakers, Part E, or a cluster family as a candidate.

---

## Blocking

None. The catch field is now the one the engine actually stores as the valuation price, the 4-way order can fire, and UNCLASSIFIED fail-closed is specified. A close-valued 21 Aug sell hits MISS (`mid == collapse_close`); an open-valued one hits PARTIAL. That was the Draft 3 blocker.

## Material

### 1. “Filled at the open” is not “skipped the close-to-close crash”

**Section:** One sentence; H0; What I expect; Definition of done.

The −29.6% / −32.2% figures are last-mark to last-mark. `planned_mid_price` is the **first** mark of the decision day. PARTIAL CATCH means the sell was valued at that first mark. Whether that mark still sits near the previous close is a second fact, and it is the one the operator asked about.

Both collapses have marks in every 4-hour bucket, so the first mark of 21 Aug / 21 May is somewhere in 00:00–04:00, not a midnight print by construction. If that first mark has already moved 20–30%, the incumbent *took* the crash at the open, `gate12_2d` selling on 19 Aug *did* avoid it, and the definition of done’s “do not say `gate12_2d` avoided the collapse when H0 held” forbids the true sentence.

**Fix:** Split H0.

- **H0a (price kind):** `|planned_mid_price − decision_bar_open| ≤ 1e-9 × open` on the two collapse sells. This is the Draft 3 predicate. Keep it.
- **H0b (where the crash sits):** from the pricing candle universe, print previous close, this open, this close for 21 Aug and 21 May, and the two legs (close→open, open→close). PARTIAL CATCH skipped the close-to-close bar only if the open→close leg is the crash. If the close→open leg is the crash, say so in sentence (1) of the heading, and the definition of done’s fail condition keys off H0b, not only H0a.

Look the open/close up from `strategy_universe.data_universe.candles` (the daily row at the decision timestamp). Do not call `get_price_with_tolerance(kind="open")` for the reference — that comparison is tautological with `planned_mid_price`. Do not use Part 0 step 1’s last-mark path as the open.

### 2. Async flags are printed and then ignored by the predicate

**Section:** H0; Part 0 step 2.

If `_is_async_vault(pair, is_buy=False)` is true, settlement re-prices at a later `ts` (`pricing.mid_price * (1 − fee)`). `planned_mid_price` is still the request-time open. The 4-way predicate would label PARTIAL CATCH and keep confirmatory status while the book took the gap at settlement.

**Fix:** If any of `is_async_vault()`, `has_delayed_vault_redemption()`, `_is_async_vault(..., is_buy=False)` is true on a collapse sell, the valuation price for the predicate is the settlement mid, `executed_price / (1 − stored_fee)`, matched to bars at `executed_at`. `planned_mid_price` stays in the printout as the request. If the flags disagree with each other, UNCLASSIFIED, stop. Do not let a request-time open carry a catch label for a delayed fill.

### 3. The 4-way predicate is only well-defined on the collapse-day sells

**Section:** Part 0 step 2; run-2 stop rule.

CATCH requires `|mid − decision_open| ≤ 1e-9 × open` *and* decision bar before the collapse bar. That is right for the 21 Aug / 21 May sells. Applied to `gate12_2d`’s 19 Aug sell in a close-valued world: 19 Aug close matches neither 19 Aug open nor 21 Aug close, decision is not after the collapse → UNCLASSIFIED, and the notebook stops even though that fill skipped 21 Aug entirely. In the expected open-valued world the 19 Aug sell matches 19 Aug open and is CATCH; the hole does not bite. It does bite if H0a is MISS and they reuse the same 4-way label for the stop rule.

**Fix:** The 4-way CATCH / PARTIAL / MISS / UNCLASSIFIED predicate applies only to the two collapse sells on run 1 (and, if you want a check, to `gate12_2d`’s August sell *only in the open-valued world*). Run 2’s stop is: the August position was sold on the 19 Aug decision, at the same price kind H0a already measured. After an H0a MISS, later runs are already DIAGNOSTIC; do not UNCLASSIFY them for a close-valued 19 Aug fill.

### 4. First-entry of `first_extreme` is the aftermath row

**Section:** Part 0 step 4; Review log (claims Material 3 closed).

Classification is at T, reading T-1. `first_extreme` = T-1 last day ≤ −20%.

| Clock | First day T-1 last day is 21 Aug −29.6% | 1-day forward from that row |
|---|---|---|
| 1d | **22 Aug** | 22 Aug (after the gap) |
| 2d | **23 Aug** | after the gap |

On 21 Aug, T-1 last day is 20 Aug +2.0%. The plan’s “so the 22 Aug aftermath of a 21 Aug collapse is not a row” is the opposite of the rule. On the 2d grid August never enters `first_single` either: at 21 Aug the window 18–20 Aug is −2.6%, −14.5%, +2.0% — one −10% day, not the last day.

The skippable August path is `first_single` on a **daily** calendar at 20 Aug (T-1 last day = 19 Aug −14.5%), whose 2-day forward includes 21 Aug. May’s skippable path *is* `first_extreme` at 21 May (1-day forward = −32.2%). The two classes do not measure the same thing.

**Fix:** Classify every UTC day, not 2d decisions. State that `first_extreme`’s first row is the morning after the extreme close. Primary August row = first `first_single`; primary May row = first `first_extreme`. The every-day table stays an appendix. Nothing is gated. Do not claim the aftermath row is absent.

### 5. “What I expect” still scripts REJECT on gate 6 under H0

**Section:** What I expect vs H2a.

H2a: the increment under H0 is the 19–21 Aug cycle (~4 points at ~0.32 weight); gate 6 “is whatever the increment makes it — a spike is likely only if H0 fails.”

What I expect, same H0 world: “`gate12_2d` … is a spike on the gate axis, and is REJECT on gate 6.”

That is the Draft 3 local-verdict problem at one remove. A 4-point cycle might fail the 0.25 plateau or might not. Scripting REJECT invites a heading that treats a pass as a surprise.

**Fix:** Delete the gate-6 sentence from What I expect. The expected finding is H0a/H0b, then whether `gate12_2d` sold on 19 Aug, then the cycle P&L table, then the standing gates as measured. Gate 6 is a result, not a plot.

---

## Minor

- **Window B.** A = 2026-01-01 to 2026-07-10 is the old `Parameters.backtest_end` (May in, August out). B is written as 2025-08-01 to 2026-09-09. This track trades from 2026-01-01. Moving `backtest_start` to 2025-08-01 is a different book on sparse data. B is the track window (2026-01-01 to 2026-09-08/09), not a start-date change.
- **Independent candle row.** Say once: decision-bar and collapse-bar open/close are the `open`/`close` columns of that date’s row in the backtest candle universe. Print `price_structure.market_feed_delay` (or equivalent) on the three trades.
- **Forced-exit fill table.** Define forced as pool-removal sells (momentum gate, and cluster if reached). Rank-churn is the one pre-registered example, not 85 extra catch labels.
- **Churn hold.** “Held under four days” = `sell_decision − opened_at` in calendar time, first such rank-exit in calendar order.
- **Part 0 title.** Step 2 is after run 1. The 0a / 0b split already says this; the section heading “before any backtest” does not.
- **H3 `executed_price`.** It is fee-dirty. The print already has `planned_mid_price` beside it; one clause so the lock-up table is not read as a second catch predicate.

---

## Overall verdict

**Worth running with the changes above. Not worth running as written.**

The plan is converging. Draft 3’s blocker is actually fixed: `planned_mid_price` is the daily bar’s open under `candle_timepoint_kind="open"`, the fee overlay does not touch it, and a non-async HyperCore sell fills immediately at the fee-dirty open. That is enough to answer “what price did the backtest use.” It is not yet enough to answer “did that price skip the crash,” because the crash is a close-to-close bar and the fill is a first-mark.

Do not do a fifth wording round. Apply Material 1–5 (H0b’s overnight/intra-day split is the one that still changes a heading; 2–5 are short clauses), then build. Let the assertion print settle whether this pair is async and whether 21 Aug’s open was already the gap. The confirmatory list is done: `anchor` → `gate12_2d` / `gate10_2d` → stop. Cluster stays a labelled diagnostic of a T-1 point that cannot fire before the gap, and only if 19 Aug did not already sell.

Expect REJECT or NOT CONFIRMED. That is still worth the notebook if sentence (1) of the heading is whether the 21 Aug / 21 May sells were the **open**, and whether that open had already moved.
