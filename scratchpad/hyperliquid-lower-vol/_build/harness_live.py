"""harness_live.py - NB43: the live hyper-ai executor beside the anchor backtest.

Loaded after harness_crash_exit.py. Reads the live trade-executor state (a dated snapshot of
`https://hyper-ai.tradingstrategy.ai/state`, cached under `~/.cache/tradingstrategy/live-state/`)
and puts it next to the anchor run:

- `live_state()`: the cached snapshot; downloaded once per `LIVE_STATE_DATE`.
- `live_share_price_daily()`, `live_nav_daily()`, `live_flows()`: the Lagoon share price (the
  depositor's return, unaffected by deposits and redemptions), net asset value, and the
  deposit / redemption flow from the reserve position's balance updates.
- `live_cycles()`: one row per live decision, parsed from the executor's own cycle messages
  (candidate counts, survivors, equity, cash, allocation discarded by the size-risk model, and
  the signal flags).
- `live_positions()`, `live_trades()`: ledgers with the executor's close reason read from the
  trade notes, and the count of zero-value repair trades.
- `live_book_at(when)`, `backtest_book_at(label, when)`: the held addresses just after a decision.
- `book_overlap(label, start, end)`: per live decision, the two books side by side with the
  backtest's reconstructed rank of every name held on one side only.
- `curve_comparison(label, start, end)`: both curves rebased at `start`, with return, drawdown,
  volatility and Sharpe on the anchor's two-day grid.
- `fill_timing(start, end)`: for every live fill, the vault's own mark at the first archive mark of
  the UTC day (the backtest's fill point, NB42) against the last mark before the live execution.

The strategy version timeline is copied from `~/code/strategies` git history (commit hashes are
the provenance); deployment dates are inferred from the live cadence, not from git.
"""

import datetime
import json
import re
import urllib.request
from pathlib import Path

import plotly.graph_objects as go
from tradeexecutor.state.state import State
from tradeexecutor.state.balance_update import BalanceUpdateCause

LIVE_STATE_URL = "https://hyper-ai.tradingstrategy.ai/state"
#: Snapshot date. The file is fetched once and reused, so the notebook is reproducible.
LIVE_STATE_DATE = "2026-09-19"
LIVE_STATE_DIR = Path.home() / ".cache/tradingstrategy/live-state"
LIVE_STATE_PATH = LIVE_STATE_DIR / f"hyper-ai-state-{LIVE_STATE_DATE}.json"
#: Vault launch on Lagoon: the first share-price entry (`launched_at` in the executor metadata).
LIVE_LAUNCH = pd.Timestamp("2026-03-30")
#: First live decision on the two-day cycle (v4/v5 deployment; from the cadence, see `live_cadence`).
LIVE_2D_START = pd.Timestamp("2026-08-12")
#: The backtest's last traded day.
BACKTEST_END = pd.Timestamp("2026-09-08")

#: `git log -- strategy/hyper-ai*.py` in ~/code/strategies. Commit dates, not deployment dates.
VERSION_TIMELINE = pd.DataFrame([
    {"commit": "db6f287", "date": "2026-03-19", "version": "v1", "note": "Add HyperAI"},
    {"commit": "20158c3", "date": "2026-07-21", "version": "v2", "note": "cash margin version"},
    {"commit": "41dc621", "date": "2026-07-26", "version": "v3", "note": "gated inverse-vol (#42)"},
    {"commit": "c70c09a", "date": "2026-08-10", "version": "v4", "note": "inverse-variance, 150k capacity (#45)"},
    {"commit": "1956ec6", "date": "2026-08-12", "version": "v5", "note": "CAGR x Sortino ranker (#46) - the incumbent's trading logic"},
    {"commit": "d1aa5b3", "date": "2026-08-21", "version": "v6", "note": "backtest performance-fee accounting only; live logic unchanged from v5"},
])


def live_state() -> State:
    if "state" not in _LIVE_CACHE:
        LIVE_STATE_DIR.mkdir(parents=True, exist_ok=True)
        if not LIVE_STATE_PATH.exists():
            print(f"downloading {LIVE_STATE_URL} to {LIVE_STATE_PATH}")
            urllib.request.urlretrieve(LIVE_STATE_URL, LIVE_STATE_PATH)
        _LIVE_CACHE["state"] = State.read_json_file(LIVE_STATE_PATH)
    return _LIVE_CACHE["state"]


