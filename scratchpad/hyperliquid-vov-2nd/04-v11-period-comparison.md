# Experiment 04 — v11 period comparison

> **Latest follow-up, 7 October 2026:** producer PR #1634 restores archived leader shares and policy caps; trading-strategy #255 and trade-executor #1671 retain them without inventing an independent capacity clock. Fresh 01–05 reruns use the restored publication. Source v11 now reaches **41.20% CAGR**, versus the earlier 41.59%; the first 558 chronological trades match. See [the restored-data rerun](restored-data-rerun-2026-10-07.md). The findings below refer to earlier input generations.

## Finding

The other agent's v11 result is reproducible. A fresh direct ``hyper-ai-v11.py`` replay gives **$194,928.64 final equity, 41.59% CAGR, 2.00 daily Sharpe and −6.40% maximum drawdown**, with **101 positions, 582 trades and 139 two-day cycles**. All nine published reference checks pass at their displayed precision. The existing [01 initial notebook](01-initial.ipynb) already contains the same short-period reproduction.

Experiment 04's original v11 control reports a different window: all available vault history, requested 1 March 2023 through 5 October 2026 exclusive. Its initial engine snapshot is 28 February 2023; its first trade is 31 May 2023. The other agent starts with fresh capital on 1 January 2026. Both last value the portfolio on 4 October 2026; 5 October is the exclusive end boundary in both implementations.

## Side-by-side metrics

| Run | Starting state | Final equity | Cumulative return | CAGR | Sharpe | Sortino | Max DD | Calmar |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fresh v11, January–October 2026 | $150,000 fresh deposit | $194,928.64 | 30.08% | 41.59% | 2.00 | 3.56 | -6.40% | 6.50 |
| Experiment 04 v11, full history | $150,000 fresh deposit in 2023 | $254,510.70 | 69.67% | 15.82% | 1.25 | 1.91 | -7.92% | 2.00 |
| Long replay, 2026 segment | $202,612.55 inherited equity and six positions | $254,510.70 | 25.61% | 35.20% | 1.94 | 3.31 | -5.71% | 6.17 |

The long segment is a slice of the original trading path, not a fresh backtest or a reset to $150,000. It includes the return from the final December valuation into the first January valuation.

## Why the figures differ

1. **The full window contains weaker earlier returns.** Annual compounded returns of the long replay are −3.66% in partial 2023, +23.51% in 2024, +13.52% in 2025 and +25.61% in January–October 2026. The full run earns +69.67% over approximately 3.6 years, which annualises to 15.82%. Cash-only dates before the first trade are included. The fresh 2026 run earns +30.08% over 277 daily return observations, which annualises to 41.59%.
2. **Restarting changes the trading path.** On entry into 2026, the long run holds Crypto Trading Channel, Dobutsu - Alpha Club, 22Cap, Hyperrr, -VectorZero- and Mahamor. They retain their position histories and cost bases. On the first January decision the fresh run buys all six; the inherited run sells some Hyperrr and buys more -VectorZero-. Rank hysteresis, trade bands, TVL limits and profit-dependent redemption costs can therefore produce different allocations and returns even over overlapping dates. The observed 2026 comparison is 25.61% versus 30.08% cumulative return; it does not isolate the individual contribution of each mechanism.
3. **The original control and matrix variants are different rows.** Experiment 04's original v11 control uses the exact source formula: 60% 360-day CAGR plus 40% 45-day Sortino, clipped at 100% and 3, with 90-day inverse variance and source missingness. Its exact compatibility matrix reproduces all 1,074 long-period trades and the equity curve. The near-v6 row changes Sortino to 46 days, producing 15.49% long-period CAGR. Requested clipping is instead 50% / 7; selected blend rows use mixed clip profiles, equal position sizing and missing=False. Those rows should not be read as the original v11 replay.

## Rules, data and metric conventions

The direct replay imports the same local v11 source as experiments 01 and 04. Its SHA-256 is ``5ed8a4c00f1edb14ae9af40ac3d94d3622587445921d1e92ef33f9676761ffbe``. It uses the current Trading Strategy vault dataset, 514 selected vaults and the same v10 Lagoon guard record. V11 retains six core/capacity positions, entry rank 6, exit rank 8 and its source allocation, admission and fee rules.

The other notebook's hard-six v10 parameters disable the extension by setting both core and capacity to six. Comparing its current source with v11 confirms the same trading rules under those parameters; other differences are identifiers, renamed helpers/environment variables, the default end boundary and the assertion tolerance discussed below. V10's deployed 6+4 extension row is a separate strategy configuration.

Both notebooks calculate metrics from ``calculate_returns(equity).resample("1D").sum(min_count=1).fillna(0)`` with 365-day annualisation. This is not a daily-versus-two-day Sharpe mismatch. The short run has 277 daily return observations; the full history has 1,315 and 658 decision valuations. Annualisation stays 365 even when the trailing CAGR scoring window is 360 days.

**Starting-equity convention:** the nominal short deposit is $150,000, but its first marked, net-redeemable portfolio equity after initial allocation is $149,853. The reported +30.08% compounds returns from that marked equity; final equity divided by the nominal deposit gives +29.95%. This convention is shared with the other agent and explains no discrepancy between the reproductions. The full run's first marked equity is $150,000 while still entirely in cash.

## Local tolerance edit

The only current uncommitted v11 change replaces the quantity-reconciliation assertion with ``math.isclose(..., rel_tol=1e-12, abs_tol=1e-8)``. It changes neither the cost-basis updates nor their returned value. Experiment 01 documents this as an execution fix for floating-point accumulation at very large share counts in the long history. The fresh short replay with the edit still matches the published reference. This comparison did not modify or commit the strategy.

## Evidence and limitations

The fresh three-cell audit notebook and machine-readable comparison, reference checks, annual returns and inherited-position evidence are saved under the ignored ``_artifacts-matrix-long-v2/`` directory. All audit cells completed without errors or warning output. The full-history state is the saved experiment 04 source-control state, verified against its metrics and source fingerprint; it was not regenerated for this audit.

Today's universe/guard snapshot and deposit-state history beginning 11 April 2026 remain shared historical assumptions. None of these comparisons establishes out-of-sample performance.

## Same-period v6-like candidate check

The frozen near-v6 candidate was also replayed independently over 1 January–5 October 2026 exclusive, starting with $150,000. It uses 60% 360-day CAGR plus 40% 46-day Sortino, legacy clips 100% / 3, six positions, 90-day inverse variance, missing=True and unchanged v11 selection/execution. Its only rule difference from the exact compatibility configuration is 46 versus 45 days.

| Configuration | Final equity | CAGR | Sharpe | Sortino | Max DD | Trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original v11 | $194,928.64 | 41.59% | 2.00 | 3.56 | -6.40% | 582 |
| Exact v6 scoring / v11 selection | $194,928.64 | 41.59% | 2.00 | 3.56 | -6.40% | 582 |
| Near-v6 candidate, 46-day Sortino | $194,284.21 | 40.97% | 1.97 | 3.53 | -6.70% | 573 |

The 46-day candidate trails by 0.62 percentage points of CAGR, 0.023 Sharpe and $644.43 ending equity. Its drawdown is 0.29 percentage points deeper. The exact 45-day compatibility matrix matches source v11's complete short equity curve and all 582 trades. This establishes v6 scoring/sizing under v11 selection, not native v6 selection.
