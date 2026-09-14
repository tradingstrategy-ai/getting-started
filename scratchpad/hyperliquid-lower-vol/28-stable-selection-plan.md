# Stable-selection plan: screen the signal first, backtest only what predicts

- **Status**: DRAFT 1, awaiting Codex CLI review.
- **Rules**: [RESEARCH-RULES.md](RESEARCH-RULES.md). Objective: maximise cycle Sharpe by selecting
  stable vaults, not lucky and volatile ones, holding as many distinct vaults as the Sharpe allows.
- **Track**: `hyperliquid-lower-vol`, NB28-NB31. Supersedes
  [27-event-concentration-plan.md](27-event-concentration-plan.md), whose question survives here as
  one screened signal; its Codex review's blocking findings on nulls, event-time measures and
  re-sampling are applied below.
- **Anchor**: [02-better-format.ipynb](02-better-format.ipynb), a reference not a bar. `BASELINE`
  in `_build/harness_stability.py`, asserted in every notebook.
- **Every result is exploratory and in-sample.** ADOPT = admission to the shadow protocol.

## What the rejected experiments taught, and what this plan does about it

| Lesson | Source | Consequence here |
|---|---|---|
| Portfolio Sharpe cannot tell a mechanism from luck. The best Sharpe in either batch was one vault; a random removal of nine vaults ranks 7th of 57. | NB26, NB25 | Gate 5 of the rules: a signal must predict forward stability BEFORE it is backtested. This plan screens first. |
| Composite re-weightings that favour "consistency" pick vaults that do not lose because they do not earn. | NB09, NB16 | The mechanism is a PRE-FILTER that removes the unstable tail and then lets the incumbent's return ranking run, not a re-weighting. That is the structure of the one thing that worked. |
| The measured-only volatility drop has a small real return edge that survives leave-one-vault-out; its risk gains are generic. | NB26 | It is the special case `signal = inverse_vol`. It runs here as the baseline the other signals must beat. |
| No selection mechanism moves concentration. Vol barely moves either. | NB25, NB26 | The diversification floor is expected to bind on nothing; the tie-break at 0.25 Sharpe will decide most comparisons. Stated, not hidden. |
| Staleness is a size proxy and the calendar-day concentration measure confounds lumpiness with sparse reporting. | 2026-09-14 check, 27-plan review | Every forward target and every signal is computed on FRESH marks over the tradable pool only. A fresh-event concentration measure is defined properly and screened alongside the calendar one. |
| A pooled null changes more than ranking information; ten draws floor at p = 0.0909. | 27-plan review | Within-date permutation of the exact signal vector; distinctness asserted; "beats all ten" is a deterministic screen, never called significant. |

## The mechanism under test

`stability_prefilter`: at each decision, among the candidates that reach the ranking step, read
signal `S` at T-1, exclude the least-stable fraction `q` of them by `S`, then rank and size the
survivors exactly as the incumbent does. `q = 0` is the anchor. `S = inverse_vol` with a count
instead of a fraction is NB26's `measured_only` drop.

A fraction rather than a count, so the filter's strength does not depend on how many candidates
are unmeasured on a given date. Candidates whose `S` is NaN are kept by default (permissive), or
excluded under `stability_prefilter_strict = True` (strict); both are run.

## Rules for the executing agent

All of [RESEARCH-RULES.md](RESEARCH-RULES.md) §Standing method rules, plus:

1. Shared code goes in `_build/blocks_prefilter.py` and `_build/harness_rules.py`, built from
   the existing modules' replacement dicts without editing them. The prefilter block is inserted
   into the VALUE of `blocks_stability.py`'s "Rank by composite" replacement, ahead of the
   complementary-selection block, the way `blocks_drop_modes.py` widened the drop block.
2. `stability_prefilter_signal = ''` (off) is the default. The anchor must reproduce `BASELINE`
   with the splice present; NB26's `measured_8` must reproduce 0.409685 / 2.373768 under
   `signal='inverse_vol', count=8`. Both asserted before any notebook is built.
