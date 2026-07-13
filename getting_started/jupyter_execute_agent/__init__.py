"""Observable Jupyter notebook execution helpers.

This package provides a small reusable execution agent for running notebooks
cell-by-cell with explicit progress events, partial-save support, and logging
extensions suitable for long-running research workflows.
"""

from .core import NotebookCellRecord
from .core import NotebookExecutionEvent
from .core import NotebookExecutionResult
from .core import DEFAULT_KERNEL_MEMORY_LIMIT_BYTES
from .core import build_cell_label
from .core import execute_notebook_observable
from .core import iter_code_cells
from .core import load_notebook_document
from .core import save_notebook_document
from .cli import build_argument_parser
from .cli import main
from .extension import build_logging_observer
from .extension import format_execution_event
from .extension import log_execution_event

__all__ = [
    "NotebookCellRecord",
    "NotebookExecutionEvent",
    "NotebookExecutionResult",
    "DEFAULT_KERNEL_MEMORY_LIMIT_BYTES",
    "build_argument_parser",
    "build_cell_label",
    "build_logging_observer",
    "execute_notebook_observable",
    "format_execution_event",
    "iter_code_cells",
    "load_notebook_document",
    "log_execution_event",
    "main",
    "save_notebook_document",
]
