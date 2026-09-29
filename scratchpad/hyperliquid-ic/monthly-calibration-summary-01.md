# Monthly stability calibration

Parent: [23-research-profitable-months.ipynb](23-research-profitable-months.ipynb), using its corrected single-fee accounting. Executed notebook: [24-research-monthly-calibration.ipynb](24-research-monthly-calibration.ipynb).

## Key new insights

0 of all 48 settings and 0 of the three shortlisted settings pass the predeclared training criteria. Non-qualifying settings are diagnostic runs, not endorsed leads.

All three shortlisted settings have at least six score-1 vaults on every diagnostic date. The bounded gain reward and perfect positive-month fraction saturate the score: loss penalties cannot reorder those vaults. Deterministic tie-breaking, deposit availability and incumbent holding rules then choose among them. These are not three independent confirmations of a preferred coefficient balance.

All three shortlisted equity curves are exactly identical in: hyper_ai, full, later. The experiment has not identified a uniquely useful penalty coefficient within this saturated region.

Every selected vault in all three shortlisted strategies has score exactly 1. This is confirmed from actual engine selection logs, not inferred from the calibration pool. The shortlisted loss penalties are inactive at the selection boundary because these winners have no recorded negative months in their chosen history.

For the first shortlisted setting, separately ranked later-period mature-history top groups average 1.8% over 60 days, versus -15.6% for young-history top groups. This motivates testing confidence in short histories; the cohort comparison does not isolate the provisional fallback or establish a causal age effect, and does not justify a long-history admission barrier.

Removing the leading contributor from the first shortlisted later-period run changes CAGR from -38.1% to -47.3%, and Sharpe from -1.57 to -2.47. This full re-simulation does not reveal a robust profitable portfolio.

No shortlisted cold-start later-period portfolio reaches 20% CAGR. There is no qualifying strategy to promote from this experiment.

## Experiment design

Score = p^alpha × min(median_positive_month_return/tau, 1) × exp(−penalty × negative_month_fraction − severity × downside/tau). Downside is the sum of absolute negative monthly returns divided by available month count. Zero months contribute to the denominator. The 48 settings use alpha {1,2}, penalty {0,1,2}, severity {0,1}, tau {1%,2%}, and history {3,6 months}. No score parameter is chosen from portfolio backtest outcomes.

Completed calendar months only; missing inception history is omitted. With no complete month, unannualised observed partial return is used after two observations at least one day apart. Weekly observations work. This is a monthly consistency score, not an intramonth smoothness score.

Daily ranking diagnostics use historical TVL ≥ $7,500 and positive trailing 14-day return, falling back to available inception history for young vaults. This common gate is independent of the monthly score. Rankings are formed BEFORE future labels are masked. The top fifth is compared with the remaining vaults, ties resolved deterministically by address. Execution additionally checks the inherited deposit availability/capacity rules; the diagnostic pool is not an exact executed-portfolio reconstruction.

Outcomes: future 30/60-day return, positive-return frequency, observed-path maximum drawdown, negative endpoint return, and fraction of negative non-overlapping 30-day blocks (monthly proxies, not calendar months). Endpoints use earlier marks with up to seven days of carry for sparse observations. Incomplete or missing future outcomes are not zero-filled; coverage is exported. Young (<90 days of observed history) and mature cohorts are separately reported. The five-labelled-vault threshold applies to cross-sectional statistics, not vault admission.

Training decision labels must fully mature by 1 April 2026. Later diagnostics start on 1 April; intervening overlapping labels are embargoed. Three settings are selected by training-only worst-horizon drawdown lift and the median lift of one-parameter neighbours. Qualification requires positive top-group return, nonnegative positive-return lift and positive drawdown lift at BOTH horizons, plus positive neighbourhood median drawdown lift. If fewer than three qualify, remaining backtests are clearly diagnostic. No minimum-history admission requirement is introduced.

Matched portfolio arms all use six positions, equal weighting, 33% portfolio cap, 33% historical vault-TVL capacity, the same young-compatible recent-return gate, cash policy, fees and trade thresholds. Only ranking varies: original CAGR/Sortino versus the three shortlisted monthly scores. Zero-score candidates are not given an extra exclusion; the common recent-return gate handles eligibility. Equal weighting avoids the inherited 90-day inverse-volatility sizing barrier. These fixed limits isolate ranking; they are not a proposed production allocation policy. Separate original inverse-variance anchors reproduce corrected NB23 exactly in both native periods.

