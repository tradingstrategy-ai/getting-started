"""Causal sparse-observation research helpers for Hyperliquid vaults.

Candidate features use fresh NAV observations only. The production comparator is
kept separate and uses carried daily closes only for live-score parity.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 365.0
LOOKBACKS = (7, 14, 21, 30, 45, 60)
LONG_LOOKBACKS = (90, 120, 180, 270, 360)
FORECAST_HORIZONS = (7, 14, 21, 30, 45, 60, 90)
EMA_SPANS = (10, 90, 120, 180, 270, 360)
TVL_FLOOR_USD = 7_500.0
STD_FLOOR = 1e-4
CANDIDATE_ANNUALISED_VOL_FLOOR = 0.05


@dataclass(frozen=True)
class ResearchConfig:
    """Frozen constants used by every notebook."""

    chain_id: int = 9999
    decision_frequency: str = "D"
    lookbacks: tuple[int, ...] = LOOKBACKS
    long_lookbacks: tuple[int, ...] = LONG_LOOKBACKS
    forecast_horizons: tuple[int, ...] = FORECAST_HORIZONS
    ema_spans: tuple[int, ...] = EMA_SPANS
    tvl_floor_usd: float = TVL_FLOOR_USD
    max_nav_age_days: int = 14
    endpoint_delay_days: int = 7
    #: Pre-evaluation daily decisions retained for expanding-model training.
    #: Raw observations before this remain available to every feature window.
    training_history_days: int = 180
    btc_symbol: str = "BTCUSDT"
    initial_cash: float = 150_000.0
    target_deployment: float = 0.98
    max_weight: float = 0.33
    max_tvl_fraction: float = 0.33
    young_max_weight: float = 0.05
    performance_fee: float = 0.10
    redemption_capital_fee: float = 0.001
    production_rebalance_days: int = 2


def config_dict(config: ResearchConfig | None = None) -> dict:
    return asdict(config or ResearchConfig())


def _download_paths() -> tuple[Path, Path]:
    root = Path.home() / ".tradingstrategy" / "vaults" / "downloads"
    prices = root / "vault-prices.parquet"
    return (prices if prices.exists() else root / "vault-price-history.parquet", root / "vault-universe.json")


def _normalise_raw(raw: pd.DataFrame, chain_id: int) -> pd.DataFrame:
    frame = raw.copy()
    if "timestamp" not in frame:
        frame = frame.reset_index()
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True).dt.tz_localize(None)
    frame["written_at"] = pd.to_datetime(frame.get("written_at", frame.timestamp), utc=True, errors="coerce").dt.tz_localize(None)
    frame["address"] = frame.address.astype(str).str.lower()
    if "chain" in frame:
        frame = frame[frame.chain.astype(int) == chain_id].copy()
    frame["share_price"] = pd.to_numeric(frame.share_price, errors="coerce")
    frame["total_assets"] = pd.to_numeric(frame.get("total_assets"), errors="coerce")
    repair = frame.get("hypercore_repair_status", pd.Series("", index=frame.index)).fillna("").astype(str)
    frame["is_fresh"] = frame.get("is_fresh", ~repair.str.contains("_carried", case=False, regex=False)).astype(bool)
    return frame[frame.share_price.gt(0)].sort_values(["address", "timestamp", "written_at"])


def load_source_data(*, refresh: bool = False, config: ResearchConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load the current reconstructed source without a written-at filter."""

    config = config or ResearchConfig()
    prices_path, universe_path = _download_paths()
    if refresh:
        from tradingstrategy.client import Client

        raw = Client.create_jupyter_client(needs_vault_data=True).get_vault_data_client().fetch_vault_price_history().copy()
    else:
        raw = pd.read_parquet(prices_path)
    raw = _normalise_raw(raw, config.chain_id)
    if universe_path.exists():
        universe = json.loads(universe_path.read_text())
        metadata = pd.DataFrame(universe.get("vaults", universe if isinstance(universe, list) else []))
    else:
        metadata = pd.DataFrame(columns=["address"])
    if "address" not in metadata:
        metadata = pd.DataFrame(columns=["address"])
    metadata["address"] = metadata.address.astype(str).str.lower()
    metadata = metadata.drop_duplicates("address", keep="last").set_index("address")
    info = {"refresh": refresh, "source_path": str(prices_path), "price_rows": int(len(raw)), "vaults": int(raw.address.nunique()), "observation_start": str(raw.timestamp.min()), "observation_end": str(raw.timestamp.max()), "written_at_start": str(raw.written_at.min()), "written_at_end": str(raw.written_at.max()), "historical_point_in_time_reconstructable": False, "research_contract": "current reconstructed provider history; written_at audit only"}
    return raw, metadata, info


def prepare_observations(raw: pd.DataFrame) -> pd.DataFrame:
    """Return fresh, valid observations and retain repair/source provenance."""

    cols = ["address", "timestamp", "written_at", "share_price", "total_assets", "is_fresh", "raw_share_price", "hypercore_repair_status", "hypercore_source"]
    frame = raw.reindex(columns=[c for c in cols if c in raw]).copy()
    return frame[frame.is_fresh & frame.share_price.gt(0)].sort_values(["address", "timestamp", "written_at"]).drop_duplicates(["address", "timestamp"], keep="last").reset_index(drop=True)


