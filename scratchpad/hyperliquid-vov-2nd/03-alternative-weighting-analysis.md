# Experiment 03 — restored-data rerun

## Restored-data results — 7 October 2026

All 20 short/full-history executions completed. Source and cap controls reproduce notebooks 01 and 02. Highest observed short-period CAGR is 41.20% for Short — Baseline redistribution — Original inverse variance, with 1.96 Sharpe and -6.40% maximum drawdown.

### Strategy comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Fresh engine backtests on the same pinned publication and merged readers, each starting with $150,000. Full-history runs are retained separately in the saved outputs.

| Strategy | Final equity (USD) | CAGR | Sharpe | Maximum drawdown | Trades | Mean cash |
| --- | --- | --- | --- | --- | --- | --- |
| Short — Baseline redistribution — Original inverse variance | \$194,520.81 | 41.20% | 1.96 | -6.40% | 581 | 8.83% |
| Short — Dollar cap — Original inverse variance | \$160,350.69 | 9.31% | 1.31 | -4.22% | 474 | 51.32% |
| Short — Baseline redistribution — P1: 50/50 inverse volatility + equal | \$187,263.59 | 34.28% | 1.49 | -9.11% | 595 | 12.43% |
| Short — Dollar cap — P1: 50/50 inverse volatility + equal | \$177,349.75 | 24.93% | 1.49 | -8.17% | 571 | 23.76% |
| Short — Baseline redistribution — P2: Equal weights | \$188,032.51 | 35.01% | 1.44 | -9.53% | 541 | 14.29% |
| Short — Dollar cap — P2: Equal weights | \$182,873.01 | 30.10% | 1.51 | -9.35% | 473 | 23.47% |
| Short — Baseline redistribution — P3: Regularised inverse volatility | \$188,482.08 | 35.43% | 1.61 | -7.69% | 595 | 10.79% |
| Short — Dollar cap — P3: Regularised inverse volatility | \$169,228.81 | 17.40% | 1.28 | -6.68% | 571 | 25.56% |
| Short — Baseline redistribution — P4: Correlation-aware risk budget | \$188,575.25 | 35.52% | 1.62 | -7.84% | 599 | 10.45% |
| Short — Dollar cap — P4: Correlation-aware risk budget | \$171,296.33 | 19.30% | 1.39 | -6.71% | 575 | 25.39% |

Both periods completed. Historical benchmark differences are separate from mandatory equality between controls on identical inputs. See [the rerun report](restored-data-rerun-2026-10-07.md) for input and clock provenance.

<details>
<summary>Earlier analysis on the previous publication</summary>

# Experiment 03 — alternative vault weighting

Parents: [01-initial.ipynb](01-initial.ipynb) and [02-backtest-accepted-dollar-cap.ipynb](02-backtest-accepted-dollar-cap.ipynb), using the same `hyper-ai-v11.py` source, guard record, data snapshot and execution framework.

[Executed notebook](03-backtest-alternative-weighting.ipynb).

## Repaired-data results — 7 October 2026

The repaired source gives 33.47% CAGR, 1.63 Sharpe and −9.04% drawdown. This differs from the earlier 41.59% benchmark; the [capacity diagnostic](repaired-data-rerun-2026-10-07.md) explains most of the difference. Historical benchmark checks report differences; mandatory controls on the same repaired inputs pass. Original inverse variance has the highest observed CAGR and Sharpe among these ten short-period treatments. All 20 short/full-history executions completed; source and cap controls match notebooks 01 and 02.

### Strategy comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Fresh engine executions on the same pinned repaired inputs, with $150,000 initial equity. This is the default short period; full-history runs remain in the saved outputs and isolated artefacts.

