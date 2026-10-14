# Expanded experiment 10 — composite scores for ranking and allocation

Written 10 October 2026. Revised smoke scope: full available 2026 history, with 2025 indicator warmup; reduce combinations, not dates. **Status: the initial 36-arm smoke stage is implemented and executed; broader stages remain proposed.** This supersedes the original three-score restriction and extends [the original NB10 plan](10-portfolio-snapshot-plan.md) and [original executed snapshot notebook](appendices/10-original-portfolio-snapshots.ipynb). Preserve the first implementation and its [findings](10-portfolio-snapshot-findings.md) as the reference generation. Implement the expansion in the same main notebook, with linked appendices and separately fingerprinted artefacts.

## 1. User goal and the essential design change

Explore a substantially wider set of portfolio allocation methods, using all existing scoring variants and new composite scores containing inverse variance, inverse volatility, K-ratio and other existing performance metrics. Allow the score that ranks/selects vaults to differ from the score that sizes them. Start with the smoke-test matrix below; do not launch the full search on the first implementation run.

Inverse variance and the other metrics are **features inside a per-vault composite score**. They are calculated and transformed on the eligible universe before selecting a basket. There is one final conversion of the weighting score into requested portfolio weights, followed by the declared allocation constraints.

For example:

`ranking_score_i = (base_score_i + inverse_variance_score_i + K_score_i) / 3`

`weighting_score_i = (inverse_variance_score_i + K_score_i) / 2`

Select the top N using `ranking_score`; size those selected names using a specified mapping of `weighting_score`.

Do not implement this request as a 50/50 blend of two already normalised portfolio allocations. Do not normalise each ingredient to sum to one across the selected basket and then combine those allocations. The component transformations below have fixed meanings before selection, and component values must not change when N or the selected basket changes. Old equal/inverse-risk portfolios remain named comparison controls only.

### Questions and hypotheses

| ID | Question | Evidence sought |
| --- | --- | --- |
| H1 | Does including low-risk characteristics in the composite score help? | Paired selection and sizing effects for base score versus base plus inverse-risk score, with unchanged cash/caps where applicable. |
| H2 | Does K-ratio add information beyond growth, risk and existing ratios? | K-on versus K-off ablations on matched support, plus age/reporting diagnostics. |
| H3 | Should ranking and weighting use the same score? | Crossed ranking/sizing comparisons with one side held fixed. |
| H4 | Do score magnitudes deserve proportional capital? | Linear, power, percentile and softmax mappings compared on the identical selected basket. |
| H5 | Do richer composites generalise across existing score recipes? | Coverage of every registered recipe, family distributions and temporal stability, not only one winning recipe. |
| H6 | Do constraints alter which scoring method works? | Requested versus accepted weights; matched constrained/uncapped controls and equal-budget benchmarks. |
| H7 | Can young/sparse vaults participate sensibly? | Explicit missing-component policies, confidence sensitivities and retained candidate/position ledgers. |

NB10 established that concentration/TVL projection can materially alter conclusions. Thus the expanded experiment's main branch includes these constraints from the start. Uncapped results are mechanism controls, not substitutes for constrained comparisons.

## 2. Scope, inputs and chronology

Reuse the pinned repaired archive, source eligibility, causal calendar NAV, fixed-unit outcomes and independent audit machinery from NB10. Do not download a newer archive as part of implementation. Verify actual archive and metadata hashes, framework commits and module fingerprints at run time.

- Main displayed origin period: **2026-01-01 → 2026-10-05, end exclusive, naive UTC**.
- Indicator warmup: load all available 2025 observations before the first 2026 decision, including the last preceding valid NAV anchor. Retain earlier recorded history wherever available for 730-day features, maximum-history K and frozen recipes; 2025 is a minimum warmup requirement, not a truncation boundary. Warmup observations initialise features only and never become 2026 outcome rows. Do not require a vault to have existed throughout 2025.
- Secondary periods: full history **2023-03-01 → 2026-10-05**, and pre-2026 **2023-03-01 → 2026-01-01**, separately labelled.
- Primary origin cadence: four days, anchored at 2026-01-01. All four phases are later robustness checks.
- Smoke horizon: **30 days only**. Subsequent stages evaluate **7, 30 and 90 days**, with 30 days primary.
- At decision T, use completed features through A=T−1, actual observations strictly before T, and the existing audited target convention A through A+h. Labels become usable only at their recorded availability time.
- Current inventory/guard and permission-clock limitations remain disclosed. NAV forward filling never fills permission or capacity fields.
- Gross NAV fixed-unit snapshots remain the initial research vehicle. Do not derive strategy CAGR or a single strategy Sharpe by compounding overlapping snapshots.

### Existing score and feature inventory

The NB08 registry currently contains **139 distinct composite recipes**, including aliases/provenance from NB04–NB07. Load its canonical recipe hashes and verify this inventory; do not silently restrict the expansion to the three focal scores. If the count changes, emit a registry diff and resolve the cause before evaluating new outcomes.

The three focal scores are used for the first smoke test only:

- `L`: original v11 / Legacy 45d recipe.
- `B`: Blend 46d recipe.
- `F`: four-input focal recipe.

Broader stages substitute every registered recipe for the base-score role. Preserve coefficients, clipping profiles, recipe missingness and aliases. Admission filters and sizing rules attached to an old experiment are separate policy fields; an alias is not a new score.

Require standalone single-metric scores as well as blends: **CAGR alone, Sharpe alone, Sortino alone, maximum drawdown alone, Calmar alone, inverse volatility alone, inverse variance alone and K-ratio alone**. Each metric can supply ranking, weighting or both. These are additional baseline recipes: NB08's 139-composite registry deliberately excluded single-feature diagnostics, so loading that registry alone does not provide this coverage. Use the existing feature definitions rather than reimplementing financial ratios inside the allocator.

Required component windows for broader exploration:

| Component | Windows / definitions |
| --- | --- |
| Frozen composite recipe | Its exact original windows and clipping; no silent retuning |
| Inverse volatility / inverse variance | 30, 60, 90, 180 days; 75/105-day local controls where used |
| K-ratio | 30, 60, 90, 180, 360 days and maximum recorded history |
| Other raw performance metrics | Existing NB09 inventory: 30, 46, 60, 90, 120, 180, 270, 360, 730 days where defined; retain source 45-day compatibility |

