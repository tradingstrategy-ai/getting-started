# Rewrite plan: use the available data efficiently

Date: 2026-09-14. Status: corrected implementation, feature/model rerun and
allocation replay executed on the frozen source. The rerun fixes the prior
calendar-risk label, stale-holding, capped-weight, raw-mark and
production-incumbent replay defects. Outputs and findings are in
[summary-02.md](summary-02.md).
Exact engine-settlement replay and a full feature-bundle null remain promotion
validation, not prerequisites for rerunning the implemented workflow.

## Objective and precedence

Rewrite the existing four notebooks and their shared helper to answer the original question: can available vault price history identify portfolios with steadier returns, including strong young vaults?

This plan supersedes conflicting rules in [plan.md](plan.md) and earlier Claude reviews. In particular, remove the publication-date filter and the global 30-day observed-history admission rule from the main experiment. Use daily predictions and all usable historical data. Do not turn a provenance limitation into a requirement to wait months for new observations.

Preserve [summary-01.md](summary-01.md) and the first-pass artefacts as historical results. The old cash-only replay is not a production benchmark.

## Research data and clocks

1. Use the frozen reconstructed share-price series at its observation timestamps. Do not filter rows using `written_at <= observation_date + 2 days`, or use ingestion dates as vault inception. Preserve ingestion time, raw NAV and provider repair status for audit only. Describe the experiment as historical research on the provider's current reconstructed series; do not claim a historical revision archive exists.
2. Load all available earlier history for feature calculation and model training. Set the headline evaluation interval to the final 365 complete daily return intervals supported by the frozen source. Determine the last complete day from observation timestamps and bar definitions, rather than assuming the latest partial date is complete. Report exact boundaries and actual daily coverage.
3. Build one daily feature/prediction grid. Keep each vault on dates where it has usable data; do not restrict the whole panel to the common history of all vaults. A year means approximately 365 daily decision dates, not 183 two-day decisions or 64 dates after the old filter.
4. Define features at a completed daily close. Where a fresh NAV exists, the historical NAV simulation uses an explicit idealised close-fill assumption. For sparse series, issue daily predictions but execute at the next observed NAV, never at an old carried mark. Record the execution delay and do not revise the original signal using information arriving before the fill. Apply identical fill conventions to comparator and candidate; align completed BTC bars consistently. Remove the artificial T+2 prediction clock.
5. Keep causal rolling calculations: features at T never use observations after T. Train only on outcomes whose exit time is no later than the model fit boundary. These rules prevent lookahead without discarding older history because it was ingested later.
6. Preserve the exact BTC snapshot and source hashes. Provider-carried rows remain distinct from fresh marks. A refreshed unchanged NAV is still valid evidence; do not require positive returns or price changes to count an observation.

## Young-vault admission and missing features

Use a small computational minimum rather than an age or daily-density requirement: at least two valid, non-provider-carried NAV observations separated by at least one calendar day, with the latest NAV and latest known TVL no more than 14 days old, and latest known TVL at least $7,500. Join those observations backwards as of each prediction timestamp. Record their actual timestamps and ages. This permits daily predictions from weekly observations after the second weekly mark. It also permits young daily-observed vaults without waiting seven or thirty days. Predictions with little evidence are explicitly flagged; eligibility does not assert that risk is accurately estimable.

**Remove the proposed six-daily-returns-in-seven-days admission rule.** The older cache is predominantly weekly. No minimum daily-observation density applies to global eligibility. The 14-day recency expiry is a fixed initial setting allowing weekly updates and one missed update, not a searched performance threshold.

There is **no global 30/90/180/360-day history requirement**, no ingestion-history requirement, and no requirement to have every feature or future label. Calendar age and available-history length are optional predictors and diagnostics, not admission gates.

