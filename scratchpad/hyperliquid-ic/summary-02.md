# Sparse-data rewrite results

Date: 2026-09-15. Corrected rerun following the implementation review.

This is the executed result of [rewrite-plan-01.md](rewrite-plan-01.md). It
replaces the first-pass publication-clock and global-history experiment. The
old artefacts and [summary-01.md](summary-01.md) remain historical records.

The 15 September rerun regenerated notebooks 02–04 and `_artifacts-rewrite`
after the sparse interval panel correction. The figures below supersede the
earlier candidate figures; the stable-profit replay uses this regenerated
incumbent as its A0 anchor.

## Coverage and label construction

The frozen provider reconstruction contains 1,495,861 timestamped rows across
602 vaults. The headline interval is 13 September 2025 through 12 September
2026: 365 daily decision dates. The panel retains 180 pre-evaluation decision
dates for expanding-model training, giving 545 dates and 104,618 eligible
vault-date rows in total. The headline year has 87,081 rows.

Young and sparsely observed vaults are admitted after two non-carried marks at
least one day apart, subject to the 14-day fresh-NAV and $7,500 TVL rules. The
synthetic weekly-vault acceptance check passed: it receives seven daily
predictions between marks without inventing daily risk observations.

Forward variance and downside labels now use the last observed NAV on each
calendar day and require 80% observed consecutive daily returns. This corrects
the previous use of raw intraday inter-arrival intervals, which had discarded
nearly all dense-vault daily risk labels. Growth labels remain conditional on
continued reporting: a label is absent when the required future exit mark is
not available.

| Horizon | Growth labels | Daily variance labels | Unique realised outcomes |
| --- | ---: | ---: | ---: |
| 7 | 101,066 | 59,694 | 66,127 |
| 14 | 99,231 | 58,501 | 64,298 |
| 21 | 97,387 | 57,300 | 62,436 |
| 30 | 93,360 | 55,467 | 59,716 |
| 45 | 89,060 | 51,619 | 55,303 |
| 60 | 84,582 | 47,831 | 50,756 |
| 90 | 75,695 | 40,014 | 41,993 |

Daily predictions and realised outcomes are counted separately. Repeated daily
predictions that share a sparse entry/exit pair retain total model-training
weight one per outcome.

## Forecast evidence

The screen assesses 196 economic features against the forward targets. The
short core is limited to the requested 7–60-day sparse measures; longer and
dense-only measures belong to the optional catalogue. Fold-local Ridge models
retain missingness flags but univariate IC excludes them because availability
is not an economic signal.

Risk persistence is strong on well-covered dates. At a 30-day horizon, for
example, 14-day interval volatility has rank IC 0.771 for forward variance
(219 dates), while 14-day daily volatility has 0.771 (196 dates). The same
measures have rank ICs of 0.748 and 0.741 respectively for 30-day downside
semivariance. These results establish that recent observed risk forecasts
future realised risk; they do not establish a positive-return strategy.

The short-core model's forward-growth IC rises to 45 days and then plateaus in
this sample.
The moving-block intervals below use the conservative horizon-plus-14-day
block length, which includes the allowed endpoint delays. Their effective
block counts are small at longer horizons, so 45–90 day results are evidence
for follow-up rather than a model-selection result.

| Horizon | Mean rank IC | 5th percentile | 95th percentile | Dates | Nominal blocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 | 0.038 | 0.012 | 0.065 | 358 | 17.0 |
| 14 | 0.051 | 0.012 | 0.092 | 351 | 12.5 |
| 21 | 0.091 | 0.048 | 0.131 | 344 | 9.8 |
| 30 | 0.122 | 0.091 | 0.150 | 335 | 7.6 |
| 45 | 0.161 | 0.119 | 0.203 | 320 | 5.4 |
| 60 | 0.150 | 0.115 | 0.180 | 305 | 4.1 |
| 90 | 0.146 | 0.121 | 0.172 | 275 | 2.6 |

