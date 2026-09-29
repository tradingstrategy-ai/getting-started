# Reflection on the latest research batch

Date: 2026-09-15.

The clearest finding is that future risk and likely losers are predictable, but
the tested forecast signals do not produce a portfolio with higher Sharpe than
the production-style return ranking. The useful predictive information is
mainly in risk persistence and loser avoidance, rather than reliably ranking
the best future winners.

## What worked

Recent volatility and downside risk are highly persistent:

- Fourteen-day volatility has approximately 0.77 rank IC against 30-day
  forward variance.
- The short-core growth model has positive rank IC across every tested
  horizon: 0.122 at 30 days, peaking at 0.161 at 45 days.
- The severe-loss classifier has useful ranking power, with ROC AUC 0.658 and
  PR AUC 0.397.
- Both the learned model and simple downside measures identify genuinely bad
  vaults.

On the identical finite comparison rows, the subsequently realised outcomes
of the excluded vaults were:

| Exclusion rule | Mean forward growth | Loss probability |
| --- | ---: | ---: |
| Simple downside veto | -26.1% | 43.8% |
| Learned-loss veto | -25.5% | 42.9% |
| Absolute BTC-beta veto | -19.9% | 38.6% |
| Random exclusion | -7.3% | 19.6% |

This confirms that loser avoidance is predictable. The learned classifier,
however, does not improve on the simple downside feature. Its probability
estimates are also not calibrated: model log loss is 0.562, compared with
0.540 for the constant base-rate forecast. It should therefore be treated as
a ranking signal only.

The finite A1/A2/A3 comparison covers 201 dates with exclusions between 25
January and 13 August 2026. It is a near-daily subset: only 0.1% of its rows
have intervals longer than two days, compared with 5.0% in the full comparison
pool. The result does not establish equivalent effectiveness for sparse weekly
vaults.

## What failed at portfolio level

| Strategy | CAGR | Annualised volatility | Sharpe | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: |
| Production replay A0 | 2.9% | 20.1% | 0.24 | -15.4% |
| Simple downside veto A1 | -1.3% | 15.6% | -0.00 | -8.6% |
| Learned-loss veto A2 | -8.3% | 16.1% | -0.46 | -15.0% |
| Absolute BTC-beta veto A3 | -7.1% | 16.7% | -0.36 | -10.3% |

The simple downside veto produced lower volatility and a shallower drawdown,
but removed too much profitable exposure. The learned and BTC-beta vetoes did
worse. None of the primary arms passed the provisional shortlist criteria, and
the paired block-bootstrap results provide no reliable evidence of higher
Sharpe.

The production CAGR/Sortino ranking therefore appears to contain a
load-bearing return signal. Removing risky vaults indiscriminately also removes
vaults responsible for much of the upside. Forecasting an adverse outcome is
not enough: the portfolio mapping must preserve enough expected return for the
lower volatility to improve Sharpe.

## Young and sparse vaults

The rewritten pipeline can make daily decisions for young and weekly-observed
vaults without a long-history admission barrier. The growth model has positive
IC in these cohorts:

| Cohort | 30-day growth rank IC |
| --- | ---: |
| 14–29 days of available history | 0.162 |
| 30–89 days of available history | 0.181 |
| Weekly-observed vaults | 0.162 |

This forecasting evidence did not survive portfolio allocation:

| Young-vault arm | CAGR | Volatility | Sharpe | Maximum drawdown |
| --- | ---: | ---: | ---: | ---: |
| A0 with young access | -3.6% | 24.5% | -0.03 | -17.4% |
| Learned veto with young access | -16.5% | 21.1% | -0.75 | -18.6% |
| Cash-matched A0 with young access | -3.8% | 24.4% | -0.04 | -17.5% |

Young vaults are now technically accessible, but a short attractive equity
curve is not sufficient evidence for a material allocation. The 5% cap for
young and sparsely observed vaults remains justified.

## Directionality

The absolute BTC-beta veto did not improve Sharpe. It had sufficient data to
operate on only 117 dates, from 23 January to 12 September 2026. Its full-year
metric includes the earlier period during which it simply replayed A0.

The regime diagnostic shows that portfolio returns remain directional. A0 had
conditional Sharpe of approximately 2.45 on BTC-up days and -1.66 on BTC-down
days. Avoiding high absolute beta alone is too crude: a vault can have moderate
measured beta while earning most of its return through a small number of
directional events.

## Most promising result

The strongest numerical result came from changing position sizing rather than
from replacing the production ranking:

| Sizing diagnostic | CAGR | Volatility | Sharpe | Maximum drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: | ---: |
| A0 accepted-dollar cap | 18.6% | 10.6% | 1.66 | -6.3% | 45.3% |
| Cash-matched A0 cap | 18.5% | 10.0% | 1.75 | -4.8% | 47.8% |
| A0 cap without its leading contributor | 7.9% | 11.6% | 0.71 | -12.9% | 44.0% |
| A2 accepted-dollar cap | 8.3% | 9.7% | 0.88 | -8.7% | 44.0% |
| A2 cap without its leading contributor | 2.1% | 10.6% | 0.25 | -12.3% | 42.5% |

This suggests that preventing redistributed capital from flowing into weaker
tail positions may be more useful than replacing the incumbent ranking with a
forecast model. The result is still a cash-heavy sizing diagnostic rather than
a production candidate. Removing the leading contributor also reduces the A0
cap result materially, from 18.6% CAGR and 1.66 Sharpe to 7.9% and 0.71.

## Robustness and interpretation

The incumbent itself is fragile in this one-year replay. Removing its best day
changes CAGR to -2.6%, while excluding February changes CAGR to -6.1%. This
means that the positive A0 performance is concentrated in a small part of the
sample and cannot serve as strong evidence that any overlay is production
ready.

The current evidence supports the following conclusions:

1. Recent risk is strongly forecastable.
2. Likely large losers can be identified, but a simple downside metric performs
   at least as well as the learned classifier.
3. The tested vetoes reduce some risk but sacrifice too much return to improve
   Sharpe.
4. Young and sparse vault admission now works correctly, but the tested young
   allocation rules are unprofitable.
5. Conservative accepted-dollar caps and intentional cash exposure are the
   most promising direction from this batch.
6. The cap result needs unseen-time validation and an exact strategy-engine
   replay before it can be considered for production.

The immediate follow-up should retain the production return ranking, use a
simple risk measure rather than an uncalibrated classifier, and evaluate one
predeclared conservative dollar-cap rule. The cap mechanism, cash target and
leader-removal control should be frozen before running it on new data.
