# Experiment 09 — K-ratio features and future vault performance

> **10 October 2026 amendment:** the user requested sparse-data support for all metric families. The complete actual-daily-observation requirement below is superseded by causal calendar-day forward filling, with actual observation masks retained and future labels censored after the last actual vault mark/archive end. See [current summary](summary.md) and [sparse-data audit](sparse-nav-rerun-2026-10-10.md).


Written 2026-10-09. Status: implemented and executed on the pinned repaired archive. See [notebook](09-research-k-ratio-feature-forecasts.ipynb) and [findings](09-k-ratio-feature-forecast-findings.md). The prospective design is saved separately from the retrospective analysis.

## Goal

Measure whether historical K-ratio predicts future **CAGR, Sharpe and K-ratio**, and whether adding K-ratio features improves forecasts made from the existing vault features. Forecast each target over **7, 30 and 90 calendar days**, allowing incomplete feature histories with **`missing=True`**. Establish the strength, stability and incremental value of the relationships before proposing strategy changes.

The starting point is **experiment 05's “Causal feature diagnostics”**, implemented in `score_calibration_experiment.py:feature_audit`, together with experiment 04's feature definitions and redundancy analysis. These are individual historical performance features. Composite scoring methods, matrix coefficients, position weights and experiment 08's catalogue of scoring recipes are outside the predictor set. Experiment 08's independent raw-observation audit can inform data checks, but does not define this experiment's features or models.

## Questions and decisions

1. Which individual existing features and K-ratio lookbacks relate to each future target?
2. Does K-ratio improve chronological forecasts beyond the existing features on the **same vault/date observations**?
3. Does any improvement survive quarter changes, vault-age cohorts, price-quality controls and removal of influential vaults/events?
4. Can partially observed young vaults receive useful forecasts, rather than being dropped because a long lookback is missing?
5. Is the sample sufficient to support a conclusion for each target/horizon, particularly 90 days?

An outcome may be useful, redundant, misleading because of stale marks, or inconclusive. A higher feature correlation or a successful in-sample fit alone does not establish forecast improvement. Portfolio admission thresholds and strategy backtests are a later experiment if these checks support them.

## Existing feature analysis and weaknesses to address

### Starting evidence

Experiment 05 analyses raw CAGR, Sharpe, Sortino, signed maximum drawdown and Calmar across nine searchable lookbacks. It samples every two days, uses 14/30/60-day future return and Sharpe labels, and averages within-date Spearman correlations. Experiment 09 keeps the feature inventory, changes the targets/horizons as requested, and uses the earlier requested **four-day forecast cadence**, anchored at 2026-01-01 UTC.

The saved 05 table illustrates why this needs a forecast experiment: 30-day historical Sharpe has mean IC +0.106 with future 30-day Sharpe, but only +0.026 with future return; its 60-day return IC is −0.033. These are exploratory associations using the old label construction, not validated predictions. Recompute them on audited labels before drawing a conclusion. Source: `_artifacts-restored-2026-10-07/05/2026-forward-feature-summary.csv`.

### Required improvements

Each row describes a limitation found in the earlier implementation and the corresponding change in this experiment.

| Earlier limitation | Improvement in experiment 09 |
| --- | --- |
| Future labels are built from the strategy candle series, which can include carried or processed prices. | Build genuine targets independently from actual per-share NAV observations; preserve an explicitly labelled source-compatible feature panel for comparison. |
| The feature audit reports associations, without chronological multivariate forecasts or constant/persistence comparisons. | Fit bounded feature-based models with matured labels only; compare predictive losses and rank IC against simple baselines. |
| Eligibility applies source inclusion, return gate, quarantine and whitelist, but omits some execution constraints and permissions. | Separate observed, operationally eligible, permission-unknown, fundable and actually selected populations. Diagnose forecasts independently of funding feasibility. |
| Pairwise deletion gives different features different vault/date samples. Complete-case multivariate analysis would exclude young vaults. | Show pair counts, common-cohort comparisons and expanded-cohort coverage; explicitly model missing inputs. |
| Existing Calmar already has a 1% drawdown denominator floor. | Preserve this definition in the reproduction arm; disclose it and compare an unfloored, undefined-at-zero diagnostic separately. |
| Correlation and feature-bin charts do not identify incremental information or distinguish coverage from skill. | Use paired old-versus-old-plus-K model ablations, an age/quality/missingness baseline and training-only conditional diagnostics. |
| Moving blocks are expressed in a count of retained dates; skipped dates and overlapping horizons complicate inference. | Resample complete calendar blocks with all vaults kept together; report support and phase sensitivity, rather than treating row counts as independent observations. |
| Many cells are explored on already inspected history; top-feature tables invite retrospective selection. | Predeclare primary comparisons, limit model complexity, retain all cells and label 2026 as researched history. Require a frozen future confirmation before promotion. |
| Earlier displays combine multiple charts and can become large. | Each chart gets its own heading and description; keep the main notebook bounded and link separate feature appendices. |