_LIVE_CACHE: dict = {}


def live_facts() -> pd.Series:
    st = live_state()
    ps = st.stats.portfolio
    trades = list(st.portfolio.get_all_trades())
    return pd.Series({
        "snapshot": LIVE_STATE_DATE,
        "first_portfolio_stat": str(ps[0].calculated_at),
        "last_portfolio_stat": str(ps[-1].calculated_at),
        "nav_usd": float(ps[-1].net_asset_value),
        "share_price": float(ps[-1].share_price_usd),
        "positions": len(list(st.portfolio.get_all_positions())),
        "open_positions": len(st.portfolio.open_positions),
        "vaults_traded": len({p.pair.pool_address for p in st.portfolio.get_all_positions() if p.pair.is_vault()}),
        "trades": len(trades),
        "zero_value_trades": sum(1 for t in trades if float(t.get_value() or 0.0) == 0.0),
        "repair_trades": sum(1 for t in trades if t.is_repair_trade()),
        "failed_trades": sum(1 for t in trades if t.is_failed()),
        "frozen_positions": len(st.portfolio.frozen_positions),
        "decision_cycles_logged": len(st.visualisation.messages),
    })


def _portfolio_frame() -> pd.DataFrame:
    if "pf" not in _LIVE_CACHE:
        rows = []
        for s in live_state().stats.portfolio:
            rows.append({"t": pd.Timestamp(s.calculated_at), "share_price": s.share_price_usd, "nav": s.net_asset_value,
                         "equity": float(s.total_equity), "cash": float(s.free_cash or 0.0)})
        _LIVE_CACHE["pf"] = pd.DataFrame(rows).dropna(subset=["share_price"]).sort_values("t").set_index("t")
    return _LIVE_CACHE["pf"]


def live_share_price_daily() -> pd.Series:
    """Last share price of each UTC day, forward-filled over days without a statistics row."""
    s = _portfolio_frame()["share_price"].astype(float)
    return s.resample("1D").last().ffill().rename("live_share_price")


def live_nav_daily() -> pd.DataFrame:
    f = _portfolio_frame()
    out = f[["nav", "equity", "cash"]].astype(float).resample("1D").last().ffill()
    out["invested_share"] = 1.0 - out["cash"] / out["equity"]
    return out


def live_flows() -> pd.DataFrame:
    """Deposits (+) and redemptions (-) into the vault's reserve, from the balance updates."""
    rp = live_state().portfolio.get_default_reserve_position()
    rows = []
    for b in rp.balance_updates.values():
        if b.cause != BalanceUpdateCause.deposit_and_redemption:
            continue
        rows.append({"t": pd.Timestamp(b.block_mined_at), "usd": float(b.usd_value or 0.0), "quantity": float(b.quantity)})
    frame = pd.DataFrame(rows).sort_values("t")
    return frame[frame["usd"] != 0.0].reset_index(drop=True)


def monthly_returns(series: pd.Series) -> pd.Series:
    m = series.resample("1ME").last()
    first = series.iloc[0]
    out = m.pct_change()
    out.iloc[0] = m.iloc[0] / first - 1.0
    return out


def drawdown_table(series: pd.Series, top: int = 3) -> pd.DataFrame:
    """`drawdown_episodes` on any series (the forensics version reads a run by label)."""
    high = series.cummax()
    dd = series / high - 1.0
    episodes, in_dd, start = [], False, None
    for i, t in enumerate(series.index):
        if not in_dd and dd.iloc[i] < 0:
            in_dd, start = True, max(i - 1, 0)
        elif in_dd and dd.iloc[i] >= 0:
            seg = dd.iloc[start:i + 1]
            trough = seg.idxmin()
            episodes.append({"peak": series.index[start].date(), "trough": trough.date(), "recovered": t.date(), "depth": float(seg.min()),
                             "days_to_trough": int((trough - series.index[start]).days), "days_under_water": int((t - series.index[start]).days)})
            in_dd = False
    if in_dd:
        seg = dd.iloc[start:]
        trough = seg.idxmin()
        episodes.append({"peak": series.index[start].date(), "trough": trough.date(), "recovered": None, "depth": float(seg.min()),
                         "days_to_trough": int((trough - series.index[start]).days), "days_under_water": int((series.index[-1] - series.index[start]).days)})
    frame = pd.DataFrame(episodes)
    return frame.sort_values("depth").head(top).reset_index(drop=True) if not frame.empty else frame


