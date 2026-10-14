# Experiment 10 — sorting, risk estimation and portfolio allocation snapshots

Written 10 October 2026. **Status: implemented and executed on 10 October 2026. The mandatory core and bounded covariance, satellite and capacity companions are complete. See [the notebook](10-research-portfolio-snapshots.ipynb) and [findings](10-portfolio-snapshot-findings.md); separately deferred extensions remain labelled.**

**Expansion plan:** [Composite scores for ranking and allocation](10-expanded-score-allocation-plan.md) supersedes the three-score restriction for the next work. It starts with a 36-arm smoke matrix over the full available 2026 history with 2025 indicator warmup; broader stages have not been executed.

Planned notebook: `10-research-portfolio-snapshots.ipynb`. Research folder: `scratchpad/hyperliquid-vov-2nd`. Read [summary.md](summary.md) and the [sparse NAV correction](sparse-nav-rerun-2026-10-10.md) before implementing. This plan supersedes the earlier suggestion to begin with a grid of full strategy backtests.

## 1. Goal and decisions this experiment supports

Measure separately whether our frozen scoring methods select better vaults, whether risk estimates predict subsequent risk, whether position weights improve a selected basket, and whether additional positions help or dilute it. Obtain information coefficients (IC) where they measure the intended question, and paired economic/risk outcomes where correlation is insufficient.

The user considers feature exploration sufficiently extensive. Do not create new return-prediction features, retune the scoring coefficients, or search the 139 earlier score recipes. Use the existing three focal scores. The experiment is a repeated observational allocation study: construct independent portfolios at each origin, hold fixed units for a specified horizon, and evaluate the subsequent NAV path. There is no inherited portfolio state, strategy engine, turnover execution or compounded strategy equity curve.

The intended output is a short list of construction rules worth implementing in a later complete backtest, together with explanations of where their effect comes from. Valid conclusions include no benefit, an advantage confined to a period/cohort, and insufficient support.

### Questions and falsifiable hypotheses

| ID | Question | Hypothesis and evidence needed |
| --- | --- | --- |
| S | Does sorting select useful opportunities? | Frozen score ranks have positive future return IC and selected equal-weight baskets improve on a common eligible-universe reference. Show both broad ordering and selection-boundary behaviour. |
| R | Is the risk estimate useful? | Predicted variance orders future variance and improves calibrated loss against a contemporaneous peer-risk baseline. A high risk IC alone does not establish accurate risk levels. |
| W | Does weighting add value? | On exactly the same basket and invested budget, unequal weights improve return and/or reduce realised risk compared with equal weights. State the trade-off instead of collapsing it into an arbitrary objective. |
| N | Does breadth improve construction? | Increasing N improves the return/risk trade-off and effective diversification. Attribute the change to new vaults and changed weights in shared vaults. |
| C | Do allocation constraints alter the answer? | Conclusions survive a clearly specified capacity/concentration projection, or the distortion explains the change. This is conditional on recorded capacity, not a production execution claim. |
| Q | Are apparent advantages a reporting artefact? | Conclusions remain interpretable after separating young, sparse, stale, near-flat and source-price-guard-divergent histories, and after accounting for missing future outcomes. |

## 2. Starting evidence and scope

- Replicated v11 uses **90-day inverse variance**. Its 45-day window belongs to the Sortino ranking input. Source comments describe earlier lookback/exponent research and a reversal of the weighting comparison when the concentration cap changes.
- NB03 compared fixed alternative weighting policies; regularisation and exponent changed together in some arms. It did not establish which individual component helped.
- NB07 changed breadth and entry/exit rank settings together. Most of the deterioration from six to ten positions in the four-input candidate came from changed allocations/timing in shared vaults. This motivates direct attribution of shared and added positions.
- NB08/NB09 now support causal calendar-day NAV filling. Volatility persistence is stronger than broad return predictability, but observed NAV risk includes reporting effects.
- The 2026 period and full history have both been extensively researched. Results are retrospective screening, even though every individual snapshot is causally constructed. The 2023-03-01 secondary start matches the existing source replay and pinned research period; it is not estimated vault inception or the earliest possible chain history.

The snapshot study deliberately omits incumbent retention, trading fees, realised profit accounting, rebalance costs, lock-ups during a holding period and future capacity changes. These mechanisms need a later engine replay. Do not present snapshot outcomes as executable CAGR, portfolio backtest Sharpe or a new production strategy.

## 3. Formal estimands: IC is not a universal weighting score

At origin T and horizon h, compute within-date Spearman correlation across the eligible vaults between the frozen score s and future simple return R. Report the equal-date mean of these correlations; do not pool all vault/date rows into one primary IC.

`IC_score(T,h) = Spearman_i(s_i,T, R_i,T,h)`.

Future CAGR and simple return have identical ranks at a fixed horizon. Report one return-ranking result, not two pieces of evidence. Score versus future vault Sharpe is a separate secondary target. Keep undefined Sharpe missing.

For a positive risk estimate sigma and unconstrained `w_i ∝ sigma_i^(-p)`, every positive p produces the same weight ranking. Consequently, rank IC cannot distinguish inverse volatility from inverse variance or choose concentration strength. Equal weights have undefined weight IC, not zero skill. Even Pearson correlation discards allocation scale and cannot replace an economic comparison.

For an eligible universe U, selected basket S, normalised initial weights w summing to one, and simple h-day NAV returns R:

- `R_universe_equal = mean(R_i for i in U)`.
- `R_selected_equal = mean(R_i for i in S)`.
- `R_selected_weighted = sum(w_i * R_i for i in S)`.
- `selection_lift = R_selected_equal - R_universe_equal`.
- `weighting_lift = R_selected_weighted - R_selected_equal`.
- `total_lift = selection_lift + weighting_lift` exactly on the same origin and outcome support.

These are arithmetic percentage-point return differences over h days. Never subtract individual vault Sharpes to infer portfolio Sharpe, and never compute a portfolio return as a weighted average of individual CAGRs.

Optional descriptive weight association: Pearson correlation between active weights `w_i - 1/|S|` and R. The exact dollar-relevant quantity is their dot product. With population covariance, `weighting_lift = |S| * Cov_i(w_i - 1/|S|, R_i)`. Assert this identity and retain the scale of active weights. Label this association distinctly from forecast IC.

## 4. Data, periods and clocks

### Pinned inputs and reporting periods

Use the same repaired publication as NB08/NB09 under `_artifacts-restored-2026-10-07`. Do not fetch a newer archive during implementation. Record archive hashes, strategy/framework commits, guard snapshot, relevant source hashes and every configuration field before producing outcomes. Verify the actual file hashes rather than trusting a directory name.

- Primary displayed period: **2026-01-01 → 2026-10-05, end exclusive, UTC**.
- Secondary full-history origin period: **2023-03-01 → 2026-10-05**, subject to available pre-origin inputs.
- Add a pre-2026-only summary when comparing periods; the full-history period contains 2026 and is not independent confirmation.
- All charts, tables and Markdown result tables default to the primary period. Every title/caption identifies period and horizon. Secondary periods require an explicit separate heading or collapsed section.

Forecast origins are the existing four-day grid anchored at 2026-01-01, extended backwards by multiples of four calendar days. Horizons are 7, 30 and 90 calendar days; 30 days is the primary endpoint. Alternative grid phases are sensitivities, not additional independent observations. Under the frozen calendar-block reporting gate below, the 2026 period is descriptive by construction at all three horizons. Full-history and pre-2026 results may have enough blocks for exploratory intervals; neither becomes confirmatory evidence merely by being longer.

