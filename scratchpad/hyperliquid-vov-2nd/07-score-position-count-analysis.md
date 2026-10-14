# Experiment 07 — scoring inputs and portfolio breadth

[Executed notebook](07-opt-score-position-count.ipynb).

## Key new insights

- **Frozen highlighted score, six-position reference:** 51.77% CAGR, 2.30 Sharpe and -6.35% maximum drawdown in 2026; this matches experiment 06.
- **Highest CAGR among wider versions of that score:** N=7 gives 30.85% CAGR, 1.58 Sharpe and -6.42% drawdown. Highest Sharpe among wider versions is 1.58 at N=7. 0 of the three wider focal variants improve all three metrics against N=6.
- **Highest observed 2026 CAGR in the complete wider grid:** Blend 46d / 7 positions: 47.93% CAGR, 2.46 Sharpe and -4.71% drawdown. Highest observed Sharpe is 2.46 for Blend 46d / 7 positions. These are descriptive search maxima.
- **Matched breadth effects:** 47 of 222 wider score/breadth combinations have higher CAGR and Sharpe with no worse drawdown than their own six-position support. This is not a probability of success or an independent significance test.
- **Highlighted-score conclusion:** all three wider portfolios have lower 2026 CAGR and Sharpe than six positions. Lower cash alone is not an improvement; retain six positions as the reference for this frozen score.
- **Useful alternative, not the highlighted four-input formula:** two-input Blend 46d at seven positions gives 47.93% CAGR, 2.46 Sharpe and -4.71% drawdown in 2026. Full-history CAGR is 18.40%, Sharpe 1.39 and drawdown -8.08%. It improves its own six-position clipping-blend reference in both periods, but does not exceed the four-input six-position CAGR.

## Summary of results

### Highlighted four-input score — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Hold 48% 360-day CAGR, 32% 45-day source-compatible Sortino, 10% 180-day CAGR and 10% 30-day Sortino fixed with legacy clips. Only the position limits and associated entry/exit ranks change. All portfolios start at \$150,000 with no inherited positions. “Maximum vaults held” is realised breadth; the position parameter is a limit.

| Positions | CAGR | Sharpe | Maximum drawdown | Mean cash weight | Maximum vaults held | Trades |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 51.77% | 2.30 | -6.35% | 10.18% | 6 | 569 |
| 7 | 30.85% | 1.58 | -6.42% | 6.21% | 7 | 726 |
| 8 | 16.24% | 1.04 | -6.57% | 4.35% | 8 | 824 |
| 10 | -3.01% | -0.28 | -6.79% | 2.83% | 10 | 1027 |

<details><summary>Same frozen score over full history — 2023-03-01 → 2026-10-05 (end exclusive, UTC)</summary>

Independent fresh-start replays on the same inputs. Full history overlaps 2026; it is not a holdout.

| Positions | CAGR | Sharpe | Maximum drawdown | Mean cash weight | Maximum vaults held | Trades |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 22.05% | 1.62 | -8.08% | 43.71% | 6 | 1071 |
| 7 | 17.30% | 1.26 | -9.99% | 40.13% | 7 | 1247 |
| 8 | 14.88% | 1.12 | -11.91% | 37.73% | 8 | 1417 |
| 10 | 8.49% | 0.70 | -17.42% | 34.00% | 10 | 1847 |

</details>

### Observed scoring leaders at each breadth — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

<details><summary>Highest observed CAGR and Sharpe supports, including the six-position reference</summary>

Supports are chosen by inspecting 2026, so these are descriptive comparisons. Coefficients and clips remain the predeclared experiment 06 settings.

