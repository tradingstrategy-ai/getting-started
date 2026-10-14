# Experiment 14 — Claude contribution and review

Date: 11 October 2026. Accompanies the [experiment plan](14-profitable-allocation-plan.md).

## Review method

Claude CLI was invoked with `--model claude-fable-5-1 --effort high`, tools disabled, safe mode and no session persistence. Both responses completed successfully and each reports `claude-fable-5-1` as its only model, with no fallback or permission denials. Claude received the draft plan and NB12/NB13 findings; it did not independently inspect the repositories. The second review received the revised plan and the empirical-window, peer-prior and forecast helper source.

Raw prompts, responses, reviewed drafts and their SHA-256 hashes are saved in the ignored `_artifacts-restored-2026-10-07/14-plan-review/` directory. This document records the reasoning that should remain available with the plan. No notebook or backtest was executed during planning.

## Contributions and dispositions

| Claude contribution | Decision and reason |
| --- | --- |
| The original six-arm factorial mostly explains existing allocation differences; add a direct profit hypothesis | Accepted. Add G: regularised downside-based sizing, testing whether treating upside jumps as risk reduces subsequent profit. This remains an untested hypothesis. |
| Drop the gap-estimator/source-allocator arm; reuse existing gap results | Accepted. Five active arms A/B/C/D/G, with F/C07 as optional matching saved context. |
| Distinguish fresh replays from cached reference results | Accepted with qualification. Ten required arm/period results; six new B/C/G replays if four A/D results and their ledgers match exactly. Changed data, code or timing require control replays. |
| Focus on net profit and show the drawdown cost | Accepted. Long-history profit ordering, short-period profit leader and calendar attribution; no arbitrary combined CAGR/Sharpe objective or new drawdown cutoff. |
| Full-history cash overstates today's deployment opportunity | Accepted qualitatively. Show annual cash and distinguish early universe scarcity from recent allocation behaviour. Average cash does not mathematically bound the profit effect. |
| Downside sizing should use source log returns and only actual-return days | Corrected after source inspection. Source uses calendar simple returns. G shares C's path, support and elapsed-day denominator, retaining actual-update counting for regularisation. |
| Size zero-downside vaults directly to their caps | Rejected. Use regularisation and explicit peer fallback to avoid treating a short loss-free history as risk-free. No new direct-to-cap rule. |
| Downside semivariance is never larger than variance | Rejected. An uncentred downside second moment can exceed centred variance. The implementation must not rely on this inequality. |
| Late receipts prove lookahead; use yesterday's NAV as a sensitivity fill | Corrected. Trace actual input and fill consumption first. Stale past NAV is not automatically executable; use an explicitly causal execution convention if correction is necessary. |
| Equal redemption rates cannot change relative rankings | Rejected. Different turnover creates different modelled costs; report those by arm. |
| Attribute profits exactly as exposure difference times invested return plus placement | Rejected as stated. Compounding, costs and changing holdings prevent that simple exact attribution; use observed exposure and vault/quarter profit contributions descriptively. |
| Give earlier historical years more objective weight because C03 was selected on 2026 | Rejected. Earlier periods were searched too. Present both periods and annual contributions without inventing an independent holdout or new objective weights. |
| Add an idle-cash yield sleeve | Deferred. Requires an executable instrument, capacity/liquidity and historical availability evidence. It is a separate strategy change. |
| Avoid trimming winners unless they breach the cap | Deferred. Potential profit/turnover idea, but changes trade generation and portfolio drift. Keep NB14 focused on allocation. |

## Revised economic question

Can source-risk redistribution, regularisation under the original allocator, or downside-based regularised sizing earn more dollars than C03? If so, does the gain repeat across years, how much drawdown does it cost, and does it survive correction of any confirmed execution-timing error?

The new downside arm is compared with C to isolate the risk-functional change and with A to measure practical improvement. The A/B/C/D block separates the original estimator and allocator changes. This retains causal interpretability without requiring a second research framework.

## Final focused review

Verdict: **ready to execute, with three small clarifications**. Claude checked the formulas, matched controls and ten-result/six-fresh-run count. The following were incorporated:

- Separate `zero_downside_nonflat` from genuinely flat observations; retain partial/full support separately.
- Disclose the loss-conditioned positive downside peer pool and the unscaled fallback to a total-variance peer prior. Report actual fallback use.
- Annotate the fresh-2026 endpoint (4 October) versus carried-2026 endpoint (7 October), both inherited from NB13.
- State the 25% minimum prior weight under a positive prior and at most 90 daily actual updates. This does not hold for empirical-only fallback when the prior is unavailable.
- Perform the reference timing trace before fresh replays and check new trades as they are generated.
- Remove the synthetic largest-update-deletion diagnostic; use quarter/vault contribution outputs.
- Record G plus redistribution as a possible later single-arm extension, not an automatic addition.

Two review assertions were qualified: total variance is not universally twice the downside second moment, and the number of invalidated caches depends on the scope of the timing correction. The plan makes neither assumption. The final clarifications were checked locally; no third Claude review was requested.

The final scope is five active methods over two periods. The work remains a plan; no experiment results are claimed.
