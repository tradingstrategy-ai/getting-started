# Experiment 12 — allocation follow-up findings

Period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**; all2025 and earlier warmup retained. **12 sensitivities + eight cap-aware methods + ten controls; 16 full engine replays.**

## What was examined

Local risk windows, prior strength, raw floors and constrained risk-budget allocations on fixed six-vault baskets. The engine shortlist then carries holdings with source two-day rebalancing, actual fill timing, hysteresis, permissions and fees.

## Hypotheses and snapshot results

A useful sizing method should survive nearby parameters; including capacity constraints inside the convex objective may improve allocation. Snapshot results use 62 resolved30-day origins, eight complete blocks; all comparisons are descriptive.
| arm   | label                                    |   mean_return |   mean_drawdown |   mean_cash |
|:------|:-----------------------------------------|--------------:|----------------:|------------:|
| S01   | F:equal                                  |      0.017158 |       -0.061931 |    0.033153 |
| S02   | L:equal                                  |      0.019285 |       -0.056981 |    0.030078 |
| S03   | F:regular L90/p2/κ30                     |      0.025121 |       -0.041906 |    0.033153 |
| S04   | L:regular L90/p2/κ30                     |      0.019920 |       -0.037771 |    0.030078 |
| S15   | L:bounded_V                              |      0.020312 |       -0.050285 |    0.030078 |
| S16   | L:T18                                    |      0.023903 |       -0.050033 |    0.030078 |
| S17   | F:calendar_log L90/p2/κ30                |      0.024131 |       -0.042496 |    0.033153 |
| S18   | F:gap_log L90/p2/κ30                     |      0.025788 |       -0.041825 |    0.033153 |
| M39   | L:calendar_log L90/p2/κ30                |      0.019676 |       -0.037820 |    0.030078 |
| M40   | L:gap_log L90/p2/κ30                     |      0.020073 |       -0.038312 |    0.030078 |
| X01   | F:regular L75/p2/κ30                     |      0.026157 |       -0.039427 |    0.033153 |
| X02   | F:regular L105/p2/κ30                    |      0.023789 |       -0.045335 |    0.033153 |
| X03   | L:regular L75/p2/κ30                     |      0.020784 |       -0.035367 |    0.030078 |
| X04   | L:regular L105/p2/κ30                    |      0.019589 |       -0.041109 |    0.030078 |
| X05   | F:regular L90/p2/κ10                     |      0.024818 |       -0.040985 |    0.033153 |
| X06   | F:regular L90/p2/κ90                     |      0.024420 |       -0.045191 |    0.033153 |
| X07   | L:regular L90/p2/κ10                     |      0.018122 |       -0.037508 |    0.030078 |
| X08   | L:regular L90/p2/κ90                     |      0.021022 |       -0.040613 |    0.030078 |
| X09   | F:raw L90/p2/κ30                         |      0.023527 |       -0.041779 |    0.033153 |
| X10   | F:raw L90/p2/κ30                         |      0.023527 |       -0.041779 |    0.033153 |
| X11   | L:raw L90/p2/κ30                         |      0.014668 |       -0.039727 |    0.030078 |
| X12   | L:raw L90/p2/κ30                         |      0.014668 |       -0.039727 |    0.030078 |
| C01   | F:equal_risk / projected                 |      0.019186 |       -0.047853 |    0.033153 |
| C02   | F:equal_risk / constrained_convex        |      0.020468 |       -0.046417 |    0.033153 |
| C03   | F:frozen_score_risk / projected          |      0.019549 |       -0.049579 |    0.033153 |
| C04   | F:frozen_score_risk / constrained_convex |      0.021033 |       -0.047671 |    0.033153 |
| C05   | L:equal_risk / projected                 |      0.017787 |       -0.043771 |    0.030078 |
| C06   | L:equal_risk / constrained_convex        |      0.018356 |       -0.042487 |    0.030078 |
| C07   | L:frozen_score_risk / projected          |      0.018338 |       -0.045809 |    0.030078 |
| C08   | L:frozen_score_risk / constrained_convex |      0.019306 |       -0.044045 |    0.030078 |

