# Experiment 08: score forecasts and vault admission thresholds

> **10 October 2026 amendment:** the user requested sparse-data support for all metric families. The complete actual-daily-observation requirement below is superseded by causal calendar-day forward filling, with actual observation masks retained and future labels censored after the last actual vault mark/archive end. See [current summary](summary.md) and [sparse-data audit](sparse-nav-rerun-2026-10-10.md).


## Goal and scope

Written on 2026-10-08. This is an implementation plan; no new notebook or backtest has been run for this experiment.

Understand whether our existing vault scores predict future profitability and risk-adjusted returns, and whether there is a score threshold below which admitting a vault makes the portfolio worse. Generate forecasts every four calendar days. For every distinct scoring method and each **7-, 30- and 90-day lookahead**, plot score against realised **CAGR and Sharpe**, with trend lines and dots coloured by forecast quarter.

Answer three separate questions:

1. **Ranking:** does a higher score identify better future outcomes among the vaults available on the same date?
2. **Calibration:** does an absolute score, or a score relative to its contemporaneous universe, indicate an expected return or likelihood of loss?
3. **Portfolio value:** does refusing low-scoring entries improve an executable strategy after fees, capacity constraints, concentration limits and cash usage?

A current score is a bounded ranking signal, not itself a predicted CAGR or Sharpe. The requested score-versus-outcome plots diagnose that signal. Any forecast in return or Sharpe units must be calibrated using earlier, fully matured labels only. A positive scatter slope alone does not establish a profitable trading rule.

## Existing evidence and starting points

Use the repaired data generation and scoring definitions from experiments 04–07. Do not download a new archive silently or refit the existing scoring coefficients during this analysis.

### Relevant research and reusable code

These references identify the existing methods and explain which parts can be reused. They are implementation sources, not new forecast results.

| Source | Role in experiment 08 |
| --- | --- |
| [04 report](04-score-matrix-analysis.md), `score_matrix.py`, `score_matrix_blends.py` | Frozen matrices, requested/legacy clipping, dense equal scores, missingness semantics and completed daily features |
| [05 notebook](05-opt-score-calibration-selection-cash.ipynb), `score_calibration_experiment.py` | Hard clips, smooth saturation, blended clips, ratio floors and missing-value alternatives; prior feature IC diagnostics |
| [06 report](06-score-3-4-inputs-analysis.md), `score_input_count_experiment.py` | 74 frozen two-, three- and four-input score recipes |
| [07 report](07-score-position-count-analysis.md), `score_position_count_experiment.py` | The same 74 recipes at 6, 7, 8 and 10 positions; evidence that wider portfolios admit weaker scores and alter existing exposures |
| `precompute_repaired_singletons.py`, `repaired_data_replay.py` | Pinned universe, input hashes and source fingerprints |

The focal four-input method is `Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino`: 48% 360-day CAGR, 32% 45-day Sortino, 10% 180-day CAGR and 10% 30-day Sortino, using legacy clipping. Include it alongside original v11, near-v6 360/46 and the two-input Blend 46d control. Their past portfolio results motivate the investigation; they do not establish forecast quality.

**Audit the old label implementation before reuse.** Experiment 05 uses 14/30/60-day labels, a two-day diagnostic schedule and a T−1 valuation anchor. The new experiment needs explicit 7/30/90-day timestamps, a four-day schedule and verified horizon endpoints. Do not change a shift value and assume the result is correct. The actual matrix currently defines the two-year feature as **730 days**, one year as **360 days**, with a separate 45-day compatibility cell; inherit these actual definitions and record them.

## Frozen design and method inventory

### Period and data contract

Default every chart, table and Markdown result to **2026-01-01 → 2026-10-05, end exclusive, UTC**. Put longer-history results under clearly labelled secondary sections, collapsed by default in the notebook. Both periods have already been used in previous strategy research; neither is an untouched holdout.

