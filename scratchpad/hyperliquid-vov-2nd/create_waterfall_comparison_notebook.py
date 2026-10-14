"""Create and finalise the NB15 waterfall variant."""

from pathlib import Path
import nbformat
from waterfall_comparison import LOGIC

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "16-backtest-waterfall-allocation-vs-v11.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook(
        cells=[
            md("""# Experiment 16 — waterfall allocation versus NB15

Based on [NB15](15-backtest-allocation-vs-v11.ipynb). Repeat deployed V11, four-input A, regularised-variance C and regularised-downside G with the framework's capped waterfall allocator. Compare every treatment with its exact original allocator.

The goal is to improve economic outcomes and determine whether waterfall reduces capacity-related cash. Keep six positions, the original score and risk recipes, all admission/exit rules, caps, costs and as-of-observation NAV pricing. Waterfall fills selected vaults by descending raw risk-sizing weight; it does not expand the basket or rerank candidates by capacity.

Run fresh $150,000 accounts over **2026-01-01 → 2026-10-05 exclusive** and **2023-03-01 → 2026-10-08 exclusive**, with all available earlier indicator warmup. The final full-history archive day is partial. Show 2026 first, separate all images, and give every table/chart a subheading, description and explicit period.

<!-- Results -->

Results will be inserted after execution.
"""),
            md(LOGIC),
            code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'waterfall_comparison.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from waterfall_comparison import initialise,run,report
from score_matrix_visualisation import compact_output
"""),
            md("""## Load the matched environment

Reuse NB15's repaired archive, source/framework fingerprints and causal NAV convention. Establish a separate cache generation for waterfall treatments; original controls use their saved NB15 engine accounts."""),
            code("""with compact_output('Pinned NB15 environment and timing controls; estimated 2–4 minutes'):
    data,evaluator=initialise()
"""),
            md("""## Execute matched original and waterfall accounts

Eight original-control replays and eight waterfall treatments cover both periods. Verify exact NB15 control metrics, pre-admission target caps, held-position limits, realised asset weights, profit and known-NAV fill timing."""),
            code("""with compact_output('Eight waterfall treatments and eight matched controls; estimated 4–15 minutes'):
    results,runs,attribution,absolute_weights=run(data,evaluator)
"""),
            md("""## Compare outcomes and investigate cash

Side-by-side metrics, matched differences, equity curves, quarterly returns, cash histories and absolute waterfall asset weights appear separately for each period. September cash and vault attribution test the capacity explanation and dependence on extreme updates."""),
            code("""with compact_output('Period comparisons, attribution and rendering; estimated 1–2 minutes'):
    findings=report(data,results,runs,attribution,absolute_weights)
"""),
        ],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
    )
    nbformat.write(nb, PATH)


def finalise():
    header = max((ROOT / "_artifacts-restored-2026-10-07/16").glob("*/final-header.md"), key=lambda p: p.stat().st_mtime)
    nb = nbformat.read(PATH, as_version=4)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = header.read_text()
    nb.cells[1].source = LOGIC
    nb.metadata["nb16"] = {"status": "complete", "artifact_generation": str(header.parent), "accounts": 16, "periods": 2}
    nbformat.write(nb, PATH)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
