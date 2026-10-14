# Experiment 14 — more profitable allocation

Status: **implemented and executed** in [NB14](14-backtest-profitable-allocation.ipynb). Ten primary engine results and four quote-freshness sensitivities are complete. Eight legacy metric parity checks pass. Confirmed later-observation fills triggered shared as-of observation pricing; indicators and risk still use T−1. All primary fills match recorded as-of NAV, both primary/sensitivity holdings remain at most six, and PnL reconciles within $1. See [findings](14-profitable-allocation-findings.md). The plan was reviewed twice with confirmed `claude-fable-5-1`; execution findings are separate from that plan review.

## Goal

Make the strategy more profitable by improving position sizing and the deployment of available capital. Use full trading-engine profit and CAGR as the primary outcomes; show the accompanying drawdown and Sharpe so higher exposure is not mistaken for a free improvement. Seek a simple change we can explain and maintain.

Keep this small: five active allocation combinations, the existing two backtesting periods, and one short report. Reuse the NB12/NB13 engine and attribution code. Do not build another feature study, snapshot experiment, optimiser, covariance model or general data-audit framework.

## Evidence and hypotheses

The source C03 four-input strategy returned 51.77% CAGR / 2.30 Sharpe over the fresh 2026 replay. Over full history it returned 22.09% / 1.62 / -8.08% maximum drawdown. The same ranking with regularised90 and simultaneous cap allocation (B02) returned 27.07% / 1.48 / -10.24%; gap-aware sizing (C07) returned 27.44% / 1.50 / -10.24%.

The larger long-period gain combines changes in risk estimation and allocation. The isolated gap-estimator gain over regularised90 is only 0.37 percentage points CAGR. Much of the allocation-family gain is in 2024; C03 performed better in 2025 and carried-account 2026. Mean full-history cash was 43.8% for C03 versus 38.7% for C07, whereas fresh-2026 cash is around 10% for both families. Early empty/limited-universe periods inflate the full-history cash figure. Cash and return differences alone do not identify a causal benefit from deployment; average cash does not provide a numerical bound on the benefit of reallocating at particular dates.

Hypotheses:

1. Redistributing capped allocations among the existing selected vaults can increase net profit without needing a different selector.
2. Regularisation or gap-aware risk estimation can improve capital placement, particularly for young and sparsely observed vaults; it can also dilute profitable source positions.
3. Downside-based sizing may keep more capital in vaults after profitable upward moves, increasing net profit. It may also overallocate to vaults with infrequent losses: this is an untested economic hypothesis, not evidence that upside jumps are safe. Failure to find a better combination is an acceptable result.

References: [NB12 findings](12-allocation-followup-findings.md), [NB13 findings](13-long-candidates-findings.md).

## Fixed strategy and data

- Use C03's exact saved ranking: 0.48 CAGR360 + 0.32 Sortino45 + 0.10 CAGR180 + 0.10 Sortino30 after the existing normalisations/clips. CAGR normalisation is 100%; Sortino is 3. This is four inputs from two metric families.
- Six maximum positions; existing entry/exit ranks, missing-score handling (`missing=True`), guard rules, hysteresis, minimum trade thresholds and two-day decision schedule.
- Keep existing 98% investment target, 33% concentration and pool constraints with the source engine's exact budget units. Do not change capacity metadata or force full investment.
- Start each independent replay with $150,000 and zero positions. Preserve the original source fee settings for comparable results; identify the estimated redemption allowance separately from actual vault fees. No invented vault slippage or double charging of fees internalised in NAV.
- Keep the repaired archive, vault universe and source versions pinned to NB13. Record differences if the current environment has moved; do not silently compare different inputs.
- Retain all pre-start history for indicators, including 2025 and earlier. No pre-inception filling.
- The source variance lookback is 90 days; 45 days is a Sortino input.

## Small comparison matrix

| ID | Risk estimate | Allocator | Question |
| --- | --- | --- | --- |
| A | Exact source 90-day inverse variance | Original sequential | Can we reproduce C03? |
| B | Exact source 90-day inverse variance | Simultaneous cap redistribution | Does the allocator alone increase profit? |
| C | Regularised 90-day inverse variance | Original sequential | Does regularisation alone increase profit? |
| D | Regularised 90-day inverse variance | Simultaneous cap redistribution | Reproduce B02 and measure interaction |
| G | Regularised 90-day downside second moment | Original sequential | Can we avoid reducing weight merely because of profitable upside moves? |

