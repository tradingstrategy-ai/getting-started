# Experiment 09 notebook and verdict review

## Review scope

Reviewed on 2026-10-09 with **Claude Opus 5.5**, using Claude CLI 2.1.281 and the exact model identifier `claude-opus-5-5`, high effort. The response confirms that canonical model and the first-party provider; there was no fallback. The read-only review completed successfully, without permission denials. All submitted source and notebook fingerprints still match after the review.

The packet included the reviewed plan, executed [experiment 09 notebook](09-research-k-ratio-feature-forecasts.ipynb), [written findings](09-k-ratio-feature-forecast-findings.md), notebook builder and six helper modules, complete model and sensitivity result tables, numerical audits and chart paths. Claude inspected **16 of the 96 separate chart PNGs**. Its visual findings apply to that subset; this is not a second inspection of every chart.

Default evaluation period: **2026-01-01 → 2026-10-05, end exclusive, UTC**. The pinned archive SHA-256 is `30ec7e9dfa7eb236518cf1922a9ba82f4f42cfbfb041c06f5db3273d114aa8f2`.

## Assessed verdict

**Requires corrections before the absolute forecast claims or prospective design can be relied on.** The time alignment, matured-label fitting, provenance, K formula and paired old/new comparisons received a positive review. The numerical results describe the fitted models, but do not establish that the feature set lacks predictive information.

A defensible current conclusion is:

> No robust incremental benefit was established for the four additional K-ratio inputs in the current fixed models. Primary estimates are small and negative; several 7-day estimates change sign under cadence, delay and source sensitivities. These findings do not establish that K-ratio lacks useful information. No supported 90-day comparison was obtained.

This assessment leaves the original notebook, findings and frozen design untouched. The full independent Claude response is preserved below, including claims that need the qualifications in this assessment.

## Confirmed issues and disposition

### Extreme extrapolation is the main correction

Only the K-named inputs receive the asinh transform. Annualised CAGR, Calmar and unfloored Sharpe/Sortino enter the full ridge model without comparable tail control. Training-only standardisation prevents leakage, but does not prevent a later observation from being far beyond the training range. The inverse sinh for K-target forecasts then greatly amplifies extreme predictions.

Saved results confirm that Existing + K has 7-day log-return MSE **16.760225**, compared with **0.225513** for Constant, approximately **74 times** larger. At 30 days the values are **853.387260** and **1.275586**, approximately **669 times** larger. The CAGR calibration slopes are **0.000277** and **0.000599**. A supported 7-day raw K-target prediction reaches approximately **−7.14 × 10¹⁸⁰**.

This supports a diagnosis of severe extrapolation and poor calibration. It does not justify interpreting baseline underperformance as evidence that the inputs themselves are useless. Rank IC is still a descriptive result of these models, but changing their preprocessing can change their rankings too.

The correction should be a predeclared robust input representation, with an explicitly measured extrapolation policy and target-aware inverse-transform safeguards. Compare the existing and K-augmented arms on identical rows again, then amend the prospective specification. Clipping a chart does not correct the forecast.

**Qualification to Claude:** its calibration range of 0.0002–0.0009 applies to the full CAGR arms, not every target and model. Some Compact K forecasts also have extreme tails; those models should not be described as bounded.

### The incremental K verdict needs narrower wording

On strict inputs, CAGR ΔIC remains negative across all four cadence phases at both supported horizons. At 7 days, Sharpe and K ΔIC change sign across phases; all strict 30-day phase estimates are negative. The primary 7-day CAGR band crosses zero when the block length increases to 14 days, and the 30-day comparison has only three non-overlapping blocks.

Retain the numerical primary contrasts and disclose the sensitivity sign changes. Replace “evidence against K” with the qualified conclusion above.

**Qualification to Claude:** changes within approximately ±0.02 are observed point estimates. They are not confidence bounds on the true effect, nor proof of a negligible effect. “No detectable benefit” should not imply a formal equivalence test.

### Partial-history and complete-case diagnostics do not answer the young-vault question

