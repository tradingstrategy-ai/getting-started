"""harness_crash_exit.py - NB42 (plan 42, Draft 5): the fill predicate, the two-clock Sharpe, the
fire counts, the first-strike table and the raw-archive path helpers.

Loaded after harness_trades.py. Redefines `run_and_record()` once more so `CLUSTER_LOG` is
cleared and snapshotted, and adds:

- `candle_row(pair, date)`: the open/close of that UTC date's row in the backtest candle
  universe - the reference for the fill predicate, never a `get_price_with_tolerance()` call.
- `fill_record(label, address, date)`: the sell trade of that vault executed on that decision
  date, with the pair's async flags, decision timestamp, `executed_at`, `planned_mid_price`,
  `executed_price`, the stored fee and `market_feed_delay`.
- `classify_fill(record, collapse_date)`: CATCH / PARTIAL / MISS / UNCLASSIFIED in the plan's
  fixed order on the valuation price; the settlement mid if any async flag is true.
- `crash_leg(pair, collapse_date)`: H0b - previous close, open, close and the two legs.
- `sharpe_on_2d_grid(label)`: a run's equity reindexed onto the two-day anchor's timestamps.
- `churn_pnl(label)`: P&L of the positions the ranking closed (exit class "outranked").
- `gate_fire_count(lo, hi)`: held-vault T-1 `return_gate` in (lo, hi] per decision, with the
  vault's 5- and 30-day forward return; `breaker_fire_count(threshold)` the same for the last
  daily log return.
- `first_strike_table()`: first-entry rows per vault per class on UTC days, and the every-day
  appendix.
- `archive_daily()` / `archive_4h()`: last mark per bucket from the raw archive, for the path
  and coverage cells.
- `date_window_cycles(labels, dates)`: cycle return and USD P&L of the cycles ending on the
  named dates, per run.
"""

ARCHIVE = Path.home() / ".cache/tradingstrategy/vaults/downloads/vault-prices.parquet"
COLLAPSE_DATES = {"august": pd.Timestamp("2026-08-21"), "may": pd.Timestamp("2026-05-21")}
WARNING_DATES = {"august": pd.Timestamp("2026-08-19"), "may": pd.Timestamp("2026-05-20")}
REL_TOL = 1e-9
FIRST_STRIKE = -0.10
FIRST_EXTREME = -0.20


def run_and_record(label: str, family: str, **overrides) -> dict:
    assert label not in run_by_label, f"duplicate run label {label!r}"
    for log in (VOL_DROP_LOG, COMPLEMENT_LOG, SLEEVE_LOG, PREFILTER_LOG, CRASH_LOG, QUALITY_LOG, CASH_SLEEVE_LOG, CLUSTER_LOG):
        log.clear()
    state_, equity_, returns_ = run_variant(label, **overrides)
    panel_row = panel(label, state_, equity_, returns_, anchor_cycle_returns)
    entry = {
        "label": label, "family": family, "overrides": dict(overrides),
        "state": state_, "equity": equity_, "returns": returns_, "panel": panel_row,
        "cycle_returns": cycle_returns(equity_)[0],
        "vol_drop_log": dict(VOL_DROP_LOG), "complement_log": dict(COMPLEMENT_LOG),
        "sleeve_log": dict(SLEEVE_LOG), "prefilter_log": dict(PREFILTER_LOG),
        "crash_log": dict(CRASH_LOG), "quality_log": dict(QUALITY_LOG), "cash_sleeve_log": dict(CASH_SLEEVE_LOG),
        "cluster_log": dict(CLUSTER_LOG),
    }
    runs.append(entry)
    run_by_label[label] = entry
    return entry


# --------------------------------------------------------------------------------------------
# The fill predicate (Part 0b).
# --------------------------------------------------------------------------------------------

_CANDLES = strategy_universe.data_universe.candles.df


def candle_row(pair, date) -> dict:
    """Open and close of the UTC date's row in the backtest candle universe."""
    date = pd.Timestamp(date).normalize()
    key = ("__candles__", pair.internal_id)
    if key not in _SERIES_CACHE:
        try:
            _SERIES_CACHE[key] = _CANDLES.xs(pair.internal_id, level="pair_id")[["open", "close"]].sort_index()
        except KeyError:
            _SERIES_CACHE[key] = None
    frame = _SERIES_CACHE[key]
    if frame is None or date not in frame.index:
        return {"open": float("nan"), "close": float("nan"), "present": False}
    hit = frame.loc[date]
    return {"open": float(hit["open"]), "close": float(hit["close"]), "present": True}


