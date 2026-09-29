"""Small shared ledgers for rolling-track notebooks 25 and 26."""

from __future__ import annotations

import json
import hashlib
import importlib.metadata
from pathlib import Path

import numpy as np
import pandas as pd

from nb20_stability_screens import curve_metrics

WINDOWS = {
    "hyper_ai": (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-10")),
    "full": (pd.Timestamp("2025-08-01"), pd.Timestamp("2026-09-09")),
    "later": (pd.Timestamp("2026-04-01"), pd.Timestamp("2026-09-09")),
}


def rank_panel(panel: pd.DataFrame, ranking: str, lookback: int = 30) -> pd.DataFrame:
    """Create a causal diagnostic ranking and future-outcome summary."""
    from rolling_track_features import rolling_score

    # The young-compatible gate keeps the incumbent -16% threshold while
    # substituting the available-history return when a full lookback is absent.
    d = panel.loc[panel.lookback.eq(lookback) & panel.tvl_eligible & panel.gate.gt(-0.16)].copy()
    d["score"] = d.apply(lambda row: rolling_score(row.to_dict(), ranking), axis=1)
    d["rank"] = d.groupby("date")["score"].rank(method="first", ascending=False)
    d["pool"] = d.groupby("date")["address"].transform("size")
    d["top20"] = d["rank"] <= np.ceil(d["pool"] * 0.2)
    return d


def ranking_summary(panel: pd.DataFrame, lookbacks=(14, 30, 60)) -> pd.DataFrame:
    """Compare growth and growth-over-risk diagnostics without selecting on labels."""
    rows = []
    for lookback in lookbacks:
        for ranking in ("growth", "growth_over_risk"):
            d = rank_panel(panel, ranking, lookback)
            for horizon in (14, 30, 60):
                target = f"future_return_{horizon}"
                dd_target = f"future_drawdown_{horizon}"
                for date, group in d.groupby("date"):
                    top = group[group.top20]
                    rest = group[~group.top20]
                    if len(top) == 0 or len(rest) == 0:
                        continue
                    rows.append(
                        {
                            "ranking": ranking,
                            "lookback": lookback,
                            "horizon": horizon,
                            "date": date,
                            "pool": len(group),
                            "labelled": int(group[target].notna().sum()),
                            "top_return": top[target].mean(),
                            "rest_return": rest[target].mean(),
                            "top_drawdown": top[dd_target].mean(),
                            "rest_drawdown": rest[dd_target].mean(),
                            "top_coverage": float(top[target].notna().mean()),
                            "rest_coverage": float(rest[target].notna().mean()),
                        }
                    )
    return pd.DataFrame(rows)


def gate_coverage_audit(panel: pd.DataFrame, lookback: int = 30, threshold: float = -0.16) -> pd.DataFrame:
    """Audit the common available-history gate before applying it to any arm."""
    d = panel.loc[panel.lookback.eq(lookback)].copy()
    if d.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "feature_rows",
                "vaults",
                "gate_pass",
                "gate_pass_rate",
                "tvl_eligible",
                "gate_pass_tvl_eligible",
            ]
        )
    d["gate_pass"] = d["gate"] > threshold
    d["gate_pass_tvl_eligible"] = d["gate_pass"] & d["tvl_eligible"]
    return d.groupby("date", as_index=False).agg(
        feature_rows=("address", "size"),
        vaults=("address", "nunique"),
        gate_pass=("gate_pass", "sum"),
        gate_pass_rate=("gate_pass", "mean"),
        tvl_eligible=("tvl_eligible", "sum"),
        gate_pass_tvl_eligible=("gate_pass_tvl_eligible", "sum"),
    )