For the standalone sweep, evaluate every metric at every declared compatible lookback, not just one representative window. In particular, compare CAGR-only and Sharpe-only scores across 30/46/60/90/120/180/270/360/730 days; retain 45-day compatibility as a named additional control. K uses its listed six definitions, and risk components use their listed windows. Fixed and maximum-history variants have distinct recipe IDs.

Do not cross all windows with all recipes in the smoke test. The stage schedule specifies which dimensions expand and when. Additional raw metric cells already in the feature inventory receive an inventory row even if scheduled for a later batch.

## 3. Component scores: before selection, on a declared scale

Every ingredient has a value, availability mask, empirical/prior status, transformation ID and observation-support fields. Let `s_i` be a frozen base score, `v_i` the declared daily variance estimate, and `v0_i` the positive leave-one-out eligible-peer variance prior from NB10.

### Default component transforms

| Symbol | Definition | Interpretation and edge cases |
| --- | --- | --- |
| `S` | Frozen recipe output on its documented 0–1 scale | Preserve the recipe exactly. Audit the range rather than silently clipping new out-of-range values. A recipe using another scale needs an explicitly registered transform. |
| `I_d` | `v0_i / (v_i + v0_i)` using d-day risk | Bounded inverse-variance component: 0.5 at peer risk, closer to 1 for lower variance. This is a monotone bounded transform of `1/v`; it is not a normalised allocation. |
| `V_d` | `sqrt(v0_i) / (sqrt(v_i) + sqrt(v0_i))` | Bounded inverse-volatility component with the same 0.5 peer anchor and different sensitivity to risk magnitude. |
| `K_d`, `K_max` | `0.5 + atan(K_i / k0) / pi` | Signed K quality: negative K below 0.5, zero at 0.5, positive K above 0.5. `k0` is the median strictly positive absolute finite K in the eligible universe at T, for that same K window. |
| `C_d`, `Sh_d`, `So_d`, `D_d`, `Ca_d` | Average-rank percentile of finite historical CAGR, Sharpe, Sortino, signed maximum drawdown or Calmar | Larger means better. Maximum drawdown nearer zero is better; do not compute `1/abs(drawdown)` and create an infinite score. |

Use the existing NB09 K definition: fit intercept OLS to equally spaced log NAV marks including the anchor, then K=(slope/slope_standard_error)*sqrt(365)/n, where n is the fitted calendar-mark count. Require n>=3 and the existing non-degenerate residual/standard-error checks from `k_ratio_features.k_statistics`; keep actual updates separate from filled marks. Within a fixed complete window n is constant, so this factor cancels in the median-absolute-K normalisation; the transformed ordering is the corresponding slope t-statistic ordering. For maximum history, n differs across vaults and does not cancel. This span scaling does not prove comparable reliability across ages. Report K and transformed K by elapsed span and actual support; do not substitute raw slope t-statistics.

For the K transform, if all finite K values are zero, assign those valid zeros 0.5; missing K remains missing. If there are no finite values, the component is unavailable. Record the peer count and scale; a one-peer scale is usable but weak and separately flagged. Fixed K windows and maximum history get separate scales. Do not assume a short maximum-history K has the same measurement reliability as a long one.

For percentile transforms, use `(average_rank - 0.5)/n_finite`. A single finite observation receives 0.5; ties receive identical values. Availability remains separate. Components are transformed using the eligible universe at T, before any top-N selection. Do not use future outcome support to define the transformation population.

The peer prior both regularises risk and anchors the bounded I/V transform. Low-support prior-dominated estimates can therefore produce scores near 0.5 even under M0; label them as prior-supported estimates, not empirically observed risk or ordinary missing-zero values. The default smoke run diagnoses resulting dispersion; a raw-versus-regularised matched arm belongs in the proposed next batch if needed.

Smoke risk inputs use NB10's **regularised variance**, with actual-update support and positive peer priors; source/raw estimates are separate controls. A risk estimate without a usable peer reference makes `I`/`V` unavailable; do not invent a peer scale. Empirical zero variance with genuine observations can be handled by the declared risk estimator. An unobserved carried-flat history cannot become a confident maximum low-risk score.

### Registered transform alternatives

Explore these after the default smoke pass, always naming the transform:

1. Cross-sectional percentile representations of S, I, V and K.
2. Original compatible clipping for existing return/ratio scores, versus the percentile representation of that same feature.
3. Positive-K variant: transform `max(K,0)` with `x/(x+k0)`; valid negative/zero K produces zero, not a missing observation.
4. Confidence-adjusted K: `K_conf = 0.5 + c*(K_score−0.5)`, `c=m/(m+kappa_K)`, where m is the number of actual update dates after the initial anchor in the fitted span. Initial `kappa_K=30`, with 10/90 sensitivities. This is a heuristic confidence rule, not a statistical standard error.
5. Raw/source versus regularised variance inside I/V, and the existing risk-prior/floor sensitivities.

**Deduplication invariant:** percentile-ranked `1/sigma` and `1/variance` have identical order on identical positive support when built from the same variance estimates. Their percentile vectors must match. For peer-relative transforms built from the same variance, prior and support, set r=v_i/v0_i: I=1/(1+r) and V=1/(1+sqrt(r)). Both are strictly decreasing in r, so their rankings and percentile vectors also coincide, even with vault-specific priors. Their order need not equal raw inverse-risk order because the peer prior can vary. Different estimators, priors or support masks require separate checks. Magnitude-based I and V remain different components. Preserve aliases but count identical constructions only once in computation and evidence.

## 4. Composite score grammar

A score recipe is an expression tree over the component scores, not a collection of portfolio weights. Every expression is evaluated for the whole eligible universe before selection.

### Combiners

- `A(X,Y,...)`: arithmetic mean of component scores, with equal coefficients unless stated. General form `sum(a_j*x_j)` with non-negative coefficients summing to one.
- `A[coefficients](...)`: explicit weighted arithmetic score. Initial coefficient anchors are 0, 0.25, 0.5, 0.75 and 1 for two components; three-component anchors include equal thirds and each permutation of (0.5,0.25,0.25).
- `G(X,Y,...)`: weighted geometric score, `product(x_j**a_j)`. A valid zero with positive coefficient makes the product zero. Zero-coefficient components are removed before evaluation; do not use arbitrary epsilons to change this behaviour.
- `Min(X,Y,...)`: weakest-component score. This is a conjunction control that asks whether all qualities must be acceptable; it is not the default.

Arithmetic means test compensating strengths; geometric/minimum scores test agreement between ingredients. No training or optimisation is needed to define these fixed candidates.

Example of the user's requested inverse-variance score:

`Q_i = 0.5*S_i + 0.25*I_90,i + 0.25*K_90,i`

