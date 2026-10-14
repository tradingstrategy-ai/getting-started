# Experiment 18 — conditional cash allocation with limited additional risk

Status: implemented and completed on 12 October 2026; all eighteen accounts, causal/execution audits and individual visual/static-preview checks passed. Reviewed twice with confirmed `claude-fable-5-1`. See [Claude contributions and review decisions](18-conditional-cash-allocation-review.md).

Proposed notebook: `18-backtest-conditional-cash-allocation.ipynb`.

## Goal

Use spare capital when the expected additional profit justifies its risk. Avoid mechanically filling every available slot or maximising invested percentage. Find an interpretable rule that improves net profit/CAGR while retaining competitive Sharpe and drawdown. Six positions is a control, not a demonstrated optimum. Position count should increasingly follow opportunity and risk, subject to an explicit operational ceiling.

Start with a small mechanism experiment. Preserve the established score and core strategy, add an economically motivated cash admission/sizing rule, and isolate whether forecasting actually adds value. Do not repeat the 139-score search or introduce another feature-engineering project.

## Evidence and hypotheses

Read [NB08 findings](08-score-forecast-findings.md), [NB10 findings](10-portfolio-snapshot-findings.md), [NB11 findings](11-weighting-sizing-findings.md), [NB17 findings](17-capital-allocation-findings.md) and the [NB17 implementation plan](17-capital-allocation-plan.md).

- NB17 greedy/joint score optimisation reduced September cash from 48.9% to about 1.8%, but fresh-2026 CAGR fell from 51.35% to about 32–33% and drawdown worsened from 6.08% to 15.40%. We can deploy cash; the selection/sizing objective needs improvement.
- Four-slot overflow reduced September cash to 4.8%. It underperformed in fresh 2026 but improved full-history returns. An unconditional rule is not consistently superior.
- The admission-aware core alone lost $4,507 versus exact C-W in 2026. Treat it as a separate control so new overflow is not blamed for this inherited difference.
- NB08 return IC was weak and changed sign across quarters. Learned absolute floors rejected no actual entries. A threshold must be evaluated on the affected marginal opportunities, not on mostly irrelevant low-ranked vaults.
- Missing-score exclusion reduced long-period returns. Missing, finite-zero and finite-positive scores must remain distinguishable.
- Risk ordering has been more predictable than future mean return. Use this evidence to prioritise a simple risk-only control and conservative allocation over a sophisticated return optimiser.
- Correcting partial-trim fees reversed NB17's small 2026 exit-delay advantage. The corrected fee convention must be shared by all primary NB18 comparisons.

Hypotheses: (H1) limiting additional risk improves on unconditional overflow; (H2) score-conditioned admission improves on the same risk-only allocation; (H3) gradual sizing improves on a binary gate; (H4) additional positions can be useful without displacing a profitable core; (H5) any benefit survives missing/sparse-history handling, costs and contributor concentration checks.

## Fixed contracts and replay periods

1. Freeze NB17 archive, source module, universe, observation-time NAV pricing, framework versions and fingerprints. Inspect current files without silently refreshing any input. All arms use identical inputs.
2. Fresh 2026: `[2026-01-01, 2026-10-05)` naive UTC. Full history: `[2023-03-01, 2026-10-08)`, final archive day partial. Each starts with $150,000. Keep all earlier indicator/calibration data, including 2025; history availability must be audited rather than assumed.
3. Two-day execution decisions. Four-day forecast/calibration sample origins, anchored consistently with NB08. A monthly forecast fit is frozen until the next month; current scores and risk may update at each two-day decision.
4. Retain the four-input focal score, source `missing=True` semantics, regularised 90-day core risk, source return/TVL/permission/curator/leader-share gates, 98% investment target, 33% concentration and TVL participation limits, minimum trades and global 0.5% close floor. Do not assume 98% of headline equity equals spendable cash.
5. Use NB17's corrected partial-redemption pricing for every NB18 primary arm, preserving the other explicitly modelled costs. Reproduce saved corrected C-W and corrected four-slot overflow before interpreting new results. Also retain their legacy-fee figures as labelled historical context. No additional slippage at vault NAV; no double-charging fees already in NAV.
6. Pinned/non-redeemable positions retain engine semantics and consume slots; pending redemption proceeds are unavailable. Model fees paid and open exit liabilities separately and reconcile to reported equity.

## Candidate population and causal labels

Build a shared historical panel from the source-eligible universe at each four-day origin. Determine feasible deposit capacity with as-of state; include finite-zero and unscored vaults. Persist per-vault score, score availability, capacity, return gate, risk, actual observation count/age and core membership. Core membership is determined by the causal full-history C01 reference replay, never by a later winning strategy. At a forecast origin that is not a reference decision, use its most recent completed decision at/before that origin and current as-of eligibility/capacity; do not move a later reference decision backwards. Preserve the source cycle phase for each account and record the forecast/reference phase difference. Every new arm may query this frozen mapping for its own current residual candidates.

