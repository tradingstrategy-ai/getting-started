# Portfolio effects of the StratWise-inspired stability screens

Based on `18-research-leads-no-blacklists.ipynb` and `19-research-stratwise-entry-forensics.ipynb`.

## Key new insights and what did we learn?

The strongest full-common-period Sharpe is inverse_vol_q10 / none: 15.7% CAGR, 0.97 two-day Sharpe, -10.2% maximum drawdown. This experiment tests portfolio outcomes, not just rejecting known losing vaults.

Of 12 screened-versus-control comparisons on the full common period, 0 improve Sharpe. The best screened full-period Sharpe is anchor/weekly: -1.0% CAGR and -0.01 Sharpe. These fixed thresholds should be judged by those results, not by the fraction of retrospectively bad entries they exclude.

## Summary of results

| period   | candidate       | screen   | cagr   |   sharpe | max_drawdown   |
|:---------|:----------------|:---------|:-------|---------:|:---------------|
| hyper_ai | anchor          | none     | 34.2%  |     1.74 | -10.4%         |
| hyper_ai | anchor          | daily    | -15.9% |    -1.65 | -9.5%          |
| hyper_ai | anchor          | weekly   | -1.5%  |    -0.11 | -8.4%          |
| hyper_ai | measured_8      | none     | 49.9%  |     2.54 | -5.0%          |
| hyper_ai | measured_8      | daily    | -9.5%  |    -1.99 | -5.5%          |
| hyper_ai | measured_8      | weekly   | -14.0% |    -1.96 | -8.4%          |
| hyper_ai | inverse_vol_q10 | none     | 50.8%  |     2.59 | -5.1%          |
| hyper_ai | inverse_vol_q10 | daily    | -16.7% |    -1.73 | -9.7%          |
| hyper_ai | inverse_vol_q10 | weekly   | -9.1%  |    -0.84 | -9.3%          |
| hyper_ai | floor15         | none     | 26.6%  |     1.4  | -11.4%         |
| hyper_ai | floor15         | daily    | -17.1% |    -1.6  | -10.5%         |
| hyper_ai | floor15         | weekly   | -31.5% |    -1.65 | -22.5%         |
| hyper_ai | floor20         | none     | 20.0%  |     1.09 | -11.8%         |
| hyper_ai | floor20         | daily    | -16.7% |    -1.57 | -10.1%         |
| hyper_ai | floor20         | weekly   | -30.1% |    -1.55 | -21.1%         |
| hyper_ai | A0b             | none     | 42.2%  |     1.92 | -9.6%          |
| hyper_ai | A0b             | daily    | -19.8% |    -1.88 | -12.9%         |
| hyper_ai | A0b             | weekly   | -41.4% |    -2.46 | -25.5%         |
| full     | anchor          | none     | -0.4%  |     0.07 | -14.4%         |
| full     | anchor          | daily    | -23.9% |    -1.84 | -25.9%         |
| full     | anchor          | weekly   | -1.0%  |    -0.01 | -11.8%         |
| full     | measured_8      | none     | 14.4%  |     0.89 | -10.5%         |
| full     | measured_8      | daily    | -13.1% |    -1.84 | -13.7%         |
| full     | measured_8      | weekly   | -10.5% |    -0.87 | -14.5%         |
| full     | inverse_vol_q10 | none     | 15.7%  |     0.97 | -10.2%         |
| full     | inverse_vol_q10 | daily    | -25.5% |    -2.02 | -27.2%         |
| full     | inverse_vol_q10 | weekly   | -8.7%  |    -0.59 | -15.9%         |
| full     | floor15         | none     | 9.2%   |     0.58 | -11.3%         |
| full     | floor15         | daily    | -20.8% |    -1.81 | -23.1%         |
| full     | floor15         | weekly   | -14.0% |    -0.77 | -24.2%         |
| full     | floor20         | none     | 1.1%   |     0.15 | -14.4%         |
| full     | floor20         | daily    | -24.9% |    -1.97 | -27.0%         |
| full     | floor20         | weekly   | -19.0% |    -1.01 | -27.2%         |
| full     | A0b             | none     | 2.2%   |     0.21 | -13.7%         |
| full     | A0b             | daily    | -26.0% |    -2.29 | -27.9%         |
| full     | A0b             | weekly   | -28.5% |    -1.81 | -32.9%         |

