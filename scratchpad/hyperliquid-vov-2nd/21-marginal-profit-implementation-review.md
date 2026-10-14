# Experiment 21 — notebook implementation and verdict review

## Review scope

Reviewed on 13 October 2026 with **Claude Opus 5.5**, through Claude CLI 2.1.296, high effort, using the exact model identifier `claude-opus-5-5`. Both responses confirm that canonical model and the first-party provider, with no fallback or permission denials. The independent review completed in 62 turns; a verification and qualification pass completed in 31 turns.

Claude reviewed the executed [NB21 notebook](21-research-marginal-profit-allocation.ipynb) through an export of every Markdown/code cell, textual output and HTML table, plus the reviewed plan, findings, helper modules and result artefacts. The follow-up inspected the builder and relevant inherited strategy/accounting code. It read **22 of the 52 separate chart PNGs**. This was a representative visual review, not another inspection of all charts.

The reviewed authoritative generation is `78a4c63b9f8da28d12576acb1e94338027e9c79e2974552b0371ffeca6820522`. All submitted notebook, code, plan and conclusions fingerprints remain unchanged after this review. No strategy edits, tests or account reruns were performed. Raw prompts/responses, source fingerprints and read-only numerical audits are ignored local artefacts under `_artifacts-restored-2026-10-07/21-opus-review/`.

## Assessed verdict

**The historical economic result stands, but some diagnostics and robustness claims require correction.** No new portfolio-construction challenger beat C00 on the evaluated calendars. F01 is the explicit exception among execution controls: it has a small historical gain of $116 in 2026 and $1,025 over the long calendar. That does not establish a material or statistically significant improvement.

The model ladder, actual comparisons and control replication provide exploratory evidence about these particular fitted policies. They do not establish that the features lack information, that additional positions are intrinsically harmful, or that inverse variance is generally optimal. All registered accounts ran, but several planned robustness and mechanism checks are only partially implemented or missing.

Claude found no decision-path temporal lookahead or inherited accounting defect in the code it inspected. This is a review conclusion with the scope limitations below, not a proof of every framework path.

## Confirmed corrections and checks

| Priority | Finding | Verified evidence | Required action and scope |
| --- | --- | --- | --- |
| 1 | **MARGIN uses stale uncertainty inputs** | Every saved monthly `Calibration_SE` matches the old calendar, rather than the final expanded calendar. January: 0.014539 saved versus 0.016005 recomputed; October: 0.011534 versus 0.012580. `common_calibration_se` consumes matured historical labels across all prediction origins, which are outside the short-only cache comparison. | Rerun **MARGIN** using final predictions, or explicitly freeze and document the calibration sample. Extend cache validation to arm-specific decision inputs. Correct the compatibility statement that realised labels never enter decisions: historical matured labels do enter this uncertainty calculation. |
| 2 | **Worst-update NAV and market intervals do not match the account PnL interval** | The audit compares a one-day NAV change with equity changes from a two-day cycle. ATM gross exposure is $33,065 after 7 April and $3,539 before the 9 April sell: approximately **−89.3% over the cycle**, whereas the displayed NAV interval reports **−79.2% over one day**. | Regenerate attribution using the actual preceding portfolio valuation/decision and matching observation timestamps. Reconcile quantities, transactions, fees and liabilities. This is a report correction, not evidence that account PnL is wrong. |
| 3 | **BTC/ETH returns display as dollar zeros** | The table formatter treats any numeric column containing `usd` as dollars; this catches `BTCUSDT return` and `ETHUSDT return`. Saved HTML shows `$0`/`$-0`. | Format market returns as percentages, then regenerate the reports. |
| 4 | **Claimed carried-NAV sensitivity was not executed** | `Y_mark` is computed and stored, but no fit/report consumes it. The notebook robustness text nevertheless calls it a sensitivity. | Withdraw that claim until the supported-versus-carried outcome sensitivity and reporting-disappearance cohorts are actually analysed. Missing future observations must remain distinct from proven losses. |
| 5 | **Long-period model and pooled phases need separate interpretation** | The first supported 30-day fit is 1 February 2025. Earlier policies use common pooled constants rather than personalised performance forecasts. Substantial equal-split tie dollars are recorded before this switch. | Report pooled and supported phases separately, with executed tie allocations and contributor reliance. Long D03's retained HLP exposure is not isolated evidence for the learned downside model. |
| 6 | **The interval-risk diagnostic changes more than the risk input** | Its fitting filter does not retain `Training_origin`, unlike the main models. Added engine origins therefore enter that diagnostic's training sample. | Match the training sample and penalties before calling it a matched input sensitivity; otherwise label it approximate. |

Relevant locations: [cache validation](marginal_profit_report.py:436), [uncertainty calculation](marginal_profit_allocation.py:436), [table formatting](marginal_profit_report.py:23), [loss interval calculation](marginal_profit_report.py:502), and [stored outcome views](marginal_profit_data.py:236).

### Latent issues with no observed account effect

The missing-P branch freezes an incumbent and assigns zero downside, contrary to the intended treatment of unknown risk. However, the complete authoritative candidate table contains **zero** rows satisfying `Gross_old > 1e-8`, not pinned, and `Downside == 0`. This branch does not explain the saved results; it is a guard to improve before future use.

