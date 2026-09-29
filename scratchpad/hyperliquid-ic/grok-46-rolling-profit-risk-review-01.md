# Grok 4.6 review of the rolling profit/risk plan

Completed with Grok CLI `--model grok-4.6`; actual backend `grok-4.6-build`. Nine history passes plus this synthesis completed with `end_turn`. Read together with [the disposition](grok-46-rolling-profit-risk-disposition-01.md): this raw review contains suggestions and claims the author did not accept.

I'll read the remaining supplied reviews, production source and feature documentation, then synthesise them against the draft plan.The remaining reviews and the production/feature sources are next; I’ll read those before judging the draft plan.I’ll finish the remaining reviews, then check production ranking/sizing and the feature-engineering notes.Independent synthesis of the nine history reviews, production `hyper-ai.py`, the examples comparison, and the feature-engineering contract. Markdown narratives only; code cells and numerical outputs were not re-audited.

## 1. Plan flaws

**R1–R3 mostly reinvent failed stability ranking.** Lower-vol NB32 already did “keep some profit, then prefer calm”: 26/30 non-incumbent configs had negative CAGR; calm/downside/ulcer/Sortino rankers lost even with a 15–30% floor. Waterfall NB24 made trailing CAGR or Sharpe as the *ranking* key a true negative; NB31 showed inverse-vol *selection* is a different defensive book (~11.5% CAGR), not a simplification of the composite. IC rewrite: interval vol predicts vol (IC ~0.77) while short-core growth IC is ~0.12 and lost to a low-downside sort; the growth-model allocator then lost after accounting was repaired. R1 (`U(g)/max(v,0.05)`) is a continuous form of that same vol-in-the-denominator ranker. Calling it “joint” rather than “floor then calm” is a formula difference, not a new mechanism. R2 stacks a drawdown term whose hard cousin (D1 ≤3%) already failed as a replacement book (IC NB16/NB20). R3 ranks trend smoothness; ATM had zero observed drawdown and a near-linear path, then lost 88.9% in 14 days. Two-point lines will look perfect. Feature-engineering PR #524 is the same warning: residualise against vol before treating a risk-adjusted score as profit skill.

**Equal-weight six-name isolation should not be the first test.** Waterfall NB69: equal weight and composite-score sizing were loss-making at $150k; volatility weighting is load-bearing, partly as a capacity rule. Production sizes by 90-day inverse variance (`hyper-ai.py`). Ranking-isolation on a known-bad sizer confounds R0 vs R1 with a sizer the chain already rejected. Rank-preserving sizing (same membership, production inverse variance) is the first operational test, not Notebook C item 1. The six-name quota also contradicts the contract’s “do not force a fixed number of weak candidates; leftover cash is allowed.”

**The short-history risk fallback is the `drop_30` bug with a new label.** Missing `inverse_vol` stored as 0.0 and sorted as most volatile was the actual placebo (NB21/NB26: ~71% of N=30 removals unmeasured; `unmeasured_30` bit-identical to the anchor). Substituting training-frozen upper-quartile risk does the same thing: young and weekly names look risky and lose rank. That is the opposite of “able to receive capital.” Production already zeros missing 90-day vol (`inv_vol … else 0.0`), which is why StratWise had zero engine positions even when overlays “allowed” it (IC NB20). Two marks can still produce a huge annualised `g` (×365), so a conservative `v` need not stop a jump from ranking first.

**`U(g)` does not solve the real plateau, and annualised `g` amplifies jumps.** The NB24 failure was every selected vault scoring exactly 1, so coefficients could not change membership (C12/C36/C44 identical; later −38% CAGR; ATM two perfect months then −$21k). Production already caps CAGR at 100% and Sortino at 3.0. A slow log still ranks ATM’s ~18% 28-day run above StratWise’s 0.31% median week. Soft scores fix *hard 0–1 ties*, not ATM, and not “profit while ranking risk.”

**Cash-floor C.3 is vague and is the wrong cash experiment.** “Positive subsequent return with tolerable downside” will be fitted on Notebook A. The only overlay that moved Sharpe toward the ~20% region without a new ranker was A0-cap: do not refill clipped dollars (~12.5% CAGR, Sharpe 1.17, ~45% cash; leader-out 3.0%/0.31). That is geometry, not a quality floor. Do not mix “more cash” with “better selection.”

**C.4 `n/(n+4)` is a soft observation-count barrier.** Weekly names have fewer intervals; the haircut treats them as low-evidence. The user forbade compulsory observation-count/long-age barriers. Cadence-matched freshness (do not treat a weekly print as stale) is the version that does not punish the desired cohort.

