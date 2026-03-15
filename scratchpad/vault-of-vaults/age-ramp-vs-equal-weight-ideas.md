# Age-ramp vs equal-weight ideas

The recent notebook history points to a narrow but important conclusion. For many Hyperliquid notebooks, equal weight was surprisingly hard to beat once the universe was sensible. Then NB88 found the first weighting rule that clearly outperformed equal weight, and that rule was `age_ramp`.

The key question now is not "can we invent another weighting rule?" but "what exactly is `age_ramp` doing that equal weight is not?" These experiments are meant to answer that question cleanly.

## Starting point

- NB62 to NB64 already found that signal-responsive sizing kept losing to equal weight, even when the signals themselves looked plausible. That is the direct pre-history for any `age_ramp` versus equal-weight comparison.
- NB66 to NB70 suggest selection and sizing should be treated separately: better gates helped, but equal weight often still beat clever weighting after selection.
- NB83 to NB86 then reinforced that inclusion criteria and diversification mattered more than clever post-inclusion ranking.
- NB87 suggests age and TVL thresholds matter, but threshold choice is less important than it first appears.
- NB88 shows that `age_ramp` is the first weighting rule to beat equal weight in the wide universe.
- NB95 shows that this result survives walk-forward testing better than the newer share-price-derived ideas.
- So the right next step is to audit `age_ramp` itself, not to assume it is already fully understood.

## Baseline numbers

The most useful baseline is the like-for-like wide-universe comparison, not the absolute best result from some older and different architecture.

- NB62 to NB64 equal-weight era baseline: roughly `85%` to `86%` CAGR, `2.52` Sharpe, and `-6.26%` max drawdown. This is the pre-`age_ramp` reference point where equal weight kept beating smarter sizing ideas.
- NB68 strong conservative baseline: `124.64%` CAGR, `3.05` Sharpe, and `-5.79%` max drawdown. This is a better gate plus equal-weight portfolio, but not a direct like-for-like comparison to the later wide-universe notebooks.
- NB88 wide-universe equal-weight baseline: about `136%` CAGR, `3.01` Sharpe, `-4%` max drawdown, and Calmar around `34.0` to `36.2`.
- NB88 wide-universe `age_ramp` baseline: about `217%` CAGR, `3.58` Sharpe, `-4%` max drawdown, and Calmar around `54.25` to `58.5`.
- NB93 soft-prior best result so far in the age-ramp branch: `305%` CAGR, `3.43` Sharpe, `-4%` max drawdown, and Calmar `76.25`.
- NB95 walk-forward holdout average for `equal_weight`: CAGR `2.55`, Sharpe `1.92`, Calmar `257.81`, max drawdown `-1.33%`
- NB95 walk-forward holdout average for `age_ramp`: CAGR `2.83`, Sharpe `1.70`, Calmar `291.38`, max drawdown `-1.67%`

The current working baseline should therefore be:

- Plain baseline: wide-universe `equal_weight`
- Structural baseline: wide-universe `age_ramp`
- Best structural extension so far: `age_tvl_soft_prior`

Any new idea should be judged against all three, and the most important comparison is whether it improves on `age_ramp` without losing the simplicity and robustness that made `age_ramp` convincing in the first place.

## Experiment ideas

### Age-ramp attribution

- Hypothesis: `age_ramp` wins because it shrinks exposure to immature vaults without changing the selected universe much.
- Test shape: hold the universe fixed and compare `equal_weight` versus `age_ramp` on the exact same included vault set each day.
- What to report: overlap in names, weight dispersion, turnover, top-vault PnL share, and how much PnL comes from vaults below 30, 60, 90, and 180 days old.
- Success condition: the edge remains even when selection is held constant.
- Notebook motivation: NB83, NB86, and NB88. Earlier work often showed that selection mattered more than weighting, so this test asks whether NB88 really found sizing alpha.
- Why this matters: it separates sizing alpha from hidden selection effects.

### Ramp shape ablation