def run_engine_jobs(ns: dict, jobs: list[dict], out: Path) -> pd.DataFrame:
    """Run declared engine arms and save curves plus causal selection ledgers."""
    out.mkdir(parents=True, exist_ok=True)
    metrics, positions, allocations, selections, fees, replay_rows, exposure_rows = [], [], [], [], [], [], []
    for job in jobs:
        period, arm = job["period"], job["arm"]
        ns["ROLLING_ARM"] = arm
        # Legacy controls retain the exact NB24 engine path, while their
        # output labels identify the native window explicitly.
        ns["CAL_RULE"] = "anchor" if arm.startswith("LEGACY_") else arm
        ns["CAL_CONFIG"] = job
        ns["CAL_LOG"].clear()
        ns["CYCLE_LOG"].clear()
        ns["SCREEN_LOG"].clear()
        if "REPLAY_LOG" in ns:
            ns["REPLAY_LOG"].clear()
        if "TARGET_SCHEDULE_BY_PERIOD" in ns:
            ns["TARGET_SCHEDULE"] = ns["TARGET_SCHEDULE_BY_PERIOD"].get(period, {})
        if "EXPOSURE_LOG" in ns:
            ns["EXPOSURE_LOG"].clear()
        start, end = WINDOWS[period]
        overrides = dict(job.get("overrides", {}))
        with ns["patch"](
            "tradeexecutor.strategy.pandas_trader.position_manager.PositionManager.is_problematic_pair",
            return_value=False,
        ):
            state, equity, _ = ns["run_variant"](
                f"rolling-{period}-{arm}",
                backtest_start=start.to_pydatetime(),
                backtest_end=end.to_pydatetime(),
                **overrides,
            )
        curve = equity.rename("equity").to_frame()
        curve.attrs = {}
        curve.to_parquet(out / f"curve-{period}-{arm}.parquet")
        if arm == f"LEGACY_{period}" and period in ("hyper_ai", "full"):
            expected_path = Path(ns["PROJECT"]) / "_artifacts-profitable-months" / f"curve-{period}-anchor-6.parquet"
            expected = pd.read_parquet(expected_path).equity
            assert equity.index.equals(expected.index), f"Legacy {period} date index differs from corrected control"
            assert np.allclose(equity.to_numpy(), expected.to_numpy(), rtol=0, atol=1e-7), f"Legacy {period} equity differs from corrected NB23 control"
        metric_start = pd.Timestamp("2026-01-01") if period == "hyper_ai" else pd.Timestamp("2025-09-13") if period == "full" else pd.Timestamp("2026-04-01")
        metric_end = pd.Timestamp("2026-07-08") if period == "hyper_ai" else pd.Timestamp("2026-09-08")
        metrics.append({"period": period, "arm": arm, **curve_metrics(equity.loc[metric_start:metric_end])})
        for position in state.portfolio.get_all_positions():
            if position.is_credit_supply():
                continue
            address = str(position.pair.pool_address).lower()
            positions.append(
                {
                    "period": period,
                    "arm": arm,
                    "position_id": position.position_id,
                    "address": address,
                    "name": ns["META"].get(address, {}).get("name"),
                    "opened_at": position.opened_at,
                    "closed_at": position.closed_at,
                    "pnl": float(position.get_total_profit_usd() or 0),
                }
            )
            for trade in position.trades.values():
                if trade.is_sell() and trade.executed_at is not None and "nb23_gross_redemption_mid" in trade.other_data:
                    gross = float(trade.other_data["nb23_gross_redemption_mid"])
                    fee = float(trade.other_data["backtest_vault_redemption_fee"])
                    expected = gross * (1.0 - fee)
                    actual = float(trade.executed_price)
                    assert np.isclose(actual, expected, rtol=1e-9, atol=1e-12)
                    fees.append({"period": period, "arm": arm, "trade_id": trade.trade_id, "expected": expected, "actual": actual})
        allocations.extend({"period": period, "arm": arm, **row} for row in ns["CYCLE_LOG"])
        selections.extend({"period": period, "arm": arm, **row} for row in ns["CAL_LOG"])
        replay_rows.extend({"period": period, "arm": arm, **row} for row in ns.get("REPLAY_LOG", []))
        exposure_rows.extend({"period": period, "arm": arm, **row} for row in ns.get("EXPOSURE_LOG", []))
        del state
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(out / "portfolio-metrics.csv", index=False)
    pd.DataFrame(positions).to_csv(out / "positions.csv", index=False)
    pd.DataFrame(allocations).to_csv(out / "allocations.csv", index=False)
    pd.DataFrame(selections).to_csv(out / "selection-log.csv", index=False)
    pd.DataFrame(fees).to_csv(out / "redemption-checks.csv", index=False)
    if replay_rows:
        pd.DataFrame(replay_rows).to_csv(out / "schedule-replay-log.csv", index=False)
    if exposure_rows:
        pd.DataFrame(exposure_rows).to_csv(out / "exposure-intervention-log.csv", index=False)
    return metrics_df


def write_manifest(out: Path, *, notebook: str, parent: str, mechanism_delta: str, arms: list[dict]) -> None:
    """Write a compact ancestry and run declaration beside notebook artefacts."""
    source_files = [
        Path(__file__),
        Path(__file__).with_name("rolling_track_features.py"),
        Path(__file__).with_name("build_rolling_track.py"),
    ]
    hashes = {}
    for source in source_files:
        if source.exists():
            hashes[str(source.name)] = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        executor_version = importlib.metadata.version("trade-executor")
    except importlib.metadata.PackageNotFoundError:
        executor_version = "editable checkout"
    manifest = {
        "notebook": notebook,
        "parent_experiment": parent,
        "mechanism_delta": mechanism_delta,
        "why_not_duplicate": "Direct rolling observed-price features; no completed month/week admission rule.",
        "arms": arms,
        "windows": {k: [a.isoformat(), b.isoformat()] for k, (a, b) in WINDOWS.items()},
        "blacklists": "off",
        "fee_accounting": "NB23 corrected single redemption fee",
        "source_hashes": hashes,
        "environment": {"python": __import__("platform").python_version(), "trade_executor": executor_version},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