At T, the completed daily NAV anchor is A=T−1 under the earlier candle-label convention. Historical observations must have timestamps strictly before T. An L-day complete lookback uses prices A−L through A inclusive. Future target marks run from A through A+h, including the anchor. Earliest daily label availability is A+h+1 day. Persist all these timestamps explicitly. Assert that the cached score recipe cutoff is this same A; the column name alone is not evidence of correct timing. Derive final admissible origins from the actual grid and h, rather than copying approximate dates or effective-window counts from a review.

### Existing code and data to reuse

| Resource | Reuse | Constraint |
| --- | --- | --- |
| `score_forecast_data.py`, registry and three focal score rows | Frozen recipes, scores and source-compatible eligibility | Load only `v11`, `blend_46d`, `focal_four` with Parquet filtering; do not load all 23.5 million score rows or regenerate 139 recipes. |
| NB08 `prices.parquet`, `eligibility.parquet`, `labels.parquet`, `provenance.json` | Identity, observation provenance and endpoint cross-checks | Labels must be the post-sparse-fix generation, `delay_days=0`; source guarded candles are not raw target NAV. |
| `k_ratio_features.py:raw_inputs`, `forward_fill_nav` | Reading positive raw NAV and building the calendar | Confirm sufficient pre-origin history from the original archive; a truncated cache must not manufacture young vaults. |
| `score_forecast_audit.py`, `k_ratio_forecast_audit.py` | Independent timing and sparse-data checks | Do not simply call the function under test to create its expected result. |
| `weighting_methods.py` | Reference for earlier policies and source comparison | Its non-flat-count confidence and fixed regularisation constants are research choices, not validated defaults to inherit silently. |
| `score_forecast_visualisation.py`, `k_ratio_forecast_report.py` | Table styling and separate-image presentation | Reuse display helpers without importing old findings or old support decisions. |

Construct one shared daily NAV tensor and one observation-provenance tensor; cache risk estimates once per origin/window, not once per portfolio arm. Preserve the full selected identity list even when an outcome is missing.

## 5. Sparse histories, young vaults and missing values

### Calendar construction

1. Keep finite positive raw share NAV; retain reasons/counts for rejected non-positive or non-finite observations.
2. Choose the last valid observation within each labelled UTC day using a stable timestamp order.
3. Reindex to the complete daily calendar and forward-fill causally from the first positive mark. Never backfill leading history or compress missing calendar days into adjacent observations.
4. Retain actual-observation masks, carried-value flags, actual timestamps, age of the latest observation, age since first recorded NAV, actual update counts, calendar-return counts, flat-return counts and source/raw price divergence.
5. Historical features may carry the latest known value through A. A future label cannot extend past the vault's final actual positive observation or the archive boundary. This terminal check belongs to evaluation, never to selection.
6. Carried days are valuation assumptions and not new independent observations. Do not use the number of filled rows as confidence in a risk estimate. Do not count genuinely observed unchanged NAV as missing data merely because its return is zero.

Recorded history is not known inception. Positive tiny NAV values remain in outcomes; do not floor away genuine collapses. An unknown redemption payout is not zero NAV, last NAV forever, or a forced total loss. Audit rejected zero/non-positive NAV records separately: a verified total loss or actual payout needs an explicit terminal-event treatment and independent evidence. Do not classify a documented loss as a harmless data gap. This study otherwise retains unresolved terminal outcomes; it does not invent a closure ledger.

### Missing score policy

Use each frozen registry recipe exactly, including clipping, component propagation and `missing=True`. Store the raw missing score and reason. A finite zero, a component-imputed score and a missing composite are different states.

The primary stateless selection adapter ranks finite scores descending, then appends eligible unscored vaults as a separate lowest-priority tier. This preserves access for young vaults when scored candidates do not fill N. It is a declared analogue of the source fallback, not a reproduction of stateful v11 retention. Use the canonical lowercase vault address as the deterministic final tie-breaker; never use future return, history length or risk to resolve a tie silently.

For score IC, use finite scores only and report omitted unscored counts/outcomes separately. For portfolio selection, retain the unscored tier. Include a paired `exclude_unscored` sensitivity and show its changed membership and available breadth. No global complete-case feature filter is allowed.

### Missing and short risk history

Risk estimation and scoring missingness are independent. A missing long-window score must not make a usable risk estimate disappear, and missing risk must not retrospectively remove a selected vault.

For each L, the available daily return segment begins no earlier than the first recorded positive NAV. Compute a partial-window sample variance when there are at least two calendar returns and at least two distinct actual observation dates supporting the segment: the actual observation behind the initial NAV anchor, which may precede the window, and at least one subsequent actual daily update inside the return segment. Require finite returns and variance; non-finite results get an explicit invalid-estimate reason and the same prior fallback. Store the exact span n and actual update count m. With less information, the empirical variance is unavailable. A one-price carried-flat path is unknown risk, not zero risk.

Do not extrapolate a young vault's partial history into a claimed L-day sample. Label `full_window`, `partial_window`, `prior_only`, `observed_flat` and `unavailable` separately. Fully observed flat paths can have empirical variance zero; Sharpe remains undefined when its denominator is zero.

The implementer must keep all selected vaults in the output and use the declared risk fallback below. If no supported positive forecast or fallback can be estimated, mark the allocation as using an equal-weight fallback, rather than silently deleting the vault or pretending an arbitrary volatility is measured.

## 6. Risk estimators and their evaluation

### Reference and primary estimators

Implement these as separate, labelled model IDs:

1. **Source-compatible control:** reproduce the current source 90-day volatility and `0.0001` daily volatility floor from source candles. Verify against cached source indicators or direct indicator calculations. This is a control for requested risk weights, not a claim to reproduce the source portfolio. Exact source-weight checks use common baskets with supported source indicators; a young-vault fallback in the snapshot adapter is labelled a hybrid policy and cannot be claimed as exact source behaviour.
2. **Raw rolling control:** sample variance of causally filled raw NAV daily simple returns over the declared full or partial window L. Its final forecast and weight variance is max(empirical variance, 1e-8), using the source .0001 daily-sigma floor consistently. Store unfloored empirical variance separately. Missing empirical variance uses the peer prior followed by that same floor; the reported empirical field stays missing. If both are unavailable, apply the declared allocation fallback, never `fillna(floor)` as if it were measured risk. This isolates source-price processing and exposes the inherited floor.
3. **Regularised partial-history estimator:** use available empirical variance and shrink it towards a contemporaneous eligible-peer prior. This is the primary young-vault treatment.

Define the peer prior separately for vault i at T and L, excluding i itself (leave-one-out), as the median of strictly positive empirical variances among eligible peers with a complete elapsed L-day window and at least two actual positive observation dates. If that pool is empty, use strictly positive partial-window estimates and label the fallback. If both pools are empty, there is no supported positive prior. Never use future data to populate it. Store prior pool size, dispersion and which fallback was used. A positive one-peer prior is allowed in the primary estimator and explicitly marked weak. In gated-prior sensitivities, require at least 5 or 10 peers; if the full-window pool fails the gate, try the positive partial-window pool with the same gate. If that also fails, the prior is unavailable. Never silently lower the gate.

For counts, m is the number of actual daily NAV updates at return endpoints inside the available calendar segment, with a valid preceding NAV anchor. Retain the actual timestamp behind a carried initial anchor. Multiple intraday observations on the same date do not increase m.

