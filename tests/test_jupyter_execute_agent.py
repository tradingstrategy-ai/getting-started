"""Observability regression test for the ``jupyter-execute-agent`` runner.

This exercises :func:`execute_notebook_observable` end-to-end on a tiny,
self-contained notebook and asserts that the run is genuinely *observable*:
the runner must stream a live cell-output event carrying the printed marker
*before* it reports the cell as completed. This is the contract the observable
runner exists to provide, so if it regresses this test fails.
"""

from pathlib import Path

import nbformat

from getting_started.jupyter_execute_agent import execute_notebook_observable


def _write_simple_notebook(notebook_path: Path) -> None:
    """Write a one-cell notebook that prints an observable marker."""

    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell("print('observable-marker')"),
        ],
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
    )
    with notebook_path.open("w", encoding="utf-8") as handle:
        nbformat.write(notebook, handle)


def test_notebook_run_is_observable(tmp_path: Path) -> None:
    """A simple notebook run must stream live output before completion."""

    notebook_path = tmp_path / "simple.ipynb"
    output_path = tmp_path / "simple-executed.ipynb"
    _write_simple_notebook(notebook_path)

    observed_events: list[tuple[str, str | None]] = []

    def observer(event) -> None:
        observed_events.append((event.kind, event.output_preview))

    result = execute_notebook_observable(
        notebook_path,
        output_path=output_path,
        timeout=60,
        observers=[observer],
    )

    # The notebook executed fully.
    assert result.executed_code_cells == 1
    assert result.total_code_cells == 1

    event_kinds = [kind for kind, _ in observed_events]

    # Lifecycle events are emitted, which is what makes the run observable.
    assert "notebook_started" in event_kinds
    assert "cell_started" in event_kinds
    assert "cell_completed" in event_kinds
    assert "notebook_completed" in event_kinds

    # The printed marker is streamed as a live output event...
    assert any(
        kind == "cell_output" and preview == "observable-marker"
        for kind, preview in observed_events
    )

    # ...and it arrives before the cell is reported as completed.
    assert event_kinds.index("cell_output") < event_kinds.index("cell_completed")

    # The executed notebook was saved with the marker in its outputs.
    executed = nbformat.read(output_path, as_version=4)
    stream_text = "".join(
        str(output.get("text", ""))
        for output in executed.cells[0].get("outputs", [])
        if output.get("output_type") == "stream"
    )
    assert "observable-marker" in stream_text
