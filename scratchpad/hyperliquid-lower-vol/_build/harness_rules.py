#: Stable-selection harness (28-stable-selection-plan.md, Draft 2), NB28-NB31.
#:
#: Loaded after harness.py, harness_evidence.py and harness_stability.py. It ADDS the nine gates
#: of RESEARCH-RULES.md and the screen machinery, and REDEFINES exactly one name -
#: `run_and_record()` - so that `PREFILTER_LOG` is cleared and snapshotted alongside the older
#: logs. Without that, candidate membership leaks between runs and NB28's screen reads a mixture
#: of two runs' pools.
#:
#: There is no ADOPT in this module. Meeting every gate yields SHORTLIST: admission to a
#: prospective shadow specification, to be judged on data that does not exist yet. The screen
#: chooses signals using 30-day forward returns and the backtest then judges portfolios built
#: from those signals on returns that overlap the same windows; procedural ordering does not make
#: that out-of-sample, and on 126 decisions with a minimum detectable Sharpe difference near 2.50
#: no purge or split fixes it.

from scipy.stats import rankdata

# --------------------------------------------------------------------------------------------
# Pre-registered constants. Fixed here, before any run of this plan.
# --------------------------------------------------------------------------------------------

#: Gate 5's non-inferiority margin for the return clause, in ANNUALISED PERCENTAGE POINTS.
#:
#: A signal may pick vaults earning up to this much less per year, provided it demonstrably picks
#: more stable ones. `delta = 0` demands the stable set be no worse in return, which given NB09's
#: and NB16's results would reject almost everything; a large `delta` makes the clause vacuous.
#: At 5 points the clause would have rejected NB09's consistency legs (15.0%, 24.3% and 9.2% CAGR
#: against the anchor's 37.9%) on MAGNITUDE rather than on noise, which is the failure mode the
#: review objected to: "the interval does not exclude zero" is a failure to reject, not a
#: guarantee, and a materially negative but noisy association passes it.
DELTA_ANNUALISED_PP = 5.0

#: Forward-target horizon, in calendar days. Common to every target so that no target is
#: frequency-dependent and a densely polled vault is not compared against a sparse one on a
#: different clock.
FORWARD_HORIZON_DAYS = 30
#: Fewest usable decision dates before a signal-target pair is evaluated at all.
SCREEN_MIN_DATES = 40
#: Fewest usable candidates on a date before that date contributes a per-date correlation.
SCREEN_MIN_CANDIDATES = 8
#: Fewest positive residual events in a forward window before the forward event-concentration
#: target exists. Below this the ratio degenerates towards exactly 1.0.
MIN_POSITIVE_EVENTS = 8
#: The exclusion fraction the tail-aligned contrast is evaluated at. This is the mechanism NB29
#: centres on, so the screen's tail diagnostic and the backtest's centre agree.
TAIL_FRACTION = 0.30

#: Circular moving-block length over the decision schedule, in decisions. At a 2-day cycle 15
#: decisions is a month, which is long relative to the autocorrelation of these vaults' returns
#: and short enough to leave the block count above 7.
SCREEN_DATE_BLOCK = 15
SCREEN_DRAWS = 500
SCREEN_SEED = 20260914

#: Gate 2's Sharpe-retention bar under leave-one-vault-out. Pre-registered in RESEARCH-RULES.md
#: and calibrated on Sharpe, not CAGR: measured, the anchor retains 1.781367/2.159792 = 0.825,
#: NB26's `measured_8` retains 2.040695/2.373768 = 0.860, and the `drop_30` spike retains
#: 1.889823/2.747391 = 0.688. The bar sits above the spike and below both legitimate cases.
LOVO_RETENTION_BAR = 0.70
#: Gate 6's plateau flatness tolerance, on cycle Sharpe.
PLATEAU_TOLERANCE = 0.25
#: Gate 3's limit on the share of a date's held weight that may carry no indicator value before
#: that date is dropped from the capital-weighted mean entirely.
HELD_BOOK_MAX_DROPPED_WEIGHT = 0.25
#: Gate 9's minimum number of DISTINCT null draws, measured on realised cycle-return series.
NULL_MIN_DISTINCT = 10

#: The operator indifference band from RESEARCH-RULES.md. A DECISION POLICY, not a statistical
#: resolution claim: this window's minimum detectable Sharpe difference is about 2.50, which says
#: the sample is poorly powered for differences far larger than 0.25 and does not identify 0.25
#: as a boundary between signal and noise.
INDIFFERENCE_BAND = 0.25

#: The thirteen screened signals. `direction` is 'low' when a SMALLER value means a LESS stable
#: vault. `time_base` is stated because the signals are deliberately NOT harmonised: each keeps
#: its exact cached definition, and only the forward targets use the new fresh-return
#: construction. Harmonising them would have changed what NB03b-NB26 measured.
SIGNALS = [
    {"name": "inverse_vol", "direction": "low", "time_base": "90 calendar rows", "note": "the sizing rule's own premise; NB26's measured_only drop"},
    {"name": "downside_deviation_90", "direction": "high", "time_base": "90 calendar rows", "note": ""},
    {"name": "ulcer_index_180", "direction": "high", "time_base": "180 calendar rows", "note": ""},
    {"name": "drawdown_recovery_days", "direction": "high", "time_base": "180 calendar rows", "note": ""},
    {"name": "residual_event_concentration", "direction": "high", "time_base": "180 calendar rows", "note": "calendar clock"},
    {"name": "fresh_event_concentration", "direction": "high", "time_base": "90 fresh events", "note": "event clock"},
    {"name": "positive_window_share", "direction": "low", "time_base": "30/180 calendar rows", "note": ""},
    {"name": "gain_to_pain_score", "direction": "low", "time_base": "180 calendar rows", "note": "gains/pain mapped to 0..1, so HIGH is better - Draft 2 of the plan declared this backwards"},
    {"name": "min_window_sortino", "direction": "low", "time_base": "30-360 calendar rows", "note": "strict; NaN unless every window has history"},
    {"name": "sortino_score", "direction": "low", "time_base": "45 calendar rows", "note": ""},
    {"name": "sortino_shrunk_score", "direction": "low", "time_base": "90 fresh events", "note": ""},
    {"name": "btc_beta", "direction": "high", "time_base": "90 calendar rows", "note": "absolute value taken"},
    {"name": "fresh_observation_count", "direction": "low", "time_base": "90 calendar rows", "note": "CONTROL - the staleness proxy, expected to fail on the tradable pool"},
]
SIGNAL_NAMES = [s["name"] for s in SIGNALS]
SIGNAL_DIRECTION = {s["name"]: s["direction"] for s in SIGNALS}
#: Signals read as an absolute value, because their sign is not what stability means.
SIGNAL_ABSOLUTE = {"btc_beta"}

#: The three forward stability targets gate 5 names, plus the return target its non-inferiority
#: clause uses. Max drawdown is DIAGNOSTIC only and is not a gate target.
STABILITY_TARGETS = ["forward_vol", "forward_downside", "forward_event_top5"]
RETURN_TARGET = "forward_return"
DIAGNOSTIC_TARGETS = ["forward_max_dd"]
SCREEN_TARGETS = STABILITY_TARGETS + [RETURN_TARGET]


# --------------------------------------------------------------------------------------------
# Offline indicator access.
#
# Gate 3 and the screen both need a candidate's cached indicator value at T-1, outside
# `decide_trades`. `run_variant()` builds its indicator set internally and discards it, so this
# computes the ANCHOR-parameter set once and reads series from it. Every signal used here is
# parameter-independent of the prefilter, so one cached set serves every run; NB28 asserts that
# by reproducing the logged in-trade values exactly.
# --------------------------------------------------------------------------------------------

