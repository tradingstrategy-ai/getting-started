# Experiment 09 — feedback resolution and longer K verdict

> **10 October 2026 amendment:** the user requested sparse-data support for all metric families. The complete actual-daily-observation requirement below is superseded by causal calendar-day forward filling, with actual observation masks retained and future labels censored after the last actual vault mark/archive end. See [current summary](summary.md) and [sparse-data audit](sparse-nav-rerun-2026-10-10.md).


## Current run

Updated and rerun [notebook 09](09-research-k-ratio-feature-forecasts.ipynb) in place, including 360-day (one-year) and max (full recorded-history) K alongside 30/60/90/180 days. All 19 code cells completed with no saved errors or stream outputs. The archive hash is unchanged. The previous corrected four-window run is preserved under `09-before-long-k`; the original pre-review run remains under `09-before-robust-amendment`.

Default period: **2026-01-01 → 2026-10-05, end exclusive, UTC**. Forecast every four days, refit monthly with strictly matured labels, and retain missing=True. All-history windows stop at T−1 and require every actual daily NAV from the first positive recorded mark. Recorded history is not certified inception.

## Updated measured findings

Adding six K inputs (30/60/90/180/360 days and max recorded history) improves primary mean rank IC in **2 of 6** supported target/horizon comparisons. This is a measured result of fixed amended models on previously researched history, not a general claim about K or an untouched holdout.

- **7-day CAGR:** old/new rank IC 0.041/0.038; delta -0.003; modelling-scale MAE change +0.2%; 38 origins, 21 complete blocks. Exploratory block band [-0.011, +0.005].
- **7-day K-ratio:** old/new rank IC 0.147/0.152; delta +0.005; modelling-scale MAE change -0.1%; 38 origins, 21 complete blocks. Exploratory block band [-0.013, +0.016].
- **7-day Sharpe:** old/new rank IC 0.139/0.141; delta +0.001; modelling-scale MAE change -0.0%; 38 origins, 21 complete blocks. Exploratory block band [-0.013, +0.012].
- **30-day CAGR:** old/new rank IC 0.093/0.086; delta -0.007; modelling-scale MAE change +0.2%; 24 origins, 3 complete blocks. Too few blocks for an uncertainty band.
- **30-day K-ratio:** old/new rank IC 0.197/0.189; delta -0.008; modelling-scale MAE change +0.1%; 24 origins, 3 complete blocks. Too few blocks for an uncertainty band.
- **30-day Sharpe:** old/new rank IC 0.165/0.155; delta -0.010; modelling-scale MAE change +0.2%; 24 origins, 3 complete blocks. Too few blocks for an uncertainty band.
- **90 days:** no supported paired forecast comparison. Illustrative forecasts and descriptive feature relationships do not establish model skill.

## One-year and all-history amendment

One year follows the existing 360-day convention. Max uses every calendar-day NAV from the first actual positive mark through T−1, with at least three fitted marks and no fill or compressed gaps. Recorded history is not certified inception. Short-window ablations keep shared missingness controls fixed, so the longer K values can be assessed separately from history availability. The previous four-window run is archived under `09-before-long-k`.

