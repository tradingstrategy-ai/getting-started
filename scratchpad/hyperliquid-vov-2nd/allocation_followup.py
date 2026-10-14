"""Registered NB11 sensitivity and constrained allocation follow-up for NB12."""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sizing_study_design import ROOT, GENERATION, START, END, PERIOD, main_registry, followups, canonical
from sizing_study_data import read_inputs, freeze_baskets, build_risk
from sizing_study_allocation import allocate as original_allocate
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast
from portfolio_snapshot_construction import bounded_proportional, covariance_weights
from portfolio_snapshot_data import CONFIG
from portfolio_score_allocation import project

REFERENCE11 = GENERATION / "11/main/b64b9738eff5af379f16d62b65e0147ce2ee4ab8143505b6fb42c864e37f161c"


def registry():
    """Execute precisely 20 new policies and ten mechanism/benchmark controls."""
    base = [p for p in main_registry() if p["arm"] in ("S01", "S02", "S03", "S04", "S15", "S16", "S17", "S18", "M39", "M40")]
    f = followups()
    for p in f["sensitivities"]:
        p.pop("status")
    for p in f["cap_aware"]:
        p.update(method="cap_" + p["method"], p=1.0, floor=None, label=f"{p['selector']}:{p['target']} / {p['method']}", status="executed_on_run", budget=0.98, budget_definition="min(0.98,sum(positive_target_caps))")
    result = base + f["sensitivities"] + f["cap_aware"]
    assert len(result) == 30 and len({p["arm"] for p in result}) == 30
    return result


def initialise():
    """Pin unchanged NB11 inputs and separate generated outputs."""
    data = read_inputs()
    policies = registry()
    identity = dict(version="12-followup-v1", policies=policies, downloads=data["downloads"], reference=hashlib.sha256((REFERENCE11 / "manifest.json").read_bytes()).hexdigest(), code={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob("*followup*.py"))}, inherited_code={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob("sizing_study_*.py"))})
    key = hashlib.sha256(canonical(identity).encode()).hexdigest()
    folder = GENERATION / "12" / key
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=key, stage="registered follow-up", solver_diagnostics=[])
    (folder / "manifest.json").write_text(json.dumps(dict(identity=identity, fingerprint=key, period=PERIOD, warmup="All available 2025 and earlier history retained", framework=data["framework_commits"]), indent=2))
    return data, policies


def risk_at(data, t, ids, L=90, kappa=30, floor=1e-8, estimator="regular"):
    """Causal peer pool over the eligible universe, including selected incumbents."""
    a = data["date_index"][pd.Timestamp(t) - pd.Timedelta(days=1)]
    e = data["eligibility"]
    pool = e.loc[e.origin_at.eq(t) & e.eligible_as_of_origin, "pair_id"].to_numpy(int)
    pool = np.unique(np.r_[pool, np.asarray(ids, int)])
    jj = [data["id_index"][int(pid)] for pid in pool]
    vals = [empirical_window(data["arrays"]["nav"][max(0, a - L) : a + 1, j], data["arrays"]["actual"][max(0, a - L) : a + 1, j], L) for j in jj]
    emp = np.array([v["empirical"] for v in vals])
    full = np.array([v["full"] for v in vals])
    rows = []
    for i, (pid, v) in enumerate(zip(pool, vals)):
        prior, count, poolname, disp = peer_prior(emp, full, i)
        pred = forecast(emp[i], prior, v["m"], "raw" if estimator == "raw" else "regularised", kappa, floor)
        rows.append(dict(origin_at=t, pair_id=int(pid), estimator=estimator, units="simple", L=L, kappa=kappa, **v, prior=prior, prior_count=count, prior_pool=poolname, prior_dispersion=disp, predicted=pred, weak_prior=count < 5, prior_only=not np.isfinite(emp[i]), floor_active=bool(estimator == "raw" and pred == floor), shrinkage=v["m"] / (v["m"] + kappa) if np.isfinite(emp[i]) else 0, anchor_age=float((t.to_datetime64() - data["arrays"]["last_observed"][a, data["id_index"][int(pid)]]) / np.timedelta64(1, "D")), history_age=a - data["first_index"][data["id_index"][int(pid)]], actual_fraction=v["m"] / L))
    return pd.DataFrame(rows)


def build_followup_risk(data, baskets):
    """Preserve reference risk tensors and add the two windows/prior strengths."""
    base, _ = build_risk(data)
    parts = [base]
    for t in data["origins"]:
        ids = baskets.loc[baskets.origin_at.eq(t), "pair_id"].unique()
        for L, k in ((75, 30), (105, 30), (90, 10), (90, 90)):
            parts.append(risk_at(data, t, ids, L, k))
    return pd.concat(parts, ignore_index=True)