A vault with `(S,I,K)=(0.8,0.2,0.6)` has Q=0.6; a vault with `(0.4,0.9,0.7)` also has Q=0.6. They tie before the final sizing rule. Neither ingredient was normalised over the selected basket. Coefficients express feature preference on the declared scales, not fractions of portfolio capital.

Treat these coefficients as design anchors, not optimal weights. Do not optimise coefficients using the period subsequently displayed as validation.

## 5. Ranking score and weighting score are separate policy fields

Each policy declares:

`ranking_recipe_id, weighting_recipe_id, sizing_map, N, missing_policy, constraint_policy`

1. Compute both recipes across the full eligible universe using historical information.
2. Rank by ranking score descending, with fully unavailable scores in a distinct lowest-priority tier. Break exact ties by (chain ID, canonical lowercase vault address); seeded tie sensitivities come later and include the wholly unscored tier. Address order gives persistent arbitrary preference within that tier; it is not evidence about young-vault quality.
3. Select `min(N, eligible_count)` vaults, including the unscored tier when needed under `missing=True`.
4. Apply the declared sizing map to weighting scores on those selected names.
5. Normalise the resulting requested weights once, then apply the common budget/concentration/TVL projection.

Supported sizing maps:

| Map | Requested weight rule | Purpose |
| --- | --- | --- |
| Equal | Identical requested weights | Selection-only control |
| Linear | `u_i = Q_i` | Direct use of score magnitude |
| Power | `u_i = Q_i**q`, initial q=0.5 or 2 | Flatten or amplify composite-score differences |
| Percentile | `u_i = percentile(Q_i)` calculated on eligible valid Q before selection; unavailable Q gets zero under missing-zero policy | Test ordering versus score magnitude |
| Softmax | `u_i = exp(beta*(Q_i−max_selected_Q))` | Positive allocation with bounded sensitivity to score gaps; initial beta=ln(4), giving a maximum 4:1 raw ratio over a full 0–1 score range |
| Score risk budgets | `b_i proportional to Q_i`, then solve covariance-aware risk budgeting | Let a composite score determine relative risk contribution rather than dollar share |

The score risk-budget solver uses NB10's covariance estimate and enforces non-negative weights. On the strictly positive target-budget subset, normalise b to sum to one and solve `min_x 0.5*x.T*Sigma*x − sum(b_i*log(x_i))`, x positive, then set `w=x/sum(x)`. Independently verify `w_i*(Sigma*w)_i / (w.T*Sigma*w) = b_i` within the inherited tolerance. This replaces the equal-budget vector in NB10's solver; do not merely multiply existing risk-parity weights by scores. Zero-score names receive zero target risk and remain in the ledger; solve on positive targets. If all targets are zero/missing, fall back to bounded equal weights. If the solver fails, fall back to linear score sizing, with an explicit status. The entry cap projection may disturb achieved risk contributions; show requested and accepted contributions. Equal risk contribution is recovered when all positive scores are equal.

Softmax's baseline allocation to an unavailable score represented numerically as zero is intentional and reported. Linear/power/percentile mappings can give selected zero-score names zero dollars. Keep those names in the selection ledger and distinguish requested N, selected count and positive-weight count. Do not call a nominal ten-name basket ten invested positions if some weights are zero.

Old pure inverse-volatility/inverse-variance sizing remains a comparison control with its exact definition. Do not describe it as the new bounded inverse-risk component.

## 6. Missing and sparse observations

The default new-composite policy is **M0: missing-zero, no coefficient renormalisation**. Unavailable component values contribute numeric zero to arithmetic/geometric/minimum expressions, but retain their masks. A composite is fully unavailable only when every positively weighted component is unavailable. A valid composite equal to zero remains distinct from that fully unavailable case.

Two explicit alternatives:

- **MN: neutral prior.** Unavailable components contribute 0.5 on the declared 0–1 scale; retain flags, and keep a wholly unavailable composite in the unscored tier even though its numerical fill is 0.5.
- **MA: available components.** Renormalise coefficients over available components. If none is available, use the unscored fallback. Report retained coefficient mass because a one-component score is not the original complete recipe.

**Unavailable weighting contract:** for linear, power and score risk budgets, fully unavailable Q receives numeric zero under M0/MA and 0.5 under MN. Equal sizing ignores Q availability. Softmax uses those same numerical fills and intentionally gives zero-filled names positive mass. For percentile sizing, rank only genuinely available composite Q values; M0/MA unavailable names receive zero. MN unavailable names receive the mid-distribution percentile of the fill 0.5 against that available reference: `(count(Q<0.5)+0.5*count(Q==0.5))/n_available`; if no available reference exists, use 0.5 and flag the neutral fallback. This also reproduces `(average_rank−0.5)/n` for available observations. All-zero positive-budget maps use the declared equal fallback; an empty basket remains all cash. Ranking availability masks remain unchanged by these fills.

**Zero weights under caps:** redistribute only among positive requested-weight names. Do not fund a valid zero or unavailable zero-filled name through cap redistribution. Residual cash is possible when too few positive names can accept the budget. Report that outcome separately from the all-zero equal fallback, including the discontinuity between one positive name and none. No epsilon or hidden minimum allocation is permitted.

These policies wrap the frozen base recipe; they do not rewrite its historical internal missingness. For example, a missing base composite can still coexist with finite I or K in a new score. Such a vault may receive a finite ranking score from those ingredients; this is an intentional new rule, not exact v11 parity.

All-zero/all-unavailable linear sizing falls back to equal requested weights, including empty/candidate-limited cases handled explicitly. There is no automatic exclusion of a young vault because K360 or the base composite is absent.

**Standalone missingness:** a missing sole metric leaves that vault unscored, rather than excluding it from the eligible universe. It can fill a selected slot in the unscored tier under `missing=True`. Under M0, linear sizing can give it zero dollars when other selected names have positive scores; if all selected weighting scores are unavailable/zero, use equal sizing. MN can provide a neutral weighting value, but does not turn an entirely missing ranking feature into a scored observation. MA has no other component to substitute in a single-metric recipe and therefore retains the unavailable status. Report selected and actually funded young vaults separately.

A missing 360-day CAGR for a 60-day-old vault remains missing; do not relabel a 60-day calculation as a 360-day metric. Gaps within an otherwise supported elapsed window are handled by causal forward filling. Using shorter available windows is permitted through the explicitly registered shorter-window recipes and mixed-window composites; it must not occur silently inside a fixed-window recipe.

