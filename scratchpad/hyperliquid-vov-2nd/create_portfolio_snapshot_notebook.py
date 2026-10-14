"""Build the separately rendered experiment 10 snapshot study."""

from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent


def build():
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md("""# Experiment 10 — sorting, risk estimation and portfolio allocation snapshots

## Goal and method

Understand whether our frozen scoring methods select profitable vaults, whether risk forecasts anticipate future risk, and whether weighting, breadth and capacity improve construction. This implements [the reviewed plan](10-portfolio-snapshot-plan.md), building on [09](09-research-k-ratio-feature-forecasts.ipynb) and [08](08-research-score-forecast-thresholds.ipynb) inputs. It introduces no new score features or fitted score coefficients.

Every four days we construct an independent basket using completed inputs through T−1, then hold fixed units for 7, 30 or 90 days. There is no inherited strategy state or daily weight rebalancing. IC measures ordering; matched-basket return and variance differences measure allocation effects. These snapshots do not produce executable strategy CAGR or one backtest Sharpe.

Sparse positive NAV is forward-filled causally with actual observation counts and clocks kept separate. Young vaults retain partial risk histories and contemporaneous leave-one-out peer priors; missing scores remain a distinct lowest-ranked tier. Unresolved future outcomes censor the complete selected basket, without replacing vaults or renormalising survivors.

Primary display period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**. Secondary full/pre-2026 history is explicitly labelled. The plan's ten-block reporting gate makes 2026 descriptive. All inspected history is retrospective research, including longer-period exploratory intervals.

## Results

Completed on 10 October 2026 using the unchanged repaired archive. Future-return score IC is modest (about 0.087–0.089), while selected-basket risk IC is stronger (about 0.51–0.55). Uncapped inverse variance lowers risk but loses30-day return versus equal weights. Peer regularisation moderates that loss; concentration/TVL projection materially changes the comparison. Increasing six to ten positions lowers matched returns and risk. These are independent gross-NAV snapshots, not an executable strategy backtest.

2026 results remain descriptive: the ten-complete-calendar-block gate is unmet. Supported longer-history simultaneous bands include zero, and the periods have already been researched. Sparse/missing histories retain separate observed clocks and explicit support. Independent original-archive and adverse-fixture audits pass; 47 figures have been inspected separately. Full [findings](10-portfolio-snapshot-findings.md) and [risk](appendices/10-snapshot-risk-tables.ipynb), [allocation](appendices/10-snapshot-allocation-tables.ipynb) and [statistical](appendices/10-snapshot-statistics-tables.ipynb) appendices explain support and limitations.
"""),
        code("""from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Markdown
ROOT = Path.cwd()
if not (ROOT / 'portfolio_snapshot_data.py').exists():
    ROOT = ROOT / 'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0, str(ROOT))
from portfolio_snapshot_data import load_inputs, CONFIG, ARTIFACT
from portfolio_snapshot_risk import build_risk
from portfolio_snapshot_construction import run_snapshots
from portfolio_snapshot_pipeline import execute_stage
from score_matrix_visualisation import compact_output
"""),
        md("""## Frozen design — 2026-01-01 → 2026-10-05; 7/30/90-day horizons

The controls separate sorting, risk forecasts, unequal weights and breadth. The main comparison uses six positions and a 90-day risk window; these are reference settings, not an established optimum.
"""),
        code("""display(pd.DataFrame([
    ('Scores', 'v11; Blend 46d; four-input focal'),
    ('Risk windows', '30, 60, 90, 180 days; local 75/105-day checks'),
    ('Weight powers', '0 / 0.5 / 1 / 2; p=0 deduplicated equal weights'),
    ('Breadth', '4 / 6 / 8 / 10 requested; retain actual candidate-limited breadth'),
    ('Risk', 'Raw daily variance; support-weight regularisation; source-candle control'),
    ('Sparse history', 'Causal daily carry; no leading backfill; real updates counted separately'),
    ('Capacity', '$150,000; 98% budget; 33% concentration/TVL; unknown-state policies separate'),
    ('Uncertainty', '1,999 calendar-block draws; ten-block gate; fixed 18-contrast family'),
], columns=['Choice', 'Definition']))"""),
        md("""## Pinned population and causal clocks — 2026-01-01 → 2026-10-05; 7/30/90-day horizons

Use the repaired archive already used by experiments 08/09. Original observations supply NAV history; frozen source eligibility and recipes supply selection. Alternate grid phases recompute only those same three recipes, without an engine backtest.
"""),
        code("""with compact_output('Pinned data and four origin phases'):
    data = load_inputs(include_phases=True)
"""),
        md("""## Risk inputs — 2026-01-01 → 2026-10-05; 7/30/90-day horizons

Estimate calendar-return variance using available elapsed history. Shrink towards a positive leave-one-out eligible-peer median with confidence m/(m+L/3), where m counts actual daily updates. A one-mark flat carry is unknown risk, not measured zero variance.
"""),
        code("""with compact_output('Shared causal risk tensors'):
    risk = execute_stage('risk', data)
"""),
        md("""## Independent fixed-unit portfolios — 2026-01-01 → 2026-10-05; 7/30/90-day horizons

Each arm uses a basket selected before future labels are joined. Whole-basket equal fallback and candidate-limited dates remain in policy comparisons. Entry caps affect initial deployment; the portfolio then drifts without rebalancing.
"""),
        code("""with compact_output('Stages R/W/N/C and bounded companions'):
    result = execute_stage('snapshots', data, risk)
"""),
        md("""## Paired analysis — 2026-01-01 → 2026-10-05; 30-day primary horizon

Preserve the calendar when resampling paired effects. Assignment placebos retain the exact weight multiset; pooled nulls keep seeded identity priorities across dates. Exact breadth and first-update decompositions identify where apparent improvements come from.
"""),
        code("""with compact_output('Paired inference and mechanism diagnostics'):
    result = execute_stage('statistics', data, risk, result)
"""),
        md("""## Independent calculation audit — 2026-01-01 → 2026-10-05; 7/30/90-day horizons

Adverse fixtures and direct original-archive reconstructions check filling, timestamps, source weights, held units, missing targets and exact attribution. Expected values are computed independently of the implementation being checked.
"""),
        code("""from portfolio_snapshot_audit import run_audit
with compact_output('Independent sparse, timing and portfolio audit'):
    audit = run_audit(data, risk, result, ARTIFACT)
display(audit)
"""),
        code("""from portfolio_snapshot_report import render_report
render_report(data, risk, result, audit)
"""),
    ]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, ROOT / "10-research-portfolio-snapshots.ipynb")


if __name__ == "__main__":
    build()
