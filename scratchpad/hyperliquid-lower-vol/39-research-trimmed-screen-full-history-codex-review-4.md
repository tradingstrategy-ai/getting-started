No blocking defects found. The headline is supported as a descriptive, explicitly non-controlled diagnostic: cell 6 does compute 15/16 positive bounds under each displayed block choice, and cell 0 now clearly disclaims controlled family-wise inference.

Findings:

- **Material — cell 4:** A “90/180-day” trailing score need not cover its stated calendar window. `i_first` is merely the first mark after the window start; the code requires a mark before the start but places no freshness limit on that first in-window mark. A vault can therefore have eight closely clustered late events after a long unobserved gap, while its return and volatility are annualised over the full 90/180 days. This changes the estimand and can create a score driven by a much shorter effective history.  
  **Fix:** require the first in-window mark to be within the declared staleness tolerance of the window start, or report and enforce an explicit minimum observed-span condition. Otherwise describe these as “up-to-W-day observed-event scores”, not W-day scores.

- **Material — cell 4; cell 0, section 4:** The young/old split is not vault age. `born = mdays[0]` is calculated after `df` has been truncated to 2025-01-01, so any vault already present before then is assigned a falsely recent birth date. The reported 75.8% young share and the young-versus-old interpretation are therefore shares by archive-observed age, not actual vault age. In particular, “the incumbent’s 360-day CAGR leg cannot score a young vault” does not follow for a vault whose pre-2025 history was discarded.  
  **Fix:** derive each vault’s first mark before applying the 2025 cut-off, if the archive contains it. Otherwise rename the cohorts to “observed for <360 days in this archive” and remove claims about true vault age or the incumbent’s history requirement.

- **Material — cell 6; consequentially cell 10:** The non-wrapping moving-block bootstrap severely underweights the temporal endpoints at the 90-decision setting. Starts are restricted to `0..len(dates)-block`; with 192 decisions and 90-day blocks, the first and last dates occur in very few eligible blocks while central dates occur in nearly all of them. The truncated third block worsens this imbalance. Thus bootstrap replicates are not resamples of the equal-date full-panel estimand, particularly across the changing polling regimes. The existing caveat correctly says the result is not controlled inference, but calling the 180-day result an “honest check” is too generous.  
  **Fix:** do not interpret these current long-block bounds as inferential robustness evidence. If retained, replace the resampler with a non-wrapping construction that preserves full-date coverage and document its weights; apply the same correction to the short regime cohorts.

- **Minor — cell 6:** The third-review comment fix was not applied. The source still says the 45-decision sensitivity is “the trailing-score persistence length”, although it is only 90 days and cannot cover the 180-day score window.  
  **Fix:** change it to “an intermediate 90-day sensitivity”; reserve persistence coverage for the 90-decision run.

- **Minor — cell 0:** “About 3 blocks per draw” describes the implementation’s `ceil(192 / 90)` draws, but overstates the effective information: it is two complete 90-decision blocks plus a 12-decision truncation, about 2.13 block-equivalents. This conflicts with cell 2’s more accurate “about two blocks per draw” comment.  
  **Fix:** state the two full blocks plus truncated third block explicitly.

- **Minor — cell 0 citations:** Several cohort-age figures are attributed only to cell 10, although 75.8% overall young share and 99.2% weekly-regime young share are printed in cell 4. NB38’s “70 decisions” and rho 0.136 are also not displayed in this notebook.  
  **Fix:** cite cell 4 alongside cell 10 for cohort percentages, and cite the precise NB38 cell or display the imported comparison value.

Checks that pass:

- Cell 4 keeps signals at or before T−1. Forward marks are strictly after T; there is no direct signal look-ahead.
- The event returns do not cross the trailing-window boundary, and trim arithmetic is now correct.
- Cell 6 resamples vault and date dimensions, shares draws across hypotheses within a screen, uses `ddof=1`, has the correct one-sided lower max-T direction, and uses add-one p-values.
- The third-review headline caveat and one-sided p-value label were correctly applied.
- Cell 8 is a valid narrow reachability check: the target-copy oracle clears the same full-screen machinery.
- The quoted full-panel point estimates, 15/16 counts, bounds, and trim figures match cells 4, 6, 8, and 10.

Overall verdict: **DIAGNOSTIC.** The revised headline does not overclaim controlled inference and is supported as a report of the executed calculation. The cohort-age analysis is materially mislabelled, and the bootstrap’s long-block endpoint weighting means its bounds should remain strictly descriptive until corrected.