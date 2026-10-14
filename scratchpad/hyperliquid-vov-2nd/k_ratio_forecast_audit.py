"""Independent numerical, source-compatibility and clock checks for experiment 09."""

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from k_ratio_features import ARTIFACT_DIR, GENERATION, START, END, WINDOWS, METRICS, k_statistics, window_metrics, sha256


def formula_audit():
    """Check OLS against an independent least-squares implementation."""
    rng = np.random.default_rng(109)
    returns = rng.normal(0.002, 0.015, 90)
    nav = np.exp(np.r_[0.0, np.cumsum(returns)])
    actual = k_statistics(nav)
    n = len(nav)
    x = np.column_stack([np.ones(n), np.arange(n)])
    y = np.log(nav)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    variance = np.sum(residual**2) / (n - 2)
    se = np.sqrt(variance * np.linalg.inv(x.T @ x)[1, 1])
    expected = beta[1] / se * np.sqrt(365) / n
    r = np.corrcoef(np.arange(n), y)[0, 1]
    identity = r * np.sqrt((n - 2) / (1 - r * r)) * np.sqrt(365) / n
    altered = np.exp(np.r_[0.0, np.cumsum(returns + np.r_[0.2, np.zeros(89)])])
    gap = nav.copy()
    gap[20] = np.nan
    result = {
        "independent_OLS": bool(np.isclose(actual["K-ratio"][0], expected, atol=1e-10)),
        "signed_R2_identity": bool(np.isclose(expected, identity, atol=1e-10)),
        "scale_invariance": bool(np.isclose(actual["K-ratio"][0], k_statistics(nav * 1e-9)["K-ratio"][0], rtol=1e-10)),
        "first_return_changes_primary_K": bool(not np.isclose(actual["K-ratio"][0], k_statistics(altered)["K-ratio"][0])),
        "ends_only_excludes_first_return": bool(np.isclose(k_statistics(nav, include_anchor=False)["K-ratio"][0], k_statistics(altered, include_anchor=False)["K-ratio"][0])),
        "flat_is_undefined": bool(np.isnan(k_statistics(np.ones(31))["K-ratio"][0])),
        "exact_linear_log_path_is_undefined": bool(np.isnan(k_statistics(np.exp(np.arange(31) * 0.01))["K-ratio"][0])),
        "negative_path_negative_K": bool(k_statistics(1 / nav)["K-ratio"][0] < 0),
        "general_return_permutation_changes_K": bool(not np.isclose(actual["K-ratio"][0], k_statistics(np.exp(np.r_[0.0, np.cumsum(rng.permutation(returns))]))["K-ratio"][0])),
        "complete_return_reversal_preserves_anchor_K": bool(np.isclose(actual["K-ratio"][0], k_statistics(np.exp(np.r_[0.0, np.cumsum(returns[::-1])]))["K-ratio"][0])),
        "missing_day_forward_filled_without_compression": bool(np.isclose(k_statistics(gap)["K-ratio"][0], k_statistics(pd.Series(gap).ffill().to_numpy())["K-ratio"][0])),
        "leading_missing_day_not_backfilled": bool(np.isnan(k_statistics(np.r_[np.nan, nav])["K-ratio"][0])),
        "zero_risk_Sharpe_undefined": bool(np.isnan(window_metrics(np.ones((31, 1)))["Sharpe"][0])),
        "fit_observations": n,
        "advertised_returns": n - 1,
        "primary_K": expected,
    }
    sparse = nav.copy()
    sparse[[12, 13, 40, 66]] = np.nan
    expected_path = pd.Series(sparse).ffill().to_numpy()[:, None]
    sparse_values = window_metrics(sparse[:, None])
    expected_values = window_metrics(expected_path)
    result["all_metric_families_match_manual_forward_fill"] = bool(all(np.allclose(sparse_values[key], expected_values[key], equal_nan=True) for key in ("CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar")))
    result["sparse_K_matches_manual_forward_fill"] = bool(np.allclose(k_statistics(sparse)["K-ratio"], k_statistics(expected_path)["K-ratio"], equal_nan=True))
    truncated = sparse[:45]
    result["future_changes_do_not_change_past_fills"] = bool(np.allclose(window_metrics(truncated[:, None])["CAGR"], window_metrics(expected_path[:45])["CAGR"], equal_nan=True))
    checks = [key for key, value in result.items() if isinstance(value, bool)]
    assert all(result[key] for key in checks), result
    return result


