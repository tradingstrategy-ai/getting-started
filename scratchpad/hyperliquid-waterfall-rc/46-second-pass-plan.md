# Second-pass allocation research plan

- **Status**: EXECUTED (NB47-NB51). Outcome: Stage 0 gated out NB49; NB48 and NB50 passed Stage 0 but both REJECTED in backtest; no Adopt/Provisional; NB36 remains champion. See "Execution outcomes" at the end. Original: design for execution (stages 0-2). Follows the first-pass programme
  (`40-allocation-strategy-research-plan.md`, NB41-NB45) which rejected all four hypotheses.
- **Baseline to beat**: `36-backtest-gated-inverse-vol-max6.ipynb` (re-run as an anchor in
  every notebook, since vault data drifts daily).

## Why a second pass, and what changed

The first-pass post-mortem found the failures were mostly **not** unsound ideas or bad
parameters, but three systematic defects in how we tested:

1. **Metric-decision misalignment.** We screened features by full-cross-section IC and
   quintile spreads (breadth statistics), but the strategy picks the **top 6** and re-ranks
   daily. A feature can raise IC while degrading the ordering at the very top. NB39's own
   detectability table already showed the rank blend was *worse* at putting winners in the
   top 6 - we flagged it as a watch-out instead of treating it as the decision metric.
2. **Timing artefacts.** NB45 showed a same-day feature panel beat the framework composite
   by ~+1.0 Sharpe, but a +1-day lag inverted it - a look-ahead/alignment artefact, not
   signal.
3. **Mechanism mismatches.** H3's evidence was *early detection* but we tested a static
   blend weight; H4's evidence supported excluding the extreme-inflow tail but we applied a
   monotone penalty that drifted into the dying-vault tail; and the original "BTC residual"
   idea (rank on residualised returns) was never actually tested - we tested |beta| instead.

The second pass fixes all three before spending backtests.

## Stage 0 - two cheap fixes before any backtest (NB47)

**0a. Decision-aligned screening (precision-at-6).** For each candidate feature, at each
14-day observation date: form the *tradable* candidate pool (TVL >= floor, feature
computable, momentum gate 14d > -8% applied - the pool `decide_trades` actually sees), take
the feature's **top 6**, and score the mean 30-day forward return of that top-6 vs (a) the
composite's top-6 and (b) the pool median. Also measure top-6 day-to-day set persistence
(turnover proxy). **Pre-registered gate: an idea earns a Stage-1 backtest only if its top-6
beats the composite's top-6 here.**

**0b. Framework indicator timing pin-down.** Determine exactly which timestamp the framework
`cagr_score`/`sharpe_score` value at cycle T reflects (as-of-T or as-of-T-1) by comparing the
framework indicator *series* against the research panel at T and T-1 for sample vaults. All
Stage-1 panels are then built at the **same** timing, closing the NB45 artefact class:
every second-pass result is live-parity by construction.

## Stage 1 - three pre-registered backtests, one mechanism each (NB48-NB50)

All vs the NB36 anchor (re-run in-notebook), everything else frozen (gate 14d/-8%,
inverse-vol 60d sizing, 6-vault basket, conc cap 0.50, pool cap 0.15, deposit-aware). New
features use framework-matched timing (Stage 0b). The composite base is the framework
`cagr_sharpe_weight` indicator (live-parity); each notebook re-verifies its baseline
reproduces the anchor to the dollar.

