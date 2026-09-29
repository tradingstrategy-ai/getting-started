# Rolling profit/risk track summary

The rolling track tested whether direct causal rolling features, short history access, alternative sizing and exposure interventions improve stable vault-of-vault results. Blacklists were off, the common return gate was -16%, and the corrected single redemption fee was used throughout. The three windows overlap, so the later window is a robustness slice rather than an independent holdout.

## What ran

| Notebook | Experiment | Result |
| --- | --- | --- |
| NB25 | Direct rolling metrics and legacy/B00 controls | Executed over `hyper_ai`, `full` and `later` windows |
| NB26 | B00/B10/B01/B11 ranking and access factorial | Executed over all three windows |
| NB27 | B11 fixed membership with equal raw, inverse-volatility and inverse-variance sizing | Executed; replay Jaccard 1.0 for every arm |
| NB28 | B00 parent with E1 no-refill and E2 drawdown haircut, each with uniform-scaling control | Executed; all 12 runs and exposure ledger saved |
| NB29 | Artefact-only lineage, curves, metrics, exposure and contributor synthesis | Executed; no new search or backtest |

## NB27 sizing results

The sizing arms used the same requested B11 membership on each date. This isolates sizing from selection. The full-period results were:

| Sizing | CAGR | Sharpe | Volatility | Max drawdown |
| --- | ---: | ---: | ---: | ---: |
| Equal raw | -89.2% | -3.49 | 58.0% | -89.4% |
| Inverse volatility, `k=1` | -91.1% | -3.00 | 71.0% | -92.7% |
| Inverse variance, `k=2` | -91.0% | -3.08 | 69.3% | -91.9% |

Inverse-risk sizing therefore did not rescue the B11 membership in this sample. The replay log has 379 cycles for each arm, with mean Jaccard 1.0 and zero missing or unexpected addresses.

## NB28 exposure results

E1 keeps residual cash after the parent allocator's capacity clip. E2 applies the causal haircut `target* = exp(-max(drawdown, 0) / 0.10)` to each target and keeps the released amount as cash. The `_SCALE` arms uniformly scale the same intervention total and act as controls for the effect of invested capital.

| Window | Arm | CAGR | Sharpe | Volatility | Max drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| hyper_ai | E1 | 17.5% | 1.85 | 8.9% | -4.3% |
| hyper_ai | E1_SCALE | 31.0% | 2.60 | 10.6% | -4.3% |
| hyper_ai | E2 | 12.4% | 1.57 | 7.6% | -3.2% |
| hyper_ai | E2_SCALE | 19.4% | 1.98 | 9.2% | -5.2% |
| full | E1 | 9.4% | 1.10 | 8.5% | -4.4% |
| full | E1_SCALE | 5.7% | 0.56 | 10.9% | -9.6% |
| full | E2 | 1.7% | 0.20 | 11.6% | -7.2% |
| full | E2_SCALE | -0.5% | 0.03 | 12.8% | -10.8% |
| later | E1 | 5.9% | 0.65 | 9.6% | -4.5% |
| later | E1_SCALE | 18.9% | 1.60 | 11.2% | -3.6% |
| later | E2 | -1.3% | -0.10 | 9.2% | -5.6% |
| later | E2_SCALE | 7.1% | 0.73 | 10.1% | -4.4% |

The exposure experiments are mixed. E1 is the more defensible risk-control result because it preserves the parent allocator's relative sizing and leaves rejected capacity in cash; its benefit is positive in the full and later windows but not a uniform improvement over B00. E2 reduced exposure but did not improve the full or later risk-adjusted outcome. The strong hyper-ai results should not be treated as confirmation without a non-overlapping holdout.

## Artefacts

All saved outputs are under `_artifacts-rolling-profit-risk/nb25` through `nb29`. NB29 contains `metrics-all.csv`, `equity-curves-long.csv`, `equity-curves.html`, `exposure-report.csv`, `contributor-report.csv`, `selection-coverage-report.csv`, `lineage-results.csv` and `deferred-robustness.csv`.

The bounded follow-ups in `deferred-robustness.csv` remain unrun: interval-lookback sensitivity for B01/B11 and removal of the largest positive B11 contributor. These are follow-ups, not hidden results.