## Full engine results

Engine CAGR is directly executable in the simulation. Research methods share simultaneous cap allocation; source_v11 uses its untouched original sequential allocator. Caps are relative to the current deployable budget, unlike fixed-account snapshot caps. Missing scores keep source selection behaviour; young risk histories use causal partial histories and peer fallbacks.
| Arm          | Method                                             |     CAGR |   Sharpe |   Maximum drawdown |   Final equity (USD) |   Mean cash weight |   Trades |
|:-------------|:---------------------------------------------------|---------:|---------:|-------------------:|---------------------:|-------------------:|---------:|
| S01          | F:equal                                            | 0.379663 | 1.525982 |          -0.115787 |        191142.290360 |           0.093897 |      582 |
| S02          | L:equal                                            | 0.336302 | 1.375717 |          -0.105610 |        186582.139005 |           0.083684 |      584 |
| S03          | F:regular L90/p2/κ30                               | 0.466005 | 2.091681 |          -0.070479 |        200120.271950 |           0.096751 |      598 |
| S04          | L:regular L90/p2/κ30                               | 0.333386 | 1.631836 |          -0.065990 |        186274.117683 |           0.083346 |      606 |
| S15          | L:bounded_V                                        | 0.342456 | 1.463631 |          -0.099511 |        187231.475629 |           0.083865 |      609 |
| S16          | L:T18                                              | 0.396587 | 1.642138 |          -0.097452 |        192912.638171 |           0.086394 |      612 |
| S17          | F:calendar_log L90/p2/κ30                          | 0.470421 | 2.115691 |          -0.070768 |        200575.966577 |           0.097230 |      606 |
| S18          | F:gap_log L90/p2/κ30                               | 0.474613 | 2.123093 |          -0.071036 |        201008.203735 |           0.097263 |      604 |
| C01          | F:equal_risk / projected                           | 0.429839 | 1.916015 |          -0.082587 |        196375.826278 |           0.096035 |      600 |
| C02          | F:equal_risk / constrained_convex                  | 0.428769 | 1.925486 |          -0.080553 |        196264.657699 |           0.095599 |      596 |
| C05          | L:equal_risk / projected                           | 0.334856 | 1.574289 |          -0.076833 |        186429.414551 |           0.083434 |      607 |
| C06          | L:equal_risk / constrained_convex                  | 0.338843 | 1.602299 |          -0.074981 |        186850.322569 |           0.083052 |      596 |
| X01          | F:regular L75/p2/κ30                               | 0.469185 | 2.122572 |          -0.070837 |        200448.422774 |           0.097650 |      595 |
| X08          | L:regular L90/p2/κ90                               | 0.320718 | 1.527898 |          -0.070591 |        184934.421947 |           0.082607 |      613 |
| source_focal | Focal score / original source sizing and allocator | 0.517666 | 2.303466 |          -0.063454 |        205430.301709 |           0.101765 |      569 |
| source_v11   | Unchanged v11 source                               | 0.412004 | 1.959590 |          -0.064031 |        194520.812686 |           0.088321 |      581 |

## Key new insights

- F best registered sensitivity X01 has mean30-day return 2.616% versus 2.512% for the regularised90-day benchmark. Its engine replay CAGR is 46.92% versus 46.60%; this sensitivity was selected retrospectively.

- L best registered sensitivity X08 has mean30-day return 2.102% versus 1.992% for the regularised90-day benchmark. Its engine replay CAGR is 32.07% versus 33.34%; this sensitivity was selected retrospectively.

- Constrained C02 minus projected C01: +0.128 percentage points mean30-day return, +0.144 points mean drawdown. Same snapshot invested budget.

- Constrained C04 minus projected C03: +0.148 percentage points mean30-day return, +0.191 points mean drawdown. Same snapshot invested budget.

- Constrained C06 minus projected C05: +0.057 percentage points mean30-day return, +0.128 points mean drawdown. Same snapshot invested budget.

