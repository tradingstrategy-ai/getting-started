The executed result is correctly limited to **VACUOUS**: two folds were evaluable, neither selected a signal, and the stitched series is exactly the anchor. The second-review max-T and walk-forward fixes are working on this run.

Findings:

- **Material — cells 20, 24, 26:** `leading_signal()` is incompatible with the pre-registered raw screen. `run_screen(..., "pre_registered")` temporarily uses `forward_event_top5`, then restores global `STABILITY_TARGETS` to the corrected `forward_event_top5_excess`. If a raw-screen signal passed, `leading_signal()` would try to read `lo_forward_event_top5_excess`, which does not exist in that screen, causing a `KeyError`. It is hidden only because there are no passers.  
  Fix: make `leading_signal()` take the target list explicitly, or derive the concentration lower-bound column from `screen.attrs["concentration_target"]`.

- **Material — cells 27–29:** The conditional stitched-path implementation remains invalid if a fold ever activates. Each segment comes from a separately rerun backtest that starts from the anchor state, so a changed book/equity state from an earlier active fold is discarded. Returns are also assigned by return timestamp, although the decision producing a boundary return belongs to the preceding decision date. The current anchor-only identity is valid only as a segmentation check, as the heading now says; it is not a valid implementation of a non-vacuous cross-fitted path.  
  Fix: construct one stateful run driven by a date-to-signal schedule, or assign returns to their preceding decision timestamp and carry state across folds.

- **Minor — cell 22 and heading cell 0:** The heading says upstream manifests were checked “before their manifests were read”, but cell 22 reads and parses both JSON manifests before calling `assert_same_snapshot()`. The check does occur before their substantive values are used, so this does not taint the result, but the wording is false.  
  Fix: say “asserted equal before their results were used”, or store provenance separately if pre-read validation is required.

- **Minor — cells 24 and 31:** NB30 still uses `manifest_28["gate_5"]` for displayed comparisons despite having locally recomputed `full_screen`; this remains contrary to the stated `runs` / local-result single-source rule.  
  Fix: populate `full_sample_gate_5` and the comparison print from local `full_screen`; retain NB28 only as labelled historical context.

What checks out:

- Walk-forward training now ends before the 30-day embargo, so neither forward targets nor trailing signal windows can contain held-out-fold returns.
- The evaluated-family max-T correction is active: folds 3 and 4 use 27 and 33 stability hypotheses respectively, retain all 200 complete draws, and count only 9 and 11 evaluated signals. Thus `0 / 20` is arithmetically correct.
- The raw, pre-registered concentration target is used in NB30’s actual screens.
- Provenance hashes match NB28 and NB29, and anchor parity holds.
- The heading’s numeric claims match cells 24, 26, 28, 29, and 31.

On reachability: NB30 itself does not establish that a full Gate-5 pass is reachable; appropriately, it does not claim that. NB28’s oracle output shows the stability clause is reachable (`oracle_all`) and the return clause is reachable (`oracle_return`), but neither oracle passes the combined gate. Therefore the batch supports “no real signal passed under this implementation”, not “Gate 5 itself is jointly attainable” or a stronger substantive null.