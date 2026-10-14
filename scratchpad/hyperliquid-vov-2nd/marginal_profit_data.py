"""Frozen inputs, control economics and causal opportunity rows for NB21."""

import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm_loggable.auto import tqdm
import clean_c00_v11_comparison as baseline
from k_ratio_features import k_statistics, sha256
from portfolio_snapshot_risk import empirical_window, forecast, peer_prior

ROOT = baseline.ROOT
PERIODS = baseline.PERIODS
LABELS = baseline.LABELS
HORIZONS = (2, 7, 30)
PERFORMANCE = ("log_return_360", "sortino_45", "return_14", "drawdown_30", "k_max")
SUPPORT = ("risk_90", "updates_30", "quote_age", "recorded_age", "k_history", "can_deposit", "permission_unknown", "deposit_headroom", "log_tvl")
REGISTRY = dict(version="nb21-v1", horizons=HORIZONS, policy_horizon=30, initial_cash=150000, missing=True, penalties=[0.1, 1.0, 10.0], support_blocks=6, support_vaults=30, sign_blocks=3, component_draws=101, account_cap=0.33, tvl_cap=0.33, tvl_floor=7500.0, performance_fee=0.10, capital_fee=0.001, action_margin=0.0, refinements=12, objective_tolerance_usd=1.0, target_tolerance_usd=10.0, seed=2121)
ARMS = {"B00": "Exact C00", "B01": "Exact v11", "F01": "C00: 1% sell band", "P00": "Support prior / adaptive portfolio", "D00": "Conditional downside / adaptive portfolio", "M00": "Conditional magnitudes / adaptive portfolio", "C01": "Calibrated C00 score / adaptive portfolio", "D02": "Downside / maximum six", "D03": "Downside / entry only", "D04": "Downside / no loss budget"}


def initialise():
    """Require the original NB20 identity before creating a separate generation."""
    data, evaluator = baseline.initialise()
    nb = json.loads((ROOT / "20-backtest-c00-vs-v11.ipynb").read_text())
    reference = Path(nb["metadata"]["nb20"]["artifact_generation"])
    expected = json.loads((reference / "manifest.json").read_text())["identity"]
    assert json.loads(json.dumps(data["manifest"]["identity"], default=str)) == expected, "NB20 identity changed"
    files = sorted(ROOT.glob("marginal_profit_*.py")) + [ROOT / "create_marginal_profit_notebook.py"]
    identity = dict(version=REGISTRY["version"], parent=expected, code={p.name: sha256(p) for p in files if p.exists()}, registry=dict(REGISTRY), arms=dict(ARMS))
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/21" / key
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=key, nb20_reference=reference, figures=[], nb21_candidates=[], nb21_decisions=[], nb21_checks=[], nb21_states=[])
    economics = {n: d for n, d in identity["code"].items() if n not in ("marginal_profit_report.py", "create_marginal_profit_notebook.py")}
    econkey = hashlib.sha256(json.dumps(dict(parent=expected, code=economics, registry=REGISTRY), sort_keys=True).encode()).hexdigest()
    cache_root = ROOT / "_artifacts-restored-2026-10-07/21/cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    evaluator.folder = cache_root / econkey / "engine"
    evaluator.folder.mkdir(parents=True, exist_ok=True)
    inputkey = hashlib.sha256((sha256(Path(__file__)) + json.dumps(expected, sort_keys=True)).encode()).hexdigest()
    data["feature_artifact"] = cache_root / inputkey
    data["feature_artifact"].mkdir(exist_ok=True)
    data["manifest_engine"] = str(evaluator.folder)
    data["manifest"] = dict(identity=identity, fingerprint=key, framework=data["framework_commits"], periods={p: list(map(str, v)) for p, v in PERIODS.items()}, status="registered", limitations=["Researched overlapping calendars", "Retrospective inventory and guard", "Inherited unverified fee model", "Recorded NAV is not certified executable NAV"])
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data, evaluator


