## 1. Flaws and risks in the plan as written

- The proposed Sortino t-statistic is not statistically valid for its stated data-generating process. [`sortino_t()`](14-evidence-weighted-plan.md:206) applies Lo’s iid Sharpe standard-error approximation to a Sortino ratio, counts only non-zero returns as \(n\), but calculates the mean and downside deviation over calendar-day returns including stale zero marks. Those are inconsistent samples. Stale marks also create serial dependence and catch-up returns, so \(n\) materially overstates the effective sample size.

- [`inverse_vol_early()`](14-evidence-weighted-plan.md:347) says `inverse_vol_min_periods` is an observation threshold, but `rolling(..., min_periods=...)` counts non-null calendar rows, including stale zero returns. It can therefore fund a young, scarcely marked vault on an artificially low volatility estimate—the precise failure NB13 warned about.

- [`expanding_cagr_score()`](14-evidence-weighted-plan.md:278) has an implicit calendar-age threshold (`days >= cagr_min_days`) but only weakly shrinks a series with very few fresh marks. It clips an extreme annualised CAGR before applying the shrinkage, so one large catch-up mark can still score positively. It also assumes `close.iloc[0]` is the vault’s true first tradable mark without auditing that assumption against the forward-filled universe.

- The NB14 screen and NB16 implementation do not rank the same thing. NB14 ranks raw, unbounded `sortino_t` and `sortino_lcb`; NB16 uses capped `sortino_t_score` and `sortino_lcb_score`. Values above the cap become ties in the backtest but not in the screen. A score can therefore pass the gate for a ranking which is never traded.

- The NB14 gate—“beats incumbent on mean forward return in both regimes and median Martin in dense”—is too noisy to be an admission test. It uses overlapping 30-day outcomes, about eight effectively independent outcomes per regime, equal-weight baskets, and no turnover, sizing, deposit-window or pool-cap simulation. It should be a descriptive screen only, not a hard branch that determines which mechanisms may be adopted.

- The plan has no genuine out-of-sample evidence. The late period is repeatedly viewed and used as an adoption constraint, so it is a further in-sample filter, not validation. NB12 and NB13 have already consumed July–September information.

- Constraint 7 is broken in code. [`placebo_sharpe_at()`](14-evidence-weighted-plan.md:534) returns `NaN` outside the observed volatility range, and [`passes_constraints_v2()`](14-evidence-weighted-plan.md:544) treats `NaN` as a pass through `ref != ref or ...`. A candidate quieter than every placebo—or noisier than the anchor—automatically passes the placebo constraint.

- The placebo table is mislabelled. In [`build_placebo_frontier()`](14-evidence-weighted-plan.md:513), the frame is sorted by `cycle_vol`, then `frontier["drop_n"] = list(PLACEBO_DROPS)` is assigned. The displayed `drop_n` no longer belongs to its row. The chart and any conclusions about “drop 30” versus “drop 50” can be wrong.

- The seven placebo observations are not necessarily a frontier. Sorting points by volatility and linearly joining their Sharpes permits dominated points and assumes a linear relationship which has no economic justification. Use a defined upper envelope or compare candidates directly with the relevant pre-registered controls.

- “Paired bootstrap CI is reported beside it” is not implemented. The inherited `panel()` bootstrap is a confidence interval for mean paired cycle-return difference, not for Sharpe difference or distance above the placebo frontier.

- The core/satellite override is not a reliable sleeve implementation. The snippet at [`core_fraction = ...`](14-evidence-weighted-plan.md:432) picks core vaults from all candidates but takes satellite vaults from the incumbent `selected` list. It can evict minimum-hold-protected incumbent positions when high-ranked core names displace them, defeating the documented hold protection in `cell14_enhanced.py`.

- The claimed `core_fraction` is only a pre-normalisation target. The subsequent beta-group cap, `AlphaModel.normalise_weights()`, 33% concentration cap and pool-cap sizing alter realised sleeve weights. A capacity-constrained core can also leave capital unallocated or move its intended allocation to the satellite. The plan must measure realised sleeve exposure per cycle; it currently calls an unenforced target “the share of the deployed book”.

- `core_fraction` is not validated. Negative values and values above one are truthy and produce negative or over-100% sleeve weights. `core_assets` is also not range-checked.

- NB18’s stated dial curve is not comparable. The grid changes both `core_fraction` and `core_assets`; `core_1.0_n6` is not an endpoint for the claimed “at `core_assets = 4`” curve. There is no `(1.0, 4)` point.

- NB18 can apparently adopt a core mechanism even if NB14 rejected its underlying `sortino_t` score. That contradicts the gate’s purpose. If it is exploratory despite gate failure, it must be DIAGNOSTIC and ineligible for adoption.

- The “pure evidence book” claim is inaccurate. `core_1.0_n6` uses the momentum gate, core ranking by raw `sortino_t`, evidence sizing, and different eligibility mechanics from NB16’s capped-score, inverse-variance selection run.

