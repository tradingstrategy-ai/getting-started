"""Reusable observer extensions for observable notebook execution.

This module contains helpers that turn structured execution events into
terminal- or logger-friendly messages. Keep these helpers separate from the
core execution loop so they can be mixed, replaced, or composed by different
callers.
"""

import logging

from .core import NotebookExecutionEvent
from .core import NotebookExecutionObserver

__all__ = [
    "build_logging_observer",
    "format_execution_event",
    "log_execution_event",
]


def format_execution_event(event: NotebookExecutionEvent) -> str:
    """Format one execution event for human-readable logs.

    Example:

    .. code-block:: python

        from getting_started.jupyter_execute_agent.extension import format_execution_event

        message = format_execution_event(event)
        print(message)

    :param event:
        Structured notebook execution event.
    :return:
        Single-line human-readable message.
    """

    if event.kind == "notebook_started":
        return (
            f"Notebook started path={event.notebook_path} "
            f"code_cells={event.total_code_cells}"
        )
    if event.kind == "cell_started":
        return (
            f"Cell started {event.code_cell_index}/{event.total_code_cells} "
            f"index={event.cell_index} label={event.cell_label}"
        )
    if event.kind == "cell_output":
        output_suffix = f" output={event.output_preview}" if event.output_preview else ""
        return (
            f"Cell output {event.code_cell_index}/{event.total_code_cells} "
            f"index={event.cell_index} type={event.output_type}"
            f" label={event.cell_label}{output_suffix}"
        )
    if event.kind == "cell_completed":
        output_suffix = (
            f" output={event.output_preview}" if event.output_preview else ""
        )
        return (
            f"Cell completed {event.code_cell_index}/{event.total_code_cells} "
            f"index={event.cell_index} elapsed={event.elapsed_seconds:.2f}s"
            f" label={event.cell_label}{output_suffix}"
        )
    if event.kind == "cell_failed":
        return (
            f"Cell failed {event.code_cell_index}/{event.total_code_cells} "
            f"index={event.cell_index} elapsed={event.elapsed_seconds:.2f}s "
            f"label={event.cell_label} error={event.error_name}: {event.error_value}"
        )
    if event.kind == "notebook_saved":
        return f"Notebook saved path={event.output_path}"
    if event.kind == "notebook_completed":
        return (
            f"Notebook completed path={event.output_path} "
            f"elapsed={event.elapsed_seconds:.2f}s"
        )
    return f"Notebook event kind={event.kind}"


def log_execution_event(
    event: NotebookExecutionEvent,
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
) -> None:
    """Write one execution event through a standard logger.

    Example:

    .. code-block:: python

        import logging
        from getting_started.jupyter_execute_agent.extension import log_execution_event

        logger = logging.getLogger("notebook-runner")
        log_execution_event(event, logger=logger)

    :param event:
        Structured notebook execution event.
    :param logger:
        Logger to use. Defaults to this module's logger.
    :param level:
        Logging level used for the emitted message.
    :return:
        None.
    """

    active_logger = logger or logging.getLogger(__name__)
    active_logger.log(level, "%s", format_execution_event(event))


def build_logging_observer(
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
    stream_cell_outputs: bool = True,
) -> NotebookExecutionObserver:
    """Build an observer callback that logs every execution event.

    This is the simplest extension point for terminal-friendly notebook
    execution. Pass the returned callback to
    :func:`getting_started.jupyter_execute_agent.execute_notebook_observable`.

    Example:

    .. code-block:: python

        import logging
        from pathlib import Path

        from getting_started.jupyter_execute_agent import execute_notebook_observable
        from getting_started.jupyter_execute_agent.extension import build_logging_observer

        observer = build_logging_observer(
            logger=logging.getLogger("observable-notebook")
        )
        execute_notebook_observable(
            Path("notebooks/demo.ipynb"),
            observers=[observer],
        )

    :param logger:
        Logger to receive execution messages. Defaults to this module's logger.
    :param level:
        Logging level used for every emitted event.
    :param stream_cell_outputs:
        Whether to log live output payloads while a cell is still running.
    :return:
        Observer callback suitable for ``execute_notebook_observable``.
    """

    def _observer(event: NotebookExecutionEvent) -> None:
        if event.kind == "cell_output" and not stream_cell_outputs:
            return
        log_execution_event(event, logger=logger, level=level)

    return _observer
