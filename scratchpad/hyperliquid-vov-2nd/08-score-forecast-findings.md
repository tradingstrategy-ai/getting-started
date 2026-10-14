# Experiment 08: scores, forecasts and admission floors

[Executed notebook](08-research-score-forecast-thresholds.ipynb). Primary period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**. Updated 10 October 2026; in-place sparse-data rerun.

## Key new insights

- Recomputed all 139 score recipes at 7/30/90-day horizons. Primary targets use the latest actual positive NAV carried forward on calendar days; observation counts remain separate. No leading backfill or labels beyond each vault’s last actual mark/archive end. The source score and portfolio machinery is unchanged.
- Primary 30-day return rank IC ranges from **0.087 to 0.089**; Sharpe rank IC ranges from **0.129 to 0.137** across the three frozen methods. Inspect the intervals and origin counts below before interpreting these point estimates.
- Of 54 supported linear/isotonic method–horizon–target comparisons, **35** have lower equal-date MSE than the same-row historical constant. This does not by itself establish forecast or portfolio skill.
- The absolute floor is active in **27/30** 2026 method-months and rejects **0** proposed entries across the replay treatments.
- The highest non-random replay is **focal_four, 6 positions, none / slot_to_cash**: CAGR **51.77%**, Sharpe **2.30**, drawdown **-6.35%**. This is a descriptive maximum on previously researched history.

## Focal ranking evidence — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Equal-date cross-sectional Spearman IC measures score discrimination among eligible candidates. CAGR and horizon-return ranks coincide at a fixed horizon. Future paths can contain carried marks, which may alter risk metrics.

| method                                |   lookahead_days | outcome   |   mean_ic |     ic_lower |    ic_upper |   supported_origins |   distinct_vaults |   paired_rows | inference_status                       |
|:--------------------------------------|-----------------:|:----------|----------:|-------------:|------------:|--------------------:|------------------:|--------------:|:---------------------------------------|
| Blend 46d (two inputs)                |                7 | cagr      | 0.0500281 |   0.0083368  |   0.0957821 |                  68 |               126 |          3141 | conditional_exploratory_block_interval |
| Blend 46d (two inputs)                |                7 | sharpe    | 0.0655002 |   0.0157641  |   0.109025  |                  68 |               123 |          2849 | conditional_exploratory_block_interval |
| Blend 46d (two inputs)                |               30 | cagr      | 0.0867487 |  -0.00755728 |   0.203788  |                  62 |               113 |          2728 | conditional_exploratory_block_interval |
| Blend 46d (two inputs)                |               30 | sharpe    | 0.134822  |   0.0251177  |   0.262159  |                  62 |               110 |          2626 | conditional_exploratory_block_interval |
| Blend 46d (two inputs)                |               90 | cagr      | 0.21905   | nan          | nan         |                  47 |                87 |          1798 | short_90_day_descriptive_only          |
| Blend 46d (two inputs)                |               90 | sharpe    | 0.241781  | nan          | nan         |                  47 |                87 |          1788 | short_90_day_descriptive_only          |
| Four inputs (180d CAGR + 30d Sortino) |                7 | cagr      | 0.0578955 |   0.0107117  |   0.110301  |                  68 |               126 |          3055 | conditional_exploratory_block_interval |
| Four inputs (180d CAGR + 30d Sortino) |                7 | sharpe    | 0.0806739 |   0.0311817  |   0.122272  |                  68 |               123 |          2813 | conditional_exploratory_block_interval |
| Four inputs (180d CAGR + 30d Sortino) |               30 | cagr      | 0.0889767 |  -0.00495454 |   0.198315  |                  62 |               113 |          2657 | conditional_exploratory_block_interval |
| Four inputs (180d CAGR + 30d Sortino) |               30 | sharpe    | 0.1366    |   0.0245559  |   0.251061  |                  62 |               110 |          2582 | conditional_exploratory_block_interval |
| Four inputs (180d CAGR + 30d Sortino) |               90 | cagr      | 0.170077  | nan          | nan         |                  47 |                85 |          1746 | short_90_day_descriptive_only          |
| Four inputs (180d CAGR + 30d Sortino) |               90 | sharpe    | 0.199754  | nan          | nan         |                  47 |                85 |          1740 | short_90_day_descriptive_only          |
| v11 (legacy 45d)                      |                7 | cagr      | 0.050177  |   0.0068578  |   0.0961477 |                  68 |               126 |          3137 | conditional_exploratory_block_interval |
| v11 (legacy 45d)                      |                7 | sharpe    | 0.0629588 |   0.0127207  |   0.10733   |                  68 |               123 |          2848 | conditional_exploratory_block_interval |
| v11 (legacy 45d)                      |               30 | cagr      | 0.0876523 |  -0.0068962  |   0.200393  |                  62 |               113 |          2726 | conditional_exploratory_block_interval |
| v11 (legacy 45d)                      |               30 | sharpe    | 0.128569  |   0.0192539  |   0.246071  |                  62 |               110 |          2626 | conditional_exploratory_block_interval |
| v11 (legacy 45d)                      |               90 | cagr      | 0.183998  | nan          | nan         |                  47 |                87 |          1796 | short_90_day_descriptive_only          |
| v11 (legacy 45d)                      |               90 | sharpe    | 0.210543  | nan          | nan         |                  47 |                87 |          1787 | short_90_day_descriptive_only          |

