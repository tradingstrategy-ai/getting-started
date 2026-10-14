"""Build expanded NB10 in place, preserving the first executed generation."""

from pathlib import Path
import shutil
import nbformat

ROOT = Path(__file__).resolve().parent


def build():
    path = ROOT / "10-research-portfolio-snapshots.ipynb"
    original = ROOT / "appendices/10-original-portfolio-snapshots.ipynb"
    if not original.exists():
        shutil.copy2(path, original)
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md("""# Experiment 10 — composite scores for ranking and portfolio allocation

## Goal and method

Expand the original [NB10 snapshot study](appendices/10-original-portfolio-snapshots.ipynb): inverse variance **and other metrics are ingredients inside per-vault scores**, with separate recipes for ranking and weighting. Build on the existing scoring variants and sparse-data feature definitions from experiments 04–09. This implements the [expanded reviewed plan](10-expanded-score-allocation-plan.md).

For example, `Q = (F + I90 + K90) / 3` is calculated for the full eligible universe before selecting a basket. Only the final Q is mapped into requested position weights. We compare arithmetic, geometric and minimum scores; standalone CAGR/Sharpe/Sortino/drawdown/Calmar/K; score sizing maps; score risk budgets; missing-data policies; six versus ten positions; and entry constraints.

The **smoke study runs 36 combinations over the full available 2026 history**, on a four-day decision cadence from 1 January to 4 October. It retains all **70 origins: 62 mature 30-day outcome windows, eight pending**. All available **2025 indicator warmup** and earlier recorded observations are retained for longer windows and maximum-history K. Sparse NAV is carried causally; observation counts and permission/capacity clocks remain separate. Young vaults remain eligible when long-window metrics are unavailable.

Each basket holds fixed units for 30 days. Overlapping snapshots give descriptive allocation comparisons, not executable strategy CAGR. Current universe/guard and publication-clock limitations remain. The ten-complete-block inference gate is unmet in 2026. The broader all-139 recipe and multi-horizon stages are proposed next work, not part of this executed smoke scope.

## Key new insights

On 62 common mature origins, adding the inverse-variance component to the focal weighting score improves mean 30-day return by **0.165 percentage points** versus focal-score sizing, and **0.145 points** versus a neutral-offset control. Including it in ranking instead reduces return by **1.112 points** versus the focal ranking/equal-sizing control. Keeping ranking fixed, the tested K weighting addition changes return by **−0.014 points**. These are specific recipe comparisons, not general metric verdicts.

## Summary of results

All **36 policies × 70 scheduled origins** completed. Exact source and focal equal-weight controls reproduce the original saved ledgers. There are **27 passing audit checks** and **15 separate inspected charts**, with matched budgets, pending labels, missingness, cap distortion and quarter/vault attribution reported. The proposed next-stage registry contains **334 unique standalone metric/lookback policies**, alongside the preserved inventory of 139 frozen scoring recipes; these broader stages have not been run.

## Robustness of results

The study retains 2025 warmup and earlier observations, forward-fills sparse NAV causally, and separates missing metrics from valid zeros. Independent arithmetic, source parity, historical NAV reconstruction and allocation checks pass. The calendar lacks the required ten complete blocks, so no statistical superiority or strategy promotion is claimed. Profit concentration, young-vault support and cash deployment need further matched checks. Snapshot returns are not strategy CAGR.

See [smoke findings](10-expanded-score-allocation-smoke-findings.md) for all matched effects, limitations and the exact next-stage scope.
"""),
        code("""from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Markdown
ROOT = Path.cwd()
if not (ROOT / 'portfolio_score_design.py').exists():
    ROOT = ROOT / 'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0, str(ROOT))
from portfolio_score_design import smoke_registry
from portfolio_score_components import read_inputs, build_components
from portfolio_score_pipeline import execute_smoke
from portfolio_score_audit import run_fixtures, run_audit
from portfolio_score_report import render_report, write_findings
from score_matrix_visualisation import compact_output
policies = smoke_registry()
"""),
        md("""## Independent numerical fixtures — 2026-01-01 → 2026-10-05; 30-day horizon

Before reading outcomes, check score arithmetic, missing versus valid zero, component order, sparse filling, sizing odds, zero allocations under caps and the K formula using independent calculations.
"""),
        code("""fixtures = run_fixtures()
display(fixtures)
"""),
        md("""## Pinned full history and indicator warmup — 2026-01-01 → 2026-10-05; 30-day horizon

Verify the archive, metadata, 139-recipe inventory and audited feature generation. Retain all 2025 and earlier input history; decision origins start in 2026. No outcomes are used to trim the grid or eligible universe.
"""),
        code("""with compact_output('Pinned full-history inputs; estimated under one minute'):
    data = read_inputs()
display(pd.DataFrame([{'Scheduled origins': len(data['origins']), 'Mature 30-day origins': 62, 'Pending origins': 8, 'Verified frozen recipes': len(data['registry']), 'Recorded NAV start': str(data['daily'].date.min()), 'Generation': data['fingerprint'][:16]}]))
"""),
        md("""## Eligible-universe component scores — 2026-01-01 → 2026-10-05; 30-day horizon

Transform metrics and estimate risk before selecting any baskets. Inverse-risk components use leave-one-out priors and genuine update counts. Missingness stays explicit; maximum-history K retains the first recorded anchor.
"""),
        code("""with compact_output('Causal component tensors; estimated one–two minutes'):
    tensors = build_components(data, policies)
display(tensors['feature_inventory'])
"""),
        md("""## Full-2026 restricted-combination smoke run — 2026-01-01 → 2026-10-05; 30-day horizon

Execute all 36 arms at every scheduled origin. Allocate before joining future labels; keep immature late dates in the ledger. Entry caps redistribute only to names with positive requested capital. Outcomes retain unresolved terminal weights and common-basket equal-budget comparisons.
"""),
        code("""with compact_output('36 policies × 70 origins; estimated one–three minutes'):
    result = execute_smoke(data, tensors, policies)
"""),
        md("""## Original-archive and saved-reference audit — 2026-01-01 → 2026-10-05; 30-day horizon

Reconstruct first-origin metrics from the full retained NAV, perturb future data, inspect support counts and risk contributions, and compare exact per-origin T00/T01 weights and returns with the original saved NB10 controls.
"""),
        code("""with compact_output('Independent warmup, causality and source parity checks'):
    audit = run_audit(data, tensors, result, policies)
"""),
        md("""## Smoke results and allocation mechanisms — 2026-01-01 → 2026-10-05; 30-day horizon

Each table and separate figure below has its own description. Means use mature resolved support; pending Q4 remains visible. Matched effects and cash diagnose the mechanisms rather than promoting a strategy from researched history.
"""),
        code("""figures = render_report(data, tensors, result, audit, policies)
"""),
        md("""## Findings and next-stage inventory — 2026-01-01 → 2026-10-05; 30-day horizon

Write the smoke conclusions and the exact proposed standalone metric/lookback policy registry. Broad stages remain unexecuted; the smoke stage ends after audit, rendering and findings.
"""),
        code("""findings = write_findings(data, result, audit)
next_stage = __import__('json').loads((data['artifact'] / 'next-stage-registry.json').read_text())
display(pd.DataFrame([{'Audits passed': int(audit.passed.sum()), 'Smoke policies': 36, 'Scheduled origins': 70, 'Separate figures': len(figures), 'Proposed A0 policies (not run)': next_stage['unique_policies'], 'Execution seconds': data['execution_seconds']}]))
display(Markdown('[Detailed smoke findings](10-expanded-score-allocation-smoke-findings.md)'))
"""),
    ]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, path)


if __name__ == "__main__":
    build()