# --------------------------------------------------------------------------------------------
# Decisions, positions, trades.
# --------------------------------------------------------------------------------------------

_CYCLE_FIELDS = {
    "Cycle": "cycle", "Open/about to open positions": "positions", "Trades decided": "trades_decided",
    "Pairs meeting inclusion criteria": "pairs_included", "Candidate signals created": "candidates",
    "Selected survivor signals": "survivors", "Total equity": "equity", "Cash": "cash",
    "Discarded allocation because of lack of lit liquidity": "discarded_liquidity_usd", "Top signal pair": "top_signal",
    "Signals with flag capped_by_pool_size": "flag_capped_by_pool_size", "Signals with flag capped_by_concentration": "flag_capped_by_concentration",
    "Signals with flag cannot_deposit": "flag_cannot_deposit", "Signals with flag closed": "flag_closed",
    "Signals with flag close_position_weight_limit": "flag_close_weight_limit", "Signals with flag individual_trade_size_too_small": "flag_trade_too_small",
    "Candidates skipped for closed deposit window": "deposit_window_skips", "Signals blocked by minimum hold": "blocked_by_min_hold",
}


def _number(text: str) -> float:
    m = re.search(r"-?[\d,]+(?:\.\d+)?", str(text))
    return float(m.group(0).replace(",", "")) if m else np.nan


def live_cycles() -> pd.DataFrame:
    """One row per live decision cycle, from the executor's cycle messages."""
    if "cycles" in _LIVE_CACHE:
        return _LIVE_CACHE["cycles"]
    msgs = live_state().visualisation.messages
    rows = []
    for key in sorted(msgs):
        text = "\n".join(msgs[key]) if isinstance(msgs[key], list) else str(msgs[key])
        row = {"t": pd.Timestamp(datetime.datetime.fromtimestamp(float(key), datetime.UTC).replace(tzinfo=None))}
        for line in text.split("\n"):
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            field = _CYCLE_FIELDS.get(name.strip())
            if field is None:
                continue
            row[field] = value.strip() if field == "top_signal" else _number(value)
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values("t").reset_index(drop=True)
    for c in [c for c in _CYCLE_FIELDS.values() if c.startswith("flag_") or c in ("deposit_window_skips", "blocked_by_min_hold", "discarded_liquidity_usd")]:
        if c in frame.columns:
            frame[c] = frame[c].fillna(0.0)
    _LIVE_CACHE["cycles"] = frame
    return frame


def live_cadence() -> pd.DataFrame:
    """Decisions per month and their spacing: shows when the live instance moved to the 2-day cycle."""
    c = live_cycles()
    gap = c["t"].diff().dt.total_seconds() / 86400.0
    frame = pd.DataFrame({"t": c["t"], "gap_days": gap, "hour_utc": c["t"].dt.hour + c["t"].dt.minute / 60.0})
    frame["month"] = frame["t"].dt.to_period("M")
    return frame.groupby("month").agg(decisions=("t", "size"), median_gap_days=("gap_days", "median"),
                                      first_hour_utc=("hour_utc", "first"), last_hour_utc=("hour_utc", "last")).round(2)


def _close_reason(position) -> str:
    sells = [t for t in position.trades.values() if t.is_sell() and t.executed_at is not None and float(t.get_value() or 0.0) > 0]
    if not sells:
        return "no executed sell"
    note = (sells[-1].notes or "").split(":")[0].strip()
    if "below close position weight" in note:
        return "not selected (signal 0)"
    if "protected HyperCore withdrawal" in note:
        return "not selected (signal 0, two-leg withdrawal)"
    return note[:60] or "no note"


