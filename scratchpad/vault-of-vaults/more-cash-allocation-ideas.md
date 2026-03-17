# More cash allocation ideas

This note proposes the next allocation experiments for the Hyperliquid survivor-first branch, with a specific focus on reducing unallocated cash without blowing up drawdown.

It is based on the current findings from:

- [129-hyperliquid-final-age-ramp-backtest.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/129-hyperliquid-final-age-ramp-backtest.ipynb)
- [130-hyperliquid-post-floor-renormalisation.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/130-hyperliquid-post-floor-renormalisation.ipynb)
- [137-hyperliquid-survivor-first-hotspot-backtest.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/137-hyperliquid-survivor-first-hotspot-backtest.ipynb)
- [138-hyperliquid-survivor-first-sharpe-optimiser.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/138-hyperliquid-survivor-first-sharpe-optimiser.ipynb)
- [139-hyperliquid-survivor-first-sharpe-hotspot-optimiser.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/139-hyperliquid-survivor-first-sharpe-hotspot-optimiser.ipynb)
- [140-hyperliquid-survivor-first-sharpe-breadth-concentration-optimiser.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/140-hyperliquid-survivor-first-sharpe-breadth-concentration-optimiser.ipynb)
- [141-hyperliquid-survivor-first-sharpe-threshold-optimiser.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/141-hyperliquid-survivor-first-sharpe-threshold-optimiser.ipynb)
- [142-hyperliquid-survivor-first-equal-weight-recycle.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/142-hyperliquid-survivor-first-equal-weight-recycle.ipynb)
- [143-hyperliquid-survivor-first-waterfall.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/143-hyperliquid-survivor-first-waterfall.ipynb)
- [144-hyperliquid-survivor-first-capacity-aware-equal-weight.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/144-hyperliquid-survivor-first-capacity-aware-equal-weight.ipynb)
- [145-hyperliquid-equal-weight-recycle-hotspot-optimiser.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/145-hyperliquid-equal-weight-recycle-hotspot-optimiser.ipynb)
- [146-hyperliquid-equal-weight-recycle-walk-forward-validation.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/146-hyperliquid-equal-weight-recycle-walk-forward-validation.ipynb)
- [147-hyperliquid-equal-weight-recycle-event-exclusion-stress.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/147-hyperliquid-equal-weight-recycle-event-exclusion-stress.ipynb)
- [148-hyperliquid-equal-weight-recycle-execution-friction-stress.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/148-hyperliquid-equal-weight-recycle-execution-friction-stress.ipynb)
- [149-hyperliquid-equal-weight-recycle-universe-perturbation.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/149-hyperliquid-equal-weight-recycle-universe-perturbation.ipynb)
- [150-hyperliquid-equal-weight-recycle-allocator-ablation.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/150-hyperliquid-equal-weight-recycle-allocator-ablation.ipynb)
- [README.md](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/README.md)

## Current read

The main structural problem in the original final notebook was not a lack of vaults. It was that the strategy spread weight across too many candidates, many tickets became too small to trade, and the dropped tail was not recycled properly.

The later notebooks changed that picture:

- survivor-first re-normalisation fixed most of the fake underdeployment
- the remaining bottleneck is now much closer to real capacity and pool-size constraints
- Sharpe-optimised variants showed that broader books and lower TVL floors can smooth the path, but they also tend to leave a bit more cash idle

The practical implication is that the next ideas should focus on **allocation mechanics**, not on inventing a new signal family.

## Lessons learnt from the NB142 robustness run

The strongest new lesson is that NB142 now looks like a **real allocation architecture**, not just a lucky single backtest. The confidence does not come from one number, but from the pattern across NB145 to NB150:

- the local optimiser in NB145 stayed in the same family instead of escaping to a different regime
- the walk-forward notebook in NB146 kept deployment very high in every fold
- the event-exclusion notebook in NB147 showed real event sensitivity, but not a complete collapse from removing one short cluster
- the execution-friction notebook in NB148 showed the strategy is more sensitive to capacity than to small ticket thresholds
- the universe-perturbation notebook in NB149 showed the strategy is not a one-vault artefact
- the allocator ablation in NB150 showed that the final sizing rule really matters, and that deployment-aware evaluation gives a different answer from pure performance tables

### The deployment fix is more robust than the alpha magnitude

This is the most important distinction from the new batch.

NB145 found a supportive local plateau around:

- `max_assets_in_portfolio=18`
- `max_concentration=0.10`
- `min_tvl=7.5k`
- `min_age=0.075`
- `age_ramp_period=0.75`

Its fixed rerun delivered:

- `99.11%` cumulative return
- `211.88%` CAGR
- `3.85` Sharpe
- `17.53` Sortino
- `-6.21%` max drawdown
- `84.05%` final accepted / investable
- `87.33%` mean accepted / investable
- `14.95%` mean cash

That says the equal-weight recycle family is not a knife-edge point estimate. But the walk-forward results in NB146 show the return stream is still uneven through time:

- `90/30` scheme: `2/4` positive folds
- `120/30` scheme: `1/3` positive folds
- `120/45` scheme: `1/2` positive folds

