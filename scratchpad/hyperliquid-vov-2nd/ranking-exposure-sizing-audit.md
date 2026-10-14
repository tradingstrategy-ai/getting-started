# Ranking, exposure and sizing: audit of existing research

Reviewed 13 October 2026. This is a retrospective audit before choosing another experiment. No backtest, optimiser or forecast was rerun, and no strategy rule was changed.

## Scope and evidence

The audit covers the current `hyperliquid-vov-2nd` series and its earlier research branches: `vault-of-vaults`, `hyperliquid-waterfall-rc`, `hyperliquid-ic`, `hyperliquid-lower-vol` and `hyperliquid-vault-model`. Duplicate notebook numbers, superseded notebooks and profiling copies are retained in the coverage inventory. Nested scatter catalogues and NB10 appendices are supporting outputs, not additional independent trials.

### Notebook coverage

The main series contains 360 notebooks. There are also 51 current-folder chart/table/archive companions and seven lower-vol verification notebooks: 418 notebook files in total, excluding ignored run artefacts and checkpoint copies. The verification notebooks are mechanical checks, not seven new economic hypotheses.

| Folder | Main notebooks | Companion/verification notebooks |
| --- | ---: | ---: |
| hyperliquid-vov-2nd | 21 | 51 |
| vault-of-vaults | 167 | 0 |
| hyperliquid-waterfall-rc | 91 | 0 |
| hyperliquid-ic | 32 | 0 |
| hyperliquid-lower-vol | 41 | 7 |
| hyperliquid-vault-model | 8 | 0 |
| Total | 360 | 58 |

We extracted notebook JSON, Markdown, source configuration and saved named result tables, cross-checking consequential conclusions against later corrections. A notebook with saved old results but interrupted/unexecuted current cells is not treated as a successful current rerun. Generated evidence and per-notebook inventories are retained locally under `_artifacts-restored-2026-10-07/research-knowledge-audit/`.

Earlier branches use different archives, universes, dates, capital, valuation and fee conventions. Their metrics are cited only inside their own experiment comparisons. NB20/NB21 provide the most recent common-accounting C00/v11 comparison; old 41.20% v11 or 51.77% four-input numbers belong to an earlier accounting generation. The short and long periods overlap and have repeatedly been researched. They are not independent holdouts.

## Answer in brief

All three questions have already been investigated. The useful distinction is a way to interpret the existing evidence, rather than an untried experimental design.

| Question | Existing evidence | What we can currently conclude |
| --- | --- | --- |
| Ranking: better vaults than peers? | IC feature/ranking tracks; VOV gate/rank ablations; current NB04–10, NB21 | Modest relative signal exists, particularly for future risk/Sharpe. A better relative rank need not imply positive absolute return, and marginal feature additions often add little conditional information. |
| Exposure: investing better than cash? | PSR gates, stability/monthly filters, cash controls, source overlays; current NB08, NB17–19, NB21 | No reliable, independently validated profitable admission threshold has been established. Some gates are inactive; others chiefly avoid unprofitable exposure. Operational cash constraints must be separated from a decision to stay out. |
| Sizing: distribute capital among opportunities? | Extensive matched baskets, risk/score/covariance maps, caps, recycle/waterfall and breadth tests; current NB10–20 | Sizing matters, but its benefit depends on selection, caps and execution. Regularised risk plus waterfall is a strong historical package; inverse variance, equal weights and broader books are not universal winners. |

## 1. Ranking: what is already learnt

### We have tested much more than two-component formulas

Current NB04–07 test metric/lookback matrices, three/four-input formulas, score maps, clipping, missing-score behaviour and position counts. NB08 examines 139 frozen recipes and 7/30/90-day future targets. NB09 examines individual inputs and K-ratio additions; expanded NB10 inserts inverse variance, inverse volatility and K into scores and allows different recipes for ranking and sizing.

Earlier VOV NB43–67 include Calmar/Sterling variants, confidence weighting, percentile composites, probabilistic Sharpe, Bayesian shrinkage, softmax and gate-versus-weight separation. Waterfall NB19–25 and later signal branches also change the selection and sizing roles separately. The field has not been restricted to inverse variance, volatility and equal weighting.

