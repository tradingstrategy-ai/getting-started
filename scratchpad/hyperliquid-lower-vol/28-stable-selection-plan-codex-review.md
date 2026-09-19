## Overall verdict

The plan is not executable as an adoption protocol as written. The fresh-event construction is substantially better than Draft 27, and the per-date Spearman estimator can be a reasonable descriptive statistic. However, gate 5 currently has invalid uncertainty handling, uncontrolled signal selection, incomplete forward targets and same-window double selection. Several downstream gates also require definitions the executing agent would have to invent.

Line references refer to [28-stable-selection-plan.md](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/28-stable-selection-plan.md).

## Blocking findings

1. **Blocking — the final 30 days have no complete forward target**

> “Forward targets over `(T, T + 30 d]`” (lines 174–176)

The user-identified gap is confirmed. Decisions after approximately 2026-08-09 cannot have a complete target on data ending 2026-09-08. Treating truncated windows as complete would systematically give late dates shorter, less volatile outcomes.

There are further undefined details: the starting NAV observation, minimum fresh observations, zero positive-return denominators, and how an event straddling \(T\) is handled.

Concrete replacement:

- Only admit dates satisfying `T + 30 days <= last_available_timestamp`.
- Build returns from the carried NAV at \(T\), so no event contains pre-\(T\) return.
- Pre-register minimum complete fresh events for each target.
- Make zero denominators, insufficient events and non-finite targets explicit missing reasons.
- Print eligible dates and candidate-date counts per target; do not continue to claim 126 dates.

2. **Blocking — gate 5 has uncontrolled selection across 65 tests**

> “at least three of the four forward stability targets … interval excluding zero” (lines 185–189)

The second user-identified gap is confirmed. There are 52 stability hypotheses plus 13 return-harm hypotheses. Requiring three of four positives makes the within-signal rule more stringent than one isolated test, but it does not control selection across thirteen correlated signals. Passing signals are then the only ones backtested, so false passage directly affects the candidate family.

Concrete replacement: use common resamples for all 65 statistics and construct simultaneous one-sided max-\(T\) intervals, or apply a pre-registered family-wise correction to resampling-based p-values. Any p-values must use the add-one correction. Unadjusted intervals may still be printed descriptively.

3. **Blocking — “the wider interval governs” is not a valid clustered interval**

> “a block bootstrap over dates … AND a separate interval from resampling vaults … the wider governs” (lines 178–183)

Taking the wider of two marginal intervals does not produce two-way cluster coverage. “Wider” is also unsafe for the pass rule: a wider interval can have a higher lower endpoint than a narrower interval, causing a pass that the narrower interval rejects.

The ten-decision block is only about 20 days, shorter than the 30-day overlapping target horizon. Adjacent outcomes share most of their observations.

Concrete replacement:

- Use one joint procedure that resamples date blocks and vault clusters together and recomputes the entire nonlinear statistic.
- Use the same resamples across every signal and target.
- Use date blocks of at least 15 two-day decisions, with the exact moving/circular-block procedure specified.
- For a conservative two-interval fallback, use the minimum lower bound for positive claims and maximum upper bound for harm claims—not interval width.
- Pre-register a minimum number of usable dates. Thirty candidates on one date is not enough.
- Define percentile/basic/studentised interval construction and fail closed on constant-input or non-finite Spearman results.

4. **Blocking — the screen and portfolio evaluation select twice on the same returns**

> “which NB29 reads to decide what to run” (lines 196–200)

Procedural ordering—screen first, backtest second—does not make gate 5 out-of-sample. The 30-day forward returns used to choose signals overlap the returns subsequently used to judge their portfolios. NB30 adds a third selection layer by combining only signals whose same-window portfolio centres already passed.

This is worse than testing a pre-registered fixed mechanism once: the data now select the mechanism, select the successful portfolio variants and evaluate the selected result on the same history. `family_wise_joint()` cannot repair the upstream screening.

Concrete replacement: separate signal selection and portfolio evaluation temporally, with at least a 30-day purge between them, or use nested rolling-origin/cross-fitted evaluation where every reported portfolio outcome comes from a fold that did not select its signal. If the window is too short, NB28–NB31 must remain hypothesis generation and no configuration should be admitted until a prospective shadow period.

5. **Blocking — the pass rule does not match research-rule gate 5**

> “at least three of the four forward stability targets” (lines 185–187)

The research rules name volatility, downside deviation and event concentration. The plan adds maximum drawdown and permits one of the four to fail. Consequently, a signal may fail one of the three mandatory targets but substitute maximum drawdown and pass.

Concrete replacement: require the three targets named in the research rules. Maximum drawdown may be an additional diagnostic, or `RESEARCH-RULES.md` must be explicitly revised before execution.

