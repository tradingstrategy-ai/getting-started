# Hyperliquid vault strategy experiments

Research notes for **NB01–NB23**, updated **14 October 2026**. Each experiment below records its question, hypothesis, measured outcome, verdict and useful follow-up. References point to the saved notebooks and detailed analyses; the scatter catalogues are presentation appendices of NB08 and NB09, rather than additional experiments.

Here, a hypothesis is the experiment's testable research proposition, with inferred propositions identified as such. Confirmation or rejection refers to the specified treatment on the evaluated history; it does not establish a universal rule or unseen-time superiority.

## Periods, data and interpretation

The default reporting period is **1 January–4 October 2026 inclusive**, written in code as `[2026-01-01, 2026-10-05)` in naive UTC. The secondary full-history portfolio period is **1 March 2023–4 October 2026 inclusive**, with a fresh $150,000 start. Full-history runs include the early cash-only warm-up and overlap the 2026 period. They provide another view of the same inspected history, rather than independent confirmation.

NB13–NB23 extend the full-history portfolio period through **7 October 2026**, written as `[2023-03-01, 2026-10-08)`, with a partial final archive day. Their fresh-2026 comparison retains the default period above. Each experiment labels its actual reporting boundaries.

The [sparse NAV audit](sparse-nav-rerun-2026-10-10.md) records metric coverage, all affected calculations and the in-place rerun policy.

NB01–NB07 rebalance every **two days**. NB08 forecasts every **four days** and retains two-day decisions for its portfolio treatments. NB09 forecasts every **four days**, refits monthly on strictly matured labels, and runs no portfolio strategy. NB10 and NB11 construct independent fixed-unit baskets every four days and run no strategy engine. NB08, NB09 and the original NB10 evaluate 7-, 30- and 90-day outcomes; the expanded NB10 smoke evaluates 30 days; the effective evaluation samples are shorter than the reporting period because future labels must mature.

The selected universe is **514 Hyperliquid/HyperCore vaults** on chain 9999, with three additional supporting pairs in the cached universe. This is the maximum selected vault inventory, not the number eligible or observed at every decision. The selection is a policy snapshot, with historical membership and permission-clock limitations. NB09 finds 101 of 615 already archived addresses outside that selected universe by October.

Current portfolio figures use the **7 October restored publication and merged readers**. Older figures inside historical sections of analysis files are superseded. The early NB01–NB17 source v11 reference returns **41.20% CAGR, 1.96 Sharpe and −6.40% drawdown**, compared with the earlier saved 41.59% reference. Under the later shared accounting corrections in NB20/NB23, v11 returns **49.15% CAGR, 2.214 Sharpe and −6.41% drawdown**; C00 returns **58.59%, 2.474 and −6.36%**. These accounting generations must be compared within their matched experiments. [README.md](README.md) gives the complete index and current common-accounting comparison. Matching source and research controls reproduce complete equity paths and trade ledgers on identical inputs. The remaining $407.83 difference against the older publication is reconciled to prices, holdings and cash in the [restored-data report](restored-data-rerun-2026-10-07.md).

Portfolio replays retain the source strategy's modelled 10% charge on positive redemption profit and 10bp gross redemption friction, including estimated exit costs on open holdings. These are inherited assumptions, rather than newly established live charges. Current guards apply retrospectively; recorded deposit-state coverage starts on 11 April 2026 and earlier decisions assume deposits open. Forecast labels measure vault NAV outcomes and do not include portfolio execution costs. All metric families support sparse positive NAV histories using causal forward filling on a daily calendar. NB01–NB07 already obtain filled candles from the source universe. NB08/NB09 were amended and rerun on 10 October to remove their overly strict complete-observation requirement. Actual observations, their counts and ages remain separate from carried prices. There is no backfill before the first mark; future labels remain censored beyond the last actual vault observation/archive end. Fixed lookbacks require enough elapsed history, and mathematically undefined flat-path ratios remain missing.

### Selected portfolio comparisons — 1 January–4 October 2026

These rows identify the reference, unsuccessful allocation treatments and candidates carried into later experiments. They are measured replays, not a ranking of independently validated strategies. Drawdown is signed; nearer zero is better.

| Experiment and configuration | Maximum positions | CAGR | Sharpe | Maximum drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: | ---: |
| NB01: source v11 | 6 | 41.20% | 1.96 | −6.40% | 8.83% |
| NB02: original-request dollar cap | 6 | 9.31% | 1.31 | −4.22% | 51.32% |
| NB03: correlation-aware risk budget, parent redistribution | 6 | 35.52% | 1.62 | −7.84% | 10.45% |
| NB04/NB05: Blend 46d | 6 | 41.38% | 2.12 | −4.85% | 7.43% |
| NB05: feasible entrants | 6 | 41.83% | 1.99 | −6.39% | 8.83% |
| NB06/NB07/NB08: four-input focal score | 6 | 51.77% | 2.30 | −6.35% | 10.18% |
| NB07/NB08: Blend 46d | 7 | 47.93% | 2.46 | −4.71% | 5.03% |

## NB01 — source v11 replication

[Notebook](01-initial.ipynb). Starting point: `hyper-ai-v11.py` from the strategies repository, a variant of the earlier v6 rules. Hyperliquid vault-only universe; two-day decisions; six maximum positions; short and full-history periods as defined above.

### What was being examined

Establish a reproducible source-strategy reference with comparable metrics, equity curves, absolute vault/cash holdings and quarterly returns. Ranking combines 60% 360-day CAGR and 40% source-compatible 45-day Sortino, clipped at 100% CAGR and Sortino 3, with missing-score behaviour and a strict 14-day return gate greater than −16%. Sizing uses 90-day inverse variance with a 0.0001 daily volatility floor, a 98% fresh allocation budget and 33% concentration/TVL limits. Minimum vault TVL is $7,500; residual capacity extensions are disabled at six assets. Entry/exit score comparisons use ranks six/eight, while refill can scan the full eligible list to fill six slots. The source buy/sell bands are 0.05%/0.5% of reference equity with a $5 minimum, plus 0.5% tiny-position cleanup.

### Was there a hypothesis?

The technical hypothesis was that the notebook could reproduce the source implementation when period, initial state, data, guards and accounting matched. It was a baseline exercise, with no claim that v11 was the optimal strategy.

### What was the result?

The current 2026 source replay ends at **$194,520.81**, with **41.20% CAGR, 1.96 Sharpe, −6.40% drawdown and 581 trades**. Full history ends at **$254,103.35**, with **15.77% CAGR, 1.24 Sharpe and −7.92% drawdown**. Its requested March start aligns to a cash-only engine snapshot on 28 February 2023, with the first trade on 31 May 2023. Later exact-formula controls match its full equity and trade paths in both periods. Restoring missing archived leader-share/cap values recovered most of the earlier benchmark gap; comparisons with an older publication retain small, reconciled differences.

### Was the hypothesis confirmed or rejected, and why?

**Confirmed for implementation parity on identical inputs.** Matching an older archive to the dollar is a separate question, because publication differences change executions and marks. The lower full-history annualised return also includes a much longer warm-up and cannot be compared directly with the 2026 CAGR as evidence of a strategy defect.

### What useful new leads did we learn?

Keep this exact control in every experiment, match costs and starting state, and investigate input/ledger differences before attributing a gap to strategy logic. Report cash, capacity and contributor concentration alongside headline returns. A trusted reference makes later scoring, weighting and selection changes interpretable.

## NB02 — accepted-dollar caps

[Notebook](02-backtest-accepted-dollar-cap.ipynb) · [analysis](02-accepted-dollar-cap-analysis.md). Derived from NB01; identical scoring and six-position, two-day portfolio machinery, with a changed allocation rule.

### What was being examined

Cap each vault's accepted allocation at its initial requested dollars, as well as the existing concentration and TVL limits. The parent redistributes rejected capacity through the remaining basket; the treatment leaves those dollars in cash. This portfolio allocation cap is separate from archived deposit-admission caps.

### Was there a hypothesis?

The proposed rule would prevent redistribution from increasing a vault beyond its initial risk-weighted request, potentially improving allocation discipline or risk. A follow-up question was whether underperformance came from incorrect parameters, idle cash, or changed allocation proportions.

### What was the result?

The cap returns **9.31% CAGR, 1.31 Sharpe and −4.22% drawdown** in 2026, versus the source's **41.20%, 1.96 and −6.40%**. Mean cash rises from **8.83% to 51.32%**. Full-history cap CAGR is **2.08%**, Sharpe **0.35**, and drawdown **−7.92%**. The target checks confirm that accepted/final targets respect the original request; the parameter investigation found no percentage, volatility exponent or budget-unit error.

Near-flat vaults can dominate initial inverse-variance weights and then accept little capital because of TVL limits. With redistribution disabled, other selected vaults retain tiny requests, sometimes below trade/cleanup thresholds. The current cash-matched parent gives **19.43% CAGR, 1.92 Sharpe and −3.38% drawdown**, with **50.14% mean cash** in 2026, outperforming the cap at similar average deployment. Full-history cash-matched results are **3.93% CAGR and 0.60 Sharpe**. This control matches decision-time accepted totals on its own state, rather than matching exact realised cash/trade paths; it shows that allocation proportions also matter without an additive cash-versus-weighting decomposition. Caps constrain desired targets, while unchanged sell bands allow realised holdings to remain temporarily above them.

### Was the hypothesis confirmed or rejected, and why?

**Correct implementation confirmed; performance improvement rejected for this fixed rule and parameter set.** Reduced drawdown accompanies much lower exposure and does not compensate for the return and Sharpe loss. The cap's interaction with inverse variance, capacity and minimum positions explains the result more convincingly than an accidental parameter error.

### What useful new leads did we learn?

Analyse requested weights, accepted dollars and realised holdings separately. Test flatter weights under the same caps before relaxing risk limits, and isolate cleanup thresholds from allocation changes. NB03 follows this lead; simply increasing deployment or concentration is not justified by NB02.

## NB03 — alternative position weighting

[Notebook](03-backtest-alternative-weighting.ipynb) · [analysis](03-alternative-weighting-analysis.md). Derived from NB01 and NB02; two-day decisions and six positions, with each weighting method evaluated under both allocation rules and both periods.

### What was being examined

Compare original inverse variance with four fixed alternatives: 50/50 inverse volatility plus equal weights, equal weights, regularised inverse volatility, and a correlation-aware risk budget. The intervention replaces weights after the source selects its basket. Capacity, concentration, admission and execution rules still affect the accepted portfolio.

### Was there a hypothesis?

Flatter or regularised weights could reduce domination by near-flat vaults and make the dollar-cap allocator more productive. Correlation-aware risk budgets might improve diversification beyond considering each vault's volatility separately.

### What was the result?

All **20** short/full executions completed. Under parent redistribution, alternative 2026 CAGRs are **34.28%, 35.01%, 35.43% and 35.52%**, all below original inverse variance's **41.20%**; their Sharpes are also lower. Under the dollar cap, the alternatives improve CAGR to **24.93%, 30.10%, 17.40% and 19.30%**, versus **9.31%** for capped inverse variance. Equal weights give the strongest capped short-period result: **30.10% CAGR, 1.51 Sharpe and −9.35% drawdown**.

Over full history, redistributed inverse variance gives **15.77% CAGR and 1.24 Sharpe**, versus **14.98% and 1.14** for regularised inverse volatility, the strongest alternative by Sharpe. Capped equal weights give **11.49% CAGR, 0.98 Sharpe and −9.29% drawdown**, versus **2.08%, 0.35 and −7.92%** for the original cap. The baseline alternatives preserve the same selected core on every recorded sizing date, while evolving cap portfolios can later select different baskets. Requested equal risk budgets are also distorted after allocation constraints. These are whole-policy comparisons: regularisation changes more than the inverse-volatility exponent.

### Was the hypothesis confirmed or rejected, and why?

**Partly confirmed for repairing the cap interaction; not confirmed as a replacement for the parent.** Flatter weights materially improve capped deployment and returns, but no tested alternative beats the original parent Sharpe in either period. Solving one allocator's weakness does not establish a generally better sizing method.

### What useful new leads did we learn?

Retain inverse variance as the portfolio reference. Separate plain inverse volatility, volatility-floor changes and shrinkage before introducing more combined policies. Evaluate diversification and risk contributions after capacity/admission constraints, and distinguish sizing effects from changed future basket selection.

## NB04 — metric/window score matrices

[Notebook](04-opt-score-matrix.ipynb) · [analysis](04-score-matrix-analysis.md). Derived from the source baseline and both allocators. Selection remains the source machinery; the experiment changes ranking scores, sizing and missingness options.

### What was being examined

Combine CAGR, Sharpe, Sortino, maximum drawdown and Calmar over nine windows into a score matrix. Search sparse supports, fit CAGR and Sharpe objectives separately, blend their scores at 50/50 or 60/40, and examine compression to fewer inputs. Compare 4/6/10 positions, equal/score-proportional/inverse-variance sizing, missing flags and clipping profiles. Exact 360/45 and near-source 360/46 controls distinguish machinery changes from a one-day window change.

### Was there a hypothesis?

A metric/window matrix might improve the fixed hand-picked formula, and a small number of weights might capture most of any benefit. Clipping, missingness and position sizing were expected to matter; the search did not isolate all of them into a single causal comparison.

### What was the result?

The sparse CAGR and Sharpe fits retain **60% 360-day CAGR and 40% 46-day Sortino**, but choose different clipping profiles. Blending the scores therefore changes ranking despite identical coefficient matrices. Exact 360/45 reproduces the source; near-source 360/46 returns **40.58% CAGR, 1.94 Sharpe and −6.70% drawdown**.

The highest distinct 2026 grid CAGR is the six-position, inverse-variance, missing=True **50/50 clipping blend**: **41.38% CAGR, 2.12 Sharpe and −4.85% drawdown**. Only one distinct grid configuration improves all three headline metrics against v11 in 2026. Its full-history result is **15.42% CAGR, 1.24 Sharpe and −8.51% drawdown**, below the source's full-history return/drawdown combination. Full-history grid maxima reach 18.77% CAGR but incur −13.33% drawdown and weaker 2026 returns.

Clipped same-window CAGR/Sharpe correlations are **0.89–0.92**. Calmar cap changes cannot test Calmar's usefulness when its coefficient is zero. The sparse search explored limited three/four-input proposals; its two-input result was not evidence that additional inputs cannot help.

### Was the hypothesis confirmed or rejected, and why?

**A consistently better replacement was not established.** A promising short-period risk/return trade-off emerged, but it did not dominate full history. Exact source parity was confirmed, and clipping/sizing/missingness materially affected results. Full-history fitting includes 2026, so the short replay is not independent validation of the selected matrix.

### What useful new leads did we learn?

Separate score calibration from sizing and selection in subsequent experiments. Test more three/four-input supports while holding other rules fixed, and measure saturation, missingness and actual ranking differences rather than counting coefficients. NB05 isolates calibration/selection/cash mechanisms; NB06 expands the input-count comparison.

## NB05 — clipping, selection and cash deployment

[Notebook](05-opt-score-calibration-selection-cash.ipynb) · [analysis](05-opt-score-calibration-selection-cash.md). Derived from NB04; six positions, two-day decisions and 90-day inverse variance remain the reference.

### What was being examined

Test hard versus smooth score calibration, clipping blends, feasible-entry selection, replacement hurdles, tie ordering and residual cash refill. Add feature/future-outcome diagnostics and trade-level concentration attribution. The experiment separates ranking changes from selector and allocator interventions.

### Was there a hypothesis?

