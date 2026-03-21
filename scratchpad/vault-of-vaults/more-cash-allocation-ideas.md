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

## Correction notice (2026-03-19)

All notebooks from NB63 onwards were affected by a cache bug in Hyperliquid vault universe curation. The bug caused incorrect vault universe data to be used in backtests. The results below were updated after rerunning NB150 on 2026-03-19 with corrected data. See `rerun-differences.md` for the full rerun table.

The most significant change is that **waterfall allocation is no longer the worst risk profile**. The old waterfall result (Sharpe 3.16, MaxDD -10%) was an artefact of the buggy universe. Corrected waterfall achieves Sharpe 3.47 and MaxDD -4%, which reverses the original decision to choose equal-weight recycle over waterfall.

## Lessons learnt from the NB142 robustness run

NB142 looks like a real allocation architecture, not just a lucky single backtest. The confidence comes from the pattern across NB145 to NB150:

- the local optimiser in NB145 stayed in the same family instead of escaping to a different regime
- the walk-forward notebook in NB146 kept deployment very high in every fold
- the event-exclusion notebook in NB147 showed real event sensitivity, but not a complete collapse from removing one short cluster
- the execution-friction notebook in NB148 showed the strategy is more sensitive to capacity than to small ticket thresholds
- the universe-perturbation notebook in NB149 showed the strategy is not a one-vault artefact
- the allocator ablation in NB150 showed that waterfall is now competitive on risk while delivering the highest CAGR

### Allocator ablation (NB150 — rerun 2026-03-19)

NB150 held the thresholds fixed and changed only the final allocator.

Performance:

| Allocator | Cum. return | CAGR | Sharpe | Sortino | Max DD |
|---|---|---|---|---|---|
| `signal_proportional_no_recycle` | 82.10% | 169.1% | **3.73** | 14.19 | **-3%** |
| `equal_weight_no_recycle` | 80.44% | 165.1% | 3.64 | 12.75 | -4% |
| `equal_weight_recycle` | 87.77% | 183.1% | 3.50 | 10.65 | -5% |
| `capacity_aware_equal_weight` | 89.30% | 186.9% | 3.64 | 13.10 | -4% |
| `waterfall` | **120.45%** | **269.0%** | 3.47 | 13.29 | -4% |

Deployment:

| Allocator | Mean accepted / investable | Mean cash % | Final cash % | Cycles > 75% deployed |
|---|---|---|---|---|
| `signal_proportional_no_recycle` | 82.6% | 19.5% | 29.2% | 91.9% |
| `equal_weight_no_recycle` | 81.4% | 20.7% | 29.1% | 97.3% |
| `equal_weight_recycle` | 89.3% | 13.0% | 17.3% | 94.6% |
| `capacity_aware_equal_weight` | 84.8% | 17.4% | 26.7% | 98.2% |
| `waterfall` | **98.5%** | **4.1%** | **2.1%** | **100.0%** |

Key changes versus the old (buggy) run:

- **Waterfall** went from the worst risk profile (Sharpe 3.16, MaxDD -10%) to competitive (Sharpe 3.47, MaxDD -4%). It now leads on CAGR by a wide margin while matching the middle of the pack on risk. It also dominates deployment: 98.5% mean accepted/investable, only 4.1% mean cash, and 100% of cycles above 75% deployed.
- **equal_weight_recycle** now has the **worst** MaxDD (-5%) and worst Sortino (10.65) of all five allocators. Its deployment advantage (89.3% accepted) is real but much smaller than waterfall's (98.5%).
- **capacity_aware_equal_weight** emerges as the most balanced choice on performance: second-best CAGR, tied-best MaxDD, second-best Sharpe. However its deployment (84.8% accepted, 17.4% mean cash) is worse than equal_weight_recycle.
- **signal_proportional_no_recycle** has the best Sharpe (3.73) and best MaxDD (-3%) but lowest CAGR and worst deployment (82.6% accepted, 19.5% cash).

The production shortlist should now be:

1. **Waterfall** — highest CAGR by far (269%), competitive risk (Sharpe 3.47, MaxDD -4%), and best deployment (98.5% accepted, 4.1% cash). Needs walk-forward validation of the corrected results.
2. **equal_weight_recycle** — second-best deployment (89.3% accepted, 13.0% cash), moderate CAGR (183.1%), but worst MaxDD (-5%) and Sortino.
3. **capacity_aware_equal_weight** — most balanced performance profile (186.9% CAGR, Sharpe 3.64, MaxDD -4%) but weaker deployment (84.8% accepted, 17.4% cash).

### Practical conclusion

The best current read is:

- keep `age_ramp` as the selector
- keep survivor-first logic as the structural starting point
- **waterfall deserves walk-forward validation** as a production candidate — the risk objection that ruled it out was based on buggy data
- **capacity_aware_equal_weight** is the conservative fallback if waterfall concentration proves fragile out-of-sample
- equal-weight recycle remains a viable option but is no longer the default recommendation
- treat the remaining problem as a capacity and concentration problem, not a signal problem
- be explicit that the strategy is deployable and structurally real, but still opportunistic and event-amplified

That means the next allocation ideas should validate the waterfall's corrected risk profile out-of-sample, and compare it against capacity-aware equal weight under realistic friction.

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

## Priority 2: walk-forward validation of waterfall

### Idea

The NB150 rerun (2026-03-19) showed that waterfall now has the best CAGR (269%) with competitive risk (Sharpe 3.47, MaxDD -4%). The old risk objection (Sharpe 3.16, MaxDD -10%) was based on buggy universe data. Waterfall needs walk-forward validation before it can replace equal-weight recycle as the production default.

### Implementation sketch

1. Use the current survivor-first `age_ramp` selection with waterfall allocation.
2. Run walk-forward with the same fold structure as NB146.
3. Compare holdout performance against equal-weight recycle and capacity-aware equal weight.

### Variants worth checking

- pure waterfall
- waterfall with a minimum breadth floor
- waterfall with a mild equal-weight reserve across all accepted names first

### What would count as success

- Waterfall maintains its CAGR advantage out-of-sample.
- MaxDD stays below -6% across folds (confirming the corrected -4% is not an artefact).
- Sharpe stays above 3.0 across folds.

### Main risk

- Concentration may still rise in specific folds and undo the risk improvements seen in the full-period backtest.

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

Updated after the 2026-03-19 universe cache fix and NB150 rerun.

Suggested next experiment order:

1. Walk-forward validate waterfall with corrected data (highest priority — the risk objection was based on buggy results)
2. Walk-forward validate capacity-aware equal weight as a conservative alternative
3. Refine accepted-set equal weight with survivor-first recycling
4. Explore a discrete knapsack-style allocator if simpler methods still leave meaningful cash idle
5. Test a residual cash sleeve only if the main allocator is already correct

## Decision criteria

An experiment should be considered promising only if:

- it improves mean deployment materially
- it does not worsen max drawdown too much
- it does not merely shift accounting while leaving realised cash unchanged
- it remains understandable enough to trust in production

The target is not zero idle cash. The target is to eliminate **wasted** idle cash while preserving the strategy’s risk discipline.