Use NB09's audited daily calendar metrics. Forward-fill positive NAV causally, with no leading backfill or future interpolation. Fixed-window metrics require their declared elapsed span; maximum-history K can use the available span, subject to its mathematical requirements. Preserve actual timestamp, actual count, calendar span, anchor age, flatness and denominator-degeneracy reasons. Future outcomes are never carried beyond the supported terminal archive boundary. Never renormalise away an asset with a missing future outcome.

## 7. Smoke-test matrix — implement this first

The purpose is to cover different mechanisms and expose errors across **the full available 2026 origin history, using 2025 indicator warmup**. Limit the number of parameter combinations, never the historical dates. These arms are deliberately chosen for variety, not a complete factorial. A multi-change row is a coverage probe; only the matched rows listed below support attribution.

Defaults unless a row overrides them: N=6; regularised 90-day risk; M0; linear sizing; **C** constraints ($150,000 account, 98% entry budget, 33% account concentration cap, 33% TVL cap, source-report-only state and redistribution). **P** means the original pure 100%-invested uncapped snapshot. Archive hard dollar deposit limits remain a separately labelled later sensitivity, not quietly added to source-compatible C.

Here `I=I_90`, `V=V_90`; `K30+` is the positive-K transform at 30 days. `A`, `G` and `Min` have the exact component-score meanings defined above.

| ID | Ranking score | Weighting score / control | Sizing map | N | Missing | Constraints | Coverage / why included |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| T00 | L | Source 90-day raw inverse variance | Existing control | 6 | Legacy | C | Reproduce the prior NB10 capped source reference |
| T01 | F | Constant 1 | Equal | 6 | M0 | C | Same-basket equal benchmark |
| T02 | F | F | Linear | 6 | M0 | C | Direct existing-score sizing |
| T03 | F | I | Linear | 6 | M0 | C | Bounded inverse-variance feature alone; differs from raw 1/v sizing |
| T04 | F | V | Linear | 6 | M0 | C | Bounded inverse-volatility feature alone |
| T05 | F | A(F,I) | Linear | 6 | M0 | C | Add inverse variance to weighting score only |
| T06 | A(F,I) | Constant 1 | Equal | 6 | M0 | C | Add inverse variance to ranking only |
| T07 | A(F,I) | A(F,I) | Linear | 6 | M0 | C | Same risk-enriched score for ranking and weighting |
| T08 | F | A(F,V) | Linear | 6 | M0 | C | Inverse-volatility versus inverse-variance score blend |
| T09 | F | G(F,I) | Linear | 6 | M0 | C | Agreement/product score versus compensating arithmetic score |
| T10 | F | A(F,I) | Power q=2 | 6 | M0 | C | Amplified composite-score conviction |
| T11 | F | A(F,I) | Softmax beta=ln(4) | 6 | M0 | C | Smooth mapping; sparse/zero-score names can retain capital |
| T12 | F | A(F,I) | Percentile | 6 | M0 | C | Magnitude versus ordering |
| T13 | F | A(F,I,K90) | Linear | 6 | M0 | C | K addition to the weighting score |
| T14 | A(F,I,K90) | A(F,I,K90) | Linear | 6 | M0 | C | Complete three-component ranking and weighting |
| T15 | A(F,I,Kmax) | A(F,I,Kmax) | Linear | 6 | M0 | C | Maximum-history K; short histories remain usable |
| T16 | A(F,I,K360) | A(F,I,K360) | Linear | 6 | M0 | C | Long fixed K and substantial feature missingness |
| T17 | B | G(B,I,K30+) | Linear | 6 | M0 | C | Another existing score, responsive positive-K transform and three-way agreement |
| T18 | L | Min(Sh90,Ca180,V180,Kmax) | Linear | 6 | M0 | C | Four-input conjunction and fallback-coverage probe: any missing ingredient makes Q zero; report unfunded names/cash and propose an MA companion later |
| T19 | A(C180,So30,K90) | A(I,Kmax,D90) | Linear | 6 | M0 | C | Distinct raw-metric recipes for opportunity ranking and capital allocation |
| T20 | A(F,I,K90) | A(F,I,K90) | Linear | 10 | M0 | C | Breadth sensitivity matched to T14 |
| T21 | A(F,I,K90) | A(F,I,K90) | Linear | 6 | MN | C | Neutral missingness matched to T14 |
| T22 | A(F,I,K90) | A(F,I,K90) | Linear | 6 | MA | C | Available-component renormalisation matched to T14 |
| T23 | A(F,I,K90_conf) | A(F,I,K90_conf) | Linear | 6 | M0 | C | Confidence adjustment matched to T14; kappa_K=30 |
| T24 | F | A(F,I,K90) | Score risk budgets | 6 | M0 | C | Composite scores drive covariance-aware risk allocation; paired with T13 |
| T25 | A(F,I,K90) | A(F,I,K90) | Linear | 6 | M0 | P | Uncapped counterpart to T14; deployment difference shown separately |
| T26 | A(F,I,K90) | A(F,I) | Linear | 6 | M0 | C | K affects ranking but is removed from weighting; same basket as T14 |
| T27 | F | A(F,constant 0.5) | Linear | 6 | M0 | C | Constant-component flattening control: T05 versus T27 tests whether I adds value beyond a neutral offset; T02 versus T27 shows mechanical flattening |
| T28 | C30 | C30 | Linear | 6 | M0 | C | CAGR alone: responsive standalone ranking and weighting |
| T29 | C360 | C360 | Linear | 6 | M0 | C | CAGR alone: long lookback and young-vault missingness; matched to T28 |
| T30 | Sh90 | Sh90 | Linear | 6 | M0 | C | Sharpe alone: standalone risk-adjusted performance score |
| T31 | Sh360 | Sh360 | Linear | 6 | M0 | C | Sharpe alone: long lookback and missingness; matched to T30 |
| T32 | So180 | So180 | Linear | 6 | M0 | C | Sortino alone: downside-risk performance score |
| T33 | D90 | D90 | Linear | 6 | M0 | C | Maximum drawdown alone: shallower drawdown ranks higher |
| T34 | Ca360 | Ca360 | Linear | 6 | M0 | C | Calmar alone: long span and undefined-denominator coverage |
| T35 | Kmax | Kmax | Linear | 6 | M0 | C | K-ratio alone: young and mature vaults with differing recorded spans |

The matrix contains **36 named arms**, including one exact legacy control. Runtime deduplication may identify identical outputs on some dates; retain the design rows and report when a treatment was inactive. Do not count date-specific equality as universal recipe equivalence.

