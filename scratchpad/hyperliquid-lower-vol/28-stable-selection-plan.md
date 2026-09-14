# Stable-selection plan: screen the signal first, and admit nothing from this window

- **Status**: DRAFT 2, after Codex CLI review
  ([28-stable-selection-plan-codex-review.md](28-stable-selection-plan-codex-review.md),
  `gpt-5.6-sol`, 11 blocking and 13 material findings). **Blocked on one operator input**, marked
  OPERATOR INPUT REQUIRED below; everything else is resolved.
- **Rules**: [RESEARCH-RULES.md](RESEARCH-RULES.md). Objective: maximise cycle Sharpe by selecting
  stable vaults, not lucky and volatile ones, holding as many distinct vaults as the Sharpe allows.
- **Track**: `hyperliquid-lower-vol`, NB28-NB31. Supersedes
  [27-event-concentration-plan.md](27-event-concentration-plan.md).
- **Anchor**: [02-better-format.ipynb](02-better-format.ipynb), a reference not a bar.

## The change that matters most in this draft

**Nothing in this plan can be adopted, and ADOPT is removed from its vocabulary.**

The review's blocking finding 4 is correct and cannot be engineered around on this window. The
screen chooses signals using 30-day forward returns; the backtest then judges portfolios built
from those signals on returns that overlap the same 30-day windows. Procedural ordering does not
make the screen out-of-sample. The data would select the mechanism, select the surviving variants
and score the survivor, all on 126 decisions whose minimum detectable Sharpe difference is about
2.50.

A purge-and-split would leave roughly 35 decisions to evaluate on, which cannot resolve anything.
So the honest structure is the third option the review offers: **NB28-NB31 are hypothesis
generation.** Their deliverable is a ranked shortlist and a frozen prospective specification, not
an admission. NB30 replaces the combined mechanism (undefined, and a third selection layer) with
a cross-fitted evaluation, which is the only way this window yields an out-of-fold number at all,
and even that is reported as a diagnostic.

**Verdict vocabulary**: SHORTLIST (carried to the prospective shadow) / REJECT / DIAGNOSTIC.
There is no ADOPT. `RESEARCH-RULES.md` gate language is retained for scoring, and a candidate
meeting every gate is SHORTLISTED, not adopted.

## OPERATOR INPUT REQUIRED

Gate 5's return clause needs a **non-inferiority margin `delta`**, in annualised percentage
points, for the contrast between the forward return of the vaults a signal calls stable and those
it calls unstable. The review is right that "the interval does not exclude zero" is a
failure-to-reject, not a guarantee: a materially negative but noisy association would pass it.

The rule becomes: the lower simultaneous bound on that contrast must exceed `-delta`.

`delta = 0` demands the stable set be no worse in return, which given NB09's and NB16's results
would reject almost everything. Large `delta` makes the clause vacuous. **Recommendation: 5
annualised percentage points**, which says a signal may pick vaults earning up to 5 points less
per year if it demonstrably picks more stable ones, and which would have rejected NB09's
consistency legs (15.0%, 24.3% and 9.2% CAGR against 37.9%) on magnitude rather than on noise.
The executing agent must not invent this number.

## What the rejected experiments taught, and what this plan does about it

| Lesson | Source | Consequence here |
|---|---|---|
| Portfolio Sharpe cannot tell a mechanism from luck. The best Sharpe in either batch was one vault; a random removal of nine vaults ranks 7th of 57. | NB25, NB26 | Signals are screened for forward predictiveness before any backtest, and nothing is adoptable from this window. |
| Composite re-weightings favouring "consistency" pick vaults that do not lose because they do not earn. | NB09, NB16 | The return clause is a non-inferiority test with a margin, not a failure-to-reject. |
| The measured-only volatility drop has a small real return edge surviving leave-one-vault-out. | NB26 | It is the `inverse_vol` special case and the reference every other signal is compared against. |
| No selection mechanism moves concentration; volatility barely moves either. | NB25, NB26 | The diversification floor binds on nothing, and the 0.25 tie-break is an operator indifference band, not a resolution claim. |
| Staleness is a size proxy; the calendar concentration measure confounds lumpiness with sparse reporting. | 2026-09-14 check | Both concentration measures are screened, and their difference is tested by a paired contrast, not by two separate intervals. |
| A null can be degenerate in ways a naive distinctness check misses. | NB26 | Effectiveness is asserted on excluded sets, baskets AND cycle-return series, not on the value map. |

