# Grok review of plan 42, Draft 3 (grok-4.6, reasoning xhigh, no sandbox, 2026-09-19)

Prompt: Draft 3, the Draft 1 and Draft 2 reviews, RESEARCH-RULES.md, the incumbent's parameters and decide_trades, the engine's settlement and pricing excerpts, harness.py, and the track-history context document.

Draft 3 is a real rewrite of the run list and the verdict vocabulary. The remaining hole is the thing the notebook is for: a catch is still not a predicate you can assert without improvising, and under the plan’s own H0 the confirmatory run does not skip the gap.

## 1. Draft 2 findings: real fix or wording?

| Draft 2 | Draft 3 | Real or incomplete |
|---|---|---|
| B1 fill **price**, not timestamps; partial catch; three trades; do not trip on `DEFAULT_VAULT_SETTLEMENT_DELAY` | Structure applied: catch / partial / miss on price, three trades, delay constant not the lag | **Incomplete** — `executed_price` is fee-dirty, tolerance is not a number, “a bar strictly before” is not the decision bar, unclassified fills have no rule (Blocking 1) |
| B2 universe screen as kill-switch; aftermath class; overlapping labels; retired return-clause bound | First-strike table, disjoint ordered classes, gates nothing | **Incomplete** — still classified on **every** candidate-day, so `first_extreme` is not first (Material 3) |
| M3 local “one-event NOT CONFIRMED”; gate-6 spike relabelled | Vocabulary removed; H2a predicts REJECT on gate 6 | **Real**, residual dishonesty in the 10-point prediction (Material 2) |
| M4 breaker cannot beat 21 May | Run removed; fire count promised | **Real**; fire count is not a numbered Part 0 step (Minor) |
| M5 stop-when-answered; drop `gate20_2d`; name the window labels | Run order rewritten; `gate20_2d` dropped; windows on named **runs** | **Mostly real**; Windows A/B **dates** still undefined; stop rule uses a catch predicate that cannot fire as written; “runs 3–5” is a leftover number |
| M6 −12% held-book fire count | Part 0 step 2b | **Real** |
| M7 two Sharpe series; BASELINE parity | Named and not mixed; BASELINE 1e-5 plus splice 1e-9 | **Real**; mixed tolerances (Minor) |
| Minors (churn inequality, H5 wording, lock-up on the long holds, May fill printed) | Applied | **Real**, except Windows A/B dates |

None of the seven Draft 2 findings was only reworded. Two that the log calls closed are still wrong in a way that changes a heading or a stop.

## 2. Is the catch predicate assertable?

No. The three-way split is the right shape. The fields and the match are not.

Every vault sell in this strategy does:

```text
planned_price = planned_mid_price * (1 − backtest_vault_redemption_fee)
executed_reserve = planned_quantity * planned_price
```

`executed_price` is therefore the candle open times (1 − fee). The fee is at least the 10 bp capital line and, on a winner, a 10% performance slice. Exact equality of `executed_price` to any candle open is **false for every redemption**.

Consequences if the text is implemented as written:

- “Catch” (`executed_price` equals the open of a bar strictly before the collapse bar) never holds.
- “Partial catch” (equals the collapse bar’s open) never holds.
- “Miss” (at or after the collapse bar’s close) also does not hold on an open fill: open × 0.999 is still far above a −29.6% close.
- Every fill is **unclassified**. The kill-switch never fires. Run 2’s stop (“if `gate12_2d` catches August on fill price”) never fires, so the 1d gates and the cluster diagnostic run as if August were not caught.

A miss can still be called a catch if someone loosens “the price tolerance of the candle feed” (there is no such number; `data_delay_tolerance` is a time window) **or** matches `executed_price` to **any** earlier bar’s open. On a 62-day winning hold the crash close can equal an open from the way up. That is a miss labelled a catch.

The rank-churn trade has no collapse bar; applying the same catch label to it is undefined.

Part 0 is “research, no backtest”, but `executed_at` / `executed_price` exist only on a trade object. NB41’s ledger does not store them. The assertion has to run against `anchor`’s state (run 1), not against a reconstruction.