C and D use existing kappa=30 actual updates and the existing peer prior and fallback semantics. G uses the same support and regularisation structure with the downside risk functional specified below. Do not tune the window, prior strength, score weights or position count in this experiment. These values are inherited reference choices, not proven optima. Source versus regularised comparisons include their existing flooring, support and fallback differences; label this as the estimator package.

Implementation must separate the risk-weight calculation from cap allocation. B must receive the exact raw weights used by A; C and G must pass their alternative raw weights through the original allocator. Preserve exit signals, source decision bookkeeping and budget units. Compare requested and accepted weights on a saved common decision as a small correctness check; this does not require a separate snapshot study. Full engine holdings may diverge because of capital and replacement feedback.

### One new profit hypothesis: downside-based sizing

G is Claude's proposed economic addition, revised to share C's sparse-data and young-vault support. Its fair comparison is **G versus C**; G versus A is the practical strategy comparison. This replaces the redundant gap-estimator/source-allocator arm. Keep C07/F as a separately labelled saved reference when its inputs and timing match; do not add a fresh gap-estimator grid.

Implementation:

1. Use exactly C's causal 90-calendar-day simple-return path, feature endpoint, eligible peer universe and empirical availability rule. Current `empirical_window` requires at least two elapsed returns and one actual update. Forward-filled days stay in the elapsed-day denominator; they do not increase actual update count. Do not switch to log returns or drop zero returns in only G.
2. For the n finite daily returns, calculate `d_i = sum(min(r_t, 0)**2) / n`. The target is zero return: squared losses per elapsed day. This is an uncentred downside second moment, not variance conditional on losses and not divided by the number of negative days.
3. Form a leave-one-out peer prior using the same complete-window-first/partial-window-fallback positive-median rule as C, substituting `d` for empirical variance. If no positive downside peer prior exists, use C's positive full-variance peer prior and record that fallback. Observed zero downside is valid empirical data; no observed losses does not mean no economic risk. The positive downside peer pool is conditional on having losses; report this selection effect rather than treating it as an unbiased all-peer prior. The full-variance fallback is used without rescaling: both quantities have squared-return units but different centring/normalisation and potentially different magnitudes. Do not assume a universal factor-of-two relationship or that fallback is rare; record count and invested weight.
4. Use `c_i = m_i / (m_i + 30)` with actual update count m, and `v_down_i = c_i*d_i + (1-c_i)*prior_down_i`. Missing empirical data receives zero empirical weight. Call the same `forecast` helper as C: when no positive prior exists it retains a finite positive empirical estimate, otherwise returns missing. If the final risk estimate remains unusable, use C's existing basket-level equal fallback; do not silently remove a young vault. Reuse C's existing numerical handling, rather than introducing a new downside floor or allocating a cap directly to zero-risk names. With this daily boolean observation mask m is at most 90; when a positive prior exists, its weight is at least 25%, so a non-negative empirical downside estimate cannot drive the forecast below one quarter of that prior. This bound does not apply to empirical-only fallback without a prior.
5. Set raw weights proportional to `1/v_down_i` and apply the original sequential allocator, identical to C. Keep all caps, gates and turnover rules unchanged.

G versus C changes both the individual and peer risk functional, deliberately. Denominator, return units, update counting, regularisation strength and allocator are matched. Downside second moment can exceed centred variance; do not rely on a contrary inequality. Use distinct statuses `zero_downside_nonflat` and `observed_flat`, determined using C's total variance, so an increasing loss-free vault is not labelled flat. Preserve partial/full support as a separate field. Report zero-downside, full-variance-prior fallback and peer-only cases plus their invested weight in the small diagnostics table. Repeated flat marks must not masquerade as a large independent sample.

## Price timing: a focused correctness check

Before new B/C/G replays, perform one reference-data timing check using saved A/D and NB13 audit inputs; choose and record the common pricing convention first to avoid duplicate work. Trace actual NAV observations through indicators, execution prices and equity marking for the November 2024 update identified in NB13. Also count any later-than-decision marks used for fills across the existing reference replays. Retain that check on the new runs too, because their trades can differ. A daily midnight label alone is not proof of a lookahead bug.

Distinguish NAV effective time, observation/availability time and archive write time. Never use a later archive rewrite as automatic evidence that the historical observation was unavailable. Do not reconstruct historical permission clocks or discard archived operational state as part of this experiment.

If the audit confirms a later observation is used before it was available, implement the smallest shared timing correction and apply it to every arm. Keep legacy reproduction results separate from corrected results; the corrected A is the reference for the corrected candidates. If only valuation labels are misleading, fix/report the labels and assess the effect on risk statistics without assuming the trading profit is invalid.

