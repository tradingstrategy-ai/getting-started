# Research rules for the hyperliquid-lower-vol track

Supersedes the anchor-relative adoption rules v1-v4 used in NB03-NB26. Set by the operator on
2026-09-14. Every plan and notebook from NB27 onward uses these.

## Objective

**Maximise cycle Sharpe.**

No return floor. The operator removed it on 2026-09-14 on the grounds that we do not know what
vaults the universe will contain in future, so a floor calibrated to today's opportunity set is
arbitrary. There is no requirement to match or beat
[02-better-format.ipynb](02-better-format.ipynb) on any metric. The anchor is now a REFERENCE
POINT, reported on every table so results stay comparable with NB03-NB26, and it is not a bar.

Metrics are computed on the strategy's own two-day cycle clock, never on a zero-filled daily one.

## What changed, and why it matters

Rules v1-v4 required Sharpe no worse than the anchor's, volatility no worse, a 15% ulcer
improvement, beta below the anchor's and at least 90% of capital deployed. Those five gates
rejected almost everything, and two of them were rejecting candidates the operator would have
accepted.

Dropped: Sharpe non-inferiority, the volatility ceiling, the ulcer-improvement requirement, the
beta ceiling, and the deployment floor. Concentration and cash are both acceptable if they buy
Sharpe.

Also dropped: the 20% CAGR floor. Checked before removing it, across all 57 runs of both
batches: **nothing has high Sharpe and low return.** No run anywhere has Sharpe above 1.8 with
CAGR below 20%. The floor was never binding, so removing it admits nothing it was holding back.

## Three consequences the operator should know

1. **Cash overlays are now out, not in.** They were rejected under v1-v4 by the deployment floor,
   which has gone - but they reduce Sharpe here, so the new objective rejects them on the merits.
   Scaling a book by a constant fraction leaves Sharpe unchanged in theory; this implementation is
   dynamic and de-levers after volatility spikes, which on this data means selling after
   drawdowns. Measured: anchor 2.1598, `target_vol_0.15` 1.8488, `target_vol_0.10` 1.5335, falling
   monotonically as more cash is held.
2. **In this universe Sharpe IS return, so maximising it will not lower volatility.** Across all
   57 runs, cycle Sharpe correlates **+0.985** with CAGR and only **-0.270** with cycle
   volatility. Volatility across every candidate ever built spans a narrow 0.138 to 0.169, while
   CAGR spans -0.23 to 0.49. Selection mechanisms move return; they barely move volatility. The
   only thing in this track that has materially lowered volatility is holding cash - 0.105 at the
   15% target and 0.085 at the 10% - and that lowers Sharpe. **So the operator can have lower
   volatility or higher Sharpe, not both, until a mechanism exists that changes volatility without
   changing deployment.** Nothing tested so far does.
3. **Sharpe is below this window's resolution.** NB03a put the minimum detectable Sharpe
   difference at about 2.50 on 125 two-day cycles. The spread across every candidate ever run is
   roughly 1.5 to 2.7. Ranking runs by Sharpe is therefore ranking on noise, and the new objective
   makes that the explicit selection criterion. **The robustness gates below are now doing all the
   work that the anchor-relative constraints used to do, and they are tightened accordingly.**

## Gates

A candidate is ADOPTED (= admitted to the prospective shadow protocol, never deployed on this
evidence alone) only if every one of these holds.

1. **Positive return.** `cagr > 0`. Not a performance bar, a sanity one: Sharpe is not
   meaningful for a losing strategy and the ratio is uninterpretable when the numerator is
   negative.
2. **Single-vault survival.** Re-simulate with the candidate's largest total-P&L contributor
   masked. The masked run must retain at least 70% of the unmasked run's cycle Sharpe, and must
   still satisfy gate 1. The 70% is pre-registered here, before any run: the anchor retains
   roughly 62% of its CAGR under this test and the best candidate retains 49%, so the bar sits
   deliberately above both. This is a GATE, evaluated before the
   plateau, not a closing robustness note. NB26 established that masking one vault takes the
   anchor from 37.90% to 23.90% and takes the best candidate's edge from 11.10 points to 0.22;
   single-name dependence is the binding property of this book.
