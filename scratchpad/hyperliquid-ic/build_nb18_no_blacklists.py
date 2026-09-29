from pathlib import Path
import copy
import nbformat as nbf

root = Path(__file__).resolve().parent
source = nbf.read(root / "09-research-leads-vs-a0b.ipynb", as_version=4)
cells = []


def md(s):
    cells.append(nbf.v4.new_markdown_cell(s))


def code(s):
    cells.append(nbf.v4.new_code_cell(s))


md("""# Incumbent and leads with blacklists disabled

Based on `09-research-leads-vs-a0b.ipynb` and the independent simulator in
`08-research-a0b-production-comparison.ipynb`.

Paired blacklists-on/off reruns of anchor, measured_8, inverse_vol_q10, floor15,
floor20 and A0b. Both modes use the same locally cached data snapshot. Disable
manual address/protocol exclusions, producer Blacklisted/Dangerous risk labels,
malicious/broken flags, curator quarantine and engine/token blacklist guards.
All overrides are local to this notebook process. Preserve strategy risk filters,
TVL, denomination, deposit availability, fees, forward filling and execution rules.
Upstream observations already removed by the data producer cannot be recovered here.

Engine windows retain the parent cold starts: 2026-01-01 to 2026-07-10 and
2025-08-01 to 2026-09-09 (exclusive ends). A0b retains its 2026-01-01–07-08 and
2025-09-13–2026-09-12 inclusive windows. Shared-date metrics are additionally
reported, with the full comparison a slice of the engine run, not a new cold start.

## Key new insights
Pending execution.

## Summary of results
Pending execution.

## Robustness of results
Pending execution; inspect restored vault contributions, best cycles, kurtosis
and curator quarantine overlap before interpreting any improved Sharpe.
""")
for i in [2, 4, 6]:
    c = copy.deepcopy(source.cells[i])
    c.outputs = []
    c.execution_count = None
    c.source = c.source.replace("09-research-leads-vs-a0b", "18-research-leads-no-blacklists")
    cells.append(c)
