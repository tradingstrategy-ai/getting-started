# Experiment 04 — short-period report

[Executed notebook](04-opt-score-matrix.ipynb). Default period: 2026-01-01 → 2026-10-05 (end exclusive, UTC). Coefficients and detailed settings remain frozen from the full-history fit.

## Follow-up on input count

[Experiment 06](06-score-3-4-inputs-analysis.md) expands the three/four-input search while fixing selection and sizing. Its four-input leader improves both CAGR and Sharpe in the 2026 and full-history replays. The two-input winners below describe this earlier limited search, not a general conclusion about the optimal number of inputs.

## Key new insights

- **Default period:** every displayed performance result is a fresh 2026-01-01 → 2026-10-05 (end exclusive, UTC) replay with \$150,000 and no inherited positions.
- **Original v11:** 41.20% CAGR / 1.96 Sharpe / -6.40% max drawdown. Exact 360/45 compatibility reproduces its full equity path and all 581 trades.
- **Near-v6 360/46:** 40.58% CAGR / 1.94 Sharpe / -6.70% max drawdown. Its score window differs from the exact control by one day.
- **Highest observed grid CAGR:** 41.38% for 50/50 blend, 6 positions, inverse_variance, missing=True; Sharpe 2.12, drawdown -4.85%. This grid maximum does not change the frozen strategy settings.
- **Joint improvements:** 1 distinct qualifying configuration with higher CAGR, higher Sharpe and no worse drawdown than original v11 in 2026. The fitting period overlaps this replay, so these are in-sample observations.
- **Repaired-input benchmark:** Archived leader-share inputs and policy caps are restored. Source v11 reaches 41.20% CAGR versus the older 41.59%; its first 558 chronological trades match. The final equity gap is \$407.83 and is reconciled in restored-data-rerun-2026-10-07.md.
- **Feature redundancy:** same-lookback CAGR and Sharpe scores have Spearman correlations of 0.89–0.92 under requested clipping in 2026. The heatmaps compare raw metrics, clipping and lookbacks with pair counts; these are pooled feature correlations, not evidence of predictive performance.

## Summary of results

### Frozen matrices used in the replay — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Input coefficients were selected on full history and are held fixed for 2026. Identical coefficients with different clipping recipes can produce different scores; these rows are parameters, not performance.

| Family | Clips | Active cells | Period / metric weights |
| --- | --- | --- | --- |
| CAGR matrix | requested | 2 | 1y CAGR: 60%; 46d Sortino: 40% |
| Sharpe matrix | legacy | 2 | 1y CAGR: 60%; 46d Sortino: 40% |
| 50/50 blend | 50% requested + 50% legacy | 2 | 1y CAGR: 60%; 46d Sortino: 40% |
| 60/40 blend | 60% requested + 40% legacy | 2 | 1y CAGR: 60%; 46d Sortino: 40% |
| Compressed blend | 50% requested + 50% legacy | 2 | 1y CAGR: 60%; 46d Sortino: 40% |
| Dense equal matrix | requested | 45 | All 45 searchable cells equally weighted |
| 360/46 anchor | requested | 2 | 1y CAGR: 60%; 46d Sortino: 40% |

### Strategy performance side by side — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Compare distinct fresh 2026 equity/trade paths using the long-fitted strategy settings. Equivalent named aliases appear once. Drawdown is signed: values nearer zero are better.

| Family | Positions | Sizing | Missing | Clips | Allocator | Final equity (USD) | CAGR | Sharpe | Sortino | Max DD | Mean cash weight | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original v11 | 6 | inverse_variance | True | legacy | parent | \$194,521 | 41.20% | 1.96 | 3.43 | -6.40% | 8.83% | 581 |
| Near-v6 360/46 legacy | 6 | inverse_variance | True | legacy | parent | \$193,876 | 40.58% | 1.94 | 3.39 | -6.70% | 8.99% | 572 |
| CAGR matrix | 6 | equal | False | requested | parent | \$154,762 | 4.35% | 0.32 | 0.45 | -12.38% | 10.83% | 597 |
| 50/50 blend | 6 | equal | False | 50% requested + 50% legacy | parent | \$183,564 | 30.75% | 1.50 | 2.28 | -9.47% | 11.80% | 554 |
| 60/40 blend | 6 | equal | False | 60% requested + 40% legacy | parent | \$176,236 | 23.89% | 1.23 | 1.84 | -9.31% | 11.56% | 564 |
| Dense equal matrix | 4 | score | True | requested | parent | \$152,155 | 2.00% | 0.27 | 0.35 | -8.06% | 8.89% | 308 |
| CAGR matrix | 6 | equal | False | requested | accepted_dollar_cap | \$149,550 | -0.29% | 0.07 | 0.09 | -11.76% | 19.22% | 496 |
| 60/40 blend | 6 | equal | False | 60% requested + 40% legacy | accepted_dollar_cap | \$170,188 | 18.30% | 1.07 | 1.57 | -8.28% | 21.27% | 472 |
| Sharpe matrix | 6 | inverse_variance | True | legacy | accepted_dollar_cap | \$159,117 | 8.20% | 1.23 | 1.67 | -3.79% | 52.16% | 462 |

