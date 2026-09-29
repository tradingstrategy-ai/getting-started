# Claude Opus review 03

Review command: `claude --model opus --effort high --print --dangerously-skip-permissions`

Date: 2026-09-13

The CLI `opus` alias was used for the current Opus 5 model. The review was read-only and covered the final rerun, source module, all four notebooks and artefacts using [`_review/05-claude-opus-final-prompt.md`](_review/05-claude-opus-final-prompt.md).

## Verdict

**Safe to proceed with prospective collection. The Phase 1 gate is met only through its data-gap branch, and one deliverable of that branch is still missing.** Feature/eligibility causality passes on the real generator: the review's truncated-prefix run on 40 vaults produced zero feature, eligibility or matured-label differences. Source provenance remains inadequate (`historical_point_in_time_reconstructable: false`), so the plan requires a data-gap report and prospective collection specification. The report exists; the specification still needs to be written. The Phase 4 shortlist gate is not met: there is no block bootstrap, intact-bundle null, incremental control test or horizon selection, and the 12-column fold shortlists are near-duplicate volatility measures. The result is risk persistence; growth IC is approximately zero.

## Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
| --- | --- | --- | --- | --- |
| NB01 data/baseline | Panel build, hashes and lag audit are correct; `available_ts` drives masking downstream. | Thin: no raw-to-TVL-to-eligible-to-labelled funnel, hand-checked rows, production parity comparison, April 2026 polling check or survivorship sensitivity. | 602 vaults and 1,293 days are plausible. | Low, deferred |
| NB02 feature panel | Generator is causal on the executed truncated-prefix check. Weekly masking, EWM `adjust=True`, seven-day carry and labels are correct. | 82 predictors, six seed controls, 49 outcomes; manifest still lacks formula/units/minimum-observation/role fields. No terminal-NAV stress. | Eligible cross-sections are 229–280 vaults; long-history coverage is absent because of ingestion truncation. | Important, non-blocking |
| NB03 IC screen | Purging, fold-local selection, minimum cross-section and equal date weighting are enforced. | Exhaustive table exists, but no bootstrap, null, upper-basket, cohort split, incremental control test or horizon rule. | Volatility persistence dominates; growth OOF rank IC is approximately 0.035. | Medium, deferred |
| NB04 replay | Accounting is internally consistent and both arms correctly remain in cash when the 360-day leg is unavailable. | B/D are correctly deferred; Arm C is a bounded geometry control. | Cash is a coverage outcome, not a performance conclusion. | Important labelling |

## Remaining issues

1. The cash-on-all-zero behaviour is a deliberate research abstention rather than exact production-engine parity; label the result as an abstaining research anchor and record that the live engine tie-breaks zero scores.
2. NB03's `control_prod_composite` still fills each leg separately, so it is effectively a Sortino-only control while the shared production score requires both legs. Relabel it or compute it with composite-level missing semantics.
3. `longest_gap_30/90` counts all pre-first-observation dates as one gap, making it a hidden youth feature. Set the gap to missing before the first valid NAV.
4. `unchanged_nav_frac_30/90` counts carried marks as unchanged observations. Compute it from fresh-to-fresh changes while retaining separate coverage flags.
5. Weight clipping followed by renormalisation can breach the concentration cap; preserve a cash residual, and abstain from new allocation when risk is unavailable rather than median-filling it.
6. The research Sortino minimum-observation rule differs from production's full-window rule; record this parity difference explicitly.

These issues are inactive in the current cash replay but should be corrected before model freeze. The bulk publication timestamp limitation, 68-date causal panel, two diagnostic folds, absent long-history controls, and NAV-only replay are acceptable documented limitations.

## Minimal next actions

1. Write the prospective collection specification: per-decision snapshots and hashes for vault price/TVL, availability, deposit/redemption state, fee mode and the production indicator values before outcomes mature; record zero-score tie behaviour.
2. Correct the NB03 control, pre-inception gap masking, fresh-only unchanged fraction, cap-preserving weights and missing-risk abstention, then rerun NB02–NB04 and add the full-generator truncated-prefix check to NB02.
3. On the existing fold shortlists only, add paired date-block bootstrap intervals, an intact-bundle placebo against `vol_30`, and explicit rows for unavailable IC cells before selecting a horizon or freezing a model.
