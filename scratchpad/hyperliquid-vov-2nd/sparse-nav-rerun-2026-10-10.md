# Sparse NAV metric audit and rerun

Updated **10 October 2026**. [Experiment summary](summary.md) · [NB08 findings](08-score-forecast-findings.md) · [NB09 findings](09-k-ratio-feature-forecast-findings.md).

## Scope and calculation policy

Audit metric calculations in **NB01–NB09** and their supporting modules. Use the unchanged 7 October restored archive. Default result period is **2026-01-01 → 2026-10-05 (end exclusive, UTC)**; NB08 also replays full history from 2023-03-01. This audit does not cover every unrelated notebook in the repository.

Every metric family can consume a daily positive-NAV series with **causal forward filling**. Carry a previously observed value over missing calendar days; never backfill before the first observation or compress elapsed days. Historical inputs end at T−1. Keep actual observation masks, timestamps, counts and ages separately. Future labels remain censored after each vault's last actual positive mark and the archive end. Filling a price does not create an observation or a permission/capacity record.

Fixed lookbacks still require enough elapsed history. Sharpe/Sortino and K remain undefined when their relevant denominator is zero; completely flat paths are not automatically assigned a favourable risk score. Max K needs at least three fitted daily points, starting at the first recorded positive NAV. Recorded history is not certified inception.

## Metrics inspected

The table separates observed defects from already-correct source handling. Earlier strategy experiments need no sparse-data rerun because their metric inputs are unchanged by additional filling.

| Layer | Metrics | Finding and action |
| --- | --- | --- |
| NB01–NB07 source universe and score panel | CAGR, Sharpe, Sortino, drawdown, Calmar, 90-day inverse variance and return gate | The source universe already forward-fills daily candles. All 514 vault columns have zero gaps after their first positive source mark; explicit extra filling changes no values or returns. Retain existing results. |
| NB03 alternative allocation | Regularised volatility, correlations/covariance and risk budget | Uses those same filled candles and daily calendar returns. No additional sparse-input defect found; limited pair overlap and constant correlations use the declared prior/shrinkage rules. |
| NB08 future labels | Return, CAGR, Sharpe and realised volatility | Previously required actual endpoints or every actual daily mark. Rebuild from daily raw positive NAV with causal carry, retaining actual counts and terminal censoring; rerun forecasts, thresholds and portfolio arms. |
| NB08 rejected-entry diagnostics | Foregone 30-day return and marked PnL | The legacy annotation also demanded actual endpoints. Recompute from causally carried raw NAV with terminal censoring, preserving actual endpoint counts and the original economic state. |
| NB08 market diagnostics | BTC/ETH beta and market residuals | Use filled calendar NAV consistently. Keep supported calendar-return counts separate from actual-observation-supported counts; the old “actual daily returns” caption would become incorrect after filling. Regularise reference calendars before log differences and censor beyond last reference mark. |
| NB09 historical features and targets | All five old metric families plus K | Previously rejected sparse calendar windows, including all-history K and year features. Fill the full calendar before slicing windows, refit and rerun in place. |
| NB09 additional path diagnostics | EWMA volatility, autocorrelation, variance ratio, weekly K and flat/activity measures | Inherit the corrected daily NAV grid. Weekly samples remain seven calendar days apart. Observation-quality controls continue to count real marks. |
| Portfolio reporting | CAGR, Sharpe, Sortino, drawdown, quarterly return and attribution | Uses marked portfolio equity and the declared daily/cycle clock. Missing valuation days carry the last equity value, equivalent to zero return until the next mark; elapsed days are retained. No new sparse-NAV defect identified. |

## Source input audit

This covers the full source candle calendar, while the feature-coverage comparison below uses 2026. The repeated fill is idempotent, so source scoring, sizing and portfolio control values remain unchanged.

- Source vaults: **514**.
- Source calendar days: **1,314**.
- Missing source marks after first positive NAV: **0**.
- Source returns equal returns from an explicitly filled daily grid: **yes**.
- Underlying actual daily marks: **106,031**; source carried daily marks: **81,377**. These are separate categories.

## Same-anchor metric coverage — 2026-01-01 → 2026-10-05

Identical **24,605 actual-observation anchor rows** isolate the calculation change. This denominator excludes newly admitted carried anchors. Missing fixed-window history and degenerate ratios remain legitimate reasons for unavailable metrics.

| Feature          |   Actual-anchor rows | Before finite fraction   | After finite fraction (same rows)   |
|:-----------------|---------------------:|:-------------------------|:------------------------------------|
| 30d CAGR         |                24605 | 80.2%                    | 93.7%                               |
| 30d Sharpe       |                24605 | 67.8%                    | 79.6%                               |
| 30d Sortino      |                24605 | 67.4%                    | 78.9%                               |
| 30d Max drawdown |                24605 | 80.2%                    | 93.7%                               |
| 30d Calmar       |                24605 | 80.2%                    | 93.7%                               |
| 30d K-ratio      |                24605 | 68.7%                    | 80.6%                               |
| 360d K-ratio     |                24605 | 0.0%                     | 26.7%                               |
| max K-ratio      |                24605 | 27.3%                    | 98.5%                               |

