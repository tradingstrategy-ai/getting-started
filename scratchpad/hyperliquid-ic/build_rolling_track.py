"""Build the first rolling profit/risk track notebooks from the corrected NB24 harness."""

from pathlib import Path
import copy

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
PARENT = nbf.read(ROOT / "24-research-monthly-calibration.ipynb", as_version=4)


def patch_engine_cell(source: str) -> str:
    """Replace NB24's monthly score lookup with rolling arm lookups."""
    score_start = source.find("            record=CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),int(CAL_CONFIG['lookback'])))")
    score_end = source.find("\n        scored =", score_start)
    if score_start < 0 or score_end < 0:
        raise ValueError("NB24 score lookup was not found; refuse to build an unpatched rolling notebook")
    source = source[:score_start] + """            record=CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),30))
            if CAL_RULE in ('B10', 'B11'):
                composite_signal=record['growth_annualised'] if record is not None else float('nan')
            else:
                composite_signal=indicators.get_indicator_value(selection_score_indicator, pair=pair)""" + source[score_end:]
    source = source.replace(
        "        scored = composite_signal is not None and composite_signal == composite_signal\n",
        "        scored = composite_signal is not None and composite_signal == composite_signal\n" "        # Growth arms rank only mathematically available features.  Keep the\n" "        # incumbent's missing-composite behaviour in B00/B01, but do not turn\n" "        # missing rolling growth into a zero score that can win a degenerate\n" "        # basket when every finite score is negative.\n" "        if CAL_RULE in ('B10', 'B11') and not scored:\n" "            continue\n",
    )
    source = source.replace(
        "common=CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),3))\n            if common is None or common['gate'] <= 0:",
        "common=CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),30))\n            if common is None or common['gate'] <= gate_threshold:",
    )
    source = source.replace(
        "inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)\n        inv_vol_by_id[pair_id] = float(inv_vol) if inv_vol is not None and inv_vol == inv_vol else 0.0",
        "inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)\n        if CAL_RULE in ('B01', 'B11'):\n            risk_record = CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),30))\n            risk_value = risk_record.get('volatility', float('nan')) if risk_record else float('nan')\n            inv_vol = 1.0 / max(float(risk_value), 0.05) if risk_value == risk_value else float('nan')\n        inv_vol_by_id[pair_id] = float(inv_vol) if inv_vol is not None and inv_vol == inv_vol else 0.0",
    )
    source = source.replace(
        "if CAL_RULE in ('B01', 'B11'):",
        "if CAL_RULE in ('B01', 'B11', 'S_INV_VOL', 'S_INV_VAR'):",
    )
    source = source.replace(
        "if CAL_RULE not in ('anchor','matched_original'):",
        "if CAL_RULE not in ('anchor','matched_original','B00','B01','S_EQUAL','S_INV_VOL','S_INV_VAR'):",
    )
    source = source.replace(
        "assert abs(quantity - float(position.get_quantity())) < 1e-8, (",
        "held = float(position.get_quantity())\n    assert abs(quantity - held) <= 1e-8 * max(1.0, abs(held)), (",
    )
    marker = "    # Sizing. Selection above ranked on the composite score;"
    fallback = """    if CAL_RULE in ('B01', 'B11', 'S_INV_VOL', 'S_INV_VAR') and selected:
        # Missing interval risk receives the median finite raw inverse-risk weight
        # within this selected set. If none is finite, use equal raw weights.
        selected_ids = [pair_id for pair_id, _pair, _signal in selected]
        finite_inverse_risk = [inv_vol_by_id[pid] for pid in selected_ids if inv_vol_by_id.get(pid, 0.0) > 0]
        fallback_inverse_risk = float(np.median(finite_inverse_risk)) if finite_inverse_risk else 1.0
        for selected_id in selected_ids:
            if inv_vol_by_id.get(selected_id, 0.0) <= 0:
                inv_vol_by_id[selected_id] = fallback_inverse_risk

"""
    schedule_filter = """    if CAL_RULE.startswith('S_'):
        # Restrict the candidate set to the causal B11 requested membership for this decision.
        # Gate, deposit-window and minimum-hold checks remain active and are measured as replay drift.
        requested_addresses = set(TARGET_SCHEDULE.get(pd.Timestamp(timestamp).normalize(), set()))
        candidates = [
            item for item in candidates
            if str(item[1].pool_address).lower() in requested_addresses
        ]

"""
    source = source.replace("    # Rank by composite (selection), but SIZE by inverse volatility (linear weighting).", schedule_filter + "    # Rank by composite (selection), but SIZE by inverse volatility (linear weighting).")
    source = source.replace(marker, fallback + marker)
    return source


