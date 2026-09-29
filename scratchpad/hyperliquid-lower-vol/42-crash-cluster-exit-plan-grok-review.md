# Grok review of plan 42, Draft 1 (grok-4.6, reasoning xhigh, no sandbox, 2026-09-18)

Prompt: the plan, RESEARCH-RULES.md, the incumbent's parameters and decide_trades, NB40's heading, and a context document covering the track's history (NB03-NB41), the limitations and the operator's questions.


**1. Circularity.** Yes. The cluster shape was read off two collapses and a handful of recoveries. H4’s classes are the same statistic the rule uses (`count >= 2` vs `count == 1`), applied to the same 96-position ledger. That stops a heading from naming `Realist Capital`, it does not stop the family from being reverse-engineered on those events. Passing H4 is close to tautology for the exit branch.

**2. Search size.** Too large. Cadence × gate × strike × window × factor × breaker, then Part E on the in-sample winner, is ~20 confirmatory runs on 126–252 decisions that cannot resolve a 0.25 Sharpe gap. Cut 4h as a candidate, cut −7%, cut consecutive-bucket strikes, cut strike-one from the confirmatory grid, cut the breaker family, cut Part E.

**3. 4h scaling.** Row × 6 keeps calendar span for a *level* (`close / close.shift`). It does not keep CAGR, Sortino, or inverse-variance the same, because those still annualise with `TRADING_DAYS_PER_YEAR = 365` and take the std of *per-row* returns. `sqrt(6)` on the strike is a diffusion scaling for a jump process. Forward-filled weekly marks on a 4h grid fill inverse-variance with zeros and dump capital onto the stalest names.

**4. Settlement.** Reporting backtest decision-to-fill lag does not, by itself, catch a fill at a price live trading could not have got. Hyperliquid leader vaults lock for about a day after deposit; HLP for about four. That lock-up is display-only in backtest. If the pair is treated as async, the engine default delay is **two days**. H3 must mean *filled* before the crash mark, and Part 0 must be a kill-switch, not a footnote.

**5. Breaker quantile.** Not a fair pre-registration. A full-window percentile is a function of the crashes it is meant to catch, then applied in January. It will land in the left tail; whether that is −20% is beside the point.

**6. Gate family.** Right control, wrong clock, and the plan’s own numbers already strain “a tighter gate is a wash”. If the 19 Aug gate really read −14.5%, then −12% at the *existing* two-day cadence is the cheap test. That prediction is falsifiable; the plan should let it be falsified on 2d first.

**7. Missing / noise.** Missing: universe-wide forward screen of cluster vs single-strike; fill-time (not decision-time) collapse P&L; worst-five cycles *excluding* the two collapse windows; Sharpe on a common clock; live lock-up vs engine delay. Noise: Part C’s 8-cell grid, Part E, consecutive-bucket strikes, two breaker quantiles, 4h portfolio metrics from `cycle_returns()` as written.

**8. Is NOT CONFIRMED worth a notebook?** A fitted cluster search that was always going to land in the band is not. A short notebook that answers “does 1d or a tighter gate fill before the gap?” is, even if the answer is no.

---

## Blocking

### 1. The centre rule does not do what the one-sentence claim says

**Section:** The mechanism §2; Families (centre −10%, window 3); H3; What I expect.

On a T-1 read, a cluster of two −10% days fires the *cycle after the second strike is already in the past candle*.

August, using the plan’s own daily path (−8.1%, −2.6%, **−14.5%**, +2.0%, **−29.6%**):

| Decision (T-1 window of 3) | −10% strikes | Centre fires? |
|---|---|---|
| 20 Aug (17–19) | one (−14.5%) | no |
| 21 Aug (18–20) | one (−14.5%) | no |
| 22 Aug (19–21) | two (−14.5%, −29.6%) | yes, after the gap |

May (`−23.9%` then `−32.2%`): count reaches 2 only when day two is already a past candle. H3’s “closes on 21 May” is not what T-1 implements; you take both days unless the fill is intra-day.

The arm that can exit August on 20 Aug is **−7%**, declared post-hoc because the first down day was −8.1%. H3 is written as “at least one Part C member”, so the fitted cell can carry the hypothesis while the centre fails.

