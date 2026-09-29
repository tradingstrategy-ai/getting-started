# Fable review of the experiment rewrite plan

Requested model: `fable`. Reviewed the authoritative `rewrite-plan-01.md`, with `plan.md`, earlier results and implementation supplied as context. This is a review; its recommendations have not been applied to the plan.

## Assessment of the review

The useful implementation clarifications are the decision/fill timestamp convention, production signal parity versus research execution, mixed risk-available/risk-missing basket sizing, and precise daily-risk label construction. Report distinct outcomes and actual holding durations alongside daily prediction counts.

Do not apply every recommendation literally:

- Finding 2 is a documentation clarification, not a blocking conflict: the authoritative rewrite already says it supersedes all conflicting rules in the original plan.
- Finding 4 proposes overlapping `<=` feature and `>=` entry timestamps, which does not guarantee its claimed strictly later fill. Choose and test an explicit same-mark idealisation or strictly later execution convention; changing the inequality cannot be left implicit.
- Finding 5's distinct-outcome support is useful for uncertainty reporting, but must not become a new 60-week admission or training barrier. Daily predictions and young/sparse-vault access remain requirements. Equal-date IC measures daily decision performance; report dependence-adjusted uncertainty and outcome-weighted results alongside it.
- Findings 8 and 9 are suggestions, not validated estimators: dividing both regression variables by duration is not generally equivalent to duration-weighted interval OLS, and squared returns per day alone estimate a second moment rather than drift-centred variance. Specify and test the estimator if these optional features are implemented.

The plan and notebooks have not been changed by this review. The original reviewer output follows unchanged.

---

Review complete. Here is the review as Markdown.

# Review of `scratchpad/hyperliquid-ic/rewrite-plan-01.md`

Reviewer: Claude Fable 5.1, read-only. Sources read: rewrite-plan-01.md, plan.md, summary-01.md, ic_research.py, code cells of notebooks 01 to 04, the production strategy `hyper-ai.py` (decision, scoring and sizing functions), and two read-only queries against the frozen `_artifacts/raw-observations.parquet`.

## 1. Verdict

The plan is implementable and its core design (daily as-of grid, next-observed-NAV entry, shared outcome identifiers, exit-time purging with monthly refits, feature-local missingness) is internally sound and respects every non-negotiable requirement. Four small wording contradictions must be resolved before coding, and one data fact the plan does not yet state changes how the sparse period should be counted: the pre-2026 history is a synchronised weekly snapshot of the whole universe, not per-vault irregular sampling.

## 2. Material findings

Severity: **M** = must fix (contradiction or undefined rule an implementer cannot resolve alone), **S** = should fix (accuracy of the reported evidence), **O** = optional refinement.

