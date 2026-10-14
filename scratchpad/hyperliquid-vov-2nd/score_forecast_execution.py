"""Frozen, research-only admission floors for experiment 08.

The source selector, incumbent hysteresis, fees and caps are retained. Policy
intervention happens after the proposed basket is known; it never selects a
replacement entrant. The random controls match rejected counts exactly and
proposed dollars approximately on each decision, not on realised profits.
"""

import datetime
import hashlib
import io
import json
import time
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from accepted_dollar_cap import AuditedAlphaModel, calculate_position_profit_curves
from score_matrix import MatrixIndicators
from repaired_data_replay import RUN_ROOT
from tradeexecutor.backtest.backtest_runner import run_backtest_inline
from tradeexecutor.state.state import State
from tradeexecutor.strategy.reserve_currency import ReserveCurrency
from tradeexecutor.analysis.weights import calculate_asset_weights
from tradeexecutor.visual.equity_curve import calculate_equity_curve, calculate_returns
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe, calculate_sortino, calculate_max_drawdown
from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined

ARTIFACT_DIR = RUN_ROOT / "08" / "execution"
METHODS = ("v11", "blend_46d", "focal_four")
PERIODS = {"2026": (datetime.datetime(2026, 1, 1), datetime.datetime(2026, 10, 5)), "Long": (datetime.datetime(2023, 3, 1), datetime.datetime(2026, 10, 5))}
RANDOM_SEEDS = (8081, 8082, 8083)


