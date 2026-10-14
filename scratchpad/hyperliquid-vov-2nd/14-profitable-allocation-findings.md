# Experiment 14 — profitable allocation findings


Pricing: **as_of_observation**. Five fixed allocation methods, fresh $150,000 accounts, the original four-input ranking and six-position limit.


## Results — 2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC)

2026: profit leader **A**. Best challenger **B** changes profit by **$-1,342**, CAGR by -1.31 percentage points, and drawdown by -0.19 percentage points versus A.


| Arm   | Method                                         | Net profit (USD)   | CAGR   |   Sharpe | Maximum drawdown   | Mean cash weight   |
|:------|:-----------------------------------------------|:-------------------|:-------|---------:|:-------------------|:-------------------|
| A     | Source variance / original allocation          | $55,430            | 51.77% |     2.3  | -6.35%             | 10.18%             |
| B     | Source variance / simultaneous allocation      | $54,089            | 50.46% |     2.25 | -6.54%             | 9.88%              |
| C     | Regularised variance / original allocation     | $51,111            | 47.56% |     2.12 | -6.93%             | 10.08%             |
| D     | Regularised variance / simultaneous allocation | $50,120            | 46.60% |     2.09 | -7.05%             | 9.67%              |
| G     | Regularised downside / original allocation     | $50,819            | 47.28% |     2.11 | -7.72%             | 10.03%             |


## Results — 2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial)

Long: profit leader **G**. Best challenger **G** changes profit by **$+51,687**, CAGR by +5.32 percentage points, and drawdown by -3.46 percentage points versus A.


| Arm   | Method                                         | Net profit (USD)   | CAGR   |   Sharpe | Maximum drawdown   | Mean cash weight   |
|:------|:-----------------------------------------------|:-------------------|:-------|---------:|:-------------------|:-------------------|
| A     | Source variance / original allocation          | $162,108           | 22.53% |     1.65 | -7.92%             | 43.95%             |
| B     | Source variance / simultaneous allocation      | $163,522           | 22.69% |     1.63 | -7.92%             | 43.66%             |
| C     | Regularised variance / original allocation     | $210,443           | 27.53% |     1.56 | -10.73%            | 40.62%             |
| D     | Regularised variance / simultaneous allocation | $211,823           | 27.66% |     1.54 | -10.63%            | 38.85%             |
| G     | Regularised downside / original allocation     | $213,794           | 27.85% |     1.54 | -11.37%            | 40.32%             |


## Hypothesis verdicts

Allocator: 2026 $-1,342; full history $+1,414. The profit hypothesis is supported over full history and rejected for the fresh 2026 comparison.

Regularisation: 2026 $-4,319; full history $+48,335. The profit hypothesis is supported over full history and rejected for the fresh 2026 comparison.

Downside vs regular: 2026 $-292; full history $+3,352. The profit hypothesis is supported over full history and rejected for the fresh 2026 comparison.

Redistribution alone contributes little: most of the full-history improvement is already present with the regularised estimator package under the original allocator. That package also changes historical support, NAV filling, flooring and missing-risk fallback; this does not isolate shrinkage alone. Downside sizing adds only about $3,352 over that regularised control and has worse drawdown in both primary periods. Keep A as the 2026 reference; G is a historical profit challenger, not an established replacement.

Allocator and regularisation effects are the paired engine differences below. G−C tests the downside estimator package, including its downside peer prior. Positive incremental dollars support a profit benefit for that period; disagreement between periods indicates year dependence.


| Period   | Comparison                        | Profit difference (USD)   | CAGR difference (pp)   | Drawdown difference (pp)   |
|:---------|:----------------------------------|:--------------------------|:-----------------------|:---------------------------|
| 2026     | Allocator                         | $-1,342                   | -1.31                  | -0.19                      |
| 2026     | Regularisation                    | $-4,319                   | -4.21                  | -0.58                      |
| 2026     | Downside vs regular               | $-292                     | -0.28                  | -0.79                      |
| 2026     | Downside vs source                | $-4,611                   | -4.49                  | -1.38                      |
| 2026     | Allocator × estimator interaction | $351                      | —                      | —                          |
| Long     | Allocator                         | $1,414                    | 0.15                   | 0.00                       |
| Long     | Regularisation                    | $48,335                   | 4.99                   | -2.82                      |
| Long     | Downside vs regular               | $3,352                    | 0.33                   | -0.64                      |
| Long     | Downside vs source                | $51,687                   | 5.32                   | -3.46                      |
| Long     | Allocator × estimator interaction | $-34                      | —                      | —                          |


## Sparse-price sensitivity

| Period   | Arm   | Net profit (USD)   | CAGR   |   Sharpe | Maximum drawdown   |
|:---------|:------|:-------------------|:-------|---------:|:-------------------|
| 2026     | A     | $57,198            | 53.49% |     2.37 | -6.34%             |
| 2026     | B     | $56,101            | 52.42% |     2.33 | -6.54%             |
| Long     | A     | $98,640            | 15.05% |     1.13 | -16.86%            |
| Long     | G     | $139,821           | 20.04% |     1.22 | -14.74%            |


## Robustness and limitations

With trading deferred when NAV observations are older than two days, A earns $57,198 versus B $56,101 in 2026. Over full history, G earns $139,821 versus A $98,640: a $41,181 lead, with maximum drawdown -14.74% versus -16.86%. This supports a historical profit advantage under this conservative assumption, but is not a ranking of all five methods under that alternative execution rule.

The saved reference trace found 24 successful trades using a later intraday daily-close mark. Primary fills and valuation now use recorded NAV observations at or before the query timestamp; score/risk inputs remain completed T−1 buckets. This assumes observation timestamps identify effective NAV times, independently of archive rewrites.

A carried last-known NAV is not independent evidence of the actual deposit/redemption price. The quote-freshness sensitivity defers trading when observations are older than a source two-day cycle. It changes trading availability and can change holdings; it is deliberately conservative, not a proof of the true fill price. Permission and capacity history are otherwise inherited unchanged.

The long replay contains early empty-universe/cash periods and previously searched years. Fresh 2026 ends 4 October; carried long-run 2026 ends 7 October. No independent forward validation is claimed. The redemption allowance is estimated and turnover differs between arms. The inherited source records a net-of-fee mid price for partial Hypercore trims and applies the sell fee again to planned execution; this existing convention is retained for reference comparability. The recorded redemption-cost column is the source estimate, not a separately verified total economic fee. Gross-NAV timing checks undo the partial-trim fee adjustment before comparing observations.


## Next action

Retain A as the current-period allocation reference. Regularisation is the economically material historical lever; downside sizing supplies a small additional historical gain with a risk cost. A single later-data comparison of A and a frozen regularised/downside challenger is more useful than a wider grid. The two-day quote-freshness sensitivity improves A’s 2026 profit by $1,768 with similar drawdown; investigate this as an execution-data-quality lead, rather than treating an archive gap as a real vault closure. The full-history quote-freshness sensitivity preserves G’s profit lead while changing drawdown materially, so execution assumptions remain part of the result.