Dates are 1 January–8 July 2026 and 13 September 2025–8 September 2026. Native engine full runs begin 1 August 2025; the common full table slices an already-running portfolio. All screens retain the source fees, sizing, forward filling and execution conventions. Independent A0b is not fee/accounting-identical to the engine.

Thirty engine runs and six independent A0b runs compare unchanged, daily and weekly screens across anchor, measured_8, inverse_vol_q10, floor15 and floor20 (A0b receives both screens directly). Blacklists are disabled throughout, matching NB18 off controls. No blacklists-on screened experiment is claimed. Exact source-control parity is saved separately.

Daily screen: prior 30-day return remains positive after deleting the two best daily log gains; trailing maximum drawdown at most 5%; worst of four completed non-overlapping weeks at least -3%. Weekly screen uses four completed weeks, deletes the best week's log gain and measures drawdown on weekly marks, retaining the -3% worst-week bound. Both screen existing holdings as well as new purchases. Thresholds are fixed from NB19, not searched here.

Missing screen history is UNKNOWN and passes through the existing selection rules, rather than creating a new age barrier. The weekly screen becomes measurable after 28 days; daily needs 30 days, both ending at the previous midnight. Existing incumbent score/sizing history requirements are unchanged. Passing the screen is not a promise of selection or allocation for young vaults. See screen-coverage.csv and stratwise-screen-decisions.csv. These include engine and A0b candidate evaluations; A0b actual selections and target dollars are separately saved in stratwise-a0b-pool.csv.

Mean invested fraction and position counts over the same common periods:

| period   | candidate       | screen   |   mean_invested_fraction |   mean_positions |
|:---------|:----------------|:---------|-------------------------:|-----------------:|
| full     | A0b             | daily    |                 0.824276 |          4.76454 |
| full     | A0b             | none     |                 0.973372 |          6.15512 |
| full     | A0b             | weekly   |                 0.890119 |          5.30194 |
| full     | anchor          | daily    |                 0.915747 |          4.91713 |
| full     | anchor          | none     |                 0.972516 |          5.93923 |
| full     | anchor          | weekly   |                 0.963044 |          5.58011 |
| full     | floor15         | daily    |                 0.875752 |          5.34807 |
| full     | floor15         | none     |                 0.969898 |          5.90055 |
| full     | floor15         | weekly   |                 0.950877 |          5.66298 |
| full     | floor20         | daily    |                 0.866378 |          5.27624 |
| full     | floor20         | none     |                 0.970924 |          5.90055 |
| full     | floor20         | weekly   |                 0.944672 |          5.63536 |
| full     | inverse_vol_q10 | daily    |                 0.912847 |          4.86188 |
| full     | inverse_vol_q10 | none     |                 0.974999 |          6       |
| full     | inverse_vol_q10 | weekly   |                 0.959535 |          5.55249 |
| full     | measured_8      | daily    |                 0.571402 |          3.01105 |
| full     | measured_8      | none     |                 0.975719 |          6       |
| full     | measured_8      | weekly   |                 0.894618 |          4.94475 |
| hyper_ai | A0b             | daily    |                 0.902283 |          5.08995 |
| hyper_ai | A0b             | none     |                 0.97704  |          6       |
| hyper_ai | A0b             | weekly   |                 0.957537 |          5.77778 |
| hyper_ai | anchor          | daily    |                 0.903265 |          4.93684 |
| hyper_ai | anchor          | none     |                 0.967001 |          5.85263 |
| hyper_ai | anchor          | weekly   |                 0.956275 |          5.78947 |
| hyper_ai | floor15         | daily    |                 0.861388 |          5.24211 |
| hyper_ai | floor15         | none     |                 0.96123  |          5.84211 |
| hyper_ai | floor15         | weekly   |                 0.943088 |          5.71579 |
| hyper_ai | floor20         | daily    |                 0.850744 |          5.15789 |
| hyper_ai | floor20         | none     |                 0.962563 |          5.84211 |
| hyper_ai | floor20         | weekly   |                 0.940662 |          5.70526 |
| hyper_ai | inverse_vol_q10 | daily    |                 0.899663 |          4.8     |
| hyper_ai | inverse_vol_q10 | none     |                 0.968008 |          5.93684 |
| hyper_ai | inverse_vol_q10 | weekly   |                 0.949033 |          5.69474 |
| hyper_ai | measured_8      | daily    |                 0.55667  |          2.75789 |
| hyper_ai | measured_8      | none     |                 0.968057 |          5.93684 |
| hyper_ai | measured_8      | weekly   |                 0.891739 |          5.10526 |