- Primary forecast origins: `2026-01-01 + 4k days`, strictly before 2026-10-05, at 00:00 naive UTC.
- Secondary history: 2023-03-01 → 2026-10-05, end exclusive. Extend the primary grid backwards in multiples of four days from 2026-01-01, retaining origins inside the secondary period, so all primary origins are an exact subset. Do not restart the grid on 2023-03-01 or duplicate overlapping observations in combined statistics.
- Feature warm-up may precede the reporting period. The forecast schedule is independent of the existing **two-day strategy rebalance cadence**, which stays unchanged in subsequent portfolio tests.
- Reuse `_artifacts-restored-2026-10-07/inputs/downloads.json`; verify the two data hashes and record the actual package/source fingerprints, universe membership, guard snapshot and recipes.
- Preserve restored legacy leader-share and capacity values when their independent observation clock is NULL. Unknown observation time is not evidence that a value was zero or unavailable. Retain permission and capacity provenance in the audit.
- Nor does an unknown clock prove that a value was observed at T. Flag `eligibility_time_unknown`, distinguish archived historical values from later backfills, and compare source-compatible eligibility with a historical-confidence sensitivity. Do not overwrite restored values or convert NULL clocks into zero capacity. Label historical availability as unverified where it cannot be established.
- Save derived frames, chart exports, manifests and review logs under an ignored `_artifacts*` directory. Keep reusable code, notebooks and written conclusions outside it. The repository already ignores `**/_artifacts*/`.

### What counts as a scoring method

Create an explicit registry before plotting. Start with all **74 recipes in experiment 06**, which experiment 07 reuses. Then add distinct implemented recipes from 04 and 05: original/near-v6 controls, requested/legacy/blended matrices, dense equal scoring, hard-clip alternatives, smooth saturation and ratio-floor/missingness variants.

Deduplicate by the **complete score-generating recipe**, including feature lookbacks, coefficients, component transforms, caps, denominator floors and missing-value policy. Retain familiar names as aliases. Do not deduplicate merely because scores happen to coincide in one sample. Conversely, position count, position sizing, dollar cap, refill, replacement hurdle and tie-breaking changes do not create a new numeric score and should not multiply the scatter plots. An activity filter changes the eligible cohort and needs a separate cohort sensitivity, rather than being mistaken for a new score formula.

Export the registry, method count `M`, coefficient tables, aliases and fingerprints. The main 06 grid alone implies **222 figures**, each with two target panels. The final number is `3 × M` after deduplicating all included experiments. List any excluded historical proposal and its reason; do not omit an implemented scoring method just because its portfolio performance was poor. Single raw features are supplementary diagnostics, not substitutes for the composite methods.

## Observation and target construction

### One row per forecast origin, vault and method

Compute scores once on the existing completed T−1 feature panel. Share labels and eligibility across methods instead of recomputing them per plot. Recommended fields:

`origin_at`, `feature_cutoff`, `vault_address`, `method_id`, `score`, `score_missing_reason`, `eligible_as_of_origin`, `eligibility_reason`, `eligibility_time_unknown`, `rank_percentile`, `origin_quarter`, `lookahead_days`, `nav_anchor_at`, `nav_target_at`, `anchor_observed_at`, `target_observed_at`, `anchor_nav`, `target_nav`, `future_return`, `future_log_return`, `future_cagr`, `future_sharpe`, `target_status`, and observation freshness/coverage fields.

Keep component availability and clipping flags in an accompanying component frame. Keep the primary label frame at `(origin, vault, lookahead)` granularity and score frame at `(origin, vault, method)` granularity; join for a chart on demand to limit memory.

### Exact target definitions

Use **per-share NAV/share price**, never TVL or total vault account value. Confirm this in the source mapping and check large price jumps against flow events. A deposit must not appear as investment profit.

Use the **last completed daily NAV at T−1** as the diagnostic anchor at forecast time T, matching the existing completed-feature convention. A lookahead of `h` days ends at `T−1+h` and uses the `h` daily returns labelled T through T+h−1. This mapping is provisional until the source candle convention is verified: an open-labelled T−1 candle closes at wall-clock T, whereas a point snapshot labelled T−1 was measured a day earlier. Record raw observation times, candle intervals and publication lag; the anchor must have been observable by T. Show worked examples for regular, irregular, missing-day and stale observations. Unknown publication history remains an explicit limitation, not an invented clock. Correct and document the mapping before producing results.

