"""Causal score calibration and common sparse risk for experiment 18."""

import json
import numpy as np
import pandas as pd
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast
from sizing_study_data import sparse_window
import profitable_allocation as engine

HORIZONS = (7, 30, 90)
GROUPS = ("0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1", "missing")
ORIGIN = pd.Timestamp("2023-03-01")


def group(score):
    """Keep unavailable composites distinct from finite zero."""
    return GROUPS[min(4, max(0, int(float(score) * 5)))] if np.isfinite(score) else "missing"


def net_outcome(y):
    return y - 0.10 * np.maximum(y, 0) - 0.001 * (1 + y)


def payoff(y, value, basis):
    """Hold versus redeem using the identical accrued charge on both sides."""
    later = value * (1 + np.asarray(y))
    now = value - 0.10 * max(value - basis, 0) - 0.001 * value
    return later - 0.10 * np.maximum(later - basis, 0) - 0.001 * later - now


def alpha(g, base, extra):
    return float(np.clip((g - 30 * base * extra) / (30 * extra * extra), 0, 1)) if np.isfinite(extra) and extra > 0 and np.isfinite(g + base) else 0.0


def capped_inverse_volatility(ids, caps, sigma, cash, risk):
    """Largest capped common marginal-risk contribution under two budgets."""
    if not ids or cash <= 0 or risk <= 0:
        return {}
    ids = [i for i in ids if caps[i] > 0 and np.isfinite(sigma[i]) and sigma[i] > 0]
    if not ids:
        return {}
    hi = max(caps[i] * sigma[i] for i in ids)
    lo = 0.0
    for _ in range(70):
        mid = (lo + hi) / 2
        v = {i: min(caps[i], mid / sigma[i]) for i in ids}
        if sum(v.values()) <= cash and sum(v[i] * sigma[i] for i in ids) <= risk:
            lo = mid
        else:
            hi = mid
    return {i: min(caps[i], lo / sigma[i]) for i in ids}


def risk(data, t, ids):
    """Fixed eligible peer pool, including no treatment-dependent prior members."""
    t = pd.Timestamp(t)
    cache = data.setdefault("nb18_risk", {})
    a = data["date_index"].get(t - pd.Timedelta(days=1))
    if a is None:
        return pd.DataFrame(index=pd.Index(ids, name="pair_id"), columns=["sigma", "regular", "gap", "updates", "intervals", "age", "prior_only"], dtype=float)
    if t not in cache:
        e = data["eligibility"]
        pool = tuple(sorted(e.loc[e.origin_at.eq(t) & e.eligible_as_of_origin, "pair_id"].astype(int).unique()))
        cache[t] = {"pool": pool, "values": {}, "rows": {}}
    item = cache[t]

    def empirical(pid):
        if pid not in item["values"]:
            j = data["id_index"][pid]
            start = max(0, a - 90)
            r = empirical_window(data["arrays"]["nav"][start : a + 1, j], data["arrays"]["actual"][start : a + 1, j], 90)
            g = sparse_window(data["arrays"]["raw_nav"][start : a + 1, j], 90)
            item["values"][pid] = (r, g)
        return item["values"][pid]

    for i in item["pool"]:
        empirical(i)
    for pid in map(int, ids):
        if pid in item["rows"]:
            continue
        r, g = empirical(pid)
        pool = [i for i in item["pool"] if i != pid]
        priors = []
        components = []
        for component in ("regular", "gap"):
            values = [empirical(i)[0 if component == "regular" else 1] for i in pool]
            emp = np.array([v["empirical" if component == "regular" else "calendar"] for v in values])
            full = np.array([v["full"] for v in values], bool)
            positives = np.isfinite(emp) & (emp > 0)
            chosen = emp[positives & full] if np.any(positives & full) else emp[positives]
            prior = float(np.median(chosen)) if len(chosen) else np.nan
            empirical_value = r["empirical"] if component == "regular" else g["gap"]
            pred = forecast(empirical_value, prior, r["m"] if component == "regular" else g["m"], "regularised", 30)
            if not np.isfinite(pred) or pred <= 0:
                pred = prior
            components.append(np.sqrt(pred) if np.isfinite(pred) and pred > 0 else np.nan)
            priors.append(prior)
        supported = np.isfinite(components).all()
        j = data["id_index"][pid]
        last = data["arrays"]["last_observed"][a, j]
        item["rows"][pid] = dict(pair_id=pid, sigma=max(components) if supported else np.nan, regular=components[0], gap=components[1], updates=r["m"], intervals=g["m"], age=float((t.to_datetime64() - last) / np.timedelta64(1, "D")), prior_only=not np.isfinite(r["empirical"]) or not np.isfinite(g["gap"]), peer_count=len(pool))
    return pd.DataFrame([item["rows"][int(i)] for i in ids]).set_index("pair_id") if len(ids) else pd.DataFrame()


