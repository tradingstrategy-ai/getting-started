# Experiment 09 — K-ratio feature forecast findings

Default period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**. In-place post-review amendment; original results archived separately. No data refresh or portfolio-rule change.

## Key new insights

All historical metrics and realised targets now use causal daily forward fill; the unchanged archive and pre-fill results are preserved in `09-before-sparse-fill`. Adding six K inputs (30/60/90/180/360 days and max recorded history) improves primary mean rank IC in **6 of 6** supported target/horizon comparisons. This is a measured result of fixed amended models on previously researched history, not a general claim about K or an untouched holdout.

- **7-day CAGR:** Existing/Existing + K rank IC 0.018/0.021; delta +0.003; modelling-scale MAE change +0.5%; 45 origins, 25 complete blocks. Exploratory block band [-0.004, +0.011].
- **7-day K-ratio:** Existing/Existing + K rank IC 0.118/0.125; delta +0.007; modelling-scale MAE change -0.1%; 45 origins, 25 complete blocks. Exploratory block band [-0.015, +0.021].
- **7-day Sharpe:** Existing/Existing + K rank IC 0.103/0.114; delta +0.012; modelling-scale MAE change -0.1%; 45 origins, 25 complete blocks. Exploratory block band [-0.011, +0.024].
- **30-day CAGR:** Existing/Existing + K rank IC 0.067/0.069; delta +0.002; modelling-scale MAE change +0.3%; 24 origins, 3 complete blocks. Too few blocks for an uncertainty band.
- **30-day K-ratio:** Existing/Existing + K rank IC 0.159/0.166; delta +0.007; modelling-scale MAE change -0.1%; 24 origins, 3 complete blocks. Too few blocks for an uncertainty band.
- **30-day Sharpe:** Existing/Existing + K rank IC 0.120/0.132; delta +0.012; modelling-scale MAE change -0.0%; 24 origins, 3 complete blocks. Too few blocks for an uncertainty band.
- **90 days:** no supported paired forecast comparison. Illustrative forecasts and descriptive feature relationships do not establish model skill.

## One-year and all-history amendment

One year follows the existing 360-day convention. Max uses calendar-day NAV from the first actual positive mark through T−1, causally carrying prices over gaps, with at least three fitted marks and no backfill or gap compression. Recorded history is not certified inception. Short-window ablations keep shared missingness controls fixed, so the longer K values can be assessed separately from history availability. The previous four-window run is archived under `09-before-long-k`.

