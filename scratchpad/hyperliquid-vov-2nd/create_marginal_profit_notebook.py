"""Create and finalise experiment 21 while preserving executed notebook outputs."""

from pathlib import Path
import json
import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "21-research-marginal-profit-allocation.ipynb"
HEADER = """# Experiment 21 — marginal profitability and adaptive portfolio allocation

Based on [NB20](20-backtest-c00-vs-v11.ipynb), [NB18](18-backtest-conditional-cash-allocation.ipynb), [NB09](09-research-k-ratio-feature-forecasts.ipynb), and the [reviewed NB21 plan](21-marginal-profit-portfolio-plan.md).

**Goal:** increase net account profit by identifying capital worth investing, holdings worth retaining, and opportunities better left in cash. Challenge fixed six-position baskets, rank admission and prescribed inverse-variance allocation. Evaluate when positions are unlikely to profit, including young and missing-score vaults.

**Method:** reproduce C00/v11 under frozen NB20 accounting; audit fees and capital-weighted holding spells; fit monthly causal support, loss-probability, gain/loss-magnitude and calibrated-score forecasts; compare complete basis-aware hold/cash/top-up/replacement path values. Main challengers choose absolute allocations, breadth and cash under explicit capacity and estimated-downside budgets. Ten full-2026 accounts, a registered full-history shortlist and five local sensitivities. Features use completed prior daily buckets; preceding 2025 and earlier history remain available. Missing=True and sparse data use explicit masks/support priors. No untouched holdout exists.

## Key new insights

Pending execution.

## Summary of results

Pending execution.

## Robustness of results

Pending execution. Inherited fees, sparse NAV execution, retrospective inventory, forecast support, contributor concentration and numerical projection will be audited.
"""


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md(HEADER),
        code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'marginal_profit_data.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
import marginal_profit_data as inputs
import marginal_profit_forecasts as forecasts
import marginal_profit_allocation as allocation
import marginal_profit_report as reporting
from marginal_profit_checks import checks
from score_matrix_visualisation import compact_output
"""),
    ]
    stages = [
        ("Freeze inputs and verify control economics", "Retain the NB20 archive, source, guard and framework identities. Compare both full control equity paths, fees and holding spells before selecting a forecast horizon.", "with compact_output('Frozen inputs and controls; estimated 2–5 minutes'):\n    data,evaluator=inputs.initialise()\n    control_results,spells=inputs.controls(data,evaluator)\n    fresh_control_parity=reporting.fresh_control_checks(data,evaluator)\n    mechanism_checks=checks()\n    reporting.control_audit(data,control_results,spells,mechanism_checks)"),
        ("Construct the opportunity panel", "All operationally eligible and held vaults are retained. Forward-filled features and actual endpoint learning evidence are distinct; missing scores remain explicit.", "with compact_output('Causal features and labels; estimated 2–5 minutes'):\n    panel=inputs.build_panel(data,evaluator)\n    reporting.panel_audit(data)"),
        ("Fit chronological forecasts and register risk budgets", "Monthly fits use only matured past outcomes. P is a support baseline, D adds loss probability, M adds conditional magnitudes, and C calibrates the existing score. Register budgets before any challenger account results.", "with compact_output('Causal monthly forecasts; estimated 3–12 minutes'):\n    predictions=forecasts.build_forecasts(data)\n    budget_registration=allocation.register_budgets(data)\n    reporting.calendar_alignment(data,evaluator)\n    reporting.training_audit(data,budget_registration)"),
        ("Run ten complete-2026 accounts", "Every smoke row runs 1 January through 4 October. Compare the economic signal ladder, calibrated C00 score, six-slot ablation, incumbent management and budget removal.", "with compact_output('Ten complete-2026 accounts; estimated 5–20 minutes'):\n    results,runs,attribution,absolute_weights=allocation.run_smoke(data,evaluator)"),
        ("Replay the frozen historical shortlist", "Select at most three distinct challenger trade paths from 2026, then replay them and both controls from March 2023 through 7 October 2026. Models cold-start and budgets are established causally.", "with compact_output('Historical shortlist; estimated 5–15 minutes'):\n    results,runs,attribution,absolute_weights=allocation.run_long(data,evaluator,results,runs,attribution,absolute_weights)\n    results,runs,attribution,absolute_weights=reporting.extra_fee_control(data,evaluator,results,runs,attribution,absolute_weights)"),
        ("Run the registered local sensitivities", "Compare half/double risk budget, a seven-day policy package, a common calibration-error margin and restoration of the original return gate. These are fixed checks, not another optimiser search.", "with compact_output('Five local sensitivities; estimated 5–15 minutes'):\n    results,runs,attribution,absolute_weights=allocation.run_extensions(data,evaluator,results,runs,attribution,absolute_weights)"),
        ("Inspect signal calibration and economic outcomes", "Show separate scatter and reliability charts for each model/horizon. Quarterly colours, support, avoided loss and missed profit explain whether signals contain usable information.", "with compact_output('Signal calibration and opportunity analysis; estimated 1–3 minutes'):\n    reporting.signal_report(data)"),
        ("Compare 2026 portfolio outcomes", "Key metrics, equity, absolute weights, cash, breadth and quarterly PnL use the short history by default. Each chart is separate and names its backtesting period.", "reporting.portfolio_report(data,results,runs,attribution,absolute_weights,'2026')"),
        ("Compare full-history outcomes", "Full-history accounts start from cash and include every cold-start day. The 2026 and long calendars overlap and are not independent validation.", "reporting.portfolio_report(data,results,runs,attribution,absolute_weights,'Long')"),
        ("Audit robustness and record conclusions", "Reconcile actual trades, projected allocations, contributor concentration, largest NAV intervals, curator flags and BTC/ETH context. Record hypothesis verdicts and any gaps.", "with compact_output('Robustness, accounting and conclusions; estimated 1–4 minutes'):\n    findings=reporting.final_report(data,results,runs,attribution,absolute_weights)"),
    ]
    for title, description, source in stages:
        cells.extend([md(f"## {title}\n\n{description}"), code(source)])
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "nb21": {"status": "pending"}})
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, 4)
    folder = max((ROOT / "_artifacts-restored-2026-10-07/21").glob("*/final-header.md"), key=lambda p: p.stat().st_mtime).parent
    assert (folder / "complete.json").exists()
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = (folder / "final-header.md").read_text()
    nb.metadata["nb21"] = {"status": "complete", "artifact_generation": str(folder), "plan": "21-marginal-profit-portfolio-plan.md", **json.loads((folder / "complete.json").read_text())}
    nbformat.write(nb, PATH)
    findings = ROOT / "21-marginal-profit-findings.md"
    findings.write_text((folder / "findings.md").read_text())
    summary = ROOT / "summary.md"
    text = summary.read_text()
    marker = "\n## Experiment 21 — marginal profitability and adaptive portfolio allocation\n"
    if marker in text:
        text = text.split(marker)[0]
    summary.write_text(text.rstrip() + marker + "\n" + findings.read_text().split("\n", 1)[1] + "\n")


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