- The plateau is incomplete. NB16 varies only some parameters; it does not test the early-volatility setting, minimum CAGR history, the missing upper `cagr_weight` neighbour, or the interaction between admission and sizing. Calling seven chosen variants “every one-step neighbour” overstates the robustness test.

- NB16 has label and control ambiguity: each passing score is to run an `"evidence_selection"` centre, so rows may collide; the displayed loop does not collect states, equities, panels or rows. The later required tables cannot be produced from the shown code.

- `hidden_cohort_reach()` measures a share of positions, not the share of capital or time-weighted exposure, despite saying it measures “how much of the book went” to the cohort. It silently excludes positions absent from the life cache and returns an incomplete schema when there are no positions.

- The plan’s “same-snapshot” claim is not reproducible. It says data are downloaded fresh in every notebook, relies on a mutable `/tmp` cache from NB13, yet requires exact anchor parity with NB12. It needs a frozen archive/version/hash and a specified cache rebuild rule.

- The build assertions only establish that a splice anchor occurs at least once. `builder.py` uses `str.replace()` without asserting exactly one occurrence. The plan’s claim that every old string “must occur exactly once” is false as enforced; a future duplicate anchor would silently patch multiple locations.

## 2. Can a less capable agent execute it verbatim?

No. It supplies useful fragments, but not executable notebook specifications. Add the following sentences.

| Ambiguity or missing instruction | Sentence to add |
|---|---|
| No exact `build_14.py`–`build_19.py` content | “Each notebook build script must be included in full in this plan; do not instruct the agent to copy or adapt cells.” |
| “Copy NB13 §6 verbatim” then “change only the rule set” leaves many edits undefined | “Replace the specified NB13 cells with the complete code block below; make no other changes.” |
| NB14 does not define `indicator_series_for`, age data, score parameter retrieval, or the new reach columns | “Use these exact helper definitions and add these exact fields to each `screen_rows` record.” |
| No commands to build notebooks | “From repository root run `.venv/bin/python _build/build_14.py` through `_build/build_19.py`, in numeric order.” |
| No rule for locating or freezing the data snapshot | “Before NB14, record SHA-256 hashes and timestamps for the vault-price archive, metadata archive and life-statistics parquet; all notebooks must use those exact files.” |
| NB15 does not say how to retain placebo states/equities or cash-overlay rows | “Store every `run_variant()` result as `(label, state, equity, returns, panel)` in `runs`; build all tables and charts only from `runs`.” |
| “paired bootstrap CI” has no definition | “Bootstrap the candidate-minus-control Sharpe difference with a stationary/block bootstrap of cycle returns; report the 2.5th and 97.5th percentiles.” |
| “largest position” is imprecise | “Use `largest_contributing_vault(centre_state)` exactly, run a full masked re-simulation, and append its panel to the same verdict table.” |
| NB16 does not specify unique labels for multiple passing scores | “Prefix every label with the score name, for example `sortino_t__centre` and `evidence_composite_06__t_cap_2`.” |
| “centre-point overrides” is not machine-readable | “Write `NB16_SELECTION_OVERRIDES` as a literal dictionary in the NB16 output and copy that exact dictionary into NB17/NB19.” |
| NB17 says it holds selection fixed but does not state whether early-vol sizing remains enabled | “For NB17, `SELECTION` must include the chosen score indicator, `require_scored_candidates`, all evidence parameters and `inverse_vol_min_periods`.” |
| NB18 does not say whether a failed NB14 gate permits adoption | “If `sortino_t` failed NB14, label every NB18 result DIAGNOSTIC and prohibit ADOPT.” |
| Core/satellite attribution has no data source | “Record selected core IDs, satellite IDs and realised post-normalisation weights in `state.visualisation` every cycle, then calculate attribution from those records.” |
| “First failing item” has no ordering | “Use constraint order 1–7, then plateau, leave-one-vault-out, late period, and gate eligibility.” |
| The 90-day shadow rule lacks comparator, costs and decision criterion | “Shadow the frozen candidate and unchanged anchor on identical decision dates; include realised deposit availability, pool-cap fills, turnover and fees, and treat the 45-cycle result as monitoring evidence rather than a deployment proof.” |
| Commit instructions conflict with later plan/status/NB12 changes | “Make a final `research: NB19 close-out` commit containing the status update and comparison-notebook update.” |

## 3. Answers to open questions

### (a) Sortino t-statistic

No. It is a reasonable exploratory ranking feature, but not a valid admission t-statistic under stale marks and autocorrelated returns. Lo’s form is for the Sharpe ratio under assumptions not met here, and it does not become valid by substituting Sortino.

