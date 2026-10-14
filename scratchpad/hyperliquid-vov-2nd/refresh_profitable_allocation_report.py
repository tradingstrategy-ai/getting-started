"""Refresh NB14 presentation from verified saved engine results without new trades."""

from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent


def build():
    main = nbformat.read(ROOT / "14-backtest-profitable-allocation.ipynb", as_version=4)
    folder = Path(main.metadata["nb14"]["artifact_generation"])
    code = nbformat.v4.new_code_cell
    cells = [
        code(f"""from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
ROOT=Path({str(ROOT)!r})
sys.path.insert(0,str(ROOT))
from profitable_allocation import ARMS,PERIODS,FEATURES,analyse_run,raw_history
from long_candidate_backtest import initialise as legacy_initialise
from profitable_allocation_report import report
from score_matrix_visualisation import compact_output
folder=Path({str(folder)!r})
manifest=json.loads((folder/'manifest.json').read_text())
assert hashlib.sha256((ROOT/'profitable_allocation.py').read_bytes()).hexdigest()==manifest['identity']['code']['profitable_allocation.py']
"""),
        code("""with compact_output('Reload verified pinned data and ten saved states; no new engine runs'):
    data,evaluator,_,_=legacy_initialise()
    data['artifact']=folder;data['manifest']=manifest;data['figures']=[]
    data['pricing_convention']=manifest['identity']['pricing']
    data['raw_history'],data['nav_history']=raw_history(data)
    evaluator.folder=folder/'engine'
    results=pd.read_csv(folder/'results.csv');sensitivity=pd.read_csv(folder/'freshness-sensitivity.csv')
    runs={};attribution={};absolute_weights={}
    weight=np.zeros(len(FEATURES));weight[0]=1
    for period,(start,end) in PERIODS.items():
        for arm in ARMS:
            tag=json.dumps(dict(w=list(weight.round(10)),start=str(start),end=str(end),n=6,sizing='inverse_variance',allocator='parent',source_control=False,calmar_cap=5.0,missing=True,profile=f"NB14-{arm}-{data['pricing_convention']}"),sort_keys=True)
            key=hashlib.sha256(tag.encode()).hexdigest()[:24]
            assert (evaluator.folder/f'{key}-state.json').exists()
            r=evaluator.run(weight,start,end,n=6,sizing='inverse_variance',missing=True,profile=f"NB14-{arm}-{data['pricing_convention']}",keep=True)
            _,vaults,w=analyse_run(data,r,arm,period)
            runs[(period,arm)]=r;attribution[(period,arm)]=vaults;absolute_weights[(period,arm)]=w
"""),
        code("""assert evaluator.engine_calls==0
assert len(runs)==10 and len(sensitivity)==4
"""),
        code("""findings=report(data,results,runs,attribution,absolute_weights,sensitivity)
"""),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
    nbformat.write(notebook, folder / "refresh-report.ipynb")
    return folder / "refresh-report.ipynb"


def apply():
    import hashlib, json

    path = ROOT / "14-backtest-profitable-allocation.ipynb"
    main = nbformat.read(path, as_version=4)
    folder = Path(main.metadata["nb14"]["artifact_generation"])
    rendered = nbformat.read(folder / "refresh-report.ipynb", as_version=4)
    assert all(c.execution_count is not None for c in rendered.cells)
    assert all(not any(o.output_type == "error" for o in c.get("outputs", [])) for c in rendered.cells)
    main.cells[-1].outputs = rendered.cells[-1].outputs
    main.cells[-1].execution_count = rendered.cells[-1].execution_count
    from profitable_allocation_report import verdict_excerpt

    for output in main.cells[-1].outputs:
        markdown = output.get("data", {}).get("text/markdown", "")
        if markdown.startswith("# Experiment 14 — profitable allocation findings"):
            output.data["text/markdown"] = verdict_excerpt(markdown)
    main.cells[0].source = (folder / "final-header.md").read_text()
    main.metadata["nb14"]["presentation_refreshed_from_saved_states"] = True
    nbformat.write(main, path)
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["final_presentation"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT / "profitable_allocation_report.py", Path(__file__)]}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))


if __name__ == "__main__":
    import sys

    apply() if "--apply" in sys.argv else print(build())