- **360d K-ratio:** 8,052/31,274 supported-anchor rows have a finite input (25.7%).
- **max K-ratio:** 30,560/31,274 supported-anchor rows have a finite input (97.7%).
- **Available max durations:** 2–1312 days, median 217 days; 18,047 of 30,560 finite max rows span at least 180 days. Max is not necessarily a longer input for young vaults. One-year availability is measured separately above; young vaults retain usable shorter inputs.
- **Existing + K, 7-day CAGR:** versus four-window K, same-row rank IC 0.0173 → 0.0214; delta +0.0040; MAE change +0.2%; 45 origins, 25 blocks.
- **Existing + short K + max, 7-day CAGR:** versus four-window K, same-row rank IC 0.0173 → 0.0221; delta +0.0047; MAE change +0.1%; 45 origins, 25 blocks.
- **Existing + short K + year, 7-day CAGR:** versus four-window K, same-row rank IC 0.0173 → 0.0164; delta -0.0009; MAE change +0.0%; 45 origins, 25 blocks.
- **Existing + K, 7-day K-ratio:** versus four-window K, same-row rank IC 0.1136 → 0.1254; delta +0.0117; MAE change -0.2%; 45 origins, 25 blocks.
- **Existing + short K + max, 7-day K-ratio:** versus four-window K, same-row rank IC 0.1136 → 0.1255; delta +0.0119; MAE change -0.2%; 45 origins, 25 blocks.
- **Existing + short K + year, 7-day K-ratio:** versus four-window K, same-row rank IC 0.1136 → 0.1133; delta -0.0003; MAE change +0.0%; 45 origins, 25 blocks.
- **Existing + K, 7-day Sharpe:** versus four-window K, same-row rank IC 0.0987 → 0.1143; delta +0.0156; MAE change -0.2%; 45 origins, 25 blocks.
- **Existing + short K + max, 7-day Sharpe:** versus four-window K, same-row rank IC 0.0987 → 0.1143; delta +0.0156; MAE change -0.2%; 45 origins, 25 blocks.
- **Existing + short K + year, 7-day Sharpe:** versus four-window K, same-row rank IC 0.0987 → 0.0986; delta -0.0001; MAE change +0.0%; 45 origins, 25 blocks.
- **Existing + K, 30-day CAGR:** versus four-window K, same-row rank IC 0.0665 → 0.0688; delta +0.0023; MAE change +0.2%; 24 origins, 3 blocks.
- **Existing + short K + max, 30-day CAGR:** versus four-window K, same-row rank IC 0.0665 → 0.0716; delta +0.0051; MAE change +0.2%; 24 origins, 3 blocks.
- **Existing + short K + year, 30-day CAGR:** versus four-window K, same-row rank IC 0.0665 → 0.0634; delta -0.0031; MAE change +0.1%; 24 origins, 3 blocks.
- **Existing + K, 30-day K-ratio:** versus four-window K, same-row rank IC 0.1592 → 0.1657; delta +0.0065; MAE change -0.1%; 24 origins, 3 blocks.
- **Existing + short K + max, 30-day K-ratio:** versus four-window K, same-row rank IC 0.1592 → 0.1661; delta +0.0069; MAE change -0.1%; 24 origins, 3 blocks.
- **Existing + short K + year, 30-day K-ratio:** versus four-window K, same-row rank IC 0.1592 → 0.1580; delta -0.0012; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + K, 30-day Sharpe:** versus four-window K, same-row rank IC 0.1192 → 0.1319; delta +0.0127; MAE change -0.0%; 24 origins, 3 blocks.
- **Existing + short K + max, 30-day Sharpe:** versus four-window K, same-row rank IC 0.1192 → 0.1327; delta +0.0136; MAE change -0.0%; 24 origins, 3 blocks.
- **Existing + short K + year, 30-day Sharpe:** versus four-window K, same-row rank IC 0.1192 → 0.1178; delta -0.0014; MAE change +0.0%; 24 origins, 3 blocks.

## Sensitivities

- **Compact:** positive K delta in 6/6 supported cells; observed delta range +0.006 to +0.011. This range is not a confidence bound.
- **Rank existing:** positive K delta in 6/6 supported cells; observed delta range +0.002 to +0.011. This range is not a confidence bound.
- **Activity existing:** positive K delta in 3/6 supported cells; observed delta range -0.002 to +0.010. This range is not a confidence bound.
- **Compact controls existing:** positive K delta in 6/6 supported cells; observed delta range +0.002 to +0.013. This range is not a confidence bound.
- **Existing complete-case:** positive K delta in 0/6 supported cells; observed delta range -0.010 to -0.002. This range is not a confidence bound.
  - 7-day CAGR: 45 target-valid paired origins, 45 defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.
  - 7-day K-ratio: 45 target-valid paired origins, 45 defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.
  - 7-day Sharpe: 45 target-valid paired origins, 45 defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.
  - 30-day CAGR: 24 target-valid paired origins, 24 defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.
  - 30-day K-ratio: 24 target-valid paired origins, 24 defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.
  - 30-day Sharpe: 24 target-valid paired origins, 24 defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.
- **Existing missing=False:** positive K delta in 6/6 supported cells; observed delta range +0.002 to +0.016. This range is not a confidence bound.
- **7-day CAGR, cadence/delay:** 4/5 positive point estimates; range -0.005 to +0.003.
- **7-day K-ratio, cadence/delay:** 5/5 positive point estimates; range +0.004 to +0.010.
- **7-day Sharpe, cadence/delay:** 5/5 positive point estimates; range +0.005 to +0.013.
- **30-day CAGR, cadence/delay:** 5/5 positive point estimates; range +0.001 to +0.003.
- **30-day K-ratio, cadence/delay:** 5/5 positive point estimates; range +0.003 to +0.007.
- **30-day Sharpe, cadence/delay:** 5/5 positive point estimates; range +0.008 to +0.014.