Strict 270/360/730-day inputs are unavailable throughout this evaluation. Consequently **all 84,147 primary Existing + K forecasts** have fewer than all 45 existing inputs, while the complete-case arms produce no forecasts. “Partial history” therefore duplicates the entire paired cohort.

The adapter does mechanically support `missing=True`. Predictive usefulness for short-history vaults still needs a non-vacuous cohort comparison against the same-row baselines. Recorded-history age is time since the first archived observation, not verified inception age. Define completeness over an explicitly supported inventory, and keep true age separate if reliable inception metadata exists. Vaults with less than 30 days of continuous history currently abstain.

### Low-activity paths need a sensitivity, not an assumed data defect

For h daily returns containing one non-zero return and h−1 zeros, sample Sharpe is `sign(return) × sqrt(365/h)`, independently of return magnitude. K likewise depends on the step's sign and position. This explains discrete stripes and limits the interpretation of smoothness or persistence signals.

**Qualification to Claude:** these patterns do not prove stale observations. Unchanged genuinely observed NAVs can result from inactivity or reporting precision. Diagnose actual activity, flat runs, precision and collector gaps, and add predeclared sensitivity cohorts. The suggested minimum number of non-zero returns is a proposed sensitivity, not an established validity requirement. Do not delete genuine zero-return observations on this evidence alone.

### Additional corrections and missing comparisons

The review identified hard-coded verdict text that can become stale on rerun; a squared-loss Sharpe model despite the planned robust loss; raw K persistence inputs without their own missingness indicator; gate-eligible skill reported only as population counts; and unequal calendar/cohort support in lookback and weekly comparisons. These warrant generated result-dependent prose, explicit target-aware transforms, and matched-population diagnostics.

The pooled level-fitting objective is a design limitation for within-date rank IC. A date-centred or rank-target companion could answer the ranking question, but should remain separate from an absolute level forecaster. These are feature-forecast comparisons, not an instruction to change selection or portfolio weighting.

The existing zero-fill sensitivity retains shared missing indicators. That is a legitimate paired adapter comparison, but it should be labelled **zero-fill with indicators**. It does not reproduce a legacy composite selector's unscored-entry behaviour; the plan did not promise such a selector replay.

## Checks on unverified concerns

### Zero NAV observations

An independent scan of the pinned archive for the 514 selected addresses found **35 non-positive marks, all zero, for one address**, `0x117648bb0e09517af02877a6df8fdd85e533dbb7`, dated **2026-03-07 → 2026-04-10**. Every mark also has zero total assets and zero total supply; there are no negative prices in this selected set.

The positive-NAV filter does remove these marks. However, zero assets and zero supply do not establish that an investor suffered a −100% loss: the share price may be undefined for an empty vault. The archive alone does not resolve this. Verify the vault's preceding assets, shares and liquidation/redemption history before assigning a terminal-loss outcome. The audit output is saved among the ignored review artefacts.

### Historical universe completeness

Experiment 09 inherits experiment 08's identities, which derive from the frozen research universe. The universe loader uses all vault pairs in that snapshot. The strategy builder includes closed vaults and avoids a small ranking cap, but starts from a discovered source universe with a minimum-TVL parameter and optional manifest membership.

That establishes snapshot conditioning; it does not establish a complete historical population or prove that a particular survivor filter caused the findings. A listing/inception audit against an independent historical inventory is still required. Current guard membership is not a primary feature in this experiment.

## Recommended next action

Create a bounded, explicitly amended follow-up before interpreting absolute forecast errors or locking the prospective model: robust causal inputs; monitored extrapolation and K inversion; robust Sharpe loss; meaningful short-history and label-activity cohorts; same-row baseline and gate-cohort comparisons; matched lookback/weekly comparisons; and verdict text derived from the results. Preserve the current experiment as the original exploratory run.

Loss-tail prediction, sign versus smoothness decomposition and matched weekly K are promising secondary questions. Any disappearance target must be labelled as an archive-coverage event unless an actual closure or loss is independently established.

## Full Claude Opus 5.5 review

The following is Claude's original response, preserved verbatim. Where it differs from the evidence or makes a stronger interpretation, the disposition above takes precedence.

---

# Independent review: experiment 09, K-ratio features and future vault performance

