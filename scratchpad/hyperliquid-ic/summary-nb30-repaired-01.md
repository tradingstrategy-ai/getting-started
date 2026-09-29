# NB30 repaired results

## What we learned

**The repair substantially weakens the claim that lower-quartile rolling return supplies new return-prediction information. It remains a useful exploratory downside diagnostic. We have not identified a steady-profit basket.**

[NB30](30-research-rolling-typical-profitability.ipynb) was repaired and rerun on 2026-09-19. The final execution completed all seven code cells in 305.54 seconds without errors. Deterministic checks and full-panel timing assertions passed. This summary supersedes the original NB30 conclusions and the earlier top-quintile claims.

## Corrected results

The table uses nominal seven-day return windows ending in the trailing 60 days. IC is average daily cross-sectional Spearman correlation. A positive drawdown IC means shallower subsequent observed losses. Forward returns are unannualised; these are descriptive group averages, not strategy backtests.

| Metric | 30-day return IC | 60-day return IC | 30-day drawdown IC | Top-group 30-day return | Top-group 60-day return |
| --- | ---: | ---: | ---: | ---: | ---: |
| Median rolling return M | 0.024 | 0.031 | 0.026 | -4.67% | -7.08% |
| Lower-quartile rolling return Q25 | 0.089 | 0.123 | 0.479 | -1.57% | -2.96% |
| Positive-window frequency P | 0.050 | 0.052 | -0.206 | -2.44% | -3.56% |
| Sharpe-like score | 0.056 | 0.069 | 0.043 | -0.83% | -1.51% |
| Lower volatility | 0.099 | 0.149 | 0.631 | -0.26% | -0.65% |

Source: [marginal results](_artifacts-rolling-typical-profitability/marginal-summary.csv). Each score has its own finite-feature set; use the [paired contrasts](_artifacts-rolling-typical-profitability/paired-block-contrasts.csv) for matched comparisons.

Q25's top group performs **1.03 percentage points better over 30 days and 2.53 points better over 60 days** than its remaining opportunity set. The important qualification is that the top group itself still loses money on average. Ranking less-bad outcomes is not yet evidence of repeatable profits.

After residualising Q ranks against historical growth, positive-window frequency and volatility, its return association is **0.00496 at 30 days and 0.00322 at 60 days**. The earlier 30-day figure was 0.0356. Its conditional drawdown associations remain **0.205 and 0.165**. Median return has negative conditional return associations, about -0.026/-0.030. The 7/30 Q neighbour has conditional return IC -0.018/-0.010. See [conditional results](_artifacts-rolling-typical-profitability/conditional-summary.csv).

This supports a mainly risk-related interpretation, with little incremental return information after those existing features. It does not establish that all possible nonlinear uses of Q are redundant. The repaired dates/labels and measurements changed together, so the IC decline cannot be attributed to one fix alone.

Paired Q-versus-P return IC differences are +0.039/+0.071; the descriptive 60-calendar-day block interval includes zero at 30 days and excludes zero at 60 days. However, the top-minus-rest return-spread improvement over P has intervals including zero at both horizons. Q does not outperform inverse volatility on point-estimate return IC or group-return separation. No significance claim across multiple researched settings is made.

## Young vaults and reference examples

- Same 92,008 rows, 530 vaults and **81,095 opportunity rows across 405 daily decisions**. The dates now explicitly mean midnight decisions from 2025-08-01 through 2026-09-09; the old source-date labels were one day earlier. No extra history was manufactured.
- Q25_7_60 is available on 81,071 opportunity rows across 489 vaults. There are 627 one-outcome rows; they remain included, not treated as strong independent evidence.
- Return labels are available on 76,241/67,979 rows, over 386/356 dates for 30/60 days. Observed drawdown labels cover 55,896/47,483 rows. Each group reports missing-label coverage separately.
- **StratWise:** 41 opportunity dates, Q>0 on 28, and only 22 dates with a measurable 30-day forward return.
- **Systemic L/S Grids:** 391 opportunity dates, Q>0 on 130, and 372 with measurable 30-day forward returns.

The reference counts are diagnostic, not portfolio picks. They show why imposing Q>0 would not automatically retain our examples throughout their histories. Across the finite opportunity set, Q>0 and P>=0.75 agree on **97.59%** of rows; a hard zero-Q floor largely repeats a frequency filter. See [references](_artifacts-rolling-typical-profitability/reference-vaults.csv) and [overlap](_artifacts-rolling-typical-profitability/q-frequency-overlap.csv).

## What was repaired

1. Lower-is-better orientation, fractional boundary ties, constant-score behaviour, complementary rest weights and labelled-weight denominators. Group averages now use the same evaluated dates.
2. Original observation timestamps and explicit T=source_date+1 midnight timing. Features use only marks strictly before T. Label entry equals the last feature mark, instead of a separately chosen future entry.
3. Raw observations are clipped at the label horizon before daily aggregation. A later same-day mark cannot hide a valid midnight exit. Actual elapsed spans and sparse label gaps are retained.
4. Mean drawdown integrates the final carried interval through T. The undocumented 5% Sharpe-like denominator floor is removed; zero/near-zero volatility makes the ratio unavailable.
5. Largest-event containment now identifies a positive single observed gain rather than the largest overlapping return window. Exact M=Q uses equality rather than a loose numerical closeness test.
6. Paired return tests no longer require drawdown labels. Both conditional horizons run; rank-deficient designs and numerical zero residuals are unavailable. Both M and Q receive daily cohort statistics.
7. Paired IC and group-spread contrasts, 60/90-calendar-day bootstrap intervals, reduced-overlap results, label coverage, actual spans and old/new tables are saved.

Verification covers unique/tied/constant scores, lower-is-better direction, missing outcomes, complementary weights, smooth/flat/jump paths, young and weekly observations, future mutation invariance, exact horizon exits and final drawdown carry. Full-panel assertions check decision cutoffs and feature/label entry agreement.

## Limits and next step

Reduced-overlap Q return IC remains positive (0.096 across 13 dates at 30 days; 0.165 across six dates at 60 days), but these are very few time observations. Historical research reuse, overlapping windows, retrospective universe selection and unobserved intragap losses limit generalisation. Original-plan analyses still missing are listed in the notebook: matched losing-vault case studies, individual-vault influence, period-stratified IC tables and conditional feature-complete comparator coverage. This repair is not a claim that every original research deliverable is complete.

The [basket plan](steady-profit-basket-plan-01.md) should now be understood as a **falsification experiment for allocation value**, not the deployment of a confirmed new return signal. Comparing Q weighting against P and volatility controls remains essential. No basket was run, no 20% CAGR was established, and no production strategy changed.

## Reproduction and preserved evidence

- [Builder](build_nb30_typical_profitability.py), [measurement helpers](nb30_diagnostics.py), [checks](test_nb30_diagnostics.py).
- [Current manifest](_artifacts-rolling-typical-profitability/manifest.json), [before/after table](_artifacts-rolling-typical-profitability/before-after.csv), [current tables](_artifacts-rolling-typical-profitability/results.md).
- Original outputs: `_artifacts-rolling-typical-profitability-superseded-01/`; original executed notebook: `30-research-rolling-typical-profitability-superseded-01.ipynb`.

Run with `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent scratchpad/hyperliquid-ic/30-research-rolling-typical-profitability.ipynb --timeout=1800`.
