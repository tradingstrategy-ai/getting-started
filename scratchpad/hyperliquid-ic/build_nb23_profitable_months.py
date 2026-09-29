"""Build the next fixed profitable-month experiment from the NB22 engine."""

from pathlib import Path
import copy
import nbformat as n

p = Path(__file__).resolve().parent
parent = n.read(p / "22-research-allocation-decomposition.ipynb", as_version=4)
cells = [n.v4.new_markdown_cell("# Profitable-month selection variants\n\nBased on `22-research-allocation-decomposition.ipynb`. Four monthly scores, two lookbacks, both periods, equal-profit and fee-corrected anchor controls. Findings pending execution.")]
for i in range(1, 11):
    c = copy.deepcopy(parent.cells[i])
    c.outputs = []
    c.execution_count = None
    c.source = c.source.replace("id = '22-research-allocation-decomposition'", "id = '23-research-profitable-months'").replace("OUT = PROJECT / '_artifacts-allocation-decomposition'", "OUT = PROJECT / '_artifacts-profitable-months'")
    if i == 4:
        start = c.source.index("import shutil\nSNAPSHOT=")
        end = c.source.index("META_PATH=", start)
        c.source = c.source[:start] + "SNAPSHOT=PROJECT/'_artifacts-allocation-decomposition/inputs'\n" + c.source[end:]
    if i == 8:
        old = """        gate_value = indicators.get_indicator_value('return_gate', pair=pair)
        if gate_value is None or gate_value != gate_value or gate_value <= gate_threshold:
            continue"""
        new = """        gate_value = indicators.get_indicator_value('return_gate', pair=pair)
        if MONTH_RULE == 'anchor' and (gate_value is None or gate_value != gate_value or gate_value <= gate_threshold):
            continue"""
        assert old in c.source
        c.source = c.source.replace(old, new)
        old = "        scored = composite_signal is not None and composite_signal == composite_signal"
        new = """        if MONTH_RULE != 'anchor':
            record = MONTH_LOOKUP.get((pd.Timestamp(timestamp).normalize(),str(pair.pool_address).lower(),MONTH_LOOKBACK))
            monthly_score = (1.0 if record and record['growth'] > 0 else 0.0) if MONTH_RULE == 'equal_profit' else (record.get(MONTH_RULE,0.0) if record else 0.0)
            MONTH_LOG.append({'date':timestamp,'address':str(pair.pool_address).lower(),'score':monthly_score,**(record or {})})
            if monthly_score <= 0:
                continue
            composite_signal = monthly_score
        scored = composite_signal is not None and composite_signal == composite_signal"""
        assert old in c.source
        c.source = c.source.replace(old, new)
        c.source = c.source.replace("if not candidates and ACTIVE_SCREEN == 'none':", "if not candidates and ACTIVE_SCREEN == 'none' and MONTH_RULE == 'anchor':")
        old = '            trade.planned_price = trade.planned_mid_price * (1.0 - trade.other_data["backtest_vault_redemption_fee"])'
        assert old in c.source
        c.source = c.source.replace(old, "            set_single_redemption_fee(trade, input.pricing_model, timestamp)")
    cells.append(c)
cells.append(n.v4.new_code_cell("""from nb23_profitable_months import verify, prepare, run_all, report, set_single_redemption_fee
verify()
MONTH_RULE='anchor';MONTH_LOOKBACK=6;MONTH_LOOKUP={};MONTH_LOG=[]
SCREEN_LOOKUP={};SCREEN_LOG=[];ACTIVE_SCREEN='none';BLACKLIST_MODE='off'
strategy_universe=UNIVERSES['off']
CYCLE_LOG=[]
old_decide=decide_trades
def decide_trades(input):
    portfolio=input.state.portfolio;equity=portfolio.get_total_equity()
    values=[float(p.get_value()) for p in portfolio.get_open_positions()]
    CYCLE_LOG.append({'date':input.timestamp,'invested':sum(values)/equity if equity else 0.,'positions':len(values),'max_weight':max(values+[0.])/equity if equity else 0.})
    return old_decide(input)
WINDOWS={'hyper_ai':(datetime.datetime(2026,1,1),datetime.datetime(2026,7,10)), 'full':(datetime.datetime(2025,8,1),datetime.datetime(2026,9,9))}
panel=prepare(globals())
"""))
cells.append(n.v4.new_code_cell("run_all(globals())"))
cells.append(n.v4.new_code_cell("findings=report(globals())"))
n.write(n.v4.new_notebook(cells=cells, metadata=copy.deepcopy(parent.metadata)), p / "23-research-profitable-months.ipynb")
