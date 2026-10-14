"""Build NB19 and keep one heading/description per displayed element."""

from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "19-backtest-protected-core-score-risk-allocation.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook(
        cells=[
            md("""# Experiment 19 — protected core with score and risk sizing

Based on [NB18](18-backtest-conditional-cash-allocation.ipynb) and the exact corrected-fee C-W benchmark from NB16/17.

**Goal:** test whether more than six positions increase net profit while controlling weaker additional holdings through position weights. Preserve C00's selection, entry6/exit8, regularised 90-day inverse-variance waterfall and source execution rules. C00 is a research benchmark, not deployed v11.

**Hypotheses:** extra breadth helps; performance score and risk jointly improve sizing; absolute tickets outperform normalised score × risk; holding units reduces turnover; eight/ten/twelve slots offer different economic trade-offs; findings survive smaller caps and a lower score floor.

**Method:** source-authoritative six-slot core; additional candidates retain source score/address order, without a rank cutoff. Compare flat, risk-only, score-only and combined tickets. Regularised daily variance uses 90 days, 30 actual-update shrinkage and a fixed eligible leave-one-out peer pool. Risk multiplier is `min(1, sqrt(peer prior / predicted variance))`; score multiplier is `0.5 + 0.5*clip(score,0,1)`, with missing scores using the 0.5 floor. Entry ticket is half the 5% single-position gross cap, multiplied before capacity clipping. Additional gross exposure is capped at 25%; unspent reductions remain cash. Hold means retaining shares, with source eligibility, hard caps and core-funding recalls. Resize and normalised controls use the same candidate order. Missing histories remain eligible when the causal peer risk prior is supported. Sparse NAV is carried forward after inception; actual updates and ages remain separate.

**Periods:** fresh $150,000 accounts for **2026-01-01 → 2026-10-05 exclusive** and **2023-03-01 → 2026-10-08 exclusive**, with all earlier warmup including 2025. Two-day decisions and as-of recorded NAV. The last archive day is partial. 2026 is the default for tables/charts; full history appears separately. These searched, overlapping histories provide no untouched validation.

[Plan and formulas](19-protected-core-score-risk-allocation-plan.md) · [Claude review](19-protected-core-score-risk-allocation-review.md)

Results pending execution.
"""),
            code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'protected_core_score_allocation.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from protected_core_score_allocation import initialise,controls,run
from score_matrix_visualisation import compact_output
"""),
            md("""## Freeze repaired inputs

Verify inherited archive, strategy and framework identities before creating a separate NB19 artefact generation. All preceding indicator history remains available."""),
            code("""with compact_output('Pinned inputs; estimated 2–4 minutes'):
    data,evaluator=initialise()
from protected_core_score_checks import algebra
from IPython.display import Markdown,display
display(Markdown('### Formula and sparse-data checks — both registered periods\\n\\nIndependent fixtures verify tickets, clipped capacity, normalised budgets, missing risk and causal forward filling.'))
checks=algebra()
checks.to_csv(data['artifact']/'algebra-checks.csv',index=False)
display(checks.style.hide(axis='index'))
"""),
            md("""## Source authority and zero-extra parity

Replay historical C00 and the new adapter with no extra allocation for both periods. Require identical complete equity curves, trade times, quantities, prices and reserves before running treatments."""),
            code("""with compact_output('Historical controls and zero-slot replay; estimated 5–10 minutes'):
    control_runs=controls(data,evaluator)
from IPython.display import display,Markdown
display(Markdown('### Complete control parity — both registered periods\\n\\nExact equality checks for historical source C-W versus the zero-extra adapter. This establishes adapter parity before treatment trajectories diverge.'))
import pandas as pd
display(pd.read_csv(data['artifact']/'control-parity.csv').style.hide(axis='index'))
"""),
            md("""## Execute registered independent accounts

Nine primary methods in each period, followed by the two registered sensitivities when combined fresh tickets are active. Every completed account and diagnostic ledger is saved. The source core targets are captured before extras and checked after merging; executable buys give the core priority."""),
            code("""with compact_output('Eighteen primary accounts and four sensitivities; estimated 15–35 minutes'):
    results,runs,attribution,absolute_weights=run(data,evaluator)
"""),
            md("""## Economic outcomes and mechanism evidence

Read profit and risk alongside cash, actual funded breadth, ticket activation, turnover, costs and individual contributors. Every chart is displayed separately with its own heading and description."""),
            code("""from protected_core_score_report import report
with compact_output('Reporting and robustness; estimated 2–4 minutes'):
    findings=report(data,results,runs,attribution,absolute_weights,evaluator)
"""),
        ],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "nb19": {"status": "in progress"}},
    )
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, 4)
    folder = max((ROOT / "_artifacts-restored-2026-10-07/19").glob("*/final-header.md"), key=lambda p: p.stat().st_mtime).parent
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = (folder / "final-header.md").read_text()
    nb.metadata["nb19"] = {"status": "complete", "artifact_generation": str(folder), "economic_accounts": 22, "zero_extra_parity_accounts": 2, "historical_reference_accounts": 2, "same_state_diagnostic_accounts": 1, "periods": 2}
    nbformat.write(nb, PATH)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
