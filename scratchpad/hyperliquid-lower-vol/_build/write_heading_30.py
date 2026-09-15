"""Generate NB30's heading FROM manifest_30.json."""
import json
from pathlib import Path

here = Path(__file__).parent
m = json.load(open(here / "manifest_30.json")); m28 = json.load(open(here / "manifest_28.json"))
FT, SEG, ST, PS, SS = m["fold_table"], m["segments"], m["stitched"], m["paired_sharpe"], m["signal_stability"]
folds = sorted(FT, key=int)
FS = m["full_screen"]
def _prov(m):
    for path, rec in m["provenance"].items():
        if path.endswith("vault-prices.parquet"):
            return rec
    raise KeyError("vault-prices.parquet not in provenance")
PV = _prov(m)

evaluable = [k for k in folds if FT[k]["evaluable"]]
n_ev = len(evaluable)
chose = [k for k in folds if FT[k]["leading_signal"] not in ("(none)", "(unevaluable)")]
total_evals = int(m["total_signal_fold_evaluations"])
passes = sum(int(v["folds_passing_gate_5"]) for v in SS.values())
identical = all(SEG[k]["identical_to_anchor"] for k in SEG)
st, an = ST["stitched out-of-fold"], ST["anchor, same cycles"]

def f4(x): return f"{x:.4f}"

def fold_row(k):
    r = FT[k]
    def _i(v): return "-" if v is None or v != v else str(int(v))
    ev = _i(r.get("signals_evaluated")); fam = _i(r.get("family_used")); cd = _i(r.get("complete_draws"))
    return (f"| {k} | {str(r['start'])[:10]} to {str(r['end_inclusive'])[:10]} | {r['fold_decisions']} | "
            f"{r['training_decisions']} | {'yes' if r['evaluable'] else 'no'} | {ev} | {fam} | {cd} | {r['leading_signal']} |")

H = f"""# NB30 - cross-fitted evaluation of the leading signal

A DIAGNOSTIC. It replaces the combined mechanism the plan's first draft proposed, which was
undefined and would have added a third selection layer on top of two that already share the same
returns.

Five contiguous folds over the decision schedule, trained WALK-FORWARD: for each fold, gate 5 is
re-run using only decisions strictly before the fold minus a 30-day embargo, the leading signal is
re-chosen from that reduced screen, and the prefilter runs with the fold's own choice active only
during that fold. The first build also used dates AFTER the fold, purged by 30 days - which covers
the forward targets and nothing else, because the signals use trailing windows of 45 to 360 rows
and a post-fold date carries the fold's returns inside its signal values. The review caught it.
Walk-forward means the earliest folds have too little history to screen on and are marked
unevaluable rather than screened.

**This is not a clean out-of-sample test and is not reported as one.** The folds share vaults and
one market regime; walk-forward removes temporal contamination and nothing removes
cross-sectional contamination.

**Verdict: {m['fold_stability'].split(' - ')[0]}.** {m['fold_stability'].split(' - ', 1)[1] if ' - ' in m['fold_stability'] else ''}

**Revised after Codex review**
([30-backtest-stability-crossfit-codex-review.md](30-backtest-stability-crossfit-codex-review.md),
`gpt-5.6-terra`) and re-run. This heading is generated from `_build/manifest_30.json` by
`_build/write_heading_30.py`.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb),
[29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb) and
[28-stable-selection-plan.md](28-stable-selection-plan.md). Full window 2026-01-01 to 2026-09-08.

## Key new insights and what did we learn from this experiment?

**1. {n_ev} of {len(folds)} folds are evaluable walk-forward, and none of those selected a
signal (cell 26).** A fold needs at least 40 training decisions before it, minus the embargo.

| fold | dates | decisions | training | evaluable | signals evaluated | family used | complete draws | leading signal |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(fold_row(k) for k in folds) + f"""

