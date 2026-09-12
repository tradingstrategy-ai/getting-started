## 1. Do the heading's claims match the outputs?

The core frontier numbers match the executed output, but several interpretations do not.

- The seven placebo runs, their `drop_n` values, CAGR, cycle volatility, Sharpe, ulcer, and envelope membership in the summary table are supported by cell 23. In particular, it prints `vol_matched_drop_30` at CAGR `0.489942`, volatility `0.149229`, Sharpe `2.747391`, and ulcer `0.013843`; the anchor is `0.378971`, `0.154278`, `2.159792`, and `0.017964`.

- The claimed envelope `[drop_60, drop_50, drop_30]` and range `0.0769 to 0.1492` are supported by cell 23.

- The claim that `drop_30` has lower volatility and higher Sharpe than the anchor is supported. It formally dominates the anchor: `0.149229 < 0.154278` and `2.747391 > 2.159792`.

- The anchor’s constraint-7 failure is mechanically supported. Cell 23 shows its volatility lies above the envelope maximum; cell 27 reports the anchor as failed with `"placebo (not evalu..."`. This is a failure because the reference is NaN, not because `placebo_sharpe_at()` directly compares the anchor with `drop_30`.

- One sentence has the dominance direction backwards: cell 0 says `drop_30` “dominates every point at or below its own volatility”. It can only dominate points at or above its volatility. It does not dominate `drop_50` or `drop_60`.

- The approximate bar at volatility `0.149` is numerically right under the implemented interpolation: about `2.744`, hence a required Sharpe around `2.844` after the 0.10 margin. Cell 23 supplies the two bracketing points.

- The stronger claim that `drop_30` “reproduces NB12’s spike”, is known to fail leave-one-vault-out, and is noise rather than a result is not computed in this notebook. This notebook shows a sharp local maximum, but does not run a plateau analysis, leave-one-vault-out, or compare against NB12.

- The cash-overlay numbers and their position inside the envelope range are supported by cell 25: `target_vol_0.15` is Sharpe `1.848841`, invested `0.774092`; `target_vol_0.10` is Sharpe `1.533534`, invested `0.604519`.

- The claim that cash overlays are excluded “by deployment, not by Sharpe” is contradicted. Both also fail Sharpe non-inferiority: the floor is about `2.060`, versus `1.849` and `1.534`. Cell 27 additionally reports placebo failures. Deployment is a valid independent rejection reason, but not the sole one.

- Cell 24 says cash overlays are “not compared against constraint 7”; cell 27 contradicts this. It sends `cash_rows` through `verdict_table(..., frontier)`, which applies the placebo test to every row.

- The “fresh download”, “independent snapshot”, and NB16–NB18 rebuilding claims are not evidenced by this executed notebook. Cell 8 reports cached universe data and records no immutable data-version or price-history hash.

- The claim that chart variants were re-run only to obtain curves is supported by cell 30’s source, but there is no numerical determinism check between the first and chart runs.

## 2. Correctness of the code that produced the numbers

`build_placebo_frontier()` is correct on the alleged label-assignment issue. The previous reviewer was wrong.

It builds labelled rows first, uses keyed `.loc[...]` assignments for `drop_n`, then sorts complete rows by `cycle_vol`. Sorting does not detach a column from its row. Cell 23 is the executed check: volatility order is `60, 50, 40, 30, 20, 10, 0`, with matching `drop_n` values. No labels are misassigned in the frontier itself.

`_pareto_envelope()` has the correct direction for its stated rule, provided volatility values are distinct. Sorting volatility ascending and retaining only strictly higher Sharpe points correctly removes a point when a quieter-or-equal point already has equal-or-higher Sharpe. The resulting envelope is correct for this output.

There is a robustness bug for tied volatility: the function does not first collapse equal-volatility points to the highest-Sharpe one. With an unfortunate tie order, it can retain a lower-Sharpe point at the same volatility. That does not affect this run, whose displayed volatilities are distinct.

The larger conceptual issue is in the combination of `_pareto_envelope()` and `placebo_sharpe_at()`. The envelope-selection rule describes “best Sharpe achieved at or below” the candidate’s volatility, but linear interpolation does not do that between observed control points. At volatility `0.149000`, `drop_30` is at `0.149229`, so it is not a control achieved at or below `0.149000`; the best observed such control is `drop_50`, Sharpe `2.015`. The interpolated value near `2.744` is a pre-registered synthetic line, not an achieved at-or-below control result.

NaN handling is correct as implemented:

```python
ok = ref == ref and row["cycle_sharpe"] >= ref + PLACEBO_MARGIN
```

