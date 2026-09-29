"""harness_rules_v3.py - the plan 34 screen: two signals, two targets, the actual exclusion.

Loaded AFTER harness_rules.py and harness_rules_v2.py in the same kernel, so anything it defines
replaces the earlier definition by name. NB28-NB33 embed those two modules and are committed
with executed outputs, so they are not edited; the changes live here.

What changes for plan 34 (34-volatility-tail-exclusion-plan.md, amendments A1, A2 and the scope
statement in RESEARCH-RULES.md):

- The screened family is TWO signals - `calm_score` and `inverse_vol`, both direction 'low' -
  not thirteen. The signal was chosen by NB28; this screen is run once for coverage and for the
  post-break regime, not to choose a signal.
- Gate 5's stability targets are forward volatility and forward downside variation only. The
  concentration target is kept as a DIAGNOSTIC column and is not in any gated family.
- The tail contrasts are computed at the mechanism's ACTUAL exclusion: the `EXCLUSION_COUNT`
  candidates with the lowest finite signal on each date, chosen among the FULL logged pool from
  decision-time information, before any row is dropped for a missing forward outcome. The
  previous screens excluded a 30% tail of the complete-case sample instead, which is a
  different set.
- The return clause is a typical-vault non-inferiority: per date, the MEDIAN forward 30-day
  log NAV return of the retained set minus that of the excluded set, averaged over dates, and
  its simultaneous lower bound must exceed `-RETURN_MARGIN_LOG`. The mean-based clause in
  compounded annual percentage points is gone; NB28 showed its half-width was 20-60x its margin.
- The share of retained and of excluded vaults whose forward return is below `CRASH_LOG_RETURN`
  is reported beside the clause as a diagnostic, because a median cannot see a crash minority.
- Screens are run on decisions on or after `POST_BREAK_START` for the verdict; earlier decisions
  are screened separately and labelled diagnostic.
"""

#: First decision date of the dense-polling regime. Before it, 99% of 180-day-old candidates
#: had fewer than 60 price-changing marks in 180 days, so a 30-day forward PATH is mostly
#: unobserved and a path target measured on it is not the quantity the gate names.
POST_BREAK_START = pd.Timestamp("2026-04-01")

#: Amendment A2: the return clause's margin in 30-day log-return units. Half a percentage point
#: of typical-vault return per month, about 6% a year.
RETURN_MARGIN_LOG = 0.005

#: A forward 30-day log return below this is a crash for the diagnostic share.
CRASH_LOG_RETURN = -0.5

#: The mechanism's exclusion count at the centre of plan 34, and the count the actual-exclusion
#: tail contrast is computed at.
EXCLUSION_COUNT = 8

SIGNALS = [
    {"name": "calm_score", "direction": "low", "time_base": "90 calendar rows, fresh-guarded",
     "note": "inverse_vol, NaN unless >= 30 fresh marks in the window and the last within 10 rows"},
    {"name": "inverse_vol", "direction": "low", "time_base": "90 calendar rows",
     "note": "the sizing rule's own premise; measured_8's signal; the calendar reference"},
]
SIGNAL_NAMES = [s["name"] for s in SIGNALS]
SIGNAL_DIRECTION = {s["name"]: s["direction"] for s in SIGNALS}
SIGNAL_ABSOLUTE = set()

STABILITY_TARGETS = ["forward_vol", "forward_downside"]
RETURN_TARGET = "forward_return"
SCREEN_TARGETS = STABILITY_TARGETS + [RETURN_TARGET]
DIAGNOSTIC_TARGETS = ["forward_max_dd", "forward_event_top5", "forward_event_top5_excess",
                      "forward_positive_events"]
STAT_NAMES = (
    [f"spearman_{t}" for t in STABILITY_TARGETS] + [f"spearman_{RETURN_TARGET}"]
    + [f"tail_{t}" for t in STABILITY_TARGETS]
    + ["median_return_contrast", "crash_share_retained", "crash_share_excluded", "excluded_in_sample"]
)


def exclusion_flag_column(signal: str) -> str:
    return f"excluded_{EXCLUSION_COUNT}_{signal}"


def actual_exclusion_flags(panel_frame: pd.DataFrame, signal: str, count: int = EXCLUSION_COUNT) -> pd.Series:
    """Which panel rows the splice would exclude at `count` on `signal`, per date.

    Mirrors `_PREFILTER_BLOCK` exactly: among candidates whose signal is finite, sort by
    `(sign * value, pair_id)` ascending and take the first `min(count, measured)`. Computed on
    the FULL logged pool for the date, so a candidate whose forward outcome is later found to be
    missing still counts towards the eight, as it does in the engine.
    """
    sign = 1.0 if SIGNAL_DIRECTION[signal] == "low" else -1.0
    flag = pd.Series(False, index=panel_frame.index)
    for _date, group in panel_frame.groupby("date"):
        finite = group[np.isfinite(group[signal])]
        order = sorted(finite.index, key=lambda i: (sign * float(finite.at[i, signal]), int(finite.at[i, "pair_id"])))
        flag.loc[order[:min(int(count), len(order))]] = True
    return flag


