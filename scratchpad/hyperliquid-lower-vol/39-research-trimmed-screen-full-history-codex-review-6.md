## Findings

- **Material — cell 6:** The four Sharpe trimmed-minus-raw comparisons are not computed on matched vault samples. `date_statistics()` independently applies each signal’s finite-value mask; the finite shares differ (`sharpe90_f00` 94.4% vs f10 93.9%, etc., cell 4). Thus each reported difference can combine a trimming effect with the effect of excluding vaults for which the trimmed Sharpe is undefined. Shared bootstrap draws do not make these comparisons data-paired.

  **Fix:** for each raw/trimmed pair and target, calculate both date-level Spearman statistics using their joint finite mask, then bootstrap that per-date difference. Report any loss of eligible candidates separately.

- **Minor — cell 6:** The fifth-review wording fix is incomplete in the executed output. It still prints “192 decisions tile into 2 full tiles plus remainders per draw”, which is false with random offsets and resampled tiles. The heading correctly uses 2.13 block-equivalents and describes the one-or-two-full-tile construction.

  **Fix:** replace that print wording with the heading’s corrected description.

- **Minor — cell 6:** Inclusion is recorded per decision and min/max coverage is displayed, but the assertion tests only the *pooled* first-and-last-block average. It would not catch asymmetric bias between the beginning and end that cancels in the average, nor enforce a stated per-date tolerance.

  **Fix:** assert first and last blocks separately (and, if the intended invariant is per-date coverage, assert an explicitly justified per-date tolerance). The current reported all-panel values themselves do not indicate an endpoint problem.

## Checks that pass

- The fifth review’s substantive resampling defect is fixed: selected tiles are no longer truncated. The variable draw lengths and reported coverage are consistent with that change.
- The old stale 45-decision comment is corrected.
- The trailing-span wording is now accurate: marks bracket the window and observed event-return span is approximately \(W-28\) to \(W\) days.
- NB38 comparison values are now displayed in cell 6, so the heading’s NB38 figures have a cited cell.
- Signal construction reads only through T−1; forward targets are deliberately future-looking and are not fed back into signals.
- The bootstrap resamples both date tiles and vault clusters, uses shared draws across the signal family and paired calculations, uses sample `ddof=1`, has the correct one-sided lower max-T direction, and add-one p-values are implemented correctly.
- Heading figures checked against cells 2, 4, 6, 8, and 10 match their cited outputs. The interpretive language is generally appropriately diagnostic and does not claim controlled inference.

## Overall verdict

**DIAGNOSTIC, with one material comparison-sample defect.** The full-screen descriptive association result and the repaired tiled-bootstrap coverage are supported by the displayed outputs. However, the “no trim improvement” conclusion is not cleanly supported for Sharpe-score trimming until raw-versus-trimmed correlations are recomputed on common eligible vault samples.