def live_positions() -> pd.DataFrame:
    if "positions" in _LIVE_CACHE:
        return _LIVE_CACHE["positions"]
    st = live_state()
    end = pd.Timestamp(st.stats.portfolio[-1].calculated_at)
    rows = []
    for p in st.portfolio.get_all_positions():
        if not p.pair.is_vault():
            continue
        trades = list(p.trades.values())
        buys = sum(float(t.get_value() or 0.0) for t in trades if t.is_buy())
        rows.append({
            "position": p.position_id, "vault": p.pair.get_vault_name(), "address": str(p.pair.pool_address).lower(),
            "opened": pd.Timestamp(p.opened_at), "closed": pd.Timestamp(p.closed_at) if p.closed_at else None,
            "days": int(((pd.Timestamp(p.closed_at) if p.closed_at else end) - pd.Timestamp(p.opened_at)).days),
            "pnl_usd": float(p.get_total_profit_usd() or 0.0), "bought_usd": buys,
            "trades": len(trades), "zero_value_trades": sum(1 for t in trades if float(t.get_value() or 0.0) == 0.0),
            "close_reason": _close_reason(p) if p.closed_at else "open",
        })
    frame = pd.DataFrame(rows).sort_values("opened").reset_index(drop=True)
    frame["return_on_bought"] = frame["pnl_usd"] / frame["bought_usd"].replace(0.0, np.nan)
    _LIVE_CACHE["positions"] = frame
    return frame


def live_trades() -> pd.DataFrame:
    if "trades" in _LIVE_CACHE:
        return _LIVE_CACHE["trades"]
    rows = []
    for t in live_state().portfolio.get_all_trades():
        if not t.pair.is_vault() or t.executed_at is None:
            continue
        rows.append({"trade": t.trade_id, "position": t.position_id, "vault": t.pair.get_vault_name(), "address": str(t.pair.pool_address).lower(),
                     "executed_at": pd.Timestamp(t.executed_at), "side": "buy" if t.is_buy() else "sell", "usd": float(t.get_value() or 0.0),
                     "repair": bool(t.is_repair_trade()), "note": (t.notes or "").split("|")[0].strip()[:90]})
    _LIVE_CACHE["trades"] = pd.DataFrame(rows).sort_values("executed_at").reset_index(drop=True)
    return _LIVE_CACHE["trades"]


def live_turnover(start, end) -> pd.DataFrame:
    """Per live decision: executed buy and sell volume as a share of equity (repairs excluded)."""
    tr = live_trades()
    tr = tr[(tr["executed_at"] >= pd.Timestamp(start)) & (tr["executed_at"] <= pd.Timestamp(end)) & (tr["usd"] > 0)]
    c = live_cycles()
    rows = []
    for i, r in c[(c["t"] >= pd.Timestamp(start)) & (c["t"] <= pd.Timestamp(end))].iterrows():
        nxt = c["t"].iloc[i + 1] if i + 1 < len(c) else pd.Timestamp(end) + pd.Timedelta(days=1)
        mine = tr[(tr["executed_at"] >= r["t"]) & (tr["executed_at"] < nxt)]
        eq = float(r.get("equity", np.nan))
        rows.append({"t": r["t"], "equity": eq, "buys_usd": float(mine.loc[mine["side"] == "buy", "usd"].sum()),
                     "sells_usd": float(mine.loc[mine["side"] == "sell", "usd"].sum())})
    frame = pd.DataFrame(rows)
    frame["turnover"] = (frame["buys_usd"] + frame["sells_usd"]) / 2.0 / frame["equity"]
    return frame


def backtest_turnover(label: str, start, end) -> pd.DataFrame:
    state_ = run_by_label[label]["state"]
    equity_at = {pd.Timestamp(s.calculated_at): float(s.total_equity) for s in state_.stats.portfolio}
    rows = {}
    for t in state_.portfolio.get_all_trades():
        if not t.pair.is_vault() or t.executed_at is None:
            continue
        ts = pd.Timestamp(t.executed_at)
        if ts < pd.Timestamp(start) or ts > pd.Timestamp(end):
            continue
        row = rows.setdefault(ts, {"t": ts, "buys_usd": 0.0, "sells_usd": 0.0})
        row["buys_usd" if t.is_buy() else "sells_usd"] += abs(float(t.get_value() or 0.0))
    frame = pd.DataFrame(list(rows.values())).sort_values("t")
    eq = pd.Series(equity_at).sort_index()
    frame["equity"] = [float(eq[eq.index <= t].iloc[-1]) if (eq.index <= t).any() else np.nan for t in frame["t"]]
    frame["turnover"] = (frame["buys_usd"] + frame["sells_usd"]) / 2.0 / frame["equity"]
    return frame.reset_index(drop=True)


