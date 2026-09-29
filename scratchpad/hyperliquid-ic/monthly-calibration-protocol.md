# Monthly calibration protocol

Notebook 24 follows corrected notebook 23. This is a bounded exploratory experiment on previously examined history, not a fresh statistical holdout.

- Grid: consistency power {1,2}; negative-month frequency penalty {0,1,2}; loss-size penalty {0,1}; positive-return cap {1%,2%}; lookback {3,6 months}. Total 48 settings.
- Formula: `p**alpha * min(median_positive_return/tau, 1) * exp(-penalty*q - severity*downside/tau)`.
- Available completed months; partial unannualised history when there are none. Two earlier marks at least one day apart suffice. Weekly observations are supported.
- Common admission gate: positive trailing 14-day return, using available shorter history for young vaults. No monthly compounded-growth gate differing between the two lookbacks.
- Daily cross-sectional diagnostics from 13 September 2025. Historical TVL floor $7,500. Execution applies the inherited deposit and capacity checks in addition; the diagnostic pool is an approximation to the opportunity set, not the executed book.
- Label horizons 30 and 60 days: return, positive-return indicator, drawdown, downside endpoint return, and negative 30-day-block frequency. Future gaps exceeding seven days at required endpoints make labels unavailable, not zero. Rank before applying that label mask and report coverage.
- Top fifth versus the rest, deterministic address tie-break; report rank IC and young/mature cohorts. Statistics require five labelled vaults, not five observations per vault.
- Calibration labels must mature by 1 April 2026. Later evaluation decisions start 1 April. Intervening overlapping training labels are embargoed.
- Qualification: positive top-group return, nonnegative positive-return uplift, positive drawdown uplift at both horizons, and positive median drawdown uplift among one-parameter neighbours. Order by neighbourhood median then worst-horizon drawdown uplift. Select three settings; fill missing qualifying slots with clearly labelled diagnostics.
- Matched portfolio arms: original ranking and the three monthly scores, all with six positions, equal weights, 33% portfolio-weight cap, 33% historical vault-TVL capacity, identical recent-return gate, cash policy and execution thresholds. Only ranking changes within this comparison. These limits isolate score effects rather than prescribe production allocation.
- Separate original inverse-variance anchors must exactly reproduce corrected notebook 23 in the two historical windows.
- Backtests: full history, Hyper-ai period and a separate cold start on 1 April. Historical windows are diagnostic because shortlist selection uses part of them. The later cold-start window has no inherited training-period positions, but its dates are still previously researched.
- Re-simulate the first training-shortlisted setting's later run with its largest profit contributor excluded from inception. Do not select another formula using this stress outcome.
- Keep all failures. Prefer stability across neighbouring settings and chronological periods; do not infer independent sample counts from overlapping daily labels or claim ranking skill from a profitable portfolio alone.
