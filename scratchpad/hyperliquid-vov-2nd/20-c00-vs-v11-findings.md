# Experiment 20 — C00 versus deployed v11 rules

Based on [NB19](19-backtest-protected-core-score-risk-allocation.ipynb) and [NB15](15-backtest-allocation-vs-v11.ipynb).

**Goal:** compare C00 and hyper-ai-v11.py under identical data, capital, timing, fees and accounting. No parameter search. C00 changes the score, risk-estimation package and allocation method together; this experiment measures the combined strategy difference, not each change's isolated contribution.

**Periods:** 2026-01-01 → 2026-10-05 exclusive (through 4 October); full history 2023-03-01 → 2026-10-08 exclusive (through 7 October, last archive day partial). Fresh USD 150,000 in each account, all preceding warmup including 2025. 2026 outputs appear first, with full-history outputs explicitly labelled.

## Key new insights

2026: C00 changes profit by USD +9,630, CAGR by +9.44 percentage points and Sharpe by +0.260. The largest positive vault contribution to the difference is [ Systemic Strategies ] L/S Grids, USD +4,868 (50.5% of the net account gap).

Long: C00 changes profit by USD +143,804, CAGR by +14.58 percentage points and Sharpe by +0.278. The largest positive vault contribution to the difference is Road to 10 Million, USD +26,941 (18.7% of the net account gap).

C00 improves historical CAGR and Sharpe in both periods, supporting the economic hypothesis on these inspected samples. Full-history drawdown is worse, so this is not an improvement in every risk measure. In 2026, C00 earns more despite higher average cash. Full-history differences also include earlier deployment and different accumulated wealth. Isolating score, risk estimation and waterfall contributions remains a separate experiment.

## Summary of results

| Period | V11 CAGR | C00 CAGR | V11 Sharpe | C00 Sharpe | V11 max DD | C00 max DD | C00 extra profit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026 | 49.15% | 58.59% | 2.214 | 2.474 | -6.41% | -6.36% | USD +9,630 |
| Long | 18.55% | 33.13% | 1.374 | 1.651 | -7.92% | -9.94% | USD +143,804 |

## Robustness of results

2026 C00: largest positive contributor Realist Capital accounts for 35.4% of positive vault profit; best daily update 6.46%, excess kurtosis 11.0. Long C00: largest positive contributor Delta_01 accounts for 17.2% of positive vault profit; best daily update 15.65%, excess kurtosis 90.9.

2026 C00 strongest update: Realist Capital contributes USD 6,419, with a 14.1% NAV change across 2.0 days; BTC and ETH change -4.7% and -6.0% over that observation interval. Curator excluded=False, quarantined=False.

Long C00 strongest update: Road to 10 Million contributes USD 15,536, with a 30.3% NAV change across 7.0 days; BTC and ETH change 19.6% and 17.1% over that observation interval. Curator excluded=False, quarantined=False.

C00 reproduces NB19's daily equity and metrics. All executed fills pass the as-of-NAV audit, and position profit reconciles to account profit within USD 1. Common partial-sell, cached-tax and funding corrections apply to both arms. Strongest vault updates are checked against curator flags and BTC/ETH over their actual observation intervals in the tables below. Sparse NAV may bunch returns; last-known NAV does not establish an executable live price. The two periods overlap and were previously researched; there is no untouched holdout or statistical significance claim. Universe/guard selection is retrospective and inherited fee assumptions remain economically unverified. No deployment-server revision was verified.

### Strategy logic — applies to both backtesting periods

These are strategy rules, not separate fitted configurations for each period. Scores select vaults; risk estimates determine allocation. The local v11 module represents deployed rules, not a verified replay of live account decisions.

| Rule | V11 | C00 |
| --- | --- | --- |
| Ranking | 0.60 CAGR360 + 0.40 Sortino45 | 0.48 CAGR360 + 0.32 Sortino45 + 0.10 CAGR180 + 0.10 Sortino30 |
| Component clips | CAGR 0–100%; Sortino 0–3, normalised to 0–1 | Same |
| Risk | Source 90-day variance, volatility floor 0.0001 | 90-day variance blended with leave-one-out positive peer median; own weight m/(m+30), m actual updates |
| Allocation | Proportional inverse variance with source capacity adjustment | Waterfall: lowest regularised risk first, filling each permitted capacity |
| Missing score | Composite becomes unscored/zero; eligible vaults can still enter | Same; no available-component reweighting |
| Missing risk | Source missing indicator gives zero raw signal | Partial history and peer prior supported; unusable basket risk falls back to equal raw priorities |
| Maximum positions | 6; no capacity extension | Same |
| Selection | Source rank hysteresis, entry 6 / exit 8, minimum improvement 0 | Same machinery, different score values |
| Limits | 98% deployment, 33% concentration, 33% vault TVL, minimum TVL USD 7,500 | Same |
| Rebalance and gate | Every 2 days; 14-day return must exceed −16% | Same |
| Execution thresholds | Buy 0.05%, sell 0.5% of reference equity, USD 5 floor; cleanup 0.5% | Same |
| Permissions | Source guard, whitelist, deposit/redemption and leader-share policy | Same |

### Common accounting and data — applies to both backtesting periods

Fresh USD 150,000 accounts; the same repaired archive, universe, guard and preceding warmup, including 2025 for the 2026 accounts. Indicators use completed prior daily buckets. Execution uses the latest recorded NAV at or before each query, with no additional slippage or freshness veto. Causal research NAV filling starts at inception; missing observations are not backfilled from the future.

Both arms use three identical research accounting corrections: partial sells charge the modelled redemption fee once against gross observed NAV; newly reopened positions reset the previous position's cached tax before marking; buys are bounded by final synchronous net sell proceeds. These changes leave ranking and sizing rules intact. Modelled charges remain 10% of positive redemption profit plus a 0.1% capital allowance; the allowance is an assumption, not a verified venue fee. Live v11 pays actual execution costs, so this is a clean comparison of rules rather than a live-performance replication.
