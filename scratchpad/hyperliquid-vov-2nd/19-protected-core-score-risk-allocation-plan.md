# Experiment 19 — score and risk sizing around the C00 core

Status: implemented and executed, 12 October 2026. See the [notebook](19-backtest-protected-core-score-risk-allocation.ipynb) and [findings](19-protected-core-score-risk-allocation-findings.md). Two Claude CLI calls used confirmed `claude-fable-5-1` with independent read-only folder/source inspection. The final review was conditional; its material corrections are incorporated below. Implemented notebook: `19-backtest-protected-core-score-risk-allocation.ipynb`.

## Goal and research question

Test whether more than six positions can increase net profits while controlling weaker additional positions through their dollar weights. Preserve the C00 core policy, including its selection algorithm, entry/exit ranks and waterfall allocation. Add an allocation that responds to both performance strength and risk, using only cash the core can spare. Success means a better economic trade-off against C00, not a higher invested percentage.

The notebook heading must contain this goal, the hypotheses, formulas and registered matrix, the reporting periods, and a completed verdict after execution. Explain that C00 is the corrected-fee C-W research strategy, not deployed hyper-ai-v11.

## Earlier attempts and what this experiment adds

| Earlier work | What was tried | Result or limitation | Consequence for NB19 |
| --- | --- | --- | --- |
| NB01–03 | Source inverse variance, accepted-dollar caps, equal/flattened weights, regularisation and correlation-aware budgets at six slots | Flatter weights repaired some cap interactions but did not beat redistributed source sizing. Tiny requests and cleanup floors explained much lost deployment. | Keep source core intact; explicitly measure score attenuation lost to trade/position floors. |
| NB04 | Score matrix, 4/6/10 positions, equal/score/inverse-variance sizing | No consistently superior replacement across both periods. | Do not claim that score weighting above six slots is new. |
| NB06–07 | 74 two/three/four-input recipes at 6/7/8/10 slots | Focal 2026 CAGR fell 51.77%→30.85%→16.24%→−3.01%. At ten, shared-vault PnL changes explained $58,491 of $59,004 deterioration. Other supports sometimes improved at seven. Entry/exit ranks also changed. | Isolate additional allocation from core incumbent/entry machinery; do not attribute every loss to extra names. |
| NB08–09 | Score and feature forecasts, K-ratio, sparse-data revisions | Risk prediction was stronger than mean-return prediction; absolute return admission thresholds were not established. | Score is a monotone preference, not expected profit or a calibrated probability. No new feature/model search in NB19. |
| Original and expanded NB10 | Fixed-unit portfolios; risk, score, composite inverse-variance/K weighting; six versus ten | T20/T14 ten-versus-six mean 30-day return −0.873 pp. Score/risk mixtures were tested but without repeated engine execution. | Replay a small, defined construction matrix; retain requested/accepted/executed weight distinctions. |
| NB11–14 | Risk windows/exponents, sparse estimators, regularisation and cap-aware allocations | Snapshot gains sometimes reversed in the engine; original regularised90 remains a useful reference. | Freeze risk estimator and window; avoid another broad risk grid. |
| NB15–16 | Six-position A/C/G/v11 and matched waterfall allocation | C-W became a strong historical challenger, but small selected vaults still left substantial September cash. | Exact C-W with corrected fees is the primary C00 control. Its core is a risk-priority waterfall, not proportional inverse variance. |
| NB17 | 8/10-slot overflow, scored-only/fee-aware overflow, capacity selection, joint optimiser and ten-name core | Corrected four-slot overflow improved long CAGR to 37.73% versus 33.13%, but lost in 2026. Missing-score exclusion hurt long results; contributor dependence was large. | Preserve unknown/young histories; try weights rather than assuming a score veto improves returns. |
| NB18 | Admission-aware six-name core plus up to six extras; inverse volatility, risk budgets, forecast gates/exits and gradual sizing | The core already lost $4,104 in 2026 against C00. Risk-only extras lost against that core; no forecast arm bought fresh extras in 2026. Gradual sizing never gave intermediate fresh allocations. | Use C00, not C01; prove active score-sensitive dollars before interpreting results. Avoid adding another forecast gate that disables the experiment. |
| Older vault folders | Calmar, Bayesian confidence, softmax, separate gate/sizing signals, 20–30-slot books, clusters and capacity recycling | Different archive/accounting/Sharpe conventions; archived headline results are not matched C00 comparisons. | Reuse relevant mechanisms only after checking actual source. Do not transplant historical winners or blacklists. |

