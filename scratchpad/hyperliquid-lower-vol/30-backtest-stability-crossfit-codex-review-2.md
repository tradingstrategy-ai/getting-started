The first review’s temporal-leakage finding is fixed: cell 20’s walk-forward schedule uses only dates strictly before `fold_start - 30 days`, so neither targets nor trailing signals can include the held-out fold. The heading now correctly limits the stitched-path check to anchor segmentation.

Findings:

- **Blocking — cells 20, 26, 31; heading cell 0:** The reported “0 of 26 signal-fold gate-5 evaluations” is not an interpretable null. `simultaneous_ci()` now requires complete-family draws, but `screen_table()` supplies all 39 stability hypotheses (and all 13 return hypotheses) to each family. The warnings in cell 26 show non-finite/insufficient bootstrap statistics. One such hypothesis makes its standard error non-finite, which makes every draw incomplete and therefore makes the family critical value and all simultaneous lower bounds `NaN`. Every affected signal then fails mechanically. Cell 26 does not print `n_draws`, incomplete-draw counts, per-signal usable dates, bounds, or failure clauses; cell 31 nevertheless counts all 13 signals in each fold as “evaluations”.

  This means the complete zero may be a consequence of an unevaluable simultaneous family, not evidence that every signal failed the gate. The safe result is only: “no fold produced a valid selected signal under this implementation.”

  Fix: expose each family’s complete-draw diagnostics and each signal’s sample/date count, bounds and failed clauses. Mark a fold or hypothesis unevaluable where the required simultaneous bound cannot be formed; do not count it as a failed evaluation. If a full 39-hypothesis family is required, an incomplete family must make the fold unevaluable, not make all 13 signals false.

- **Material — cells 20, 24, 26; heading cell 0:** The revised excess-over-uniform event-concentration target is algebraically correct for equal-sized positive events: `share - min(5, n)/n` is zero in that case. But it is a new Gate-5 estimand introduced after the original screen, not merely a numerical correction. It changes both the scale and cross-sectional ordering of the target; its attainable range also still varies with the positive-event count.

  This does not literally alter the pre-registered `delta=5` threshold, but it does matter for pre-registration: NB30 cannot describe this as the original pre-registered Gate-5 test without qualification. The heading should identify the result as the revised-v2 target diagnostic, rather than treating it as direct confirmation of the original gate.

- **Material — heading cell 0 versus cell 22:** The heading’s snapshot claim is false. It says `vault-prices.parquet` is 254,818,366 bytes with SHA prefix `3e79966a`; cell 22 reports 255,136,297 bytes and `8bce13191183c7d4`. This matters because NB30 also imports NB28 and NB29 manifests, while its live panel uses the current snapshot.

  Fix: generate snapshot provenance from the current run’s recorded provenance, and either verify the imported manifests have identical provenance or avoid using them for current-run claims.

- **Minor — cells 22, 24, 31; heading cell 0:** The notebook still violates the stated single-source rule. It reads eligibility and Gate-5 comparisons from `manifest_28.json`, despite rebuilding the local panel and full screen. The coincidentally matching values do not make the provenance check unnecessary.

  Fix: generate the heading’s eligible-decision and full-screen claims from NB30’s local `eligibility` and `full_screen`, stored in `manifest_30.json`; reserve imported manifests for labelled historical context only.

What checks out:

- Signal reads are strictly prior to the decision timestamp; forward targets begin from the carried decision NAV.
- Cycle Sharpe, volatility and the stitched comparison use two-day-cycle returns with sample standard deviation.
- Bootstrap resamples are shared across hypotheses within a screen.
- The activation branch is accurately described as unexercised, and the anchor reconstruction is no longer overstated as an activation-window test.
- The compounded annual-return contrast in cell 20 has the stated units. Its potentially extreme magnitude is a property of compounding the supplied log-return tails, not an arithmetic mismatch here.