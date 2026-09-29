# Event-concentration plan: is the penalty measuring lumpy returns or sparse reporting?

- **Status**: SUPERSEDED, never executed. The Codex review
  ([27-event-concentration-plan-codex-review.md](27-event-concentration-plan-codex-review.md))
  found seven blocking problems, and the research rules changed the same day. Its question -
  does the concentration measure confound lumpiness with sparse reporting - survives as one of
  thirteen signals screened in [28-stable-selection-plan.md](28-stable-selection-plan.md), and
  the review's findings on nulls, event-time measures and re-sampling are applied there.
- **Track**: `hyperliquid-lower-vol`, notebooks NB27-NB30. Follows
  [20-stability-leads-plan.md](20-stability-leads-plan.md) (NB20-NB26, NOTHING ADOPTED, every
  notebook independently reviewed) and revisits a result from
  [09-backtest-consistency-selection.ipynb](09-backtest-consistency-selection.ipynb) that the
  earlier plan passed over.
- **Baseline**: [02-better-format.ipynb](02-better-format.ipynb), re-run as the anchor in every
  notebook. Full precision in `_build/harness_stability.py` (`BASELINE`): CAGR 0.378971, cycle
  Sharpe 2.159792, cycle vol 0.154278, ulcer 0.017964, max drawdown -0.044504, invested beta
  0.045797, mean invested 0.971969, late CAGR 0.272027, late ulcer 0.025268.
- **Every result is exploratory and in-sample.** ADOPT means admission to the prospective shadow
  protocol, never authorisation to deploy capital.
- **Data provenance**: each notebook prints SHA-256 content hashes of the price archive, metadata
  snapshot, Binance store and BTC cache, plus the `_build/` commit. The 2026-09-13 archive refresh
  did not move the anchor; parity is asserted, not assumed.

## The result being revisited, stated correctly

`event_concentration_lambda = 0.5` in NB09, full window, one point, no sweep:

| metric | penalty | anchor | rule v3 |
|---|---|---|---|
| CAGR | 0.474299 | 0.378971 | PASS |
| cycle Sharpe | 2.380774 | 2.159792 | PASS |
| cycle volatility | 0.169071 | 0.154278 | **FAIL** |
| ulcer | 0.018649 | 0.017964 | **FAIL**, worse than the anchor |
| max drawdown | -0.047311 | -0.044504 | worse |
| invested BTC beta | 0.021197 | 0.045797 | PASS |
| mean invested | 0.961087 | 0.971969 | PASS |
| Martin | 25.43 | 21.10 | - |

It fails two constraints, which is the best failure profile of anything in either completed plan
apart from the `drop_30` spike that NB26 dismantled. But note what it does: **it improves return
and roughens the curve.** NB09 said so explicitly. It is a return-and-beta enhancer, not a
stability mechanism, and it is the opposite of the operator's stated objective as it stands. This
plan does not pretend otherwise, and would not exist if that were the whole story.

## Why it is worth a plan anyway

The measure is defined on CALENDAR days:

```python
top5 = residual.rolling(180, min_periods=180).apply(lambda x: np.sort(x)[-5:].sum(), raw=True)
concentration = top5 / positive.rolling(180, min_periods=180).sum()
```

A stale Hyperliquid mark is an exact zero return (NB57). A vault polled weekly therefore delivers
the same economic return through roughly a seventh as many non-zero days, and its best-five-day
share is mechanically higher. **The measure cannot distinguish a vault whose returns are genuinely
lumpy from one that is simply observed less often.**

On 2026-09-14 a direct check established the confound this implies: median TVL correlates -0.46
with the share of days inside a five-day reporting gap, the bottom TVL decile spends 80% of days
in such a gap against 7% for the top, and the gap-predicts-loss effect that NB20 reported across
the whole archive falls to -20 bps with a vault-clustered interval of [-91, +39] once restricted
to the vaults above the strategy's own $7,500 screen.

**So the hypothesis this plan tests is mechanical, not statistical.** If the penalty is partly a
covert sparse-reporting filter, it is down-weighting vaults whose ulcer is *understated* by flat
lines between marks. Removing them would raise the portfolio's MEASURED ulcer without raising its
economic risk - which is exactly the signature observed: return up, ulcer up, volatility up, beta
down. A polling-invariant version of the same measure would then keep the return and beta benefit
without the risk cost. That is a falsifiable prediction and this plan is built to falsify it.

