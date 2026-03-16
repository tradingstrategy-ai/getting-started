# Hyperliquid vault candidate signals

The five most interesting experiment results from 113 notebooks of vault-of-vaults research on Hyperliquid. Each signal below has survived at least one robustness check beyond pooled in-sample backtesting, uses genuinely different information from the others, and addresses a distinct dimension of the allocation problem.

## Selection criteria

- **Robustness:** survives walk-forward, regime splits, or parameter sensitivity analysis — not just one lucky in-sample run.
- **Real signal:** the mechanism is understood and makes economic sense, not just a statistical artefact.
- **Uncorrelated insight:** each candidate draws on different information (age, price trend quality, capital flows, drawdown behaviour, structural diversification) so they are not five variants of the same idea.

---

## 1. Age-based cohort allocation

**Signal:** penalise young vaults structurally — via a smooth ramp, three-bucket equal weight, or hard min_age filter.

**Best result:** age_ramp at period=0.5y — 217% CAGR, 3.58 Sharpe, -4% max DD, Calmar 58.5 (NB88). Three-bucket `age_bucket_equal` slightly outperforms the smooth ramp (Calmar 56.0 vs 54.25, NB104).

**Why it is real:**
- First signal to beat equal weight across 25+ notebooks (NB88).
- Survives walk-forward testing 3-0 on Calmar and Sharpe across all folds (NB100).
- Works across all time regimes and volatility regimes — helps more in the mature ecosystem period when new launches are frequent (NB105).
- Confirmed structural: all ramp shapes (linear, convex, step, logistic, concave, capped) beat equal weight at period=0.5y. The insight is "penalise youth", not a specific functional form (NB98).
- Age is genuinely informative, not a TVL proxy — controlling for TVL does not remove the age effect (NB99).

**Mechanism:** vault avoidance/selection, not sizing alpha. When the universe is held fixed, equal weight slightly wins (NB96). The ramp works by excluding or underweighting young vaults that have not yet proven themselves. Over 82% of PnL comes from vaults older than 180 days regardless of weighting method.

**Recommended production configuration:** age_ramp_period=0.50, ramp_floor=0.10 (NB107 inverted-U sensitivity analysis). Alternatively, a simpler three-bucket equal-weight split achieves the same result with fewer parameters (NB104).

