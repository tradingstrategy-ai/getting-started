The revised notebook fixes the original imported-Gate-5 and max-T defects in code, but it still has two blocking interpretation problems.

1. **Blocking — cells 20, 26; heading cell 0:** Gate 5 is no longer the pre-registered test. `forward_event_top5` is replaced after the first review with `forward_event_top5_excess`, and the heading calls the resulting zero-of-thirteen result “under the pre-registered criterion”. The excess construction is mathematically sensible, but it changes the target and hence the gate after results were known.

   Fix: retain the original raw-concentration Gate 5 as the pre-registered verdict, and label the excess-target screen as a corrected post-hoc diagnostic unless it was pre-registered before this run.

2. **Blocking — cell 22; heading cell 0:** The claimed common snapshot is contradicted by the notebook’s own provenance output. The heading says all four notebooks used `vault-prices.parquet` of 254,818,366 bytes with hash `3e79966a`; cell 22 reports 255,136,297 bytes and `8bce13191183c7d4`. No upstream manifest preserves an expected hash and no equality assertion is made.

   This invalidates the claim that the cross-kernel checks are on one snapshot. Matching seven panel values does not prove the rebuilt Gate-5 panel used the same input archive.

   Fix: store full provenance in each upstream manifest and assert it equals the current provenance before describing results as reproduced or comparable across kernels.

3. **Material — cell 26; heading cell 0:** The original finding is only partly addressed. Cell 26 genuinely rebuilds the panel and bootstrap and downstream gates use `GATE_5_REDERIVED`, which is good. But it compares only Gate-5 booleans, forward-volatility lower bounds, and return lower bounds. It does not compare the forward-downside or event-concentration lower bounds, sample/date counts, missingness, critical values, or complete-family draw counts.

   Therefore “agrees with NB28” is true only for the displayed subset and the all-false flags, not for the complete screen output.

   Fix: compare every persisted screen field and bootstrap-family diagnostic, including retained/incomplete draw counts, and fail on unexpected differences. The stated `4.38e-07` difference is also consistent with six-decimal manifest serialisation, not necessarily “floating-point noise”.

4. **Material — cell 26; heading cell 0:** The surprising all-zero Gate-5 result is reproduced, but not shown *unreachable as a measurement failure*. The output does provide reassuring evidence against an all-NaN/no-op target: the rebuilt panel has 9,954 finite excess observations and signal estimates vary. However, rerunning the same machinery cannot establish that the screen could ever produce a pass if its third-target orientation, ranking, or lower-bound construction were defective.

   Fix: add a deterministic reachability/invariant check for the screening machinery and report it beside the retained-draw diagnostics. This is validation of the implemented gate, not a new research experiment.

5. **Minor — cell 28; heading cell 0:** The corrected residual-concentration diagnostic is not shown “both ways” in a meaningful numeric sense. Cell 28 displays only `gate_3_held_book` and `gate_3_corrected`; it omits the original and corrected held concentrations, anchor values, coverage, and any equality check. A shared `False` does not demonstrate that the known numerator defect is unreachable for this book.

   Fix: display and persist both concentrations and their coverage, then explicitly state whether they are equal within tolerance.

6. **Minor — cell 34; heading cell 0:** The frozen specification still says concentration is “set by … sizing, not by selection”, while the heading correctly notes NB29 showed that selection does move concentration. The correction is not applied to the specification itself.

   Fix: replace that known-limit text with the observed qualification: selection can move concentration; Gate 8 tests whether it becomes worse than the anchor.

What is sound:

- Cell 20’s complete-family max-T lower-bound construction is correct and fails closed below 100 complete draws.
- The return contrast now correctly differences compounded annual returns derived from mean 30-day log returns. The hundreds-to-thousands of percentage-point half-widths are an honest consequence of that estimand; they make the return clause uninformative, not arithmetically wrong.
- Cycle Sharpe and volatility remain measured on the native two-day clock.
- The walk-forward fold rule is free of the prior post-fold trailing-signal leak, and NB30 labels early folds unevaluable rather than treating them as failures or passes.
- No new decision-time look-ahead is apparent in the strict-prior signal access.