For the regularised estimator, `v_hat = c * v_empirical + (1-c) * v_prior`, with `c = m/(m+kappa)`. Here m counts actual daily observation updates contributing to the available segment, not non-zero returns or imputed calendar rows. For an unavailable empirical variance, set c=0. This is a transparent support-weight heuristic, not a claimed effective sample size or posterior derived from a likelihood. Use `kappa=L/3` in the primary regularised window comparison. A fully observed window then has approximately constant support weight across L; otherwise fixed kappa would confound lookback with shrinkage strength. The ratio one-third is a registered design choice, reproducing kappa=30 at L=90, not an empirically established optimum. Compare fixed kappa=30 across L and kappa=10/90 at L=90 as paired sensitivities. Do not select kappa by the highest snapshot profit.

When a positive prior exists, this estimator yields positive risk even for a one-mark or flat vault. If no positive prior exists but the empirical variance is strictly positive, use that empirical variance and mark `empirical_without_prior`. If neither a positive prior nor a positive empirical variance exists, risk is unsupported. In a basket with any such unsupported component, the allocation adapter uses equal weights for that entire basket and records `risk_fallback_equal`; it does not reallocate the unsupported name's share to measured names. Such cases do not contribute manufactured risk IC or QLIKE values. The source-floor control remains separately visible.

### Variance targets and losses

For each h, define `v_realised = Var_ddof1(r[A+1:A+h])` in daily simple-return units. Volatility is its square root; annualised display volatility multiplies by sqrt(365). All forecasts compared with this target must be daily variance forecasts. Store uncentred mean squared returns separately as a second-moment diagnostic; do not interchange them.

Measure per-date risk rank IC over eligible vaults. Also measure calibration by bins formed from predictions at T, predicted/realised variance summaries, variance MSE and paired QLIKE loss against the peer prior:

`L(v_hat, v_realised) = log(v_hat) + v_realised / v_hat`, for `v_hat > 0`.

Use paired loss differences `log(v_method/v_reference) + v_realised*(1/v_method - 1/v_reference)` on identical rows. Zero realised variance is allowed; a non-positive forecast is unsupported and separately counted. Do not report percentage changes of QLIKE: its arbitrary additive level makes them misleading. Give every date equal total weight before averaging its vault losses. Report the mean difference, median, fraction favouring the method, and the distribution of paired row differences. For tail concentration, report the share of the total absolute weighted difference accounted for by the largest 5% of absolute weighted row differences, and their signed contribution separately. Each row's weight is 1/(number of paired vaults at its origin), followed by equal weighting of origins. Do not divide by a near-zero signed total or winsorise the primary loss. The 5% cutoff is descriptive and is registered, not a filtering rule.

Calibration ratio means `equal-date mean(v_hat) / equal-date mean(v_realised)` on paired support; undefined when the denominator is zero. Also show the median `log(v_hat/v_realised)` on strictly positive realised-variance rows and their excluded-zero fraction. No arbitrary epsilon may turn a zero realised variance into a positive observation.

For selected baskets, QLIKE and calibration are primary risk diagnostics; per-date six-name rank IC is secondary and displays its small cross-section. As an allocation-level check, compare `w' diag(v_hat) w` and, where supported, `w' Sigma_hat w` at entry with realised fixed-unit portfolio daily variance. These are entry-risk forecasts for a subsequent drifting portfolio, so the calibration includes both risk forecast error and weight drift. Do not imply an exact constant-weight forecasting target.

QLIKE is motivated by variance-forecast comparison under noisy proxies, but forward-filled NAV variance is not guaranteed to be a conditionally unbiased proxy for latent economic risk. Report the empirical held-NAV target and qualify that interpretation explicitly. [Patton (2011)](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf).

No universal correction factor for sparse observations is assumed. A carried series with catch-up jumps may redistribute squared variation across days; it need not have volatility reduced by the square root of the observation interval. Unobserved within-gap fluctuations can still be missed. Evaluate observed reporting patterns and simulations rather than imposing a blanket scaling rule.

**Irregular-interval companion diagnostic:** from actual positive observations at times t_k, compute `q_interval = sum((log P_k - log P_(k-1))**2) / sum(delta_days_k)` for intervals wholly contained in the historical window. This is an observed log-return quadratic-variation proxy under explicit process/sampling assumptions; drift, jumps and informative observation times can bias it. Preserve covered duration and interval distribution. It is not automatically an unbiased estimate of latent risk or interchangeable with daily simple-return sample variance. Compare it with daily log-return second moments and an equivalent future log-return proxy on identical support; do not mix its QLIKE table with different-unit/definition targets. No backfill or interpolation across the current decision time.

**Optional chronological calibration:** fit an affine calibration of predicted variance on matured historical outcomes and evaluate it on later origins, with each date equally weighted. A Mincer–Zarnowitz calibration plot is descriptive; its log–log slope is not automatically the correct shrinkage coefficient. Any positivity-constrained level calibration is a separately registered model, with training window, support, objective and fallback specified before fitting. This is deferred until the fixed estimators have been reported; do not sneak in an estimated kappa using evaluation outcomes.

Weekly sampling is a declared sensitivity: use non-overlapping seven-calendar-day simple returns ending at A, retain the anchor, and report `Var(weekly return)/7` as a daily-equivalent approximation. Show actual updates and all seven weekly phases. Do not drop gaps and pretend unequal observation intervals are equal-length returns. Annualisation across weekly and daily returns assumes a relationship that reporting autocorrelation may violate.

## 7. Snapshot construction and outcome calculation

### Core factorial and benchmarks

Freeze score IDs `{v11, blend_46d, focal_four}`; N `{4,6,8,10}`; rolling windows `{30,60,90,180}`; weighting powers `{0,0.5,1,2}`. Primary horizon is 30 days. Six positions, 90-day risk and inverse variance are the reference settings, not a privileged optimum.

Run the core in stages so interactions remain interpretable:

- **Stage R:** all risk estimators/windows on one common eligible panel, then the same diagnostics conditional on membership in each frozen top-six basket. Selection on low estimated risk can amplify estimation error; do not assume its direction or magnitude without measuring it. Risk calibration must be evaluated where the weights actually use it.
- **Stage W:** N=6; all three frozen sorts; raw/regularised estimators; L=30/60/90/180; p=0/.5/1/2. Primary regularisation uses kappa=L/3; fixed kappa=30 across L and kappa=10/90 at L=90 are paired robustness arms rather than a complete new grid. Add L=75/105 at N=6/p=2 as a local stability diagnostic around the source window; these neighbours come from the source's earlier search and are not a new winner-selection grid.
- **Stage N:** N=4/6/8/10 at L=90, p=0/1/2 for both estimators. Supplement with marginal-rank profiles. The full N-by-L factorial is not required; add an interaction only if a specified mechanism needs it and mark it as follow-up exploration.
- **Stage C:** the bounded capacity branch below. Its controls are fixed before viewing R/W/N results, not selected from their winners.

Equal weights are one policy per score/N: p=0 must not be duplicated across windows, estimator choices or kappa values. Compute source-compatible requested weights as an additional explicit control. Store the complete design registry and deduplicate any other economically identical weight vectors before counting independent configurations.

Use the same sorted basket for all weighting arms at a given score/N/T. Set `N_actual=min(N, number eligible)`; do not postpone the first origin until N vaults exist. Dates with fewer candidates remain visible and are labelled candidate-limited breadth. When no vault is eligible, retain a cash-only origin with a reason, but no cross-sectional IC.

For positive risk estimates calculate log weights `log_u_i = -p/2 * log(v_hat_i)`, subtract the largest log weight, exponentiate and normalise. This avoids avoidable overflow. No hidden minimum weight or clipping. Any explicit risk floor or allocation cap is part of the registered policy.

Pure construction uses a common 100% invested budget and no dollar-capacity claims. This is a normalisation for comparison, not a recommendation to deploy all capital. The constrained branch below introduces cash and dollar scale.