rules_indicators = calculate_and_load_indicators_inline(
    strategy_universe=strategy_universe,
    create_indicators=indicators.create_indicators,
    parameters=StrategyParameters.from_class(Parameters),
    max_workers=1,
)

_SERIES_CACHE: dict = {}


def indicator_series(name: str, pair) -> pd.Series | None:
    """Whole cached series for one indicator and pair, future included. Never read at T."""
    key = (name, pair.internal_id)
    if key not in _SERIES_CACHE:
        try:
            series = rules_indicators.get_indicator_series(name, pair=pair, unlimited=True)
        except Exception:
            series = None
        _SERIES_CACHE[key] = None if series is None else series.astype(float)
    return _SERIES_CACHE[key]


def close_series(pair) -> pd.Series:
    key = ("__close__", pair.internal_id)
    if key not in _SERIES_CACHE:
        _SERIES_CACHE[key] = rules_indicators.get_price_series(pair=pair).astype(float).dropna()
    return _SERIES_CACHE[key]


def value_at_prior(series: pd.Series | None, timestamp) -> float:
    """The last value STRICTLY before `timestamp`, mirroring `get_indicator_value(index=-1)`.

    `decide_trades` reads bar T-1 by design. A diagnostic that reads bar T and is compared
    against a trading result is not measuring the same thing, which is the leakage this whole
    track has been caught by before.
    """
    if series is None or not len(series):
        return float("nan")
    position = series.index.searchsorted(pd.Timestamp(timestamp), side="left")
    if position == 0:
        return float("nan")
    value = float(series.iloc[position - 1])
    return value if np.isfinite(value) else float("nan")


# --------------------------------------------------------------------------------------------
# Run bookkeeping, extended for PREFILTER_LOG.
# --------------------------------------------------------------------------------------------

def run_and_record(label: str, family: str, **overrides) -> dict:
    """`harness_stability.run_and_record()` plus the prefilter log.

    Redefined rather than edited: NB20-NB26 are committed with executed outputs that embed
    harness_stability.py verbatim, so that module cannot change. The only behavioural difference
    is that `PREFILTER_LOG` is cleared before the run and snapshotted after it, exactly as the
    three older logs already were. Without this the log accumulates across runs and NB28 reads a
    candidate pool that is the union of two different configurations.
    """
    assert label not in run_by_label, f"duplicate run label {label!r}"
    VOL_DROP_LOG.clear()
    COMPLEMENT_LOG.clear()
    SLEEVE_LOG.clear()
    PREFILTER_LOG.clear()
    state_, equity_, returns_ = run_variant(label, **overrides)
    panel_row = panel(label, state_, equity_, returns_, anchor_cycle_returns)
    entry = {
        "label": label, "family": family, "overrides": dict(overrides),
        "state": state_, "equity": equity_, "returns": returns_, "panel": panel_row,
        "cycle_returns": cycle_returns(equity_)[0],
        "vol_drop_log": dict(VOL_DROP_LOG), "complement_log": dict(COMPLEMENT_LOG),
        "sleeve_log": dict(SLEEVE_LOG), "prefilter_log": dict(PREFILTER_LOG),
    }
    for name in ("vol_drop_log", "complement_log", "sleeve_log", "prefilter_log"):
        keys = list(entry[name])
        assert len(set(keys)) == len(keys), f"{name} has duplicate decision timestamps for {label}"
    runs.append(entry)
    run_by_label[label] = entry
    return entry


def prefilter_overrides(
    signal: str, fraction: float = 0.0, count: int = 0,
    strict: bool = False, seed: int = -1,
) -> dict:
    """Override dict for one prefilter configuration, with the direction taken from `SIGNALS`."""
    assert signal in SIGNAL_DIRECTION, f"{signal!r} is not one of the pre-registered signals"
    return {
        "stability_prefilter_signal": signal,
        "stability_prefilter_direction": SIGNAL_DIRECTION[signal],
        "stability_prefilter_fraction": float(fraction),
        "stability_prefilter_count": int(count),
        "stability_prefilter_strict": bool(strict),
        "stability_prefilter_null_seed": int(seed),
    }


