# Incumbent and leads without blacklists

## Key new insights and what did we learn?

Disabling source-universe exclusions increases coverage from 343 to 359 vaults.
The manual Scared Money exclusion and runtime curator quarantines are also disabled.
The strongest blacklist-off full-overlap Sharpe is inverse_vol_q10:
15.7% CAGR, 0.97 two-day-clock Sharpe and
-10.2% maximum drawdown. The largest absolute full-window
CAGR change across the six comparisons is 24.1 percentage points.

## Summary of results

| period   | candidate       | cagr_on   | cagr_off   |   sharpe_on |   sharpe_off | max_drawdown_on   | max_drawdown_off   |
|:---------|:----------------|:----------|:-----------|------------:|-------------:|:------------------|:-------------------|
| hyper_ai | anchor          | 58.7%     | 34.2%      |        2.9  |         1.74 | -3.9%             | -10.4%             |
| hyper_ai | measured_8      | 64.0%     | 49.9%      |        3.22 |         2.54 | -2.9%             | -5.0%              |
| hyper_ai | inverse_vol_q10 | 61.1%     | 50.8%      |        3.19 |         2.59 | -2.9%             | -5.1%              |
| hyper_ai | floor15         | 53.6%     | 26.6%      |        2.77 |         1.4  | -5.1%             | -11.4%             |
| hyper_ai | floor20         | 60.2%     | 20.0%      |        3.05 |         1.09 | -5.2%             | -11.8%             |
| hyper_ai | A0b             | 50.8%     | 42.2%      |        2.6  |         1.92 | -5.2%             | -9.6%              |
| full     | anchor          | 20.7%     | -0.4%      |        1.26 |         0.07 | -6.6%             | -14.4%             |
| full     | measured_8      | 27.6%     | 14.4%      |        1.72 |         0.89 | -5.1%             | -10.5%             |
| full     | inverse_vol_q10 | 25.9%     | 15.7%      |        1.67 |         0.97 | -5.1%             | -10.2%             |
| full     | floor15         | 33.4%     | 9.2%       |        1.83 |         0.58 | -6.6%             | -11.3%             |
| full     | floor20         | 20.8%     | 1.1%       |        1.29 |         0.15 | -9.1%             | -14.4%             |
| full     | A0b             | 18.1%     | 2.2%       |        1.05 |         0.21 | -6.5%             | -13.7%             |

HyperAI dates: 2026-01-01–2026-07-08. Full common observation dates:
2025-09-13–2026-09-08. Engine full-period portfolios started earlier, on
2025-08-01; full-overlap values are slices, not cold-start replays. The paired
on/off results isolate blacklist policy on one snapshot; historical-control drift
is saved separately. Sharpe here uses two-day observations, not the weekly clock
of NB16. These are retrospective experiments.

## Robustness of results

The highest leader concentration in the blacklist-off full engine runs is
measured_8: Realist Capital contributes 30.2%
of positive per-vault P&L ($17,364). Full attribution, positions,
executed trades, quarantine overlaps, best-cycle BTC/ETH returns, extreme interval
moves and observed NAV charts are saved. Positive-P&L shares are descriptive;
they do not establish the result of a leave-one-vault-out resimulation.

All six comparisons lose CAGR and Sharpe when blacklists are disabled on the
shared full-history window. The volatility-prefilter leads are the strongest
remaining candidates, but none reaches the provisional 18% CAGR floor there.
The largest late-June gains occur while BTC and ETH fall; the saved held-vault
NAV intervals show vault-specific gains rather than establishing a broad market
rally. These NAV intervals are not exact engine P&L attribution. The capital
audit found 0 closed positions
funded above $100 with less than $1 returned in executed trade value.

The blacklists-on controls are freshly rerun; compare them to the off results,
not to stale headline numbers. The independent A0b simulator had no runtime
quarantine logic to disable, so its toggle restores universe/manual exclusions.
All restored source addresses are checked against saved feature coverage. The
same strategy filters, fee assumptions and forward-filled accounting are retained.
The engine's inherited redemption fees differ from A0b's; no fee harmonisation is
claimed. Producer-cleaned or omitted observations are not recovered by disabling
local blacklists, and restored price-series artefacts can inflate apparent gains.
