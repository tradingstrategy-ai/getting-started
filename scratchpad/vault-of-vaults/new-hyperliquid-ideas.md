# New Hyperliquid ideas

Age and TVL are the only clearly validated structural factors so far. By contrast, most raw share-price transforms have failed to beat equal weight consistently, so the next round should focus less on new ratio variants and more on residual, regime-aware and metadata-aware features.

This note turns the NB87 and NB88 review into a standalone experiment backlog. The aim is not to assume that share price has no information, but to stop treating raw share-price momentum and drawdown measures as if they were already the right representation.

## Audit notes

- NB87 suggests a broad `min_tvl` plateau, not a single magic threshold. The useful region looks more like roughly `20k-50k` than a unique optimum at `25k`.
- NB87 also shows that threshold effects are smaller than the robustness of the equal-weight architecture itself. That is encouraging, but it means we should be careful about over-interpreting one best cell.
- NB88's winner is an age prior, not a pure share-price alpha factor. Age ramp works because it is a structural uncertainty discount, not because it extracts a subtle edge from price dynamics.
- NB88 also changes both the universe and the backtest window, so the improvement cannot be read as a clean confirmation of NB87. Wide-universe effects, start-date effects and survivorship still need to be separated.
- The main open question is still valid: share price should communicate something, but probably not through the same rolling-ratio family that has already been tried many times.

## Prioritised experiment ideas

### Residualised share-price alpha

- Hypothesis: raw vault returns are too contaminated by common market and ecosystem moves, but residual returns may contain manager-specific skill.
- Feature definition: regress vault returns on simple common factors such as BTC, ETH, HYPE and a vault-market average, then test residual momentum, residual Sharpe, residual trend strength and residual hit-rate.
- Notebook test shape: compare raw signals against residualised versions in both curated and wide universes, with equal weight and age-ramp as baselines.
- Success condition: residual signals beat their raw equivalents and keep an edge after controlling for age and TVL.
- Failure mode / criticism: this may just repackage noise, and the factor model may be unstable in the sparse early period.

### Underwater geometry

- Hypothesis: the shape of a vault's drawdown history contains more information than current drawdown alone.
- Feature definition: time under water, drawdown area, recovery speed, new-high frequency, and ratio of recovery days to drawdown days.
- Notebook test shape: rank vaults by these recovery-quality features instead of cutting weight when they are already in drawdown.
- Success condition: improved Calmar or Sharpe versus equal weight without materially worse tail concentration.
- Failure mode / criticism: these features may still be backward-looking and may mostly proxy for age.

### Regime-capture fingerprints

- Hypothesis: good vaults distinguish themselves by how they behave in specific market regimes, not by unconditional return ratios.
- Feature definition: upside capture, downside capture, behaviour during vol spikes, crash resilience, weekend behaviour and trend-versus-chop performance.
- Notebook test shape: classify days into simple regimes first, then build cross-sectional ranks from regime-conditional performance.
- Success condition: regime-aware ranks outperform unconditional rolling metrics and remain useful in the mature window.
- Failure mode / criticism: regime labels can become a source of overfitting if they are too elaborate.

### Flow and leader-conviction factors

- Hypothesis: vault metadata may reveal trust, stickiness and deployer conviction earlier than price alone.
- Feature definition: follower growth, vault equity growth, leader fraction, days following, return per unit of volume, and simple flow acceleration measures.
- Notebook test shape: test metadata-only ranks, then combine them with age-ramp and residual price features.
- Success condition: metadata adds explanatory power after age and TVL controls and improves ranking stability.
- Failure mode / criticism: these fields may mostly restate popularity and size, so they need to be tested against TVL directly.

### Soft priors vs hard filters

- Hypothesis: hard cut-offs lose useful information, while soft priors preserve diversification and still penalise weak vaults.
- Feature definition: age ramps, TVL ramps, age-by-TVL interaction terms, and continuous penalties instead of binary inclusion rules.
- Notebook test shape: compare strict filters against soft ramps using the same portfolio construction rules.
- Success condition: soft priors match or beat hard filters with smoother performance across nearby parameter choices.
- Failure mode / criticism: this may not produce new alpha and may only make the strategy look more elegant.

### Shrinkage correlations

- Hypothesis: diversification signals failed because the correlation estimates were too noisy, not because correlation is irrelevant.
- Feature definition: shrinkage covariance, longer windows, rank-based similarity, correlation-to-market-average and mild cluster penalties rather than full reallocation.
- Notebook test shape: retry correlation-aware sizing with weak adjustments layered on top of equal weight or age-ramp.
- Success condition: lower concentration and similar or better Calmar without the instability seen in NB88.
- Failure mode / criticism: even improved estimates may still be too noisy for a young vault universe.

### Walk-forward validation

- Hypothesis: any surviving signal should work across multiple folds, not just one hand-picked backtest span.
- Feature definition: fold-by-fold performance versus equal weight and age-ramp, plus win rate, degradation rate and parameter drift.
- Notebook test shape: run rolling train-test splits for the most promising ideas only, rather than for every exploratory notebook.
- Success condition: the signal wins in most folds and does not rely on one launch-heavy period.
- Failure mode / criticism: this may show that the apparent edge was mostly a start-date and survivorship artefact.

## Default evaluation protocol

- Always report results separately for the early ecosystem window (`2025-04-01` to `2025-07-31`) and the mature window (`2025-08-01` to `2026-03-11`).
- Test each idea in both the curated universe and the wide universe.
- Keep equal weight and age-ramp as the default baselines in every notebook.
- Reject any signal that disappears once age and TVL are included as controls.
- Reject any signal that improves CAGR mainly by increasing drawdown, kurtosis or dependence on one or two vaults.
- Prefer rank-based use of noisy features over raw proportional weighting unless there is clear evidence that magnitude matters.
