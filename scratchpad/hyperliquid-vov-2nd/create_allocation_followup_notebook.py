"""Create NB12 as a variant of NB11's fixed-selection research."""

from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent
HEADER = """# Experiment 12 — local sensitivity, constraint-aware allocation and engine replay

Based on [NB11](11-research-weighting-sizing.ipynb) and its [registered follow-up design](11-weighting-sizing-plan.md).

## Goal and method

Run the 12 registered local sensitivity combinations and eight constraint-aware allocation combinations, keeping regularised 90-day inverse variance as the benchmark. Then replay a small interpretable shortlist through the full trading engine. Keep the same six-vault focal_four and v11 selectors, their score recipes and missing=True behaviour. Determine whether nearby windows, prior strength, raw variance floors or caps inside allocation improve outcomes.

Sensitivities: two selectors × lookback 75/105 days; two selectors × kappa 10/90 actual updates at 90 days; two selectors × raw variance floors 1e-10/1e-6. Constraints: two selectors × equal/frozen-score risk budgets × projected/constrained convex allocations, with identical covariance, support and invested budget. The convex objective is variance minus calibrated weighted log diversification; it does not promise exact risk budgets under caps. All inherited numerical conditioning is recorded.

**2026-01-01 → 2026-10-05, exclusive end, UTC**, retaining all 2025 and earlier warmup. Snapshot origins every four days;7/30/90-day horizons. NAV alone is causally forward-filled, with no pre-launch backfill; actual observations remain distinct. Young vaults use partial empirical risk or the peer prior. Missing scores retain the frozen selection tier; zero score risk budgets get zero capital unless the entire target is zero. Unsupported terminal targets remain unresolved.

Engine replays use actual source decision/fill timing, two-day rebalancing, changing holdings, source hysteresis, operational deposit checks and applicable fees. Research sizing uses a common simultaneous cap projection; source v11 is a separate unchanged sequential-allocation control. Shortlist selection is retrospective and disclosed before reading engine results. There is no fresh holdout, and only eight complete primary 30-day blocks. Snapshot returns are not strategy CAGR.

## Key new insights

The original four-input score with source inverse-variance sizing and allocation remains strongest: **51.77% CAGR, 2.30 Sharpe, −6.35% maximum drawdown**. No replayed candidate beats it. A small sparse-estimator gain survives against the regularised benchmark, but adjacent-window and prior-strength snapshot improvements do not consistently survive full execution. Optimising with caps improves all four projected snapshot risk-budget pairs, yet trails the regularised inverse-variance benchmark; the engine cap effect is mixed.

Raw-floor changes are economically inactive on the selected baskets. The best snapshot sensitivities are 75 days for the four-input selector and kappa 90 for v11; engine CAGR changes are respectively +0.32 and −1.27 percentage points against their regularised 90-day benchmarks. This is a historical parameter comparison, not evidence of generalisation.

## Summary of results — 2026-01-01 → 2026-10-05

Completed **12 sensitivities + eight cap-aware policies + ten reproduced NB11 controls** over 70 origins and 7/30/90-day targets. Replayed 14 research/control policies plus two original strategy controls through the full engine. Full available 2026 evaluation history and earlier warmup are retained.

### Executable comparison

The table reports engine performance, including source holdings, trade thresholds and applicable fees. F means the four-input selector; L means v11 selection. Research allocations use a common simultaneous cap projection; original strategy controls retain their sequential allocator.

| Selection | Allocation | CAGR | Sharpe | Maximum drawdown |
| --- | --- | ---: | ---: | ---: |
| F | Original source sizing and allocator | **51.77%** | **2.30** | **−6.35%** |
| F | Regularised90-day inverse variance | 46.60% | 2.09 | −7.05% |
| F | Sparse gap-adjusted90-day inverse variance | 47.46% | 2.12 | −7.10% |
| F | Regularised75-day inverse variance | 46.92% | 2.12 | −7.08% |
| F | Constrained equal-risk allocation | 42.88% | 1.93 | −8.06% |
| L | Original v11 sizing and allocator | **41.20%** | **1.96** | **−6.40%** |
| L | Regularised90-day inverse variance | 33.34% | 1.63 | −6.60% |
| L | Four-component minimum score, T18 | 39.66% | 1.64 | −9.75% |
| L | Regularised90-day variance, kappa 90 | 32.07% | 1.53 | −7.06% |
| L | Constrained equal-risk allocation | 33.88% | 1.60 | −7.50% |

All 30 snapshot policies and all 16 engine runs are shown below. Snapshot means are independent-window returns and must not be compounded into CAGR.

## Robustness of results

Thirteen mathematical fixtures and 13 snapshot checks pass. All ten NB11 controls reproduce their weights and every horizon outcome. Constrained/projected pairs share covariance, support and invested budgets. Engine source controls reproduce the earlier repaired-data results; position PnL reconciles to equity within $1. Saved outputs have no errors or warnings; figures were individually inspected and corrected.

The sparse four-input gain over its regularised benchmark is only **$888**, with pmalt contributing +$1,606, Goon Edging +$968 and  Hyperrr −$1,683. The source strategies themselves have substantial profit concentration: Realist Capital represents about 38%/45% of positive vault PnL for F/L. The largest recorded update is a two-day valuation change, mainly Realist Capital and Goon Edging; actual daily NAV marks exist across the interval. These gains occurred while BTC/ETH fell, so a broad rising market does not explain them; the marks do not establish a data error.

The primary snapshot horizon contains only eight complete blocks; 90-day terminal support leaves one mature basket unresolved. Ranking tiers differ between the stateless snapshot and executable source’s zero-score ties, and the engine adds hysteresis, changing budgets, fees and operational checks. All results are retrospective and repeatedly searched. No production change is warranted by this experiment.

Every figure and table has its own heading and description; the default evaluation interval is 2026.
"""