- Constrained C08 minus projected C07: +0.097 percentage points mean30-day return, +0.176 points mean drawdown. Same snapshot invested budget.

## Robustness of results

All ten NB11 reference controls reproduce accepted weights and all horizon outcomes. Mathematical fixtures, cap feasibility, solver KKT/objective checks and paired-budget checks pass. One mature90-day basket remains unresolved without survivor renormalisation. Only eight independent primary30-day blocks and repeatedly searched history prevent confirmation claims. Source inventory/guard history and archive publication clocks remain limitations.

Position curves reconcile to total portfolio PnL within $1. Tail statistics and vault contribution tables are saved and shown. Concentration and quarter influence must be assessed alongside aggregate metrics.
| Arm          |   Best day |   Worst day | Best day date   |   Excess kurtosis | Top positive vault   |   Top positive vault share |   PnL residual (USD) |
|:-------------|-----------:|------------:|:----------------|------------------:|:---------------------|---------------------------:|---------------------:|
| S01          |   0.068415 |   -0.049393 | 2026-06-26      |          7.415235 | Realist Capital      |                   0.352826 |             0.000000 |
| S02          |   0.068650 |   -0.050560 | 2026-06-26      |          7.349009 | Realist Capital      |                   0.398010 |             0.000000 |
| S03          |   0.068083 |   -0.047246 | 2026-06-26      |         11.133952 | Realist Capital      |                   0.377969 |             0.000000 |
| S04          |   0.070523 |   -0.050641 | 2026-06-26      |         13.315592 | Realist Capital      |                   0.400094 |             0.000000 |
| S15          |   0.069809 |   -0.050391 | 2026-06-26      |          8.231274 | Realist Capital      |                   0.408875 |            -0.000000 |
| S16          |   0.069701 |   -0.048955 | 2026-06-26      |          8.026562 | Realist Capital      |                   0.421166 |             0.000000 |
| S17          |   0.068055 |   -0.047142 | 2026-06-26      |         11.252963 | Realist Capital      |                   0.378178 |             0.000000 |
| S18          |   0.068002 |   -0.047044 | 2026-06-26      |         11.333579 | Realist Capital      |                   0.378728 |             0.000000 |
| C01          |   0.068242 |   -0.048119 | 2026-06-26      |         10.202296 | Realist Capital      |                   0.381899 |             0.000000 |
| C02          |   0.068249 |   -0.048145 | 2026-06-26      |         10.461157 | Realist Capital      |                   0.380165 |             0.000000 |
| C05          |   0.070335 |   -0.050600 | 2026-06-26      |         11.193234 | Realist Capital      |                   0.386986 |             0.000000 |
| C06          |   0.070405 |   -0.050490 | 2026-06-26      |         11.502972 | Realist Capital      |                   0.399066 |             0.000000 |
| X01          |   0.068409 |   -0.047171 | 2026-06-26      |         11.800145 | Realist Capital      |                   0.399434 |             0.000000 |
| X08          |   0.070499 |   -0.050996 | 2026-06-26      |         11.533107 | Realist Capital      |                   0.401285 |             0.000000 |
| source_focal |   0.068003 |   -0.046062 | 2026-06-26      |         11.841919 | Realist Capital      |                   0.384162 |             0.000000 |
| source_v11   |   0.068871 |   -0.048563 | 2026-06-26      |         13.403416 | Realist Capital      |                   0.447703 |             0.000000 |

## Paired engine attribution — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Largest observed candidate per selector; searched historical comparison.

| Selector   | Arm   | Control      |   CAGR difference (pp) |   Sharpe difference |   Drawdown difference (pp) |   Equity difference (USD) |
|:-----------|:------|:-------------|-----------------------:|--------------------:|---------------------------:|--------------------------:|
| F          | S18   | S03          |                  0.861 |               0.031 |                     -0.056 |                   887.932 |
| F          | S18   | source_focal |                 -4.305 |              -0.180 |                     -0.758 |                 -4422.098 |
| L          | S16   | S04          |                  6.320 |               0.010 |                     -3.146 |                  6638.520 |
| L          | S16   | source_v11   |                 -1.542 |              -0.317 |                     -3.342 |                 -1608.175 |

