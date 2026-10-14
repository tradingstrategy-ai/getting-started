# Root cause of the experiment 04/05 v11 discrepancy

> **Latest follow-up, 7 October 2026:** producer PR #1634 restores archived leader shares and policy caps; trading-strategy #255 and trade-executor #1671 retain them without inventing an independent capacity clock. Fresh 01–05 reruns use the restored publication. Source v11 now reaches **41.20% CAGR**, versus the earlier 41.59%; the first 558 chronological trades match. See [the restored-data rerun](restored-data-rerun-2026-10-07.md). The findings below refer to earlier input generations.

Investigated on 2026-10-06. References: [04](04-opt-score-matrix.ipynb), [05](05-opt-score-calibration-selection-cash.ipynb), and the reusable [input-swap script](analyse_05_replication.py).

## Conclusion

The earlier “data drift” explanation was too broad and did not establish a cause. The investigation identifies a specific interaction between republished historical observations and the loader's point-in-time deposit admission rules. September observations in the newer price archive have October `written_at` timestamps. The loader consequently moves their deposit-state records into October; September entries then fail with unknown availability. There are also changed NAV values and intraday sampling.

**Follow-up after reviewing the producer PRs:** this identifies the numerical mechanism, not a defect in the `max(...)` rule itself. Hyperliquid permission flags are current snapshots, whereas price timestamps can be historical. The exporter preserves the source database's `written_at`; publication alone does not necessarily rewrite it. The October stamps could reflect later historical fetching or database updates. Reliable historical permission must retain its own observation provenance. See the deposit availability follow-up below before interpreting either archive as ground truth.

This is not a comparison of different backtesting periods. Both saved source runs use 2026-01-01 → 2026-10-05, end exclusive, UTC, with $150,000 and 139 two-day cycles. The source v11 run and the exact-formula research variant agree on the complete trade ledger and equity within each experiment's own inputs.

Fresh controlled runs recover 70.7% of the $21,699.44 final-equity gap by replacing only 15–27 September inputs. A further $5,480.22 is identifiable as a different final DOEZOE valuation on exactly the same share count. These two components account for 96.0% of the original gap. They do not constitute a complete fresh reproduction of 41.59% CAGR: the full older October raw snapshot is no longer available locally.

## Why notebook 04 still reports a successful replication

### Saved-state comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

The current 04 presentation path deliberately preserves earlier results. Its successful parity assertions do not establish parity with the data freshly loaded by 05.

| Check | Current notebook 04 behaviour |
| --- | --- |
| Execution mode | `REUSE_SAVED_EXPERIMENT = True` |
| Engine | `SavedExperiment`, whose `engine_calls` remains zero |
| Source result | Reads saved metrics and `State.read_json_file()` |
| Exact-formula result | Reads another saved state from the same original experiment |
| Replication assertion | Compares those two saved equity curves and complete trade ledgers |
| Fresh raw price/permission load | Does not occur in this path |

This preserves the original 41.59% result correctly. Describing a recent report refresh as a fresh source backtest on today's raw archive would be misleading. See `score_matrix_report.py`, especially `SavedExperiment.__init__()` and `run()`.

## Where the runs first diverge

### Source equity comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Trades were sorted chronologically by `(opened_at, trade_id)`; `get_all_trades()` alone groups trades by position. The original and new source ledgers and equity match through 14 September. Their first divergence is on 16 September.

| Valuation date | 04 source equity | 05 source equity | Difference |
| --- | ---: | ---: | ---: |
| 2026-09-16 | $183,950.89 | $183,392.97 | −$557.91 |
| 2026-09-18 | $182,666.81 | $182,072.25 | −$594.56 |
| 2026-09-20 | $187,783.04 | $178,823.19 | −$8,959.85 |
| 2026-10-04 | $194,928.64 | $173,229.20 | −$21,699.44 |

On 16 September, changed opening marks for existing Octavious Maximus and AceVault Hyper01 positions contribute to the initial valuation difference. The old run buys Citadel and Mad Scientists; the new run only buys Mad Scientists. The large divergence follows the different 18 September deposit decision.

## The decisive admission difference

### DOEZOE entry evidence — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Both saved source states retain the deposit admission decision in `visualisation.calculations`. This is direct execution evidence, rather than an inference from rounded performance metrics.

| Observation | Earlier inputs / 04 | New inputs / 05 |
| --- | --- | --- |
| Raw DOEZOE samples on 17 September | 21 | 1 |
| `deposits_open` in raw data | `true` | `true` |
| `written_at` of those samples | 17–18 September | 5 October, 22:50:50.271 UTC |
| Loader availability bucket for the republished sample | September | 6 October |
| 18 September DOEZOE entry decision | Accepted | Blocked: `unknown` |
| 18 September trades | Three, including DOEZOE entry and Citadel exit | Zero |

