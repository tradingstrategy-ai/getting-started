"""Assemble the reviewed NB11 research notebook without changing NB10."""

import sys
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parent

HEADER = """# Experiment 11 — risk estimation, weighting and position sizing

Based on [experiment 10](10-research-portfolio-snapshots.ipynb) and the [reviewed plan](11-weighting-sizing-plan.md), co-designed with Claude CLI fable 5.1.

## Goal and method

Improve weighting and sizing while keeping the selected vaults fixed. Determine whether inverse-variance performance comes from its risk horizon, strength of the allocation preference, shrinkage towards a peer prior, score transformation or subsequent entry constraints. Seek a sensible parameter neighbourhood rather than one best historical cell. Freeze six-vault **focal_four** and **v11** baskets, their eligibility, missing-score tiers and tie-breaking.

Compare risk windows 45/90/180 days, allocation powers 1/1.5/2, fixed kappa 30 versus inherited L/3, raw and regularised risk, bounded inverse-risk scores, median/maximum multi-window forecasts and matched calendar-log/gap-scaled sparse estimators. Risk is calculated on the full eligible universe before selecting baskets. Only NAV is causally forward-filled; actual updates and permission/capacity clocks remain separate. Young/partial histories use the declared peer prior and whole-basket equal fallback, without changing selection.

## Calendar and scope

**2026-01-01 → 2026-10-05, exclusive end, naive UTC**. Four-day cadence gives **70 origins**. Features end at T−1; all 2025 and earlier warmup is retained. Fixed units use inherited anchor NAV(T−1) and terminal NAV(T−1+h). This convention ensures NB10 parity; it is not an executable claim of filling yesterday’s NAV at today’s decision. Mature counts are **68/62/47** for 7/30/90 days, with 2/8/23 pending. Targets require vault-specific terminal support; unresolved holdings stay unresolved.

The **18-policy smoke** is a correctness checkpoint over the full calendar at 30 days. After it passes, the **40-policy main study** reuses those allocations and evaluates all three horizons: 2,800 allocations and 8,400 scheduled outcomes. Twelve sensitivities and eight cap-aware policies are registered, not executed. Historical outcomes are descriptive: primary 30-day inference has at most eight complete blocks, below the required ten. Overlapping snapshots must not be compounded into strategy CAGR.

## Results status

Execution and reference checks below establish the completed scope. Written conclusions appear in [findings](11-weighting-sizing-findings.md) after the main run.
"""


def build(smoke=False):
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md(HEADER),
        code("""from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Markdown
ROOT=Path.cwd()
if not (ROOT/'sizing_study_design.py').exists():
    ROOT=ROOT/'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0,str(ROOT))
from sizing_study_design import smoke_registry, main_registry, followups
from sizing_study_data import read_inputs, stage_folder, freeze_baskets, build_risk
from sizing_study_analysis import execute
from sizing_study_audit import fixtures, audit
from sizing_study_report import render_smoke, render_main, write_findings
from score_matrix_visualisation import compact_output
pd.options.display.max_colwidth=None
"""),
        md("""## Independent mathematical fixtures — 2026-01-01 → 2026-10-05; 30-day horizon; smoke

Check sparse/partial/flat risk, ddof1, priors, shrinkage, log-space powers, gap drift, fixed-unit paths, unresolved bounds and exact registry counts independently before inspecting returns.
"""),
        code("""fixture_results=fixtures()
display(fixture_results)
"""),
        md("""## Pinned inputs and full warmup — 2026-01-01 → 2026-10-05; 30-day horizon; smoke

Verify source archives, metadata, 139 recipes, NB09 features and NB10 component/code hashes. Freeze both baskets once; do not use future availability to alter selection. Earlier generations are read-only.
"""),
        code("""with compact_output('Read-only inputs and causal risk; estimated one–two minutes'):
    data=read_inputs()
    baskets=freeze_baskets(data)
    risk,support=build_risk(data)
display(pd.DataFrame([{'Origins':len(data['origins']),'Recorded NAV start':str(data['daily'].date.min()),'Frozen recipes':len(data['registry']),'Unique frozen baskets':baskets.groupby(['origin_at','selector']).ngroups,'Unique risk estimates':len(risk)}]))
"""),
        md("""## Full-calendar smoke checkpoint — 2026-01-01 → 2026-10-05; 30-day horizon; smoke

Run all 18 registered methods at 70 dates, then compare exact saved controls and per-vault ledgers. Advance based on correctness rather than profitability. A separate chart shows the earliest mechanically cap-active example.
"""),
        code("""smoke_policies=smoke_registry()
stage_folder(data,smoke_policies,'smoke')
with compact_output('18-policy full-calendar smoke; estimated under two minutes'):
    smoke=execute(data,baskets,risk,smoke_policies,[30])
    smoke_audit=audit(data,smoke,smoke_policies,[30])
smoke_figures=render_smoke(data,smoke,smoke_audit)
display(pd.DataFrame([{'Smoke checks passed':int(smoke_audit.passed.sum()),'Numerical fixtures passed':int(fixture_results.passed.sum()),'Smoke allocations':18*70,'Smoke target rows':len(smoke['outcomes'])}]))
"""),
    ]
    if not smoke:
        cells += [
            md("""## Complete main matrix — 2026-01-01 → 2026-10-05; 7/30/90-day horizons; main

Reuse all 18 smoke allocations and add the 22 remaining registered methods. Allocate once per origin/policy; only future valuation changes with horizon. Save pending dates, terminal censoring, calibration and matched effects.
"""),
            code("""policies=main_registry()
stage_folder(data,policies,'main')
with compact_output('40 policies,70origins,three horizons; estimated two–five minutes'):
    result=execute(data,baskets,risk,policies,[7,30,90],reuse=smoke)
    main_audit=audit(data,result,policies,[7,30,90],reuse=smoke)
    support.to_parquet(data['artifact']/'risk_pool_support.parquet',index=False)
display(pd.DataFrame([{'Policies':len(policies),'Origin-policy allocations':40*70,'Scheduled outcomes':len(result['outcomes']),'Main audit checks passed':int(main_audit.passed.sum()),'Execution seconds':data['execution_seconds']}]))
"""),
            md("""## Results and mechanisms — 2026-01-01 → 2026-10-05; 30-day primary horizon; main

Every table and figure has a separate heading and explanation. Main displays use 30 days; explicitly titled 7/90-day tables are secondary. Colour scales match across comparable cells, and pending/unsupported cells remain grey.
"""),
            code("""figures=render_main(data,result,main_audit,policies,support)
"""),
            md("""## Verdict and registered next work — 2026-01-01 → 2026-10-05; 30-day horizon; main

Write findings only after the 40-policy study and its exact control checks finish. No sensitivities or cap-aware follow-up optimisation are run. Results describe searched historical snapshots, not an executable production return.
"""),
            code("""findings_path=write_findings(data,result,main_audit)
display(Markdown(f'[Detailed findings]({findings_path.name})'))
display(pd.DataFrame([{'Main checks passed':int(main_audit.passed.sum()),'Separate main figures':len(figures),'Sensitivity policies not run':len(followups()['sensitivities']),'Cap-aware policies not run':len(followups()['cap_aware']),'Generation':data['fingerprint']}]))
"""),
        ]
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, ROOT / "11-research-weighting-sizing.ipynb")


if __name__ == "__main__":
    build(smoke="--smoke" in sys.argv)
