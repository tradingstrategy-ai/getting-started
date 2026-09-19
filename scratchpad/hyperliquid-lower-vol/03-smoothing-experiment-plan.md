# Equity-curve smoothing plan: allocate to steady vaults, not to single-event BTC beta

- **Status**: EXECUTED (NB03a-NB09, NB11, NB12), then **re-run on the full window**; NB13 added as an out-of-plan audit of the inclusion rules.

> ## Amendment (2026-09-09): the development/hold-out split is retired
>
> Every notebook now runs the full **2026-01-01 to 2026-09-08** window, matching
> [01-initial.ipynb](01-initial.ipynb) and [02-better-format.ipynb](02-better-format.ipynb). The
> design below reserved 2026-07-01 to 2026-09-08 as a hold-out, opened once in NB11; that
> reservation no longer holds and **the track carries no out-of-sample claim**. Results are
> in-sample throughout. The formerly-reserved period is still reported as a `late_*` sub-period so
> its deterioration stays visible, and NB11 still runs it as a fresh deployment, but it can only
> describe the deterioration now, not validate against it.
>
> Two verdicts changed as a result, and both moved against the candidate:
>
> - The vol-matched rule passed at N = 25, 30 and 35 on the shorter window, which is a plateau. On
>   the full window only 30 and 35 pass, with 30 sitting 15 Martin points above both neighbours -
>   a spike. It then fails leave-one-vault-out. **A plateau is only as stable as the window it is
>   computed on**, which is the sharpest methodological finding the track produced.
> - `min_tvl_usd = 25,000` cleared all five constraints on the shorter window and misses the CAGR
>   floor on the full one.
>
> The binding constraint also changed: the CAGR floor is now the most commonly failed (13 of 22
> variants) where the ulcer index was before, because the later period is where the strategy earns
> least.

> ## Addendum (2026-09-09): NB13, the age barrier
>
> [13-research-age-barrier.ipynb](13-research-age-barrier.ipynb) answers a question outside the
> original plan: are high-Sharpe vaults being excluded by an inclusion rule rather than by rank,
> particularly vaults launched after 2026-04-01?
>
> **Finding.** The strategy has no age rule, but `cagr_lookback_days = 360` acts as one:
> **225 of 336 vaults in the trading universe (67%) can never be scored**, an unscored vault
> ranks at signal 0 and never wins a basket slot, and across all 96 anchor positions the youngest
> vault ever bought was **361 days old at entry**. Every one of the 43 post-April launches sits
> behind this barrier.
>
> **Verdict: no change warranted.** The hidden cohort's median life Sharpe is -0.43 against the
> scorable cohort's +0.14. At tradable size only 2 of 32 hidden vaults have a Sharpe resolvable at
> `t > 2`, and the single post-April name that qualifies (Stratwise Multi-Asset Public, Sharpe 7.67)
> earns 27.2% CAGR - below the track's own 30% floor. A decision-aligned screen of the minimal fix,
> shortening the CAGR leg to 90 days, loses the dense regime by 4.00 pp of mean 30-day forward
> return and fails the both-regimes gate. No NB14 follows.
>
> The barrier is nonetheless **undocumented and larger than anyone intended**, and it interacts with
> `inverse_vol_window = 90`, which would zero the weight of any young vault that did get selected.
> If the universe's age mix shifts, this is the first thing to re-measure.

- **Original status**: EXECUTED (NB03a-NB09, NB11). Outcome: every lever tested was REJECTed on the
  development window, and the one apparent lead (NB09's event-concentration penalty) failed the
  NB11 plateau check. NB08 and NB10 were not built - both were gated out by NB03b's precision-at-6
  screen before a backtest was spent on them. The anchor's own hold-out run (2026-07-01 to
  2026-09-08) confirms the track's premise: CAGR falls from 48.76% to 18.59% and Martin ratio from
  34.77 to 9.45 exactly where the BTC-beta pumpers this track targeted actually appear, and a fresh
  hold-out deployment converges to the same closing basket as the full-window backtest and the live
  `hyper-ai` executor. See [11-backtest-closeout.ipynb](11-backtest-closeout.ipynb) for the full
  verdict table and recommended next steps. Below is the original design, revised after an
  independent Codex CLI review (see
  [03-smoothing-experiment-plan-codex-review.md](03-smoothing-experiment-plan-codex-review.md))
  and extended with implementation snippets before execution.
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

## Where the baseline can be changed

Every experiment touches one or more of three cells in [02-better-format.ipynb](02-better-format.ipynb).
The cell numbers below are its code cells as they stand; the descriptions identify them if the
numbering drifts.

