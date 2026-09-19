## Findings

1. **Severity**: blocking.  
   **Cell**: 0.  
   **What is wrong**: “**A candidate that clears the 15% ulcer constraint by only a few percentage points cannot be distinguished from a reporting artefact**”.  
   **Why it is wrong**: Cell 39 measures an anchor-only deletion sensitivity. It does not estimate, bound, or even identify the error in a candidate’s *relative* ulcer improvement: each candidate can hold different vaults, at different weights and dates, with a different stale-mark exposure. The 4.4–11.1% figures therefore cannot be used as a universal uncertainty band for NB21–NB24 ulcer differences.  
   **The concrete fix**: Replace the conclusion with a narrower statement: “The anchor’s measured ulcer is sensitive by 4.4–11.1% under these deletion rules. This is contextual caution, not a bound on any candidate’s relative ulcer improvement.” Remove downstream language saying a particular candidate is indistinguishable from artefact solely because it clears inside this band.

2. **Severity**: blocking.  
   **Cell**: 39.  
   **What is wrong**: `risk_of()` describes annualised volatility as being “on its OWN observed spacing”, but calculates `periods = 365 / median(spacings)` in `cycle_returns()`, then applies it to returns spanning unequal intervals after observations have been removed.  
   **Why it is wrong**: A return across a four- or six-day hole is treated as one return but annualised as though it were a two-day return whenever the median remains two days. Thus `cycle vol (own spacing)` is not valid annualised volatility on the retained irregular series; the displayed 4.3–11.7% volatility changes are not interpretable as stated. The table itself confirms only that the *median* spacing remains two days, not that every spacing does.  
   **The concrete fix**: Do not report annualised cycle volatility for the gapped curves, or calculate an explicitly irregular-time risk statistic using each actual interval length. Rename the existing figure if retained as an unannualised, deletion-sample dispersion diagnostic.

3. **Severity**: material.  
   **Cell**: 38.  
   **What is wrong**: Section 5 classifies a valuation timestamp using `gap_len`, where `gap_len` is the length of the entire maximal run: `gap_len = stale.groupby(run_id).transform("size")`.  
   **Why it is wrong**: On the first day of a run, whether it is ultimately a “5+ day gap” is only known from future marks. The sensitivity therefore uses future data to decide which earlier cycle observations to drop. This is permissible only as an explicitly retrospective full-run description; it cannot represent the stale information available at that cycle or support an operational interpretation.  
   **The concrete fix**: For the sensitivity, use point-in-time `mark_age >= 5`, or label every section-5 result as an ex-post “eventual 5+ day run” sensitivity and remove language implying it identifies contemporaneously known stale cycles.

4. **Severity**: material.  
   **Cell**: 0.  
   **What is wrong**: “A gap does predict a loss - **but only in the dense polling regime**” and “the entire effect is post-April”.  
   **Why it is wrong**: Cell 30 estimates sparse as -56.8 bps, in the same direction as dense, with a wide interval of [-265.0, +83.5]. That interval is compatible with a material negative sparse effect. The Robustness section correctly says it is consistent with low power as well as no effect; the headline contradicts that caveat. The explanation that silence was “normal cadence” and hence uninformative is also causal/mechanistic language not established by this analysis.  
   **The concrete fix**: State that the five-day estimate is negative in both regimes, but the bootstrap interval excludes zero only in the dense segment under this resampling scheme. Remove “only”, “entire effect”, and the causal cadence explanation.

5. **Severity**: material.  
   **Cell**: 0.  
   **What is wrong**: “The universe carries outright dead vaults” and “These vaults are still candidates on every decision date.”  
   **Why it is wrong**: The analysis deliberately defines an unchanged daily mark as both a potentially unpolled mark and a genuinely unchanged polled mark. It cannot establish that a vault is “outright dead”. Nor do cells 22–26 inspect the per-date inclusion set, quarantine state, deposit window, or other filters needed to establish that every such vault is a candidate on every date.  
   **The concrete fix**: Say “vaults with long unmoved-mark runs” and limit the claim to their presence in the trading universe. Remove the unsupported every-decision-date candidate claim.

