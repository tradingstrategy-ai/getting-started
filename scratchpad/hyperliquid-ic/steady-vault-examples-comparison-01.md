# Steady-profit references versus later losing winners

We compared StratWise and **[ Systemic Strategies ] L/S Grids** with five losing entries from notebook 24. These are retrospectively chosen case studies, not evidence that a screening rule predicts unseen outcomes. “Lucky” describes the hypothesis; prices alone do not establish the underlying trading mechanism.

## Comparison design

Frozen notebook 22 input files, as used by notebooks 23–24. Outcomes stop at 9 September 2026 exclusive. The references use 13 August 2026 (StratWise’s first shortlisted purchase); L/S Grids uses the same comparison date, not a claimed portfolio entry. Losers use their individual notebook 24 entry dates. Thus the comparison is event-aligned, not market-regime matched. All input features use strictly earlier observations. Reference snapshots on 1 August, 13 August, 1 September and 9 September check date sensitivity.

Metrics are calculated over 7, 14, 28, 60 and 90 calendar days, using whatever history exists. Weekly returns use complete seven-day boundary intervals; endpoints use the latest earlier observation no more than seven days old. No backfill or minimum-age exclusion. Few weekly observations mean uncertain estimates. Daily metrics in the CSV are supplemental: carried prices can inflate apparent daily smoothness, so daily win rate should not be compared blindly across observation frequencies. Drawdown uses all observed prices and can reveal setbacks weekly endpoints miss. Higher-frequency series may reveal more intraperiod drawdown.

## What was visible before selection

Below: up to 28 days of history. Weekly volatility is the sample standard deviation of weekly simple returns, unannualised. Best-week share divides the largest positive weekly return by the sum of positive weekly returns. It is sensitive to sample count and week alignment.

| name                        | date       |   weeks | positive_weeks   | median_week   | weekly_std   | best_week_share   | drawdown   |
|:----------------------------|:-----------|--------:|:-----------------|:--------------|:-------------|:------------------|:-----------|
| StratWise                   | 2026-08-13 |       3 | 100.00%          | 0.31%         | 0.32%        | 66.25%            | -0.52%     |
| Systemic L/S Grids          | 2026-08-13 |       4 | 75.00%           | 0.76%         | 1.01%        | 56.04%            | -4.08%     |
| $🏧| ATM |🏧$               | 2026-04-01 |       4 | 100.00%          | 4.44%         | 0.93%        | 29.70%            | 0.00%      |
| Crypto Czars - Road to 100k | 2026-06-02 |       4 | 50.00%           | 0.43%         | 1.38%        | 73.73%            | -2.37%     |
| SOL/BTC Neutral             | 2026-06-04 |       4 | 75.00%           | 2.34%         | 13.85%       | 85.99%            | -11.48%    |
| Orion                       | 2026-07-02 |       4 | 75.00%           | 2.94%         | 6.06%        | 56.23%            | -14.89%    |
| Anti Martigaler             | 2026-07-16 |       1 | 0.00%            | -11.07%       | Unavailable  | Unavailable       | -67.82%    |