The primary calibration population is feasible non-core candidates when the reference core leaves a positive executable residual. Keep all feasible candidates in this population rather than only subsequently purchased names. Give each origin equal total fitting weight and equal weight to candidates within an origin. Save a broader eligible-universe calibration as a support diagnostic; do not silently mix populations when the marginal sample is thin.

For horizon H in {7,30,90}, define simple gross NAV return `Y(i,t,H)=P(i,t+H)/P(i,t)-1`. Use the latest known actual positive NAV at/before each endpoint. Forward fill only after first observation. Labels become available only after their endpoint and required observations were available; require endpoint strictly earlier than the fit decision. When terminal support requires an actual mark on/after the endpoint, its actual availability time is also part of the label-maturity clock. Record that clock and use it in every training mask; final-archive knowledge cannot make a label mature earlier. Censor labels beyond each vault's last actual archive observation; do not extrapolate departed vaults to the archive end or drop unresolved cases without reporting their weight and signed return bounds. An archived last mark is not evidence of liquidation. Only an independently recorded terminal redemption/settlement with observable cash proceeds can resolve departure early; otherwise keep it unresolved. Track missing outcomes by score/history group, unresolved-weight bounds and first-update contribution. Forecasts fitted on resolved observations are conditional and may have survivorship bias; do not call them unconditional expected returns. If unresolved material has unbounded upside, show an unbounded upper sensitivity instead of inventing a return cap. The post-endpoint supporting observation confirms recorded survival/coverage only; it is not used as the endpoint price. No additional NAV-age veto is imposed in this first experiment. Report the actual endpoint mark age and a dense-observation sensitivity; a 30-day labelled interval may contain a shorter interval of actual price discovery. Treat 30 days as the primary forecast horizon; 7/90 are diagnostics, not alternative models selected on 2026 PnL.

Training starts as early as the frozen archive supports valid causal inputs; full-history accounts fall back to the matched core before calibration support is available. Report this activation date and time spent inactive. 2026 fits may use matured 2023–2025 data and earlier matured 2026 data. Report fixed pre-2026-fit diagnostic predictions as a check on adaptive hindsight.

## Simple score calibration and uncertainty

Keep a single pooled marginal-candidate forecast and five fixed score bands `[0,.2), [.2,.4), [.4,.6), [.6,.8), [.8,1]`, plus a separate missing-composite group. Finite zero stays in the first finite band. These bands discretise the existing [0,1] score; they are not profitable cutoffs. Do not enforce increasing expected return with increasing score.

For a new dollar bought at NAV and held for H=30 days, calculate the modelled net outcome **before** taking means or bootstrap bounds:

```
Z = Y - 0.10 * max(Y, 0) - 0.001 * (1 + Y)
```

This follows the source's 10% charge on positive redemption profit and 0.1% gross redemption allowance. Check it against the corrected source helper on worked gains/losses. It is a fixed-horizon new-deposit cost model, not an estimate of every incumbent's future cost or the full dynamic strategy PnL. Engine fees remain authoritative. Never subtract a mean fee from a gross-return lower quantile and call that the lower quantile of net return. Cash return is zero in the primary experiment.

Fit gross Y and net Z in parallel with the identical group/support/shrinkage rules, keeping gross estimates for the incumbent economic exit. Within each date, average Z over the relevant group; average these date means equally. Estimate pooled mean `mu_pool` from all marginal candidates. For supported group g estimate `mu_g_raw` and use an explicit, simple shrinkage rule:

```
B_g = number of distinct non-overlapping 30-day calendar blocks represented
block_id(t) = floor((t - 2023-03-01 00:00 UTC) / 30 calendar days)
rho_g = B_g / (B_g + 1)
mu_g = rho_g * mu_g_raw + (1-rho_g) * mu_pool
```

One pooled block is a declared shrinkage pseudocount, not an estimated number of independent samples or an empirically optimal prior. The pooled model requires 20 matured origins, ten vaults and six represented H-day blocks. A group requires ten origins, five vaults and three represented blocks; otherwise `rho_g=0`. Missing-score groups use the same rule; missingness never becomes a fabricated zero return or a default veto. Publish pooled fallback and group-specific allocation separately.

Use a 30-day moving calendar-block bootstrap, resampling all cross-sectional rows for sampled dates together, with 500 fixed-seed replicates. Recompute pooled/group shrinkage on each replicate, using original time-block support for the frozen shrinkage strength so duplicate resamples do not invent more independent history. The 20th percentile is the one-sided 80% lower estimate. This describes uncertainty in a mean, not a vault-return prediction interval or a guarantee against loss. Report 90-day block and leave-one-vault-out calibration diagnostics without choosing the trading rule from them.

Compare three admission signals in the matrix: pooled lower net estimate greater than zero, group central net estimate greater than zero, and no forecast gate. A pooled gate can only turn the whole sleeve on/off; it is not a score threshold. Group-positive regions may be disconnected and may shrink to the same pooled estimate. Report that honestly instead of manufacturing a universal cutoff or adding a monotonic constraint after seeing results.

Unsupported pooled training means no new forecast-driven residual deposits; the risk-only arm remains operational if its separate risk anchor has support. This tests whether estimation adds value. Report the entire forecast activation calendar and any intervals indistinguishable from the core-only control.

