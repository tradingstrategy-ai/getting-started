"""Frozen stateless baskets, fixed units, and bounded entry allocations."""

import itertools
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from portfolio_snapshot_data import METHODS, CONFIG, ARTIFACT, HORIZONS, END, future_panel
from portfolio_snapshot_risk import qlike_difference


def select_basket(candidates, N, exclude_unscored=False, tie_priorities=None):
    """Finite scores precede missing scores; address resolves equal scores."""
    frame = candidates.copy()
    if "eligible_as_of_origin" in frame:
        frame = frame[frame.eligible_as_of_origin]
    if exclude_unscored:
        frame = frame[np.isfinite(frame.score)]
    frame["tier"] = np.where(np.isfinite(frame.score), 0, 1)
    frame["tie"] = frame.vault_address.str.lower() if tie_priorities is None else frame.vault_address.map(tie_priorities)
    return frame.sort_values(["tier", "score", "tie"], ascending=[True, False, True], na_position="last", kind="stable").head(N)


def risk_weights(variances, p):
    """Return normalised weights; unsupported risk falls back for the whole basket."""
    v = np.asarray(variances, float)
    if not len(v):
        return v.copy()
    if p == 0 or not (np.isfinite(v) & (v > 0)).all():
        return np.full(len(v), 1 / len(v))
    logs = -p / 2 * np.log(v)
    u = np.exp(logs - logs.max())
    return u / u.sum()


def bounded_proportional(desired, caps, budget):
    """Water-fill accepted entry weights within each explicit capacity."""
    u = np.asarray(desired, float)
    c = np.asarray(caps, float)
    if len(u) != len(c) or np.any(~np.isfinite(c)) or np.any(c < 0) or np.any(u < 0):
        raise ValueError("Invalid desired weights/capacities")
    out = np.zeros(len(u))
    target = min(budget, float(c[u > 0].sum()))
    remaining = target
    free = (u > 0) & (c > 0)
    for _ in range(len(u) + 1):
        if not free.any() or remaining <= 1e-14:
            break
        proposed = remaining * u[free] / u[free].sum()
        indices = np.flatnonzero(free)
        hit = proposed > c[free] + CONFIG["matrix_tolerance"]
        if not hit.any():
            out[indices] = proposed
            break
        fixed = indices[hit]
        out[fixed] = c[fixed]
        remaining -= out[fixed].sum()
        free[fixed] = False
    assert np.all(out <= c + 1e-10) and np.isclose(out.sum(), target, atol=1e-10)
    return out


def fixed_unit_path(price_matrix, weights, cash=None):
    """Value one initial account with drifting positions, without daily mixing."""
    p = np.asarray(price_matrix, float)
    w = np.asarray(weights, float)
    cash = 1 - w.sum() if cash is None else cash
    active = w > 0
    if not active.any():
        return np.ones(len(p))
    return cash + (p[:, active] / p[0, active]) @ w[active]


def policy_registry():
    rows = []

    def add(score, N=6, L=90, p=2, estimator="regularised", branch="pure", variant="main", state="permissive", redistribute=True, cap=0.33, account=150000, satellite=0):
        row = dict(score=score, N=N, L=L, p=float(p), estimator=estimator, branch=branch, variant=variant, state=state, redistribute=redistribute, cap=cap, account=account, satellite=satellite)
        row["policy_id"] = f"{score}|N{N}|{estimator}|L{L}|p{p:g}|{branch}|{variant}|{state}|r{int(redistribute)}|c{cap:g}|a{account}|s{satellite:g}"
        if not any(r["policy_id"] == row["policy_id"] for r in rows):
            rows.append(row)

    for score in METHODS:
        for N in (4, 6, 8, 10):
            add(score, N=N, p=0, estimator="equal")
        for L in (30, 60, 90, 180):
            for estimator in ("raw", "regularised"):
                for p in (0.5, 1, 2):
                    add(score, L=L, p=p, estimator=estimator)
            if L != 90:
                add(score, L=L, p=2, estimator="kappa30", variant="fixed_kappa")
        for estimator in ("raw", "regularised"):
            for N in (4, 8, 10):
                for p in (1, 2):
                    add(score, N=N, p=p, estimator=estimator)
            for L in (75, 105):
                add(score, L=L, estimator=estimator, variant="local_window")
        for estimator in ("kappa10", "kappa90", "gate5", "gate10", "floor_low", "floor_high"):
            add(score, estimator=estimator, variant="risk_sensitivity")
        add(score, estimator="source", variant="source_candle_control")
        add(score, variant="exclude_unscored")
        for p in (0, 1, 2):
            estimator = "equal" if p == 0 else "regularised"
            for state in ("permissive", "known_only"):
                for redistribute in (True, False):
                    add(score, p=p, estimator=estimator, branch="capacity", state=state, redistribute=redistribute)
            # Source only reports hard caps; its entry gate is already in candidate eligibility.
            add(score, p=p, estimator=estimator, branch="capacity", state="source_report_only")
        for cap in (0.2, 0.25, 0.33):
            for account in (75000, 150000, 300000):
                add(score, branch="capacity", cap=cap, account=account, variant="capacity_surface")
        for satellite in (0.1, 0.2):
            add(score, N=10, satellite=satellite, variant="satellite")
        for variant in ("minimum_variance", "equal_risk_contribution", "minimum_variance_gate60"):
            add(score, variant=variant)
    return pd.DataFrame(rows)