**R0 is not a matched control.** Production is 360-day CAGR + 45-day Sortino + 14-day gate at −16% + 90-day inverse variance + six slots + 33%/33% caps. R0 is `U(g)`, equal weight, six names, short clock. Too many differences. The contract correctly asks to reproduce the original policy, then match the operational universe; B as written still changes ranking, lookback, sizing, and score cap at once.

**Blacklist wording mixes data quality with performance masks.** IC NB18: all six blacklist-off comparisons lost CAGR and Sharpe. Production `MANUAL_BLACKLIST` is Scared Money (share-price precision), not a performance judgement. Keep that exclusion; disable research performance masks only.

**Notebook A mostly re-asks a settled vault-level question.** Trailing vol/downside predict forward vol/downside (NB28/NB34). Predicting vol is not a portfolio edge (`measured_8` +0.21 Sharpe, inside noise, rank 4/20 vs a persistence-destroying null). Within-profit lower-risk ranking is NB32’s mechanism. A is useful only as coverage and score-spread, not as a licence to ship R1.

## 2. Prioritised options

Do not stack these. One mechanism per run. Do not fit to StratWise or L/S Grids; report them after the fact. Kill bars use ~20% as a *region*, not a per-slice mandate, and do not require beating hyper-ai.

**1. Replace only the 360-day composite with available-history interval growth; keep production sizing and gate.**\
Rank depositable names by elapsed-interval log growth over `min(30 calendar days, available history)` — not annualised for ranking (annualisation is a reporting unit). Keep the 14-day gate, six-slot cap, 33%/33% caps, 2-day cadence, fee-correct NB24 harness. Size with production inverse variance, but compute σ on the *same actual intervals* as the growth score. If σ is underdetermined, give that selected name an equal share of the selected set; never 0.0 and never upper-quartile risk. Two marks suffice for growth; missing risk does not eject the name.\
*Why new:* Waterfall Phase C never tested a short clock as the primary selector (360-day CAGR is the age wall: ~66% never scorable; youngest anchor entry 361 days). IC overlays never changed that score, so StratWise got $0. NB32 ranked *calmness* after a floor; this ranks *profit* on a short clock.\
*Falsify:* requested weight of names with <180 days of history stays 0; or later-period capital-weighted subsequent vault return is worse than the fee-correct original on the same dates *and* the book is one jump (top contributor collapses inside 14 days, ATM-class). Kill if CAGR < 0. Do not kill for not beating the incumbent.

**2. On that frozen membership, equal weight vs production inverse variance vs available-history inverse variance.**\
Same names, three sizers, report requested → accepted weights after capacity.\
*Why new:* NB69’s “volatility weighting is the strategy” was measured on the 360-composite basket. IC NB21/22 withdrew “flexible N = quality.” Untested on a short-history selected set.\
*Falsify:* inverse variance of the short basket turns a profitable equal-weight set into a quiet loss (NB32 leakage into sizing). If equal weight cannot deploy, that is capacity, not ranking.

**3. Do not refill clipped capital (A0-cap geometry).**\
Keep ranking from (1) or from the reproduced original. After pool/concentration caps, leftover stays cash. One frozen rule. Cash-matched parent at the same invested fraction; one leader-out resimulation.\
*Why new:* This is the cash result the track actually has. It is not a score floor and not another vol-target overlay (NB04 cut Martin).\
*Falsify:* Sharpe gap vs the cash-matched parent is ~0 (dilution); leader-out collapses the result (concentration). If young names still get zero size, the 90-day vol zero is still binding — fix sizing, do not add a floor.

**4. Graded fallback inside the incumbent composite, not a new ranker.**\
Keep `cagr_sortino_weight` when both legs exist. If 360-day CAGR is NaN, score available-history growth with the same 0–1 map (or leave the Sortino leg alone if a down interval exists). No reserved junior slot (waterfall NB48 J=1 is a true negative). Missing vol as in (1).\
*Why new:* NB16 *replaced* the whole book and lost on the hidden cohort (median event-time Sharpe −0.35). Waterfall NB51 proposed a graded immature score; NB48 tested reserved slots instead.\
*Falsify:* Jaccard ≈ 1 vs original (no-op); or the fallback sleeve’s matured 30-day return ≤ 0 in both the sparse-early and dense-late segments.

Drop from the first wave: R2/R3, `U(g)` unless A shows it changes membership vs raw `g`, score-proportional sizing, all-positive-score breadth, `n/(n+4)`, measured_8 retunes, 180-day Sharpe as the first ranker (still ~180 days; StratWise at ~61 days stays unscored), monthly/weekly bucket gates.