**2. {passes} of {total_evals} signal-fold evaluations pass on the evaluable folds, counting only
signals that were actually EVALUATED - enough dates, finite bounds (cell 26, cell 31).** The first
build of this round counted all 13 signals per fold as evaluations while a single unevaluable
hypothesis had voided every simultaneous bound; the review caught it. The simultaneous family is
now the evaluated hypotheses only, and its size and complete-draw count are in the table above.
This is the same test as NB28's, applied to overlapping prefixes of the same window; it is not
independent confirmation.

**3. "Unstable across folds" is not the finding; "empty on every evaluable fold" is.** The plan
pre-registered the conclusion for a leading signal that varies across folds - that the screen is
fitting noise. That does not apply, because no fold selected a signal at all. A screen that picks
a different winner each time is overfitting; one that picks nothing anywhere is either measuring
something absent or is mis-specified. NB28's decomposition is where that is drawn, and it draws
it against the gate.

**4. The stitched path is the anchor's own, by construction (cell 28, cell 29).** Every fold
contributed the anchor's segment - {'all' if identical else 'not all'} segments identical to the
anchor's - and they reassemble to it exactly: stitched Sharpe {f4(st['sharpe'])} against
{f4(an['sharpe'])}, CAGR {f4(st['cagr'])} against {f4(an['cagr'])}, paired difference
{PS['observed']:+.4f} on {PS['n']} cycles. This checks the segment slicing and re-indexing of the
anchor only. It does NOT exercise the activation window, which no run set, and the first heading
was wrong to call it a self-test of that code.

## Summary of results

| | |
|---|---|
| Eligible decisions | {m['eligible_decisions']} (cell 24, this kernel) |
| Folds | {len(folds)} contiguous (cell 26) |
| Evaluable walk-forward (>= 40 training decisions) | **{n_ev} of {len(folds)}** (cell 26) |
| Folds selecting a leading signal | **{len(chose)} of {n_ev}** evaluable (cell 26) |
| Signal-fold evaluations passing, evaluated signals only | **{passes} of {total_evals}** (cell 31) |
| Full-sample leader at {m['draws']} draws, this kernel | {m['full_sample_leader'] or 'None'}; {sum(1 for v in FS.values() if v['gate_5'])} of 13 pass (cell 24) |
| Stitched out-of-fold path | identical to the anchor's (cell 28, cell 29) |

## Robustness of results

- **What changed after the review.** Training is walk-forward only, so no training date's
  signal window can contain the fold's returns; unevaluable folds are reported as such. The
  "every fifth of the window" claim is withdrawn: each fold's screen is trained on a PREFIX of
  the schedule, and the prefixes overlap. The stitched-path identity is described as a check of
  anchor slicing only. The bootstrap machinery is the corrected `harness_rules_v2.py`.
- **Fewer bootstrap draws than NB28** ({m['draws']} against 500), because a fold's screen is a
  selection step rather than a reported interval. The full-sample screen at {m['draws']} draws
  reaches NB28's verdict on all thirteen signals, from this kernel's own `full_screen` (cell 24).
- **This notebook cannot distinguish "no effect" from "gate 5 is mis-specified".** It only
  re-applies the same gate to prefixes of the same sample.
- **The activation-window splice was never exercised.** `stability_prefilter_active_from` and
  `_active_to` are in `decide_trades` and defaulted off; no fold chose a signal, so no run set
  them. Their inertness on the anchor path is asserted (cell 22); their behaviour inside a fold
  is untested.
- **The screens use the PRE-REGISTERED raw concentration target**, as NB28's verdict does; the
  corrected excess target is NB28's post-review diagnostic and is not used here.
- **Snapshot**: `vault-prices.parquet` {PV['bytes']:,} bytes, sha256 prefix `{PV['sha256']}`, from
  this run's provenance via the manifest, asserted equal to NB28's and NB29's before their
  manifests were read (cell 22). Anchor parity holds at 1e-5 (cell 22).
"""
out = here.parent / "30-backtest-stability-crossfit.ipynb"
nb = json.load(open(out))
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"NB30 heading written: {m['fold_stability']}; evaluable {n_ev}/{len(folds)}; passes {passes}/{total_evals}")
