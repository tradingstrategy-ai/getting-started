#: Corrections to harness_rules.py after the first independent review of NB28-NB31 (gpt-5.6-terra,
#: 2026-09-14). Loaded AFTER harness_rules.py and REDEFINES the names below; harness_rules.py is
#: left as it is because NB32 embeds its text and is committed with executed outputs.
#:
#: Every function in harness_rules.py that calls one of these looks the name up in the notebook
#: namespace at call time, so the redefinitions take effect for `build_screen_panel()`,
#: `joint_cluster_bootstrap()`, `screen_table()` and `verdict_table_rules()` without those being
#: touched.
#:
#: What is corrected, and why:
#:
#: - `simultaneous_ci()` used `np.nanmax` across hypotheses. A draw in which one hypothesis was
#:   non-finite was maximised over the others, which LOWERS the critical value and RAISES every
#:   lower bound - anti-conservative. It cannot have created a pass (none occurred), but the
#:   reported bounds were slightly too high. Now a draw is retained only when the whole family is
#:   finite, the retained count is reported, and the bound fails closed below a minimum.
#: - `add_one_p()` counted non-finite draws as non-exceedances while keeping them in the
#:   denominator, so its p-values were too small. Now per-hypothesis on finite draws.
#: - `_statistics_from()` applied `sign` to the return Spearman as well as the stability ones,
#:   which INVERTED the documented meaning of `rho_forward_return`. It also expressed the return
#:   contrast in annualised log-return points while `delta` is calibrated in CAGR points. Both
#:   fixed: `-sign` on the return correlation, and the contrast as a difference of compounded
#:   annual returns.
#: - `forward_event_top5` was bounded below by 5/n for a window with n positive events - 0.625 at
#:   the 8-event minimum, 0.10 at fifty - so it partly measured how often a vault reported. The
#:   gate target is now the EXCESS over the uniform-events value, `share - min(5, n)/n`, which is
#:   zero for perfectly unconcentrated upside at any n. The raw share is kept as a diagnostic.
#: - `fold_schedule()` purged 30 days either side of a fold, which covers the 30-day forward
#:   targets and nothing else: the signals use trailing windows of 45 to 360 rows, so a training
#:   date after a fold carried that fold's returns inside its signal values. Now walk-forward
#:   only: training dates strictly before the fold, minus the forward embargo. Folds with fewer
#:   than `SCREEN_MIN_DATES` training dates are marked unevaluable rather than screened.
#: - `residual_event_concentration` (NB08) takes its top five from all residuals, not the
#:   positive ones. Gate 3 is pre-registered on that indicator and stays on it; the corrected
#:   `residual_event_concentration_positive` is reported alongside as `gate_3_corrected`.

#: Fewest complete-family bootstrap draws before a simultaneous bound is reported at all.
SIMULTANEOUS_MIN_DRAWS = 100

STABILITY_TARGETS = ["forward_vol", "forward_downside", "forward_event_top5_excess"]
RETURN_TARGET = "forward_return"
DIAGNOSTIC_TARGETS = ["forward_max_dd", "forward_event_top5", "forward_positive_events"]
SCREEN_TARGETS = STABILITY_TARGETS + [RETURN_TARGET]
STAT_NAMES = (
    [f"spearman_{t}" for t in STABILITY_TARGETS] + [f"spearman_{RETURN_TARGET}"]
    + [f"tail_{t}" for t in STABILITY_TARGETS] + [f"tail_{RETURN_TARGET}_pp"]
)


