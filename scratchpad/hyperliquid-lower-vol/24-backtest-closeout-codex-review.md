## Review outcome

The core backtests, cycle-clock metrics, manifest metric comparison, and `family_wise_joint()` implementation are sound. The family-wise p-value arithmetic is correct: common block indices are applied to one aligned matrix; each difference is centred; the within-draw maximum is used; and `(1 + 812) / (999 + 1) = 0.813`.

I found five genuine material/blocking issues and one minor latent code bug.

## Genuine errors

- **Severity:** blocking  
  **Exact cell number:** 53  
  **What is wrong:** Lead 2’s adoption Boolean omits its pre-registered requirement that realised within-basket joint-loss concentration improve versus the anchor. It can therefore adopt `complementary_18` even if the proxy fails its stated objective.  
  **Why it is wrong:** Cell 53 uses centre, plateau, window and leave-one-vault-out Booleans only. The frozen manifest’s `within_basket_concentration_falls` flag is not used — correctly, as source flags should not be trusted — but no replacement is recomputed from this kernel’s logs and returns. The present REJECT is unaffected because the other gates already fail; a future passing configuration could be falsely admitted.  
  **The concrete fix:** Recompute this Boolean in NB24 from the re-run anchor and `complementary_18` records, then require it explicitly:
  ```python
  NB22_WITHIN_BASKET_OK = recompute_within_basket_concentration_falls(
      run_by_label["anchor"],
      run_by_label["complementary_18"],
  )
  ...
  "adopt": bool(
      NB22_CENTRE_OK and NB22_PLATEAU_OK
      and NB22_WITHIN_BASKET_OK and nb22_lovo_ok
  )
  ```
  Print the Boolean and its underlying anchor/candidate quantities beside the other lead-2 gates.

- **Severity:** material  
  **Exact cell number:** 53  
  **What is wrong:** Lead 2’s adoption Boolean adds `NB22_WINDOW_OK`, although the pre-registered NB22 verdict requires the centre, plateau and leave-one-vault-out; window sensitivity is specified as reporting “beside the plateau”, not as an adoption gate.  
  **Why it is wrong:** This changes the adoption rule after it was specified, albeit in a stricter direction. It does not affect this result because all four sensitivity runs fail, but it could reject a future otherwise-qualifying centre for an unregistered reason.  
  **The concrete fix:** Remove `NB22_WINDOW_OK` from the adoption expression, retain it as a reported robustness result, and add the missing within-basket condition:
  ```python
  "adopt": bool(
      NB22_CENTRE_OK and NB22_PLATEAU_OK
      and NB22_WITHIN_BASKET_OK and nb22_lovo_ok
  )
  ```

- **Severity:** material  
  **Exact cell number:** 0 and 29  
  **What is wrong:** “The whole plan reproduces bit-for-bit” overstates what cell 29 verifies. The check genuinely compares re-run values with stored manifest literals, but only for CAGR and cycle Sharpe. It does not compare state, trades, equity paths, diagnostic logs, other panel metrics, or even the re-run override dictionary with its manifest counterpart. Also, a future mismatch cannot automatically be “stated in the heading”: cell 0 is fixed markdown and continues to state success.  
  **Why it is wrong:** The exact zero is not tautological — `actual_*` comes from the re-run panel and `expected_*` from manifests — and is plausible for deterministic reruns. But it supports only exact reproduction of those 72 stored metric values. On a mismatch, the non-fatal banner is below the heading, while the heading would still assert a successful bit-for-bit reproduction.  
  **The concrete fix:** Replace the claim with: “All 36 re-runs reproduce the two frozen metrics checked here — CAGR and cycle Sharpe — exactly.” Compare overrides too:
  ```python
  assert entry["overrides"] == EXPECTED[label]["overrides"]
  ```
  On failure set the formal verdict to `INVALID — CROSS-CHECK FAILED; no adoption decision`, rather than retaining an ordinary verdict beneath a stale success heading.

