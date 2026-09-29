# NB25 independent review

## Findings

### 1. Constraint 7 chart does not plot the actual constraint

- **Severity:** material
- **Cells:** 35, 36
- **What is wrong:** The chart joins the raw drop-family points with a polyline and says a candidate must be 0.10 Sharpe above “the line”. `placebo_ref_observed()` instead uses the maximum Sharpe among all controls no noisier than the candidate: a non-decreasing step function, not the raw polyline.
- **Why:** The plotted line falls at several points (for example around `drop_55`, `drop_45`, and `drop_40`), whereas the actual reference cannot fall as volatility increases. It also does not plot the required `+0.10` margin.
- **Concrete fix:** Plot the cumulative maximum of family Sharpe sorted by volatility as a horizontal-step line, plus a dashed `reference + 0.10` line. Add each non-family row’s actual reference label/value to `comparison` and the table.

### 2. “Its comparator is the `drop_30` spike” is false for 11 rows

- **Severity:** material
- **Cells:** 0, 24, 26, 38
- **What is wrong:** The notebook says constraint 7’s comparator is `drop_30` for every row. It is not.
- **Why:** `placebo_ref_observed()` depends on each row’s volatility. From the displayed panel, `drop_30` is the reference for 25 of 36 rows. The other 11 use:
  - `drop_35` for `drop_35`, `swap__t_cap_4`, `swap__cagr_weight_0.7`, and `swap__min_events_30`;
  - `drop_50` for `drop_40`, `drop_45`, `drop_50`, `swap__cagr_weight_0.5`, and `swap__prior_90`;
  - `drop_60` for `drop_55` and `drop_60`.
  
  Literal self-comparison occurs for `drop_30`, `drop_35`, `drop_50`, and `drop_60`, not every drop-family member. The mechanical “0 of 36” result is true, but it combines 23 applicable mechanism rows with an anchor and 12 comparator-family rows for which the rule is intentionally inapplicable.
- **Concrete fix:** Mark the anchor and drop family’s constraint-7 status as `N/A`, show `passes_1_to_6` for the latter, and report the constraint-7 result separately for the 23 additional-mechanism rows. If retaining the mechanical all-row column, label it explicitly as such and show the actual control label and Sharpe reference per row.

### 3. The “complete failure inventory per family” is incomplete

- **Severity:** material
- **Cell:** 0
- **What is wrong:** The Summary calls its list “the complete failure inventory per family”, but omits the NB22 window-sensitivity family and NB23 policy family.
- **Why:** Cell 38 has six groups, not three: anchor, drop, joint downside, joint-downside window sensitivity, Sortino swap, and policy. The omitted groups have substantive failures:
  - window sensitivity: all six non-deployment constraints fail, each x4;
  - policy: CAGR, Sharpe, ulcer, beta, and observed control fail, each x1.
- **Concrete fix:** Either include all six groups, or rename the sentence to “core mechanism sweeps” and explicitly state that the sensitivity and policy rows are reported separately in cell 38.

### 4. The failure-string parser is correct, but the qualitative headline is selective

- **Severity:** minor — correct but poorly worded, not a code error
- **Cells:** 0, 26, 38
- **What is wrong:** The counter in cell 38 is robust for the current failure vocabulary: none of the strings emitted by `failing_constraints_v3()` contains an internal comma. The displayed counts also match the full cell-26 failures: drop ulcer x7, Sharpe x5, beta x4, CAGR x4, observed control x12; joint downside all six relevant constraints x7; Sortino swap CAGR/Sharpe/ulcer/control x11, beta x4, volatility x2.
- **Why:** The headline’s numbers are accurate, but “three families fail in qualitatively different ways” foregrounds selected failures while omitting the drop family’s CAGR failures and the universal observed-control failure. The latter is partly artificial, but that should be stated alongside the categorisation.
- **Concrete fix:** Replace the claim with: “The core mechanisms differ primarily in return retention: four drop settings fail the CAGR floor, versus all seven joint-downside and all eleven Sortino-swap settings. The complete failure inventory, including the uniformly applied observed-control column, is in cell 38.”

### 5. The late-period conclusion over-interprets a hidden composite Boolean

- **Severity:** material
- **Cells:** 0, 26, 38
- **What is wrong:** “Only the simplest mechanism survives the late period” and “degraded more gracefully” treat `late_ok` as a standalone family comparison.
- **Why:** `late_ok` is the conjunction of positive late CAGR and late ulcer strictly below the anchor’s. The anchor necessarily fails its own ulcer comparison, and the two component metrics and margins are not displayed. Thus the 8/12, 0/11, and 4/11 counts are correctly counted flags, but do not by themselves establish relative graceful degradation. They can also be sensitive to tiny strict-threshold margins.
- **Concrete fix:** Display `late_cagr`, `late_ulcer`, and the ulcer difference from the anchor. Replace the heading with: “On the pre-registered composite late-period eligibility flag, 8/12 drop rows are true, versus 0/11 joint-downside and 4/11 Sortino-swap rows. This is an eligibility component, not a standalone measure of degradation.”

