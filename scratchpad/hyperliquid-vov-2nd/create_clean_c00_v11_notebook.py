"""Build and finalise the clean NB20 comparison notebook."""

from pathlib import Path
import json
import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "20-backtest-c00-vs-v11.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook(
        cells=[
            md("""# Experiment 20 — C00 versus deployed v11 rules

Based on [NB19](19-backtest-protected-core-score-risk-allocation.ipynb) and [NB15](15-backtest-allocation-vs-v11.ipynb).

**Goal:** clean comparison of the two strategies on identical data and accounting, for 2026 and full history. Fresh $150,000 accounts, common as-of NAV, partial-sell fee correction, fresh-entry tax reset and final-proceeds funding. Preserve each strategy's score, sizing and allocation method. No parameter optimisation. Results pending execution."""),
            code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'clean_c00_v11_comparison.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from clean_c00_v11_comparison import initialise,run,report
from score_matrix_visualisation import compact_output
"""),
            md("""## Freeze shared inputs

Use the repaired archive and the same frozen strategy/framework identities as NB19. Retain all available warmup; no data downloads or parameter search."""),
            code("with compact_output('Shared data and source identity; estimated 2–4 minutes'):\n    data,evaluator=initialise()"),
            md("""## Execute four independent accounts

Replay V11 and C00 for 2026 and full history. Both start from cash under identical accounting corrections. Require C00 to reproduce NB19 before reporting comparative results."""),
            code("with compact_output('Four full-engine replays; estimated 4–10 minutes'):\n    results,runs,attribution,absolute_weights=run(data,evaluator)"),
            md("""## Compare outcomes and inspect robustness

Each period has side-by-side metrics, overlaid equity/drawdown/cash charts, separate absolute asset-weight charts and quarterly returns. Individual vault contributions and strongest-update market context explain concentrated results."""),
            code("with compact_output('Charts, accounting and curator audit; estimated 1–3 minutes'):\n    findings=report(data,results,runs,attribution,absolute_weights)"),
        ],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "nb20": {"status": "pending"}},
    )
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, 4)
    folder = max((ROOT / "_artifacts-restored-2026-10-07/20").glob("*/final-header.md"), key=lambda p: p.stat().st_mtime).parent
    assert (folder / "complete.json").exists()
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = (folder / "final-header.md").read_text()
    nb.metadata["nb20"] = {"status": "complete", "artifact_generation": str(folder), "economic_accounts": 4, "periods": 2}
    nbformat.write(nb, PATH)
    summary = ROOT / "summary.md"
    text = summary.read_text()
    marker = "\n## Experiment 20 — C00 versus deployed v11 rules\n"
    if marker in text:
        text = text.split(marker)[0]
    body = (folder / "final-header.md").read_text().split("## Key new insights")[1]
    summary.write_text(text.rstrip() + marker + "\n**Examined:** C00 versus v11, with common data and accounting, in 2026 and full history.\n\n**Hypothesis:** C00 improves net economic outcomes over the deployed-rule strategy. The comparison is descriptive; no independent significance claim.\n\n### Findings and useful leads\n" + body.replace("## Summary of results", "### Summary of results").replace("## Robustness of results", "### Robustness of results") + "\n")


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
