"""Evaluate score expressions with explicit availability and imputation mass."""

import numpy as np
from portfolio_score_components import percentile


def evaluate(expr, components, missing="M0"):
    """Return numerical scores separately from their availability mask."""
    size = len(next(iter(components.values())))
    if isinstance(expr, (int, float)):
        return dict(value=np.full(size, float(expr)), available=np.ones(size, bool), mass=np.ones(size))
    if isinstance(expr, str):
        raw = np.asarray(components[expr], float)
        available = np.isfinite(raw)
        fill = 0.5 if missing == "MN" else 0.0
        return dict(value=np.where(available, raw, fill), available=available, mass=available.astype(float))
    children = [evaluate(a, components, missing) for a in expr["args"]]
    coefficients = np.asarray(expr["coefficients"] if expr.get("coefficients") is not None else np.full(len(children), 1 / len(children)), float)
    assert np.all(coefficients >= 0) and np.isclose(coefficients.sum(), 1)
    positive = coefficients > 0
    coefficients = coefficients[positive]
    values = np.vstack([c["value"] for c, k in zip(children, positive) if k])
    available = np.vstack([c["available"] for c, k in zip(children, positive) if k])
    masses = np.vstack([c["mass"] for c, k in zip(children, positive) if k])
    any_available = available.any(axis=0)
    weights = np.broadcast_to(coefficients[:, None], values.shape).copy()
    if missing == "MA":
        weights *= available
        total = weights.sum(axis=0)
        weights = np.divide(weights, total, out=np.zeros_like(weights), where=total > 0)
    if expr["op"] == "A":
        value = np.sum(weights * values, axis=0)
    elif expr["op"] == "G":
        # Zero coefficients contribute identity, and genuine positive-weight zeros remain zero.
        value = np.prod(np.power(values, weights), axis=0)
    elif expr["op"] == "Min":
        value = np.min(np.where(weights > 0, values, np.inf), axis=0)
        value[~np.isfinite(value)] = 0.5 if missing == "MN" else 0.0
    else:
        raise ValueError(expr["op"])
    value[~any_available] = 0.5 if missing == "MN" else 0.0
    return dict(value=value, available=any_available, mass=np.sum(coefficients[:, None] * masses, axis=0))


def sizing_values(score, map, missing="M0", q=2.0, beta=np.log(4)):
    """Map an eligible-universe weighting score before selection."""
    value = np.asarray(score["value"], float)
    available = score["available"]
    if map == "equal":
        return np.ones(len(value))
    if map in ("linear", "risk_budget"):
        return value.copy()
    if map == "power":
        return value**q
    if map == "softmax":
        return np.exp(beta * (value - value.max())) if len(value) else value.copy()
    if map == "percentile":
        out = percentile(np.where(available, value, np.nan))
        out[~available] = 0.0
        if missing == "MN":
            reference = value[available]
            out[~available] = (np.sum(reference < 0.5) + 0.5 * np.sum(reference == 0.5)) / len(reference) if len(reference) else 0.5
        return out
    raise ValueError(map)