def metrics(data, r, arm, period):
    if any(pos.pair.is_vault() for pos in r["result"].state.portfolio.get_all_positions()):
        m, v, w = baseline.core.engine.analyse_run(data, r, arm, period)
    else:
        eq = r["equity"].resample("D").last().ffill()
        reserve = r["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        w = pd.DataFrame({reserve: 1.0}, index=eq.index)
        v = pd.Series(dtype=float)
        m = {**r["metrics"], "Net profit (USD)": float(eq.iloc[-1] - 150000), "Mean cash weight": 1.0, "Mean largest vault weight": 0.0, "Largest vault weight": 0.0, "PnL residual (USD)": 0.0}
        pd.DataFrame(index=eq.index).to_parquet(data["artifact"] / f"{period}-{arm}-position-curves.parquet")
        pd.DataFrame(columns=["Position id", "Vault", "Address", "Opened", "Closed", "Final profit (USD)"]).to_parquet(data["artifact"] / f"{period}-{arm}-positions.parquet")
        w.to_parquet(data["artifact"] / f"{period}-{arm}-absolute-weights.parquet")
        eq.to_csv(data["artifact"] / f"{period}-{arm}-equity.csv")
    m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
    m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"]) if m["Maximum drawdown"] < 0 else np.nan
    reserve = r["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
    m["September cash"] = float(w.loc["2026-09-01":"2026-09-30", reserve].mean())
    held = w.drop(columns=reserve)
    m["Mean vaults held"] = float(held.gt(1e-8).sum(axis=1).mean())
    m["Mean effective breadth"] = float((held.sum(axis=1) ** 2 / held.pow(2).sum(axis=1).replace(0, np.nan)).mean())
    return dict(Period=period, Arm=arm, Method=ARMS.get(arm, arm), **m), v, w


def controls(data, evaluator):
    """Read full engine states, then compare daily equity and every trade."""
    expected = pd.read_csv(data["nb20_reference"] / "results.csv").set_index(["Period", "Arm"])
    records = []
    runs = {}
    attrs = {}
    weights = {}
    parity = []
    folder = evaluator.folder
    for period in PERIODS:
        for old, arm in (("C00", "B00"), ("V11", "B01")):
            print(f"Control parity {period} / {arm}; approximately 1–3 minutes remaining", flush=True)
            evaluator.folder = data["nb20_reference"] / "engine"
            try:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    r = baseline.v11_replay(data, evaluator, period) if old == "V11" else baseline.core.replay(data, evaluator, "C00", period, active=False)
            finally:
                evaluator.folder = folder
            row, v, w = metrics(data, r, arm, period)
            saved = pd.read_csv(data["nb20_reference"] / f"{period}-{old}-equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
            daily = r["equity"].resample("D").last().ffill()
            assert saved.index.equals(daily.index)
            error = float((saved - daily).abs().max())
            assert error < 1e-6
            for k in ("Final equity (USD)", "CAGR", "Sharpe", "Maximum drawdown"):
                assert abs(row[k] - expected.loc[(period, old), k]) < 1e-6
            trades = baseline.core.trade_signature(r)
            parity.append(dict(Period=period, Arm=arm, Equity_error_usd=error, Trades=len(trades), Trade_sha256=hashlib.sha256(json.dumps(trades).encode()).hexdigest()))
            records.append(row)
            runs[(period, arm)] = r
            attrs[(period, arm)] = v
            weights[(period, arm)] = w
    data.update(control_results=pd.DataFrame(records), control_runs=runs, control_attribution=attrs, control_weights=weights)
    pd.DataFrame(parity).to_csv(data["artifact"] / "control-parity.csv", index=False)
    data["control_results"].to_csv(data["artifact"] / "control-results.csv", index=False)
    from capital_allocation_report import fee_accounting

    data["fee_audit"] = fee_accounting(data, runs)
    rows = []
    for (period, arm), r in runs.items():
        for pos in r["result"].state.portfolio.get_all_positions():
            if not pos.pair.is_vault():
                continue
            opened = pd.Timestamp(pos.opened_at)
            closed = pd.Timestamp(pos.closed_at) if pos.closed_at else pd.Timestamp(r["equity"].index[-1])
            span = max(0.0, (closed - opened).total_seconds() / 86400)
            buy = sum(float(t.executed_reserve or 0) for t in pos.get_successful_trades() if t.is_buy())
            # Dollar-days use actual marked position snapshots, including partial trims.
            snapshots = r["result"].state.stats.positions.get(pos.position_id, [])
            dd = 0.0
            previous = opened
            value = 0.0
            for snap in sorted(snapshots, key=lambda x: x.calculated_at):
                t = pd.Timestamp(snap.calculated_at)
                dd += value * max(0.0, (t - previous).total_seconds() / 86400)
                previous = t
                value = float(snap.value)
            dd += value * max(0.0, (closed - previous).total_seconds() / 86400)
            rows.append(dict(Period=period, Arm=arm, Position=pos.position_id, Vault=pos.pair.get_vault_name(), Days=span, Open=not pos.is_closed(), Buy_usd=buy, Dollar_days=dd, Net_profit=float(pos.get_cash_flow_profit_usd()), Bucket="<7" if span < 7 else "7–30" if span <= 30 else ">30"))
    spells = pd.DataFrame(rows)
    spells.to_parquet(data["artifact"] / "holding-spells.parquet", index=False)
    data["spells"] = spells
    short = spells[spells.Period.eq("2026")]
    total = short.groupby("Arm").agg(Dollar_days=("Dollar_days", "sum"), Abs_profit=("Net_profit", lambda z: z.abs().sum()))
    small = short[short.Days.lt(7)].groupby("Arm").agg(Dollar_days=("Dollar_days", "sum"), Abs_profit=("Net_profit", lambda z: z.abs().sum())).reindex(total.index, fill_value=0)
    shares = small / total
    data["horizon_audit"] = shares
    # Open spells prevent a retrospective short-lifetime conclusion.
    switch = bool((shares > 0.5).all().all() and not short.Open.any())
    data["policy_horizon"] = 7 if switch else 30
    registration = dict(registry=REGISTRY, policy_horizon=data["policy_horizon"], horizon_rule="Both controls must exceed 50% short-spell capital and absolute PnL; censored open spells veto an unsupported amendment", short_shares=shares.to_dict(), cold_start="Pooled after one mature horizon block with both signs; supported after six blocks/30 vaults/three sign blocks", prior_budget_window=["2024-01-01", "2026-01-01"], numerical={"USD objective": 1, "USD L1 targets": 10, "refinements": 12})
    (data["artifact"] / "registration.json").write_text(json.dumps(registration, indent=2, default=str))
    return data["control_results"], spells


def build_panel(data, evaluator):
    """Calculate pre-decision features, actual observation masks and outcome maturity."""
    cache = data["feature_artifact"] / "opportunity-panel.parquet"
    if cache.exists():
        data["panel"] = pd.read_parquet(cache)
        return data["panel"]
    required = set()
    for r in data["control_runs"].values():
        if "Date" in r["allocation_df"]:
            required.update(pd.to_datetime(r["allocation_df"].Date.unique()))
    nav = data["nav"]
    raw = data["raw_nav"]
    observed = data["observed"]
    prices = data["prices"]
    end = max(required) - pd.Timedelta(days=1)
    if end > nav.index[-1]:
        index = pd.date_range(nav.index[0], end)
        raw = raw.reindex(index)
        observed = observed.reindex(index)
        for pid, (times, values) in data["nav_history"].items():
            late = (times >= (data["nav"].index[-1] + pd.Timedelta(days=1)).value) & (times < (end + pd.Timedelta(days=1)).value)
            if not late.any():
                continue
            z = pd.DataFrame({"timestamp": pd.to_datetime(times[late]), "value": values[late]})
            z["date"] = z.timestamp.dt.floor("D")
            z = z.groupby("date", sort=False).tail(1)
            raw.loc[z.date, int(pid)] = z.value.to_numpy()
            observed.loc[z.date, int(pid)] = z.timestamp.to_numpy()
        nav = raw.ffill()
        last_observed = observed.ffill()
        extra = []
        for t in index[index > prices.date.max()]:
            extra.append(pd.DataFrame(dict(date=t, pair_id=nav.columns, close=nav.loc[t].to_numpy(), metric_observed_at=last_observed.loc[t].to_numpy(), supported_daily_mark=raw.loc[t].notna().to_numpy(), metric_forward_filled=(raw.loc[t].isna() & nav.loc[t].notna()).to_numpy())))
        prices = pd.concat([prices, *extra], ignore_index=True)
    actual = raw.notna()
    obs = observed.ffill()
    date_index = {t: i for i, t in enumerate(nav.index)}
    arrays = {"nav": nav.to_numpy(), "actual": actual.to_numpy()}
    archive_end = pd.Timestamp(max(z[0][-1] for z in data["nav_history"].values()))
    dates = nav.index
    ids = nav.columns.to_numpy(int)
    N = len(ids)
    # Availability is separate from carried feature prices.
    first = data["first"].reindex(ids)
    age = np.maximum(0, (dates.to_numpy()[:, None] - first.to_numpy()[None, :]) / np.timedelta64(1, "D"))
    log360 = np.log(nav / nav.shift(360))
    r14 = nav / nav.shift(14) - 1
    ret = nav.pct_change(fill_method=None)
    mean = ret.rolling(45, min_periods=45).mean()
    down = ret.clip(upper=0).pow(2).rolling(45, min_periods=45).mean().pow(0.5)
    sortino = mean.div(down.where(down > 0)) * np.sqrt(365)
    from numpy.lib.stride_tricks import sliding_window_view

    drawdown = np.full(nav.shape, np.nan)
    for j in range(N):
        windows = sliding_window_view(nav.iloc[:, j].to_numpy(), 31)
        valid = np.isfinite(windows).all(axis=1)
        safe = np.where(np.isfinite(windows), windows, 1.0)
        values30 = (safe / np.maximum.accumulate(safe, axis=1) - 1).min(axis=1)
        drawdown[30:, j] = np.where(valid, values30, np.nan)
    dd30 = pd.DataFrame(drawdown, index=dates, columns=ids)
    counts = actual.rolling(30, min_periods=1).sum()
    observed_age = (dates.to_numpy()[:, None] + np.timedelta64(1, "D") - obs.to_numpy(dtype="datetime64[ns]")) / np.timedelta64(1, "D")
    kmax = np.full(nav.shape, np.nan)
    kh = np.zeros(nav.shape)
    print("Expanding K and common risk features; approximately 1–3 minutes", flush=True)
    for j in tqdm(range(N), desc="NB21 expanding K", mininterval=15):
        values = nav.iloc[:, j].to_numpy()
        start = np.flatnonzero(np.isfinite(values))
        if not len(start):
            continue
        s = int(start[0])
        y = np.log(values[s:] / values[s])
        x = np.arange(len(y), dtype=float)
        sy = np.cumsum(y)
        sy2 = np.cumsum(y * y)
        sxy = np.cumsum(x * y)
        n = x + 1
        sxx = n * (n * n - 1) / 12
        xy = sxy - x * 0.5 * sy
        slope = np.divide(xy, sxx, out=np.zeros_like(y), where=sxx > 0)
        sse = np.maximum(0, sy2 - sy * sy / n - slope * slope * sxx)
        se = np.sqrt(np.divide(sse, np.maximum(n - 2, 1) * sxx, out=np.zeros_like(y), where=sxx > 0))
        valid = (n >= 3) & (sse > (np.finfo(float).eps * 32) ** 2 * np.maximum(sy2 - sy * sy / n, 1)) & (se > 0)
        k = np.divide(slope * np.sqrt(365), se * n, out=np.full_like(y, np.nan), where=valid)
        kmax[s:, j] = k
        kh[s:, j] = n - 1
    e = data["eligibility"].copy()
    e = e[e.origin_at >= pd.Timestamp(PERIODS["Long"][0])]
    training_origins = set(pd.to_datetime(e.origin_at.unique()))
    missing = sorted(required - training_origins)
    if missing:
        from score_forecast_data import _eligibility

        anchors = []
        for t in pd.DatetimeIndex(missing) - pd.Timedelta(days=1):
            if t not in nav.index:
                continue
            anchors.append(pd.DataFrame(dict(date=t, pair_id=nav.columns, close=nav.loc[t].to_numpy(), metric_observed_at=obs.loc[t].to_numpy(), supported_daily_mark=raw.loc[t].notna().to_numpy(), metric_forward_filled=(raw.loc[t].isna() & nav.loc[t].notna()).to_numpy())))
        prices = pd.concat([prices, *anchors], ignore_index=True).drop_duplicates(["date", "pair_id"], keep="last")
        extra = _eligibility(evaluator, pd.DatetimeIndex(missing), prices)
        e = pd.concat([e, extra], ignore_index=True).drop_duplicates(["origin_at", "pair_id"])
    e["Training_origin"] = e.origin_at.isin(training_origins)
    e["operational_pool"] = e.source_inclusion & e.current_guard_allows & ~e.blacklisted & ~e.quarantined
    origins = sorted(e.origin_at.unique())
    parts = []
    values = {c: z.to_numpy() for c, z in [("log_return_360", log360), ("sortino_45", sortino), ("return_14", r14), ("drawdown_30", dd30), ("updates_30", counts)]}
    for t in tqdm(origins, desc="NB21 pre-decision rows", mininterval=15):
        t = pd.Timestamp(t)
        a = date_index.get(t - pd.Timedelta(days=1))
        if a is None:
            continue
        f = e[e.origin_at.eq(t) & (e.anchor_supported | e.operational_pool)].copy()
        if not len(f):
            continue
        jj = np.array([data["id_index"][int(i)] for i in f.pair_id], dtype=int)
        for col, z in values.items():
            f[col] = z[a, jj]
        f["k_max"] = kmax[a, jj]
        f["k_history"] = kh[a, jj]
        f["recorded_age"] = age[a, jj]
        f["quote_age"] = observed_age[a, jj]
        f["deposit_headroom"] = pd.to_numeric(f.max_deposit, errors="coerce")
        f["permission_unknown"] = f.permission_time_unknown.astype(float)
        source_i = evaluator.panel.date_index[t]
        f["c00_score"] = data["focal_values"][source_i, [evaluator.panel.pair_index[int(i)] for i in f.pair_id]]
        pool = f[f.operational_pool].pair_id.to_numpy(int)
        rows = []
        for pid in pool:
            j = data["id_index"][int(pid)]
            z = empirical_window(arrays["nav"][max(0, a - 90) : a + 1, j], arrays["actual"][max(0, a - 90) : a + 1, j], 90)
            rows.append(z)
        emp = np.array([r["empirical"] for r in rows])
        full = np.array([r["full"] for r in rows], bool)
        risk = {}
        for j, (pid, v) in enumerate(zip(pool, rows)):
            prior, *_ = peer_prior(emp, full, j)
            risk[int(pid)] = np.sqrt(forecast(v["empirical"], prior, v["m"], "regularised", 30))
        f["risk_90"] = f.pair_id.map(risk)
        tvl = []
        lookup = evaluator.indicators
        lookup.prepare_decision_cycle(0, t)
        for pid in f.pair_id:
            pair = evaluator.universe.get_pair_by_id(int(pid))
            try:
                liq = lookup.get_indicator_value("tvl", pair=pair)
            except (KeyError, AssertionError):
                liq = np.nan
            tvl.append(float(liq) if liq is not None else np.nan)
        # Source inclusion supplies the TVL rule even where its indicator name differs.
        f["log_tvl"] = np.log1p(np.maximum(tvl, 0))
        f["Date"] = t
        f["Pair"] = f.pair_id.astype(int)
        f["Vault"] = f.vault_name
        f["feature_cutoff"] = t - pd.Timedelta(days=1)
        for h in HORIZONS:
            part = f.copy()
            part["H"] = h
            ys = []
            marks = []
            maturity = []
            supported = []
            end_age = []
            for pid in part.Pair:
                times, prices = data["nav_history"][int(pid)]
                i = np.searchsorted(times, t.value, side="right") - 1
                end = t + pd.Timedelta(days=h)
                j = np.searchsorted(times, end.value, side="right") - 1
                y = prices[j] / prices[i] - 1 if i >= 0 and j >= i else np.nan
                endpoint_age = (end.value - times[j]) / 86400e9 if j >= 0 else np.nan
                ok = end <= archive_end and i >= 0 and j >= i and endpoint_age <= 1 and np.isfinite(y)
                support = np.searchsorted(times, end.value, side="left")
                carried_ok = i >= 0 and j >= i and support < len(times)
                mat = max(end, pd.Timestamp(times[j])) if ok else pd.NaT
                ys.append(y if ok else np.nan)
                marks.append(y if end <= archive_end else np.nan)
                maturity.append(mat)
                supported.append(ok)
                end_age.append(endpoint_age)
            part["Y"] = ys
            part["Y_mark"] = marks
            part["Mature_at"] = maturity
            part["Resolved"] = supported
            part["Endpoint_age"] = end_age
            parts.append(part)
    frame = pd.concat(parts, ignore_index=True)
    for col in (*PERFORMANCE, *SUPPORT, "c00_score"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    frame["can_deposit"] = frame.can_deposit.astype(float)
    # Verify the cumulative expanding-K calculation against the canonical OLS implementation.
    check_rows = frame[frame.H.eq(30) & np.isfinite(frame.k_max)].iloc[:: max(1, int(np.isfinite(frame.k_max).sum() / 90))].head(30)
    for row in check_rows.itertuples():
        end = date_index[row.Date - pd.Timedelta(days=1)]
        j = data["id_index"][int(row.Pair)]
        start = data["first_index"][j]
        expected = k_statistics(arrays["nav"][start : end + 1, j])["K-ratio"][0]
        assert np.isclose(row.k_max, expected, rtol=1e-6, atol=1e-8), (row.Pair, row.Date, row.k_max, expected)
    frame.to_parquet(cache, index=False)
    data["panel"] = frame
    assert (frame.feature_cutoff < frame.Date).all()
    assert (frame.loc[frame.Resolved, "Mature_at"] <= archive_end).all()
    assert required.issubset(set(frame.Date)), "Missing actual engine decision origins"
    return frame
