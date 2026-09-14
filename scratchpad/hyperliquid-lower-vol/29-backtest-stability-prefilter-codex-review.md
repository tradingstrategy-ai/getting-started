NB29’s **REJECT** verdict is not overturned: `inverse_vol_q30` independently fails gates 4, 6, 7 and 8, as well as the carried gate-5 result. The failure string in cell 34 correctly lists all eight failed gates.

Findings:

- **Material — cell 10; affects cell 29 gate 3.** `residual_event_concentration()` claims to measure the share of *positive* residual returns delivered by the best five positive events, but its numerator takes the five largest values from `residual`, not from `positive`. With fewer than five positive residuals, negative returns enter the numerator. The 60-fresh-mark condition does not ensure five positive residuals. This can invalidate the held-concentration comparison and the “SPIKIER” headline claim.  
  Fix: calculate `top5` from `positive`, require at least five positive residual events, otherwise return `NaN`; then recompute gate 3.

- **Material — cells 0 and 21.** The surprising “zero of thirteen signals pass gate 5” result is merely imported and reported as Booleans. Cell 21 shows only date counts and pass/fail flags, not the estimates, simultaneous lower bounds, missingness, bootstrap validity, or the binding target. Thus NB29 does not meet the requirement to show the universal null is unreachable rather than simply observed.  
  The existing manifest does contain useful evidence: inverse volatility has strong simultaneous lower bounds for forward volatility (0.551795) and downside (0.489299), while forward event concentration is binding (-0.142554), with return also failing (-28.213827 pp). NB29 hides this.  
  Fix: render those existing manifest fields in cell 21, including per-signal sample counts and every binding lower bound; otherwise remove the global claim from the heading and point readers to NB28’s demonstrated diagnostic.

- **Material — cells 40 and 42.** The integrity and redemption-fee audits inspect only `state`, which remains the anchor state from cell 16. None of the five prefilter runs or the strict run is audited, despite having materially different holdings and redemption paths.  
  Fix: iterate over the relevant entries in `runs`, assert the integrity and fee reconciliation for each, and report the run label alongside any failure.

- **Material — cell 0 / `_build/build_29.py`.** The executed heading is not reproducible from the supplied build script: the builder still contains “_To be filled in after the run_” at all three results sections, whereas cell 0 contains the completed interpretation. Rebuilding changes the reviewed notebook’s conclusions.  
  Fix: update the build source to contain the executed markdown and regenerate the notebook.

- **Minor — cell 19.** `_statistics_from()` applies `sign` to the return Spearman correlation as well as the stability correlations. This reverses the documented interpretation of `rho_forward_return`: for either signal direction, positive return at the retained/stable end is currently reported with the wrong sign. It does not alter gate 5, which uses `return_contrast_pp`, but it makes that diagnostic unreliable.  
  Fix: apply `sign` to the three stability correlations and `-sign` to the return correlation.

- **Minor — cell 0 citing cell 27.** “Exactly inert”, “to 0.000e+00 on every metric”, and “bit-identical” are not established by cell 27. It prints nine rounded fields to four decimals and omits max drawdown and the equity-path comparison. The conclusion may be true, but the cited evidence does not prove it.  
  Fix: calculate and display full-precision metric differences and an equity-path equality assertion for the strict run.

- **Minor — cell 0.** “Without holding any cash” and “fully invested” contradict the reported mean invested range of 0.9697–0.9798.  
  Fix: say “without materially reducing deployment” or “roughly 97–98% invested”.

- **Minor — cell 0.** The explanation for gate 4 says `luck_ratio` is NaN because the “without-best-five” leg is non-positive. The function returns NaN if either that leg *or* the random-removal median is non-positive, and neither component is printed. Similarly, the claim that the occasional five-name book arose “because the prefilter shrank the candidate pool” is not demonstrated.  
  Fix: print the two luck-ratio components and selected-count/deposit-window diagnostics; soften the causal wording until shown.

What checks out: anchor parity is correctly asserted in cell 21; Sharpe and volatility use the two-day strategy clock; the paired Sharpe bootstrap uses common blocks and `ddof=1`; plateau arithmetic in cell 29 is correct; skipped LOVO/null gates are correctly represented as failures rather than passes; and the heading’s eight-gate failure list matches cell 34 exactly.