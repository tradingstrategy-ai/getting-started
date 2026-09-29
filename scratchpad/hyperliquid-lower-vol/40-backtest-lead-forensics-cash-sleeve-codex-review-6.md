## Findings

- **Material — cell 0, robustness coverage; cells 44 and 48.** The heading says poor quality-score coverage “does not explain” the lost June–August engine position because the position is measured. Cell 44 only shows finite scores at selected opening dates; cell 48 does not show the score or eligibility state at the 18 June exit. The notebook itself notes that the closing log entry is not printed.  
  **Fix:** say the displayed output cannot distinguish a below-floor score, later missing score, or another eligibility change at exit.

- **Material — cell 0, robustness checks; cell 40.** “Held-name exclusions are zero on every six-name and four-name threshold run, so the hysteresis and the exit threshold remain unverified by any result in this track” overstates the evidence. `thr150_nall_invvar` has one held-name exclusion on 2026-06-26. This does not verify hysteresis, but it does show the exit threshold firing once.  
  **Fix:** limit the zero statement to six-/four-name runs, and say the unlimited run supplies one exit observation, insufficient to assess the mechanism.

- **Minor — cell 0, final interpretation; cell 50.** “N = 3 and N = 5 also fail gate 7” is too broad for the capped filtered family: `thr150_n5cap` passes gate 7.  
  **Fix:** name the actual failing runs, or distinguish unfiltered N=3/N=5 and filtered N=3 from filtered N=5.

- **Minor — cell 0, finding 1; cells 34 and 38.** “One position dominates” is rhetorically stronger than the cited measures: the largest anchor position supplies 46.0% of net P&L and its vault 41.9% of positive P&L. The figures are correct.  
  **Fix:** prefer “is the largest contributor” unless “dominates” is explicitly defined.

## Checks that pass

The revised heading now correctly scopes the aligned attribution as an aligned P&L contribution, distinguishes `thr175`’s identical displayed track-window metrics from identical books, treats endpoints as unevaluated, and limits sleeve deployment to a mean-versus-mean claim.

I found no blocking calculation, look-ahead, floor-placement, cash-sleeve arithmetic, bootstrap, cycle-clock, or gate-construction error. The quality statistic and causal T−1 interface are sound; the floor’s offline reconstruction agrees on all ten six-slot runs.

## Overall verdict

**Not ready to sign off on interpretation.** The executed results remain usable, but the two material heading claims need narrowing before approval.