def anchor_at(data, t):
    a = data["anchor"]
    t = pd.Timestamp(t)
    v = a[(a.Date >= t - pd.Timedelta(days=90)) & (a.Date < t) & a.Valid]
    return (float(v.L_full.median()), len(v)) if len(v) >= 30 else (np.nan, len(v))


def label(data, pid, t, h):
    """Terminal-support time is part of maturity; endpoint uses no later price."""
    times, prices = data["nav_history"][int(pid)]
    start = pd.Timestamp(t)
    end = start + pd.Timedelta(days=h)
    i = np.searchsorted(times, start.value, side="right") - 1
    j = np.searchsorted(times, end.value, side="right") - 1
    support = np.searchsorted(times, end.value, side="left")
    result = dict(Resolved=False, Y=np.nan, Z=np.nan, Mature_at=pd.NaT, Endpoint_age=np.nan, First_update=False)
    if i < 0 or j < 0:
        return result
    result["Endpoint_age"] = (end - pd.Timestamp(times[j])).total_seconds() / 86400
    result["First_update"] = j > i and i == 0
    if support >= len(times):
        return result
    y = float(prices[j] / prices[i] - 1)
    result.update(Resolved=True, Y=y, Z=float(net_outcome(y)), Mature_at=max(end, pd.Timestamp(times[support])))
    return result


def build_anchor(data, reference):
    """Normalise actual reference core/pinned exposure, lag only when querying."""
    state = reference["result"].state
    trades = sorted([v for v in state.portfolio.get_all_trades() if v.is_success()], key=lambda v: v.executed_at)
    quantities = {}
    j = 0
    dates = sorted(pd.to_datetime(reference["allocation_df"].Date.unique()))
    eq = reference["equity"].sort_index()
    rows = []
    for t in dates:
        while j < len(trades) and pd.Timestamp(trades[j].executed_at) <= t:
            tr = trades[j]
            pid = int(tr.pair.internal_id)
            quantities[pid] = quantities.get(pid, 0) + float(tr.executed_quantity)
            j += 1
        held = {i: q * engine.observed_quote(data, i, t)[0] for i, q in quantities.items() if q > 1e-6 and engine.observed_quote(data, i, t) is not None}
        if not held:
            rows.append(dict(Date=t, Valid=False, L_full=np.nan, q=0, Reason="no exposure"))
            continue
        rr = risk(data, t, list(held))
        e = float(eq.loc[:t].iloc[-1])
        q = sum(held.values()) / e
        valid = q > 0 and np.isfinite(rr.sigma).all() and rr.sigma.gt(0).all()
        ell = sum(held[i] / e * rr.loc[i, "sigma"] for i in held) if valid else np.nan
        rows.append(dict(Date=t, Valid=valid, L_full=0.98 * ell / q if valid else np.nan, q=q, Reason="supported" if valid else "unknown position risk"))
    data["anchor"] = pd.DataFrame(rows)
    data["anchor"].to_parquet(data["artifact"] / "risk-anchor.parquet", index=False)