- **Severity:** material  
  **Exact cell number:** 48, with the corresponding claim in cell 0  
  **What is wrong:** The code and prose conclude that all five family ulcer improvements are “not distinguishable from a reporting artefact”. NB20’s sensitivity only remeasures the anchor after dropping stale cycles; it does not measure the candidate–anchor difference in reporting bias.  
  **Why it is wrong:** There is no percentage-unit mismatch in the arithmetic: both the margin over the 15% threshold and the sensitivity are expressed relative to the anchor ulcer, so comparison on that scale is valid. But an anchor-only sensitivity cannot establish that a candidate’s lower ulcer is caused by differential staleness. It supports a measurement concern, not the claimed indistinguishability conclusion. In addition, `drop_50`’s margin is 4.328 percentage points, below the stated lower sensitivity endpoint of 4.426, while `inside_the_staleness_band` tests only `margin <= upper`.  
  **The concrete fix:** Rename the Boolean to `margin_no_larger_than_max_anchor_sensitivity`, and replace the conclusion with: “The anchor-only staleness sensitivity is large relative to these margins, so it materially limits interpretation of the apparent ulcer improvement; it does not establish that the candidate–anchor difference is a reporting artefact.” If retaining a literal “inside the band” claim, require both bounds; otherwise describe the interval as `0% to 11.2%` only if that is the intended uncertainty range.

- **Severity:** material  
  **Exact cell number:** 55  
  **What is wrong:** Several NB22/NB23 diagnostic claims are presented as findings of this kernel but are hard-coded text, not recomputed or even read from a manifest in NB24. Most notably, the claim that joint-loss frequency has “no forward information” is inferred from a descriptive `+0.013` correlation over 2,106 heavily overlapping trailing-window reads.  
  **Why it is wrong:** The close-out only re-runs and cross-checks CAGR and Sharpe. Cell 55 neither derives the co-loss interval, rank, deployment mechanism, stage-1 audit, nor identity statistics from `runs`/logs. A near-zero descriptive correlation on overlapping observations is not a test establishing absence of predictive information, nor does it prove the stated causal failure mechanism.  
  **The concrete fix:** Either recompute these diagnostics from the re-run records, or label them explicitly as quoted source-notebook results with their manifest keys. Replace “with no forward information” with: “with no useful descriptive one-cycle association in this sample (`r = +0.013`); the overlapping reads do not establish absence of predictive information.”

- **Severity:** material  
  **Exact cell number:** 50  
  **What is wrong:** The claimed frozen shadow specification does not fully specify adoption rule v3. In particular, it never defines the prospective constraint-7 comparator family, whether all family members are run in shadow, or how its volatility-matched reference is calculated. Metadata/universe handling is also discretionary: “hashes change in a way that alters universe membership” supplies no fixed detection or restart rule.  
  **Why it is wrong:** The decision rule says to apply v3, but describes only the shadow anchor for constraints 2–5. Constraint 7 requires an observed volatility-matched family, not merely the anchor. This leaves a material post-data degree of freedom in a supposedly frozen prospective rule.  
  **The concrete fix:** State explicitly that the shadow runs the anchor plus `drop_5` through `drop_60` with the frozen code and parameters; define `placebo_ref_observed()` unchanged; state whether constraint 7 applies to each candidate; and name exactly which provenance files may update, which frozen metadata file determines membership, and the deterministic condition requiring restart.

- **Severity:** minor  
  **Exact cell number:** 18  
  **What is wrong:** `bootstrap_margin_table()` will raise when it finds an observed-control reference:
  ```python
  name = reference_label.name
  ```
  `idxmax()` returns an index label such as `"drop_30"`, which is a string and has no `.name`.  
  **Why it is wrong:** The function was not exercised here because no eligible centre needed its margin table, so it does not change NB24’s result. It will fail the intended paired-bootstrap reporting path when called.  
  **The concrete fix:** Use:
  ```python
  name = str(reference_label) if reference_label is not None else family["cycle_vol"].idxmin()
  ```

## Correct but potentially clearer

- The cross-check is a real recomputation-versus-stored-literal comparison, not a stored-value self-comparison. Exact zeros are credible for deterministic, identical reruns.
- Constraint 7’s arithmetic is correct: `2.747391 + 0.10 = 2.847391`, and the anchor’s 2.159792 fails it. The “zero of thirteen” count is also numerically correct, though twelve of those rows are self-comparisons for which constraint 7 is explicitly inapplicable.
- The cell-48 percentage scales are compatible. The error is the causal interpretation and the loose meaning of “inside the band”, not percentage-versus-percentage-point arithmetic.
- The family-wise test is correctly jointly resampled and appropriately caveated as low-power; it does not claim that p = 0.813 proves no effect.
- Cycle Sharpe, volatility and beta use the strategy’s two-day clock rather than zero-filled daily returns.
---

