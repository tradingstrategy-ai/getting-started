"""Execute the independent fixed-seed Sharpe fit beside the notebook's CAGR fit."""

import datetime
import io
import json
import os
from contextlib import redirect_stdout, redirect_stderr

from precompute_repaired_singletons import create_evaluator
from score_matrix import sparse_search


def main():
    """Publish complete deterministic metrics into the matching shared generation."""
    evaluator, parameters, folder, fingerprint = create_evaluator("sharpe-search-worker")
    shared = folder / fingerprint[:16]
    screen = json.loads((folder / "screen.json").read_text())
    original_run = evaluator.run
    published = set()

    def run_and_publish(*args, **kwargs):
        result = original_run(*args, **kwargs)
        for key in evaluator.records:
            source = evaluator.folder / f"{key}.json"
            destination = shared / source.name
            if destination.exists() or key in published:
                continue
            temporary = shared / f".{key}-worker-{os.getpid()}.tmp"
            temporary.write_bytes(source.read_bytes())
            temporary.replace(destination)
            published.add(key)
            print(f"Sharpe fit worker published {len(published)} completed evaluations", flush=True)
        return result

    evaluator.run = run_and_publish
    # Keep engine diagnostics compact; completed-evaluation messages reach stdout.
    with redirect_stderr(io.StringIO()):
        best, proposals, neighbours = sparse_search(
            evaluator,
            screen,
            [(datetime.datetime(2023, 3, 1), parameters.backtest_end)],
            "Sharpe objective",
            iterations=18,
            seed=105,
        )
    (folder / "sharpe-search-worker.json").write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "winner": best,
                "proposals": proposals,
                "neighbours": neighbours,
                "published": sorted(published),
            },
            indent=2,
        )
    )
    print("Independent Sharpe fit completed", flush=True)


if __name__ == "__main__":
    main()