# --------------------------------------------------------------------------------------------
# Books and overlap.
# --------------------------------------------------------------------------------------------

#: Live trades execute minutes after the decision; the book "after" a live decision is read here.
LIVE_SETTLE = pd.Timedelta(hours=3)


def live_book_at(when) -> dict:
    """{address: name} of the live vault positions open at `when` + LIVE_SETTLE."""
    when = pd.Timestamp(when) + LIVE_SETTLE
    pos = live_positions()
    mask = (pos["opened"] <= when) & (pos["closed"].isna() | (pos["closed"] > when))
    return dict(zip(pos.loc[mask, "address"], pos.loc[mask, "vault"]))


def live_weights_at(when) -> dict:
    """{address: value / equity} from the last position statistics row of the UTC day of `when`."""
    st = live_state()
    day = pd.Timestamp(when).normalize()
    if "pos_stats" not in _LIVE_CACHE:
        rows = []
        addr = {p.position_id: str(p.pair.pool_address).lower() for p in st.portfolio.get_all_positions() if p.pair.is_vault()}
        for pid, stats in st.stats.positions.items():
            if pid not in addr:
                continue
            for s in stats:
                rows.append({"t": pd.Timestamp(s.calculated_at), "address": addr[pid], "value": float(s.value or 0.0)})
        _LIVE_CACHE["pos_stats"] = pd.DataFrame(rows)
    ps = _LIVE_CACHE["pos_stats"]
    ps = ps[(ps["t"] >= day) & (ps["t"] < day + pd.Timedelta(days=1))]
    if ps.empty:
        return {}
    last_t = ps["t"].max()
    eq = _portfolio_frame()["equity"]
    equity = float(eq[eq.index <= last_t].iloc[-1])
    vals = ps[ps["t"] == last_t].groupby("address")["value"].sum()
    return {a: float(v) / equity for a, v in vals.items() if v > 0}


def backtest_decision_at_or_before(label: str, when) -> pd.Timestamp:
    ts = pd.DatetimeIndex(_decision_timestamps(label))
    ts = ts[ts <= pd.Timestamp(when)]
    return ts[-1] if len(ts) else None


def backtest_book_at(label: str, when) -> dict:
    """{address: name} of the run's vault positions open just after the decision at `when`."""
    when = pd.Timestamp(when)
    out = {}
    for p in _vault_positions(run_by_label[label]["state"]):
        opened, closed = pd.Timestamp(p.opened_at), (pd.Timestamp(p.closed_at) if p.closed_at else None)
        if opened <= when and (closed is None or closed > when):
            addr = str(p.pair.pool_address).lower()
            out[addr] = vault_name(addr)
    return out


def _rank_of(t, address: str) -> tuple:
    frame = ranking_at(t)
    if frame.empty:
        return (np.nan, 0)
    hit = frame[frame["address"] == address]
    return (int(hit.iloc[0]["rank"]) if not hit.empty else np.nan, int(len(frame)))


def book_overlap(label: str, start, end) -> pd.DataFrame:
    """Per live decision in [start, end]: the live and backtest books after the decision, their
    overlap, and for each name on one side only where the backtest's ranking put it."""
    rows = []
    c = live_cycles()
    for _, r in c[(c["t"] >= pd.Timestamp(start)) & (c["t"] <= pd.Timestamp(end))].iterrows():
        t_live = r["t"]
        t_bt = backtest_decision_at_or_before(label, t_live)
        if t_bt is None:
            continue
        live, bt = live_book_at(t_live), backtest_book_at(label, t_bt)
        both = set(live) & set(bt)
        only_live, only_bt = set(live) - set(bt), set(bt) - set(live)
        def describe(addresses: set, names: dict) -> str:
            parts = []
            for a in sorted(addresses, key=lambda x: names[x]):
                if a not in PAIR_BY_ADDRESS:
                    parts.append(f"{names[a]} [not in backtest universe]")
                    continue
                rank, n = _rank_of(t_bt, a)
                parts.append(f"{names[a]} [rank {rank if rank == rank else 'not in pool'} of {n}]")
            return "; ".join(parts)
        rows.append({"live_decision": t_live, "backtest_decision": t_bt, "live_n": len(live), "backtest_n": len(bt), "both": len(both),
                     "jaccard": len(both) / len(set(live) | set(bt)) if (live or bt) else np.nan,
                     "only_live": describe(only_live, live), "only_backtest": describe(only_bt, bt)})
    return pd.DataFrame(rows)