def patch_exposure_engine_cell(source: str) -> str:
    """Add causal cash-preserving exposure interventions for NB28 only."""
    source = patch_engine_cell(source)
    marker = "    alpha_model.update_old_weights(state.portfolio, ignore_credit=False)"
    intervention = """    if CAL_RULE in ('E1', 'E1_SCALE', 'E2', 'E2_SCALE') and alpha_model.signals:
        # Keep the parent allocator's selected names and capacity checks.  This block only changes
        # the requested dollar targets after the parent path has produced them.
        _base_targets = {
            s.pair.internal_id: float(s.position_target or 0.0)
            for s in alpha_model.signals.values()
        }
        _base_total = sum(_base_targets.values())
        _target_map = dict(_base_targets)
        _released_reason = 'none'
        _haircut_sum = 0.0
        if CAL_RULE in ('E1', 'E1_SCALE'):
            # Re-run each selected name against its original normalised share of the budget.  The
            # accepted amounts are kept as cash instead of being redistributed to later names.
            _raw_total = sum(max(float(s.raw_weight), 0.0) for s in alpha_model.signals.values())
            _no_refill = {}
            for _signal in alpha_model.signals.values():
                _raw_share = max(float(_signal.raw_weight), 0.0) / _raw_total if _raw_total else 0.0
                _asked = min(_raw_share, float(parameters.max_concentration_pct)) * float(portfolio_target_value)
                _risk = size_risk_model.get_acceptable_size_for_position(timestamp, _signal.pair, _asked)
                _signal.position_size_risk = _risk
                _no_refill[_signal.pair.internal_id] = float(_risk.accepted_size)
            _treatment_total = sum(_no_refill.values())
            if CAL_RULE == 'E1_SCALE' and _base_total > 0:
                _scale = _treatment_total / _base_total
                _target_map = {pid: value * _scale for pid, value in _base_targets.items()}
                _released_reason = 'uniform_scale_control'
            else:
                _target_map = _no_refill
                _released_reason = 'no_refill'
        else:
            _haircuts = {}
            for _signal in alpha_model.signals.values():
                _record = CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(), str(_signal.pair.pool_address).lower(), 30))
                _drawdown = float(_record.get('max_drawdown', 0.0)) if _record else 0.0
                _factor = math.exp(-max(_drawdown, 0.0) / 0.10)
                _haircuts[_signal.pair.internal_id] = _factor
            _haircut_sum = sum(_base_targets[pid] * _haircuts.get(pid, 1.0) for pid in _base_targets)
            if CAL_RULE == 'E2_SCALE' and _base_total > 0:
                _scale = _haircut_sum / _base_total
                _target_map = {pid: value * _scale for pid, value in _base_targets.items()}
                _released_reason = 'uniform_scale_control'
            else:
                _target_map = {pid: _base_targets[pid] * _haircuts.get(pid, 1.0) for pid in _base_targets}
                _released_reason = 'drawdown_haircut'
        _treatment_total = sum(_target_map.values())
        for _signal in alpha_model.signals.values():
            _target = _target_map.get(_signal.pair.internal_id, 0.0)
            _signal.position_target = _target
            _signal.normalised_weight = _target / float(portfolio_target_value) if portfolio_target_value else 0.0
        alpha_model.accepted_investable_equity = _treatment_total
        alpha_model.size_risk_discarded_value = max(float(portfolio_target_value) - _treatment_total, 0.0)
        EXPOSURE_LOG.append({
            'date': timestamp,
            'arm': CAL_RULE,
            'base_target': _base_total,
            'treatment_target': _treatment_total,
            'released_cash': max(_base_total - _treatment_total, 0.0),
            'released_reason': _released_reason,
            'haircut_target': _haircut_sum,
        })

"""
    if marker not in source:
        raise ValueError("NB24 update_old_weights marker was not found for exposure patch")
    return source.replace(marker, intervention + marker)