## Data, timing and populations

### Reporting periods and reproducibility

Default charts, tables and Markdown conclusions use **2026-01-01 → 2026-10-05, end exclusive, UTC**, matching the repaired experiment generation. The full available history is a separately headed secondary analysis. Pre-2026 history can initialise features. Supervised labels before 2026 belong only to the secondary sensitivity and must pass the same actual-observation quality rules.

Pin the repaired input generation used by the earlier experiments, archive hashes, framework/strategy commits, guard snapshot and feature code. Before implementation, confirm the actual archive end and coverage rather than silently fetching a newer generation. Use a new experiment-09 artefact namespace and include metric definitions, missing policy, timing convention and source hashes in cache keys. Reusing an earlier feature cache is permitted only after its manifest and values pass an explicit compatibility audit.

### Time alignment

At origin **T**, use only observations available before the decision. The completed-day anchor **A = T−1** is the existing open-labelled daily close convention, subject to a raw observation-time check. An L-day feature uses L returns and L+1 positive daily NAV marks ending at A. A horizon h target uses returns after A through A+h. Store candle labels, actual observation times, target-end time and the earliest defensible label-availability time separately.

Train only on labels whose entire future window was observed **strictly before** the model fitting origin. Never include an incomplete horizon or shorten a terminal label. Archive `written_at` is not an invented historical publication clock. Retain archived leader-share and permission values when their independent clock is NULL; mark the provenance/availability assumption instead of manufacturing a date or discarding the value. Where trustworthy publication times exist, enforce them. Where only observation times exist, label the research as observation-time replay and include a one-day delay sensitivity.

### Population and price quality

Primary forecast analysis includes observable vaults with positive valid anchors, without using future success, survival, selection or target availability to define entry membership. Also report the experiment-05 gate-filtered population as a secondary comparison, reproducing its rules exactly. Funding feasibility is a separate diagnostic, including availability of the 90-day sizing indicator; a valid forecast does not imply that a vault can receive a position.

Current guard/whitelist membership, leader share, deposit permission and fields without a reliable historical observation clock never enter the primary predictors, controls or population definition. Their archived values are retained for the caveated compatibility/funding audit. NULL clocks do not prove that a value is current; equally, they cannot prove historical availability. Source inclusion or gates derived from future-aware membership also remain outside the primary population.

For every feature and label, record missing reasons: insufficient age, absent daily observations, non-positive NAV, flat/zero-risk window, numerical degeneracy, stale/carried marks and right censoring. Actual unchanged prices remain legitimate observations. Synthetic carry-forward is distinguished using provenance, not simply by deleting all zero returns. Record last actual observation age, observed fraction and longest flat run. Publish the current-snapshot universe limitation and any missing historical vaults, including terminal observations and closures; do not fill unavailable delisted returns with favourable outcomes.

Primary daily metrics require the full consecutive calendar-day window. Do not compress gaps into consecutive observation numbers, fit irregular samples and call them daily K-ratio, or infer completeness from a filled candle. Long features may therefore be mostly missing, especially before 2026; this is an audited result, not a reason to loosen the rule. Primary supervised labels originate in 2026. Earlier labels are a separate sensitivity admitted only when they pass these same strict daily/endpoint observation checks. All datetime values are naive UTC.

Treat verified closure and lost observations separately. Record closure and severe-loss events as attrition diagnostics; a vanished series alone does not establish closure, redemption proceeds or when cash was available. Where an actual payout and its timing are documented, add a separately labelled terminal-payout-plus-cash return sensitivity. Do not manufacture a full-horizon NAV, Sharpe or K path from a last quote. Otherwise preserve the missing label and disclose potentially informative attrition.