3. **Candidate membership at each decision date is read from the trading code's own log**, never
   reconstructed. `PREFILTER_LOG[timestamp]` records the candidate addresses, each one's signal
   value, its NaN status, and the excluded set. NB28's screen uses the same membership, taken
   from a `q = 0` run that logs but excludes nothing.
4. **Every null asserts its draws differ** and prints the count of distinct `(date, vault, value)`
   mappings across seeds, and asserts no draw is the identity permutation.
5. Signals are read at T-1 in the screen exactly as `decide_trades` reads them. A screen result
   computed at T is not comparable to a trading result and is not accepted.

## Gates

The nine gates in RESEARCH-RULES.md, evaluated in this order so an expensive gate is never run for
a candidate that has already failed a cheap one: 1 positive return; 5 signal predicts stability
(from NB28, once per signal); 2 single-vault survival; 3 held-book stability; 4 not luck; 8
diversification floor; 6 plateau; 7 sub-period sign; 9 null. Every Boolean is listed separately
on every row; an unexecuted gate is False.

The tie-break: within 0.25 Sharpe, the more diversified candidate. Expected to decide most
comparisons and stated as such in every heading.

## Shared additions

### `_build/blocks_prefilter.py`

Parameters, all defaulting to off:

```python
    stability_prefilter_signal = ''          # indicator name; '' disables the block entirely
    stability_prefilter_fraction = 0.0       # exclude this share of candidates by the signal
    stability_prefilter_count = 0            # OR this many; count wins if both set (NB26 parity)
    stability_prefilter_direction = 'low'    # 'low': smaller signal = less stable (e.g. inverse_vol)
                                             # 'high': larger signal = less stable (e.g. ulcer)
    stability_prefilter_strict = False       # exclude NaN-signal candidates rather than keep them
    stability_prefilter_null_seed = -1       # >= 0: permute the signal vector within the date
```

The block, placed after the vol-matched drop and before complementary selection:

```python
    prefilter_signal = str(getattr(parameters, 'stability_prefilter_signal', '') or '')
    if prefilter_signal:
        values = {}
        for _pid, _pair, _sig in candidates:
            v = indicators.get_indicator_value(prefilter_signal, pair=_pair)
            values[_pid] = float(v) if v is not None and v == v else float('nan')
        seed = int(getattr(parameters, 'stability_prefilter_null_seed', -1))
        if seed >= 0:
            # Within-date permutation of the EXACT signal vector across this date's candidates
            # (27-plan review, finding 6). Preserves the date-level distribution and the number
            # and location of NaNs; destroys only which vault carries which value.
            ids = sorted(values); vals = [values[i] for i in ids]
            rng = np.random.default_rng(seed * 1_000_003 + timestamp.toordinal())
            values = dict(zip(ids, rng.permutation(vals)))
        direction = str(getattr(parameters, 'stability_prefilter_direction', 'low'))
        strict = bool(getattr(parameters, 'stability_prefilter_strict', False))
        scored = [c for c in candidates if values[c[0]] == values[c[0]]]
        unscored = [c for c in candidates if values[c[0]] != values[c[0]]]
        ordered = sorted(scored, key=lambda c: (values[c[0]] if direction == 'low' else -values[c[0]], c[0]))
        count = int(getattr(parameters, 'stability_prefilter_count', 0) or 0)
        if count <= 0:
            count = int(round(float(getattr(parameters, 'stability_prefilter_fraction', 0.0)) * len(scored)))
        excluded = {c[0] for c in ordered[:count]}
        if strict:
            excluded |= {c[0] for c in unscored}
        PREFILTER_LOG[timestamp] = {...candidate addresses, values, nan flags, excluded, seed...}
        candidates = [c for c in candidates if c[0] not in excluded]
        if not candidates:
            return []
```

`np` must be available in the strategy cell; verify, and import it in the splice if not.

### `fresh_event_concentration` (new indicator, in the same module)

