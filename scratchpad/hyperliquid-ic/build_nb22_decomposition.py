from pathlib import Path
import copy
import nbformat as n

p = Path(__file__).resolve().parent
parent = n.read(p / "21-research-quality-only-portfolios.ipynb", as_version=4)
cells = [n.v4.new_markdown_cell("""# Allocation-limit decomposition

Based on `21-research-quality-only-portfolios.ipynb`. Full 2×2×2 factorial for the engine anchor: position count (6/all), portfolio cap (33%/100%), historical vault-TVL capacity (33%/100%). Run both periods, with and without intothecryptoverse.com: 32 fixed simulations, no optimisation. Blacklists remain disabled. Preserve ranking, inverse-variance sizing, return gate, fees and execution. No new quality screen or young-vault policy.

## Key new insights
Pending execution.

## Summary of results
Pending execution.

## Robustness of results
Pending execution.""")]
for i in range(1, 11):
    c = copy.deepcopy(parent.cells[i])
    c.outputs = []
    c.execution_count = None
    c.source = c.source.replace("'_artifacts-quality-only'", "'_artifacts-allocation-decomposition'").replace("id = '21-research-quality-only-portfolios'", "id = '22-research-allocation-decomposition'")
    if i == 4:
        a = c.source.index("META_PATH = Path.home()")
        b = c.source.index("RAW_META =", a)
        c.source = c.source[:a] + """import shutil
SNAPSHOT=OUT/'inputs';SNAPSHOT.mkdir(exist_ok=True)
for filename in ['vault-metadata.json','vault-prices.parquet']:
    target=SNAPSHOT/filename
    if not target.exists():shutil.copy2(Path.home()/'.cache/tradingstrategy/vaults/downloads'/filename,target)
META_PATH=SNAPSHOT/'vault-metadata.json'
PRICE_PATH=SNAPSHOT/'vault-prices.parquet'
from tradingstrategy.vault_data_client import VaultDataset

def frozen_download(self,dataset,*args,**kwargs):
    return {VaultDataset.vault_metadata:META_PATH,VaultDataset.vault_prices:PRICE_PATH}[dataset]

""" + c.source[b:]
    if i == 5:
        c.source = c.source.replace("    with contextlib.ExitStack() as stack:", "    with contextlib.ExitStack() as stack:\n        stack.enter_context(patch('tradingstrategy.vault_data_client.VaultDataClient.download',frozen_download))")
    cells.append(c)
