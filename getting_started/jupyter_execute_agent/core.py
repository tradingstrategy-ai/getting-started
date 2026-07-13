"""Core helpers for observable Jupyter notebook execution.

The functions in this module are designed for long-running notebook workflows
where plain ``jupyter execute`` is too opaque. The execution loop emits
structured events before and after each code cell, can save the partially
executed notebook after every completed cell, and keeps enough timing
information for human-friendly progress reporting.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import html
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Sequence

from jupyter_client.manager import KernelManager
import nbformat
from nbclient import NotebookClient
from nbclient.client import output_from_msg
from nbclient.exceptions import CellExecutionError
from nbformat import NotebookNode


EventKind = Literal[
    "notebook_started",
    "cell_started",
    "cell_output",
    "cell_completed",
    "cell_failed",
    "notebook_saved",
    "notebook_completed",
]

#: Default address-space cap for local Python Jupyter kernels so large
#: notebooks fail inside the kernel before exhausting the host.
DEFAULT_KERNEL_MEMORY_LIMIT_BYTES = 24 * 1024 * 1024 * 1024

#: Shell path used for applying the memory cap before the Python kernel starts.
_KERNEL_MEMORY_LIMIT_SHELL = "/bin/sh"

#: Shell snippet used because ``ulimit`` is a shell builtin on common POSIX systems.
_KERNEL_MEMORY_LIMIT_SCRIPT = (
    'limit_kbytes="$1"\n'
    "shift\n"
    'ulimit -v "$limit_kbytes" || exit 126\n'
    'exec "$@"\n'
)

__all__ = [
    "DEFAULT_KERNEL_MEMORY_LIMIT_BYTES",
    "NotebookCellRecord",
    "NotebookExecutionEvent",
    "NotebookExecutionObserver",
    "NotebookExecutionResult",
    "build_cell_label",
    "execute_notebook_observable",
    "iter_code_cells",
    "load_notebook_document",
    "save_notebook_document",
]


@dataclass(slots=True, frozen=True)
class NotebookExecutionEvent:
    """One structured notebook-execution event.

    :ivar kind:
        Event kind such as ``"cell_started"`` or ``"cell_completed"``.
    :ivar notebook_path:
        Source notebook path.
    :ivar output_path:
        Destination notebook path written during execution.
    :ivar cell_index:
        Zero-based absolute cell index inside the notebook, or ``None`` for
        notebook-level events.
    :ivar code_cell_index:
        One-based code-cell position among code cells only, or ``None`` for
        notebook-level events.
    :ivar total_code_cells:
        Total number of code cells in the notebook.
    :ivar cell_label:
        Short cell label derived from the cell source.
    :ivar started_at:
        UTC timestamp when the event scope started.
    :ivar finished_at:
        UTC timestamp when the event scope finished.
    :ivar elapsed_seconds:
        Duration in seconds for the event scope.
    :ivar execution_count:
        Jupyter execution count written to the cell, if available.
    :ivar output_preview:
        Short preview of the cell output payload, if any.
    :ivar output_type:
        Jupyter output payload type for live ``"cell_output"`` events.
    :ivar error_name:
        Jupyter error name for failed cells, if available.
    :ivar error_value:
        Jupyter error value for failed cells, if available.
    """

    kind: EventKind
    notebook_path: Path
    output_path: Path
    cell_index: int | None = None
    code_cell_index: int | None = None
    total_code_cells: int | None = None
    cell_label: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    execution_count: int | None = None
    output_preview: str | None = None
    output_type: str | None = None
    error_name: str | None = None
    error_value: str | None = None


@dataclass(slots=True, frozen=True)
class NotebookCellRecord:
    """Summary record for one executed code cell.

    :ivar cell_index:
        Zero-based absolute notebook cell index.
    :ivar code_cell_index:
        One-based code-cell position among code cells only.
    :ivar label:
        Human-friendly cell label derived from the source.
    :ivar status:
        Final status, typically ``"completed"`` or ``"failed"``.
    :ivar elapsed_seconds:
        Cell execution time in seconds.
    :ivar execution_count:
        Jupyter execution counter written to the cell.
    :ivar output_preview:
        Short output preview extracted from the executed cell.
    """

    cell_index: int
    code_cell_index: int
    label: str
    status: Literal["completed", "failed"]
    elapsed_seconds: float
    execution_count: int | None
    output_preview: str | None = None


@dataclass(slots=True, frozen=True)
class NotebookExecutionResult:
    """Summary of an observable notebook execution run.

    :ivar notebook_path:
        Source notebook path.
    :ivar output_path:
        Final saved notebook path.
    :ivar started_at:
        UTC start timestamp.
    :ivar finished_at:
        UTC end timestamp.
    :ivar total_elapsed_seconds:
        Total notebook execution time in seconds.
    :ivar total_code_cells:
        Total number of code cells discovered before execution.
    :ivar executed_code_cells:
        Number of code cells that finished execution.
    :ivar cell_records:
        Per-cell execution summaries in completion order.
    """

    notebook_path: Path
    output_path: Path
    started_at: datetime
    finished_at: datetime
    total_elapsed_seconds: float
    total_code_cells: int
    executed_code_cells: int
    cell_records: tuple[NotebookCellRecord, ...]


type NotebookExecutionObserver = Callable[[NotebookExecutionEvent], None]


class ObservableNotebookClient(NotebookClient):
    """Notebook client that emits observer events for live cell outputs."""

    def __init__(
        self,
        *args: Any,
        output_observer: Callable[[NotebookNode, int], None] | None = None,
        kernel_memory_limit_bytes: int | None = DEFAULT_KERNEL_MEMORY_LIMIT_BYTES,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("kernel_manager_class", MemoryLimitedKernelManager)
        super().__init__(*args, **kwargs)
        self._output_observer = output_observer
        self._kernel_memory_limit_bytes = kernel_memory_limit_bytes
        self._widget_progress_tracker = _WidgetProgressTracker()

    def create_kernel_manager(self) -> KernelManager:
        """Create a kernel manager configured for observable execution.

        The base nbclient implementation owns kernel-manager construction. We
        extend it only to pass the optional memory limit to our local manager
        subclass after traitlets has instantiated the manager.

        :return:
            Configured kernel manager.
        """

        manager = super().create_kernel_manager()
        if isinstance(manager, MemoryLimitedKernelManager):
            manager.kernel_memory_limit_bytes = self._kernel_memory_limit_bytes
        return manager

    def process_message(
        self,
        msg: dict[str, Any],
        cell: NotebookNode,
        cell_index: int,
    ) -> NotebookNode | None:
        """Process a kernel message and notify callers about new outputs."""

        output = super().process_message(msg, cell, cell_index)
        if output is not None and self._output_observer is not None:
            self._output_observer(output, cell_index)
        if self._output_observer is not None:
            live_output = self._build_live_output_from_message(msg)
            if live_output is not None:
                self._output_observer(live_output, cell_index)
        return output

    def _build_live_output_from_message(
        self,
        msg: dict[str, Any],
    ) -> NotebookNode | None:
        """Build a live output payload from non-append kernel messages.

        ``nbclient`` returns appended outputs from :meth:`process_message`, but
        notebook progress bars commonly refresh through ``update_display_data``
        or ipywidgets ``comm_msg`` traffic. Those messages mutate earlier
        outputs or widget state instead of appending a new output object, so
        callers need a small translation layer for headless observability.

        :param msg:
            Raw kernel IOPub message.
        :return:
            Synthetic output node for observer callbacks, or ``None``.
        """

        msg_type = str(msg.get("msg_type", ""))
        if msg_type == "update_display_data":
            try:
                return output_from_msg(msg)
            except ValueError:
                return None
        if msg_type in {"comm_open", "comm_msg"}:
            preview = self._widget_progress_tracker.update(msg)
            if preview:
                return NotebookNode(
                    {
                        "output_type": "widget_progress",
                        "text": preview,
                    }
                )
        return None


class MemoryLimitedKernelManager(KernelManager):
    """Kernel manager that applies an optional local-process memory cap."""

    kernel_memory_limit_bytes: int | None = DEFAULT_KERNEL_MEMORY_LIMIT_BYTES

    async def _async_pre_start_kernel(
        self,
        **kw: Any,
    ) -> tuple[list[str], dict[str, Any]]:
        """Prepare the kernel command and wrap it with ``ulimit`` when viable.

        :param kw:
            Kernel startup keyword arguments.
        :return:
            Kernel command and launch keyword arguments.
        """

        kernel_cmd, launch_kwargs = await super()._async_pre_start_kernel(**kw)
        if _kernel_memory_limit_is_supported(self.kernel_memory_limit_bytes):
            kernel_cmd = _wrap_kernel_command_with_memory_limit(
                kernel_cmd,
                self.kernel_memory_limit_bytes,
            )
        return kernel_cmd, launch_kwargs


class _WidgetProgressTracker:
    """Track ipywidgets progress bars and render them as compact text."""

    _PROGRESS_MODELS = {"FloatProgressModel", "IntProgressModel"}
    _HTML_MODELS = {"HTMLModel", "LabelModel"}
    _CONTAINER_MODELS = {"HBoxModel", "VBoxModel"}

    def __init__(self) -> None:
        self._models: dict[str, dict[str, Any]] = {}
        self._last_preview_by_container: dict[str, str] = {}

    def update(self, msg: dict[str, Any]) -> str | None:
        """Update widget state from one comm message and maybe render progress.

        :param msg:
            Raw ``comm_open`` or ``comm_msg`` kernel message.
        :return:
            Progress preview when a tqdm-like widget changed, otherwise
            ``None``.
        """

        content = msg.get("content", {})
        comm_id = str(content.get("comm_id", ""))
        if not comm_id:
            return None

        msg_type = str(msg.get("msg_type", ""))
        data = content.get("data", {})
        if not isinstance(data, dict):
            return None

        if msg_type == "comm_open":
            state = data.get("state", {})
            if isinstance(state, dict):
                self._models[comm_id] = dict(state)
            return None

        if msg_type != "comm_msg":
            return None

        state = data.get("state", {})
        if isinstance(state, dict):
            self._models.setdefault(comm_id, {}).update(state)

        return self._build_preview_for_changed_model(comm_id)

    def _build_preview_for_changed_model(self, comm_id: str) -> str | None:
        """Render a tqdm widget when its right-hand status text changes."""

        for container_id, container in self._models.items():
            if not self._is_container_model(container):
                continue
            children = self._normalise_widget_children(container.get("children", []))
            if comm_id not in children:
                continue
            progress_child_ids = [
                child_id
                for child_id in children
                if self._is_progress_model(self._models.get(child_id, {}))
            ]
            if not progress_child_ids:
                continue
            html_child_ids = [
                child_id
                for child_id in children
                if self._is_html_model(self._models.get(child_id, {}))
            ]
            if html_child_ids and comm_id != html_child_ids[-1]:
                continue
            preview = self._build_container_preview(children, progress_child_ids[0])
            if not preview:
                continue
            if self._last_preview_by_container.get(container_id) == preview:
                continue
            self._last_preview_by_container[container_id] = preview
            return preview
        return None

    def _build_container_preview(
        self,
        children: Sequence[str],
        progress_child_id: str,
    ) -> str | None:
        """Build a text preview from a tqdm notebook widget container."""

        progress = self._models.get(progress_child_id, {})
        html_parts = [
            self._normalise_widget_text(self._models[child_id].get("value", ""))
            for child_id in children
            if child_id in self._models and self._is_html_model(self._models[child_id])
        ]
        text = " ".join(part for part in html_parts if part).strip()
        if not text:
            text = self._build_progress_ratio(progress)
        return text or None

    def _build_progress_ratio(self, progress: dict[str, Any]) -> str:
        """Build a fallback ``n/total`` text from a progress widget."""

        value = progress.get("value")
        total = progress.get("max")
        if value is None or total is None:
            return ""
        try:
            value_number = float(value)
            total_number = float(total)
        except (TypeError, ValueError):
            return ""
        if total_number <= 0:
            return f"{value_number:g}"
        percent = value_number / total_number * 100.0
        return f"{percent:.0f}% {value_number:g}/{total_number:g}"

    def _normalise_widget_children(self, children: object) -> tuple[str, ...]:
        """Return comm ids from ``IPY_MODEL_*`` child references."""

        if not isinstance(children, (list, tuple)):
            return ()
        return tuple(
            str(child).removeprefix("IPY_MODEL_")
            for child in children
            if str(child).startswith("IPY_MODEL_")
        )

    def _normalise_widget_text(self, value: object) -> str:
        """Convert widget HTML text to compact terminal text."""

        text = html.unescape(str(value))
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("\u2007", " ").replace("\xa0", " ")
        return " ".join(text.split())

    def _is_container_model(self, model: dict[str, Any]) -> bool:
        """Return whether a widget model is a box container."""

        return str(model.get("_model_name")) in self._CONTAINER_MODELS

    def _is_progress_model(self, model: dict[str, Any]) -> bool:
        """Return whether a widget model is a progress bar."""

        return str(model.get("_model_name")) in self._PROGRESS_MODELS

    def _is_html_model(self, model: dict[str, Any]) -> bool:
        """Return whether a widget model carries display text."""

        return str(model.get("_model_name")) in self._HTML_MODELS


def load_notebook_document(notebook_path: Path) -> NotebookNode:
    """Load a notebook document from disk.

    Reads the notebook using ``nbformat`` version 4 so it can be passed
    directly to :class:`nbclient.NotebookClient`.

    Example:

    .. code-block:: python

        from pathlib import Path
        from getting_started.jupyter_execute_agent import load_notebook_document

        notebook = load_notebook_document(Path("notebooks/demo.ipynb"))

    :param notebook_path:
        Notebook file to load.
    :return:
        Parsed ``NotebookNode`` document.
    """

    with notebook_path.open("r", encoding="utf-8") as handle:
        return nbformat.read(handle, as_version=4)


def save_notebook_document(notebook: NotebookNode, output_path: Path) -> Path:
    """Save a notebook document to disk.

    Example:

    .. code-block:: python

        from pathlib import Path
        from getting_started.jupyter_execute_agent import save_notebook_document

        save_notebook_document(notebook, Path("notebooks/demo-executed.ipynb"))

    :param notebook:
        Parsed notebook document.
    :param output_path:
        Destination notebook path.
    :return:
        The written output path.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        nbformat.write(notebook, handle)
    return output_path


