# Steady-profit baskets from lower-quartile rolling returns

## Objective and status

Design one bounded experiment, provisionally `31-research-steady-profit-baskets.ipynb` (verify numbering), to maximise credible portfolio Sharpe with CAGR around 20%. The incumbent is a reference, not a return hurdle. Test whether a vault's weaker recent return windows help select repeatably profitable vaults, beyond simply sizing by volatility.

Design only: no basket backtests have run. Implementation must first repair and rerun NB30. This plan does not authorise production changes. Use the existing engine harness and frozen data; no new framework, dependencies or optimiser. Reviewed by Grok 4.6 xhigh with sandbox disabled; actionable findings incorporated below. See [review](grok-46-steady-profit-basket-review-01.md) and [disposition](grok-46-steady-profit-basket-disposition-01.md). Revised design has not received a second external review.

## Research lineage and limits of the discovery

**NB30 repair update, 2026-09-19:** Stage 0's calculation repairs and rerun are now complete; see
[corrected summary](summary-nb30-repaired-01.md). Q25_7_60's residual return IC after G/P/V is
0.005/0.003 at 30/60 days, substantially below the pre-repair evidence quoted in the lineage table.
Q's top group still loses money on average. The basket is therefore a falsification test of allocation
value, not a confirmed return lead. The notebook lists remaining original-plan research diagnostics;
do not confuse completed repairs with completion of every original research deliverable.

Read these sources before implementation. Compare results within experiments, since accounting and date ranges differ.

| Source | Relevant evidence | Consequence |
| --- | --- | --- |
| [NB30](30-research-rolling-typical-profitability.ipynb), [builder](build_nb30_typical_profitability.py), [original plan](rolling-typical-profitability-plan-01.md) | Q25 of nominal 7-day log-growth rates over 60 days had return IC 0.112/0.141 at 30/60 days; median had 0.025/0.035. Q25's 30-day return residual IC after growth, positive-window share and volatility was only 0.036. | Q25 is an exploratory lead, substantially related to existing risk information. The 7/60 setting was selected after seeing results; do not call it preregistered or independent confirmation. |
| NB30 saved summaries | Top-group calculations ignore lower-is-better orientation, mishandle ties and include missing outcomes in weight denominators. | Withdraw the claimed 2.0/3.3 percentage-point top-group advantage pending repair. A successful notebook execution was not a correctness audit. |
| [Rolling-track summary](rolling-profit-risk-track-summary-01.md), NB25–29 | NB27 inverse-volatility sizing did not rescue bad B11 membership: full-period CAGR about -91%. NB28 drawdown haircuts did not achieve the objective. | Volatility sizing is a control, not an assumed improvement. Do not add drawdown penalties to this experiment. |
| [NB20](20-research-stability-screen-portfolios.ipynb) | Example-inspired hard screens improved none of 12 full-period Sharpe comparisons. | Explicitly account for excluded winners; do not tune thresholds to StratWise. |
| [Monthly calibration](monthly-calibration-summary-01.md), NB23/24 | 0/48 configurations qualified; shortlisted scores saturated at one. | Check discrimination, ties, breadth and binding rules. Positive frequency alone is insufficient. |
| [Lower-vol NB09](../hyperliquid-lower-vol/09-backtest-consistency-selection.ipynb) | Profitable-window frequency blend: CAGR 24.3%, Sharpe 1.49 versus 37.9%, 2.16 control. | Rolling consistency is not new; this tests lower-tail magnitude with matched sizing controls. |
| [Lower-vol NB32](../hyperliquid-lower-vol/32-backtest-return-floor-stability-rank.ipynb) | Return floor plus stability ranking: 26/30 configurations negative, best CAGR 8.8%. | Do not repeat a floor/calmness grid; isolate continuous Q weighting against P weighting. |
| [Lower-vol NB07](../hyperliquid-lower-vol/07-backtest-drawdown-sizing.ipynb), [vault-of-vaults NB90](../vault-of-vaults/90-hyperliquid-underwater-geometry.ipynb) | Downside sizing and underwater geometry have already disappointed in portfolios. | Keep drawdown depth descriptive until it demonstrates additional value. |

