# Rebalancing method trial plan

## Objective

Create `04-backtest-rebalancing-method-trials.ipynb` as a variant of `03-backtest-25000-initial-capital.ipynb`. Run every distinct method catalogued in `scratchpad/vault-of-vaults/rebalanching-trials.md` against the new Hyperliquid vault universe and report a controlled comparison. Keep the trial reproducible, prevent indicator-level look-ahead, disclose inherited universe survivorship limitations, and make method-level implementation differences explicit.

## Fixed experiment controls

The following settings stay identical to notebook 03 unless a method's defining feature explicitly changes one of them:

- Hyperliquid source vault universe built by `build_hyperliquid_vault_universe()`.
- USDC-family denomination filter and the same supporting benchmark pairs.
- Daily candles and daily decision cycle.
- Backtest period `2025-08-01` to the exclusive boundary `2026-07-10`.
- Initial capital `25,000 USD`, target allocation `98%`, maximum 20 positions, maximum position weight `12%`, and per-pool cap `20%`.
- Hard eligibility floors of `7,500 USD` TVL and `0.075` years of age.
- Full-history indicator loading, quarantine checks, slippage, minimum vault deposit, and buy/sell rebalance thresholds from notebook 03.
- No method may use price, TVL, age, or cross-sectional observations after the decision timestamp.

The primary comparison uses the redemption-aware portfolio target from notebook 03. Historical allocator trials whose defining feature is the target/deployment mechanism will state and isolate that difference in the configuration table.

### Universe point-in-time limitation

`build_hyperliquid_vault_universe()` selects addresses from the current `top-defi-vaults` snapshot and caches that address list. Historical price availability, age, and TVL eligibility are evaluated point in time, so a vault cannot trade before it exists or before it passes the dynamic floors; however, the outer address membership is not a reconstructed historical snapshot. This trial therefore inherits notebook 03's static-membership survivorship bias and must not claim a fully point-in-time universe.

The notebook will record the curator fingerprint, cache filename/mtime, selected address count, first price timestamp per vault, and the generated-at timestamp from the downloaded universe metadata where available. This is a disclosure and audit of the fixed requested universe, not an attempt to replace it with a different universe.

### Parameter provenance and evaluation split

Most historical winning constants were selected on data overlapping `2025-08-01` to `2026-03-11`. They may be run because the user requested all historical methods, but their full-period scores are exploratory and labelled `historical-overlap`, not clean out-of-sample evidence.

The notebook will produce two scorecards from each backtest:

- Full requested period: `2025-08-01` to `2026-07-09`, used for operational comparison.
- Clean extension holdout: `2026-03-12` to `2026-07-09`, which starts after the common historical research cut-off and is the primary ranking for conclusions.

Before implementation, every method-specific numeric constant must be copied into `TrialConfig` with its source notebook and source cell or heading note. This includes PSR floor/multiplier/window, Sterling constant, Bayesian half-life, signal windows, gate thresholds, softmax temperature, TVL soft-floor bounds, trend-overlay strength, age-bucket boundaries, vol-of-vol penalty bounds, correlation window/linkage threshold, capacity clip, and hold duration. No undocumented approximation may silently stand in for a source constant; if a source does not identify a fixed winner, the trial row is marked `approximation` and excluded from winner claims.

## Trial architecture

1. Copy notebook 03 to the next numbered backtest notebook and replace its inherited findings with the new hypothesis and an empty results section.
2. Add the common rolling indicators needed by the catalogue: daily returns, rolling return, volatility, downside volatility, Sharpe, Sortino, Calmar, PSR, Bayesian credibility, trend R-squared, volatility of volatility, TVL soft prior, age-bucket weights, and correlation-cluster weights.
3. Represent each method as a declarative `TrialConfig` containing its source ID, human name, selector, weighting transform, allocator, cash-target policy, and optional minimum holding period.
4. Precompute one immutable, timestamp-indexed feature panel and reuse it across all 31 trials. Correlation clustering uses deterministic average-linkage hierarchical clustering, a 60-day trailing window, and distance threshold `0.5`; its timestamp results are cached and never recomputed inside each trial cycle.
5. Use one decision-function factory so every trial shares universe filtering, quarantine handling, risk sizing, trade thresholds, and diagnostics. Keep the six subtle survivor-first allocator branches in explicit named handlers within the factory rather than a loose combination of booleans.
6. Profile NB158 and NB128 over a 30-day dry run, estimate total runtime, and inspect peak RSS before executing the full matrix. Split the matrix across multiple notebook cells or raise the per-cell timeout if the estimate approaches 15 minutes.
7. Execute trials sequentially with one worker. Retain compact summaries for every run and full state only for the target baseline plus the best holdout CAGR, Sharpe, and max-drawdown methods to avoid excessive memory use.
8. Render comparison tables sorted by holdout Sharpe with full-period and holdout CAGR, Sharpe, Sortino, max drawdown, cumulative return, trades, positions, final equity, mean accepted deployment, mean cash, provenance status, and implementation status.
9. Add focused charts for CAGR versus max drawdown, Sharpe by method, equity curves for retained winners, and a component-family comparison.

