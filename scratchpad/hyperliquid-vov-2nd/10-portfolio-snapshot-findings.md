# Experiment 10 — portfolio snapshot findings

Executed on 10 October 2026. Primary origin period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**; primary horizon **30 days**. Labels must mature inside the reporting boundary. Sources are the unchanged repaired archive used by NB08/NB09.

## What was examined

Frozen v11, Blend 46d and four-input scores select independent baskets every four days. We compare equal, inverse-volatility and inverse-variance weights, risk regularisation/windows, 4/6/8/10 positions, entry caps and bounded correlation/satellite companions. NAV paths hold fixed units; no strategy equity curve, engine replay, executable CAGR or portfolio backtest Sharpe is inferred.

## Main outcomes — 2026 period; 30-day horizon

Rows are equal-origin means on each policy’s resolved basket support. Weighting lift pairs the same basket and budget with equal weights. Return percentages are 30-day simple returns, not annualised strategy returns.

| score      | estimator   |   p | mean_return   |   mean_variance | weighting_lift   |   resolved_origins | unresolved_weight   |
|:-----------|:------------|----:|:--------------|----------------:|:-----------------|-------------------:|:--------------------|
| blend_46d  | equal       |   0 | 1.337%        |       0.0001812 | 0.000%           |                 62 | 0.000%              |
| blend_46d  | raw         |   1 | 0.287%        |       6.287e-05 | -1.050%          |                 62 | 0.000%              |
| blend_46d  | raw         |   2 | -0.538%       |       5.909e-05 | -1.874%          |                 62 | 0.000%              |
| blend_46d  | regularised |   1 | 1.000%        |       9.676e-05 | -0.337%          |                 62 | 0.000%              |
| blend_46d  | regularised |   2 | 0.581%        |       7.85e-05  | -0.756%          |                 62 | 0.000%              |
| blend_46d  | source      |   2 | -0.538%       |       5.909e-05 | -1.874%          |                 62 | 0.000%              |
| focal_four | equal       |   0 | 2.003%        |       0.0002317 | 0.000%           |                 62 | 0.000%              |
| focal_four | raw         |   1 | 1.019%        |       7.09e-05  | -0.984%          |                 62 | 0.000%              |
| focal_four | raw         |   2 | 0.207%        |       5.468e-05 | -1.797%          |                 62 | 0.000%              |
| focal_four | regularised |   1 | 1.622%        |       0.0001174 | -0.381%          |                 62 | 0.000%              |
| focal_four | regularised |   2 | 1.083%        |       8.829e-05 | -0.921%          |                 62 | 0.000%              |
| focal_four | source      |   2 | 0.207%        |       5.468e-05 | -1.797%          |                 62 | 0.000%              |
| v11        | equal       |   0 | 2.224%        |       0.0001887 | 0.000%           |                 62 | 0.000%              |
| v11        | raw         |   1 | 0.713%        |       6.334e-05 | -1.511%          |                 62 | 0.000%              |
| v11        | raw         |   2 | -0.137%       |       5.749e-05 | -2.361%          |                 62 | 0.000%              |
| v11        | regularised |   1 | 1.508%        |       9.723e-05 | -0.716%          |                 62 | 0.000%              |
| v11        | regularised |   2 | 0.837%        |       7.605e-05 | -1.387%          |                 62 | 0.000%              |
| v11        | source      |   2 | -0.137%       |       5.749e-05 | -2.361%          |                 62 | 0.000%              |

## Hypothesis verdicts — 2026 period; 30-day horizon

IC measures finite-score ordering. Weighting and breadth effects are paired horizon-return differences in percentage points; they are not annualised strategy returns.

| Score      |   Return IC |   Regularised weighting lift (pp) |   Raw weighting lift (pp) |   10−6 return difference (pp) | Verdict                                                                                       |
|:-----------|------------:|----------------------------------:|--------------------------:|------------------------------:|:----------------------------------------------------------------------------------------------|
| v11        |     0.08765 |                           -1.387  |                    -2.361 |                       -0.7425 | descriptive screening; inspect risk, concentration and reporting attribution before promotion |
| blend_46d  |     0.08675 |                           -0.756  |                    -1.874 |                       -0.1277 | descriptive screening; inspect risk, concentration and reporting attribution before promotion |
| focal_four |     0.08898 |                           -0.9207 |                    -1.797 |                       -0.5828 | descriptive screening; inspect risk, concentration and reporting attribution before promotion |

