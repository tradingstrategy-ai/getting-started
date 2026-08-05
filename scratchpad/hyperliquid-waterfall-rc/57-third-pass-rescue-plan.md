# NB57 - third-pass rescue plan: why the allocation research failed and how to redo it

- **Inputs**: NB38/NB39 (IC studies), NB40 plan, NB41-NB45 (first pass, H1-H4), NB46 plan,
  NB47-NB51 (second pass), NB55/NB56 (holding-period and capacity searches).
- **Purpose**: two passes of allocation-signal research returned "nothing beats the shipped
  NB36 composite". This document establishes *why* that happened, separates genuine negative
  results from artefacts of the test protocol, and specifies a third pass that can actually
  answer the question.
- **Status**: analysis complete, redesign proposed, nothing executed.

---

## Part 1 - post-mortem

### Finding 1: there is no look-ahead bias, and the strongest lead was disqualified by a mis-specified test

The data pipeline and the engine were audited end to end.

**Raw data is point-in-time.** In `cleaned-vault-prices-1h.parquet`, `timestamp` is the poll
instant (e.g. `2026-07-23 16:02:44.039`) and `written_at` is when it was recorded. Across
950,952 Hyperliquid rows, `written_at - timestamp` has median **1.6 hours**, 25th percentile
0.011 h, and **0.0% of rows are written at or before the poll instant**. This is a real-time
on-chain poll, not delayed accounting data.

**Candle construction is left-labelled.** `resample_candles()` calls
`df.resample(freq).agg({"close": "last"})`; pandas defaults to `label="left"`, so the daily
bar labelled `T` spans `[T, T+1d)` and its close is the last poll before `T+1d`.

**The engine already applies a one-bar shift.** `StrategyInputIndicators.get_indicator_value()`
computes `shifted_ts = ts + time_frame * index` with `index = -1` by default, and its docstring
states the intent explicitly: *"Does not return the current timestamp value in the decision
cycle, because any decision must be made based on the previous price."*

**Net alignment**: at decision cycle `T` the strategy reads the bar labelled `T-1d`, which
closes at `T`. It therefore uses a share price observed just before `T`. **This is correct.**

**Consequence for NB45.** The panel-composite (`a_composite_panel`, +0.98 Sharpe, bootstrap CI
excluding zero, survived the single-position robustness check) was disqualified because a
`+1 day` publication lag collapsed it to Sharpe 1.60. That test is invalid here:

- it applies a **1-day** correction to a feed whose measured latency is **~1.6 hours** - an
  over-correction of roughly 15x;
- it is applied *on top of* the framework's existing one-bar shift, so `composite_panel_lag1`
  is not "the signal without look-ahead", it is **the signal one full day stale**;
- that is exactly why it landed *below* the anchor (1.60 vs 1.81) instead of converging to it.
  A genuine look-ahead removal converges to the honest value; an over-correction undershoots.

NB47 independently found the framework composite is as-of-T (shift 0) and concluded the panel
advantage was a *computation* difference, not look-ahead - but the panel-composite was never
rehabilitated after NB45 disqualified it. **It should be.**

### Finding 2: the adoption rule was underpowered by construction

Measured on the current strategy: annualised volatility **17.7%**, daily volatility **93 bps**.

| Effect | Mean daily outperformance required |
|---|---:|
| ΔSharpe +0.15 (the adoption threshold) | **0.73 bps/day** |
| ΔSharpe +0.27 (H3 smoothness) | 1.31 bps/day |
| ΔSharpe +0.37 (H2 BTC-neutrality) | 1.79 bps/day |
| ΔSharpe +0.98 (panel-composite) | 4.75 bps/day |

Observed 20-day block-bootstrap 95% CI half-widths on paired daily differences: **1.64 bps**
(H3 as reported in NB43, n≈344) to **3.25 bps** (measured directly here at n=190). The implied
**minimum detectable effect is ΔSharpe ≈ +0.34 to +0.50**.