def prefilter_exclusion_frame(entry: dict) -> pd.DataFrame:
    """Per-date counts from one run's prefilter log: measured, NaN, excluded, share, remaining.

    Equal `q` is NOT equal filtering strength across signals - a signal with a higher NaN rate
    filters a smaller share of the whole pool at the same `q`. Comparisons across signals are
    made at matched REALISED exclusion share, which is the `excluded_share` column here, never at
    matched `q`.
    """
    log = entry.get("prefilter_log") or {}
    rows = []
    for timestamp in sorted(log):
        record = log[timestamp]
        rows.append({
            "date": pd.Timestamp(timestamp),
            "signal": record["signal"], "strict": record["strict"], "seed": record["seed"],
            "pool_size": record["pool_size"], "measured": record["measured_count"],
            "nan": record["nan_count"], "excluded": record["excluded_count"],
            "remaining": record["remaining_count"], "excluded_share": record["excluded_share"],
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------
# Forward targets.
# --------------------------------------------------------------------------------------------

def _event_intervals(price: pd.Series, start_value: float):
    """Log returns between consecutive price-CHANGING marks, and their interval endpoints."""
    values, starts, ends = [], [], []
    previous = float(start_value)
    for timestamp, value in price.items():
        value = float(value)
        if not np.isfinite(value) or value == previous or previous <= 0 or value <= 0:
            continue
        values.append(math.log(value / previous))
        ends.append(pd.Timestamp(timestamp))
        previous = value
    return np.asarray(values, dtype=float), ends


def forward_targets_for(pair, timestamp, beta: float) -> dict:
    """Realised forward stability and return of ONE vault over `(T, T + 30 days]`.

    Built from the carried NAV at T, so no event straddles T: the first forward interval runs
    from the value the vault was marked at when the decision was made. Every target carries an
    explicit missing reason rather than a bare NaN.

    :param beta:
        The vault's BTC beta as known at T, from `fresh_event_table`. Applied to forward BTC
        intervals to form residuals. A beta estimated at evaluation time would be a look-ahead.
    """
    out = {name: float("nan") for name in SCREEN_TARGETS + DIAGNOSTIC_TARGETS}
    out["reason"] = ""
    close = close_series(pair)
    if not len(close):
        out["reason"] = "no_price_series"
        return out
    t0 = pd.Timestamp(timestamp)
    t1 = t0 + pd.Timedelta(days=FORWARD_HORIZON_DAYS)
    position = close.index.searchsorted(t0, side="right")
    if position == 0:
        out["reason"] = "no_mark_at_decision"
        return out
    carried = float(close.iloc[position - 1])
    window = close.iloc[position:]
    window = window[window.index <= t1]
    if not len(window) or carried <= 0:
        out["reason"] = "no_forward_marks"
        return out

    returns, ends = _event_intervals(window, carried)
    scale = 365.0 / FORWARD_HORIZON_DAYS
    if len(returns):
        out["forward_vol"] = float(np.sqrt(np.sum(returns ** 2) * scale))
        negative = np.clip(returns, None, 0.0)
        out["forward_downside"] = float(np.sqrt(np.sum(negative ** 2) * scale))
        path = np.concatenate([[0.0], np.cumsum(returns)])
        out["forward_max_dd"] = float(np.min(path - np.maximum.accumulate(path)))
    else:
        out["reason"] = "no_fresh_events"

    terminal = float(window.iloc[-1])
    if terminal > 0:
        out["forward_return"] = float(math.log(terminal / carried))

    # Forward event concentration, on residuals against the beta known at T.
    if not len(returns):
        pass
    elif not np.isfinite(beta):
        out["reason"] = (out["reason"] + "; " if out["reason"] else "") + "no_beta"
    else:
        span = pd.date_range(t0 - pd.Timedelta(days=1), t1 + pd.Timedelta(days=1), freq="1D")
        btc_cum = np.log1p(_btc_daily_returns_for(span).clip(lower=-0.99)).cumsum()
        starts = [t0] + ends[:-1]
        btc = (
            btc_cum.reindex(pd.DatetimeIndex(ends), method="ffill").to_numpy()
            - btc_cum.reindex(pd.DatetimeIndex(starts), method="ffill").to_numpy()
        )
        residual = returns - beta * btc
        residual = residual[np.isfinite(residual)]
        positive = residual[residual > 0]
        if len(positive) < MIN_POSITIVE_EVENTS:
            out["reason"] = (out["reason"] + "; " if out["reason"] else "") + "insufficient_positive_events"
        elif positive.sum() <= 0:
            out["reason"] = (out["reason"] + "; " if out["reason"] else "") + "zero_denominator"
        else:
            out["forward_event_top5"] = float(np.sort(positive)[-5:].sum() / positive.sum())

    for name in SCREEN_TARGETS:
        if not np.isfinite(out[name]) and not out["reason"]:
            out["reason"] = "non_finite"
    return out


def causal_beta_at(pair, timestamp) -> float:
    """The vault's event-time BTC beta as known at T: the last beta on an event at or before T."""
    key = ("__events__", pair.internal_id)
    if key not in _SERIES_CACHE:
        _SERIES_CACHE[key] = fresh_event_table(close_series(pair))
    table = _SERIES_CACHE[key]
    if not len(table):
        return float("nan")
    betas = table["beta"].dropna()
    betas = betas[betas.index <= pd.Timestamp(timestamp)]
    return float(betas.iloc[-1]) if len(betas) else float("nan")


def build_screen_panel(entry: dict, verbose: bool = True) -> tuple:
    """The long (date, candidate) panel the whole screen is computed from.

    Candidate membership comes from the logging run's `PREFILTER_LOG` and is never reconstructed,
    because an offline reconstruction cannot mirror `is_good_pair`, the quarantine list,
    `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the momentum gate, strict admission or the tie order.

    Only decisions whose full forward window is inside the archive are eligible; the rest are
    reported and dropped rather than evaluated on a truncated window.

    :return:
        ``(panel, eligibility)`` - the long frame, and a one-row-per-decision frame saying why
        each ineligible decision was dropped.
    """
    log = entry["prefilter_log"]
    assert log, "the logging run recorded no candidate pools; the prefilter splice did not fire"
    logged_ids = {pid for t in log for pid in log[t]["candidate_ids"]}
    last_available = max(
        close_series(strategy_universe.get_pair_by_id(pid)).index[-1] for pid in logged_ids
    )
    horizon = pd.Timedelta(days=FORWARD_HORIZON_DAYS)

    eligibility, rows = [], []
    pair_by_id = {}
    for timestamp in sorted(log):
        t0 = pd.Timestamp(timestamp)
        eligible = (t0 + horizon) <= last_available
        eligibility.append({
            "date": t0, "eligible": eligible, "pool_size": log[timestamp]["pool_size"],
            "reason": "" if eligible else "forward window extends past the archive",
        })
        if not eligible:
            continue
        for pair_id, address in zip(log[timestamp]["candidate_ids"], log[timestamp]["candidate_addresses"]):
            if pair_id not in pair_by_id:
                pair_by_id[pair_id] = strategy_universe.get_pair_by_id(pair_id)
            pair = pair_by_id[pair_id]
            row = {"date": t0, "pair_id": pair_id, "address": address}
            for name in SIGNAL_NAMES:
                value = value_at_prior(indicator_series(name, pair), t0)
                row[name] = abs(value) if name in SIGNAL_ABSOLUTE else value
            row.update(forward_targets_for(pair, t0, causal_beta_at(pair, t0)))
            rows.append(row)

    panel_frame = pd.DataFrame(rows)
    eligibility_frame = pd.DataFrame(eligibility)
    if verbose:
        n_eligible = int(eligibility_frame["eligible"].sum())
        print(f"decisions logged: {len(eligibility_frame)}; eligible on a complete "
              f"{FORWARD_HORIZON_DAYS}-day forward window: {n_eligible}; "
              f"dropped: {len(eligibility_frame) - n_eligible}")
        print(f"archive ends {last_available.date()}; panel rows: {len(panel_frame)}")
    return panel_frame, eligibility_frame


def missing_reason_table(panel_frame: pd.DataFrame) -> pd.DataFrame:
    """Counts per target of finite values and of each recorded missing reason."""
    rows = []
    for name in SCREEN_TARGETS + DIAGNOSTIC_TARGETS:
        finite = int(np.isfinite(panel_frame[name]).sum())
        missing = panel_frame[~np.isfinite(panel_frame[name])]
        reasons = missing["reason"].replace("", "unrecorded").value_counts().to_dict()
        rows.append({"target": name, "finite": finite, "missing": len(missing), **reasons})
    return pd.DataFrame(rows).fillna(0)


# --------------------------------------------------------------------------------------------
# One joint two-way cluster bootstrap, shared by every screened hypothesis.
# --------------------------------------------------------------------------------------------

def _signal_sample(panel_frame: pd.DataFrame, signal: str) -> dict:
    """Complete-case sample for one signal: rows where it AND all four targets are finite.

    A common sample across the four targets, per signal, so the four correlations describe the
    same candidates and the tail contrast is computed on the same rows the correlations are. The
    sample differs BETWEEN signals - `min_window_sortino` is strict and unscored for most of the
    young cohort - so per-signal row and date counts are reported beside every estimate.
    """
    columns = [signal] + SCREEN_TARGETS
    usable = panel_frame[np.isfinite(panel_frame[columns]).all(axis=1)]
    by_date = {}
    for date, group in usable.groupby("date"):
        if len(group) < SCREEN_MIN_CANDIDATES:
            continue
        matrix = group[columns].to_numpy(dtype=float)
        if np.ptp(matrix[:, 0]) == 0:
            continue   # a constant signal has no ranking; fail closed rather than emit 0.0
        by_date[pd.Timestamp(date)] = {
            "vault": group["pair_id"].to_numpy(),
            "matrix": matrix,
        }
    return {"signal": signal, "by_date": by_date, "rows": len(usable), "dates": len(by_date)}


def _statistics_from(matrix: np.ndarray, sign: float) -> np.ndarray:
    """The eight per-date statistics for one signal on one date's candidate matrix.

    Columns of `matrix`: the signal, then `forward_vol`, `forward_downside`,
    `forward_event_top5`, `forward_return`.

    :return:
        ``[3 signed Spearman, return Spearman, 3 normalised-rank tail contrasts,
        annualised-pp return tail contrast]``.
    """
    n = matrix.shape[0]
    ranks = rankdata(matrix, axis=0)
    centred = ranks - ranks.mean(axis=0)
    norms = np.sqrt((centred ** 2).sum(axis=0))
    norms[norms == 0] = np.nan
    correlations = (centred[:, 1:] * centred[:, :1]).sum(axis=0) / (norms[1:] * norms[0])
    # `sign` makes a positive number mean "the signal's stable end had the more stable outcome"
    # for the three stability targets. The return correlation keeps the same orientation, so a
    # positive number there means the stable end also earned more.
    spearman = sign * correlations

    # Tail-aligned contrast at the fraction NB29 centres on. The stable end is the RETAINED set.
    k = int(math.floor(TAIL_FRACTION * n))
    tail = np.full(4, np.nan)
    if k >= 1 and n - k >= 1:
        # `sign * signal_rank` ascending puts the least-stable end first, matching the splice.
        order = np.argsort(sign * -ranks[:, 0], kind="stable")
        excluded, retained = order[:k], order[k:]
        normalised = (ranks - 1.0) / max(n - 1, 1)
        for j in range(3):
            # Lower forward vol/downside/concentration is MORE stable, so retained-minus-excluded
            # is negated to make "positive = the retained set was more stable".
            tail[j] = -(normalised[retained, j + 1].mean() - normalised[excluded, j + 1].mean())
        # The return contrast is on the raw target, annualised and in percentage points, because
        # gate 5's non-inferiority margin is stated in those units.
        tail[3] = (
            matrix[retained, 4].mean() - matrix[excluded, 4].mean()
        ) * (365.0 / FORWARD_HORIZON_DAYS) * 100.0
    return np.concatenate([spearman, tail])


#: Column order of the eight statistics `_statistics_from` returns, per signal.
STAT_NAMES = (
    [f"spearman_{t}" for t in STABILITY_TARGETS] + [f"spearman_{RETURN_TARGET}"]
    + [f"tail_{t}" for t in STABILITY_TARGETS] + [f"tail_{RETURN_TARGET}_pp"]
)


def _mean_over_dates(samples: dict, dates, multiplicity=None) -> np.ndarray:
    """Equal-weight mean over dates of the eight per-date statistics, for every signal.

    The estimand is stated explicitly and is not a pooled correlation: the mean association on a
    TYPICAL decision date, equal weight per date regardless of how many candidates that date
    carried.
    """
    out = np.full((len(SIGNAL_NAMES), len(STAT_NAMES)), np.nan)
    for i, signal in enumerate(SIGNAL_NAMES):
        sample = samples[signal]
        sign = -1.0 if SIGNAL_DIRECTION[signal] == "low" else 1.0
        total = np.zeros(len(STAT_NAMES))
        count = np.zeros(len(STAT_NAMES))
        for date in dates:
            block = sample["by_date"].get(date)
            if block is None:
                continue
            matrix = block["matrix"]
            if multiplicity is not None:
                # Keyed by (signal, date): each signal has its own complete-case row set for a
                # date, so a cache keyed by date alone would hand one signal's repeat counts to
                # another signal's rows - a silent misalignment, not an error.
                cache_key = (signal, date)
                repeats = multiplicity.get(cache_key)
                if repeats is None:
                    repeats = np.array(
                        [multiplicity["counts"].get(v, 0) for v in block["vault"]], dtype=int,
                    )
                    multiplicity[cache_key] = repeats
                if repeats.sum() < SCREEN_MIN_CANDIDATES:
                    continue
                matrix = np.repeat(matrix, repeats, axis=0)
                if np.ptp(matrix[:, 0]) == 0:
                    continue
            values = _statistics_from(matrix, sign)
            finite = np.isfinite(values)
            total[finite] += values[finite]
            count[finite] += 1
        with np.errstate(invalid="ignore"):
            out[i] = np.where(count > 0, total / np.maximum(count, 1), np.nan)
    return out


def joint_cluster_bootstrap(
    panel_frame: pd.DataFrame, draws: int = SCREEN_DRAWS, block: int = SCREEN_DATE_BLOCK,
    seed: int = SCREEN_SEED, verbose: bool = True,
) -> dict:
    """ONE two-way cluster bootstrap whose resamples every screened hypothesis shares.

    Decision dates are resampled in circular moving blocks and vaults are resampled as clusters,
    together, and the whole nonlinear statistic is recomputed on each draw. The same resamples
    are reused across all thirteen signals and all four targets, which is what makes a
    simultaneous max-T interval over them valid: resampling each hypothesis separately would
    destroy the dependence a max-statistic is entirely about, exactly the misspecification the
    previous plan's `family_wise_reality_check()` was found to have.

    Two-way, not one-way, because the panel is dependent in both directions: the same vault
    appears on many dates and the same date carries every vault.

    :return:
        ``{"observed": (13, 8) array, "draws": (draws, 13, 8) array, "samples": ..., "dates": ...}``
    """
    samples = {signal: _signal_sample(panel_frame, signal) for signal in SIGNAL_NAMES}
    dates = sorted(panel_frame["date"].unique())
    dates = [pd.Timestamp(d) for d in dates]
    vaults = sorted(panel_frame["pair_id"].unique())
    observed = _mean_over_dates(samples, dates)

    rng = np.random.default_rng(seed)
    n_dates, n_vaults = len(dates), len(vaults)
    n_blocks = int(math.ceil(n_dates / block))
    replicates = np.full((draws, len(SIGNAL_NAMES), len(STAT_NAMES)), np.nan)
    for draw in range(draws):
        starts = rng.integers(0, n_dates, size=n_blocks)
        index = np.concatenate([(np.arange(s, s + block) % n_dates) for s in starts])[:n_dates]
        drawn_dates = [dates[i] for i in index]
        drawn_vaults = rng.choice(n_vaults, size=n_vaults, replace=True)
        counts = {}
        for v in drawn_vaults:
            counts[vaults[v]] = counts.get(vaults[v], 0) + 1
        multiplicity = {"counts": counts}
        replicates[draw] = _mean_over_dates(samples, drawn_dates, multiplicity)
        if verbose and (draw + 1) % 100 == 0:
            print(f"  bootstrap draw {draw + 1}/{draws}")
    return {
        "observed": observed, "draws": replicates, "samples": samples,
        "dates": dates, "vaults": vaults, "block": block, "seed": seed, "n_draws": draws,
    }


def simultaneous_ci(observed: np.ndarray, replicates: np.ndarray, level: float = 0.95) -> dict:
    """One-sided simultaneous LOWER bounds over a pre-registered family, by studentised max-T.

    `c` is the `level` quantile over draws of `max_h (theta*_h - theta_h) / se_h`, and the bound
    is `theta_h - c * se_h`. Coverage is joint over the whole family, which is what "pass on all
    three targets" needs: three separate 95% intervals do not give a 95% guarantee on their
    conjunction, and reporting the wider of two intervals - the previous draft's rule - is not a
    multiplicity correction at all.

    Unadjusted per-hypothesis bounds are returned alongside, for description only.

    :param observed: shape (H,). :param replicates: shape (draws, H).
    """
    observed = np.asarray(observed, dtype=float)
    replicates = np.asarray(replicates, dtype=float)
    standard_error = np.nanstd(replicates, axis=0, ddof=1)
    safe = np.where(standard_error > 0, standard_error, np.nan)
    studentised = (replicates - observed[None, :]) / safe[None, :]
    per_draw_max = np.nanmax(studentised, axis=1)
    per_draw_max = per_draw_max[np.isfinite(per_draw_max)]
    critical = float(np.percentile(per_draw_max, level * 100.0)) if len(per_draw_max) else float("nan")
    return {
        "observed": observed, "se": standard_error, "critical": critical,
        "lower_simultaneous": observed - critical * standard_error,
        "lower_unadjusted": np.nanpercentile(replicates, (1.0 - level) * 100.0, axis=0),
        "n_draws": int(len(per_draw_max)),
    }


def add_one_p(replicates: np.ndarray, observed: np.ndarray) -> np.ndarray:
    """One-sided add-one bootstrap p-values for `theta <= 0`, per hypothesis."""
    # H0: theta <= 0. The bootstrap null recentres each draw on zero, so the exceedance count
    # is over draws whose CENTRED value reaches the observed estimate.
    centred = replicates - observed[None, :]
    exceed = (centred >= observed[None, :]).sum(axis=0)
    return (1.0 + exceed) / (replicates.shape[0] + 1.0)


def screen_table(bootstrap: dict, delta: float = DELTA_ANNUALISED_PP) -> tuple:
    """The screen's result table and gate-5 verdicts, from one bootstrap's shared resamples.

    Two pre-registered families, each given its own simultaneous control:

    - STABILITY: 13 signals x 3 stability targets = 39 signed Spearman hypotheses.
    - RETURN: 13 signals x 1 tail contrast in annualised percentage points = 13 hypotheses.

    The 39 stability TAIL contrasts are a third family, reported as a DIAGNOSTIC with its own
    control. They test the mechanism (what the excluded tail actually did) where the Spearman
    tests the rule (monotone association across the whole cross-section). Both are wanted; only
    the Spearman family is what gate 5 is written on.
    """
    observed, replicates = bootstrap["observed"], bootstrap["draws"]
    n_signals, n_stats = observed.shape
    index = {name: i for i, name in enumerate(STAT_NAMES)}

    def family(stat_names):
        columns = [index[n] for n in stat_names]
        flat_observed = observed[:, columns].reshape(-1)
        flat_draws = replicates[:, :, columns].reshape(replicates.shape[0], -1)
        result = simultaneous_ci(flat_observed, flat_draws)
        result["p"] = add_one_p(flat_draws, flat_observed)
        for key in ("observed", "se", "lower_simultaneous", "lower_unadjusted", "p"):
            result[key] = np.asarray(result[key]).reshape(n_signals, len(stat_names))
        return result

    stability = family([f"spearman_{t}" for t in STABILITY_TARGETS])
    returns = family([f"tail_{RETURN_TARGET}_pp"])
    tails = family([f"tail_{t}" for t in STABILITY_TARGETS])

    rows = []
    for i, signal in enumerate(SIGNAL_NAMES):
        sample = bootstrap["samples"][signal]
        row = {
            "signal": signal, "direction": SIGNAL_DIRECTION[signal],
            "time_base": next(s["time_base"] for s in SIGNALS if s["name"] == signal),
            "rows": sample["rows"], "dates": sample["dates"],
        }
        for j, target in enumerate(STABILITY_TARGETS):
            row[f"rho_{target}"] = stability["observed"][i, j]
            row[f"lo_{target}"] = stability["lower_simultaneous"][i, j]
            row[f"tail_{target}"] = tails["observed"][i, j]
            row[f"tail_lo_{target}"] = tails["lower_simultaneous"][i, j]
        row["rho_forward_return"] = observed[i, index[f"spearman_{RETURN_TARGET}"]]
        row["return_contrast_pp"] = returns["observed"][i, 0]
        row["return_lo_pp"] = returns["lower_simultaneous"][i, 0]
        enough = sample["dates"] >= SCREEN_MIN_DATES
        stability_ok = bool(
            enough and all(
                np.isfinite(stability["lower_simultaneous"][i, j])
                and stability["lower_simultaneous"][i, j] > 0.0
                for j in range(len(STABILITY_TARGETS))
            )
        )
        return_ok = bool(
            enough and np.isfinite(returns["lower_simultaneous"][i, 0])
            and returns["lower_simultaneous"][i, 0] > -float(delta)
        )
        row["enough_dates"] = enough
        row["stability_clause"] = stability_ok
        row["return_clause"] = return_ok
        row["gate_5"] = bool(stability_ok and return_ok)
        rows.append(row)
    table = pd.DataFrame(rows).set_index("signal")
    detail = {"stability": stability, "returns": returns, "tails": tails, "delta": float(delta)}
    return table, detail


def paired_measure_difference(bootstrap: dict, left: str, right: str) -> pd.DataFrame:
    """Paired difference between two signals' correlations, on the SAME resamples.

    The calendar-versus-fresh question is a difference, not two intervals: two overlapping
    intervals do not establish that the underlying quantities differ, and two disjoint ones on
    dependent estimates overstate how strongly they do. The estimate here is
    `theta_left - theta_right` recomputed on every shared draw, with a percentile interval.
    """
    i, j = SIGNAL_NAMES.index(left), SIGNAL_NAMES.index(right)
    observed, replicates = bootstrap["observed"], bootstrap["draws"]
    rows = []
    for k, name in enumerate(STAT_NAMES):
        difference = replicates[:, i, k] - replicates[:, j, k]
        difference = difference[np.isfinite(difference)]
        rows.append({
            "statistic": name,
            f"{left}": observed[i, k], f"{right}": observed[j, k],
            "difference": observed[i, k] - observed[j, k],
            "ci_lo": float(np.percentile(difference, 2.5)) if len(difference) else np.nan,
            "ci_hi": float(np.percentile(difference, 97.5)) if len(difference) else np.nan,
            "draws": len(difference),
        })
    return pd.DataFrame(rows).set_index("statistic")


def rank_persistence(panel_frame: pd.DataFrame) -> pd.DataFrame:
    """Spearman of each signal against itself one decision later, on the common candidate set.

    A diagnostic, not a filter. A signal that does not persist across two days cannot be
    selecting a durable property, but persistence is not evidence of predictiveness either - the
    staleness control persists almost perfectly and predicts nothing on the tradable pool.
    """
    rows = []
    dates = sorted(panel_frame["date"].unique())
    for signal in SIGNAL_NAMES:
        values = []
        for a, b in zip(dates, dates[1:]):
            left = panel_frame[panel_frame["date"] == a].set_index("pair_id")[signal]
            right = panel_frame[panel_frame["date"] == b].set_index("pair_id")[signal]
            joined = pd.concat([left.rename("a"), right.rename("b")], axis=1).dropna()
            if len(joined) >= SCREEN_MIN_CANDIDATES and joined["a"].nunique() > 1:
                values.append(joined["a"].corr(joined["b"], method="spearman"))
        rows.append({
            "signal": signal, "pairs": len(values),
            "median_persistence": float(np.median(values)) if values else np.nan,
        })
    return pd.DataFrame(rows).set_index("signal")


# --------------------------------------------------------------------------------------------
# Gates 1-9 of RESEARCH-RULES.md.
# --------------------------------------------------------------------------------------------

def _position_weights(state_) -> dict:
    """`{timestamp: [(pair, share of total equity), ...]}` over the realised holdings."""
    equity_at = {}
    for s in state_.stats.portfolio:
        if s.total_equity:
            equity_at[pd.Timestamp(s.calculated_at)] = float(s.total_equity)
    out = {}
    for position_id, series in state_.stats.positions.items():
        position = state_.portfolio.get_position_by_id(position_id)
        if position is None or position.is_credit_supply():
            continue
        for s in series:
            timestamp = pd.Timestamp(s.calculated_at)
            total = equity_at.get(timestamp)
            value = float(s.value or 0.0)
            if not total or value <= 0:
                continue
            out.setdefault(timestamp, []).append((position.pair, value / total))
    return out


def held_book_character(entry: dict) -> dict:
    """Gate 3: capital-weighted own volatility and own event concentration of what was HELD.

    One observation per decision date. Each holding is joined to its T-1 cached indicator value
    for realised volatility (`1 / inverse_vol`) and for `residual_event_concentration`. A holding
    whose indicator is NaN is dropped from that date's weighted mean and the dropped weight share
    is reported; a date where more than `HELD_BOOK_MAX_DROPPED_WEIGHT` of weight is dropped is
    excluded from the mean and counted, because a mean over the quarter of the book that happens
    to be scorable is not a statement about the book.
    """
    weights = _position_weights(entry["state"])
    volatility, concentration, dropped, excluded = [], [], [], 0
    for timestamp in sorted(weights):
        holdings = weights[timestamp]
        total = sum(share for _pair, share in holdings)
        if total <= 0:
            continue
        values_vol, values_conc, weight_vol, weight_conc = 0.0, 0.0, 0.0, 0.0
        for pair, share in holdings:
            inverse = value_at_prior(indicator_series("inverse_vol", pair), timestamp)
            if np.isfinite(inverse) and inverse > 0:
                values_vol += share * (1.0 / inverse)
                weight_vol += share
            value = value_at_prior(indicator_series("residual_event_concentration", pair), timestamp)
            if np.isfinite(value):
                values_conc += share * value
                weight_conc += share
        missing = 1.0 - min(weight_vol, weight_conc) / total
        dropped.append(missing)
        if missing > HELD_BOOK_MAX_DROPPED_WEIGHT:
            excluded += 1
            continue
        if weight_vol > 0:
            volatility.append(values_vol / weight_vol)
        if weight_conc > 0:
            concentration.append(values_conc / weight_conc)
    return {
        "held_vol": float(np.mean(volatility)) if volatility else float("nan"),
        "held_concentration": float(np.mean(concentration)) if concentration else float("nan"),
        "dates_used": len(volatility), "dates_excluded": excluded,
        "mean_dropped_weight": float(np.mean(dropped)) if dropped else float("nan"),
    }


def diversification(entry: dict) -> dict:
    """Gate 8: the five realised diversification measures.

    `top_vault_pnl_share` is address-aggregated total P&L of the largest contributing address
    divided by the sum of POSITIVE address-level total P&L, so a book carried by one winner
    scores near 1.0 whether or not other names lost.
    """
    weights = _position_weights(entry["state"])
    counts, largest, herfindahl = [], [], []
    for timestamp in sorted(weights):
        shares = np.array([share for _pair, share in weights[timestamp]], dtype=float)
        total = shares.sum()
        if total <= 0:
            continue
        normalised = shares / total
        counts.append(len(normalised))
        largest.append(float(normalised.max()))
        herfindahl.append(float((normalised ** 2).sum()))
    by_address = {}
    for position in entry["state"].portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        key = str(position.pair.pool_address).lower()
        by_address[key] = by_address.get(key, 0.0) + float(position.get_total_profit_usd() or 0.0)
    positive = sum(v for v in by_address.values() if v > 0)
    top = max(by_address.values()) if by_address else float("nan")
    return {
        "mean_holdings": float(np.mean(counts)) if counts else float("nan"),
        "mean_largest_weight": float(np.mean(largest)) if largest else float("nan"),
        "mean_herfindahl": float(np.mean(herfindahl)) if herfindahl else float("nan"),
        "distinct_vaults": len(by_address),
        "top_vault_pnl_share": float(top / positive) if positive > 0 else float("nan"),
    }


#: The five gate-8 measures and whether a LARGER value is worse.
DIVERSIFICATION_MEASURES = {
    "mean_holdings": False, "mean_largest_weight": True, "mean_herfindahl": True,
    "distinct_vaults": False, "top_vault_pnl_share": True,
}


def lovo_gate(label: str, verbose: bool = True) -> dict:
    """Gate 2: re-simulate with the largest total-P&L contributor masked, and report retention.

    A full re-simulation, not a subtraction: the vault is unavailable from the first cycle, so
    the strategy substitutes and the counterfactual is a strategy that never held it.
    """
    entry = run_by_label[label]
    masked = largest_contributing_vault(entry["state"])
    lovo_label = f"{label}__lovo"
    if lovo_label in run_by_label:
        lovo = run_by_label[lovo_label]
    else:
        lovo = run_and_record(
            lovo_label, "robustness", masked={masked}, **entry["overrides"],
        )
    base_sharpe = float(entry["panel"]["cycle_sharpe"])
    lovo_sharpe = float(lovo["panel"]["cycle_sharpe"])
    retention = lovo_sharpe / base_sharpe if base_sharpe > 0 else float("nan")
    result = {
        "label": label, "masked": masked, "sharpe": base_sharpe, "lovo_sharpe": lovo_sharpe,
        "lovo_cagr": float(lovo["panel"]["cagr"]),
        "retention": float(retention),
        "passes": bool(
            np.isfinite(retention) and retention >= LOVO_RETENTION_BAR
            and float(lovo["panel"]["cagr"]) > 0
        ),
    }
    if verbose:
        print(f"{label}: masked {masked}, Sharpe {base_sharpe:.6f} -> {lovo_sharpe:.6f} "
              f"(retention {retention:.3f}, bar {LOVO_RETENTION_BAR:.2f}), "
              f"masked CAGR {result['lovo_cagr']:.6f}")
    return result


def plateau_gate(centre: str, neighbours: list) -> dict:
    """Gate 6: a FLATNESS test. A centre standing above its own neighbours is a spike, not a plateau."""
    centre_sharpe = float(run_by_label[centre]["panel"]["cycle_sharpe"])
    rows, ok = [], True
    for label in neighbours:
        if label not in run_by_label:
            rows.append({"neighbour": label, "executed": False, "sharpe": np.nan,
                         "gap": np.nan, "cagr": np.nan, "ok": False})
            ok = False
            continue
        row = run_by_label[label]["panel"]
        gap = abs(centre_sharpe - float(row["cycle_sharpe"]))
        good = bool(float(row["cagr"]) > 0 and gap <= PLATEAU_TOLERANCE)
        ok = ok and good
        rows.append({"neighbour": label, "executed": True, "sharpe": float(row["cycle_sharpe"]),
                     "gap": gap, "cagr": float(row["cagr"]), "ok": good})
    return {"centre": centre, "centre_sharpe": centre_sharpe, "passes": bool(ok and len(neighbours) > 0),
            "detail": pd.DataFrame(rows)}


def null_effectiveness(centre: str, null_labels: list) -> dict:
    """Gate 9: did the null actually destroy anything, and did the centre beat every draw?

    NB26's null was one draw repeated ten times, and the tell - `null_median == null_best` on
    every metric - was printed and missed. Distinctness is therefore asserted on the REALISED
    CYCLE-RETURN SERIES, not on the value map: two different permutations can produce identical
    baskets, and identical baskets produce identical returns, so a count of distinct value maps
    proves nothing about how many effective draws there were.
    """
    def digest(obj) -> str:
        return hashlib.sha256(repr(obj).encode()).hexdigest()[:16]

    maps, excluded, baskets, series = set(), set(), set(), set()
    sharpes = []
    for label in null_labels:
        entry = run_by_label[label]
        log = entry["prefilter_log"]
        maps.add(digest([(str(t), sorted(log[t]["values"].items())) for t in sorted(log)]))
        excluded.add(digest([(str(t), log[t]["excluded_addresses"]) for t in sorted(log)]))
        held = {}
        for position in entry["state"].portfolio.get_all_positions():
            if position.is_credit_supply():
                continue
            held.setdefault(str(position.pair.pool_address).lower(), 0)
            held[str(position.pair.pool_address).lower()] += 1
        baskets.add(digest(sorted(held.items())))
        series.add(digest(np.round(entry["cycle_returns"].to_numpy(), 12).tolist()))
        sharpes.append(float(entry["panel"]["cycle_sharpe"]))
    centre_sharpe = float(run_by_label[centre]["panel"]["cycle_sharpe"])
    distinct_series = len(series)
    return {
        "centre": centre, "centre_sharpe": centre_sharpe, "draws": len(null_labels),
        "distinct_value_maps": len(maps), "distinct_excluded_sets": len(excluded),
        "distinct_baskets": len(baskets), "distinct_cycle_return_series": distinct_series,
        "null_best": float(np.max(sharpes)) if sharpes else float("nan"),
        "null_median": float(np.median(sharpes)) if sharpes else float("nan"),
        "passes": bool(
            distinct_series >= NULL_MIN_DISTINCT and sharpes
            and centre_sharpe > float(np.max(sharpes))
        ),
    }


def inertness(entry: dict, reference: str = "anchor") -> dict:
    """Did the mechanism change anything at all? Reported for every run, gate or no gate.

    A run that changes nothing is reported as inert whatever its metrics say, because an inert
    run's metrics ARE the reference's metrics, and reading them as a result is how a no-op gets
    mistaken for a mechanism.

    Four separate questions, because they can disagree: whether any candidate was excluded at
    all; whether the book actually held different names on a date; how many excluded names the
    reference was holding at that moment (an exclusion that removes a name nobody would have
    selected is arithmetically real and economically nothing); and whether the realised equity
    path differs at all.
    """
    base = run_by_label[reference]
    log = entry.get("prefilter_log") or {}
    base_by_date = {
        timestamp: {str(pair.pool_address).lower() for pair, _share in holdings}
        for timestamp, holdings in _position_weights(base["state"]).items()
    }
    held_by_date = {
        timestamp: {str(pair.pool_address).lower() for pair, _share in holdings}
        for timestamp, holdings in _position_weights(entry["state"]).items()
    }
    decisions_with_exclusions = 0
    excluded_that_were_held = 0
    matched_dates, changed_basket = 0, 0
    for timestamp, record in log.items():
        if record["excluded_count"]:
            decisions_with_exclusions += 1
        timestamp = pd.Timestamp(timestamp)
        reference_basket = base_by_date.get(timestamp)
        if reference_basket is None:
            continue
        matched_dates += 1
        excluded_that_were_held += len(set(record["excluded_addresses"]) & reference_basket)
        if held_by_date.get(timestamp, set()) != reference_basket:
            changed_basket += 1
    base_held = {str(p.pair.pool_address).lower() for p in base["state"].portfolio.get_all_positions()
                 if not p.is_credit_supply()}
    held = {str(p.pair.pool_address).lower() for p in entry["state"].portfolio.get_all_positions()
            if not p.is_credit_supply()}
    union = base_held | held
    jaccard = len(base_held & held) / len(union) if union else float("nan")
    aligned = pd.concat(
        [entry["cycle_returns"].rename("a"), base["cycle_returns"].rename("b")], axis=1,
    ).dropna()
    identical = bool(len(aligned) and np.allclose(aligned["a"], aligned["b"], atol=1e-12))
    return {
        "label": entry["label"],
        "decisions_logged": len(log),
        "decisions_with_exclusions": decisions_with_exclusions,
        "dates_matched_to_reference": matched_dates,
        "dates_with_a_different_basket": changed_basket,
        "share_of_decisions_changed": (changed_basket / matched_dates) if matched_dates else float("nan"),
        "excluded_names_the_reference_held": excluded_that_were_held,
        "basket_jaccard_vs_reference": jaccard,
        "distinct_vaults": len(held),
        "equity_path_identical_to_reference": identical,
        "inert": bool(identical),
    }


#: `held_book_character()` and `diversification()` both walk the whole position-statistics tree,
#: and `gate_row()` needs the anchor's values once per candidate. Memoised by run label.
_CHARACTER_CACHE: dict = {}
_DIVERSIFICATION_CACHE: dict = {}


def held_book_character_cached(entry: dict) -> dict:
    label = entry["label"]
    if label not in _CHARACTER_CACHE:
        _CHARACTER_CACHE[label] = held_book_character(entry)
    return _CHARACTER_CACHE[label]


def diversification_cached(entry: dict) -> dict:
    label = entry["label"]
    if label not in _DIVERSIFICATION_CACHE:
        _DIVERSIFICATION_CACHE[label] = diversification(entry)
    return _DIVERSIFICATION_CACHE[label]


def gate_row(
    label: str, gate_5_by_signal: dict, signal: str, neighbours: list,
    null_labels: list | None = None, anchor_label: str = "anchor",
) -> dict:
    """All nine gates for one candidate, scored cheapest-first.

    Every Boolean is listed separately and an unexecuted gate is False, never absent: a
    robustness run that was skipped, failed or never executed cannot produce a passing flag.
    Meeting all nine yields SHORTLIST, not ADOPT.
    """
    entry = run_by_label[label]
    row = entry["panel"]
    anchor = run_by_label[anchor_label]["panel"]
    anchor_entry = run_by_label[anchor_label]
    out = {"label": label, "signal": signal}
    out.update({k: float(row[k]) for k in
                ("cycle_sharpe", "cagr", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta",
                 "mean_invested", "sparse_cagr", "dense_cagr", "late_cagr", "luck_ratio",
                 "top5_gross_share")})

    # Gate 1: positive return. A sanity gate - Sharpe is uninterpretable on a losing book.
    out["gate_1_positive"] = bool(np.isfinite(row["cagr"]) and float(row["cagr"]) > 0)

    # Gate 7: sub-period sign. Cheap, and it kills regime-specific results before any re-simulation.
    segments = [float(row.get(f"{r}_cagr", np.nan)) for r in ("sparse", "dense", "late")]
    out["gate_7_subperiod"] = bool(all(np.isfinite(s) and s > 0 for s in segments))

    # Gate 4: not luck. "No worse than the anchor", NOT "luck-free" - the anchor's own luck_ratio
    # is 0.1459 and its top five positions deliver 60.8% of gross profit.
    out["gate_4_luck"] = bool(
        np.isfinite(row["luck_ratio"]) and np.isfinite(row["top5_gross_share"])
        and float(row["luck_ratio"]) >= float(anchor["luck_ratio"])
        and float(row["top5_gross_share"]) <= float(anchor["top5_gross_share"])
    )

    # Gate 5: the signal predicts forward stability, measured outside the backtest.
    out["gate_5_screen"] = bool(gate_5_by_signal.get(signal, False))

    # Gate 3: the book held stable vaults.
    character = held_book_character_cached(entry)
    anchor_character = held_book_character_cached(anchor_entry)
    out.update({f"held_{k}": v for k, v in character.items()})
    out["anchor_held_vol"] = anchor_character["held_vol"]
    out["anchor_held_concentration"] = anchor_character["held_concentration"]
    out["gate_3_held_book"] = bool(
        np.isfinite(character["held_vol"]) and np.isfinite(character["held_concentration"])
        and character["held_vol"] < anchor_character["held_vol"]
        and character["held_concentration"] < anchor_character["held_concentration"]
    )

    # Gate 8: diversification no worse than the anchor, on all five measures.
    measures = diversification_cached(entry)
    anchor_measures = diversification_cached(anchor_entry)
    out.update(measures)
    failures = []
    for name, larger_is_worse in DIVERSIFICATION_MEASURES.items():
        value, reference = measures[name], anchor_measures[name]
        if not np.isfinite(value) or not np.isfinite(reference):
            failures.append(f"{name} not finite")
        elif larger_is_worse and value > reference:
            failures.append(name)
        elif not larger_is_worse and value < reference:
            failures.append(name)
    out["gate_8_diversification"] = not failures
    out["diversification_failures"] = ", ".join(failures)

    # Gate 6: plateau flatness.
    plateau = plateau_gate(label, neighbours)
    out["gate_6_plateau"] = plateau["passes"]
    out["plateau_detail"] = plateau["detail"]

    # Gate 2: single-vault survival. Expensive - a full re-simulation - so it runs last among the
    # deterministic gates, but it still runs whenever every cheaper gate passed.
    if all(out[g] for g in ("gate_1_positive", "gate_7_subperiod", "gate_4_luck",
                            "gate_5_screen", "gate_3_held_book", "gate_8_diversification",
                            "gate_6_plateau")):
        lovo = lovo_gate(label)
        out["gate_2_lovo"] = lovo["passes"]
        out["lovo_retention"] = lovo["retention"]
        out["lovo_masked"] = lovo["masked"]
    else:
        out["gate_2_lovo"] = False
        out["lovo_retention"] = float("nan")
        out["lovo_masked"] = "not evaluated - a cheaper gate failed"

    # Gate 9: the mechanism's own information-destroying null.
    if null_labels:
        null = null_effectiveness(label, null_labels)
        out["gate_9_null"] = null["passes"]
        out["null_best"] = null["null_best"]
        out["null_distinct_series"] = null["distinct_cycle_return_series"]
    else:
        out["gate_9_null"] = False
        out["null_best"] = float("nan")
        out["null_distinct_series"] = 0

    gates = [f"gate_{i}" for i in range(1, 10)]
    named = {
        "gate_1": "gate_1_positive", "gate_2": "gate_2_lovo", "gate_3": "gate_3_held_book",
        "gate_4": "gate_4_luck", "gate_5": "gate_5_screen", "gate_6": "gate_6_plateau",
        "gate_7": "gate_7_subperiod", "gate_8": "gate_8_diversification", "gate_9": "gate_9_null",
    }
    failed = [g for g in gates if not out[named[g]]]
    out["failed_gates"] = ", ".join(failed)
    out["verdict"] = "SHORTLIST" if not failed else "REJECT"
    return out


def verdict_table_rules(rows: list) -> pd.DataFrame:
    """One row per scored candidate, with every gate Boolean and the complete failure string.

    Never truncate `failed_gates`. Three headings in this track under-reported failures because
    pandas elided the column at 50 characters and the text was read as complete.
    """
    frame = pd.DataFrame([{k: v for k, v in row.items() if k != "plateau_detail"} for row in rows])
    if not len(frame):
        return frame
    return frame.set_index("label").sort_values("cycle_sharpe", ascending=False)


def tie_break(left: str, right: str) -> dict:
    """The operator indifference band, then Pareto dominance on the five gate-8 measures.

    A DECISION POLICY. Below a 0.25 Sharpe difference the more diversified candidate is preferred;
    above it the higher Sharpe wins and the diversification gate still applies as a floor. If
    neither candidate dominates, the comparison is UNRESOLVED and both are carried - this returns
    that verdict rather than inventing a winner.
    """
    left_sharpe = float(run_by_label[left]["panel"]["cycle_sharpe"])
    right_sharpe = float(run_by_label[right]["panel"]["cycle_sharpe"])
    gap = left_sharpe - right_sharpe
    if abs(gap) > INDIFFERENCE_BAND:
        winner = left if gap > 0 else right
        return {"winner": winner, "basis": f"Sharpe gap {gap:+.4f} exceeds the {INDIFFERENCE_BAND} band",
                "resolved": True, "sharpe_gap": gap}
    a, b = diversification_cached(run_by_label[left]), diversification_cached(run_by_label[right])
    def dominates(x, y):
        no_worse, strictly_better = True, False
        for name, larger_is_worse in DIVERSIFICATION_MEASURES.items():
            if not (np.isfinite(x[name]) and np.isfinite(y[name])):
                return False
            better = x[name] < y[name] if larger_is_worse else x[name] > y[name]
            worse = x[name] > y[name] if larger_is_worse else x[name] < y[name]
            no_worse = no_worse and not worse
            strictly_better = strictly_better or better
        return no_worse and strictly_better
    if dominates(a, b):
        return {"winner": left, "basis": "Pareto dominance on the five diversification measures",
                "resolved": True, "sharpe_gap": gap}
    if dominates(b, a):
        return {"winner": right, "basis": "Pareto dominance on the five diversification measures",
                "resolved": True, "sharpe_gap": gap}
    return {"winner": None, "basis": "inside the indifference band and neither dominates",
            "resolved": False, "sharpe_gap": gap}


print(f"harness_rules.py loaded: nine gates of RESEARCH-RULES.md, the screen, "
      f"delta = {DELTA_ANNUALISED_PP} annualised pp. SHORTLIST is the strongest verdict available.")


def assert_anchor_parity_rules(panel_row: pd.Series = None) -> pd.DataFrame:
    """`assert_anchor_parity()` plus the proof that the prefilter splice is inert on the anchor.

    The prefilter block only runs when `stability_prefilter_signal` is a non-empty string, which
    it is not for the anchor, so an empty `PREFILTER_LOG` beside identical anchor metrics is the
    evidence that the third splice this track adds changed nothing.
    """
    frame = assert_anchor_parity(panel_row)
    assert not PREFILTER_LOG, "the stability prefilter fired on the anchor path; the splice is not inert"
    print("Prefilter splice also inert on the anchor path.")
    return frame


# --------------------------------------------------------------------------------------------
# Cross-fitting (NB30). A DIAGNOSTIC, not an out-of-sample test: the folds share vaults and
# market regime, and a purge removes temporal contamination but not cross-sectional.
# --------------------------------------------------------------------------------------------

#: Contiguous folds over the decision schedule, and the purge either side of each fold, in days.
CROSSFIT_FOLDS = 5
CROSSFIT_PURGE_DAYS = 30
#: Fewer draws than the full screen. Five folds of the whole nonlinear statistic is five times
#: the cost, and a fold's screen is a selection step rather than a reported interval.
CROSSFIT_DRAWS = 200


def leading_signal(screen: pd.DataFrame) -> str | None:
    """The signal a screen selects, by a rule pre-registered before any fold was run.

    Among the signals passing gate 5, the one whose WEAKEST simultaneous lower bound across the
    three stability targets is largest. That is deliberately not "the largest correlation": gate 5
    requires all three targets, so the binding evidence for a signal is its weakest leg, and
    ranking on the strongest leg would prefer a signal that predicts one thing well and the other
    two barely at all.

    Ties are broken by signal name, so the choice is reproducible and never depends on row order.

    :return:
        The chosen signal, or ``None`` when no signal passes gate 5 on this screen - in which case
        the fold runs with no prefilter at all and says so.
    """
    passers = [s for s in screen.index if bool(screen.loc[s, "gate_5"])]
    if not passers:
        return None
    scored = [
        (min(float(screen.loc[s, f"lo_{t}"]) for t in STABILITY_TARGETS), s) for s in passers
    ]
    best = max(score for score, _s in scored)
    return sorted(s for score, s in scored if score == best)[0]


def fold_schedule(dates, folds: int = CROSSFIT_FOLDS, purge_days: int = CROSSFIT_PURGE_DAYS) -> list:
    """Contiguous date folds with a purge either side, as `(start, end, training dates)` tuples.

    `end` is EXCLUSIVE, so the folds partition the schedule with no decision counted twice. The
    training set for a fold excludes the fold itself and every date within `purge_days` of it,
    because a decision just before a fold has a 30-day forward window that overlaps the fold's
    returns - which is the whole reason a plain split does not make this out-of-sample.
    """
    dates = sorted(pd.Timestamp(d) for d in dates)
    boundaries = np.linspace(0, len(dates), folds + 1).astype(int)
    purge = pd.Timedelta(days=purge_days)
    out = []
    for k in range(folds):
        lo, hi = boundaries[k], boundaries[k + 1]
        if hi <= lo:
            continue
        start, end = dates[lo], dates[hi - 1]
        training = [
            d for d in dates
            if d < (start - purge) or d > (end + purge)
        ]
        out.append({
            "fold": k, "start": start, "end_inclusive": end,
            "end_exclusive": end + pd.Timedelta(days=1),
            "fold_dates": dates[lo:hi], "training_dates": training,
        })
    return out