## Baselines and calibration

- **7-day CAGR versus Constant:** same-row modelling-scale MAE change -0.5% (45 origins).
- **7-day K-ratio versus Constant:** same-row modelling-scale MAE change -1.1% (45 origins).
- **7-day Sharpe versus Constant:** same-row modelling-scale MAE change -0.7% (45 origins).
- **30-day CAGR versus Constant:** same-row modelling-scale MAE change -4.7% (24 origins).
- **30-day K-ratio versus Constant:** same-row modelling-scale MAE change -2.0% (24 origins).
- **30-day Sharpe versus Constant:** same-row modelling-scale MAE change -1.2% (24 origins).
- **7-day CAGR versus Zero return:** same-row modelling-scale MAE change +17.9% (45 origins).
- **30-day CAGR versus Zero return:** same-row modelling-scale MAE change +25.3% (24 origins).
- **7-day CAGR versus Persistence:** same-row modelling-scale MAE change -21.0% (45 origins).
- **7-day K-ratio versus Persistence:** same-row modelling-scale MAE change -22.0% (45 origins).
- **7-day Sharpe versus Persistence:** same-row modelling-scale MAE change -26.1% (45 origins).
- **30-day CAGR versus Persistence:** same-row modelling-scale MAE change -16.3% (24 origins).
- **30-day K-ratio versus Persistence:** same-row modelling-scale MAE change -21.2% (24 origins).
- **30-day Sharpe versus Persistence:** same-row modelling-scale MAE change -22.5% (24 origins).
- **7-day CAGR versus Quality/age:** same-row modelling-scale MAE change +5.2% (45 origins).
- **7-day K-ratio versus Quality/age:** same-row modelling-scale MAE change -0.9% (45 origins).
- **7-day Sharpe versus Quality/age:** same-row modelling-scale MAE change -0.5% (45 origins).
- **30-day CAGR versus Quality/age:** same-row modelling-scale MAE change +4.0% (24 origins).
- **30-day K-ratio versus Quality/age:** same-row modelling-scale MAE change -1.0% (24 origins).
- **30-day Sharpe versus Quality/age:** same-row modelling-scale MAE change +0.2% (24 origins).
- **7-day CAGR, original versus amended:** same-row MSE 1.676e+01 → 2.271e-01; IC 0.048 → 0.031.
- **7-day K-ratio, original versus amended:** same-row MSE 3.513e+01 → 1.119e+00; IC 0.127 → 0.145.
- **7-day Sharpe, original versus amended:** same-row MSE 2.038e+03 → 7.610e+01; IC 0.120 → 0.132.
- **30-day CAGR, original versus amended:** same-row MSE 8.534e+02 → 1.207e+00; IC 0.113 → 0.065.
- **30-day K-ratio, original versus amended:** same-row MSE 2.540e+01 → 1.053e+00; IC 0.177 → 0.171.
- **30-day Sharpe, original versus amended:** same-row MSE 7.720e+02 → 1.620e+01; IC 0.148 → 0.137.
- **7-day CAGR, amended prediction range:** [-4.810e-01, 1.376e-01]; output bound applied to 0.0% of forecasts.
- **7-day K-ratio, amended prediction range:** [-3.413e+00, 4.703e+00]; output bound applied to 0.0% of forecasts.
- **7-day Sharpe, amended prediction range:** [-4.626e+00, 5.541e+00]; output bound applied to 0.0% of forecasts.
- **30-day CAGR, amended prediction range:** [-1.248e+00, 5.468e-01]; output bound applied to 0.0% of forecasts.
- **30-day K-ratio, amended prediction range:** [-3.236e+00, 3.625e+00]; output bound applied to 0.0% of forecasts.
- **30-day Sharpe, amended prediction range:** [-2.775e+00, 4.039e+00]; output bound applied to 0.0% of forecasts.
- **Current-policy gate, 7-day CAGR:** paired K IC delta +0.004; 45 defined origins. Membership is caveated, not historically certified.
- **Current-policy gate, 7-day K-ratio:** paired K IC delta +0.017; 45 defined origins. Membership is caveated, not historically certified.
- **Current-policy gate, 7-day Sharpe:** paired K IC delta +0.018; 45 defined origins. Membership is caveated, not historically certified.
- **Current-policy gate, 30-day CAGR:** paired K IC delta +0.004; 24 defined origins. Membership is caveated, not historically certified.
- **Current-policy gate, 30-day K-ratio:** paired K IC delta +0.027; 24 defined origins. Membership is caveated, not historically certified.
- **Current-policy gate, 30-day Sharpe:** paired K IC delta +0.028; 24 defined origins. Membership is caveated, not historically certified.