## 1. Overall verdict

**Requires corrections.** The results can be shared as exploratory research only if the claims are narrowed first.

- **Pipeline: sound.** Timing, maturity, provenance and same-row pairing are implemented carefully. The K formula matches the declared Kestner 2013 convention, and the experiment-05 reproduction is exact.
- **Main incremental result: survives in narrowed form.** On this archive, adding 30/60/90/180-day K to the fixed ridge models gave **no detectable improvement** in within-date rank IC at 7 or 30 days. The better-conditioned Compact arm shows the same direction.
- **Level-error verdicts and the frozen design: not valid as stated.** The full-inventory models feed raw annualised CAGR, Calmar and unfloored Sharpe/Sortino into a linear model without bounding them, and they extrapolate badly. Calibration slopes are about 0.0003. MSE is 74 times the constant forecast at 7 days. Raw K-target MAE reaches about 10¹⁷⁶. So "the model loses to constant/zero/age baselines" describes a preprocessing defect, not the features. The frozen prospective design currently locks in that defect.
- **7-day Sharpe and K labels:** these are partly shaped by stale-mark artefacts that I could see in the charts. The persistence/smoothness interpretation needs that caveat.
- **The `missing=True` young-vault question is mechanically demonstrated but not answered.** Every forecast is "partial history", the complete-case arms are empty by construction, and "age" means time since the first archive observation, not vault inception.

**Scope:** 2026-01-01 → 2026-10-05 (end exclusive, UTC), current-snapshot universe of 514 vaults. This is already-researched history and observation-time replay. 90-day results are descriptive only.

## 2. Findings

### Blocker

**B1. Unbounded raw-unit inputs cause catastrophic extrapolation. This invalidates the level-error verdicts and the frozen design.**
- **Where:** `k_ratio_forecast_models.py:58-95` (`FoldAdapter`), with feature definitions at `k_ratio_features.py:101-111`.
- **Mechanism:**
  - Only columns containing `K-ratio` are asinh-transformed (line 62).
  - Annualised 30–180-day CAGR (`expm1(logret*365/L)`), floored Calmar (CAGR/≥1%) and unfloored Sharpe/Sortino stay in raw units. Their training mean and std are dominated by a few extreme rows, and `transform` (lines 89-95) does not clip test z-scores to the training range.
  - Test rows beyond the training extremes get z-scores in the thousands, which then multiply ridge coefficients.
- **Evidence:**
  - Calibration slopes of 0.0002–0.0009 for every full-inventory arm. K alone, Compact and Quality/age are 0.4–1.1.
  - 7-day log-return MSE: 16.7 for Existing versus 0.226 for Constant.
  - Raw K-target MAE: 6.6×10¹⁷⁶ for Existing + K versus 7.4 for Constant.
  - Phase-1 7-day CAGR MAE change of +55.7%.
  - In `forecast-7-CAGR.png` (inspected), predicted CAGR runs from −100% to beyond 10⁵%. There is a dense horizontal band of realised ≈0% at predicted 1,000%–100,000%, which suggests stale vaults with one large historical jump.
- **Impact:**
  - Every "Existing + K versus constant/zero/age baseline" level comparison reflects this defect (43%/115% worse than constant; 64%/174% worse than zero return).
  - The paired ΔIC is less affected because it is rank-based. But the CAGR/Calmar columns behave as outlier detectors rather than informative inputs, so "Existing" is effectively a smaller feature set than advertised.
  - `freeze_design` (`k_ratio_forecast_report.py:377-395`) freezes this configuration for the 2026-10-12 confirmation.
- **Correction:**
  - Apply one predeclared robust transform to every ratio input inside each fold:
    - either within-date percentile rank (causal; uses only same-date features),
    - or asinh with a training-median-absolute scale, plus clipping of test z-scores to the training [min, max] or ±5.
  - Keep CAGR inputs as h-day log return rather than annualised CAGR.
  - Re-run all arms, re-freeze before any post-2026-10-05 outcome is seen, and record the change as a protocol amendment.

### High

