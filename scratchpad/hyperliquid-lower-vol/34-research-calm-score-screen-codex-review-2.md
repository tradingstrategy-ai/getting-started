## Findings

- **Material — cell 36.** `oracle_return` does not set its exclusion flags on the stated full pool where `forward_vol` is finite. Its signal is noisy `forward_return`, which is finite on all rows, so it can exclude rows later dropped for missing forward volatility/downside. This violates the declared oracle construction and can leave fewer than eight excluded rows in its complete-case statistic.  
  Fix: mask both oracle signals to the full forward-volatility-finite pool before `add_exclusion_flags()`, assert eight flags per eligible date, then re-run cell 36 and regenerate the heading. `oracle_vol` already uses that pool and independently establishes reachability, so this does not overturn the main conclusion.

- **Minor — cell 0, finding 1.** “39.3% at the median over 30 days” misstates a log-return contrast as a simple percentage return. A `+0.393` log-return difference corresponds to a gross-return-factor ratio of `exp(0.393) ≈ 1.48`, not 39.3% simple return.  
  Fix: call it “+0.393 log-return units”, or state the correctly converted simple-return interpretation.

- **Minor — cell 0, finding 5.** “The eight … actually removes ARE the ones that misbehave” overstates the complete-case evidence. The tail statistic uses an average of 7.92 and 7.91 excluded rows per date (cells 32 and 34), not invariably all eight. The flags are correctly set on the full pool, but rows lacking a stability target are subsequently absent from the contrast.  
  Fix: say “the excluded complete-case members (mean approximately 7.9 of eight per date) …”.

- **Minor — cell 0, summary table.** Several repeated numerical claims in the generated summary table lack explicit cell citations, contrary to the standing heading rule.  
  Fix: add concise table notes: screen statistics → cell 32; count-eight backtest metrics → cell 25; oracle metrics → cell 36; diagnostic regime values → cell 38.

## Checks that passed

The main gate-5 calculation is otherwise sound: it averages per-date medians on the stated complete-case sample, retains full-pool exclusion flags, and correctly handles repeated vault clusters when recomputing medians. The two-way bootstrap resamples date blocks and vault clusters jointly, shares draws within each max-T family, uses sample standard deviations, and forms one-sided simultaneous lower bounds in the correct direction. Signal reads, tie ordering, T-1 causality, and engine/offline exclusions are all directly verified in cell 27.

The first-round findings were addressed: the heading no longer calls the clause intrinsically unresolvable; the non-inferiority wording is corrected; the guard population is described as older and often sparse/recently silent; and the concentration section is explicitly descriptive.

## Overall verdict

**DIAGNOSTIC remains the correct verdict.** The revised finding that the return clause is reachable, but not demonstrated by either trailing signal on this sample, is supported by `oracle_vol`. Correct cell 36’s `oracle_return` flag pool before treating its supporting oracle result as valid.