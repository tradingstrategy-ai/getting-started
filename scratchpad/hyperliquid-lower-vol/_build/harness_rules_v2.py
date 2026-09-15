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


# --------------------------------------------------------------------------------------------
# Second-round corrections (gpt-5.6-terra, 2026-09-15).
#
# - A hypothesis that is NOT EVALUATED - its signal has fewer than `SCREEN_MIN_DATES` usable
#   dates, or its bootstrap standard error is non-finite - was making every draw incomplete under
#   the complete-family rule, which set the whole family's critical value to NaN and failed every
#   signal mechanically. NB30's walk-forward folds hit this. Unevaluated hypotheses are now
#   REMOVED from the family before the max-T is formed, the family size actually used is
#   reported, and an unevaluated signal is marked as such rather than as failed.
# - The corrected event-concentration target changed gate 5's estimand after results were known.
#   `run_screen()` produces the screen for either target, so the PRE-REGISTERED raw target gives
#   the verdict and the corrected excess target is reported as a post-review diagnostic.
# - `oracle_reachability()` shows what the screening machinery CAN do on this panel by feeding it
#   a perfect-foresight signal: standing rule 9 asks that a surprising null be shown unreachable,
#   not merely unobserved.
# --------------------------------------------------------------------------------------------

def simultaneous_ci(observed: np.ndarray, replicates: np.ndarray, level: float = 0.95,
                    evaluated: np.ndarray | None = None) -> dict:
    """One-sided simultaneous LOWER bounds by studentised max-T over the EVALUATED family.

    `evaluated` marks hypotheses that belong in the family. Those with a non-finite observed
    value or a non-finite bootstrap standard error are dropped as well, and counted. A draw is
    then used only if every REMAINING hypothesis is finite in it. Fails closed below
    `SIMULTANEOUS_MIN_DRAWS` complete draws, or with an empty family.
    """
    observed = np.asarray(observed, dtype=float)
    replicates = np.asarray(replicates, dtype=float)
    standard_error = np.nanstd(replicates, axis=0, ddof=1)
    member = np.isfinite(observed) & np.isfinite(standard_error) & (standard_error > 0)
    if evaluated is not None:
        member &= np.asarray(evaluated, dtype=bool)
    safe = np.where(standard_error > 0, standard_error, np.nan)
    studentised = (replicates - observed[None, :]) / safe[None, :]
    if member.any():
        complete = np.isfinite(studentised[:, member]).all(axis=1)
        per_draw_max = studentised[complete][:, member].max(axis=1) if complete.any() else np.array([])
    else:
        per_draw_max = np.array([])
    critical = float(np.percentile(per_draw_max, level * 100.0)) if len(per_draw_max) >= SIMULTANEOUS_MIN_DRAWS else float("nan")
    lower = np.where(member, observed - critical * standard_error, np.nan)
    return {
        "observed": observed, "se": standard_error, "critical": critical,
        "lower_simultaneous": lower,
        "lower_unadjusted": np.nanpercentile(replicates, (1.0 - level) * 100.0, axis=0),
        "n_draws": int(len(per_draw_max)), "n_draws_total": int(replicates.shape[0]),
        "n_draws_incomplete": int(replicates.shape[0] - len(per_draw_max)),
        "family_size_used": int(member.sum()), "family_size_total": int(len(observed)),
        "member": member,
    }


