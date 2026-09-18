"""harness_forensics.py - NB40 bookkeeping: the quality-floor and cash-sleeve logs, and the
position-level forensics the rejected leads are examined with.

Loaded after harness_threshold.py. Redefines `run_and_record()` once more so `QUALITY_LOG` and
`CASH_SLEEVE_LOG` are cleared before each run and snapshotted after it, and adds:

- `position_ledger()`: every closed and open position of a run with its P&L, holding time and
  peak weight, so a gate failure can be read off the trades that caused it.
- `drawdown_episodes()` and `episode_attribution()`: the deepest drawdowns of the equity curve
  and which held vaults lost the money inside them.
- `worst_cycles()`: the worst cycle returns and the vault that moved most in each.
- `held_exclusion_outcomes()`: every time the crash filter removed a name the book was holding,
  the vault's own forward return afterwards - did the exit avoid a loss or forgo a gain.
- `band_attribution()`: the names one run held while a tighter run's filter excluded them, and
  their share of each run's P&L - the plateau cliff read as a list of vaults.
- `sparse_capital_share()`: capital-weighted count of moved marks in the trailing 90 rows, and the
  share of capital in names with fewer than 30 - the sizing rule's known bias made visible.
- `book_overlap()`: per-decision overlap of a run's book with the anchor's.
- `risk_row()`: the risk-side panel: drawdown, ulcer, worst cycles, time under water, held-book
  volatility, concentration, luck.
- `quality_stats()` and `sleeve_stats()`: what the floor and the sleeve actually did per run.
"""

#: Moved marks in the trailing 90 rows below which a name is called sparse-marked.
SPARSE_FRESH_ROWS = 30
#: Forward horizon, in days, for the outcome of a held-name exclusion.
EXCLUSION_HORIZON_DAYS = 30


def run_and_record(label: str, family: str, **overrides) -> dict:
    assert label not in run_by_label, f"duplicate run label {label!r}"
    VOL_DROP_LOG.clear()
    COMPLEMENT_LOG.clear()
    SLEEVE_LOG.clear()
    PREFILTER_LOG.clear()
    CRASH_LOG.clear()
    QUALITY_LOG.clear()
    CASH_SLEEVE_LOG.clear()
    state_, equity_, returns_ = run_variant(label, **overrides)
    panel_row = panel(label, state_, equity_, returns_, anchor_cycle_returns)
    entry = {
        "label": label, "family": family, "overrides": dict(overrides),
        "state": state_, "equity": equity_, "returns": returns_, "panel": panel_row,
        "cycle_returns": cycle_returns(equity_)[0],
        "vol_drop_log": dict(VOL_DROP_LOG), "complement_log": dict(COMPLEMENT_LOG),
        "sleeve_log": dict(SLEEVE_LOG), "prefilter_log": dict(PREFILTER_LOG),
        "crash_log": dict(CRASH_LOG), "quality_log": dict(QUALITY_LOG), "cash_sleeve_log": dict(CASH_SLEEVE_LOG),
    }
    for name in ("vol_drop_log", "complement_log", "sleeve_log", "prefilter_log", "crash_log", "quality_log", "cash_sleeve_log"):
        keys = list(entry[name])
        assert len(set(keys)) == len(keys), f"{name} has duplicate decision timestamps for {label}"
    runs.append(entry)
    run_by_label[label] = entry
    return entry


def short(address: str) -> str:
    a = str(address).lower()
    return a[:6] + ".." + a[-4:]


def _vault_positions(state_):
    return [p for p in state_.portfolio.get_all_positions() if not p.is_credit_supply()]


def _peak_weight(state_, position_id: int) -> float:
    equity_at = {pd.Timestamp(s.calculated_at): float(s.total_equity) for s in state_.stats.portfolio if s.total_equity}
    best = 0.0
    for s in state_.stats.positions.get(position_id, []):
        total = equity_at.get(pd.Timestamp(s.calculated_at))
        if total and s.value:
            best = max(best, float(s.value) / total)
    return best