## Forecast calibration against constants — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Negative MSE change is better. Monthly training uses only matured labels and requires at least 20 training origins and ten vaults for each outcome. Dates overlap; reported rows are not independent samples.

| method_id   |   lookahead_days | outcome    | model    |   origin_count |   equal_date_mse |   constant_mse |   MSE change vs constant |
|:------------|-----------------:|:-----------|:---------|---------------:|-----------------:|---------------:|-------------------------:|
| blend_46d   |                7 | log_return | isotonic |             68 |        0.0144769 |      0.0143402 |              0.00953698  |
| blend_46d   |                7 | log_return | linear   |             68 |        0.0143414 |      0.0143402 |              8.30564e-05 |
| blend_46d   |                7 | loss       | isotonic |             68 |        0.263124  |      0.26357   |             -0.00169238  |
| blend_46d   |                7 | loss       | linear   |             68 |        0.263034  |      0.26357   |             -0.00203552  |
| blend_46d   |                7 | sharpe     | isotonic |             68 |       69.0932    |     69.0239    |              0.00100365  |
| blend_46d   |                7 | sharpe     | linear   |             68 |       69.0725    |     69.0239    |              0.000704811 |
| blend_46d   |               30 | log_return | isotonic |             62 |        0.093952  |      0.0937586 |              0.00206276  |
| blend_46d   |               30 | log_return | linear   |             62 |        0.0931171 |      0.0937586 |             -0.00684241  |
| blend_46d   |               30 | loss       | isotonic |             62 |        0.249488  |      0.251383  |             -0.00753804  |
| blend_46d   |               30 | loss       | linear   |             62 |        0.255574  |      0.251383  |              0.0166713   |
| blend_46d   |               30 | sharpe     | isotonic |             62 |       15.8624    |     16.1304    |             -0.016618    |
| blend_46d   |               30 | sharpe     | linear   |             62 |       16.1174    |     16.1304    |             -0.000806394 |
| blend_46d   |               90 | log_return | isotonic |             47 |        0.228522  |      0.244711  |             -0.0661563   |
| blend_46d   |               90 | log_return | linear   |             47 |        0.228888  |      0.244711  |             -0.0646609   |
| blend_46d   |               90 | loss       | isotonic |             47 |        0.252719  |      0.272514  |             -0.072639    |
| blend_46d   |               90 | loss       | linear   |             47 |        0.252443  |      0.272514  |             -0.0736512   |
| blend_46d   |               90 | sharpe     | isotonic |             47 |        4.5611    |      4.81234   |             -0.0522082   |
| blend_46d   |               90 | sharpe     | linear   |             47 |        4.60864   |      4.81234   |             -0.0423299   |
| focal_four  |                7 | log_return | isotonic |             68 |        0.0148245 |      0.0147069 |              0.00799583  |
| focal_four  |                7 | log_return | linear   |             68 |        0.0147148 |      0.0147069 |              0.000539771 |
| focal_four  |                7 | loss       | isotonic |             68 |        0.266946  |      0.266141  |              0.00302651  |
| focal_four  |                7 | loss       | linear   |             68 |        0.265735  |      0.266141  |             -0.00152332  |
| focal_four  |                7 | sharpe     | isotonic |             68 |       69.4848    |     69.1622    |              0.0046642   |
| focal_four  |                7 | sharpe     | linear   |             68 |       69.1939    |     69.1622    |              0.000457987 |
| focal_four  |               30 | log_return | isotonic |             62 |        0.09841   |      0.0977624 |              0.00662512  |
| focal_four  |               30 | log_return | linear   |             62 |        0.097285  |      0.0977624 |             -0.00488277  |
| focal_four  |               30 | loss       | isotonic |             62 |        0.250594  |      0.253915  |             -0.0130791   |
| focal_four  |               30 | loss       | linear   |             62 |        0.254386  |      0.253915  |              0.00185739  |
| focal_four  |               30 | sharpe     | isotonic |             62 |       16.0067    |     16.345     |             -0.0206951   |
| focal_four  |               30 | sharpe     | linear   |             62 |       16.1681    |     16.345     |             -0.010822    |
| focal_four  |               90 | log_return | isotonic |             47 |        0.239052  |      0.248065  |             -0.0363329   |
| focal_four  |               90 | log_return | linear   |             47 |        0.237552  |      0.248065  |             -0.0423784   |
| focal_four  |               90 | loss       | isotonic |             47 |        0.27028   |      0.27706   |             -0.0244716   |
| focal_four  |               90 | loss       | linear   |             47 |        0.264024  |      0.27706   |             -0.047051    |
| focal_four  |               90 | sharpe     | isotonic |             47 |        4.60453   |      4.76882   |             -0.0344494   |
| focal_four  |               90 | sharpe     | linear   |             47 |        4.63317   |      4.76882   |             -0.0284455   |
| v11         |                7 | log_return | isotonic |             68 |        0.0144079 |      0.0143469 |              0.00425014  |
| v11         |                7 | log_return | linear   |             68 |        0.0143475 |      0.0143469 |              4.09503e-05 |
| v11         |                7 | loss       | isotonic |             68 |        0.263497  |      0.263835  |             -0.00128171  |
| v11         |                7 | loss       | linear   |             68 |        0.263818  |      0.263835  |             -6.48942e-05 |
| v11         |                7 | sharpe     | isotonic |             68 |       69.2412    |     69.0333    |              0.00301183  |
| v11         |                7 | sharpe     | linear   |             68 |       69.1731    |     69.0333    |              0.00202526  |
| v11         |               30 | log_return | isotonic |             62 |        0.0937169 |      0.0937766 |             -0.000636555 |
| v11         |               30 | log_return | linear   |             62 |        0.0932456 |      0.0937766 |             -0.0056624   |
| v11         |               30 | loss       | isotonic |             62 |        0.249848  |      0.251463  |             -0.00642142  |
| v11         |               30 | loss       | linear   |             62 |        0.256064  |      0.251463  |              0.0182985   |
| v11         |               30 | sharpe     | isotonic |             62 |       15.8442    |     16.1338    |             -0.0179499   |
| v11         |               30 | sharpe     | linear   |             62 |       16.1871    |     16.1338    |              0.00329946  |
| v11         |               90 | log_return | isotonic |             47 |        0.22834   |      0.244238  |             -0.0650905   |
| v11         |               90 | log_return | linear   |             47 |        0.231283  |      0.244238  |             -0.0530417   |
| v11         |               90 | loss       | isotonic |             47 |        0.253406  |      0.27285   |             -0.0712635   |
| v11         |               90 | loss       | linear   |             47 |        0.257374  |      0.27285   |             -0.0567187   |
| v11         |               90 | sharpe     | isotonic |             47 |        4.54866   |      4.80778   |             -0.053896    |
| v11         |               90 | sharpe     | linear   |             47 |        4.66899   |      4.80778   |             -0.0288674   |