def base_notebook(number: int, title: str, slug: str, patcher=patch_engine_cell):
    cells = []
    heading = f"""# {title}

Parent: [24-research-monthly-calibration.ipynb](24-research-monthly-calibration.ipynb), using its corrected single-redemption-fee execution harness.

This is a separate rolling-price experiment. It uses observed share-price marks strictly before each decision, supports sparse/weekly histories, and does not require completed months or a long history. Blacklists are off in the primary universe. Results are filled in after execution.

## Experiment contract

The first wave measures direct rolling growth, volatility, downside deviation and drawdown over 14, 30 and 60 calendar days. Volatility uses actual elapsed intervals and is missing when only one interval is available. Valuation still forward-fills through the engine; feature risk does not. Young vaults remain eligible when the feature is mathematically available.

This notebook is a corrected reproduction where it reuses NB24 controls. It does not repeat the monthly score grid, the lower-volatility calmness ranker or long-history gates. StratWise and Systematic L/S grid are explanatory references only.

## Key new insights

Pending execution.

## Summary of results

Pending execution.

## Robustness analysis

Pending execution.
"""
    cells.append(nbf.v4.new_markdown_cell(heading))
    for i in range(1, 11):
        c = copy.deepcopy(PARENT.cells[i])
        c.outputs = []
        c.execution_count = None
        c.source = c.source.replace(
            "OUT = PROJECT / '_artifacts-monthly-calibration'",
            f"OUT = PROJECT / '_artifacts-rolling-profit-risk/nb{number}'",
        )
        if i == 8:
            c.source = patcher(c.source)
        cells.append(c)
    return cells


def append_common_cells(cells, *, nb25: bool):
    init = """
from nb23_profitable_months import set_single_redemption_fee
from rolling_track_features import build_rolling_panel, validate_rolling_features
from rolling_track_simulation import WINDOWS, gate_coverage_audit, run_engine_jobs, ranking_summary, write_manifest

validate_rolling_features()
ROLLING_ARM = 'anchor'
CAL_RULE = 'anchor'
CAL_CONFIG = None
CAL_LOOKUP = {}
ROLLING_LOOKUP = {}
CAL_LOG = []
MONTH_LOG = CAL_LOG
SCREEN_LOOKUP = {}
SCREEN_LOG = []
ACTIVE_SCREEN = 'none'
BLACKLIST_MODE = 'off'
strategy_universe = UNIVERSES['off']
CYCLE_LOG = []

old_decide = decide_trades
def decide_trades(input):
    portfolio = input.state.portfolio
    equity = portfolio.get_total_equity()
    values = [float(p.get_value()) for p in portfolio.get_open_positions()]
    CYCLE_LOG.append({'date': input.timestamp, 'invested': sum(values) / equity if equity else 0., 'positions': len(values), 'max_weight': max(values + [0.]) / equity if equity else 0.})
    return old_decide(input)

ROLLING_PANEL = build_rolling_panel(globals(), lookbacks=(14, 30, 60), include_outcomes=True)
CAL_LOOKUP = {(pd.Timestamp(r.date), r.address, int(r.lookback)): r._asdict() for r in ROLLING_PANEL.itertuples(index=False)}
ROLLING_LOOKUP = CAL_LOOKUP
GATE_COVERAGE = gate_coverage_audit(ROLLING_PANEL, lookback=30)
GATE_COVERAGE.to_csv(OUT / 'gate-coverage-audit.csv', index=False)
display(GATE_COVERAGE.describe(include='all'))
display(ROLLING_PANEL.groupby('lookback').agg(rows=('address', 'size'), vaults=('address', 'nunique'), sparse_share=('sparse', 'mean')))
"""
    cells.append(nbf.v4.new_code_cell(init))
    if nb25:
        eval_source = """
ROLLING_SUMMARY = ranking_summary(ROLLING_PANEL)
ROLLING_SUMMARY.to_csv(OUT / 'rolling-ranking-summary.csv', index=False)
display(ROLLING_SUMMARY.groupby(['ranking', 'lookback', 'horizon']).agg(dates=('date', 'size'), top_return=('top_return', 'mean'), rest_return=('rest_return', 'mean'), top_drawdown=('top_drawdown', 'mean'), rest_drawdown=('rest_drawdown', 'mean'), labelled=('labelled', 'sum')).reset_index())
"""
        cells.append(nbf.v4.new_code_cell(eval_source))
        run_source = """
        arms = [
            {'period': period, 'arm': f'LEGACY_{period}', 'overrides': {}}
            for period in WINDOWS
        ] + [
            {'period': period, 'arm': 'B00', 'overrides': {} }
            for period in WINDOWS
        ]
write_manifest(OUT, notebook='25-research-rolling-metrics-controls.ipynb', parent='24-research-monthly-calibration.ipynb', mechanism_delta='Direct rolling observed-price features plus legacy/common control audit.', arms=arms)
portfolio_metrics = run_engine_jobs(globals(), arms, OUT)
display(portfolio_metrics)
"""
        cells.append(nbf.v4.new_code_cell(run_source))
    else:
        eval_source = """
ROLLING_SUMMARY = ranking_summary(ROLLING_PANEL, lookbacks=(30,))
ROLLING_SUMMARY.to_csv(OUT / 'rolling-ranking-summary.csv', index=False)
display(ROLLING_SUMMARY.groupby(['ranking', 'lookback', 'horizon']).agg(dates=('date', 'size'), top_return=('top_return', 'mean'), rest_return=('rest_return', 'mean'), top_drawdown=('top_drawdown', 'mean'), rest_drawdown=('rest_drawdown', 'mean'), labelled=('labelled', 'sum')).reset_index())
"""
        cells.append(nbf.v4.new_code_cell(eval_source))
        run_source = """
arms = []
for period in WINDOWS:
    arms.extend([
        {'period': period, 'arm': 'B00', 'overrides': {}},
        {'period': period, 'arm': 'B10', 'overrides': {}},
        {'period': period, 'arm': 'B01', 'overrides': {'weighting_method': 'inverse_variance', 'inverse_vol_window': 30}},
        {'period': period, 'arm': 'B11', 'overrides': {'weighting_method': 'inverse_variance', 'inverse_vol_window': 30}},
    ])
write_manifest(OUT, notebook='26-research-rolling-ranking-access.ipynb', parent='25-research-rolling-metrics-controls.ipynb', mechanism_delta='Four-arm ranking/access factorial: original composite versus available-history growth and original versus 30-day interval inverse-variance sizing.', arms=arms)
portfolio_metrics = run_engine_jobs(globals(), arms, OUT)
display(portfolio_metrics)
"""
        cells.append(nbf.v4.new_code_cell(run_source))
    return cells


