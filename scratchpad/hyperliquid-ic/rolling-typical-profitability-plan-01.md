# Rolling typical profitability: incremental-information experiment

## Objective and scope

Determine whether the typical magnitude of rolling returns helps identify future profitable, steady vaults beyond information already supplied by ordinary return, profitable-window frequency, Sharpe and volatility. Measure drawdown separately and ask whether it adds information conditional on profitability and risk.

The portfolio objective remains high Sharpe with reasonable CAGR around 20%, not beating the incumbent on return. This first experiment is a vault-level diagnostic, not a portfolio optimiser. Do not annualise a short forward return into a claim that a strategy meets the portfolio objective.

Status: design only; no new notebooks or backtests have run. Reviewed with Grok CLI using `grok-4.6` and `xhigh`; actionable feedback incorporated. See [review](grok-46-rolling-typical-profitability-review-01.md) and [disposition](grok-46-rolling-typical-profitability-disposition-01.md). The revised text has not received a second external review. Existing experiments and their historical results are inputs, not independent validation.

Implement one notebook, provisionally `30-research-rolling-typical-profitability.ipynb` (check numbering first), with a small helper module only if necessary. No new dependencies, generic framework, model search or automatic follow-on portfolios.

## Prior evidence and what is actually new

Paths in this table are relative to this folder. These results have different universes, accounting and dates: compare arms within their source experiment, never assemble their returns into one leaderboard.

| Earlier experiment | Relevant method and saved finding | Constraint on this experiment |
| --- | --- | --- |
| [Lower-vol NB09](../hyperliquid-lower-vol/09-backtest-consistency-selection.ipynb) | Positive trailing 30-day return frequency over 180 days blended with CAGR. CAGR 24.3%, cycle Sharpe 1.49, max DD -6.44%, versus control 37.9%, 2.16, -4.45%. | Rolling profitable-window frequency is an existing comparator, not a discovery. Its portfolio failure was not merely sacrificing return. |
| [Lower-vol NB28](../hyperliquid-lower-vol/28-research-stability-signal-screen.ipynb) | Ulcer and positive-window share predicted subsequent volatility/downside. Signed ICs roughly 0.642/0.611 and 0.427/0.414 respectively. Later audit corrected overly restrictive rejection criteria; seven signals passed the revised risk criterion. | Do not rediscover risk persistence or treat an old failed acceptance gate as absence of information. |
| [Lower-vol NB32](../hyperliquid-lower-vol/32-backtest-return-floor-stability-rank.ipynb) | Return floor then stability ranking: 26/30 main-grid configurations negative, best CAGR 8.8%. | No new return-floor-plus-calmness portfolio grid. |
| [Lower-vol NB38/39](../hyperliquid-lower-vol/39-research-trimmed-screen-full-history.ipynb) | Trimming exceptional gains did not establish improvement over raw scores; full-history trailing risk-adjusted scores had positive forward-Sharpe associations, with limited independent time blocks. | No best-day-removal search; Sharpe belongs among comparators. Insufficient precision is inconclusive, not a failure of the feature. |
| [IC NB11/12](11-research-profitability-repeatability.ipynb) | Positive returns in both halves, positive-week share, event concentration and downside screens. Full-panel P2 full-period CAGR about 4.7%; no robust target portfolio emerged. | Repeatability and young-compatible access have already been attempted. |
| [IC NB19/20](20-research-stability-screen-portfolios.ipynb) | Median week/worst week/drawdown described StratWise; hard screens inspired by examples improved none of 12 full-period Sharpe comparisons in the saved experiment. | Example separation is not predictive evidence; no name-fitted thresholds or new hard exclusions. |
| [IC NB23/24](monthly-calibration-summary-01.md) | 0/48 monthly configurations qualified. Shortlisted selected vaults all scored 1, with identical curves and inactive negative-month penalties. | Include all return outcomes in quantiles; avoid clipping the entire signal to a common perfect score. |
| [Vault-of-vaults NB90](../vault-of-vaults/90-hyperliquid-underwater-geometry.ipynb) | Time underwater, drawdown area and new-high frequency over 30/60/90 days underperformed controls. | Drawdown depth/path is established territory; test incremental information, not novelty. |
| [Lower-vol NB07](../hyperliquid-lower-vol/07-backtest-drawdown-sizing.ipynb) | Inverse ulcer/downside sizing worsened portfolio ulcer from 1.80% to 2.10%/2.17%. | Do not equate low measured downside with permission to allocate heavily. |
| [Waterfall NB39/78](../hyperliquid-waterfall-rc/78-research-curve-shape-and-ensemble-scoring.ipynb) | Ulcer had exploratory forward-return IC; some eventual large losers had few losing days and little downside before entry. | Apparently flawless histories are not evidence of safety. Old IC t-statistics with overlapping labels are not independent confirmation. |
| [IC NB25–29](rolling-profit-risk-track-summary-01.md) | Raw rolling growth selection performed badly; sizing did not rescue it. Drawdown haircuts did not reach the objective. Some robustness arms remain unrun. | Reuse the corrected snapshot/control definitions. This study neither completes those missing arms nor establishes a production-equivalent backtest. |

