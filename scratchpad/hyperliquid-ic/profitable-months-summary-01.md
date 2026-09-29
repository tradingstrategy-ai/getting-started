# Profitable-month selection variants

Executed notebook: [23-research-profitable-months.ipynb](23-research-profitable-months.ipynb).

Based on `22-research-allocation-decomposition.ipynb`. Twenty fixed engine runs on its frozen inputs; all blacklists remain disabled. The experiment changes monthly selection and score-based sizing together, with an equal-weight profitability control. It is historical exploratory research, not an out-of-sample strategy discovery.

## Key new insights

No monthly-score arm reaches 20% CAGR in hyper_ai.

No monthly-score arm reaches 20% CAGR in full.

StratWise has actual positions in 7 of the 20 runs; see the table for periods and variants. Admission alone does not imply a meaningful portfolio weight.

Every new arm loses money in both periods, including the equal-weight profitability control. These standalone monthly policies do not meet the objective of high Sharpe with roughly 20% CAGR. This does not isolate whether the monthly feature itself lacks value: selection, sizing and the removal of the recent-return gate all change relative to the anchor.

The count score is still a return-chasing score: multiplying by mean positive return allows large winning months to dominate modest steady gains. A positive trailing compounded return also admits many vaults whose recent performance has deteriorated. Completed-month scores do not react to a reversal within the current month. These are mechanisms to investigate, not separately proven causal attributions.

The 10% cap improves CAGR and drawdown versus uncapped mean-return sizing at both lookbacks in both periods. This does not establish an investable strategy or isolate ranking skill.

StratWise is purchased in 7 configurations, with native-window P&L from $0.76 to $28.16 on $150,000 initial capital. It has no history in the Hyper-ai period. Young-vault access is distinct from meaningful allocation to steady vaults.

Four simple rules are tested at three and six completed calendar months. Let P/N be positive/negative month counts, M all available completed months including zeros, and G the mean positive-month return.

| Rule | Formula | Meaning |
|---|---|---|
| positive_reward | P/M × G | Reward frequent and larger profitable months; losses dilute frequency |
| month_balance | (P−N)/M × G | Losing months explicitly penalise desirability |
| mean_return | Mean monthly return | Include the size of losses as well as gains |
| capped_mean | Mean(min(monthly return, 10%)) | Limit the influence of exceptional positive months; retain losses in full |
| equal_profit | Equal weights for positive compounded growth, six months | Sizing/selection reference without the monthly ranking |
| anchor | Original six-position CAGR/Sortino + inverse variance | NB22 policy with corrected redemption accounting |

All new arms require positive compounded growth and a positive score. Relative scores determine weights across all qualifying, deposit-eligible vaults; no fixed position count or portfolio-weight ceiling. The inherited 33% historical vault-TVL capacity, 98% deployment target, 0.5% minimum position weight, small-trade thresholds and engine fee/settlement model remain. A tiny positive score does not guarantee an executed position. Monthly arms replace the old 14-day gate and long-lookback score; inverse variance is not used. Thus comparison with the original anchor is a full-policy comparison, not an isolated score substitution. Rebalancing retains the parent's two-day engine cycle; completed-month scores normally change monthly, while provisional scores can change each cycle.

All 20 runs, including anchors, now price redemptions from the gross quoted mid and apply the fee once. Partial reductions previously supplied an already-net planned mid, causing a second deduction. The extra accrued-fee cash buffer has been removed: every arm uses the same inherited cash headroom. Original outputs are preserved in `_artifacts-profitable-months-before-fee-fix/`; corrected anchors intentionally no longer match the defective NB22 equity curves. Strategy rules and frozen data remain unchanged.

The inherited $750 sell-rebalance threshold can suppress trims in the smaller monthly-rule positions, so realised weights can drift from targets. A monthly arm with no qualifying candidates liquidates, whereas the inherited anchor retains its original empty-candidate behaviour.

