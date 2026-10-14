# Experiment 21 — marginal profitability and adaptive portfolio allocation

Status: ready for implementation after two Claude Fable 5.1 planning reviews, 13 October 2026. Final review amendments are recorded below and in the review log. Planning only; no experiment executed.

Proposed notebook: `21-research-marginal-profit-allocation.ipynb`. Parents: NB08–12 signal research, NB17–19 allocation experiments and NB20's clean accounting comparison. The contribution and decision log belongs in `21-marginal-profit-portfolio-review.md`.

## Goal

Find whether existing information can increase net account profit by distinguishing capital worth investing from capital better left in cash, and holdings worth retaining from holdings worth replacing. Let position count, position sizes, entries, exits and cash respond to the economic opportunity. C00 and v11 are controls, not mandatory portfolio construction rules.

The main challengers have **no six-slot ceiling, fixed top-rank admission, compulsory inverse-variance sizing, protected core, or automatic normalisation to full investment**. They may hold more or fewer than six vaults, resize incumbents, and retain cash. All decisions use one real account and its available capital.

Evaluate expected gain **and loss magnitude**, action-specific costs, and the opportunity cost of keeping a holding. A probability of profit alone is insufficient: frequent small wins may conceal rare large losses. A low historical score is not evidence that a position will lose money. Unknown information is not a forecast loss.

The first stage is deliberately small: an accounting/holding audit, a causal signal study, and ten full-2026 portfolio comparisons. Defer joint CVaR optimisation and large model searches until the simpler experiment establishes useful decisions.

## What is different from the previous searches

| Earlier limitation or finding | NB21 response |
| --- | --- |
| NB06 screened 74 bounded recipes with designed 48/32/10/10 coefficients | Reuse the existing features; learn economically calibrated outcomes rather than launch another arbitrary formula grid |
| NB08 thresholds sometimes vetoed zero executed dollars | Require activation, avoided losses, missed winners and net dollar effects at the actual decision margin |
| NB09 K gave small, uncertain return-forecast improvements; support controls were competitive | Use pooled/support baselines, retain missing vaults, and test a small conditional model against them |
| NB10–12 already explored risk estimators and score composites | Risk enters an explicit loss budget; it does not prescribe inverse-risk weights |
| NB17 filled more cash but often diluted profitable holdings | Cash usage is a diagnostic, not the optimisation target; evaluate replacements as well as additions |
| NB18 forecast 30 days ahead while closed-position count-weighted median lifetime was four days | Audit capital-weighted and profit-weighted holding spells before locking the policy horizon |
| NB19 changed extras around a protected core; the fresh-2026 gain was only USD 255 and extra-role PnL negative | Make all feasible holdings decision variables, with entry-only and six-slot ablations to identify the source of any improvement |
| NB20 established a clean C00/v11 accounting comparison | Reuse its frozen data and accounting; reproduce the controls before interpreting challengers |

NB20 reference results: fresh 2026 CAGR C00/v11 **58.59%/49.15%**, Sharpe **2.474/2.214**; full-history CAGR **33.13%/18.55%**, Sharpe **1.651/1.374**. C00's full-history drawdown is worse. One vault explains 50.5% of the 2026 net profit difference. These are historical controls, not evidence that a learned replacement policy will win.

### Required reading

Read `06-score-3-4-inputs-analysis.md`, `08-score-forecast-findings.md`, `09-k-ratio-feature-forecast-findings.md`, `10-expanded-score-allocation-smoke-findings.md`, `11-weighting-sizing-findings.md`, `12-allocation-followup-findings.md`, `17-capital-allocation-findings.md`, `18-conditional-cash-allocation-findings.md`, `19-protected-core-score-risk-allocation-findings.md`, and `20-c00-vs-v11-findings.md`.

Inspect the actual implementations where assumptions matter: `conditional_cash_forecasts.py`, `conditional_cash_report.py`, `conditional_cash_allocation.py`, `protected_core_score_allocation.py`, `portfolio_snapshot_risk.py`, `k_ratio_features.py`, `score_matrix.py`, `clean_c00_v11_comparison.py`, the source `hyper-ai-v11.py` and framework AlphaModel/pricing/valuation. Reuse validated components; do not silently inherit NB19 diagnostics gaps or change previous notebooks.

## Questions and hypotheses

| ID | Hypothesis or question | Required evidence |
| --- | --- | --- |
| H1 | Some trading destroys net value through avoidable churn | Fees, remaining liabilities and spell PnL audit; wider sell-band control using corrected net proceeds |
| H2 | A conditional loss model identifies unprofitable exposure better than reporting quality alone | Causal calibration and monetary avoided-loss/missed-gain comparison, then identical allocation with and without the conditional signal |
| H3 | Conditional gain/loss magnitudes add useful information beyond loss probability | Same probability model and allocator, pooled versus conditional magnitude estimates |
| H4 | Profit-based decisions can improve construction without a prescribed slot count or inverse-risk weights | Full-account marginal-profit allocator against C00, and its otherwise identical six-slot ablation |
| H5 | Acting on incumbents matters as much as admission of extra vaults | Joint management versus entry-only action set |
| H6 | Sparse/young vaults can remain eligible without being treated as zero-risk | Missingness/fallback cohorts, calibration, conservative risk support and actual allocated dollars |
| H7 | Results survive nearby cost/risk assumptions and contributor dependence | Fixed sensitivity list, account replays where state changes, no after-the-fact winning grid |