At the same time, deployment remained strong in every fold:

- mean accepted deployment stayed around `94.9%`
- every fold stayed above `75%` deployment

So the honest read is: the allocator is robust, but the realised edge is still opportunistic rather than smooth.

### Event sensitivity is real, but this is not a one-day fake

NB147 showed how much of the result depended on the strongest realised days.

Baseline NB142:

- `90.71%` cumulative return
- `3.80` Sharpe
- `16.15` Sortino

Removing the `2026-02-04` to `2026-02-08` cluster:

- `47.87%` cumulative return
- `3.24` Sharpe
- `10.55` Sortino

Removing the top `5` gain days:

- `26.54%` cumulative return
- `2.67` Sharpe

Removing the top `10` gain days:

- `5.93%` cumulative return
- `0.97` Sharpe
- `1.47` Sortino

This means the strategy is not reducible to one lucky jump, but the magnitude of the final result was still strongly amplified by a relatively small number of exceptional days.

### Capacity remains the real bottleneck

NB148 is important because it shows where the strategy is actually fragile.

Baseline NB142:

- `90.71%` cumulative return
- `3.80` Sharpe
- `89.37%` mean accepted deployment

Higher minimum trade threshold:

- almost unchanged

Tighter pool cap:

- `78.37%` cumulative return
- `3.70` Sharpe
- `84.84%` mean accepted deployment

Lower allocation:

- `84.09%` cumulative return
- `3.83` Sharpe

Combined harsher case:

- `75.01%` cumulative return
- `3.72` Sharpe

The deployment breakthrough is therefore not a fragile ticket-rounding artefact. The true long-term limit is still vault capacity. That pushes future work towards capacity-aware deployment and concentration control rather than tiny rebalance-threshold tweaks.

### The strategy is not one-vault luck, but top winners still matter

NB149 removed the biggest contributors and reran the strategy.

Baseline rerun:

- `90.71%` cumulative return
- `3.80` Sharpe

Exclude top `1` PnL vault:

- `59.61%` cumulative return
- `2.67` Sharpe
- `-12%` max drawdown

Exclude top `3` PnL vaults:

- `43.60%` cumulative return
- `2.01` Sharpe
- `-9%` max drawdown

So the architecture survives those removals, which is good evidence against a single-vault artefact. But the step-down is still large, so the biggest winners clearly mattered to the final magnitude of the result.

### Allocator choice matters, and pure performance tables are not enough

NB150 held the thresholds fixed and changed only the final allocator:

- `signal_proportional_no_recycle`: `84.36%` cumulative return, `3.82` Sharpe, `17.54` Sortino
- `equal_weight_no_recycle`: `84.81%` cumulative return, `3.84` Sharpe, `17.92` Sortino
- `equal_weight_recycle`: `90.71%` cumulative return, `3.80` Sharpe, `16.15` Sortino
- `capacity_aware_equal_weight`: `91.89%` cumulative return, `3.79` Sharpe, `18.31` Sortino
- `waterfall`: `112.85%` cumulative return, `3.16` Sharpe, `-10%` max drawdown

This is a very useful lesson. If we looked only at Sharpe or Sortino, we might prefer a no-recycle allocator or the mild capacity-aware variant. If we looked only at raw return, waterfall would win. But those reads miss the whole reason these experiments were started: idle cash and deployability.

Once the earlier direct capital-utilisation audits are brought back into the picture, equal-weight recycle still looks like the cleanest production compromise.

### Practical conclusion

The best current read is:

- keep `age_ramp` as the selector
- keep survivor-first logic as the structural starting point
- treat equal-weight recycle as the current best deployable default
- treat the remaining problem as a capacity and concentration problem, not a signal problem
- be explicit that the strategy is deployable and structurally real, but still opportunistic and event-amplified

That means the next allocation ideas should try to improve capacity absorption and concentration discipline without giving back the deployment gains that NB142 achieved.

## Design principles

The next experiments should follow these rules:

- Keep `age_ramp` as the structural selector unless there is a very strong reason not to.
- Keep survivor-first logic as the starting point.
- Treat cash efficiency as a first-class metric, not just CAGR and Sharpe.
- Prefer simple sizing rules over complicated responsive weighting.
- Use diagnostics in the NB30a style for every experiment.
- Judge each idea on both deployment and path quality.

Core metrics to benchmark in every notebook:

- cumulative return
- CAGR
- Sharpe
- Sortino
- Calmar
- max drawdown
- final cash USD and cash % of equity
- final accepted / investable %
- mean accepted / investable %
- share of cycles above 50% deployment
- share of cycles above 75% deployment
- accepted position count
- mean and median accepted position size
- `capped_by_pool_size` count
- `individual_trade_size_too_small` count

## Priority 1: accepted-set equal weight with survivor-first recycling

### Idea

Use `age_ramp` only to decide which vaults survive into the accepted set. After removing the too-small tail, equal-weight the accepted survivors and recycle leftover cash only across names that still have capacity.

### Why this is worth testing

- It follows the old repo lesson that signals are often better for selection than for sizing.
- It directly attacks the current failure mode: capital stranded after small tickets are dropped.
- It is simpler than proportional signal weighting and easier to reason about.

