# Experiment 13 — long-period candidate replay

Period: **2023-03-01 → 2026-10-08 (end exclusive, UTC; final archive day partial)**. Ten frozen 2026 leaders and two benchmarks, each starting with $150,000.

## What was examined

Whether the ten best repaired-data 2026 CAGR/Sharpe candidates retain strong returns over every available vault backtesting observation. Original scoring, sizing, N, missing behaviour, source selection and allocation methods are preserved.

## Hypothesis and method

Hypothesis: 2026 leaders retain gains against v11 and regularised90 across full history. Select the union of top five by each metric, fill to ten by their equal-weight rank sum. Freeze before long replay. All 24 2026 metric parity checks pass. Include source v11 and focal regularised90 as additional benchmarks.

## Results
| Candidate   | Name                                                       |     CAGR |   Sharpe |   Maximum drawdown |   Final equity (USD) |   Mean cash weight |   2026 CAGR |   2026 Sharpe |
|:------------|:-----------------------------------------------------------|---------:|---------:|-------------------:|---------------------:|-------------------:|------------:|--------------:|
| C01         | Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR / 6 positions | 0.196103 | 1.455181 |          -0.079151 |        286077.842541 |           0.417960 |    0.522998 |      2.234661 |
| C02         | Blend 46d / 3 inputs / 6m CAGR / 6 positions               | 0.172029 | 1.303356 |          -0.079151 |        265856.053356 |           0.417193 |    0.519891 |      2.291272 |
| C03         | Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino / 6 positions | 0.220883 | 1.621567 |          -0.080840 |        308029.504531 |           0.437623 |    0.517666 |      2.303466 |
| C04         | Blend 46d / 7 positions                                    | 0.184532 | 1.394665 |          -0.080792 |        276224.866844 |           0.383954 |    0.479314 |      2.458715 |
| C05         | Legacy 45d / 4 inputs / 2m CAGR + 6m Sharpe / 6 positions  | 0.190605 | 1.452288 |          -0.079151 |        281365.121169 |           0.419798 |    0.496024 |      2.188999 |
| C06         | Blend 46d / 4 inputs / 6m Sortino + 2m CAGR / 7 positions  | 0.167068 | 1.256156 |          -0.104905 |        261821.698681 |           0.380648 |    0.404731 |      2.230642 |
| C07         | NB12 S18 F:gap_log L90/p2/κ30                              | 0.274434 | 1.504597 |          -0.102369 |        359592.422465 |           0.386749 |    0.474613 |      2.123093 |
| C08         | NB12 X01 F:regular L75/p2/κ30                              | 0.267854 | 1.469563 |          -0.102918 |        352943.139434 |           0.385632 |    0.469185 |      2.122572 |
| C09         | Legacy 45d / 4 inputs / 2m CAGR + 6m Sharpe / 7 positions  | 0.182339 | 1.361572 |          -0.079483 |        274385.512650 |           0.385777 |    0.441740 |      2.163980 |
| C10         | NB12 S17 F:calendar_log L90/p2/κ30                         | 0.273557 | 1.498344 |          -0.102369 |        358701.264437 |           0.386547 |    0.470421 |      2.115691 |
| B01         | Unchanged v11                                              | 0.158230 | 1.242672 |          -0.079151 |        254743.261549 |           0.418606 |    0.412004 |      1.959590 |
| B02         | Focal regularised90 benchmark                              | 0.270742 | 1.482563 |          -0.102369 |        355851.124426 |           0.385796 |    0.466005 |      2.091681 |

## Calendar-year returns
| Candidate   |   2023 (partial) |     2024 |     2025 |   2026 (partial) |
|:------------|-----------------:|---------:|---------:|-----------------:|
| C01         |        -0.036647 | 0.235121 | 0.208714 |         0.326095 |
| C02         |        -0.036647 | 0.235121 | 0.116320 |         0.334355 |
| C03         |        -0.036647 | 0.244127 | 0.291491 |         0.326659 |
| C04         |        -0.036647 | 0.238981 | 0.202280 |         0.283263 |
| C05         |        -0.036647 | 0.235121 | 0.206908 |         0.306200 |
| C06         |        -0.036647 | 0.238981 | 0.155732 |         0.265340 |
| C07         |         0.014324 | 0.458622 | 0.252121 |         0.294058 |
| C08         |         0.014324 | 0.458130 | 0.232458 |         0.290828 |
| C09         |        -0.036647 | 0.238981 | 0.220198 |         0.255999 |
| C10         |         0.014324 | 0.456342 | 0.251149 |         0.293876 |
| B01         |        -0.036647 | 0.235121 | 0.135220 |         0.257293 |
| B02         |         0.014324 | 0.456342 | 0.244428 |         0.290527 |

## Key new insights

Highest long CAGR: **C07 NB12 S18 F:gap_log L90/p2/κ30**, 27.44%, Sharpe 1.50, drawdown -10.24%. Highest long Sharpe: **C03 Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino / 6 positions**, 1.62, CAGR 22.09%.

Source v11: 15.82% CAGR / 1.24 Sharpe. Regularised90: 27.07% / 1.48. 10/10 exceed source v11 on both metrics; 2/10 exceed regularised90 on both.

