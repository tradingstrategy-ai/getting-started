# Experiment 15 — allocation candidates versus deployed v11

## Summary of results

### 2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC)

| Strategy | Net profit | CAGR | Sharpe | Max drawdown |
|:--|--:|--:|--:|--:|
| V11 | $44,521 | 41.20% | 1.96 | -6.40% |
| A | $55,430 | 51.77% | 2.30 | -6.35% |
| C | $51,111 | 47.56% | 2.12 | -6.93% |
| G | $50,819 | 47.28% | 2.11 | -7.72% |

### 2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial)

| Strategy | Net profit | CAGR | Sharpe | Max drawdown |
|:--|--:|--:|--:|--:|
| V11 | $108,947 | 16.35% | 1.28 | -7.92% |
| A | $162,108 | 22.53% | 1.65 | -7.92% |
| C | $210,443 | 27.53% | 1.56 | -10.73% |
| G | $213,794 | 27.85% | 1.54 | -11.37% |

## Key new insights

- **2026:** A has the highest profit ($55,430), with 51.77% CAGR, 2.30 Sharpe and -6.35% maximum drawdown.
  - A versus V11: profit $+10,909; CAGR +10.57 percentage points; Sharpe +0.34; drawdown +0.06 percentage points.
  - C versus A: profit $-4,319; CAGR -4.21 percentage points; Sharpe -0.18; drawdown -0.58 percentage points.
  - G versus C: profit $-292; CAGR -0.28 percentage points; Sharpe -0.01; drawdown -0.79 percentage points.
- **Full history:** G has the highest profit ($213,794), with 27.85% CAGR, 1.54 Sharpe and -11.37% maximum drawdown.
  - A versus V11: profit $+53,161; CAGR +6.18 percentage points; Sharpe +0.37; drawdown +0.00 percentage points.
  - C versus A: profit $+48,335; CAGR +4.99 percentage points; Sharpe -0.09; drawdown -2.82 percentage points.
  - G versus C: profit $+3,352; CAGR +0.33 percentage points; Sharpe -0.02; drawdown -0.64 percentage points.

A versus V11 changes the ranking formula with source sizing held fixed. C versus A changes a risk-estimation package, including partial-history support and filling, so its advantage cannot be attributed to shrinkage alone. G versus C changes the downside functional and its peer prior. These are historical comparisons, not independent statistical confirmation.

## Robustness of results

All eight accounts reconcile asset weights to equity and position profit to net account profit. A/C/G reproduce NB14 metrics under the shared NAV timing convention. Every successful vault fill matches an observation at or before its query, after undoing the inherited partial-trim fee adjustment for the timing check. Maximum positions remain six.

The full-history results include young vaults, sparse observations, empty-universe cash periods and previously searched years. Current universe/guard membership is retrospective. No quote-freshness veto is imposed. The inherited partial-trim fee issue and assumed redemption allowance remain material limitations.

Across the eight accounts, the largest single account update is 13.57%; the largest positive-profit concentration in one vault is 44.8%. The tables below attribute the strongest updates to actual NAV intervals and market context.

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


### Interpretation of the comparison

A versus v11 improves both periods with source sizing held fixed: the four-input ranking earns about $10,909 more in fresh 2026 and $53,161 more over full history. Its 2026 Sharpe rises from 1.96 to 2.30, with slightly smaller drawdown; full-history Sharpe rises from 1.28 to 1.65 with the same −7.92% maximum drawdown. This is the clearest favourable comparison in this notebook.

C and G improve full-history CAGR further, but lose to A in fresh 2026. Their long gain is concentrated in earlier years: 2024 Q4 returns are approximately 47.2% for C and 48.1% for G, versus 17.0% for A. The biggest long-run updates are 13.02% and 13.57%, compared with A’s 6.62%. Several NAV marks span roughly a week; the underlying BTC/ETH interval returns are about +19.6%/+17.1%. Road to 10 Million supplies the largest contribution on that update, alongside FFLGN and Delta_01. The observations support the recorded movement, while actual executable NAV during sparse intervals remains uncertain.

Retain A as the current-period research benchmark and C as the main historical sizing challenger. G earns only $3,352 more than C over full history, with larger drawdown. These comparisons justify a frozen subsequent-period evaluation; the already searched history does not establish a production replacement.
