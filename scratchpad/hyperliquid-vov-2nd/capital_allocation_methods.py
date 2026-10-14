"""Explicit decision-time target rules for experiment 17."""

import time
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

METHODS = {"M00": "Exact C-W benchmark", "M01": "Admission-aware risk waterfall", "M02": "Proportional capped risk", "M03": "Score-priority waterfall", "M04": "Core + two score-first overflow", "M05": "Core + four score-first overflow", "M06": "Core + four scored-only overflow", "M07": "Capacity-aware incumbent retention", "M08": "Greedy score-dollar basket", "M09": "Maintained / fee-aware overflow", "M10": "One-decision rank-exit confirmation", "M11": "Joint six-slot score optimiser", "M12": "Legacy capacity extension", "M13": "Fixed ten-name core"}
ARMS = tuple(METHODS)
OVERFLOW = {"M04": 2, "M05": 4, "M06": 4, "M09": 4}
LIMITS = {a: 8 if a == "M04" else 10 if a in ("M05", "M06", "M09", "M12", "M13") else 6 for a in ARMS}
NUMERICAL = {"dollar_tolerance": 1e-6, "objective_tolerance": 1e-10, "mip_rel_gap": 1e-8, "time_limit": 30.0}


def waterfall(ids, cap, priority, budget, address):
    """Allocate bounded dollars in deterministic priority order."""
    out = {i: 0.0 for i in ids}
    left = max(float(budget), 0.0)
    for i in sorted(ids, key=lambda i: (-priority[i], address[i])):
        out[i] = min(max(cap[i], 0.0), left)
        left = max(0.0, left - out[i])
    return out


def proportional(ids, cap, raw, budget):
    """Water-fill proportional weights until budget or every ceiling binds."""
    out = {i: 0.0 for i in ids}
    active = set(ids)
    left = min(max(budget, 0.0), sum(cap[i] for i in ids))
    while active and left > 0:
        total = sum(raw[i] for i in active)
        proposed = {i: left * (raw[i] / total if total > 0 else 1 / len(active)) for i in active}
        saturated = [i for i in active if proposed[i] >= cap[i]]
        if not saturated:
            out.update(proposed)
            break
        for i in saturated:
            out[i] = cap[i]
            left = max(0.0, left - cap[i])
            active.remove(i)
    return out


def score_lp(ids, cap, score, old, budget, address):
    """Solve the fixed-basket positive-score fill with minimum-turnover ties."""
    out = {i: 0.0 for i in ids}
    left = max(budget, 0.0)
    groups = {}
    for i in ids:
        groups.setdefault(score[i], []).append(i)
    for s, group in sorted(groups.items(), reverse=True):
        group = sorted(group, key=lambda i: address[i])
        D = min(left, sum(cap[i] for i in group))
        held = {i: min(old[i], cap[i]) for i in group}
        if s == 0:
            D = min(D, sum(held.values()))
        remaining = D
        for i in group:
            out[i] = min(held[i], remaining)
            remaining -= out[i]
        for i in group:
            extra = min(cap[i] - out[i], remaining)
            out[i] += extra
            remaining -= extra
        left = max(0.0, left - D)
    return out


def floors(ids, allocate, cap, old, buy, epsilon):
    """Remove non-executable entries/close-weight dust and refill survivors."""
    active = list(ids)
    removed = []
    for _ in range(len(ids) + 1):
        out = allocate(active)
        total = sum(out.values())
        bad = [i for i in active if out[i] > 0 and (out[i] < epsilon * total - 1e-8 or (old[i] == 0 and out[i] < buy - 1e-8))]
        if not bad:
            return out, removed
        removed.extend(bad)
        active = [i for i in active if i not in bad]
    raise RuntimeError("Target floor pass did not converge")


