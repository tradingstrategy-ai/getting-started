"""Repeat experiment 06's frozen scoring supports at wider portfolio breadth."""

import datetime
import hashlib
import json
import multiprocessing
import re
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from tqdm_loggable.auto import tqdm

import score_input_count_experiment as parent
from score_matrix import FEATURES
from repaired_data_replay import RUN_ROOT, RESEARCH_DIR

ARTIFACT_DIR = RUN_ROOT / "07"
NOTEBOOK = RESEARCH_DIR / "07-opt-score-position-count.ipynb"
PERIODS = parent.PERIODS
SHORT_PERIOD = parent.SHORT_PERIOD
LONG_PERIOD = parent.LONG_PERIOD
FOCAL_SCORE = "Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino"


class ExperimentParameters:
    """Frozen support grid and predeclared portfolio breadth axis."""

    #: Preserve the parent's bounded support search.
    iterations = 18
    #: Six positions are the matched reference, not a new treatment.
    position_counts = (6, 7, 8, 10)
    #: Independent engine processes; each engine runs serially.
    max_workers = 3


def initialise(positions=6):
    """Verify the exact parent generation before reusing its six-position cache."""
    evaluator, parameters, candidates, previous = parent.initialise(private=True)
    original = json.loads((parent.ARTIFACT_DIR / "design.json").read_text())
    assert original["fingerprint"] == evaluator.fingerprint
    assert original["configurations"] == candidates
    assert parent.SearchParameters.iterations == ExperimentParameters.iterations
    source_fingerprint = evaluator.fingerprint
    fingerprint = hashlib.sha256((source_fingerprint + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()).encode()).hexdigest()
    generation = ARTIFACT_DIR / fingerprint[:16]
    generation.mkdir(parents=True, exist_ok=True)
    destination = generation / f"n{positions}"
    destination.mkdir(exist_ok=True)
    if positions == 6:
        for path in previous.iterdir():
            if re.fullmatch(r"[0-9a-f]{24}(?:\.json|-state\.json|-allocations\.csv)", path.name):
                target = destination / path.name
                if not target.exists():
                    shutil.copy2(path, target)
    evaluator.folder = destination
    evaluator.fingerprint = fingerprint
    return evaluator, parameters, candidates, generation


def evaluate(evaluator, row, period, positions, keep=False):
    """Change the position/rank limits while retaining all scoring and guard rules."""
    return evaluator.run(row["Weights"], *PERIODS[period], n=int(positions), sizing="inverse_variance", allocator="parent", missing=True, profile=row["Profile"], keep=keep)


def record(row, positions, metrics):
    """Keep the score identity separate from the full strategy identity."""
    return {"Configuration": f"{row['Configuration']} / {positions} positions", "Score": row["Configuration"], "Positions": positions, **{k: v for k, v in row.items() if k not in ("Configuration", "Weights", "Profile")}, **metrics}


def worker(positions):
    """Run one breadth arm with its own cache and incremental progress files."""
    from contextlib import redirect_stdout, redirect_stderr
    import io

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        evaluator, _, rows, generation = initialise(positions)
    priority = [FOCAL_SCORE, "Legacy 45d", "Blend 46d", "Blend 46d / 3 inputs / 6m CAGR"]
    rows = sorted(rows, key=lambda r: priority.index(r["Configuration"]) if r["Configuration"] in priority else len(priority))
    timings = []
    for period in ("2026", "Long"):
        results = []
        for row in rows:
            started = time.monotonic()
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                metrics = evaluate(evaluator, row, period, positions)
            timings.append(time.monotonic() - started)
            results.append(record(row, positions, metrics))
            pd.DataFrame(results).to_csv(generation / f"{period}-n{positions}-results.csv", index=False)
            total = len(results) + (len(rows) if period == "Long" else 0)
            status = {"positions": positions, "period": period, "completed": total, "total": len(rows) * 2, "score": row["Configuration"], "CAGR": metrics["CAGR"], "Sharpe": metrics["Sharpe"], "remaining_minutes": float(np.mean(timings[-10:]) * (len(rows) * 2 - total) / 60), "fingerprint": evaluator.fingerprint}
            progress = generation / f"progress-n{positions}.json"
            temporary = progress.with_suffix(".tmp")
            temporary.write_text(json.dumps(status))
            temporary.replace(progress)
    return positions


