# Stable-profit forecasting aligned with hyper-ai

Date: 2026-09-14. Status: implemented, corrected and rerun after independent Opus 5 review.

## Objective and evidence

Improve profitable stability and portfolio Sharpe, including young vaults, while avoiding directional and exceptional-event dependence. The 20–30% CAGR objective is an aspiration, not a demonstrated opportunity. Preserve the daily/sparse data contract of [rewrite-plan-01.md](rewrite-plan-01.md).

Read [summary-02.md](summary-02.md), [final allocation verification](claude-review-opus5-final-01.md), notebooks 01–04 and their artefacts, and current `/Users/moo/code/strategies/strategy/hyper-ai.py`. Read the [adjacent stability plan](../hyperliquid-lower-vol/28-stable-selection-plan.md), NB25/26 findings, NB23 Sortino-swap review and [NB28 review](../hyperliquid-lower-vol/28-research-stability-signal-screen-codex-review.md). Consult `/Users/moo/code/freqtrade-strategies/.claude/docs/feature-engineering.md` on residualisation, concentration, matched controls and harness validation.

| Established finding | Consequence |
| --- | --- |
| Short risk predicts forward variance: IC 0.771 over 219 dates | Start with simple risk controls |
| Growth Ridge IC 0.122 at 30 days; low-downside control stronger point estimates at every horizon | Test loser avoidance versus winner selection |
| Optional catalogue weaker than short core | Avoid another wide feature search |
| Young-cohort IC exists but profitability is unproven | Keep forecasts/access research; report losses |
| Corrected fixed candidate CAGR -7.9%, vol 25.5%, Sharpe -0.20, DD -27.8%; incumbent replay 2.9%, 20.1%, 0.24, -15.4% | No stability improvement yet |
| Corrected adaptive candidate lost 12.4%; fixed candidate also lost capital | Test concentration and episodic performance |
| Greedy cap redistribution can amplify a risky tail name | Isolate selection from sizing |
| Consistency filters can select non-earners | Preserve incumbent return ranking initially |
| NB28 concentration inference has count confounds and bootstrap defects | Do not interpret its negative screen as proof of no predictability |

Confirmed directly from saved predictions: the 30-day daily-downside model produces forecasts only from **1 May to 12 September 2026, 135 dates**. It cannot be the main year-long ranking model.

The existing year has already been examined repeatedly. New walk-forward results on it are retrospective development evidence, not untouched validation. Research-replay incumbent numbers are not production performance.

## Preserve clocks and sparse admission

Reuse frozen NAV/BTC data, 365 headline daily dates and earlier training history. Hash source, production file, helper, configuration and artefacts. Keep notebooks 01–04 and `_artifacts-rewrite` as the baseline inputs; write stable-profit outputs to `_artifacts-stable-profit`.

The 15 September 2026 rerun regenerated notebooks 02–04 and
`_artifacts-rewrite` after the sparse interval-panel correction. Its corrected
allocation figures supersede the earlier candidate figures quoted in the first
draft of this plan; the incumbent replay remains the stable-profit A0 anchor.

Global research admission remains two fresh valid NAV observations at least 24 hours apart, NAV/TVL age at most 14 days and TVL at least $7,500. No global age, long-window, density or written-at barrier. Metadata age and available-history length remain distinct.

Features use observations strictly before the decision boundary. Measured unchanged NAVs count; provider-carried rows do not. Weekly changes remain multi-day intervals. Missing future labels never delete current predictions. Zero measured downside is zero; insufficient evidence is missing.

Retain existing next-observed entry/exit labels, seven-day endpoint-delay limits, actual duration, raw and nominal-H-scaled growth, and outcome IDs. Monthly expanding fits use matured exits only, training-only imputation/scaling, and duplicate-outcome weights summing to one within training samples.

Retain raw fresh observations for feature provenance, but mark the policy book from each vault's latest causally available NAV on every calendar day. Fresh-but-ineligible holdings get zero target at rebalance; no holding disappears from equity or freezes at a pre-collapse NAV. Report the capital held at carried marks separately.

## Phase 0: diagnose the selectable pool

Use saved artefacts first. Save actual date/vault membership rather than reconstructing it from final holdings.

- Reproduce incumbent selectable pool and top-six/top-twelve neighbourhood. Report composite saturation, tie boundaries and zero-score membership.
- By downside quintile, report raw forward growth distributions, loss probability and >10% holding-period loss. Repeat within the incumbent neighbourhood. Recompute IC after excluding the highest-risk quintile: does most growth information identify losers?
- Double-sort recent risk and absolute BTC beta on common rows. Report loss/growth by cell and month, controlling for TVL and sampling. Beta correlated with volatility is not automatically independent information.
- Repeat by available-history cohorts <7, 7–13, 14–29, 30–89, 90–179, 180–359, 360+ and daily/weekly/irregular sampling, with row/date/vault/outcome counts.
- Separate zero-downside low earners. Audit label attrition after cessation, reporting last observed losses and missing outcomes without filling them as safe.
- Treat Opus's additional tail-loss, beta and Sortino calculations as hypotheses to reproduce. They are exploratory, not established out-of-sample findings.