Completed calendar months exclude the current incomplete month and the inception partial month. If no completed month exists, use unannualised since-inception return as one provisional observation after two marks at least a day apart; the month count remains zero. No 90/360-day sizing requirement, minimum monthly evidence count or daily-reporting gate. Older vaults are normalised by available month count, not rewarded just for age. A month with zero return gives no positive reward. Provisional history is shorter and less comparable; it is disclosed rather than assigned fake completed months.

## Summary of results

| period   | rule            |   lookback | cagr   |   sharpe |   weekly_sharpe | max_drawdown   |
|:---------|:----------------|-----------:|:-------|---------:|----------------:|:---------------|
| hyper_ai | anchor          |          6 | 41.2%  |     2.01 |            2.13 | -10.2%         |
| hyper_ai | equal_profit    |          6 | -16.5% |    -1.69 |           -1.49 | -11.6%         |
| hyper_ai | positive_reward |          3 | -58.5% |    -2.32 |           -2    | -42.5%         |
| hyper_ai | positive_reward |          6 | -29.5% |    -1.61 |           -1.43 | -20.8%         |
| hyper_ai | month_balance   |          3 | -49.1% |    -2.32 |           -2.06 | -36.4%         |
| hyper_ai | month_balance   |          6 | -29.2% |    -1.87 |           -1.91 | -20.1%         |
| hyper_ai | mean_return     |          3 | -57.2% |    -2.34 |           -2.12 | -40.8%         |
| hyper_ai | mean_return     |          6 | -35.6% |    -1.98 |           -1.92 | -23.3%         |
| hyper_ai | capped_mean     |          3 | -34.3% |    -2.41 |           -2.44 | -20.3%         |
| hyper_ai | capped_mean     |          6 | -29.8% |    -2.17 |           -2.08 | -18.8%         |
| full     | anchor          |          6 | 4.8%   |     0.34 |            0.34 | -13.8%         |
| full     | equal_profit    |          6 | -23.3% |    -2.06 |           -2.01 | -26.0%         |
| full     | positive_reward |          3 | -52.0% |    -2.18 |           -1.99 | -58.0%         |
| full     | positive_reward |          6 | -43.4% |    -2.22 |           -2.18 | -47.8%         |
| full     | month_balance   |          3 | -49.6% |    -2.51 |           -2.4  | -53.3%         |
| full     | month_balance   |          6 | -48.6% |    -2.78 |           -2.74 | -51.6%         |
| full     | mean_return     |          3 | -52.3% |    -2.24 |           -2.12 | -57.9%         |
| full     | mean_return     |          6 | -43.9% |    -2.28 |           -2.27 | -48.6%         |
| full     | capped_mean     |          3 | -32.8% |    -2.19 |           -2.16 | -37.4%         |
| full     | capped_mean     |          6 | -32.3% |    -2.19 |           -2.14 | -34.7%         |

Full common period: 13 September 2025–8 September 2026. Hyper-ai common period: 1 January–8 July 2026. Native full engine run starts 1 August (initial equity point 31 July). Full metrics slice already-running portfolios. Two-day and weekly Sharpe are separately reported; no assumption of annual returns persisting.

### Actual StratWise allocations

| period   | rule            |   lookback | first_entry   |   positions |       pnl |
|:---------|:----------------|-----------:|:--------------|------------:|----------:|
| full     | capped_mean     |          3 | 2026-08-15    |           1 | 17.4568   |
| full     | capped_mean     |          6 | 2026-08-07    |           1 | 28.1644   |
| full     | equal_profit    |          6 | 2026-07-24    |           3 | 23.8367   |
| full     | mean_return     |          6 | 2026-08-23    |           1 |  2.40181  |
| full     | month_balance   |          3 | 2026-08-23    |           1 |  2.22967  |
| full     | month_balance   |          6 | 2026-08-21    |           1 |  7.445    |
| full     | positive_reward |          6 | 2026-08-29    |           1 |  0.761453 |

### Allocation and leading contributors