Novel intervention: continuously tilt allocations towards higher Q, compared with both equal weights and positive-window-frequency P weights, crossed with one volatility-sizing change. Grok found Q>0 and P>=0.75 agree on about 98% of saved opportunity rows; a zero-Q floor largely repeats the old frequency screen and discards Q magnitude. Remove that floor from the main experiment. These figures require confirmation after Stage 0. This experiment tests capital allocation among profitable vaults, not a new hard membership screen or proof that smooth curves identify algorithms.

## Stage 0: repair the evidence before using it

Repair NB30 in its builder and rerun with the observable runner. Preserve old summaries under a clearly superseded name, then record corrected output hashes and a before/after table. Audit the original plan against actual implementation; do not merely fix the three visible defects.

- Orient desirability before assigning membership. For a tied score group, membership per member is `clip((target_mass - strictly_better_count) / tied_count, 0, 1)`. Constant scores assign the same fraction to everyone and therefore produce no separation.
- Form membership before labels. For each outcome, divide weighted sums by labelled membership mass only. The rest uses complementary weights `1-membership`, including the fractional remainder of boundary ties. Report both groups' label coverage. Missing outcomes are unknown, never zero.
- Paired comparisons use identical feature-complete rows, then outcome-specific masks: return evaluation must not require a drawdown label. Compute feature ranks before labels, report evaluated dates, and preserve the opportunity set.
- Reconcile decision timestamps, observed mark timestamps and reused labels. All features and operational inputs must be available strictly before midnight T; a feature built from the whole of date T cannot be paired with a start-of-T label. Verify entry marks actually agree. Daily last marks must retain original observation timestamps and actual elapsed spans.
- Check one-jump containment against the largest positive observed interval, not the largest overlapping holding-period return. Audit forward labels, deduplication and actual-span distributions against the plan. Clearly list any original diagnostics still omitted.
- Meaningful checks: unique/tied/constant ranks; missing group outcomes; lower-is-better scores; future-data mutation invariance; late same-day marks; weekly marks; young history; jump-and-flat versus steady compounding; and no future label used in historical membership.

The new experiment can run even if corrected evidence weakens, but its introduction must use corrected findings and label a negative result honestly.

## Frozen universe, simulator and features

Reuse the corrected NB25/B00 input snapshot and `rolling_track_simulation.py` engine job runner (`run_engine_jobs` calls `run_variant`); this is not the independent A0b simulator. Read [production reproduction differences](production-candidate-vs-research-reproduction-differences.md). Reproduce saved B00 before adding arms, comparing equity, positions, trades and fees on its native two-day cycle. B00 is an accounting reference: six slots, redistribution and native metric convention remain intact for parity. The experimental arms explicitly change to daily decisions, flexible breadth and E1-style no-refill projection, identically across arms. A0b and production archives remain separate references. Attribute Q effects only to matched experimental contrasts, never to basket-minus-B00.

Record exact full-history and hyper-ai window boundaries from the parent manifest, input hashes, source revision, initial capital and warm-up. Also report the already-used later slice as descriptive, not a holdout. Daily decisions, common rebalancing schedule and common valuation dates; independent cash initialisation for each window.

Blacklists off; historical TVL floor $7,500; common young-compatible recent-return gate greater than -16%; same stale-mark tolerance and operational rules as the corrected parent. No long-history admission rule, fixed number of positions or discretionary concentration limit. Preserve actual vault capacity, deposits/redemptions, lockups, cash accounting and minimum trade constraints. Log their effects. Valuation uses causal forward fill as in the corrected simulator; feature measurements do not count carried prices as new observations. Reuse verified fees without duplicate charging; do not invent vault slippage.