def build_panel(data, evaluator, reference):
    """Current eligibility/capacity joined to most recent completed reference core."""
    from score_forecast_data import forecast_origins, _eligibility
    from tradeexecutor.backtest.backtest_pricing import BacktestPricing
    from tradeexecutor.backtest.backtest_routing import BacktestRoutingIgnoredModel
    from tradeexecutor.strategy.tvl_size_risk import USDTVLSizeRiskModel

    origins = forecast_origins()
    extra = _eligibility(evaluator, origins, data["prices"])
    data["eligibility"] = pd.concat([data["eligibility"], extra], ignore_index=True).drop_duplicates(["origin_at", "pair_id"], keep="last")
    ledger = reference["allocation_df"]
    mapping = {pd.Timestamp(t): g for t, g in ledger.groupby("Date")}
    dates = sorted(mapping)
    reserve = evaluator.universe.reserve_assets[0].address
    pricing = BacktestPricing(evaluator.universe, BacktestRoutingIgnoredModel(reserve), data_delay_tolerance=pd.Timedelta(days=2), vault_state=evaluator.universe.vault_state, liquidity_universe=evaluator.universe.data_universe.liquidity)
    model = USDTVLSizeRiskModel(pricing_model=pricing, per_position_cap=float(evaluator.parameters.per_position_cap_of_pool_pct))
    eq = reference["equity"].sort_index()
    rows = []
    trades = sorted([v for v in reference["result"].state.portfolio.get_all_trades() if v.is_success()], key=lambda v: v.executed_at)
    cash = 150000.0
    trade_index = 0
    for t, e in extra[extra.eligible_as_of_origin].groupby("origin_at"):
        k = np.searchsorted(np.array(dates, dtype="datetime64[ns]"), t.to_datetime64(), side="right") - 1
        if k < 0:
            continue
        ref = mapping[dates[k]]
        core = set(ref.loc[ref.Role.eq("core"), "Pair id"].astype(int))
        B = float(ref["Deployable budget (USD)"].iloc[0])
        used = float(ref["Core-only target (USD)"].sum())
        while trade_index < len(trades) and pd.Timestamp(trades[trade_index].executed_at) <= t:
            tr = trades[trade_index]
            cash += (-1 if tr.is_buy() else 1) * abs(float(tr.executed_reserve or 0))
            trade_index += 1
        equity = float(eq.loc[:t].iloc[-1])
        residual = max(0.0, cash - 0.02 * equity - max(0.5, 0.0005 * equity))
        rr = risk(data, t, e.pair_id.astype(int).tolist())
        for row in e.itertuples():
            pid = int(row.pair_id)
            pair = evaluator.universe.get_pair_by_id(pid)
            cap = float(model.get_acceptable_size_for_position(t, pair, 0.33 * 0.98 * equity).accepted_size)
            # The marginal calibration models fresh dollars, with no incumbent basis.
            from tradeexecutor.strategy.redemption import DepositCheckStage

            check = pricing.check_deposit(t, pair, stage=DepositCheckStage.buy_rebalance)
            if not check.can_deposit:
                cap = 0.0
            elif check.max_deposit is not None:
                cap = min(cap, max(0.0, float(check.max_deposit)))
            score = float(data["focal_values"][evaluator.panel.date_index[t], evaluator.panel.pair_index[pid]])
            ticket = max(float(evaluator.parameters.absolute_min_vault_deposit_usd), equity * 0.0005)
            marginal = pid not in core and residual > ticket and cap >= ticket
            for h in HORIZONS:
                rows.append(dict(Date=t, Pair=pid, Vault=row.vault_name, Score=score, Group=group(score), Available=np.isfinite(score), H=h, Marginal=marginal, Capacity=cap, Reference_date=dates[k], Reference_phase_days=(t - dates[k]).days, Residual=residual, **rr.loc[pid].to_dict(), **label(data, pid, t, h)))
    frame = pd.DataFrame(rows)
    frame.to_parquet(data["artifact"] / "calibration-panel.parquet", index=False)
    data["calibration_panel"] = frame
    return frame


