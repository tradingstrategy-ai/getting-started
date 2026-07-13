# Running notebooks observably

Read this when creating or executing Jupyter notebooks, especially long
backtest, grid search, or optimiser runs that an agent needs to watch.

## Observability requirements

- All notebook cells must be observable, with `print()` and a
  [`tqdm_loggable`](https://github.com/tradingstrategy-ai/tqdm-loggable) progress
  bar for any operation longer than one minute.
- Each long-running cell should print an estimate of how many minutes it will
  still be running.
- Prefer table output (Pandas DataFrame + `display()`) over `print()` for
  tabular results.

## Preferred entrypoint: `jupyter-execute-agent`

The preferred command-line entrypoint is `jupyter-execute-agent`. It keeps the
Jupyter-kernel execution model while making slow notebooks observable:
notebook-level and cell-level progress, live cell output previews, live
`tqdm` progress-bar text, and a partial save after every completed code cell.
On operating systems whose shell supports it, the Python kernel is started with
a 24 GiB virtual-memory cap so a runaway cell fails inside the kernel instead of
exhausting the host.

```shell
# Run in-place, streaming progress to the terminal.
poetry run jupyter-execute-agent notebooks/single-backtest/moving-average.ipynb
```

Useful flags:

- `--output PATH` — write the executed notebook somewhere else instead of
  overwriting in place.
- `--timeout SECONDS` — per-cell timeout. Omit for the nbclient default; use a
  large value (or run without a timeout) for long optimisers.
- `--allow-errors` — keep executing after a cell raises.
- `--no-save-every-cell` — only save once at the end instead of after each cell.
- `--no-stream-cell-outputs` — quieter logs; only lifecycle events.

Because the runner saves after every completed cell, if a long notebook crashes
you still get every output produced up to the failing cell.

### tqdm progress must reach the terminal

All notebooks use `tqdm_loggable`. Force terminal progress output and keep the
command in the foreground so the progress bar is visible from the calling
terminal:

```shell
TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent my-notebook.ipynb
```

Do not rely on notebook widgets alone.

## Plain fallback

For a plain, non-observable run, `poetry run jupyter execute my-notebook.ipynb --inplace`
still works, but prefer `jupyter-execute-agent` for anything an agent needs to
watch.

Never use `ipython` to run notebooks — it forces single-process execution and
breaks multiprocessing. Use it only for targeted debugging of extracted code.

## Running multiple notebooks

When running multiple notebooks with subagents, use at most 3 agents at a time
to avoid exhausting RAM and crashing the machine. If several agents run
notebooks concurrently, never kill all `ipykernel` processes broadly — identify
the exact `jupyter-execute-agent ... my-notebook.ipynb` parent process first,
then match its child kernel by PID before killing anything.

## Programmatic use

The same execution flow is importable for tests and scripts:

```python
import logging
from pathlib import Path

from getting_started.jupyter_execute_agent import execute_notebook_observable
from getting_started.jupyter_execute_agent import build_logging_observer

result = execute_notebook_observable(
    Path("notebooks/single-backtest/moving-average.ipynb"),
    observers=[build_logging_observer(logger=logging.getLogger("notebook"))],
)
print(result.executed_code_cells, result.total_elapsed_seconds)
```

`execute_notebook_observable()` emits structured
`NotebookExecutionEvent` objects (`notebook_started`, `cell_started`,
`cell_output`, `cell_completed`, `cell_failed`, `notebook_saved`,
`notebook_completed`) to any observer callback, which is what makes runs
observable and testable. See
[tests/test_jupyter_execute_agent.py](../../tests/test_jupyter_execute_agent.py)
for a minimal observability regression test.