def add_exclusion_flags(panel_frame: pd.DataFrame, count: int = EXCLUSION_COUNT) -> pd.DataFrame:
    for signal in SIGNAL_NAMES:
        panel_frame[exclusion_flag_column(signal)] = actual_exclusion_flags(panel_frame, signal, count)
    return panel_frame


def verify_exclusion_flags(panel_frame: pd.DataFrame, entry: dict, signal: str) -> pd.DataFrame:
    """Compare the offline flags against a real `count = EXCLUSION_COUNT` run's log.

    Only dates on which that run's candidate pool is IDENTICAL to the logging run's pool are
    comparable: once the exclusion changes the book, later pools can differ through the
    position-dependent admission rules. On comparable dates the excluded address sets must match
    exactly; the number of comparable dates is returned so it cannot be quietly small.
    """
    log = entry["prefilter_log"]
    column = exclusion_flag_column(signal)
    rows = []
    for date, group in panel_frame.groupby("date"):
        record = log.get(pd.Timestamp(date)) or log.get(date)
        if record is None:
            continue
        logged_pool = set(record["candidate_addresses"])
        panel_pool = set(group["address"])
        comparable = logged_pool == panel_pool
        offline = set(group.loc[group[column], "address"])
        engine = set(record["excluded_addresses"])
        rows.append({"date": pd.Timestamp(date), "comparable_pool": comparable,
                     "offline_excluded": len(offline), "engine_excluded": len(engine),
                     "match": bool(offline == engine) if comparable else None})
    frame = pd.DataFrame(rows)
    comparable = frame[frame["comparable_pool"]]
    assert len(comparable) > 0, f"no comparable dates between the panel and {entry['label']}"
    mismatches = comparable[~comparable["match"].astype(bool)]
    assert mismatches.empty, (
        f"offline exclusion differs from the engine's on {len(mismatches)} comparable dates for {signal}")
    print(f"{signal}: offline exclusion at {EXCLUSION_COUNT} matches {entry['label']}'s engine log on all "
          f"{len(comparable)} comparable dates of {len(frame)} (pools identical on those dates)")
    return frame


def verify_signal_reads(panel_frame: pd.DataFrame, entry: dict, signal: str) -> int:
    """The panel's `value_at_prior` read must equal what the splice read in-trade, per candidate."""
    log = entry["prefilter_log"]
    assert all(record["signal"] == signal for record in log.values()), "logging run used a different signal"
    checked, worst = 0, 0.0
    for date, group in panel_frame.groupby("date"):
        record = log.get(pd.Timestamp(date)) or log.get(date)
        if record is None:
            continue
        for address, value in zip(group["address"], group[signal]):
            logged = record["values"].get(address)
            if logged is None:
                continue
            both_nan = (not np.isfinite(value)) and (not np.isfinite(logged))
            if both_nan:
                checked += 1
                continue
            assert np.isfinite(value) == np.isfinite(logged), (
                f"{signal} finiteness differs offline vs in-trade for {address} at {date}")
            worst = max(worst, abs(float(value) - float(logged)))
            checked += 1
    assert worst < 1e-9, f"{signal}: offline read differs from the in-trade read by {worst}"
    print(f"{signal}: {checked} offline reads equal the in-trade reads (max abs diff {worst:.1e})")
    return checked


def _signal_sample(panel_frame: pd.DataFrame, signal: str) -> dict:
    """Complete-case sample for one signal: rows where it and all THREE targets are finite.

    The exclusion flag travels with each row as a fifth column. It was set on the full pool, so
    the excluded set inside the complete-case sample is a subset of the engine's eight; the
    per-date count that survived is one of the statistics, so its typical size is reported.
    """
    columns = [signal] + SCREEN_TARGETS + [exclusion_flag_column(signal)]
    usable = panel_frame[np.isfinite(panel_frame[[signal] + SCREEN_TARGETS]).all(axis=1)]
    by_date = {}
    for date, group in usable.groupby("date"):
        if len(group) < SCREEN_MIN_CANDIDATES:
            continue
        matrix = group[columns].to_numpy(dtype=float)
        if np.ptp(matrix[:, 0]) == 0:
            continue
        by_date[pd.Timestamp(date)] = {"vault": group["pair_id"].to_numpy(), "matrix": matrix}
    return {"signal": signal, "by_date": by_date, "rows": len(usable), "dates": len(by_date)}


