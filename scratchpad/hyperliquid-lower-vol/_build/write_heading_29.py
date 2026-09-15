"""Generate NB29's heading FROM manifest_29.json and manifest_28.json."""
import json
from pathlib import Path

here = Path(__file__).parent
m = json.load(open(here / "manifest_29.json")); m28 = json.load(open(here / "manifest_28.json"))
F, G, D, C, ST, A, N, I = (m["family"], m["gates"], m["gate_3_detail"], m["cheap_gates"], m["strict"],
                           m["anchor_reference"], m["nulls"], m["inertness"])
PB = m["paired_bootstrap"]
centre = f"inverse_vol_q{int(round(m['centre']*100)):02d}"
g, d, c = G[centre], D[centre], C[centre]
fam = {int(round(F[k]["q"] * 100)): F[k] for k in F if F[k]["signal"] == "inverse_vol"}
strict_on, strict_off = ST[centre + "_strict"], ST[centre]
strict_diff = max(abs(strict_on[k] - strict_off[k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta", "mean_invested"))
pb5 = next(r for r in PB if r["run"] == centre and r["block"] == 5)
pb20 = next(r for r in PB if r["run"] == centre and r["block"] == 20)
failed = g["failed_gates"]
n_failed = len([x for x in failed.split(", ") if x])
inert_any = any(v["inert"] for v in I.values())
q20, q40 = fam[20], fam[40]
gap20, gap40 = abs(fam[30]["cycle_sharpe"] - q20["cycle_sharpe"]), abs(fam[30]["cycle_sharpe"] - q40["cycle_sharpe"])
carried = m["carried"]

def f4(x): return f"{x:.4f}"
def pc(x): return f"{x*100:.1f}%"

H = f"""# NB29 - the stability prefilter, one signal at a time

[NB28](28-research-stability-signal-screen.ipynb) screened thirteen signals for whether they
predict forward stability at all. **{sum(m28['gate_5'].values())} passed gate 5**, so
{'none is' if not sum(m28['gate_5'].values()) else 'only those are'} backtested as a candidate -
that is what "REJECTED without a backtest" means in [RESEARCH-RULES.md](RESEARCH-RULES.md).
This notebook runs `inverse_vol` {'alone, ' if carried == ['inverse_vol'] else ''}as the labelled
REFERENCE it always was: the sizing rule's own premise and NB26's `measured_only` drop, generalised.

The mechanism: at each decision, among the candidates that reach the ranking step, exclude the
least-stable fraction `q` of those for which the signal is FINITE, then rank and size the
survivors exactly as the incumbent does.

**Verdict: {m['verdict'].split(' - ')[0]}.** {'Nothing is shortlisted.' if not m['shortlisted'] else 'Shortlisted: ' + ', '.join(m['shortlisted'])}

**Revised after Codex review**
([29-backtest-stability-prefilter-codex-review.md](29-backtest-stability-prefilter-codex-review.md),
`gpt-5.6-terra`) and re-run. This heading is generated from `_build/manifest_29.json` by
`_build/write_heading_29.py`. The review log is in the Robustness section.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) as the anchor,
[28-stable-selection-plan.md](28-stable-selection-plan.md), and NB26's `measured_only` drop, which
this mechanism generalises - `inverse_vol` with a count of 8 reproduces `measured_8` on every
panel metric to 0.000e+00, verified in [_build/verify-prefilter.ipynb](_build/verify-prefilter.ipynb).
Full window 2026-01-01 to 2026-09-08, in-sample throughout.

## Method

Five exclusion fractions, centre 0.30, permissive - a candidate with no signal value is KEPT. A
strict variant at the centre excludes them instead and is DIAGNOSTIC only. The nine gates are
scored cheapest-first, so an expensive re-simulation never runs for a candidate that already
failed a cheap gate, and every unexecuted gate is False rather than absent.

## Key new insights and what did we learn from this experiment?

**1. Excluding the most volatile candidates lowers portfolio volatility a great deal and destroys
return doing it (cell 24).**

| q | realised exclusion share | CAGR | cycle Sharpe | cycle vol | ulcer | invested |
|---|---|---|---|---|---|---|
| anchor | 0.0000 | {f4(A['cagr'])} | {f4(A['cycle_sharpe'])} | {f4(A['cycle_vol'])} | {f4(A['ulcer'])} | {f4(A['mean_invested'])} |
""" + "".join(
    f"| {q/100:.2f} | {f4(fam[q]['realised_excluded_share'])} | {f4(fam[q]['cagr'])} | {f4(fam[q]['cycle_sharpe'])} | {f4(fam[q]['cycle_vol'])} | {f4(fam[q]['ulcer'])} | {f4(fam[q]['mean_invested'])} |\n"
    for q in sorted(fam)) + f"""
Cycle volatility falls monotonically from {f4(A['cycle_vol'])} to {f4(fam[50]['cycle_vol'])} while
mean invested stays between {f4(min(v['mean_invested'] for v in fam.values()))} and
{f4(max(v['mean_invested'] for v in fam.values()))}. `RESEARCH-RULES.md` consequence 2 said the only
thing in this track that had ever materially lowered volatility was holding cash; this lowers it
further than the 10% volatility target did (0.085) while staying invested. Sharpe falls with it,
from {f4(A['cycle_sharpe'])} to {f4(fam[50]['cycle_sharpe'])}.

**2. At q = 0.10 the mechanism beats the anchor on all four headline metrics, and that is not
evidence of anything.** CAGR {f4(fam[10]['cagr'])} against {f4(A['cagr'])}, Sharpe
{f4(fam[10]['cycle_sharpe'])} against {f4(A['cycle_sharpe'])}, volatility {f4(fam[10]['cycle_vol'])}
against {f4(A['cycle_vol'])}, ulcer {f4(fam[10]['ulcer'])} against {f4(A['ulcer'])}. It is not the
pre-registered centre, its signal failed gate 5, and NB25 established that a random removal of
nine vaults ranks seventh of 57 by Sharpe.

**3. The strict variant is inert to {strict_diff:.1e} on every metric (cell 28).** Strict excludes
unmeasured candidates as well, raising the realised exclusion share from
{f4(strict_off['realised_excluded_share'])} to **{f4(strict_on['realised_excluded_share'])}**, and CAGR,
Sharpe, volatility, ulcer, max drawdown, invested beta and mean invested are identical at ten
decimal places. The vaults with no volatility estimate were never going to be selected. NB21 and
NB26 found the data-availability half of the vol-matched drop inert; this reproduces it through
a different mechanism.

**4. The centre is not a plateau, and it fails on the low side (cell 30).** `inverse_vol_q20`
reaches Sharpe {f4(q20['cycle_sharpe'])}, a gap of {f4(gap20)} from the centre's
{f4(fam[30]['cycle_sharpe'])} against a tolerance of 0.25. `inverse_vol_q40` passes at {f4(gap40)}.

**5. The book it holds is calmer; whether it is spikier depends on which concentration indicator
is believed (cell 35).** Capital-weighted own volatility falls from {f4(d['anchor_held_vol'])} to
{f4(d['held_held_vol'])}. Own event concentration by the PRE-REGISTERED indicator rises from
{f4(d['anchor_held_concentration'])} to {f4(d['held_held_concentration'])} on {int(d['held_dates_used'])} dates,
so gate 3 fails. By the corrected indicator - `residual_event_concentration_positive`, whose
numerator takes the five largest POSITIVE residuals as the original's docstring claimed - it is
{f4(d['held_concentration_corrected'])} against the anchor's {f4(d['anchor_held_concentration_corrected'])}
on {int(d['dates_used_corrected'])} dates, and `gate_3_corrected` is **{g['gate_3_corrected']}**.
{'The two indicators give IDENTICAL held-book values here: on every held vault-date where the original is finite, the window already holds at least five positive residual days, so the top five of all residuals and the top five of the positive ones coincide. The defect is real in the code and unreachable on this book - shown, not assumed, which is what standing rule 9 asks of a surprising null.' if abs(d['held_held_concentration'] - d['held_concentration_corrected']) < 1e-9 and abs(d['anchor_held_concentration'] - d['anchor_held_concentration_corrected']) < 1e-9 else 'The two indicators differ on this book, and the verdict gate uses the pre-registered one as the rules name it.'}

**6. Nothing is inert and everything changes a lot (cell 26).** At the centre the prefilter
changes the selected basket on {int(I[centre]['dates_with_a_different_basket'])} of
{int(I[centre]['dates_matched_to_reference'])} decisions, excludes
{int(I[centre]['excluded_names_the_reference_held'])} names the anchor was holding, and reaches a basket
Jaccard of {f4(I[centre]['basket_jaccard_vs_reference'])} against it.
{'No run is inert.' if not inert_any else 'Inert runs: ' + ', '.join(k for k, v in I.items() if v['inert'])}

## Summary of results

**{m['verdict'].split(' - ')[0]}.** `{centre}` fails {n_failed} of nine gates: **{failed}** (cell 35).

| gate | result | why |
|---|---|---|
| 1 positive return | {'PASS' if g['gate_1_positive'] else 'FAIL'} | CAGR {f4(fam[30]['cagr'])} |
| 2 single-vault survival | {'PASS' if g['gate_2_lovo'] else 'FAIL'} | {'not evaluated - a cheaper gate failed' if not c['all_cheap_gates'] else 'evaluated'} |
| 3 held-book stability | {'PASS' if g['gate_3_held_book'] else 'FAIL'} | own volatility {f4(d['held_held_vol'])} vs {f4(d['anchor_held_vol'])}; own concentration {f4(d['held_held_concentration'])} vs {f4(d['anchor_held_concentration'])} (corrected indicator: {g['gate_3_corrected']}) |
| 4 not luck | {'PASS' if g['gate_4_luck'] else 'FAIL'} | `luck_ratio` {'NaN - fails closed' if d['luck_ratio'] != d['luck_ratio'] else f4(d['luck_ratio'])}; `top5_gross_share` {f4(d['top5_gross_share'])} vs anchor {f4(A['top5_gross_share'])} |
| 5 screen | {'PASS' if g['gate_5_screen'] else 'FAIL'} | {sum(m28['gate_5'].values())} signals passed NB28 |
| 6 plateau | {'PASS' if g['gate_6_plateau'] else 'FAIL'} | q = 0.20 gap {f4(gap20)}, q = 0.40 gap {f4(gap40)}, tolerance 0.25 |
| 7 sub-period sign | {'PASS' if g['gate_7_subperiod'] else 'FAIL'} | sparse {fam[30]['sparse_cagr']:+.4f}, dense {fam[30]['dense_cagr']:+.4f}, late {fam[30]['late_cagr']:+.4f} |
| 8 diversification | {'PASS' if g['gate_8_diversification'] else 'FAIL'} | {d['diversification_failures'] or 'all five measures no worse'} |
| 9 null | {'PASS' if g['gate_9_null'] else 'FAIL'} | {'not executed - a cheaper gate failed' if not N else 'executed'} |

Paired block bootstrap against the anchor, context only (cell 38): observed Sharpe difference
{pb5['observed_diff']:+.4f}, 95% interval [{pb5['ci_lo']:+.2f}, {pb5['ci_hi']:+.2f}] at block 5 and
[{pb20['ci_lo']:+.2f}, {pb20['ci_hi']:+.2f}] at block 20.

## Robustness of results

- **What changed after the review.** Gate 3 is now reported with both the pre-registered
  indicator and its corrected form; the strict-variant claim is made from ten-decimal manifest
  values rather than a four-decimal display; "fully invested" is replaced by the measured range;
  the gate-4 explanation names the non-finite leg rather than asserting which one it is. The
  review's finding that the integrity and fee audits inspect only the anchor state is correct
  and inherited from the base notebook; it is recorded, not fixed here.
- **Gate 8 rejected on an arithmetic margin.** `mean_holdings` {f4(d['mean_holdings'])}
  against the anchor's exactly 6.0000. The rule was pre-registered and stands; four of five
  diversification measures are better than the anchor's, including `top_vault_pnl_share`
  {f4(d['top_vault_pnl_share'])} against {f4(A['top_vault_pnl_share'])}.
- **Gate 3 is measured on {int(d['held_dates_used'])} of 126 dates** by the pre-registered indicator
  and {int(d['dates_used_corrected'])} by the corrected one, because most held vaults carry no
  event-concentration value at T-1.
- **Gate 4 failed on a non-finite value.** `luck_ratio` is NaN when either of its legs is
  non-positive; the components are not printed and the notebook does not say which.
- **Gates 2 and 9 were never executed.** They are False per standing rule 8.
- **Only one signal was backtested**, so the matched-share table has one row and there is no
  family-wise correction to run.
- **Snapshot**: `vault-prices.parquet` 254,818,366 bytes, sha256 prefix `3e79966a`. Anchor parity
  holds at 1e-5 (cell 22).
"""
out = here.parent / "29-backtest-stability-prefilter.ipynb"
nb = json.load(open(out))
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"NB29 heading written: {m['verdict']}; gate_3_corrected={g['gate_3_corrected']}; strict diff {strict_diff:.1e}")
