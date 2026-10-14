# Experiment 17 — capital allocation findings

## Key new insights

- **2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC):** M10 (One-decision rank-exit confirmation) leads net profit at **\$55,676**, **52.01% CAGR**, **2.15 Sharpe**, **-10.25% maximum drawdown**; **\$+669** versus exact C-W.
- **2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial):** M05 (Core + four score-first overflow) leads net profit at **\$296,112**, **35.30% CAGR**, **1.65 Sharpe**, **-12.12% maximum drawdown**; **\$+49,476** versus exact C-W.
- **Positive net-profit differences in both periods:** none. Only gains in both would support a broadly better historical policy; these periods overlap and provide no independent validation.
- The selected six-name capacity ceiling cannot be repaired by a different within-basket weighting alone. Overflow changes the set of exposures, whereas greedy/joint score allocation changes both selection and concentration; compare their realised economics rather than the score proxy.
- Primary and corrected-fee results are separate. Sparse marks, retrospective guard/inventory, estimated fees and contributor concentration remain material assumptions.

## Summary of results

Incremental net profit relative to the matched C-W benchmark, with the same primary fee convention. Positive values indicate higher profit; the two periods overlap.

| Arm   |   2026 profit delta (USD) |   Full-history profit delta (USD) |
|:------|--------------------------:|----------------------------------:|
| M00   |                         0 |                                 0 |
| M01   |                    -4,507 |                            -2,394 |
| M02   |                    -5,503 |                           -35,836 |
| M03   |                   -10,701 |                           -29,009 |
| M04   |                   -11,398 |                           -25,855 |
| M05   |                   -11,598 |                            49,476 |
| M06   |                   -11,598 |                           -32,825 |
| M07   |                    -2,233 |                           -17,572 |
| M08   |                   -18,603 |                          -148,749 |
| M09   |                   -14,241 |                           -32,216 |
| M10   |                       669 |                           -40,056 |
| M11   |                   -19,809 |                          -152,162 |
| M12   |                   -11,428 |                            16,871 |
| M13   |                   -64,862 |                          -140,887 |

- **Missing-score screen:** M05 full-history CAGR is 35.30% versus 27.86% for otherwise matched scored-only overflow M06. Both are 40.13% / 40.13% in fresh 2026. Missing composite scores are not a demonstrated profitability veto; young-history and undefined-metric exposure must be separated.
- **Exit delay:** M10 is 52.01% CAGR / -10.25% drawdown in fresh 2026, but 27.15% / -10.72% over full history. The small short-period profit gain is regime-dependent and carries more risk.


### What the allocation contrasts teach us

- **M05, fresh 2026:** September cash 4.8% versus 48.9%, with **\$-11,598** incremental net profit. Better deployment did not establish better economics.
- **M08, fresh 2026:** September cash 1.8% versus 48.9%, with **\$-18,603** incremental net profit. Better deployment did not establish better economics.
- **M11, fresh 2026:** September cash 1.8% versus 48.9%, with **\$-19,809** incremental net profit. Better deployment did not establish better economics.
- **M13, fresh 2026:** September cash 3.5% versus 48.9%, with **\$-64,862** incremental net profit. Better deployment did not establish better economics.

- **The exit-delay lead fails the fee check:** corrected 2026 C-W is **58.58% CAGR**, versus **57.17%** for M10. The primary small lead reverses when both share corrected partial-trim costs. Corrected full-history M05 is **37.73%** versus **33.13%** for C-W, so its long-period lead persists. These are sensitivity figures, not replacements for the legacy comparisons.
- **Full-history overflow dependence:** the largest incremental vault contributor is **[ Systemic Strategies ] L/S Grids**, **\$+38,137**, versus **\$+49,476** total M05−M00 profit. This is a vault-level whole-account difference, not exact overflow-role PnL; position changes elsewhere can offset it.


## Robustness of results

All 28 registered accounts completed, and exact C-W metrics match saved NB16 in both periods. Successful trades were checked against known as-of NAV, position PnL reconciled to equity, and holdings respected each method’s slot limit. Protected overflow target checks and core-first executable funding checks are recorded. NAV forward filling starts after inception; actual update counts govern risk confidence. A price series being calculable does not establish fills during archive gaps.

The audit covers 23,492 successful fills, 14,892 core-target equality checks and 2,718 core-first funding checks. Maximum position-PnL/equity reconciliation residual is below \$0.000000001. M11 uses the declared safe M01 fallback on four decisions (one in fresh 2026 and three in full history) after a solver target fails executable-domain checks. Its realised results therefore include these fallbacks; they do not establish a globally optimal executable portfolio on every date.

The inherited partial-trim fee model is retained for primary parity and corrected for the benchmark/profit-leader union. Open performance liabilities and gross-versus-estimated-liquidation equity are reported separately. Contributor/tail tables check leading vaults and BTC/ETH intervals rather than treating all large updates as market-wide gains. Both periods have been researched and overlap. Freeze a small profit/risk shortlist for prospective observation before adopting an allocation method.


## Reproducibility

Generated run manifest and full diagnostic ledgers: `_artifacts-restored-2026-10-07/17/da419d3284ae4516ac93b58665b5e31e755f9c2151dc158d4a89242d68ceb3f9`. Generated artefacts are ignored; notebook outputs contain reviewable tables and charts.