def completed_daily_window(observations: pd.DataFrame, *, days: int = 365) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Final completed daily-close window; latest partial calendar day is excluded."""

    end = pd.Timestamp(observations.timestamp.max()).normalize() - pd.Timedelta(days=1)
    return end - pd.Timedelta(days=days - 1), end


def fetch_btc_reference(config: ResearchConfig | None = None) -> pd.DataFrame:
    """Use the cached standard Binance reference series."""

    from tradingstrategy.binance.price import fetch_binance_price

    btc = fetch_binance_price(symbol=(config or ResearchConfig()).btc_symbol).copy()
    btc.index = pd.to_datetime(btc.index, utc=True).tz_localize(None).normalize()
    return btc.loc[~btc.index.duplicated(keep="last")]


def _search(ts: np.ndarray, point: pd.Timestamp) -> int:
    return int(np.searchsorted(ts, np.datetime64(point), side="left"))


def _path_metrics(prices: np.ndarray, returns: np.ndarray) -> tuple[float, float, float]:
    if len(prices) < 2:
        return np.nan, np.nan, np.nan
    dd = prices / np.maximum.accumulate(prices) - 1
    return float(dd.min()), float(np.sqrt(np.mean(dd**2))), float(np.mean(returns < 0))


def _ema(prices: np.ndarray, ts: np.ndarray, span: int) -> tuple[np.ndarray, np.ndarray]:
    out, seed = np.full(len(prices), np.nan), np.full(len(prices), np.nan)
    if not len(prices):
        return out, seed
    value, retained = float(prices[0]), 1.0
    out[0], seed[0] = value, retained
    for i in range(1, len(prices)):
        days = max((pd.Timestamp(ts[i]) - pd.Timestamp(ts[i - 1])).total_seconds() / 86400, 0)
        decay = math.exp(-math.log(2) * days / span)
        value = decay * value + (1 - decay) * float(prices[i])
        retained *= decay
        out[i], seed[i] = value, retained
    return out, seed


def _daily_measures(daily: pd.Series, date: pd.Timestamp, window: int) -> dict:
    """Fixed-window values require literal endpoints and 80% observed daily returns."""

    start, end = date - pd.Timedelta(days=window), date
    out = {f"return_{window}": np.nan, f"cagr_{window}": np.nan, f"daily_vol_{window}": np.nan, f"daily_downside_dev_{window}": np.nan, f"daily_sharpe_{window}": np.nan, f"daily_sortino_{window}": np.nan, f"daily_max_dd_{window}": np.nan, f"daily_ulcer_{window}": np.nan, f"daily_skew_{window}": np.nan, f"daily_kurtosis_{window}": np.nan}
    p0, p1 = daily.get(start), daily.get(end)
    if pd.notna(p0) and pd.notna(p1) and p0 > 0 and p1 > 0:
        growth = float(np.log(p1 / p0))
        out[f"return_{window}"], out[f"cagr_{window}"] = growth, float(np.exp(growth * TRADING_DAYS_PER_YEAR / window) - 1)
    path = daily.loc[start:end]
    r = np.log(path).diff().dropna()
    if len(r) < math.ceil(0.8 * window):
        return out
    std, downside = r.std(ddof=1), np.sqrt(np.mean(np.minimum(r.to_numpy(), 0) ** 2))
    out[f"daily_vol_{window}"] = float(std * math.sqrt(TRADING_DAYS_PER_YEAR)) if std > 0 else np.nan
    out[f"daily_downside_dev_{window}"] = float(downside * math.sqrt(TRADING_DAYS_PER_YEAR)) if np.isfinite(downside) else np.nan
    out[f"daily_sharpe_{window}"] = float(r.mean() / std * math.sqrt(TRADING_DAYS_PER_YEAR)) if std > 0 else np.nan
    out[f"daily_sortino_{window}"] = float(r.mean() / downside * math.sqrt(TRADING_DAYS_PER_YEAR)) if downside > 0 else np.nan
    prices = path.dropna().to_numpy(dtype=float)
    if len(prices) >= math.ceil(0.8 * window):
        dd, ulcer, _ = _path_metrics(prices, r.to_numpy())
        out[f"daily_max_dd_{window}"], out[f"daily_ulcer_{window}"] = dd, ulcer
    if len(r) >= 8:
        out[f"daily_skew_{window}"], out[f"daily_kurtosis_{window}"] = float(r.skew()), float(r.kurt())
    return out


def _btc_returns(intervals: pd.DataFrame, btc: pd.Series, *, max_endpoint_error_days: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Align BTC closes to the actual sparse interval endpoints.

    BTC provider rows are candle opens, so endpoint alignment uses the nearest
    daily candle close (open timestamp plus one day).  This avoids treating an
    evening mark as a close at the start of the same candle.
    """

    values, errors = [], []
    reference = btc.sort_index()
    index = pd.DatetimeIndex(reference.index)
    close_index = index + pd.Timedelta(days=1)
    for start, end in zip(intervals.start_ts, intervals.end_ts, strict=True):
        prices = []
        endpoint_errors = []
        for endpoint in (pd.Timestamp(start), pd.Timestamp(end)):
            insertion = int(close_index.searchsorted(endpoint, side="left"))
            candidates = [position for position in (insertion - 1, insertion) if 0 <= position < len(close_index)]
            if not candidates:
                prices.append(np.nan)
                endpoint_errors.append(np.nan)
                continue
            position = min(candidates, key=lambda item: abs(close_index[item] - endpoint))
            mark_ts = close_index[position]
            prices.append(float(reference.iloc[position]))
            endpoint_errors.append((endpoint - mark_ts).total_seconds() / 86400)
        error = max(abs(value) for value in endpoint_errors) if endpoint_errors and all(pd.notna(endpoint_errors)) else np.nan
        errors.append(error)
        values.append(np.log(prices[1] / prices[0]) if pd.notna(error) and error <= max_endpoint_error_days and all(pd.notna(prices)) and all(price > 0 for price in prices) else np.nan)
    return np.asarray(values), np.asarray(errors)


