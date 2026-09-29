# Smoke-test finding: the naive Sortino t-statistic prefers pumps, not evidence

Found while verifying `14-evidence-weighted-plan.md` splices through the real builder (not part of
the pre-registered protocol; informs Draft 2 before NB14-NB19 are built for real).

`sortino_t_at_entry` across the 75 positions the `core_fraction=0.7` smoke run took correlates
**-0.41** with realised P&L. The single worst position, "$🏧| ATM |🏧", entered on 2026-04-03 at
`sortino_t = 9.49` from 45 fresh observations - the maximum score the plan's default
`evidence_t_cap = 3.0` can express - and lost **-$28,990** over 6 days, the largest loss of any
position in the run.

Root cause: `evidence_t_cap` clips the score at `t = 3.0`, so a vault at `t = 9.5` on 45
observations scores identically to one at `t = 3.0` on 365 observations. The formula
`t = s * sqrt(n) / sqrt(1 + s^2/2)` already rewards larger `n`, but the clip erases exactly the
discrimination between "extreme ratio, thin sample" and "moderate ratio, deep sample" that the
whole point of a t-statistic is supposed to buy. And at n=45 the normal-approximation SE the
formula uses is itself unreliable - the true sampling distribution of a short-window Sharpe/Sortino
estimator is fat-tailed, so extreme t-stats are *more* likely at small n than the formula assumes,
not less. A smooth, sharp early run - which is what a pump looks like before it reverses - is
exactly what produces one.

Candidates for Draft 2, to reconcile with the Codex review's answer to open question (a):

1. Shrink the per-vault mean Sortino toward a cross-sectional prior (population median across
   scored vaults) by `n / (n + k)` before computing `t`, so `t` cannot reach its ceiling on a thin
   sample regardless of how extreme the raw ratio is. This is the structural fix; the clip alone
   is not one.
2. A calendar-day minimum (e.g. 21-30 days since inception) in addition to the fresh-observation
   count, since `evidence_min_fresh` counts non-zero-return days and a vault trading actively for
   a week can clear 45 "fresh" observations on 2-day-cycle sampling faster than its risk is
   knowable.
3. Winsorize the daily return series before computing the mean/downside inputs, so one explosive
   move cannot dominate a 45-observation window on its own.

Not mutually exclusive; (1) is the one that would have stopped this specific case, since 45
observations of a levered pump ratio should not out-rank a deep, merely-good record regardless of
where t is capped.