| period   | rule            |   lookback |   mean_invested |   mean_positions |   peak_weight |
|:---------|:----------------|-----------:|----------------:|-----------------:|--------------:|
| full     | anchor          |          6 |        0.971576 |          5.93923 |     0.352888  |
| full     | capped_mean     |          3 |        0.975088 |         51.326   |     0.085753  |
| full     | capped_mean     |          6 |        0.976991 |         51.0276  |     0.0775484 |
| full     | equal_profit    |          6 |        0.99355  |         76.0331  |     0.0242934 |
| full     | mean_return     |          3 |        0.957983 |         46.7735  |     0.133963  |
| full     | mean_return     |          6 |        0.966403 |         50.4917  |     0.128192  |
| full     | month_balance   |          3 |        0.96673  |         44.3094  |     0.19257   |
| full     | month_balance   |          6 |        0.980179 |         45.8564  |     0.186384  |
| full     | positive_reward |          3 |        0.959642 |         49.4033  |     0.139074  |
| full     | positive_reward |          6 |        0.969621 |         54.4475  |     0.101765  |
| hyper_ai | anchor          |          6 |        0.966438 |          5.85263 |     0.336212  |
| hyper_ai | capped_mean     |          3 |        0.959038 |         51.5368  |     0.0862206 |
| hyper_ai | capped_mean     |          6 |        0.961166 |         51.8     |     0.0786275 |
| hyper_ai | equal_profit    |          6 |        0.983924 |         77.8842  |     0.0251625 |
| hyper_ai | mean_return     |          3 |        0.938516 |         47.2421  |     0.137252  |
| hyper_ai | mean_return     |          6 |        0.947492 |         52.3895  |     0.126094  |
| hyper_ai | month_balance   |          3 |        0.950598 |         44.9474  |     0.192834  |
| hyper_ai | month_balance   |          6 |        0.965107 |         46.4842  |     0.195976  |
| hyper_ai | positive_reward |          3 |        0.941171 |         49.5474  |     0.139472  |
| hyper_ai | positive_reward |          6 |        0.954616 |         55.9368  |     0.0907079 |

| period   | rule            |   lookback | address                                    | name            |      pnl |   positive_pnl_share |
|:---------|:----------------|-----------:|:-------------------------------------------|:----------------|---------:|---------------------:|
| hyper_ai | anchor          |          6 | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital | 22643.4  |            0.513695  |
| full     | anchor          |          6 | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital | 17234.3  |            0.300909  |
| hyper_ai | positive_reward |          6 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  8480.42 |            0.216012  |
| hyper_ai | mean_return     |          3 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  7009.93 |            0.199082  |
| hyper_ai | mean_return     |          6 | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital |  6328.9  |            0.1728    |
| hyper_ai | positive_reward |          3 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  6181.98 |            0.169225  |
| full     | mean_return     |          3 | 0x4dec0a851849056e259128464ef28ce78afa27f6 | pmalt           |  6050.88 |            0.13508   |
| hyper_ai | month_balance   |          6 | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital |  5963.1  |            0.183328  |
| full     | positive_reward |          6 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  5842.13 |            0.142619  |
| full     | positive_reward |          3 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  5753.52 |            0.125579  |
| full     | mean_return     |          6 | 0x4dec0a851849056e259128464ef28ce78afa27f6 | pmalt           |  5697.51 |            0.142327  |
| full     | month_balance   |          6 | 0x4dec0a851849056e259128464ef28ce78afa27f6 | pmalt           |  5651.86 |            0.195007  |
| full     | month_balance   |          3 | 0x4dec0a851849056e259128464ef28ce78afa27f6 | pmalt           |  5506.2  |            0.14515   |
| hyper_ai | month_balance   |          3 | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital |  5050.81 |            0.162002  |
| full     | capped_mean     |          6 | 0x4dec0a851849056e259128464ef28ce78afa27f6 | pmalt           |  4714.54 |            0.122486  |
| full     | capped_mean     |          3 | 0x4dec0a851849056e259128464ef28ce78afa27f6 | pmalt           |  4292.84 |            0.103747  |
| hyper_ai | capped_mean     |          6 | 0x77fee2df7bad4f1db93052fa82bf78eaab771a16 | Realist Capital |  3271.08 |            0.145625  |
| hyper_ai | equal_profit    |          6 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  2819.38 |            0.13196   |
| full     | equal_profit    |          6 | 0x5290ab34acb59cfe1371baa5782eba14433d308f | Scared Money    |  2778.47 |            0.0798506 |
| hyper_ai | capped_mean     |          3 | 0x697bc3dd77539fa84156d0e1c95287ea5524fd6b | Probot 5/9/12   |  2542    |            0.114177  |