## 3. If H0 is true, what is left for `gate12_2d`?

H0 says the incumbent’s 21 Aug and 21 May sells filled at those days’ **opens**. Under the plan’s own labels that is a **partial catch**: the −29.6% and −32.2% close-to-close bars are already skipped; the book took the days before.

Then `gate12_2d` does not skip the gap. It moves the August exit from 21 Aug 00:00 to 19 Aug 00:00 and skips the 19 Aug −14.5% and 20 Aug +2.0% closes. Peak weight on that name is 0.32, so the incremental cycle is about 4–5 points, not the ~10-point day H2a uses (that 10 points is `0.33 × 29.6%`, which is the bar H0 says the incumbent never took).

The previous-research table still says “the book held one more two-day cycle and **took the −29.6% day**.” That sentence is the H0-false world. NB41’s `vault_return_while_held` / `vault_max_dd_while_held` (−47%) are close-to-close marks through `closed_at`; they are not the fill.

What is still worth running, if H0 holds:

- the −12% / −10% held-book fire count (collateral);
- standing gates, with gate 6 **not** pre-committed to a 10-point spike;
- rank-churn P&L and recovered names under `gate12_2d`;
- cycle P&L of 19–21 Aug and 20–21 May on the **2d equity**, anchor vs `gate12_2d`.

“What I expect” is honest that the answer is “the 48-hour gate was two days early and four points too loose.” H2a and the research table are not. A heading that says `gate12_2d` caught the collapse is false under H0.

## 4. Sharpe series, run order, parity, first-strike

**Two series.** `cycle_sharpe` (own clock, plateaus within a cadence) and `cycle_sharpe_on_2d_grid` (`equity.reindex(anchor_cycle_index)`, fail closed, spacing 2, 182.5 periods/year, band vs `anchor`) are named and not mixed. That is enough to implement.

**Run order.** Cheaper-first is now real: Part 0 → `anchor` → `gate12_2d`/`gate10_2d` → `anchor_1d` diagnostic → 1d gates and cluster only if 2d did not catch August. The breaker is gone. No Part E. The stop still keys off a catch predicate that, as written, cannot fire (Blocking 1), so the order is only as good as that predicate.

**Parity.** Two-day `anchor` with `cluster_on = False` vs `BASELINE` is the right target. 1e-5 vs BASELINE and 1e-9 on the splice is a mixed bar; standing method rule 4 does not need two epsilons.

**First-strike table.** Classes are disjoint and ordered: last-day ≤ −20% first, then exactly one ≤ −10% that is the last day, else `neither`. No cluster class. It gates nothing. That part of Draft 2 is in.

It is still classified on **every** candidate-day. `first_extreme` on 22 Aug (last day = 21 Aug −29.6%) contributes a *post-gap* 1-day forward; `first_extreme` on 21 May contributes the second crash day. Averaging them is not “the path the exit is trying to skip.” The name says `first_`; the rule is not first.

**Windows A/B.** Named as runs (`anchor`, `anchor_1d`, `gate12_2d`), not “the best run.” The windows themselves are still unnamed. In this track they have been `A: 2026-01-01 → 2026-07-10` (includes May, **excludes August**) and `B: 2025-08-01 → 2026-09-09`. An implementer copying NB33/37 will silently drop the August event from window A.

**Heading surface that can still mislead**

- “`gate12_2d` skipped −29.6%” under H0.
- Gate-6 REJECT “as a ~10-point spike” when the increment is the −14.5% day.
- First-strike “extreme days have mild forwards” because aftermath rows are in the average.
- Definition of done leads the heading with “whether the 19 Aug fill was the 19 Aug open” and does not require H0 (incumbent 21 Aug / 21 May open) as the first sentence.

## 5. Still not measured

1. **Pre-fee mid vs fee vs close** on the three trades — required for a catch predicate that can fire.
2. **Incremental bars** `gate12_2d` skips relative to the incumbent (19 Aug −14.5% and 20 Aug +2%, not 21 Aug −29.6% if H0 holds), as cycle P&L on the 2d equity, not only worst-five with/without those dates.
3. **Windows A/B dates.**
4. **Breaker fire count** as a numbered Part 0 step (promised in the run table, absent from steps 1–5).
5. A **pre-registered** rank-churn example (calendar-first hold &lt; 4 days), so the third assertion cannot be cherry-picked.

