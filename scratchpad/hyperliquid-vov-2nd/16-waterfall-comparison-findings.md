# Experiment 16 — waterfall allocation comparison

## Key new insights

- **2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC):** waterfall improves profit for 2/4 matched strategies. The highest-profit account is G-W, with 56.19% CAGR, 2.46 Sharpe and -6.81% drawdown.
- **2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial):** waterfall improves profit for 3/4 matched strategies. The highest-profit account is C-W, with 30.96% CAGR, 1.73 Sharpe and -10.33% drawdown.

Waterfall changes risk-weight ordering into greedy dollar allocation. Its results therefore measure a different use of the risk estimator, rather than a new feature or ranking formula. Both allocators retain the six-position capacity ceiling; no residual-capacity extension is enabled.

## Summary of results

### 2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC)

| Arm | CAGR | Sharpe | Max drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: |
| V11 | 41.20% | 1.96 | -6.40% | 8.83% |
| V11-W | 31.57% | 1.55 | -6.64% | 8.39% |
| A | 51.77% | 2.30 | -6.35% | 10.18% |
| A-W | 48.89% | 2.14 | -6.07% | 9.89% |
| C | 47.56% | 2.12 | -6.93% | 10.08% |
| C-W | 51.35% | 2.23 | -6.08% | 9.98% |
| G | 47.28% | 2.11 | -7.72% | 10.03% |
| G-W | 56.19% | 2.46 | -6.81% | 10.07% |

### 2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial)

| Arm | CAGR | Sharpe | Max drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: |
| V11 | 16.35% | 1.28 | -7.92% | 42.06% |
| V11-W | 15.36% | 1.20 | -8.66% | 39.08% |
| A | 22.53% | 1.65 | -7.92% | 43.95% |
| A-W | 22.58% | 1.65 | -7.92% | 40.31% |
| C | 27.53% | 1.56 | -10.73% | 40.62% |
| C-W | 30.96% | 1.73 | -10.33% | 39.05% |
| G | 27.85% | 1.54 | -11.37% | 40.32% |
| G-W | 29.94% | 1.60 | -12.83% | 38.71% |

### September 2026 cash

| Strategy | Original mean cash | Waterfall mean cash | Change |
| --- | ---: | ---: | ---: |
| V11 | 41.6% | 39.7% | -1.89 pp |
| A | 49.1% | 48.5% | -0.62 pp |
| C | 48.7% | 48.9% | +0.11 pp |
| G | 48.8% | 49.5% | +0.66 pp |

## Robustness of results

All eight original-control accounts reproduce NB15 metrics. All sixteen accounts reconcile asset weights and position profit to equity, remain within six held vaults, and use known NAV at or before successful fill queries. Waterfall target ledgers check pre-admission concentration/TVL ceilings. Inherited deposit checks and rebalance bands can subsequently alter targets and realised holdings.

The largest update across these accounts is 13.57%; the largest single-vault share of positive profit is 44.8%. Tables attribute extreme updates to vault NAV observation intervals, BTC/ETH context and curator flags. These statistics do not establish independence from leading contributors.

Both periods have already been examined in earlier research; the long account overlaps the fresh 2026 period. Sparse observations, retrospective universe/guard membership, inherited fee assumptions and the partial-trim fee convention remain limitations. No production change or independent predictive confirmation is claimed.

### Dependence and useful leads

G-W’s 2026 gain over G is led by pmalt: $9,182, 100.7% of the net advantage. C-W’s full-history gain over C is led by Citadel: $17,265, 47.7% of the net advantage. These are ledger differences, not removal replays. The better results arise from changed exposures and timing; September remains capacity-limited. C-W is the stronger historical waterfall challenger; G-W has stronger 2026 performance but a deeper full-history drawdown.

### Funding correction

The uncorrected A-W run failed on 12 July 2026 with $94.63 of overspending after final sell-price charges. The executable treatments retain those charges and reduce buys only to available net synchronous proceeds. 2 decision queues required correction across the eight treatments, reducing requested buys by $170.06 in total.

## Strategy logic comparison

This table describes the rules replayed in both periods. A is the research benchmark; v11 is the deployed strategy's source configuration. The historical simulation uses the shared repaired archive and current frozen universe/guard, rather than a replay of recorded live decisions.

