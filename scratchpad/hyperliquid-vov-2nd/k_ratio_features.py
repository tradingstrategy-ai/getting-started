"""Audited individual vault features and future labels for experiment 09."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from numpy.lib.stride_tricks import sliding_window_view
from tqdm_loggable.auto import tqdm

ROOT = Path(__file__).resolve().parent
GENERATION = ROOT / "_artifacts-restored-2026-10-07"
ARTIFACT_DIR = GENERATION / "09"
START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-10-05")
LONG_START = pd.Timestamp("2023-03-01")
PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
LONG_PERIOD = "2023-03-01 → 2026-10-05 (end exclusive, UTC)"
WINDOWS = (30, 46, 60, 90, 120, 180, 270, 360, 730)
METRICS = ("CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar")
EXISTING = [f"{days}d {metric}" for days in WINDOWS for metric in METRICS]
K_SHORT = [f"{days}d K-ratio" for days in (30, 60, 90, 180)]
K_YEAR = "360d K-ratio"
K_MAX = "max K-ratio"
K_MAIN = K_SHORT + [K_YEAR, K_MAX]
K_ALL = [f"{days}d K-ratio" for days in WINDOWS] + [K_MAX]
COMPATIBLE = [f"45d {metric}" for metric in METRICS]
TARGETS = ("CAGR", "Sharpe", "K-ratio")
HORIZONS = (7, 30, 90)
VERSION = "09-causal-sparse-fill-v4"


def sha256(path):
    """Fingerprint a local pinned input without fetching a new generation."""
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def forward_fill_nav(nav):
    """Carry positive NAV forward on the calendar grid, without backfilling.

    Missing leading marks stay missing. Observation masks must be retained
    separately; carrying a price does not create a new observation.
    """
    nav = np.asarray(nav, dtype=float)
    if nav.ndim == 1:
        nav = nav[:, None]
    valid = np.isfinite(nav) & (nav > 0)
    rows = np.arange(len(nav))[:, None]
    last = np.maximum.accumulate(np.where(valid, rows, -1), axis=0)
    return np.where(last >= 0, nav[np.maximum(last, 0), np.arange(nav.shape[1])], np.nan)


def k_statistics(nav, frequency=365.0, include_anchor=True):
    """Return intercept OLS diagnostics, one column per complete positive path.

    :param nav: Equally spaced wealth marks, including the initial anchor.
    :param include_anchor: Include every advertised return in the fitted path.
    """
    nav = forward_fill_nav(nav)
    count = nav.shape[1]
    result = {key: np.full(count, np.nan) for key in ("K-ratio", "slope", "slope_se", "signed_r2", "residual_scale")}
    result["reason"] = np.full(count, "incomplete_observations", dtype=object)
    good = np.isfinite(nav).all(axis=0) & (nav > 0).all(axis=0)
    if not good.any():
        return result
    wealth = np.log(nav[:, good])
    if not include_anchor:
        wealth = wealth[1:]
    n = len(wealth)
    if n < 3:
        result["reason"][good] = "too_few_fitted_points"
        return result
    x = np.arange(n, dtype=float)
    x -= x.mean()
    y = wealth - wealth.mean(axis=0)
    sxx = np.dot(x, x)
    slope = np.sum(x[:, None] * y, axis=0) / sxx
    residual = y - x[:, None] * slope
    sse = np.sum(residual**2, axis=0)
    syy = np.sum(y**2, axis=0)
    se = np.sqrt(sse / (n - 2) / sxx)
    tolerance = (np.finfo(float).eps * 32) ** 2 * np.maximum(syy, 1.0)
    nondegenerate = (sse > tolerance) & (se > 0)
    k = np.full(len(slope), np.nan)
    k[nondegenerate] = slope[nondegenerate] / se[nondegenerate] * np.sqrt(frequency) / n
    r2 = np.divide(slope**2 * sxx, syy, out=np.zeros_like(slope), where=syy > 0)
    for key, value in [("K-ratio", k), ("slope", slope), ("slope_se", se), ("signed_r2", np.sign(slope) * np.clip(r2, 0, 1)), ("residual_scale", np.sqrt(sse / (n - 2)))]:
        result[key][good] = value
    reason = np.where(nondegenerate, "defined", "zero_or_numerically_degenerate_slope_se")
    result["reason"][good] = reason
    return result


def window_metrics(nav):
    """Calculate all return/risk metrics on causally filled daily paths."""
    nav = forward_fill_nav(nav)
    n = nav.shape[1]
    values = {metric: np.full(n, np.nan) for metric in METRICS}
    values.update({key: np.full(n, np.nan) for key in ("Sharpe floor", "Sortino floor", "Calmar unfloored", "log_return", "volatility", "mean_return", "flat_fraction", "nonzero_returns")})
    complete = np.isfinite(nav).all(axis=0) & (nav > 0).all(axis=0)
    values["complete"] = complete
    if complete.any():
        p = nav[:, complete]
        returns = p[1:] / p[:-1] - 1
        mean = returns.mean(axis=0)
        sigma = returns.std(axis=0, ddof=1)
        downside = np.sqrt(np.mean(np.minimum(returns, 0) ** 2, axis=0))
        dd = np.min(p / np.maximum.accumulate(p, axis=0) - 1, axis=0)
        logret = np.log(p[-1] / p[0])
        with np.errstate(over="ignore"):
            cagr = np.expm1(logret * 365 / (len(nav) - 1))
        cagr[~np.isfinite(cagr)] = np.nan
        for key, value in [("CAGR", cagr), ("Max drawdown", dd), ("Calmar", cagr / np.maximum(np.abs(dd), 0.01)), ("log_return", logret), ("volatility", sigma), ("mean_return", mean), ("flat_fraction", np.mean(np.abs(returns) <= 1e-12, axis=0)), ("nonzero_returns", np.sum(np.abs(returns) > 1e-12, axis=0)), ("Sharpe floor", mean / np.maximum(sigma, 0.0001) * np.sqrt(365)), ("Sortino floor", mean / np.maximum(downside, 0.0001) * np.sqrt(365))]:
            values[key][complete] = value
        for metric, denominator in [("Sharpe", sigma), ("Sortino", downside), ("Calmar unfloored", np.abs(dd))]:
            numerator = cagr if metric == "Calmar unfloored" else mean * np.sqrt(365)
            values[metric][complete] = np.divide(numerator, denominator, out=np.full(len(p[0]), np.nan), where=denominator > 0)
    return values


def raw_inputs():
    """Read original observations; cached 08 files provide identity/audit only."""
    downloads = json.loads((GENERATION / "inputs/downloads.json").read_text())
    price_path = Path(downloads["vault_prices"]["path"])
    assert sha256(price_path) == downloads["vault_prices"]["sha256"], "Pinned archive changed"
    audit_prices = pd.read_parquet(GENERATION / "08/prices.parquet")
    eligibility = pd.read_parquet(GENERATION / "08/eligibility.parquet")
    identities = eligibility[["pair_id", "vault_address", "vault_name"]].drop_duplicates().sort_values("vault_address")
    assert not identities.pair_id.duplicated().any()
    dataset = ds.dataset(price_path, format="parquet")
    raw = dataset.to_table(columns=["timestamp", "address", "share_price"], filter=(ds.field("chain") == 9999) & ds.field("address").isin(identities.vault_address.tolist())).to_pandas().reset_index()
    raw["timestamp"] = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(None)
    raw = raw[np.isfinite(raw.share_price) & raw.share_price.gt(0)].copy()
    raw["date"] = raw.timestamp.dt.floor("D")
    raw = raw.sort_values(["address", "timestamp"], kind="stable")
    daily = raw.groupby(["address", "date"], sort=False).tail(1)
    daily = daily.merge(identities, left_on="address", right_on="vault_address", validate="many_to_one")
    daily = daily[daily.date < END]
    check = daily.merge(audit_prices[["date", "pair_id", "raw_close", "observed_at"]], on=["date", "pair_id"], how="inner", validate="one_to_one")
    assert np.allclose(check.share_price, check.raw_close, rtol=1e-12, atol=1e-14)
    assert (check.timestamp == check.observed_at).all()
    dates = pd.date_range(min(LONG_START - pd.Timedelta(days=731), daily.date.min()), END - pd.Timedelta(days=1))
    ids = identities.pair_id.tolist()
    nav = daily.pivot(index="date", columns="pair_id", values="share_price").reindex(index=dates, columns=ids)
    observed = daily.pivot(index="date", columns="pair_id", values="timestamp").reindex(index=dates, columns=ids)
    source = audit_prices.pivot(index="date", columns="pair_id", values="source_close").reindex(index=dates, columns=ids)
    first = daily.groupby("pair_id").date.min().reindex(ids)
    last = daily.groupby("pair_id").date.max().reindex(ids)
    raw_nav = nav.copy()
    nav = nav.ffill()
    return {"nav": nav, "raw_nav": raw_nav, "observed": observed, "source": source, "daily": daily, "identities": identities, "eligibility": eligibility, "first": first, "last": last, "downloads": downloads, "raw_mapping_checks": len(check)}


def build_features(inputs):
    """Compute genuine features at T-1, plus a source-compatible audit panel."""
    all_origins = pd.date_range(START, END - pd.Timedelta(days=1))
    long_origins = pd.date_range(LONG_START + pd.Timedelta(days=1), START - pd.Timedelta(days=1), freq="4D")
    origins = all_origins.union(long_origins)
    nav = inputs["nav"].to_numpy()
    source = inputs["source"].to_numpy()
    dates = inputs["nav"].index
    ids = inputs["identities"].pair_id.to_numpy()
    last_observed = inputs["observed"].ffill()
    first_indices = dates.get_indexer(inputs["first"])
    actual_nav = inputs["raw_nav"].to_numpy()
    actual_counts = np.cumsum(np.isfinite(actual_nav), axis=0)
    nonzero = np.isfinite(nav[1:]) & np.isfinite(nav[:-1]) & (np.abs(nav[1:] / np.where(nav[:-1] > 0, nav[:-1], np.nan) - 1) > 1e-12)
    nonzero_counts = np.vstack([np.zeros((1, len(ids)), dtype=int), np.cumsum(nonzero, axis=0)])
    chunks = []
    source_chunks = []
    reason_chunks = []
    for origin in tqdm(origins, desc="09 causal daily features; estimated 1–3 minutes", mininterval=15):
        anchor = origin - pd.Timedelta(days=1)
        ai = dates.get_loc(anchor)
        feature = {"origin_at": origin, "pair_id": ids}
        source_feature = {"origin_at": origin, "pair_id": ids}
        history = nav[max(0, ai - 89) : ai + 1]
        age = (anchor - inputs["first"]).dt.days.to_numpy()
        observed_history = np.isfinite(actual_nav[max(0, ai - 89) : ai + 1])
        last_at = last_observed.iloc[ai]
        feature["age_days"] = age.astype(float)
        feature["observed_fraction_90"] = observed_history.sum(axis=0) / 90
        feature["freshness_hours"] = (origin - last_at).dt.total_seconds().to_numpy() / 3600
        feature["anchor_supported"] = np.isfinite(nav[ai])
        feature["anchor_actually_observed"] = np.isfinite(actual_nav[ai])
        feature["anchor_forward_filled"] = feature["anchor_supported"] & ~feature["anchor_actually_observed"]
        feature["phase"] = int((origin - START).days % 4)
        #: Full recorded history, never a trailing contiguous subset or compressed gap.
        max_days = ai - first_indices
        max_complete = (first_indices >= 0) & (max_days >= 2) & np.isfinite(nav[ai])
        feature["max days"] = np.where(max_days >= 0, max_days, np.nan)
        feature["max complete"] = max_complete
        feature["max observed_marks"] = actual_counts[ai]
        feature["max filled_marks"] = np.where(max_complete, max_days + 1 - actual_counts[ai], 0)
        feature["max nonzero_returns"] = np.where(max_complete, nonzero_counts[ai], np.nan)
        for key in ("K-ratio", "slope", "slope_se", "signed_r2", "residual_scale"):
            feature[f"max {key}"] = np.full(len(ids), np.nan)
        feature["max reason"] = np.where(max_days < 2, "insufficient_recorded_history", "missing_daily_observations").astype(object)
        for first_index in np.unique(first_indices[max_complete]):
            choose = max_complete & (first_indices == first_index)
            full = k_statistics(nav[first_index : ai + 1, choose])
            for key in ("K-ratio", "slope", "slope_se", "signed_r2", "residual_scale"):
                feature[f"max {key}"][choose] = full[key]
            feature["max reason"][choose] = full["reason"]
        flat_run = np.zeros(len(ids), dtype=int)
        longest_run = flat_run.copy()
        for mark in range(max(1, ai - 89), ai + 1):
            equal = np.isfinite(nav[mark]) & np.isfinite(nav[mark - 1]) & (np.abs(nav[mark] / np.where(nav[mark - 1] > 0, nav[mark - 1], np.nan) - 1) <= 1e-12)
            flat_run = np.where(equal, flat_run + 1, 0)
            longest_run = np.maximum(longest_run, flat_run)
        feature["longest_recent_flat_run"] = longest_run
        for days in (*WINDOWS, 45, 7):
            path = nav[ai - days : ai + 1]
            values = window_metrics(path)
            k = k_statistics(path)
            for metric in METRICS:
                feature[f"{days}d {metric}"] = values[metric]
            for key in ("Sharpe floor", "Sortino floor", "Calmar unfloored"):
                feature[f"{days}d {key}"] = values[key]
            for key in ("K-ratio", "slope", "slope_se", "signed_r2", "residual_scale"):
                feature[f"{days}d {key}"] = k[key]
            feature[f"{days}d K-ends-only"] = k_statistics(path, include_anchor=False)["K-ratio"]
            feature[f"{days}d complete"] = values["complete"]
            feature[f"{days}d log_return"] = values["log_return"]
            feature[f"{days}d nonzero_returns"] = values["nonzero_returns"]
            if days in WINDOWS or days == 45:
                src = window_metrics(source[ai - days : ai + 1])
                for metric in METRICS:
                    source_feature[f"{days}d {metric}"] = src[metric]
                for metric in ("Sharpe floor", "Sortino floor"):
                    source_feature[f"{days}d {metric}"] = src[metric]
                for metric in (*METRICS, "K-ratio"):
                    vector = k["K-ratio"] if metric == "K-ratio" else values[metric]
                    reason = np.where(np.isfinite(vector), "defined", "undefined_ratio")
                    reason = np.where(~values["complete"], "missing_daily_observations", reason)
                    reason = np.where(age < days, "insufficient_age", reason)
                    if metric == "K-ratio":
                        reason = np.where(values["complete"] & ~np.isfinite(vector), k["reason"], reason)
                    counts = pd.Series(reason).value_counts()
                    reason_chunks.append(pd.DataFrame({"origin_at": origin, "days": days, "metric": metric, "reason": counts.index, "vaults": counts.to_numpy()}))
        path30 = nav[ai - 30 : ai + 1]
        m30 = window_metrics(path30)
        feature["flat_fraction_30"] = m30["flat_fraction"]
        feature["volatility_30"] = m30["volatility"]
        feature["mean_return_30"] = m30["mean_return"]
        feature["ewma_volatility_30"] = np.full(len(ids), np.nan)
        feature["positive_fraction_30"] = np.full(len(ids), np.nan)
        feature["autocorrelation_30"] = np.full(len(ids), np.nan)
        feature["variance_ratio_30"] = np.full(len(ids), np.nan)
        good = m30["complete"]
        if good.any():
            rr = path30[1:, good] / path30[:-1, good] - 1
            feature["positive_fraction_30"][good] = np.mean(rr > 0, axis=0)
            ew = 0.94 ** np.arange(29, -1, -1, dtype=float)
            ew /= ew.sum()
            ew_mean = np.sum(rr * ew[:, None], axis=0)
            feature["ewma_volatility_30"][good] = np.sqrt(np.sum(ew[:, None] * (rr - ew_mean) ** 2, axis=0))
            left = rr[:-1] - rr[:-1].mean(axis=0)
            right = rr[1:] - rr[1:].mean(axis=0)
            denom = np.sqrt(np.sum(left**2, axis=0) * np.sum(right**2, axis=0))
            feature["autocorrelation_30"][good] = np.divide(np.sum(left * right, axis=0), denom, out=np.full(good.sum(), np.nan), where=denom > 0)
            lr = np.log(path30[1:, good] / path30[:-1, good])
            block = sliding_window_view(lr, 5, axis=0).sum(axis=-1)
            variance = np.var(lr, axis=0, ddof=1)
            feature["variance_ratio_30"][good] = np.divide(np.var(block, axis=0, ddof=1), 5 * variance, out=np.full(good.sum(), np.nan), where=variance > 0)
        for days in (30, 60, 90, 180):
            offsets = np.arange(0, days + 1, 7)
            path = nav[ai - offsets[::-1]]
            feature[f"{days}d weekly K-ratio"] = k_statistics(path, frequency=365 / 7)["K-ratio"]
        chunks.append(pd.DataFrame(feature))
        source_chunks.append(pd.DataFrame(source_feature))
    features = pd.concat(chunks, ignore_index=True)
    features["origin_quarter"] = features.origin_at.dt.to_period("Q").astype(str)
    features["observed_inputs"] = features[EXISTING].notna().sum(axis=1)
    features["available_windows"] = features[[f"{d}d complete" for d in WINDOWS]].sum(axis=1)
    features = features.merge(inputs["identities"], on="pair_id", validate="many_to_one")
    source_frame = pd.concat(source_chunks, ignore_index=True)
    source_reference = source_frame.copy()
    with np.load(next((GENERATION / "05").glob("features-*.npz"))) as stored:
        source_raw = stored["raw"]
        source_floors = stored["floored"]
        row_index = (source_frame.origin_at - LONG_START).dt.days.to_numpy()
        pair_index = source_frame.pair_id.map({pid: j for j, pid in enumerate(ids)}).to_numpy()
        for k, days in enumerate((30, 45, 46, 60, 90, 120, 180, 270, 360, 730)):
            for m, metric in enumerate(METRICS):
                source_frame[f"{days}d {metric}"] = source_raw[row_index, pair_index, k * 5 + m]
            for m, metric in enumerate(("Sharpe floor", "Sortino floor")):
                source_frame[f"{days}d {metric}"] = source_floors[row_index, pair_index, k * 2 + m]
    return features, source_frame, pd.concat(reason_chunks, ignore_index=True), source_reference


def build_labels(inputs, features):
    """Create calendar-horizon labels with causal carry and terminal censoring."""
    dates = inputs["nav"].index
    nav = inputs["nav"].to_numpy()
    actual_nav = inputs["raw_nav"].to_numpy()
    ids = inputs["identities"].pair_id.to_numpy()
    chunks = []
    origins = sorted(features.origin_at.unique())
    for origin in tqdm(origins, desc="09 genuine 7/30/90-day labels", mininterval=15):
        origin = pd.Timestamp(origin)
        for horizon in HORIZONS:
            for delay in (0, 1):
                anchor = origin - pd.Timedelta(days=1) + pd.Timedelta(days=delay)
                endpoint = anchor + pd.Timedelta(days=horizon)
                vectors = {target: np.full(len(ids), np.nan) for target in (*TARGETS, "log_return", "mean_return", "volatility", "K-ends-only")}
                counts = np.zeros(len(ids), dtype=int)
                nonzero = np.full(len(ids), np.nan)
                status = np.full(len(ids), "administrative_censoring", dtype=object)
                kreason = status.copy()
                if endpoint < END and anchor in dates:
                    ai = dates.get_loc(anchor)
                    path = nav[ai : ai + horizon + 1].copy()
                    terminal = endpoint > inputs["last"].to_numpy()
                    path[:, terminal] = np.nan
                    counts = np.isfinite(actual_nav[ai : ai + horizon + 1]).sum(axis=0)
                    measures = window_metrics(path)
                    k = k_statistics(path)
                    nonzero = measures["nonzero_returns"]
                    endpoints = np.isfinite(path[0]) & np.isfinite(path[-1])
                    lr = np.full(len(ids), np.nan)
                    lr[endpoints] = np.log(path[-1, endpoints] / path[0, endpoints])
                    vectors["log_return"] = lr
                    with np.errstate(over="ignore"):
                        vectors["CAGR"] = np.expm1(lr * 365 / horizon)
                    vectors["CAGR"][~np.isfinite(vectors["CAGR"])] = np.nan
                    for target in ("Sharpe", "mean_return", "volatility"):
                        vectors[target] = measures[target]
                    vectors["K-ratio"] = k["K-ratio"]
                    vectors["K-ends-only"] = k_statistics(path, include_anchor=False)["K-ratio"]
                    status[:] = "missing_daily_observations"
                    status[endpoint > inputs["last"].to_numpy()] = "disappearance_or_terminal_coverage"
                    status[~np.isfinite(nav[ai])] = "missing_anchor_or_prelaunch"
                    status[endpoints] = "endpoints_only"
                    status[measures["complete"]] = "complete"
                    kreason = k["reason"]
                chunk = pd.DataFrame({"origin_at": origin, "pair_id": ids, "horizon": horizon, "delay": delay, "anchor_at": anchor, "target_end_at": endpoint, "label_available_at": endpoint + pd.Timedelta(days=1), "daily_marks": counts, "filled_marks": np.where(status == "complete", horizon + 1 - counts, 0), "actual_complete_path": counts == horizon + 1, "nonzero_returns": nonzero, "status": status, "k_reason": kreason, **vectors})
                chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)


def prepare_data():
    """Cache only under the ignored experiment namespace, with exact inputs."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    signature = sha256(__file__)
    manifest_path = ARTIFACT_DIR / "data-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("module_sha256") == signature:
            assert sha256(GENERATION / "inputs/vault-prices.parquet") == manifest["archive_sha256"]
            assert sha256(next((GENERATION / "05").glob("features-*.npz"))) == manifest["source_feature_cache_sha256"]
            assert sha256(GENERATION / "08/eligibility.parquet") == manifest["operational_audit_sha256"]
            return {key: pd.read_parquet(ARTIFACT_DIR / f"{key}.parquet") for key in ("features", "source_features", "source_reference", "reasons", "labels", "eligibility", "daily")} | {"manifest": manifest}
    inputs = raw_inputs()
    features, source, reasons, source_reference = build_features(inputs)
    labels = build_labels(inputs, features)
    manifest = {
        "version": VERSION,
        "module_sha256": signature,
        "archive_sha256": inputs["downloads"]["vault_prices"]["sha256"],
        "source_feature_cache_sha256": sha256(next((GENERATION / "05").glob("features-*.npz"))),
        "operational_audit_sha256": sha256(GENERATION / "08/eligibility.parquet"),
        "inputs": inputs["downloads"],
        "source_05_manifest": json.loads((GENERATION / "05/run-manifest.json").read_text()),
        "primary_period": [str(START), str(END)],
        "vaults": len(inputs["identities"]),
        "rows": len(features),
        "k_fit": "anchor included; n=L+1; ordinary intercept OLS; sqrt(365)/n; zero risk free",
        "primary_k_inputs": K_MAIN,
        "sparse_nav_policy": "Causal positive NAV forward fill; never backfill before first mark. Features may carry through T-1 with actual observation age recorded. Future labels are censored after each vault last actual mark and archive end. Flat/zero-denominator ratios remain missing.",
        "one_year_days": 360,
        "max_k_policy": "First actual positive daily NAV through T-1; causal forward fill on calendar days, at least three fitted points, no backfill or gap compression; recorded history is not certified inception",
        "mapping_checks": inputs["raw_mapping_checks"],
        "existing_features": EXISTING,
        "K_features": K_ALL,
        "activity_rule": "|daily return|>1e-12; exploratory sensitivity max(4,ceil(window/2)); not a stale-data assertion",
        "weekly_actual_spans_days": {"30": 28, "60": 56, "90": 84, "180": 175},
        "publication_caveat": "Observation-time replay; archived written_at is not a receipt clock; current snapshot is not a complete historical universe.",
    }
    data = {"features": features, "source_features": source, "source_reference": source_reference, "reasons": reasons, "labels": labels, "eligibility": inputs["eligibility"], "daily": inputs["daily"], "manifest": manifest}
    for key, frame in data.items():
        if isinstance(frame, pd.DataFrame):
            frame.to_parquet(ARTIFACT_DIR / f"{key}.parquet", index=False)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return data