| Hook | Cell | What lives there | Which notebooks touch it |
|---|---|---|---|
| `Parameters` class | 6 | Every tunable. Indicator functions receive parameters **by argument name**, so a new indicator argument must have a same-named attribute here | all |
| `indicators` registry | 10 | `@indicators.define(...)` functions. `close` per pair by default; `dependencies=(...)` plus `source=IndicatorSource.dependencies_only_per_pair` for composites built from other per-pair indicators | NB03a, NB03b, NB07, NB08, NB09, NB10 |
| `compute_sizing_weights()` | 20 | Turns per-vault statistics into raw weights; `method` is selected by `Parameters.weighting_method` | NB07 |
| `decide_trades()` candidate loop | 20 | Reads `inclusion_criteria`, applies `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the `return_gate`, then reads `parameters.selection_score_indicator` into `signal` | NB08, NB09, NB10 |
| `decide_trades()` allocation block | 20 | `calculate_portfolio_target_value(position_manager, parameters.allocation_pct)`, `USDTVLSizeRiskModel(per_position_cap=...)`, `normalise_weights(max_weight=..., max_positions=...)` | NB04, NB05, NB06 |
| `MASKED_VAULTS` | 20 | A set of lower-case pool addresses excluded for the run. Already wired into the candidate loop. This is the leave-one-vault-out mechanism | every robustness panel |

Three framework facts that every snippet relies on:

- `indicators.get_indicator_value(name, pair=pair)` inside `decide_trades` returns the value at
  `index=-1`, one bar before the decision timestamp. That is the live-parity path (NB57). Never read
  a pandas panel directly at the decision date.
- `indicator_data.get_indicator_series(name, pair=pair, unlimited=True)` outside `decide_trades`
  returns the whole series for analysis. Use `.asof(timestamp)` to read it as-of a date.
- A new indicator with new argument names forces those indicators to be recomputed; existing cached
  indicators are untouched. If a run crashes with an indicator-cache error after adding indicators,
  use the `clear-backtesting-cache` skill and rerun.

### Creating a notebook

1. Copy `02-better-format.ipynb` to `NN-backtest-<slug>.ipynb` (or `NN-research-<slug>.ipynb` for
   NB03a and NB03b, which run no strategy variant).
2. Set `Parameters.id` to the new file stem and `backtest_end = datetime.datetime(2026, 7, 1)` so
   the run stops at the development window. Do not touch the hold-out.
3. Insert the shared harness below as a new code cell **after** the backtest cell, then the
   notebook's own variant cells after that.
4. Run it with the observable runner. In this environment the shell profile activates the wrong
   virtual environment, so the working form is:

   ```shell
   set -a; source .env; set +a
   VIRTUAL_ENV=$PWD/.venv PATH=$PWD/.venv/bin:$PATH TQDM_LOGGABLE_FORCE=stdout \
     .venv/bin/python -m getting_started.jupyter_execute_agent.cli \
     scratchpad/hyperliquid-lower-vol/NN-backtest-slug.ipynb --timeout=1800
   ```

   `poetry run jupyter-execute-agent <notebook>` is the canonical form when poetry resolves to
   `.venv` correctly.
5. Fill the heading's "Key new insights", "Summary of results" and "Robustness of results" from the
   panel, and state the tier (Adopt, Provisional, Reject) for the single nominated configuration.

## Shared harness

Paste this cell into every backtest notebook after the anchor run. It gives one function to run a
variant, one to compute the panel, and the helpers the robustness rules need. It relies on the
names the baseline already defines: `Parameters`, `parameters`, `indicators`, `indicator_data`,
`strategy_universe`, `client`, `decide_trades`, `MASKED_VAULTS`, `state`, `equity`, `returns`.

```python
import contextlib
import numpy as np
import pandas as pd
from tradeexecutor.strategy.parameters import StrategyParameters
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
from tradeexecutor.backtest.backtest_runner import run_backtest_inline
from tradeexecutor.visual.equity_curve import calculate_equity_curve, calculate_returns
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe, calculate_sortino
from tradingstrategy.binance.price import fetch_binance_price

DEV_START = pd.Timestamp("2026-01-01")
DEV_END = pd.Timestamp("2026-07-01")          # exclusive
REGIME_BREAK = pd.Timestamp("2026-04-01")      # NB57: polling density jumps here
HOLDOUT_START, HOLDOUT_END = pd.Timestamp("2026-07-01"), pd.Timestamp("2026-09-09")


