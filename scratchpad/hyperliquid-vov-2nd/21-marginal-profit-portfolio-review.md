# Experiment 21 — Claude planning contribution and review

Date: 13 October 2026. Planning review only; no NB21 notebook or backtest has been run.

## Review process

The user requested collaborative planning with Claude CLI, using Fable 5.1, to escape prior portfolio construction limits and evaluate when capital is unlikely to earn a profit.

The first call used Claude CLI 2.1.296, explicitly requested `claude-fable-5-1`, and completed successfully in 27 turns. The result's `modelUsage` contains only `claude-fable-5-1`; no fallback model was requested or reported. No permission denials occurred. Claude received read-only Read/Glob/Grep tools, no MCP servers, and access to the research folder, strategies and trade-executor repositories. It read the draft, earlier findings, source strategy, forecast/allocator code, framework normaliser and holding-duration calculation.

The initial prompt asked for a critical review, independent higher-impact alternatives, a smaller diverse smoke matrix, actual formula corrections and hidden-assumption checks. The revised plan was then submitted for a second focused review of validity and implementation ambiguities. The second call completed successfully in nine turns, again reporting only `claude-fable-5-1` in `modelUsage`, with no permission denials.

Raw prompts, stream logs and review responses are local ignored artefacts under `_artifacts-restored-2026-10-07/21-plan-review/`. Durable decisions and limitations are recorded here rather than committing generated logs.

## What Claude contributed

Claude challenged the original draft as too similar to NB18 and too broad in its forecast model ladder. It identified the main novel actions as allowing incumbent changes and comparing replacements against holding/cash. It recommended a fee/turnover audit, a capital-weighted holding-duration audit, a simpler downside model, and deferring weakly supported joint CVaR estimation.

It also proposed wider trade bands, loss-hazard gating, capacity-aware retention, a greedy replacement contest, and an optional market-regime policy. We merged the useful parts while retaining the user's requirement that the main challengers break away from prescribed inverse-variance weights.

## Contribution decisions

| Contribution | Decision | What changed or why qualified |
| --- | --- | --- |
| Four-day median is count-weighted and may describe small flapping positions | Accepted | Audit capital-weighted duration, PnL by spell and open/censored positions before locking a policy horizon |
| Use different horizons for entry and incumbent decisions | Qualified | Include short-step diagnostics, but every directly compared action path uses a common terminal horizon |
| Put fees and short-spell PnL before another model search | Accepted | Stage 0 accounting and trade-suppression audit; wider-band F01 control with corrected proceeds |
| Remove redundant turnover penalties | Accepted | Complete basis-aware path values include modelled fees once; uncertainty margin is distinct from transaction cost |
| Fresh break-even approximation | Corrected | Retain the exact 0.001*(1+r) capital charge; condition is 0.999*E[r] − 0.10*E[max(r,0)] − 0.001 > 0 |
| Smaller loss-focused model ladder | Accepted with limits | Support prior, conditional negative-return probability, then conditional gain/loss magnitudes; no advance claim that hazard is learnable |
| Subtract predicted hazard losses from an unconditional mean | Rejected as written | Use a coherent conditional mixture; subtracting them again would double-count expected loss |
| Strong risk IC implies useful tail prediction | Not assumed | Volatility ordering is not evidence of negative-return or tail-event predictability; test those targets directly |
| Mean predictions will necessarily be indistinguishable from a constant | Not adopted | Earlier evidence motivates strong baselines, but does not establish NB21's result before fitting |
| Keep C00 inverse-variance sizing inside new construction | Rejected for main challengers | Would preserve the user's challenged constraint; only exact controls and F01 retain inherited sizing |
| Defer high-dimensional joint CVaR | Accepted | Initial allocator uses a common explicit sum-of-expected-downside budget; CVaR remains a conditional extension |
| No-update observations must not create zero risk | Accepted with sparse-data safeguards | Keep causal forward-filled metrics; distinguish actual marks and carried values; pool unsupported risk and show interval sensitivity |
| Ban stale vaults or equate reporting cessation with loss | Not adopted | No new universal stale veto; liquidity/reporting and financial loss are separate outcomes |
| Inverse-variance weight similarity check | Accepted as a diagnostic | Compare target correlations and actual dollar differences; no arbitrary similarity cutoff discards informative results |
| Replace all-name equal-ticket breadth straw man | Accepted | Main structural comparison is prior-based marginal-profit construction; exact six-slot ablation isolates the cap |
| Greedy replacement contest | Accepted | Compare holding, cash and funded replacements on complete same-horizon path values, with projection and local-optimum checks |
| Deposit coverage can affect broader portfolios differently | Accepted | Verify the archive boundary and report pre/post coverage and actual assumed-open exposures |
| Capacity-aware retention and market-regime policy | Retained as optional | One-step retention is part of the contest; multi-step reservation and regime modelling require supporting episodes |