- Horizon return: `NAV[end] / NAV[anchor] − 1`.
- Realised CAGR: `(NAV[end] / NAV[anchor]) ** (365 / h) − 1`.
- Realised Sharpe: `sqrt(365) × mean(daily_returns) / sample_std(daily_returns)`, using exactly `h` returns, `ddof=1` and zero risk-free rate to match the existing daily feature convention.
- Require positive NAVs and complete supported daily observations for the target. A zero return variance makes Sharpe undefined, not zero or infinity. Store its reason. A complete flat NAV window can have zero CAGR while Sharpe is missing.
- Flag near-zero realised daily variance separately, initially using the existing `daily_risk_floor=0.0001` as a declared diagnostic boundary, plus counts of flat/carried marks. Show Sharpe results with and without flagged rows; do not silently floor the primary realised Sharpe denominator.
- Do not clip **realised** CAGR or Sharpe to the input-score caps. Seven-day annualisation and seven-observation Sharpe can be extreme and noisy: retain the requested panels and add horizon-return/log-return views and robust summaries. Never remove large genuine losses or gains just to improve the trend line.
- Diagnostic NAV outcomes are gross vault outcomes. A later executable backtest uses actual entry/exit NAV, recorded fees and timing; it must not claim that this anchor is an executed trade price.
- Add one- and two-day forward-start sensitivities with the same horizon length, using the original score and a delayed anchor. These test how much apparent predictability depends on a shared/stale endpoint or impossible entry timing. Input lookbacks of 360 days and target annualisation of 365 are intentionally different; record both.

**Right-censor strictly:** only include labels whose entire future window exists before the data end. Never shorten a 90-day label to fit the archive, forward-fill beyond the final observation, or use incomplete Sharpe windows. Produce exact last valid origin, date count, vault count and missing/censored fractions for each horizon. In this archive, most late-quarter forecasts cannot have long-horizon outcomes; the quarter colours describe the **forecast origin**, not the end of the outcome window. Include a common-origin comparison across horizons alongside the horizon-specific samples.

There are 70 scheduled 2026 origins. Conditional on a last daily label of 2026-10-04 and the provisional T−1 mapping, expected matured-origin counts are 68/62/47 for 7/30/90 days, with last origins 2026-09-26/09-02/07-04 respectively. Verify rather than hard-code these counts. Q4 has no matured outcomes; the 90-day Q3 population has only one origin. Label empty/partial quarters accordingly. **Do not report short-period 90-day bootstrap confidence intervals or p-values:** roughly two independent origin blocks cannot support meaningful precision. Show descriptive estimates and non-overlapping observations; longer-history inference is conditional on sufficient actual coverage.

### Eligible population and missing scores

Use the source inclusion criteria, return gate, blacklist, quarantine and permissions as of the forecast origin wherever historical state is available. Reconstruct feasible entry status separately from existing-holder status; incumbent redemption-only vaults are not new-entry opportunities.

Where a blacklist/quarantine/guard addition date is unknown, do not claim today's list was known historically. Keep those rows in an observed-universe diagnostic with an unknown-eligibility flag and show the current-source-filtered population separately. Executable controls retain their existing guard policy and disclose that limitation. Compare addresses against available earlier archives to quantify missing/deceased vaults and later list additions; if no historical universe exists, report the unmeasurable coverage explicitly.

Report three populations: all observed vaults for coverage; operationally eligible candidates for the primary relationship analysis; and ranked/selected/held cohorts for economic relevance. Do not restrict the main scatter to profitable survivors or previously funded vaults. Record which current guard/universe membership assumptions cannot be reconstructed historically and label the resulting survivorship limitation.

Missing composite scores remain missing under the original v6/v11 policy. **A missing score is not a valid numerical zero.** Show their forward outcomes as a separate cohort and quantify their potential funding. Zero-imputed methods retain explicit imputation flags. Compare methods both on their own valid populations and on a common valid population, so a change in coverage cannot masquerade as improved forecasting.

Audit flat/carried NAV marks, stale observations, young vaults, delistings and disappearing vaults. Report attrition by score bin and method. A missing future endpoint is not evidence of a harmless exit; investigate the last usable redemption valuation and show an explicitly labelled adverse sensitivity where recovery is unknown. Future observation quality may be used to describe target reliability, but not to decide whether the strategy could enter at T.

