# Claude Opus review 04

Review command: `claude --model opus --effort high --print --dangerously-skip-permissions`

Date: 2026-09-13

This final review used the Opus 5 CLI alias and the post-rerun artefacts with [`_review/06-claude-opus-final-final-prompt.md`](_review/06-claude-opus-final-final-prompt.md).

## Verdict

**Proceed with prospective collection.** Phase 1 passes only through its data-gap branch: the cache is not historically point-in-time reconstructable, but the real generator's truncated-prefix test passes for features, eligibility and matured labels. The Phase 4 shortlist gate remains open: there is no bootstrap, intact-bundle null, incremental control lift, horizon selection or B/D feature arm. The result is risk persistence, not an edge.

## Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
|---|---|---|---|---|
| NB01 | Panel, hashes, lag audit and availability masking are correct. | Missing the full funnel, hand-checked rows, polling-break and survivorship checks; config lacks code and production-strategy hashes. | 602 vaults / 1,293 days plausible. | Low, deferred |
| NB02 | Causal prefix check, labels, EWM, gap and unchanged fixes verified. | 82 + 6 + 49 declared; formula/units manifest and terminal stress remain deferred. The first four eligible dates use truncated 24–29-day histories. | 229–280 eligible vaults/date; long-history features absent from ingestion window. | Low–Medium |
| NB03 | Purge, fold-local selection, pairwise minimum and grid audit correct. | Bootstrap, null, upper baskets, cohort split, incremental controls and horizon selection remain deferred. | Volatility persistence dominates; growth OOF IC approximately 0.035 and flips sign across folds. | Medium, deferred |
| NB04 | Accounting is consistent; both arms correctly remain in cash with no 360-day production leg. | A/C only; B/D correctly deferred. | Cash is a coverage outcome, not performance evidence. | Important labelling |

## Remaining defects

1. Replace “faithful production/parity” wording with “research abstention”: the live engine converts missing composite signals to zero and tie-breaks by pair ID, while this research replay holds cash. Record that Sortino's minimum-observation rule also differs from production's full-window rule.
2. Expand the prospective collection specification to retain every raw poll since the prior snapshot, the BTC daily bar and hash, and the engine's selected basket/weights per decision.
3. Add code-revision and `/Users/moo/code/strategies/strategy/hyper-ai.py` SHA-256 values to the frozen config.
4. Start the eligible window after 30 visible history days (2026-05-10 for this cache) so truncated 24–29-day rows do not enter the 30-day feature panel.

The two-day ingestion-clock approximation, missing long-history controls, underpowered folds, NAV-only replay and deferred Phase 4 work are acceptable documented limitations. Definitional differences such as time-underwater, Herfindahl gain concentration, TVL-change variability and panel-anchored weekly blocks should be recorded in the manifest rather than expanded into another feature search.

## Next actions

1. Apply the four documentation/config/eligibility corrections above and rerun the notebooks.
2. Begin immutable prospective snapshots with pre-outcome hashes and engine decisions.
3. On the existing fold shortlists only, add paired date-block bootstrap and intact-bundle null comparisons against `vol_30` before choosing a horizon or freezing a model.