def covariance(data, t, ids, v):
    """Inherited Ledoit–Wolf correlation and explicitly inherited conditioning."""
    _, status, shrink, jitter = covariance_weights(data, t, ids, v, "equal_risk_contribution", CONFIG["covariance_min_returns"])
    raw = data["_covariance_cache"][(t, tuple(map(int, ids)), CONFIG["covariance_min_returns"])].copy()
    C = raw / np.diag(raw).mean()
    minimum = np.linalg.eigvalsh(C).min()
    conditioning = CONFIG["numerical_jitter_relative"] if minimum <= 0 else 0.0
    C += conditioning * np.eye(len(C))
    return C, dict(covariance_status=status, correlation_shrinkage=shrink, conditioning=conditioning, min_eigenvalue=float(np.linalg.eigvalsh(C).min()))


def solve_budget(C, b, caps, B):
    """Return both allocations from the same covariance, support and budget."""
    C = np.asarray(C, float)
    C = C / np.diag(C).mean()
    b = np.asarray(b, float)
    caps = np.asarray(caps, float)
    b = b / b.sum()
    B = min(float(B), float(caps.sum()))
    n = len(b)
    objective = lambda w, lam: 0.5 * w @ C @ w - lam * np.dot(b, np.log(w))
    if B <= 0:
        return np.zeros(n), np.zeros(n), dict(status="all_cash", objective_gain=0.0, kkt=0.0, rc_error=0.0)
    if n == 1:
        w = np.array([B])
        return w, w.copy(), dict(status="singleton", objective_gain=0.0, kkt=0.0, rc_error=0.0)
    x0 = np.sqrt(b / np.diag(C))
    opt = minimize(lambda x: 0.5 * x @ C @ x - np.dot(b, np.log(x)), x0, jac=lambda x: C @ x - b / x, bounds=[(CONFIG["positive_solver_bound"], None)] * n, method="L-BFGS-B", options={"ftol": CONFIG["erc_objective_tolerance"], "gtol": CONFIG["solver_tolerance"], "maxiter": CONFIG["solver_iterations"]})
    w0 = B * opt.x / opt.x.sum()
    rc = w0 * (C @ w0) / (w0 @ C @ w0)
    err = float(np.max(np.abs(rc - b)))
    projected = bounded_proportional(w0, caps, B)
    lam = float(w0 @ C @ w0)
    if not opt.success or err > CONFIG["risk_contribution_tolerance"]:
        return projected, projected.copy(), dict(status="unconstrained_failed_projected_fallback", objective_gain=0.0, kkt=np.nan, rc_error=err)
    if np.all(w0 <= caps + 1e-10):
        return projected, projected.copy(), dict(status="no_binding_caps", objective_gain=0.0, kkt=0.0, rc_error=err)
    if np.isclose(caps.sum(), B, atol=1e-12, rtol=0):
        w = caps.copy()
        return projected, w, dict(status="all_caps_bound", objective_gain=float(objective(projected, lam) - objective(w, lam)), kkt=0.0, rc_error=err)
    solve = minimize(lambda w: objective(w, lam), projected, jac=lambda w: C @ w - lam * b / w, bounds=[(CONFIG["positive_solver_bound"], float(c)) for c in caps], constraints=[{"type": "eq", "fun": lambda w: w.sum() - B, "jac": lambda w: np.ones(n)}], method="SLSQP", options={"ftol": 1e-12, "maxiter": CONFIG["solver_iterations"]})
    w = solve.x
    grad = C @ w - lam * b / w
    free = w < caps - 1e-8
    nu = -float(np.median(grad[free])) if free.any() else -float(np.min(grad))
    residual = grad + nu
    kkt = max(float(np.max(np.abs(residual[free]))) if free.any() else 0.0, float(np.maximum(residual[~free], 0).max()) if (~free).any() else 0.0)
    gain = float(objective(projected, lam) - objective(w, lam))
    feasible = abs(w.sum() - B) < 1e-9 and np.all(w > 0) and np.all(w <= caps + 1e-10)
    good = solve.success and feasible and gain >= -1e-9 and kkt < 1e-5
    return projected, w if good else projected.copy(), dict(status="solved" if good else "constrained_failed_projected_fallback", objective_gain=gain, kkt=kkt, rc_error=err, solver_message=solve.message, lambda_value=lam, constrained_rc_error=float(np.max(np.abs(w * (C @ w) / (w @ C @ w) - b))))


