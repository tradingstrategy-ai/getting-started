# Experiment 09 — Claude review and decisions

Reviewed 2026-10-09. This accompanies the [revised feature forecast plan](09-k-ratio-feature-forecast-plan.md).

## Review provenance

The draft was written before invoking Claude CLI 2.1.281 with `--model claude-opus-5-5 --effort high`. The successful JSON response reports `canonicalModel: claude-opus-5-5`, provider `firstParty`; no fallback model was configured. Tools, customisations and session persistence were disabled. The supplied context contained the draft, experiment 05's actual `feature_audit`/`ic_summary` code and the glossary excerpt. Claude did not independently inspect the repositories.

Claude called the draft sound in intent but not ready to implement. The decisions below address that review; they do not claim a second review or new experimental results.

## Accepted changes

Each row states the review concern and how the plan now handles it.

| Concern | Decision |
| --- | --- |
| Fitting only period ends with an intercept makes the first return irrelevant to K. | Include the anchor in the primary fitted path, disclose n=L+1 and the formula, and preserve a separately named period-ends-only sensitivity. Verify first-return influence. Read the author's 2013 paper to check its scaling and initialisation. |
| The 90-day sample cannot support the proposed comparison after warm-up. | Explicitly expect descriptive/unsupported 90-day outputs and exploratory 30-day comparisons. Compute actual support before fitting. Attempt stronger inference only at 7 days if support permits. |
| Inner-fold tuning exceeds the available temporal evidence. | Fix ridge alpha=10 with explicitly normalised fitting weights; defer a fixed shallow tree until support allows it. |
| Level losses can reflect common market shocks rather than useful vault differences. | Make incremental within-date rank IC the primary discrimination measure; retain raw unit forecast errors and date-demeaned error diagnostics. Realised date means never become predictors. |
| K forecasting K may simply capture persistence. | Add past h-day target statistics to both comparison arms and compare against persistence, including past 7-day K. Do not assume improvement is guaranteed. |
| Missing-day rules and long-window coverage are vague. | Require consecutive actual daily marks in the primary panel, publish per-window coverage and keep carried-data reproduction separate. Admit pre-2026 labels only in a strictly audited secondary analysis. |
| Missingness itself can create apparent incremental value. | Give matched arms identical availability controls, including K availability, and add a compact age/quality control sensitivity. Keep meaningful metric-specific flags. |
| K input transformations and their scales were unspecified. | Use training-only asinh scales for K features/targets, shared across paired arms; preserve finite raw values and numerical-quality flags. |
| A large collinear feature set can dilute the signal. | Retain all existing features and add a fixed compact companion set, without retrospective feature selection. |
| Signed R² is not independent of K at fixed sample length. | Keep the identity audit; use slope/residual scale as decomposition controls. |
| Forecast errors need an evaluation support gate. | Require at least eight non-overlapping calendar blocks before reporting intervals or formal inference. Show individual block differences below that gate. |
| Existing guard membership can leak selection decisions. | Exclude guard, permission and unclocked operational fields from primary features/population; retain them only in caveated reproduction/funding diagnostics. |
| Delays should affect realised entry timing. | Shift the start and end of the label together in the delayed-execution sensitivity. |

## Suggestions adapted or rejected

### Preserve the requested missing semantics

Claude suggested redefining `missing=False` as complete-case filtering. Existing experiment machinery already uses that flag for zero contribution/ratio-floor behaviour. The plan retains a labelled legacy forecast adapter and adds complete-case filtering as a separate sensitivity. It documents that a zero raw metric and a zero quality score have different meanings.

### Do not assume closure pays the last NAV

Claude proposed treating every closure as redemption at last NAV followed by cash. Closure, loss of observations and an actual redeemable payout are different events. The plan uses terminal-payout-plus-cash labels only as a separate sensitivity when proceeds and timing are evidenced; otherwise it records missing targets and attrition. It also avoids accepting the review's assertion that NULL-clock fields are necessarily current values.

### Keep the daily K definition explicit

Claude proposed fitting on irregular observed calendar days with 80% coverage and a three-day maximum gap. That changes the equally spaced daily metric and makes its annual-frequency adjustment harder to interpret. The primary analysis keeps strict daily observations. Weekly observed sampling is a labelled quality sensitivity. The original paper supports the sample-count/frequency scaling, but endpoint conventions remain explicit rather than being inferred from the metric's name.

### Preserve all-chart visual review

Claude suggested inspecting only selected appendix charts. The user previously required every chart to be visually inspected and each image to appear separately. Those requirements remain. Notebook size is managed through small linked appendices rather than reduced review.

### Use support computed from data

The review's estimated earliest refits and independent-window counts are indicative, not verified. The implementation must calculate them from actual target maturation, usable feature rows and calendar blocks. Eight blocks remains a screening floor, not proof of power. No hypothetical formula for a metric's uncertainty is imported without validation.

## Creative ideas and priority

These suggestions refine the feature question without turning the plan into a composite-score or portfolio-weight search.

| Idea | Decision and requirements |
| --- | --- |
| Isolate K beyond same-window Sharpe, then compare autocorrelation/variance-ratio/path-shape controls. | Include a bounded training-only residual diagnostic using existing returns. Avoid K/Sharpe division near zero. |
| Separate predictability of mean return from predictability of volatility. | Include volatility/persistence decomposition, so successful Sharpe/K forecasts are not mistaken for profitable-return skill. |
| Compare daily versus weekly observed K. | Include as a staleness sensitivity with explicitly aligned windows, observation counts and frequency. |
| Shrink unreliable young-vault statistics and add 7/14-day or since-inception inputs. | Defer to a bounded follow-up. Requires a justified dependence-aware reliability model; native partial-history forecasts are implemented first. |
| Predict closure or severe losses. | Add event/attrition diagnostics where observed; a predictive event model needs reliable event labels and enough events. |
| Add performance-adjusted flows/depositor counts. | Defer until historical observation clocks and input coverage are audited. |
| Validate NAV using fills/positions or unsmooth the series. | Defer; each needs additional data or assumptions. Do not substitute adjusted labels for primary actual NAV. |
| Freeze a future confirmation and collect reliable snapshots. | Include as an implementation requirement. Determine the future window from target maturity and independent block support, not just total vault rows. |

## Retained evidence

The ignored directory `_artifacts-restored-2026-10-07/09/plan-review/` contains the original draft, exact prompt, raw JSON response, readable review, CLI/model metadata and the author's retrieved 2013 paper. The final plan hash is recorded there for reproducibility. The revised plan has not been submitted for a second Claude pass.
