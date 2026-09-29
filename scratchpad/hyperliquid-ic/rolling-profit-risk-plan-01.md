# Rolling profitability and risk experiments

## Objective and status

Find high-Sharpe portfolios with steady positive profit and reasonable CAGR around 20%. Beating hyper-ai is not the objective. Use direct rolling share-price metrics, not weekly/monthly profitability admission gates. Young vaults and sparse weekly observations must remain usable. Allow 1–n vaults; concentration is a reported outcome, not an acceptance requirement.

StratWise and **[ Systemic Strategies ] L/S Grids** are illustrative positive references, never whitelist entries or targets for fitting thresholds. Their paths differ: L/S Grids is considerably bumpier. ATM is the counterexample that looked smooth before collapsing. No price-only rule is expected to reject every future loser.

Plan revised after nine Grok 4.6 research-history passes and one synthesis. Read [Grok’s review](grok-46-rolling-profit-risk-review-01.md) and [our disposition](grok-46-rolling-profit-risk-disposition-01.md). No new strategy implementation or backtest has been run. The pre-review draft is preserved under `_review/rolling-metrics-grok46/plan-before-review.md`.

## Research lessons carried forward

| Evidence | Consequence for this plan |
|---|---|
| Lower-vol NB28/34: rolling risk predicts future risk; later audits corrected some original rejection labels | Reuse the risk evidence. Do not require it to predict every outcome simultaneously |
| Lower-vol NB32: return floor followed by pure stability ranking selected calmer vaults but lost too much return | No repeat of “choose the calmest survivors” as the main proposal |
| Lower-vol NB34–36: modest measured-volatility exclusion was conditionally positive; guards neutralised related variants | Keep as historical context, not another exclusion-count search |
| Lower-vol NB38/39: no established benefit from trimming; longer-history Sharpe/Sortino had useful forward association | Untrimmed risk-adjusted scores remain plausible; long-history evidence does not validate young-history estimates |
| IC NB19/20: hard screens removed winners, changed exits and forced replacements | Separate ranking, sizing and exit changes; do not stack screens |
| IC NB21/22 corrected interpretation: flexible size did not establish steady selection | Treat breadth as a separate deferred question; do not inherit the withdrawn conclusion |
| IC NB23/24: monthly scores hid within-month swings and saturated all selected scores at 1 | Inspect score distributions and allocation effects; use rolling paths |
| Waterfall experiments: sizing, capacity and cadence were load-bearing; some attractive IC results were lookahead-contaminated | Keep execution fixed while testing selection; reproduce controls on the same snapshot |
| Young vaults sometimes passed filters but got zero sizing weight from missing 90-day volatility | Audit actual dollars, not just eligibility |

Use current corrected notebook headings and artefacts. `summary-04.md` contains superseded forward-fill-era figures; do not use its portfolio numbers as current. A0, A0b, corrected engine controls and production archives are separate comparators, not interchangeable results.

## Shared contract

- Start from the corrected NB24 engine and frozen inputs. Reproduce corrected NB23/24 original-policy controls exactly before strategy changes; verify single redemption-fee application on full and partial sells. A0b is an optional independent comparison, not the same engine.
- Freeze input hashes, code revision, universe, execution settings and comparison dates in a manifest. Read the current `/Users/moo/code/strategies/strategy/hyper-ai.py` and record differences from the research control; do not silently relabel the research control “current production”.
- Use both the full-history and hyper-ai windows on identical dates for each paired comparison. Default frozen NB24 common windows: 13 September 2025–8 September 2026 and 1 January–8 July 2026. Preserve native engine starts and distinguish sliced ongoing portfolios from cold starts. Include a cold start on 1 April–8 September 2026. Changes to the data endpoint require an explicit new manifest and all paired controls rerun.
- Features are evaluated daily from strictly earlier observations. Keep the inherited trading/rebalance cadence, exit policy, capacity limits and trade thresholds fixed unless the notebook explicitly changes one.
- Primary comparisons disable local name blacklists, consistently across arms. Retain operational availability and historical capacity checks. Do not selectively restore Scared Money or other names after seeing results. An optional production-universe reference is separately labelled.
- Share-price features only. Age/evidence metadata are allowed; BTC is optional context. No account P&L, volume, follower counts or social factors.
- No hard minimum age or compulsory count of daily/weekly returns. Underdetermined metrics remain missing, with an explicit sizing fallback. Do not backfill history or score missing risk as zero.
- Early/later comparisons are retrospective: all these dates have been researched. Labels used for any early-period choice must mature before 1 April. Do not call later results an untouched holdout.
- Follow the causal availability and missing-data principles in `/Users/moo/code/freqtrade-strategies/.claude/docs/feature-engineering.md`; do not import unrelated market-specific requirements or a generic multi-year gate.

## Rolling metrics

Primary lookbacks: **14, 30 and 60 calendar days**, using available shorter history. Thirty days is the primary specification; 14/60 are separate sensitivity runs, not a parameter cross-product. Seven and 90 days are optional descriptive follow-ups only. No complete week or month is needed.