## The mechanism under test

`stability_prefilter`: at each decision, among candidates reaching the ranking step, read signal
`S` at T-1, exclude the least-stable fraction `q` **of the candidates for which `S` is finite**,
then rank and size survivors exactly as the incumbent does. `q = 0` is the anchor. `S =
inverse_vol` with a count is NB26's `measured_only` drop.

The review is right that equal `q` is not equal filtering strength across signals: a signal with a
higher NaN rate filters a smaller share of the whole pool. Every run therefore reports, per date,
the measured count, the NaN count, the excluded count, the **excluded share of all candidates**
and the remaining count. Comparisons across signals are made at matched *realised* exclusion
share, never at matched `q`.

Candidates with NaN `S` are kept (permissive) or excluded (`stability_prefilter_strict`). **Strict
runs are DIAGNOSTIC only** and cannot inherit a permissive signal's gate-5 pass, because gate 5 is
a complete-case statistic and missingness-as-exclusion is precisely the behaviour it does not test.

## Rules for the executing agent

All of [RESEARCH-RULES.md](RESEARCH-RULES.md) §Standing method rules, plus:

1. Shared code in `_build/blocks_prefilter.py` and `_build/harness_rules.py`, built from existing
   modules' replacement dicts without editing them.
2. `stability_prefilter_signal = ''` is the default and disables the block. The anchor must
   reproduce `BASELINE` with the splice present, and NB26's `measured_8` must reproduce
   0.409685 / 2.373768. Both asserted before any notebook is built.
3. **`run_and_record()` must clear and snapshot `PREFILTER_LOG`** alongside the existing logs, or
   candidate membership leaks between runs. The existing helper does not know about it.
4. **Signals keep their exact cached definitions** and are only read at T-1. Only the forward
   targets use the new fresh-return construction. The signal table states each signal's time base.
5. Candidate membership comes from `PREFILTER_LOG`, never reconstructed.
6. Replace `v == v` with `np.isfinite(v)` everywhere; the fail-closed rule excludes infinities.

## Gates

The nine gates of `RESEARCH-RULES.md`, scored in this order so an expensive gate never runs for a
candidate that failed a cheap one. Every Boolean listed separately; unexecuted means False.
Meeting all nine yields SHORTLIST, not ADOPT.

Two corrections the review forced:

- **Gate 2** gates on Sharpe retention and is now calibrated on Sharpe, not CAGR. Measured under
  leave-one-vault-out: the anchor retains 1.781367/2.159792 = **0.825**, `measured_8` retains
  2.040695/2.373768 = **0.860**, and the `drop_30` spike retains 1.889823/2.747391 = **0.688**.
  The 70% bar therefore sits above the spike and below both legitimate cases, as intended.
- **Gate 3 and gate 8** are defined exactly below, because "capital-weighted" and "more
  diversified" were both unimplementable as written.

### Gate 3, held-book stability, defined

One observation per decision date. Weights are each vault's share of total equity at that
timestamp from `state.stats.positions` over `state.stats.portfolio` equity, normalised across
finite holdings on that date. Each holding is joined to its **T-1 cached indicator value** for
realised volatility (`1/inverse_vol`) and for `residual_event_concentration`. A holding whose
indicator is NaN is dropped from that date's weighted mean and the dropped weight share is
reported; a date where more than 25% of weight is dropped is excluded and counted. The gate
compares the mean across dates against the anchor's, computed identically.

### Gate 8 and the tie-break, defined

`top_vault_pnl_share` is address-aggregated total P&L of the largest contributing address divided
by the sum of **positive** address-level total P&L. "More diversified" is **Pareto dominance**
across the five measures: no worse on all five and strictly better on at least one. If neither
dominates, the comparison is declared unresolved and both are shortlisted.

The 0.25 Sharpe tie-break is an **operator indifference band**, a decision policy. It is not a
statistical resolution claim and the plan does not describe it as one. `RESEARCH-RULES.md` is
corrected on this point in the same commit.

## Shared additions

### `_build/blocks_prefilter.py`

