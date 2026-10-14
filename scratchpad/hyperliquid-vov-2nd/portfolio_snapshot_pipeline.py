"""Content-addressed stage caches keep notebook reruns concrete and observable."""

import hashlib
import json
import pandas as pd
from portfolio_snapshot_data import ARTIFACT, CONFIG, fingerprint


def stage_key(stage, data):
    relevant = {"risk": ["portfolio_snapshot_data.py", "portfolio_snapshot_risk.py"], "snapshots": ["portfolio_snapshot_data.py", "portfolio_snapshot_risk.py", "portfolio_snapshot_construction.py"], "statistics": ["portfolio_snapshot_data.py", "portfolio_snapshot_risk.py", "portfolio_snapshot_construction.py", "portfolio_snapshot_statistics.py", "portfolio_snapshot_companions.py"]}[stage]
    files = fingerprint()
    identity = {"code": {p: files[p] for p in relevant}, "config": CONFIG, "inputs": data["downloads"], "phases": True, "origin_count": len(data["origins"])}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()


def execute_stage(stage, data, risk=None, result=None):
    if stage == "statistics":
        from portfolio_snapshot_companions import add_source_capacity_controls

        result = add_source_capacity_controls(data, risk, result)
    marker = ARTIFACT / f"{stage}-completed.json"
    key = stage_key(stage, data)
    names = {"risk": ["risk"], "snapshots": ["allocations", "outcomes", "ranks", "risk_evaluation", "score_ic", "population", "stability", "policies"], "statistics": ["contrasts", "breadth_attribution", "summaries", "risk_summary", "intervals", "assignment_dates", "assignment_pooled", "ties", "synthetic", "score_null"]}[stage]
    if marker.exists() and json.loads(marker.read_text()).get("key") == key and all((ARTIFACT / f"{n}.parquet").exists() for n in names):
        frames = {n: pd.read_parquet(ARTIFACT / f"{n}.parquet") for n in names}
        print(f"{stage}: verified stage fingerprint; loading saved calculations", flush=True)
        if stage == "risk":
            return frames["risk"]
        if stage == "snapshots":
            return frames
        result.update(frames)
        result["_data"] = data
        result["_risk"] = risk
        return result
    if stage == "risk":
        from portfolio_snapshot_risk import build_risk

        computed = build_risk(data)
    elif stage == "snapshots":
        from portfolio_snapshot_construction import run_snapshots

        computed = run_snapshots(data, risk)
    else:
        from portfolio_snapshot_statistics import run_statistics

        computed = run_statistics(data, risk, result)
    marker.write_text(json.dumps({"key": key, "stage": stage, "code": fingerprint(), "files": names}, indent=2))
    return computed