## Feature inventory

### Existing inputs

The primary existing panel is **45 raw features**: five metrics × **30, 46, 60, 90, 120, 180, 270, 360 and 730 days**. The five original **45-day compatibility** features are retained for reproduction/sensitivity, giving 50 inventoried existing features. Do not optimise a 45-versus-46 switch retrospectively. Annualisation remains 365 even for a 360-day lookback.

Keep CAGR, Sharpe, Sortino, signed maximum drawdown and existing floored Calmar in their original units. Compare source-compatible and strictly observed feature construction on matched rows to reveal any apparent advantage driven by filling. Preserve the earlier formulas in the reproduction arm. The primary forecasting arm uses audited inputs and never treats synthetic marks as complete actual history.

### New K-ratio inputs

Calculate K-ratio at all nine primary lookbacks, with 45 days for compatibility only. Inventory all of them, but predeclare **30/60/90/180-day K-ratio** as the bounded initial incremental feature group. The other K-ratio windows form a secondary expansion, not nine opportunities to choose a favourable result after seeing targets.

For each window also store the fitted daily log-growth slope, slope standard error, signed goodness of fit, residual scale and quality flags. These are diagnostic decomposition controls. For an intercept OLS trend with n points, `b/SE(b) = r * sqrt((n−2)/(1−r²))`, where r is the time/log-NAV correlation. Thus fixed-length K-ratio and signed R² encode the same ordering. They are not two independent novel features. Verify this identity numerically and ask whether any value comes from path consistency, growth magnitude or observation quality.

Transform finite K inputs with `asinh(K/s)` before modelling, with s equal to the median absolute non-zero finite K in the fitting data, separately per feature. If that support is absent, disable the feature for that fit. Use the same training-derived scales, imputers and target transformation in matched arms. Do not fit a global transform using evaluation observations. Signed R² remains an identity check; decomposition forecasts use slope and residual scale rather than presenting signed R² as an independent extra input.

### K-ratio convention

Follow the repository [glossary definition](/Users/moo/code/docs/source/glossary.rst:4353): **Kestner 2013**, intercept OLS on log wealth against equally spaced daily observation numbers, **m=365**. Kestner describes the sample-count and annual-frequency adjustment in [(Re)Introducing the K-ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2230949).

For L daily returns, take L+1 observed positive per-share NAV marks, normalise by the anchor and fit **all L+1 daily wealth points**, including the initial point, at t=0,…,L with an intercept. Set **n=L+1 fitted observations** and compute:

`K2013_anchor_included = slope / ordinary_OLS_slope_standard_error * sqrt(365) / (L+1)`.

This explicitly declared anchor-included convention ensures every return in the advertised L-day window affects the fitted path. Fitting only t=1,…,L with an intercept makes the first return a constant shift and therefore excludes its effect. The 2013 paper uses the sample-count adjustment and an initialised cumulative path, but its return-count terminology does not settle every implementation's endpoint convention. Retain a labelled period-ends-only sensitivity (n=L), disclose the fitted-point/return counts, and never combine conventions in one feature or target column. The author's paper was retrieved and read during plan review; the local glossary is unchanged.

Future K-ratio follows the identical primary convention with L=h. Use share NAV, not TVL or deposit-driven total assets. Use zero risk-free return consistently: this plan follows the glossary's log-NAV convention, whereas the author's paper also discusses excess-return accumulation. The slope t-statistic is a metric component, not a valid significance test on serially dependent cumulative wealth.

All-flat and exactly linear log-wealth windows can have zero standard error; mark K-ratio undefined with a reason. For nearly linear paths, retain the raw finite result and numerical-condition diagnostics; use a stable signed transform for modelling. Do not silently set undefined values to zero, invent a universal K-ratio cap or replace the ordinary OLS denominator with a different estimator while retaining the same name. Evaluate stricter numerical/price-quality rules as labelled sensitivities.

## Targets and prediction scale

Each horizon has its own training rows, target support audit and model. Invalid labels stay missing and are never imputed.