def screen_table(bootstrap: dict, delta: float = DELTA_ANNUALISED_PP) -> tuple:
    """The screen's result table and gate-5 verdicts, with unevaluated signals marked as such.

    As harness_rules.screen_table, with two changes: hypotheses of a signal that has fewer than
    `SCREEN_MIN_DATES` usable dates are removed from the simultaneous family before the max-T is
    formed, and the table carries an `evaluated` column so a signal that could not be tested is
    not counted as one that failed.
    """
    observed, replicates = bootstrap["observed"], bootstrap["draws"]
    n_signals = observed.shape[0]
    index = {name: i for i, name in enumerate(STAT_NAMES)}
    evaluated_signal = np.array([bootstrap["samples"][s]["dates"] >= SCREEN_MIN_DATES for s in SIGNAL_NAMES])

    def family(stat_names):
        columns = [index[n] for n in stat_names]
        flat_observed = observed[:, columns].reshape(-1)
        flat_draws = replicates[:, :, columns].reshape(replicates.shape[0], -1)
        flat_evaluated = np.repeat(evaluated_signal, len(stat_names))
        result = simultaneous_ci(flat_observed, flat_draws, evaluated=flat_evaluated)
        result["p"] = add_one_p(flat_draws, flat_observed)
        for key in ("observed", "se", "lower_simultaneous", "lower_unadjusted", "p", "member"):
            result[key] = np.asarray(result[key]).reshape(n_signals, len(stat_names))
        return result

    stability = family([f"spearman_{t}" for t in STABILITY_TARGETS])
    returns = family([f"tail_{RETURN_TARGET}_pp"])
    tails = family([f"tail_{t}" for t in STABILITY_TARGETS])

    rows = []
    for i, signal in enumerate(SIGNAL_NAMES):
        sample = bootstrap["samples"][signal]
        row = {"signal": signal, "direction": SIGNAL_DIRECTION[signal],
               "time_base": next((s["time_base"] for s in SIGNALS if s["name"] == signal), ""),
               "rows": sample["rows"], "dates": sample["dates"]}
        for j, target in enumerate(STABILITY_TARGETS):
            row[f"rho_{target}"] = stability["observed"][i, j]
            row[f"lo_{target}"] = stability["lower_simultaneous"][i, j]
            row[f"tail_{target}"] = tails["observed"][i, j]
            row[f"tail_lo_{target}"] = tails["lower_simultaneous"][i, j]
        row["rho_forward_return"] = observed[i, index[f"spearman_{RETURN_TARGET}"]]
        row["return_contrast_pp"] = returns["observed"][i, 0]
        row["return_lo_pp"] = returns["lower_simultaneous"][i, 0]
        enough = bool(evaluated_signal[i])
        in_family = bool(stability["member"][i].all() and returns["member"][i, 0])
        row["enough_dates"] = enough
        row["evaluated"] = bool(enough and in_family)
        stability_ok = bool(row["evaluated"] and all(
            np.isfinite(stability["lower_simultaneous"][i, j]) and stability["lower_simultaneous"][i, j] > 0.0
            for j in range(len(STABILITY_TARGETS))))
        return_ok = bool(row["evaluated"] and np.isfinite(returns["lower_simultaneous"][i, 0])
                         and returns["lower_simultaneous"][i, 0] > -float(delta))
        row["stability_clause"] = stability_ok
        row["return_clause"] = return_ok
        row["gate_5"] = bool(stability_ok and return_ok)
        rows.append(row)
    table = pd.DataFrame(rows).set_index("signal")
    detail = {"stability": stability, "returns": returns, "tails": tails, "delta": float(delta)}
    return table, detail


#: The two constructions of the event-concentration target. `pre_registered` is what the plan and
#: harness_rules.py specified; `corrected` is the excess over the uniform-events value.
CONCENTRATION_TARGETS = {"pre_registered": "forward_event_top5", "corrected": "forward_event_top5_excess"}


def run_screen(panel_frame: pd.DataFrame, concentration: str = "pre_registered",
               draws: int = SCREEN_DRAWS, seed: int = SCREEN_SEED, verbose: bool = True) -> tuple:
    """Bootstrap and screen the panel with one construction of the event-concentration target.

    Sets the module-level target lists for the duration of the call and restores them after, so
    the pre-registered and the corrected screens can both be produced from one panel and neither
    silently becomes the other.
    """
    global STABILITY_TARGETS, SCREEN_TARGETS, STAT_NAMES
    saved = (STABILITY_TARGETS, SCREEN_TARGETS, STAT_NAMES)
    target = CONCENTRATION_TARGETS[concentration]
    STABILITY_TARGETS = ["forward_vol", "forward_downside", target]
    SCREEN_TARGETS = STABILITY_TARGETS + [RETURN_TARGET]
    STAT_NAMES = ([f"spearman_{t}" for t in STABILITY_TARGETS] + [f"spearman_{RETURN_TARGET}"]
                  + [f"tail_{t}" for t in STABILITY_TARGETS] + [f"tail_{RETURN_TARGET}_pp"])
    try:
        bootstrap = joint_cluster_bootstrap(panel_frame, draws=draws, seed=seed, verbose=verbose)
        table, detail = screen_table(bootstrap)
        table.attrs["concentration_target"] = target
        return table, detail, bootstrap
    finally:
        STABILITY_TARGETS, SCREEN_TARGETS, STAT_NAMES = saved


