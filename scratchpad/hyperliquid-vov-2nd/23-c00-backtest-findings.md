# C00 Hyperliquid vault strategy

Based on [NB20](20-backtest-c00-vs-v11.ipynb), using the outline of [NB160](../vault-of-vaults/160-backtest-hyperliquid-low-value-treasury-test.ipynb).

C00 ranks vaults with four clipped performance components and allocates to up to six vaults using a regularised 90-day risk estimate and a capacity waterfall. This notebook presents its fixed rules and compares them with `hyper-ai-v11.py`.

Each account starts with USD 150,000. The 2026 backtest runs from **1 January to 4 October 2026**; full history runs from **1 March 2023 to 7 October 2026**, with a partial final archive day. Both retain all preceding indicator warmup.

## Key new insights

All four accounts reproduce NB20's complete equity paths, successful trade sequences and key metrics. This notebook adds a single-strategy reporting layout; it introduces no new strategy configuration.

C00 earns more and has higher Sharpe in both periods. Its full-history drawdown is deeper. The comparison changes ranking, risk estimation and allocation together, so it does not identify which change produced the gain.

## Summary of results

| Period | Strategy | Final equity | CAGR | Sharpe | Maximum drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| 2026 | C00 | USD 212,376 | 58.59% | 2.474 | -6.36% |
| 2026 | V11 | USD 202,746 | 49.15% | 2.214 | -6.41% |
| Long | C00 | USD 420,882 | 33.13% | 1.651 | -9.94% |
| Long | V11 | USD 277,078 | 18.55% | 1.374 | -7.92% |

## Robustness of results

2026 C00: Realist Capital contributes 35.4% of positive vault profit. The best daily update is 6.46%; excess kurtosis is 11.0.

Long C00: Delta_01 contributes 17.2% of positive vault profit. The best daily update is 15.65%; excess kurtosis is 90.9.

The strongest NAV updates are compared with BTC and ETH over the actual observation intervals and checked against curator exclusions and quarantine. Sparse NAV can bunch returns, and the recorded NAV does not establish the live executable price. These are previously researched, overlapping periods with retrospective universe and guard selection.

Both strategies use the same partial-sale fee correction, entry-tax reset and final-proceeds funding. Charges model 10% of positive redemption profit plus a 0.1% capital allowance; that allowance is an inherited assumption. The v11 comparison runs the local module's rules with these shared research corrections, rather than reproducing recorded live decisions.
