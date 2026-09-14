## Overall verdict

The plan is not executable as written. The empirical comparison is worthwhile, but the central mechanism is not identified, the “event-time” statistic is not genuinely polling-invariant, and rule v4 cannot be implemented consistently using the helpers the plan says to reuse.

All line references below refer to [27-event-concentration-plan.md](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/27-event-concentration-plan.md).

## Blocking findings

1. **Blocking — the proposed outcome cannot confirm or refute the central mechanism**

> “If it keeps the return AND the roughness, the hypothesis is refuted and the penalty is genuinely selecting lumpy winners rather than sparsely-reported ones.”

This is a false dichotomy. A calendar measure can be confounded by sparse reporting and still select genuinely lumpy winners. Conversely, an event-time version can improve measured volatility and ulcer for unrelated reasons:

- Its effective calendar lookback varies by vault.
- Its beta estimator changes frequency and weighting.
- Its score-availability/NaN pattern changes.
- Aggregating returns between fresh marks changes the numerator and denominator.
- It selects a different in-sample portfolio by chance.

The underlying “economic risk” during unobserved gaps is never observed, so the plan cannot establish that the calendar version raised only measured rather than economic risk.

Concrete replacement:

> “NB27 tests whether the legacy statistic is sensitive to zero padding and observation spacing. NB29 tests whether a fresh-event construction produces the predicted in-sample portfolio signature. Meeting that signature is consistent with the sparse-reporting explanation but does not identify it causally. Failure means this construction did not remove the observed risk cost; it does not prove that the legacy statistic is free of reporting-frequency confounding.”

2. **Blocking — the event-time measure is not polling-invariant**

> “Polling-invariant by construction: a vault observed weekly and the same vault observed daily give the same value, up to estimation noise.”

It does not. Daily and weekly observation partition the economic path differently. The top five of 90 daily returns is not the same statistic as the top five of 90 weekly compounded returns; the latter also covers roughly seven times as much calendar time. Re-estimating beta on those different partitions introduces further frequency dependence.

“Fresh mark” is also undefined. The incumbent code counts `r != 0`, which means “price changed”, not necessarily “a new poll arrived”.

Concrete replacement procedure:

- Rename it the **fresh-event measure**, not polling-invariant.
- Define event \(j\) at timestamps \(t_{j-1},t_j\) using:
  - vault log return `log(P[t_j] / P[t_{j-1])`;
  - BTC log return compounded over `(t_{j-1}, t_j]`;
  - beta estimated from matched vault/BTC interval returns.
- Define whether the rolling beta includes the current event and its exact minimum observations.
- Require exactly `event_concentration_max_events` complete residual events, or state another `min_periods` rule.
- Report the calendar-day span covered by each 90-event window.
- Claim only invariance to inserting duplicate unchanged rows without merging economic-return events.

3. **Blocking — NB27 section 2 does not isolate the claimed mechanical effect**

> “keeping every k-th mark and carrying the price forward … for the SAME economic return series. This isolates the confound”

With the supplied indicator, it also changes beta and residualisation:

- A retained vault return covers \(k\) days, but `b` remains the BTC return for only the retained calendar day.
- On forward-filled days, `r=0` but the residual is `log1p(-beta * b)`, not zero. Positive residuals can therefore be manufactured on BTC-down stale days and enter the denominator.
- Beta is attenuated or otherwise biased according to reporting phase and BTC path.
- The terminal return differs unless the last retained mark is forced to the common endpoint.
- “Every k-th” leaves the starting phase unspecified.
- For event time, subsampling merges returns, so the top-five share is not expected to remain unchanged.

This experiment can manufacture precisely the movement attributed to zero padding.

Concrete replacement procedure:

- For the pure mechanical test, estimate beta once and construct one fixed ordered residual-event sequence.
- Re-embed those identical residual events on calendar grids separated by \(k-1\) zeros; do not re-estimate beta.
- Use common endpoints and either evaluate every phase offset or pre-register one.
- If the implemented fresh-event estimator is tested separately, compound BTC over each retained vault interval and label that result as a combined sampling-and-estimation effect, not the isolated confound.

4. **Blocking — the anchor will not actually enter the v4 control family**

> “The family is the 5-step drop family INCLUDING N = 0”

and:

> “It reuses `run_and_record`, `build_family` … unchanged.”

The existing [`build_family()`](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/harness_stability.py:175) iterates only over `FAMILY_DROPS = 5, 10, …, 60`, and `family_frame()` likewise omits the anchor. Therefore the family passed to `control_ref_v4()` will not contain N=0.

Concrete replacement:

Create `build_family_v4()` that calls the existing builder, prepends the recorded anchor with `drop_n=0`, and asserts that the returned index contains exactly anchor plus drops 5–60, with finite volatility and Sharpe.

5. **Blocking — the reused bootstrap helper still tests the v3 maximum**