The narrow new question: does the median or lower quartile of ALL recent rolling holding-period returns distinguish future profitable steadiness among vaults with similar ordinary return and risk? Keeping drawdown as an explanatory diagnostic is deliberate. No new allocation formula is presumed.

## Frozen data and decision universe

1. Reuse the NB25 input manifest, raw observed price history and universe membership. Record hashes, snapshot endpoint, source versions and exact joins. Do not silently refresh the dataset.
2. Daily decisions use information strictly before UTC midnight T. Dates cover the available history through the frozen endpoint, including the full-history and hyper-ai date slices used in NB25. Export exact dates; horizon labels naturally shorten the scored tail.
3. Primary opportunity set: historical TVL at least $7,500, the NB25 young-compatible -16% recent-return gate, and its point-in-time operational checks. Blacklists off. Distinguish this research opportunity set from actual engine-funded positions. Do not introduce a six-vault minimum or long-history eligibility rule.
4. Young and weekly-observed vaults remain in the universe. Feature unavailability is a measurement limitation, not rejection. Keep rows before any forward-label mask, and report their coverage by age and observation cadence. Do not pretend unknown returns are zero.
5. Use the frozen retrospectively selected universe transparently: there is no clean survivorship-free claim. StratWise and Systemic L/S Grids (verify canonical names/addresses from metadata) are illustrative cases only.

## Features and exact timing

Primary rolling-return horizon h=7 calendar days and history span W=30 calendar days. Three declared sensitivity pairs: (14,30), (7,60), (14,60). Run all four feature settings; do not select the best full-history setting and call it primary.

T is an exclusive UTC-midnight boundary: all marks on calendar day T-1 are usable, but marks at or after T are forbidden. Historical endpoints s are UTC calendar-day ends in (T-W, T), including the final instant before T. At each historical endpoint s<T, use the most recent observed price at or before s and at or before s-h; both must be no more than seven days old relative to their respective requested boundaries. Keep actual mark timestamps. Require distinct marks and positive actual elapsed time. Never interpolate from a future observation.

Store raw nominal-h simple return P_end/P_start-1 for explanation. The value entering M and Q is log(P_end/P_start) / actual_elapsed_days, an unannualised daily log growth rate. This normalises differing realised interval lengths; it does not claim an unobserved daily path or remove cadence dependence. Store actual elapsed days; do not treat repeated carried endpoint pairs as fresh evidence. Within each trailing W-day formation window, retain each unique (start_mark,end_mark) pair once, using the latest nominal endpoint in the window as its representative. These are sparse-compatible nominal-h returns, not claims of exact h-day observed returns. Report actual-span distributions and a dense-only sensitivity so weekly and daily evidence are not silently conflated. The formation window contains the ENDPOINTS of rolling outcomes: their start marks may predate T-W by up to h+7 days. Report this maximum historical footprint explicitly and use it consistently across matched comparators. Do not annualise individual intervals into exaggerated short-horizon gains.

A young vault with less than h days has no nominal-h feature yet, but remains in the opportunity set. Report its available-history growth separately as a provisional descriptor; do not pass it off as the same median feature. If only one rolling outcome exists, calculate its median/quantile but identify the one-outcome cohort explicitly. No minimum outcome count is used for vault admission.