The notebook finaliser chooses the newest header by file modification time rather than asserting its association with the executed notebook. No generation mismatch was found here; tying finalisation to an explicit run manifest would make later research safer.

The sampled solver bounds cover four D00 decisions, mostly with no positive opportunity. They do not establish optimiser quality for M00/C01 or an active, profitable allocation problem. Their small gaps cannot justify a general claim that numerical optimisation has been exhaustively resolved.

## Qualifications to Claude's initial review

The full initial response and addendum are preserved below. Where they differ, the addendum and these checked qualifications take precedence.

- **Compression is a hypothesis, not a measured calibration slope.** The approximately 0.24 number divides the forecast spread between two C00-defined cohorts by their realised spread. It is not a regression coefficient of realised return on forecast. The suggested regularisation explanation and simplified coefficient shrinkage factors are untested explanations, not established causes.
- **Brier improvement is small but real as a descriptive measurement.** P/D error is 0.2497/0.2481. This is neither proof of useful economic prediction nor evidence that predictive skill is absent. A paired blocked comparison and reliability/resolution analysis are missing.
- **H5 has ambiguous wording.** The plan asks about the importance of incumbent actions; the code tests whether joint management outprofits entry-only. The negative verdict is correct for the latter question. It does not answer the complete magnitude comparison in the plan.
- **F01's arithmetic gain should remain reported.** “Small historical gain” and “no material improvement established” are compatible. A descriptive block win fraction is not a statistical null test.
- **H07 mixes measurement periods and strategy changes.** September investment and whole-run loss do not show that September deployment caused loss. H07 also changes horizon, regularisation, budget and turnover, so it is not a pure breadth experiment.
- **ATM did not hit the 33% account cap.** Its targets were 14.50% of equity on 3 April and 22.45% on 7 April. The latter reached the saved vault capacity ceiling, below the account concentration ceiling. M's conditional magnitude forecasts changed sharply and made the net prediction positive. Whether this was extrapolation beyond training support needs a feature-range/coefficient audit; an unbounded head alone does not prove extrapolation.
- **Pooled allocation is not solely a capacity/address choice.** Proposed equal-split tie dollars total about $127,015 for C01/P00 and $93,935 for D03 in the pooled phase. These are not executed amounts. Capacity/address fallbacks apply when the equal-split feasibility conditions fail; their economic share remains unmeasured.
- **The seven-day budget is unchanged.** An additional read-only audit found exactly equal old/final pre-2026 median seven-day budgets, using 366 reference rows in each. This resolves the addendum's unasserted-budget concern numerically, without a fresh H07 replay.

## Plan coverage still outstanding

The main controls, horizon audit, signal ladder, calendars, smoke accounts, shortlist and registered extensions are implemented. The review identifies the following incomplete parts of the plan:

| Planned check | Status and implication |
| --- | --- |
| Carried-NAV labels and invested-dollar attrition | Missing analysis, despite a robustness claim |
| Half/double support thresholds | Missing sensitivity |
| Whole-fit calendar bootstrap / blocked signal permutation | Missing; limited scatter bands and block signs do not substitute for it |
| Buy-only residual allocation after sell suppression | Buys are reduced for feasibility, but the residual cash is not re-optimised as prescribed |
| Executed tie allocations | Proposed tie dollars are recorded; executed tie contribution is not reported |
| Missing/young cohort funded dollars and PnL | Partial; row fractions are insufficient to establish economic participation |
| Permission-era portfolio outcomes | Missing split; state availability tables alone do not answer it |
| Related-vault failure stresses / long-period grown concentration | Partial; individual/two-largest stresses do not establish related-vault stress, and long D03 concentration needs explicit coverage |
| Independent magnitude penalties / tail-support diagnostics | Shared penalty is disclosed; target-specific selection and detailed tail-support reporting remain incomplete |

## Useful next steps

1. Correct the cache, attribution, formatting and robustness claims before using NB21 to justify another economic search.
2. Diagnose forecast levels and ranking separately: monthly mean forecasts, per-date demeaned relationships, each model's own top-decile outcomes, and supported-tail calibration. Separate penalty strength from magnitude-head structure with a small causal factorial refit.
3. Examine the feature changes behind ATM's 1–3 April magnitude jump and the actual binding constraint. Evaluate age/support-sensitive concentration as a declared comparison, rather than treating a 10–15% cap as an established optimum.
4. A cautious forecast overlay on C00 is an untested lead. Demeaned forecasts and entry/exit hysteresis could be compared while preserving the benchmark's profitable selection. This would assess forecast usefulness, not claim that the overlay already improves profits.
5. Report long pooled and supported regimes, concentration and executed tie decisions before crediting D03's result to its learned model or retention rule.

## Full independent Claude review

The following initial response is retained verbatim for traceability. Its withdrawn or refined statements must be read with the addendum that follows.

# NB21 review: marginal-profit allocation

## Overall verdict

The headline negative result holds: **none of the NB21 challengers beat C00** on either calendar, and the code mostly does what the plan asked. The accounting maths is correct and the controls match NB20 exactly. I found no temporal lookahead in the decision path.