## Risk budget independent of idle cash

### Sparse-aware risk used for all new sleeve methods

Core selection/sizing remains exactly C01. For the **new allocation risk checks**, use `sigma_i = max(sigma_regular90_i, sigma_gap90_i)` with the explicit numerical convention `max(sqrt(v_regular90), sqrt(v_gap90))`. The gap estimate is log-return variance per calendar day; use its square root as a first-order fractional-return volatility proxy. This is an approximation, not an exact log-to-simple variance conversion. Reuse the existing NB11 regularised actual-update interval estimator and its peer/support rules for the gap estimate; do not replace it with a new estimator or a hand-picked peer percentile. Document the simple/log-return approximation and both components. This maximum is a conservative research choice, not a proven bound on true volatility.

If one component is unavailable, use its documented positive peer-prior fallback before taking the maximum; if there is no finite positive supported/prior estimate, do not fund a new sleeve position. Existing positions with unknown risk block additional sleeve buys until risk can be bounded. Flat carried NAV, young history or a missing score must never be assigned zero risk. Keep both observation age and actual-update counts; forward filling prices cannot create risk observations. This common risk layer differs from original core sizing, and is explicit in every new-arm comparison.

Pin both risk windows to 90 calendar days and shrinkage strength to 30 actual updates/intervals under their respective helper definitions. Use a fixed as-of source-eligible peer pool shared by reference and all treatments; evaluate out-of-pool held names against this same pool without adding them to other names' prior samples. The existing `sparse_risk_at()` augments its peer pool with requested IDs, so wrap its constituent calculations locally rather than blindly calling it on different arm lists. Reuse `sizing_study_data.sparse_window()` and `portfolio_snapshot_risk.forecast()` semantics. Clamp window starts to available history; negative array indices must not pull later observations into early forecasts. A flat empirical estimate with a positive regularised prior is supported; use the inherited positive prior fallback if the final estimate is zero. No valid positive empirical/prior estimate means unavailable, with no new arbitrary variance floor.

No empirical covariance is needed in the first notebook. Define the conservative marginal-volatility measure `L(w)=sum_i w_i*sigma_i`, including all core and pinned holdings. Perfectly positive correlation would give this portfolio standard deviation if the sigma estimates were correct. Sparse estimates may still miss real losses; this is not a maximum-loss guarantee.

### Lagged, normalised risk reference and high-risk brake

Use the causal **full-history C01 reference account** to build the shared risk-reference series before running treatments. At each reference decision s with positive core exposure q(s), set:

```
L_full(s) = 0.98 * L(w_reference(s)) / q(s)
q(s) = sum of reference core and pinned risky weights
A(t) = median of L_full(s) from t-90 calendar days <= s < t
```

This rescales the actual reference mix to 98% invested, rather than inventing six equal weights or filling missing slots with hypothetical vaults. It is an **infeasible-in-some-states risk reference**, not a claim that those positions can accept those dollars or that its risk is approved for live trading. Normalisation removes the mechanical fall in risk allowance caused by idle cash. The lagged median avoids increasing the allowance immediately during a volatility spike. It adapts slowly to persistent regimes, so report its drift and never describe it as a permanent absolute risk cap.

A reference decision is valid only if q>0 and every core/pinned position has a finite positive sigma under the same definitions/peer pool as treatments, including permitted prior-only estimates. Include pinned risky holdings once in both q and L; exclude reserve cash and pending proceeds. Drop invalid reference decisions from the anchor and record the cause, without replacing them with zeros. Require 30 valid distinct reference decisions within that trailing window. Prior to support, no new residual buys; continue core-only. Use all available pre-2026 reference history for the fresh-2026 account. The same A(t) is used by all new arms in both replay periods; its dependence on the full-history reference's holdings is disclosed. Never use a future reference decision, future normalisation or a fitted 2026 quantile.

For each arm's **own same-state funded core** w and total equity E, define:

```
T(t) = k * A(t)
J(t) = max(0, T(t) - L(w))
sum_i x_i*sigma_i <= J(t)
sum_i x_i <= min(executable_residual_dollars/E, 0.25)
0 <= x_i <= min(remaining_executable_capacity_i/E, 0.05)
```

Primary `k=0.75`; paired research sensitivity `k=1.00`. These are 75%/100% of the lagged hypothetical fully invested reference's marginal-volatility measure. They are not forecasts that realised volatility, Sharpe or drawdown will match it. When current core risk already consumes T, J is zero: no new sleeve exposure is permitted and redeemable sleeve holdings are reduced as execution permits. The core itself is not forcibly reduced, so this brake limits **additional** risk and does not guarantee safety of the whole strategy. With similar reference/current risk composition, k=.75 tends to allow new residual exposure mainly when core cash is around 25% or more; most other dates can legitimately match the core. This is an approximate interpretation, not an exact cash threshold. Record conditional opportunity results and whole-period economics together.