It still does not need a 4h backtest, −7%, strike-one, quantile breakers, Part E, or a cluster family as a candidate.

---

## Blocking

### 1. The catch predicate cannot be asserted, and as written it cannot fire

**Section:** One sentence; H0; Part 0 step 2; run-2 stop rule; Definition of done.

`executed_price` is not the valuation price. It is `planned_mid_price × (1 − fee)`. The plan matches it to candle opens “to the price tolerance of the candle feed,” which is not a constant. Result: catch and partial-catch are never true; miss is not true of an open fill; every trade is unclassified; the kill-switch and the run-2 stop never trigger; 1d gates and cluster run anyway. A wide tolerance, or matching “any earlier open,” can still label a close fill a catch.

**Fix:** Pin the bars and the field, then fail closed.

- Collapse bars: August = **21 Aug** daily candle; May = **21 May** daily candle. Warning bars: 19 Aug and 20 May. The rank-churn trade gets flags, timestamps, and prices only — no catch label. Pre-register that trade as the first rank-exit with hold &lt; 4 days in calendar order.
- Run `anchor` (run 1) **before** the assertion; read the trade objects. Part 0 path/coverage cells can stay before that; the kill-switch cannot.
- On each collapse sell print: `get_vault_features()`, `is_async_vault()`, `has_delayed_vault_redemption()`, `_is_async_vault(pair, is_buy=False)`, settlement override, `decision_ts`, `executed_at`, `planned_mid_price`, `executed_price`, stored fee, decision-bar open/close, collapse-bar open/close, warning-bar open.
- Valuation price = `planned_mid_price`. Match to the **decision bar’s open** with relative tolerance `1e-9` (same candle). Do not match `executed_price` to opens; print it beside the fee.
- If `|mid − decision_open| ≤ 1e-9 × open`: **catch** if `decision_bar < collapse_bar`; **partial catch** if equal; **miss** if after.
- If `mid ≤ collapse_close + 1e-9 × close` **or** `decision_bar > collapse_bar`: **miss**.
- Anything else: **unclassified**, fail closed, do not proceed to a catch label or to confirmatory runs.
- Kill confirmatory status only on **miss**. Partial catch remains a candidate.
- Run 2 “catches August” means `gate12_2d`’s August sell is a **catch** under this predicate (19 Aug open, strictly before 21 Aug), not a partial catch and not “executed_at is 19 Aug.”

Until that is in the plan, H0 is a story about mids and the notebook scores a different number.

---

## Material

### 2. Under H0, `gate12_2d` is two days earlier, not a gap catch; the 10-point spike is the wrong increment

**Section:** Previous-research table (August row); H2a; What I expect; run-2 stop; Definition of done.

H0 and H2a cannot both be the headline. If the incumbent already filled at the 21 Aug open, `gate12_2d` skips −14.5% and +2.0%, not −29.6%. Gate 6 may still spike; it may not. “Took the −29.6% day” in the research table is the H0-false world.

**Fix:** Rewrite the August row as: *the 19 Aug T-1 gate was −14.5% against −16%; the next 2d decision is 21 Aug; whether the −29.6% close was taken is H0, not a settled fact.* Pre-register the increment as the 19–21 Aug **cycle** on the 2d equity, `anchor` vs `gate12_2d`. H2a’s gate-6 prediction is conditional: a ~10-point day only if H0 is **false** (incumbent took the collapse close); if H0 is true, do not cite 10 points and do not treat a gate-6 pass as a surprise that needs a new verdict. Heading order, required: (1) incumbent fill vs 21 Aug / 21 May open (H0); (2) whether `gate12_2d` filled at 19 Aug open; (3) incremental cycle P&L vs the incumbent; (4) standing gates. A heading that says `gate12_2d` caught the collapse, if H0 held, is a fail of the definition of done.

### 3. The first-strike table is still every-day, so it averages the gap with the aftermath

