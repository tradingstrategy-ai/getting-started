# Grok review of plan 44, Draft 1 (grok-4.6, reasoning xhigh, no sandbox, 2026-09-19)

Prompt: Draft 1 of 44-live-parity-plan.md, RESEARCH-RULES.md, the incumbent's parameters, universe creation and decide_trades, the universe builder, NB43's heading, the 29 Aug live log excerpt, and the track-history context. Grok also read the engine and NB43 files itself (40 tool turns).

**Verdict: worth running with changes.** Stage A is the right next experiment. As written it will score the wrong book, on the wrong clock, from the wrong starting holdings, and can still “pass”. Do not build Stage B until that is fixed.

NB43’s own overlap table already contradicts several of the plan’s size-orderings. The review uses that table, `get_indicator_value`, the universe filter, and the 12 Aug cycle flags, not the plan’s narrative.

---

## The seven questions

**1. Jaccard ≥ 0.85 plus two named round trips is a reachable bar, not a parity bar.**

For two 6-name books, 5 of 6 matching is Jaccard \(5/7 \approx 0.714\), which **fails**. Mean 0.85 on 12 decisions needs about six exact 6/6 matches mixed with 5/6. That is “the sixth slot is still wrong on half the days”, and the sixth slot is the whole story (F5, F6).

Worse: live often does not have a 6-name book. Mean live open names is **6.75**; on 22 Aug it is 9, on 25 Aug 8, on 31 Aug 7. NB43 scores open positions after a 3-hour settle. If the backtest’s 6 names are a subset of live’s 8, Jaccard is capped at \(6/8 = 0.75\) even when ranking is perfect. Four of twelve days already look like that.

The two named round trips are the sixth-slot bug by name (research rule 1, used as a gate). A sceptic would pre-register, split by sub-window:

| Test | Why |
|---|---|
| Jaccard of **intended** books (non-zero new weights / L6 names), not open positions | Strips two-leg leftovers |
| Exact 6/6 rate on the **aligned** sub-window (25 Aug–5 Sep), separate from 12–22 Aug | Those weeks are different mechanisms |
| Weight L1 or max per-name error, and top-2 weight | The drawdown is F6, not names |
| Round-trip **count**, not Citadel/AceVault | Keep names as labels |
| Every mismatch named; leftovers may not be swept into D4 | See Blocking 2 |

**2. D3’s offline cut cannot be assumed to reproduce the live rank.**

F3 shows a partial 29 Aug candle **exists**. It does not show `decide_trades` **read** it. Default `get_indicator_value(index=-1)` with `data_delay_tolerance="auto"` floors the 16:33 cycle to 00:00 and looks up the **previous** daily bar (`strategy_input.py`). “Strategy indicators moved to the cycle” only sets `self.timestamp`. Live at 29 Aug 16:33 and a backtest at 29 Aug 00:00 should both read 28 Aug if the lookup hits.

A global cut of `vault-prices.parquet` at `filtered_max_timestamp` is missing at least:

- Live’s file is the **hourly remote parquet**, 9 hours stale on 29 Aug, not the research archive (20–60 marks/day, possibly repaired — D8).
- Staleness is **per vault** (38 stale that morning). A single cut is not that.
- Ranking is 360-day CAGR, 45-day Sortino, 14-day gate, 90-day inverse vol, on the live inclusion set (~185), not last price on 339 names.
- No persisted per-cycle address list (operator action 1).
- Log “signal #k” is alpha-model order **including the close** (L5: 7 = 6 held + AceVault at weight 0), not composite rank.
- `A8` `index=0` in a backtest is the **complete** decision day (lookahead), not a bound on a morning partial.

The D3 cell is worth running as a **probe** (T-1 complete vs T-partial vs live intended six). It is not evidence until a cell prints the timestamp actually read.

**3. `include_closed_vaults=True` is not D1, and D2 is not what live did.**