Failure to beat the pooled forecast or C00 is an informative result. Do not increase the search budget until a winner appears.

## Freeze data, accounting and dates

Use NB20's exact archive, universe/guard, source and framework identities. Save hashes and resolve mismatches before attributing performance. Do not pull repositories or refresh vault data during implementation. Use `tradingstrategy.binance.price.fetch_binance_price()` for BTC/ETH context if needed.

- Primary evaluation: `[2026-01-01, 2026-10-05)` UTC, through 4 October. **Every smoke arm covers the whole period.** Reduce combinations, not dates.
- Full-history account replay: `[2023-03-01, 2026-10-08)`, through 7 October; last archive day partial.
- Start each account with USD 150,000. Retain all historical indicator warmup, including 2025 and earlier data for long windows and expanding K.
- Two-day decisions as in the controls. Features use completed data through T−1. Monthly forecasts train only on labels whose outcomes and required evidence matured before the fit timestamp.
- Full-history models must cold-start causally; no January-2026-trained model may trade in 2023.
- These calendars have already been researched and overlap. Call the exercise chronological/prequential, not an untouched holdout. Future newly collected data is the proper later frozen-policy evaluation.

Reuse NB20's three common accounting corrections: partial redemption fees applied once against gross NAV; cached sell-tax reset on genuinely reopened positions; buys funded by final synchronous net sale proceeds. No vault slippage is added. Modelled fees are inherited assumptions, not certified venue economics; NAV may already internalise some fees. Report their effect explicitly.

## Stage 0 — find the economic decisions that matter

Before fitting forecasts, produce these tables for C00 and v11:

1. Gross investment profit, realised modelled fees, change in open liquidation liabilities, net profit and turnover. Reconcile to account equity.
2. Holding spells: count-weighted duration, dollar-day-weighted duration, and gross/net PnL by `<7`, `7–30`, `>30` calendar-day buckets. Include open/censored spells separately. Avoid selection bias from reporting only closed winners.
3. Each decision's proposed versus executed buys, trims, closes and replacements. Identify suppression by buy/sell bands, permissions, funding and capacity.
4. Lost or gained capital exposure during rotation: sold incumbent dollars, feasible replacement dollars, resulting cash, and subsequent marked returns. This is descriptive attribution, not a causal claim.
5. Deposit-permission coverage by date. Verify the reported 11 April 2026 start in the actual archive; label earlier assumed-open decisions explicitly and compare pre/post-coverage results.

The four-day count-weighted median from NB18 is **not sufficient** to choose a horizon. Register 2, 7 and 30-day signal views. Default policy horizon is 30 days; it is a planning horizon, with decisions revisited every two days. Before fitting, a documented amendment may change the primary horizon to seven days if a majority of both capital exposure and absolute net PnL in the controls lies in spells shorter than seven days. Do not choose by challenger performance. Report cancellation if open-spell censoring makes this decision unsupported.

All alternatives in a given action comparison must share the **same terminal horizon**. Two-day incumbent labels and 30-day fresh-entry labels cannot be directly subtracted. Fixed-horizon forecasts omit future optimal switching; disclose this and compare a matched seven-day policy only in the registered extension.

## Operational restrictions and free investment decisions

Preserve source blacklist/quarantine, protocol permissions, redemption locks, TVL capacity, actual cash funding and pending/pinned exposure. Unknown permission observations remain distinct from false; retain archived states according to the established reader contract. A locked position remains actual exposure and cannot fund another trade.

Main challengers scan all operationally eligible names, including unscored/young vaults and incumbents. Remove rank6/rank8 and fixed-N machinery. Turn the inherited 14-day return gate into a feature; a registered gate-on sensitivity measures its economic contribution. Keep the USD 7,500 TVL universe convention and provisional 33% account/33% vault-TVL caps initially, clearly labelled as inherited choices. Report rejected capacity and binding rates. Same-state 20%/33%/50% account-cap and starting-capital shadows are mandatory diagnostics, not automatically additional backtests.

Use the source's actual minimum ticket, buy band, sell band and dust handling. These are execution constraints with measured economic effects, not disguised fixed position counts. Record gross NAV exposure separately from fee-adjusted account marks. Pinned holdings consume capital and risk limits exactly once.

Do not add a new universal stale-quote ban. The task explicitly requires sparse histories to work. Quote age and support enter forecasts and conservative risk fallbacks. If an operational stale-price rule already exists, retain and disclose it; any new veto needs a separately named experiment and sensitivity.

## Stage 1 — causal opportunity and label panel

### Population and sparse history