| Target | Raw realised label | Primary modelling/evaluation scale |
| --- | --- | --- |
| CAGR | `(NAV[A+h]/NAV[A])**(365/h) − 1`; exact observed positive endpoints required. | Forecast h-day log return; report log-return MAE/MSE and convert to CAGR for displays. Raw CAGR errors and actual h-day return are secondary, since annualising seven days magnifies extremes. |
| Sharpe | `mean(daily simple returns)/sample_std(ddof=1) * sqrt(365)` with zero risk-free return; h actual daily returns required. | Raw Sharpe, robust loss and squared-error diagnostic. Zero variance is undefined; no denominator floor in the target. |
| K-ratio | Anchor-included Kestner 2013 scaling on h+1 observed daily wealth points, as specified above. | `asinh(K/s)` with a scale s fitted only on historical training labels; rank IC and raw-unit MAE as companions. Raw extreme-tail errors stay visible. |

A model fitted to log return or transformed K-ratio predicts that transformed conditional quantity. Its inverse transformation is not automatically the conditional mean of raw CAGR or raw K-ratio. Name the displayed estimate accordingly. Compare arms in identical target units, including after inverse transforms. Seven-day Sharpe and K-ratio are especially noisy realised labels; treat their reliability as an empirical question and avoid presenting them as precise latent skill estimates.

For K targets, set the target transform scale to the training median absolute non-zero finite K for that horizon, shared across compared arms; an unsupported scale means no supported K model. Check `ddof=1` for historical and future Sharpe alike. CAGR and h-day log return have identical ranks; their IC is one result, not independent evidence. Label Sharpe-to-Sharpe and K-to-K relationships as possible persistence of volatility/path smoothness, not established return skill.

## Missing=True behaviour

This flag is a **feature availability policy**, not an imported matrix-scoring rule.

- With **`missing=True`**, retain per-feature NaN and missing-reason masks. A missing 360/730-day input must not discard a young vault with usable 30-day inputs. Never require all 45 or 54 features to be finite.
- Linear models use training-only per-column median imputation plus fixed-schema missing indicators and quality/age controls. Entirely unsupported columns are disabled within that fitting fold; their missing indicators and column identity remain recorded. Tree models may handle NaN natively. Imputation is a model adapter; the stored raw panel remains NaN.
- Record a forecast's observed input count, K availability, reasons, training support and whether it is informed by performance features. If no performance input is usable, the primary feature model abstains; a separately labelled age/quality or constant baseline may still produce a forecast.
- With **`missing=False`**, run an explicitly labelled legacy zero-filled sensitivity with the earlier Sharpe/Sortino floors where applicable, following the availability distinction in `score_matrix.py:ScorePanel.cell_scores`. This is a forecast adapter, not a reproduction of composite scoring: a zero-filled raw drawdown has a different meaning from a zero quality score. Keep this bias visible. Add a separate **complete-case** sensitivity showing which vaults would be lost; do not redefine the existing flag to mean complete-case filtering. Preserve NaN/masks upstream and never impute targets.
- Compare old versus old-plus-K on the same origins/vaults and target-valid rows. Also measure expanded coverage and young-vault performance separately. A method gaining rows is not automatically improving accuracy.
- Missing future labels remain missing in both modes. Track their fractions by origin, age, closure/permission and stale-price cohorts; report informative attrition rather than claiming paired surviving rows describe every vault.

All arms share the same inventory of availability controls, including K-window availability masks, so the incremental K-value comparison cannot win merely by adding a new age/missingness indicator. Keep metric-specific missing reasons because zero-risk and missing-history states differ. Regularise nested masks; include a compact-control sensitivity using log age, number of available windows and observed fraction.

## Bounded forecasting experiment

### Feature groups and controls

The following arms isolate information rather than optimise strategy coefficients. Quality/age/missing controls are identical across matched model pairs.

| Arm | Inputs and purpose |
| --- | --- |
| Historical constant | Equal-date weighted training mean on the target's modelling scale; no feature information. |
| Zero-return control | A zero h-day log return/CAGR forecast; avoids relying only on the past-drift training mean. It does not define zero as a natural Sharpe/K baseline. |
| Target persistence | The latest available past h-day measure, computed before T; an honest same-target continuation baseline. |
| Quality/age baseline | Vault age, observation freshness/completeness, flat-run measures and missing masks; exposes predictability caused by data availability. |
| Existing features | The 45 historical metrics plus the common controls. |
| Existing + K | Identical model plus the four predeclared K windows; the primary incremental comparison. |
| Persistence + existing / + K | Add the past h-day target statistic to both matched arms. In particular, include past 7-day K in both 7-day K arms. This checks whether K adds information beyond own-statistic persistence. |
| K alone + controls | Tests marginal information without pretending this proves independence from the existing metrics. |
| Decomposition sensitivity | Existing inputs plus log-growth slope/residual scale for the same four windows, compared with K on common rows. |
| Expanded K sensitivity | Existing inputs plus all nine K windows, with the same regularisation budget. |

