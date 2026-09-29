# Disposition of the notebook development review

The [development plan](rolling-profit-risk-notebook-development-plan-01.md) has been updated using [Grok’s review](grok-46-notebook-development-review-01.md). No notebooks were implemented or run.

## Accepted

- **Freeze and name gate/control variants.** Legacy controls remain exact. If the availability audit requires a common available-history gate, all four factorial arms use it and B00 requires three new runs. Preserve the original threshold, not the positive-return gate in monthly diagnostics.
- **Label the sizing change accurately.** It changes lookback, interval estimation, floor and fallback together; this is a sizing-path factor, not an isolated lookback effect. Preserve deterministic ties.
- **Describe membership replay as an intervention on the parent policy.** Requested schedules can reflect its earlier fills and hold protections. Save stateless ranks too, and do not claim identical realised holdings.
- **Verify actual redistribution before the no-refill experiment.** The allocator source has a remaining-equity loop; execution-path/ledger verification establishes whether it matters in this harness. Do not import old A0-cap headline numbers.
- **Preserve released cash.** Neither exposure treatment may be normalised back to full investment. E2 now applies its drawdown haircut to the parent's accepted targets calculated in the treatment's own state. This avoids inadvertently combining it with E1's change to cap redistribution.
- **Cash controls must be causal fractions.** Use the same pre-trade desired targets, never another simulation's future equity or absolute dollar balance. Report achieved exposure differences.
- **Report nominal versus effective holdings.** A heavily penalised name can retain one of six slots; this is different from hard exclusion and replacement.
- **Make prior-experiment overlap explicit.** Notebook 27 is new short-history-basket evidence only when the requested selection schedule differs. Otherwise label it a corrected transport of waterfall NB69 and reuse identical results where available.

## Rejected or qualified

- **Replacing the hyper-ai run with a slice of the full run:** rejected. The January-start simulation and the August-start ongoing portfolio have different initial holdings, cash, costs and subsequent paths. A reporting slice cannot substitute for the separately initialised comparator. The stated three-window run budget remains; windows are explicitly overlapping, not independent confirmations.
- **Skipping 14/60-day sensitivities because 30 days is a no-op:** rejected. Other lookbacks can change membership or funding. Keep the predeclared sensitivities, skipping only invalid implementation or truly identical already-validated configurations.
- **Reducing the run count based on the above two shortcuts:** rejected. Reuse is by exact configuration/data/execution/start state, not overlapping dates or similar headline metrics. The conditional budgets remain explicit.
- **“Original-ranking arms keep original missing-volatility semantics”:** only B00/B10 retain old sizing. B01 intentionally uses new sizing while retaining original missing-score handling. Clarified in the plan.
- **A near-one membership Jaccard proves duplication:** qualified. Exact equivalence permits reuse; small differences may still matter. No arbitrary similarity gate will be fitted after outcomes.

## Prior-experiment input and reading evidence

The exact input packet is saved as `_review/rolling-track-plan-02/prompt.md`; `input-files.json` lists the sources. It includes:

- Actual extracted notebook narratives/results from lower-vol NB28, NB32 and NB39, and waterfall NB69.
- IC monthly-calibration, profitable-months, stability-screen and corrected allocation-decomposition summaries.
- The earlier Grok synthesis across all 152 notebook narratives and 106 research documents, plus the author's accepted/rejected disposition.
- The new development plan.

Grok read the remainder of the supplied packet in its session prompt file, then inspected relevant `hyper-ai.py` and `AlphaModel` source. Its final response explicitly identifies these experiments and gives a notebook-by-notebook duplication matrix. This is reading of previous experiments and their results, not a fresh audit of all historical code or a recomputation of numerical outputs.

The first investigation exhausted its 14-turn budget and ended `cancelled`; it is preserved as incomplete. The same session was resumed with a no-more-tools instruction to finish using the context already read. That response completed with `end_turn`, requested model `grok-4.6`, recorded backend `grok-4.6-build`. Raw investigation/completion streams and validation are retained. The author revisions above were not submitted for a second review.