| Objective | Positions | Score | Inputs | CAGR | Sharpe | Maximum drawdown | Mean cash weight |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CAGR | 6 | Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 4 | 52.30% | 2.23 | -7.62% | 8.41% |
| Sharpe | 6 | Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 4 | 51.77% | 2.30 | -6.35% | 10.18% |
| CAGR | 7 | Blend 46d | 2 | 47.93% | 2.46 | -4.71% | 5.03% |
| Sharpe | 7 | Blend 46d | 2 | 47.93% | 2.46 | -4.71% | 5.03% |
| CAGR | 8 | Blend 46d / 4 inputs / 3m CAGR + 1y Sharpe | 4 | 29.92% | 1.99 | -5.16% | 4.78% |
| Sharpe | 8 | Blend 46d / 4 inputs / 3m CAGR + 1y Sharpe | 4 | 29.92% | 1.99 | -5.16% | 4.78% |
| CAGR | 10 | Legacy 45d / 4 inputs / 1y Sortino + 3m CAGR | 4 | 14.52% | 1.46 | -4.12% | 3.81% |
| Sharpe | 10 | Legacy 45d / 4 inputs / 1y Sortino + 3m CAGR | 4 | 14.52% | 1.46 | -4.12% | 3.81% |

</details>

### Matched effects across all 74 supports — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Compare each support against itself with six positions. Changes in percentage metrics are percentage points. Positive cash-weight change means more cash held; each breadth arm contains 74 paired comparisons.

| Positions | Median CAGR change | Median Sharpe change | Median cash-weight change | Joint improvements |
| --- | --- | --- | --- | --- |
| 7 | -3.05% | +0.03 | -2.43% | 29 |
| 8 | -12.94% | -0.40 | -3.85% | 12 |
| 10 | -24.81% | -0.87 | -3.96% | 6 |

## Robustness of results

All 296 configurations completed both periods: 444 new wider-position replays and 148 verified six-position references. Source v11 and the exact two-input wrapper match complete equity and every trade in both periods. Every six-position result matches experiment 06's metrics. Realised vault counts never exceed their assigned limits. Position attribution reconciles to equity with a maximum residual of 2.04e-10 USD.

The selector algorithm remains the source implementation, but its cardinality-related entry/exit ranks change from 6/8 to N/(N+2). The 33% concentration cap, 98% allocation target, sizing lookback, clipping recipes, missing-score handling, admission checks and rebalancing costs remain fixed. Wider breadth is therefore not a standalone change in diversification: it also changes which ranks can enter and be retained. The engine follows the existing parent allocation and pinning rules rather than guaranteeing exactly N funded vaults on every decision.

- **Fixed score, N=6:** leading vault Realist Capital contributes 38.4% of positive vault profits. Best day 2026-06-26 returns 6.80%; excess kurtosis 12.08. Sharpe is 2.00 with that return zeroed and 1.58 after removing the leader PnL on the fixed ledger.
- **Fixed score, N=7:** leading vault Realist Capital contributes 34.4% of positive vault profits. Best day 2026-06-26 returns 5.62%; excess kurtosis 11.76. Sharpe is 1.25 with that return zeroed and 0.81 after removing the leader PnL on the fixed ledger.
- **Fixed score, N=8:** leading vault Realist Capital contributes 23.6% of positive vault profits. Best day 2026-06-26 returns 4.23%; excess kurtosis 15.55. Sharpe is 0.72 with that return zeroed and 0.58 after removing the leader PnL on the fixed ledger.
- **Fixed score, N=10:** leading vault 22Cap contributes 17.7% of positive vault profits. Best day 2026-08-23 returns 2.32%; excess kurtosis 17.01. Sharpe is -0.63 with that return zeroed and -0.54 after removing the leader PnL on the fixed ledger.

On 24 June, Realist Capital supplies 99.7% of positive vault PnL in the focal six-position portfolio, while BTC and ETH return -0.91% and -2.33% over the matching interval. It is not curator-excluded or quarantined at that date. These gains are vault-specific rather than a broad market rise; short or hedged vault profits can still be valid. The leading-vault and best-day sensitivities above quantify the dependence without applying post-hoc exclusions.

