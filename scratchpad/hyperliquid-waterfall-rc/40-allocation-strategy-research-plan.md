# Allocation strategy research plan: five backtests from the NB38/NB39 predictive-feature findings

- **Status**: v3 — EXECUTED (NB41-NB45 built and run). Outcome: clean negative result, all four hypotheses rejected; see the "Execution outcomes" section below. Originally v2 — revised after external review (Codex CLI, GPT-5.6-sol, verdict "rework"; see the review-response section at the end). Initial research, looking for leads — not release work.
- **Baseline to beat**: `36-backtest-gated-inverse-vol-max6.ipynb` — CAGR 33.6%, Sharpe 1.85, Sortino 3.14, max drawdown −7.8%, Calmar 4.33, deposit-window-aware, full 327-vault universe, 2025-08-01 → 2026-07-10, 25,000 USD.
- **Prior evidence chain**: NB31 (ablation: every element load-bearing except min-hold), NB33/NB34 (deposit-window honesty), NB35/NB36 (6-vault basket halves drawdown), NB38 (IC study: long-horizon quality dominates), NB39 (extended feature study).

## Hypotheses (from the NB38/NB39 cross-sectional IC studies)

Spearman information coefficients against 30-day forward vault returns, computed every 14
days over ~100+ eligible vaults (≥ 60d history, TVL ≥ 7,500 USD). Redundancy = average
cross-sectional rank correlation with `cagr_360`.

| # | Hypothesis | Evidence (mean IC, t-stat, redundancy) |
|---|---|---|
| H1 | Ranking vaults by the average cross-sectional **rank** of {cagr_360, sharpe_360, inverse_vol_60} selects better vaults than the current clipped-score composite `0.5×CAGR(360)+0.5×Sharpe(180)` | rank blend IC 0.315 (t 4.9) vs composite 0.242 (t 3.9); largest quintile spread +17.1pp/30d |
| H2 | **BTC market-neutrality** (low \|rolling 90d beta to BTC\|) carries orthogonal positive signal: genuinely delta-neutral vaults persist, directional ones mean-revert | IC 0.154, t 4.3, redundancy only 0.34 — most orthogonal useful feature found |
| H3 | **Equity-curve smoothness** (gain-to-pain 180d, ulcer 90d) detects future winners *earlier* than the composite | gain-to-pain IC 0.168 (t 4.9, red 0.60); detected pmalt by 2025-08-13 and Realist Ca by 2025-10-15 vs composite's 2025-10-11 / 2026-03-07 |
| H4 | **Net TVL inflows are contrarian**: money chases vaults that subsequently underperform; penalising recent net inflows avoids losers | net_flow_30 IC −0.072, t −2.9, redundancy −0.11 (orthogonal) |
| H5 | The winning legs **combine**: improvements from H1–H4 are at least partly additive because their redundancies are low | to be established by NB45; supported by low pairwise redundancy of the legs |

Known negative results to respect: swapping the Sharpe leg to 360d in *clipped-score* form
hurts (IC 0.217 < 0.242) — the improvement exists only in rank space; short-horizon
momentum has no ranking power (IC 0.02–0.05) and stays an exit gate only; vol-of-vol,
return autocorrelation, stale-NAV share and tail ratio carry no usable signal.

## Common protocol for all five backtests

- Template: NB36 (`36-backtest-gated-inverse-vol-max6.ipynb`). Everything held fixed
  except the single change under test: full universe (`top_n=9999`), momentum gate
  14d/−8%, inverse-vol 60d sizing, 6-vault basket, concentration cap 0.50, pool cap 0.15,
  deposit-aware selection, daily rebalance, 25k USD, 2025-08-01 → 2026-07-10.
- All features strictly trailing (no lookahead); new indicators follow the existing
  `IndicatorRegistry` dependency pattern so live execution gets them for free.
- Each notebook reports: headline metrics vs NB36, daily-return correlation and tracking
  error vs NB36, cash-deployment diagnostics, top/bottom positions, and the three heading
  sections (key insights / summary / robustness).
