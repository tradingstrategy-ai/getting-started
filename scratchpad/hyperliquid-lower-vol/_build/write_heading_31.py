"""Generate NB31's heading FROM manifest_31.json and the upstream manifests."""
import json
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent))
from pathlib import Path

here = Path(__file__).parent
m = json.load(open(here / "manifest_31.json"))
m28 = json.load(open(here / "manifest_28.json")); m29 = json.load(open(here / "manifest_29.json")); m30 = json.load(open(here / "manifest_30.json"))
R, G, SP = m["reproduction"], m["gates"], m["specification"]; AU = m.get("audit", {})
S28 = m28["screen_full"]; G3 = m["gate_3_detail"]
def _prov(m):
    for path, rec in m["provenance"].items():
        if path.endswith("vault-prices.parquet"):
            return rec
    raise KeyError("vault-prices.parquet not in provenance")
PV = _prov(m)

centre = next(iter(G))
g = G[centre]
strong = [s for s in S28 if S28[s]["lo_forward_vol"] > 0 and S28[s]["lo_forward_downside"] > 0]
excess = [s for s in S28 if S28[s]["lo_forward_event_top5"] > 0]
hw = {s: m28["decomposition"][s]["return_half_width_pp"] for s in S28}
fam29 = {int(round(v["q"] * 100)): v for k, v in m29["family"].items() if v["signal"] == "inverse_vol"}
st29 = m29["strict"]; c29 = f"inverse_vol_q{int(round(m29['centre']*100)):02d}"
strict_diff = max(abs(st29[c29 + "_strict"][k] - st29[c29][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta", "mean_invested"))

def f4(x): return f"{x:.4f}"

H = f"""# NB31 - close-out, and the frozen prospective specification

Re-runs every configuration NB29 and NB30 executed, in ONE kernel on ONE snapshot; re-derives
gate 5 from a rebuilt panel; re-derives gates 1, 3, 4, 6, 7 and 8 from the re-run states, with
gates 2 and 9 failing closed as unexecuted; and cross-checks each run against the manifest it
was first recorded in at 1e-9.

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

**2. Gate 5 re-derived here agrees with NB28 (cell 26).** The panel is rebuilt from this
kernel's own logging run and the joint bootstrap and simultaneous bounds recomputed with the same
pre-registered target. Agreement is asserted on the gate-5 flags, on {len(m['gate_5_booleans_compared'])}
clause and evaluation booleans, on {m['gate_5_fields_compared']} unrounded numeric screen fields
(largest absolute difference {m['gate_5_worst_lo_diff']:.1e}), and on all six persisted diagnostics
of all three bootstrap families - critical value, complete, total and incomplete draw counts,
family size used and total - for all thirteen signals
({'True' if m['gate_5_rederived_agrees'] and m['gate_5_families_agree'] else 'FALSE'}).

**3. The two kernels agree on the verdict (cell 28).** `{centre}` fails the same gates here as in
NB29 - **{g['failed_gates']}** - with gates 1, 3, 4, 6, 7 and 8 re-derived from this kernel's
states, gate 5 from Part 1b, and gates 2 and 9 failing closed as unexecuted because no cheaper
gate survived. `gate_3_corrected`, using the concentration indicator whose numerator takes
the five largest POSITIVE residuals, is **{g['gate_3_corrected']}**: held concentration
{G3[centre]['held_held_concentration']:.6f} (original) against {G3[centre]['held_concentration_corrected']:.6f}
(corrected), anchor {G3[centre]['anchor_held_concentration']:.6f} against {G3[centre]['anchor_held_concentration_corrected']:.6f},
same covered dates {G3[centre]['indicators_same_dates']}, largest per-date difference
{G3[centre]['indicators_max_abs_diff_per_date']:.1e} (cell 28). The verdict gate uses the pre-registered
indicator, as the rules name it.

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
  {int(next(r for r in m28['missing_reasons'] if r['target']=='forward_event_top5')['missing'])/m28['panel_rows']*100:.0f}% missing;
  a near-perfect-foresight oracle that knows all three targets {'passes' if m28['oracle']['oracle_all']['stability_clause'] else 'fails'}
  the stability clause, one that knows only forward volatility {'passes' if m28['oracle']['oracle_vol']['stability_clause'] else 'fails'} it
  (forward volatility and forward concentration correlate {m28['oracle']['oracle_vol']['rho_forward_event_top5']:+.3f}),
  one that knows the forward return {'passes' if m28['oracle']['oracle_return']['return_clause'] else 'fails'} the return clause,
  and one that knows both clauses' targets {'PASSES' if m28['oracle']['oracle_gate5']['gate_5'] else 'FAILS'} the complete
  gate (NB28 cell 35). {'The whole gate is reachable on this panel; no real signal reaches it.' if m28['oracle']['oracle_gate5']['gate_5'] else 'Each clause is reachable separately; the complete gate was not shown reachable, and the null is stated no more strongly than that.'}
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

- **What changed after the reviews.** Gate 5 is re-derived, not imported, and compared on every
  field. Both concentration indicators are shown with their coverage and per-date equality. The return contrast is
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
- **The specification's `known_limits` text now says selection CAN move concentration** (cell 34),
  as NB29 cell 26 shows: `mean_holdings` {f4(m29['gate_3_detail'][c29]['mean_holdings'])} against
  6.0000, `top_vault_pnl_share` {f4(m29['gate_3_detail'][c29]['top_vault_pnl_share'])} against
  {f4(m29['anchor_reference']['top_vault_pnl_share'])}.
- **All four notebooks ran on one snapshot, asserted rather than assumed**: `vault-prices.parquet`
  {PV['bytes']:,} bytes, sha256 prefix `{PV['sha256']}`, with each upstream manifest's provenance
  checked against this kernel's before any of its results were used (cell 22). An earlier heading
  hard-coded a prior snapshot's hash; the review caught it.
- **Every re-run configuration is audited, and the fee recomputed independently** (cell 41,
  written back to the manifest): {AU.get('runs_audited', '?')} runs, {AU.get('integrity_failures', '?')}
  integrity failures; over {AU.get('fee_redemptions', '?')} redemptions the stored fee rate differs
  from `10% x max(gross - released cost basis, 0) + 10 bps` by at most
  {AU.get('fee_worst_rate_diff', float('nan')):.2e}, a worst net-proceeds difference of
  ${AU.get('fee_worst_proceeds_diff_usd', float('nan')):,.2f} on one redemption, {AU.get('fee_over_1bp', '?')}
  redemptions over 1 bp, a net signed difference of ${AU.get('fee_net_signed_proceeds_diff_usd', float('nan')):+,.2f}
  across the eight runs{" - one-sided: the engine charged more than the formula on every affected redemption, never less" if abs(AU.get('fee_sum_abs_proceeds_diff_usd', 0) + AU.get('fee_net_signed_proceeds_diff_usd', 0)) < 1e-6 else ""}. The cause is NOT decomposed - the engine stores its rate at the decision
  timestamp and this recomputation uses the trade's planned mid-price, and separating price drift
  from basis mismatch needs decision-time inputs recorded on the trade. Track-level item.
- **What would change the conclusion.** Gate 5 fails on a third target nothing established and a
  return clause far wider than its margin. A rule change addressing either is a legitimate
  pre-registration for a NEXT plan and is not made here.
"""
out = here.parent / "31-backtest-stability-closeout.ipynb"
nb = json.load(open(out))
from audit_notes import insert_audit
H = insert_audit(H, 31)
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"NB31 heading written: {SP['status']}; reproduce {R['reproducing_at_1e-9']}/{R['configurations']}; gate5 agrees {m['gate_5_rederived_agrees']}")