Timing contract: T is the actual midnight decision timestamp; use only observations with their original timestamps strictly before T, matching the NB25 `< decision` convention. A legacy NB30 row labelled d with a `d+1` cutoff maps to decision T=d+1, not T=d. Rebuild/align labels and indicators explicitly; execute using the engine's audited price convention and record actual fill timestamps. Diagnostic last-observed-mark labels and engine fills are distinct and must not be presented as identical realised returns. Stage 0 must report that distinction and the entry gap.

At each T, compute median M, lower quartile Q and positive-window fraction P of the same actual-span-normalised rolling log returns used by corrected NB30. Use h=7 days, W=60 days as the exploratory main specification and h=7, W=30 as one fixed neighbouring sensitivity. W=30 is descriptive; report sign agreement and disagreement, without selecting a winner or an arbitrary pass conjunction. No 14-day or threshold grid here.

Use all available history within W, distinct observed endpoint pairs and the existing seven-day boundary tolerance. No minimum event-count gate. Under-h vaults remain in the opportunity ledger with Q unavailable; do not invent Q from available-history growth. Report this access limitation explicitly. Quantiles from one outcome are computable but weak evidence, not mature estimates.

Trailing volatility uses the audited parent's irregular-interval estimator over the same available W. Annualise consistently with 365 days. Fixed annualised volatility floor 10%, chosen as a declared numerical stabiliser, not fitted to results. Zero observed volatility uses the floor. Unavailable volatility uses that same floor for allocation and a visible missing-risk flag, keeping requested membership matched across sizing arms; disclose that this is a provisional assumption and may overweight poorly measured vaults. Report their weights/contribution separately.

## Six-arm allocation decomposition

| Arm | Requested basket | Raw weights |
| --- | --- | --- |
| A: profitable control | Finite M > 0 | 1 |
| B: Q tilt | Exactly A's requested basket | `rank_Q` |
| C: volatility control | Exactly A's requested basket | `1 / max(volatility, 0.10)` |
| D: Q and volatility | Exactly A's requested basket | `rank_Q / max(volatility, 0.10)` |
| E: frequency comparator | Exactly A's requested basket | `rank_P` |
| F: frequency and volatility | Exactly A's requested basket | `rank_P / max(volatility, 0.10)` |

Ranks are contemporaneous ascending average percentile ranks on A's names: higher Q/P gets higher weight. Divide each score's finite ranks by their cross-sectional mean, so a constant score produces a factor of one. Missing Q/P receives factor one with an explicit missing-score flag and remains in every arm. If the whole score is missing, the arm equals its unscored control. No rank exponent or top-k truncation; negative Q can receive capital if M>0. The extra E/F arms are required to isolate magnitude beyond frequency, not an additional search. Log rank dispersion and realised concentration.

Normalise raw weights to the same investable capital. Empty basket means cash; one qualifying vault may receive all deployable capital. Apply the same operational projection to every arm. Do not redistribute rejected capacity after clipping: retain it as cash, following the parent E1 convention. Persist requested weights and realised funded positions separately. Any deviation from parent accounting must be documented before interpretation.

Main contrasts: B-E and D-F test Q versus already-known frequency; B-A and D-C test Q versus no tilt; C-A, D-B and F-E isolate risk sizing. All six arms must have identical requested membership per date. Operational funding differences are reported separately. Distinguish increased capital in steady vaults from a change in the requested name set.

Run all six arms on both W settings and both principal periods: 24 simulations, plus the single parent replay per period. Later slices are derived from the full run with inherited state and labelled accordingly. Do not select winners by hyper-ai-period return.

## Distinguish steady selection from less exposure

