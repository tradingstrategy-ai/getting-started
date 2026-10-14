"""Research-only sizing intervention and allocation audit for Hyper-AI v11.

The production source is imported unchanged. Only its AlphaModel factory is
replaced during an individual backtest decision, then restored in ``finally``.
"""

from copy import copy, deepcopy
from types import ModuleType
from typing import Callable, Literal

import pandas as pd

from tradeexecutor.strategy.alpha_model import AlphaModel, TradingPairSignalFlags
from tradeexecutor.strategy.pandas_trader.strategy_input import StrategyInput
from tradeexecutor.strategy.size_risk_model import SizeRiskModel
from tradeexecutor.strategy.weighting import normalise_weights
from tradeexecutor.state.trade import TradeExecution
from tradeexecutor.state.types import USDollarAmount


class AuditedAlphaModel(AlphaModel):
    """Audit the parent allocator or apply original-allocation dollar caps."""

    def __init__(
        self,
        *args,
        sizing_mode: Literal["parent", "accepted_dollar_cap", "cash_matched_parent"],
        allocation_ledger: list[dict],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._sizing_mode = sizing_mode
        self._allocation_ledger = allocation_ledger
        self._audit_rows = []

    def _normalise_weights_size_risk_positions(
        self,
        max_positions: int,
        max_weight: float = 1.0,
        investable_equity: USDollarAmount | None = None,
        size_risk_model: SizeRiskModel | None = None,
        epsilon_usd: USDollarAmount = 5.0,
        max_weight_function: Callable | None = None,
    ):
        """Keep requested shares fixed while clipping concentration and capacity.

        The counterfactual parent is sized from the same pre-trade signals and
        budget. It changes no holdings and supplies an allocation-level control.
        Normalised weights describe the accepted basket; explicit dollar targets
        preserve the unallocated cash through subsequent target calculations.
        """
        assert investable_equity is not None and size_risk_model is not None
        budget = float(investable_equity)
        raw_weights = {s.pair.internal_id: float(s.raw_weight) for s in self._get_allocatable_signals()}
        assert all(weight >= 0 for weight in raw_weights.values())
        original_weights = normalise_weights(raw_weights)
        kwargs = dict(
            max_positions=max_positions,
            max_weight=max_weight,
            investable_equity=investable_equity,
            size_risk_model=size_risk_model,
            epsilon_usd=epsilon_usd,
            max_weight_function=max_weight_function,
        )
        if self._sizing_mode == "parent":
            super()._normalise_weights_size_risk_positions(**kwargs)
            parent_targets = {pid: float(s.position_target or 0.0) for pid, s in self.signals.items()}
        else:
            counterfactual = copy(self)
            # Copy signals only: the growing audit ledger is shared, never deep-copied.
            counterfactual.signals = deepcopy(self.signals)
            AlphaModel._normalise_weights_size_risk_positions(counterfactual, **kwargs)
            parent_targets = {pid: float(s.position_target or 0.0) for pid, s in counterfactual.signals.items()}
            selected_ids = sorted(original_weights, key=original_weights.get, reverse=True)[:max_positions]
            for pid, signal in self.signals.items():
                if signal.carry_forward_position:
                    continue
                signal.position_target = 0.0
                signal.normalised_weight = 0.0
                if pid not in selected_ids or original_weights.get(pid, 0.0) <= 0:
                    continue
                requested = original_weights[pid] * budget
                concentration = float(max_weight)
                if max_weight_function is not None:
                    per_pair = max_weight_function(signal)
                    if per_pair is not None:
                        concentration = float(per_pair)
                capped_request = min(requested, concentration * budget)
                if capped_request < requested:
                    signal.flags.add(TradingPairSignalFlags.capped_by_concentration)
                risk = size_risk_model.get_acceptable_size_for_position(self.timestamp, signal.pair, capped_request)
                accepted = float(risk.accepted_size)
                assert 0 <= accepted <= capped_request + 1e-6
                signal.position_size_risk = risk
                signal.position_target = accepted
                if risk.capped:
                    signal.flags.add(TradingPairSignalFlags.capped_by_pool_size)
            total = sum(float(s.position_target or 0.0) for s in self._get_allocatable_signals())
            if self._sizing_mode == "cash_matched_parent":
                parent_total = sum(parent_targets.get(s.pair.internal_id, 0.0) for s in self._get_allocatable_signals())
                scale = total / parent_total if parent_total else 0.0
                assert scale <= 1.0 + 1e-9
                for signal in self._get_allocatable_signals():
                    signal.position_target = parent_targets.get(signal.pair.internal_id, 0.0) * scale
            self.investable_equity = budget
            self.accepted_investable_equity = total
            self.size_risk_discarded_value = max(budget - total, 0.0)
            for signal in self._get_allocatable_signals():
                signal.normalised_weight = float(signal.position_target or 0.0) / total if total else 0.0

        for pid, signal in self.signals.items():
            if signal.carry_forward_position:
                continue
            intended = original_weights.get(pid, 0.0) * budget
            accepted = float(signal.position_target or 0.0)
            if self._sizing_mode == "accepted_dollar_cap":
                assert accepted <= intended + 1e-6
            row = {
                "Date": self.timestamp,
                "Pair id": pid,
                "Address": str(signal.pair.pool_address).lower(),
                "Vault": signal.pair.get_vault_name() or signal.pair.base.token_symbol,
                "Mode": self._sizing_mode,
                "Deployable budget (USD)": budget,
                "Original weight": original_weights.get(pid, 0.0),
                "Raw weight": float(signal.raw_weight),
                "Old value (USD)": float(signal.old_value or 0.0),
                "Concentration limit (USD)": float(max_weight) * budget,
                "TVL (USD)": float(signal.position_size_risk.tvl or 0.0) if signal.position_size_risk else 0.0,
                "Intended allocation (USD)": intended,
                "Parent accepted, same state (USD)": parent_targets.get(pid, 0.0),
                "Accepted allocation (USD)": accepted,
                "Final target (USD)": None,
            }
            self._audit_rows.append(row)
            self._allocation_ledger.append(row)


def make_decide_trades(
    strategy: ModuleType,
    sizing_mode: Literal["parent", "accepted_dollar_cap", "cash_matched_parent"],
    allocation_ledger: list[dict],
) -> Callable[[StrategyInput], list[TradeExecution]]:
    """Wrap one decision without editing strategy or framework source files."""
    assert sizing_mode in ("parent", "accepted_dollar_cap", "cash_matched_parent")
    source_decide_trades = strategy.decide_trades

    def decide_trades(input: StrategyInput) -> list[TradeExecution]:
        assert input.execution_context.mode.is_backtesting()
        assert input.parameters.max_capacity_assets == input.parameters.max_assets_in_portfolio == 6
        original_factory = strategy.AlphaModel
        models = []

        def factory(*args, **kwargs):
            model = AuditedAlphaModel(
                *args,
                sizing_mode=sizing_mode,
                allocation_ledger=allocation_ledger,
                **kwargs,
            )
            models.append(model)
            return model

        strategy.AlphaModel = factory
        try:
            trades = source_decide_trades(input)
            for model in models:
                for row in model._audit_rows:
                    target = float(model.signals[row["Pair id"]].position_target or 0.0)
                    row["Final target (USD)"] = target
                    signal = model.signals[row["Pair id"]]
                    row["Normalised accepted weight"] = float(signal.normalised_weight or 0.0)
                    row["Flags"] = ",".join(sorted(flag.value for flag in signal.flags))
                    row["Adjustment ignored"] = bool(signal.position_adjust_ignored)
                    pair_trades = [trade for trade in trades if trade.pair.internal_id == row["Pair id"]]
                    row["Planned buy (USD)"] = sum(float(trade.planned_reserve or 0.0) for trade in pair_trades if trade.is_buy())
                    row["Planned sells"] = sum(trade.is_sell() for trade in pair_trades)
                    if sizing_mode == "accepted_dollar_cap":
                        assert target <= row["Intended allocation (USD)"] + 1e-6
                        assert target <= row["Accepted allocation (USD)"] + 1e-6
            return trades
        finally:
            strategy.AlphaModel = original_factory

    return decide_trades


def calculate_position_profit_curves(state, daily_index: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconstruct cumulative position PnL from marked holdings and USDC flows.

    Closed positions retain their realised profit but have zero holdings. All
    successful trade flows are grouped on their UTC execution day. The result
    can be reconciled to portfolio equity minus the initial deposit.
    """
    profit_curves = {}
    metadata = []
    for position in state.portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        pid = position.position_id
        samples = [(pd.Timestamp(s.calculated_at), float(s.value)) for s in state.stats.positions.get(pid, [])]
        if position.closed_at is not None:
            samples.append((pd.Timestamp(position.closed_at), 0.0))
        marked = pd.Series([value for _, value in samples], index=pd.DatetimeIndex([ts for ts, _ in samples]), dtype=float)
        marked = marked.groupby(level=0).last().resample("1D").last().reindex(daily_index).ffill().fillna(0.0)
        flows = []
        for trade in position.get_successful_trades():
            if trade.is_buy() or trade.is_sell():
                amount = float(trade.executed_reserve or 0.0) * (-1 if trade.is_buy() else 1)
                flows.append((pd.Timestamp(trade.executed_at).normalize(), amount))
        cash_flows = pd.Series([value for _, value in flows], index=pd.DatetimeIndex([ts for ts, _ in flows]), dtype=float)
        cash_flows = cash_flows.groupby(level=0).sum().reindex(daily_index, fill_value=0.0)
        profit_curves[pid] = marked + cash_flows.cumsum()
        metadata.append(
            {
                "Position id": pid,
                "Vault": position.pair.get_vault_name() or position.pair.base.token_symbol,
                "Address": str(position.pair.pool_address).lower(),
                "Opened": position.opened_at,
                "Closed": position.closed_at,
                "Final profit (USD)": float(position.get_cash_flow_profit_usd()),
            }
        )
    return pd.DataFrame(profit_curves, index=daily_index), pd.DataFrame(metadata)