- Hypothesis: the benefit comes from "some penalty for youth", not specifically from a linear ramp.
- Test shape: compare linear, concave, convex, stepwise, logistic, and capped-piecewise ramps, all normalised to the same minimum and maximum weights.
- What to report: Calmar, Sharpe, max drawdown, concentration, and sensitivity to small parameter changes.
- Success condition: one family is clearly more robust than the others, or linear turns out to be the least fragile default.
- Notebook motivation: NB88 and NB93. NB88 introduced linear `age_ramp`; NB93 hints that softer structural priors may beat both hard filters and naive equal treatment.
- Why this matters: if many shapes work, then the insight is structural; if only one works, the current result may be more brittle than it looks.

### Age-ramp versus hard age filters

- Hypothesis: soft age penalties outperform binary age cut-offs because they preserve diversification while still discounting uncertainty.
- Test shape: compare `equal_weight + min_age filter`, `age_ramp + loose min_age`, and `age_ramp only` on the same windows.
- What to report: number of active vaults, capital utilisation, tail concentration, and whether gains come from keeping more names alive.
- Success condition: soft age penalties beat hard filters at similar or lower drawdown.
- Notebook motivation: NB87 versus NB88. NB87 made age binary; NB88 made it continuous.
- Why this matters: it ties NB87 and NB88 together directly.

### Equal-weight on matched age buckets

- Hypothesis: part of the apparent `age_ramp` edge may just come from underweighting the youngest launch cohort.
- Test shape: split the universe into age buckets, then run equal weight inside each bucket and compare that to `age_ramp`.
- What to report: per-bucket returns, per-bucket drawdowns, and the implied bucket allocation chosen by `age_ramp`.
- Success condition: `age_ramp` still wins after bucket effects are made explicit.
- Notebook motivation: NB87 and NB95. NB87 suggested young survivors matter in the early period, while NB95 suggests the mature-period edge still survives.
- Why this matters: it tells us whether age is a smooth cross-sectional signal or simply a cohort-allocation rule.

### Age-ramp by regime

- Hypothesis: `age_ramp` helps most during launch-heavy or noisy periods, but adds less in stable mature periods.
- Test shape: evaluate early ecosystem window versus mature window, and also split by broad vault-market volatility regime.
- What to report: relative improvement over equal weight in each slice, not just full-period summary metrics.
- Success condition: a consistent sign of improvement, even if the effect size changes by regime.
- Notebook motivation: NB80, NB87, and NB88. Those notebooks already showed that start date and ecosystem maturity strongly change results.
- Why this matters: if the edge only exists in one launch regime, it may be a dated ecosystem effect rather than a durable rule.

### Age-ramp concentration decomposition

- Hypothesis: `age_ramp` improves Calmar mainly by reducing accidental concentration in a few fresh winners.
- Test shape: compare equal weight and age ramp on Herfindahl concentration, effective number of positions, top-1 and top-3 contribution share, and per-vault drawdown contribution.
- What to report: whether drawdown control comes from better diversification or from genuinely better signal alignment.
- Success condition: concentration and tail dependence improve without giving up too much upside.
- Notebook motivation: NB69, NB73, and NB80. Those notebooks showed that concentration, idle cash, and top-vault dependence often explain more than the raw signal label.
- Why this matters: this is the cleanest explanation if the edge is really portfolio-construction rather than vault-picking skill.

### Ramp minimum-weight sensitivity

- Hypothesis: the floor weight in `age_ramp` matters almost as much as the ramp period.
- Test shape: keep the same ramp but vary the floor from near-zero to a generous minimum such as `0.25`.
- What to report: trade count, diversification, whether very young vaults contribute positive or negative marginal PnL, and whether the floor mostly controls false exclusions.
- Success condition: find a stable floor region rather than a knife-edge optimum.
- Notebook motivation: NB45, NB47 to NB50, and NB88. Earlier notebooks repeatedly showed that small-sample behaviour near zero or near full exclusion creates fragile signals.
- Why this matters: a soft prior can quietly become a hard filter if the floor is too low.

### TVL-controlled age-ramp