`filter_vault` still drops sub-vaults, `NON_SELECTABLE_RISKS`, Blacklisted/Dangerous, malicious/broken, unknown protocol, wrong denomination, peak-TVL-as-of-now, age. Live catalogue N moved 330→345→341→343; that is listings and flags, not three closes. `pairs_included` moved 191→178 — a **current-TVL** screen, not peak. Live also skips addresses missing from remote metadata.

F1 says Danny Ocean closed 17 Aug. Live still held it through **22 Aug** (six live-only days). Gucky_4coin closed ~29 Aug and was still held 31 Aug and 5 Sep. F2’s “drops held vaults at the next cycle” is false for the names that motivate D1. `pit_drop_closed` (A4) would sell earlier than live and can **lower** Jaccard.

**4. The $30k/$50k bracket does not break a name test; starting from cash does. The two-segment replay is not sound as specified.**

Pinned $75/$750 at either bankroll is the same dollar gate, so name-set Jaccard may survive the bracket. Weights will not: 27 Aug live discarded **$14.6k** of $55k. F6 is weights. The acceptance test ignores them.

The engine cannot inject the 19–20 Aug deposit, and there is no stock “seed with live book” path. The plan still starts A3 from cash on 12 Aug. Live on 12 Aug: equity $30.2k, **2 trades decided, 4 too-small**, top signal 22Cap (backtest rank **13**). The book is leftover v1–v4, not a fresh top six. A cash-start v6 run will fully buy six names; live did not. Seeding 20 Aug and not 12 Aug is the wrong join. If the bracket disagrees on more than two **name** sets, you still have not tested the path that produced the drawdown.

**5. Stage B’s four arms are the right *ideas*; the design is not coherent until Stage A has a target-book match.**

B1/B2/B3/B4 map to operator 2, 3, 5. Neighbours for gate 6 are fine. Twelve full-window runs on 126 decisions that cannot resolve 0.25 Sharpe is the track’s usual in-band theatre; the plan already predicts that. Evaluating “would this have stopped the live churn?” on 12–18 decisions is descriptive only — §7 is right — and then the stop rule lets Stage B run on a backtest that never matched live.

B3 cannot “raise mean names above 6” with `max_assets_in_portfolio = 6`; it walks to rank 9 to **fill** six slots. Full-window gates must stay on the $100k 2-day track clock, not A3’s $30k live-date clock. Gate 5 is N/A (no new score). Gate 8 is the one B3 can fail. B1+B3 is the interaction that matches the 27 Aug event; B1+B4 is not.

**6. §3 over-claims; the plan does not measure the things NB43 already put on the table.**

Asserted, not evidenced: F3 “the two reads differ on every decision”; D1 “Jaccard ~0.8 on its own”; D5 “small”; D2 “explains some signal-0 sells”; D4 “weights within 2 pp”; F2 dropping held names.

Not measured: intended vs realised book; NB43’s **odd/even phase** (live 12 Aug vs backtest 11 Aug, until the 25 Aug restart); 12 Aug inertia; indicator timestamp actually read; live parquet vs archive at the same instant; per-cycle catalogue diff (L2, not done); weight L1.

Noise: mean Jaccard on open positions; A8 as a D3 bound; A7 with `DEFAULT_VAULT_SETTLEMENT_DELAY = 2 days` (HyperCore native fills at the decision in backtest; live is minutes to hours); optional 12 vs 18 decision switch; “whether Citadel/AceVault are held through” as a Stage B output.

**7. Operator list: 5 is mapped well; 1 and 6 are not; 4’s diagnostic is the wrong delay.**

| Action | Plan | Honest split |
|---|---|---|
| 1 Persist and replay the per-decision universe | D1+D2 | **Cannot.** Logs have N, not addresses. Approximation only; residual = snapshot error. |
| 2 Hysteresis / min-hold | B1, B2 | Backtestable on a parity config. Full-window: expect NO EFFECT (NB40/NB41). |
| 3 Capacity-aware selection | B3 | Backtestable. Live bind is $50k; full window at $100k is a different question. |
| 4 Execution state machine | Out of scope; D7 | Live-only. D7’s 2-day delay is not HyperCore. |
| 5 Live NAV + thresholds from equity | A3 pinned, A6/B4 scaled | Right split: pinned for parity, scaled for the fix. |
| 6 Fixed UTC cut-off; no restart decisions | D3+D5 | Parity should **reproduce** restart dates. The fix is live-executor. A3’s date mask is parity, not the fix. |
| 7 Diagnostics; survivor count | Out of scope | Honest. Needed **before** action 1 is testable. |