## Phase 1: preserve the return engine and test three risk vetoes

Refactor the replay minimally into explicit pool, ranking/filter and sizing policies, reusing one accounting path. Save the pre-refactor baseline. A generic no-op policy must reproduce baseline membership, weights, trades and equity within numerical tolerance. The existing candidate mode is not a valid no-op path because it changes gate and sizing.

Freeze production settings: 360-day CAGR/45-day Sortino, 60/40 composite, 14-day gate > -16%, six forward-filled daily slots, 90-day inverse-variance sizing, 98% deployment, 33% concentration/TVL limits and greedy redistribution. Keep identical tie order. Missing composite is score zero; missing gate fails. There is no explicit 360-day eligibility gate, but positive ranking is effectively dominated by long histories.

Use the same two-day forward-filled daily-mark execution convention across arms. Record actual-versus-carried marks and discrepancies from the current engine: no-candidate handling, quarantine/blacklist, deposit availability, minimum hold, trade thresholds, fee valuation and asynchronous settlement. Missing historical operational restrictions must be disclosed and treated consistently. Score/sizing parity is not full engine parity.

| Arm | Pool change | Ranking/sizing |
| --- | --- | --- |
| A0 | None | Production |
| A1 simple downside veto | Exclude highest 20% of finite observed 30-day interval downside estimates | Production on survivors |
| A2 learned loss veto | Exclude highest 20% of finite predicted severe-loss probabilities | Production on survivors |
| A3 directional veto | Exclude highest 20% of finite absolute 30-day BTC beta estimates | Production on survivors |

Exclude floor(0.2 × finite count), with deterministic address ties. Missing scores remain eligible and are logged. Do not backfill vetoed names; fewer names/cash are allowed. Until a pooled model is fitted its veto is inactive, explicitly flagged; inactive dates are not evidence of forecast success.

Only these three candidates at H=30 are shortlist-eligible. No threshold optimisation. Compare vetoes on identical finite-score rows, and report finite count, missing count, realised exclusion share, fraction of incumbent picks vetoed and remaining pool.

For A2 incremental diagnostics, match realised exclusion counts with simple volatility/downside controls and 20 fixed outcome-free permutation draws. Preserve missingness and monthly identity persistence; quantify any permutation-induced sample loss. Null controls are not winner candidates. Validate that null baskets differ and never treat non-finite null statistics as non-exceedances.

## Model and targets

Use the existing short core including TVL, counts and missing flags. Primary model: regularised logistic regression with fixed C=1 and no class balancing initially, so prevalence is not deliberately changed. Train with distinct-outcome weights. Require the existing 60 matured training-date minimum and both label classes; otherwise predictions are unavailable and veto inactive. This is pooled training warm-up, never per-vault age admission.

| Target | Definition | Use |
| --- | --- | --- |
| Severe holding-period loss | `forward_log_growth_raw_H < log(0.90)` | Primary A2 classifier, compatible with sparse endpoints |
| Forward growth | Existing raw and nominal-H-scaled log growth | Retain Ridge for return-retention/calibration diagnostics |
| Negative return | Raw growth < 0 | Diagnostic |
| Daily downside semivariance | Existing annualised negative squared consecutive daily returns, 80% coverage rule | Diagnostic model on its actual matched window only |
| Observed max drawdown | Drawdown on actual marks | Lower-bound path-risk diagnostic |
| Growth excluding largest positive interval | Sum log returns minus max(0, largest interval return) | Luck diagnostic, not achievable P&L |

H=30 primary; H=14/45 are fixed diagnostic sensitivities after primary runs, not alternative winners. Retain earlier 7/21/60/90 findings rather than rerunning the entire search.

Report calibration bins, Brier/log loss versus training prevalence, PR-AUC, top-tail enrichment and retained growth on held-out months. Raw loss is measured over actual delayed holding duration: report duration distributions and exact/delayed endpoint splits. Hold-to-horizon loss is not the production gate-exit outcome; compare with the realised gate exit path.

Do not hard-gate on uncalibrated positive Ridge forecasts. Dense-risk comparisons must restrict all comparators to identical predicted dates/rows and report lost coverage. Imputation does not establish daily-risk accuracy for weekly vaults.