## Matched lookback and sampling evidence

- **30d K-ratio → 30-day CAGR:** common-row IC 0.036; 62 defined origins and 15,618 rows, identical within this lookback comparison.
- **60d K-ratio → 30-day CAGR:** common-row IC 0.036; 62 defined origins and 15,618 rows, identical within this lookback comparison.
- **90d K-ratio → 30-day CAGR:** common-row IC 0.034; 62 defined origins and 15,618 rows, identical within this lookback comparison.
- **30d K-ratio → 30-day Sharpe:** common-row IC 0.085; 62 defined origins and 14,558 rows, identical within this lookback comparison.
- **60d K-ratio → 30-day Sharpe:** common-row IC 0.077; 62 defined origins and 14,558 rows, identical within this lookback comparison.
- **90d K-ratio → 30-day Sharpe:** common-row IC 0.077; 62 defined origins and 14,558 rows, identical within this lookback comparison.
- **30d K-ratio → 30-day K-ratio:** common-row IC 0.100; 62 defined origins and 14,764 rows, identical within this lookback comparison.
- **60d K-ratio → 30-day K-ratio:** common-row IC 0.098; 62 defined origins and 14,764 rows, identical within this lookback comparison.
- **90d K-ratio → 30-day K-ratio:** common-row IC 0.095; 62 defined origins and 14,764 rows, identical within this lookback comparison.
- **Snapshot conditioning:** 101 of 615 already archived addresses are outside the selected universe at 2026-10-01; this is a conditional study, not a complete historical-vault evaluation.

## Method and robustness

All continuous model inputs use training-only median-absolute asinh scales and explicit training-range/±5z bounds. CAGR inputs use exact lookback log returns. Sharpe fits a fixed scaled pseudo-Huber objective; K fits fold-scaled asinh targets. Level predictions use training 0.5%–99.5% target bounds before inverse transformation; labels and calculation tails remain untrimmed. Baselines are unbounded. Ranking companions have IC only, not level error.

Complete-case uses the fixed 30/60/90-day inventory, while partial history is measured over the supported ≤180-day inventory. Archive age is not inception. Missing=True is mechanical support for usable shorter inputs; same-row cohort errors separately assess usefulness. Zero-fill keeps shared indicators and is not a legacy selector replay.

The low-activity sensitivity requires max(4, ceil(window/2)) non-zero returns for Sharpe/K windows. Actual unchanged marks are valid primary observations. Discrete Sharpe/K stripes can reflect inactivity or precision; they do not prove stale prices. Activity sensitivity predictions use historical information only; realised future activity defines label validity afterwards, not forecast or entry eligibility. Calendar mark coverage and attrition are reported without inventing payouts.

Cadence phases, one-day delay, source-filled feature prices, quarterly stability, matched lookbacks/weekly sampling, calendar dependence, leave-vault/leave-block checks and explicit missing-outcome scenarios are exploratory. Bands do not eliminate dependence; the measured number of usable calendar blocks determines horizon support.

Current snapshot identities are not a certified historical listing. Zero assets/zero supply marks do not establish −100% investor loss. Inception, historical universe completeness and actual receipt/publication clocks remain unverified; no prospective collection pipeline is claimed. No strategy performance or deployment decision follows.

## Reproducibility

[Executed notebook](09-research-k-ratio-feature-forecasts.ipynb) · [Amendment](09-k-ratio-feature-forecast-amendment.md) · [Original implementation review](09-k-ratio-feature-forecast-implementation-review.md). Original code/notebook/headline outputs are preserved in the ignored `09-before-robust-amendment` namespace; current results and folds are under `09`.
