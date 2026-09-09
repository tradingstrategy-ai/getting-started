"""Generic builder for the hyperliquid-lower-vol smoothing track notebooks (NB03a-NB11).

Not a notebook itself; imported by per-notebook build_NNx.py scripts.
"""
import json
from pathlib import Path

BUILD_DIR = Path(__file__).parent
TRACK_DIR = BUILD_DIR.parent
BASE = json.load(open(TRACK_DIR / "01-initial.ipynb"))

CELL6_ENHANCED = (BUILD_DIR / "cell6_enhanced.py").read_text()
CELL10_ENHANCED = (BUILD_DIR / "cell10_enhanced.py").read_text()
CELL14_ENHANCED = (BUILD_DIR / "cell14_enhanced.py").read_text()
HARNESS = (BUILD_DIR / "harness.py").read_text()


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": text.splitlines(keepends=True)}


def base_cell(i, transform=None):
    src = "".join(BASE["cells"][i]["source"])
    if transform:
        src = transform(src)
    return code(src) if BASE["cells"][i]["cell_type"] == "code" else md(src)


def cell6(notebook_id: str, dev_window: bool = True, extra_replacements: dict | None = None):
    src = CELL6_ENHANCED.replace("id = '01-initial'", f"id = '{notebook_id}'")
    if dev_window:
        src = src.replace(
            "backtest_end = datetime.datetime(2026, 9, 9)",
            "#: Development window end (exclusive). The hold-out (2026-07-01 to 2026-09-08) is\n"
            "    #: reserved and opened only in NB11 (03-smoothing-experiment-plan.md).\n"
            "    backtest_end = datetime.datetime(2026, 7, 1)",
        )
    for old, new in (extra_replacements or {}).items():
        assert old in src, f"cell6 replacement anchor not found: {old[:80]!r}"
        src = src.replace(old, new)
    return code(src)


def cell10(extra_source: str = ""):
    src = CELL10_ENHANCED
    if extra_source:
        assert "display_indicators(indicators)" in src
        src = src.replace("display_indicators(indicators)", extra_source.strip() + "\n\n\ndisplay_indicators(indicators)")
    return code(src)


def cell14(extra_replacements: dict | None = None):
    src = CELL14_ENHANCED
    for old, new in (extra_replacements or {}).items():
        assert old in src, f"cell14 replacement anchor not found: {old[:80]!r}"
        src = src.replace(old, new)
    return code(src)


def research_backtest_cell(name: str):
    """cell 16 unmodified apart from the run_backtest_inline `name=` label."""
    src = "".join(BASE["cells"][16]["source"])
    src = src.replace(
        'name="NB93 candidate with performance fee and redemption-capital accounting"',
        f'name="{name}"',
    )
    return code(src)


def harness_cell():
    return code(HARNESS)


def common_prefix_cells(notebook_id: str, cell6_replacements=None, cell10_extra=""):
    """Cells 1-10: notebook setup through indicators (heading cell 0 is added by the caller)."""
    return [
        base_cell(1), base_cell(2),
        base_cell(3), base_cell(4),
        base_cell(5), cell6(notebook_id, extra_replacements=cell6_replacements),
        base_cell(7), base_cell(8),
        base_cell(9), cell10(cell10_extra),
    ]


def common_suffix_cells(cell14_replacements=None):
    """Cells 11-14: time range through algorithm (backtest cell added separately by the caller)."""
    return [
        base_cell(11), base_cell(12),
        base_cell(13), cell14(cell14_replacements),
    ]


def integrity_and_audit_cells():
    """Cells 17-20: integrity check and redemption-fee audit, unmodified."""
    return [base_cell(17), base_cell(18), base_cell(19), base_cell(20)]


PLACEHOLDER = "_To be filled in after the run._"


def write_notebook(cells, out_path: Path):
    """Write the notebook, preserving a heading that already carries written-up findings.

    Headings are filled in after a run, by hand, from the actual results; the build scripts only
    carry the placeholder template. Rebuilding a notebook to re-run it would otherwise silently
    reset its findings back to placeholders - which happened once, after the harness fixes, and
    cost a full rewrite of seven headings. So: if the existing notebook's heading has no
    placeholder left and the incoming one does, keep the existing heading.
    """
    if out_path.exists() and cells and cells[0]["cell_type"] == "markdown":
        try:
            existing = json.load(open(out_path))
            existing_heading = "".join(existing["cells"][0]["source"])
            incoming_heading = "".join(cells[0]["source"])
            if PLACEHOLDER not in existing_heading and PLACEHOLDER in incoming_heading:
                cells = list(cells)
                cells[0] = {"cell_type": "markdown", "metadata": {}, "source": existing_heading.splitlines(keepends=True)}
                print(f"  (kept the existing written-up heading for {out_path.name})")
        except (KeyError, IndexError, ValueError):
            pass

    out = {"cells": cells, "metadata": BASE.get("metadata", {}), "nbformat": 4, "nbformat_minor": 5}
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"wrote {out_path} with {len(cells)} cells")
