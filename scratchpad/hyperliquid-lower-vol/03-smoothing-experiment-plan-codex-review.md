# Critical review

## 1. Flaws and risks in the plan as written

- The plan omits the chain’s most important measurement warning: stale vault NAVs, a reporting-regime break around April, and a much smaller effective sample size than daily observations imply. NB57, “Finding 3”, found 28–57% zero-return vault days and explicitly says Sharpe, drawdown and feature comparisons are distorted unless reported on a staleness-aware/weekly basis and split by regime. The plan’s NB03 should establish this before treating downside deviation, ulcer, best-day share or beta as investable signals.

- “All features via `get_indicator_value(..., index=-1)`” is necessary but not sufficient. NB57’s correction confirms the framework path is correctly aligned, but it also shows that direct daily-panel calculations had a full-bar look-ahead. Each new custom feature needs an as-of-availability/timestamp audit, not merely an assertion that it is an indicator. This is particularly important for residual NAV construction, rolling beta, TVL trajectory and deposit flags.

- The proposed feature gate is under-powered and partly ill-defined. A 30-day forward Martin ratio for a cross-sectional top-six screen is noisy, overlapping, and has only about eight non-overlapping observations in this backtest. NB47, “Robustness”, already describes its 23 fortnightly observations as directional rather than fine-grained. NB57, “Finding 2”, estimates that even the older, longer sample could not reliably detect the adopted-size effects. The gate should be descriptive/pre-screening only, not evidence that a feature works.

- The plan repeatedly selects on the full January–September period and only then proposes a “fit/test” check in NB10. That is not out-of-sample: NB04–NB09, their sweeps, and the choice of which variants to combine have already consumed the proposed test period. Lock a last-period hold-out before any variants are examined, or use a pre-specified expanding walk-forward protocol throughout.

- The half-split requirement is not meaningful validation. Each half has roughly four months, the first crosses a data-quality regime change, and a 30-day-forward feature has only a few effectively independent outcomes. “Positive in both halves” has no effect-size or uncertainty requirement, so it can both discard a real effect and admit a trivial one.

- Portfolio beta is specified incorrectly for the stated goal. “Mean portfolio BTC beta down” can be achieved by becoming more negatively beta, or simply holding more cash. Measure absolute invested-basket beta, beta confidence/R², and residual return separately; report cash-inclusive beta only as an exposure result. NB42 tested `|beta|`, not signed beta, and found most apparent benefit was generic de-risking.

- NB07 repeats a previously gated-out idea without a sufficiently changed premise. NB47 found residual-composite top-six forward return of 0.33% versus 0.70% for the incumbent. Changing the evaluation objective from Sharpe to Martin does not itself make residual CAGR a better selector. Keep it as an NB03 measurement candidate; do not allocate a full backtest unless it clears a stronger, staleness-aware screen.

- NB08’s `best5_share_180` penalty is unstable. The ratio is undefined or explosive when trailing total return is near zero or negative; clipping at one discards useful ordering exactly among the worst cases; and it conflates legitimate positively skewed trend-following with a single untradeable mark. NB83 shows why a random-removal null is required, while NB84 shows that event concentration can be timing luck. Define the statistic on residual log returns and require adequate fresh observations before it can affect ranking.

- NB09’s missing-history rule is an implicit age policy. Scoring a young vault on “the windows it has” is not a minimum-across-windows consistency score comparable with a 360-day-old vault. It recreates the permissive-history problem in NB78, where the NaN-tolerant ensemble was catastrophic, and mixes consistency with maturity. Either require the same windows for all candidates or run a separately identified young-vault experiment.

- NB06’s proposed “continuous cap” is not a cap. Multiplying weight by `min(1, 0.60 / vol_90)` penalises high-volatility vaults while leaving low-volatility vaults uncapped; after normalisation it can further concentrate capital in the low-volatility loser cohort identified in NB77. Ulcer and downside deviation have the same stale-NAV vulnerability: a vault with no reported down days can receive an extreme weight. Use floors, observation-quality requirements and an actual maximum weight/risk-contribution limit.

- The capacity rationale for NB05 is too optimistic. More discarded liquidity does not imply more safely deployable names. The baseline still permits 33% of pool TVL per position; NB84 found large gains came from implausibly large fractions of tiny vaults and recommends a low single-digit TVL cap. Increasing breadth before making the pool-cap model realistic can spread capital into more untradeable marks.

- The “luck ratio”, top-five net-profit share and largest-position stress are not sufficiently defined. Net profit can be close to zero or negative, making contribution shares misleading. “Remove the largest position” must mean a full re-simulation with that vault unavailable from the start, not subtracting realised P&L; NB83, “Robustness”, explicitly says the latter is not a portfolio counterfactual.

- The plan has substantial family-wise model-selection risk: five volatility targets, nine breadth/cap cells, several sizing methods, beta variants, four penalty strengths, two consistency rules, then combinations. Plateau checks reduce but do not solve this. There is no paired block-bootstrap confidence interval, reality-check-style correction, or pre-declared one-winner-per-family rule.

- The retrospective live-book comparison is contaminated by its role in motivating the plan. The known Octavious/DOEZOE/Sequoia failures are useful case studies, but making a rule pass because it would have avoided them is outcome fitting. It is not independent out-of-sample validation.

## 2. Answers to the open questions