Less saturated scores might rank vaults better; screening infeasible entrants and requiring a replacement advantage might avoid wasted decisions and churn. Redistributing residual budget after admission checks might improve returns by deploying more cash.

### What was the result?

The experiment completes **18 score calibrations, 11 mechanism diagnostics and six full-history confirmations**. Feasible entrants produce **41.83% CAGR, 1.99 Sharpe and −6.39% drawdown** in 2026, and **15.87% CAGR, 1.25 Sharpe and −7.92% drawdown** over full history. They prevent a deposit-ineligible entrant's score from displacing an incumbent. The 0.05 replacement hurdle gives **41.78% CAGR**, a similarly small improvement, whereas 0.025 falls to **37.95%**. Blend 46d returns **41.38% CAGR, 2.12 Sharpe and −4.85% drawdown**, while Smooth C1 S3 falls to **31.64%, 1.65 and −5.28%**.

Refill reduces source mean cash only from **8.83% to 8.40%**, and CAGR falls to **39.56%**. Blend refill similarly reduces cash slightly but lowers CAGR to **40.00%**; both also underperform their controls over full history. Clipping creates many ties: **39.1%** of baseline funded observations have maximum score, and **63.3%** of decisions fund at least two such vaults. Requiring ten non-flat returns lowers CAGR to **27.39%**; this does not establish that flat marks are wrong or that the tested activity cutoff is useful. Two-day-origin feature diagnostics examine 14/30/60-day future outcomes; promising longer-window ratios often have small, changing cohorts. Source profits remain concentrated in Realist Capital and a small number of large moves.

### Was the hypothesis confirmed or rejected, and why?

**Feasibility screening receives modest replay support; smoothing and the tested refill rule do not.** The cash reduction is small and does not improve profitability. A blend provides stronger 2026 risk metrics but does not dominate full history. Ties are a demonstrated mechanism worth investigating, not proof that every smoother transform will improve selection.

### What useful new leads did we learn?

Carry feasible-entry screening forward as a small controlled change. Investigate actual marginal entrants, tie sensitivity and the reason each dollar remains cash before changing allocation. Track leading-vault/best-day sensitivities alongside performance, and use strict future targets to assess features separately from profitable portfolio paths.

## NB06 — three and four scoring inputs

[Notebook](06-opt-score-3-4-inputs.ipynb) · [analysis](06-score-3-4-inputs-analysis.md). Derived from NB04/NB05, with source selection, six positions, two-day decisions, inverse-variance sizing and parent redistribution held fixed.

### What was being examined

Compare **74 configurations**: two two-input controls, 36 three-input and 36 four-input recipes. Added inputs receive 20% total score mass: 48/32/20 coefficients for three inputs, or 48/32/10/10 for four. An input is a metric/window pair, so four inputs need not be four distinct metrics. Matched controls collapse extra windows while preserving total metric weights.

### Was there a hypothesis?

Meaningful additional windows or metrics might improve the two-input core. The matched controls test whether any gain exceeds the effect of merely changing the total CAGR/Sortino balance.

### What was the result?

The balanced four-input candidate uses **48% 360-day CAGR + 32% source-compatible 45-day Sortino + 10% 180-day CAGR + 10% 30-day Sortino**, with legacy CAGR 100% and Sortino 3 clips. It produces **51.77% CAGR, 2.30 Sharpe and −6.35% drawdown** in 2026; full-history figures are **22.05%, 1.62 and −8.08%**. Collapsing its extra windows into a two-input 58/42 control reduces CAGR to **41.89%** in 2026 and **15.85%** over full history, with Sharpes **1.99 and 1.24**.

The descriptive 2026 CAGR maxima reach **51.99%** with three inputs and **52.30%** with four, but with worse drawdown than the balanced candidate. Only one of 72 added-input configurations jointly improves CAGR, Sharpe and drawdown against v11. The winning four-input recipe still uses only two metrics, and its 30-day Sortino is saturated on **79.0% of requested target dollars**. Realist Capital contributes **38.4%** of positive 2026 vault profits.

### Was the hypothesis confirmed or rejected, and why?

**Provisionally supported within the replay; independent predictive superiority remains unconfirmed.** The matched-weight ablation supports a benefit from extra windows beyond metric balance alone. However, the winning support was selected from inspected history, full-history drawdown is slightly worse than v11, and clipping reduces independent information. NB08 later finds no clear broad ranking advantage for the four-input score.

### What useful new leads did we learn?

Freeze the 48/32/10/10 candidate against strong two-input controls and evaluate subsequent periods. Examine coefficients and clipping around this support using chronological validation, not another winner selection from the same sample. Measure input activity, basket ranking and contributor dependence; NB07 tests whether the benefit survives wider portfolios.

## NB07 — portfolio breadth

[Notebook](07-opt-score-position-count.ipynb) · [analysis](07-score-position-count-analysis.md). Derived from NB06; repeats all 74 frozen scores with 6, 7, 8 and 10 positions, completing **296 configurations per period**.

### What was being examined

Whether wider baskets improve diversification, cash deployment or returns. Sizing and scoring remain fixed, but maximum positions and entry rank become N, while exit rank becomes N+2. The intervention therefore changes retention/entry thresholds as well as breadth.

### Was there a hypothesis?

The notebook asks whether wider portfolios help without assuming they will. The inferred hypothesis is that additional eligible vaults could reduce cash and improve diversification while preserving the profitable core.

### What was the result?

For the focal four-input score, widening substantially worsens performance despite deploying more cash.

#### Focal four-input breadth — 1 January–4 October 2026

Each row keeps the score and sizing method fixed and changes N with its associated rank limits. Lower cash does not imply better capital use.

| Maximum positions | CAGR | Sharpe | Maximum drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: |
| 6 | 51.77% | 2.30 | −6.35% | 10.18% |
| 7 | 30.85% | 1.58 | −6.42% | 6.21% |
| 8 | 16.24% | 1.04 | −6.57% | 4.35% |
| 10 | −3.01% | −0.28 | −6.79% | 2.83% |

The same ordering holds over full history: CAGR falls from **22.05% to 17.30%, 14.88% and 8.49%**, while ten-position drawdown reaches **−17.42%**. Much of the loss comes from changed allocations/timing in shared vaults, rather than only losses in newly added names. At ten positions, shared-vault changes explain **$58,491 of the $59,004** equity deterioration versus six.

A useful alternative is **two-input Blend 46d at seven positions**: **47.93% CAGR, 2.46 Sharpe and −4.71% drawdown** in 2026; full-history figures are **18.40%, 1.39 and −8.08%**. It improves its own six-position blend control in both periods.

### Was the hypothesis confirmed or rejected, and why?

**Rejected for the frozen four-input focal strategy.** Less cash coincides with lower return and Sharpe and worse drawdown in both periods. Some other supports benefit from widening, so there is no universal optimum established. The seven-position blend is a second candidate requiring independent validation; breadth and rank-limit effects remain coupled.

### What useful new leads did we learn?

Keep six positions for the focal score and treat the seven-position blend as a distinct candidate. Isolate future tests of breadth from entry/exit hysteresis, and examine how marginal additions alter profitable core allocations. Admission research should focus on the actual last-slot entrants; NB08 addresses that question.

## NB08 — scores, forward forecasts and admission floors

[Notebook](08-research-score-forecast-thresholds.ipynb) · [findings](08-score-forecast-findings.md). Derived from NB04–NB07 scoring recipes. Forecast every four days over 7/30/90 days; portfolio treatments use two-day decisions and six or seven positions. Sparse-data corrections supersede the earlier complete-observation forecasts.

### What was being examined

Whether **139 distinct score recipes** rank future vault returns and Sharpe, support useful absolute forecasts, or reveal a threshold below which entries should remain cash. Compare monthly learned absolute floors, a fixed 75th-percentile floor, matched random vetoes and rejection of unscored entrants. Frozen focal methods are v11, Blend 46d and the four-input candidate. Target return, CAGR, Sharpe and volatility now use causal calendar-day NAV carry, retaining actual observation counts and terminal censoring.

### Was there a hypothesis?

Higher scores should identify better future profitability, with extra inputs strengthening that relationship. A low-score region might have reliably negative expected net return, making entry vetoes beneficial. Missing scores were examined as a possible reason to withhold capital.

### What was the result?

#### Thirty-day ranking — 1 January–4 October 2026

Equal-date Spearman correlations among eligible vaults. Bands account for dependent dates but are exploratory on previously researched history; they are not corrected confirmation across 139 recipes.

| Score       | Target   |   Mean rank IC |   Lower block band |   Upper block band |   Supported origins |
|:------------|:---------|---------------:|-------------------:|-------------------:|--------------------:|
| v11         | cagr     |         0.0877 |            -0.0069 |             0.2004 |                  62 |
| v11         | sharpe   |         0.1286 |             0.0193 |             0.2461 |                  62 |
| Four inputs | cagr     |         0.089  |            -0.005  |             0.1983 |                  62 |
| Four inputs | sharpe   |         0.1366 |             0.0246 |             0.2511 |                  62 |
| Blend 46d   | cagr     |         0.0867 |            -0.0076 |             0.2038 |                  62 |
| Blend 46d   | sharpe   |         0.1348 |             0.0251 |             0.2622 |                  62 |

Return bands include zero; Sharpe bands are positive for all three focal methods. Thirty-day return ranking still reverses from **+0.227–0.235 in Q1 to −0.072–−0.107 in Q3**. The added score inputs do not establish stable broad return-ranking superiority.

Calibration is no longer uniformly worse than constants. At thirty days, return MSE changes range from **-0.68% to +0.66%**, and Sharpe from **-2.07% to +0.33%**. Seven-day return/Sharpe fits still lose to constants. Ninety-day calibration now has **47 supported 2026 origins** per focal method/target, with return MSE **3.6–6.6% lower** and Sharpe **2.8–5.4% lower** than constants. NB08 can train on earlier matured history, unlike NB09's fixed 2026-only training design. The short evaluation still contains few independent ninety-day windows.

The absolute floor is active in **27/30 method-months**, including February floors of 0.3 for v11 and 0.2 for Blend 46d, but rejects **zero 2026 entries** across the allocation treatments. The percentile floor changes one entry for the seven-position four-input strategy; its small improvement is reproduced by random controls and remains below the six-position baseline. All 2026 portfolio controls reproduce their earlier figures: **51.77% CAGR / 2.30 Sharpe** for four inputs at six positions, and **47.93% / 2.46** for Blend 46d at seven.

The foregone-return diagnostic also needed sparse-data correction. The single distinct 2026 rejected entry now has a **−37.79% thirty-day gross filled-NAV return**; its earlier label was missing because the anchor had no actual mark. Treatment and random-control duplicates do not constitute separate entry evidence.

Full-history percentile filters have mixed effects against their own controls: v11 CAGR rises by **0.31–0.83 percentage points**, while the four-input and blended strategies lose **0.46–1.25 points**. Absolute floors veto no entries in either period. Excluding unscored entrants in the six additional full-history replays lowers CAGR by **3.75–5.31 points**; it is not a justified blanket cash rule.

Contributor concentration remains material: Realist Capital supplies **38.4%** of the focal candidate's positive vault PnL; DOEZOE supplies **90.3%** of same-sign losses on the worst booked day. Sparse forecast fixes alter labels and calibration, while source portfolio NAV marking and selection remain unchanged.

### Was the hypothesis confirmed or rejected, and why?

**A weak score relationship is present, with stronger evidence for Sharpe ranking than growth ranking; useful admission floors remain unconfirmed.** The earlier blanket claim that every forecast loses to constants is superseded. Small error improvements and positive risk-ranking bands do not establish stable return selection or profitable cash thresholds. The absolute rule still does not change actual 2026 entries, and the percentile effect is matched by random vetoes.

### What useful new leads did we learn?

Test a predeclared dense-observation cohort and genuinely marginal entrants before learning a new floor. Investigate whether score information forecasts risk or smoothness more consistently than growth. Treat filled-risk outcomes as held-NAV estimates and retain reporting-age controls. Freeze promising portfolio candidates for later confirmation; preserve missing, imputed and finite zero scores separately.

## NB09 — individual features and K-ratio

[Notebook](09-research-k-ratio-feature-forecasts.ipynb) · [latest findings](09-k-ratio-feature-forecast-findings.md) · [amendment](09-k-ratio-feature-forecast-amendment.md). Builds on NB05's feature questions and NB04's metric inventory; individual inputs are examined rather than NB08 composite scores. Sparse-data corrections and this in-place rerun supersede the earlier complete-observation verdicts.

### What was being examined

Predict future CAGR, Sharpe and K-ratio from five existing metric families across nine windows, adding **30/60/90/180/360-day and max recorded-history K**. Forecast every four days, refit monthly from strictly matured labels, and compare models on identical vault/date rows. Missing=True retains usable shorter histories with shared availability controls and training-only imputation.

K fits ordinary intercept OLS to log NAV with the anchor included: `slope / slope_SE × sqrt(365)/(L+1)`. All metrics now carry the latest known positive NAV on calendar days; no gap compression or backfill before first observation. Max spans the first recorded positive mark through T−1 and needs at least three fitted points. Actual mark counts and ages remain separate. Future outcomes are censored beyond the last actual vault observation/archive end. Recorded history is not certified inception.

### Was there a hypothesis?

K's path consistency might add predictive information beyond existing ratios, including for partial-history vaults. Longer K windows might improve the original 30/60/90/180-day inventory. Gains should survive matched cohorts, activity, precision, missingness and calendar checks.

### What was the result?

#### Incremental K prediction — 1 January–4 October 2026

Mean within-date rank correlations on identical supported rows. These are forecast discrimination measures, not strategy returns. Seven days now has 45 paired origins and 25 complete blocks; thirty days has 24 origins and three blocks.

|   Horizon (days) | Target   |   Existing features |   Existing + six K |   Change |   Paired origins |   Calendar blocks |
|-----------------:|:---------|--------------------:|-------------------:|---------:|-----------------:|------------------:|
|                7 | CAGR     |              0.0185 |             0.0214 |   0.0029 |               45 |                25 |
|                7 | K-ratio  |              0.118  |             0.1254 |   0.0074 |               45 |                25 |
|                7 | Sharpe   |              0.1026 |             0.1143 |   0.0117 |               45 |                25 |
|               30 | CAGR     |              0.0671 |             0.0688 |   0.0017 |               24 |                 3 |
|               30 | K-ratio  |              0.1591 |             0.1657 |   0.0067 |               24 |                 3 |
|               30 | Sharpe   |              0.1202 |             0.1319 |   0.0117 |               24 |                 3 |

All six point estimates improve after adding K. **Every seven-day incremental block interval still includes zero**; thirty days has too few blocks for an interval, and ninety-day models remain unsupported under the fixed chronological training requirements. The K model's growth MAE is **17.9% worse at seven days and 25.3% worse at thirty days than zero return**. Positive rank changes do not establish profitable absolute forecasts.

#### Sparse metric coverage — 1 January–4 October 2026

On the **same 24,605 actual-observation anchor rows**, max K coverage rises from **27.3% to 98.5%**, and 360-day K from **0% to 26.7%**. The earlier missing-year conclusion was caused by the strict daily-observation requirement. With carried anchors admitted, the wider population is **31,274 rows**, and max K is finite for **30,560 (97.7%)**. Its span is **2–1312 days, median 217**. Leading missing history and degenerate ratios remain legitimately missing.

Relative to four-window K, **adding max alone improves all six point estimates**, by **+0.0047 to +0.0156**. **Adding year alone lowers all six**, by **-0.0031 to -0.0001**. These are exploratory same-row ablations; the larger max effect is a useful lead, while the tested year feature has no demonstrated benefit.