A backtest cannot settle: as-of catalogue membership, hourly-parquet vs archive marks, two-leg lock-ups, mid-window deposits, restart hour. The plan is almost honest in §7 and then pretends D1+D3 close those gaps.

---

## Blocking

### 1. The acceptance test can pass with the sixth slot still wrong, and can pass with ranking perfect but leftovers still open

**Section:** §1 acceptance test; §4 outputs (`book_overlap`); §4 stop rule.

NB43 Jaccard 0.64 is open-position Jaccard against a phase-shifted 2-day grid. Live open names: 6–9. Intended survivors on 29 Aug were 6 plus a close. Mean 0.85 on that metric is:

- reachable if D1 fixes Gucky/Danny/HYPErQuantum4 on the **aligned** days (27–31 Aug already 0.71/0.71/0.86) and a few leftover days stay messy — I get ~0.83 from D1 alone on the published overlap, sitting on the line;
- unreachable on days with 8–9 open names even if the six targets match.

The stop rule then **passes Stage A below 0.85** if the D3 cell is blamed, which contradicts §1 (“a backtest that cannot reproduce the live book cannot be used to evaluate a fix”).

**Fix:** Split the window and the metric before any run:

- **Intended-book Jaccard** (L6 non-zero new weights vs the run’s selected six). Gate: mean ≥ 0.85 **and** exact 6/6 on at least 8 of 12, reported separately for 12–22 Aug and 25 Aug–5 Sep.
- **Open-position extra-name count** as a diagnostic (D7), not in the gate.
- Weight L1 / max error / top-2 weight, gated to “where the intended names match, max weight error ≤ 5 pp” (2 pp is tighter than D6’s $7k discard).
- Round-trip **count** within 4 days, not named vaults.
- Drop the D3 backdoor. If intended Jaccard < 0.85, Stage A fails and Stage B is not built. D3 may still explain *why*.

### 2. A3 from cash on 12 Aug is not a live replay

**Section:** §4 window and run table; deposits paragraph; F4; manifest cycles 12 Aug.

12 Aug live: 2 trades decided, 4 `individual_trade_size_too_small`, top signal 22Cap (anchor rank 13), book includes Danny Ocean, Scared Money, 22Cap. That is **inertia plus a different ranker read**, not a missing-universe sixth slot. A cash-start run at $30k with $75 buys **will** open a full book. Live did not.

The 19–20 Aug seed is the wrong join: the path is already diverged. The engine cannot inject deposits; it also cannot (today) seed six vault positions. The bracket A3 vs A5 tests dollar size, not the missing deposit, and not the missing starting book.

**Fix:** Make the primary Stage A test a **one-step replay**, not a closed-loop from cash:

1. For each live decision, take live equity, live holdings (pre-decision), pinned $75/$750/$75, pit-or-better universe.
2. Run `decide_trades` once. Score intended names and weights against L6.
3. Only then, if you can build it, a closed-loop from the **12 Aug pre-decision book** (not from cash). If seeding is not implementable, say so and do not pretend A3 is parity.
4. Keep A3/A5 as capital sensitivity on the one-step weights, not as the acceptance run.

### 3. D5 is first-order; the plan calls it small. NB43’s overlap is off by a day for a week.

**Section:** D5 prediction; §4 A0 vs A3; F10; `book_overlap` → `backtest_decision_at_or_before`.

