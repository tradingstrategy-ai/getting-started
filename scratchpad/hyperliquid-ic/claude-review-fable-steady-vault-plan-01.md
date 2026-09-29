# Fable review of the steady-vault plan

Requested command: `claude -p --model fable`; completed successfully. Session metadata reports `claude-fable-5-1`. Review context and pre-review draft are retained under `_review/`.

## Applied changes and judgement

- Applied the useful controls, metric definitions and notebook dependency clarifications listed in the plan's review disposition.
- Verified the held-mark issue in `stable_profit.py`: marks come from eligible feature rows. The plan now requires a separate held-NAV ledger and a versioned A0b-v2 baseline for every new arm. The original A0b remains the parity control.
- Did not accept forced redemption at an assumed immediately executable NAV; exits must respect the declared execution model and data availability.
- Added full-panel comparisons early, but did not require beating a comparator or a sign-consistency adoption gate before running the other fixed experiments.
- The Hyper-ai dates are pre-discovery for this manual example exercise but are already heavily used in prior research. They are not a clean holdout. Added pre-discovery segmentation without moving the primary goalpost.
- Short-window dense volatility now has an explicit fallback. Unknown correlations retain bounded provisional treatment with a singleton sensitivity, rather than treating missing dependence as known independence.
- Fee schedules need verified metadata: the cleaned observation table is not guaranteed to contain them. Preserve old accounting for parity, then version the common corrected accounting and its fee sensitivities.
- Rejected the arbitrary written-at <= date+1 cutoff for reconstructed historical marks. Audit repair causality and distinguish retrospective backfill from actual historical publication availability.
- Reviewer-specific numerical counts below are reviewer claims, not independently re-established by this plan-writing task. They motivate audits; the implementation must reproduce them before presenting them as findings.

## Original review

Review complete. Below are the findings ordered by severity, then suggestions, then the verdict. I verified the simulator assumptions against the code and the current CSVs rather than the summaries.

## Correctness findings

1. **High. Survivorship check arrives too late.** The allowlist is a 2026-09-09 snapshot filtered on current TVL. Of the 194 panel addresses it excludes, 121 ended below the TVL floor and 46 stopped reporting a month before period end, and their median full-history return is worse than the included set. The same incumbent rule moves from 4.9% CAGR and -15.6% drawdown on the full panel to 15.9% and -8.6% on the allowlist. A return floor plus shallow-drawdown screen is exactly what a survivor list flatters, because vaults that looked steady and then died never reach the screen. The plan only checks this for finalists in NB16. Smallest fix: run NB11's three P arms on both the full panel and the allowlist, and carry a parent forward only if its direction holds on both. NB12 to NB15 can stay on the allowlist.

2. **High. Held vaults that lose eligibility are frozen at their last mark.** In `simulate_stable_policy` holdings are marked only from the panel NAV of eligible rows. A held vault whose TVL dips under 7,500 or whose NAV age exceeds 14 days becomes a stale holding: it leaves the budget, is never sold, and is never re-marked even though its raw observations continue. A0b already averages 0.95 such positions over the full window. A 20-name book with 5% young slots near the TVL floor will hit this far more often, and the frozen value counts in equity and Sharpe. The plan's line about redemption-blocked holders endorses this artefact as a real constraint. Fix: in the new selection path, mark every held vault from its latest raw observation and treat loss of eligibility as a forced redemption at that mark. Report frozen-value share of equity per date. Leave the A0b path untouched for parity.

3. **Medium. The discovery window sits inside the full period.** Thresholds were chosen looking at 16 July to 12 September 2026, which the full backfilled window contains. The hyper-ai window ends 8 July and is clean. Fix: NB16 reports a pre-discovery sub-window, 2025-09-13 to 2026-07-15, and the 18% feasibility check on the full period uses that sub-window. The planned monthly segments make this cheap.

4. **Medium. D2 and G2 impose history barriers the plan forbids.** The dense 60-day volatility feature needs 48 observed daily returns, so under D2 every vault younger than about 48 days is provisional regardless of evidence. G2 needs eight paired weeks and the plan keeps unknown-dependence names at provisional caps, so a vault that is fully evidenced under E0 at 30 days is still capped at 5% in G2 until day 56. Fix: D2 uses the shortest available dense window with 80% coverage, 14, 30 or 60 days, disclosed per row, matching P1's own fallback. G2 treats ungroupable names as singleton groups with the ordinary individual cap and reports how many were ungroupable.