- **360d K-ratio:** 0/24,605 observed-anchor rows have a finite input (0.0%).
- **max K-ratio:** 6,707/24,605 observed-anchor rows have a finite input (27.3%).
- **Available max durations:** 2–257 days, median 93 days; 851 of 6,707 finite max rows span at least 180 days. Max is not necessarily a longer input for young vaults. No complete year inputs exist in this generation, so this rerun cannot measure a true one-year K effect.
- **Existing + K, 7-day CAGR:** versus four-window K, same-row rank IC 0.0387 → 0.0375; delta -0.0011; MAE change +0.1%; 38 origins, 21 blocks.
- **Existing + short K + max, 7-day CAGR:** versus four-window K, same-row rank IC 0.0387 → 0.0375; delta -0.0011; MAE change +0.1%; 38 origins, 21 blocks.
- **Existing + short K + year, 7-day CAGR:** versus four-window K, same-row rank IC 0.0387 → 0.0387; delta +0.0000; MAE change +0.0%; 38 origins, 21 blocks.
- **Existing + K, 7-day K-ratio:** versus four-window K, same-row rank IC 0.1504 → 0.1516; delta +0.0011; MAE change -0.1%; 38 origins, 21 blocks.
- **Existing + short K + max, 7-day K-ratio:** versus four-window K, same-row rank IC 0.1504 → 0.1516; delta +0.0011; MAE change -0.1%; 38 origins, 21 blocks.
- **Existing + short K + year, 7-day K-ratio:** versus four-window K, same-row rank IC 0.1504 → 0.1504; delta +0.0000; MAE change +0.0%; 38 origins, 21 blocks.
- **Existing + K, 7-day Sharpe:** versus four-window K, same-row rank IC 0.1393 → 0.1406; delta +0.0013; MAE change -0.1%; 38 origins, 21 blocks.
- **Existing + short K + max, 7-day Sharpe:** versus four-window K, same-row rank IC 0.1393 → 0.1406; delta +0.0013; MAE change -0.1%; 38 origins, 21 blocks.
- **Existing + short K + year, 7-day Sharpe:** versus four-window K, same-row rank IC 0.1393 → 0.1393; delta +0.0000; MAE change +0.0%; 38 origins, 21 blocks.
- **Existing + K, 30-day CAGR:** versus four-window K, same-row rank IC 0.0862 → 0.0857; delta -0.0005; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + short K + max, 30-day CAGR:** versus four-window K, same-row rank IC 0.0862 → 0.0857; delta -0.0005; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + short K + year, 30-day CAGR:** versus four-window K, same-row rank IC 0.0862 → 0.0862; delta +0.0000; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + K, 30-day K-ratio:** versus four-window K, same-row rank IC 0.1877 → 0.1893; delta +0.0016; MAE change -0.0%; 24 origins, 3 blocks.
- **Existing + short K + max, 30-day K-ratio:** versus four-window K, same-row rank IC 0.1877 → 0.1893; delta +0.0016; MAE change -0.0%; 24 origins, 3 blocks.
- **Existing + short K + year, 30-day K-ratio:** versus four-window K, same-row rank IC 0.1877 → 0.1877; delta +0.0000; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + K, 30-day Sharpe:** versus four-window K, same-row rank IC 0.1554 → 0.1551; delta -0.0003; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + short K + max, 30-day Sharpe:** versus four-window K, same-row rank IC 0.1554 → 0.1551; delta -0.0003; MAE change +0.0%; 24 origins, 3 blocks.
- **Existing + short K + year, 30-day Sharpe:** versus four-window K, same-row rank IC 0.1554 → 0.1554; delta +0.0000; MAE change +0.0%; 24 origins, 3 blocks.



The short-K ablation shares the new all-history missingness controls with the longer-K arm. Its IC differs slightly from the previous run because of these shared controls; the comparison does not imply a data change. Max improves K-to-K ranking slightly and seven-day Sharpe slightly; CAGR ranking decreases at both supported horizons. The seven-day incremental bands include zero. Thirty-day comparisons have only three blocks and 90-day models remain unsupported. No robust profitable-growth improvement is established.

## Review feedback disposition

Each row distinguishes an implemented correction from an unresolved data limitation.