## Verification of these findings, and what was applied

Each finding above was checked against `_build/build_24.py` and the executed notebook before
anything was changed. Verdicts below; the independent findings that this verification turned up
are listed after them.

| # | Finding | Cell | Verdict | Applied |
|---|---|---|---|---|
| 1 | Lead 2's adoption Boolean omits the within-basket concentration gate | 53 | CONFIRMED | yes |
| 2 | `NB22_WINDOW_OK` is an unregistered adoption gate | 53 | REJECTED | no |
| 3 | "reproduces bit-for-bit" overstates a two-metric check; overrides not compared | 0, 29 | PARTIAL | yes |
| 4 | The ulcer indistinguishability claim outruns an anchor-only sensitivity | 48, 0 | CONFIRMED | yes |
| 5 | Cell 55's diagnostics are quoted, and "no forward information" overstates r = +0.013 | 55 | PARTIAL | yes |
| 6 | The shadow specification never defines constraint 7's prospective comparator | 50 | CONFIRMED | yes |
| 7 | `bootstrap_margin_table()` raises on `reference_label.name` | harness | REJECTED | no |

**1 - CONFIRMED.** The plan states lead 2's criterion twice. The NB22 section's Verdict line
(`20-stability-leads-plan.md` line 288) omits the concentration gate, but the leads table (line 41)
requires it and says why: "passing the constraint table while the basket still sinks together would
mean the proxy failed". Cell 53 used neither the manifest flag nor a recomputation. The measurement
needs NB22 Part A's mark matrix, which this close-out does not rebuild, so the gate is now carried
explicitly as a fail-closed `False` in the lead-2 row and in `adopt`, in the same way an unexecuted
masked run is, with a printed note that NB22 measured the concentration as falling (0.2143 to
0.1876) and that this False means "not re-derived here", not "the proxy failed". Recorded in
Robustness. No verdict changes: lead 2 already fails six constraints, the late period, the plateau
and leave-one-vault-out.

**2 - REJECTED.** The review cites only line 288. Line 41 lists "the plateau over P and the window
sensitivity" inside lead 2's success criterion, so including `NB22_WINDOW_OK` follows the plan
rather than departing from it. The plan's own inconsistency between its two statements is recorded
in Robustness and left alone, per rule 2.

**3 - PARTIAL.** The exact-zero cross-check is genuine: `actual_*` comes from `entry["panel"]` in
this kernel and `expected_*` from the manifest JSON, which stores full double precision
(`2.1597920746960435`), so an exact zero is the expected result of a deterministic rerun and not a
self-comparison. What was overstated is the scope: the bold lead-in said "the whole plan reproduces
bit-for-bit" when only cycle Sharpe and CAGR were compared. Cell 29 now also compares each run's
override dictionary against its manifest entry and folds `OVERRIDES_MATCH` into `CROSS_CHECK_OK`
and into the failure set; the heading and the cell-28 markdown state the scope. The suggestion to
change the formal verdict to `INVALID` on a mismatch was not applied: the verdict words are
pre-registered, and cell 53 already prints a second banner under the verdict when `CROSS_CHECK_OK`
is False. The honest residue - that cell 0 is static markdown and would not rewrite itself on a
future mismatch - is now stated in Robustness rather than claimed away.

**4 - CONFIRMED.** There is no unit error: `margin_over_the_bar_pp` and the staleness band are both
percentages of the anchor's measured ulcer, so they are directly comparable. Two things were wrong.
The Boolean was named `inside_the_staleness_band` but tested only `margin <= STALE_BAND_HIGH`, and
`drop_50`'s margin of +4.328 pp is below the band's lower end of +4.426%, so "sits inside the band"
was literally false for one of the five; it is renamed
`margin_no_larger_than_the_top_of_the_band`. And the conclusion "not distinguishable from a
reporting artefact" does not follow from a sensitivity measured on the anchor alone - it is the
candidate-minus-anchor difference in reporting bias that would have to move, and NB20 never
measured it. Cell 48, the cell-47 markdown, the manifest statement and the heading now claim the
weaker and correct thing: the band limits how the improvement may be read, and limitation 1 is what
makes a differential plausible, but the improvement has not been shown to be an artefact.

