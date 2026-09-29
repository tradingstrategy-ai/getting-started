# Entry-time comparison with StratWise

Based on `18-research-leads-no-blacklists.ipynb`. Six addresses, including both Sentiment Edge vaults; all five blacklist-off engine configurations on the full engine period. 139 positions and 53 unique vault-entry dates. Positions across different strategies are separate counterfactuals: their P&Ls must not be added as a portfolio.

## Key new insights and what did we learn?

StratWise observations begin 2026-07-16 15:00:00.016000. Earlier entries cannot be compared with contemporary StratWise history. A separate shape chart aligns a deliberately later StratWise reference date (17 August 2026) with each worst entry; it is an illustration, never contemporaneous evidence. All charts mark missing history explicitly. The separate contemporary chart compares observed curves during July–September; it cannot justify earlier decisions.

## Summary of results

Worst position per vault (chosen retrospectively for explanation, not for screening):

| name                        | candidate       | entry               | exit                |      pnl |   gate_return_proxy |   gate_threshold |   composite_proxy | unscored_proxy   |   nav_return_during_position |   worst_from_entry |
|:----------------------------|:----------------|:--------------------|:--------------------|---------:|--------------------:|-----------------:|------------------:|:-----------------|-----------------------------:|-------------------:|
| Scared Money                | floor20         | 2026-06-04 00:00:00 | 2026-06-08 00:00:00 | -7961.25 |           1.05234   |        0.0227325 |          1        | False            |                   -0.408786  |         -0.461485  |
| BULBUL2DAO                  | measured_8      | 2025-12-14 00:00:00 | 2025-12-18 00:00:00 | -7103.69 |          -0.0605319 |       -0.16      |          0.419346 | False            |                   -0.250313  |         -0.250313  |
| Hyperliquidity Trader (HLT) | floor20         | 2026-01-19 00:00:00 | 2026-02-02 00:00:00 | -5018.83 |           0.178365  |        0.0227325 |          0.825777 | False            |                   -0.278611  |         -0.278611  |
| Cryptoaddcited              | anchor          | 2026-05-09 00:00:00 | 2026-06-04 00:00:00 | -3700.46 |           0.0519336 |       -0.16      |          0.778704 | False            |                   -0.0672777 |         -0.0672777 |
| Sentiment Edge 0xb7e7d0     | floor15         | 2025-12-14 00:00:00 | 2025-12-28 00:00:00 | -3672.9  |           0.151897  |        0.0173802 |          0        | True             |                   -0.0820156 |         -0.0820156 |
| Sentiment Edge 0x026a2e     | inverse_vol_q10 | 2026-06-02 00:00:00 | 2026-06-14 00:00:00 |  -806.72 |           0.15256   |       -0.16      |          0.703367 | False            |                   -0.0264353 |         -0.0299434 |

30-day metric medians (returns and drawdowns are fractions):

|                                             |   return_ |   volatility |   max_drawdown |      ulcer |   top2_gain_share |   return_without_best2 |   positive_week_share |   median_week |   worst_week |   path_efficiency |   max_gap_days |   weekly_return_without_best |   weekly_drawdown |
|:--------------------------------------------|----------:|-------------:|---------------:|-----------:|------------------:|-----------------------:|----------------------:|--------------:|-------------:|------------------:|---------------:|-----------------------------:|------------------:|
| ('StratWise', 'StratWise')                  | 0.0240713 |    0.0248475 |    -0.00254586 | 0.0005329  |          0.330074 |             0.0149418  |                 1     |    0.00389087 |   0.00203131 |          0.780559 |      0.099431  |                   0.00984332 |         0         |
| ('StratWise reference', 'StratWise')        | 0.0240713 |    0.0339876 |    -0.00464369 | 0.00131219 |          0.386186 |             0.0132633  |                 1     |    0.00442018 |   0.00198033 |          0.677196 |      0.0972232 |                   0.0103444  |         0         |
| ('selected', 'BULBUL2DAO')                  | 0.12093   |    0.508663  |    -0.0592231  | 0.0232407  |          0.514158 |             0.0122794  |                 0.625 |    0.00265359 |  -0.0355081  |          0.254039 |      1.5       |                  -0.0304021  |        -0.0355081 |
| ('selected', 'Cryptoaddcited')              | 0.0950985 |    0.299184  |    -0.0405778  | 0.0186143  |          0.496523 |             0.00906042 |                 0.5   |    0.0132146  |  -0.0222679  |          0.381808 |      1         |                   0.0130541  |        -0.0222679 |
| ('selected', 'Hyperliquidity Trader (HLT)') | 0.176414  |    0.996931  |    -0.0352926  | 0.0109262  |          1        |            -0.0218378  |                 0.5   |    0.00697347 |  -0.0180593  |          0.773322 |     13.0764    |                  -0.00436423 |        -0.0180593 |
| ('selected', 'Scared Money')                | 0.136505  |    1.3713    |    -0.223358   | 0.0847525  |          0.557295 |            -0.160425   |                 0.5   |    0.0562607  |  -0.112516   |          0.12915  |      1         |                  -0.120559   |        -0.136541  |
| ('selected', 'Sentiment Edge 0x026a2e')     | 0.0826564 |    0.262778  |    -0.0589778  | 0.0251024  |          0.324887 |             0.0154072  |                 0.75  |    0.0165665  |  -0.0396525  |          0.250944 |      0.125416  |                   0.0079328  |        -0.0396525 |
| ('selected', 'Sentiment Edge 0xb7e7d0')     | 0.0913868 |    0.331183  |    -0.0497172  | 0.0265499  |          1        |            -0.0497172  |                 0.5   |    0.0103424  |  -0.0303878  |          0.5541   |      6.07222   |                  -0.0164552  |        -0.0303878 |