## Phase 2: bounded repeatability and directional diagnostics

| Feature | Windows | Definition/support |
| --- | --- | --- |
| Largest positive gain share | 30/60 days | Largest positive log contribution / all positive contributions; 4 comparable intervals |
| Top-three gain share | 30/60 days | Largest three / positive total; 6 intervals and at least 4 positive |
| Growth excluding best interval | 30/60 days | Observed growth less largest positive contribution; retain elapsed duration/count |
| Positive-week fraction/dispersion | 60 days | Non-overlapping fixed UTC weekly endpoints with observed closes; 4 valid weeks |
| Negative-interval fraction/time under water | 30/60 days | Observed downside frequency and elapsed time below observed peak; 4 intervals |
| BTC beta/correlation/R² | 30 primary, 90 diagnostic | 10 aligned pairs, positive BTC variance and residual degrees of freedom |
| BTC-residual growth/downside | 30/90 days | Beta estimated strictly before each evaluated interval; 4 subsequent residuals |
| Flat-mark duration/following jump | 30/60 days | Observation-quality diagnostic |

Missing denominator/support means missing; zero measured loss is not missing. No feature changes global admission.

Keep daily-close and irregular-interval variants separately named. Gain shares mechanically depend on positive-event count: compare within count/duration cohorts and fixed-weekly versions where supported. Downsample dense paths to quantify sensitivity; do not assert polling invariance or interpret a weekly jump as a one-day event.

For BTC use common calendar closes for dense series; for sparse series align daily-resolution BTC prices to actual multi-day endpoints within an explicit maximum 24h error, reporting errors. Exclude sub-day intervals from the sparse estimator. Never blindly reuse the old unused `_btc_returns`: normalising intraday endpoints can fabricate zero BTC returns. Use the cached Binance `fetch_binance_price()` if refresh is needed. Low beta is not proof of market neutrality.

Evaluate incremental IC beyond downside/volatility, TVL and sampling on identical rows. Residualisation diagnoses independent information; it does not disqualify useful low-risk exposure. BTC-up/down conditional performance is an outcome report, not another model-feature search.

At most one diagnostic model refit adds this entire predeclared family to A2. It cannot replace the primary model or become shortlist-eligible. Do not pick individual inputs from evaluation-period IC.

## Phase 3: young access and sizing, independently

Young-vault research runs regardless of primary results. Do not require young cohorts to match older cohorts' losses before studying them.

Run two paired access extensions, A0-young and A2-young:
- Apply 14-day loss gate where observable; otherwise retain sparse admission and flag gate unavailable.
- Keep production ranking for normally scored vaults. For unscored young names, map positive observed short-growth proxy to a production-score percentile using training data only. Use the identical mapping in both arms; no positive growth evidence means score zero. Record this as an explicit ranking extension, not pure admission.
- Define the proxy as observed interval growth per elapsed day in the latest 30-day window (or explicitly labelled available shorter span). Build its empirical training CDF from prior eligible rows and map to the prior finite production-score quantile. Freeze monthly, weight dates equally, and use production/address tie order. If no training mapping exists, score zero with a warm-up flag.
- For unavailable 90-day sizing risk, use 30→14→7-day daily risk, then capped equal-share fallback. Do not convert interval risk into calibrated daily volatility.
- Apply a 5% cap to every under-90-day-history name OR name lacking credible measured daily risk, including old weekly vaults. Keep the same fallback policy in both arms. For short-risk fallback use the existing 5% annualised credibility threshold; sub-floor risk gets the conservative equal-share treatment.
- Preserve six forward-filled daily slots; report the separate effects of access, mapping, sizing and loss veto. Save selected capital and realised losses by age/sampling; IC alone is not profitable access.

One sizing sensitivity on frozen A0 and A2: limit accepted dollars to each name's original normalised intended allocation as well as concentration/TVL caps. Do not redirect displaced capital beyond that allocation. Leave cash. Add a causal cash-matched A0 using the same decision-time deployment budget; distinguish cash dilution from selection. No adaptive breadth or covariance optimisation.

## Evaluation and decisions

Report whole-universe and selectable-neighbourhood IC, selected-basket growth/losses, calibration and monthly consistency. Portfolio results must not be inferred from IC.

Use common weekly UTC valuation endpoints alongside marked daily metrics, preserving all weeks. Weekly sampling does not recover unobserved NAV paths: report capital-weighted staleness, dense-period paired results and sensitivity to mark-age coverage. Never require all names to be fresh simultaneously. A candidate cannot qualify because its book has more carried prices.

