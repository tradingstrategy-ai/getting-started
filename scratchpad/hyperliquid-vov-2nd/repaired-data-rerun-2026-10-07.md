# Repaired Hyperliquid data rerun — 7 October 2026

> **Latest follow-up, 7 October 2026:** producer PR #1634 restores archived leader shares and policy caps; trading-strategy #255 and trade-executor #1671 retain them without inventing an independent capacity clock. Fresh 01–05 reruns use the restored publication. Source v11 now reaches **41.20% CAGR**, versus the earlier 41.59%; the first 558 chronological trades match. See [the restored-data rerun](restored-data-rerun-2026-10-07.md). The findings below refer to earlier input generations.

## Current outcome

The permission recovery substantially improves v11, but does not reproduce the earlier 41.59% CAGR. The largest remaining difference comes from discarding historical inputs to the 5.5% leader-share trading policy, represented as zero-dollar deposit caps. These were policy limits, not established venue-reported dollar capacities. Source strategy code is unchanged, but missing leader-share inputs change which policy blocks apply. Original and research-formula equity and full trade ledgers match on the repaired inputs.

### Benchmark comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

All runs start with $150,000 and use the same 139 two-day decisions. The old-cap row is an artificial diagnostic, not a deployable strategy or authenticated historical capacity model.

| Run                                   | Final equity (USD)   | CAGR   |   Sharpe | Maximum drawdown   |   Trades |
|:--------------------------------------|:---------------------|:-------|---------:|:-------------------|---------:|
| Earlier saved v11                     | $194,928.64          | 41.59% |     2    | -6.40%             |      582 |
| Corrupted-input v11                   | $173,229.20          | 21.13% |     1.23 | -11.33%            |      564 |
| Repaired source v11                   | $186,418.03          | 33.47% |     1.63 | -9.04%             |      601 |
| Diagnostic: repaired prices, old caps | $194,562.55          | 41.24% |     1.96 | -6.40%             |      583 |
| 05: Blend 46d + refill                | $191,577.98          | 38.38% |     2.01 | -4.94%             |      577 |

## What changed

The fresh authenticated download contains 10,387,238 price rows and dedicated `permission_observed_at`, `permission_provenance`, `permission_observation_id` and `capacity_observed_at` columns. Its SHA-256 is `b45ce736510919270e52299711a072b75e23207d06f33bd2243efedbb978027f`. The metadata SHA-256 is `7201adaf27f925e9f0b4714c6c03c9c3831f3622e98ecd7e281ef1a845ddf532`.

