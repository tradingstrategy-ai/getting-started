# Experiment 06 — three and four scoring inputs

[Executed notebook](06-opt-score-3-4-inputs.ipynb).

## Key new insights

- **3 inputs, highest 2026 CAGR:** Blend 46d / 3 inputs / 6m CAGR: 51.99% CAGR, 2.29 Sharpe and -7.29% drawdown. Highest Sharpe is 2.29 for Blend 46d / 3 inputs / 6m CAGR.
- **4 inputs, highest 2026 CAGR:** Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR: 52.30% CAGR, 2.23 Sharpe and -7.62% drawdown. Highest Sharpe is 2.30 for Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino.
- **Joint improvements against original v11:** 1 of 72 added-input configurations have higher 2026 CAGR and Sharpe with no worse drawdown. This does not establish unseen-time improvement.

- **Strongest balanced four-input candidate:** 48% 360-day CAGR + 32% 45-day Sortino + 10% 180-day CAGR + 10% 30-day Sortino, with legacy score clips (CAGR 100%, Sortino 3). It improves 2026 CAGR and Sharpe with slightly better drawdown than original v11; full-history drawdown is slightly worse (-8.08% versus -7.92%). These are four metric/window inputs but only two different metrics.
- **Extra windows matter in this replay:** collapsing the four-input leader to the same 58/42 metric balance on just 360-day CAGR/45-day Sortino reduces 2026 CAGR from 51.77% to 41.89% and Sharpe from 2.30 to 1.99. Full-history CAGR falls from 22.05% to 15.85% and Sharpe from 1.62 to 1.24. This diagnostic supports an incremental benefit from the additional windows, subject to search selection bias.

## Summary of results

### Selected comparisons — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Two-input controls, the best full-history candidates at each cardinality/objective, and the descriptive 2026 maxima. Every candidate uses six inverse-variance positions and unchanged selection. Equivalent paths can repeat.

| Configuration | Inputs | CAGR | Sharpe | Maximum drawdown | Mean cash weight | Trades |
| --- | --- | --- | --- | --- | --- | --- |
| Legacy 45d | 2 | 41.20% | 1.96 | -6.40% | 8.83% | 581 |
| Blend 46d | 2 | 41.38% | 2.12 | -4.85% | 7.43% | 583 |
| Blend 46d / 3 inputs / 1m Sortino | 3 | 39.26% | 2.05 | -4.93% | 6.87% | 647 |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 4 | 51.77% | 2.30 | -6.35% | 10.18% | 569 |
| Blend 46d / 3 inputs / 6m CAGR | 3 | 51.99% | 2.29 | -7.29% | 9.80% | 569 |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 4 | 52.30% | 2.23 | -7.62% | 8.41% | 593 |

<details><summary>Same configurations over full history — 2023-03-01 → 2026-10-05 (end exclusive, UTC)</summary>

Independent $150,000 starts; this period overlaps 2026 and is not a holdout.

| Configuration | Inputs | CAGR | Sharpe | Maximum drawdown | Mean cash weight | Trades |
| --- | --- | --- | --- | --- | --- | --- |
| Legacy 45d | 2 | 15.77% | 1.24 | -7.92% | 41.81% | 1074 |
| Blend 46d | 2 | 15.42% | 1.24 | -8.51% | 41.18% | 1060 |
| Blend 46d / 3 inputs / 1m Sortino | 3 | 17.45% | 1.31 | -9.50% | 42.52% | 1158 |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 4 | 22.05% | 1.62 | -8.08% | 43.71% | 1071 |
| Blend 46d / 3 inputs / 6m CAGR | 3 | 17.15% | 1.30 | -7.92% | 41.67% | 1063 |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 4 | 19.57% | 1.45 | -7.92% | 41.77% | 1088 |

</details>

## Robustness of results

All 74 configurations completed both periods. Three-input scores allocate 20% to one additional metric/window; four-input scores allocate 10% to each of two additional cells. Both keep 80% on the same 60/40 CAGR/Sortino core. This tests a predeclared add-on grid, not all combinations or optimal coefficients. Missing additional metrics propagate an unscored composite, as in the source; sparse long-window coverage can therefore change ranking materially. Full-history selections and 2026 maxima are labelled separately, with no claim of independent validation.

Source v11 and its exact two-input matrix match equity and complete trade ledgers in both periods. Position attribution reconciles to initial capital with a maximum residual of 5.82e-11 USD. The notebook reports best days, excess kurtosis, leading-vault concentration, curator annotations and matching BTC/ETH intervals. Fixed-ledger contributor removals are sensitivities, not executable exclusion backtests.

## Additional-signal availability — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Distinct non-zero coefficients do not guarantee distinct information. This audit measures undefined composite scores and each input's availability, clipping saturation and variation across funded vaults. Dollar fractions use requested final targets, not realised time-weighted exposure. Variation within the funded basket does not measure predictive power or the whole eligible universe.