def build(nb25: bool):
    number = 25 if nb25 else 26
    slug = "rolling-metrics-controls" if nb25 else "rolling-ranking-access"
    title = "Rolling metrics and controls" if nb25 else "Rolling ranking and young-vault access"
    cells = base_notebook(number, title, slug)
    cells = append_common_cells(cells, nb25=nb25)
    nb = nbf.v4.new_notebook(cells=cells, metadata=copy.deepcopy(PARENT.metadata))
    nbf.write(nb, ROOT / f"{number}-research-{slug}.ipynb")


def build_nb27_real() -> None:
    """Build the fixed-membership sizing experiment from the shared harness."""
    cells = base_notebook(27, "Rolling sizing diagnostics", "rolling-sizing")
    cells[0].source = """# Rolling sizing diagnostics

Parent: [26-research-rolling-ranking-access.ipynb](26-research-rolling-ranking-access.ipynb)

This experiment replays the causal B11 requested membership schedule saved by NB26 over the same three native windows. It compares equal raw weights, 30-day interval inverse-volatility weights and inverse-variance weights. The requested membership is frozen before sizing; gate, deposit-window and minimum-hold checks remain active and replay divergence is recorded. No new gate, ranking or optimiser is introduced.

Blacklists are off, the common gate remains the inherited -16% threshold, and the corrected NB23 single-redemption fee is retained.

## Results

Filled after execution.
"""
    init = """
from nb23_profitable_months import set_single_redemption_fee
from rolling_track_features import validate_rolling_features
from rolling_track_simulation import WINDOWS, run_engine_jobs, write_manifest

validate_rolling_features()
ROLLING_ARM = 'S_EQUAL'
CAL_RULE = 'S_EQUAL'
CAL_CONFIG = None
CAL_LOOKUP = {}
ROLLING_LOOKUP = {}
CAL_LOG = []
MONTH_LOG = CAL_LOG
SCREEN_LOOKUP = {}
SCREEN_LOG = []
ACTIVE_SCREEN = 'none'
BLACKLIST_MODE = 'off'
strategy_universe = UNIVERSES['off']
CYCLE_LOG = []
REPLAY_LOG = []
TARGET_SCHEDULE = {}

panel_path = PROJECT / '_artifacts-rolling-profit-risk' / 'nb26' / 'rolling-panel.parquet'
ROLLING_PANEL = pd.read_parquet(panel_path)
CAL_LOOKUP = {(pd.Timestamp(r.date), r.address, int(r.lookback)): r._asdict() for r in ROLLING_PANEL.itertuples(index=False)}
ROLLING_LOOKUP = CAL_LOOKUP

schedule_source = pd.read_csv(PROJECT / '_artifacts-rolling-profit-risk' / 'nb26' / 'selection-log.csv')
schedule_source = schedule_source.loc[schedule_source.arm.eq('B11')].copy()
schedule_source['date'] = pd.to_datetime(schedule_source['date']).dt.normalize()
TARGET_SCHEDULE_BY_PERIOD = {
    period: {
        date: set(group.address.astype(str).str.lower())
        for date, group in period_group.groupby('date')
    }
    for period, period_group in schedule_source.groupby('period')
}

old_decide = decide_trades
def decide_trades(input):
    portfolio = input.state.portfolio
    equity = portfolio.get_total_equity()
    values = [float(p.get_value()) for p in portfolio.get_open_positions()]
    CYCLE_LOG.append({'date': input.timestamp, 'invested': sum(values) / equity if equity else 0., 'positions': len(values), 'max_weight': max(values + [0.]) / equity if equity else 0.})
    before = len(CAL_LOG)
    trades = old_decide(input)
    actual = {row['address'] for row in CAL_LOG[before:]}
    requested = set(TARGET_SCHEDULE.get(pd.Timestamp(input.timestamp).normalize(), set()))
    union = requested | actual
    REPLAY_LOG.append({
        'date': input.timestamp,
        'requested_count': len(requested),
        'actual_count': len(actual),
        'missing_count': len(requested - actual),
        'unexpected_count': len(actual - requested),
        'jaccard': len(requested & actual) / len(union) if union else 1.0,
        'requested_addresses': '|'.join(sorted(requested)),
        'actual_addresses': '|'.join(sorted(actual)),
    })
    return trades

display(schedule_source.groupby('period').agg(dates=('date', 'nunique'), requested_rows=('address', 'size'), requested_names=('address', 'nunique')))
"""
    cells.append(nbf.v4.new_code_cell(init))
    run = """
arms = []
for period in WINDOWS:
    for arm, method in (('S_EQUAL', 'equal'), ('S_INV_VOL', 'inverse_vol'), ('S_INV_VAR', 'inverse_variance')):
        arms.append({'period': period, 'arm': arm, 'overrides': {'weighting_method': method, 'inverse_vol_window': 30}})
write_manifest(OUT, notebook='27-research-rolling-sizing.ipynb', parent='26-research-rolling-ranking-access.ipynb', mechanism_delta='Fixed causal B11 requested-membership replay with equal, inverse-volatility and inverse-variance sizing.', arms=arms)
portfolio_metrics = run_engine_jobs(globals(), arms, OUT)
display(portfolio_metrics)
replay_summary = pd.read_csv(OUT / 'schedule-replay-log.csv').groupby('arm').agg(cycles=('date', 'size'), mean_jaccard=('jaccard', 'mean'), missing=('missing_count', 'sum'), unexpected=('unexpected_count', 'sum')).reset_index()
display(replay_summary)
assert set(replay_summary.arm) == {'S_EQUAL', 'S_INV_VOL', 'S_INV_VAR'}
assert (replay_summary.mean_jaccard == 1.0).all()
assert (replay_summary.missing == 0).all() and (replay_summary.unexpected == 0).all()
"""
    cells.append(nbf.v4.new_code_cell(run))
    nb = nbf.v4.new_notebook(cells=cells, metadata=copy.deepcopy(PARENT.metadata))
    nbf.write(nb, ROOT / "27-research-rolling-sizing.ipynb")