Start with fixed regularised linear regression. Add a predeclared compact companion input set: 30/90/180-day Sharpe, 90-day CAGR and 90-day signed drawdown, with the same old-versus-old-plus-K pairing. The full existing inventory remains available; the compact arm measures dilution/redundancy without retrospectively selecting favourable features. Use one model per target/horizon; pooling horizons is outside the primary comparison. No vault address/name as a predictor and no model including a catalogue of composite scores.

Use ridge alpha=10 with training-only standardisation and total fitting weights normalised to the number of distinct training origins, so alpha does not change meaning when vault counts grow. No primary hyperparameter search. A deferred nonlinear sensitivity may use a depth-2 boosted tree, 100 iterations, learning rate 0.05 and minimum leaf rows `max(20, ceil(0.05 * training_rows))`; audit leaf distinct-origin counts afterwards instead of assuming a library implements date-count constraints. Run this only after the support audit permits it, without selecting settings on evaluation labels. Check installed library/API support at implementation. Feature grouping, transform scales, imputation and reduction are training-only.

### Chronological fitting and evaluation

1. Build a coverage timeline before fitting, separately for all nine target/horizon combinations. Establish which early labels are actual observations; never create extra training support from filled pre-2026 labels.
2. Refit monthly with an expanding historical training window. Predict on the fixed four-day origins until the next refit. Every included training label must have matured before refit time; a naive split by its origin is insufficient.
3. Keep the fixed primary settings. If later work authorises tuning, use earlier chronological folds and purge training labels crossing validation boundaries; apply maturity within each fold. Keep all vaults at a given origin together. No random vault/date row split.
4. Require at least 20 target-valid training origins, 10 distinct vaults and three non-overlapping horizon-length calendar blocks for the supported-model tables. These are minimum screening gates, not proof of sufficient statistical power. Show exploratory forecasts failing the gate separately or abstain; do not use them to choose winners.
5. Evaluate paired forecasts against constants, persistence and the quality/age baseline, with all dates weighted equally and each date's vaults sharing that date's weight. Report quarter and rolling performance, train/evaluation dates and retraining support for every arm.
6. Repeat on origins spaced at least h days apart and on the four cadence phases as dependence sensitivities. Blocks for uncertainty must be at least horizon length; compare longer blocks and state the number of genuinely usable blocks. Whole-date blocks preserve common market shocks; leave-vault-out diagnostics assess concentration/transfer, not extra temporal independence.

The 2026 reporting span contains only about three 90-day windows before censoring, and fewer after supervised warm-up. A large number of vault rows cannot repair this. Expect **90-day results to be descriptive**, with models abstaining under the support gates; still produce all requested features, labels and relationship charts. Any separately displayed thin-support forecasts are explicitly unsupported. Expect **30-day forecast comparisons to be exploratory**. The **7-day** horizon is the only candidate for stronger retrospective inference, subject to its actual support and noisy labels. Compute exact supported refit/evaluation origins from the audited data rather than copying estimates from the review. All periods here have already been researched; chronological evaluation is not an untouched final holdout.

Evaluation uncertainty requires at least **eight non-overlapping horizon-length calendar blocks**, plus paired forecasts from both arms in those blocks. Below that screening gate, show block-level differences and sign counts without confidence intervals or p-values. Eight blocks is still a minimum, not a guarantee of reliable inference; longer-block sensitivities can reduce support further. Freeze future evaluation dates from the actual maturity and block requirements, rather than assuming another month's data resolves 90-day evidence.

## Analyses and interpretation

### Individual feature relationships