```python
    stability_prefilter_signal = ''          # indicator name; '' disables the block
    stability_prefilter_fraction = 0.0       # share of FINITE-signal candidates to exclude
    stability_prefilter_count = 0            # OR this many; count wins when > 0 (NB26 parity)
    stability_prefilter_direction = 'low'    # 'low' = smaller signal means less stable
    stability_prefilter_strict = False       # exclude NaN-signal candidates (DIAGNOSTIC only)
    stability_prefilter_null_seed = -1       # >= 0: permute FINITE values within the date
```

The null, corrected per blocking finding 7 — NaNs stay with their original vault so only finite
ranking is destroyed:

```python
        seed = int(getattr(parameters, 'stability_prefilter_null_seed', -1))
        if seed >= 0:
            finite_ids = sorted(i for i in values if np.isfinite(values[i]))
            finite_vals = [values[i] for i in finite_ids]
            rng = np.random.default_rng(seed * 1_000_003 + timestamp.toordinal())
            values = dict(values)
            values.update(zip(finite_ids, rng.permutation(finite_vals)))
```

`PREFILTER_LOG[timestamp]` records candidate addresses, each signal value, its finite flag, the
excluded set, the measured/NaN/excluded/remaining counts and the seed.

### `fresh_event_concentration`

Event `j` spans `(t_{j-1}, t_j]` between consecutive marks where the price changed. Vault return
is `log(P[t_j]/P[t_{j-1}])`; BTC return is the log return compounded over the same interval.
**Each residual uses a rolling beta estimated solely from matched events strictly preceding that
event**, minimum 30 matched pairs — one causal beta per event, not one evaluation-time beta
applied retrospectively. The statistic is the sum of the five largest positive residuals over the
latest 90 finite residual events, divided by the sum of all positive residuals in that window;
NaN until 90 finite residual events exist, which requires at least 120 raw events. Each window's
calendar span is reported.

It is **not** polling-invariant and is not described as such. Its claim is invariance to inserting
unchanged marks, verified by a test that inserts unchanged marks **at new intermediate
timestamps** while preserving every original price-change endpoint and the BTC path, then asserts
equality at original timestamps, equality of the finite/NaN mask, and equality of reported spans.

### `_build/harness_rules.py`

`passes_rules()` / `failing_rules()`; `held_book_character()` and `diversification()` as defined
above; `lovo_gate()` returning Sharpe retention; `joint_cluster_bootstrap()`; `simultaneous_ci()`;
`null_effectiveness()`; `verdict_table_rules()`; `tie_break()` implementing Pareto dominance.

## Experiment track

### NB28 - research: which stability signals predict forward stability?

**File**: `28-research-stability-signal-screen.ipynb`. Verdict DIAGNOSTIC.

**Eligible dates.** Only decisions with `T + 30 days <= last_available_timestamp`, which excludes
roughly the final fifteen decisions. The notebook prints the eligible count and never claims 126.

**Forward targets**, all on a common 30-calendar-day horizon so they are not frequency-dependent
(blocking 1, material 14, material 15). Returns are built from the carried NAV at T, so no event
straddles T. Per candidate over `(T, T+30d]`:

- **Forward volatility**: `sqrt(sum of squared fresh interval log returns * 365/30)`.
- **Forward downside variation**: the same over negative intervals only.
- **Forward fresh-event top-five share**: as the indicator, over the forward window. NaN unless at
  least `min_positive_events = 8` positive residual events exist, so it cannot degenerate to
  exactly 1.0.
- **Forward 30-day cumulative log-NAV return**: the return clause's target.
- Maximum drawdown is reported as a DIAGNOSTIC only, not a gate target (blocking 5).

Every target has explicit missing-reason codes: insufficient events, zero denominator,
non-finite. Counts per reason are printed.

**Signals screened.** Each keeps its cached definition; the table names its time base.

| signal | time base | less stable when |
|---|---|---|
| `inverse_vol` | 90 calendar rows | low |
| `downside_deviation_90` | 90 calendar rows | high |
| `ulcer_index_180` | 180 calendar rows | high |
| `drawdown_recovery_days` | 180 calendar rows | high |
| `residual_event_concentration` | 180 calendar rows | high |
| `fresh_event_concentration` | 90 fresh events | high |
| `positive_window_share` | 30/180 calendar rows | low |
| `gain_to_pain_score` | 180 calendar rows | high |
| `min_window_sortino` | 30-360 calendar rows | low |
| `sortino_score` | 45 calendar rows | low |
| `sortino_shrunk_score` | 90 fresh events | low |
| `btc_beta` (absolute) | 90 calendar rows | high |
| `fresh_observation_count` | 90 calendar rows | low - CONTROL, the staleness proxy |