| Feature group | Lookbacks or spans | Treatment of young vaults |
| --- | --- | --- |
| Short return and risk core | 7, 14, 21, 30, 45, 60 days | Add log return, volatility, downside deviation, drawdown and losing-day fraction at these windows. Dense daily versions are optional; the sparse interval core below supplies predictions when they are missing. |
| Existing medium/long catalogue | Existing 90, 120, 180, 270, 360-day configurations where applicable | Retain as optional columns. An unavailable column never deletes the vault's row. Do not cross every family with every window. |
| BTC exposure | 7, 14, 30, 90 days | Single-window aligned OLS beta and residual risk, with sample count and residual degrees of freedom. Short beta is noisy; it is optional and cannot block the core model. |
| EMA and EWM | Existing spans 10, 90, 120, 180, 270, 360 | Use elapsed-time decay on actual observations; expose input count, age and seed influence. NAV EMA can initialise from the first mark. Return dispersion needs at least three observed intervals and remains optional. Carried daily predictions are not new EMA inputs. |
| Age, TVL and observation quality | Current values; 7/30/90-day summaries | Available current and short summaries can be used immediately. Coverage controls describe available history rather than requiring a complete long window. |
| Sharpe, Sortino, skewness and kurtosis | Retain existing optional catalogue | Undefined or insufficiently supported estimates remain missing. Do not make these ratios prerequisites for a prediction. |

For literal L-day return/CAGR features, require the actual L-day endpoints and otherwise leave the value missing. For explicitly daily fixed-window risk statistics, require the elapsed window and at least 80% valid daily observations. This is a **feature-local** rule, not a vault admission rule. Do not present an eight-day return as CAGR-360. The sparse interval core and optional dense features provide separate, honestly labelled evidence.

## Weekly and irregular observation contract

Daily prediction frequency is independent of observation frequency. Keep the original irregular observations and construct daily prediction rows by backward as-of lookup. Between weekly updates, some predictions will repeat; this is expected. Retain `last_observation_ts`, `nav_age_days`, interval durations, actual observation counts and provider-carried flags. Never interpolate from a future weekly mark or treat a forward-filled mark as a new observation.

The common sparse core includes the most recent observed log return, its actual duration, log return per elapsed day, latest known TVL, observation age/count and available-history length. With two marks seven days apart it already contains usable economic inputs. Add bounded summaries over the existing lookbacks using only actual observed intervals; expose their actual covered duration and minimum sample counts. Do not silently substitute a shorter estimate into a literal fixed-L column.

| Quantity | Sparse-series treatment |
| --- | --- |
| Return | Use `log(P_end / P_start)` and actual elapsed days. A seven-day interval is one seven-day return, not seven measured daily returns. |
| Risk | Keep true daily risk missing when daily paths are unavailable. Optional interval-risk proxies require at least three observed intervals, account for their durations, and are labelled separately from daily volatility/downside risk. Annualisation of such proxies is an assumption, not recovery of an unobserved daily path. |
| Drawdown and losing frequency | Calculate on observed marks/intervals, explicitly named as observed-path measures. Intraperiod drawdowns are unknown. |
| BTC beta and residual risk | Aggregate BTC log returns between exactly the same vault endpoints before fitting. Require sufficient aligned intervals and residual degrees of freedom; daily BTC observations cannot manufacture vault observations. |
| EMA | Update at observed marks with decay based on elapsed calendar time. Carry the estimate for prediction purposes while increasing its observation age; do not update it with invented daily returns. |

Models use the sparse core when daily-risk and long-history columns are missing. Fit preprocessing within folds and report dense-versus-weekly/irregular coverage and performance separately. Missing daily volatility must not be imputed as zero risk. For portfolio sizing without a credible risk estimate, use capped equal weights rather than excluding all sparse vaults or applying an inverse-zero-risk weight.

Sparse outcome handling must be explicit. Keep nominal daily prediction horizons H in the requested grid. For execution-aligned growth evaluation, take the first observed NAV at/after the decision and the first observed NAV at/after `entry_ts + H`, allowing at most seven days of delay at each endpoint. Otherwise mark that label unavailable. Save nominal H, entry/exit timestamps, delays, actual holding duration and the unscaled return. For modelling a nominal-H growth proxy, scale realised log growth by `H / actual_holding_days` and label this convention explicitly; also report unscaled returns and actual-duration annualisation. Score exact-endpoint results separately from delayed-endpoint proxies.