`get_indicator_value(..., index=-1)` is the previous bar, not the bar in progress (`strategy_input.py`). Index `0` is explicitly looking into the current day.

**Fix:** Pre-register the centre (−10%, 3, no halving) as the only confirmatory cluster run. Drop −7% from SHORTLIST / H3, or keep it as a named sensitivity that cannot pass. Rewrite H3 to the T-1 implication: August is *not* caught before 21 Aug at −10%; May is not cut on day one. If that is a fail, it is a fail.

### 2. Two collapses, two mechanisms, stitched after the fact

**Section:** What the previous research established; One sentence; H2–H4.

August is a gate-threshold miss: the plan says the 19 Aug 14-day gate was −14.5% against −16%, then the book sat through one more two-day cycle. May is a no-warning daily gap; 4h is the clock that sees a grind. A “cluster of two large down days” is the lowest-common-denominator story that fits both once you have seen them.

If the −14.5% figure is really the *gate* at the 19 Aug decision, then **−12% at the incumbent two-day cadence** already sells before the −29.6% day. Cadence is not required for August. Cluster is not required for August. May still needs a next-day breaker after a huge day, or a faster clock plus a fill that actually happens.

**Fix:** Split the question in Part 0, before any new indicator.

1. Reproduce the 19 Aug gate value at T-1. If it is ≤ −12%, run `gate_threshold = -0.12` at **2d** as the first comparator (not only at 1d).
2. Treat May as a separate class: “first daily return ≤ some pre-stated extreme, exit next cycle”. Do not force it into a two-strike cluster.

Do not run cluster until those two cheaper tests are scored.

### 3. Settlement can make “react in a day” impossible; lag tables do not fix that

**Section:** Mechanism (cadence); Limitations (redemption lag); Part 0 1c; H3.

Live HyperCore leader vaults lock ~1 day after *deposit*; protocol/HLP ~4 days (`hypercore-vault.md`). That estimate is stored for display (`maybe_set_vault_lockup_expiry`); backtest execution does not enforce it. There is no Hyperliquid *withdrawal epoch* in the sense the plan uses; that is ERC-7540 language. Once lock-up has expired, live `vaultTransfer` is a multi-phase walk that takes minutes to hours, not a two-day epoch.

Engine defaults, if the pair is classified async (empty `vault_features` plus a non-generic `hypercore` slug is enough for `is_async_vault()` to return true): `DEFAULT_VAULT_SETTLEMENT_DELAY = 2 days`. A 20 Aug *decision* then fills on 22 Aug and still takes the 21 Aug gap. A 4h decision with a two-day fill is twelve cycles of theatre.

The two named collapses were long holds, so live lock-up is probably expired. Rank-churn names with a median hold of four days are a different matter. None of that is what a lag *table* decides. If H3 says “closes on or before 20 Aug” and “closes” means the position object, a run can “exit” on 20 Aug, fill on 22 Aug, and still be called a catch.

**Fix:** Part 0 1c is a **kill-switch**, not documentation. Before Part A:

- State, from code and one asserted position: async or not; delay in days; whether lock-up blocks the sell.
- Define H3 on **fill timestamp**, not decision timestamp (the limitations section already says P&L is at fill; the hypothesis does not).
- If fill lag ≥ the gap you are trying to skip, Parts C–E are DIAGNOSTIC and are not run as candidates.
- Compare that delay to live lock-up (1d / 4d) and to sequential HyperCore phases. A 4h backtest fill is not a live 4h fill.

### 4. The 4h arm changes the ranking and the sizer, and the metric stack is wrong

**Section:** Mechanism §1; Families (4h, Part C4); H1; Limitations (4h on sparse data).

`cagr_score` does `ratio.pow(365 / lookback) - 1`. Scaling 360 days to 2160 4h rows keeps the price ratio and **breaks annualisation** (a 40% year becomes ~6%). `sortino_score` / `sharpe_score` take the mean/std of per-row returns and still multiply by `sqrt(365)`, so 4h Sortino is ~`1/sqrt(6)` of daily. Relative ranks move, especially near the cap of 3.