def iter_code_cells(notebook: NotebookNode) -> Iterator[tuple[int, int, NotebookNode]]:
    """Yield the code cells in notebook order.

    The returned tuple contains ``(cell_index, code_cell_index, cell)`` where
    ``cell_index`` is the absolute notebook index and ``code_cell_index`` is
    one-based among code cells only.

    Example:

    .. code-block:: python

        for cell_index, code_cell_index, cell in iter_code_cells(notebook):
            print(cell_index, code_cell_index, cell.cell_type)

    :param notebook:
        Notebook document to inspect.
    :return:
        Iterator over code-cell tuples.
    """

    code_cell_index = 0
    for cell_index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        code_cell_index += 1
        yield cell_index, code_cell_index, cell


def build_cell_label(
    cell: NotebookNode,
    cell_index: int,
    *,
    max_chars: int = 96,
) -> str:
    """Build a compact label for one notebook cell.

    The label uses the first non-empty source line when possible, falling back
    to a synthetic ``Cell <n>`` label when the source is empty.

    Example:

    .. code-block:: python

        label = build_cell_label(cell, 7)
        print(label)

    :param cell:
        Notebook cell node.
    :param cell_index:
        Zero-based absolute cell index.
    :param max_chars:
        Maximum label length before truncation.
    :return:
        Human-readable cell label.
    """

    raw_source = str(cell.get("source", ""))
    for line in raw_source.splitlines():
        stripped = line.strip()
        if stripped:
            normalized = " ".join(stripped.split())
            if len(normalized) <= max_chars:
                return normalized
            return normalized[: max_chars - 3] + "..."
    return f"Cell {cell_index + 1}"


