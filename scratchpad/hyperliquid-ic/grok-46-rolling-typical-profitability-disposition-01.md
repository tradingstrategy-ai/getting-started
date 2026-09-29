# Review disposition

The [plan](rolling-typical-profitability-plan-01.md) incorporates actionable findings from the [Grok review](grok-46-rolling-typical-profitability-review-01.md).

Grok CLI was invoked with `--model grok-4.6 --reasoning-effort xhigh`. The completed stream records backend `grok-4.6-build`, two turns and `end_turn`. The initial model-list authentication warning did not prevent the review. The reviewer received the entire draft and excerpts from ten earlier notebooks, including the revised lower-vol NB28 verdict. This was a plan/history review, not a full source or numerical audit.

## Changes adopted

- Include profitable-window share in the conditional comparison, with a separate fixed Sharpe-plus-frequency comparator view. The original growth/volatility-only adjustment could not distinguish the proposed feature from the already-tested consistency signal.
- Calculate median and quartile from unannualised log return per actual elapsed day. Keep raw simple returns and actual spans for interpretation. Sparse intervals no longer acquire larger scores merely because they span more days.
- Specify daily endpoint boundaries, the rolling features' potentially longer historical footprint, a common latest pre-decision mark for formation and forward entry, and genuinely subsequent exits.
- Fix average ranks, fractional boundary ties, feature-only ranking before outcome masking, matched feature-complete pair comparisons and zero-variance handling.
- Specify paired comparisons against ordinary growth, positive-window frequency, Sharpe and inverse risk. These are descriptive contrasts, not a new search or acceptance conjunction.
- Add an explanatory jump-containment table, never a selection feature. Preserve the synthetic counterexample and honest small-sample quantile reporting.

## Reviewer claims corrected or qualified

- **“n=2 makes Q=M” is false with the specified linear interpolation.** For two different outcomes, the 25th percentile and median generally differ. Report actual equality and sample count; do not manufacture equality or discard young vaults.
- **S being a function of G/V does not imply linear rank collinearity.** Separate comparator sets are useful for interpretation; the plan now avoids the reviewer's incorrect claim that G, V and S are necessarily rank-deficient together.
- **The reviewer's jump-overlap percentages assume a different formation-window convention.** This plan includes intervals by their ending date, potentially using start marks before T-W. The plan explicitly declares that footprint and measures actual containment rather than adopting the approximate percentages.
- The optional joint-quadrant target was not added: marginal/conditional forward-return and drawdown tables already answer the stated question. Being above a cross-sectional median return would not itself establish positive profit. Keep the notebook focused.

## Outcome

Proceed with the revised single-notebook specification when implementation is requested. No portfolio experiment, additional feature grid or mandatory long-history condition was added. No notebook has been implemented or run as part of this task. The author revisions have not received a second Grok review.

Review input, original draft, source fingerprints, raw completed stream and completion metadata are retained in `_review/rolling-typical-profitability-plan-01/`.
