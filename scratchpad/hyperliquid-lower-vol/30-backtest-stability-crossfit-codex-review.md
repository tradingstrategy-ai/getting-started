NB30’s safe conclusion is only **VACUOUS**: no fold chose a signal, so it did not exercise or evaluate the cross-fitted mechanism. Its stronger claims about temporal isolation, “every fifth” of the sample, and the completeness of the gate-5 null are not supported.

- **Blocking — cells 19, 25; heading cell 0:** The purge does not remove temporal leakage into the fold screens. `fold_schedule()` admits training dates after a held-out fold once their 30-day *forward targets* no longer overlap it. But the signals at those later training dates use trailing windows of 45–360 calendar rows, 90 fresh events, etc.; their values therefore contain returns from the held-out fold. The claim that no segment was “scored by a screen that saw it” is false.

  Fix: exclude post-fold training dates whose signal lookbacks touch the held-out fold (or use only pre-fold training with the required target embargo). If that leaves fewer than 40 dates, mark the fold unevaluable rather than cross-fitted.

- **Blocking — cells 23, 25, 30; heading cell 0:** The “zero of thirteen” result is not shown to be unreachable, only observed again under the same machinery. The notebook prints gate booleans and dates, but not the individual lower bounds, target coverage/missingness, bootstrap-valid draw counts, or each signal’s exact failing clause. The heading’s explanation — “one target is unpredictable by anything” and return intervals are “20 to 60 times” the margin — appears in no cited NB30 output.

  This fails the standing requirement for a complete null result: rerunning a potentially defective measurement on overlapping subsets cannot distinguish an absent effect from a broken target or bound construction.

  Fix: either downgrade the conclusion to “no gate-5 pass was observed under this implementation”, or print and cite the complete decomposition already asserted from NB28: finite-target counts and reasons, per-signal estimates and simultaneous bounds, clause failures, and bootstrap validity diagnostics.

- **Material — cells 25 and 30; heading cell 0:** “It holds on every fifth of [the window] that was tested” is incorrect. Each fold screen is trained on the complementary 59–74 dates, not evaluated on its withheld fifth; the five training samples overlap extensively. The result is five correlated failures on overlapping training subsets, not evidence about each fifth of the period.

  Fix: say: “None of the five purged training screens selected a signal.” Remove the claim of per-fifth replication.

- **Material — cells 27–28; heading cell 0:** The stitched-path check cannot validate the activation window, despite claiming it would catch an activation-window error. No fold chose a signal, so cell 27 always sources the anchor; the activation branch never runs. Moreover, segments are sliced by return timestamp while folds are defined by decision timestamp. A decision at a fold’s final date affects the following cycle return, which is assigned to the next segment/run. This would mis-assign boundary returns if a prefilter were active.

  Fix: construct the out-of-fold path in one stateful backtest using a date-to-signal schedule, or explicitly map each return to its preceding decision timestamp and preserve portfolio state across boundaries. Limit the current identity check to segmentation/reindexing of the anchor only.

- **Material — heading cell 0:** The statement that exact anchor reconstruction is a “genuine self-test” of the activation code contradicts the robustness section, which correctly says the activation splice was never exercised. The former is an overstatement; the latter is accurate.

  Fix: retain the robustness wording and change the heading to say the result checks only anchor-segment slicing.

- **Minor — cells 21, 23, 30:** NB28 comparisons are read from `manifest_28.json`, rather than from `runs` / `run_by_label`, contrary to the stated single-source rule. The current notebook also does not verify that the imported manifest was generated from the displayed snapshot.

  Fix: rely on the locally recomputed `full_screen` for NB30 claims, or explicitly verify and record imported provenance before making a comparison.

What checks out: strategy Sharpe, volatility and the stitched comparison use two-day-cycle returns with `ddof=1`; the screen reads indicators strictly before the decision timestamp; forward targets start from the NAV carried at the decision; and the bootstrap resamples are shared across the signal/target family within each screen.