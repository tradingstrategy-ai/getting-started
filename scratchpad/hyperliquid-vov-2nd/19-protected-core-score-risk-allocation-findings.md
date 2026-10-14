# Experiment 19 — protected core with score and risk sizing

## Key new insights

The experiment preserves the source-authoritative C-W core and adds limited absolute tickets. Extra holdings influence future account wealth, fees and core decisions; incremental account profit is not a causal sleeve-only return.

## 2026 results

2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC). Fresh \$150,000; common corrected entry valuation.

| Method | Net profit | CAGR | Sharpe | Max drawdown | September cash |
| --- | ---: | ---: | ---: | ---: | ---: |
| C00 | \$62,376 | 58.59% | 2.47 | -6.36% | 49.75% |
| E00 | \$58,251 | 54.53% | 2.31 | -7.30% | 36.78% |
| R00 | \$58,355 | 54.63% | 2.32 | -7.29% | 37.44% |
| S00 | \$58,106 | 54.39% | 2.31 | -7.29% | 37.71% |
| RS00 | \$58,219 | 54.50% | 2.32 | -7.29% | 38.26% |
| RS01 | \$62,631 | 58.84% | 2.48 | -6.45% | 42.68% |
| NRS00 | \$60,250 | 56.49% | 2.35 | -7.29% | 33.80% |
| RS08 | \$59,091 | 55.35% | 2.35 | -7.27% | 43.39% |
| RS12 | \$58,359 | 54.64% | 2.32 | -7.29% | 34.47% |
| GF25 | \$58,141 | 54.42% | 2.31 | -7.29% | 38.67% |
| CAP10 | \$60,942 | 57.17% | 2.42 | -6.72% | 45.19% |

CAGR leader: **RS01**. Sharpe leader: **RS01**. RS00 versus C00 changes net profit by \$-4,157, CAGR by -4.09 percentage points and Sharpe by -0.16.
Holding versus resizing combined tickets: RS01 − RS00 profit \$+4,411. Normalising versus absolute resize: NRS00 − RS01 \$-2,381.

## Full-history results

2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial). Fresh \$150,000; common corrected entry valuation.

| Method | Net profit | CAGR | Sharpe | Max drawdown | September cash |
| --- | ---: | ---: | ---: | ---: | ---: |
| C00 | \$270,882 | 33.13% | 1.65 | -9.94% | 63.17% |
| E00 | \$275,406 | 33.52% | 1.67 | -9.94% | 52.23% |
| R00 | \$274,127 | 33.41% | 1.66 | -9.94% | 52.09% |
| S00 | \$274,995 | 33.49% | 1.66 | -9.94% | 53.11% |
| RS00 | \$272,980 | 33.31% | 1.66 | -9.94% | 53.00% |
| RS01 | \$276,951 | 33.66% | 1.67 | -9.94% | 56.16% |
| NRS00 | \$270,027 | 33.05% | 1.64 | -9.94% | 50.77% |
| RS08 | \$274,121 | 33.41% | 1.66 | -9.94% | 57.37% |
| RS12 | \$272,186 | 33.24% | 1.65 | -9.94% | 49.58% |
| GF25 | \$272,424 | 33.26% | 1.66 | -9.94% | 53.45% |
| CAP10 | \$269,352 | 33.00% | 1.65 | -9.94% | 58.43% |

CAGR leader: **RS01**. Sharpe leader: **RS01**. RS00 versus C00 changes net profit by \$+2,098, CAGR by +0.18 percentage points and Sharpe by +0.01.
Holding versus resizing combined tickets: RS01 − RS00 profit \$+3,972. Normalising versus absolute resize: NRS00 − RS01 \$-6,924.

## Hypotheses and interpretation

- **H1 — Extra breadth:** E00 − C00 \$-4,125 in 2026 / \$+4,524 full history; mixed across histories. These are package comparisons, not independent statistical confirmations.
- **H2 — Combined score/risk versus risk alone:** RS00 − R00 \$-136 in 2026 / \$-1,147 full history; rejected on both inspected histories. These are package comparisons, not independent statistical confirmations.
- **H3 — Absolute versus normalised resizing:** RS01 − NRS00 \$+2,381 in 2026 / \$+6,924 full history; supported on both inspected histories. These are package comparisons, not independent statistical confirmations.
- **H4 — Hold versus resize:** RS00 − RS01 \$-4,411 in 2026 / \$-3,972 full history; rejected on both inspected histories. These are package comparisons, not independent statistical confirmations.
- **H5 — Twelve versus eight slots:** RS12 − RS08 \$-732 in 2026 / \$-1,935 full history; rejected on both inspected histories. These are package comparisons, not independent statistical confirmations.

**H6 — local assumptions:** lower floor GF25 − RS00 profit \$-78 / \$-555; smaller-cap CAP10 − RS00 \$+2,722 / \$-3,627. Neither floor nor caps are established as optimal.

**Practical shortlist:** RS01 leads inspected 2026 CAGR. RS01 is the direct management contrast to the primary held-ticket method. Compare its full-history profit, drawdown, contributors and costs before considering further observations. More cash use alone is not a reason to promote a strategy.

**Economic attribution:** RS01 gains only \$+255 in fresh 2026. Interval-start role bookkeeping assigns \$-189 to additional holdings and \$+444 to core/other feedback. This does not show profitable extras in isolation. Its September cash is 42.7%, versus 49.8%; substantial cash remains.

**Timing and concentration:** economic accounts are identical before the first additional opportunities in late 2025 in the long account. The fresh-2026 common strongest update is 26 June: Realist Capital and Goon Edging each gain about 14% over roughly two observed days while BTC/ETH fall about 4.7%/6.0%. Realist contributes about 35% of positive 2026 vault profit. The long strongest update, 13 November 2024, precedes any additional allocation and therefore cannot explain a treatment advantage. These are sparse recorded-NAV updates, not demonstrated executable fills at every intervening timestamp.

## Robustness of results

Complete historical versus zero-extra equity and trade parity is required. The source core targets are unchanged by the merge and executed gross exposure/slot checks pass. A common fresh-entry cached-tax reset isolates the previously identified close/reopen marking inconsistency; historical control metrics are shown separately. Daily-resampled Sharpe includes off-cycle zero bins.

Contributor deletion, strongest-update curator/BTC/ETH context, overlapping quarter differences, sparse actual-update support, locked-slot counterfactuals and mechanical sleeve loss stress appear in the notebook. The hard-cap audit caught and repaired a suppressed trim: marked-to-gross conversion now uses each holding’s actual ratio, with a full close when the required reduction is below the source band. All accounts were rerun under the new identity. The conservative denominator includes both existing-position liquidation allowances and a possible new-entry capital allowance; initial all-cash snapshots are checked as well. No untouched holdout exists. Recorded NAV is not proof of an executable quote, and the inherited fee assumptions remain economically unverified.

## Next action

Treat improved historical profit and risk as a shortlist criterion. Require a later observation period and verified fee/permission conventions before production changes. Do not optimise floor, slot count or exposure limits using this same result table.
