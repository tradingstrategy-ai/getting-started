# Forward-fill rerun

The research allocation backtests now use the latest causally available vault
NAV on each calendar date. Raw observation freshness is retained only as a
diagnostic. This matches the production universe's forward-filled daily candle
convention and allows weekly or irregularly observed vaults to remain in the
daily replay while their risk features still record the sparse coverage.

The shared change covers `04-allocation-validation.ipynb`, which calls
`simulate_allocator`, and the stable-profit replays in notebooks 05 and 07,
which call `simulate_stable_policy`. Notebooks 01–03 are data, feature and IC
experiments and do not contain portfolio equity backtests.

## Allocation validation

| Arm | Final equity before | Final equity after | CAGR before | CAGR after | Sharpe before | Sharpe after | Max drawdown before | Max drawdown after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Incumbent | $154,322 | $157,402 | 2.9% | 4.9% | 0.24 | 0.34 | -15.4% | -15.6% |
| Candidate, fixed breadth | $138,201 | $148,774 | -7.9% | -0.8% | -0.20 | 0.06 | -27.8% | -22.3% |
| Candidate, adaptive breadth | $131,421 | $141,835 | -12.4% | -5.5% | -0.57 | -0.33 | -24.4% | -17.3% |

Forward fill improves every candidate's ending equity, volatility and drawdown
in this historical run. The candidates still do not beat the incumbent on
Sharpe or satisfy the production promotion criteria.

## Stable-profit replay

The primary stable-profit results were regenerated with the same forward-filled
execution path. The new full-period A0 row is CAGR 4.95%, volatility 20.04%,
Sharpe 0.34 and maximum drawdown -15.64%; the full table is in
`summary-03.md`. The replay records a mean of 1.97 positions marked from
carried NAVs, with zero stale positions dropped from equity.

On the exact Hyper AI comparison window (1 January–8 July 2026), forward-filled
A0 ends at $161,482 (+7.66%, Sharpe 0.76). The earlier fresh-only A0 ended at
$173,362 (+15.57%, Sharpe 1.45), while the recorded production engine result
was $191,446 (+27.76%, Sharpe 2.88). Therefore forward fill fixes a real
execution mismatch but does not by itself reproduce the production engine;
historical universe inputs and engine settlement/filtering differences remain.

The no-op parity check still passes exactly: 365 rows, zero maximum equity
difference and zero maximum cash difference between the shared A0 and
incumbent research paths.