The sorting hypothesis is supported only where observed finite-pair IC and strict-reference selection evidence agree; full-universe attrition prevents treating conditional IC as unbiased selection skill. Unequal weights are assessed by their paired return/risk trade-off, not by weight rank IC: all positive inverse-risk powers have the same rank order. No primary 2026 comparison receives an inferential success label.

## Risk accuracy and reporting boundaries — 2026 period; 30-day horizon

Leave-one-out positive peer priors use complete elapsed windows first, partial history second. Support weight counts actual daily updates; observed flat and one-mark carried-flat paths are distinguished. Raw risk retains the inherited 1e-4 daily-sigma floor. Extreme floor errors remain in mean QLIKE; weighted median, win fraction and absolute-tail concentration provide context. Forecasted risk and forward-filled NAV risk are not established proxies for true executable economic risk.

| score      | estimator   |   risk_ic |   qlike_delta |   qlike_median |   win_fraction |   tail_absolute_share |   calibration_ratio |   paired_origins |
|:-----------|:------------|----------:|--------------:|---------------:|---------------:|----------------------:|--------------------:|-----------------:|
| blend_46d  | raw         |    0.5171 |        -1.822 |        -0.3112 |         0.5645 |                0.5042 |              0.8622 |               62 |
| blend_46d  | regularised |    0.5152 |        -1.896 |        -0.2259 |         0.5968 |                0.6478 |              0.7085 |               62 |
| blend_46d  | source      |    0.5171 |        -1.822 |        -0.3112 |         0.5645 |                0.5042 |              0.8622 |               62 |
| focal_four | raw         |    0.5401 |        -3.22  |        -0.3091 |         0.5726 |                0.6149 |              0.6891 |               62 |
| focal_four | regularised |    0.5456 |        -3.13  |        -0.2296 |         0.6048 |                0.7348 |              0.5601 |               62 |
| focal_four | source      |    0.5401 |        -3.22  |        -0.3091 |         0.5726 |                0.6149 |              0.6891 |               62 |
| v11        | raw         |    0.5143 |        -1.985 |        -0.3112 |         0.5618 |                0.5025 |              0.8581 |               62 |
| v11        | regularised |    0.5189 |        -2.033 |        -0.2248 |         0.5941 |                0.64   |              0.7019 |               62 |
| v11        | source      |    0.5143 |        -1.985 |        -0.3112 |         0.5618 |                0.5025 |              0.8581 |               62 |

First-update attribution uses original notional and reconciles with remaining-mark contribution. A catch-up mark can include genuine post-origin gains as well as unknown earlier movement; removing it does not identify an investable adjusted return. Endpoint staleness and terminal censoring remain unresolved economic limitations.

## Robustness and uncertainty — 2026 period; 30-day horizon

All 2026 intervals are descriptive under the frozen ten-complete-calendar-block gate. Full and pre-2026 simultaneous intervals are exploratory when support permits; their history has also been researched. Bootstrap draws preserve missing scheduled dates and share blocks across all 18 comparisons. Conditional active-treatment effects are saved alongside the primary policy effects, including equal-fallback and unchanged actual-breadth dates.