For every existing/new K feature × target × horizon, calculate within-origin Spearman IC, equal-date mean/median, paired vault count, variable-feature count and coverage. Show quarter stability, tie-aware feature quantiles and forward target distributions. Show feature redundancy heatmaps with pair counts and a common-cohort companion. Do not pool repeated observations into a single significance calculation or label high redundancy as predictive skill.

Compute IC only with at least ten paired vaults and non-constant inputs/outcomes. Paired model IC changes use identical vaults and origins with both correlations defined; disclose dates lost to constant predictions. Constant and zero-return controls are evaluated with losses, not an invented zero IC.

### Incremental forecasting value

Report equal-date forecast errors, rank IC, paired changes versus baselines and old-plus-K versus old, calibration slope/intercept and coverage. **Incremental cross-sectional rank IC** is the primary measure of whether K helps distinguish vaults; show raw-level losses as essential companions for the requested unit forecasts. Add date-demeaned log-return loss to separate common market moves from vault differences. Realised date means are an evaluation diagnostic only, never a contemporaneously available predictor or deployed adjustment. Use whole-date block uncertainty when supported. Present all nine target/horizon comparisons together; if making formal inferential claims, use Holm correction across the nine paired full-panel ridge comparisons, with other lookbacks/models exploratory. Do not select a K lookback using the retrospective feature leaderboard.

The user-relevant headline is **30-day future CAGR**, evaluated as log return, but available data may not support a formal test there. The predeclared primary inferential comparison, if supported, is **7-day CAGR rank-IC improvement from adding K**; all other target/horizon results remain visible. Report a 5% paired log-return MAE reduction as a practical exploratory marker, not a statistically resolvable gate. Require positive paired incremental IC, compare levels with constant/zero/persistence controls and check the effect's sign after leaving out each influential vault/calendar block. If the sign changes, describe concentration rather than suppressing the result. “Inconclusive” applies when support cannot distinguish benefit from noise.

### Robustness and additional feature checks

- Separate young/old vaults, complete/partial feature availability and actual/non-stale marks. Repeat on a common high-quality cohort and report the coverage trade-off.
- Leave one influential vault and one influential event block out of evaluation; preserve the ordinary result alongside these sensitivities.
- Compare K against growth slope and signed R², and quantify how much of its ordering is already represented by Sharpe/Sortino/Calmar. Conditional residual diagnostics must use training-only fits.
- Regress transformed K on same-window Sharpe within training only, then forecast with its out-of-sample residual. Compare bounded path-shape controls (lag-one return autocorrelation, five-day variance ratio, positive-day fraction and flat-run length) to distinguish path information from reporting artefacts. Do not use unstable K/Sharpe division near zero.
- Decompose realised Sharpe associations into future mean-return and volatility predictability, using historical/EWMA volatility controls. Smoothness persistence alone does not establish prediction of profitable returns.
- Compare daily K with K on genuinely observed weekly endpoints as a staleness diagnostic. Use explicit weekly sample counts/frequency (365/7 for fixed seven-day intervals), aligned windows and enough points; do not compare their raw scales as interchangeable.
- Use block-shift or date-preserving null checks and cadence phases to expose persistence/common-date structure; reject permutations that create fake independent observations.
- Inspect feature stability, extreme K values, seven-day annualisation tails and model sensitivity to robust training transformations. Predeclare transformations; do not select a clipping region on future evaluation labels.
- Test observation-time delay and source-compatible versus strictly observed input panels. A delayed-execution sensitivity shifts the label start and end together, preserving h returns, rather than changing inputs alone. If market controls are added, align vault/BTC/ETH interval endpoints first and fetch references with `tradingstrategy.binance.price.fetch_binance_price()`.
- Show disappearance/target-missing patterns and plausible labelled bounds where outcomes are truly unobserved. Do not turn an unsupported bound into a realised label.

## Notebook and output design

### Deliverables

Implement `09-research-k-ratio-feature-forecasts.ipynb`, reusable feature/label/model/report helpers, and `09-k-ratio-feature-forecast-findings.md`. Generated datasets, images, model caches, logs, manifests and Claude raw review belong under an ignored `_artifacts*/09` directory. The notebook heading must reproduce the user goal and the final reviewed method, including the feature-level scope and `missing=True` interpretation.

### Visual structure

Every element follows **subheading → short clear description → table/chart**. Every chart title gives **2026-01-01 → 2026-10-05 (end exclusive, UTC)** and the target horizon; secondary periods have their actual dates instead. Quarter means forecast-origin quarter. Each image is separate with its own heading; no merged images or collations.