| Feature | Definition | Role |
| --- | --- | --- |
| Typical return M | Median of daily log growth rates of all valid unique nominal-h intervals ending in trailing W | Primary candidate |
| Lower-quartile return Q | 25th percentile, standard linear interpolation, of those same daily log growth rates | Second candidate, no separate threshold sweep |
| Positive-window share P | Fraction of those returns strictly positive; zero remains in denominator | Matched-window existing-idea comparator |
| Ordinary growth G | Available-history log growth per elapsed day inside W, using observed endpoints | Return comparator, no clipped score |
| Volatility V | Reuse NB25 interval-risk definition over available W; retain missing risk | Risk comparator |
| Sharpe-like ratio S | NB25-compatible annualised available growth / interval volatility; missing when denominator zero or unavailable | Existing risk-adjusted comparator; label estimator precisely |
| Mean drawdown A | Time-weighted mean absolute drawdown below the running high within available W | Separate path diagnostic |
| Current drawdown D | Decline from that same formation-window running high at the latest mark | Separate path diagnostic |
| Evidence descriptors | Observed age, actual span, unique return-pair count, last-mark age, cadence | Coverage/cohort diagnostics, not alpha factors |

For A, integrate the last-observation-carried-forward drawdown path over elapsed time between observations up to the exclusive boundary T; use no mark before inception and initialise the running high at the first valid formation-window mark. Carry at the final boundary only within the same seven-day tolerance. Divide by actual covered time. Store current D separately: recovered setbacks remain in A but not D. No new ulcer/underwater-feature grid.

Check M/Q ties and rank agreement with G, P, S and -V. Overlapping windows can repeat the effect of a single lucky gain despite deduplicating mark pairs. Show one synthetic jump-and-flat example alongside smooth-profit and loss-and-recovery paths to make that limitation explicit; do not delete best events in the main feature. Report exact M=Q frequency and unique-outcome counts without assuming equality for two or three outcomes: linear-interpolated quantiles can differ. As an explanatory diagnostic only, identify the largest positive observed log-return event (earliest timestamp breaks ties) and the fraction of unique rolling intervals containing both its bounding marks; report overlapping-but-not-containing intervals separately. Missing positive events remain missing. This containment statistic never enters ranking or tuning.

## Forward outcomes

Use fixed H=30 days primary and H=60 days sensitivity. Labels start at the same latest valid mark strictly before T that ends the formation path (not an independently chosen entry mark) and end at the last observed mark at or before T+H, with at most seven days of endpoint carry. Require exit timestamp strictly after T and positive elapsed holding time; observations after T alone extend the entry path. Record actual entry/exit timestamps and elapsed days, preserve missing outcomes and deduplicate realised intervals in evidence counts. No retrospective coverage condition changes the original ranks or universe.

Primary outcomes, reported jointly rather than merged into an optimised utility:

- Forward holding-period return: endpoint simple return, unannualised.
- Forward path maximum drawdown over the holding interval, including the entry mark.

Secondary outcomes: negative-endpoint-return frequency, forward interval volatility and forward Sharpe-like ratio using the same documented estimator as historical comparators. Do not gate admission on future coverage or impute missing future labels. Report label coverage separately for top-ranked and remaining candidates.

Do not use future median 7-day return as the only success target: that would reward resemblance to the feature rather than establishing profitable investment outcomes. No CAGR conclusion from a vault-level ranking panel.

## Analysis and controls