`inverse_vol` is `pct_change().rolling(lb).std()` with no annualisation (`cell10_orig.py`). On 4h rows, std falls ~`sqrt(6)` if marks are dense. On forward-filled weekly marks it falls toward zero. `VOL_FLOOR = 1e-4` is a daily floor; 4h zeros hit it. Inverse-variance then overweights the stalest names. That is the NB40 unlimited-book failure, turned up. Midnight agreement of `return_gate` does not catch this.

`sqrt(6)` on the strike asks a different question: two −4.1% buckets in 18 rows is not two −10% days in 3 days. Consecutive-down-bucket strikes of 3+ are a pmalt-shaped hair trigger on any 12-hour drift.

`cycle_returns()` in `harness.py` uses `(b - a).days`. A 4h spacing has `.days == 0`, so `periods_per_year` becomes `365 / 1e-9`. Cycle Sharpe and vol on the 4h arm are unusable unless that is changed. H1’s 0.25 Sharpe band was calibrated on the **two-day** clock (126 decisions). Comparing 4h or even 1d cycle Sharpe to the 2d anchor mixes clocks. RESEARCH-RULES still say metrics are on the two-day clock.

**Fix:** Do not backtest 4h. Answer the operator in Part 0 with mark coverage and a path diagnostic on the two collapse windows only. If 4h stays: scale annualisation (`365 * 6` periods), resample vol to a calendar clock rather than row-std of zeros, drop `sqrt(6)` strikes, drop consecutive-bucket strikes from confirmatory, fix `cycle_returns` to `total_seconds()`, and score 4h only against `anchor_4h` on the post-break window as DIAGNOSTIC. Gate 3 must not compare 4h row-vol to the daily anchor.

### 5. Gate 6 cannot be scored on Part C, so H3 cannot SHORTLIST

**Section:** Families (plateau neighbours); H3; Verdict vocabulary.

Gate 6 needs both pre-registered neighbours (`plateau_gate` fails closed if a neighbour is missing; `standing_gates` treats an unrun gate as UNEVALUATED, never a pass). Strike {−7%, −10%}, window {3, 5}, factor {1.0, 0.5} are all two-point axes. Every cell is an endpoint. The stated centre has one strike neighbour and one window neighbour. H3 requires gate 6. SHORTLIST requires every standing gate. Part C is UNEVALUATED by construction.

**Fix:** Either add a third pre-stated point on any axis you will plateau (and accept more search), or run **one** cluster specification, mark gate 6 UNEVALUATED, and cap the verdict at DIAGNOSTIC / NOT CONFIRMED. Do not write H3 as if Part C can SHORTLIST.

---

## Material

### 6. H4 is a renaming of the fit, not a protection

**Section:** H4; What is deliberately NOT tested; Limitations (five events).

Event classes: “a day at or below the strike with no second such day in the window” vs “a second such day in the window”. The rule: sell if count ≥ 2. Applied to the anchor’s 96 positions, the same window the rule was read from.

By construction, cluster-class events reach count 2 and single-strike events do not. The exit branch will not close a true single-strike before recovery except via path dependence, the **admission** branch (`count ≥ 1` for names not held), or rank churn. The plan also says it will not use names, then fits −7% to −8.1%, window 3 to “second day within 1–2 days”, and consecutive buckets to pmalt.

**Fix:** In Part 0, on **all candidate-days** (not the held ledger): at T, classify cluster vs single-strike vs neither; report 1-, 2- and 5-day forward log return of the vault, with a date-block interval. That is the gate-5 analogue for an exit. H4 then uses those universe-level classes, frozen before Part C. If the forward contrast is inside noise, do not backtest cluster. Keep the named collapses as illustrations only.

### 7. The search is too large; Part E re-opens it after seeing Sharpe

**Section:** Families; Part C, C4, D, E; H5–H6.

Eight Part C cells, up to four 4h translations, two breakers, then “best Part C by cycle Sharpe” combined with breakers and the best gate. 126 two-day decisions (252 at 1d) still have a minimum detectable Sharpe difference near 2.5 (roughly 1.8 if you naively give 1d credit for more samples). Every interesting gap in this track is 0.13–0.21. Eight cells will produce a winner. Part E is declared exploratory and will still be the number in the heading.