For each main contrast, report invested-capital fraction, cash, breadth, turnover, largest weight, effective number of holdings and capacity shortfalls alongside performance. Report requested capital subject to the volatility floor and missing-risk fallback: an arm flattened to equal weights is not evidence of useful sizing. For the primary W=60 contrasts B-E and D-F, if risk improves while average realised exposure differs by more than five percentage points, run at most one diagnostic control per contrast. Replay the comparator's desired relative weights scaled to the candidate's point-in-time post-cap intended risky dollars, retain residual cash and apply the same operational projection. Never infer the schedule from future equity; record the causal capacity calculation and achieved exposure mismatch. This adds at most four runs across two periods. Do not call lower volatility alone selection improvement.

Measure vault quality at decision time and after entry separately. Forward 30/60-day return, negative-return fraction, maximum drawdown and future lower-quartile rolling return are descriptive outcomes, never trading inputs. Show both equal-vault and realised-capital-weighted outcomes, missing-label coverage, and effective unique holdings/intervals. Future lower quartile cannot be the sole success measure.

Create retained/added/removed vault tables with subsequent return and contribution, so excluded winners and avoided losers are visible together. For StratWise (`0x0ff219ac20596b457558341bc410bc7a08a1394c`) and Systemic L/S Grids (`0x07fd993f0fa3a185f7207adccd29f7a87404689d`), verify canonical names, then show opportunity dates, score availability, first selection, requested/realised weights and every rejection reason. They are examples, not threshold targets. Include previously documented lucky winners and losers using the NB19/NB20 records, chosen before inspecting these arms.

## Young vaults and robustness

Report observed-history cohorts <30, 30–89 and >=90 days, separating sparse/daily cadence, one-outcome Q estimates, missing-risk allocation and operational exclusions. Also split capital and contribution by Q=M versus Q<M, and report Q>0 versus P>=0.75 overlap as diagnostics only. Do not exclude Q=M: constant positive growth can genuinely have equal median and lower quartile. Neither event count nor score equality is a new admission barrier. No confidence shrinkage in these arms: that would be a third intervention. If young cohorts receive negligible capital, or dominate because of weak evidence, report that unmet objective. A later short-history sizing experiment needs its own frozen specification.

Report the two windows/settings without picking an optimum. Add contributor concentration, leave-largest-positive-contributor-out descriptive accounting, and fixed non-overlapping forward-outcome dates. Contributions removed from accounting are not a rerun with portfolio reallocation. Dates and labels overlap, all dates have prior research exposure, and the universe is retrospectively assembled. No independent holdout claim. Avoid a bootstrap significance programme unless the underlying coverage supports it.

## Outputs, interpretation and implementation completion

Save manifest, daily decisions/features/reasons, requested and funded weights, trades, cash/fees, equity curves, metrics, exposure, cohorts, reference cases, and capital-increased/decreased winner/loser tables under `_artifacts-steady-profit-baskets/`. Include normalised equity curves, CAGR, volatility, maximum drawdown, turnover and concentration. Experimental Sharpe uses genuine daily marks, 365-day annualisation and zero risk-free rate. B00 parity retains its native two-day Sharpe. Recompute B00 on genuine common daily valuations only if available; otherwise show native metrics separately and never annualise carried two-day samples as independent daily returns.

The desired economic outcome is high Sharpe with CAGR around 20%; report exact CAGR and the full trade-off for every arm, without selecting a winning lookback or fitting an objective function. A basket near 20% in one reused slice alone is not success. Advancement requires evidence that Q improves capital-weighted subsequent vault outcomes and portfolio risk-adjusted performance beyond P controls, not chiefly through cash or one contributor. The neighbouring setting is descriptive; disagreement limits generalisation. Weak precision is inconclusive, not automatic rejection. If no arm supports the objective, record the failure and do not launch another threshold search.

Notebook heading must state what changed, what ran, key findings and robustness limits. Run `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`; check accounting, causality, requested-membership parity and finite equity. Review code and saved results, fix material issues, and rerun affected stages. This plan itself requests no implementation yet.