6. **Blocking — the return clause is a failure-to-reject rule, not non-inferiority**

> “its correlation with forward mean return is not negative with the interval excluding zero” (lines 185–189)

This only rejects a precisely estimated negative association. A materially negative but noisy estimate whose interval crosses zero passes. It therefore does not establish the claimed protection against choosing vaults that “do not earn”.

“Mean fresh log return” is also frequency-dependent: a weekly compounded fresh event is not comparable with a daily event. It is not a 30-day earning measure.

Concrete replacement: define a 30-calendar-day cumulative log-NAV return and a pre-registered non-inferiority margin \(\delta\). Require the lower confidence bound for the stable-versus-unstable return contrast to exceed \(-\delta\). The operator must supply \(\delta\); the executing agent must not invent it.

7. **Blocking — the null does not preserve the claimed NaN locations**

> “Preserves … the number and location of NaNs; destroys only which vault carries which value.” (lines 94–99)

Permuting `vals`, including NaNs, preserves the number of NaNs on each date but changes which vault is unmeasured. Under permissive mode, that changes which vault receives a NaN exemption; under strict mode, it changes which vault is automatically excluded. It therefore destroys availability assignment as well as finite ranking.

The resulting prefilter is computationally valid: `len(scored)` and hence the fraction-derived exclusion count remain constant. But it is not the claimed ranking-only null.

Concrete replacement:

```python
finite_ids = [i for i in ids if np.isfinite(values[i])]
finite_vals = [values[i] for i in finite_ids]
permuted = dict(values)
permuted.update(zip(finite_ids, rng.permutation(finite_vals)))
```

Keep NaNs attached to their original vault/date for a finite-ranking null. If strict-mode missingness itself is treated as information to destroy, specify a separate strict null and stop describing it as preserving NaN locations.

Also replace `v == v` with `np.isfinite(v)`; the current code admits infinities despite the fail-closed rule.

8. **Blocking — null-map distinctness does not prove ten effective draws**

> “prints the count of distinct `(date, vault, value)` mappings” (lines 51–52)

Different value mappings can generate identical excluded sets, identical top-six selections and identical return paths—especially when the prefilter removes candidates the incumbent would never select. This repeats the effective-null failure the rule is intended to prevent.

Concrete replacement: assert and print distinct counts for:

- complete signal mappings;
- excluded-set histories;
- realised selected-basket histories;
- cycle-return series.

Gate 9 must be false if fewer than ten effective null outcomes exist. It should be the strict finite comparison `centre_sharpe > max(null_sharpes)` and remain explicitly non-significance-based.

9. **Blocking — the plan contradicts itself about how signals are computed**

> “Every forward target and every signal is computed on FRESH marks” (line 22)

The table explicitly includes the calendar `residual_event_concentration`, while the cached incumbent signals include calendar/row-window constructions. Recomputing all thirteen on fresh events would create different signals and break the claimed parity with their existing mechanisms.

Concrete replacement: state that signals retain their exact cached definitions and are merely read at \(T-1\); only the forward targets use the newly specified fresh-return construction. Identify which signals themselves use calendar rows, fresh observations or event time.

10. **Blocking — the combined mechanism is undefined**

> “Rank-sum of the passing signals … same null” (lines 224–227)

The plan does not define:

- rank handling when a candidate is NaN for some but not all signals;
- whether ranks are normalised before summing;
- tie handling;
- permissive versus strict combined admission;
- whether the null permutes signals jointly or independently.

Independent permutations destroy inter-signal dependence and missingness structure; a joint row permutation preserves them but tests a different null.

Concrete replacement: specify an exact combined score, NaN rule and tie rule. For the null, permute each date’s complete multi-signal row vectors jointly across candidates if cross-signal structure is to be preserved. “Independently predictive” must become “individually passed”; separate marginal screens do not establish independent information.

11. **Blocking — gate 3 and the diversification tie-break cannot yet be implemented**

> “`held_book_character(entry)` computing capital-weighted mean realised vol…” (lines 137–142)

“Capital-weighted” does not define whether weights are capital-at-entry, mean invested capital, or capital-days. Nor does it say whether vault volatility is measured over its full life, while held, or from the T−1 indicator at each decision. Missing indicator coverage is unspecified.

Likewise, “the more diversified candidate” is undefined across five measures that can disagree. `top_vault_pnl_share` also lacks a denominator definition.

Concrete replacement:

- Define one observation per decision date, using actual per-vault equity weights from `state.stats.positions`.
- State the exact T−1 character value joined to each holding, normalisation across finite holdings and the missing-capital rule.
- Define `top_vault_pnl_share` as an address-aggregated quantity with an explicit gross-positive or net denominator.
- Define “more diversified” using an exact rule. Pareto dominance is defensible: no worse on all five measures and strictly better on at least one; otherwise declare the comparison unresolved.