Claude's independent inspection adds two leads, with qualifications. NB17's M01 ledger shows positive residual capacity on roughly 30/139 fresh-2026 decisions in three June–October windows; this is not an exact C00 opportunity count and must be recalculated from C00. Our direct check of the final NB18 C00 target ledger finds 37/139 dates with positive target-budget residual, including 7 May, the June windows and August–October; several July/August residuals are only $104–$415. These are target residuals, not proof of executable cash or enough ticket/cleanup capacity. Use the final `5cc3a1f2…` generation, not earlier partial generations. Full-history R00 had 154 repurchases within four days versus C01's 61, and about $3,689 more modelled costs. This suggests testing turnover, but does not prove resizing or the risk brake caused its total loss. Shared-vault changes in NB07 include timing and compounding, not just dilution. Unconditional overflow gained in earlier years and lost in 2026; intrinsically weak extra vaults are not established.

Detailed references: [summary](summary.md), [NB07](07-score-position-count-analysis.md), [expanded NB10](10-expanded-score-allocation-smoke-findings.md), [NB17](17-capital-allocation-findings.md), [NB18](18-conditional-cash-allocation-findings.md), and [cross-folder inventory](../hyperliquid-ic/hyperliquid-ic-summary.md).

## Inputs, periods and fixed assumptions

- Fresh 2026: `[2026-01-01, 2026-10-05)`, through 4 October UTC, default for every chart, table and narrative metric comparison.
- Full history: `[2023-03-01, 2026-10-08)`, through 7 October UTC; the last archive day is partial. Separate fresh $150,000 accounts in each period. The periods overlap and are researched history.
- Use the same repaired archive and pinned source/framework identities as NB18. Verify the actual hashes; do not download, pull or change the universe during implementation. Keep all available preceding indicator warmup, including 2025 for the 2026 accounts. Earlier reference history can estimate risk but cannot supply future account state.
- Two-day decisions, naive UTC, source as-of observed NAV fill convention and indicators ending at the last completed prior daily bucket. No invented slippage. Actual observation ages/update masks remain separate from carried NAV.
- Core: six maximum positions; entry rank 6, exit rank 8; existing minimum score improvement, 14-day loss gate, $7,500 TVL minimum, guard/curator/leader-share/permission checks, 98% fresh allocation budget, 33% account concentration and TVL participation limits. Read values from frozen parameters rather than duplicating constants.
- Core score: `0.48*CAGR360 + 0.32*Sortino45 + 0.10*CAGR180 + 0.10*Sortino30`, with the existing normalised clips at CAGR 1 and Sortino 3 and `missing=True`. Core waterfall priority is the exact existing regularised90 inverse variance implementation.
- Preserve source buy/sell bands, absolute minimum deposit, settlement/pinning, cost basis, and global 0.5% tiny-position cleanup. Do not alter thresholds to make an inactive treatment appear active.

## Historical control reference — 2026

These are saved NB18 corrected-fee values on the pinned inputs, not a forecast of new results. A shared valuation correction can change the replay and must be labelled.

| Backtesting period | Net profit | CAGR | Sharpe | Maximum drawdown | September cash |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 January–4 October 2026 | $62,366 | 58.58% | 2.49 | −6.09% | 49.82% |

<details><summary>Full-history control reference, 1 March 2023–7 October 2026</summary>

Saved C00 net profit $270,857, CAGR33.13%, Sharpe1.82, maximum drawdown−9.97%; September2026 cash63.22%. This account starts separately at $150,000 and carries earlier profits into 2026. It is not an independent holdout.

</details>

## Hypotheses and estimands

| ID | Question | Primary comparison | Interpretation |
| --- | --- | --- | --- |
| H1 | Does controlled extra breadth add value without rewriting the core? | Held flat tickets versus C00; risk-only versus flat | Separate extra opportunity from risk-based sizing, including feedback and costs. |
| H2 | Do score and risk both help position weights? | Held combined tickets versus held risk-only and score-only tickets | Main question; deployment can differ, so supplement with common-budget diagnostics. |
| H3 | Does absolute sizing improve on normalised weights? | Absolute combined resizing versus normalised score×risk, plus common-budget fixed-basket shadows | Normalisation changes allocation amount and cap-distorted proportions under the same resizing rule; the shadows identify their effects. |
| H4 | Does retaining units improve economics? | Held combined tickets versus identical tickets resized every decision | Whole-policy turnover contrast, including its exposure path and timing. |
| H5 | Do extra slots help once entry weights control weakness? | Combined hold method at 8/10/12 total ceilings | Core ranks remain fixed; report effective funded breadth and slot exclusions. |
| H6 | Are results dependent on arbitrary strength floors/exposure limits? | Registered floor and smaller-cap sensitivities | Expose assumptions; do not choose defaults after seeing outcomes. |

Primary outcome is net profit/CAGR versus matched C00. Report Sharpe, maximum drawdown, worst 7/30-day returns, costs, cash and concentration alongside them. A higher-profit policy with worse risk is a trade-off, not a dominant replacement. Report direct additional-role PnL and whole-account profit differences separately: compounding, promotions, funding and costs interact.

## Preserve the C00 policy correctly

### Rules versus independent portfolio trajectories