def async_flags(pair) -> dict:
    return {"vault_features": sorted(str(f) for f in (pair.get_vault_features() or set())),
            "is_async_vault": bool(pair.is_async_vault()),
            "has_delayed_vault_redemption": bool(pair.has_delayed_vault_redemption()),
            "settlement_override": False}   # run_variant passes no vault_settlement_delay_overrides


def fill_record(label: str, address: str, date) -> dict | None:
    """The sell trade of `address` in run `label` executed on `date` (UTC day)."""
    date = pd.Timestamp(date).normalize()
    state_ = run_by_label[label]["state"]
    for p in _vault_positions(state_):
        if str(p.pair.pool_address).lower() != str(address).lower():
            continue
        for t in p.get_successful_trades():
            if not t.is_sell():
                continue
            if pd.Timestamp(t.executed_at).normalize() != date:
                continue
            pricing = getattr(t, "price_structure", None)
            delay = getattr(pricing, "market_feed_delay", None) if pricing is not None else None
            decision = pd.Timestamp(t.opened_at or t.started_at)
            dec_row = candle_row(p.pair, decision)
            fee = float((t.other_data or {}).get("backtest_vault_redemption_fee", float("nan")))
            return {"label": label, "vault": vault_name(address), "address": str(address).lower(), "position": p.position_id,
                    "decision": decision, "executed_at": pd.Timestamp(t.executed_at),
                    "planned_mid_price": float(t.planned_mid_price) if t.planned_mid_price is not None else float("nan"),
                    "planned_price": float(t.planned_price), "executed_price": float(t.executed_price) if t.executed_price is not None else float("nan"),
                    "stored_fee": fee, "market_feed_delay": str(delay) if delay is not None else None,
                    "decision_bar_open": dec_row["open"], "decision_bar_close": dec_row["close"], "decision_bar_present": dec_row["present"],
                    "hold_days": int((pd.Timestamp(t.executed_at) - pd.Timestamp(p.opened_at)).days), **async_flags(p.pair)}
    return None


def classify_fill(record: dict, pair, collapse_date) -> dict:
    """The plan's 4-way predicate, in its fixed order, on the valuation price."""
    collapse_date = pd.Timestamp(collapse_date).normalize()
    col = candle_row(pair, collapse_date)
    flags = [record["is_async_vault"], record["has_delayed_vault_redemption"], record["settlement_override"]]
    out = {"collapse_bar_open": col["open"], "collapse_bar_close": col["close"]}
    if any(flags) and not all(flags[:2]):
        out.update({"valuation_price": float("nan"), "price_kind": "async flags disagree", "label": "UNCLASSIFIED"})
        return out
    if any(flags):
        mid = record["executed_price"] / (1.0 - record["stored_fee"]) if np.isfinite(record["stored_fee"]) else float("nan")
        bar = candle_row(pair, record["executed_at"])
        bar_date = pd.Timestamp(record["executed_at"]).normalize()
        kind = "settlement mid at executed_at"
    else:
        mid = record["planned_mid_price"]
        bar = {"open": record["decision_bar_open"], "close": record["decision_bar_close"]}
        bar_date = pd.Timestamp(record["decision"]).normalize()
        kind = "planned_mid_price at the decision"
    out.update({"valuation_price": mid, "price_kind": kind, "bar_date": bar_date, "bar_open": bar["open"], "bar_close": bar["close"]})
    if not np.isfinite(mid) or not np.isfinite(bar["open"]) or not np.isfinite(col["close"]):
        out["label"] = "UNCLASSIFIED"
        return out
    if abs(mid - bar["open"]) <= REL_TOL * bar["open"]:
        out["label"] = "CATCH" if bar_date < collapse_date else ("PARTIAL CATCH" if bar_date == collapse_date else "MISS")
    elif mid <= col["close"] * (1.0 + REL_TOL) or bar_date > collapse_date:
        out["label"] = "MISS"
    else:
        out["label"] = "UNCLASSIFIED"
    return out


def crash_leg(pair, collapse_date) -> dict:
    """H0b: previous close, open, close of the collapse day and the two legs."""
    collapse_date = pd.Timestamp(collapse_date).normalize()
    prev = candle_row(pair, collapse_date - pd.Timedelta(days=1))
    col = candle_row(pair, collapse_date)
    c2o = float(np.log(col["open"] / prev["close"])) if prev["present"] and col["present"] else float("nan")
    o2c = float(np.log(col["close"] / col["open"])) if col["present"] else float("nan")
    return {"previous_close": prev["close"], "open": col["open"], "close": col["close"],
            "close_to_open": c2o, "open_to_close": o2c,
            "crash_leg": ("open_to_close" if o2c < c2o else "close_to_open") if np.isfinite(c2o) and np.isfinite(o2c) else "unknown"}


# --------------------------------------------------------------------------------------------
# Two clocks, churn, fire counts.
# --------------------------------------------------------------------------------------------

