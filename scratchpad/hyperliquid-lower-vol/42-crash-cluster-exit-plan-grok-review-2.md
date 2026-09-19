# Grok review of plan 42, Draft 2 (grok-4.6, reasoning xhigh, no sandbox, 2026-09-19)

Prompt: Draft 2, the Draft 1 review, RESEARCH-RULES.md, the incumbent's parameters and decide_trades, the engine's settlement and pricing excerpts, harness.py's cycle clock, and the track-history context document.

Draft 2 is a real rewrite, not a polish pass. The Draft 1 cuts that mattered (drop 4h, drop −7%, split August/May, one cluster spec, fill as a kill-switch, no Part E) are in the document. The remaining holes can still produce the wrong heading, because the notebook’s one-sentence question is about the **fill price of the gap**, and the plan still scores that with timestamps and a lag-versus-calendar-gap rule.

## 1. Draft 1 findings: real fix or wording?

None of the fourteen Draft 1 findings were only reworded. Incomplete real fixes are called out below.

| Draft 1 | Draft 2 | Real or incomplete |
|---|---|---|
| B1 −10%×2-in-3 cannot fire before the gap; −7% post-hoc | One cluster spec, last, T-1 implication in H5, verdict capped | **Real** |
| B2 two collapses, two mechanisms | August = `gate12_2d` first; May = breaker | **Real** |
| B3 settlement / fill | Kill-switch exists; H2a/H3 on fill timestamps | **Incomplete** — timestamps, not price (Blocking 1) |
| B4 4h arm | Not backtested; Part 0 coverage only | **Real** |
| B5 two-point axes, gate 6 UNEVALUATED | Three gate points per cadence; cluster gate 6 declared UNEVALUATED | **Real** |
| M6 H4 circular | Universe-wide forward contrast | **Incomplete / newly wrong** (Blocking 2) |
| M7 search + Part E | ≤8 runs, no Part E | **Real**, residual bloat in 3a/3b |
| M8 quantile breaker | Round −20%, frozen here | **Real** |
| M9 gate control at 2d | `gate12_2d` first | **Real** |
| M10 admission branch | Held names only | **Real** |
| M11 gate 2 / worst-five | With and without collapse windows; gate 2 failure is REJECT | **Real** |
| M12 gate 5 dropped | Exemption written; substitute is the contrast | **Incomplete** (same as M6) |
| M13 `0` as off | Explicit flags | **Real** |
| M14 clocks, churn, A6 | 2d-grid sampling, churn floor, A6 block | **Real**, grid underspecified (Minor) |
| Minors (gate vs daily −14.5%, “epoch”, 4h hold) | Applied | **Real** |

## 2. The −12% / 19 Aug claim (checked)

NB41’s engine timeline (`manifest_41.json`) on the two-day clock:

| Decision | `return_14d` at T-1 | In pool? |
|---|---|---|
| 15 Aug | +0.02% | yes |
| 17 Aug | −2.15% | yes |
| 19 Aug | **−14.5011%** | yes |
| 21 Aug | not in pool (exit: 14-day return **−27.9%** ≤ −16%) | no |

`return_gate` is `close / close.shift(14) - 1`. `get_indicator_value(index=-1)` at 19 Aug 00:00 reads the 18 Aug bar. So −14.5011% is the 14-day simple return **through 18 Aug**, not the 19 Aug daily return. The coincidence of values is real; Draft 2 is right to print both with timestamps.

`gate_value <= gate_threshold` drops the name. −0.145011 ≤ −0.12 is true; ≤ −0.16 is false. **`gate12_2d` does sell at the 19 Aug decision.** −10% would too. 17 Aug (−2.15%) would not. That part of “What I expect” is true **for the decision**.

It is not yet a statement about the fill. That is Blocking 1.

---

## Blocking

### 1. The fill kill-switch still scores timestamps, so a decision-time exit can still be called a catch

