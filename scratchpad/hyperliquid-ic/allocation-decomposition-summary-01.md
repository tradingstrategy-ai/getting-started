# Allocation-limit decomposition

Based on `21-research-quality-only-portfolios.ipynb`. Thirty-two fixed engine-anchor simulations: eight allocation combinations, two periods and two universe treatments. No search for a winning threshold; no A0b or other ranker generalisation is claimed.

## Key new insights and what did we learn?

This factorial separates three simultaneous NB21 changes. N changes the position maximum from 6 to the full eligible universe (360 vault addresses in this snapshot); W changes maximum portfolio weight from 33% to 100%; V changes historical vault-TVL capacity from 33% to 100%. A 1 means relaxed, a 0 means original. All primary runs retain blacklists off; leader_out excludes only intothecryptoverse.com from inception as a diagnostic counterfactual.

**The N result is not evidence that flexible portfolio size improves risk.** N alone changes full-period CAGR from -0.37% to 8.50%, Sharpe from 0.073 to 1.273 and maximum drawdown from -14.37% to -2.50%. But N raises the ceiling from six to 360 addresses: the ranker still orders candidates, yet every gate-passing candidate can enter sizing. The unchanged inverse-variance sizing then favours low-volatility share-price histories, including stale marks. In N1W0V0, 32.2% of funded dollars went to vaults whose daily price moved on fewer than 30% of common-window days; 30.4% of reconstructed terminal marked value was older than 30 days, and kurtosis was 62.7. Its measured risk statistics cannot therefore be compared with the N0 arms as evidence of steadier economic returns.

**The apparent diversification is mark-quality confounded.** Mean effective holdings rise under N, but the relevant distinction is between independently re-marked holdings and a book with flat NAVs that later catch up. The allocation table remains a correct description of engine weights; it is not proof that the additional vaults are StratWise-like or that the lower measured drawdown is real. The raw diagnostics in `mark-quality-audit.csv` and `mark-quality-by-vault.csv` must accompany any N comparison.

**Removing the portfolio-weight cap is not a stable-return result.** The short-period W-only result (54.48% CAGR, 2.720 Sharpe) weakens to 22.28% CAGR, 1.176 Sharpe and -13.72% drawdown in the full period. Realist Capital supplies 52.9% of its positive per-vault P&L in that short run ($23,365 across 2 positions). The full-period Shapley W contribution includes this N0 concentrated path, so it does not contradict the small conditional effect of W after N is relaxed.

**Relaxing vault-TVL capacity is also dark-holding and leader dependent.** With N relaxed and W retained, it changes unmasked full CAGR from 8.50% to 11.02%, while the low-fresh funded share rises from 32.2% to 57.6% and stale-over-30-day terminal marked value rises from 30.4% to 72.5%. Removing intothecryptoverse.com changes the same pair to 5.63% and 4.47% CAGR. It is not a robust capacity improvement.

**Conclusion:** this experiment does not identify an allocation-limit change to carry forward for the stable-vault objective. It confirms that W-only return is concentrated and that V relaxation is not robust, but it withdraws the former N recommendation. A later experiment may test freshness-aware, age-aware sizing, including young vaults fairly; it must measure mark freshness and terminal stale-value exposure before interpreting Sharpe or drawdown. We have not demonstrated robust ~20% CAGR, steady StratWise-like selection, or a reason to introduce a new hard age barrier.

[Full-period equity curves](_artifacts-allocation-decomposition/equity-full.png) · [Hyper-ai-period equity curves](_artifacts-allocation-decomposition/equity-hyper_ai.png) · [Leading-vault NAV](_artifacts-allocation-decomposition/leading-vault-nav.png).

Full-period Sharpe attribution, averaged over all six orders of applying the switches:

| mask       | factor   |   contribution |   total_change |
|:-----------|:---------|---------------:|---------------:|
| all        | N        |     0.774316   |        1.24871 |
| all        | W        |     0.387259   |        1.24871 |
| all        | V        |     0.0871383  |        1.24871 |
| leader_out | N        |     0.375978   |        0.77113 |
| leader_out | W        |     0.386341   |        0.77113 |
| leader_out | V        |     0.00881155 |        0.77113 |

These Shapley contributions sum exactly to the N0W0V0→N1W1V1 change. They allocate interaction effects across factors; they are not independent effect sizes, statistical significance or estimates of live-market causality. Inspect conditional-effects.csv for every single-switch comparison and interactions.csv for dependence between switches.

## Summary of results