### Relative discrimination is modest, and stronger for risk than return

Current NB08, 2026 origins and 30-day labels: mean cross-sectional return IC is approximately **0.087–0.089**, compared with future-Sharpe IC **0.129–0.137**. The return intervals include zero. These are conditional on resolved labels and finite scores; the many vault/date rows are not independent observations.

Current NB09 adds six K inputs, including 360 days and maximum recorded history. At 30 days, existing versus existing-plus-K forecast IC changes from **0.067 to 0.069** for return and **0.120 to 0.132** for Sharpe. Absolute return MAE does not improve from adding K. Only three complete paired 30-day blocks are available; 90-day paired model support is absent. K is a small conditional ranking lead, especially for future Sharpe, rather than a proven profitability selector.

Current NB10 reports selected-basket risk IC around **0.51–0.55**, materially stronger than return IC. However, realised carried-NAV risk is not certified executable economic risk.

Sources: [NB08 findings](08-score-forecast-findings.md), [NB09 findings](09-k-ratio-feature-forecast-findings.md), [NB10 original findings](10-portfolio-snapshot-findings.md).

### Relative outperformance can still select losing vaults

Corrected IC NB30 is a direct example. Lower-quartile rolling-return score Q25_7_60 has marginal return IC **0.089/0.123** at 30/60 days, but only **0.005/0.003** after growth, frequency and volatility controls. Its top group averages **−1.57%/−2.96%**, despite outperforming the rest. The corrected notebook supersedes the earlier stronger incremental-return narrative.

IC NB24 monthly consistency scoring saturates: shortlisted selected names have score exactly one, all three shortlist equity curves coincide, and **0/48 settings** pass the predeclared training qualification. This is evidence against crediting a more elaborate formula when its coefficients do not change actual decisions.

IC NB26 explicitly changes ranking and risk sizing in a four-arm factorial. Available-history growth ranking is negative in every inspected window; changing the risk estimator is a separate, smaller and period-dependent effect. IC NB27 then freezes the diagnostic B11 requested membership and gets deeply negative returns under equal, inverse-volatility and inverse-variance sizing. That diagnoses a bad selected schedule; it does not reject those allocators on C00.

Sources: [corrected IC NB30](../hyperliquid-ic/30-research-rolling-typical-profitability.ipynb), [IC NB24](../hyperliquid-ic/24-research-monthly-calibration.ipynb), [IC NB26](../hyperliquid-ic/26-research-rolling-ranking-access.ipynb), [IC NB27](../hyperliquid-ic/27-research-rolling-sizing.ipynb).

### Some apparent ranking breakthroughs were universe or reporting effects

VOV NB66 already separates a Bayesian gate from a simpler weight signal. Later NB83 shows the full gate and no gate are identical in the filtered opportunity universe; this weakens earlier attribution of success to the Bayesian gate. NB86 shows broad no-gate equal weighting and a matched random selector beating the studied ranked selectors. These are results for that universe, not permission to select randomly in the current strategy.

The age-ramp and correlation branches also require caution: later matched-universe and holdout comparisons weaken sweeping claims that age-ramp sizing is superior. Some fold-level “best age” or “best correlation” summaries choose winners using holdout outcomes, and near-zero realised downside creates enormous, unhelpful ratio values. Strong historical headlines are not interchangeable with genuine later-data verification.

Waterfall NB38–51 already tests whether better all-universe IC translates into a concentrated portfolio. A rank blend has IC **0.315**, above the original composite **0.242**, yet its decision-aligned top-six forward return is **−0.07%**, versus **+0.70%** for the composite. The actual portfolio rank blend also underperforms. Beta, smoothness, residual, maturity and inflow follow-ups do not establish an adopted improvement. Top-of-book diagnostics and substitution checks are therefore existing work, not new ideas.