def audit_dataset(data):
    """Recompute source values and genuine labels through independent paths."""
    fingerprint = sha256(__file__) + data["manifest"]["module_sha256"]
    audit_file = ARTIFACT_DIR / "audit.json"
    if audit_file.exists():
        saved = json.loads(audit_file.read_text())
        if saved.get("fingerprint") == fingerprint:
            return pd.DataFrame({"Check": saved.keys(), "Result": [str(value) for value in saved.values()]})
    checks = formula_audit()
    src = data["source_features"]
    source_reference = data["source_reference"].set_index(["origin_at", "pair_id"])
    features = data["features"]
    identities = features[["pair_id", "vault_address"]].drop_duplicates().sort_values("vault_address")
    ids = identities.pair_id.tolist()
    candle_prices = pd.read_parquet(GENERATION / "08/prices.parquet")
    candle_nav = candle_prices.pivot(index="date", columns="pair_id", values="source_close").reindex(columns=ids)
    candle_returns = candle_nav.pct_change(fill_method=None)
    with np.load(next((GENERATION / "05").glob("features-*.npz"))) as cache:
        old = cache["raw"]
        assert old.shape[1] == len(ids)
        start = pd.Timestamp("2023-03-01")
        source_checks = []
        for record in src[(src.origin_at >= START) & (src.origin_at <= END - pd.Timedelta(days=1))].sample(100, random_state=109).itertuples(index=False):
            date, pid = record.origin_at, record.pair_id
            row = src[(src.origin_at == date) & (src.pair_id == pid)].iloc[0]
            i = int((date - start).days)
            j = ids.index(pid)
            periods = (30, 45, 46, 60, 90, 120, 180, 270, 360, 730)
            for k, days in enumerate(periods):
                for m, metric in enumerate(METRICS):
                    value = row[f"{days}d {metric}"]
                    expected = old[i, j, k * 5 + m]
                    match = (np.isnan(value) and np.isnan(expected)) or np.isclose(value, expected, rtol=1e-7, atol=1e-7)
                    independent = source_reference.loc[(date, pid), f"{days}d {metric}"]
                    sigma = candle_returns.loc[date - pd.Timedelta(days=days) : date - pd.Timedelta(days=1), pid].std(ddof=1)
                    low_risk = metric in ("Sharpe", "Sortino") and np.isfinite(sigma) and sigma < 0.0001
                    tol = 1e-3 if low_risk else 1e-7
                    independent_match = (np.isnan(independent) and np.isnan(expected)) or np.isclose(independent, expected, rtol=tol, atol=tol)
                    source_checks.append({"origin_at": date, "pair_id": pid, "feature": f"{days}d {metric}", "matches": bool(match), "direct_window_matches_tolerance": bool(independent_match), "absolute_error": abs(value - expected) if np.isfinite(value) and np.isfinite(expected) else np.nan, "daily_sigma": sigma, "low_risk_rolling_precision_case": bool(low_risk), "direct_window_absolute_error": abs(independent - expected) if np.isfinite(independent) and np.isfinite(expected) else np.nan})
    sf = pd.DataFrame(source_checks)
    assert sf.matches.all(), sf[~sf.matches].head().to_dict("records")
    assert sf.direct_window_matches_tolerance.all(), sf[~sf.direct_window_matches_tolerance].head().to_dict("records")
    sf.to_csv(ARTIFACT_DIR / "05-source-feature-audit.csv", index=False)
    checks["05_cached_feature_cells_match"] = len(sf)
    checks["source_direct_window_max_absolute_rounding_difference"] = float(sf.direct_window_absolute_error.max())
    checks["source_direct_window_precision_tolerance"] = "atol=rtol=1e-7; 1e-3 only for Sharpe/Sortino with daily sigma<0.0001 (rolling precision); exact frozen values also checked"
    daily = data["daily"].set_index(["pair_id", "date"])
    #: Recompute full recorded-history fits independently, including incomplete paths.
    max_candidates = features[features.origin_at.ge(START)]
    max_sample = pd.concat([max_candidates[max_candidates["max K-ratio"].notna()].sample(min(30, int(max_candidates["max K-ratio"].notna().sum())), random_state=109), max_candidates[max_candidates["max K-ratio"].isna()].sample(min(20, int(max_candidates["max K-ratio"].isna().sum())), random_state=110)])
    max_checks = []
    for _, row in max_sample.iterrows():
        marks = daily.loc[row.pair_id].sort_index()
        anchor = row.origin_at - pd.Timedelta(days=1)
        first = marks.index.min()
        expected = np.nan
        if anchor >= first:
            path = marks.share_price.reindex(pd.date_range(first, anchor)).ffill().to_numpy(dtype=float)
            n = len(path)
            if n >= 3 and np.isfinite(path).all():
                x = np.column_stack([np.ones(n), np.arange(n)])
                y = np.log(path)
                beta = np.linalg.lstsq(x, y, rcond=None)[0]
                residual = y - x @ beta
                sse = np.dot(residual, residual)
                syy = np.dot(y - y.mean(), y - y.mean())
                if sse > (np.finfo(float).eps * 32) ** 2 * max(syy, 1.0):
                    se = np.sqrt(sse / (n - 2) * np.linalg.inv(x.T @ x)[1, 1])
                    expected = beta[1] / se * np.sqrt(365) / n
        observed = row["max K-ratio"]
        match = (np.isnan(expected) and np.isnan(observed)) or np.isclose(expected, observed, rtol=1e-7, atol=1e-8)
        assert match, (row.origin_at, row.pair_id, expected, observed)
        max_checks.append(match)
    checks["independently_recomputed_max_k_rows"] = len(max_checks)
    checks["max_k_full_recorded_history_matches"] = bool(all(max_checks))
    labels = data["labels"]
    candidates = labels[(labels.origin_at >= START) & labels.delay.eq(0)]
    selected = pd.concat([g.sample(min(4, len(g)), random_state=109) for _, g in candidates.groupby(["horizon", "status"])])
    finite = candidates[np.isfinite(candidates["K-ratio"])]
    selected = pd.concat([selected, finite.sample(min(30, len(finite)), random_state=110)]).drop_duplicates(["origin_at", "pair_id", "horizon"])
    label_checks = []
    for row in selected.itertuples(index=False):
        path = pd.date_range(row.anchor_at, row.target_end_at)
        if row.pair_id in daily.index.get_level_values(0):
            marks = daily.loc[row.pair_id].sort_index()
            calendar = pd.date_range(marks.index.min(), max(row.target_end_at, marks.index.max()))
            piece = marks.reindex(calendar).ffill().reindex(path)
            if row.target_end_at > marks.index.max():
                piece["share_price"] = np.nan
        else:
            piece = pd.DataFrame(index=path, columns=["share_price", "timestamp"])
        nav = piece.share_price.to_numpy(dtype=float)
        endpoint_valid = row.target_end_at < END and np.isfinite(nav[[0, -1]]).all()
        log_return = np.log(nav[-1] / nav[0]) if endpoint_valid else np.nan
        full = endpoint_valid and np.isfinite(nav).all()
        sharpe = np.nan
        k = np.nan
        if full:
            ret = np.diff(nav) / nav[:-1]
            if ret.std(ddof=1) > 0:
                sharpe = ret.mean() / ret.std(ddof=1) * np.sqrt(365)
            x = np.column_stack([np.ones(len(nav)), np.arange(len(nav))])
            y = np.log(nav)
            beta = np.linalg.lstsq(x, y, rcond=None)[0]
            residual = y - x @ beta
            sse = np.dot(residual, residual)
            centered = y - y.mean()
            tolerance = (np.finfo(float).eps * 32) ** 2 * max(np.dot(centered, centered), 1.0)
            if sse > tolerance:
                se = np.sqrt(sse / (len(nav) - 2) * np.linalg.inv(x.T @ x)[1, 1])
                k = beta[1] / se * np.sqrt(365) / len(nav)
        matches = {}
        for name, expected in [("log_return", log_return), ("Sharpe", sharpe), ("K-ratio", k)]:
            observed = getattr(row, name.replace("-", "_"), None) if name != "K-ratio" else labels.loc[(labels.origin_at == row.origin_at) & (labels.pair_id == row.pair_id) & labels.horizon.eq(row.horizon) & labels.delay.eq(0), name].iloc[0]
            matches[name] = bool((np.isnan(expected) and np.isnan(observed)) or np.isclose(expected, observed, rtol=1e-8, atol=1e-8))
        assert all(matches.values()), (row.origin_at, row.pair_id, matches)
        label_checks.append({"origin_at": row.origin_at, "pair_id": row.pair_id, "horizon": row.horizon, "status": row.status, "matches": all(matches.values())})
    pd.DataFrame(label_checks).to_csv(ARTIFACT_DIR / "independent-label-audit.csv", index=False)
    checks["independently_recomputed_labels"] = len(label_checks)
    checks["label_clock_convention_end_plus_one_day"] = bool((labels.target_end_at < labels.label_available_at).all())
    checks["young_vault_partial_feature_rows"] = int(((features.age_days < 180) & (features.age_days >= 30) & (features.observed_inputs > 0) & features[f"180d CAGR"].isna()).sum())
    right = labels.status.eq("administrative_censoring")
    assert not np.isfinite(labels.loc[right, ["log_return", "Sharpe", "K-ratio"]].to_numpy()).any()
    incomplete = ~labels.status.eq("complete")
    assert not np.isfinite(labels.loc[incomplete, ["Sharpe", "K-ratio"]].to_numpy()).any()
    checks["right_censored_labels_have_no_fabricated_targets"] = True
    checks["unsupported_or_terminal_paths_have_no_fabricated_Sharpe_or_K"] = True
    checks["fingerprint"] = fingerprint
    (ARTIFACT_DIR / "audit.json").write_text(json.dumps(checks, indent=2))
    return pd.DataFrame({"Check": checks.keys(), "Result": [str(value) for value in checks.values()]})


