# Hyper-ai risk overlay and September drawdown attribution

## Objective and scope

Test a small change to the actual hyper-ai strategy that may reduce drawdowns while preserving reasonable growth around 20% CAGR. The question is whether gentler sizing or a causal response to rising vault volatility improves risk-adjusted performance. September 2026 is a retrospective case study, not a parameter-fitting target or independent holdout.

Design only. Implement one notebook, provisionally `32-research-hyper-ai-risk-overlay.ipynb` (check numbering before creation), with a small helper only where required. Do not modify or deploy production code. The earlier [six-arm basket plan](steady-profit-basket-plan-01.md) remains a separate, unrun proposal; do not bundle its selection changes into this experiment.

Reviewed with Grok CLI `grok-4.6`, xhigh reasoning, sandbox disabled. Actionable findings are incorporated below; see [review](grok-46-hyper-ai-risk-overlay-review-01.md) and [disposition](grok-46-hyper-ai-risk-overlay-disposition-01.md). Grok reviewed the initial draft; this revised text has not had a second external review.

The current source is `/Users/moo/code/strategies/strategy/hyper-ai.py`. At drafting it describes 360-day CAGR / 45-day Sortino selection (60/40 blend), a 14-day return gate above -16%, six slots, 90-day inverse-variance sizing, 98% target deployment, two-day cycles, 33% portfolio-weight and vault-capacity limits. Read and hash the actual source at implementation. Never substitute the old CAGR/Sharpe production description, B00 or A0b for this parent.

## Evidence and why this experiment is bounded

| Source | Finding | Implication |
| --- | --- | --- |
| [Repaired NB30](summary-nb30-repaired-01.md) | Q25_7_60 return IC 0.089/0.123, but only 0.005/0.003 after growth/frequency/volatility controls. Top group still loses money. Conditional drawdown association remains 0.205/0.165. | Keep production selection; Q is initially a diagnostic, not a new gate or weighting multiplier. |
| Same study | Q>0 and P>=0.75 agree on 97.6% of rows. | Do not repeat a hard profitable-window frequency filter. |
| [Rolling-track summary](rolling-profit-risk-track-summary-01.md), NB27 | Inverse-risk sizing did not rescue poor B11 membership. | Risk sizing is not a cure for bad selection. Test it on the actual hyper-ai parent. |
| Same summary, NB28 | Drawdown haircuts did not achieve the goal; cash controls changed interpretation. | No drawdown-trigger grid. Compare any reduction against a uniform exposure control. |
| Current hyper-ai source comments | Inverse variance previously added return with little Sharpe gain and slightly worse drawdown; its advantage depends on concentration settings. | Inverse volatility is a small, already-supported implementation switch. Hold all caps and other parameters fixed. These comments are historical evidence, not a fresh validation run. |
| [Production/research differences](production-candidate-vs-research-reproduction-differences.md) | Archive, current engine replay and independent simulators have different data/accounting. | Reproduce the current engine on common inputs; do not use old headline metrics as a matched baseline. |
| [Allocation decomposition](allocation-decomposition-summary-01.md) | Earlier breadth/cap improvements were confounded and did not establish steady-vault selection. | No simultaneous changes to breadth, concentration, capacity, universe, cadence or eligibility. This is experimental control, not a new concentration preference. |

Novel question: does within-vault volatility deterioration provide actionable warning for the incumbent's held names? NB30's cross-sectional risk persistence does not itself establish that temporal signal. The overlay below is a hypothesis, not a fitted forecast or proven September fix.

## Stage 1: September coverage, parent reproduction and attribution

1. Obtain the actual deployed source revision, starting holdings/cost bases, fills, fees and equity ledger where locally available. Separately preserve/hash the current local source. If the September deployed revision differs, reproduce the deployed parent for the September question; a current-source replay is a separately labelled counterfactual. If live state/revision is unavailable, proceed with an engine backtest but explicitly withhold claims about actual production loss prevention.
2. NB30's decisions end on 9 September and its underlying snapshot is not full-month evidence. Use the repository's existing data loaders to obtain the required history through the latest fully completed UTC day available at implementation. Record the exact cutoff, collection date and completeness. Do not forward-fill beyond the dataset endpoint to manufacture September coverage. If later data is unavailable, run the supported interval and label the September conclusion incomplete; continue earlier-period comparisons.
3. Freeze a single snapshot for all arms. Read repository vault-selection instructions before changing universe lists. Match the parent universe, quarantine/blacklist treatment, deposit availability and operational checks exactly; do not switch blacklists off for this experiment. Record historical-versus-current universe limitations. No social/follower factors or additional history gate.
4. Run the unmodified strategy through the existing trade-executor engine with the same capital, pre-start indicator history and fee/execution configuration as its matched reproduction. Retain current performance-fee cost-basis accounting, redemption settlement, deposit restrictions, cash-budget handling and minimum-trade rules. No fee double counting or invented slippage.
5. Separate source parity from a fresh-data backtest: verify the notebook parent matches a direct run of the same frozen source/data/configuration in equity, holdings, transactions and fees. An older archive with different inputs need not have identical metrics. Never tune the parent to match an archive headline.
6. Use two independently initialised windows: the parent's documented January–July comparison window, and a full-history run beginning on the earliest supported common date with appropriate pre-start data and continuing to the frozen cutoff. The current source's January run boundaries are 1 January–10 July exclusive; the documented metric comparison ends on 8 July. Preserve that distinction and verify exact boundaries at implementation. Export actual start/end timestamps and metric slices. These windows overlap and are not independent samples. September is month-to-date through the frozen cutoff, sliced from the full run with inherited holdings, not a fresh September cash start or a claim of complete calendar-month coverage.