## 3. Keep / defer / drop

| Item | Disposition |
|---|---|
| Shared contract (hashes, fee-correct NB24, both windows, interval not ffill, cadence fixed, leftover cash, no named-vault rules) | **Keep.** Audit the NB24 redemption helper as planned. Keep Scared Money; disable performance masks only. |
| Notebook A | **Keep, shrink.** Score spread/ties of raw `g` vs `U(g)` vs production composite; finite-`g` vs finite-`v` coverage by age and sparse/dense; descriptive StratWise / L/S Grids / ATM / Orion paths. If `U(g)` and `g` pick the same top set, drop `U`. **Drop** within-profit-group risk ranking as a go/no-go for R1 (that is NB32). |
| B: reproduce original policy | **Keep** as the only matched anchor. |
| B: R0 profit-only | **Keep**, but with production inverse variance and the same gate/universe as the original, not equal-weight six. |
| B: R1 | **Defer** until A shows lower interval vol *inside a profitable set* predicts better forward *return*, not only lower vol. Otherwise it is NB32. |
| B: R2 | **Drop** from the first wave. More complex than R1; ATM had D=0. |
| B: R3 | **Drop.** Smoothness ranker; ATM; two-point fit. Keep residual `e` as a plot in A only. |
| B: equal-weight six | **Defer** to a labelled sibling of one ranking lead. Not the primary B design. |
| B: upper-quartile risk fallback | **Drop.** Replace with available-history vol or equal-share. |
| C.1 equal vs score-proportional | **Keep equal vs inverse variance** on frozen membership; **drop** score-proportional (NB69). Run with the ranking lead, not after a fitted floor. |
| C.2 all positive scores | **Defer.** Greedy tail refill (IC-2; NB21/22). |
| C.3 training-frozen score floor | **Drop** as written. Replace with option 3 if a ranking lead exists. |
| C.4 `n/(n+4)` | **Drop.** Soft observation-count barrier; punishes weekly names. |

## 4. Conflicts, rejected suggestions, coverage

**Rejected (violate the brief or ignore other batches).** `account_pnl` / volume / followers (lower-vol-1; Stage C; user forbade). Reserved StratWise-type slots/sleeves (lower-vol-2 Idea 4; IC-2 Idea 4; NB48). Event-count or 60-day-span admission (observation/age barriers). BTC circuit breaker and |β| vetoes (A3 negative; optional BTC is diagnostic only). Hard crash/drawdown overlays (IC NB20: 0/24 improved Sharpe). Monthly consistency as ranker or tie-break (user: direct rolling metrics; NB23/24 true negative). `drop_30` / `q30` / stability rankers / joint-loss / Sortino-leg swap / trim / N<6 / cap-off / core-satellite. Fitting thresholds to StratWise or L/S Grids. Another NAV/provenance project as the selection work. Must-beat-incumbent or 20% in every subperiod.

**Conflicts resolved, not averaged.** A0 vs A0b vs production is universe membership, not a ranking result (IC-08/09). `drop_30` is one vault in one quarter plus an unmeasured filter (NB26), not a vol law. `measured_8` is a small, unconfirmed, blacklist-sensitive prefilter; it does not admit young names and is not this rolling-metric programme. `floor15` is knife-edge and window-dependent (NB32/33) and still cannot score sub-year names while CAGR-360 remains. A0-cap is cash plus a leader, not a 20% product. Prefer summary-03 A0-young (+8.5%) over stale summary-04 (−3.6%). Production docstring ~62% CAGR is Jan–Jul 2026; lower-vol full-window ~37.9% to 8 Sep; fee-correct IC NB23 ~4.8% — never mix with a new run. Sortino did not beat Sharpe at the same winner (NB82); keep production’s Sortino-as-NaN-on-zero-downside behaviour, do not re-search it. ERC (NB07) is a near-miss on the *incumbent* book, un-LOVO’d, and not a young-access fix.

**Coverage.** Nine independent markdown passes over 152 notebooks and 106 research documents; no code-cell audit. Feature-engineering.md is mostly Binance/vol/TFT; the transferable rules here are missing≠zero, vol-residualisation, screens≠portfolios, and “IC is not a strategy.” L/S Grids has no dedicated selection ledger (NB24 P&L line plus the examples table). StratWise is a snapshot/forensics object with zero production-engine fills. Point-in-time `written_at` and deposit windows remain unprovable. No untouched hold-out remains; early/later is retrospective. Sharpe MDE on ~125 two-day cycles is large (~2.5). ATM is the bound on price-only crash detection; do not claim a rolling metric will catch the next one.