1. **Coverage and discrimination:** counts of dates, vaults, rows, distinct feature/outcome intervals, history/cadence cohorts, missingness, tied-score share and the effect of deduplication. Show expanding-history examples, including ages below seven days without an invented median.
2. **Marginal comparison:** per-date Spearman for M, Q and all comparators against each outcome. Report top-quintile forward returns and risk versus the remaining opportunity set. Compute average percentile ranks for ties and fractional membership for a tied quintile boundary rather than address tie-breaking. Form ranks and membership weights on the feature-available opportunity set BEFORE looking at labels. When scoring, omit missing labels without re-ranking or changing original membership and report both group coverages. A constant score produces an uninformative contrast, not evidence of selection. A statistic needing variation or enough ranks may be missing; it does not remove vaults from the underlying universe.
3. **Conditional comparison:** use same-date average percentile ranks. Residualise each candidate rank (M or Q) against an intercept, G, V and P ranks using that date's feature-only cross-section; correlate the residual with each forward outcome. P is required to distinguish return magnitude from the already-tested positive-window frequency. A second fixed view residualises M/Q against S and P ranks, explicitly checking the existing risk-adjusted comparator. For drawdown, first residualise negative A/negative D against G, V and P; then add M in a separate view to ask whether path adds information beyond typical profitability. Use only contemporaneous features, never outcomes in these regressions. With fewer than 10 complete candidates, rank-deficient design or zero residual variance, report the conditional estimate as unavailable. Include ordinary comparator results on the identical feature-complete subset and excluded-young coverage. G,V,S need not be exactly linearly collinear: separate comparator sets limit redundancy and keep interpretation simple, rather than asserting an algebraic impossibility. These are descriptive checks of linear rank dependence, not causal effects, fitted forecasts or proof of independence from every baseline simultaneously.
4. **Robustness without a search:** report the four (h,W) pairs and both horizons; by historical period and observed-age cohort (<30, 30–89, >=90 days); and separately on dates/vaults with daily versus sparse observations. Age is descriptive, not an exclusion. Add a non-overlapping decision-date view for each H, starting at the first scored date, to show whether a daily result survives reduced overlap. Do not tune its offset.
5. **Examples and failures:** plot past-only feature paths and subsequent returns for the two reference vaults and historically documented losing counterparts. Mark each hypothetical decision boundary. Select examples from prior records, not whichever names favour the new metric. Compare within similar historical growth/risk and explain any missing measurements.

Predeclare paired M-minus-G, M-minus-P, M-minus-S, M-minus-negative-V contrasts, and the same contrasts for Q: per-date Spearman, top-quintile mean forward return and mean drawdown magnitude. Recompute each pair's ranks and fractional memberships on the SAME feature-complete subset before labels are masked; retain the main opportunity-set tables separately. Bootstrap paired date differences, not separately generated confidence intervals. No comparator is selected after seeing outcomes.

Daily observations and rolling labels overlap. Summarise dates with equal weight. Use descriptive paired 60-calendar-day block-bootstrap intervals (90-day sensitivity) for new-minus-comparator statistics, keeping all vault rows on a sampled date together. Report block counts and individual-vault contribution sensitivity; short cohort intervals are explicitly unreliable. No claim of controlled family-wise significance, independent holdout or causal skill. Existing dates have been repeatedly researched.

## Interpretation and stopping

The notebook must distinguish four outcomes:

- **Redundant:** candidates closely reproduce existing orderings and show little additional forward separation.
- **Risk-only:** lower future volatility/drawdown without useful future profitability. This can inform sizing research, but is not successful steady-profit selection.
- **Potential incremental lead:** useful joint forward-return/risk separation, directionally consistent across neighbouring settings and periods, including informative young-history coverage. Report trade-offs and uncertainty rather than forcing all cells to pass.
- **Inconclusive:** insufficient coverage or precision, conflicting periods, or excessive ties. Do not label it disproved.

Do not require beating the incumbent's CAGR or statistically proving a 20% portfolio CAGR in this diagnostic. Do not require every horizon/cohort to pass an impossible conjunction. Conversely, attractive StratWise charts alone do not justify advancement.

No portfolio reruns in this notebook. If evidence warrants a follow-up, freeze one primary candidate and propose a separate matched ranking-only backtest against the corrected B00 control; keep allocation, fees, execution and universe fixed. Any later sizing trial is a separate intervention. A0b remains a separately labelled independent simulator, not an interchangeable engine control. A proposed follow-up must state its new information beyond NB09/NB20/NB32 and the limitations of reused dates.

## Deliverables and verification

Outputs under `_artifacts-rolling-typical-profitability/`: input/specification manifest; daily feature/label panel; coverage and tie tables; marginal and conditional results; robustness tables; example plots; and a short conclusion identifying redundancy, risk-only evidence, incremental evidence or uncertainty.

Verify with small deterministic examples: constant price; steady compounding; single jump then flat; positive path with temporary losses; young history; weekly marks; duplicate endpoint pairs; zero volatility; and strict T-1 timing. Alter observations after a decision and assert its features do not change. Adding an unlabelled future tail must not change historical ranks. Check fractional quintile weights sum to the requested fraction and existing comparators share the same evaluation rows.

Run with the repository notebook runner and display tables rather than print-heavy output. Review formulas and results for correctness, but do not conflate a completed code review with economic validation. This file authorises design for one experiment; implementation is a subsequent task.
