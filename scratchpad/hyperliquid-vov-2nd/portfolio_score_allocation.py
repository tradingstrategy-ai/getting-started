"""Score-to-dollar maps and covariance-aware score risk budgets."""

from types import SimpleNamespace
import numpy as np
from scipy.optimize import minimize
from portfolio_snapshot_data import CONFIG
from portfolio_snapshot_construction import bounded_proportional, capacity_limits, covariance_weights, risk_weights


def score_risk_budget(data, origin, ids, variances, budgets):
    """Solve positive target risk contributions; preserve zero-budget names."""
    b = np.asarray(budgets, float)
    positive = b > 0
    w = np.zeros(len(b))
    if not positive.any():
        return risk_weights(b, 0), "all_zero_equal", None, np.nan
    ii = np.flatnonzero(positive)
    v = np.asarray(variances, float)[ii]
    if not (np.isfinite(v) & (v > 0)).all():
        return b / b.sum(), "risk_budget_fallback_linear", None, np.nan
    active_ids = np.asarray(ids)[ii]
    _, cov_status, _, _ = covariance_weights(data, origin, active_ids, v, "equal_risk_contribution", CONFIG["covariance_min_returns"])
    covariance = data.get("_covariance_cache", {}).get((origin, tuple(map(int, active_ids)), CONFIG["covariance_min_returns"]))
    if covariance is None:
        return b / b.sum(), "risk_budget_fallback_linear", None, np.nan
    C = covariance / np.diag(covariance).mean()
    if np.linalg.eigvalsh(C).min() <= 0:
        C = C + CONFIG["numerical_jitter_relative"] * np.eye(len(C))
    target = b[ii] / b[ii].sum()
    x0 = np.sqrt(target / np.diag(C))
    solve = minimize(lambda x: 0.5 * x @ C @ x - np.dot(target, np.log(x)), x0, jac=lambda x: C @ x - target / x, bounds=[(CONFIG["positive_solver_bound"], None)] * len(ii), method="L-BFGS-B", options={"ftol": CONFIG["erc_objective_tolerance"], "gtol": CONFIG["solver_tolerance"], "maxiter": CONFIG["solver_iterations"]})
    solution = solve.x / solve.x.sum()
    rc = solution * (C @ solution)
    rc /= rc.sum()
    error = float(np.max(np.abs(rc - target)))
    if not solve.success or error > CONFIG["risk_contribution_tolerance"]:
        return b / b.sum(), "risk_budget_fallback_linear", None, error
    w[ii] = solution
    full = np.zeros((len(b), len(b)))
    full[np.ix_(ii, ii)] = C
    return w, "score_risk_budget_" + cov_status, full, error


def project(data, origin, basket, requested, constraints):
    """Apply shared source entry constraints only after score sizing."""
    if constraints == "P":
        return requested.copy(), np.ones(len(requested)), np.zeros(len(requested), bool)
    policy = SimpleNamespace(account=150000, cap=0.33, state="source_report_only")
    caps, unknown = capacity_limits(data, origin, basket, policy)
    return bounded_proportional(requested, caps, 0.98), caps, unknown