**What it does not do:** it does not improve diversification — it actually increases PnL concentration (top-3 share 45.2% vs equal_weight's 39.5%, NB106). The mechanism is quality filtering, not portfolio construction.

---

## 2. Trend R² overlay on age ramp

**Signal:** R-squared of OLS regression on log share price over a 30-day window, applied as a mild multiplier on the age-ramp base weight.

**Best result:** 255% CAGR, -2% max DD, Calmar 127.5 at overlay_strength=0.3, overlay_window=30 (NB101). As a standalone signal: 251% CAGR, Calmar 62.7 (NB108).

**Why it is real:**
- Captures trend smoothness — whether a vault goes up consistently rather than in volatile jumps — which is a genuine proxy for manager quality and strategy stability.
- The only price-derived signal that consistently improved age_ramp across both NB101 (overlay) and NB108 (standalone). Momentum, Sharpe residuals, recovery momentum, and within-bucket ranking all failed the same test (NB89, NB101, NB102, NB110).
- Short lookback (30 days) works best, consistent with DeFi vault return dynamics where recent behaviour is most informative.
- Not a concentration trap: leave-one-out analysis shows it retains a meaningful fraction of CAGR after removing the top contributor (NB113 confirmed that other price signals fail this test).

**Mechanism:** measures process quality rather than outcome magnitude. A vault with high R² has a smooth equity curve — indicating a strategy that compounds steadily rather than one that had a lucky spike. This is fundamentally different from momentum (which chases magnitude) or Sharpe (which is noisy with short history).

**Key risk:** Sharpe drops from 3.58 to 2.67 when used standalone (NB108), indicating concentration into fewer smooth-trending vaults. The overlay approach (NB101) mitigates this by keeping age_ramp as the dominant factor with R² as a secondary tilt.

**Uncorrelated with signal 1:** age captures vault maturity; R² captures equity curve quality. A mature vault can have a choppy equity curve, and a younger vault can have a smooth one. The two dimensions are logically independent.

---

## 3. Flow-confirmed age ramp

**Signal:** age_ramp base weight multiplied by a TVL flow confirmation signal (recent TVL change over a 30-day window).

**Best result:** 153% CAGR, **3.77 Sharpe** (highest in the entire 113-notebook series), -4% max DD (NB112).

**Why it is real:**
- TVL change — not TVL level — is the informative dimension. NB99 showed age is not a TVL proxy, and NB103 showed TVL level as a multiplier is noisy. But NB112 found that TVL *flow* (recent change) genuinely confirms price signals.
- The Sharpe of 3.77 exceeds every other configuration tested across 113 notebooks, including plain age_ramp (3.58), equal_weight (3.52), and all standalone price signals.
- flow_window=30 dominates across all interaction variants, suggesting recent capital flow (not long-term TVL trend) is the useful confirmation.

**Mechanism:** a share-price move is more credible when accompanied by stable or rising TVL. Rising TVL while price holds means new followers are entering (capital confirmation). Falling TVL while price holds means existing followers are leaving (capital flight). The flow signal acts as a behavioural filter on whether the age-ramp-selected vaults have genuine follower conviction.

**Key risk:** not yet walk-forward validated. The Sharpe improvement over age_ramp is modest (3.77 vs 3.58) and could be parameter-specific. The raw `return_x_tvl_growth` variant delivers 381% CAGR but doubles max DD to -8.9%, showing that the flow signal without age-ramp discipline is a concentration trap.

**Uncorrelated with signals 1 and 2:** age captures maturity, R² captures equity curve quality, flow captures capital behaviour. A vault can be old with a smooth equity curve but losing followers (flow-negative), or young with a choppy curve but attracting capital (flow-positive).

---

## 4. Drawdown asymmetry score

**Signal:** scores vaults by up/down capture ratio, crash-day participation, and recovery lag. Used as a standalone allocation (pure_asymmetry) or as a mild overlay on age_ramp.

**Best result:** pure_asymmetry — Calmar 71.4, -3% max DD, 214% CAGR, but Sharpe 2.36 (NB111). As overlay: Sharpe 3.62, slightly above age_ramp's 3.58.

**Why it is real:**
- Targets the part of price behaviour most likely to reflect manager discipline — how vaults behave in stress, not their average return.
- The standalone signal achieves the best Calmar and shallowest drawdown of any method tested (-3% max DD vs -4% for age_ramp), suggesting it identifies vaults with genuine tail-risk management.
- Best parameters favour the 90-day lookback and weakest overlay strength (0.1), indicating the signal is informative but should be applied gently.

**Mechanism:** vaults that participate less in market-wide drawdowns and recover faster are more likely to have active risk management or strategies that are genuinely uncorrelated with the broader vault ecosystem. This is manager-discipline information that is not captured by age, trend quality, or flow.

**Key risk:** the Sharpe trade-off is steep — pure_asymmetry drops Sharpe to 2.36 because it concentrates into fewer "safe" vaults, sacrificing upside breadth. As an overlay on age_ramp, the improvement is marginal (3.62 vs 3.58). Best used as a capital-preservation sleeve or veto filter rather than a primary allocation signal.

**Uncorrelated with signals 1–3:** age captures maturity, R² captures trend smoothness, flow captures capital conviction, asymmetry captures stress behaviour. A vault can be old, smooth, well-funded, but still participate heavily in drawdowns.

---

## 5. Hard TVL and age inclusion thresholds

**Signal:** hard minimum thresholds for vault inclusion — min_tvl and min_age — applied before any weighting method.

**Best result:** min_tvl=25k is robustly optimal across all age levels (NB87). Loosening min_age from 0.3y to 0.05y improved Calmar by 63% (NB87). Combined with age_ramp: 305% CAGR, 3.43 Sharpe, Calmar 76.25 (NB93 soft prior variant).

**Why it is real:**
- min_tvl=25k is the single most consistent finding across the entire notebook series — it appears as optimal or near-optimal in NB75, NB87, NB93, and NB99.
- NB97 showed the min_age threshold is the dominant factor in the ramp-vs-filter comparison, more important than whether the penalty is smooth or binary.
- NB83 showed the Bayesian credibility gate became redundant once hard min_tvl and min_age thresholds were in place — every vault passing these criteria automatically had a positive gate signal.
- NB87's 56-point exhaustive grid over min_tvl × min_age provides the most comprehensive parameter surface in the series.

**Mechanism:** hard thresholds are the bluntest form of quality filtering — they exclude vaults that are too young to have a meaningful track record or too small to absorb meaningful capital. Unlike smooth ramps, they create a clean binary partition: either a vault is in the universe or it is not. The simplicity is the feature — there are no estimation errors, no parameter sensitivity within the included set, and no interaction effects with other signals.

**Key risk:** hard thresholds are regime-dependent. NB87's extended backtest revealed that the sparse April–July 2025 period matters: young vaults that survived the early ecosystem are winners. Loosening min_age to 0.05y improved performance precisely because it kept these early survivors in the universe. The optimal thresholds may shift as the Hyperliquid vault ecosystem matures.

**Uncorrelated with signals 1–4:** while age thresholds and age_ramp both use vault age, they operate at different stages of the pipeline. Thresholds determine universe membership (who is eligible); the other four signals determine allocation within the eligible set. A vault passing min_age=0.05 still gets full age_ramp, R², flow, and asymmetry treatment.

---

## How these five signals relate to each other

| Signal | Information used | Pipeline stage | Primary benefit | Key limitation |
|---|---|---|---|---|
| Age cohort allocation | Vault inception date | Weighting | CAGR uplift via young vault avoidance | No sizing alpha within the included set |
| Trend R² overlay | Share price path quality | Weighting overlay | Calmar uplift via smooth-trend tilt | Sharpe penalty from concentration |
| Flow-confirmed age ramp | TVL change × age | Weighting interaction | Highest Sharpe (3.77) | Not walk-forward validated |
| Drawdown asymmetry | Stress behaviour | Standalone or veto | Shallowest max DD (-3%) | Sharpe drops as standalone |
| Hard inclusion thresholds | TVL level + age | Universe construction | Clean universe, no estimation error | Regime-dependent optimal levels |

The five signals are designed to stack: hard thresholds define the universe → age cohort allocation sets the base weights → trend R² and flow confirmation refine the weights → drawdown asymmetry acts as a final veto or capital-preservation sleeve.

---

## What did not work

For completeness, here are the major categories of signals that were tested and consistently failed across the 113-notebook series:

- **Raw momentum and Sharpe-based weighting** (NB62–NB64, NB89, NB110): chases recent winners, concentrates into volatile vaults, 3–4× worse drawdowns.
- **Metadata multipliers** (NB70–NB71, NB103): TVL growth, stability, follower metrics — too noisy as continuous weight multipliers.
- **Within-group ranking** (NB86, NB102): ranking vaults by any signal within age buckets or quality tiers consistently underperformed equal weight within the same groups.
- **Correlation-based diversification** (NB88, NB94): noisy correlation estimates in small samples; shrinkage helped directionally but not enough to beat simpler methods.
- **Regime-switching and dispersion-based methods** (NB72b, NB91): insufficient sample depth for stable regime fingerprints; dispersion switches activated too rarely.
- **Volatility ranking** (NB35, NB37, NB58, NB84a, NB109): realised vol and downside vol penalties consistently destroy returns. Only vol-of-vol showed a fragile improvement.
- **Recovery momentum** (NB110): avoids catastrophic failures of raw momentum but cannot displace structural signals.
- **Underwater geometry** (NB90): biased against young vaults still building their first equity run-up.

---

## Next 10 experiments

These experiments are designed to validate and combine the five candidate signals above. They prioritise **Sharpe** over Calmar as the optimisation target for stability, given limited backtesting history where a single lucky CAGR spike can inflate Calmar without indicating robust risk-adjusted performance.

### Why optimise for Sharpe

Calmar is dominated by a single worst-drawdown event. With ~11 months of Hyperliquid vault history, there are at most 2–3 independent drawdown episodes, making Calmar a noisy estimator. Sharpe uses every daily return, giving ~230 independent observations — a much more stable target for parameter selection. Several earlier notebooks (NB101, NB108, NB112) showed signals that looked excellent on Calmar but suffered Sharpe degradation from concentration, which is the more dangerous failure mode in production.

---

### NB114 — Walk-forward validation of flow-confirmed age ramp

- **Goal:** determine whether `age_ramp_flow_confirmed` (Sharpe 3.77 in NB112) survives out-of-sample testing or is a parameter-specific in-sample artefact.
- **Hypothesis:** the flow confirmation signal retains a Sharpe advantage over plain age_ramp on holdout folds.
- **Test shape:** replicate NB100's walk-forward matrix (expanding + rolling folds) but compare `age_ramp`, `age_ramp_flow_confirmed`, and `equal_weight`. Optimise for Sharpe on training folds, report holdout Sharpe, Calmar, and parameter drift.
- **What to report:** fold-by-fold Sharpe win/loss/tie scorecard; whether `flow_window=30` is consistently selected; whether parameter choices are stable across folds.
- **Success condition:** `age_ramp_flow_confirmed` wins ≥2/3 folds on holdout Sharpe and the selected parameters are stable.
- **Why this matters:** NB112 is the strongest Sharpe result in 113 notebooks but has zero out-of-sample validation. This is the single highest-priority experiment.

### NB115 — Stacked signal: age ramp + R² overlay + flow confirmation

- **Goal:** test whether combining the top two overlay signals (trend R² from NB101 and flow confirmation from NB112) on top of age_ramp produces additive Sharpe improvement or whether they are redundant.
- **Hypothesis:** the two overlays capture different information (equity curve quality vs capital behaviour) and combining them beats either alone on Sharpe.
- **Test shape:** four-arm comparison: (A) age_ramp only, (B) age_ramp + R² overlay, (C) age_ramp + flow confirmed, (D) age_ramp + R² + flow. Grid over overlay_strength and flow_strength with both at [0.1, 0.2, 0.3]. Optimise for Sharpe.
- **What to report:** whether the combined signal (D) improves Sharpe over the best single overlay; whether the two overlay strengths interact or are independent; concentration diagnostics.
- **Success condition:** the combined signal achieves higher Sharpe than either overlay alone without materially increasing max DD.
- **Why this matters:** if the two signals are genuinely uncorrelated, stacking should improve risk-adjusted returns. If they are redundant, we should pick the simpler one.

### NB116 — Age bucket equal weight with Sharpe optimisation

- **Goal:** re-test the three-bucket equal-weight approach (NB104) with Sharpe as the optimisation target and a wider parameter search over bucket boundaries.
- **Hypothesis:** optimising for Sharpe rather than Calmar will favour a different bucket structure — possibly more balanced allocation across cohorts rather than extreme mature-vault concentration.
- **Test shape:** vary bucket boundaries (young/mid/mature thresholds at 30/60/90/120/180/365 days), number of buckets (2, 3, 4), and whether buckets are equal-capital or proportional-to-count. Optimise for Sharpe.
- **What to report:** optimal bucket boundaries; Sharpe surface smoothness; whether the result is meaningfully different from the Calmar-optimised NB104 configuration.
- **Success condition:** a bucket configuration that achieves Sharpe ≥ 3.5 with stable parameters across nearby grid points.
- **Why this matters:** NB104 showed bucket allocation is the true mechanism behind age_ramp. If the Sharpe-optimal version is simpler (e.g., just 2 buckets: young vs mature), it strengthens the production case for replacing the smooth ramp entirely.

### NB117 — Drawdown asymmetry as a veto filter, not a weight signal

- **Goal:** test whether using asymmetry scores as a binary veto (exclude the worst-asymmetry vaults) is more effective than using them as continuous weights.
- **Hypothesis:** a veto approach preserves the Sharpe advantage of equal_weight or age_ramp while capturing the drawdown protection that pure_asymmetry demonstrated (NB111).
- **Test shape:** compute asymmetry scores for all vaults, then exclude the bottom 10%/20%/30% by asymmetry rank before applying age_ramp + equal weight. Compare against (A) no veto, (B) continuous asymmetry overlay, (C) pure_asymmetry standalone. Optimise for Sharpe.
- **What to report:** Sharpe at each veto threshold; number of vaults excluded; whether excluded vaults actually contributed negative PnL in the no-veto scenario.
- **Success condition:** a veto threshold that improves Sharpe over plain age_ramp without reducing the tradeable universe below 20 active positions.
- **Why this matters:** NB103 and NB109 both showed that continuous multipliers from secondary signals tend to inject noise. A veto approach is the simplest way to extract the asymmetry signal's drawdown benefit without degrading Sharpe.

### NB118 — Min_tvl and min_age threshold stability under Sharpe optimisation

- **Goal:** re-run NB87's exhaustive min_tvl × min_age grid but optimising for Sharpe instead of Calmar, and extend to the full available history starting 2025-01-01.
- **Hypothesis:** Sharpe-optimal thresholds will be looser than Calmar-optimal ones (lower min_tvl, lower min_age) because Sharpe rewards diversification breadth whereas Calmar rewards drawdown avoidance.
- **Test shape:** 7 × 8 grid over min_tvl [2.5k, 5k, 10k, 25k, 50k, 75k, 100k] × min_age [0.0, 0.05, 0.1, 0.15, 0.25, 0.3, 0.5, 0.75]. Equal weight within. Backtest from 2025-01-01. Optimise for Sharpe.
- **What to report:** Sharpe surface heatmap; whether min_tvl=25k remains optimal; whether looser min_age improves Sharpe; the trade-off between universe breadth and quality.
- **Success condition:** identify a robust Sharpe plateau (not a knife-edge optimum) for the threshold pair.
- **Why this matters:** the inclusion thresholds are the most impactful parameter choice in the entire pipeline (NB75, NB87, NB97). Getting them right under Sharpe optimisation is foundational for everything that follows.

### NB119 — Cross-validation of trend R² overlay stability

- **Goal:** determine whether the R² overlay's strong Calmar result (127.5 in NB101) holds under Sharpe optimisation and walk-forward validation, or whether it is a Calmar-specific artefact driven by a single shallow-drawdown period.
- **Hypothesis:** R² overlay improves holdout Sharpe but by a smaller margin than it improves Calmar, because R² concentrates into fewer vaults.
- **Test shape:** walk-forward folds (expanding + rolling) with R² overlay strength [0.1, 0.2, 0.3] and overlay_window [14, 30, 60]. Compare age_ramp + R² overlay vs age_ramp alone. Optimise training for Sharpe. Report holdout Sharpe, concentration (effective N), and leave-one-out CAGR retention.
- **What to report:** fold-by-fold Sharpe win/loss/tie; whether R² overlay strength drifts across folds; concentration penalty.
- **Success condition:** R² overlay wins ≥2/3 folds on holdout Sharpe with effective N ≥ 15.
- **Why this matters:** R² is the most promising price overlay but NB108 showed it drops Sharpe when used aggressively. Walk-forward under Sharpe optimisation will reveal whether a light-touch overlay survives or whether the signal concentrates too much for production.

### NB120 — Sensitivity to backtest start date

- **Goal:** test whether the candidate signals are robust to the choice of backtest start date, which determines how much early-ecosystem data (April–July 2025) is included.
- **Hypothesis:** signals that rely on structural information (age, TVL thresholds) will be robust to start date; price-derived signals (R², flow) will be more sensitive.
- **Test shape:** run the stacked signal (age_ramp + R² + flow) and plain age_ramp across five start dates: 2025-01-01, 2025-04-01, 2025-06-01, 2025-08-01, 2025-10-01. Same end date. Optimise for Sharpe.
- **What to report:** Sharpe degradation curve as history shrinks; whether any signal loses its edge entirely at a particular start date; effective universe size at each start date.
- **Success condition:** the stacked signal maintains Sharpe advantage over equal_weight across all start dates, even if absolute performance changes.
- **Why this matters:** with only ~11 months of Hyperliquid vault history, any finding could be dominated by one sub-period. NB105 already showed the early period is qualitatively different. If the signals only work from August 2025 onward, they may be ecosystem-maturity effects rather than durable rules.

### NB121 — Fundamental analysis: vault strategy type decomposition

- **Goal:** decompose PnL by vault strategy type (delta-neutral market-making, directional perps, basis trading, funding rate farming, etc.) to understand whether the candidate signals are picking strategy types rather than individual vault quality.
- **Hypothesis:** age_ramp's edge may partly come from avoiding new entrants in crowded strategy types (e.g., many young vaults are delta-neutral copycats) rather than from vault-level age information.
- **Test shape:** classify vaults into strategy type buckets using vault descriptions and metadata. Run equal_weight and age_ramp within each strategy type. Compare per-type Sharpe, CAGR, and drawdown. Check whether age_ramp's advantage disappears within homogeneous strategy groups.
- **What to report:** per-strategy-type performance table; whether age_ramp's edge is uniform or concentrated in specific strategy types; whether the candidate signals pick the same or different strategy types.
- **Success condition:** understand whether we are selecting good vaults or good strategy types. If the latter, we may need strategy-type diversification constraints.
- **Why this matters:** this is the most important question we have not yet asked. If all five candidate signals implicitly select the same strategy type (e.g., mature market-makers), the portfolio may have hidden systematic risk from strategy-type concentration. Production needs to know this.

### NB122 — Sharpe-optimised full pipeline backtest

- **Goal:** run the complete stacked pipeline (hard thresholds → age bucket allocation → R² overlay → flow confirmation → asymmetry veto) with all parameters jointly optimised for Sharpe.
- **Hypothesis:** the full pipeline achieves a higher Sharpe than any individual component, demonstrating that the signals stack rather than cancel.
- **Test shape:** use the best parameter choices from NB114–NB119 as starting points. Grid over the remaining interaction parameters (overlay strengths, veto threshold, bucket boundaries). Optimise for Sharpe. Report full metrics plus concentration, turnover, capital utilisation, and number of active positions.
- **What to report:** whether the stacked pipeline beats the best single signal on Sharpe; parameter interaction effects; turnover cost sensitivity; capital utilisation.
- **Success condition:** Sharpe ≥ 3.8 with max DD ≤ -5%, effective N ≥ 15, and reasonable turnover (< 20% daily).
- **Why this matters:** this is the integration test. Individual signals can look good in isolation but cancel or interfere when stacked. The full pipeline backtest reveals whether the candidate signals are genuinely complementary or merely different views of the same information.

### NB123 — Walk-forward validation of the full pipeline

- **Goal:** final out-of-sample validation of the NB122 pipeline using rolling walk-forward folds with Sharpe as the holdout metric.
- **Hypothesis:** the stacked pipeline retains its Sharpe advantage over equal_weight and plain age_ramp on holdout data.
- **Test shape:** 3–4 rolling folds with 90-day training windows and 30-day holdout periods. Compare (A) equal_weight, (B) age_ramp, (C) full pipeline. Freeze pipeline parameters from NB122's best training result or allow walk-forward re-optimisation. Report holdout Sharpe, Calmar, parameter stability, and turnover.
- **What to report:** fold-by-fold Sharpe scorecard; parameter drift across folds; whether the pipeline degrades more or less than individual components on holdout; worst-fold drawdown.
- **Success condition:** full pipeline wins ≥ 3/4 folds on holdout Sharpe and no fold has max DD worse than -8%.
- **Why this matters:** this is the final gate before production. If the pipeline cannot beat age_ramp out of sample, then the additional complexity is not justified and we should deploy plain age_ramp (or age_bucket_equal) as the production strategy. If it does beat age_ramp, we have a validated multi-signal allocation system ready for live deployment.

---

### Recommended execution order

1. **NB118** (threshold stability) — foundational; all other experiments depend on getting the universe right.
2. **NB114** (flow walk-forward) — highest-priority single-signal validation.
3. **NB119** (R² walk-forward) — second-priority single-signal validation.
4. **NB116** (bucket Sharpe optimisation) — simplification of the base weighting layer.
5. **NB117** (asymmetry veto) — test the cleanest way to use the asymmetry signal.
6. **NB121** (strategy type decomposition) — fundamental analysis to understand what we are actually selecting.
7. **NB115** (stacked signal) — test whether R² and flow are additive.
8. **NB120** (start date sensitivity) — robustness check before integration.
9. **NB122** (full pipeline) — integration test.
10. **NB123** (walk-forward of full pipeline) — final validation gate.
