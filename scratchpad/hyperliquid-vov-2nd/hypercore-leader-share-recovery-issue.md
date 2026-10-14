# Restore archived HyperCore leader shares and policy caps; keep missing evidence NULL

## What has changed

The HyperCore permission recovery now publishes historical rows with `leader_fraction=NULL` and `max_deposit=NULL` where the previous archive contained a leader-share value and an explicit zero policy cap. The price row can survive with the same timestamp, write timestamp and Open permission, while its historical leader-share input disappears from the consumer dataset.

Concrete example, vault `0x3a6747c8e913085e243a2c22d188dafa8c6a612a` (Gucky):

| Field | Before recovery | Downloaded repaired export |
| --- | --- | --- |
| Price timestamp, UTC | 2026-04-11 04:22:05.613 | 2026-04-11 04:22:05.613 |
| Original `written_at`, UTC | 2026-04-11 04:22:06.999 | 2026-04-11 04:22:06.999 |
| `deposits_open` | true | true |
| `leader_fraction` | 0.05000280943338046 | NULL |
| `max_deposit` | 0.0 | NULL |

The compared HyperCore projections contain:

| Measurement | Previous archive | Repaired export |
| --- | ---: | ---: |
| HyperCore price rows | 1,530,404 | 1,759,599 |
| Non-NULL leader-share values | 1,452,449 | 5,916 |
| Non-NULL deposit caps | 15,458 | 51 |

These are exported row counts, **not counts of independent API observations**. The older export carried some leader shares forwards. The recovery correctly restores additional price rows, but largely removes the historical share/policy inputs.

Content hashes of the retained comparison files:

- Previous archive: `cec5c353c04d728c747088164af33a1f0f0f54f2ead00bdb1f3a5323018ef871`.
- Repaired export downloaded on 7 October 2026: `b45ce736510919270e52299711a072b75e23207d06f33bd2243efedbb978027f`.

## Why it has changed

[Recovery PR #1629](https://github.com/tradingstrategy-ai/web3-ethereum-defi/pull/1629), commit `a0da5c4571814504588e594084b5bba113c5fade`, introduced separate permission receipts and a deliberately strict capacity policy.

The migration first preserves raw evidence in `hypercore_legacy_price_evidence` and `hypercore_raw_parquet_evidence`, then executes this blanket update against the scanner price table:

```sql
UPDATE {table}
SET is_closed=NULL, allow_deposits=NULL, leader_fraction=NULL
```

See [permission_recovery.py](https://github.com/tradingstrategy-ai/web3-ethereum-defi/blob/a0da5c4571814504588e594084b5bba113c5fade/eth_defi/hyperliquid/permission_recovery.py#L313).

Legacy permission reconstruction restores `is_closed`, `allow_deposits` and relationship information with inferred price-clock provenance, but does not restore leader-share/capacity evidence into the selected snapshots. The exporter requires eligible capacity evidence to generate the low-share policy cap. The consumer fixes in [trading-strategy #253](https://github.com/tradingstrategy-ai/trading-strategy/pull/253) and [trade-executor #1670](https://github.com/tradingstrategy-ai/trade-executor/pull/1670) additionally discarded legacy caps without an independent capacity clock.

The reason was valid: historical portfolio time, API receipt time and database publication/write time are different clocks. Current or carried measurements must not silently become fresh historical observations. However, the repair used missing independent timing metadata as grounds to remove the underlying historical values from the published projection.

## How the change is wrong

1. **Missing timing metadata does not establish that an archived value is wrong.** Older schemas did not collect `capacity_observed_at`. Preserve their values and describe the timing uncertainty explicitly. A near-matching original write time is useful evidence to audit, although it alone does not authenticate a receipt.
2. **Permission recovery and leader-share recovery are inconsistent.** Inferred legacy flags can establish Open under the approved recovery policy, while the leader-share input from the historical record is discarded. Consumers consequently admit deposits that the same strategy previously blocked.
3. **It changes the effective trading policy.** `classify_hyperliquid_vault_deposit()` generates `max_deposit=0` for an open normal vault with leader share below 5.5%. This is our conservative trading policy, not a venue-reported dollar capacity. Removing its input silently disables that guard in historical replays.
4. **Reader changes cannot recreate emptied producer fields.** Retaining NULL correctly in the client does not recover a share value that is only present in archived evidence tables or backups.

The numerical impact is material. On unchanged source v11 rules, $150,000 initial cash and **2026-01-01 → 2026-10-05 end exclusive**, the earlier run returned 41.59% CAGR; the repaired dataset returns 33.47%. An artificial diagnostic using repaired prices plus the previous caps reaches 41.24%, explaining 95.7% of the final-equity gap. That diagnostic establishes the effect of the caps; it does not authenticate their history or supply a target that the data repair should optimise towards.

## How to restore the historical data, keeping unknown values NULL

1. **Recover the original evidence.** Use operator-selected pre-migration daily/HF DuckDB backups, `hypercore_legacy_price_evidence`, `hypercore_raw_parquet_evidence`, retained raw Parquet files and any original API-response logs. Preserve vault identity, source row key, original price/scan time, original write time, source hash and raw payload. Keep the repaired economic price history.
2. **Restore known leader shares without requiring a newly introduced independent clock.** Publish recoverable historical `leader_fraction` values and explicit historical policy caps with legacy provenance. Where an actual receipt time exists, retain it. Where it does not, retain the original source date and an explicitly inferred timing policy; keep the independent receipt field NULL rather than relabelling an approximation as measured evidence.
3. **Distinguish recorded snapshots from carried projections.** Older Parquet leader-share columns can contain forward-filled values. Recover the original measurement keys from scanner rows or raw payloads where possible; a later price update or migration publication must not refresh the age of a carried share. Preserve ambiguous carried values as legacy evidence with unknown measurement timing rather than manufacturing fresh observations.
4. **Keep genuinely missing fields NULL.** If no historical share is available, `leader_fraction` remains NULL. If no cap or sufficient share-policy input is available, the policy cap remains NULL. Do not substitute zero, a current share, an assumed sufficient share, or unlimited capacity. An explicit historical zero stays distinct from NULL. Retain explicit venue closure/disabled flags independently.
5. **Preserve source coherence and precedence.** Do not combine a current permission response with an unrelated old share and present them as one measured response. Keep independent capacity history/provenance if needed. Genuine newer responses and explicit unknown/conflict boundaries retain their precedence; restoring legacy shares must not resurrect corrupted permission flags or overwrite verified newer data.
6. **Republish the repaired files and matching generation metadata.** Export the recovered historical inputs, refresh content hashes/manifests and make the generation available to consumers. Consumer readers should honour the documented legacy fallback and freshness rules, rather than discarding a value solely because its independent clock is absent.

Acceptance should compare matched historical rows and NULL masks against the selected evidence, confirm that repeated scans/publication do not refresh original ages, preserve all repaired price values, and verify that missing share/cap evidence stays NULL. Include daily and HF cases, repeated exports/migration, conflicting sources, genuine unknown responses and low-share policy blocks.

Related: [original timestamp issue #1628](https://github.com/tradingstrategy-ai/web3-ethereum-defi/issues/1628), [recovery #1629](https://github.com/tradingstrategy-ai/web3-ethereum-defi/pull/1629), [export completion #1630](https://github.com/tradingstrategy-ai/web3-ethereum-defi/pull/1630), [permission/capacity separation #1596](https://github.com/tradingstrategy-ai/web3-ethereum-defi/pull/1596).