def execute_notebook_observable(
    notebook_path: Path,
    *,
    output_path: Path | None = None,
    cwd: Path | None = None,
    kernel_name: str = "python3",
    kernel_memory_limit_bytes: int | None = DEFAULT_KERNEL_MEMORY_LIMIT_BYTES,
    timeout: int | None = None,
    allow_errors: bool = False,
    save_every_cell: bool = True,
    observers: Sequence[NotebookExecutionObserver] = (),
    client_kwargs: dict[str, Any] | None = None,
) -> NotebookExecutionResult:
    """Execute a notebook cell-by-cell with structured progress events.

    This is the main high-observability execution helper. It emits notebook and
    cell events, optionally saves the notebook after each completed code cell,
    and returns a summary object at the end. Failed cells are saved before the
    original :class:`nbclient.exceptions.CellExecutionError` is re-raised.

    Example:

    .. code-block:: python

        import logging
        from pathlib import Path

        from getting_started.jupyter_execute_agent import execute_notebook_observable
        from getting_started.jupyter_execute_agent import build_logging_observer

        logger = logging.getLogger("notebook-runner")
        result = execute_notebook_observable(
            Path("notebooks/demo.ipynb"),
            output_path=Path("notebooks/demo-executed.ipynb"),
            observers=[build_logging_observer(logger=logger)],
            save_every_cell=True,
        )
        print(result.executed_code_cells, result.total_elapsed_seconds)

    :param notebook_path:
        Source notebook path to execute.
    :param output_path:
        Destination notebook path. Defaults to overwriting ``notebook_path``.
    :param cwd:
        Working directory exposed to the kernel via nbclient resources. Defaults
        to the notebook's parent directory.
    :param kernel_name:
        Jupyter kernel name. Defaults to ``"python3"``.
    :param kernel_memory_limit_bytes:
        Address-space memory cap applied to the local kernel process before it
        starts, when the operating system shell supports virtual-memory
        limits. Defaults to 24 GiB. Use ``None`` to disable the cap.
    :param timeout:
        Per-cell timeout in seconds. ``None`` uses nbclient defaults.
    :param allow_errors:
        Forwarded to nbclient. If ``False``, execution stops on the first cell
        error and re-raises ``CellExecutionError`` after saving the notebook.
    :param save_every_cell:
        If ``True``, save the notebook after every completed code cell.
    :param observers:
        Sequence of event callbacks invoked for notebook and cell lifecycle
        events.
    :param client_kwargs:
        Additional keyword arguments forwarded to ``NotebookClient``.
    :return:
        Execution summary result.
    """

    source_path = notebook_path.resolve()
    final_output_path = output_path.resolve() if output_path else source_path
    notebook = load_notebook_document(source_path)
    total_code_cells = sum(1 for _ in iter_code_cells(notebook))
    active_cwd = (cwd or source_path.parent).resolve()
    started_at = _utc_now()
    start_perf = time.perf_counter()
    observer_tuple = tuple(observers)
    _validate_kernel_memory_limit(kernel_memory_limit_bytes)

    _notify(
        observer_tuple,
        NotebookExecutionEvent(
            kind="notebook_started",
            notebook_path=source_path,
            output_path=final_output_path,
            total_code_cells=total_code_cells,
            started_at=started_at,
        ),
    )

    cell_labels: dict[int, str] = {}
    code_cell_indexes: dict[int, int] = {}
    for cell_index, code_cell_index, cell in iter_code_cells(notebook):
        cell_labels[cell_index] = build_cell_label(cell, cell_index)
        code_cell_indexes[cell_index] = code_cell_index

    def _notify_live_output(output: NotebookNode, cell_index: int) -> None:
        output_preview = _build_single_output_preview(output)
        if output_preview is None:
            return
        _notify(
            observer_tuple,
            NotebookExecutionEvent(
                kind="cell_output",
                notebook_path=source_path,
                output_path=final_output_path,
                cell_index=cell_index,
                code_cell_index=code_cell_indexes.get(cell_index),
                total_code_cells=total_code_cells,
                cell_label=cell_labels.get(cell_index),
                finished_at=_utc_now(),
                execution_count=_coerce_execution_count(notebook.cells[cell_index]),
                output_preview=output_preview,
                output_type=str(output.get("output_type", "")) or None,
            ),
        )

    client = ObservableNotebookClient(
        notebook,
        timeout=timeout,
        kernel_name=kernel_name,
        allow_errors=allow_errors,
        resources={"metadata": {"path": str(active_cwd)}},
        output_observer=_notify_live_output,
        kernel_memory_limit_bytes=kernel_memory_limit_bytes,
        **(client_kwargs or {}),
    )

    cell_records: list[NotebookCellRecord] = []
    executed_code_cells = 0

    try:
        with client.setup_kernel():
            for cell_index, code_cell_index, cell in iter_code_cells(notebook):
                label = cell_labels[cell_index]
                cell_started_at = _utc_now()
                cell_start_perf = time.perf_counter()
                _notify(
                    observer_tuple,
                    NotebookExecutionEvent(
                        kind="cell_started",
                        notebook_path=source_path,
                        output_path=final_output_path,
                        cell_index=cell_index,
                        code_cell_index=code_cell_index,
                        total_code_cells=total_code_cells,
                        cell_label=label,
                        started_at=cell_started_at,
                    ),
                )
                try:
                    client.execute_cell(
                        cell,
                        cell_index,
                        execution_count=code_cell_index,
                    )
                except CellExecutionError:
                    cell_elapsed = time.perf_counter() - cell_start_perf
                    failure_event = NotebookExecutionEvent(
                        kind="cell_failed",
                        notebook_path=source_path,
                        output_path=final_output_path,
                        cell_index=cell_index,
                        code_cell_index=code_cell_index,
                        total_code_cells=total_code_cells,
                        cell_label=label,
                        started_at=cell_started_at,
                        finished_at=_utc_now(),
                        elapsed_seconds=cell_elapsed,
                        execution_count=_coerce_execution_count(cell),
                        output_preview=_build_output_preview(cell),
                        error_name=_extract_error_name(cell),
                        error_value=_extract_error_value(cell),
                    )
                    cell_records.append(
                        NotebookCellRecord(
                            cell_index=cell_index,
                            code_cell_index=code_cell_index,
                            label=label,
                            status="failed",
                            elapsed_seconds=cell_elapsed,
                            execution_count=_coerce_execution_count(cell),
                            output_preview=_build_output_preview(cell),
                        )
                    )
                    save_notebook_document(notebook, final_output_path)
                    _notify(
                        observer_tuple,
                        NotebookExecutionEvent(
                            kind="notebook_saved",
                            notebook_path=source_path,
                            output_path=final_output_path,
                            total_code_cells=total_code_cells,
                            finished_at=_utc_now(),
                        ),
                    )
                    _notify(observer_tuple, failure_event)
                    raise

                cell_elapsed = time.perf_counter() - cell_start_perf
                executed_code_cells += 1
                cell_records.append(
                    NotebookCellRecord(
                        cell_index=cell_index,
                        code_cell_index=code_cell_index,
                        label=label,
                        status="completed",
                        elapsed_seconds=cell_elapsed,
                        execution_count=_coerce_execution_count(cell),
                        output_preview=_build_output_preview(cell),
                    )
                )
                _notify(
                    observer_tuple,
                    NotebookExecutionEvent(
                        kind="cell_completed",
                        notebook_path=source_path,
                        output_path=final_output_path,
                        cell_index=cell_index,
                        code_cell_index=code_cell_index,
                        total_code_cells=total_code_cells,
                        cell_label=label,
                        started_at=cell_started_at,
                        finished_at=_utc_now(),
                        elapsed_seconds=cell_elapsed,
                        execution_count=_coerce_execution_count(cell),
                        output_preview=_build_output_preview(cell),
                    ),
                )
                if save_every_cell:
                    save_notebook_document(notebook, final_output_path)
                    _notify(
                        observer_tuple,
                        NotebookExecutionEvent(
                            kind="notebook_saved",
                            notebook_path=source_path,
                            output_path=final_output_path,
                            cell_index=cell_index,
                            code_cell_index=code_cell_index,
                            total_code_cells=total_code_cells,
                            cell_label=label,
                            finished_at=_utc_now(),
                        ),
                    )
    finally:
        if not save_every_cell:
            save_notebook_document(notebook, final_output_path)
            _notify(
                observer_tuple,
                NotebookExecutionEvent(
                    kind="notebook_saved",
                    notebook_path=source_path,
                    output_path=final_output_path,
                    total_code_cells=total_code_cells,
                    finished_at=_utc_now(),
                ),
            )

    finished_at = _utc_now()
    result = NotebookExecutionResult(
        notebook_path=source_path,
        output_path=final_output_path,
        started_at=started_at,
        finished_at=finished_at,
        total_elapsed_seconds=time.perf_counter() - start_perf,
        total_code_cells=total_code_cells,
        executed_code_cells=executed_code_cells,
        cell_records=tuple(cell_records),
    )
    _notify(
        observer_tuple,
        NotebookExecutionEvent(
            kind="notebook_completed",
            notebook_path=source_path,
            output_path=final_output_path,
            total_code_cells=total_code_cells,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_seconds=result.total_elapsed_seconds,
        ),
    )
    return result


