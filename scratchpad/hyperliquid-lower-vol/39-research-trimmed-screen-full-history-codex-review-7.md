## Findings

- **Material — cell 6:** The tiled-bootstrap coverage check measures raw inclusion counts, but the statistic is a mean normalised by each draw’s variable length. Since whole tiles are retained, draw lengths vary (203.3, 208.6, and 221.5 decisions). A date’s effective weight is therefore `multiplicity / draw_length`, not its raw multiplicity. The reported coverage and endpoint assertions do not establish equal effective date weighting for the statistic actually bootstrapped. This affects all standard errors, max-T bounds, and paired intervals.  
  **Fix:** accumulate and report per-date `1 / len(index)` for every selected occurrence, normalise that effective-weight vector, and assert the intended coverage tolerance on it (including all dates, not only endpoint averages). If it fails, change the tile sampling/weighting scheme and rerun.

- **Minor — cell 0:** “This screen has three times the decisions” overstates the displayed comparison: NB39 has 192 decisions and NB38 has 70, or **2.74×**, not 3×.  
  **Fix:** say “2.74 times as many decisions” or “nearly three times”.

## Sixth-review checks

The substantive matched-comparison correction is correctly implemented. Cell 6 computes each raw/trimmed pair’s Spearman values on the joint finite mask of raw score, trimmed score, and primary target; the displayed matched/unmatched values and matched candidate counts support the heading.

The stale tile-count wording is corrected, and the first and last endpoint averages are now asserted separately. However, the assertion is on the wrong weighting quantity for a variable-length bootstrap draw, so it does not complete the coverage validation.

## Checks that pass

- Signal construction reads only through T−1; forward outcomes are future-looking targets and are not fed into signals.
- Event-time construction avoids daily zero-filling.
- Vault and date dimensions are both resampled, with draws shared across the signal family and paired comparisons.
- Sample `ddof=1`, one-sided lower max-T direction, and add-one p-values are correctly implemented.
- The oracle assertion executes and demonstrates that the machinery can certify an intentionally near-perfect target-derived signal; its scope is appropriately only reachability.
- Heading figures checked against cells 2, 4, 6, 8, and 10 match their cited outputs apart from the “three times” rounding claim.
- The heading’s diagnostic language generally does not overclaim controlled inference; it explicitly acknowledges the insufficiency of 2.13 long blocks.

## Overall verdict

**DIAGNOSTIC, with one material bootstrap-weighting validation defect.** The sixth-review paired-mask fix is sound, but the revised coverage check does not validate the weights used by the variable-length tiled bootstrap. The reported bounds and “15 of 16” result need that correction and rerun before being relied upon.