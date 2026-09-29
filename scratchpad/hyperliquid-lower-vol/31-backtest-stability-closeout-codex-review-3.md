## Review findings

1. **Blocking — heading cell 0; cited NB28 cell 35:** The reachability evidence does not show that the complete Gate 5 can ever pass. `oracle_all` passes only the stability clause and `oracle_return` passes only the return clause; all three oracles have `gate_5 == False`. This validates each component separately, but not the conjunction that produced the surprising 0/13 result.

   Fix: add a deterministic Gate-5 reachability invariant which constructs an evaluated, finite case with both clauses true and asserts `screen_table()` emits `gate_5=True`. Report it beside the oracle output. The current heading should say that the two clauses are individually reachable, not that the complete screen has been shown reachable.

2. **Material — cell 26; heading cell 0:** “Agrees with NB28 on every field” remains overstated. The code compares 17 numeric table fields and the final Gate-5 flag, but does not compare/assert `stability_clause`, `return_clause`, `enough_dates`, or all bootstrap diagnostics. It prints only the stability family’s critical value, complete-draw count, and family size; return/tail critical values, complete/incomplete draws, and family sizes are neither compared nor asserted.

   Fix: persist every detail-family diagnostic in the manifest and assert equality for all screen columns, including booleans, and all three bootstrap families. Until then, describe the result as agreement on the 17 numeric fields, `evaluated`, and Gate-5 flags.

3. **Minor — heading cell 0, insight 3:** It says gates 1–4 and 6–9 were “re-derived from this kernel’s states”. Gates 2 and 9 were not evaluated: cell 28 fail-closes both because no cheaper-gate survivor and no null runs exist. The later robustness text states this correctly, but the headline contradicts it.

   Fix: say gates 1, 3, 4, 6, 7 and 8 were re-derived; gates 2 and 9 failed closed as unexecuted.

4. **Minor — heading cell 0, provenance bullet:** “each upstream manifest’s provenance checked … before it was read” is literally false. Cell 22 reads all three JSON manifests before calling `assert_same_snapshot()`.

   Fix: say “before their results were used”, or store provenance separately if asserting before reading a manifest is required procedurally.

## What is sound

- The earlier imported-Gate-5 defect is fixed: cell 26 rebuilds the panel from `screen_log`, runs the pre-registered raw-concentration target, and uses the re-derived flags downstream.
- Snapshot parity is now materially demonstrated: cell 22 checks all four data-file hashes against all three upstream manifests.
- The Gate-5 max-T implementation correctly uses evaluated hypotheses and complete-family draws; the output reports 499/500 complete stability draws and a 39-member family.
- Cycle Sharpe and volatility are computed on the native two-day clock with sample standard deviation.
- The heading’s full eight-gate failure string for `inverse_vol_q30` matches cell 28.
- The revised event-concentration wording is appropriately cautious: it says no signal established a positive association, rather than claiming that none exists.