### Smoke origins and outputs

1. Run independent synthetic/adverse calculation fixtures first.
2. Generate every phase-zero four-day origin in 2026-01-01 → 2026-10-05 (end exclusive). Do not sample, thin or choose representative dates. Full history means the full available 2026 interval on the declared cadence, not future dates after the archive ends.
3. Load the 2025 warmup and any earlier history required by the registered lookbacks before calculating the first origin. Compute features causally through T−1. Record data-start dates, oldest actual anchors and finite/missing component coverage at the first 2026 origin. Compare first-origin feature values with the untruncated historical feature calculation; unsupported young-vault windows remain missing rather than dropping the vault.
4. Run T00–T35 across the entire grid for the 30-day horizon. Keep late origins with administratively immature labels in the feature/allocation ledger and mark their economic outcomes pending. Evaluate mature outcomes only where the horizon fits within the pinned archive boundary, independently of individual vault outcome availability. Never shorten feature history or omit an origin to make an arm complete. Do not launch seven-/90-day, pre-2026 outcome or all-139-recipe sweeps yet.
5. Save correctness, support, quarterly and full-2026 provisional economic summaries marked **smoke test — full available 2026 history; restricted combinations**. Report scheduled origins, administratively mature origins and resolved paired support separately. An unresolved individual path remains visible and is handled by the inherited censoring rules; it must not silently reduce the scheduled calendar.
6. Emit coverage by mechanism: inverse-risk variants, K windows/sign, arithmetic/product, different ranking/weighting, maps, missingness, covariance, breadth and constraints. Min-combiner and positive-K behaviour must also be verified with deterministic fixtures, because a historical date may not exercise valid-zero or negative-K edges.

### Calendar assertions — 2026 origins, 30-day outcomes

Use administrative maturity `A+30 days <= 2026-10-04`, equivalently `T+30 days <= 2026-10-05`; label availability is at the end-exclusive boundary or earlier. With the pinned boundary and phase-zero cadence, assert the counts below. Any mismatch must be explained before interpreting outcomes. Quarter refers to the decision origin, and Q4 remains visible with no mature outcomes.

| Origin quarter | Scheduled origins | Mature origins | Pending origins |
| --- | ---: | ---: | ---: |
| 2026 Q1 | 23 | 23 | 0 |
| 2026 Q2 | 23 | 23 | 0 |
| 2026 Q3 | 23 | 16 | 7 |
| 2026 Q4 | 1 | 0 | 1 |
| Full available 2026 | 70 | 62 | 8 |

### Input reconciliation and reference parity

Before allocating, materialise each required component/window/transform and record whether it was loaded, causally computed from the pinned inputs, or genuinely unsupported. Explicitly include V180 and its matching 180-day peer prior, Sh90, Ca180, Ca360, So30, C180, D90, K360 and Kmax. An absent cache is not evidence that the feature itself is unavailable: compute required supported features using the existing audited definitions. Do not replace windows or silently drop arms.

Compare T00 and T01 on the same 62 mature origins against saved NB10 identities, per-origin weights, support, cash and outcomes. T00's displayed reference is approximately 1.467% mean 30-day return and 3.008% cash. T01's capped equal benchmark is approximately 1.716% mean return and 3.315% cash; extract its unrounded reference from the saved equal benchmark ledger, and verify that budget/caps/positive-support definitions coincide before asserting parity. Rounded findings are orientation only. Require identical discrete keys/masks and use `rtol=1e-9, atol=1e-10` for dimensionless floating weights/returns; these are reproducibility tolerances, not economic thresholds. Diagnose any failure instead of loosening tolerances to obtain a pass.

Smoke success requires every arm to execute or have an explicit unsupported reason; no unexplained joins/NaNs, no negative/non-finite weights, reconciled budgets/caps and zero future-data dependence. It does not require a positive return.

**Execution boundary:** implementing this plan initially means implement the shared machinery and run the smoke matrix. Finish with a smoke findings file and exact proposed next-stage registry/count. Do not automatically launch the broad or refined searches. A subsequent instruction to expand/run the next stage authorises that stage. No repeated permission prompt is needed for work already explicitly authorised.

## 8. Controlled expansion after the smoke pass

### Stage A0 — standalone metrics across their lookbacks

Before interpreting complex blends, materialise a standalone registry for every metric/window pair in section 2, separate from the 139 frozen composites. For each single component X, evaluate these three roles:

| Ranking | Weighting | Purpose |
| --- | --- | --- |
| X | Constant 1 / equal | Isolate selection by that metric |
| F | X / linear | Isolate its allocation contribution on a common reference basket |
| X | X / linear | Use the same standalone metric for selection and sizing |

Use the main capped constraints and N=6 initially. Retain missing=True throughout; compare M0/MN/MA explicitly and deduplicate single-component cases where two policies are mathematically equivalent. Report metric × lookback heatmaps for IC, paired selection lift and paired weighting lift separately. Calendar span, missing-feature share and positive-weight participation must accompany the comparisons. Unsupported windows remain visible; do not reduce the universe to vaults with every lookback available.

This is a broader stage after smoke, not an extra smoke factorial. Its single-metric controls remain visible in later blend comparisons. When window changes alter selected baskets or target support, use the resolved union for paired comparisons and also show each policy's own support.

### Stage A — all existing recipes and allocation families

Every one of the 139 frozen recipes takes the role of S. At N=6, risk window 90 and K90/Kmax, construct the following finite family inventory:

- S, I, V, K90 and Kmax alone, with recipe-independent controls deduplicated.
- A(S,I), A(S,V), A(S,K90), A(S,Kmax).
- A(S,I,K90), A(S,I,Kmax), A(S,V,K90), A(S,V,Kmax).
- G(S,I), G(S,K90), G(S,I,K90), and Min(S,I,K90).
- Weighted three-component score permutations of (0.5,0.25,0.25), alongside equal thirds.
- The same families with selected percentile/positive-K alternatives from the declared transformation catalogue.

For each two-/three-component family, retain matched roles: base ranking/new weighting; new ranking/equal weighting; new ranking/new weighting; and new ranking/base weighting where needed to isolate the ingredient. Add the K-off weighting counterpart on the identical K-on basket. Do not evaluate all 139×139 ranking/weighting recipe pairs automatically.

Apply linear sizing to every family first. Then apply the registered sizing maps to the fixed family representatives, keeping selection fixed; all 139 bases must receive those representatives. Report a coverage table proving that recipes were not silently dropped after weak initial results.