### Hold units, not constantly rebalanced weights

For each selected vault, set units proportional to `w_i/P_i(A)`. For d=0..h:

`V(d) = w_cash + sum_i w_i * P_i(A+d)/P_i(A)`.

Use cash gross growth 1 in the primary calculation. At d=0, V=1; at d=h, return is V(h)-1. Portfolio daily returns are `V(d)/V(d-1)-1`. Weights drift naturally. Do not substitute `sum_i w_i*r_i,d` each day, which would imply daily rebalancing.

Calculate horizon simple/log return, path volatility, sample Sharpe if defined, maximum drawdown, largest initial weight, invested effective position count `1/sum(q_i^2)` where q renormalises the invested weights only, and initial estimated risk contributions where covariance is available. Report snapshot Sharpe distributions as noisy horizon outcomes; they are not one strategy Sharpe.

### Reporting-boundary attribution

A carried anchor is a valuation convention, not proof of the NAV at which a deposit at T would execute. A later catch-up observation can include movement from both before and after T; its exact economic timing is unknown. Similarly, a carried endpoint can omit movement before the planned exit. Keep sparse vaults in the primary population and expose these boundary assumptions.

Record actual timestamp/age behind both A and A+h, the first actual mark F after A within the holding window, the last actual mark E at or before A+h, the invested weight in carried anchors/endpoints, and future actual update counts. If the anchor is actually observed, set F=A for this attribution. If the anchor is carried and no new actual mark exists inside h, report `no_in_window_update`: the held-NAV return may be zero but no first-update decomposition is identified.

Where F exists, with P0=P(A), PF=P(F), PH=P(A+h):

- `first_update_component = (PF-P0)/P0`.
- `remaining_mark_component = (PH-PF)/P0`.
- Their sum equals the h-day simple return exactly. The second term uses the original notional, not a fresh investment of one dollar at F.

Apply the same decomposition to weighting lift with active weights: sum each component times `(w_i - b_i)` on identical fully resolved baskets. Describe the first term as **first-update attribution**, not a known pre-origin return or pure stale-price bias. Removing it removes some potentially genuine post-origin movement too. Show its size and sign without claiming the residual is an executable adjusted return.

For stale endpoints, no missing economic movement can be reconstructed from an unobserved price. Show endpoint age and a separately labelled fresh-endpoint cohort; an actual-to-actual F-to-E subinterval diagnostic must disclose its variable duration and cannot be relabelled as the original h-day outcome. Do not borrow an observation after A+h to repair the primary target. Future reporting-quality groups are ex-post diagnostics, never selection rules.

### Missing future outcomes and paired comparisons

Never select a basket after joining future labels. A basket outcome is unresolved if any positive-weight component lacks the complete supported future path. Do not renormalise surviving weights, silently drop the vault, extend a terminated NAV forever or substitute a payout assumption.

For comparisons of weights on the same basket, require a common supported path mask across the paired arms. For breadth or sorting comparisons, construct the paired union of positive-weight names and report results on origins where that union is resolved. Also report each arm's own support, the change in paired support and unresolved invested weight. Absence of future information is a result.

The primary policy estimand includes equal-weight fallback dates: that is the declared behaviour when risk information is absent, and a zero weighting lift on those dates is a real result. Also show a paired conditional estimand restricted to origins where neither arm uses `risk_fallback_equal`. Report both support sets and never substitute the conditional result for the primary one. Similarly include origins where two requested N values produce the same actual basket in the primary breadth effect, and separately report the subset where feasible breadth changes.

The equal-universe reference often needs more outcomes than a small selected basket. Therefore selection lift is a secondary stricter-support estimand: evaluate it only when the entire predeclared eligible-universe reference is resolved. Do not let this strict denominator suppress the primary same-basket weighting study. If support collapses, show that failure instead of creating a survivor-only universe.

If the strict universe reference has few or no resolved origins, retain it as unsupported and use rank-level conditional outcome profiles for descriptive selection evidence. Do not replace the universe with a hindsight survivor set. Add a missing-outcome contribution analysis: for long-only gross NAV with nonnegative terminal value and no capital calls, unresolved return is bounded below by -100% and has no defensible finite upper bound from this archive. A basket's lower return bound is the resolved weighted contribution minus unresolved invested weight; its upper bound is generally infinite. For a contrast, propagate bounds through the signed active weights; both directions can be unbounded. Report vacuous bounds honestly.

Also report the missing weighted contribution required to reverse the known part of a contrast. Under an explicitly hypothetical common missing return x, `Delta(x)=known_contribution + x*sum(unknown_active_weights)` and the break-even x is defined only when that coefficient is nonzero. This is a scenario, not a bound or an imputation. The largest observed return is not a valid upper bound on an unobserved return. Placing all missing labels lowest/highest is also not generally a sharp bound for Spearman IC; any such display must be labelled a scenario, not an identified interval.

Per-vault IC may use available finite pairs, with target-missingness tables for the full ex-ante population. This is a conditional observed-outcome association and must not be labelled unbiased universe skill.

## 8. Capacity and concentration branch

Keep this branch separate from the unconstrained decomposition. Apply only to the predeclared six-position controls and a small fixed set of p={0,1,2}, L=90 alternatives; do not cross every capacity sensitivity with every estimator.

Use a fresh hypothetical account of $150,000, a 98% investment budget and a 33% account-equity concentration ceiling as source-reference settings. These are inherited assumptions and need sensitivities. Derive each vault's maximum accepted dollars at T from the same source guard, TVL and deposit-capacity rules, using only known state. Preserve archived state when independent clocks are NULL and label the assumption. A missing cap is not zero capacity and not proof of unlimited capacity.

Run two recorded-state policies: source-compatible permissive treatment of unknown permission/capacity, and a conservative known-state-only diagnostic. Show the latter's population and date attrition; it is not automatically more historically accurate. No filling of missing permission/capacity records merely because NAV is filled.

Convert valid capacity to an upper weight c_i. The source-style redistribution diagnostic is bounded proportional allocation `w_i=min(c_i, lambda*u_i)` with lambda chosen so total invested weight is `min(B,sum(c_i))`, B=.98. If unknown capacities prevent a defensible c_i, follow the declared state policy. Implement bounded proportional allocation by fixing any weights exceeding their caps, subtracting their accepted amount from the remaining budget, and renormalising positive desired weights over the remaining unfixed names; repeat until no violations remain. Handle zero budget, zero total capacity and empty baskets directly. Monotonic fixing terminates after at most N saturation steps; verify the budget and caps independently. These are entry caps: subsequent fixed-unit weight drift may exceed them because the snapshot does not rebalance inside h. A no-redistribution diagnostic uses `w_i=min(c_i,B*u_i)` and leaves the residual in cash. These are stateless allocations; exact source alpha-model equivalence requires an independent calculation check and must not be assumed.

Equal-weight comparisons under constraints use bounded equal allocation at the SAME accepted total budget on the SAME basket, so weighting uplift is not explained by different cash. Show deployment changes separately against each arm's unconstrained budget. For constrained attribution use active weights relative to the bounded-equal benchmark, including a cash component where budgets differ. The earlier `N*Cov(w,R)` equal-weight identity must not be applied to a non-equal constrained benchmark without this change. Sensitivities: concentration 20/25/33%, account sizes 0.5x/1x/2x the source account, and observed capacity utilisation curves. Reject impossible constraints explicitly rather than silently relaxing them.

Primary outcomes are gross NAV outcomes. Do not add slippage to NAV deposits/redemptions. Source-modelled redemption charges belong in a clearly labelled optional one-shot sensitivity only, after confirming their formula and avoiding double-counting fees already embedded in NAV. Do not manufacture a turnover-cost estimate from independent snapshots.