A NaN reference fails, and `failing_constraints_v2()` accurately calls this `"placebo (not evaluable)"`. The anchor therefore fails constraint 7 mechanically and correctly under the stated rule.

There is no apparent feature look-ahead in this backtest. `decide_trades()` calls `get_indicator_value()` without overriding its default `index=-1`; the framework documentation states that this reads “the previous time frame value”. Thus features are read from the bar before the decision date.

There is a real presentation/data-frame bug in cell 27. This line strips the label from placebo rows:

```python
all_rows = [anchor_panel] + [frontier.loc[l].drop("role") for l in frontier.index if l != "anchor"] + cash_rows
```

`frontier.loc[l]` has `label` in its index, not as a Series field. `verdict_table()` then does `.set_index("label")`, producing repeated `NaN` labels. The output visibly contains several `NaN` rows. Metrics and pass/fail calculations remain aligned with their rows, but the verdict table cannot identify which placebo row is which.

The CONTROL role is only display metadata; it does not prevent a row being evaluated by `passes_constraints_v2()`. The relevant existing framework-overwrite line, which caused the NB18 diagnostic issue, is:

```python
state.visualisation.add_calculations(timestamp, {'unallocatable_signals': alpha_model.get_unallocatable_signals()})
```

The shared evidence code correctly documents that this overwrites a same-timestamp diagnostic dictionary. It does not affect NB15’s frontier calculation, because NB15 does not enable the core/satellite replacement.

Finally, `vol_matched_drop_count` silently treats a missing inverse-volatility estimate as zero:

```python
inv_vol_by_id[pair_id] = ... else 0.0
```

and then drops the smallest values first. That makes an unavailable volatility estimate equivalent to maximal volatility. It may be harmless here, but without an audit of affected candidates it weakens the claim that this is a pure volatility-only placebo.

## 3. Statistical interpretation

The raw frontier and the rule-v2 mechanical verdicts are justified by the pre-registered implementation: the plan explicitly specifies linear interpolation, a 0.10 margin, and failure outside the envelope range.

However, the notebook should not overstate what this establishes.

- Around 125 two-day cycles, with an April polling-regime break and a fully in-sample window, are insufficient to infer that a single grid point is noise or structurally repeatable.
- NB15 stores cycle returns but does not run its paired bootstrap, confidence intervals, regime-specific placebo comparison, plateau test, or leave-one-vault-out test.
- The “recurring spike” classification rests materially on the external NB12 findings. NB15 itself establishes only a local discontinuity: `drop_30` Sharpe `2.747` versus `2.082` (`drop_20`) and `1.225` (`drop_40`).
- The inference that a candidate near volatility `0.149` faces an approximately `2.85` bar is correct under the pre-registered interpolated rule. It is not correct if described as the best observed placebo result at or below that volatility.
- The 0.10 placebo margin is a practical hurdle, not a significance test. The reported NB19 family-wise result is not computed or evidenced in this notebook.

## 4. What should be re-run or checked before these results are trusted

1. Fix and re-display cell 27’s verdict-table labels; preserve each placebo row’s `label`.
2. Add synthetic unit checks for row alignment, equal-volatility ties, endpoint NaNs, and the exact interpolation rule.
3. Decide whether constraint 7 is intentionally a linear synthetic frontier or an observed at-or-below control hurdle. If the latter, replace interpolation with a stepwise running maximum and re-evaluate all later candidates.
4. Log, per cycle, missing `inverse_vol` observations and identities of names removed by each `drop_n`; establish whether the placebo is genuinely volatility-only.
5. Re-run `drop_20`, `drop_30`, and `drop_40` on the same frozen snapshot with current-window plateau, leave-one-vault-out, and paired Sharpe-bootstrap outputs.
6. Record immutable raw-data/version hashes and compare chart reruns with their original panels, rather than only plotting their curves.
7. Correct the cash-overlay wording: they fail deployment, Sharpe non-inferiority, and placebo; either exclude them programmatically from constraint 7 or stop claiming they are not compared against it.

## 5. Verdict

RESULTS STAND WITH CAVEATS

The reported frontier values, ordering, Pareto subset, anchor NaN failure, and `drop_30` dominance over the anchor are correctly computed. The alleged `drop_n` label-misassignment is not present.

The notebook’s interpretation needs correction: the verdict table loses placebo labels; cash overlays are not rejected solely by deployment and are in fact tested against constraint 7; and the `~2.85` hurdle near 0.149 is an interpolated rule value, not an observed lower-volatility control result. The assertion that `drop_30` is recurring noise rests on earlier NB12 evidence, not this notebook’s computation.