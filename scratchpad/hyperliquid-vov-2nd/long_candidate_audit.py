"""Audit actual observation intervals underlying extreme long-history valuations."""

import numpy as np
import pandas as pd
from tradingstrategy.binance.price import fetch_binance_price
from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe
from IPython.display import display, Markdown
from long_candidate_backtest import PERIOD


def audit(data, summary, runs, quarters):
    """Match NAV updates to real mark dates instead of presumed daily observations."""
    root = data["artifact"]
    rows = []
    sens = []
    market = {symbol: fetch_binance_price(symbol=symbol, request_timeout=10.0) for symbol in ("BTCUSDT", "ETHUSDT")}
    for cid, r in runs.items():
        dr = r["daily_returns"]
        best = dr.idxmax()
        previous = r["equity"].index[r["equity"].index < best].max()
        curves = pd.read_parquet(root / f"{cid}-position-curves.parquet")
        meta = pd.read_parquet(root / f"{cid}-positions.parquet").set_index("Position id")
        delta = curves.diff().loc[best].groupby(meta.Vault).sum().sort_values(ascending=False)
        for name, pnl in delta.head(3).items():
            address = meta[meta.Vault.eq(name)].iloc[0].Address
            actual = data["daily"][data["daily"].address.eq(address) & data["daily"].date.le(best)].sort_values("date")
            prior = actual[actual.date.le(pd.Timestamp(previous).floor("D"))]
            current = actual[actual.date.gt(pd.Timestamp(previous).floor("D"))]
            if prior.empty or current.empty:
                rows.append(dict(Candidate=cid, Update=best, Vault=name, PnL=pnl, Supported=False))
                continue
            first = prior.iloc[-1]
            last = current.iloc[-1]
            # A daily bucket label is distinct from its actual intraday receipt.
            row = dict(Candidate=cid, Update=best, Vault=name, PnL=pnl, Supported=True, First_mark=first.timestamp, Last_mark=last.timestamp, Elapsed_days=(last.timestamp - first.timestamp).total_seconds() / 86400, NAV_return=last.share_price / first.share_price - 1, Actual_marks=int(actual.date.between(first.date, last.date).sum()), Receipt_after_engine_label=bool(last.timestamp > best), Curator_excluded=address in EXCLUDED_VAULTS, Quarantined=is_quarantined(address, best))
            for symbol, m in market.items():
                p = m.loc[first.date : last.date, "close"]
                row[symbol + " return"] = p.iloc[-1] / p.iloc[0] - 1
            rows.append(row)
        zeroed = dr.copy()
        zeroed.loc[best] = 0
        eq = r["equity"].resample("1D").last().ffill()
        leader = meta.groupby("Vault")["Final profit (USD)"].sum().idxmax()
        removed = curves.loc[:, curves.columns.isin(meta[meta.Vault.eq(leader)].index)].sum(axis=1)
        fixed = eq - removed
        assert fixed.min() > 0
        ret = fixed.pct_change(fill_method=None).fillna(0)
        sens.append(dict(Candidate=cid, **{"Best update": dr.max(), "CAGR best update zeroed": calculate_cagr(zeroed), "Sharpe best update zeroed": calculate_sharpe(zeroed, periods=365), "Removed vault": leader, "CAGR without leader fixed ledger": calculate_cagr(ret), "Sharpe without leader fixed ledger": calculate_sharpe(ret, periods=365)}))
    audit_frame = pd.DataFrame(rows)
    audit_frame.to_csv(root / "actual-mark-tail-audit.csv", index=False)
    sensitivity = pd.DataFrame(sens)
    sensitivity.to_csv(root / "tail-influence.csv", index=False)
    display(Markdown(f"### Actual NAV intervals behind extreme updates — {PERIOD}\n\nA two-day engine valuation can recognise a week of vault profits when archive marks are weekly. This audit uses the actual preceding/new observation pair, rather than assuming marks exist on T−1. BTC/ETH are compared over the same vault-specific dates. Observation receipts after the daily engine label show the inherited daily-close timing convention; the replay does not validate intraday executable fills."))
    view = audit_frame[audit_frame.Candidate.isin(["C03", "C07", "B01"])].copy()
    display(view[["Candidate", "Update", "Vault", "PnL", "First_mark", "Last_mark", "Elapsed_days", "NAV_return", "Actual_marks", "Receipt_after_engine_label", "Quarantined", "BTCUSDT return", "ETHUSDT return"]].style.format({"PnL": "${:,.0f}", "Elapsed_days": "{:.2f}", "NAV_return": "{:+.2%}", "BTCUSDT return": "{:+.2%}", "ETHUSDT return": "{:+.2%}"}, na_rep="Unavailable").hide(axis="index"))
    display(Markdown(f"### Tail influence on the fixed ledger — {PERIOD}\n\nSet each run’s best recorded return to zero, or remove its most profitable vault’s accumulated PnL while retaining all original transactions. These are influence diagnostics, not reruns with a changed trading strategy."))
    display(sensitivity.style.format({c: "{:.2%}" if "CAGR" in c or c == "Best update" else "{:.2f}" for c in sensitivity if c not in ["Candidate", "Removed vault"]}).hide(axis="index"))
    return audit_frame, sensitivity
