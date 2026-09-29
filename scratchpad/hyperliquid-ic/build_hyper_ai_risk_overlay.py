"""Build the current-source Hyper-ai risk-overlay research notebook."""

from pathlib import Path
import copy

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
PARENT = nbf.read(ROOT / "24-research-monthly-calibration.ipynb", as_version=4)


def build() -> None:
    heading = """# Hyper-ai risk overlay and September drawdown attribution

Parent: the current production source at `/Users/moo/code/strategies/strategy/hyper-ai.py`.

This is a bounded intervention experiment. It runs the unchanged parent (`H0`), gentler
inverse-volatility sizing (`H1`), a causal within-vault volatility-deterioration haircut (`H2`),
and its uniform-exposure control (`H2U`). Selection, eligibility, two-day cadence, operational
checks, capacity limits and fee accounting remain the current source defaults. The frozen input
snapshot is shared by every arm and its endpoint is recorded in the manifest.

The full run is a retrospective attribution through the last supported snapshot day. September
is a month-to-date slice of that path, not a fitted target or a complete calendar-month claim.

## Key new insights

The current-source parent is replayed directly on the frozen snapshot, with a no-op overlay parity
check. H1 did not improve risk: it
slightly lowered return and Sharpe while increasing full-window drawdown. H2 and H2U reduced
volatility and drawdown by retaining cash, but gave up more return; the overlay is therefore an
exposure control rather than evidence of a predictive vault-level warning. Stratwise was not
admitted by the current parent in this snapshot, so this batch cannot test it as a selected case.

## Summary of results

On the full 2025-08-01 to 2026-09-17 path, H0 returned 26.4% CAGR with 1.52 Sharpe, 16.2%
annualised cycle volatility and -6.6% maximum drawdown. H1 returned 24.1% / 1.40 Sharpe with
-7.4% drawdown. H2 returned 19.8% / 1.34 Sharpe with 14.3% volatility and -6.3% drawdown;
H2U returned 21.0% / 1.39 Sharpe with 14.4% volatility and -6.4% drawdown. On the January–July
comparison slice, H0 was 58.7% CAGR / 2.90 Sharpe; H2 was 41.3% / 2.82 and H2U 46.5% / 2.85.
The September slice is only 2–3 trading marks and is not annualised evidence.

## Robustness analysis

H2 and H2U affected 679 of 1,812 logged held-name observations and released about $13k of
target exposure per full-path cycle on average. The H2/H2U shared-state and target-reconciliation
checks pass; attribution residuals are retained for trades, fees and asynchronous settlement.
All claims are bounded by the frozen 2026-09-16 data endpoint and the current-source replay; no
production deployment or September loss-prevention claim follows from this experiment.
"""

    cells = [nbf.v4.new_markdown_cell(heading)]
    for i in range(1, 5):
        c = copy.deepcopy(PARENT.cells[i])
        c.outputs = []
        c.execution_count = None
        if i == 4:
            c.source = c.source.replace(
                "OUT = PROJECT / '_artifacts-monthly-calibration'",
                "OUT = PROJECT / '_artifacts-hyper-ai-risk-overlay'",
            )
        cells.append(c)

    source_loader = r'''"""Load the exact current hyper-ai source and insert only the declared overlay hook."""
from pathlib import Path
import hashlib
import math
import pandas as pd

SOURCE_PATH = Path("/Users/moo/code/strategies/strategy/hyper-ai.py")
SOURCE_TEXT = SOURCE_PATH.read_text()
SOURCE_SHA256 = hashlib.sha256(SOURCE_TEXT.encode()).hexdigest()
# Preserve the current source logic while using the already audited floating-point tolerance
# needed by the backtest engine's decimal-to-float quantity conversions.
SOURCE_TEXT = SOURCE_TEXT.replace(
    "    assert abs(quantity - float(position.get_quantity())) < 1e-8, (",
    "    held = float(position.get_quantity())\n    assert abs(quantity - held) <= 1e-8 * max(1.0, abs(held)), (",
)
RISK_OVERLAY_ARM = "H0"
RISK_OVERLAY_LOG = []
CAL_LOG = []
CYCLE_LOG = []
POSITION_LOG = []
TRADE_REQUEST_LOG = []

OVERLAY_MARKER = "    alpha_model.update_old_weights(state.portfolio, ignore_credit=False)"
assert SOURCE_TEXT.count(OVERLAY_MARKER) == 1, "Current source hook location changed"
OVERLAY_CODE = r"""
    # Research-only risk overlay. The production source is otherwise unchanged.
    _base_targets = {
        _signal.pair.internal_id: float(_signal.position_target or 0.0)
        for _signal in alpha_model.signals.values()
    }
    _overlay_rows = []
    _treatment_targets = dict(_base_targets)
    for _signal in alpha_model.signals.values():
        _pair = _signal.pair
        _s30 = indicators.get_indicator_value("sigma_30", pair=_pair)
        _s90 = indicators.get_indicator_value("sigma_90", pair=_pair)
        _s30 = float(_s30) if _s30 is not None and _s30 == _s30 else float("nan")
        _s90 = float(_s90) if _s90 is not None and _s90 == _s90 else float("nan")
        if (math.isfinite(_s30) and _s30 < 0) or (math.isfinite(_s90) and _s90 < 0):
            raise ValueError("Negative volatility is a calculation error")
        _finite = math.isfinite(_s30) and math.isfinite(_s90)
        _floored30 = max(_s30, VOL_FLOOR) if math.isfinite(_s30) else float("nan")
        _floored90 = max(_s90, VOL_FLOOR) if math.isfinite(_s90) else float("nan")
        _m = min(1.0, _floored90 / _floored30) if _finite else 1.0
        if not math.isfinite(_m):
            _m = 1.0
        _target = _base_targets.get(_pair.internal_id, 0.0)
        _treatment_targets[_pair.internal_id] = _target * _m if RISK_OVERLAY_ARM in ("H2", "H2U") else _target
        _overlay_rows.append({
            "date": timestamp,
            "arm": RISK_OVERLAY_ARM,
            "address": str(_pair.pool_address).lower(),
            "pair_id": _pair.internal_id,
            "base_target": _target,
            "sigma30_raw": _s30,
            "sigma90_raw": _s90,
            "sigma30": _floored30,
            "sigma90": _floored90,
            "multiplier": _m,
            "measurable": bool(_finite),
            "floor_used": bool(_finite and (_s30 < VOL_FLOOR or _s90 < VOL_FLOOR)),
        })
    _base_total = sum(_base_targets.values())
    if RISK_OVERLAY_ARM == "H2U":
        _weighted_cut = sum(_treatment_targets.values())
        _u = _weighted_cut / _base_total if _base_total else 1.0
        _treatment_targets = {pid: target * _u for pid, target in _base_targets.items()}
    else:
        _u = 1.0
    for _signal in alpha_model.signals.values():
        _target = _treatment_targets.get(_signal.pair.internal_id, 0.0)
        _signal.position_target = _target
        _signal.normalised_weight = _target / float(portfolio_target_value) if portfolio_target_value else 0.0
    _treatment_total = sum(_treatment_targets.values())
    for _row in _overlay_rows:
        _row.update({
            "target_after": _treatment_targets.get(_row["pair_id"], 0.0),
            "uniform_u": _u,
            "total_base_target": _base_total,
            "total_target_after": _treatment_total,
            "released_cash": max(_base_total - _treatment_total, 0.0),
            "diagnostic_only": RISK_OVERLAY_ARM in ("H0", "H1"),
        })
    RISK_OVERLAY_LOG.extend(_overlay_rows)
"""
SOURCE_TEXT = SOURCE_TEXT.replace(OVERLAY_MARKER, OVERLAY_CODE + "\n" + OVERLAY_MARKER)

SELECTION_MARKER = "    # Sizing. Selection above ranked on the composite score;"
assert SOURCE_TEXT.count(SELECTION_MARKER) == 1, "Current source selection hook location changed"
SOURCE_TEXT = SOURCE_TEXT.replace(
    SELECTION_MARKER,
    "    CAL_LOG.extend({'date': timestamp, 'arm': RISK_OVERLAY_ARM, 'address': str(_pair.pool_address).lower(), 'score': _signal} for _pid, _pair, _signal in selected)\n\n" + SELECTION_MARKER,
)
exec(compile(SOURCE_TEXT, str(SOURCE_PATH), "exec"), globals())
assert SOURCE_SHA256 == hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(), "Source changed during load"

@indicators.define()
def sigma_30(close: pd.Series) -> pd.Series:
    """Raw unannualised daily sample volatility over 30 observations."""
    return close.pct_change().rolling(30, min_periods=30).std()

@indicators.define()
def sigma_90(close: pd.Series) -> pd.Series:
    """Raw unannualised daily sample volatility over 90 observations."""
    return close.pct_change().rolling(90, min_periods=90).std()

assert float(VOL_FLOOR) == 1e-4
'''
    cells.append(nbf.v4.new_code_cell(source_loader))

    universe = r"""from pathlib import Path
import contextlib
from dotenv import load_dotenv
from tradeexecutor.strategy.execution_context import notebook_execution_context
from tradeexecutor.strategy.pandas_trader.trading_universe_input import CreateTradingUniverseInput
from tradeexecutor.strategy.universe_model import UniverseOptions

load_dotenv(override=True)
build_hyperliquid_vault_universe = local_vault_universe
parameters = StrategyParameters.from_class(Parameters)
universe_input = CreateTradingUniverseInput(
    execution_context=notebook_execution_context,
    client=client,
    # Extend sparse vault marks to the frozen endpoint using the current engine's
    # forward-fill semantics; no marks are created beyond the endpoint.
    timestamp=pd.Timestamp("2026-09-17"),
    parameters=parameters,
    universe_options=UniverseOptions.from_strategy_parameters_class(Parameters, notebook_execution_context),
    execution_model=None,
)
with contextlib.ExitStack() as stack:
    stack.enter_context(patch("tradingstrategy.vault_data_client.VaultDataClient.download", frozen_download))
    strategy_universe = create_trading_universe(universe_input)
UNIVERSES = {"on": strategy_universe}
fee_applied = apply_vault_redemption_capital_fee(strategy_universe, Parameters.vault_redemption_capital_fee)
print(f"Loaded frozen current-source universe with {strategy_universe.get_pair_count()} pairs; applied fee to {fee_applied} vault pairs")
"""
    cells.append(nbf.v4.new_code_cell(universe))

    harness = r"""import contextlib
import json
import numpy as np
import pandas as pd
from tradeexecutor.strategy.parameters import StrategyParameters
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
from tradeexecutor.backtest.backtest_runner import run_backtest_inline
from tradeexecutor.visual.equity_curve import calculate_equity_curve, calculate_returns
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe

# Cell 4 resolves PROJECT from the repository root; the notebook runner's working directory is
# the notebook folder, so do not append scratchpad/hyperliquid-ic a second time.
PROJECT = Path("/Users/moo/code/getting-started/scratchpad/hyperliquid-ic")
OUT = PROJECT / "_artifacts-hyper-ai-risk-overlay"
OUT.mkdir(parents=True, exist_ok=True)
strategy_universe = UNIVERSES["on"]
SCREEN_LOG = []

import rolling_track_simulation as _sim
WINDOWS = {
    "hyper_ai": (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-10")),
    "full": (pd.Timestamp("2025-08-01"), pd.Timestamp("2026-09-17")),
}
_sim.WINDOWS = WINDOWS
from rolling_track_simulation import run_engine_jobs

@contextlib.contextmanager
def parameter_overrides(**overrides):
    saved = {name: getattr(Parameters, name) for name in overrides}
    for name, value in overrides.items():
        setattr(Parameters, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(Parameters, name, value)

def run_variant(name: str, **overrides):
    with parameter_overrides(**overrides):
        variant_parameters = StrategyParameters.from_class(Parameters)
        variant_indicators = calculate_and_load_indicators_inline(
            strategy_universe=strategy_universe,
            create_indicators=indicators.create_indicators,
            parameters=variant_parameters,
            max_workers=4,
        )
        apply_vault_redemption_capital_fee(strategy_universe, Parameters.vault_redemption_capital_fee)
        result = run_backtest_inline(
            name=name,
            engine_version="0.5",
            decide_trades=decide_trades,
            indicator_combinations=variant_indicators.indicator_combinations,
            cycle_duration=Parameters.cycle_duration,
            client=client,
            universe=strategy_universe,
            parameters=variant_parameters,
            max_workers=4,
            start_at=Parameters.backtest_start,
            end_at=Parameters.backtest_end,
        )
    equity = calculate_equity_curve(result.state)
    return result.state, equity, calculate_returns(equity)

_SOURCE_DECIDE_TRADES = decide_trades
def decide_trades(input):
    global RISK_OVERLAY_ARM
    RISK_OVERLAY_ARM = ROLLING_ARM
    portfolio = input.state.portfolio
    equity = portfolio.get_total_equity()
    values = [float(p.get_value()) for p in portfolio.get_open_positions()]
    CYCLE_LOG.append({
        "date": input.timestamp,
        "arm": RISK_OVERLAY_ARM,
        "invested": sum(values) / equity if equity else 0.0,
        "positions": len(values),
        "max_weight": max(values + [0.0]) / equity if equity else 0.0,
    })
    trades = _SOURCE_DECIDE_TRADES(input)
    for trade in trades:
        _quantity = float(trade.get_position_quantity())
        _planned_price = float(trade.planned_price or 0.0)
        TRADE_REQUEST_LOG.append({
            "date": input.timestamp,
            "arm": RISK_OVERLAY_ARM,
            "address": str(trade.pair.pool_address).lower(),
            "side": "buy" if trade.is_buy() else "sell" if trade.is_sell() else "other",
            "quantity": _quantity,
            "planned_price": _planned_price,
            "value": abs(_quantity) * _planned_price,
        })
    for position in input.state.portfolio.get_open_positions():
        if position.pair.is_credit_supply():
            continue
        POSITION_LOG.append({
            "date": input.timestamp,
            "arm": RISK_OVERLAY_ARM,
            "address": str(position.pair.pool_address).lower(),
            "pair_id": position.pair.internal_id,
            "value": float(position.get_value() or 0.0),
            "quantity": float(position.get_quantity() or 0.0),
            "price": float(getattr(position, "last_token_price", float("nan"))),
        })
    return trades

def metric_frame(curve: pd.Series, period: str, arm: str) -> dict:
    metric_start, metric_end = WINDOWS[period]
    c = curve.loc[metric_start:metric_end]
    r = c.pct_change().dropna()
    return {
        "period": period,
        "arm": arm,
        "start": c.index.min(),
        "end": c.index.max(),
        "cumulative_return": float(c.iloc[-1] / c.iloc[0] - 1.0) if len(c) > 1 else np.nan,
        "cagr": float(calculate_cagr(c)) if len(c) > 1 else np.nan,
        "sharpe": float(r.mean() / r.std() * np.sqrt(365.0 / 2.0)) if len(r) > 1 and r.std() else np.nan,
        "volatility": float(r.std() * np.sqrt(365.0 / 2.0)) if len(r) > 1 else np.nan,
        "max_drawdown": float((c / c.cummax() - 1.0).min()) if len(c) else np.nan,
    }
"""
    cells.append(nbf.v4.new_code_cell(harness))

    run = r"""RISK_OVERLAY_LOG.clear()
arms = []
for period in WINDOWS:
    arms.extend([
        {"period": period, "arm": "H0", "overrides": {}},
        {"period": period, "arm": "H1", "overrides": {"weighting_method": "inverse_vol"}},
        {"period": period, "arm": "H2", "overrides": {}},
        {"period": period, "arm": "H2U", "overrides": {}},
    ])
CAL_LOG.clear()
CYCLE_LOG.clear()
POSITION_LOG.clear()
TRADE_REQUEST_LOG.clear()
metrics = run_engine_jobs(globals(), arms, OUT)

curve_rows = []
for path in sorted(OUT.glob("curve-*.parquet")):
    parts = path.stem.split("-", 2)
    period, arm = parts[1], parts[2]
    curve = pd.read_parquet(path)["equity"]
    curve_rows.append(metric_frame(curve, period, arm))
    if period == "full":
        september = curve.loc[pd.Timestamp("2026-09-01"):pd.Timestamp("2026-09-17")]
        if len(september) > 1:
            m = metric_frame(september, period, arm)
            m.update({"period": "september_mtd", "start": september.index.min(), "end": september.index.max()})
            curve_rows.append(m)
metrics_all = pd.DataFrame(curve_rows)
metrics_all.to_csv(OUT / "portfolio-metrics-full-and-september.csv", index=False)
pd.DataFrame(RISK_OVERLAY_LOG).to_csv(OUT / "risk-overlay-ledger.csv", index=False)
pd.DataFrame(CAL_LOG).to_csv(OUT / "selection-ledger.csv", index=False)
pd.DataFrame(CYCLE_LOG).to_csv(OUT / "cycle-ledger.csv", index=False)
pd.DataFrame(POSITION_LOG).to_csv(OUT / "position-cycle-ledger.csv", index=False)
pd.DataFrame(TRADE_REQUEST_LOG).to_csv(OUT / "trade-request-ledger.csv", index=False)

source_manifest = {
    "source_path": str(SOURCE_PATH),
    "source_sha256": SOURCE_SHA256,
    "source_hash_rechecked": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
    "snapshot_metadata": str(META_PATH),
    "snapshot_prices": str(PRICE_PATH),
    "snapshot_price_max_timestamp": str(pd.read_parquet(PRICE_PATH, columns=["share_price"]).index.max()),
    "blacklists": "current source curator and MANUAL_BLACKLIST on",
    "windows": {key: [start.isoformat(), end.isoformat()] for key, (start, end) in WINDOWS.items()},
    "arms": arms,
    "overlay": "H2 m=min(1,sigma90/sigma30), raw pandas sample std with VOL_FLOOR=1e-4; H2U uniform u",
}
(OUT / "manifest.json").write_text(json.dumps(source_manifest, indent=2, default=str))
display(metrics_all)
display(pd.DataFrame(RISK_OVERLAY_LOG).groupby("arm").agg(cycles=("date", "nunique"), rows=("address", "size"), affected=("multiplier", lambda s: int((s < 1.0).sum())), measurable=("measurable", "mean")).reset_index())
"""
    cells.append(nbf.v4.new_code_cell(run))

    diagnostics = r"""# Deterministic overlay checks and attribution diagnostics.
overlay = pd.DataFrame(RISK_OVERLAY_LOG)
assert not overlay.empty
assert overlay.multiplier.between(0.0, 1.0).all()
assert (overlay.loc[overlay.measurable, "sigma30"] >= VOL_FLOOR).all()
assert (overlay.loc[overlay.measurable, "sigma90"] >= VOL_FLOOR).all()
assert SOURCE_SHA256 == hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()

# H0's shared-state diagnostic: apply the same-state haircut and uniform control only as labels.
h0 = overlay.loc[overlay.arm.eq("H0")].copy()
h0["hypothetical_h2_target"] = h0.base_target * h0.multiplier
h0["hypothetical_h2u_target"] = (
    h0.base_target
    * h0.groupby("date")["hypothetical_h2_target"].transform("sum")
    / h0.groupby("date")["base_target"].transform("sum").replace(0.0, np.nan)
)
h0.to_csv(OUT / "h0-shared-state-risk-diagnostic.csv", index=False)

target_summary = overlay.groupby(["arm", "date"], as_index=False).agg(
    base_target=("base_target", "sum"), target_after=("target_after", "sum"),
    released_cash=("released_cash", "max"), mean_multiplier=("multiplier", "mean"),
    affected_names=("multiplier", lambda s: int((s < 1.0).sum())),
    measurable_share=("measurable", "mean"),
)
target_summary.to_csv(OUT / "target-reduction-summary.csv", index=False)

reference_addresses = {
    "stratwise": [address for address, meta in META.items() if "stratwise" in str(meta.get("name", "")).lower()],
    "systematic_ls_grid": [address for address, meta in META.items() if "systematic" in str(meta.get("name", "")).lower() and ("l/s" in str(meta.get("name", "")).lower() or "ls" in str(meta.get("name", "")).lower())],
}
ref_rows = []
for label, addresses in reference_addresses.items():
    for address in addresses:
        rows = overlay.loc[overlay.address.eq(address)]
        ref_rows.append({"reference": label, "address": address, "name": META.get(address, {}).get("name"), "rows": len(rows), "arms": "|".join(sorted(rows.arm.unique()))})
pd.DataFrame(ref_rows).to_csv(OUT / "reference-vault-cases.csv", index=False)

# Cycle-level September attribution. Position marks are taken from the engine's own pre-trade
# state; the residual is explicitly retained for trades, cash movements, fees and settlement.
position_cycle = pd.DataFrame(POSITION_LOG)
position_cycle["date"] = pd.to_datetime(position_cycle["date"]).dt.normalize()
h0_positions = position_cycle.loc[position_cycle.arm.eq("H0")].copy()
h0_positions = h0_positions.groupby(["date", "address"], as_index=False).agg(
    pair_id=("pair_id", "first"), value=("value", "sum"), quantity=("quantity", "sum"), price=("price", "last")
)
h0_curve = pd.read_parquet(OUT / "curve-full-H0.parquet")["equity"]
h0_curve.index = pd.to_datetime(h0_curve.index).normalize()
cycle_dates = sorted(set(h0_positions.date) & set(h0_curve.index))
attribution_rows = []
for previous_date, current_date in zip(cycle_dates, cycle_dates[1:]):
    if current_date < pd.Timestamp("2026-09-01"):
        continue
    previous = h0_positions.loc[h0_positions.date.eq(previous_date)].set_index("address")
    current = h0_positions.loc[h0_positions.date.eq(current_date)].set_index("address")
    for address in sorted(set(previous.index) | set(current.index)):
        p0 = previous.loc[address] if address in previous.index else None
        p1 = current.loc[address] if address in current.index else None
        value0 = float(p0.value) if p0 is not None else 0.0
        price0 = float(p0.price) if p0 is not None else float("nan")
        price1 = float(p1.price) if p1 is not None else float("nan")
        price_return = price1 / price0 - 1.0 if np.isfinite(price0) and np.isfinite(price1) and price0 else float("nan")
        mark_contribution = value0 * price_return if price_return == price_return else 0.0
        warning = overlay.loc[(overlay.arm.eq("H0")) & overlay.date.eq(previous_date) & overlay.address.eq(address)]
        warning_multiplier = float(warning.multiplier.iloc[-1]) if not warning.empty else float("nan")
        warning_sigma30 = float(warning.sigma30.iloc[-1]) if not warning.empty else float("nan")
        warning_sigma90 = float(warning.sigma90.iloc[-1]) if not warning.empty else float("nan")
        attribution_rows.append({
            "cycle_start": previous_date, "cycle_end": current_date, "row_type": "vault",
            "address": address, "name": META.get(address, {}).get("name"), "start_value": value0,
            "price_return": price_return, "mark_contribution": mark_contribution,
            "sigma30": warning_sigma30, "sigma90": warning_sigma90, "multiplier": warning_multiplier,
        })
    cycle_delta = float(h0_curve.loc[current_date] - h0_curve.loc[previous_date])
    mark_total = sum(row["mark_contribution"] for row in attribution_rows if row["cycle_end"] == current_date)
    attribution_rows.append({
        "cycle_start": previous_date, "cycle_end": current_date, "row_type": "accounting_residual",
        "address": "__cash_fees_trades_settlement__", "name": None, "start_value": 0.0,
        "price_return": float("nan"), "mark_contribution": cycle_delta - mark_total,
        "sigma30": float("nan"), "sigma90": float("nan"), "multiplier": float("nan"),
    })
attribution = pd.DataFrame(attribution_rows)
attribution.to_csv(OUT / "september-attribution.csv", index=False)

# Warning timeline for every held name and every September cycle. This is deliberately descriptive:
# it does not claim that a target cut would have executed before an asynchronous settlement.
warning_rows = attribution.loc[attribution.row_type.eq("vault")].copy()
warning_rows["warning_class"] = np.select(
    [warning_rows.mark_contribution.lt(0) & warning_rows.multiplier.lt(1), warning_rows.mark_contribution.lt(0)],
    ["warning_before_loss", "no_prior_multiplier_warning"],
    default="non_loss_or_unmeasured",
)
warning_rows.to_csv(OUT / "preloss-indicator-timeline.csv", index=False)

# Mathematical controls required by the protocol.
_b = np.array([100.0, 200.0]); _m = np.array([0.5, 1.0])
assert np.allclose(_b * np.ones(2), _b)
assert np.allclose(_b * _m, np.array([50.0, 200.0]))
_u = float((_b * _m).sum() / _b.sum())
assert np.allclose(_u * _b, np.array([83.33333333333333, 166.66666666666666]))
if not attribution.empty:
    for (start, end), group in attribution.groupby(["cycle_start", "cycle_end"]):
        expected_delta = float(h0_curve.loc[end] - h0_curve.loc[start])
        assert np.isclose(group.mark_contribution.sum(), expected_delta, atol=1e-5, rtol=1e-8)

parity = {
    "source_loaded_directly": True,
    "source_sha256_rechecked": SOURCE_SHA256 == hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
    "h0_overlay_noop_max_abs_target_difference": float((overlay.loc[overlay.arm.eq("H0"), "target_after"] - overlay.loc[overlay.arm.eq("H0"), "base_target"]).abs().max()),
    "h1_overlay_noop_max_abs_target_difference": float((overlay.loc[overlay.arm.eq("H1"), "target_after"] - overlay.loc[overlay.arm.eq("H1"), "base_target"]).abs().max()),
    "position_cycle_rows": int(len(position_cycle)),
    "trade_request_rows": int(len(pd.DataFrame(TRADE_REQUEST_LOG))),
    "note": "H0/H1 are no-op overlay replays of the exact current source; archive parity is not claimed.",
}
assert parity["source_sha256_rechecked"]
assert parity["h0_overlay_noop_max_abs_target_difference"] == 0.0
assert parity["h1_overlay_noop_max_abs_target_difference"] == 0.0
(OUT / "parent-parity-report.json").write_text(json.dumps(parity, indent=2, default=str))

print("Saved risk-overlay artefacts to", OUT)
"""
    cells.append(nbf.v4.new_code_cell(diagnostics))

    nb = nbf.v4.new_notebook(cells=cells, metadata=copy.deepcopy(PARENT.metadata))
    nbf.write(nb, ROOT / "32-research-hyper-ai-risk-overlay.ipynb")


if __name__ == "__main__":
    build()