Three portfolio periods: Hyper-ai, full-history and a cold start on 1 April through 8 September. The first two are historical diagnostics because the shortlist was trained on part of those dates. The cold-start later run uses no pre-April holdings. All dates have been researched previously: no untouched holdout or statistical discovery claim is made.

## Summary of results

### Training-only shortlist

| config   |   horizons |   min_return |   min_positive_lift |   worst_dd_lift |   min_dates |   alpha |   penalty |   severity |   tau |   lookback |   neighbour_median_dd_lift | qualifies   | status                                    |
|:---------|-----------:|-------------:|--------------------:|----------------:|------------:|--------:|----------:|-----------:|------:|-----------:|---------------------------:|:------------|:------------------------------------------|
| C36      |          2 |     -0.05494 |             0.08068 |         0.05794 |         141 |       2 |         1 |          1 |  0.01 |          3 |                    0.05794 | False       | diagnostic only: failed training criteria |
| C12      |          2 |     -0.05494 |             0.08068 |         0.05794 |         141 |       1 |         1 |          1 |  0.01 |          3 |                    0.0579  | False       | diagnostic only: failed training criteria |
| C44      |          2 |     -0.05494 |             0.08068 |         0.05796 |         141 |       2 |         2 |          1 |  0.01 |          3 |                    0.05785 | False       | diagnostic only: failed training criteria |

### Score saturation

| config   | split   |   mean_saturated |   mean_saturated_fraction |   fraction_dates_at_least_six |
|:---------|:--------|-----------------:|--------------------------:|------------------------------:|
| C12      | train   |          17.5603 |                    0.3297 |                             1 |
| C12      | later   |          19.8323 |                    0.2114 |                             1 |
| C36      | train   |          17.5603 |                    0.3297 |                             1 |
| C36      | later   |          19.8323 |                    0.2114 |                             1 |
| C44      | train   |          17.5603 |                    0.3297 |                             1 |
| C44      | later   |          19.8323 |                    0.2114 |                             1 |

These diagnostic opportunity sets precede execution checks. Score ties are resolved by address in the ranking analysis and by pair id in the inherited engine. Neither tie-break is evidence of trading quality.

### Future-outcome evidence

| config   |   horizon | split   |   dates |   ic_return |   ic_drawdown |   top_ret |   lift_ret |   lift_dd |   lift_positive |   lift_negative_blocks |   top_coverage |   rest_coverage |
|:---------|----------:|:--------|--------:|------------:|--------------:|----------:|-----------:|----------:|----------------:|-----------------------:|---------------:|----------------:|
| C12      |        30 | later   |     132 |     0.01991 |       0.22057 |  -0.0431  |   -0.02073 |   0.00875 |         0.06577 |               -0.06152 |        0.99953 |         0.99864 |
| C12      |        30 | train   |     171 |     0.14544 |       0.26056 |  -0.02943 |    0.03852 |   0.05794 |         0.10092 |               -0.10268 |        0.99581 |         0.9376  |
| C12      |        60 | later   |     102 |     0.08616 |       0.16183 |  -0.06389 |   -0.01468 |  -0.01352 |         0.07674 |               -0.07174 |        0.99939 |         0.99824 |
| C12      |        60 | train   |     141 |     0.21875 |       0.26659 |  -0.05494 |    0.06025 |   0.07434 |         0.08068 |               -0.08995 |        0.99397 |         0.914   |
| C36      |        30 | later   |     132 |     0.02069 |       0.22222 |  -0.04303 |   -0.02064 |   0.00875 |         0.06637 |               -0.06212 |        0.99953 |         0.99864 |
| C36      |        30 | train   |     171 |     0.14483 |       0.26032 |  -0.02943 |    0.03852 |   0.05794 |         0.10092 |               -0.10268 |        0.99581 |         0.9376  |
| C36      |        60 | later   |     102 |     0.08845 |       0.16328 |  -0.06384 |   -0.01462 |  -0.01343 |         0.07893 |               -0.07211 |        0.99939 |         0.99824 |
| C36      |        60 | train   |     141 |     0.21829 |       0.26588 |  -0.05494 |    0.06025 |   0.07434 |         0.08068 |               -0.08995 |        0.99397 |         0.914   |
| C44      |        30 | later   |     132 |     0.02033 |       0.22116 |  -0.04305 |   -0.02067 |   0.00877 |         0.06637 |               -0.06212 |        0.99953 |         0.99864 |
| C44      |        30 | train   |     171 |     0.14453 |       0.25975 |  -0.02947 |    0.03846 |   0.05796 |         0.10092 |               -0.10268 |        0.99581 |         0.9376  |
| C44      |        60 | later   |     102 |     0.08823 |       0.1629  |  -0.06384 |   -0.01462 |  -0.01343 |         0.07893 |               -0.07211 |        0.99939 |         0.99824 |
| C44      |        60 | train   |     141 |     0.21796 |       0.26494 |  -0.05494 |    0.06025 |   0.07434 |         0.08068 |               -0.08995 |        0.99397 |         0.914   |