def compatibility_ic(data):
    """Reproduce the old 14/30/60-day source-price audit on its shared origins."""
    fingerprint = sha256(__file__) + data["manifest"]["module_sha256"]
    cache = ARTIFACT_DIR / "05-compatibility-manifest.json"
    if cache.exists() and json.loads(cache.read_text()).get("fingerprint") == fingerprint:
        result = pd.read_parquet(ARTIFACT_DIR / "05-compatibility-ic.parquet")
        return pd.DataFrame([{"Compared IC cells": len(result), "Matched": int(result.matches.sum()), "Maximum absolute error": result.absolute_error.max(), "Old horizons (days)": "14 / 30 / 60"}])
    src = data["source_features"].set_index(["origin_at", "pair_id"])
    prices = pd.read_parquet(GENERATION / "08/prices.parquet")
    ids = data["features"][["pair_id", "vault_address"]].drop_duplicates().sort_values("vault_address").pair_id.tolist()
    nav = prices.pivot(index="date", columns="pair_id", values="source_close").reindex(columns=ids)
    ret = nav.pct_change(fill_method=None)
    old_ic = pd.read_csv(GENERATION / "05/features-555f345396445f0a/ic.csv", parse_dates=["Date"])
    eligibility = data["eligibility"]
    eligible = eligibility[(eligibility.origin_at >= START) & eligibility.source_inclusion & eligibility.gate_passes & eligibility.current_guard_allows & ~eligibility.blacklisted & ~eligibility.quarantined]
    period_labels = {30: "1m", 46: "46d", 60: "2m", 90: "3m", 120: "4m", 180: "6m", 270: "9m", 360: "1y", 730: "2y"}
    rows = []
    from tqdm_loggable.auto import tqdm

    for origin, group in tqdm(list(eligible.groupby("origin_at")), desc="05 original IC compatibility; estimated 1 minute", mininterval=15):
        pids = group.pair_id.tolist()
        if len(pids) < 10:
            continue
        for h in (14, 30, 60):
            if origin + pd.Timedelta(days=h) > END:
                continue
            anchor = origin - pd.Timedelta(days=1)
            forward = nav.shift(-h).loc[anchor, pids] / nav.loc[anchor, pids] - 1
            future = ret.shift(-h)
            mean = future.rolling(h, min_periods=h).mean().loc[anchor, pids]
            std = future.rolling(h, min_periods=h).std().loc[anchor, pids].replace(0, np.nan)
            sharpe = mean / std * np.sqrt(365)
            for days, period in period_labels.items():
                for metric in METRICS:
                    x = src.loc[(origin, pids), f"{days}d {metric}"].to_numpy()
                    for outcome, target in [("Forward return", forward), ("Forward Sharpe", sharpe)]:
                        y = target.to_numpy()
                        good = np.isfinite(x) & np.isfinite(y)
                        if good.sum() < 10 or np.unique(x[good]).size < 2 or np.unique(y[good]).size < 2:
                            continue
                        reference = old_ic[(old_ic.Date == origin) & old_ic.Period.eq(period) & old_ic.Metric.eq(metric) & old_ic.Horizon.eq(h) & old_ic.Outcome.eq(outcome)]
                        if len(reference):
                            rho = spearmanr(x[good], y[good]).statistic
                            rows.append({"origin_at": origin, "days": days, "metric": metric, "horizon": h, "outcome": outcome, "matches": bool(np.isclose(rho, reference.IC.iloc[0], atol=1e-10)), "absolute_error": abs(rho - reference.IC.iloc[0])})
    result = pd.DataFrame(rows)
    assert len(result) and result.matches.all(), result[~result.matches].head().to_dict("records")
    result.to_parquet(ARTIFACT_DIR / "05-compatibility-ic.parquet", index=False)
    cache.write_text(json.dumps({"fingerprint": fingerprint}, indent=2))
    return pd.DataFrame([{"Compared IC cells": len(result), "Matched": int(result.matches.sum()), "Maximum absolute error": result.absolute_error.max(), "Old horizons (days)": "14 / 30 / 60"}])