def joint(ids, cap, score, old, budget, slots, buy, epsilon, address):
    """Optimise score dollars, then turnover and cardinality, with explicit floors."""
    start = time.monotonic()
    ids = sorted([i for i in ids if cap[i] > 0 and (old[i] > 0 or cap[i] >= buy)], key=lambda i: address[i])
    n = len(ids)
    diag = {"Status": "all_cash", "Stages": 0, "Runtime": 0.0, "Gap": 0.0, "Objective": 0.0}
    if not n or budget <= 0 or slots <= 0:
        return {}, diag
    c = np.array([cap[i] / budget for i in ids])
    s = np.array([score[i] for i in ids])
    h = np.array([old[i] / budget for i in ids])
    # Variables are target fractions, binary membership and absolute turnover.
    rows = []
    lo = []
    hi = []

    def row(a, l=-np.inf, u=np.inf):
        rows.append(a)
        lo.append(l)
        hi.append(u)

    v = np.zeros(3 * n)
    v[:n] = 1
    row(v, u=1)
    v = np.zeros(3 * n)
    v[n : 2 * n] = 1
    row(v, u=slots)
    for k, i in enumerate(ids):
        v = np.zeros(3 * n)
        v[k] = 1
        v[n + k] = -c[k]
        row(v, u=0)
        if old[i] == 0:
            v = np.zeros(3 * n)
            v[k] = -1
            v[n + k] = buy / budget
            row(v, u=0)
        v = np.zeros(3 * n)
        v[:n] = epsilon
        v[k] -= 1
        v[n + k] = 1
        row(v, u=1)
        v = np.zeros(3 * n)
        v[k] = 1
        v[2 * n + k] = -1
        row(v, u=h[k])
        v = np.zeros(3 * n)
        v[k] = -1
        v[2 * n + k] = -1
        row(v, u=-h[k])
    bounds = Bounds(np.zeros(3 * n), np.r_[c, np.ones(n), np.maximum(h, c) + 1])
    integer = np.r_[np.zeros(n), np.ones(n), np.zeros(n)]
    solution = None
    statuses = []
    objectives = [np.r_[-s, np.zeros(2 * n)], np.r_[np.zeros(2 * n), np.ones(n)], np.r_[np.zeros(n), np.ones(n), np.zeros(n)], np.r_[np.zeros(n), np.arange(1, n + 1) / (n + 1), np.zeros(n)]]
    for stage, obj in enumerate(objectives):
        remaining = NUMERICAL["time_limit"] - (time.monotonic() - start)
        if remaining <= 0:
            statuses.append("time_limit")
            break
        result = milp(obj, integrality=integer, bounds=bounds, constraints=LinearConstraint(np.array(rows), lo, hi), options={"time_limit": remaining, "mip_rel_gap": NUMERICAL["mip_rel_gap"]})
        statuses.append(str(result.message))
        if result.x is None:
            if solution is None:
                raise RuntimeError(f"No feasible joint solution: {result.message}")
            break
        solution = result.x
        diag.update(Stages=stage + 1, Gap=float(getattr(result, "mip_gap", np.nan) or 0.0))
        if result.status != 0:
            break
        row(obj, u=float(obj @ solution) + NUMERICAL["objective_tolerance"])
    x = np.maximum(solution[:n], 0.0) * budget
    # Restore bounds conservatively after the normalised solver's rounding.
    x = np.minimum(x, np.array([cap[i] for i in ids]))
    excess = max(0.0, float(x.sum()) - budget)
    for k in reversed(range(n)):
        take = min(x[k], excess)
        x[k] -= take
        excess -= take
    assert x.sum() <= budget + 1e-6 and (x >= 0).all()
    keep = x > 1e-6
    if keep.sum() > slots or np.any(x[keep] < epsilon * x.sum() - 1e-6) or any(x[k] > 1e-6 and old[i] == 0 and x[k] < buy - 1e-6 for k, i in enumerate(ids)):
        raise RuntimeError("Joint solution violates executable target domain")
    diag.update(Status=" / ".join(statuses), Runtime=time.monotonic() - start, Objective=float(s @ x / budget), Selected=int(keep.sum()))
    return {i: float(v) for i, v in zip(ids, x) if v > 1e-6}, diag


def mechanism_checks():
    """Check the reviewed algebra examples without a separate test suite."""
    ids = list(range(4))
    addr = {i: str(i) for i in ids}
    cap = dict(zip(ids, [20000.0, 33000.0, 33000.0, 33000.0]))
    raw = dict(zip(ids, [8.0, 4.0, 2.0, 1.0]))
    score = dict(zip(ids, [0.4, 0.9, 0.8, 0.7]))
    assert np.allclose(list(waterfall(ids, cap, raw, 100000, addr).values()), [20000, 33000, 33000, 14000])
    assert np.allclose(list(proportional(ids, cap, raw, 100000).values()), [20000, 33000, 31333.333333, 15666.666667])
    assert np.allclose(list(waterfall(ids, cap, score, 100000, addr).values()), [1000, 33000, 33000, 33000])
    old = {i: 0.0 for i in ids}
    lp = score_lp(ids, cap, score, old, 100000, addr)
    assert np.allclose(list(lp.values()), list(waterfall(ids, cap, score, 100000, addr).values()))
    ids = list(range(12))
    cap = {i: 33000.0 if i < 6 else 16000.0 for i in ids}
    score = {i: 0.5 if i < 6 else 0.99 for i in ids}
    old = {i: 0.0 for i in ids}
    addr = {i: f"{i:02}" for i in ids}
    x, d = joint(ids, cap, score, old, 100000.0, 6, 75.0, 0.005, addr)
    assert set(x) == set(range(6, 12)) and abs(d["Objective"] - 0.9504) < 1e-8
    return {"Algebra examples": 4, "Joint cardinality counterexample": True, "Checked joint objective": d["Objective"]}