def _notify(
    observers: Sequence[NotebookExecutionObserver],
    event: NotebookExecutionEvent,
) -> None:
    """Dispatch one event to all observers.

    :param observers:
        Event callback sequence.
    :param event:
        Event to emit.
    :return:
        None.
    """

    for observer in observers:
        observer(event)


def _validate_kernel_memory_limit(
    memory_limit_bytes: int | None,
) -> None:
    """Validate a requested kernel memory cap.

    :param memory_limit_bytes:
        Desired address-space limit in bytes, or ``None`` to disable the cap.
    :return:
        None.
    """

    if memory_limit_bytes is None:
        return
    if memory_limit_bytes <= 0:
        raise ValueError("kernel_memory_limit_bytes must be positive or None")


@lru_cache(maxsize=16)
def _kernel_memory_limit_is_supported(memory_limit_bytes: int | None) -> bool:
    """Return whether this OS can launch Python under the requested cap.

    Some systems expose Python ``resource`` constants but cannot lower virtual
    memory limits to 24 GiB for a Python process. Probing through the same
    ``ulimit`` wrapper keeps the production path a no-op on those systems.

    :param memory_limit_bytes:
        Desired address-space limit in bytes, or ``None`` to disable the cap.
    :return:
        ``True`` when the wrapper can start a tiny Python child.
    """

    if memory_limit_bytes is None or os.name != "posix":
        return False
    if not Path(_KERNEL_MEMORY_LIMIT_SHELL).exists():
        return False

    command = _wrap_kernel_command_with_memory_limit(
        [sys.executable, "-c", "pass"],
        memory_limit_bytes,
    )
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _wrap_kernel_command_with_memory_limit(
    kernel_cmd: list[str],
    memory_limit_bytes: int,
) -> list[str]:
    """Wrap a kernel command so the shell lowers virtual memory before exec.

    :param kernel_cmd:
        Original Jupyter kernel command.
    :param memory_limit_bytes:
        Desired address-space limit in bytes.
    :return:
        Wrapped command suitable for ``subprocess.Popen``.
    """

    limit_kbytes = str(_bytes_to_kib(memory_limit_bytes))
    return [
        _KERNEL_MEMORY_LIMIT_SHELL,
        "-c",
        _KERNEL_MEMORY_LIMIT_SCRIPT,
        "jupyter-memory-limit",
        limit_kbytes,
        *kernel_cmd,
    ]