## Material findings

12. **Material — mean per-date Spearman is coherent, but not aligned with the prefilter tail**

> “Spearman rank correlation across that date’s candidates” (lines 178–180)

The estimator is defensible if its estimand is explicitly “the equal-weight mean association on a typical decision date”. A changing candidate set does not require a balanced panel. It does mean the result is conditional on each date’s jointly observed tradable pool, not a persistent vault-level effect.

The larger problem is that the prefilter acts only on the worst \(q\) tail. A positive full-cross-section Spearman can be driven by middle ranks while the bottom 30% is misranked; a useful nonlinear tail signal can also have weak overall Spearman.

Concrete replacement: retain Spearman to satisfy gate 5, but require a mechanism-aligned centre diagnostic: at each date, compare the forward target ranks of the exact 30% that would be excluded with the retained set, then average that contrast using the same clustered inference. Without this, the screen does not test the action the strategy takes.

13. **Material — complete-case gate 5 does not test the strict variant**

> “Minimum 30 candidates with both signal and target” (lines 181–183)

Complete-case Spearman drops NaNs. The strict mechanism uses missingness as an exclusion signal, so its defining behaviour is absent from gate 5. It cannot inherit the permissive signal’s pass.

Concrete replacement: either label every strict run diagnostic/non-adoptable, or separately test the forward outcomes of NaN candidates and include that information in a fully specified strict gate.

14. **Material — fresh forward volatility and downside deviation remain frequency-dependent**

> “on fresh marks only” (lines 174–176)

Taking the standard deviation of irregular fresh-event returns compares different return horizons. A weekly interval naturally has a different scale from a daily interval even under the same process. Maximum drawdown also misses more intragap movement for sparsely observed vaults.

Concrete replacement: define forward realised volatility on the common 30-day horizon, for example from the sum of squared fresh interval returns annualised by `365/30`, and define downside variation analogously. Report fresh-event count. Keep maximum drawdown diagnostic unless its cadence dependence is explicitly accepted.

15. **Material — the forward top-five target can silently degenerate to 1.0**

> “fresh-event top-five share … over the forward window” (lines 174–176)

With five or fewer positive residual events, the numerator equals the denominator and the target is exactly 1. With no positive residuals it is undefined. On a 30-day window this can create large tied or all-NaN cross-sections without raising.

Concrete replacement: pre-register `min_forward_events` and `min_positive_events > 5`; otherwise return NaN with a reason code. Count constant-target dates separately and require a pre-registered minimum number of usable dates.

16. **Material — the fresh-event indicator is improved, but its residual construction remains ambiguous**

> “beta is estimated … excluding the current event” (lines 121–128)

It is unclear whether every residual \(e_j\) uses its own causally shifted \(\beta_{j-1}\), or whether one evaluation-time beta is applied retrospectively to all 90 events. These produce different statistics and availability dates.

Concrete replacement: state that each residual event uses a rolling beta estimated solely from matched events preceding that event, then the concentration window takes the latest 90 finite residual events. Specify the number of raw events consequently required.

Estimating beta on matched intervals is the correct alignment, but it remains observation-frequency-dependent because different mark schedules create different interval horizons, calendar coverage and regression weighting. The plan appropriately avoids claiming full polling invariance; that qualification should remain.

17. **Material — the duplicate-row invariance test is too weak as described**

> “duplicate every row of a series three times” (lines 130–133)

Duplicating rows at identical timestamps mainly tests duplicate-index handling. It does not necessarily test inserted unchanged observations at new timestamps, which is the actual zero-padding claim.

Concrete replacement: insert unchanged vault marks at distinct intermediate timestamps while preserving all original price-change endpoints and the BTC path. Assert equality at original timestamps, equality of the finite/NaN mask and equality of the reported calendar spans. Add the T-and-later perturbation test proving a decision at \(T\) still reads only T−1.

18. **Material — the fraction does depend on signal availability**

> “the filter’s strength does not depend on how many candidates are unmeasured” (lines 32–34)

The code excludes `round(q * len(scored))`, so the percentage of all candidates excluded is \(q\) times the measured share. Strict mode additionally removes every unmeasured candidate. Signals with different NaN rates therefore receive materially different effective filter strength at the same \(q\).

Concrete replacement: call it “a fraction of measured candidates”, and report per date the measured count, NaN count, excluded count, excluded share of all candidates and remaining candidate count. Do not describe equal \(q\) across signals as equal filtering strength.

19. **Material — the prefilter can be behaviourally inert**

The hard prefilter is mechanically different from NB09/NB16’s continuous composite reweighting: it creates a lexicographic rule—stability threshold first, incumbent return rank second. It is nevertheless the same broad class of stability-conditioned selection and does not by itself solve the low-return-vault problem.