def run_grid(evaluator, rows, generation):
    """Observe three independent breadth arms and merge only completed outputs."""
    assert len(rows) == 74
    reference = {}
    for period in PERIODS:
        records = [record(row, 6, evaluate(evaluator, row, period, 6)) for row in rows]
        reference[period] = pd.DataFrame(records)
        old = pd.read_csv(parent.ARTIFACT_DIR / f"{period}-results.csv").set_index("Configuration")
        for result in records:
            for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)", "Trades"):
                assert np.isclose(result[metric], old.loc[result["Score"], metric], rtol=1e-12, atol=1e-8)
    manifest = {"fingerprint": evaluator.fingerprint, "parent_fingerprint": json.loads((parent.ARTIFACT_DIR / "design.json").read_text())["fingerprint"], "positions": list(ExperimentParameters.position_counts), "supports_per_arm": len(rows), "iterations": ExperimentParameters.iterations, "new_backtests": 444, "inverse_variance_days": 90, "missing": True, "concentration_cap": 0.33, "allocation_pct": 0.98, "entry_rank": "N", "exit_rank": "N+2", "max_assets_in_portfolio": "N", "max_capacity_assets": "N", "periods": {k: list(map(str, v)) for k, v in PERIODS.items()}, "configurations": rows}
    (ARTIFACT_DIR / "design.json").write_text(json.dumps(manifest, indent=2))
    print("444 new engine replays across three breadth arms; estimated 20–35 minutes with three workers.", flush=True)
    progress = tqdm(total=444, desc="Position-count replays")
    completed = 0
    with ProcessPoolExecutor(max_workers=ExperimentParameters.max_workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = [pool.submit(worker, positions) for positions in (7, 8, 10)]
        while True:
            statuses = []
            for positions in (7, 8, 10):
                path = generation / f"progress-n{positions}.json"
                if path.exists():
                    statuses.append(json.loads(path.read_text()))
            new_completed = sum(r["completed"] for r in statuses)
            if new_completed > completed:
                progress.update(new_completed - completed)
                completed = new_completed
            progress.set_postfix_str(" | ".join(f"N={r['positions']} {r['period']} {r['completed']}/148 ~{r['remaining_minutes']:.1f}m" for r in statuses))
            for future in futures:
                if future.done():
                    future.result()
            if all(future.done() for future in futures):
                break
            time.sleep(3)
    progress.close()
    frames = {}
    for period in PERIODS:
        frames[period] = pd.concat([reference[period]] + [pd.read_csv(generation / f"{period}-n{n}-results.csv") for n in (7, 8, 10)], ignore_index=True)
        assert len(frames[period]) == 296 and not frames[period].Configuration.duplicated().any()
        assert (frames[period]["Maximum vaults held"] <= frames[period].Positions).all()
        frames[period].to_csv(ARTIFACT_DIR / f"{period}-results.csv", index=False)
    return frames["2026"], frames["Long"]


def short_label(row):
    """Use compact, traceable labels that fit static charts."""
    score = row["Score"]
    identity = score if row["Inputs"] == 2 else f"{row['Family']} · {row['Inputs']} inputs · support {int(row['Support']):02d}"
    return f"{identity} · N={int(row['Positions'])}"


def matched_deltas(frame):
    """Compare each support directly with its six-position counterpart."""
    reference = frame[frame.Positions.eq(6)].set_index("Score")
    result = frame[~frame.Positions.eq(6)].copy()
    for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Trades"):
        result[f"Delta {metric}"] = result[metric] - result.Score.map(reference[metric])
    result["Joint improvement"] = (result["Delta CAGR"] > 0) & (result["Delta Sharpe"] > 0) & (result["Delta Maximum drawdown"] >= 0)
    return result


def metric_heatmap(frame, count):
    """Show each support at each breadth, with a common scale per metric."""
    metrics = ("CAGR", "Sharpe", "Maximum drawdown")
    families = ("Legacy 45d", "Blend 46d")
    fig = make_subplots(rows=2, cols=3, subplot_titles=[f"{family}: {metric}" for family in families for metric in metrics], horizontal_spacing=0.10, vertical_spacing=0.12)
    subset = frame[frame.Inputs.eq(count)]
    for col, metric in enumerate(metrics, 1):
        scale = 1 if metric == "Sharpe" else 100
        lo, hi = subset[metric].min() * scale, subset[metric].max() * scale
        for row, family in enumerate(families, 1):
            data = subset[subset.Family.eq(family)].pivot(index="Support", columns="Positions", values=metric).sort_index()
            labels = subset[subset.Family.eq(family)].drop_duplicates("Support").set_index("Support")["Added inputs"]
            z = data.to_numpy() * scale
            fig.add_trace(go.Heatmap(z=z, x=[str(n) for n in data.columns], y=[f"{int(i):02d}: {labels.loc[i]}" for i in data.index], text=np.array([[f"{v:.2f}" for v in line] for line in z]), texttemplate="%{text}", colorscale="RdYlGn", zmin=lo, zmax=hi, showscale=False), row=row, col=col)
            fig.update_yaxes(autorange="reversed", showticklabels=col == 1, row=row, col=col)
            fig.update_xaxes(title="Maximum positions", row=row, col=col)
    fig.update_layout(title=f"Exactly {count} scoring inputs across position counts", width=1750, height=1450, template="plotly_white", margin=dict(t=130, l=380, b=80, r=40))
    return fig


def cluster_figure(frame):
    """Compare risk/return maps without selecting unseen-period parameters."""
    pairs = [("CAGR", "Sharpe"), ("CAGR", "Maximum drawdown"), ("Sharpe", "Maximum drawdown")]
    colours = {6: "#111827", 7: "#2563eb", 8: "#ea580c", 10: "#16a34a"}
    symbols = {2: "circle", 3: "diamond", 4: "square"}
    fig = make_subplots(rows=1, cols=3, subplot_titles=["CAGR / Sharpe", "CAGR / max drawdown", "Sharpe / max drawdown"], horizontal_spacing=0.09)
    for col, (x, y) in enumerate(pairs, 1):
        for n in ExperimentParameters.position_counts:
            data = frame[frame.Positions.eq(n)]
            fig.add_trace(go.Scatter(x=data[x] * (1 if x == "Sharpe" else 100), y=data[y] * (1 if y == "Sharpe" else 100), mode="markers", name=f"N={n}", legendgroup=str(n), showlegend=col == 1, text=data.Configuration, marker=dict(size=8, color=colours[n], symbol=data.Inputs.map(symbols)), hovertemplate="%{text}<br>%{x:.2f}, %{y:.2f}<extra></extra>"), row=1, col=col)
        fig.update_xaxes(title=x + (" (%)" if x != "Sharpe" else ""), row=1, col=col)
        fig.update_yaxes(title=y + (" (%)" if y != "Sharpe" else ""), row=1, col=col)
    fig.update_layout(title="Scoring and portfolio breadth risk/return clusters", width=1600, height=650, template="plotly_white", legend=dict(orientation="h", y=-0.18), margin=dict(t=120, b=130, l=80, r=40))
    return fig


def selected_configurations(short, long):
    """Retain the frozen focal score plus separately labelled observed maxima."""
    names = short[short.Score.eq(FOCAL_SCORE)].Configuration.tolist()
    names += short[short.Score.eq("Legacy 45d") & short.Positions.eq(6)].Configuration.tolist()
    for frame in (long, short):
        for n in (7, 8, 10):
            subset = frame[frame.Positions.eq(n)]
            for metric in ("CAGR", "Sharpe"):
                names.append(subset.sort_values([metric, "Configuration"], ascending=[False, True]).iloc[0].Configuration)
    return list(dict.fromkeys(names))
