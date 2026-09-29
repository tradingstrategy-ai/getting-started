# Claude Opus review 02

Review command: `claude --model opus --effort high --print --dangerously-skip-permissions`

Date: 2026-09-13

The CLI `opus` alias was used for the current Opus 5 model. The review was read-only and used the corrected artefacts plus the explicit run summary in [`_review/04-claude-opus-prompt.md`](_review/04-claude-opus-prompt.md).

## Verdict

**Safe to continue with prospective data collection; not ready for a model freeze.** The panel, labels, IC table and folds are correctly plumbed (purge, fold-local selection, `min_n_cross_section`, no social/follower columns), and the run honestly shows only risk persistence (OOF Ridge rank IC approximately 0.63–0.70 for downside/variance, approximately 0.02 for growth). This satisfies the plan's Phase 1 gate only via its data-gap → prospective collection branch; it does not meet the Phase 4 shortlist gate because there is no block bootstrap, intact-bundle null or incremental lift versus controls on identical rows, and the shortlist is 12 near-duplicate volatility columns rather than at most three families. NB04's Arm A/C numbers should not be quoted as an anchor or geometry verdict because the production score is degenerate on the causal window.

## Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
| --- | --- | --- | --- | --- |
| NB01 data/baseline | Panel build and hashes fine; audit is four cells. | Thin: no raw→TVL→eligible→labelled funnel, no hand-checked rows, no April 2026 polling check. | Counts consistent with config (602 vaults, `written_at` from 2026-03-23). | Low |
| NB02 feature panel | `positive_week_frac_90` counted missing weeks as losses; publication mask is an ingestion filter rather than a full as-of join. | 82 predictors + six seed weights; manifest lacks formula/units/minimum observations; synthetic perturbation test does not call the full generator. | Labels sane and coverage matches 68 dates / 17,683 rows. | Important |
| NB03 IC screen | Purge, fold-local shortlist and minimum cross-section are enforced. | No bootstrap, null, terciles/upper basket, cohort split or incremental control test; shortlist averages growth and downside IC and is risk-feature heavy. | 7,112 rows and 69 OOF diagnostics are internally consistent. | Medium |
| NB04 replay | Fee, cost-basis, stale-mark and cash accounting internally consistent; selection is arbitrary among tied vaults. | Arms B/D deferred consistently; Arm C omits the momentum gate and is not the plan's threshold allocator. | Arithmetic verified, but turnover and fees are tie-break artefacts. | Blocking for its stated purpose |

## Blocking issue

**Degenerate production score.** `_production_score` filled components separately, so with `cagr_360` absent everywhere it allowed the Sortino leg to rank the causal panel. The faithful production composite requires both legs and a deterministic tie-break; the causal replay should therefore remain in cash until a point-in-time panel contains the long leg. The corrected implementation must apply composite-level missing semantics and report that Arm A/C are undefined as performance tests on this window.

## Important issues

- `positive_week_frac_90` must preserve missing weekly observations as missing before rolling means; otherwise young histories receive a false losing-week fraction.
- The two-day publication cutoff is a conservative ingestion filter, not a full historical as-of join. It is internally consistent and intentionally documented; the source does not contain the prospective decision snapshots required for a complete point-in-time reconstruction.
- Arm C must apply the same 14-day momentum gate as every other arm. Its adaptive breadth is a bounded geometry diagnostic, not the plan's future economic hurdle allocator.
- Return EWM should use normalised weights (`adjust=True`) while the NAV EMA may remain `adjust=False`.
- Feature returns should use the seven-day marked-NAV carry so a permitted gap produces zero carried returns and a fresh-day catch-up move; coverage flags must continue to use actual observations.

## Acceptable limitations

Bulk publication timestamps and the 68-date causal panel, two underpowered folds, absent long-history controls, NAV-only replay without exact engine minimum-hold rules, and deferred B/D arms are explicit plan limitations. The review also noted definitional differences such as time-underwater and Herfindahl positive-gain concentration; these should be recorded in the manifest rather than expanded into a new feature search.

## Recommended next actions

1. Apply the composite-level missing semantics and deterministic ties, the momentum gate, missing-week masking, normalised return EWM and marked-NAV feature returns; rerun NB02–NB04 and report the cash result if the long leg remains unavailable.
2. Make the decision clock explicit in the prospective collection specification, with per-decision snapshots and hashes saved before outcomes.
3. On the existing shortlist only, add paired date-block uncertainty and an intact-bundle placebo against the `vol_30` control before freezing a model.
