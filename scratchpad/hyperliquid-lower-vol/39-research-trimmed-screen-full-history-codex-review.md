## Blocking

- **Cell 6; cell 0 robustness — the bootstrap cannot support the claimed family-wise bounds.** The 60-day forward targets overlap for 30 decisions, but date blocks contain only 15 decisions (30 days). The 90/180-day trailing scores are serially persistent too. Resampling shorter blocks breaks material dependence, so standard errors and max-T lower bounds can be too optimistic. Circularly joining July 2026 to July 2025 further assumes away the documented polling-regime change. Calling the bounds “controlled figures” after admitting the problem is incorrect.  
  **Fix:** recompute the existing screen with horizon-appropriate, non-wrapping date resampling (at least 30 decisions, with the longer score persistence considered) before retaining “15 of 16 clear”.

## Material

- **Cell 10; cell 0 finding 3 — the regime results are not separate polling-regime outcome samples.** Regimes are assigned from decision date only. For example, late-December “weekly 2025” decisions use forward 60-day outcomes reaching into the January–March regime; late-March decisions reach into dense April data. Thus the claim that weekly polling produced the strongest persistence confounds weekly trailing data with later, differently sampled outcomes.  
  **Fix:** restrict regime-labelled results to decisions whose full forward horizon remains inside that regime, or describe them strictly as decision-date cohorts and remove polling-regime comparisons.

- **Cell 4; cell 0 method — the stated trailing window is not strict.** The first return uses the mark before `(T-1-W, T-1]`, so its return interval can begin before the advertised 90/180-day window. This is not look-ahead, but it is especially consequential with weekly marks and means the score is not solely a W-day-window statistic.  
  **Fix:** either exclude the boundary-crossing event, or explicitly define scores as events whose *end* mark falls in the window and report the possible pre-window span.

- **Cell 0 findings 2–3 — several interpretations exceed the paired evidence.** “Trimming adds nothing” and “flat” imply equivalence; the simultaneous lower bounds merely fail to establish an improvement. The claimed old-vault Sharpe-trim “cost” uses a selected, unadjusted 95% interval from one of several cohort/regime comparison families; its own simultaneous bound is negative but does not establish harm. “A Sharpe score already normalises … removing them takes information out” is an untested mechanism.  
  **Fix:** say no trim improvement was detected under the stated family bound; describe the old-cohort result as exploratory; remove the mechanism claim.

- **Cell 0 finding 3 — “a weekly mark is itself a week’s average” is unsupported and inconsistent with cell 2.** The code retains the last observed poll on each UTC day; it is a snapshot, not an average. The relevant issue is coarse, irregularly observed returns plus highly overlapping targets and repeatedly unchanged trailing scores between weekly marks. The current caveat therefore understates the mechanical-dependence concern.  
  **Fix:** replace “week’s average” with an accurate description of an interval return between sparse snapshots, and tie the caveat to the invalid short-block inference.

- **Cell 0 finding 4 — “the young cohort carries it” is too strong.** Old vaults still show positive, family-bound-clearing associations for raw/10%-trimmed 180-day Sharpe and Sortino. Young and old screens use different date coverage (192 versus 102 decisions), and no comparison test is reported.  
  **Fix:** say the association is larger and more widespread in the young-panel estimate; do not attribute the full-sample result to that cohort.

## Minor

- **Cell 0; cell 4 — trimming examples are arithmetically wrong.** With the implemented `ceil(f × n)`, 13 events remove 2 at 10% and 4 at 25%, not one and three; 90 events remove 9 and 23, not 9 and 22. The implementation itself is correct.  
  **Fix:** correct the examples.

- **Cell 0; cell 2 — the density claim is unsupported.** Cell 2 reports roughly 0.86 retained mark-days per vault per day after daily aggregation, not “fifteen or more a day”; it also never establishes that marks are price-changing.  
  **Fix:** say that raw polling may be intraday, but this notebook reduces it to one last mark per UTC day; remove “price-changing” unless measured.

- **Cell 0 — the 75.8% young-row figure is not displayed in its cited outputs.** It is written into the manifest, but cell 12 only confirms that the manifest was written.  
  **Fix:** print the full-panel young share in cell 4 or cell 12 and cite that output.

## Checks that pass

- Cell 4 correctly keeps trailing inputs at or before T−1 and forward marks strictly after T; there is no direct trailing/forward return overlap or T-date signal leakage.
- Actual-mark staleness, last-observed-mark TVL eligibility, forward end freshness, and the minimum-mark checks are correctly implemented without forward-filling.
- Cell 6 genuinely resamples both date and vault dimensions, shares each draw across hypotheses within a screen, uses sample `ddof=1` for bootstrap standard errors, and has the correct lower max-T direction and add-one p-value construction.
- Cell 8 is a valid limited reachability check: the near-perfect target-copy oracle passes through the same panel and resampling machinery. It does not cure the short-block problem.
- The principal quoted full-screen and regime numbers match cells 4, 6, 8, and 10.

## Overall verdict

**DIAGNOSTIC, not yet trustworthy as evidence of 15 signal passes.** The event panel is substantially cleaner than NB38 and has no evident look-ahead defect, but the 30-day bootstrap blocks are too short for 60-day overlapping targets, and the regime interpretation crosses its own boundaries. The headline family-wise conclusion should not stand until those existing calculations are corrected.