Run the full 2026 grid and the three horizons, in restartable batches by score family. Add full/pre-2026 summaries as separate jobs. Store date-level results and support masks for every arm, not just leaders. Keep C as the primary constraint policy. P and explicit hard-deposit-cap/no-redistribution controls are matched sensitivities.

Before execution, materialise the complete registry and report unique component tensors, score expressions, economic policies, origins, estimated CPU/RAM/storage and duplicate counts. Measure runtime on the smoke batch before choosing chunk sizes. Stage A is permitted only after the smoke boundary above is satisfied and expansion is requested.

### Stage B — broader features, lookbacks, coefficients and breadth

Expand with a balanced, predeclared coverage design before outcome-driven refinement:

- All declared risk and K windows; include 360-day and maximum-history K explicitly.
- Existing raw performance components: CAGR, Sharpe, Sortino, drawdown and Calmar. Include two-, three- and four-component composites; do not silently turn all of these into another inverse-risk-only family.
- N=4/6/7/8/10; record actual positive holdings and effective diversification.
- Both raw/source and regularised risk components.
- Arithmetic coefficient anchors, geometric and minimum combiners, sizing q=0.5/1/2, and softmax maximum raw odds 2:1/4:1/8:1 (beta=ln(odds)).
- I versus V versus no risk feature; K versus no K; raw-metric versus existing composite base; identical versus different ranking/weighting recipes.
- Missing M0/MN/MA and K confidence sensitivity.

Use a deterministic pairwise covering design over compatible categorical factors, plus the explicitly matched ablations. Publish every generated arm and the uncovered higher-order interactions. Pairwise coverage is an economical screen, not proof that three-way or higher interactions are absent. No coverage algorithm may use future returns to choose its initial combinations.

Shortlist for expensive path/covariance analysis using training-period Pareto trade-offs and stability, retaining distinct method families and controls rather than one maximum. Run the same shortlisted policies on later periods without reselecting from later results. Expand an interaction only with a named hypothesis and a new registry version.

The plan does not authorise an unrestricted combinatorial sweep or an optimiser whose evaluation period is also its fitting objective. Fine coefficient fitting and learned score calibration are separate later work packages.

### Stage C — strategy replays

Only after the snapshot comparison, freeze a small diverse shortlist and run complete engine replays with the exact ranking/weighting recipe, accepted-weight projection, incumbent rules, fees and rebalance cadence. Snapshot returns cannot establish replay CAGR. Keep the source control and matched equal benchmark in those replays. Prospective observations are required before describing the researched archive as independent validation.

## 9. Attribution, benchmarks and uncertainty

### Primary measurements

- Score IC against future simple return and future vault Sharpe for the ranking and weighting score separately; future K is an optional descriptive target, not a replacement objective.
- Mean/median horizon return, fixed-unit daily variance, drawdown and downside outcomes.
- Paired weighting lift against bounded equal allocation on the same selected basket and accepted budget.
- Paired selection lift with equal allocations, using resolved union support when ranking changes.
- Component removal effects: risk, K, raw performance term, confidence adjustment and missingness policy.
- Desired/accepted concentration, effective invested positions, cash, cap saturation, risk contribution and allocation stability.
- Young/sparse/missing-component participation, priors, fully unavailable scores and unresolved future weight.

IC cannot select sizing power or softmax temperature: monotone maps preserve ordering while changing dollars. A bounded composite score is a preference index, not a calibrated expected return. Do not compute a portfolio return as a weighted average of vault CAGRs or Sharpes.

### Four-cell ranking/sizing comparison

For each main added-feature recipe, evaluate the base/new ranking crossed with equal/new-score sizing. Use the same resolved union of baskets for the comparison. Let R00 be base selection/equal allocation, R10 new selection/equal allocation, R01 base selection/new allocation and R11 new selection/new allocation.

`R11−R00 = (R10−R00) + (R01−R00) + (R11−R10−R01+R00)`.

Report the last term as the interaction. Under constraints, actual deployment can differ between selected baskets: disclose it and add common-invested-budget controls for the ranking comparison. Do not call the full difference a pure selection or sizing effect when cash differs. The existing same-basket weighting benchmark always has the same accepted budget.

The smoke matrix deliberately limits combinations. It has no complete K three-component four-cell block: add new-ranking/equal-sizing to the next-stage registry before making that attribution. T10 versus T05 isolates q=2. The q=0.5 historical arm moves to the next stage to keep 36 smoke combinations; its numerical fixture remains required. T27 replaces it with the constant-0.5 control. T05 versus T27 varies only the risk ingredient on the same F basket; T02 versus T27 measures the effect of adding a neutral offset.

The smoke matrix contains the F/I four-cell block T01/T05/T06/T07. T13/T14 isolates the addition of K to ranking with the same weighting recipe; T14/T26 isolates K in weighting on the same selected basket. T05/T13 compares replacing a two-component average with equal thirds, which also changes F/I coefficients: label it as a recipe comparison. For an exact K coefficient ablation later, use `Q(a)=(1−a)*A(F,I)+a*K`, with a in {0, 0.25, 1/3, 0.5} and report the associated coefficient change explicitly.

### Robustness and model selection

Retain NB10's complete calendar, matched support, censoring, signed missing-return bounds, first-update attribution, endpoint-age and quarter/vault influence diagnostics. All origins count equally; unsupported rows are not compressed out of the resampling calendar.

The smoke run covers the full available 2026 origin grid. Keep its economic comparisons descriptive and make no winner or promotion claims; retaining all dates does not remove overlap or increase the number of independent horizon blocks. Show the inherited complete-block count and whether the inference gate is met; do not relax that gate for smoke. For later stages, use horizon-aware calendar blocks, phase sensitivities and the inherited ten-complete-block reporting gate. The larger search **cannot inherit the old 18-comparison multiplicity label**. Freeze an explicit primary contrast family for each expansion stage before outcomes are inspected, and compute supported simultaneous bands for that family; large secondary grids remain descriptive. Report all searched policy counts and every refinement round.

For any outcome-based refinement, split chronologically using label availability. At each selection/refit date, only labels matured strictly before that date may influence the chosen configuration. Purge overlapping target intervals at train/validation boundaries, and use inner historical folds for coefficient/window selection. Do not treat a random split of overlapping vault/date rows as validation. Reuse of this already researched history remains exploratory even with correct chronological fitting.

