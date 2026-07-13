"""Command-line entrypoint for observable notebook execution.

This module exposes a small Poetry script wrapper around
``execute_notebook_observable()`` so notebook runs can use the same
high-observability execution flow from the shell.
"""

import argparse
from pathlib import Path
import logging
import sys

from .core import execute_notebook_observable
from .extension import build_logging_observer


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for the observable notebook runner.

    Example:

    .. code-block:: python

        parser = build_argument_parser()
        namespace = parser.parse_args(["notebooks/demo.ipynb", "--save-every-cell"])

    :return:
        Configured argument parser.
    """

    parser = argparse.ArgumentParser(
        prog="jupyter-execute-agent",
        description="Execute a Jupyter notebook cell-by-cell with observable logs.",
    )
    parser.add_argument(
        "notebook_path",
        type=Path,
        help="Notebook file to execute.",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        type=Path,
        help="Destination executed notebook path. Defaults to in-place save.",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Kernel working directory. Defaults to the notebook parent.",
    )
    parser.add_argument(
        "--kernel-name",
        default="python3",
        help="Jupyter kernel name to use. Default: python3.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Per-cell timeout in seconds. Default: nbclient default.",
    )
    parser.add_argument(
        "--allow-errors",
        action="store_true",
        help="Continue execution when a cell raises an error.",
    )
    parser.add_argument(
        "--save-every-cell",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Save the notebook after every completed code cell. Default: true.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level for progress events. Default: INFO.",
    )
    parser.add_argument(
        "--stream-cell-outputs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Log cell stdout/stderr/result payloads as they arrive. Default: true.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the observable notebook CLI.

    Example:

    .. code-block:: shell

        poetry run jupyter-execute-agent notebooks/demo.ipynb --save-every-cell

    :param argv:
        Optional explicit argument vector, excluding the executable name.
    :return:
        Process exit code, where ``0`` means success.
    """

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(message)s",
    )

    execute_notebook_observable(
        args.notebook_path,
        output_path=args.output_path,
        cwd=args.cwd,
        kernel_name=args.kernel_name,
        timeout=args.timeout,
        allow_errors=args.allow_errors,
        save_every_cell=args.save_every_cell,
        observers=[
            build_logging_observer(
                logger=logging.getLogger(__name__),
                stream_cell_outputs=args.stream_cell_outputs,
            )
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