### Largest losses in the six-month capped rule

| period   | rule        |   lookback | address                                    | name                                |      pnl |
|:---------|:------------|-----------:|:-------------------------------------------|:------------------------------------|---------:|
| full     | capped_mean |          6 | 0x503b30b2eff8d62f07ab9fe5f1fb0e6a18e86bc1 | Singh Capital                       | -5307.32 |
| full     | capped_mean |          6 | 0x2ee1f7d5650bb9bc08e101dc5ab2300b4f5c1be9 | Pepe vs                             | -4075.19 |
| full     | capped_mean |          6 | 0xb1688bcae7de088fe9f2ef1d1f79e681fc0443ed | $🏧| ATM |🏧$                       | -4012.74 |
| full     | capped_mean |          6 | 0x6135b5d1050968d2dfe27dd1d0b9bf57336893f4 | OM MA NI PAD ME HUM                 | -2328.26 |
| full     | capped_mean |          6 | 0xdc9955a83218b71713a83ee072055591bd4c7304 | Crypto Plaza Relative Momentum Edge | -2001.19 |
| full     | capped_mean |          6 | 0x2fc81b8d1d22921acb412c7a054ff62ce880eece | Cycle Model                         | -1932.97 |
| full     | capped_mean |          6 | 0xa93aaeeb8e641122777cce7cb78e729702149059 | Anti Martigaler                     | -1931.74 |
| full     | capped_mean |          6 | 0x06cd60ae3be5e43a444ee0352cb28ce961209b3b | AIIA Quant                          | -1875.42 |

These position P&Ls cover the native engine run, including the period before the full-period common metrics slice. They should not be summed to reconcile the sliced CAGR.

## Robustness of results

### Largest cycles and market comparison

| period   | rule            |   lookback | start               | end                 |   portfolio_return |   kurtosis |     BTCUSDT |     ETHUSDT |
|:---------|:----------------|-----------:|:--------------------|:--------------------|-------------------:|-----------:|------------:|------------:|
| hyper_ai | anchor          |          6 | 2026-06-24 00:00:00 | 2026-06-26 00:00:00 |          0.0753088 |    9.92439 | -0.0468732  | -0.0595574  |
| hyper_ai | equal_profit    |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0327183 |    4.7687  | -0.00984317 | -0.00774409 |
| hyper_ai | positive_reward |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.097457  |    5.10638 |  0.0290225  |  0.0683746  |
| hyper_ai | positive_reward |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0491133 |    3.4268  | -0.00984317 | -0.00774409 |
| hyper_ai | month_balance   |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0559466 |    4.58492 |  0.0290225  |  0.0683746  |
| hyper_ai | month_balance   |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0441061 |    1.87738 | -0.00984317 | -0.00774409 |
| hyper_ai | mean_return     |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.095592  |    4.48222 |  0.0290225  |  0.0683746  |
| hyper_ai | mean_return     |          6 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0501423 |    3.96416 |  0.0290225  |  0.0683746  |
| hyper_ai | capped_mean     |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0383499 |    1.59496 |  0.0290225  |  0.0683746  |
| hyper_ai | capped_mean     |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0343363 |    2.32377 | -0.00984317 | -0.00774409 |
| full     | anchor          |          6 | 2026-06-24 00:00:00 | 2026-06-26 00:00:00 |          0.0734473 |   11.57    | -0.0468732  | -0.0595574  |
| full     | equal_profit    |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0293191 |   10.0172  | -0.00984317 | -0.00774409 |
| full     | positive_reward |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0969273 |    5.80938 |  0.0290225  |  0.0683746  |
| full     | positive_reward |          6 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0542095 |    7.3501  |  0.0290225  |  0.0683746  |
| full     | month_balance   |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0586608 |    7.77426 |  0.0290225  |  0.0683746  |
| full     | month_balance   |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0448491 |   11.759   | -0.00984317 | -0.00774409 |
| full     | mean_return     |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0976397 |    6.11221 |  0.0290225  |  0.0683746  |
| full     | mean_return     |          6 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0567573 |    8.71798 |  0.0290225  |  0.0683746  |
| full     | capped_mean     |          3 | 2026-06-14 00:00:00 | 2026-06-16 00:00:00 |          0.0391905 |   18.4267  |  0.0290225  |  0.0683746  |
| full     | capped_mean     |          6 | 2026-01-25 00:00:00 | 2026-01-27 00:00:00 |          0.0340733 |   26.6929  | -0.00984317 | -0.00774409 |

