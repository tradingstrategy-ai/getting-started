# Earlier Hyperliquid allocation and capacity experiments

Reviewed 12 October 2026. This is a source and saved-output audit of the earlier research in `vault-of-vaults`, `hyperliquid-waterfall-rc`, `hyperliquid-ic`, `hyperliquid-vault-model` and `hyperliquid-lower-vol`. No backtests were rerun. Historical results retain each notebook's own archive, pricing, execution and fee assumptions; they are not directly comparable with repaired NB15 results.

## What the earlier work addressed

The earlier work distinguishes several reasons for cash: weights diluted across candidates that never receive capital; discarded tickets below trading floors; selected vaults reaching TVL or concentration ceilings; closed deposit windows; and intentional exposure reductions. Only the third mechanism dominates the September 2026 NB15 diagnosis. Methods that repair the other mechanisms cannot increase the combined capacity of an already capped basket.

| Folder and experiments | Mechanism tested | Finding and relevance to NB15 |
| --- | --- | --- |
| `vault-of-vaults` NB62–64, NB69 | Alternative sizing, cash diagnostics and capacity attribution | Identified both weighting-related underdeployment and TVL ceilings. More deployment did not consistently improve risk-adjusted returns. |
| `vault-of-vaults` NB129–133 | Select survivors before normalising; equal deployment; prune small tickets; residual HLP sleeve | NB130 repaired denominator dilution. NB132 pruning did not change the result. NB133 increased reported accepted capital without changing realised cash or the equity curve; the sleeve was not an effective deployment fix. |
| `vault-of-vaults` NB142–144 and NB150 | Equal-weight recycling, capped waterfall and capacity-aware equal sizing | Recycling and waterfall materially improved deployment. The actual capacity tilt is `clip(sqrt(TVL/min_tvl), 1, 2)` after selection; some README descriptions incorrectly say log(TVL). All methods still operate on a selected, bounded basket. |
| `vault-of-vaults` NB154–158 | Waterfall walk-forward and stress studies, followed by redemption-aware cash targeting | Waterfall remained promising on that archive and broad basket, with regime dependence. It does not demonstrate that waterfall can deploy money beyond a basket's summed capacity. |
| `vault-of-vaults` NB73 and NB133 | HLP weighting boosts, sweeps, fixed tranches and a capped residual sleeve | NB73's saved narrative reports worse drawdowns and no sufficient return improvement from special HLP treatment. NB133 did not change realised deployment. HLP overflow remains a separate allocation hypothesis requiring a fully wired trade path. |
| `hyperliquid-waterfall-rc` NB33–35 | Deposit-aware selection and basket breadth | NB33 skips closed unheld entrants in favour of the next depositable candidate, while held vaults can remain. This repairs wasted entry slots. Its cash diagnostics explicitly identify the remaining fixed-basket capacity ceiling. NB35 tests wider baskets under these admission rules. |
| `hyperliquid-waterfall-rc` NB67–68 | Capital size, pool participation, concentration and breadth | Direct predecessor of the current capacity concern. Doubling capital exposed capacity limits; changing pool participation was more consistently helpful than adding positions. Wider nominal baskets did not produce proportional effective diversification. |
| `hyperliquid-waterfall-rc` NB69–73 | Equal, risk, score, softmax and blended sizing; lookbacks and allocation parameter searches | Sizing rankings depend on the concentration and pool caps. These experiments retain top-N selection and redistribute only inside the basket. |
| `hyperliquid-ic` NB21–22 | Separate position-count, portfolio-weight and historical TVL-cap relaxations | Explicitly tested the limits, including admitting all eligible candidates to sizing. Attractive measured risk was confounded by stale marks and concentrated contributors; the detailed decomposition withdrew the broad-position recommendation. |
| `hyperliquid-ic` accepted-cap and steady-vault sizing work | Clip original requested allocations, preserve cash, compare redistribution and cash-matched controls | These deliberately constrain deployment. They address allocation discipline and exposure, rather than extending capacity beyond the chosen basket. |
| `hyperliquid-vault-model` NB07 and NB09 | Core plus young-vault satellites; additive breadth and sleeve dose | NB07 satellites displaced core slots. NB09 preserves the six-slot core and adds satellite positions, but uses a predetermined sleeve budget. All five 15% additive-sleeve construction arms underperform their anchor on the saved development/full results. This is not a residual-only capacity-extension test. |
| `hyperliquid-lower-vol` NB40 | Position/cap sensitivity and quality floors with cash sleeves | Investigates whether capital should remain unallocated when candidates fail a quality floor. Deliberate quality-related cash must be distinguished from capacity-related cash. |

## Saved allocator comparison from the original vault-of-vaults folder

The following table is transcribed from NB150's saved output, rather than its older introductory narrative. Period: **1 August 2025–10 March 2026**, $100,000 initial capital, daily decisions, age-ramp selection, at most 20 positions, 12% portfolio concentration, 20% vault-TVL participation and a 98% target budget. Mean cash is realised account cash; accepted/investable is a decision-time target diagnostic.