**H1. Stale and near-flat paths create magnitude-free Sharpe/K labels and features. Plan promised quality sensitivities that were not run.**
- **Where:** `k_ratio_features.py:84-112` and `39-81`; labels at `build_labels` lines 274-296.
- **Mechanism:**
  - For an h-day path with one non-zero return r and h−1 zeros, `mean/std(ddof=1)*sqrt(365)` = sign(r)·√(365/h), whatever the size of r. That is ±7.22 at 7 days and ±3.49 at 30 days.
  - K on a single-step path is likewise a deterministic function of step position and sign only.
  - `forecast-30-Sharpe.png` (inspected) shows a horizontal streak at about −3.5. `forecast-7-K-ratio.png` (inspected) shows streaks in the lower cluster.
  - `feature-coverage.png` (inspected) shows 80% coverage for 30-day CAGR/drawdown but 68% for Sharpe. So about 12% of observed anchors have perfectly flat 30-day NAV.
  - The future-volatility IC of `flat_fraction_30` is −0.59.
- **Impact:**
  - 7-day Sharpe/K targets and features partly measure "rare tick sign and timing".
  - Sharpe→Sharpe and K→K IC can come from this marking pattern, not from return skill or volatility persistence.
  - Ties at zero also affect Spearman IC for the CAGR targets.
- **Correction:**
  - Add a predeclared label-quality rule as a parallel primary sensitivity, for example at least ⌈h/2⌉ (and at least 4) non-zero daily returns for Sharpe/K labels and features.
  - Report a stale cohort (`longest_recent_flat_run`, `flat_fraction_30` above a threshold) separately.
  - Run the plan's "stricter numerical/price-quality rules" sensitivity (plan §K-ratio convention, last paragraph).

**H2. "Evidence against" K overstates the support. Signs are not robust outside phase 0.**
- **Where:** `k_ratio_forecast_report.py:368` (findings text); paired_summary.
- **Mechanism:**
  - The 7-day Sharpe and K deltas are positive in 3 of the 5 non-primary sensitivities: delay=1 (+0.0060 / +0.0027), phase 1 (+0.0047 / +0.0026) and phase 2 for K (+0.0019). source=True is also positive for 7-day CAGR (+0.0050) and K (+0.0013).
  - The 7-day block bands include zero for Sharpe and K. Only 7-day CAGR excludes zero, at [−0.0177, −0.0008] with 7-day blocks, and that band crosses zero with 14-day blocks [−0.013, +0.0006].
  - At 30 days there are 3 blocks, and leave-one-block-out flips sign for all three targets. `quarter-K-ratio.png` (inspected) shows 30-day Q2 +0.004 versus Q3 −0.020.
- **Impact:** the data support "no detectable benefit; effects below about 0.02 IC in magnitude". They do not support a measured harm, except a weak, exploratory, consistent negative for 7-day CAGR.
- **Correction:** replace the wording (see §3).

**H3. The `missing=True` young-vault question is not answered. Two diagnostics are vacuous.**
- **Where:**
  - `k_ratio_forecast_statistics.py:225`: the "Partial history" cohort is `observed_inputs < 45`.
  - `k_ratio_forecast_models.py:228-235`: complete-case requires all of `perf_columns`.
  - `k_ratio_features.py:142, 168`: `age_days` measures from the first archive observation.
  - `k_ratio_forecast_extensions.py:37`.
- **Mechanism:**
  - 270/360/730-day windows are never available, so every row is "partial". The "Partial history" cohort is identical to "All paired", and `actual_partial_history_forecasts = 84147` is trivially every forecast.
  - Complete-case therefore has zero support everywhere.
  - The `Young <180d` cohort mixes genuinely new vaults with vaults whose archive daily coverage starts late. The fact that 270-day coverage is 0% for every vault implies continuous daily data starts around the turn of 2026 for everyone.
  - Vaults with less than 30 days of history abstain (deferred by design). No young-cohort accuracy against baselines is reported, only ΔIC.
- **Correction:**
  - Define partial and complete-case over the windows that are actually available (30–180 days).
  - Take inception dates from `vault-metadata.json` (if available) and split true age from archive age.
  - Report young-cohort IC/MAE for Existing, Existing + K, Quality/age and Constant on the same rows.

### Medium