The K confidence rule changes effective component influence: for K90 with at most 90 actual update dates, c<=0.75, so an equal-third K coefficient has at most 0.25 slope on the original K score, plus a neutral intercept. Under M0, unavailable K still contributes zero while a weak finite confidence-adjusted K moves towards 0.5. Label this missing-versus-neutral discontinuity; include an MN companion in the proposed later confidence batch. Disclose this; a later constant-confidence control must match both attenuation and neutral intercept before attributing an effect to support adaptation.

The 139 canonical recipes are already deduplicated, but remain correlated. Report score-family distributions and score/rank correlation clusters; 139 recipe results are not 139 independent trials. Clustering must not use future outcomes.

Investigate whether K mainly duplicates low-risk or growth information with exact K-on/off allocation ablations and score-component correlation tables. Report maximum-K results by recorded history duration and actual update support. Do not discard a noisy young cohort after inspecting its outcome and retain a favourable mature cohort as the new headline.

## 10. Required notebook presentation

The heading must reproduce the user's goal: inverse variance **and other metrics are inside the score**, ranking and weighting may differ, all existing recipes are in the expansion inventory, and execution begins with the smoke matrix. Explain the score formula before any results.

Every output uses **subheading → brief description → one table or separate image**. Titles/captions always include period, horizon and stage; smoke captions explicitly say full 2026 grid / restricted combinations. Show the 2025 warmup separately from the outcome period. Default to 2026; full/pre-2026 output is separately labelled. No image collages, merged contact sheets or giant unreadable 139-row chart.

### Smoke outputs

| Element | Required content / purpose |
| --- | --- |
| Executed design matrix | The 36 arms, exact recipe IDs, constraints, missingness and status |
| Score worked example | A selected origin with component values, masks, ranking score, weighting score, desired/accepted weights; show that components precede selection |
| Arm × mechanism coverage table | Show which code paths were actually exercised, including inactive/fallback treatments |
| Component distributions and treatment activity | Separate I/V and signed K plots; per-origin component dispersion, correlations with the composite, base/new basket overlap, missing/prior fractions, requested/accepted effective N and distance from equal weights. Coefficients are not empirical influence: top-N bounded scores can give nearly equal sizing. |
| Requested versus accepted weights | One separate chart for a representative score blend and one for a constraint-sensitive case; choose examples by predeclared mechanics, not profit |
| Smoke outcome table | Mean return/risk, paired support and cash; explicitly provisional, no ranking-based promotion |
| Correctness table | Independent audit verdicts and unavailable-case reasons |

### Expanded outputs

- Ranking-recipe × weighting-recipe heatmaps for selected matched panels, with support counts; separate return, variance and drawdown figures.
- Component-weight simplex plots for three-input composites. Each triangle describes **score coefficients**, not portfolio budget shares.
- Score transform × sizing-map heatmaps on fixed baskets.
- I/V/K component ablation plots; paired points/intervals where supported.
- Return/risk scatter and frontier, with method family colour and caps shown; separate origin-level scatter coloured by quarter.
- Requested/accepted concentration, cash and effective-position charts.
- K lookback × actual-history/coverage diagnostics; neutral versus zero versus available-component treatment.
- Family distributions across all 139 recipes, followed by paginated appendix tables of every recipe. Do not show only winners.
- A compact verdict table separating implementation success, observed allocation improvement and evidence sufficient for later replay.

Keep stdout/progress compact, use existing styled tables, and inspect each rendered figure individually through saved outputs/static preview. Retain reusable presentation code outside generated artefacts.

## 11. Implementation contracts and execution packages

Use the existing snapshot modules where their contracts remain valid. Add score-specific modules instead of burying transformations in the portfolio loop:

| File / output | Responsibility |
| --- | --- |
| `portfolio_score_components.py` | Audited per-origin components/transforms/support, raw-to-score mapping and provenance |
| `portfolio_score_recipes.py` | Expression registry, missingness policies, independent ranking/weighting recipes and canonical IDs |
| `portfolio_score_allocation.py` | Score-to-weight maps and score-driven covariance risk budgets; common constraints reused from NB10 |
| `portfolio_score_design.py` | Smoke registry, subsequent stage registries, deterministic covering design and manifest counts |
| Existing `portfolio_snapshot_*` modules | Causal paths, fixed-unit economics, paired attribution, capacity, inference and compatible reports |
| `10-expanded-score-allocation-smoke-findings.md` | Smoke coverage, audits, unresolved issues and proposed next-stage scope; no claimed strategy winner |
| `10-expanded-score-allocation-findings.md` | Written only when broader stages are actually executed; hypotheses, results, support and follow-up |

Generated artefacts go under `_artifacts-restored-2026-10-07/10-expanded/<stage>/<fingerprint>/`, covered by the repository artefact ignore rules. Keep the original NB10 generation. Do not change source strategy modules or resave NB01–NB09 merely to run this expansion.

New data contracts:

- Component tensor: origin/pair/component/window/transform, value, available, prior status, actual count, history span, scale and scale support.
- Score tensor: origin/pair/recipe, numerical value, availability, available coefficient mass, imputed mass, recipe hash.
- Policy registry: ranking recipe, weighting recipe, sizing map and parameters, N, missing treatment, constraint/risk-budget details, all-zero and solver fallback policy IDs, stage and matched control IDs.
- Allocation ledger: horizon-independent and reusable for later 7-/90-day outcome joins, with no allocation recalculation unless a policy/input hash changes; both scores and ranks, selected flag, desired/accepted weight, actual positive-position count, cash/caps and all fallback reasons.
- Outcome/contrast contracts: preserve the existing unresolved masks, label availability, date keys and independent fixed-unit definitions.

All joins assert key uniqueness and cardinality. Cache component tensors separately from expression evaluation and allocation. Changing a score transform must invalidate dependent score/weight caches, even if the source data is unchanged. Load the 139-recipe cache in chunks; do not copy a full score cube into one object per policy. Deduplicate calculations while retaining registered aliases and origin-specific treatment activity.

Implement in these packages, sequentially:

1. Read provenance, reconcile the registry, and specify component/score contracts.
2. Implement transforms, expression evaluation, score maps and independent numerical fixtures.
3. Materialise and inspect the 36-arm registry; reproduce T00 and previous equal controls.
4. Execute the full-2026-grid smoke study with 2025 indicator warmup, audit it, render/inspect outputs and write smoke findings.
5. Stop at the smoke boundary. Subsequent packages implement/run Stage A0, Stage A, Stage B and full replays only when those stages are requested.