Strike-one is a different mechanism (re-weight, not exit). On a daily T-1 clock it is the one component that can cut May’s second day in half (count = 1 on the morning after −23.9%). Burying it in a 2×2×2 grid wastes that. The breaker is a next-day stop on an extreme day, which is the honest May rule, and should not be a two-quantile add-on.

**Fix:** Confirmatory runs, in order, and stop when a cheaper one answers:

| Run | Why |
|---|---|
| `anchor` | parity |
| `anchor_1d` | H1 only |
| `gate -12%` at **2d** | August cheap control |
| `gate -12%` and `−10%` at 1d | H2, plateau with −16% |
| optionally one next-day breaker at a **round number** (e.g. −20%), off vs on | May |
| optionally one cluster (−10%, 3, no halving, 1d) | only if the universe-wide screen in finding 6 is positive |

Drop −7%, window 5, factor 0.5 as a grid, both breaker quantiles, Part C4, Part E. Report strike-one once as a diagnostic if at all.

### 8. Full-window breaker quantiles are look-ahead

**Section:** Mechanism §4; Families (0.5th / 0.2nd percentile); H6; Part 0 step 3.

Computing the 0.2nd percentile on every candidate-day of the track window, then using it from 1 Jan, uses August to set January’s switch. Two collapse days do not uniquely pin a percentile among thousands of candidate-days, but they sit in the tail that defines it. “Not chosen by eye” is worse than picking −20% in public, because it looks objective.

H6 (“fires fewer than 10 times”) is also close to “fires on the events we already know”.

**Fix:** Freeze a round threshold before Part 0 looks at the histogram, or an expanding quantile using only data before T. Print the in-sample percentile as a diagnostic, not as the rule.

### 9. H2 is the right control and is not run at the incumbent cadence

**Section:** Families (gate threshold at 1d); H2; What I expect.

A tighter 14-day gate is the correct “do we need a new indicator?” test. Running it only at 1d confounds threshold with cadence. The prediction “tighter gate is a wash” *can* be wrong: if 19 Aug’s gate is −14.5%, −12% and −10% exit that cycle and −16% / −20% do not. That is a clean, pre-stated contrast. Collateral damage on recoveries is exactly what Part B should measure (rank-churn P&L, the eight single-day shocks).

**Fix:** Put −12% (and if you want a plateau, −10%) on the **2d** anchor first. Then 1d. If 2d −12% already cuts August’s worst cycle by a third and passes 1, 3, 7, cluster is moot. If it also fails gate 6 as a spike, record that; do not rescue it with a new indicator.

### 10. The plan says it does not touch admission, then adds an admission filter

**Section:** What the previous research established (last row); Mechanism §2; NB40 finding that crash-filter exits never fired.

“A vault not held is not admitted while its count is at least 1” is an entry rule. NB40’s crash filter never took an exit; it only blocked entry. This branch can do the same: a single −10% day keeps a name out of the pool for the whole window, which changes rank-churn, fees, and re-entry, and is how H4 can fail without the exit ever firing on a recovery.

**Fix:** Confirmatory cluster = exit on held names with count ≥ 2 only. Put the “do not buy a first strike” branch in a labelled diagnostic, or drop it.

### 11. A successful August save can fail gate 2, and worst-five is the named event

**Section:** H3 (worst five cycles −⅓); Standing gate 2; NB40 / NB41 (one position is 46% of net P&L).

Avoiding 0.33 × −29.6% is a ~10 point portfolio day. That alone can hit “worst five down by a third” (anchor worst-five −11.0% in NB40). Masked Sharpe does not get the save; unmasked does; retention falls. The track already sits on 0.825 retention. A rule that “works” can REJECT on gate 2.

**Fix:** Report worst-five **with and without** the two collapse windows. Pre-register that a catch of the largest contributor may fail gate 2, and that this is a reject, not a footnote. Do not let H3 pass on a worst-five move that disappears when those windows are dropped.

### 12. Gate 5 is standing and is silently dropped