**M1. Findings and notebook narrative are hard-coded rather than computed.**
- **Where:** `k_ratio_forecast_report.py:367-371` and `create_k_ratio_forecast_notebook.py:29-31`.
- **Mechanism:** "All six … negative", "64% … 174%", "0.91" and the header "Key new insights" are literal strings. A re-run on different data would publish stale claims.
- **Correction:** generate these sentences from `paired_summary`, `extension-baseline_pairs` and `extension-redundancy_support`, with assertions guarding the qualitative wording.

**M2. Model objective does not match the plan or the primary metric.**
- **Where:** `k_ratio_forecast_models.py:248-251`.
- **Mechanism:**
  - Pooled squared-loss ridge on level targets that include common date moves.
  - The raw Sharpe target is heavy-tailed. The plan promised a "robust loss" for Sharpe; none was implemented.
  - The primary measure is within-date rank IC, which the fit does not target.
- **Correction:** fit on date-demeaned or within-date rank-Gaussianised targets for the IC question (labels are only used inside the training fold, so this is causal). Use Huber loss for Sharpe. Keep the level models separately for the unit forecasts.

**M3. Persistence arms are inconsistent with the K transform policy.**
- **Where:** `k_ratio_forecast_models.py:224-226`.
- **Mechanism:**
  - `past_target` enters raw: past 7-day K is not asinh-transformed, unlike all other K inputs.
  - It has no missing indicator, because `mask_columns` covers only `EXISTING+K_ALL`.
  - Separately, indicator columns such as `missing 30d K-ratio` match `'K-ratio' in name` (line 62) and are asinh-transformed. That is harmless (monotone 0/0.88) but unintended.
- **Correction:** transform `past_target` like K when the target is K, add its indicator, and match on an explicit list of K feature names rather than a substring.

**M4. The investable population is not evaluated.**
- **Where:** `k_ratio_forecast_statistics.py:167-180`; plan §Population.
- **Mechanism:**
  - The IC is computed over about 380 vaults per date.
  - The 05 gate-eligible, deposit-feasible set is 5,977 rows (270 vaults), and the 05 baseline allocated to only 35 vaults.
  - The plan's "05 gate-filtered population as a secondary comparison" appears only as counts.
- **Impact:** a K increment could differ in the cross-section that matters.
- **Correction:** repeat the paired ΔIC within the caveated gate population, labelled as current-policy membership.

**M5. Universe and NAV-filter choices may bias labels (unverified).**
- **Universe:**
  - Identities come from `08/eligibility.parquet` (`k_ratio_features.py:120-122`).
  - *Unverified suspicion:* if 08's identity list applies any current-snapshot filter (TVL, listing, whitelist), the universe is selected on future survival.
  - Check how 08 built it and report vault counts per origin against an independent historical listing.
- **Non-positive NAV:**
  - `share_price > 0` at line 128 turns a wipe-out to zero NAV into a missing label instead of −100%.
  - Magnitude is probably small (CAGR "other missing" is 1–9%), but these are exactly the losses K might predict.
  - Count zero or negative marks and add a −100% terminal sensitivity where the zero is a genuine observation.

**M6. Sharpe/K label attrition is large and not characterised.**
- **Where:** target_coverage; `extension-target_attrition`.
- **Mechanism:**
  - At 7 days, 30% of observed anchors lack a complete daily path, against 4.5% missing for CAGR.
  - Missingness is higher in the ≥180-day cohort (32.6%) than the young one (25.5%).
  - `k-missing-reasons.png` (inspected) shows 27–38% "missing actual daily marks" across windows.
  - Attrition is split only by age, not by flat-run, closure or gap pattern. The plan promised closure, permission and stale-price cohorts.
- **Correction:** establish whether gaps are date-wide (collector outages) or vault-specific. Report attrition by stale and gap cohort. Note that CAGR, Sharpe and K results describe different populations.

**M7. The `missing=False` legacy arm is not the legacy semantics.**
- **Where:** `k_ratio_forecast_models.py:70, 80-85` together with line 226.
- **Mechanism:** zero-fill is applied, but the 54 missing indicators remain. In a linear model those indicators absorb the fill value, so zero-fill and median-fill nearly coincide by construction.
- **Correction:** drop the indicators in the legacy arm, or label it "zero-fill with indicators".