The diagnosis behind that result is weaker than the notebook says. Several saved conclusions mistake implementation artefacts for evidence about features or about portfolio design:

- **The long calendar mostly does not test the models.** The first supported 30-day fit is 2025-02-01. Before that, every vault gets the same pooled forecast, so the greedy solver picks vaults by tie-break, which here means largest capacity. Long D03's result comes from HLP and Liquidator, bought around August 2023 under that uninformed prior and then held.
- **The forecasts are compressed and their level is unstable.** Most of the "100% cash" behaviour follows the monthly change in the overall forecast level, not judgements about individual vaults. So "the features are uninformative" does not follow.
- **Two claims are not backed by any output.** "Carried engine outcomes are a sensitivity" has no code behind it, and the BTC/ETH "market context" columns display as `$0`.

**Reliability:** usable as exploratory evidence that "this learned construction, as configured, did not beat C00". Not reliable as evidence about why, or about the value of the features, breadth, budgets or incumbent management.

## Prioritised findings

| Sev. | Finding | Evidence | Impact | Correction / check |
|---|---|---|---|---|
| **High** | **The long calendar is mostly a cold-start test.** The first supported 30-day fit is 2025-02-01. Before that, all vaults share constant pooled `p/g/ell`, so every buy has the same per-dollar rate. Ties are broken by `-gain`, i.e. the largest feasible amount, so the largest-capacity names win whenever the equal split fails the risk or minimum-ticket test. Long D03 bought HLP and Liquidator at ~32% each around Aug 2023 and held them: HLP made $63,890 of D03's $52,076 total. Long C01/P00 jump to 36 names at the support switch and lose −$23.9k/−$15.8k in 2025Q1. | `budget-registration.json:4` (`long_freeze_date 2025-02-01`); `marginal_profit_allocation.py:186-197`; Long-D03-weights, Long-count and Long-quarters charts; `results.csv:16` | "Highest-profit long challenger D03" is not evidence about the D model or about retention. The long C01/P00 losses are dominated by the switch from pooled to personalised forecasts. | Report long results split at 2025-02-01. Report `Tie_dollars`, which is recorded but never shown. Replace the capacity tie-break with an equal split down to the minimum ticket, or with cash. |
| **High** | **Forecasts are compressed and their level is knife-edge.** At C00's names D forecasts −1.2% against −2.4% elsewhere, but the realised returns are +1.8% against −3.1%: a calibration slope of about 0.24. 30-day reliability slopes exceed 1 in Q2/Q3 (the forecasts are under-confident). On the D/C/M 30-day scatters, nearly all positive forecasts are Q1 points, and the top bin realises worse than the middle bins. In the interval-risk refits, P's share of positive forecasts goes 61% (Feb) → 0.5% (Mar) → 0% (Apr–Sep). D00/C01 flip from 100% cash to about 100% invested on the 1 October refit. | benchmark-cohort table; D-30/P-30 reliability and D/M/C-30 scatter charts; `interval-risk-signal-diagnostic.csv`; 2026-D00/C01 weight charts | "No positive fresh net forecast" in September mostly reflects the monthly forecast level, not vault-level information. That H07, BHALF, BDOUBLE and D04 lose when they invest more is consistent with the top of the forecast ranking being badly calibrated. | Per-date de-meaned (cross-sectional) calibration; decile calibration at the top of each model's own forecast ranking; a monthly plot of the mean forecast. |
| **High** | **The penalty convention plausibly causes the compression.** The logistic head minimises mean log-loss + (α/2)‖β‖². Near p≈0.5 its curvature is 0.25, so α=1 shrinks the probability coefficients to about 0.2× their unpenalised size, versus 0.5× for the ridge magnitude heads with the same α. The 7-day horizon selected α=0.1, the grid boundary. D, P and C also share support-only magnitude heads, so performance information only enters through p. The 0.2 shrinkage factor is suspiciously close to the observed 0.24 slope; that is consistent with the explanation, not proof of it. | `marginal_profit_forecasts.py:36-38`, `:148-155`; training audit (30d α=1, 7d α=0.1) | "Model failure shows uninformative features" is unsupported. | Refit with α ∈ {0.001, 0.01} added to the grid, and compare calibration slope and Brier at the top decile. |
| **High** | **The claimed engine-mark label sensitivity does not exist.** `Y_mark` is computed but never used. The supported labels need an actual mark within one day of the endpoint, so vaults that collapse and stop reporting (ATM's last mark is 2026-04-10) drop out of training, Brier, cohort and exit tables. | `marginal_profit_data.py:231-236`; a search for `Y_mark` finds no reporting use; Cell 0 robustness text; findings line 75 | The robustness text states something that was not done. Tail-loss evidence is survivorship-biased. | Add the `Y_mark` / carried-label table and a "went dark within the horizon" cohort. Reword the claim until then. |
| **High** | **M00's ATM loss is a 33%-cap corner solution.** The M00 weight chart shows roughly 33% of equity in "Other" (by its timing, ATM) just before the −79.2% NAV day. The risk budget uses support-only P downside, so a smooth pre-blowup history looks low-risk. `g_M` has no upper bound. Excluding ATM, M00 still lost about $18k. | worst-update table (−$29,497, NAV −0.792); 2026-M00-weights chart; `marginal_profit_forecasts.py:129-135` | "Dominated by ATM" (about 62% of the loss) is fair, but M is also bad without ATM, and the 33% cap is the economic failure. | Pull M00's ATM candidate rows (`g`, `ell`, `Downside`, `Target_gross`, `risk_90`, age). Test age/support-dependent vault caps. |
| **Med–high** | **The H5 verdict points the wrong way, and MARGIN is mislabelled.** H5 is coded "Not supported" because D03 > D00. But D03 (+$3.6k, no sells), MARGIN (−$0.1k) and D00 (−$3.1k) together show that forecast-driven incumbent reductions lost money. MARGIN's `required()` applies to sells too, so it works as a no-trade band (61.8% cash vs 79.3% for D00), not a more cautious entry rule. D03's lead is one vault: 69 Jump Street, without which its fixed-ledger profit is −$3.3k. | `marginal_profit_report.py:259`; `marginal_profit_allocation.py:140-144, 168`; `results.csv:21` | Conclusions about incumbent management and the margin arm are mis-stated. | Reword H5 as "model-driven reductions cost money in 2026 (one-vault dependent)". Describe MARGIN as an entry-and-exit hysteresis band. |
| **Medium** | **The budget is calibrated on mixed regimes, and the long budget is much tighter.** The 2026 B (0.025) median spans 2024-01 to 2025-12, of which about 13 months used pooled-prior downside and C00 was often 25–55% invested. Personalised d for C00 names is about 0.055–0.077, so B allows only about 35–45% in C00-like names. The long B (0.014) comes from the pooled pre-2025 period and also governs the long calendar's 2026 decisions. | `risk-budget-reference.csv` rows 154–518; `marginal_profit_allocation.py:86-90, 121` | The budget prior is not neutral. It matters less for D (D04 is worse), but the long and short 2026 segments are not comparable. | Report the budget by regime. State that the long arms run under 0.56× the 2026 budget. |
| **Medium** | **The cache reuse does not verify everything.** All 12 2026 challenger accounts come from generation `f8f4aa…`. The `marginal_profit_forecasts.py` hash differs between generations; only forecast outputs and shapes are compared, so `Distribution.terminal` for non-fresh basis is unchecked. MARGIN's SE is computed from realised labels (`Y`, `Resolved`, `Mature_at`) over all prediction origins, including the newly added pre-2026 engine origins, and those fields are excluded from the check. The 7-day budget is not asserted. The trading-strategy and web3 commits are recorded as "unavailable". | `short-cache-compatibility.json`; both `manifest.json:275`; `marginal_profit_report.py:452-487`; `marginal_profit_allocation.py:436-445` | The MARGIN account may be stale; the others are probably fine but unproven. | Recompute `common_calibration_se` per month and compare with the cached `Calibration_SE`. Replay D00 fresh and compare trade signatures. |
| **Medium** | **The worst-update audit does not reconcile.** It uses a one-day NAV interval against equity diffs that may cover two days. D00's −$1,279 at NAV −0.33% would need about $390k of exposure. D04's Hyperrr shows NAV +7.9% next to a −$6.8k loss. The BTC/ETH columns render as `$0` because any column name containing "usd" gets dollar formatting. | `worst-update-audit.csv`; `marginal_profit_report.py:24, 499-507` | The market-context and attribution claims are only verified for ATM. | Use the PnL interval that matches the cycle. Fix the formatter. |
| **Medium** | **A held vault with no P forecast is frozen with zero risk.** In that case `lower=upper=G, d=0`, which overrides operational exits and counts zero downside, contrary to the plan ("not d=0"). The "operational exit" reason is then overwritten. | `marginal_profit_allocation.py:243-247` | Frequency is unknown. | Count candidate rows with `Gross_old>0`, not pinned, and `Downside==0`. |
| **Medium** | **Permission features shift over time.** `permission_unknown` is 1 throughout training before April 2026 and 0 for all of Q3. These SUPPORT features feed every head and the budget, so Q3 predictions extrapolate many standard deviations from a short, time-confounded window. Standard deviations are floored at 1e-8. | panel audit (Q1 1.0 → Q3 0); `marginal_profit_forecasts.py:29` | Possibly contributes to the 2026 level drift; unproven. | Report the coefficient and standardised value per fit; refit without the permission features. |
| **Medium** | **The sensitivity suite runs on an inactive base.** D00 is about 80% cash, so D02 = D00 exactly, GATE14 ≈ D00, and BHALF/BDOUBLE mostly test small exposure. H07 changes horizon, α (0.1 vs 1), budget and turnover (897 trades, $7.9k fees) all at once. | `results.csv`; 2026-count chart | "Six slots not binding" holds only for an arm that rarely held more than three names. H07 is not a breadth test. | Present them as such; run future sensitivities on an active base. |
| **Low** | **Solver-bound evidence is thin.** It covers four D00 dates, three of which have no positive action; only 2026-04-01 is informative. The tangent envelope is only an upper bound where the gain function is concave. | `solver-bounds.csv`; `marginal_profit_allocation.py:458-485` | "Lower priority" is right, but because the forecasts are the bottleneck, not because solver gaps were shown to be negligible. | Reword. |
| **Low** | **Two-day penalty selection says "unsupported prior folds" in every 2026 month** despite more than 5,000 rows. | training audit table | Diagnostic only; possibly a fold-construction bug. | Debug `select_penalty` for h=2. |

## Plan coverage

| Requirement | Status |
|---|---|
| Control parity, fees, liabilities, holding spells, horizon rule | Implemented |
| T−1 features, matured monthly fits, purged penalty, archive-end censoring | Implemented (two-day folds anomalous) |
| Engine-mark label sensitivity; attrition by invested dollars | **Missing** (claimed in the text) |
| Pooled cold start, support contract | Implemented; half/double support sensitivity **missing** |
| P/D/M/C ladder, physical loss bound, exact fee path values | Implemented; formulas check out |
| Magnitude-head penalty selection, unsupported-tail reporting | Partial (shared α, disclosed; no tail report) |
| Calendar-block bootstrap, blocked permutation | **Missing** (scatter bands only, and suppressed at 30 days) |
| Greedy dollar/risk candidates, refinement, equal-dollar ties | Implemented; tie dollars **not reported**; capacity tie-break undisclosed |
| Buy-only residual pass after sell suppression | **Missing** (buys are only scaled down) |
| Ten smoke arms, shortlist, five extensions, F01 long | Implemented |
| H6: allocated dollars and PnL by missing/young cohort | Partial (candidate-row fractions only) |
| Capacity/bankroll shadows | Implemented (September only; all 1.0, so uninformative) |
| Pre/post permission-era result split | **Missing** |
| Largest and related-vault failure stresses | Largest only; related-vault **missing**; long D03 57% not stressed |
| BTC/ETH and curator context | Partial (BTC/ETH returns display as $0) |
| Joint CVaR, pairwise switch, hazard model | Not applicable (deferred by the plan) |

## Which conclusions survive

- **Survive:** C00 remains the benchmark. No challenger approached it: C01 trails by $49,753, and every new construction trails on the long calendar. F01's effect is tiny. D02 = D00. H07 gets more breadth without profit.
- **Reword:**
  - **H1 verdict "Historical gain".** Replace with "No material effect". F01's +$116 has a 7-day block win rate of 0.375.
  - **H2 verdict "Probability gain".** Replace with "Negligible skill". The Brier skill score against a 0.25 base is under 1%.
  - **H5.** Say that model-driven reductions cost money in 2026, and that this depends on one vault.
  - **Strongest challenger C01.** All of its profit is Q1 (+$14.2k), and $10.8k of it is MC Recovery Fund. After February it is a cash account.
  - **Long D03.** This is a pooled-prior selection of HLP that was then held; it says nothing about the D model.
  - **H07.** Its losses fall in Q1/Q2 (−$9.4k/−$20.7k). In Q3, when it was fully invested, it gained $5.4k. The "fills September cash yet loses money" framing gets the timing wrong.
  - **"Better forecasts needed".** Narrow this to calibration of the forecast level and of the top of the ranking, not feature value.
- **Withdraw until done:** "carried engine outcomes are a sensitivity", and the BTC/ETH context claims.

## Highest-impact follow-ups for profit

1. **Use the forecasts as an overlay on C00, not a replacement.** Keep C00's selection and sizing; use cross-sectionally de-meaned D/M forecasts only to veto entries or trim, with a hysteresis band. C00 is the profit engine, and the evidence above suggests these forecasts are more useful as filters than as allocators.
2. **Fix the calibration slope:** a wider α grid, per-date de-meaning to separate the market level from vault ranking, and a calibration check on each model's top decile. Re-run C01 and D00 afterwards.
3. **Add a tail guard.** Cap single vaults by age, support or TVL (for example 10–15%). Re-run C00 and M00 to measure the ATM-type exposure.
4. **Add the engine-mark / went-dark label sensitivity** before trusting any loss model.
5. **Re-run the long calendar** reporting the cold-start and supported regimes separately, with ties resolved by equal split or cash.

## Inspected material and limitations

- **Files:** the full export; the plan; the findings; all six `marginal_profit_*.py` files (data, forecasts, allocation, report, checks); `compiled-marginal-callback.py`; `AlphaModel.calculate_target_positions` and `get_indicator_value` in trade-executor; `results.csv`; both manifests; `short-cache-compatibility.json`; `budget-registration.json`; `registration.json`; `long-shortlist.json`; `risk-budget-reference.csv` (partial); `worst-update-audit.csv`; `interval-risk-signal-diagnostic.csv`; `solver-bounds.csv`; a search of `summary.md`.
- **Charts (22):**
  - 2026 calendar: equity, quarters, sensitivity-equity, count, weights for B00, C01, D00, D03, M00 and H07; reliability for D-30, P-30 and D-7; scatters for D-30, M-30 and C-30.
  - Long calendar: equity, quarters, count, weights for D03, P00 and C01.
- **Charts not inspected:** all drawdown charts (both calendars, including sensitivity drawdown); the 2-day signal charts and the remaining 7-day ones; the other weight charts.
- **Not read:** the builder `create_marginal_profit_notebook.py`, the NB20/NB18 helpers (`clean_c00_v11_comparison`, `capital_allocation_report`), the trading-strategy source, and the full `hyper-ai-v11.py` (only its compiled callback). So inherited accounting is taken on parity evidence, not inspected.
- **Parquet tables could not be read** (candidates, decisions, predictions). The ATM position size, frozen-holding frequency, tie dollars, MARGIN SE staleness and the shrinkage explanation therefore remain hypotheses. Each has a specific check in the table above.

## Claude verification and qualification addendum

# Addendum to the NB21 review: verification against the builder, helpers, inherited accounting and new evidence

## Bottom line

The main economic verdict holds, narrowed as follows. **No new-construction challenger beat C00 on either calendar.** That covers P00, D00, M00, C01, D02, D03, D04, the five registered sensitivities and the long shortlist. The one exception is F01, a C00 execution variant, which is ahead by a small amount (USD 116 in 2026 and USD 1,025 long).

The gaps are much larger than anything the defects below could close. C01 trails by about USD 49.8k in 2026. Long D03 makes 8.62% CAGR against C00's 33.13%. The confirmed defects affect one sensitivity arm (MARGIN, −USD 0.1k), reporting, and diagnostic interpretation, not the controls or the main accounts.

Several of my original diagnostic statements were overstated and are withdrawn or refined below. Three matter most:
- **The "0.24 calibration slope" was a spread ratio.** It is not a fitted slope.
- **The M00/ATM loss was not a 33% account-cap corner.** Capacity was limited at the vault level.
- **The frozen zero-risk branch never fired.**

I found no inherited accounting defect.

## Confirmed issues

| Sev. | Issue | Evidence | Consequence |
|---|---|---|---|
| **Medium (confirmed, was "may be stale")** | **MARGIN ran on a stale calibration SE.** `common_calibration_se` uses `Y`, `Resolved` and `Mature_at` from *all* prediction origins (`marginal_profit_allocation.py:441-444`). The cache-reuse check drops exactly those columns (`marginal_profit_report.py:469`). It also states "realised labels never enter account decisions" (`:487`), which is false for MARGIN. | `margin-cache-audit.csv`: in all 10 months the recorded SE equals the old value and not the final one. January 0.014539 vs 0.016005; October 0.011534 vs 0.012580, about 9–10% low. The date count roughly doubled (116→233 in January), from the added engine origins. | The MARGIN −USD 0.1k account and the "hysteresis band" comparison are not from the final generation. The direction of the PnL effect is unknown, because a wider band means fewer trades both ways. The compatibility note's statement is wrong. |
| **Medium (strengthened)** | **The worst-update audit does not reconcile.** It compares a one-day NAV interval (`marginal_profit_report.py:502-505`) against a daily-resampled equity diff (`:499`) on a 2-day decision cycle. | ATM: the 7 April executed holding of USD 33,065 is USD 3,539 at the 9 April decision. That is a −89.3% move over the cycle, against the audit's −79.2% over one day. The vault loss of USD 29,497 matches the two-day move. | NAV_return understates the cycle move, so the audit's attribution claims are unreliable. Rerunning the report is enough; no account rerun is needed. |
| **Medium (confirmed)** | **BTC/ETH context columns render as dollar zeros.** The column names `BTCUSDT return` and `ETHUSDT return` contain "usd", so `table()` formats them as `${:,.0f}` (`marginal_profit_report.py:24`). | `rendered-market-context.txt`: every row shows `$0` or `$-0`. | The market-context claims in the robustness text are not visible in the output. This is a formatter fix. |
| **Medium (unchanged)** | **The "carried engine outcomes are a sensitivity" claim has no code behind it.** `Y_mark` is built (`marginal_profit_data.py:235-236`), carried into predictions (`marginal_profit_forecasts.py:184`) and never used. | A search finds no consumer. The robustness text claims it (`marginal_profit_report.py:280`). | Withdraw the claim until the sensitivity is run. Tail evidence remains survivorship-exposed. |
| **Low (new)** | **The interval-risk diagnostic is not matched to the main fits.** It trains without the `Training_origin` filter (`marginal_profit_report.py:425`); the main fits use it (`marginal_profit_forecasts.py:173`). | Its training set includes the added engine origins. | Its "matched signal-only sensitivity" label is slightly overstated. Use it as an approximate diagnostic only. |
| **Low (new)** | **`finalise()` can pick the wrong artefact folder.** It selects the newest `final-header.md` by modification time (`create_marginal_profit_notebook.py:61`) and does not check that it matches the executed notebook's generation. | Code inspection. | The header text could come from the wrong generation. This is a provenance risk, not an observed error. |
| **Low (downgraded from Medium)** | **The missing-P branch (`lower=upper=G, d=0`) is a latent design bug.** It is at `marginal_profit_allocation.py:245` and contradicts the plan's "not d=0". | `frozen-zero-risk-holdings.csv` finds zero authoritative rows with `Gross_old>1e-8`, not pinned, and `Downside==0`. | It did not affect any result. Fix it before future use, but stop listing it as a possible explanation. |

## Withdrawn or refined statements

**1. Compression and the "0.24 slope" (my High findings 2 and 3).**
- **Withdrawn: "calibration slope of about 0.24".** The cohort table gives the forecast spread between C00-selected and other names (−1.2% vs −2.4%, so 1.2 pp) divided by the realised spread (+1.8% vs −3.1%, so 4.9 pp). That ratio is about 0.24. In the usual orientation, realised regressed on forecast, the two-point "slope" would be about 4.1. Neither number is a fitted calibration slope. These are two equal-date-weighted means over overlapping 30-day labels. The cohorts were also formed by C00's selection, which is a different ranking from D's own forecasts.
- **Refined:** the evidence is consistent with D's net forecasts being under-dispersed relative to realised outcomes in 2026. It does not measure how much.
- **Withdrawn: "the 0.2 shrinkage is suspiciously close to 0.24".** The 0.2× (logistic) and 0.5× (ridge) factors assume orthogonal, unit-variance features, p≈0.5 and unit mean weights. In fact the features are correlated, the mask columns are unstandardised 0/1 indicators (`marginal_profit_forecasts.py:30`), and shrinkage differs by direction. Shrinkage of the probability coefficients also does not map one-to-one onto the spread of the net forecast.
- **Alternative explanations I did not weigh before:**
  - **Model structure.** D varies only through p; its magnitudes come from the support-only P heads (`marginal_profit_forecasts.py:129-130`). That makes D's net spread structurally narrow, roughly −(g + loss) times the spread in p.
  - **Monthly level drift.**
  - **Equal-date weighting.**
  - **Genuinely weak features.**
- **Evidence against the penalty explanation at 30 days.** The registered fold selection preferred α=1 over α=0.1 at that horizon. This is weak evidence: three 30-day windows with overlapping labels. Even so, the penalty is one hypothesis among several, and no regression or causal attribution has been run.

**2. H2 and Brier.** The Brier scores are P 0.2497 and D 0.2481, a 0.0016 reduction (0.64% relative to P). "Probability gain" is a true description of that lower error. My proposed "Negligible skill" turned a small observed difference into a verdict that skill is absent. My "skill score against 0.25" also used the wrong reference; the comparison is against P. Suggested wording: *"Small descriptive reduction in probability error versus P (0.2497→0.2481). There is no paired or block uncertainty and no Brier decomposition, and the economic value is not shown."*

**3. H5 direction.** **Withdrawn: "points the wrong way".** The plan's wording ("acting on incumbents matters as much as admission of extra vaults") is a claim about magnitude. The code tests a signed claim: does joint management (D00) earn more than entry-only (D03)? (`marginal_profit_report.py:259`). Under the signed reading, "Not supported" is correct, since D03 is about USD 6.7k ahead of D00. The mapping from plan to code is ambiguous rather than reversed, and the "as much as admission" comparison is not tested at all, because there is no admission contrast. Two caveats remain:
- D03 also changes the cash path, because it has no sell proceeds to fund buys. It is not a clean switch of incumbent actions alone.
- D03's lead depends on one vault, 69 Jump Street.

The MARGIN point stays: `required()` applies to sells and replacements as well as buys (`marginal_profit_allocation.py:140-144,168,181`), so it works as an entry-and-exit hysteresis band. Its numbers are now also known to be stale.

**4. F01 (H1).** **Withdrawn: rewriting "Historical gain" as "No material effect".** Both are compatible descriptions: the arithmetic gain is real but small (USD 116 in 2026, about 0.2% of C00's profit; USD 1,025 long). The 0.375 seven-day block win rate is descriptive and is not a statistical null. Suggested wording: *"Small historical gain"*.

**5. "None beat C00".** Narrowed to new-construction challengers, as in the bottom line, with F01 as the explicit exception.

**6. H07.** The notebook places September investment (`September cash`) next to the whole-period loss (`marginal_profit_report.py:268`). My quarter split (−9.4k in Q1, −20.7k in Q2, +5.4k in Q3) shows the loss and the deployment fall in different periods. Neither the notebook's framing nor my split shows that September or marginal cash deployment caused, or prevented, the loss. H07 also changes horizon, α, budget and turnover at the same time.

**7. Long-calendar tie-break (High finding 1).**
- **Stands:** before 2025-02-01, unsupported snapshots give every vault identical constants (`marginal_profit_forecasts.py:126-128`). Fresh-buy rates therefore tie exactly, so pooled-phase selection carries no vault-specific forecast information.
- **Refined:** this does not mean all pooled dollars went to address or capacity choices. `long-tie-dollars.csv` records pooled-phase equal-split tie dollars of USD 127,014.73 for C01 and P00, and USD 93,935.39 for D03. These are cumulative *proposed* amounts before minimum-weight, ticket and funding adjustments, not executed amounts. Their share of total buys is unknown.
- **Where the fallback applies:** the `(−rate, −gain, address)` ordering, which favours the largest feasible ticket, applies only when the equal split fails its ticket, slot, risk or objective test (`:189-197`).
- **D03 specifically:** its two roughly 32% holdings (HLP, Liquidator) could come from an equal split or from both hitting the 0.33·E account cap. I have not distinguished these.
- **Side note:** C01 and P00 have identical pooled-phase tie dollars and breadth. That is expected, because their forecasts are identical before support.

**8. M00 and ATM (High finding 5).** **Withdrawn: "33%-cap corner solution" and "roughly 33% of Other is ATM".** From the exact-vault rows (pair 268714989; I ignored the second, broader "AI ATM" match):
- **3 April:** first entry, target USD 21,267.39, which is 14.50% of equity (E = USD 146,671.50). The capacity limit was USD 21,808.57, so this target was below every cap. The binding constraint (risk budget, cash or greedy step size) is not identifiable from these rows.
- **7 April:** target USD 33,065.36, exactly the saved vault capacity limit (`Cap = min(TVL/size-model cap, G + deposit headroom)`, `marginal_profit_allocation.py:235-236`). That is 22.45% of equity, below the 0.33·E account cap of about USD 48.6k. The top-up followed rising vault capacity.
- **The risk charge was ordinary.** The common P `Downside` was 0.0676, inside the range of 0.055–0.077 I quoted for C00 names. So **"smooth history looked low-risk" is withdrawn**.
- **What drove the entry was M's own magnitudes.** Within the same April fit, between 1 and 3 April, g_M rose from 0.067 to 0.148, ell_M fell from 0.126 to 0.053, and the net forecast went from −1.7% to +4.8%. That is a feature-driven jump. The loss probability p was about 0.45 and the vault had a missing C00 score.
- **Conclusion:** unbounded magnitude extrapolation plus capacity-bound sizing explain the exposure. The account cap does not. The rest of "Other" is not established to be ATM.

**9. Inventory correction.** There are five `marginal_profit_*` helpers plus the builder, not six.

## Inherited accounting: no defect found

I checked the following and found them consistent:
- **Engine marks.** Positions are marked at gross × (1 − 0.001 − 0.10 × max(gross − basis, 0)/gross) (`hyper-ai-v11.py:887-920`). The remaining basis falls pro rata on sells (`:832-864`).
- **NB21's fee model matches.** `Distribution.terminal` uses the same 10% and 0.1% constants and the same basis convention (`marginal_profit_forecasts.py:89-92`, `marginal_profit_allocation.py:34,48`). Selling now uses the post-refresh net/gross ratio; the refresh runs at compiled line 40 and select at line 151.
- **The partial-sell fee correction** is identical in all arms (`clean_c00_v11_comparison.py:71-76`, `marginal_profit_allocation.py:345-349`).
- **The realised-net formula in the signal report** matches the forecast's net definition (`marginal_profit_report.py:77`).

Three minor latent points, none affecting results:
- `reference_equity` is read before the redemption revaluation (compiled line 34). This is inherited from source and only affects ticket and reserve thresholds.
- `entry_marking` overwrites the shared pair's `sell_tax` with 0.001 on first buys (`protected_core_score_allocation.py:293-306`). It does so the same way in every arm, and parity passes.
- `fee_accounting` hard-codes 0.1 and 0.001 (`capital_allocation_report.py:95`) instead of reading the parameters. The values match the current parameters.

## What needs rerunning

1. **The MARGIN 2026 account, with the SE recomputed from final predictions.** This is the only account rerun required. Also correct the compatibility note, or make the cache check include label columns for any arm that uses them.
2. **Report-only fixes:** the worst-update audit with cycle-matched intervals, the BTC/ETH formatter, and dropping or implementing the `Y_mark` claim.
3. **Signal diagnostics, with no account reruns:**
   - Realised regressed on forecast, de-meaned per date, with block-bootstrap intervals.
   - A paired, blocked P-vs-D Brier comparison with a reliability/resolution decomposition.
   - The monthly mean forecast.
   - Factorial refits that cross penalty (α ∈ {0.001, 0.01, 0.1, 1}) with magnitude source (P vs M heads for D), to separate the penalty from model structure.
4. **Long-calendar reporting:** split pooled vs supported phases, and report executed (not proposed) tie dollars as a share of buys.
5. **M00 on 3 April:** extract Risk vs B and cash from the decisions parquet to identify the binding constraint, and attribute the features behind the g_M/ell_M jump between 1 and 3 April.
6. **H5:** if the plan's wording is kept, add an admission-only contrast. Otherwise relabel it as the signed incumbent-management test.

The controls and the other eleven 2026 challengers do not need rerunning on the evidence so far. Their forecasts and shapes were checked as identical, and the 30-day budget was asserted equal. The 7-day budget and the H07 account are still unasserted, which is low risk.

## Material read in this pass, and remaining limits

**Read:** `create_marginal_profit_notebook.py`, and all of `marginal_profit_allocation.py`, `marginal_profit_forecasts.py`, `marginal_profit_data.py` and `marginal_profit_report.py`. Also `clean_c00_v11_comparison.py`, `protected_core_score_allocation.py`, `capital_allocation_report.py:79-101`, `hyper-ai-v11.py:784-930,1349-1357`, the order of the refresh and select calls in the compiled callback, the findings file, and the seven evidence files.

**Not read:**
- `marginal_profit_checks.py`, which I covered originally.
- `capital_allocation.py`, `profitable_allocation.py` (`observed_quote`, `analyse_run`) and `waterfall_comparison.py` (`cap_to_final_sell_proceeds`). These are taken on exact control-parity evidence.
- The decisions and predictions Parquets, which I could not read directly.

So the binding constraint on 3 April, executed tie dollars, D03's split-versus-cap mechanism and every proposed calibration diagnostic are still open. Nothing was edited or rerun.