- **StratWise:** very small absolute fluctuations and drawdown. On 13 August, only three complete weekly returns were available. It was not uniformly profitable from inception: at 1 August both available complete weeks were negative. By September its weekly gains were consistently positive. A strict early win-rate gate would have excluded it.
- **L/S Grids:** profitable but substantially bumpier than StratWise. Its 28-day drawdown varied from 2.47% to 6.88% across the four reference snapshots. Best-week gain concentration reached 74.9% on 1 September. Treating the two references as an identical smoothness class would be misleading.
- **SOL/BTC Neutral and Orion:** material fluctuations and drawdowns were already visible despite favourable monthly records. SOL/BTC Neutral derived 86% of its positive weekly gains from one week. Orion had a 14.9% observed drawdown in the preceding 28 days.
- **Anti Martigaler:** a 67.8% drawdown was already visible within its roughly ten-day history. A positive inception-to-entry return hid a very unstable path. The daily-boundary return in the CSV is negative because its first daily sample follows a large initial intraday gain; it is not the inception return used by notebook 24. Do not substitute one for the other.
- **Crypto Czars:** weaker recent consistency (two of four weeks positive) and concentrated weekly gains, but its drawdown was smaller than L/S Grids. A drawdown-only filter cannot separate these examples cleanly.
- **ATM is the decisive counterexample:** four positive weeks, zero observed drawdown and only 30% of positive gains in its best week. It looked smoother than L/S Grids on these measures, then lost 88.9% over the following 14-day observation window. Its roughly 18.2% preceding 28-day return was unusually high relative to StratWise, but L/S Grids also had 15–18% rolling 28-day gains at other snapshots. A high-return ban does not robustly preserve both references while rejecting ATM.

## Which measurements deserve the next experiment

| Measure / time series | Evidence here | Use |
|---|---|---|
| Rolling 14/28/60-day observed drawdown | Exposes Anti Martigaler, Orion and SOL/BTC Neutral | Soft risk penalty; test separately from profitability |
| Weekly return dispersion and worst week | Separates large swings from StratWise’s small movements | Risk sizing with uncertainty for short samples |
| Positive-week fraction alongside monthly profitability | Highlights Crypto Czars’ recent deterioration | Continuous reward, not an all-positive requirement |
| Largest week’s share of positive gains | Highlights SOL/BTC Neutral and Crypto Czars | Diagnostic first; can also penalise L/S Grids and young StratWise |
| Residual dispersion around a log-price trend | Low for StratWise; higher for volatile cases | Candidate measure of deviation from steady growth; does not solve ATM |
| Rolling change in risk and weekly hit rate | Separates improving and deteriorating histories | Test incremental prediction, avoiding many tuned thresholds |
| Weekly BTC beta and residual return series | Not measured in this comparison | Separate directional gains from market-independent progress in a subsequent experiment; beta alone does not imply luck |

The best-week share, weekly consistency and volatility overlap between good references and losing examples. No single threshold tested here separates every loser while retaining both references. Path efficiency is especially misleading for ATM: its monotonic earlier path gives the maximum value.

## Time series to inspect together

1. Entry-normalised equity before and after selection, displayed separately.
2. Non-overlapping weekly returns; monthly totals alongside them.
3. Rolling observed drawdown and weekly dispersion over 14/28/60 days.
4. Rolling positive-week fraction and gain concentration, showing observation counts.
5. In a subsequent test, BTC-relative returns and regression residuals, with uncertainty for short histories.

![Before and after comparison](_artifacts-steady-examples/before-after.png)

The chart uses separate vertical scales to expose each path; compare the numeric amplitudes, not just shape. Curves stop where observations or the research period end. A line between sparse observations does not establish continuous smoothness. StratWise and L/S Grids have only 26 days of subsequent research-period observations at the chosen reference date, so their 30/60-day labels are unavailable. Missing future labels are not zero returns. The references’ 14-day returns were +1.54% and +13.30%; these are underlying vault returns, not portfolio P&L.

## Practical conclusion

Price-path risk measures could have reduced exposure to several visibly unstable selections. They do not prove that a smooth winner is safe: ATM defeats that interpretation. Next test a few independent soft penalties and risk-sizing rules against the unchanged monthly ranking, across all eligible vaults and chronological periods. Retain young-vault eligibility, record missing evidence explicitly, and do not tune thresholds to force these seven examples into the desired categories. No new strategy or backtest was executed in this comparison.

Reproducible script: `steady_vault_examples_compare.py`. Generated tables: `pre-entry-metrics.csv`, `reference-sensitivity.csv`, and `forward-returns.csv` in the ignored `_artifacts-steady-examples` folder. Source cases: notebook 24 `largest-loss-entry-features.csv`.
