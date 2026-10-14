"""Sizing maps before the unchanged NB10 capacity projection."""

import numpy as np
from portfolio_snapshot_construction import risk_weights
from portfolio_score_allocation import project


def requested(policy, risk, component):
    """Return normalised weights, risk forecasts and explicit fallback status."""
    ids = component.index
    method = policy["method"]

    def get(estimator, L, kappa):
        return risk[(risk.estimator == estimator) & (risk.L == L) & (risk.kappa == kappa)].set_index("pair_id").reindex(ids)

    if method == "equal":
        return np.full(len(ids), 1 / len(ids)), np.full(len(ids), np.nan), "equal_control"
    if method == "T18":
        x = component[["Sh90", "Ca180", "V180", "Kmax"]].fillna(0).min(axis=1).to_numpy(float)
        if x.sum() <= 0:
            return np.full(len(ids), 1 / len(ids)), np.full(len(ids), np.nan), "all_zero_equal"
        return x / x.sum(), np.full(len(ids), np.nan), "minimum_score"
    if method in ("median", "maximum"):
        forecasts = np.column_stack([get("regular", L, 30).predicted.to_numpy(float) for L in (45, 90, 180)])
        v = np.median(forecasts, axis=1) if method == "median" else np.max(forecasts, axis=1)
        invalid = ~(np.isfinite(forecasts) & (forecasts > 0)).all(axis=1)
        v[invalid] = np.nan
    else:
        est = "regular" if method in ("bounded_I", "bounded_V") else method
        r = get(est, policy["L"], policy["kappa"])
        v = r.predicted.to_numpy(float)
        if method in ("bounded_I", "bounded_V"):
            prior = r.prior.to_numpy(float)
            valid = np.isfinite(v) & (v > 0) & np.isfinite(prior) & (prior > 0)
            if not valid.all():
                return np.full(len(ids), 1 / len(ids)), v, "risk_unavailable_equal"
            x = prior / (v + prior) if method == "bounded_I" else np.sqrt(prior) / (np.sqrt(v) + np.sqrt(prior))
            return x / x.sum(), v, "bounded_score"
    valid = np.isfinite(v) & (v > 0)
    return risk_weights(v, policy["p"]), v, "risk_power" if valid.all() else "risk_unavailable_equal"


def allocate(data, origin, basket, policy, risk, components):
    desired, v, status = requested(policy, risk, components)
    accepted, caps, unknown = project(data, origin, basket, desired, "C")
    B = accepted.sum()
    shadow = B * desired
    return dict(desired=desired, variances=v, status=status, accepted=accepted, caps=caps, unknown=unknown, shadow=shadow, distortion=float(np.abs(accepted - shadow).sum()), cash=1 - B)