def build(with_replay=True):
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md(HEADER),
        code("""from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Markdown
ROOT=Path.cwd()
if not (ROOT/'allocation_followup.py').exists():ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from allocation_followup import initialise, fixtures, registry, run_snapshots
from allocation_followup_report import snapshots, replay
from score_matrix_visualisation import compact_output
pd.options.display.max_colwidth=None
"""),
        md("""## Mathematical checks — 2026-01-01 → 2026-10-05

Independent examples check inverse-volatility risk budgets, cap feasibility, stationarity, covariance scaling, the diagonal minimum-variance identity and young/missing-history fallbacks.
"""),
        code("display(fixtures())"),
        md("""## Registered combinations and pinned inputs — 2026-01-01 → 2026-10-05

Twenty new combinations are accompanied by ten NB11 controls. This cell pins archive, source and policy hashes; earlier notebook outputs are preserved.
"""),
        code("""with compact_output('Verify pinned inputs; estimated under one minute'):
    data,policies=initialise()
display(pd.DataFrame(policies)[['arm','label','selector','method','L','kappa','floor']].style.hide(axis='index'))
"""),
        md("""## Full-calendar snapshots — 2026-01-01 → 2026-10-05; 7/30/90-day horizons

Allocate once per policy/origin, then value the three horizons independently. Exact NB11 controls, optimiser checks and shared-budget comparisons must pass before engine replay.
"""),
        code("""with compact_output('30 policies across 70 origins; estimated two–four minutes'):
    result=run_snapshots(data,policies)
snapshot_summary=snapshots(data,result)
"""),
    ]
    if with_replay:
        cells += [
            md("""## Engine shortlist and replay — 2026-01-01 → 2026-10-05

Keep equal and regularised 90-day controls for both selectors; matched sparse controls; T18 and its V180 control; both equal-risk cap methods for both selectors; one sensitivity per selector chosen for its mean 30-day return; and unchanged source v11. The sensitivity choice is exploratory. Freeze these identities before observing engine results.
"""),
            code("""from allocation_followup_engine import run_shortlist
with compact_output('Full engine shortlist; estimated three–eight minutes'):
    engine_summary,runs,robustness=run_shortlist(data,result,policies)
replay(data,engine_summary,runs,robustness)
"""),
            md("""## Findings and robustness — 2026-01-01 → 2026-10-05

Write the verdict after successful snapshot checks, complete engine execution and position-level attribution. Report searched-history limitations and the differences between snapshot and executable allocation mechanics.
"""),
            code("""from allocation_followup_engine import write_findings
findings=write_findings(data,result,engine_summary,runs,robustness)
from allocation_followup_review import render_review
engine_contrasts=render_review(data)
display(Markdown(f'[Detailed findings]({findings.name})'))
"""),
        ]
    if with_replay:
        cells += [
            md("""## Tail attribution and valuation clock — 2026-01-01 → 2026-10-05

Check the largest recorded equity update against actual NAV marks, position cash-flow PnL and BTC/ETH references."""),
            code("from allocation_tail_audit import audit_tail\ntail_audit=audit_tail(data)\n(folder if 'folder' in globals() else data['artifact']).joinpath('figure-manifest.json').write_text(__import__('json').dumps(list(dict.fromkeys(data['figures'])),indent=2));"),
        ]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, ROOT / "12-research-allocation-followup.ipynb")


if __name__ == "__main__":
    build(with_replay="--snapshots-only" not in __import__("sys").argv)