Weekly observations can support growth labels without supporting daily variance labels. Leave unobservable daily risk outcomes missing; do not forward-fill prices to manufacture daily-risk targets. If coarse interval-risk targets are evaluated, give them separate names/models and never pool them as equivalent to observed daily-risk labels. The seven-day sparse risk target will often be unavailable even when its growth target is usable.

Resolve training eligibility using the actual exit timestamp, including endpoint delays. Daily predictions sharing one realised entry/exit pair do not become independent labels: retain a shared outcome identifier and weight duplicate outcome pairs to total one within each training sample. Report unique observed intervals/outcomes alongside daily prediction counts and use temporal block uncertainty.

Fit imputation and scaling on training rows only. Drop all-missing columns within a training fold, never all rows missing optional long features. Use training medians plus missingness indicators, and compare the short-core model with the optional-feature model on identical evaluation rows. Report whether adding age or missingness introduces a systematic young-vault penalty.

The incumbent's 14-day loss gate must not silently exclude vaults younger than 14 days from the research panel. Keep exact incumbent rules in its own replay. For candidate portfolio eligibility, apply that gate when its full-window value exists; record it as unavailable otherwise and use the short-evidence admission rule. Attribute access differences separately from ranking improvements.

## Targets and evaluation

- Produce daily predictions for forward log growth, downside semivariance and total variance at **7, 14, 21, 30, 45, 60 and 90 days**. Fit/evaluate every horizon, not only 30 days. Retain forward Sharpe, Sortino, maximum drawdown and ulcer as descriptive outcomes.
- A seven-day-old vault can receive a 90-day forecast. Its training/evaluation label becomes available 90 days later. Missing long-horizon outcomes must not delete shorter-horizon labels or today's prediction.
- Separate training-history requirements from each vault's history. Pool training examples across vaults; a newly admitted vault uses the fitted model immediately. Never require it to span a whole training fold.
- Use expanding chronological training with monthly refits and daily predictions. Start fitting each horizon when at least 60 distinct matured training dates and adequate cross-sectional coverage exist; use pre-evaluation history where available. Report warm-up dates without model forecasts instead of moving the headline data window. Do not reuse the old fixed two-fold setup.
- Select features and fit preprocessing inside each training fold. Use the actual label end/availability convention to purge outcomes crossing the fit boundary. Compare horizons on both their full valid samples and common evaluation dates.
- Retain equal-date IC, but also evaluate forward returns and risk of the investable upper ranking. Compare simple low-volatility and short-return controls, a small short-core Ridge model, and that model with optional families. Test incremental value on matched rows.
- Daily overlapping labels are useful training/evaluation data, not independent experiments. Use paired date-block intervals and the existing bounded permutation test for promotion decisions. Do not reduce prediction frequency to avoid accounting for dependence.
- Report age cohorts <7, 7–13, 14–29, 30–89, 90–179, 180–359 and 360+ days, with actual counts. Separately report daily, weekly and irregular sampling cohorts. Separate metadata age from available-history length. Check a verified Stratwise address as an illustration, not a privileged training example.

## Notebook rewrite order

| File | Required rewrite | Evidence to save |
| --- | --- | --- |
| `01-data-and-baseline.ipynb` | Load the complete reconstructed series without publication filtering; daily grid; separate warm-up and one-year evaluation; preserve repair provenance and BTC snapshot | Coverage by date and age; raw → valid NAV → TVL → short-evidence eligibility funnel; snapshot manifest and exact evaluation dates |
| `02-feature-panel.ipynb` | Remove global observed-history gate; add the short core; feature-local missingness; daily targets at all seven horizons | Formula/units/minimum-count manifest; young-vault feature availability; daily labels and statuses; prefix causality and entry-clock checks |
| `03-ic-screen.ipynb` | Daily predictions with monthly refits; horizon-specific matured training; short-core versus optional-feature comparisons | Per-vault/date/horizon predictions; IC profiles, cohort results, matched controls, basket outcomes and uncertainty; no final model declaration based only on in-sample IC |
| `04-allocation-validation.ipynb` | Replace the degenerate cash anchor with a faithful incumbent replay; evaluate supported short-history candidates and dynamic breadth | Daily equity, holdings, cash, turnover, fees, concentration and return contributions; matched-date comparisons |

