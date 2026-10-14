"""Frozen experiment 11 policy registries and full-2026 calendar."""

import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
GENERATION = ROOT / "_artifacts-restored-2026-10-07"
START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-10-05")
PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
VERSION = "11-sizing-v1"
REFERENCE = GENERATION / "10-expanded/smoke/0d3861e02592ca8f484c54cc3dec9d29865911000cb43a37f1f9ce31bd0c6f03"
SELECTORS = {"F": "focal_four", "L": "v11"}


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), default=str)


def policy(selector, method, L=90, p=2.0, kappa=30.0, floor=1e-8):
    body = dict(selector=selector, method=method, L=int(L), p=float(p), kappa=float(kappa), floor=float(floor) if method == "raw" else None, N=6, missing="frozen_unscored_tier", fallback="whole_basket_equal", projection="bounded_proportional", state="source_report_only", account=150000, budget=0.98, concentration=0.33, tvl_fraction=0.33, tvl_carry_days=2)
    key = hashlib.sha256(canonical(body).encode()).hexdigest()[:16]
    name = f"{selector}:{method}" + (f" L{L}/p{p:g}/κ{kappa:g}" if method in ("regular", "raw", "calendar_log", "gap_log") else "")
    return dict(policy_id=key, label=name, **body)


def smoke_registry():
    configs = [("equal", 90, 0, 30), ("regular", 90, 2, 30), ("regular", 45, 1, 30), ("regular", 180, 1.5, 30), ("raw", 90, 2, 30), ("bounded_I", 90, 2, 30), ("source", 90, 2, 30)]
    rows = [policy(s, m, L, p, k) for m, L, p, k in configs for s in SELECTORS]
    rows += [policy("L", "bounded_V", 180, 1, 60), policy("L", "T18"), policy("F", "calendar_log"), policy("F", "gap_log")]
    return [dict(arm=f"S{i+1:02d}", **r) for i, r in enumerate(rows)]


def main_registry():
    rows = smoke_registry()
    seen = {r["policy_id"] for r in rows}
    extras = [policy(s, "regular", L, p) for s in SELECTORS for L in (45, 90, 180) for p in (1, 1.5, 2)]
    extras += [policy(s, "regular", L, 2, L / 3) for s in SELECTORS for L in (45, 180)]
    extras += [policy(s, m) for s in SELECTORS for m in ("median", "maximum", "calendar_log", "gap_log")]
    for r in extras:
        if r["policy_id"] not in seen:
            rows.append(dict(arm=f"M{len(rows)+1:02d}", **r))
            seen.add(r["policy_id"])
    assert len(rows) == 40 and len(seen) == 40
    return rows


def followups():
    sensitivity = [policy(s, "regular", L) for s in SELECTORS for L in (75, 105)]
    sensitivity += [policy(s, "regular", 90, 2, k) for s in SELECTORS for k in (10, 90)]
    sensitivity += [policy(s, "raw", 90, 2, 30, f) for s in SELECTORS for f in (1e-10, 1e-6)]
    caps = [dict(selector=s, target=t, method=m, N=6, L=90, kappa=30, covariance="inherited_Ledoit_Wolf_correlation_identity_fallback", objective="0.5*w.T*C*w - lambda*sum(b*log(w)); lambda=w0.T*C*w0", budget="min(0.98,sum(positive_target_caps))", status="registered_not_executed") for s in SELECTORS for t in ("equal_risk", "frozen_score_risk") for m in ("projected", "constrained_convex")]
    for i, r in enumerate(caps):
        r["policy_id"] = hashlib.sha256(canonical(r).encode()).hexdigest()[:16]
        r["arm"] = f"C{i+1:02d}"
    return dict(sensitivities=[dict(arm=f"X{i+1:02d}", status="registered_not_executed", **r) for i, r in enumerate(sensitivity)], cap_aware=caps, placebo_status="deferred: persistent assignment and trial count not registered")


def primary_pairs(policies):
    pairs = []
    for s in SELECTORS:
        baseline = next(r for r in policies if r["selector"] == s and r["method"] == "regular" and r["L"] == 90 and r["p"] == 2 and r["kappa"] == 30)
        for r in policies:
            if r["selector"] == s and r["method"] == "regular" and r["kappa"] == 30 and r["policy_id"] != baseline["policy_id"]:
                pairs.append((r["arm"], baseline["arm"], "primary"))
    pairs.append(("S16", "S15", "primary"))
    assert len(pairs) == 17
    return pairs