Keep the 25%-of-equity sleeve ceiling and 5% per-residual-vault ceiling. Reject the suggestion that volatility alone makes these redundant: a low estimated sigma cannot establish safety against a vault failure or discontinuous loss. These are provisional research loss-exposure limits, not user-approved production tolerances. At 50% simultaneous sleeve loss the 25% ceiling still permits 12.5% account loss; at full loss it permits 25%. Display those mechanical stresses explicitly. Binding sensitivity diagnostics at smaller/larger limits show whether these choices dominate; do not add a grid of engine runs.

All x denote the total desired residual sleeve, including retained residual positions, not just today's purchases. Existing sleeve risk consumes J before any new buy. Do not subtract current sleeve holdings in both the core-risk term and the residual budget. Pinned former-sleeve positions count once with core/pinned risk and use slots; unknown or excessive pinned risk closes new admissions and is reported as an unenforceable inherited exposure.

### Relative sizing and genuinely gradual total deployment

First execute the common retention/mandatory-trim calculation below, obtaining retained residual weights r. Deduct r from total sleeve cash/risk/slot allowances exactly once. For risk-only and binary-gate policies, form fresh incremental capped inverse-volatility targets, `xbar_i=min(c_i,tau/sigma_i)`, where c includes remaining sleeve/capacity limits after r. Find the largest tau satisfying remaining cash and marginal-risk budgets. This equalises marginal risk contributions before saturation and avoids squaring a possibly underestimated volatility. Inverse volatility is a new sleeve rule only; the core's established regularised inverse variance stays fixed.

For the gradual policy, start from the **same positive-group-forecast full-remaining-budget increments xbar**. Let `a_i=mu_g(i)` be the central net 30-day forecast, `G=sum_i xbar_i*a_i`, `L_base=L(w+r)`, `L_extra=sum_i xbar_i*sigma_i`, and H=30. Set:

```
alpha = clip((G - H*L_base*L_extra) / (H*L_extra**2), 0, 1)
x_desired = r + alpha*xbar
```

If L_extra is non-finite or non-positive, alpha is zero and the reason is recorded. Use explicit finite checks and stable arithmetic; numerical tolerances cannot act as an undeclared economic hurdle. This maximises the one-dimensional conservative quadratic-growth approximation

```
f(alpha) = alpha*G
           - H/2 * ((L_base + alpha*L_extra)**2 - L_base**2)
```

The one-half coefficient comes from the second-order log-growth approximation, not a coefficient tuned to the best backtest. The linear H scaling assumes daily variance adds over the horizon; stale marks, serial correlation, jumps and non-small returns weaken this approximation. Report forecast/realised risk and stress outcomes rather than presenting it as an exact Kelly allocation or future CAGR forecast.

Unlike normalising `advantage/variance` to fill the risk allowance, alpha controls **total** deployment: a tiny positive forecast may allocate nothing, or only part of the available budget. The formula is a proposal for fresh residual dollars and target risk. Incumbent retention/exit costs below can prevent immediately reaching x_desired; record desired versus retained versus executed exposure separately. Do not count modelled exit charges again at each two-day rebalance.

Worked fixture: L_base=0.005 daily, L_extra=0.002, H=30. At G=0.0002 alpha=0; at G=0.00036 alpha=0.5; at G=0.0006 alpha=1. These G values are expected net portfolio return contributions, not vault CAGR. Alpha may spend most dates at zero or one; report the fractions at zero, strictly between zero/one, and one, both by decision count and by feasible dollars. Do not claim gradual sizing is active when it is numerically a binary policy. Verify the arithmetic and how target floors change executable alpha.

### Deliberately deferred

Empirical covariance, a multidimensional quadratic optimiser, and fully adaptive replacement of the protected six-name core remain separate follow-ups. The first notebook tests conditional residual deployment with conservative risk accounting. It cannot establish that six core positions is optimal. If the operational ceiling binds or the core blocks attractive substitutions, quantify those opportunities and write an explicit next-stage amendment rather than silently extending this matrix.

## Entry, retention and execution

Evaluate existing-plus-new residual holdings on every decision. Keep a separate ledger of core membership, sleeve role, actual held status, promotion and pinned status. A promoted sleeve vault must not be sold and rebought; one vault receives one final net target and one net trade direction per decision.

Retain source gates and core-first funding. Source-required exits occur as usual. When core funding or hard sleeve risk/exposure/capacity limits require selling, those constraints override retention. Trim redeemable residual holdings by lowest current score then address, enforcing source minimum trades/full closes and recomputing final net proceeds. Use the same order in all new arms; do not add a fee-minimising order to one arm as an unnoticed treatment.

Binary gate failures block new deposits and top-ups, and do not automatically liquidate holdings. To avoid indefinite retention of an adverse forecast, use the same scenario-based economic exit in all forecast-exit sleeve arms. For an incumbent's current gross NAV value V and remaining source cost basis K, define:

```
F(V,K) = 0.10 * max(V-K, 0) + 0.001 * V
N_now = V - F(V,K)
N_hold(Y) = V*(1+Y) - F(V*(1+Y), K)
Delta_hold = expected(N_hold(Y)) - N_now*(1+cash_return_H)
```