**Section:** Part 0 step 2; H2a; H3; What I expect; The runs (stop rule on #0).

Draft 2 did what Draft 1 asked: Part 0 step 2 is a kill-switch, H2a/H3 are on `executed_at`. That is not enough to assert the operator’s question.

Vault daily candles are timestamped at the **open** of the UTC day. Resampling is `open=first`, `close=last` of the day’s marks (`resample_candles`). `BacktestSimplePricingModel` defaults to `candle_timepoint_kind="open"`. HyperCore metadata sets `features={hypercore_native}`, which is **not** in `ASYNC_VAULT_FEATURES`, so `is_async_vault()` / `has_delayed_vault_redemption()` are false and the engine’s two-day `DEFAULT_VAULT_SETTLEMENT_DELAY` is unused. The expected path is: **immediate fill at the decision, at that day’s OPEN**.

On that path, 19 Aug 00:00 fill price ≈ first mark of 19 Aug ≈ last mark of 18 Aug. The −14.5% day and the −29.6% day are both skipped. `executed_at == decision_ts` and it is a real catch.

The same timestamps also cover the miss:

- Fill at 19 Aug **close** (last mark of 19 Aug): `executed_at` is still 19 Aug 00:00, but the −14.5% day is taken.
- Async 2-day settlement at 21 Aug **open**: lag = 2 days = the plan’s August “gap”, so the kill-switch fires (“cannot avoid the collapse”). The fill price is 21 Aug open ≈ 20 Aug close, which **still skips the −29.6% bar**.
- Settlement at 21 Aug **close**: lag still 2 days; this one really takes the gap.

Lag ≥ gap, and “fill timestamp before the collapse day”, cannot tell these apart. H2a as written will call any 19 Aug `executed_at` a catch, including a close fill, and will declare a 21 Aug-open fill a miss even though it skipped the gap.

HyperCore’s expected path is the first one, so a careful implementer who prints `executed_at` on the Realist sell will see lag 0 and proceed. An implementer who reads `DEFAULT_VAULT_SETTLEMENT_DELAY = 2 days` and trips the kill-switch will abort the only run that answers the operator. Both are compatible with the current text.

**Fix:** Define a catch on **price**, then assert it on named trades.

On the Realist 21 Aug sell and the pmalt 21 May sell, print and assert:

1. `vault_features`, `is_async_vault()`, `has_delayed_vault_redemption()`, and `_is_async_vault(..., is_buy=False)` — the actual pair in this universe, not a generic HyperCore answer.
2. `decision_ts`, `executed_at`, `executed_price`.
3. The collapse bar’s open and close, and the warning bar’s open (19 Aug for August; 21 May for May).

A catch of the gap = `executed_price` matches the **open of a bar strictly before the collapse bar** (August collapse bar = 21 Aug; May collapse bar = 21 May). Report as a separate line whether the 19 Aug close-to-close return was taken.

Kill candidates only if `executed_price` is at or after the collapse bar’s **close**. A fill at the collapse bar’s open is a **partial catch** (skipped the gap, took earlier days) and remains a candidate, labelled as such.

Do not use `DEFAULT_VAULT_SETTLEMENT_DELAY` as the lag. Do not trip the kill-switch on lag ≥ 2 days. One asserted position is not enough: assert the two long holds (lock-up expired: 62 and 136 days) **and** one median-4-day churn name (where a live 1-day lock-up can bind). Lock-up stays display-only in backtest; H3’s 1-day / 4-day live count stays a diagnostic.

Until that assertion exists, H2a’s “FILLS … before the collapse day” is still a decision-time exit with extra words.

### 2. The universe-wide contrast is the wrong quantity, scored with an idiot-gate, and used as a kill-switch

**Section:** Plan header (gate 5 substitute); Part 0 step 4; runs 4–5 stop rules; Limitations.

Draft 1 asked for a universe-wide forward screen so H4 was not a renaming of the fit. Draft 2 built one, then used it as a significance test that kills runs 4 and 5.

Three problems, each enough to make a “positive contrast” uninterpretable.

**The cluster class’s forward return is the aftermath, not the crash.** Classification is at T, reading T-1. Cluster becomes true when the second −10% day is already in the past candle. For August that is the 22 Aug decision (window 19–21 contains −14.5% and −29.6%). The 1- and 2-day forwards from there start **after** the gap. The screen then asks whether post-crash drift is worse than “neither”, which is not the exit question.

The August gap actually sits in the **single-strike** 2-day forward: at 20 Aug (1d), T-1 window 17–19 is one −10% day (−14.5%) and not extreme, and the 2-day forward includes 21 Aug −29.6%. So a working screen would credit single-strike, the branch they dropped, and would not credit cluster.

**Classes overlap and the priority is unstated.** Cluster = “≥2 days ≤ −10% in 3”; extreme = “last day ≤ −20%”; single-strike = “exactly one ≤ −10% and not extreme”. A window with a −20% day and another −10% day is both cluster and extreme. May’s 21 May T-1 is extreme (20 May −23.9%) and possibly single-strike. Say the order, or make the classes disjoint: last-day extreme first, then cluster, then single-strike.

**“Upper edge of the interval below neither” is the demoted gate-5 return clause.** A 30-day date-block bootstrap on 1- to 5-day returns, on 126 × ~150 overlapping candidate-days, will not resolve a small contrast. The idiot-gate audit dropped exactly this demand. Using it as a kill-switch either (a) never clears, so 4–5 are skipped for lack of power, or (b) clears only because the two named crashes dominate, which is the circularity the screen was meant to prevent. Conservative skip of cluster is harmless; treating a “pass” as evidence the shape carries information is not.

The breaker should not sit behind this screen at all (see Material 4).

**Fix:** Part 0 step 4 is a **table**, not a kill-switch. Classify at the **first** strike, then measure 1- and 2-day forward log return (that is the path the exit is trying to skip):

- `first_extreme`: T-1 last day ≤ −20%.
- `first_single`: exactly one day ≤ −10% in the trailing 3, and that day is the last day, and not extreme.
- `neither`.

Do not classify “cluster” for the screen; two strikes means the second day is already in T-1. Report point estimates and the 30-day date-block interval as diagnostics. Freeze the classes before any backtest. Do not require the interval’s upper edge to sit below “neither”. Run 5 stays one pre-stated diagnostic, only if runs 2–3 did not already cut August, and stays capped at DIAGNOSTIC. Run 4 is not gated on this table.

---

## Material

### 3. “One-event NOT CONFIRMED” is a new unpublished gate, and the likely result of a working `gate12_2d` is REJECT on gate 6

**Section:** Verdict vocabulary; H2a; What I expect; Limitations.

NOT CONFIRMED in RESEARCH-RULES already means: every standing gate passed, Sharpe gap inside 0.25, carrying it is the operator’s call on priors. Draft 2 adds a local verdict that (i) requires the only measurable gain to sit inside the two collapse windows and (ii) **must not be carried** without a prospective window.

That is a third bar, not in the rules. If `gate12_2d` passes 1, 2, 3, 6, 7 and beats the band, the rules say SHORTLIST. The plan says do not carry it. If it fails gate 2 or 6, the rules say REJECT. The plan’s “candidate for a one-event NOT CONFIRMED” never applies.

A working August save is structurally a **cliff** on the gate axis. −16% does not sell on 19 Aug; −12% and −10% both do. Gate 6 requires the centre within 0.25 of **each** neighbour. Skipping ~0.33 × 29.6% is a ~10-point portfolio day; the track’s interesting Sharpe gaps are 0.13–0.21. H2a predicts a pass on 1, 3, 7 and a possible REJECT on gate 2. It does not predict the plateau failure that the same one-event save almost certainly produces. NB37 already saw this shape (threshold 1.5 vs 1.25).

If the heading then softens REJECT-on-6 into “one-event NOT CONFIRMED”, that is a verdict cheat.

**Fix:** Delete the new verdict. Pre-register: if `gate12_2d` catches August on fill price, expect REJECT on gate 6 as a spike versus −16%, and possibly REJECT on gate 2; both are REJECT. Worst-five with and without the collapse windows stays a diagnostic of *why*. NOT CONFIRMED is used only if every standing gate actually passed and the 2d-clock Sharpe gap is inside 0.25. “Do not carry a one-event rule” is an operator prior, stated as one, not a vocabulary patch.

### 4. The breaker cannot beat the incumbent on a T-1 daily clock; H4 does not say so

**Section:** Runs #4; H4; What the previous research established (May row).

H5 correctly pre-registers that cluster at −10% × 2-in-3 does not fire before the 21 Aug gap. H4 does not do the same job for the breaker.

Breaker: held name, T-1 daily log return ≤ −20%, remove from pool.

- **May.** First 1d decision that sees 20 May −23.9% is **21 May 00:00**. The incumbent already sells pmalt on 21 May (`exit_return_14d` −20.3% ≤ −16%). Same decision. The breaker does not get an extra day.
- **August.** The first daily return ≤ −20% is 21 Aug −29.6% itself. The breaker fires 22 Aug, after the gap. Same T-1 failure as cluster.

Whether May’s second day is skipped is **only** the 21 May fill price (Blocking 1). A new indicator is not required for that. Conditioning the breaker on a positive “extreme” contrast then running it as H4 is a second fitted cell.

**Fix:** Do not run `breaker20_1d` as a candidate. Optional diagnostic: print the fire count and the 21 May fill price versus the incumbent gate exit. Pre-register the T-1 implication in H4 the way H5 already does for cluster. If Part 0 shows the incumbent’s 21 May fill already skipped −32.2%, May is answered before any new run.

### 5. Stop-when-answered is written, then not used; 1d gates are extra search after 2d has answered August

**Section:** The runs, in order; stop rule column; Definition of done; H1; H2b.

The table says “stop when a cheaper one answers”. Run 2’s stop rule is “—”. Definition of done still requires 1–3b executed. After `gate12_2d` has sold on 19 Aug and the fill is a catch, the operator’s question is answered: **you did not need a faster clock; you needed a 4-point tighter gate at 48 hours.** Runs 3a (`gate12_1d`, `gate10_1d`) then search a second deployment. Run 5 already stops in that case; 3a does not.

H1 failing on churn (floor = anchor rank-churn − $1,000, i.e. about −$1.9k) would skip 3a, which is the right abort if 1d is unusable. If H1 **passes** and run 2 already caught August, 3a is still extra.

`gate20_2d` is −16%’s other neighbour, not −12%’s. Gate 6 for `gate12_2d` needs `anchor` (−16%) and `gate10_2d` (−10%). `gate20_2d` is not required.

There is **no cheaper candidate backtest** than `gate12_2d`. Part 0 can already prove the 19 Aug **decision** fires, from the reconstructed gate. The backtest is for collateral, standing gates, and the fill. That is the right first run.

**Fix:** Confirmatory, in order, and actually stop:

| Run | Stop |
|---|---|
| Part 0, including fill-**price** assertion and the −12% fire count | If fill price took the collapse close, remaining runs are DIAGNOSTIC |
| `anchor` (parity vs BASELINE) | — |
| `gate12_2d` | If it catches August on fill price, 3a/4/5 are not candidates |
| `gate10_2d` (plateau neighbour) | — |
| `anchor_1d` | H1 diagnostic; 1d gates only if H1 passes **and** 2d did not already catch August |
| `cluster_1d` | Only as DIAGNOSTIC, only if 2d did not catch August; gate 6 UNEVALUATED |

Drop `gate20_2d` and `breaker20_1d` as candidates. Windows A/B for `anchor`, `anchor_1d`, and `gate12_2d` — not “the best run”.

### 6. Part 0 still does not count how many times −12% actually fires

**Section:** Part 0 step 1; H2a (“one-event rescue”); What I expect.

The 19 Aug gate is one held name on one 2d decision. A tighter gate also sells every other held name whose T-1 14-day return sits in (−16%, −12%]. Without that count, “one-event” is a hope. The same-day −10% stop already showed 8 of 10 fires were winners; a 14-day −12% gate is a different statistic, but it is the same collateral question.

**Fix:** Before any backtest, on every 2d decision, for every then-held vault, count T-1 `return_gate` in (−16%, −12%] and in (−16%, −10%]. Print the dates and whether the vault recovered over the next 5 and 30 days. If the only held fire is 19 Aug, `gate12_2d` is a one-date intervention and the backtest is only standing gates plus fill. If there are many fires, H2a’s “one-event” prediction is already false.

### 7. 1d Sharpe on a “two-day grid” is right in spirit and still underspecified

**Section:** The runs (metrics paragraph); H1; RESEARCH-RULES (cycle clock).

Sampling 1d equity onto the 2d clock is the correct way to apply the 0.25 band. “Every second day” is not a grid. If the 1d series is subsampled on odd dates, you are not on the anchor’s clock. `cycle_returns()` uses median `.days`; a correct reindex onto the anchor’s decision timestamps gives spacing 2 and `periods_per_year = 182.5`.

Gate 6 for the 1d family must use **1d-clock** Sharpe among 1d runs. The indifference band versus the 2d anchor must use the **2d-grid** Sharpe. Those are different numbers. The plan currently has one “cycle Sharpe”.

**Fix:** Name two series: `cycle_sharpe` (own decision clock) and `cycle_sharpe_on_2d_grid` (`equity.reindex(anchor_cycle_index)`, fail closed on missing timestamps). H1 and the band versus `anchor` use the grid series. Plateau among `{anchor_1d, gate12_1d, gate10_1d}` uses own-clock. Do not mix.

Also assert 2d `anchor` with breaker/cluster flags off against BASELINE to 1e-9 (standing method rule 4). Splice-inert on `anchor_1d` is necessary and not sufficient.

---

## Minor

- **Parity target.** Standing method rule 4 is BASELINE, not only `anchor_1d`.
- **`gate20_2d`.** Not a neighbour of −12%. Drop it, or label it as the incumbent’s other neighbour and do not feed it to `plateau_gate("gate12_2d", ...)`.
- **Windows A/B on “the best run”.** That is Part E in one phrase. Pre-name the labels.
- **H1 churn floor.** “Anchor minus $1,000” is about −$1.9k, not −$1k. Write the inequality: `churn_pnl >= anchor_churn_pnl - 1000`.
- **Cluster H5 wording.** “Does not fire before 21 Aug” is true (first fire 22 Aug on 1d). Say “fires 22 Aug, after the gap”.
- **Live lock-up on the two collapses.** 62- and 136-day holds: 1-day leader / 4-day HLP lock-up is expired. Assert that so H3’s lock-up table is not mistaken for the crash constraint.
- **May incumbent fill.** Part 0 should print whether the existing 21 May gate fill skipped −32.2%, before anyone proposes a breaker.

---

## What the plan still does not measure (and should)

1. **Fill price** versus collapse-bar open/close (Blocking 1) — this *is* the operator’s question.
2. **Held-book fire count** of the −12% / −10% 14-day gate versus −16% (Material 6).
3. **Whether the incumbent already skipped May day two** at 21 May open.
4. **Rank-churn P&L and recovered names** under `gate12_2d` (collateral of a tighter gate, the thing Part B was for in Draft 1).
5. **Cycle P&L of 19–21 Aug and 20–21 May** as date windows, not vault names.
6. Forward returns from the **first** strike, not from a cluster label that already contains the second (Blocking 2).

It does not need: 4h backtest, −7%, strike-one, quantile breakers, Part E, or a cluster family.

---

## Overall verdict

**Worth running with the changes above. Not worth running as written.**

Draft 2 is the right notebook shape: Part 0, then a tighter incumbent gate at 48 hours, then stop. The 19 Aug T-1 gate really is −14.5%, so `gate12_2d` really does sell that morning, and HyperCore in this universe is almost certainly an immediate open fill. That is a real answer to “can we react in a day”: **often we do not need to; the 14-day gate was already there two days early.**

As written, the plan can still (a) call a close fill a catch because `executed_at` equals the decision, (b) abort on a 2-day default delay that this pair does not use, (c) kill or bless runs 4–5 with a circular, underpowered screen, (d) relabel a gate-6 spike as “one-event NOT CONFIRMED”, and (e) run a breaker that cannot beat the 21 May gate. Those are heading bugs, not leftover Draft 1 cells.

Run this, and stop:

1. Part 0: path, gate vs daily −14.5% with timestamps, **fill-price assertion**, −12% fire count, 4h coverage, first-strike forward table (no kill-switch).
2. `anchor` vs BASELINE.
3. `gate12_2d` + `gate10_2d` for plateau. Expect REJECT on gate 6 (and maybe gate 2) if the fill is a catch; that is the result.
4. `anchor_1d` as a cadence diagnostic on the **anchor’s** 2d timestamps. No 1d gates unless this passes H1 **and** step 3 did not already catch August.
5. Cluster only as a labelled diagnostic of the T-1 point, if at all.

Expect REJECT or NOT CONFIRMED. That is still worth the notebook if the heading says whether the 19 Aug fill was the 19 Aug **open**.