The 27-plan review's finding 2 applied. Event `j` spans `(t_{j-1}, t_j]` between consecutive
marks where the price CHANGED. Vault return is `log(P[t_j] / P[t_{j-1}])`; BTC return is the log
return compounded over the same interval; beta is estimated on the trailing
`event_concentration_max_events` matched interval pairs, excluding the current event, with at
least 30 pairs. Residual is vault minus beta times BTC. The statistic is the sum of the largest
five positive residuals over the trailing `event_concentration_max_events = 90` complete events,
divided by the sum of all positive residuals in the same window; NaN until exactly 90 complete
residual events exist. Report the calendar span covered by each window. This is the
**fresh-event measure**; it is NOT called polling-invariant, because merging economic-return
events across a gap changes the partition of the path. It is invariant to inserting duplicate
unchanged rows, which is the property that matters for the staleness confound, and that
invariance is asserted by a unit test in the verification notebook: duplicate every row of a
series three times and assert the value is unchanged at every original timestamp.

### `_build/harness_rules.py`

`passes_rules()` / `failing_rules()` implementing the nine gates with the ordering above;
`held_book_character(entry)` computing capital-weighted mean realised vol and mean
`residual_event_concentration` of the held vaults from `state.stats.positions`;
`lovo_gate(label)` running the masked candidate and returning Sharpe retention;
`diversification(entry)` returning the five floor measures; `within_date_null_ok(centre, nulls)`;
`verdict_table_rules()`; `tie_break(a, b)`.

## Experiment track

### NB28 - research: which stability signals predict forward stability?

**File**: `28-research-stability-signal-screen.ipynb`. Verdict: DIAGNOSTIC. Gate 5 for everything
downstream.

**Membership and alignment.** Run the anchor and one `q = 0` prefilter run (`signal='inverse_vol',
fraction=0.0`) whose `PREFILTER_LOG` records every candidate at every decision date. The screen is
over exactly those (date, candidate) pairs, 126 dates, roughly 148 candidates each. Signals are
read from the cached indicators at T-1.

**Signals screened**, each with its pre-registered "less stable" direction:

| signal | window | less stable when |
|---|---|---|
| `inverse_vol` | 90 d | low |
| `downside_deviation_90` | 90 d | high |
| `ulcer_index_180` | 180 d | high |
| `drawdown_recovery_days` | 180 d | high |
| `residual_event_concentration` (calendar) | 180 d | high |
| `fresh_event_concentration` (new) | 90 events | high |
| `positive_window_share` | 30/180 d | low |
| `gain_to_pain_score` | 180 d | low |
| `min_window_sortino` | 30-360 d | low |
| `sortino_score` | 45 d | low |
| `sortino_shrunk_score` | 90 events | low |
| `btc_beta` (absolute) | 90 d | high |
| `fresh_observation_count` | 90 d | low - a CONTROL: the staleness proxy itself |

**Forward targets** over `(T, T + 30 d]`, on fresh marks only, per candidate: realised volatility
of fresh log returns; downside deviation; maximum drawdown; fresh-event top-five share as defined
above but over the forward window; and mean fresh log return, the "not dead" check.

**Statistic.** For each signal and each target, at each date, the Spearman rank correlation
across that date's candidates, signed so that positive means "the signal's stable end had the
more stable outcome". The reported figure is the mean across dates, with a 95% interval from a
block bootstrap over dates (block 10) AND a separate interval from resampling vaults with
replacement, both printed; the wider governs. Minimum 30 candidates with both signal and target
on a date, or the date is skipped and the skip counted.

**Pass rule for gate 5**, pre-registered: a signal passes if its mean correlation with at least
three of the four forward stability targets is positive with the governing interval excluding
zero, AND its correlation with forward mean return is not negative with the interval excluding
zero. The second clause is what rejects the NB09 pattern of picking vaults that do not lose
because they do not earn.

**Also reported per signal:** rank autocorrelation of the signal itself across consecutive
dates (a stable-vault signal that reshuffles every cycle is measuring noise); its Spearman
correlation with `fresh_observation_count` and with median TVL (the confound); its NaN rate on
the tradable pool; and the calendar span of the fresh-event window.

**Output.** A table of all thirteen signals with pass/fail on gate 5 and every statistic, written
to `_build/manifest_28.json`, which NB29 reads to decide what to run. The heading names the
passing signals and says in plain words whether the calendar and fresh-event concentration
measures differ in what they predict, which is the 27-plan's question answered without a
backtest.