Use a conservative event-time statistic instead: collapse stale runs into one return when the NAV next changes, require a minimum number of independent mark events and downside events, estimate uncertainty with a block/bootstrap or HAC method, and rank by a lower confidence bound. Treat this as a shrinkage score, not a hypothesis-test p-value.

### (b) Placebo-frontier constraint

It is not well posed as implemented. The control points are not an efficient frontier, the drop labels are misassigned after sorting, the interpolation has no justification, and values outside the range pass automatically.

A 0.10 annualised-Sharpe margin can be a pre-registered practical threshold, but it is smaller than likely estimation and selection error on roughly 90 cycles. Require both a practical margin and a bootstrap-adjusted uncertainty result. Outside the control range, mark the candidate **not evaluable and failing** until the placebo design is extended pre-registered to cover its volatility; never default-pass it.

### (c) Strictly beating 2.16

Yes, it is too strict as an adoption condition and too weak statistically at the same time. A tiny observed improvement can be noise; a genuinely smoother, fully deployed strategy can fail by a trivial amount.

Make the operator’s decision a Pareto decision: require comparable deployment, capacity realism and costs; require Sharpe non-inferiority within a pre-registered tolerance; require a material ulcer/drawdown improvement; and report the CAGR sacrifice. Cash overlays remain excluded by a deployment floor close to the anchor and by comparing return per invested capital. The final outcome can be “no statistically supported adoption, but this is the explicit CAGR-versus-consistency dial”.

### (d) Out-of-sample evidence

Do not re-label July–September as out of sample: it has already informed NB12, NB13 and this plan. A historical 60-day cold start plus 90-day evidence window leaves too little untouched time for a credible validation slice anyway.

The NB19 prospective shadow is the right next gate, provided parameters, data rules, placebo method, comparator and decision rule are frozen before new data arrive. A rolling-origin historical exercise may still be reported as a diagnostic, clearly labelled in-sample.

### (e) Core/satellite sleeve

It is a sensible structural fallback because it makes the operator’s trade-off explicit rather than hiding it in a single blended score. The proposed implementation is not sound: it can violate hold protection, does not guarantee sleeve fractions after normalisation/capacity limits, does not validate inputs, and does not preserve the 33% cap in a sleeve-aware way.

Implement sleeve construction before final portfolio normalisation, reserve protected holdings first, cap and capacity-adjust each sleeve explicitly, then either reallocate unfilled capital by a stated rule or hold cash and report it. Record realised sleeve weights and test `core_fraction=0` as byte-identical anchor behaviour.

### (f) Multiplicity

No. Plateau, leave-one-vault-out, placebo and a repeatedly inspected late period are useful robustness checks, but they do not correct for the full adaptive family: score choice, gate, parameters, sizing, sleeves and later selection of a winner.

Pre-register the exact candidate family and use a stationary/block-bootstrap reality check or SPA/max-statistic test on cycle-return differentials against the anchor, with the entire family included. It will have low power, so it should prevent overclaiming rather than become a permissive pass/fail machine. Freeze one winner per family before cross-family combinations.

## 4. Missing ideas

| Idea | Mechanism | What could go wrong | Where it belongs in the track |
|---|---|---|---|
| Event-time mark-quality model | Treat stale runs and catch-up marks as reporting events; gate on mark density and downside-event count | May exclude genuinely low-turnover but valid vaults | Before NB14 |
| Hierarchical/shrinkage return estimate | Shrink young-vault return estimates towards cohort mean rather than annualising short histories | Cohort definition may conceal genuine new managers | Replace raw t-score admission |
| Availability and capacity audit | Use deposit-window history, pool-cap fill rate and realised unallocated capital | May be operational quality, not alpha | NB14 and every backtest panel |
| Sleeve-neutral placebo | Randomly assign the same number/weight of core slots, preserving all structural constraints | Random scores may not reproduce score concentration | NB18 control |
| Turnover and revision-cost constraint | Require comparable turnover, redemption delays and fees | Costs may be estimated poorly | Adoption rule and prospective shadow |
| Family-wise bootstrap | Test selected maximum performance over all pre-registered candidates | Low effective sample size makes it conservative | NB19 close-out |

## 5. Prioritised top-five changes to the plan

1. Fix the placebo constraint: preserve labels, define an actual frontier/control comparison, fail rather than pass outside its range, and bootstrap the relevant Sharpe difference.

2. Replace the Sortino “t-statistic” admission rule with an event-time, autocorrelation-aware lower-confidence-bound score; fix early-volatility eligibility to use fresh observations.

3. Rewrite NB14 and NB16 as complete executable specifications, with identical screened/traded ranking, unique labels, collected run objects and explicit downstream parameter hand-off.

4. Correct the core/satellite implementation: preserve holds, validate inputs, account for capacity and 33% concentration after sleeve allocation, and measure realised sleeve exposure.

5. Freeze a prospective anchor-versus-candidate shadow protocol and add a pre-registered family-wise block-bootstrap/reality-check analysis to NB19.