## 9. High-impact approaches to run alongside the core study

These are bounded companion studies, not new feature optimisation. Their role is to challenge the assumed mechanism.

### A. Concentration-matched assignment placebo

Within each preselected basket, randomly permute the proposed weight vector over vault identities, preserving its exact cash, concentration and effective position count. Compare the actual assignment's return and path risk with the permutation distribution. Restrict the primary assignment study to N=6, L=90, p=1/2 and the regularised estimator. For N_actual<=6, enumerate all permutations per origin; for other sensitivity baskets use the registered Monte Carlo budget. Return uplift relative to the permutation mean equals uplift relative to equal weight under exhaustive permutation, providing an independent identity check. The permutation percentile is conditional evidence, not an independent predictive sample.

For pooled risk or return placebo distributions across dates, use a coherent mapping: for each draw assign each vault a seeded stable hash priority; sort the basket by that priority and assign the current weight multiset in descending order. Preserve that draw's identity priorities across origins. This retains persistence of random tilts while allowing basket membership to change. Report Monte Carlo uncertainty. Do not regard independent per-date permutations as a null for a temporally persistent policy. The result asks whether the risk-based assignment adds information beyond simply being concentrated.

For the constrained branch, unconstrained permutation can violate capacities. Apply the same bounded allocator to permuted desired weights and report any resulting concentration change; do not claim an exactly concentration-matched placebo there.

### B. Marginal ranks, breadth attribution and a bounded satellite allocation

Show per-origin outcomes by individual rank through rank 20 (twice the maximum requested N), plus cumulative equal-weight top-N outcomes. Compact paired-rank buckets 1–2, 3–4, 5–6, 7–8, 9–10 and 11–20 are display summaries only; publish individual ranks so those boundaries cannot hide a reversal. Retain tie mass, score tier and label availability at every rank. Do not replace an unobserved rank outcome with the next observed name. Bucket-level observed-pair means are labelled conditional; total-basket outcomes still require their complete preselected membership.

Compute consecutive-origin basket Jaccard overlap and total variation of desired weights, including cash, as membership/target-change diagnostics. These are not realised turnover or executable costs. Missing origins must not be compressed into a four-day change. Future rank retention can be an outcome diagnostic, never an input.


For nested top-N sets, decompose the N-to-M horizon return difference exactly into shared-name reweighting plus new-name contribution (and cash, when present). Preserve signed terms and verify they reconcile to total return difference. This directly examines the NB07 mechanism without strategy path feedback.

Alongside normalised widening, retain a six-name core and assign 10% or 20% of the invested budget to ranks 7–10, preserving relative weights within the core and satellite. Both groups use the same estimator, L and p as the reference allocation; they are normalised within their own group before applying the group budgets. If satellites do not exist, return their budget to the core; if their outcomes are unresolved, censor the whole positive-weight basket. These fractions are hypotheses, not optimal allocations; show the allocation curve including zero satellites and ordinary widening.

### C. Clairvoyant risk and assignment diagnostics

At N=6/L=90/p=1 and 2, substitute realised future risk into the weight formula as a deliberately non-causal diagnostic, keeping the basket fixed. It asks whether the weighting mechanism would help even with knowledge of the measured future risk. This is **not a bound on achievable return, Sharpe or minimum-variance performance**: future volatility alone is not future covariance/return knowledge. Zero/undefined future risk gets an explicitly separate unsupported status, not a favourable infinite weight. Display only in an appendix marked “uses future information”; exclude from method rankings and promotion tables.

A true in-sample maximum-return bound, if included, must solve a linear optimisation using realised returns and exactly the same budget/capacity constraints and outcome support. This is optional and non-investable; it does not bound Sharpe or other path metrics. Do not label heuristic inverse-volatility hindsight weights an oracle optimum.

### D. Correlation-aware risk and diversification

On N=6 and L=90 only, compare inverse variance with long-only minimum variance and equal risk contribution using a positive-semidefinite shrunk covariance estimate. Use one documented shrinkage implementation; record fitted shrinkage and sample support. Retain the same selected basket and budget. Do not use naive pairwise covariance with arbitrary missing entries replaced by zero or assume zero estimated covariance proves independence.

For a fixed basket, use the common trailing calendar overlap after every component has a positive NAV and at least two daily returns. Fit `sklearn.covariance.LedoitWolf(assume_centered=False)` with its **scaled-identity shrinkage target** on those filled daily returns, then convert its supported covariance to a correlation matrix and rescale by the same regularised marginal standard deviations used in the diagonal-risk arms. Thus changes in marginal risk and correlations remain identifiable. Record common calendar span, actual observation fractions, fitted shrinkage, zero-variance columns and the shortest history that truncates the overlap.

The primary correlation-support gate requires at least 30 common calendar returns and at least three actual daily updates per component inside that overlap. A 60-return gate is a sensitivity. These are conservative estimation-support choices, not mathematical guarantees; no vault is removed when they fail. If the common overlap fails the gate, use the diagonal regularised covariance and explicitly label `correlation_prior_identity`; it is an independence prior, not measured independence. A constant column has zero off-diagonal correlations and unit diagonal as an explicit unsupported-correlation fallback. If any final marginal variance forecast is unavailable, use the already declared equal-weight allocation fallback; an `empirical_without_prior` forecast that is strictly positive remains supported. No selected young vault is silently removed. Include a supported-common-window cohort diagnostic to reveal how much of the result relies on fallback.

Normalise covariance by its positive mean diagonal before numerical checks/solves and restore units afterwards. Use named defaults `matrix_relative_tolerance=1e-10`, `budget_absolute_tolerance=1e-10`, `solver_optimality_tolerance=1e-9`, `risk_contribution_tolerance=1e-5`, and `solver_max_iterations=10000`. They are numerical tolerances, not economic risk floors; validate tighter/looser tolerances on independent fixtures and record any result changes. Check symmetry, finite values and positive semidefiniteness. The minimum-variance arm solves `min_w w' Sigma w` with nonnegative weights summing to the common budget. The equal-risk-contribution arm can minimise `.5*x' Sigma*x - sum_i b_i*log(x_i)` for x>0, b_i=1/N, then normalise x. If the covariance is only semidefinite, add `1e-10 * mean(diag(Sigma))` to its diagonal and report the amount; do not hide an economic risk floor in solver jitter. Verify risk contribution equality in the unconstrained arm. A failed solve retains a labelled diagonal-risk fallback and an error record, not a deleted origin.

Correlation estimates from asynchronously reported NAVs can mistake reporting alignment for diversification. Compare daily versus seven-day return correlation diagnostics on the supported common cohort before interpreting a covariance-based gain.