def _label(obs: pd.DataFrame, decision_ts: pd.Timestamp, horizon: int, config: ResearchConfig) -> dict:
    """Execution-aligned label: next observed entry and exit, with delays recorded."""

    prefix = "forward_"
    out = {f"{prefix}log_growth_{horizon}": np.nan, f"{prefix}log_growth_raw_{horizon}": np.nan, f"{prefix}variance_{horizon}": np.nan, f"{prefix}downside_semivariance_{horizon}": np.nan, f"{prefix}max_drawdown_{horizon}": np.nan, f"{prefix}ulcer_{horizon}": np.nan, f"entry_ts_{horizon}": pd.NaT, f"exit_ts_{horizon}": pd.NaT, f"entry_delay_days_{horizon}": np.nan, f"exit_delay_days_{horizon}": np.nan, f"actual_holding_days_{horizon}": np.nan, f"outcome_id_{horizon}": None}
    ts = obs.timestamp.to_numpy(dtype="datetime64[ns]")
    entry_i = _search(ts, decision_ts)
    if entry_i == len(obs):
        return out
    entry = obs.iloc[entry_i]
    entry_delay = (entry.timestamp - decision_ts).total_seconds() / 86400
    if entry_delay > config.endpoint_delay_days:
        return out
    exit_target = entry.timestamp + pd.Timedelta(days=horizon)
    exit_i = _search(ts, exit_target)
    if exit_i == len(obs):
        return out
    exit_mark = obs.iloc[exit_i]
    exit_delay = (exit_mark.timestamp - exit_target).total_seconds() / 86400
    holding = (exit_mark.timestamp - entry.timestamp).total_seconds() / 86400
    if exit_delay > config.endpoint_delay_days or holding <= 0:
        return out
    raw = float(np.log(exit_mark.share_price / entry.share_price))
    out.update({f"{prefix}log_growth_{horizon}": raw * horizon / holding, f"{prefix}log_growth_raw_{horizon}": raw, f"entry_ts_{horizon}": entry.timestamp, f"exit_ts_{horizon}": exit_mark.timestamp, f"entry_delay_days_{horizon}": entry_delay, f"exit_delay_days_{horizon}": exit_delay, f"actual_holding_days_{horizon}": holding, f"outcome_id_{horizon}": f"{entry.address}|{entry.timestamp.isoformat()}|{exit_mark.timestamp.isoformat()}"})
    path = obs.iloc[entry_i : exit_i + 1]
    daily_path = path.assign(date=path.timestamp.dt.normalize()).groupby("date").share_price.last()
    daily_path = daily_path.reindex(pd.date_range(entry.timestamp.normalize(), exit_mark.timestamp.normalize(), freq="D"))
    daily_r = np.log(daily_path).diff().dropna()
    if len(daily_r) >= math.ceil(0.8 * horizon):
        out[f"{prefix}variance_{horizon}"] = float(daily_r.var(ddof=1))
        out[f"{prefix}downside_semivariance_{horizon}"] = float(np.mean(np.minimum(daily_r.to_numpy(), 0) ** 2))
        observed_daily_path = daily_path.dropna().to_numpy(dtype=float)
        out[f"{prefix}max_drawdown_{horizon}"], out[f"{prefix}ulcer_{horizon}"], _ = _path_metrics(observed_daily_path, daily_r.to_numpy())
    return out


