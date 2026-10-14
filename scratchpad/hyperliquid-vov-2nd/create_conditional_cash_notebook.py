"""Create and finalise the reviewed conditional-cash experiment notebook."""

from pathlib import Path
import json
import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "18-backtest-conditional-cash-allocation.ipynb"


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    nb = nbformat.v4.new_notebook(
        cells=[
            md(r"""# Experiment 18 — conditional cash allocation

Based on [NB17](17-backtest-capacity-aware-allocation.ipynb). **Goal:** allocate extra cash when it increases profits, while avoiding excessive additional risk. Six core positions are a benchmark, not a demonstrated optimum. Better cash utilisation alone is not success.

**Hypotheses:** a limited-risk sleeve improves on unconditional overflow; score-conditioned admission adds value; gradual sizing improves on a binary gate; additional positions complement the protected core; benefits survive sparse/missing data, costs and contributor checks.

**Method:** preserve the established four-input score and regularised 90-day inverse-variance core. Compare three corrected-fee controls and six conditional sleeves, with a causal lagged risk reference, capped inverse-volatility relative sizing, monthly score-band forecasts, scenario-based exits, and a gradual quadratic-growth sizing rule. Forecasts use four-day origins, mature 30-day outcomes and equal date weights; 7/90 days are diagnostics. Missing composites remain a separate group. Sparse NAV is causally carried forward, without inventing observations or terminal redemptions.

**Periods:** fresh \$150,000 accounts over **2026-01-01 → 2026-10-05 exclusive** and **2023-03-01 → 2026-10-08 exclusive** (last archive day partial), with all earlier warmup and calibration history. All accounts correct repeated partial-trim fees. These researched, overlapping periods are not an independent holdout.

The [reviewed plan](18-conditional-cash-allocation-plan.md) and [Claude Fable 5.1 contributions](18-conditional-cash-allocation-review.md) contain formulas, assumptions and registered contrasts.

Results will be inserted after execution.
"""),
            code("""from pathlib import Path
import sys
ROOT=Path.cwd()
if not (ROOT/'conditional_cash_allocation.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from conditional_cash_allocation import initialise,controls,prepare,run,METHODS,REGISTRY
from score_matrix_visualisation import compact_output
"""),
            md("""## Freeze inputs and check formulas

Reuse the pinned NB17 archive, source and framework identity. Check sparse label maturity, missing-score handling, net payoff, capped allocation and the gradual-sizing algebra before running accounts."""),
            code("""with compact_output('Pinned inputs and algebra; estimated 2–4 minutes'):
    data,evaluator=initialise()
"""),
            md("""## Reproduce corrected controls

Run/load exact C-W, the matched admission-aware core and unconditional four-slot overflow. Verify both saved fee-corrected controls to the cent and reproduce the full-history reference before fitting any treatment forecast."""),
            code("""with compact_output('Six corrected controls; estimated 2–10 minutes'):
    control_runs=controls(data,evaluator)
from conditional_cash_report import turnover,heading,table
heading('Reference holding durations before forecasting','Replicated corrected NB17 controls. Closed-position lifetimes include the core; C02 is the unconditional overflow reference. The registered 30-day horizon stays fixed even when actual holdings last longer or shorter.','2026')
reference_durations=turnover(data,control_runs)
reference_durations.to_csv(data['artifact']/'reference-holding-duration.csv',index=False)
table(reference_durations[reference_durations.Period.eq('2026')].drop(columns='Period'))
"""),
            md("""## Build causal forecasts and fresh-proposal shadows

Use current as-of eligibility and capacity, the latest completed reference core, and actual observations around every label endpoint. Freeze monthly models after strict label maturity. Build a common fixed-peer sparse risk layer and lagged normalised core risk anchor. Inspect full-2026 proposal, gate, slot, cap, stress and core-top-up diagnostics without sleeve feedback."""),
            code("""with compact_output('Causal panel, monthly calibration and shadows; estimated 2–5 minutes'):
    prepare(data,evaluator)
"""),
            md("""## Execute the registered independent accounts

Run every registered method over the complete 2026 period, then full history. Protect core targets/funding, reconcile PnL and verify fills against previously observed NAV. Save each completed account and its mechanism ledger for recovery."""),
            code("""with compact_output('Eighteen corrected-fee accounts; estimated 10–25 minutes'):
    results,runs,attribution,absolute_weights=run(data,evaluator)
"""),
            md("""## Interpret profits, risk and deployment

2026 is the default for every table and separate chart below; full history has its own explicit section. Each element explains its economic meaning and limitations. Report inactivity and negative results as well as improvements."""),
            code("""from conditional_cash_report import report
with compact_output('Economic reporting and figures; estimated 1–3 minutes'):
    findings=report(data,results,runs,attribution,absolute_weights)
"""),
        ],
        metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "nb18": {"status": "implementation in progress"}},
    )
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, as_version=4)
    folder = max((ROOT / "_artifacts-restored-2026-10-07/18").glob("*/final-header.md"), key=lambda p: p.stat().st_mtime).parent
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    nb.cells[0].source = (folder / "final-header.md").read_text()
    nb.metadata["nb18"] = {"status": "complete", "artifact_generation": str(folder), "primary_accounts": 18, "periods": 2, "fee_convention": "corrected partial trims"}
    nbformat.write(nb, PATH)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