Distinguish archive-end administrative censoring from informative per-vault disappearance. For missing endpoints after disappearance, supplement observed-case IC with worst-rank and median-rank imputations within the origin; these are scenarios, not guaranteed mathematical bounds. Investigate terminal flat runs as possible closure/stale-data events rather than automatically accepting them as harmless zero-return outcomes.

## Notebook presentation

### Required scatter figure for every method and lookahead

For every `(method, h)` produce **one figure with two side-by-side scatter panels**: realised CAGR and realised Sharpe. This satisfies one chart per combination while retaining both requested targets.

- X: the actual numeric composite score. Y: the corresponding realised target, with CAGR labelled in percent.
- Colour dots by origin quarter; use the same quarter palette throughout. Use transparency and hover details for vault, date, target window, score and missing/quality flags.
- Add a labelled linear trend line. Also show a binned mean/median or robust smoother to expose nonlinearity; do not imply the smoother is a calibrated live forecast.
- Keep the requested CAGR-versus-score plot and its labelled OLS trend, but make annualised log return/log-return trend and robust fitting the primary economic interpretation. Add a mapped log-space trend and median bins when extreme annualised targets dominate OLS. Label means of horizon CAGRs as descriptive transformed outcomes, never expected annual portfolio returns.
- Show paired row count, distinct origins/vaults, pooled Spearman/Pearson correlations and the dependence-aware uncertainty reference. Plot NaNs only in separate missing-cohort summaries, not at X=0.
- Titles always mention **reporting period, lookahead and method**. Descriptions explain that different horizons have different matured-origin coverage. An empty or constant-score panel must say why a trend/correlation cannot be estimated.
- Preserve all finite points. If extreme targets compress the useful region, add an explicitly labelled zoom or signed-log companion without silently truncating the primary analysis. Distinguish any deterministic display-only subsampling from the complete statistical sample.
- Use interactive scatter figures for the few focal methods, and static PNG/SVG figures for the full appendix. Export detailed point data separately. Hundreds of full Plotly hover payloads must not make the saved notebook or static viewer unusable; record image size and estimated notebook size before the full render.

Use the consistent layout **subheading → short description → chart/table** for every element, including Markdown tables. Keep a front section for the frozen controls and focal four-input method, followed by a complete, indexed appendix grouped by scoring family. Collapsible sections may shorten navigation, but no required combination disappears. Table styling should highlight relationship strength, uncertainty and coverage, rather than use portfolio CAGR colours for unrelated statistics.

### Additional core visualisations

Each element should answer a specific question rather than add another decorative parameter map.

1. **Method × lookahead IC heatmaps**, one each for CAGR and Sharpe: mean same-date rank correlation, uncertainty and date coverage. Distinguish absent evidence from an IC of zero.
2. **Calibration curves**: absolute score bins and contemporaneous rank buckets against horizon return, CAGR, Sharpe and probability of loss; show counts, medians and uncertainty. Use fixed score bins; do not split tied scores arbitrarily to manufacture smooth deciles.
3. **Quarter stability heatmap**: per-quarter IC and slopes, with matured-origin counts. Mark unavailable quarters instead of comparing partial Q3 or absent Q4 as complete periods.
4. **Tail-risk map**: score bins versus loss frequency, downside quantiles and large-loss incidence. A score may predict mean returns while failing to identify catastrophic entries.
5. **Rank and clipping diagnostics**: score distribution, saturated components, ties and conditional outcomes inside plateaus. Compare raw-feature ordering within tied scores, without changing the original score.
6. **Marginal admission chart**: outcomes for ranks 1–6, 7, 8 and 9–10 within each date, plus cash and equal-capital controls. This investigates the actual breadth question from experiment 07.

## Measuring relationship strength

Treat pooled scatter correlations as descriptive. They mix market regimes, persistent vault quality and changing eligible populations.

Primary statistic: compute **same-date cross-sectional Spearman IC** between score and realised target, then summarise dates with equal date weight. Require at least ten paired vaults, at least five distinct score ranks and a nonconstant target for the primary inference; retain thinner/tied dates as labelled descriptive diagnostics. Report mean/median IC, positive-date fraction, date/vault counts, score ties and confidence intervals where support permits. Supplement with pooled Pearson/Spearman and equal-vault weighting, not replace the date-level statistic with them. Keep pooled Pearson on raw CAGR descriptive; use log-return Pearson and robust slopes for economic interpretation.