At each decision include the full eligible opportunity set plus every held position. Record feasible fresh deposit, top-up, redemption, pinned status, source score/rank/gate, TVL headroom, actual observation counts and ages, and original missing-score status. Do not select rows by future survival or by what C00 bought.

Metrics use causal calendar-day forward-filled NAV after inception, with no backfill. Actual unchanged observations are valid; carried values are separately flagged. An unchanged carried mark is not proof of a resolved zero return or low risk. Do not compress multi-day gains into one-day risk observations.

Keep two outcome views:

- **Engine mark outcome:** exactly what the frozen backtest can mark at T+h, including carried NAV. This reconciles portfolio results.
- **Supported learning outcome:** a fixed-horizon target with sufficient actual endpoint evidence under an explicitly recorded observation-resolution rule. Missing terminal evidence stays censored; observations after T+h must not be quietly substituted as though observed at T+h. If a later mark resolves an interval rather than the exact horizon, retain actual duration and report it separately. Target support and maturity must be recorded, not inferred from filled prices.

Primary supported endpoints use actual observations within their daily endpoint buckets; no future bucket tolerance. This is a measurement restriction on learning, not a vault admission restriction. It is stricter than NB18’s carried-endpoint label and must be implemented as a new labelled view, not described as unchanged behaviour. Show its attrition by reporting frequency, age, quarter and invested dollars; run the engine-mark outcome as a labelled sensitivity. If exact-endpoint support is inadequate, do not claim a precise fixed-horizon forecast. Use the pooled fallback and report that limitation. No new threshold should silently exclude young vaults from the account.

### Economic labels and cost equations

Use gross NAV P, units q and remaining weighted-average basis b. Under the inherited assumptions:

`C(q,P,b) = 0.10*max(q*P-b, 0) + 0.001*q*P`.

For a fresh investment d, `q=d/P0` and terminal liquidation value is `L_fresh=q*Ph−C(q,Ph,d)`. Its net outcome against cash is `L_fresh−d`. For gross return r, the exact normalised outcome is:

`r_net = r − 0.10*max(r,0) − 0.001*(1+r)`.

Thus the expected fresh break-even condition is `0.999*E[r] − 0.10*E[max(r,0)] − 0.001 > 0`, before any uncertainty requirement. Apply the cost to each predicted outcome, not only to the mean.

For an incumbent, `L0=q*P0−C(q,P0,b)` and `L_hold=q*Ph−C(q,Ph,b)`. Its hold-over-cash increment is `L_hold−L0` with zero cash yield. For a full switch i→j, buy `q_j=L0/P_j0`; compare `q_j*P_jh−C(q_j,P_jh,L0)` directly with `L_hold` at the same horizon. Partial sales and top-ups use the actual basis and update equations. Gains already earned are not a new future forecast.

Implement a common path-value function for any proposed action vector a: current feasible sells, resulting cash, buys, remaining basis, and terminal net liquidation value `V_h(a)`. Optimisers compare complete path values under a common scenario distribution. Do **not** charge an extra turnover cost on top. Explicit uncertainty margins are preferences about forecast error, not fabricated transaction costs.

Future inability to redeem is a separate outcome. Marked terminal profit is not necessarily available cash. Keep liquidity/reporting hazards separate from financial-loss labels; disappearing observations do not establish a −100% return.

### Features and missing=True

Reuse a compact subset of existing features rather than repeat NB09's full feature search:

- Performance: 360-day log return (the CAGR input before annualisation), 45-day Sortino, 14-day return, 30-day drawdown and max-history K with its fitted history length.
- Risk/support: existing regularised 90-day risk estimate from NB11 (a predictor, never an allocation weight), actual 30-day observation count, quote age, recorded age, feature missing flags and endpoint-support history.
- Operational state: permission state/known flag, deposit headroom and TVL. Do not reconstruct historical TVL or leader-share changes from later snapshots. Optional change features require verified as-of provenance before registration.

Controls keep their exact scoring semantics, including `missing=True`. Models use training-only transforms and explicit missing masks; missing performance values receive training-median imputation, with pooled fallback where no supported fit exists. All-missing, mathematically undefined, partial-window, actual zero and unavailable history remain distinguishable. Do not code a missing forecast as negative profit or zero risk.

## Stage 2 — small signal ladder focused on losses and gains

Use three main models and the calibrated-score comparator specified in the smoke table; all predict a coherent gross-return distribution and have the same population, support handling and calendar.

| Model | What is learned | Purpose |
| --- | --- | --- |
| P: support prior | Support-only probability and conditional magnitude estimates, with pooled distribution shapes | Baseline without performance inputs |
| D: conditional downside | Negative-return probability from the compact feature set; same P gain/loss distributions | Does knowing when losses are more likely change profitable decisions? |
| M: conditional magnitudes | Same downside probability head as D, with performance inputs added to the conditional gain/loss magnitude heads | Do personalised expected profits add beyond probability? |