def covariance_weights(data, origin, ids, variances, method, gate=30):
    """Ledoit–Wolf correlations rescaled by the frozen marginal forecasts."""
    from sklearn.covariance import LedoitWolf
    from scipy.optimize import minimize

    v = np.asarray(variances, float)
    N = len(v)
    if not N:
        return v, "empty", np.nan, np.nan
    if not (np.isfinite(v) & (v > 0)).all():
        return risk_weights(v, 0), "risk_fallback_equal", np.nan, np.nan
    a = data["date_index"][origin - pd.Timedelta(days=1)]
    jj = [data["id_index"][int(pid)] for pid in ids]
    start = max(a - 90, int(np.max(data["first_index"][jj])))
    p = data["arrays"]["nav"][start : a + 1, jj]
    actual = data["arrays"]["actual"][start + 1 : a + 1, jj].sum(axis=0)
    status = "estimated_correlation"
    corr = np.eye(N)
    shrink = np.nan
    if len(p) - 1 < gate or (actual < 3).any():
        status = "correlation_prior_identity"
    else:
        r = p[1:] / p[:-1] - 1
        lw = LedoitWolf(assume_centered=False).fit(r)
        C = lw.covariance_
        shrink = lw.shrinkage_
        sigma = np.sqrt(np.diag(C))
        den = sigma[:, None] * sigma[None, :]
        corr = np.divide(C, den, out=np.zeros_like(C), where=den > 0)
        np.fill_diagonal(corr, 1)
    cov = corr * np.sqrt(v[:, None] * v[None, :])
    data.setdefault("_covariance_cache", {})[(origin, tuple(map(int, ids)), gate)] = cov.copy()
    scale = np.diag(cov).mean()
    C = cov / scale
    assert np.allclose(C, C.T, atol=CONFIG["matrix_tolerance"]) and np.linalg.eigvalsh(C).min() > -CONFIG["matrix_tolerance"]
    jitter = 0.0
    if np.linalg.eigvalsh(C).min() <= 0:
        jitter = CONFIG["numerical_jitter_relative"]
        C += jitter * np.eye(N)
    if method == "minimum_variance":
        solve = minimize(lambda w: w @ C @ w, np.full(N, 1 / N), jac=lambda w: 2 * C @ w, bounds=[(0, 1)] * N, constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(N)}], method="SLSQP", options={"ftol": CONFIG["solver_tolerance"], "maxiter": CONFIG["solver_iterations"]})
        w = np.maximum(solve.x, 0)
        w /= w.sum()
    else:
        b = np.full(N, 1 / N)
        x0 = 1 / np.sqrt(N * np.diag(C))
        solve = minimize(lambda x: 0.5 * x @ C @ x - np.sum(b * np.log(x)), x0, jac=lambda x: C @ x - b / x, bounds=[(CONFIG["positive_solver_bound"], None)] * N, method="L-BFGS-B", options={"ftol": CONFIG["erc_objective_tolerance"], "gtol": CONFIG["solver_tolerance"], "maxiter": CONFIG["solver_iterations"]})
        w = solve.x / solve.x.sum()
        rc = w * (C @ w)
        rc /= rc.sum()
        if np.max(np.abs(rc - 1 / N)) > CONFIG["risk_contribution_tolerance"]:
            solve.success = False
    if not solve.success:
        return risk_weights(v, 2), "solver_fallback_diagonal", shrink, float(jitter * scale)
    return w, status, shrink, float(jitter * scale)


