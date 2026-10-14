"""Predeclared weighting interventions for experiment 03.

Selection, operational checks and execution remain in the imported v11 source.
Only post-selection raw weights and the experiment 02 allocator are replaced.
"""

from dataclasses import dataclass
from types import ModuleType
from typing import Callable

import numpy as np
import pandas as pd

from accepted_dollar_cap import AuditedAlphaModel
from tradeexecutor.strategy.pandas_trader.strategy_input import StrategyInput
from tradeexecutor.state.trade import TradeExecution


@dataclass(frozen=True)
class WeightingConfig:
    """Fixed research settings; none are fitted to portfolio results."""

    #: Trailing completed daily returns, matching the parent risk window.
    window: int = 90
    #: Equal-weight contribution to the priority 1 blend.
    equal_blend: float = 0.5
    #: Pseudo-observation count for variance shrinkage.
    prior_count: int = 30
    #: Minimum daily volatility and fallback cross-sectional prior.
    sigma_floor: float = 0.001
    #: Fraction of identity in the regularised correlation matrix.
    correlation_shrinkage: float = 0.5
    #: Minimum overlapping returns for a measured pairwise correlation.
    correlation_min_periods: int = 30


METHOD_NAMES = {
    "inverse_variance": "Original inverse variance",
    "blend": "P1: 50/50 inverse volatility + equal",
    "equal": "P2: Equal weights",
    "regularised_inverse_vol": "P3: Regularised inverse volatility",
    "risk_budget": "P4: Correlation-aware risk budget",
}


class WeightingProvider:
    """Causal trailing risk estimates cached by decision date and selected set."""

    def __init__(self, universe, config: WeightingConfig):
        self.config = config
        self.returns = {}
        self.cache = {}
        for pair in universe.iterate_pairs():
            if pair.is_vault():
                close = universe.data_universe.candles.get_candles_by_pair(pair.internal_id)["close"]
                self.returns[pair.internal_id] = close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)

    def estimate(self, timestamp, pair_ids):
        key = (pd.Timestamp(timestamp), tuple(sorted(pair_ids)))
        if key in self.cache:
            return self.cache[key]
        cfg = self.config
        end = pd.Timestamp(timestamp)
        start = end - pd.Timedelta(days=cfg.window)
        panel = pd.concat({pid: self.returns[pid].loc[lambda s: (s.index >= start) & (s.index < end)] for pid in pair_ids}, axis=1).reindex(columns=pair_ids)
        assert panel.empty or panel.index.max() < end
        observed = panel.count().astype(float)
        nonflat = panel.abs().gt(1e-12).sum().astype(float)
        measured_sigma = panel.std().fillna(cfg.sigma_floor)
        reliable = measured_sigma.loc[nonflat.ge(cfg.prior_count)]
        prior = max(float(reliable.median()) if len(reliable) else cfg.sigma_floor, cfg.sigma_floor)
        confidence = nonflat / (nonflat + cfg.prior_count)
        sigma = np.sqrt(confidence * measured_sigma.pow(2) + (1 - confidence) * prior**2).clip(lower=cfg.sigma_floor)
        correlation = panel.corr(min_periods=cfg.correlation_min_periods).fillna(0.0).to_numpy()
        np.fill_diagonal(correlation, 1.0)
        correlation = (1 - cfg.correlation_shrinkage) * correlation + cfg.correlation_shrinkage * np.eye(len(pair_ids))
        eigenvalues, eigenvectors = np.linalg.eigh(correlation)
        correlation = (eigenvectors * np.maximum(eigenvalues, 1e-6)) @ eigenvectors.T
        diagonal = np.sqrt(np.diag(correlation))
        correlation = correlation / np.outer(diagonal, diagonal)
        covariance = correlation * np.outer(sigma.to_numpy(), sigma.to_numpy())
        diagnostics = {pid: {"Risk observations": int(observed[pid]), "Non-flat returns": int(nonflat[pid]), "Measured sigma": float(measured_sigma[pid]), "Prior sigma": prior, "Regularised sigma": float(sigma[pid]), "Risk confidence": float(confidence[pid]), "Latest risk observation": panel[pid].last_valid_index()} for pid in pair_ids}
        result = (sigma.to_numpy(), correlation, covariance, diagnostics)
        self.cache[key] = result
        return result

    def weights(self, method, timestamp, pair_ids):
        sigma, correlation, covariance, diagnostics = self.estimate(timestamp, pair_ids)
        n = len(pair_ids)
        inverse = 1.0 / sigma
        inverse /= inverse.sum()
        iterations = 0
        if method == "equal":
            weights = np.full(n, 1.0 / n)
        elif method == "blend":
            weights = self.config.equal_blend / n + (1 - self.config.equal_blend) * inverse
        elif method == "regularised_inverse_vol":
            weights = inverse
        elif method == "risk_budget":
            # Solve the convex risk-budget objective in correlation-scaled units.
            risk_units = np.full(n, 1 / np.sqrt(n))
            budgets = np.full(n, 1.0 / n)
            for iterations in range(1, 2001):
                for i in range(n):
                    a = correlation[i, i]
                    b = float(correlation[i] @ risk_units - a * risk_units[i])
                    risk_units[i] = (-b + np.sqrt(b * b + 4 * a * budgets[i])) / (2 * a)
                contributions = risk_units * (correlation @ risk_units)
                fractions = contributions / contributions.sum()
                if np.max(np.abs(fractions - budgets)) < 1e-8:
                    break
            else:
                raise RuntimeError("Risk-budget solver did not converge")
            weights = risk_units / sigma
            weights /= weights.sum()
        else:
            raise ValueError(method)
        assert np.isfinite(weights).all() and (weights > 0).all()
        weights /= weights.sum()
        risk = weights * (covariance @ weights)
        fractions = risk / risk.sum()
        if method == "risk_budget":
            assert np.max(np.abs(fractions - 1.0 / n)) < 1e-7
        for i, pid in enumerate(pair_ids):
            diagnostics[pid] = {**diagnostics[pid], "Requested risk fraction": float(fractions[i]), "Solver iterations": iterations}
        return dict(zip(pair_ids, weights)), covariance, diagnostics