def freeze_execution_design():
    """Save the policy source hash before reading outcomes or running engines."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    design = {"source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "methods": METHODS, "positions": [6, 7], "thresholds": ["none", "monthly_absolute", "percentile_75"], "treatments": ["slot_to_cash", "renormalise_within_caps"], "random_seeds": RANDOM_SEEDS, "random_reference": "percentile_75; count-exact, approximately dollar-matched on same proposed entrants", "missing_policy": "source-compatible, retain unscored new-entry behaviour", "held_topups": "unchanged", "cadence": "2 days", "variance_days": 90, "allocation_pct": 0.98, "concentration_cap": 0.33, "pool_cap": 0.33, "selection": "source selected IDs and hysteresis; no extra entrants/refill", "primary_horizon_days": 30, "periods": {k: list(map(str, v)) for k, v in PERIODS.items()}}
    (ARTIFACT_DIR / "design.json").write_text(json.dumps(design, indent=2))
    return design


class FloorPolicy:
    """Read immutable monthly training decisions and current eligible scores."""

    def __init__(self, kind, monthly, method_id, seed=None, exclude_unscored=False):
        self.kind = kind
        self.method_id = method_id
        self.seed = seed
        self.exclude_unscored = exclude_unscored
        self.monthly = monthly[monthly.method_id.eq(method_id)].copy() if len(monthly) else monthly.copy()
        if len(self.monthly) and "policy" in self.monthly:
            self.monthly = self.monthly[self.monthly.policy.eq("monthly_absolute")]
        if len(self.monthly) and "lookahead_days" in self.monthly:
            self.monthly = self.monthly[self.monthly.lookahead_days.eq(30)]
        if len(self.monthly):
            self.monthly["calibration_at"] = pd.to_datetime(self.monthly.calibration_at)
            self.monthly = self.monthly.sort_values("calibration_at")
        self.percentile_floor = np.nan

    def floor(self, timestamp):
        if self.kind in ("percentile_75", "random_percentile_75"):
            return self.percentile_floor, bool(np.isfinite(self.percentile_floor)), None
        if self.kind == "none" or not len(self.monthly):
            return np.nan, False, None
        prior = self.monthly[self.monthly.calibration_at <= pd.Timestamp(timestamp)]
        if prior.empty:
            return np.nan, False, None
        row = prior.iloc[-1]
        active = bool(row.get("active", False)) and pd.notna(row.get("floor", np.nan))
        latest = row.get("latest_training_target_at", None)
        if active and pd.notna(latest):
            assert pd.Timestamp(latest) < pd.Timestamp(row.calibration_at), "Unmatured threshold label"
        observed = row.get("latest_training_observed", None)
        if active and pd.notna(observed):
            assert pd.Timestamp(observed) < pd.Timestamp(row.calibration_at), "Threshold label was not observed before training"
        available = row.get("latest_training_available", None)
        if active and pd.notna(available):
            assert pd.Timestamp(available) < pd.Timestamp(row.calibration_at), "Training candle was incomplete at calibration"
        return float(row.floor) if active else np.nan, active, row.calibration_at

    def rejects(self, score, timestamp):
        floor, active, _ = self.floor(timestamp)
        if not np.isfinite(score):
            return self.exclude_unscored and self.kind != "none"
        return bool(active and np.isfinite(floor) and score < floor)


class AdmissionAlphaModel(AuditedAlphaModel):
    """Veto entry dollars or rerun the parent allocator on accepted raw weights."""

    def __init__(self, *args, held_ids, score_for_pair, policy, treatment, **kwargs):
        super().__init__(*args, sizing_mode="parent", **kwargs)
        self._held_ids = held_ids
        self._score_for_pair = score_for_pair
        self._policy = policy
        self._treatment = treatment

    def _normalise_weights_size_risk_positions(self, *args, **kwargs):
        initial = deepcopy(self.signals)
        super()._normalise_weights_size_risk_positions(*args, **kwargs)
        baseline_rows = self._audit_rows.copy()
        proposed = {pid: float(s.position_target or 0.0) for pid, s in self.signals.items()}
        entrants = [pid for pid, s in self.signals.items() if pid not in self._held_ids and not s.carry_forward_position and proposed[pid] > 0]
        blocked = [pid for pid in entrants if self._policy.rejects(self._score_for_pair(self.signals[pid].pair), self.timestamp)]
        expected = blocked.copy()
        dollar_error = 0.0
        if self._policy.seed is not None and blocked:
            # Candidate draws use the current policy state's own proposed entrants.
            # They are conditional controls, not counterfactuals sharing future state.
            digest = hashlib.sha256(f"{self._policy.seed}|{self.timestamp}".encode()).digest()
            rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
            target = sum(proposed[pid] for pid in blocked)
            draws = [rng.choice(entrants, size=len(blocked), replace=False).tolist() for _ in range(32)]
            blocked = min(draws, key=lambda ids: abs(sum(proposed[pid] for pid in ids) - target))
            dollar_error = sum(proposed[pid] for pid in blocked) - target
        if blocked and self._treatment == "renormalise_within_caps":
            self.signals = initial
            # For inverse variance these raw weights are 1/sigma^2; removing an
            # entrant before normalisation is identical to recomputing the
            # source inverse-variance weights on the accepted selected IDs.
            for pid in blocked:
                self.signals[pid].raw_weight = 0.0
            before = len(self._allocation_ledger)
            super()._normalise_weights_size_risk_positions(*args, **kwargs)
            del self._allocation_ledger[before:]
            self._audit_rows = baseline_rows
        elif blocked:
            for pid in blocked:
                self.signals[pid].position_target = 0.0
                self.signals[pid].normalised_weight = 0.0
        total = sum(float(s.position_target or 0.0) for s in self._get_allocatable_signals())
        self.accepted_investable_equity = total
        self.size_risk_discarded_value = max(float(self.investable_equity or 0.0) - total, 0.0)
        for s in self._get_allocatable_signals():
            s.normalised_weight = float(s.position_target or 0.0) / total if total else 0.0
        floor, active, calibrated = self._policy.floor(self.timestamp)
        for row in baseline_rows:
            pid = row["Pair id"]
            row.update({"Threshold policy": self._policy.kind, "Treatment": self._treatment, "Threshold": floor, "Floor active": active, "Calibrated at": calibrated, "New entrant": pid in entrants, "Rejected": pid in blocked, "Score-policy rejection": pid in expected, "Rejected target (USD)": proposed[pid] if pid in blocked else 0.0, "No-floor proposed target (USD)": proposed[pid], "Random dollar matching error (USD)": dollar_error if pid == min(entrants, default=-1) else 0.0, "Ranking score": self._score_for_pair(self.signals[pid].pair), "Held at decision": pid in self._held_ids})
            if pid in blocked:
                assert float(self.signals[pid].position_target or 0.0) == 0.0
        if self._treatment == "slot_to_cash":
            for pid, s in self.signals.items():
                if pid not in blocked:
                    assert np.isclose(float(s.position_target or 0.0), proposed[pid], atol=1e-8), "Veto changed surviving dollar target"


def make_floor_decision(evaluator, values, policy, treatment, ledger):
    """Restore the production module factory even when a decision fails."""
    strategy = evaluator.strategy
    source = strategy.decide_trades

    def decide(input):
        held = {p.pair.internal_id for p in input.state.portfolio.get_open_positions() if not p.is_credit_supply()}
        proxy = MatrixIndicators(input.indicators, evaluator.panel, values, input.timestamp)
        included = proxy.get_indicator_value("inclusion_criteria", na_conversion=False)
        scores = []
        # Percentiles describe the current source-eligible new-entry universe,
        # including incumbent scores only when they could themselves deposit.
        manager = input.get_position_manager(vault_record_file=strategy._guard_record_file())
        for pid in (list(included) if included is not None and policy.kind in ("percentile_75", "random_percentile_75") else []):
            pair = input.strategy_universe.get_pair_by_id(pid)
            address = strategy._v11_pair_address(pair)
            gate = proxy.get_indicator_value("return_gate", pair=pair)
            if not input.state.is_good_pair(pair) or strategy.is_quarantined(pair.pool_address, input.timestamp):
                continue
            if address in strategy.MANUAL_BLACKLIST or address in strategy.MASKED_VAULTS:
                continue
            if gate is None or not np.isfinite(gate) or gate <= float(input.parameters.gate_threshold):
                continue
            if not manager.is_whitelisted_vault(pair):
                continue
            check = input.pricing_model.check_deposit(input.timestamp, pair, stage=strategy.DepositCheckStage.buy_rebalance)
            score = proxy.get_indicator_value("matrix_score", pair=pair)
            if check.can_deposit and np.isfinite(score):
                scores.append(score)
        policy.percentile_floor = float(np.quantile(scores, 0.75)) if scores else np.nan
        models = []
        original = strategy.AlphaModel

        def factory(*args, **kwargs):
            model = AdmissionAlphaModel(*args, held_ids=held, score_for_pair=lambda pair: proxy.get_indicator_value("matrix_score", pair=pair), policy=policy, treatment=treatment, allocation_ledger=ledger, **kwargs)
            models.append(model)
            return model

        strategy.AlphaModel = factory
        try:
            trades = source(replace(input, indicators=proxy))
            for model in models:
                for row in model._audit_rows:
                    signal = model.signals[row["Pair id"]]
                    row["Final target (USD)"] = float(signal.position_target or 0.0)
                    row["Planned buy (USD)"] = sum(float(t.planned_reserve or 0.0) for t in trades if t.pair.internal_id == row["Pair id"] and t.is_buy())
                    row["Flags"] = ",".join(sorted(f.value for f in signal.flags))
                    assert not row["Rejected"] or row["Planned buy (USD)"] == 0.0, "Rejected entrant still buys"
                    if not signal.carry_forward_position:
                        assert row["Final target (USD)"] <= row["Concentration limit (USD)"] + 1e-6, "Concentration cap changed"
                        assert not row["Rejected"] or not row["Held at decision"], "Floor blocked an incumbent"
                    row["Capacity accepted before source top-up gate (USD)"] = float(signal.position_size_risk.accepted_size or 0.0) if signal.position_size_risk else 0.0
                    row["After-policy budget (USD)"] = float(model.accepted_investable_equity or 0.0)
                    row["Entry-only increases retained"] = bool(row["Held at decision"] and row["Final target (USD)"] > row["Old value (USD)"])
            return trades
        finally:
            strategy.AlphaModel = original

    return decide


def state_metrics(state, n):
    """Use the same daily equity convention as the parent experiments."""
    equity = calculate_equity_curve(state)
    daily = calculate_returns(equity).resample("1D").sum(min_count=1).fillna(0.0)
    day_equity = equity.resample("1D").last().reindex(daily.index).ffill()
    weights = calculate_asset_weights(state).unstack().resample("1D").last().reindex(daily.index).ffill().fillna(0.0)
    reserve = state.portfolio.get_default_reserve_asset()[0].token_symbol
    cash = weights[reserve] / day_equity
    occupancy = weights.drop(columns=reserve).gt(1e-8).sum(axis=1)
    trades = list(state.portfolio.get_all_trades())
    costs = sum(abs(float(t.executed_quantity or 0.0)) * float(t.planned_mid_price or 0.0) * float(t.other_data.get("backtest_vault_redemption_fee", 0.0)) for t in trades if t.is_success() and t.is_sell())
    finite = lambda v: float(v) if np.isfinite(v) else 0.0
    metrics = {"Final equity (USD)": float(equity.iloc[-1]), "CAGR": finite(calculate_cagr(daily)), "Sharpe": finite(calculate_sharpe(daily, periods=365)) if daily.std() > 0 else 0.0, "Sortino": finite(calculate_sortino(daily, periods=365)) if daily.lt(0).any() else 0.0, "Maximum drawdown": finite(calculate_max_drawdown(daily)), "Mean cash weight": float(cash.mean()), "Mean vaults held": float(occupancy.mean()), "Maximum vaults held": int(occupancy.max()), "Trades": len(trades), "Modelled redemption costs (USD)": float(costs), "Gross trade turnover (USD)": float(sum(float(t.executed_reserve or 0.0) for t in trades if t.is_success()))}
    assert metrics["Maximum vaults held"] <= n
    return metrics, day_equity, daily, cash


def attach_rejection_outcomes(evaluator, ledger):
    """Mark rejected dollars at 30-day NAV as a foregone-outcome sensitivity.

    This is a gross static-holding sensitivity. It neither models the policy's
    alternative trade timing nor replaces the executable portfolio comparison.
    """
    if ledger.empty:
        return ledger
    rows = []
    for index, row in ledger.loc[ledger.Rejected].iterrows():
        raw = evaluator.forecast_raw_prices
        close = raw.xs(int(row["Pair id"]), level="pair_id")["close"]
        supported = raw.xs(int(row["Pair id"]), level="pair_id")["supported_daily_mark"]
        origin = pd.Timestamp(row["Date"]).normalize()
        anchor = origin - pd.Timedelta(days=1)
        endpoint = anchor + pd.Timedelta(days=30)
        nav = close.reindex([anchor, endpoint])
        actual = supported.reindex([anchor, endpoint]).astype("boolean").fillna(False)
        complete = len(nav) == 2 and nav.notna().all() and nav.gt(0).all() and actual.all()
        outcome = float(nav.iloc[-1] / nav.iloc[0] - 1) if complete else np.nan
        rows.append({"index": index, "Foregone 30d gross return": outcome, "Foregone 30d gross marked PnL (USD)": float(row["Rejected target (USD)"]) * outcome, "Foregone target status": "actual raw endpoints" if complete else "missing/censored raw endpoints", "Foregone valuation source": "actual raw positive per-share NAV, no framework price guard/forward fill", "Foregone anchor at": anchor, "Foregone target at": endpoint})
    if rows:
        extras = pd.DataFrame(rows).set_index("index")
        for column in extras:
            ledger[column] = extras[column].reindex(ledger.index)
    return ledger


def trade_comparison_frame(state):
    """Compare complete successful ledgers by addresses, timestamps and fills."""
    return pd.DataFrame([{"trade_id": t.trade_id, "position_id": t.position_id, "address": str(t.pair.pool_address).lower(), "opened_at": str(t.opened_at), "executed_at": str(t.executed_at), "buy": t.is_buy(), "quantity": float(t.executed_quantity or 0.0), "reserve": float(t.executed_reserve or 0.0), "price": float(t.executed_price or 0.0), "fee": float(t.other_data.get("backtest_vault_redemption_fee", 0.0))} for t in state.portfolio.get_all_trades() if t.is_success()])


def validate_parent_path(evaluator, method, period, n, destination):
    """Require the research no-floor hook to match saved source-compatible paths."""
    previous = json.loads((RUN_ROOT / "07" / "design.json").read_text())
    old_folder = evaluator.folder
    evaluator.folder = RUN_ROOT / "07" / previous["fingerprint"][:16] / f"n{n}"
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            reference = evaluator.run(method["weights"], *PERIODS[period], n=n, sizing="inverse_variance", allocator="parent", missing=True, profile=method["profile"], keep=True)
    finally:
        evaluator.folder = old_folder
    actual = State.read_json_file(destination / "state.json")
    actual_equity = calculate_equity_curve(actual)
    expected_equity = reference["equity"]
    assert actual_equity.index.equals(expected_equity.index), "No-floor equity timestamps differ"
    assert np.allclose(actual_equity.to_numpy(), expected_equity.to_numpy(), atol=1e-8, rtol=1e-12), "No-floor equity path differs"
    actual_trades, expected_trades = trade_comparison_frame(actual), trade_comparison_frame(reference["result"].state)
    assert actual_trades.shape == expected_trades.shape, "No-floor trade count differs"
    for column in actual_trades:
        if column in ("quantity", "reserve", "price", "fee"):
            assert np.allclose(actual_trades[column], expected_trades[column], atol=1e-8, rtol=1e-12), f"No-floor fill {column} differs"
        else:
            assert actual_trades[column].equals(expected_trades[column]), f"No-floor ledger {column} differs"
    report = {"equity_points": len(actual_equity), "successful_trades": len(actual_trades), "maximum_equity_error_usd": float((actual_equity - expected_equity).abs().max()), "trade_ledger_identical": True, "parent_cache_key": reference["cache_key"]}
    (destination / "parent-path-check.json").write_text(json.dumps(report, indent=2))
    return report


def save_run_audit(state, ledger, destination, metrics, day_equity, daily, cash):
    """Persist executable evidence and contributor sensitivities, including losses."""
    samples = calculate_equity_curve(state)
    previous = pd.Series(samples.index, index=samples.index).shift(1)
    previous = previous.groupby(previous.index.normalize()).last().reindex(daily.index)
    pd.DataFrame({"equity": day_equity, "daily_return": daily, "cash_weight": cash, "previous_valuation_at": previous}).to_csv(destination / "equity.csv", index_label="Date")
    ledger.to_csv(destination / "allocations.csv", index=False)
    trades = [{"Trade id": t.trade_id, "Position id": t.position_id, "Address": str(t.pair.pool_address).lower(), "Vault": t.pair.get_vault_name(), "Executed at": t.executed_at, "Buy": t.is_buy(), "Reserve (USD)": float(t.executed_reserve or 0.0), "Quantity": float(t.executed_quantity or 0.0), "Mid NAV": t.planned_mid_price, "Redemption fee": t.other_data.get("backtest_vault_redemption_fee", 0.0)} for t in state.portfolio.get_all_trades() if t.is_success()]
    pd.DataFrame(trades).to_csv(destination / "trades.csv", index=False)
    curves, positions = calculate_position_profit_curves(state, daily.index)
    if len(positions):
        positions["Curator excluded"] = positions.Address.isin(EXCLUDED_VAULTS)
        positions["Quarantined at entry"] = [is_quarantined(a, t) for a, t in zip(positions.Address, positions.Opened)]
        by_vault = positions.groupby(["Address", "Vault"])["Final profit (USD)"].sum().sort_values(ascending=False)
        leader = by_vault.index[0]
        leader_ids = positions.loc[positions.Address.eq(leader[0]), "Position id"]
        no_leader = calculate_returns(day_equity - curves[leader_ids].sum(axis=1))
        positive = float(by_vault.clip(lower=0).sum())
        residual = (curves.sum(axis=1) - (day_equity - float(state.portfolio.get_initial_deposit()))).abs().max()
        leader_name = leader[1]
        leader_share = float(by_vault.iloc[0] / positive) if positive else 0.0
        leader_sharpe = float(calculate_sharpe(no_leader, periods=365)) if no_leader.std() > 0 else 0.0
    else:
        residual, leader_name, leader_share, leader_sharpe = 0.0, None, 0.0, 0.0
    positions.to_csv(destination / "positions.csv", index=False)
    curves.diff().fillna(curves.iloc[0] if len(curves) else 0.0).to_csv(destination / "position-daily-pnl.csv", index_label="Date")
    modified = daily.copy()
    if len(modified):
        modified.loc[daily.idxmax()] = 0.0
    robustness = {"Best day": str(daily.idxmax()) if len(daily) else None, "Best day return": float(daily.max()), "Worst day": str(daily.idxmin()), "Worst day return": float(daily.min()), "Excess kurtosis": float(daily.kurt()), "Leading vault": leader_name, "Leader share of positive vault PnL": leader_share, "Sharpe with best day zeroed": float(calculate_sharpe(modified, periods=365)) if modified.std() > 0 else 0.0, "Sharpe without leader (fixed ledger)": leader_sharpe, "Attribution residual (USD)": float(residual)}
    (destination / "robustness.json").write_text(json.dumps(robustness, default=str))
    return robustness


def run_one(evaluator, method, monthly, period, n, kind, treatment, seed=None):
    """Run a complete engine replay under an immutable, cached policy recipe."""
    source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    threshold_hash = hashlib.sha256(monthly.to_json(date_format="iso", orient="records").encode()).hexdigest()
    recipe = {"method": method["method_id"], "weights": method["weights"], "profile": method["profile"], "period": period, "n": n, "threshold": kind, "treatment": treatment, "seed": seed, "source": source, "threshold_hash": threshold_hash, "panel": evaluator.panel.fingerprint, "framework_generation": str(evaluator.folder)}
    key = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:24]
    destination = ARTIFACT_DIR / key
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    if path.exists():
        return json.loads(path.read_text()), destination
    parameters = deepcopy(evaluator.parameters)
    start, end = PERIODS[period]
    parameters["backtest_start"], parameters["backtest_end"] = start, end
    parameters["max_assets_in_portfolio"] = parameters["max_capacity_assets"] = n
    parameters["entry_rank"], parameters["exit_rank"] = n, n + 2
    parameters["selection_score_indicator"] = "matrix_score"
    parameters["weighting_method"] = "inverse_variance"
    for name, expected in [("allocation_pct", 0.98), ("max_concentration_pct", 0.33), ("per_position_cap_of_pool_pct", 0.33)]:
        assert np.isclose(float(parameters[name]), expected)
    values = evaluator.panel.score_values(method["weights"], missing=True, profile=method["profile"])
    ledger = []
    policy = FloorPolicy(kind, monthly, method["method_id"], seed=seed)
    decide = make_floor_decision(evaluator, values, policy, treatment, ledger)
    evaluator.strategy.apply_vault_redemption_capital_fee(evaluator.universe, float(parameters.vault_redemption_capital_fee))
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = run_backtest_inline(engine_version=evaluator.strategy.trading_strategy_engine_version, client=evaluator.client, decide_trades=decide, universe=evaluator.universe, indicator_storage=evaluator.indicator_storage, indicator_combinations=evaluator.indicators.indicator_combinations, parameters=parameters, cycle_duration=parameters.cycle_duration, initial_deposit=parameters.initial_cash, reserve_currency=ReserveCurrency.usdc, trade_routing=parameters.routing, max_slippage=parameters.slippage_tolerance_pct, start_at=start, end_at=end, max_workers=1, name=f"Forecast admission {key}", strategy_logging=False)
    metrics, day_equity, daily, cash = state_metrics(result.state, n)
    ledger = attach_rejection_outcomes(evaluator, pd.DataFrame(ledger))
    rejected = ledger.loc[ledger.Rejected] if len(ledger) else pd.DataFrame()
    metrics.update({"Rejected entry dollars (USD)": float(rejected["Rejected target (USD)"].sum()) if len(rejected) else 0.0, "Rejected entry proposals": len(rejected), "Floor-active decision fraction": float(ledger.groupby("Date")["Floor active"].first().mean()) if len(ledger) else 0.0, "Random dollar matching absolute error (USD)": float(ledger["Random dollar matching error (USD)"].abs().sum()) if len(ledger) else 0.0})
    robustness = save_run_audit(result.state, ledger, destination, metrics, day_equity, daily, cash)
    result.state.write_json_file(destination / "state.json")
    record = {"Period": period, "Method": method["method_id"], "Positions": n, "Threshold policy": kind, "Treatment": treatment, "Seed": seed, "cache_key": key, **metrics, **robustness}
    (destination / "recipe.json").write_text(json.dumps(recipe, indent=2))
    path.write_text(json.dumps(record, default=str, allow_nan=True))
    return record, destination


def run_threshold_experiments(data, statistics, include_random=True, progress=None):
    """Run six source controls and frozen threshold arms in both periods.

    All random arms use the fixed percentile rule, allowing useful controls even
    when the strictly trained absolute rule finds no supported cash threshold.
    Duplicate inactive monthly floors are marked as reused no-floor paths.
    """
    design = json.loads((ARTIFACT_DIR / "design.json").read_text())
    assert design["source_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "Re-freeze changed policy source before execution"
    evaluator = data["evaluator"]
    evaluator.forecast_raw_prices = data["prices"].set_index(["date", "pair_id"]).sort_index()
    methods = [r for r in data["registry"] if r["method_id"] in METHODS]
    assert len(methods) == 3
    monthly = statistics["monthly_thresholds"].copy()
    frames, records, audits = {}, [], []
    total = 2 * 3 * 2 * (5 + (6 if include_random else 0))
    completed = 0
    for period in ("2026", "Long"):
        for method in methods:
            for n in (6, 7):
                jobs = [("none", "slot_to_cash", None)]
                for kind in ("monthly_absolute", "percentile_75"):
                    jobs += [(kind, treatment, None) for treatment in ("slot_to_cash", "renormalise_within_caps")]
                if include_random:
                    jobs += [("random_percentile_75", treatment, seed) for treatment in ("slot_to_cash", "renormalise_within_caps") for seed in RANDOM_SEEDS]
                baseline = None
                for kind, treatment, seed in jobs:
                    started = time.monotonic()
                    record, destination = run_one(evaluator, method, monthly, period, n, kind, treatment, seed)
                    record["No-floor equivalent"] = record["Rejected entry proposals"] == 0
                    if kind == "none":
                        baseline = record
                        validate_parent_path(evaluator, method, period, n, destination)
                        reference = pd.read_csv(RUN_ROOT / "07" / f"{period}-results.csv")
                        parent_name = {"v11": "Legacy 45d", "blend_46d": "Blend 46d", "focal_four": "Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino"}[method["method_id"]]
                        matching = reference[reference.Score.eq(parent_name) & reference.Positions.eq(n)]
                        assert len(matching) == 1
                        for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)", "Trades"):
                            assert np.isclose(record[metric], matching.iloc[0][metric], atol=1e-8, rtol=1e-11), f'Parent control drift: {method["method_id"]} N={n} {metric}'
                    else:
                        for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight"):
                            record[f"{metric} delta vs no-floor"] = record[metric] - baseline[metric]
                        base_curve = pd.read_csv(ARTIFACT_DIR / baseline["cache_key"] / "equity.csv", index_col="Date", parse_dates=["Date"])
                        policy_curve = pd.read_csv(destination / "equity.csv", index_col="Date", parse_dates=["Date"])
                        assert isinstance(base_curve.index, pd.DatetimeIndex) and isinstance(policy_curve.index, pd.DatetimeIndex)
                        assert base_curve.index.equals(policy_curve.index), "Exposure comparison has different valuation dates"
                        scale = ((1 - policy_curve.cash_weight) / (1 - base_curve.cash_weight).replace(0, np.nan)).fillna(0.0)
                        scaled = base_curve.daily_return * scale
                        record["Exposure-scaled baseline CAGR (ex-post)"] = float(calculate_cagr(scaled))
                        record["Exposure-scaled baseline Sharpe (ex-post)"] = float(calculate_sharpe(scaled, periods=365)) if scaled.std() > 0 else 0.0
                    records.append(record)
                    audits.append({"Period": period, "Method": method["method_id"], "Positions": n, "Threshold policy": kind, "Treatment": treatment, "Seed": seed, "Artefact directory": str(destination), "Runtime seconds": time.monotonic() - started})
                    completed += 1
                    pd.DataFrame(records).to_csv(ARTIFACT_DIR / "results.csv", index=False)
                    if progress:
                        progress(completed, total, record)
        frames[period] = pd.DataFrame(records).query("Period == @period").copy()
        frames[period].to_csv(ARTIFACT_DIR / f"{period}-results.csv", index=False)
    pd.DataFrame(audits).to_csv(ARTIFACT_DIR / "manifest.csv", index=False)
    return build_execution_tables(records, audits)


def build_execution_tables(records, audits):
    """Assemble compact portfolio, attribution and randomness diagnostics."""
    results = pd.DataFrame(records)
    positions, contributors, jumps, quarters, outcomes = [], [], [], [], []
    from tradingstrategy.binance.price import fetch_binance_price

    references = {symbol: fetch_binance_price(symbol=symbol)["close"] for symbol in ("BTCUSDT", "ETHUSDT")}
    for audit in audits:
        folder = Path(audit["Artefact directory"])
        identity = {k: audit[k] for k in ("Period", "Method", "Positions", "Threshold policy", "Treatment", "Seed")}
        metadata = pd.read_csv(folder / "positions.csv")
        if len(metadata):
            positions.append(metadata.assign(**identity))
            sums = metadata.groupby(["Address", "Vault"])["Final profit (USD)"].sum().reset_index()
            sums["Share of positive vault PnL"] = sums["Final profit (USD)"].clip(lower=0) / sums["Final profit (USD)"].clip(lower=0).sum()
            contributors.append(sums.assign(**identity))
        curve = pd.read_csv(folder / "equity.csv", index_col="Date", parse_dates=["Date"])
        extremes = curve.loc[curve.daily_return.abs().nlargest(5).index].reset_index().rename(columns={"index": "Date"})
        pnl = pd.read_csv(folder / "position-daily-pnl.csv", index_col="Date", parse_dates=["Date"])
        if len(metadata) and len(pnl.columns):
            info = metadata.set_index("Position id")
            signed = pnl.loc[extremes.Date]
            positive_lead = signed.idxmax(axis=1)
            negative_lead = signed.idxmin(axis=1)
            lead = pd.Series([negative_lead.loc[ts] if value < 0 else positive_lead.loc[ts] for ts, value in zip(extremes.Date, extremes.daily_return)], index=extremes.Date)
            extremes["Leading position vault"] = [info.Vault.get(int(pid), "unknown") for pid in lead]
            extremes["Leading position address"] = [info.Address.get(int(pid), "unknown") for pid in lead]
            extremes["Leading position PnL (USD)"] = [float(pnl.loc[ts, pid]) for ts, pid in zip(extremes.Date, lead)]
            extremes["Leading position curator excluded"] = [bool(info["Curator excluded"].get(int(pid), False)) for pid in lead]
            extremes["Leading position quarantined at event"] = [is_quarantined(info.Address.get(int(pid), ""), pd.Timestamp(ts).to_pydatetime()) for ts, pid in zip(extremes.Date, lead)]
            denominator = pd.Series([float((-signed.loc[ts].clip(upper=0)).sum()) if value < 0 else float(signed.loc[ts].clip(lower=0).sum()) for ts, value in zip(extremes.Date, extremes.daily_return)], index=extremes.Date)
            extremes["Leader share of same-sign day PnL"] = [abs(float(pnl.loc[ts, pid])) / denominator.loc[ts] if denominator.loc[ts] else np.nan for ts, pid in zip(extremes.Date, lead)]
            extremes["Leader contribution sign"] = np.where(extremes.daily_return.lt(0), "negative", "positive")
        for symbol, prices in references.items():
            reference_returns = []
            reference_starts = []
            reference_ends = []
            for _, event in extremes.iterrows():
                end = pd.Timestamp(event.Date).normalize() - pd.Timedelta(days=1)
                previous = pd.to_datetime(event.get("previous_valuation_at"), errors="coerce")
                start = previous.normalize() - pd.Timedelta(days=1) if pd.notna(previous) else pd.NaT
                marks = prices.reindex([start, end])
                reference_returns.append(float(marks.iloc[-1] / marks.iloc[0] - 1) if marks.notna().all() and marks.gt(0).all() else np.nan)
                reference_starts.append(start)
                reference_ends.append(end)
            extremes[f"{symbol} matching interval return"] = reference_returns
            extremes["Reference candle start"] = reference_starts
            extremes["Reference candle end"] = reference_ends
        jumps.append(extremes.assign(**identity))
        for quarter, group in curve.groupby(curve.index.to_period("Q")):
            daily = group.daily_return
            quarters.append({**identity, "Quarter": str(quarter), "Calendar days": len(group), "Quarter return": float((1 + daily).prod() - 1), "Sharpe": float(calculate_sharpe(daily, periods=365)) if daily.std() > 0 else np.nan, "Maximum drawdown": float(calculate_max_drawdown(daily)), "Mean cash weight": float(group.cash_weight.mean())})
        ledger = pd.read_csv(folder / "allocations.csv")
        if len(ledger) and "Foregone 30d gross return" in ledger:
            rejected = ledger[ledger.Rejected]
            outcomes.append({**identity, "Rejected proposals": len(rejected), "Matured foregone labels": int(rejected["Foregone 30d gross return"].notna().sum()), "Foregone 30d gross return, unweighted": float(rejected["Foregone 30d gross return"].mean()), "Foregone 30d gross marked PnL (USD)": float(rejected["Foregone 30d gross marked PnL (USD)"].sum(min_count=1))})
    robustness_columns = ["Period", "Method", "Positions", "Threshold policy", "Treatment", "Seed", "Best day", "Best day return", "Worst day", "Worst day return", "Excess kurtosis", "Leading vault", "Leader share of positive vault PnL", "Sharpe with best day zeroed", "Sharpe without leader (fixed ledger)", "Attribution residual (USD)"]
    random_controls = []
    actual = results[results["Threshold policy"].eq("percentile_75")]
    for _, row in actual.iterrows():
        matches = results[(results.Period.eq(row.Period)) & (results.Method.eq(row.Method)) & results.Positions.eq(row.Positions) & results.Treatment.eq(row.Treatment) & results["Threshold policy"].eq("random_percentile_75")]
        if len(matches):
            random_controls.append({"Period": row.Period, "Method": row.Method, "Positions": row.Positions, "Treatment": row.Treatment, "Random seeds": len(matches), "Policy CAGR": row.CAGR, "Random median CAGR": float(matches.CAGR.median()), "Policy beats random CAGR fraction": float(matches.CAGR.lt(row.CAGR).mean()), "Policy Sharpe": row.Sharpe, "Random median Sharpe": float(matches.Sharpe.median()), "Interpretation": "Three-seed conditional controls; approximate dollar match, not a p-value"})
    tables = {"results": results, "2026": results[results.Period.eq("2026")].copy(), "Long": results[results.Period.eq("Long")].copy(), "robustness": results[robustness_columns], "manifest": pd.DataFrame(audits), "positions": pd.concat(positions, ignore_index=True) if positions else pd.DataFrame(), "contributors": pd.concat(contributors, ignore_index=True) if contributors else pd.DataFrame(), "jumps": pd.concat(jumps, ignore_index=True) if jumps else pd.DataFrame(), "quarterly": pd.DataFrame(quarters), "random_controls": pd.DataFrame(random_controls), "rejected_outcomes": pd.DataFrame(outcomes)}
    for name, frame in tables.items():
        frame.to_csv(ARTIFACT_DIR / f"{name}.csv", index=False)
    return tables
