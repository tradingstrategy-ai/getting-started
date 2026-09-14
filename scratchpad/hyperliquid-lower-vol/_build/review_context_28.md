# Shared context for an independent review of the stable-selection notebooks (NB28-NB31)

You are reviewing ONE notebook from a quantitative research track. This file is the background
every reviewer gets. The notebook, its build script and the shared modules follow.

## What the strategy is

A vault-of-vaults on Hyperliquid, backtested with the `trade-executor` framework. It holds at
most six Hyperliquid vaults at a time, rebalancing on a two-day cycle over 2026-01-01 to
2026-09-08. Vaults are admitted by a TVL and tradability screen, filtered by a 14-day momentum
gate, ranked by a composite selection score, and sized by inverse volatility. Deposits and
redemptions fill at net asset value; there is no slippage, and performance fees are internalised
in the share-price series.

The anchor (baseline) at full precision: CAGR 0.378971, cycle Sharpe 2.159792, cycle volatility
0.154278, ulcer 0.017964, max drawdown -0.044504, invested BTC beta 0.045797, mean invested
0.971969, late CAGR 0.272027, late ulcer 0.025268.

## What the operator wants NOW (this supersedes every earlier objective)

`RESEARCH-RULES.md`, set 2026-09-14: **maximise cycle Sharpe by selecting stable vaults, not lucky
and volatile ones, holding as many distinct vaults as the Sharpe allows.** There is NO return
floor and no requirement to match or beat the anchor on anything - the anchor is a reference
point, reported for continuity, not a bar.

