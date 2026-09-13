## 1. Do the heading's claims match the outputs?

### Key new insights

- `sortino_shrunk` is the only gate PASS: supported. Cell 26 reports dense/sparse mean returns of `2.0147%` / `0.7125%` against incumbent `1.4161%` / `-0.5048%`, and dense median Martin `1.5781` against `0.8389`. Cell 28 confirms `{'sortino_shrunk': True, ...}`.

- Both composites fail, with dense median Martins `0.0782` and `0.0078`: supported by Cell 26. Both also trail the incumbent on mean return in both regimes. “The CAGR leg actively hurts” is an association from these two blends, not causal proof that the CAGR leg is generally harmful.

- The reach figures are reported as claimed: Cell 26 gives mean ages `545.13` versus `577.87` days and young-slot shares `35.19%` versus `0%`. However, the claim applies only to matched cache entries: the code silently excludes selected vaults absent from the life-statistics cache. It does not display a match-rate audit, so “top-6 slots” is not fully evidenced.

- “An order of magnitude above” is contradicted. Cell 26 gives sparse mean Martin `10.3275` and dense `2.6414`: about 3.9×, not 10×. The “15 dates” statement is supported.

### Summary of results

- Mean scorable-pool sizes are supported by Cell 24: incumbent `16.1728`, shrunk `41.6543`, composites `36.8642`. “Roughly two-thirds” excluded is loose: the incumbent has about 61% fewer candidates than `sortino_shrunk`, nearer three-fifths.

- Every displayed result-table value and gate label matches Cell 26 and Cell 28.

- The statement that all scores are subsequently backtested is not an NB14 output. It is supported by the pre-registered plan, not by this executed notebook.

### Robustness

- The overlap warning is correct: Cell 22 reports 81 screen dates, spaced two days apart, with 30-day forward windows.

- The equal-weight-versus-live-sizing warning is correct from the screen code and strategy configuration.

- The claims that this is “not a result” and that the CAGR conclusion is screen-level only are appropriate. The reference to a prior power calculation is not demonstrated by NB14 itself.

## 2. Correctness of the code that produced the numbers

The central score-form and timing claims are mostly correct.

- The screen reads inclusion, gate, TVL, incumbent, shrunk score, composite, and both inline-blend legs at `at = when - ONE_BAR` in `_build/build_14.py` lines 164–195. This is live-parity timing.

- The capacity threshold is correctly calculated as `$150,000 × 0.98 / 6 / 0.33 = $74,242.42`; Cell 22 reports `$74,242`.

- `sortino_shrunk_score` is bounded by `.clip(lower=0.0, upper=1.0)`, and `expanding_cagr_score` is likewise bounded. Therefore both composites and the inline `0.3/0.7` blend are bounded. The NB16 plan uses the same indicators and parameterisation.

- The cross-sectional prior is not, by itself, a look-ahead. `_build/blocks_evidence.py` line 180 takes the median at each timestamp only; the screen subsequently reads the resulting indicator at the preceding bar. Each raw Sortino at that timestamp uses trailing fresh events only. It does, however, assume every vault’s same-day mark was available before the next decision. That availability assumption has not been tested with a data-cutoff reconstruction.

There are material parity and robustness defects:

- **Ranking ties do not match `decide_trades`.** The screen uses:

  ```python
  top = sorted(pool, key=pool.get, reverse=True)[:K_MAIN]
  ```

  while `decide_trades` uses `sorted(candidates, key=lambda item: (-item[2], item[0]))`. The screen’s tie order inherits `inclusion_criteria`, which is built from a set. Bounded scores make ties, particularly ceiling ties, plausible. This can change the top six precisely at the cut-off. No output reports ties or verifies they did not affect a selected basket.

- **“Full basket” does not prove six valid forward-return constituents.** `basket_size == 6` is recorded before `forward_metrics()` silently skips a pair lacking a usable price window. The reported date count then counts full selections, not non-null forward outcomes. The current forward-filled universe may make this harmless, but the notebook does not assert it.

- **Age metrics silently omit unmatched selected vaults.** The relevant line is:

  ```python
  for pid in top if pid in inception_by_pair_id
  ```

  No assertion requires six matched inception dates, and the cache is merely required to exist. It is not fingerprinted to the current vault-price snapshot or backtest end date.

- **The screen is not the actual executable candidate set.** It omits `is_good_pair`, quarantine status, and closed-deposit-window exclusions used by `decide_trades`. This is an intentional ranking screen rather than a full backtest, but Cell 21’s “tradable pool” wording is too strong.

- The reported “Martin” is `30-day total return / 30-day ulcer`, not the conventional annualised Martin ratio. It is consistently applied to every rule, so it does not invalidate the pre-registered comparison, but the label should be more precise.

## 3. Statistical interpretation

The PASS/FAIL labels are correctly produced under the pre-registered implemented rule: at least five nominal full-basket dates in each regime, better mean forward return in both, and better dense median Martin. The plan explicitly makes this a descriptive gate, not an adoption rule, and the heading reflects that correctly.

“Passes cleanly” nevertheless overstates the evidence. The screen has 81 nominal dates, not the anchor’s 126 cycles: 15 sparse and 66 dense. With 30-day horizons and two-day starts, sparse windows almost completely overlap; the sparse screen span is only about one horizon. Even the dense subset has only a small number of meaningfully independent 30-day outcomes, not 66.

The sparse mean Martin of `10.33` deserves stronger treatment than the heading gives it. The methodology itself notes that mean Martin can explode when ulcer is near zero. More importantly, the sparse **mean forward return** is a required condition for PASS. Saying the dense figures are more trustworthy does not remove the sparse condition that helped create the PASS.

Thus the defensible interpretation is: `sortino_shrunk` cleared a descriptive, in-sample ranking screen and merits the already planned backtest; it is not evidence that the mechanism works. The later family-wise result of `p = 1.000` and no adoption is consistent with that limited interpretation.

## 4. What should be re-run or checked before these results are trusted

1. Make screen tie-breaking identical to `decide_trades`: sort by `(-score, pair_id)`. Log tied score groups, especially ties crossing ranks 6–7, then rerun NB14.

2. Assert that every selected constituent has a valid 31-day forward window; calculate basket returns from exactly six constituents and count non-null outcomes rather than selected dates.

3. Rebuild or fingerprint the NB13 life-statistics cache against the same raw-price snapshot and end date. Assert all selected slots match an inception date; report unmatched slots if not.

4. Perform a strict point-in-time reconstruction for several dates: truncate every vault series at `at`, recompute the cross-sectional prior and scores, and require exact equality with the stored indicator values.

5. Report paired rule-minus-incumbent forward-return differences with block-aware uncertainty, plus a non-overlapping-horizon sensitivity table. Keep the original gate unchanged, but stop describing its PASS as clean.

6. Either apply the deposit-window and other executable eligibility filters in a supplementary screen or relabel NB14 clearly as a score-ranking screen rather than a tradable-pool simulation.

## 5. Verdict

**RESULTS STAND WITH CAVEATS**

The displayed arithmetic, gate outcome, bounded score construction, and one-bar feature reads are supported. However, the claimed live-ranking parity is incomplete because the screen’s tie-breaking differs from `decide_trades`, and neither forward-basket completeness nor age-cache coverage is audited. The PASS is a descriptive in-sample screen result only; its sparse-regime contribution is far too dependent on overlapping observations to support “passes cleanly.”