## Target coverage — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

The denominator includes all snapshot vaults and scheduled origins. Supported calendar paths can include carried NAV; undefined ratios and immature/terminal outcomes stay missing.

|   period |   lookahead_days |   scheduled_origins |   matured_origins | last_matured_origin   |   complete_pairs |   return_endpoint_pairs |   sharpe_finite_pairs |   endpoint_only_pairs |   framework_approximate_pairs |   vaults_with_complete_target |   complete_fraction_all_vault_origins |   administrative_censoring_fraction |   flat_target_fraction_complete |   low_variance_fraction_complete |
|---------:|-----------------:|--------------------:|------------------:|:----------------------|-----------------:|------------------------:|----------------------:|----------------------:|------------------------------:|------------------------------:|--------------------------------------:|------------------------------------:|--------------------------------:|---------------------------------:|
|     2026 |                7 |                  70 |                68 | 2026-09-26 00:00:00   |            26543 |                   26543 |                 19965 |                     0 |                         26543 |                           511 |                              0.737715 |                           0.0285714 |                       0.247824  |                         0.280903 |
|     2026 |               30 |                  70 |                62 | 2026-09-02 00:00:00   |            23514 |                   23514 |                 19639 |                     0 |                         23514 |                           493 |                              0.65353  |                           0.114286  |                       0.164795  |                         0.205962 |
|     2026 |               90 |                  70 |                47 | 2026-07-04 00:00:00   |            16416 |                   16416 |                 14947 |                     0 |                         16416 |                           451 |                              0.456253 |                           0.328571  |                       0.0894859 |                         0.131335 |