def name_level_divergence(label: str, start, end) -> pd.DataFrame:
    """Every (decision, vault) held on one side only, classified."""
    rows = []
    c = live_cycles()
    for _, r in c[(c["t"] >= pd.Timestamp(start)) & (c["t"] <= pd.Timestamp(end))].iterrows():
        t_live = r["t"]
        t_bt = backtest_decision_at_or_before(label, t_live)
        if t_bt is None:
            continue
        live, bt = live_book_at(t_live), backtest_book_at(label, t_bt)
        for a in set(live) - set(bt):
            if a not in PAIR_BY_ADDRESS:
                cls = "live only: not in backtest universe"
            else:
                rank, n = _rank_of(t_bt, a)
                cls = "live only: not in backtest pool at t" if rank != rank else (f"live only: backtest rank <= {N_BOOK}" if rank <= N_BOOK else f"live only: backtest rank > {N_BOOK}")
            rows.append({"decision": t_live, "vault": live[a], "address": a, "side": "live only", "class": cls})
        for a in set(bt) - set(live):
            rank, n = _rank_of(t_bt, a)
            rows.append({"decision": t_live, "vault": bt[a], "address": a, "side": "backtest only", "class": f"backtest only (backtest rank {rank if rank == rank else 'n/a'})"})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------
# Curves.
# --------------------------------------------------------------------------------------------

def backtest_equity_daily(label: str) -> pd.Series:
    eq = run_by_label[label]["equity"]
    return eq.resample("1D").last().ffill().rename(f"{label}_equity")