K remains highly correlated with Sharpe (30-day feature rank correlation approximately **0.91**). Historical ordinary/EWMA volatility has much stronger future-volatility rank IC, around **0.74–0.77** at seven/thirty days, with weak future-mean-return relationships. Filled NAV assumes the last reported level persists between observations; dense-observation and activity cohorts remain necessary interpretation checks.

### Was the hypothesis confirmed or rejected, and why?

**A small incremental K signal is suggested, but superiority remains unconfirmed.** The corrected six-input treatment improves every supported point estimate, reversing the earlier growth-ranking verdict. Intervals and limited calendar blocks do not establish reliable gains, and zero return still beats the K model's growth MAE. The tested max-history addition warrants follow-up; the tested year-only addition deteriorates point estimates. No portfolio strategy using these forecasts has been backtested here.

### What useful new leads did we learn?

Prioritise a predeclared max-K ablation and dense-observation validation, with explicit age and fill-quality controls. Test volatility prediction for position sizing or risk limits in an executable strategy. Retain robust scaling and exact log-return growth inputs; missing=True is mechanically supported but does not prove young-vault forecasting advantage. Confirm findings on later observations before promoting a rule.

## NB10 — sorting, risk and allocation snapshots

Original notebook: [10-original-portfolio-snapshots.ipynb](appendices/10-original-portfolio-snapshots.ipynb). Detailed [findings](10-portfolio-snapshot-findings.md) and [reviewed plan](10-portfolio-snapshot-plan.md).

### What was being examined?

Separate the predictive ordering of frozen scores and risk estimates from the economic effect of position weights, breadth and allocation constraints. Three frozen recipes (v11, Blend 46d and four-input) select baskets every four days; each holds fixed units for 7, 30 or 90 days. This uses the unchanged repaired archive and introduces no new return features or score coefficients. Primary reporting origins are **1 January–4 October 2026**, with 30-day outcomes requiring maturity before the archive boundary; 62 phase-zero origins qualify.

### Was there a hypothesis?

Six explicit hypotheses cover sorting, risk forecasts, unequal weighting, breadth, allocation constraints and reporting artefacts. Risk estimates should predict future variance; unequal weights should improve the selected basket's return/risk trade-off; wider baskets should diversify without excessive dilution. The study tests each claim separately using matched dates, baskets and budgets.

### What was the result?

The table uses the same six-position, 90-day-risk reference and all 62 resolved2026 origins. Returns are mean independent **30-day simple returns**, not compounded strategy CAGR. “Regularised” shrinks empirical variance towards a contemporaneous leave-one-out peer prior; p=2 means inverse variance.

| Frozen score | Future-return rank IC | Equal-weight return | Raw inverse-variance return | Regularised inverse-variance return | Regularised weighting lift vs equal |
| --- | ---: | ---: | ---: | ---: | ---: |
| v11 | 0.0877 | 2.224% | −0.137% | 0.837% | −1.387pp |
| Blend 46d | 0.0867 | 1.337% | −0.538% | 0.581% | −0.756pp |
| Four-input | 0.0890 | 2.003% | 0.206% | 1.083% | −0.921pp |

Selected-basket 90-day risk rank IC is about 0.51–0.55, stronger than return IC. Raw and regularised forecasts improve mean QLIKE against the peer prior, but regularisation does not uniformly beat raw forecast loss. Calibration ratios below 1 expose underprediction. Unequal weights reduce observed variance and drawdown while sacrificing uncapped returns.

Matched10-versus6-position regularised inverse-variance returns decline by0.128–0.743 pp, while risk falls. The10-position baskets resolve on 55 origins versus 62 for six positions; breadth and satellite curves use common resolved origins. First-update attribution is small relative to the remaining negative weighting lift, which persists across four overlapping origin phases.

Entry constraints change the answer. Under source-report-only concentration/TVL projection, regularised inverse-variance weighting lifts mean 30-day return over the same-budget capped equal benchmark by **0.063pp (v11),0.345pp (Blend 46d),0.796pp (four-input)**. Corresponding capped raw/source inverse-variance lifts are **−0.462pp,−0.098pp,+0.637pp**. These are stateless projections; the source engine's repeated decisions, retention and costs are absent. Unknown observation clocks retain archived state rather than inventing unavailable history. A known-only exclusion sensitivity becomes all cash and is explicitly not the default.

### Was the hypothesis confirmed or rejected, and why?

**Risk ordering is supported descriptively; uncapped return-enhancing inverse-variance weighting is rejected on this period.** Regularisation moderates the return loss, and constraints can reverse the weighting comparison. **Wider baskets provide a trade-off, not established profit improvement.** Sorting IC is modest and similar across the three recipes, conditional on finite scores and observed future labels. Strict eligible-universe references resolve on 55 of 62origins; they do not justify survivor-only selection benchmarks.

No construction rule receives an inferential promotion label.2026 has too few complete calendar blocks for the frozen ten-block gate. All supported full/pre-2026 simultaneous 18-comparison bands include zero; those periods are already researched, so remain exploratory. Snapshot results cannot replace the source 41.20% CAGR replay or establish future strategy performance.

### What useful new leads did we learn?

Prioritise matched **risk regularisation × concentration/TVL redistribution** controls in the next executable replay. Test weaker exponents and longer nearby risk windows as explicit risk/return trade-offs, without choosing a lone highest-return cell. Preserve same-budget equal controls and the requested/accepted ledger: otherwise caps can obscure what the weighting rule contributes. Investigate shared-name dilution before widening baskets. Retain reporting-quality and realised-risk calibration checks when evaluating apparently low-risk vaults.

Independent original-archive audits check causal filling, young/missing histories, source score clocks, fixed units, signed missing-return bounds, covariance numerics and the source-capacity controls. The original report has 47 separate inspected figures; exhaustive tables are saved in three linked appendices.

## Expanded NB10 — composite scores for ranking and weighting

Notebook: [10-research-portfolio-snapshots.ipynb](10-research-portfolio-snapshots.ipynb). Detailed [smoke findings](10-expanded-score-allocation-smoke-findings.md) and [reviewed expansion plan](10-expanded-score-allocation-plan.md). The original NB10 remains preserved above.

### What was being examined?

Combine inverse variance, inverse volatility, K and performance metrics **inside per-vault scores**, before converting the final score into position weights. Ranking and sizing may use different recipes. The initial matrix covers 36 combinations, arithmetic/geometric/minimum aggregation, standalone metrics, five sizing maps, three missing-data policies, six versus ten positions and entry constraints. Decisions cover all 70 four-day origins from **1 January–4 October 2026**, retaining all 2025 warmup and earlier recorded history. There are 62 mature 30-day windows and eight pending windows.

### Was there a hypothesis?

Low-risk components may improve sizing or selection beyond simply flattening weights; K may add information; role separation, missing-data treatments and sizing maps may improve realised allocation outcomes. A neutral-offset control separates risk information from mechanical flattening. These are hypothesis probes on previously researched history, with no inferential winner claim.

### What was the result?

Matched effects below are mean **30-day simple-return differences in percentage points**, new minus control. These are overlapping fixed-unit snapshots, not strategy CAGR. All comparisons have 62 common resolved origins except ten versus six, which has 59.

| Comparison | Difference | Interpretation |
| --- | ---: | --- |
| Focal ranking; average of focal and inverse-variance scores for sizing vs focal-only sizing | +0.165 pp | Modest sizing improvement |
| Same risk sizing vs focal plus constant-0.5 offset | +0.145 pp | Varying risk information adds more than flattening alone |
| Risk-containing ranking, equal sizing vs focal ranking, equal sizing | −1.112 pp | Changing selection hurts; common-budget effect is −1.094 pp |
| K-containing sizing vs K removed, identical ranking | −0.014 pp | No improvement in this particular coefficient comparison |
| Squared versus linear focal/risk sizing | +0.115 pp | Sharper sizing helps this controlled recipe |
| Ten versus six positions for the joint focal/risk/K recipe | −0.873 pp | Wider basket dilutes return on matched support |
| Available-component renormalisation vs missing-zero | −0.889 pp | Mean cash rises by 29.917 pp; common-budget effect remains −0.778 pp |

The source v11 and focal equal-weight controls reproduce their original saved identities, weights and outcomes. All 27 independent audit checks pass. Fifteen separate charts show component redundancy, missingness, requested/accepted allocations, quarterly returns, risk contributions and influence. Some standalone probes have unresolved endpoints and cannot be compared by unmatched means. Short-CAGR sizing has large downside tails; aggregate results depend on specific vaults and quarters.

### Was the hypothesis confirmed or rejected, and why?

**Risk as a sizing ingredient is supported descriptively for the focal recipe; improved ranking is rejected for the tested blend.** K weighting, broader baskets and available-component missingness do not improve their tested controls. The ten-complete-block inference gate remains unmet, so these findings establish neither statistical superiority nor future profitability. The expanded smoke does not establish an improvement over every original NB10 weighting control.

### What useful new leads did we learn?

Keep ranking and sizing separate. Prioritise risk-score sizing, its neutral-offset control and common-budget comparisons. Complete the K ranking/sizing four-cell block and nearby risk-window/raw-regularised comparisons before attribution. Investigate capacity and cash changes under missingness, and retain young vaults without treating absent long history as measured zero risk. The next-stage registry contains **334 proposed standalone metric/lookback policies**, and all **139 frozen recipes** remain verified in inventory. Those broader stages have not been executed; the reviewed plan explicitly stops after smoke findings.

### Interpretation — obvious and less obvious outcomes

NB10 suggests preserving the stronger return-ranking formulas and focusing on how to size their selected vaults. Adding more ingredients to ranking often reduced returns. Several sizing changes helped, but **the new composite methods have not beaten the original NB10 regularised inverse-variance control**.

#### Allocation outcomes — 1 January–4 October 2026; 30-day horizon

The table compares average outcomes across 62 mature, overlapping observations, with 2025 indicator warmup retained. Each decision creates a separate basket held for 30 days. Returns are mean 30-day simple returns, not strategy CAGR; drawdown is the mean of each window's maximum drawdown, not the maximum drawdown of a continuous strategy.

| Selection and sizing | Mean 30-day return | Mean drawdown within each 30-day window |
| --- | ---: | ---: |
| v11 selection, source sizing | 1.47% | −3.97% |
| Four-input selection, equal weights | 1.72% | −6.19% |
| Four-input selection, proportional to its score | 1.65% | −7.00% |
| Same selection, arithmetic mean of return and inverse-variance scores | 1.81% | −5.81% |
| Same selection, geometric mean of those scores | 2.15% | −5.32% |
| Same selection, bounded inverse-variance score alone | **2.38%** | **−4.64%** |
| Same selection, original NB10 regularised inverse-variance sizing | **2.51%** | **−4.19%** |
| v11 selection, minimum of four metric scores | 2.39% | −5.00% |

The four-input formula is the existing CAGR/Sortino blend. The bounded inverse-variance component is a transformed, regularised risk score; it differs from allocating directly in proportion to inverse variance. The original regularised control and its bounded-score counterpart use the same 62 dates and mean invested budget.

#### Obvious findings

- **Risk information helped sizing more than selection.** Adding inverse variance to the weighting score improved return by **0.165 percentage points** over return-score sizing. Adding it to ranking, while retaining equal weights, reduced return by **1.112 points**. It selected calmer portfolios, but sacrificed substantial return.
- **More positions brought a measurable trade-off.** Ten versus six positions reduced mean return by **0.873 points** on 59 matched dates, while reducing mean realised variance by about **38%**. Diversification worked, but it was expensive in returns.
- **Extra complexity did not reliably help.** Covariance-based score risk budgets improved on their corresponding linear score allocation, but still trailed the simpler inverse-risk sizing treatment.
- **Standalone metrics varied greatly.** Thirty-day CAGR alone returned **−3.31%**, with a worst basket of **−39.06%**. The 360-day CAGR version returned **+2.41%**. Their available outcome samples differ—58 versus 60 resolved origins—so this warrants lookback sensitivity checks rather than establishing one year as optimal.

#### Less obvious findings

1. **A score can select useful vaults without telling us how many dollars each deserves.** Proportional sizing from the four-input return score performed worse than equal weights: **1.65% versus 1.72%**, with worse drawdowns. Ranking confidence and position size should therefore be treated as separate questions.

2. **IC alone cannot judge weighting methods.** The inverse-volatility and inverse-variance components have identical ordering, yet produced **2.05% versus 2.38%** returns on the same selected baskets. Their score magnitudes produce different allocations. Likewise, replacing 90-day K with maximum-history K increased return-ranking IC from **0.073 to 0.102**, while portfolio return fell from **1.58% to 1.30%**. Better ordering across the whole universe does not guarantee a better top-six portfolio.

3. **The risk-sizing benefit mainly appeared when the return-selected basket struggled.** For Q3's mature origins, inverse-risk sizing returned **+0.91%**, versus **−3.49%** for equal weights on the same baskets. It underperformed equal weights in Q1 and Q2. This looks more like protection against a difficult regime than a uniform return improvement. These are mean 30-day outcomes grouped by origin quarter, not compounded quarterly profits.

4. **Missing-data policy effectively changes the selector.** Under available-component renormalisation, **84% of selected vault/date observations lacked the original four-input score**, versus **0.27%** under missing-zero. Mean cash rose from **2.12% to 32.04%**. Even after matching invested budgets, return remained **0.778 points lower**. Ignoring missing components gives a major relative advantage to vaults without complete scoring history; it is an economic policy, not merely a calculation convenience. Missing the composite can reflect unavailable or undefined constituent metrics, not just youth.

5. **The promising four-metric minimum score mostly behaved like a risk rule.** In T18, the 180-day inverse-volatility component was the minimum—and therefore determined the score—for **79% of selected vault/date observations** across mature origins. Its good result does not yet demonstrate that four inputs contributed useful information. A matched **v11 selection + inverse-volatility-only sizing** control is needed to establish what the other three inputs add.

6. **Caps can substantially rewrite sophisticated allocations.** The score risk-budget solver met its requested targets, but entry constraints subsequently distorted them. Across mature dates, the largest position-level deviation averaged about **17 percentage points of risk contribution**. Optimising requested weights without examining accepted weights would give a misleading account of the strategy.

#### Implications for the next experiment

Prioritise **fixed selectors with a broader, controlled sizing sweep**, retaining the original regularised inverse-variance method as a serious benchmark. The most informative additions are nearby risk lookbacks, risk-score transformations and exponents, the T18 single-component control, and explicit missing-history admission rules.

The current evidence supports these research directions. It does **not yet establish a replacement strategy**: observations overlap, profits depend on particular quarters and vaults, the ten-complete-block inference gate remains unmet, and the broader scoring inventory has not been run. See the [expanded notebook](10-research-portfolio-snapshots.ipynb), [smoke findings](10-expanded-score-allocation-smoke-findings.md) and [original NB10 findings](10-portfolio-snapshot-findings.md) for the underlying results.

## NB11 — risk estimation, weighting and position sizing

### What was being examined?

[NB11](11-research-weighting-sizing.ipynb) implements the [Claude-reviewed plan](11-weighting-sizing-plan.md), using frozen six-vault focal-four and v11 selectors. It tests 45/90/180-day risk windows, inverse-volatility through inverse-variance powers, fixed versus window-dependent shrinkage, raw floors, bounded risk scores, median/max multi-window forecasts and matched calendar-log versus gap-scaled sparse estimates. Ranking and eligibility remain unchanged.

The smoke covers 18 combinations over all 70 origins. The main study covers 40 combinations, reuses all smoke allocations and evaluates 7/30/90-day outcomes. Indicators retain all 2025 and earlier recorded history, starting in March 2023. Only NAV is forward-filled causally; young histories use declared priors/fallbacks. These are fixed-unit snapshots with inherited T−1 anchor fills, not continuous strategy backtests or strategy CAGR.

