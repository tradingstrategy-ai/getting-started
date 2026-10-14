# Experiment 21 — marginal profitability and adaptive portfolio allocation

## What was examined

 increase net account profit by identifying capital worth investing, holdings worth retaining, and opportunities better left in cash. Challenge fixed six-position baskets, rank admission and prescribed inverse-variance allocation. Evaluate when positions are unlikely to profit, including young and missing-score vaults.

**Method:** reproduce C00/v11 under frozen NB20 accounting; audit fees and capital-weighted holding spells; fit monthly causal support, loss-probability, gain/loss-magnitude and calibrated-score forecasts; compare complete basis-aware hold/cash/top-up/replacement path values. Main challengers choose absolute allocations, breadth and cash under explicit capacity and estimated-downside budgets. Ten full-2026 accounts, a registered full-history shortlist and five local sensitivities. Features use completed prior daily buckets; preceding 2025 and earlier history remain available. Missing=True and sparse data use explicit masks/support priors. No untouched holdout exists.



## Hypotheses and verdicts

| Hypothesis                      | Verdict                          | Reason                                                                                                                    |
|:--------------------------------|:---------------------------------|:--------------------------------------------------------------------------------------------------------------------------|
| H1: churn optimisation          | Historical gain                  | One fixed wider-band account isolates net execution effects under the inherited fee model.                                |
| H2: conditional downside        | Probability gain                 | 30d Brier P/D 0.2497/0.2481; economic value must also beat P00.                                                           |
| H3: conditional magnitudes      | Not supported                    | M00 versus D00 holds the probability head, risk budget and allocator constant.                                            |
| H4: new construction beats C00  | Not confirmed                    | Best required new-construction row C01: profit difference USD -49,753, Sharpe 1.654 versus 2.474.                         |
| H5: incumbent decisions         | Not supported                    | Compare joint portfolio decisions with entry-only capital deployment.                                                     |
| H6: missing/young participation | Implemented; utility conditional | Masks, global fit/pooled fallback and actual allocations are reported; undefined metrics are not losses.                  |
| H7: robustness                  | Exploratory                      | No independent holdout; budget, horizon and margin extensions plus contributor/fee/solver diagnostics remain conditional. |

## Results

The strongest required challenger is **C01**, with 11.28% CAGR, 1.654 Sharpe and -1.90% maximum drawdown, versus C00’s 58.59%, 2.474 and -6.36%. Its net account profit difference is **USD -49,753**. This is a researched historical comparison, not independent evidence of future profitability.

Conditional downside probability has 30-day Brier error 0.2481, versus the support prior’s 0.2497. The signal ladder and calibrated-score control distinguish feature value from construction. The highest-profit long new-construction challenger is D03, CAGR 8.62%, Sharpe 1.456, compared with C00 33.13%/1.651.

The notebook evaluates adaptive breadth, incumbent replacement and cash decisions under complete basis-aware path values. The risk-budget-free arm exposes whether the new budget merely restrains profitable exposure. Main weights are not prescribed by inverse variance. Caps, ticket minima and weak forecasts can still determine the realised basket.

The wider sell band F01 adds only **USD 116** in 2026 and **USD 1,025** over the long calendar. Its 2026 drawdown is slightly worse; the long gain is not explained solely by lower paid fees. This is a small execution lead, not a substantial improvement.

At C00’s selected names, the supported 30-day fresh-unit net outcome averages **1.81%**, while D forecasts **-1.23%**. Population-wide probability improvements therefore do not imply useful calibration at the profitable investment margin. These overlapping observations are an opportunity diagnostic, not account attribution.

The H07 sensitivity reaches **26 vaults**, with **99.87%** average September investment, yet loses **USD 23,654**. Removing the risk budget also loses money, and D02 exactly matches D00: six slots were not the binding constraint in that comparison. Retaining incumbents helps D03 relative to D00, but leaves it far behind C00. Better cash use requires better marginal forecasts, not merely more slots or looser risk limits.

M00’s largest marked loss is concentrated in **$🏧| ATM |🏧$**, on **2026-04-09**, with USD -29,497 attributed to that vault. The NAV interval, curator status and BTC/ETH context are reported below; a major single-vault loss is not evidence that probability calibration alone controlled tail severity.

The long D03 retention account reaches 57.24% in one vault through inherited position drift. Its better retention result does not demonstrate concentration control; failure stresses must consider the actual grown exposure.