The main notebook includes coverage/missing-reason heatmaps, feature-to-target IC heatmaps separately for each target/horizon, K redundancy maps, old-versus-old-plus-K loss-difference heatmaps, chronological calibration/support tables and quarterly stability charts. Add separate predicted-versus-realised scatter charts for all three targets × three horizons, quarter colours, identity line and clearly labelled descriptive trend. Add individual K-feature versus realised-target scatters, with raw/transform units explicit; page the exhaustive feature inventory into linked small appendices rather than embedding hundreds of images in the main file. Calculations always use the full sample, even if a deterministic display-only subsample is required for clarity.

If a horizon has no supported model forecasts, show a clear support notice in its forecast section and still plot the requested feature/realised-label relationships. Any illustrative thin-support model forecasts must be separately labelled and excluded from winner tables, confidence intervals and claims of forecast improvement; do not draw an empty prediction scatter as evidence of no relationship.

Blank cells must explain insufficient/constant data, not show artificial zeros. Include counts and censoring beneath visuals; distinguish no model support from no apparent predictive relationship. Keep progress/stdout out of saved outputs, colour key tables sensibly and use existing chart helpers where appropriate. Before considering the implementation complete, execute with the observable repository runner, preview through its static notebook server and visually inspect every separate chart, including appendix charts. Check that VS Code can render the saved notebook; keep its payload bounded (aim below 10 MiB, splitting appendices when needed).

## Implementation sequence and completion criteria

1. Inventory experiment-05 feature formulas, caches, origins and eligibility; reproduce representative feature values and its 14/30/60-day diagnostics as a compatibility audit. Keep these old horizons in the audit, not the new report grid.
2. Independently audit feature/label timing and the K formula: sign, scaling invariance, sample count, flat/linear/near-linear paths, return ordering, zero-risk labels, missing-day gaps, young vaults and right censoring. No framework or strategy changes are required by this plan.
3. Build one shared raw feature/label dataset with provenance, target-specific missingness and manifests. Verify the same-input comparison arms and partial-history forecasts before fitting the model grid.
4. Produce chronological predictions, baseline comparisons and feature analyses. Stop unsupported tuning paths early; retain the requested horizon's descriptive outputs and explain missing support.
5. Generate bounded notebooks/appendices, inspect each visual, and write findings stating which features add information, which merely duplicate existing inputs, and where the evidence is insufficient.
6. Freeze selected model definitions and the next prospective confirmation window before receiving new target outcomes. Count required independent future blocks explicitly; mature 90-day labels before evaluating that horizon.

Completion requires reproducible feature/label audits, explicit `missing=True` and target-missing tests, all nine target/horizon outputs, paired incremental results with support disclosure, visually reviewed separate charts and a concise conclusions file. No claim that K improves a portfolio is made without a later executable strategy experiment.

Deferred ideas: empirical-Bayes reliability/shrinkage and 7/14-day or since-inception inputs for vaults younger than 30 days; flow/depositor features with audited historical timestamps; fill-based NAV verification; unsmoothing models; additional model families. These need separate assumptions or inputs and should not expand the primary experiment before it answers whether K adds information to the existing features. Record prospective daily observations and actual observation/publication clocks now when implementing, to support later confirmation.

## Claude review

Reviewed on **2026-10-09** with Claude CLI **2.1.281**, requested model **`claude-opus-5-5`**, effort **high**. The successful JSON response confirms **`canonicalModel: claude-opus-5-5`**, first-party provider, with no fallback configured. Tools were disabled; Claude reviewed the written draft plus actual experiment-05 feature-audit code and the local glossary excerpt. Its verdict on that draft was “not ready to implement”, identifying definition and design changes.

The plan has now been revised to address fitted-point alignment, limited support, fixed models, common-date effects, own-target persistence, explicit calendar gaps and matched missingness controls. The detailed [review disposition](09-k-ratio-feature-forecast-review.md) records accepted suggestions, assumptions rejected and deferred creative ideas. The revised plan has not had a second Claude pass. Raw prompt/draft/response/model metadata and the author's retrieved paper are retained in ignored `_artifacts-restored-2026-10-07/09/plan-review/`.
