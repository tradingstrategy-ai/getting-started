# NB23 independent review findings

Verdict: **REJECT is supported.** The centre’s complete failure set is correctly reported as five constraints plus the late period. I found no look-ahead error in the stage-1 audit, and the measured forward-fill count of zero is credible.

## Findings

1. **Material — cells 42–46: required target-weight identity diagnostic is absent.**

   The plan requires both target-weight and realised-weight L1 distances. The notebook explicitly elects to report only realised weights. The 10% gate itself correctly uses changed holdings (113/126), but the promised target-weight diagnostic was not implemented.

   Fix: retain and report per-decision target weights from the decision/alpha-model output, alongside the existing realised-weight calculation.

2. **Material — cells 18 and 63: bootstrap “observed Sharpe difference” uses a different standard-deviation convention from the reported Sharpe.**

   `panel()` obtains Sharpe through `calculate_sharpe`, while `bootstrap_paired_sharpe_diff()` uses NumPy `std()` with `ddof=0`. This produces the reported −1.582576 rather than the panel-consistent difference, \(0.583559 - 2.159792 = -1.576233\). With 125 cycles, the discrepancy is exactly consistent with the population-versus-sample standard-deviation scaling.

   This does not change the rejection: every reported lower interval still fails the −0.10 boundary. It does make the reported observed bootstrap margins internally inconsistent.

   Fix: use the same Sharpe implementation/convention as `panel()` for both the observed difference and every bootstrap draw, including sample `ddof=1`.

3. **Material — cell 33 and heading cell 0: the 57.3x figure is arithmetically correct but misinterpreted as reporting speed.**

   The ratio is `max(per-candidate median span) / min(per-candidate median span)`, i.e. 1,146 / 20 = 57.3. It is not a direct slowest-versus-fastest reporting-rate ratio. The extreme longest candidate has a median of only 37 window events, and the shortest has 21 events across only two reads; valid scores use an expanding **up-to-90-event** window, not necessarily a completed 90-event window.

   Therefore “the slowest-reporting vault” and “ranking a three-month ratio against a three-year one” overstate what this statistic establishes.

   Fix: describe it as the ratio of extreme candidate-level median spans among valid, up-to-90-event windows; alternatively restrict the reported dispersion to completed 90-event windows with sufficient reads.

4. **Material — cells 52, 57, 69 and heading cell 0: strict-admission equivalence is demonstrated for panel metrics, but its claimed explanation is not demonstrated.**

   The manifest verifies that `swap__centre` and `swap__require_scored` have identical stored panel metrics, including Sharpe to the quoted final digit. However, no cell reports selected positions with a NaN composite, selected-slot score validity, trade equality, or equity-curve equality. Thus “because a NaN-composite candidate … never wins a slot” is plausible from the selection code, but not established by the notebook.

   “Strict admission changes literally nothing” is also broader than the evidence shown.

   Fix: report the count of selected NaN-score candidates by decision date and assert equality of the two runs’ holdings, trades and equity series before making the causal explanation.

5. **Material — cells 70–73: integrity and redemption-fee audits inspect only the anchor, not the swap or sweep runs.**

   `state` remains the anchor alias assigned in cell 16. Consequently, “no destroyed or stranded positions” and “every vault redemption” apply only to the anchor despite appearing after the candidate results.

   Fix: iterate over `runs` and report the integrity and fee audit per label, or label these two outputs explicitly as anchor-only.

6. **Minor — cell 39 and heading cell 0: “saturate at the cap” is imprecise.**

   The arithmetic is correct: 47.5953% are floored at zero and 12.0856% are capped at one, totalling 59.6810% at either bound. But zero-bound and one-bound scores remain ordered relative to each other; only scores sharing the same bound are tied. “At a bound” is accurate; “no ordering information at all against any other saturated read” is not.

   Fix: say the score partitions 59.68% of reads into tied zero and tied one groups, leaving 40.32% strictly ranked between them.

7. **Minor — cells 48 and heading cell 0: drawdown attribution is incomplete for positions with fewer than two in-window statistics.**

   `profit_delta_by_address()` silently excludes such positions. Its output is therefore an approximate partial attribution, not necessarily the contribution of all changed holdings over an episode. The prose appropriately calls it approximate, but should disclose this omission.

   Fix: report excluded positions and their value, or calculate endpoint contributions with an explicit treatment for positions opened or closed within the episode.