**Section:** Plan header (standing gates 1, 2, 3, 6, 7); RESEARCH-RULES after the idiot-gate audit.

The stability clause of gate 5 still stands. An exit rule is not a selection score, so an exemption is reasonable, but it is not written. The right substitute is finding 6’s universe-wide forward screen, not a free pass to the backtest.

**Fix:** One sentence: gate 5 does not apply to a position-level exit; the Part 0 forward contrast replaces it; if that contrast is not positive, no cluster backtest.

### 13. `strike_threshold = 0` / breaker `0` is not an off state unless special-cased

**Section:** Mechanism §2–4.

“Off at `strike_threshold = 0`” implemented as `log_return <= 0` counts every non-up day; two down days in three is the normal book. Same for the breaker. The parity assertion would then fail, or worse, pass on a different bug.

**Fix:** Explicit disabled flags (`cluster_exit = false`, `breaker = false`). Do not use 0 as a magic threshold.

### 14. 1d vs 2d Sharpe, churn, and fees

**Section:** H1; Limitations (fees and churn); RESEARCH-RULES (cycle clock); A6.

H1’s 0.25 band between `anchor` and `anchor_1d` is not the operator indifference band, which compares two books on the **same** clock. Rank churn is 89% of trades and nets about zero; doubling the clock will not cap turnover at 1.6× just because that was written down. A6’s fee bug bites harder when redemptions multiply.

**Fix:** Judge 1d candidates against `anchor_1d` only. For H1, also report 1d equity sampled onto the two-day grid so Sharpe is comparable. Pre-register a rank-churn P&L floor (e.g. churn net ≥ −$1k, or no worse than the 2d churn). A6 remains diagnostic; if the fee gap exceeds $1,000, say so and do not SHORTLIST.

---

## Minor

- **Part 0 must not conflate the 19 Aug *daily* return with the 14-day *gate*.** Both are written as −14.5%. At a 00:00 cycle, T-1 is the previous UTC day. Print both numbers, with timestamps.
- **`minimum_hold_days = 1` on 4h is four hours.** If 4h exists at all, scale hold protection to calendar time or rank-churn becomes the experiment.
- **H1 turnover 3× for 4h** is not a prediction derived from 12× as many decisions; treat a fail as expected, not as a near-miss.
- **“Epoch for withdrawals”** should be struck. HyperCore has deposit lock-up and a multi-phase transfer, not an ERC-7540 epoch.
- **Parity for 4h** cannot use the 2d BASELINE; it is a new baseline, as the plan says for 1d. Say that for 4h too.
- **Windows A/B and gate 7 on 4h** scored on post-break only are a different test than the rest of the track; they cannot SHORTLIST a 4h book against the full-window 2d anchor.

---

## Overall verdict

**Not worth running as written.** Worth running with the cuts in findings 2, 4, 7 and 9.

The operator asked a real question. The incumbent’s worst losses are long holds that the 14-day gate saw late, and a same-day −10% stop is net harmful on this ledger. That is enough to justify Part 0 plus a handful of runs.

It is not enough to justify a new three-component indicator, a post-hoc −7% cell, a 4h translation, two in-sample breaker quantiles, and a Sharpe-guided Part E, all on one window whose MDS is still ~2.5. This track has already produced NOT CONFIRMED leads that are the anchor with one or two slots moved (`measured_8`, +0.21). A cluster rule that was read off five events will, at best, land in the same band by skipping one named day. That is not a prospective specification.

Run this instead, and stop:

1. Part 0: reproduce the path; split August vs May; universe-wide cluster vs single-strike forward returns; engine fill lag as a kill-switch; live lock-up vs backtest.
2. `anchor_1d` (daily candles, 1d cycle). If H1 fails, stop.
3. Gate −12% at 2d, then −12%/−10% at 1d.
4. Only if 3 does not already catch August, and only if the universe-wide screen is positive: one cluster (−10%, window 3, held names only).
5. Optional diagnostic: one round-number next-day breaker for May.

Expect NOT CONFIRMED or REJECT. That is still worth the notebook if it shows whether a fill happens before the gap. The cluster family as drafted will not tell you that; it will tell you which of eight fitted cells printed the nicest Sharpe.