class WeightedAlphaModel(AuditedAlphaModel):
    """Replace weights after the source has selected its basket."""

    def __init__(self, *args, weighting_method, weighting_provider, **kwargs):
        super().__init__(*args, **kwargs)
        self.weighting_method = weighting_method
        self.weighting_provider = weighting_provider
        self.weighting_diagnostics = {}
        self.selected_pair_ids = []

    def assign_weights(self, method):
        super().assign_weights(method)
        ids = sorted(s.pair.internal_id for s in self._get_allocatable_signals() if s.raw_weight > 0)
        self.selected_pair_ids = ids
        if ids and self.weighting_method != "inverse_variance":
            weights, _, diagnostics = self.weighting_provider.weights(self.weighting_method, self.timestamp, ids)
            self.weighting_diagnostics = diagnostics
            for pid, value in weights.items():
                self.signals[pid].raw_weight = float(value)
        self.source_membership = tuple(sorted(self.signals))


def make_weighted_decide_trades(strategy: ModuleType, sizing_mode: str, weighting_method: str, allocation_ledger: list[dict], provider: WeightingProvider) -> Callable[[StrategyInput], list[TradeExecution]]:
    """Install a research AlphaModel only for one backtesting decision."""
    assert weighting_method in METHOD_NAMES
    assert sizing_mode in ("parent", "accepted_dollar_cap")
    source_decide = strategy.decide_trades

    def decide_trades(input: StrategyInput) -> list[TradeExecution]:
        assert input.execution_context.mode.is_backtesting()
        assert input.parameters.max_capacity_assets == input.parameters.max_assets_in_portfolio == 6
        original_factory = strategy.AlphaModel
        models = []

        def factory(*args, **kwargs):
            model = WeightedAlphaModel(*args, sizing_mode=sizing_mode, allocation_ledger=allocation_ledger, weighting_method=weighting_method, weighting_provider=provider, **kwargs)
            models.append(model)
            return model

        strategy.AlphaModel = factory
        try:
            trades = source_decide(input)
            for model in models:
                ids = model.selected_pair_ids
                if ids and weighting_method != "inverse_variance":
                    _, _, covariance, _ = provider.estimate(model.timestamp, ids)
                    targets = np.array([float(model.signals[pid].position_target or 0.0) for pid in ids])
                    risk = targets * (covariance @ targets)
                    actual_risk = risk / risk.sum() if risk.sum() > 0 else np.zeros(len(ids))
                    actual_risk_by_id = dict(zip(ids, actual_risk))
                else:
                    actual_risk_by_id = {}
                assert tuple(sorted(s.pair.internal_id for s in model.signals.values() if s.raw_weight > 0 or s.carry_forward_position)) == model.source_membership
                for row in model._audit_rows:
                    pid = row["Pair id"]
                    signal = model.signals[pid]
                    row.update(model.weighting_diagnostics.get(pid, {}))
                    row["Weighting method"] = weighting_method
                    row["Selected pair ids"] = ",".join(map(str, model.source_membership))
                    row["Final target (USD)"] = float(signal.position_target or 0.0)
                    row["Normalised accepted weight"] = float(signal.normalised_weight or 0.0)
                    row["Accepted risk fraction"] = actual_risk_by_id.get(pid, np.nan)
                    row["Flags"] = ",".join(sorted(flag.value for flag in signal.flags))
                    row["Adjustment ignored"] = bool(signal.position_adjust_ignored)
                    pair_trades = [t for t in trades if t.pair.internal_id == pid]
                    row["Planned buy (USD)"] = sum(float(t.planned_reserve or 0.0) for t in pair_trades if t.is_buy())
                    row["Planned sells"] = sum(t.is_sell() for t in pair_trades)
                    if sizing_mode == "accepted_dollar_cap":
                        assert row["Final target (USD)"] <= row["Accepted allocation (USD)"] + 1e-6
                        assert row["Accepted allocation (USD)"] <= row["Intended allocation (USD)"] + 1e-6
            return trades
        finally:
            strategy.AlphaModel = original_factory

    return decide_trades