### Curator-flagged executed positions

| period   | rule            |   lookback |   flagged_positions |   flagged_pnl |
|:---------|:----------------|-----------:|--------------------:|--------------:|
| full     | anchor          |          6 |                  19 |    -8765.58   |
| full     | capped_mean     |          3 |                  36 |      787.744  |
| full     | capped_mean     |          6 |                  27 |     -390.279  |
| full     | equal_profit    |          6 |                  26 |     -897.772  |
| full     | mean_return     |          3 |                  39 |    -1183.6    |
| full     | mean_return     |          6 |                  27 |    -1627.18   |
| full     | month_balance   |          3 |                  38 |    -1057.75   |
| full     | month_balance   |          6 |                  29 |    -3592.63   |
| full     | positive_reward |          3 |                  30 |     -875.633  |
| full     | positive_reward |          6 |                  24 |    -1651.03   |
| hyper_ai | anchor          |          6 |                  13 |    -1834.98   |
| hyper_ai | capped_mean     |          3 |                  25 |     1963.27   |
| hyper_ai | capped_mean     |          6 |                  17 |     1355.5    |
| hyper_ai | equal_profit    |          6 |                  18 |    -1792.95   |
| hyper_ai | mean_return     |          3 |                  24 |       60.0989 |
| hyper_ai | mean_return     |          6 |                  20 |    -1734.03   |
| hyper_ai | month_balance   |          3 |                  27 |     1987.55   |
| hyper_ai | month_balance   |          6 |                  17 |      218.467  |
| hyper_ai | positive_reward |          3 |                  20 |     -599.696  |
| hyper_ai | positive_reward |          6 |                  18 |    -2491.22   |

Anchor dates must still match NB22; equity differences from corrected fees are exported to `anchor-fee-correction.csv`. Every executed redemption is checked against gross mid times one minus its fee, with 10,530 checked sells in `redemption-fee-audit.csv`. Month-cutoff and young-history assertions run before the score panel. Every decision uses strictly earlier prices; weekly observations can be carried to month boundaries. Scores and decisions are exported, as are trades, per-vault P&L, curator annotations and the best two-day return alongside BTC/ETH. All universe arms share the same frozen file paths. Reporting and repair limitations of that snapshot persist.

The largest positive cycles and BTC/ETH comparisons appear above; they are not evidence of steady returns. Curator-flagged vault P&L and leading-contributor shares are retained so unusually large gains are visible without treating them as proof of selection skill.

### Change after fixing fees

