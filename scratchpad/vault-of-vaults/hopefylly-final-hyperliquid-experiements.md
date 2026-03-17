# Hopefully final Hyperliquid experiments

## Why this list is short

Most of the large idea backlog has now been tested across NB96-NB127.
The broad picture is fairly stable:

- The robust region is around `min_tvl=15k`.
- `min_age=0.0` to low-positive age filters still matter.
- `equal_weight` and `age_ramp` are the only signal families still worth serious production attention.
- Many more exotic ranking, overlay, and vault-name-based ideas did not survive robustness or walk-forward checks.

So the remaining work should be less about inventing new signals and more about proving that the shortlist is investable, durable, and not driven by accidental concentration.

## Recommended final experiments

### 1. Cost and turnover stress test on the production shortlist

Take the best candidates from NB124, NB125, NB126, and NB127 and rerun them with a realistic grid of:

- trading fees
- slippage assumptions
- rebalance frequency
- minimum trade thresholds

Why this matters:
The current winners may still be too dependent on frictionless rebalancing. A result that stays good under modest cost stress is much more production-worthy than one that is only slightly ahead gross of costs.

Success criterion:
The preferred configuration keeps its ranking under reasonable cost assumptions and does not collapse once turnover is penalised.

### 2. Leave-one-winner-out and concentration stress

Run the current shortlist while removing:

- the top 1 vault by contribution
- the top 3 vaults by contribution
- the strongest month
- the strongest quarter

Why this matters:
Several earlier ideas looked good until the returns were decomposed. We should make sure the production candidate is not just a disguised bet on a handful of exceptional vaults or one lucky burst.

Success criterion:
The strategy remains clearly positive and reasonably ranked after these removals, even if absolute performance drops.

### 3. Strategy-type or risk-bucket decomposition with proper metadata

Redo the spirit of NB121, but with real vault metadata instead of vault-name heuristics. Group vaults by actual behaviour or design, such as:

- directional trading
- market making
- basis or funding capture
- neutral or low-beta carry
- higher-volatility opportunistic vaults

Why this matters:
The question in NB121 was good, but the labels were weak. If one bucket drives almost all of the edge, we should know that before treating the portfolio as diversified.

Success criterion:
We learn whether the current winner is genuinely diversified across strategy types, or whether we should cap exposure by bucket.

### 4. Matched Sharpe vs Sortino walk-forward decision notebook

Build one final apples-to-apples comparison where:

- the search region is identical
- the folds are identical
- the candidate budget is identical
- the holdout scorecard includes `Sharpe`, `Sortino`, `Calmar`, `Recovery`, `Longest DD`, `Time in market`, and `Avg capital util`

Why this matters:
NB124, NB125, and NB127 together suggest that the parameter region is more stable than the exact winner, but they still do not fully settle whether the production objective should be Sharpe-led or Sortino-led.

Success criterion:
We end with one objective choice for production, plus a short written reason for why that objective best matches the desired trade-off.

### 5. Liquidity and absorbability stress inside the `15k` region

Stress the leading candidates with tighter assumptions around:

- capital deployment capacity
- maximum position size per vault
- volume or liquidity gating
- slower entry and exit

Why this matters:
Some configurations may look attractive because they rotate into vaults that are fine for a notebook but less comfortable at real size. This is a separate question from simple slippage.

Success criterion:
The preferred setup still works when we constrain it to something we would actually be willing to run with real capital.

### 6. Longer walk-forward revalidation once more data exists

Plan a repeat of the final walk-forward notebook after more live history accumulates, using the same shortlist and the same evaluation protocol.

Why this matters:
The remaining uncertainty is now less about missing clever ideas and more about limited stress history. More time and more bad periods are likely to be more informative than yet another ranking transform.

Success criterion:
The chosen production family remains competitive as new history arrives, rather than only looking strong in the current sample.

## Optional one last exploratory branch

### Correlation-clustered equal weight

If we want exactly one final exploratory experiment, this is the one I would still consider:

- cluster vaults by return correlation
- pick the best vaults within each cluster
- equal-weight across clusters instead of across all selected vaults

Why this is still interesting:
It introduces genuinely new information rather than another transform of age, TVL, or recent returns. It may reduce hidden concentration without needing fragile scoring logic.

Why it is optional:
This is still a research branch, not a validation step. I would only do it after the main production checks above.

## Suggested order

1. Cost and turnover stress
2. Concentration stress
3. Matched Sharpe vs Sortino walk-forward decision
4. Liquidity and absorbability stress
5. Strategy-type or risk-bucket decomposition with proper metadata
6. Longer walk-forward revalidation
7. Optional correlation-clustered equal weight

## What I think we should avoid now

I would avoid spending more time on:

- new vault-name-based signals
- more minor age-ramp shape variations
- more parameter polishing without stronger out-of-sample checks
- complicated signal composites unless they use genuinely new information

Those directions have mostly already told us what they can tell us.

## Bottom line

The project feels close to a final production decision.
The biggest unresolved question is not "what is the next clever signal?" but "which of the current shortlist survives realistic friction, concentration stress, and matched out-of-sample comparison?"

That is the standard I would use for the next experiments.
