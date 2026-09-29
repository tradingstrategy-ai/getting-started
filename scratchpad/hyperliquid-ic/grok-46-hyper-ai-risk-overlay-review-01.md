# Grok 4.6 risk-overlay plan review

Completed 2026-09-19 using `--model grok-4.6 --reasoning-effort xhigh --sandbox none`; resolved model `grok-4.6-build`, normal end_turn completion. Review-only prompt, no subagents. This reviews the initial draft, not subsequent revisions.

I'll review the plan against the listed sources only — read-only, no notebooks or edits — and start by loading the plan plus the review skill.The `/review` skill wants subagents; this request is a plan review with no subagents, so I’ll read the listed sources myself.I have the evidence notes; next I’ll read the strategy’s sizing, trade-generation, and volatility estimator.I need the allocation hook and the parent volatility estimator so I can check whether the haircut and H2U are actually implementable as written.**Verdict:** Proceed. Four arms and two windows are the right size. The parent is the current CAGR/Sortino plus inverse-variance source, Q stays diagnostic, and H2U is the correct cash-control idea. Do not implement until three pins are explicit: September is only as complete as the frozen cutoff, H2 uses the parent unannualised volatility estimator, and the haircut mutates post-cap dollar targets before `calculate_target_positions`.

## High

**1. September is not yet a live-loss object.** The plan’s Stage 1 caveats are right; the later wording still overreaches. `production-candidate-vs-research-reproduction-differences.md` has no full-history production equity, only a Jan–Jul current-source replay (summary, not a daily ledger) plus an older archive. Repaired NB30 decisions stop on 9 September. Other frozen panels in this chain end 8 or 12 September. A current-source engine run is not the live September book. If the deployed revision, starting holdings, cost bases and equity ledger are not actually on disk, withhold production-loss-prevention claims. Treat “September” as month-to-date through the frozen cutoff, not calendar September and not NB30’s 9 September panel extended by silence.

**2. H2’s zero/floor rule fights the parent estimator.** `inverse_vol` is unannualised `close.pct_change().rolling(window, min_periods=window).std()`, then `clip(lower=1e-4)` (`VOL_FLOOR`). Sizing does not annualise. The plan’s “≤1e-12 in annualised units, either missing or near-zero → m=1” would treat a long window sitting on the floor as unmeasurable and skip the exact flat-then-move case H2 is meant to catch. Pin: same return series and pandas sample std as `inverse_vol`; change only the window; inherit `VOL_FLOOR`; m=1 only when either std is NaN/non-finite; a floored finite std is measurable. `m = min(1, σ90/σ30)` is then the same as `min(1, inv_vol_30/inv_vol_90)` after the floor.

**3. “Before trade generation” is the wrong hook if taken literally.** Parent order in `decide_trades` is `normalise_weights` (this path sets `position_target` and still redistributes leftover capacity with `waterfall=False`), then `update_old_weights`, then `calculate_target_positions` (`position_adjust_usd = position_target - old_value`), then trades and the backtest redemption-fee snapshot. Mutating `position_target` after `calculate_target_positions` leaves stale adjusts, so requested haircuts will not be the trades. Pin the NB28 pattern: after `normalise_weights` has produced `b_i`, set `position_target ← b_i * m_i` (H2) or `u * b_i` (H2U), do not call `normalise_weights` again, then let `calculate_target_positions` run. Same-state checks in the plan (all m=1 ⇒ H2=H0; equal m ⇒ H2=H2U; halved m does not refill) only hold with that hook.

H2U’s `u = Σ b_i m_i / Σ b_i` is the right uniform control on a shared state. It is not a promise of matched September cash after paths diverge.

## Medium

**Cross-sectional evidence is not a temporal warning.** Repaired NB30 residual Q return IC is about 0.005/0.003; the top group still loses; drawdown association remains. That is a cross-sectional risk ranking, not proof that `σ30/σ90` on held names leads losses. The plan states this once; Stage 1 “warning before / after / none” labels on one month must stay descriptive. H2 only cuts when short-window vol exceeds long-window vol. If September losers were already high-vol (`m ≈ 1`), H2 will not fire.