## Merged design

The revised plan has ten full-2026 arms: exact C00/v11, one fee/churn control, three progressively conditional signal models inside a common marginal-profit allocator, a calibrated-C00-score control inside that same allocator, and three matched ablations for the six-position ceiling, incumbent management and loss budget. The old return gate moves to a bounded sensitivity.

The main allocator has no prescribed inverse-risk weights. It evaluates feasible incremental net account value and may add, retain, trim or replace holdings. Cash competes directly. A common P-model downside estimate and explicit budget keep signal comparisons interpretable; budget-free and neighbouring-budget arms expose how much that new constraint matters.

The models retain young/missing-score vaults with explicit support and priors. The final budget uses the P model’s implied negative-return expectation consistently, without adding an unspecified own/peer blend. Carried NAV remains usable for metrics and engine reconciliation, while learning labels distinguish actual endpoint evidence from unresolved marks. No unsupported return is silently treated as a confirmed zero or loss.

## Final review and remaining limits

Claude’s second verdict was that the revised design addresses the user’s aim and is implementable. It identified remaining specification gaps rather than validating any economic result. The following amendments were made after that review; they have not been separately reviewed in a third CLI call.

| Final review point | Amendment or qualification |
| --- | --- |
| A mathematical expected-downside inequality is not a guarantee about estimated risk | State the pointwise identity and distinguish estimated d values; budget-free and half/double-budget comparisons remain essential |
| Linear objectives can fill caps or favour low-downside names | Disclose corner solutions and lack of an explicit diversification reward; attribute breadth to caps, ties, forecasts and budgets |
| Greedy search can favour larger tickets or arbitrary addresses | Compare dollar-priority and risk-priority feasible solutions, split economic ties equally in dollars, disclose approximation and refinement tolerances |
| Incumbent fees have a kink away from zero return | Specify full sign-preserving empirical mixture shapes and evaluate actual remaining-basis fees over outcomes |
| Fee model can favour holding underwater positions | Add separate zero-profit-fee and zero-capital-allowance sensitivities; no claim this is actual venue economics |
| Exact endpoint evidence is stricter than NB18 | Name it as a new learning view, retain carried-mark sensitivity and full engine reconciliation; no individual-vault exclusion |
| Fitting support/cold starts were vague | Specify horizon-scaled evidence conventions, pooled fallback, provisional/frozen budgets and cold-start cash |
| Exclude cold-start phase from paired comparison | Rejected for headline economics: every calendar day stays in account metrics; a secondary supported-date view is labelled |
| Budget refresh can cause forced uneconomic sales | Use soft drift breaches, prohibit new risk-increasing actions, report breach magnitude/duration; entry-only arm retains its meaning |
| Projection can repeatedly invent sell proceeds | Freeze executable sells, then one buy-only residual pass and final cap/cash checks |
| No same-allocator old-score comparator | Replace gate-on smoke arm with C01 calibrated-C00-score control; move gate restoration to the bounded extension |
| Report probability that an action is worse than no trade | Accepted for cash-relative marginal outcomes; a switch-versus-hold probability needs an identified joint return law and cannot come from arbitrary independent draws |
| Model/label delay can make a policy slow | Add fit/maturity lag reporting and 14-day return to the small performance feature set |

Claude proposed particular support thresholds (300 labels, six 30-day blocks, 50% cohort resolution). These were not adopted as universal truths. The merged plan uses explicitly declared horizon-scaled support conventions, requires their sensitivity to be shown, and avoids a reporting-frequency threshold that automatically removes sparse vaults. The final implementation manifest must record the actual support and fallback counts before interpreting forecasts.

The plan remains a research proposal, not evidence of a more profitable strategy. Statistical support, inherited fees, observation timing, retrospective universe choices, local optimisation and concentration in a few profit contributors remain material limitations. The first experiment has ten complete-2026 arms, at most three distinct long-period challengers plus two controls, and five registered local 2026 extensions. No notebook, model fit or backtest was executed in this planning task.