- **Observability rule** (lookahead beyond "trailing"): signals at cycle T use vault
  closes and TVL up to T−1's completed daily candle; deposit-window status resolves
  through `BacktestPricing.can_deposit` exactly as in live; the BTC series uses only
  candles whose close time precedes T. Publication-latency sensitivity (shifting all
  signals one extra day) is run once on the winning variant.
- **Adoption rule**: a variant is promoted to the NB45 combination stage if Sharpe
  improves by ≥ 0.15 **and** max drawdown does not worsen by more than 2pp **and** the
  outperformance survives removing its single largest winning position (re-computed
  equity delta ≥ 50% of the original delta) **and** turnover/cost and deployment
  statistics are reported and not materially worse. Confidence intervals for the
  strategy-vs-baseline daily-return difference come from a 20-day block bootstrap.
- **Multiple-testing discipline**: variant specifications above are pre-registered in
  this plan; no per-notebook parameter tuning beyond the listed values. One
  placebo control (a permuted-rank selection leg) is run once to calibrate what "passing"
  looks like under the null.

## The five backtests

### NB41 — rank-blend selection (H1), factorial

- The rank blend changes three things at once (score→rank representation, Sharpe horizon
  180→360, adding an inverse-vol leg). Run it as a small pre-registered factorial so the
  effect is attributable: (a) baseline composite; (b) rank-space version of the current
  composite (cagr_360 + sharpe_180 ranks); (c) b with sharpe_360; (d) c plus the
  inverse-vol leg (= the full blend). Four runs, no per-variant tuning.
- Because inverse-vol already controls *sizing*, variant (d) is additionally run with
  equal-weight sizing once, to separate its selection value from its sizing value.
- Implementation note: cross-sectional ranks need a universe-level indicator
  (`IndicatorSource.dependencies_only_universe`), unlike the current per-pair composite.
- Watch-out from NB39: the rank blend's *top-6 detectability* of the eventual winners was
  weaker than its IC suggests; the backtest, not the IC, is the arbiter.

### NB42 — BTC market-neutrality tilt (H2)

- Compute rolling 90d beta of each vault's daily returns to BTC daily returns; add a
  fourth rank leg `rank_pct(−|beta_btc_90|)` (variant A) or an eligibility filter
  `|beta_btc_90| < threshold` searched over {0.1, 0.25, 0.5} (variant B).
- BTC reference price comes from the new `tradingstrategy` helper (see below) so the
  indicator does not depend on the DEX WBTC/USDC supporting pair's quality. Because the
  NB39 signal was discovered on the DEX series, the IC must first be reproduced with the
  Binance series and production timestamps before any backtest run.
- Confound control: low |beta| can proxy low volatility or cash-heavy books rather than
  genuine neutrality. Report the beta leg's IC conditional on inverse-vol quintile, and
  compare the backtest against a volatility-matched placebo tilt.
- Risk: in the 2025-08 → 2026-07 bear window, "low beta" partially proxies "not long
  crypto"; a low-beta filter can lift bear-market Sharpe purely by de-risking.
  Regime-dependence is the main threat to external validity.

### NB43 — smoothness / early-detection leg (H3)

- Add `gain_to_pain_180` (fallback: −ulcer_90) as a rank leg or as a tie-breaker within
  the current composite selection.
- Evaluation guards against two circularities the review flagged: (a) "earlier detection"
  is only credited on dates where *both* the smoothness feature and the composite are
  computable (shorter windows becoming available sooner is mechanical, not signal);
  (b) entry quality is measured across all ex-ante eligible vaults (capture of forward
  share-price growth per entry), not just the six outcome-selected hindsight winners.

### NB44 — net-inflow contrarian penalty (H4)