Admitting carried anchors expands the NB09 population to **31,274 rows**. Max K is then finite for **30,560 (97.7%)**; 360-day K for **8,052 (25.7%)**. The max span ranges from **2 to 1,312 days**, median **217 days**. On the original actual anchors, max coverage is **98.5%**, rather than the earlier 27.3%. Both denominators are reported to avoid attributing population changes to the formula alone.

## Updated forecast findings — 2026-01-01 → 2026-10-05

### Experiment 09

Adding six K inputs improves all six supported rank-IC point estimates. Seven-day CAGR/Sharpe/K changes are approximately **+0.0029/+0.0117/+0.0074**; thirty-day changes are **+0.0017/+0.0117/+0.0067**. Every seven-day incremental block band includes zero; thirty days has only three complete blocks. Ninety-day forecasts remain unsupported under NB09's fixed 2026-only training requirements.

Max-only additions improve every point estimate relative to four-window K; year-only additions lower every point estimate. Growth MAE is still **17.9%/25.3% worse than zero return** at seven/thirty days. These are leads for confirmation, not evidence of improved portfolio returns. No portfolio is run in NB09.

### Experiment 08

Thirty-day return rank IC is **0.0867–0.0890**, with bands spanning zero. Sharpe rank IC is **0.1286–0.1366**, with positive exploratory bands. Return ranking still reverses from positive Q1 to negative Q3.

The old blanket claim that all calibrations lose to constants is superseded. Thirty-day improvements are small and mixed. Ninety-day calibrations have **47 supported evaluation origins** using earlier matured filled-history labels, and beat constants on MSE by **3.6–6.6% for log return** and **2.8–5.4% for Sharpe**. Overlap and the held-NAV assumption constrain interpretation.

All 2026 portfolio controls reproduce their earlier numbers. Absolute floors are active in **27/30** method-months but veto **zero entries**. The percentile floor changes one seven-position four-input entry, with an effect also reproduced by random vetoes. Forecast improvements do not establish a useful cash threshold.

Full-history percentile effects are mixed: v11 gains **0.31–0.83 percentage points** of CAGR; four inputs lose **0.95–1.25 points**, and Blend 46d loses **0.46–1.12 points**. Absolute floors reject no entries in either period. The six additional full-history unscored-entry replays lose **3.75–5.31 points** of CAGR versus their own controls.

The corrected foregone-return diagnostic supports the one distinct 2026 rejected entry: its filled-NAV thirty-day gross return is **−37.79%**, previously missing because the anchor had no actual daily mark. Eight ledger instances refer to this same entry across treatments/random controls. Full-history labels cover **362 distinct vault/date rejections**, repeated in **8,072** arm-specific ledger instances; these repeats are not independent evidence. Source economic paths and costs are unchanged.

## Independent checks and interpretation

- All five old metric families and K agree with independently forward-filled sparse fixtures.
- Leading gaps are not backfilled; future changes do not alter historical fills.
- Sampled max K fits agree with independent intercept OLS on the full filled calendar.
- Future labels agree with independent reconstruction from actual archive rows and terminal censoring.
- Experiment-05 source feature values and earlier source-compatible feature IC still reproduce.
- Missing=True retains partial-history forecasts; training transforms and label maturity remain causal.
- Final NB08/NB09 runs execute all **11/19 code cells** with no errors, stdout streams or logged warnings. NB08 includes **132 portfolio arms**, **six additional full-history missing-score replays** and the recalculated foregone outcomes.
- All **1,251 NB08** and **99 NB09** separate catalogue images decode correctly; main notebook images also validate. Both exact static notebook previews return HTTP 200. This validates saved images and rendering; it is not a claim that all refreshed figures received individual visual inspection.
- All nine main notebooks validate and retain completed code outputs. Earlier NB01–NB07 results are retained because the sparse-input audit proves their consumed prices and returns are unchanged.

Forward filling assumes NAV remains at the last reported level between observations. Risk/path metrics can reflect reporting cadence and carried flats as well as economics. Keep dense-observation, observation-age, activity and precision sensitivities alongside the primary results. No missing redemption payout, permission record or historical listing is invented.

## Reproducibility

Pre-fill notebook, source and headline datasets are retained in ignored `08-before-sparse-fill` and `09-before-sparse-fill` namespaces. Current derivatives remain under ignored `08`/`09`; no archive refresh was performed. `audit_sparse_metrics.py` records the shared input audit and same-anchor coverage. Current notebook findings and `summary.md` supersede the old complete-observation conclusions.