6. **Severity**: material.  
   **Cell**: 0.  
   **What is wrong**: “This biases every staleness figure **upwards and therefore biases the section-5 sensitivity upwards too — the +4.4% is an upper bound**.”  
   **Why it is wrong**: Misclassifying genuinely flat days does inflate the count labelled stale, but it does not imply a direction for the ulcer deletion sensitivity. Dropping additional observations can raise or lower an ulcer index depending on their place in the path and the returns spliced across them. The observed +4.4% is not mathematically an upper bound.  
   **The concrete fix**: Retain the correct statement that the staleness *counts* may be overstated, but say that the direction of the resulting sensitivity bias is unknown.

7. **Severity**: material.  
   **Cell**: 0.  
   **What is wrong**: “A long quiet run followed by a red mark is a real loss reported late, not a print that bounces.”  
   **Why it is wrong**: Cell 33 shows that 54.0% of these recorded events do not return to the pre-gap level within 30 calendar days; it does not establish when the economic loss occurred, whether the gap was missing reporting rather than genuine flat performance, or whether the control is “otherwise comparable”. The control has a different preceding-gap and return-size composition and is not matched or adjusted.  
   **The concrete fix**: Use: “In the recorded mark series, 54.0% did not revisit the pre-gap level within 30 days; this is descriptive and does not identify when or why the loss occurred.” Remove “real loss reported late” and “otherwise comparable”.

8. **Severity**: material.  
   **Cell**: 0.  
   **What is wrong**: “129,083 vault-days and 71,539 fresh marks were tabulated” is attributed to “cells 22, 24, 25, 26”.  
   **Why it is wrong**: In the executed notebook, cell 22 loaded an existing cache and printed no row counts; cells 24–26 do not print either total. The cited output therefore does not contain those figures. This breaches the stated cell-citation requirement.  
   **The concrete fix**: After either cache path, print `len(daily_marks)` and `len(mark_events)` in cell 22, then cite cell 22 alone.

9. **Severity**: minor.  
   **Cell**: 30.  
   **What is wrong**: The prose says the bootstrap resamples “calendar days”, but the code creates blocks from `pd.factorize(frame["date"])`: only dates with at least one event appear in `unique_dates`.  
   **Why it is wrong**: If a calendar day has no fresh marks, it is omitted and adjacent entries in a block need not be adjacent calendar days. This is not shown to affect this realised sample, but the implementation does not guarantee its stated design.  
   **The concrete fix**: Construct the complete calendar range for each segment and retain empty dates in the block index; map each selected date to zero or more events.

## Claims that are correct but could be worded more carefully

- Cell 30’s long-gap versus unconditional comparison is not invalid merely because the unconditional population includes long-gap events. It is a pooled-mean estimand and the bootstrap preserves that membership within each draw. It is mechanically diluted, not manufactured; with 1,275 long-gap events among 41,045, the dilution is small. Cell 27 usefully presents the 0–1-day comparison as an additional reference. An explicit acknowledgement would improve clarity.

- The recovery arithmetic in cell 33 is sound: the forward maximum correctly uses the next 30 calendar days, truncated events are separately reported, and the quoted 46.0% and 74.9% values match the output. “Does not reverse” is rhetorically stronger than necessary because 46.0% do recover.

- “All excluding zero” in the block-length sensitivity should be qualified as “under the stated calendar-date block-bootstrap assumption”, especially as the notebook itself notes that recurrent vault identities are not resampled.

## Sections found clean

- Anchor parity, provenance, and the cited cell-20 figures are correct.
- The census arithmetic in cells 24–26, including 38.1% and 34.9%, matches the displayed output.
- The five-day whole-window and regime-specific bootstrap values quoted from cell 30 are accurate.
- The bootstrap does preserve long-gap and unconditional samples within the same date draw, preserves all same-day cross-sectional events, has no wrap-around, and truncates each draw correctly to `n_dates`.
- The anchor-book figures in cells 35–36, including the 15.7% capital-day exposure and named-position values, match their cited output.
- The notebook repeatedly and correctly labels cycle dropping as a sensitivity rather than a correction; the issue is the invalid irregular-spacing volatility calculation and the overextended downstream interpretation, not that disclosure.