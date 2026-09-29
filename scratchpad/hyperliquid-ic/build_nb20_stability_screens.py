from pathlib import Path
import copy
import nbformat as n

p = Path(__file__).resolve().parent
src = n.read(p / "18-research-leads-no-blacklists.ipynb", as_version=4)
cells = [n.v4.new_markdown_cell("""# Portfolio tests of StratWise-inspired stability screens

Based on `18-research-leads-no-blacklists.ipynb` and `19-research-stratwise-entry-forensics.ipynb`.

Fixed daily and weekly screens; six strategies; two periods; blacklists disabled. Missing screen history passes through, preserving young-vault eligibility under existing strategy rules.

## Key new insights
Pending execution.

## Summary of results
Pending execution.

## Robustness of results
Pending execution.""")]
for i in range(1, 11):
    c = copy.deepcopy(src.cells[i])
    c.outputs = []
    c.execution_count = None
    c.source = c.source.replace("'_artifacts-leads-no-blacklists'", "'_artifacts-stability-screens'").replace("id = '18-research-leads-no-blacklists'", "id = '20-research-stability-screen-portfolios'")
    if i == 8:
        needle = "        composite_signal = indicators.get_indicator_value(selection_score_indicator, pair=pair)"
        assert needle in c.source
        c.source = c.source.replace(
            needle,
            """        _addr=str(pair.pool_address).lower()
        _record=SCREEN_LOOKUP.get((pd.Timestamp(timestamp).normalize(),_addr),{})
        _known=bool(_record.get(ACTIVE_SCREEN+'_known',False)) if ACTIVE_SCREEN!='none' else False
        _pass=bool(_record.get(ACTIVE_SCREEN+'_pass',True)) if ACTIVE_SCREEN!='none' else True
        SCREEN_LOG.append({'date':timestamp,'address':_addr,'known':_known,'passed':_pass})
        if not _pass:
            continue
""" + needle,
        )
    cells.append(c)