The primary treatment preserves C00's algorithm and thresholds on each treatment's current wealth and core state. It cannot promise identical future dollar holdings to an independently compounded C00 account after additional positions gain or lose money. State this explicitly; do not call a same-date target comparison independent economic parity.

Maintain persistent `core`, `additional`, `pinned` and `pending` roles. For core incumbent hysteresis and best-new-entry comparisons, only core incumbents receive held-core status. Additional holdings cannot suppress a better new core entrant merely by already being held. Candidate ranking, eligibility and all source tie-breaking remain unchanged. An additional vault promoted to core must pass the source's core admission logic; ownership alone cannot bypass permissions or guard checks. During execution it is still the same actual position, so only the necessary net top-up/trim is generated. A departing core name may be admitted to the additional basket under the same rules as other extras; its actual cost basis and entry date persist.

Keep source `max_assets_in_portfolio=max_capacity_assets=6` for every arm and call the evaluator with `n=6`; separate additional-slot policy implements 8/10/12 total ceilings. The evaluator otherwise sets source capacity to n and can activate its own extension. Assert both source parameters and entry6/exit8 each cycle.

Use the frozen source C00 callback as the authority. Add narrow hooks for core-role held status and combining additional targets before final trade generation. Audit every source use of `held_pair_ids`, not just hysteresis: whitelist bypass, new-entry scores, incumbent retention, deposit-check skip, blocked-top-up handling, extension and diagnostics. Use one declared core-role held set for these core selection/admission predicates; maintain a distinct actual-held set for valuation, cost basis, pins, old weights, execution netting and funding. Extra ownership cannot bypass a fresh core-entry check. Emit retained extra signals even if an extra drops out of the source candidate list; apply its explicit source/guard/permission/settlement exit or pinned handling, not accidental absence-of-signal selling. Do not rebuild the core using `capital_allocation.Policy`/M01 and call it exact: NB18 demonstrated that this substitution changes results. Inspect `waterfall_comparison.waterfall_decision()` and `capital_allocation.corrected_benchmark()` for the real authority. Keep candidate filtering, score transformation, risk peer conventions, fee refresh, waterfall and blocked-top-up handling in their original order. If the compiled source hook changes, hash and document the exact transformation.

Refresh and mark actual holdings once. Pinned additional holdings remain real exposures, liabilities and unavailable capital; never convert them to virtual cash or hide them from settlement accounting. Source pinning and slot semantics must remain unchanged, including cases where pinning prevents six funded core holdings.

For every decision, independently calculate the C00 core-only intention from the same timestamp, eligible universe, account valuation and core-role state. Compare membership, ordered scores, risk priority, targets, threshold decisions and funding with the combined proposal. This comparison treats redeemable extras as liquidatable at actual modelled proceeds for funding, not as an injected reserve. Protect the core first; reduce or close redeemable extras when needed. Record unavoidable funding differences caused by pinned extras rather than claiming protection succeeded.

The global cleanup denominator can change when extras are added. Bound the additional allocation so that the source's core cleanup/trade intents do not change solely through that denominator. Use an independently checked source calculation; the NB17 expression `min(core_target/epsilon)-sum(core_targets)` is an initial bound, not sufficient proof for actual holdings, ignored small trims and pinned names. Suppressed core trades remain part of realised exposures. One vault receives one final net target and one net trade direction per decision.

### Required parity before treatment execution

1. Reproduce historical C00 in both periods, then run the new adapter with zero additional slots and compare complete equity, membership, quantities, fees and trade timestamps, not just rounded metrics.
2. Insert additional-role candidates with zero capital and verify no changes to core intentions on representative stored decision states.
3. Verify source cases: unscored new entry, rank hysteresis, blocked incumbent top-up, scarce TVL, pinned settlement, promotion/demotion, minimum tickets, outgoing position fees and source tiny-position cleanup.
4. Verify additional-role positions at source ranks 6, 7 and 9; assert that the source held predicates agree, that every retained extra receives a signal, and that source extension stays disabled.
5. Assert conditional core-target equality and executable core-first funding at every treatment decision; explain any pinned-liquidity exception and fail the protection claim if it is material.

Independent C00 account membership may differ later because wealth and execution differ. Quantify divergence and core PnL changes; do not describe all incremental profit as extra-vault PnL. No separate shadow account is needed for trading: same-state counterfactual core evaluation supplies conditional parity. Any locked-reference ledger is a labelled diagnostic and cannot supply spendable cash.

## Cost and valuation prerequisite

Use NB18's corrected partial-redemption calculation for all accounts. First reproduce the historical C00 with that convention, then check the cached-pair close/reopen valuation issue described in NB18. Compare gross NAV, remaining cost basis, single modelled liquidation fees, actual cash received and the generic post-trade quote on fresh/open/trimmed/closed/reopened positions. Do not assert that the source wrapper doubles fees without tracing the actual route.