**Second defect, independent of the first.** `residual_event_concentration` is NaN until 180
calendar days and 60 fresh marks. `decide_trades` applies the penalty only when the value is
non-NaN, so a vault too young or too sparse to be measured **escapes the penalty entirely and
keeps its full signal**. The penalty is therefore weakest exactly where lumpiness is most likely.
Nobody has tested the strict alternative.

## The three leads

| # | Lead | What would make it a result |
|---|---|---|
| 1 | **Is the measure confounded?** Correlate realised concentration against fresh-mark count, median TVL and stale share across every candidate and decision date, and measure the mechanical effect directly by re-sampling a vault's own history at lower frequency. | A quantified confound: the share of cross-sectional variance in concentration attributable to observation frequency rather than to return shape. NB27 adopts nothing. |
| 2 | **Does the incumbent penalty survive a proper test?** One lambda, no plateau, no leave-one-vault-out, one window, permissive admission. | A contiguous lambda plateau passing rule v4 including leave-one-vault-out, with the volatility and ulcer failures either resolved or confirmed as structural. |
| 3 | **Does a polling-invariant version keep the return and drop the risk cost?** Same construction in event time: best-five share of positive residual return over the last N FRESH events. | The event-time penalty retains the CAGR and beta improvement while its volatility and ulcer land at or below the anchor's. If it keeps the return AND the roughness, the confound hypothesis is refuted and the penalty is genuinely selecting lumpy winners. |

## Rules for the executing agent

Carried from the previous two plans, plus what their twelve independent reviews taught.

1. **Never select or tune towards a vault by name.**
2. **Never change a pre-registered threshold after seeing a result.** Record a badly placed one in
   the Robustness section and leave it. Rule v4's constraint 7 is being changed BEFORE this plan
   runs, for a stated reason, which is the legitimate case.
3. **Build from `_build/`** with a `build_NN.py` importing `builder.py`; never hand-edit a code
   cell. New shared code goes in `_build/blocks_concentration.py`, which builds its splice from
   `blocks_stability.py` rather than editing it. **Do not modify `blocks_stability.py`,
   `blocks_evidence.py`, `harness_stability.py`, `harness_evidence.py`, `harness.py` or any
   `cell*_enhanced.py`**: NB14-NB26 are committed with executed outputs and embed their text, so
   editing them stops those notebooks regenerating from `_build`.
4. **Anchor parity every notebook**, asserted against `BASELINE` at full precision. Any new
   `decide_trades` branch must default to incumbent behaviour and be proved inert on the anchor
   path by that assertion, exactly as `vol_drop_mode` was.
5. **Print the `failed` column in full** and write every heading claim from the complete string.
6. **Every numeric claim in a heading cites the cell it comes from.** A figure that appears in no
   cell must be computed in one or removed.
7. **`runs` / `run_by_label` is the only source** for every table; unique labels; every control
   goes through `run_and_record()`.
8. **Adoption logic complete from the first run.** A robustness run that was skipped, failed or
   was never executed cannot produce a passing flag.
9. **A surprising null must be shown unreachable, not merely unobserved.** NB23's zero
   forward-fill count survived because a follow-up measurement proved the threshold could not be
   reached on this cohort. NB26's random null did not survive: all ten seeds were one draw.
   **Any null, permutation or randomisation must assert that its draws actually differ**, and
   print the count of distinct draws.
10. **A rolling window counts ROWS, not calendar days**, unless it is explicitly resampled. That
    confusion made a supposedly inert fix bite in NB22 and it is the single most repeated error in
    this track.
11. **Fail closed on any non-finite required metric** and name it in the failure string.
12. **Run with the observable runner** from the repository root; at most three notebooks at once.
13. **Headings** carry the three standard sections, UK English, sentence case, verdict word in the
    first insight bullet, and the provenance hashes. Commit per notebook. Post nothing to the PR
    unless asked. Each notebook is independently reviewed after its run before anything is called
    a result.

## Objective and adoption rule (v4)