3. **Sharpe plateau.** Both pre-registered neighbours must clear gate 1, and the centre's cycle
   Sharpe must be within 0.25 of each neighbour's. This is a FLATNESS test, not a superiority
   test: it rejects a centre that stands above its own neighbours, which is what a spike looks
   like. `drop_30` at 2.747 against `drop_35` at 2.301 fails it by 0.45, correctly.
4. **Sub-period sign.** Positive CAGR in all three segments: sparse (to 2026-03-31), dense (April
   to June) and late (July onwards). A candidate that earns in one regime only has not been shown
   to work.
5. **Null.** Beat all draws of the mechanism's own information-destroying null on cycle Sharpe,
   with at least ten draws. The null must preserve the mechanism's structure and destroy only its
   ranking information. **Assert that the draws actually differ and print the count of distinct
   draws** - NB26's null was one draw repeated ten times and the tell, `null_median == null_best`,
   was visible and missed.

## Reported on every row, never gated

`cycle_sharpe`, `cagr`, `cycle_vol`, `ulcer`, `max_dd`, `abs_invested_beta`, `mean_invested`, the
three sub-period CAGRs and ulcers, `top_vault_pnl_share`, and `lovo_cagr_drop` (CAGR lost when the
largest contributor is masked). Also the anchor's own values, for continuity with NB03-NB26.

Paired block-bootstrap intervals against the anchor are reported for context. They are not a gate,
because the window cannot resolve the differences involved and pretending otherwise was the
mistake constraint 7 made.

## What is retired

- **Constraint 7 in all its forms.** v3 compared against the best observed volatility-matched
  control at or below the candidate's volatility; NB24 found the bar was 2.847, set entirely by
  the `drop_30` spike, which the anchor itself fails at 2.160, and zero of thirteen rows cleared
  it. v4's proposed median fix is not adopted either: with no anchor-relative objective there is
  nothing for it to do. The vol-matched family is still run as a REFERENCE family and reported.
- **The vol-matched family as a "control".** NB21 and NB26 showed 70.9% of its removals at N = 30
  have no volatility estimate at all and that half is exactly inert. Call it the
  data-availability drop family and treat it as a set of candidates, not a placebo.

## Standing method rules, unchanged from the previous plans

1. Never select or tune towards a vault by name.
2. Never change a pre-registered threshold after seeing a result. Record a badly placed one and
   leave it. Changing a rule BEFORE a plan runs, with the reason stated, is the legitimate case -
   this file is that.
3. Build notebooks from `_build/build_NN.py`; never hand-edit a code cell. New shared code goes in
   a new module that builds its splice from the existing ones, never by editing
   `blocks_stability.py`, `blocks_evidence.py`, `harness_*.py` or any `cell*_enhanced.py`:
   NB14-NB26 are committed with executed outputs and embed their text.
4. Assert anchor parity against `BASELINE` in every notebook. Any new `decide_trades` branch
   defaults to incumbent behaviour and is proved inert on the anchor path by that assertion.
5. Print the `failed` column in full; write every heading claim from the complete string.
6. Every numeric claim in a heading cites the cell it comes from. A figure in no cell is removed.
7. `runs` / `run_by_label` is the only source for every table.
8. A robustness run that was skipped, failed or never executed cannot produce a passing flag.
9. A surprising null must be shown unreachable, not merely unobserved.
10. A rolling window counts ROWS, not calendar days, unless explicitly resampled.
11. Fail closed on any non-finite required metric and name it in the failure string.
12. At most three notebooks running at once.
13. Every notebook is independently reviewed after its run, and every finding is verified against
    the cited cell before it is applied.