| Strategy                                                               | Final equity (USD)   | CAGR   |   Sharpe | Maximum drawdown   |   Trades |
|:-----------------------------------------------------------------------|:---------------------|:-------|---------:|:-------------------|---------:|
| Short — Baseline redistribution — Original inverse variance            | $186,418.03          | 33.47% |     1.63 | -9.04%             |      601 |
| Short — Dollar cap — Original inverse variance                         | $156,878.83          | 6.19%  |     0.91 | -5.29%             |      513 |
| Short — Baseline redistribution — P1: 50/50 inverse volatility + equal | $183,690.58          | 30.90% |     1.35 | -9.97%             |      620 |
| Short — Dollar cap — P1: 50/50 inverse volatility + equal              | $173,766.75          | 21.60% |     1.32 | -8.32%             |      591 |
| Short — Baseline redistribution — P2: Equal weights                    | $186,020.64          | 33.10% |     1.37 | -9.97%             |      568 |
| Short — Dollar cap — P2: Equal weights                                 | $180,229.61          | 27.62% |     1.4  | -9.36%             |      495 |
| Short — Baseline redistribution — P3: Regularised inverse volatility   | $182,511.86          | 29.79% |     1.38 | -9.59%             |      621 |
| Short — Dollar cap — P3: Regularised inverse volatility                | $164,925.19          | 13.47% |     1.02 | -7.20%             |      600 |
| Short — Baseline redistribution — P4: Correlation-aware risk budget    | $183,107.35          | 30.35% |     1.41 | -9.48%             |      618 |
| Short — Dollar cap — P4: Correlation-aware risk budget                 | $167,318.55          | 15.65% |     1.15 | -7.18%             |      598 |

Both backtesting periods completed without saved errors or warnings. Strategy parameters are unchanged. Legacy permission times remain inferred where independent receipts are unavailable.


<details>
<summary>Historical analysis before the 7 October repaired-data rerun</summary>

These earlier figures used the previous input generation and are retained as dated research history. The updated tables above are the current results.

# Experiment 03 — alternative weighting results

[Executed notebook](03-backtest-alternative-weighting.ipynb). Short: 1 January–5 October 2026; long: 1 March 2023–5 October 2026, ends exclusive.

## Key new insights

- **Short baseline:** 0/4 alternatives beat the original inverse-variance Sharpe. Best alternative by Sharpe is P4: Correlation-aware risk budget: 35.91% CAGR, 1.65 Sharpe and -7.84% maximum drawdown; original control: 41.59%, 2.00 and -6.40%.
- **Long baseline:** 0/4 alternatives beat the original inverse-variance Sharpe. Best alternative by Sharpe is P3: Regularised inverse volatility: 15.03% CAGR, 1.15 Sharpe and -7.92% maximum drawdown; original control: 15.82%, 1.25 and -7.92%.
- **Short dollar cap:** best CAGR is P2: Equal weights, 30.27% versus 9.33% for the original cap. Mean cash falls from 51.39% to 23.45%; Sharpe changes from 1.31 to 1.52, and drawdown from -4.22% to -9.35%. Improved deployment comes with more observed risk.
- **Long dollar cap:** best CAGR is P2: Equal weights, 11.52% versus 2.10% for the original cap. Mean cash falls from 70.57% to 51.15%; Sharpe changes from 0.36 to 0.98, and drawdown from -7.92% to -9.29%. Improved deployment comes with more observed risk.
- The results favour retaining the current inverse-variance-plus-redistribution parent among these fixed candidates. Improving the failed dollar-cap control does not establish an improvement over experiment 01. No method was tuned after seeing results.
- Equal risk budgets apply to **requested** exposures. TVL caps, concentration limits, blocked top-ups and cleanup change the accepted portfolio; the risk-budget diagnostics quantify this distortion. The regularised methods also change volatility estimation and its floor, so these are whole-policy comparisons rather than an isolated exponent ablation.
- The hook preserves the source-selected core on each pre-trade state. In these runs, all four baseline alternatives matched the original baseline’s selected sets on all 139 short and 612 long sizing dates. Dollar-cap alternatives differed from the original cap on 13/139 short and 112/612 long sizing dates, so their results include effects from evolving holdings and later selections. Gross turnover and modelled fees are shown alongside performance; neither fewer trades nor flatter requested weights alone proves better sizing.