### Full-history sensitivity of the highlighted score — 2023-03-01 → 2026-10-05 (end exclusive, UTC)

<details><summary>Best-day and leading-vault sensitivities</summary>

These remove booked returns or contributor PnL without rerunning selection; they are sensitivities, not tradable exclusion strategies. Curator annotations and matching BTC/ETH returns are saved in the notebook and detailed artefacts.

| Positions | Leading vault | Leader share of positive PnL | Best day | Best day return | Sharpe with best day zeroed | Sharpe without leader |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | Realist Capital | 15.7% | 2025-08-14 | 6.71% | 1.53 | 1.46 |
| 7 | Realist Capital | 14.9% | 2025-08-14 | 6.50% | 1.16 | 1.06 |
| 8 | Realist Capital | 11.1% | 2025-08-14 | 6.41% | 1.02 | 0.95 |
| 10 | Hyperliquidity Provider (HLP) | 16.5% | 2025-08-14 | 6.12% | 0.58 | 0.46 |

</details>

The full and short histories overlap and have already been inspected. The support grid and fixed coefficient mass are bounded; these results do not demonstrate an unseen-time optimum. Current membership/guard assumptions, carried NAV observations, weak historical permission coverage and concentration in individual vaults remain limitations. Default charts and tables use 2026 with explicit period titles. Generated caches, logs and states are ignored; reviewable findings and saved notebook outputs remain outside generated artefact directories.

## How breadth changes the highlighted score — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

### Realised holdings and funded scores

Mean holdings are calculated across daily carried portfolio valuations. Score averages use requested final target dollars, not realised time-weighted exposure. Removing Pepe vs PnL retains the original trading ledger and is a sensitivity, not an exclusion backtest. Cash is realised; missing component scores follow source semantics. A lower funded score is a ranking description, not a proof of lower future returns.