**5 - PARTIAL.** Cell 55's rows do name their source notebook and verdict, so they are not passed
off as this kernel's own work, but nothing said they were quoted rather than recomputed the way
NB20's figures are flagged. A scope paragraph is added above the table and a Robustness entry
below. "With no forward information" is genuinely stronger than `r = +0.013` on heavily overlapping
trailing-window reads supports, and is rewritten as "no measurable forward association in this
sample ... not a test that establishes the absence of predictive information".

**6 - CONFIRMED.** The decision rule said "apply adoption rule v3" but named a comparator only for
constraints 2 to 5. Constraint 7 needs an observed control family, which the specification never
defined, and the provenance stopping condition ("hashes change in a way that alters universe
membership") left the detection to judgement. Both are now specified: the shadow runs `drop_5`
through `drop_60` beside the candidate and evaluates `placebo_ref_observed()` on the shadow
window's own family, never on this notebook's 2.847; appended price candles never restart the
shadow, a metadata change restarts it only if the re-derived admitted address set differs, settled
by a diff against the frozen metadata file; the staleness band on the shadow window is defined as
NB20's four variants recomputed on the shadow anchor; and a stopping condition is stated to end the
shadow as a REJECT with no later decision and no restart of the same candidate.

**7 - REJECTED.** The review read `reference_label` as the output of `idxmax()`. It is
`family.loc[<that label>]`, a row Series whose `.name` is the index label, so `.name` returns
`"drop_30"` and the call is correct. No change, and the file is shared with NB21-NB23 in any case.

### Findings this verification added

- **material, cell 34.** `binding_constraints` appended `"late period"` only when the constraints
  1-6 string was empty, so a centre that failed both a constraint and the late period was reported
  as failing only the constraint. It under-reported N = 20, N = 25 and N = 55, each of which also
  fails the late period. This is precisely the class of error the review context names as the one
  this track has made most often. The column is now the join of both parts.

- **material, cell 0.** The Summary of results called `swap__max_events_60` "still failing five
  constraints". Its complete v3 failure set in cell 32 is six - CAGR < 20%, Sharpe non-inferiority,
  volatility, ulcer (not material), beta, observed control - and five is the constraints-1-to-6
  count. The sentence now gives six, names all six, and says which count is which. Every other
  failure count in the heading was checked against cell 32 and is correct.

- **minor, Robustness.** The family-wise test's width was attributed to sample size alone. Two
  things drive it: an annualised cycle Sharpe on 125 two-day cycles carries a standard error of
  roughly `sqrt(182.5 / 125)` = 1.2 before any differencing, and a max-statistic null is set by the
  widest member of the family, so stacking in 23 complementary and swap runs that sit three to four
  Sharpe points below the anchor inflates the maximum well beyond what the drop family alone would
  give. That is the correct price of testing the complete executed family, and it is now stated.

### Checked and found correct

- `family_wise_joint()` is correctly specified. One aligned matrix, one set of block starts per
  draw applied to every column, each candidate centred on its observed difference, the maximum
  taken within the draw, `p = (1 + 812) / (999 + 1) = 0.813`. The null 95th percentile of 3.204 is
  plausible for this design and this sample, and the notebook already reads the result as "no
  power", not "no effect".
- The manifest cross-check compares recomputed values against stored literals; the manifests carry
  full double precision, so the exact zero is real.
- Every gate is genuinely re-derived from `harness_stability.py`. The manifest Booleans appear only
  in `agrees_with_manifest` comparison columns, never as inputs to a verdict.
- Constraint 7's arithmetic: 2.747391 + 0.10 = 2.847391, the anchor's 2.159792 fails it, zero of
  thirteen rows clear it, and the notebook draws the correct conclusion that a constraint the
  incumbent fails is a constant rather than a discriminator.
- Anchor parity, the run inventory (36 expected, 36 executed, empty missing and extra sets), the
  drop-composition arithmetic (49,140 = 126 x 390 removals, 59.76% pooled) and every remaining
  numeric claim in the heading check out against their cited cells.
