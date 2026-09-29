## Findings

- **Material — cell 0 finding 1; cells 34 and 38.** “The same one name, held a little larger” is not supported. The cited peak weight is identical for the main position in anchor and ranker (32.37%); the 48.5% versus 41.9% figures are positive-P&L shares, not exposure.  
  **Fix:** retain the separate retention and P&L-share diagnostics, but remove the exposure claim.

- **Material — cell 0 finding 3; cell 46.** `thr175` is called “the same book as 1.5”, yet its mean crash-filter survivor count differs from `thr150` (137.49 versus 135.54). Equal displayed performance metrics do not establish identical candidate or held books.  
  **Fix:** say the two thresholds produced identical displayed track-window metrics, not the same book.

- **Material — cell 0 findings 5–6; cells 42, 44 and 48.** Several causal/general claims outrun the evidence:
  - The unlimited book is described as the sizing rule’s stale-mark bias, but the run changes capacity and implementation as well as exposure to sparse marks.
  - “The quality floor removes the vaults that earn” and that comfortable qualifiers are the low-return universe are too broad. Cell 44 shows a major profitable anchor position with quality 3.01, and the displayed runs do not identify a cross-sectional return effect of qualification.
  
  **Fix:** frame these as consistency statements about the realised implementations. Name the lost June–August engine exposure specifically; do not generalise to all winners or qualifiers.

- **Material — cell 0 final interpretation; cells 34 and 36.** “Inherit every property of the anchor” and “the result is two names” remain overclaims. The evidence shows high overlap, a shared major position, about 64% of positive P&L from the largest vault in `thr150_n4`, and substantial—but not exclusive—drawdown contribution from two positions.  
  **Fix:** describe shared exposure and concentration using those measured shares.

- **Minor — cell 0 opening summary; cell 28.** The lead summary says leads were “REJECTED or left NOT CONFIRMED”, omitting `nocap`, which was UNEVALUATED because its plateau and mask were not run.  
  **Fix:** include UNEVALUATED.

- **Minor — cell 0 finding 7; cell 48.** “Deploys no more than intended” is only demonstrated for mean realised versus mean intended deployment. The calculation does not establish that inequality decision by decision.  
  **Fix:** say “mean realised deployment was no greater than mean intended deployment”.

## Checks that pass

- The quality score is causal at the T−1 interface, uses row windows, and handles forward-filled marks correctly. Its documented boundary difference from NB39 is real and accurately stated.
- The floor placement, empty-book close-out path, sleeve arithmetic, splice guards, and anchor inertness are sound.
- The aligned attribution is properly limited to disputed-cycle P&L contribution, not a counterfactual.
- Plateau neighbour chains and endpoint treatment are correct; old-lead plateau rereads remain framed as assumption checks.
- The fifth-round scoping repairs hold: mask diagnostics are separate, the floor agreement check is correctly limited to ten six-slot runs, and the sleeve is not presented as independently responsible for the result.

## Overall verdict

**Not ready to sign off on the interpretation.** I found no blocking calculation, look-ahead, floor-placement, sleeve, or gate-construction error. The remaining issues are material prose overclaims plus two minor scope/precision corrections; the executed results themselves remain usable once those are corrected.