def _statistics_from(matrix: np.ndarray, sign: float) -> np.ndarray:
    """The nine per-date statistics for one signal on one date.

    Columns of `matrix`: the signal, `forward_vol`, `forward_downside`, `forward_return`, the
    actual-exclusion flag (1.0 = the engine would exclude this candidate).

    :return:
        ``[2 signed stability Spearman, return Spearman, 2 normalised-rank tail contrasts at
        the actual exclusion, median log-return contrast, crash share retained, crash share
        excluded, excluded rows in this sample]``.
    """
    n = matrix.shape[0]
    ranks = rankdata(matrix[:, :4], axis=0)
    centred = ranks - ranks.mean(axis=0)
    norms = np.sqrt((centred ** 2).sum(axis=0))
    norms[norms == 0] = np.nan
    correlations = (centred[:, 1:] * centred[:, :1]).sum(axis=0) / (norms[1:] * norms[0])
    # Stability: positive = the signal's stable end had the more stable outcome. Return: the
    # stable end is the HIGH-signal end under direction 'low', so positive raw correlation means
    # it earned more, and `-sign` keeps that orientation (as harness_rules_v2).
    out = np.full(len(STAT_NAMES), np.nan)
    out[0] = sign * correlations[0]
    out[1] = sign * correlations[1]
    out[2] = -sign * correlations[2]

    flag = matrix[:, 4] > 0.5
    excluded, retained = np.flatnonzero(flag), np.flatnonzero(~flag)
    out[8] = float(len(excluded))
    if len(excluded) >= 1 and len(retained) >= 1:
        normalised = (ranks - 1.0) / max(n - 1, 1)
        # Lower forward vol / downside is more stable, so retained-minus-excluded is negated to
        # make positive = the retained set was more stable.
        out[3] = -(normalised[retained, 1].mean() - normalised[excluded, 1].mean())
        out[4] = -(normalised[retained, 2].mean() - normalised[excluded, 2].mean())
        forward = matrix[:, 3]
        out[5] = float(np.median(forward[retained]) - np.median(forward[excluded]))
        out[6] = float(np.mean(forward[retained] < CRASH_LOG_RETURN))
        out[7] = float(np.mean(forward[excluded] < CRASH_LOG_RETURN))
    return out


