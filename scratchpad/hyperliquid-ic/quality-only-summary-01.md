# Variable-size portfolios with absolute quality floors

Based on `20-research-stability-screen-portfolios.ipynb`, using the same frozen inputs. Thirty main engine runs, six independent A0b runs and two additional leave-one-vault-out replays; no parameter search.

## Key new insights and what did we learn?

The best new full-common-period Sharpe is A0b/unrestricted: 8.4% CAGR, 1.40 Sharpe, -2.4% maximum drawdown. Judge return, drawdown, cash and realised concentration together; removing a cap is not evidence of higher-quality selections.

## Summary of results

| period   | candidate       | variant       | cagr   |   sharpe | max_drawdown   |
|:---------|:----------------|:--------------|:-------|---------:|:---------------|
| hyper_ai | anchor          | bounded       | 34.2%  |     1.74 | -10.4%         |
| hyper_ai | anchor          | unrestricted  | 19.7%  |     1.97 | -0.7%          |
| hyper_ai | anchor          | daily_floors  | -8.4%  |    -1.12 | -7.1%          |
| hyper_ai | anchor          | weekly_floors | 2.0%   |     0.42 | -2.6%          |
| hyper_ai | measured_8      | bounded       | 49.9%  |     2.54 | -5.0%          |
| hyper_ai | measured_8      | unrestricted  | 19.7%  |     1.96 | -0.8%          |
| hyper_ai | measured_8      | daily_floors  | -8.4%  |    -1.12 | -7.1%          |
| hyper_ai | measured_8      | weekly_floors | 2.0%   |     0.42 | -2.6%          |
| hyper_ai | inverse_vol_q10 | bounded       | 50.8%  |     2.59 | -5.1%          |
| hyper_ai | inverse_vol_q10 | unrestricted  | 19.6%  |     1.96 | -0.7%          |
| hyper_ai | inverse_vol_q10 | daily_floors  | -8.4%  |    -1.12 | -7.1%          |
| hyper_ai | inverse_vol_q10 | weekly_floors | 2.0%   |     0.42 | -2.6%          |
| hyper_ai | floor15         | bounded       | 26.6%  |     1.4  | -11.4%         |
| hyper_ai | floor15         | unrestricted  | -13.1% |    -2.57 | -8.6%          |
| hyper_ai | floor15         | daily_floors  | -23.9% |    -3.18 | -13.2%         |
| hyper_ai | floor15         | weekly_floors | -15.9% |    -2.5  | -9.8%          |
| hyper_ai | floor20         | bounded       | 20.0%  |     1.09 | -11.8%         |
| hyper_ai | floor20         | unrestricted  | -15.1% |    -2.6  | -10.0%         |
| hyper_ai | floor20         | daily_floors  | -20.1% |    -2.63 | -11.9%         |
| hyper_ai | floor20         | weekly_floors | -13.4% |    -1.9  | -9.9%          |
| hyper_ai | A0b             | bounded       | 42.2%  |     1.92 | -9.6%          |
| hyper_ai | A0b             | unrestricted  | 12.3%  |     2.12 | -0.5%          |
| hyper_ai | A0b             | daily_floors  | -3.3%  |    -0.39 | -5.8%          |
| hyper_ai | A0b             | weekly_floors | 2.2%   |     0.39 | -3.0%          |
| full     | anchor          | bounded       | -0.4%  |     0.07 | -14.4%         |
| full     | anchor          | unrestricted  | 11.0%  |     1.32 | -2.8%          |
| full     | anchor          | daily_floors  | -5.1%  |    -0.52 | -11.1%         |
| full     | anchor          | weekly_floors | 2.8%   |     0.37 | -4.1%          |
| full     | measured_8      | bounded       | 14.4%  |     0.89 | -10.5%         |
| full     | measured_8      | unrestricted  | 10.9%  |     1.31 | -2.8%          |
| full     | measured_8      | daily_floors  | -5.1%  |    -0.52 | -11.1%         |
| full     | measured_8      | weekly_floors | 2.8%   |     0.37 | -4.1%          |
| full     | inverse_vol_q10 | bounded       | 15.7%  |     0.97 | -10.2%         |
| full     | inverse_vol_q10 | unrestricted  | 10.9%  |     1.31 | -2.8%          |
| full     | inverse_vol_q10 | daily_floors  | -5.1%  |    -0.52 | -11.1%         |
| full     | inverse_vol_q10 | weekly_floors | 2.8%   |     0.37 | -4.1%          |
| full     | floor15         | bounded       | 9.2%   |     0.58 | -11.3%         |
| full     | floor15         | unrestricted  | -4.9%  |    -0.54 | -11.1%         |
| full     | floor15         | daily_floors  | -14.2% |    -1.31 | -19.6%         |
| full     | floor15         | weekly_floors | -6.1%  |    -0.54 | -13.0%         |
| full     | floor20         | bounded       | 1.1%   |     0.15 | -14.4%         |
| full     | floor20         | unrestricted  | -8.5%  |    -1.34 | -12.1%         |
| full     | floor20         | daily_floors  | -21.2% |    -2.01 | -24.6%         |
| full     | floor20         | weekly_floors | -7.3%  |    -0.91 | -13.1%         |
| full     | A0b             | bounded       | 2.2%   |     0.21 | -13.7%         |
| full     | A0b             | unrestricted  | 8.4%   |     1.4  | -2.4%          |
| full     | A0b             | daily_floors  | -0.9%  |    -0.05 | -7.7%          |
| full     | A0b             | weekly_floors | 4.6%   |     0.57 | -3.7%          |