| Selector   | Arm   | Control      | Vault            |   PnL difference (USD) |   Total equity difference (USD) |
|:-----------|:------|:-------------|:-----------------|-----------------------:|--------------------------------:|
| L          | S16   | S04          | Hyperrr          |               4908.918 |                        6638.520 |
| L          | S16   | S04          | Realist Capital  |               3696.226 |                        6638.520 |
| L          | S16   | S04          | pmalt            |              -3852.853 |                        6638.520 |
| L          | S16   | S04          | AceVault Hyper01 |               -870.543 |                        6638.520 |
| L          | S16   | source_v11   | Hyperrr          |               4725.643 |                       -1608.175 |
| L          | S16   | source_v11   | Citadel          |               1599.284 |                       -1608.175 |
| L          | S16   | source_v11   | pmalt            |              -4837.231 |                       -1608.175 |
| L          | S16   | source_v11   | Realist Capital  |              -1814.066 |                       -1608.175 |
| F          | S18   | S03          | pmalt            |               1605.511 |                         887.932 |
| F          | S18   | S03          | Goon Edging      |                968.225 |                         887.932 |
| F          | S18   | S03          | Hyperrr          |              -1682.886 |                         887.932 |
| F          | S18   | S03          | Citadel          |               -138.150 |                         887.932 |
| F          | S18   | source_focal | Goon Edging      |                713.581 |                       -4422.098 |
| F          | S18   | source_focal | IKAGI            |                357.445 |                       -4422.098 |
| F          | S18   | source_focal | Realist Capital  |              -1943.402 |                       -4422.098 |
| F          | S18   | source_focal | Hyperrr          |              -1263.862 |                       -4422.098 |

## Tail attribution and valuation clock

The source v11 maximum recorded equity return is 6.887% on 26 June. Equity is marked at a two-day decision cadence, so this is a multi-day update displayed on a daily grid. Realist Capital contributes $6,929.95 and Goon Edging$4,620.27 to that update. Both have actual positive daily NAV marks across 23–25 June; neither is excluded or quarantined by the current curator at the update date. BTC and ETH fell across the corresponding 23–25 June window. A broad rising market does not explain these vault profits, and the observations alone do not establish a data error.

| Asset           |   23→25 June NAV return |   Actual daily marks |   Recorded PnL change (USD) | Curator excluded   | Quarantined at update   |
|:----------------|------------------------:|---------------------:|----------------------------:|:-------------------|:------------------------|
| Realist Capital |                0.140586 |                    3 |                 6929.951861 | False              | False                   |
| Goon Edging     |                0.138565 |                    3 |                 4620.271682 | False              | False                   |
| BTCUSDT         |               -0.046873 |                    3 |                  nan        | False              | False                   |
| ETHUSDT         |               -0.059557 |                    3 |                  nan        | False              | False                   |

## Verdict after engine replay

Retain the original hand-picked four-input score and source allocator as the performance reference. The regularised benchmark remains a research control rather than an established production improvement. Sparse gap sizing provides a small incremental gain against that control; its vault contributions offset strongly. Local 75-day gains are small in the engine, stronger v11 shrinkage loses, and the cap-aware benefit is mixed once holdings are carried through time. All four cap-aware snapshot uplifts are mainly concentrated in Q3. Raw variance-floor sensitivity is inactive in these baskets.

Source v11 and focal controls reproduce 41.20% and 51.77% CAGR on the pinned repaired archive. The best replayed new candidate is sparse focal sizing at 47.46%, 2.12 Sharpe and −7.10% drawdown, below the original focal strategy on all three metrics. No production change follows from these results. A useful next question is why regularisation/redistribution changes exposure to individual profitable vaults, with controlled source-allocator versus simultaneous-allocator comparisons and later fresh observations. More broad parameter searching is unlikely to resolve the concentration and execution issues shown here.