| score      |   phase |   mean_return |   weighting_lift |   variance_lift |   resolved |
|:-----------|--------:|--------------:|-----------------:|----------------:|-----------:|
| blend_46d  |       0 |      0.005806 |        -0.00756  |      -0.0001027 |         62 |
| blend_46d  |       1 |      0.004157 |        -0.008881 |      -0.0001139 |         62 |
| blend_46d  |       2 |      0.007532 |        -0.01296  |      -0.0001034 |         62 |
| blend_46d  |       3 |      0.004758 |        -0.007763 |      -0.0001796 |         62 |
| focal_four |       0 |      0.01083  |        -0.009207 |      -0.0001434 |         62 |
| focal_four |       1 |      0.008207 |        -0.008672 |      -0.0001109 |         62 |
| focal_four |       2 |      0.01084  |        -0.01503  |      -0.0001666 |         62 |
| focal_four |       3 |      0.008604 |        -0.009802 |      -0.0002138 |         62 |
| v11        |       0 |      0.008374 |        -0.01387  |      -0.0001127 |         62 |
| v11        |       1 |      0.004905 |        -0.01081  |      -0.0001126 |         62 |
| v11        |       2 |      0.007255 |        -0.01706  |      -0.0001089 |         62 |
| v11        |       3 |      0.004643 |        -0.01214  |      -0.0001675 |         62 |

Four grid phases overlap and are not independent replications. Ties are perturbed with 999 seeded identity priorities per tied origin. Assignment controls preserve concentration, and pooled random assignments retain identity priorities across dates. Quarter/vault influence holds the original ledger fixed, rather than reselecting a strategy. Gross NAV outcomes contain no invented slippage or turnover fees.

## Capacity assumptions — 2026 period; 30-day horizon

Source-report-only control applies source concentration/TVL and the source eligibility gate. The framework reports archived hard deposit caps but does not enforce them as partial rebalance sizing limits; the permissive hard-cap branch is therefore explicitly a capacity diagnostic, not exact source alpha-model parity. Unknown independent clocks retain recorded fields. Known-only state is an exclusion sensitivity, not a claim to be historically more accurate. Each constrained unequal policy has a same-accepted-budget bounded equal benchmark.

## Useful leads

1. Carry forward only paired construction trade-offs stable across score, nearby window, grid phase and reporting-quality diagnostics. Do not select a lone best cell as an optimum.
2. Treat peer regularisation and tempering the risk exponent separately: they change risk forecast accuracy and allocation concentration by different mechanisms.
3. Use exact shared/new-name breadth attribution to decide whether added positions help; requested N alone can conceal concentration or dilution.
4. Reconcile cash and capacity effects before converting any shortlist into a complete source strategy replay. Snapshot results omit retention, settlement, trading and fee state.

## Verification and remaining scope

Independent audit: 14 checks reported; saved audit table and original-archive reconstructions are under the ignored experiment 10 artefacts. Every selected name survives into the ledger, even with missing targets. No terminal payout or finite missing-upside bound is invented.

Core stages, source requested-risk checks, all primary contrasts, attribution, persistent assignment placebos, missingness, alternate phases/ties and basic capacity are implemented. Bounded covariance, satellite and cap/account-size companions are included. Irregular-interval/weekly risk, chronological calibration, category priors, full execution costs, the non-causal clairvoyant-risk diagnostic and a true realised-return LP bound remain separately labelled follow-up work; they do not change the frozen core estimands.

Notebook: [10-research-portfolio-snapshots.ipynb](10-research-portfolio-snapshots.ipynb). Reusable modules are saved beside it; generated figures, ledgers and manifests remain ignored.
## Answers to the research questions — 2026 period; 30-day horizon

**S — sorting:** observed future-return IC is modest and positive (about 0.087–0.089), with little separation between these three frozen recipes. Finite-pair ordering is conditional on observed targets. Strict eligible-universe references resolve on 55 of 62 mature origins; use that common cohort for selection-lift comparisons. This supports further evaluation, without establishing a superior score.

**R — risk forecasts:** selected-basket risk IC is about 0.51–0.55, substantially stronger than return IC. Raw and regularised variance improve mean QLIKE against the peer prior in the selected 90-day panels. Regularisation does not uniformly improve raw QLIKE: the four-input panel has a worse mean but a better win fraction. Level calibration ratios below 1 indicate underprediction; extreme errors contribute heavily to aggregate loss. Useful ordering and accurate risk levels are different claims.

