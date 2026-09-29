# Grok 4.6 xhigh plan review

Run on 2026-09-19 with `--model grok-4.6 --reasoning-effort xhigh --sandbox none`. CLI resolved model: `grok-4.6-build`. Completed normally with `stopReason: end_turn`. Reviews the initial draft, not the subsequent revisions; see disposition.

**Verdict: revise.** Stage 0 (repair and timing-audit NB30, then rerun) is the right first step and should happen before any basket. The four-arm basket, as specified, does **not** identify incremental Q. On the saved panel a `Q>0` floor is almost a high positive-window-share cut, young vaults pass it more often than mature ones, and the named simulator/accounting parent is not the module or convention the plan thinks it is. Do not implement `31-research-steady-profit-baskets.ipynb` until those are pinned. Do not treat the old 2.0 / 3.3 percentage-point top-group gaps as evidence.

What the saved NB30 numbers actually support, after the known bugs:

- Spearman ICs for `Q25_7_60` are the only plausible lead: mean ρ **0.112** (30d, 379 dates) and **0.141** (60d, 349 dates) in `marginal-summary.csv`.
- Residual return IC after G, P and V is **0.036** (`conditional-residual-statistics.csv`, `Q25_7_60` / `G_P_V` / return). That is the incremental-Q number.
- Paired return contrasts were computed on **219 / 196** dates, not 379 / 349, because `dropna()` on return **and** drawdown together. Versus P at 30d the difference is **+0.024** with CI **[-0.026, +0.088]** (`paired-block-contrasts.csv`). Versus inverse volatility, Q **loses** on return.
- On opportunity rows, `Q>0` is a subset of `M>0` (0 rows with `Q>M`). `Q>0` disagrees with `P≥0.75` on **2.0%** of rows.

So a hard `Q>0` basket tests a high-P screen plus a 1–n policy, not the continuous Q ranking that produced the IC.

---

## High

**1. The novel intervention does not test incremental Q.**\
`steady-profit-basket-plan-01.md` Four-arm table (arms A/B) versus `_artifacts-rolling-typical-profitability/feature-label-panel.parquet`.

`finite M>0 and finite Q>0` is identical to `Q>0` (Q≤M always). On this panel `Q>0` is 12.7% of opportunity, `M>0` is 46.6%, and `Q>0` matches `P≥0.75` on 98% of rows (P when `Q>0`: min 0.50, 25th 0.78; P when `Q≤0`: max 0.75). NB09 already rejected ranking by `positive_window_share` (CAGR 24.3%, cycle Sharpe 1.49 versus anchor 37.9% / 2.16). NB20 hard screens improved 0/12 full-period Sharpes. NB32’s return-floor-then-stability grid had 26/30 negative, best CAGR 8.8%. Residual Q after G, P, V is 0.036.

**Minimal fix:** Keep A as the `M>0` control if you want a floor experiment, but rename B to what it is: a weaker-period / high-P hard screen. Promotion must require B−A **and** a date-level disagreement with `P≥0.75` among A’s names. If you want the NB30 lead, the matched test is ranking or weighting by Q on the same A universe, not a zero floor. Do not add another threshold grid.

**2. Named accounting parent does not match the code.**\
`rolling_track_simulation.py` is an engine job runner (`run_engine_jobs` → `run_variant`), not an independent allocator. Independent replay lives in `ic_research.capped_weights` / `simulate_allocator`, which **redistributes** clipped capital. NB28 E1 is the opposite: original shares once, residual cash (`exposure-method-check.csv`: parent `AlphaModel._normalise_weights_size_risk_positions` redistributes). B00 itself is six-slot original policy, two-day engine, Sharpe `sqrt(365/2)` (`nb20_stability_screens.curve_metrics`). Rewrite config uses `production_rebalance_days: 2`, `max_weight: 0.33`. The plan asks for daily decisions, 1–n, no concentration, E1 no-refill, and daily Sharpe with 365-day annualisation, while “reproducing B00”.

**Minimal fix:** Pick one stack and write it down: (i) engine B00 replay with the existing `curve_metrics` clock, then E1-style projection on A–D, or (ii) a no-refill fork of the independent simulator with daily marks. Do not compare `sqrt(365)` daily Sharpe to B00’s `sqrt(365/2)`. Treat B00 as an accounting replay only; Q is B−A, not basket versus B00.

**3. Young vaults are not handled fairly; they are over-selected.**\
Same panel. Opportunity already has **100% finite M and Q** (`coverage.csv`; 81,095/81,095). Under-h “Q unavailable” never appears once the −16% gate and TVL floor are applied. `<30d` pass `Q>0` at **28.9%** versus **10.8%** for `≥90d`. 35% of `<30d` rows have fewer than four events. One qualifying name may take all capital. That is the NB24 saturation failure (perfect short-history scores, then large losses), not a long-history barrier.