Daily labels overlap strongly; date counts are not independent sample counts. No p-values or annualised claims are inferred from these label averages. Values above are fractions, not percentages.

### Young versus mature observed histories

| cohort   |   horizon |   dates |   top_ret |   lift_dd |   lift_positive |   top_coverage |   rest_coverage |
|:---------|----------:|--------:|----------:|----------:|----------------:|---------------:|----------------:|
| all      |        30 |     132 |  -0.04303 |   0.00875 |         0.06637 |        0.99953 |         0.99864 |
| all      |        60 |     102 |  -0.06384 |  -0.01343 |         0.07893 |        0.99939 |         0.99824 |
| mature   |        30 |     132 |  -0.01557 |   0.03891 |         0.14029 |        1       |         1       |
| mature   |        60 |     102 |   0.01756 |   0.06103 |         0.24757 |        1       |         1       |
| young    |        30 |     110 |  -0.06327 |  -0.00664 |         0.03073 |        1       |         0.99545 |
| young    |        60 |     102 |  -0.15608 |  -0.05817 |        -0.01745 |        1       |         0.99509 |

These are independently ranked cohorts for the first training-shortlisted setting. They are descriptive comparisons, not an age treatment or justification for excluding young vaults. Different date counts are shown. Available history below one completed month can receive a perfect score after a small gain, despite much less evidence of persistence.

### One-parameter changes across the grid

| parameter   | change       | split   |   horizon |   pairs |   delta_top_ret |   delta_lift_positive |   delta_lift_dd |   delta_ic_return |   delta_ic_drawdown |
|:------------|:-------------|:--------|----------:|--------:|----------------:|----------------------:|----------------:|------------------:|--------------------:|
| alpha       | 1 -> 2       | later   |        30 |      24 |         0.00116 |               0.00929 |         0.00333 |           0.00376 |             0.01822 |
| alpha       | 1 -> 2       | later   |        60 |      24 |         0.0007  |               0.00901 |         0.00347 |           0.00361 |             0.01506 |
| penalty     | 0 -> 1       | later   |        30 |      16 |         0.00104 |               0.00901 |         0.00294 |           0.00173 |             0.01599 |
| penalty     | 0 -> 1       | later   |        60 |      16 |         0.0007  |               0.0095  |         0.00383 |           0.00316 |             0.01496 |
| penalty     | 1 -> 2       | later   |        30 |      16 |         0.00048 |               0.00635 |         0.00196 |           0.00084 |             0.01008 |
| penalty     | 1 -> 2       | later   |        60 |      16 |         0.00077 |               0.00748 |         0.00284 |           0.0021  |             0.00982 |
| severity    | 0 -> 1       | later   |        30 |      24 |         0.00457 |               0.01268 |         0.01414 |           0.01501 |             0.16157 |
| severity    | 0 -> 1       | later   |        60 |      24 |        -0.00378 |               0.00948 |         0.00756 |           0.02368 |             0.14183 |
| tau         | 0.02 -> 0.01 | later   |        30 |      24 |         0.00394 |               0.03045 |         0.01382 |           0.00473 |             0.05733 |
| tau         | 0.02 -> 0.01 | later   |        60 |      24 |         0.00366 |               0.03523 |         0.02021 |           0.00653 |             0.05539 |
| lookback    | 6 -> 3       | later   |        30 |      24 |        -0.00727 |              -0.02961 |        -0.01765 |          -0.02153 |            -0.07746 |
| lookback    | 6 -> 3       | later   |        60 |      24 |         0.01052 |               0.00877 |        -0.0048  |          -0.01528 |            -0.07572 |