If an inherited marking inconsistency is confirmed, use one common consistent quote/valuation convention for C00 and every treatment in a new identity. Keep historical C00 as a labelled replication row and explain its metric change. Never compare a repaired challenger with an unrepaired control or claim the old 58.58% is guaranteed after a shared accounting correction. Prefer a local research pricing hook; editable framework fixes belong under `~/code/trade-executor`, require separate documentation and must not silently change existing notebook generations.

Bound the audit to the known route issue; do not turn NB19 into a framework refactor. Each decision creates separate pricing and valuation instances. The source wrapper replaces price from mid; the generic valuation can reuse a stale cached pair exit tax after reopening. A reopened profitable vault can show a dip until the next fee refresh. That can affect Sharpe differently in hold and resize arms, so shared code does not imply cancellation.

Record each reopen, cached rate, fallback rate, gross value and duration until refresh. Show the summed tax-gap dollar-days as an exposure diagnostic, not a fabricated exact profit adjustment. Detect stale-tax exposure in the final valuation window; never assert it is absent without checking. Verify reference equity before refresh, targets after refresh and actual cash received separately. If the discrepancy affects the compared accounts, use a local shared hook resetting cached tax for closed/non-held pairs to the source capital-fee fallback before new-entry valuation, and verify same-cycle entry/trim/close/reopen quotes. Re-run all affected accounts with a common identity; retain historical C00 separately. This bounded correction uses existing fee assumptions and does not require a framework rewrite.

The source's 10% positive-profit redemption fee and 0.1% capital allowance are inherited modelling assumptions, not verified extra venue fees. They must not duplicate a fee already internalised in NAV. An unresolved economic fee convention qualifies the strategy verdict; numerical reconciliation alone does not prove the assumptions.

## Sparse data and score strength

Carry positive NAV forward only after the first genuine observation; never backfill before inception or fabricate a future terminal quote. Calendar metrics must work with sparse carried paths, while actual update count, observation age and gaps remain confidence diagnostics. Preserve archived permission/cap/leader-share values when independent observation clocks are unknown. Explicit zero, explicit NULL and unknown clock differ; archive `written_at` is not a fabricated permission-observation time.

Keep the core composite and availability mask separate. For additional performance sizing use:

```
g_i = f + (1-f)*clip(s_i, 0, 1)   if the source composite is finite
g_i = f                           if the source composite is unavailable
```

Primary f=0.5; predetermined f=0.25 sensitivity. This positive floor allows eligible unscored and finite-zero vaults modest tickets while retaining their different flags/reasons. It is a sizing convention, not a measured expected return. Ranking uses original source missing numeric-zero/address tie behaviour. Core `missing=True` is unchanged; do not replace its composite with an available-component formula. Show young partial-history versus mathematically undefined metrics separately.

The floor avoids recreating NB17's scored-only M06 through a zero multiplier. It also weakens selectivity and could fund unprofitable vaults: test and disclose it. Do not choose the floor using historical winners. A lower finite score weakly lowers an uncapped ticket, but cap/floor effects may erase the difference. Report intermediate g values and actual score-sensitive executed dollars. Unknown histories must not appear confidently low risk merely because filled returns are flat.

## Additional risk and common feasible budget

Use the existing regularised90 daily-simple variance estimator with actual-update shrinkage strength 30. Extras use a fixed, as-of source-eligible peer pool, shared across treatments. Use each focal estimate's existing leave-one-out positive prior: `v_i=predicted_variance_i`, `v0_i=prior_variance_i` and `sigma_i=sqrt(v_i)`. Follow the existing helper's support/fallback rules; requesting extra IDs cannot change core priors or other peer estimates. Core priority uses the exact C00 estimator, including its existing peer semantics. Missing empirical risk uses the existing supported positive prior and is labelled; no usable positive estimate/prior means no new ticket. No fabricated variance floor.

Define bounded risk preference `r_i=min(1,sqrt(v0_i/v_i))`. This penalises high estimated volatility without amplifying a flat/prior-only estimate into an unlimited ticket. Prior-only names have v_i=v0_i and therefore r_i=1: the performance floor and ticket/exposure limits are their only additional attenuation. State this explicitly. Risk prediction is not profit prediction. Include NB18's max(regular,gap) risk estimate as a same-state diagnostic, not another estimator package in the primary engine matrix.

Use gross exposures and conservative post-trade equity E_safe, accounting for actual modelled exit charges, ignored small trims, pending/pinned holdings and fee marks. Convert gross NAV dollars to engine target dollars explicitly; do not create exposure headroom from fee-discounted marks. Unknown pinned exposure blocks new extras.

Primary limits are four additional slots, ten total including pinned positions, 25% gross additional exposure and 5% per additional vault. These are provisional limits inherited from NB18, not approved production risk tolerances. Four 5% positions imply at most 20% exposure; the 25% total limit can bind in the six-extra sensitivity or inherited/pinned cases. Display which limits actually bind. Never force ten invested names.

