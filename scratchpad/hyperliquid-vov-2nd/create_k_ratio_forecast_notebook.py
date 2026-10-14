"""Build the bounded experiment-09 feature research notebook."""

from pathlib import Path

import nbformat
from k_ratio_features import TARGETS, HORIZONS

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "09-research-k-ratio-feature-forecasts.ipynb"


def build():
    """Keep narrative, descriptions and outputs separate and reproducible."""
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell
    cells = [
        md("""# Experiment 09 — K-ratio features and future vault performance

Based on [experiment 05's causal feature diagnostics](05-opt-score-calibration-selection-cash.ipynb), the [reviewed implementation plan](09-k-ratio-feature-forecast-plan.md), and the [post-review amendment](09-k-ratio-feature-forecast-amendment.md). This notebook is corrected and rerun in place; the original run is archived.

## Goal

Measure the prediction power of **individual historical vault features**, adding **K-ratio** to the existing CAGR, Sharpe, Sortino, maximum drawdown and Calmar inputs. Predict future **CAGR, Sharpe and K-ratio** over **7, 30 and 90 days**, using four-day forecast origins. Support **missing=True** so a missing long lookback does not exclude a vault with usable shorter inputs. This is feature forecasting, not composite scoring or portfolio weighting.

## Method

Use pinned repaired data, daily share NAV with causal forward filling and strictly matured future labels. Add six K inputs: **30, 60, 90, 180 and 360 days (one year), plus max (all recorded history)**. Max starts at each vault's first actual positive daily NAV and ends at T−1; it carries the latest known NAV over missing calendar days, requires at least three fitted points, and never compresses gaps or backfills before the first observation. Its duration varies by vault/date and is not certified inception. Forecasts use only history through T−1, with no additional gap; future outcomes never extend a feature window. The loader includes the earliest actual archive date, even if it precedes the usual 731-day buffer. Missing=True preserves shorter-window forecasts when year/max is unavailable.

Use exact lookback log returns for CAGR inputs, robust training-only asinh/standardisation with training-range/±5z input bounds and training 0.5%–99.5% prediction bounds. Sharpe uses scaled pseudo-Huber loss; K uses asinh targets. Compare fixed monthly forecasts with and without K on identical vault/date rows, with shared availability controls, constant/zero/persistence baselines, compact and path-decomposition companions. Retain four-window K ablations, adding year only, max only, and both with the same controls. Model preprocessing is training-only. K uses ordinary intercept OLS on all L+1 daily wealth points, including the anchor, and sqrt(365)/(L+1); undefined ratios stay missing. Report 2026 by default, with earlier-history diagnostics separately. These dates were previously researched; results are not an untouched holdout.

## Key new insights

Measured findings are generated after execution from the supported comparisons below. The original pre-review conclusions are not inherited.

## Summary

The notebook covers all nine target/horizon combinations, preserves partial-history forecasts with missing=True, and retains actual observation masks alongside carried daily prices. Future labels are censored after the last actual vault observation. Horizon support is measured in the tables below. Separate linked notebooks hold the complete K scatter catalogue.

## Robustness

Independent metric and target checks, experiment-05 compatibility, paired model ablations, quarter/cohort/phase/delay sensitivities, non-overlapping origins, longer blocks and influential-vault checks are included. Current-snapshot selection and limited daily history constrain conclusions. No strategy rules are changed.

## Interpretation

The support audit controls what can be inferred. A relationship between past and future K may reflect persistent smoothness, low activity or reporting precision; it does not itself show prediction of profitable returns. The measured training and calendar-block support determines which horizons support forecast comparisons.
"""),
        code("""from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent if '__file__' in globals() else Path.cwd()
if not (ROOT/'k_ratio_features.py').exists():
    ROOT=Path('/Users/moo/code/getting-started/scratchpad/hyperliquid-vov-2nd')
sys.path.insert(0,str(ROOT))
import json
import numpy as np
import pandas as pd
from IPython.display import display, Markdown
from score_matrix_visualisation import compact_output
from k_ratio_features import *
from k_ratio_forecast_audit import audit_dataset, compatibility_ic
from k_ratio_forecast_models import run_models
from k_ratio_forecast_statistics import analyse
from k_ratio_forecast_extensions import run_extensions
from k_ratio_forecast_feedback import run_feedback
from k_ratio_forecast_report import table, show, report_overview, robustness_report, ic_map, forecast_scatter, feature_scatter, write_catalogue, write_findings, freeze_design, feedback_report
"""),
        md("""## Pinned inputs and genuine daily observations

Rebuild all metric features from actual positive NAV observations with causal forward filling on the daily grid. Cached earlier files provide vault identities and a separate source-compatibility audit, never composite-score predictors. Actual unchanged marks remain observations; synthetic carry-forward is not an actual daily mark."""),
        code("""with compact_output('Audited feature and future-label dataset — estimated 1 minute'):
    data=prepare_data()
table(pd.DataFrame([{'Vaults':data['manifest']['vaults'],'Existing primary features':len(EXISTING),'New K windows':len(K_ALL),'Forecast cadence (days)':4,'Horizons (days)':'7 / 30 / 90','Missing policy':'True (partial histories)','Publication clock':'Unknown; observation-time replay'}]),
      'Research inputs','The 45 existing features use nine lookbacks. Main K inputs are 30/60/90/180/360 days and max recorded history; the inventory includes other diagnostic windows. Five 45-day compatibility features remain audit-only. No new remote archive is fetched.')
"""),
        md("""## Numerical and source compatibility checks

Check K against independently solved OLS, its signed-R² identity, first-return influence, scale/sign/order behaviour and missing/flat paths. Recompute forward-filled targets independently, and reproduce experiment 05's source feature values and 14/30/60-day feature IC on shared origins."""),
        code("""with compact_output('Independent metrics and experiment-05 compatibility audits — estimated 1 minute'):
    audit=audit_dataset(data)
    compatibility=compatibility_ic(data)
table(audit,'Numerical and genuine-label checks','Every boolean check must pass. Source cells are compared with the frozen 05 feature cache; sampled supported labels are recomputed through independent paths.')
table(compatibility,'Reproducing the earlier feature analysis','These old 14/30/60-day associations verify compatibility only. The experiment-09 forecast horizons remain 7/30/90 days.')
"""),
        md("""## Chronological models and target support

Refit monthly using strictly matured labels; predict every four days. Ridge alpha is 10; raw Sharpe uses scaled pseudo-Huber delta 1.35, with one total weight per origin. Training-only robust adapters preserve NaN, bound inputs and level predictions, and abstain without usable performance inputs. Complete-case uses 30/60/90 days. Ranking companions use causal input percentiles and matured rank targets with IC only; activity and compact-control arms are fixed sensitivities."""),
        code("""with compact_output('Fixed chronological feature forecasts — estimated 3–6 minutes'):
    models=run_models(data)
with compact_output('Individual feature evidence and paired diagnostics — estimated 3–5 minutes'):
    statistics=analyse(data,models)
with compact_output('Missingness, calibration and path-quality diagnostics — estimated 1 minute'):
    extensions=run_extensions(data,models,statistics)
with compact_output('Matched cohorts, extrapolation and attrition — estimated 1 minute'):
    feedback=run_feedback(data,models,statistics)
"""),
        md("""## Availability and incremental prediction

The following sections separate observation coverage, operational eligibility and predictive accuracy. The principal comparison adds six K inputs (30/60/90/180/360 days and max recorded history). Separate same-row ablations compare year/max additions with the original four-window K inventory, keeping model settings and shared availability controls fixed."""),
        code("""report_overview(data,models,statistics)
"""),
    ]
    for target in TARGETS:
        cells.append(md(f"## Forecasting future {target}\n\nHeatmaps show individual feature associations. Scatter plots show chronological Existing + K predictions in target units where supported, coloured by origin quarter. CAGR is fitted and shown as h-day log return so short-horizon annualisation does not overwhelm the chart; it has the same ordering as CAGR. Future labels and errors retain all tails."))
        for horizon in HORIZONS:
            cells.append(code(f"""show(ic_map(statistics,{horizon},{target!r}),
    'Individual features versus {horizon}-day future {target}',
    'Tiles are equal-origin rank IC, with defined-origin counts. Higher historical signed drawdown means a smaller loss. Correlation is descriptive and blank cells do not mean zero skill.')
p=models['predictions']
supported=p[p.horizon.eq({horizon})&p.target.eq({target!r})&p.arm.eq('Existing + K')&p.supported&p.phase.eq(0)&p.delay.eq(0)&~p.source&np.isfinite(p.actual)]
if len(supported):
    show(forecast_scatter(models,{horizon},{target!r}),
        '{horizon}-day {target}: chronological forecast versus outcome',
        'One dot is a supported vault/origin pair. The dashed identity is a perfect forecast; the decile-median line is descriptive. Display tails are disclosed, with all data retained for calculation. Axis scales are stated on the chart; CAGR uses linear horizon log-return units.')
else:
    display(Markdown({('### '+str(horizon)+'-day '+target+': forecast support'+chr(10)*2)!r}+PERIOD+'. No supported target-valid model predictions. Required label maturation and training support are insufficient; this is not evidence that the feature relationship is zero.'))
    show(forecast_scatter(models,{horizon},{target!r},supported_only=False),
        '{horizon}-day {target}: illustrative thin-support forecasts',
        'These forecasts fail the predeclared training-support gate. They are shown to inspect the requested horizon, excluded from headline errors/IC and cannot establish forecasting skill. Colours are forecast-origin quarters.')
"""))
    cells.extend(
        [
            md("""## Reading individual K inputs

These representative 30-day K plots show raw feature values against each future outcome at 30 days, using log-return units for CAGR. The linked catalogue contains every inventoried K window and all nine target/horizon combinations, each as a separate image."""),
            code("""for target in TARGETS:
    show(feature_scatter(data,'30d K-ratio',30,target),
         '30-day historical K versus 30-day future '+target,
         'X is historical K, not a composite score. Colours are origin quarters. Axis scales are stated on the chart; CAGR uses horizon log return; decile medians describe the relationship. Counts exclude only undefined feature/target pairs.')
"""),
            md("""## Baselines, missing policies and robustness

Compare forecast errors with historical constants and own-target persistence; then examine calendar phases, delayed entry, source-price filling, age/quality cohorts and concentration. All these are fixed diagnostics, not another parameter search."""),
            code("""primary=statistics['model_summary']
primary=primary[primary.phase.eq(0)&primary.delay.eq(0)&~primary.source]
for target in TARGETS:
    table(primary[primary.target.eq(target)][['horizon','arm','mean_IC','MAE','MSE','raw_MAE','demeaned_MSE','evaluation_origins','defined_IC_origins']],
          target+' forecast methods side by side',
          'Errors average within dates and then across dates. CAGR error uses h-day log return; K error uses fold-scaled asinh, with raw-unit MAE alongside. Different model coverage is disclosed; paired K effects are evaluated separately.',limit=60)
table(statistics['model_coverage'].query('supported == True'),'Forecast availability and partial histories',
      'Missing=True uses available shorter inputs. Complete-case uses the supported fixed 30/60/90-day inventory. Partial history is measured across ≤180-day existing inputs; 270/360/730-day columns are excluded from this partial-history definition. Coverage is separate from accuracy.',limit=60)
table(statistics['cohorts'],'Young and high-quality cohort comparisons',
      'Paired changes use identical vault/date observations within each cohort; small or constant cross-sections have undefined IC.')
paired=statistics['paired_summary']
table(paired[paired.old.eq('Existing')][['horizon','target','phase','delay','source','mean_delta_IC','MAE_change_fraction','calendar_blocks']],
      'Cadence, delayed-entry and source-price sensitivities',
      'phase 0 is the Jan-1 four-day schedule; phases 1–3 shift origins. delay=1 shifts both target endpoints one day. source=True changes only existing feature prices, keeping actual future labels.',limit=60)
table(statistics['blocks'].query('phase == 0 and delay == 0 and source == False and old == "Existing"'),
      'Independent-calendar-block paired changes','Each row is one complete horizon-length calendar block. Below eight usable blocks, show signs and estimates without an uncertainty interval.',limit=60)
robustness_report(data,models,statistics,extensions)
feedback_report(data,models,statistics,extensions,feedback)
"""),
            md("""## Secondary earlier-history evidence

This section is explicitly outside the default 2026 report. Earlier labels must meet the same actual-observation rules; no interpolation creates supervised Sharpe/K history."""),
            code("""prior=statistics['feature_summary'].query('period == "Long prior"')
table(prior.groupby(['horizon','target']).agg(defined_feature_origin_cells=('defined_origins','sum'),max_defined_origins=('defined_origins','max')).reset_index(),
      'Earlier actual-label feature support','This is a coverage audit, not extra independent model-validation evidence.',
      period='2023-03-01 → 2026-01-01 (end exclusive, UTC)')
"""),
            md("""## Complete individual K scatter catalogue

Each linked notebook has nine target/horizon sections, each with its own heading and description. Available combinations have separate images; unsupported long lookbacks have explanations. The 45-day notebook is an endpoint/legacy compatibility sensitivity. Splitting the catalogue keeps the main notebook renderable in VS Code."""),
            code("""with compact_output('Separate K scatter catalogue — estimated 1 minute'):
    catalogue=write_catalogue(data)
display(Markdown(catalogue))
"""),
            md("""## Reproducibility and research conclusions

Complete datasets, folds, support tables, numerical audits and individual PNG exports live under the ignored experiment-09 artefact namespace. The written findings distinguish incremental information, persistence and lack of evidence."""),
            code("""table(freeze_design(data),'Frozen prospective confirmation windows','The next four-day phase begins after the design date. These are earliest dates for eight complete horizon-length blocks and matured labels, conditional on observation and model support; eight blocks do not guarantee reliable inference.')
findings=write_findings(statistics,models,data,extensions,feedback)
display(Markdown(findings.replace('# Experiment 09 — K-ratio feature forecast findings','### Measured findings',1)))
table(pd.DataFrame([{'File':path.name,'SHA-256':sha256(path)} for path in sorted(ROOT.glob('k_ratio_*.py'))]),
      'Helper source fingerprints','Together with the pinned archive hash and model/data manifests, these identify the exact experiment implementation.')
"""),
        ]
    )
    findings_path = ROOT / "09-k-ratio-feature-forecast-findings.md"
    cache = ROOT / "_artifacts-restored-2026-10-07/09/models-manifest.json"
    if findings_path.exists() and cache.exists():
        import json
        from k_ratio_features import sha256

        signature = json.loads(cache.read_text()).get("fingerprint", "")
        if signature.startswith(sha256(ROOT / "k_ratio_forecast_models.py")) and signature.endswith(sha256(ROOT / "k_ratio_features.py")):
            measured = findings_path.read_text().split("## Key new insights\n\n", 1)[-1].split("## Sensitivities", 1)[0].strip()
            cells[0].source = cells[0].source.replace("Measured findings are generated after execution from the supported comparisons below. The original pre-review conclusions are not inherited.", measured)
    nb = nbformat.v4.new_notebook(cells=cells)
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.write(nb, NOTEBOOK)
    return NOTEBOOK


if __name__ == "__main__":
    print(build())