### Was there a hypothesis?

1. A sensible risk-window/power neighbourhood could improve on the original 90-day inverse-variance benchmark.
2. Shrinkage and sparse-observation modelling could improve risk forecasts and accepted allocations.
3. T18's four-input minimum might largely be explained by its V180 component.
4. Multi-window estimates and capacity-aware diagnostics might offer more stable allocation than choosing one window.

### What was the result?

#### Selected allocation comparisons — 1 January–4 October 2026; 30-day horizon

Every row uses the same 62 resolved origins within its selector. Means are independent 30-day snapshots; drawdown is the mean within-window drawdown. Cash uses the same resolved calendar.

| Selector and method | Mean return | Mean daily variance | Mean drawdown | Mean cash |
| --- | ---: | ---: | ---: | ---: |
| S01: F:equal | 1.716% | 0.000196 | -6.193% | 3.315% |
| S03: F:regular L90/p2/κ30 | 2.512% | 0.000120 | -4.191% | 3.315% |
| S09: F:raw L90/p2/κ30 | 2.353% | 0.000118 | -4.178% | 3.315% |
| S18: F:gap_log L90/p2/κ30 | 2.579% | 0.000121 | -4.183% | 3.315% |
| M35: F:median | 2.366% | 0.000117 | -4.194% | 3.315% |
| M36: F:maximum | 2.364% | 0.000137 | -4.877% | 3.315% |
| S02: L:equal | 1.929% | 0.000169 | -5.698% | 3.008% |
| S04: L:regular L90/p2/κ30 | 1.992% | 0.000100 | -3.777% | 3.008% |
| S14: L:source | 1.467% | 0.000100 | -3.973% | 3.008% |
| S15: L:bounded_V | 2.031% | 0.000144 | -5.028% | 3.008% |
| S16: L:T18 | 2.390% | 0.000147 | -5.003% | 3.008% |
| M40: L:gap_log L90/p2/κ30 | 2.007% | 0.000104 | -3.831% | 3.008% |

The original regularised focal 90-day/p2 policy leads all nine core window/power cells. Increasing p improves focal means within each window; 180 days gives worse realised variance and drawdown for both selectors. v11's mean-return surface is flatter around 90/180 days, while its 90-day baseline retains better realised risk. No tested multi-window method beats the focal 90-day baseline.

Gap-scaled focal sizing returns **2.579%**, versus **2.512%** for the baseline and **2.413%** for its matched calendar-log control. The baseline difference is **+0.067 percentage points**, but median return falls from **2.620% to 2.106%**. Quarter-level mean differences are positive in all three mature quarters; vault effects offset strongly, with approximately **+0.177 pp from pmalt and −0.177 pp from Hyperrr**. A modest mean improvement is not a broad distributional improvement.

T18 returns **2.390%**, versus **2.031%** for V180 alone: **+0.359 pp** despite V180 determining about 79% of minima. This uplift is concentrated in Q1 (**+1.106 pp**); Q2 is **−0.135 pp**, and Q3 is approximately flat. The other components matter economically, but do not improve every regime.

Risk-forecast calibration and allocation profits disagree. L45 gives more favourable QLIKE differences against its own window-specific prior, but not the strongest portfolio returns; those references vary by window, so this is not an absolute forecast-loss ranking. Within the matched sparse pair, gap improves focal QLIKE modestly, but v11 QLIKE worsens slightly despite higher 30-day portfolio mean return. Ratios of mean realised to forecast variance move closer to one for both selectors.

All methods deploy identical total capital within each selector. Explicit common-budget reprojection reproduces paired effects, so cash differences do not explain the sizing outcomes. Caps change the distribution substantially: original baseline sum-absolute shadow distortion averages about 45% of account capital, equivalent to about 22.6% transferred between names.

### Was the hypothesis confirmed or rejected, and why?

**H1: no demonstrated improvement from the core surface.** The original focal 90-day/p2 cell remains strongest in that matrix. The surface does not establish a universal optimum or a broad flat peak; the registered local-window sensitivities remain unrun.

**H2: useful descriptive support, not confirmation.** Regularisation improves mean returns against raw90 by **+0.159 pp focal / +0.525 pp v11**. The matched gap estimator gives a small lead, but calibration and median-return trade-offs prevent a strong improvement verdict. It assumes variance proportional to elapsed days and is not economic ground truth. Kappa30 counts complete intervals for the sparse pair and actual updates for the original estimator.

**H3: the single-component explanation is incomplete.** V180 dominates minimum activity, but the remaining components add a measurable, Q1-concentrated return difference. Keep both controls in any replay.

**H4: no portfolio benefit established for median/max aggregation.** The maximum forecast can still produce greater realised portfolio variance after relative normalisation and caps. The cap-aware optimiser remains separately registered, not executed.

The primary 17 contrasts cover 51 outcome statistics, but only **eight complete 30-day blocks** exist; the ten-block gate fails. Seven-day views are secondary, with 38 complete blocks. Ninety-day targets have 47 mature origins but only 46 resolved baskets: the 17 January Dobutsu–Alpha Club target exceeds its final actual mark. Censoring reduces complete paired 90-day blocks to one. Pending/unresolved rows remain explicit, with signed return bounds and no survivor renormalisation.

### What useful new leads did we learn?

- Retain regularised90/p2 and equal allocation as explicit engine-replay controls.
- Carry the matched sparse gap estimator into a small replay; compare its own calendar-log control as well as the original simple-return estimator.
- Treat T18 as a regime-sensitive allocation lead, with V180-only control and quarter/vault attribution.
- Run the registered 12 nearby-window/prior/floor sensitivities before declaring a stable risk setting.
- Caps materially distort requested weights; the eight registered cap-aware policies address a real mechanism, rather than cash deployment differences in this study.
- Risk calibration should accompany portfolio evaluation. Better reported-NAV forecasting does not guarantee profitable sizing.

All **17 numerical fixtures, 22 smoke checks and 26 main checks pass**. Five historical controls reproduce exact saved weights and mature outcomes. The notebook completes all seven code cells without warnings and provides 27 separate main figures plus one smoke figure. Reusable implementation, provenance, ledgers, forecast calibration, contrast attribution and follow-up registries are saved. See [detailed findings](11-weighting-sizing-findings.md).

## Leads carried forward

1. **Prioritise portfolio construction:** NB10 motivates a matched engine replay of risk regularisation × concentration/TVL redistribution. Preserve source/raw and equal-weight controls; uncapped snapshot results and capped entry results differ materially.
2. **Validate two fixed portfolio candidates:** four-input scoring at six positions, and two-input Blend 46d at seven. Their results justify follow-up, but search selection, overlapping periods and contributor concentration prevent declaring a validated winner.
3. **Separate return selection from risk allocation:** volatility persistence offers a stronger measured relationship than growth persistence. Test whether using it actually improves net portfolio outcomes after capacity and admission limits.
4. **Investigate marginal entries and core allocation:** extra positions can dilute or change profitable shared holdings. A score floor must affect actual proposed entrants to establish a useful cash-versus-entry decision.
5. **Treat cash as a consequence to explain:** both no-redistribution caps and indiscriminate widening show that cash percentage alone is a poor objective. Refill must be evaluated against matched controls and realised exposure.
6. **Measure effective information:** clipping saturation, correlated ratios, repeated windows and missingness can make nominally large feature sets much smaller. Preserve availability distinctions and use matched ablations.
7. **Improve validation and provenance:** retain exact controls, full ledgers, causal daily NAV paths, actual observation provenance and explicit support gates. Avoid interpreting inactive treatments, sparse complete cases or a missing one-year feature as evidence of no effect.

## Indicator reference

The table records the first notebook using a definition in this folder. Later implementations may reproduce the same economics under stricter observation rules; these are identified separately.

| Indicator/helper | First notebook | Definition and use |
| --- | --- | --- |
| Source TVL and availability: `tvl()`, `tvl_inclusion_criteria()`, `trading_availability_criteria()`, `inclusion_criteria()` | NB01 | Produce timestamp-bounded TVL and candle-availability membership, intersecting the TVL-qualified lists and removing benchmarks. Candle availability and deposit permission are separate checks. |
| Growth: `cagr_score()` | NB01 | Annualises the trailing NAV price ratio and clips growth into a 0–1 score at the source 100% upper limit. NB04's `ScorePanel` extends the metric across multiple windows and clipping profiles. |
| Sharpe: `sharpe_score()` | NB01 | Computes rolling annualised return mean divided by standard deviation and clips the ratio to 0–3. It is registered in source fallback ranking and later included in the searchable metric panel. |
| Sortino: `sortino_score()` | NB01 | Divides annualised return mean by downside deviation, with zero downside remaining undefined. It supplies the active 45-day source ranking leg, clipped to 0–3. |
| Composite ranking: `cagr_sortino_weight()`, `cagr_sharpe_weight()` | NB01 | Combine the source score legs, requiring finite components. The active source formula uses CAGR/Sortino; a missing composite becomes a lowest-priority zero-score candidate at selection. |
| Risk and gate: `inverse_vol()`, `return_gate()` | NB01 | Estimate inverse 90-day rolling volatility with a floor and raw trailing price return for eligibility. `compute_sizing_weights()` squares inverse volatility for inverse-variance sizing; the return gate uses 14 days. |
| Membership count: `tvl_included_pair_count()` | NB01 | Counts the TVL-qualified vault IDs available at each date. It helps distinguish the snapshot inventory from the eligible trading population. |
| `ScorePanel` performance metrics | NB04 | Computes trailing CAGR, Sharpe, Sortino, maximum drawdown and floored Calmar across the metric/window panel. Completed T−1 data and per-cell completeness allow ranking recipes to vary without changing the source selector. |
| `ScorePanel.cell_scores()` / `score_values()` | NB04 | Clips/scales individual metrics into bounded scores, then combines non-negative metric/window coefficients. Legacy/requested profiles and missingness can change ranking even with identical coefficients. |
| `WeightingProvider` risk estimates | NB03 | Produces causal trailing volatility and regularised covariance for selected vaults. These estimates drive the alternative weights and requested risk-contribution diagnostics, which can change after allocation constraints. |
| `feature_audit()` / `ic_summary()` | NB05 | Relates completed historical inputs to strictly future, end-censored NAV outcomes. Date-level rank correlations and exploratory block uncertainty distinguish association from portfolio backtest performance. |
| `method_values()` / `_labels()` | NB08 | Evaluates frozen composite recipes and builds terminally censored forward endpoint/path outcomes. Missing, imputed and valid zero scores remain separate, and carried NAV retains separate actual observation counts. |
| `k_statistics()` | NB09 | Fits intercept OLS to equally spaced log-NAV and returns K, slope, slope SE, signed R² and residual scale. Insufficient elapsed history or degenerate slope uncertainty remains undefined with explicit reasons. |
| `window_metrics()` / `build_features()` | NB09 | Recompute the five historical metrics on causally filled daily paths, adding exact log return, volatility, flat/active-return counts and observation-quality controls. Additional diagnostics include EWMA volatility, positive-return fraction, autocorrelation, variance ratio and weekly K. |
| `target_persistence()` / `residual_k()` | NB09 | Construct own-target/horizon persistence and training-only residual K controls. They test whether any apparent information survives a simpler forecast or overlap with existing ratios. |

## Weighting and allocation reference

These mechanisms have different purposes: score coefficients rank vaults, position weights allocate dollars, and forecast sample weights determine fitting influence.

| Mechanism | First notebook | Purpose and observed implication |
| --- | --- | --- |
| 90-day inverse variance | NB01 | Allocates requested weights proportional to inverse squared volatility, using the source floor. It remains the strongest tested weighting under parent redistribution, but near-flat paths interact badly with no-redistribution caps. |
| Parent capacity redistribution | NB01 | Reallocates rejected capacity through the remaining selected basket under concentration/TVL limits. Its behaviour is important to productive deployment and must be replicated explicitly. |
| Original-request dollar cap, `AuditedAlphaModel` | NB02 | Preserves initial requested dollar ceilings and leaves rejected capital in reserve. It validates cap behaviour but materially reduces exposure and profitability. |
| Inverse-volatility/equal blend and equal weights | NB03 | Flatten requested allocations compared with inverse variance. They repair much of the cap interaction without beating the original parent strategy. |
| Regularised inverse volatility | NB03 | Uses stabilised risk estimates to reduce extreme weights. The tested fixed policy underperforms the original redistributed baseline. |
| Correlation-aware risk budget | NB03 | Uses regularised covariance to target balanced estimated variance contributions. Admission/capacity constraints distort accepted risk budgets; requested risk parity is not a realised risk guarantee. |
| Equal and score-proportional sizing | NB04 | Compare identical ranking with equal dollars or dollars proportional to score. Inverse variance remains materially stronger for the source-like anchors. |
| Sparse score coefficients and score blends | NB04–NB06 | Rank metric/window inputs; they are not dollar position weights. Blending differently clipped scores and adding extra windows can alter basket selection despite the same aggregate metric balance. |
| Residual cash refill, `ResearchAlphaModel` | NB05 | Attempts redeployment after admission checks within the existing budget and ceilings. It recovers little target budget and underperforms paired controls. |
| Admission vetoes, `AdmissionAlphaModel` | NB08 | Sends rejected entry slots to cash or redistributes within surviving selected holdings and caps. The tested floors scarcely change actual entries and establish no benefit. |
| Support-weight variance regularisation, `m/(m+L/3)` | NB10 | Stabilises variance with a causal leave-one-out peer prior. It moderates uncapped return drag; capped comparisons differ and require matching budgets. |
| Stateless entry projection and bounded companions | NB10 | Isolates concentration/TVL, risk powers, breadth, covariance and satellite effects in independent fixed-unit snapshots. It does not reproduce engine retention or repeated rebalances. |
| `training_weights()` | NB09 | Gives each forecast-origin date one total fitting weight. It prevents large cross-sections dominating the model; NB09 introduces no new portfolio weighting rule. |

## Chart and table reference

Every displayed element should have a subheading, a short explanation and its period. Scatters are individual images; the catalogue subdivisions keep notebooks renderable.

| Analytics/helper | First notebook | What it helps examine |
| --- | --- | --- |
| `calculate_equity_curve()`, `calculate_returns()`, `calculate_advanced_metrics()` | NB01 | Compare growth, risk and the path of capital across fresh starts; daily resampling keeps metric conventions consistent. |
| `equity_curve_by_asset()` / `calculate_asset_weights()` / `visualise_weights(normalised=False)` | NB01 | The rendered wrapper shows absolute vault and reserve holdings, exposing concentration and idle cash rather than only normalised invested fractions. |
| `visualise_returns_over_time(period="quarter")` | NB01 | Quarterly profit heatmaps expose regime changes, with partial quarters and period boundaries labelled. |
| `calculate_position_profit_curves()` | NB02 | Reconciles trade flows and marked holdings to portfolio equity and attributes missed profits/losses to vaults. |
| Requested/accepted risk-budget and allocation diagnostics | NB03 | Show how sizing goals are distorted by TVL, concentration, admission and cleanup rules. |
| `factorial_heatmap()`, `singleton_heatmaps()`, `missing_effect_heatmaps()` | NB04 | Compare parameter combinations, individual inputs and missingness effects with explicit performance scales. |
| `pareto_chart()` / `parallel_coordinates()` | NB04 | Display CAGR/Sharpe, CAGR/drawdown, Sharpe/drawdown trade-offs and the search-space relationships. |
| `feature_correlations()` / `correlation_heatmap()` | NB04 | Measure metric/window redundancy with paired counts; correlations between inputs do not establish forecasting power. |
| `saturation_audit()`, `ic_figure()`, `quintile_figure()` | NB05 | Reveal clipped ties, forward ranking associations and outcome distributions across feature groups. |
| Support/cardinality and breadth grids | NB06–NB07 | Compare controlled added-input supports and their own six-position references before interpreting a selected maximum. |
| `scatter_figure()` / `interactive_scatter()` | NB08 | Plot score against realised forward outcomes with quarter colours, descriptive trends and tail-aware views. |
| Chronological calibration and threshold/random-control tables | NB08 | Show whether scores beat simple forecast baselines and whether floors change entries beyond an equivalent random veto. |
| `ic_map()`, `feature_scatter()`, `forecast_scatter()` | NB09 | Separate individual-feature association from chronological prediction accuracy, with counts and support notices. |
| `paired_comparison()` / `block_summary()` | NB09 | Compare identical observations and report calendar-block uncertainty rather than treating overlapping rows as independent. |
| `coverage_tables()` / `attrition_diagnostics()` | NB09 | Distinguish scheduled identities, observed anchors, finite inputs, future labels, fundability and model support. |

