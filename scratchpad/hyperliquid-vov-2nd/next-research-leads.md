# C00 research leads after PR #61

Prepared on 14 October 2026. These are proposed follow-ups; no new experiment results are reported.

[PR #61](https://github.com/tradingstrategy-ai/getting-started/pull/61) has no posted discussion comments, inline comments or reviews at the time of this review. Its concluding findings and “Likely future leads” discussion provide the closure record used here. The recommendations are cross-checked against the executed notebooks, [research summary](summary.md) and [ranking/exposure/sizing audit](ranking-exposure-sizing-audit.md).

## What remains promising

Keep exact C00 as the economic benchmark: the four-input score, regularised 90-day risk and capacity waterfall. Its latest matched comparison improves historical CAGR and Sharpe over v11 in both periods, with worse full-history drawdown. No large subsequent allocation improvement has been established.

For 1 January–4 October 2026, C00 returns 58.59% CAGR, 2.474 Sharpe and −6.36% maximum drawdown. Over 1 March 2023–7 October 2026, it returns 33.13%, 1.651 and −9.94%. Each account starts with USD 150,000; full history overlaps 2026 and is already researched.

The two positive follow-up candidates are modest:

| Candidate | Evidence | Meaning |
| --- | --- | --- |
| [NB21 F01](21-research-marginal-profit-allocation.ipynb): widen the sell band from 0.5% to 1% | Extra net profit of **USD 116 in 2026** and **USD 1,025 over full history**; 2026 drawdown slightly worse | Execution/retention lead; an isolated same-account comparison, with no return forecast added |
| [NB19 RS01](19-backtest-protected-core-score-risk-allocation.ipynb): resize absolute score × risk tickets around the protected C00 core | Extra net profit of **USD 255 in 2026** and **USD 6,069 over full history**; 2026 drawdown slightly worse | Small construction/management lead; not proof that the extra vaults themselves have positive expected returns |

Amounts above are rounded from the saved result tables. PR #61 described the first short-period gain as about USD 111; the saved account difference is USD 115.74, rounded here to USD 116.

RS01’s interval-start role attribution assigns about USD −189 to additional holdings and USD +444 to core/other feedback in fresh 2026. Its net improvement therefore cannot be credited to a profitable extra-position sleeve in isolation. The distinction matters when deciding what to change next.

## Prioritised leads

| Priority | Lead | What earlier work already covered | Useful next comparison | Evidence required to continue |
| --- | --- | --- | --- | --- |
| 1 | Combine the wider sell band with RS01 resizing | Each intervention has a small positive historical result separately; their interaction around exact C00 is not isolated | Four policies: C00, F01, RS01, RS01 with the same 1% sell-band change | Matched control parity, net profit/risk differences, trade and fee attribution, and a clearly identified interaction |
| 2 | Forecast the economic downside of actual managed entries | NB08 floors, NB21 adaptive forecasts and NB22 entry-band calibration already failed to establish a useful veto | Diagnose managed initial-entry outcomes and tail loss on actual executable proposals, with fresh-entry and incumbent decisions separate | Useful local discrimination and loss calibration, beyond pooled and calendar/identity controls; unfinished outcomes must not reverse the result |
| 3 | Attribute exact C00’s score/risk/waterfall interaction under current accounting | NB14/16 explored related packages; NB20 proves the final package comparison; NB22’s optional factorial was not run | A frozen two-by-two-by-two score × risk × allocator comparison under NB20/NB23 accounting | Identify which interaction creates the gain before changing its components; treat risk support/fallback as part of the estimator package |
| 4 | Study accepted portfolio risk and covariance within the same six-name core | Equal/volatility/variance grids, constrained risk budgets and correlation methods already have extensive tests | First examine actual remaining allocation freedom under C00’s caps; if meaningful, one covariance-aware sizing control at the same funded budget | Forecast/realised risk quality and post-cap risk contributions, with robust sparse-data support; an optimiser objective alone is insufficient |
| 5 | Allocate spare cash where the marginal opportunity beats cash | NB17 capacity/breadth, NB18 conditional sleeves, NB19 protected tickets and NB21 adaptive breadth already tested nearby designs | Reuse exact C00 core and compare a supported marginal sleeve with cash, only after the local opportunity model qualifies | Positive whole-account economics and separately reported extra-position profit, costs and core feedback; reduced cash is not a pass condition |
| 6 | Obtain later confirmation and stronger data/fee evidence | Current histories overlap, use retrospective inventory/guard and modelled costs, and contain sparse NAV updates | Freeze the shortlist and observe genuinely later decisions; verify permission chronology, actual-update support and fee behaviour | A later economic advantage that survives data/cost qualification, rather than another winner selected from 2026 |

The highest potential profit opportunity is learning when additional executable vaults are worth buying after core capacity is exhausted. The present forecasts have not solved it. The first proposed notebook instead combines the two surviving small leads because it is a bounded economic comparison with interpretable controls.

## Recommended next notebook

Working title: **NB24 — C00 execution band and additional-position management**. Implement this only as a separate experiment with frozen rules; this document contains the design, not executed accounts.

### Goal and hypothesis

Determine whether RS01’s management benefit and F01’s wider sell band complement each other and improve C00’s net account profit without an unacceptable risk trade-off.

The hypothesis is deliberately narrow. Separate positive historical differences do not imply that their combination is positive. The wider band may avoid unnecessary transactions, but it may also delay useful trims or trigger different mandatory cap actions.

### Initial comparison matrix

Use four policies over two periods: **eight matched accounts**. Existing controls may use exact validated caches if their full input and execution identities match; record cached versus fresh execution explicitly.

| ID | Core and extra-position rules | Source sell band | Role |
| --- | --- | ---: | --- |
| A | Exact C00, six-position core, no extras | 0.5% | Primary benchmark; reproduce NB20/NB23 |
| B | Same as A | 1% | Reproduce NB21 F01 |
| C | Exact NB19 RS01: protected C00 core with absolute score × risk tickets, continuously resized | 0.5% | Reproduce NB19 RS01 |
| D | Same as C, with the same source sell-band intervention as B | 1% | New interaction comparison |

Keep the existing buy threshold, dollar floor, mandatory cap handling, cleanup, score clips, rank hysteresis, missing behaviour, risk estimator, ticket coefficients and exposure/slot limits. Do not infer that the wider band exempts an additional position from a mandatory exposure limit. The intervention can affect core and additional routine sells wherever the source parameter applies; report both.

C/D use RS01’s existing additional-position specification, not a new normalised allocation: base tickets are 2.5% of conservative equity, multiplied by the score-strength and risk factors, subject to existing per-name, sleeve, capacity and slot limits. Use the exact existing helper definitions rather than reconstructing the approximations in this prose. Later wealth and holdings may change future core decisions; same-state core protection is distinct from historical account-path equality.

### Calendar and accounting

- Short account: `[2026-01-01, 2026-10-05)` naive UTC, through 4 October.
- Full-history account: `[2023-03-01, 2026-10-08)`, through 7 October; final archive day partial.
- Fresh USD 150,000 per account, with all preceding indicator history, including 2025 for short accounts.
- Use NB20/NB23’s common partial-sale correction, fresh-entry tax reset and final-net-proceeds funding for every policy.
- Keep the recorded 10% positive-profit charge and 0.1% capital allowance consistent across arms. Report their sensitivity separately if verified fee evidence requires a different economic model; do not mix accounting generations.

Reproduce A/B/C before interpreting D. Code in the merged publication copy was formatted; old byte-hash cache identities may therefore differ even where economic semantics match. Use the preserved measured sources/input generations for exact replication, or explicitly regenerate identities and reproduce the account results under the new source identity. Do not weaken the control comparisons to bypass a mismatch.

### What to report

Lead with a side-by-side key metrics table, equity and drawdown, separate absolute asset weights, quarterly returns, cash, paid charges, turnover and effective positions. Every chart and table has its own heading, short description and period. Default to 2026, with full history in a labelled section; keep images separate.

The primary contrasts are B−A, C−A, D−C and D−B. Report the interaction:

`interaction = profit(D) − profit(C) − profit(B) + profit(A)`.

This is a whole-policy factorial contrast. It includes compounding and holding feedback and is not a decomposition into independent fee savings and forecast alpha.

For each contrast, reconcile vault-level profit and executed trade changes. Report avoided routine sells, affected re-entry/trim decisions, mandatory cap closes, realised costs, open liquidation allowances and additional-role versus core/other profit. Include the strongest-update, leading-vault and quarter influence checks using existing curator and BTC/ETH observation-interval methods.

### Decision after the notebook

A candidate with higher net profit in both researched periods and no worse risk measures can enter the frozen shortlist. Higher profit with worse drawdown remains an explicit trade-off. One-period gains or only reduced cash do not establish a replacement. If the interaction is negligible or negative, retain C00 and the isolated small leads rather than expand the matrix after viewing results.

Even a favourable result is exploratory. Use later observations for confirmation. No statistical significance threshold or minimum-dollar gain is invented to turn these small historical leads into a promotion claim.

## What the larger leads require

### Managed downside forecasting

NB21 forecasts the supported C00 cohort’s 30-day net outcome at −1.23% versus realised +1.81%. NB22 improves seven-day average bias but leaves rank IC at −0.065 and sign accuracy near 49%. More mean calibration, more slots or a new optimiser is not yet an evidenced solution.

A useful new diagnostic should target the managed entry’s economic outcome:

`managed initial-unit return = (attributed net redemption receipts + remaining net marked value − initial entry cost) / initial entry cost`.

Follow NB22’s proportional initial-unit attribution through actual sales and later top-ups. Fully closed outcomes become trainable only when their close and necessary observations are available. Open, vanished and unresolved outcomes require separate reporting, censoring/support checks and scenarios; a current mark is not a completed outcome and unknown future returns are not zero.

Evaluate fresh-entry and incumbent hold/redeem decisions separately. Compare loss probability and severity on actual executable opportunities with supported pooled forecasts, whole-entry identity controls and calendar-block controls. Any held-period choice must be frozen from past information. Retain young/missing vaults through explicit support priors; neither missing metrics nor carried zero returns establish bad quality or low risk.

Advance to an account treatment only after evidence survives the local ranking/calibration and unresolved-outcome checks. NB22 already performed a failed entry-veto qualification; changing the horizon or threshold on that same 2026 result does not create an independent lead.

### Current-accounting component attribution

The proposed factorial has two scores (v11 versus C00 four-input), two risk packages (source versus regularised 90-day variance, including their support/fallback policies), and two allocators (source proportional versus risk-priority waterfall). That makes eight policies per period. Two corners are the existing NB20 controls; the six other cells per period require current-accounting measurements, even where older related results exist.

Its purpose is to locate fragile dependencies and profitable interactions. It does not itself create a better strategy. Use it before interpreting a change to the four-input formula or regularisation as an isolated causal improvement.

### Covariance and spare-capacity allocation

The covariance lead is conditional on useful degrees of freedom. If a basket’s capacities force virtually the same dollar targets, another sizing optimiser cannot resolve its cash ceiling. Existing studies already tried related covariance/risk-budget policies; a repeat needs exact C00 selection, the latest accounting and accepted-budget controls to answer a different question.

Use causal daily NAV after inception for calendar risk, but retain actual joint-observation support and quote age. Shared carried zeros must not be treated as independent evidence of diversification. A covariance method needs a declared positive-semidefinite estimate, shrinkage and unsupported-history fallback. Examine accepted, not only requested, risk contributions.

For residual cash, preserve the source core and assess the new positions’ managed net economic advantage over cash. Include whole-account effects because capital, realised costs and later core membership interact. The 96.9% September capacity-shortfall attribution diagnoses cash usage; it cannot certify that buying available lower-ranked vaults increases profit.

## Lower-priority work

A broad new score grid, the unexecuted 334-policy expansion, another simple equal/inverse-volatility/inverse-variance sweep, blanket rejection of unscored vaults and unqualified 7-day exposure forecasts are lower priority. Nearby methods already received substantial coverage. Max-history K remains a possible feature ablation, but its small incremental forecast evidence has not yet justified another portfolio formula search.

Use [PR #61’s method inventory](README.md), [NB11](11-research-weighting-sizing.ipynb), [NB17](17-backtest-capacity-aware-allocation.ipynb), [NB19](19-backtest-protected-core-score-risk-allocation.ipynb), [NB21](21-research-marginal-profit-allocation.ipynb) and [NB22](22-research-c00-entry-margin-calibration.ipynb) to distinguish these outstanding comparisons from already tested mechanisms.