def capacity_limits(data, origin, basket, policy):
    """Archived hard caps are a declared diagnostic beyond source open/closed gates."""
    account = policy.account
    cap = policy.cap
    L = []
    unknown = []
    a = origin - pd.Timedelta(days=1)
    cache = data.setdefault("_tvl_state_cache", {})
    if origin in cache:
        state = cache[origin]
    else:
        price = data["prices"]
        price = price[(price.date <= a) & (price.date >= a - pd.Timedelta(days=2))]
        price = price[np.isfinite(price.total_assets)]
        state = price.sort_values("date").groupby("pair_id").tail(1).set_index("pair_id")
        cache[origin] = state
    for row in basket.itertuples():
        tvl = state.loc[row.pair_id, "total_assets"] if row.pair_id in state.index else np.nan
        hard = row.max_deposit
        hard = float(hard) if pd.notna(hard) else np.nan
        known_capacity = np.isfinite(hard) and pd.notna(row.capacity_observed_at) and pd.Timedelta(0) <= origin - pd.Timestamp(row.capacity_observed_at) <= pd.Timedelta(days=2)
        known_permission = not row.permission_time_unknown and pd.notna(row.permission_observed_at) and pd.Timedelta(0) <= origin - pd.Timestamp(row.permission_observed_at) <= pd.Timedelta(days=2)
        is_unknown = not known_capacity or not known_permission or not np.isfinite(tvl)
        if policy.state == "known_only" and is_unknown:
            limit = 0.0
        else:
            limit = cap
            if np.isfinite(tvl):
                limit = min(limit, max(0, float(tvl)) * 0.33 / account)
            elif policy.state == "known_only":
                limit = 0.0
            if policy.state != "source_report_only" and np.isfinite(hard):
                limit = min(limit, max(0, hard) / account)
        L.append(limit)
        unknown.append(is_unknown)
    return np.array(L), np.array(unknown)


def outcome_metrics(panel, w, variances=None):
    """Report unresolved portfolios without renormalising surviving names."""
    active = w > 0
    cash = 1 - w.sum()
    resolved = bool(panel["supported"][active].all())
    unknown = float(w[active & ~panel["supported"]].sum())
    known = float(np.nansum(w * panel.get("returns", np.zeros(len(w)))))
    q = w / w.sum() if w.sum() > 0 else np.zeros(len(w))
    result = dict(resolved=resolved, unresolved_weight=unknown, lower_return_bound=known - unknown, upper_return_bound=np.inf if unknown else known, known_return_contribution=known, cash=cash, max_weight=float(w.max()) if len(w) else 0, effective_N=float(1 / np.sum(q * q)) if w.sum() else 0, carried_anchor_weight=float(w[panel.get("anchor_carried", np.zeros(len(w), bool))].sum()), carried_endpoint_weight=float(w[panel.get("endpoint_carried", np.zeros(len(w), bool))].sum()), no_update_weight=float(w[panel.get("future_updates", np.zeros(len(w))) == 0].sum()), anchor_age_weighted=float(np.dot(w, panel.get("anchor_age", np.zeros(len(w))))), endpoint_age_weighted=float(np.dot(w, panel.get("endpoint_age", np.zeros(len(w))))))
    for key in ("return", "variance", "sharpe", "drawdown", "first_update", "remaining", "forecast_variance"):
        result[key] = np.nan
    if resolved:
        path = fixed_unit_path(panel["paths"], w, cash)
        dr = path[1:] / path[:-1] - 1
        var = np.var(dr, ddof=1)
        result.update({"return": float(path[-1] - 1), "variance": float(var), "sharpe": float(dr.mean() / np.sqrt(var) * np.sqrt(365)) if var > 0 else np.nan, "drawdown": float(np.min(path / np.maximum.accumulate(path) - 1))})
        if np.isfinite(panel.get("first_update", np.full(len(w), np.nan))[active]).all():
            result["first_update"] = float(np.dot(w[active], panel["first_update"][active]))
            result["remaining"] = float(np.dot(w[active], panel["remaining"][active]))
        if variances is not None and np.isfinite(np.asarray(variances)[active]).all():
            result["forecast_variance"] = float(np.dot(w[active] ** 2, np.asarray(variances)[active]))
    return result


