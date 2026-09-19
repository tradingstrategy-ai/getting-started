## Overall verdict

The numerical screen result is correct: both signals pass the two stability legs and fail gate 5 solely because the frozen return-clause lower bound is below -0.005. The cycle-clock, causal T-1 signal reads, actual-exclusion matching, shared two-way bootstrap, max-T lower bounds, and failure reporting are sound.

However, the heading materially overstates what the return result proves. NB34 does not demonstrate that the return clause is intrinsically unreachable; it only demonstrates that it was not passed on this sample.

## Findings

- **Material — cell 32 (and heading findings 1–2).** The notebook does not meet standing rule 9 for its striking complete return-clause failure. It shows two observed failures, but does not show whether the mechanism can ever clear this clause on this panel. The inherited `oracle_reachability()` is not run and is incompatible with v3’s altered statistic layout if called unchanged.

  The claim that “no clause on a forward return of the excluded tail can be resolved” is therefore unsupported. A perfect-foresight return ordering would be the relevant reachability check; without it, a wide interval can reflect either insufficient resolution or a coding/estimand defect.

  Fix: either remove the unreachable/data-limit conclusion and report only the observed failure, or add the mandated deterministic reachability diagnostic before making that conclusion. This does not alter the current gate-5 failure.

- **Minor — cell 32 / heading finding 1.** The arithmetic is right: passing requires observed contrasts above approximately `2.2671 × SE − 0.005`, or +0.393 for `calm_score` and +0.363 for `inverse_vol`. But calling this “not the non-inferiority test the clause was written to be” is technically inaccurate. It remains a one-sided non-inferiority test; with this realised uncertainty its rejection region happens to require a strongly positive estimate.

  Fix: say it is “operationally as demanding as a large superiority result on this sample”, rather than saying it is not a non-inferiority test.

- **Minor — cell 30 / heading finding 3.** “Old silent vaults” is too broad. The masked group is older than the raw-measured group (median 294 versus 257 days), but 729 post-break rows have a recent mark and fail only the fewer-than-30-fresh-marks guard. Those vaults are thinly observed, not necessarily silent.

  Fix: describe the group as “older and often sparse or recently silent”; retain the separate guard-reason counts.

- **Minor — cell 38 / heading summary.** “Nothing here suggests a price signal could answer” exceeds the descriptive evidence. Cell 38 gives unbootstrapped, overlapping-window descriptive correlations only; it is reasonable context for dropping the target, but cannot establish a general negative claim.

  Fix: say “these descriptive correlations are near zero in this panel”.

## Checks that passed

- **Cell 16:** Sharpe and volatility use two-day cycle returns, not zero-filled daily returns.
- **Cells 27 and 32:** The panel reads T-1 values; both offline signals match the in-trade reads exactly. Actual count-eight flags match the engine on all 111 eligible dates, including tie order and permissive handling of unmeasured candidates.
- **Cells 21 and 32:** The bootstrap resamples date blocks and vault clusters jointly, reuses the same draws across both signals, uses sample standard deviations, and forms one-sided simultaneous lower bounds in the correct direction.
- **Cells 29–30:** `calm_score` is correctly shown to be a subset of `inverse_vol`, with every masked row explained by a guard.
- **Heading finding 4:** Its core exclusion-set logic is sound: the two filters can differ only if a raw bottom-eight `inverse_vol` candidate is guard-masked. Strictly, “the ninth goes instead” applies when exactly one of those eight is masked; more can push replacement further down the raw ordering.

So: retain the **DIAGNOSTIC** verdict and the reported gate failure, but revise the claimed explanation from “unresolvable/unreachable” to “not established by this sample unless reachability is demonstrated.”