## Summary of results

All 20 backtests completed. Daily-resampled Sharpe matches the parent convention; the detailed tables also show native-cycle Sharpe.

| Period | Allocator | Weighting | CAGR | Sharpe | Max DD | Mean cash | Final equity |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Short | Baseline redistribution | Original inverse variance | 41.59% | 2.00 | -6.40% | 8.83% | $194,928.64 |
| Short | Dollar cap | Original inverse variance | 9.33% | 1.31 | -4.22% | 51.39% | $160,369.21 |
| Short | Baseline redistribution | P1: 50/50 inverse volatility + equal | 34.66% | 1.51 | -9.11% | 12.43% | $187,672.33 |
| Short | Dollar cap | P1: 50/50 inverse volatility + equal | 25.04% | 1.50 | -8.17% | 23.75% | $177,475.29 |
| Short | Baseline redistribution | P2: Equal weights | 35.39% | 1.47 | -9.53% | 14.29% | $188,440.32 |
| Short | Dollar cap | P2: Equal weights | 30.27% | 1.52 | -9.35% | 23.45% | $183,057.26 |
| Short | Baseline redistribution | P3: Regularised inverse volatility | 35.82% | 1.63 | -7.69% | 10.79% | $188,889.90 |
| Short | Dollar cap | P3: Regularised inverse volatility | 17.47% | 1.28 | -6.68% | 25.55% | $169,298.56 |
| Short | Baseline redistribution | P4: Correlation-aware risk budget | 35.91% | 1.65 | -7.84% | 10.45% | $188,982.98 |
| Short | Dollar cap | P4: Correlation-aware risk budget | 19.46% | 1.40 | -6.71% | 25.39% | $171,466.22 |
| Long | Baseline redistribution | Original inverse variance | 15.82% | 1.25 | -7.92% | 41.81% | $254,510.70 |
| Long | Dollar cap | Original inverse variance | 2.10% | 0.36 | -7.92% | 70.57% | $161,658.47 |
| Long | Baseline redistribution | P1: 50/50 inverse volatility + equal | 14.28% | 1.07 | -8.87% | 43.84% | $242,538.94 |
| Long | Dollar cap | P1: 50/50 inverse volatility + equal | 10.41% | 1.01 | -8.01% | 51.95% | $214,266.49 |
| Long | Baseline redistribution | P2: Equal weights | 13.62% | 1.00 | -11.22% | 46.28% | $237,536.93 |
| Long | Dollar cap | P2: Equal weights | 11.52% | 0.98 | -9.29% | 51.15% | $222,078.07 |
| Long | Baseline redistribution | P3: Regularised inverse volatility | 15.03% | 1.15 | -7.92% | 42.58% | $248,333.88 |
| Long | Dollar cap | P3: Regularised inverse volatility | 8.25% | 0.94 | -7.92% | 56.31% | $199,508.23 |
| Long | Baseline redistribution | P4: Correlation-aware risk budget | 14.30% | 1.09 | -7.92% | 42.48% | $242,655.19 |
| Long | Dollar cap | P4: Correlation-aware risk budget | 8.09% | 0.91 | -7.92% | 56.39% | $198,454.11 |

## Robustness of results

**Replication and execution.** All 30 code cells completed without saved warnings or errors. Both experiment 01 controls pass the ten saved checks per period, and both original-cap controls pass five checks per period: 30 replication comparisons. All capped targets satisfy final target ≤ accepted allocation ≤ original request; all runs hold at most six vaults. Alternative risk samples end strictly before each decision. These checks validate the saved run; the notebook does not establish historical point-in-time universe availability.

