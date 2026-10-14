"""Build and finalise NB15, keeping generated research artefacts ignored."""

from pathlib import Path
import nbformat
from allocation_comparison import LOGIC

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "15-backtest-allocation-vs-v11.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook(
        cells=[
            md("""# Experiment 15 — allocation candidates versus deployed v11

Based on [NB14](14-backtest-profitable-allocation.ipynb). Compare **A**, the four-input score with original 90-day inverse variance; **C**, its regularised variance challenger; **G**, its downside-risk challenger; and the deployed **hyper-ai-v11.py** source rules.

The goal is to determine whether the research ranking and sizing changes improve net profit, CAGR and risk relative to deployed v11. Run every strategy with fresh $150,000 capital over **2026-01-01 → 2026-10-05 exclusive** and **2023-03-01 → 2026-10-08 exclusive**, retaining all available indicator warmup. The full-history final archive day is partial. Keep each strategy's existing logic, use NB14's repaired data and shared as-of-observation NAV pricing, and reproduce A/C/G before interpreting the comparison.

2026 results appear first. Full-history tables and charts are explicitly labelled. Every chart is a separate image with its own subheading, explanation and backtesting dates.

<!-- Results -->

Results and robustness conclusions will be inserted after execution.
"""),
            md(LOGIC),
            code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'allocation_comparison.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from allocation_comparison import initialise,run,report
from score_matrix_visualisation import compact_output
"""),
            md("""## Load the common research environment

Pin the repaired archive, all pre-decision history, source strategy, guard and framework fingerprints. Reuse NB14's timing audit to set the common NAV convention. The v11 control retains its original score, sizing and source decision callback."""),
            code("""with compact_output('Pinned environment and cached NB14 timing controls; estimated 2–4 minutes'):
    data,evaluator=initialise()
"""),
            md("""## Execute four strategies over two periods

Eight independent full-engine backtests, each starting from $150,000. Check A/C/G against NB14 and reconcile successful fill timestamps, position counts, asset weights and profit. The long run carries its own portfolio through 2026; its final year is not the same account as the separate fresh-start 2026 backtest."""),
            code("""with compact_output('Four strategies × two periods; estimated 4–12 minutes'):
    results,runs,attribution,absolute_weights=run(data,evaluator)
"""),
            md("""## Compare returns, deployment and robustness

Tables show strategies side by side. Separate period sections include equity curves, quarterly returns, absolute asset weights and vault attribution for the largest account updates. BTC/ETH reference returns use the same actual NAV observation intervals."""),
            code("""with compact_output('Saved-state attribution and chart rendering; estimated 1–2 minutes'):
    findings=report(data,results,runs,attribution,absolute_weights)
"""),
        ],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
    )
    nbformat.write(nb, PATH)


def finalise():
    headers = list((ROOT / "_artifacts-restored-2026-10-07/15").glob("*/final-header.md"))
    header = max(headers, key=lambda p: p.stat().st_mtime)
    nb = nbformat.read(PATH, as_version=4)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = header.read_text()
    nb.metadata["nb15"] = {"status": "complete", "artifact_generation": str(header.parent), "strategies": 4, "periods": 2}
    nbformat.write(nb, PATH)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