Let `p=P(r<0)`, `g=E[r | r>=0]` (including genuine unchanged observations), `ell=E[-r | r<0]`. Then `mu=(1−p)*g−p*ell`. Retain empirical conditional residual/distribution information so fees and downside estimates can be evaluated on outcomes. M must preserve the sign/support of each conditional distribution. Do not subtract `p*ell` again from an unconditional pooled mean; that would double-count expected losses.

Use a two-component empirical distribution: with probability p, `r=−ell*Z_minus`; otherwise `r=g*Z_plus`. The Z values are same-sign, training-only empirical return magnitudes normalised to unit mean, with genuine zero outcomes retained in the non-negative component. Use one common date-weighted pooled shape per component in smoke; do not introduce unregistered cohort grids. Predictions may change component probabilities and scales, not borrow future residuals. Negative returns cannot be below −100%; apply that physical bound, recompute the distribution's implied p/g/ell/mu and report any discrepancy from the original heads. Use the actual resulting distribution consistently for calibration and path valuation. Extreme positive labels are not trimmed merely to improve stability.

For incumbents the fee kink is `r_star=b/(q*P0)−1`, not necessarily zero. Three moments do not determine its expected fee. Evaluate hold, trim and replacement value over the full component distributions. Under the inherited fee model, recovery of an underwater position towards basis can be fee-free while gains in a fresh replacement incur fees; report how much this preference drives retention. Add zero-performance-fee and zero-capital-allowance shadows separately.

No joint return distribution is inferred by pairing independent component draws. The base objective is additive expected terminal value and its common loss budget needs marginal distributions only. Same-vault partial actions share the same return draws. The probability that a full replacement outperforms holding requires a joint law; show it only where dependence is supported, otherwise show marginal cash-relative profit probabilities and label the replacement probability unidentifiable.

Use regularised logistic regression for p and ridge conditional magnitude fits, with predicted g floored at zero and ell bounded to [0,1]. P uses only support/risk inputs in each head; D adds performance inputs only to p; M also adds them to g/ell. This defines the quality baseline without arbitrary age-cell boundaries. Zero-frequency and one-class fits fall back to training-only pooled estimates; a training component with no positive empirical support cannot invent a positive magnitude from extrapolation. P includes the same support controls as D/M but no performance inputs; distinguish a completely constant prior in diagnostic tables. Model disagreement and unsupported tails are reported, not hidden by clipping outcomes.

Initial modelling budget: fixed feature set; L2 penalties `{0.1, 1, 10}` under one documented scaled-loss convention; no feature subset search. Fit monthly on expanding matured labels. Use at most three preceding chronological validation blocks with target overlap purged; if fewer than three supported blocks are available, use penalty 1 and mark selection unsupported. Use training-only scaling, missing-value handling and calibration. Conditional magnitude fits use economic loss on the original return scale; a robustness loss may be registered as a later sensitivity, not silently remove the extreme gains driving profitability.

### Support and cold-start contract

A personalised horizon head is supported only after at least six non-overlapping horizon-length calendar blocks contain matured labels, at least 30 distinct vaults contribute, and each required sign component occurs in at least three blocks. These are disclosed minimum-evidence conventions, not guarantees of forecasting power; report them and half/double-support diagnostic sensitivities. They do not exclude an individual young vault: it uses the supported common fit and missing masks or the pooled fallback. Do not require 300 observations or six 30-day blocks for a seven-day model just because such thresholds were suggested in review.

Before those fit conditions are met, use date-weighted pooled component distributions once at least one fully matured horizon block contains actual supported returns of both signs. Before even that minimal prior exists, the challenger retains cash, explicitly recorded as cold start. Never fabricate a loss distribution from an all-flat or no-label panel. Include the entire cold-start calendar in headline account metrics and paired profit comparisons; a secondary common-supported-date view may explain the training cost, but cannot replace the full-period verdict. Signal-only comparisons use matched supported origins, with coverage shown.

Training rows receive equal total weight per decision date. Report repeated-vault dependence and non-overlapping effective blocks. Select p by proper probability loss, magnitude heads by proper conditional prediction loss; evaluate whole-model utility on the prior validation folds. Do not tune a classifier using 2026 account profit or select solely on IC. Use calendar-block resampling for uncertainty and a blocked signal permutation with the whole fitting procedure rerun as a diagnostic.

Report Brier/base-rate skill, calibration, gain/loss magnitude error, rank IC as secondary, and predicted net profit versus realised outcome. At the actual admission margin show dollars rejected, avoided loss, missed positive profit and support. Strong volatility IC does **not** establish predictable negative returns or tail events; the conditional downside head must demonstrate its own skill.

## Stage 3 — allocation by marginal net value

### Portfolio objective and explicit risk budget

At each decision, let E be conservative current equity, w gross NAV exposures/E after proposed actions, and d_i the supported estimate of `E[max(−r_i,h,0)]` at the policy horizon. The initial risk proxy is:

`D(w) = sum_i w_i*d_i`.

