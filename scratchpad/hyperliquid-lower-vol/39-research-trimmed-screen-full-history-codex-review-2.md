## Blocking

- **Cell 6; headline and robustness text in cell 0 — the 15/16 “family-wise clear” conclusion is still not supported.** The 30-decision blocks now cover the 60-day target overlap and correctly do not wrap; the 45-decision sensitivity is also correctly implemented. But both are shorter than the 180-day rolling-score dependence: 45-decision blocks still share half of a 180-day trailing window across adjacent blocks. Cell 0 explicitly concedes that residual dependence leaves bounds understated. Therefore these cannot simultaneously be described as controlled family-wise lower bounds and used to support “15 of 16 clear”.

  **Fix:** retain the point estimates and label the 15/16 count as passing the *computed 30-/45-decision block calculation*, not family-wise evidence. A valid controlled conclusion requires an inference design that covers the longest material dependence; with this archive that may leave too few effective blocks to make the claimed conclusion.

## Material

- **Cell 0, section 3; cell 10 — “regime cohorts, each measured entirely on its own marks” is false.** The forward outcome is correctly contained within its regime, addressing the first review’s principal regime defect. However, a 180-day score for early dense-regime decisions still reads pre-April, non-dense marks. The regime screen is therefore outcome-contained, not wholly regime-contained.

  **Fix:** rename this section and its interpretation to “forward outcomes contained within their regime”; state that trailing scores may cross the preceding polling regime. Do not interpret the weekly/dense contrast as a wholly within-regime comparison.

## Minor

- **Cell 0, method; cell 4 — trailing eligibility is described as “at least 8 marks”, but the code requires 8 event returns, hence at least 9 marks.** The implementation is correct.

  **Fix:** say “at least 8 events / 9 marks”.

- **Cell 0, method; cell 4 — the reported “marks per 90-day window” are event counts.** `events90` is `len(np.diff(log(prices)))`, so the reported weekly median 12 means 12 return events and normally 13 marks.

  **Fix:** call these “event returns”, or add one when reporting marks.

- **Cell 0, section 1 and robustness; cell 6 — two block-sensitivity claims are numerically false.** The text says all bounds move by under 0.01, but `ret180_f00` moves from 0.0639 to 0.0763, a 0.0124 change. It also says 90-day blocks “widen every bound”; several bounds instead increase, for example `ret90_f00` 0.0183 to 0.0209.

  **Fix:** state that the passing set is unchanged, while bounds move in both directions, with the largest displayed change about 0.012.

- **Cell 0, section 1; cell 6 — the forward-return range is misattributed.** The sentence says the strongest 180-day Sharpe/Sortino scores correlate with forward return at 0.192–0.199, but 0.199 belongs to `ret90_f10`. The named 180-day Sharpe/Sortino scores are about 0.191–0.193.

  **Fix:** use the latter range, or explicitly expand the set being described.

- **Cell 0, opening; cell 2 — “raw polling is intraday” is not shown by the cited output.** Cell 2 shows the post-aggregation daily-mark density only.

  **Fix:** either print raw-observation density or remove that assertion. The revised “mark on most days” wording itself is supported.

## Checks that pass

- The first-review fixes for non-wrapping blocks, horizon containment of regime outcomes, strict trailing-event windows, corrected trim arithmetic, printed young share, and narrower causal/equivalence language were implemented correctly.
- Signal inputs stop at T−1; future outcomes use marks after T, with the carried mark only as the starting NAV. I found no direct signal look-ahead.
- The bootstrap does resample both vault and date dimensions, shares draws across hypotheses within each screen, uses `ddof=1`, and has the correct max-T lower-bound direction and add-one p-value construction. The problem is dependence length, not the arithmetic.
- The oracle is a valid narrow reachability check for a near-perfect target-copy signal.
- The displayed core 15/16 count, table values, cohort values, and corrected wording on the exploratory old-cohort result match their cited outputs, apart from the reporting issues above.

## Overall verdict

**DIAGNOSTIC.** The code and descriptive results are much improved, and the computed result is indeed 15 of 16 under both displayed block choices. But the headline is not yet justified as controlled family-wise evidence because neither block length covers the 180-day rolling-score dependence.