Four-day forecast origins create heavily overlapping 7/30/90-day labels. Reuse complete date baskets in a moving-block bootstrap with blocks at least as long as the evaluated horizon; inspect IC and score-rank persistence when choosing longer blocks. Cross-check with HAC uncertainty on the IC time series and non-overlapping-origin sensitivities. Bootstrap confidence bands must not treat every vault/date dot as independent. For the short 90-day sample, omit confidence bands/p-values and show the small number of independent windows. Add leave-one-vault-out and leave-one-quarter-out checks to reveal domination by one vault or episode. Date-controlled regressions and a separate within-vault sensitivity can help separate ranking from persistent vault identity.

Account for searching many highly correlated scoring recipes and thresholds. Specify a dependence-preserving null explicitly: jointly circular-shift the outcome panel relative to scores by offsets exceeding the horizon, or consistently relabel entire vault paths within sufficiently long blocks. Preserve serial and cross-sectional dependence; audit changing membership and regime boundaries. Do not independently reshuffle each origin. Recompute all methods on the same null draws and common valid population for a family-level maximum-statistic comparison. Report effect sizes, stability and economically relevant spreads alongside any supported p-values.

For a fixed horizon, CAGR, return and log return have identical Spearman ranks: they are one finding, not three independent successes. Use the three frozen focal methods and 30-day return-rank IC as the primary analysis; other recipes/horizons/cohorts are exploratory. Because these methods were selected on known history, even the primary analysis is not new confirmatory evidence. Estimate effective sample size and minimum detectable IC before expensive inference. Add realised-volatility IC to check whether Sharpe predictability is mainly persistent low volatility rather than higher future mean return.

## Learning and validating an exclusion threshold

### Chronological calibration

Use expanding/rolling chronological folds with **training labels fully matured before the validation origin**. Purge training rows whose lookahead overlaps validation; enforce this separately for each horizon. Fit calibration, bins selected from data, thresholds and any regime interactions on training data only. A long feature lookback requires warm-up history, not an arbitrary two-year label embargo.

Compare three small calibration baselines: constant historical expectation, linear score mapping, and monotonic isotonic mapping. Fit the return models in log-return space; evaluate log-return error and map their predictions into horizon-return/CAGR units, distinguishing transformed point predictions from expected CAGR. Calibrate Sharpe separately with robust error summaries and low-variance sensitivity. Use spline/non-monotonic fits only as a diagnostic unless they improve chronological validation with adequate support. Do not treat an isotonic monotonic fit as evidence that the empirical relationship is monotonic.

Use pre-2026 matured data to initialise folds where available; evaluate 2026 sequentially and provide full-history rolling results secondarily. Because existing score recipes were selected after inspecting these same dates, call this **conditional chronological validation of frozen recipes**, not an untouched strategy holdout. Strong confirmation needs subsequently collected data with the recipe and threshold frozen.

### Threshold candidates and decision rule

Begin with no threshold, a coarse absolute-score grid from 0 to 1 in 0.1 increments, and a small set of within-date percentile floors. Refine only if a broad stable region exists; do not search every observed score. Absolute thresholds are method-specific because clips and missingness change the score scale. Retention counts, loss rates, mean horizon returns and uncertainty must accompany each threshold.

**Freeze the selection algorithm before anyone inspects full-period scatter/threshold results.** Record its source hash and fold definitions; do not let an agent choose a threshold after viewing validation outcomes. Initial primary horizon: 30 days. Use pre-2026 holding-duration data to assess whether this is economically relevant; any change to the primary horizon must be recorded before 2026 outputs are examined. Seven-day timing and 90-day persistence are exploratory. The latter's 2026 threshold calibration relies on pre-2026 support, not the insufficient matured 2026 history alone.