Apply the current score group's **central shrunk empirical gross-outcome distribution** to this nonlinear payoff: average per date and mix the group and pooled expected payoffs using the same rho/support as admission. Do not apply the fee to a mean return. If pooled training support is absent, the exit forecast is unsupported and cannot trigger a voluntary exit. Sell an otherwise eligible residual incumbent when Delta_hold<0. Use the same group/pooled fallback in every forecast-exit arm, regardless of its entry gate. Remaining cost basis uses the source helper and actual fills. At Y=0 and zero cash return this comparison is exactly indifferent; the same accrued charge is not counted as a special hurdle against selling today. Verify fixtures for gains, losses crossing cost basis, and flat outcomes.

This is a fixed-horizon hold-versus-cash heuristic with the inherited fees; it is not optimal stopping and does not model intervening turnover or reinvestment after exit. Record triggers and realised holding durations. Gross/new-dollar admission outcomes and incumbent payoff forecasts intentionally differ because cost basis differs. For top-ups, the new-dollar net forecast remains a labelled incremental-cost approximation; the engine computes the real pooled-basis cost.

R01 therefore has uncalibrated **entry** but forecast-based exits; R00 is the fully forecast-free comparison. Source-required exits, core funding and hard sleeve constraints take priority over voluntary forecast exits. After all required and voluntary reductions, freeze retained weights r and deduct their cash/risk/capacity/slots once before constructing fresh increments.

The gradual alpha rule limits fresh deployment and voluntary increases. Its lower target alone does not force additional incumbent sales beyond this common exit rule. Retained holdings occupy cash, risk, single-name and slot budgets first; scale only remaining proposed increments. Log this hysteresis and time since last positive forecast. Do not claim realised holdings exactly maximise f(alpha).

Preserve NB17's core-first final-proceeds funding and global 0.5% denominator protection. Recompute combined targets after every discrete removal, floor, fee or funding change. Check the resulting executable weights and risk, not just the continuous proposal. Hard risk-limit violations trigger a permitted larger trim/full close when a smaller trim is suppressed; if pinned liquidity prevents compliance, record the breach, prohibit new residual buys and retain source handling. Never silently weaken a risk limit or liquidate the protected core to make a chart look compliant.

Operational ceiling: 12 total vaults, including pinned holdings, with at most six residual names. This is a ceiling, never a target. Candidate ordering for slot admission is descending source score then ascending lower-case vault address in all new arms; missing composite scores use source numeric zero for ordering, tie with finite zero by address, and retain their separate availability flag. Mandatory trims use ascending numeric score then address. Apply positive forecast gates before filling available slots and backfill later feasible candidates after dust rejection; retained positions consume slots first. Never evict an eligible retained position solely to admit a marginal score improvement. Candidate ordering is shared; compare the full feasible pool with 10/12/no-ceiling same-state proposals as a capacity diagnostic. Report excluded profitable/risk-feasible dollars. Position count can expand or contract below the ceiling; no claim of optimality follows from choosing 12.

Do not add a minimum holding period: it can conflict with a high-risk brake and core funding. Instead report actual holding duration, core-refill round trips and fee incidence. Before modelling, describe NB17 residual holding durations; retain 30 days as the registered primary target and 7/90-day calibration diagnostics. A materially different holding horizon is a documented follow-up, not an outcome-driven switch within NB18.

## Initial run matrix

Run the entire 2026 period with 2025/earlier warmup for this smoke matrix; reduce combinations, never shorten the history. Every registered arm then receives the full-history replay. Identical accounts may share execution only after exact identity is established.

| ID | Core and residual admission | Residual allocation | Risk reference k | Exit policy | Main contrast |
| --- | --- | --- | --- | --- | --- |
| C00 | Exact C-W, corrected fees; no sleeve | Existing core | Existing | Source | Historical economic control |
| C01 | Admission-aware M01, corrected fees; no sleeve | Existing core | Existing | Source | Matched core control |
| C02 | Exact NB17 M05, corrected fees | Existing unconditional four-slot overflow | NB17 caps | NB17 | High-deployment control |
| R00 | C01 + every feasible residual candidate | Capped inverse volatility | .75 | Source/core funding/risk only | Fully forecast-free cautious allocation |
| R01 | Same entry as R00 | Same | .75 | Common economic exit added | Isolate exit forecast effect |
| R02 | R01 + pooled 80% lower net estimate > 0 | Same | .75 | Common economic exit | Market-wide marginal-opportunity switch |
| R03 | R01 + group central net estimate > 0 | Same | .75 | Common economic exit | Score-conditioned admission |
| R04 | Same admission as R03 | Same relative mix, alpha limits total fresh deployment | .75 | Common economic exit | Gradual amount versus binary filling |
| R05 | Same as R04 | Same | 1.00 | Common economic exit | More risk budget for more deployment |

Nine arms, eighteen primary accounts. All new arms use twelve-slot ceilings and identical risk estimators, sleeve limits and trade machinery. The controls retain their exact six/ten-position semantics. R00–C02 is an allocation package comparison, not an isolated risk-budget effect: both slot policy and sizing also differ. R01–R00, R02–R01, R03–R01, R04–R03 and R05–R04 are the principal matched contrasts.