def screen_table_v3(bootstrap: dict, margin: float = RETURN_MARGIN_LOG) -> tuple:
    """Result table and gate-5 verdicts under amendments A1 and A2.

    Three families, each a simultaneous max-T over the evaluated hypotheses on shared draws:
    stability (2 signals x 2 targets, GATED), returns (2 signals x 1 median contrast, GATED),
    tails (2 x 2 at the actual exclusion, DIAGNOSTIC).
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
    returns = family(["median_return_contrast"])
    tails = family([f"tail_{t}" for t in STABILITY_TARGETS])

    rows = []
    for i, signal in enumerate(SIGNAL_NAMES):
        sample = bootstrap["samples"][signal]
        row = {"signal": signal, "direction": SIGNAL_DIRECTION[signal],
               "rows": sample["rows"], "dates": sample["dates"]}
        for j, target in enumerate(STABILITY_TARGETS):
            row[f"rho_{target}"] = stability["observed"][i, j]
            row[f"lo_{target}"] = stability["lower_simultaneous"][i, j]
            row[f"p_{target}"] = stability["p"][i, j]
            row[f"tail_{target}"] = tails["observed"][i, j]
            row[f"tail_lo_{target}"] = tails["lower_simultaneous"][i, j]
        row["rho_forward_return"] = observed[i, index[f"spearman_{RETURN_TARGET}"]]
        row["median_return_contrast"] = returns["observed"][i, 0]
        row["median_return_lo"] = returns["lower_simultaneous"][i, 0]
        row["median_return_se"] = returns["se"][i, 0]
        row["crash_share_retained"] = observed[i, index["crash_share_retained"]]
        row["crash_share_excluded"] = observed[i, index["crash_share_excluded"]]
        row["excluded_in_sample_mean"] = observed[i, index["excluded_in_sample"]]
        enough = bool(evaluated_signal[i])
        in_family = bool(stability["member"][i].all() and returns["member"][i, 0])
        row["enough_dates"] = enough
        row["evaluated"] = bool(enough and in_family)
        stability_ok = bool(row["evaluated"] and all(
            np.isfinite(stability["lower_simultaneous"][i, j]) and stability["lower_simultaneous"][i, j] > 0.0
            for j in range(len(STABILITY_TARGETS))))
        return_ok = bool(row["evaluated"] and np.isfinite(returns["lower_simultaneous"][i, 0])
                         and returns["lower_simultaneous"][i, 0] > -float(margin))
        row["stability_clause"] = stability_ok
        row["return_clause"] = return_ok
        row["gate_5"] = bool(stability_ok and return_ok)
        rows.append(row)
    table = pd.DataFrame(rows).set_index("signal")
    detail = {"stability": stability, "returns": returns, "tails": tails, "margin": float(margin)}
    return table, detail


def run_screen_v3(panel_frame: pd.DataFrame, draws: int = SCREEN_DRAWS, seed: int = SCREEN_SEED,
                  verbose: bool = True) -> tuple:
    """Bootstrap and screen one panel under the plan 34 definitions. No target switching."""
    bootstrap = joint_cluster_bootstrap(panel_frame, draws=draws, seed=seed, verbose=verbose)
    table, detail = screen_table_v3(bootstrap)
    return table, detail, bootstrap


def family_summary(detail: dict) -> pd.DataFrame:
    rows = []
    for name in ("stability", "returns", "tails"):
        f = detail[name]
        rows.append({"family": name, "hypotheses_used": f["family_size_used"], "hypotheses_total": f["family_size_total"],
                     "critical": f["critical"], "complete_draws": f["n_draws"], "incomplete_draws": f["n_draws_incomplete"],
                     "gated": name != "tails"})
    return pd.DataFrame(rows).set_index("family")


# --------------------------------------------------------------------------------------------
# Coverage: which candidates each signal can score, and why the guard masks the rest.
# --------------------------------------------------------------------------------------------

def coverage_by_date(panel_frame: pd.DataFrame) -> pd.DataFrame:
    """Per decision date: pool size, finite `inverse_vol`, finite `calm_score`, both, only
    `inverse_vol` (= masked by the guard), neither."""
    rows = []
    for date, group in panel_frame.groupby("date"):
        iv = np.isfinite(group["inverse_vol"])
        cs = np.isfinite(group["calm_score"])
        rows.append({"date": pd.Timestamp(date), "pool": len(group), "inverse_vol": int(iv.sum()),
                     "calm_score": int(cs.sum()), "both": int((iv & cs).sum()),
                     "masked_by_guard": int((iv & ~cs).sum()), "calm_only": int((~iv & cs).sum()),
                     "neither": int((~iv & ~cs).sum()),
                     "regime": "post_break" if pd.Timestamp(date) >= POST_BREAK_START else "pre_break"})
    return pd.DataFrame(rows).set_index("date")


def guard_reasons(panel_frame: pd.DataFrame, pairs_by_id: dict, window: int = 90,
                  min_fresh: int = 30, max_stale: int = 10) -> pd.DataFrame:
    """For every (date, candidate) with finite `inverse_vol` and NaN `calm_score`: the fresh-mark
    count in the window and rows since the last fresh mark at T-1, and which guard fired.
    Recomputed here from the close series with the same helpers the indicator uses."""
    rows = []
    masked = panel_frame[np.isfinite(panel_frame["inverse_vol"]) & ~np.isfinite(panel_frame["calm_score"])]
    for pid, date, address in zip(masked["pair_id"], masked["date"], masked["address"]):
        close = close_series(pairs_by_id[pid])
        fresh = value_at_prior(_fresh_count(close, window), date)
        stale = value_at_prior(_rows_since_fresh(close), date)
        age = float((pd.Timestamp(date) - close.index[0]).days) if len(close) else float("nan")
        too_few = (not np.isfinite(fresh)) or fresh < min_fresh
        too_stale = (not np.isfinite(stale)) or stale > max_stale
        rows.append({"date": pd.Timestamp(date), "address": address, "age_days": age, "fresh_in_window": fresh,
                     "rows_since_fresh": stale,
                     "reason": "both" if (too_few and too_stale) else ("fewer_than_%d_fresh" % min_fresh if too_few
                                                                     else ("stale_over_%d_rows" % max_stale if too_stale else "unexplained")),
                     "regime": "post_break" if pd.Timestamp(date) >= POST_BREAK_START else "pre_break"})
    return pd.DataFrame(rows)


def vault_age_days(pairs_by_id: dict, panel_frame: pd.DataFrame) -> pd.Series:
    ages = []
    for pid, date in zip(panel_frame["pair_id"], panel_frame["date"]):
        close = close_series(pairs_by_id[pid])
        ages.append(float((pd.Timestamp(date) - close.index[0]).days) if len(close) else float("nan"))
    return pd.Series(ages, index=panel_frame.index)


print("harness_rules_v3.py: two-signal, two-target screen; actual-exclusion tail contrast at "
      f"{EXCLUSION_COUNT}; median return clause with margin {RETURN_MARGIN_LOG}; post-break scope from "
      f"{POST_BREAK_START.date()}.")