1. **Martin ratio or CAGR with a volatility ceiling?**  
   Use constrained optimisation: retain CAGR ≥30%, require annualised volatility no worse than the 15.47% anchor and a materially lower ulcer index, then use Martin ratio as the ranking/tie-break metric. Martin alone is too easily improved by cash.

2. **Time-in-market floor?**  
   Yes, but separate it from the cash-overlay result. Require at least 45% active days versus the anchor’s 50%, and report mean invested exposure and return per unit of invested exposure. A result below that is valid only as a separately labelled cash-overlay strategy, not evidence that selection improved.

3. **Is a 30% CAGR floor right?**  
   Keep it. It already permits a 7.9 percentage-point sacrifice from the 37.90% anchor. Lowering it on this short, selected sample would make “smoothness” too easy to buy with cash. Revisit only after prospective frozen-spec evidence.

4. **What is missing from NB03?**  
   Add: fresh-versus-stale NAV flags and observation density; beta confidence/R² and beta stability; residual-event concentration; TVL growth/change in liquidity relative to requested position; deposit/redemption availability history; drawdown duration/recovery; and independent vault metadata such as leader stake, commission, follower growth, volume and account P&L. NB57, “Stage C”, identifies the latter as less dependent on stale share prices.

5. **Should the retrospective shadow comparison be a hard gate?**  
   No. Keep it as a diagnostic case study. Make a prospective, frozen-spec shadow period the hard pre-deployment gate instead: for example, a minimum number of decision cycles and an explicit capacity/availability audit. The existing live book is one labelled failure sequence, not an unbiased test set.

## 3. Missing ideas

| Idea | Mechanism | What could go wrong | Placement |
|---|---|---|---|
| Fresh-NAV and mark-quality score | Selection/eligibility | May exclude legitimate low-turnover vaults and reduce the universe | New NB03a, before every alpha experiment |
| Residual return concentration: top-k residual-day share, positive residual-window share, beta stability/R² | Selection | Penalises valid convex or trend-following vaults; sparse marks make residuals noisy | NB03 screen, then a replacement for NB08 if it passes |
| TVL trajectory, pool-capacity ratio, deposit/redemption liveness and follower crowding | Structure/eligibility | Can become a backward-looking popularity filter | New capacity notebook before breadth; do not treat all of it as alpha |
| Drawdown duration and recovery speed, measured only on fresh observations | Selection or exit sizing | Can chase already recovered vaults and miss genuine turnaround returns | New NB07, not folded into beta residual CAGR |
| Portfolio marginal risk contribution and residual correlation caps | Sizing | Correlations and covariances are unstable with short/stale histories | Replace the malformed third arm of NB06 |
| Profit-ratchet sizing: retain a small core but de-risk a vault after an extreme idiosyncratic residual jump | Sizing/structure | NB84 indicates top-ups into winners generated much of the return, so this can directly cut CAGR | New notebook only after selection and capacity are fixed |

## 4. Ordering and scope

Split NB03 into:

1. NB03a: data availability, staleness, regime split, baseline attribution, power calculation.
2. NB03b: a frozen, decision-aligned feature screen using only reliable observations.

Move capacity realism ahead of breadth. Establish a realistic per-vault TVL cap before using discarded liquidity as a reason to add more names.

Split NB05: test breadth at fixed caps first; only then test concentration around a pre-specified breadth. The present 3×3 grid is nine model choices, not one structural change.

Split NB06. Test one drawdown-risk sizing family at a time, with actual weight caps and risk floors. Drop the proposed volatility multiplier as written.

Defer NB07 unless it clears NB03b. NB47’s residual result is a strong reason not to spend another full in-sample backtest on it.

Keep NB08 and NB09 separate, but require comparable history and fresh-observation rules. Do not combine “Adopt and Provisional” results: provisionals failed a stated gate and should not be promoted by combination. NB10 should combine only pre-specified Adopt winners, with parameters frozen before the hold-out. Merge NB11 into NB10’s final validation/close-out.

The adoption rule is simultaneously too loose statistically and too tight mechanically. It is loose because it permits selection across many variants without uncertainty or multiplicity control; it is tight because arbitrary all-or-nothing half-split and 25% Martin thresholds are under-powered on this sample. Replace them with pre-specified constraints, a detectable-effect threshold, paired uncertainty intervals, and one externally frozen validation.

## 5. Prioritised top-five changes to the plan

1. Add mandatory NB03a measurement work: fresh/stale NAV flags, weekly/staleness-aware results, regime split, availability audit and effective-sample/power calculation, following NB57 “Stage A”.

2. Reserve the final period before running any variants. Apply the same frozen development/hold-out or expanding walk-forward design to every experiment; remove NB10’s retrospective “fit/test” claim.

3. Replace the adoption rule with CAGR ≥30%, volatility ≤15.47%, lower ulcer, lower absolute invested-basket BTC beta, actual leave-one-vault-out re-runs, paired confidence intervals, and a one-winner-per-family rule.

4. Correct NB06 and capacity sequencing: impose an actual per-vault capacity limit, then test risk-contribution sizing with floors and weight caps. Do not use `min(1, 0.60 / vol_90)` as a purported cap.

5. Defer NB07, rewrite NB08’s event-concentration metric, and make NB09 history-comparable. Neither should proceed merely because the full-period top-six screen looks better.