- Use the proportional share-issuance proxy `net_flow_30 =
  (TVL_t / TVL_{t−30}) / (price_t / price_{t−30}) − 1` (cleaner than the additive
  difference used in NB39), winsorised at the 1st/99th cross-sectional percentiles, NaN
  when TVL is stale for more than 7 days. Subtract `λ × rank_pct(net_flow_30)` from the
  selection rank score, λ fixed at 0.25 (single pre-registered value; the {0.1, 0.5}
  sensitivity runs are diagnostics, not selection candidates).
- The IC is modest (−0.07); the pre-registered success metric for this notebook is
  drawdown and turnover improvement at non-inferior CAGR — not the headline Sharpe rule.

### NB45 — combined champion + leave-one-out validation (H5)

- Combine every leg that individually passed the adoption rule in NB41–NB44 into one
  scoring function; re-run; then NB31-style leave-one-out ablation of the new legs to
  confirm each still earns its keep in combination.
- Also run the NB39 IC study on the pre-2025-08 history window (with non-overlapping
  forward windows and block-bootstrap confidence intervals) as a cheap pseudo-OOS check
  of the feature ranking. A full pre-window portfolio backtest is impossible — the vault
  universe barely exists before mid-2025 — which is exactly why the final step below is
  walk-forward, not another in-sample pass.
- **Adoption endpoint**: whatever NB45 produces is frozen as a written specification and
  evaluated walk-forward on data that accrues after the freeze date (and/or shadow-live),
  before it can replace NB36 as the reference. No further tuning after the freeze.

## Supporting infrastructure: Binance reference price helper

`tradingstrategy.binance.price.fetch_binance_price()` (new, implemented and verified):

- Generic: fetches candles for any Binance spot symbol (default `BTCUSDT`, configurable
  interval) from the public Binance klines REST endpoint, with automatic fallback to the
  non-geo-blocked market-data mirror.
- Caches locally in a DuckDB file at `~/.tradingstrategy/binance-price.duckdb` (alongside
  the other trading-strategy local caches), table keyed by symbol/interval/timestamp.
- **Incremental**: on each call, queries the cache's max timestamp and fetches only newer
  candles, so repeated notebook runs cost one small HTTP request (measured: 6.0 s cold,
  0.46 s warm).
- Naive UTC timestamps throughout, per repo convention.
- Adds `duckdb` as a `trading-strategy` package dependency.
- CLAUDE.md instructs all notebooks to use this helper for BTC beta/residual
  calculations instead of DEX pair prices or ad hoc HTTP fetching.

## Execution outcomes (NB41-NB45)

All five notebooks were built and run on the full 327-vault universe, 2025-08-01 -> 2026-07-10.
**Every hypothesis was rejected under the pre-registered adoption rule; NB36 remains champion.**

| # | Notebook | Best variant | Sharpe (anchor 1.81) | Verdict |
|---|---|---|---|---|
| H1 | NB41 rank-blend factorial | d_rank_blend | 1.60 | REJECTED — rank discards magnitude; every construction step subtracts Sharpe |
| H2 | NB42 BTC-neutrality | beta_filter_0.25 | 2.18 | REJECTED — vol-matched placebo replicates it (low-vol de-risking, not neutrality alpha); edge one-position deep; CI includes 0 |
| H3 | NB43 smoothness | gtp_tiebreak | 2.07 | REJECTED — CI includes 0; edge dies when top position removed |
| H4 | NB44 inflow penalty | inflow_penalty_0.25 (pre-reg λ) | 1.15 | REJECTED — wrecks drawdown (−21%) and doubles turnover |
| — | NB41 incidental lead | composite_panel | 2.79 | ARTEFACT — collapses to Sharpe 1.60 under a +1-day publication lag (NB45); ffill not the cause |

