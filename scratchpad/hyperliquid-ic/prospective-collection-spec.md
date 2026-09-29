# Prospective collection specification

This specification is the data-gap deliverable for the Hyperliquid vault IC research. It is designed to produce a genuine point-in-time panel before any outcome is observed. The current bulk cache cannot provide this history retrospectively.

At each native two-day decision, create a UTC snapshot after the completed daily observation is consumable. Use the decision timestamp recorded in the snapshot as the information boundary; the current diagnostic approximation is the labelled calendar date plus two days, rounded from the cached publication-lag p95. A prospective collector should record the actual timestamp rather than rely on this approximation.

For every Hypercore vault known at the snapshot, save:

- `address`, chain and vault identity, including the inception/creation timestamp as reported at the snapshot;
- every raw observation poll since the previous snapshot (each poll's `timestamp`, cleaned `share_price`, `raw_share_price`, `total_assets`, source `written_at`, response status, `hypercore_repair_status`, `hypercore_source` and retrieval timestamp), rather than only the latest daily value;
- collector `retrieved_at`, the decision `available_ts`, and the source revision/hash;
- the BTC daily reference bar used for that decision, including its interval, close timestamp and source/hash;
- `deposits_open` and `redemption_open` as known at the decision boundary;
- performance-fee and management-fee mode/rates, including whether each is internalised in NAV;
- the raw observation count, last fresh timestamp, gap length and fresh coverage;
- the production indicator values used by the engine at that decision: `return_gate`, `cagr_sortino_weight`, `inverse_vol`, TVL inclusion and deposit eligibility;
- the engine's actual decision output: selected basket, per-vault weights, cash residual, tie-break ordering and reason for every excluded candidate;
- the frozen source file hash and the code/configuration hash used to generate the snapshot.

Write the raw response and a manifest before the next decision's outcomes mature. The manifest must contain retrieval time, decision boundary, schema, row count, vault count, source revision and SHA-256 for each file. Do not overwrite a snapshot; append a new immutable snapshot directory keyed by decision timestamp.

Use a source `written_at` watermark (or retain a full raw re-dump) when collecting the next snapshot. Providers may revise an already-seen observation timestamp in place, so retain every version keyed by `(timestamp, written_at)` and resolve the as-of value using `written_at <= decision_ts`.

The collector must retain failed, closed and delisted vaults whenever a raw observation exists. Unknown deposit status is recorded as unknown, not open. A missing observation is distinct from an unchanged NAV. Rows marked `_carried` by the provider are retained for provenance but do not count as fresh endpoints. No follower count, leader activity, social field, follower deposit flow or later closure metadata may enter the predictor panel.

The research loader should consume snapshots with a backward as-of join satisfying `available_ts <= decision_ts`. The feature panel must pass a truncated-prefix test: adding a later snapshot cannot change any feature, eligibility flag or matured label before the truncation boundary. Labels are written only after their declared 7, 14, 21, 30, 45, 60 and 90-day horizons mature. Define label entry as the first executable NAV at or after the recorded decision boundary; do not include a pre-decision or merely published mark in the forward holding interval.

The first prospective shadow decision begins only after the feature catalogue, selected horizon, model, eligibility rules, caps, fee treatment and allocator are frozen. Save forecasts and candidate holdings before each future outcome is known. Continue collection if the initial 90-day shadow period is underpowered; do not move its start date after observing results.
