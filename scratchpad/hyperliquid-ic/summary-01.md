# Hyperliquid IC research: first results summary

Date: 2026-09-14. Results use the frozen cache through 2026-09-13.

## Conclusion

We found strong persistence in vault risk, but have not demonstrated a better portfolio allocation strategy or reliable return prediction. Recent volatility is the clearest predictor of future volatility and downside risk. Whether this can improve portfolio stability while retaining useful returns remains untested. The objective of 20–30% annual CAGR is still a hypothesis, not a supported forecast.

The notebooks have been executed and their calculations reviewed. This completes a diagnostic research pass, not the full research plan or production validation.

## Evidence

| Finding | Saved result | Interpretation |
| --- | --- | --- |
| Recent volatility predicts future volatility | 10-day volatility versus next 7-day variance: mean rank IC **0.849**, across 60 dates | Relatively quiet vaults tend to remain relatively quiet. |
| Recent volatility predicts downside risk | 10-day EWM volatility versus next 30-day downside semivariance: IC **0.806**, across 49 dates | Potentially useful for risk screening or sizing. |
| The fitted model predicts risk rankings | Out-of-fold 30-day variance IC **0.692**; downside semivariance IC **0.595** | Encouraging, but incremental value over a simple volatility control has not been established. |
| The fitted model has no demonstrated stable return skill | Out-of-fold 30-day growth IC **0.005**; individual folds **+0.072 / −0.180** | This model's return ranking does not generalise consistently across the two folds. |
| BTC exposure has an exploratory return association | 90-day BTC beta versus 30-day growth: IC **0.327**, across only 19 dates | Could reflect one market regime; insufficient evidence for selection. |
| Young vaults can enter the feature panel | Eligibility starts after 30 observed days; 30-day BTC features do not require a second trailing window | The pipeline supports young vaults. Profitable selection of them remains unproven. |
| Allocation comparison provides no performance evidence | Both research arms hold cash throughout | Neither improvement over production nor adaptive position counts has been evaluated economically. |

Univariate figures above use the whole-universe panel. Model figures are equal-date means from the saved walk-forward diagnostics. Rank IC measures ranking association: 0.85 does not mean 85% forecast accuracy or imply a particular portfolio return. Univariate and model ICs use different date/coverage sets and must not be compared as a matched test of model lift.

## Scope of the completed run

- 602 vaults; 647 two-day panel dates before eligibility filtering.
- 64 eligible decision dates, from 10 May to 13 September 2026; 16,425 eligible vault-date rows.
- 82 catalogue predictors and four fixed controls screened; six additional EMA seed diagnostics retained in the feature panel.
- Seven forecast horizons: 7, 14, 21, 30, 45, 60 and 90 days; 49 forward outcomes.
- 7,028 available IC results across 8,428 declared feature/target/panel combinations; 1,400 unavailable combinations recorded.
- Two purged, fold-local model evaluations, with 14 and five matured test dates respectively. The 57 saved model rows are 19 dates multiplied by three targets, not 57 independent tests.
- Walk-forward model fitting covers **30-day outcomes only**. Screening all seven horizons does not establish model performance at the other horizons.

## What matters for the strategy objective

A simple risk filter deserves an economic test. The evidence suggests we can identify comparatively lower-risk vaults, but low risk alone does not establish positive returns or protection against rare blow-ups. Quiet losing vaults and inactive vaults can also look attractive on risk measures.

The earlier lower-volatility and waterfall research already showed that smoothness and risk signals can pass screens without improving investable portfolios. The current result is consistent with that history: a clearer risk-persistence finding, with portfolio translation still unresolved.

There is no evidence yet that BTC residual risk, longer EMAs, age or TVL add useful out-of-sample information beyond simple trailing volatility. These inputs have been included or screened; inclusion is not evidence of incremental value. Nor has the research established a superior forecast horizon or an adaptive allocation policy.

## Material limitations

### Short and overlapping evaluation history

The effective sample is much smaller than the vault-date row count suggests. Many vaults share the same market environment, and successive forward outcomes overlap. Nineteen matured out-of-fold dates do not constitute nineteen independent 30-day experiments. Bootstrap uncertainty, permutation tests and matched-control comparisons remain unfinished.

### The cash result is caused by the research data and scoring policy

The publication filter admits a historical daily observation only if it was available within two days of that observation date. It permanently excludes later-published observations, even from subsequent decisions when that history might have been available. This is stricter than a decision-time as-of policy.

That conservative construction removes all eligible 360-day CAGR inputs. The research composite abstains when either component is missing, so both allocation arms stay at $150,000 with zero positions and trades. This is not a test of the live production strategy: its missing-signal ranking and tie-break behaviour differ. The cash result cannot establish allocator performance, concentration benefits or production superiority.

### Historical timing and provenance remain diagnostic

Diagnostic labels enter at `NAV_T`, while the information set uses a conservative `T+2` publication clock. Prospective labels must instead start at the first executable NAV at or after the recorded decision boundary. Historical provider revisions, deposit/redemption availability and survivorship are not fully reconstructable from the bulk cache.

The exact BTC reference and source hashes are retained. Raw and repaired NAV fields and provider repair status are retained, and 1,008,123 provider-carried rows are excluded from fresh-coverage counts. These repairs improve auditability but do not turn the cache into a complete historical point-in-time archive.

### Plan coverage remains incomplete

Outstanding work includes matched-row incremental comparisons against volatility and availability controls, block uncertainty, permutation tests, investable upper-ranked baskets, age-cohort comparisons, missing-outcome stress scenarios and the forecast-horizon decision. Feature-score allocation arms B/D and exact production-engine replay remain deferred.

Some feature definitions and manifest descriptions still differ from the plan, as recorded in the final review. These should be reconciled before freezing a feature catalogue. Successful execution and repeated code reviews do not substitute for the remaining research tests.

## Recommended next steps

1. **Establish an interpretable production baseline.** Compare the strict publication filter with an explicit decision-time as-of information policy, retaining the limitations of the available revision history. Reproduce the production engine's scoring and execution behaviour for the baseline.
2. **Test simple volatility screening economically.** Compare forward basket returns and risk on matched dates, eligibility and exposure. Check whether lower risk retains useful returns and whether results depend on individual vaults, cash or concentration.
3. **Measure model lift against that control.** Use identical rows and folds, add block uncertainty and the planned null test, then evaluate the existing horizon grid before selecting a horizon or adding more features.
4. **Collect prospective data alongside the diagnostic work.** Preserve immutable source versions and predictions before outcomes are known. A collection specification exists; a running collector has not been delivered by this research pass.

No production strategy change is justified by the current results.

## Files supporting this summary

- [Research plan](plan.md)
- [Data and baseline notebook](01-data-and-baseline.ipynb)
- [Feature panel notebook](02-feature-panel.ipynb)
- [IC screening and walk-forward notebook](03-ic-screen.ipynb)
- [Allocation validation notebook](04-allocation-validation.ipynb)
- [Final Claude Opus review and post-review resolution](claude-review-opus-12.md)
- [Prospective collection specification](prospective-collection-spec.md)
- Saved numerical evidence: `_artifacts/ic-results.parquet`, `_artifacts/ic-grid-audit.csv`, `_artifacts/walk-forward-ridge.parquet` and `_artifacts/allocation-metrics.csv`.
