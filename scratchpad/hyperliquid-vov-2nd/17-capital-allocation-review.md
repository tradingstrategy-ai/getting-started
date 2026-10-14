# Experiment 17 — Claude contribution and review

Date: 12 October 2026. Accompanies the [capital allocation plan](17-capital-allocation-plan.md). Planning only; no experiment has been run.

## Review method

Claude CLI was explicitly invoked with `--model claude-fable-5-1`, safe mode, tools disabled, no session persistence and JSON output. The first contribution used high effort and the focused second review used medium effort. Both returned successful execution with `claude-fable-5-1` as the only model, no fallback and no permission denials. The second review received the revised plan plus actual selection, normalisation and trade-generation source.

Claude reviewed supplied text and source excerpts. It did not independently explore the repositories or execute allocation code. Exact prompts, responses, draft snapshots and their SHA-256 hashes are retained in the ignored `_artifacts-restored-2026-10-07/17-plan-review/` directory.

## First contribution and dispositions

| Contribution | Disposition and reason |
| --- | --- |
| Fixed-basket sizing cannot overcome a summed capacity ceiling | Accepted, with the positive-score LP qualification. Explain saturation beforehand; evaluate sizing on budget-bound dates too. |
| Score waterfall and fixed-basket LP duplicate each other | Accepted for positive distinct scores before floors. Make L01 a common-state diagnostic/greedy helper rather than a full-account replay. Zero-score and tie policies are explicitly different. |
| M08 and joint optimisation originally used different sizing | Accepted. Greedy trial sizing now uses the same score objective; disclose floor/inner-heuristic differences and compare feasible objective gaps rather than claiming perfect search isolation. |
| Residual positions can churn and pay repeated redemption costs | Accepted. Add M09: incumbent maintenance with fee-aware residual trims. Keep score-first M05 as the matched control, so turnover restraint is measured. |
| Core-to-overflow transitions can produce round trips | Accepted as a required implementation invariant, not as proof that the existing source has this bug. Merge targets and emit one net trade per vault. |
| Weakest-core-score overflow screen is almost inactive | Accepted. Use scored-only M06 as an active information-policy comparison and retain the stricter relative screen as a cheap diagnostic. |
| Diagonal risk budgets ignore shared exposures and sparse-mark bias | Accepted. Document Q01's actual formula but defer it from the initial matrix. It is not an observed-risk guarantee. |
| One-decision confirmation could reduce brief core exits | Accepted as active M10 with a mathematical predicate and immediate gate exits. This is an explicit two-day cadence hypothesis, not a tuned lookback. |
| Known partial-trim fee convention can distort turnover comparisons | Accepted. Trace the actual helper and add shared corrected-fee sensitivities for the baseline and primary profit leaders, separate from legacy parity. |
| Lowest redemption charge can guide cash transfers | Accepted only inside the explicit M09 package. Merely reordering unchanged sells cannot reduce total fees; changing targets across every arm would confound the comparisons. |
| Incumbents within exit rank eight cannot be outgoing; extend the band | Rejected after source inspection. The best-entry-score override can remove an incumbent inside the rank band. Keep bounded M07 and count its actual opportunities. |
| Joint optimiser reduces universally to top score × capacity | Rejected. Only a simplified slack-budget regime has that shortcut. A six-slot numerical counterexample demonstrates failure when the budget binds. |
| Minimum TVL makes minimum entry tickets irrelevant | Rejected. Deposit permissions/amount limits can reduce usable capacity; the global 0.5% target floor is also distinct from incremental entry thresholds. |
| A relaxed-capacity replay bounds achievable profit | Rejected. More exposure can lose money and changes subsequent decisions. Show capacity bounds/diagnostics without claiming a realised-profit upper bound. |
| Require gains outside September and a largest contributor below 50% | Rejected as arbitrary economic vetoes. Explain localisation and dependence, show profit/risk trade-offs and avoid an invented contributor cutoff. |
| Add multiple capital-size engine replays | Deferred. Include only same-state capacity diagnostics at reference deployable budgets; they do not predict CAGR or represent new initial-account simulations. |
| Relax TVL participation limits or add a cash-yield instrument | Deferred as risk-policy/instrument changes. NB17 keeps existing caps and cash as the residual alternative. |