## Robustness of results

The first actual positive NAV is 2023-03-01 00:00:00, last is 2026-10-07 00:00:00. The 1 March calendar includes the initial empty lead-in. All position PnL reconciles within $1; absolute weights sum to whole account equity. NAV-only forward fill preserves missing leading marks and actual-observation masks. Permission and capacity fields are handled by the unchanged source engine.
| Candidate   |   Best update |   Worst update | Best update date   |   Excess kurtosis | Top vault       |   Top positive profit share |   Sharpe with best update zeroed |   PnL residual (USD) |
|:------------|--------------:|---------------:|:-------------------|------------------:|:----------------|----------------------------:|---------------------------------:|---------------------:|
| C01         |      0.057310 |      -0.079151 | 2025-08-14         |         34.959365 | Realist Capital |                    0.153648 |                         1.369279 |             0.000000 |
| C02         |      0.057438 |      -0.079151 | 2025-08-14         |         36.204205 | Realist Capital |                    0.158476 |                         1.212822 |             0.000000 |
| C03         |      0.067128 |      -0.079151 | 2025-08-14         |         38.011957 | Realist Capital |                    0.156393 |                         1.534953 |            -0.000000 |
| C04         |      0.060350 |      -0.079151 | 2025-01-22         |         39.625049 | Realist Capital |                    0.195523 |                         1.303870 |             0.000000 |
| C05         |      0.054865 |      -0.079151 | 2025-08-14         |         36.547868 | Realist Capital |                    0.167200 |                         1.367201 |             0.000000 |
| C06         |      0.060350 |      -0.079151 | 2025-01-22         |         40.014372 | Realist Capital |                    0.139441 |                         1.162090 |             0.000000 |
| C07         |      0.151570 |      -0.072729 | 2024-11-13         |         95.494778 | Delta_01        |                    0.178532 |                         1.422212 |            -0.000000 |
| C08         |      0.151570 |      -0.073073 | 2024-11-13         |         95.412476 | Delta_01        |                    0.181710 |                         1.382266 |            -0.000000 |
| C09         |      0.060350 |      -0.079151 | 2025-01-22         |         36.609417 | Realist Capital |                    0.179001 |                         1.270500 |             0.000000 |
| C10         |      0.151570 |      -0.072473 | 2024-11-13         |         95.147606 | Delta_01        |                    0.176941 |                         1.414956 |            -0.000000 |
| B01         |      0.054258 |      -0.079151 | 2025-08-14         |         39.051128 | Realist Capital |                    0.172163 |                         1.152120 |            -0.000000 |
| B02         |      0.151570 |      -0.072779 | 2024-11-13         |         94.571284 | Delta_01        |                    0.180243 |                         1.396907 |            -0.000000 |

The largest recorded updates are audited against their vault NAV marks, current curator and BTC/ETH price context. Daily-resampled returns include two-day updates. The concentration table and quarterly heatmap should be considered alongside CAGR. No single removed-day or removed-vault diagnostic represents an executable rebalanced portfolio.

## Observation-interval audit
| Candidate   | Update     | Vault                  |          PnL | Supported   | First_mark              | Last_mark               |   Elapsed_days |   NAV_return |   Actual_marks | Receipt_after_engine_label   | Curator_excluded   | Quarantined   |   BTCUSDT return |   ETHUSDT return |
|:------------|:-----------|:-----------------------|-------------:|:------------|:------------------------|:------------------------|---------------:|-------------:|---------------:|:-----------------------------|:-------------------|:--------------|-----------------:|-----------------:|
| C03         | 2025-08-14 | naze oppa degen nation |  4388.842904 | True        | 2025-08-06 00:00:00.000 | 2025-08-13 00:00:00.000 |       7.000000 |     0.086983 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| C03         | 2025-08-14 | DailyTradeAI  Low risk |  3611.727339 | True        | 2025-08-06 22:14:00.022 | 2025-08-13 22:54:00.047 |       7.027778 |     0.071758 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| C03         | 2025-08-14 | cDOGE                  |  3026.232817 | True        | 2025-08-06 22:56:00.044 | 2025-08-13 22:16:00.032 |       6.972222 |     0.158532 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| C07         | 2024-11-13 | Road to 10 Million     | 15050.797563 | True        | 2024-11-06 00:00:00.000 | 2024-11-13 00:00:00.000 |       7.000000 |     0.302617 |              2 | False                        | False              | False         |         0.195882 |         0.170945 |
| C07         | 2024-11-13 | FFLGN                  |  4326.216664 | True        | 2024-11-06 22:12:00.158 | 2024-11-13 23:12:00.065 |       7.041666 |     0.416908 |              2 | True                         | False              | False         |         0.195882 |         0.170945 |
| C07         | 2024-11-13 | Delta_01               |  3588.314338 | True        | 2024-11-06 21:54:00.123 | 2024-11-13 23:14:00.148 |       7.055556 |     0.072605 |              2 | True                         | False              | False         |         0.195882 |         0.170945 |
| B01         | 2025-08-14 | DailyTradeAI  Low risk |  3611.727339 | True        | 2025-08-06 22:14:00.022 | 2025-08-13 22:54:00.047 |       7.027778 |     0.071758 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| B01         | 2025-08-14 | cDOGE                  |  3163.767157 | True        | 2025-08-06 22:56:00.044 | 2025-08-13 22:16:00.032 |       6.972222 |     0.158532 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| B01         | 2025-08-14 | JizzJazz               |  1820.820961 | True        | 2025-08-06 00:00:00.000 | 2025-08-13 22:24:00.019 |       7.933334 |     0.114081 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |

The new allocation family recognises a 15.16% account update on 13 November 2024. This catches weekly marks, including Road to 10 Million (+30.26% NAV), FFLGN (+41.69%) and Delta_01 (+7.26%) since 6 November. BTC/ETH context is measured over those same real mark dates. Late intraday marks can fall after the daily engine label: this preserves the inherited daily-close convention, not a timestamp-faithful execution validation.

## Tail influence
| Candidate   |   Best update |   CAGR best update zeroed |   Sharpe best update zeroed | Removed vault   |   CAGR without leader fixed ledger |   Sharpe without leader fixed ledger |
|:------------|--------------:|--------------------------:|----------------------------:|:----------------|-----------------------------------:|-------------------------------------:|
| C01         |      0.057310 |                  0.177758 |                    1.369279 | Realist Capital |                           0.163921 |                             1.323856 |
| C02         |      0.057438 |                  0.154014 |                    1.212822 | Realist Capital |                           0.141172 |                             1.154520 |
| C03         |      0.067128 |                  0.199079 |                    1.534953 | Realist Capital |                           0.185922 |                             1.465509 |
| C04         |      0.060350 |                  0.165436 |                    1.303870 | Realist Capital |                           0.140443 |                             1.120438 |
| C05         |      0.054865 |                  0.173097 |                    1.367201 | Realist Capital |                           0.156179 |                             1.280607 |
| C06         |      0.060350 |                  0.148254 |                    1.162090 | Realist Capital |                           0.138415 |                             1.094634 |
| C07         |      0.151570 |                  0.225513 |                    1.422212 | Delta_01        |                           0.224952 |                             1.248214 |
| C08         |      0.151570 |                  0.219186 |                    1.382266 | Delta_01        |                           0.218180 |                             1.209237 |
| C09         |      0.060350 |                  0.163278 |                    1.270500 | Realist Capital |                           0.143680 |                             1.142687 |
| C10         |      0.151570 |                  0.224670 |                    1.414956 | Delta_01        |                           0.224440 |                             1.241576 |
| B01         |      0.054258 |                  0.141381 |                    1.152120 | Realist Capital |                           0.125269 |                             1.053733 |
| B02         |      0.151570 |                  0.221963 |                    1.396907 | Delta_01        |                           0.220853 |                             1.221916 |

## Allocation contrasts
| Candidate   | Reference   |   CAGR difference (pp) |   Sharpe difference |   Drawdown difference (pp) |   Final equity difference (USD) |
|:------------|:------------|-----------------------:|--------------------:|---------------------------:|--------------------------------:|
| C07         | C03         |               5.355112 |           -0.116970 |                  -2.152912 |                    51562.917933 |
| C07         | B02         |               0.369152 |            0.022034 |                  -0.000000 |                     3741.298039 |
| C08         | C03         |               4.697089 |           -0.152004 |                  -2.207870 |                    44913.634902 |
| C08         | B02         |              -0.288872 |           -0.013000 |                  -0.054959 |                    -2907.984992 |
| C10         | C03         |               5.267435 |           -0.123222 |                  -2.152912 |                    50671.759906 |
| C10         | B02         |               0.281475 |            0.015782 |                  -0.000000 |                     2850.140012 |

Most of the long-period allocation-family gain is already present in the regularised90 benchmark: compare C07 directly with B02 before attributing it to the gap estimator. New allocations have worse drawdown and lower Sharpe than the original four-input source candidate, despite greater CAGR. Q4 2024 and sparse valuation timing materially affect the result.

## Hypothesis verdict and next leads

The descriptive hypothesis is supported against v11, but there is no consistent allocation-family winner across years. C07 returns 45.86% in 2024 versus C03’s 24.41%; it then trails C03 in 2025 (25.21% versus 29.15%) and carried 2026 (29.41% versus 32.67%). The highest fresh-2026 Sharpe candidate, C04, is not the full-history Sharpe leader. C03 retains the strongest long Sharpe; C07 has the highest CAGR with greater drawdown. The isolated gap-estimator improvement over regularised90 is only about 0.37 percentage points CAGR and 0.02 Sharpe.

Relative performance is descriptive: 2026 selection overlaps the full period and earlier years were already searched. Earlier and new candidates can be compared with the same archive, but this replay does not provide independent confirmation. Early low deployment and changing vault availability depress full-calendar CAGR. Use the quarter/cash plots to distinguish these effects from poor selected-vault performance. Next, freeze a candidate and compare source versus simultaneous allocation on matched selection, then observe genuinely later data.