Sources: [Waterfall NB47](../hyperliquid-waterfall-rc/47-research-stage0-decision-aligned-screening.ipynb), [VOV NB83](../vault-of-vaults/83-hyperliquid-gate-value-ablation.ipynb), [VOV NB86](../vault-of-vaults/86-hyperliquid-ranked-selection-ablation.ipynb).

### The lower-vol and model branches already tested more advanced forecasting

The vault-model chain goes beyond hand-picked formulas: NB04 fits low-dimensional monotone rank blends with shrinkage; NB05 applies walk-forward LightGBM ranking; NB06 adds evidence/confidence inputs and development-selected configurations. Young vaults have lower measured model IC than mature vaults in that study, but not worse average outcomes. Maturity is therefore not automatically a positive-return premium.

Vault-model NB07 rejects a young-vault satellite during development when the zero-sleeve anchor wins. NB09 fixes the core-slot confound and tests an additive full-six core with score-ranked versus seeded-random sleeves, two versus twelve extras, screening and budget doses. Those sleeve arms do not establish an improvement. This construction question was already asked before current NB19.

Lower-vol NB13–19 separately investigates the implicit age/history barrier, evidence-based selection, fixed-incumbent evidence sizing and core–satellite combinations. The screened young-compatible selection lead fails in the executable portfolio. With fixed incumbent selection, equal/evidence/blend sizing yields **25.77%/33.36%/36.42% CAGR**, versus the **37.90%** source control; none is a robust replacement.

Lower-vol NB28–40 again finds strong forward risk ordering without a profitable new risk selector. A quality180 hard floor can eliminate a profitable incumbent, and the cash-sleeve tests fail. That does not reject the feature as a ranker: a hard cutoff, a ranking leg and a weighting ingredient are different interventions.

Sources: [vault-model NB09](../hyperliquid-vault-model/09-research-breadth-sleeve-dose-response.ipynb), [lower-vol NB17](../hyperliquid-lower-vol/17-backtest-evidence-sizing.ipynb), [lower-vol NB40](../hyperliquid-lower-vol/40-backtest-lead-forensics-cash-sleeve.ipynb).

## 2. Exposure: what is already learnt

### The cash problem has several distinct causes

Earlier VOV NB08/20/24/28/29 and NB129–160 address allocation mechanics, minimum tickets, pool caps, survivor renormalisation, recycling, HLP residual sleeves and waterfall. Waterfall NB33–35 tests deposit-aware redistribution and additional slots. Current NB15/16 September diagnostics show six selected vaults reaching a combined capacity ceiling. Reweighting those same six cannot exceed their total feasible capacity.

This is different from NB21's model-driven all-cash choices: a negative forecast can deliberately decline capacity which is available. Separately, redemption timing, minimum trade bands, retained holdings and permission constraints can keep actual capital different from requested targets.

### More cash use has repeatedly failed to improve the economic trade-off

VOV NB63 softmax increases average capital utilisation from **87.23% to 95.57%** in one comparison and CAGR from **112.45% to 201.39%**, but reduces Sharpe **2.87 to 1.41** and worsens drawdown **−6% to −27%**. NB64 threshold-linear weights likewise raise utilisation but worsen Sharpe/drawdown. These old runs illustrate the trade-off; their CAGR levels are not comparable with C00.

Waterfall NB33 deposit-aware redistribution improves deployment but worsens CAGR/Sharpe/drawdown in its own matched replay. Current NB17 overflow and joint allocators achieve very low September cash in some arms, but lose profit in fresh 2026; the long-period overflow lead is heavily contributor-dependent. Current NB18 risk-limited and calibrated sleeves do not improve profit, Sharpe and drawdown across both researched periods. A gate that mostly refuses additions can avoid losses without identifying profitable marginal purchases.

Current NB19 preserves the exact C00 core and tests extra absolute tickets weighted by equal, performance strength, risk and combined strength/risk, including 8/12 slots. The best inspected variant RS01 adds only **USD 255** to fresh-2026 profit. Role bookkeeping attributes **−USD 189** to extra holdings and **+USD 444** to core/other feedback. That small account lead does not demonstrate profitable extras in isolation.