For non-negative weights, `(sum_i w_i*r_i)^- <= sum_i w_i*(r_i)^-` pointwise under any dependence. Taking expectations gives the bound only when d_i are the true marginal expected downsides. Estimated or pooled d_i have **no guaranteed bound property**: D<=B constrains an estimate. D is pre-fee; the objective accounts for fees separately. It is **not** a volatility forecast, tail guarantee, CVaR estimate or maximum loss. It deliberately makes no diversification credit from unreliable sparse correlations. Report concentration and simultaneous loss stresses separately.

Maximise expected terminal net account value `E[V_h(a)]` subject to:

- Feasible cash, source execution restrictions and absolute account/TVL caps;
- Pinned/pending exposures retained and funded once;
- New actions may not create a breach of `D(w) <= B`. Breaches caused by marks, refits or pinned exposure are soft: forbid risk-increasing actions, allow risk-neutral/improving actions only when their path-value increment is positive, and report breach dates, size and duration. Do not force uneconomic sales merely because the estimate refreshed;
- No leverage and no mandatory position count or invested fraction.

Define the decision-time denominator `E = actual cash + sum(current fee-adjusted liquidation marks)`, using the same conservative liability convention for pinned holdings while keeping their unavailable proceeds out of cash. It is frozen during one target calculation; final executed caps must be rechecked against the actual post-trade accounting state.

This is a marginal-profit optimisation with a loss budget. **It does not assign weights proportional to inverse variance, inverse volatility or a score.** Risk changes the feasible trade-off; expected incremental value chooses the actions. No current C00 target is supplied to the challenger's sizing code.

This objective does not reward diversification by itself. Near-linear expected values can fill caps and produce corner solutions; when forecast means are similar and the loss budget binds, the priority may reduce to low-downside ordering. This is a possible result, not proof of a richer signal. Attribute realised breadth to forecasts, capacities, ties and the risk constraint. The budget-free D04 arm is essential. Cash is selected when incremental expected net value is non-positive or no feasible profitable action remains; a low win probability alone is not its criterion.

Use a single common P risk model for d across all challenger arms: `d_i = E_P[max(−r_i,h,0)] = p_i_P*ell_i_P`, computed from P's final bounded empirical distribution. Thus changing the profit forecast from P to D/M/C01 does not simultaneously change the risk constraint. D/M's personalised downside remains a diagnostic in smoke; using it in the budget is a later matched extension. P may use the common risk/support inputs but no performance-score inputs. Unsupported own histories use the common prior, not d=0. Reuse NB11's audited regularised/actual-interval risk feature, document its gap-scaling assumptions, and report the interval-only input sensitivity; do not add an unspecified second own/peer blend on top of P. Interval scaling is an assumption, not a reconstructed synchronous price path.

### Budget and uncertainty registration

For the fresh-2026 smoke, compute B once from the median C00 gross-weighted D over all decision dates in `[2024-01-01, 2026-01-01)`, using only information available at those decisions and the same risk fallback for unsupported holdings. Do not drop sparse names or dates to manufacture a favourable budget. Dates before any usable risk prior are flagged separately; if any such dates exist in this fixed window, the primary budget registration is unsupported and requires an explicit pre-result amendment rather than silently imputing zero or dropping dates. Freeze B for all 2026 arms. This supplies an interpretable comparable risk level without a time-varying C00 anchor. Report the pretraining sample, missing-date fraction, distribution and share of historical C00 decisions the resulting budget would have constrained. A zero median must be reported; do not silently replace it with an active-date median. If unsupported, explicitly amend/register an absolute budget before seeing challenger results; never select it using the realised 2026 risk or return.

For the long replay, establish B at the first cut meeting the six-block support contract, using all earlier C00 decisions since its first usable risk prior and the same fallback, then freeze it. Before that cut, use the pooled forecast with a provisional B updated from only already-observed C00 D values; if no usable prior/budget exists, retain cash. Label the earlier provisional-budget/cold-start phase. Do not apply the 2026 B to 2023. Report the separately established budgets; comparisons between periods are descriptive.

Primary action margin is zero beyond exact modelled costs. A model need not produce a statistically certain profit to participate. If the long-period provisional budget cannot be estimated, that is an explicitly labelled capital-allocation cold start, not a loss prediction for every vault. Block-bootstrap lower-bound/margin policies are a registered sensitivity, not a hidden gate that forces every young vault into cash. Report predicted uncertainty and unsupported decisions throughout.

### Executable greedy replacement contest

Use the same allocator for P/D/M and the calibrated-score control. Begin from actual holdings and cash. Generate feasible add, trim, close and paired replacement proposals on their **complete terminal path-value increment**, under the same horizon. A switch evaluates sale and purchase together. The denominator for a proposal's economic rate is the larger of gross capital sold and gross capital bought, not its arbitrary ticket count. Sell proposals start at the source executable sell threshold, which differs from the buy threshold.

Do not choose large proposals merely because they contain more dollars. Construct two deterministic feasible greedy candidates: one prioritises positive net gain per dollar of changed capital; the other prioritises positive net gain per incremental D when D increases. Risk-neutral or risk-reducing positive-gain actions use the dollar priority rather than divide by zero/negative D. Both obey cash, caps and the soft-breach rule at every step. Keep the final feasible candidate with the higher exact expected terminal value, including no-trade and cash-target alternatives evaluated from the actual initial account. This is an explicit approximation for multiple binding resources, not a claimed fractional-knapsack optimum.