**H1 is not a drawdown overlay.** `inverse_variance` is `1/σ²`; `inverse_vol` is `1/σ`. At the pinned 33% cap the source already says inverse variance won on return and that the ranking reverses with concentration. H1 is a milder low-vol tilt and can *raise* weight on jumpy held names. That is the intended NB27 follow-up on the real parent (NB27 failed on B11, Jaccard 1.0, all sizing arms ~−90% CAGR). It is not a duplicate of NB27, and it is not H2.

**H2 is not a duplicate of NB28 E2.** E2 was `exp(-drawdown/0.10)` on B00 with blacklists off; it failed on the full and later windows, and the scale controls changed the reading. Reusing the cash-preserving post-cap hook and a uniform control is what that summary asked for. Do not revive the drawdown grid, Q>0 (97.6% overlap with P≥0.75), or N/W/V. Allocation decomposition still forbids reading those Sharpe/drawdown moves as a shared accounting result.

**H2−H2U in September is path-contaminated.** Both arms are live from the start of the full-history window, so by September membership, cash and cost bases differ. A better September reading of “vault-specific vs just less invested” is a frozen-H0 overlay, not another simulated arm.

**Sub-threshold trims.** Sell threshold is 0.5% of initial cash ($750 at $150k). Small `m` moves will no-op; log requested vs executed or a “no September effect” result is unreadable. Haircuts that push a name under `min_portfolio_weight_pct` (0.5%) can become full exits; that is operational, not selection-policy.

**Two clocks.** Engine `get_indicator_value` uses the previous bar, not the decision timestamp. Q must keep repaired NB30 timing (`T = source_date+1`, marks strictly before T). Do not join NB30’s 9 September decision table onto later cycles, and do not claim “Q led, ratio did not” until both series sit on the same decision T.

## Low

- Hash the current `hyper-ai.py`. Do not use the docstring 61.72% CAGR / 2.88 Sharpe archive, B00, A0b, or `hyper-ai-v6.py` as matched H0.
- Pin the comparison window in timestamps: parameters are 1 January–10 July exclusive; the documented table and production-candidate window are through 8 July.
- The two windows are independently initialised, not independent samples. Full-history contains January–July.
- Overlapping 30/90-day windows mute “deterioration” versus a lagged complementary window. Keep the overlapping definition; do not invent a new estimator.
- No new history gate: missing `σ90` on a young name is m=1, not exclusion. Parent selection still needs 360/45-day scores.

## Two ideas (no extra live arm, no grid)

1. **Strengthen H2U for September:** on H0’s saved per-cycle `b_i`, apply the same causal `m_i` and the same `u`, and report requested cuts versus later realised losses. That answers whether the overlay would have reduced the inherited parent path, which live H2 vs H2U by September will not.
2. **Do not drop H1 or H2U.** H1 is the actual-parent sizing follow-up; H2U is what made NB28 interpretable. If the September table needs one extra column, it is days since last true mark next to the sigma ratio, not a fifth arm.

Do not add Q to H2 in the same notebook, do not search thresholds, do not deploy on a better September slice, and stop if H2 does not beat H2U with usable lead time.

## Files read

- `scratchpad/hyperliquid-ic/hyper-ai-risk-overlay-plan-01.md`
- `/Users/moo/code/strategies/strategy/hyper-ai.py` (docstring, `Parameters`, fees, `compute_sizing_weights`, `decide_trades`, `inverse_vol`)
- `scratchpad/hyperliquid-ic/summary-nb30-repaired-01.md`
- `scratchpad/hyperliquid-ic/rolling-profit-risk-track-summary-01.md`
- `scratchpad/hyperliquid-ic/production-candidate-vs-research-reproduction-differences.md`
- `scratchpad/hyperliquid-ic/allocation-decomposition-summary-01.md`
- `tradeexecutor/strategy/alpha_model.py` (`normalise_weights` / size-risk refill, `calculate_target_positions`, trade generation)
- `tradeexecutor/strategy/pandas_trader/strategy_input.py` (`get_indicator_value` previous-bar clock)
- `scratchpad/hyperliquid-ic/build_rolling_track.py` (NB28 post-cap haircut / `_SCALE` hook)
- `.claude/docs/vault-selection.md` (bounded; universe freeze only)