## Net portfolio rules — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Fresh $150,000 replays preserve guards, capacity, inverse variance, two-day trading and source-modelled redemption costs. Thresholds use recomputed matured labels; no-floor controls retain their original rules.

| Method     |   Positions | Threshold policy   | Treatment               | CAGR   |   Sharpe | Maximum drawdown   | Mean cash weight   |   Rejected entry proposals |
|:-----------|------------:|:-------------------|:------------------------|:-------|---------:|:-------------------|:-------------------|---------------------------:|
| v11        |           6 | none               | slot_to_cash            | 41.20% |  1.95959 | -6.40%             | 8.83%              |                          0 |
| v11        |           7 | none               | slot_to_cash            | 33.47% |  1.74631 | -5.11%             | 5.09%              |                          0 |
| focal_four |           6 | none               | slot_to_cash            | 51.77% |  2.30347 | -6.35%             | 10.18%             |                          0 |
| focal_four |           7 | none               | slot_to_cash            | 30.85% |  1.58224 | -6.42%             | 6.21%              |                          0 |
| focal_four |           7 | percentile_75      | slot_to_cash            | 31.39% |  1.60489 | -6.44%             | 6.26%              |                          1 |
| focal_four |           7 | percentile_75      | renormalise_within_caps | 31.35% |  1.60279 | -6.43%             | 6.20%              |                          1 |
| blend_46d  |           6 | none               | slot_to_cash            | 41.38% |  2.11861 | -4.85%             | 7.43%              |                          0 |
| blend_46d  |           7 | none               | slot_to_cash            | 47.93% |  2.45871 | -4.71%             | 5.03%              |                          0 |

## Interpretation and next research

Compare changed entry proposals, cash and net portfolio results with each method’s own no-floor control. A score relationship or lower forecast error is insufficient to justify an admission floor. Freeze promising rules and collect later observations before declaring superiority.

Forward filling removes the incorrect complete-observation requirement. It assumes NAV is held at the last reported level between observations; reported returns can arrive as jumps. Inspect actual coverage, observation age, low activity and dense-observation sensitivity alongside the primary results.

## Robustness and reproducibility

- Four-day origins overlap. Confidence procedures use date baskets; 90-day estimates remain descriptive with too few independent windows. Both periods were previously used for research.
- The 514-vault inventory and current guards are snapshot policy assumptions. Archived write times are not receipt clocks. No new input archive was fetched.
- Raw-price targets retain positive tiny collapse prices, while framework guarded prices remain a separate sensitivity. Actual observations and carried marks are never conflated.
- Missing scores, component-imputed scores and finite zero scores stay distinct. Fees retain the v11 model; gross vault outcomes are separate from executable portfolio PnL.
- Independent target recomputation, source-score replication, equity/trade controls and chart manifests are retained under ignored artefacts. Pre-fill notebook, code and results are in `08-before-sparse-fill`.
- Data fingerprint: `a624ef920a984624bc2f56d4de26d94afe3a84114a684dbd583750c5cf40a588`.
