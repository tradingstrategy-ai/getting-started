# Hyperliquid experiments after leader-share recovery

## Execution status

**Completed:** notebooks 01–05, both the 2026 and full-history periods, on the restored publication and updated readers. All 86 code cells finished without saved errors or warnings. The analyses, metrics tables, heatmaps, equity/allocation charts and DOEZOE daily status table have been refreshed.

## Source benchmark — 2026-01-01 → 2026-10-05, end exclusive, UTC

Each source replay starts with $150,000, no inherited positions and the same 139 two-day cycles. CAGR and Sharpe use the original daily-resampled convention. The new run recovers 95.2% of the equity gap remaining after the previous repair.

| Input generation | Final equity | CAGR | Sharpe | Maximum drawdown | Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| Earlier saved source reference | $194,928.64 | 41.59% | 2.00 | −6.40% | 582 |
| Previous permission repair | $186,418.03 | 33.47% | 1.63 | −9.04% | 601 |
| Restored leader shares and merged readers | $194,520.81 | **41.20%** | **1.96** | **−6.40%** | 581 |

The source and exact-formula research controls reproduce each other's equity and complete trade ledgers on the new inputs. This checks the strategy implementation independently of comparison with an older publication.

## What was updated

The repositories were fast-forwarded to their fetched remote master heads. Existing unrelated local edits were preserved. Our earlier unmerged reader patches were archived in the ignored run directory and replaced by the merged implementations.