| Configuration | Inputs | Funded target rows | Unscored target dollars |
| --- | --- | --- | --- |
| Legacy 45d | 2 | 834 | 0.0% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 4 | 834 | 0.0% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 4 | 834 | 0.0% |
| Blend 46d | 2 | 834 | 0.0% |
| Blend 46d / 3 inputs / 6m CAGR | 3 | 834 | 0.0% |
| Blend 46d / 3 inputs / 1m Sortino | 3 | 834 | 0.0% |

<details><summary>Per-input activity and clipping — 2026-01-01 → 2026-10-05 (end exclusive, UTC)</summary>

Each coefficient is meaningful by design, but a clipped input can be constant across the funded basket. Missing inputs follow the unchanged source unscored behaviour.

| Configuration | Feature | Coefficient | Available target dollars | At maximum score | Funded dates with varying score |
| --- | --- | --- | --- | --- | --- |
| Legacy 45d | 45d compatibility Sortino | 40.0% | 100.0% | 81.7% | 54.0% |
| Legacy 45d | 1y CAGR | 60.0% | 100.0% | 42.1% | 100.0% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 1m Sortino | 10.0% | 100.0% | 79.0% | 65.5% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 45d compatibility Sortino | 32.0% | 100.0% | 82.3% | 54.7% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 6m CAGR | 10.0% | 100.0% | 38.3% | 100.0% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 1y CAGR | 48.0% | 100.0% | 41.2% | 100.0% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 45d compatibility Sortino | 32.0% | 100.0% | 83.6% | 55.4% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 2m CAGR | 10.0% | 100.0% | 51.7% | 89.2% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 6m Sortino | 10.0% | 100.0% | 51.6% | 95.7% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 1y CAGR | 48.0% | 100.0% | 42.9% | 100.0% |
| Blend 46d | 46d Sortino | 40.0% | 100.0% | 58.8% | 95.0% |
| Blend 46d | 1y CAGR | 60.0% | 100.0% | 37.1% | 100.0% |
| Blend 46d / 3 inputs / 6m CAGR | 46d Sortino | 32.0% | 100.0% | 54.6% | 95.0% |
| Blend 46d / 3 inputs / 6m CAGR | 6m CAGR | 20.0% | 100.0% | 40.1% | 100.0% |
| Blend 46d / 3 inputs / 6m CAGR | 1y CAGR | 48.0% | 100.0% | 42.2% | 100.0% |
| Blend 46d / 3 inputs / 1m Sortino | 1m Sortino | 20.0% | 100.0% | 68.4% | 87.1% |
| Blend 46d / 3 inputs / 1m Sortino | 46d Sortino | 32.0% | 100.0% | 65.3% | 92.8% |
| Blend 46d / 3 inputs / 1m Sortino | 1y CAGR | 48.0% | 100.0% | 34.1% | 100.0% |

</details>

## Does an extra lookback add information? — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Collapse every additional CAGR/Sortino lookback into the original core lookback while preserving total weight on each metric, clipping recipes, sizing and selection. Other metric inputs stay unchanged. These post-selection diagnostic backtests distinguish an extra window from merely changing the CAGR/Sortino balance; they are exploratory and are not a new optimiser.

| Configuration | Original inputs | Collapsed inputs | Candidate CAGR | Collapsed CAGR | Candidate Sharpe | Collapsed Sharpe | Candidate max DD | Collapsed max DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Blend 46d / 3 inputs / 1m Sortino | 3 | 2 | 39.26% | 26.67% | 2.05 | 1.49 | -4.93% | -5.77% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 4 | 2 | 51.77% | 41.89% | 2.30 | 1.99 | -6.35% | -6.39% |
| Blend 46d / 3 inputs / 6m CAGR | 3 | 2 | 51.99% | 42.76% | 2.29 | 2.03 | -7.29% | -5.85% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 4 | 2 | 52.30% | 41.89% | 2.23 | 1.99 | -7.62% | -6.39% |

<details><summary>Same metric-mass controls over full history — 2023-03-01 → 2026-10-05 (end exclusive, UTC)</summary>

Independent fresh-start runs on the same inputs. Feature counts can remain above two when the original candidate contains an additional metric such as Sharpe.

| Configuration | Original inputs | Collapsed inputs | Candidate CAGR | Collapsed CAGR | Candidate Sharpe | Collapsed Sharpe | Candidate max DD | Collapsed max DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Blend 46d / 3 inputs / 1m Sortino | 3 | 2 | 17.45% | 16.00% | 1.31 | 1.21 | -9.50% | -8.77% |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 4 | 2 | 22.05% | 15.85% | 1.62 | 1.24 | -8.08% | -7.92% |
| Blend 46d / 3 inputs / 6m CAGR | 3 | 2 | 17.15% | 14.58% | 1.30 | 1.12 | -7.92% | -10.55% |
| Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR | 4 | 2 | 19.57% | 15.85% | 1.45 | 1.24 | -7.92% | -7.92% |