def build_nb28_real() -> None:
    """Build the cash-preserving exposure intervention experiment."""
    cells = base_notebook(28, "Rolling exposure diagnostics", "rolling-exposure", patcher=patch_exposure_engine_cell)
    cells[0].source = """# Rolling exposure diagnostics

Parent: [25-research-rolling-metrics-controls.ipynb](25-research-rolling-metrics-controls.ipynb)

The frozen parent is the NB25 `B00` original-policy control. E1 removes the allocator's size-risk redistribution by applying each selected name's original budget share once and leaving clipped dollars in cash. E2 applies the causal drawdown haircut `target_i *= exp(-D_i / 0.10)` to the parent's post-cap targets. `E1_SCALE` and `E2_SCALE` are uniform-scaling controls matched to each treatment's invested fraction. All four arms use the same selected names, -16% common gate, operational checks and corrected fees.

The interventions are applied to target dollars after the parent allocator has selected names and performed its normal capacity checks. No additional exit gate or ranking is introduced.

## Results

Filled after execution.
"""
    init = """
from nb23_profitable_months import set_single_redemption_fee
from rolling_track_features import validate_rolling_features
from rolling_track_simulation import WINDOWS, run_engine_jobs, write_manifest

validate_rolling_features()
ROLLING_ARM = 'E1'
CAL_RULE = 'E1'
CAL_CONFIG = None
CAL_LOOKUP = {}
ROLLING_LOOKUP = {}
CAL_LOG = []
MONTH_LOG = CAL_LOG
SCREEN_LOOKUP = {}
SCREEN_LOG = []
ACTIVE_SCREEN = 'none'
BLACKLIST_MODE = 'off'
strategy_universe = UNIVERSES['off']
CYCLE_LOG = []
EXPOSURE_LOG = []

old_decide = decide_trades
def decide_trades(input):
    portfolio = input.state.portfolio
    equity = portfolio.get_total_equity()
    values = [float(p.get_value()) for p in portfolio.get_open_positions()]
    CYCLE_LOG.append({'date': input.timestamp, 'invested': sum(values) / equity if equity else 0., 'positions': len(values), 'max_weight': max(values + [0.]) / equity if equity else 0.})
    return old_decide(input)

panel_path = PROJECT / '_artifacts-rolling-profit-risk' / 'nb25' / 'rolling-panel.parquet'
ROLLING_PANEL = pd.read_parquet(panel_path)
CAL_LOOKUP = {(pd.Timestamp(r.date), r.address, int(r.lookback)): r._asdict() for r in ROLLING_PANEL.itertuples(index=False)}
ROLLING_LOOKUP = CAL_LOOKUP

parent_metrics = pd.read_csv(PROJECT / '_artifacts-rolling-profit-risk' / 'nb25' / 'portfolio-metrics.csv')
parent_metrics = parent_metrics.loc[parent_metrics.arm.eq('B00')].copy()
parent_metrics.to_csv(OUT / 'parent-b00-metrics.csv', index=False)
method_check = pd.DataFrame([{
    'parent_allocator': 'AlphaModel._normalise_weights_size_risk_positions',
    'redistributes_after_capacity_clip': True,
    'e1_intervention': 'recompute original-share accepted dollars and retain residual cash',
    'e2_intervention': 'post-cap causal drawdown haircut',
}])
method_check.to_csv(OUT / 'exposure-method-check.csv', index=False)
display(parent_metrics)
display(method_check)
"""
    cells.append(nbf.v4.new_code_cell(init))
    run = """
arms = []
for period in WINDOWS:
    for arm in ('E1', 'E1_SCALE', 'E2', 'E2_SCALE'):
        arms.append({'period': period, 'arm': arm, 'overrides': {}})
write_manifest(OUT, notebook='28-research-rolling-exposure.ipynb', parent='25-research-rolling-metrics-controls.ipynb', mechanism_delta='B00 parent with causal no-refill and drawdown-haircut interventions plus uniform-investment controls.', arms=arms)
portfolio_metrics = run_engine_jobs(globals(), arms, OUT)
exposure_log = pd.read_csv(OUT / 'exposure-intervention-log.csv')
assert set(exposure_log.arm) == {'E1', 'E1_SCALE', 'E2', 'E2_SCALE'}
assert exposure_log.treatment_target.notna().all()
display(portfolio_metrics)
display(exposure_log.groupby('arm').agg(cycles=('date', 'size'), mean_base=('base_target', 'mean'), mean_treatment=('treatment_target', 'mean'), mean_released_cash=('released_cash', 'mean')).reset_index())
"""
    cells.append(nbf.v4.new_code_cell(run))
    nb = nbf.v4.new_notebook(cells=cells, metadata=copy.deepcopy(PARENT.metadata))
    nbf.write(nb, ROOT / "28-research-rolling-exposure.ipynb")


