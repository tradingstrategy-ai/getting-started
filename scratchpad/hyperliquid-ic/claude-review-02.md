# Claude fable review of the expanded plan

Requested model: `fable`. Reported model: `claude-fable-5-1`. This reviews `_review/02-plan-before-review.md`, including the full feature inventory and seven forecast horizons. Subsequent responses and edits are recorded in the plan.

**Verdict: implementable after a small set of precise edits.** The plan now honours the user's scope, keeps calendar time, treats a fresh unchanged NAV as evidence, and separates access from ranking. The feature budget arithmetic checks out at 82 + 4 + 4 = 90 and 1,890 cells. What remains are a few internal contradictions and undefined conventions that would otherwise be resolved ad hoc during implementation.

## Material findings

1. **Pool admission contradicts the 30-day coverage rule.** Blocking. Phase 3 missing-data policy versus the coverage convention. The pool admits a vault with 20 fresh observations in 30 days, but every 30-day feature needs 24. Some pool members would therefore carry all-missing 30-day columns, and the common model would rank them on imputed medians plus the missingness indicator, which is the NB24 availability effect in a new place. Edit: require 24 fresh daily endpoints in the trailing 30 days for admission, matching the label rule, and exempt F28 to F31 from the coverage rule since they measure it.

2. **EMA and EWM stepping clock is undefined.** Blocking. Phase 3 EMA definition. The plan does not say whether the recursion advances once per calendar day on the audited grid, with carried NAVs counted as steps, or once per fresh observation. The two give different values and different seed weights for sparse vaults. Edit: step both on the daily calendar grid. Carried days count as steps for the NAV EMA. EWM return variance applies the same 80% fresh-coverage gate as rolling variance over its effective span. Also state that F36 uses the seeded recursive form and F37 uses normalised weights without a seed, because the text currently gives one definition and then another.

3. **Long spans on young vaults collapse to since-inception growth.** Prudent diagnostic. Same section. For span 360 the seed weight after 180 days is about 0.37, so F36 at long spans on a young vault is nearly the log return since the first observation, and the alpha/2 variant at span 360 has an effective span longer than the dataset. Keep the spans as requested, but add a rule that a value whose seed weight exceeds 0.5 is flagged seed-dominated and expect the training-only dedup to merge it with F01 and F27. No deletion needed.

4. **Sizing floor is in the wrong unit.** Blocking. Phase 5 sizing. Production's floor is on daily standard deviation, but the downside forecast lives on the squared scale, so a floor of 1e-4 there means a 1% daily downside deviation and would flatten sizing across most vaults. Edit: floor daily downside deviation at 1e-4, equivalently semivariance at 1e-8, and say so.

5. **Arm D entry threshold is either ambiguous or nearly zero.** Blocking. Phase 5 adaptive breadth. The fee hurdle for a new position is roughly 0.1% plus 10% of profit, so "predicted growth above the exit-cost hurdle" admits almost any positive forecast. Combined with capped equal weights and a 30-name ceiling, that reproduces NB09's breadth result by construction. Edit: predeclare the threshold as the greater of the fee hurdle and the objective's lower reference scaled to H, about 1.5% log growth per 30 days, and require the out-of-fold calibration slope to be positive before the threshold is read on the absolute scale. Keep the single neighbouring sensitivity.

6. **Horizon selection needs a tie-break rule.** Blocking. Phase 2 forecast grid and validation section. All history is development, and the maximum-statistic null over 1,890 cells with three or fewer 90-day blocks will be uninformative, as NB19 showed. Without a rule, the winning horizon is whichever cell is largest in sample. Edit: 30 days remains the default. Another horizon replaces it only if it beats 30 days on the common-date paired comparison for both growth and downside risk and both immediate neighbours agree in sign. Otherwise 30 days is frozen and the profile is reported.

7. **BTC interactions duplicate beta in date-level IC.** Prudent diagnostic. Phase 3 F34 and F35. BTC return and BTC volatility are constants within a date, so the cross-sectional rank of F34 equals the rank of beta with the sign of that day's BTC return, and F35 equals the rank of absolute beta. Their univariate IC therefore adds nothing beyond F32 and |F32|. Edit: keep the budget as is, but state that F34 and F35 are evaluated as conditional-beta terms in the Ridge increment test, and report absolute beta explicitly as the NB39 lead.