**Minimal fix:** For B/D membership only, treat `unique_event_count < 2` (and rows with `exact_median_equals_q25`) as Q unavailable — still in A/C and the opportunity ledger. Report capital and contribution split by `<30 / 30–89 / ≥90` and by event-count. If young capital is large because Q cannot fall below M, record that as the floor not identifying a lower tail. Do not add a 90-day admission rule.

**4. Timestamp contract is still contradictory; Stage 0 must pick one.**\
NB30 markdown: marks on T-1 only. Code: `boundary = date + 1 day` (`build_nb30_typical_profitability.py` `rolling_row`). Saved panel: 72% of opportunity last marks sit on date T; none after T. Rewrite `config.json`: features before date+1 00:00, labels enter at the first fresh mark **at or after** that timestamp. Labels: 0% enter on date, 59,716 enter on date+1; 100% of joined entries are after the formation last-mark day, with 23,708 rows at a 7-day gap. Parent rolling features use `daily.index < decision` (`rolling_track_features.py`). Original NB30 spec wanted the label start to be the last formation mark.

**Minimal fix:** Freeze one contract (rewrite date+1 vs NB25 `< decision` vs original T−1). Recompute M/Q under that contract. Do not mix NB30 features with B00 marks. Keep real observation timestamps on daily-last marks. Confirm a T-close feature is never paired with a start-of-T fill.

---

## Medium

**5. Stage 0 repair list is right; do not skip the audit.**\
`fractional_top_membership` always ranks `ascending=False` (direction ignored for −V/−A/−D). Boundary overwrite is not `clip((target − strictly_better) / tied, 0, 1)`; constant scores can get weight 0. Top returns divide by all membership, including missing labels. Paired `dropna()` on return and drawdown cuts return dates from 379 to 219. Conditional residuals were only run at H=30. Cohort table used **median**, not Q. Containment uses `argmax(rates)` (largest per-day rate), not the largest positive observed interval. `last_mark_per_day` drops to a day index, so ages are integers (min last-mark age 1.0).

The plan already withdraws the 2.0 / 3.3pp top-group claim. Keep that. ICs for Q may survive; top-group and paired-return tables must be rebuilt before they inform B.

**6. Interpretation rules fight each other.**\
“Do not select between W=60 and W=30” versus “prefer the highest Sharpe among baskets near 20% CAGR” versus “survives the neighbour setting reasonably”. Uncorrected `Q25_7_30` residual G_P_V return IC is **−0.005**. A 20% CAGR on hyper-ai (B00 51.5%) is a different object from 20% on full (B00 9.7%).

**Minimal fix:** Drop the Sharpe-near-20% preference. Report all 16 runs. Predefine “neighbour survives” as sign agreement on B−A invested-vault outcomes, or call W=30 descriptive only. 20% CAGR stays a reporting band, not a picker.

**7. Inverse-vol control is valid; the 10% floor will flatten it.**\
NB27 on B11: equal −89% CAGR, inv-vol −91% (`rolling-profit-risk-track-summary-01.md`, `nb27/portfolio-metrics.csv`). Here C/D are controls, which is correct. About 20–24% of names have trailing vol `<0.10`, so many C/D weights collapse toward equal. Missing vol is rare (0.2% of `<30d`) but is then treated as 10% vol, i.e. as a calm name.

**Minimal fix:** Keep C/D. Report the share of requested weight sitting on floored vol. If C≈A because of the floor, say so; do not call it a sizing result.

**8. Exposure scale-control is the right cash/risk separator; trigger on desired weights, then report realised mismatch.**\
NB28 already showed that cutting exposure is not the same as better selection (E2 full Sharpe 0.20 versus E1 1.10). Keep the 5pp rule. Do not treat a cash-heavy B as Q quality.

---

## Low

**9.** Arm B’s “and M>0” is algebraically redundant; write B as `finite Q>0` (with Q from the same sample as M). Harmless, clearer.

**10.** `31-research-steady-profit-baskets.ipynb` is free after NB30. Fine.

**11.** Per-date `Q>0` count is 16–37 (median 25), so “one name takes 100%” is allowed but not the historical typical case. Still log empty/single-name dates.

---

## Experiments to remove or change