Let R_mark be the non-negative residual of the source marked-dollar target budget after core and cleanup protection. Use that numerical USD amount conservatively as a gross-dollar spending ceiling, without inflating it by an inverse fee factor: `T_gross=min(R_mark,0.25*E_safe)`. Also require summed marked extra targets <=R_mark and actual fresh-buy reserve <= actual cash plus synchronous final net sale proceeds after core funding and source headroom. T_gross includes retained gross extras; it is not fresh cash to add again. This conservative convention can leave additional cash and must be reported. Settlement and pinned capital remain excluded by the source budget/funding route. Subtract retained/pinned usage once before fresh admission. Per-name total holding capacity includes source concentration/TVL ceiling and the 5% gross limit; buy increment capacity separately includes deposit headroom. A blocked deposit permits retention/reduction where redemption rules allow, never a fresh buy/top-up. Explicitly transform between marked and gross capacities before comparing T with exposure.

No volatility-anchor brake, Kelly multiplier or return forecast is in primary trading. Removing NB18's brake is a declared package difference: current-risk subtraction may force sales after shocks, but earlier results do not prove that it caused losses. A same-state diagnostic recalculates the NB18 brake from a causal C00 reference and measures excluded dollars; it cannot attribute returns. Here risk is controlled through entry sizing and gross limits; total account risk can rise and is assessed as an outcome.

## Absolute tickets, normalised controls and management

Set entry ticket scale `D=eta*c_name*E_safe`, with primary `eta=0.5` and `c_name=0.05`, giving 2.5% of E_safe before multipliers. The hard gross holding cap remains 5%. This headroom avoids entering every low-risk winner directly at its trim boundary. Eta is a declared research choice, not an optimal value; show eta=1 in same-state capacity/drift diagnostics rather than another engine grid. Hard drift trims can still sell winners and must be counted. All amounts below are gross NAV dollars, not pre-fee engine target marks:

```
Flat ticket:       a_i = min(source_capacity_i, D)
Risk ticket:       a_i = min(source_capacity_i, D*r_i)
Score ticket:      a_i = min(source_capacity_i, D*g_i)
Combined ticket:   a_i = min(source_capacity_i, D*r_i*g_i)
```

Multipliers act before capacity clipping. Small vaults may receive identical tickets despite different recipes: report this rather than treating it as an error. No pooled-return gate or fitted marginal-core ticket anchor is needed. Absolute weaker-score ticket reductions stay cash; no renormalisation recycles them into other names. For a fresh buy source_capacity is the allowed increment capacity. For incumbent target resizing it is total permitted holding capacity, including existing value. Actual cost basis and fee consequences remain in the engine.

For normalised controls on a fixed basket, choose `x_i(lambda)=min(c_i,lambda*u_i)` with `sum x<=T_gross`, stopping when every positive utility capacity saturates. Utilities are r_i for risk-only and g_i*r_i for combined weights. Independently check active-set/bisection conservation and common-utility scale invariance. Uniformly smaller positive utilities do not reduce total deployment by themselves. With four slots, 5% single caps and a large residual, normalised methods often saturate at the same cap-filled basket. The economic matrix therefore keeps just the combined normalised control; risk-only normalisation is a same-state diagnostic. Report unsaturated dates/dollars instead of treating identical capped results as evidence that score information is useless. Remaining capacity-constrained cash stays cash.

### Worked ticket example

At E_safe=$150,000, D=$3,750 and the hard single cap=$7,500, suppose gross residual allowance is $10,000 and there are three feasible extra candidates with enough source capacity. A has score1 and risk equal to its peer prior; B has score0.2 and sigma twice its prior sigma; C has a missing score and prior-only risk. Then r=(1,0.5,1), g=(1,0.6,0.5), and combined tickets are ($3,750,$1,125,$1,875). Total=$6,750; $3,250 stays cash. Normalised g*r weights on that same unconstrained basket spend $10,000 as approximately ($5,556,$1,667,$2,778). These are proposal amounts before source fees/trade floors, not realised profits or a reason to prefer one method.

If held A gains at the next decision, hold retains its share quantity while its gross value rises, until mandatory funding/cleanup/limits apply. Resetting its dollar value to $3,750 would rebalance and belongs to the resizing arm. Independently verify the arithmetic, cap clipping and incremental-deposit versus total-target versions.

### Selection and retention

The source-ranked non-core candidate pool is identical before treatment-specific execution. Exclude core and non-allocatable pinned names; order by original score/address. Source eligibility, guard and deposit checks remain mandatory. An additional holding in a de-whitelisted vault cannot use the core held-status bypass; emit its permitted exit or pinned signal explicitly. Fresh candidate scanning can use the whole eligible list, as in the earlier refill policy; do not add an undisclosed rank `6+K` admission gate. Skip infeasible minimum-ticket/cleanup entries and continue scanning; report every skipped candidate and reason. Realised baskets can differ because weights change executable tickets. Use common fixed-basket shadows before interpreting a comparison as pure weighting.