| Feedback | Disposition |
| --- | --- |
| B1: raw-input extrapolation and inverse-K blow-up | Exact log-return CAGR inputs; continuous training-only asinh scales; training-range/±5z bounds; target-range safeguards; full clipping/range diagnostics; original-versus-new same-row comparisons. Corrected. |
| H1: one-tick and near-flat Sharpe/K labels | Fixed activity refits plus precision/near-linearity cohort sensitivities, counts and attrition. Actual unchanged NAVs remain valid primary observations. Future activity only defines sensitivity-label validity after forecasting; it never controls entry or forecast availability. Staleness is not assumed. |
| H2: overly strong anti-K verdict | All primary and sensitivity conclusions generated from results; block bands and sign changes disclosed. No equivalence bound or general feature-uselessness claim. |
| H3: vacuous partial/complete history | Partial inventory is ≤180 days; complete-case is fixed 30/60/90 days; same-row young-cohort baseline errors shown. True inception remains unavailable: metadata start_date equals first_updated_at for all 616 Hyperliquid records and deployment dates are absent. |
| M1: stale hard-coded findings | Numerical findings and verdict counts generated from saved tables. Builder imports matching-run headline findings only with matching model/data source hashes. |
| M2: objective mismatch | Fixed scaled pseudo-Huber Sharpe loss; separate within-origin input/target rank companions scored by IC, without meaningless level errors. |
| M3: persistence transform and indicators | All continuous inputs, including matched K persistence, transformed explicitly; separate persistence missingness indicator; binary masks are not asinh-transformed. |
| M4: investable/gate comparison missing | Same-row IC, MAE, MSE and support for gate and deposit-feasible cohorts. Current policy and unknown clocks are disclosed. |
| M5: universe and zero NAV bias | Archive audit finds 101/615 previously observed addresses outside the selected snapshot by October. Zero-NAV audit finds 35 marks for one empty zero-assets/zero-supply vault. No investor loss or historical-listing completeness is fabricated. Conditioning remains a limitation. |
| M6: attrition poorly characterised | Activity, daily-history gaps, permission-clock, current closure/leader-disabled and disappearance cohorts; calendar-wide mark coverage; explicit missing-outcome scenarios. Current closure is retrospective metadata, not point-in-time truth. |
| M7: missing=False semantics | Explicitly labelled zero-fill with indicators and earlier ratio floors. It is an adapter sensitivity, not a legacy selector replay. |
| M8: calendar/lookback confounding | Matched origin/vault lookback and daily/weekly tables and maps. Unmatched plots now disclose differing populations. |
| L1: tautological or literal audit checks | Assumed clock convention labelled as such; right-censored and incomplete-path targets checked for fabricated values. The assumed label clock is not claimed to be a receipt clock. |
| L2/L3: extreme/error table and scatter clarity | Scientific notation for large tails; horizon log-return CAGR plots on linear axes; numerical range diagnostics beyond display cropping. Each image has its own heading, description and period title. |
| L4/L5: heatmap support and weekly alignment | Correlation maps include paired-row or origin counts; weekly actual spans 28/56/84/175 days are stated. |
| L6: numerical degeneracy | Precision/near-linearity sensitivity screens with explicit assumed thresholds and counts. The primary K convention is preserved; the screen is not claimed to be a certified data-quality rule. |
| L7: missing diagnostics | Individual-feature quarterly stability, forward outcome quantiles, unfloored Calmar tails and EWMA volatility decomposition displayed. Constant-model calibration omitted. |
| L8: dependence | Exploratory horizon/double-horizon blocks and non-overlapping-origin diagnostics retained; no formal multiple-testing claims. |
| L9: native rendering | All 11 notebooks validate; static notebook rendering and embedded PNGs checked. Native VS Code rendering has not been independently checked. |
| Prospective confirmation | Amended specification and source hashes frozen; required future observation/receipt schema recorded. The notebook does not implement a new data-collection pipeline or certify unavailable historical publication clocks. |


## Current execution and rendering checks

The main notebook and all 11 catalogue notebooks validate. Every embedded main PNG decodes. The new longer-K maps, coverage/missingness maps and representative all-history scatters were inspected individually; no collations were made. Complete numerical findings are generated from saved result tables. Native VS Code rendering has not been independently checked.

See [generated findings](09-k-ratio-feature-forecast-findings.md) and [the amendment](09-k-ratio-feature-forecast-amendment.md) for the current specification and measured support. Existing review corrections and unresolved data limitations remain as described above.