Use forward filling only for causal NAV marking/features and retain observation age. A carried price is not evidence that a new deposit could execute at that old NAV. If available history cannot establish the execution price at a decision, declare the modelling convention and show a conservative timing sensitivity for A and the leading challenger, with identical handling. Do not invent historical prices or use future availability to choose vaults.

Keep this scoped to economically relevant timing; do not delay the allocation comparison to build a comprehensive timestamp platform. Unresolved execution timing prevents a deployment verdict, not an honestly labelled research comparison.

## Sparse data and young vaults

- Preserve causal NAV filling after the first positive observation, with actual observations tracked separately.
- Filled calendar days must not become extra independent observations for regularisation.
- Partial histories remain eligible under existing selection rules; risk estimation uses the existing partial-history/peer fallback, with no newly invented age filter.
- Distinguish missing variance from observed zero variance and report fallback frequency in one small table.
- Do not forward-fill permission, leader-share or capacity fields using the NAV rule. Preserve repaired-reader semantics.

## Calendar and run order

1. Establish A and D parity against saved NB13 results when hashes match; cached results are reusable only for identical code, parameters, inputs and timing, with saved states sufficient for all displayed diagnostics. Existing NB13 CAGR and Sharpe tolerance is absolute error below 2e-6, and position-PnL/equity reconciliation is within $1. F/C07 is optional saved context, never a mismatched-timing comparator.
2. Run all five active arms over **2026-01-01 to 2026-10-05 exclusive** (through 4 October). The first run covers the entire period, with full warmup.
3. Run all five active arms over **2023-03-01 to 2026-10-08 exclusive** (through 7 October, final archive day partial). Five arms are few enough to avoid selecting the long-period sample from short-period winners.
4. Produce calendar-year and quarterly attribution from these runs. Fresh-start 2026 and carried-account 2026 are different experiments; keep them labelled. Their inherited NB13 endpoints differ as well: fresh 2026 ends 4 October, carried 2026 ends 7 October. Annotate the latter column with its endpoint and do not subtract the two as if dates and initial holdings matched.

This is ten required arm/period results. Four A/D results may be reused exactly, leaving six fresh B/C/G replays when valid caches and ledgers exist; otherwise rerun the relevant controls. Optional saved F results are context, not extra active combinations. Timing correction/sensitivity runs are additional only if needed and must be listed. A correction invalidates affected cached references. Do not promise a fixed extra-run count before tracing its scope: a common pricing change may affect both periods, even if the motivating event is in 2024. The historical periods have already informed strategy development; they are not independent holdouts.

## Economic evaluation

Primary: final equity, net dollar profit and CAGR. Secondary: Sharpe, maximum drawdown, turnover/costs and cash. Compare B-A (allocator), C-A (regularisation), G-C (downside sizing), G-A (net practical gain), and the dollar-PnL interaction D-B-C+A. Differences are within the same period and timing convention. Rank profit within each period, not by averaging incompatible annualised and cumulative measures.

For each profitable change, answer:

1. How many extra dollars did it earn after the modelled costs?
2. Did it invest more cash, change which vaults received capital, or both?
3. Which quarters and vaults produced the difference?
4. What extra drawdown accompanied it, and did it lose the original candidate's 2025/2026 advantage?

Use saved engine ledgers for requested/accepted weights, cash, turnover and vault profit. The same redemption rate can change relative performance because turnover differs; report modelled fees by arm. A simple invested-weight comparison is sufficient initially; no new volatility-targeting or matched-exposure strategy is required. Contribution decompositions are descriptive, not rebalanced counterfactuals.

Present the long-period profit leader and fresh-2026 profit leader side by side; if they differ, make the disagreement explicit. Long-period final equity supplies a profit-first ordering, while calendar-year/quarter contributions explain whether it is relevant to current conditions. Earlier years and 2026 have both been searched: do not invent an independent holdout or an arbitrary weighting that favours one period.

Do not impose an arbitrary new drawdown cutoff or weighted CAGR/Sharpe objective. Show the profit/drawdown trade-off. A candidate that increases profit and improves or preserves drawdown is especially attractive; a higher-profit/higher-drawdown candidate remains a separate risk choice. If changes only help one exceptional quarter, classify them as fragile. Use the existing quarterly and vault contribution outputs to expose concentration; no synthetic update-deletion table is needed.

## Compact notebook presentation

Proposed notebook: `14-backtest-profitable-allocation.ipynb`. Its opening markdown reproduces the goal, hypothesis, fixed rules, five-arm matrix, date boundaries and final conclusion.

Default tables/charts use the short 2026 period. Every element has its own subheading, a one- or two-sentence explanation, and a title/caption naming the dates. Every image is separate; no collages.