| period   | rule            |   lookback |   cagr_before |   cagr_corrected |   cagr_change_pp |   sharpe_before |   sharpe_corrected |   max_drawdown_before |   max_drawdown_corrected |
|:---------|:----------------|-----------:|--------------:|-----------------:|-----------------:|----------------:|-------------------:|----------------------:|-------------------------:|
| hyper_ai | anchor          |          6 |        0.3422 |           0.4123 |           7.0162 |          1.7359 |             2.0054 |               -0.104  |                  -0.1019 |
| hyper_ai | equal_profit    |          6 |       -0.1734 |          -0.1649 |           0.8471 |         -1.8092 |            -1.6916 |               -0.1202 |                  -0.1162 |
| hyper_ai | positive_reward |          3 |       -0.6001 |          -0.5849 |           1.5181 |         -2.4364 |            -2.3159 |               -0.433  |                  -0.4254 |
| hyper_ai | positive_reward |          6 |       -0.3205 |          -0.2951 |           2.5357 |         -1.8268 |            -1.6125 |               -0.2201 |                  -0.2079 |
| hyper_ai | month_balance   |          3 |       -0.5072 |          -0.4913 |           1.5862 |         -2.4662 |            -2.3195 |               -0.3705 |                  -0.3643 |
| hyper_ai | month_balance   |          6 |       -0.3182 |          -0.2923 |           2.5923 |         -2.1053 |            -1.8742 |               -0.2098 |                  -0.2006 |
| hyper_ai | mean_return     |          3 |       -0.5908 |          -0.5722 |           1.8607 |         -2.4688 |            -2.3358 |               -0.4168 |                  -0.4083 |
| hyper_ai | mean_return     |          6 |       -0.3853 |          -0.3563 |           2.9079 |         -2.2215 |            -1.9843 |               -0.2497 |                  -0.2332 |
| hyper_ai | capped_mean     |          3 |       -0.361  |          -0.3431 |           1.7916 |         -2.5866 |            -2.4092 |               -0.2138 |                  -0.2031 |
| hyper_ai | capped_mean     |          6 |       -0.3134 |          -0.2981 |           1.5254 |         -2.311  |            -2.1671 |               -0.1961 |                  -0.1875 |
| full     | anchor          |          6 |       -0.0037 |           0.0477 |           5.1374 |          0.0725 |             0.3432 |               -0.1437 |                  -0.1381 |
| full     | equal_profit    |          6 |       -0.2381 |          -0.233  |           0.5082 |         -2.1566 |            -2.059  |               -0.263  |                  -0.2597 |
| full     | positive_reward |          3 |       -0.5383 |          -0.5201 |           1.8136 |         -2.3304 |            -2.1804 |               -0.5918 |                  -0.5802 |
| full     | positive_reward |          6 |       -0.4475 |          -0.4337 |           1.3874 |         -2.3756 |            -2.2238 |               -0.4857 |                  -0.4779 |
| full     | month_balance   |          3 |       -0.5112 |          -0.4961 |           1.5084 |         -2.6653 |            -2.5075 |               -0.5453 |                  -0.5331 |
| full     | month_balance   |          6 |       -0.5014 |          -0.4857 |           1.573  |         -2.9361 |            -2.7782 |               -0.5276 |                  -0.5159 |
| full     | mean_return     |          3 |       -0.5405 |          -0.5229 |           1.7604 |         -2.3789 |            -2.2367 |               -0.5899 |                  -0.5792 |
| full     | mean_return     |          6 |       -0.4649 |          -0.4393 |           2.5556 |         -2.4931 |            -2.2836 |               -0.5056 |                  -0.4861 |
| full     | capped_mean     |          3 |       -0.3502 |          -0.328  |           2.2178 |         -2.4222 |            -2.189  |               -0.3916 |                  -0.374  |
| full     | capped_mean     |          6 |       -0.3438 |          -0.3226 |           2.1135 |         -2.4077 |            -2.1895 |               -0.3654 |                  -0.3472 |

This comparison comes from full re-simulations, not adding estimated fees back to equity. Changed cash balances can alter later allocations and trades.

The 10% positive-month cap is a declared sensitivity, not an optimised threshold. The equal-profit control helps show whether scoring adds value, but different positive-score sets also change holdings. Cumulative buy value is turnover, not time-weighted allocation. Individual P&L covers the native engine window. No winner chosen on these reused dates constitutes independent validation; young-vault access is checked through actual trades.
