# Why signal-responsive weighting fails, and what might work

## The evidence

Every signal-responsive weighting method tested across 25+ notebooks underperforms equal weight:

| Notebook | Method | Result vs equal weight |
|---|---|---|
| NB22 | Inverse volatility | Highest Sharpe (7.15) but CAGR only 9.76% |
| NB23b | Log-signal weighting | Worse |
| NB54-56 | PSR-based concentration | Worse drawdowns |
| NB59-64 | Rolling returns/sharpe/calmar/sterling as weights | All worse — strictly monotonic degradation |
| NB65 | Comprehensive analysis | "Signals are better for selection than sizing" |
| NB66 | Dual-signal (gate + weight) | Breakthrough, but blend_alpha=0.6 means 60% equal weight |
| NB70 | Metadata-adjusted signals (TVL, age) | Worse |
| NB71 | Rank composite weighting | Worse |
| NB72b | Dispersion-aware switching | Activated only 5.9% of time, worse |
| NB84 | Momentum acceleration (short/long ratio) | Avg Calmar 11.9 vs baselines 24-28 |

And NB83 proved the **Bayesian gate does nothing** — inclusion criteria (min_tvl=25k, min_age=0.3y) already filter all the same vaults. The gate signal is positive for every included vault at every timestamp.

## Why equal weight wins: root cause analysis

### 1. The strategy is already "equal weight + universe curation"

NB83 revealed the true architecture:
1. Curate vault universe (database quality, excluded protocols, survivorship measures)
2. Apply inclusion criteria (min_tvl, min_age)
3. Equal weight across survivors
4. Rebalance daily

Everything else — Bayesian gate, weight signals, blend function — is noise. The edge comes from **what's in the universe**, not how it's weighted.

### 2. Estimation error dominates signal

With ~7 months of daily data across ~30 vaults, any signal estimated from vault returns has enormous estimation error. To reliably say "vault A should get 2x the weight of vault B", you need a signal with SNR >> 1. But:
- Rolling Sharpe over 90 days has ~50% estimation error (standard result from statistics)
- Rolling returns are noisy by construction
- Momentum acceleration ratios amplify noise through division

Equal weight is the maximum-entropy (minimum-assumption) allocation. When estimation error is high, the regularisation benefit of equal weight overwhelms any signal.

### 3. All signals tested are variants of the same information

Every weight signal tested — rolling returns, Sharpe, Calmar, Sterling, PSR, momentum, rank composites — derives from **the same underlying data**: the vault's own return series. They are all functions of `close.pct_change()` over various windows. No amount of transformation (log, Bayesian shrinkage, ratios, ranks) can extract information that isn't in the raw returns.

### 4. The diversification premium is real

In a portfolio of ~30 weakly-correlated vaults, equal weight captures the full diversification premium. Any deviation concentrates into fewer return drivers, reducing diversification. The Sharpe ratio of an equal-weight portfolio of N uncorrelated assets scales as √N — this is a mathematical fact, not an empirical finding.

## What might actually work: approaches using different information

The key insight: to beat equal weight, you need information **not contained in individual vault return series**. All prior experiments used the same data differently. The following approaches use fundamentally different information sources.

### A. Cross-vault correlation clustering (most promising)

**Information source**: pairwise return correlations (cross-vault, not individual)

Equal weight treats all vaults as interchangeable. But if vaults A and B have 0.9 correlation (same underlying strategy), holding both equally is wasteful — you get the diversification benefit of one vault, not two.

**Approach**: cluster vaults by return correlation each rebalance period. Equal-weight across *clusters*, then equal-weight within clusters. Vaults in a large correlated cluster get less total weight than vaults that are unique diversifiers.

**Why it might work**: uses portfolio-level structure, not individual vault signals. Even with noisy correlation estimates, the clustering is robust — you only need to identify that vaults are "similar" or "different", not predict their returns.

**Implementation**: compute rolling pairwise correlations → hierarchical clustering → weight = 1/(cluster_size × num_clusters) per vault.

### B. Drawdown-state position sizing (risk management)

**Information source**: current drawdown state (observable, not predictive)

**Approach**: among gated vaults, reduce weight for vaults currently in drawdown > X% from their peak. Not predictive (doesn't try to forecast returns), purely a risk management overlay.

**Why it might work**: cuts losers faster. Equal weight holds a vault at full weight even when it's down 20% from peak. A drawdown-based rule reduces exposure to vaults that may be in structural decline.

**Implementation**: `weight = 1.0 if drawdown > -threshold else (1.0 + drawdown/threshold)`. Simple, no estimation error, uses real-time data.

### C. Vault age ramp-up (risk management)

**Information source**: vault age (structural, not return-based)

**Approach**: new vaults start with reduced weight that ramps up linearly over their first N months. A vault at age=0.3y (just past min_age) gets weight 0.3; a vault at age=1.0y gets full weight.

**Why it might work**: less data = more uncertainty about vault quality. Even though the vault passed inclusion criteria, you know less about a 4-month vault than a 12-month vault. This is a Bayesian allocation — shrink toward zero for uncertain vaults.

**Implementation**: `weight = min(1.0, age_years / ramp_period)`. No signal estimation needed.

### D. Market regime overlay (external information)

**Information source**: BTC/ETH price action (external to vault universe)

**Approach**: in high-crypto-volatility regimes (e.g., BTC realised vol > X%), reduce overall allocation and hold more cash. This isn't about vault weighting — it's about total portfolio risk management.

**Why it might work**: many Hyperliquid vaults have hidden crypto beta. During crypto crashes, even "market-neutral" vaults can drawdown. A volatility-triggered cash overlay would reduce exposure during these periods.

**Implementation**: `allocation = base_allocation * min(1.0, vol_target / realised_vol)`.

### E. Strategy-type diversification (metadata-based)

**Information source**: vault strategy classification (external metadata)

**Approach**: classify vaults as "market-neutral", "directional long", "directional short", "arbitrage", etc. Balance the portfolio across strategy types rather than equally across all vaults. This ensures exposure to diverse return drivers.

**Why it might work**: two "market-neutral" vaults may be more correlated with each other than with a "directional" vault. Strategy-type balancing forces diversification across return generators.

**Challenge**: requires manual or algorithmic classification of vault strategies. May not scale.

### F. Dynamic universe sizing by regime

**Information source**: cross-sectional signal dispersion or market volatility

**Approach**: instead of always holding max_assets=30, dynamically adjust the number of vaults. In high-confidence periods (strong signals, low cross-vault correlation), hold fewer concentrated vaults. In low-confidence periods, hold more for diversification.

**Why it might work**: the optimal number of positions isn't always 30. During periods when a few vaults clearly outperform, concentration helps. During uncertain periods, diversification helps.

## Recommended priority

1. **Correlation clustering (A)** — most theoretically grounded, uses genuinely new information
2. **Drawdown sizing (B)** — simplest to implement, pure risk management
3. **Age ramp-up (C)** — simple, no estimation needed
4. **Market regime (D)** — uses external data, addresses hidden beta risk
5. **Strategy-type (E)** — requires metadata, harder to scale
6. **Dynamic sizing (F)** — interesting but complex
