"""Causal rolling return and risk features for the rolling profit/risk track.

The functions in this module deliberately operate on observed share-price marks.
They do not use forward-filled values when estimating volatility, and every
feature uses marks strictly before the decision timestamp.
"""

from __future__ import annotations

import hashlib
import inspect
import time
from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import display
from tqdm_loggable.auto import tqdm

RISK_FLOOR = 0.05


def _daily_last(series: pd.Series) -> pd.Series:
    """Keep the last observed price per UTC day, retaining sparse observations."""
    s = series.dropna().sort_index()
    if len(s) == 0:
        return s
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    s = pd.Series(s.to_numpy(dtype=float), index=idx)
    return s.groupby(s.index.normalize()).last().sort_index()


def rolling_features(series: pd.Series, decision: pd.Timestamp, lookback_days: int) -> dict | None:
    """Calculate direct rolling features from observations before ``decision``.

    The first available mark at or before the rolling boundary is included as
    the left endpoint.  Interval lengths use elapsed days, so weekly marks are
    not treated as daily observations.  Volatility is missing for one interval
    because its residual variance is not identifiable from a single return.
    """
    decision = pd.Timestamp(decision).tz_localize(None) if pd.Timestamp(decision).tzinfo else pd.Timestamp(decision)
    daily = _daily_last(series)
    daily = daily.loc[daily.index < decision]
    if len(daily) < 2:
        return None
    right = daily.index[-1]
    left_boundary = decision.normalize() - pd.Timedelta(days=int(lookback_days))
    left_candidates = daily.loc[daily.index <= left_boundary]
    left = left_candidates.index[-1] if len(left_candidates) else daily.index[0]
    window = daily.loc[left:right]
    if len(window) < 2:
        return None
    prices = window.to_numpy(dtype=float)
    if not np.all(np.isfinite(prices)) or np.any(prices <= 0):
        return None
    times = pd.DatetimeIndex(window.index)
    # Do not use ``DatetimeIndex.view('i8')`` here: parquet can return a
    # ``datetime64[us]`` index, for which the integer unit is microseconds
    # rather than nanoseconds.  Timedelta arithmetic is unit independent.
    dt = np.asarray(
        [(times[i] - times[i - 1]).total_seconds() / 86_400.0 for i in range(1, len(times))],
        dtype=float,
    )
    valid = np.isfinite(dt) & (dt > 0)
    if not valid.any():
        return None
    log_returns = np.diff(np.log(prices))[valid]
    intervals = dt[valid]
    span_days = float(intervals.sum())
    growth_per_day = float(log_returns.sum() / span_days)
    residuals = log_returns - growth_per_day * intervals
    volatility = float(np.sqrt(365.0 * np.sum(residuals**2) / span_days)) if len(residuals) >= 2 else np.nan
    downside = float(np.sqrt(365.0 * np.sum(np.minimum(log_returns, 0.0) ** 2) / span_days))
    running_max = np.maximum.accumulate(prices)
    drawdown = float(np.max(1.0 - prices / running_max))
    return {
        "growth_per_day": growth_per_day,
        "growth_annualised": 365.0 * growth_per_day,
        "volatility": volatility,
        "downside_deviation": downside,
        "max_drawdown": drawdown,
        "observations": int(len(window)),
        "intervals": int(len(log_returns)),
        "span_days": span_days,
        "last_observation": times[-1],
        "first_observation": times[0],
        "sparse": bool(span_days / max(len(log_returns), 1) > 2.0),
    }


def rolling_score(feature: dict | None, ranking: str = "growth") -> float:
    """Return a causal ranking signal for the declared factorial arms."""
    if feature is None:
        return float("nan")
    if ranking == "growth":
        return float(feature["growth_annualised"])
    if ranking == "growth_over_risk":
        risk = feature["volatility"]
        if not np.isfinite(risk):
            return float("nan")
        return float(feature["growth_annualised"] / max(risk, RISK_FLOOR))
    raise ValueError(f"Unknown rolling ranking: {ranking}")


