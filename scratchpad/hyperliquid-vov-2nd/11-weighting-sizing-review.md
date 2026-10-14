# Experiment 11 — Claude contribution and plan review

This note accompanies the [NB11 weighting and sizing plan](11-weighting-sizing-plan.md). Claude CLI was explicitly requested with **`claude-fable-5-1`**. The first contribution completed successfully and the returned model usage confirms that exact model, without a fallback. A second call reviewed the complete revised draft and returned **ready with specific corrections**. All three calls completed successfully and returned only the explicitly requested model. The focused final verdict was **ready**, with no material implementation blocker. No NB11 notebook or experiment has been run.

## Co-design contribution and dispositions

| Contribution or claim | Decision and reason |
| --- | --- |
| Varying L with kappa=L/3 confounds risk lookback and shrinkage | Accepted. Use kappa30 throughout the core surface, with explicitly separate L/3 companions. Different lookbacks still change actual update counts and peer pools. |
| Test returns between actual observations, adjusted for elapsed time | Accepted as a hypothesis. Add a drift-adjusted log-increment estimator with a matched-span calendar-log control, the same support and a common calendar-log peer prior. Forward filling is not assumed incorrect by definition. |
| Reproduce NB10 and inspect risk calibration by support | Accepted. Exact per-origin controls and numerical sparse/young/flat fixtures precede economic interpretation. |
| A diagonal minimum-variance QP duplicates inverse-variance redistribution | Accepted for that quadratic objective. Include an independent mathematical fixture, so a reformulation is not mistaken for a novel method. This is not a universal equivalence for capped entropy/risk-budget objectives. |
| Include selector overlap, cap binding and effective-position diagnostics | Accepted. Both selectors remain related views regardless of their measured overlap; no threshold creates independence. |
| The 98% budget and 33% caps force three positions to be capped | Rejected. Six equal positions of approximately 16.33% each are a counterexample. Actual pool caps can bind, but their activity must be measured. |
| T18 changes selection; V180 is available on only 79% of its rows | Rejected. The executed registry uses frozen v11 ranking and the minimum for sizing. The 79% statistic measures which component determines the minimum among selected rows, not coverage. |
| A generic realised volatility implies a particular standard error for NB10 | Rejected. No such standard error was measured; retain the actual block-support gate and descriptive results. |
| Forward-filled zeros necessarily understate daily variance | Rejected as a general statement. Catch-up returns can offset zero days. Smoothing, timing and stale marks remain empirical concerns. |
| Use a robust region only when neighbouring intervals exclude zero | Modified. The primary horizon lacks the required calendar blocks. Display neighbourhood consistency descriptively; absence of an interval is not a reason to invent inference. |
| Replace the strongest reference with equal weights as the sole primary control | Declined. The research question is improvement over the original regularised inverse-variance benchmark. Equal remains a mandatory secondary control. |
| Do not advance the grid automatically because it could become a leaderboard | Addressed through registered contrasts and complete response surfaces. Advance from smoke on correctness only; retain all cells and avoid a profitability-based stopping rule. |
| Introduce downside risk, BTC factors or larger covariance models | Deferred. The next notebook targets sizing mechanics with fixed selectors. These require distinct hypotheses and additional controls. |

The proposed main scope adds two low-parameter alternatives: median and maximum risk forecasts across the registered windows. These are exploratory hypotheses suggested during the design process, not findings or additional independent samples.

## Formal review

Claude verified the 40-policy main matrix, 18-policy smoke subset, 12 sensitivity policies and eight separately scoped cap-aware policies. It also verified the 70-origin calendar and maturity totals, the gap-scaled drift/variance formula under its stated observation model, and the convex objective's no-binding-cap equivalence and covariance-scale invariance.

| Formal review item | Amendment or disposition |
| --- | --- |
| Which count drives sparse-pair shrinkage? | Explicitly use complete actual-mark intervals, marks minus one. Store NB10 update counts separately. |
| Which kappa does bounded I90 use? | Explicitly pin kappa30 for exact NB10 component parity. |
| Entry and exit timestamps were implicit | Define fixed units bought at NAV(A), A=T−1, and valued at NAV(A+h); explain this inherited snapshot convention and zero cash return. |
| Block lengths and likely gate outcome were implicit | Define exact h-calendar-day bins, scheduled masks and complete-block counting. Maximum bins are 38/8/2 for 7/30/90 days; the primary 30-day gate cannot pass. |
| What does gate1 mean? | At least one other eligible peer with finite positive variance; full pool preferred, partial pool fallback. No minimum fraction is implied. |
| Sparse-pair full windows require observed endpoints | Require per-origin strict-pool versus original-pool support and partial-fallback reporting. This convention change is not attributed to the estimator itself. |
| Could pool limits be shared constraints? | Checked local `capacity_limits`: the 33% limit applies to each vault's TVL and becomes an individual cap. Shared groups would require a changed feasibility/optimisation specification. |
| Variance heatmap statistic | Ratio of mean variances on identical supported origins, logarithmic colour scale centred at 1, with counts and undefined cases. |
| V180 and main L180 use different shrinkage | Label inherited V180 kappa60 and main L180 kappa30 explicitly. |
| Does partial history count as an available ensemble input? | Yes, if the final regularised estimate is finite and positive. Undefined inputs trigger the declared fallback. |
| Promote forecast calibration to required output | Accepted. Deduplicate estimator rows; compare simple/log forecasts with matching realised variance units; use equal-origin QLIKE/calibration, support and floor/prior status. |
| Add cap-free shadows | Accepted as derived same-accepted-budget allocation diagnostics, with no additional outcome-evaluated policies or search. |
| Add 200 permuted-weight trials | Deferred. Trial count, persistent assignment, dependence and matched exposure need registration; do not silently add 28,000 allocations to the main study. |

The sparse estimator is a hypothesis under a variance-proportional-to-time observation model. Its model-dependent unbiasedness is not a claim that sparse vault data follow that model. The existing calendar estimator is retained as the exact control.

The 17 contrasts × three outcomes are a predeclared **joint reporting family**, not fresh confirmatory evidence. The primary horizon cannot meet the inherited ten-block gate in 2026. The plan explicitly prevents shortening blocks, promoting seven-day evidence or changing missing-support handling to obtain a claim.

## Focused final check

Claude’s final verdict was **ready**. It verified all six required corrections and the policy/horizon counts, formulas, per-vault caps, calibration units and research-only interpretation. Its three remaining non-blocking clarifications are now explicit: END is 5 October exclusive, missing TVL retains the source-compatible concentration ceiling and unknown-state flag, and sparse-pair kappa counts complete intervals rather than NB10 updates. These clarifications and review-status text were added after the final response; no further model pass was requested because no formula or policy scope changed. No NB11 notebook or experiment has been executed.

## Provenance

Prompts, full CLI JSON responses, extracted contributions and the reviewed plan snapshot are retained under the ignored `_artifacts-restored-2026-10-07/11-plan-review/` directory. `request-manifest.json` records the reviewed draft's SHA-256. This written note and the plan are maintained outside generated artefact directories for review.

### Reviewed snapshots and final plan

- Co-designed draft reviewed: `fcf9116d84232f088b383632fbd25a09ab1a45c98e3bd8d78f4d979f48596cf0`.
- Amended draft checked in the final call: `b8f6569d517650d0f51385e90694000169af42ef3fb6b615f64defed861b587c`.
- Final plan, including the requested non-blocking clarifications: `ab606071d7fd5e64d2996625ab83b7352c73f937b121f445319ef4f2e2869679`.
- All three CLI responses report success and `claude-fable-5-1` as the only model used. No fallback model was requested or returned.
