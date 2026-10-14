# Experiment 19 — Claude contribution and review

This accompanies [the NB19 plan](19-protected-core-score-risk-allocation-plan.md). Requested collaborator: Claude CLI, model `claude-fable-5-1`. This document records planning, not notebook execution or strategy results.

## Access and evidence

The contribution ran with high effort, safe mode, no session persistence, read-only `Read`, `Glob` and `Grep` tools, non-interactive permission handling and empty strict MCP configuration. The working repository and the trade-executor/strategies repositories were available for inspection. Claude could inspect research folders and saved ledgers; it could not edit or run backtests through these tools.

The first successful call took approximately nine minutes and 63 turns. Its result confirms `claude-fable-5-1` as the only model, no fallback, no permission denials and no web searches. A preliminary invocation failed locally because the empty MCP configuration lacked `mcpServers`; it was corrected before the successful model call.

Claude reports inspecting: the complete folder summary; NB07, expanded NB10 and NB17–18 findings/plans; September capacity analysis; `capital_allocation.py`, `capital_allocation_methods.py`, `conditional_cash_allocation.py`, `conditional_cash_forecasts.py`, `waterfall_comparison.py`, `allocation_comparison.py`, `profitable_allocation.py`, `score_matrix.py`, risk/sizing helpers; the full v11 decision path and framework AlphaModel; cross-folder inventory, older cash allocation ideas and lower-vol reviews; and NB17/NB18 saved ledgers. The final review uses streaming tool traces so its actual file reads can be recorded separately.

Raw prompts/responses are retained under the ignored `_artifacts-restored-2026-10-07/19-plan-review/` directory. The durable plan and this review remain outside generated artefacts.

## Main independent challenges

Claude challenged our interpretation that weak extra vaults alone explain widening losses. Earlier overflow gained in 2024/2025 and lost in 2026, while shared-vault changes and resizing timing mattered. It suggested that turnover control may be higher impact than another score transform. It also found that NB17/NB18's admission-aware core is not exact C00, and that role isolation is needed both for hysteresis and new-entry permission checks.

It proposed absolute risk/score tickets with a positive score floor, holding units between mandatory exits, separate risk-only and score-only controls, and 8/10/12 total-position comparisons. It opposed normalising every score mixture to fill cash, retaining NB18's volatility-anchor brake, using zero for missing-score capital, and adding another forecast gate. It suggested reporting active opportunity dates, deployed dollar-days, repurchases, contributor dependence and account-size capacity.

## Decisions on contributions

| Suggestion or claim | Decision | Reason and resulting plan |
| --- | --- | --- |
| Use actual source/framework C00 rather than M01 targets | Accepted | Zero-slot adapter parity, narrow source hooks and per-decision conditional core assertions. |
| Split held status for both core hysteresis and entry/deposit logic | Accepted | Actual holdings still determine net trades, cost basis, pins and available proceeds. |
| Hold extra units versus resize them every two days | Accepted as matched experiment | Primary combined method holds units; a matched resizing arm measures the complete timing/exposure/cost effect. Entry dollar value is not itself a held-unit target. |
| Avoid score-zero veto of unscored histories | Accepted | Positive sizing floor, explicit missing flag and predetermined floor sensitivity. |
| Absolute tickets rather than automatically filled normalised weights | Accepted, with controls | Risk-only, score-only and combined absolute tickets; normalised risk/combined controls retain a fair mechanism comparison. |
| Drop the current-risk anchor brake | Accepted as a declared package difference | Entry risk sizing and gross caps remain; same-state anchor diagnostics quantify omitted restrictions. No claim that removing the brake is proven profitable. |
| The brake caused procyclical losses | Qualified | Direction of the trigger is plausible; observed arm differences do not isolate its causal contribution. |
| Capacity opportunities occur on about 30/139 exact-core dates | Corrected | Claude used the M01 ledger. Recompute the actual C00 opportunity calendar before treating the number as C00 evidence. |
| Most R00 loss was timing rather than fees | Qualified | Extra booked fees are smaller than the profit gap; this is not a causal PnL decomposition. |
| Lagged median core risk/ticket anchors v*/d* with 30-decision support | Replaced | They add anchors/support assumptions and may again be inactive/cap-bound. Use bounded peer-relative risk and an explicit per-vault ticket ceiling. |
| Require fresh rank at most 6+K and exit above 6+K+2 | Rejected for this matrix | It would change extra admission/retention with breadth and might remove useful deep/unscored refill names. Fixed source eligibility and mandatory exits are shared; measure incumbent slot locking. |
| Raise single extra cap to 10%; remove total cap | Rejected | Volatility estimates do not bound vault failure losses. Retain explicit provisional gross caps and a smaller-cap sensitivity. |
| Treat valuation inconsistency as harmless because code is shared | Rejected | The cached quote is state dependent; different holdings can expose different distortions. Keep a bounded shared cost/valuation audit and common corrected identity if required. |
| Explore account-size capacity and opportunity-level economics | Accepted as diagnostics | Avoid another capital-size engine grid; report same-state capacity and net role PnL per gross dollar-day. |