Use paired contiguous-calendar-block uncertainty across arms: H+14 and 2(H+14) sensitivity for labels, ceil((H+14)/7) weeks for weekly portfolio comparisons. Keep zero-mark dates/weeks rather than compressing calendar time. Report nominal blocks, valid resamples and gaps. For the three primary candidates use simultaneous paired bounds on Sharpe differences, preserving dependence across arms; any family draw must be finite for the complete statistic family.

Run registry before outcomes: four primary arms (including anchor); up to six horizon sensitivities; one family refit; two access extensions; two sizing variants plus one cash-matched anchor; matched-null controls and contributor-removal reruns explicitly diagnostic. Only A1/A2/A3 at H=30 may be shortlisted.

Shortlist point criteria: higher net Sharpe, no higher coarse-clock volatility/downside, no deeper DD, CAGR at least 10%, and at most 5 percentage points CAGR below A0. The 10% floor and five-point margin are provisional research policies, not approved production mandates. Report 5%-annual-reference excess Sharpe as a sensitivity, not an asserted executable yield. Report the 20–30% aspiration separately. If uncertainty includes material harm, verdict is inconclusive despite point-estimate passing.

Save CAGR, Sharpe, downside/volatility, DD/ulcer, fees, turnover, invested fraction, weekly/monthly cash, capital-weighted staleness, per-name targets, zero/missing-score incidence, veto incidence, top-profit concentration and actual rebalance counts.

Remove best day/month from fixed-ledger attribution as labelled counterfactuals. Separately rerun candidate and A0 with the same leading contributor excluded, using each arm's leader in turn. Do not equate P&L subtraction with reallocated performance. Report BTC regimes and results excluding February; these are falsification checks, not new tuning targets.

If learned veto does not beat simple controls, prefer the simple mechanism. Stop families with no incremental evidence. No production promotion from this repeatedly examined year; freeze a surviving specification for later unseen-time evaluation without postponing current work. Exact engine replay plus independent ledger reconciliation precede production-improvement claims.

## Deliverables and acceptance

Append:
1. `05-stable-profit-selection.ipynb`: pool diagnostics, generic baseline parity, fixed models/policies and primary replay.
2. `06-repeatability-and-direction.ipynb`: bounded diagnostics, confound checks, matched dense-risk diagnostic and family refit.
3. `07-stable-profit-validation.ipynb`: paired access, sizing sensitivity, uncertainty/concentration checks and verdict.
4. `summary-03.md`, feature/target/run manifests and prediction/pool/holding/trade/equity artefacts in the new directory.

Before full runs: no-op parity; synthetic young/weekly predictions; future-mark perturbation; measured-zero/missing-risk distinction; BTC alignment; below-TVL raw-mark sale; empty-pool handling; partial-sale fee/cost basis; cap/budget and equity reconciliation.

Use `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent`, saving progress. Rerun dependent outputs after corrections. Review implementation against this plan and actual production code.

## Independent review and adjudication

Claude CLI confirmed model `claude-opus-5`. [Full independent review](claude-review-opus5-stable-profit-plan-01.md); prompt/raw output `_review/19-*`; original draft `_review/19-stable-profit-plan-before-review.md`. Subsequent implementation reviews and the post-fix audit are recorded in `_review/20-*` through `_review/28-*`.

The post-fix audit's remaining documentation findings were corrected in
`summary-02.md`, `summary-03.md` and this plan. Notebooks 05–07 were rerun
after the final source edit; no unresolved high or medium finding remains.

| Suggestion | Decision |
| --- | --- |
| Preserve return ranking, test directional/downside vetoes | Accepted A1/A3 |
| Use sparse-compatible tail-loss classifier | Accepted A2; dense model's late start verified directly |
| Generic policy path/no-op parity, coarse risk, staleness, explicit trial count | Accepted |
| Conservative sizing for old sparse names | Accepted 5% cap; no assumption interval risk is calibrated daily risk |
| Sortino-leg inversion/CAGR-only replay | Deferred; conflicts with prior load-bearing-leg evidence and adds tuning; retain margin-IC diagnostic |
| Delay young access until loss rates match old vaults | Rejected: conflicts with explicit user requirement |
| Event concentration is disproven | Rejected: NB28 review documents confounded targets and invalid bootstrap inference; retain bounded diagnostics |
| Reuse old BTC helper for exact interval alignment | Rejected as written; daily resolution cannot align arbitrary intraday endpoints |
| Drop zero-mark dates from bootstrap | Rejected; changes calendar estimand and dependence |
| Return signal absent / 20–30% impossible | Rejected as overstrong; loser-avoidance and trade-off remain hypotheses |
| New tie-break only for risk overlay | Deferred; preserve common tie order and log saturation |
| Backfill positive-growth-gate failures | Not needed after removing uncalibrated growth gate from primary arms |