| period   | mask       | arm    | cagr   |   sharpe | max_drawdown   |
|:---------|:-----------|:-------|:-------|---------:|:---------------|
| hyper_ai | all        | N0W0V0 | 34.2%  |     1.74 | -10.4%         |
| hyper_ai | all        | N0W0V1 | 24.6%  |     1.49 | -7.1%          |
| hyper_ai | all        | N0W1V0 | 54.5%  |     2.72 | -3.9%          |
| hyper_ai | all        | N0W1V1 | 8.1%   |     0.63 | -8.7%          |
| hyper_ai | all        | N1W0V0 | 12.8%  |     2.32 | -0.9%          |
| hyper_ai | all        | N1W0V1 | 19.7%  |     1.97 | -0.7%          |
| hyper_ai | all        | N1W1V0 | 13.0%  |     2.35 | -0.9%          |
| hyper_ai | all        | N1W1V1 | 19.7%  |     1.97 | -0.7%          |
| hyper_ai | leader_out | N0W0V0 | 34.2%  |     1.74 | -10.4%         |
| hyper_ai | leader_out | N0W0V1 | 24.6%  |     1.49 | -7.1%          |
| hyper_ai | leader_out | N0W1V0 | 54.5%  |     2.72 | -3.9%          |
| hyper_ai | leader_out | N0W1V1 | 8.1%   |     0.63 | -8.7%          |
| hyper_ai | leader_out | N1W0V0 | 6.3%   |     1.96 | -0.9%          |
| hyper_ai | leader_out | N1W0V1 | 6.6%   |     1.65 | -0.8%          |
| hyper_ai | leader_out | N1W1V0 | 6.6%   |     1.99 | -0.9%          |
| hyper_ai | leader_out | N1W1V1 | 6.6%   |     1.65 | -0.8%          |
| full     | all        | N0W0V0 | -0.4%  |     0.07 | -14.4%         |
| full     | all        | N0W0V1 | 8.5%   |     0.58 | -8.4%          |
| full     | all        | N0W1V0 | 22.3%  |     1.18 | -13.7%         |
| full     | all        | N0W1V1 | 8.7%   |     0.65 | -8.7%          |
| full     | all        | N1W0V0 | 8.5%   |     1.27 | -2.5%          |
| full     | all        | N1W0V1 | 11.0%  |     1.33 | -2.8%          |
| full     | all        | N1W1V0 | 9.0%   |     1.33 | -2.5%          |
| full     | all        | N1W1V1 | 11.0%  |     1.32 | -2.8%          |
| full     | leader_out | N0W0V0 | -0.4%  |     0.07 | -14.4%         |
| full     | leader_out | N0W0V1 | 8.5%   |     0.58 | -8.4%          |
| full     | leader_out | N0W1V0 | 22.3%  |     1.18 | -13.7%         |
| full     | leader_out | N0W1V1 | 8.7%   |     0.65 | -8.7%          |
| full     | leader_out | N1W0V0 | 5.6%   |     0.95 | -2.4%          |
| full     | leader_out | N1W0V1 | 4.5%   |     0.85 | -2.8%          |
| full     | leader_out | N1W1V0 | 6.0%   |     1.01 | -2.4%          |
| full     | leader_out | N1W1V1 | 4.4%   |     0.84 | -2.8%          |

Common periods: 1 January–8 July 2026 and 13 September 2025–8 September 2026. Full engine runs begin 1 August; full-common figures are slices of already-running portfolios. Sharpe uses two-day marks. Weekly Sharpe, volatility, best-cycle return and kurtosis are also exported.

## Allocation outcomes