The chain is:

1. `convert_vault_prices_to_vault_state()` computes the HyperCore effective timestamp as `max(source timestamp, written_at)` and rounds it upwards to the next daily decision bucket.
2. Republished September rows stamped in October therefore cannot provide September state, even when they contain `deposits_open=true`.
3. `BacktestPricing._lookup_vault_state()` requires a sample at or before the decision within the configured tolerance. The frozen 05 DOEZOE state frame has no new September records after 15 September.
4. After the 11 April historical cutoff, missing or stale HyperCore state rejects deposits with reason `unknown`.
5. The unchanged v11 selector skips the rejected entry. The strategy misses the profitable DOEZOE exposure that the original run admitted.

Relevant implementation: `tradingstrategy/alternative_data/vault.py`, `convert_vault_prices_to_vault_state()`; `tradeexecutor/backtest/backtest_pricing.py`, `_lookup_vault_state()` and the HyperCore deposit check; and `strategy/hyper-ai-v11.py`, the entry admission check in `decide_trades()`.

The ranking also changes: DOEZOE's active 60% CAGR / 40% Sortino score for the 17 September observation falls from 0.893167 to 0.752485. However, the saved execution log explicitly identifies unknown deposit availability as the blocked-entry reason. Its 14-day return remains above the −16% gate in both archives. This was not a Sharpe-versus-Sortino mix-up or a return-gate rejection.

## Historical inputs actually differ

### Raw HyperCore cadence — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

These are raw observation counts across all HyperCore vaults in each parquet, before daily resampling. The older local file ends on 28 September; it is used only for complete 15–27 September days in the controlled runs.

| Raw observation date | Earlier dense cache | 05 input cache |
| --- | ---: | ---: |
| 2026-09-13 | 11,247 | 11,199 |
| 2026-09-14 | 10,859 | 5,954 |
| 2026-09-15 | 10,827 | 297 |
| 2026-09-16 | 10,286 | 297 |
| 2026-09-17 | 10,936 | 297 |
| 2026-09-18 | 11,072 | 297 |

The newer archive has approximately one observation per vault per day from 15–26 September. Daily candles consequently have equal open and close for the vaults during that interval. The converter labels the day's first observation as its opening price at midnight, even if the only observation is late that evening. That changes simulated execution and valuation timing as well as returns.

DOEZOE's 17 September daily closing NAV also differs: 2.1638406973 in the earlier dense cache versus 1.8889326396 in the new cache. Sparse sampling alone does not establish why the upstream reconstructed closing NAV changed.

The older dense file's daily closes reproduce 04's saved rolling CAGR values to floating-point precision for DOEZOE, Citadel, Octavious Maximus and AceVault Hyper01 through 27 September. This ties the file to the original experiment independently of its modification time.

Inputs inspected:

- Earlier dense archive: `/Users/moo/code/strategies/cache/hyper-ai/vaults/downloads/vault-prices.parquet`, 10,254,373 rows, 262,800,920 bytes.
- Fresh-loader archive: `/Users/moo/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet`, 10,080,124 rows, 258,643,953 bytes.
- Actual frozen 05 universe: `_artifacts-calibration-05/universe.pickle`.

The ordinary vault data loader downloads or reuses the currently published object in its client cache; the downloader uses a 12-hour cache lifetime. A user does not need to change a notebook or manually replace data for a fresh experiment to pick up a republished historical object. The present 04 saved-report path does not call this loader.

## Controlled source runs

### Input substitution results — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Each diagnostic executes the unchanged production v11 source through the real engine in its own run directory, with one engine call. Parameters, initial capital, cycle, fees and the 513-vault universe are fixed. Only 15–27 September inputs are substituted. Recalculated indicators use a separate input cache namespace. The missing `tantalus` vault is not restored.

| Source case | Final equity | CAGR | Sharpe | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: |
| Original 04 reference, saved | $194,928.64 | 41.59% | 2.00 | −6.40% |
| Fresh 05 inputs | $173,229.20 | 21.13% | 1.23 | −11.33% |
| Earlier candles; 05 indicators and deposit state | $173,664.53 | 21.53% | 1.24 | −11.11% |
| Earlier candles and recalculated indicators; 05 TVL and deposit state | $173,664.53 | 21.53% | 1.24 | −11.11% |
| Earlier deposit state only; 05 prices and indicators | $186,720.89 | 33.76% | 1.67 | −6.72% |
| Earlier candles, indicators, TVL and deposit state | $188,578.43 | 35.52% | 1.75 | −6.40% |

