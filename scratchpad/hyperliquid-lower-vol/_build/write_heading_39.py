"""Generate NB39's heading from _build/manifest_39.json; qualitative claims asserted."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "39-research-trimmed-screen-full-history.ipynb"
m = json.loads((HERE / "manifest_39.json").read_text())
m38 = json.loads((HERE / "manifest_38.json").read_text())

P = m["panel"]
SC = m["screens"]
T = {k: SC[k]["table"] for k in SC}
PD = {k: {(r["family"], r["window"], r["trim"]): r for r in SC[k]["paired"]} for k in SC}
BR = m["by_regime"]
OR = m["oracle"]
DR = m["dropped"]
SENS = m["block_sensitivity"]
RC = m["regime_contained_decisions"]
clear45 = [s for s in SENS if SENS[s]["clears_block45"]]
clear90 = [s for s in SENS if SENS[s]["clears_block90"]]
max_shift = max(abs(SENS[s]["lo_block45"] - SENS[s]["lo_block30"]) for s in SENS)
n_full_long = P["decisions"] // m["constants"]["date_block_long"]
n38_dec = m["nb38_reference"]["nb38_decisions"]
COV = {k: SC[k]["coverage"] for k in ("all", "all_block45", "all_block90")}
block_equiv = P["decisions"] / m["constants"]["date_block_long"]
prov = m["provenance"]
WK, TR, DN = "weekly 2025", "transition Jan-Mar 2026", "dense Apr 2026 on"


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pc(x): return f"{x * 100:.1f}%"
def rho(k, s): return T[k][s]["rho_fwd60_sharpe"]
def lo(k, s): return T[k][s]["lo_primary_simultaneous"]
def p(k, s): return T[k][s]["p_primary"]
def r30(k, s): return T[k][s]["rho_fwd30_sharpe"]
def rret(k, s): return T[k][s]["rho_fwd60_return"]
def rvol(k, s): return T[k][s]["rho_fwd60_vol"]


clear_all = [s for s in T["all"] if lo("all", s) > 0]
clear_young = [s for s in T["young"] if lo("young", s) > 0]
clear_old = [s for s in T["old"] if lo("old", s) > 0]
best_all = max(T["all"], key=lambda s: rho("all", s))
assert len(clear_all) >= 10, clear_all
assert len(clear45) >= 6, clear45
assert best_all in ("sharpe180_f10", "sortino180", "sharpe180_f00"), best_all
assert lo("all", "vol180") < 0
assert PD["all"][("ret", 90, 0.1)]["lo_simultaneous_family"] < 0 and PD["all"][("ret", 90, 0.1)]["difference"] > 0.04
assert abs(PD["all"][("ret", 180, 0.1)]["difference"]) < 0.02
assert PD["all"][("sharpe", 90, 0.25)]["difference"] < 0
assert lo(WK, "sharpe180_f00") > 0
assert OR["lo_simultaneous"] > 0
n38 = m["nb38_reference"]["nb38_sharpe180_rho_fwd30_sharpe"]
assert all(abs(c["coverage_first"] - 1.0) < 0.15 and abs(c["coverage_last"] - 1.0) < 0.15 for c in COV.values())

HEADING = f"""# NB39 - trimmed trailing scores on the full archive, in event time

NB38 screened trimmed trailing scores against forward Sharpe on the dense-polling regime only
(from 2026-04-01): about four months, 70 overlapping decisions. This notebook runs the same
question on the whole archive from mid-2025, which means running it on WEEKLY data for most of
its length: through 2025 the archive holds about one mark per vault per week, one every two days
in January-March 2026, and a mark on most days from April (this notebook keeps one last mark
per UTC day, cell 2).

Forward-filling weekly marks to a daily grid and then computing daily statistics is where the
gotchas live, so nothing here is computed on a daily grid. Every score uses observed marks
only: event log returns between consecutive marks inside the window, trimming by a FRACTION of
events rounded up (so a weekly vault with 13 events in 90 days loses 2 or 4 of them and a daily
vault with 90 loses 9 or 23), staleness measured in days since the vault's own last mark, and forward
outcomes that must contain marks near the end of the window. The primary horizon is 60 days
because a 30-day window holds about four weekly marks; the 30-day horizon is kept as a
secondary target. The three polling regimes are screened together and separately.