Covariance shrinkage is grounded in estimation-error control; it does not establish effectiveness for sparsely reported vault NAVs. [Ledoit and Wolf](https://bse.eu/sites/default/files/working_paper_pdfs/92.pdf).

## 10. Statistical comparisons and falsification

- Primary summaries give each forecast origin equal weight. Per-date IC uses average ranks for ties; require at least three finite non-constant pairs to compute it mathematically and label small cross-sections. Also show results with 5/10/20-pair support gates. No particular gate establishes independence or significance.
- Primary exploratory contrasts, per frozen score, are: (a) raw p=1 versus raw p=2 at L=90/N=6; (b) regularised versus raw at p=2/L=90/N=6; (c) regularised N=10 versus N=6 at p=2/L=90/kappa=30. For each, the two endpoints are mean 30-day return difference and mean daily portfolio-variance difference. Thus the family has 3 contrasts × 3 scores × 2 endpoints = 18 comparisons. N=4/8, p=0 breadth and other horizons are secondary. Report all frozen scores, not only the best. Primary contrasts include declared fallback and candidate-limited dates; conditional active-treatment results are separate.
- Calculate paired differences on identical origins/support. Keep all vaults and arms together in calendar-block resampling. Block duration is at least the target horizon; use max(30,h) days and a twice-as-long sensitivity. Do not bootstrap vault/date rows as independent observations.
- Report origin count, calendar span, paired vault counts, the number of non-overlapping complete target windows and block support. Count actual non-overlapping complete outcome windows from their intervals, and count complete resampling blocks separately over the supported origin calendar; neither is a measured effective sample size. With fewer than ten complete resampling blocks, omit inferential confidence labels and show descriptive estimates/phase ranges. Ten is a frozen conservative reporting gate, not a theorem. This makes all 2026 intervals descriptive under B=max(30,h); do not lower the gate to obtain a favourable interval. Full and pre-2026 periods receive exploratory intervals only when their actual support passes the gate. All periods remain researched history.
- Use 1,999 fixed-seed bootstrap draws for reproducible exploratory 95% intervals where supported; disclose Monte Carlo precision and compare a small set of interval endpoints at a larger draw count if unstable. For supported primary comparisons, use simultaneous max-standardised-deviation bootstrap intervals across the 18-comparison family. Create the full scheduled origin calendar for each period/horizon through its last administratively mature origin, keeping NaNs for unsupported dates. Draw moving calendar blocks of B days with replacement (no wrap across period boundaries), concatenate to the original calendar length, and use the SAME sampled calendar indices for every contrast. Do not compress missing origins. For each comparison j, compute paired mean theta_j and bootstrap means theta*_j,b; take s_j as their bootstrap standard deviation. Let q be the 95th percentile across valid draws of `max_j abs((theta*_j,b - theta_j)/s_j)`. Report `theta_j ± q*s_j`. Zero bootstrap variance is a separately flagged degenerate contrast; never divide by zero. A draw with no paired observations for a family member is unsupported. Use complete valid joint draws only if at least 95% of the requested draws are valid; otherwise withhold the joint interval and report marginal descriptive results. Record the invalid-draw count and the support mask; never silently change the family. The 95% valid-draw gate is a declared numerical reporting tolerance, not evidence of independence. Also report marginal exploratory intervals separately and label their lack of multiplicity adjustment. This finite-sample construction does not confer confirmatory status on researched history. Secondary grids are exploratory and get no winner-significance claims.
- Show all four origin phases as a sensitivity; phases overlap and cannot be combined as four independent experiments. Add horizon-spaced origins with deterministic phase offsets as a dependence diagnostic, never as many independent holdouts.
- Prespecified random seeds are 1010, 2010 and 3010 for separate resampling, assignment and tie-break streams. Seeds identify reproducible draws, not economic parameters. Use 999 coherent assignment/tie draws initially, exhaustive per-origin assignment enumeration for the primary N<=6 subset, and record Monte Carlo error. Double the draw budget only for a numerical precision check, never to seek significance. Tie perturbations are propagated through baskets and allocation results because clipping can put many vaults at the selection boundary.
- A synthetic reporting experiment takes a known dense path, masks observations under fixed daily/two-day/seven-day and empirically sampled gap schedules, then runs each estimator. Measure bias against the known full path. Do not infer latent live risk from the synthetic process alone; use it to check the proposed sparse-data mechanism and estimator implementation.
- A positive-control intentionally future-informed feature may test sensitivity, but an increase after using future data is not evidence that the original pipeline already leaked. Causality is established by invariance of historical inputs to future-data mutation.
- Score IC placebo: permute scores within each date, keeping outcome and eligibility fixed. This tests an exchangeable assignment null, not a proof against omitted variables. Include a quality/age-stratified permutation sensitivity where supported, with strata fixed from pre-origin information.
- Report leave-one-quarter and leave-one-vault influence. This is a descriptive stability check, not a new investable strategy; distinguish holding a ledger fixed from reconstructing a portfolio without a vault.
- For sparse and young cohorts, report continuous coverage/age relationships and quantile groups formed from pre-origin values. Do not infer that a convenient 30-day age or 80% coverage cutoff has economic validity.
- Required causality tests: modifying prices after T cannot change eligibility, priors, ranks, weights or historical risk at T; modifying a target endpoint changes only that outcome and later eligible training rows if calibration is added.

## 11. Register of numbers and assumptions

The implementation must serialise this register. Any new numerical constant needs a name, units, rationale and sensitivity or a statement that it is a numerical tolerance. No local helper may hide a threshold in an expression.

| Choice | Initial value | Why present / required check |
| --- | --- | --- |
| Origin cadence/phase | Four days; anchor 2026-01-01 | Matches prior forecasts; four phases tested, dependence retained. |
| Horizons | 7/30/90 days; primary 30 | Existing operational questions; report support, no horizon selected by profit. |
| Rolling windows | 30/60/90/180 days | Coarse responsiveness range containing source 90; inspect smoothness rather than choosing an isolated maximum. |
| Powers | 0/.5/1/2 | Equal, tempered, inverse volatility, inverse variance; identical rank IC is an invariant. |
| N | 4/6/8/10 | Existing breadth range; actual breadth and shared-name dilution reported. |
| Annualisation | 365; sample ddof=1 | Daily calendar convention; actual horizon returns primary. |
| Source volatility floor | .0001 daily sigma; variance 1e-8 | Inherited economic floor; vary by .1x/1x/10x in sigma. At p=2, its raw weight is 10,000 times that of a 1% daily-sigma vault. |
| Regularisation kappa | L/3; fixed 30 across L; 10/90 at L=90 | Keeps dense-history shrinkage comparable across L; ratio is a heuristic, not estimated certainty. |
| Positive prior | Leave-one-out median eligible variance | Full-window then partial pool; gated arms require 5/10 peers, else use positive empirical variance or labelled equal fallback. |
| Risk calculation minimum | Two calendar returns and two actual dates | Algebraic variance plus some observed change opportunity; tiny samples use strong shrinkage. |
| IC pair minimum | 3; 5/10/20 diagnostics | Computability and support reporting, not significance thresholds. |
| Bootstrap gate/count | 10 complete resampling blocks; 1,999 draws | Frozen reporting gate; 2026 descriptive, longer-block sensitivity, no post-hoc gate lowering. |
| Confidence and multiplicity | 95% intervals; 18-comparison family; at least 95% valid joint bootstrap draws | Conventional uncertainty and numerical reporting choices, not investment or independence thresholds. |
| Account/budget/cap | $150k/.98/.33 | Source reference only; scale/cap/deployment sensitivities separate. |
| Cash return | Zero | Common baseline convention; report cash amount and break-even cash yield where relevant. |
| Ties/unscored tier | Address order; unscored last | Deterministic arbitrary tie resolution; measure tie mass and seeded tie permutations. |
| Satellite budget | 0/10/20% | Mechanism probe; not claimed optimal. |
| Fees | Gross primary | NAV costs embedded; source fee assumptions isolated if used. |
| Inventory/guards | Pinned 514-vault snapshot | Historical survivorship/admission limitation; no hindsight claims. |
| Stale historical NAV | Carry, retain actual age | No blanket stale-age exclusion; age-conditioned results and last-real-mark sensitivity. |
| Terminal future NAV | Censor | No fabricated redemptions or survivor renormalisation; unresolved weight reported. |
| Missing score/risk | Separate masks and declared fallback | No conversion of missing score into finite zero; no risk-based eligibility change. |
| Numerical tolerances | Matrix/budget 1e-10; solver 1e-9; risk contributions 1e-5; 10,000 iterations | Scale-normalised checks; report jitter and solver fallback; verify tolerance stability. |
| Local risk windows | 75/105 days | Adjacent windows from source research, used to check the 90-day neighbourhood only. |
| Correlation support | 30 common returns and 3 actual updates per component; 60-return sensitivity | A declared support heuristic; failure uses an identity-correlation prior, not vault exclusion. |
| QLIKE tail display | Largest 5% absolute weighted row differences | Diagnostic only; never deletes or clips losses. |
| Seeds/draws | 1010/2010/3010; 999 random assignment/tie draws | Reproducibility and Monte Carlo precision; no economic meaning. |
| Rank display | Individual ranks through 20; paired-rank summaries | 20 is twice the maximum N; raw ranks stay available so bins cannot hide behaviour. |
| Terminal loss bound | -100%, upper unbounded | Requires nonnegative share value/no capital calls in the gross-NAV snapshot; no observed-max upper bound. |

Zero hard-coded unexplained constants is the objective; zero modelling choices is impossible. The report must identify which conclusions depend on these choices.

## 12. Notebook output and chart specification

### Heading and bounded narrative

The opening Markdown cell includes the user's goal, the snapshot method, source controls, missing/young-vault policy, period, and the distinction between IC and allocation outcomes. After execution, update key findings from saved results, including unsupported hypotheses. Do not inherit an earlier notebook's verdicts.

Every element follows **subheading → short description → table or separate image**. Explain population, unit, comparison and meaning of a positive value. Each chart title names the period and horizon; each table caption names them. Never merge charts into contact sheets or multi-panel collations. Use the repository static notebook preview server and inspect each main figure separately. Put exhaustive grids in small linked appendix notebooks.

### Main notebook order

| Section | Required output | Interpretation the description must explain |
| --- | --- | --- |
| Design and provenance | Compact configuration table; expandable full assumption register | Frozen choices, raw/source NAV distinction, researched periods and omitted execution mechanics. |
| Population and missingness | Origin/vault counts; actual vs carried marks; young/unscored/prior-only shares; future censoring | Denominators and where each stage loses support. No aggregate coverage percentage without its denominator. |
| Risk prediction | Separate heatmaps for risk IC, paired QLIKE difference and calibration ratio; one 30-day calibration scatter | Higher risk IC is useful ordering; lower QLIKE is better accuracy; coloured missing cells are never zero. |
| Sorting | Score × horizon IC heatmap; score × N selection-lift heatmap; tie/unscored table | Broad ordering versus the selected tail; strict universe-reference support may differ. |
| Weighting | Separate p × L heatmaps for mean weighting lift, realised variance difference and drawdown difference, N=6 | Same basket/budget comparisons; identify source control and uncertainty/support. |
| Trade-offs | One scatter of mean horizon return versus realised risk, points labelled by method; quarter colours in companion per-origin scatter | Descriptive outcomes, no invented compound utility or annualised strategy Sharpe. |
| Breadth | N curve for return lift and a separate N curve for effective count; shared/new-name attribution table | More positions and more independent risk exposure are different quantities. |
| Companion experiments | Assignment-placebo effect plot; satellite curve; covariance-method table | Each addresses a named mechanism with matched comparison and support. |
| Constraints | Desired/accepted weights example, deployment table and cap/account-size heatmaps | Identify cash and clipping effects; gross snapshot economics are conditional. |
| Robustness | Quarter heatmap, continuous age/coverage plot, unresolved-weight table and stability summary | Identify fragility, attrition and concentration; no automatic re-optimisation after seeing a weak cohort. |
| Findings | Compact hypothesis verdict table with effect, interval/status, coverage and next action | Useful/inconclusive/unsupported outcomes; shortlist only for subsequent complete backtests. |

Use diverging colours centred at zero for paired differences, sequential colours for coverage, consistent scales for directly comparable charts, percentages for returns/weights, and explicit units for daily variance. Annotate paired origin count and independent-block status. Grey/hatch missing or unsupported cells with their reason. Show uncertainty on primary contrasts, not tiny illegible text on every large grid.

Each main table should be short enough to read (roughly 10–20 rows is a presentation target, not an analytical filter). Full results stay in labelled appendix tables and ignored Parquet/CSV artefacts. Quiet routine output; compact runner progress, no saved wall of stdout. Parameter labels must distinguish source candles/raw NAV, floor/shrinkage, N requested/actual and score missingness.

## 13. Delivery scope and implementation contracts

### Mandatory first implementation and separately labelled extensions

The mandatory notebook contains: causal/missingness audits; source/raw/regularised risk comparison; stages R/W/N; marginal ranks and exact breadth attribution; first-update/endpoint-age diagnostics; same-basket assignment placebo; source-reference capacity/deployment comparison; paired inference/support; and all frozen primary contrasts. This directly answers S/R/W/N and the basic C/Q questions.

Keep the following as bounded appendices or later independent work packages: covariance-aware construction, irregular-interval and weekly risk comparisons, satellite allocations, account/cap sensitivity surfaces and the clairvoyant-risk diagnostic. They are the proposed high-impact parallel approaches; their addition must not delay or alter the core estimands. Chronologically fitted calibration, category-specific priors, full execution costs and a true realised-return LP bound are explicitly deferred. No implementer may silently substitute a deferred method for the frozen primary one.



Implement reusable modules beside the notebook. Generated data, figures, manifests, logs and raw review output go under ignored `_artifacts-restored-2026-10-07/10`; written findings and this plan stay outside generated directories.

Proposed files:

- `portfolio_snapshot_data.py`: pinned readers, clocks, calendar/provenance and outcome paths.
- `portfolio_snapshot_risk.py`: risk estimates, priors, forecast losses and covariance alternatives.
- `portfolio_snapshot_construction.py`: frozen sorting adapter, weights, constraints, fixed-unit paths and exact decompositions.
- `portfolio_snapshot_statistics.py`: paired comparisons, calendar resampling, support and placebos.
- `portfolio_snapshot_report.py`: styled tables and individual charts.
- `create_portfolio_snapshot_notebook.py`: reproducible notebook builder.
- `10-portfolio-snapshot-findings.md`: generated/reviewed conclusions after execution.

Data contracts, using naive UTC timestamps and stable pair IDs:

| Dataset | Primary key / required fields |
| --- | --- |
| `origins` | origin_at; feature_cutoff; period flags; phase |
| `nav_daily` | pair_id/date; raw_nav; filled_nav; actual flag; actual timestamp; age; source_nav |
| `candidates` | origin_at/pair_id; eligible flags/reasons; score per method; score missing/imputed/tie fields; age/quality; capacity provenance |
| `risk` | origin_at/pair_id/estimator/L/kappa; calendar span; actual counts; empirical/prior/final variance; prior support; fallback/reason |
| `allocations` | origin_at/policy_id/pair_id; rank tier; desired/accepted weight; cash; units; capacity; estimator status |
| `outcomes` | origin_at/policy_id/h; label end/availability; resolved flag; unresolved weight; return/path metrics; no daily portfolio state shared across origins |
| `contrasts` | origin_at/comparison_id/h; paired support; effects; reconciliation residual |
| `summaries` | period/comparison_id/h; estimand; mean/median; uncertainty status; support; dependence diagnostics |

Build unique IDs from all policy fields and code/data fingerprints. Preserve unresolved rows. Assert keys and merge cardinalities; a missing join must not quietly turn a weight into zero.

Prefer one implementation agent and one independent audit agent after the data contract is agreed. If parallelising the bounded companions, use at most three agents with exclusive file ownership: data/risk, construction, and statistics/report. The coordinator integrates the notebook, reviews joins and runs the single main notebook. Independent expected values belong to the auditor, not the author of the calculation being checked. Do not run three independent full universes or kernels. Subagents may not introduce scoring features, fees, clipping, thresholds or extra exclusions without updating the registry and coordinator review.

### Meaningful verification before interpreting results

- Sparse fixture equals an independently filled calendar; leading gaps stay missing; young paths use only their available elapsed history; actual counts do not increase on carry days.
- Missing score differs from finite zero; an unscored vault can fill a vacant slot; risk fallback does not remove it.
- Weights sum to the declared budget; p=0 equals equal weights; p>0 rank order is invariant on positive common risk inputs; risk-scale multiplication leaves unconstrained normalised weights unchanged.
- Fixed-unit path agrees with hand calculations and differs from constant-weight daily rebalancing when prices diverge.
- Selection/weighting, covariance/dot-product, and breadth/cash decompositions reconcile to numerical tolerance.
- QLIKE accepts zero realised variance, rejects unsupported forecast variance, uses same-row comparisons, and has no percentage-change display.
- Capacity projection respects every bound, records unallocated cash, preserves unknown-state reasons and has a same-budget equal benchmark.
- Terminally unsupported assets censor baskets; no future prices influence selection or priors; no survivor renormalisation.
- Independent spot checks reproduce source risk weights and post-fix NB08 raw endpoint labels. Differences from source portfolio returns are expected because no execution state is simulated.
- A full separate checker recomputes a small stratified set of snapshot paths from original archive rows, including young, sparse, zero-risk, tiny-NAV and missing-terminal cases.

Use `poetry run python` for scripts. Execute the implemented notebook through `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`, saving in place, and validate saved outputs. Current task creates/reviews the plan only; experiment execution follows a separate implementation request.

## 14. Completion and promotion criteria

The study is complete when every predeclared arm has either a supported result or an explicit reason, all primary paired contrasts and sparse/young-vault audits are present, independent identities pass, charts render separately with correct periods, and findings explain hypothesis verdicts and assumptions.

A construction rule advances only if its effect is economically interpretable, stable across nearby choices and not explained entirely by one vault, reporting sparsity, missing outcomes or changed cash. Do not require an arbitrary minimum CAGR uplift from this study. Report the return/risk Pareto trade-off and uncertainty; source controls and equal weights must remain visible. Freeze any shortlist before later strategy backtests or prospective observations.

## 15. Findings from the first Claude co-design review

Claude CLI returned a successful response with `modelUsage` identifying **`claude-fable-5-1`**. Its high-value recommendations are incorporated: staged estimands; selected-basket risk calibration; marginal-rank profiles; exact weighting covariance attribution; assignment placebos; snapshot membership stability; explicit capacity treatments; and a separately labelled future-risk diagnostic.

Several suggestions required correction before implementation:

- **Reject a universal sparse-volatility correction.** The review asserted a square-root-of-gap deflation factor. Catch-up jumps and the return process invalidate that blanket rule. Keep causal filling, observed-interval diagnostics and synthetic missingness checks.
- **Do not assume terminal payout.** A last NAV or “closed” flag does not verify redeemable proceeds. Actual documented cash flows can support a separate outcome reconstruction; otherwise retain terminal censoring. Never renormalise survivors.
- **Do not impose actual-anchor-only eligibility as the main rule.** That would reverse the user's sparse/young-vault requirement. Actual-anchor and dense-observation cohorts are labelled sensitivities.
- **Do not modify frozen Sortino scores with a new downside floor.** Preserve each recipe's existing convention and distinguish missing/tied scores.
- **Do not identify a log calibration slope with optimal shrinkage.** It is a diagnostic; a fitted risk model needs chronological training and a declared objective.
- **Do not call future-volatility weights a performance ceiling.** They are a non-causal mechanism diagnostic only.
- **Do not demand snapshot returns equal a stateful source backtest.** Reconcile input scores, risk estimates, endpoint conventions and requested weights where comparable; portfolio returns differ because the mechanisms differ.
- **Do not call an improvement from intentionally leaked features proof of existing leakage.** Use future-mutation invariance tests on the causal pipeline.
- **Do not assume an inverse-volatility return/sigma regression slope threshold of one determines benefit.** Without a specified scaling model, its units make that threshold meaningless. Use the exact active-weight/return covariance identity.

The raw review is retained under the ignored `10-plan-review` namespace. These dispositions are part of the implementation contract; reviewers' unaccepted suggestions must not be implemented from the raw transcript.

## 16. Final Claude review and disposition

Two successful CLI reviews used the explicitly requested **`claude-fable-5-1`**, confirmed in each response's `modelUsage`; no model fallback was used. The second review considered the full draft and the first-review corrections. Raw requests/responses are retained under ignored `_artifacts-restored-2026-10-07/10-plan-review`, with readable response text there. The table below is the durable review record.

| Review point | Disposition in the final plan |
| --- | --- |
| The block gate suppresses 2026 intervals | Accepted. State that 2026 is descriptive by construction. Full/pre-2026 intervals remain exploratory, not “confirmatory”. Derive support counts from actual scheduled intervals. |
| Stale anchors/endpoints can affect apparent weighting lift | Accepted with correction. Add exact first-update attribution and age diagnostics; neither the first jump nor its exclusion identifies the true pre-origin economic return. |
| Fixed kappa confounds lookback and shrinkage strength | Accepted. Primary kappa=L/3; fixed-kappa and strength sensitivities retain the modelling uncertainty. Raw rolling arms provide the cleaner window comparison. |
| Full-universe outcome support may collapse | Accepted. Keep strict selection lift secondary and visibly unsupported when necessary; add rank profiles, unresolved mass, valid possibly-vacuous bounds and break-even scenarios. |
| Bound missing returns by the observed maximum; rank missing labels all-high/all-low as IC bounds | Rejected. Unobserved upside is not capped by the observed maximum, and those rank placements are not generally extrema. Any such exercise is a scenario, not a bound. |
| Remove fallback-equal dates and identical-actual-N dates from the primary comparison | Rejected as a primary rule. The policy genuinely does nothing on these dates. Preserve the overall policy effect and additionally report the explicitly conditional active-treatment effect. |
| Unspecified prior gate, covariance support and shrinkage target | Accepted. Specify leave-one-out prior, gate actions, empirical/equal fallback, common-overlap gate, scaled-identity Ledoit–Wolf target, solver tolerances and identity-correlation prior. |
| Undefined simultaneous interval method and breadth contrast | Accepted. Freeze the 18-comparison family, exact reference weights, shared calendar resampling and max-standardised-deviation interval algorithm. |
| QLIKE dominated by a few extreme floor errors | Accepted. Keep the primary mean and show median, win fraction and absolute-tail concentration without clipping. |
| Add basket-level variance calibration | Accepted as a cheap core diagnostic; disclose weight drift between entry forecast and fixed-unit realised risk. |
| Rank-only risk remapping to peer quantiles | Deferred. Mapping into the same empirical distribution can be a no-op and a genuinely different mapping needs a fixed reference distribution and separate hypothesis. The exponent family and assignment placebo already isolate useful parts of this question. |
| Reduce parallel implementation risk | Accepted. Prefer one implementer plus one independent auditor; bounded companion modules may run separately after the core contract is stable. |

The review identifies modelling choices; it does not certify empirical success or execution parity. The final plan keeps causal filling and young-vault inclusion, documents unresolved economic timing, and does not import unaccepted reviewer suggestions into the implementation.