def cap_allocate(data, t, ids, v, scores, caps, target):
    """Keep zero score targets at zero; both methods use identical support."""
    scores = np.nan_to_num(np.asarray(scores, float), nan=0.0)
    b = np.ones(len(ids)) if target == "equal_risk" else np.maximum(scores, 0)
    zero_fallback = not np.any((b > 0) & (caps > 0))
    if zero_fallback:
        b = np.ones(len(ids))
    active = (b > 0) & (caps > 0)
    S = np.flatnonzero(active)
    out = np.zeros(len(ids))
    desired = out.copy()
    B = min(0.98, float(caps[active].sum()))
    if not len(S):
        return out, out.copy(), desired, dict(status="all_cash", excluded_target_mass=float(b[~active].sum()), objective_gain=0.0, kkt=0.0)
    bb = b[S] / b[S].sum()
    vv = np.asarray(v)[S]
    diagnostic = dict(excluded_target_mass=float(b[~active].sum()), all_zero_target_fallback=zero_fallback)
    if not (np.isfinite(vv) & (vv > 0)).all():
        desired[S] = bb
        out = bounded_proportional(desired, caps, B)
        return out, out.copy(), desired, dict(diagnostic, status="missing_risk_projected_fallback", objective_gain=0.0, kkt=np.nan)
    C, cd = covariance(data, t, np.asarray(ids)[S], vv)
    projected, constrained, sd = solve_budget(C, bb, caps[S], B)
    out[S] = projected
    new = out.copy()
    new[S] = constrained
    # The uncapped risk target is separately solved with non-binding unit capacities.
    uncap, _, _ = solve_budget(C, bb, np.full(len(S), B), B)
    desired[S] = uncap / B
    return out, new, desired, dict(diagnostic, **cd, **sd, accepted_L1_difference=float(np.abs(new - out).sum()), budget=B)


def allocate(data, t, basket, p, risk, components):
    """Intervene only in the registered estimator or cap-aware objective."""
    if p["method"].startswith("cap_"):
        ids = basket.pair_id.to_numpy(int)
        r = risk[(risk.estimator == "regular") & (risk.L == 90) & (risk.kappa == 30)].set_index("pair_id").reindex(ids)
        _, caps, unknown = project(data, t, basket, np.ones(len(ids)) / len(ids), "C")
        projected, new, u, diag = cap_allocate(data, t, ids, r.predicted.to_numpy(), basket.score.to_numpy(), caps, p["target"])
        w = new if p["method"] == "cap_constrained_convex" else projected
        data["solver_diagnostics"].append(dict(origin_at=t, arm=p["arm"], **diag))
        return dict(desired=u, variances=r.predicted.to_numpy(), status=diag["status"], accepted=w, caps=caps, unknown=unknown, shadow=w.sum() * u, distortion=float(np.abs(w - w.sum() * u).sum()), cash=1 - w.sum())
    if p["method"] == "raw" and p.get("floor") != 1e-8:
        risk = risk.copy()
        mask = (risk.estimator == "raw") & (risk.L == 90) & (risk.kappa == 30)
        for ix, row in risk[mask].iterrows():
            risk.loc[ix, "predicted"] = forecast(row.empirical, row.prior, row.m, "raw", 30, p["floor"])
    return original_allocate(data, t, basket, p, risk, components)


def fixtures():
    """Independent algebra, cap feasibility, scaling and missing-risk examples."""
    checks = []

    def check(name, ok):
        assert bool(ok), name
        checks.append(dict(check=name, passed=True))

    C = np.diag([1.0, 4.0, 9.0])
    b = np.ones(3) / 3
    B = 0.98
    w, new, d = solve_budget(C, b, np.ones(3), B)
    expected = B * np.array([1.0, 0.5, 1 / 3]) / sum([1.0, 0.5, 1 / 3])
    check("Unconstrained diagonal equal risk is inverse volatility", np.allclose(w, expected, atol=1e-6))
    check("Non-binding caps reproduce projected allocation", np.allclose(w, new, atol=1e-9))
    caps = np.array([0.2, 0.6, 0.6])
    w, new, d = solve_budget(C, b, caps, B)
    check("Binding cap objective improves", d["status"] == "solved" and d["objective_gain"] > 0)
    check("Binding cap feasibility and KKT", abs(new.sum() - B) < 1e-9 and np.all(new <= caps) and d["kkt"] < 1e-5)
    _, scaled, _ = solve_budget(C * 100, b, caps, B)
    check("Covariance scale invariance", np.allclose(new, scaled, atol=1e-6))
    qp = minimize(lambda x: x @ C @ x, np.full(3, B / 3), jac=lambda x: 2 * C @ x, bounds=list(zip(np.zeros(3), caps)), constraints=[{"type": "eq", "fun": lambda x: x.sum() - B}], method="SLSQP", options={"ftol": 1e-12})
    check("Diagonal minimum variance matches inverse variance water-fill", np.allclose(qp.x, bounded_proportional(1 / np.diag(C), caps, B), atol=1e-6))
    check("Missing empirical variance uses prior", forecast(np.nan, 0.04, 0, "regularised", 30) == 0.04)
    check("Zero empirical variance stays distinct from missing", np.isclose(forecast(0, 0.04, 30, "regularised", 30), 0.02))
    check("Raw floor sensitivities use declared floor", forecast(0, 0.04, 2, "raw", 30, 1e-6) == 1e-6)
    check("Young partial histories remain measurable", np.isfinite(empirical_window([np.nan, 1, 1.1, 1.05], [0, 1, 1, 1], 3)["empirical"]))
    w, new, d = solve_budget(np.eye(2), np.ones(2), np.array([0.1, 0.2]), 0.3)
    check("All-capacity-bound solution", np.allclose(new, [0.1, 0.2]))
    engine_caps = np.array([0.2, 0.4, 0.5])
    proj, con, _ = solve_budget(C, b, 0.98 * engine_caps, 0.98)
    check("Deployable-budget unit conversion preserves engine caps", np.all(proj / 0.98 <= engine_caps + 1e-10) and np.all(con / 0.98 <= engine_caps + 1e-10) and np.isclose(con.sum() / 0.98, 1.0))
    check("Registry exactly 12 plus eight new combinations", sum(p["arm"].startswith("X") for p in registry()) == 12 and sum(p["arm"].startswith("C") for p in registry()) == 8)
    return pd.DataFrame(checks)