Use `poetry run python` and the observable `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent` runner. Use the repository static preview server. Do not start multiple independent data universes or broad kernel jobs. This plan does not require extra agents; if a later implementation explicitly delegates work, give independent score/risk-budget auditing exclusive ownership and keep notebook execution coordinated.

## 12. Meaningful correctness checks

These checks must use independent arithmetic/fixtures or original archive rows, not just the implementation under test twice.

1. **Component-before-selection invariant:** changing N or the selected basket leaves the eligible-universe component and composite scores unchanged. A fixture must fail for an accidental blend of separately normalised selected-basket allocations.
2. **Scale and ordering:** I/V equal 0.5 at peer risk and decrease with own risk holding the peer reference fixed. Multiplying both variance and its peer prior by the same positive constant leaves I/V unchanged. Signed K respects zero/sign and remains bounded.
3. **Composite arithmetic:** reproduce the worked example, unequal coefficients, valid zeros, geometric zero and minimum. No epsilon silently changes missing/zero cases.
4. **Rank equivalence:** percentile raw inverse-volatility and inverse-variance controls match on identical support; peer-relative I/V ranks match each other with identical estimators and priors; aliases are reported rather than treated as independent discoveries.
5. **Missingness:** M0/MN/MA produce different documented outputs on the same partial vector; fully unavailable differs from valid zero. Changing future availability cannot affect historical component masks or eligibility.
6. **Young/sparse NAV:** independently fill a calendar; actual-update counts do not grow on carried days. Fixed versus max K uses the correct span; flat/degenerate K remains unavailable for its mathematical reason.
7. **Separate score roles:** changing only the weighting recipe cannot change the selected basket. Changing ranking can change the basket; the unchanged weighting tensor still has identical pre-selection values.
8. **Sizing:** linear/power/percentile/softmax normalise correctly, respect score ties, and have declared all-zero/missing fallbacks. Softmax full-range odds agree with its specified beta.
9. **Risk budgets:** recover equal risk contribution for equal budgets; independently check target contributions before caps, and report distortion after caps. Report numerical fallback rather than silently relabelling it success.
10. **Constraints and outcomes:** reproduce inherited budget/cap/source controls, fixed units, missing-terminal censoring and equal-budget benchmarks. Reconcile the four-cell interaction identity and breadth attribution.
11. **Temporal invariance:** changing observations at/after T leaves historical scores, peer scales, ranks and requested/accepted weights unchanged. Original archive spot checks cover sparse, young, negative-K and missing-score cases.
12. **Reporting:** smoke labels must identify full 2026 history and restricted combinations; no broad-search or strategy CAGR claim; long/short periods and support are explicit; every registered arm has a result or reason. Validate notebook JSON, saved cell completion and separate chart rendering.

## 13. Numerical assumptions and boundaries

| Choice | Initial setting | Rationale / required sensitivity |
| --- | --- | --- |
| Smoke scale | 36 arms × every four-day 2026 origin × one 30-day horizon; 2025 warmup and earlier history retained | Restrict combinations only; mature outcomes and pending late labels reported separately |
| Primary N | 6 | Source reference; smoke includes 10, later 4/7/8/10 |
| Component scale | 0–1, before selection | Makes coefficients interpretable; transform choices remain tested assumptions |
| I/V peer scale | NB10 positive leave-one-out variance prior | Preserves causal risk support; peer composition/weak support disclosed |
| K scale | Median positive absolute finite same-window K at T | Robust contemporaneous magnitude reference; no fixed arbitrary K clip |
| Default missingness | M0, separate masks | Compatibility-oriented zero contribution; MN/MA are explicit alternatives |
| Blend anchors | Halves, thirds, quarters | Broad coverage and readable ablations, not an optimality claim |
| Power map | q=0.5/1/2 | Flatter/proportional/sharper preference |
| Softmax | beta=ln(4); later ln(2)/ln(8) | Interpretable maximum raw full-range odds, not a chosen optimal temperature |
| K confidence | m/(m+30); later 10/90 | Heuristic support discount; actual dates, not filled rows |
| Risk estimator | NB10 regularised baseline; raw/source controls | Retain actual observation support, prior/floor provenance |
| Covariance support / solver | Inherit NB10 named gates/tolerances | Report identity prior, jitter, convergence and accepted risk-budget distortion |
| Constraints | $150k, budget 98%, concentration/TVL 33%, source-report-only | Existing baseline; pure and cap/deployment sensitivities explicit |
| Seeds | Reuse named 1010/2010/3010 streams; register separate covering-design seed if needed | Reproducible numerical work, no economic meaning |
| Uncertainty | NB10 horizon-aware blocks and ten-complete-block gate | No smoke inference; freeze a new contrast family for expanded searches |
| Date/annualisation conventions | Naive UTC; original daily 365 convention; 360-day one-year feature | Preserve metric parity and distinguish feature span from annualisation |

A helper must not introduce a hidden clip, minimum score, minimum allocation, age exclusion, temperature, optimiser penalty or confidence threshold. Register each additional choice, its units and its sensitivity before using it.

## 14. Completion for the next implementation request

The first implementation is complete when the component-score machinery and separate ranking/weighting contracts work, all 36 smoke arms have auditable statuses, the full-2026-grid smoke notebook runs and renders with verified 2025 warmup, the independent checks pass, and the smoke findings identify what is ready for expansion. The report must show that inverse variance and other ingredients were combined **inside scores** rather than as separately normalised allocation budgets.

Completion of the smoke stage does not mean the 139-recipe experiment has been run. Its exact proposed registry and computational scope are the next deliverable. The broader experiment is complete only after all scheduled recipes/families have results or explicit support reasons, matched ablations and uncertainty limits are reported, and subsequent replay candidates are frozen without relabelling searched history as fresh evidence.

## 15. Review status

Reviewed with Claude CLI, model `claude-fable-5-1`, on 10 October 2026. Verdict: the design is sound, with targeted specification fixes before smoke. The calendar, warmup, peer-relative rank invariant, fallback labelling, reference parity and component reconciliation clarifications have been incorporated. T27 now supplies the neutral-offset control while the smoke count stays at 36. See [the review and dispositions](10-expanded-score-allocation-review.md). These post-review edits have been checked against the review; they were not submitted for a second Claude pass. The reviewed smoke matrix has now been executed in place: 36 policies, 70 scheduled 2026 origins, retained 2025 warmup, 27 passing audits and 15 separate figures. See [smoke findings](10-expanded-score-allocation-smoke-findings.md). The 334-policy proposed Stage A0 registry and all-139 recipe inventory are materialised; broader stages remain unexecuted as specified in section 12.