The number of combinations is the smoke constraint; every arm runs the complete fresh-2026 history and the complete full-history account. Deterministic matched-budget ungated/random admission **shadow** diagnostics test whether forecast gates add value beyond reducing exposure, without adding a large engine grid. They are not substitutes for executable returns.

## Evidence, decision rules and useful negative results

Primary comparison is net profit/CAGR against C01 and C00. Also report Sharpe, maximum drawdown, worst 7/30-day loss, costs, effective breadth and September/whole-period cash. Do not optimise a weighted sum of CAGR, Sharpe and cash. Show the empirical trade-off frontier and identify dominated policies.

Differences between legacy and corrected fee conventions are a systematic accounting sensitivity, not a statistical noise floor or a minimum acceptable CAGR improvement. Do not dismiss small differences using the fee correction magnitude. The inventory and retrospective curator/guard policies are inherited limitations; these experiments do not reconstruct a survivorship-free historical universe. No live risk appetite is inferred. Prefer candidates with more profit and no worse Sharpe/drawdown; if none exist, show the exact exchange of profit for risk instead of declaring a winner. Forecast risk limits are assessed against realised outcomes; report breaches and estimation error. Increasing cash usage alone cannot pass.

At each actual opportunity, record the cash-only/core reference, admitted/rejected candidate, feasible dollar amount, forecast band/support, forecast return/cost/risk, binding constraint and subsequent gross/net outcome where observable. Track dollars rejected due to negative estimate, uncertainty, unsupported history, risk budget, slots, caps, permissions, floor and fees. Categories must be ordered for an additive waterfall or labelled overlapping. Show extra-capital-weighted outcomes, not just equal-vault IC.

Measure whether gates are active on real proposals. An inactive gate cannot establish predictive value. Compare accepted/rejected score regions and overlapping uncertainty; retain no-threshold conclusion if appropriate. For the score-conditioned R03 versus R01 include a deterministic matched random admission diagnostic, conditioned on date and comparable risk/capacity, using the same accepted dollar budget. R02 is an all-candidate monthly switch, so use an exposure-matched ungated shadow instead; random cross-sectional vetoes would be meaningless there. This is a shadow diagnostic rather than another large engine matrix.

Full-history and 2026 overlap and have already been examined. Monthly training can be causal without making this untouched validation. Show quarterly contributions, leave-largest-vault-out fixed-ledger sensitivity, first-actual-update sensitivity and parameter neighbourhood rather than claiming independent significance. No fixed-ledger deletion is an executable strategy backtest.

## Notebook presentation

Header: goal in the user's terms, hypotheses, method, fixed periods, fee convention and a concise completed verdict. Every table/chart: its own subheading, brief plain-English description, then element. All chart titles include the backtesting period. Default all figures and narrative metric tables to fresh 2026; full history has a separate explicitly labelled section. Each image is separate, no collages.

Required displays:

1. Strategy logic table and all fixed/researched parameters, including slot ceiling and missing-data behaviour.
2. Matched key metrics table, coloured by profit/CAGR/Sharpe/drawdown; show all nine arms and both matched controls.
3. Separate CAGR–Sharpe, net-profit–cash and net-profit–drawdown plots; colour by risk allowance, label method, separate coincident points.
4. Separate equity curves and absolute asset-weight charts for C00, C01, C02 and distinct shortlist leaders. Cash uses consistent grey; vault colours stay consistent.
5. Quarter-by-method incremental net-profit heatmap against C01, with C00 differences in a separate table. Label partial quarters.
6. Separate daily cash, active position count and additional risk budget usage charts; explain retained sleeve versus new buys and the 2% reserve.
7. Score-band future-return calibration plot with support/uncertainty and a time table of actually used profitable score regions. Separate missing bucket.
8. Actual marginal opportunity scatter, score versus forward net return, coloured by quarter and identifying admitted/rejected. Do not plot unobservable returns as zero.
9. Admission/constraint reasons table, additive dollar waterfall only if reason precedence reconciles; distinguish snapshots from distinct dollars. Cash provenance includes capacity/slot residue, reserve, pending proceeds and guard exits. A vault-specific gate applies to that vault, not automatically to all cash; a genuine portfolio-wide emergency restriction blocks new buys in every arm.
10. Forecast versus realised risk and worst-window loss table; independent NAV update counts, young/missing cohorts and unsupported durations.
11. Fees paid, open liability, turnover and brief round trips. Compare matched corrected fee accounts only.
12. Vault-level incremental PnL and tail concentration, including curator and BTC/ETH observation-interval context using existing helpers. Report any HLP allocations as ordinary risky-vault exposure, never as cash or a guaranteed-yield substitute; identify concentration in it if present.
13. Full-history metrics/quarter or year heatmap and activation dates in a separate section. Record early all-cash/core-only periods.
14. Verdict on each hypothesis, economic compromise, remaining limitations and the smallest frozen follow-up.

## Cheap mechanism checks before engine treatments