Produce a daily/cycle September loss-attribution table: vault/address, pre-loss held value and weight, price-return contribution, fees/costs, trades, and accounting residual. Contribution totals must reconcile to equity change; separate marked changes from realised exits so a fee or settlement effect is not mistaken for a price signal. Include winners as well as losers.

For each held name record sigma30, sigma90, their ratio, Q25_7_60, current drawdown, return-gate distance and actual availability timestamps at each preceding production rebalance. Define September metrics as month-to-date return from the last pre-September valuation, within-month max drawdown, and decline from the inherited historical high. Do not annualise one month's return into evidence for 20% CAGR.

Classify loss episodes descriptively: warning before losses, warning only after the first loss, or no warning. Show hypothetical target reduction and earliest feasible execution time alongside the losses. A two-day policy cannot react at a timestamp between its decisions, and an asynchronous redemption cannot protect capital already exposed while settling.

On H0's saved per-cycle targets b, also calculate the hypothetical H2 and uniform H2U cuts using the same H0 state and causal m. Relate those cuts to subsequent losses on H0's actual path. This is a shared-state target diagnostic with no new simulated arm, fee model or claim of executable counterfactual P&L. It distinguishes immediate allocation differences from the accumulated path divergence of full-run H2/H2U. Record time since the last observation alongside the ratio as context, not an additional admission gate.

## Stage 2: fixed variants

Keep the source's selection, parameters, two-day rebalance clock and ordinary operational rules. No rank/age/filter/hold-time changes.

| Arm | Intervention | Intended contrast |
| --- | --- | --- |
| H0 | Unmodified parent | Matched control |
| H1 | `weighting_method = inverse_vol`, keeping the 90-day estimate | Effect of gentler sizing versus inverse variance |
| H2 | Parent sizing plus the volatility-deterioration haircut below | Effect of a causal within-vault risk response |
| H2U | Uniform exposure control for H2 | Separate vault-specific reductions from simply holding more cash |

Four arms over the two windows: eight simulations. No H1+H2 combination, threshold search or Q-trading arm in this batch. All four September paths are already contained in the full-history runs.

For H2, compute `m_i(T) = min(1, sigma90_i(T) / sigma30_i(T))`. Define each sigma as the parent's unannualised daily sample standard deviation: `close.pct_change().rolling(L, min_periods=L).std()` with the existing `VOL_FLOOR = 1e-4` applied to finite values. Change only L to 30/90; preserve the source's return-series handling and forward-fill semantics. No NB30 irregular-interval estimator substitution. Equivalently m is `min(1, inverse_vol_30 / inverse_vol_90)` after the floor. Save raw and floored estimates and the fraction of targets affected by the floor.

All inputs strictly precede decision T, using the engine's previous-bar accessor. Reuse the estimator's existing coverage requirements; add no new admission requirement. Missing/non-finite estimates imply m=1 with an unmeasurable flag. Finite zero or near-zero raw volatility is floored, not treated as missing; both windows on the floor yield m=1. Negative raw volatility is a calculation error. No extra smoothing, hysteresis, exponent, fitted floor or increased allocation when recent volatility falls. A previously volatile vault with sigma30 approximately sigma90 will not be cut: this is a deterioration response, not an absolute-volatility ceiling.

Let b_i be the parent's target dollars after its usual weighting, concentration, capacity and redistribution stage, calculated using the arm's current state. Immediately after `alpha_model.normalise_weights`, set each signal's `position_target` to `b_i*m_i` (H2) or `b_i*u` (H2U). Then run the parent's `update_old_weights`, `calculate_target_positions` and trade generation in their normal order. Do not change targets after `calculate_target_positions`: that would leave stale dollar adjustments. Apply the haircut once, retain released cash and never call normalisation again. Normal minimum-trade, execution and settlement handling still applies; log requested reductions, realised exposure and reasons an intended trim did not execute. Include the 0.5%-of-initial-cash sell threshold and any full exit caused by the 0.5% minimum position-weight rule; neither is evidence of changed selection logic.

