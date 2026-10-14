"""Causal score panels, sparse search and v11 backtests for experiment 04."""

import datetime
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from tqdm_loggable.auto import tqdm

from accepted_dollar_cap import AuditedAlphaModel
from tradeexecutor.backtest.backtest_runner import BacktestResult, run_backtest_inline
from tradeexecutor.state.state import State
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe, calculate_sortino, calculate_max_drawdown
from tradeexecutor.strategy.reserve_currency import ReserveCurrency
from tradeexecutor.visual.equity_curve import calculate_equity_curve, calculate_returns
from tradeexecutor.analysis.weights import calculate_asset_weights

PERIODS = {"1m": 30, "45d compatibility": 45, "46d": 46, "2m": 60, "3m": 90, "4m": 120, "6m": 180, "9m": 270, "1y": 360, "2y": 730}
METRICS = ("CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar")
FEATURES = [(period, metric) for period in PERIODS for metric in METRICS]
SEARCH_FEATURES = [i for i, (period, metric) in enumerate(FEATURES) if period != "45d compatibility"]


@dataclass(frozen=True)
class MatrixConfig:
    """Fixed feature definitions; clips are not jointly optimised."""

    #: Maximum CAGR rewarded by the score.
    cagr_cap: float = 0.50
    #: Maximum Sharpe rewarded by the score.
    sharpe_cap: float = 3.0
    #: Maximum Sortino rewarded by the score.
    sortino_cap: float = 7.0
    #: Drawdown magnitude assigned zero quality.
    drawdown_cap: float = 0.70
    #: Initial Calmar saturation point; neighbours are diagnostics.
    calmar_cap: float = 5.0
    #: Minimum Calmar drawdown denominator.
    calmar_drawdown_floor: float = 0.01
    #: Daily return-risk denominator floor for Sharpe and Sortino.
    daily_risk_floor: float = 0.0001


