# Claude Opus 5 final review

Requested model: `opus` (resolved as `claude-opus-5`). Read-only review after the final raw-fresh-mark allocation rerun.

# Final review: Hyperliquid IC allocation correction (read-only)

## Verdict

The must-fix is genuinely closed: `simulate_allocator` now marks every held vault from the raw fresh-mark table, sells fresh-but-ineligible holdings at their observed NAV (13 instances in the fixed arm, 29 in adaptive), carries zero holding-days with a mark older than 14 days in any arm, and reproduces all three saved curves and the incumbent's prior-cycle figures bit-for-bit. The only remaining defect is a sentence in `summary-02.md` that misdescribes when the replay holds cash; the code is production-faithful and the "no improvement, no production change" conclusion is correct with margin.

## Verification performed

- Re-simulated all three arms in memory: equity curves identical to `equity-*.parquet`; CAGR/vol/Sharpe/MDD/positions/cash/stale match `allocation-metrics.csv` to 6 d.p.
- `observations.parquet` is exactly the raw `is_fresh` set (487,738 rows, no `(address, timestamp)` duplicates, all `share_price > 0`), so "raw fresh marks" is satisfied.
- All 65,466 fresh candidate rows have `features.nav` equal to the same-day raw mark (0 missing, 0 mismatches), so buys and sells fill at the same price the feature clock saw.
- Production (`hyper-ai.py:857-935`) builds candidates only from `inclusion_criteria`; anything unselected gets weight 0 and is closed. The research sell path matches.
- The greedy loop in `capped_weights` matches `_normalise_weights_size_risk_positions` (renormalise remaining, take largest, cap by concentration × investable and TVL, decrement, delete).

## Material findings

| # | Severity | Location | Failure (verified) | Smallest fix |
|---|---|---|---|---|
| 1 | Should fix (wording) | `summary-02.md` "Corrected allocation replay", sentence "keeps cash only when every remaining selected name is at its concentration or TVL cap" | False. In the fixed arm, 49 of the 54 rebalances that left >2% of budget uninvested had at least one selected name under its cap (mean 6.4% uninvested with 81 pp of aggregate cap slack). 26 Feb 2026: 16% of budget in cash while `0xfeab…` sat at 23.3% vs a 31.5% cap and `0xff91…` at 20.9% vs 33%. The pass is single descending order; excess flows only to names processed *later*, so cash remains whenever the lowest-weight tail is capped. This is what production does, so the code is right, but the 16.3% mean-cash column is being explained by the wrong mechanism. | Replace with: "Excess from a capped name flows only to lower-weight names still to be processed, as in production's `_normalise_weights_size_risk_positions`; cash remains when the tail of the ranking is capped even if earlier names have headroom." |
| 2 | Optional | `summary-02.md` same paragraph and NB04 cell 3 guard: "dark holdings retain their aged last NAV" | Describes a path that never executes post-fix: 0 holding-days in any arm with a last raw mark older than 14 days; every end-of-period holding is marked on 12 Sep 2026. Presenting it as a live limitation over-hedges. | Append "(no such holding occurred in this run)". |
| 3 | Optional (carried over from review 17, #4/#5) | `summary-02.md` "production two-day rebalance cadence"; `ic_research.py:184` `_incumbent_inputs` | 108 of 365 dates have zero fresh marks (median 0 marks/day to 15 Jan 2026, 452 after); all arms trade on 9 rebalances in that four-month span. Matched across arms, so not a bias, but "production cadence" overstates fidelity. `_incumbent_inputs` is still dead code with non-production constants. | One sentence of disclosure; delete the function. |

Not defects (checked): `nav_age_days ≤ 1` ⇔ same-calendar-day raw mark; stale = "no raw mark today", kept at last mark and excluded from budget; sparse-but-eligible holdings are never re-sized on a carried price; cost-basis and redemption/performance fee accounting on partial and full sales; cash assertion; `stale_positions` computed on post-trade holdings; empty-`fresh_marks` days degrade to hold-only correctly.

## Calibration of the allocation conclusion

- **"Effectively flat" is right but understates fragility.** Fixed arm: +18.0% in Feb 2026 vs incumbent +9.0%; ex-February the fixed arm is −12.6% versus the incumbent's −5.6%. 27 Feb alone is +12.6% of equity, from `0xfeab…` (+37% NAV in one day, 290% annualised 30-day vol) and `0xff91…` (+3.3%). `0xfeab…` was held at 23% of budget because the eight lower-vol names were TVL- or young-capped and the pass flowed their excess to it; pure inverse-vol would have given it 3%.
- **The inversion is episodic, not systematic.** The largest position was a >100%-vol name on 6 of 129 active rebalances; across all rebalances the weight share in >100%-vol names is 5.5% versus 9.8% of selected names. So the fixed arm's parity with the incumbent is one lottery ticket that paid; the defensible ordering is incumbent ≥ fixed > adaptive.
- **Incumbent unchanged by the fix** (2.9% / 20.1% / 0.24 / −15.4% identical to the prior cycle), confirming the correction touched only the collapsed-holding path.
- Absolute Sharpe and volatility for every arm are deflated by the 108 flat-equity zero-mark days; comparisons across arms hold, but these figures should not be compared with production backtests.
- "Neither candidate meets the 20–30% objective" and "no production change" hold under any convention; the predeclared next step (single low-risk ranking, one horizon, one capped rule, matched dates, then settlement replay) remains the right one.

## Choices to retain

- `simulate_allocator(observations=…)`: date-level last raw mark per address; mark all holdings from it; stale = no raw mark today; stale kept at last mark and excluded from the budget; fresh-but-ineligible absent from candidates and therefore sold at observed NAV.
- New buys only on a same-day fresh mark; no fabricated fills for sparse names; `written_at` audit only.
- `capped_weights` greedy loop as-is (production-matched), young cap on candidates only, equal-weight fallback below the 5% vol floor.
- `summarise_backtest` emitting `mean_cash_fraction` and `mean_stale_positions` so the summary table is reproducible from the CSV.
- Incumbent constants, NaN-gate exclusion and NaN-score → 0.
- The summary's conclusion and next-step paragraph, subject to the wording fix in #1.
