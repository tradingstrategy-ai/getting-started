"""Create the observable, complete forecast research notebook."""

from pathlib import Path
import nbformat

RESEARCH_DIR = Path(__file__).resolve().parent
NOTEBOOK = RESEARCH_DIR / "08-research-score-forecast-thresholds.ipynb"


def main():
    """Create fresh cells without inheriting parent research conclusions."""
    cells = []

    def md(source):
        cells.append(nbformat.v4.new_markdown_cell(source))

    def code(source):
        cells.append(nbformat.v4.new_code_cell(source))

    md("""# Experiment 08 — score forecasts and vault admission thresholds

Based on [07-opt-score-position-count.ipynb](07-opt-score-position-count.ipynb), with frozen scoring methods from experiments 04–07. Implementation follows [the reviewed plan](08-forecast-score-threshold-plan.md), reviewed with Claude Opus 5.5.

## User goal

Understand how the different scoring methods relate to future vault profitability and whether there is a score threshold below which vaults should no longer be admitted. Forecast **every four calendar days**. For **every scoring method × 7/30/90-day lookahead**, show score on X and realised **CAGR and Sharpe** on Y, trend lines and points coloured by forecast-origin quarter. Analyse the strength and stability of the relationships and test additional ways to understand the data.

## Method

Inventory every distinct implemented composite recipe, including the 74 frozen two-/three-/four-input supports and older clipping/missingness alternatives. Compute scores from completed T−1 features and use calendar-aligned future per-share NAV endpoints. All metrics use the latest observed positive NAV carried across missing calendar days. Never backfill before first observation or create labels after last observation/archive end. Do not replace unknown scores with zero or treat filled historical marks as actual observations. Analyse same-date rank IC, uncertainty, calibration, clipping, missingness, tails, quarters, delayed anchors, lagged-score placebos and incremental inputs.

Freeze the monthly threshold rule before seeing outcomes. Compare source v11, two-input Blend 46d and the focal four-input method at 6/7 positions, with separate slot-to-cash and source capped-renormalisation treatments. Keep the original two-day trading cadence, inverse variance, selection hysteresis, guards and source-modelled costs. Short-period **2026-01-01 → 2026-10-05 (end exclusive, UTC)** is the default throughout; full history is secondary and overlaps previously researched dates.

## Key new insights

Results are recorded after the complete execution and chart review.

## Summary of results

The tables below distinguish forecast ranking, calibration and actual executable portfolio performance. The three focal methods have separate scatter views after the input checks. The complete catalogue contains every method/lookahead combination in small, separately linked notebooks.

## Robustness of results

Checks include independent raw-label recomputation, original source-score equality, full equity/trade baseline matching, actual versus carried NAVs, serial dependence, sparse support, extreme annualisation, per-vault/quarter omissions and PnL concentration. Short-period 90-day estimates are descriptive: confidence intervals and p-values are deliberately absent. Existing methods were selected on already inspected history; this is conditional chronological validation, not an untouched holdout.
""")
    md("""## Inputs, observed targets and frozen design

Load the pinned repaired generation, freeze the analysis rules and independently audit raw observations before viewing relationships.""")
    code("""from pathlib import Path
import sys
RESEARCH_DIR = Path.cwd()
if not (RESEARCH_DIR / 'score_forecast_data.py').exists():
    RESEARCH_DIR = RESEARCH_DIR / 'scratchpad' / 'hyperliquid-vov-2nd'
sys.path.insert(0, str(RESEARCH_DIR))
import json
import numpy as np
import pandas as pd
from IPython.display import display, HTML, Markdown
from score_matrix_visualisation import compact_output
from score_forecast_data import prepare_data, ARTIFACT_DIR
from score_forecast_statistics import analyse_data, join_method, freeze_threshold_rule
from score_forecast_execution import freeze_execution_design, run_threshold_experiments
from score_forecast_audit import independent_label_audit
from score_forecast_visualisation import *
from score_forecast_report import *

class Parameters:
    forecast_days = 4
    lookaheads = (7, 30, 90)
    positions = (6, 7)
    threshold_horizon = 30
    random_seeds = (8081, 8082, 8083)
    short_start = pd.Timestamp('2026-01-01')
    long_start = pd.Timestamp('2023-03-01')
    end_exclusive = pd.Timestamp('2026-10-05')

with compact_output('Pinned score/label generation and predeclared policy rules'):
    data = prepare_data()
    threshold_rule = freeze_threshold_rule(data)
    execution_design = freeze_execution_design()
    raw_audit, audit_report = independent_label_audit(data, ARTIFACT_DIR)
FIGURE_DIR = ARTIFACT_DIR / 'figures'
FIGURE_DIR.mkdir(exist_ok=True)
figure_paths = []
registry_ids = [r['method_id'] for r in data['registry']]
styled_table(pd.DataFrame([{'Methods': len(registry_ids), 'Required method/lookahead combinations': 3 * len(registry_ids),
                           'Forecast cadence (days)': Parameters.forecast_days, 'Lookahead (days)': '7 / 30 / 90',
                           'Source-score checks': data['provenance'].get('source_score_audit', {}).get('observations', 546),
                           'Independent raw-label checks': audit_report['samples'], 'Raw targets match': audit_report['all_targets_match']}]),
             'Frozen experiment design and replication', 'Scoring recipes are deduplicated by complete transforms and missingness policy. '
             'Position sizing and position-count aliases do not multiply the forecast chart grid.')
styled_table(data['coverage'].query("period == '2026'"), 'Daily NAV target coverage',
             'The denominator includes all archived vaults and forecast dates, not only eligible or old vaults. '
             'CAGR/return and Sharpe use causally forward-filled daily NAV, retaining actual observation counts and carried-day counts. Administrative censoring means the lookahead has not finished.')
styled_table(raw_audit, 'Independent raw NAV label audit', 'A separate implementation recomputes endpoint return, log return, CAGR and Sharpe from raw share-price rows. '
             'Samples include flat, missing, delayed and price-guard divergence cases.', collapsed=True)
method_inventory = pd.DataFrame([{'ID': r['method_id'], 'Method': method_name(data, r['method_id']), 'Inputs': r['inputs'], 'Missing policy': r['missing_policy'],
                                 'Recipe': json.dumps(r['recipe'], sort_keys=True), 'Source': ', '.join(r['sources']), 'Aliases': '; '.join(r['aliases'])} for r in data['registry']])
styled_table(method_inventory, 'Complete scoring-method inventory', 'All implemented composite recipes from 04–07 are retained, including poor performers. '
             'Full recipes and coefficients are stored with the registry; identical aliases share one chart set.', collapsed=True)
mapping = data['provenance'].get('raw_mapping_audit', data['provenance'].get('mapping_audit', {}))
if mapping:
    styled_table(pd.DataFrame([mapping]), 'Price observation and candle mapping',
                 'Daily candles close on the last raw share-price observation inside the labelled day. Archive written_at is not a historical publication receipt. '
                 'Framework carried-price divergences remain visible and true tiny NAV losses are retained in forward targets.', collapsed=True)
universe_audit_path = ARTIFACT_DIR / 'universe-history-audit.csv'
if universe_audit_path.exists():
    styled_table(pd.read_csv(universe_audit_path), 'Frozen universe and historical coverage',
                 'The 514-vault parent population is kept for comparable experiments. It is a cached policy snapshot, not a historically complete vault population. '
                 'Older selected lists and the latest metadata show policy exclusions and newer candidates that the parent snapshot cannot cover.', collapsed=True)
""")
    md("""## Score versus future profitability: main scatter plots

For **v11, Blend 46d and the four-input candidate**, each **7-, 30- and 90-day lookahead** has three separate images, each with its own heading and description: **CAGR in the shared −100% to +300% linear range**, **CAGR over its full range**, and **Sharpe over its full range**. The zoomed view exposes ordinary outcomes; its overflow count refers to the separate tail audit. Scores and trends use all finite pairs. All charts use **2026-01-01 → 2026-10-05 (end exclusive, UTC)**; the complete appendix shows all remaining scoring methods.""")
    code("""chunk = render_method_appendix(data, FOCAL_METHODS, FIGURE_DIR)
scatter_manifest = chunk
figure_paths.extend(row['path'] for row in chunk)
""")
    md("""## Predictive relationships and calibration

Scores are rankings, not return-unit forecasts. Compare within-date relationships first, then chronological calibration and economic admission rules.""")
    code("""with compact_output('Shared forecast statistics — estimated 4–10 minutes'):
    statistics = analyse_data(data)
styled_table(focal_ic_table(data, statistics), 'Frozen controls: predictive rank relationships',
             'Mean IC weights forecast dates equally and ranks vaults available on that date. Positive means higher scores identify better future outcomes. '
             'Uncertainty uses whole date baskets; dashes indicate unsupported inference. Short-period 90-day confidence intervals are omitted.')
figure_paths.extend(overview_figures(data, statistics, FIGURE_DIR))
""")
    code("""figure_paths.extend(display_calibration(data, statistics, FIGURE_DIR))
for frame_name, title, description in [
    ('coverage', 'Eligible score coverage and missing cohorts', 'Separate missing scores, valid zeros, unsupported future prices and undefined ratios; coverage differences are not forecasting skill.'),
    ('clipping', 'Score plateaus and ties', 'Hard clips can turn materially different vaults into equal scores. This audit counts zero/one scores and within-date ties.'),
    ('robustness', 'Vault, quarter, variance and attrition sensitivities', 'Compare omissions and target-quality sensitivities with the same frozen method; no worst observation is deleted from the primary estimate.'),
    ('lagged_score', 'Freshness placebo', 'A stale score predicts the same future outcome. Requested lag 30 days maps to the last available four-day score, while 60 days is exact.'),
    ('incremental_information', 'Incremental information from the extra inputs', 'Residualise the focal four-input score against its two-input core within each date; this tests information beyond the shared core, not a new optimised score.')]:
    frame = statistics.get(frame_name, pd.DataFrame())
    if not frame.empty:
        if 'period' in frame:
            frame = frame[frame.period.eq('2026')]
        styled_table(frame, title, description, collapsed=True)
""")
    md("""## Interactive focal views

These zoomable 30-day views supplement the complete static appendix. Raw CAGR units can be dominated by extreme annualisation; the appendix uses signed-log axes without dropping points.""")
    code("""for method_id in FOCAL_METHODS:
    frame = join_method(data, method_id, 30)
    for target in ('future_cagr', 'future_sharpe'):
        label = 'CAGR' if target == 'future_cagr' else 'Sharpe'
        intro(method_name(data, method_id) + ' · interactive 30-day ' + label,
              'Each point is one vault/forecast date, coloured by quarter. The robust line is descriptive. '
              'CAGR starts in a zoomed range; double-click or zoom out for all extremes. No target values are clipped.')
        fig = interactive_scatter(data, method_id, 30, frame, target=target)
        display(HTML(fig.to_html(full_html=False, include_plotlyjs='cdn')))
""")
    md("""## Executable entry-floor experiments

The forecast cadence remains four days; these policies trade on the original two-day schedule. No scoring coefficients or selector ranks are retuned. Admission floors veto selected new entrants, so the source may still exit a displaced incumbent; no hidden replacement entrant is added.""")
    code("""from tqdm_loggable.auto import tqdm
with compact_output('Source-controlled threshold replays — estimated 10–20 minutes'):
    progress_bar = tqdm(total=132, desc='Entry floors and matched controls')
    def execution_progress(done, total, row):
        progress_bar.total = total
        progress_bar.set_postfix(period=row['Period'], method=row['Method'], n=row['Positions'], policy=row['Threshold policy'], refresh=False)
        progress_bar.update(done - progress_bar.n)
    try:
        execution = run_threshold_experiments(data, statistics, include_random=True, progress=execution_progress)
    finally:
        progress_bar.close()
from audit_sparse_metrics import refresh_foregone_targets
execution = refresh_foregone_targets(data, execution)
figure_paths.extend(display_execution(data, execution, FIGURE_DIR))
""")
    code("""for frame_name, title, description in [
    ('jumps', 'Strongest booked portfolio moves', 'Inspect the leading position behind large positive and negative equity changes; concentrated vault events can dominate performance.'),
    ('positions', 'Individual positions and curator flags', 'Realised position profits and losses retain curator exclusion/quarantine flags. The flags are a diagnostic, not a hindsight removal.'),
    ('rejected_outcomes', 'What rejected entries subsequently earned', 'These are static gross 30-day outcomes from proposed entries using causal daily NAV carry, not counterfactual strategy PnL. Actual endpoint counts remain separate; prelaunch and terminally censored futures stay missing.')]:
    frame = execution.get(frame_name, pd.DataFrame())
    if not frame.empty:
        frame = frame[frame.Period.eq('2026') & frame.Seed.isna()]
        if frame_name == 'positions':
            frame = pd.concat([frame.nlargest(12, 'Final profit (USD)'), frame.nsmallest(12, 'Final profit (USD)')]).drop_duplicates()
        styled_table(frame, title, description, collapsed=True)
""")
    md("""## Missing-score entry sensitivity

An unscored vault is distinct from a valid zero score. This diagnostic keeps the source selector and incumbent rules, vetoes only new unscored entries, and leaves their proposed dollars as cash.""")
    code("""from score_forecast_missing import run_missing_sensitivity
with compact_output('Missing-score entry sensitivity — six historical replays'):
    missing_bundle = run_missing_sensitivity(data, execution)
missing_sensitivity = missing_bundle['summary']
missing_columns = ['Method', 'Positions', 'CAGR', 'Sharpe', 'Maximum drawdown', 'Mean cash weight', 'Rejected entry proposals', 'CAGR delta vs no-floor', 'Sharpe delta vs no-floor', 'Derived identical']
styled_table(missing_sensitivity[missing_sensitivity.Period.eq('2026')][missing_columns], 'Unscored admission in the short period',
             'The six baseline ledgers contain no funded unscored new entries, so the identical entry-veto paths are reused after explicit checks. These are equivalent policies, not additional independent successes.')
styled_table(missing_sensitivity[missing_sensitivity.Period.eq('Long')][missing_columns], 'Unscored admission in earlier history',
             'Six fresh full-history engine replays veto only nonfinite-score new entries. Finite zero scores, existing holdings, sizing, guards, fees and selection machinery retain the source rules.', period=LONG_PERIOD, collapsed=True)
""")
    md("""## Population, price-path and market-exposure checks

These supplementary analyses test whether apparent predictability depends on the eligible population, carried price marks or broad market exposure. They do not change the frozen scoring rules.""")
    code("""from score_forecast_extensions import run_extensions
with compact_output('Population and market-exposure sensitivities — estimated 2–5 minutes'):
    extensions = run_extensions(data, statistics)
for name, frame in extensions.items():
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        shown = frame[frame.period.eq('2026')] if 'period' in frame else frame
        if shown.empty:
            continue
        descriptions = extensions.get('descriptions', {})
        styled_table(shown, name.replace('_', ' ').capitalize(), descriptions.get(name,
                     'Supporting diagnostics use frozen methods and causal input cutoffs; unsupported estimates remain missing.'), collapsed=True)
""")
    md("""## Complete scatter catalogue

The complete **139-method × 7/30/90-day** catalogue is in [small linked notebooks](08-scatter-catalogue/index.ipynb). Every metric/view has a **separate image, heading and description**. There are no merged images or collations. Splitting the catalogue keeps notebook 08 usable in VS Code; its 27 main-method images remain visible above.

Each method/lookahead has a zoomed CAGR image, a full-range CAGR audit and a full-range Sharpe image. All charts use **2026-01-01 → 2026-10-05 (end exclusive, UTC)**. The table below lists every catalogue page and the methods it covers.""")
    code("""from score_forecast_catalogue import write_scatter_catalogue
with compact_output('Complete separate scatter catalogue — estimated 5–8 minutes'):
    scatter_manifest, catalogue_index = write_scatter_catalogue(data, registry_ids, FIGURE_DIR,
                                                              RESEARCH_DIR / '08-scatter-catalogue')
styled_table(catalogue_index, 'Complete scatter catalogue pages',
             'Open a linked page in 08-scatter-catalogue/index.ipynb to view the listed scoring recipes. '
             'Each small notebook embeds its own images and has executable cells to regenerate them.')
""")
    md("""## Secondary history and completion record

Longer history is secondary. Its raw observations are sparse; primary metrics carry the latest known NAV and preserve actual observation counts separately.""")
    code("""styled_table(data['coverage'].query("period == 'Long'"), 'Full-history target availability',
             'All primary metrics use causally carried positive raw NAV. Actual observations remain identifiable; filled daily volatility uses a held-NAV assumption. '
             'Training uses only matured labels, with no leading backfill or target beyond each vault’s last actual observation.', period=LONG_PERIOD, collapsed=True)
styled_table(focal_ic_table(data, statistics, period='Long'), 'Secondary full-history predictive relationships',
             'The same recipes and origin grid extend backwards. More calendar history does not create more supported realised targets.', period=LONG_PERIOD, collapsed=True)
manifest = pd.DataFrame(scatter_manifest)
assert len(manifest) == 9 * len(registry_ids)
assert not manifest.duplicated(['method_id', 'lookahead_days', 'outcome', 'view']).any()
assert set(manifest.lookahead_days) == {7, 30, 90}
manifest.to_csv(ARTIFACT_DIR / 'scatter-figure-manifest.csv', index=False)
source_hashes = {p.name: __import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in RESEARCH_DIR.glob('score_forecast_*.py')}
from score_forecast_catalogue import visual_review_status
review = visual_review_status(ARTIFACT_DIR)
completion = {'methods': len(registry_ids), 'scatter_figures': len(manifest), 'portfolio_arms': len(execution['results']), 'missing_score_cases': len(missing_sensitivity), 'additional_missing_score_replays': 6,
              'raw_label_audit': audit_report, 'source_hashes': source_hashes, 'data_fingerprint': data['provenance']['fingerprint'],
              'visual_review_complete': review['complete'], 'visual_review': review}
(ARTIFACT_DIR / 'completed.json').write_text(json.dumps(completion, indent=2))
findings = write_findings(data, statistics, execution, RESEARCH_DIR / '08-research-score-forecast-thresholds.ipynb')
styled_table(pd.DataFrame([{'Methods': len(registry_ids), 'Scatter figures': len(manifest),
                           'Portfolio arms': len(execution['results']), 'Raw label audit': audit_report['all_targets_match'],
                           'Visual inspection': 'Complete individual chart review' if review['complete'] else 'Pending complete chart review'}]),
             'Execution and evidence record', 'All figures and replay arms have saved manifests. The coordinator checks the complete rendered notebook '
             'and updates the heading with conclusions after execution; generated external artefacts remain ignored.')
""")
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata.language_info = {"name": "python"}
    nbformat.write(notebook, NOTEBOOK)
    print(f"Created {NOTEBOOK.name}: {len(cells)} cells; 139 methods, 417 required figures.")


if __name__ == "__main__":
    main()
