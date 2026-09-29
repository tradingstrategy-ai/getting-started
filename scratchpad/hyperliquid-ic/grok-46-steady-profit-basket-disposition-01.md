# Grok review disposition

Reviewed on 2026-09-19 using CLI `--model grok-4.6 --reasoning-effort xhigh --sandbox none`, with bypassPermissions and always-approve for tool execution, and a review-only prompt. CLI resolved `grok-4.6-build` and completed normally (`stopReason: end_turn`). See [raw review](grok-46-steady-profit-basket-review-01.md), [prompt](grok-steady-profit-basket-review-prompt-01.md), and [revised plan](steady-profit-basket-plan-01.md). Raw JSONL is retained beside the review. Grok read the prior notebook summaries, NB30 artefacts and allocation code; the review lists sources actually read.

## Accepted changes

- **Zero-Q floor mostly duplicates frequency:** replaced the proposed hard floor with continuous Q percentile weighting. Added matched P percentile controls, creating six fixed arms rather than four. This tests capital allocation towards steady returns; requested membership remains identical. Twenty-four main runs, two parent parity replays, at most four exposure controls; no parameter optimiser.
- **Accounting stack was mislabelled:** use the NB25 trade-executor engine harness, not an imaginary independent implementation in `rolling_track_simulation.py`. B00 retains its native two-day/six-slot configuration for parity only. Daily flexible experimental arms and E1-style no-refill projection are explicit shared changes. A0b remains separate.
- **Timing contradiction:** freeze actual midnight T, strictly earlier original observation timestamps, remap old date+1 features, and distinguish diagnostic entry marks from actual engine fills. Audit and repair NB30 before drawing new conclusions.
- **Weak-history overconfidence:** add event-count, Q=M, young-cohort capital and contribution diagnostics. Check observed eligibility rather than assuming under-h vaults exist in the scored opportunity set.
- **Volatility floor and exposure confounds:** report floored/missing-risk weight share and bound exposure-control reruns. Do not interpret an inactive weighting factor as evidence.
- **Selection of best settings:** W=60 is explicitly exploratory and post-selected from NB30. W=30 is descriptive; report every result and disagreement. The 20% CAGR goal is economic context, not an after-the-fact model selection rule.
- **NB30 gaps:** retain full Stage 0 audit, including missing conditional horizons, Q cohort diagnostics and timing/labels, rather than claiming three top-group repairs constitute full compliance with the old plan.

## Not adopted

Grok proposed marking Q unavailable whenever there are fewer than two events or Q=M. We do not add that exclusion: Q=M can occur in genuinely steady positive paths and does not prove the lower tail is undefined. Removing those rows risks repeating the hard-screen failure and conflicts with the user's young-vault objective. Their evidence weakness is explicitly reported, with no claim that short records establish safety. Short-history sizing remains a separate intervention.

Grok offered retaining the zero-Q floor with clearer labels as an alternative. We chose continuous Q weighting with P controls because the user wants to refine the NB30 magnitude discovery and avoid repeating frequency screens. The floor remains a descriptive overlap diagnostic only.

## Status

Actionable review findings are incorporated in the plan. Grok reviewed the initial draft; the revised six-arm design has not had a second external review. No NB30 repairs or portfolio implementation/runs were performed in this planning task. Implementation begins with Stage 0 and must report corrected evidence, even if it weakens the proposed lead.