### Explicit 60/40 anchor options — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Hold six positions and ranking at 60% 360-day CAGR plus 40% 46-day Sortino. Compare only clipping profiles, sizing and missing flags in the short replay.

| Clips | Sizing | Missing | CAGR | Sharpe | Max DD | Mean cash weight |
| --- | --- | --- | --- | --- | --- | --- |
| requested | equal | False | 4.35% | 0.32 | -12.38% | 10.83% |
| requested | equal | True | 8.33% | 0.52 | -12.56% | 11.86% |
| requested | score | False | 2.23% | 0.21 | -12.68% | 9.89% |
| requested | score | True | 6.61% | 0.43 | -12.66% | 10.77% |
| requested | inverse_variance | False | 23.05% | 1.53 | -4.23% | 5.71% |
| requested | inverse_variance | True | 28.09% | 1.77 | -4.07% | 5.88% |
| legacy | equal | False | 23.71% | 1.14 | -9.95% | 11.89% |
| legacy | equal | True | 27.99% | 1.31 | -10.03% | 12.62% |
| legacy | score | False | 20.79% | 0.97 | -10.88% | 10.66% |
| legacy | score | True | 25.31% | 1.15 | -10.77% | 11.22% |
| legacy | inverse_variance | False | 35.81% | 1.77 | -6.79% | 8.68% |
| legacy | inverse_variance | True | 40.58% | 1.94 | -6.70% | 8.99% |

### Rolling metric availability — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Coverage counts complete positive-price windows across all vaults × replay dates, including dates before a vault has enough history. Undefined ratios use only complete windows as their denominator; flat windows are vault-day counts. Lookback labels are indicator windows, not reporting periods.

| Period | Coverage | Undefined ratio within complete windows | Flat complete vault-days |
| --- | --- | --- | --- |
| 1m | 81.94% | 27.76% | 30729 |
| 46d | 79.08% | 24.30% | 26320 |
| 2m | 76.46% | 21.95% | 23006 |
| 3m | 70.48% | 17.54% | 16873 |
| 4m | 64.05% | 13.51% | 11683 |
| 6m | 50.31% | 6.38% | 4007 |
| 9m | 34.04% | 2.75% | 996 |
| 1y | 22.78% | 2.33% | 646 |
| 2y | 3.73% | 0.98% | 0 |

### Profit concentration and return sensitivities — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Identify the leading vault and strongest booked day in each 2026 path. Removing their PnL retains the original trades and is a sensitivity, not a new executable backtest.

| Run | Leading vault | Leading vault profit (USD) | Leading vault share of positive vault profits | Best day | Best day return | Sharpe with best day set to zero | Sharpe without leader PnL (fixed ledger) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 50/50 blend / parent | Realist Capital | \$13,980 | 26.49% | 2026-06-26 | 4.37% | 1.24 | 0.98 |
| 60/40 blend / parent | Realist Capital | \$12,424 | 27.43% | 2026-06-26 | 4.58% | 0.94 | 0.74 |
| CAGR matrix / parent | Realist Capital | \$8,669 | 29.75% | 2026-06-26 | 6.40% | -0.15 | -0.12 |
| Dense equal matrix / parent | Hyperliquidity Provider (HLP) | \$2,234 | 39.90% | 2026-01-07 | 3.06% | -0.21 | 0.05 |
| Original v11 / parent | Realist Capital | \$24,196 | 44.77% | 2026-06-26 | 6.89% | 1.62 | 1.10 |
| Near-v6 360/46 legacy / parent | Realist Capital | \$25,883 | 48.48% | 2026-06-26 | 6.87% | 1.60 | 0.99 |
| CAGR matrix / accepted_dollar_cap | Goon Edging | \$5,187 | 22.78% | 2026-06-26 | 4.16% | -0.28 | -0.25 |
| Sharpe matrix / accepted_dollar_cap | pmalt | \$3,824 | 28.42% | 2026-02-28 | 1.87% | 0.90 | 0.75 |
| 60/40 blend / accepted_dollar_cap | Realist Capital | \$8,789 | 23.10% | 2026-06-26 | 4.16% | 0.78 | 0.68 |