HyperAI common dates: 1 January–8 July 2026. Full common dates: 13 September 2025–8 September 2026. Native engine full runs start 1 August 2025, so the common full period is a slice rather than a cold start. Sharpe uses two-day marks. A0b remains an independent simulator with its inherited different fee/accounting conventions.

## What changed?

- Bounded controls are saved NB20 unscreened runs: six slots, 33% portfolio weight and 33% historical vault TVL capacity.
- Unrestricted changes those limits to the entire universe, 100% portfolio weight and 100% historical vault TVL. It retains each strategy's relative filters, making this the allocation-limit experiment.
- Daily/weekly floor-only arms use the same unrestricted limits and fixed NB19 quality conditions. They disable measured_8's eight-name deletion and inverse_vol_q10's 10% deletion. Consequently those two families collapse to the anchor under identical floors; exact curve equality is checked rather than claiming three independent findings.
- Daily: positive 30-day return excluding the two best days; maximum drawdown at most 5%; worst completed week at least -3%. Weekly: positive four-week return excluding the best week; weekly-mark drawdown at most 5%; worst week at least -3%.
- Missing quality estimates FAIL admission in these floor-only arms; NB20 passed them through. Thus differences from old screened runs combine allocation limits, stricter missingness and removal of relative filters. See versus-nb20-screens.csv. This is not a one-parameter causal attribution.
- Empty eligible sets in the floor-only engine arms continue through zero-target rebalancing, instead of the inherited early return that could preserve old holdings. This is another intentional difference from NB20. No minimum number of positions or fallback picks. Cash is permitted if no qualifying vault is investable. The portfolio retains a 98% deployment target and the existing small-position/trade thresholds, so not every qualifying vault necessarily receives a trade.
- TVL, operational deposit checks, return gates, fees and inverse-variance sizing are retained. 100% historical TVL remains a capacity assumption, not a claim of practical capacity for a large live deposit.

## Allocation outcomes