## Execution and source notes

All eleven main notebooks have saved completed outputs. NB11 completes seven code cells, its 18-policy smoke and 40-policy main matrices, all three horizons, 26 main checks and 27 separate main figures. Expanded NB10 completes all eight code cells with 27 passing audit checks and 15 separate inspected figures; its static preview renders. The original NB10 and its three result appendices remain preserved with completed outputs. The 10 October sparse-data reruns complete all 11 NB08 and 19 NB09 code cells without errors or logged warnings; both static previews render. The 1,251/99 separate catalogue images validate. NB01–NB07 retain their results because additional filling leaves their inputs unchanged. See [the metric audit](sparse-nav-rerun-2026-10-10.md). Metric-extraction helpers cannot recognise every custom styled table, so `NO_RESULTS` alone does not indicate an unrun experiment. This summary uses saved notebook results and the latest written findings, with older generations kept as historical evidence. Supporting repair investigations, DOEZOE status notes and review/amendment files explain provenance and implementation corrections; they are not additional strategy variants.

Primary detailed references: [restored inputs and controls](restored-data-rerun-2026-10-07.md), [NB02](02-accepted-dollar-cap-analysis.md), [NB03](03-alternative-weighting-analysis.md), [NB04](04-score-matrix-analysis.md), [NB05](05-opt-score-calibration-selection-cash.md), [NB06](06-score-3-4-inputs-analysis.md), [NB07](07-score-position-count-analysis.md), [NB08](08-score-forecast-findings.md), [NB09](09-k-ratio-feature-forecast-findings.md), [NB10](10-portfolio-snapshot-findings.md), and [NB11](11-weighting-sizing-findings.md).

## Experiment 12 — local sensitivity and constraint-aware allocation

Notebook: [12-research-allocation-followup.ipynb](12-research-allocation-followup.ipynb). Details: [findings](12-allocation-followup-findings.md). Period: **2026-01-01 → 2026-10-05 (exclusive end, UTC)**, with full earlier indicator warmup.

### What was examined

The 12 registered local sensitivities and eight cap-aware allocations from NB11, with ten exact controls. Fixed six-vault baskets at 70 origins; 7/30/90-day targets. Sixteen full engine replays cover benchmarks, matched sparse estimators, T18/V180, paired equal-risk allocations, selected sensitivities and original source controls.

### Hypotheses

Nearby windows/prior strengths might outperform the 90-day benchmark; caps inside a risk-budget objective might improve accepted allocations; snapshot gains might survive executable rebalancing.

### Results

The 75-day focal sensitivity improves mean 30-day return from 2.512% to 2.616%; engine CAGR rises only 46.60%→46.92%. V11 kappa 90 raises the snapshot mean 1.992%→2.102%, but engine CAGR falls 33.34%→32.07%. Both raw-floor alternatives produce identical accepted weights/outcomes to the raw baseline.

Solving with caps improves all four projected snapshot risk-budget pairs by 0.057–0.148 percentage points, chiefly in Q3, but every cap-aware snapshot policy trails its regularised inverse-variance benchmark. In the equal-risk engine comparisons, focal constrained CAGR falls 42.98%→42.88%; v11 rises 33.49%→33.88%, with better drawdown in both.

Sparse focal sizing improves engine CAGR 46.60%→47.46% and Sharpe 2.09→2.12, with slightly worse drawdown −7.05%→−7.10%. The original focal strategy remains strongest at 51.77% CAGR, 2.30 Sharpe, −6.35% drawdown; original v11 returns 41.20%, 1.96, −6.40%. No replayed candidate beats these same-selector source controls.

### Were the hypotheses confirmed?

Local sensitivity and cap-objective benefits are supported descriptively within the snapshot calculation, but consistent execution improvements are not established. Stronger v11 shrinkage reverses direction in the engine; cap effects are mixed. Sparse weighting has a small surviving gain against the regularised control, but fails to beat the earlier hand-picked strategy. Only eight primary 30-day blocks and repeatedly searched history preclude confirmation.

### Robustness and useful leads

Thirteen fixtures and 13 snapshot checks pass; ten NB11 controls reproduce all weights and horizon outcomes; position PnL reconciles. Absolute-weight charts were corrected to zero closed assets at observed timestamps and reconcile to equity with at most six active vaults. All 14 separate images were inspected; final outputs are free of warnings/errors.

Sparse sizing's $888 engine gain versus the regularised focal control combines pmalt +$1,606,Goon Edging +$968 and Hyperrr −$1,683. Realist Capital accounts for roughly 38%/45% of positive vault PnL under original focal/v11 controls. Their maximum recorded returns share 26 June, a two-day valuation update, mainly Realist Capital and Goon Edging. Actual daily NAV marks exist; BTC and ETH fell across 23–25 June. This shows concentrated trading profits, with no demonstrated archive fault.

The next useful controlled comparison separates regularisation from sequential versus simultaneous allocation under the same source sizing. Study which vault exposures and operational cash constraints cause the snapshot/engine reversal, and seek fresh observations rather than declaring a winner from more retrospective combinations.

# Experiment 13 — long-period candidate replay

Period: **2023-03-01 → 2026-10-08 (end exclusive, UTC; final archive day partial)**. Ten frozen 2026 leaders and two benchmarks, each starting with $150,000.

## What was examined

Whether the ten best repaired-data 2026 CAGR/Sharpe candidates retain strong returns over every available vault backtesting observation. Original scoring, sizing, N, missing behaviour, source selection and allocation methods are preserved.

## Hypothesis and method

Hypothesis: 2026 leaders retain gains against v11 and regularised90 across full history. Select the union of top five by each metric, fill to ten by their equal-weight rank sum. Freeze before long replay. All 24 2026 metric parity checks pass. Include source v11 and focal regularised90 as additional benchmarks.

## Results
| Candidate   | Name                                                       |     CAGR |   Sharpe |   Maximum drawdown |   Final equity (USD) |   Mean cash weight |   2026 CAGR |   2026 Sharpe |
|:------------|:-----------------------------------------------------------|---------:|---------:|-------------------:|---------------------:|-------------------:|------------:|--------------:|
| C01         | Legacy 45d / 4 inputs / 6m Sortino + 2m CAGR / 6 positions | 0.196103 | 1.455181 |          -0.079151 |        286077.842541 |           0.417960 |    0.522998 |      2.234661 |
| C02         | Blend 46d / 3 inputs / 6m CAGR / 6 positions               | 0.172029 | 1.303356 |          -0.079151 |        265856.053356 |           0.417193 |    0.519891 |      2.291272 |
| C03         | Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino / 6 positions | 0.220883 | 1.621567 |          -0.080840 |        308029.504531 |           0.437623 |    0.517666 |      2.303466 |
| C04         | Blend 46d / 7 positions                                    | 0.184532 | 1.394665 |          -0.080792 |        276224.866844 |           0.383954 |    0.479314 |      2.458715 |
| C05         | Legacy 45d / 4 inputs / 2m CAGR + 6m Sharpe / 6 positions  | 0.190605 | 1.452288 |          -0.079151 |        281365.121169 |           0.419798 |    0.496024 |      2.188999 |
| C06         | Blend 46d / 4 inputs / 6m Sortino + 2m CAGR / 7 positions  | 0.167068 | 1.256156 |          -0.104905 |        261821.698681 |           0.380648 |    0.404731 |      2.230642 |
| C07         | NB12 S18 F:gap_log L90/p2/κ30                              | 0.274434 | 1.504597 |          -0.102369 |        359592.422465 |           0.386749 |    0.474613 |      2.123093 |
| C08         | NB12 X01 F:regular L75/p2/κ30                              | 0.267854 | 1.469563 |          -0.102918 |        352943.139434 |           0.385632 |    0.469185 |      2.122572 |
| C09         | Legacy 45d / 4 inputs / 2m CAGR + 6m Sharpe / 7 positions  | 0.182339 | 1.361572 |          -0.079483 |        274385.512650 |           0.385777 |    0.441740 |      2.163980 |
| C10         | NB12 S17 F:calendar_log L90/p2/κ30                         | 0.273557 | 1.498344 |          -0.102369 |        358701.264437 |           0.386547 |    0.470421 |      2.115691 |
| B01         | Unchanged v11                                              | 0.158230 | 1.242672 |          -0.079151 |        254743.261549 |           0.418606 |    0.412004 |      1.959590 |
| B02         | Focal regularised90 benchmark                              | 0.270742 | 1.482563 |          -0.102369 |        355851.124426 |           0.385796 |    0.466005 |      2.091681 |

## Calendar-year returns
| Candidate   |   2023 (partial) |     2024 |     2025 |   2026 (partial) |
|:------------|-----------------:|---------:|---------:|-----------------:|
| C01         |        -0.036647 | 0.235121 | 0.208714 |         0.326095 |
| C02         |        -0.036647 | 0.235121 | 0.116320 |         0.334355 |
| C03         |        -0.036647 | 0.244127 | 0.291491 |         0.326659 |
| C04         |        -0.036647 | 0.238981 | 0.202280 |         0.283263 |
| C05         |        -0.036647 | 0.235121 | 0.206908 |         0.306200 |
| C06         |        -0.036647 | 0.238981 | 0.155732 |         0.265340 |
| C07         |         0.014324 | 0.458622 | 0.252121 |         0.294058 |
| C08         |         0.014324 | 0.458130 | 0.232458 |         0.290828 |
| C09         |        -0.036647 | 0.238981 | 0.220198 |         0.255999 |
| C10         |         0.014324 | 0.456342 | 0.251149 |         0.293876 |
| B01         |        -0.036647 | 0.235121 | 0.135220 |         0.257293 |
| B02         |         0.014324 | 0.456342 | 0.244428 |         0.290527 |

## Key new insights

Highest long CAGR: **C07 NB12 S18 F:gap_log L90/p2/κ30**, 27.44%, Sharpe 1.50, drawdown -10.24%. Highest long Sharpe: **C03 Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino / 6 positions**, 1.62, CAGR 22.09%.

Source v11: 15.82% CAGR / 1.24 Sharpe. Regularised90: 27.07% / 1.48. 10/10 exceed source v11 on both metrics; 2/10 exceed regularised90 on both.

## Robustness of results

The first actual positive NAV is 2023-03-01 00:00:00, last is 2026-10-07 00:00:00. The 1 March calendar includes the initial empty lead-in. All position PnL reconciles within $1; absolute weights sum to whole account equity. NAV-only forward fill preserves missing leading marks and actual-observation masks. Permission and capacity fields are handled by the unchanged source engine.
| Candidate   |   Best update |   Worst update | Best update date   |   Excess kurtosis | Top vault       |   Top positive profit share |   Sharpe with best update zeroed |   PnL residual (USD) |
|:------------|--------------:|---------------:|:-------------------|------------------:|:----------------|----------------------------:|---------------------------------:|---------------------:|
| C01         |      0.057310 |      -0.079151 | 2025-08-14         |         34.959365 | Realist Capital |                    0.153648 |                         1.369279 |             0.000000 |
| C02         |      0.057438 |      -0.079151 | 2025-08-14         |         36.204205 | Realist Capital |                    0.158476 |                         1.212822 |             0.000000 |
| C03         |      0.067128 |      -0.079151 | 2025-08-14         |         38.011957 | Realist Capital |                    0.156393 |                         1.534953 |            -0.000000 |
| C04         |      0.060350 |      -0.079151 | 2025-01-22         |         39.625049 | Realist Capital |                    0.195523 |                         1.303870 |             0.000000 |
| C05         |      0.054865 |      -0.079151 | 2025-08-14         |         36.547868 | Realist Capital |                    0.167200 |                         1.367201 |             0.000000 |
| C06         |      0.060350 |      -0.079151 | 2025-01-22         |         40.014372 | Realist Capital |                    0.139441 |                         1.162090 |             0.000000 |
| C07         |      0.151570 |      -0.072729 | 2024-11-13         |         95.494778 | Delta_01        |                    0.178532 |                         1.422212 |            -0.000000 |
| C08         |      0.151570 |      -0.073073 | 2024-11-13         |         95.412476 | Delta_01        |                    0.181710 |                         1.382266 |            -0.000000 |
| C09         |      0.060350 |      -0.079151 | 2025-01-22         |         36.609417 | Realist Capital |                    0.179001 |                         1.270500 |             0.000000 |
| C10         |      0.151570 |      -0.072473 | 2024-11-13         |         95.147606 | Delta_01        |                    0.176941 |                         1.414956 |            -0.000000 |
| B01         |      0.054258 |      -0.079151 | 2025-08-14         |         39.051128 | Realist Capital |                    0.172163 |                         1.152120 |            -0.000000 |
| B02         |      0.151570 |      -0.072779 | 2024-11-13         |         94.571284 | Delta_01        |                    0.180243 |                         1.396907 |            -0.000000 |

The largest recorded updates are audited against their vault NAV marks, current curator and BTC/ETH price context. Daily-resampled returns include two-day updates. The concentration table and quarterly heatmap should be considered alongside CAGR. No single removed-day or removed-vault diagnostic represents an executable rebalanced portfolio.

## Observation-interval audit
| Candidate   | Update     | Vault                  |          PnL | Supported   | First_mark              | Last_mark               |   Elapsed_days |   NAV_return |   Actual_marks | Receipt_after_engine_label   | Curator_excluded   | Quarantined   |   BTCUSDT return |   ETHUSDT return |
|:------------|:-----------|:-----------------------|-------------:|:------------|:------------------------|:------------------------|---------------:|-------------:|---------------:|:-----------------------------|:-------------------|:--------------|-----------------:|-----------------:|
| C03         | 2025-08-14 | naze oppa degen nation |  4388.842904 | True        | 2025-08-06 00:00:00.000 | 2025-08-13 00:00:00.000 |       7.000000 |     0.086983 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| C03         | 2025-08-14 | DailyTradeAI  Low risk |  3611.727339 | True        | 2025-08-06 22:14:00.022 | 2025-08-13 22:54:00.047 |       7.027778 |     0.071758 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| C03         | 2025-08-14 | cDOGE                  |  3026.232817 | True        | 2025-08-06 22:56:00.044 | 2025-08-13 22:16:00.032 |       6.972222 |     0.158532 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| C07         | 2024-11-13 | Road to 10 Million     | 15050.797563 | True        | 2024-11-06 00:00:00.000 | 2024-11-13 00:00:00.000 |       7.000000 |     0.302617 |              2 | False                        | False              | False         |         0.195882 |         0.170945 |
| C07         | 2024-11-13 | FFLGN                  |  4326.216664 | True        | 2024-11-06 22:12:00.158 | 2024-11-13 23:12:00.065 |       7.041666 |     0.416908 |              2 | True                         | False              | False         |         0.195882 |         0.170945 |
| C07         | 2024-11-13 | Delta_01               |  3588.314338 | True        | 2024-11-06 21:54:00.123 | 2024-11-13 23:14:00.148 |       7.055556 |     0.072605 |              2 | True                         | False              | False         |         0.195882 |         0.170945 |
| B01         | 2025-08-14 | DailyTradeAI  Low risk |  3611.727339 | True        | 2025-08-06 22:14:00.022 | 2025-08-13 22:54:00.047 |       7.027778 |     0.071758 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| B01         | 2025-08-14 | cDOGE                  |  3163.767157 | True        | 2025-08-06 22:56:00.044 | 2025-08-13 22:16:00.032 |       6.972222 |     0.158532 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |
| B01         | 2025-08-14 | JizzJazz               |  1820.820961 | True        | 2025-08-06 00:00:00.000 | 2025-08-13 22:24:00.019 |       7.933334 |     0.114081 |              2 | False                        | False              | False         |         0.072302 |         0.289411 |

