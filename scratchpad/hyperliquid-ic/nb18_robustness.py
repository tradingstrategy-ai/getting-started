"""Saved-output diagnostics for the paired blacklist experiment."""

from pathlib import Path
import json
import importlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from tradingstrategy.binance.price import fetch_binance_price


def report(project: Path):
    out = project / "_artifacts-leads-no-blacklists"
    matched = pd.read_csv(out / "date-matched-metrics.csv")
    delta = pd.read_csv(out / "blacklist-effect.csv")
    positions = pd.read_csv(out / "engine-positions.csv")
    concentration = pd.read_csv(out / "concentration.csv")
    membership = pd.read_csv(out / "universe-membership.csv")
    engine = pd.read_csv(out / "engine-metrics.csv")
    trades = pd.read_csv(out / "engine-trades.csv")
    positions["opened_at"] = pd.to_datetime(positions.opened_at)
    positions["closed_at"] = pd.to_datetime(positions.closed_at)
    trade_keys = ["mode", "period", "candidate", "position_id"]
    trades["funded"] = trades.value.abs().where(trades.quantity.gt(0), 0.0)
    trades["returned"] = trades.value.abs().where(trades.quantity.lt(0), 0.0)
    flow = trades.groupby(trade_keys).agg(funded=("funded", "sum"), returned=("returned", "sum"), residual_quantity=("quantity", "sum")).reset_index()
    flow = flow.merge(positions[trade_keys + ["address", "closed_at"]], on=trade_keys)
    flow["closed_without_returned_capital"] = flow.closed_at.notna() & flow.funded.gt(100) & flow.returned.lt(1)
    flow.to_csv(out / "closed-position-capital-audit.csv", index=False)
    curator = importlib.import_module("tradeexecutor.curator.curator")
    positions["quarantine_overlap"] = positions.apply(lambda row: any(row.address == address and row.opened_at <= pd.Timestamp(end) and (pd.isna(row.closed_at) or row.closed_at >= pd.Timestamp(start)) for address, start, end, reason in curator.QUARANTINE_PERIODS), axis=1)
    positions.to_csv(out / "position-quarantine-audit.csv", index=False)
    selected = positions.groupby(["mode", "period", "candidate", "address"]).agg(pnl=("pnl", "sum"), positions=("position_id", "count")).reset_index()
    selected = selected.merge(membership, on="address", how="left")
    selected.to_csv(out / "selected-vault-membership.csv", index=False)
    names = membership.set_index("address")["name"].to_dict()
    affected = set(membership.loc[~membership.universe_on | membership.manual_blacklist | membership.quarantines.ne("[]"), "address"])
    top = selected[selected["mode"].eq("off") & selected.address.isin(affected)].groupby("address").pnl.sum().abs().nlargest(6).index.tolist()
    raw = pd.read_parquet(Path.home() / ".cache/tradingstrategy/vaults/downloads/vault-prices.parquet", columns=["address", "chain", "share_price", "total_assets"]).reset_index()
    raw = raw[raw.chain.eq(9999)].copy()
    raw["timestamp"] = pd.to_datetime(raw.timestamp)
    raw["address"] = raw.address.str.lower()
    observed_event_rows = []
    for row in engine[engine["mode"].eq("off")].itertuples():
        curve = pd.read_parquet(out / f"engine-equity-{row.mode}-{row.period}-{row.candidate}.parquet").equity
        end = pd.Timestamp(row.best_cycle_date)
        start = curve.index[curve.index.get_loc(end) - 1]
        held = positions[positions["mode"].eq(row.mode) & positions.period.eq(row.period) & positions.candidate.eq(row.candidate) & positions.held_during_best_cycle]
        for address in held.address.unique():
            marks = raw[raw.address.eq(address)].sort_values("timestamp")
            before = marks[marks.timestamp.le(start)]
            after = marks[marks.timestamp.le(end)]
            if before.empty or after.empty:
                continue
            observed_event_rows.append({"mode": row.mode, "period": row.period, "candidate": row.candidate, "address": address, "name": names.get(address), "cycle_start": start, "cycle_end": end, "observed_start": before.timestamp.iloc[-1], "observed_end": after.timestamp.iloc[-1], "observed_nav_return": after.share_price.iloc[-1] / before.share_price.iloc[-1] - 1, "interpretation": "Observed NAV interval only; not exact engine cycle P&L attribution"})
    pd.DataFrame(observed_event_rows).to_csv(out / "best-cycle-held-vault-nav.csv", index=False)
    forensic_rows = []
    fig, axes = plt.subplots(max(len(top), 1), 1, figsize=(13, 3 * max(len(top), 1)), squeeze=False)
    for ax, address in zip(axes[:, 0], top):
        prices = raw[raw.address.eq(address) & raw.timestamp.between("2025-08-01", "2026-09-09")].sort_values("timestamp")
        prices = prices.drop_duplicates("timestamp", keep="last")
        price = pd.to_numeric(prices.share_price, errors="coerce")
        ax.plot(prices.timestamp, price)
        ax.set_title(f"{names.get(address,address)} — observed NAV")
        ax.grid(alpha=0.25)
        for a, start, end, reason in curator.QUARANTINE_PERIODS:
            if a == address:
                ax.axvspan(start, end, color="red", alpha=0.15)
        observed_returns = price.pct_change(fill_method=None)
        forensic_rows.append({"address": address, "name": names.get(address), "observations": len(prices), "min_nav": price.min(), "max_nav": price.max(), "best_observed_interval_return": observed_returns.max(), "worst_observed_interval_return": observed_returns.min(), "interval_return_kurtosis": observed_returns.kurt()})
    fig.tight_layout()
    fig.savefig(out / "restored-vault-nav-audit.png", dpi=140)
    plt.show()
    pd.DataFrame(forensic_rows).to_csv(out / "restored-vault-nav-audit.csv", index=False)
    refs = {symbol: fetch_binance_price(symbol=symbol)["close"] for symbol in ("BTCUSDT", "ETHUSDT")}
    market = []
    for row in engine.itertuples():
        curve = pd.read_parquet(out / f"engine-equity-{row.mode}-{row.period}-{row.candidate}.parquet").equity
        end = pd.Timestamp(row.best_cycle_date)
        start = curve.index[curve.index.get_loc(end) - 1]
        item = {"mode": row.mode, "period": row.period, "candidate": row.candidate, "start": start, "end": end, "portfolio_best_cycle": row.best_cycle}
        for symbol, prices in refs.items():
            # Daily candle timestamps label their start. Use only closes completed by the endpoint.
            prices = prices.copy()
            prices.index = pd.DatetimeIndex(prices.index).tz_localize(None) + pd.Timedelta(days=1)
            p0 = prices.loc[:start]
            p1 = prices.loc[:end]
            item[symbol + "_return"] = float(p1.iloc[-1] / p0.iloc[-1] - 1) if len(p0) and len(p1) else np.nan
        market.append(item)
    market = pd.DataFrame(market)
    market.to_csv(out / "best-cycle-market-context.csv", index=False)
    display(market)
    table = delta[["period", "candidate", "cagr_on", "cagr_off", "sharpe_on", "sharpe_off", "max_drawdown_on", "max_drawdown_off"]].copy()
    for column in table.columns:
        if "cagr" in column or "drawdown" in column:
            table[column] = table[column].map(lambda v: f"{v:.1%}")
        elif "sharpe" in column:
            table[column] = table[column].map(lambda v: f"{v:.2f}")
    display(table)
    display(concentration)
    display(selected[selected["mode"].eq("off") & selected.address.isin(affected)].sort_values("pnl", ascending=False).head(20))
    drift = []
    for period in ("hyper_ai", "full"):
        bridge = pd.read_csv(out / f"historical-control-drift-{period}.csv")
        for row in bridge.itertuples():
            drift.append({"period": period, "candidate": row.candidate, "cagr_change": row.cagr_current - row.cagr_historical, "sharpe_change": row.sharpe_current - row.sharpe_historical})
    drift = pd.DataFrame(drift)
    drift.to_csv(out / "historical-drift-summary.csv", index=False)
    strongest = matched[matched["mode"].eq("off") & matched.period.eq("full")].sort_values("sharpe", ascending=False).iloc[0]
    on_n = int(membership.universe_on.sum())
    off_n = int(membership.universe_off.sum())
    leader = concentration[concentration["mode"].eq("off") & concentration.period.eq("full")].sort_values("leader_positive_pnl_share", ascending=False).iloc[0]
    changed = delta.loc[delta.period.eq("full"), "cagr_change"].abs().max()
    findings = f"""## Key new insights and what did we learn?

Disabling source-universe exclusions increases coverage from {on_n} to {off_n} vaults.
The manual Scared Money exclusion and runtime curator quarantines are also disabled.
The strongest blacklist-off full-overlap Sharpe is {strongest['candidate']}:
{strongest.cagr:.1%} CAGR, {strongest.sharpe:.2f} two-day-clock Sharpe and
{strongest.max_drawdown:.1%} maximum drawdown. The largest absolute full-window
CAGR change across the six comparisons is {changed * 100:.1f} percentage points.

## Summary of results

{table.to_markdown(index=False)}

HyperAI dates: 2026-01-01–2026-07-08. Full common observation dates:
2025-09-13–2026-09-08. Engine full-period portfolios started earlier, on
2025-08-01; full-overlap values are slices, not cold-start replays. The paired
on/off results isolate blacklist policy on one snapshot; historical-control drift
is saved separately. Sharpe here uses two-day observations, not the weekly clock
of NB16. These are retrospective experiments.

## Robustness of results

The highest leader concentration in the blacklist-off full engine runs is
{leader.candidate}: {leader.leader_name} contributes {leader.leader_positive_pnl_share:.1%}
of positive per-vault P&L (${leader.leader_pnl:,.0f}). Full attribution, positions,
executed trades, quarantine overlaps, best-cycle BTC/ETH returns, extreme interval
moves and observed NAV charts are saved. Positive-P&L shares are descriptive;
they do not establish the result of a leave-one-vault-out resimulation.

All six comparisons lose CAGR and Sharpe when blacklists are disabled on the
shared full-history window. The volatility-prefilter leads are the strongest
remaining candidates, but none reaches the provisional 18% CAGR floor there.
The largest late-June gains occur while BTC and ETH fall; the saved held-vault
NAV intervals show vault-specific gains rather than establishing a broad market
rally. These NAV intervals are not exact engine P&L attribution. The capital
audit found {int(flow.closed_without_returned_capital.sum())} closed positions
funded above $100 with less than $1 returned in executed trade value.

The blacklists-on controls are freshly rerun; compare them to the off results,
not to stale headline numbers. The independent A0b simulator had no runtime
quarantine logic to disable, so its toggle restores universe/manual exclusions.
All restored source addresses are checked against saved feature coverage. The
same strategy filters, fee assumptions and forward-filled accounting are retained.
The engine's inherited redemption fees differ from A0b's; no fee harmonisation is
claimed. Producer-cleaned or omitted observations are not recovered by disabling
local blacklists, and restored price-series artefacts can inflate apparent gains.
"""
    (project / "no-blacklists-summary-01.md").write_text("# Incumbent and leads without blacklists\n\n" + findings)
    (out / "heading-results.md").write_text(findings)
    return findings