8. **Minor — cell 55 and heading cell 0: “reproduce exactly” overstates the output.**

   The check passes at `1e-5`, but the displayed absolute differences are non-zero, up to \(3.43\times10^{-7}\).

   Fix: say “reproduce within the pre-specified 1e-5 tolerance”.

## Checked and clean

- **Forward-fill audit (cells 22–37):** correct. The reconstruction uses the same fresh-event subsequence, rolling windows, `min_periods`, down-count mask, and T−1 read timestamp as the shipped indicator. `searchsorted(..., side="right") - 1` selects the latest event available at the read. The equality assertion alone would not prove the mask positions, but the separately reconstructed `down_count` does test them. A zero bridge count is structurally plausible here: every valid read has a latest event window with at least five down events.

- **Span arithmetic (cell 33):** 113 days, 48–520 days and 10.83x are correct for the stated pooled valid-read statistic. Only the reporting-speed interpretation is defective.

- **Identity arithmetic (cells 44–46):** realised weights are compared at matching timestamps and each run is divided by its own contemporaneous total equity. The 113/126 set-change gate is correctly computed and exceeds 10%.

- **Clock and pairing:** volatility, Sharpe and beta use the two-day strategy clock; bootstrap resampling uses common paired block indices. No p-value is claimed in NB23.

- **Failure reporting:** the centre’s full set is consistently reported in heading cell 0, cells 59 and 67, and the frozen manifest: CAGR, Sharpe non-inferiority, ulcer, beta, observed control, and late period. The “not ulcer only” conclusion is correct.
---

# Verification of the review, and what was applied

Every finding above was checked against `_build/build_23.py`, `_build/blocks_evidence.py`,
`_build/blocks_stability.py`, `_build/harness_stability.py`, `_build/cell14_enhanced.py` and the
executed notebook's own output before anything was changed. Nothing was applied that was not first
reproduced. The notebook was rebuilt and re-run in full after the code changes; anchor parity, the
three previous-plan reference values and `_build/manifest_23.json` are all unchanged.

| # | Finding | Cells | Verdict | Applied |
|---|---|---|---|---|
| 1 | Target-weight L1 diagnostic absent | 42-46 | PARTIAL | markdown + robustness note |
| 2 | Bootstrap Sharpe uses `ddof=0`, panel uses `ddof=1` | 18, 63 | CONFIRMED, exactly | recorded, not changed (shared harness) |
| 3 | 57.3x described as a reporting-speed ratio | 33, 0 | CONFIRMED for the heading, not for the code | heading rewritten |
| 4 | Strict-admission equivalence explained but not established | 57, 59, 69, 0 | CONFIRMED | new measurement added to cell 59 |
| 5 | Integrity and fee audits cover the anchor only | 71, 73 | CONFIRMED | recorded, not changed (shared builder) |
| 6 | "Saturate at the cap" imprecise | 39, 0 | CONFIRMED | markdown + heading tightened |
| 7 | Drawdown attribution silently drops short-lived positions | 48, 0 | CONFIRMED | exclusion counted and printed |
| 8 | "Reproduce exactly" overstates a 1e-5 tolerance check | 55, 0 | CONFIRMED | heading corrected |
| 9 | "Six addresses the candidate held, the anchor never did" is measured wrongly | 46, 0 | CONFIRMED - the correct answer is **4**, not 6 | computation and heading fixed |

Finding 9 was found during verification and is not in the review above.

## The zero forward-fill measurement: genuine, not a measurement bug

This was the single most suspicious number in the notebook - a measured zero for a defect that
demonstrably exists in `_event_time_stats()`. It survives scrutiny on every axis checked:

- The reconstruction in cell 25 rebuilds `fresh_r = r[r.abs() > 0]` from the same `close` series,
  with the same `w = evidence_max_events`, the same `min_periods = evidence_min_events` on the
  mean, downside deviation and count, and the same `min_periods = 1` on `down_count`. It is the
  shipped helper's code, not a paraphrase of it.
- The condition tested is the right way round. `latest_window_fails_down_mask` is
  `down_count[latest event at or before the read] < evidence_min_down_events`, and `bridged` is
  `score_valid & latest_window_fails_down_mask` - a valid score whose *current* window FAILS.
- The equality assertion in cell 27 is **not** trivially satisfied. Both sides apply the same
  forward fill, but they apply it to differently-masked series: if the shipped `down_count` masked
  a position the audit's did not, the cached value at that read would be the older `raw[q]` while
  the rebuild would give the fresh `raw[p]`, and the two differ generically. The assertion
  therefore does constrain the mask positions, not only the ffill mechanics.