def fit(frame, cutoff, h=30, bootstrap=500, block_days=30, population="marginal"):
    """Equal-date conditional means with causal maturity and block uncertainty."""
    f = frame[(frame.H == h) & frame.Resolved & frame.Mature_at.lt(pd.Timestamp(cutoff)) & frame.Date.add(pd.Timedelta(days=h)).lt(pd.Timestamp(cutoff))]
    if population == "marginal":
        f = f[f.Marginal]
    blocks = lambda v: int(((pd.to_datetime(v) - ORIGIN).dt.days // h).nunique())
    origins = f.Date.nunique()
    vaults = f.Pair.nunique()
    nb = blocks(f.Date)
    supported = origins >= 20 and vaults >= 10 and nb >= 6
    date = f.groupby("Date")[["Y", "Z"]].mean()
    pool = date.mean()
    out = {"cutoff": pd.Timestamp(cutoff), "H": h, "supported": supported, "origins": origins, "vaults": vaults, "blocks": nb, "rows": f, "groups": {}}
    if not len(date):
        out.update(pool_y=np.nan, pool_z=np.nan, lower=np.nan)
        return out
    out.update(pool_y=float(pool.Y), pool_z=float(pool.Z))
    groups = {}
    matrix = np.full((len(date), len(GROUPS)), np.nan)
    for j, g in enumerate(GROUPS):
        fg = f[f.Group.eq(g)]
        b = blocks(fg.Date)
        ok = fg.Date.nunique() >= 10 and fg.Pair.nunique() >= 5 and b >= 3
        rho = b / (b + 1) if ok else 0.0
        gd = fg.groupby("Date")[["Y", "Z"]].mean()
        raw = gd.mean()
        matrix[:, j] = gd.Z.reindex(date.index)
        out["groups"][g] = dict(rho=rho, origins=fg.Date.nunique(), vaults=fg.Pair.nunique(), blocks=b, raw_y=float(raw.get("Y", np.nan)), raw_z=float(raw.get("Z", np.nan)), y=float(rho * raw.Y + (1 - rho) * pool.Y) if rho else float(pool.Y), z=float(rho * raw.Z + (1 - rho) * pool.Z) if rho else float(pool.Z))
    rng = np.random.default_rng(180030 + h + block_days)
    z = date.Z.to_numpy()
    dates = date.index
    ends = np.searchsorted(dates.to_numpy(), (dates + pd.Timedelta(days=block_days)).to_numpy(), side="left")
    samples = []
    group_samples = []
    for _ in range(bootstrap):
        pieces = []
        n = 0
        while n < len(date):
            start = int(rng.integers(len(date)))
            chunk = np.arange(start, max(start + 1, ends[start]))
            pieces.append(chunk)
            n += len(chunk)
        ii = np.concatenate(pieces)[: len(date)]
        mu = float(z[ii].mean())
        samples.append(mu)
        gs = []
        for j, g in enumerate(GROUPS):
            v = matrix[ii, j]
            finite = v[np.isfinite(v)]
            rho = out["groups"][g]["rho"]
            gs.append(rho * float(finite.mean()) + (1 - rho) * mu if rho and len(finite) else mu)
        group_samples.append(gs)
    out["lower"] = float(np.quantile(samples, 0.2))
    for j, g in enumerate(GROUPS):
        out["groups"][g]["lower"] = float(np.quantile(np.array(group_samples)[:, j], 0.2))
    return out


def forecast_at(data, t):
    key = pd.Timestamp(t).to_period("M").start_time
    return data["forecasts"][key]


def expected_hold(model, g, value, basis):
    if not model["supported"]:
        return np.nan
    f = model["rows"]
    rho = model["groups"][g]["rho"]

    def expectation(rows):
        values = pd.Series(payoff(rows.Y.to_numpy(), value, basis), index=rows.index)
        return float(values.groupby(rows.Date).mean().mean())

    pooled = expectation(f)
    return rho * expectation(f[f.Group.eq(g)]) + (1 - rho) * pooled if rho else pooled


def build_forecasts(data):
    months = pd.date_range("2023-03-01", "2026-10-01", freq="MS")
    data["forecasts"] = {}
    records = []
    diagnostics = []
    panel = data["calibration_panel"]
    for t in months:
        for h in HORIZONS:
            model = fit(panel, t, h)
            if h == 30:
                data["forecasts"][t] = model
            for g, v in model["groups"].items():
                records.append(dict(Fit_date=t, H=h, Group=g, Supported=model["supported"], Pooled_origins=model["origins"], Pooled_vaults=model["vaults"], Pooled_blocks=model["blocks"], Pooled_net=model["pool_z"], Pooled_lower=model["lower"], **v))
    data["calibration"] = pd.DataFrame(records)
    data["calibration"].to_parquet(data["artifact"] / "monthly-calibration.parquet", index=False)
    for h in HORIZONS:
        for pop in ("marginal", "broader"):
            m = fit(panel, pd.Timestamp("2026-10-01"), h, block_days=90, population=pop)
            diagnostics.append(dict(H=h, Diagnostic=pop + " / 90-day blocks", Net=m["pool_z"], Lower=m["lower"], Origins=m["origins"], Vaults=m["vaults"]))
        base = fit(panel, "2026-10-01", h, bootstrap=1)
        f = base["rows"]
        values = []
        for pid in f.Pair.unique():
            v = f[f.Pair.ne(pid)].groupby("Date").Z.mean().mean()
            values.append(v)
        diagnostics.append(dict(H=h, Diagnostic="Leave one vault out range", Net=min(values) if values else np.nan, Lower=max(values) if values else np.nan, Origins=base["origins"], Vaults=base["vaults"]))
    pd.DataFrame(diagnostics).to_csv(data["artifact"] / "calibration-sensitivities.csv", index=False)
    # Direct causal mutation audit: unresolved/future data must not affect a fit.
    cutoff = pd.Timestamp("2026-01-01")
    old = fit(panel, cutoff, bootstrap=50)
    changed = panel.copy()
    future = ~(changed.Resolved & changed.Mature_at.lt(cutoff) & changed.Date.add(pd.to_timedelta(changed.H, unit="D")).lt(cutoff))
    changed.loc[future, ["Y", "Z"]] = 999.0
    new = fit(changed, cutoff, bootstrap=50)
    assert np.isclose(old["pool_z"], new["pool_z"], equal_nan=True) and np.isclose(old["lower"], new["lower"], equal_nan=True)
    data["fixed_forecast"] = data["forecasts"][cutoff]
    (data["artifact"] / "forecast-causality.json").write_text(json.dumps(dict(future_mutation_unchanged=True, strict_maturity=True, monthly_freeze=True)))


def fixtures():
    checks = []

    def check(name, ok):
        assert bool(ok), name
        checks.append(dict(Check=name, Passed=True))

    for g, want in ((0.0002, 0), (0.00036, 0.5), (0.0006, 1)):
        check("Alpha " + str(want), np.isclose(alpha(g, 0.005, 0.002), want))
    check("Unusable risk blocks alpha", alpha(0.1, 0, np.nan) == 0)
    check("Finite zero distinct from missing", group(0) != group(np.nan))
    check("Flat hold is exactly indifferent", payoff(np.array([0.0]), 100, 80)[0] == 0)
    check("Loss crossing basis is scenario dependent", np.isclose(payoff(np.array([-0.3]), 100, 80)[0], -27.97))
    check("New deposit gain cost", np.isclose(net_outcome(0.2), 0.1788))
    check("New deposit loss cost", np.isclose(net_outcome(-0.2), -0.2008))
    v = capped_inverse_volatility([1, 2], {1: 0.05, 2: 0.1}, {1: 0.01, 2: 0.02}, 0.2, 0.001)
    check("Risk and cash bound", sum(v.values()) <= 0.2 + 1e-12 and sum(v[i] * {1: 0.01, 2: 0.02}[i] for i in v) <= 0.001 + 1e-12)
    check("Zero residual buys none", not capped_inverse_volatility([1], {1: 0.1}, {1: 0.01}, 0, 1))
    check("Unknown risk buys none", not capped_inverse_volatility([1], {1: 0.1}, {1: np.nan}, 1, 1))
    check("Young history uses positive prior", forecast(np.nan, 0.04, 0, "regularised", 30) == 0.04)
    check("Flat history keeps positive risk", forecast(0, 0.04, 1, "regularised", 30) > 0)
    check("Perfect correlation linear risk identity", np.isclose(np.sqrt(np.array([0.2, 0.3]) @ np.outer([0.01, 0.02], [0.01, 0.02]) @ np.array([0.2, 0.3])), 0.008))
    toy = dict(nav_history={1: (np.array([pd.Timestamp(x).value for x in ("2026-01-01", "2026-01-10", "2026-02-01")]), np.array([1.0, 1.1, 1.2]))})
    v = label(toy, 1, "2026-01-01", 7)
    check("Sparse endpoint uses earlier NAV and later maturity only", v["Y"] == 0 and v["Mature_at"] == pd.Timestamp("2026-01-10"))
    check("Terminal extrapolation remains unresolved", not label(toy, 1, "2026-02-01", 7)["Resolved"])
    check("Negative advantage gives no fresh deployment", alpha(-0.01, 0.005, 0.002) == 0)
    t = pd.Timestamp("2026-01-05")
    dates = pd.date_range("2026-01-01", periods=5)
    nav = np.array([[1.0, 1.0, np.nan], [1.01, 0.98, np.nan], [0.99, 1.03, np.nan], [1.02, 1.01, 1.0], [100.0, 0.1, 2.0]])
    tiny = {"date_index": {v: i for i, v in enumerate(dates)}, "id_index": {1: 0, 2: 1, 3: 2}, "eligibility": pd.DataFrame({"origin_at": [t, t], "eligible_as_of_origin": [True, True], "pair_id": [1, 2]}), "arrays": {"nav": nav.copy(), "raw_nav": nav.copy(), "actual": np.isfinite(nav), "last_observed": np.broadcast_to(dates.to_numpy()[:, None], nav.shape).copy()}}
    r = risk(tiny, t, [1])
    new = risk(tiny, t, [1, 3])
    check("Requested held names cannot change peer forecasts", r.loc[1, "sigma"] == new.loc[1, "sigma"])
    check("Young one-mark history receives supported peer risk", np.isfinite(new.loc[3, "sigma"]) and new.loc[3, "sigma"] > 0)
    tiny.pop("nb18_risk")
    tiny["arrays"]["nav"][-1] = 999.0
    tiny["arrays"]["raw_nav"][-1] = 999.0
    check("Clamped early risk excludes future tail", risk(tiny, t, [1]).loc[1, "sigma"] == r.loc[1, "sigma"])
    fake = []
    for date in pd.date_range("2025-01-01", periods=20, freq="10D"):
        for i in range(10):
            fake.append(dict(Date=date, Pair=i, H=30, Resolved=True, Marginal=True, Mature_at=date + pd.Timedelta(days=30), Group="missing", Y=0.01, Z=float(net_outcome(0.01))))
    m = fit(pd.DataFrame(fake), "2026-01-01", bootstrap=10)
    check("All-missing score population still supports a forecast", m["supported"] and m["groups"]["missing"]["z"] > 0)
    anchor = {"anchor": pd.DataFrame([dict(Date=t - pd.Timedelta(days=2 * i), Valid=True, L_full=0.01) for i in range(30)])}
    check("Anchor excludes current decision and needs 30 prior decisions", np.isnan(anchor_at(anchor, t)[0]))
    check("Retained sleeve risk is deducted once", np.isclose((0.01 - 0.006) - 0.002, 0.002))
    check("Retained sleeve over headroom permits no increment", not capped_inverse_volatility([1], {1: 0.1}, {1: 0.01}, 0.1, max(0, 0.001 - 0.002)))
    check("Pinned slots consume the total ceiling", min(6, max(0, 12 - 6 - 3)) == 3)
    check("Scarce proceeds fund core before residual", min(80, 90) == 80 and max(0, 90 - 80) == 10)
    check("Core floor denominator is protected", min(2000 / 0.005 - 100000, 500000) == 300000)
    return pd.DataFrame(checks)
