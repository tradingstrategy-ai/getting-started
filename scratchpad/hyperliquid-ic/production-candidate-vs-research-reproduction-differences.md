# Production candidate versus research reproduction

This note documents why the independent A0/A0b research simulations do not exactly reproduce the Hyperliquid production candidate. The detailed experiment is in [08-research-a0b-production-comparison.ipynb](08-research-a0b-production-comparison.ipynb). Its saved metrics are in [`_artifacts-a0b/a0-a0b-production-metrics.csv`](_artifacts-a0b/a0-a0b-production-metrics.csv), and the complete vault membership audit is in [`_artifacts-a0b/a0-a0b-vault-membership.csv`](_artifacts-a0b/a0-a0b-vault-membership.csv).

## Measured comparison

The production candidate window is 2026-01-01 through 2026-07-08 inclusive. All independent simulations use the same starting capital and the same daily forward-filled research panel.

| implementation | final equity | cumulative return | CAGR | volatility | Sharpe | max drawdown | equity path |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A0 independent simulator | $161,482 | 7.65% | 15.40% | 21.86% | 0.76 | -15.44% | saved daily path |
| A0b independent simulator | $185,368 | 23.58% | 50.84% | 17.58% | 2.43 | -7.36% | saved daily path |
| Production current-source replay | $190,095 | 26.85% | 58.70% | not retained | 2.87 | -3.91% | summary only |
| Production archived candidate | $191,446 | 27.76% reported* | 61.72% | not reported | 2.88 | -4.44% | endpoint only |

A0b is 2.49% below the current-source production replay by final equity. Its Sharpe is 0.45 lower and its drawdown is 3.45 percentage points deeper. The large improvement from A0 to A0b shows that candidate-universe membership accounts for most of the original reproduction gap, while the residual difference comes from execution, timing and data-model details.

The full backfilled research period is 2025-09-13 through 2026-09-12. A0b produces $173,708 final equity, 15.85% CAGR, 17.74% volatility, 0.92 Sharpe and -8.59% drawdown. A matching full-history production result is unavailable because the old production engine inputs and its equity series were not retained.

\* The archived report states 27.76% cumulative return. $191,446 from a $150,000 start implies 27.63%; both values are retained in the notebook and CSV rather than silently changing the archived result.

## What A0 and A0b are

* **A0** is the independent forward-filled simulator using all addresses present in the research feature panel for the period.
* **A0b** uses the same independent simulator, accounting and six-position cap as A0. It additionally restricts the panel to the current production-style cached universe and removes the documented manual data-quality blacklist entry.
* Neither A0 nor A0b calls the production strategy engine. This is deliberate: A0 remains an independent check on the data, feature panel, forward filling and portfolio accounting.

The current production-style cache contains 339 addresses; after the manual blacklist, 338 remain in the allowlist. Intersecting that set with the research panel leaves 296 simulated addresses in the production window and 335 in the full-history window. The membership audit contains 532 research-panel addresses: 194 are outside the allowlist, one is manually blacklisted, 28 are selected by A0b in the production window, and A0 selects 33.

## Causes of the differences

### Universe snapshots

A0b uses `/Users/moo/.cache/indicators/vault-universe-tvl7500-top9999-age0.0-sort1Y-curbbf10d84.json`, generated 2026-09-09. The current-source production replay rebuilds the universe through `build_hyperliquid_vault_universe` and then applies engine metadata, denomination and trading-availability filters. The archived candidate used an older 2026-08-21 input snapshot. Identical headline parameters therefore do not guarantee identical addresses.

The allowlist is also applied retrospectively in A0b. It is a useful reconciliation control, not a point-in-time historical universe reconstruction.

### Eligibility and stateful gates

The production strategy in [`hyper-ai-v6.py`](/Users/moo/code/strategies/strategy/hyper-ai-v6.py) applies engine-level checks including `state.is_good_pair`, quarantine, the manual blacklist/mask, current TVL and candle availability, and stateful deposit/redemption availability through `can_deposit` and related accounting.

A0b applies the cached allowlist, the documented blacklist, the incumbent return gate and the research panel's causal NAV availability. It does not reproduce engine state, dynamic deposit capacity, quarantine state or every engine eligibility transition.

### Ranking and tie ordering

A0b ranks the research signal using the independent simulator's address ordering. The engine ranks pair objects using internal pair identifiers and its own source ordering. Equal or near-equal signals can therefore change the final selected slot and all subsequent weights, even when the signal formula is otherwise the same.

### Sizing and capital accounting

The production engine sizes against its net redeemable capital and applies AlphaModel normalisation, TVL headroom, per-vault limits, deployment thresholds and precise redemption/performance-fee accounting. A0b uses the independent inverse-variance/cap allocator with the shared research fee model. Both assume vault deposits and redemptions fill at NAV, but the capital base and state transitions can differ after each rebalance.

### Timing and marks

A0b consumes normalised daily feature dates and forward-fills each vault's latest causally available NAV. The production engine works with exact candle timestamps, engine cycle state and its own carried marks. Sparse observations, deposits, redemptions and intermediate marks can change the path even when the selected addresses match.

### Archive versus current replay

The archived production candidate and the current-source replay are not the same run. The archive references an older source/data snapshot and retains only headline metrics. The current replay was run from the current strategy source and current cached data on 2026-09-15, and retained summary output but not its daily equity series. The approximately $1,351 endpoint difference between those two production references cannot be uniquely attributed without the archived input snapshot and equity ledger.

## Interpretation

A0b demonstrates that applying production-like universe membership brings the independent research reproduction close to the production endpoint and preserves the same ordering of return, Sharpe and drawdown. It does not demonstrate exact production parity. The remaining gap is expected from the different universe snapshots, stateful eligibility, ranking order, timestamp handling and capital accounting.

The production-period chart therefore plots the saved A0/A0b daily paths and marks the production endpoint. It does not fabricate a daily production curve. Before using A0b for a deployment decision, run a contemporaneous production-engine backtest while saving the full equity and trade ledgers, then reconcile those ledgers against the A0b pool and trade files.

## References

* [A0b comparison notebook](08-research-a0b-production-comparison.ipynb)
* [A0b metrics](_artifacts-a0b/a0-a0b-production-metrics.csv)
* [A0/A0b vault membership audit](_artifacts-a0b/a0-a0b-vault-membership.csv)
* [A0/A0b concentration audit](_artifacts-a0b/a0-a0b-concentration.csv)
* [A0b run manifest](_artifacts-a0b/run-manifest.json)
* [Production strategy source](/Users/moo/code/strategies/strategy/hyper-ai-v6.py)
* [Production replay verification notebook](../hyperliquid-lower-vol/_build/verify-hyperai-window.ipynb)