Each row averages matched parameter pairs with all other parameters held fixed. Positive drawdown lift means shallower future drawdown relative to the rest of the pool; it is not portfolio Sharpe. These later-period diagnostics did not choose the shortlist. Tau changes both profit saturation and the scale of the downside penalty, so its effect cannot be attributed solely to the profit cap. Small differences are not established significant effects.

### Portfolio metrics

| period   | rule             |    cagr |   sharpe |   weekly_sharpe |   max_drawdown | start      | end        |
|:---------|:-----------------|--------:|---------:|----------------:|---------------:|:-----------|:-----------|
| hyper_ai | anchor           |  0.4123 |   2.0054 |          2.1314 |        -0.1019 | 2026-01-01 | 2026-07-08 |
| full     | anchor           |  0.0477 |   0.3432 |          0.3389 |        -0.1381 | 2025-09-13 | 2026-09-08 |
| hyper_ai | matched_original | -0.1261 |  -0.6531 |         -0.6519 |        -0.1974 | 2026-01-01 | 2026-07-08 |
| hyper_ai | C36              | -0.2197 |  -0.8409 |         -0.7912 |        -0.2148 | 2026-01-01 | 2026-07-08 |
| hyper_ai | C12              | -0.2197 |  -0.8409 |         -0.7912 |        -0.2148 | 2026-01-01 | 2026-07-08 |
| hyper_ai | C44              | -0.2197 |  -0.8409 |         -0.7912 |        -0.2148 | 2026-01-01 | 2026-07-08 |
| full     | matched_original | -0.2629 |  -1.3203 |         -1.2509 |        -0.3177 | 2025-09-13 | 2026-09-08 |
| full     | C36              | -0.3129 |  -1.301  |         -1.2821 |        -0.3742 | 2025-09-13 | 2026-09-08 |
| full     | C12              | -0.3129 |  -1.301  |         -1.2821 |        -0.3742 | 2025-09-13 | 2026-09-08 |
| full     | C44              | -0.3129 |  -1.301  |         -1.2821 |        -0.3742 | 2025-09-13 | 2026-09-08 |
| later    | matched_original | -0.1714 |  -0.8168 |         -0.6598 |        -0.1992 | 2026-04-01 | 2026-09-08 |
| later    | C36              | -0.3808 |  -1.5736 |         -1.4782 |        -0.254  | 2026-04-01 | 2026-09-08 |
| later    | C12              | -0.3808 |  -1.5736 |         -1.4782 |        -0.254  | 2026-04-01 | 2026-09-08 |
| later    | C44              | -0.3808 |  -1.5736 |         -1.4782 |        -0.254  | 2026-04-01 | 2026-09-08 |
| later    | C36_leader_out   | -0.4734 |  -2.4719 |         -2.3301 |        -0.254  | 2026-04-01 | 2026-09-08 |

### Actual StratWise positions

| period   | rule           | first_entry   |   positions |    pnl |
|:---------|:---------------|:--------------|------------:|-------:|
| full     | C12            | 2026-08-13    |           4 | 65.225 |
| full     | C36            | 2026-08-13    |           4 | 65.225 |
| full     | C44            | 2026-08-13    |           4 | 65.225 |
| later    | C12            | 2026-08-13    |           4 | 79.581 |
| later    | C36            | 2026-08-13    |           4 | 79.581 |
| later    | C36_leader_out | 2026-08-13    |           4 | 83.283 |
| later    | C44            | 2026-08-13    |           4 | 79.581 |

## Robustness of results