| period   | mask       | arm    |   mean_invested |   mean_positions |   max_positions |   peak_weight |   effective_positions |
|:---------|:-----------|:-------|----------------:|-----------------:|----------------:|--------------:|----------------------:|
| full     | all        | N0W0V0 |        0.972516 |          5.93923 |               6 |      0.353226 |               4.17429 |
| full     | all        | N0W0V1 |        0.981584 |          5.87845 |               6 |      0.350079 |               3.96049 |
| full     | all        | N0W1V0 |        0.971343 |          5.64641 |               6 |      0.948814 |               3.14555 |
| full     | all        | N0W1V1 |        0.980246 |          5.45304 |               6 |      0.954533 |               2.5736  |
| full     | all        | N1W0V0 |        0.930058 |         27.3923  |              42 |      0.337324 |              13.9895  |
| full     | all        | N1W0V1 |        0.95695  |         16.3536  |              32 |      0.324873 |              11.1924  |
| full     | all        | N1W1V0 |        0.928618 |         26.7348  |              42 |      0.550397 |              13.7251  |
| full     | all        | N1W1V1 |        0.956538 |         16.2762  |              32 |      0.398126 |              11.1224  |
| full     | leader_out | N0W0V0 |        0.972516 |          5.93923 |               6 |      0.353226 |               4.17429 |
| full     | leader_out | N0W0V1 |        0.981584 |          5.87845 |               6 |      0.350079 |               3.96049 |
| full     | leader_out | N0W1V0 |        0.971343 |          5.64641 |               6 |      0.948814 |               3.14555 |
| full     | leader_out | N0W1V1 |        0.980246 |          5.45304 |               6 |      0.954533 |               2.5736  |
| full     | leader_out | N1W0V0 |        0.930618 |         27.1989  |              42 |      0.337327 |              13.7721  |
| full     | leader_out | N1W0V1 |        0.956122 |         16.2983  |              32 |      0.324881 |              10.9208  |
| full     | leader_out | N1W1V0 |        0.928929 |         26.5359  |              42 |      0.550397 |              13.5159  |
| full     | leader_out | N1W1V1 |        0.956288 |         16.1602  |              32 |      0.398126 |              10.8336  |
| hyper_ai | all        | N0W0V0 |        0.967001 |          5.85263 |               6 |      0.335858 |               4.17028 |
| hyper_ai | all        | N0W0V1 |        0.970495 |          5.83158 |               6 |      0.335072 |               4.00619 |
| hyper_ai | all        | N0W1V0 |        0.966367 |          5.55789 |               6 |      0.948814 |               3.33217 |
| hyper_ai | all        | N0W1V1 |        0.970784 |          5.48421 |               6 |      0.948814 |               2.6358  |
| hyper_ai | all        | N1W0V0 |        0.923313 |         24.3368  |              34 |      0.337189 |              12.5413  |
| hyper_ai | all        | N1W0V1 |        0.956479 |         13.5579  |              30 |      0.323469 |              10.7707  |
| hyper_ai | all        | N1W1V0 |        0.92305  |         24.2316  |              34 |      0.360057 |              12.4928  |
| hyper_ai | all        | N1W1V1 |        0.956149 |         13.4526  |              30 |      0.359414 |              10.7345  |
| hyper_ai | leader_out | N0W0V0 |        0.967001 |          5.85263 |               6 |      0.335858 |               4.17028 |
| hyper_ai | leader_out | N0W0V1 |        0.970495 |          5.83158 |               6 |      0.335072 |               4.00619 |
| hyper_ai | leader_out | N0W1V0 |        0.966367 |          5.55789 |               6 |      0.948814 |               3.33217 |
| hyper_ai | leader_out | N0W1V1 |        0.970784 |          5.48421 |               6 |      0.948814 |               2.6358  |
| hyper_ai | leader_out | N1W0V0 |        0.921323 |         23.9053  |              34 |      0.337189 |              12.0349  |
| hyper_ai | leader_out | N1W0V1 |        0.953086 |         13.3368  |              30 |      0.323469 |              10.2381  |
| hyper_ai | leader_out | N1W1V0 |        0.921156 |         23.8     |              34 |      0.360071 |              11.9856  |
| hyper_ai | leader_out | N1W1V1 |        0.952756 |         13.2316  |              30 |      0.35943  |              10.2018  |

Holdings are marked before each rebalance. Effective positions equal inverse concentration of invested weights; holding count can include small residuals. Cash policy, execution thresholds, inverse-variance sizing, the CAGR/Sortino ranking, the 14-day return gate, fees and historical data are unchanged. N changes admission into sizing: at 360, all gate-passing candidates can enter, so the ranking does not impose a practical selection limit. V is a capacity assumption, not proof that depositing an entire historical vault TVL is practical.

## Mark-quality audit

| arm    |   funded_low_fresh_share |   stale_over_30d_end_mark_share |   stale_over_60d_end_mark_share |   kurtosis |
|:-------|-------------------------:|--------------------------------:|--------------------------------:|-----------:|
| N0W0V0 |               0.0108179  |                     2.65311e-19 |                     2.65311e-19 |   11.6082  |
| N0W0V1 |               0.00816771 |                     0           |                     0           |    7.93152 |
| N0W1V0 |               0.0044538  |                     2.52501e-20 |                     2.52501e-20 |   24.3474  |
| N0W1V1 |               0.00574004 |                     0           |                     0           |   31.4258  |
| N1W0V0 |               0.322236   |                     0.304401    |                     0.251197    |   62.6675  |
| N1W0V1 |               0.576427   |                     0.725194    |                     0.581772    |   69.1797  |
| N1W1V0 |               0.314268   |                     0.307957    |                     0.254132    |   63.0299  |
| N1W1V1 |               0.564121   |                     0.725759    |                     0.582054    |   69.3493  |

