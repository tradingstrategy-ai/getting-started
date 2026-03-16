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

## Experiment findings (2026-03-16)

All 18 experiments have been run across NB96 to NB113. Findings are written into each notebook's heading cell. Below is the consolidated summary.

### Age-ramp core audit

| NB | Experiment | Hypothesis | Verdict | Key number |
|---|---|---|---|---|
| **96** | Age-ramp attribution | Sizing alpha exists | **Rejected** | Equal weight slightly wins when universe is held fixed (Calmar 33.6 vs 31.0) |
| **97** | vs hard age filters | Soft > hard filters | **Not confirmed** | Best result is equal_weight with min_age=0.0 (Calmar 40.3); min_age threshold is the dominant factor, not weighting method |
| **98** | Ramp shape ablation | Benefit is structural | **Confirmed** | All shapes beat equal weight; convex at 0.5y best (Calmar 57.75) |
| **99** | TVL-controlled age-ramp | Age proxies for TVL | **Partially confirmed** | Age is genuinely informative, not just a TVL proxy; hard TVL filtering (min_tvl 5k→25k) is the dominant lever |
| **100** | Walk-forward matrix | Fold-by-fold wins | **Confirmed** | age_ramp wins Calmar 3-0, Sharpe 3-0 across folds; rolling windows preferred |
| **104** | Matched age buckets | Bucket allocation explains edge | **Confirmed** | Simple `age_bucket_equal` slightly outperforms smooth ramp (Calmar 56.0 vs 54.25) |
| **105** | Age-ramp by regime | Helps more in noisy periods | **Wrong** | Helps more in mature period (+51% Calmar); 69 new launches in mature vs 21 in early |
| **106** | Concentration decomposition | Reduces concentration | **Rejected** | Actually increases PnL concentration (top-3 share 45.2% vs 39.5%); mechanism is vault avoidance |
| **107** | Floor sensitivity | Floor matters | **Confirmed** | Clear inverted-U pattern: ramp_floor=0.10–0.15 optimal (avg Calmar 44–47); extremes (0.01 or 0.25) much worse (avg Calmar 19–24) |

### Share-price extensions

| NB | Experiment | Verdict | Key number |
|---|---|---|---|
| **101** | Residual price overlay | **Partially confirmed** | Trend R² overlay works (Calmar 127.5, -2% max DD); momentum/Sharpe residuals hurt |
| **102** | Relative price in age buckets | **Rejected** | Within-bucket price ranks don't improve over bucket-level equal weight; ranking concentrates into volatile winners |
| **103** | Metadata-enhanced age-ramp | **Rejected** | TVL-derived metadata too noisy as a weight multiplier; plain age_ramp dominated every variant |
| **108** | Share-price slope stability | **Partially confirmed** | Trend R² best Calmar (62.7, 251% CAGR) but Sharpe drops (2.67) from concentration |
| **109** | Volatility as veto | **Partially supported** | Vol-of-vol penalty modestly improves Sharpe (3.89) but is parameter-sensitive |
| **110** | Recovery-adjusted momentum | **Rejected** | Doesn't beat age ramp; overlay worsens drawdown to -6.1% |
| **111** | Drawdown asymmetry | **Partially supported** | pure_asymmetry dominates Calmar (best 71.4, -3% max DD); as overlay on age_ramp adds little (Sharpe 3.62 vs 3.58) |
| **112** | Price-TVL interaction | **Informative** | Flow-confirmed age_ramp achieves highest Sharpe (3.77); `return_x_tvl_growth` boosts CAGR to 381% but doubles drawdown |
| **113** | Contribution decomposition | **Confirmed** | Price-signal alpha is concentration on a few lucky vaults; trend_weight retains only 64% of CAGR after removing top vault |

### Key takeaways