| NB | Idea (fixed mechanism) | Pre-registered spec | Diagnostic (not a candidate) |
|---|---|---|---|
| NB48 - maturity-conditional ranking (H3') | Composite-immature vaults (180-360d history: `sharpe_180` computable but `cagr_360` NaN) currently score 0 and are unrankable for their first year. Reserve **J junior slots** of the 6 for such vaults, ranked by `gain_to_pain_180`; juniors still pass gate/TVL/deposit and are inverse-vol sized | J = 1 | J = 2 |
| NB49 - residual composite (H2', the true BTC-residual idea) | Compute daily residuals `r - beta_90 * r_BTC` (Binance series via `fetch_binance_price`), rebuild a residual NAV index, compute the *same* `0.5*CAGR(360)+0.5*Sharpe(180)` on it, select by that. Gate stays on **raw** returns (exits must respond to real NAV drops) | full beta | beta shrunk 50% toward 0 (estimation-noise control) |
| NB50 - extreme-inflow exclusion (H4') | Exclude candidates in the **top decile of net_flow_30** among the gated pool - the asymmetric form the NB39 evidence actually supported. No penalty gradient, so no drift into the dying-vault tail. `net_flow_30 = (TVL_t/TVL_{t-30})/(price_t/price_{t-30}) - 1` | P90 cutoff | P80 |

Design notes: NB48 caps junior exposure at 1-2 slots because fresh entries are the
strategy's known tail risk (the IKAGI blow-up, NB34); NB49 changes *selection only* and for
the near-zero-beta majority residual ~= raw, so the change concentrates on directional
vaults; NB50 is declared a *hygiene* leg (NB44's endpoint: DD/turnover not worse at
non-inferior CAGR and Sharpe), not the Sharpe bar.

## Adjusted adoption rule (three tiers - honest about power)

Eleven months cannot push a real +0.2-0.3 Sharpe edge through a 95% bootstrap CI, so instead
of quietly lowering the bar we tier it:

- **Adopt**: dSharpe >= +0.15, dDD <= +2pp, edge survives largest-position removal (>=50%
  retained), edge positive in **both halves** of the sample, **and** the 20-day
  block-bootstrap CI on the daily-return difference excludes zero.
- **Provisional**: all of the above except the CI - carried to walk-forward as a frozen
  spec alongside the champion, not merged into it.
- **Reject**: anything else.

Re-used controls: NB41's permuted-rank placebo (null) stands; NB42's vol-matched control is
re-run for NB49 (a residual composite that merely de-risks should be caught by it); the
+1-day latency check runs on any Adopt/Provisional winner.

## Stage 2 - close-out (NB51)

Combine Adopts only, LOO-ablated. Provisionals are frozen as written specifications and
tracked walk-forward from the freeze date. Given first-pass experience, a set of
well-specified Provisionals plus the decision-aligned screening leaderboard is the most
likely useful output.

## Numbering

- `46-second-pass-plan.md` (this file)
- `47-research-stage0-decision-aligned-screening.ipynb`
- `48-backtest-maturity-conditional-ranking.ipynb`
- `49-backtest-residual-composite.ipynb`
- `50-backtest-extreme-inflow-exclusion.ipynb`
- `51-research-second-pass-closeout.ipynb`


## Execution outcomes (NB47-NB51)

- **NB47 Stage 0**: timing pinned to as-of-T (live-parity). Precision-at-6 leaderboard put
  the shipped composite near the top (0.70%), gated out the residual composite (0.33% ->
  NB49 not run), and re-confirmed the rank blend (-0.07%) and standalone smoothness (-0.55%)
  are poor top-6 selectors. NB48 (maturity) and NB50 (inflow exclusion) passed their
  mechanism-specific screens.
- **NB48 maturity**: REJECT. Pre-registered J=1 hurts (Sharpe -0.26, DD -11.3% - fresh-entry
  blow-up risk). Diagnostic J=2 has good point estimates (Sharpe +0.29) but fails the CI,
  single-position and both-halves gates; non-monotonic in J = noise signature.
- **NB49 residual composite**: NOT RUN (gated out by Stage 0). The true BTC-residual idea,
  tested properly, degrades top-6 selection - most vaults are near zero-beta so residual ~=
  raw, and the residual adds noise for the directional minority.
- **NB50 inflow exclusion**: REJECT. Fails its own hygiene endpoint (DD/Sharpe/CAGR all
  slightly worse). The +0.31pp Stage-0 top-6 gain did not survive sizing/gate/turnover.
- **NB51**: no Adopt/Provisional -> empty combination stage; NB36 unchanged.

**Meta-finding**: precision-at-6 is a strict improvement over IC (it correctly gated the
residual and would have predicted H1) but is necessary-not-sufficient - the two ideas it
passed still failed the backtest, only mildly. After two disciplined passes over ~35
features, no cross-sectional selection change beats the shipped composite; the evidence
points at a data/regime ceiling, not a missing feature. Recommendation: shift effort from
selection features to walk-forward validation and capacity/cost realism.