`funded_low_fresh_share` is the share of recorded positive trade value in vaults whose daily NAV moved on fewer than 30% of common-window days. Terminal stale-value shares reconstruct the remaining trade quantities at the frozen terminal share price; they are an exposure diagnostic, not a replacement for engine equity accounting. The marked-NAV kurtosis is reported on the same two-day portfolio-return series as the results table. High stale-value exposure means low measured volatility or drawdown cannot be read as a stable equity curve.

## Leading-vault NAV diagnostics

| address                                    | name                          | period   |   best_marked_day |   worst_marked_day | best_day            |   marked_daily_kurtosis |
|:-------------------------------------------|:------------------------------|:---------|------------------:|-------------------:|:--------------------|------------------------:|
| 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital               | hyper_ai |         0.189806  |        -0.185127   | 2026-06-04 00:00:00 |                 4.47815 |
| 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital               | full     |         0.313713  |        -0.256212   | 2025-10-15 00:00:00 |                 9.00868 |
| 0xcbbb26d5e622fb877e12745921ae8b1f820ffbed | intothecryptoverse.com        | hyper_ai |         0.963031  |        -0.535224   | 2026-06-25 00:00:00 |                68.5834  |
| 0xcbbb26d5e622fb877e12745921ae8b1f820ffbed | intothecryptoverse.com        | full     |         0.963031  |        -0.736587   | 2026-06-25 00:00:00 |                49.5017  |
| 0xdfc24b077bc1425ad1dea75bcb6f8158e10df303 | Hyperliquidity Provider (HLP) | hyper_ai |         0.0628375 |        -0.00368323 | 2026-02-01 00:00:00 |               185.323   |
| 0xdfc24b077bc1425ad1dea75bcb6f8158e10df303 | Hyperliquidity Provider (HLP) | full     |         0.0739024 |        -0.00798702 | 2025-10-15 00:00:00 |               176.962   |
| 0x1e37a337ed460039d1b15bd3bc489de789768d5e | Growi HF                      | hyper_ai |         0.325307  |        -0.239439   | 2026-02-06 00:00:00 |                59.7167  |
| 0x1e37a337ed460039d1b15bd3bc489de789768d5e | Growi HF                      | full     |         0.325307  |        -0.239439   | 2026-02-06 00:00:00 |                90.4004  |
| 0xcae0d1558b70b92ee9fd0acb20cb639c8c28ae69 | DOEZOE                        | hyper_ai |         0.331087  |        -0.241033   | 2026-05-05 00:00:00 |                10.8443  |
| 0xcae0d1558b70b92ee9fd0acb20cb639c8c28ae69 | DOEZOE                        | full     |         0.777941  |        -0.30408    | 2026-09-03 00:00:00 |                41.0762  |

These are marked NAV changes, not evidence of fresh daily observations. Forward filling preserves stale marks; jumps can incorporate several days of trading. See `leading-vault-nav.png`.

## Robustness of results

Vault metadata and prices refreshed since NB21. NB22 freezes both input files in its inputs directory and patches downloads to these files for every universe load. All 32 arms, including both endpoints, are freshly rerun on that snapshot. input-drift.csv records old/new hashes; parity.csv records equity differences against six historical endpoints, without assuming parity across different datasets. The maximum absolute equity difference across those six historical checks is $0.00000000. Other source and feature hashes are checked before execution. Historical endpoint drift is separate from allocation effects within this batch. Leader exclusion is a full resimulation with substitutes, not subtraction of realised profit. The full factorial is repeated under exclusion to expose changes driven by that known NAV jump; choosing the highest remaining row still does not provide out-of-sample evidence.

Individual positions, full per-vault P&L, curator flags, positive-P&L concentration, best-cycle BTC/ETH returns, kurtosis and mark-quality exposure are saved. Native position P&L covers the original engine window, which starts earlier than the common full curve slice. Closed positions funded above $100 with less than $1 returned: 0. The N arms materially increase sparse/stale-mark exposure, so their Sharpe and drawdown remain descriptive outputs, not evidence of a lower-risk allocation. A high Sharpe caused by a few large gains or stale-to-catch-up marks is not the steady-profit objective. Prior research documented the intothecryptoverse.com jump; excluding it does not establish that other contributors are free of the same issue.

No new hard quality filters or short-history sizing rules are introduced. This experiment answers which allocation-limit changes matter inside the frozen anchor, not whether young-vault selection now works or whether 20% CAGR is reliably achievable.