def curve_comparison(label: str, start, end) -> tuple:
    """Rebased curves and a statistics table for the anchor and the live share price on [start, end].
    Volatility and Sharpe are computed on the anchor's own two-day decision grid for both."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    bt = backtest_equity_daily(label)
    lv = live_share_price_daily()
    both = pd.concat([bt, lv], axis=1).loc[start:end].dropna()
    rebased = both / both.iloc[0]
    grid = run_by_label[label]["equity"].index
    grid = grid[(grid >= start) & (grid <= end)]
    stats = {}
    for col in rebased.columns:
        s = rebased[col]
        on_grid = s.reindex(grid.normalize()).dropna()
        rc = on_grid.pct_change().dropna()
        ppy = 365.0 / 2.0
        stats[col] = {"start": str(s.index[0].date()), "end": str(s.index[-1].date()), "days": int((s.index[-1] - s.index[0]).days),
                      "cumulative_return": float(s.iloc[-1] - 1.0), "max_drawdown": float((s / s.cummax() - 1.0).min()),
                      "vol_2d_grid": float(rc.std() * np.sqrt(ppy)), "sharpe_2d_grid": float(calculate_sharpe(rc, periods=ppy)) if len(rc) > 2 else np.nan,
                      "grid_points": int(len(on_grid))}
    return rebased, pd.DataFrame(stats)


def curve_figure(rebased: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    for col in rebased.columns:
        fig.add_trace(go.Scatter(x=rebased.index, y=rebased[col], mode="lines", name=col))
    fig.update_layout(title=title, height=420, template="plotly_white", yaxis_title="rebased to 1")
    return fig


def live_overview_figure() -> go.Figure:
    sp = live_share_price_daily()
    nav = live_nav_daily()
    flows = live_flows()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sp.index, y=sp, mode="lines", name="share price", yaxis="y1"))
    fig.add_trace(go.Scatter(x=nav.index, y=nav["nav"], mode="lines", name="NAV (USD)", yaxis="y2", line=dict(dash="dot")))
    fig.add_trace(go.Bar(x=flows["t"], y=flows["usd"], name="deposit (+) / redemption (-) USD", yaxis="y2", opacity=0.5))
    for _, v in VERSION_TIMELINE.iterrows():
        # plotly's annotated vline cannot average Timestamps; milliseconds since the epoch work.
        fig.add_vline(x=pd.Timestamp(v["date"]).value / 1e6, line=dict(color="grey", dash="dash", width=1), annotation_text=v["version"], annotation_position="top")
    fig.update_layout(title="Live hyper-ai: share price, NAV and flows (dashed lines: strategy version commits)", height=480, template="plotly_white",
                      yaxis=dict(title="share price"), yaxis2=dict(title="USD", overlaying="y", side="right"))
    return fig


# --------------------------------------------------------------------------------------------
# Fill timing.
# --------------------------------------------------------------------------------------------

def _archive_marks(address: str) -> pd.Series:
    key = ("__marks__", address)
    if key not in _SERIES_CACHE:
        g = _archive()
        g = g[g["address"] == str(address).lower()]
        _SERIES_CACHE[key] = g.set_index("timestamp")["share_price"].astype(float).sort_index()
    return _SERIES_CACHE[key]


def fill_timing(start, end) -> pd.DataFrame:
    """For each executed live fill with value: the vault's first archive mark of the UTC day (the
    backtest's fill point) and the last mark at or before the live execution. `usd_vs_day_open`
    is what the live fill gained (+) or lost (-) against filling at the day's first mark."""
    tr = live_trades()
    tr = tr[(tr["executed_at"] >= pd.Timestamp(start)) & (tr["executed_at"] <= pd.Timestamp(end)) & (tr["usd"] > 0)]
    rows = []
    for _, r in tr.iterrows():
        marks = _archive_marks(r["address"])
        day = r["executed_at"].normalize()
        today = marks[(marks.index >= day) & (marks.index <= r["executed_at"])]
        if today.empty:
            rows.append({**r.to_dict(), "day_open": np.nan, "at_fill": np.nan, "move": np.nan, "usd_vs_day_open": np.nan, "marks_before_fill": 0})
            continue
        p_open, p_fill = float(today.iloc[0]), float(today.iloc[-1])
        move = p_fill / p_open - 1.0
        # A sell at a higher mark receives more; a buy at a higher mark gets fewer shares.
        usd = r["usd"] * (1.0 - p_open / p_fill) if r["side"] == "sell" else r["usd"] * (p_open / p_fill - 1.0)
        rows.append({**r.to_dict(), "day_open": p_open, "at_fill": p_fill, "move": move, "usd_vs_day_open": usd, "marks_before_fill": int(len(today))})
    return pd.DataFrame(rows)