**Inference** (blocking 2 and 3). One joint procedure resamples **date blocks of at least 15
decisions (circular moving blocks) and vault clusters together**, recomputing the whole nonlinear
statistic on each draw, with **the same resamples reused across every signal and target**.
Simultaneous one-sided max-T intervals control the 39 stability hypotheses and the 13 return
hypotheses as two pre-registered families. Any p-value uses the add-one correction. Unadjusted
intervals may be printed descriptively and labelled as such. Percentile construction; fail closed
on constant input or non-finite Spearman. Minimum 40 usable dates per signal-target or that pair
is not evaluated.

**Statistic.** The estimand is stated explicitly as the equal-weight mean association on a typical
decision date: per date, Spearman across that date's candidates, signed so positive means the
signal's stable end had the more stable outcome, averaged over eligible dates.

**Tail-aligned diagnostic** (material 12), required alongside: at each date compare the forward
target ranks of the exact fraction that WOULD be excluded at `q = 0.30` against the retained set,
and average that contrast under the same clustered inference. The Spearman satisfies the rule; the
tail contrast tests the mechanism.

**Gate 5 pass rule**, pre-registered, matching `RESEARCH-RULES.md` exactly (blocking 5 and 6):

> All THREE of forward volatility, forward downside variation and forward fresh-event top-five
> share show a positive association with the signal's stable end, with the simultaneous lower
> bound above zero; AND the simultaneous lower bound on the stable-versus-unstable forward 30-day
> return contrast exceeds `-delta`.

**Also reported**: rank persistence across consecutive dates on the common candidate intersection,
as a diagnostic, not a filter; Spearman against `fresh_observation_count` and median TVL; NaN rate
on the tradable pool; fresh-event window spans.

**The calendar-versus-fresh question** (material 21) is answered by a **paired difference** of the
two measures' correlations on the same candidate-date sample with common resamples and the same
multiplicity control. The heading says their predictive patterns differed by such-and-such, with
an interval. It does not say "settles".

### NB29 - backtest: the prefilter, one signal at a time

**File**: `29-backtest-stability-prefilter.ipynb`. Verdict SHORTLIST / REJECT.

For each gate-5 passer, `stability_prefilter_fraction` in {0.10, 0.20, 0.30, 0.40, 0.50}, centre
0.30, permissive. Strict at the centre, DIAGNOSTIC. `inverse_vol` always runs as the reference
even if it fails gate 5, labelled as such.

Gates in order; leave-one-vault-out on centre and both neighbours before the plateau is scored;
the corrected within-date permutation null, ten seeds, at the centre.

**Null effectiveness** (blocking 8). Print distinct counts of: signal mappings, excluded-set
histories, realised basket histories, and cycle-return series. **Gate 9 is False if fewer than ten
distinct cycle-return series exist.** The comparison is the strict `centre_sharpe >
max(null_sharpes)` and is never called significant.

**Inertness check** (material 19), every run: share of decisions where the prefilter changed the
selected six, how many excluded names would otherwise have been selected, basket Jaccard against
the anchor, and whether the realised equity path is distinct from the anchor's. A run that changes
nothing is reported as inert regardless of its metrics.

### NB30 - diagnostic: cross-fitted evaluation of the leading signal

**File**: `30-backtest-stability-crossfit.ipynb`. Verdict DIAGNOSTIC. Replaces the combined
mechanism, which was undefined and added a third selection layer.

Five contiguous folds over the decision schedule. For each fold, gate 5 is re-run using only dates
outside that fold **and outside a 30-day purge either side**, the leading signal is re-chosen from
that reduced screen, and the prefilter runs with the fold's own choice active only during that
fold. Stitching the five out-of-fold segments gives one equity path in which no segment was
scored by a screen that saw it.

Report: whether the same signal wins in all five folds; the stitched out-of-fold Sharpe and CAGR
against the anchor's over the same dates; and how often the fold-selected signal differs. **If the
leading signal is not stable across folds, the screen is fitting noise and the plan says so.**

This is a diagnostic because folds share vaults and market regime, and the purge cannot remove
cross-sectional contamination. It is the best this window supports, not a clean out-of-sample test.

### NB31 - close-out and the prospective specification

**File**: `31-backtest-stability-closeout.ipynb`.