| Metric | Definition | Role |
|---|---|---|
| Elapsed-time growth `g` | Sum of observed interval log returns divided by elapsed days | Positive-profit ranking; multiply by 365 only for a common annualised scoring unit |
| Total risk `v` | `sqrt(365 × sum((r_i − m Δt_i)^2) / sum(Δt_i))`, with `m=sum(r_i)/sum(Δt_i)` | Annualised interval-based volatility approximation |
| Downside variation `d` | `sqrt(365 × sum(min(r_i,0)^2) / sum(Δt_i))` | Negative return variation |
| Drawdown `D` | Absolute worst observed peak-to-trough percentage decline in the window | Path damage hidden by endpoint gains |
| Trend slope `b` | Elapsed-time regression slope of log price | Descriptive sustained growth |
| Trend residual dispersion `e` | Elapsed-time-weighted RMS log-price residual | Descriptive unevenness; not a first-wave selector |
| Evidence | Available elapsed span, actual return intervals, typical/max gap, boundary coverage | Explain missingness and confidence; no age exclusion |

Use actual elapsed intervals for risk, not forward-filled zero returns. Continue forward filling for portfolio valuation. Interval risk is not sampling-invariant; show sparse/dense cohorts and a common seven-day sampling sensitivity, without excluding sparse vaults. Use at most one observation per UTC day for primary metrics, and show observed intraday drawdown separately when available. A boundary observation may precede the nominal lookback: include its actual elapsed interval and disclose effective span. A long interval is not evidence of zero intervening risk.

Two observations can estimate growth but cannot reliably establish volatility or trend residual dispersion. An exact two-point line fit must not produce perfect risk-adjusted desirability. No floor or fallback removes genuine uncertainty; disclose it.

## Notebook A — coverage, controls and decision-path diagnostics

Allocate the next free notebook number during implementation. This notebook provides one shared panel and checks that the intended mechanism can operate.

1. Reproduce the corrected engine control and save its pre-sizing candidate order, selected set, raw weights and final accepted dollars.
2. Calculate the rolling metrics and compare coverage of growth, production composite and production/new volatility. Show under-30-day, 30–89-day and 90+-day cohorts, and sparse/dense observation cohorts.
3. Show rolling series for both reference vaults and the earlier losing examples, with separate before/after entry curves. These are illustrations; never use their names or future paths in rules.
4. Save score distributions and tie rates. A monotonic transformation such as `log(1+max(g,0)/0.20)` cannot change positive-growth ordering by itself; no extra backtest is needed to establish that. It may change a ratio or sizing rule, which must be labelled separately.
5. Report forward 14/30/60-day return, risk and drawdown for the candidate groups. Future Sharpe is secondary and noisy. Ranking is formed before masking missing future labels; incomplete outcomes are missing, not zero. Daily overlapping labels are not independent samples.

Do not turn A into another broad feature discovery or all-target acceptance gate. Its outputs explain access, effect on decisions and whether the available-history candidates are profitable enough for the intended trade-off.

## Notebook B — separate short-history ranking from short-history sizing

Grok’s primary useful suggestion is to make short-history access concrete. Its proposed “ranking-only” change also changed sizing; this notebook explicitly separates the two.

Run a **2 × 2 factorial** at the primary 30-day lookback:

| Arm | Ranking | Sizing |
|---|---|---|
| B00 | Original research-control composite | Original 90-day inverse-variance implementation |
| B10 | Available-history growth `g`, higher first | Original sizing |
| B01 | Original composite | Available-history interval inverse variance |
| B11 | Available-history growth `g` | Available-history interval inverse variance |

Keep the original gate, six-position limit, caps, cadence and exits identical in these four diagnostic arms. Six and the inherited concentration cap isolate changes; they are not final portfolio requirements. Preserve the original gate’s behaviour for missing history and report it explicitly. If it blocks young vaults, add one separately labelled common-gate comparison across the affected arms; do not silently change it in B11 alone.

For new interval sizing, use `q_i=1/max(v_i,0.05)^2` when risk is estimable. For an underdetermined risk estimate, use the median finite raw `q` in that date’s selected set; if every selected risk estimate is missing, use equal raw weights. This is a neutral fallback, not an assertion of safety. Report fallback usage and resulting weights, especially for the examples. Do not silently impute missing risk with an upper-quartile training value or zero.

B10 may select young names but fail to fund them: that is a measured sizing limitation, not evidence that their ranking failed. Compare B01 with B00 for sizing alone and B11 with B01 for ranking under the repaired sizing path. Report interactions rather than calling the joint difference a single mechanism.

Add an **equal-weight sibling of B11**. For a clean sizing diagnostic, first replay the same requested candidate-membership schedule; then report whether operational rules cause actual holdings to diverge. Do not claim identical realised holdings merely because scores match.

Repeat B11 and its paired control at 14/60 days only after the 30-day outputs are inspected and documented. Do not choose a later-period winner and then describe it as an early-frozen lead.

## Notebook C — preserve membership, change exposure

This is independent of finding a new ranking winner. Run on the reproduced original policy and, if useful, one B candidate frozen from early-period evidence. Keep the candidate ranking and requested membership schedule fixed for paired diagnostics.

