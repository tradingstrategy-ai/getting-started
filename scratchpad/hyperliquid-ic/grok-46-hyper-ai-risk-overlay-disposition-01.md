# Risk-overlay plan review disposition

Grok reviewed the initial [plan](hyper-ai-risk-overlay-plan-01.md) on 2026-09-19 using `--model grok-4.6 --reasoning-effort xhigh --sandbox none`, review-only instructions and no subagents. The CLI resolved `grok-4.6-build` and ended normally with `stopReason: end_turn`. See [review](grok-46-hyper-ai-risk-overlay-review-01.md) and [prompt](grok-hyper-ai-risk-overlay-review-prompt-01.md). Raw JSONL and stderr are retained beside the review.

Verdict: proceed after clarifying three implementation requirements. No arm removed or extra simulated arm added.

## Incorporated

- September means month-to-date through the actual frozen cutoff. Production-loss attribution requires the deployed revision and starting state/ledger; otherwise label the result a source backtest. No extension of NB30's September coverage by assumption.
- Pin sigma to the parent's daily sample standard deviation, unannualised, with `VOL_FLOOR=1e-4`. Removed the draft's annualised near-zero fallback. Missing estimates remain m=1; finite low volatility uses the parent floor. Added floor-activation reporting.
- Pin target modification immediately after `normalise_weights`, before `calculate_target_positions`, with no re-normalisation. This avoids stale trade adjustments and refilling the intended cash reserve.
- Add a same-H0-state target diagnostic for H2 and H2U, with no extra backtest, to distinguish immediate allocation effects from accumulated membership/cash/cost-basis divergence.
- Explicitly report ineffective small trims, minimum-weight full exits and execution delays. H1 may increase exposure to volatile names; H2 cannot warn merely because absolute volatility is persistently high.
- Clarify two overlapping windows, January simulation boundaries versus metric endpoints, the previous-bar indicator clock, and the difference between cross-sectional risk persistence and temporal warnings.
- Corrected a draft typo: four September paths, all contained in the full-history runs.

## Interpretation retained

The experiment still has four arms over two windows. Q stays diagnostic. No volatility grid, new history gate, concentration change or deployment. Retaining production selection does not mean newly enforcing complete 360-day scores: preserve actual source behaviour, including its existing treatment of unavailable scores.

The revised plan has not received a second external review. No implementation or backtest occurred in this planning task.
