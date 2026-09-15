"""Generate NB28's heading FROM manifest_28.json. Every number is read from the frame that produced
it; the first heading quoted critical values from a discarded run, which the review caught."""
import json
from pathlib import Path

m = json.load(open(Path(__file__).parent / "manifest_28.json"))
S, D, U = m["screen"], m["decomposition"], m["unadjusted"]
signals = list(S)
delta = float(m["delta_annualised_pp"])
crit = m["bootstrap"]
draws = m["draws_complete"]
T = ["forward_vol", "forward_downside", "forward_event_top5_excess"]

def pct(x): return f"{x*100:.1f}%"
def f4(x): return f"{x:.4f}"

passers = [s for s in signals if m["gate_5"][s]]
cleared = {s: [t for t in T if S[s][f"lo_{t}"] > 0] for s in signals}
two_plus = [s for s in signals if len(cleared[s]) >= 2]
vol_down = [s for s in signals if "forward_vol" in cleared[s] and "forward_downside" in cleared[s]]
excess_clear = [s for s in signals if "forward_event_top5_excess" in cleared[s]]
best_excess = max(signals, key=lambda s: S[s]["rho_forward_event_top5_excess"])
u_best = next(r for r in U if r["signal"] == best_excess and r["target"] == "forward_event_top5_excess")
hw = {s: D[s]["return_half_width_pp"] for s in signals}
share = {s: D[s]["margin_as_share_of_half_width"] for s in signals}
positive_contrast = [s for s in signals if S[s]["return_contrast_pp"] > 0]
conc = ["residual_event_concentration", "fresh_event_concentration"]
cvf = m["calendar_vs_fresh"]
pers = m["persistence"]; conf = m["confounds"]; nan = m["nan_rates"]
miss = {r["target"]: r for r in m["missing_reasons"]}
fr = m["forward_return_describe"]
corr = m["corrected_concentration_diagnostic"]
strong = sorted(vol_down, key=lambda s: -S[s]["rho_forward_vol"])

def strong_line(s):
    return (f"`{s}` ({f4(S[s]['rho_forward_vol'])} / {f4(S[s]['lo_forward_vol'])} on volatility, "
            f"{f4(S[s]['rho_forward_downside'])} / {f4(S[s]['lo_forward_downside'])} on downside)")