1. Colourised side-by-side key metrics table, ranked by net profit, for 2026.
2. One 2026 equity chart: A, D, G and any other best-profit arm, deduplicated.
3. Dollar-profit-difference bars for the paired allocator and estimator comparisons in 2026.
4. One quarterly incremental net-profit heatmap versus A for 2026, to show whether gains repeat.
5. One small cash/concentration/cost table for 2026; include fallback counts here.
6. Clearly labelled long-period metrics table and separate long-period equity chart.
7. Calendar-year incremental dollar-PnL heatmap versus A; explain different starting equity for carried years.
8. Small top positive/negative vault contribution table for the leading challenger versus A.
9. A short timing verdict and final recommendation: retain A, choose a challenger for forward observation, or acknowledge an explicit profit/risk trade-off.

Detailed ledgers belong in ignored artefacts. Avoid progress output and large raw tables in saved cells. Visually inspect every saved figure using the repository static notebook preview workflow.

## Implementation and completion

Reuse `long_candidate_backtest.py`, `allocation_followup_engine.py`, `long_candidate_audit.py` and the existing report helpers. Add a small NB14 driver and allocator adapter rather than rewriting the engine. Keep reusable source and written conclusions outside artefact directories; generated states, logs and ledgers stay under the already ignored `_artifacts-restored-2026-10-07/14/` tree.

Execute with the repository's observable `jupyter-execute-agent` runner and terminal progress. Verify reference parity, no future indicator observations, allocations obey source constraints, and position profit/equity reconciliation. Update `summary.md` with the hypothesis, economic result, limitations and next action after execution.

Completion means all five active arms evaluated over both periods, readable saved outputs, timing assumptions made explicit and a dollar-based recommendation. Do not automatically expand the grid or deploy a strategy. If redistribution improves A and downside sizing improves C, a subsequent single G-plus-redistribution comparison is a logical next hypothesis; it is not part of this five-arm run.

## Claude contribution and review

The first successful CLI review used `claude-fable-5-1`, with the returned model metadata confirming the requested model and no fallback. Claude reviewed the supplied draft and NB12/NB13 findings, with tools disabled; it did not independently inspect source code.

Accepted: reduce the active matrix to A/B/C/D/G, treat C07 as saved context, add one downside-sizing profit hypothesis, clarify fresh versus reusable results, expose the early-history cash effect and keep profit as the main ordering. G's formula was corrected to match C's daily-return/support conventions and retain regularisation for young/zero-loss histories.

Deferred ideas: earning yield on idle cash would need a separately researched executable instrument and availability history; asymmetric trimming of winners changes trade generation and deserves a separate experiment if allocation gains are insufficient. Neither is automatically run here.

Rejected/corrected: later-than-label receipts alone do not prove an execution leak; moving fills to yesterday's NAV is not an execution correction; identical fee rates can change strategy rankings; downside second moment is not always below centred variance; mean cash does not bound the profitability of redistribution; a simple exposure-times-return calculation is not an exact compounded attribution; no new historical period weights are justified by in-sample selection.

The focused second review returned **ready to execute with three small clarifications**. Incorporated: zero-downside versus flat labels, explicit unscaled full-variance-prior fallback, unequal inherited period endpoints, the positive-prior bound, reference timing preflight and removal of the update-deletion diagnostic. Its approximate variance/downside scale ratio and fixed extra replay count are not assumed; both depend on data and timing scope. These final clarifications were checked locally and were not submitted for a third review.

See the accompanying [review record](14-profitable-allocation-review.md) for the final review disposition. Raw prompts, responses and plan snapshots are retained under ignored `_artifacts-restored-2026-10-07/14-plan-review/`.


## Execution notes

The timing preflight confirmed 24 later-observation fills in the legacy A/D references, all on historical CryptoZer0_ trades. The primary convention is now as-of observation time. Existing partial-trim fee-adjusted mid fields are normalised for the timing audit; the source fee model itself is retained and its limitation is recorded in the findings.

The conservative freshness sensitivity defers both deposits and redemptions after a two-day observation gap. Pinned positions reserve their portfolio slots so deferred exits cannot increase holdings beyond six. This slot reservation applies only to the sensitivity. The new downside checks cover zero-loss non-flat histories, partial histories, positive-prior contribution and total-variance-prior fallback.

Saved notebook outputs contain seven separate inspected charts and no warnings or errors. Presentation was refreshed from the ten verified saved engine states with zero new engine calls; source engine calculations were not changed. The long-period leader G earns more with greater primary drawdown, while A remains the fresh-2026 profit leader. No production change follows automatically.