## Additional source-driven corrections

The local review identified `min_portfolio_weight_pct=0.005`, which acts on total accepted allocatable targets. Overflow can therefore cause an otherwise retained small core position to close by enlarging the denominator. The plan gives an explicit protection inequality and numerical example.

Core membership and actual held status are separated: overflow incumbents do not automatically receive core hysteresis, while permissions/available value still recognise that they are already held. Funding is core-first using final net proceeds; an overflow deficit cannot silently scale down core buys.

The legacy extension must retain its one-pass non-waterfall behaviour and residual-budget concentration semantics. NB16's global force-waterfall adapter cannot simply be reused for both models. The rebuilt extension uses whole-account concentration bounds and an explicit executable-capacity pass.

The active matrix has 14 methods over the entire fresh 2026 period and full history, with full warmup. L01 and the strict relative score floor are diagnostics; Q01 is deferred. SciPy is already available, so no new solver dependency is currently needed.

## Final focused review

Verdict: **the revised plan is mathematically sound, and the 28 primary replays plus two to six sensitivity runs are reasonable**. Claude checked the worked arithmetic and reconsidered the source-predicate/product-ranking assertions. Final corrections were incorporated locally; there was no third CLI call.

| Final concern / idea | Final disposition |
| --- | --- |
| Source score override weakens rank-band protection | Accepted with qualification. With strictly ordered scores, rank-seven/eight protection generally fails. Exact ties include positive clipped values, not only unavailable zeros. Source admission backfill can re-add an incumbent when entrants are blocked. |
| M07 needs an explicit exit/entry pairing | Accepted. Enumerate outgoing incumbent/new entrant pairs, maximise strictly positive recovered feasible capacity, then tie-break by turnover/address. Recompute after each reversal. |
| Source shares one held set across selection and admission | Accepted. Split core-incumbent membership from actual-held value/permission handling. A top-six overflow holder counts as a possible core entrant but remains held for admission. |
| Core denominator protection can restrict deployment | Accepted as a measured limitation. Count its frequency/dollars. Reject writing mixed per-role denominators into one global weight field: their weights would sum above one. A separate role-specific close rule would be a new policy, not a bookkeeping fix. |
| Fee-aware maintenance may defer rather than eliminate charges | Accepted. Show charges paid and modelled accrued open-position liability; verify gross/net reporting marks and avoid double deduction. |
| Small trims may be suppressed by sell bands | Accepted. Trim sequentially, honour the minimum executable partial trim/full-close path, net targets once and recompute proceeds. Core-first funding takes precedence over overflow maintenance. |
| Turnover tie-break requires another integer solve | Accepted. Explicit auxiliary absolute-value variables and lexicographic stages share a declared total decision runtime; record unfinished stages instead of claiming exactness. |
| Greedy/local objective improvement is not net profit | Retained explicitly. Shared proxy/feasible target domain permits useful objective-gap diagnostics, but floors, fees and executed queues can differ. |
| Add a common-state hysteresis audit | Accepted as a cheap diagnostic: in-band incumbents, ties, rejected entrants, actual replacements and short-lived returns. Registered historical arms remain fixed; preliminary counts do not select the long-period matrix. |

## Implementation scope and interpretation

Fourteen active methods cover admission-aware redistribution, proportional/risk/score priority, two/four residual slots, missing-score screening, capacity-aware retention, greedy/global proxy selection, maintained overflow, delayed rank exits, legacy extension and fixed breadth. Every active method runs the entire fresh 2026 replay with historical indicator warmup and the full-history account. Exact duplicate computations can be reused only after equality/identity checks.

L01 is a cheap fixed-basket mathematical diagnostic/helper. The diagonal-risk Q01, relaxed TVL participation, external cash instruments and expected-return calibration are deferred. The small numerical configuration is explicit and is not tuned for economic performance.

The goal is higher net dollars under comparable assumptions. Lower cash, a better score objective or a smaller diagonal risk proxy alone does not establish improvement. Both historical periods were already researched; the findings will require a frozen prospective follow-up before claiming predictive superiority. No strategy or framework files were edited and no backtest was run during this planning task.
