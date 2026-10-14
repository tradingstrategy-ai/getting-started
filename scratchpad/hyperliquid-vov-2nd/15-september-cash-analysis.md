# NB15 — September cash analysis

## September 2026 cash investigation

### Actual cash balances — 2026-01-01 through 2026-10-04 backtest, September focus

These are daily USDC balances as a fraction of total account equity. The lighter grey region in the asset-weight charts is cash; the darker grey region is invested in other vaults.

| Strategy | September mean cash | Peak cash | 30 September cash |
|:--|--:|--:|--:|
| V11 | 41.6% | 72.8% | 58.2% |
| A | 49.1% | 74.0% | 60.5% |
| C | 48.7% | 73.4% | 59.6% |
| G | 48.8% | 73.3% | 59.5% |

### Why the cash increased

The ranking selects six vaults without considering whether their combined position capacity can absorb the account. The source allocator then limits each target to both 33% of the deployable account budget and 33% of that vault’s TVL. Lower-ranked vaults cannot fill the gap: `max_capacity_assets = max_assets_in_portfolio = 6` disables the residual-capacity extension.

In A, Citadel leaves on 4 September and AceVault Hyper01 on 8 September. They return on 14 and 12 September respectively, reducing cash. Citadel leaves again on 18 September; AceVault Hyper01 and Octavious Maximus leave on 20 September. The last two are replaced by Buyback Spread Engine and Sequoia HyperStable Yield Optimizer. The archived score changes explain these rotations; the removed vaults pass the −16% return gate on the inspected dates.

Across September’s 15 decision cycles, **96.9% of the sum of A’s planned deployment shortfalls** comes from the combined concentration/TVL ceiling, 2.6% from rejected top-ups and 0.5% from allocation below the feasible ceiling. This sums repeated decision-level shortfalls, not lost profit or distinct cash dollars.

### Concrete example — decision on 20 September 2026

A has a $194,853 deployable budget. The six selected vaults have combined TVL of approximately $219,878; their 33%-of-TVL limits admit only $72,560 in total. All six targets reach their TVL limits before admission checks. The table shows target dollars, not new deposit requests.

| Selected vault | TVL | Target before admission | Final target |
|:--|--:|--:|--:|
| HYPErQuantum4 | $24,597 | $8,117 | $7,810 |
| Gucky_4coin_2dot5x | $13,875 | $4,579 | $3,532 |
| Mad Scientists | $52,495 | $17,323 | $17,323 |
| Buyback Spread Engine | $20,968 | $6,919 | $6,919 |
| Sequoia HyperStable Yield Optimizer | $16,161 | $5,333 | $5,333 |
| DOEZOE | $91,783 | $30,288 | $30,288 |

Pool limits leave **$122,293** of the deployable budget unused. HYPErQuantum4 and Gucky_4coin_2dot5x then reject **$1,354** of additional top-ups, leaving a $71,206 final target basket. Together with the approximately $3,977 deployment reserve, this predicts about **$127,624 cash**, matching the saved post-trade wallet balance. Cash is 64.2% of marked equity on that day.

### Deposit checks and other explanations

The inspected HYPErQuantum4 and Gucky_4coin_2dot5x rows have fresh previous-day permission observations, open-deposit flags and archived zero deposit caps; leader shares are approximately 5.38% and 5.19% on 20 September, below the strategy’s 5.5% policy. These checks reject top-ups rather than close the existing positions. DOEZOE is open on 20 September, then reports deposits disabled by its leader from the 22 September decision onward. By 30 September, rejected top-ups total $8,436; the concentration/TVL shortfall is still much larger, at $109,774.

No pending redemptions or pinned settlement capital are recorded on any September decision in these four accounts. This comparison imposes no extra NAV-freshness veto. The inspected rejected checks use known recent observations rather than an unknown/stale permission clock. The 2% deployment reserve and trade thresholds cannot explain cash above 60%.

By 20 September, all four strategies target the same $71,206 basket despite their different variance estimators and account sizes. Different weights cannot overcome the aggregate TVL ceiling; A’s larger capital also produces a higher cash percentage under the same absolute vault limits.

### Cash and allocation shortfalls — 2026-01-01 through 2026-10-04 backtest, September focus

Bars split the unallocated target budget into cap constraints, allocator slack and blocked top-ups. The line is actual wallet cash after trades, which also includes the deployment reserve and trade/accounting differences. Each bar is a separate decision snapshot, not a cumulative loss.

![September cash decomposition](_artifacts-restored-2026-10-07/15/54a3012575bb225b74792185adaeb1a7ef66722a208ee9c5e2ab9c6a8c47ca1a/september-cash/september-cash.png)

### Implication

September is mainly a basket-capacity problem. A useful next comparison would let selection account for usable capacity, or retain a larger incumbent when a proposed replacement contributes little deployable capital. Increasing the number of positions or relaxing TVL caps are other possible interventions, but should be judged by net profit and risk: filling cash with lower-quality vaults need not improve returns.