Constraints 1-6 are unchanged from v3, via `harness_evidence.py`: CAGR >= 0.20; cycle Sharpe >=
anchor - 0.10; cycle volatility <= anchor; ulcer <= 0.85 x anchor; invested-basket beta < anchor;
mean invested >= 0.90.

**Constraint 7 is changed, before running, for a stated reason.** v3's comparator was the highest
cycle Sharpe among volatility-matched family members no noisier than the candidate. NB24 found
that made the bar 2.847, set entirely by the `drop_30` spike, which the ANCHOR ITSELF fails at
2.160 - zero of thirteen rows cleared it and the constraint discriminated nothing. NB26 then
showed that spike is 98%-attributable to a single vault. A maximum over a family containing one
outlier is not a robust comparator. v4 uses the **median**:

```python
def control_ref_v4(family: pd.DataFrame, vol: float) -> float:
    """Median cycle Sharpe among vol-matched family members no noisier than the candidate.

    Median, not max: v3's maximum was set by a single spike that NB26 showed was one vault, and
    the anchor could not clear the resulting bar. The median cannot be moved by one outlier. The
    family is the 5-step drop family INCLUDING N = 0, which is the anchor - v3's docstring said
    the anchor was a member and the implementation omitted it.
    """
    at_or_below = family[family["cycle_vol"] <= vol]
    if not len(at_or_below):
        at_or_below = family.nsmallest(1, "cycle_vol")
    return float(at_or_below["cycle_sharpe"].median())
```

Constraint 7: `cycle_sharpe >= control_ref_v4(family, cycle_vol) + 0.10`. This is chosen for
robustness to a single outlier, not tuned to a result; the family has not been re-run under it.

**Constraint 8 is new: leave-one-vault-out is a first-class gate, not a final robustness step.**
NB26 established that masking one vault takes the anchor from 37.90% to 23.90%, over a third of
its return, and takes the best candidate's edge from 11.10 points to 0.22. Single-name dependence
is the binding property of this book, so every candidate is judged with it removed:

> With the candidate's largest total-P&L contributor masked, and compared against the ANCHOR with
> its own largest contributor masked, the candidate must still satisfy constraints 1, 2 and 4.

Masked-to-masked is the right counterfactual; comparing a masked candidate to an unmasked anchor
would fail everything. Constraint 8 requires a full re-simulation per candidate, so the lambda
sweep is deliberately small.

Robustness on top, unchanged: a plateau (both neighbours also pass constraints 1-8), the late
period (`late_cagr > 0` and `late_ulcer < anchor late_ulcer`), and paired block-bootstrap margins
against the anchor at -0.10 and against the constraint-7 comparator at +0.10.

**Reported on every row, not gated:** `top_vault_pnl_share` (the largest single vault's share of
gross profit) and `lovo_cagr_drop` (CAGR lost when it is masked). The operator's objective is a
stable curve; a book whose result is one name is not stable however its ulcer reads.

Verdict words: ADOPT (= admission to shadow) / REJECT / CONTROL / DIAGNOSTIC.

## Shared additions

### `_build/blocks_concentration.py`

Built from `blocks_stability.py`'s replacements, never by editing it, exactly as
`blocks_drop_modes.py` was. Adds:

- **`concentration_mode`** parameter: `'calendar'` (the incumbent, default, so every earlier run
  is unaffected) or `'event'`.
- **`residual_event_concentration_event_time`**: the same statistic computed over the last
  `event_concentration_max_events` FRESH marks rather than 180 calendar days. Beta is estimated on
  the same fresh subsequence. Polling-invariant by construction: a vault observed weekly and the
  same vault observed daily give the same value, up to estimation noise.
- **`require_concentration_scored`** parameter: when true, a candidate whose concentration is NaN
  is excluded rather than admitted at full signal. Default false, the incumbent behaviour.
- **`CONCENTRATION_LOG`**: a per-cycle read-only record of each candidate's concentration value,
  the realised signal multiplier `1 - lambda * c`, and whether the value was NaN. Cleared and
  snapshotted by `run_and_record()` like the other logs. NB28 and NB29 read this rather than
  reconstructing the penalty offline.

The `decide_trades` splice extends the existing concentration block; the `'calendar'` branch is
character-identical to the line it replaces, so the default reproduces NB09's 0.474299 / 2.380774
exactly. That equality is asserted, not assumed.

### `_build/harness_concentration.py`

