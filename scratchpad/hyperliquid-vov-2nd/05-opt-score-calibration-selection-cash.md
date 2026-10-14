# Experiment 05 — scoring, selection and cash deployment

[Executed notebook](05-opt-score-calibration-selection-cash.ipynb).

## Key new insights

- **Same-data benchmark:** the fresh original-formula control has 41.20% CAGR, 1.96 Sharpe and -6.40% maximum drawdown. It reproduces source v11 equity and every trade.
- **Highest observed CAGR:** Feasible entrants gives 41.83% CAGR, 1.99 Sharpe and -6.39% drawdown. This ranking excludes tie-seed diagnostics.
- **Highest observed Sharpe:** Blend 46d gives 2.12 Sharpe and 41.38% CAGR. 3 tested treatment rows improve CAGR and Sharpe with no worse drawdown than the current control; equivalent paths may repeat.
- **Clipping ties:** 39.1% of baseline funded observations have maximum composite score; 63.3% of decisions fund at least two such vaults. Tie ordering must be treated as a robustness check.
- **Benchmark discrepancy:** Restored leader-share/cap inputs and merged readers return 41.20% CAGR versus the earlier 41.59%, closing most of the preceding 33.47% gap. The first 558 chronological trades match the earlier source exactly; remaining differences start in September. See the restored-data rerun report.

## Summary of results

### Matched strategy comparisons — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Completed real engine backtests with six inverse-variance positions. Includes the source-equivalent control, predeclared scoring/cash pairs and the strongest observed treatment; tie seeds are excluded from winner selection. All metrics are net of source-modelled costs.

| Configuration | CAGR | Sharpe | Maximum drawdown | Mean cash weight | Trades |
| --- | --- | --- | --- | --- | --- |
| Hard C1 S3 | 41.20% | 1.96 | -6.40% | 8.83% | 581 |
| Blend 46d | 41.38% | 2.12 | -4.85% | 7.43% | 583 |
| Smooth C1 S3 | 31.64% | 1.65 | -5.28% | 5.42% | 628 |
| Hard C1 S3 / refill | 39.56% | 1.88 | -6.44% | 8.40% | 585 |
| Blend 46d / refill | 40.00% | 2.05 | -5.08% | 7.12% | 584 |
| Smooth C1 S3 / refill | 29.65% | 1.54 | -6.01% | 5.24% | 629 |
| Feasible entrants | 41.83% | 1.99 | -6.39% | 8.83% | 571 |

## Robustness of results

The 18 score calibrations, 11 mechanism diagnostics and 6 predeclared full-history confirmations completed. Default tables and charts use the 2026 period; full-history performance is retained separately. Results are exploratory comparisons over previously inspected history, not an untouched holdout. Feature labels use strictly future NAV outcomes, are censored at the report end and are never used to tune backtest parameters in this notebook. Feature IC uncertainty bands resample overlapping decision dates in blocks and remain exploratory.

Source replication passes the equity and complete-ledger checks. Every backtest holds at most six vaults. Refill targets remain within the source fresh budget and concentration/TVL ceilings; deposit checks, pinned holdings and ordinary execution bands can prevent intended dollars from becoming realised exposure. Position attribution reconciles to equity with a largest residual of 8.00e-11 USD.

- **Hard C1 S3:** leading vault Realist Capital supplies 44.8% of positive vault profits. Best day 2026-06-26 returns 6.89%; excess kurtosis 13.67. Zeroing that return gives Sharpe 1.62; removing the leader PnL on the fixed ledger gives Sharpe 1.10. These sensitivities retain the original trading path.
- **Feasible entrants:** leading vault Realist Capital supplies 44.8% of positive vault profits. Best day 2026-06-26 returns 6.88%; excess kurtosis 13.68. Zeroing that return gives Sharpe 1.65; removing the leader PnL on the fixed ledger gives Sharpe 1.13. These sensitivities retain the original trading path.
- **Blend 46d:** leading vault Realist Capital supplies 31.6% of positive vault profits. Best day 2026-06-26 returns 6.77%; excess kurtosis 16.75. Zeroing that return gives Sharpe 1.79; removing the leader PnL on the fixed ledger gives Sharpe 1.49. These sensitivities retain the original trading path.

- **Hard C1 S3 / refill:** mean recovered target is 0.36% of fresh budget, on 18 decisions; realised mean cash is 8.40%. A target-budget recovery is not a guaranteed reduction in realised cash.
- **Blend 46d / refill:** mean recovered target is 0.28% of fresh budget, on 12 decisions; realised mean cash is 7.12%. A target-budget recovery is not a guaranteed reduction in realised cash.
- **Smooth C1 S3 / refill:** mean recovered target is 0.14% of fresh budget, on 11 decisions; realised mean cash is 5.24%. A target-budget recovery is not a guaranteed reduction in realised cash.

The expanded attribution tables show the largest days alongside matching Binance BTC/ETH intervals and curator annotations. Gross NAV labels do not include the strategy's redemption costs. Flat or carried NAV, weak long-window coverage, current membership/guard assumptions and incomplete historical deposit permissions can affect feature diagnostics. The clip, selector and tie grid is bounded; no claim of a global optimum is made.