In every extra arm, retain source-eligible incumbents before fresh candidates, subject to funding, source capacity and gross limits. Retained names consume slots and T_gross once. Core/additional are exclusive economic roles; pinned/pending are orthogonal flags. Compute available fresh slots from the union of actual retained/core/pinned holdings and positive planned entries, without counting a pinned core twice. Enforce K additional names and 6+K actual total names, and report any inherited non-redeemable exception. No new rank-based extra exit rule: a lower score alone is not source ineligibility. Source return/TVL/guard failures, redemption availability and mandatory funding/limit handling still apply. This intentionally permits a low-scoring eligible incumbent to occupy a slot; measure locked slots and attractive fresh candidates excluded. Replacing incumbents by rank is a separately registered follow-up, not a silent modification to this notebook. A core demotion can enter this retained-extra stage only if it is feasible and consumes the same limits as other extra incumbents.

**Hold units:** freeze actual shares after purchase. Do not continuously target the entry dollar value, which would itself rebalance. No routine top-ups/trims for changing scores or sigma. Trim/exit for source ineligibility, funding/settlement, source capacity/gross-limit breaches or source cleanup. Emit a signal with target equal to its current post-refresh old value for every retained extra; the source trade generator otherwise treats an unsignalled open position as an exit. Verify that this signal produces zero rebalance quantity when no mandatory action applies. Promotion to core transfers role and nets the required quantity, without an obligatory sell/rebuy. Retained units are marked and checked against limits every decision.

**Resize:** recompute absolute or normalised total targets every two-day decision, then apply the identical retention/admission/mandatory-exit policy and source buy/sell bands. Blocking a top-up does not imply liquidating an incumbent. The resize-versus-hold contrast includes different exposure paths and timing, not just fees. Source buy and sell bands differ roughly tenfold, so resizing can ratchet upward: show requested/executed increases and decreases separately, and measure small suppressed reductions. Do not silently equalise the bands.

Hard funding/cap reductions may require a larger permitted trim/full close when a smaller required reduction cannot execute. Ordinary score-driven changes retain source bands. Pinned exceptions are explicit; prohibit fresh extras when compliance cannot be restored. Sell the lowest-source-score redeemable extras first for funding, breaking ties by address, consistently across methods. Recompute actual proceeds before new buys. The combined target goes through one final net trade pass.

## Small registered matrix

Run every arm on the entire fresh-2026 period with 2025/earlier warmup, then a separate complete full-history account. Nine economic methods, eighteen accounts, plus two adapter zero-slot parity replays. No Cartesian feature/window/threshold/risk grid.

| ID | Additional ticket/utility | Management | Extra / total slots | Purpose |
| --- | --- | --- | --- | --- |
| C00 | None | Source | 0 / source six | Corrected exact C-W control |
| E00 | Absolute flat D | Hold units | 4 / 10 | Clean capped extra-breadth control |
| R00 | Absolute D*r | Hold units | 4 / 10 | Risk sizing versus flat tickets |
| S00 | Absolute D*g | Hold units | 4 / 10 | Score-only sizing under shared caps |
| RS00 | Absolute D*r*g | Hold units | 4 / 10 | Combined score/risk; primary hypothesis |
| RS01 | Same tickets as RS00 | Resize each decision | 4 / 10 | Turnover-management contrast |
| NRS00 | Normalised g*r | Resize each decision | 4 / 10 | Normalisation contrast with RS01; risk-only normalisation is a shadow |
| RS08 | Same tickets as RS00 | Hold units | 2 / 8 | Fewer extra slots, core thresholds fixed |
| RS12 | Same tickets as RS00 | Hold units | 6 / 12 | More extra slots, core thresholds fixed |

The zero-slot adapter is labelled P00 in audit tables and must equal C00 before interpretation. Use namespaced experiment IDs in caches: NB18's R00 is a different policy. Earlier C01/C02 are labelled historical context only. All primary extra arms share estimator, source core, exposure limits, performance floor, candidate order and mandatory handling.

After primary audits, run two predetermined local sensitivities of RS00 in both complete periods if it executes fresh extra dollars. Keep RS00 as the parent even if another arm wins. If RS00 is inactive or all absolute methods are identical under binding capacity, diagnose before any registered amendment.

| ID | Change from RS00 | Purpose |
| --- | --- | --- |
| GF25 | f=0.25 instead of 0.5, for finite and missing scores | Strength/floor dependence; not a missing-only intervention |
| CAP10 | 10% total / 2% single limits; D becomes 1% of E_safe with eta=0.5 | Smaller loss exposure; ticket scale and both limits change as a labelled package |