def _vault_panel(address: str, obs: pd.DataFrame, metadata: pd.DataFrame, btc: pd.Series, dates: pd.DatetimeIndex, config: ResearchConfig) -> tuple[list[dict], list[dict], list[dict]]:
    obs = obs.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    ts, prices = obs.timestamp.to_numpy(dtype="datetime64[ns]"), obs.share_price.to_numpy()
    intervals = pd.DataFrame({"start_ts": obs.timestamp.shift(), "end_ts": obs.timestamp, "start_price": obs.share_price.shift(), "end_price": obs.share_price}).iloc[1:].copy()
    intervals["duration_days"] = (intervals.end_ts - intervals.start_ts).dt.total_seconds() / 86400
    intervals = intervals[intervals.duration_days.gt(0)]
    intervals["log_return"] = np.log(intervals.end_price / intervals.start_price)
    intervals["per_day_return"] = intervals.log_return / intervals.duration_days
    daily_full = obs.assign(date=obs.timestamp.dt.normalize()).groupby("date").share_price.last().reindex(pd.date_range(obs.timestamp.iloc[0].normalize(), dates[-1], freq="D"))
    btc_daily = obs.assign(date=obs.timestamp.dt.normalize()).sort_values("timestamp").groupby("date", as_index=False).last()
    btc_intervals = pd.DataFrame({"start_ts": btc_daily.timestamp.shift(), "end_ts": btc_daily.timestamp, "start_price": btc_daily.share_price.shift(), "end_price": btc_daily.share_price}).iloc[1:].copy()
    btc_intervals["duration_days"] = (btc_intervals.end_ts - btc_intervals.start_ts).dt.total_seconds() / 86400
    btc_intervals = btc_intervals[btc_intervals.duration_days.ge(1.0)].copy()
    btc_intervals["log_return"] = np.log(btc_intervals.end_price / btc_intervals.start_price)
    daily = daily_full.reindex(dates)
    carried = daily_full.ffill()
    carried_returns = carried.pct_change()
    production_cagr = (carried / carried.shift(360)).pow(TRADING_DAYS_PER_YEAR / 360) - 1
    production_downside = carried_returns.clip(upper=0).pow(2).rolling(45, min_periods=45).mean().pow(0.5).replace(0, np.nan)
    production_sortino = carried_returns.rolling(45, min_periods=45).mean() / production_downside * math.sqrt(TRADING_DAYS_PER_YEAR)
    production_score = 0.6 * production_cagr.clip(0, 1) + 0.4 * (production_sortino / 3).clip(0, 1)
    production_gate = carried / carried.shift(14) - 1
    production_inverse_vol = 1 / carried_returns.rolling(90, min_periods=90).std().clip(lower=STD_FLOOR)
    first = obs.timestamp.iloc[0]
    start = metadata.loc[address, "start_date"] if address in metadata.index and "start_date" in metadata and pd.notna(metadata.loc[address, "start_date"]) else first
    start = pd.Timestamp(start)
    if start.tzinfo:
        start = start.tz_localize(None)
    emas = {span: _ema(prices, ts, span) for span in config.ema_spans}
    rows, labels, funnel = [], [], []
    first_date = first.normalize()
    final_date = min(dates[-1], (obs.timestamp.iloc[-1] + pd.Timedelta(days=config.max_nav_age_days - 1)).normalize())
    for date in dates[(dates >= first_date) & (dates <= final_date)]:
        decision_ts = date + pd.Timedelta(days=1)
        end_i = _search(ts, decision_ts) - 1
        if end_i < 0:
            continue
        last, prior = obs.iloc[end_i], obs.iloc[: end_i + 1]
        nav_age = (decision_ts - last.timestamp).total_seconds() / 86400
        history = (last.timestamp - first).total_seconds() / 86400
        tvl = float(last.total_assets) if pd.notna(last.total_assets) else np.nan
        two_marks = len(prior) >= 2 and (last.timestamp - prior.timestamp.iloc[0]).total_seconds() >= 86400
        eligible = bool(two_marks and nav_age <= config.max_nav_age_days and pd.notna(tvl) and tvl >= config.tvl_floor_usd)
        funnel.append({"date": date, "address": address, "has_two_marks": two_marks, "fresh_nav_age_days": nav_age, "tvl_current": tvl, "eligible": eligible})
        if not eligible:
            continue
        row = {"date": date, "decision_ts": decision_ts, "address": address, "eligible": True, "nav": float(last.share_price), "tvl_current": tvl, "last_observation_ts": last.timestamp, "nav_age_days": nav_age, "available_history_days": history, "observation_count": len(prior), "metadata_age_days": (decision_ts - start).total_seconds() / 86400, "is_sparse_prediction": nav_age > 1}
        past = intervals[intervals.end_ts <= last.timestamp]
        if len(past):
            last_r = past.iloc[-1]
            row.update({"last_interval_log_return": last_r.log_return, "last_interval_days": last_r.duration_days, "last_interval_return_per_day": last_r.per_day_return})
        else:
            row.update({"last_interval_log_return": np.nan, "last_interval_days": np.nan, "last_interval_return_per_day": np.nan})
        for window in config.lookbacks + config.long_lookbacks:
            subset = past[past.end_ts > last.timestamp - pd.Timedelta(days=window)]
            row[f"observed_interval_count_{window}"], row[f"observed_covered_days_{window}"] = len(subset), float(subset.duration_days.sum())
            if len(subset):
                row[f"interval_log_growth_{window}"] = float(subset.log_return.sum())
                dd, ulcer, lose = _path_metrics(np.r_[subset.start_price.iloc[0], subset.end_price.to_numpy()], subset.log_return.to_numpy())
                row[f"observed_max_dd_{window}"], row[f"observed_ulcer_{window}"], row[f"observed_losing_fraction_{window}"] = dd, ulcer, lose
            else:
                for name in ("interval_log_growth", "observed_max_dd", "observed_ulcer", "observed_losing_fraction"):
                    row[f"{name}_{window}"] = np.nan
            if len(subset) >= 3:
                covered_days = float(subset.duration_days.sum())
                mean_per_day = float(subset.log_return.sum() / covered_days)
                variance_per_day = float(((subset.log_return - mean_per_day * subset.duration_days) ** 2).sum() / covered_days)
                row[f"interval_vol_{window}"] = float(np.sqrt(variance_per_day) * math.sqrt(TRADING_DAYS_PER_YEAR))
                down = np.sqrt(np.minimum(subset.log_return.to_numpy(), 0).dot(np.minimum(subset.log_return.to_numpy(), 0)) / covered_days)
                row[f"interval_downside_dev_{window}"] = float(down * math.sqrt(TRADING_DAYS_PER_YEAR)) if np.isfinite(down) else np.nan
            else:
                row[f"interval_vol_{window}"], row[f"interval_downside_dev_{window}"] = np.nan, np.nan
            if window in config.lookbacks:
                row.update(_daily_measures(daily_full, date, window))
        for window in (7, 14, 30, 90):
            interval_window = btc_intervals[(btc_intervals.end_ts > last.timestamp - pd.Timedelta(days=window)) & btc_intervals.end_ts.le(last.timestamp)]
            btc_returns, endpoint_errors = _btc_returns(interval_window, btc)
            vault_returns = interval_window.log_return.to_numpy(dtype=float)
            valid = np.isfinite(vault_returns) & np.isfinite(btc_returns)
            row[f"btc_beta_pairs_{window}"] = int(valid.sum())
            row[f"btc_endpoint_error_days_{window}"] = float(np.nanmax(np.abs(endpoint_errors[valid]))) if valid.any() else np.nan
            if valid.sum() >= 10 and np.var(btc_returns[valid]) > 1e-14:
                beta = float(np.cov(btc_returns[valid], vault_returns[valid], ddof=1)[0, 1] / np.var(btc_returns[valid], ddof=1))
                residual = vault_returns[valid] - beta * btc_returns[valid]
                row[f"btc_beta_{window}"] = beta
                row[f"btc_residual_vol_{window}"] = float(residual.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))
            else:
                row[f"btc_beta_{window}"], row[f"btc_residual_vol_{window}"] = np.nan, np.nan
        for window in (7, 30, 90):
            values = prior[prior.timestamp > last.timestamp - pd.Timedelta(days=window)].total_assets.dropna()
            row[f"tvl_min_{window}"], row[f"tvl_max_{window}"], row[f"tvl_observation_count_{window}"] = (values.min() if len(values) else np.nan), (values.max() if len(values) else np.nan), len(values)
        for span, (ema, seed) in emas.items():
            row[f"ema_distance_{span}"], row[f"ema_seed_weight_{span}"] = float(last.share_price / ema[end_i] - 1), seed[end_i]
            if len(past) >= 3:
                weights = np.exp(-math.log(2) * (last.timestamp - past.end_ts).dt.total_seconds().to_numpy() / 86400 / span)
                values = past.log_return.to_numpy()
                durations = past.duration_days.to_numpy()
                mean_per_day = np.sum(weights * values) / np.sum(weights * durations)
                variance_per_day = np.sum(weights * (values - mean_per_day * durations) ** 2) / np.sum(weights * durations)
                row[f"ewm_interval_vol_{span}"] = float(np.sqrt(variance_per_day) * math.sqrt(TRADING_DAYS_PER_YEAR))
            else:
                row[f"ewm_interval_vol_{span}"] = np.nan
        row.update({"incumbent_score": production_score.get(date), "incumbent_return_gate": production_gate.get(date), "incumbent_inverse_vol": production_inverse_vol.get(date)})
        rows.append(row)
        label = {"date": date, "address": address, "eligible": True}
        for horizon in config.forecast_horizons:
            label.update(_label(obs, decision_ts, horizon, config))
        labels.append(label)
    return rows, labels, funnel