5. **Medium. The NB32 summary in the plan is wrong in a direction that matters.** NB32's own heading says stability rankers performed poorly, but the 15% return floor with the incumbent ranker beat the anchor on CAGR and Sharpe. The NB33 lead rerun in the leads artefacts has floor15 as the best full-period lead on date-matched cycles, though worse than the anchor in the hyper-ai window. That is P1's closest sibling. Fix: reword the starting evidence to "the floor helped, ranking by stability instead of return hurt, and part of the stability rankers' low volatility was cash". Add floor15 as a reference row in NB16 with the engine and period caveat already recorded in the leads manifest.

6. **Medium. Fee schedule is blanket rather than per vault.** The simulator charges 10% of realised profit on every vault plus 10 bp of redeemed capital. The frozen raw observations carry per-vault performance fees: 594 vaults at 10%, 8 at zero. The 10 bp has no documented basis per the NB32 Codex review. Fix: read the per-vault fee from the raw observations, set the capital fee to zero, rerun A0b once under the corrected schedule so every arm shares it, and keep the old A0b outputs as the parity record. Use the same per-vault fee in the 15% net-growth qualification.

7. **Low to medium. Primary metric and floor window are undeclared.** Sharpe depends on the clock: A0b is 0.92 daily and 1.05 on two-day dates over the full window, and carried marks zero out daily returns, which flatters arms that hold sparse names. Sharpe with zero cash yield is also indifferent to cash, so the CAGR floor is the only thing stopping a cash-heavy winner. Fix: declare weekly Sharpe as the ranking metric with daily secondary, apply the floor as feasible-first then rank, and state that the floor is tested on the pre-discovery full window and reported for the hyper-ai window.

8. **Low. The simulator has no selection hook.** The incumbent gate and score are hardwired, and the accepted-dollar-cap argument cannot reach names outside the incumbent top-N. Fix: add one `target_weights_by_date` argument defaulting to None so the A0b path stays byte-identical. The planned no-op parity test is the right check.

9. **Low. No manager identity in the frozen data.** Raw observations have names and slugs but no leader address. G1 would rest on a name-prefix heuristic. Fix: state the heuristic, or check whether the vault-universe download read by the StratWise study script carries a leader field and freeze it.

10. **Low. Repaired-mark causality is reported but not tested.** About 98% of observation rows differ from the raw share price under the approximated-PnL status, and 328 rows are lag-repaired or deferred outliers. Fix: in NB10 compare the written-at timestamp with the mark timestamp for repaired rows and confirm no feature at date d uses a mark written after d+1. Document the count if any.

**Observation, not a defect.** Sparse marks are an early-period provider regime, not a vault type. On 2026-01-01 all 111 allowlist names carried NAV older than a day, and from April 2026 no name has an interval over two days. So the cadence-stratified concentration test has one bucket per date, and P2 can stratify by period rather than per vault. The live question is young vaults: 60 of 167 allowlist names were under 90 days old on 2026-04-01. The E arms matter more than the weekly arms.

## Suggestions

- **Most useful missing comparison: a sizing-only control.** Run A0b's own gate and incumbent ranking under the NB11 sizing contract, equal weight, 20% cap, TVL cap, cash residual. A0b's effective pool is the 360-day cohort, 20 of 111 names in January and 70 of 178 in September, while the P arms draw from every eligible name. The A0-cap diagnostic already lifted Sharpe from 0.34 to 1.17 by sizing alone at the cost of 45% cash. Without this rung a P1 gain cannot be split between breadth, the floor, and the sizing. It is two lines in the arm loop.
- **Report D1 pass rates by age bucket.** A five-day-old vault passes a 3% drawdown screen trivially. The age-matched control the plan reserves for D3 applies to D1 as well.
- **Count TVL-cap binding and frozen-holding share per date.** NB32 found the TVL cap strongly protective, and small young vaults will bind it constantly. This is where the 20% CAGR feasibility will be decided.

## Verdict

Proceed after amending items 1 to 6 in the plan text. Items 7 to 10 can be settled inside NB10 as long as the decisions are written down before NB11 runs. None of the fixes needs a new model, a grid, an approval gate or a history requirement. The objective matches the user's intent: Sharpe first, 18% floor, no bonus for extra return, young vaults admissible through the provisional sleeve. The main threat to the objective is cash drag under non-redistributed caps, which the plan already measures. A0b remains an independent simulator with documented gaps to the engine, and the discovery examples stay descriptive.