Ties within numerical tolerance split equally in dollars subject to each name's feasibility/caps, with canonical address used only for indivisible residuals. Report dollars determined by ties. Do not let an all-prior forecast choose a concentrated basket purely by address ordering.

Numerical grid starts from executable buy/sell minimums, full-close points, fee/basis kinks and capacity breakpoints. Refine candidate intervals and halve their widths until the improvement in expected terminal value is below USD 1 and target gross-dollar L1 change below USD 10, or a predeclared 12 refinements are reached. These are numerical tolerances, not admission thresholds; report non-convergence and one tighter same-state check. No global optimality claim follows. Add a same-state continuous piecewise-linear optimisation bound on a small representative set of decisions if supported by the existing solver; this is a solver-quality diagnostic, not another strategy arm.

Iterations are hypothetical. Consolidate into **one final net action vector**, and calculate actual fees/basis/cash once. Suppress non-executable sells first, freeze the executable sell set, then recompute net available proceeds. Perform one buy-only residual allocation pass without proposing new sells. If final cap/accounting checks fail, reduce buys deterministically until feasible and record the utility lost. Never charge per numerical ticket or spend suppressed-sale proceeds. Record intended, projected and executed dollars, utility, both passes and any residual infeasibility. Pinned holdings remain present throughout.

Monitor execution activation, number of holdings, concentration, risk-budget usage, cash and turnover. Compare desired weights with matched-date C00 inverse-variance targets using rank correlation, absolute weight distance and support overlap. Similar weights are evidence of limited structural novelty; they are not automatic grounds to discard an economically informative result using an arbitrary correlation cutoff.

## Stage 4 — ten full-calendar smoke arms

The table is the registered starting surface. Every row covers all of 2026, includes prior warmup, and uses the same accounting and operational universe except where explicitly stated.

| ID | Signal | Construction / intervention | Main comparison |
| --- | --- | --- | --- |
| B00 | Exact C00 | NB20 source rules | Economic benchmark |
| B01 | Exact v11 | NB20 source rules | Deployed-rule comparison |
| F01 | Exact C00 | Sell band 1% instead of 0.5%; buys unchanged; corrected final proceeds | Forecast-free fee/churn alternative; inherited inverse variance is confined to this control |
| P00 | Support prior P | Marginal-value contest, adaptive count/cash, common loss budget | New construction without personalised performance predictions |
| D00 | Conditional downside D | Same contest and budget | Value of predicting loss probability, versus P00 |
| M00 | Conditional magnitudes M | Same contest and budget | Added value of personalised gain/loss magnitudes, versus D00 |
| C01 | Calibrated frozen C00 score plus the same support inputs | Same contest and budget | Do the new inputs beat calibration of the score we already had? |
| D02 | D | D00 with a maximum of six simultaneously held vaults | Effect of the fixed position ceiling; pins counted explicitly |
| D03 | D | D00 entry-only: permit new money/top-ups, no discretionary incumbent reductions/replacements | Does active management of held capital help? |
| D04 | D | D00 without aggregate D budget; account/TVL caps still apply | Cost/benefit of the conservative loss budget |

F01's 1% is one disclosed factor-of-two local check, not a tuned optimum. C01 uses the same distribution/regularisation machinery as D: replace the five performance inputs in the probability head with C00's frozen scalar score; keep the P support-only magnitude heads. Unscored rows retain a missing flag and support fallback. No C00 allocation weights enter C01. Compare C01 versus P00 for the old score's predictive content and D00 versus C01 for incremental signal content.

Do not reinstate the C00 risk-sizing formula in P00–D04. D03 retains mandatory operational exits and frozen inherited dust handling, documented before execution; otherwise retained holdings may consume all capital. D02 counts pinned names, cannot force an impossible redemption, and must report any inherited excess over six.

All arms run even if a forecast has low IC; account effects are the question. Unsupported dates must use the documented prior, not disappear. If a model cannot be fitted at all, show its fallback-equivalence result explicitly rather than presenting it as a distinct learned policy.

### Bounded expansion after smoke

Replay at most three distinct challengers plus B00/B01 over full history, selected by paired net profit, risk, activation and contributor stability. Preserve rejected smoke rows. Pre-register the selection explanation before looking at long results; do not use long results to retune 2026.

Then permit at most five additional 2026 engine comparisons around D00: B at half and twice its primary value; the matched seven-day horizon with its own causally registered budget; a one-block-standard-error action margin; and restoration of the source 14-day investment gate with its original entry/retention semantics. The horizon arm changes labels, fits and risk-budget calibration together and is labelled a horizon package. The margin arm uses calendar-block bootstrap uncertainty of expected path-value differences, including cash versus hold; the base remains zero margin. If D00 is entirely fallback-equivalent, run these on P00 and label that substitution. Cost sensitivities begin as diagnostics; any cost change used to support a strategy claim requires a full stateful rerun and comparison under identical changed costs for both challenger and B00. No unlimited cross product.

