No blocking defects found.

**Material — cell 0 (headline caveat):** It says “the block lengths that fit this archive do not cover the 180-day persistence”. That is false: cell 6 explicitly runs 90-decision / 180-day blocks, which do cover the stated 180-day score window. The real limitation is that this leaves only 192/90 ≈ 2.1 effective block-lengths (implemented as three draws with the final block truncated), too few for dependable controlled inference.

Fix: replace with: “No block choice is both long enough to cover the 180-day score persistence and numerous enough for reliable controlled bootstrap inference.” The later robustness text already says this correctly.

**Minor — cells 0 and 6:** The code comment calls the 45-decision sensitivity “the trailing-score persistence length”. It is only 90 days; the longest score window is 180 days. This does not affect the computation.

Fix: describe 45 decisions as an intermediate 90-day sensitivity; reserve the persistence-coverage statement for the 90-decision run.

**Minor — cell 0 summary table:** `p` is reported as an “unadjusted add-one p” without saying it is directional/one-sided. Cell 6 computes the signed, one-sided upper-tail bootstrap p-value. The arithmetic is correct, but the label is incomplete.

Fix: label it “unadjusted one-sided add-one p”.

The second-review findings are otherwise addressed:

- The new 90-decision sensitivity is present, produces 15/16, and the result is no longer claimed as controlled family-wise evidence.
- Regime wording is correctly narrowed to forward-outcome containment; it explicitly admits trailing scores cross prior regimes.
- The trailing requirement now correctly says eight events / nine marks.
- The 90-day trailing count is correctly called event returns; the forward count is correctly describable as marks because each forward mark creates one return interval from the carried mark/path.
- The block-movement claim, forward-return range, and polling-density wording now match cells 6 and 2.
- The outputs support the cited 15/16 counts and the displayed 180-day bounds, including `sharpe180_f00` at 0.118 / 0.126 / 0.117.
- Signals use marks through T−1; forward targets start from the carried T mark and subsequently use `(T, T+H]`. I found no direct signal look-ahead.
- The bootstrap genuinely resamples both vaults and date blocks, shares draws across hypotheses, uses sample standard deviations, and has the correct max-T lower-bound direction. The limitation is effective temporal sample size, not its arithmetic.
- The oracle is a valid narrow reachability check. There is no “zero of thirteen” null result in NB39; its positive oracle result shows the machinery is not mechanically incapable of producing a positive bound.

Overall verdict: **DIAGNOSTIC.** The headline’s numerical result is supported as a *computed* 15/16 result under all three block choices, and its main non-controlled-inference caveat is appropriate. Correct the one contradictory headline sentence about 180-day coverage; after that, the interpretation does not overreach.