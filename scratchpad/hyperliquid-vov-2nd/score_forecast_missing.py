"""Separate missing-score entry sensitivity for experiment 08.

The core experiment's frozen source and 132 arms are untouched. The primary
2026 paths are derived only after verifying that no unscored new entry receives
funding. Longer-history paths are actual engine replays with an entry-only
missing-score veto after source basket selection and sizing. Incumbent top-ups,
exits, hysteresis, fees, caps and deposit checks retain the source behaviour.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import score_forecast_execution as core

ARTIFACT_DIR = core.ARTIFACT_DIR.parent / "unscored"
EXPECTED_CORE_SOURCE = "193cf660751a51c9720e3f47f980fdb2b0da6ca7ca452c38114148b54e4104f7"


class MissingOnlyPolicy(core.FloorPolicy):
    """Reject missing scores alone; numeric scores never face an extra floor."""

    def floor(self, timestamp):
        return np.nan, True, None

    def rejects(self, score, timestamp):
        return not np.isfinite(score)


def _baseline(data, monthly, method, period, positions):
    """Read the exact core cache, producing a baseline only when not yet cached."""
    return core.run_one(data["evaluator"], method, monthly, period, positions, "none", "slot_to_cash", None)


def _entry_audit(destination):
    """Separate unscored entry dollars from retained-holder adjustments."""
    ledger = pd.read_csv(destination / "allocations.csv", parse_dates=["Date"])
    missing = ledger["Ranking score"].isna()
    entry = ledger["New entrant"].astype(bool)
    new_slot = ~ledger["Held at decision"].astype(bool)
    return {"Missing score rows": int(missing.sum()), "Missing proposed new entrants": int((missing & entry).sum()), "Missing new-slot rows": int((missing & new_slot).sum()), "Missing new-entry planned dollars (USD)": float(ledger.loc[missing & entry, "Planned buy (USD)"].sum()), "Missing new-entry proposed dollars (USD)": float(ledger.loc[missing & entry, "No-floor proposed target (USD)"].sum()), "Missing incumbent buy dollars (USD)": float(ledger.loc[missing & ~new_slot, "Planned buy (USD)"].sum())}


def run_missing_sensitivity(data, execution=None, progress=None):
    """Produce six verified-identical 2026 paths and six actual Long replays.

    Run in a separate process while the core notebook executes, or after it.
    Never call concurrently within the same Python interpreter: the temporary
    factory replacement is scoped to this function and restored in ``finally``.
    """
    actual_core = hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest()
    assert actual_core == EXPECTED_CORE_SOURCE, "Core changed; review the sensitivity before replay"
    own_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    namespace = "exclude_unscored_" + own_hash[:20]
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    monthly = pd.read_parquet(core.ARTIFACT_DIR.parent / "monthly-thresholds.parquet")
    methods = {r["method_id"]: r for r in data["registry"] if r["method_id"] in core.METHODS}
    assert len(methods) == 3
    data["evaluator"].forecast_raw_prices = data["prices"].set_index(["date", "pair_id"]).sort_index()
    design = {"source_sha256": own_hash, "core_source_sha256": actual_core, "cache_policy_namespace": namespace, "treatment": "slot_to_cash", "rule": "After source selection/sizing, veto positive new-entry targets whose original score is nonfinite", "incumbents": "Held position top-ups, exits and hysteresis unchanged", "score_floor": "None for finite scores", "selector": "Unchanged; no replacement/refill entrants", "primary_period": "2026-01-01 → 2026-10-05 (end exclusive, UTC)", "secondary_period": "2023-03-01 → 2026-10-05 (end exclusive, UTC)", "planned_runs": {"fresh_Long": 6, "derived_identical_2026": 6}, "missing_policy_choice": "Separate exploratory sensitivity, not selected using portfolio outcome optimisation"}
    (ARTIFACT_DIR / "design.json").write_text(json.dumps(design, indent=2))
    records, audits = [], []
    for period in ("2026", "Long"):
        for method_id in core.METHODS:
            method = methods[method_id]
            for positions in (6, 7):
                baseline, baseline_directory = _baseline(data, monthly, method, period, positions)
                counts = _entry_audit(baseline_directory)
                if period == "2026":
                    assert counts["Missing proposed new entrants"] == 0, "Cannot derive unchanged 2026 path: unscored entry proposed"
                    assert counts["Missing new-entry planned dollars (USD)"] == 0.0, "Unscored new entry actually funded"
                    assert counts["Missing new-entry proposed dollars (USD)"] == 0.0, "Unscored entry target exists"
                    outcome, directory = baseline.copy(), baseline_directory
                    derived = True
                else:
                    original_policy = core.FloorPolicy
                    core.FloorPolicy = MissingOnlyPolicy
                    try:
                        outcome, directory = core.run_one(data["evaluator"], method, monthly, period, positions, namespace, "slot_to_cash", None)
                    finally:
                        core.FloorPolicy = original_policy
                    derived = False
                record = {**outcome, "Threshold policy": "exclude unscored", "Execution status": "Verified identical baseline; no new engine replay" if derived else "Fresh executable missing-entry replay", "Derived identical": derived, **counts, "Baseline cache key": baseline["cache_key"], "Artefact directory": str(directory)}
                for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Final equity (USD)", "Trades"):
                    record[f"Baseline {metric}"] = baseline[metric]
                    record[f"{metric} delta vs no-floor"] = outcome[metric] - baseline[metric]
                records.append(record)
                audits.append({"Period": period, "Method": method_id, "Positions": positions, "Derived identical": derived, "Baseline directory": str(baseline_directory), "Sensitivity directory": str(directory), **counts})
                pd.DataFrame(records).to_csv(ARTIFACT_DIR / "summary.csv", index=False)
                pd.DataFrame(audits).to_csv(ARTIFACT_DIR / "entry-audit.csv", index=False)
                if progress:
                    progress(len(records), 12, record)
    summary = pd.DataFrame(records)
    (ARTIFACT_DIR / "completed.json").write_text(json.dumps({"source_sha256": own_hash, "core_source_sha256": actual_core, "rows": len(summary), "fresh_Long": 6, "derived_identical_2026": 6}, indent=2))
    return {"summary": summary, "2026": summary[summary.Period.eq("2026")].copy(), "Long": summary[summary.Period.eq("Long")].copy(), "entry_audit": pd.DataFrame(audits), "design": design}
