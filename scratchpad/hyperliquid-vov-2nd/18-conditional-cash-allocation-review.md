# Experiment 18 — Claude contribution and review

Date: 12 October 2026. Accompanies the [conditional cash allocation plan](18-conditional-cash-allocation-plan.md). Planning only; no NB18 notebook or experiment has been run.

## Review method

Claude CLI was requested explicitly by the user with Fable 5.1. Calls use `--model claude-fable-5-1`, high effort, safe mode, tools disabled, strict MCP configuration, no session persistence and JSON output. Both calls returned success and confirmed `claude-fable-5-1` as their only model, with no permission denials or fallback. The second call reviewed the revised formulas, worked example and existing risk-helper excerpts.

Claude reviewed supplied text and source excerpts. It did not independently inspect the repositories, run the experiment, establish future profitability or verify vault closure events. Raw prompts, JSON responses, extracted reviews, draft snapshots and their hashes are retained in the ignored `_artifacts-restored-2026-10-07/18-plan-review/` directory.

## Contributions and decisions

| Claude contribution or critique | Decision and reason |
| --- | --- |
| Additional risk proportional to the current core's risk shrinks when idle cash is highest | Accepted. Use a lagged reference risk for the core mix normalised to 98% investment. The current account's core risk consumes that budget before additional allocation. |
| Use current equal-weight risk of six names, filling missing slots with a median risk | Modified. Use actual reference weights and a lagged median, without invented positions. Current volatility must not instantly expand the allowance; the reference remains hypothetical and is not an approved live risk level. |
| Separate pooled profitability from score discrimination | Accepted. Include a pooled lower-estimate gate and a score-group central-estimate gate, with separate activity and contribution diagnostics. |
| Band-based lower-bound gates may be inactive or collapse to pooled predictions | Accepted as a risk, not a known future result. Show support, pooled fallback, feasible dollars affected and concrete changed trades. Do not assume inactivity before execution. |
| Advantage divided by variance may reproduce risk weights within a score band | Accepted. Coordinator also identified that normalising these weights spends the full allowance even for tiny advantages. Replace it with a scalar amount decision derived from a quadratic growth approximation. |
| Use inverse volatility for new residual sizing to reduce amplification of risk-estimation errors | Accepted for the new sleeve only. The core retains its established inverse-variance rule and exact controls. |
| Replace the risk estimator with a new raw interval second moment and 75th-percentile peer prior | Rejected as an unnecessary unverified estimator change. Reuse existing regularised/gap estimators, with an explicit conservative maximum for sleeve risk checks and supported prior fallbacks. |
| Archive disappearance resolves to a cash redemption at the last NAV | Rejected. Disappearance is not an observed redemption, settlement or proof of zero subsequent loss. Only independently recorded terminal cashflows can resolve departure; otherwise retain censoring and its selection-bias qualification. |
| Use the legacy-versus-corrected fee difference as a statistical noise floor | Rejected. The fee convention is a systematic accounting difference. C-W's 2026 correction changes CAGR from 51.35% to 58.58%, about 7.23 percentage points, not the review's approximate 1.5 points. Neither number is a statistical significance threshold. |
| Remove single-vault and total sleeve exposure caps because the risk budget makes them redundant | Rejected. Low estimated volatility does not protect against jumps, stale marks or a vault failure. Keep provisional 5% single-residual and 25% total-sleeve limits, disclose them as research assumptions and show mechanical stress losses and binding frequency. |
| Drop the ten-versus-twelve-slot engine comparison | Accepted. Use common-state 10/12/no-ceiling capacity diagnostics; retain the twelve-slot operational ceiling without claiming it is optimal. |
| Defer covariance and fully adaptive replacement of the core | Accepted for this first notebook. Explicitly state that it cannot prove six core positions optimal. |
| Keep negative-forecast residual positions until the core or budget needs their cash | Modified twice. The final plan compares expected net redemption after holding with net redemption now, using the actual remaining cost basis and the same fees on both choices. Keep a fully forecast-free control. Retention can differ from desired allocation; report that difference. |
| Add a minimum holding period | Rejected for this matrix because it can conflict with mandatory risk reductions and core funding. Report holding times and round trips; preserve immediate required exits. |
| Examine HLP if it receives residual capital | Accepted as ordinary risky-vault exposure; no assumed cash yield or risk-free substitute. |
| Show exact PnL by core/overflow role | Qualified. Record role transitions and use a documented cost-basis attribution if it reconciles. Until then use whole-account vault attribution and descriptive role exposure; do not fabricate causal sleeve PnL. |

## Joint design after the first review