cells.append(n.v4.new_code_cell("""from nb20_stability_screens import make_screens
SCREEN_FRAME, SCREEN_CHECKS = make_screens(PROJECT, off_addresses)
SCREEN_FRAME.to_parquet(OUT/'screen-features.parquet',index=False)
SCREEN_CHECKS.to_csv(OUT/'scalar-parity.csv',index=False)
SCREEN_LOOKUP=SCREEN_FRAME.set_index(['date','address'])[['daily_known','daily_pass','weekly_known','weekly_pass']].to_dict('index')
ACTIVE_SCREEN='none'; SCREEN_LOG=[]; CYCLE_LOG=[]
original_decide_trades=decide_trades

def decide_trades(input):
    portfolio=input.state.portfolio
    equity=portfolio.get_total_equity()
    CYCLE_LOG.append({'date':input.timestamp,'invested_fraction':1-portfolio.get_cash()/equity if equity>0 else 0.,
        'positions':len(list(portfolio.get_open_positions()))})
    return original_decide_trades(input)

display(SCREEN_FRAME.groupby('address')[['daily_known','weekly_known']].sum().describe())
"""))
cells.append(n.v4.new_markdown_cell("""## Engine runs

The screen filters candidates after the existing momentum gate, before ranking and sizing. Rejected holdings can therefore be sold. A fresh unchanged control must reproduce NB18 before its screened companions are interpreted. Saves results after every run."""))
code = src.cells[12].source
code = code.replace("jobs = [(mode, period, label) for mode in ('on','off') for period in WINDOWS for label in CONFIGS]", "jobs = [(screen,period,label) for period in WINDOWS for label in CONFIGS for screen in ('none','daily','weekly')]")
code = code.replace("(mode, period, label) in enumerate", "(screen, period, label) in enumerate")
code = code.replace("    BLACKLIST_MODE = mode", "    mode='off'\n    ACTIVE_SCREEN=screen\n    SCREEN_LOG.clear();CYCLE_LOG.clear()\n    BLACKLIST_MODE = mode")
code = code.replace("{mode}/{period}/{label}", "{screen}/{period}/{label}")
code = code.replace("f'no-blacklists-{mode}-{label}-{period}'", "f'screen-{screen}-{label}-{period}'")
code = code.replace("r.update(mode=mode,period=period,candidate=label", "r.update(mode=mode,period=period,candidate=label,screen=screen")
code = code.replace("RESULTS[(mode,period,label)]", "RESULTS[(screen,period,label)]")
code = code.replace("OUT/f'engine-equity-{mode}-{period}-{label}.parquet'", "OUT/f'curve-{period}-{label}-{screen}.parquet'")
code = code.replace("'candidate':label,'position_id'", "'candidate':label,'screen':screen,'position_id'")
code = code.replace("OUT/'engine-metrics.csv'", "OUT/'native-engine-metrics.csv'").replace("OUT/'engine-positions.csv'", "OUT/'positions.csv'").replace("OUT/'engine-trades.csv'", "OUT/'trades.csv'")
code = code.replace(
    "    del st",
    """    if screen=='none':
        prior=pd.read_parquet(PROJECT/'_artifacts-leads-no-blacklists'/f'engine-equity-off-{period}-{label}.parquet').equity
        assert eq.index.equals(prior.index)
        error=float((eq-prior).abs().max())
        parity_rows.append({'period':period,'candidate':label,'max_absolute_equity_difference':error})
        pd.DataFrame(parity_rows).to_csv(OUT/'control-parity.csv',index=False)
        assert error<0.01, f'NB18 control drift: {period}/{label}: {error}'
    for record in SCREEN_LOG: record.update(period=period,candidate=label,screen=screen)
    for record in CYCLE_LOG: record.update(period=period,candidate=label,screen=screen)
    decision_rows.extend(SCREEN_LOG);cycle_rows.extend(CYCLE_LOG)
    pd.DataFrame(decision_rows).to_csv(OUT/'screen-decisions.csv',index=False)
    pd.DataFrame(cycle_rows).to_csv(OUT/'cycle-diagnostics.csv',index=False)
    del st""",
)
code = code.replace("started = time.monotonic()", "parity_rows=[];decision_rows=[];cycle_rows=[]\nstarted = time.monotonic()")
cells.append(n.v4.new_code_cell(code))
cells.append(n.v4.new_markdown_cell("""## Independent A0b

Keep all NAV rows for valuation. Apply screen rejection only to the existing return-gate field, forcing it below the eligibility threshold; do not remove price rows or freeze rejected holdings. All other A0b accounting is unchanged."""))
cells.append(n.v4.new_code_cell("""from ic_research import ResearchConfig
from stable_profit import simulate_stable_policy
features=pd.read_parquet(PROJECT/'_artifacts-rewrite/features.parquet')
observations=pd.read_parquet(PROJECT/'_artifacts-rewrite/observations.parquet')
features.date=pd.to_datetime(features.date).dt.normalize();features.address=features.address.str.lower()
observations.timestamp=pd.to_datetime(observations.timestamp);observations.address=observations.address.str.lower()
A0B_PERIODS={'hyper_ai':('2026-01-01','2026-07-08'),'full':('2025-09-13','2026-09-12')}
for period,(start,end) in A0B_PERIODS.items():
    for screen in ('none','daily','weekly'):
        f=features[features.date.between(start,end)&features.address.isin(off_addresses)].copy()
        o=observations[observations.timestamp.dt.normalize().between(start,end)&observations.address.isin(off_addresses)].copy()
        if screen!='none':
            flags=SCREEN_FRAME[['date','address',screen+'_known',screen+'_pass']]
            f=f.merge(flags,on=['date','address'],how='left',validate='one_to_one')
            rejected=f[screen+'_pass'].eq(False)
            f.loc[rejected,'incumbent_return_gate']=-np.inf
        eq,tr,pool=simulate_stable_policy(f,o,policy_name='A0b',config=ResearchConfig(),max_positions=6)
        curve=pd.Series(eq.equity.to_numpy(),index=pd.to_datetime(eq.date),name='equity')
        curve.to_frame().to_parquet(OUT/f'curve-{period}-A0b-{screen}.parquet')
        eq.to_parquet(OUT/f'a0b-equity-{period}-{screen}.parquet',index=False)
        tr.to_parquet(OUT/f'a0b-trades-{period}-{screen}.parquet',index=False)
        pool.to_parquet(OUT/f'a0b-pool-{period}-{screen}.parquet',index=False)
        if screen=='none':
            old=pd.read_parquet(PROJECT/'_artifacts-leads-no-blacklists'/f'a0b-equity-off-{period}.parquet')
            assert pd.DatetimeIndex(old.date).equals(curve.index)
            error=float(np.max(np.abs(old.equity.to_numpy()-curve.to_numpy())))
            parity_rows.append({'period':period,'candidate':'A0b','max_absolute_equity_difference':error})
            assert error<.01,error
        cycle_rows.extend([{'date':r.date,'period':period,'candidate':'A0b','screen':screen,'invested_fraction':1-r.cash/r.equity,'positions':r.n_positions} for r in eq.itertuples()])
pd.DataFrame(parity_rows).to_csv(OUT/'control-parity.csv',index=False)
pd.DataFrame(cycle_rows).to_csv(OUT/'cycle-diagnostics.csv',index=False)
display(pd.DataFrame(parity_rows))
"""))
cells.append(n.v4.new_markdown_cell("## Equity curves, allocation and robustness\n\nBoth periods use the same two-day comparison marks across all candidates. Report cash exposure, selection coverage, actual vault P&L and market context rather than treating fewer losing picks as sufficient evidence."))
cells.append(n.v4.new_code_cell("from nb20_stability_screens import report\nresults, changes = report(PROJECT)"))
nb = n.v4.new_notebook(cells=cells, metadata=copy.deepcopy(src.metadata))
n.write(nb, p / "20-research-stability-screen-portfolios.ipynb")