Initial executable rule: recalibrate monthly at the **first scheduled four-day origin on or after the first calendar day of the month**, using expanding historical training labels whose endpoint was observable strictly before that origin. Activate the saved floor at the first actual strategy decision at or after calibration, then hold it fixed until the next calibration. Among coarse absolute floors, select the **lowest** floor whose below-floor cohort has a negative upper 95% dependence-aware confidence bound for mean net horizon log return versus cash and meets the support rules; otherwise apply no floor. Account for searching the eleven floors within that training comparison. Show gross and recorded-fee-adjusted comparisons; where investor costs cannot be established, a gross-only floor remains exploratory. The second policy is a fixed 75th-percentile entry floor within the contemporaneous eligible, scored universe; it is not chosen from validation results. Treat unknown scores separately. Record how often either rule actually rejects marginal proposed entries rather than irrelevant bottom-ranked candidates.

Predeclare an initial support floor of at least ten distinct vaults, twenty matured forecast origins and three independent horizon blocks in a training comparison. These are screening minima, not sufficient proof; mark thin 90-day evidence inconclusive. Evaluate whether below-threshold candidates underperform cash or merely underperform higher-scoring vaults. Relative underperformance does not justify leaving capital idle if the excluded vaults remain profitable and no better feasible substitute exists.

Take at most three fixed scoring methods into the first executable threshold tests: original v11, two-input Blend 46d and the focal four-input method. Choose at most two threshold policies per method from training evidence; keep a no-cutoff control. If no stable useful floor exists, retain that result rather than manufacture one. Wider exploratory method comparisons stay labelled exploratory.

Start with an **entry-only floor**: below-threshold new deposits are forbidden; retained holdings, pins, exits and existing hysteresis follow the original rules. Initially, the floor does not block increases to already held eligible positions. Do not forcibly fill N positions. Keep missing-score entry behaviour explicit and compare retaining the source policy with a separately labelled exclusion of unscored entrants. A forced-exit floor is a later independent treatment, requiring turnover/fee analysis and exit hysteresis.

Separate two allocation treatments rather than conflating them: **slot to cash** computes the no-floor proposed targets, vetoes the failing new-entry dollars and retains them as cash; **renormalise within caps** excludes failing entrants before source inverse-variance sizing and preserves normal source redistribution. They are different strategies. Implement an audited order-of-operations contract and compare both to the identical no-floor control. The first treatment measures the value of avoiding those proposed entries; the second measures the deployable admission policy under existing sizing.

### Executable profitability tests

Run chronological, threshold-frozen policies at **6 and 7 positions** first; 8 and 10 are secondary breadth diagnostics. Preserve the source two-day cadence, 90-day inverse-variance sizing, 33% concentration/pool limits, 98% allocation budget, permission/capacity checks, source fee handling and rank hysteresis. Admission floors are checked at actual two-day decisions; the four-day diagnostic cadence does not become a trading schedule. Apply a threshold trained at a four-day origin only after its training labels have matured and freeze it until the next predeclared recalibration date.

Report net portfolio CAGR, Sharpe, maximum drawdown, cash weight, occupancy, turnover, fees, rejected entry dollars, foregone returns and vault-level PnL concentration. Primary economic objective: improved net CAGR with no deterioration in Sharpe or drawdown relative to the matching no-floor control; also report each metric separately without reselecting thresholds on validation metrics. Compare date-matched randomly thinned admission controls drawn from the same proposed entrants with matched rejected counts/dollars; fix seeds and report the policy's percentile in their distribution. Add a no-floor return stream scaled to the threshold policy's exposure path as an **ex-post attribution sensitivity**, not a causal tradable control. Compare against simply reducing the no-floor portfolio from seven to six positions. Retain zero-yield cash matching existing accounting, with non-zero cash yield separately labelled. Use recorded vault fees, avoid double-counting fees already internalised in share price, and do not invent slippage at NAV.

Keep capacity checks, concentration limits and fee handling unchanged within each declared allocation treatment. Do not introduce the separate residual-dollar refill experiment at the same time. Profit attribution that removes a vault from a fixed ledger is a sensitivity, not an executable threshold replay.

## Further analyses and creative extensions

Prioritise extensions that explain why a method works or fails:

- **Incremental information:** compare the four-input method with its two-input core on the same rows. Test whether the extra cells predict future outcomes after controlling for the core score. Distinguish genuinely new ranking information from changed clipping or loss of younger vaults.
- **IC decay and forward-start windows:** add a compact exploratory curve over 1/2/4/7/14/30/60/90 days and a 30→60-day forward-start window. This identifies whether information is brief, persistent or merely endpoint timing. It does not replace the three required horizons.
- **Freshness placebo:** compare current scores with scores lagged 30/60 days for the same future outcomes. This tests the value of fresh information and helps diagnose score persistence.
- **Actual-entry event study:** join source 06/07 proposed/executed entries to their scores and subsequent share-price outcomes. Hysteresis means candidate rank 7 is not necessarily the seventh marginal entry; analyse the actual affected entrants too.
- **Risk forecasts rather than a mean-only gate:** calibrate probability of a negative horizon return and a predeclared material-loss event, with reliability curves, Brier score and chronological validation. Assess whether a downside-risk floor is more useful than a single raw-score floor.
- **Reference-market residuals:** compare raw outcomes with BTC/ETH-adjusted returns using betas estimated before T. Use `tradingstrategy.binance.price.fetch_binance_price()` and its cache, not ad hoc reference-price downloads. This tests whether scores identify vault skill or mostly market exposure.
- **Regime-conditioned relationships:** split by as-of-T market volatility, vault age and observation activity. Prefer a few predeclared groups; do not create a complex regime tree from the same short sample.
- **Ranking versus absolute confidence:** compare absolute scores, same-date percentiles and calibrated expected excess returns over cash. A useful ranking signal can have no reliable absolute cutoff.
- **Schedule sensitivity:** repeat diagnostic calculations with the other three four-day origin offsets and with thinned non-overlapping labels. A conclusion that depends on one anchor date is fragile.
- **Threshold frontier:** plot net return, downside risk, average cash and admitted-vault count together across coarse thresholds. Prefer a stable region over a single fitted optimum.
- **Surprise/event audit:** investigate the largest positive and negative prediction residuals, including previously identified loss episodes. Distinguish NAV/data artefacts from real strategy failures without deleting inconvenient observations.

Keep speculative new forecasting models, new coefficient optimisation and selector rewrites out of the first stage. The experiment should first tell us whether the signals we already have contain usable forward information.

## Work breakdown for subagents

No subagents or notebook executions are started by writing this plan. The implementation can use parallel agents after a shared, reviewed data contract is ready.

### Dependency order and ownership

Each worker owns separate files and outputs. Only the coordinator writes the final notebook and conclusions.

| Phase | Owner | Work and hand-off |
| --- | --- | --- |
| A | Coordinator + data agent + independent audit agent | Freeze registry, threshold-selection code and fingerprints; build causal score/label/eligibility frames and shared statistics/plotting library. Audit agent independently recomputes approximately 50 stratified random labels from raw rows using the written contract, including irregular/flat/missing cases. Check source-score equality and coverage before releasing immutable frames. |
| B | Three horizon agents | One worker each for 7, 30 and 90 days. Parameterise the same reviewed library, rather than write three implementations. Produce every method's two-panel scatter, IC/bin/quarter summaries and a figure manifest. Own separate `08-h7`, `08-h30`, `08-h90` shards. Do not regenerate the universe or mutate shared caches. |
| C | Statistical agent + execution agent, after B | Statistical agent applies the already frozen chronological calibration/threshold rule and runs joint-across-method uncertainty draws. Execution agent prepares the two declared allocation treatments; dependent threshold replays start only after fold-specific training choices are saved. Coordinator reviews both. |
| D | Coordinator | Assemble the complete 08 notebook, check coverage against `3 × M`, inspect charts using the static preview server, write findings and document whether a stable threshold exists. |

Use **at most three agents running notebooks concurrently**, with no coordinator kernel during phase B. Prefer fewer if measured memory pressure demands it; the runner's per-kernel cap is not a promise that three kernels fit in host RAM. Compute the large feature panel once, load only the required horizon/columns, and persist reusable columnar frames. Limit backtest process workers independently so nested multiprocessing does not multiply concurrency.

Use `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...` in the foreground. Show progress and estimated remaining time for long cells, but remove repetitive saved stdout/progress output from the final notebook. Save after every cell; keep shard manifests and timings so a failed worker resumes only its missing work. Never kill kernels broadly. Each agent must identify its own parent/kernel process before stopping anything.