## What changed in the portfolio?

Largest adverse changes in full-period anchor per-vault contributions under the weekly screen (native engine period, dollars):

| name                |     none |   weekly |   weekly_pnl_change |
|:--------------------|---------:|---------:|--------------------:|
| Realist Capital     | 13323.2  |  1096.66 |           -12226.5  |
| Winwin              |  2857    | -3616.46 |            -6473.46 |
| pmalt               |  2683.19 | -2156.5  |            -4839.69 |
| AceVault Hyper01    |  4177.47 |   377.29 |            -3800.18 |
| Citadel             |  6688.23 |  2896.6  |            -3791.64 |
| LowRiskCryptoGainer |  2022.98 | -1587.85 |            -3610.83 |

These include changed entry/exit timing and capital allocation, not simply omitted trades. Replacement positions can lose even if a screen removes some previously losing vaults. The measured_8 filter still removes eight measured high-volatility names AFTER the new screen, so the filters can leave very few investable candidates. Portfolio cash is an outcome of the experiment, not a matched-volatility control. Gross executed turnover is exported separately to expose additional churn.

StratWise passing these new rules does not fix the inherited incumbent's long-history ranking and sizing: its 360-day composite cannot yet be complete and its 90-day inverse-volatility estimate is unavailable on this sample. The engine inverse-variance sizing gives a missing estimate zero raw weight. This experiment intentionally measures the rules as overlays; it does not implement a separate young-vault allocation policy. Check the actual position and pool ledgers before claiming that any strategy now buys StratWise.

## Robustness of results

Inputs are hash-checked against NB18 and the vectorised daily/weekly feature calculations are checked against the independent scalar NB19 implementation. All marks are causal as-of marks; nothing is backfilled. Weekly screens mitigate reporting-cadence differences but cannot reveal losses between sparse observations. These are retrospective in-sample tests of thresholds motivated by known vault histories.

Deployment and number of positions are reported: reduced volatility can reflect more cash. There is no matched-exposure causal decomposition. Largest contributor shares, full position P&L, trades, curator flags and best-cycle BTC/ETH returns are exported. There are 0 closed positions funded above $100 with less than $1 returned in executed trade value. Large positive-P&L shares do not establish leave-one-vault-out results. Current source exclusions are disabled locally; upstream removed data cannot be recovered.

StratWise has 0 engine positions across the separate runs; these are not independent observations. Screen logs count candidate evaluations after the incumbent return gate, not the complete source universe. Engine deployment is marked before each decision; A0b deployment uses its saved post-decision equity rows. The same two-day clock is used for comparative Sharpe, with weekly Sharpe also exported.

## Decision from this batch

All 24 screened-versus-control comparisons (six strategies, two screens, two periods) reduce both CAGR and Sharpe. The filters separate selected historical problem vaults from StratWise in NB19, but fail as hard portfolio overlays in this broader test. Do not treat the NB19 retention result as validated selection skill.

The daily screen rejects about 84% of ordinary-gate candidate evaluations in the shorter period; the weekly screen rejects about 73%. They remove winners, alter entry/exit timing and force substitutions. This is not only a cash effect: on the full common period anchor remains 96.3% invested with the weekly screen versus 97.3% in the control. By contrast measured_8 plus the daily screen averages only 57.1% invested because a fixed additional eight-name exclusion acts on the shrunken pool.

StratWise receives zero actual engine positions and zero positive A0b target allocations. The overlay permits it but does not repair the incumbent's long-history score/sizing requirements. A future young-vault policy would need explicit short-history ranking and sizing; any softer stability tilt should be tested separately from such a change. No additional thresholds were searched after seeing these losses.

Validation: all 12 unchanged controls reproduce NB18 exactly; admission was checked for all 5,125 engine positions and every screened A0b selected row. No new position opened despite a recorded screen rejection. Independent scalar/vectorised feature checks and input hashes pass.