Both corrected NB23 anchors must reproduce to absolute equity tolerance 1e-7. Every executed redemption is checked for single-fee pricing. Source/data signatures guard the feature cache. The same frozen universe and blacklists-off setting are used throughout; inherited current-metadata universe filtering remains a limitation.

Neighbour comparisons and young-vault tables cover all 48 settings, including failed settings. Stable-looking monthly outcomes do not prove intramonth safety. The best positive-profit contributor is removed from the FIRST training-shortlisted setting in a complete cold-start later-period re-simulation; this stress is diagnostic, not another selection criterion. Portfolio outcomes and rankings for the remaining shortlisted settings are retained even if they look worse.

### Leading contributors

| period   | rule             | address                                    | name                                      |      pnl |   positive_pnl_share |
|:---------|:-----------------|:-------------------------------------------|:------------------------------------------|---------:|---------------------:|
| hyper_ai | anchor           | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital                           | 22643.4  |               0.5137 |
| hyper_ai | C12              | 0xe67dbf2d051106b42104c1a6631af5e5a458b682 | Overdose                                  | 20634.3  |               0.6028 |
| hyper_ai | C36              | 0xe67dbf2d051106b42104c1a6631af5e5a458b682 | Overdose                                  | 20634.3  |               0.6028 |
| hyper_ai | C44              | 0xe67dbf2d051106b42104c1a6631af5e5a458b682 | Overdose                                  | 20634.3  |               0.6028 |
| full     | anchor           | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital                           | 17234.3  |               0.3009 |
| full     | C12              | 0xe67dbf2d051106b42104c1a6631af5e5a458b682 | Overdose                                  | 14851.5  |               0.3382 |
| full     | C44              | 0xe67dbf2d051106b42104c1a6631af5e5a458b682 | Overdose                                  | 14851.5  |               0.3382 |
| full     | C36              | 0xe67dbf2d051106b42104c1a6631af5e5a458b682 | Overdose                                  | 14851.5  |               0.3382 |
| later    | C44              | 0x32b1223d162056db0fb94ab244d1ef821421b95c | 一三七                                    |  8291.43 |               0.4987 |
| later    | C36              | 0x32b1223d162056db0fb94ab244d1ef821421b95c | 一三七                                    |  8291.43 |               0.4987 |
| later    | C12              | 0x32b1223d162056db0fb94ab244d1ef821421b95c | 一三七                                    |  8291.43 |               0.4987 |
| hyper_ai | matched_original | 0x2431edfcb662e6ff6deab113cc91878a0b53fb0f | Goon Edging                               |  5304.85 |               0.3994 |
| full     | matched_original | 0xd914c5164bc253676386269d90dcf56b441cf75b | Tortoise Fund                             |  5042.08 |               0.1234 |
| later    | C36_leader_out   | 0xd6e56265890b76413d1d527eb9b75e334c0c5b42 | [ Systemic Strategies ] ♾️ HyperGrowth ♾️ |  4145.47 |               0.4958 |
| later    | matched_original | 0x07fd993f0fa3a185f7207adccd29f7a87404689d | [ Systemic Strategies ] L/S Grids         |  3197.32 |               0.2022 |

### Largest cycles versus BTC and ETH