Sources: [NB17 findings](17-capital-allocation-findings.md), [NB18 findings](18-conditional-cash-allocation-findings.md), [NB19 findings](19-protected-core-score-risk-allocation-findings.md).

### The absolute “beats cash” threshold is still unproven

NB08's absolute floor is active in **27/30 method-months**, yet rejects **zero proposed entries**. It therefore supplies no treatment evidence for improved admission. NB09's amended return forecast has worse MAE than a zero-return baseline by **17.9%/25.3%** at 7/30 days. MAE alone is not a trading verdict, but it warns against assuming useful absolute return levels from modest rank IC.

NB21 gives a sharper diagnosis on supported 30-day C00 observations: forecast **−1.23%**, realised **+1.81%**; other feasible candidates are forecast **−2.38%**, realised **−3.11%**. Ordering these two cohorts correctly does not establish level calibration. C01 retains roughly 80% mean cash and earns **11.28% CAGR**, far below C00's **58.59%**, in fresh 2026. This is a measured model/portfolio package failure, not proof every low-scored vault loses money.

The broadly invested H07 reaches approximately 99.87% investment in September yet loses money over the year. Its major losses occur earlier, and it changes horizon, penalties, budget and turnover together. It must not be described as a clean test of September investment or of position count alone.

Sources: [NB21 findings](21-marginal-profit-findings.md), [NB21 implementation review](21-marginal-profit-implementation-review.md).

Lower-vol NB04 also tests portfolio volatility targets while holding ranking unchanged. Lower exposure reduces some path-risk measures but gives up substantial CAGR. NB05/06 shows tighter pool limits and broader baskets can redirect capital into worse opportunities rather than safely removing risk. Lower-vol NB42 finds that the source as-of-fill model already avoids the investigated opening-to-closing crash intervals; a tighter return gate or daily cadence does not improve its economics. A generic circuit breaker is therefore not wholly untested.

### We have already used controls to separate exposure from asset discrimination

IC NB28 compares targeted cash/no-refill and drawdown haircuts with uniform scaling that matches aggregate investment. Targeted treatments underperform the uniform controls in the hyper-ai window but outperform them in the full window: no stable result across periods. IC NB32 tests current-source volatility haircuts against a uniform-exposure control; most observed risk reduction comes from retaining cash, with return sacrificed. This separation is already an executed design.

Sources: [IC NB28](../hyperliquid-ic/28-research-rolling-exposure.ipynb), [IC NB32](../hyperliquid-ic/32-research-hyper-ai-risk-overlay.ipynb).

## 3. Sizing: what is already learnt

### We already have extensive controlled allocator evidence

Original NB10 freezes baskets and compares equal, inverse volatility, inverse variance, risk regularisation, risk windows, breadth and constraints. Expanded NB10 additionally compares standalone metrics, arithmetic/geometric/minimum scores, separate ranking/sizing scores, linear/squared/percentile/softmax maps, covariance risk budgets and missing-component rules. The **36-arm smoke** ran; its **334-policy registry** and generalisation across all 139 composite recipes did not.

NB11 evaluates 40 policies on frozen focal-four/v11 baskets, including 45/90/180-day windows, powers 1/1.5/2, shrinkage, bounded risk, multi-window risk and sparse-observation estimators. NB12 adds local sensitivity and constraint-aware allocation; NB13 replays a long-period shortlist. NB14 isolates allocation and estimator packages in the engine; NB15/16 compare proportional versus waterfall variants. NB17–19 explore capacity expansion, joint allocation and protected-core tickets. We should not describe a new equal/volatility/variance grid as unexplored.

The older VOV NB150 supplies a matched allocator frontier after its universe-cache correction. Signal-proportional no-recycle, equal no-recycle, equal recycle, capacity-aware equal and waterfall all use the same survivor-first architecture. Waterfall has the highest cumulative return and deployment (**120.45%, 98.52% accepted**), while no-recycle has higher Sharpe (**3.73** versus waterfall **3.47**). “Signal” is the age prior here. Recycling and waterfall are proven historical deployment mechanisms in that experiment; neither dominates every objective.