**M8. Lookback availability is confounded with calendar period.**
- **Where:** `ic-7-CAGR-2026.png` (inspected) shows n=56 origins at 30 days and n=18 at 180 days.
- **Mechanism:** 180-day features exist only in later origins.
- **Impact:** cross-window IC differences (and the weekly comparison) partly compare quarters, not lookbacks.
- **Correction:** add a common-origin, common-vault companion for each window comparison.

### Low

- **L1. Audit "checks" that cannot fail.** In `k_ratio_forecast_audit.py:138`, `label_end_before_available_clock` is tautological. At line 140, `terminal_or_closed_labels_fabricated = 0` is a constant. At line 139, the young partial count follows from age alone. Relabel them as descriptions or make them real checks.
- **L2. Table formatting.** Raw K MAE prints as 170-digit numbers (`model_summary` display). Use scientific format or suppress the column when it is not finite in a meaningful sense.
- **L3. Chart readability.** All observed in inspected PNGs:
  - The 7-day CAGR y-axis reaches 1e+14% with odd ticks (3e+09%).
  - The 90-day K axes have only ±10⁰/0 ticks.
  - The 90-day CAGR x-axis has no positive tick.
  - The 1% display trim on the 90-day K illustrative chart (`k_ratio_forecast_report.py:193`) hides the extrapolation that B1 explains. It is disclosed (73 points) but should be diagnosed, not trimmed.
  - Make h-day log return the primary forecast scatter and show annualised CAGR as secondary.
- **L4. Missing counts in heatmaps.** The redundancy and weekly heatmaps lack pair counts (`redundancy-30.png`, `weekly-Sharpe.png`, inspected), which the plan required.
- **L5. Weekly 30-day K window.** It spans 28 days (`k_ratio_features.py:232`, offsets 0…28). Disclosed only generically.
- **L6. Degeneracy tolerance.** `max(syy, 1)` (`k_ratio_features.py:70`) makes the tolerance effectively absolute for low-variance paths, so near-flat rounding paths produce defined, extreme K. This links to H1.
- **L7. Unreported diagnostics.** Feature-IC quarterly stability is computed (`quarterly`) but not displayed. The unfloored Calmar diagnostic is computed but not reported. Constant-arm calibration slopes are reported although they are meaningless.
- **L8. Bootstrap structure.** 7-day blocks with 7-day labels overlap adjacent blocks, and the bootstrap resamples block means as if independent. This is acceptable as an exploratory band and is already caveated.
- **L9. Display-only.** VS Code rendering was not verified (macOS permissions). Treat it as open.

### Unmet plan promises

| Promise | Status |
| --- | --- |
| Robust loss for Sharpe target | Not implemented |
| 05 gate-filtered secondary comparison | Counts only |
| Complete-case sensitivity showing lost vaults | Vacuous (requires 730-day inputs) |
| Compact-control sensitivity (log age, available windows, observed fraction) | Not implemented; all arms use 54 indicators |
| Stricter numerical/price-quality K sensitivities | Not implemented |
| Attrition by closure/permission/stale cohorts | Age only |
| Redundancy maps with pair counts and common cohort | Partial (common cohort for K pairs only) |
| Quarter stability and forward distributions for individual features | Computed, not shown; means only |
| EWMA volatility controls in the decomposition | 30-day volatility only |
| Plausible labelled bounds for unobserved outcomes | Not implemented |
| Record prospective observation/publication clocks | No evidence in code |
| Holm correction | Not needed, since no formal claims are made |

## 3. Audit of written verdicts