The revised design keeps nine methods: three economic controls, fully forecast-free risk-limited deployment, a matched economic-exit variant, pooled profitability gating, score-group gating, genuinely gradual amount sizing, and one larger risk-budget comparison. All run the complete fresh-2026 and full-history periods with causal warmup and shared corrected fees.

The main new mechanism is a cash-independent, lagged risk allowance. Current core risk uses up that allowance, so elevated current risk can stop residual buys without forcing the benchmark core to change. Independent dollar-exposure caps protect against risks that volatility estimates miss. Score calibration is allowed to fail or become a pooled estimate; missing scores remain a supported group rather than a default exclusion.

The initial scope expands beyond the six arms Claude proposed because the user explicitly wants score-conditioned admission, and because isolating a common forecast-based exit needs a genuinely forecast-free control. It remains a fixed matrix rather than a Cartesian parameter search.

## Focused second review

Verdict: **the revised matrix answers the economic question and the allocation formulas/worked alpha example are correct**. Claude identified implementation choices and possible inactivity that needed registration before coding. The final plan incorporates the changes below; they were made locally after the second review, and no third CLI review is claimed.

| Focused concern or contribution | Final disposition |
| --- | --- |
| Scalar alpha arithmetic and units | Confirmed: the worked expected-return contributions yield alpha 0, 0.5 and 1. Register the possibility that alpha saturates and report when it is genuinely gradual. |
| k=.75 may allow deployment chiefly in high-cash states | Accepted and stated explicitly. This is an intentional cautious first setting, not a promise of full deployment or a universal cash threshold. |
| Pin risk units, windows and prior pools | Accepted. Both windows are 90 days with inherited 30-update/interval shrinkage; square roots precede the maximum. Log sigma is an explicit first-order proxy. Reference and treatments use the same as-of eligible peer pool; wrapper code must prevent requested held IDs silently changing that pool. |
| Reference validity and pinned holdings | Accepted. Include risky pinned value once in both exposure and risk. Invalid/no-positive-risk reference decisions are omitted, logged and never replaced by zero. Require 30 valid prior decisions. |
| Fixed calendar-block origin | Accepted. Anchor 30-day support blocks on 1 March 2023; bootstrap duplicates cannot invent new support. |
| Endpoint support versus actual price mark | Accepted. Later observations establish recorded terminal coverage but are never used as earlier endpoint prices. No new age veto is imposed; mark ages and dense-observation sensitivity remain visible. |
| Full accrued fee as an exit hurdle favours retaining profitable positions | Accepted. Replace the hurdle with a scenario payoff comparison: net redeem-now versus expected net redeem-after-H, with the same cost basis and fee schedule. Do not call accrued profit fees universally unavoidable; their amount depends on future NAV. |
| Identify which forecast incumbents use | Accepted. The same shrunk group/pool gross-outcome distribution is used in every forecast-exit arm; R00 has no forecast exit. |
| Missing candidate order and unusable/flat risk | Accepted. Source zero/address ordering remains explicit, with distinct missing flag. Positive prior-backed flat paths are usable; unavailable positive risk blocks new exposure. |
| Compute proposals on the reference path before new engine accounts | Accepted as a no-feedback activity/constraint shadow, not a retained-sleeve backtest. It cannot justify deleting registered arms or claiming full-account equivalence. |
| Core top-up comparison under identical risk/capacity | Accepted as a shadow that quantifies whether additional names are necessary. No new engine arm or covariance model. |
| Separate unavoidable from decision-induced fees | Qualified. Fee deferral is state dependent and not automatically an avoided charge. Report paid charges, current liability, actual round trips and the scenario exit calculation without a spurious exact causal partition. |

## Final scope and limitations

The final plan has nine registered methods and eighteen complete-period accounts, plus cheap capacity/activity shadows. Forecast support and young/missing/sparse histories are explicit. Every new method shares the corrected fee convention and known execution constraints. The risk anchor is lagged and independent of the current amount of idle cash; it still adapts and relies on imperfect risk estimates.

The 25% sleeve and 5% individual residual caps are provisional experimental settings. A 50% simultaneous sleeve loss could still cost 12.5% of account equity, so the plan neither describes these as safe nor infers the user's production risk tolerance. It includes smaller-cap stress/capacity diagnostics. It also explicitly defers covariance optimisation and replacement of the protected core, rather than claiming six positions are optimal.

No research return forecast or risk constraint guarantees profits or realised drawdown. Previously inspected historical periods overlap. A candidate needs subsequent observation before a deployment claim. No NB18 code, notebook or backtest was executed during planning.