def position_ledger(label: str) -> pd.DataFrame:
    """One row per position: address, open/close, days held, P&L, share of the run's net P&L,
    peak weight. Sorted by absolute P&L."""
    state_ = run_by_label[label]["state"]
    end = pd.Timestamp(state_.stats.portfolio[-1].calculated_at) if state_.stats.portfolio else WINDOW_END
    rows = []
    for p in _vault_positions(state_):
        opened = pd.Timestamp(p.opened_at)
        closed = pd.Timestamp(p.closed_at) if p.closed_at else pd.NaT
        rows.append({
            "position": p.position_id, "vault": short(p.pair.pool_address),
            "address": str(p.pair.pool_address).lower(),
            "opened": opened.date(), "closed": closed.date() if closed is not pd.NaT else None,
            "days": int(((closed if closed is not pd.NaT else end) - opened).days),
            "pnl_usd": float(p.get_total_profit_usd() or 0.0), "peak_weight": _peak_weight(state_, p.position_id),
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    net = frame["pnl_usd"].sum()
    frame["pnl_share"] = frame["pnl_usd"] / net if net != 0 else np.nan
    return frame.reindex(frame["pnl_usd"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def ledger_summary(label: str) -> dict:
    frame = position_ledger(label)
    if frame.empty:
        return {"label": label}
    by_vault = frame.groupby("address")["pnl_usd"].sum().sort_values(ascending=False)
    positive = by_vault[by_vault > 0].sum()
    return {"label": label, "positions": int(len(frame)), "distinct_vaults": int(by_vault.size),
            "win_rate": float((frame["pnl_usd"] > 0).mean()), "median_days_held": float(frame["days"].median()),
            "net_pnl_usd": float(frame["pnl_usd"].sum()),
            "top_vault": short(by_vault.index[0]), "top_vault_pnl_share_of_positive": float(by_vault.iloc[0] / positive) if positive > 0 else np.nan,
            "top3_vaults_pnl_share_of_positive": float(by_vault.iloc[:3].sum() / positive) if positive > 0 else np.nan,
            "largest_loss_usd": float(frame["pnl_usd"].min()), "largest_loss_vault": short(frame.loc[frame["pnl_usd"].idxmin(), "address"])}


def drawdown_episodes(label: str, top: int = 3) -> pd.DataFrame:
    """The `top` deepest drawdowns: peak, trough, depth, days peak-to-trough, recovery date."""
    equity_ = run_by_label[label]["equity"]
    high = equity_.cummax()
    dd = equity_ / high - 1.0
    episodes, in_dd, start = [], False, None
    for i, t in enumerate(equity_.index):
        if not in_dd and dd.iloc[i] < 0:
            in_dd, start = True, max(i - 1, 0)
        elif in_dd and dd.iloc[i] >= 0:
            seg = dd.iloc[start:i + 1]
            trough = seg.idxmin()
            episodes.append({"peak": equity_.index[start].date(), "trough": trough.date(), "recovered": t.date(),
                             "depth": float(seg.min()), "days_to_trough": int((trough - equity_.index[start]).days),
                             "days_under_water": int((t - equity_.index[start]).days)})
            in_dd = False
    if in_dd:
        seg = dd.iloc[start:]
        trough = seg.idxmin()
        episodes.append({"peak": equity_.index[start].date(), "trough": trough.date(), "recovered": None,
                         "depth": float(seg.min()), "days_to_trough": int((trough - equity_.index[start]).days),
                         "days_under_water": int((equity_.index[-1] - equity_.index[start]).days)})
    frame = pd.DataFrame(episodes)
    if frame.empty:
        return frame
    return frame.sort_values("depth").head(top).reset_index(drop=True)


def pnl_change_by_position(label: str, start, end) -> pd.DataFrame:
    """Change in each position's cumulative P&L between `start` (exclusive) and `end`
    (inclusive), from the per-cycle position statistics. A position opened inside the interval
    starts from zero."""
    state_ = run_by_label[label]["state"]
    peak, trough = pd.Timestamp(start), pd.Timestamp(end)
    rows = []
    for p in _vault_positions(state_):
        series = state_.stats.positions.get(p.position_id, [])
        if not series:
            continue
        s = pd.Series({pd.Timestamp(x.calculated_at): float(x.profit_usd or 0.0) for x in series}).sort_index()
        before = s[s.index <= peak]
        during = s[(s.index > peak) & (s.index <= trough)]
        if during.empty:
            continue
        start_value = float(before.iloc[-1]) if len(before) else 0.0
        rows.append({"vault": short(p.pair.pool_address), "address": str(p.pair.pool_address).lower(), "position": p.position_id,
                     "pnl_change_usd": float(during.iloc[-1] - start_value)})
    return pd.DataFrame(rows)


def episode_attribution(label: str, peak, trough, top: int = 5) -> pd.DataFrame:
    """The `top` positions whose cumulative P&L fell most between the peak and the trough."""
    frame = pnl_change_by_position(label, peak, trough)
    if frame.empty:
        return frame
    return frame.sort_values("pnl_change_usd").head(top).reset_index(drop=True)


def regime_pnl_by_vault(label: str, start, end, top: int = 5) -> pd.DataFrame:
    """P&L change per vault (address-aggregated) inside [start, end], the `top` winners and losers."""
    frame = pnl_change_by_position(label, pd.Timestamp(start) - pd.Timedelta(days=1), end)
    if frame.empty:
        return frame
    by_vault = frame.groupby("address")["pnl_change_usd"].sum().sort_values()
    picked = pd.concat([by_vault.head(top), by_vault.tail(top)]).drop_duplicates()
    out = pd.DataFrame({"vault": [short(a) for a in picked.index], "pnl_change_usd": picked.to_numpy()})
    out["regime_pnl_total_usd"] = float(by_vault.sum())
    out["regime_vaults"] = int(by_vault.size)
    return out.reset_index(drop=True)


def ledger_with_quality(label: str, top: int = 8) -> pd.DataFrame:
    """The largest positions of a run with the vault's `quality_sharpe` read offline at T-1 of the
    opening decision, so a floor's effect on the run's winners can be read directly."""
    ledger = position_ledger(label).head(top).copy()
    if ledger.empty:
        return ledger
    values = []
    for _, row in ledger.iterrows():
        pair = PAIR_BY_ADDRESS.get(row["address"])
        values.append(value_at_prior(indicator_series("quality_sharpe", pair), pd.Timestamp(row["opened"])) if pair is not None else np.nan)
    ledger["quality_at_open"] = values
    return ledger.drop(columns=["address"])


def worst_cycles(label: str, n: int = 5) -> pd.DataFrame:
    """The `n` worst cycle returns and the position whose cumulative P&L fell most in that cycle."""
    entry = run_by_label[label]
    rc = entry["cycle_returns"].sort_values().head(n)
    state_ = entry["state"]
    per_position = {}
    for p in _vault_positions(state_):
        series = state_.stats.positions.get(p.position_id, [])
        if series:
            per_position[p] = pd.Series({pd.Timestamp(x.calculated_at): float(x.profit_usd or 0.0) for x in series}).sort_index()
    rows = []
    for t, r in rc.items():
        worst_vault, worst_change, movers = None, 0.0, 0
        for p, s in per_position.items():
            before = s[s.index < t]
            at = s[s.index <= t]
            if at.empty or before.empty:
                continue
            change = float(at.iloc[-1] - before.iloc[-1])
            if change < 0:
                movers += 1
            if change < worst_change:
                worst_change, worst_vault = change, short(p.pair.pool_address)
        rows.append({"cycle_end": t.date(), "cycle_return": float(r), "worst_vault": worst_vault,
                     "worst_vault_pnl_change_usd": worst_change, "positions_down": movers})
    return pd.DataFrame(rows)


def _pair_by_address() -> dict:
    out = {}
    for pair in strategy_universe.iterate_pairs():
        out[str(pair.pool_address).lower()] = pair
    return out


PAIR_BY_ADDRESS = _pair_by_address()


def forward_log_return(address: str, timestamp, horizon_days: int = EXCLUSION_HORIZON_DAYS) -> float:
    """Log return of the vault's own mark from the last close at or before T-1 to the last close at
    or before T-1+H. NaN if either end is missing."""
    pair = PAIR_BY_ADDRESS.get(str(address).lower())
    if pair is None:
        return float("nan")
    close = close_series(pair)
    t1 = pd.Timestamp(timestamp) - pd.Timedelta(days=1)
    i0 = close.index.searchsorted(t1, side="right") - 1
    i1 = close.index.searchsorted(t1 + pd.Timedelta(days=horizon_days), side="right") - 1
    if i0 < 0 or i1 <= i0:
        return float("nan")
    return float(np.log(close.iloc[i1] / close.iloc[i0]))


def held_exclusion_outcomes(label: str, horizon_days: int = EXCLUSION_HORIZON_DAYS) -> pd.DataFrame:
    """Every (decision, vault) at which the crash filter removed a HELD name, with the vault's
    own volatility at the decision and its forward log return over `horizon_days`."""
    log = run_by_label[label].get("crash_log") or {}
    rows = []
    for t, rec in sorted(log.items()):
        for addr in rec["excluded_addresses"]:
            if rec["held"].get(addr):
                rows.append({"decision": pd.Timestamp(t), "vault": short(addr), "address": addr,
                             "vol_at_decision": float(rec["vol"].get(addr, np.nan)), "limit": float(rec["limit"].get(addr, np.nan)),
                             "forward_log_return": forward_log_return(addr, t, horizon_days)})
    return pd.DataFrame(rows, columns=["decision", "vault", "address", "vol_at_decision", "limit", "forward_log_return"])


def exclusion_outcome_summary(label: str, horizon_days: int = EXCLUSION_HORIZON_DAYS) -> dict:
    frame = held_exclusion_outcomes(label, horizon_days)
    if frame.empty:
        return {"label": label, "held_exclusions": 0}
    f = frame["forward_log_return"]
    return {"label": label, "held_exclusions": int(len(frame)), "distinct_vaults": int(frame["address"].nunique()),
            "measured": int(f.notna().sum()), "mean_forward_log_return": float(f.mean()), "median_forward_log_return": float(f.median()),
            "share_negative": float((f < 0).mean()), "share_crash": float((f < CRASH_LOG_RETURN).mean()),
            "share_gain_over_10pct": float((f > 0.1).mean())}


def held_addresses_by_date(entry: dict) -> dict:
    return {t: {str(p.pool_address).lower(): share for p, share in holdings} for t, holdings in _position_weights(entry["state"]).items()}


def band_attribution(wide_label: str, tight_label: str, reference_label: str = "anchor") -> dict:
    """Names the wide run held on dates when the tight run's filter excluded them, and what those
    names earned for the wide run and for the reference."""
    wide, tight = run_by_label[wide_label], run_by_label[tight_label]
    held = held_addresses_by_date(wide)
    band = set()
    for t, rec in (tight.get("crash_log") or {}).items():
        excluded = set(rec["excluded_addresses"])
        band |= excluded & set(held.get(pd.Timestamp(t), {}))
    out = {"wide": wide_label, "tight": tight_label, "band_vaults": len(band), "band_addresses": sorted(band)}
    for name, label in (("wide", wide_label), ("reference", reference_label)):
        ledger = position_ledger(label)
        if ledger.empty:
            continue
        net = ledger["pnl_usd"].sum()
        in_band = ledger[ledger["address"].isin(band)]
        out[f"{name}_band_pnl_usd"] = float(in_band["pnl_usd"].sum())
        out[f"{name}_band_pnl_share_of_net"] = float(in_band["pnl_usd"].sum() / net) if net else np.nan
        out[f"{name}_band_positions"] = int(len(in_band))
    return out


def sparse_capital_share(label: str, fresh_rows: int = SPARSE_FRESH_ROWS) -> dict:
    """Capital-weighted moved-mark count (trailing 90 rows, T-1) of the held book, and the share
    of capital in names below `fresh_rows`, averaged over decisions; also by regime."""
    entry = run_by_label[label]
    weights = _position_weights(entry["state"])
    rows = []
    for t in sorted(weights):
        total = sum(share for _p, share in weights[t])
        if total <= 0:
            continue
        fresh_w, sparse_w, covered = 0.0, 0.0, 0.0
        for pair, share in weights[t]:
            fresh = value_at_prior(indicator_series("fresh_observation_count", pair), t)
            if np.isfinite(fresh):
                fresh_w += share * fresh
                covered += share
                if fresh < fresh_rows:
                    sparse_w += share
        if covered > 0:
            rows.append({"date": t, "weighted_fresh": fresh_w / covered, "sparse_share": sparse_w / total,
                         "regime": "sparse" if t < REGIME_BREAK else ("dense" if t < LATE_START else "late")})
    frame = pd.DataFrame(rows)
    out = {"label": label, "decisions": int(len(frame))}
    if frame.empty:
        return out
    out["weighted_fresh_marks_90"] = float(frame["weighted_fresh"].mean())
    out["sparse_capital_share"] = float(frame["sparse_share"].mean())
    for regime, g in frame.groupby("regime"):
        out[f"sparse_share_{regime}"] = float(g["sparse_share"].mean())
    return out


def book_overlap(label: str, reference_label: str = "anchor") -> dict:
    """Per-decision overlap with the reference book, averaged: Jaccard of the held sets and the
    share of the run's capital in names the reference also held."""
    mine = held_addresses_by_date(run_by_label[label])
    theirs = held_addresses_by_date(run_by_label[reference_label])
    jaccard, shared_capital = [], []
    for t in sorted(set(mine) & set(theirs)):
        a, b = set(mine[t]), set(theirs[t])
        if not a and not b:
            continue
        jaccard.append(len(a & b) / len(a | b))
        total = sum(mine[t].values())
        shared_capital.append(sum(v for k, v in mine[t].items() if k in b) / total if total > 0 else np.nan)
    return {"label": label, "decisions": len(jaccard), "mean_jaccard_vs_reference": float(np.mean(jaccard)) if jaccard else np.nan,
            "capital_share_in_reference_names": float(np.nanmean(shared_capital)) if shared_capital else np.nan}


def risk_row(label: str, anchor_label: str = "anchor") -> dict:
    entry = run_by_label[label]
    row = entry["panel"]
    equity_ = entry["equity"]
    rc = entry["cycle_returns"]
    dd = equity_ / equity_.cummax() - 1.0
    under = dd < 0
    longest, run = 0, 0
    for flag, t0, t1 in zip(under.to_numpy(), equity_.index, equity_.index[1:].append(equity_.index[-1:])):
        run = run + (t1 - t0).days if flag else 0
        longest = max(longest, run)
    g3 = gate_3_v3(label, anchor_label)   # for the anchor itself own == reference, so its own value
    measures = diversification_cached(entry)
    worst = rc.sort_values()
    return {"label": label, "cagr": float(row["cagr"]), "cycle_sharpe": float(row["cycle_sharpe"]), "cycle_vol": float(row["cycle_vol"]),
            "max_dd": float(row["max_dd"]), "ulcer": float(row["ulcer"]), "worst_cycle": float(worst.iloc[0]),
            "worst5_cycles_sum": float(worst.iloc[:5].sum()), "share_of_cycles_under_water": float(under.mean()),
            "longest_under_water_days": int(longest), "kurtosis": float(rc.kurt()),
            "held_vol_post": float(g3["held_vol_post"]), "mean_largest_weight": float(measures["mean_largest_weight"]),
            "mean_holdings": float(measures["mean_holdings"]), "top_vault_pnl_share": float(measures["top_vault_pnl_share"]),
            "luck_ratio": float(row["luck_ratio"]), "top5_gross_share": float(row["top5_gross_share"]),
            "mean_invested": float(row["mean_invested"])}


def quality_stats(entry: dict) -> dict:
    log = entry.get("quality_log") or {}
    if not log:
        return {"quality_decisions": 0, "qualifying_mean": np.nan, "qualifying_min": np.nan, "qualifying_max": np.nan,
                "quality_measured_share": np.nan, "quality_held_removed_total": 0, "decisions_none_qualifying": 0}
    q = np.array([r["qualifying"] for r in log.values()], dtype=float)
    pools = np.array([r["pool_size"] for r in log.values()], dtype=float)
    measured = np.array([r["measured_count"] for r in log.values()], dtype=float)
    return {"quality_decisions": len(log), "qualifying_mean": float(q.mean()), "qualifying_min": int(q.min()), "qualifying_max": int(q.max()),
            "quality_measured_share": float((measured / np.maximum(pools, 1)).mean()),
            "quality_held_removed_total": int(sum(r["held_removed"] for r in log.values())),
            "decisions_none_qualifying": int((q == 0).sum())}


def sleeve_stats(entry: dict) -> dict:
    log = entry.get("cash_sleeve_log") or {}
    if not log:
        return {"sleeve_decisions": 0, "sleeve_active_share": np.nan, "sleeve_mean_fill": np.nan, "sleeve_min_fill": np.nan}
    fill = np.array([r["fill"] for r in log.values()], dtype=float)
    return {"sleeve_decisions": len(log), "sleeve_active_share": float((fill < 1.0).mean()),
            "sleeve_mean_fill": float(fill.mean()), "sleeve_min_fill": float(fill.min())}


def summary_row_40(label: str, anchor_label: str = "anchor") -> dict:
    out = summary_row(label, anchor_label)
    out.update(quality_stats(run_by_label[label]))
    out.update(sleeve_stats(run_by_label[label]))
    return out


print(f"harness_forensics.py: QUALITY_LOG / CASH_SLEEVE_LOG lifecycle, position ledger, drawdown episodes, "
      f"held-exclusion outcomes ({EXCLUSION_HORIZON_DAYS} d), band attribution, sparse-capital share (< {SPARSE_FRESH_ROWS} moved marks), "
      f"risk rows; {len(PAIR_BY_ADDRESS)} pairs indexed by address.")