1. **Age ramp's edge is selection/avoidance, not sizing alpha.** When the universe is held fixed, equal weight slightly wins. The ramp works by excluding or underweighting young, unproven vaults (NB96, NB106).
2. **Any youth penalty works.** Linear, convex, step, logistic — they all beat equal weight. The insight is structural, not shape-specific. Convex at 0.5y is marginally best (NB98).
3. **Age ramp is really a cohort-allocation rule.** A simple three-bucket equal-weight scheme slightly outperforms the smooth ramp, confirming the edge comes from balanced maturity allocation, not continuous signal value (NB104).
4. **Age ramp survives walk-forward testing decisively.** Calmar 3-0, Sharpe 3-0 across folds. Rolling windows are preferable to expanding for parameter selection (NB100).
5. **Age ramp helps more in the mature ecosystem period**, not the early noisy period as hypothesised. The mature period had 3× more new launches, giving the ramp more work to do (NB105).
6. **Age is genuinely informative, not a TVL proxy.** Adding TVL scoring on top of age ramp does not reliably help. Hard TVL filtering (raising min_tvl) is the dominant lever (NB99).
7. **The most promising extensions are trend R² and flow confirmation.** Trend R² overlay (NB101: Calmar 127.5) and flow-confirmed age ramp (NB112: Sharpe 3.77) are the only signals that incrementally improve on plain age ramp without catastrophic trade-offs.
8. **Most price signals are concentration traps.** Momentum, Sharpe residuals, recovery momentum, within-bucket ranking, and metadata multipliers all either hurt or concentrate PnL on a few lucky vaults (NB102, NB103, NB110, NB113).
9. **Volatility penalties are fragile.** Vol-of-vol shows a small Sharpe improvement but is highly parameter-sensitive. Realised vol and downside vol consistently destroy returns (NB109).
10. **The ramp floor matters more than initially thought.** ramp_floor=0.10–0.15 is optimal; extremes hurt. Recommended defaults: age_ramp_period=0.50, ramp_floor=0.10 (NB107).
11. **Drawdown asymmetry is a strong standalone signal for drawdown control** (best Calmar 71.4, -3% max DD), but as a mild overlay on age_ramp it adds little (NB111).
12. **The min_age threshold matters more than the weighting method.** Soft ramps do not clearly beat hard age filters — the dominant factor is where the age cut-off sits, not whether the penalty is smooth or binary (NB97).

### Per-notebook key observations

#### NB96 — Age-ramp attribution

- Equal weight outperformed age_ramp when universe is held fixed (CAGR 140% / Sharpe 3.52 vs 138% / 3.34).
- Over 82% of PnL in both methods comes from vaults older than 180 days — young vault drag is minimal.
- The methods did not trade identical vaults (67 for EW vs 52 for AR, only 46 in common).
- Age_ramp actually hurt in the 60–90 day bucket (-3.0% vs +1.2%) and gave up significant 90–180d PnL.
- **Core insight:** age_ramp's NB88 edge was a selection effect (fewer young vaults enter the portfolio), not sizing alpha within the same universe.

#### NB97 — Age-ramp vs hard age filters

- Cache collision with NB88 fixed by hardcoding unique notebook ID. Grid now correctly varies `min_age` across [0.0, 0.05, 0.1, 0.25, 0.5].
- **Best risk-adjusted result:** equal_weight with min_age=0.0 (Calmar 40.3, 121% CAGR, 3.42 Sharpe, -3% max DD).
- age_ramp opens more positions (153 vs 135) but achieves marginally lower Calmar (38.7).
- At high min_age values (0.25, 0.5), both methods converge to identical results.
- **Core insight:** the dominant factor is the min_age threshold, not the weighting method. Soft ramps do not clearly beat hard age filters.

#### NB98 — Ramp shape ablation

- All six ramp shapes beat equal weight at the 0.5y period, confirming the benefit is structural.
- **Ranking at 0.5y:** convex (57.75 Calmar) > logistic > linear > step > concave > capped_linear > equal_weight (34.0).
- 0.5y is the universal sweet spot. At 0.25y the ramp is too short to differentiate; at 1.0y it is too aggressive.
- Shapes that penalise youth heavily upfront (convex, logistic, step) outperform concave alternatives.
- The original NB88 linear ramp (Calmar ~54) remains solid, but convex edges it by ~3.5 points.

#### NB99 — TVL-controlled age-ramp

- All four weight signals now tested: equal_weight, age_ramp, tvl_ramp, and age_ramp_tvl_controlled.
- Age_ramp retains its edge after TVL control (Calmar 75.5 vs 75.3 for tvl_ramp). Plain age_ramp has the best average performance (Calmar 53.9).
- Best single result: `age_tvl_soft_prior` at min_tvl=25k (305% CAGR, 3.43 Sharpe, Calmar 76.1).
- **Raising min_tvl to 25k was the dominant lever** for all signals.
- **Core insight:** age is genuinely informative, not merely a TVL proxy. Adding TVL scoring on top of age ramp does not reliably help.

#### NB100 — Walk-forward matrix

- age_ramp won the fold-by-fold scorecard decisively: Calmar 3-0, Sharpe 3-0 (identical for expanding and rolling).
- age_ramp was the training winner on all 6 folds (3 expanding, 3 rolling).
- **age_ramp_0.50 is the strongest holdout variant** (avg CAGR ~355%, avg Calmar ~364 vs equal_weight ~255% / ~129).
- Rolling windows are preferable to expanding — rolling adapted from period 0.75→0.50 across folds, whilst expanding locked onto 0.75 (weakest holdout variant).
- **Caveat:** Fold 3 had an extreme bull run inflating absolute numbers.