**Focus is forward Sharpe.** Verdict DIAGNOSTIC: a screen, not a result. No vault is selected,
masked or tuned by name. **Headline: on {P["decisions"]} decisions over a year, trailing risk-adjusted
scores are positively associated with the next 60 days' Sharpe - the 180-day Sharpe and Sortino
lead at rho {f2(rho("all", best_all))}, and {len(clear_all)} of 16 signals clear the computed simultaneous bound with
60-day blocks, {len(clear45)} with 90-day blocks and {len(clear90)} with 180-day blocks - and no trim improvement
is detected.** No block choice is both long enough to cover the 180-day persistence of the
trailing scores and numerous enough for reliable controlled bootstrap inference (the 192
decisions are {block_equiv:.2f} 180-day block-equivalents), so the bounds are the computed figures under
each block choice, not a controlled family-wise result; NB38's four-month, 30-day-horizon screen could not resolve any
of this.

**Based on:** [38-research-trimmed-return-screen.ipynb](38-research-trimmed-return-screen.ipynb)
(machinery and its two reviews), [33-research-lead-comparison.ipynb](33-research-lead-comparison.ipynb)
(the archive density table that defines the regimes). Snapshot `vault-prices.parquet`
{prov["bytes"]:,} bytes, sha256 `{prov["sha256"][:16]}`, last mark {prov["last_mark"][:10]} (cell 2).

## Method

Marks: one per vault per UTC day (the last poll of the day). Events: consecutive marks; event
return = log price ratio; event span = days between them. A candidate at decision T needs, in
the trailing window (T-1-W, T-1] for W in 90 and 180 days, at least 8 event returns (9 marks), a
mark at or before the window start, its first in-window mark within 14 days of that start and
its last mark within 14 days of T-1 (so marks bracket the window and the observed event span is
between W - 28 and W days), and a TVL of at least 7,500 USD at the last mark. Scores per window: return score
(sum of event returns, annualised over W; raw and with the best 10% and 25% of events removed),
Sharpe score (return score over event volatility sqrt(sum r^2 / W x 365), raw and trimmed the
same way), Sortino, event volatility. Forward outcomes over (T, T + H] for H = 60 (primary) and
30: log return from the mark carried at T to the last mark in the window, event volatility,
event Sharpe, log max drawdown on the mark path; a window needs at least 6 (H = 60) or 4
(H = 30) marks and one within 14 days of its end. Panel: {P["rows"]:,} candidate-dates, {P["vaults"]}
vaults, {P["decisions"]} decisions {P["first"]} to {P["last"]}, {pc(P["young_share"])} of rows under 360 days old measured from
the vault's first mark anywhere in the archive (cell 4);
{DR["stale_or_too_few_marks"]:,} candidate-dates dropped as stale or under-marked, {DR["tvl"]:,} for TVL, {DR["forward_marks"]}
for an unobserved forward window (cell 4).
Event returns per 90-day window, median: {BR[WK]["events90_median"]:.0f} in the weekly regime, {BR[TR]["events90_median"]:.0f} in
the transition, {BR[DN]["events90_median"]:.0f} in the dense regime; marks per 60-day forward window {BR[WK]["fwd60_events_median"]:.0f} /
{BR[TR]["fwd60_events_median"]:.0f} / {BR[DN]["fwd60_events_median"]:.0f} (cell 4, decision-date regimes).

Inference as NB38 with one change forced by the horizon: per-date signed Spearman averaged
over dates, one two-way cluster bootstrap of TILED, non-wrapping {m["constants"]["date_block"]}-decision (60-day)
date blocks (a random offset per draw, every decision in exactly one tile, whole tiles resampled
with replacement and never truncated; measured coverage of the first and last block of dates
{f3(COV["all"]["coverage_first"])} and {f3(COV["all"]["coverage_last"])} of the mean against {f3(COV["all"]["coverage_middle"])} for the middle, cell 6) x vault clusters, {m["constants"]["draws"]} draws, seed {m["constants"]["seed"]}, shared across every hypothesis,
studentised max-T simultaneous lower bounds over the 16-signal family on the primary target
(critical {f2(SC["all"]["critical"])}), the same with {m["constants"]["date_block_sensitivity"]}-decision (90-day) tiles (critical
{f2(SC["all_block45"]["critical"])}) and {m["constants"]["date_block_long"]}-decision (180-day) tiles (critical {f2(SC["all_block90"]["critical"])}; the
source tiling is one or two full tiles plus remainders depending on the offset, and a draw
repeats tiles), paired trimmed-minus-raw differences on the same draws
with their own family bound, and a foresight-oracle reachability assertion (lower bound
{f3(OR["lo_simultaneous"])}, cell 8). Regime cohorts contain only decisions whose whole 60-day horizon lies
inside the regime ({", ".join(f"{k}: {v}" for k, v in RC.items())} decisions).

## Key new insights and what did we learn from this experiment?