class ScorePanel:
    """Completed daily metrics with per-cell missingness and v6-compatible ratios."""

    def __init__(self, universe, start, end, config: MatrixConfig, cache_dir: Path):
        self.config = config
        pairs = sorted([p for p in universe.iterate_pairs() if p.is_vault()], key=lambda p: str(p.pool_address).lower())
        self.pair_ids = [p.internal_id for p in pairs]
        self.pair_index = {pid: i for i, pid in enumerate(self.pair_ids)}
        self.names = {p.internal_id: p.get_vault_name() for p in pairs}
        self.addresses = {p.internal_id: str(p.pool_address).lower() for p in pairs}
        self.dates = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize() - pd.Timedelta(days=1))
        self.date_index = {ts: i for i, ts in enumerate(self.dates)}
        price_dates = pd.date_range(self.dates[0] - pd.Timedelta(days=max(PERIODS.values()) + 1), self.dates[-1] - pd.Timedelta(days=1))
        prices = np.full((len(price_dates), len(pairs)), np.nan)
        digest = hashlib.sha256(json.dumps(config.__dict__, sort_keys=True).encode())
        digest.update(Path(__file__).read_bytes())
        digest.update(str((start, end)).encode())
        for j, pair in enumerate(pairs):
            close = universe.data_universe.candles.get_candles_by_pair(pair.internal_id)["close"]
            close = close[~close.index.duplicated(keep="last")].where(lambda s: s > 0).reindex(price_dates)
            prices[:, j] = close.to_numpy()
            digest.update(str((pair.internal_id, pair.pool_address)).encode())
        digest.update(prices.tobytes())
        self.fingerprint = digest.hexdigest()
        cache = cache_dir / f"features-{self.fingerprint}.npz"
        if cache.exists():
            with np.load(cache) as stored:
                self.raw, self.floored, self.valid, self.nonflat = [stored[k] for k in ["raw", "floored", "valid", "nonflat"]]
            print(f"Loaded completed metric panel: {self.raw.shape}")
        else:
            shape = (len(self.dates), len(pairs))
            self.raw = np.full((*shape, len(FEATURES)), np.nan)
            self.floored = np.full((*shape, len(PERIODS) * 2), np.nan)
            self.valid = np.zeros((*shape, len(PERIODS)), dtype=bool)
            self.nonflat = np.zeros_like(self.valid, dtype=np.uint16)
            for j in tqdm(range(len(pairs)), desc="Completed metric panels", total=len(pairs)):
                series = pd.Series(prices[:, j], index=price_dates)
                returns = series.pct_change(fill_method=None)
                for k, (period, days) in enumerate(PERIODS.items()):
                    good = series.rolling(days + 1, min_periods=days + 1).count().eq(days + 1).reindex(self.dates - pd.Timedelta(days=1)).to_numpy()
                    mean = returns.rolling(days, min_periods=days).mean()
                    sigma = returns.rolling(days, min_periods=days).std()
                    downside = returns.clip(upper=0).pow(2).rolling(days, min_periods=days).mean().pow(0.5)
                    cagr = (series / series.shift(days)).pow(365 / days) - 1
                    sharpe = mean / sigma.replace(0, np.nan) * np.sqrt(365)
                    sortino = mean / downside.replace(0, np.nan) * np.sqrt(365)
                    windows = sliding_window_view(prices[:, j], days + 1)
                    safe = np.where(np.isfinite(windows), windows, 1.0)
                    dd = pd.Series(np.r_[np.full(days, np.nan), (safe / np.maximum.accumulate(safe, axis=1) - 1).min(axis=1)], index=price_dates)
                    calmar = cagr / dd.abs().clip(lower=config.calmar_drawdown_floor)
                    for m, values in enumerate([cagr, sharpe, sortino, dd, calmar]):
                        arr = values.reindex(self.dates - pd.Timedelta(days=1)).to_numpy()
                        self.raw[:, j, k * 5 + m] = np.where(good, arr, np.nan)
                    for m, risk in enumerate([sigma, downside]):
                        ratio = mean / risk.clip(lower=config.daily_risk_floor) * np.sqrt(365)
                        self.floored[:, j, k * 2 + m] = np.where(good, ratio.reindex(self.dates - pd.Timedelta(days=1)), np.nan)
                    self.valid[:, j, k] = good
                    self.nonflat[:, j, k] = returns.abs().gt(1e-12).astype(float).rolling(days, min_periods=days).sum().reindex(self.dates - pd.Timedelta(days=1)).fillna(0).to_numpy().astype(np.uint16)
            np.savez_compressed(cache, raw=self.raw, floored=self.floored, valid=self.valid, nonflat=self.nonflat)
        assert not np.isinf(self.raw).any()

    def cell_scores(self, feature, missing=False, profile="requested", calmar_cap=5.0):
        k, m = divmod(feature, 5)
        values = self.raw[:, :, feature]
        if m in (1, 2) and not missing:
            values = self.floored[:, :, k * 2 + m - 1]
        caps = [1.0 if profile == "legacy" else self.config.cagr_cap, self.config.sharpe_cap, 3.0 if profile == "legacy" else self.config.sortino_cap, self.config.drawdown_cap, calmar_cap]
        score = 1 - np.minimum(np.abs(values), caps[m]) / caps[m] if m == 3 else np.clip(values / caps[m], 0, 1)
        return score if missing else np.nan_to_num(score, nan=0.0)

    def score_values(self, weights, calmar_cap=5.0, missing=False, profile="requested"):
        w = np.asarray(weights, dtype=float)
        assert len(w) == len(FEATURES) and (w >= 0).all() and abs(w.sum() - 1) < 1e-9
        values = np.zeros(self.raw.shape[:2])
        for i in np.flatnonzero(w):
            values += w[i] * self.cell_scores(i, missing=missing, profile=profile, calmar_cap=calmar_cap)
        finite = values[np.isfinite(values)]
        assert ((finite >= -1e-12) & (finite <= 1 + 1e-12)).all()
        return values

    def diagnostics(self, start=None, end=None):
        mask = (self.dates >= pd.Timestamp(start or self.dates[0])) & (self.dates < pd.Timestamp(end or self.dates[-1] + pd.Timedelta(days=1)))
        rows = []
        for i, (period, metric) in enumerate(FEATURES):
            k = i // 5
            valid = self.valid[mask, :, k]
            score = self.cell_scores(i)[mask]
            available = score[valid]
            rows.append({"Period": period, "Metric": metric, "Coverage": valid.mean(), "Undefined raw fraction when complete": (~np.isfinite(self.raw[mask, :, i])[valid]).mean() if valid.any() else np.nan, "Zero fraction when available": (available == 0).mean() if len(available) else np.nan, "Saturated fraction when available": (available >= 1).mean() if len(available) else np.nan, "Flat full windows": int((valid & (self.nonflat[mask, :, k] == 0)).sum())})
        return pd.DataFrame(rows)