> “paired block-bootstrap margins … against the constraint-7 comparator”

and:

> “reuses … `bootstrap_margin_table` … unchanged.”

The existing [`bootstrap_margin_table()`](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/harness_stability.py:374) selects the eligible row using `idxmax()`. It will bootstrap against the v3 maximum, not the v4 median.

Moreover, with an even number of eligible controls, the numerical median is the average of two Sharpes and has no single cycle-return series. It is not an “observed control”.

Concrete replacement:

Add `bootstrap_margin_table_v4()`. On every common-block draw:

1. Resample the candidate, anchor and all family members using identical cycle indices.
2. Recompute sample volatility and Sharpe with `ddof=1`.
3. Reapply the no-noisier eligibility rule.
4. Compute the median family Sharpe.
5. Store candidate Sharpe minus that median.

Call it a **family-median reference**, not an observed control. Fail closed if any required series or reference is non-finite.

6. **Blocking — the pooled null changes much more than ranking information**

> “`u` is drawn per (vault, date) from the empirical distribution … so the marginal distribution of multipliers matches and only the ranking information is destroyed.”

A pooled draw matches the global distribution only in expectation. It does not preserve:

- the multiplier distribution on each date;
- polling regimes over time;
- the number and location of NaN exemptions;
- vault-level persistence;
- signal strength on high- versus low-dispersion dates.

If the pool uses the full window, early null trades also use the future distribution of concentration values. Independent per-date draws may create extra turnover and thereby change returns for reasons unrelated to ranking information.

Concrete replacement:

At each decision date, using only T−1 values, form the exact vector of effective multipliers among that date’s candidate set:

```python
m = 1.0 if c is non-finite else 1.0 - lambda_ * np.clip(c, 0.0, 1.0)
```

Permute that vector without replacement across the same candidates. This preserves the date-level distribution and number of exemptions exactly. Hash and compare the complete `(date, vault, multiplier)` mappings, assert all seeds differ and assert no draw is the identity permutation. Report null turnover because the permutation still destroys temporal assignment.

The plan also needs explicit null-mode and seed parameters; none are currently specified in `blocks_concentration.py`.

7. **Blocking — “beats the ten nulls” is not an executable gate**

> “it beats the ten nulls on CAGR and on ulcer.”

This does not say whether “beats” means every null, the median, the mean, or a randomisation p-value. It also leaves the two-metric joint rule undefined.

With ten draws, the smallest possible one-sided add-one p-value is \(1/11=0.0909\). The null cannot support a 5% significance claim.

Concrete replacement if ten runs are retained:

> “`null_ok` is true only when the centre has strictly higher CAGR and strictly lower ulcer than every one of the ten null runs. This is a deterministic robustness screen, not a significance test. Report empirical ranks; do not use ‘significant’. If a p-value is nevertheless printed, use the add-one correction and state that its minimum is 0.0909.”

## Material findings

8. **Material — constraint 7 is data-informed, not cleanly pre-registered**

> “which is the legitimate case”

and:

> “This is chosen for robustness … not tuned to a result.”

The choice was made because the observed maximum was 2.847, no row passed, and one known vault generated the spike. That is explicitly result-informed. The fact that the family has not been re-run is irrelevant because its metrics are already known.

The median is defensible as a robust policy choice, but it cannot honestly be described as independent of this snapshot.

Concrete replacement:

> “v4 is a post hoc, data-informed rule revision motivated by NB24/NB26. It is frozen before NB27–NB30 and reported alongside v3. A configuration that passes only v4 is exploratory on this snapshot. The rule becomes genuinely prospective only when applied unchanged to future data or a subsequent shadow period.”

9. **Material — masked-to-masked compares different counterfactual universes**

> “the candidate’s largest … masked … against the ANCHOR with its own largest contributor masked”

Full re-simulation is correct: it captures substitution and should not be replaced by subtracting realised P&L. But if the two largest contributors differ, the comparison mixes two different universe shocks. It estimates “each strategy after removing its own ex-post best name”, not the candidate’s performance relative to the anchor under a common missing-vault counterfactual.

The justification “comparing … to an unmasked anchor would fail everything” is outcome-based, not an estimand.

Concrete replacement:

For candidate \(C\), determine its largest contributor \(V_C\) from the unmasked run. Re-run both \(C\) and the anchor with the common mask `{V_C}`, then evaluate constraints 1, 2 and 4. Report the anchor-own-largest mask separately as a symmetric influence diagnostic. If the existing each-own comparison is retained, rename it a “symmetric Achilles-heel stress” and do not call it a common counterfactual.

10. **Material — NB27’s main association statistic is undefined**

> “the share of cross-sectional variance … attributable to observation frequency rather than to return shape”

No regression, response transform, weighting, unit of analysis or return-shape comparator is specified. Fresh count and stale share may also be near-deterministic complements. The later expectation that freshness beats “any return-shape measure” is impossible to evaluate because no return-shape measures are named.