### 6. “Beat the anchor on both axes” is numerically correct but materially overstated for two rows

- **Severity:** material
- **Cells:** 0, 31, 34
- **What is wrong:** The strict filter correctly returns `drop_10`, `drop_15`, `drop_30`, and `drop_35`. However, the prose groups all four as meaningful two-axis improvements despite the notebook’s own reporting-behaviour caveat.
- **Why:** `drop_10` is effectively tied with the anchor at the displayed precision. `drop_15` improves ulcer from 1.7964% to 1.7905%, roughly a 0.33% relative change—well below the 4.4% anchor-only sensitivity cited in cell 31. `drop_30` and `drop_35` have materially larger ulcer reductions. The filter establishes strict arithmetic ordering, not four equally interpretable improvements.
- **Concrete fix:** Rename the output to “Rows meeting the strict numerical two-axis predicate”. Report CAGR and ulcer deltas. State separately that only `drop_30` and `drop_35` have visibly large ulcer separations, while NB20 remains context rather than an error bar.

### 7. The underwater-chart caveat contradicts the corrected NB20 interpretation

- **Severity:** material
- **Cells:** 0, 31
- **What is wrong:** Cell 31 says curve differences below 4.4% “are not distinguishable from reporting behaviour”. Cell 0 more accurately says the sensitivity perturbs the anchor only and is not an error bar for candidates.
- **Why:** NB20 never measured candidate-minus-anchor reporting bias. Its anchor-only sensitivity cannot define a statistical or directional distinguishability threshold for differences between two underwater curves.
- **Concrete fix:** Replace cell 31’s final paragraph with: “NB20’s anchor-only sensitivity moved the anchor ulcer by 4.4%. It does not measure candidate-minus-anchor reporting differences and is context for interpreting visual differences, not an error bar or a distinguishability threshold.” Soften cell 0’s “below which” wording similarly.

### 8. The shared-view re-run has no source-result cross-check

- **Severity:** minor
- **Cells:** 20, 24, 26
- **What is wrong:** NB25 asserts anchor parity but does not assert that its 35 re-run panels match the frozen NB21–NB24 results.
- **Why:** Its purpose is to consolidate prior work, so source parity matters as much as anchor parity. The visually identical rows are plausible rather than evidence of a bug: `drop_5` appears inert relative to the anchor, and `swap__centre`/`swap__require_scored` appear to have identical realised behaviour. But the displayed rounding cannot establish exact equality or explain it.
- **Concrete fix:** Load the frozen source manifests or expected panel fingerprints and assert every common metric at the established tolerance. Explicitly annotate exact or near-exact duplicates as inert configurations.

### 9. Several numerical heading claims are not traceable to a cited cell

- **Severity:** material
- **Cell:** 0
- **What is wrong:** The 70.9%, 57.91%, 4.4%, and family-wise `p = 0.813` claims cite prior notebooks by name but not their source cells; 57.91% is not reproduced in NB25 output.
- **Why:** This breaches the track’s rule that every numeric heading claim cite its source cell, and prevents audit from NB25 alone.
- **Concrete fix:** Add exact originating notebook-and-cell citations, or reproduce a compact source table in NB25. For example: “NB20 cell X reports the 4.4% anchor-only sensitivity; NB24 cell Y reports family-wise p = 0.813.”

## Checks that passed

- Cycle Sharpe, volatility, and beta are inherited from cycle-clock calculations, not zero-filled daily strategy returns.
- Anchor parity and splice inertness are correctly asserted in cell 20.
- The `runs` / `run_by_label` workflow is used consistently for the NB25 tables and charts.
- The strict two-axis filter in cell 34 is correct and returns exactly the four stated labels.
- “Data-availability drop” is justified by the cited removal composition and is consistently used in NB25’s user-facing tables, legends, and prose.
- Martin ordering is clearly identified as continuity/reporting only, not an adoption-rule metric.
---

# Verification of the review, and what was applied (2026-09-13)

Every finding above was checked against `_build/build_25.py`, the executed notebook output and
the frozen `_build/manifest_24.json` before anything was changed. Verdicts follow the review's
own numbering.