def add_missingness_flags(features: pd.DataFrame) -> pd.DataFrame:
    reserved = {"date", "decision_ts", "address", "eligible", "nav", "tvl_current", "last_observation_ts", "is_sparse_prediction"}
    output = features.copy()
    for column in features.columns:
        if column not in reserved and pd.api.types.is_numeric_dtype(features[column]):
            output[f"{column}__missing"] = features[column].isna().astype(float)
    return output


def generate_research_panels(observations: pd.DataFrame, metadata: pd.DataFrame, *, btc: pd.DataFrame, config: ResearchConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build all historical causal daily decisions and their horizon-specific labels."""

    config = config or ResearchConfig()
    observations = prepare_observations(observations)
    evaluation_start, evaluation_end = completed_daily_window(observations)
    dates = pd.date_range(evaluation_start - pd.Timedelta(days=config.training_history_days), evaluation_end, freq="D")
    btc_close = btc.close.copy()
    btc_close.index = pd.to_datetime(btc_close.index).tz_localize(None).normalize()
    rows, labels, funnel = [], [], []
    vault_groups = list(observations.groupby("address", sort=True))
    for number, (address, vault) in enumerate(vault_groups, start=1):
        a, b, c = _vault_panel(address, vault, metadata, btc_close, dates, config)
        rows.extend(a)
        labels.extend(b)
        funnel.extend(c)
        if number % 50 == 0 or number == len(vault_groups):
            print(f"Feature panel: {number}/{len(vault_groups)} vaults; {len(rows):,} eligible daily rows")
    features, label_frame = add_missingness_flags(pd.DataFrame(rows)), pd.DataFrame(labels)
    for horizon in config.forecast_horizons:
        outcome = f"outcome_id_{horizon}"
        counts = label_frame[outcome].dropna().value_counts()
        label_frame[f"outcome_weight_{horizon}"] = label_frame[outcome].map(lambda x: 1 / counts[x] if pd.notna(x) else np.nan)
    return features, label_frame, pd.DataFrame(funnel)


def feature_names(features: pd.DataFrame, *, include_optional: bool = True) -> list[str]:
    excluded = {"date", "decision_ts", "address", "eligible", "nav", "last_observation_ts", "incumbent_score", "incumbent_return_gate", "incumbent_inverse_vol"}
    names = [c for c in features if c not in excluded and pd.api.types.is_numeric_dtype(features[c])]
    if not include_optional:
        always_core = ("last_interval_", "nav_age_", "available_history_", "observation_count", "tvl_current")
        short_interval = ("interval_log_growth_", "interval_vol_", "interval_downside_dev_")
        names = [column for column in names if column.startswith(always_core) or (column.removesuffix("__missing").startswith(short_interval) and any(column.removesuffix("__missing").endswith(f"_{window}") for window in LOOKBACKS))]
    return names


def _rank_ic(frame: pd.DataFrame, x: str, y: str) -> float:
    sample = frame[[x, y]].dropna()
    return float(sample[x].corr(sample[y], method="spearman")) if len(sample) >= 10 and sample[x].nunique() > 1 and sample[y].nunique() > 1 else np.nan


def compute_ic_table(features: pd.DataFrame, labels: pd.DataFrame, *, feature_columns: Sequence[str], target_columns: Sequence[str], start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Vectorised equal-date Spearman IC.

    Ranks are formed within the complete decision-date cross-section before
    pairwise missing values are removed. This keeps a feature's score
    comparable across differing sparse-feature coverage and avoids thousands
    of Python-level group-by calls.
    """

    merged = features.merge(labels, on=["date", "address", "eligible"])
    if start is not None:
        merged = merged[merged.date >= start]
    if end is not None:
        merged = merged[merged.date <= end]
    date_codes, date_index = pd.factorize(merged.date, sort=True)
    group_count = len(date_index)
    target_ranks = {name: merged.groupby("date")[name].rank().to_numpy(dtype=float) for name in target_columns}
    rows = []
    for feature in feature_columns:
        x = merged.groupby("date")[feature].rank().to_numpy(dtype=float)
        for target, y in target_ranks.items():
            valid = np.isfinite(x) & np.isfinite(y)
            if valid.sum() < 10:
                continue
            code, xv, yv = date_codes[valid], x[valid], y[valid]
            n = np.bincount(code, minlength=group_count).astype(float)
            sx = np.bincount(code, weights=xv, minlength=group_count)
            sy = np.bincount(code, weights=yv, minlength=group_count)
            sxx = np.bincount(code, weights=xv * xv, minlength=group_count)
            syy = np.bincount(code, weights=yv * yv, minlength=group_count)
            sxy = np.bincount(code, weights=xv * yv, minlength=group_count)
            numerator = n * sxy - sx * sy
            denominator = np.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))
            correlations = np.full(group_count, np.nan)
            np.divide(numerator, denominator, out=correlations, where=denominator > 0)
            values = correlations[(n >= 10) & np.isfinite(correlations)]
            if len(values):
                rows.append({"feature": feature, "target": target, "mean_rank_ic": values.mean(), "median_rank_ic": np.median(values), "mean_abs_rank_ic": np.abs(values).mean(), "ic_ir": values.mean() / values.std(ddof=1) if len(values) > 1 and values.std(ddof=1) else np.nan, "dates": len(values)})
    return pd.DataFrame(rows)


