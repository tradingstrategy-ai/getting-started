from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "30-research-rolling-typical-profitability.ipynb"


def md(s):
    return nbf.v4.new_markdown_cell(s.strip())


def code(s):
    return nbf.v4.new_code_cell(s.strip())


cells = [
    md("""
# NB30 — rolling typical profitability, corrected

Repairs the earlier NB30 diagnostic; no portfolio backtest. See the
[original plan](rolling-typical-profitability-plan-01.md) and [basket plan](steady-profit-basket-plan-01.md).
Prior evidence: NB09's failed frequency blend, NB20's failed hard screens, NB24's saturated monthly
scores, and NB25–29's unsuccessful raw-growth membership and risk-sizing experiments.

## Key new insights and what did we learn from this experiment?

The corrected run substantially weakens the incremental return claim: Q25_7_60 return IC is
0.089/0.123 at 30/60 days, but only 0.005/0.003 after growth, frequency and volatility controls.
Its top group loses 1.57%/2.96% on average despite outperforming the rest. The remaining lead is
mainly downside information, not demonstrated steady profitability. Median returns add little.
See [full corrected summary](summary-nb30-repaired-01.md). Earlier conclusions are superseded;
original outputs are preserved under the superseded-01 directory.

## Summary of results

Four h/W settings (7/30, 14/30, 7/60, 14/60), forward 30/60 days, daily decisions and separate risk
diagnostics. Young and weekly histories remain eligible; one-outcome estimates are identified.

## Robustness of results

Repeatedly researched dates, overlapping windows and retrospectively assembled universe; no independent
validation or portfolio CAGR claim. Forward path metrics require gaps at most seven days and still
miss intragap losses. Conditional ICs are descriptive feature-rank residual associations.
"""),
    code("""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
PROJECT=Path.cwd() if (Path.cwd()/'nb30_diagnostics.py').exists() else Path.cwd()/'scratchpad/hyperliquid-ic'
sys.path.insert(0,str(PROJECT))
from nb30_diagnostics import *
from test_nb30_diagnostics import run_checks
display(pd.DataFrame(run_checks()))
OUT=PROJECT/'_artifacts-rolling-typical-profitability'
OLD=PROJECT/'_artifacts-rolling-typical-profitability-superseded-01'
SOURCE=PROJECT/'_artifacts-rewrite'
OUT.mkdir(exist_ok=True)
sources=[SOURCE/'observations.parquet',SOURCE/'features.parquet',PROJECT/'nb30_diagnostics.py',PROJECT/'build_nb30_typical_profitability.py']
hashes={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
"""),
    md("""
## Timing and measurement contract

Rewrite date d uses information before midnight d+1. Relabel explicitly as decision T=d+1;
retain source_date for old/new joins. Original observation timestamps are preserved. Every feature
uses marks strictly before T. Labels start at that same last mark and exit at the last observed mark
at or before T+H, at most seven days old and strictly after T. These are observed-mark diagnostics,
not engine fills. No reused rewrite labels with independently chosen future entry marks.

Rolling endpoints in (T-W,T) contribute once, with the most recent start at/before endpoint-h,
at most seven days of start carry, using actual elapsed time. Starts can reach W+h+7 days back.
Risk uses irregular observed intervals. Sharpe-like has no hidden denominator floor and is missing
at zero volatility. Drawdown area carries through the final interval to T.
"""),
    code("""
raw=pd.read_parquet(SOURCE/'observations.parquet')
raw['timestamp']=pd.to_datetime(raw.timestamp)
raw['address']=raw.address.str.lower()
raw=raw.loc[raw.is_fresh & raw.share_price.gt(0) & np.isfinite(raw.share_price)].copy()
marks={a:last_mark_per_day(g) for a,g in raw.groupby('address')}
label_marks={a:g.sort_values('timestamp',kind='stable').drop_duplicates('timestamp',keep='last').set_index('timestamp') for a,g in raw.groupby('address')}
point=pd.read_parquet(SOURCE/'features.parquet',columns=['date','address','tvl_current','last_observation_ts','available_history_days','incumbent_return_gate'])
point['source_date']=pd.to_datetime(point.date).dt.normalize()
point=point.loc[point.source_date.between('2025-07-31','2026-09-08')].copy()
point['date']=point.source_date+pd.Timedelta(days=1)
point['address']=point.address.str.lower()
assert (pd.to_datetime(point.last_observation_ts)<point.date).all()
rows=[]
started=time.monotonic()
for number,(address,g) in enumerate(point.groupby('address')):
    for t in g.date:
        row=dict(address=address,date=t)
        for h,w in SPECS:
            row.update({f'{k}_{h}_{w}':v for k,v in rolling_row(marks[address],t,h,w).items()})
        for horizon in HORIZONS:
            row.update({f'forward_{k}_{horizon}':v for k,v in forward_row(label_marks[address],t,horizon).items()})
        rows.append(row)
    if number%50==0:
        elapsed=time.monotonic()-started
        print(f'{number+1}/{point.address.nunique()} vaults; estimated minutes remaining {elapsed/(number+1)*(point.address.nunique()-number-1)/60:.1f}',flush=True)
panel=point.merge(pd.DataFrame(rows),on=['date','address'],validate='one_to_one')
panel['opportunity']=panel.tvl_current.ge(7500) & panel.incumbent_return_gate.gt(-.16) & panel.last_mark_age_days_7_60.le(7)
panel['age_cohort']=pd.cut(panel.available_history_days,[-np.inf,30,90,np.inf],right=False,labels=['<30d','30-89d','>=90d'])
panel['cadence']=np.where(panel.median_mark_gap_days_7_60.gt(1.5),'sparse','dense')
for h,w in SPECS:
    ts=panel[f'last_observation_ts_{h}_{w}']
    assert (ts.isna() | ts.lt(panel.date)).all()
    for horizon in HORIZONS:
        assert (ts.isna() | panel[f'forward_entry_ts_{horizon}'].eq(ts)).all()
for horizon in HORIZONS:
    ex=panel[f'forward_exit_ts_{horizon}']
    assert (ex.isna() | (ex.gt(panel.date) & ex.le(panel.date+pd.Timedelta(days=horizon)))).all()
panel.to_parquet(OUT/'feature-label-panel.parquet',index=False)
opportunity=panel.loc[panel.opportunity].copy()
display(pd.DataFrame([dict(rows=len(panel),dates=panel.date.nunique(),vaults=panel.address.nunique(),opportunity_rows=len(opportunity),first_decision=panel.date.min(),last_decision=panel.date.max())]))
"""),
    md("""
## Coverage and label audit

Opportunity membership precedes labels. Missing M/Q does not remove an opportunity. Repaired
timestamps, entry conventions and ranking calculations all affect the before/after comparison.
"""),
    code("""
coverage=[]
for h,w in SPECS:
    s=f'{h}_{w}'
    for label,(col,hi) in score_columns(h,w).items():
        coverage.append(dict(score=f'{label}_{s}',opportunity_rows=len(opportunity),finite_rows=opportunity[col].notna().sum(),finite_vaults=opportunity.loc[opportunity[col].notna(),'address'].nunique(),one_event_rows=opportunity[f'unique_event_count_{s}'].eq(1).sum(),exact_m_q_share=opportunity[f'exact_median_equals_q25_{s}'].mean(),median_actual_span=opportunity[f'actual_span_median_{s}'].median()))
coverage=pd.DataFrame(coverage)
coverage.to_csv(OUT/'coverage.csv',index=False)
display(coverage)
label_coverage=[]
for h in HORIZONS:
    for target in ['return','drawdown','volatility','sharpe_like']:
        col=f'forward_{target}_{h}'
        valid=opportunity.loc[opportunity[col].notna()]
        label_coverage.append(dict(horizon=h,target=target,rows=len(valid),dates=valid.date.nunique(),unique_intervals=len(valid.drop_duplicates(['address',f'forward_entry_ts_{h}',f'forward_exit_ts_{h}']))))
pd.DataFrame(label_coverage).to_csv(OUT/'label-coverage.csv',index=False)
display(pd.DataFrame(label_coverage))
"""),
    md("""
## Corrected marginal rankings

Higher desirability has higher rank. Top weights sum to 20% of finite names with fractional ties;
the rest uses complementary weights. Mask labels after membership and divide by labelled weight
mass. Constant scores have no separation. Higher signed drawdown means shallower losses; lower
negative-return frequency and volatility are desirable. These group returns are not backtests.
"""),
    code("""
tables=[]
members=[]
for h,w in SPECS:
    for label,(col,hi) in score_columns(h,w).items():
        for horizon in HORIZONS:
            stats,member=marginal_stats(opportunity,f'{label}_{h}_{w}',col,hi,horizon)
            tables.append(stats)
            if horizon==30: members.append(member)
    print(f'Marginal statistics complete: h={h}, W={w}',flush=True)
marginal=pd.concat(tables,ignore_index=True)
marginal.to_csv(OUT/'marginal-date-statistics.csv',index=False)
pd.concat(members,ignore_index=True).to_parquet(OUT/'top-quintile-membership.parquet',index=False)
summary=marginal.groupby(['score','horizon','target']).agg(dates=('date','nunique'),rho_dates=('rho','count'),mean_rho=('rho','mean'),top=('top','mean'),rest=('rest','mean'),spread=('spread','mean'),top_coverage=('top_coverage','mean'),rest_coverage=('rest_coverage','mean')).reset_index()
summary.to_csv(OUT/'marginal-summary.csv',index=False)
display(summary.loc[summary.target.isin(['return','drawdown']) & summary.score.isin(['M_7_60','Q25_7_60','P_7_60','S_7_60','-V_7_60'])])
old=pd.read_csv(OLD/'marginal-summary.csv')
comparison=summary.merge(old[['score','horizon','target','mean_rho','top_minus_rest_return','top_minus_rest_drawdown']],on=['score','horizon','target'],suffixes=('_corrected','_old'))
comparison['old_spread']=np.where(comparison.target.eq('return'),comparison.top_minus_rest_return,comparison.top_minus_rest_drawdown)
comparison.to_csv(OUT/'before-after.csv',index=False)
"""),
    md("""
## Conditional and paired comparisons

Feature-only rank residuals; reject rank-deficient designs or numerical zero residuals. Both horizons
run. Paired comparisons share feature-complete rows before outcome-specific masking: no drawdown
coverage requirement on return comparisons. Descriptive calendar-block intervals use 60/90 days,
200 draws, seed 3030. Report effective blocks; these are not independent validation.
"""),
    code("""
conditional_rows=[]
paired_rows=[]
for setting in SPECS:
    for label in ['M','Q25']:
        for horizon in HORIZONS:
            conditional_rows.extend(residual_stats(opportunity,label,setting,horizon))
    paired_rows.extend(paired_stats(opportunity,setting))
    print(f'Conditional and paired comparisons complete: {setting}',flush=True)
conditional=pd.DataFrame(conditional_rows)
conditional.to_csv(OUT/'conditional-residual-statistics.csv',index=False)
cs=conditional.groupby(['score','horizon','target','view']).agg(rho_dates=('rho','count'),mean_rho=('rho','mean')).reset_index()
cs.to_csv(OUT/'conditional-summary.csv',index=False)
display(cs.loc[cs.score.eq('Q25_7_60')])
paired=pd.DataFrame(paired_rows)
paired.to_csv(OUT/'paired-date-statistics.csv',index=False)
contrasts=[]
for key,g in paired.groupby(['setting','candidate','comparator','horizon','target']):
    for metric in ['rho_difference','spread_difference']:
        values=g.set_index('date')[metric]
        for block in [60,90]:
            low,high=bootstrap(values,block)
            contrasts.append(dict(zip(['setting','candidate','comparator','horizon','target'],key),metric=metric,block_days=block,dates=values.notna().sum(),mean_difference=values.mean(),bootstrap_q025=low,bootstrap_q975=high,calendar_blocks=(values.index.max()-values.index.min()).days/block))
contrasts=pd.DataFrame(contrasts)
contrasts.to_csv(OUT/'paired-block-contrasts.csv',index=False)
display(contrasts.loc[contrasts.setting.eq('7_60') & contrasts.candidate.eq('Q25') & contrasts.target.eq('return') & contrasts.block_days.eq(60)])
"""),
    md("""
## Cohorts, reduced-overlap checks and reference examples

M and Q cohort ICs average dates rather than pool rows. Non-overlapping decision dates use one fixed
H-day offset from the first scored date; no independent holdout. Reference plots are illustrative.
"""),
    code("""
cohorts=[]
for setting in SPECS:
    for label in ['M','Q25']:
        col,hi=score_columns(*setting)[label]
        for key,g in opportunity.groupby(['age_cohort','cadence'],observed=True):
            for horizon in HORIZONS:
                rhos=pd.Series([correlation(d[col],d[f'forward_return_{horizon}']) for _,d in g.groupby('date')]).dropna()
                cohorts.append(dict(setting=str(setting),score=label,age=str(key[0]),cadence=key[1],horizon=horizon,rows=len(g),scored_dates=len(rhos),mean_rho=rhos.mean(),one_event_share=g[f'unique_event_count_{setting[0]}_{setting[1]}'].eq(1).mean()))
pd.DataFrame(cohorts).to_csv(OUT/'cohort-summary.csv',index=False)
robust=[]
for key,g in marginal.groupby(['score','horizon','target']):
    good=g.dropna(subset=['rho'])
    if good.empty: continue
    offset=(pd.to_datetime(good.date)-pd.to_datetime(good.date).min()).dt.days
    nonoverlap=good.loc[offset.mod(key[1]).eq(0)]
    robust.append(dict(score=key[0],horizon=key[1],target=key[2],dates=len(nonoverlap),mean_rho=nonoverlap.rho.mean(),mean_spread=nonoverlap.spread.mean()))
pd.DataFrame(robust).to_csv(OUT/'nonoverlap-summary.csv',index=False)
references={'StratWise':'0x0ff219ac20596b457558341bc410bc7a08a1394c','Systemic L/S Grids':'0x07fd993f0fa3a185f7207adccd29f7a87404689d'}
fig,axes=plt.subplots(2,1,figsize=(12,7))
reference_rows=[]
for ax,(name,address) in zip(axes,references.items()):
    d=panel.loc[panel.address.eq(address)].sort_values('date')
    for prefix,label in [('median_log_rate','M'),('lower_quartile_log_rate','Q25')]:
        ax.plot(d.date,100*d[f'{prefix}_7_60'],label=label)
    ax.axhline(0,color='grey'); ax.set_title(name); ax.set_ylabel('Daily log growth (%)'); ax.legend()
    reference_rows.append(dict(reference=name,address=address,opportunity_rows=int(d.opportunity.sum()),q_positive_rows=int((d.opportunity & d.lower_quartile_log_rate_7_60.gt(0)).sum()),labelled_30_rows=int((d.opportunity & d.forward_return_30.notna()).sum())))
fig.tight_layout(); fig.savefig(OUT/'reference-rolling-features.png',dpi=150); display(fig)
pd.DataFrame(reference_rows).to_csv(OUT/'reference-vaults.csv',index=False)
display(pd.DataFrame(reference_rows))
q=opportunity.lower_quartile_log_rate_7_60
p=opportunity.positive_window_share_7_60
both=q.notna() & p.notna()
overlap=pd.DataFrame([dict(finite_rows=int(both.sum()),q_positive_fraction=q[both].gt(0).mean(),q_p_floor_agreement=q[both].gt(0).eq(p[both].ge(.75)).mean())])
overlap.to_csv(OUT/'q-frequency-overlap.csv',index=False)
display(overlap)
"""),
    md("""
## Corrected findings and remaining limits

Before/after changes include original timestamps, entry labels, ranking repairs and removal of the
hidden Sharpe denominator floor. The 7/60 candidate was selected after earlier inspection.
Coverage, both conditional horizons, Q cohorts, paired outcome-specific contrasts, calendar-block
intervals and reduced-overlap checks run here. Still omitted from the original broad plan:
matched losing-vault case studies, individual-vault influence sensitivity, period-stratified IC
tables and conditional feature-complete comparator coverage. No portfolio validation is claimed.
"""),
    code("""
report=summary.loc[summary.score.isin(['M_7_60','Q25_7_60','P_7_60','S_7_60','-V_7_60']) & summary.target.isin(['return','drawdown'])]
display(report)
lines=['# NB30 corrected results','','Supersedes original NB30. No portfolio backtest or CAGR claim.','',report.to_markdown(index=False),'','## Conditional Q25_7_60 results','',cs.loc[cs.score.eq('Q25_7_60')].to_markdown(index=False)]
(OUT/'results.md').write_text('\\n'.join(lines))
manifest=dict(status='executed_corrected_diagnostic',source_hashes=hashes,settings=SPECS,horizons=HORIZONS,decision_contract='T=source_date+1; original timestamps strictly before T',label_contract='last pre-T mark to last at/before T+H; endpoint carry <=7d; path gap <=7d',superseded=OLD.name,panel_rows=len(panel),opportunity_rows=len(opportunity),outputs=sorted(p.name for p in OUT.iterdir() if p.is_file()))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,default=str))
"""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
nbf.write(nb, NOTEBOOK)
print(NOTEBOOK)