The adoption threshold (+0.15) therefore sits **2-3x below the detection floor**. The protocol
was structurally incapable of adopting anything in the +0.15 to +0.35 band.

Every hypothesis tested landed in or below that dead zone - H1 −0.21, H3 +0.27, NB48 J=2 +0.29,
H2 +0.37 - and the **only** variant whose CI excluded zero (panel-composite, +0.98) is the only
one that cleared the floor. That is not four independent scientific refutations; it is a power
curve. The "clean negative result" was substantially predetermined by sample size.

### Finding 3 (new): NAV staleness is the dominant noise source, and it is non-stationary

Hyperliquid vault marks are stale for a large and *time-varying* fraction of days.

Polling density (polls per vault per day):

| Period | Polls/vault/day |
|---|---:|
| 2025-01 .. 2025-12 | ~1.8 |
| 2026-01 .. 2026-03 | **1.1 - 1.5** |
| 2026-04 .. 2026-07 | **12 - 22** |

Measured daily vault returns in the NB41 window:

| Month | % days exactly zero return | % days abs > 5% | Excess kurtosis |
|---|---:|---:|---:|
| 2025-08 | 13.0 | 48.6 | 4.9 |
| 2025-12 | 20.1 | 28.6 | 17.5 |
| 2026-02 | **47.6** | 14.0 | 46.1 |
| 2026-03 | **57.2** | 10.0 | 50.0 |
| 2026-05 | 28.1 | 11.9 | **180.0** |
| 2026-07 | 33.1 | 11.2 | 51.4 |

Consequences:

1. **Portfolio risk statistics are distorted.** This is textbook illiquidity smoothing: stale
   marks understate volatility and inflate Sharpe, while catch-up jumps manufacture fat tails.
   Every Sharpe and max-drawdown comparison in NB41-NB50 rests on this substrate.
2. **Effective sample size is far below nominal.** A third to a half of daily observations
   carry no information, so the bootstrap CIs in Finding 2 are *optimistic* - the true
   detection floor is worse than +0.34.
3. **There is a data-regime break at 2026-04** - inside the NB55/NB56 evaluation window and
   near the end of the NB41-NB45 window. Results either side are not comparable, and no
   notebook currently splits on it.
4. It explains previously flagged artefacts: NB55's implausible Goon Edging sequence
   (+22.86%, −48.13%, +37.83% on consecutive days) sits in the 48-57%-stale February/March
   window, as does its 9.88 excess kurtosis.

### Finding 4 (retained from NB47): the estimand was wrong

