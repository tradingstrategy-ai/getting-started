# Expanded experiment 10 — plan review

Reviewed 10 October 2026 using Claude CLI with **`claude-fable-5-1`**. The CLI returned success and its model usage confirms the requested model; no fallback model was used. This reviews the [expanded plan](10-expanded-score-allocation-plan.md), not experiment results. No notebook or backtest was executed.

## Verdict

Claude's verdict: **“The design is sound.”** I agree. Combining pre-selection metric components inside a score, separating ranking from sizing, and comparing paired allocations addresses the user's research question. Smoke uses a restricted combination matrix across the full available 2026 history. It must not sample dates to save execution time.

The current plan is sufficiently specified to start smoke implementation after the targeted corrections below. Successful implementation still requires input reconciliation, exact reference comparisons and numerical audits. The broader stages require an enumerated registry, declared primary contrasts and a measured execution budget before they run. This review is not evidence of better investment performance.

## Historical scope

- Decision interval: 2026-01-01 to 2026-10-05, end exclusive, on the four-day phase-zero cadence.
- All 70 scheduled origins are retained; 62 have administratively mature 30-day outcomes and eight remain pending.
- All available 2025 observations initialise indicators. Older observations remain available for two-year features, maximum-history K and frozen recipes; 2025 is not a truncation boundary.
- Young vaults remain eligible despite missing long-window features. Causal NAV carry fills internal calendar gaps without creating actual observations or filling permissions.
- Smoke remains 36 combinations and one 30-day horizon. The q=0.5 historical combination moves to the next batch; a constant-component control replaces it.

## Review findings and dispositions

| Finding | Assessment and action |
| --- | --- |
| Calendar and label maturity need exact assertions | Accepted. Added 70/62/8 totals, quarterly counts and the explicit maturity inequality. Keep Q4 visible with zero mature outcomes. |
| Peer-relative inverse-variance/inverse-volatility rank equivalence | Accepted clarification. Both are monotone functions of the same own-variance/peer-prior ratio, even with vault-specific priors. Deduplicate their percentile ranks on identical inputs; magnitude sizing remains different. These rankings need not equal raw inverse-risk rankings. |
| Adding I might merely flatten F allocations | Accepted. Replaced T27 with F ranking and A(F, constant 0.5) linear sizing. Compare T05 with T27 to isolate the varying risk ingredient, and T02 with T27 to measure the neutral-offset effect. No increase in smoke combinations. |
| Min with missing-zero may mostly exercise zero weights and cash | Accepted as a mechanism concern, not a demonstrated historical result. Preserve M0 semantics and label T18 a conjunction/fallback probe; propose an MA companion later. |
| Confidence-adjusted K and M0 have different missing/weak-value treatment | Accepted. Disclose the discontinuity and attenuation; propose an MN companion later. Do not silently rewrite M0. |
| Reference reproduction needs concrete anchors | Accepted. Require per-origin comparison with saved, unrounded NB10 ledgers. Displayed T00/T01 numbers are approximate orientation only; verify equal-benchmark budget/cap equivalence before asserting T01 parity. |
| Some required feature windows may not already be cached | Accepted. Package 1 lists load/compute/unsupported status for every required feature. Compute supported missing cache entries using audited definitions; an absent cache must not silently remove an arm. |
| Unscored vault tie-breaking is arbitrary and persistent | Accepted. Disclose address preference and include the unscored tier in later seeded tie sensitivities. |
| Fixed-window K scaling cancels in its cross-sectional transform | Accepted clarification. It cancels when all fitted spans have the same n; it does not cancel for maximum-history K. Retain the audited NB09 formula and age/support diagnostics. |
| Zero-score and solver fallbacks need identifiers | Accepted. Added explicit fallback policy IDs to the registry so activity is countable. |

## Other ideas from Claude

1. **Shuffled-component placebo:** potentially useful in the next batch, with age/reporting-support strata and persistent identity considerations. A single shuffled draw is a diagnostic, not a validated statistical null. It should not enlarge this smoke grid.
2. **Horizon-independent allocation ledgers:** accepted now. Reuse allocations when joining 7-/90-day outcomes later; future horizons must not alter an ex-ante allocation.
3. **Summarise contrasts across score families:** useful for the broader stage, alongside every recipe's results. The 139 recipes are correlated researched constructions, not independent replications. Any pooled estimator or cluster uncertainty needs a specified method; do not claim that pooling alone resolves multiple testing.

## Remaining assumptions

Neutral 0.5 anchors, missing-zero, prior regularisation, score transforms, K confidence, coefficient anchors, sizing curvature, N, caps and the inference gate are explicit design choices. Component dispersion, effective positions, cash, missingness and treatment activity must accompany returns so apparent gains can be explained. Near-equal allocations from top-ranked bounded scores and prior-dominated risk estimates are possibilities to measure, not results already established.

All 2026 findings remain retrospective. Overlapping 30-day snapshots are not independent trials and cannot be compounded into strategy CAGR. The short history does not become statistically strong merely because all 70 origin dates are present.

## Provenance

- Reviewed plan SHA-256: `658b2cfe913afd27f4dd67d5a81bfa45d997799d97594ab8166519da90f61fd7`.
- Current plan SHA-256 after incorporating feedback: `3e21924fe9ca207e71821f8d02c7dcec48bf7931564b9d75e03f8581b16e9924`.
- Full prompt, CLI JSON, extracted response and request manifest are retained locally in the ignored `_artifacts-restored-2026-10-07/10-expanded-plan-review-full-2026/` directory.
- The final targeted amendments were checked against the review but were not submitted for another Claude pass.
