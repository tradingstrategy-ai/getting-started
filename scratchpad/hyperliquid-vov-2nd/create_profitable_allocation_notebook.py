"""Build and finalise the compact NB14 engine comparison notebook."""

from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "14-backtest-profitable-allocation.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md("""# Experiment 14 — more profitable allocation

Based on [NB13](13-backtest-leading-candidates.ipynb) and [NB12](12-research-allocation-followup.ipynb). Implements the [reviewed five-arm plan](14-profitable-allocation-plan.md).

The goal is to make the strategy more profitable by improving position sizing and deployment within caps. Freeze C03 ranking, six positions, missing=True and the source selection/trade rules. Compare original and regularised 90-day variance under sequential and simultaneous allocation, plus regularised downside sizing under sequential allocation. Net profit and CAGR lead the comparison; report drawdown, Sharpe, turnover and cash alongside them.

Run fresh $150,000 accounts over 2026-01-01 → 2026-10-05 exclusive and 2023-03-01 → 2026-10-08 exclusive, with all earlier indicator warmup. First trace saved trades to actual NAV timestamps; apply a common as-of observation pricing adapter if later prices were consumed. NAV filling is causal and actual update counts remain separate. Young/partial histories retain existing selection and peer fallback support. The downside hypothesis is that upward jumps should not automatically reduce future capital allocation; zero-loss histories remain regularised.

Results and robustness conclusions will be inserted after execution. Default output uses the 2026 period. Each chart has a separate heading, explanation and period title.
"""),
        code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'profitable_allocation.py').exists():ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from profitable_allocation import initialise,run
from profitable_allocation_report import setup,report
from score_matrix_visualisation import compact_output
"""),
        md("""## Fix the reference and pricing convention — 2026-01-01 → 2026-10-05 exclusive

Load pinned inputs and all pre-decision history, reproduce saved A/D controls and inspect successful fills. Choose the shared observation-time convention before new replays. No operational permission field is filled by the NAV rule."""),
        code("""with compact_output('Pinned inputs, four legacy parity controls and timing trace; estimated 2–4 minutes'):
    data,evaluator,preflight=initialise()
setup(data,preflight)
"""),
        md("""## Run five allocation methods over both periods

Ten required primary results: full 2026 and full available history. Preserve source trade generation while separating risk estimates from allocation. Then compare A and each period's leading challenger when trading requires a NAV observation within the previous two-day source cycle."""),
        code("""with compact_output('Five methods × two periods plus sparse-price sensitivities; estimated 8–20 minutes'):
    results,runs,attribution,absolute_weights,sensitivity=run(data,evaluator)
"""),
        md("""## Profit, attribution and robustness — 2026-01-01 → 2026-10-05 exclusive

Default charts and tables use fresh-start 2026. Explicitly labelled long-period results show previously searched calendar years and carried capital; those accounts end three days later than the fresh 2026 comparison."""),
        code("""findings=report(data,results,runs,attribution,absolute_weights,sensitivity)
"""),
    ]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, NOTEBOOK)


def finalise():
    candidates = list((ROOT / "_artifacts-restored-2026-10-07/14").glob("*/final-header.md"))
    header = max(candidates, key=lambda p: p.stat().st_mtime)
    nb = nbformat.read(NOTEBOOK, as_version=4)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert all(not any(o.output_type == "error" for o in c.get("outputs", [])) for c in nb.cells)
    nb.cells[0].source = header.read_text()
    nb.metadata["nb14"] = {"status": "complete", "artifact_generation": str(header.parent), "arms": 5, "periods": 2}
    nbformat.write(nb, NOTEBOOK)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