def forward_targets_for(pair, timestamp, beta: float) -> dict:
    """Realised forward stability and return of ONE vault over `(T, T + 30 days]`.

    As in harness_rules.py, with the event-concentration target replaced by its excess over the
    uniform-events value and the raw share and positive-event count kept as diagnostics.
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
        n = len(positive)
        out["forward_positive_events"] = float(n)
        if n < MIN_POSITIVE_EVENTS:
            out["reason"] = (out["reason"] + "; " if out["reason"] else "") + "insufficient_positive_events"
        elif positive.sum() <= 0:
            out["reason"] = (out["reason"] + "; " if out["reason"] else "") + "zero_denominator"
        else:
            share = float(np.sort(positive)[-5:].sum() / positive.sum())
            out["forward_event_top5"] = share
            # Uniform upside over n events puts exactly min(5, n)/n in the top five; the excess is
            # what concentration adds on top of that, and it is zero for any n when nothing does.
            out["forward_event_top5_excess"] = share - min(5, n) / n

    for name in SCREEN_TARGETS:
        if not np.isfinite(out[name]) and not out["reason"]:
            out["reason"] = "non_finite"
    return out


def _statistics_from(matrix: np.ndarray, sign: float) -> np.ndarray:
    """The eight per-date statistics for one signal on one date's candidate matrix.

    Columns of `matrix`: the signal, `forward_vol`, `forward_downside`,
    `forward_event_top5_excess`, `forward_return`.

    :return:
        ``[3 signed stability Spearman, return Spearman, 3 normalised-rank tail contrasts,
        return tail contrast in compounded annual percentage points]``.
    """
    n = matrix.shape[0]
    ranks = rankdata(matrix, axis=0)
    centred = ranks - ranks.mean(axis=0)
    norms = np.sqrt((centred ** 2).sum(axis=0))
    norms[norms == 0] = np.nan
    correlations = (centred[:, 1:] * centred[:, :1]).sum(axis=0) / (norms[1:] * norms[0])
    # Stability targets: `sign` makes positive mean "the stable end had the more stable outcome".
    # Return target: the stable end is the HIGH-signal end when direction is 'low' (sign = -1),
    # so "the stable end earned more" is a POSITIVE raw correlation there, and `-sign` keeps the
    # documented orientation. harness_rules.py applied `sign` to all four, inverting this one.
    spearman = np.concatenate([sign * correlations[:3], [-sign * correlations[3]]])

    k = int(math.floor(TAIL_FRACTION * n))
    tail = np.full(4, np.nan)
    if k >= 1 and n - k >= 1:
        order = np.argsort(sign * -ranks[:, 0], kind="stable")
        excluded, retained = order[:k], order[k:]
        normalised = (ranks - 1.0) / max(n - 1, 1)
        for j in range(3):
            tail[j] = -(normalised[retained, j + 1].mean() - normalised[excluded, j + 1].mean())
        # Compounded annual return of each group from its mean 30-day log return, then the
        # difference in percentage points - the unit `delta` was calibrated in. The earlier form,
        # a scaled difference of mean log returns, is a different unit.
        annual = 365.0 / FORWARD_HORIZON_DAYS
        retained_cagr = math.expm1(matrix[retained, 4].mean() * annual)
        excluded_cagr = math.expm1(matrix[excluded, 4].mean() * annual)
        tail[3] = (retained_cagr - excluded_cagr) * 100.0
    return np.concatenate([spearman, tail])


def simultaneous_ci(observed: np.ndarray, replicates: np.ndarray, level: float = 0.95) -> dict:
    """One-sided simultaneous LOWER bounds by studentised max-T, on COMPLETE-FAMILY draws only.

    A draw is used only if every hypothesis in the family has a finite studentised statistic in
    it. Maximising over the finite subset - what `np.nanmax` did - shrinks the maximum on exactly
    the draws where a hypothesis is missing, lowers the critical value, and raises every bound.
    Fails closed: fewer than `SIMULTANEOUS_MIN_DRAWS` complete draws yields NaN bounds.
    """
    observed = np.asarray(observed, dtype=float)
    replicates = np.asarray(replicates, dtype=float)
    standard_error = np.nanstd(replicates, axis=0, ddof=1)
    safe = np.where(standard_error > 0, standard_error, np.nan)
    studentised = (replicates - observed[None, :]) / safe[None, :]
    complete = np.isfinite(studentised).all(axis=1)
    per_draw_max = studentised[complete].max(axis=1) if complete.any() else np.array([])
    if len(per_draw_max) >= SIMULTANEOUS_MIN_DRAWS:
        critical = float(np.percentile(per_draw_max, level * 100.0))
    else:
        critical = float("nan")
    return {
        "observed": observed, "se": standard_error, "critical": critical,
        "lower_simultaneous": observed - critical * standard_error,
        "lower_unadjusted": np.nanpercentile(replicates, (1.0 - level) * 100.0, axis=0),
        "n_draws": int(len(per_draw_max)), "n_draws_total": int(replicates.shape[0]),
        "n_draws_incomplete": int(replicates.shape[0] - len(per_draw_max)),
    }


def add_one_p(replicates: np.ndarray, observed: np.ndarray) -> np.ndarray:
    """One-sided add-one bootstrap p-values for `theta <= 0`, per hypothesis, on finite draws."""
    centred = replicates - observed[None, :]
    finite = np.isfinite(centred)
    exceed = ((centred >= observed[None, :]) & finite).sum(axis=0)
    n_finite = finite.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(n_finite > 0, (1.0 + exceed) / (n_finite + 1.0), np.nan)


def paired_measure_difference_common(panel_frame: pd.DataFrame, left: str, right: str,
                                     draws: int = SCREEN_DRAWS, seed: int = SCREEN_SEED) -> tuple:
    """Paired difference of two signals' statistics on ONE common (date, vault) sample.

    `paired_measure_difference()` shares resamples but each signal has its own complete-case
    sample, so the difference mixes estimand with sample. This restricts the panel to rows where
    BOTH signals are finite, runs the joint bootstrap on that panel, and differences there.

    :return:
        ``(difference frame, bootstrap dict, rows in the common sample)``.
    """
    common = panel_frame[np.isfinite(panel_frame[left]) & np.isfinite(panel_frame[right])]
    bootstrap = joint_cluster_bootstrap(common, draws=draws, seed=seed, verbose=False)
    return paired_measure_difference(bootstrap, left, right), bootstrap, int(len(common))


def fold_schedule(dates, folds: int = CROSSFIT_FOLDS, purge_days: int = CROSSFIT_PURGE_DAYS) -> list:
    """Contiguous folds, trained WALK-FORWARD only: on dates strictly before the fold minus the
    forward embargo. No post-fold training dates, because every signal's trailing window would
    carry the fold's returns into them; the earliest folds are therefore unevaluable, and say so.
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
        training = [d for d in dates if d < (start - purge)]
        out.append({
            "fold": k, "start": start, "end_inclusive": end,
            "end_exclusive": end + pd.Timedelta(days=1),
            "fold_dates": dates[lo:hi], "training_dates": training,
            "evaluable": len(training) >= SCREEN_MIN_DATES,
        })
    return out