There are 24 registered accounts including two adapter replays and four sensitivities. A changed common valuation identity can require two additional historical C00 replication runs (26 executed account jobs in that case); every treatment must use the corrected common identity. Cache reuse is allowed only with exact identities. Same-state diagnostics cover unlimited slots, NB18 k=0.75/1 brakes, gap risk, squared-risk preference and account sizes $75k/$150k/$300k. They are allocation diagnostics, not executable engine results. Do not scale actual permissions/fees or infer an economic capital-size backtest from a capacity chart.

## Economic and mechanism diagnostics

Log every decision/candidate: role, raw score, availability/missing reason, raw finite clipped score (NaN retained) and g, actual-history/update count, quote age, regular risk and gap diagnostic, prior variance/confidence, core intention, risk-only dollars, attenuated dollars, accepted/executed change, capacity, fee/cost basis, minimum ticket, blocked permission and binding budget. Distinguish selected, positive target, actually invested and effective concentration-based breadth.

Required comparisons:

- Extra capital requested versus actual fresh buys, retained exposure and recalled capital. Count score multipliers strictly between zero and one and the dollars reaching execution with them. Report fractions at the floor, strictly intermediate, and one; an inactive continuous rule has not demonstrated useful sizing.
- Active C00 target-residual calendar versus executable residual after tickets, core funding and cleanup; primary results conditioned descriptively on actual opportunity dates, with the rest of 2026 still included.
- Additional-role net PnL per gross dollar-day, paid charges versus open liabilities, source mandatory exit reasons and new purchases versus demotions.
- Daily total/core/additional cash weights, September capacity episodes, complete-quarter PnL attribution and core refill funding recalls. Measure actual additional-position and role holding durations; a position ID can change role without closing.
- Additional buy/hold losses and positive contributors; whole-account shared-vault versus additional-only attribution; role-transfer accounting that reconciles holdings, cost basis and cash. Avoid counting a demoted incumbent as a new purchase.
- Unscored versus finite-zero versus finite-positive exposure and outcomes; young versus old histories; actual-update/quote-age strata. A low volatility estimate may reflect stale marks, not low economic risk.
- Locked-slot diagnostic: on full-slot dates, pair each skipped finite-score feasible fresh candidate with the lowest finite-score extra incumbent and compare same-origin forward 7/30-day NAV outcomes where terminal support resolves. Keep unresolved cases/maturity/observation ages and overlap visible. Define outcome as as-of NAV(t+h)/as-of NAV(t)-1, with terminal-support/maturity handling from NB18 and no invented future mark. These are counterfactual NAV opportunities, not executed replacement PnL, and do not alter trading. A registered future replacement rule could contest a full slot only when a finite-score fresh candidate beats a finite-score incumbent by the source minimum improvement; missing scores are not automatically evicted.
- Same-state C00 snapshot comparison on every source decision date for all utilities. Pair weights/baskets/budgets, show cap/floor distortion, and reproject to a common smaller ex-ante deployment budget. These diagnose allocation mechanics and cannot replace engine results.
- Fixed matched-budget risk-only weight control for score methods, plus a documented deterministic score-assignment placebo if score improvement is material. Do not add a broad random search. Ex-ante score permutations must preserve the candidate basket and recompute execution constraints; fixed-ledger attribution alone is not a tradable strategy.
- Largest contributor and best-update removal on the fixed ledger, quarter exclusion, first-observation/catch-up contribution, and 50%/100% additional-vault loss stress. Label fixed-ledger and mechanical stress views clearly.
- Report count of available non-overlapping time blocks if estimating uncertainty. Neither overlapping 30-day snapshots nor the two overlapping account periods are independent confirmations. Descriptive paired quarterly economics are primary; do not claim a searched winner is statistically established.

## Notebook structure and visual presentation

Every display must appear as subheading, short clear description, then element. All chart titles include actual backtesting period. Every image is separate, never a collage. Default narrative tables and charts use 2026; full-history tables/figures are in a distinct labelled section. Use existing trade-executor chart/metric helpers and the NB15–18 plotting conventions, including absolute account weights and distinct consistent cash colour. Tables colour each key metric in its appropriate direction.

Keep the NB18 daily-resampled Sharpe convention, including off-cycle zero bins; do not mix older cycle-clock figures into matched tables. Key metrics include net profit, cumulative return, CAGR, Sharpe, Sortino, maximum drawdown, Calmar, paid fees/open liabilities, trades, maximum/mean/effective holdings and mean/September cash.