The recalculated indicator set includes inclusion indicators as well as price indicators; the fourth row is not a pure individual-feature ablation. Nevertheless, it produces the same realised path as the preceding row. Restoring state alone provides much larger recovery than restoring candles/indicators while retaining the missing state. The treatments interact, so their differences should not be treated as an additive causal decomposition.

### Remaining terminal valuation difference — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

After the complete September substitution, the DOEZOE position holds exactly the same number of shares as the original 04 source. Its different terminal net mark explains most of the remaining gap. This is a terminal accounting comparison, not another strategy backtest.

| DOEZOE position at final valuation | Original 04 source | Restored September run |
| --- | ---: | ---: |
| Shares | 10,187.94982100425826415503222 | 10,187.94982100425826415503222 |
| Net position value | $35,421.55 | $29,941.33 |
| Difference | | −$5,480.22 |

The September substitution recovers $15,349.23 of the original $21,699.44 gap, leaving $6,350.21. The DOEZOE terminal valuation accounts for $5,480.22 of that remainder; other allocation, valuation and trading differences account for the remaining $869.98. These are mutually separated accounting components for these particular runs, not proof of a complete original-data reproduction.

## What is ruled out, and what remains uncertain

- The compared source runs use the same dates, capital, cycle and scoring rules. Annualisation and a long-versus-short period comparison do not explain this gap.
- The research formula does not lose this return relative to source v11 on identical inputs: their complete ledgers and equity match in both experiments.
- The ten strategy/guard/harness/framework files recorded by 04 still hash-match. This limited list does not cover every reader, dataset generator or dependency, so it cannot alone rule out all implementation differences.
- `tantalus` is absent in the new universe, but it was not held in the original source run. Recovery occurs while keeping it absent. Its disappearance does not explain the observed September admission failure.
- Fresh diagnostic engine executions reproduce 05's 21.13% control, so the diagnosis does not rely on reloading that result from the research engine cache.
- The input change and loader/admission mechanism are demonstrated locally. Why the upstream publisher replaced the dense observations, changed NAV values and assigned October write timestamps requires inspection of that publisher. Parquet footer commit messages are provenance clues, not proof of the responsible backend change.
- Full fresh reproduction of 41.59% requires the complete old snapshot, including prices, TVL, metadata and deposit observations through 4 October. Available dense input stops on 28 September. Neither result establishes which upstream reconstructed NAV is economically correct.

## Corrective actions

1. Preserve historical permission observations separately from prices, with an immutable `permission_observed_at` and source provenance. Store price-row update and publication times separately. An October fetch of historical prices cannot establish September permission; a rebuilt price archive must retain genuinely recorded September permission observations.
2. Pin raw price, metadata and permission snapshots and their content hashes for cross-notebook comparisons. A hash of only the strategy source or a filename/mtime-based cache stamp is insufficient.
3. Add preflight diagnostics for observation cadence, opening-observation time, deposit-state age and unknown-admission rates before accepting a freshly loaded snapshot as benchmark-equivalent.
4. Label saved-state presentation refreshes explicitly. Reserve “fresh replication” for an actual engine execution on identified inputs.
5. Retain 05's current outputs as results on its frozen snapshot. Re-run its treatments on the restored benchmark inputs before comparing them with the earlier 41.59% hand-picked formula.

No production trading rule or availability policy was changed during this analysis. Ignoring `written_at` indiscriminately would hide the issue and risk look-ahead; the durable correction is to preserve the true historical observation time.

## Reproduction evidence

Generated diagnostics are retained locally under ignored `_artifacts-root-cause-05/`: `input-swap-results.csv`, `source-equity-comparison.csv`, `deposit-admission-events.csv`, `terminal-positions.csv`, `hypercore-raw-cadence.csv`, `doez-17-september-raw.csv`, `parquet-provenance.json`, and the complete engine states. The archived `executed-script.py` preserves the exact diagnostic script associated with the executed fingerprints; its third-case wording was subsequently clarified without changing the computation.

Run the reusable script with `TQDM_LOGGABLE_FORCE=stdout poetry run python scratchpad/hyperliquid-vov-2nd/analyse_05_replication.py`. Its two parquet paths and frozen 05 universe must remain available and unchanged for these particular results to reproduce.

## Deposit availability follow-up

Reviewed on 2026-10-06 in response to the question whether `max(price timestamp, written_at)` is correct.

### The timing rule is justified for a newly fetched snapshot