**Position attribution.** Every run’s position-flow/marked-value PnL reconciles to equity minus initial capital; largest residual is $0.0000000001. Top vaults, top three positions and the three largest portfolio days are shown with curator/exclusion/quarantine annotations. BTC/ETH comparisons use the same interval between portfolio snapshots; a return bucket can contain two days of movement.

**Short / Baseline redistribution, best alternative by Sharpe (P4: Correlation-aware risk budget).** Leading vault Realist Capital earns $21,409.63, 43.06% of positive vault PnL. Removing its PnL on the fixed ledger changes CAGR to 15.93% and Sharpe to 0.95. The largest positive difference against the matching inverse-variance control is Goon Edging, $1,243.68, against a net final-equity difference of $-5,945.66. Contributor-removal sensitivities leave the original sizing/trades in place; they are not exclusion backtests.

**Short / Dollar cap, best alternative by Sharpe (P2: Equal weights).** Leading vault Realist Capital earns $12,706.13, 29.01% of positive vault PnL. Removing its PnL on the fixed ledger changes CAGR to 18.45% and Sharpe to 1.07. The largest positive difference against the matching inverse-variance control is Realist Capital, $11,144.57, against a net final-equity difference of $22,688.05. Contributor-removal sensitivities leave the original sizing/trades in place; they are not exclusion backtests.

**Long / Baseline redistribution, best alternative by Sharpe (P3: Regularised inverse volatility).** Leading vault Delta_01 earns $26,437.40, 18.66% of positive vault PnL. Removing its PnL on the fixed ledger changes CAGR to 11.49% and Sharpe to 0.85. The largest positive difference against the matching inverse-variance control is Delta_01, $1,517.32, against a net final-equity difference of $-6,176.82. Contributor-removal sensitivities leave the original sizing/trades in place; they are not exclusion backtests.

**Long / Dollar cap, best alternative by Sharpe (P1: 50/50 inverse volatility + equal).** Leading vault Hyperliquidity Provider (HLP) earns $13,451.60, 13.29% of positive vault PnL. Removing its PnL on the fixed ledger changes CAGR to 8.44% and Sharpe to 0.81. The largest positive difference against the matching inverse-variance control is Realist Capital, $11,411.72, against a net final-equity difference of $52,608.01. Contributor-removal sensitivities leave the original sizing/trades in place; they are not exclusion backtests.

**Extreme-return sensitivity.** Highest excess kurtosis is 263.84 in Long — Dollar cap — Original inverse variance. Its best day is 2025-10-15 (3.34%); Growi HF supplies $3,299.66, 60.78% of positive vault PnL. BTC/ETH move -1.68% / -0.66% over the matching snapshot interval. Setting that one portfolio return to zero changes CAGR to 1.17% and Sharpe to 0.22. This gain is concentrated in a vault event while the market references fell over the matching interval.

**Capacity versus risk parity.** Maximum requested risk-budget error is 9.87e-09; mean absolute accepted risk-budget deviations range from 7.36% to 18.72% across runs. These are fractions of estimated variance contribution under the regularised covariance, not realised economic risk or guaranteed drawdown limits.

**Historical scope and interpretation.** The two windows overlap and provide no independent out-of-sample validation. Today’s selected universe and static guard permissions apply to the historical replay, and deposit-state history before 11 April 2026 is unavailable. The engine starts the long run with cash on 28 February 2023; long-window mean cash includes the early idle period. Partial boundary quarters are labelled in the heatmap section. Non-flat observation counts cannot distinguish carried NAV from genuinely stable observations. True covariance risk can be understated by sparse or smoothed prices. These fixed regularisation settings have not been assessed on an untouched future window.

**Conclusion.** No tested alternative improves the baseline Sharpe in either window. The dollar-cap alternatives improve deployment and CAGR but do not beat the original baseline. Retain the parent pending a separate predeclared comparison; a useful next diagnostic would isolate plain inverse volatility, variance shrinkage and floor changes before introducing another combined policy.
</details>


</details>
