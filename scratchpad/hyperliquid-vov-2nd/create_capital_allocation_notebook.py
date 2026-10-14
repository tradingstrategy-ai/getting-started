"""Build/finalise the capital-allocation comparison notebook."""

from pathlib import Path
import json
import re
import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "17-backtest-capacity-aware-allocation.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    plan = (ROOT / "17-capital-allocation-plan.md").read_text()
    nb = nbformat.v4.new_notebook(
        cells=[
            md("""# Experiment 17 — better capital allocation

Based on [NB16](16-backtest-waterfall-allocation-vs-v11.ipynb). **Goal:** earn more net profit with better use of capital, testing redistribution, capacity-aware replacement, conditional overflow, turnover restraint and joint selection/sizing. Lower cash alone is not success.

Fourteen predeclared methods use the same four-input score, source gates, regularised 90-day risk package and causal NAV pricing. Run fresh $150,000 accounts over **2026-01-01 → 2026-10-05 exclusive**, and **2023-03-01 → 2026-10-08 exclusive**, keeping all preceding history, including 2025 indicator warmup. The last full-history archive day is partial. The primary engine retains source cost conventions; baseline/profit leaders also receive a shared corrected-partial-trim-fee sensitivity.

Methods and formulas were reviewed twice with Claude Fable 5.1. The [complete plan](17-capital-allocation-plan.md) and [review](17-capital-allocation-review.md) document missing/sparse-history support, core/overflow roles, global 0.5% close-weight floors, executable capacity, final-net-proceeds funding and score-proxy limitations.

<!-- Results -->

Results will be inserted after execution.
"""),
            md(plan[plan.index("## Fixed inputs") : plan.index("## Economic evaluation")]),
            code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'capital_allocation.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from capital_allocation import initialise,run,sensitivities
from score_matrix_visualisation import compact_output
"""),
            md("""## Load pinned inputs and check formulas

Verify NB16 source/data/framework identities and the reviewed algebra, including the binding-budget cardinality counterexample. Keep a separate fingerprinted generation for each allocation implementation."""),
            code("""with compact_output('Pinned inputs and mathematical checks; estimated 2–4 minutes'):
    data,evaluator=initialise()
"""),
            md("""## Execute the registered methods in both periods

The first run covers the entire 2026 history with prior warmup, then every method receives the full-history run. Exact C-W benchmark parity, target feasibility, known-NAV timing, funded trades, holdings and position-profit reconciliation are checked before reporting."""),
            code("""with compact_output('28 capital-allocation accounts; estimated 10–30 minutes'):
    results,runs,attribution,absolute_weights=run(data,evaluator)
"""),
            md("""## Check sensitivity to the partial-trim fee convention

Run the union of the benchmark and each period’s profit leader in both periods, correcting only the repeated fee on partial-trim mid-prices. These results are separate from primary legacy-fee comparisons."""),
            code("""with compact_output('Shared corrected-fee shortlist; estimated 2–8 minutes'):
    fee_sensitivity=sensitivities(data,evaluator,results)
"""),
            md("""## Compare economic results and capital usage

Fresh 2026 is the default. Tables and separate figures explain incremental profit, cash, capacity, turnover, role support and contributor dependence; full-history results have their own labelled section."""),
            code("""from capital_allocation_report import report
with compact_output('Economic reporting and rendering; estimated 1–3 minutes'):
    findings=report(data,results,runs,attribution,absolute_weights,fee_sensitivity)
"""),
        ],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
    )
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, as_version=4)
    header = max((ROOT / "_artifacts-restored-2026-10-07/17").glob("*/final-header.md"), key=lambda p: p.stat().st_mtime)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = header.read_text()
    for cell in nb.cells:
        if cell.cell_type == "markdown":
            cell.source = cell.source.replace(r"\[", "$$").replace(r"\]", "$$")
            cell.source = re.sub(r"(?<!\\)\$(?=[+-]?[0-9])", r"\\$", cell.source)
    nb.metadata["nb17"] = {"status": "complete", "artifact_generation": str(header.parent), "primary_accounts": 28, "periods": 2}
    nbformat.write(nb, PATH)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