Appended after `harness_stability.py`. Defines `control_ref_v4()`, `passes_constraints_v4()` /
`failing_constraints_v4()` (constraints 1-8, failing closed on non-finite and on any unexecuted
leave-one-vault-out run), `lovo_gate()` which runs the masked candidate and masked anchor and
returns the three Booleans, `top_vault_pnl_share()`, and `verdict_table_v4()`. It reuses
`run_and_record`, `build_family`, `bootstrap_margin_table` and `family_wise_joint` unchanged.

**Before any notebook is built**: splice both files, compile every cell, run the anchor with the
splice present and `event_concentration_lambda = 0`, assert `BASELINE` parity and an empty
`CONCENTRATION_LOG`, then run `event_concentration_lambda = 0.5` and assert it reproduces NB09.
Reuse the `_build/verify-stability-splices.ipynb` pattern.

## Experiment track

### NB27 - research: is the concentration measure confounded by observation frequency?

**File**: `27-research-concentration-confound.ipynb`, `_build/build_27.py`. Verdict: DIAGNOSTIC.

No backtests beyond the anchor. Four sections.

1. **Cross-sectional association.** For every candidate on every decision date, read
   `residual_event_concentration` from the cached indicator and pair it with that vault's
   fresh-mark count over the same 180-day window, its stale share, its median TVL over the window
   and its age. Report Spearman correlations, a decile table of concentration by fresh-mark count,
   and the share of cross-sectional variance in concentration explained by observation frequency
   alone. Restrict the whole analysis to the tradable pool (the vaults that actually pass the
   screens and reach `decide_trades`), because the 2026-09-14 check showed cohort-wide statistics
   are dominated by vaults the strategy never touches.
2. **The mechanical effect, measured directly.** Take each vault's own daily history and re-sample
   it to 1-in-2, 1-in-3, 1-in-5 and 1-in-7 observation frequency by keeping every k-th mark and
   carrying the price forward. Recompute the calendar-day measure on each. Report how far the
   value moves for the SAME economic return series. This isolates the confound from any
   correlation with vault quality. Do the same for the event-time measure and show it does not
   move, which is the falsifiable claim behind lead 3.
3. **What the penalty actually down-weights.** From the anchor's own decision schedule, compute
   the realised multiplier `1 - 0.5 * c` each candidate would receive, and report the mean
   multiplier by TVL decile, by fresh-mark decile and by age. If the penalty's incidence tracks
   observation frequency more than return shape, it is a sparse-reporting filter wearing a
   consistency label.
4. **How often the penalty does not apply at all.** The share of (candidate, date) reads where
   concentration is NaN, split by age and freshness, and how many of those unscored vaults went on
   to win a basket slot. This quantifies the second defect.

**Adopts nothing.** Its conclusion constrains how NB28's and NB29's results may be read and is
carried into NB30.

### NB28 - backtest: the incumbent penalty under rule v4

**File**: `28-backtest-concentration-incumbent.ipynb`, `_build/build_28.py`.

**Runs.** The anchor; `build_family()` for the constraint-7 comparator; then
`run_and_record(f"calendar_lambda_{x}", "candidate", event_concentration_lambda=x)` for x in
{0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9}, with **0.5 pre-registered as the centre** because
it is the value NB09 ran. Window sensitivity at the centre: `event_window_days` in {90, 360} and
`min_fresh_observations` in {30, 90}. Admission alternative:
`require_concentration_scored=True` at the centre, reported beside the plateau, not part of it.

**Constraint 8** for the centre and both neighbours: mask each run's largest contributor and the
anchor's, and evaluate constraints 1, 2 and 4 masked-to-masked.

**The null.** A signal tilt that carries no information: multiply each candidate's signal by
`1 - lambda * u` where `u` is drawn per (vault, date) from the empirical distribution of realised
concentration values, so the marginal distribution of multipliers matches and only the ranking
information is destroyed. Ten seeds. **Assert the ten draws differ** and print the count of
distinct draw sequences, per rule 9. This separates "concentration ranks vaults usefully" from
"perturbing the ranking helps".

**Diagnostics.** From `CONCENTRATION_LOG`: the realised multiplier distribution, how often the
penalty changed the traded top six, the share of reads where it did not apply, and the
`top_vault_pnl_share` and `lovo_cagr_drop` for every run.