#### NB101 — Residual price overlay

- **Residual trend quality (R²) is the clear overlay winner:** 255% CAGR, -2% max DD, Calmar 127.5 (age_ramp_period=0.25, overlay_strength=0.3, overlay_window=30).
- Mean Calmar for R² overlay (36.2) beats control mean (29.5).
- Residual momentum and residual Sharpe both degraded performance — roughly doubled max drawdown (-9% and -8% median) without compensating CAGR gains.
- Short overlay windows (30 days) performed best.
- **Core insight:** trend smoothness captures whether vaults go up consistently; useful as a secondary signal on top of the age structural prior.

#### NB102 — Relative price in age buckets

- **`age_bucket_equal` was the winner** (Calmar 48.1, 144% CAGR, -3% max DD), beating NB88 equal_weight baseline (~35 Calmar).
- Within-bucket return ranking boosted raw CAGR (191–226%) but max DD ballooned to -5% to -10%, destroying Calmar.
- Within-bucket Sharpe ranking similarly increased drawdown (-6% to -9%).
- Higher `rank_tilt` consistently worsened risk-adjusted returns.
- **Core insight:** the age-bucket structure itself is the value-add; trying to be clever with price ranks within buckets concentrates into volatile winners.

#### NB103 — Metadata-enhanced age-ramp

- **Plain age_ramp dominated every metadata-enhanced variant** across all ramp periods. Best: Calmar 34.5, CAGR 138%, Sharpe 3.34 at period=0.50.
- TVL growth boosted some CAGRs (up to 167.9%) but worsened drawdowns (-7% to -9%).
- TVL stability was least harmful (lowest DD of -3%) but still underperformed plain age ramp on Calmar.
- Composite (growth + stability blend) performed worst overall.
- **Core insight:** TVL-derived metadata is too noisy as a continuous weight multiplier. If pursued, use veto-style filters rather than multiplicative adjustments.

#### NB104 — Equal-weight matched age buckets

- **`age_bucket_equal` slightly outperforms smooth age_ramp** (Calmar 56.0 vs 54.25, CAGR 224% vs 217%).
- age_ramp with period=0.5y implicitly allocates: Young 2.5%, Mid 21.5%, Mature 76.1%.
- `age_bucket_underweight_young` is sensitive to `young_bucket_alloc` — best at 0.333 (equal), worst at 0.15.
- Bucket methods have lower Sharpe (2.70–2.75 vs 3.58) because they concentrate capital in fewer high-quality vaults.
- All methods match on max DD (-4%), so Calmar differences are entirely CAGR-driven.
- **Core insight:** the smooth ramp shape carries no additional information beyond bucket-level allocation. `age_bucket_equal` is simpler, more robust, and marginally better.

#### NB105 — Age-ramp by regime

- **The hypothesis was wrong.** Age ramp helps more in the mature period (+85% CAGR, +17% Sharpe, +51% Calmar) than in the early period (+37% CAGR, but -12% Sharpe, -36% Calmar).
- The mature period had far more new vault launches (69 vs 21), meaning the ramp does heavier work there.
- In low-volatility regimes, age ramp more than doubles the Calmar ratio (+121% vs +12% in high-vol).
- **Core insight:** age ramp is a durable edge across all tested regimes. Its primary mechanism is filtering newer, less proven vaults rather than dampening volatility spikes.
- Optimal `age_ramp_period` is 1.0 year for both methods, consistent with NB88.

#### NB106 — Concentration decomposition

- **Age ramp increases PnL concentration, not decreases it.** Top-3 share: 45.2% (age_ramp) vs 39.5% (equal_weight). Top-5 share: 62.1% vs 52.7%.
- Age ramp trades fewer vaults (52 vs 67), excluding ~15 young vaults.
- Both methods have identical max drawdowns (-4%), so Calmar differences are entirely CAGR-driven.
- Top PnL contributors differ: age_ramp reshuffles the winner ranking rather than spreading returns more evenly.
- **Core insight:** the mechanism is signal alignment (weighting older established vaults) and vault avoidance, not diversification.

#### NB107 — Ramp minimum-weight sensitivity

- **Previous finding corrected.** With all analysis cells now executed, the floor weight shows a clear inverted-U pattern.
- **Optimal range:** ramp_floor=0.10–0.15 (avg Calmar 44–47). Extremes perform much worse: floor=0.01 (avg Calmar ~19) and floor=0.25 (avg Calmar ~24).
- Too-low floor effectively excludes young vaults entirely after normalisation; too-high floor dilutes the age signal by giving young vaults too much weight.
- Best pick: age_ramp_period=0.50, ramp_floor=0.10.
- **Core insight:** the floor is not inert — it interacts with normalisation and position-cap constraints to create a meaningful performance surface. Recommended defaults: period=0.50, floor=0.10.