Research 2-day grid from 1 Jan is **odd** August days (11, 13, 15, …). Live 2-day from 12 Aug is **even** days. NB43 therefore compares live 12 Aug 10:57 (reading, if `index=-1` works as coded, 11 Aug) to backtest 11 Aug 00:00 (reading 10 Aug). That lasts until the 25 Aug restart lands on the backtest grid. Then 3 Sep and 5 Sep slip off again. There is **no 7 Sep decision** in the state (cycle 113 = 5 Sep, 114 = 9 Sep). F10’s “3 Sep → 7 Sep gap” is the 5 Sep → 9 Sep gap, and 9 Sep is after the candle cache.

So D5 is the first week’s comparison clock, not a footnote about one restart. A1 (`D1` on the 2-day grid) **cannot** test the D1 Jaccard prediction, because it still overlaps at_or_before onto the wrong day.

**Fix:** Score every run on the live decision **calendar date** (00:00 that UTC day), not `at_or_before`. Put live dates on A1 as well, or do not quote a D1-alone Jaccard. Strike “small” from D5. Do not treat 7 Sep as a decision. Freeze 12 vs 18 before the run: 18 needs a new load and includes the 9 Sep $18k discard and the 9/11 Sep AceVault trip; they are not the same test.

### 4. F3/D3 is an untested mechanism sitting on the pass path

**Section:** F3; D3; A8; §4 stop rule; L1.

One freshness line plus the existence of a 00:00 candle is not “live ranks on a row the backtest never sees”. If the exact-timestamp hit works, both sides read T-1 complete. The 27/29/31 Aug mismatches on the **aligned** clock are Gucky not in the universe (D1), not a partial-day read.

**Fix:** Before A8 or any D3-based pass:

- Print, for all 12 dates: `filtered_max_timestamp`, stale count (L1), and the **indicator index timestamp** `get_indicator_value` would return (a one-cycle probe, or a log of the series index used).
- Offline ranking must recompute the incumbent indicators on (a) archive marks through previous midnight, (b) archive marks through `filtered_max_timestamp`, (c) if you have it, the hourly parquet as of that cycle. Score against L6 intended six, not “signal #k”.
- If T-1 archive matches live and T-cut does not, D3 is false.
- Drop A8 from the parity table, or label it lookahead. It is not a partial-day bound.

Until L1 is done for all 12, D3 must not be in the stop rule.

---

## Material

### 5. D1 is a static superset, not action 1; D2 can hurt

**Section:** F1, F2, D1, D2, A4; universe builder `filter_vault` / `select_top_vaults`.

`include_closed_vaults=True` on a 9 Sep cache adds whatever is closed **now**, for the whole history, with peak TVL and risk flags as of the call. It does not replay 12 Aug’s 330-name catalogue. Live membership also moves with current TVL, metadata misses, and flags.

Danny Ocean / Gucky held **after** `deposits_open` flipped. A4 (`pit_drop_closed`) is a different rule from live. Do not promote A4 because it “adds explained sells”.

**Fix:** Keep A1 as a sensitivity. Class leftover membership errors as `universe_snapshot` (action 1, not yet loggable). Run L2 **before** locking A4: which addresses left, were they held, did live sell them that cycle? Default parity candidate is A3 **without** drop-closed unless L2 shows live actually dropped held names. Do not change the track anchor because A1 moved Jan–Mar P&L; report it.

### 6. Name match without weight match does not answer the operator

**Section:** F6, F8, D4, D6; 27 Aug cycle (`discarded_liquidity_usd=14603`).

Goon Edging 19.8% → 33% is the drawdown. Capacity discard is $0 on 12–16 Aug and $5.6k–$14.6k later. D4’s “within 2 pp where the book matches” is incompatible with D6 unless discard matches. A3 at $30k **under**-binds the 33% pool cap relative to live at $55k, so it can match names and miss the concentration.

**Fix:** Log `size_risk_discarded_value` on every run (D6 is a measurement, not an arm). Gate weight error only on name-matched decisions. Report top-2 weight vs live. Do not call A3 a parity config if intended names match and Goon Edging is 20% vs 33%.

### 7. Stage B is the right fixes on the wrong gate stack, and too many full-window runs

**Section:** §5.