| Repository | Master revision | Relevant merged fix |
| --- | --- | --- |
| trading-strategy | `6f34f9b` | [#255: retain shares and caps without a separate clock](https://github.com/tradingstrategy-ai/trading-strategy/pull/255) |
| trade-executor | `2db909b3` | [#1671: honour recorded caps without a capacity clock](https://github.com/tradingstrategy-ai/trade-executor/pull/1671) |
| web3-ethereum-defi | `d2bdf847b` | [#1634: restore leader shares and deposit caps](https://github.com/tradingstrategy-ai/web3-ethereum-defi/pull/1634), fixing [#1633](https://github.com/tradingstrategy-ai/web3-ethereum-defi/issues/1633) |

Fresh authenticated downloads were pinned by SHA-256. All experiments use a new universe, indicator and result generation under `_artifacts-restored-2026-10-07`. Metadata is pinned in a private client cache. Source settings, optimiser seeds, clipping choices, costs, guard record and both period boundaries remain unchanged. The cache key now consistently uses `5.0` for the same Calmar cap, avoiding duplicate evaluations caused by integer/float JSON spelling.

| File | SHA-256 |
| --- | --- |
| Prices | `30ec7e9dfa7eb236518cf1922a9ba82f4f42cfbfb041c06f5db3273d114aa8f2` |
| Metadata | `6c5ec12de41f1c10fc48e54a832eff065d14c77ea19c85fd482c46ea33a5382c` |

The price file contains 10,523,290 rows, including 1,764,297 HyperCore rows. The downloaded v1 scan receipt describes the price publication at 18:49:13 UTC on 7 October. Its separate permission endpoint returned HTTP 404; these source-strategy replays use the permission projection in the price file. The v1 receipt does not authenticate an independent sidecar.

## Restored policy inputs — 2026-01-01 → 2026-10-05, end exclusive, UTC

Counts refer to projected price rows, including carried values, rather than independent API measurements. Missing independent capacity clocks stay missing; they no longer erase recorded policy inputs.

| Field | Previous repair | Restored publication |
| --- | ---: | ---: |
| HyperCore rows in the comparison period | 1,720,365 | 1,720,365 |
| Non-NULL leader shares | 0 | 1,659,793 |
| Explicit deposit caps | 0 | 54,863 |
| Independent capacity clocks | 0 | 0 |

Gucky's 11 April 04:22:05.613 observation again contains its exact leader fraction `0.05000280943338046`, `max_deposit=0`, Open permission and original write time 04:22:06.999. The cap is the recorded conservative 5.5% leader-share policy, rather than a venue-reported dollar capacity. NULL remains distinct from zero. This availability policy applies to every experiment; experiment 02 separately tests clipping each portfolio allocation to its original requested dollars.

Across all 1,759,599 matched HyperCore rows from the two repair publications, deposit flags, permission clocks, capacity clocks, original write times and total assets are unchanged. There are 1,675,209 NULL-to-known leader-share restorations and 55,444 NULL-to-known caps. No previously known share or cap was removed or changed. The new cleaned publication also changes 295 matched share-price/total-supply values; this is an observed publication difference, not evidence that the leader-share migration itself rewrote raw economic fields.

The [refreshed DOEZOE daily audit](doezoe-deposit-status.md) contains one row per day through 7 October and checks agreement between both executor admission APIs. Midnight permission is Open and admission Allowed on 13–21 September; Closed and Blocked from 22 September. Original observation clocks determine permission age.

## Remaining benchmark difference — 2026-01-01 → 2026-10-05, end exclusive, UTC

The first **558 chronologically ordered trades match exactly**. Differences begin on 16 September. At that date equity differs by −$23.84; on 18 September the difference is only +$0.0049. Mad Scientists' 16 September execution price changes from `2.1595988328` to `2.1592000039`; DOEZOE's 18 September entry price changes from `2.1638406973` to `2.1580179048`. One earlier $102.06 Mad Scientists top-up on 2 October is absent in the new ledger.

The final −$407.83 equity difference reconciles to the final holdings and cash. This is an accounting attribution of the realised ledger difference; it does not isolate the causal effect of every changed input.

| Final component | New minus earlier value |
| --- | ---: |
| DOEZOE holding | −$385.87 |
| Reserve cash | −$21.59 |
| Other five holdings, combined | −$0.37 |
| Total final equity | **−$407.83** |

DOEZOE's marked price changes from approximately 3.476809 to 3.429680; its final quantity also changes because the same entry dollars bought shares at different prices. Thus exact reproduction of the older final equity is not expected solely from restoring the missing policy fields.

## Score-matrix search — 2026-01-01 → 2026-10-05, end exclusive, UTC

Experiment 04 completed the full-history singleton screen and sparse fits, then replayed the frozen families in 2026. The 126 labelled grid rows reduce to 90 distinct settings after equivalent clipping recipes are canonicalised. This is a description of the completed search, not a further selection step.

| Configuration | Positions / sizing / missing | CAGR | Sharpe | Maximum drawdown |
| --- | --- | ---: | ---: | ---: |
| Exact source v11, 360/45 | 6 / inverse variance / True | 41.20% | 1.96 | −6.40% |
| Near-v6, 360/46 legacy clips | 6 / inverse variance / True | 40.58% | 1.94 | −6.70% |
| Highest grid CAGR: 50/50 blend | 6 / inverse variance / True | **41.38%** | **2.12** | **−4.85%** |

Only one distinct grid configuration improves CAGR, Sharpe and drawdown together in 2026. It is the same blend tested as “Blend 46d” in experiment 05, whose full-history CAGR is 15.42% with −8.51% drawdown, below the source's 15.77% and −7.92%. Full-history grid maxima reach 18.77% CAGR, but with −13.33% drawdown; that configuration returns 31.63% CAGR in 2026. Neither result establishes a consistently better replacement.

The sparse fits retain just two cells: 60% 360-day CAGR and 40% 46-day Sortino. The CAGR and Sharpe objectives choose different clipping profiles, so blending their scores changes ranking even though their coefficient matrices are identical. Same-lookback clipped CAGR/Sharpe correlations are 0.89–0.92. One-month complete-window coverage is now 81.94% in the default 2026 panel; unavailable histories and undefined ratios are reported separately. Detailed coefficients, coverage, correlations and sensitivities are in [the experiment 04 analysis](04-score-matrix-analysis.md).

## Controlled treatments — 2026-01-01 → 2026-10-05, end exclusive, UTC

These are fresh engine backtests on identical inputs. The shortlist is descriptive, excludes tie-seed probes, and preserves the predeclared treatment definitions. The periods have already been inspected and overlap the full-history fitting window.

| Strategy | CAGR | Sharpe | Maximum drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: |
| Source v11 / exact formula | 41.20% | 1.96 | −6.40% | 8.83% |
| Original-request dollar cap | 9.31% | 1.31 | −4.22% | 51.32% |
| Feasible entrants | **41.83%** | 1.99 | −6.39% | 8.83% |
| Replacement hurdle 0.05 | 41.78% | 1.99 | −6.40% | 8.88% |
| Blend 46d | 41.38% | **2.12** | **−4.85%** | 7.43% |
| Source formula with cash refill | 39.56% | 1.88 | −6.44% | 8.40% |
| Blend 46d with cash refill | 40.00% | 2.05 | −5.08% | 7.12% |

Experiment 03's original inverse variance has the highest CAGR and Sharpe of its ten short-period allocation/weighting combinations. The four alternative baseline weightings return 34.28%–35.52% CAGR. Keeping the original-request cap materially reduces deployment and returns; lower costs do not compensate for this loss. Cash refill marginally increases exposure but underperforms its corresponding scoring control in both tested periods.

<details>
<summary>Full-history confirmations — 2023-03-01 → 2026-10-05, end exclusive, UTC</summary>

These are independent $150,000 starts over all available selected-vault history. They include the early cash-only warm-up and retain the fixed engine two-day alignment. They are not independent holdouts of the 2026 window.

| Strategy | CAGR | Sharpe | Maximum drawdown |
| --- | ---: | ---: | ---: |
| Source v11 / exact formula | 15.77% | 1.24 | −7.92% |
| Original-request dollar cap | 2.08% | 0.35 | −7.92% |
| Feasible entrants | **15.87%** | **1.25** | −7.92% |
| Blend 46d | 15.42% | 1.24 | −8.51% |
| Smooth C1 S3 | 14.84% | 1.16 | −7.92% |
| Source formula with cash refill | 15.37% | 1.20 | −7.92% |
| Blend 46d with cash refill | 15.20% | 1.21 | −8.61% |

The full-history v11 source ends at $254,103.35, close to the earlier $254,510.70 reference. Feasible entrants has a small improvement in both windows. Blend 46d's stronger 2026 risk metrics do not carry through to the full period.

</details>

## Completion and checks

The observable Jupyter runner completed all five notebooks and saved their outputs in place. The final saved-output audit found 86 completed code cells, no error outputs and no warning text. All 103 saved chart images were inspected; chart titles include their actual backtesting periods, and the score-matrix/calibration reports default to 2026. The interactive parameter explorer remains available in notebook 04.

Twelve cross-notebook source/cap metric comparisons agree for both periods. Notebooks 04 and 05 additionally assert source/exact-formula equity and complete ledger parity. All 166 overlapping metrics from the private cache workers match the shared results exactly. Those workers ran this input generation; no previous-publication strategy result was imported. The independent Sharpe fit also selects the same configuration and coefficients; its rounded screen summary is compared within 1e-9.

A final fetch confirms trading-strategy and trade-executor still match remote master at the revisions above. Existing unrelated local framework changes remain present and their active source fingerprints are recorded in the run manifests. No commits or pushes were made. Generated run files are ignored.

## Research files

- [01: v11 source baseline](01-initial.ipynb).
- [02: accepted-dollar caps](02-backtest-accepted-dollar-cap.ipynb) and [trade analysis](02-accepted-dollar-cap-analysis.md).
- [03: alternative weightings](03-backtest-alternative-weighting.ipynb) and [analysis](03-alternative-weighting-analysis.md).
- [04: score-matrix search](04-opt-score-matrix.ipynb) and [analysis](04-score-matrix-analysis.md).
- [05: clipping, selection and cash](05-opt-score-calibration-selection-cash.ipynb) and [analysis](05-opt-score-calibration-selection-cash.md).

Earlier publications and notebook outputs are retained in separate ignored generations. Generated states, CSVs, manifests and inspection images remain ignored. Reusable scripts, saved notebook outputs and written research conclusions are retained for review.
