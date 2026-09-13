# Shared context for an independent review of the stability-leads notebooks (NB20-NB24)

You are reviewing ONE notebook from a quantitative research track. This file is the background
every reviewer gets. The notebook, its build script and the shared modules follow.

## What the strategy is

A vault-of-vaults on Hyperliquid, backtested with the `trade-executor` framework. It holds at
most six Hyperliquid vaults at a time, rebalancing on a two-day cycle over 2026-01-01 to
2026-09-08. Vaults are admitted by a TVL and tradability screen, filtered by a 14-day momentum
gate, ranked by a composite selection score, and sized by inverse volatility. Deposits and
redemptions fill at net asset value; there is no slippage, and performance fees are internalised
in the share-price series.

The anchor (baseline) on the current data snapshot, at full precision:

| metric | value |
|---|---|
| CAGR | 0.378971 |
| cycle Sharpe | 2.159792 |
| cycle volatility | 0.154278 |
| ulcer index | 0.017964 |
| max drawdown | -0.044504 |
| invested-basket BTC beta | 0.045797 |
| mean invested fraction | 0.971969 |
| late-period CAGR | 0.272027 |
| late-period ulcer | 0.025268 |

## What the operator actually wants

Not more return. A **more stable equity curve** - consistent vault profit, smaller drawdowns -
and they have said explicitly they will give up CAGR to get it. The adoption rule encodes that
trade: a floor on return, non-inferiority rather than superiority on Sharpe, and a MATERIAL
required improvement in the ulcer index.

## History that matters

- **NB03-NB12** tested smoothing, volatility targeting, pool caps, breadth, drawdown sizing and
  consistency selection. Nothing was adopted.
- **NB13** found an age barrier: 210 of 320 vaults (66%) are never scorable by the incumbent
  composite because its CAGR leg needs 360 days of history. The hidden cohort's median life
  Sharpe is -0.35 against +0.08 for the scorable cohort, so the barrier is mostly protective, but
  two hidden vaults were genuinely good.
- **NB14-NB19** (plan `14-evidence-weighted-plan.md`) built evidence-weighted selection: an
  event-time, autocorrelation-discounted, cross-sectionally shrunk Sortino score, an expanding
  CAGR score, a composite of the two, evidence-weighted sizing, and a core/satellite structure.
  **NOTHING WAS ADOPTED.** Every notebook was independently reviewed afterwards and the reviews
  found real errors in five of seven: a mixed-sample Sharpe standard error, a union-of-ever-core
  sleeve attribution that misattributed profit, three headings that under-reported failed
  constraints because a pandas column was elided at 50 characters, and several overstated words
  ("unambiguous", "only candidate to clear the floor") that the data did not support. Assume this
  notebook has errors of the same kind until you have checked.
- **NB20-NB24** (plan `20-stability-leads-plan.md`, included below) are the notebooks under
  review now.

## The adoption rule the notebooks are judged against (v3)

Constraints 1-6, from `harness_evidence.py`, unchanged from the previous plan:

1. CAGR >= 0.20
2. cycle Sharpe >= anchor - 0.10 (non-inferiority, not superiority)
3. cycle volatility <= anchor
4. ulcer <= anchor x 0.85 (a MATERIAL 15% improvement, not merely "better")
5. invested-basket BTC beta < anchor
6. mean invested fraction >= 0.90

Constraint 7, redefined for this plan in `harness_stability.py`: cycle Sharpe >=
`placebo_ref_observed(family, vol) + 0.10`, where the reference is the highest cycle Sharpe among
volatility-matched family members no noisier than the candidate. No interpolation.

Robustness on top: a plateau (both 5-step neighbours must also pass), leave-one-vault-out by full
re-simulation with the largest contributing vault masked, and a late-period check
(`late_cagr > 0` and `late_ulcer < anchor late_ulcer`).

ADOPT in this plan means **admission to a prospective shadow protocol**, never authorisation to
deploy capital. Every historical result is exploratory and in-sample.

## Standing rules the notebook was supposed to follow

1. Never select or tune towards a vault by name.
2. Never change a pre-registered threshold after seeing a result. A badly placed one is recorded
   in the Robustness section and left alone.
3. Notebooks are generated from `_build/build_NN.py`; code cells are never hand-edited.
4. Anchor parity is asserted in every notebook against `BASELINE` at full precision.
5. The `failed` column is printed in full and every heading claim is written from the COMPLETE
   failure string. Reporting a row as failing one constraint when it failed six is the single
   most common error this track has made.
6. Every numeric claim in a heading cites the cell it came from.
7. `runs` / `run_by_label` is the only source for every table.
8. Diagnostic logs are cleared before each run and snapshotted after.
9. Adoption logic must be complete from the first run; a robustness run that was skipped, failed
   or was never executed cannot produce a passing flag.
10. Fail closed on any non-finite required metric.

## Two bugs already found and fixed, for calibration

The splice verification run caught both before any research notebook used them.

