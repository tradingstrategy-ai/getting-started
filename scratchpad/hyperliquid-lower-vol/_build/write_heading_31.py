"""Generate NB31's heading FROM manifest_31.json and the upstream manifests."""
import json
from pathlib import Path

here = Path(__file__).parent
m = json.load(open(here / "manifest_31.json"))
m28 = json.load(open(here / "manifest_28.json")); m29 = json.load(open(here / "manifest_29.json")); m30 = json.load(open(here / "manifest_30.json"))
R, G, SP = m["reproduction"], m["gates"], m["specification"]
S28 = m28["screen"]
centre = next(iter(G))
g = G[centre]
strong = [s for s in S28 if S28[s]["lo_forward_vol"] > 0 and S28[s]["lo_forward_downside"] > 0]
excess = [s for s in S28 if S28[s]["lo_forward_event_top5_excess"] > 0]
hw = {s: m28["decomposition"][s]["return_half_width_pp"] for s in S28}
fam29 = {int(round(v["q"] * 100)): v for k, v in m29["family"].items() if v["signal"] == "inverse_vol"}
st29 = m29["strict"]; c29 = f"inverse_vol_q{int(round(m29['centre']*100)):02d}"
strict_diff = max(abs(st29[c29 + "_strict"][k] - st29[c29][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta", "mean_invested"))

def f4(x): return f"{x:.4f}"

H = f"""# NB31 - close-out, and the frozen prospective specification

Re-runs every configuration NB29 and NB30 executed, in ONE kernel on ONE snapshot; re-derives
gate 5 from a rebuilt panel and the corrected bootstrap; re-derives gates 1-4 and 6-9 from the
re-run states; and cross-checks each run against the manifest it was first recorded in at 1e-9.

**Verdict: {SP['status'].split(' - ')[0]}.** {SP['status'].split(' - ', 1)[1] if ' - ' in SP['status'] else ''}
ADOPT is not in this batch's vocabulary and SHORTLIST was the strongest verdict available;
neither was reached.

**Revised after Codex review**
([31-backtest-stability-closeout-codex-review.md](31-backtest-stability-closeout-codex-review.md),
`gpt-5.6-terra`) and re-run. The first build imported gate 5 from NB28's manifest and called every
gate "re-derived"; gate 5 is now recomputed here (cell 26) and compared with NB28 before anything
uses it. This heading is generated from `_build/manifest_31.json` by `_build/write_heading_31.py`.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb),
[29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb),
[30-backtest-stability-crossfit.ipynb](30-backtest-stability-crossfit.ipynb) and
[28-stable-selection-plan.md](28-stable-selection-plan.md).

## Key new insights and what did we learn from this experiment?

**1. Every backtest in this batch reproduces across kernels (cell 24).** {R['reproducing_at_1e-9']} of
{R['configurations']} configurations re-run to a worst absolute difference of {R['worst_abs_diff']:.1e}
across CAGR, cycle Sharpe, cycle volatility, ulcer, max drawdown, invested beta and mean invested.

**2. Gate 5 re-derived here agrees with NB28 (cell 26).** The panel is rebuilt from this kernel's
own logging run and the joint bootstrap and simultaneous bounds recomputed with the corrected
machinery: the gate-5 flags agree on all thirteen signals ({'True' if m['gate_5_rederived_agrees'] else 'FALSE'}),
and the largest difference in any forward-volatility lower bound is {m['gate_5_worst_lo_diff']:.1e}.

**3. The two kernels agree on the verdict (cell 28).** `{centre}` fails the same gates here as in
NB29 - **{g['failed_gates']}** - with gates 1-4 and 6-9 re-derived from this kernel's states and
gate 5 from Part 1b. `gate_3_corrected`, using the concentration indicator whose numerator takes
the five largest POSITIVE residuals, is **{g['gate_3_corrected']}**; the verdict gate uses the
pre-registered indicator, as the rules name it.

**4. The candidate family is EMPTY, so there is no multiplicity to correct (cell 30).** Family
membership is every configuration evaluated as potentially shortlistable, which requires a gate-5
pass upstream; {sum(m28['gate_5'].values())} signals have one. All {len(m['family_excluded'])} executed
runs are excluded by role and `family_wise_joint()` is not run.

**5. No specification to freeze, and that is the correct output (cell 34).** Five of six fields
are fixed - comparator, horizon, statistic, stopping rule, what may not change - and the signal
and `q` are `None`, because gate 5 admitted nothing.

## Summary of results

| | |
|---|---|
| Configurations re-run and cross-checked | **{R['reproducing_at_1e-9']} of {R['configurations']}**, worst difference {R['worst_abs_diff']:.1e} (cell 24) |
| Gate 5 re-derived agrees with NB28 | **{m['gate_5_rederived_agrees']}** on 13 of 13 (cell 26) |
| Kernels agree with NB29 on the verdict | **{m['kernels_agree_with_nb29']}** (cell 28) |
| Shortlisted | **{'nothing' if not m['shortlisted'] else ', '.join(m['shortlisted'])}** (cell 28) |
| Candidate family size | **{len(m['family_membership'])}** (cell 30) |
| Prospective specification | signal `{SP['signal']}`, `q` `{SP['exclusion_fraction_q']}` (cell 34) |

What this batch established, across NB28-NB31, after review:

- {len(strong)} signals predict forward volatility and forward downside with simultaneous lower
  bounds above zero; `inverse_vol` at {f4(S28['inverse_vol']['rho_forward_vol'])} / {f4(S28['inverse_vol']['lo_forward_vol'])}
  (NB28 cell 29).
- {len(excess)} of 13 established a positive association with forward event concentration under
  the pre-registered criterion (NB28 cell 33) - a failure to establish, on a target that is
  {int(next(r for r in m28['missing_reasons'] if r['target']=='forward_event_top5_excess')['missing'])/m28['panel_rows']*100:.0f}% missing.
- Gate 5's return clause has a half-width of {min(hw.values()):.0f} to {max(hw.values()):.0f}
  compounded annual percentage points against a {m28['delta_annualised_pp']:.0f}-point margin
  (NB28 cell 32).
- Excluding the most volatile candidates cuts cycle volatility from {f4(m29['anchor_reference']['cycle_vol'])}
  to {f4(fam29[50]['cycle_vol'])} while staying {fam29[50]['mean_invested']*100:.0f}% invested, and Sharpe
  from {f4(m29['anchor_reference']['cycle_sharpe'])} to {f4(fam29[50]['cycle_sharpe'])} (NB29 cell 24).
- The data-availability half of the filter is inert to {strict_diff:.1e} (NB29 cell 28).
- {m30['folds_evaluable']} of {m30['folds']} folds are evaluable walk-forward and none selected a
  signal (NB30 cell 26).

## Robustness of results

- **What changed after the review.** Gate 5 is re-derived, not imported. The return contrast is
  in compounded annual percentage points, the unit `delta` was calibrated in. The heading no
  longer says "nothing predicts forward event concentration"; it says no signal established a
  positive association under the criterion, which is what the cells show. Gate 3 is reported
  both ways.
- **"Reproduces at 1e-9" is a weaker claim than the result.** The tolerance is 1e-9; the observed
  worst difference is {R['worst_abs_diff']:.1e}.
- **Gates 2 and 9 were never executed anywhere in this batch.** Six cheaper gates failed first.
  They are False per standing rule 8, and this batch contributes no evidence about single-vault
  dependence or the prefilter's own null.
- **Only one signal was ever backtested**, so this close-out exercises no cross-signal comparison
  and no family-wise correction.
- **The activation-window splice is still unexercised.**
- **The specification's `known_limits` text says concentration is not moved by selection.** NB29
  cell 26 shows the prefilter does move it: `mean_holdings` {f4(m29['gate_3_detail'][c29]['mean_holdings'])}
  against 6.0000, `top_vault_pnl_share` {f4(m29['gate_3_detail'][c29]['top_vault_pnl_share'])} against
  {f4(m29['anchor_reference']['top_vault_pnl_share'])}. The cell is left as executed; the correction is here.
- **Reproducibility across kernels is not reproducibility across snapshots.** All four notebooks
  ran on `vault-prices.parquet` 254,818,366 bytes, sha256 prefix `3e79966a`.
- **What would change the conclusion.** Gate 5 fails on a third target nothing established and a
  return clause far wider than its margin. A rule change addressing either is a legitimate
  pre-registration for a NEXT plan and is not made here.
"""
out = here.parent / "31-backtest-stability-closeout.ipynb"
nb = json.load(open(out))
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"NB31 heading written: {SP['status']}; reproduce {R['reproducing_at_1e-9']}/{R['configurations']}; gate5 agrees {m['gate_5_rederived_agrees']}")