1. **Question and registered methods:** goal, previous evidence, narrative strategy-logic table and compact frozen matrix; data/source/cost fingerprints in collapsed detail.
2. **Control and execution checks:** readable parity table, conditional core protection, funding/role/limit checks and any common valuation correction. Failed prerequisite stops economic interpretation.
3. **2026 key results:** one side-by-side metrics table, equity curves, CAGR/Sharpe, CAGR/drawdown and Sharpe/drawdown scatter plots, separate absolute asset/cash weight chart per arm. Legends must show every visible series without clipped names.
4. **2026 incremental economics:** quarterly profit-difference heatmap versus C00; table separating role PnL from account uplift and core feedback; cash versus profit plot. Show every quarter, marking October as partial.
5. **2026 sizing activation:** absolute risk-only versus score-adjusted ticket scatter, colour by score availability/quarter; score versus executed additional weight, showing caps/floors; additive ordered capital rejection waterfall or labelled overlapping reasons; realised position/effective-breadth timelines. Different graphics must answer different questions.
6. **2026 risk, missingness and turnover:** score/support/risk exposure tables, drawdown and loss stress, holding-duration histogram, costs and core funding recall table. Distinguish dollars from decision counts and intention from execution.
7. **2026 local sensitivities:** compact slot/management/floor/cap matrix table and heatmaps only for actual matched combinations. Never imply an unrun Cartesian grid or interpolate absent cells; show unavailable cells explicitly.
8. **Full-history results:** separate side-by-side metrics, equity curves, absolute weights, quarterly incremental PnL and contributor/cost diagnostics. Attribute early cash-only history explicitly.
9. **Verdicts and next action:** hypothesis-by-hypothesis conclusion, activation, economic gain/risk exchange, cost/data limitations and a small frozen candidate for later observation if justified. Update `summary.md` and write `19-protected-core-score-risk-allocation-findings.md` after execution.

## Implementation steps, ownership and completion criteria

1. Read `.claude/docs/vault-selection.md`, notebook execution/preview guidance and repository instructions. Do not edit universe lists, original source strategies, documentation repository or existing NB18 artefact generations.
2. Pin inputs and audit cost routes; reproduce C00. Build source-authoritative core hooks and meaningful independent fixtures for role isolation, fees, funding, cleanup, sparse support and score scale invariance.
3. Implement score/risk proposal helpers and independent algebra examples before engine accounts. Store reusable modules/builders outside generated artefact directories; proposed names `protected_core_score_allocation.py`, `protected_core_score_report.py`, `create_protected_core_score_notebook.py`.
4. Run nine methods serially after the zero-slot adapter checks for fresh 2026 and full history. Use `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`; save after every cell; progress visible to the runner but suppress unnecessary saved stdout/progress bars. Reuse only caches with exact matching identities.
5. Run the two registered RS00 sensitivities if activated, otherwise record why and defer changed designs. Complete all result/diagnostic displays and narrative verdicts. Generated datasets, states, manifests, review logs and PNGs live under ignored `_artifacts*/19/`; notebooks and durable conclusions remain reviewable.
6. Inspect every chart separately and verify saved notebook rendering via the repository static preview server. No live Jupyter server for previews. Reconcile all weights/PnL/cash/fees and ensure no saved error/warning output.

Completion requires complete account outputs, exact zero-allocation C00 parity, demonstrated conditional core protection or explicitly failed protection, no fabricated cash or future marks, executed exposure/risk/slot checks, active-sizing diagnostics, clear economic verdicts for both periods and updated findings/summary. A stronger strategy is not assumed as a completion condition.

## Claude contribution and review

Both contribution and final review are complete. The final verdict was conditional on concrete corrections; these are incorporated and documented in the [review decisions](19-protected-core-score-risk-allocation-review.md). Both successful responses report only `claude-fable-5-1`, no fallback and no permission denials. Claude received full earlier context and read-only access to the research folders and relevant source repositories. The review records actual inspected-file evidence, objections, alternatives and accepted/rejected changes; raw prompts/responses and the submitted-plan fingerprint are retained under the ignored review directory. Final corrections were checked against the conditional review, rather than described as an additional independent review.

## Implementation record

The registered eleven methods produced 22 economic accounts across both periods, plus two complete zero-extra parity accounts and two historical references. One additional C00 diagnostic replay captures common-state allocations and verifies identical complete equity/trades; it trades no extra capital. All reported economic arms use the same fresh-entry cached-tax reset, with the legacy control retained separately. Hard cap reductions below the inherited sell band now close the affected extra holding; the conservative equity bound also reserves possible fresh-entry capital charges. Every economic account was rerun after these corrections under a new identity.

The source core parameter remains six; a local evaluator assertion permits each registered total slot ceiling without changing selection. Generated states, ledgers and charts are ignored artefacts. Formula/sparse-data and synthetic adapter fixtures complement actual per-decision audits. Actual accounts contain no pinned positions, so asynchronous settlement and non-redeemable extra role transitions remain unvalidated production cases rather than claimed empirical successes. Capital-size, unlimited-slot, score-reversal, gap-risk, squared-risk and NB18-brake comparisons are explicitly proposal diagnostics, not additional economic backtests. Deletion sensitivities use fixed booked ledgers.

Results do not establish that the extra sleeve is independently profitable. RS01 is a modest historical challenger; the primary held-ticket hypothesis is rejected in fresh 2026. No new selector, extra rank-exit gate, future-filled metric or synthetic cash was introduced.