| Strategy | Ranking and score | Position sizing | Parent and change | Missing and sparse history |
|:--|:--|:--|:--|:--|
| **V11: deployed rules** | 60% 360-day CAGR + 40% 45-day Sortino. CAGR is clipped to 0–100% and Sortino to 0–3; each component is mapped to 0–1. | Original inverse variance, using the source 90-day volatility indicator. | Source `hyper-ai-v11.py` decision callback and parameters, apart from the two replay date ranges. The existing local edit only relaxes a backtest floating-point assertion. | Missing composite scores become zero in source selection; eligible unscored vaults can still enter through the normal ranking. Source risk fallback is retained. |
| **A: research benchmark** | 48% 360-day CAGR + 32% 45-day Sortino + 10% 180-day CAGR + 10% 30-day Sortino. Same clips as v11. | Original source 90-day inverse variance, exactly as v11. | NB14 A: changes the ranking formula from v11 while retaining source sizing and the original allocator. | `missing=True`: retain the source unscored-entry behaviour; do not invent a score for unavailable active components. Source risk fallback is retained. |
| **C: historical challenger** | Same four-input score as A. | Inverse regularised 90-day variance: empirical variance is blended with a positive leave-one-out peer median. Empirical weight is `m / (m + 30)`, where `m` counts actual daily observation updates. | NB14 C, derived from A: changes the risk estimator package while retaining the original allocator. | Causal daily NAV forward filling starts at the first observation. Partial histories are allowed; actual updates determine confidence. Missing risk uses peer support; an unusable basket forecast falls back to equal sizing. |
| **G: downside challenger** | Same four-input score as A. | Inverse regularised 90-day downside moment: mean squared negative returns, including zero contributions from non-negative days. Uses the same observation-count shrinkage. | NB14 G, derived from C: replaces individual and peer total variance with downside risk. | Same partial-history support as C. A loss-free vault receives positive peer risk where available; use total-variance peer support if downside support is unavailable, then the existing basket fallback. |

### Shared portfolio and execution rules

Every strategy uses a six-position limit, two-day decisions, entry rank 6, incumbent exit rank 8, a 98% deployment target, 33% concentration and pool-size caps, $7,500 minimum TVL and a 14-day return gate above −16%. Source deposit/redemption permissions, guard checks, leader-share policy, rank hysteresis and trade thresholds are retained. There is no additional dollar-cap allocator or quote-freshness veto in this comparison.

New capital is blocked when observed leader share is below 5.5%. The source buy and sell thresholds start at $75 and $750 respectively for the $150,000 account, with the source equity-scaling behaviour retained. Redemption modelling retains 10% of positive realised profit plus a 0.1% gross redemption allowance; this allowance is an assumption, not a verified venue fee. No additional vault slippage is imposed.

All strategies use NAV observations timestamped at or before each price query, and indicators from completed prior daily buckets. This NB14 timing convention is shared by v11 as well: it is a research execution model, not a change to v11's live trading rules. Last-known NAV does not establish the actual executable NAV during an archive gap. The inherited partial-trim fee calculation can apply a fee twice and is retained for comparison; differing turnover can affect its impact.

### Waterfall intervention

Each `-W` arm keeps its parent's performance ranking, eligibility, six-position basket limit, risk estimator, hysteresis, caps and execution model. The sole intervention forces the existing framework `waterfall=True` allocation path. Capital fills the highest **raw sizing weight** first, up to its concentration/TVL ceiling, then cascades to the next selected vault. V11/A use source inverse variance for this priority; C uses regularised variance; G uses regularised downside risk. Risk weights determine order rather than proportional dollar shares.

This is a sizing-priority waterfall, not a performance-score-order waterfall. No lower-ranked capacity-extension positions are introduced. Six selected small vaults can still leave cash when their combined capacity is below the deployable budget. Deposit checks subsequently reject blocked top-ups; this experiment adds no new admission-refill pass. Different holdings can change later selection through the inherited hysteresis.

An uncorrected A-W run failed on 12 July 2026: a buy exceeded net available cash by $94.63 after source fees. The source modifies sell prices after its buy-budget calculation, and its inherited partial-trim fee convention can further reduce proceeds. A research funding correction checks concrete planned sell quantities and final sell prices after the source callback. It scales buys only when they exceed current reserve plus those synchronous net proceeds, leaving ten reserve raw units for the framework's rounding tolerance. It preserves the inherited charges and records every intervention; it does not increase the portfolio cash reserve or inject capital. The correction is a no-op on successfully executed NB15 original trade queues, whose actual buys were funded.

| Arm | Ranking | Waterfall priority | Matched control |
| --- | --- | --- | --- |
| V11-W | Source two-input score | Source 90-day inverse variance | V11 |
| A-W | Four-input score | Source 90-day inverse variance | A |
| C-W | Four-input score | Regularised 90-day inverse variance | C |
| G-W | Four-input score | Regularised 90-day inverse downside moment | G |