**1. On a year of data, trailing risk-adjusted scores are positively associated with the next
60 days' Sharpe.** With 60-day blocks, {len(clear_all)} of 16 signals clear the computed simultaneous lower
bound of zero on forward 60-day Sharpe; with 90-day blocks {"the same " + str(len(clear45)) if set(clear45) == set(clear_all) else str(len(clear45))}, and with 180-day
tiles - the longest trailing window, {block_equiv:.2f} block-equivalents in the archive - {len(clear90)} (cell 6). The strongest are
the 180-day Sharpe and Sortino scores: `sharpe180_f10` {f3(rho("all", "sharpe180_f10"))} (bounds
{f3(lo("all", "sharpe180_f10"))} / {f3(SENS["sharpe180_f10"]["lo_block45"])} / {f3(SENS["sharpe180_f10"]["lo_block90"])} at 60 / 90 / 180-day blocks), `sortino180`
{f3(rho("all", "sortino180"))} ({f3(lo("all", "sortino180"))} / {f3(SENS["sortino180"]["lo_block45"])} / {f3(SENS["sortino180"]["lo_block90"])}), `sharpe180_f00`
{f3(rho("all", "sharpe180_f00"))} ({f3(lo("all", "sharpe180_f00"))} / {f3(SENS["sharpe180_f00"]["lo_block45"])} / {f3(SENS["sharpe180_f00"]["lo_block90"])}). The 180-day Sharpe and
Sortino scores correlate with forward RETURN at {f3(min(rret("all", "sharpe180_f00"), rret("all", "sortino180"), rret("all", "sharpe180_f10")))} to
{f3(max(rret("all", "sharpe180_f00"), rret("all", "sortino180"), rret("all", "sharpe180_f10")))} and with 30-day forward Sharpe at {f3(min(r30("all", "sharpe180_f00"), r30("all", "sortino180"), r30("all", "sharpe180_f10")))} to
{f3(max(r30("all", "sharpe180_f00"), r30("all", "sortino180"), r30("all", "sharpe180_f10")))}. NB38 saw {f3(n38)} for the 180-day Sharpe on {n38_dec} decisions at a 30-day horizon and
could not clear a family bound (its manifest values are displayed in cell 6); this screen has three times the
decisions and a horizon that holds enough marks. Going from 60- to 90-day tiles leaves the
passing set {"unchanged" if set(clear45) == set(clear_all) else "at " + str(len(clear45))} and moves individual bounds in both directions by at most
{f3(max_shift)}; the 180-day tiles cover the trailing scores' own persistence but the archive holds only
{block_equiv:.2f} of them, so their bounds are descriptive, not a robustness proof.

**2. No trim improvement is detected under a family bound.** Paired comparisons are MATCHED: raw
and trimmed Spearmans are computed per date on the joint finite mask of both scores and the
target, so a difference is trimming alone (cell 6). The return-score trim at 90 days lifts the
matched correlation from {f3(PD["all"][("ret", 90, 0.1)]["raw_rho_matched"])} to {f3(PD["all"][("ret", 90, 0.1)]["trimmed_rho_matched"])} (difference
{f3(PD["all"][("ret", 90, 0.1)]["difference"])} [{f3(PD["all"][("ret", 90, 0.1)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 0.1)]["ci_hi"])}], add-one p
{f3(PD["all"][("ret", 90, 0.1)]["p_two_sided_add_one"])} alone, simultaneous bound over the 8 paired comparisons
{f3(PD["all"][("ret", 90, 0.1)]["lo_simultaneous_family"])}); at 180 days the difference is {f3(PD["all"][("ret", 180, 0.1)]["difference"])}. As in NB38
the trimmed return score takes on a volatility loading (signed correlation with lower forward
volatility {f3(rvol("all", "ret90_f00"))} raw, {f3(rvol("all", "ret90_f10"))} trimmed) and lands where the raw 180-day
scores already are. The Sharpe-score trim differences are {f3(PD["all"][("sharpe", 90, 0.1)]["difference"])} and
{f3(PD["all"][("sharpe", 180, 0.1)]["difference"])} at 10%, {f3(PD["all"][("sharpe", 90, 0.25)]["difference"])} and
{f3(PD["all"][("sharpe", 180, 0.25)]["difference"])} at 25%, with intervals that include zero (cell 6). The old-cohort
90-day 25% trim reads {f3(PD["old"][("sharpe", 90, 0.25)]["difference"])} [{f3(PD["old"][("sharpe", 90, 0.25)]["ci_lo"])},
{f3(PD["old"][("sharpe", 90, 0.25)]["ci_hi"])}] on its own interval (cell 10), one of several cohort comparisons and
exploratory. Nothing here establishes that trimming helps or harms; it establishes that no
improvement was found.