### Information available when funding positions — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Fractions weight target dollars across 2026 decisions, not realised time-weighted exposure. Unscored funding can occur under missing=True. Original v11 is absent because it has no matrix allocation ledger.

| Run | Funded target rows | Unscored funding | Missing 360d history | Missing 2y history | Flat 1m marks |
| --- | --- | --- | --- | --- | --- |
| 50/50 blend / parent | 834 | 0.00% | 0.00% | 74.66% | 0.00% |
| 60/40 blend / parent | 834 | 0.00% | 0.00% | 74.33% | 0.00% |
| CAGR matrix / parent | 834 | 0.00% | 0.00% | 74.87% | 0.00% |
| Dense equal matrix / parent | 555 | 0.00% | 0.00% | 0.00% | 0.00% |
| Near-v6 360/46 legacy / parent | 834 | 0.00% | 0.00% | 73.79% | 0.00% |
| CAGR matrix / accepted_dollar_cap | 834 | 0.00% | 0.00% | 76.63% | 0.00% |
| Sharpe matrix / accepted_dollar_cap | 834 | 0.00% | 0.00% | 64.03% | 0.00% |
| 60/40 blend / accepted_dollar_cap | 834 | 0.00% | 0.00% | 76.71% | 0.00% |

### Compression candidates — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Compare completed short-period compression replays at six equal-weight positions and missing=False. The diagnostic tolerance is within one percentage point CAGR and 0.10 Sharpe of the full blend; the frozen compression choice is not reselected.

| Active cells | CAGR | Sharpe | Max DD | Within 2026 tolerance |
| --- | --- | --- | --- | --- |
| 1 | 24.60% | 1.04 | -13.58% | False |
| 2 | 30.75% | 1.50 | -9.47% | True |

### Calmar clipping sensitivity — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Compare caps 3/5/10 using six positions and the frozen sizing, missing flag and score recipe. These matrices have no active Calmar term, so changing the cap cannot alter their score or trade path.

| Family | Calmar cap | CAGR | Sharpe | Max DD |
| --- | --- | --- | --- | --- |
| CAGR matrix | 3.0 | 4.35% | 0.32 | -12.38% |
| CAGR matrix | 5.0 | 4.35% | 0.32 | -12.38% |
| CAGR matrix | 10.0 | 4.35% | 0.32 | -12.38% |
| Sharpe matrix | 3.0 | 40.58% | 1.94 | -6.70% |
| Sharpe matrix | 5.0 | 40.58% | 1.94 | -6.70% |
| Sharpe matrix | 10.0 | 40.58% | 1.94 | -6.70% |
| 50/50 blend | 3.0 | 30.75% | 1.50 | -9.47% |
| 50/50 blend | 5.0 | 30.75% | 1.50 | -9.47% |
| 50/50 blend | 10.0 | 30.75% | 1.50 | -9.47% |
| 60/40 blend | 3.0 | 23.89% | 1.23 | -9.31% |
| 60/40 blend | 5.0 | 23.89% | 1.23 | -9.31% |
| 60/40 blend | 10.0 | 23.89% | 1.23 | -9.31% |

## Robustness and interpretation

All 26 code cells completed. The short-period manifest records 194 configuration evaluations. Position PnL reconciles to equity minus starting capital, with a largest residual of 4.73e-11 USD. Source scoring, selection and execution rules are unchanged. Full-history fitting and reference artefacts remain available separately.

The long fitting window includes 2026: this is exploratory in-sample analysis, not independent validation. Frozen families and detailed settings are not reselected using the short-period rankings. Missing history, flat NAV marks, current-universe assumptions and incomplete historical deposit-state data remain limitations.