def _bytes_to_kib(value: int) -> int:
    """Convert bytes to ceiling-rounded kibibytes for ``ulimit -v``.

    :param value:
        Byte count.
    :return:
        Kibibyte count rounded up.
    """

    return (value + 1023) // 1024


def _utc_now() -> datetime:
    """Return the current UTC timestamp.

    :return:
        Timezone-aware UTC timestamp.
    """

    return datetime.now(timezone.utc)


def _coerce_execution_count(cell: NotebookNode) -> int | None:
    """Extract the execution count from a cell node.

    :param cell:
        Notebook cell node.
    :return:
        Integer execution count or ``None``.
    """

    execution_count = cell.get("execution_count")
    return int(execution_count) if execution_count is not None else None


def _build_output_preview(cell: NotebookNode, *, max_chars: int = 240) -> str | None:
    """Build a compact output preview from a cell's outputs.

    :param cell:
        Notebook cell node.
    :param max_chars:
        Maximum preview length before truncation.
    :return:
        Output preview text or ``None`` if the cell has no text-like outputs.
    """

    fragments = [
        preview
        for output in cell.get("outputs", [])
        if (preview := _build_single_output_preview(output, max_chars=max_chars)) is not None
    ]
    preview = " | ".join(fragment for fragment in fragments if fragment)
    if not preview:
        return None
    if len(preview) <= max_chars:
        return preview
    return preview[: max_chars - 3] + "..."