After the corrected C01 reference and causal forecasts exist, compute one-decision **fresh-proposal shadows** on every C01 decision over the entire 2026 period, with no sleeve feedback. Save both risk caps, risk/cash/sleeve headroom, forecast-gate activity, alpha and binding limits before running new treatment accounts. This can reveal inactive or saturated mechanisms cheaply. It is not a simulated retained sleeve and cannot prove evolving accounts identical. Do not select arms on their subsequent returns or delete registered arms because the shadow appears unpromising.

Add a core-top-up shadow using the same cash, risk, admission and concentration/TVL constraints. It tests whether existing core holdings could absorb the same extra dollars, without invoking new names. Report this alongside new-name proposals; if core caps bind, quantify why breadth is needed. No execution or return claim is attached to the shadow.

Show same-state sleeve/single-name limits of 10%/2%, 25%/5% (primary), and no additional limits beyond source caps as **capacity/stress diagnostics**, not extra backtested performance. These diagnose whether provisional risk-exposure caps dominate. Record 50% and 100% sleeve losses arithmetically; do not attach invented scenario probabilities. The 10/12/no-ceiling slot diagnostic is likewise a proposal check.

Preserve the registered matrix even if alpha/gates appear inactive; exact duplicate account reuse requires whole-policy/state equivalence, not just matching a few shadows. Any later change to the horizon, risk anchor, support or limits requires a dated amendment before rerunning and is reported as another searched treatment.

## Implementation sequence and checks

1. Read local instructions and create-variant skill when implementing. Reuse NB17 engine/funding/capacity/report helpers and NB08 causal panel utilities. Keep new calibration and allocation code in small experiment-local modules (for example `conditional_cash_forecasts.py`, `conditional_cash_allocation.py`, `conditional_cash_report.py`); avoid framework changes unless a concrete shared bug requires one.
2. Freeze an explicit registry: methods, numerical constants, training rules, sampling phases, fee/data/source identities. All generated data, reviews, charts, logs and manifests go into ignored `_artifacts*` directories; research code/notebook/conclusions remain outside.
3. Build the causal panel and hand-audit labels around sparse gaps, first/last marks and monthly boundaries. Check future-data mutation cannot change an earlier fit/decision. Verify two-day origin queries use their current inputs and previously fitted coefficients.
4. Reproduce corrected C-W/M05 metrics, equity paths and fills; new C01 corrected control is also saved. Do not compare a corrected challenger with an uncorrected control.
5. Run the cheap fresh-proposal/core-top-up shadows above, recording activity without using future outcomes to change the matrix. Numerical fixtures: zero residual; no positive advantage; all-missing group; empty/zero-risk support; short history with peer prior; covariance-free risk bound; cap saturation; core floor protection; pinned slot; retained sleeve over new budget and exact once-only risk deduction; invalid/young pinned anchor; alpha 0/0.5/1; incumbent net hold versus redeem now; scarce final net cash; minimum ticket; a promoted core member. Check the formulas with worked numbers before engine runs.
6. Run nine full-2026 accounts, then the same nine full-history accounts. Save per-cell outputs with `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`; suppress noisy saved streams while preserving terminal progress.
7. Validate cash conservation, known as-of fills, target/funded core preservation, slot/cap/risk limits at proposal and execution, PnL reconciliation, sparse support and fee accounting. Flag discrete-trade residual violations; do not call a pre-trade bound an executed risk guarantee.
8. Inspect every chart separately and static-preview the completed notebook. Update `summary.md` and write `18-conditional-cash-allocation-findings.md`, including failed/inactive rules.

## Numbers and assumptions registry

| Choice | Reason | Interpretation and required check |
| --- | --- | --- |
| 30-day primary; 7/90 diagnostics | Existing marginal-return research framework | Actual holding-time mismatch remains visible; no searched horizon |
| Five 0.2-wide score bands + missing group | Simple discrete existing-score calibration | May all shrink to pooled; do not force a useful score threshold |
| One pooled block shrinkage pseudocount | Explicit modest regularisation | A modelling assumption; compare unshrunk/pooled calibration descriptively |
| 80% pooled lower estimate; 500 block samples | Cautious opportunity-wide switch | Not an individual-loss guarantee; show inactivity and sampling sensitivity |
| 20 origins/10 vaults/6 blocks pooled; 10/5/3 group | Minimum support | Research floors, not proof of precision; distinct blocks are not independent observations |
| 90-day risk-anchor history; 30 actual reference decisions | Stable lagged reference with support | Same archive/reference for all arms; anchor adapts and can still become high |
| k=.75/1.00 | Small conservative risk/deployment comparison | Fractions of hypothetical fully invested reference; not approved live tolerances |
| max(regular90, gap90) volatility | Reduce reliance on artificially flat carried NAV | Shared research risk layer; inherited core unchanged; inspect prior-driven risk |
| 25% sleeve / 5% individual residual exposure | Limit damage that low sigma may conceal | Declared provisional limits; joint 50%/100% loss stresses shown; smaller-limit shadows |
| Perfect positive correlation | No unearned sparse-data diversification credit | Upper bound only conditional on adequate marginal forecasts |
| Growth coefficient one-half and H scaling | Second-order growth approximation | Not exact CAGR/Kelly; investigate jumps, serial dependence and zero/tiny-advantage cases |
| Twelve total slots | Bounded operational work beyond six | Report 10/12/unlimited feasible shadow differences, without claiming best N |
| Scenario net-redemption economic exit | Compare selling now with holding under identical accrued-fee accounting | Common matched forecast exit, with fully forecast-free R00 control; still a horizon heuristic |
| Corrected partial fees and zero cash yield | Comparable economics with NB17 sensitivities | Preserve modelled-cost qualification and old figures as context |