| # | Severity | Verdict | One-line reason |
|---|---|---|---|
| 1 | material | CONFIRMED | The bar is `cummax` of family Sharpe + 0.10, a non-decreasing step; the plotted polyline falls to ~2.08 in the 14.9-15.4% band where the bar is 2.847. |
| 2 | material | CONFIRMED, one detail corrected | 11 of 36 rows do have a non-`drop_30` comparator, but `swap__t_cap_4` (vol 13.31%) is referenced to `drop_50`, not `drop_35`. |
| 3 | material | CONFIRMED | The "complete failure inventory per family" listed three of six groups, omitting window sensitivity, the policy run and the anchor. |
| 4 | minor | CONFIRMED as stated | The comma split is safe - no name `failing_constraints_v3()` emits contains a comma - and the counts reproduce exactly from cell 26; only the wording was selective. |
| 5 | material | CONFIRMED, with stronger evidence | `late_ulcer_vs_anchor` is -1.21e-06 for `drop_10` and +1.20e-04 for `drop_20`; all 19 non-drop failures fail the CAGR leg; the anchor fails by construction. |
| 6 | material | CONFIRMED | `drop_10` wins the ulcer by 0.0026% relative and `drop_15` by 0.33%, against `drop_30` and `drop_35` at ~22.9%. |
| 7 | material | CONFIRMED | Cell 31 asserted a distinguishability threshold; only cell 0 carried the anchor-only qualifier, and the two disagreed. |
| 8 | minor | CONFIRMED as a gap, no defect found | All 35 configurations were checked externally against `manifest_24.json` and every metric agrees exactly; the notebook simply never asserts it. |
| 9 | material | REJECTED | The track cites the source NOTEBOOK for imported figures and the source CELL for in-notebook ones; NB21-NB24 do the same, and NB25 cites a cell for every number it computes. Adding cell-level citations for imported figures would be an improvement, not a correction. |

## Additional findings the review did not raise

- **Material, cell 0.** "`drop_30` ... was still REJECTED by NB21, because both its neighbours
  fail" is wrong. `manifest_21.json` records centre 30 as `centre_ok: true`, `lower_ok: false`,
  `upper_ok: true`: only `drop_25` fails, on constraint 4. Corrected in the heading.
- **Material, cells 26, 28, 32.** `drop_5` reproduces the anchor bit for bit on all ten panel
  metrics, so one of the twelve drop-family runs is the anchor under another name. It is counted
  in every "N of 12", it scores `late_ok = False` for the anchor's definitional reason, and its
  curve sits exactly under the anchor's in both chart sections. Not disclosed anywhere; now
  recorded in "Robustness of results".
- **Minor, cells 26, 28, 32.** `swap__centre` and `swap__require_scored` are likewise identical on
  all ten metrics, so `require_scored_candidates` is inert on this snapshot. Now recorded.
- **Minor.** NB25 is not one of the notebooks the plan pre-registers; it was added afterwards as a
  diagnostic. The heading does not claim otherwise, so this is noted rather than corrected.

## What was changed

Code, in `_build/build_25.py` only. No shared module was touched.

- **Cell 24** now derives `c7_reference`, the family member each row's constraint 7 is actually
  measured against, and asserts that reproducing the selection reproduces `placebo_ref_observed()`
  to 1e-12. It also derives `late_ulcer_vs_anchor`. The reference breakdown is printed.
- **Cell 26** adds `late_cagr`, `late_ulcer_vs_anchor` and `c7_reference` to the table, so
  `late_ok` and the observed-control column are auditable from the notebook rather than asserted
  in prose. `late_ulcer_vs_anchor` is formatted in scientific notation because the deciding
  margins are of order 1e-06.
- **Cell 34** reports `cagr_vs_anchor` and `ulcer_vs_anchor_rel` for the two-axis winners, and the
  print label no longer says "beating the anchor".
- **Cell 36** draws the actual constraint: the family is plotted as points and the bar as a
  separate dashed `hv` step at `cummax(cycle_sharpe) + PLACEBO_MARGIN_V3`.

Markdown: cells 25, 31, 33, 35 and 37 rewritten, and the cell 0 write-up rewritten against every
verdict above.

## Re-run and parity

Re-run in full after the changes. Anchor parity holds against `BASELINE` on all ten metrics at
1e-5 (worst absolute difference 3.99e-07) and both `decide_trades` splices are asserted inert.
Reference values reproduce exactly: anchor 0.378971 / 2.159792, `drop_30` 0.489942 / 2.747391,
`complementary_18` -0.177391 / -1.176589. No metric moved; the only number that changed anywhere
is the wall-clock time of the backtest loop, 624s to 656s, updated in the heading. The verdict is
unchanged and remains DIAGNOSTIC.