| period   | candidate       | screen   |   mean_invested |   mean_positions |   min_positions |   max_positions |   peak_weight |   mean_effective_positions |
|:---------|:----------------|:---------|----------------:|-----------------:|----------------:|----------------:|--------------:|---------------------------:|
| full     | A0b             | daily    |        0.98054  |         18.0416  |               5 |              56 |      0.959821 |                    4.04273 |
| full     | A0b             | none     |        0.984354 |        153.812   |              58 |             274 |      0.394963 |                   11.9013  |
| full     | A0b             | weekly   |        0.981665 |         32.8283  |              14 |              86 |      0.895218 |                    5.12195 |
| full     | anchor          | daily    |        0.972336 |          9.03867 |               1 |              27 |      0.966879 |                    3.92782 |
| full     | anchor          | none     |        0.956538 |         16.2762  |              10 |              32 |      0.398126 |                   11.1224  |
| full     | anchor          | weekly   |        0.964738 |         12.768   |               1 |              27 |      0.960404 |                    4.94522 |
| full     | floor15         | daily    |        0.975343 |         10.9834  |               1 |              33 |      0.98015  |                    5.43178 |
| full     | floor15         | none     |        0.9443   |         24.1602  |              13 |              45 |      0.589138 |                   10.4121  |
| full     | floor15         | weekly   |        0.973556 |         15.2431  |               6 |              39 |      0.662026 |                    6.92353 |
| full     | floor20         | daily    |        0.961421 |         10.4807  |               1 |              33 |      0.98015  |                    5.26687 |
| full     | floor20         | none     |        0.952939 |         24.6796  |              13 |              45 |      0.524016 |                   11.0558  |
| full     | floor20         | weekly   |        0.975319 |         14.9558  |               6 |              38 |      0.627335 |                    6.84156 |
| full     | inverse_vol_q10 | daily    |        0.972336 |          9.03867 |               1 |              27 |      0.966879 |                    3.92782 |
| full     | inverse_vol_q10 | none     |        0.957668 |         16.2099  |              10 |              32 |      0.398368 |                   11.0936  |
| full     | inverse_vol_q10 | weekly   |        0.964738 |         12.768   |               1 |              27 |      0.960404 |                    4.94522 |
| full     | measured_8      | daily    |        0.972336 |          9.03867 |               1 |              27 |      0.966879 |                    3.92782 |
| full     | measured_8      | none     |        0.957574 |         16.1989  |              10 |              32 |      0.398596 |                   11.0963  |
| full     | measured_8      | weekly   |        0.964738 |         12.768   |               1 |              27 |      0.960404 |                    4.94522 |
| hyper_ai | A0b             | daily    |        0.980693 |         16.3492  |               5 |              41 |      0.897435 |                    4.22297 |
| hyper_ai | A0b             | none     |        0.983342 |        150.577   |              94 |             245 |      0.359445 |                   11.4722  |
| hyper_ai | A0b             | weekly   |        0.980578 |         31.6296  |              14 |              61 |      0.89523  |                    4.69344 |
| hyper_ai | anchor          | daily    |        0.962702 |          9.09474 |               0 |              27 |      0.960958 |                    4.06252 |
| hyper_ai | anchor          | none     |        0.956149 |         13.4526  |               0 |              30 |      0.359414 |                   10.7345  |
| hyper_ai | anchor          | weekly   |        0.953959 |         12.9263  |               0 |              27 |      0.930358 |                    4.35871 |
| hyper_ai | floor15         | daily    |        0.964286 |         10.4316  |               0 |              26 |      0.98015  |                    5.33441 |
| hyper_ai | floor15         | none     |        0.93204  |         24.7474  |               0 |              39 |      0.47337  |                   10.701   |
| hyper_ai | floor15         | weekly   |        0.963147 |         15.7579  |               0 |              28 |      0.634709 |                    7.15209 |
| hyper_ai | floor20         | daily    |        0.95679  |          9.91579 |               0 |              25 |      0.98015  |                    4.96344 |
| hyper_ai | floor20         | none     |        0.941594 |         24.9684  |               0 |              38 |      0.438204 |                   11.1174  |
| hyper_ai | floor20         | weekly   |        0.963618 |         15.2105  |               0 |              28 |      0.622745 |                    6.94159 |
| hyper_ai | inverse_vol_q10 | daily    |        0.962702 |          9.09474 |               0 |              27 |      0.960958 |                    4.06252 |
| hyper_ai | inverse_vol_q10 | none     |        0.956366 |         13.4421  |               0 |              30 |      0.359622 |                   10.7335  |
| hyper_ai | inverse_vol_q10 | weekly   |        0.953959 |         12.9263  |               0 |              27 |      0.930358 |                    4.35871 |
| hyper_ai | measured_8      | daily    |        0.962702 |          9.09474 |               0 |              27 |      0.960958 |                    4.06252 |
| hyper_ai | measured_8      | none     |        0.956414 |         13.4526  |               0 |              30 |      0.359569 |                   10.7391  |
| hyper_ai | measured_8      | weekly   |        0.953959 |         12.9263  |               0 |              27 |      0.930358 |                    4.35871 |

Position counts, actual peak single-vault weights and effective position counts expose whether the result is a broad book or effectively one vault. Engine values use pre-decision marks; A0b concentration uses rebalance target dollars and deployment uses saved daily equity. Missing or zero-investment rows are not evidence of diversification.