| Arm   | CAGR    |   Sharpe | Maximum drawdown   | Net profit (USD)   | September cash   |   Maximum vaults held |
|:------|:--------|---------:|:-------------------|:-------------------|:-----------------|----------------------:|
| B00   | 58.59%  |    2.474 | -6.36%             | $62,376            | 49.75%           |                     6 |
| B01   | 49.15%  |    2.214 | -6.41%             | $52,746            | 42.70%           |                     6 |
| F01   | 58.70%  |    2.479 | -6.46%             | $62,492            | 48.97%           |                     6 |
| P00   | 10.44%  |    1.53  | -2.01%             | $11,701            | 100.00%          |                     5 |
| D00   | -2.73%  |   -1.526 | -2.30%             | $-3,112            | 100.00%          |                     6 |
| M00   | -39.74% |   -1.846 | -32.09%            | $-47,722           | 7.62%            |                     8 |
| C01   | 11.28%  |    1.654 | -1.90%             | $12,623            | 100.00%          |                     4 |
| D02   | -2.73%  |   -1.526 | -2.30%             | $-3,112            | 100.00%          |                     6 |
| D03   | 3.19%   |    0.737 | -2.86%             | $3,600             | 16.53%           |                     6 |
| D04   | -17.85% |   -2.127 | -14.55%            | $-20,726           | 100.00%          |                     8 |

### Full-history comparison — 2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial)

The frozen three-candidate shortlist, both controls and the wider-band diagnostic use fresh accounts and genuine historical model cold starts.

| Arm   | CAGR   |   Sharpe | Maximum drawdown   | Net profit (USD)   |
|:------|:-------|---------:|:-------------------|:-------------------|
| B00   | 33.13% |    1.651 | -9.94%             | $270,882           |
| B01   | 18.55% |    1.374 | -7.92%             | $127,078           |
| C01   | 0.86%  |    0.145 | -18.01%            | $4,716             |
| P00   | 5.68%  |    0.654 | -14.32%            | $33,057            |
| D03   | 8.62%  |    1.456 | -4.62%             | $52,076            |
| F01   | 33.22% |    1.664 | -9.92%             | $271,907           |

## Useful leads

Preserve C00 as the economic benchmark. Investigate calibration on the feasible selection margin and a reliable asymmetric loss model before giving these forecasts control of the portfolio. Distinguish prior-dominated young vaults from well-supported names without discarding missing features. The conditional-magnitude model requires tail and extrapolation diagnostics after its large loss. A wider sell band merits a small execution follow-up; additional numerical optimiser complexity is a lower priority because the sampled same-state solver gaps are negligible. Separate incumbent sell decisions from fresh-entry forecasts: D03’s retention ablation helped, but did not establish an improved strategy. Increasing breadth or removing downside restraint alone did not solve profitability.

## Robustness

Independent source controls match NB20 daily equity and every trade; all daily equity paths match to below USD 0.000001. Independent fee/basis and sparse-fill examples passed, and every successful fill was checked against as-of NAV. Engine decision dates and forecast dates are explicitly aligned on both calendars; forecasts are not shifted backwards from a future date. Additional long prediction origins and the last completed feature bucket use the same archive, with the original training and budget samples retained. The base policy horizon is 30 days; the short-holding audit includes dollar-days and censored open positions.

Forecasts refit monthly with matured prior labels. Penalties are selected once per horizon/year using preceding purged probability folds; magnitude heads share that penalty, a disclosed computational compromise. Learning endpoints use actual marks; carried engine outcomes are a sensitivity. The margin arm addresses common calibration uncertainty only, not full personalised coefficient uncertainty.

The allocator is a numerical greedy approximation. Convergence, projection differences and continuous same-state bounds are reported; the frozen denominator and later marked-equity changes can leave inherited cap drift. Gain/loss heads retain the full date measure when conditioning; their mixture passes an exact weighted-mean fixture. The simple loss budget does not provide a guaranteed tail bound or reward diversification by itself.

Fees remain the inherited 10% positive-profit charge plus 0.1% capital allowance, rather than verified live fees. Universe and guard history are retrospective. Largest contributors and strongest NAV intervals are checked with curator flags and BTC/ETH context; fixed-ledger contributor deletion and failure stresses are descriptive. No independent significance or deployment claim is made.