def build_rolling_panel(ns: dict, lookbacks=(14, 30, 60), include_outcomes=True) -> pd.DataFrame:
    """Build/reuse the causal rolling panel and forward outcome labels."""
    out = Path(ns["OUT"])
    out.mkdir(parents=True, exist_ok=True)
    path = Path(ns["PRICE_PATH"])
    stat = path.stat()
    signature = hashlib.sha256((inspect.getsource(rolling_features) + inspect.getsource(build_rolling_panel) + str(path.resolve()) + str((stat.st_size, stat.st_mtime_ns)) + str(sorted(ns["off_addresses"])) + str(tuple(lookbacks)) + str(include_outcomes)).encode()).hexdigest()
    cache = out / "rolling-panel.parquet"
    sig_path = out / "rolling-panel.signature"
    if cache.exists() and sig_path.exists() and sig_path.read_text() == signature:
        panel = pd.read_parquet(cache)
        ns["ROLLING_LOOKUP"] = {(r.date, r.address, int(r.lookback)): r._asdict() for r in panel.itertuples(index=False)}
        return panel

    columns = ["address", "share_price", "total_assets"]
    raw = pd.read_parquet(path, columns=columns, filters=[("address", "in", sorted(ns["off_addresses"]))])
    raw["date"] = pd.to_datetime(raw.index).normalize()
    groups = {address: group.sort_index() for address, group in raw.groupby("address")}
    dates = pd.date_range("2025-07-31", "2026-09-08", freq="D")
    rows = []
    started = time.monotonic()
    end = pd.Timestamp("2026-09-09")
    for i, (address, group) in enumerate(tqdm(groups.items(), desc="Rolling feature panel")):
        series = group.share_price.dropna()
        marks = _daily_last(series)
        for date in dates:
            prior = marks.loc[marks.index < date]
            if len(prior) < 2:
                continue
            assets = group.loc[group.index < date, "total_assets"].dropna()
            tvl_eligible = bool(len(assets) and float(assets.iloc[-1]) >= ns["Parameters"].min_tvl_usd)
            for lookback in lookbacks:
                feature = rolling_features(series, date, lookback)
                if feature is None:
                    continue
                gate_left = date - pd.Timedelta(days=14)
                gate_prior = prior.loc[prior.index <= gate_left]
                gate_start = gate_prior.iloc[-1] if len(gate_prior) else prior.iloc[0]
                gate = float(prior.iloc[-1] / gate_start - 1.0)
                row = dict(address=address, date=date, lookback=int(lookback), tvl_eligible=tvl_eligible, gate=gate, **feature)
                if include_outcomes:
                    for horizon in (14, 30, 60):
                        future = marks.loc[(marks.index >= date) & (marks.index <= date + pd.Timedelta(days=horizon))]
                        valid = len(future) and future.index[-1] >= date + pd.Timedelta(days=horizon - 7)
                        if valid:
                            path_values = pd.concat([pd.Series([prior.iloc[-1]], index=[date]), future])
                            ret = float(path_values.iloc[-1] / path_values.iloc[0] - 1.0)
                            dd = float((path_values / path_values.cummax() - 1.0).min())
                        else:
                            ret, dd = np.nan, np.nan
                        row[f"future_return_{horizon}"] = ret
                        row[f"future_drawdown_{horizon}"] = dd
                rows.append(row)
        if (i + 1) % 60 == 0:
            remaining = (time.monotonic() - started) / (i + 1) * (len(groups) - i - 1) / 60.0
            print(f"{i + 1}/{len(groups)} vaults; estimated minutes remaining {remaining:.1f}", flush=True)
    panel = pd.DataFrame(rows)
    panel.to_parquet(cache, index=False)
    sig_path.write_text(signature)
    ns["ROLLING_LOOKUP"] = {(r.date, r.address, int(r.lookback)): r._asdict() for r in panel.itertuples(index=False)}
    display(panel.groupby("lookback").agg(rows=("address", "size"), vaults=("address", "nunique"), first_date=("date", "min"), last_date=("date", "max")))
    return panel


def validate_rolling_features() -> None:
    """Independent scalar checks for causal and sparse behaviour."""
    idx = pd.to_datetime(["2026-07-01", "2026-07-15"])
    series = pd.Series([100.0, 110.0], index=idx)
    feature = rolling_features(series, pd.Timestamp("2026-07-16"), 30)
    assert feature is not None and feature["observations"] == 2
    assert np.isclose(feature["growth_annualised"], 365 * np.log(1.10) / 14)
    assert np.isnan(feature["volatility"]), "One constant-growth interval residual is not a risk estimate"
    extended = pd.concat([series, pd.Series([1.0], index=[pd.Timestamp("2026-07-16")])])
    assert rolling_features(extended, pd.Timestamp("2026-07-16"), 30) == feature
    weekly = pd.Series(
        [100.0, 101.0, 102.01],
        index=pd.to_datetime(["2026-07-01", "2026-07-08", "2026-07-15"]),
    )
    weekly_feature = rolling_features(weekly, pd.Timestamp("2026-07-16"), 30)
    assert weekly_feature is not None and weekly_feature["observations"] == 3
    assert weekly_feature["sparse"] and weekly_feature["intervals"] == 2
    assert np.isfinite(weekly_feature["volatility"])
    weekly_future = pd.concat([weekly, pd.Series([1.0], index=[pd.Timestamp("2026-07-16")])])
    assert rolling_features(weekly_future, pd.Timestamp("2026-07-16"), 30) == weekly_feature
    assert rolling_features(pd.Series([100.0], index=[idx[0]]), pd.Timestamp("2026-07-16"), 30) is None
    microsecond_index = pd.DatetimeIndex(["2026-07-01", "2026-07-15"], dtype="datetime64[us]")
    microsecond_feature = rolling_features(pd.Series([100.0, 110.0], index=microsecond_index), pd.Timestamp("2026-07-16"), 30)
    assert microsecond_feature is not None
    assert np.isclose(microsecond_feature["span_days"], 14.0)
    assert np.isclose(microsecond_feature["growth_annualised"], 365 * np.log(1.10) / 14)