The client uses original permission clocks, rounds availability upwards to the first decision bucket and retains complete snapshots. The executor checks age against the unrounded observation time. Publication and price updates no longer refresh permissions. Capacity has a separate clock: inferred permission evidence does not authenticate a carried zero-dollar deposit cap. These are the merged contracts in [trade-executor #1670](https://github.com/tradingstrategy-ai/trade-executor/pull/1670) and [trading-strategy #253](https://github.com/tradingstrategy-ai/trading-strategy/pull/253).

The source loader uses the repaired price projection, which includes permission evidence. No independent sidecar was implicitly downloaded. DOEZOE has recovered intraday prices and inferred legacy permission times: midnight admission is Open on 13–21 September and Closed from 22 September. Its flags change during 21 September. The recovery does not manufacture genuine historical permission receipts.

## Why the result is still below 41.59%

The first 211 dated trades match the earlier source ledger exactly. The first divergence is 13 April, before the September corruption: the repaired run sells Systemic Strategies and buys Gucky and Realist Capital, while the earlier run keeps Systemic Strategies. The source score components for those three vaults are identical on that decision.

The earlier frozen state assigns Gucky `max_deposit=0` on 11–13 April. The repaired state has unknown capacity, with no independent capacity receipt. Source rules therefore permit an entry that the earlier cap blocked. This interacts with the unchanged selector and alters subsequent holdings.

Controlled source replays hold repaired prices, source indicators, code, fees, guards and initial cash fixed. Restoring only Gucky's legacy cap raises CAGR from 33.47% to 34.18%. Restoring all legacy caps raises it to 41.24%, Sharpe to 1.96 and drawdown to −6.40%, explaining 95.7% of the $8,510.61 final-equity shortfall. That diagnostic matches the earlier source's first 558 dated trades through 14 September. The first subsequent difference is a 16 September Mad Scientists execution price: 2.15920000 in the repaired data versus 2.15959883 previously. Thus the residual is not a changed backtesting period. A complete attribution of the remaining $366.09 has not been established.

The prior frozen 2026 state contains 2,503 finite deposit-cap samples across 49 vaults; every finite value is zero, and none has an independent capacity clock. The repaired state removes these unauthenticated caps. Valid historical capacity receipts would be needed to reintroduce venue capacity constraints; the retained zero values alone do not establish them.

Legacy cap restoration deliberately supplies synthetic capacity clocks to reproduce the old cap-consumption behaviour. It is a causal intervention, not evidence those caps were valid. The loader must not reinstate them merely to recover a desirable headline number; equally, the missing new clock column does not prove the archived leader-share measurements were false.

### What the zero caps actually mean

The shared `classify_hyperliquid_vault_deposit()` implementation returns `deposits_open=True, max_deposit=0` for an open normal vault whose observed leader share is below 5.5%. This is our conservative trading rule. Hyperliquid's documented 5% leader rule explicitly restricts leader withdrawals; its application to follower deposits is not established by that documentation. Treating the generated zero as proof that the venue rejected deposits is therefore incorrect.

In the old raw Gucky archive, the 11 April 04:22:05.613 price row has `written_at=04:22:06.999`, `deposits_open=true`, leader share approximately 5.0003% and `max_deposit=0`. Other nearby snapshots contain changing leader shares, also below 5.5%. These look plausibly contemporaneous, although a near-matching write timestamp alone does not authenticate the API receipt or exclude an earlier rewrite. The repaired archive retains inferred permission but clears these leader-share values and their caps. The migration also preserves raw legacy evidence separately for further recovery.

The new reader deliberately accepts inferred legacy permission clocks but refuses inferred capacity clocks. With permission Open and capacity unknown, the executor permits deposits, so the leader-share guard is effectively absent for those historical decisions. This is an explicit missing-data policy with a potentially material backtest/live mismatch. It is not proof that historical capacity was unlimited or that all earlier zero caps were erroneous. The replay comparison establishes the cause of the numerical gap; it does not choose which historical admission model is correct. Resolving that requires auditing original scanner backups or response logs and reconstructing dated leader-share evidence under a documented recovery policy.

### Vault profit attribution — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

The largest positive contributions to the earlier-minus-repaired gap, aggregating every position lifecycle by vault address. These are net marked profit differences on the actual respective trade ledgers, not counterfactual removal of vaults. The diagnostic restores legacy caps while keeping repaired prices. All-vault differences reconcile to the $8,510.61 final-equity gap.

| Vault                             | Earlier    | Repaired   | Legacy-cap diagnostic   | Earlier minus repaired   |
|:----------------------------------|:-----------|:-----------|:------------------------|:-------------------------|
| Realist Capital                   | $24,196.23 | $20,837.83 | $24,196.23              | $3,358.39                |
| [ Systemic Strategies ] L/S Grids | $-647.66   | $-1,801.94 | $-647.66                | $1,154.28                |
| Goon Edging                       | $686.18    | $-254.55   | $686.18                 | $940.73                  |
| Larp Capital_LLC                  | $0.00      | $-718.53   | $0.00                   | $718.53                  |
| Gucky_1coin_1dot5x                | $552.85    | $-152.82   | $552.85                 | $705.67                  |
| 22Cap                             | $3,624.34  | $3,007.78  | $3,624.34               | $616.56                  |

## Experiment reruns

- **01:** fresh source backtests for 2026 and full history completed. Current full-history source is 14.81% CAGR, 1.16 Sharpe and −8.41% drawdown.
- **02:** parent and accepted-dollar-cap treatments completed for both periods, with cash-matched diagnostics. Source controls match 01. Short-period cap CAGR is 6.19%.
- **03:** all 20 weighting/allocator/period backtests completed. Original inverse variance has the highest 2026 CAGR and Sharpe among these treatments. Source and cap controls match 01 and 02.
- **04:** all 26 code cells completed: fresh full-history feature screening and sparse fitting, both-period 126-row parameter grids, detailed references, cap treatments and diagnostics. The 2026 source and exact compatibility controls match all 601 trades and the full equity curve. The 46-day legacy approximation reaches 33.04% CAGR / 1.62 Sharpe / −9.53% drawdown. The highest 2026 grid CAGR is 25.74% / 1.64 Sharpe / −4.94% drawdown; no grid setting improves CAGR, Sharpe and drawdown together versus source. No original saved-report mode is used.
- **05:** 29 short-period treatments, six predeclared full-history confirmations and source controls completed. Formula/source full ledgers and equity match in both periods. The best eligible 2026 treatment is Blend 46d + refill, improving CAGR, Sharpe and drawdown versus the repaired source. Full-history refill results do not confirm that gain.

All five notebooks completed without error outputs or substantive warning output. Their headings and written analyses now use repaired-input figures; earlier findings are backed up or explicitly marked historical. The 2026 charts remain the default report. All 34 saved static figures in 04 and all ten in 05 were visually reviewed. Nine parameter views in 04 were redrawn after identifying an equivalent compressed-matrix alias: 108 cache configurations correspond to 90 effective settings. Canonicalisation changes presentation only. The table and chart descriptions distinguish return, drawdown, target-dollar information gaps and overlapping-history sensitivity checks.

The 04 manifests retain 274 full-history and 218 short-period configuration records. Independent foreground workers executed cases from the same pinned generation while the notebook ran; complete metrics were published atomically. A numeric cache-key mismatch (`5` versus `5.0` for an identical Calmar cap) caused duplicate short replays. All 51 duplicate engine results matched exactly before the remaining equivalent entries were reused. These are execution and presentation fixes, not changes to scoring, selection or clipping parameters. Position profit attribution reconciles to portfolio equity within numerical rounding.

### Full-history confirmations — 2023-03-01 → 2026-10-05 (end exclusive, UTC)

This explicitly longer-period table is a sensitivity check over overlapping history. It is not an independent holdout. Six positions and 90-day inverse-variance sizing are fixed.

| Configuration       | CAGR   |   Sharpe | Maximum drawdown   |
|:--------------------|:-------|---------:|:-------------------|
| Hard C1 S3          | 14.81% |     1.16 | -8.41%             |
| Blend 46d           | 14.86% |     1.2  | -8.51%             |
| Smooth C1 S3        | 14.84% |     1.16 | -7.92%             |
| Hard C1 S3 / refill | 14.24% |     1.11 | -8.18%             |
| Blend 46d / refill  | 14.66% |     1.18 | -8.61%             |
| Feasible entrants   | 14.91% |     1.17 | -8.25%             |

## Repository and execution provenance

### Synced repositories

All five checkouts contain fetched remote master. Existing local edits were preserved and nothing was committed, pushed or deployed.

| Repository         | Master commit   | HEAD equals remote master   |
|:-------------------|:----------------|:----------------------------|
| getting-started    | 0be3392775ff    | True                        |
| trade-executor     | 2494d5c4b10c    | True                        |
| trading-strategy   | 1ffded76753d    | True                        |
| web3-ethereum-defi | baec2a246d3e    | True                        |
| strategies         | ba57a8cbd0ae    | True                        |

The imported packages resolve to the editable trade-executor and dependency checkouts, not stale installed copies. CairoSVG was installed in the research environment to satisfy the merged metadata loader's optional data dependency. Preparation and engine loading both use the same fresh indicator directory. Each experiment has an isolated artifact directory under the ignored `_artifacts-repaired-2026-10-07` folder; the raw inputs are pinned and checked by content hash. Earlier notebook outputs, inputs and notes were backed up before replacement.

Both periods retain the original source end boundary; data available after 4 October does not extend these comparison runs. Score grids and optimiser seeds remain unchanged. Generated states, CSVs, cached panels, manifests and chart-review images remain ignored; saved notebook outputs and written conclusions are the reviewable research record.