def sharpe_on_2d_grid(label: str, reference: str = "anchor") -> dict:
    eq = run_by_label[label]["equity"]
    grid = run_by_label[reference]["equity"].index
    on_grid = eq.reindex(grid)
    missing = int(on_grid.isna().sum())
    assert missing == 0, f"{label}: {missing} anchor timestamps missing from the equity curve"
    rc, ppy = cycle_returns(on_grid)
    return {"label": label, "cycle_sharpe_on_2d_grid": float(calculate_sharpe(rc, periods=ppy)),
            "cycle_vol_on_2d_grid": float(rc.std() * np.sqrt(ppy)), "periods_per_year": float(ppy), "cycles": int(len(rc))}


def churn_pnl(label: str) -> dict:
    ledger = trade_ledger(label)
    cls = ledger["exit_reason"].map(lambda t: "outranked" if isinstance(t, str) and t.startswith("outranked") else "other")
    churn = ledger[cls == "outranked"]
    return {"label": label, "churn_positions": int(len(churn)), "churn_pnl_usd": float(churn["pnl_usd"].sum()),
            "churn_median_days": float(churn["days"].median()) if len(churn) else float("nan"), "positions": int(len(ledger))}


def _forward_log_return(pair, t, days: int) -> float:
    close = close_series(pair)
    i0 = close.index.searchsorted(pd.Timestamp(t) - pd.Timedelta(days=1), side="right") - 1
    i1 = close.index.searchsorted(pd.Timestamp(t) - pd.Timedelta(days=1) + pd.Timedelta(days=days), side="right") - 1
    if i0 < 0 or i1 <= i0:
        return float("nan")
    return float(np.log(close.iloc[i1] / close.iloc[i0]))


def gate_fire_count(label: str, lo: float, hi: float) -> pd.DataFrame:
    """Held vaults whose T-1 `return_gate` lies in (lo, hi] at each decision of `label`."""
    rows = []
    for t, holdings in sorted(_position_weights(run_by_label[label]["state"]).items()):
        for pair, share in holdings:
            g = value_at_prior(indicator_series("return_gate", pair), t)
            if np.isfinite(g) and lo < g <= hi:
                rows.append({"decision": t.date(), "vault": vault_name(str(pair.pool_address)), "weight": share, "return_14d": g,
                             "fwd_5d": _forward_log_return(pair, t, 5), "fwd_30d": _forward_log_return(pair, t, 30)})
    return pd.DataFrame(rows, columns=["decision", "vault", "weight", "return_14d", "fwd_5d", "fwd_30d"])


def breaker_fire_count(label: str, threshold: float) -> pd.DataFrame:
    rows = []
    for t, holdings in sorted(_position_weights(run_by_label[label]["state"]).items()):
        for pair, share in holdings:
            close = close_series(pair)
            i = close.index.searchsorted(pd.Timestamp(t), side="left") - 1
            if i < 1:
                continue
            r = float(np.log(close.iloc[i] / close.iloc[i - 1]))
            if r <= threshold:
                rows.append({"decision": t.date(), "vault": vault_name(str(pair.pool_address)), "weight": share, "last_daily_log_return": r,
                             "fwd_5d": _forward_log_return(pair, t, 5)})
    return pd.DataFrame(rows, columns=["decision", "vault", "weight", "last_daily_log_return", "fwd_5d"])


# --------------------------------------------------------------------------------------------
# The first-strike table (Part 0a step 4).
# --------------------------------------------------------------------------------------------

def first_strike_table(pool_label: str, start=None, end=None) -> tuple:
    """Every UTC day, every candidate in the pool log's union of candidates, classified at T
    reading T-1: first_extreme (last day <= -20%), first_single (exactly one day <= -10% in the
    trailing 3, that day the last one, not extreme), neither. Returns (first-entry rows, every-day rows)."""
    log = run_by_label[pool_label]["crash_log"]
    candidates = sorted({a for rec in log.values() for a in rec["candidate_addresses"]})
    start = pd.Timestamp(start) if start is not None else WINDOW_START
    end = pd.Timestamp(end) if end is not None else WINDOW_END
    days = pd.date_range(start, end, freq="D")
    every, first = [], []
    for addr in candidates:
        pair = PAIR_BY_ADDRESS.get(addr)
        if pair is None:
            continue
        close = close_series(pair)
        r = np.log(close).diff()
        seen = set()
        for t in days:
            # T-1 window: the last three daily returns strictly before t
            i = r.index.searchsorted(t, side="left")
            w = r.iloc[max(0, i - 3):i].dropna()
            if len(w) < 3:
                continue
            last = float(w.iloc[-1])
            strikes = int((w <= FIRST_STRIKE).sum())
            if last <= FIRST_EXTREME:
                cls = "first_extreme"
            elif strikes == 1 and last <= FIRST_STRIKE:
                cls = "first_single"
            else:
                cls = "neither"
            row = {"date": t, "address": addr, "vault": vault_name(addr), "class": cls, "last_return": last,
                   "fwd_1d": _forward_log_return(pair, t, 1), "fwd_2d": _forward_log_return(pair, t, 2)}
            every.append(row)
            if cls != "neither" and cls not in seen:
                seen.add(cls)
                first.append(row)
    return pd.DataFrame(first), pd.DataFrame(every)