- Full-window evaluation of B1–B4 belongs on the **track** config ($100k, 2-day from 1 Jan, standing gates 1, 2, 3-vol, 6, 7, **8**; gate 5 N/A). Expect in-band / NO EFFECT. That is a sanity check, not a search.
- Live-replay evaluation is descriptive and only on a Stage A that passed intended-book parity.
- B3 prediction “mean names above 6” is false; rewrite as “fewer discarded dollars, lower top-2, still six names”. Neighbours 0.25/0.75 are fine.
- Pre-register B1+B3, not (only) B1+B4. 27 Aug is sixth-slot **and** $14k discard.
- B2 on the full window repeats NB40. Keep it as a replay-only arm.
- “Whether Citadel/AceVault are held through” violates rule 1. Use round-trip count and top-2 persistence.

If Stage A fails, do not build 45. If Stage A passes, six runs beat twelve: B1 centre + two neighbours, B3 centre + two neighbours, B1+B3. B4 only on the replay.

### 8. D7 uses a two-day ERC-7540 delay for HyperCore native fills

**Section:** D7, A7; `DEFAULT_VAULT_SETTLEMENT_DELAY`; F9.

Backtest HyperCore is `hypercore_native`, fills at the decision. Live withdrawals are minutes, plus repairs. Forcing a two-day delay will move equity by more than live execution and can inflate open-position Jaccard (extra names). If it exceeds 1 pp, the plan promotes execution to Stage B on a false signal.

**Fix:** A7 is optional and must use a delay in **hours**, or be dropped. Extra live names vs intended six are the execution diagnostic you already have (`flag_close_weight_limit`, two-leg notes). Action 4 stays live-only.

### 9. Log checks L2, L3, L4, L6 are still the plan’s evidence, and they have not been run

**Section:** §6; Review log.

L6 **is** the live intended six. L4 is whether 12 Aug’s four suppressed trades were the $750 sell band (the message prints $75). L2 decides A4. L3 decides whether D3/D5 are contaminated.

**Fix:** Do all six greps, paste results into the plan, then freeze the run table. Do not send Draft 2 with L1 still “one day”.

---

## Minor

### 10. 12 vs 18 is a moving target

**Section:** §4 window.

Twelve decisions to 5 Sep (cache). Eighteen adds 9–19 Sep, where discard peaks at $18k and AceVault rounds again. Pick one in the plan, not “if the load works”.

### 11. F7 fill timing is a different question from D7

Net −$365 vs the day’s first mark is mark movement, not two-leg settlement. Do not cite F7 as evidence that execution is P&L-irrelevant for leftovers sitting 3–48 h.

### 12. Build process

Standing method 3: `44-backtest-live-parity.ipynb` from `_build/build_44.py`, no hand-edited cells. Unstated.

### 13. `A0` as “NB43’s baseline”

A0 at $100k / $50/$500 / odd-day 2d will not reproduce NB43’s 0.64 if scoring is fixed to calendar dates. Quote A0 on the **new** scorer, and separately quote NB43’s published 0.64 as the old scorer.

### 14. D8’s 1% NAV cut

Arbitrary. Report the live valuation vs archive mark series (L3) and say whether any decision’s ranking inputs differ by enough to move rank 6 vs 7.

---

## What to run instead (minimum Stage A)

1. Finish L1–L6.
2. One-step `decide_trades` on all 12 dates with live holdings, live equity, pinned thresholds, `include_closed_vaults=True`.
3. D3 probe: indicator timestamp actually read; T-1 vs T-cut vs live intended six.
4. Closed-loop only if (2) matches and seeding is real; otherwise stop.
5. Report open-position extras, discard series, weight error. No Stage B until intended 6/6 rate on the aligned week is high enough that a fix has a book to stand on.

The operator asked why live is not the backtest, and for a backtest that behaves like live. That is a reconstruction problem. The plan already has most of the mechanisms; it then scores a cash-start, odd-day, open-position Jaccard and gives itself a pass if the hardest mechanism (D3) is waved through. Fix the scorer and the starting book, and Stage A is worth a notebook. As written it will produce a heading that says “parity 0.87” while Goon Edging is still 33% live and 20% in the run.