def build_nb29_real() -> None:
    """Build the artefact-only synthesis notebook."""
    heading = """# Rolling track synthesis

Parents: [25-research-rolling-metrics-controls.ipynb](25-research-rolling-metrics-controls.ipynb), [26-research-rolling-ranking-access.ipynb](26-research-rolling-ranking-access.ipynb), [27-research-rolling-sizing.ipynb](27-research-rolling-sizing.ipynb), [28-research-rolling-exposure.ipynb](28-research-rolling-exposure.ipynb)

This notebook reads saved NB25–NB28 artefacts and performs no new search or simulation. It reports lineage, same-date equity curves and metrics, selection coverage, exposure/cash effects and contributor shares. The three windows overlap and are not independent holdouts.

## Results

Filled after NB27 and NB28 execution.
"""
    init = """
from pathlib import Path
import json
import sys
import pandas as pd
import plotly.express as px
from IPython.display import display

PROJECT = Path.cwd()
while not (PROJECT / 'pyproject.toml').exists():
    if PROJECT == PROJECT.parent:
        raise RuntimeError('Repository root not found')
    PROJECT = PROJECT.parent
PROJECT = PROJECT / 'scratchpad/hyperliquid-ic'
OUT = PROJECT / '_artifacts-rolling-profit-risk' / 'nb29'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PROJECT))
from rolling_track_reporting import read_optional_csv, write_pending_manifest

ARTIFACT_ROOT = PROJECT / '_artifacts-rolling-profit-risk'
"""
    analysis = """
metrics_frames = []
curve_frames = []
position_frames = []
allocation_frames = []
lineage_rows = []
for number in (25, 26, 27, 28):
    directory = ARTIFACT_ROOT / f'nb{number}'
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    status = manifest.get('status', 'executed' if (directory / 'portfolio-metrics.csv').exists() else 'missing')
    lineage_rows.append({
        'notebook': number,
        'status': status,
        'parent': manifest.get('parent_experiment'),
        'mechanism_delta': manifest.get('mechanism_delta'),
        'metrics_rows': len(read_optional_csv(directory / 'portfolio-metrics.csv')),
    })
    metrics = read_optional_csv(directory / 'portfolio-metrics.csv')
    if not metrics.empty:
        metrics.insert(0, 'notebook', number)
        metrics_frames.append(metrics)
    positions = read_optional_csv(directory / 'positions.csv')
    if not positions.empty:
        positions.insert(0, 'notebook', number)
        position_frames.append(positions)
    allocations = read_optional_csv(directory / 'allocations.csv')
    if not allocations.empty:
        allocations.insert(0, 'notebook', number)
        allocation_frames.append(allocations)
    for curve_path in sorted(directory.glob('curve-*.parquet')):
        curve = pd.read_parquet(curve_path).reset_index()
        curve.columns = ['date', 'equity']
        stem = curve_path.stem.split('-', 2)
        curve['notebook'] = number
        curve['period'] = stem[1] if len(stem) > 1 else None
        curve['arm'] = stem[2] if len(stem) > 2 else None
        curve_frames.append(curve)

lineage = pd.DataFrame(lineage_rows)
metrics = pd.concat(metrics_frames, ignore_index=True) if metrics_frames else pd.DataFrame()
curves = pd.concat(curve_frames, ignore_index=True) if curve_frames else pd.DataFrame()
positions = pd.concat(position_frames, ignore_index=True) if position_frames else pd.DataFrame()
allocations = pd.concat(allocation_frames, ignore_index=True) if allocation_frames else pd.DataFrame()
lineage.to_csv(OUT / 'lineage-results.csv', index=False)
metrics.to_csv(OUT / 'metrics-all.csv', index=False)
curves.to_csv(OUT / 'equity-curves-long.csv', index=False)

if not curves.empty:
    curves['series'] = curves['notebook'].astype(str) + ':' + curves['period'].astype(str) + ':' + curves['arm'].astype(str)
    fig = px.line(curves, x='date', y='equity', color='series', title='Rolling track equity curves')
    fig.write_html(OUT / 'equity-curves.html', include_plotlyjs='cdn')

if not allocations.empty:
    exposure = allocations.groupby(['notebook', 'period', 'arm']).agg(
        cycles=('date', 'size'),
        mean_invested=('invested', 'mean'),
        min_invested=('invested', 'min'),
        mean_positions=('positions', 'mean'),
        mean_max_weight=('max_weight', 'mean'),
    ).reset_index()
else:
    exposure = pd.DataFrame()
exposure.to_csv(OUT / 'exposure-report.csv', index=False)

if not positions.empty:
    contributor = positions.groupby(['notebook', 'period', 'arm', 'address', 'name'], dropna=False).agg(
        position_count=('position_id', 'nunique'), pnl=('pnl', 'sum')
    ).reset_index()
    contributor['abs_pnl_share'] = contributor['pnl'].abs() / contributor.groupby(['notebook', 'period', 'arm'])['pnl'].transform(lambda x: x.abs().sum()).replace(0, float('nan'))
else:
    contributor = pd.DataFrame()
contributor.to_csv(OUT / 'contributor-report.csv', index=False)

replay = read_optional_csv(ARTIFACT_ROOT / 'nb27' / 'schedule-replay-log.csv')
if not replay.empty:
    replay_summary = replay.groupby('arm').agg(cycles=('date', 'size'), mean_jaccard=('jaccard', 'mean'), missing=('missing_count', 'sum'), unexpected=('unexpected_count', 'sum')).reset_index()
else:
    replay_summary = pd.DataFrame()
replay_summary.to_csv(OUT / 'selection-coverage-report.csv', index=False)

ranking = read_optional_csv(ARTIFACT_ROOT / 'nb26' / 'rolling-ranking-summary.csv')
ranking.to_csv(OUT / 'selection-before-label-coverage.csv', index=False)

deferred = pd.DataFrame([
    {'sensitivity': 'B01/B11 interval lookback 14 and 60 days', 'status': 'declared_not_run', 'reason': 'bounded robustness follow-up after primary results'},
    {'sensitivity': 'largest positive B11 contributor removal', 'status': 'declared_not_run', 'reason': 'retrospective sensitivity; identity fixed from primary result'},
])
deferred.to_csv(OUT / 'deferred-robustness.csv', index=False)
display(lineage)
display(metrics)
display(exposure)
display(replay_summary)
write_pending_manifest(OUT, notebook='29-research-rolling-track-synthesis.ipynb', parent='27-research-rolling-sizing.ipynb and 28-research-rolling-exposure.ipynb', mechanism_delta='Artefact-only synthesis of validated rolling-track experiments.', inputs=['nb25', 'nb26', 'nb27', 'nb28'], status='executed', why_not_duplicate='No new simulation, optimiser or result-dependent selection; all tables and curves are derived from saved experiment artefacts.')
"""
    nb = nbf.v4.new_notebook(
        cells=[nbf.v4.new_markdown_cell(heading), nbf.v4.new_code_cell(init), nbf.v4.new_code_cell(analysis)],
        metadata=copy.deepcopy(PARENT.metadata),
    )
    nbf.write(nb, ROOT / "29-research-rolling-track-synthesis.ipynb")