def run_snapshots(data, policies):
    """Reuse NB11 target semantics, with reference controls checked in place."""
    import sizing_study_analysis as analysis

    baskets = freeze_baskets(data)
    risk = build_followup_risk(data, baskets)
    old = analysis.allocate
    analysis.allocate = allocate
    try:
        result = analysis.execute(data, baskets, risk, policies, [7, 30, 90])
    finally:
        analysis.allocate = old
    # A proportional re-projection is not the constrained optimiser's counterfactual.
    mask = result["contrasts"].arm.str.startswith("C")
    result["contrasts"].loc[mask, "common_budget_difference"] = np.nan
    result["contrasts"].loc[mask, "common_budget_paired"] = 0
    result["contrast_dates"].loc[result["contrast_dates"].arm.str.startswith("C"), "common_budget_difference"] = np.nan
    for name in ("contrasts", "contrast_dates"):
        result[name].to_parquet(data["artifact"] / f"{name}.parquet", index=False)
    diagnostics = pd.DataFrame(data["solver_diagnostics"])
    diagnostics.to_parquet(data["artifact"] / "solver_diagnostics.parquet", index=False)
    olda = pd.read_parquet(REFERENCE11 / "allocations.parquet")
    oldo = pd.read_parquet(REFERENCE11 / "outcomes.parquet")
    checks = []
    for arm in [p["arm"] for p in policies if p["arm"].startswith(("S", "M"))]:
        a = result["allocations"].query("arm == @arm").merge(olda.query("arm == @arm"), on=["origin_at", "pair_id"], suffixes=("_new", "_old"), validate="one_to_one")
        o = result["outcomes"].query("arm == @arm").merge(oldo.query("arm == @arm"), on=["origin_at", "h"], suffixes=("_new", "_old"), validate="one_to_one")
        ok = np.allclose(a.accepted_weight_new, a.accepted_weight_old, atol=1e-12, rtol=0) and np.allclose(o["return_new"], o["return_old"], atol=1e-12, rtol=0, equal_nan=True)
        assert ok, arm
        checks.append(dict(check=f"{arm}: NB11 weights and all horizon outcomes", passed=ok))
    a = result["allocations"]
    check = np.all(a.accepted_weight <= a.capacity + 1e-10) and np.all(a.accepted_weight >= 0)
    assert check
    checks.append(dict(check="All capacities and non-negative weights", passed=True))
    # Require equal budgets inside every constrained/projected risk-target pair.
    totals = a.groupby(["origin_at", "arm"]).accepted_weight.sum().unstack()
    for i in (1, 3, 5, 7):
        assert np.allclose(totals[f"C{i:02d}"], totals[f"C{i+1:02d}"], atol=1e-10)
    checks.append(dict(check="All four cap-aware pairs share budgets", passed=True))
    check = not diagnostics.status.str.contains("failed").any()
    assert check, diagnostics[diagnostics.status.str.contains("failed")]
    checks.append(dict(check="All cap solvers succeed or use explicit analytical solutions", passed=True))
    result["solver_diagnostics"] = diagnostics
    result["checks"] = pd.DataFrame(checks)
    result["checks"].to_parquet(data["artifact"] / "audit.parquet", index=False)
    (data["artifact"] / "execution.json").write_text(json.dumps(dict(status="complete", policies=30, new_policies=20, origins=70, targets=6300, checks=len(checks)), indent=2))
    return result
