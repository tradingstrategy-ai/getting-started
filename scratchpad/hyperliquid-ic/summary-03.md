# Stable-profit experiment results

The stable-profit track preserved the production return ranking and compared fixed 30-day tail vetoes: observed interval downside (A1), a sparse-compatible severe-loss classifier (A2), and endpoint-aligned absolute BTC beta (A3). A0 is the production replay anchor. The BTC beta rebuild uses actual sparse interval endpoints with a 12-hour reference tolerance; rows with aligned pairs have a median endpoint error of about 2.0 hours and a maximum of about 10.9 hours, all within tolerance. This removes the earlier dense-period-only artefact.

## Primary results

| arm   |    cagr |   volatility |   sharpe |   max_drawdown |   mean_cash_fraction |   mean_stale_positions |   mean_carried_positions |
|:------|--------:|-------------:|---------:|---------------:|---------------------:|-----------------------:|-------------------------:|
| A0    |  0.0495 |       0.2004 |   0.3409 |        -0.1564 |               0.0248 |                      0 |                   1.9726 |
| A1    |  0.0289 |       0.1624 |   0.256  |        -0.0855 |               0.0278 |                      0 |                   1.9671 |
| A2    | -0.0699 |       0.1614 |  -0.369  |        -0.1491 |               0.0291 |                      0 |                   1.9726 |
| A3    | -0.0371 |       0.1668 |  -0.1433 |        -0.1033 |               0.0217 |                      0 |                   1.9699 |

Weekly metrics use recomputed weekly equity returns and 52 periods per year:

| arm   |    cagr |   volatility |   sharpe |   max_drawdown |
|:------|--------:|-------------:|---------:|---------------:|
| A0    |  0.0496 |       0.2173 |   0.3288 |        -0.1486 |
| A1    |  0.0289 |       0.1529 |   0.2606 |        -0.072  |
| A2    | -0.0701 |       0.155  |  -0.3899 |        -0.1296 |
| A3    | -0.0372 |       0.1665 |  -0.1438 |        -0.0868 |

A3's BTC-beta veto was active on 117 dates from 2026-01-23 to 2026-09-12; its full-period metric includes the earlier A0 replay window.

The A2 classifier is used rank-only for vetoing (ROC AUC 0.658, PR AUC 0.397); its log loss 0.562 versus base-rate 0.540 is not a calibrated probability claim. The optional family bundle is scored separately (ROC AUC 0.670) in `family-loss-classifier-metrics.json`.



## Young and sizing checks

| arm                   |    cagr |   volatility |   sharpe |   max_drawdown |   mean_cash_fraction |
|:----------------------|--------:|-------------:|---------:|---------------:|---------------------:|
| A0-young              |  0.085  |       0.2124 |   0.4899 |        -0.1516 |               0.0752 |
| A2-young              | -0.0713 |       0.1846 |  -0.3087 |        -0.1513 |               0.0605 |
| A0-young-cash-matched |  0.0805 |       0.2106 |   0.4725 |        -0.1524 |               0.0917 |

Young access, age and sampling attribution (including selected capital and forward-loss P&L proxies) is saved in `young-selection-attribution.csv`. Young arms apply the 5% cap to under-90-day names and to names with intervals longer than two days; short proxy spans are labelled in the young pool ledgers.



The cash-scaled A0-young arm scales final capped weights down towards the realised A2-young decision-time investment fraction, separating cash dilution from selection where the young caps permit it. Cap-limited dates remain below the reference and are recorded in `cap-diagnostic-manifest.json`. The sizing diagnostic applies each arm's current pre-cap requested allocation before redistribution:

| arm                   |    cagr |   volatility |   sharpe |   max_drawdown |   mean_cash_fraction |
|:----------------------|--------:|-------------:|---------:|---------------:|---------------------:|
| A0-cap                |  0.1248 |       0.1054 |   1.168  |        -0.0639 |               0.4526 |
| A2-cap                |  0.037  |       0.0977 |   0.4202 |        -0.0888 |               0.4413 |
| A0-cap-cash-matched   |  0.1292 |       0.0989 |   1.2782 |        -0.0484 |               0.4742 |
| A0-cap-without-leader |  0.0297 |       0.1169 |   0.3084 |        -0.1311 |               0.4336 |
| A2-cap-without-leader | -0.0294 |       0.1063 |  -0.2282 |        -0.1243 |               0.4279 |

A0-cap's cash-heavy result is a sizing/exposure diagnostic, not a production candidate; the leader-removal and cash-scaled controls are saved with the cap artefacts. Cash matching is cap-feasible rather than exact when A0's TVL or per-vault limits bind.

## Uncertainty and falsification

Paired 44/88-day daily-return block bootstraps include pointwise and simultaneous Sharpe-difference bounds in `_artifacts-stable-profit/paired-block-uncertainty.csv`. The A0 remove-best-day counterfactual has CAGR -0.007, while excluding February has CAGR -0.004; these are attribution sensitivities, not new tuning targets. The 5% annual-reference excess-Sharpe sensitivity is saved in `excess-sharpe-5pct.csv`, and conditional-return volatility/Sharpe by BTC up/down regime is saved in `btc-regime-policy-metrics.csv`.

On identical finite rows, the comparison has 201 dates with at least one excluded row from 2026-01-25 to 2026-08-13 (the finite BTC-beta intersection begins 2026-01-22). Its long-interval share is 0.1%, versus 5.0% in the full evaluation pool, so this is a near-daily subset rather than a complete sparse comparison. Mean excluded growth/loss rates are A1 -0.261/43.8%, A2 -0.255/42.9%, and A3 -0.199/38.6%, versus permutation-null -0.073/19.6%; the learned veto does not beat the simple downside control.

## Decision

| arm   |   higher_sharpe |   no_higher_volatility |   no_deeper_drawdown |   cagr_floor_10pct |   within_5pp_of_anchor |   point_estimate_pass |
|:------|----------------:|-----------------------:|---------------------:|-------------------:|-----------------------:|----------------------:|
| A1    |               0 |                      1 |                    1 |                  0 |                      1 |                     0 |
| A2    |               0 |                      1 |                    1 |                  0 |                      0 |                     0 |
| A3    |               0 |                      1 |                    1 |                  0 |                      0 |                     0 |

The policy replay forward-fills each vault's latest causally available NAV, matching the production universe's daily candle convention. `mean_carried_positions` identifies the exposure marked from such carried values; it does not reveal an unobserved intra-interval path. The no-op A0 replay remains exactly equal to the incumbent path, but neither replay is yet identical to the trade-executor engine. No production promotion follows without unseen-time validation and exact engine reconciliation.
