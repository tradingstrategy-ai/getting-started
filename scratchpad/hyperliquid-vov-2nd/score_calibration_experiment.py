"""Controlled scoring, selection and cash experiments for notebook 05."""

import datetime
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import inspect
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import score_matrix
from score_matrix import FEATURES, PERIODS, MatrixBacktester, MatrixConfig, ScorePanel, MatrixIndicators
from accepted_dollar_cap import AuditedAlphaModel
from tradeexecutor.strategy.alpha_model import TradingPairSignalFlags
from tradeexecutor.strategy.execution_context import notebook_execution_context
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
from tradeexecutor.strategy.pandas_trader.trading_universe_input import CreateTradingUniverseInput
from tradeexecutor.strategy.universe_model import UniverseOptions
from tradeexecutor.state.types import Percent
from tradeexecutor.strategy.redemption import DepositCheckStage


@dataclass(frozen=True)
class Calibration:
    """One predeclared experiment, with scoring and execution choices separated."""

    #: Human-readable research identity.
    name: str
    #: Scoring transform: hard clip, blended clips or smooth saturation.
    transform: str = "hard"
    #: CAGR upper clip, or half-saturation scale for a smooth score.
    cagr_scale: Percent = 1.0
    #: Sortino upper clip, or half-saturation scale for a smooth score.
    sortino_scale: float = 3.0
    #: Risk lookback; 45 replicates the original formula.
    risk_days: int = 45
    #: Apply the recorded daily ratio denominator floor independently of missingness.
    ratio_floor: bool = False
    #: Fill missing component scores with zero instead of propagating missingness.
    missing_zero: bool = False
    #: Redeploy residual dollars among existing eligible selected holdings.
    refill: bool = False
    #: Check entrant deposit availability before its score can displace incumbents.
    feasible_entry: bool = False
    #: Required score advantage for replacing an eligible incumbent.
    hurdle: float = 0.0
    #: Stable alternative ordering within exactly equal scores; zero keeps address order.
    tie_seed: int = 0
    #: Minimum number of non-flat risk-window marks; zero preserves the source universe.
    minimum_nonflat: int = 0

    @property
    def key(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()[:16]


def configurations():
    """Predeclare 18 score calibrations and separate mechanism diagnostics."""
    grid = [Calibration(f"Hard C{c:g} S{s:g}", cagr_scale=c, sortino_scale=s) for c in (0.5, 1.0, 2.0) for s in (3.0, 7.0, 12.0)]
    grid += [Calibration("Blend 45d", transform="blend"), Calibration("Blend 46d", transform="blend", risk_days=46), Calibration("Legacy 46d", risk_days=46)]
    grid += [Calibration(f"Smooth C{c:g} S{s:g}", transform="smooth", cagr_scale=c, sortino_scale=s) for c, s in [(0.5, 3.0), (1.0, 3.0), (1.0, 7.0)]]
    grid += [Calibration("Ratio floor only", ratio_floor=True), Calibration("Zero missing only", missing_zero=True), Calibration("Activity filter 10/45", minimum_nonflat=10)]
    assert len(grid) == 18
    baseline = grid[3]
    assert baseline.cagr_scale == 1 and baseline.sortino_scale == 3
    blend = next(c for c in grid if c.name == "Blend 46d")
    smooth = next(c for c in grid if c.name == "Smooth C1 S3")
    mechanisms = [replace(c, name=f"{c.name} / refill", refill=True) for c in (baseline, blend, smooth)]
    mechanisms += [replace(baseline, name="Feasible entrants", feasible_entry=True)]
    mechanisms += [replace(baseline, name=f"Replacement hurdle {h:g}", feasible_entry=True, hurdle=h) for h in (0.025, 0.05)]
    mechanisms += [replace(baseline, name=f"Tie seed {seed}", tie_seed=seed) for seed in (11, 23, 37, 53, 71)]
    confirmations = [baseline, blend, smooth, replace(baseline, name=f"{baseline.name} / refill", refill=True), replace(blend, name="Blend 46d / refill", refill=True), replace(baseline, name="Feasible entrants", feasible_entry=True)]
    return grid, mechanisms, confirmations


def load_snapshot(strategy, parameters, client, folder, indicator_storage_path=None):
    """Freeze one universe snapshot for every control and treatment in notebook 05."""
    path = folder / "universe.pickle"
    if path.exists():
        with path.open("rb") as handle:
            universe = pickle.load(handle)
    else:
        options = UniverseOptions.from_strategy_parameters_class(strategy.Parameters, notebook_execution_context)
        request = CreateTradingUniverseInput(execution_context=notebook_execution_context, client=client, timestamp=None, parameters=parameters, universe_options=options, execution_model=None)
        universe = strategy.create_trading_universe(request)
        with path.open("wb") as handle:
            pickle.dump(universe, handle, pickle.HIGHEST_PROTOCOL)
    storage_options = {} if indicator_storage_path is None else {"indicator_storage_path": indicator_storage_path}
    indicators = calculate_and_load_indicators_inline(**storage_options, strategy_universe=universe, parameters=parameters, create_indicators=strategy.create_indicators, execution_context=notebook_execution_context, max_workers=1)
    first = min(universe.data_universe.candles.get_candles_by_pair(p.internal_id).index.min() for p in universe.iterate_pairs() if p.is_vault())
    panel = ScorePanel(universe, pd.Timestamp(first).to_pydatetime(), parameters.backtest_end, MatrixConfig(), folder)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return universe, indicators, panel, digest


def scores(panel, config):
    """Use completed T−1 metrics, fixed 60/40 coefficients and source missing semantics."""
    period = next(p for p, d in PERIODS.items() if d == config.risk_days)
    ci = FEATURES.index(("1y", "CAGR"))
    si = FEATURES.index((period, "Sortino"))
    c = panel.raw[:, :, ci]
    s = panel.floored[:, :, si // 5 * 2 + 1] if config.ratio_floor else panel.raw[:, :, si]

    def hard(v, cap):
        return np.clip(v / cap, 0, 1)

    def smooth(v, scale):
        positive = np.maximum(v, 0)
        return positive / (positive + scale)

    if config.transform == "blend":
        values = 0.3 * hard(c, 0.5) + 0.3 * hard(c, 1.0) + 0.2 * hard(s, 3.0) + 0.2 * hard(s, 7.0)
    else:
        transform = hard if config.transform == "hard" else smooth
        values = 0.6 * transform(c, config.cagr_scale) + 0.4 * transform(s, config.sortino_scale)
    if config.missing_zero:
        if config.transform == "blend":
            values = 0.3 * np.nan_to_num(hard(c, 0.5)) + 0.3 * np.nan_to_num(hard(c, 1.0)) + 0.2 * np.nan_to_num(hard(s, 3.0)) + 0.2 * np.nan_to_num(hard(s, 7.0))
        else:
            values = 0.6 * np.nan_to_num(transform(c, config.cagr_scale)) + 0.4 * np.nan_to_num(transform(s, config.sortino_scale))
    return values


class ExperimentPanel:
    """Supply a registered score array to the unchanged backtest cache machinery."""

    def __init__(self, panel):
        self.panel = panel
        self.configs = {}

    def __getattr__(self, name):
        return getattr(self.panel, name)

    def score_values(self, weights, calmar_cap=5.0, missing=True, profile=None):
        return scores(self.panel, self.configs[profile])


class ResearchAlphaModel(AuditedAlphaModel):
    """Redeploy residual budget after deposit checks, before trade generation."""

    def __init__(self, *args, refill=False, cash_ledger=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.refill = refill
        self.cash_ledger = cash_ledger

    def calculate_target_positions(self, position_manager, investable_equity=None):
        signals = list(self._get_allocatable_signals())
        budget = float(self.investable_equity or 0.0)
        before = {s.pair.internal_id: float(s.position_target or 0.0) for s in signals}
        residual = max(budget - sum(before.values()), 0.0)
        blocked = sum(float(s.other_data.get("missed_deposit_usd") or 0.0) for s in signals)
        recovered = 0.0
        if self.refill and residual > 0:
            limits = {r["Pair id"]: min(r["Concentration limit (USD)"], r["TVL (USD)"] * 0.33) for r in self._audit_rows}
            rooms = {}
            for signal in signals:
                if signal.carry_forward_position or not position_manager.is_whitelisted_vault(signal.pair):
                    continue
                check = position_manager.pricing_model.check_deposit(self.timestamp, signal.pair, stage=DepositCheckStage.buy_rebalance)
                signal.set_deposit_check_result(check)
                if not check.can_deposit or TradingPairSignalFlags.cannot_deposit in signal.flags:
                    continue
                pid = signal.pair.internal_id
                rooms[pid] = max(limits.get(pid, 0.0) - before[pid], 0.0)
            additions = {pid: 0.0 for pid in rooms}
            by_id = {s.pair.internal_id: s for s in signals}
            for _ in range(len(rooms) + 1):
                free = [pid for pid, room in rooms.items() if room - additions[pid] > 1e-6 and by_id[pid].raw_weight > 0]
                left = residual - sum(additions.values())
                if not free or left < 1e-6:
                    break
                mass = sum(float(by_id[pid].raw_weight) for pid in free)
                amounts = {pid: min(left * float(by_id[pid].raw_weight) / mass, rooms[pid] - additions[pid]) for pid in free}
                for pid, amount in amounts.items():
                    additions[pid] += amount
            reference = float(position_manager.get_current_portfolio().get_total_equity())
            threshold = max(5.0, reference * 0.0005)
            for pid, amount in additions.items():
                if amount < threshold:
                    continue
                signal = by_id[pid]
                signal.position_target = before[pid] + amount
                assert signal.position_target <= limits[pid] + 1e-6
                signal.other_data["research_refill_usd"] = amount
                recovered += amount
            accepted = sum(float(s.position_target or 0.0) for s in signals)
            assert accepted <= budget + 1e-6
            self.accepted_investable_equity = accepted
            self.size_risk_discarded_value = max(budget - accepted, 0.0)
            for signal in signals:
                signal.normalised_weight = float(signal.position_target or 0.0) / accepted if accepted else 0.0
        if self.cash_ledger is not None:
            self.cash_ledger.append({"Date": self.timestamp, "Budget (USD)": budget, "Residual before refill (USD)": residual, "Blocked top-ups (USD)": blocked, "Recovered target (USD)": recovered, "Residual after refill (USD)": max(residual - recovered, 0.0)})
        return super().calculate_target_positions(position_manager, investable_equity)


def research_selector(strategy, config):
    """Compile guarded research edits in memory against the exact source function."""
    source = inspect.getsource(strategy.decide_trades)
    source = source.replace("def decide_trades(", "def research_decide_trades(", 1)
    if config.feasible_entry:
        old = "if pair_id not in held_pair_ids and rank_by_id[pair_id] <= int(parameters.entry_rank)"
        assert source.count(old) == 1
        source = source.replace(old, old + " and check_entry_candidate(strategy_universe.get_pair_by_id(pair_id)).can_deposit")
    if config.tie_seed:
        old = "(-item[2], _v11_pair_address(item[1]))"
        assert source.count(old) == 1
        source = source.replace(old, "(-item[2], _research_tie_key(item[1]))")
    namespace = dict(strategy.__dict__)
    namespace["_research_tie_key"] = lambda pair: hashlib.sha256(f"{config.tie_seed}:{str(pair.pool_address).lower()}".encode()).hexdigest()
    exec(compile(source, "<notebook-05-selector>", "exec"), namespace)
    return namespace["research_decide_trades"], namespace


def decision_factory(strategy, panel, values, config, ledger, cash_ledger):
    """Keep source sizing and execution while intervening at documented boundaries."""
    function, namespace = research_selector(strategy, config)

    def decide(input):
        models = []

        def factory(*args, **kwargs):
            model = ResearchAlphaModel(*args, sizing_mode="parent", allocation_ledger=ledger, refill=config.refill, cash_ledger=cash_ledger, **kwargs)
            models.append(model)
            return model

        namespace["AlphaModel"] = factory
        proxy = MatrixIndicators(input.indicators, panel, values, input.timestamp)
        if config.minimum_nonflat:
            original = proxy.get_indicator_value

            def get_indicator_value(name, *args, **kwargs):
                result = original(name, *args, **kwargs)
                if name == "inclusion_criteria" and result is not None:
                    date = panel.date_index[pd.Timestamp(input.timestamp)]
                    k = list(PERIODS).index(next(p for p, d in PERIODS.items() if d == config.risk_days))
                    result = [pid for pid in result if panel.nonflat[date, panel.pair_index[pid], k] >= config.minimum_nonflat]
                return result

            proxy.get_indicator_value = get_indicator_value
        trades = function(replace(input, indicators=proxy))
        for model in models:
            for row in model._audit_rows:
                signal = model.signals[row["Pair id"]]
                row["Final target (USD)"] = float(signal.position_target or 0.0)
                row["Ranking score"] = proxy.get_indicator_value("matrix_score", pair=signal.pair)
                row["Refill (USD)"] = float(signal.other_data.get("research_refill_usd") or 0.0)
                row["Unscored"] = not np.isfinite(row["Ranking score"])
        return trades

    return decide


class CalibrationBacktester(MatrixBacktester):
    """Cache real engine executions under data, code and configuration fingerprints."""

    def run_config(self, config, start, end, keep=True, source_control=False):
        self.panel.configs[config.key] = config
        original = score_matrix.make_matrix_decision
        parameters = self.parameters
        self.parameters = deepcopy(parameters)
        self.parameters["minimum_score_improvement"] = config.hurdle
        cash_ledger = []
        score_matrix.make_matrix_decision = lambda strategy, panel, values, sizing, allocator, ledger, **kwargs: decision_factory(strategy, panel, values, config, ledger, cash_ledger)
        weights = np.zeros(len(FEATURES))
        weights[FEATURES.index(("1y", "CAGR"))] = 1
        try:
            result = super().run(weights, start, end, n=6, sizing="inverse_variance", missing=True, profile=config.key, keep=keep, source_control=source_control)
        finally:
            score_matrix.make_matrix_decision = original
            self.parameters = parameters
        if keep:
            path = self.folder / f'{result["cache_key"]}-cash.csv'
            if cash_ledger:
                pd.DataFrame(cash_ledger).to_csv(path, index=False)
            result["cash_ledger"] = pd.read_csv(path, parse_dates=["Date"]) if path.exists() else pd.DataFrame()
            result["config"] = config
        return result


def feature_audit(strategy, universe, indicators, panel, parameters, start, end):
    """Measure per-date feature associations with strictly censored future NAV labels.

    Current membership and guard permissions remain source-archive assumptions.
    The diagnostic set applies source inclusion, gate, quarantine and whitelist
    filters; individual portfolio exclusions and entry deposit state are not
    observable here. Labels are gross vault NAV outcomes, not executable PnL.
    """
    from tradeexecutor.curator.curator import is_quarantined
    from tqdm_loggable.auto import tqdm

    dates = panel.dates[(panel.dates >= start) & (panel.dates < end)][::2]
    lookup = replace(indicators, timestamp=None)
    guard = strategy.load_hypercore_vault_whitelist(strategy._guard_record_file())
    rows = []
    bins = []
    correlations = []
    coverage = []
    prices = pd.DataFrame({pid: universe.data_universe.candles.get_candles_by_pair(pid)["close"] for pid in panel.pair_ids}).sort_index()
    returns = prices.pct_change(fill_method=None)
    targets = {}
    for horizon in (14, 30, 60):
        future = returns.shift(-horizon)
        mean = future.rolling(horizon, min_periods=horizon).mean()
        sigma = future.rolling(horizon, min_periods=horizon).std().replace(0, np.nan)
        targets[horizon] = {"Forward return": prices.shift(-horizon) / prices - 1, "Forward Sharpe": mean / sigma * np.sqrt(365)}
    for date in tqdm(dates, desc="Causal feature diagnostics"):
        lookup.prepare_decision_cycle(0, date)
        included = lookup.get_indicator_value("inclusion_criteria", na_conversion=False)
        if included is None:
            continue
        eligible = []
        for pid in included:
            pair = universe.get_pair_by_id(pid)
            gate = lookup.get_indicator_value("return_gate", pair=pair)
            if gate is None or not np.isfinite(gate) or gate <= parameters.gate_threshold or is_quarantined(pair.pool_address, date):
                continue
            address = str(pair.pool_address).lower()
            if address in strategy.MANUAL_BLACKLIST or address in strategy.MASKED_VAULTS or not guard.allows(address):
                continue
            eligible.append(pid)
        if len(eligible) < 10:
            continue
        i = panel.date_index[date]
        js = [panel.pair_index[pid] for pid in eligible]
        values = panel.raw[i, js, :]
        labels = {(h, outcome): frame.loc[date - pd.Timedelta(days=1), eligible].to_numpy() for h, outcomes in targets.items() if date + pd.Timedelta(days=h) <= pd.Timestamp(end) for outcome, frame in outcomes.items()}
        for feature, (period, metric) in enumerate(FEATURES):
            if period == "45d compatibility":
                continue
            v = values[:, feature]
            finite = np.isfinite(v)
            coverage.append({"Date": date, "Period": period, "Metric": metric, "Eligible vaults": len(eligible), "Finite feature": int(finite.sum()), "Non-flat 1m": int((panel.nonflat[i, js, 0] > 0).sum())})
            for (horizon, outcome), target in labels.items():
                good = finite & np.isfinite(target)
                if good.sum() < 10 or np.unique(v[good]).size < 2 or np.unique(target[good]).size < 2:
                    continue
                rho = float(spearmanr(v[good], target[good]).statistic)
                rows.append({"Date": date, "Period": period, "Metric": metric, "Horizon": horizon, "Outcome": outcome, "IC": rho, "Vaults": int(good.sum())})
                if outcome == "Forward return":
                    ranks = pd.Series(v[good]).rank(method="average", pct=True).to_numpy()
                    for bucket in range(1, 6):
                        pick = (ranks > (bucket - 1) / 5) & (ranks <= bucket / 5)
                        if pick.any():
                            bins.append({"Date": date, "Period": period, "Metric": metric, "Horizon": horizon, "Score quintile": bucket, "Mean forward return": float(target[good][pick].mean()), "Vaults": int(pick.sum())})
        for period in ("45d compatibility", "3m", "1y"):
            frame = pd.DataFrame(values[:, [FEATURES.index((period, m)) for m in ("CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar")]], columns=["CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar"])
            corr = frame.corr("spearman", min_periods=10)
            for a in corr.index:
                for b in corr.columns:
                    correlations.append({"Date": date, "Period": period, "Row": a, "Column": b, "Rho": corr.loc[a, b]})
    return pd.DataFrame(rows), pd.DataFrame(bins), pd.DataFrame(correlations), pd.DataFrame(coverage)


def ic_summary(frame, seed=105):
    """Summarise per-date IC with moving-block exploratory uncertainty bands."""
    rng = np.random.default_rng(seed)
    rows = []
    for keys, group in frame.groupby(["Period", "Metric", "Horizon", "Outcome"], sort=False):
        values = group.sort_values("Date").IC.to_numpy()
        block = max(7, int(np.ceil(keys[2] / 2)))
        length = len(values)
        starts = rng.integers(0, max(length - block + 1, 1), size=(200, int(np.ceil(length / block))))
        index = (starts[:, :, None] + np.arange(block)).reshape(200, -1)[:, :length].clip(0, length - 1)
        draws = values[index].mean(axis=1)
        rows.append(dict(zip(["Period", "Metric", "Horizon", "Outcome"], keys), **{"Mean IC": values.mean(), "Positive IC fraction": (values > 0).mean(), "Decision dates": length, "Mean paired vaults": group.Vaults.mean(), "Lower block band": np.quantile(draws, 0.025), "Upper block band": np.quantile(draws, 0.975)}))
    return pd.DataFrame(rows)