def monthly_walk_forward_ridge(features: pd.DataFrame, labels: pd.DataFrame, *, feature_columns: Sequence[str], target: str, horizon: int, evaluation_start: pd.Timestamp, evaluation_end: pd.Timestamp, alpha: float = 10.0, min_train_dates: int = 60) -> pd.DataFrame:
    """Monthly expanding Ridge refits; only labels with realised exits may train."""

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    exit_column, weight_column = f"exit_ts_{horizon}", f"outcome_weight_{horizon}"
    data = features.merge(labels[["date", "address", "eligible", target, exit_column, weight_column]], on=["date", "address", "eligible"], how="left")
    output = []
    evaluation_dates = pd.date_range(evaluation_start, evaluation_end, freq="D")
    for period in evaluation_dates.to_period("M").unique():
        test_dates = evaluation_dates[evaluation_dates.to_period("M") == period]
        boundary = test_dates.min()
        train = data[(data[exit_column] <= boundary) & data[target].notna() & (data.date < boundary)]
        if train.date.nunique() < min_train_dates:
            output.append(pd.DataFrame({"date": test_dates, "address": "__warmup__", "target": target, "horizon": horizon, "prediction": np.nan, "actual": np.nan, "status": "warmup"}))
            continue
        columns = [c for c in feature_columns if c in train and train[c].notna().any()]
        model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), Ridge(alpha=alpha))
        model.fit(train[columns], train[target], ridge__sample_weight=train[weight_column].fillna(1))
        test = data[data.date.isin(test_dates) & data.eligible].copy()
        test["prediction"], test["actual"], test["target"], test["horizon"], test["fit_boundary"], test["status"] = model.predict(test[columns]), test[target], target, horizon, boundary, "predicted"
        output.append(test[["date", "address", "target", "horizon", "prediction", "actual", "fit_boundary", "status"]])
    return pd.concat(output, ignore_index=True) if output else pd.DataFrame()


