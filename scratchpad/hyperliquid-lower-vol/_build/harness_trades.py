"""harness_trades.py - NB41: the trades, by vault name, with why they were entered and exited.

Loaded after harness_forensics.py. Adds:

- `vault_name(address)`: the vault's name from the pair (falls back to the vault metadata file).
- `pool_at(t)`: the momentum-gated candidate pool at decision t, taken from a threshold run's
  crash log (`candidate_addresses` is written BEFORE the crash filter, so it is the pool every
  run sees at t, up to `is_good_pair` differences), with each candidate's trailing volatility.
- `ranking_at(t)`: every candidate at t ranked by the incumbent's composite score read at T-1
  (`cagr_sortino_weight`, offline), with its legs (`cagr_score`, `sortino_score`), the momentum
  gate value, volatility and `quality_sharpe`. Ranks are a RECONSTRUCTION from the cached
  indicator set: the in-trade tie order, the deposit-window check, quarantine and masks are not
  mirrored, so a rank can be off by a place where scores tie.
- `entry_reason(label, position)` and `exit_reason(label, position)`: what the ranking said on
  the decision that opened or closed the position: rank of M, the legs, and on exit whether the
  vault fell out of the pool (momentum gate / left the universe), was excluded by the run's
  crash filter or quality floor, or was outranked (and by whom).
- `vault_path(address, entry, exit)`: the vault's OWN share-price return in the 90 days before
  entry, while held, and 30 and 60 days after exit.
- `trade_ledger(label)`: one row per position with all of the above.
- `vault_figure(address, labels)`: the vault's share price with each run's held intervals shaded.
"""

import json
from pathlib import Path
import plotly.graph_objects as go

VAULT_METADATA_PATH = Path.home() / ".cache/tradingstrategy/vaults/downloads/vault-metadata.json"
_META_NAMES: dict = {}
try:
    for _v in json.loads(VAULT_METADATA_PATH.read_text())["vaults"]:
        for _k in ("address", "share_token_address"):
            if _v.get(_k):
                _META_NAMES[str(_v[_k]).lower()] = _v["name"]
except Exception as _e:   # the metadata file is a convenience; the pair carries the name
    print(f"vault metadata not read: {_e}")


def vault_name(address: str) -> str:
    address = str(address).lower()
    pair = PAIR_BY_ADDRESS.get(address)
    name = None
    if pair is not None:
        try:
            name = pair.get_vault_name()
        except Exception:
            name = None
    name = name or _META_NAMES.get(address) or short(address)
    return name


#: The run whose crash log supplies the candidate pool per decision.
POOL_SOURCE = "thr150"
GATE_THRESHOLD = float(Parameters.gate_threshold)
N_BOOK = int(Parameters.max_assets_in_portfolio)


def pool_at(t) -> dict:
    """{address: trailing annualised volatility (NaN if unmeasured)} of the momentum-gated pool at t."""
    log = run_by_label[POOL_SOURCE]["crash_log"]
    rec = log.get(pd.Timestamp(t))
    if rec is None:
        rec = log.get(t)
    if rec is None:
        return {}
    return {a: float(rec["vol"].get(a, np.nan)) for a in rec["candidate_addresses"]}


_RANK_CACHE: dict = {}