| Verdict (source) | Assessment | Replacement wording |
| --- | --- | --- |
| Six per-cell bullets with ΔIC/MAE values (findings, Key findings) | **Supported** as numbers | Add the 7-day bands. Example: "7-day CAGR ΔIC −0.008, 7-day-block band [−0.018, −0.001]; crosses zero with 14-day blocks." |
| 90-day: no supported comparison | **Supported** | Unchanged. Add: "90-day feature ICs rest on about 1–2 non-overlapping windows." |
| "All six … negative IC and small MAE increase" | **Needs narrowing** | "In the primary phase-0 schedule all six deltas are negative and small (≤0.013). In phase, delay and source sensitivities, 7-day Sharpe and K deltas turn positive in several runs; only 7-day CAGR is negative throughout the strict-input sensitivities." |
| "Evidence against adding these four K values…" | **Needs narrowing** | "No detectable rank-IC benefit from adding 30/60/90/180-day K to these fixed ridge models; any effect is within about ±0.02 IC. The Compact arm agrees in direction." |
| "Existing + K loses to constant, zero-return and age/quality controls in CAGR error" | **Unsupported as an interpretation** (numerically true) | "The full-inventory ridge extrapolates on unbounded raw ratio inputs (calibration slope ≈0.0003). Its level errors are not informative about the features until inputs are bounded. Bounded arms (K alone, Compact) are close to the constant at 7 days; at 30 days zero return beats every arm." |
| "64% worse at seven days and 174% worse at 30 days" | **Supported** numerically | Keep it, but only with the B1 mechanism attached. |
| "30-day K and Sharpe ≈0.91 rank correlation" | **Supported** | Unchanged (pairwise 0.910, common cohort 0.910). |
| "Historical volatility predicts future volatility much more strongly…" | **Supported** | Unchanged (0.75 versus ≤0.07). |
| "Much of the available signal describes persistent risk or path smoothness" | **Needs narrowing** | "Volatility and flat-fraction persist strongly. K's and Sharpe's IC with future Sharpe (≈0.12) is not explained by volatility (IC −0.06/+0.01) and may partly reflect stale-mark labels whose Sharpe is ±√(365/h) regardless of size." |
| "Strict 270/360/730-day windows have no complete actual daily history" | **Supported** | Add: "180-day inputs cover 18–19% of anchors and only later origins." |
| "Missing=True produces forecasts with partial histories…" | **Needs narrowing** | "Every forecast uses a partial inventory. Vaults with less than 30 days of continuous archive history abstain. 'Young' means archive-recorded age, and young-cohort accuracy against baselines is not yet reported." |
| "K/signed-R² identity independently checked" | **Supported** (synthetic path) | Unchanged |
| "Current guards … never become primary predictors" | **Supported** | Add: "The vault universe is the experiment-08 identity list." |
| "Flat/exact-linear paths are undefined" | **Supported, incomplete** | Add: "Near-flat single-step paths remain defined, with size-independent values." |
| Notebook header: "risk and smoothness persistence are stronger than future growth relationships" | **Needs narrowing** | Same replacement as the smoothness row above. |
| Notebook header: "fixed models also lose to simple baselines in absolute CAGR error" | **Unsupported as framed** | Same replacement as the level-error row. |

## 4. What is implemented correctly

- **K definition.** Anchor-included intercept OLS with n = L+1 and √365/n. Independently verified against `lstsq`, the signed-R² identity, first-return influence, scale invariance, reversal symmetry and gap non-compression. The endpoint-convention sensitivity is stored separately (ρ = 0.95 / 0.996 / 0.999 at 7/30/90 days).
- **Provenance.** Raw `share_price` equals the 08 `raw_close` exactly, observation timestamps match, the archive hash is pinned, and caches are keyed on module hashes.
- **Time alignment.**
  - Features end at the T−1 close.
  - Labels start at the same anchor, with no shared returns.
  - Training requires `label_available_at < refit` (verified in `model-support`: `latest_training_label_at` is always before `refit_at`).
  - The delayed sensitivity shifts both label endpoints.
- **Training-only preprocessing.** Medians, scales, standardisation and K-target asinh scales come from the fold only. Synthetic tests show that test rows cannot change them.
- **Same-row pairing.** Inner join with `validate='one_to_one'`. Identical controls and availability masks in both arms. Equal-date weighting, and IC is undefined below 10 pairs or for constant inputs.
- **Support gating.** 90-day forecasts abstain and the illustrative charts are clearly separated. Thirty-day evaluation is correctly limited to 3 blocks, without intervals.
- **Experiment-05 compatibility.** 5,000 feature cells and 15,210 IC cells reproduced exactly.
- **Diagnostics.** Whole-vault-path placebo, leave-vault and leave-block checks, phase and delay sensitivities, and a source-price sensitivity. Strict inputs give a higher 7-day CAGR base IC (0.056) than carried-price inputs (0.038), which supports the strict panel.
- **Integrity.** No fabricated terminal outcomes. Operational fields stay out of the predictors.