| Allocator | CAGR | Sharpe | Mean cash | Mean accepted / investable |
| --- | ---: | ---: | ---: | ---: |
| Signal-proportional, no recycle | 169.12% | 3.73 | 19.53% | 82.55% |
| Equal weight, no recycle | 165.08% | 3.64 | 20.66% | 81.40% |
| Equal weight, recycle | 183.10% | 3.50 | 12.99% | 89.29% |
| Capacity-aware equal weight | 186.91% | 3.64 | 17.40% | 84.75% |
| Capped waterfall | 268.98% | 3.47 | 4.09% | 98.52% |

This confirms real deployment improvements under that setup. NB150's heading still quotes an obsolete waterfall drawdown of about 10%; the corrected NB154 rerun quotes 4.5%. Historical summaries must be reconciled with outputs before reusing their conclusions.

## Closest capital-capacity comparison

Waterfall-rc NB67 records the following controlled capital/pool-cap comparison for **1 January–9 July 2026**, six positions, 33% concentration, two-day decisions and 60-day inverse-volatility sizing. These historical results describe that particular strategy and dataset.

| Initial capital | Vault-TVL participation cap | CAGR | Maximum drawdown |
| --- | ---: | ---: | ---: |
| $75,000 | 15% | 35.13% | −7.08% |
| $75,000 | 25% | 39.74% | −6.32% |
| $150,000 | 15% | 6.31% | −13.31% |
| $150,000 | 25% | 26.65% | −7.93% |

NB68 extends the $150,000 / 25% / 33% arm: six positions give 26.65% CAGR, seven 10.40%, and eight 21.34%. Increasing breadth did not monotonically improve profitability. Its realised effective breadth is only about 3.2–4.8 across the tested six/eight-slot configurations.

## What transfers to the current research

1. **Record the reason for every deployment shortfall.** Earlier ticket dilution differs from NB15's simultaneous saturation of six vaults. Keep requested targets, capacity ceilings, admission rejections, final targets, executed holdings and realised cash separate.
2. **Reuse survivor-first sizing, recycling and waterfall as mechanism controls.** NB15 already selects before sizing and redistributes within the selected basket. These controls have limited ability to recover September cash while the same six vaults remain selected and capped.
3. **Make capacity and capital size explicit in comparisons.** Earlier NB67 shows how the same signal and risk weights behave differently at another account size. Express capacity in executable dollars, accounting for held value and deposit permissions.
4. **Test conditional extra positions separately from replacing or resizing the core.** Preserve the six-slot core's normal targets; use only otherwise idle capital for depositable lower-ranked candidates, with explicit quality and capacity rules. Compare against cash and a fixed broader basket. NB09's fixed-budget satellite results do not answer this residual-only question.
5. **Keep idle capital available when the marginal candidate is poor.** Earlier broader-basket, HLP and unrestricted-limit treatments did not establish that maximum deployment maximises profit. Report incremental PnL and drawdown alongside utilisation.

The exact missing comparison in the current folder is a conditional capacity-extension or capacity-aware replacement rule under NB15's repaired data and execution conventions. Earlier research already tests several adjacent mechanisms, so it should supply controls and implementation ideas rather than being treated as unexplored.

## References

- [Earlier cash diagnosis](../vault-of-vaults/cash-left-table.md) and [allocation follow-up notes](../vault-of-vaults/more-cash-allocation-ideas.md).
- [Allocator ablation NB150](../vault-of-vaults/150-hyperliquid-equal-weight-recycle-allocator-ablation.ipynb), [waterfall validation NB154](../vault-of-vaults/154-hyperliquid-waterfall-walk-forward-validation.ipynb) and [release candidate NB158](../vault-of-vaults/158-backtest-hyperliquid-waterfall-release-candidate.ipynb).
- [Deposit-aware selection NB33](../hyperliquid-waterfall-rc/33-backtest-gated-inverse-vol-deposit-aware.ipynb), [capital/cap comparison NB67](../hyperliquid-waterfall-rc/67-backtest-150k-pool-cap-25pct.ipynb), [breadth NB68](../hyperliquid-waterfall-rc/68-backtest-breadth-7-8-at-75k-150k.ipynb) and [sizing NB69](../hyperliquid-waterfall-rc/69-backtest-weighting-methods-150k.ipynb).
- [Allocation-limit decomposition](../hyperliquid-ic/allocation-decomposition-summary-01.md), [additive satellite NB09](../hyperliquid-vault-model/09-research-breadth-sleeve-dose-response.ipynb) and [quality/cash NB40](../hyperliquid-lower-vol/40-backtest-lead-forensics-cash-sleeve.ipynb).
- [Current September diagnosis](15-september-cash-analysis.md).