| Option | Exact change | What it tests |
|---|---|---|
| C0 | Parent allocation | Control |
| C1: no refill | Compute parent requested dollars once; after operational/capacity clipping, leave unused dollars in cash instead of reallocating them to other names | Whether residual capital was going into weak replacements |
| C2: soft downside exposure | Multiply parent requested dollars by `exp(−D/0.10)`, then apply the same operational clipping; released dollars remain cash | Whether visible path damage can reduce exposure without a hard veto or forced replacement |

First inspect and log the parent’s allocation flow. If it already leaves clipped dollars in cash, C1 is a documented no-op and is not presented as a new backtest result. “No refill” must name the actual redistribution step being removed, not accidentally change the initial normalisation or cash budget.

For C2, an underdetermined drawdown applies a multiplier of 1 and an explicit unknown flag: absence of evidence is not automatically a penalty. This is a declared permissive diagnostic, not assurance of safety. The fixed 10% scale is not fitted to the reference names; ATM’s observed zero drawdown would still receive no penalty. No further loss thresholds are tuned after outcomes.

For each exposure arm, compare with a uniform scaling of the parent’s weights to the same decision-time invested budget, without using future information. Show invested-basket outcomes alongside total portfolio metrics. This separates cash dilution from differential exposure. Actual caps/fills can make achieved cash differ; report that rather than claiming exact matching.

Keep fees/cadence unchanged. A reduction in turnover is a mechanism to report, not an excuse to attribute every improvement to vault quality.

## Notebook D — optional alternatives, not one combined grid

Proceed only after A–C have a written conclusion. Choose at most one option based on early evidence and explicit unresolved questions.

| Option | Minimal experiment | Why it remains optional |
|---|---|---|
| Graded fallback inside original composite | Preserve finite original scores. For missing long-history legs, apply the same original scoring maps to available-history estimates; keep old/new sizing as explicit controls | Preserves established ordering, but different histories may not be comparable and score saturation can return |
| Continuous joint profit/risk rank | `U(g)/max(v,0.05)`, with annualised `g` and `U(g)=log(1+max(g,0)/0.20)`, versus growth-only under identical sizing/gates | A candidate alternative, not a proven escape from NB32; must retain enough profit, not necessarily more return than control |
| Flexible breadth | Same frozen ranking/sizer with six versus all positive-score candidates, then independently remove the portfolio-weight cap | Tests allocation limits separately. Allow 1–n vaults and up to 100% portfolio weight, keeping historical vault-TVL capacity unchanged; no claim that more names means better quality |
| Slower resizing | Same daily signals and membership/exit rules, but apply discretionary weight updates less frequently | Cadence evidence exists; test only if turnover remains material. Do not simultaneously slow emergency/operational exits |

Defer trend-residual ranking, joint downside-plus-drawdown ranking, event trimming, learned classifiers, correlation clustering, BTC circuit breakers, reserved young-vault slots and any new monthly score grid. Raw trend metrics remain useful plots. No named-vault sleeves or compulsory confidence haircut.

## Results required from every executed comparison

- Equity curves, CAGR, Sharpe, volatility, drawdown, turnover, invested fraction and effective holdings on matched dates. Use one explicit return clock/annualisation convention; include weekly sensitivity.
- Actual vault selections and subsequent capital-weighted profitability/risk, not only historical score quality. Show requested → selected → sized → accepted dollars and reasons for zeros.
- StratWise and L/S Grids ranks, allocation dates and capital when available. No requirement that an objectively applied rule must select either name.
- Largest winners/losers, best-cycle contribution, and a full resimulation without the frozen candidate’s largest contributor. A diagnostic exclusion is not a new production blacklist.
- Missing-feature handling, sampling/history cohorts, score ties, cap hits and allocation changes. Verify calculations against a few independent scalar cases, including sparse and short histories.
- Label results as failed implementation, no-op, tested negative, inconclusive or promising. Historical signals stopped by old gates remain untested unless actually rerun.

The objective is a favourable return/risk trade-off near 20% CAGR, not a rigid pass/fail number in every slice. Lower risk with somewhat lower return can be useful; lower volatility without enough profit is not success. Do not require a risk score to predict higher forward return. Do not require beating every random strategy or every incumbent metric. Report uncertainty without inventing precise confidence from overlapping dates.

## Execution order and review record

Implement A, then B and C as separate notebooks with shared inputs and controls. Stop to explain results before choosing any D option. Do not implement all alternatives as an optimiser sweep.

Grok review completed on 17 September 2026: nine history passes and one synthesis, all with successful `end_turn`, actual backend `grok-4.6-build`. Coverage: 152 notebooks’ saved markdown narratives and 106 top-level research documents across `hyperliquid-lower-vol`, `hyperliquid-waterfall-rc` and `hyperliquid-ic`; the synthesis also received current production code, feature documentation and the reference comparison. Targeted source checks were made, but this was not an audit of every code cell or a numerical rerun.

Coverage, prompts, individual reviews, raw JSONL and validation records: `_review/rolling-metrics-grok46/`. The final plan contains author corrections after the review; it is not a claim that Grok reviewed those revisions in a second pass.
