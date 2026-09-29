## 1. Do the heading's claims match the outputs?

### Key new insights

- The census claim is numerically supported: Cell 22 reports 601 Hypercore vaults and 339 curator-admitted; Cell 26 reports 225 of 336 price-history-bearing tradable vaults never receive `cagr_sortino_weight` (67%). However, “336 vaults in the trading universe” is imprecise: Cell 24 says “Vaults in the trading universe **with price history**: 336”; the built universe contained 339.

- “Created downstream by CAGR alone … Sortino costs 13” is not supported as a causal decomposition. Cell 26 reports 210 never-valid `cagr_score`, 13 never-valid `sortino_score`, but 225 never-valid composite. Those figures cannot support an additive explanation: the composite has 15 more never-valid vaults than CAGR alone, despite only 13 never-valid Sortino legs.

- The hard-binding claim is supported for this run. Cell 28 reports 96 matched positions, minimum entry age 361 days, mean 511.7 days, and zero positions below 360 days.

- “Every vault launched after 2026-04-01” is supported only for the 336-vault price-history subset: Cells 24 and 26 report 43 of 43. It is not demonstrated for all 339 curator-admitted vaults.

- The hidden/scorable median Sharpe and CAGR figures are reproduced in Cell 30: -0.432 versus +0.136 Sharpe and -24.456% versus -19.027% CAGR. Their interpretation is unreliable because of the faulty `sharpe_t` construction discussed below.

- The headline “2 of 32 at tradable size have `t > 2`” is reproduced by Cell 30, including Cold Process at 3.209 and Stratwise at 2.703. The output supports the count, not the claim that either Sharpe is statistically resolvable.

- The post-April five-vault table and the one qualifying name are supported by Cell 32. But “below the track’s 30% floor” contradicts Draft 2: the pre-registered floor is 20%, explicitly lowered from the previous 30% floor. Stratwise’s 27.2% CAGR clears the current floor.

- The NB78 comparison is numerically reproduced by Cell 34: top-quartile median down-day share is 0.337455 versus 0.346450, stale share 0.037144 versus 0.160463, and median `sharpe_t` 1.216 versus 2.350. It does not establish that high Sharpes are “not NB78 fakes”; there is no uncertainty test and the cohorts are mechanically confounded by the polling-regime break.

- The decision-screen result is reproduced by Cell 39: capacity-filtered dense mean return is +1.416% for the incumbent and -2.582% for the short-CAGR rule, a 3.998 pp difference; dense median Martin is 0.839 versus -0.786. Cell 41 correctly reports that the implemented gate fails.

### Summary of results

- The curator-stage counts are supported by Cell 22. “Denylist / sub-vault / risk: 23” is correctly the sum of 15, 7, and 1.

- The barrier table is reproduced by Cell 26, subject to the non-additivity problem above.

- The five post-April names and figures are supported by Cell 32, but use a hindsight, end-of-window `$50,000` size filter rather than the screen’s decision-date `$74,242` capacity rule.

- The capacity-filtered screen table is supported by Cell 39. The “wins one of four cells” statement is also supported by Cell 41: sparse Martin is the sole `True`; both return comparisons are `False`.

### Robustness

- The 15 sparse and 66 dense decision-date counts are supported by Cell 39.

- “Roughly 8 non-overlapping observations per regime” is contradicted by the dates. Sparse decisions run only from 2 March to 30 March: all 15 30-day forward windows substantially overlap, giving approximately one independent sparse forward interval, not eight. Dense decisions span roughly 130 days, giving only about four non-overlapping 30-day intervals.

- The hindsight/decision-aligned distinction is mostly respected: life metrics use each vault’s full realised life, while the screen reads signals at `when - ONE_BAR`. However, the screen does not reproduce all execution eligibility and sizing rules, so it is decision-aligned for features, not for tradable portfolio outcomes.

- The autocorrelation caveat is directionally right, but understates the more basic defect: the reported Sharpe and the stated sample size are not computed from the same observations.

- The inverse-volatility and equal-weight caveats are correct and important. They mean the screen cannot establish that a 90-day-CAGR strategy would have produced the reported portfolio result.

## 2. Correctness of the code that produced the numbers

The central statistical calculation is incorrect.

```python
fresh = r[r != 0.0]
...
"life_sharpe": float(r.mean() / r.std() * np.sqrt(365))
```

`life_sharpe` uses all returns, including zero-return marks, while `add_sharpe_error()` treats `fresh_days` as its `n`. Lo’s IID form is only applicable when the Sharpe and `n` describe the same return sample. Here they do not. This invalidates the “t > 2” interpretation and all claims based on “resolvable” Sharpes.

There is a further timing issue: `daily = prices.resample("1D").last().dropna()` drops unpolled calendar days. Before the dense regime, a return can cover multiple days but is annualised as a one-day return. This makes the life Sharpe and its standard error particularly regime-dependent.

The life-statistics cache is unsafe:

```python
if life_cache_path.exists():
    life = pd.read_parquet(life_cache_path)
```

`/tmp/hyperliquid-lower-vol-vault-life-stats.parquet` has no data-snapshot fingerprint, source hash, or `backtest_end` validation. A later notebook can silently reuse stale statistics. The extract cannot prove that it did, so all life-statistic results need provenance verification.