## Review scope

Claude is asked to challenge the formulas, activation, risk anchor, soft total deployment, missing/sparse-data treatment and economic interpretation; contribute simpler alternatives; and identify hidden assumptions. Review documents must distinguish accepted suggestions, qualified changes, rejected assertions and deferred ideas. Raw review prompts/responses and draft hashes live in ignored artefacts. No review suggestion changes historical data or replaces a missing redemption observation with an invented payout. Both reviews confirmed the requested model. Final focused-review corrections were incorporated locally and are itemised in the linked review record; no third CLI review is claimed.

## Implementation notes — 12 October 2026

Executable audits exposed two mechanical problems in the first implementation. Those outputs are superseded, and the corrected policy receives every registered account again. These are correctness fixes, not an economic parameter search:

1. A core member being demoted is an existing residual incumbent, not a fresh buy. Include it in retention, risk and minimum-trim handling. When a mandatory reduction is below the source sell ticket, request the permitted full close and block same-decision re-entry. Promotions remain held positions rather than close/reopen round trips.
2. The source captures `reference_equity` before refreshing accrued exit fees, and its refreshed mark differs from the generic post-trade valuation quote. Risk/exposure constraints need a conservative bound on the actual denominator used after execution. The framework creates a separate valuation pricing instance without the source’s instance-level single-fee wrapper. Use the generic class valuation quote for every current position, then bound the possible additional buy marking deductions using its actual per-pair rates:

```
E_v = current cash + sum_i quantity_i * generic_sell_valuation_price_i
b_i = max(0, 1 - generic_sell_valuation_price_i / observed_gross_NAV_i)
D_core = sum_i max(core_target_i - old_marked_value_i, 0) * b_i
D_sleeve = 0.25 * E_v * max_feasible_residual_i(b_i)
E_safe = E_v - D_core - D_sleeve
```

Use `E_safe` for new sleeve risk/exposure limits; preserve the core's original dollar targets. The sleeve bound follows the registered 25% exposure ceiling, rather than an invented numerical haircut. Check that actual post-trade marked equity is at least `E_safe` and that actual gross sleeve risk/exposure/slots obey their limits. Convert marked target dollars conservatively to gross NAV exposure using the current source accrued-fee factor; economic forecast advantage still uses the dollars actually proposed for purchase. Reference risk normalisation uses actual gross NAV holdings.

Framework revaluation uses the protocol pricing route without the source instance-level wrapper. Pair tax can persist on a closed vault and affect a reopened position’s mark, while the fresh source wrapper falls back to the capital fee for an as-yet unrefreshed pair. Mirror the routed BacktestPricing class quote, including that current cached pair tax. NB18 mirrors that generic valuation quote for constraint consistency; the registered controls retain their exact saved valuation/cost conventions. Report gross NAV equity, estimated single-fee liquidation value and the engine's marked equity separately. A broader correction of that valuation convention requires a separately labelled comparison, not a silent change to the NB17 controls.

Replicated NB17 corrected C02 control positions have median closed lifetimes of four days in fresh 2026 and twelve days over full history. These include core positions, rather than only overflow. The implementation retains the registered 30-day primary horizon and displays this mismatch before fitting; no horizon is switched on realised profit.

### Completed implementation evidence

The completed notebook and [findings](18-conditional-cash-allocation-findings.md) report all nine registered arms for both periods. The same findings are included in `summary.md`. Final numerical generation: `5cc3a1f2f6b3a296361141bd9db6d7add053d03620cd03992e8c6921b3ac6437` under the ignored NB18 artefacts. Superseded debugging generations are not used for conclusions.

- Six completed code cells; no saved error outputs.
- Corrected C-W and unconditional-overflow control equity reproduce exactly; other parity errors are floating-point roundoff.
- 16,021 NAV fill checks; 4,614 executed treatment decision checks with zero risk/exposure breaches and every conservative equity bound valid.
- Core-preservation, capacity, slot, retained-accounting, future-label mutation and strict-maturity checks passed; cash and position-PnL reconciliation errors below $0.000001.
- All 29 images inspected separately; label overlap, duplicate line legends, symmetric-log ticks and inactive-alpha axis corrected. Static browser preview: 42 tables, 29 charts, no broken images.
- Negative economic verdict retained: no new conditional method improves profit, Sharpe and drawdown against the matched core on both researched periods. No profitable admission threshold is established in 2026, when forecast-gated fresh deposits are inactive.