def block_bootstrap_mean(values: pd.Series, dates: pd.Series, block_days: int = 30, draws: int = 500, seed: int = 20260919) -> tuple:
    v = values.to_numpy(dtype=float)
    d = pd.to_datetime(dates).to_numpy()
    ok = np.isfinite(v)
    v, d = v[ok], d[ok]
    if len(v) < 5:
        return float("nan"), float("nan"), float("nan")
    blocks = ((d - d.min()) / np.timedelta64(block_days, "D")).astype(int)
    uniq = np.unique(blocks)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        chosen = rng.choice(uniq, size=len(uniq), replace=True)
        sample = np.concatenate([v[blocks == b] for b in chosen])
        means.append(sample.mean())
    return float(v.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# --------------------------------------------------------------------------------------------
# Raw-archive path helpers (Part 0a).
# --------------------------------------------------------------------------------------------

_ARCHIVE_CACHE: dict = {}


def _archive():
    if "df" not in _ARCHIVE_CACHE:
        df = pd.read_parquet(ARCHIVE, columns=["address", "share_price", "total_assets"]).reset_index()
        df["address"] = df["address"].str.lower()
        _ARCHIVE_CACHE["df"] = df[df["share_price"] > 0].sort_values("timestamp")
    return _ARCHIVE_CACHE["df"]


def archive_daily(address: str, start, end) -> pd.DataFrame:
    g = _archive()
    g = g[(g["address"] == str(address).lower()) & (g["timestamp"] >= pd.Timestamp(start)) & (g["timestamp"] <= pd.Timestamp(end))]
    daily = g.set_index("timestamp").resample("1D").agg(open=("share_price", "first"), close=("share_price", "last"),
                                                        low=("share_price", "min"), high=("share_price", "max"),
                                                        marks=("share_price", "size"), tvl_close=("total_assets", "last"))
    daily["log_return"] = np.log(daily["close"] / daily["close"].shift(1))
    return daily


def archive_4h(address: str, start, end) -> pd.DataFrame:
    g = _archive()
    g = g[(g["address"] == str(address).lower()) & (g["timestamp"] >= pd.Timestamp(start)) & (g["timestamp"] <= pd.Timestamp(end))]
    b = g.set_index("timestamp").resample("4h").agg(marks=("share_price", "size"), first=("share_price", "first"), last=("share_price", "last"))
    b["log_return"] = np.log(b["last"] / b["last"].shift(1))
    return b


def bucket_coverage(address: str, start, end, freq: str = "4h") -> dict:
    g = _archive()
    g = g[(g["address"] == str(address).lower()) & (g["timestamp"] >= pd.Timestamp(start)) & (g["timestamp"] <= pd.Timestamp(end))]
    if g.empty:
        return {"buckets": 0, "empty_share": float("nan"), "marks_per_bucket": float("nan")}
    counts = g.set_index("timestamp").resample(freq)["share_price"].size()
    return {"buckets": int(len(counts)), "empty_share": float((counts == 0).mean()), "marks_per_bucket": float(counts.mean())}


def date_window_cycles(labels: list, cycle_end_dates: list) -> pd.DataFrame:
    """Cycle return and USD P&L of the cycles ENDING on the given dates, per run."""
    rows = []
    for label in labels:
        eq = run_by_label[label]["equity"]
        rc = run_by_label[label]["cycle_returns"]
        for d in cycle_end_dates:
            d = pd.Timestamp(d)
            i = eq.index.searchsorted(d, side="right") - 1
            if i < 1:
                continue
            end_ts = eq.index[i]
            rows.append({"label": label, "cycle_end": end_ts.date(), "cycle_start": eq.index[i - 1].date(),
                         "cycle_return": float(rc.get(end_ts, np.nan)), "pnl_usd": float(eq.iloc[i] - eq.iloc[i - 1])})
    return pd.DataFrame(rows)


print(f"harness_crash_exit.py: collapse dates {[str(v.date()) for v in COLLAPSE_DATES.values()]}, warning dates "
      f"{[str(v.date()) for v in WARNING_DATES.values()]}, predicate tolerance {REL_TOL}, archive {ARCHIVE.name}.")