The new allocation family recognises a 15.16% account update on 13 November 2024. This catches weekly marks, including Road to 10 Million (+30.26% NAV), FFLGN (+41.69%) and Delta_01 (+7.26%) since 6 November. BTC/ETH context is measured over those same real mark dates. Late intraday marks can fall after the daily engine label: this preserves the inherited daily-close convention, not a timestamp-faithful execution validation.

## Tail influence
| Candidate   |   Best update |   CAGR best update zeroed |   Sharpe best update zeroed | Removed vault   |   CAGR without leader fixed ledger |   Sharpe without leader fixed ledger |
|:------------|--------------:|--------------------------:|----------------------------:|:----------------|-----------------------------------:|-------------------------------------:|
| C01         |      0.057310 |                  0.177758 |                    1.369279 | Realist Capital |                           0.163921 |                             1.323856 |
| C02         |      0.057438 |                  0.154014 |                    1.212822 | Realist Capital |                           0.141172 |                             1.154520 |
| C03         |      0.067128 |                  0.199079 |                    1.534953 | Realist Capital |                           0.185922 |                             1.465509 |
| C04         |      0.060350 |                  0.165436 |                    1.303870 | Realist Capital |                           0.140443 |                             1.120438 |
| C05         |      0.054865 |                  0.173097 |                    1.367201 | Realist Capital |                           0.156179 |                             1.280607 |
| C06         |      0.060350 |                  0.148254 |                    1.162090 | Realist Capital |                           0.138415 |                             1.094634 |
| C07         |      0.151570 |                  0.225513 |                    1.422212 | Delta_01        |                           0.224952 |                             1.248214 |
| C08         |      0.151570 |                  0.219186 |                    1.382266 | Delta_01        |                           0.218180 |                             1.209237 |
| C09         |      0.060350 |                  0.163278 |                    1.270500 | Realist Capital |                           0.143680 |                             1.142687 |
| C10         |      0.151570 |                  0.224670 |                    1.414956 | Delta_01        |                           0.224440 |                             1.241576 |
| B01         |      0.054258 |                  0.141381 |                    1.152120 | Realist Capital |                           0.125269 |                             1.053733 |
| B02         |      0.151570 |                  0.221963 |                    1.396907 | Delta_01        |                           0.220853 |                             1.221916 |

## Allocation contrasts
| Candidate   | Reference   |   CAGR difference (pp) |   Sharpe difference |   Drawdown difference (pp) |   Final equity difference (USD) |
|:------------|:------------|-----------------------:|--------------------:|---------------------------:|--------------------------------:|
| C07         | C03         |               5.355112 |           -0.116970 |                  -2.152912 |                    51562.917933 |
| C07         | B02         |               0.369152 |            0.022034 |                  -0.000000 |                     3741.298039 |
| C08         | C03         |               4.697089 |           -0.152004 |                  -2.207870 |                    44913.634902 |
| C08         | B02         |              -0.288872 |           -0.013000 |                  -0.054959 |                    -2907.984992 |
| C10         | C03         |               5.267435 |           -0.123222 |                  -2.152912 |                    50671.759906 |
| C10         | B02         |               0.281475 |            0.015782 |                  -0.000000 |                     2850.140012 |

Most of the long-period allocation-family gain is already present in the regularised90 benchmark: compare C07 directly with B02 before attributing it to the gap estimator. New allocations have worse drawdown and lower Sharpe than the original four-input source candidate, despite greater CAGR. Q4 2024 and sparse valuation timing materially affect the result.

## Hypothesis verdict and next leads

The descriptive hypothesis is supported against v11, but there is no consistent allocation-family winner across years. C07 returns 45.86% in 2024 versus C03’s 24.41%; it then trails C03 in 2025 (25.21% versus 29.15%) and carried 2026 (29.41% versus 32.67%). The highest fresh-2026 Sharpe candidate, C04, is not the full-history Sharpe leader. C03 retains the strongest long Sharpe; C07 has the highest CAGR with greater drawdown. The isolated gap-estimator improvement over regularised90 is only about 0.37 percentage points CAGR and 0.02 Sharpe.

Relative performance is descriptive: 2026 selection overlaps the full period and earlier years were already searched. Earlier and new candidates can be compared with the same archive, but this replay does not provide independent confirmation. Early low deployment and changing vault availability depress full-calendar CAGR. Use the quarter/cash plots to distinguish these effects from poor selected-vault performance. Next, freeze a candidate and compare source versus simultaneous allocation on matched selection, then observe genuinely later data.

## Experiment 14 — more profitable allocation

### What was examined

Five allocation methods with fixed four-input ranking and six positions. Profit and CAGR are the main outcomes, accompanied by drawdown and cost attribution.

### Hypothesis

Redistribution, regularisation or downside-based sizing improves capital placement and net profit.

### Result

2026: profit leader **A**. Best challenger **B** changes profit by **$-1,342**, CAGR by -1.31 percentage points, and drawdown by -0.19 percentage points versus A.

Long: profit leader **G**. Best challenger **G** changes profit by **$+51,687**, CAGR by +5.32 percentage points, and drawdown by -3.46 percentage points versus A.

### Hypothesis verdict and useful leads

All three new mechanisms lose incremental profit in fresh 2026 and gain over full history. Redistribution alone adds little; the regularised estimator package supplies most of the historical gain, including its support and fallback differences. Downside sizing adds only $3,352 over C, with worse primary drawdown. The long quote-freshness sensitivity retains G’s $41,181 lead over A; the 2026 sensitivity retains A’s lead over B. Corrected observation-time pricing changes the comparable reference; old daily-close results are not mixed into the ranking. Sparse NAV execution and previously searched history remain limitations. See [NB14](14-backtest-profitable-allocation.ipynb) and [findings](14-profitable-allocation-findings.md).

## Experiment 15 — allocation candidates versus deployed v11

### What was examined

A, C and G from NB14 versus the deployed hyper-ai-v11 source rules, using fresh $150,000 accounts for 2026-01-01 through 2026-10-04 and full history from 2023-03-01 through 2026-10-07. Shared repaired inputs and as-of-observation NAV pricing; original sequential allocation and six positions throughout.

### Hypothesis

The four-input ranking improves on deployed v11 with original sizing; regularised variance and downside sizing may add a further economic advantage.

### Result — 2026-01-01 through 2026-10-04

| Strategy | Net profit | CAGR | Sharpe | Max drawdown |
|:--|--:|--:|--:|--:|
| Deployed v11 | $44,521 | 41.20% | 1.96 | −6.40% |
| A: four-input / source variance | $55,430 | 51.77% | 2.30 | −6.35% |
| C: regularised variance | $51,111 | 47.56% | 2.12 | −6.93% |
| G: regularised downside | $50,819 | 47.28% | 2.11 | −7.72% |

### Result — full history, 2023-03-01 through 2026-10-07

| Strategy | Net profit | CAGR | Sharpe | Max drawdown |
|:--|--:|--:|--:|--:|
| Deployed v11 | $108,947 | 16.35% | 1.28 | −7.92% |
| A: four-input / source variance | $162,108 | 22.53% | 1.65 | −7.92% |
| C: regularised variance | $210,443 | 27.53% | 1.56 | −10.73% |
| G: regularised downside | $213,794 | 27.85% | 1.54 | −11.37% |

### Hypothesis verdict and useful leads

The four-input ranking is descriptively favourable versus v11 in both periods, with higher profit and Sharpe and no worse maximum drawdown. The sizing extension is period dependent: C/G gain over full history but lose to A in fresh 2026. Most historical sizing uplift is already in C; G’s extra $3,352 comes with larger drawdown. C/G’s strongest quarter is 2024 Q4 and their biggest account updates include weekly NAV changes, so the advantage needs later-data validation.

All eight accounts passed weight/profit reconciliation, 24 NB14 metric checks and 6,936 successful fill timing checks. The current retrospective universe/guard, sparse executable NAV uncertainty and inherited partial-trim fee convention remain limitations. Keep A as benchmark and C as main historical challenger. See [NB15](15-backtest-allocation-vs-v11.ipynb) and [findings](15-allocation-comparison-findings.md).

### September 2026 cash investigation

The saved-state audit finds mean September cash of 41.6% for v11, 49.1% for A, 48.7% for C and 48.8% for G. A ends September with 60.5% cash and peaks at 74.0%. Across A’s 15 decision cycles, 96.9% of the sum of planned deployment shortfalls comes from combined concentration/TVL limits, 2.6% from blocked top-ups and 0.5% from allocator slack. These are repeated decision snapshots, not lost-profit attribution.

The ranking rotates out large-capacity Citadel and AceVault Hyper01 and replaces them with higher-scoring smaller vaults. With six positions and a 33%-of-vault-TVL cap, the selected basket cannot absorb the account; the six-slot limit disables residual-capacity extension. On 20 September, A has $194,853 deployable but the six vaults together admit only $72,560 before $1,354 of rejected top-ups. Actual cash after trades is about $127,624. All four methods reach the same dollar targets on that date. Known recent deposit observations explain the small rejected-top-up component; pending redemptions and pinned settlement capital are zero throughout September. This suggests investigating usable capacity in basket selection or replacement decisions. See [cash analysis](15-september-cash-analysis.md); an explanatory chart is embedded in NB15.


## NB16 — waterfall allocation versus NB15

[Notebook](16-backtest-waterfall-allocation-vs-v11.ipynb) · [findings](16-waterfall-comparison-findings.md). Completed 12 October 2026. Sixteen accounts compare V11/A/C/G with their matched waterfall variants over 1 January–4 October 2026 and 1 March 2023–7 October 2026, using NB15's repaired data, causal NAV prices and $150,000 fresh starts.

### What was being examined

Whether capped waterfall allocation improves profitability and reduces the September cash bottleneck. Performance ranking selects the same six-position core policy. Waterfall fills selected names by descending raw risk-sizing weight; the original risk estimators determine priority rather than proportional dollar shares. Admission checks, caps, hysteresis, thresholds and costs are retained. No additional capacity-extension positions are enabled.

### Was there a hypothesis?

Greedy allocation could improve deployment and economic results inside the selected basket. It cannot deploy beyond the basket's combined concentration/TVL capacity. The experiment separates these two possibilities.

### What was the result?

2026 results appear below. Full-history figures use an independent fresh account, overlap 2026 and retain previously examined years.

| Arm | 2026 CAGR | 2026 Sharpe | 2026 max drawdown | Full CAGR | Full Sharpe | Full max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V11-W | 31.57% | 1.55 | −6.64% | 15.36% | 1.20 | −8.66% |
| A-W | 48.89% | 2.14 | −6.07% | 22.58% | 1.65 | −7.92% |
| C-W | 51.35% | 2.23 | −6.08% | 30.96% | 1.73 | −10.33% |
| G-W | 56.19% | 2.46 | −6.81% | 29.94% | 1.60 | −12.83% |

Waterfall improves C's profit, CAGR, Sharpe and drawdown in both periods. It improves G's return and Sharpe in both, but worsens full-history drawdown. V11 loses in both periods; A loses 2026 profit and adds only $445 over full history. C-W adds $36,193 over C in full history; G-W adds $9,119 over G in 2026.

September mean cash stays at 39.7% for V11-W, 48.5% for A-W, 48.9% for C-W and 49.5% for G-W. The six-vault capacity constraint remains. G-W's 2026 gain over G is led by pmalt (+$9,182, 100.7% of the net advantage); other changes partly offset it. C-W's full gain over C is led by Citadel (+$17,265, 47.7% of the net advantage).

### Was the hypothesis confirmed or rejected, and why?

The profitability hypothesis receives descriptive support for regularised-risk waterfall, especially C; it fails as a universal allocator improvement. The hypothesis that waterfall inside six slots resolves September cash is rejected. The advantage reflects exposure and timing changes while combined capacity remains binding.

### What useful new leads did we learn?

Keep C-W as a historical allocation challenger and G-W as a stronger 2026 candidate with a less favourable long-period drawdown. Investigate pmalt sensitivity before generalising G-W's advantage. Test conditional residual-capacity extension separately from greedy sizing, preserving the preferred core and comparing marginal deployment with cash.

### Robustness and execution qualification

All eight original accounts reproduce NB15 in 32 metric checks; 12,936 successful fills match known NAV, and weights/profit reconcile. All 14 separate figures were visually inspected; the final repeat reproduces every metric exactly. Large historical updates reflect six/seven-day NAV intervals during large BTC/ETH moves, while the strongest 2026 update involves Realist Capital and Goon Edging during a declining market.

Uncorrected A-W failed on 12 July with a buy $94.63 beyond net available cash after source sell-price charges. A scoped correction retains the charges and reduces buys only to final available synchronous proceeds. Two 2026 queues, A-W and C-W, required $170.06 of total buy reductions; no full-history queue required correction. All 1,875 original-control trade queues were checked and would require no correction. The inherited partial-trim fee convention, sparse executable-NAV uncertainty, retrospective universe/guard and absence of an independent holdout remain limitations.

## Experiment 17 — capital allocation

### What was examined

Fourteen fixed allocation policies, both periods, plus shared corrected-partial-fee sensitivity. The score and risk estimator stayed fixed; mechanisms varied redistribution, capacity selection, conditional overflow, turnover retention and joint optimisation.

### Hypothesis

Better usable-capacity selection and controlled overflow can overcome the six-name ceiling and improve net profit. Lower cash alone is insufficient.

### Results

- **2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC):** M10 (One-decision rank-exit confirmation) leads net profit at **\$55,676**, **52.01% CAGR**, **2.15 Sharpe**, **-10.25% maximum drawdown**; **\$+669** versus exact C-W.
- **2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial):** M05 (Core + four score-first overflow) leads net profit at **\$296,112**, **35.30% CAGR**, **1.65 Sharpe**, **-12.12% maximum drawdown**; **\$+49,476** versus exact C-W.
- **M05, fresh 2026:** September cash 4.8% versus 48.9%, with **\$-11,598** incremental net profit. Better deployment did not establish better economics.
- **M08, fresh 2026:** September cash 1.8% versus 48.9%, with **\$-18,603** incremental net profit. Better deployment did not establish better economics.
- **M11, fresh 2026:** September cash 1.8% versus 48.9%, with **\$-19,809** incremental net profit. Better deployment did not establish better economics.
- **M13, fresh 2026:** September cash 3.5% versus 48.9%, with **\$-64,862** incremental net profit. Better deployment did not establish better economics.