def prediction_ic(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    valid = predictions[(predictions.status == "predicted") & predictions.actual.notna()]
    for (target, horizon), group in valid.groupby(["target", "horizon"]):
        values = group.groupby("date").apply(lambda g: _rank_ic(g.rename(columns={"prediction": "x", "actual": "y"}), "x", "y"), include_groups=False).dropna()
        if len(values):
            rows.append({"target": target, "horizon": horizon, "mean_rank_ic": values.mean(), "dates": len(values), "ic_ir": values.mean() / values.std(ddof=1) if len(values) > 1 and values.std(ddof=1) else np.nan})
    return pd.DataFrame(rows)


def daily_prediction_ic(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return one realised rank IC per target, horizon and decision date."""

    rows = []
    valid = predictions[(predictions.status == "predicted") & predictions.actual.notna()]
    for (target, horizon, date), group in valid.groupby(["target", "horizon", "date"], sort=True):
        ic = _rank_ic(group.rename(columns={"prediction": "x", "actual": "y"}), "x", "y")
        if pd.notna(ic):
            rows.append({"target": target, "horizon": horizon, "date": date, "rank_ic": ic, "vaults": len(group.dropna(subset=["prediction", "actual"]))})
    return pd.DataFrame(rows)


def daily_feature_ic(features: pd.DataFrame, labels: pd.DataFrame, *, feature: str, target: str, sign: float = 1.0, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Return daily IC for one signed, simple feature control."""

    data = features[["date", "address", "eligible", feature]].merge(labels[["date", "address", "eligible", target]], on=["date", "address", "eligible"])
    if start is not None:
        data = data[data.date >= start]
    if end is not None:
        data = data[data.date <= end]
    rows = []
    for date, group in data.groupby("date", sort=True):
        sample = group.rename(columns={feature: "x", target: "y"}).copy()
        sample["x"] *= sign
        ic = _rank_ic(sample, "x", "y")
        if pd.notna(ic):
            rows.append({"date": date, "rank_ic": ic, "vaults": len(sample.dropna(subset=["x", "y"]))})
    return pd.DataFrame(rows)


def matched_daily_feature_control_ic(predictions: pd.DataFrame, features: pd.DataFrame, *, feature: str, target: str, sign: float = 1.0, zero_downside: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return model/control ICs on identical valid cross-sectional rows."""

    data = predictions[(predictions.target == target) & (predictions.status == "predicted")][["date", "address", "prediction", "actual"]].merge(features[["date", "address", feature, "observed_interval_count_30"]], on=["date", "address"], how="inner")
    if zero_downside:
        data.loc[data[feature].isna() & data.observed_interval_count_30.ge(3), feature] = 0.0
    data = data.dropna(subset=["prediction", "actual", feature])
    model_rows, control_rows = [], []
    for date, group in data.groupby("date", sort=True):
        model_ic = _rank_ic(group, "prediction", "actual")
        control = group[[feature, "actual"]].rename(columns={feature: "x", "actual": "y"}).copy()
        control["x"] *= sign
        control_ic = _rank_ic(control, "x", "y")
        if pd.notna(model_ic) and pd.notna(control_ic):
            vaults = len(group)
            model_rows.append({"date": date, "rank_ic": model_ic, "vaults": vaults})
            control_rows.append({"date": date, "rank_ic": control_ic, "vaults": vaults})
    return pd.DataFrame(model_rows), pd.DataFrame(control_rows)


def paired_block_bootstrap_difference(left: pd.DataFrame, right: pd.DataFrame, *, block_length: int, draws: int = 1_000, seed: int = 1) -> dict:
    """Paired moving-block interval for a daily IC difference."""

    paired = left[["date", "rank_ic"]].merge(right[["date", "rank_ic"]], on="date", suffixes=("_left", "_right")).sort_values("date")
    values = (paired.rank_ic_left - paired.rank_ic_right).to_numpy(dtype=float)
    if not len(values):
        return {"paired_dates": 0, "mean_difference": np.nan, "bootstrap_p05": np.nan, "bootstrap_p95": np.nan}
    rng = np.random.default_rng(seed)
    length = min(max(int(block_length), 1), len(values))
    means = np.empty(draws)
    for draw in range(draws):
        starts = rng.integers(0, len(values), size=math.ceil(len(values) / length))
        sample = np.concatenate([np.take(values, np.arange(start, start + length) % len(values)) for start in starts])[: len(values)]
        means[draw] = sample.mean()
    return {"paired_dates": len(values), "mean_difference": values.mean(), "bootstrap_p05": np.quantile(means, 0.05), "bootstrap_p95": np.quantile(means, 0.95)}


def moving_block_bootstrap_ic(daily_ic: pd.DataFrame, *, block_length: int, draws: int = 1_000, seed: int = 1) -> pd.DataFrame:
    """Confidence intervals for equal-date IC using contiguous date blocks.

    Each resample selects whole daily cross-sections in contiguous blocks. Vault
    rows are never treated as independent market histories.
    """

    rng = np.random.default_rng(seed)
    rows = []
    for (target, horizon), group in daily_ic.groupby(["target", "horizon"], sort=True):
        values = group.sort_values("date").rank_ic.to_numpy(dtype=float)
        if not len(values):
            continue
        length = min(max(int(block_length), 1), len(values))
        means = np.empty(draws)
        for draw in range(draws):
            starts = rng.integers(0, len(values), size=math.ceil(len(values) / length))
            sample = np.concatenate([np.take(values, np.arange(start, start + length) % len(values)) for start in starts])[: len(values)]
            means[draw] = sample.mean()
        rows.append({"target": target, "horizon": horizon, "block_length_days": length, "dates": len(values), "nominal_blocks": len(values) / length, "mean_rank_ic": values.mean(), "bootstrap_p05": np.quantile(means, 0.05), "bootstrap_p50": np.quantile(means, 0.50), "bootstrap_p95": np.quantile(means, 0.95), "positive_date_fraction": float(np.mean(values > 0))})
    return pd.DataFrame(rows)


def blockwise_prediction_permutation_null(predictions: pd.DataFrame, *, block_length: int = 90, draws: int = 200, seed: int = 1) -> pd.DataFrame:
    """Bounded growth-model placebo with persistent identity shuffles per block.

    The mapping is constant within each contiguous date block and moves an
    entire vault prediction identity, rather than independently shuffling daily
    values. It is a prediction-level sensitivity null: a future promotion still
    requires rerunning model selection under a feature-bundle null.
    """

    rng = np.random.default_rng(seed)
    data = predictions[(predictions.status == "predicted") & predictions.actual.notna() & predictions.target.str.startswith("forward_log_growth_")].copy()
    if data.empty:
        return pd.DataFrame()
    addresses = np.sort(data.address.unique())
    address_code = {address: number for number, address in enumerate(addresses)}
    grouped = {(target, horizon): {date: frame.set_index("address")[["prediction", "actual"]] for date, frame in part.groupby("date")} for (target, horizon), part in data.groupby(["target", "horizon"])}
    dates = np.array(sorted(data.date.unique()))
    blocks = [dates[start : start + block_length] for start in range(0, len(dates), block_length)]
    rows = []
    for draw in range(draws):
        values_by_target: dict[tuple[str, int], list[float]] = {key: [] for key in grouped}
        for block in blocks:
            mapping = rng.permutation(len(addresses))
            for key, by_date in grouped.items():
                for date in block:
                    frame = by_date.get(date)
                    if frame is None:
                        continue
                    source_codes = np.array([mapping[address_code[address]] for address in frame.index])
                    source_addresses = addresses[source_codes]
                    shuffled = frame.prediction.reindex(source_addresses).to_numpy(dtype=float)
                    sample = pd.DataFrame({"prediction": shuffled, "actual": frame.actual.to_numpy(dtype=float)}).dropna()
                    if len(sample) >= 10 and sample.prediction.nunique() > 1 and sample.actual.nunique() > 1:
                        values_by_target[key].append(float(sample.prediction.corr(sample.actual, method="spearman")))
        means = {key: float(np.mean(value)) for key, value in values_by_target.items() if value}
        if means:
            best_key = max(means, key=lambda key: abs(means[key]))
            rows.append({"draw": draw, "max_abs_mean_rank_ic": abs(means[best_key]), "best_target": best_key[0], "best_horizon": best_key[1], "best_mean_rank_ic": means[best_key], "block_length_days": block_length})
    return pd.DataFrame(rows)


def adaptive_breadth(scores: pd.Series, *, max_positions: int = 20, minimum_positions: int = 3) -> int:
    clean = scores.dropna().sort_values(ascending=False)
    if len(clean) <= minimum_positions:
        return len(clean)
    scale = clean.std(ddof=1)
    if not scale or not np.isfinite(scale):
        return min(max_positions, len(clean))
    return int(np.clip(max_positions - int(np.clip((clean.iloc[0] - clean.median()) / scale, 0, max_positions - minimum_positions)), minimum_positions, min(max_positions, len(clean))))


def capped_weights(frame: pd.DataFrame, score: pd.Series, *, max_positions: int, config: ResearchConfig, portfolio_equity: float, use_risk: bool = False, use_inverse_variance: bool = False, use_young_cap: bool = False, accepted_dollar_cap: pd.Series | None = None) -> pd.Series:
    """Build risk-capped weights, redistributing remaining capital greedily."""

    ranked = score.sort_values(ascending=False, kind="stable").head(max_positions)
    if ranked.empty or portfolio_equity <= 0:
        return pd.Series(dtype=float)
    weights = pd.Series(1 / len(ranked), index=ranked.index)
    if use_risk:
        risk = frame.loc[ranked.index, "daily_vol_30"].combine_first(frame.loc[ranked.index, "daily_vol_14"]).combine_first(frame.loc[ranked.index, "daily_vol_7"])
        credible = risk.notna() & risk.ge(CANDIDATE_ANNUALISED_VOL_FLOOR)
        if credible.any():
            inv = 1 / risk[credible]
            inv /= inv.sum()
            weights.loc[credible] = inv * (credible.sum() / len(weights))
            weights.loc[~credible] = 1 / len(weights)
    if use_inverse_variance:
        inverse_variance = frame.loc[ranked.index, "incumbent_inverse_vol"].fillna(0).clip(lower=0).pow(2)
        if inverse_variance.sum() > 0:
            weights = inverse_variance / inverse_variance.sum()
    caps = pd.Series(config.max_weight, index=weights.index)
    if use_young_cap:
        caps.loc[frame.loc[weights.index, "available_history_days"].lt(90)] = config.young_max_weight
    capacity = (config.max_tvl_fraction * frame.loc[weights.index, "tvl_current"] / (portfolio_equity * config.target_deployment)).clip(lower=0, upper=config.max_weight)
    caps = pd.concat([caps, capacity], axis=1).min(axis=1)
    investable = portfolio_equity * config.target_deployment
    remaining, allocated, equity_left = weights.to_dict(), {}, investable
    while equity_left > 1e-6 and remaining:
        total_weight = sum(remaining.values())
        if not np.isfinite(total_weight) or total_weight <= 0:
            break
        address = max(remaining, key=lambda item: remaining[item] / total_weight)
        asked = equity_left * remaining[address] / total_weight
        accepted = min(asked, caps[address] * investable)
        if accepted_dollar_cap is not None:
            accepted = min(accepted, float(accepted_dollar_cap.get(address, accepted)))
        allocated[address] = accepted / investable
        equity_left -= accepted
        del remaining[address]
    return pd.Series(allocated, dtype=float)


def simulate_allocator(features: pd.DataFrame, scores: pd.DataFrame, *, observations: pd.DataFrame, config: ResearchConfig | None = None, mode: str = "candidate", max_positions: int = 10, rebalance_days: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily marked replay with production-style forward-filled vault marks."""

    config = config or ResearchConfig()
    frame = features.merge(scores, on=["date", "address"], how="left")
    all_marks = observations[observations.is_fresh].copy()
    all_marks["date"] = all_marks.timestamp.dt.normalize()
    actual_mark_groups = {date: group.sort_values("timestamp").groupby("address").share_price.last() for date, group in all_marks.groupby("date", sort=True)}
    forward_mark_groups = {date: group.set_index("address").nav.dropna() for date, group in frame.groupby("date", sort=True)}
    cash, holdings, last_marks, cost_basis, rows, trades = config.initial_cash, {}, {}, {}, [], []
    for number, (date, day) in enumerate(frame.groupby("date", sort=True)):
        day = day.set_index("address")
        marks = forward_mark_groups.get(date, pd.Series(dtype=float))
        actual_marks = actual_mark_groups.get(date, pd.Series(dtype=float))
        for address, nav in marks.items():
            last_marks[address] = float(nav)
        marked = {address: quantity * last_marks[address] for address, quantity in holdings.items() if address in last_marks}
        equity = cash + sum(marked.values())
        if number % (rebalance_days or config.production_rebalance_days) == 0:
            available = day
            stale_holdings = {address: value for address, value in marked.items() if address not in marks.index}
            budget = max(equity - sum(stale_holdings.values()), 0.0)
            if mode == "incumbent":
                candidates = available[available.incumbent_return_gate.gt(-0.16)].copy()
                signal = candidates.incumbent_score.fillna(0).sort_index()
                weights = capped_weights(candidates, signal, max_positions=max_positions, config=config, portfolio_equity=budget, use_inverse_variance=True)
            else:
                candidates = available[available.prediction.notna()].copy()
                signal = candidates.prediction.sort_index()
                limit = adaptive_breadth(signal, max_positions=max_positions) if mode == "adaptive" else max_positions
                weights = capped_weights(candidates, signal, max_positions=limit, config=config, portfolio_equity=budget, use_risk=True, use_young_cap=True)
            target = stale_holdings | {address: budget * config.target_deployment * weight for address, weight in weights.items()}
            turnover = sum(abs(target.get(a, 0) - marked.get(a, 0)) for a in set(target) | set(marked))
            sold = sum(max(marked.get(a, 0) - target.get(a, 0), 0) for a in set(target) | set(marked))
            profit_fee = 0.0
            for address in set(marked) | set(target):
                sale = max(marked.get(address, 0) - target.get(address, 0), 0)
                if sale:
                    basis_sold = cost_basis.get(address, marked.get(address, 0)) * sale / marked[address]
                    profit_fee += max(sale - basis_sold, 0) * config.performance_fee
                    cost_basis[address] = max(cost_basis.get(address, marked[address]) - basis_sold, 0)
            fee = sold * config.redemption_capital_fee + profit_fee
            cash = equity - sum(target.values()) - fee
            assert cash >= -1e-6, f"Negative cash on {date}: {cash}"
            cash = max(cash, 0.0)
            for address, value in target.items():
                if value > marked.get(address, 0):
                    cost_basis[address] = cost_basis.get(address, 0) + value - marked.get(address, 0)
            holdings = {address: value / last_marks[address] for address, value in target.items() if value > 0 and address in last_marks}
            equity = cash + sum(target.values())
            trades.append({"date": date, "turnover": turnover, "sold_value": sold, "fee": fee, "performance_fee": profit_fee, "mode": mode, "stale_holdings": len(stale_holdings)})
        else:
            turnover = fee = 0.0
        rows.append({"date": date, "equity": equity, "cash": cash, "n_positions": len(holdings), "turnover": turnover, "fee": fee, "stale_positions": sum(address not in marks.index for address in holdings), "carried_positions": sum(address in marks.index and address not in actual_marks.index for address in holdings), "mode": mode})
    equity = pd.DataFrame(rows)
    equity["return"], equity["drawdown"] = equity.equity.pct_change(), equity.equity / equity.equity.cummax() - 1
    return equity, pd.DataFrame(trades)


def summarise_backtest(equity: pd.DataFrame, *, periods_per_year: float = TRADING_DAYS_PER_YEAR) -> dict:
    if equity.empty:
        return {}
    returns, years = equity["return"].dropna(), max((equity.date.iloc[-1] - equity.date.iloc[0]).days / TRADING_DAYS_PER_YEAR, 1 / TRADING_DAYS_PER_YEAR)
    std = returns.std(ddof=1)
    return {"start": str(equity.date.iloc[0]), "end": str(equity.date.iloc[-1]), "final_equity": float(equity.equity.iloc[-1]), "cagr": float((equity.equity.iloc[-1] / equity.equity.iloc[0]) ** (1 / years) - 1), "volatility": float(std * math.sqrt(periods_per_year)) if pd.notna(std) else np.nan, "sharpe": float(returns.mean() / std * math.sqrt(periods_per_year)) if pd.notna(std) and std > 0 else np.nan, "max_drawdown": float(equity.drawdown.min()), "mean_positions": float(equity.n_positions.mean()), "mean_turnover": float(equity.turnover.mean()), "mean_cash_fraction": float((equity.cash / equity.equity).mean()), "mean_stale_positions": float(equity.stale_positions.mean()), "mean_carried_positions": float(equity.carried_positions.mean()) if "carried_positions" in equity else 0.0}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
