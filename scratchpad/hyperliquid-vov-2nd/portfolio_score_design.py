"""Explicit score policy registries for the expanded experiment 10."""

import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-10-05")
PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
VERSION = "10-score-smoke-v1"


def expression(op, *args, coefficients=None):
    """Build a canonical expression over metric components."""
    return {"op": op, "args": list(args), "coefficients": coefficients}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def recipe_id(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()[:20]


def label(value):
    if isinstance(value, str):
        return value
    if isinstance(value, (float, int)):
        return f"constant {value:g}"
    return value["op"] + "(" + ",".join(label(a) for a in value["args"]) + ")"


def smoke_registry():
    A = lambda *x: expression("A", *x)
    G = lambda *x: expression("G", *x)
    Min = lambda *x: expression("Min", *x)
    rows = []

    def add(R, Q, map="linear", N=6, missing="M0", constraints="C", purpose=""):
        row = dict(arm=f"T{len(rows):02d}", ranking=R, weighting=Q, sizing_map=map, N=N, missing=missing, constraints=constraints, purpose=purpose, all_zero_fallback="bounded_equal", solver_fallback="linear_score", q=2.0, beta=float(__import__("numpy").log(4)))
        row["ranking_recipe_id"] = recipe_id(R)
        row["weighting_recipe_id"] = recipe_id(Q)
        rows.append(row)

    add("L", "source90", "source", missing="Legacy", purpose="Exact source control")
    add("F", 1.0, "equal", purpose="Same-basket equal")
    add("F", "F", purpose="Frozen score sizing")
    add("F", "I90", purpose="Inverse variance component")
    add("F", "V90", purpose="Inverse volatility component")
    add("F", A("F", "I90"), purpose="Risk in sizing score")
    add(A("F", "I90"), 1.0, "equal", purpose="Risk in ranking only")
    add(A("F", "I90"), A("F", "I90"), purpose="Risk in both roles")
    add("F", A("F", "V90"), purpose="Inverse volatility blend")
    add("F", G("F", "I90"), purpose="Geometric agreement")
    add("F", A("F", "I90"), "power", purpose="Squared conviction")
    add("F", A("F", "I90"), "softmax", purpose="Softmax conviction")
    add("F", A("F", "I90"), "percentile", purpose="Ordering-based sizing")
    add("F", A("F", "I90", "K90"), purpose="K in sizing")
    add(A("F", "I90", "K90"), A("F", "I90", "K90"), purpose="Three-input joint score")
    add(A("F", "I90", "Kmax"), A("F", "I90", "Kmax"), purpose="Maximum-history K")
    add(A("F", "I90", "K360"), A("F", "I90", "K360"), purpose="Long fixed K")
    add("B", G("B", "I90", "K30+"), purpose="Positive K geometric blend")
    add("L", Min("Sh90", "Ca180", "V180", "Kmax"), purpose="Minimum and zero/fallback probe")
    add(A("C180", "So30", "K90"), A("I90", "Kmax", "D90"), purpose="Different ranking and sizing features")
    add(A("F", "I90", "K90"), A("F", "I90", "K90"), N=10, purpose="Breadth control")
    add(A("F", "I90", "K90"), A("F", "I90", "K90"), missing="MN", purpose="Neutral missingness")
    add(A("F", "I90", "K90"), A("F", "I90", "K90"), missing="MA", purpose="Available-component mean")
    add(A("F", "I90", "K90_conf"), A("F", "I90", "K90_conf"), purpose="K support confidence")
    add("F", A("F", "I90", "K90"), "risk_budget", purpose="Score risk contributions")
    add(A("F", "I90", "K90"), A("F", "I90", "K90"), constraints="P", purpose="Uncapped mechanism control")
    add(A("F", "I90", "K90"), A("F", "I90"), purpose="K-off sizing on K-on basket")
    add("F", A("F", 0.5), purpose="Neutral-offset flattening control")
    for x, purpose in [("C30", "Short CAGR"), ("C360", "Long CAGR"), ("Sh90", "Short Sharpe"), ("Sh360", "Long Sharpe"), ("So180", "Sortino"), ("D90", "Drawdown"), ("Ca360", "Calmar"), ("Kmax", "K alone")]:
        add(x, x, purpose=purpose)
    assert len(rows) == 36
    return rows


def next_stage_registry(frozen):
    """Materialise A0 scope without executing it or choosing from outcomes."""
    rows = []
    windows = (30, 45, 46, 60, 90, 120, 180, 270, 360, 730)
    singles = [f"{prefix}{d}" for prefix in ("C", "Sh", "So", "D", "Ca") for d in windows]
    singles += [f"{prefix}{d}" for prefix in ("I", "V") for d in (30, 60, 75, 90, 105, 180)]
    singles += [f"K{d}" for d in (30, 60, 90, 180, 360)] + ["Kmax"]
    for component in singles:
        for R, Q, map in ((component, 1.0, "equal"), ("F", component, "linear"), (component, component, "linear")):
            for missing in ("M0", "MN", "MA"):
                # One-component MA equals M0; equal maps ignore missing sizing fills.
                if missing == "MA" or (map == "equal" and missing == "MN"):
                    continue
                rows.append(dict(stage="A0", ranking=R, weighting=Q, sizing_map=map, N=6, missing=missing, constraints="C"))
    # Pure I/V percentile ranking/equal roles are exact duplicates on shared risk/prior support.
    dedup = []
    seen = set()
    for row in rows:
        effective = row.copy()
        if row["sizing_map"] == "equal" and isinstance(row["ranking"], str) and row["ranking"].startswith("V"):
            effective["ranking"] = "I" + row["ranking"][1:]
        identity = canonical(effective)
        if identity not in seen:
            seen.add(identity)
            row["policy_id"] = recipe_id(row)
            dedup.append(row)
    return dict(stage="A0", status="proposed_not_executed", policies=dedup, unique_policies=len(dedup), standalone_components=len(singles), frozen_composites=len(frozen), horizons=[7, 30, 90], origins=70, chronology="Retrospective 2026 display; any fitting uses matured pre-2026 labels only", primary_contrasts="Equal-selection lift and common-basket weighting lift by metric/window; descriptive 2026", deferred="Stage A needs its own exact registry and contrast freeze after A0; all 139 frozen recipes retained in inventory")