def oracle_reachability(panel_frame: pd.DataFrame, concentration: str = "pre_registered",
                        draws: int = 200, seed: int = SCREEN_SEED + 1) -> pd.DataFrame:
    """Can the screen pass ANYTHING on this panel? Feed it perfect foresight and see.

    Two oracle signals are appended: `oracle_stability`, equal to the forward volatility itself
    (direction 'high': a high value IS less stable), and `oracle_return`, equal to the forward
    return itself (direction 'low': a low value is the end the mechanism would exclude). A screen
    that cannot pass the stability clause for `oracle_stability`, or the return clause for
    `oracle_return`, cannot pass it for any real signal, and the zero-of-thirteen result is then a
    property of the gate on this data rather than of the signals. That is what standing rule 9
    asks: shown unreachable, not merely unobserved.
    """
    global SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION
    saved = (SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION)
    frame = panel_frame.copy()
    frame["oracle_stability"] = frame["forward_vol"]
    frame["oracle_return"] = frame["forward_return"]
    SIGNALS = list(SIGNALS) + [
        {"name": "oracle_stability", "direction": "high", "time_base": "perfect foresight", "note": "= forward_vol"},
        {"name": "oracle_return", "direction": "low", "time_base": "perfect foresight", "note": "= forward_return"},
    ]
    SIGNAL_NAMES = [s["name"] for s in SIGNALS]
    SIGNAL_DIRECTION = {s["name"]: s["direction"] for s in SIGNALS}
    try:
        table, detail, _ = run_screen(frame, concentration, draws=draws, seed=seed, verbose=False)
    finally:
        SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION = saved
    keep = ["dates", "evaluated"] + [c for c in table.columns if c.startswith("rho_") or c.startswith("lo_")] + \
           ["return_contrast_pp", "return_lo_pp", "stability_clause", "return_clause", "gate_5"]
    out = table.loc[["oracle_stability", "oracle_return"], keep].copy()
    out.attrs["draws"] = draws
    return out


def gate_3_corrected(label: str, anchor_label: str = "anchor") -> dict:
    """Gate 3 with the corrected concentration indicator, AND a per-date full-precision comparison
    of the two indicators on the held book, so "identical" is shown rather than inferred from two
    rounded aggregates."""
    entry, anchor_entry = run_by_label[label], run_by_label[anchor_label]

    def per_date(entry_, indicator):
        weights = _position_weights(entry_["state"])
        out = {}
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
            if 1.0 - covered / total <= HELD_BOOK_MAX_DROPPED_WEIGHT and covered > 0:
                out[pd.Timestamp(timestamp)] = accumulated / covered
        return pd.Series(out, dtype=float)

    own_o, own_c = per_date(entry, "residual_event_concentration"), per_date(entry, "residual_event_concentration_positive")
    ref_o, ref_c = per_date(anchor_entry, "residual_event_concentration"), per_date(anchor_entry, "residual_event_concentration_positive")
    character, anchor_character = held_book_character_cached(entry), held_book_character_cached(anchor_entry)
    same_dates = bool(own_o.index.equals(own_c.index) and ref_o.index.equals(ref_c.index))
    max_diff = float(max(
        (own_o - own_c.reindex(own_o.index)).abs().max() if len(own_o) else 0.0,
        (ref_o - ref_c.reindex(ref_o.index)).abs().max() if len(ref_o) else 0.0,
    ))
    return {
        "held_concentration_corrected": float(own_c.mean()) if len(own_c) else float("nan"),
        "anchor_held_concentration_corrected": float(ref_c.mean()) if len(ref_c) else float("nan"),
        "dates_used_corrected": int(len(own_c)),
        "indicators_same_dates": same_dates,
        "indicators_max_abs_diff_per_date": max_diff,
        "gate_3_corrected": bool(
            len(own_c) and len(ref_c)
            and np.isfinite(character["held_vol"]) and np.isfinite(anchor_character["held_vol"])
            and character["held_vol"] < anchor_character["held_vol"]
            and own_c.mean() < ref_c.mean()
        ),
    }


def provenance_record() -> dict:
    """Provenance as a plain dict keyed by file, for manifests and cross-notebook assertions."""
    frame = provenance()
    return {str(row["file"]): {"bytes": (None if row["bytes"] != row["bytes"] else int(row["bytes"])),
                               "sha256": str(row["sha256"])} for _i, row in frame.iterrows()}


def assert_same_snapshot(upstream: dict, name: str) -> None:
    """Fail loudly if an upstream manifest's data files differ from this kernel's."""
    here = provenance_record()
    for path, record in upstream.items():
        if path == "git HEAD":
            continue
        assert path in here, f"{name}: {path} missing from this kernel's provenance"
        assert here[path]["sha256"] == record["sha256"], (
            f"{name} was produced on a different snapshot of {path}: "
            f"{record['sha256']} there, {here[path]['sha256']} here")
    print(f"snapshot matches {name} on {sum(1 for p in upstream if p != 'git HEAD')} data files")


print("harness_rules_v2.py second round: evaluated-family max-T, run_screen() for both concentration "
      "targets, oracle_reachability(), per-date gate-3 comparison, provenance assertions.")