| # | Sev | Plan section | Concrete failure mode | Minimal correction |
|---|---|---|---|---|
| 1 | M | rewrite-plan-01 "Research data and clocks" item 4 and acceptance check 8, versus "Notebook rewrite order" paragraph "The baseline must reproduce incumbent ... behaviour" | Item 4 requires identical fill conventions and check 8 forbids fills at a carried price, but the incumbent replay is told to reproduce production, and `hyper-ai.py` computes `cagr_score`, `sortino_score`, `inverse_vol` and `return_gate` on engine daily closes that are forward-filled, then fills at those closes. On the weekly period the two rules give different incumbent trades, so the implementer must pick one. | State explicitly: incumbent selection, gate, ranking (missing composite scored 0.0, `pair_id` tie-break), and sizing are computed exactly as production does on engine-style forward-filled daily closes; fills, marks and fees for every arm use the common next-observed-NAV convention. Record the engine's carried-close fill as a parity gap, not a research arm. |
| 2 | M | plan.md "Active rewrite plan" superseding list, versus plan.md Phase 2 ("carried NAV days have zero marked returns"), Phase 3 "EMA clock" ("F37 ... including zero returns on carried days"), and "Missing-data policy" ("at least 24 fresh daily NAV endpoints in the trailing 30 days") | The superseding sentence lists filtering, admission, frequency, missingness and execution gates, but not label construction or the EMA/EWM carried-day rule. rewrite-plan-01 acceptance check 9 and the "Weekly and irregular observation contract" contradict those three legacy passages, and an implementer following plan.md literally would rebuild the zero-return calendar grid the user rejected. | Add to the superseding list: forward-label construction on the calendar grid, EMA/EWM updates on carried days, and the 24-of-30 fresh-endpoint admission rule. One sentence. |
| 3 | M | rewrite-plan-01 "Notebook rewrite order", candidate sizing paragraph, versus plan.md Phase 5 "Use capped equal weights first" | The cascade 30 → 14 → 7-day inverse volatility plus capped equal weights for vaults without any daily risk is undefined inside one basket: the plan does not say how an equal-weight member and an inverse-vol member share the same normalisation. A 7-day volatility estimate is also very noisy and will concentrate weight before the caps bind. | First pass: capped equal weights for all candidate arms (plan.md's own default). Keep the inverse-vol cascade as one labelled variant, and if it is run, give risk-unavailable members the smaller of the cap and the median inverse-vol weight of the available members. |
| 4 | M | rewrite-plan-01 "Research data and clocks" item 4 ("completed daily close", "idealised close-fill") and "Weekly and irregular observation contract" (entry at "first observed NAV at/after the decision") | Since April 2026 the source has roughly 4-hourly fresh marks. "Decision at day T" is ambiguous between 00:00 of T and the close of T, and "at/after" lets the close mark used for features also be the fill. plan.md's NB57 correction records exactly this kind of off-by-one-bar error. Also "separated by at least one calendar day" is ambiguous for intraday marks. | Define `decision_ts` = 00:00 UTC of T+1 (the close of day T). Features use observations with `timestamp <= decision_ts`; entry is the first observation with `timestamp >= decision_ts` (in the dense regime this is the next 4-hourly mark, not the feature mark). Define the two-mark rule as `t2 - t1 >= 24 h`. Drop the separate "idealised close-fill" sentence so there is one entry rule. |
| 5 | S | rewrite-plan-01 "Targets and evaluation" (60 distinct matured training dates; equal-date IC) and "Weekly and irregular observation contract" (dense versus weekly cohorts) | Frozen data fact: from mid-2025 to January 2026 every vault is observed on the same weekly snapshot day (Sep 2025: 4 distinct fresh dates, ~200 vaults each; Jan 2026: 17; Feb 2026 onwards: daily). So Sep 2025 to Jan 2026 contains about 19 distinct cross-sections spread over ~140 calendar dates. Counting "60 distinct matured training dates" or averaging equal-date IC over calendar dates treats each weekly cross-section as seven observations, and the "weekly versus daily cohort" is a calendar-period split, not a vault-type split. | Count warm-up and IC support in distinct outcome cross-sections (unique entry-mark dates), or weight each date by 1/(number of dates sharing the same entry mark). Use bootstrap blocks of at least max(H, 7) + 7 days. Label the sampling-cohort comparison as a period comparison and compare model versus controls within each period. Add the distinct-cross-section count to the saved coverage table. |
| 6 | S | rewrite-plan-01 "Weekly and irregular observation contract", risk-label paragraph | "Leave unobservable daily risk outcomes missing" does not say what enters a daily variance label when up to 20% of days are missing inside an otherwise dense path: a two-day return straddling the gap is neither a daily return nor a zero. | Keep plan.md's `ceil(0.8*H)` fresh-endpoint counts, and compute variance and semivariance only from returns between consecutive observed closes exactly one day apart. Do not include multi-day gap returns and never zero-fill them. |
| 7 | S | rewrite-plan-01 "Weekly and irregular observation contract", growth-label paragraph | On the weekly lattice, exit delays are deterministic: H = 7, 14, 21 give exact holds, H = 90 gives 91 days, but H = 30, 45, 60 become 35, 49 and 63-day holds for the entire pre-2026 period. "Score exact-endpoint results separately" will therefore have zero exact rows at H = 30/45/60 before February 2026. Not an error, but the plan should not expect a within-period exact-versus-delayed comparison there. | State it. Report the actual-holding distribution per horizon and period, and treat the pre-2026 H = 30/45/60 results as delayed-endpoint proxies only. |
| 8 | O | rewrite-plan-01 feature table, BTC exposure row, and "Weekly and irregular" BTC row | Interval OLS on returns of unequal duration is heteroscedastic (variance scales with duration), and BTC is a daily Binance bar while vault marks are intraday. | Regress per-elapsed-day returns (or weight by 1/duration), and align each vault mark to the last completed daily BTC bar at or before it. |
| 9 | O | rewrite-plan-01 EMA row | Elapsed-time decay is specified for the NAV EMA, but EWM return dispersion on interval returns needs squared returns normalised by duration, otherwise a 7-day interval counts as a 7x-variance day. | Use `r^2 / duration_days` as the input to the elapsed-time EWM variance. |
| 10 | O | rewrite-plan-01 "Weekly and irregular", sparse core definition | "Most recent observed log return" means a 4-hour or 1-day return for dense vaults and a 7-day return for weekly vaults, so the same column has period-dependent meaning. | Make the trailing-L interval-sum log growth (with covered duration and interval count) the primary core column; keep last-interval return and its duration as companions. |
| 11 | O | rewrite-plan-01 "Targets and evaluation" ("the existing bounded permutation test") | No permutation test exists in `ic_research.py`; it is specified only in plan.md Phase 4. Not a plan defect, but "existing" misleads. | Reword to "the permutation test specified in plan.md Phase 4" and decide whether the first rerun implements the minimal blockwise version or reports without it. |
| 12 | O | rewrite-plan-01 "Research data and clocks" item 1 and 6 | The frozen artefact contains hindsight repairs (`lag_repaired` 268 rows, `outlier` 60, `clipped` 9). This is a historical-research provenance limitation, not lookahead introduced by the plan. | Add one sensitivity: recompute features and predictions from `raw_share_price` for the affected vaults and report the difference. |

Findings 1 to 4 are contradictions or undefined rules. Findings 5 to 7 change what the saved evidence means. Findings 8 to 12 are refinements and can be deferred without harming the experiment.

Nothing in the plan reintroduces the rejected daily-density rule, the 30/90/360-day admission gates or the ingestion-date filter. No genuine lookahead was found in the plan's construction: features use `timestamp <= decision_ts`, training purges on actual exit time, and the sparse label endpoints are chosen from future observations only on the label side. The remaining causality concerns are provenance limitations (reconstructed series, repair statuses, survivorship) that the plan already discloses.

## 3. Choices to retain

- **Daily as-of grid over raw observations** with `last_observation_ts`, age, interval duration and carried flags kept as columns. This satisfies the daily-prediction requirement without fabricating data.
- **Entry at the next observed NAV, delayed endpoints recorded, `H / actual_holding_days` scaling labelled as a convention** with unscaled returns saved alongside.
- **Shared outcome identifier with duplicate weights summing to one** per training sample. Correct and cheap.
- **Exit-time purge with monthly pooled refits** and warm-up reported rather than the window moved.
- **Feature-local availability rules**: literal L-day columns stay missing, sparse core always present, all-missing columns dropped per fold, rows never dropped.
- **Two valid marks, 14-day recency, $7,500 TVL** as the only admission rule.
- **Capped equal weights when risk is unavailable**, and the 5% cap for under-90-day history.
- **Incumbent replay kept separate from the research panel**, including its 14-day gate exclusions, with access and ranking effects attributed separately.
- **Acceptance checks 3, 8 and 9** (ingestion-timestamp invariance, weekly synthetic vault, single interval return per jump) are exactly the right tests.

## 4. Implementation sequence and acceptance additions

The plan's four-notebook order is right. Only these additions improve it:

1. **Notebook 01**: save an observation table keyed by `(address, timestamp)` with `is_fresh`, and a per-date count of distinct fresh cross-sections. Acceptance: for September 2025 to January 2026 the distinct-cross-section count per month equals the weekly snapshot count (4 to 5, then 17 in January), and `decision_ts` is stored as 00:00 UTC of T+1.
2. **Notebook 02**: build labels before features and save `entry_ts`, `exit_ts`, `entry_delay_days`, `exit_delay_days`, `actual_holding_days`, `outcome_id`. Acceptance: in the weekly period, H = 7/14/21 labels have zero exit delay and H = 30 labels have holding 35 days; every feature row's newest input observation has `timestamp <= decision_ts`; in the dense period `entry_ts > decision_ts` strictly.
3. **Notebook 03**: monthly refits per horizon and target, training rows filtered by `exit_ts <= fit_boundary`, duplicate-outcome weights, and both calendar-date and distinct-cross-section counts saved. Acceptance: weighting is `1 / n_dates_sharing_outcome`, and bootstrap block length is at least max(H, 7) + 7 days.
4. **Notebook 04**: one common fill and marking module used by all arms; incumbent scores computed on engine-style forward-filled closes. Acceptance: on any dense date, the replay's incumbent ranking matches the ordering produced by the `hyper-ai.py` indicator formulas for the same closes; no arm records a fill at a mark older than the decision.

None of this requires new infrastructure, a new feature search or prospective collection.