def weight_key(weights):
    return hashlib.sha256(np.asarray(weights, dtype=float).round(10).tobytes()).hexdigest()[:16]


def weight_table(weights):
    return pd.DataFrame({"Period": [p for p, m in FEATURES], "Metric": [m for p, m in FEATURES], "Weight": weights}).query("Weight > 0").sort_values("Weight", ascending=False)


class MatrixIndicators:
    """Proxy only the ranking score; all original indicators remain accessible."""

    def __init__(self, original, panel, values, timestamp):
        self.original = original
        self.panel = panel
        self.values = values
        self.timestamp = pd.Timestamp(timestamp)

    def get_indicator_value(self, name, *args, **kwargs):
        if name == "matrix_score":
            pair = kwargs["pair"]
            i = self.panel.date_index.get(self.timestamp)
            j = self.panel.pair_index.get(pair.internal_id)
            return float(self.values[i, j]) if i is not None and j is not None else 0.0
        return self.original.get_indicator_value(name, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.original, name)


def make_matrix_decision(strategy, panel, values, sizing, allocator, ledger, missing=False, profile="requested"):
    """Use v11's source selection, operational checks and execution machinery."""
    source = strategy.decide_trades

    def decide(input):
        assert input.execution_context.mode.is_backtesting()
        original_compute = strategy.compute_sizing_weights
        original_factory = strategy.AlphaModel
        models = []

        def sizing_weights(selected_pair_ids, inv_vol_by_id, signal_by_id, **kwargs):
            method = "composite" if sizing == "score" else sizing
            options = {**kwargs, "method": method}
            weights = original_compute(selected_pair_ids, inv_vol_by_id, signal_by_id, **options)
            if missing:
                return weights
            return {pid: value if signal_by_id.get(pid, 0) > 0 else 0.0 for pid, value in weights.items()}

        def factory(*args, **kwargs):
            model = AuditedAlphaModel(*args, sizing_mode=allocator, allocation_ledger=ledger, **kwargs)
            models.append(model)
            return model

        strategy.compute_sizing_weights = sizing_weights
        strategy.AlphaModel = factory
        try:
            proxy = MatrixIndicators(input.indicators, panel, values, input.timestamp)
            trades = source(replace(input, indicators=proxy))
            for model in models:
                for row in model._audit_rows:
                    signal = model.signals[row["Pair id"]]
                    row["Final target (USD)"] = float(signal.position_target or 0)
                    row["Ranking score"] = proxy.get_indicator_value("matrix_score", pair=signal.pair)
                    row["Missing"] = missing
                    row["Profile"] = profile
                    row["Sizing"] = sizing
                    row["Unscored"] = not np.isfinite(row["Ranking score"])
                    row["Normalised accepted weight"] = float(signal.normalised_weight or 0)
                    row["Flags"] = ",".join(sorted(f.value for f in signal.flags))
                    if allocator == "accepted_dollar_cap":
                        assert row["Final target (USD)"] <= row["Accepted allocation (USD)"] + 1e-6
                        assert row["Accepted allocation (USD)"] <= row["Intended allocation (USD)"] + 1e-6
            return trades
        finally:
            strategy.compute_sizing_weights = original_compute
            strategy.AlphaModel = original_factory

    return decide


