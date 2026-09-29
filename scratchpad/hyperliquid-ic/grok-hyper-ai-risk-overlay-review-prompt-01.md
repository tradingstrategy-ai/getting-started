Review `scratchpad/hyperliquid-ic/hyper-ai-risk-overlay-plan-01.md` with a practical, independent research judgement. Read-only: do not edit files, run notebooks/backtests, install tools or change external state. No subagents. Avoid overengineering. Return a concise review, not a rewritten plan or a broad search.

User wants to use the repaired NB30 evidence to improve actual hyper-ai risk and possibly reduce September 2026 drawdowns. They prefer high Sharpe with reasonable CAGR around 20%, not beating incumbent CAGR. September loss causes have NOT been established. NB30 decision data only covers through 9 September. The proposed experiment preserves actual production selection/cadence and compares gentler sizing, a recent/long volatility haircut and a causal uniform-exposure control. Q is diagnostic only.

Read these sources before giving findings (bounded excerpts are enough):
- `/Users/moo/code/strategies/strategy/hyper-ai.py`: docstring, parameter block, compute_sizing_weights, decide_trades including fee and allocation/trade-generation path. It is currently CAGR/Sortino and inverse variance, not the old Sharpe incumbent.
- `scratchpad/hyperliquid-ic/summary-nb30-repaired-01.md`: latest evidence supersedes original NB30 results. Residual Q return IC after G/P/V is about .005/.003, top Q group still loses; risk signal remains.
- `scratchpad/hyperliquid-ic/rolling-profit-risk-track-summary-01.md`: NB27 sizing failed on bad membership; NB28 risk/exposure interventions mixed or failed.
- `scratchpad/hyperliquid-ic/production-candidate-vs-research-reproduction-differences.md`.
- `scratchpad/hyperliquid-ic/allocation-decomposition-summary-01.md`: do not repeat breadth/cap changes or claim all strategies share accounting.
- Relevant volatility indicator implementation imported by hyper-ai if needed to assess estimator consistency; avoid a repository-wide read.

Focus on (1) whether September/live vs current-source claims are properly bounded; (2) mathematical and execution correctness of post-allocation haircuts and H2U; (3) distinction between cross-sectional risk evidence and an unproven temporal deterioration signal; (4) duplicated failed experiments; (5) minimal fixes for any blocking ambiguities. Respect the user's no-new-long-history-barrier requirement. Retaining current production policy in a matched test is intentional.

Return verdict, high/medium/low actionable findings with file/section references, at most two ideas to replace an unnecessary arm or strengthen a control without a grid, and the files actually read. Do not assume unavailable production data exists. Do not recommend a new model, multiple notebook framework, vol/threshold optimisation or deployment. Four arms/two periods is intentionally small. Finish once the listed sources and concrete design have been reviewed.