Change the shared `ic_research.py` defaults and callers together. Use separate prediction and rebalance settings: daily forecasts are mandatory; production's native two-day rebalance remains the primary matched portfolio comparison. Daily candidate rebalancing is a labelled follow-up, not a hidden change in the comparison clock.

The baseline must reproduce incumbent missing-score, ranking and sizing behaviour rather than the research all-missing abstention shortcut. Feed it the available pre-evaluation history. If a production feature is genuinely unavailable for a vault, follow production semantics and report that coverage; do not replace all holdings with cash because of the discarded ingestion history.

Candidate sizing uses short-window risk when available (30-day, then 14-day, then seven-day daily volatility), with a fixed risk floor. If daily risk is unavailable, use capped equal weights; do not force an unvalidated sparse-risk proxy into inverse-volatility sizing. Missing 90-day or daily volatility must not create another young/sparse-vault exclusion. Keep explicit portfolio/TVL caps and a 5% maximum weight for vaults with fewer than 90 days of available history; no compulsory young-vault allocation. Test adaptive breadth against the same information with fixed breadth so concentration changes do not masquerade as feature improvements. Value sparse holdings using explicitly aged last marks, but report coarse-period realised returns and observation coverage alongside marked equity; do not interpret carried flat days as measured daily stability.

## Acceptance checks

1. The headline data panel covers approximately one year at daily frequency when the source supports it. Every missing date has a coverage explanation; none is removed because of `written_at` or a required 360-day feature.
2. A synthetic vault with seven days of valid return evidence receives a prediction with every 90/180/360-day feature missing. Missing 90-day risk also does not prevent candidate sizing when short-risk evidence exists.
3. Altering ingestion timestamps alone leaves main-experiment features, eligibility and predictions unchanged. Altering future NAV observations leaves earlier features and predictions unchanged.
4. All seven horizons have daily prediction outputs or explicit training-warm-up status. Unmatured labels are excluded only from the relevant training/evaluation calculation.
5. Short-core and optional-feature results use matched rows for incremental comparisons; daily evaluation uncertainty accounts for overlapping outcomes.
6. The incumbent replay contains interpretable holdings/trades whenever its actual rules and available data permit them. No artificial cash result caused by the removed publication filter is accepted as a performance comparison.
7. Rerun the four notebooks in order using the repository notebook runner. Save new outputs separately from first-pass artefacts, then write `summary-02.md` with changes in coverage, findings and portfolio evidence.
8. A weekly synthetic vault receives daily predictions after its second valid mark, including between updates, with every daily-risk/long-history feature missing. It remains admitted within the 14-day recency limit and expires beyond it. No trade fills at an old carried price.
9. A jump between two weekly marks produces one observed interval return, not six measured zero returns and one measured daily jump. Future mark perturbations cannot change predictions issued before the mark. Daily risk labels remain unavailable where the intervening path is unobserved.
10. Recount the pre-23-January-2026 data under sparse admission and report all remaining exclusions by reason. Save daily prediction count, unique outcome count and horizon-specific mature-label count separately; replace the earlier six-daily-return sample estimate.

## Scope and review discipline

Keep the existing notebook structure and small model class. Do not add a new collection platform, deep learning or a large feature-generation search. Prospective collection can proceed separately and is not a gate on using the existing historical dataset.

If reviewed with Claude, provide this rewrite contract before the old plan and explain that earlier long-history/publication gates have been explicitly superseded by the user. Ask for concrete calculation, leakage, missingness and comparison defects. Judge feedback against this objective; do not reinstate discarded barriers or repeatedly rerun notebooks for review-output-file artefacts.