**3. Regime cohorts with the forward outcome contained in the regime.** The forward 60 days lie
inside the regime; the trailing 180-day score of an early dense-regime decision still reads
pre-April marks, so this is outcome-containment, not a wholly within-regime comparison. Weekly
2025 ({RC.get(WK, 0)} decisions whose whole horizon is in 2025): `sharpe180_f00` {f3(rho(WK, "sharpe180_f00"))} (bound
{f3(lo(WK, "sharpe180_f00"))}), `sortino180` {f3(rho(WK, "sortino180"))}. {"Transition (" + str(RC.get(TR, 0)) + " decisions): `sharpe180_f10` " + f3(rho(TR, "sharpe180_f10")) + " (bound " + f3(lo(TR, "sharpe180_f10")) + ")." if TR in T else "The transition cohort has too few contained decisions to screen (" + str(RC.get(TR, 0)) + ")."}
{"Dense April on (" + str(RC.get(DN, 0)) + " decisions): `sharpe180_f00` " + f3(rho(DN, "sharpe180_f00")) + " (bound " + f3(lo(DN, "sharpe180_f00")) + ")." if DN in T else "The dense cohort has too few contained decisions to screen (" + str(RC.get(DN, 0)) + ")."}
(cell 10). The weekly-regime estimate is the largest. Two readings are consistent with that and
this screen cannot separate them: quality persisted more in 2025's universe (which was
{pc(BR[WK]["young_share"])} under a year old, cell 4), or coarse, irregularly observed returns - a weekly mark is a
snapshot, and the return between two of them is a week's interval return - together with
trailing scores that barely change between marks make trailing and forward scores mechanically
more alike than daily marks would.

**4. Young and old vaults: the 180-day risk-adjusted scores carry over to both; the return
scores only to the young.** Age is measured from the vault's first mark anywhere in the
archive ({pc(P["young_share"])} of rows under 360 days; {pc(m["by_regime"][WK]["young_share"])} in the weekly cohort; cell 4).
Young vaults ({SC["young"]["decisions"]} decisions): `sharpe180_f00` {f3(rho("young", "sharpe180_f00"))} (bound
{f3(lo("young", "sharpe180_f00"))}), `ret90_f10` {f3(rho("young", "ret90_f10"))} (bound {f3(lo("young", "ret90_f10"))}), {len(clear_young)} of 16
clear. Old vaults ({SC["old"]["decisions"]} decisions): `sharpe180_f00` {f3(rho("old", "sharpe180_f00"))} (bound
{f3(lo("old", "sharpe180_f00"))}), `sortino180` {f3(rho("old", "sortino180"))}, and only {len(clear_old)} clear
({", ".join(f"`{s}`" for s in clear_old)}); the return scores sit at {f3(min(rho("old", "ret90_f00"), rho("old", "ret180_f00")))}-{f3(max(rho("old", "ret90_f00"), rho("old", "ret180_f00")))} with
bounds below zero (cell 10). The two are estimates on different samples, not a test of a
difference. The incumbent's 360-day CAGR leg cannot score a vault younger than a year; the
scores that carry over in both cohorts need 180 days.

**5. What this says about the incumbent's ranker.** Its Sortino leg looks back 45 days and its
CAGR leg 360; this screen has no 45-day window, so the leg itself is not tested, but the pattern
is that 180-day risk-adjusted scores ({f3(min(rho("all", "sharpe180_f00"), rho("all", "sortino180")))}-{f3(max(rho("all", "sharpe180_f00"), rho("all", "sortino180")))}) sit
above 90-day ones ({f3(min(rho("all", "sharpe90_f00"), rho("all", "sortino90")))}-{f3(max(rho("all", "sharpe90_f00"), rho("all", "sortino90")))}) and above raw
return scores at either length. That is a lead for a ranker test, not a result: the effect on a
six-name book is what the standing gates measure, and portfolio consequences are not claimed
here.

## Summary of results

Forward 60-day Sharpe screen, all regimes (cell 6): signed Spearman, simultaneous lower bounds
over the 16-signal family with 60-day blocks (critical {f2(SC["all"]["critical"])}) and 90-day blocks (critical
{f2(SC["all_block45"]["critical"])}), unadjusted one-sided add-one p; the forward volatility column is signed so positive =
the score's good end had LOWER forward volatility.