cells.append(n.v4.new_code_cell("""import hashlib,json,itertools,time
from tqdm_loggable.auto import tqdm
from nb20_stability_screens import curve_metrics
prior_inputs=json.loads((PROJECT/'_artifacts-quality-only/input-manifest.json').read_text())
current_inputs=json.loads((OUT/'input-manifest.json').read_text())
input_drift=[]
for before,after in zip(prior_inputs,current_inputs):
    input_drift.append({'old_path':before['path'],'new_path':after['path'],'old_hash':before['sha256'],'new_hash':after['sha256'],'identical':before['sha256']==after['sha256']})
    if not before['path'].endswith(('vault-metadata.json','vault-prices.parquet')):
        assert before['sha256']==after['sha256'],before['path']
pd.DataFrame(input_drift).to_csv(OUT/'input-drift.csv',index=False)
display(pd.DataFrame(input_drift))
SCREEN_LOOKUP={};SCREEN_LOG=[];CYCLE_LOG=[];ACTIVE_SCREEN='none';BLACKLIST_MODE='off'
strategy_universe=UNIVERSES['off']
original_decide_trades=decide_trades

def decide_trades(input):
    portfolio=input.state.portfolio;equity=portfolio.get_total_equity();cash=portfolio.get_cash()
    values=[float(p.get_value()) for p in portfolio.get_open_positions()]
    invested=sum(values)
    CYCLE_LOG.append({'date':input.timestamp,'invested_fraction':invested/equity if equity else 0.,
        'positions':len(values),'max_weight':max(values+[0.])/equity if equity else 0.,
        'effective_positions':invested**2/sum(v*v for v in values) if invested>0 else 0.})
    return original_decide_trades(input)

WINDOWS={'hyper_ai':(datetime.datetime(2026,1,1),datetime.datetime(2026,7,10)),
         'full':(datetime.datetime(2025,8,1),datetime.datetime(2026,9,9))}
LEADER='0xcbbb26d5e622fb877e12745921ae8b1f820ffbed'
FACTORS=list(itertools.product([0,1],repeat=3))
display(pd.DataFrame([{'arm':f'N{a}W{b}V{c}','max_positions':len(off_addresses) if a else 6,'portfolio_cap':1. if b else .33,'vault_tvl_cap':1. if c else .33} for a,b,c in FACTORS]))
"""))
cells.append(n.v4.new_code_cell("""results=[];positions=[];trades=[];cycles=[];parity=[]
jobs=[(period,removed,*bits) for period in WINDOWS for removed in [False,True] for bits in FACTORS]
started=time.monotonic()
for k,(period,removed,n_all,w_all,v_all) in enumerate(tqdm(jobs,desc='Allocation factorial')):
    arm=f'N{n_all}W{w_all}V{v_all}';mask='leader_out' if removed else 'all'
    remaining=(time.monotonic()-started)/k*(len(jobs)-k)/60 if k else None
    print(f'Run {k+1}/{len(jobs)}: {period}/{mask}/{arm}; estimated minutes remaining: {remaining}')
    SCREEN_LOG.clear();CYCLE_LOG.clear();start,end=WINDOWS[period]
    with patch('tradeexecutor.strategy.pandas_trader.position_manager.PositionManager.is_problematic_pair',return_value=False):
        state,eq,ret=run_variant('allocation-decomposition-'+period+'-'+mask+'-'+arm,
            masked={LEADER} if removed else set(),backtest_start=start,backtest_end=end,
            max_assets_in_portfolio=len(off_addresses) if n_all else 6,
            max_concentration_pct=1. if w_all else .33,per_position_cap_of_pool_pct=1. if v_all else .33)
    assert eq.notna().all() and eq.gt(0).all()
    saved=eq.rename('equity').to_frame();saved.attrs={};saved.to_parquet(OUT/f'curve-{period}-{mask}-{arm}.parquet')
    common_start=pd.Timestamp('2026-01-01' if period=='hyper_ai' else '2025-09-13')
    common_end=pd.Timestamp('2026-07-08' if period=='hyper_ai' else '2026-09-08')
    matched=eq.loc[common_start:common_end]
    keys={'period':period,'mask':mask,'arm':arm,'N':n_all,'W':w_all,'V':v_all}
    results.append({**keys,**curve_metrics(matched)})
    ref=None
    if not removed and arm=='N0W0V0':ref=PROJECT/'_artifacts-stability-screens'/f'curve-{period}-anchor-none.parquet'
    elif not removed and arm=='N1W1V1':ref=PROJECT/'_artifacts-quality-only'/f'curve-{period}-anchor-none.parquet'
    elif removed and arm=='N1W1V1':ref=PROJECT/'_artifacts-quality-only/leave-one-out'/f'curve-{period}.parquet'
    if ref is not None:
        old=pd.read_parquet(ref).equity;assert eq.index.equals(old.index)
        error=float((eq-old).abs().max());parity.append({**keys,'maximum_equity_difference':error})
    for pos in state.portfolio.get_all_positions():
        if pos.is_credit_supply():continue
        address=str(pos.pair.pool_address).lower()
        assert not removed or address!=LEADER
        positions.append({**keys,'position_id':pos.position_id,'address':address,'name':META.get(address,{}).get('name'),
            'opened_at':pos.opened_at,'closed_at':pos.closed_at,'pnl':float(pos.get_total_profit_usd() or 0)})
        for trade in pos.trades.values():
            trades.append({**keys,'position_id':pos.position_id,'address':address,'date':trade.executed_at,
                'quantity':float(trade.executed_quantity or 0),'value':float(trade.get_executed_value() or 0)})
    cycles.extend([{**keys,**c} for c in CYCLE_LOG])
    for name,rows in [('metrics',results),('positions',positions),('trades',trades),('cycles',cycles),('parity',parity)]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    del state
METRICS=pd.DataFrame(results);display(METRICS)
"""))
cells.append(n.v4.new_code_cell("from nb22_decomposition_report import report\nfindings=report(PROJECT)"))
n.write(n.v4.new_notebook(cells=cells, metadata=copy.deepcopy(parent.metadata)), p / "22-research-allocation-decomposition.ipynb")
