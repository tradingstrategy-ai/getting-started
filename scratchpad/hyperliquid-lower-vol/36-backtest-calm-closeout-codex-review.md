## Overall verdict

**No blocking arithmetic or verdict defect found.** The two REJECT verdicts remain supported. However, NB36 overstates how independently it re-derives checks, and its headline interpretation again exceeds the null evidence.

- **Material — cell 28.** Gate 5’s rebuilt flags are never verified against a real count-eight engine run, nor are the panel’s `calm_score`/`inverse_vol` reads checked against the in-trade reads. `add_exclusion_flags()` merely reuses the offline mirror. Matching NB34’s rounded statistics cannot independently catch a common mirror/splice error.  
  **Fix:** call `verify_signal_reads()` and `verify_exclusion_flags()` for both `calm_8` and `measured_8`, assert adequate comparable-date coverage, and record the results before accepting the re-derived screen.

- **Material — cells 26 and 30.** The reproduction comparisons fail open on non-finite values. In cell 26, `max(0.0, nan)` leaves `worst` at zero; in cell 30, any field non-finite on either side is excluded from `worst_num`. Thus a finite-to-NaN mismatch could be reported as reproducing exactly.  
  **Fix:** assert matching finiteness for every compared field first; only then compare finite values to the stated tolerance. Treat an unexpected non-finite as a failed reproduction.

- **Material — cell 30 and heading cell 0.** “Every other gate [is] re-derived” is too broad. Gate 2 is deliberately set False by short-circuiting after cheap-gate failure; although the leave-one-vault-out runs were re-run, their retention and masked-CAGR diagnostics are not recomputed or cross-checked here. Gate 9 is independently evaluated later in cell 32, but not through the verdict row.  
  **Fix:** retain the protocol gate booleans as False, but separately recompute and compare `lovo_gate()` outputs for both centres, labelled “diagnostic / would pass”, as cell 32 already does for the null.

- **Material — heading cell 0, “What the track now knows”.** Several conclusions overreach the evidence:
  - “predicting them is not sufficient for a Sharpe that a random exclusion cannot match” ignores that this null also destroys temporal persistence;
  - “the return clause … cannot be resolved by a trailing signal” generalises two screened signals to all trailing signals;
  - the guard “removes the mechanism’s effect, because …” assigns cause rather than reporting the observed association;
  - “not evidence of a mechanism” is stronger than failure to clear this pre-registered hurdle.
  
  **Fix:** say the two signals did not demonstrate an advantage over the specified, persistence-destroying null; the return clause was not demonstrated by either signal on this sample; and the guard result is consistent with the masked cohort contributing to the difference.

- **Minor — cell 32.** `distinct_baskets` is not a digest of the sequence of realised baskets. It hashes per-address counts of positions opened over the full run. Different date-by-date baskets can share that summary. The distinct cycle-return-series and excluded-set assertions do establish effective distinct draws, so this does not alter gate 9.  
  **Fix:** hash the ordered `(decision date, held-address set)` sequence if “distinct baskets” is to be asserted.

- **Minor — cell 34 and heading cell 0.** Cell 34 establishes that each run’s *net* discrepancy is non-positive; it does not establish that every redemption is in the engine’s favour. “The fee differential does not explain any comparison in this plan” is also too broad: several null draws fail the fee-share check, even though the six main candidate-versus-anchor comparisons pass and fee differences do not affect the REJECT verdicts. The `inf` zero-gap case itself is correctly fail-closed.  
  **Fix:** describe this as a non-positive net discrepancy, and limit the conclusion to the six main comparisons and the final verdicts.

- **Minor — heading cell 0.** The paragraph following the specification imports numerical NB34/NB35 findings (66 decisions, one-third coverage, three-to-five null draws) without cell citations that support them in NB36.  
  **Fix:** cite the upstream cells/manifests explicitly, or re-display the supporting figures in NB36.

Checks that pass: cycle Sharpe and volatility use the two-day strategy clock; the gate-5 bootstrap and simultaneous lower-bound construction are carried through consistently; the 19 null cycle-return and excluded-set series are genuinely distinct; the zero-equity-gap fee share is correctly `inf` and fails closed; and the complete failure strings shown for both centres are correct.

The close-out’s **NOTHING SHORTLISTED** result should stand after the reporting and verification-strength corrections above.