Illustrative screen retention, not a strategy backtest:

| rule                                                   | cohort              |   n |   kept |   keep_rate |
|:-------------------------------------------------------|:--------------------|----:|-------:|------------:|
| Return survives removing best two days                 | selected            |  53 |     18 |    0.339623 |
| Return survives removing best two days                 | StratWise           |   1 |      1 |    1        |
| Return survives removing best two days                 | StratWise reference |  23 |     23 |    1        |
| Drawdown under 5%                                      | selected            |  53 |     17 |    0.320755 |
| Drawdown under 5%                                      | StratWise           |   1 |      1 |    1        |
| Drawdown under 5%                                      | StratWise reference |  23 |     23 |    1        |
| Worst completed week above -3%                         | selected            |  53 |     16 |    0.301887 |
| Worst completed week above -3%                         | StratWise           |   1 |      1 |    1        |
| Worst completed week above -3%                         | StratWise reference |  23 |     23 |    1        |
| At least 75% positive completed weeks                  | selected            |  53 |     18 |    0.339623 |
| At least 75% positive completed weeks                  | StratWise           |   1 |      1 |    1        |
| At least 75% positive completed weeks                  | StratWise reference |  23 |     22 |    0.956522 |
| Top two days below 50% of gains                        | selected            |  53 |     22 |    0.415094 |
| Top two days below 50% of gains                        | StratWise           |   1 |      1 |    1        |
| Top two days below 50% of gains                        | StratWise reference |  23 |     18 |    0.782609 |
| Combined: residual gain + drawdown + weekly loss       | selected            |  53 |      7 |    0.132075 |
| Combined: residual gain + drawdown + weekly loss       | StratWise           |   1 |      1 |    1        |
| Combined: residual gain + drawdown + weekly loss       | StratWise reference |  23 |     23 |    1        |
| Weekly cadence: residual gain + drawdown + weekly loss | selected            |  53 |     12 |    0.226415 |
| Weekly cadence: residual gain + drawdown + weekly loss | StratWise           |   1 |      1 |    1        |
| Weekly cadence: residual gain + drawdown + weekly loss | StratWise reference |  23 |     23 |    1        |

## Why these entries won slots and then lost money

- **Scared Money, 4 June 2026:** its reconstructed 45-day return is +105%, above the floor20 gate of +2.27%, and its composite saturates at 1.00. But the preceding 30 days already contained a 48.7% drawdown, and return becomes -35.2% after deleting the two best days. The position's observed NAV falls about 40.9% by closure. The production source documents share-price rounding problems: these are not reliable trading-return observations.
- **BULBUL2DAO, 14 December 2025:** the 14-day return is -6.1%, which still passes the -16% gate. Its reconstructed composite is 0.42 despite a visibly declining 90-day curve. NAV then drops about 25.0% during the position. Historical ranking and a permissive gate admitted an already unstable path.
- **HLT, 19 January 2026:** a rebound produces +17.8% over 45 days and a composite around 0.83, passing floor20. After removing the two largest gains, the preceding 30-day return is -9.4%. NAV subsequently loses about 27.9% by closure. The return floor mistakes a recovery jump for persistent profitability; the curator also flags unstable share prices.
- **Sentiment Edge 0xb7e7d0, 14 December 2025:** +15.2% over 45 days passes floor15. The conservative reconstruction has no complete composite and assigns zero, which is admissible under the code. Its staircase rise is dominated by a few jumps: removing the best two days turns its preceding 30-day return negative. NAV subsequently falls about 8.2% during the position. The exact engine ranking remains unverified; zero score does not mean the strategy bars entry.
- **Sentiment Edge 0x026a2e, 2 June 2026:** the 14-day rebound is +15.3% and the composite is about 0.70, but the preceding 30-day drawdown is 7.7%. The rebound fails and NAV loses about 2.6% during the position.
- **Cryptoaddcited, 9 May 2026:** +5.2% over 14 days and a composite around 0.78 accompany an increasingly positive curve. Its 30-day drawdown is only 2.4%, and return remains +2.5% after removing the two best days. It passes the proposed combined screen, yet subsequently loses about 6.7% in NAV during the position. This is a genuine limitation of the selected metrics: a reasonable-looking history can reverse.