The Hyperliquid API response contains historical portfolio prices alongside current `isClosed` and `allowDeposits` flags. The high-frequency collector assigns those flags only to the latest row of each response, leaves earlier rows without a new permission measurement, and records the fetch/write time. The exporter subsequently carries permission flags forwards within a vault's history. A historical price point therefore does not by itself establish a historical permission observation.

For a flag first fetched on 5 October, making it available only in October avoids using future knowledge in September. For a genuine flag observed on 17 September and published again in October, historical availability should remain in September. These cases require different provenance; the price timestamp alone cannot distinguish them.

The consumer's daily rounding upwards is appropriate for midnight decision cycles: an observation received at 18:00 is first usable at the next midnight. Rejecting unknown or stale permission after the historical cutoff is also the documented conservative policy. [Trading Strategy PR #251](https://github.com/tradingstrategy-ai/trading-strategy/pull/251) explicitly introduced delayed-observation handling; its regression covers flags becoming visible only after they were observed.

### Current `written_at` is not a dedicated permission clock

In the inspected high-frequency producer:

- `fetch_and_store_vault_high_freq()` sets `written_at=now` for fetched price rows.
- `upsert_high_freq_prices()` retains existing permission fields through `COALESCE` when the incoming row has no new flags, but always updates `written_at=EXCLUDED.written_at`.
- `_prepare_hypercore_export()` forwards the stored `written_at` without replacing it with the export time, and carries permission values forwards without a separate timestamp for the original permission measurement.

Consequently, updating an old price row can move the apparent availability of a retained permission into the future. Conversely, forward-filled permission can appear fresh because a later price row has a recent write time. These are identifiable limitations of the schema and code; the local parquets do not prove which producer operation caused the particular September replacement.

Relevant files: `eth_defi/hyperliquid/high_freq_metrics.py`, especially the upsert around lines 220–239 and snapshot assignment around lines 556–568; `eth_defi/hyperliquid/vault_data_export.py`, `_prepare_hypercore_export()` around lines 424–498. The [upstream collector](https://github.com/tradingstrategy-ai/web3-ethereum-defi/blob/master/eth_defi/hyperliquid/high_freq_metrics.py) contains the same handling.

### Permission classification has been corrected, but legacy evidence has limits

[web3-ethereum-defi PR #1596](https://github.com/tradingstrategy-ai/web3-ethereum-defi/pull/1596) separates venue permission from the conservative 5.5% leader-share capacity policy:

- Explicit `isClosed=true` or normal-vault `allowDeposits=false` means deposits are closed.
- Missing required API flags mean permission is unknown.
- Explicitly open permission with an actually observed low leader share retains `deposits_open=true` and sets `max_deposit=0` as the strategy's capacity policy.
- An absent amount limit does not establish permission.

The PR also states that older parser defaults cannot be distinguished from explicit observations without the original responses. Thus, an older row containing `true` is not automatically certified reliable just because it is timestamped in September. The current source classifier is consistent with the corrected contract; full historical reliability requires retained source observations and their actual measurement times.

### Interpretation of the sparse archive observation

The lower September row counts and changed NAV values are established by the two local parquets. They do not establish why rows disappeared, whether a scanner database was replaced, or whether permission was measured at each retained price timestamp. The same collector documents that API history loses intraday resolution as it ages: a later refetch can recover historical prices at lower resolution without recovering historical permission snapshots. This is a plausible mechanism, not a confirmed explanation for this publication.

The correct next implementation is a separate permission observation series carrying `permission_observed_at`, explicit source flags and policy-input observation times, preserved independently of price compaction/refetching. The consumer should select the latest observation available by the decision time and age it using that original clock. Preserve the conservative unknown rule; do not replace `max(...)` with the historical price timestamp merely to recover the earlier CAGR.

### Latest master verification

The active editable web3-ethereum-defi checkout was fast-forwarded on 2026-10-06 from `1a26c81c5170e2ead1ca5c1904949e838621e590` to `788dc71c198680407c059728e66ff9be652cd01f`, matching the fetched `origin/master`. Poetry resolves `eth_defi` to this checkout. The existing local `.vscode/settings.json` edit was preserved. The high-frequency collector, daily collector and HyperCore exporter have no changes between these two revisions; the previously identified timestamp handling remains present.

The confirmed defect is the producer/consumer provenance contract: both upserts can preserve an old permission using `COALESCE` while unconditionally replacing `written_at`. For example, a September row carrying a September permission can receive an October price-only update, retain its flag and acquire an October write time. The consumer then cannot recover the original permission observation time. `written_at` can still be correct as the last row-write timestamp; it is not correct as a substitute for the retained field's original observation time. This code finding does not prove that the same upsert caused every October-stamped DOEZOE historical row; later first-time fetching can legitimately carry an October write date.