| period   | rule             | start               | end                 |   best_cycle |   kurtosis |   BTCUSDT |   ETHUSDT |
|:---------|:-----------------|:--------------------|:--------------------|-------------:|-----------:|----------:|----------:|
| hyper_ai | anchor           | 2026-06-24 00:00:00 | 2026-06-26 00:00:00 |       0.0753 |     9.9244 |   -0.0469 |   -0.0596 |
| full     | anchor           | 2026-06-24 00:00:00 | 2026-06-26 00:00:00 |       0.0734 |    11.57   |   -0.0469 |   -0.0596 |
| hyper_ai | matched_original | 2026-02-26 00:00:00 | 2026-02-28 00:00:00 |       0.032  |     2.495  |   -0.0311 |   -0.062  |
| hyper_ai | C36              | 2026-01-29 00:00:00 | 2026-01-31 00:00:00 |       0.0499 |    37.5796 |   -0.0564 |   -0.1008 |
| hyper_ai | C12              | 2026-01-29 00:00:00 | 2026-01-31 00:00:00 |       0.0499 |    37.5796 |   -0.0564 |   -0.1008 |
| hyper_ai | C44              | 2026-01-29 00:00:00 | 2026-01-31 00:00:00 |       0.0499 |    37.5796 |   -0.0564 |   -0.1008 |
| full     | matched_original | 2026-05-05 00:00:00 | 2026-05-07 00:00:00 |       0.0372 |     9.2757 |    0.0199 |    0.0016 |
| full     | C36              | 2026-09-02 00:00:00 | 2026-09-04 00:00:00 |       0.0855 |    22.159  |    0.0495 |    0.0368 |
| full     | C12              | 2026-09-02 00:00:00 | 2026-09-04 00:00:00 |       0.0855 |    22.159  |    0.0495 |    0.0368 |
| full     | C44              | 2026-09-02 00:00:00 | 2026-09-04 00:00:00 |       0.0855 |    22.159  |    0.0495 |    0.0368 |
| later    | matched_original | 2026-08-19 00:00:00 | 2026-08-21 00:00:00 |       0.0354 |     1.5986 |    0.1282 |    0.2132 |
| later    | C36              | 2026-09-02 00:00:00 | 2026-09-04 00:00:00 |       0.0843 |    32.6741 |    0.0495 |    0.0368 |
| later    | C12              | 2026-09-02 00:00:00 | 2026-09-04 00:00:00 |       0.0843 |    32.6741 |    0.0495 |    0.0368 |
| later    | C44              | 2026-09-02 00:00:00 | 2026-09-04 00:00:00 |       0.0843 |    32.6741 |    0.0495 |    0.0368 |
| later    | C36_leader_out   | 2026-05-17 00:00:00 | 2026-05-19 00:00:00 |       0.0185 |    47.424  |   -0.0147 |   -0.0232 |

### Largest losing positions and their entry histories

| name                        | address                                    | opened_at           |       pnl |   months | provisional   |      age |   p |   q |   gain |   downside | curator_excluded   | quarantined_entry   |
|:----------------------------|:-------------------------------------------|:--------------------|----------:|---------:|:--------------|---------:|----:|----:|-------:|-----------:|:-------------------|:--------------------|
| $🏧| ATM |🏧$               | 0xb1688bcae7de088fe9f2ef1d1f79e681fc0443ed | 2026-04-01 00:00:00 | -21262.6  |        2 | False         |  71      |   1 |   0 | 0.1619 |         -0 | False              | False               |
| Crypto Czars - Road to 100k | 0x3eaf61e9ebe3edae184c14841d5bb8203611d96f | 2026-06-02 00:00:00 |  -2861.67 |        2 | False         |  92      |   1 |   0 | 0.0421 |         -0 | False              | False               |
| SOL/BTC Neutral             | 0xf085dbd3f4cda645be4884c9d4c1af9cd1303591 | 2026-06-04 00:00:00 |  -2698.87 |        2 | False         |  92      |   1 |   0 | 0.0522 |         -0 | False              | False               |
| Orion                       | 0x5384bc21c19d8e154cdb4d9b6f3bb17dbf609d01 | 2026-07-02 00:00:00 |  -2368.76 |        3 | False         | 129      |   1 |   0 | 0.2959 |         -0 | False              | False               |
| Anti Martigaler             | 0xa93aaeeb8e641122777cce7cb78e729702149059 | 2026-07-16 00:00:00 |  -2353.04 |        0 | True          |   9.8436 |   1 |   0 | 0.3572 |         -0 | False              | False               |

These are individual position P&Ls for the first training-shortlisted later-period run. Perfect positive-month histories and zero downside penalties can precede severe losses. A large positive median month saturates the same reward as modest steady gains; a cap removes extra reward but does not distinguish their risk. Provisional short-history gains can saturate it too. This is an observed failure mode of the score, not evidence that a different loss-penalty coefficient would have prevented those entries.

Curator flags and quarantine-at-entry checks are saved in `position-audit.csv`. P&L and allocation averages cover each native run, whereas full-history headline metrics begin 13 September 2025. The $750 trim threshold and 0.5% minimum position weight remain fixed and can cause realised weights to differ from targets. Higher returns alone are not evidence of steady-vault selection.