### NB29 - backtest: the prefilter, one signal at a time

**File**: `29-backtest-stability-prefilter.ipynb`.

For each signal that passed gate 5 in NB28, in the order of its mean stability correlation:
`stability_prefilter_fraction` in {0.10, 0.20, 0.30, 0.40, 0.50}, **0.30 the pre-registered
centre**, permissive admission. Plus the strict variant at the centre. If only `inverse_vol`
passed, run it alone and say so in the first bullet. If nothing passed, this notebook runs the
anchor and the `inverse_vol` sweep as a reference only, verdict DIAGNOSTIC, and NB30 is skipped.

Per signal: gates in the stated order; leave-one-vault-out on the centre and both neighbours
before the plateau is evaluated; the within-date permutation null, ten seeds, at the centre;
`held_book_character`, `diversification`, `luck_ratio`, `top5_gross_share` on every row.

**Verdict per signal.** ADOPT the centre only if all nine gates hold. Across signals with a
passing centre, apply the tie-break. REJECT otherwise, with the complete failure set.

### NB30 - backtest: combining passing signals

**File**: `30-backtest-stability-prefilter-combined.ipynb`. Runs only if at least two signals had
a passing centre in NB29; otherwise the file is not created and NB31 says why.

Rank-sum of the passing signals (each ranked in its stable direction, ranks summed, exclude the
worst fraction `q`), same sweep, same gates, same null. The question is whether two independently
predictive stability signals beat either alone, at the same `q`, by more than the 0.25 tie-break
margin. Expected answer: no, and the tie-break decides.

### NB31 - close-out

**File**: `31-backtest-stability-closeout.ipynb`. Re-runs every executed configuration in one
kernel, re-derives every gate from `harness_rules.py`, cross-checks against manifests at 1e-9,
`family_wise_joint()` over the complete executed family, frontier and equity charts, the
held-book character and diversification tables for every run, and the frozen shadow
specification. States which gate rejected most candidates, whether the tie-break ever decided
anything, and whether any signal other than `inverse_vol` predicted forward stability at all.

## Order and cost

```
verify splices, parity, measured_8 reproduction, fresh-event duplicate-row test   (~10 min)
NB28  anchor + one logging run + archive analysis over 13 signals                 (~15 min)
NB29  per passing signal: 5 + 1 + 3 LOVO + 10 null = 19 runs, ~7 min each          (~7 min x signals)
NB30  conditional, same shape                                                      (~7 min)
NB31  every executed run                                                           (~20 min)
```

**What I expect, stated before running.** `inverse_vol` passes gate 5 easily, because volatility
clusters; that is the sizing rule's premise and not news. `fresh_observation_count` fails gate 5
on the tradable pool, which is the 2026-09-14 finding restated. The calendar concentration
measure correlates with `fresh_observation_count` and the fresh-event one does not, which settles
the 27-plan's question. Of the remaining signals I expect two or three to pass gate 5 and none of
them to beat `inverse_vol` in NB29 by more than 0.25 Sharpe, so the tie-break decides and the
plan's most likely verdict is a small, real, diversification-neutral improvement that the rules
correctly refuse to call more than that.

## Definition of done

- [ ] `_build/blocks_prefilter.py`, `_build/harness_rules.py`; verification notebook reproduces
      `BASELINE` and `measured_8`, and passes the duplicate-row invariance test.
- [ ] `build_28.py` .. `build_31.py` exist; every notebook prints provenance and asserts parity.
- [ ] NB28: thirteen signals screened with both intervals, pass/fail on gate 5, manifest written.
- [ ] NB29: every passing signal swept, nine gates in order, null distinctness asserted.
- [ ] NB30 run or its absence explained in NB31.
- [ ] NB31: gates re-derived, cross-check at 1e-9, shadow specification frozen.
- [ ] Each notebook independently reviewed; findings verified before applied.
- [ ] One commit per notebook. Nothing posted to the PR unless asked.

## Review log

- **Draft 1**, 2026-09-14. Written under the new rules from NB09, NB16, NB25, NB26 and the
  27-plan's Codex review, whose blocking findings 1, 2, 3, 6 and 7 are applied above.
