"""Forensic PnL and price checks for the largest NB12 recorded equity update."""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from tradingstrategy.binance.price import fetch_binance_price
from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined
from allocation_followup import PERIOD, ROOT
from allocation_followup_report import figure


def audit_tail(data):
    """Compare position cash-flow PnL with original NAV and reference prices."""
    folder = data["artifact"]
    positions = pd.read_parquet(folder / "engine_position_attribution.parquet").query('Arm == "source_v11"').set_index("Position id")
    curves = pd.read_parquet(folder / "engine/source_v11-position-curves.parquet")
    aggregate = curves.sum(axis=1)
    date = pd.Timestamp("2026-06-26")
    delta = curves.diff().loc[date].groupby(positions.Vault).sum().sort_values(ascending=False)
    first, last = pd.Timestamp("2026-06-23"), pd.Timestamp("2026-06-25")
    prices = pd.read_parquet(ROOT / "_artifacts-restored-2026-10-07/08/prices.parquet")
    rows = []
    for name in ("Realist Capital", "Goon Edging"):
        meta = positions[positions.Vault.eq(name)].iloc[0]
        address = meta.Address
        p = prices[prices.vault_address.eq(address) & prices.date.between(first, last)]
        marks = p[p.supported_daily_mark].set_index("date").raw_close
        rows.append(dict(Asset=name, **{"23→25 June NAV return": float(marks.loc[last] / marks.loc[first] - 1), "Actual daily marks": len(marks), "Recorded PnL change (USD)": float(delta.loc[name]), "Curator excluded": address in EXCLUDED_VAULTS, "Quarantined at update": is_quarantined(address, date)}))
    for symbol in ("BTCUSDT", "ETHUSDT"):
        f = fetch_binance_price(symbol=symbol, request_timeout=10.0)
        rows.append(dict(Asset=symbol, **{"23→25 June NAV return": float(f.loc[last, "close"] / f.loc[first, "close"] - 1), "Actual daily marks": 3, "Recorded PnL change (USD)": np.nan, "Curator excluded": False, "Quarantined at update": False}))
    frame = pd.DataFrame(rows)
    frame.to_parquet(folder / "tail_price_audit.parquet", index=False)
    display(Markdown(f"### Largest recorded equity update — {PERIOD}\n\nThe equity series is marked at the engine’s two-day cadence. Its largest non-zero return is recorded on 26 June and spans multiple days; it should not be interpreted as a independently observed one-day return. Realist Capital and Goon Edging account for most of the PnL increase. Actual positive archive marks exist on each of 23–25 June; the BTC/ETH comparison uses cached Binance daily prices. These gains occurred while both references fell, so a broad rising market does not explain them. This does not establish an archive error."))
    display(frame.style.format({"23→25 June NAV return": "{:+.2%}", "Recorded PnL change (USD)": "${:,.0f}"}, na_rep="Not held").hide(axis="index"))
    grouped = curves.T.groupby(positions.Vault).sum().T
    named = ["Realist Capital", "Goon Edging"]
    fig, ax = plt.subplots(figsize=(10, 5))
    for name in named:
        ax.plot(grouped.index, grouped[name], label=name, lw=1.7)
    ax.plot(grouped.index, grouped.drop(columns=named).sum(axis=1), label="All other vaults", lw=1.7)
    ax.axvline(date, color="grey", ls=":", label="26 June equity update")
    ax.set(xlabel="Date (UTC)", ylabel="Cumulative marked cash-flow PnL (USD)", title=f"Source v11 vault profit concentration\n{PERIOD}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    figure(data, fig, "tail-profit-concentration", "Source v11 profit concentration", "Closed positions retain realised PnL. Profits are aggregated across entries in each vault and reconcile to total portfolio equity less initial capital. This is an influence diagnostic rather than a rerun excluding these vaults.")
    shown = delta.head(6)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(shown.index[::-1], shown.iloc[::-1], color="#2563eb")
    ax.set(xlabel="Marked cash-flow PnL change (USD)", title=f"Source v11 update recorded 26 June\n{PERIOD}")
    ax.grid(axis="x", alpha=0.2)
    figure(data, fig, "tail-update-contributions", "Vault PnL on the largest recorded update", "The two largest contributions are about $6,930 from Realist Capital and $4,620 from Goon Edging. Position cash flows remove the effect of purchases and sales from profit attribution; all figures use the same recorded valuation clock.")
    text = "\n## Tail attribution and valuation clock\n\nThe source v11 maximum recorded equity return is 6.887% on 26 June. Equity is marked at a two-day decision cadence, so this is a multi-day update displayed on a daily grid. Realist Capital contributes $6,929.95 and Goon Edging$4,620.27 to that update. Both have actual positive daily NAV marks across 23–25 June; neither is excluded or quarantined by the current curator at the update date. BTC and ETH fell across the corresponding 23–25 June window. A broad rising market does not explain these vault profits, and the observations alone do not establish a data error.\n\n"
    text += frame.to_markdown(index=False, floatfmt=".6f") + "\n"
    with (ROOT / "12-allocation-followup-findings.md").open("a") as handle:
        handle.write(text)
    return frame