class MatrixBacktester:
    """Cache complete engine evaluations using sources, prices and guard hashes."""

    def __init__(self, strategy, universe, indicators, parameters, client, panel, folder, fingerprint, indicator_storage=None):
        self.indicator_storage = indicator_storage
        self.strategy = strategy
        self.universe = universe
        self.indicators = indicators
        self.parameters = parameters
        self.client = client
        self.panel = panel
        self.folder = folder / fingerprint[:16]
        self.folder.mkdir(exist_ok=True)
        self.records = {}
        self.values = {}
        self.durations = []
        self.engine_calls = 0

    def run(self, weights, start, end, n=6, sizing="equal", allocator="parent", keep=False, source_control=False, calmar_cap=5.0, missing=False, profile="requested"):
        tag = json.dumps({"w": list(np.asarray(weights).round(10)), "start": str(start), "end": str(end), "n": n, "sizing": sizing, "allocator": allocator, "source_control": source_control, "calmar_cap": calmar_cap, "missing": missing, "profile": profile}, sort_keys=True)
        key = hashlib.sha256(tag.encode()).hexdigest()[:24]
        metrics_path = self.folder / f"{key}.json"
        state_path = self.folder / f"{key}-state.json"
        parameters = deepcopy(self.parameters)
        parameters["backtest_start"] = start
        parameters["backtest_end"] = end
        if not source_control:
            parameters["max_assets_in_portfolio"] = parameters["max_capacity_assets"] = n
            parameters["entry_rank"] = n
            parameters["exit_rank"] = n + 2
            parameters["selection_score_indicator"] = "matrix_score"
            parameters["weighting_method"] = sizing
        cached = metrics_path.exists() and (not keep or state_path.exists())
        if cached:
            metrics = json.loads(metrics_path.read_text())
            result = BacktestResult(State.read_json_file(state_path), self.universe, {}, self.indicators) if keep else None
            ledger = pd.read_csv(self.folder / f"{key}-allocations.csv", parse_dates=["Date"]) if keep and not source_control else pd.DataFrame()
        else:
            started = time.monotonic()
            ledger = []
            vk = (weight_key(weights), calmar_cap, missing, profile)
            if not source_control and vk not in self.values:
                self.values[vk] = self.panel.score_values(weights, calmar_cap, missing=missing, profile=profile)
            decide = self.strategy.decide_trades if source_control else make_matrix_decision(self.strategy, self.panel, self.values[vk], sizing, allocator, ledger, missing=missing, profile=profile)
            self.strategy.apply_vault_redemption_capital_fee(self.universe, float(parameters.vault_redemption_capital_fee))
            result = run_backtest_inline(engine_version=self.strategy.trading_strategy_engine_version, client=self.client, decide_trades=decide, universe=self.universe, indicator_storage=self.indicator_storage, indicator_combinations=self.indicators.indicator_combinations, parameters=parameters, cycle_duration=parameters.cycle_duration, initial_deposit=parameters.initial_cash, reserve_currency=ReserveCurrency.usdc, trade_routing=parameters.routing, max_slippage=parameters.slippage_tolerance_pct, start_at=start, end_at=end, max_workers=1, name=f"Matrix {key}", strategy_logging=False)
            state = result.state
            equity = calculate_equity_curve(state)
            daily = calculate_returns(equity).resample("1D").sum(min_count=1).fillna(0)
            weights_daily = calculate_asset_weights(state).unstack().resample("1D").last().reindex(daily.index).ffill().fillna(0)
            reserve = state.portfolio.get_default_reserve_asset()[0].token_symbol
            daily_equity = equity.resample("1D").last().reindex(daily.index).ffill()
            counts = {}
            for snapshots in state.stats.positions.values():
                for snap in snapshots:
                    if snap.value > 0:
                        counts[snap.calculated_at] = counts.get(snap.calculated_at, 0) + 1
            trades = list(state.portfolio.get_all_trades())
            cost = 0.0
            turnover = 0.0
            for t in trades:
                if t.is_success() and (t.is_buy() or t.is_sell()):
                    turnover += float(t.executed_reserve or 0)
                    if t.is_sell():
                        cost += abs(float(t.executed_quantity or 0)) * float(t.planned_mid_price or 0) * float(t.other_data.get("backtest_vault_redemption_fee", 0))
            finite = lambda v: float(v) if np.isfinite(v) else 0.0
            metrics = {"Final equity (USD)": float(equity.iloc[-1]), "CAGR": finite(calculate_cagr(daily)), "Sharpe": finite(calculate_sharpe(daily, periods=365)) if daily.std() > 0 else 0.0, "Sortino": finite(calculate_sortino(daily, periods=365)) if daily.lt(0).any() else 0.0, "Maximum drawdown": finite(calculate_max_drawdown(daily)), "Mean cash weight": float((weights_daily[reserve] / daily_equity).mean()), "Cycle-clock Sharpe": finite(calculate_sharpe(calculate_returns(equity), periods=365 / 2)) if calculate_returns(equity).std() > 0 else 0.0, "Trades": len(trades), "Maximum vaults held": max(counts.values(), default=0), "Modelled redemption costs (USD)": cost, "Gross trade turnover (USD)": turnover}
            assert metrics["Maximum vaults held"] <= n, (key, metrics["Maximum vaults held"], n)
            ledger = pd.DataFrame(ledger)
            if keep:
                state.write_json_file(state_path)
                if not source_control:
                    ledger.to_csv(self.folder / f"{key}-allocations.csv", index=False)
            metrics_path.write_text(json.dumps(metrics, allow_nan=False))
            self.engine_calls += 1
            self.durations.append(time.monotonic() - started)
        self.records[key] = {**metrics, "key": key, "weights": list(weights), "start": str(start), "end": str(end), "positions": n, "sizing": sizing, "allocator": allocator, "calmar_cap": calmar_cap, "source_control": source_control, "missing": missing, "profile": profile}
        if not keep:
            return metrics
        equity = calculate_equity_curve(result.state)
        daily = calculate_returns(equity).resample("1D").sum(min_count=1).fillna(0)
        return {"result": result, "parameters": parameters, "equity": equity, "daily_returns": daily, "metrics": metrics, "allocation_df": ledger, "cache_key": key}

    def remaining(self, jobs):
        seconds = np.mean(self.durations) if self.durations else 8.0
        return seconds * jobs / 60