def per_vault_pnl(label: str, start, end) -> pd.DataFrame:
    """Net P&L per vault, live and backtest, for positions CLOSED in (or still open at the end of)
    [start, end], with the count of positions on each side."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    lv = live_positions()
    lv = lv[(lv["opened"] <= end) & (lv["closed"].isna() | (lv["closed"] >= start))]
    live_g = lv.groupby("address").agg(live_pnl=("pnl_usd", "sum"), live_positions=("position", "size"), vault=("vault", "first"))
    bt_rows = []
    for p in _vault_positions(run_by_label[label]["state"]):
        opened, closed = pd.Timestamp(p.opened_at), (pd.Timestamp(p.closed_at) if p.closed_at else None)
        if opened <= end and (closed is None or closed >= start):
            bt_rows.append({"address": str(p.pair.pool_address).lower(), "pnl": float(p.get_total_profit_usd() or 0.0)})
    bt = pd.DataFrame(bt_rows)
    bt_g = bt.groupby("address").agg(backtest_pnl=("pnl", "sum"), backtest_positions=("pnl", "size")) if not bt.empty else pd.DataFrame(columns=["backtest_pnl", "backtest_positions"])
    out = live_g.join(bt_g, how="outer")
    out["vault"] = [n if isinstance(n, str) else vault_name(a) for a, n in zip(out.index, out["vault"])]
    for c in ("live_pnl", "backtest_pnl"):
        out[c] = out[c].fillna(0.0)
    for c in ("live_positions", "backtest_positions"):
        out[c] = out[c].fillna(0).astype(int)
    return out.sort_values("backtest_pnl", ascending=False).reset_index()



def live_pnl_change(start, end) -> pd.DataFrame:
    """`pnl_change_by_position` for the live state: change in each position's cumulative P&L
    between `start` (exclusive) and `end` (inclusive), summed per vault."""
    st = live_state()
    peak, trough = pd.Timestamp(start), pd.Timestamp(end)
    rows = []
    for p in st.portfolio.get_all_positions():
        if not p.pair.is_vault():
            continue
        series = st.stats.positions.get(p.position_id, [])
        if not series:
            continue
        s = pd.Series({pd.Timestamp(x.calculated_at): float(x.profit_usd or 0.0) for x in series}).sort_index()
        before = s[s.index <= peak]
        during = s[(s.index > peak) & (s.index <= trough)]
        if during.empty:
            continue
        start_value = float(before.iloc[-1]) if len(before) else 0.0
        rows.append({"vault": p.pair.get_vault_name(), "address": str(p.pair.pool_address).lower(), "pnl_change_usd": float(during.iloc[-1] - start_value)})
    frame = pd.DataFrame(rows)
    return frame.groupby(["address", "vault"])["pnl_change_usd"].sum().reset_index().sort_values("pnl_change_usd")


def pnl_change_both_sides(label: str, start, end) -> pd.DataFrame:
    """Per vault: P&L change in (start, end] live and backtest, each as a share of the side's
    equity at `start`, so the two books can be read on one scale."""
    lv = live_pnl_change(start, end).set_index("address")
    bt = pnl_change_by_position(label, start, end)
    bt = bt.groupby("address")["pnl_change_usd"].sum().rename("backtest_pnl_change") if not bt.empty else pd.Series(dtype=float, name="backtest_pnl_change")
    eq_live = float(live_nav_daily()["equity"].loc[:pd.Timestamp(start)].iloc[-1])
    eq_bt = float(run_by_label[label]["equity"].loc[:pd.Timestamp(start)].iloc[-1])
    out = pd.concat([lv["pnl_change_usd"].rename("live_pnl_change"), bt], axis=1).fillna(0.0)
    out["vault"] = [vault_name(a) if a in PAIR_BY_ADDRESS else lv["vault"].get(a, short(a)) for a in out.index]
    out["live_share_of_equity"] = out["live_pnl_change"] / eq_live
    out["backtest_share_of_equity"] = out["backtest_pnl_change"] / eq_bt
    out = out[["vault", "live_pnl_change", "live_share_of_equity", "backtest_pnl_change", "backtest_share_of_equity"]]
    total = pd.DataFrame({"vault": ["TOTAL"], "live_pnl_change": [out["live_pnl_change"].sum()], "live_share_of_equity": [out["live_share_of_equity"].sum()],
                          "backtest_pnl_change": [out["backtest_pnl_change"].sum()], "backtest_share_of_equity": [out["backtest_share_of_equity"].sum()]}, index=["total"])
    return pd.concat([out.sort_values("live_share_of_equity"), total])


def weights_both_sides(label: str, when) -> pd.DataFrame:
    """Held weights after the decision at `when`, live and backtest, per vault."""
    t_bt = backtest_decision_at_or_before(label, when)
    lw = live_weights_at(when)
    bw = {str(pair.pool_address).lower(): w for pair, w in _position_weights(run_by_label[label]["state"]).get(t_bt, [])}
    names = {**backtest_book_at(label, t_bt), **live_book_at(when)}
    rows = []
    for a in set(lw) | set(bw):
        rows.append({"vault": names.get(a, vault_name(a) if a in PAIR_BY_ADDRESS else short(a)), "live_weight": lw.get(a, 0.0), "backtest_weight": bw.get(a, 0.0)})
    return pd.DataFrame(rows).sort_values("backtest_weight", ascending=False).reset_index(drop=True)



def jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return str(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj) if obj == obj else None
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if obj is pd.NaT:
        return None
    return obj


print(f"harness_live.py: snapshot {LIVE_STATE_DATE}; launch {LIVE_LAUNCH.date()}; two-day cadence from {LIVE_2D_START.date()}; backtest end {BACKTEST_END.date()}.")