The universe census is plausible and its count matches the built universe, but it does not assert address-level equality between:

- the cached `build_hyperliquid_vault_universe()` result;
- the metadata file read directly in Cell 22; and
- the final loaded trading universe.

Matching 339 counts is not proof of matching constituents.

The screen correctly avoids direct feature look-ahead:

```python
at = when - ONE_BAR
...
indicator_series_for(...).asof(at)
```

and `short_cagr_score()` slices only through `at`. That part is sound.

But it is not execution-parity screening. It omits dynamic `can_deposit()` checks, quarantines, incumbent holding protection, inverse-volatility availability, inverse-variance sizing, concentration caps, fees, cash constraints, and turnover. The screen’s capacity threshold guarantees only an equal one-sixth allocation:

```python
CAPACITY_TVL = initial_cash * allocation_pct / 6 / 0.33
```

It does not guarantee capacity for the actual inverse-volatility portfolio, where a position can approach the 33% book-weight cap and hence require nearer `$147,000` TVL.

`MIN_FULL_BASKET_DATES = 5` is defined but never applied. It did not change this extraction because every displayed rule has full-basket rate 1.0, but it is a silent guard failure.

The claim that an unscored vault “never reaches a basket slot” is too absolute. `require_scored_candidates` is `False`, and the shared decision function explicitly assigns an unscored candidate signal `0.0`; such a vault can be selected if the scored candidate set is inadequate. Cell 28 shows that it did not happen here, not that it cannot happen.

The known NB18 diagnostic overwrite is real in the shared base:

```python
state.visualisation.add_calculations(
    timestamp,
    {'unallocatable_signals': alpha_model.get_unallocatable_signals()}
)
```

This is `_build/cell14_enhanced.py:601`. It overwrites same-timestamp diagnostic data rather than merging it. It does not alter NB13’s displayed census or screen figures, but it confirms that shared diagnostics need explicit collision checks.

## 3. Statistical interpretation

The numerical screen verdict is justified only as a directional diagnostic: the 90-day rule loses both dense-regime metrics and fails both mean-return comparisons. It is not evidence of a statistically estimated 4.00 pp effect.

The current Draft 2 adoption rule is seven backtest constraints, including cycle Sharpe, volatility, ulcer, beta, deployment, and the placebo frontier. NB13 executes none of those. Its screen gate is not an adoption test.

Moreover, Draft 2’s later descriptive screen gate requires better mean forward return in both regimes and better dense Martin. NB13’s code requires all four comparisons, including sparse Martin. That is stricter, though immaterial here because the short rule already fails both return comparisons.

The sparse regime cannot bear an independent-regime verdict: 15 dates at two-day spacing with 30-day outcomes are almost one overlapping observation. The dense regime is also heavily overlapped. Neither mean return nor median Martin has a confidence interval, block bootstrap, clustered standard error, or non-overlapping sensitivity analysis.

The hindsight distinction is conceptually recognised, but the headline overreaches it:

- Whole-life Sharpe, CAGR, stale share, and down-day share are hindsight descriptions, not selection evidence.
- The hidden cohort is disproportionately post-April and therefore observed in the dense polling regime; the scorable cohort contains much more sparse history.
- Consequently, the apparent marking-quality difference and the NB78-signature comparison are confounded by the measurement regime.
- Selecting high-Sharpe names from 32 vaults and then declaring `t > 2` “distinguishable from zero” also ignores multiple comparisons, even if the statistic had been computed correctly.

## 4. What should be re-run or checked before these results are trusted

1. Rebuild life statistics from the exact raw-price snapshot, with a cache key containing source fingerprint and end date; assert it was not reused stale.

2. Recompute life returns on a coherent event-time or calendar-time basis. Calculate Sharpe, its Lo-style error, and `n` from exactly the same observations; account for irregular polling intervals and autocorrelation.

3. Assert address-level equality among the curator result, census admissions, loaded universe, and the 336-vault history subset. Report the three missing-history vaults.

4. Reconcile the barrier union: identify the 15 composite-only failures beyond the 210 CAGR failures and correct the causal wording.

5. Re-run the screen with exact decision-function eligibility: deposit status, quarantine, zero-signal behaviour, holdings, sizing availability, concentration/pool limits, and execution costs. Then run the actual 90-day variant if it remains a valid diagnostic.

6. Report block-bootstrap or non-overlapping-window sensitivity, especially separating the effectively single sparse forward interval. Remove claims of statistical resolution unless they survive the corrected calculation.

7. Amend the heading: use Draft 2’s 20% CAGR floor, label `$50,000` as an end-date descriptive filter rather than tradable capacity, and soften the NB78 conclusion.

## 5. Verdict

**RESULTS UNRELIABLE.**

The census and dense-screen arithmetic appear reproducible, and the directional dense-screen failure is informative. But a central headline claim—only two hidden vaults have statistically resolvable Sharpe—is computed with mismatched returns and sample size, potentially stale cached inputs, irregular polling treated as daily returns, and no multiplicity control. The cohort-quality and NB78 conclusions are additionally confounded by the sparse-to-dense polling break.