## Independent alternatives retained for later work

These ideas are not silently added to the first smoke.

1. **Joint scenario CVaR allocation.** Useful only after verifying enough joint actual-observation support. Objective `E[V_h]/E − lambda*CVaR_alpha(loss)` with fees already inside V; `CVaR_alpha=min_eta[eta+E[(loss−eta)+]/(1−alpha)]`. Shared-date dependencies, missing-cell imputation assumptions and effective tail observations must be audited. Independently resampled vault residuals cannot pretend to preserve correlation. Compare against the simple loss-budget policy at matched ex-ante risk; do not assume a sophisticated tail estimator is superior.
2. **Pairwise switch-advantage learning.** Predict the same-horizon net value of holding i versus replacing it with feasible j. Cash is an explicit alternative. This may learn relative opportunity cost more easily than precise absolute means, but must not multiply correlated pairs into fictitious sample size or learn from only past chosen trades.
3. **Reporting/liquidity hazard.** Model inability to obtain an actual mark or redeem separately from financial loss. Use it to price capital lock-up, not label missing returns as disasters. Requires enough historical permission observations.
4. **Capacity-aware retention.** Penalise rotations that sell a worthwhile holding but cannot fund a feasible profitable replacement. The main contest already addresses one-step versions; multi-step reservation is deferred until actual rotation episodes show value.
5. **Regime-conditioned cash policy.** Optional portfolio-level state model after an economic signal is established. BTC/ETH relationship signs must be measured; the strongest 2026 vault gains occurred while those references fell. No arbitrary market-risk dial in smoke.

## Results and chart specification

All tables/charts need **subheading, short purpose description, element**. Each chart title names the backtesting period and any forecast horizon. Default 2026, separate full-history section. Every image separate; no collages. Colour outcome tables as in existing notebooks. Save static outputs and visually inspect all charts.

1. **Control economics:** the Stage 0 fees, liabilities and holding-duration/PnL tables first. These explain which actions could plausibly improve profit.
2. **Rules comparison:** one narrative table with signal, eligibility, allocation objective, slot policy, cash policy, exits, loss budget and costs.
3. **Support:** origins/vaults, actual updates, training maturity, censoring, missing/young groups and effective time blocks. Include label-resolution rate by reporting frequency and permission-coverage eras.
4. **Signal charts:** separate predicted-versus-realised net return scatter for each model/horizon, quarter-coloured points, zero-profit line, support-aware binned means and uncertainty; separate loss-probability reliability plots. Show P/D/M side-by-side metric tables. No trend line interpreted as predictive proof on overlapping rows.
5. **Economic decisions:** predicted marginal net gain against realised same-horizon action opportunity, actual accepted/rejected dollars, false vetoes, avoided loss and missed gains. Report probability of a negative fresh/hold-over-cash outcome from each marginal distribution; do not report switch-versus-hold probability from independent vault draws as if dependence were known. Same-state counterfactuals are labelled; they are not substitute account paths.
6. **Portfolio outcomes:** key metrics side by side, common equity curve, separate absolute asset weights including cash, actual position count/effective breadth, quarterly PnL, drawdown, turnover and fees. Include mean/September cash and paired net dollar difference against C00.
7. **Constraints and opportunity costs:** permission/capacity/budget/minimum/cash/non-positive gain reasons, desired/projected/executed allocations, missed replacement funding, locked capital and September examples.
8. **Robustness:** paired calendar-block uncertainty (descriptive when blocks are few), quarters and permission eras, contributors, best-update observation intervals, curator/BTC/ETH context, fixed-ledger contributor removal clearly labelled, same-state capacity/bankroll shadows, and 50%/100% largest/related-vault loss stresses. A fixed-ledger deletion is not a causal no-vault replay.
9. **Conclusions:** hypothesis verdicts, where profit changed, support and sensitivity limitations, whether improvement survives costs/concentration, and next leads. Update `summary.md` after execution.

Report historical improvement separately from statistical evidence. All-cash safety is not an economic win unless it meets the profit goal under the declared comparison. A small gain due to one vault, quarter or fee assumption is a lead, not a robust superiority claim.

## Implementation order and acceptance criteria

1. Freeze identities and reproduce complete NB20 control daily equity/trade signatures. Show both fees and gross/net reconciliation.
2. Complete the holding/support audit and lock horizon, feature registry, training protocol, budget and numerical tolerances in a manifest **before challenger results**.
3. Build the causal panel. Fixtures must cover forward fill without future backfill, actual unchanged versus carried prices, label maturity, missing=True, zero-class/young-vault fallbacks, permission clocks and missing risk.
4. Check path-value maths against engine buy/hold/partial sell/top-up/full switch examples, including reopened tax reset, actual basis, pinned funds and gross-versus-marked caps. These implementation checks are part of the authorised future experiment.
5. Fit P/D/M chronologically. Persist train-through times, transformations, penalties, class support and fallback reasons per forecast. No future labels in training, validation or bootstrap.
6. Implement the contest with conservation, no-trade feasibility, deterministic ordering, ticket-grid refinement and projection checks. Confirm no hidden inverse-risk conversion or fixed six slots.
7. Execute the ten full-2026 arms using the observable notebook runner. Save after accounts/cells; retain all arms. Audit actual activation before explaining performance.
8. Run only the registered shortlist/extensions; inspect all charts and write findings. Do not overwrite previous experiments or add uncontrolled searches.