Nine gates, all of which must hold: 1 positive return; 2 single-vault survival (>= 70% Sharpe
retention with the largest contributor masked, by full re-simulation); 3 held-book stability
(capital-weighted own volatility AND own event concentration both better than the anchor's);
4 not luck (`luck_ratio` >= anchor's, `top5_gross_share` <= anchor's); 5 the selection signal
predicts forward stability, measured OUTSIDE the backtest; 6 Sharpe plateau (a FLATNESS test -
centre within 0.25 of each neighbour); 7 positive CAGR in all three sub-periods; 8 diversification
no worse than the anchor on five measures; 9 beat all ten draws of the mechanism's own
information-destroying null.

## The plan these notebooks execute

`28-stable-selection-plan.md`, Draft 3. Its single most important structural decision:
**ADOPT is removed from the vocabulary entirely.** An earlier Codex review found that the screen
chooses signals using 30-day forward returns and the backtests then judge portfolios built from
those signals on returns that overlap the same windows - procedural ordering does not make the
screen out-of-sample, and 126 decisions with a minimum detectable Sharpe difference near 2.50
cannot be split or purged into resolving it. So the batch is hypothesis generation. Verdicts are
SHORTLIST / REJECT / DIAGNOSTIC.

Gate 5's return clause carries an operator-set non-inferiority margin `delta = 5` annualised
percentage points, pre-registered in `_build/harness_rules.py` before any run.

## History that matters

- **NB03-NB12**: smoothing, volatility targeting, pool caps, breadth, drawdown sizing, consistency
  selection. Nothing adopted.
- **NB13**: 210 of 320 vaults are never scorable by the incumbent composite, whose CAGR leg needs
  360 days of history.
- **NB14-NB19**: evidence-weighted selection. Nothing adopted. Independent review found real
  errors in five of seven notebooks, including three headings that under-reported failed
  constraints because a pandas column was elided at 50 characters.
- **NB20-NB24**: stability leads. Nothing adopted. Review found a ddof mismatch and a
  NaN-as-reported bug, and overturned three headline claims.
- **NB25-NB26**: `drop_30` reached the best Sharpe in either batch and 98% of its edge was one
  vault; a purely RANDOM removal of nine vaults ranks 7th of 57 by Sharpe. 70.9% of the
  vol-matched drop's removals at N = 30 have no volatility estimate, and that half is inert.
- **NB28-NB31** are under review now.

## Calibration: bugs this track has already made, so you know the shape to look for

- An indicator took a cross-sectional median over every vault including stale zero returns, so the
  median was exactly zero, the dependent indicator was NaN everywhere, and a selection block
  silently degenerated into "keep the six lowest pair ids" - costing 37 percentage points of CAGR.
- The same indicator rewarded silence: a vault that stops reporting never records a loss and
  scored as perfectly complementary.
- A "random" null used a multiplicative hash that only ROTATED one fixed ring order, so ten seeds
  drew the same set ten times. The tell was `null_median == null_best` on every row, printed and
  missed.
- `rolling(180)` counts 180 ROWS, not 180 calendar days, and most vault series begin recently
  enough that their own first bar sits inside the trailing window.
- A bootstrap used the population standard deviation while the rule it served is defined on the
  sample one.

## What was verified BEFORE these notebooks were built

`_build/verify-prefilter.ipynb` asserts, and all pass: anchor parity against BASELINE at 1e-5 with
all three `decide_trades` splices present and none firing on the anchor path; NB26's `measured_8`
still reproduces (0.409685 / 2.373768); the new prefilter with `inverse_vol` and a count of 8
reproduces `measured_8` on every panel metric at 0.000e+00; `fresh_event_concentration` is
invariant to inserted unchanged marks on all 184 vaults that have one; the offline indicator reads
the screen uses reproduce what `decide_trades` read on all 18,651 (candidate, date) pairs; and the
within-date permutation null draws differently on every decision.

## Standing rules the notebook was supposed to follow

1. Never select or tune towards a vault by name.
2. Never change a pre-registered threshold after seeing a result. Record a badly placed one and
   leave it.
3. Notebooks are generated from `_build/build_NN.py`; code cells are never hand-edited. New shared
   code goes in a NEW module built from the existing ones, never by editing them.
4. Anchor parity asserted in every notebook against `BASELINE` at full precision.
5. The `failed` column printed in full; every heading claim written from the COMPLETE failure
   string. Reporting a row as failing one gate when it failed eight is this track's most common
   error.
6. Every numeric claim in a heading cites the cell it came from. A figure in no cell is removed.
7. `runs` / `run_by_label` is the only source for every table.
8. A robustness run that was skipped, failed or never executed cannot produce a passing flag.
9. A surprising null must be shown UNREACHABLE, not merely unobserved.
10. A rolling window counts ROWS, not calendar days, unless explicitly resampled.
11. Fail closed on any non-finite required metric and name it in the failure string.

## What I want from you

Correctness of the CODE and correctness of the RESULT INTERPRETATION.

- **Arithmetic and statistics.** Is each statistic computed on the sample it claims? Are Sharpe
  and volatility annualised on the strategy's own two-day cycle clock rather than a zero-filled
  daily one? Is the two-way cluster bootstrap actually resampling both dimensions, and are the
  resamples genuinely SHARED across hypotheses as the simultaneous max-T bound requires? Is the
  max-T construction correct for a one-sided LOWER bound? Are p-values add-one corrected? Is any
  test applied to overlapping windows and described as though the observations were independent?
- **Look-ahead and leakage.** Does any indicator or diagnostic read data from at or after the
  decision timestamp? `decide_trades` reads bar T-1 by design. Forward targets are measured over
  `(T, T+30d]` from the NAV carried at T and are deliberately future-looking - that is the point -
  but the SIGNALS they are correlated against must not be.
- **Silent degeneration.** Any place a filter, mask, sort or join can become a no-op, an arbitrary
  ordering, or an all-NaN column without raising.
- **Heading claims against cell output.** For every numeric claim and every verdict word in the
  markdown heading, find the cell it cites and check the number is actually there and means what
  the sentence says. Flag overstatement, understatement, and any failure set reported as shorter
  than it is.
- **Conclusions that outrun the evidence.** Causal language for a correlation, a general claim
  from one window, "significant" without a test, a mechanism named as the cause when the notebook
  only showed it is consistent.

A specific thing to scrutinise in this batch: the headline result is that ZERO of thirteen signals
pass gate 5. A null result of that completeness is exactly the shape a measurement bug takes.
Standing rule 9 requires it be shown unreachable rather than merely unobserved. Decide whether the
notebook does that, or whether the null is better explained by a defect.

For each finding give: a severity (blocking / material / minor), the exact cell number, what is
wrong, why it is wrong, and the concrete fix. If a claim is correct but poorly worded, say so
separately from an actual error. If you find nothing wrong in a section, say that too - a review
that manufactures findings is worse than a short one.

Do not propose new experiments. Review what is here.