Re-runs every executed configuration in one kernel, re-derives every gate, cross-checks manifests
at 1e-9, and prints the combined verdict table.

`family_wise_joint()` membership (material 24) is **exactly**: every configuration evaluated as
potentially shortlistable, including failed centres and neighbours; excluding the anchor,
reference-only runs, leave-one-vault-out runs and null runs. The notebook states that this test
cannot correct for the thirteen screened alternatives upstream.

**The deliverable** is the frozen prospective specification: which signal, which `q`, the strict
or permissive variant, the fixed comparator, the monitoring horizon, the stopping rule, and the
literal override dictionary. Fixed before new data arrive. Plus a sentence per signal on what the
screen found and one on what it could not.

## Order and cost

Each backtest is about 20 seconds on a warm indicator cache; each notebook costs about 3 minutes
of startup. Corrected from Draft 1, which the review read as 7 minutes per run.

```
verify splices, parity, measured_8 reproduction, inserted-mark invariance test   (~10 min)
NB28  anchor + one logging run + screen over 13 signals with joint bootstrap      (~25 min)
NB29  per passing signal: 19 runs ~ 7 min compute + 3 min startup                 (~10 min x signals)
NB30  5 folds x (screen + 1 run)                                                  (~20 min)
NB31  every executed run                                                          (~25 min)
```

**What I expect.** `inverse_vol` passes gate 5; that is the sizing rule's premise, not news.
`fresh_observation_count` fails on the tradable pool, restating the 2026-09-14 finding. The two
concentration measures differ in what they predict, with an interval. Two or three other signals
pass, none beats `inverse_vol` by more than the indifference band, several prefilter runs are
inert, and NB30 finds the leading signal is not stable across folds. The most likely honest
outcome is a shortlist of one or two signals for a prospective shadow and no claim stronger than
that.

## Definition of done

- [ ] OPERATOR INPUT REQUIRED resolved: `delta` supplied.
- [ ] `_build/blocks_prefilter.py`, `_build/harness_rules.py`; verification reproduces `BASELINE`
      and `measured_8` and passes the inserted-mark invariance test.
- [ ] `run_and_record()` clears and snapshots `PREFILTER_LOG`.
- [ ] NB28: eligible dates printed, targets on a common 30-day horizon with missing-reason counts,
      one joint two-way cluster bootstrap with shared resamples, simultaneous intervals over two
      pre-registered families, tail-aligned contrast, paired calendar-versus-fresh difference.
- [ ] NB29: gates in order, null effectiveness on cycle-return series, inertness check every run.
- [ ] NB30: five folds with purge, fold-stability of the leading signal reported.
- [ ] NB31: explicit family membership, frozen prospective specification, no ADOPT anywhere.
- [ ] Each notebook independently reviewed; findings verified against cited cells before applied.

## Review log

- **Draft 1**, 2026-09-14. Written under the new rules from NB09, NB16, NB25, NB26 and the
  27-plan's review.
- **Codex CLI review** (`gpt-5.6-sol`): 11 blocking, 13 material, 4 minor. Verdict "not executable
  as an adoption protocol as written".
- **Draft 2**, 2026-09-14. All 11 blocking findings applied. The largest change is structural:
  finding 4's double-selection problem cannot be engineered around on 126 decisions, so ADOPT is
  removed and the plan is hypothesis generation producing a frozen prospective specification.
  NB30's combined mechanism is replaced by a cross-fitted diagnostic. Also applied: forward
  targets restricted to complete windows on a common 30-day horizon with explicit missing reasons;
  one joint two-way cluster bootstrap with shared resamples and simultaneous intervals over two
  pre-registered families; the pass rule aligned to the three targets the rules name; the return
  clause made a non-inferiority test pending `delta`; the null permuting only finite values with
  NaNs left attached; null effectiveness asserted on cycle-return series; signals keeping their
  cached definitions with time bases stated; gate 3, gate 8 and the tie-break given exact
  definitions; gate 2 recalibrated on real Sharpe retention (0.825 anchor, 0.860 `measured_8`,
  0.688 the spike); strict runs made diagnostic-only; the tail-aligned contrast added; the
  calendar-versus-fresh comparison made a paired difference; inertness checks added; 0.25
  redescribed as an operator indifference band; `luck_ratio` described as five cycles; family
  membership specified; and the cost arithmetic corrected.