The optional catalogue underperforms the short core for every growth horizon
in this rerun. At 30 days its IC is 0.072, versus 0.122 for the short core.
Matched controls give an important qualification: a simple low
`interval_downside_dev_30` ranking is stronger than the Ridge model for most
horizons. The low-downside control treats an observed window with no losing
interval as zero downside and every daily comparison uses the model/control
row intersection. At 30 days, the model-minus-low-risk IC difference is
-0.027 with a paired 90% (5th–95th percentile) block-bootstrap interval of
[-0.065, 0.005]. The short-return control difference is 0.035 with interval
[-0.029, 0.093]. Thus the model has
forecast signal, but it has not demonstrated incremental value over a simple
low-risk sort.

The 30-day model is not excluding young vaults. Its IC is 0.181 for the
30–89-day available-history cohort (334 dates, mean 36 vaults per date) and
0.162 for 14–29 days (208 dates, mean 15 vaults). The <14-day cohorts have
only five to seven dates, so their higher point estimates are not
interpretable. By sampling cohort, the 30-day model has IC 0.118 over the
daily-mark cohort (335 dates) and 0.162 over weekly marks (139 dates). These
cohorts overlap in time and should be read as access and coverage diagnostics,
not independent validation samples.

The bounded prediction-level permutation test gives 0 exceedances in 200
90-day-block draws: familywise p < 0.005 (reported estimate 0.004975). It
holds the fitted predictions fixed and does not rerun feature selection or
model training, so it is not a full research-search null or a promotion test.

## Corrected allocation replay

The allocation replay uses daily forecasts and the production two-day
rebalance cadence. Existing sparse holdings remain marked at their last known
NAV until an actual sale; new buys require a fresh mark. The simulation keeps
cash after a greedy production-style pass: excess from a capped name flows
only to lower-weight names still to be processed, so cash can remain when the
tail of the ranking is capped even if earlier names have headroom. The
incumbent reproduces the
production settings:
360-day CAGR, 45-day Sortino, 60/40 blend, 14-day loss gate and 90-day
inverse-variance sizing, with deterministic address tie-breaking.

The candidate arms use 30-day short-core growth predictions. They are not
improvements in this historical reconstruction.

| Arm | CAGR | Annualised volatility | Sharpe | Maximum drawdown | Mean positions | Mean cash | Mean stale positions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Incumbent | 2.9% | 20.1% | 0.24 | -15.4% | 6.2 | 3.4% | 2.0 |
| Candidate, fixed breadth | -7.9% | 25.5% | -0.20 | -27.8% | 10.2 | 18.8% | 3.2 |
| Candidate, adaptive breadth | -12.4% | 19.9% | -0.57 | -24.4% | 19.2 | 7.4% | 6.0 |

The corrected fixed-breadth replay loses capital and has higher volatility and
deeper drawdown than the incumbent. Adaptive breadth also loses capital and
has the deepest drawdown. Neither candidate supports the requested 20–30%
objective or a production change. This is an idealised fresh-NAV
close-fill reconstruction: all held vaults are marked from raw fresh
observations, a freshly marked vault below candidate TVL eligibility is sold,
and dark holdings would retain their aged last NAV (none occurred in this
run). The source has no fresh marks on 108 of 365 dates, so the nominal
two-day production cadence produces only nine rebalances during the initial
weekly-marked period; this is matched across arms but does not reproduce a
carried-candle production backtest. Exact strategy-engine settlement remains
promotion validation.

## Result and next step

The useful finding is narrower than the original ambition: recent observed
risk, particularly short-window interval and daily volatility, is highly
predictive of future realised risk; lower observed downside risk also predicts
better forward growth. The current multi-feature growth model adds no
demonstrated value over that simple low-risk control. Neither tested allocation
rule improves the incumbent's stability profile or meets the return objective.

The next experiment should predeclare a low-risk ranking with one horizon and
one capped sizing rule, compare it directly with the incumbent on matched
dates, and only then run an exact settlement replay. A full feature-bundle
permutation is required if a data-mined multi-feature candidate is considered
for production.
