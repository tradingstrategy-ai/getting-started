"""Check completed research controls against the pinned source replays."""

import json
import math

import pandas as pd

from repaired_data_replay import RUN_ROOT


def main():
    """Audit saved metrics and independent worker caches without running a kernel."""
    source = json.loads((RUN_ROOT / "01/metrics.json").read_text())
    caps = json.loads((RUN_ROOT / "02/metrics.json").read_text())
    weighting = json.loads((RUN_ROOT / "03/metrics.json").read_text())
    rows = []
    keys = ["Final equity (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Trades"]
    for label, filename in [("Short", "chart-2026-detailed-results.csv"), ("Long", "detailed-results.csv")]:
        reference = next(v for k, v in source.items() if k.startswith(label))
        matrix = pd.read_csv(RUN_ROOT / "04" / filename)
        calibration = pd.read_csv(RUN_ROOT / "05" / ("2026-results.csv" if label == "Short" else "long-results.csv"))
        controls = {
            "02 source": caps[f"{label} — v11 parent"],
            "03 source": weighting[f"{label} — Baseline redistribution — Original inverse variance"],
            "04 source": matrix[matrix.Family == "Original v11"].iloc[0],
            "04 exact formula": matrix[matrix.Family == "Exact 360/45 compatibility"].iloc[0],
            "05 exact formula": calibration[calibration.Configuration == "Hard C1 S3"].iloc[0],
        }
        for name, actual in controls.items():
            matches = all(math.isclose(float(reference[k]), float(actual[k]), rel_tol=1e-12, abs_tol=1e-10) for k in keys)
            assert matches, (label, name)
            rows.append({"period": label, "control": name, "metrics_match": matches})
        for key in keys:
            assert caps[f"{label} — accepted-dollar cap"][key] == weighting[f"{label} — Dollar cap — Original inverse variance"][key]
        rows.append({"period": label, "control": "02/03 cap", "metrics_match": True})
    cache_audit = []
    for folder_name in ["long-singleton-worker", "sharpe-search-worker", "factorial-worker-long", "factorial-worker-short"]:
        count = 0
        for path in (RUN_ROOT / "04" / folder_name).glob("*/*.json"):
            if path.name.endswith("-state.json"):
                continue
            shared = RUN_ROOT / "04" / path.parent.name / path.name
            if shared.exists():
                assert json.loads(path.read_text()) == json.loads(shared.read_text()), path
                count += 1
        cache_audit.append({"worker": folder_name, "exact_metric_matches": count})
    report = {"controls": rows, "independent_worker_metrics": cache_audit, "note": "Source/formula equity and full ledger equality are also asserted in notebooks 04 and 05. Worker metrics are fresh runs on this pinned input generation."}
    (RUN_ROOT / "cross-notebook-control-audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