## Method mapping

| Source ID | Trial name | Planned implementation on the fixed universe | Special handling |
|---|---|---|---|
| NB22 | Inverse-volatility weighting | Weight eligible vaults by inverse rolling volatility. | Floor volatility before inversion and use only trailing data. |
| NB23a | Equal weight | Give all selected vaults identical raw weights. | Use the non-waterfall baseline normalisation. |
| NB23b | Log-signal weighting | Apply `log1p` compression to the positive age-ramp signal. | Preserve age-ramp ordering while reducing dispersion. |
| NB24 | Signal-ranked waterfall | Use log-compressed age-ramp ranking with waterfall normalisation. | Greedily recycle capacity down the ranked list. |
| NB26 | Sortino-based weighting | Weight by positive rolling Sortino. | Use a denominator floor and zero non-finite values. |
| NB27 | Sharpe-based weighting | Weight by positive rolling Sharpe. | Use the same trailing window as Sortino. |
| NB28 | Diversified waterfall | Apply waterfall with protocol concentration controls. | The chain cap is a no-op because the fixed universe is single-chain; report this explicitly. |
| NB29 | Dynamic diversified waterfall | Rank daily by rolling Sharpe and apply the diversified waterfall. | Selection and weights update each daily cycle; its inherited chain cap is also a no-op on the single-chain universe. |
| NB45 | Calmar-signal allocation | Weight by positive rolling Calmar. | Floor small drawdown denominators and pad only with past flat observations. |
| NB54 | PSR concentration | Use PSR both as signal confidence and as a continuous per-vault concentration multiplier. | Clip PSR to `[0, 1]`. |
| NB59 | Linear PSR gate | Exclude low-PSR vaults and linearly scale the survivors between floor and ceiling. | Keep the historical soft-gate shape. |
| NB60 | Bayesian credibility weighting | Shrink rolling-return signals towards the cross-sectional prior according to available history. | Compute the prior from same-timestamp eligible vaults only. |
| NB63 | Softmax allocation | Convert standardised trailing signals to softmax weights. | Use a numerically stable softmax and fixed temperature. |
| NB64 | Threshold-linear allocation | Map the trailing signal through a clipped piecewise-linear weighting rule. | Derive thresholds from trailing cross-sectional ranks, not future full-sample values. |
| NB66 | Dual-signal gate and weight | Gate with Bayesian credibility and weight survivors by rolling Sharpe. | Keep gate and sizing signals separate. |
| NB68 | Bayesian gate with equal weight | Gate with Bayesian credibility and equal-weight the survivors. | Use the same gate as NB66 for a clean weighting ablation. |
| NB71 | Rank-composite selection | Rank eligible vaults by trailing return, Sharpe, drawdown, age, and TVL, then select the top set. | Use cross-sectional percentile ranks available at the cycle timestamp. |
| NB88 | Age-ramp weighting | Use the notebook 03 `age_ramp` signal with non-waterfall normalisation. | This is the structural signal baseline. |
| NB93 | Age-TVL soft prior | Multiply age ramp by a clipped soft TVL factor. | Use current TVL only and preserve hard eligibility floors. |
| NB101 | Age ramp with trend overlay | Multiply age ramp by a mild trailing trend-R-squared overlay. | Fit the regression only over prices available before the rebalance. |
| NB102 | Age-bucket equal weight | Equal-weight within young, middle-aged, and mature cohorts and allocate equally across active cohorts. | Use the historical bucket boundaries as fixed constants. |
| NB109 | Volatility-of-volatility penalty | Apply a soft inverse vol-of-vol penalty to age-ramp weights. | Clip the penalty to prevent a zero-sized portfolio. |
| NB116 | Sharpe-optimised age buckets | Use the fixed winning bucket boundaries recorded by NB116. | Do not re-optimise boundaries on the new backtest. |
| NB128 | Correlation-cluster equal weight | Cluster trailing return correlations, equal-weight clusters, then equal-weight members. | Fall back to equal weight when history or cluster breadth is insufficient. |
| NB130 | Survivor-first renormalisation | Select the top 20 age-ramp survivors before normalising and size without recycling. | Use the redemption-aware target so only survivor-first ordering changes. |
| NB131 | Age-ramp selection with equal deployment | Select top age-ramp survivors and replace their signals with equal raw weights. | Keep non-waterfall deployment to reproduce the cash-drag mechanism. |
| NB142 | Equal-weight recycle | Equal-weight selected survivors and recycle unused capacity across names that can absorb it. | Use the fixed target and size-risk model from notebook 03. |
| NB143 | Capped survivor-first waterfall | Apply age-ramp ranking and capped waterfall sizing using plain current equity as the target. | This isolates the pre-release-candidate cash-target policy. |
| NB144 | Capacity-aware equal weight | Tilt equal weights by a clipped square-root TVL capacity factor. | Keep non-waterfall recycling semantics from the source experiment. |
| NB152 | Equal-weight recycle with minimum hold | Run NB142 allocation with a three-day minimum hold before discretionary full exits. | Keep an otherwise-eligible young position in the selected set until day three; quarantine, `state.is_good_pair()` failure, and loss of hard eligibility bypass the hold on the next daily cycle. Count blocked selections explicitly. |
| NB158 | Waterfall release candidate | Apply age-ramp ranking, capped waterfall sizing, and the redemption-aware target from notebook 03. | This is the exact controlled baseline for the new universe. |