@contextlib.contextmanager
def parameter_overrides(**overrides):
    """Temporarily change class attributes on ``Parameters`` and restore them afterwards.

    ``StrategyParameters.from_class(Parameters)`` is the only construction path the baseline
    uses, so mutate the class in place rather than subclassing it.
    """
    saved = {name: getattr(Parameters, name) for name in overrides}
    for name, value in overrides.items():
        setattr(Parameters, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(Parameters, name, value)


def run_variant(name: str, masked: set[str] = frozenset(), **overrides):
    """Run one configuration on the development window and return ``(state, equity, returns)``.

    :param masked:
        Lower-case pool addresses to exclude for this run. This is the leave-one-vault-out
        mechanism: the vault is unavailable from the first cycle, so substitution is simulated.
    """
    with parameter_overrides(**overrides):
        variant_parameters = StrategyParameters.from_class(Parameters)
        variant_indicators = calculate_and_load_indicators_inline(
            strategy_universe=strategy_universe,
            create_indicators=indicators.create_indicators,
            parameters=variant_parameters,
        )
        MASKED_VAULTS.clear()
        MASKED_VAULTS.update(a.lower() for a in masked)
        try:
            result = run_backtest_inline(
                name=name,
                engine_version="0.5",
                decide_trades=decide_trades,
                indicator_combinations=variant_indicators.indicator_combinations,
                cycle_duration=Parameters.cycle_duration,
                client=client,
                universe=strategy_universe,
                parameters=variant_parameters,
                max_workers=1,
                start_at=Parameters.backtest_start,
                end_at=Parameters.backtest_end,
            )
        finally:
            MASKED_VAULTS.clear()
    variant_state = result.state
    variant_equity = calculate_equity_curve(variant_state)
    return variant_state, variant_equity, calculate_returns(variant_equity)


def btc_daily_returns(index: pd.DatetimeIndex) -> pd.Series:
    """BTC daily returns aligned to ``index``. Cached by ``fetch_binance_price`` in DuckDB."""
    btc = fetch_binance_price()["close"]
    btc.index = pd.to_datetime(btc.index)
    if btc.index.tz is not None:
        btc.index = btc.index.tz_localize(None)
    return btc.pct_change().reindex(index).fillna(0.0)


def daily(returns_: pd.Series) -> pd.Series:
    return returns_.resample("1D").sum(min_count=1).fillna(0.0)


def weekly(returns_: pd.Series) -> pd.Series:
    return returns_.resample("1W").sum(min_count=1).fillna(0.0)


def ulcer_index(equity_: pd.Series) -> float:
    dd = equity_ / equity_.cummax() - 1.0
    return float(np.sqrt((dd ** 2).mean()))


def cagr_of(equity_: pd.Series) -> float:
    days = (equity_.index[-1] - equity_.index[0]).days
    return float((equity_.iloc[-1] / equity_.iloc[0]) ** (365.0 / max(days, 1)) - 1.0)


def invested_basket_beta(state_, returns_daily: pd.Series, window: int = 90) -> tuple[float, float]:
    """90d rolling BTC beta of the invested part of the book, cash excluded.

    Divides the portfolio return by the prior day's invested fraction so that holding cash does
    not lower the beta. Returns ``(mean absolute beta, mean R-squared)`` over the window series.
    """
    rows = {}
    for s in state_.stats.portfolio:
        ts = pd.Timestamp(s.calculated_at).normalize()
        # free_cash is Optional on PortfolioStatistics; treat a missing value as fully invested.
        rows[ts] = 1.0 - float(s.free_cash or 0.0) / float(s.total_equity) if s.total_equity else np.nan
    invested_fraction = pd.Series(rows).sort_index().reindex(returns_daily.index).ffill()
    usable = invested_fraction.shift(1) > 0.2
    invested_return = (returns_daily / invested_fraction.shift(1)).where(usable)
    btc = btc_daily_returns(returns_daily.index)
    cov = invested_return.rolling(window, min_periods=window).cov(btc)
    var = btc.rolling(window, min_periods=window).var()
    beta = cov / var.replace(0.0, np.nan)
    corr = invested_return.rolling(window, min_periods=window).corr(btc)
    return float(beta.abs().mean()), float((corr ** 2).mean())


def luck_ratio(returns_daily: pd.Series, n: int = 5, draws: int = 500, seed: int = 0) -> float:
    """Return without the best ``n`` days, over the median return without ``n`` random days."""
    r = returns_daily.dropna()
    total = lambda x: float((1.0 + x).prod() - 1.0)
    without_best = total(r.drop(r.nlargest(n).index))
    rng = np.random.default_rng(seed)
    nulls = [total(r.drop(rng.choice(r.index, size=n, replace=False))) for _ in range(draws)]
    return without_best / float(np.median(nulls))


def top5_gross_profit_share(state_) -> float:
    profits = sorted(
        (float(p.get_total_profit_usd() or 0.0) for p in state_.portfolio.get_all_positions() if not p.is_credit_supply()),
        reverse=True,
    )
    gross = sum(x for x in profits if x > 0)
    return sum(profits[:5]) / gross if gross > 0 else float("nan")


def largest_contributing_vault(state_) -> str:
    """Pool address of the vault with the largest total P&L, for leave-one-vault-out."""
    by_vault = {}
    for p in state_.portfolio.get_all_positions():
        if p.is_credit_supply():
            continue
        by_vault[str(p.pair.pool_address).lower()] = by_vault.get(str(p.pair.pool_address).lower(), 0.0) + float(p.get_total_profit_usd() or 0.0)
    return max(by_vault, key=by_vault.get)


def block_bootstrap_ci(diff: pd.Series, block: int = 20, draws: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% CI on the mean of a paired daily-difference series under 20-day block resampling."""
    d = diff.dropna().to_numpy()
    n = len(d)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        sample = np.concatenate([d[s:s + block] for s in starts])[:n]
        means.append(sample.mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def panel(label: str, state_, equity_, returns_, anchor_returns_daily: pd.Series | None = None) -> pd.Series:
    """The constraint and robustness panel for one run, on daily and weekly returns and both regimes."""
    rd = daily(returns_)
    out = {"label": label}
    for tag, r in (("daily", rd), ("weekly", weekly(returns_))):
        periods = 365 if tag == "daily" else 52
        out[f"{tag}_sharpe"] = float(calculate_sharpe(r, periods=periods))
        out[f"{tag}_sortino"] = float(calculate_sortino(r, periods=periods))
        out[f"{tag}_vol"] = float(r.std() * np.sqrt(periods))
    out["cagr"] = cagr_of(equity_)
    out["ulcer"] = ulcer_index(equity_)
    out["martin"] = out["cagr"] / out["ulcer"] if out["ulcer"] > 0 else float("nan")
    out["max_dd"] = float((equity_ / equity_.cummax() - 1.0).min())
    out["abs_invested_beta"], out["beta_r2"] = invested_basket_beta(state_, rd)
    out["time_in_market"] = float((rd != 0).mean())
    out["luck_ratio"] = luck_ratio(rd)
    out["top5_gross_share"] = top5_gross_profit_share(state_)
    for regime, sl in (("sparse", slice(DEV_START, REGIME_BREAK - pd.Timedelta(days=1))), ("dense", slice(REGIME_BREAK, DEV_END))):
        e = equity_.loc[sl]
        out[f"{regime}_cagr"] = cagr_of(e) if len(e) > 10 else float("nan")
        out[f"{regime}_ulcer"] = ulcer_index(e) if len(e) > 10 else float("nan")
    if anchor_returns_daily is not None:
        lo, hi = block_bootstrap_ci(rd - anchor_returns_daily.reindex(rd.index).fillna(0.0))
        out["diff_ci_lo_bps"], out["diff_ci_hi_bps"] = lo * 1e4, hi * 1e4
    return pd.Series(out)


def passes_constraints(row: pd.Series, anchor: pd.Series) -> bool:
    return bool(
        row["cagr"] >= 0.30
        and row["daily_vol"] <= anchor["daily_vol"]
        and row["ulcer"] < anchor["ulcer"]
        and row["abs_invested_beta"] < anchor["abs_invested_beta"]
        and row["time_in_market"] >= 0.45
    )


# Anchor on the development window. Every notebook starts here.
anchor_state, anchor_equity, anchor_returns = run_variant("anchor")
anchor_panel = panel("anchor", anchor_state, anchor_equity, anchor_returns)
display(anchor_panel.to_frame().T)
```

Usage pattern for a sweep, which NB04 to NB10 all follow:

```python
rows = [anchor_panel]
for value in (0.10, 0.125, 0.15, 0.175, 0.20):
    s, e, r = run_variant(f"target_vol_{value}", target_portfolio_vol=value)
    rows.append(panel(f"target_vol_{value}", s, e, r, daily(anchor_returns)))
sweep_df = pd.DataFrame(rows).set_index("label")
sweep_df["passes"] = [passes_constraints(row, anchor_panel) for _, row in sweep_df.iterrows()]
display(sweep_df)

# Nominate one winner by the ranking metric, then the leave-one-vault-out re-simulation.
winner = sweep_df[sweep_df["passes"]]["martin"].idxmax()
worst_vault = largest_contributing_vault(anchor_state)
s, e, r = run_variant(f"{winner}_without_top_vault", masked={worst_vault}, **winner_overrides)
```

## Experiment track

Each notebook changes one mechanism, re-runs the anchor on the development window, reports the
constraints, ranking metric and robustness panel, and states its verdict in its heading.
Measurement gates the backtests; structural levers that do not depend on selection quality come
before score changes; capacity realism comes before breadth.

### NB03a - measurement: data quality, attribution and power

No strategy change. Four parts.

1. **Staleness flags.** For every vault-day in the development window, a fresh-observation flag
   from zero-return runs. Report the fresh share by month and by vault, and confirm the 2026-04
   regime break on this track's freshly downloaded data.
2. **Availability audit.** For each feature used anywhere in this plan, compare the framework
   indicator value at decision cycle T against what the raw poll data contained by T.
3. **Baseline attribution by vault beta.** For every position in the anchor run, the vault's 90d
   BTC beta at entry, with P&L, drawdown contribution and days held in three buckets.
4. **Power calculation.** The minimum detectable Sharpe and Martin-ratio difference on the
   development window, daily and weekly.

**Implementation.** Add these indicators to cell 10. `btc_beta` is reused by NB03b, NB07, NB08 and
NB10, so it is defined once here. Add `beta_window_days = 90` and `fresh_window_days = 90` to
`Parameters`. Call `fetch_binance_price()` once in the notebook before the indicator calculation so
the DuckDB cache is warm before worker processes read it; if the workers still contend for the
cache file, pass `max_workers=1` to `calculate_and_load_indicators_inline`.

```python
from tradingstrategy.binance.price import fetch_binance_price


def _btc_daily_returns_for(index: pd.DatetimeIndex) -> pd.Series:
    btc = fetch_binance_price()["close"]
    btc.index = pd.to_datetime(btc.index)
    if btc.index.tz is not None:
        btc.index = btc.index.tz_localize(None)
    return btc.pct_change().reindex(index).fillna(0.0)


@indicators.define()
def fresh_observation_count(close: pd.Series, fresh_window_days: int = 90) -> pd.Series:
    """Number of days in the trailing window on which the mark actually moved.

    NB57: a zero daily return on a Hyperliquid vault is almost always a stale poll, not a flat
    day. Any statistic that needs a distribution (downside deviation, ulcer, event concentration)
    is only trusted once this count clears ``Parameters.min_fresh_observations``.
    """
    moved = (close.pct_change().abs() > 0).astype(float)
    return moved.rolling(int(fresh_window_days), min_periods=1).sum()


@indicators.define()
def btc_beta(close: pd.Series, beta_window_days: int = 90) -> pd.Series:
    """Rolling OLS beta of the vault's daily return on BTC's daily return."""
    w = int(beta_window_days)
    r = close.pct_change()
    b = _btc_daily_returns_for(r.index)
    cov = r.rolling(w, min_periods=w).cov(b)
    var = b.rolling(w, min_periods=w).var()
    return cov / var.replace(0.0, float("nan"))


@indicators.define()
def btc_beta_r2(close: pd.Series, beta_window_days: int = 90) -> pd.Series:
    """R-squared of the same regression, so a beta of 1.0 on noise is not mistaken for exposure."""
    w = int(beta_window_days)
    r = close.pct_change()
    b = _btc_daily_returns_for(r.index)
    return r.rolling(w, min_periods=w).corr(b) ** 2
```

Staleness by month (part 1), using the raw universe candles rather than an indicator so it can be
compared to NB57's table directly:

```python
candles = strategy_universe.data_universe.candles.df["close"]   # index: (pair_id, timestamp)
daily_close = candles.groupby(level="pair_id").apply(lambda s: s.droplevel("pair_id").resample("1D").last())
zero_share = (daily_close.groupby(level="pair_id").pct_change() == 0).groupby(
    lambda idx: pd.Timestamp(idx[1]).to_period("M")
).mean()
display(zero_share.to_frame("share_of_zero_return_vault_days"))
```

Attribution by beta bucket (part 3):

```python
rows = []
for position in anchor_state.portfolio.get_all_positions():
    if position.is_credit_supply():
        continue
    buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
    if not buys:
        continue
    entry_at = min(t.executed_at for t in buys)
    beta_series = indicator_data.get_indicator_series("btc_beta", pair=position.pair, unlimited=True)
    rows.append({
        "vault": position.pair.base.token_symbol,
        "entry_beta": float(beta_series.asof(pd.Timestamp(entry_at))),
        "pnl_usd": float(position.get_total_profit_usd() or 0.0),
        "days_held": ((position.closed_at or pd.Timestamp(DEV_END)) - position.opened_at).days,
    })
attribution = pd.DataFrame(rows)
attribution["bucket"] = pd.cut(attribution["entry_beta"].abs(), [-1, 0.2, 0.6, 99], labels=["<0.2", "0.2-0.6", ">0.6"])
display(attribution.groupby("bucket").agg(positions=("vault", "count"), pnl=("pnl_usd", "sum"), mean_days=("days_held", "mean")))
```

Minimum detectable effect (part 4): the half-width of the block-bootstrap CI on the anchor's own
daily returns is the smallest mean daily difference a variant could be distinguished by.

```python
rd = daily(anchor_returns)
lo, hi = block_bootstrap_ci(rd - rd.mean())
half_width_bps = (hi - lo) / 2 * 1e4
mde_sharpe = (half_width_bps / 1e4) / rd.std() * np.sqrt(365)
print(f"Detectable mean daily difference: {half_width_bps:.2f} bps, i.e. a Sharpe difference of about {mde_sharpe:.2f}")
```

### NB03b - decision-aligned feature screen, descriptive only

No strategy change. Precision-at-6 (NB47 method) on the tradable pool, using fresh observations
only, reported in both polling regimes. The screen orders features and gates the selection
notebooks; it is **not** evidence that a feature works, because a 30-day forward window gives
about eight non-overlapping observations here.

**Implementation.** The candidate features are indicators, so every one is computed on the
live-parity path. Add to cell 10, alongside the NB03a indicators:

```python
@indicators.define()
def ulcer_index_180(close: pd.Series, ulcer_window_days: int = 180) -> pd.Series:
    """Root-mean-square drawdown from the trailing-window high. Penalises time under water."""
    w = int(ulcer_window_days)
    drawdown = close / close.rolling(w, min_periods=w).max() - 1.0
    return (drawdown ** 2).rolling(w, min_periods=w).mean() ** 0.5


@indicators.define()
def downside_deviation_90(close: pd.Series, downside_window_days: int = 90) -> pd.Series:
    r = close.pct_change()
    w = int(downside_window_days)
    return ((r.clip(upper=0.0) ** 2).rolling(w, min_periods=w).mean()) ** 0.5


@indicators.define()
def positive_window_share(close: pd.Series, consistency_window_days: int = 30, consistency_span_days: int = 180) -> pd.Series:
    """Share of trailing rolling 30-day returns that were positive. The reader's definition of steady."""
    rolling_return = close / close.shift(int(consistency_window_days)) - 1.0
    return (rolling_return > 0).astype(float).rolling(int(consistency_span_days), min_periods=int(consistency_span_days)).mean()


@indicators.define()
def residual_event_concentration(
    close: pd.Series,
    event_window_days: int = 180,
    beta_window_days: int = 90,
    min_fresh_observations: int = 60,
) -> pd.Series:
    """Share of the trailing window's positive residual log return delivered by its best 5 days.

    Residual means after removing ``beta * r_btc``, so a vault that is simply levered BTC does not
    look concentrated merely because BTC had a good week. The denominator is the sum of *positive*
    residual days, which keeps the ratio in ``[0, 1]`` and defined even when the total return is
    negative. NaN until ``min_fresh_observations`` marks have actually moved.
    """
    w = int(event_window_days)
    r = close.pct_change()
    b = _btc_daily_returns_for(r.index)
    beta = r.rolling(int(beta_window_days), min_periods=int(beta_window_days)).cov(b) / b.rolling(int(beta_window_days), min_periods=int(beta_window_days)).var().replace(0.0, float("nan"))
    residual = np.log1p((r - beta * b).clip(lower=-0.99))
    positive = residual.clip(lower=0.0)
    top5 = residual.rolling(w, min_periods=w).apply(lambda x: np.sort(x)[-5:].sum(), raw=True)
    concentration = top5 / positive.rolling(w, min_periods=w).sum().replace(0.0, float("nan"))
    fresh = (r.abs() > 0).astype(float).rolling(w, min_periods=1).sum()
    return concentration.where(fresh >= int(min_fresh_observations))


@indicators.define()
def min_window_sortino(close: pd.Series) -> pd.Series:
    """Minimum of the bounded Sortino score across 30, 90, 180 and 360 days.

    Strict: NaN if *any* window lacks history, so a young vault is unscored rather than scored on
    the windows it has. That is the NB78 NaN-tolerant failure this must not repeat.
    """
    legs = []
    for w in (30, 90, 180, 360):
        r = close.pct_change()
        mean = r.rolling(w, min_periods=w).mean()
        downside = ((r.clip(upper=0.0) ** 2).rolling(w, min_periods=w).mean()) ** 0.5
        sortino = (mean / downside.replace(0.0, float("nan"))) * (TRADING_DAYS_PER_YEAR ** 0.5)
        legs.append((sortino / SHARPE_SCORE_CAP).clip(lower=0.0, upper=1.0))
    return pd.concat(legs, axis=1).min(axis=1, skipna=False)


@indicators.define()
def residual_cagr_score(close: pd.Series, cagr_lookback_days: int = 360, beta_window_days: int = 90) -> pd.Series:
    """``cagr_score`` computed on a BTC-residual NAV index instead of the raw share price."""
    r = close.pct_change().fillna(0.0)
    b = _btc_daily_returns_for(r.index)
    w = int(beta_window_days)
    beta = (r.rolling(w, min_periods=w).cov(b) / b.rolling(w, min_periods=w).var().replace(0.0, float("nan"))).fillna(0.0)
    residual_nav = (1.0 + (r - beta * b).clip(lower=-0.99)).cumprod()
    lookback = int(cagr_lookback_days)
    cagr = (residual_nav / residual_nav.shift(lookback)).pow(TRADING_DAYS_PER_YEAR / lookback) - 1.0
    return (cagr / CAGR_SCORE_CAP).clip(lower=0.0, upper=1.0)
```

The screen itself. For each decision date, form the pool `decide_trades` would see, rank by the
feature, and score the top six on the forward 30-day Martin ratio of an equal-weight basket.

```python
GATE = float(Parameters.gate_threshold)
FEATURES = ["cagr_sortino_weight", "btc_beta", "ulcer_index_180", "downside_deviation_90",
            "positive_window_share", "residual_event_concentration", "min_window_sortino", "residual_cagr_score"]
LOWER_IS_BETTER = {"btc_beta", "ulcer_index_180", "downside_deviation_90", "residual_event_concentration"}

candles = strategy_universe.data_universe.candles.df["close"]
inclusion = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)
decision_dates = pd.date_range(DEV_START, DEV_END - pd.Timedelta(days=31), freq="2D")


def forward_martin(pair_ids, start, horizon=30) -> float:
    curves = []
    for pid in pair_ids:
        px = candles.loc[pid].loc[start:start + pd.Timedelta(days=horizon)]
        if len(px) > 5:
            curves.append(px / px.iloc[0])
    if not curves:
        return float("nan")
    basket = pd.concat(curves, axis=1).ffill().mean(axis=1)
    ret = basket.iloc[-1] - 1.0
    return ret / ulcer_index(basket) if ulcer_index(basket) > 0 else float("nan")


rows = []
for when in decision_dates:
    pool = [pid for pid in inclusion.asof(when) or []
            if str(strategy_universe.get_pair_by_id(pid).pool_address).lower() not in MANUAL_BLACKLIST]
    gated = [pid for pid in pool
             if (g := indicator_data.get_indicator_series("return_gate", pair=strategy_universe.get_pair_by_id(pid), unlimited=True).asof(when)) == g and g > GATE]
    for feature in FEATURES:
        values = {}
        for pid in gated:
            pair = strategy_universe.get_pair_by_id(pid)
            v = indicator_data.get_indicator_series(feature, pair=pair, unlimited=True).asof(when)
            fresh = indicator_data.get_indicator_series("fresh_observation_count", pair=pair, unlimited=True).asof(when)
            if v == v and fresh >= Parameters.min_fresh_observations:
                values[pid] = -v if feature in LOWER_IS_BETTER else v
        top6 = sorted(values, key=values.get, reverse=True)[:6]
        rows.append({"date": when, "feature": feature, "regime": "sparse" if when < REGIME_BREAK else "dense",
                     "top6_forward_martin": forward_martin(top6, when)})
screen = pd.DataFrame(rows).groupby(["feature", "regime"])["top6_forward_martin"].mean().unstack()
screen["beats_composite_both"] = (screen > screen.loc["cagr_sortino_weight"]).all(axis=1)
display(screen.sort_values("dense", ascending=False))
```

Gate: a selection feature earns its notebook only if `beats_composite_both` is true. Add
`min_fresh_observations = 60` to `Parameters`. The vault-feed metadata NB57 Stage C identified
(`leader_fraction`, `leader_commission`, `follower_count`, `cumulative_volume`, `account_pnl`) is
read from the vault metadata the universe already loads, joined by pool address, and screened the
same way; it is not an indicator because it does not derive from the price series.

### NB04 - structural: portfolio volatility target with cash as a position

Selection untouched. Scale `allocation_pct` each cycle by `min(1, target_vol / ex_ante_vol)`. Sweep
target annualised vol at 10%, 12.5%, 15%, 17.5%, 20%. Cash sits in the reserve asset. This is the
one lever that removes the overflow-into-pumpers mechanism without touching the ranking, and it is
the cash option every later change needs to avoid NB79's substitution failure. The time-in-market
constraint applies; a target that wins only by sitting out is a cash-overlay result.

**Implementation.** Add `target_portfolio_vol = None` to `Parameters` (None means off, so the anchor
is unchanged). In `decide_trades`, replace the single line
`portfolio_target_value = calculate_portfolio_target_value(position_manager, parameters.allocation_pct)`
with:

```python
allocation_pct = float(parameters.allocation_pct)
target_vol = getattr(parameters, "target_portfolio_vol", None)
vol_scale = 1.0
if target_vol:
    # Conservative ex-ante estimate: weighted sum of per-vault daily sigma, as if perfectly
    # correlated. inverse_vol is 1/sigma_daily over Parameters.inverse_vol_window (90d).
    total_weight = sum(weight_by_id.values()) or 1.0
    ex_ante_daily = sum(
        (weight_by_id[pid] / total_weight) * (1.0 / inv_vol_by_id[pid])
        for pid in weight_by_id
        if inv_vol_by_id.get(pid, 0.0) > 0
    )
    ex_ante_annual = ex_ante_daily * math.sqrt(365.0)
    if ex_ante_annual > 0:
        vol_scale = min(1.0, float(target_vol) / ex_ante_annual)
    allocation_pct *= vol_scale
portfolio_target_value = calculate_portfolio_target_value(position_manager, allocation_pct)
```

Add `Vol scale: {vol_scale:.3f}` and `Effective allocation: {allocation_pct:.3f}` to the report
string so the capital utilisation charts can show when the target bit. Sweep with
`run_variant(name, target_portfolio_vol=value)`.

### NB05 - structural: capacity realism before anything else grows

Selection untouched. `per_position_cap_of_pool_pct` swept from the baseline 0.33 down through
0.15, 0.10, 0.05. NB84 found the chain's largest wins came from positions of 38% of a vault's TVL
and recommended low single digits. The winner here becomes the fixed cap for every later notebook,
and the anchor for NB06 onwards is re-run under it. Expect CAGR to fall; the point is that any
smoothing measured on top of an unrealistic cap is not worth having.

**Implementation.** No code change. `USDTVLSizeRiskModel(per_position_cap=...)` already reads the
parameter. The sweep is:

```python
rows = [anchor_panel]
for cap in (0.33, 0.15, 0.10, 0.05):
    s, e, r = run_variant(f"pool_cap_{cap}", per_position_cap_of_pool_pct=cap)
    rows.append(panel(f"pool_cap_{cap}", s, e, r, daily(anchor_returns)))
```

Report alongside the panel, from the per-cycle messages, the mean `Discarded allocation because of
lack of lit liquidity` and the count of `capped_by_pool_size` flags, so the reader sees what the cap
refused. The chosen cap is written into `Parameters` of every later notebook, and its heading
says so.

### NB06 - structural: breadth, then concentration

Selection untouched, capacity cap from NB05. Two sequential sweeps rather than a grid:

1. `max_assets_in_portfolio` at 6, 8, 10 with `max_concentration_pct` held at 0.33.
2. `max_concentration_pct` at 0.20, 0.25, 0.33 at the breadth chosen in step 1.

NB68 found 7 to be a reproducible hole at 150,000, so step 1 must show a plateau.

**Implementation.** No code change; both are `Parameters` attributes read by
`alpha_model.normalise_weights(max_weight=..., max_positions=...)` and by the candidate loop.

```python
step1 = [panel(f"assets_{n}", *run_variant(f"assets_{n}", max_assets_in_portfolio=n), daily(anchor_returns)) for n in (6, 8, 10)]
best_n = ...  # the passing configuration with the highest martin, or 6 if none pass
step2 = [panel(f"conc_{c}", *run_variant(f"conc_{c}", max_assets_in_portfolio=best_n, max_concentration_pct=c), daily(anchor_returns)) for c in (0.20, 0.25, 0.33)]
```

### NB07 - sizing: drawdown-based risk, one family at a time

Selection untouched. Each family runs with a minimum fresh-observation count before a vault can be
sized on the measure, a weight floor so that a vault with no reported down days cannot receive an
unbounded weight, and the concentration cap as a true maximum (already enforced by
`normalise_weights(max_weight=...)`). NB77 showed inverse variance hands the largest weights to a
quiet cohort of small losers; the floors exist because ulcer and downside deviation have the same
stale-mark vulnerability.

1. `inverse_ulcer`
2. `inverse_downside`
3. A beta-group cap: the vaults with `|btc_beta| > 0.6` may together hold at most
   `high_beta_group_cap` of the basket. This is the practical form of a risk-contribution cap; it
   stops two vaults that are the same BTC trade from both filling the basket.

**Implementation.** Add to `Parameters`: `sizing_risk_indicator = "inverse_vol"`,
`min_fresh_observations = 60`, `weight_floor_fraction = 0.25`, `high_beta_group_cap = None`,
`beta_high_threshold = 0.6`. The `ulcer_index_180`, `downside_deviation_90`, `btc_beta` and
`fresh_observation_count` indicators come from NB03a and NB03b.

In the candidate loop of `decide_trades`, next to the existing `inv_vol` read, collect the extra
statistics:

```python
risk_by_id = {}
fresh_by_id = {}
beta_by_id = {}
...
        # inside the for-loop over included_pairs, after inv_vol_by_id[pair_id] is set:
        risk_name = str(getattr(parameters, "sizing_risk_indicator", "inverse_vol"))
        if risk_name != "inverse_vol":
            risk = indicators.get_indicator_value(risk_name, pair=pair)
            risk_by_id[pair_id] = float(risk) if risk is not None and risk == risk else float("nan")
        fresh = indicators.get_indicator_value("fresh_observation_count", pair=pair)
        fresh_by_id[pair_id] = float(fresh) if fresh is not None and fresh == fresh else 0.0
        beta = indicators.get_indicator_value("btc_beta", pair=pair)
        beta_by_id[pair_id] = float(beta) if beta is not None and beta == beta else 0.0
```

Extend `compute_sizing_weights` with the two new methods, the fresh-observation fallback and the
floor. The signature gains `risk_by_id`, `fresh_by_id`, `min_fresh` and `floor_fraction`:

```python
RISK_FLOOR = 1e-4

    # new branches inside compute_sizing_weights, before `raise ValueError`
    if method in ("inverse_ulcer", "inverse_downside"):
        weights = {}
        for pair_id in selected_pair_ids:
            risk = risk_by_id.get(pair_id, float("nan"))
            if fresh_by_id.get(pair_id, 0.0) < min_fresh or risk != risk:
                weights[pair_id] = None            # not enough moved marks to trust the measure
            else:
                weights[pair_id] = 1.0 / max(risk, RISK_FLOOR)
        trusted = [w for w in weights.values() if w is not None]
        fallback = float(np.median(trusted)) if trusted else 1.0
        weights = {pid: (w if w is not None else fallback) for pid, w in weights.items()}
        # Weight floor: no vault below floor_fraction of the equal-weight share, so a vault whose
        # measured risk is tiny (often because its marks are stale) cannot swallow the basket.
        mean_weight = sum(weights.values()) / len(weights)
        return {pid: max(w, floor_fraction * mean_weight) for pid, w in weights.items()}
```

The beta-group cap is applied after `compute_sizing_weights` returns and before the alpha model is
built:

```python
group_cap = getattr(parameters, "high_beta_group_cap", None)
if group_cap:
    high = {pid for pid in weight_by_id if abs(beta_by_id.get(pid, 0.0)) > float(parameters.beta_high_threshold)}
    total = sum(weight_by_id.values()) or 1.0
    high_share = sum(weight_by_id[pid] for pid in high) / total
    if high and high_share > float(group_cap):
        shrink = float(group_cap) / high_share
        for pid in high:
            weight_by_id[pid] *= shrink
        # normalise_weights() rescales the remainder, so the freed share flows to low-beta vaults
```

Sweep: `run_variant("ulcer", weighting_method="inverse_ulcer", sizing_risk_indicator="ulcer_index_180")`,
`run_variant("downside", weighting_method="inverse_downside", sizing_risk_indicator="downside_deviation_90")`,
and `run_variant(f"group_cap_{c}", high_beta_group_cap=c)` for `c` in `(0.25, 0.40, 0.50)`. The
NB72 exponent question is re-run as `weighting_method="inverse_power"` with `weighting_exponent` at
1.0 and 2.0 under whichever risk measure wins.

### NB08 - selection: continuous penalty on residual-event concentration

Requires `residual_event_concentration` to pass NB03b. Multiply the composite by
`1 - lambda * clip(concentration, 0, 1)`, sweeping lambda at 0.25, 0.5, 0.75, 1.0, applied only
where the indicator is defined (which already requires 60 fresh observations). A vault whose
positive residual return came entirely from five days scores at most `1 - lambda` of its raw
composite. This is the soft, continuous form of what NB79's vetoes tried to do by exclusion.
NB43's gain-to-pain tilt at 0.15 is the second arm. The random-day-removal null is in the panel for
every arm.

**Implementation.** Add `event_concentration_lambda = 0.0` and `gain_to_pain_tilt = 0.0` to
`Parameters`. In the candidate loop, immediately after `signal = float(composite_signal) ...`:

```python
        penalty = float(getattr(parameters, "event_concentration_lambda", 0.0))
        if penalty > 0:
            concentration = indicators.get_indicator_value("residual_event_concentration", pair=pair)
            if concentration is not None and concentration == concentration:
                signal *= 1.0 - penalty * min(max(float(concentration), 0.0), 1.0)
        tilt = float(getattr(parameters, "gain_to_pain_tilt", 0.0))
        if tilt > 0:
            gtp = indicators.get_indicator_value("gain_to_pain_score", pair=pair)
            if gtp is not None and gtp == gtp:
                signal = (1.0 - tilt) * signal + tilt * float(gtp)
```

with the bounded gain-to-pain indicator in cell 10:

```python
@indicators.define()
def gain_to_pain_score(close: pd.Series, gain_to_pain_window_days: int = 180) -> pd.Series:
    """Sum of returns over sum of absolute losses, mapped 0..3 to 0..1 like the Sharpe score."""
    r = close.pct_change()
    w = int(gain_to_pain_window_days)
    gains = r.rolling(w, min_periods=w).sum()
    pain = r.clip(upper=0.0).abs().rolling(w, min_periods=w).sum()
    return ((gains / pain.replace(0.0, float("nan"))) / SHARPE_SCORE_CAP).clip(lower=0.0, upper=1.0)
```

Sweep: `run_variant(f"lambda_{v}", event_concentration_lambda=v)` and
`run_variant("gtp_tilt", gain_to_pain_tilt=0.15)`.

### NB09 - selection: minimum-across-windows consistency

Requires `min_window_sortino` to pass NB03b. Score by the minimum of window Sortino over 30, 90,
180 and 360 days, blended with the CAGR leg at the incumbent `cagr_weight`. **Every candidate must
have the full 360 days of history**; vaults without it are excluded from this experiment rather than
scored on the windows they have. Young-vault handling is out of scope here.

**Implementation.** Add the composite to cell 10:

```python
@indicators.define(
    dependencies=(cagr_score, min_window_sortino),
    source=IndicatorSource.dependencies_only_per_pair,
)
def cagr_min_sortino_weight(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    cagr_lookback_days: int = 360,
    cagr_weight: float = 0.6,
) -> pd.Series:
    cagr_component = dependency_resolver.get_indicator_data("cagr_score", pair=pair, parameters={"cagr_lookback_days": cagr_lookback_days})
    consistency = dependency_resolver.get_indicator_data("min_window_sortino", pair=pair)
    return cagr_weight * cagr_component + (1.0 - cagr_weight) * consistency
```

Add `require_scored_candidates = False` to `Parameters`. In the candidate loop, replace the line
that turns a NaN composite into `0.0` with:

```python
        if composite_signal is None or composite_signal != composite_signal:
            if getattr(parameters, "require_scored_candidates", False):
                continue      # strict: an unscored vault is not a candidate at all
            signal = 0.0
        else:
            signal = float(composite_signal)
```

Run: `run_variant("min_sortino", selection_score_indicator="cagr_min_sortino_weight", require_scored_candidates=True)`,
and the same with `require_scored_candidates=False` as the diagnostic that shows what admitting
unscored vaults does. The variant that counts windows in the top quartile is a second indicator of
the same shape and is only built if the first passes.

### NB10 - conditional: BTC-residual CAGR leg

Runs **only** if `residual_cagr_score` clears the NB03b gate in both regimes. NB47 gated it out at
0.33% against 0.70%, and a changed objective does not on its own reverse that. If it runs: replace the
raw CAGR leg of `cagr_sortino_weight` with the residual one; the Sortino leg and the momentum gate
stay on raw returns because exits must respond to real NAV drops. Variants: full beta, and beta shrunk
50% toward zero.

**Implementation.** The composite in cell 10, reusing NB03b's `residual_cagr_score`:

```python
@indicators.define(
    dependencies=(residual_cagr_score, sortino_score),
    source=IndicatorSource.dependencies_only_per_pair,
)
def residual_cagr_sortino_weight(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    cagr_lookback_days: int = 360,
    sharpe_lookback_days: int = 45,
    cagr_weight: float = 0.6,
    beta_window_days: int = 90,
) -> pd.Series:
    residual = dependency_resolver.get_indicator_data("residual_cagr_score", pair=pair, parameters={"cagr_lookback_days": cagr_lookback_days, "beta_window_days": beta_window_days})
    sortino = dependency_resolver.get_indicator_data("sortino_score", pair=pair, parameters={"sharpe_lookback_days": sharpe_lookback_days})
    return cagr_weight * residual + (1.0 - cagr_weight) * sortino
```

For the shrunk-beta control, add `beta_shrink = 1.0` to `Parameters`, pass it through
`residual_cagr_score` as an argument, and multiply `beta` by it inside that function. Run:
`run_variant("residual", selection_score_indicator="residual_cagr_sortino_weight")` and
`run_variant("residual_shrunk", selection_score_indicator="residual_cagr_sortino_weight", beta_shrink=0.5)`.

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

**Implementation.** The combination is a dict of overrides assembled from the winners; the hold-out
is the same `run_variant` with the window moved. The hold-out cell must be the only place in the
track that sets these dates.

```python
FROZEN = {**nb04_winner_overrides, **nb07_winner_overrides, ...}   # Adopt winners only

# Development, for the record.
dev_state, dev_equity, dev_returns = run_variant("frozen_dev", **FROZEN)

# Hold-out, run once. The anchor is run on the same window for the paired comparison.
holdout = dict(backtest_start=HOLDOUT_START.to_pydatetime(), backtest_end=HOLDOUT_END.to_pydatetime())
ho_anchor = run_variant("anchor_holdout", **holdout)
ho_frozen = run_variant("frozen_holdout", **FROZEN, **holdout)
display(pd.DataFrame([
    panel("anchor_holdout", *ho_anchor),
    panel("frozen_holdout", *ho_frozen, daily(ho_anchor[2])),
]).set_index("label"))
```

`required_history_period` in `Parameters` already extends data loading backwards, so a hold-out
start of 2026-07-01 still sees the full indicator history.

## Controls in every backtest notebook

- Anchor re-run in the notebook on the development window, reproduced to the dollar before any
  variant is run.
- Both polling regimes and both daily and weekly returns reported for every figure. The `panel()`
  helper does this.
- Random-day-removal null alongside the best-5-day removal, via `luck_ratio()`.
- Vol-matched placebo for any selection change, dropping the same per-cycle count by highest
  volatility. If the placebo matches the variant, the variant is a de-risking effect and is reported
  as such, which under this objective is still admissible.
- Leave-one-vault-out by full re-simulation, via `run_variant(masked={...})`.
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
- **Draft 2** reserves the hold-out up front, adds NB03a, splits the screen into NB03b, moves
  capacity ahead of breadth, rewrites the adoption rule as constraints plus a ranking metric, makes
  the residual-CAGR leg conditional, redefines the event-concentration statistic on residual log
  returns with a fresh-observation requirement, requires identical windows in NB09, replaces the
  sizing multiplier with floors and a true maximum, and demotes the live-book comparison to a case
  study behind a prospective shadow gate.
- **Draft 3** (this file) adds the hook map, the shared harness and an implementation block for
  every notebook, written against the actual `indicators` registry, `compute_sizing_weights()` and
  `decide_trades()` in the baseline so the notebooks can be built by another agent without
  re-deriving the design. The `MASKED_VAULTS` machinery already in the baseline is used as the
  leave-one-vault-out mechanism rather than adding a new one.