- Hypothesis: `age_ramp` partly works because age and TVL are correlated, so the true effect may weaken once size is controlled explicitly.
- Test shape: compare age ramp, TVL ramp, and age ramp residualised against TVL buckets or TVL z-scores.
- What to report: whether age still adds edge after matching vaults on size.
- Success condition: age remains useful after controlling for TVL.
- Notebook motivation: NB70, NB87, and NB93. TVL keeps reappearing as a structural factor, so age needs to be tested net of size.
- Why this matters: this tells us whether age is genuinely informative or just a proxy for surviving long enough to accumulate capital.

### Metadata-enhanced age-ramp

- Hypothesis: age is only the simplest version of a broader "proof" signal, and real metadata can refine it.
- Test shape: multiply or blend `age_ramp` with follower growth, leader fraction, days following, or vault equity stability if those fields are available.
- What to report: whether metadata improves on plain age ramp without making the surface fragile.
- Success condition: an incrementally better and still robust soft prior.
- Notebook motivation: NB70 and NB71. Earlier metadata-aware sizing and ranking attempts did not beat equal weight, but they may still add value when layered on top of a stronger structural prior.
- Why this matters: this is the most natural extension if the age story is really about trust and survival.

### Age-ramp versus equal-weight walk-forward matrix

- Hypothesis: the right benchmark is not one holdout result but a repeated fold-by-fold scorecard.
- Test shape: run both methods across expanding and rolling walk-forward folds, then compare fold win rate, average rank, and performance degradation from train to test.
- What to report: win-loss-tie counts on Calmar, Sharpe, CAGR, and max drawdown, plus parameter drift for the ramp.
- Success condition: `age_ramp` wins often enough to justify its added complexity over equal weight.
- Notebook motivation: NB81 and NB95. NB81 showed how much pooled in-sample winners can decay on holdout; NB95 did the same check for the age-ramp era.
- Why this matters: if it only wins on pooled backtests, then equal weight is still the more honest default.

## Share-price-related extensions

The notebook history does not support raw share-price transforms as a primary weighting rule yet. Still, there are a few price-related ideas that are worth testing in a more disciplined way, especially as overlays on top of `age_ramp` or matched against equal weight on the same universe.

### Age-ramp plus residual price overlay

- Hypothesis: age handles uncertainty, while residual price behaviour may still carry small manager-skill information at the margin.
- Test shape: start from `age_ramp`, then apply a weak multiplier from residual momentum, residual Sharpe, or residual trend quality.
- What to report: whether the overlay improves fold-by-fold ranking without materially worsening max drawdown.
- Success condition: better risk-adjusted performance than plain `age_ramp`, not just higher pooled CAGR.
- Notebook motivation: NB67, NB68, NB89, and NB95. Earlier dual-signal work suggests price may be more useful as a secondary layer than as the main weight.
- Why this matters: this is the cleanest way to test whether price adds anything after the structural prior is already in place.

### Share-price slope stability

- Hypothesis: the useful part of share price is not the return level but the smoothness and persistence of the trend.
- Test shape: compare rolling trend slope, trend t-stat, R-squared of log share price, and trend-break frequency against equal weight and age ramp.
- What to report: whether smooth trends outperform jumpy trends after controlling for age and TVL.
- Success condition: stable-trend vaults show better out-of-sample performance than noisy high-return vaults.
- Notebook motivation: NB45, NB47, NB48, and NB51. A lot of the earlier ratio work struggled with unstable magnitudes; trend quality may be a cleaner way to use the same price path.
- Why this matters: it shifts the question from "who went up most?" to "whose equity curve looks sustainably managed?"

### Volatility as a veto, not a rank

- Hypothesis: vault volatility may be more useful as a soft penalty than as a standalone score.
- Test shape: keep equal weight or age ramp as the base, then apply mild penalties for realised volatility, downside volatility, or volatility-of-volatility.
- What to report: whether these penalties reduce drawdown without destroying CAGR.
- Success condition: lower tail risk at similar return quality.
- Notebook motivation: NB35, NB37, NB58, and NB84a. Volatility-like features have often hurt when asked to drive the full ranking, but they may still work as guardrails.
- Why this matters: many prior volatility-like signals failed when asked to rank vaults directly, but they may still work as guardrails.

### Recovery-adjusted momentum