code("""import contextlib
import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np

ROOT = Path.cwd()
while not (ROOT / 'pyproject.toml').exists():
    if ROOT == ROOT.parent: raise RuntimeError('Repository root not found')
    ROOT = ROOT.parent
PROJECT = ROOT / 'scratchpad/hyperliquid-ic'
OUT = PROJECT / '_artifacts-leads-no-blacklists'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(PROJECT))
curator = importlib.import_module('tradeexecutor.curator.curator')
selector = importlib.import_module('tradeexecutor.curator.vault_universe_creation')
hyper_selector = importlib.import_module('tradeexecutor.curator.hyperliquid_vault_universe')
META_PATH = Path.home() / '.cache/tradingstrategy/vaults/downloads/vault-metadata.json'
PRICE_PATH = META_PATH.with_name('vault-prices.parquet')
RAW_META = json.loads(META_PATH.read_text())['vaults']
MANUAL_ADDRESS = '0x5290ab34acb59cfe1371baa5782eba14433d308f'
META = {v['address'].lower(): v for v in RAW_META if v.get('chain_id') == 9999}

def digest(path):
    with open(path, 'rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

INPUTS = [{'path': str(p), 'sha256': digest(p)} for p in [META_PATH, PRICE_PATH, PROJECT/'09-research-leads-vs-a0b.ipynb', PROJECT/'stable_profit.py', PROJECT/'_artifacts-rewrite/features.parquet', PROJECT/'_artifacts-rewrite/observations.parquet']]
(OUT/'input-manifest.json').write_text(json.dumps(INPUTS, indent=2))
ORIGINAL_PARSE = selector.parse_vault

def parse_without_blacklists(*args, **kwargs):
    v = ORIGINAL_PARSE(*args, **kwargs)
    if v is not None:
        v.excluded = False
        v.excluded_protocol_reason = None
        if v.risk in {'Blacklisted', 'Dangerous'}: v.risk = None
        v.flags = [f for f in v.flags if f not in {'malicious', 'broken'}]
    return v

UNIVERSE_MODE = 'on'
SOURCE_LISTS = {}
def local_vault_universe(**kwargs):
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.object(hyper_selector, '_curator_fingerprint', return_value='nb18-local-'+UNIVERSE_MODE))
        stack.enter_context(patch.object(hyper_selector, 'fetch_vaults', return_value=RAW_META))
        stack.enter_context(patch.object(hyper_selector, '_load_cache', return_value=None))
        stack.enter_context(patch.object(hyper_selector, '_save_cache', return_value=None))
        if UNIVERSE_MODE == 'off':
            stack.enter_context(patch.object(hyper_selector, 'parse_vault', side_effect=parse_without_blacklists))
        result = hyper_selector.build_hyperliquid_vault_universe(**kwargs)
    SOURCE_LISTS[UNIVERSE_MODE] = result
    return result

BLACKLIST_MODE = 'on'
""")
u = source.cells[8].source
u = u.replace("from tradeexecutor.curator import build_hyperliquid_vault_universe", "build_hyperliquid_vault_universe = local_vault_universe")
u = u.replace(
    "strategy_universe = create_trading_universe(universe_input)",
    """UNIVERSES = {}
for UNIVERSE_MODE in ('on', 'off'):
    with contextlib.ExitStack() as stack:
        if UNIVERSE_MODE == 'off':
            stack.enter_context(patch('tradeexecutor.strategy.trading_strategy_universe.mark_blacklisted_vaults_ignored', return_value=[]))
        UNIVERSES[UNIVERSE_MODE] = create_trading_universe(universe_input)
strategy_universe = UNIVERSES['on']""",
)
code(u)
code("""on_addresses = {a.lower() for _, a in SOURCE_LISTS['on']}
off_addresses = {a.lower() for _, a in SOURCE_LISTS['off']}
assert on_addresses <= off_addresses
membership_rows = []
for address in sorted(on_addresses | off_addresses | {MANUAL_ADDRESS}):
    v = META.get(address, {})
    membership_rows.append({'address': address, 'name': v.get('name'), 'universe_on': address in on_addresses,
        'universe_off': address in off_addresses, 'manual_blacklist': address == MANUAL_ADDRESS,
        'curator_excluded': address in curator.EXCLUDED_VAULTS,
        'excluded_protocol': v.get('protocol_slug') in curator.EXCLUDED_PROTOCOLS,
        'risk': v.get('risk'), 'flags': str(v.get('flags')),
        'quarantines': str([q[1:] for q in curator.QUARANTINE_PERIODS if q[0] == address])})
MEMBERSHIP = pd.DataFrame(membership_rows)
MEMBERSHIP.to_csv(OUT/'universe-membership.csv', index=False)
display(MEMBERSHIP[~MEMBERSHIP.universe_on | MEMBERSHIP.manual_blacklist | MEMBERSHIP.quarantines.ne('[]')])
for mode, universe in UNIVERSES.items():
    rows = [{'address': p.pool_address, 'ignore_reason': p.get_ignore_reason(), 'risk': p.get_vault_risk_level()} for p in universe.iterate_pairs() if p.is_vault()]
    pd.DataFrame(rows).to_csv(OUT/f'loaded-pairs-{mode}.csv', index=False)
""")
indicator_source = source.cells[10].source.split("display_indicators(indicators)")[0]
indicator_source += """
#: Keep all dependencies of indicators consumed by these fixed configurations.
needed = {'inclusion_criteria', 'tvl_included_pair_count', 'return_gate',
          'cagr_sortino_weight', 'cagr_sharpe_weight', 'inverse_vol',
          'fresh_observation_count', 'btc_beta'}
pending = list(needed)
while pending:
    for dependency in indicators.registry[pending.pop()].dependencies or []:
        name = dependency.__name__
        if name not in needed:
            needed.add(name)
            pending.append(name)
indicators.registry = {name: definition for name, definition in indicators.registry.items() if name in needed}
display_indicators(indicators)
"""
code(indicator_source)
s = source.cells[14].source
s = s.replace("if not state.is_good_pair(pair) or is_quarantined(pair.pool_address, timestamp):", 'if BLACKLIST_MODE == "on" and (not state.is_good_pair(pair) or is_quarantined(pair.pool_address, timestamp)):')
s = s.replace("if str(pair.pool_address).lower() in MANUAL_BLACKLIST:", 'if BLACKLIST_MODE == "on" and str(pair.pool_address).lower() in MANUAL_BLACKLIST:')
code(s)
code(source.cells[16].source.split("# Anchor on the development window.")[0].replace("max_workers=1", "max_workers=4"))
code(source.cells[24].source)
md("""## Paired engine reruns

Twenty runs: five configurations × two periods × blacklists on/off. Saves each
curve, per-position profit and loss, best-cycle trade detail and compact metrics
immediately. The original settlement and fee convention is retained in both modes.
""")
code("""from tqdm_loggable.auto import tqdm
import time

CONFIGS = {
    'anchor': {},
    'measured_8': {'vol_drop_mode':'measured_only','vol_matched_drop_count':8},
    'inverse_vol_q10': {'stability_prefilter_signal':'inverse_vol','stability_prefilter_direction':'low','stability_prefilter_fraction':0.10,'require_scored_candidates':False},
    'floor15': {'gate_lookback_days':45,'gate_threshold':1.15**(45/365)-1},
    'floor20': {'gate_lookback_days':45,'gate_threshold':1.20**(45/365)-1},
}
WINDOWS = {'hyper_ai': (datetime.datetime(2026,1,1),datetime.datetime(2026,7,10)),
           'full': (datetime.datetime(2025,8,1),datetime.datetime(2026,9,9))}
RESULTS = {}; rows=[]; position_rows=[]; trade_rows=[]
started = time.monotonic()
jobs = [(mode, period, label) for mode in ('on','off') for period in WINDOWS for label in CONFIGS]
for job_index, (mode, period, label) in enumerate(tqdm(jobs, desc='Paired engine comparisons')):
    print(f'Run {job_index+1}/{len(jobs)}: {mode}/{period}/{label}; estimated remaining minutes: ' + (f'{(time.monotonic()-started)/job_index*(len(jobs)-job_index)/60:.1f}' if job_index else 'unknown until first run'))
    BLACKLIST_MODE = mode
    strategy_universe = UNIVERSES[mode]
    VOL_DROP_LOG.clear(); COMPLEMENT_LOG.clear(); SLEEVE_LOG.clear(); PREFILTER_LOG.clear()
    start,end = WINDOWS[period]
    with contextlib.ExitStack() as stack:
        if mode == 'off':
            stack.enter_context(patch('tradeexecutor.strategy.pandas_trader.position_manager.PositionManager.is_problematic_pair', return_value=False))
        st, eq, ret = run_variant(f'no-blacklists-{mode}-{label}-{period}', backtest_start=start, backtest_end=end, **CONFIGS[label])
    assert eq.notna().all() and (eq > 0).all()
    rc, ppy = cycle_returns(eq)
    r = panel(label, st, eq, ret).to_dict()
    r.update(mode=mode,period=period,candidate=label,final_equity=float(eq.iloc[-1]),
             best_cycle=float(rc.max()),best_cycle_date=str(rc.idxmax()),excess_kurtosis=float(rc.kurt()),
             largest_vault=largest_contributing_vault(st))
    rows.append(r); RESULTS[(mode,period,label)] = eq
    saved_curve = eq.rename('equity').to_frame()
    saved_curve.attrs = {}
    saved_curve.to_parquet(OUT/f'engine-equity-{mode}-{period}-{label}.parquet')
    best_date=rc.idxmax(); best_start=eq.index[eq.index.get_loc(best_date)-1]
    for pos in st.portfolio.get_all_positions():
        if pos.is_credit_supply(): continue
        address=str(pos.pair.pool_address).lower()
        position_rows.append({'mode':mode,'period':period,'candidate':label,'position_id':pos.position_id,
            'address':address,'name':META.get(address,{}).get('name'), 'opened_at':pos.opened_at,'closed_at':pos.closed_at,
            'pnl':float(pos.get_total_profit_usd() or 0), 'realised_pnl':float(pos.get_realised_profit_usd() or 0),
            'unrealised_pnl':float(pos.get_unrealised_profit_usd() or 0),
            'held_during_best_cycle':pos.opened_at<=best_date and (pos.closed_at is None or pos.closed_at>=best_start),
            'curator_excluded':address in curator.EXCLUDED_VAULTS,'manual_blacklist':address==MANUAL_ADDRESS,
            'opened_during_quarantine':curator.is_quarantined(address,pos.opened_at)})
        for tr in pos.trades.values():
            trade_rows.append({'mode':mode,'period':period,'candidate':label,'position_id':pos.position_id,'address':address,
                'date':tr.executed_at,'quantity':float(tr.executed_quantity or 0),'price':float(tr.executed_price or 0),
                'value':float(tr.get_executed_value() or 0)})
    pd.DataFrame(rows).to_csv(OUT/'engine-metrics.csv',index=False)
    pd.DataFrame(position_rows).to_csv(OUT/'engine-positions.csv',index=False)
    pd.DataFrame(trade_rows).to_csv(OUT/'engine-trades.csv',index=False)
    del st
ENGINE_METRICS=pd.DataFrame(rows)
display(ENGINE_METRICS[['mode','period','candidate','cagr','cycle_sharpe','max_dd','best_cycle','excess_kurtosis']])
""")
md("""## Independent A0b reruns

A0b has no runtime quarantine check in its original simulator; its paired toggle
changes universe exclusions and the manual blacklist only. This preserves the
independent simulator rather than introducing a new execution model. Full pre-start
feature history is already embedded in the saved features. The original observation
slicing and accounting are retained. Missing restored addresses in the saved feature
panel are reported explicitly.
""")
code("""from ic_research import ResearchConfig, summarise_backtest
from stable_profit import simulate_stable_policy
features=pd.read_parquet(PROJECT/'_artifacts-rewrite/features.parquet')
observations=pd.read_parquet(PROJECT/'_artifacts-rewrite/observations.parquet')
features['date']=pd.to_datetime(features.date).dt.normalize()
features['address']=features.address.str.lower()
observations['timestamp']=pd.to_datetime(observations.timestamp)
observations['address']=observations.address.str.lower()
a0b_rows=[]; A0B={}
A0B_PERIODS={'hyper_ai':('2026-01-01','2026-07-08'),'full':('2025-09-13','2026-09-12')}
for mode in ('on','off'):
    addresses=on_addresses-{MANUAL_ADDRESS} if mode=='on' else off_addresses
    pd.DataFrame({'address':sorted(addresses-set(features.address))}).to_csv(OUT/f'a0b-missing-features-{mode}.csv',index=False)
    for period,(start,end) in A0B_PERIODS.items():
        f=features[features.date.between(start,end)&features.address.isin(addresses)].copy()
        o=observations[observations.timestamp.dt.normalize().between(start,end)&observations.address.isin(addresses)].copy()
        eq,tr,pool=simulate_stable_policy(f,o,policy_name='A0b',config=ResearchConfig(),max_positions=6)
        A0B[(mode,period)]=pd.Series(eq.equity.to_numpy(),index=pd.to_datetime(eq.date))
        eq.to_parquet(OUT/f'a0b-equity-{mode}-{period}.parquet',index=False)
        tr.to_parquet(OUT/f'a0b-trades-{mode}-{period}.parquet',index=False)
        pool.to_parquet(OUT/f'a0b-pool-{mode}-{period}.parquet',index=False)
        a0b_rows.append({'mode':mode,'period':period,**summarise_backtest(eq)})
pd.DataFrame(a0b_rows).to_csv(OUT/'a0b-metrics.csv',index=False)
display(pd.DataFrame(a0b_rows))
""")
md("""## Same-date curves, metrics and blacklist effect

All comparison metrics use the engine's two-day marks. Weekly Sharpe is also
shown. Each on/off pair uses the same start, end, data, fees and strategy settings.
Historical NB09 figures are a separate drift check because curator policy and
metadata may have changed since that run.
""")
code("""import matplotlib.pyplot as plt

def metrics(eq):
    r=eq.pct_change().dropna(); days=(eq.index[-1]-eq.index[0]).days
    weekly=eq.resample('W-SUN').last().pct_change().dropna()
    return {'start':str(eq.index[0].date()),'end':str(eq.index[-1].date()),'observations':len(eq),
        'cagr':float((eq.iloc[-1]/eq.iloc[0])**(365/days)-1),
        'sharpe':float(r.mean()/r.std()*np.sqrt(365/2)) if r.std()>0 else np.nan,
        'weekly_sharpe':float(weekly.mean()/weekly.std()*np.sqrt(52)) if weekly.std()>0 else np.nan,
        'volatility':float(r.std()*np.sqrt(365/2)), 'max_drawdown':float((eq/eq.cummax()-1).min()),
        'best_cycle':float(r.max()),'excess_kurtosis':float(r.kurt())}
matched=[]
fig,axes=plt.subplots(2,2,figsize=(17,10))
for row_index,period in enumerate(WINDOWS):
    start=pd.Timestamp(A0B_PERIODS[period][0]); end=pd.Timestamp('2026-07-08' if period=='hyper_ai' else '2026-09-08')
    dates=RESULTS[('on',period,'anchor')].index
    dates=dates[(dates>=start)&(dates<=end)]
    for column,mode in enumerate(('on','off')):
        ax=axes[row_index,column]
        for label in list(CONFIGS)+['A0b']:
            eq=RESULTS[(mode,period,label)] if label!='A0b' else A0B[(mode,period)]
            eq=eq.reindex(eq.index.union(dates)).sort_index().ffill().reindex(dates)
            assert eq.notna().all()
            matched.append({'mode':mode,'period':period,'candidate':label,**metrics(eq)})
            ax.plot(eq.index,eq/eq.iloc[0],label=label)
        ax.set_title(f'{period}: blacklists {mode}'); ax.legend(); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig(OUT/'equity-comparison.png',dpi=150); plt.show()
MATCHED=pd.DataFrame(matched); MATCHED.to_csv(OUT/'date-matched-metrics.csv',index=False)
DELTA=MATCHED[MATCHED['mode'].eq('off')].merge(MATCHED[MATCHED['mode'].eq('on')],on=['period','candidate'],suffixes=('_off','_on'))
for col in ['cagr','sharpe','max_drawdown','best_cycle']:
    DELTA[col+'_change']=DELTA[col+'_off']-DELTA[col+'_on']
DELTA.to_csv(OUT/'blacklist-effect.csv',index=False)
display(DELTA[['period','candidate','cagr_on','cagr_off','cagr_change','sharpe_on','sharpe_off','max_drawdown_on','max_drawdown_off']])
for period,file in [('hyper_ai','production-period-date-matched.csv'),('full','full-period-date-matched-overlap.csv')]:
    old=pd.read_csv(PROJECT/'_artifacts-leads-vs-a0b'/file)
    bridge=MATCHED[MATCHED['mode'].eq('on')&MATCHED.period.eq(period)].merge(old,on='candidate',suffixes=('_current','_historical'))
    bridge.to_csv(OUT/f'historical-control-drift-{period}.csv',index=False)
""")
md("""## Position attribution and robustness

Per-position and per-address profit-and-loss quantify dependence on restored
vaults. Quarantine overlap comes from the canonical `curator.py` rules. Best-cycle
holdings and executed trades are retained for distinguishing a broad move from
one vault's price jump. Positive-P&L concentration is a descriptive decomposition,
not a leave-one-vault-out resimulation.
""")
code("""POSITIONS=pd.DataFrame(position_rows)
ATTR=POSITIONS.groupby(['mode','period','candidate','address','name'],dropna=False).agg(pnl=('pnl','sum'),positions=('position_id','count'),quarantine_entries=('opened_during_quarantine','sum'),best_cycle_positions=('held_during_best_cycle','sum')).reset_index()
ATTR=ATTR.merge(MEMBERSHIP,on=['address','name'],how='left')
ATTR.to_csv(OUT/'vault-attribution.csv',index=False)
leaders=[]
for key,group in ATTR.groupby(['mode','period','candidate']):
    group=group.sort_values('pnl',ascending=False); positive=group.pnl.clip(lower=0).sum()
    best=group.iloc[0]
    leaders.append(dict(zip(['mode','period','candidate'],key))|{'leader':best.address,'leader_name':best['name'],'leader_pnl':best.pnl,'leader_positive_pnl_share':best.pnl/positive if positive else np.nan,'top5_positive_pnl_share':group.pnl.clip(lower=0).head(5).sum()/positive if positive else np.nan})
CONCENTRATION=pd.DataFrame(leaders); CONCENTRATION.to_csv(OUT/'concentration.csv',index=False)
display(CONCENTRATION)
display(ATTR[ATTR['mode'].eq('off')&(ATTR.curator_excluded.fillna(False)|ATTR.manual_blacklist.fillna(False)|ATTR.quarantine_entries.gt(0)|~ATTR.universe_on.fillna(False))].sort_values('pnl',ascending=False).head(40))
assert all(digest(Path(i['path']))==i['sha256'] for i in INPUTS), 'Input snapshot changed during run'
report={'source':'09-research-leads-vs-a0b.ipynb','engine_runs':len(rows),'a0b_runs':len(a0b_rows),'source_universe_on':len(on_addresses),'source_universe_off':len(off_addresses),'restored_source_addresses':sorted(off_addresses-on_addresses),'inputs':INPUTS,'scope':'manual, curator, risk/flag, quarantine, producer engine and token blacklist guards disabled locally; upstream deleted observations not recovered','a0b_limitation':'saved feature-panel coverage; original simulator has no runtime quarantine logic','periods':{k:[str(a),str(b)] for k,(a,b) in WINDOWS.items()}}
(OUT/'run-manifest.json').write_text(json.dumps(report,indent=2,default=str))
summary='# Incumbent and leads without blacklists\\n\\nPaired reruns on one data snapshot. All figures below use date-matched two-day marks.\\n\\n'+DELTA[['period','candidate','cagr_on','cagr_off','sharpe_on','sharpe_off','max_drawdown_on','max_drawdown_off']].to_markdown(index=False)+'\\n\\n## Robustness of results\\n\\n'+CONCENTRATION.to_markdown(index=False)+'\\n\\nCurator exclusions and quarantines are disabled in the off engine arms. A0b changes only its universe/manual exclusion: it has no runtime quarantine guard. Upstream omitted histories remain unavailable. Full-period engine curves are sliced from their original earlier cold start. The inherited fee and NAV accounting are unchanged.\\n'
(PROJECT/'no-blacklists-summary-01.md').write_text(summary)
""")
md("""## Observed NAV and market-context audit

Inspect the largest restored-vault contributions and compare each best portfolio
cycle with BTC and ETH on completed daily candles. Raw interval spikes are
diagnostics, not additional strategy filters.
""")
code("""from nb18_robustness import report
heading_findings = report(PROJECT)
""")
nb = nbf.v4.new_notebook(cells=cells, metadata=source.metadata)
nbf.write(nb, root / "18-research-leads-no-blacklists.ipynb")
print(root / "18-research-leads-no-blacklists.ipynb")
