# Cross-chain vault allocation experiments

Four recorded experiments extend the xchain2 tail-gated, twelve-position strategy
over **1 April 2025–20 October 2026**, starting with **$100,000**. Each notebook
contains its research conclusions, saved charts and execution diagnostics.

| Notebook | Change | Recorded outcome |
| --- | --- | --- |
| [NB01](01-backtest-tail-gate-12-positions-refreshed-universe.ipynb) | Refresh the universe to 356 sources and extend the period, retaining the $1,000 bridge buffer. | Incomplete: `NotEnoughMoney` when primary-chain funding needs $1,900.04. The saved failure is intentional. |
| [NB02](02-backtest-tail-gate-refreshed-universe-3000-usd-buffer.ipynb) | Increase the bridge buffer to $3,000. | Final equity $117,332.90; 10.84% CAGR, 11.33 Sharpe, -0.12% maximum drawdown. |
| [NB03](03-backtest-tail-gate-exclude-private-vaults.ipynb) | Exclude 29 private/restricted sources and YieldNest RWA MAX; add Atoma Index and Atoma RWA, leaving 328 sources. | Final equity $117,580.65; 10.99% CAGR, 10.39 Sharpe, -0.18% maximum drawdown. |
| [NB04](04-backtest-lighter-hyperliquid-lifetime-sharpe.ipynb) | Add 16 native Lighter/Hyperliquid sources screened by snapshot lifetime Sharpe above 2.5, taking the source count to 344. | Ledger equity $117,859.20; 11.16% CAGR, 9.12 Sharpe, -0.49% maximum drawdown. |

NB03 supplies the executor module in
[trade-executor PR #1679](https://github.com/tradingstrategy-ai/trade-executor/pull/1679),
which also includes Atoma settlement support. Its CLI backtest starts one decision
cycle later and loads current data, so its recorded metrics differ slightly from
the pinned notebook run.

## Reading the results

The source selection uses the 21 October 2026 metadata snapshot retrospectively;
these are not point-in-time or untouched holdout tests. Sparse NAV observations,
forward filling and synthetic HYPE++ windows affect the reported risk metrics.

Atoma deposits are synchronous; withdrawals apply a 0.5% external fee and an
estimated seven-day settlement delay. NB04 idealises native account funding and
does not validate live funding routes or latency. Its Stratwise external fee is
not charged by the execution ledger: an estimated $8.73 fee reserve reduces final
equity to $117,850.47. Only two added native vaults receive allocations, both near
the end of the period. Read each notebook's robustness discussion before comparing
headline results.

## Local replay inputs

Run from this directory with the repository's configured Poetry environment and
notebook runner. NB01 and NB02 load remote data; refreshing those inputs can change
their saved outcomes. NB03 and NB04 require the original local inputs below, and
assert SHA-256 hashes for the snapshots and NB04 baseline:

- `_artifacts/exp03/snapshots/vault-metadata.json`
- `_artifacts/exp03/snapshots/vault-prices.parquet`
- `_artifacts/exp03/before-yieldnest-atoma/backtest-state.json` for NB03 comparisons
- `_artifacts/exp04/baseline-exp03-state.json` for NB04 comparisons

These generated datasets and ledgers remain local and ignored by Git. Saved
notebook outputs are included for review; a fresh clone alone cannot reproduce
the pinned comparisons. The execution environment also needs the supporting
trade-executor changes linked above and the applicable data access credentials.