8. **The IC pool does not say whether the momentum gate applies.** Blocking. Phase 4 first paragraph. Production removes gated vaults before ranking, and NB03b applied the gate in its pool. Edit: compute whole-universe IC on the ungated eligible pool, and apply the gate in the tercile, paper-basket and portfolio analyses. State this once.

9. **Anchor reference for the Phase 6 gates is not pinned to a window.** Prudent diagnostic. Baseline contract and Phase 6. The production docstring reports the January to 8 July run, while the lower-vol track's anchor runs to 8 September on different capital. Edit: the gates compare against the reproduced production run on the frozen replay window at $150,000, and the docstring numbers are not the anchor.

10. **Production parity of C03 must sort missing as zero.** Prudent diagnostic. Phase 3 fixed controls. In the production decision function a missing composite becomes a score of zero and the vault stays a candidate at the bottom of the ranking, rather than being excluded. Make C03 replicate that, because "preserving missingness" reads as keeping the missing value.

11. **Placebo must pass through every data-dependent choice.** Prudent diagnostic. Phase 4 nulls. The null must include horizon selection and the choice of the two EWM constructions for the decay variants, and must permute whole feature rows including their missingness pattern so young-vault rows do not become mixed rows.

12. **Zero-variance labels dominate QLIKE.** Prudent diagnostic. Phase 2 scoring. With fresh unchanged NAVs a window can have observed variance exactly zero, and QLIKE then rewards the floor. Report the count of such rows and QLIKE excluding them as a sensitivity. Also note that the ICIR from daily overlapping dates is descriptive and that the block bootstrap carries the uncertainty.

13. **Catch-up returns wording is self-contradictory.** Prudent diagnostic. Phase 2 label rule. "Never compress a multi-day catch-up return into one day" conflicts with keeping the daily grid, where a catch-up return necessarily lands on the fresh day. Reword: the grid keeps zero returns on carried days and the observed catch-up return on the fresh day, with the gap length recorded, and the fully observed subset is the sensitivity.

14. **Inception date provenance.** Optional. Phase 3 F26. Confirm that the inception timestamp used for calendar age is a fixed historical fact in the frozen snapshot rather than a revisable current metadata field.

## Simplifications compatible with the user's requirements

- **One bootstrap block length.** Use 90-day date blocks for every horizon and the joint comparison, rather than blocks of at least H per horizon plus 90 for the joint case. It is more conservative and removes one degree of freedom.
- **Drop fold-local pruning, keep training-only dedup.** With 90 candidates and few folds, pruning inside each fold adds implementation cost and changes the candidate set per fold without improving the null.
- **Restrict the measurement sensitivities to the shortlist.** Run the fully observed subset and weekly aggregation checks on shortlisted families only, not on all 1,890 cells. The exhaustive table stays exhaustive.
- **Freeze one model for arms B and D before portfolio runs.** Use the short-history model unless the augmented model shows incremental lift on matched development rows. Do not carry both into the decomposition.
- **Label rather than prune the underpowered corners.** Horizons 60 and 90 and spans 270 and 360 stay in the table and heatmaps by rule, flagged underpowered or seed-dominated. No extra machinery is required for them.
- **Merge the first two notebooks** if the panel build proves quick, since the audit and the feature panel share the same frozen inputs.

## Can implementation start?

Yes, once findings 1, 2, 4, 5, 6 and 8 are written into the plan as stated. They are each a few sentences and none changes the user's scope. Findings 3, 7 and 9 to 13 can be applied during notebook 02 and 03 as reporting rules. The plan already contains the right answers to the remaining questions the user raised: young vaults enter through the common 30-day model and a 5% cap, not a quota; overlapping labels are handled by common-date paired comparisons and date-block resampling; unknown outcomes are stressed with two fixed scenarios rather than imputed; and calendar time is preserved throughout.