| Positions | Mean realised vaults | Maximum realised vaults | Mean cash weight | Target-dollar-weighted score | Unscored target dollars | Final total vault PnL (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 5.99 | 6 | 10.18% | 0.82 | 0.00% | \$55,430 |
| 7 | 6.96 | 7 | 6.21% | 0.78 | 0.00% | \$33,638 |
| 8 | 7.86 | 8 | 4.35% | 0.74 | 0.00% | \$17,912 |
| 10 | 9.51 | 10 | 2.83% | 0.68 | 0.00% | \$-3,574 |

### Sensitivity to Pepe vs

The seven-position variant deposits \$22,983 on 8 July and redeems \$15,772 on 10 July, losing \$7,211 as modelled NAV falls by about 31%. It has no current curator exclusion or entry-date quarantine flag. Remove all this vault's PnL from the fixed trading ledger to see how much this one loss explains. The seven-position Sharpe rises to 1.97 and CAGR to 37.69%, still below six positions; no exclusion is applied to the strategy results.

| Positions | Pepe vs PnL (USD) | CAGR without Pepe vs (fixed ledger) | Sharpe without Pepe vs (fixed ledger) |
| --- | --- | --- | --- |
| 6 | \$0 | 51.77% | 2.30 |
| 7 | \$-7,211 | 37.69% | 1.97 |
| 8 | \$-3,077 | 19.06% | 1.22 |
| 10 | \$-544 | -2.54% | -0.23 |

### Shared vaults versus additional holdings

Reconcile the final PnL difference against six positions into vaults traded by both variants and vaults traded only by the wider variant. Shared-vault PnL changes include entry/exit timing, different position sizes and compounding; they cannot be attributed to simple weight dilution alone.

| Positions | Total PnL change (USD) | PnL change in shared vaults (USD) | Wider-only vault PnL (USD) |
| --- | --- | --- | --- |
| 7 | \$-21,792 | \$-11,597 | \$-10,195 |
| 8 | \$-37,518 | \$-32,425 | \$-5,093 |
| 10 | \$-59,004 | \$-58,491 | \$-513 |

### Largest losses of profit contribution

<details><summary>Five largest adverse vault-PnL changes at each wider breadth</summary>

Compare each fixed-score portfolio with six positions. Mean weights are time averages over the full period, so brief large exposures can look small in this column.

| Positions | Vault | Six-position PnL (USD) | Wider PnL (USD) | PnL change (USD) | Six-position mean weight | Wider mean weight |
| --- | --- | --- | --- | --- | --- | --- |
| 7 | Pepe vs  | \$0 | \$-7,211 | \$-7,211 | 0.00% | 0.09% |
| 7 | Realist Capital | \$24,749 | \$18,718 | \$-6,032 | 8.48% | 5.72% |
| 7 | 500 to 1M | \$0 | \$-3,766 | \$-3,766 | 0.00% | 0.34% |
| 7 | pmalt | \$7,576 | \$4,773 | \$-2,803 | 13.07% | 10.44% |
| 7 | Delta_01 | \$948 | \$-1,703 | \$-2,651 | 0.41% | 0.37% |
| 8 | Realist Capital | \$24,749 | \$8,688 | \$-16,061 | 8.48% | 3.76% |
| 8 | pmalt | \$7,576 | \$1,181 | \$-6,395 | 13.07% | 7.67% |
| 8 | DOEZOE | \$11,137 | \$5,685 | \$-5,452 | 1.35% | 1.46% |
| 8 | 500 to 1M | \$0 | \$-3,876 | \$-3,876 | 0.00% | 0.23% |
| 8 | Hyperrr | \$5,233 | \$1,760 | \$-3,473 | 3.10% | 1.23% |
| 10 | Realist Capital | \$24,749 | \$820 | \$-23,929 | 8.48% | 1.91% |
| 10 | DOEZOE | \$11,137 | \$1,588 | \$-9,549 | 1.35% | 0.49% |
| 10 | pmalt | \$7,576 | \$538 | \$-7,038 | 13.07% | 4.15% |
| 10 | Hyperrr | \$5,233 | \$564 | \$-4,669 | 3.10% | 0.61% |
| 10 | Citadel | \$2,879 | \$-821 | \$-3,700 | 14.36% | 12.50% |

</details>

### Largest individual position losses and curator flags

<details><summary>Eight largest losing positions across the four focal variants</summary>

Position profits use the executed ledger and marked holdings. Existing curator flags are descriptive; a false flag does not certify data quality. No post-hoc exclusions are applied to reported strategy results.

| Positions | Vault | Opened | Closed | Final profit (USD) | Curator excluded | Quarantined at entry |
| --- | --- | --- | --- | --- | --- | --- |
| 7 | Pepe vs  | 2026-07-08 | 2026-07-10 | \$-7,211 | False | False |
| 8 | DOEZOE | 2026-09-04 | 2026-09-14 | \$-3,899 | False | False |
| 6 | Realist Capital | 2026-06-06 | 2026-06-16 | \$-3,697 | False | False |
| 8 | 500 to 1M | 2026-03-08 | 2026-03-14 | \$-3,509 | False | False |
| 7 | Realist Capital | 2026-06-12 | 2026-06-16 | \$-3,388 | False | False |
| 10 | songer1993.hl | 2026-09-22 | 2026-09-24 | \$-3,315 | False | False |
| 8 | songer1993.hl | 2026-09-22 | 2026-09-24 | \$-3,315 | False | False |
| 6 | Goon Edging | 2026-02-22 | 2026-03-06 | \$-3,272 | False | False |

</details>

### Saved-output inspection — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

All seven code cells completed, with nine saved PNG charts and no saved errors or warnings. Visual inspection covered every chart. Allocation legends initially clipped the final vault names; a common chart height based on the largest legend now shows every name. Heatmap titles explicitly identify percentage units, and the two-input breadth controls have their own described table. Charts and default performance tables use 2026; full-history evidence is collapsed.
