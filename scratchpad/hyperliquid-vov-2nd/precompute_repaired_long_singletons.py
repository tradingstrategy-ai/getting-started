"""Publish identical full-history singleton metrics from an isolated worker."""

import datetime
import hashlib
import io
import json
import os
import time
from contextlib import redirect_stdout, redirect_stderr

import numpy as np

from precompute_repaired_singletons import create_evaluator
from score_matrix import FEATURES, SEARCH_FEATURES


def main():
    """Work backwards through the fixed screen while the notebook works forwards."""
    evaluator, parameters, folder, fingerprint = create_evaluator("long-singleton-worker")
    start = datetime.datetime(2023, 3, 1)
    end = parameters.backtest_end
    shared = folder / fingerprint[:16]
    jobs = [(i, missing) for i in SEARCH_FEATURES for missing in [False, True]]
    published = []
    for index, (feature, missing) in enumerate(reversed(jobs), 1):
        weights = np.zeros(len(FEATURES))
        weights[feature] = 1
        tag = json.dumps({"w": list(weights.round(10)), "start": str(start), "end": str(end), "n": 6, "sizing": "equal", "allocator": "parent", "source_control": False, "calmar_cap": 5.0, "missing": missing, "profile": "requested"}, sort_keys=True)
        key = hashlib.sha256(tag.encode()).hexdigest()[:24]
        destination = shared / f"{key}.json"
        if destination.exists():
            continue
        started = time.monotonic()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            evaluator.run(weights, start, end, missing=missing)
        source = evaluator.folder / f"{key}.json"
        assert source.is_file()
        temporary = shared / f".{key}-worker-{os.getpid()}.tmp"
        temporary.write_bytes(source.read_bytes())
        temporary.replace(destination)
        published.append({"key": key, "seconds": time.monotonic() - started})
        print(f"{index}/{len(jobs)} reverse full-history screen: {FEATURES[feature]}, missing={missing}; published {len(published)} runs", flush=True)
        (folder / "long-singleton-worker.json").write_text(
            json.dumps(
                {
                    "fingerprint": fingerprint,
                    "published": published,
                    "evaluations": list(evaluator.records.values()),
                },
                indent=2,
            )
        )
    print("Full-history singleton worker finished", flush=True)


if __name__ == "__main__":
    main()