def development_result(evaluator, weights, folds, n=6, sizing="equal", calmar_cap=5.0, missing=False, profile="requested"):
    results = [evaluator.run(weights, start, end, n=n, sizing=sizing, calmar_cap=calmar_cap, missing=missing, profile=profile) for start, end in folds]
    cagr = np.array([r["CAGR"] for r in results])
    sharpe = np.array([r["Sharpe"] for r in results])
    return {"CAGR objective": float(cagr.mean() - 0.25 * cagr.std()), "Sharpe objective": float(sharpe.mean() - 0.25 * sharpe.std()), "Mean fold CAGR": float(cagr.mean()), "Mean fold Sharpe": float(sharpe.mean()), "Worst fold drawdown": min(r["Maximum drawdown"] for r in results), "Weights": list(weights), "Active cells": int(np.count_nonzero(weights)), "Weight key": weight_key(weights), "Missing": missing, "Profile": profile, "Sizing": sizing}


def sparse_search(evaluator, screen, folds, objective, iterations=18, seed=104):
    """Beam proposals with two, three and four active cells, then fixed support refinements."""
    rng = np.random.default_rng(seed)
    ordered = sorted(screen, key=lambda r: r[objective], reverse=True)
    proposals = []
    available = [r for r in ordered if r["Active cells"] == 1][:12]
    beam = {k: [r for r in ordered if r["Active cells"] == k][:3] for k in [1, 2, 3, 4]}
    seen = {r["Weight key"] for r in screen}
    for iteration in tqdm(range(iterations), desc=f"Sparse {objective}", total=iterations):
        k = 2 + min(iteration // 6, 2)
        bases = beam[k - 1] or ordered[:3]
        for attempt in range(100):
            base = bases[int(rng.integers(len(bases)))]["Weights"]
            w = np.asarray(base, dtype=float).copy()
            free = [r for r in available if r["Active cells"] == 1 and not np.any((w > 0) & (np.asarray(r["Weights"]) > 0))]
            if not free:
                free = [r for r in ordered if r["Active cells"] == 1 and not np.any((w > 0) & (np.asarray(r["Weights"]) > 0))]
            feature = free[int(rng.integers(len(free)))]["Weights"]
            mass = [0.25, 0.4, 0.5, 0.6, 0.75, 0.5][iteration % 6] if k == 2 else [0.25, 0.5][iteration % 2]
            w = (1 - mass) * w + mass * np.asarray(feature)
            if weight_key(w) not in seen:
                break
        seen.add(weight_key(w))
        print(f"Sparse iteration {iteration+1}/{iterations}, {k} cells; estimate {evaluator.remaining((iterations-iteration)*len(folds)):.1f} minutes remaining")
        row = development_result(evaluator, w, folds, missing=bool(iteration % 2), sizing=("equal", "score", "inverse_variance")[iteration % 3])
        row["Search objective"] = objective
        row["Iteration"] = iteration + 1
        proposals.append(row)
        beam[k] = sorted(beam[k] + [row], key=lambda r: r[objective], reverse=True)[:3]
    best = max(screen + proposals, key=lambda r: r[objective])
    # Refine the winning support without expanding it; neighbours also diagnose sensitivity.
    refinements = []
    active = np.flatnonzero(best["Weights"])
    for i in active:
        for delta in [-0.10, 0.10]:
            w = np.asarray(best["Weights"], dtype=float).copy()
            w[i] = max(w[i] + delta, 0.01)
            w /= w.sum()
            refinements.append(development_result(evaluator, w, folds, missing=best["Missing"], profile=best["Profile"], sizing=best["Sizing"]))
    best = max(screen + proposals + refinements, key=lambda r: r[objective])
    return best, proposals, refinements