H = f"""# NB28 - which stability signals predict forward stability?

Gate 5 of [RESEARCH-RULES.md](RESEARCH-RULES.md): *before* a mechanism is backtested, its score
read at a decision timestamp must rank-correlate positively across candidates with those vaults'
REALISED FORWARD stability. Not forward return. A mechanism that fails this is not selecting
stable vaults, and whatever portfolio Sharpe it reaches is incidental.

**Nothing in this notebook or in NB29-NB31 can be adopted, and ADOPT is not in their vocabulary.**
The screen chooses signals using 30-day forward windows and the backtests then judge portfolios
built from those signals on returns that overlap the same windows. The deliverable of this batch
is a ranked shortlist and a frozen prospective specification. Verdicts are SHORTLIST / REJECT /
DIAGNOSTIC.

**Revised after Codex review**
([28-research-stability-signal-screen-codex-review.md](28-research-stability-signal-screen-codex-review.md),
`gpt-5.6-terra`) and re-run. This heading is generated from `_build/manifest_28.json` by
`_build/write_heading_28.py`; the first heading quoted two critical values from a discarded run.
The review log is in the Robustness section.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) as the anchor, the plan in
[28-stable-selection-plan.md](28-stable-selection-plan.md), and the rejected-experiment lessons
from [25-research-stability-comparison.ipynb](25-research-stability-comparison.ipynb) and
[26-backtest-drop-decomposition.ipynb](26-backtest-drop-decomposition.ipynb). Full window
2026-01-01 to 2026-09-08, in-sample throughout.

## Method

One logging run populates `PREFILTER_LOG` with the candidate pool the trading code actually
ranked at each decision - never reconstructed offline. Thirteen signals are read at T-1 for every
candidate on every eligible decision, and four forward targets are measured over `(T, T + 30
days]` from the NAV carried at T, so no event straddles the decision.

Inference is ONE two-way cluster bootstrap - circular moving blocks of 15 decisions over dates,
vault clusters resampled together - whose resamples every hypothesis shares, with simultaneous
one-sided max-T bounds over two pre-registered families: 39 stability hypotheses and 13 return
hypotheses. A draw enters the max-T statistic only when every hypothesis in the family is finite
in it: {draws['stability']} of {draws['total']} draws for the stability family, {draws['returns']}
of {draws['total']} for the return family (cell 29).

Gate 5's pass rule, pre-registered: all THREE of forward volatility, forward downside variation
and forward event concentration show a positive association with the signal's stable end, with
the simultaneous lower bound above zero; AND the simultaneous lower bound on the
stable-versus-unstable forward return contrast, in compounded annual percentage points, exceeds
`-delta` with `delta = {delta:.0f}`.

The event-concentration target is the EXCESS of the forward top-five share over the uniform-events
value `min(5, n)/n`. The raw share is bounded below by 5/n - 0.625 at the eight-event minimum -
so it partly measured how often a vault reported; the review caught that, and the raw share is
kept as a diagnostic.

## Key new insights and what did we learn from this experiment?

**{len(passers)} of 13 signals pass gate 5 (cell 30, cell 41).**{' None is carried into NB29 as a candidate; `inverse_vol` goes forward only as the labelled reference.' if not passers else ' Carried: ' + ', '.join(passers) + '.'}
"Fails gate 5" is up to four separate facts, and the decomposition (cell 32) is the actual finding:

**1. Trailing volatility predicts forward volatility, and the evidence is not marginal.** On
{S['inverse_vol']['dates']} eligible decisions and {S['inverse_vol']['rows']:,} complete-case rows,
{len(vol_down)} signals clear BOTH forward volatility and forward downside variation with
simultaneous lower bounds above zero (signed Spearman / lower bound): {'; '.join(strong_line(s) for s in strong)}.

**2. No signal established a positive association with forward event concentration under the
pre-registered criterion.** {len(excess_clear)} of 13 clear it. The largest point estimate is
`{best_excess}` at {f4(S[best_excess]['rho_forward_event_top5_excess'])}, with an unadjusted lower
bound of {f4(u_best['lo_unadjusted'])} and a simultaneous lower bound of {f4(S[best_excess]['lo_forward_event_top5_excess'])}
(cell 33). This is a failure to establish, not evidence of absence: the target is missing on
{int(miss['forward_event_top5_excess']['missing'])} of {int(miss['forward_event_top5_excess']['finite'] + miss['forward_event_top5_excess']['missing']):,}
rows (cell 26), and the excess-over-uniform construction is new to this run.

**3. The return clause cannot discriminate on this window.** Simultaneous half-widths on the
stable-versus-unstable forward return contrast run from **{min(hw.values()):.1f} to {max(hw.values()):.1f}
compounded annual percentage points** against a margin of {delta:.0f}: the margin is
{min(share.values())*100:.1f}% to {max(share.values())*100:.1f}% of the uncertainty it is compared
against (cell 32). The raw target has a minimum of {fr['min']:.2f} and a 1st percentile of
{fr['1%']:.2f} in 30-day log return on {int(fr['count']):,} rows (cell 32); a few vaults lose
essentially everything inside a month, the excluded tail collects them, and a mean over that
cross-section carries a standard error orders of magnitude larger than the margin. Compounding a
mean 30-day log return to an annual rate - the unit `delta` was calibrated in, and the change the
review asked for - amplifies that tail further; the earlier linear scaling of the log-return difference gave
narrower half-widths that were still far wider than the margin (recorded in the review log, not
in a cell of this run). Under either unit a non-inferiority test on a mean forward
return is not a usable instrument on this cohort. That is a finding about the rule, not about
the signals.

**4. The point estimates lean the other way from the prior the clause was written against.** For
{len(positive_contrast)} of 13 signals the stable-versus-unstable return contrast is positive -
`inverse_vol` at **{S['inverse_vol']['return_contrast_pp']:+.1f}** and `downside_deviation_90` at
{S['downside_deviation_90']['return_contrast_pp']:+.1f} compounded annual percentage points (cell 30).
The intervals cannot support the claim - that is point 3 - but the sign is the reverse of what the
gate was designed to catch.

**5. Both event-concentration signals have the wrong sign on forward volatility.**
`residual_event_concentration` scores {f4(S['residual_event_concentration']['rho_forward_vol'])} and
`fresh_event_concentration` {f4(S['fresh_event_concentration']['rho_forward_vol'])} (cell 29): the
vaults they call spiky have LOWER forward volatility. Neither lower bound excludes zero in the
intended direction, so this is a failure to support the premise rather than evidence of an
inverted effect.

**6. The calendar clock and the fresh-event clock are not distinguishable on a common sample.**
On {m['calendar_vs_fresh_common_rows']:,} (date, vault) rows where BOTH signals are finite, with one
bootstrap on that sample, the paired difference on forward volatility is
{cvf['spearman_forward_vol']['difference']:+.4f} with a 95% interval of
[{cvf['spearman_forward_vol']['ci_lo']:+.4f}, {cvf['spearman_forward_vol']['ci_hi']:+.4f}] (cell 37); every
one of the eight statistics' intervals contains zero. The first build differenced two
different complete-case samples; the review was right that this is the comparison the question needs.

**7. The rule and the mechanism agree in direction.** The tail-aligned contrast - what the 30% the
prefilter would exclude actually did - has the same sign as the Spearman on forward volatility for
every signal (cell 35).

**8. Persistence discriminates nothing and the volatility family is entangled with staleness.**
Median rank persistence runs {min(v['median_persistence'] for v in pers.values()):.4f} to
{max(v['median_persistence'] for v in pers.values()):.4f}, and the staleness control sits at
{pers['fresh_observation_count']['median_persistence']:.4f} (cell 39). `btc_beta` correlates
{conf['btc_beta']['rho_vs_fresh_observation_count']:+.4f} with `fresh_observation_count`,
`downside_deviation_90` {conf['downside_deviation_90']['rho_vs_fresh_observation_count']:+.4f} and
`inverse_vol` {conf['inverse_vol']['rho_vs_fresh_observation_count']:+.4f}; `ulcer_index_180` correlates
{conf['ulcer_index_180']['rho_vs_tvl']:+.4f} with TVL (cell 39).

**9. The corrected NB08 indicator behaves like its parent.** `residual_event_concentration_positive`,
which takes its top five from the positive residuals as its docstring always claimed, has a
descriptive mean Spearman of {corr['forward_vol']['mean_raw_spearman']:+.4f} against forward
volatility and {corr['forward_event_top5_excess']['mean_raw_spearman']:+.4f} against forward
event-concentration excess (cell 37) - outside the pre-registered family and without
multiplicity control.

## Summary of results

| | |
|---|---|
| Decisions logged | {m['logged_decisions']} (cell 24) |
| Eligible on a complete 30-day forward window | **{m['eligible_decisions']}** (cell 26) |
| Panel rows | {m['panel_rows']:,} (cell 26) |
| Signals passing gate 5 | **{len(passers)} of 13** (cell 30) |
| Clearing forward volatility AND downside | {len(vol_down)} (cell 32) |
| Clearing forward event-concentration excess | **{len(excess_clear)}** (cell 32) |
| Simultaneous critical value, 39 stability hypotheses | {crit['stability_critical']:.4f} on {draws['stability']} complete draws (cell 29) |
| Simultaneous critical value, 13 return hypotheses | {crit['return_critical']:.4f} on {draws['returns']} complete draws (cell 29) |
| Return-clause half-width | {min(hw.values()):.1f} to {max(hw.values()):.1f} pp against a {delta:.0f} pp margin (cell 32) |
| Carried into NB29 | {', '.join(f'`{s}`' for s in m['carried_to_nb29'])} (cell 41) |

## Robustness of results

- **What changed after the review, and what it did.** `simultaneous_ci()` maximised over the
  finite subset of hypotheses in each draw, which is anti-conservative; it now uses
  complete-family draws only ({draws['stability']} of {draws['total']}). `add_one_p()` kept
  non-finite draws in its denominator. `rho_forward_return` carried an inverted sign. The return
  contrast was in annualised log-return points while `delta` is in CAGR points; it is now a
  difference of compounded annual returns. The event-concentration target was bounded below by
  5/n. The calendar-versus-fresh difference was not on a common sample. None of these changed the
  verdict; several changed reported numbers, which is why this heading is generated.
- **A direction in the plan's signal table was wrong and was corrected before the first run.**
  `gain_to_pain_score` is gains over pain mapped to 0..1, so a HIGH value is better; Draft 2
  declared the opposite. Fixed as a factual error about the indicator's definition.
- **Missingness is severe and unevenly distributed (cell 27).** `residual_event_concentration` is
  NaN on {pct(nan['residual_event_concentration']['nan_rate'])} of reads, `fresh_event_concentration`
  on {pct(nan['fresh_event_concentration']['nan_rate'])}, `min_window_sortino` on
  {pct(nan['min_window_sortino']['nan_rate'])}, `ulcer_index_180` on {pct(nan['ulcer_index_180']['nan_rate'])}.
  The complete-case sample differs between signals by construction.
- **The event-concentration target is {int(miss['forward_event_top5_excess']['missing'])/(miss['forward_event_top5_excess']['finite']+miss['forward_event_top5_excess']['missing'])*100:.0f}% missing (cell 26)**,
  for too few positive events or no causal beta. Its null is measured on a sample that
  over-represents frequently-marking vaults.
- **The annualisation is a compounded annual return from a mean 30-day log return.** It is the
  unit `delta` was calibrated in; it should not be read as an achievable rate.
- **The tail contrast is computed on the complete-case screen sample**, so it approximates the
  mechanism's tail rather than reproducing it.
- **`fresh_event_concentration` window spans vary widely (cell 27)**: median {m['spans']['50%']:.0f}
  calendar days, 95th percentile {m['spans']['95%']:.0f}, maximum {m['spans']['max']:.0f}.
- **Snapshot**: `vault-prices.parquet` 254,818,366 bytes, sha256 prefix `3e79966a`. Anchor parity
  holds against `BASELINE` at 1e-5 with all three splices present and none firing (cell 22).
- **What this notebook does not establish.** It does not show these signals are useless - {len(vol_down)}
  of them predict forward volatility and downside with intervals well clear of zero. It shows
  that gate 5 as written was not satisfied on this cohort, because one of its three targets was
  not established by anything tested and its return clause is far wider than its own margin.
"""
out = Path(__file__).parent.parent / "28-research-stability-signal-screen.ipynb"
nb = json.load(open(out))
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"NB28 heading written: {len(passers)}/13 pass; {len(vol_down)} clear vol+downside; {len(excess_clear)} clear excess; "
      f"criticals {crit['stability_critical']:.4f}/{crit['return_critical']:.4f}")