Correlation diversification also has existing positive as well as negative evidence. VOV NB94’s saved grid has shrinkage Calmar **38.58**, above equal **24.35** and age ramp **13.04**, contrary to its old prose. This is a pooled lead with validation limitations, not a basis for claiming correlation has been exhaustively rejected.

Sources: [VOV NB150](../vault-of-vaults/150-hyperliquid-equal-weight-recycle-allocator-ablation.ipynb), [VOV NB94](../vault-of-vaults/94-hyperliquid-shrinkage-correlations.ipynb).

### Caps can reverse the apparent result

Original NB10's uncapped regularised inverse variance gives lower mean 30-day return than equal weights, while reducing variance. With the same baskets and same accepted budget projected through source concentration/TVL constraints, the focal-four comparison reverses: **2.512% versus 1.716%** mean 30-day return, a **+0.796 pp** weighting lift. These are independent fixed-unit snapshots, not executable strategy CAGR.

NB11 invests identical total capital within each selector. Its weighting differences cannot be explained by greater cash usage. For the focal-four controls, regularised 90-day variance gives 2.512% mean 30-day return and −4.191% mean window drawdown, versus equal 1.716%/−6.193%. No new weighting/window alternative establishes universal improvement; quarter/tail effects and sparse-mark assumptions remain important.

Sources: [NB10 original findings](10-portfolio-snapshot-findings.md), [expanded NB10](10-expanded-score-allocation-smoke-findings.md), [NB11 findings](11-weighting-sizing-findings.md).

### Ranking and weighting should not be assumed to use the same score

Expanded NB10 supplies a direct counterexample. Adding risk ingredients to sizing has **+0.145 pp** mean 30-day return versus its neutral-offset control on the same resolved origins. Using a risk score for selection instead has **−1.112 pp** versus its matched focal equal-sizing comparison. K changes the tested ranking recipe by −0.331 pp and the matched weighting recipe by −0.014 pp. These are specific recipe contrasts, with coefficients changing in the K addition; they do not reject all possible K combinations.

Earlier Waterfall NB24/25 shows selection-versus-sizing interactions: low-volatility selection and inverse-volatility weighting are different treatments, and a gate that helps with inverse-volatility sizing can hurt with equal weights. Current NB21 magnitude forecasts offer another failure mode: a conditional winner-size model can magnify a wrong high-upside prediction and concentrate losses, even when another forecast component has some useful ordering.

### C00 is a strong historical package, not an isolated proof about inverse variance

NB20 compares identical-accounting C00 and local v11 rules:

| Period | C00 CAGR | v11 CAGR | C00 Sharpe | v11 Sharpe | C00 max DD | v11 max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 January–4 October 2026 | 58.59% | 49.15% | 2.474 | 2.214 | −6.36% | −6.41% |
| 1 March 2023–7 October 2026 | 33.13% | 18.55% | 1.651 | 1.374 | −9.94% | −7.92% |

C00 changes the ranking formula, risk estimator/support/fallback and waterfall allocation together. It is not simply v11 with another variance lookback. The four-input score is 0.48 × CAGR360 + 0.32 × Sortino45 + 0.10 × CAGR180 + 0.10 × Sortino30. The allocation fills feasible capacity from lowest regularised risk upwards within the selected six, rather than merely scaling a score proportionally. Long-period drawdown is worse despite better profit/Sharpe.

NB19’s protection/hold-versus-resize comparison and NB21’s small wider sell-band gain indicate that retention and executed trade thresholds can matter as much as another algebraic weighting formula. They do not establish a major new improvement or an optimal six-position limit.

Source: [NB20 comparison](20-c00-vs-v11-findings.md).

## 4. Corrections that matter for interpreting the archive