def run_snapshots(data, risk, policies=None):
    """Evaluate the predeclared stage registry, sharing each selected future path."""
    from tqdm_loggable.auto import tqdm

    policies = policy_registry() if policies is None else policies
    groups = {(t, m): f for (t, m), f in data["candidates"].groupby(["origin_at", "method_id"], observed=True)}
    risk_lookup = {(t, int(L)): f.set_index("pair_id") for (t, L), f in risk.groupby(["origin_at", "L"])}
    allocations = []
    outcomes = []
    rank_rows = []
    risk_rows = []
    ic_rows = []
    population = []
    stability = []
    previous = {}
    eligible_groups = {t: f for t, f in data["eligibility"][data["eligibility"].eligible_as_of_origin].groupby("origin_at")}
    origin_list = data["origins"].sort_values("origin_at")
    for origin_row in tqdm(list(origin_list.itertuples()), desc="Snapshot portfolios; approximately 4–8 minutes"):
        origin = origin_row.origin_at
        phase = origin_row.phase
        per_origin = policies if phase == 0 else policies[(policies.branch == "pure") & (policies.variant == "main") & (policies.L == 90) & (policies.p.isin([0, 1, 2])) & (policies.estimator.isin(["equal", "raw", "regularised"]))]
        eligible = eligible_groups.get(origin, data["eligibility"].iloc[:0])
        ids_all = eligible.pair_id.to_numpy()
        eligible_targets = {h: future_panel(data, origin, h, ids_all) for h in HORIZONS if origin + pd.Timedelta(days=h) <= END}
        for h, target in eligible_targets.items():
            population.append(dict(origin_at=origin, h=h, phase=phase, candidates=len(eligible), target_supported=int(target["supported"].sum()), actual_anchor=int((~target["anchor_carried"]).sum()), actual_endpoint=int((~target["endpoint_carried"]).sum())))
        for method in METHODS:
            candidates = groups.get((origin, method), data["candidates"].iloc[:0])
            ranked = select_basket(candidates, 20)
            for h, target in eligible_targets.items():
                mapping = {int(pid): i for i, pid in enumerate(ids_all)}
                good = np.isfinite(candidates.score.to_numpy()) & np.array([target["supported"][mapping[int(pid)]] for pid in candidates.pair_id], dtype=bool)
                ss = candidates.score.to_numpy()[good]
                r = target["returns"][[mapping[int(pid)] for pid in candidates.pair_id]][good]
                sh = target["sharpe"][[mapping[int(pid)] for pid in candidates.pair_id]][good]
                for name, y in (("return", r), ("sharpe", sh)):
                    finite = np.isfinite(ss) & np.isfinite(y)
                    n = int(finite.sum())
                    value = float(spearmanr(ss[finite], y[finite]).statistic) if n >= 3 and np.ptp(ss[finite]) > 0 and np.ptp(y[finite]) > 0 else np.nan
                    ic_rows.append(dict(origin_at=origin, score=method, h=h, target=name, ic=value, n=n, unscored=int(candidates.score.isna().sum()), phase=phase))
                for rank, row in enumerate(ranked.itertuples(), 1):
                    i = mapping[int(row.pair_id)]
                    rank_rows.append(dict(origin_at=origin, score=method, h=h, rank=rank, pair_id=row.pair_id, return_value=target["returns"][i], supported=target["supported"][i], score_value=row.score, tier=row.tier, phase=phase))
            # Risk diagnostics on all eligible and the exact frozen top six.
            if phase == 0:
                selected = set(select_basket(candidates, 6).pair_id)
                for L in (30, 60, 90, 180):
                    rf = risk_lookup.get((origin, L))
                    if rf is None:
                        continue
                    for h, target in eligible_targets.items():
                        for estimator in ("raw", "regularised", "source"):
                            if estimator == "source" and L != 90:
                                continue
                            for pid in candidates.pair_id:
                                i = mapping[int(pid)]
                                rr = rf.loc[pid]
                                pred = rr[estimator]
                                real = target["variance"][i]
                                risk_rows.append(dict(origin_at=origin, score=method, L=L, h=h, estimator=estimator, pair_id=int(pid), predicted=pred, reference=rr.prior, realised=real, qlike_delta=float(qlike_difference(pred, rr.prior, real)), selected=pid in selected, prior_count=rr.prior_count, history_age=rr.history_age, actual_fraction=rr.actual_fraction, anchor_age=rr.anchor_age, phase=phase))
            method_policies = per_origin[per_origin.score == method]
            baskets = {}
            for policy in method_policies.itertuples():
                key = (policy.N, policy.variant == "exclude_unscored")
                if key not in baskets:
                    baskets[key] = select_basket(candidates, policy.N, key[1])
                basket = baskets[key]
                ids = basket.pair_id.to_numpy()
                N = len(ids)
                rf = risk_lookup.get((origin, policy.L))
                v = np.full(N, np.nan) if rf is None else rf.reindex(ids)[policy.estimator if policy.estimator != "equal" else "regularised"].to_numpy()
                fallback = policy.p > 0 and not (np.isfinite(v) & (v > 0)).all()
                w = risk_weights(v, policy.p)
                status = "risk_fallback_equal" if fallback else "estimated"
                shrink = jitter = np.nan
                if policy.variant.startswith("minimum_variance") or policy.variant == "equal_risk_contribution":
                    w, status, shrink, jitter = covariance_weights(data, origin, ids, v, "minimum_variance" if policy.variant.startswith("minimum_variance") else "equal_risk_contribution", 60 if policy.variant.endswith("60") else 30)
                if policy.satellite and N > 6 and not fallback:
                    core = risk_weights(v[:6], policy.p)
                    sat = risk_weights(v[6:], policy.p)
                    w = np.r_[core * (1 - policy.satellite), sat * policy.satellite]
                desired = w.copy()
                caps = np.ones(N)
                unknown = np.zeros(N, bool)
                if policy.branch == "capacity":
                    caps, unknown = capacity_limits(data, origin, basket, policy)
                    w = bounded_proportional(w, caps, 0.98) if policy.redistribute else np.minimum(caps, 0.98 * w)
                    benchmark = bounded_proportional(np.ones(N), caps, float(w.sum()))
                else:
                    benchmark = risk_weights(v, 0)
                a = data["date_index"][origin - pd.Timedelta(days=1)]
                jj = [data["id_index"][int(pid)] for pid in ids]
                for i, row in enumerate(basket.itertuples()):
                    allocations.append(dict(origin_at=origin, policy_id=policy.policy_id, pair_id=int(row.pair_id), rank=i + 1, tier=row.tier, score_value=row.score, desired_weight=float(desired[i]), accepted_weight=float(w[i]), benchmark_weight=float(benchmark[i]), cash=float(1 - w.sum()), units=float(w[i] / data["arrays"]["nav"][a, jj[i]]), capacity=float(caps[i]), unknown_state=bool(unknown[i]), status=status, shrinkage=shrink, jitter=jitter, phase=phase))
                if phase == 0:
                    prev = previous.get(policy.policy_id)
                    current = {int(pid): float(x) for pid, x in zip(ids, w)}
                    current[-1] = float(1 - w.sum())
                    if prev and origin - prev[0] == pd.Timedelta(days=4):
                        old = prev[1]
                        names = set(current) | set(old)
                        newset = set(ids)
                        oldset = set(old) - {-1}
                        stability.append(dict(origin_at=origin, policy_id=policy.policy_id, jaccard=len(newset & oldset) / len(newset | oldset) if newset | oldset else 1, total_variation=0.5 * sum(abs(current.get(pid, 0) - old.get(pid, 0)) for pid in names)))
                    previous[policy.policy_id] = (origin, current)
                for h in eligible_targets:
                    target = future_panel(data, origin, h, ids)
                    metrics = outcome_metrics(target, w, v)
                    covariance_forecast = np.nan
                    if policy.variant.startswith("minimum_variance") or policy.variant == "equal_risk_contribution":
                        cov = data.get("_covariance_cache", {}).get((origin, tuple(map(int, ids)), 60 if policy.variant.endswith("60") else 30))
                        if cov is not None:
                            covariance_forecast = float(w @ cov @ w)
                    metrics["covariance_forecast_variance"] = covariance_forecast
                    base = outcome_metrics(target, benchmark, v)
                    eq = outcome_metrics(target, risk_weights(v, 0), v)
                    universe = eligible_targets[h]
                    ureturn = float(np.mean(universe["returns"])) if len(ids_all) and universe["supported"].all() else np.nan
                    weighting = metrics["return"] - base["return"]
                    selection = eq["return"] - ureturn if policy.branch == "pure" else np.nan
                    first = metrics["first_update"] - base["first_update"]
                    remaining = metrics["remaining"] - base["remaining"]
                    assert not np.isfinite(weighting) or not np.isfinite(first) or np.isclose(weighting, first + remaining, atol=1e-10)
                    if policy.branch == "pure" and metrics["resolved"] and N:
                        check = N * np.mean((w - 1 / N) * (target["returns"] - np.mean(target["returns"])))
                        assert np.isclose(weighting, check, atol=1e-10)
                    boundary_score = basket.score.iloc[-1] if N else np.nan
                    boundary_tie = int((candidates.score == boundary_score).sum()) if np.isfinite(boundary_score) else int(candidates.score.isna().sum())
                    contrast_lower, contrast_upper = signed_return_bounds(w - benchmark, target["returns"], target["supported"])
                    unknown_active = (w - benchmark)[~target["supported"]]
                    known_active = float(np.nansum((w - benchmark) * target["returns"]))
                    coef = float(unknown_active.sum())
                    outcomes.append(
                        dict(
                            origin_at=origin,
                            policy_id=policy.policy_id,
                            h=h,
                            phase=phase,
                            N_actual=N,
                            risk_fallback_equal=fallback or status == "risk_fallback_equal",
                            unscored_selected=int(basket.score.isna().sum()),
                            boundary_tie=boundary_tie,
                            label_end=target.get("label_end", origin + pd.Timedelta(days=h - 1)),
                            label_available_at=target.get("label_available_at", origin + pd.Timedelta(days=h)),
                            **metrics,
                            weighting_lift=weighting,
                            variance_lift=metrics["variance"] - base["variance"],
                            drawdown_lift=metrics["drawdown"] - base["drawdown"],
                            selection_lift=selection,
                            total_lift=selection + weighting,
                            universe_supported=bool(len(ids_all) and universe["supported"].all()),
                            universe_return=ureturn,
                            benchmark_return=base["return"],
                            benchmark_variance=base["variance"],
                            first_update_lift=first,
                            remaining_lift=remaining,
                            missing_active_coefficient=coef,
                            known_active_contribution=known_active,
                            break_even_missing_return=-known_active / coef if coef != 0 else np.nan,
                            contrast_lower=contrast_lower,
                            contrast_upper=contrast_upper,
                            conditional_active=not fallback and status != "risk_fallback_equal",
                        )
                    )
    result = {"allocations": pd.DataFrame(allocations), "outcomes": pd.DataFrame(outcomes), "ranks": pd.DataFrame(rank_rows), "risk_evaluation": pd.DataFrame(risk_rows), "score_ic": pd.DataFrame(ic_rows), "population": pd.DataFrame(population), "stability": pd.DataFrame(stability), "policies": policies}
    for name, frame in result.items():
        frame.to_parquet(ARTIFACT / f"{name}.parquet", index=False)
    return result


def signed_return_bounds(active_weights, returns, supported):
    """Propagate nonnegative NAV bounds through signed portfolio differences."""
    active = np.asarray(active_weights, float)
    returns = np.asarray(returns, float)
    supported = np.asarray(supported, bool)
    known = float(np.dot(active[supported], returns[supported]))
    unknown = active[~supported]
    lower = -np.inf if np.any(unknown < 0) else known - float(unknown[unknown > 0].sum())
    upper = np.inf if np.any(unknown > 0) else known - float(unknown[unknown < 0].sum())
    return lower, upper