- The read timing is right. `READ_AT = decision timestamp floored to the bar, minus one bar`, and
  `events.searchsorted(READ_AT, side="right") - 1` selects the last event at or before that read,
  which is exactly the event whose value a forward fill would carry.
- Cell 37 now measures **why**, rather than asserting it: the down-event count behind the latest
  event window at a valid read has a minimum of **exactly 5** - the mask's own bar - a 1st
  percentile of 8 and a median of 37, and **0 valid reads sit below the mask**. Bridging is not
  merely absent on this pool, it is unreachable: a score only becomes valid after 20 fresh events,
  `down_count` only decreases once the window is full at 90 events, and no vault in this cohort
  ever runs a 90-event window with fewer than five down-moves.

The internal consistency check also holds: "valid score carried from an older event window for
*any* reason" is also 0, which is the strictly weaker condition, and the 292-day maximum evidence
age is a vault that stopped producing fresh marks at all rather than a bridged mask.

## What was changed in `_build/build_23.py`

1. **Cell 37** - the down-event distribution behind every valid read is displayed, with the
   minimum and the count below the mask printed. This is what turns the zero from an assertion
   into a measurement.
2. **Cell 46** - the held-address comparison is computed from the two runs' full books rather than
   by differencing the per-date exclusive columns. The old measure differenced `candidate_only`
   against `anchor_only`; an address held by *both* runs on the same date appears in neither
   column, so it counted as "never held by the anchor" even when the anchor held it on another
   date. The correct answer is **4**, not the 6 the heading claimed. Four extra rows now report
   both runs' full held-address counts and the difference in each direction.
3. **Cell 48** - `profit_delta_by_address()` returns the number of positions it skipped for
   carrying fewer than two statistics inside the episode window, and the total is printed: 398
   anchor and 309 candidate position-episodes across the five episodes.
4. **Cell 59** - the strict-admission equivalence is now measured. Strict admission would remove
   13,481 of 18,651 gated reads (72.28%), whose composite is NaN because the untouched 360-day
   CAGR leg is undefined, and the two runs' realised books and equity curves are bit-identical
   (largest weight difference 0.0, largest equity difference $0.00). The causal explanation is
   established rather than merely plausible.
5. **Markdown cells 38, 42, 47** - the saturation wording, the deliberate omission of the
   target-weight L1, and the partiality of the drawdown attribution.
6. **Cell 0** - rewritten for findings 1, 3, 4, 6, 7, 8 and 9.

## What was recorded rather than changed

- **Finding 2, the `ddof` mismatch.** Reproduced exactly: `sqrt(125/124) = 1.0040242` maps the
  panel difference `0.5835585952865023 - 2.1597920746960435 = -1.5762334794` onto the reported
  bootstrap observed `-1.582576`. `bootstrap_paired_sharpe_diff()` lives in
  `harness_stability.py`, which NB20-NB24 all share, and NB21's review already recorded the same
  finding for the same reason. No interval or `clears_boundary` flag moves: the centre misses the
  -0.10 boundary by 1.5, and a 0.4% rescaling is nowhere near it. Written into "Robustness of
  results" and flagged as a track-level fix.
- **Finding 5, the anchor-only integrity and fee audits.** `state` is the anchor alias bound in
  cell 16, so cells 71 and 73 do audit the anchor only. They come from `integrity_and_audit_cells()`
  in `_build/builder.py`, which every notebook in the track appends; changing it would alter
  NB03-NB24. Recorded in "Robustness of results" with the note that no claim rests on them.
- **Finding 1, the target-weight L1.** The plan asked for it; the notebook's cell 42 markdown had
  already declared that it reports realised weights only. That declaration is now explicit about
  the deviation and its reason - `decide_trades` does not persist alpha-model targets into the
  state - and the pre-registered gate quantity (the share of dates on which the *traded* book
  differs) is the one that was used.
- **Nothing pre-registered was moved.** The 2% forward-fill trigger and the 10% identity gate are
  where the plan put them.

## Also noted, below the threshold for a change

- Cell 71 rebinds the name `audit` from the stage-1a DataFrame to the integrity dictionary. It is
  harmless in the current cell order - the manifest is written in cell 69 - but it is a latent
  shadowing hazard in shared builder code.
- `max_abs_diff()` in cell 27 returns 0.0 when the two arrays share no finite position. The
  docstring says so, and the separate NaN-disagreement counter is what catches a real mismatch in
  where the score exists, so this is documented rather than silent.