- **Saved prose can be stale.** VOV NB95/100/114/123 and Waterfall NB71/76/79 contain claims inconsistent with named saved comparison tables. Do not promote their prose-selected winner without reconciling the execution generation.
- **“Time in market” is not invested equity.** Waterfall NB89 displays 49% time-in-market alongside 97.84% average capital utilisation; NB92 displays 49% alongside 95.17%. Nonzero daily returns on a two-day cadence can explain the former. The old “half the capital is cash” explanation is contradicted by the actual utilisation table.
- **Notebook titles can misdescribe implementation.** Early VOV NB23-1_slash_n uses inverse rolling-return signal weighting in source, not clean equal weighting.
- **Sparse-data calculation is not certainty.** Forward fill after inception makes elapsed calendar metrics possible. It creates no new independent NAV information or proof of intervening executable prices. Actual updates, age, endpoint support and unresolved outcomes must stay distinct. Pre-inception data must not be backfilled, and unknown future outcomes are not zero returns.
- **Missing scores are not automatic loss forecasts.** Current NB17’s long overflow contrast favours allowing unscored vaults over a scored-only veto; expanded NB10 shows neutral/available-component variants can materially alter cash and funding. Missing=True eligibility and actual financed weight must both be audited.
- **Daily-panel timing was audited, with a later decisive correction.** Vault-model NB02 checks the disputed panel value directly: `close_wide[T]` matches end-of-day T in 99.7% of cells. Reading it at midnight T is forward-looking; correctly lagging it removes the apparent panel-composite gain. This later measurement supersedes earlier blanket claims that the panel lead was incorrectly disqualified. Archive `written_at` still does not become a certified live receipt clock.
- **Fees and accounting change the verdict.** Waterfall late-chain fee corrections and current NB17–20 partial-trim/reopening/funding repairs change headline returns. Old “wins” and later corrected controls cannot be mixed.
- **Several robustness claims exceed implementation.** Some earlier “walk-forward” exercises replay fixed configurations over overlapping slices; tolerance changes do not necessarily impose actual transaction costs. NB21 review still flags a stale MARGIN forecast-SE generation and omitted carried-target sensitivity; those are qualifications, not completed checks.

## 5. What is genuinely left unanswered

These are gaps in the evidence, not a request to start another search:

1. **Incremental ranking value on the exact C00 decision population.** Existing all-universe IC, score searches and recipe ablations do not fully identify whether a frozen forecast adds useful ordering at C00’s actual entry/retention boundary after risk, capacity and missingness are held fixed. IC26/27 and expanded NB10 already supply the relevant control ideas; repeat only a genuinely different, clearly isolated contrast.
2. **Absolute return levels for executable marginal opportunities.** Admission floors, calibrated sleeves and NB21 have been tried. The unresolved task is reliable calibration for the candidates that actually survive core protection, permissions, dollar capacity and minimum tickets, including retained positions versus redeployment. A favourable peer rank is insufficient.
3. **Benefit of a forecast at fixed exposure and construction.** A forecast package can fail because of bad level calibration, unsupported magnitude tails, turnover or risk-budget assumptions. We have not demonstrated that NB21’s failure isolates one of these. Existing uniform-exposure and matched-basket controls should be reused rather than invented again.
4. **C00 component attribution under the newest common accounting.** Earlier estimator/allocator studies and NB20 establish package comparisons. They do not completely isolate the exact C00 score, regularised support/fallback and waterfall interactions in a full engine factorial with current corrected accounting.
5. **Genuinely later observations and economic execution support.** Lower-vol NB43 already finds substantial live/backtest drawdown and current-rule-period divergence despite a close aggregate launch-period return. It is an observational comparison with universe/selection parity unresolved, not a controlled validation of C00. More searches on these same overlapping dates cannot establish independent generalisation. Unresolved/ceased vault outcomes, historical opportunity/permission completeness, sparse quote availability and actual fee conventions still limit economic certainty.

The audit therefore changes the next-step framing: ranking, exposure and sizing are already mapped extensively. The strongest remaining gap is translating modest relative information into calibrated, feasible marginal decisions, while identifying which part of C00 actually earns its historical advantage. Another unrestricted score/weight grid would repeat much of the existing work.