**W — weighting:** uncapped 90-day inverse variance reduces daily variance versus equal weights but loses about 1.80–2.36 percentage points of mean 30-day return. Regularisation reduces that return drag to about 0.76–1.39pp; inverse volatility generally gives up less return than inverse variance, while accepting more risk. The return-enhancement hypothesis is rejected for these uncapped snapshots; the measured-risk-reduction hypothesis is supported descriptively.

**N — breadth:** matched 10-versus-6-position regularised inverse-variance returns decline by about 0.13–0.74pp, while realised variance falls. Ten-position outcomes resolve on 55 origins versus 62 for six positions; subtracting unmatched displayed means would misstate this effect. The satellite curve also uses common support and shows no return improvement over its matched core. Wider baskets are a risk/return trade-off, not an established profit improvement.

**C — constraints:** concentration and TVL projection substantially change the weighting comparison. The regularised inverse-variance source-report-only control has positive same-budget equal-weight lift, unlike its uncapped counterpart. Explicit source/raw controls below test this interaction using the same baskets and bounded budget. This is a stateless entry projection; it cannot establish engine-replay performance.

### Entry-capacity controls — 2026 period; 30-day horizon

Mean simple returns, paired same-budget weighting lift and initial cash are percentages. All rows use six positions, a 90-day risk window and source-report-only concentration/TVL projection. p=1 is inverse volatility; p=2 is inverse variance.

| score      | estimator   |   p | mean_return   | weighting_lift   | mean_cash   |   resolved_origins |
|:-----------|:------------|----:|:--------------|:-----------------|:------------|-------------------:|
| blend_46d  | raw         |   1 | 0.878%        | -0.152%          | 2.838%      |                 62 |
| blend_46d  | raw         |   2 | 0.931%        | -0.098%          | 2.838%      |                 62 |
| blend_46d  | regularised |   1 | 1.255%        | 0.226%           | 2.838%      |                 62 |
| blend_46d  | regularised |   2 | 1.374%        | 0.345%           | 2.838%      |                 62 |
| blend_46d  | source      |   2 | 0.931%        | -0.098%          | 2.838%      |                 62 |
| focal_four | raw         |   1 | 2.053%        | 0.337%           | 3.315%      |                 62 |
| focal_four | raw         |   2 | 2.353%        | 0.637%           | 3.315%      |                 62 |
| focal_four | regularised |   1 | 2.159%        | 0.444%           | 3.315%      |                 62 |
| focal_four | regularised |   2 | 2.512%        | 0.796%           | 3.315%      |                 62 |
| focal_four | source      |   2 | 2.353%        | 0.637%           | 3.315%      |                 62 |
| v11        | raw         |   1 | 1.656%        | -0.272%          | 3.008%      |                 62 |
| v11        | raw         |   2 | 1.467%        | -0.462%          | 3.008%      |                 62 |
| v11        | regularised |   1 | 1.973%        | 0.044%           | 3.008%      |                 62 |
| v11        | regularised |   2 | 1.992%        | 0.064%           | 3.008%      |                 62 |
| v11        | source      |   2 | 1.467%        | -0.462%          | 3.008%      |                 62 |

**Q — reporting and robustness:** first-update active attribution is small relative to the remaining negative uncapped weighting lift. The result is not explained solely by the first catch-up mark. Later marks can still contain reporting effects, so the remaining component is not labelled executable return. Negative regularised weighting lift appears in all four overlapping grid phases, with quarter and vault concentration remaining important. All supported longer-history simultaneous 18-comparison intervals include zero; 2026 has too few complete blocks for the planned inferential gate.

These 30-day snapshot returns are not comparable directly with source v11’s 41.20% strategy CAGR. The source replay includes repeated two-day decisions, incumbent rules, capped redistribution and inherited execution-cost assumptions; this study deliberately holds each independent entry basket unchanged.

## Exhaustive result appendices

The main notebook keeps 2026 as its default. Separate saved-output notebooks contain the exhaustive risk, allocation and statistical tables, including explicitly labelled long/pre-2026 periods: [risk](appendices/10-snapshot-risk-tables.ipynb), [allocation](appendices/10-snapshot-allocation-tables.ipynb), [statistics](appendices/10-snapshot-statistics-tables.ipynb).