## Leave-one-vault-out sensitivity

The unrestricted short-period anchor's largest positive contributor is intothecryptoverse.com. Its recorded daily NAV nearly doubles on 25 June 2026 after a flat stretch. The shorter-period position contributes approximately $9,533. This is not evidence of consistently earned returns, whether the jump is genuine trading performance or a reporting artefact. The source price data alone does not establish its cause.

The following is a true rerun with that vault unavailable from the beginning, allowing replacement allocations. It is a retrospective sensitivity test, not a new production blacklist:

| period   | variant                      |      cagr |   sharpe |   max_drawdown |
|:---------|:-----------------------------|----------:|---------:|---------------:|
| hyper_ai | unrestricted_anchor          | 0.19744   | 1.9673   |    -0.0074747  |
| hyper_ai | leave_intothecryptoverse_out | 0.065595  | 1.64895  |    -0.00763826 |
| full     | unrestricted_anchor          | 0.109718  | 1.32122  |    -0.0279633  |
| full     | leave_intothecryptoverse_out | 0.0441022 | 0.843633 |    -0.02846    |

The anchor falls from approximately 19.7% to 6.6% CAGR in the shorter period, and from 11.0% to 4.4% on the full common period. Reduced drawdown survives, but the return objective does not. Source concentration in P&L matters even when the portfolio holds many vaults.

## Robustness of results

NB20 controls are reused only after their input hashes match. Feature arithmetic is checked against the scalar NB19 implementation. New-position audit passes for 10636 engine positions: floor-only entries have known passing estimates. Relative-filter removal makes eight curve pairs identical within one cent. No newly chosen threshold was tuned to results.

Per-vault and per-position P&L, curator flags, largest positive-P&L shares, best-cycle BTC/ETH returns and kurtosis are exported. Leader NAV curves, zero-return shares and largest individual positions expose stale/flat histories and concentrated gains. Best-cycle held-vault observed NAV returns are contextual diagnostics, not exact cashflow-weighted P&L attribution. Closed positions funded above $100 with less than $1 returned: 0. Historical data cleaning can still affect apparent smoothness and jumps; disabling local blacklists cannot restore upstream omitted observations. These are retrospective tests, not out-of-sample evidence.

StratWise receives 0 actual engine positions across the separate runs. Existing 90-day inverse-volatility sizing is unchanged; removing the position quota does not itself supply young-vault sizing estimates. Quality floors require only 28/30 days, not a year, but that inherited sizing limitation remains.

## Conclusion from this batch

Removing allocation limits improves full-period Sharpe for anchor, measured_8, inverse_vol_q10 and A0b, but not floor15 or floor20. It does not achieve approximately 20% full-period CAGR. The unrestricted engine anchor has about 11.0% CAGR, 1.32 Sharpe and 2.8% maximum drawdown; A0b has about 8.4%, 1.40 and 2.4%, respectively.

The unrestricted anchor averages 16.3 holdings, with about 11.1 effective positions and a peak single-vault weight of 39.8%. It becomes a broader inverse-variance book rather than a one-vault bet. With no position-count truncation, the old composite ranking largely ceases to determine membership; sizing and capacity become much more influential.

Strict quality floors do not solve selection. Anchor daily/weekly floor variants return -5.1%/+2.8% CAGR, with peak weights of 96.7%/96.0%. Their candidate pools are smaller, and inverse-variance sizing can concentrate heavily in whichever survivors look calm. The measured_8 and inverse_vol_q10 floor-only arms deliberately equal the anchor after removing relative exclusions.

A0b's unrestricted book averages roughly 154 nonzero holdings but only about 12 effective positions; many allocations are tiny. Its counts are not directly comparable to the engine, which retains its trade-size and small-position thresholds. Both retain inherited accounting differences. Neither the engine nor A0b assigns positive capital to StratWise in this batch; the 90-day sizing-history limitation remains.

The June NAV jump is material: removing intothecryptoverse.com reduces full-period anchor CAGR to 4.4% and Sharpe to 0.84. The better headline risk metrics therefore do not establish steady 20% returns. All blacklists remain disabled in the primary runs; this one-vault exclusion is solely a sensitivity test.
