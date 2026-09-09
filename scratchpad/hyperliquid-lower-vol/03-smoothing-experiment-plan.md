# Equity-curve smoothing plan: allocate to steady vaults, not to single-event BTC beta

- **Status**: REVISED after an independent Codex CLI review (see
  [03-smoothing-experiment-plan-codex-review.md](03-smoothing-experiment-plan-codex-review.md)).
  Ready for execution.
- **Baseline to beat**: [02-better-format.ipynb](02-better-format.ipynb), re-run as the anchor in every
  notebook because vault data is downloaded fresh each run.
- **Inputs**: the waterfall-rc allocation research (NB40-NB51, NB77-NB79, NB83-NB84, NB88), the NB57
  post-mortem, the live `hyper-ai` book snapshot and the vault steadiness metrics posted on
  [PR #60](https://github.com/tradingstrategy-ai/getting-started/pull/60).

## Goals

1. **Maintain high CAGR.** The baseline is 37.90% CAGR. A smoother curve that gives up most of the
   return is not the target; the floor is set in the adoption rule below.
2. **Allocate more to vaults that make steady profit and less to vaults whose trailing record is one
   BTC-driven event.** This is a change in *what the score measures*, not a search for a better
   lookback.

## Why the baseline curve is not smooth

The baseline and the live book agree on the mechanism:

| Symptom | Baseline (NB02) | Live book (2026-09-09) |
|---|---|---|
| Profit concentration | Top 5 positions are 94.5% of net profit; Realist Capital alone 48.1% | Realist Capital blew up after entry: trailing 30d -67% |
| Tail dependence | Removing the best 5 days cuts total return from 24.62% to 3.49% | 24% win rate, -$8,311 realised over 108 filled positions |
| Daily return shape | Skew 3.60, kurtosis 32.40 | Held vaults Octavious, DOEZOE, Sequoia carry 90d BTC beta 1.0, 2.1, 3.8 |
| Single-event record | 41 of 96 entries at the 33% pool cap | Best-5-day share of 180d return above 1.0 for all three, meaning every other day was net negative |
| Steady vaults dropped | - | 22Cap (4% vol, beta 0.01, 93% positive 30d windows) held 5 days; HYPErQuant (13% vol, 97% positive windows) held 2 days |

Two structural facts make this worse than the score alone would:

- `allocation_pct = 0.98` forces near-full deployment. When the 33% concentration cap binds on the
  best vault (Citadel and AceVault both sit at 32.5% at the close), the overflow has nowhere to go
  except the next-ranked names, which are the pumpers.
- The candidate set grows from 106 to 172 across the window while `max_assets_in_portfolio` pins
  the basket at 6, so breadth that would dilute single-vault risk is discarded by construction.

## The measurement problem this plan must respect

NB57 established three facts about the data that shape every experiment here:

- **Marks are stale for a large, time-varying share of days.** Zero-return vault days were 47.6% in
  2026-02 and 57.2% in 2026-03. Stale marks understate volatility, inflate Sharpe and Sortino, and
  manufacture catch-up jumps that read as fat tails. Downside deviation, ulcer index, down-day share
  and best-day share are all computed from exactly these marks.
- **There is a polling-regime break at 2026-04.** Polls per vault per day went from 1.1 to 1.5 in
  January to March to 12 to 22 from April. The baseline window straddles it, so results either side
  are not comparable unless split.
- **The detection floor is high.** On the older, longer sample a paired 20-day block-bootstrap could
  not detect a Sharpe difference below about +0.34, and stale marks make that optimistic. Eight
  months of data cannot certify small edges; the protocol below is built so that it does not
  pretend to.

## What the chain has already ruled out

Every experiment below is shaped by these. Repeating them is a waste of a notebook.

| Prior result | What it rules out | What it leaves open |
|---|---|---|
| NB78: averaging the composite over 90/180/360d windows | Mean-of-windows ensembles. Strict variant fell 32% to 17% CAGR with drawdown -9% to -22%; the NaN-tolerant variant was catastrophic | A **minimum** across windows with identical windows required of every candidate. Untested. |
| NB79: five families of veto (downside share, down-day share, autocorrelation, skew, age) | Hard exclusion of candidates. Vetoes that removed only losers still lost, because freed capital went further down the ranking | Continuous re-weighting, and any filter paired with the option to hold cash |
| NB79 V6: Sharpe leg replaced by Sortino | - | Adopted into the candidate. Re-ranking helped where vetoes did not, so the score is the right place to intervene |
| NB42: BTC-beta filter at 0.25 | Adoption under a Sharpe-improvement rule. The vol-matched placebo reproduced two thirds of the gain | Under a volatility-constrained objective the "placebo" is the point. Drawdown fell from -7.8% to -5.0% |
| NB43: gain-to-pain tiebreak | Equal-weight rank blends, which dilute | A small continuous tilt (0.15 weight) cut drawdown; it failed only on bootstrap power |
| NB44 and NB50: inflow penalty and extreme-inflow exclusion | Flow-based selection in a 6-vault book | Nothing; do not revisit |
| NB47: residual composite | A residual-CAGR selection leg, which scored 0.33% against the composite's 0.70% at the top six | Re-testing only if it clears a stronger, staleness-aware screen (NB03b). It does not get a backtest on the strength of a changed objective alone |
| NB77: losers are lower-volatility and `inverse_variance` overweights them | Naive "lower vol is safer" sizing | Sizing by drawdown-based risk with floors and a real maximum weight |
| NB47 and NB51: two passes over 35 selection features | Screening by cross-sectional IC | Precision-at-6 as a descriptive pre-screen, not as evidence |
| NB57 correction: panel-indexed features had 24h look-ahead | Any feature read directly from a daily panel at the decision date | The framework `get_indicator_value()` path, plus an as-of availability audit for each new feature |
| NB83 and NB84: best-day removal without a null, and a two-value lookback grid | Reporting "removing the best N days destroys the return" as a finding; subtracting a position's P&L as a counterfactual | Best-day removal against a random-removal null; leave-one-vault-out by full re-simulation |
| NB84: the winning positions were implausibly large fractions of tiny vaults | Treating fill-at-NAV at 33% of pool TVL as realistic | Capping positions at a few percent of vault TVL before any breadth experiment |

## Hold-out, reserved before any variant is run

- **Development window**: 2026-01-01 to 2026-06-30.
- **Hold-out window**: 2026-07-01 to 2026-09-08. Roughly ten weeks, 35 decision cycles at the
  2-day cadence. It is not opened until NB11, and it is opened once.
- **Regime split inside development**: every development result is also reported for
  2026-01-01 to 2026-03-31 (sparse polling) and 2026-04-01 to 2026-06-30 (dense polling)
  separately. A variant that wins only in the sparse regime is a stale-mark artefact until shown
  otherwise.
- **Staleness-aware reporting**: every metric is reported on daily returns and on weekly-resampled
  returns. Where the two disagree on the sign of an edge, the weekly figure is the one reported in
  the heading.

The full-window numbers in [02-better-format.ipynb](02-better-format.ipynb) are the last time this
track quotes a result on the whole period before NB11.

## Pre-registered objective and adoption rule

The chain optimised Sharpe or CAGR on a window where BTC pumps paid, and any new score will be
re-optimised into pumps unless the objective changes first. The objective is therefore a
**constrained** one: satisfy the constraints, then rank by the Martin ratio.

**Constraints, all measured on the development window against the anchor re-run in the same
notebook:**

| Constraint | Threshold | Why |
|---|---|---|
| CAGR | at least 30% | Goal 1. Permits a 7.9 pp sacrifice from the anchor and no more |
| Annualised volatility | no worse than the anchor's 15.47% | Stops "smoother" meaning "more volatile but with a better ratio" |
| Ulcer index of the daily equity curve | lower than anchor | The smoothness measure that penalises time under water rather than upside |
| Absolute BTC beta of the **invested basket**, cash excluded, 90d rolling | lower than anchor, with R-squared reported | Goal 2, measured where it lives. Cash-inclusive beta is reported only as an exposure figure, since holding cash lowers it trivially |
| Time in market | at least 45% of days, against the anchor's 50% | A variant below this is reported as a cash-overlay result, not as evidence that selection improved |
| Accounting | destroyed and stranded capital identity holds; redemption-fee audit reconciles | Any variant whose books fail is rejected regardless of return |

**Ranking metric** among variants that satisfy the constraints: Martin ratio, CAGR divided by ulcer
index.

**Robustness panel**, reported for every variant and required for Adopt:

- **Leave-one-vault-out**: a full re-simulation with the largest-contributing vault blacklisted from
  the start. Subtracting its realised P&L is not a counterfactual (NB83). The edge over the anchor
  must survive.
- **Luck ratio**: total return after removing the best 5 days, divided by the median total return
  after removing 5 random days over 500 draws. Reported against the anchor's own ratio; the
  variant must not be more outlier-dependent than the anchor.
- **Gross-profit concentration**: share of gross profit in the top 5 positions. Gross rather than net,
  because net profit near zero makes shares meaningless.
- **Paired 20-day block-bootstrap CI** on the daily return difference against the anchor, reported
  with the minimum detectable effect computed in NB03a. A CI that includes zero is expected on this
  sample and is not by itself a rejection; it is stated so that no result is oversold.
- **Plateau, not spike** (NB79): adjacent parameter values must also satisfy the constraints.
- **One winner per family**: each notebook nominates at most one configuration to NB11, chosen by
  the pre-registered ranking metric, not by inspection.

**Tiers:**

- **Adopt**: all constraints, the full robustness panel, both polling regimes.
- **Provisional**: constraints and robustness panel, but the edge is present in only one regime.
  Carried to the prospective shadow period as a frozen spec. **Not combined with Adopt winners.**
- **Reject**: anything else.

## Experiment track

Each notebook changes one mechanism, re-runs the anchor on the development window, reports the
constraints, ranking metric and robustness panel, and states its verdict in its heading.
Measurement gates the backtests; structural levers that do not depend on selection quality come
before score changes; capacity realism comes before breadth.

### NB03a - measurement: data quality, attribution and power

No strategy change.

1. **Staleness flags.** For every vault-day in the development window, a fresh-observation flag
   from poll density and zero-return runs. Report the fresh share by month and by vault, and
   confirm the 2026-04 regime break on this track's freshly downloaded data.
2. **Availability audit.** For each feature used anywhere in this plan, compare the framework
   indicator value at decision cycle T against what the raw poll data contained by T. Any feature
   that fails is rebuilt or dropped before it is screened.
3. **Baseline attribution by vault beta.** For every position in the anchor run, the vault's 90d
   BTC beta at entry (Binance series via `fetch_binance_price()`, framework indicator path, fresh
   observations only), with P&L, drawdown contribution and days held in three buckets: beta below
   0.2, 0.2 to 0.6, above 0.6. This is how much of the 37.90% is the thing we want to remove.
4. **Power calculation.** The anchor's daily tracking error against itself under 20-day block
   resampling, and the implied minimum detectable Sharpe and Martin-ratio differences on the
   development window, on daily and weekly returns. Every later notebook quotes these numbers.

### NB03b - decision-aligned feature screen, descriptive only

No strategy change. Precision-at-6 (NB47 method) on the tradable pool, using fresh observations
only, reported in both polling regimes. The screen orders features and gates the selection
notebooks; it is **not** evidence that a feature works, because a 30-day forward window gives
about eight non-overlapping observations here.

Features, all as framework indicators:

- `beta_btc_90` with its R-squared and 30-day stability; residual CAGR from `r - beta * r_btc`
- **residual-event concentration**: share of trailing 180d residual log return in the top 5
  residual days, defined only where at least 60 fresh observations exist
- ulcer index 180d, downside deviation 90d, drawdown duration and recovery time, on fresh
  observations
- share of positive rolling 30d windows
- minimum across 30/90/180/360d window Sortino, for vaults with a full 360 days of history
- down-day share 90d as a band: too few is NB78's blow-up signature, too many is bleeding
- TVL trajectory and the requested-position-to-TVL ratio; deposit and redemption availability
  history
- the vault-feed metadata NB57 Stage C identified as independent of the share-price series:
  `leader_fraction`, `leader_commission`, `follower_count`, `cumulative_volume`, `account_pnl`

Gate: a selection feature earns its notebook only if its tradable top-6 beats the incumbent
composite's top-6 on 30d forward Martin ratio in **both** regimes.

### NB04 - structural: portfolio volatility target with cash as a position

Selection untouched. Scale `allocation_pct` each cycle by `min(1, target_vol / ex_ante_vol)`, where
ex-ante vol is the inverse-variance-weighted basket's trailing 30d volatility on fresh observations.
Sweep target annualised vol at 10%, 12.5%, 15%, 17.5%, 20%. Cash sits in the reserve asset; a
managed-yield variant is a diagnostic only.

This is the one lever that removes the overflow-into-pumpers mechanism without touching the ranking,
and it is the cash option every later change needs to avoid NB79's substitution failure. The
time-in-market constraint applies; a target that wins only by sitting out is a cash-overlay result.

### NB05 - structural: capacity realism before anything else grows

Selection untouched. `per_position_cap_of_pool_pct` swept from the baseline 0.33 down through
0.15, 0.10, 0.05, plus a minimum vault-TVL-to-position multiple. NB84 found the chain's largest
wins came from positions of 38% of a vault's TVL and recommended low single digits. The winner
here becomes the fixed cap for every later notebook, and the anchor for NB06 onwards is re-run
under it. Expect CAGR to fall; the point is that any smoothing measured on top of an unrealistic
cap is not worth having.

### NB06 - structural: breadth, then concentration

Selection untouched, capacity cap from NB05. Two sequential sweeps rather than a grid:

1. `max_assets_in_portfolio` at 6, 8, 10 with `max_concentration_pct` held at 0.33.
2. `max_concentration_pct` at 0.20, 0.25, 0.33 at the breadth chosen in step 1.

The candidate set doubled over the window and $87,248 was discarded for lack of lit liquidity at
the close, but more discarded liquidity does not imply more deployable names, which is why NB05
comes first. NB68 found 7 to be a reproducible hole at 150,000, so step 1 must show a plateau.

### NB07 - sizing: drawdown-based risk, one family at a time

Selection untouched. Each family is run with a **minimum fresh-observation count** before a vault
can be sized on the measure, a **weight floor** so that a vault with no reported down days cannot
receive an unbounded weight, and the concentration cap as a true maximum.

1. `1 / ulcer_180`
2. `1 / downside_deviation_90`
3. Marginal risk-contribution sizing with a residual-correlation cap, so that two vaults that are
   the same BTC trade cannot both fill the basket

NB77 showed inverse variance hands the largest weights to a quiet cohort of small losers; the
floors exist because ulcer and downside deviation have the same stale-mark vulnerability. The
NB72 exponent finding is re-tested under whichever measure wins, because it may not carry over.
The volatility multiplier from the first draft of this plan is dropped: it penalised high-vol vaults
without capping anything, and after normalisation it concentrates capital in the NB77 cohort.

### NB08 - selection: continuous penalty on residual-event concentration

Requires the residual-event concentration feature to pass NB03b. Multiply the composite by
`1 - lambda * clip(concentration, 0, 1)`, sweeping lambda at 0.25, 0.5, 0.75, 1.0, applied only
where at least 60 fresh observations exist. The statistic is defined on residual log returns, not
raw returns, so a legitimate trend-following vault with genuine positive skew is not treated as a
single untradeable mark. NB43's gain-to-pain tilt at 0.15 is the second arm, re-run under the new
objective. The random-day-removal null is reported for every arm.

### NB09 - selection: minimum-across-windows consistency

Requires the feature to pass NB03b. Score by the minimum of window Sortino over 30, 90, 180 and 360
days, blended with the CAGR leg at the incumbent `cagr_weight`. **Every candidate must have the
full 360 days of history**; vaults without it are excluded from this experiment rather than
scored on the windows they have, because that recreates NB78's NaN-tolerant failure and mixes
consistency with maturity. Young-vault handling is out of scope here and is noted as a separate
question for a later notebook.

### NB10 - conditional: BTC-residual CAGR leg

Runs **only** if residual CAGR clears the NB03b gate in both regimes. NB47 gated it out at 0.33%
against 0.70%, and a changed objective does not on its own reverse that. If it runs: replace the raw
360d CAGR leg of `cagr_sortino_weight` with CAGR of a residual NAV index built from
`r - beta_90 * r_btc`; the Sortino leg and the momentum gate stay on raw returns because exits must
respond to real NAV drops. Variants: full beta, and beta shrunk 50% toward zero.

### NB11 - combination, hold-out and close-out

1. **Combination.** Adopt winners only, one per family, added one at a time in order of Martin-ratio
   gain on the development window, checking after each addition that every constraint still holds.
   Parameters are frozen before step 2.
2. **Hold-out.** The frozen combination and the anchor are run once on 2026-07-01 to 2026-09-08.
   Constraints and the robustness panel are reported; nothing is re-tuned afterwards.
3. **Live-book case study.** Whether the frozen rule would have held Octavious, DOEZOE and Sequoia
   and dropped 22Cap and HYPErQuant, reported as a diagnostic. It is not a gate, because those names
   motivated this plan and passing on them is outcome fitting.
4. **Prospective shadow specification.** The hard pre-deployment gate is a forward shadow run of the
   frozen spec alongside the live strategy for at least 30 decision cycles, with a capacity and
   deposit-availability audit at each cycle. This is written down here so that it cannot be relaxed
   later.
5. Verdict table across NB03a to NB10 and the recommended configuration, if any.

## Controls in every backtest notebook

- Anchor re-run in the notebook on the development window, reproduced to the dollar before any
  variant is run.
- Both polling regimes and both daily and weekly returns reported for every figure.
- Random-day-removal null alongside the best-5-day removal.
- Vol-matched placebo for any selection change, dropping the same per-cycle count by highest
  volatility. If the placebo matches the variant, the variant is a de-risking effect and is reported
  as such, which under this objective is still admissible.
- Leave-one-vault-out by full re-simulation.
- Capacity realism: entries at the pool cap, discarded lit liquidity, and the reserve-drift warnings
  from the backtest log, reported rather than hidden.
- All features via the framework indicator path with `index = -1`, and each passes the NB03a
  availability audit. No direct panel indexing.

## Review log

- **Draft 1** proposed Martin ratio as a standalone objective, a full-window fit with a
  retrospective fit/test split in NB10, a half-split adoption rule, a residual-CAGR backtest by
  default, a volatility multiplier as a "cap", and breadth before capacity.
- **Codex CLI review** (file linked at the top) found: no treatment of NAV staleness or the 2026-04
  regime break; the fit/test split was not out of sample because every earlier notebook had already
  consumed the test period; the half-split rule was under-powered and had no effect-size
  requirement; portfolio beta was measured where cash could game it; the residual-CAGR notebook
  repeated NB47 without a changed premise; the best-5-day share was undefined near zero return and
  conflated skew with stale marks; the missing-history rule in the consistency score recreated
  NB78's failure; the volatility multiplier was not a cap; breadth before capacity would spread
  capital into more untradeable marks; leave-one-vault-out by P&L subtraction was not a
  counterfactual; and combining Provisional with Adopt promoted results that had failed a gate.
- **Draft 2** (this file) reserves the hold-out up front, adds NB03a, splits the screen into NB03b,
  moves capacity ahead of breadth, rewrites the adoption rule as constraints plus a ranking metric,
  makes the residual-CAGR leg conditional, redefines the event-concentration statistic on residual
  log returns with a fresh-observation requirement, requires identical windows in NB09, replaces the
  sizing multiplier with floors and a true maximum, and demotes the live-book comparison to a case
  study behind a prospective shadow gate.
