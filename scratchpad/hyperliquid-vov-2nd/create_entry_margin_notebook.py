"""Build/finalise the staged NB22 notebook without modifying earlier experiments."""

from pathlib import Path
import json
import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "22-research-c00-entry-margin-calibration.ipynb"
HEADER = """# Experiment 22 — C00 entry-margin calibration

Parent: [NB20 clean C00/v11 comparison](20-backtest-c00-vs-v11.ipynb) and [NB21 marginal-profit forecasts](21-research-marginal-profit-allocation.ipynb). Implementation of the [reviewed NB22 plan](22-c00-attribution-and-opportunity-calibration-plan.md).

**Goal:** improve net profit by identifying fresh C00 entries worth declining, while preserving its successful selection and sizing. Test separately whether existing signals rank opportunities near the admission boundary and whether their absolute net-return levels justify leaving an entry in cash. Keep young and missing-score vaults eligible.

**Method:** audit saved C00 initial-entry cohorts using proportional attribution of actual sale proceeds; register a two- or seven-day horizon against fully matured pre-2026 managed spells. Define a state-independent entry-eligible rank-1–8 band before outcomes. Reuse causal monthly NB21 D distributions, calibrating the common net-return level and within-origin spread separately on matured past paired rows. Allow sparse NAV carrying after inception, require subsequent actual reporting for primary endpoints and retain unresolved outcomes explicitly. Compare a fixed supported non-positive-entry veto with 999 identity and calendar-block ledger controls. Qualify exclusively on closed pre-2026 spells before inspecting 2026 forecast outcomes. Run C00, one veto policy and five causal random-entry controls on both calendars only if all registered checks pass and the 2026 rule activates. Otherwise finish the ledger/calibration study with an explicit stop verdict. The optional component factorial is not automatically run.

**Periods:** fresh $150,000 accounts, 2026-01-01–2026-10-04 UTC; independent full history 2023-03-01–2026-10-07 UTC, final day partial. Preceding history, including 2025, supplies warm-up. Both use NB20's frozen repaired archive and common accounting. Inherited charges (10% of positive redemption profit plus 0.1% capital allowance) are assumptions; no extra NAV slippage. No untouched holdout exists.

## Key new insights

Pending execution.

## Summary of results

Pending execution.

## Robustness of results

Pending execution. Sparse reporting, retrospective eligibility, assumed charges, selection of closed spells, repeated vaults and overlapping researched history limit inference.
"""


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md(HEADER),
        code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'entry_margin_data.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