Supporting findings:
- The BTC-beta signal reproduced on the Binance series (IC 0.157 vs NB39's DEX-series 0.154),
  so the H2 precondition passed — but the portfolio tilt still failed the vol-matched placebo.
- The pre-window IC pseudo-OOS is infeasible: 0 vaults have ≥120d of history before 2025-08-01.
- The random-selection placebo (NB41) returned Sharpe −1.85 / DD −32%, confirming the
  gate/caps/deposit machinery alone is not enough and real selection signal matters — but the
  shipped composite already captures the convertible part.

**Lesson**: the NB38/NB39 cross-sectional ICs were real but did not convert to portfolio
edges surviving bootstrap CIs, single-position robustness, placebo controls and a one-day
publication lag — the same IC≠backtest lesson as NB31, now enforced by the review-hardened
protocol. The disciplined design prevented four to five false adoptions.

## Risks and limitations (apply to all five)

- IC ≠ backtest: NB31 proved blend construction dominates single-feature signal ranks
  (cagr-only ranking had higher IC but worse drawdowns). Each hypothesis must survive the
  full pipeline including the gate, caps and deposit-window logic.
- Single regime: one 11-month window, broadly a crypto bear. Smoothness and neutrality
  legs may be bear-market artefacts; the NB45 pre-window IC check partially mitigates.
- Overlapping forward windows inflate the IC t-statistics; the *ranking* of features is
  what we rely on, not the significance levels.
- No true out-of-sample data exists; the standard live haircut from the NB30/NB36 write-ups
  (budget live Sharpe ~1.0–1.4) continues to apply to whatever wins.

## External review response (Codex CLI, GPT-5.6-sol — verdict: rework)

The full 15-point review is preserved in the research log. Disposition:

| # | Finding | Response |
|---|---|---|
| 1 | Everything reuses one window; NB45's IC check is not real validation | Accepted — adoption endpoint changed to frozen-spec walk-forward / shadow-live (NB45 section) |
| 2 | Universe may not be point-in-time / survivorship-free | Partially disputed: since NB18 the backtests use the full point-in-time vault population including vaults that later died ("survivor-first" is an allocator name, not a universe filter). Accepted residual: quarantine lists and revised metadata can embed later knowledge; noted as a limitation |
| 3 | Far more than five tests → winner's curse | Accepted — specifications pre-registered, λ fixed for NB44, factorial in NB41 replaces cherry-picking, placebo control added |
| 4 | NB41 confounds three changes | Accepted — factorial design (a)-(d) + equal-weight sizing control |
| 5 | H3 evidence and metric are circular; earlier availability is mechanical | Accepted — evaluation restricted to dates where both features exist, across all ex-ante eligible vaults |
| 6 | IC t-stats overstated (23 dates, overlap, cross-correlation) | Accepted — NB45 re-runs use non-overlapping windows + block bootstrap; t-stats treated as ordering evidence only |
| 7 | "Trailing" ≠ observable | Accepted — explicit observability rule added to the protocol |
| 8 | Eligibility/missing-leg handling underspecified | Accepted — ranking universe = deposit-open, TVL ≥ floor, all legs computable; vaults missing any leg are excluded rather than zero-filled; IC studies and backtests share this rule |
| 9 | BTC source changed between discovery and production; beta confounds | Accepted — IC reproduction with the Binance series is a precondition; vol-conditional IC and vol-matched placebo added |
| 10 | Flow proxy first-order only; hygiene unspecified | Accepted — ratio form, winsorisation, staleness rule specified |
| 11 | Additivity premise weak; redundancy only vs CAGR | Accepted in part — NB45 reports pairwise redundancy of adopted legs; final validation deferred to walk-forward per #1 |
| 12 | Adoption rule arbitrary/subjective | Accepted — numeric single-position rule, block-bootstrap CIs, turnover/cost/deployment reporting added; NB44 given its own pre-registered endpoint |
| 13 | 30d/14d research horizon vs daily trading | Accepted as diagnostics — IC decay across horizons and a daily-vs-weekly rebalance control on the winning variant |
| 14 | IC universe not investability-matched | Accepted — NB45 IC re-runs restricted to the deposit-open, pool-cap-feasible universe |
| 15 | Missing placebo/exposure controls | Accepted — permuted-rank placebo and vol/beta-matched controls added |
