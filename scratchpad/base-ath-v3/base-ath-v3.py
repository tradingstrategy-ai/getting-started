"""Profit and Loss (PnL) calculation helperes for trading positions."""
import dataclasses
import datetime
import math

from tradeexecutor.state.identifier import TradingPairKind
from tradeexecutor.state.types import USDollarPrice, USDollarAmount, Percent


@dataclasses.dataclass(frozen=True, slots=True)
class ProfitData:
    """Different profit values for a trading position."""
    profit_usd: USDollarAmount
    profit_pct: Percent
    profit_pct_annualised: Percent
    realised_usd: USDollarAmount | None
    unrealised_usd: USDollarAmount | None
    duration: datetime.timedelta

    def is_win(self) -> bool:
        return self.profit_usd > 0

    def is_loss(self) -> bool:
        return not self.is_win()


def calculate_pnl(
    position: "tradeexecutor.state.position.TradingPosition",
    end_at: datetime.datetime=None,
    mark_price: USDollarPrice=None,
    epsilon: float=1e-6,
    max_annualised_profit: Percent = 100,  # 1000% annualised profit, or 100x
) -> ProfitData:
    """Calculate the Profit and Loss (PnL) for a given trading position.

    - Use cumulative trading cost method
    - Calculate all profit variables in one pass
    - Works for realised and unrealised PnL

    See also :py:func:`tradeexecutor.visualisation.position.calculate_position_timeline`.

    :param end_at:
        For non-closed positions you need to provide the `end_at` timestamp until we calculate the PnL.
        
    :param mark_price:
        For non-closed positions you need to provide the `mark_price` to calculate the unrealised PnL.

        If not given, use ``TradingPosition.last_token_price``.

    :return:
        Profit in dollar and percentage, annualised percentage.
    """

    assert position.is_spot() or position.is_vault(), f"Test/fixc alculations for other position types: {position} - only spotty supported for now"

    cumulative_quantity = cumulative_cost = avg_price = 0
    realised_pnl_total = 0
    cumulative_value = 0

    for trade in position.trades.values():
        delta = float(trade.executed_quantity)

        if delta > 0:
            # Buy: increase cost basis
            cumulative_cost += trade.get_value()
            cumulative_value += trade.get_value()
            cumulative_quantity += delta
        elif delta < 0:
            # Sell: reduce cost basis proportionally
            if cumulative_quantity > 0:
                avg_price = cumulative_cost / float(cumulative_quantity)
                cost_reduction = avg_price * abs(delta)
                cumulative_cost -= cost_reduction
                cumulative_quantity += delta  # delta is negative here

                realised_pnl = (trade.executed_price - avg_price) * abs(delta)
                realised_pnl_total += realised_pnl

        else:
            raise NotImplementedError(f"Got a trade withe executed quantity zero: {trade}")

    if abs(cumulative_cost) < epsilon:
        # Clean up 18 decimal madness
        cumulative_cost = 0.0

    if position.is_closed():
        end_at = position.closed_at
    else:
        assert end_at, f"end_at must be provided for non-closed position: {position}"
        assert isinstance(end_at, datetime.datetime), f"end_at must be a datetime object: {end_at}"

    if not mark_price:
        mark_price = position.last_token_price

    unrealised_pnl = (mark_price * float(position.get_quantity())) - cumulative_cost

    duration = (end_at - position.opened_at)
    assert duration > datetime.timedelta(0), f"Position {position} has a negative duration: {duration}, opened at {position.opened_at}, closed at {end_at}"
    annualised_periods = datetime.timedelta(days=365) / duration
    profit_usd = realised_pnl_total + unrealised_pnl
    profit_pct = (profit_usd / cumulative_value)

    try:
        profit_pct_annualised = (1 + profit_pct) ** annualised_periods - 1
    except OverflowError as e:
        # If we make a very short position (few hours) and make gains like 4%,
        # Python floating point will overflow when calculating annualised profit.
        profit_pct_annualised = math.copysign(max_annualised_profit, profit_pct)
    except Exception as e:
        raise RuntimeError(f"Failed to annualise profit_pct {profit_pct} for position {position} with duration {duration}, periods {annualised_periods}") from e

    return ProfitData(
        profit_pct=profit_pct,
        profit_usd=profit_usd,
        profit_pct_annualised=profit_pct_annualised,
        realised_usd=realised_pnl_total,
        unrealised_usd=unrealised_pnl,
        duration=duration,
    )



def calculate_pnl_generic(
    position: "tradeexecutor.state.position.TradingPosition",
    end_at: datetime.datetime=None,
    mark_price: USDollarPrice=None,
    epsilon: float=1e-6,
) -> ProfitData:
    """Handle different position types generically."""

    match position.pair.kind:
        case TradingPairKind.spot_market_hold | TradingPairKind.vault:
            return calculate_pnl(
                position=position,
                end_at=end_at,
                mark_price=mark_price,
                epsilon=epsilon,
            )
        case _:
            # Legacy path for other position types
            pnl_usd = position.get_total_profit_usd()
            pnl_pct = position.get_total_profit_percent(end_at=end_at)
            duration = position.get_duration(end_at=end_at)
            pnl_pct_annualised = position.calculate_total_profit_percent_annualised(end_at=end_at, calculation_method="legacy")
            return ProfitData(
                profit_usd=pnl_usd,
                profit_pct=pnl_pct,
                profit_pct_annualised=pnl_pct_annualised,
                realised_usd=None,  # Not applicable for non-spot/vault positions
                unrealised_usd=None,  # Not applicable for non-spot/vault positions
                duration=duration,
            )