## 5. Follow-up ideas

### Priority order

1. **Experiment 09b (bounded, predeclared):** the same data and arms (Existing versus Existing + K, Compact versus Compact + K), with three fixed changes:
   - (a) within-date percentile ranks for all ratio inputs, with asinh plus training-range clipping as a sensitivity;
   - (b) date-demeaned targets for the IC objective and Huber loss for Sharpe;
   - (c) the stale-label quality rule from H1 as a parallel primary sensitivity.

   Headline: 7-day and 30-day CAGR as log return, with 7-day and 14-day blocks. Re-freeze the prospective design afterwards.
2. **Loss-tail targets.** `quintiles-CAGR.png` (inspected) shows the lowest 30-day K quintile averaging about −0.27 30-day log return, against about −0.06 to −0.08 in the middle quintiles. That is non-linear "loser" information that ridge and Spearman under-weight. Forecast P(h-day log return < −10%/−20%) and P(the series disappears) per date, scored with within-date AUC and Brier. This is still a feature forecast, not a portfolio rule.
3. **Separate sign from smoothness.** 30-day K is strongly bimodal (`feature-30d K-ratio-30-CAGR.png`, inspected: few values with |K| < 1). Test |K| within positive-return and negative-return vaults separately, and the existing residual-K against bounded Sharpe ranks.
4. **Gap-tolerant comparison on matched rows.** Weekly K matches or beats daily K in IC (180-day: 0.13 versus 0.08 for 30-day Sharpe) while needing fewer marks. Compare on identical rows to see whether the strict daily rule discards information or selects a cohort.
5. **True inception age** from metadata, plus empirical-Bayes shrinkage of short-window K toward the cross-sectional median. This is the deferred young-vault idea, now well motivated by H3.

### Useful baselines

- Within-date rank of past h-day return.
- Sign of past h-day return (for the K target).
- `flat_fraction_30` alone (for the Sharpe/K targets).
- 30-day volatility alone (for Sharpe).
- Sharpe alone at the same window, as K's closest substitute.
- Zero return, kept, since it beats every arm at 30 days.

### Investable-cohort check

Repeat the 09b ΔIC within the caveated 05-gate population to see whether the null result holds where positions are possible.

## 6. Bottom line

Experiment 09 is carefully engineered, with sound timing, maturity, provenance and pairing. It supports one narrow conclusion: **adding the four predeclared K windows did not measurably improve within-date ranking of future 7- or 30-day CAGR, Sharpe or K in these fixed ridge models.** 90-day questions are unanswered.

**Corrections needed before trusting or publishing:**
1. Bound or rank-transform every ratio input and clip extrapolation. Re-run, and re-freeze the prospective design before any new outcomes arrive (B1).
2. Withdraw or reword the "loses to constant/zero/age baselines" claims until (1) is done.
3. Replace "evidence against K" with "no detectable benefit; effects within ±0.02 IC". Disclose the phase and delay sign flips for 7-day Sharpe and K (H2).
4. Add a stale-mark label filter and caveat the smoothness interpretation (H1).
5. Fix the vacuous "Partial history" and complete-case diagnostics, and use true vault age (H3).
6. Generate the findings text from the result tables instead of hard-coding it (M1).

I inspected 16 of the 96 chart PNGs: the 7/30-day CAGR, 7-day K and 30-day Sharpe forecasts, the 90-day CAGR and K illustrative forecasts, 30-day K versus 30-day CAGR, feature coverage, K missing reasons, 7-day CAGR IC, 30-day CAGR K quintiles, K by quarter, paired ΔIC, future mean-return components, 30-day redundancy, and daily-versus-weekly K for Sharpe. My statements about charts are limited to those.
