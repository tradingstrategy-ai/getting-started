# Experiment 11 — risk estimation, position sizing and allocation constraints

Status: **implemented and executed**, co-designed and reviewed through three Claude CLI calls using **`claude-fable-5-1`**. The formal review’s corrections are incorporated; the final focused verdict was **ready**, with no material implementation blocker. The 18-policy smoke and 40-policy main study are complete at all declared horizons; the sensitivity/cap-aware batches were subsequently executed in [NB12](12-research-allocation-followup.ipynb), with a full engine shortlist. Their findings are documented separately; NB11 remains the original 40-policy generation. See [findings](11-weighting-sizing-findings.md). Notebook: `11-research-weighting-sizing.ipynb`. Preserve both generations of NB10. Read [NB10 interpretation](summary.md#interpretation--obvious-and-less-obvious-outcomes), [expanded findings](10-expanded-score-allocation-smoke-findings.md) and [original findings](10-portfolio-snapshot-findings.md).

## 1. Goal and research boundary

Improve weighting and sizing while keeping the selected vaults fixed. Determine whether inverse-variance performance comes from the risk horizon, strength of the allocation preference, shrinkage towards a peer prior, score transformation or subsequent entry constraints. Seek a region of sensible settings rather than one best historical cell. The current source sizing window is **90 days**; the 45-day input in the focal return selector must not be mistaken for the source risk window.

A 98% budget and a 33% per-vault cap require at least three positive holdings when fully invested; they do **not** require three names to be at their caps. Equal allocation across six names is about 16.33% each before additional pool limits. Measure cap activity instead of assuming it.

The notebook heading must reproduce this goal, its fixed-selection method, the complete 2026 evaluation calendar, retained 2025 warmup, stage scope, results and limitations. The user wants a small formal allocation experiment before committing to another strategy backtest. These are independent fixed-unit portfolio snapshots, not an executable strategy or a forecasting model fitted to returns.

Keep the existing six-vault `focal_four` and `v11` selectors. Their recipes, missing-score tiers, eligibility, source-state semantics and address tie-breaking are frozen. They are two related robustness contexts, not independent replications. Do not select using new risk scores, change N, invent return forecasts or search admission thresholds in NB11.

## 2. Evidence that motivates the design

All figures below are mean independent 30-day returns on 62 mature 2026 origins, except where stated otherwise.

| NB10 observation | Implication for NB11 |
| --- | --- |
| Focal equal weights 1.716%; focal-score sizing 1.648% | Selection scores need not be proportional capital forecasts; retain equal allocation. |
| Original focal regularised inverse variance 2.512%, versus bounded inverse-risk score 2.377% | The original method is the main benchmark. A new transformation has not yet improved it. |
| Arithmetic return/risk score 1.813%; geometric 2.148% | Score magnitudes and concentration matter; comparison by IC alone is insufficient. |
| Risk in ranking loses 1.112 percentage points | Freeze the selected identities during sizing comparisons. |
| v11 four-metric minimum returns 2.390%; bounded V180 determines its score in 79% of selected rows | Run its single-component control before attributing the result to four inputs. |
| Risk sizing helps most in Q3; source outcomes depend on particular vaults | Show quarter, vault and tail attribution; all dates remain included. |
| Available-component missingness selects many vaults lacking the focal score and raises cash | Do not change ranking missingness while testing risk estimates. Support diagnostics remain necessary. |
| Entry caps distort score risk-budget targets | A separately specified constrained-allocation study may be worthwhile; prove it differs from existing redistribution. |

The NB10 figures are reference checks, not targets to tune towards. Use unrounded saved ledgers for reconciliation.

## 3. Calendar, inputs and missing data

### Evaluation calendar

- Define `START=pd.Timestamp("2026-01-01")` and `END=pd.Timestamp("2026-10-05")`; END is the exclusive evaluation/maturity boundary, not the final scheduled origin.
- Naive UTC decision origins: `2026-01-01 <= T < 2026-10-05`, every four days anchored on 1 January. This is all available 2026 history, not a complete calendar year.
- Exactly **70** origins, including late dates whose targets have not matured. Keep pending rows in allocation and support tables.
- Features end at anchor `A = T - 1 day`. The inherited snapshot buys fixed units at NAV dated **A**, with units `initial_capital*accepted_weight/NAV(A)`, and values them at **NAV(A+h)**. Cash has zero return. This same-anchor research convention is not an executable claim that a decision made at T can fill at yesterday’s NAV. Preserve it for NB10 parity; a later engine replay must use its actual decision/fill timing. The last archived NAV date is 4 October, so `A+h <= 2026-10-04` is equivalent to administrative maturity `T+h <= 2026-10-05`.
- Expected administrative maturity: 7 days **68 mature / 2 pending**; 30 days **62 / 8**; 90 days **47 / 23**. These counts precede vault-specific terminal support checks.
- Use 30 days as the primary economic horizon. Seven and 90 days are secondary consistency views. Allocations must be identical across future horizons.
- Retain all available 2025 warmup and earlier recorded NAV, eligibility inputs and source state. Do not truncate a series at 1 January 2025; long score features can need earlier history.
- The smoke run uses every origin and the 30-day horizon. Reduce combinations, never the calendar, to make the first run smaller.

### Input provenance and historical limitations

Pin archive and metadata hashes, NB08 recipe hashes, NB09 feature hashes, original NB10 references and the expanded NB10 generation. Record relevant framework commits, configuration, code hashes and canonical policy identities. Verify inputs before using saved controls. Do not rewrite earlier outputs to make them agree with new definitions.

Use the existing repaired archive for comparability. Current inventory/guard restrictions and unverified archive publication clocks remain limitations. If input fingerprints have changed, expose the change and rerun the exact reference controls under the new fingerprint before comparisons; retain the old generation as historical evidence.

### Sparse and young vaults

1. Causally forward-fill NAV only after the first valid positive observation. Do not backfill leading gaps. Record the original observed mask separately.
2. Carrying a price over a calendar day does not create an independent observation. Retain elapsed returns `n`, actual update count `m`, anchor age, endpoint age, update fraction, first/last observations and longest internal gap.
3. Young vaults may remain in the fixed basket. A missing long lookback invokes the declared risk-estimation fallback; it must not alter selection or remove their rows.
4. Keep empirical zero variance distinct from missing empirical variance, regularised risk, peer-only risk and numerical flooring. A quiet filled path is not established evidence of low economic risk.
5. NAV filling must not fill permission, leader-share, deposit-cap or other state fields. Unknown independent observation clocks retain archived values under existing reader semantics; genuinely absent fields stay unknown.
6. Future targets cannot be fabricated after the vault's last actual positive mark. Preserve unresolved invested weight, known return contribution and inherited signed missing-return bounds. Do not renormalise surviving vaults or select based on future availability.
7. Reuse NB10's all-basket equal fallback when a required positive risk estimate is unavailable; label the exact cause and count how often it makes nominally distinct methods identical. This compatibility fallback is an assumption, not an assertion that equal is optimal.

## 4. Risk estimates and sizing formulas

For vault i at T and requested lookback L, use daily simple returns from the available causally filled path ending at A. Reuse `empirical_window`: ddof=1, at least two elapsed returns and one actual update after the first finite window price to define empirical variance `s²`. Retain partial-window status rather than pretending all L days exist.

Let `mu_i` be NB10's positive leave-one-out median empirical variance among eligible peers with complete elapsed windows, falling back to the partial-window pool if needed. Build this on the full eligible universe before basket selection. Retain peer count, pool, dispersion and whether the support gate is weak. Flat peers are currently excluded; this inherited choice must be visible. The inherited **gate=1 means at least one other eligible peer with finite positive empirical variance** in the preferred full-window pool, otherwise at least one in the fallback partial pool. It does not impose a minimum complete-window fraction. Reference: `portfolio_snapshot_risk.peer_prior`; separately flag counts below five as weak support without changing the calculation.

The regularised estimate is:

`v_i = c_i * s²_i + (1 - c_i) * mu_i`, with `c_i = m_i / (m_i + kappa)`.

Missing empirical risk receives zero empirical weight if a valid prior exists. Preserve NB10 fallback semantics when no prior exists. **Core comparisons hold kappa at 30 actual updates across lookbacks.** This reproduces the existing 90-day baseline but avoids changing the shrinkage parameter mechanically with L. Different L still changes empirical information, actual update count and peer composition; report these rather than calling the contrast a pure time-decay effect.

Add explicit `kappa=L/3` companions at L=45 and 180. These preserve the inherited convention and measure the difference from fixed kappa. Do not silently change the original controls.

Requested inverse-risk allocations are `u_i ∝ v_i^(-p/2)`. Thus p=1 is inverse volatility and p=2 is inverse variance. Compute in log space. Equal weights are one distinct policy, not nine duplicated p=0 cells.

Other named methods:

- **Raw90/p2:** empirical risk if available, otherwise peer prior, then NB10 variance floor `1e-8`. Regularised estimates do not receive that floor in the inherited code. A raw-versus-regularised difference includes this asymmetry; do not attribute the entire effect to shrinkage.
- **Source90:** exact original source-candle estimator, floor, availability and fallback. It is a compatibility control with a different observation convention, not another independent replication.
- **Bounded I90:** use regularised L90 with **kappa30**, exactly as in the NB10 reference, and `I_i = mu_i / (v_i + mu_i)`, followed by one normalisation over the selected basket. It changes both the marginal preference curve and the use of a vault-specific peer scale; it is not merely clipped direct inverse variance.
- **Bounded V180:** `V_i = sqrt(mu_i) / (sqrt(v_i) + sqrt(mu_i))`, using inherited kappa=60 to exactly match the component in T18.
- **T18 minimum:** frozen `Min(Sh90, Ca180, V180, Kmax)` using NB10 transforms and missing-zero semantics. v11 selection only. No recalibration of its component scales from future outcomes.

After requested weights, apply the same `bounded_proportional` redistribution, source-report-only capacities, 98% maximum budget, 33% concentration limit and a maximum deposit equal to 33% of each vault’s own TVL, for a $150,000 account. In this dataset the pool limit is a **per-vault capacity**, not a shared multi-vault group limit: `cap_i=min(0.33,0.33*TVL_i/150000)` when TVL is known, with explicit inherited missing-TVL behaviour: take the latest finite TVL candle at or before A within the two-day source carry; when no such TVL is available under `source_report_only`, retain the concentration cap of 0.33 and flag unknown state. Archived hard deposit limits remain reported rather than imposed as partial sizing caps in this source-compatible branch. If a future input introduces shared pool groups, the present projection and optimiser specifications are invalid for that input until explicit linear group constraints and a common feasibility calculation are added. Preserve positive-request support: a zero requested position does not silently receive redistributed capital. Report all-zero fallbacks.

## 5. Registered combination matrix and execution stages

Canonical IDs include selector, estimator, L, p, kappa rule, transform, missing/fallback policy, projection, budget and capacity assumptions. Both selectors use N=6. Aliases are deduplicated before execution and recorded in a manifest.

### Smoke matrix — full 2026 history, 2025 warmup, 30-day outcomes

This first run covers 18 policies and 1,260 origin/policy allocations. It is a mechanical checkpoint, not an economic screening stage.

| IDs | Selector | Risk and sizing | Purpose |
| --- | --- | --- | --- |
| S01–S02 | Focal / v11 | Equal requested weights | Establish each fixed basket and capacity benchmark |
| S03–S04 | Focal / v11 | Regularised L90, kappa30, p2 | Reproduce the strongest original benchmark |
| S05–S06 | Focal / v11 | Regularised L45, kappa30, p1 | Short lookback and gentler risk preference |
| S07–S08 | Focal / v11 | Regularised L180, kappa30, p1.5 | Longer lookback and intermediate exponent |
| S09–S10 | Focal / v11 | Raw L90, p2 | Floor, sparsity and regularisation control |
| S11–S12 | Focal / v11 | Bounded I90 | Risk-score magnitude transformation |
| S13–S14 | Focal / v11 | Exact Source90 | Source-data convention and reference parity |
| S15 | v11 | Bounded V180, inherited kappa60 | Single-component explanation of T18 |
| S16 | v11 | Exact T18 minimum | Reproduce the four-metric result |
| S17 | Focal | Matched-span calendar log-return variance, kappa30, p2 | Matched sparse-estimator control |
| S18 | Focal | Gap-scaled log-increment variance, kappa30, p2 | Exercise actual-mark intervals and prior fallback |

### Main NB11 matrix

After the smoke passes correctness, support reconciliation and rendering checks, proceed automatically to this predeclared scope in the same implementation task. Do not advance or stop based on profitability. Do not ask for another approval for this already specified step.

| Family | Settings | Unique policies |
| --- | --- | ---: |
| Main surface | Two selectors × L={45,90,180} × p={1,1.5,2}, regularised kappa30 | 18 |
| Equal | Two selectors | 2 |
| Raw90/p2 | Two selectors | 2 |
| Bounded I90 | Two selectors | 2 |
| Exact Source90 | Two selectors | 2 |
| T18 explanation | v11 bounded V180 and exact T18 minimum | 2 |
| Inherited shrinkage companions | Two selectors × L={45,180}, p2, kappa=L/3 | 4 |
| Multi-window alternatives | Two selectors × median/max of regularised L45/L90/L180 variances, kappa30, p2 | 4 |
| Sparse-estimator pair | Two selectors × matched-span calendar-log / gap-scaled log-increment variance, L90/kappa30/p2 | 4 |
| **Total** | Includes the 18 smoke policies; reuse their allocations | **40** |

All 40 policies run at all 70 origins: **2,800 allocations**, evaluated at 7/30/90 days for **8,400 scheduled target rows**. The 90-day target does not change the 90-day risk estimate or determine which vaults receive weights. Keep runtime, memory and realised row counts in the notebook.

The multi-window alternatives use the median or maximum of the three positive variance forecasts for each vault, then inverse-variance sizing. Require all three inputs; partial-window or prior-only positive regularised estimates count as available. Only an undefined/non-positive final risk forecast counts as unavailable. If one is truly unavailable, use the same whole-basket equal fallback and flag it. They aggregate variance forecasts, not already normalised portfolio allocations. Median tests stability without choosing one historical window; maximum tests conservative treatment of disagreement. They are exploratory alternatives, not independent estimates or an oracle for the worst future risk.

### Sparse-mark estimator pair contributed by Claude

This pair tests an alternative observation model, not an assumed correction. Forward-filled zeros followed by catch-up returns do not automatically bias daily variance downwards: the catch-up move can offset the zero days. Actual NAV smoothing, reporting frequency and stale endpoints can still make reported risk a poor economic measure. State these as hypotheses.

At each T use actual positive daily marks with timestamps in `[A-90 days, A]`. Take consecutive complete intervals within that range; never allocate a price move across the left boundary or invent a final update at A. For interval j define elapsed calendar days `d_j>0` and log change `x_j=log(P_j/P_(j-1))`. Require at least two complete intervals (three marks) for either empirical estimator. Use identical interval endpoints, eligible peer sets and actual interval count m for this matched pair. **The shrinkage formula for both members uses m=number of complete actual-mark intervals (retained marks minus one)**. NB10’s different actual-update count is stored for comparison and must not enter this pair’s shrinkage weight. Thus kappa30 here means 30 complete intervals; it is not numerically identical prior strength to 30 NB10 updates. Repeat this distinction in the findings.

- **Calendar-log control:** causally fill the daily path from the first retained actual mark through the last retained actual mark, calculate daily log returns and their sample variance (ddof=1).
- **Gap-scaled estimator:** estimate daily drift `a=sum(x_j)/sum(d_j)` and variance `s²_gap = sum((x_j-a*d_j)^2/d_j)/(m-1)`. This is a model of variance proportional to elapsed time; record the assumption. It is not the uncentred variance of `x_j/sqrt(d_j)`, which would handle drift inconsistently.
- At one-day spacing the two empirical variances must agree. Both use the same required empirical support; missing empirical risk uses a prior and remains in the basket.
- To isolate the empirical estimator, both members of the pair use the **same peer prior from matched-span calendar-log estimates**, with the same leave-one-out eligible peer identities, full/partial-window convention and kappa30. Record that this anchors the alternative to the calendar estimator; an estimator-specific-prior companion is later work. A full window here requires actual marks at both requested endpoints. If no positive full-window peer supports the prior, use the same partial pool fallback for both. Report per-origin counts and fractions of eligible vaults qualifying for the strict full-window pool versus the original filled-window pool, the positive-prior pool sizes and partial-fallback rates. Pool differences relative to the original estimator are part of the joint convention change, not evidence of an empirical-estimator advantage.
- Where empirical support is inadequate, set its shrinkage weight to zero. Track interval counts separately from NB10's original actual-update count. With no usable prior, retain the registered whole-basket equal fallback for both policies.
- Comparing these two methods isolates the estimator under their common support and prior. Comparing either to original daily-simple-return L90 also changes log/simple returns, endpoint span and support rules: explicitly label that a joint convention change.

Retain the number of intervals, covered days, maximum interval length and last-mark age. Sparse-mark estimates are not ground truth. Evaluate their forecast calibration and portfolio effects against the same fixed-unit outcome definitions, with reporting-quality diagnostics alongside them.

Earlier arithmetic/geometric score treatments and T24 may be displayed as labelled NB10 references only when fingerprints, origin support and capacities match. They are not extra newly executed NB11 policies and must not be used to hide the total number of previously searched methods.

## 6. Primary contrasts and interpretation

Freeze these contrasts before the first outcome is joined. For each selector, use exact shared origins and supported targets; all scheduled and unsupported counts remain visible.

1. Eight non-baseline cells of the 3×3 surface minus L90/p2/kappa30: **16 primary comparisons** across the two selectors at 30 days.
2. v11 T18 minimum minus bounded V180: **one primary comparison** testing whether the additional inputs improve the composite.
3. The remaining contrasts are secondary mechanism diagnostics: equal, source, raw, bounded I, proportional-kappa companions, median/max forecasts, the sparse-estimator pair and secondary horizons. List every one and its role before calculating results. No retroactive reassignment of a successful secondary comparison to the primary family.

Return differences, variance differences/ratios and drawdown differences are separate outcomes. Do not create an arbitrary CAGR/Sharpe blend or optimise a scalar risk-aversion coefficient. Selection stays fixed; no new ranking IC is needed to tell whether sizing helps. Optional risk-rank IC, calibration and QLIKE diagnose the risk estimator, not the dollar allocation.

For each contrast report mean/median return difference, paired support, win/tie/loss counts, realised variance, mean within-window maximum drawdown, worst-origin loss, median outcome and the same-budget equal benchmark. Use daily portfolio returns from fixed units, never the mean of vault Sharpes. Do not multiply overlapping snapshot returns into a curve or annualise their mean as strategy CAGR.

The main constraints are identical for positive-weight methods, so equal accepted budgets should usually follow automatically. Assert this. For zero-score/zero-cap and fallback cases, show actual deployment and a separately projected common ex-ante budget. Calculate the common budget before looking at targets. Log infeasibility or loss of target support; do not solve it by renormalising surviving future labels.

## 7. Robustness, sparsity and attribution

### Predeclared calendar-block support

Reuse `portfolio_snapshot_statistics.support_counts` exactly: create a daily origin calendar from START through END−h inclusive; partition consecutive complete h-calendar-day bins anchored at START; a complete bin must contain scheduled four-day origins and have finite paired effects for every scheduled origin in that bin. Empty/partial bins and bins with missing effects do not count. Do not compress the calendar or replace h days with h origin rows. For any moving-block resampling, h-calendar-day blocks carry the same scheduled/missing masks and are shared across policies and selectors. Horizon-length blocks address overlap but do not prove all longer temporal dependence is absent.

| Horizon | Maximum complete calendar bins before missing support | Ten-block gate | Reporting consequence |
| --- | ---: | --- | --- |
| 7 days | 38 | May pass; recompute per paired comparison | Secondary descriptive intervals only if supported |
| 30 days | 8 | Fails even with complete observations | All primary economic effects remain descriptive; no primary interval/p-value or promotion claim |
| 90 days | 2 | Fails even with complete observations | Descriptive outcomes and support only |

The maximum is `floor(len(date_range(START,END-h,freq='D'))/h)`. Per-contrast missing data can only reduce it. Do not shorten blocks or promote seven-day results to obtain an inferential claim.

### Required diagnostics

- Retain the complete scheduled calendar for horizon-aware block calculations. Use the inherited ten-complete-block reporting gate; do not treat two selectors, three horizons or overlapping phases as extra independent observations. 2026 remains retrospective regardless of whether a short-horizon interval can be computed.
- For any intervals meeting support requirements, preserve the frozen 17-comparison primary family and shared calendar resampling. Use NB10 seeds and 1,999 draws. The predeclared joint reporting family is 17 contrasts × three per-origin differences (return, variance and within-window drawdown), giving 51 jointly studentised statistics with a shared maximum-absolute-t band. Variance ratios are descriptive companion estimates. Preserve all scheduled dates, missing-pair masks and shared calendar blocks across both selectors; expose invalid/degenerate draws and follow the inherited joint-validity gate. All intervals remain retrospective research summaries, not independent confirmation. Secondary-horizon intervals do not receive a primary or confirmatory label. If implementation cannot support the declared family, show descriptive estimates and the reason rather than narrower unsupported intervals.
- Require risk-forecast calibration on unique selector/vault/origin/estimator rows, deduplicated across p and sizing transforms. Evaluate simple-return variance forecasts against future simple-return variance, and log-return forecasts against future log-return variance; do not mix units. On common finite support report per-origin mean QLIKE difference versus the same estimator’s peer prior, then average origins equally; also report realised/predicted mean-variance ratio, median forecast loss, floor/prior fractions and peer support. Future variance may legitimately be zero. Use the same maturity and terminal-support rules as portfolio targets. Show separate actual-update/age/support calibration views with explicit counts and equal origin weighting. These describe reported-NAV risk prediction, not true economic risk or a fitted return forecast. No pooled regression p-values or unlabelled billions of pseudo-independent rows.
- For every main allocation save a cap-free **shadow at the same accepted budget**: `shadow=B*u/sum(u)`, using the method’s actual requested/fallback weights and B from its capped allocation. Report L1 distortion, maximum-weight change and effective-N change before examining outcomes. These are derived allocation diagnostics, not extra return-evaluated policies or a second economic search.
- Show all parameter cells. A locally consistent region means adjacent registered L/p cells have similar paired return/risk trade-offs; display their numeric changes rather than imposing an unexamined tolerance or declaring a count of positive cells a p-value.
- Group results by origin quarter. Q3/late-period maturity varies by horizon; print mature and resolved counts. Q4 pending cells are unavailable, not zero profit. Quarter cash/exposure summaries must use the same mature/resolved calendar as their associated return summary, or explicitly be labelled all-scheduled diagnostics.
- Attribute fixed-basket return differences to vaults and dates, including first-update versus remaining return. Report both contribution to the overall mean and conditional contribution when held. Removing a quarter or a vault is an influence diagnostic, not a newly selected portfolio or proof of generalisation.
- Show continuous plots of weight and marginal risk versus actual update count, update fraction, elapsed age, anchor age, longest gap and floor/prior status. Any bins must have explicit boundaries and counts; never choose boundaries to maximise economic differences.
- Quantify how often caps make two requested methods identical after acceptance, requested/accepted effective N, maximum weight, top-vault contribution and all-zero/equal fallbacks. Variance reduction caused by cash must be distinguished from diversification.
- Report selector overlap continuously (Jaccard and shared accepted weight). No arbitrary overlap threshold makes the selectors independent. A descriptive early/late stability display may use complete calendar quarters, but it is not fresh validation and cannot choose the retained methods.
- Flat, partial and prior-only fixtures are mandatory even if historical eligibility means a code path is inactive. Missing support stays visible, not inferred to be safe because an aggregate run completed.

## 8. Follow-up sensitivity registry

These are defined follow-up batches, not part of the default 40-policy NB11 run. Materialise their exact registry and counts without executing them automatically. This keeps the next notebook focused while making subsequent work reproducible.

| Batch | Methods | Additional policies |
| --- | --- | ---: |
| S1: local stability | Two selectors × L={75,105}, p2, kappa30 | 4 |
| S2: prior strength | Two selectors × L90, p2, kappa={10,90}; kappa30 already exists | 4 |
| S3: raw floor | Two selectors × raw L90/p2, variance floor={1e-10,1e-6}; 1e-8 already exists | 4 |

These 12 policies address nearby windows, the arbitrary 30-update prior strength and the floor asymmetry. Full versus pre-2026 outcomes, additional origin phases and entry account-size/concentration surfaces are separately registered later; they must not silently enlarge the main matrix. Earlier dates are already researched, so they are robustness context rather than a fresh holdout.

## 9. Follow-up: constraints-aware risk allocation

This is a separately reviewed eight-policy allocation batch, not an automatic extension of the main matrix. It addresses a different hypothesis: accounting for caps inside an allocation objective may improve accepted risk distribution and economic outcomes. Existing proportional water-filling already solves some distance/KL projection objectives; implementing an equivalent optimiser would add no new treatment.

### Paired design and objective

Two selectors × two risk-budget targets (equal risk contribution, or budget proportional to that selector's frozen score) × two allocation methods (unconstrained risk-budget solve followed by water-filling, or constrained convex solve) = eight policies. Retain N=6, 90-day regularised marginal risk with kappa30, identical covariance estimate and identical feasible invested budget within each pair. Covariance uses the inherited Ledoit–Wolf correlation, support gates and identity-prior fallback; label which is active.

Let S contain selected names with positive requested risk budget and positive entry capacity. Record excluded target mass. Normalise target b on S; retain original selected rows at zero weight outside S. Both methods use the same S, b, covariance C and `B=min(0.98,sum(caps[S]))`. If every score target is zero, use the declared equal-risk-budget fallback across positive-capacity names in both methods; if none have capacity, both are all cash.

First find positive unconstrained risk-budget weights w0 with sum B, satisfying `w0_i*(C*w0)_i/(w0' C w0)=b_i` when supported. Set `lambda=w0' C w0`. The constrained treatment minimises:

`0.5 * w' C w - lambda * sum_i b_i * log(w_i)`

subject to `sum(w)=B` and `0<w_i<=cap_i` for i in S. This is a convex variance/diversification objective for positive-definite C and positive b; it is **not** a claim to minimise exact relative-risk-contribution error under binding caps. The calibration of lambda reproduces the unconstrained target when constraints do not bind and has no return-tuned risk-aversion constant. Scaling C by a positive constant scales lambda and leaves the solution unchanged. Report the actual change in both objective and relative risk contributions.

Use the same starting covariance and conditioning for both methods. If the unconstrained solver, covariance or constrained solver fails, record status and use the projected reference allocation; never report fallback as successful optimisation. Fix zero-cap names before logarithms. Handle a singleton or an all-capacity-bound basket analytically. Preserve meaningful lower-bound/tolerance units and report if numerical bounds change economic weights. Require convex feasibility, stationarity/complementarity residuals, objective no worse than the feasible projected control within tolerance, and independent toy calculations.

An independent diagonal minimum-variance quadratic-programme fixture must reproduce direct inverse-variance water-filling: its free-coordinate optimality condition is `v_i*w_i=constant`. This identity does not establish equivalence for every capped entropy/risk-budget objective. In the entropy objective above, a binding sum/cap constraint introduces a multiplier into `v_i*w_i-lambda*b_i/w_i+nu=0`, which need not yield proportional inverse volatility for free names. A diagonal-covariance economic companion would distinguish correlation information from cap geometry, but is a separately counted extension. Do not claim the eight-policy comparison alone isolates the value of covariance estimation. Whether this follow-up merits execution should depend on identified cap activity and the research question, not choosing only profitable core cells.

## 10. Required notebook presentation

Default every table, caption and figure to the 2026 evaluation interval. State horizon and stage in every title. Use **subheading → short explanation → one table or one separate image**. No image collages or unexplained method IDs. Use a compact main notebook with linked exhaustive tables if needed; never hide unsuccessful arms.

| Output | Required content and question |
| --- | --- |
| Goal, scope and reference table | Two selectors, exact controls, dates, warmup, stage counts, expected maturity and current status |
| Executed design matrix | Formula, L, p, kappa, observation convention, floor/fallback, capacities and exact canonical IDs |
| Original-control reproduction | Per-origin identities, desired/accepted weights, cash, outcomes and support; report missing reference dates |
| Risk-support table | Actual updates, partial/flat/missing/prior/floor fractions, peer pool support; young vaults and warmup coverage |
| Side-by-side outcome table | All policies with paired support, mean/median return, variance, within-window drawdown, cash, effective N and fallback activity |
| L × p heatmaps | Separate return difference, variance ratio and drawdown difference, one selector and one metric per image; return/drawdown differences use shared symmetric scales centred at zero. Variance cells use the ratio of mean realised per-origin variances on exactly common support, with a shared log colour scale centred at ratio1; mark zero-denominator cases and print counts |
| Return/risk scatter | All methods; selector, estimator and transform labels, clear baseline and a descriptive Pareto envelope; no winner declared from a frontier alone |
| Quarter comparisons | Separate quarter heatmaps and paired-effect figures with maturity counts; distinguish independent snapshot outcomes from quarterly profit |
| Requested/accepted allocation example | Earliest informative cap-active origin chosen mechanically before profits; compare benchmark and declared method, including cash |
| Weight/risk/support plots | Separate plots showing whether apparently low risk or high weight is concentrated in sparse, stale or young histories |
| Risk-forecast calibration | Required QLIKE and realised/predicted variance in matched simple/log units, equal-origin support, prior and floor activity; no allocation fitted to these diagnostics |
| Sparse-estimator support | Actual interval counts, paired empirical forecasts, strict full-window pool fraction versus the original pool, fallback activity and gap assumptions |
| Shrinkage and window disagreement | Fixed-kappa versus L/3; median/max alternatives versus each constituent window; forecast scales and prior influence |
| T18 mechanism | Minimum-component activity and matched T18/V180 effects; show the other three components' active contributions. Label V180 kappa60 separately from main L180/kappa30 |
| Attribution and limitations | Vault/quarter influence, tail contributions, first-update attribution, cap-induced ties, numerical fallbacks, inference gate and historical limitations |
| Verdict and next-stage inventory | Which mechanisms were exercised, which outcomes improve, what remains unidentified, and exact unexecuted batch counts |

Use styled tables with common colour scales for comparable metrics; grey unsupported cells and show pending labels explicitly. Bound figure size and label density, retain full names in companion tables, suppress unnecessary stdout/widgets and use the repository's compact progress wrapper. Inspect every final image separately and verify the static notebook preview.

## 11. Implementation packages and output contracts

Reuse pure NB10 helpers where they match the frozen semantics. Do not call an input/helper function that overwrites earlier artefacts. Add risk L45 support explicitly; absence from the NB10 cache is not an unsupported-data verdict.

| File or package | Responsibility |
| --- | --- |
| `sizing_study_design.py` | Canonical main/smoke/follow-up registries, contrasts, formulas, calendar and inherited assumptions |
| `sizing_study_data.py` | Read-only provenance checks, full warmup, fixed basket/capacity ledger and 45/90/180 risk tensors |
| `sizing_study_allocation.py` | Requested methods, aggregation, projection and fallbacks; follow-up optimiser is specified/registered but implemented only in its separate batch |
| `sizing_study_analysis.py` | Horizon-independent allocations, fixed-unit outcomes, paired effects, support and attribution |
| `sizing_study_audit.py` | Independent numerical examples, original controls and temporal invariance |
| `sizing_study_report.py` | Styled tables, separate figures, explicit descriptions and findings document |
| `create_sizing_study_notebook.py` | Reproducible NB11 assembly; never overwrite NB10 |
| `11-weighting-sizing-findings.md` | Results written only after execution, with scope and comparison limitations |

Generated artefacts live in `_artifacts-restored-2026-10-07/11/<stage>/<fingerprint>/`, already ignored. Keep reusable code, notebook outputs and written conclusions outside generated directories. Save manifest, policy/contrast registries, fixed baskets, risk support, requested/accepted allocations, outcomes, paired differences, attribution, audit and figure manifest. A saved allocation must identify T, selector, policy, vault, risk estimate/status, requested/accepted weight, capacity, cash, fallback and fingerprint; outcomes add h without changing the allocation.

Implementation order: freeze inputs/registries → independent numerical fixtures → reproduce controls → full-calendar smoke → audit and visual inspection → complete main matrix and all three horizons → paired analysis and robustness → final separate-image inspection, notebook validation, written findings and summary update. Stage advancement depends on correctness, not returns. Keep later batch registries unexecuted and labelled.

Use `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`, saving in place with observable progress and compact saved output. Use the repository static preview server. No live Jupyter server for preview. Tests/fixtures should check mathematics and temporal semantics independently, not simply repeat the implementation under test.

## 12. Required checks and assumptions register

Independent checks must cover exact control reproduction; L+1 prices versus L returns; ddof; partial/flat/missing windows; peer self-exclusion; fixed kappa versus L/3; source/raw/regularised floor differences; log-space powers; bounded I/V formulas; all-basket fallback; median/max risk aggregation before allocation; zero-request preservation; capacity and budget conservation; fixed-unit path arithmetic; terminal support and signed bounds; unchanged allocations under future NAV/state mutation; unchanged baskets across sizing methods and unchanged weights across horizons; exact stage counts and maturity totals; notebook JSON and completed outputs; separate chart rendering. The follow-up optimiser additionally needs the no-binding-cap equivalence, covariance-scale invariance and constrained numerical checks above.

| Assumption | Initial value | Reason and limitation |
| --- | --- | --- |
| Selectors / breadth | Frozen focal and v11, six positions | Isolates sizing; not evidence six is universally optimal |
| Risk windows | 45,90,180 calendar days | Half/base/double around actual 90-day source sizing; local75/105 sensitivity defined |
| Power p | 1,1.5,2 | Inverse vol through inverse variance; p1.5 is an interpretable intermediate, not a tuned optimum |
| Shrinkage kappa | 30 actual updates | Exact 90-day baseline; fixed across windows; 10/90 sensitivity proposed |
| Peer pool | Positive leave-one-out median, complete then partial, gate1 | Source parity; weak pools, flat-peer exclusion and composition changes must be reported |
| Raw floor | Variance1e-8/day | Inherited convention; not imposed on regularised control; 1e-10/1e-6 companions proposed |
| Missing risk | Prior then inherited whole-basket equal fallback | Preserves young vaults and control parity; can make method differences inactive |
| Entry constraints | $150k,98% budget,33% concentration/pool cap | Existing source-like projection; hard deposit caps are reported under inherited source semantics |
| Main horizon / secondary | 30 / 7,90 days | Existing decision question; horizons share allocations and are not independent evidence |
| Inference | Ten complete blocks;1,999 shared draws when supported | Inherited gate, retrospective history; no inferential promotion by changing the gate |
| Alternative forecasts | Median/max of three registered window variances | Low-parameter stability/conservatism probes; correlated windows, no performance-tuned blend |

Do not add a hidden age exclusion, stale-price cutoff, observation-count multiplier, uncertainty penalty, covariance jitter, weight minimum, turnover charge, slippage or return threshold. Numerical tolerances must inherit or explicitly document units and economic effect. Deposits/redemptions are at NAV; account for actual applicable fees when later execution work warrants it, rather than inventing transaction costs.

## 13. Completion and subsequent replay

The next implementation task completes the 40-policy main NB11 experiment after its 18-policy smoke checkpoint, with all horizons and full available 2026 origins, independent checks, readable outputs and updated summary. It does not execute the 12 sensitivity or eight cap-aware follow-up policies automatically.

Carry only a small, explicitly labelled research shortlist to a later engine replay, choosing interpretable parameter neighbourhoods and disclosing trade-offs rather than optimising an arbitrary composite metric. Require the original benchmark and equal control in any replay. Existing holdings, two-day rebalancing, minimum trade thresholds, state retention and changing capacity can alter snapshot conclusions. Fresh future observations are the appropriate confirmation set; splitting already researched 2026 retrospectively does not create an untouched holdout.

## 14. Claude contribution and review

The first contribution returned successfully from `claude-fable-5-1`. Accepted: fixed-kappa comparisons, matched sparse-mark risk estimation, calibration/support diagnostics and an independent diagonal-QP equivalence check. Rejected: the claim that the budget forces three cap-bound positions; the claim that T18 changes selection; reading its 79% minimum-component activity as data coverage; unsupported standard-error estimates; and unconditional claims that forward filling necessarily biases risk downwards. The formal review returned **ready with specific corrections** and verified the exact counts, maturity convention and estimator/optimiser algebra. Its six required clarifications are incorporated: sparse-pair shrinkage count, bounded-I kappa, snapshot entry/exit dates, explicit block calendar/gates, peer-count gate and strict-pool support reporting. Additional accepted clarifications cover per-vault TVL caps, variance-ratio plots, V180 kappa60 and partial-window availability. Required calibration and matched-budget allocation shadows were added; shuffled-weight placebos remain deferred pending a registered persistent-assignment design and trial count. The focused final check returned **ready**, with no material implementation blocker. Its remaining non-blocking clarifications—explicit END, exact missing-TVL behaviour and the units of sparse-pair kappa—are now stated; these clarifications do not change the policy matrix or formulas. See [the contribution and review dispositions](11-weighting-sizing-review.md); full prompts, returned-model evidence and reviewed-plan hashes are retained in the ignored review directory.