Concrete replacement:

- Report an equal-weight distribution of per-date Spearman correlations between concentration and `fresh_count / 180`.
- Define “variance explained” as the per-date cross-sectional OLS \(R^2\) of concentration rank on freshness rank, calculated only where at least three finite candidates exist; report its median and interval across dates descriptively.
- Report stale share separately rather than entering both predictors together.
- Replace “attributable” with “associated”.
- Remove every “more than return shape” claim unless one specific comparator and rule are pre-registered.

11. **Material — decision-time alignment and candidate membership are not fixed**

> “For every candidate on every decision date, read … from the cached indicator”

The executing agent must decide whether “decision date” means bar T or the T−1 value actually available to `decide_trades`. It must also reconstruct what “reach `decide_trades`” means.

Concrete replacement:

> “For a decision at T, read every indicator and trailing covariate exactly as `decide_trades` reads it, ending at bar T−1. Median TVL and age also end at T−1. The candidate set is taken after inclusion, good-pair, quarantine, blacklist and momentum-gate checks, but before concentration adjustment and top-six ranking.”

In section 4, replace “went on to win a basket slot” with “was selected into the top six at that same rebalance”.

12. **Material — NaN and effective no-op cases are mischaracterised**

> “NaN until 180 calendar days and 60 fresh marks.”

Those are necessary but not sufficient conditions. The score can also be NaN because beta is unavailable, BTC variance is zero/non-finite, residuals are non-finite, or the positive-residual denominator is zero.

There is another silent no-op. The supplied numerator takes the five largest raw residuals, not the five largest positive residuals. With fewer than five positive residuals it can be negative, after which `decide_trades` clips it to zero and applies no penalty. The current `concentration == concentration` check rejects NaN but accepts infinities.

Concrete replacement:

- Use `np.isfinite(concentration)` for scoring.
- Log mutually exclusive missing-reason codes.
- Report the positive-residual count and all effective no-penalty reads: non-finite score or clipped concentration `<= 0`.
- Correct the prose from “best-five share of positive residual return” to the actual legacy definition unless the numerator is deliberately changed.
- If the legacy calculation remains for NB09 parity, explicitly audit whether any finite value lies outside `[0,1]`.

13. **Material — the proposed evidential language exceeds the available power**

> “failures … confirmed as structural”

and:

> “the hypothesis is refuted”

Nine neighbouring lambdas are highly correlated deterministic variants, not nine independent replications. With about 125 cycles, block lengths 5, 10 and 20 correspond to only about 25, 12 and 6 non-overlapping blocks. The late period has roughly 35 cycles. Ten nulls have only 0.0909 one-sided p-value resolution.

The design can reveal large ranking changes and large performance differences on this snapshot. It cannot establish structural failure, distinguish small movements around the ulcer/volatility boundaries reliably, or prove absence of a confound.

Concrete replacement:

Use “observed across the tested grid on this snapshot”, “did/did not exhibit the predicted signature”, and “unresolved at this sample size”. State that adjacent-lambda plateau membership is a robustness rule, not independent statistical replication.

## Minor executability gaps

- “Window sensitivity” should state that the four runs change one parameter at a time while all other parameters remain at the centre.
- “Difference in which vaults each penalises” needs a metric. A concrete definition is the paired `(vault,date)` multiplier difference plus mean same-date top-six Jaccard overlap.
- `family_wise_joint()` needs an exact label set. It should include every potentially adoptable lambda and sensitivity/admission configuration, but exclude anchor, drop controls, nulls and masked robustness runs.
- NB09 reproduction should assert the complete published metric vector and preferably the realised position/trade identity, not only CAGR and Sharpe.

## Necessary verification missing from the plan

The splice verification should add three tests because they directly support existing claims rather than widen the research:

1. Perturb bar T and later bars and prove that a decision at T still reads only T−1.
2. Insert duplicate unchanged rows into a synthetic event sequence and verify the limited zero-padding-invariance property actually claimed.
3. Exercise insufficient history, zero denominator, fewer than five positive residuals, non-finite beta and `require_concentration_scored=True`, asserting the logged reason and fail-closed behaviour.

## Sections that are sound

- The incumbent cycle Sharpe and volatility are computed on the strategy’s own two-day clock.
- The existing paired Sharpe bootstrap uses common block indices and `ddof=1`.
- `family_wise_joint()` uses common resampling and the add-one p-value correction.
- Full re-simulation is the correct implementation of masking; only its comparison estimand needs changing.
- Anchor parity, complete failure strings, unique run bookkeeping and the “NB27 adopts nothing” rule are all well specified.
- The predicted ulcer-at-or-below-anchor signature is correctly weaker than adoption’s 15% ulcer-improvement requirement, provided the notebook clearly distinguishes mechanistic support from adoption.