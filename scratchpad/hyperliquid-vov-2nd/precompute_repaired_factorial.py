"""Publish completed, deterministic grid metrics from a private worker cache."""

import argparse
import datetime
import hashlib
import io
import json
import os
import time
from contextlib import redirect_stdout, redirect_stderr

import numpy as np
from precompute_repaired_singletons import create_evaluator
from score_matrix_blends import register_score_blend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=["long", "short"], default="long")
    args = parser.parse_args()
    evaluator, parameters, folder, fingerprint = create_evaluator("factorial-worker-" + args.period)
    families = json.loads((folder / "frozen-matrices.json").read_text())
    for config in families.values():
        if config["Components"]:
            weights, profile = register_score_blend(evaluator.panel, config["Components"])
            assert profile == config["Profile"]
            assert np.allclose(weights, config["Weights"], rtol=0, atol=1e-12)
    start = datetime.datetime(2023, 3, 1) if args.period == "long" else datetime.datetime(2026, 1, 1)
    end = parameters.backtest_end
    jobs = []
    seen = set()
    for family, config in families.items():
        for n in [4, 6, 10]:
            for sizing in ["equal", "score", "inverse_variance"]:
                for missing in [False, True]:
                    weights = np.asarray(config["Weights"])
                    tag = json.dumps({"w": list(weights.round(10)), "start": str(start), "end": str(end), "n": n, "sizing": sizing, "allocator": "parent", "source_control": False, "calmar_cap": 5.0, "missing": missing, "profile": config["Profile"]}, sort_keys=True)
                    key = hashlib.sha256(tag.encode()).hexdigest()[:24]
                    if key not in seen:
                        jobs.append((family, config, n, sizing, missing, key))
                        seen.add(key)
    records = []
    shared = folder / fingerprint[:16]
    for index, (family, config, n, sizing, missing, key) in enumerate(reversed(jobs), 1):
        target = shared / f"{key}.json"
        if target.exists():
            continue
        started = time.monotonic()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            evaluator.run(np.asarray(config["Weights"]), start, end, n=n, sizing=sizing, missing=missing, profile=config["Profile"])
        source = evaluator.folder / f"{key}.json"
        assert source.is_file(), "Worker configuration key differs from the notebook"
        temporary = shared / f".{key}-worker-{os.getpid()}.tmp"
        temporary.write_bytes(source.read_bytes())
        temporary.replace(target)
        records.append({"family": family, "key": key, "elapsed_seconds": time.monotonic() - started})
        print(f"{index}/{len(jobs)} reverse grid: {family}, {n}/{sizing}/missing={missing}; published {len(records)} fresh runs", flush=True)
        (folder / (args.period + "-factorial-worker.json")).write_text(json.dumps({"fingerprint": fingerprint, "engine_calls": evaluator.engine_calls, "published": records, "evaluations": list(evaluator.records.values())}, indent=2))
    print("Independent " + args.period + "-grid worker finished", flush=True)


if __name__ == "__main__":
    main()