def ranking_at(t) -> pd.DataFrame:
    """Every candidate at t with the composite score and its legs at T-1, ranked."""
    t = pd.Timestamp(t)
    if t in _RANK_CACHE:
        return _RANK_CACHE[t]
    rows = []
    for addr, vol in pool_at(t).items():
        pair = PAIR_BY_ADDRESS.get(addr)
        if pair is None:
            continue
        score = value_at_prior(indicator_series("cagr_sortino_weight", pair), t)
        rows.append({
            "address": addr, "vault": vault_name(addr),
            "score": score if np.isfinite(score) else 0.0, "score_finite": bool(np.isfinite(score)),
            "cagr_360d": value_at_prior(indicator_series("cagr_score", pair), t),
            "sortino_45d": value_at_prior(indicator_series("sortino_score", pair), t) * SHARPE_SCORE_CAP,
            "return_14d": value_at_prior(indicator_series("return_gate", pair), t),
            "vol": vol, "quality_180d": value_at_prior(indicator_series("quality_sharpe", pair), t),
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        _RANK_CACHE[t] = frame
        return frame
    # The incumbent orders by (-score, pair id); an unscored vault is 0.0 and ranks last.
    frame["pair_id"] = [PAIR_BY_ADDRESS[a].internal_id for a in frame["address"]]
    frame = frame.sort_values(["score", "pair_id"], ascending=[False, True]).reset_index(drop=True)
    frame["rank"] = np.arange(1, len(frame) + 1)
    _RANK_CACHE[t] = frame
    return frame


def _row_for(frame: pd.DataFrame, address: str):
    hit = frame[frame["address"] == address]
    return None if hit.empty else hit.iloc[0]


def _decision_timestamps(label: str) -> list:
    return sorted(_position_weights(run_by_label[label]["state"]))


def _prior_decision(label: str, when) -> pd.Timestamp:
    """The last decision timestamp at or before `when` (a position's opened_at / closed_at)."""
    when = pd.Timestamp(when)
    stamps = _decision_timestamps(label)
    idx = pd.DatetimeIndex(stamps).searchsorted(when, side="right") - 1
    return pd.Timestamp(stamps[max(idx, 0)])


def entry_reason(label: str, position) -> dict:
    t = _prior_decision(label, position.opened_at)
    addr = str(position.pair.pool_address).lower()
    frame = ranking_at(t)
    row = _row_for(frame, addr)
    out = {"entry_decision": t, "pool_size": int(len(frame))}
    if row is None:
        out.update({"entry_rank": np.nan, "entry_reason": "not in the reconstructed pool (pool log missing for this date)"})
        return out
    out.update({"entry_rank": int(row["rank"]), "entry_score": float(row["score"]), "entry_cagr_360d": float(row["cagr_360d"]),
                "entry_sortino_45d": float(row["sortino_45d"]), "entry_return_14d": float(row["return_14d"]),
                "entry_vol": float(row["vol"]), "entry_quality_180d": float(row["quality_180d"])})
    if not row["score_finite"]:
        out["entry_reason"] = "unscored (no 360-day CAGR or no down day in the Sortino window) - filled a slot the scored names left empty"
    elif row["rank"] <= N_BOOK:
        out["entry_reason"] = f"ranked #{int(row['rank'])} of {len(frame)} on the composite"
    else:
        out["entry_reason"] = f"ranked #{int(row['rank'])} of {len(frame)}: entered below the top {N_BOOK} (a higher name was held back by the deposit window, a mask, or the filter)"
    return out


def exit_reason(label: str, position) -> dict:
    entry = run_by_label[label]
    if position.closed_at is None:
        return {"exit_decision": pd.NaT, "exit_reason": "still open at the end of the window"}
    t = _prior_decision(label, position.closed_at)
    addr = str(position.pair.pool_address).lower()
    out = {"exit_decision": t}
    # 1. the run's own filters at that decision
    crash = (entry.get("crash_log") or {}).get(t)
    if crash and addr in crash["excluded_addresses"]:
        out["exit_reason"] = f"crash filter: volatility {crash['vol'].get(addr, float('nan')):.2f} above the exit limit {crash['limit'].get(addr, float('nan')):.2f}"
        return out
    quality = (entry.get("quality_log") or {}).get(t)
    if quality and addr in quality["removed_addresses"]:
        q = quality["quality"].get(addr, float("nan"))
        out["exit_reason"] = f"quality floor: score {q:.2f} below {quality['floor']:.2f}" if np.isfinite(q) else "quality floor: score not measurable"
        return out
    # 2. the pool
    frame = ranking_at(t)
    row = _row_for(frame, addr)
    pair = position.pair
    gate = value_at_prior(indicator_series("return_gate", pair), t)
    if row is None:
        if np.isfinite(gate) and gate <= GATE_THRESHOLD:
            out["exit_reason"] = f"momentum gate: 14-day return {gate:+.1%} at or below {GATE_THRESHOLD:+.0%}"
        elif not np.isfinite(gate):
            out["exit_reason"] = "momentum gate: no 14-day return (mark missing)"
        else:
            out["exit_reason"] = "left the tradable universe (TVL or availability screen)"
        out["exit_return_14d"] = gate
        return out
    out.update({"exit_rank": int(row["rank"]), "exit_score": float(row["score"]), "exit_return_14d": float(row["return_14d"]),
                "exit_vol": float(row["vol"])})
    if row["rank"] > N_BOOK:
        displacers = frame[frame["rank"] <= N_BOOK]["vault"].tolist()
        out["exit_reason"] = f"outranked: #{int(row['rank'])} of {len(frame)}; the top {N_BOOK} were {', '.join(displacers)}"
    else:
        out["exit_reason"] = f"in the top {N_BOOK} (#{int(row['rank'])}) yet closed: sizing, the deposit window or a mask - not a ranking exit"
    return out


def vault_path(address: str, entry, exit_, before_days: int = 90, after_days: int = 30) -> dict:
    """The vault's own share-price log returns around the holding."""
    pair = PAIR_BY_ADDRESS.get(str(address).lower())
    if pair is None:
        return {}
    close = close_series(pair)
    entry = pd.Timestamp(entry)
    end = pd.Timestamp(exit_) if exit_ is not None and exit_ is not pd.NaT else close.index[-1]

    def at(ts):
        i = close.index.searchsorted(pd.Timestamp(ts), side="right") - 1
        return float(close.iloc[i]) if i >= 0 else float("nan")

    def lr(a, b):
        pa, pb = at(a), at(b)
        return float(np.log(pb / pa)) if np.isfinite(pa) and np.isfinite(pb) and pa > 0 else float("nan")

    first = close.index[0]
    return {"vault_age_at_entry_days": int((entry - first).days),
            f"vault_return_{before_days}d_before": lr(entry - pd.Timedelta(days=before_days), entry),
            "vault_return_while_held": lr(entry, end),
            f"vault_return_{after_days}d_after": lr(end, end + pd.Timedelta(days=after_days)) if exit_ is not None and exit_ is not pd.NaT else float("nan"),
            "vault_return_60d_after": lr(end, end + pd.Timedelta(days=60)) if exit_ is not None and exit_ is not pd.NaT else float("nan"),
            "vault_max_dd_while_held": float((close.loc[entry:end] / close.loc[entry:end].cummax() - 1.0).min()) if len(close.loc[entry:end]) else float("nan")}


def rebalancing_split(state_, position) -> dict:
    """The position's P&L split into what buying and holding the OPENING value would have made
    (the vault's own return over the holding) and the rest, which is the effect of the two-day
    rebalancing - trimming after rises and adding after falls under the cap and the sizing rule.
    The opening value is the first position statistic; the vault return is from its marks."""
    stats = state_.stats.positions.get(position.position_id, [])
    if not stats:
        return {"opening_value_usd": float("nan"), "buy_and_hold_pnl_usd": float("nan"), "rebalancing_pnl_usd": float("nan")}
    opening = float(stats[0].value or 0.0)
    path = vault_path(str(position.pair.pool_address), position.opened_at, position.closed_at)
    r = path.get("vault_return_while_held", float("nan"))
    bah = opening * (np.exp(r) - 1.0) if np.isfinite(r) else float("nan")
    pnl = float(position.get_total_profit_usd() or 0.0)
    return {"opening_value_usd": opening, "buy_and_hold_pnl_usd": bah, "rebalancing_pnl_usd": pnl - bah if np.isfinite(bah) else float("nan")}


def trade_ledger(label: str) -> pd.DataFrame:
    state_ = run_by_label[label]["state"]
    rows = []
    for p in _vault_positions(state_):
        addr = str(p.pair.pool_address).lower()
        row = {"position": p.position_id, "vault": vault_name(addr), "address": addr,
               "opened": pd.Timestamp(p.opened_at).date(), "closed": pd.Timestamp(p.closed_at).date() if p.closed_at else None,
               "days": int(((pd.Timestamp(p.closed_at) if p.closed_at else pd.Timestamp(state_.stats.portfolio[-1].calculated_at)) - pd.Timestamp(p.opened_at)).days),
               "pnl_usd": float(p.get_total_profit_usd() or 0.0), "peak_weight": _peak_weight(state_, p.position_id)}
        row.update(entry_reason(label, p))
        row.update(exit_reason(label, p))
        row.update(vault_path(addr, p.opened_at, p.closed_at))
        row.update(rebalancing_split(state_, p))
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    net = frame["pnl_usd"].sum()
    frame["pnl_share"] = frame["pnl_usd"] / net if net else np.nan
    return frame.reindex(frame["pnl_usd"].abs().sort_values(ascending=False).index).reset_index(drop=True)


LEDGER_COLUMNS = ["vault", "opened", "closed", "days", "pnl_usd", "pnl_share", "peak_weight", "opening_value_usd", "buy_and_hold_pnl_usd", "rebalancing_pnl_usd",
                  "entry_rank", "pool_size", "entry_cagr_360d", "entry_sortino_45d", "entry_vol", "entry_quality_180d", "entry_reason",
                  "vault_return_90d_before", "vault_return_while_held", "vault_max_dd_while_held", "vault_return_30d_after",
                  "exit_rank", "exit_return_14d", "exit_reason"]


def held_intervals(label: str, address: str) -> list:
    out = []
    for p in _vault_positions(run_by_label[label]["state"]):
        if str(p.pair.pool_address).lower() == str(address).lower():
            out.append((pd.Timestamp(p.opened_at), pd.Timestamp(p.closed_at) if p.closed_at else None, float(p.get_total_profit_usd() or 0.0)))
    return sorted(out)


def vault_figure(address: str, labels: list, start=None, end=None) -> go.Figure:
    """The vault's share price (normalised to 1.0 at the window start) with each run's held
    intervals shaded and labelled with the position's P&L."""
    address = str(address).lower()
    pair = PAIR_BY_ADDRESS[address]
    close = close_series(pair)
    start = pd.Timestamp(start) if start is not None else max(close.index[0], WINDOW_START - pd.Timedelta(days=120))
    end = pd.Timestamp(end) if end is not None else close.index[-1]
    seg = close.loc[start:end]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=seg.index, y=seg / seg.iloc[0], mode="lines", name=f"{vault_name(address)} share price", line=dict(color="black")))
    colours = ["rgba(31,119,180,0.18)", "rgba(255,127,14,0.18)", "rgba(44,160,44,0.18)", "rgba(214,39,40,0.18)", "rgba(148,103,189,0.18)"]
    for i, label in enumerate(labels):
        for (a, b, pnl) in held_intervals(label, address):
            b_ = b if b is not None else end
            fig.add_vrect(x0=a, x1=b_, fillcolor=colours[i % len(colours)], line_width=0,
                          annotation_text=f"{label}: {pnl:+,.0f}", annotation_position="top left" if i % 2 == 0 else "bottom left",
                          annotation_font_size=10)
    fig.add_vline(x=WINDOW_START, line_dash="dot", line_color="grey")
    fig.update_layout(title=f"{vault_name(address)} ({short(address)}) - share price, held intervals shaded", height=380,
                      template="plotly_white", yaxis_title="share price / start", showlegend=False)
    return fig


def equity_with_positions(label: str, top: int = 6) -> go.Figure:
    """The run's equity with the `top` positions by |P&L| marked at entry and exit."""
    entry = run_by_label[label]
    eq = entry["equity"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq.index, y=eq / eq.iloc[0], mode="lines", name=label, line=dict(color="black")))
    ledger = trade_ledger(label).head(top)
    for _, r in ledger.iterrows():
        a = pd.Timestamp(r["opened"])
        b = pd.Timestamp(r["closed"]) if r["closed"] is not None else eq.index[-1]
        fig.add_vrect(x0=a, x1=b, fillcolor="rgba(31,119,180,0.10)" if r["pnl_usd"] > 0 else "rgba(214,39,40,0.12)", line_width=0,
                      annotation_text=f"{r['vault']} {r['pnl_usd']:+,.0f}", annotation_position="top left", annotation_font_size=10, annotation_textangle=-90)
    fig.update_layout(title=f"{label}: equity with the {top} largest positions", height=480, template="plotly_white", yaxis_title="equity / initial")
    return fig


print(f"harness_trades.py: {len(_META_NAMES)} vault names from metadata; pool source {POOL_SOURCE}; gate {GATE_THRESHOLD}; N {N_BOOK}.")