- Hypothesis: raw momentum fails because it chases rebound noise, but momentum conditioned on recent recovery quality may be more robust.
- Test shape: combine trailing return with time-under-water, new-high frequency, or recovery-speed features.
- What to report: whether the combined score beats plain residual momentum and plain age ramp.
- Success condition: better Sharpe and max drawdown than raw momentum-style variants.
- Notebook motivation: NB84a, NB90, and NB91. Each component failed on its own, but the interaction may be more informative than the standalone signals were.
- Why this matters: it gives share price another chance without repeating the same plain rolling-ratio family.

### Relative share-price behaviour inside age buckets

- Hypothesis: share price may only be informative after comparing vaults to peers of similar age.
- Test shape: split the universe into age buckets, then rank vaults by residual return, residual Sharpe, or trend quality within each bucket.
- What to report: whether price-derived ranks become more stable once the strongest age effect is neutralised first.
- Success condition: within-bucket price ranks add value over bucket-level equal weight.
- Notebook motivation: NB71, NB86, NB89, and NB95. Rank-style ideas have mostly failed in the full universe, so this asks whether they only fail because age dominates the cross-section.
- Why this matters: this is a direct test of whether age is masking a weaker but real price signal.

### Drawdown asymmetry score

- Hypothesis: the informative share-price feature may be asymmetric behaviour in stress, not average return quality.
- Test shape: score vaults by downside deviation, crash-day capture, recovery lag, and ratio of upside participation to downside participation.
- What to report: whether these asymmetry scores improve the portfolio when used as a mild overlay.
- Success condition: better downside control than equal weight and better upside retention than simple volatility penalties.
- Notebook motivation: NB35, NB58, NB90, and NB91. Drawdown and regime features have not worked well as crude rules, but the downside asymmetry itself may still matter.
- Why this matters: it targets the part of price behaviour most likely to reflect manager discipline.

### Price-feature interaction with TVL growth

- Hypothesis: a share-price move is more credible when accompanied by stable or rising TVL, and less credible when it happens alongside capital flight.
- Test shape: test return × TVL-growth, trend-quality × TVL-stability, and drawdown × TVL-retention interaction terms.
- What to report: whether price signals become more informative once flow confirmation is required.
- Success condition: interaction features beat pure price features and remain useful after age controls.
- Notebook motivation: NB70, NB87, NB92, and NB93. The structural story already says age and TVL matter, so price should probably be tested conditionally rather than in isolation.
- Why this matters: it links the price story to a behavioural story about follower trust.

### Share-price contribution decomposition

- Hypothesis: some price-derived signals may appear useful only because they load on one or two extreme winners.
- Test shape: for each price-based variant, decompose PnL by vault, launch cohort, and return regime, then compare concentration against equal weight and age ramp.
- What to report: top-1 and top-3 PnL share, kurtosis, and whether any apparent edge survives after removing the single biggest contributor.
- Success condition: a price feature that improves breadth as well as headline metrics.
- Notebook motivation: NB69, NB80, NB84b, and NB89. Several earlier signal wins turned out to be concentration stories once you looked at the contribution profile.
- Why this matters: this is the fastest way to reject false positives in share-price research.

## Recommended order

1. Age-ramp attribution
2. Age-ramp versus hard age filters
3. Ramp shape ablation
4. TVL-controlled age-ramp
5. Age-ramp versus equal-weight walk-forward matrix
6. Age-ramp plus residual price overlay
7. Relative share-price behaviour inside age buckets
8. Metadata-enhanced age-ramp

## Default comparison protocol

- Always compare against plain `equal_weight` on the same universe.
- Also compare against "matched equal weight", where the included vault set is frozen to the same names as `age_ramp`.
- For any share-price idea, also compare against `age_ramp + no price overlay` so the incremental value of price is visible.
- Report both full-period metrics and per-slice metrics for `2025-04-01` to `2025-07-31` and `2025-08-01` to `2026-03-11`.
- Include concentration and contribution diagnostics, not just CAGR / Sharpe / Calmar.
- Reject any `age_ramp` refinement that only improves pooled results by increasing dependence on one or two vaults.
