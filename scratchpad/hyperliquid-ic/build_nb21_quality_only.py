from pathlib import Path
import copy
import nbformat as n

p = Path(__file__).resolve().parent
src = n.read(p / "20-research-stability-screen-portfolios.ipynb", as_version=4)
nb = copy.deepcopy(src)
nb.cells[0].source = """# Variable-size portfolios with absolute quality floors

Based on `20-research-stability-screen-portfolios.ipynb`. Compare the original bounded portfolios with no six-position limit, 100% maximum portfolio weight and 100% of historical vault TVL as the capacity ceiling. Blacklists remain off. Position count can range from zero to the available universe: no quota, no fallback picks.

Unrestricted controls preserve relative filters. Daily/weekly quality arms remove relative filters and require known passing quality metrics. These arms use only absolute admission conditions plus operational checks. Existing inverse-variance sizing and long-history requirements remain unchanged, to isolate allocation policy. A young vault can pass quality floors yet receive no weight; that limitation is explicitly measured.

## Key new insights
Pending execution.

## Summary of results
Pending execution.

## Robustness of results
Pending execution."""
for c in nb.cells:
    if c.cell_type != "code":
        continue
    c.outputs = []
    c.execution_count = None
    c.source = c.source.replace("'_artifacts-stability-screens'", "'_artifacts-quality-only'").replace("id = '20-research-stability-screen-portfolios'", "id = '21-research-quality-only-portfolios'")
    if "SCREEN_LOG.append" in c.source:
        c.source = c.source.replace("if not candidates:", "if not candidates and ACTIVE_SCREEN == 'none':")
        c.source = c.source.replace("_pass=bool(_record.get(ACTIVE_SCREEN+'_pass',True)) if ACTIVE_SCREEN!='none' else True", "_pass=(_known and bool(_record.get(ACTIVE_SCREEN+'_pass',False))) if ACTIVE_SCREEN!='none' else True")
    if "def decide_trades(input):" in c.source:
        c.source = c.source.replace("'positions':len(list(portfolio.get_open_positions()))", "'positions':len(list(portfolio.get_open_positions())),\n        'max_weight':max([float(pos.get_value())/equity for pos in portfolio.get_open_positions()] or [0.]),\n        'effective_positions':1/sum((float(pos.get_value())/max(equity-portfolio.get_cash(),1e-9))**2 for pos in portfolio.get_open_positions()) if equity-portfolio.get_cash()>1e-6 else 0.")
    if "jobs = " in c.source:
        c.source = c.source.replace("    with contextlib.ExitStack() as stack:", "    allocation_overrides=dict(CONFIGS[label],max_assets_in_portfolio=len(off_addresses),max_concentration_pct=1.0,per_position_cap_of_pool_pct=1.0)\n    if screen!='none':\n        allocation_overrides.update(vol_matched_drop_count=0,stability_prefilter_signal='',stability_prefilter_fraction=0.0)\n    with contextlib.ExitStack() as stack:")
        c.source = c.source.replace("**CONFIGS[label])", "**allocation_overrides)")
        start = c.source.index("    if screen=='none':\n        prior=")
        end = c.source.index("    for record in SCREEN_LOG:", start)
        c.source = c.source[:start] + c.source[end:]
        # Run all labels explicitly to confirm floor-only configurations collapse to the same result.
    if "from stable_profit import simulate_stable_policy" in c.source:
        c.source = c.source.replace("rejected=f[screen+'_pass'].eq(False)", "rejected=~(f[screen+'_known'].eq(True)&f[screen+'_pass'].eq(True))")
        c.source = c.source.replace("config=ResearchConfig(),max_positions=6", "config=ResearchConfig(max_weight=1.0,max_tvl_fraction=1.0),max_positions=len(off_addresses)")
        start = c.source.index("        if screen=='none':\n            old=")
        end = c.source.index("        cycle_rows.extend", start)
        c.source = c.source[:start] + c.source[end:]
        c.source = c.source.replace("pd.DataFrame(parity_rows).to_csv(OUT/'control-parity.csv',index=False)", "# Source-bounded controls are loaded and compared in the final report.")
    if "from nb20_stability_screens import report" in c.source:
        c.source = "from nb21_quality_report import report\nresults, comparison=report(PROJECT)"
for c in nb.cells:
    if c.cell_type == "markdown" and c is not nb.cells[0]:
        c.source = c.source.replace("A fresh unchanged control must reproduce NB18 before its screened companions are interpreted.", "Bounded NB20 controls are reused only after input hashes are verified. The unrestricted control changes allocation limits, so it is not expected to reproduce NB20.")
# Assert saved NB20 source inputs unchanged before expensive runs.
nb.cells[11].source = """import hashlib,json
for item in json.loads((PROJECT/'_artifacts-stability-screens/input-manifest.json').read_text()):
    with open(item['path'],'rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256'],item['path']
""" + nb.cells[11].source
nb.cells.insert(len(nb.cells) - 1, n.v4.new_markdown_cell("## Largest-contributor sensitivity\n\nTwo extra unrestricted-anchor reruns exclude intothecryptoverse.com from inception. This is a diagnostic counterfactual, not an added blacklist."))
nb.cells.insert(len(nb.cells) - 1, n.v4.new_code_cell((p / "nb21_leave_one_out_cell.py").read_text()))
n.write(nb, p / "21-research-quality-only-portfolios.ipynb")
