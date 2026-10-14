## The issue

> **7 October follow-up:** the repositories and data have now been updated and the experiments rerun. The repaired source reaches 33.47% CAGR; a controlled legacy-cap restoration explains 95.7% of its remaining equity gap to the earlier benchmark. The historical findings below describe the earlier input generation. See [the repaired-data rerun](repaired-data-rerun-2026-10-07.md) for current results and permission-clock qualifications.

HyperCore deposit permission is stored alongside price history without an independent timestamp for when the permission was actually observed. Price updates can preserve an existing permission flag while replacing its apparent observation time. Export then carries permission flags forwards without carrying the original permission observation timestamp.

Confirmed by inspection of current master `788dc71c198680407c059728e66ff9be652cd01f` on 2026-10-06:

- [High-frequency upsert](https://github.com/tradingstrategy-ai/web3-ethereum-defi/blob/788dc71c198680407c059728e66ff9be652cd01f/eth_defi/hyperliquid/high_freq_metrics.py#L229-L239) retains `is_closed` and `allow_deposits` through `COALESCE`, but unconditionally assigns `written_at = EXCLUDED.written_at`.
- [Daily upsert](https://github.com/tradingstrategy-ai/web3-ethereum-defi/blob/788dc71c198680407c059728e66ff9be652cd01f/eth_defi/hyperliquid/daily_metrics.py#L558-L568) has the same behaviour.
- [HyperCore export](https://github.com/tradingstrategy-ai/web3-ethereum-defi/blob/788dc71c198680407c059728e66ff9be652cd01f/eth_defi/hyperliquid/vault_data_export.py#L424-L498) forward-fills snapshot fields and exports the price row's `written_at`, without a separate permission observation clock.

The current consumer in `tradingstrategy.alternative_data.vault.convert_vault_prices_to_vault_state()` uses `max(price timestamp, written_at)`, rounded upwards to the first decision bucket. Missing or stale HyperCore permission blocks new deposits after its historical cutoff.

### Example of the provenance loss

A September row has an explicitly recorded open permission and a September observation/write time. An October price-only update supplies no new permission flags. The upsert retains the September flag but changes `written_at` to October. The consumer can no longer establish that this permission was already known in September.

This is a confirmed code-level producer/consumer contract defect. It is not proof that this particular upsert caused every October-stamped row in the published archive.

## Why it is wrong

`written_at` may correctly describe the latest row write. It cannot simultaneously identify the original observation time of a retained or forward-filled permission field.

This has two failure modes:

1. **Historical evidence moves forwards:** a retained old flag gets a newer row-write timestamp and disappears from earlier backtest decisions.
2. **Stale evidence appears fresh:** an old permission carried onto a newer price row inherits that row's recent write time, concealing the age of the permission measurement.

Hyperliquid's API supplies current permission flags alongside historical portfolio prices. A historical price timestamp is not evidence that permission was measured at that historical time. Dropping `written_at` from the consumer or substituting the price date would risk look-ahead. Republishing a genuinely recorded historical observation, however, must preserve its actual observation time.

### DOEZOE evidence — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Vault: `0xcae0d1558b70b92ee9fd0acb20cb639c8c28ae69`, HyperCore chain ID 9999. These are stored price-row flags, not independently certified permission measurements.

| Evidence | Earlier dense archive | Current archive |
| --- | --- | --- |
| Price rows on 17 September | 21, carrying Open | 1, carrying Open |
| Write times for those rows | 17–18 September | 5 October, 22:50:50.271 UTC |
| First stored Closed row | Price time 21 September, 11:48:00.756 UTC; write time 11:48:02.468 UTC | Price time 5 October, 22:50:34.859 UTC; write time 22:50:50.271 UTC |
| Flags on 22–27 September | Closed; reason “Vault deposits disabled by leader” | Open, stamped 5 October |
| Source strategy entry on 18 September | Accepted | Blocked with reason `unknown` |

The source runs agree through 14 September and first diverge on 16 September. With identical v11 rules, capital and dates, the earlier saved result has 41.59% CAGR and the fresh current-input run has 21.13%. Replacing only 15–27 September deposit state raises fresh-run CAGR to 33.76%; replacing that interval's prices, indicators, TVL and state raises it to 35.52%.

These substitutions demonstrate material sensitivity to historical inputs. They do not establish that every older flag is correct or reproduce the complete older archive. NAV values and intraday sampling also differ. Neither a performance target nor a Parquet footer commit identifies which publisher operation caused the replacement.

## How to fix

1. **Record permission observations independently of prices.** Prefer an append-only series keyed by vault and scanner observation time, with `permission_observed_at`, an observation ID/source, nullable API flags and a coherent snapshot of relevant policy inputs. New permission observations create new records even when the API's latest price timestamp has not advanced. Corrected observations should retain their version/audit trail.
2. **Separate the clocks.** Keep row-write/publication time distinct from permission observation time. Price-only updates, overlap upserts, backfills, compaction and republication must not overwrite or refresh the original permission clock.
3. **Preserve provenance through export.** If price rows carry permission as a convenience, carry the complete permission observation and its original timestamp together. A later explicit unknown response must not silently inherit a prior open flag through per-field filling. Do not imply a new measurement just because another price row exists.
4. **Keep permission separate from capacity policy.** Preserve explicit closure/permission flags. The conservative leader-share zero-cap policy needs its own actual input observation time; a carried share cannot establish fresh capacity. Honour the contract introduced by #1596.
5. **Coordinate the consumer change.** Update Trading Strategy's schema/projection and state loader, then trade-executor's lookup/age diagnostics to use the latest permission observation available by the decision time. Use the original observation clock for freshness. Maintain appropriate decision-boundary rounding and conservative unknown handling; do not infer September permission from a flag first observed in October. See [Trading Strategy #251](https://github.com/tradingstrategy-ai/trading-strategy/pull/251).
6. **Migrate and republish safely.** Add schema/version changes, preserve existing snapshots, reconstruct only provenance supported by retained observations, and regenerate cleaned archives and matching readiness manifests after recovery. Expose coverage and missing/unknown-state diagnostics.

Implementation checks should cover retained flags during price-only overlap updates; unchanged price timestamps with newly measured permission; historical fetching with current flags; forward-fill ageing; explicit unknown snapshots; daily boundary handling; idempotent rebuilds; and coexistence of restored history with newer observations.

## What we should restore from old backups

### Priority: original permission evidence

- Recover pre-replacement Hyperliquid scanner DuckDB backups, including the daily and high-frequency price tables and any original API-response/scan logs. Extract `is_closed`, `allow_deposits`, original scanner receipt/write timestamps, vault identity and source provenance. Preserve independently recorded leader-share observations for capacity reconstruction.
- Merge recovered permission observations into the new history; do not reset the live database to an old backup or discard newer observations.
- For DOEZOE, investigate at least 15–28 September, particularly the 21 September recorded transition and Closed observations afterwards. Extend recovery through 4 October if suitable backups exist. We must recover both Open and Closed evidence, rather than selectively restoring entries that improve returns.
- The older exported archive already contains forward-filled values. Its row-write timestamps are useful evidence but are not automatically the original permission measurement times. Prefer original scanner responses. Only derive an observation timestamp where the backup's provenance supports it; otherwise retain an explicit legacy/unknown provenance marker.
- Older permissive parser defaults cannot be certified as real observations without source evidence, as documented in #1596. Do not fabricate historical observation times from price dates, current metadata, later API fetches or desired strategy results.

### Preserve dense prices and reproducibility inputs separately

- Preserve older dense price, TVL, PnL checkpoints and relevant metadata/guard snapshots in immutable versioned backups. Validate NAV reconstruction separately from permission recovery; an older price is not necessarily economically more accurate.
- Available local earlier archive: `/Users/moo/code/strategies/cache/hyper-ai/vaults/downloads/vault-prices.parquet`, SHA-256 `93fe067eb89fca316c05b8fb942cd98639eedf17d786bb23f7a6ae99e7ec4158`. This is an exported fallback, not the original scanner database. Its HyperCore price history ends during 28 September; it is insufficient for full October reproduction.
- Current comparison archive: `/Users/moo/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet`, SHA-256 `cec5c353c04d728c747088164af33a1f0f0f54f2ead00bdb1f3a5323018ef871`. Preserve it as well before any repair.
- Locate the original complete snapshot through 4 October, including permission provenance, prices, TVL and metadata. Keep source hashes and recovery manifests so consumers can compare identical inputs. Recovered September data alone does not establish full reproduction of the original 41.59% result.

Recovery is complete when proven historical permission observations survive price updates/republication with their original times, later observations remain intact, missing history is explicit, and the repaired producer/consumer path reproduces admission decisions on matched evidence without using future observations.