On any fixed input state H0/H1/H2 use the same selection logic. Over a full run they may have different eligible-held names because holdings, closed deposits, cash, cost bases and lockups evolve differently. Do not assert realised membership equality. Report requested and funded membership overlap per cycle and identify when operational feedback contributes to differences.

For H2U, calculate its own unmodified parent targets b and the same causal m values on its own state. Set `u = sum(b_i*m_i)/sum(b_i)` (u=1 when total b=0), then target `u*b_i`. Thus it matches H2's intended total on identical states while preserving the parent's relative allocation. The paths may diverge in state and realised exposure; export the mismatch. This is a causal uniform-allocation control, not a promise of exact realised cash matching. Do not derive u from future H2 equity or September outcomes.

## Q and warning diagnostics

Q remains informational. Use the corrected NB30 timestamp/actual-span definition, with original observation timestamps; never reuse a date-d feature as a start-of-d signal. Report whether Q deterioration precedes the parent's losses when sigma30/sigma90 does not. Compare the distribution among both retained winners and losers. If it offers no additional early warning, do not add it to H2 later in the same notebook.

For StratWise and Systemic L/S Grids, report whether the actual parent admits/holds them, then their unmodified and treatment weights. Their absence is a parent-policy observation, not permission to alter selection. No assumption that these two examples establish general safety.

## Evaluation and decision

Export equity curves, cumulative return, full-window CAGR, Sharpe, volatility, maximum drawdown, average risky exposure, turnover, fees, effective holdings and largest loss contributors. Use the same actual observation clock for all compared Sharpe estimates: retain the parent's two-day convention for parity; daily supplemental metrics require a genuine common daily valuation series, not carried two-day equity treated as independent daily returns. State the zero risk-free convention.

Primary contrasts are H1-H0 and H2-H2U, with H2-H0 for the total intervention. Show net fees and missed subsequent recoveries. Report whether reduced September losses came from smaller initial weights, pre-loss risk reductions, post-loss exits or operational effects. Include fixed earlier calendar-month outcomes from the full path so September cannot be the only flattering slice. No optimisation based on the largest September loser.

H1 is a gentler low-volatility tilt, not guaranteed risk reduction: compared with inverse variance it can allocate more to volatile selected names. H2-H2U is a whole-policy comparison after their states diverge, not a pure September same-holdings attribution. Use the H0 shared-state diagnostic to interpret that distinction. Cross-sectional NB30 evidence does not prove sigma30/sigma90 offers temporal lead time, even if a retrospective September chart looks attractive.

The goal remains higher credible Sharpe with reasonable CAGR around 20%; show exact trade-offs for every arm rather than select a winner with a tuned score. Reduced losses in one month are insufficient to recommend deployment. H2 must demonstrate useful lead time and value beyond H2U to support a vault-specific risk claim. H1 can be a simpler return/risk trade-off even without timing skill. A poor result should stop escalation, not trigger additional variants. Lack of data is inconclusive; a sudden first loss with no earlier warning cannot be retrospectively labelled preventable.

## Deliverables and checks

Save notebook, run/source/data manifests, parent-parity report, September attribution, pre-loss indicator timeline, all target/execution ledgers, equity/metrics, uniform-control mismatch, reference-vault cases and a concise summary under `_artifacts-hyper-ai-risk-overlay/`.

Checks: H2 equals H0 when every multiplier is one on the same state; multiplier bounds [0,1]; equal multipliers reproduce H2U targets on a shared state; halved multiplier halves the relevant pre-trade target without refilling other names; missing/zero volatility takes the declared fallback; post-T observation changes leave pre-T decisions unchanged; weights/cash and attribution reconcile; no duplicate fees; no use of settlement proceeds before available. These are code checks, not economic validation.

Execute with `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`. Inspect code and saved results, fix material defects and rerun affected stages before summarising. This plan requests no implementation or live strategy change yet.

## Implementation status

Implemented as a research-only replay in `32-research-hyper-ai-risk-overlay.ipynb`, built by `build_hyper_ai_risk_overlay.py`. The notebook loads the current production source directly at runtime, records its source hash, applies the overlay in the specified pipeline location, and uses the frozen input snapshot. It was executed successfully with `jupyter-execute-agent`; the saved notebook has no cell errors.

Results and ledgers are in `_artifacts-hyper-ai-risk-overlay/`, including the parent-parity report, target and trade ledgers, September attribution, pre-loss timeline, reference-vault cases, curves and metrics, and `summary.md`. The production `hyper-ai.py` file was not modified and no live strategy change was made.