def build_pending_notebook(number: int, title: str, parent: str, mechanism: str, body: str) -> None:
    """Build a fast, artefact-only scaffold for a deferred track notebook."""
    slug = {27: "rolling-sizing", 28: "rolling-exposure", 29: "rolling-track-synthesis"}[number]
    heading = f"""# {title}

Parent: [{parent}]({parent})

Status: pending corrected NB25/NB26 results. This notebook is an executable reporting scaffold; it does not run a new optimiser or backtest. {mechanism}

The notebook will only consume saved causal ledgers and metrics. It must be completed and run after the primary rolling panel and factorial have passed their timestamp-unit, control-parity and fee checks.
"""
    cells = [nbf.v4.new_markdown_cell(heading)]
    cells.append(nbf.v4.new_code_cell("""
from pathlib import Path
import sys
import pandas as pd
from IPython.display import display

PROJECT = Path.cwd()
while not (PROJECT / 'pyproject.toml').exists():
    if PROJECT == PROJECT.parent:
        raise RuntimeError('Repository root not found')
    PROJECT = PROJECT.parent
PROJECT = PROJECT / 'scratchpad/hyperliquid-ic'
OUT = PROJECT / '_artifacts-rolling-profit-risk' / f'nb{NUMBER}'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PROJECT))
from rolling_track_reporting import read_optional_csv, write_pending_manifest
""".replace("NUMBER", str(number))))
    cells.append(nbf.v4.new_code_cell(body))
    nb = nbf.v4.new_notebook(cells=cells, metadata=copy.deepcopy(PARENT.metadata))
    nbf.write(nb, ROOT / f"{number}-research-{slug}.ipynb")


def build_deferred_notebooks() -> None:
    build_nb27_real()
    build_nb28_real()
    build_nb29_real()


if __name__ == "__main__":
    build(True)
    build(False)
    build_deferred_notebooks()