def _build_single_output_preview(output: NotebookNode, *, max_chars: int = 500) -> str | None:
    """Build a compact preview from one Jupyter output payload.

    :param output:
        Jupyter output node.
    :param max_chars:
        Maximum preview length before truncation.
    :return:
        Output text preview or ``None`` when the payload has no text form.
    """

    output_type = output.get("output_type")
    if output_type == "stream":
        preview = _coerce_text_payload(output.get("text", "")).strip()
    elif output_type == "widget_progress":
        preview = _coerce_text_payload(output.get("text", "")).strip()
    elif output_type in {"execute_result", "display_data"}:
        data = output.get("data", {})
        preview = _coerce_text_payload(data.get("text/plain", "")).strip()
    elif output_type == "error":
        traceback_lines = output.get("traceback", [])
        if traceback_lines:
            preview = _coerce_text_payload(traceback_lines[-1]).strip()
        else:
            preview = str(output.get("evalue", "")).strip()
    else:
        preview = ""
    if not preview:
        return None
    if len(preview) <= max_chars:
        return preview
    return preview[: max_chars - 3] + "..."


def _coerce_text_payload(value: object) -> str:
    """Return text from notebook payload values that may be lists."""

    if isinstance(value, list):
        return "".join(str(item) for item in value)
    return str(value)


def _extract_error_name(cell: NotebookNode) -> str | None:
    """Extract the last error name from a failed cell.

    :param cell:
        Notebook cell node.
    :return:
        Error name or ``None``.
    """

    for output in reversed(cell.get("outputs", [])):
        if output.get("output_type") == "error":
            error_name = output.get("ename")
            return str(error_name) if error_name is not None else None
    return None


def _extract_error_value(cell: NotebookNode) -> str | None:
    """Extract the last error value from a failed cell.

    :param cell:
        Notebook cell node.
    :return:
        Error value or ``None``.
    """

    for output in reversed(cell.get("outputs", [])):
        if output.get("output_type") == "error":
            error_value = output.get("evalue")
            return str(error_value) if error_value is not None else None
    return None