- `cohort_down_flag` took a cross-sectional median over every vault. A stale Hyperliquid mark is
  an exact zero return, and after the polling-density break most vaults are stale on most days,
  so the median was exactly zero, never negative. The cohort never registered a down day, the
  dependent indicator was NaN everywhere, and the selection block silently degenerated into
  "keep the six lowest pair ids". Look for failure modes of this shape: a filter that silently
  becomes a no-op or an arbitrary ordering.
- The same indicator rewarded silence. A vault that stops reporting never records a loss, so it
  scored as perfectly complementary. Its denominator now counts only days the vault actually
  reported.

## Known limitations already recorded, which you do NOT need to rediscover

- The volatility-matched drop family is largely a data-availability filter, not volatility
  avoidance: `inverse_vol` needs 90 observations and a vault without them scores exactly 0.0,
  sorting to the front of the ascending order. At N = 30, 70.9% of removals have no volatility
  estimate.
- Constraint 7 was not discriminating on this snapshot: its comparator is a spike whose bar the
  anchor itself fails. It was left as pre-registered rather than retuned.
- Stale marks predict losses (NB20), and the resulting sensitivity band consumes 30% to 74% of
  the 15% ulcer margin.

## What I want from you

Correctness of the CODE and correctness of the RESULT INTERPRETATION. Specifically:

- **Arithmetic and statistics.** Is each statistic computed on the sample it claims? Are Sharpe
  and volatility annualised on the strategy's own two-day cycle clock rather than a zero-filled
  daily one? Are bootstrap intervals paired on common block indices? Are p-values computed with
  the add-one correction? Is any test applied to overlapping windows and described as though the
  observations were independent?
- **Look-ahead and leakage.** Does any indicator or diagnostic read data from at or after the
  decision timestamp? `decide_trades` reads bar T-1 by design; a diagnostic that reads bar T and
  is compared against a trading result is not measuring the same thing.
- **Silent degeneration.** Any place a filter, mask, sort or join can become a no-op, an
  arbitrary ordering, or an all-NaN column without raising.
- **Heading claims against cell output.** For every numeric claim and every verdict word in the
  markdown heading, find the cell it cites and check the number is actually there and means what
  the sentence says. Flag overstatement, understatement, and any failure set reported as shorter
  than it is.
- **Conclusions that outrun the evidence.** Causal language for a correlation, a general claim
  from one window, "significant" without a test, a mechanism named as the cause when the notebook
  only showed it is consistent.

For each finding give: a severity (blocking / material / minor), the exact cell number, what is
wrong, why it is wrong, and the concrete fix. If you believe a claim is correct but poorly worded,
say so separately from an actual error. If you find nothing wrong in a section, say that too -
a review that manufactures findings is worse than a short one.

Do not propose new experiments. Review what is here.

## Addendum: what the first review round already found (2026-09-13)

NB20-NB24 have each had an independent review of exactly this kind. Across the five, 41 findings
were raised: 30 confirmed, 5 rejected on inspection, 5 partial, and 4 more found by the verifying
agents that the reviewer had missed. Do not re-raise the items below; they are settled.

**Rejected findings, so you do not repeat them.** Two reviewers independently claimed
`bootstrap_margin_table()` raises an `AttributeError` because `family.loc[...idxmax()]` returns a
label string. It returns the row as a Series whose `.name` is the label, and both verifying agents
reproduced that in a REPL. A third claimed a look-ahead in a diagnostic that is symmetric across
both arms of a comparison and touches no traded result. A fourth was a speculative tie-break
concern disproved by the observed minimum score being nowhere near the boundary.

**Confirmed and already fixed.** `bootstrap_paired_sharpe_diff()` and `family_wise_joint()` used
the population standard deviation while the adoption rule's constraint 2 is defined on the sample
one; both now use `ddof=1` and every notebook was re-run. `joint_loss_frequency` counted a missing
observation as a reported day; now guarded. That second fix was expected to be inert and was NOT,
for a reason worth knowing: `rolling(180)` counts 180 ROWS, not 180 calendar days, and most series
begin recently enough that their own first bar sits inside the trailing window on 2026 decision
dates. Look for that class of confusion.

**Three headline claims were overturned by review**, which is the standard to hold these two
notebooks to. NB20's "the effect is entirely post-April" became "the sparse regime is unresolved,
not null", because its interval is wide enough to contain a larger effect - an absence of power
read as an absence of effect. NB20's staleness band was demoted from an error bar to context,
because it perturbs the anchor only and never measured the candidate-minus-anchor difference.
NB22's "the mechanism worked and the portfolio still lost" was retracted entirely: the fall in
within-basket co-loss is fully explained by the marginal down rates, and against a matched
independence benchmark the selected basket co-loses MORE than chance.

**One suspicious result survived.** NB23 measured a defect that provably exists in the code at
exactly zero occurrences. That is normally a measurement bug. It was not: the reconstruction was
verified against the cached indicator and a new measurement showed the mask threshold is
unreachable on this cohort rather than merely unhit. So do not assume a surprising null is an
error, but do demand that it be shown unreachable rather than merely unobserved.