Full-cross-section IC is not the decision metric. Precision-at-6 - the mean 30-day forward
return of the top 6 a feature actually selects - reverses the verdict on the rank blend
(−0.07% vs the composite's +0.70%) and would have predicted H1's failure. Keep it.

### Finding 5 (retained): one window, one regime, no out-of-sample

11 months, a single bear regime, and NB45 showed pre-window pseudo-OOS is impossible (no vault
has ≥120 days of history before 2025-08-01).

### What survives as a genuine negative result

Only H1 (rank blend) and H4 (inflow penalty) were rejected on **mechanism** rather than power -
H1 lost Sharpe at every construction step in the factorial, H4 wrecked drawdown and turnover at
every strength. Those stay rejected. **H2, H3 and NB48 were rejected on evidence the design
could not have produced**, and are properly *undecided*, not refuted.

---

## Part 2 - redesign

Guiding principle: **fix the measuring instrument before testing more hypotheses.** Two passes
were spent measuring signal with a ruler whose error bars exceed every effect of interest.

### Stage A - evaluation substrate (mandatory, no new features, no strategy change)

- **A1. Staleness-aware returns.** Flag every vault-day fresh or stale from poll recency.
  Build a parallel weekly-return basis where staleness largely averages out. Re-express all
  portfolio statistics on both bases.
- **A2. Unsmoothing.** Apply Getmansky-Lo style AR(1) unsmoothing to vault NAV series; report
  raw and unsmoothed Sharpe and drawdown side by side. If the champion's Sharpe moves
  materially, every historical comparison in NB41-NB50 needs re-basing.
- **A3. Effective sample size.** Replace nominal `n` in every CI with `n_eff` derived from the
  informative-observation fraction and smoothing-induced autocorrelation.
- **A4. Regime split at 2026-04-01.** Report the sparse and dense regimes separately, always.
  Never pool across the break.
- **A5. Pre-register the minimum detectable effect** for the chosen design *before* running it,
  and set the adoption threshold at or above it. If the design cannot detect +0.15 Sharpe, do
  not claim to test for +0.15 Sharpe.

*Exit criterion: we know what we can and cannot detect. No adoption decisions in this stage.*

### Stage B - rescue the one real lead (highest expected value)

- **B1.** Pre-registered clean test varying **only** the feature-computation method
  (framework candle-index vs calendar-grid panel), with selection formula, gate, caps, sizing
  and deposit logic all fixed.
- **B2.** Replace the +1-day lag test with an **as-of-availability join on `written_at`**. The
  feed records exactly when each observation became known, so realistic latency can be
  reproduced precisely instead of approximated by a round day. This is the correct robustness
  test and it is cheap.
- **B3.** If it survives correct latency in both regimes, this is a **framework
  feature-computation fix**, not a strategy change - and it is worth close to +1.0 Sharpe on
  the reported numbers. Caveat: part of the panel advantage may be its handling of sparse
  history, which Stage A also addresses; B1 must therefore run *after* A so the two are not
  confounded.

### Stage C - feature families the measurement problem does not destroy

NB38/NB39 restricted themselves to *close price and TVL only*. The Hyperliquid vault feed
carries well-populated columns that have never been tested:

| Column | Non-null in window | Rationale |
|---|---:|---|
| `leader_fraction` | 91.4% | leader skin-in-the-game |
| `leader_commission` | 91.4% | incentive alignment |
| `follower_count` | 94.1% | crowding / capacity pressure |
| `cumulative_volume` | 91.1% | turnover and activity intensity |
| `account_pnl` | 100% | realised trading outcome |

These are attractive precisely because they are **measured independently of the share-price
series**, so they do not inherit NAV staleness, and they are orthogonal to every feature in
NB39. Screen with precision-at-6 in both regimes before any backtest earns time.

### Stage D - model class discipline

Given small `n_eff`, a flexible ML model is the wrong instrument. Constrain to:

- low-dimensional, monotone combinations of pre-screened features;
- shrinkage toward the shipped composite - a candidate must *justify* departures from it;
- expanding-window walk-forward refits, never a single in-sample fit;
- learning-to-rank on precision-at-6 rather than IC, if anything is fitted at all.

Adoption requires all of: clears the Stage-A power bar, holds in both regimes, survives
as-of-availability latency, and survives removal of the single largest contributing position.

### What to drop

- Full-cross-section IC as a screen (superseded by precision-at-6).
- Any further round-day publication-lag tests.
- Re-testing H1 and H4 at the same strength - rejected on mechanism, not power.
- H2 and H3 stay parked until Stage A establishes whether they are detectable at all.

### Ordering

1. **Stage A** - calibration. Mandatory; everything else is uninterpretable without it.
2. **Stage B** - panel-composite rescue. Highest expected value; the only variant that ever
   cleared the detection floor.
3. **Stage C** - new feature families. Best chance of genuinely new signal.
4. **Stage D** - only if Stage C yields multiple survivors.

### Honest expectation

Stage A may reveal that the champion's own Sharpe is partly a staleness artefact. That would be
an uncomfortable but valuable result, and it is better found now than in live trading. The
realistic upside of this programme is a correctly-computed composite (Stage B) plus one or two
orthogonal Hyperliquid-native features (Stage C) - not a large new alpha model, which the
effective sample size cannot support.