</details>

## Full-history profit concentration — 2023-03-01 → 2026-10-05 (end exclusive, UTC)

<details><summary>Best-day and leading-vault sensitivities for full-history-selected candidates</summary>

Two-input references and the full-history CAGR/Sharpe leaders at each input count. Position PnL is reconciled to equity; contributor removals retain the original trading ledger and are not exclusion backtests. Full-history curator annotations and BTC/ETH interval context are also saved to CSV.

| Configuration | Best day | Best day return | Leading vault | Leader share of positive vault PnL | Sharpe with best day zeroed | Sharpe without leader (fixed ledger) |
| --- | --- | --- | --- | --- | --- | --- |
| Legacy 45d | 2025-08-14 00:00:00 | 5.4% | Realist Capital | 17.3% | 1.15 | 1.05 |
| Blend 46d | 2025-08-14 00:00:00 | 5.7% | Delta_01 | 16.1% | 1.14 | 0.96 |
| Blend 46d / 3 inputs / 1m Sortino | 2025-10-15 00:00:00 | 7.7% | naze oppa degen nation | 14.5% | 1.20 | 1.11 |
| Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino | 2025-08-14 00:00:00 | 6.7% | Realist Capital | 15.7% | 1.53 | 1.46 |

</details>

## Interpretation and next research step

### Three and four inputs — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Experiment 04 already evaluated three- and four-input proposals, but only six of each per objective: 12 three-input and 12 four-input proposals in total. It also tested a dense 45-input equal score. Sizing and missing-score semantics varied during that search, and coefficient refinements stayed on the winning support. The two-input selected formulas were therefore not evidence that additional inputs could not help.

Experiment 06 holds sizing and selection fixed. The strongest balanced candidate is:

`0.48 × clip(CAGR360 / 1.0, 0, 1) + 0.32 × clip(Sortino45 / 3, 0, 1) + 0.10 × clip(CAGR180 / 1.0, 0, 1) + 0.10 × clip(Sortino30 / 3, 0, 1)`

The 45-day input uses the original source compatibility calculation. Its total metric balance is 58% CAGR / 42% Sortino. Source handling remains unchanged when a component is unavailable. All retained 2026 candidates have finite component scores on their funded target rows; missing additional features can still alter ranking elsewhere in the universe.

The extra windows outperform a two-input 58/42 control in both periods. They do not establish that four unrelated metrics are required: this winner uses two metrics over four windows. Additional Sharpe, maximum drawdown and Calmar inputs were included in the grid, but none led the full-history ranking. Among the funded targets, the leading candidate's 30-day Sortino is saturated at its maximum score for 79.0% of target dollars and differs across funded vaults on 65.5% of decision dates. Counting inputs alone therefore overstates the amount of independent information.

The leading four-input candidate still benefits from the 26 June jump. Its 2026 Sharpe falls from 2.30 to 2.00 when that day's return is zeroed, versus baseline 1.96 to 1.62. Realist Capital contributes 38.4% of positive vault PnL, versus 44.8% for the baseline. Removing its PnL on the fixed ledger leaves Sharpe 1.58, versus baseline 1.10. These are sensitivities, not tradable exclusion replays. Over full history, the candidate's best-day-zeroed Sharpe is 1.53 and its leader contributes 15.7% of positive vault profits. This is broader evidence than one 2026 jump, but it remains in-sample.

Next, refine the leading support's coefficients around 48/32/10/10 and compare against the best two-input controls using chronological training/validation windows. The initial four-input grid covers 18 of 153 possible pairs from the 18 extra features in each family, with fixed coefficients and 20% total added mass. It is a bounded screening exercise, not an exhaustive or global optimum. The long and short periods overlap; neither is an independent holdout.

### Saved-output inspection — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

All eight code cells completed without saved errors or warnings. All charts use 2026 with explicit period subtitles. Visual inspection found an overlapping scatter legend/colour bar and an equity axis labelled “0”; both were corrected. Allocation charts include the full-history four-input leader as well as the short-period maxima, with shared vault colours and a common dollar scale.

## Portfolio breadth follow-up

[Experiment 07](07-score-position-count-analysis.md) repeats all 74 supports with 7, 8 and 10 positions while retaining six-position references. The highlighted four-input score remains strongest at six positions in both periods. The two-input clipping blend improves at seven positions and offers a separate return/risk comparison. Position and associated rank limits change together; scoring weights and clips stay frozen.