| signal | rho fwd60 Sharpe | bound, 60-d blocks | bound, 90-d blocks | p | rho fwd60 return | rho fwd60 vol | rho fwd30 Sharpe |
|---|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| {s} | {f3(rho('all', s))} | {f3(lo('all', s))} | {f3(SENS[s]['lo_block45'])} | {f3(p('all', s))} | {f3(rret('all', s))} | {f3(rvol('all', s))} | {f3(r30('all', s))} |"
    for s in T["all"]) + f"""

Matched paired trimmed-minus-raw on forward 60-day Sharpe (cell 6; both Spearmans on the joint
finite mask per date): per-comparison 95% intervals and add-one p; simultaneous lower bounds
over each 8-comparison family are all below zero.

| | 10% of events removed | 25% of events removed |
|---|---|---|
""" + "\n".join(
    f"| {fam} score, {W} d | {f3(PD['all'][(fam, W, 0.1)]['difference'])} [{f3(PD['all'][(fam, W, 0.1)]['ci_lo'])}, {f3(PD['all'][(fam, W, 0.1)]['ci_hi'])}] p {f3(PD['all'][(fam, W, 0.1)]['p_two_sided_add_one'])} | {f3(PD['all'][(fam, W, 0.25)]['difference'])} [{f3(PD['all'][(fam, W, 0.25)]['ci_lo'])}, {f3(PD['all'][(fam, W, 0.25)]['ci_hi'])}] p {f3(PD['all'][(fam, W, 0.25)]['p_two_sided_add_one'])} |"
    for fam, W in (("ret", 90), ("ret", 180), ("sharpe", 90), ("sharpe", 180))) + f"""

Per cohort, `sharpe180_f00` on forward 60-day Sharpe (cell 10): weekly 2025
{f3(rho(WK, "sharpe180_f00"))} (bound {f3(lo(WK, "sharpe180_f00"))}){", transition " + f3(rho(TR, "sharpe180_f00")) + " (" + f3(lo(TR, "sharpe180_f00")) + ")" if TR in T else ""}{", dense " + f3(rho(DN, "sharpe180_f00")) + " (" + f3(lo(DN, "sharpe180_f00")) + ")" if DN in T else ""},
young {f3(rho("young", "sharpe180_f00"))} ({f3(lo("young", "sharpe180_f00"))}), old {f3(rho("old", "sharpe180_f00"))} ({f3(lo("old", "sharpe180_f00"))}).

## Robustness of results

- Nothing is computed on a daily grid: scores and outcomes are event-time on observed marks
  inside their windows, eligibility needs a mark within 14 days of T-1 and 8 events in the
  window, forward windows need 6 (60 d) or 4 (30 d) marks and one within 14 days of the end
  (cell 4). A weekly vault's forward outcome is a 60-day return over about nine snapshots, and
  its "Sharpe" is a coarse quantity built from interval returns between them.
- The screen is reachable: a foresight oracle clears the 17-signal bound at
  {f3(OR["lo_simultaneous"])} (cell 8).
- Date blocks are tiled 30-decision (60-day) blocks with a random offset per draw, no wrapping,
  whole tiles never truncated; measured inclusion of the first / last block of dates is
  {f3(COV["all"]["coverage_first"])} / {f3(COV["all"]["coverage_last"])} of the mean at 60-day tiles, {f3(COV["all_block45"]["coverage_first"])} / {f3(COV["all_block45"]["coverage_last"])} at 90,
  {f3(COV["all_block90"]["coverage_first"])} / {f3(COV["all_block90"]["coverage_last"])} at 180 (each end asserted within 0.15 of 1.0), against
  {f3(COV["all"]["coverage_middle"])} / {f3(COV["all_block45"]["coverage_middle"])} / {f3(COV["all_block90"]["coverage_middle"])} for the middle (cell 6). The passing set is {len(clear_all)} / {len(clear45)} / {len(clear90)} across the three. The 180-day tiles
  match the longest trailing window but the archive holds {block_equiv:.2f} of them, so no block choice
  here is both long enough for the dependence and numerous enough for a well-behaved bootstrap;
  the bounds are the computed figures under each choice and are not claimed as controlled
  family-wise evidence.
  {P["decisions"]} decisions over about a year hold roughly six non-overlapping 60-day horizons.
- One bootstrap per screen; the regime and cohort screens are separate samples with separate
  bootstraps and their intervals are not comparable across screens in a paired sense. Regime
  cohorts contain only decisions whose whole horizon lies inside the regime.
- Trimmed scores are ranking transformations, not investable returns; forward max drawdown is
  in log units.
- The panel is the archive, not the incumbent's candidate pool; no portfolio claim is made.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB39 heading written: {len(clear_all)}/16 clear; best {best_all} {rho('all', best_all):.3f}; dense sharpe180 bound {lo(DN, 'sharpe180_f00'):.3f}")