import entry_margin_data as inputs
import entry_margin_calibration as calibration
import entry_margin_report as reporting
from score_matrix_visualisation import compact_output
"""),
    ]
    stages = [
        ("Freeze inputs and validate saved controls", "Verify repaired data hashes, frozen forecast modules, parent generations, all four saved equity paths and complete trade signatures. No new economic account is needed for these checks.", "with compact_output('NB22 input and saved-state parity; approximately 1 minute'):\n    data=inputs.initialise()\nreporting.input_report(data)"),
        ("Attribute actual entry spells", "Tag first-buy units separately from top-ups. Every sale allocates actual net cash proportionally to remaining units; ending liquidation values use the same tags. Frozen-ledger losses are headroom, not a policy profit bound.", "spells=inputs.entry_spells(data)\nreporting.ledger_report(data,'2026')"),
        ("Construct the narrow opportunity population", "Rank source entry-eligible vaults by C00 score then address. Keep ranks 1–8 plus actual executed entrants outside the band. Mathematical per-dollar labels carry observations causally but remain unresolved beyond the last actual report.", "with compact_output('NB22 band, sparse labels and D distribution parity; approximately 1–2 minutes'):\n    panel=inputs.build_panel(data)\n    horizon_registration=inputs.register_horizon(data)\nreporting.population_report(data)"),
        ("Fit monthly out-of-time calibration", "Separate the equal-origin pooled level from within-origin signal slope on the same matured paired rows. Missing or pooled D cannot veto; confidence intervals use 999 horizon-length calendar-block resamples.", "with compact_output('NB22 chronological paired calibration; approximately 1 minute'):\n    forecasts=calibration.calibrate(data)"),
        ("Register the pre-2026 qualification verdict", "The primary gate uses fully closed pre-2026 initial-unit managed returns. Preserve proposal identities and cash amounts before masking outcomes. Check identity and quarter/support-era block controls, mark-only sensitivity and missing-outcome break-even levels. Count 2026 activation without reading its outcomes.", "with compact_output('NB22 999 ledger seeds per control; approximately 1–5 minutes'):\n    registration=calibration.qualify(data)\n    rates=calibration.causal_reference_rates(data)\nreporting.qualification_report(data)"),
        ("Inspect complete-2026 forecast results", "Open the 2026 outcome reports after the qualification file exists. Every scatter is separate, names its horizon/period and retains quarterly colours. Report levels and relative discrimination separately.", "reporting.signal_report(data,'2026')\nreporting.activation_report(data,'2026')"),
        ("Run conditional whole-entry accounts", "If qualified and active, suppress only funded fresh buys after C00 allocation. Keep all other intentions and trades, leave the slot empty, and compare against five causally seeded random vetoes on both complete calendars. A registered stop produces an explicit status table.", "with compact_output('NB22 conditional accounts; approximately 0–20 minutes'):\n    accounts=reporting.conditional_accounts(data)\nreporting.account_report(data,'2026')"),
        ("Inspect the independent long account", "The long account starts from cash in March 2023; its 2026 segment carries prior wealth. Unsupported early forecasts pass through C00. The horizon/qualification configuration is retrospectively selected, despite causal monthly fits.", "reporting.ledger_report(data,'Long')\nreporting.long_signal_report(data)\nreporting.account_report(data,'Long')"),
        ("Record verdicts and limitations", "Explain the mechanism actually demonstrated, executed and stopped stages, missing-report sensitivity, repeated-vault dependence and next leads. The optional eight-cell current-accounting factorial remains unexecuted.", "findings=reporting.finalise_results(data)\nreporting.verdict_report(data)"),
    ]
    for title, desc, src in stages:
        cells.extend([md(f"## {title}\n\n{desc}"), code(src)])
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "nb22": {"status": "pending", "plan": "22-c00-attribution-and-opportunity-calibration-plan.md"}})
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, 4)
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    import re

    recorded = []
    for cell in nb.cells:
        for output in cell.get("outputs", []):
            value = output.get("data", {}).get("text/markdown", "")
            recorded.extend(re.findall(r"\*\*Executed artefact generation:\*\* `([^`]+)`", value))
    assert len(recorded) == 1, "Notebook must contain exactly one executed generation"
    folder = Path(recorded[0])
    nb.metadata["nb22"]["artifact_generation"] = str(folder)
    complete = json.loads((folder / "complete.json").read_text())
    nb.cells[0].source = (folder / "final-header.md").read_text()
    # Terminal progress remains observable, while the saved notebook has no stream wall.
    for c in nb.cells:
        if c.cell_type == "code":
            c.outputs = [o for o in c.outputs if o.output_type != "stream"]
    nb.metadata["nb22"].update(status="complete", **complete)
    nbformat.write(nb, PATH)
    (ROOT / "22-c00-entry-margin-findings.md").write_text((folder / "findings.md").read_text())
    summary = ROOT / "summary.md"
    text = summary.read_text()
    marker = "\n## Experiment 22 — C00 entry-margin calibration\n"
    section = marker + "\n" + (folder / "findings.md").read_text().split("\n", 1)[1] + "\n"
    if marker in text:
        start = text.index(marker)
        following = text.find("\n## Experiment ", start + len(marker))
        text = text[:start] + section + (text[following:] if following != -1 else "")
    else:
        text = text.rstrip() + section
    summary.write_text(text)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
