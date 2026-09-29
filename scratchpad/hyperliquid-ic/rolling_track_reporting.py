"""Small reporting helpers for the rolling profit/risk notebook track."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError


def project_path() -> Path:
    """Return the research folder without depending on the notebook cwd."""
    return Path(__file__).resolve().parent


def write_pending_manifest(
    out: Path,
    *,
    notebook: str,
    parent: str,
    mechanism_delta: str,
    inputs: list[str],
    status: str = "pending_backtest",
    why_not_duplicate: str = "Reporting scaffold only; it reuses saved artefacts and adds no optimiser or new arm.",
) -> None:
    """Record ancestry and inputs for a reporting notebook."""
    out.mkdir(parents=True, exist_ok=True)
    root = project_path()
    source_hashes = {}
    for filename in ("rolling_track_reporting.py", "rolling_track_simulation.py", "rolling_track_features.py", "build_rolling_track.py"):
        path = root / filename
        if path.exists():
            source_hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "status": status,
        "notebook": notebook,
        "parent_experiment": parent,
        "mechanism_delta": mechanism_delta,
        "why_not_duplicate": why_not_duplicate,
        "inputs": inputs,
        "source_hashes": source_hashes,
        "environment": {"python": platform.python_version()},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))


def read_optional_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Load a saved table, returning an explicit empty table when unavailable."""
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        # The engine writes an empty allocations table when no allocation
        # snapshots were emitted for a control arm.  Treat that as a valid
        # empty input for synthesis rather than failing the report.
        return pd.DataFrame(columns=columns or [])