Correcting partial-trim fees reverses the fresh-2026 exit-delay lead: C-W **58.58% CAGR** versus M10 **57.17%**. Full-history four-slot overflow remains ahead after correction: **37.73%** versus **33.13%**. The primary long-period gain includes **\$+38,137** from [ Systemic Strategies ] L/S Grids, relative to **\$+49,476** total incremental profit. Scored-only overflow reduces long CAGR from **35.30%** to **27.86%**.

### Was the hypothesis confirmed?

Methods with higher net profit in both researched periods: none. The broad claim of a more profitable replacement across both periods was rejected for this registered set. Four-slot overflow provides a long-period lead, while better cash deployment often loses profit in fresh 2026. Both periods overlap and have been researched.

### Robustness and implementation checks

The audit covers 23,492 successful fills, 14,892 core-target equality checks and 2,718 core-first funding checks. Maximum position-PnL/equity reconciliation residual is below \$0.000000001. M11 uses the declared safe M01 fallback on four decisions (one in fresh 2026 and three in full history) after a solver target fails executable-domain checks. Its realised results therefore include these fallbacks; they do not establish a globally optimal executable portfolio on every date.

### Useful leads

Keep C-W as a pinned control, compare corrected fees consistently, and freeze profit/risk leaders for prospective observation. Capacity must be handled at basket/overflow selection, not only within-basket weights. Inspect contributor dependence, missing-score exposure, deferred fees and rank-exit churn before choosing a production rule.

See [complete findings](17-capital-allocation-findings.md) and [executed notebook](17-backtest-capacity-aware-allocation.ipynb).

## Experiment 18 — conditional cash allocation

### Key new insights

- **2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC):** C00 leads with **58.58% CAGR**, **2.49 Sharpe**, **-6.09% drawdown**, and **\$62,366 profit**; **\$+4,104** versus C01. September cash is 49.8%.
- **2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial):** C02 leads with **37.73% CAGR**, **1.72 Sharpe**, **-12.09% drawdown**, and **\$325,750 profit**; **\$+57,160** versus C01. September cash is 23.3%.

- A method wins only through net economics, not cash usage. No conditional method improves profit, Sharpe and drawdown against C01 on both periods.
- The gradual treatments produced 0 genuinely interior alpha decisions in fresh 2026. Zero/full scaling and minimum tickets can make a continuous formula economically discrete; inspect the activation table before crediting forecast precision.
- Score calibration is conditional on resolved marginal outcomes. Missing scores remain eligible through their own supported group or pooled fallback, and unknown terminal outcomes are not flat zero returns.
- The gross-exposure safety conversion reserves current modelled accrued exit charges, because source targets use marked-equity dollars. Core risk includes suppressed small trims and pinned gross holdings; new cash cannot borrow artificial risk headroom from net marks.
- Adding the economic exit changes profit by **\$+1,666** in 2026 and **\$+15** over full history. The admission-aware C01 core itself differs from exact C-W by **\$-4,104** in 2026, before any new sleeve is added.
- A profitable score threshold is **not established** if its gate admits no new dollars. Keeping cash can outperform an unprofitable sleeve without demonstrating which extra vaults to buy.
- The matched core's median closed-position lifetime is **4 days** in 2026, versus the registered **30-day** forecast horizon. These lifetimes include core positions and are not an exact sleeve holding-period estimate, but the mismatch is a concrete lead for a small horizon-alignment study rather than more score bands.

### Summary of results

All eighteen registered accounts use corrected partial-trim fees and the same pinned inputs. Fresh 2026 is the default; the full-history account starts in 2023, shares a causal full-history C01 risk reference, and carries early profits into 2026. Controls retain six/ten slots; all new methods permit at most twelve total and six residual names. Forecast-free R00 is the primary check on the value of estimation.

#### Hypothesis verdicts

Profit differences use matched controls; risk-budgeted R00 versus C02 is a package contrast, not an isolated risk coefficient test.

| Hypothesis | Verdict | Evidence |
|:--|:--|:--|
| H1: Risk-limited package beats unconditional overflow | mixed / not established | R00−C02: 2026 \$+4,772; full history \$-73,396. |
| H2: Score admission improves the same risk sleeve | supported on both researched periods; 2026 benefit, if any, is avoiding exposure, not identifying profitable admissions | R03−R01: 2026 \$+454; full history \$+12,134. |
| H3: Gradual sizing improves binary admission | mixed / not established | R04−R03: 2026 \$+0; full history \$-756. |
| H4: Additional positions complement the core | rejected on both researched periods | R00−C01: 2026 \$-2,120; full history \$-16,235. |
| H5: robustness to support/cost/concentration | qualified, not independently confirmed | Corrected-fee controls reproduce; 0 executed risk/exposure breach flags. Highest positive-vault concentration is 38.4% (C02, 2026). Retrospective universe and unresolved labels remain limitations. |

### Robustness of results

- The two periods overlap and were researched earlier. Neither monthly causal fitting nor full-history replay makes them untouched validation.
- Daily NAV is carried only after inception; actual update counts determine confidence. Recorded as-of NAV does not prove executable NAV, and publication availability remains unverified.
- Thirty-day labels require a terminal supporting observation, with its availability included in maturity. Resolved training can still favour surviving vaults; unresolved lower bounds assume complete loss and upper sensitivity is unbounded.
- The shared risk anchor is a lagged median of a hypothetical 98%-invested reference mix; it may be infeasible under dollar capacity and adapts to persistent volatility. The perfect-correlation measure is conditional on imperfect marginal estimates, not a maximum-loss guarantee. Core exposure is not reduced to enforce an overall account risk tolerance.
- Economic exit forecasts apply fees to every scenario using remaining cost basis. The fixed-horizon hold-versus-cash model omits reinvestment/optimal stopping. Paid charges and still-open liabilities are shown separately.
- Corrected partial trims reproduce the registered controls, but generic post-trade valuation uses the protocol pricing route rather than the source’s instance-level wrapper. Cached pair exit-tax rates can persist on a closed vault and affect the mark when it is reopened, while the fresh source wrapper uses its fallback rate for that pair. The sleeve mirrors the generic route’s actual quote and verifies a conservative post-trade denominator; gross NAV, estimated single-fee liquidation and engine marks are displayed separately. This is not a claim that all inherited valuation conventions are economically correct.
- Fresh-proposal, matched random/ungated and cap/slot diagnostics lack sleeve feedback. They do not establish independent strategy performance or an optimal number of positions.

### Smallest useful next step

Keep the simpler control unless a treatment improves the economic trade-off in a genuinely later period. Calibrate a small, frozen marginal-opportunity population that actually survives risk limits and minimum tickets, then inspect forecast support and accepted dollars before another engine search. The current calibration includes all feasible non-core deposits, not only the next executable slot; its negative pooled forecast need not mean every possible extra vault is unprofitable. Explicitly choose tolerable loss/exposure limits before changing production. Six positions remains a baseline; this experiment does not prove its optimality.


## Experiment 19 — protected core with score and risk sizing

### What was examined

The exact source C-W six-position core, with additional positions sized by flat, risk-only, score-only or combined absolute tickets. Combined tickets also receive a two-day resizing treatment and a normalised control. Eight, ten and twelve total slots, a lower score floor and smaller caps are registered comparisons. Eleven methods run as independent accounts for fresh 2026 and full history, starting with \$150,000 each; all preceding indicator history is available. Core entry6/exit8 and its regularised 90-day inverse-variance waterfall remain fixed.

### Hypothesis

More than six holdings can improve net profit if weaker additional positions receive less capital. Score and risk together should improve sizing; absolute tickets leave attenuated capital as cash; holding units should reduce harmful turnover. Complete historical zero-extra replay parity is a prerequisite.

### Results

| Period | Method | CAGR | Sharpe | Maximum drawdown | Net profit | September cash |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2026-01-01 → 2026-10-05 exclusive | C00 | 58.59% | 2.47 | −6.36% | \$62,376 | 49.75% |
| 2026-01-01 → 2026-10-05 exclusive | RS00: combined, hold units | 54.50% | 2.32 | −7.29% | \$58,219 | 38.26% |
| 2026-01-01 → 2026-10-05 exclusive | RS01: combined, resize | 58.84% | 2.48 | −6.45% | \$62,631 | 42.68% |

Fresh 2026 is the main comparison. Full history, **2023-03-01 → 2026-10-08 exclusive**, gives RS01 **33.66% CAGR / 1.67 Sharpe / −9.94% drawdown**, versus C00 **33.13% / 1.65 / −9.94%**: approximately **\$6,069** additional profit. The last archive day is partial. These are overlapping, previously researched periods.

RS01 leads CAGR and Sharpe in both periods, but its fresh-2026 net gain is only **\$255**, with slightly worse drawdown. Interval-start role accounting assigns **−\$189** to additional holdings and about **+\$444** to core/other feedback relative to C00. That reconciliation is bookkeeping, not causal evidence of a profitable additional sleeve.

### Was the hypothesis confirmed or rejected?

- **Extra breadth alone:** mixed; flat E00 loses about \$4,125 in 2026 and gains \$4,524 over full history.
- **Combined score/risk beats risk-only hold:** rejected for these methods; RS00 loses to R00 in both periods.
- **Absolute versus normalised resize:** supported descriptively; RS01 beats NRS00 by \$2,381 / \$6,924. It does not establish predictive value from score, because exposure paths and execution differ.
- **Hold units beats resizing:** rejected; RS01 gains \$4,411 / \$3,972 over RS00.
- **More slots are better:** rejected as a general claim; twelve-slot hold loses to eight-slot hold in both periods.
- **Floor/cap robustness:** mixed. Lowering the score floor loses modest profit in both histories; reducing caps helps 2026 but hurts full history. No optimal coefficient or statistically established improvement is demonstrated.

### Robustness and accounting

Complete historical C00/P00 equity and trade parity passes in both periods. Independent source core intentions, unchanged merged core targets and core-first funding are checked throughout. Executed gross single/total limits, slot ceilings and conservative equity bounds pass. Formula, sparse-data and isolated adapter fixtures cover missing entry, blocked top-up, source bands, pins, promotion and held-role isolation. No actual pinned positions occur in these accounts; asynchronous venue settlement is not validated by this experiment.

A common local entry-pricing correction resets cached tax left by a previous closed position before reopening. All economic arms share the correction. Historical C00 remains a separate replication. Its final profit changes only about \$10 in 2026 / \$25 over full history, but Sharpe changes from **2.49 to 2.47** / **1.82 to 1.65** because temporary intermediate marks change. The archive did not change during NB19. Do not compare repaired challengers with unrepaired historical Sharpe.

All accounts share a strong 26 June 2026 update, chiefly Realist Capital and Goon Edging, over about two observed days while BTC/ETH decline. Realist supplies about 35% of positive 2026 vault profit. The strongest long update is in November 2024, before treatments diverge, so it cannot explain their relative gains. Contributor deletion, daily-update/quarter deletion, locked-slot outcomes, paid/open costs, loss stress and common-state capacity/risk diagnostics are included. Sparse recorded NAV still does not prove executable quotes; retrospective universe/guard and inherited exit-fee assumptions qualify the economics.

### Useful new leads

Keep C00 as the benchmark and RS01 as a modest historical challenger. The strongest lead is management of exposure over time, rather than more aggressive deployment or a proven benefit from multiplying by score. Compare a small frozen resizing rule in later data, inspect why core feedback generates the apparent uplift, and preserve the cash option. September cash remains above 42% for RS01 in fresh 2026; reducing it further is not itself a profit objective. Common-state unlimited normalisation also exposes a floor problem: spreading a fixed budget across too many names can make nearly all tickets unexecutable.

See the [executed notebook](19-backtest-protected-core-score-risk-allocation.ipynb), [complete findings](19-protected-core-score-risk-allocation-findings.md), and [plan and formulas](19-protected-core-score-risk-allocation-plan.md).
## Experiment 20 — C00 versus deployed v11 rules

**Examined:** C00 versus v11, with common data and accounting, in 2026 and full history.

**Hypothesis:** C00 improves net economic outcomes over the deployed-rule strategy. The comparison is descriptive; no independent significance claim.

### Findings and useful leads


2026: C00 changes profit by USD +9,630, CAGR by +9.44 percentage points and Sharpe by +0.260. The largest positive vault contribution to the difference is [ Systemic Strategies ] L/S Grids, USD +4,868 (50.5% of the net account gap).

Long: C00 changes profit by USD +143,804, CAGR by +14.58 percentage points and Sharpe by +0.278. The largest positive vault contribution to the difference is Road to 10 Million, USD +26,941 (18.7% of the net account gap).

C00 improves historical CAGR and Sharpe in both periods, supporting the economic hypothesis on these inspected samples. Full-history drawdown is worse, so this is not an improvement in every risk measure. In 2026, C00 earns more despite higher average cash. Full-history differences also include earlier deployment and different accumulated wealth. Isolating score, risk estimation and waterfall contributions remains a separate experiment.

### Summary of results

| Period | V11 CAGR | C00 CAGR | V11 Sharpe | C00 Sharpe | V11 max DD | C00 max DD | C00 extra profit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026 | 49.15% | 58.59% | 2.214 | 2.474 | -6.41% | -6.36% | USD +9,630 |
| Long | 18.55% | 33.13% | 1.374 | 1.651 | -7.92% | -9.94% | USD +143,804 |

### Robustness of results

2026 C00: largest positive contributor Realist Capital accounts for 35.4% of positive vault profit; best daily update 6.46%, excess kurtosis 11.0. Long C00: largest positive contributor Delta_01 accounts for 17.2% of positive vault profit; best daily update 15.65%, excess kurtosis 90.9.

2026 C00 strongest update: Realist Capital contributes USD 6,419, with a 14.1% NAV change across 2.0 days; BTC and ETH change -4.7% and -6.0% over that observation interval. Curator excluded=False, quarantined=False.

Long C00 strongest update: Road to 10 Million contributes USD 15,536, with a 30.3% NAV change across 7.0 days; BTC and ETH change 19.6% and 17.1% over that observation interval. Curator excluded=False, quarantined=False.

C00 reproduces NB19's daily equity and metrics. All executed fills pass the as-of-NAV audit, and position profit reconciles to account profit within USD 1. Common partial-sell, cached-tax and funding corrections apply to both arms. Strongest vault updates are checked against curator flags and BTC/ETH over their actual observation intervals in the tables below. Sparse NAV may bunch returns; last-known NAV does not establish an executable live price. The two periods overlap and were previously researched; there is no untouched holdout or statistical significance claim. Universe/guard selection is retrospective and inherited fee assumptions remain economically unverified. No deployment-server revision was verified.
## Experiment 21 — marginal profitability and adaptive portfolio allocation


### What was examined

 increase net account profit by identifying capital worth investing, holdings worth retaining, and opportunities better left in cash. Challenge fixed six-position baskets, rank admission and prescribed inverse-variance allocation. Evaluate when positions are unlikely to profit, including young and missing-score vaults.

**Method:** reproduce C00/v11 under frozen NB20 accounting; audit fees and capital-weighted holding spells; fit monthly causal support, loss-probability, gain/loss-magnitude and calibrated-score forecasts; compare complete basis-aware hold/cash/top-up/replacement path values. Main challengers choose absolute allocations, breadth and cash under explicit capacity and estimated-downside budgets. Ten full-2026 accounts, a registered full-history shortlist and five local sensitivities. Features use completed prior daily buckets; preceding 2025 and earlier history remain available. Missing=True and sparse data use explicit masks/support priors. No untouched holdout exists.



### Hypotheses and verdicts

