# Disposition of Grok 4.6 research review

The [plan](rolling-profit-risk-plan-01.md) was revised after [Grok’s synthesis](grok-46-rolling-profit-risk-review-01.md). The review is advisory; its suggestions are not empirical results. No new backtests were run.

## Accepted and incorporated

| Review point | Change |
|---|---|
| The first draft risk-ratio family risks repeating lower-vol NB32 | Move complex scores out of the first wave; begin with access and sizing decomposition |
| Eligibility is not actual funding | A full ranking × sizing factorial, with explicit missing-risk fallback and accepted-dollar ledgers |
| Do not refill clipped capital is a distinct existing lead | Add C1, conditional on identifying a real redistribution step; compare against cash-matched exposure |
| Soft path-risk sizing differs from a hard screen | Add C2 independently, with released capital staying cash and no forced replacement |
| A monotonic return transform cannot alter pure return ordering | Remove the redundant transform-only ranking comparison; retain it only as an optional ratio formula |
| A fitted “quality floor” is vague and expands the search | Remove it from the first wave |
| History reviews must resolve corrections across folders | Preserve corrected gate labels, no-op/negative/inconclusive distinctions and source coverage |
| Graded original-score fallback is worth distinguishing from replacing all ranking | Keep as one optional later experiment, with comparability and saturation limitations |

## Modified rather than accepted literally

- Grok’s option 1 claimed to replace only ranking while also changing volatility sizing. The final plan uses a 2 × 2 factorial to identify both effects and their interaction. Available-history growth is a hypothesis, not a guaranteed new edge.
- The draft’s R0 was correctly matched to the other new equal-weight arms, but not matched to production. Grok blurred those two claims. The revised plan explicitly reproduces the original-policy control and labels factor comparisons.
- Grok proposed equal-share fallback for unknown volatility. The plan implements this unambiguously as median finite raw sizing weight (equal raw weights if all are missing), then normalises through the common allocator. No risk estimate is invented.
- Grok called `n/(n+4)` an observation-count barrier that necessarily penalises weekly observations. The draft capped dense effective counts at elapsed weeks, so that particular criticism was overstated. Nonetheless the haircut was removed to simplify the first wave and avoid reducing young-vault access before testing it. This is not evidence that all confidence sizing is invalid.
- Grok sometimes required lower-risk rankings to predict higher future return. That conflicts with the user’s willingness to exchange return for stability. The plan judges the joint trade-off and sufficient profitability instead.
- The synthesis says a logarithmic reward still rewards ATM-like high returns. Correct: removing score saturation does not identify hidden crash risk. This remains an explicit limitation, not an invitation to fit an ATM exclusion.
- Some batch reviews say the monthly feature was never isolated. NB23 changed multiple policy elements, but NB24 explicitly compared monthly ranking against original ranking under matched equal sizing. Do not erase that ranking evidence.
- Partial-batch statements such as “StratWise never receives capital” are scoped to the relevant old engine arms. NB23/24 and other research variants did allocate to it. The final plan requires per-arm ledgers rather than a universal statement.

## Rejected or deferred

| Suggestion | Decision and reason |
|---|---|
| Restore Scared Money to a blacklist in the primary experiment | Rejected: user requested blacklist-off comparisons. Operational limits remain; no selective name exclusions |
| Account P&L, cumulative volume or social factors | Rejected: outside the price-derived scope |
| Reserved StratWise/young slots or named sleeves | Rejected: fit-free examples, not membership targets; also conflicts with the flexible-size direction |
| Fixed 8/20-observation admission thresholds or 180-day requirement | Rejected as admission rules: young and weekly-observed vaults must be usable |
| Monthly tie-breaks, positive-week gates and further trimmed-return searches | Deferred/rejected for this programme: user requested direct rolling metrics and the history supplies significant negative evidence |
| Require 20% CAGR in every period, outperform incumbent, or higher forward return from a risk signal | Rejected: wrong objective and excessive gates |
| Broad expansion into beta circuit breakers, provenance, ML or clustering | Deferred: would dilute the simple selection/sizing experiment |
| Run every proposed score and allocation combination | Rejected: first A–C, then at most one justified D option |

## Coverage and validation

Nine completed Grok CLI history calls covered all markdown narratives from 152 notebooks plus 106 top-level research documents in the three requested folders. One synthesis combined these with the draft, current `hyper-ai.py`, feature-engineering documentation and the two-reference comparison. Sources were split into manageable batches; each partial review lists its local coverage limits. The later synthesis supplied context missing from individual batches.

All ten calls requested `--model grok-4.6`, reported backend `grok-4.6-build`, and ended successfully with `end_turn`. This installed CLI uses lower-case `end_turn`, unlike the older troubleshooting documentation’s `EndTurn` example. The smoke test also completed with a non-empty OK response. Raw logs and validation are retained.

This establishes completed reviews, not independent verification of all historical numbers. Notebook narrative extraction excluded code cells and embedded numerical/image outputs; Grok made targeted local checks. No backtests, production changes or publishing actions were performed. The author’s final revisions were not submitted for a second Grok review.

Files under `_review/rolling-metrics-grok46/`:

- `history-index.md`, `history-inventory.json`: all notebook source paths and extracted narratives.
- `batch-manifest.json`: 258 supplied research-document entries across nine batches.
- `*-prompt.md`, `*.jsonl`, `*.err`, and per-batch `.md`: reproducible inputs and raw/readable outputs.
- `synthesis.md`, `review-validation.json`: final review and successful backend/completion records.
- `plan-before-review.md`, `source-hashes.json`: the original draft and source fingerprints.