## Final review and incorporated corrections

The final read-only review completed successfully in approximately ten minutes and 59 turns. Returned model usage again confirms only `claude-fable-5-1`, no fallback, no permission denials and no web searches. The stream records actual `Read`/`Grep` inspection of the draft, prior contribution, strategy and allocation modules, framework AlphaModel, backtest pricing/valuation, generic pricing and runner code, previous findings/review and saved artefact paths.

Claude's verdict was **conditional**: implementable after concrete specification corrections. The delivered plan incorporates those corrections; the edits were checked against the review rather than submitted for a third independent pass.

| Final feedback | Correction in delivered plan |
| --- | --- |
| Starting tickets at the hard cap makes hold trim winners immediately | Entry scale is half the 5% hard single cap: D=2.5% of safe equity before multipliers. Hard drift trims still apply and are reported; eta=0.5 is explicitly provisional. All tickets/caps use gross NAV units. |
| A second peer median adds another estimator | Risk factor uses the existing leave-one-out prior: min(1,sqrt(prior/predicted)). Prior-only names get risk factor one and this is disclosed. |
| The held set has more source uses than the initial two-predicate discussion | Audit whitelist, entry score, hysteresis, deposit-check skip, blocked top-ups, extension and diagnostics. Core held status is distinct from actual holdings used for valuation/funding/netting. |
| Unsignalled holdings are automatically sold by the source trade generator | Every retained extra receives an explicit old-value target signal. A fixture verifies zero trade quantity under unchanged held units. Guard/whitelist exits or pins are explicit signals. |
| The evaluator can activate the original source extension | Keep max_assets and max_capacity at six and evaluator n=6; external policy owns total 8/10/12 limits. Assert source parameters every cycle. |
| Normalised controls can become identical at caps | Replace the economic normalised-risk arm with a flat held-ticket breadth control. Keep one normalised-combined arm and risk-only normalisation as a same-state diagnostic. Report unsaturated dates and dollars. |
| Source resizing has unequal buy/sell bands | Report upward/downward requested and executed adjustments and suppressed trims; preserve the original bands. |
| Hold can lock slots in mediocre incumbents | Add paired, terminal-supported 7/30-day opportunity diagnostics; propose finite-versus-finite full-slot score contests as a separately registered future replacement rule. No new rank/time exit gate is added silently. |
| Stale reopened-pair valuation can distort the hold-versus-resize Sharpe comparison | Bound the shared audit to reopen tax gaps, time to refresh, actual quotes and final-window exposure. Use a local common correction/new identity if required; do not infer that shared code cancels state-dependent distortion. |
| Residual opportunities need exact C00 evidence | Directly checked the final C00 target ledger: 37/139 positive target residual dates, including May. Several are small. Plan distinguishes target residuals from executable extra cash and recalculates the full opportunity calendar. |

The economic matrix has nine methods in two periods (18 accounts), two zero-slot adapter replays (20), and two fixed sensitivities in two periods (24). If a changed common valuation identity requires additional historical C00 replication, allow two further audit account jobs (26). This is an execution count, not a larger strategy search.

No notebook was implemented or backtest rerun during planning. The ready status means the written design can be implemented subject to its explicit parity, funding, cost and activation checks; it does not establish that a candidate beats C00.