| Hypothesis                      | Verdict                          | Reason                                                                                                                    |
|:--------------------------------|:---------------------------------|:--------------------------------------------------------------------------------------------------------------------------|
| H1: churn optimisation          | Historical gain                  | One fixed wider-band account isolates net execution effects under the inherited fee model.                                |
| H2: conditional downside        | Probability gain                 | 30d Brier P/D 0.2497/0.2481; economic value must also beat P00.                                                           |
| H3: conditional magnitudes      | Not supported                    | M00 versus D00 holds the probability head, risk budget and allocator constant.                                            |
| H4: new construction beats C00  | Not confirmed                    | Best required new-construction row C01: profit difference USD -49,753, Sharpe 1.654 versus 2.474.                         |
| H5: incumbent decisions         | Not supported                    | Compare joint portfolio decisions with entry-only capital deployment.                                                     |
| H6: missing/young participation | Implemented; utility conditional | Masks, global fit/pooled fallback and actual allocations are reported; undefined metrics are not losses.                  |
| H7: robustness                  | Exploratory                      | No independent holdout; budget, horizon and margin extensions plus contributor/fee/solver diagnostics remain conditional. |

### Results

The strongest required challenger is **C01**, with 11.28% CAGR, 1.654 Sharpe and -1.90% maximum drawdown, versus C00’s 58.59%, 2.474 and -6.36%. Its net account profit difference is **USD -49,753**. This is a researched historical comparison, not independent evidence of future profitability.

Conditional downside probability has 30-day Brier error 0.2481, versus the support prior’s 0.2497. The signal ladder and calibrated-score control distinguish feature value from construction. The highest-profit long new-construction challenger is D03, CAGR 8.62%, Sharpe 1.456, compared with C00 33.13%/1.651.

The notebook evaluates adaptive breadth, incumbent replacement and cash decisions under complete basis-aware path values. The risk-budget-free arm exposes whether the new budget merely restrains profitable exposure. Main weights are not prescribed by inverse variance. Caps, ticket minima and weak forecasts can still determine the realised basket.

The wider sell band F01 adds only **USD 116** in 2026 and **USD 1,025** over the long calendar. Its 2026 drawdown is slightly worse; the long gain is not explained solely by lower paid fees. This is a small execution lead, not a substantial improvement.

At C00’s selected names, the supported 30-day fresh-unit net outcome averages **1.81%**, while D forecasts **-1.23%**. Population-wide probability improvements therefore do not imply useful calibration at the profitable investment margin. These overlapping observations are an opportunity diagnostic, not account attribution.

The H07 sensitivity reaches **26 vaults**, with **99.87%** average September investment, yet loses **USD 23,654**. Removing the risk budget also loses money, and D02 exactly matches D00: six slots were not the binding constraint in that comparison. Retaining incumbents helps D03 relative to D00, but leaves it far behind C00. Better cash use requires better marginal forecasts, not merely more slots or looser risk limits.

M00’s largest marked loss is concentrated in **$🏧| ATM |🏧$**, on **2026-04-09**, with USD -29,497 attributed to that vault. The NAV interval, curator status and BTC/ETH context are reported below; a major single-vault loss is not evidence that probability calibration alone controlled tail severity.

The long D03 retention account reaches 57.24% in one vault through inherited position drift. Its better retention result does not demonstrate concentration control; failure stresses must consider the actual grown exposure.

| Arm   | CAGR    |   Sharpe | Maximum drawdown   | Net profit (USD)   | September cash   |   Maximum vaults held |
|:------|:--------|---------:|:-------------------|:-------------------|:-----------------|----------------------:|
| B00   | 58.59%  |    2.474 | -6.36%             | $62,376            | 49.75%           |                     6 |
| B01   | 49.15%  |    2.214 | -6.41%             | $52,746            | 42.70%           |                     6 |
| F01   | 58.70%  |    2.479 | -6.46%             | $62,492            | 48.97%           |                     6 |
| P00   | 10.44%  |    1.53  | -2.01%             | $11,701            | 100.00%          |                     5 |
| D00   | -2.73%  |   -1.526 | -2.30%             | $-3,112            | 100.00%          |                     6 |
| M00   | -39.74% |   -1.846 | -32.09%            | $-47,722           | 7.62%            |                     8 |
| C01   | 11.28%  |    1.654 | -1.90%             | $12,623            | 100.00%          |                     4 |
| D02   | -2.73%  |   -1.526 | -2.30%             | $-3,112            | 100.00%          |                     6 |
| D03   | 3.19%   |    0.737 | -2.86%             | $3,600             | 16.53%           |                     6 |
| D04   | -17.85% |   -2.127 | -14.55%            | $-20,726           | 100.00%          |                     8 |

#### Full-history comparison — 2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial)

The frozen three-candidate shortlist, both controls and the wider-band diagnostic use fresh accounts and genuine historical model cold starts.

| Arm   | CAGR   |   Sharpe | Maximum drawdown   | Net profit (USD)   |
|:------|:-------|---------:|:-------------------|:-------------------|
| B00   | 33.13% |    1.651 | -9.94%             | $270,882           |
| B01   | 18.55% |    1.374 | -7.92%             | $127,078           |
| C01   | 0.86%  |    0.145 | -18.01%            | $4,716             |
| P00   | 5.68%  |    0.654 | -14.32%            | $33,057            |
| D03   | 8.62%  |    1.456 | -4.62%             | $52,076            |
| F01   | 33.22% |    1.664 | -9.92%             | $271,907           |

### Useful leads

Preserve C00 as the economic benchmark. Investigate calibration on the feasible selection margin and a reliable asymmetric loss model before giving these forecasts control of the portfolio. Distinguish prior-dominated young vaults from well-supported names without discarding missing features. The conditional-magnitude model requires tail and extrapolation diagnostics after its large loss. A wider sell band merits a small execution follow-up; additional numerical optimiser complexity is a lower priority because the sampled same-state solver gaps are negligible. Separate incumbent sell decisions from fresh-entry forecasts: D03’s retention ablation helped, but did not establish an improved strategy. Increasing breadth or removing downside restraint alone did not solve profitability.

### Robustness

Independent source controls match NB20 daily equity and every trade; all daily equity paths match to below USD 0.000001. Independent fee/basis and sparse-fill examples passed, and every successful fill was checked against as-of NAV. Engine decision dates and forecast dates are explicitly aligned on both calendars; forecasts are not shifted backwards from a future date. Additional long prediction origins and the last completed feature bucket use the same archive, with the original training and budget samples retained. The base policy horizon is 30 days; the short-holding audit includes dollar-days and censored open positions.

Forecasts refit monthly with matured prior labels. Penalties are selected once per horizon/year using preceding purged probability folds; magnitude heads share that penalty, a disclosed computational compromise. Learning endpoints use actual marks; carried engine outcomes are a sensitivity. The margin arm addresses common calibration uncertainty only, not full personalised coefficient uncertainty.

The allocator is a numerical greedy approximation. Convergence, projection differences and continuous same-state bounds are reported; the frozen denominator and later marked-equity changes can leave inherited cap drift. Gain/loss heads retain the full date measure when conditioning; their mixture passes an exact weighted-mean fixture. The simple loss budget does not provide a guaranteed tail bound or reward diversification by itself.

Fees remain the inherited 10% positive-profit charge plus 0.1% capital allowance, rather than verified live fees. Universe and guard history are retrospective. Largest contributors and strongest NAV intervals are checked with curator flags and BTC/ETH context; fixed-ledger contributor deletion and failure stresses are descriptive. No independent significance or deployment claim is made.
## Experiment 22 — C00 entry-margin calibration


## What was examined

Whether existing NB21 forecasts become economically useful near C00's fresh-entry boundary after calibrating the shared net-return level and relative spread separately. C00 selection, six slots, regularised 90-day risk, waterfall and constraints remain unchanged. Inputs are the frozen NB20/21 repaired generation.

## Hypotheses and method

H1: fresh entries contain avoidable downside; H2: supported D ordering and calibrated absolute levels identify selectively weak entries; H3: the selective veto improves account economics beyond whole-entry controls. Initial-buy units are attributed proportionally through actual net sales/top-ups. Sparse endpoint labels carry only known NAV, require a subsequent actual report, and become trainable only after confirmation. Horizon selection and the account qualification use fully matured pre-2026 entries only; 2026 model updates remain causal but exploratory. Missing and young vaults are retained, with unsupported D passing through C00.

## Result — 2026-01-01–2026-10-04 UTC

- **Stopped before conditional accounts.** Registered horizon: **7 days** from 151 pre-2026 executable entries; common horizon-alignment cohort: 144 fully closed spells.
- Closed 2026 initial cohorts: 101 spells; frozen initial-entry loss headroom **$23,985**, versus C00 account profit **$62,376**. Equal-spell median lifetime 4.0 days; initial-cash-weighted mean 11.4 days. Loss headroom is not a veto-policy profit bound.
- Pre-2026 actionable entries: **96 / 151**; vetoes **19**. Closed-spell avoided value **$6,133**; per resolved veto dollar **1.09%** (undefined if no veto dollars).
- 2026 actual-entry activation: **36 vetoes**. Calibrated L2 H7 band MAE **4.51%**, equal-origin rank IC **-0.065**, sign accuracy **49.0%** versus constant-level baseline **49.3%**. These forecast statistics alone do not establish a trading advantage.
- The calibrated mean forecast bias improves from **-0.91 to -0.19 percentage points**, but its MAE exceeds matched L0's **4.18%**. Correcting levels did not rescue 2026 relative ordering.
- Unchanged 2026 C00: **58.59% CAGR, 2.474 Sharpe, −6.36% drawdown**; v11: **49.15%, 2.214, −6.41%**. No unexecuted overlay receives a performance claim.

## Qualification and hypothesis verdicts

The closed-spell selective value is **1.09% per resolved veto dollar**, compared with the blocked-control median **1.19%**. The pre-cutoff mark-only scenario changes the avoided value to **-4,742 USD**. The gate therefore fails both timing control and missing-spell sensitivity. Complete failed checks: **above median block placebo per resolved dollar; positive pre-2026 mark-only value; mark-only lead survives identity/block controls**. H1 loss headroom is descriptive, not identified preventability. H2's registered selective-benefit hypothesis is not demonstrated. H3 remains untested when accounts stop; this does not prove no improved strategy exists.

Pre-2026 unresolved veto dollars: $165,060. Mark-only avoided value: $-4,742; loss-to-zero scenario: $171,193. Break-even positive unknown mean: 3.72%, undefined where unresolved mass is zero. Positive unknown outcomes have no finite upper bound; carry is not a universal adverse bound.

## Full-history diagnostic — 2023-03-01–2026-10-07 UTC

Fresh independent C00 ends at $420,882, **33.13% CAGR / 1.651 Sharpe / −9.94% drawdown**; v11 ends at $277,078, **18.55% / 1.374 / −7.92%**. Final archive day partial. Early unsupported forecasts pass through. These overlapping calendars are researched history; the qualification/horizon configuration is retrospective for the long account.

## Useful leads and limits

Entry-level managed economics and calibrated-band forecasts answer different questions. Short holding labels can miss source-managed exits, top-ups and re-entry; headline IC is not a licence to shut off profitable core exposure. The registered pass-through protects young/missing/pool-only observations from unsupported vetoes. The next change needs evidence on actual executable entry identities and managed outcomes, not a rescued threshold after looking at 2026.

H7 has lower past-only equal-origin capital-weighted discrepancy with managed returns than H2 (8.05% versus 10.92%); even H7 is an approximation. L2's expanding within-band slope falls from about 2.39 in January to 0.04 in October as 2026 outcomes mature. Its confidence intervals include zero; mathematical identification is not reliable forecasting. Losses concentrate in vaults that also supplied important gains, so a vault-level exclusion would not follow from this audit.

Saved-state control parity and frozen-D distribution parity were checked. All 139 native 2026 decisions have cached features. The Long-account cache omits 28 initial inactive native warm-up decisions; their candidate population is unknown, not silently assumed empty. These dates have no source targets or executable fresh entries, and no forecast can veto them. Reported long-band statistics use covered origins; full account economics retain all cash-only days. Primary labels remove the old one-day endpoint exclusion, but the frozen underlying D training still has NB21's freshness-selection limitation; H2 penalty-fold support warnings are disclosed. All saved C00 trades succeeded synchronously, and every buy's planned funded reserve equals executed reserve: actual first buys recover its executable fresh-entry schedule. Selected targets below executable floors remain separate intent diagnostics. Recorded NAV/permission chronology, retrospective guard/inventory, assumed fees, open/disappeared outcomes and repeated-vault/calendar dependence remain limits.

The frozen reference audit attributes 35.4% of C00's positive 2026 vault profit to Realist Capital. The best 2026 account update is +6.46%; Realist Capital and Goon Edging NAVs rise roughly 14% over about two days while BTC/ETH fall over the same observation interval. This is not broad-market confirmation. Sparse NAV can bunch returns; the recorded curator flags do not establish executable price truth.

The optional component factorial is **not executed**. No extra model, threshold, seed search, capacity expansion or unrelated notebook change was introduced.


## Experiment 23 — C00 backtest in the NB160 layout

Notebook: [23-backtest-c00.ipynb](23-backtest-c00.ipynb).

### What was examined

Present the fixed C00 strategy in NB160’s single-backtest outline, with parameters, indicators, algorithm, cash usage, equity, absolute asset weights, rolling performance, monthly returns, positions, trade reports and vault statistics. Add a separate comparison against the local `hyper-ai-v11.py` rules. Run independent USD 150,000 accounts for 2026 and full history under NB20’s corrected common accounting.

### Hypothesis

This is a reporting and replication experiment. Moving the strategy into the new layout should reproduce NB20’s account economics, complete equity paths and successful trade sequences.

### Result

All four accounts reproduce NB20. Maximum daily equity difference is below USD 0.000001; C00 reproduces 473 successful trades in 2026 and 1,044 over full history. V11 reproduces 575 and 1,087 respectively.

The table compares the independent accounts for **2026-01-01–2026-10-04 UTC**.

| Metric | C00 | V11 |
| --- | ---: | ---: |
| Final equity | USD 212,376 | USD 202,746 |
| CAGR | 58.59% | 49.15% |
| Sharpe | 2.474 | 2.214 |
| Maximum drawdown | −6.36% | −6.41% |

For **2023-03-01–2026-10-07 UTC**, C00 returns 33.13% CAGR, 1.651 Sharpe and −9.94% maximum drawdown; v11 returns 18.55%, 1.374 and −7.92%. The final archive day is partial. Full-history monthly charts omit the source engine’s initial cash-only tick before the requested start; the account metrics retain NB20’s exact calculation.

### Hypothesis verdict

Replication confirmed. The layout introduces no new strategy configuration or economic improvement. C00’s higher historical CAGR and Sharpe, and deeper full-history drawdown, remain the same as NB20.

### Useful leads and limitations

Use NB23 to inspect C00’s fixed rules and compare it with v11. The notebook uses the existing validated research execution helpers; it is not an exported production strategy module. Both accounts retain the same fee assumptions and accounting corrections. Curator checks and BTC/ETH comparisons over actual NAV observation intervals document profit concentration and isolated jumps. These overlapping, previously researched periods provide no untouched validation.

## Follow-up research after PR #61

[Next research leads](next-research-leads.md) records the prioritised unresolved questions and a proposed four-policy C00 sell-band × RS01-management experiment. The standalone historical gains are small; the interaction is unmeasured. The document distinguishes this bounded economic comparison from the larger unfinished work on managed downside forecasts, exact current-accounting component attribution, accepted portfolio risk and supported spare-capacity allocation. These are plans, not additional executed experiments.