#### NB108 — Share-price slope stability

- **Trend R² (30-day window) is the strongest new signal:** 251% CAGR, 2.67 Sharpe, -4% max DD, Calmar 62.7.
- Trend smoothness is second-best (up to 233% CAGR, Calmar 58.2).
- Trend t-stat is the weakest — deepest drawdowns (-7% to -11%), lowest Sharpe (1.82–2.04). It conflates slope magnitude with fit quality.
- Equal weight remains the Sharpe champion (3.52), invariant to all parameters.
- Shorter trend windows (30 days) work best for R² and smoothness.
- **Core insight:** trend smoothness is more informative than raw age, but the Sharpe penalty from concentration risk suggests a blended approach would be better than standalone use.

#### NB109 — Volatility as veto

- **Best pick:** `age_ramp_volvol_penalty` (period=1.0, strength=0.2, window=30): 144% CAGR, 3.89 Sharpe, -3.12% max DD, 46.17 Calmar.
- Vol-of-vol is the only penalty variant that showed promise — beats equal_weight on Sharpe (+0.37) and drawdown.
- Realised vol and downside vol penalties consistently hurt returns (avg CAGR of 80% and 66%).
- Equal_weight remains rock-solid at 140% CAGR, 3.52 Sharpe with zero parameter sensitivity.
- **Core insight:** vol-of-vol as a soft veto can modestly improve risk-adjusted returns, but the improvement is narrow and parameter-sensitive. Not enough to justify added complexity.

#### NB110 — Recovery-adjusted momentum

- **age_ramp remains the best signal:** 217% CAGR, 3.58 Sharpe, 54.2 Calmar, -4.0% max DD.
- Recovery momentum has higher avg CAGR (196% vs 140%) but lower Sharpe (2.87 vs 3.36) — more aggressive but worse risk-adjusted.
- age_ramp_recovery overlay actually hurts: max DD worsens to -6.1%, Sharpe drops to 2.73.
- Recovery conditioning avoids the catastrophic failures of raw momentum from earlier notebooks, but improvement is insufficient.
- **Core insight:** recovery-conditioned momentum is valid but does not displace simpler age-based weighting.

#### NB111 — Drawdown asymmetry score

- Cache collision with NB88 fixed by hardcoding unique notebook ID and clearing stale cache.
- **pure_asymmetry dominates on Calmar** (mean 50.5, best 71.4) with the shallowest drawdowns (-3% best), but Sharpe is lower (2.36 mean).
- **asymmetry_overlay** can slightly beat age_ramp Sharpe baseline (3.62 vs 3.58) but does not improve Calmar.
- Best parameters consistently favour the 90-day lookback window and weakest overlay strength (0.1).
- **Core insight:** drawdown asymmetry is a strong standalone signal for drawdown control, but as a mild overlay on age_ramp it adds little. The standalone version trades Sharpe for much tighter drawdowns.

#### NB112 — Price-TVL interaction

- **`return_x_tvl_growth` delivers extreme CAGR** (~332% mean, 381% best) but roughly doubles max DD (-8.9% mean) and lowers Sharpe (2.58 mean).
- **`age_ramp_flow_confirmed` is the most balanced signal:** best config achieves 3.77 Sharpe (highest in the entire grid), 153% CAGR, -4% max DD.
- `flow_window=30` dominates across all interaction signals — recent capital flow is the most informative confirmation.
- **Core insight:** flow confirmation is genuinely informative. Use `age_ramp_flow_confirmed` for Sharpe stability, or `return_x_tvl_growth` for raw return maximisation. The CAGR-vs-Sharpe trade-off is real.

#### NB113 — Share-price contribution decomposition

- **equal_weight and age_ramp remain the best risk-adjusted methods** (Sharpe above 3.3, Calmar above 31).
- momentum_weight posts 352% CAGR but max DD balloons to -16.5%, Sharpe drops to 1.80.
- trend_weight is the most concentrated: top-1 share 18.7%, top-3 share 45.1%, kurtosis 16.1.
- **Leave-one-out:** equal_weight retains 78% of CAGR after removing top vault; trend_weight retains only 64%.
- Price signals load heavily on 2025Q4 cohort vaults (41–59% of PnL vs 7–18% for equal_weight/age_ramp) — they pick recent winners from a single vintage.
- **Core insight:** price-derived signals inflate CAGR through concentration on a handful of winners at the cost of 3–4× worse drawdowns. Apparent alpha is driven by a small number of lucky vaults, not genuine breadth.