**Section:** Part 0 step 4; Limitations (“the only test that is not circular”).

Draft 2 asked for classification **at the first strike**. Draft 3 kept the class names and applied them to every candidate-day. 22 Aug is `first_extreme` because 21 Aug was −29.6%; its 1-day forward is not the gap.

**Fix:** Primary rows = the first date each vault enters `first_extreme` or `first_single`. Report the every-day table as a robustness appendix or drop it. Limitations should not call this the non-circular test: −10% and −20% were still read off the two events.

### 4. Cycle P&L of the two date windows is still missing

**Section:** H2a (worst-five with/without); Definition of done.

Worst-five with and without 19–21 Aug and 20–21 May tells you whether those windows *are* the worst cycles. It does not tell you what those cycles *paid*, anchor vs `gate12_2d`. Under H0 the 2d clock’s 19–21 Aug cycle is −14.5% then +2%, not −29.6%.

**Fix:** One table: cycle return and USD P&L for 19–21 Aug and 20–21 May, for `anchor` and `gate12_2d`, on the 2d equity. That is the increment. Worst-five with/without stays as the gate-2 diagnostic.

---

## Minor

- **Windows A/B dates.** Write them: A = 2026-01-01 to 2026-07-10 (May in, August out); B = 2025-08-01 to 2026-09-09. Window A cannot confirm an August-only effect.
- **“Runs 3–5.”** There is no run 5. Say runs 3–4 and the unnumbered 1d gates.
- **Parity epsilons.** One bar vs `BASELINE`: 1e-9 on cycle returns, splice-inert at the same tolerance. Drop 1e-5.
- **Breaker fire count.** Add it as Part 0 step 2c (held names, T-1 daily log return ≤ −20%), not only a sentence above the table.
- **A6 on the 1d clock.** “Fee gap over $1,000 blocks SHORTLIST” is not A6. A6 is a ratio, and only when the **equity** gap exceeds $1,000; otherwise N/A. Do not add a local fee-gap gate.
- **Warning bar for May.** Name it 20 May (the first ≤ −20% close). 21 May is the collapse bar, not the warning bar.
- **Unclassified live lock-up vs H0.** 62- and 136-day holds: the 1-day / 4-day lock-up is expired on both collapse sells. Already asserted; keep it next to H0 so the lock-up table is not read as the gap constraint.

---

## Overall verdict

**Worth running with the changes above. Not worth running as written.**

Draft 3 is the right notebook: Part 0, then a four-point tighter gate at 48 hours, then stop. The 19 Aug T-1 gate really is −14.5%, so `gate12_2d` really does sell that morning. HyperCore in this universe is almost certainly an immediate open fill, which is a **partial catch** of both named gaps. That is already the answer to “can we react in a day”: often we do not need to; the backtest already skipped the gap close, and the remaining lever is a looser 14-day gate at the same cadence.

As written, the plan can still (a) score a fee-haircut `executed_price` that matches no open, so catch never fires and the extra 1d/cluster arms run; (b) match a miss to some earlier open and call it a catch; (c) headline `gate12_2d` as skipping −29.6% when H0 already skipped it; (d) average first-strike forwards with aftermath days. Those are heading bugs.

Run this, and stop:

1. Path, gate vs daily −14.5% with timestamps, 4h coverage, −12% fire count, first-entry first-strike table (no kill-switch on that table).
2. `anchor` vs `BASELINE` at 1e-9.
3. Fill assertion on `planned_mid_price` vs the **decision bar’s** open, collapse bars 21 Aug and 21 May, one pre-registered churn sell. H0 is the first heading sentence.
4. `gate12_2d` + `gate10_2d`. Report incremental 19–21 Aug cycle P&L vs the incumbent. Standing gates; gate 6 is whatever it is, not a 10-point script. If this is a catch of August on the predicate in Blocking 1, 1d gates and cluster are not candidates.
5. `anchor_1d` as a cadence diagnostic on the anchor’s 2d timestamps.

Expect REJECT or NOT CONFIRMED. That is still worth the notebook if the heading says whether the incumbent’s 21 Aug fill was the 21 Aug **open**, and what two days of tighter gate then added.