Because it removes the unstable tail before incumbent ranking, it may remove only candidates that were nowhere near the top six. The portfolio can then be unchanged even when the screen passes.

Concrete replacement: report, for every run, the fraction of decisions where the prefilter changes the selected six, how many excluded names would otherwise have been selected, selected-set Jaccard versus anchor, and distinct realised trade/equity paths. This is a degeneration check, not a new experiment.

20. **Material — 0.25 is a policy tolerance, not justified by the MDE**

> “Below that margin the Sharpe ordering is noise” (research rules, lines 138–141)

A minimum detectable difference near 2.50 does not identify 0.25 as a boundary between signal and noise. It says this sample is poorly powered for differences far larger than 0.25. Reusing the plateau tolerance is circular, and realised diversification measures also have sampling uncertainty despite being calculated exactly on this backtest.

Concrete replacement: retain 0.25 only as an operator-chosen utility/indifference band and describe it that way. It is legitimate as a pre-registered decision policy, not as a statistical-resolution claim. If statistical evidence is intended, use the paired Sharpe-difference interval instead.

21. **Material — the calendar-versus-fresh conclusion lacks a direct comparison**

> “says … whether the calendar and fresh-event concentration measures differ” (lines 196–200)

One interval excluding zero while another does not is not evidence that the two correlations differ. The expectation that this “settles the question” (lines 250–252) repeats the previous plan’s overstatement.

Concrete replacement: compute a paired difference between their correlations on the same candidate-date sample with common resamples and multiplicity control. Otherwise say only that their observed predictive patterns differed; do not say “settles”.

22. **Material — gate 2’s calibration uses the wrong metric**

The rule gates on masked/unmasked **Sharpe retention**, but justifies 70% using the anchor’s and candidate’s **CAGR/edge retention**. Those figures do not show that the Sharpe bar lies above either historical case.

Concrete replacement: provide the actual historical Sharpe retention values, or change the gate metric to the quantity used for calibration. Do not mix them.

23. **Material — `luck_ratio` is described as five days but uses five cycles**

The existing `panel()` calls `luck_ratio(rc)`, where `rc` is the two-day cycle-return series. The research rules describe removal of the “best five days”. The implementation removes the best five cycles.

Concrete replacement: consistently call these “five cycles” throughout. Retaining the strategy clock is preferable to silently switching to daily zero-filled returns.

24. **Material — close-out family membership is still unspecified**

> “`family_wise_joint()` over the complete executed family” (lines 231–236)

“Every executed run” could include anchor, reference runs, nulls, LOVO runs and strict diagnostics, but the helper expects the complete candidate family and excludes robustness/null runs. It also cannot correct for the thirteen unbacktested screened alternatives.

Concrete replacement: list the labels or exact inclusion rule: all configurations evaluated as potentially adoptable, including failed centres and neighbours; exclude anchor, reference-only, LOVO and null runs. State explicitly that this test does not correct upstream signal screening.

## Minor findings

- “Rank autocorrelation … reshuffles every cycle is measuring noise” (lines 191–194) is too strong. A responsive signal may legitimately change. Define the consecutive-date intersection and minimum common candidates, and call low persistence a diagnostic.
- “in the order of its mean stability correlation” (line 206) does not define how the target-specific correlations are aggregated.
- The cost arithmetic is understated: 19 runs at roughly seven minutes each is about 133 minutes per passing signal, not seven minutes per signal. NB31 cannot re-run all executed configurations in roughly 20 minutes under the same estimate.
- `PREFILTER_LOG` must be explicitly cleared and snapshotted by the new `run_and_record()` wrapper. The existing helper only handles the older logs; otherwise membership can leak between runs.

## Sections that are sound

- Mean per-date Spearman is a valid descriptive estimand once it is explicitly defined as equal-weighting decision dates; changing candidate membership does not itself invalidate it.
- Reading signals at T−1 and sourcing membership from the trading path’s own log are the right alignment choices.
- Requiring anchor and `measured_8` parity before research runs is strong.
- The fresh-event definition correctly compounds BTC over matched vault intervals, excludes the current event from beta estimation, requires a full 90 residual events and limits its claim to duplicate-row invariance.
- The strategy Sharpe and volatility helpers use the native two-day cycle clock and sample standard deviations.
- The existing paired strategy bootstrap uses common cycle indices, and `family_wise_joint()` uses common resamples and the add-one correction.
- Full re-simulation for LOVO, fail-closed unexecuted gates, complete failure strings and deterministic “beat all ten” null language are sound in principle.
- No executed headings exist yet, so there are no numeric heading-to-cell claims to verify. The prospective citation rule is appropriate, subject to removing the unsupported “settles the question” language.