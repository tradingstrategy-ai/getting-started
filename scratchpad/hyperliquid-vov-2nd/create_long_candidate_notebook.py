"""Build NB13 with a frozen 2026 shortlist and full-history comparison."""

from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent
HEADER = """# Experiment 13 — leading candidates over full available history

Based on [NB12](12-research-allocation-followup.ipynb), with earlier scoring and position-count candidates from [NB06](06-opt-score-3-4-inputs.ipynb) and [NB07](07-opt-score-position-count.ipynb). Earlier NB01–05 and NB08 executable results remain eligible in the shortlist inventory.

## Goal and method

Run our top ten best candidates by CAGR and Sharpe, new and old, over all available vault backtesting historical data. Select on repaired **2026-01-01 → 2026-10-05** engine performance: union of the top five CAGR and top five Sharpe strategies, then fill overlap to ten using the sum of both ranks. No long-period result is used to select the ten. Duplicate score references, inactive floor aliases and random-veto placebo controls are excluded. Pure feature/snapshot studies are not ranked as executable CAGR.

Replay the unchanged scoring, missing=True, original sizing/allocator and N for each candidate. Add source v11 and focal regularised90 as separately labelled benchmarks. First reproduce the saved 2026 performance, then run fresh $150,000 accounts over **2023-03-01 → 2026-10-08, exclusive end, UTC; the 7 October archive day is partial**, using all available pre-decision indicator history. Retain the source two-day cycle, inclusion/return gate, hysteresis, guard, fees, deposit/capacity checks, 33% concentration and pool limits, and 98% target allocation. NAV alone is causally forward-filled without pre-launch backfill; missing scores and young risk histories retain the original rules.

Hypothesis: recent leaders retain gains against v11 and regularised90 over the full period. This is retrospective robustness analysis; the long and short periods overlap and earlier years were already searched. We will examine all quarters, cash usage, individual positions, profit concentration and extreme valuation updates. Every chart has a separate heading, short explanation and explicit long-period title. Results are computed before conclusions are added.
"""


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md(HEADER),
        code("""from pathlib import Path
import sys
from IPython.display import display,Markdown
ROOT=Path.cwd()
if not (ROOT/'long_candidate_backtest.py').exists():ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from long_candidate_backtest import initialise,run,PERIOD
from long_candidate_report import shortlist,report
from score_matrix_visualisation import compact_output
"""),
        md("""## Freeze candidates and verify history — 2023-03-01 → 2026-10-08

Read existing comparable repaired-data results and pin source/data hashes. Freeze all ten identities before long replay. Verify the archive start/end and retain all indicator warmup."""),
        code("""with compact_output('Freeze shortlist and full-history operational inputs; estimated two–four minutes'):
    data,evaluator,chosen,pool=initialise()
shortlist(data,chosen,pool)
"""),
        md("""## Reproduce and replay — 2023-03-01 → 2026-10-08

Run each shortlisted strategy and two benchmarks on the original 2026 interval; require agreement with saved CAGR/Sharpe. Then run all available history with fresh accounts. The persistent cache is isolated to NB13 and includes computational hashes."""),
        code("""with compact_output('12 source-equivalence checks and 12 long-period replays; estimated 8–18 minutes'):
    summary,runs,robustness,absolute_weights,quarters=run(data,evaluator,chosen)
"""),
        md("""## Results, charts and attribution — 2023-03-01 → 2026-10-08

All comparisons default to full available history. Each chart is separate. Metrics use the inherited daily-resampled return convention; tails are recorded valuation updates rather than independently observed daily trades."""),
        code("""findings=report(data,summary,runs,robustness,absolute_weights,quarters)
(data['artifact']/'final-header.md').write_text(data['final_header'])
display(Markdown(f'[Detailed findings]({findings.name})'))
"""),
    ]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, ROOT / "13-backtest-leading-candidates.ipynb")


def finalise():
    """Refresh the computed heading after the observable runner's final save."""
    import json

    notebook = ROOT / "13-backtest-leading-candidates.ipynb"
    candidates = list((ROOT / "_artifacts-restored-2026-10-07/13").glob("*/final-header.md"))
    header = max(candidates, key=lambda p: p.stat().st_mtime)
    nb = nbformat.read(notebook, as_version=4)
    assert all(not any(o.output_type == "error" for o in c.get("outputs", [])) for c in nb.cells)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    nb.cells[0].source = header.read_text()
    nb.metadata["nb13"] = {"status": "complete", "artifact_generation": str(header.parent), "ten_candidates": 10, "additional_benchmarks": 2, "replication_checks": 24}
    nbformat.write(nb, notebook)
    return notebook


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
