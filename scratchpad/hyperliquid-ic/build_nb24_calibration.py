"""Build the calibration notebook from the corrected NB23 engine."""

from pathlib import Path
import copy
import nbformat as n

p = Path(__file__).resolve().parent
parent = n.read(p / "23-research-profitable-months.ipynb", as_version=4)
cells = [n.v4.new_markdown_cell("# Monthly stability calibration\n\nBased on corrected notebook 23. Forty-eight settings, training-only shortlist, fixed-allocation backtests. Results pending execution.")]
for i in range(1, 11):
    c = copy.deepcopy(parent.cells[i])
    c.outputs = []
    c.execution_count = None
    c.source = c.source.replace("id = '23-research-profitable-months'", "id = '24-research-monthly-calibration'").replace("OUT = PROJECT / '_artifacts-profitable-months'", "OUT = PROJECT / '_artifacts-monthly-calibration'")
    if i == 8:
        a = c.source.index("        if MONTH_RULE == 'anchor' and (gate_value")
        b = c.source.index("        _addr=", a)
        c.source = c.source[:a] + """        if CAL_RULE == 'anchor':
            if gate_value is None or gate_value != gate_value or gate_value <= gate_threshold:
                continue
        else:
            common=CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),3))
            if common is None or common['gate'] <= 0:
                continue
""" + c.source[b:]
        a = c.source.index("        if MONTH_RULE != 'anchor':")
        b = c.source.index("        scored =", a)
        c.source = c.source[:a] + """        if CAL_RULE not in ('anchor','matched_original'):
            record=CAL_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),int(CAL_CONFIG['lookback'])))
            composite_signal=(record['p']**CAL_CONFIG['alpha'] * min(record['gain']/CAL_CONFIG['tau'],1.) * math.exp(-CAL_CONFIG['penalty']*record['q']-CAL_CONFIG['severity']*record['downside']/CAL_CONFIG['tau'])) if record else 0.
""" + c.source[b:]
        c.source = c.source.replace("and MONTH_RULE == 'anchor':", "and CAL_RULE == 'anchor':")
        marker = "    # Sizing. Selection above ranked on the composite score;"
        c.source = c.source.replace(marker, "    CAL_LOG.extend({'date':timestamp,'address':str(pair.pool_address).lower(),'score':signal} for _,pair,signal in selected)\n\n" + marker)
    cells.append(c)
cells.append(n.v4.new_code_cell("""from nb24_monthly_calibration import check, panel, evaluate, run_backtests, report, set_single_redemption_fee
check()
CAL_RULE='anchor';CAL_CONFIG=None;CAL_LOOKUP={};CAL_LOG=[]
MONTH_RULE='anchor';SCREEN_LOOKUP={};SCREEN_LOG=[];ACTIVE_SCREEN='none';BLACKLIST_MODE='off'
strategy_universe=UNIVERSES['off'];CYCLE_LOG=[]
old_decide=decide_trades
def decide_trades(input):
    portfolio=input.state.portfolio;equity=portfolio.get_total_equity()
    values=[float(p.get_value()) for p in portfolio.get_open_positions()]
    CYCLE_LOG.append({'date':input.timestamp,'invested':sum(values)/equity if equity else 0.,'positions':len(values),'max_weight':max(values+[0.])/equity if equity else 0.})
    return old_decide(input)
features=panel(globals())
"""))
cells.append(n.v4.new_code_cell("ranking_results=evaluate(globals())"))
cells.append(n.v4.new_code_cell("run_backtests(globals())"))
cells.append(n.v4.new_code_cell("findings=report(globals())"))
n.write(n.v4.new_notebook(cells=cells, metadata=copy.deepcopy(parent.metadata)), p / "24-research-monthly-calibration.ipynb")