**Verdict.** ADOPT the centre only if it passes constraints 1-8 and the late period, both
neighbours pass, and it beats the ten nulls on CAGR and on ulcer. NB09's result predicts it fails
constraints 3 and 4, so the expected outcome is REJECT with the volatility and ulcer failures
quantified across lambda rather than at one point.

### NB29 - backtest: the polling-invariant penalty

**File**: `29-backtest-concentration-event-time.ipynb`, `_build/build_29.py`.

Same structure with `concentration_mode='event'`. Lambda sweep identical so the two are directly
comparable; `event_concentration_max_events` in {60, 90, 180} with 90 the pre-registered centre.
Constraint 8 on centre and neighbours. The same information-destroying null, ten seeds, with the
distinctness assertion.

**The head-to-head is the point** (cell to be written explicitly): the event-time centre against
the calendar centre at the same lambda, reporting CAGR, volatility, ulcer, beta, and the
difference in which vaults each penalises. The confound hypothesis predicts the event-time version
keeps the CAGR and beta gain while its volatility and ulcer land at or below the anchor's. **If it
keeps the return AND the roughness, the hypothesis is refuted** and the penalty is genuinely
selecting lumpy winners rather than sparsely-reported ones. Say which happened in the first
heading bullet, in those terms.

### NB30 - close-out

**File**: `30-backtest-concentration-closeout.ipynb`, `_build/build_30.py`.

Loads each manifest, re-runs every executed configuration in one kernel, re-derives every gate
rather than trusting the source notebooks, cross-checks each run's cycle Sharpe and CAGR against
its manifest literal at 1e-9, prints the combined `verdict_table_v4()` with complete failure sets,
`family_wise_joint()` over the complete executed family, the frontier and equity charts, NB27's
constraint on interpretation, and the frozen shadow specification. States whether constraint 7's
v4 median comparator discriminated where v3's maximum did not, and whether constraint 8 changed
any verdict that constraints 1-7 would have passed.

**Verdict.** ADOPT `<labels>` or NOTHING ADOPTED, one sentence per lead on what it settled and one
on what it could not.

## Order and cost

```
verify splices + anchor parity + NB09 reproduction      (~10 min)
NB27  research, anchor only plus archive analysis       (~10 min)
NB28  1 + 12 family + 9 lambda + 4 sensitivity + 10 null + 6 LOVO  (~15 min)
NB29  same shape                                        (~15 min)
NB30  every executed run in one kernel                  (~20 min)
```

Three notebooks at most. The leave-one-vault-out gate is the cost driver and is why the lambda
sweep is nine points rather than a finer grid.

**What I expect, stated before running.** NB27 finds a substantial confound, with concentration
correlating more strongly with fresh-mark count than with any return-shape measure. NB28 confirms
NB09: the incumbent penalty fails volatility and ulcer across most of the lambda range while
passing return, Sharpe, beta and deployment, and I expect it to fail constraint 8 as well. NB29 is
the real test, and I genuinely do not know the answer; the confound hypothesis is specific enough
that it can be wrong.

## Definition of done

- [ ] `_build/blocks_concentration.py` and `_build/harness_concentration.py` exist; the splice
      verification notebook reproduces `BASELINE` and NB09's 0.474299 / 2.380774.
- [ ] `build_27.py` ... `build_30.py` exist and build without assertion errors.
- [ ] Every notebook prints provenance hashes and passes `assert_anchor_parity()`.
- [ ] NB27: confound quantified, the re-sampling experiment run, the penalty's incidence by TVL
      and freshness reported, the NaN-exemption share measured.
- [ ] NB28 and NB29: lambda plateau, constraint 8 on centre and neighbours, the null with its
      distinctness assertion and printed count, the head-to-head comparison.
- [ ] NB30: manifests loaded, gates re-derived, cross-check asserted, shadow specification frozen.
- [ ] Each notebook independently reviewed after its run, findings verified against the cited
      cells before anything is applied.
- [ ] One commit per notebook. Nothing pushed to the PR unless asked.

## Review log

- **Draft 1**. Written 2026-09-14 from NB09's overlooked result, NB26's single-vault finding, and
  the same-day check that established the TVL-staleness confound.
