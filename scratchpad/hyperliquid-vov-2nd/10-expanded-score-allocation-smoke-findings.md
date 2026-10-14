# Expanded experiment 10 — composite-score smoke findings

Executed using pinned repaired data. Decision period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**. Full four-day grid: **70 origins, 62 mature 30-day windows, eight pending**. Indicator warmup includes all 2025 observations plus earlier history. **36 combinations**; no broad-stage search or engine replay.

## What was examined

Inverse variance, inverse volatility, K-ratio and existing performance metrics enter per-vault composite scores before selection. Ranking and sizing recipes can differ. The smoke matrix covers arithmetic/geometric/minimum scores, standalone metrics, missingness, covariance risk budgets, sizing maps, breadth and constraints.

## Implementation and reference reproduction

All **27 independent audit checks passed**. T00 reproduces the original capped v11 source ledger: mean 30-day return 1.47%, cash 3.01%. T01 reproduces the capped focal-four equal benchmark: return 1.72%, cash 3.32%. Exact shared-date weights and all 62 mature outcomes match saved NB10. Its final two pending dates have no allocation reference, so the expanded calendar audit checks them separately.

## Main matched findings

| Comparison | Mean return difference | Paired origins | Cash difference | Common-budget difference |
| --- | ---: | ---: | ---: | ---: |
| T05 vs T02: Risk sizing recipe | +0.165 pp | 62 | +0.000 pp | +0.165 pp |
| T05 vs T27: Risk versus neutral offset | +0.145 pp | 62 | +0.000 pp | +0.145 pp |
| T27 vs T02: Neutral-offset flattening | +0.020 pp | 62 | -0.000 pp | +0.020 pp |
| T06 vs T01: Risk ranking / equal sizing | -1.112 pp | 62 | -0.836 pp | -1.094 pp |
| T07 vs T06: Risk score sizing / new basket | +0.081 pp | 62 | -0.000 pp | +0.081 pp |
| T14 vs T13: K ranking / same weighting recipe | -0.331 pp | 62 | -1.194 pp | -0.297 pp |
| T14 vs T26: K weighting / same ranking | -0.014 pp | 62 | -0.000 pp | -0.014 pp |
| T10 vs T05: Squared score sizing | +0.115 pp | 62 | -0.000 pp | +0.115 pp |
| T20 vs T14: Ten versus six | -0.873 pp | 59 | -0.127 pp | -0.869 pp |
| T21 vs T14: Neutral versus zero missing | -0.696 pp | 62 | +3.804 pp | -0.730 pp |
| T22 vs T14: Available-component missing | -0.889 pp | 62 | +29.917 pp | -0.778 pp |
| T23 vs T14: K confidence | -0.087 pp | 62 | -0.026 pp | -0.088 pp |
| T25 vs T14: Uncapped versus constrained | +0.531 pp | 62 | -2.121 pp | +0.489 pp |

## What the hypotheses tell us

**H1, low-risk score ingredients:** T05 minus the constant-offset control T27 is +0.145 pp on 62 common resolved origins. The neutral offset alone changes T02 by +0.020 pp. This distinguishes varying risk information from mechanical flattening; it does not establish generalisation across all 139 frozen recipes.

**H2/H3, K and separate roles:** T14 minus T26 (same ranking, K-on/off weighting recipes) is -0.014 pp on 62 origins. The K ranking comparison T14/T13 is recorded separately. These are recipe changes; the equal-third K addition changes other coefficients. A complete K ranking/sizing four-cell block remains a later-stage requirement.

**H4, sizing maps:** linear, squared, percentile, softmax and score risk budgets are executed on controlled baskets. Check requested distance from equal and accepted effective N before interpreting a gain; bounded top-ranked scores can produce nearly equal allocations.

**H5, broader recipe generalisation:** not tested in this smoke. All 139 canonical recipes were verified and preserved in inventory; only the declared focal/single-metric smoke arms were executed.

**H6/H7, constraints and missing histories:** cap/cash effects and M0/MN/MA funding are explicit. Minimum/geometric zeros can leave names unfunded; an all-zero score invokes the declared equal fallback. Young vaults remain candidates, but eligibility does not guarantee capital under linear missing-zero sizing.

## Robustness and interpretation

These are gross NAV independent fixed-unit 30-day snapshots. Do not compound their overlapping returns into strategy CAGR or average vault/portfolio Sharpes into an executable backtest Sharpe. All history is retrospective. The inherited ten-complete-block gate is unmet in 2026; comparisons are descriptive and no strategy is promoted.

Support, pending origins, missing terminal NAV, first-update attribution, unresolved-weight bounds, score imputation, covariance priors and cap distortion are saved per origin. Exact source control parity does not remove current-universe/guard or publication-clock limitations.

## Useful leads and next-stage scope

The next experiment should retain the neutral-offset control, matched score/missingness comparisons and common-support analysis. Add the complete K four-cell block, raw/regularised risk pairing, confidence/MN companion and missing-zero/minimum MA companion before stronger attribution.


### Tail attribution — 2026 origins, 30-day snapshots

The short-CAGR standalone probe T28 has a worst origin of -39.06%. Its largest negative mean contribution is 一三七: -1.351 pp over the arm’s resolved calendar. Quarter-removal and fixed-ledger vault attribution are saved and displayed; these episodes require inspection before treating means as stable forecasting evidence.

### Common deployment controls — 2026 origins, 30-day snapshots

The matched table also shows returns after reprojecting both requested portfolios to the smaller ex-ante accepted budget. This isolates total deployment changes while retaining each basket, score map and entry constraints. Its paired support is saved separately; it cannot eliminate differences in selected vault quality or cap shape.
A proposed **Stage A0 registry of 334 unique policies** covers 68 standalone metric/lookback components in separate ranking, sizing and joint roles, across 7/30/90-day horizons. It has not been executed. Its full JSON inventory is saved in this generation; broader all-139 composite families require their own frozen registry and contrasts.

Smoke allocation execution time: 25.7 seconds. Artefact generation fingerprint: `0d3861e02592ca8f484c54cc3dec9d29865911000cb43a37f1f9ce31bd0c6f03`.

Notebook: [expanded NB10](10-research-portfolio-snapshots.ipynb). Original generation: [saved NB10 appendix](appendices/10-original-portfolio-snapshots.ipynb) and [original findings](10-portfolio-snapshot-findings.md).