Suggested deliverables: `08-score-forecast-thresholds.ipynb`, reusable `score_forecast_analysis.py`, a compact `08-score-forecast-findings.md`, and ignored `08/` artefacts containing registry, frames, fold definitions, figure manifests and diagnostic summaries. Intermediate shard notebooks may live under ignored artefacts; the assembled notebook must contain all required saved charts and clear navigation.

The shared library owns label construction, tie handling, support rules, bins, date-level IC, uncertainty and rendering. Use a common summary schema such as `(method_id, horizon, population, statistic, value, lower, upper, origin_count, vault_count, support_flag)`. Vectorise joint null draws centrally rather than recomputing them independently per horizon. Horizon workers can inspect charts but cannot override the frozen threshold rule after seeing outcomes.

## Completion and review checklist

- Every distinct registered scoring method has all three lookahead figures, or an explicit missing-support panel; all chart titles include period and horizon.
- Four-day origins, T−1 inputs, exact future windows and censoring are independently checked with worked examples. Source v11/control scores match the existing implementation at sampled origins, including missing and saturated cases.
- Default presentation is 2026 everywhere, including Markdown tables. Each element has a short subheading and description. Full history is clearly separated.
- Flat windows, unknown scores, missing future data, score ties and current-universe limitations are reported rather than silently discarded.
- Relationship estimates include per-date IC, dependence-aware uncertainty, cohort coverage and outlier/quarter/vault sensitivities. Calibration and thresholds use only matured training labels.
- Threshold findings distinguish a ranking improvement from outperforming cash and from an actual net portfolio improvement. Negative/inconclusive outcomes are acceptable conclusions.
- Every chart is visually inspected through the repository static notebook preview server: axes, target units, point visibility, quarter legends, trend lines, sparse panels and clipping are checked. Inspect all appendix charts, not only the leading methods.
- Reusable code and written findings are reviewable; generated external artefacts remain ignored. No deployment is implied by a favourable backtest.

## Claude review

Reviewed on **2026-10-08 using Claude CLI 2.1.281 with `--model claude-opus-5-5 --effort high`**. The successful JSON response confirms `canonicalModel: claude-opus-5-5`; no model substitution was made. Claude reviewed the plan text only, with tools disabled, and was explicitly asked for creative analyses. Its verdict was **approve with required revisions**. This file incorporates the review; the revised text has not received a second Claude review.

### Revisions accepted from the review

These are design changes, not findings from a new experiment.

| Review concern | Change made |
| --- | --- |
| Observable timestamps and per-share NAV | Added raw observation/publication fields, candle-convention checks, flow audit and delayed-anchor sensitivities |
| Sparse 90-day evidence and misaligned history | Aligned origin grids, added provisional coverage counts, suppressed short-period 90-day significance claims |
| Informative disappearance and hindsight exclusions | Separated censoring/attrition, added rank-imputation scenarios and historical-eligibility/universe audits |
| Overlap and many scoring methods | Specified serial-dependence-preserving joint null draws, persistence checks and common-population comparisons |
| Threshold choice after viewing outcomes | Fixed monthly training cadence, primary horizon, selection objective and deterministic selection rule before rendering |
| Cash and source redistribution were conflated | Defined slot-to-cash and renormalised treatments separately, with random, exposure and breadth controls |
| Noisy seven-day annualised targets | Added log-space interpretation, robust fits, low-variance flags and volatility IC |
| Repeated worker implementations and oversized output | Required a shared library, independent raw-label audit, static appendix and limited interactive figures |
| Creative follow-ups | Prioritised power checks, IC decay, lagged-score placebos and actual-entry event studies |

Do not interpret Claude's provisional calendar counts as verified source-data coverage, its expectation of ranking evidence as a result, or its fee examples as proof of unrecorded charges. Keep the requested CAGR/Sharpe plots and OLS trend, while clearly labelling their limitations. More involved simulations of no-skill volatility persistence and backtest-overfitting estimates are deferred until basic coverage and support are established.

Raw response and metadata: `_artifacts-restored-2026-10-07/08-plan-review/claude-opus-5-5-review.json` (ignored generated artefact). This plan is the reviewable written record; no implementation, notebook execution or threshold result is implied.