## Assumptions and unresolved choices made visible

| Choice | Status and reason | Required evidence or sensitivity |
| --- | --- | --- |
| 30-day primary planning horizon; 2/7/30 diagnostics | Provisional; count-weighted four-day evidence is insufficient | Capital/PnL spell audit, same-horizon comparisons, seven-day policy extension |
| Two-day decisions; monthly fits | Comparable with source and manageable | Record actual fit/decision timestamps; not claimed optimal |
| Forward-filled metrics; actual-endpoint learning labels | Sparse metrics must work without inventing resolved outcomes | Engine-mark label sensitivity, attrition and reporting-bias analysis |
| Five performance inputs plus risk/support controls | Small initial modelling scope | Not a permanent formula limit; mean/probability ablation first |
| Penalties 0.1/1/10; three validation blocks | Declared small regularisation screen | Scaling convention and unsupported-fit fallback explicit |
| TVL floor, 33% caps, historical guard | Inherited comparability conventions | Binding rates, 20/33/50% and bankroll shadows; retrospective universe caveat |
| Zero cash yield and inherited redemption model | Matches NB20 | Isolate 0.1% allowance and profit-fee assumptions; no duplicated NAV fees or invented slippage |
| Conservative sum-of-downsides budget | Avoids false diversification from sparse overlap | Not a tail guarantee; common risk model, budget-free and half/double comparisons |
| Pre-2026 C00 median risk budget | Comparison reference, frozen rather than dynamic anchor | Support and cold-start treatment; not a validated risk tolerance |
| Zero primary uncertainty margin | Avoid unnecessary all-cash result from weak data | One-standard-error policy plus missed-gain accounting |
| Greedy optimisation and ticket discretisation | Explicit multi-resource approximation | Dollar/risk priorities, equal-dollar ties, no-trade alternatives, numerical refinement and execution audit |
| Corner solutions and inverse-risk ordering | Possible with similar expected means and binding budget | Cap/tie/budget attribution; D04 and target-similarity diagnostics |
| Soft risk-budget breaches | Avoid mechanical loss-inducing trades on an estimate refresh | Report excess duration/magnitude; D03 has no forced discretionary sales |
| Support minima and cold starts | Declared evidence rules, not individual-vault exclusions | Include cash phase in headline metrics; report fallback equivalence and support sensitivities |
| Monthly fits with delayed labels | Can lag changing conditions by 30–60 days at a 30-day horizon | Current features still update each decision; report training maturity and regime calibration |
| Reporting or permission gaps | Separate from proven losses | No automatic disaster labels or universal new stale-data bans |
| Historical evaluation and repeated research | No untouched holdout | Causal fitting cannot remove research-selection bias; later prospective validation needed |

## Implementation amendments recorded on 13 October 2026

The primary experiment retains ten smoke rows and the registered three-candidate construction shortlist. The following implementation decisions make the reviewable scope explicit:

- Regularisation is selected once per horizon/calendar year from three preceding purged folds, then coefficients refit monthly. Probability and magnitude penalties use mean-loss scaling; gain/loss conditioning retains the full date-weight measure. Independent fixtures check duplicate invariance and coherent mixture means.
- A non-positive extrapolated conditional magnitude borrows its training conditional prior, with a recorded fallback flag. Missing histories do not become zero-loss predictions.
- The margin extension measures a common calibration-error shock from matured previous forecasts. It is not full uncertainty about every personalised coefficient or an identified joint replacement probability.
- Gap-adjusted risk is examined as a matched signal-only input sensitivity, with primary targets and penalties fixed. No extra allocation search is introduced.
- The sole positive fee-control smoke result, F01, also receives a full-history control replay. This is one additional diagnostic control beyond the three construction challengers, not a new formula or tuned setting.
- Source controls receive independent complete equity and trade-signature parity checks. Raw cash, exit opportunities, selected-basket calibration, pinning and protocol capacity are audited. Protocol TVL/headroom remains fixed in bankroll shadows.

- The original feature calendar and the long engine calendar differed by one day before 2026. The implementation now creates explicit same-date predictions at every C00 engine decision origin, without shifting future forecasts backwards. Additional prediction origins keep the original causal training sample fixed. Calendar coverage is asserted before account replay; the three adaptive long accounts are rerun. Exact short forecasts and empirical distribution shapes must match before any short-account cache is reused.

- Supported learning outcomes must also have matured before the archive ends. An observation less than 24 hours old cannot resolve a target whose horizon has not yet elapsed. This archive-end censorship affects diagnostics, not forecasts available to account decisions.