def held_book_concentration(entry: dict, indicator: str) -> dict:
    """Capital-weighted own event concentration of what was held, for a named indicator, with its
    own coverage. Same construction as `held_book_character()` for the concentration leg alone."""
    weights = _position_weights(entry["state"])
    values, excluded = [], 0
    for timestamp in sorted(weights):
        holdings = weights[timestamp]
        total = sum(share for _p, share in holdings)
        if total <= 0:
            continue
        accumulated, covered = 0.0, 0.0
        for pair, share in holdings:
            value = value_at_prior(indicator_series(indicator, pair), timestamp)
            if np.isfinite(value):
                accumulated += share * value
                covered += share
        if 1.0 - covered / total > HELD_BOOK_MAX_DROPPED_WEIGHT:
            excluded += 1
            continue
        if covered > 0:
            values.append(accumulated / covered)
    return {"held_concentration": float(np.mean(values)) if values else float("nan"),
            "dates_used": len(values), "dates_excluded": excluded}


def gate_3_corrected(label: str, anchor_label: str = "anchor") -> dict:
    """Gate 3 evaluated with `residual_event_concentration_positive` in place of the original.

    NOT the verdict gate - RESEARCH-RULES.md names the original indicator and standing rule 2
    forbids swapping it after seeing a result. Reported beside it so the two can disagree visibly.
    """
    entry, anchor_entry = run_by_label[label], run_by_label[anchor_label]
    own = held_book_concentration(entry, "residual_event_concentration_positive")
    ref = held_book_concentration(anchor_entry, "residual_event_concentration_positive")
    character, anchor_character = held_book_character_cached(entry), held_book_character_cached(anchor_entry)
    return {
        "held_concentration_corrected": own["held_concentration"],
        "anchor_held_concentration_corrected": ref["held_concentration"],
        "dates_used_corrected": own["dates_used"],
        "gate_3_corrected": bool(
            np.isfinite(own["held_concentration"]) and np.isfinite(ref["held_concentration"])
            and np.isfinite(character["held_vol"]) and np.isfinite(anchor_character["held_vol"])
            and character["held_vol"] < anchor_character["held_vol"]
            and own["held_concentration"] < ref["held_concentration"]
        ),
    }


print("harness_rules_v2.py loaded: complete-family max-T, finite-draw p-values, oriented return "
      "Spearman, CAGR-point return contrast, excess event concentration, walk-forward folds, "
      "corrected gate-3 diagnostic.")