| Keep / change | Why |
| --- | --- |
| **Change B from “incremental Q” to a frozen high-P / weaker-period floor, or replace it with Q ranking/weights on A’s names** | Otherwise this repeats NB09 P, NB20 hard screens, and NB32 floors, while the Q residual is 0.036. |
| **Do not add 14-day, extra W, extra floors, drawdown haircuts, or StratWise-fitted cuts** | Plan already avoids these; keep it that way. |
| **Do not treat C/D as a second discovery** | Inverse-vol failed on bad membership (NB27). Controls only. |
| **Do not promote from hyper-ai or from a later inherited-state slice** | Already stated; keep. Later is not a holdout (`rolling-profit-risk-track-summary-01.md`). |
| **Do not run the basket on unrepaired NB30 membership/top-group tables** | Stage 0 is mandatory. |

A four-arm factorial on a repaired panel is still a reasonable **floor** experiment if B is labelled as such and P-overlap is reported. It is not a test that Q’s rank IC survived into portfolio Sharpe.

---

## At most two extra ideas (identifiability, no search)

1. **Date-level Jaccard of `Q>0` versus `P≥0.75` among A’s names**, plus capital and subsequent return on the disagreement set only. If Jaccard is ~1, a B−A win is a P-floor result. No extra grid.

2. **Descriptive split of B/D P&L into `Q<M` (lower tail exists) versus few-event / `Q=M` (quantile not identified).** No reallocation, no new arm. If the second bucket drives the result, the floor did not find steadiness.

---

## Files actually read

- `scratchpad/hyperliquid-ic/steady-profit-basket-plan-01.md`
- `scratchpad/hyperliquid-ic/rolling-typical-profitability-plan-01.md`
- `scratchpad/hyperliquid-ic/build_nb30_typical_profitability.py`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/marginal-summary.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/coverage.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/paired-block-contrasts.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/conditional-residual-statistics.csv` (aggregated)
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/cohort-summary.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/reference-vaults.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/manifest.json`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-typical-profitability/feature-label-panel.parquet` (small aggregations only)
- `scratchpad/hyperliquid-ic/rolling-profit-risk-track-summary-01.md`
- `scratchpad/hyperliquid-ic/monthly-calibration-summary-01.md`
- `scratchpad/hyperliquid-ic/production-candidate-vs-research-reproduction-differences.md`
- `scratchpad/hyperliquid-ic/stability-screens-summary-01.md`
- `scratchpad/hyperliquid-ic/_artifacts-stability-screens/heading-results.md`
- `scratchpad/hyperliquid-ic/_artifacts-stability-screens/screen-effect.csv`
- `scratchpad/hyperliquid-ic/20-research-stability-screen-portfolios.ipynb` (markdown via JSON)
- `scratchpad/hyperliquid-ic/nb20_stability_screens.py` (`curve_metrics`, screens)
- `scratchpad/hyperliquid-ic/30-research-rolling-typical-profitability.ipynb` (markdown via JSON)
- `scratchpad/hyperliquid-lower-vol/09-backtest-consistency-selection.ipynb` (markdown/JSON; `positive_window_strict` CAGR 0.243, cycle Sharpe 1.493)
- `scratchpad/hyperliquid-lower-vol/_build/build_09.py`
- `scratchpad/hyperliquid-lower-vol/32-backtest-return-floor-stability-rank.ipynb` (markdown via JSON)
- `scratchpad/hyperliquid-lower-vol/_build/write_heading_32.py`
- `scratchpad/hyperliquid-lower-vol/_build/manifest_32.json`
- `scratchpad/hyperliquid-ic/rolling_track_simulation.py`
- `scratchpad/hyperliquid-ic/rolling_track_features.py`
- `scratchpad/hyperliquid-ic/build_rolling_track.py` (B00/B11/E1 patches)
- `scratchpad/hyperliquid-ic/ic_research.py` (`capped_weights`, `simulate_allocator`)
- `scratchpad/hyperliquid-ic/_artifacts-rewrite/config.json`
- `scratchpad/hyperliquid-ic/_artifacts-rewrite/feature-manifest.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rewrite/label-coverage.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rewrite/labels.parquet` (entry timing only)
- `scratchpad/hyperliquid-ic/_artifacts-rolling-profit-risk/nb25/portfolio-metrics.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-profit-risk/nb27/portfolio-metrics.csv`
- `scratchpad/hyperliquid-ic/_artifacts-rolling-profit-risk/nb28/exposure-method-check.csv`
- `scratchpad/hyperliquid-ic/grok-46-rolling-typical-profitability-review-01.md`
- `scratchpad/hyperliquid-ic/grok-46-rolling-typical-profitability-disposition-01.md`

No files edited. No notebooks executed. No subagents.