These are the worst individual positions per address across five configurations, not six typical trades. Dollar P&Ls are in the table; NAV changes explain direction but not the complete effect of trims, deposits and fees.

## Similarities and differences from StratWise

All can display an upward recent curve and sufficiently positive trailing returns. The distinguishing feature in this sample is how much progress remains after removing the biggest gains, and how deep the intervening setbacks are. StratWise's 23 available 30-day reference windows have median return +2.4%, median return excluding the two best days +1.3%, median drawdown 0.46%, and median worst completed week +0.20%. The very high short-sample Sharpe/Sortino is not the main reason to favour it: those ratios are fragile when only a few weeks of small losses exist.

The illustrative combined screen retains 7/53 distinct problematic-vault entry dates and 23/23 StratWise reference dates. By vault it retains Scared Money 0/27, HLT 0/3, Sentiment Edge 0xb7e7d0 1/7, Sentiment Edge 0x026a2e 1/3, BULBUL2DAO 1/4, and Cryptoaddcited 4/9. These problematic-vault entries include profitable positions too; the 46 rejected dates are NOT 46 prevented losses. The weekly-cadence version retains 12/53 problematic-vault entry dates and 23/23 StratWise reference dates. Separation remains, but is weaker than the daily version: reporting cadence explains part of the apparent advantage. Only one unique problem-vault entry date has a full contemporary 30-day StratWise comparison. The other StratWise reference dates are later, overlapping observations of one vault.

## Interpretation and next tests

Compare return after deleting the two largest positive daily log returns, rolling drawdown/ulcer, worst completed week and positive-week share. These distinguish consistent progress from a jump or rebound without requiring a year of history. Positive-week share alone can reward stale data or smooth negative-skew strategies. Pair it with observation coverage and downside controls. Sharpe and Sortino can be undefined or extreme with few losses; no-loss histories are uncertainty, not proof of safety. Use 7/14-day diagnostics for young vaults and build confidence as 30/45/60/90-day evidence arrives, rather than requiring all windows.

The historical selection formula weights bounded 360-day CAGR 60% and bounded 45-day Sortino 40%, then sizes by inverse variance over 90 days. Missing composite scores are admitted at zero. Its ordinary gate allows 14-day returns above -16%; floor15/floor20 require a modest positive 45-day return. Those are return gates, not stability tests. A zero-scored vault can receive a slot when enough scored competitors are unavailable; higher short-term steadiness does not guarantee StratWise a score or a sizing estimate.

## Robustness of results

Pre-entry metrics use only observed marks available before entry, with daily grid ending at the previous midnight. They are conservative analytical reconstructions, NOT exact engine-cache scores/ranks. The source code explains admission rules; the saved NB18 ledger establishes actual selections and P&L. Exact cross-sectional rank, deposit availability and rejected competitors at each entry require instrumented engine replays and are not claimed here.

Daily marks are as-of forward-filled, never backfilled. Older vault histories often report weekly, while StratWise reports densely. A weekly update appears as one large daily gain: daily gain-concentration and apparent smoothness can therefore distinguish reporting cadence rather than trading skill. The additional weekly-cadence screen computes both cohorts on completed 7-day marks and removes their best week instead of their best two days; four weekly returns remain a very small sample. Compare its retention with the daily screen before interpreting the separation. Observation counts, maximum reporting gaps and zero-return shares accompany metrics; sparse marks can conceal intraperiod losses. 7-day returns are non-overlapping within each feature window. Daily feature dates overlap heavily and are not independent samples. No pre-inception StratWise proxy is invented; no rules were validated out of sample. Thresholds are illustrative and chosen for this diagnostic, not proven allocation improvements.

Charts show NAV, not a cashflow-adjusted trading account. The ledger includes repeated deposits, trims, fees and unrealised P&L, so entry-to-exit NAV return need not equal position profitability. After-entry plots extend up to 60 days and mark actual exits; observations after exit were not held. Full holding-period NAV return and worst loss from entry are also tabulated. The same snapshot hash as NB18 is verified. Curator labels identify known price concerns, not independent evidence of losses: Scared Money rounding artefacts and HLT unstable share prices must be distinguished from real trading losses. No new blacklists are introduced.

Files: `later-template-before-after.png`, `same-date-entries.png`, `worst-entries-before-after.png`, `all-entries-before-after.pdf`, `contemporary-curves.png`, `entry-explanations.csv`, `pre-entry-features.csv`, `screen-diagnostics.csv` under `_artifacts-entry-forensics/`.