## Fairness and interpretation

- Results compare methods on one fixed universe and period; they must not be compared directly with the historical metrics in `rebalanching-trials.md`.
- The table will label each method as `selector`, `weight`, `allocator`, or `combined`, because methods from different layers are not pure one-variable ablations.
- Any source method that cannot retain its original meaning on this single-chain universe will still run with the closest faithful implementation and an explicit caveat.
- Optimiser-derived methods use their historical fixed winning parameters. The new trial does not tune on the evaluation period.
- Missing indicator history causes a conservative equal-weight or no-entry fallback, never a forward-filled future value.
- Failed methods sort last with Sharpe treated as negative infinity, while preserving the exception class and message.
- `accepted deployment` means accepted investable equity divided by the redemption-aware portfolio target after size-risk caps; component-family charts group rows by `selector`, `weight`, `allocator`, or `combined`.

## Execution and validation

Run the notebook in the foreground with visible progress:

```shell
TQDM_LOGGABLE_FORCE=stdout poetry run jupyter execute scratchpad/hyperliquid-waterfall-rc/04-backtest-rebalancing-method-trials.ipynb --inplace --timeout=-1
```

Validation checks:

- All 31 catalogue IDs appear exactly once in the configuration and result tables.
- NB158 is an execution gate: retain notebook 03's strategy code and state as the exact control run. Compare its current metrics with notebook 03's stored output and disclose any drift caused by a refreshed remote universe or cache snapshot; stale saved metrics are not a valid hard failure when the copied control code is unchanged.
- Every result has finite CAGR, Sharpe, and max drawdown or a recorded failure reason.
- Trial start/end dates, universe count, capital, and execution thresholds are identical across successful methods except for declared method-specific mechanics.
- No configuration reads a future timestamp or uses a full-sample normalisation statistic.
- Assert the last decision and indicator timestamp is `2026-07-09` and that no computation reads the exclusive `2026-07-10` bar.
- Assert rolling-indicator warm-up periods follow the documented equal-weight or no-entry fallback and produce no NaN raw weights.
- Log every day with fewer than 20 eligible candidates and summarise the minimum, median, and final eligible breadth.
- Compare final equity, trade count, utilisation, and candidate counts for implausible outliers.
- Inspect the strongest day, skew, kurtosis, largest vault contribution, and top-five PnL concentration for the leading methods.
- If a method fails, keep it in the result table with its exception instead of silently dropping it.
- Record daily selected-pair sets and target-weight vectors for differentiation tests. NB66 and NB68 must have identical gated sets but non-identical weight vectors; NB130, NB131, NB142, NB143, NB144, and NB158 must show non-zero pairwise L1 weight distance on at least one eligible decision day unless a documented market state makes the defining mechanism non-binding.
- For NB152, report the count of selections protected from an early discretionary full exit and verify that at least one protection occurred before claiming the rule was tested.
- Re-run the summary construction twice from the same stored states and assert identical tables to catch non-deterministic clustering or unstable ordering.

## Notebook result write-up

After a successful run, update the first cell with:

- `Key new insights and what we learnt from this experiment`.
- `Summary of results` naming the best CAGR, Sharpe, and drawdown methods and the NB158 baseline.
- `Robustness of results` covering concentration, extreme days, path dependence, failed or degenerate methods, and whether the ranking is stable after excluding the strongest day.

The notebook is complete when it executes end to end, includes all 31 methods, reproduces the baseline, and contains the result and robustness analysis in its heading.

## Claude CLI review incorporated

Claude CLI reviewed this plan as a senior quantitative developer before implementation. Its critical findings were overlapping optimiser parameter provenance, collision risk among near-duplicate allocator branches, inherited static-membership survivorship bias, and an underspecified minimum-hold override; the revised plan addresses these with a clean extension holdout, explicit provenance labels, daily weight-vector differentiation tests, a universe limitation audit, and precise forced-exit semantics.

Claude also requested deterministic cached clustering, runtime controls, quantified baseline checks, warm-up and exclusive-boundary checks, sparse-universe diagnostics, defined deployment metrics, and explicit failed-row sorting. These were incorporated before implementation; historical constants and the two necessary approximations are declared in the notebook configuration table.