### Implementation sketch

1. Build the ranked `age_ramp` candidate set.
2. Apply inclusion rules and the normal trade-size floor.
3. Keep only the vaults that can receive a real ticket.
4. Equal-weight across those accepted names.
5. Re-apply pool caps.
6. Recycle any leftover only across accepted names still below cap.

### What would count as success

- Mean deployment above the current Sharpe branch.
- Cash lower than the Sharpe branch but with no major drawdown blow-up.
- Fewer too-small flags than the baseline survivor-first branch.

### Main risk

- Equal weighting may still create too many borderline tickets if the accepted set remains too wide.

## Priority 2: capped waterfall across accepted survivors

### Idea

Use a waterfall or greedy allocator after the accepted set is known. Allocate first to the highest-ranked survivors, then continue down the list until capital is exhausted, while respecting concentration and pool-size caps.

### Why this is worth testing

- Waterfall logic historically deployed cash efficiently in earlier notebooks.
- It is naturally compatible with discrete ticket sizes.
- It should reduce the “many small leftovers” problem better than smooth proportional weights.

### Implementation sketch

1. Use the current survivor-first `age_ramp` selection.
2. Build the accepted set.
3. Allocate greedily from the top-ranked survivor downwards.
4. Respect `max_concentration`, pool-size caps, and minimum trade size.
5. Stop when the next ticket would be too small or no further names can absorb size.

### Variants worth checking

- pure waterfall
- waterfall with a minimum breadth floor
- waterfall with a mild equal-weight reserve across all accepted names first

### What would count as success

- Higher final and mean deployment than the broad Sharpe family.
- Drawdown still below the aggressive NB130-style branch.
- Clear reduction in idle cash caused by discrete ticket rounding.

### Main risk

- Concentration may rise too quickly and undo the risk improvements from the Sharpe family.

## Priority 3: capacity-aware equal weight

### Idea

Start from a simple equal-weight or near-equal-weight deployment across accepted survivors, then apply only a mild capacity-aware tilt so larger vaults can absorb more without making the whole system TVL-proportional.

### Why this is worth testing

- The remaining bottleneck now looks like genuine capacity.
- A mild capacity tilt may absorb cash better without creating a noisy TVL-chasing strategy.
- It preserves the “selection is separate from sizing” lesson.

### Candidate tilts

- `sqrt(pool_headroom)`
- capped `log(pool_headroom)`
- binary large/small vault multiplier
- available accepted size from previous cycle as a persistence-aware headroom proxy

### What would count as success

- Better deployment than plain equal-weight accepted survivors.
- Similar or better drawdown than the broader Sharpe family.
- Fewer pool-cap rejections on the final cycle.

### Main risk

- Even mild TVL-aware sizing can drift into hidden concentration.

## Priority 4: discrete knapsack-style allocator

### Idea

Formulate the final deployment as a discrete packing problem: choose a set of admissible trade sizes that maximises deployed capital subject to caps, minimum trade size, and breadth rules.

### Why this is interesting

- The current problem is partly discrete and rounding-driven.
- Knapsack logic directly addresses “how do we pack capital into legal tickets”.

### Why it is not first

- More engineering-heavy.
- Easier to overfit.
- Harder to explain than the simpler survivor-first methods.

### What would count as success

- Meaningful deployment gain over the simpler methods.
- No obvious concentration explosion.
- Cleaner final-cycle utilisation than survivor-first re-normalisation alone.

## Priority 5: residual cash sleeve only after the main book is correct

### Idea

Use a residual sleeve such as HLP only for the leftover cash after the main accepted-survivor book is already final.

### Why this is lower priority

- Earlier notebooks already showed HLP is not a magic answer.
- It can improve diagnostics without changing the real portfolio.
- It solves the last slice of idle cash, not the main structural issue.

### If tested, guardrails should be strict

- hard cap the sleeve weight
- verify realised end positions, not just alpha diagnostics
- compare to the no-sleeve baseline on drawdown and deployment

## Ideas to deprioritise

These do not look like the best next use of time:

- full signal-proportional sizing
- softmax or log-signal deployment as the main fix
- dispersion-aware switching
- HLP-first or HLP-heavy cash sweep modes
- new overlay signals introduced only to improve cash use
- age-bucket equal as a production replacement, because walk-forward already rejected that family

## Recommended notebook sequence

Suggested next experiment order:

1. Refine accepted-set equal weight with survivor-first recycling
2. Test a more disciplined capacity-aware equal-weight recycle variant
3. Test capped waterfall only as an upper-bound deployment benchmark
4. Explore a discrete knapsack-style allocator if simpler methods still leave meaningful cash idle
5. Test a residual cash sleeve only if the main allocator is already correct

## Decision criteria

An experiment should be considered promising only if:

- it improves mean deployment materially
- it does not worsen max drawdown too much
- it does not merely shift accounting while leaving realised cash unchanged
- it remains understandable enough to trust in production

The target is not zero idle cash. The target is to eliminate **wasted** idle cash while preserving the strategy’s risk discipline.
