# Experiment 17 — better capital allocation

Status: implemented and executed in [NB17](17-backtest-capacity-aware-allocation.ipynb): 28 primary accounts plus 6 shared fee sensitivities. See [findings](17-capital-allocation-findings.md). The two planning reviews used confirmed `claude-fable-5-1`.

## Goal and economic question

Find a capital allocation method that earns more net profit than our existing strategies. Investigate redistribution within a basket, conditional extra positions, capacity-aware replacement and joint selection/sizing. An improvement in deployment is a mechanism, not the final objective: measure profit, CAGR, Sharpe, drawdown and costs together.

Proposed notebook: `17-backtest-capacity-aware-allocation.ipynb`. Start with a small, predeclared set of combinations covering different mechanisms. Do not run a Cartesian grid over selectors, scores, risk windows, thresholds and position counts.

## Evidence to explain

NB16 retains six positions. Its C-W arm returned 51.35% CAGR / 2.23 Sharpe / −6.08% drawdown in the fresh 2026 account, and 30.96% / 1.73 / −10.33% over full history. September cash remained about 49%. G-W is stronger in fresh 2026 but has a deeper full-history drawdown; retain it as saved context, not another risk-estimator search.

The NB15 A decision on 20 September had $194,853 deployable capital but only $72,560 combined capacity across its six selected vaults. Admission checks reduced the target further to $71,206. Across September's repeated decision snapshots, capacity limits explain 96.9% of A's summed target shortfalls. These sums are neither lost profit nor distinct idle dollars.

V8–v10 already had a residual extension. Its saved comparison underperformed hard-six v11, and increasing fixed breadth in NB07 also harmed the four-input strategy. Additional positions must therefore compete against retaining cash. The source extension is a necessary historical mechanism control, not a novel proven solution.

References: [NB16 findings](16-waterfall-comparison-findings.md), [September diagnosis](15-september-cash-analysis.md), [earlier mechanisms](earlier-capacity-allocation-audit.md), [NB07 breadth](07-score-position-count-analysis.md).

## Fixed inputs and reference policy

- Pin the NB16 repaired archive, source module, framework commits, universe, guard and pricing convention. Record hashes and all differences before execution. Never silently refresh data for only some arms.
- Each account starts independently with $150,000. Two-day decisions, 98% investment target, 33% portfolio concentration and 33% vault-TVL participation, existing TVL/return/guard/leader-share gates and trade thresholds are unchanged.
- C-W is the main method benchmark: the existing four-input ranking, regularised 90-day inverse variance and risk-priority waterfall. A and deployed v11 remain matching saved performance references.
- Preserve the source core selector and its exact rank hysteresis in all methods except explicitly labelled selection treatments. Do not replace it with naive top-six sorting. Existing entry/exit rank settings are 6/8; source tie-breaking uses vault address.
- Keep `missing=True`, causal sparse-NAV handling and the current regularisation package. Do not rescale the score, recalibrate forecasts or introduce age filters during this allocation experiment.
- Retain source modelled redemption costs and the inherited partial-trim fee convention for comparability. Identify the latter as a known limitation. Apply NB16's final-net-proceeds funding safeguard to every new arm; it must be a no-op on valid control queues. No invented vault slippage.

### Score formula and missing values

For finite components, using returns in fractional units and `clip(u)=min(1,max(0,u))`:

\[
s_i=0.48\,\operatorname{clip}(\mathrm{CAGR}_{360,i}/1.0)
 +0.32\,\operatorname{clip}(\mathrm{Sortino}_{45,i}/3)
 +0.10\,\operatorname{clip}(\mathrm{CAGR}_{180,i}/1.0)
 +0.10\,\operatorname{clip}(\mathrm{Sortino}_{30,i}/3).
\]

Use the actual compatibility helpers, including the legacy 45-day calculation. When an active component is unavailable, retain the source undefined-composite behaviour: the selector receives an unscored value represented by zero. Do not fill missing components individually with zero and accidentally create a partial positive score. Save a separate `score_available` flag: observed zero and unavailable zero are different states. Source eligible unscored entries remain supported unless a method explicitly tests a quality screen.

### Risk formula

Reuse C's existing helpers, rather than implementing an approximate copy:

\[
\gamma_i=\frac{m_i}{m_i+30},\qquad
\widetilde v_i=\gamma_i\widehat v_i+(1-\gamma_i)v_{\mathrm{peer},i},\qquad
a_i=1/\widetilde v_i.
\]

Here `m` counts actual daily observation updates within 90 calendar days, not filled days. The leave-one-out positive peer prior, partial-window support, missing-risk handling and basket equal-weight fallback are exactly C's. Formula above describes the positive-prior case; empirical-only and unusable-prior fallbacks must follow the helper. No new arbitrary variance floor.

## Decision-time dollar model

All notation below is per decision. Use source budget units throughout.

- `B`: fresh deployable budget after the source reserve and non-redeemable/pending capital handling. Obtain it from `calculate_v11_fresh_deployable_capital`; do not reconstruct it as 98% of headline equity.
- `h_i`: currently held, redeemable value in those same sizing units. Locked positions are pinned outside the allocatable budget and consume position slots where the engine requires it.
- `d_i`: permissible **additional** deposit amount at this decision, including guard, leader-share, permission and any applicable amount limits. A blocked top-up has `d_i=0`; its redeemable incumbent is not automatically liquidated. An unbounded authorised amount is infinity. Missing amounts follow the repaired reader/source policy; neither NULL nor a missing independent observation clock automatically means zero or unlimited.
- `c_i`: maximum feasible target before trade thresholds, for an allocatable vault:

\[
c_i=\min\{0.33B,\;c_i^{\mathrm{TVL}},\;h_i+d_i\},
\qquad c_i^{\mathrm{TVL}}=\text{the source size-risk model's accepted dollar ceiling}.
\]

For ordinary valid data `c_i^{TVL}=0.33 TVL_i`; use the actual framework method and historical as-of TVL. Capacity missingness and deposit permissions are not NAV series and must not be forward-filled using the price rule. Existing above-cap positions and pinned holdings follow source enforcement/drift semantics and are reported; do not claim every realised holding is always below a target cap.

Targets satisfy `0 ≤ x_i ≤ c_i` and `sum(x_i) ≤ B`. The target residual is `B−sum(x_i)`. Actual wallet cash also reflects the reserve, pinned settlement capital, minimum trades, marking and costs; report it separately.

The aggregate upper bound for a selected set `S` is:

\[
D(S)=\min\{B,\sum_{i\in S}c_i\}.
\]

This is a continuous target bound, not a promise of executable fills. Final planned buys must also fit actual current cash plus final synchronous net redemption proceeds. Pending redemptions are unavailable funding. Admission checks and source trade floors remain authoritative after target sizing.

### Common executable-capacity pass

M01 and all redesigned methods use one as-of admission/capacity snapshot before sizing. Check unheld entries and incumbent top-ups separately; retain a closed incumbent up to permissible held value. Remove zero-headroom candidates from new allocations, rather than excluding their existing holdings. Cache the same decision's checks to avoid inconsistent repeated reads.

After trade thresholds/admission, redistribute a rejected increment only if another admissible target can accept an executable ticket. Recompute the planned queue and final-net-proceeds budget. Stop when no target changes by an asset raw unit, no executable ticket remains or all capacities are exhausted; detect repeated target/queue states and report unresolved slack rather than cycle indefinitely. Use exact currency rounding, not a newly tuned dollar epsilon. Record reasons for unrecovered cash. An admission error invalidates that arm; silently ignoring it is forbidden.

The source also has `min_portfolio_weight_pct=0.005`: a positive target with normalised weight below 0.5% of total accepted allocatable targets becomes a close. This differs from the incremental deposit threshold ($75 at the initial account) and the sell threshold ($750 initially). Preserve all three. Fixed-basket continuous formulas are pre-floor targets, then use the common source-compatible floor/refill pass. Report the resulting projection/floor changes; do not claim the executable policy remains the exact relaxed optimum.

## Allocation methods and formulas

### 1. Existing waterfall and admission-aware risk waterfall

M00 reproduces C-W exactly, including its current post-sizing admission behaviour.

M01 uses the same core selector and risk priority but the common executable-capacity pass. Sort by descending `a_i`, then address. With `R_0=B`:

\[
x_{\pi(k)}=\min(c_{\pi(k)},R_{k-1}),\qquad
R_k=R_{k-1}-x_{\pi(k)}.
\]

M01−M00 isolates admission/refill handling. This cannot overcome a six-vault aggregate capacity deficit.

### 2. Proportional capped redistribution

M02 keeps M01's selector and feasible capacities, but preserves proportional risk weights. Set `D=D(S)` and solve:

\[
x_i=\min(c_i,\tau a_i),\qquad \sum_{i\in S}x_i=D.
\]

Find the non-negative scale `tau` using saturation/water filling. When `D=sum(c_i)`, return all ceilings directly. When the budget or support is zero, return no new allocation. The existing equal-risk fallback applies if necessary. Redistribute only among selected admissible vaults; record original requested versus accepted targets.

### 3. Performance-priority waterfall

M03 uses M01's basket and caps but sorts by descending performance `s_i`, then address, in the waterfall recursion above. This tests score priority against risk priority. Missing/zero scores remain last with deterministic ties; no positive score is fabricated. This is different from NB16's risk-priority waterfall.

### 4. Core-preserving residual positions and quality screening

M04/M05 first obtain M01 core targets `x_core` and residual `R=B−sum(x_core)`. The core has up to six selected slots, subject to pinned holdings. Permit up to two/four **additional** positions respectively, producing at most eight/ten total held vaults including relevant pinned positions.

Scan remaining source-eligible candidates in descending performance score/address order. Skip entries with no feasible deposit or executable ticket. For each overflow candidate use the same **whole-account** concentration cap `0.33B` and TVL/admission constraints; never apply the concentration cap to `R`. Allocate residual by the performance-priority waterfall:

\[
x_j^{\mathrm{overflow}}=\min\{c_j,R_{j-1}\},\qquad
R_j=R_{j-1}-x_j^{\mathrm{overflow}}.
\]

The overflow scan deliberately considers names outside the chosen core, without adding an entry-rank cutoff; all other eligibility gates remain. Source `entry_rank=6` affects the best-entry-score retention predicate, but its subsequent fill loop can itself scan beyond rank six after rejected candidates. Do not turn that setting into a new hard gate for the reference selector.

Residual-only means no core target is reduced to fund overflow. Store core membership separately: only previous core members receive core incumbent hysteresis; previous overflow holdings compete for core entry as candidates. Split the source's shared `held_pair_ids` concept into `core_incumbent_ids` for retention/best-entry-score classification and `actual_held_ids` for admission/value handling. A top-six overflow holding counts as a possible **core entry** in the best-entry-score predicate while remaining held for deposit checks. Actual held status still governs permissions/available value, so role changes do not require an unnecessary new deposit. If a previous overflow vault enters the core, remove it from overflow first. On each decision, budget the core before overflow; overflow may be redeemed to fund the core under the existing settlement/cost assumptions. This is a dynamic policy, not a permanent ring-fenced sleeve.

Protect the core against the global 0.5% close-weight denominator too. With core accepted total `T_core` and proposed overflow total `T_over`, every otherwise retained positive core target must still satisfy `x_core,i ≥ 0.005(T_core+T_over)`. Reduce/omit overflow if necessary; never close a core position solely because overflow enlarged the denominator. Apply the same floor to overflow targets and refill eligible residual opportunities. Compare executable core trades with a same-state core-only proposal, not just pre-trade targets.

Count decisions and dollars where this protection restricts deployment. Do not write core weights using `x_core/T_core` and overflow weights using `x_over/(T_core+T_over)` into the same global `normalised_weight` field: they sum above one whenever overflow is positive. A role-specific close predicate could be a later explicit policy change, but it is not an innocuous normalisation fix and is outside this initial matrix.

For funding, obtain the core-only funded queue first. Fund overflow from the remaining net cash/proceeds. If final charges leave a deficit attributable to overflow, reduce overflow buys first; do not proportionally dilute core buys to fund an extra position. Any independent core funding defect uses the same NB16 safeguard as M01 and is logged separately. Thus all arms share the net-proceeds accounting, while overflow has an explicit core-first spending policy.

M06 uses M05's four overflow slots but imposes a scored-only quality screen:

\[
\text{admit overflow }j\iff \text{score_available}_j.
\]

Its core still follows `missing=True`; young vaults with usable component scores remain eligible. This is an explicit overflow information screen, not a minimum age or proof of positive expected return. Observed zero scores remain distinguishable from unavailable scores. Missing-score overflow remains allowed in M04/M05 as the source-compatible control. Report any no-op and reuse identical outputs rather than manufacturing distinct results.

Also calculate the originally suggested relative screen `score_available_j AND s_j ≥ min(scored core scores)` as an admission diagnostic. With a high-scoring core it may admit almost nobody; it therefore does not receive another full replay in the initial matrix. Empty scored-core support implies no admission under that diagnostic. An absolute profitability threshold requires calibration unavailable in this experiment.

### 5. Turnover-aware residual positions

M09 uses M05's core and four residual slots, but preserves eligible existing overflow holdings before opening new overflow names. Combine core/overflow role transitions into one target per vault and generate trades only once: demotion itself must not cause a sell and re-buy. This netting rule applies to every redesigned overflow arm.

After mandatory gate/cap adjustments, initial overflow maintenance is `y_j=min(h_j,c_j)` for previously held eligible overflow, including core demotions. If more than four remain, select retained names by descending score/address; gate and excess-slot exits are recorded separately. If `sum(y) ≤ R`, retain those dollars and allocate the remaining residual to eligible top-ups/new positions in score order. If `sum(y)>R`, free exactly the necessary target dollars, subject to source floors, by trimming in ascending modelled redemption charge per dollar freed, ties by lower score/address:

\[
q=\max(0,\sum_j y_j-R),\qquad
\ell_j(u)=\frac{\text{source modelled charge to redeem }u\text{ dollars}}{u}.
\]

Use actual cost-basis/fee helpers to evaluate proposed trims, including the inherited convention; do not assume losses have zero redemption costs (the gross allowance remains). Re-evaluate charges if the marginal rate changes with the trim. Free funding sequentially from one position at a time in fee order, rather than spreading a small required amount into multiple suppressed sells. If the last partial trim is below the current source sell floor, propose at least the minimum executable trim after share/reserve rounding, capped at available held value; if a full close is required instead, use the source full-close path. Recompute actual net proceeds and leave any extra liberated money in the residual calculation. Never reduce a retained core buy solely because overflow trims were proposed below a floor.

New entries fill only spare residual/slots after maintenance. No same-decision sell/re-buy of the same overflow target to undo rounding: net all targets, rerun funding/floor checks and detect repeated states. If the maintained-overflow proposal still cannot fund the feasible core-only queue, close additional overflow in the same order and omit new overflow buys; if settlement alone prevents funding, source pinned-budget handling takes precedence and the limitation is recorded. This is an incumbent-maintenance and fee-aware trim package, compared with score-first M05; do not attribute its result to trade ordering alone. Reordering an unchanged complete sell queue would not change its total fees.

Distinguish charges paid from charges deferred. Report the source model's accrued redemption liability on open positions at period end and verify whether reported equity already incorporates that liability. The source refreshes sizing marks to redeemable value, but final/reporting marks must be checked rather than presumed. Show gross NAV equity, modelled liability and net redeemable equity consistently; do not deduct a liability a second time when already included. Delaying a charge is not proof that the charge disappeared.

This arm gives overflow an explicit holding policy without adding an arbitrary rank band, score margin or fee-versus-score coefficient. It can preserve a poorer-scoring incumbent for too long; core promotion, eligibility gates and capacity demands still act. Its exposure/quality and turnover outcomes must be reported.

### 6. Capacity-aware incumbent retention within six slots

M07 begins from the final source-proposed six-position core, after its admission backfill. An outgoing incumbent may be retained only if it remains source-eligible, redeemable and within exit rank 8. The source does not pair exits and entrants, so enumerate each eligible outgoing incumbent `i` against each newly selected non-incumbent `j`, and calculate with the same `B`, snapshot and caps:

\[
\Delta D_{j\rightarrow i}=D((S\setminus\{j\})\cup\{i\})-D(S).
\]

Accept the pair with greatest strictly positive recovered capacity; tie-break by lower proposed dollar turnover then address. Recalculate after each reversal and stop when no positive pair remains. Keep the source choice when capacities tie, including when both baskets already saturate `B`. Only reverse actual post-admission changes, not an eviction later undone by source backfill. Re-evaluate statelessly at each decision; no retention clock or expanded rank band is introduced.

This changes hysteresis only to avoid a capacity-reducing replacement inside the existing incumbent band. Do not retain a vault failing source eligibility or extend the band; guard/deposit restrictions govern new capital according to the source. It is a capacity-first hypothesis, not evidence that the incumbent has a better expected return. M07 uses M01 risk-priority sizing after selection.

Important source detail: rank at most eight alone does not guarantee retention. The source also requires `NOT(best_entry_score > incumbent_score + minimum_score_improvement)`; its improvement setting is zero. Thus a rank-seven/eight incumbent can be outgoing and M07 is not necessarily a no-op. Count actual qualifying reversals. Do not widen the rank band on the basis of an incorrect source assumption.

With six core incumbents and strictly ordered scores, at least one higher-ranked top-six name is outside a rank-seven/eight incumbent's core, so the best-entry override generally defeats band protection. Exact ties can preserve protection, including **positive clipped-score ties**, not just missing zeros. A blocked entrant can also cause the held incumbent to return through source admission backfill. Add a common-state audit of in-band incumbents, tie/predicate protection, rejected entrants, actual replacements, M07 policy retentions and returns within two decisions. Interpret M07/M10 activity from these counts rather than declaring hysteresis universally inert.

### 7. Greedy joint basket improvement within six slots

M08 starts with the M01 core. For each permissible one-for-one swap with another source-eligible, depositable candidate, run the L01 fixed-basket score allocation on the trial basket, apply the common floor/feasibility pass and calculate:

\[
J(S)=\sum_{i\in S}s_i\,x_i(S)/B.
\]

Choose the swap with the greatest strictly positive `J` improvement beyond declared solver precision. Resolve ties by lower proposed dollar turnover, then address. Repeat until no improving single swap remains, using a visited-basket cache. Use the attained L01 allocation plus the floor/feasibility pass for final sizing. Search all eligible candidates rather than an arbitrary top-20 pool, with no new entry-rank truncation. Pinned positions cannot be swapped. Incumbents may remain under source gates. Freeze per-vault inputs/risks across trial baskets from the same pre-decision eligible pool and eligible held names; changing a trial basket must not silently change its peer priors.

`J` is **score-weighted deployed capital**, a transparent selection proxy. It is not forecast dollar profit. Cash has zero proxy value; unscored vaults cannot increase the primary objective. Consequently this method can prefer scored candidates to young unscored core members even though they remain eligible. Disclose that economic preference and their invested shares. The method can sacrifice score per invested dollar for more exposure and incur costly swaps for tiny proxy improvements: the primary objective deliberately has no invented conversion from scores to fee dollars. Evaluate actual net costs/profit; M10 separately tests turnover restraint.

M08 stops at a local optimum of its trial-allocation heuristic, not necessarily of the full mathematical programme. Report candidate count, evaluated swaps and attained objective. If `B=0`, retain source handling and skip the objective. M08 and M11 share the score objective and feasible target domain; floor projection can make the heuristic's inner allocation suboptimal, whereas M11 explicitly encodes target floors. Compare feasible objective gaps separately from final post-band/funding execution outcomes. Do not claim the methods have identical realised queues or that a gap isolates only the outer search algorithm.

### 8. Fixed-basket optimiser as a cheap diagnostic

L01 keeps a specified basket but chooses target dollars by linear optimisation:

\[
\max_x\ \sum_i s_i x_i/B
\quad\text{subject to}\quad 0\le x_i\le c_i,\quad\sum_i x_i\le B.
\]

This objective uses the same proxy as M08/M11. Resolve primary-optimum ties by minimising dollar turnover `sum(abs(x_i−h_i))`, then deterministic address ordering. Lexicographic stages do not introduce a score-versus-turnover penalty coefficient. Numerical tolerances are declared solver precision, not strategy thresholds. A sorted fill for positive scores provides the analytical solution; use the LP solver only to check/handle tie stages where needed.

For positive, distinct scores, L01 should equal M03's score waterfall before trading floors. With tied/zero scores the tie policy can differ: for a zero-score unheld vault, minimising turnover can leave residual cash while M03 invests it. Disclose it. Run the equivalence check on common decision states and use L01 inside M08; it does not require its own full-account arm. This avoids spending a replay on a scored-only mathematical duplicate.

Q01, deferred from the smoke matrix, adds a **diagonal risk-proxy budget** to L01:

\[
\sum_i\widetilde v_i(x_i/B)^2\le R_{\mathrm{ref}},\qquad
R_{\mathrm{ref}}=\sum_i\widetilde v_i(x_i^{\mathrm{M01}}/B)^2.
\]

Use the feasible M01 targets for the same decision state as the risk reference, not targets from another evolving account. The reference itself makes the continuous problem feasible. This is convex optimisation, not a full covariance/portfolio-variance forecast: shared exposures and sparse marks invalidate an independence interpretation. Unusable risk inputs use C's existing basket fallback; if numeric risk coefficients still cannot be defined, skip this optimiser decision, use M01 and record the fallback. Do not invent a new penalty or zero-risk assumption. Defer because it does not address the six-name aggregate ceiling and requires more numerical work. The formula remains here for review and a later deliberate extension; it is not an implemented/registered active arm.

### 9. One-decision confirmation of rank-based core exits

M10 keeps M01 allocation, but requires two consecutive source-proposed rank/replacement exits before executing a rank-based core exit. With `e_i,t` indicating that the shadow source selector would exclude an otherwise still eligible core incumbent:

\[
\text{confirmed rank exit}_{i,t}=e_{i,t}\land e_{i,t-1}.
\]

Missing previous exit state counts as false. Eligibility/gate exits are immediate; non-redeemable handling remains source-controlled. Retain unconfirmed incumbents first, then fill available core slots from the source proposal, and store shadow exit predicates for the next decision. The delay is exactly one inherited two-day decision interval, an explicit hypothesis rather than an optimised duration. Do not delay a safety/eligibility exit. Source target sizing can still reduce a retained position; separately attribute delayed membership exits versus ordinary weight trims.

This tests whether the short-lived Citadel/Ace removals cost more than their replacement opportunities earned. It is a selection/turnover treatment, not a capacity constraint relaxation.

### 10. Joint six-position optimiser

M11 searches the entire source-eligible candidate universe with binary selection variables `z_i`:

\[
\max_{x,z}\ \sum_i s_i x_i/B,
\quad 0\le x_i\le c_i z_i,
\quad \sum_i x_i\le B,
\quad \sum_i z_i\le K,
\quad z_i\in\{0,1\}.
\]

`K` is six minus pinned slots. Locked positions are retained outside this optimisation. For a new unheld candidate require `x_i ≥ b_i z_i`, where `b_i` is the source's current minimum executable entry ticket; if `c_i<b_i`, remove that new candidate. Encode the close-weight floor for every selected allocatable target as `x_i ≥ 0.005 sum_j(x_j) − B(1−z_i)`. For held positions, permit maintenance below the incremental entry ticket, subject to that target floor, and apply source incremental buy/sell bands afterwards. Tie-break by lower turnover, then fewer selected positions, then address. Prevent zero-target binary slots from counting as funded positions in reports. Suppressed incremental trades mean the final queue can differ from the target optimum; disclose that distinction.

This is a mixed-integer linear programme. It jointly changes selection and sizing; use fixed-core L01 common-state targets to diagnose selection freedom, and M08 to compare global proxy search with the feasible greedy heuristic. It is an exact solution of the declared target proxy, subject to solver gap, **not an optimum for future profit**. Source incremental bands, fee funding and executed drift can still alter that target optimum. Do not add covariance, an expected-return regression or a mixed-integer risk model in this notebook. Expose solver status, runtime and objective gap. A timeout must be labelled approximate; an invalid solution must fall back to M01 and be counted.

Implement turnover tie-breaking as a second mixed-integer stage with auxiliary `u_i≥x_i−h_i`, `u_i≥h_i−x_i`, minimising `sum(u_i)` while keeping the primary objective within declared precision of its attained optimum. The further fewer-positions stage minimises `sum(z_i)` at fixed primary/turnover optima; deterministic address refinement must preserve earlier objectives. Budget and record time across **all** stages, not only the first solve. A zero-score new vault has no primary benefit and increases turnover, so it normally stays unfunded; explicitly report this preference for scored capacity despite continued `missing=True` eligibility.

Ranking by `s_i c_i` is exact only for the simplified regime where the budget is slack for the relevant chosen sets and entry/target floors do not change feasibility. It is not a general solution when the budget binds. Likewise the minimum TVL does not make entry floors redundant: permissions/amount limits can lower `c_i`, and the separate 0.5% target floor remains. Use those claims as review counterexamples, not optimisation shortcuts.

### 11. Source residual-extension and fixed-breadth controls

M12 uses the exact source residual extension with C risk weights and NB16 waterfall core: `max_capacity_assets=10`, existing 90% deployment trigger, extension `waterfall=False`, and the source residual-budget concentration semantics. Retain its one-pass behaviour rather than silently correcting it. Apply the common net-proceeds funding safeguard. Label this arm legacy; M05−M12 is a redesigned extension package comparison, not a single-variable effect.

M13 changes the core count to ten with source rank settings expanded transparently to entry rank 10 / exit rank 12; uses the M01 admission-aware risk waterfall. It has no protected six-name core. Compare M13 with M05 to examine fixed breadth versus conditional breadth. This introduces a documented hysteresis change as well as breadth; do not describe it as position count alone.

Keep cash as the residual in every arm. Do not add HLP, a yield instrument, leverage or relaxed TVL/leader-share limits here: these require a separate economic instrument or risk-policy change.

## Smoke-test matrix and run order

The smoke test uses the **entire fresh 2026 replay with all pre-start history, including 2025 indicator warmup**. Reduce combinations, not dates. All 14 predeclared arms subsequently receive the full-history run, so a short-period winner does not determine which mechanisms receive historical evaluation.

| ID | Selection | Allocation | Maximum positions | Purpose / matched comparison |
| --- | --- | --- | ---: | --- |
| M00 | Exact source core | Exact C-W | 6 | NB16 parity benchmark |
| M01 | Source core | Admission-aware risk waterfall | 6 | Admission/refill vs M00 |
| M02 | Source core | Proportional capped risk redistribution | 6 | Sizing vs M01 |
| M03 | Source core | Performance-score waterfall | 6 | Priority vs M01 |
| M04 | Protected source core + residual | Score waterfall for overflow | 8 | Two conditional positions vs M01 |
| M05 | Protected source core + residual | Score waterfall for overflow | 10 | Four conditional positions vs M01/M04 |
| M06 | M05 + scored-only overflow screen | Same as M05 | 10 | Missing-score/cash policy vs M05 |
| M07 | Capacity-aware incumbent retention | Admission-aware risk waterfall | 6 | Replacement policy vs M01 |
| M08 | Greedy proxy-improving swaps | Fixed-basket score allocation + floor pass | 6 | Global heuristic vs M01; objective gap vs M11 |
| M09 | Protected core + maintained overflow | Incumbent maintenance / fee-aware residual trims | 10 | Turnover package vs M05 |
| M10 | Source core + one-decision exit confirmation | Admission-aware risk waterfall | 6 | Rank-exit churn vs M01 |
| M11 | Joint proxy optimiser | Joint score-dollar allocation | 6 | Global proxy optimum vs greedy M08 |
| M12 | Source core + legacy residual extension | Source extension behaviour | 10 | Legacy extension vs M05 |
| M13 | Source ten-name core | Admission-aware risk waterfall | 10 | Fixed breadth vs M05 |

Fourteen methods × two periods = 28 arm/period results, plus cheap common-state diagnostics L01/relative quality screen. Q01 is deferred. Exact duplicate target rules may reuse computation only after equality is demonstrated, while retaining labelled rows. Matching M00 may reuse saved states/ledgers; a changed adapter/timing or insufficient ledger invalidates that reuse. A/v11/G-W are saved contextual rows with matched identities, not extra allocation combinations.

Predict the ceiling before execution: if a fixed basket has `sum(c_i)≤B`, risk/score waterfall and proportional redistribution all saturate its positive-capacity targets before floors. With strictly positive scores the relaxed LP also saturates them; zero-score tie rules can instead retain cash. Thus sizing interventions can improve budget-bound dates elsewhere, but cannot overcome September's chosen-basket capacity ceiling. Show capacity-bound and budget-bound decision counts, rather than treating a September no-op as a failed implementation.

1. Verify identities and M00 parity. On common historical decision states, including 20 September 2026, evaluate target rules using only decision-time information. Check budgets, permissions, slot counts, core preservation, funding, M03/L01 analytical equivalence and source hysteresis/admission-backfill counts. This small mechanism check is verification, not a performance-screening stage. Near-no-op arms still receive their registered runs, with exact-equality cache reuse only when demonstrated; do not quietly select the long-period matrix from preliminary activity counts.
2. Run every arm over `2026-01-01 → 2026-10-05 exclusive` (through 4 October), retaining all available pre-start indicator history. Do not tune based on September alone.
3. Run every arm over `2023-03-01 → 2026-10-08 exclusive` (through 7 October; archive's last day is partial). Retain all available warmup before 1 March where supplied.
4. Attribute full-account quarterly/calendar-year gains and vault contributions. Fresh 2026 and carried-account 2026 have different initial holdings/equity and endpoints; label them separately. Because turnover changes, form the union of M00 and the primary best-net-profit arm from each period, then run every unique member over both periods with a shared corrected-partial-trim-fee helper. Preserve the primary selection and correct the same helper for all sensitivity accounts. Keep these separate from legacy parity; do not silently compare corrected candidates with uncorrected controls. This adds two to six arm/period results (four when both periods select the same challenger), only after tracing the existing fee helper and establishing the actual correction; report if it was already fixed in pinned inputs.
5. Freeze a small profit/risk shortlist for later forward observation. Both historical periods have been examined and overlap; neither supplies independent validation.

## Sparse data, young vaults and operational state

- Features/risk use causal NAV forward filling after first valid positive NAV. Never fill before inception or backfill from future observations. Keep actual-observation masks, observation ages and flat-window statuses separate from daily values.
- Young vaults remain source-eligible with missing scores. Maintain peer-based risk support; no new age veto. Report overflow/new-position dollars in young, unscored and peer-supported groups.
- Archived permissions, leader share and amount caps follow repaired-reader semantics. Do not drop historical fields because an independent observation clock is absent, and do not use archive publication time as the historical permission time.
- Known blocked deposits have zero incremental capacity; they do not imply zero existing position capacity. An all-zero API cap and a NULL amount are not interchangeable.
- Use causal TVL and avoid circularly increasing target capacity with the experiment's own simulated deposit. Retain source treatment if its TVL units differ; document it for all arms.
- A forward-filled NAV permits feature calculation/marking, not proof of executable deposit NAV. Retain NB16's as-of fill convention and check actual successful fill timestamps. No silent quote-freshness strategy change.

## Economic evaluation and interpretation

Primary outcomes: final equity, net dollar profit and CAGR, compared within the same period/account start. Secondary: Sharpe, Sortino, maximum drawdown, quarterly profit, modelled fees, turnover and realised cash. No arbitrary combined profit/risk score or new drawdown cutoff.

For each matched comparison explain:

1. Additional net dollars earned or lost after inherited costs.
2. Additional time-weighted dollars deployed and September cash change.
3. Core versus overflow contribution and any profit lost by replacing incumbents.
4. Years/quarters and vaults producing the gain; identify dependence on sparse large updates and leading contributors.
5. Whether better deployment merely increased exposure, whether the proxy objective improved while actual profit fell, and whether gains persist outside September.

Record core target equality locally for M04/M05/M06 against M01 evaluated in the same state. Evolving overflow accounts change later equity and incumbents, so later whole-account core targets need not equal a separate M01 account. Track each vault's role per interval; a permanently labelled vault is insufficient when overflow becomes core. Role-attributed realised profit must use documented cost-basis allocation and reconcile; otherwise show realised PnL by vault plus descriptive role/exposure tables rather than claim an exact core/overflow causal decomposition.

For cash, distinguish: aggregate chosen-basket ceilings, denied top-ups, proportional/priority allocation slack, remaining eligible-universe capacity, quality-screen exclusions, slot restrictions, trade floors, funding corrections, reserve and pending redemptions. Repeated target shortfalls cannot be added and reported as cumulative lost profit. Check whether the whole eligible universe has enough usable capacity; no selector can overcome an aggregate universe ceiling.

Classify a challenger improving net profit in both periods as stronger historical evidence, and show one-period improvements as regime-dependent leads. Do not invent a 50% contributor cutoff, require gains outside the capacity problem's dates, or treat a relaxed-capacity replay as a profit upper bound. Concentrated/September-specific gains are findings to explain, not automatic rejections. Lower cash with lower net profit fails the economic goal. No historical ranking establishes future superiority.

## Small mathematical examples for implementation review

These are hand-specified algebra checks, not new performance experiments. Ignore trade rounding only where explicitly comparing pre-floor targets.

1. **Ceiling saturation:** `B=$100,000`, four chosen ceilings `(20,000, 20,000, 20,000, 20,000)`. Risk/score waterfalls and proportional redistribution all give those ceilings and $20,000 target residual. A fifth admissible overflow vault can use that residual; a fixed-four optimiser cannot create extra capacity.
2. **Budget-bound allocation:** `B=$100,000`, ceilings `(20,000, 33,000, 33,000, 33,000)`, risk priorities `(8,4,2,1)`, scores `(0.4,0.9,0.8,0.7)`. Risk waterfall gives `(20,000,33,000,33,000,14,000)`; proportional water filling gives `(20,000,33,000,31,333.33,15,666.67)` before rounding; score waterfall gives `(1,000,33,000,33,000,33,000)`. They deploy equally but choose different exposure.
3. **Unscored cash tie:** three ceilings of $33,000, `B=$100,000`, scores `(0.8,0.6,0)`, all initially unheld. Score waterfall funds all three. L01's turnover tie-break funds only the positive-score names and leaves $34,000. Thus even a capacity-slack LP can differ from a waterfall when scores are zero.
4. **No universal product shortcut:** `B=$100,000`, six slots; six candidates each have `(score=0.50, capacity=$33,000)` and another six each have `(score=0.99, capacity=$16,000)`. Ranking `score×capacity` selects the first group ($16,500 versus $15,840 per candidate), whose budget-limited objective is 0.50. Selecting the second group deploys $96,000 with objective 0.9504. Joint budget/cardinality optimisation cannot generally be replaced by top-six products. All capacities obey the 33% concentration cap and ordinary entry floors.
5. **Incumbent override:** a rank-seven eligible incumbent scoring 0.80 is inside exit rank eight, but a rank-six-or-better unheld entrant scoring 0.90 makes the source's incumbent-retention predicate false. A capacity-aware reversal is therefore possible without extending the rank band.
6. **Operational capacity:** a held redeemable position of $8,000 with blocked top-ups has `h+d=$8,000`, not zero. An unheld vault with sufficient TVL but only $10 permitted additional deposit can still fail the source entry ticket; minimum TVL alone cannot prove entry feasibility.
7. **Core denominator:** core targets sum to $50,000 and one retained target is $300. Its 0.6% accepted weight clears the source floor. Adding $30,000 overflow makes it 0.375% and would cause a close. Protected overflow must be limited so total accepted targets do not exceed `$300/0.005=$60,000`, or omitted; it cannot silently change the core.
8. **Role netting:** an existing $10,000 core holding becomes an $8,000 overflow target. Generate one $2,000 reduction, not a $10,000 redemption followed by an $8,000 deposit. Only the actual net reduction attracts the retained fee model.

Initial numerical solver configuration: use fraction-of-`B` variables, a primal dollar-feasibility check matching existing ledger precision ($0.000001), absolute primary/secondary objective tolerance `1e-10` in normalised units, relative MILP gap `1e-8`, and a 30-second **total per-decision** wall-clock limit across lexicographic stages. These are declared compute/precision limits, not economically tuned thresholds. If a stage cannot finish, preserve a verified feasible earlier-stage incumbent and label unfinished tie/gap stages; do not silently call it the exact lexicographic optimum. Record actual bounds, residuals, runtime and solution/tie status. Use canonical address ordering and fixed solver/library versions for reproducibility. Convert constraints back to dollars and raw reserve units for funding. Stop/reject an infeasible solver result; never hide excess behind tolerance.

## Further ideas and deliberate deferrals

- **Capital-size capacity curve:** show the continuous feasible deployment fraction for the same as-of candidate snapshots at $75,000/$150,000/$300,000 reference budgets, explicitly recalculating budget-dependent caps. This is a capacity diagnostic, not a CAGR forecast or equivalent-account profit comparison. Full engine account-size replays are a later operational-capacity study.
- **Relaxed TVL cap:** changing participation directly addresses the binding constraint but changes the risk policy. Defer. An uncapped replay is not a profit upper bound: additional exposure can lose money and change future trades. Historical unrestricted-cap results were already confounded by sparse marks.
- **Calibrated marginal expected return:** could permit a genuinely fee-aware economic optimiser, but current composite scores are not expected returns. Defer forecast calibration and any score-to-dollar conversion; do not tune a hidden turnover penalty now.
- **Risk-budget score optimiser Q01:** formula above remains reviewable, but covariance blindness and sparse variance estimates make it lower priority than selection/overflow policies.
- **External cash/yield sleeve:** requires a separately executable instrument, historical availability and realistic fees. Keep cash as the explicit alternative in NB17.

## Notebook presentation

Every element follows **subheading → short description → table/chart**. Every title/caption names its backtesting period. Default to fresh 2026; long-period results have their own clearly labelled section. One image per heading, no collages. Hide unnecessary saved stdout/progress, while the runner retains observable terminal progress.

1. Narrative strategy-difference table and formulas, stating selection changes and score-proxy limitations.
2. Colourised side-by-side 2026 key metrics table for all methods, plus matching A/v11/G-W references.
3. 2026 equity curves for M00 and deduplicated profit/risk leaders; use a small readable shortlist, not 14 overlapping lines.
4. Quarterly incremental net-profit heatmap versus M00, plus a separate paired-comparison table for M01-based interventions.
5. Separate profit/September-cash and profit/drawdown scatter plots, labelled by method family; no composite dashboard.
6. September realised cash chart for control and representatives of each mechanism, plus a compact 20 September target/capacity table.
7. September cash-reason heatmap across methods; use consistent units and distinguish per-decision dollar snapshots from realised cash percentages.
8. Position-count/effective-breadth table, overflow exposure, missing-score support, costs and funding-correction diagnostics.
9. Separate full-history metrics/equity section, and calendar-year incremental-profit heatmap. The annual table labels carried 2026 through 7 October distinctly from the fresh account through 4 October.
10. Compact leading-vault contribution table and optimiser-versus-greedy objective/runtime table; disclose ties, fallbacks and exact/approximate solves.
11. Final verdict: best economic improvement, accompanying risk, mechanism explanation, failures and a short prospective validation recommendation. Update `summary.md` after execution.

## Implementation boundaries and correctness

Reuse NB16's pricing, risk, funding, audit and reporting helpers. Introduce a small explicit policy adapter at the selection/target stage; do not rely on brittle global monkey-patching that accidentally changes core and extension sizing together. Source extension/control paths retain their documented semantics. In particular, NB16's force-waterfall model cannot be blindly used for both core and legacy extension: M12 must keep the extension's `waterfall=False`. Keep the optimiser separate from trade generation. SciPy is available in this environment; use its existing linear/MILP solvers with normalised dollars and feasibility checks. CVXPY/highspy are not currently installed and Q01 is deferred; no solver dependency is presently needed. A successful solver status alone does not validate fees or actual execution. If a dependency becomes necessary, explain it in `pyproject.toml`; no new general optimisation platform.

Common target ledgers record timestamp, budget, score/missing flag, risk/support, old value, TVL cap, deposit headroom/reason, core/overflow/pinned role, requested/accepted/final/executed allocation and residual reason. Solver diagnostics add objective, bounds/gap, iterations/time and fallback. Currency tolerances and any solver runtime limit belong in a declared numerical configuration, not hidden strategy coefficients.

Before interpreting performance, verify M00 metrics/trades against NB16 where identities match, feasibility, core preservation, appropriate held-position counts (including actual pinned/settling slot semantics), entry ticket floors, no overspending after final sell prices, no later-than-decision fill observations, and position PnL/equity reconciliation. Check M03/L01 equivalence on a positive distinct-score fixed basket and explain degeneracies. Numerical failures may not be silently presented as economic outcomes.

Generated states, logs, charts and review responses go under the ignored `_artifacts-restored-2026-10-07/17/` and `17-plan-review/` trees. Reusable Python/notebook/plan/findings remain outside. Run with the repository's observable notebook runner; inspect every saved chart and static notebook rendering. No deployment or automatic grid expansion.

## Assumptions to challenge during review

| Choice | Origin / assumption | How this experiment handles it |
| --- | --- | --- |
| Six core positions, 33% caps, 98% budget, 90-day risk / 30-update shrinkage | Existing strategy; not demonstrated optima | Fixed for mechanism comparisons |
| Two/four extra positions | Small breadth contrasts inherited from prior research | Test both; do not assume ten is best |
| 90% legacy extension trigger | Existing source rule | Only legacy M12 uses it; redesigned extension uses executable residual |
| Scored-only overflow / relative weakest-core floor | Information-screen hypothesis; neither proves profitability | Active M06 tests scored-only; stricter floor is a diagnostic |
| Score-weighted dollars `J` | Allocation proxy with cash score zero | Explicitly test proxy versus actual profit; never call scores expected returns |
| Diagonal risk bound equal to same-state M01 | Reference-relative constraint, ignores covariance | Q01 formula documented; deferred |
| One-decision exit confirmation / incumbent-maintenance overflow | Turnover restraint can retain declining opportunities | Active M10/M09; duration is inherited cadence, not tuned |
| Capacity computed from historical TVL and operational state | Source mechanics, potentially imperfect metadata | Common snapshot and reason ledger; preserve repaired semantics |
| Source estimated costs / partial-trim convention | Inherited modelling limitation | Keep comparable; report costs and qualify turnover-heavy gains |
| Entire eligible pool for optimiser/greedy | Avoids arbitrary candidate truncation | Record runtime; exactness/timeout/fallback explicit |
| Two overlapping researched histories | Development evidence | No holdout claim; reserve prospective evaluation for frozen shortlist |

## Claude contribution and review

Two successful CLI reviews used confirmed `claude-fable-5-1`, without fallback. Claude received the actual formulas, evidence and, in the focused second review, source selection/normalisation/trade-generation excerpts. Its final verdict was that the revised plan is mathematically sound and the 28 primary replays plus two to six fee sensitivities are reasonable. Review concerns about pairing, role-specific membership, executable trims, fees deferred versus paid and solver tie stages were incorporated.

Some suggestions were qualified or rejected using source/mathematical evidence: the score override can evict rank-seven/eight incumbents; positive clipping can produce protected ties; joint budget/cardinality selection is not universally top score×capacity; mixed per-role normalisation would break the global weight invariant; and relaxed capacity is not a realised-profit bound. Exact prompts/responses and reviewed hashes are in ignored artefacts. The maintained [review note](17-capital-allocation-review.md) records dispositions and remaining modelling limitations. Final clarifications were checked locally; no third CLI review is claimed.
