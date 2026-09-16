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
best_all = max(T["all"], key=lambda s: rho("all", s))
assert len(clear_all) >= 14, clear_all
assert best_all in ("sharpe180_f10", "sortino180", "sharpe180_f00"), best_all
assert lo("all", "vol180") < 0
assert PD["all"][("ret", 90, 0.1)]["lo_simultaneous_family"] < 0 and PD["all"][("ret", 90, 0.1)]["difference"] > 0.04
assert abs(PD["all"][("ret", 180, 0.1)]["difference"]) < 0.02
assert PD["all"][("sharpe", 90, 0.25)]["difference"] < 0 and PD["old"][("sharpe", 90, 0.25)]["ci_hi"] < 0
assert lo(DN, "sharpe180_f00") < 0 < lo(WK, "sharpe180_f00")
assert OR["lo_simultaneous"] > 0
n38 = m38["screens"]["all"]["table"]["sharpe180_k0"]["rho_fwd_sharpe"]

HEADING = f"""# NB39 - trimmed trailing scores on the full archive, in event time

NB38 screened trimmed trailing scores against forward Sharpe on the dense-polling regime only
(from 2026-04-01): about four months, 70 overlapping decisions. This notebook runs the same
question on the whole archive from mid-2025, which means running it on WEEKLY data for most of
its length: through 2025 the archive holds about one price-changing mark per vault per week,
one every two days in January-March 2026, and fifteen or more a day from April (cell 2).

Forward-filling weekly marks to a daily grid and then computing daily statistics is where the
gotchas live, so nothing here is computed on a daily grid. Every score uses observed marks
only: event log returns between consecutive marks, trimming by a FRACTION of events (so a weekly
vault loses one or three of its thirteen marks in 90 days and a daily vault loses nine or
twenty-two of ninety), staleness measured in days since the vault's own last mark, and forward
outcomes that must contain marks near the end of the window. The primary horizon is 60 days
because a 30-day window holds about four weekly marks; the 30-day horizon is kept as a
secondary target. The three polling regimes are screened together and separately.

**Focus is forward Sharpe.** Verdict DIAGNOSTIC: a screen, not a result. No vault is selected,
masked or tuned by name. **Headline: on {P["decisions"]} decisions over a year, trailing quality
DOES persist into the next 60 days - {len(clear_all)} of 16 signals clear the family-wise bound, led by
the 180-day Sharpe and Sortino at rho {f2(rho("all", best_all))} - and trimming adds nothing to that under
a family bound.** The four-month screen of NB38 could not see this because its horizon was 30
days and its sample a third of the size.

**Based on:** [38-research-trimmed-return-screen.ipynb](38-research-trimmed-return-screen.ipynb)
(machinery and its two reviews), [33-research-lead-comparison.ipynb](33-research-lead-comparison.ipynb)
(the archive density table that defines the regimes). Snapshot `vault-prices.parquet`
{prov["bytes"]:,} bytes, sha256 `{prov["sha256"][:16]}`, last mark {prov["last_mark"][:10]} (cell 2).

## Method

Marks: one per vault per UTC day (the last poll of the day). Events: consecutive marks; event
return = log price ratio; event span = days between them. A candidate at decision T needs, in
the trailing window (T-1-W, T-1] for W in 90 and 180 days, at least 8 marks, its last mark within
14 days of T-1, and a TVL of at least 7,500 USD at that mark. Scores per window: return score
(sum of event returns, annualised over W; raw and with the best 10% and 25% of events removed),
Sharpe score (return score over event volatility sqrt(sum r^2 / W x 365), raw and trimmed the
same way), Sortino, event volatility. Forward outcomes over (T, T + H] for H = 60 (primary) and
30: log return from the mark carried at T to the last mark in the window, event volatility,
event Sharpe, log max drawdown on the mark path; a window needs at least 6 (H = 60) or 4
(H = 30) marks and one within 14 days of its end. Panel: {P["rows"]:,} candidate-dates, {P["vaults"]}
vaults, {P["decisions"]} decisions {P["first"]} to {P["last"]}; {DR["stale_or_too_few_marks"]:,} candidate-dates dropped as
stale or under-marked, {DR["tvl"]:,} for TVL, {DR["forward_marks"]} for an unobserved forward window (cell 4).
Marks per 90-day window, median: {BR[WK]["events90_median"]:.0f} in the weekly regime, {BR[TR]["events90_median"]:.0f} in the
transition, {BR[DN]["events90_median"]:.0f} in the dense regime; marks per 60-day forward window {BR[WK]["fwd60_events_median"]:.0f} /
{BR[TR]["fwd60_events_median"]:.0f} / {BR[DN]["fwd60_events_median"]:.0f} (cell 4).

Inference as NB38: per-date signed Spearman averaged over dates, one two-way cluster bootstrap
(15-decision circular date blocks x vault clusters, {m["constants"]["draws"]} draws, seed {m["constants"]["seed"]}) shared
across every hypothesis, studentised max-T simultaneous lower bounds over the 16-signal family on
the primary target (critical {f2(SC["all"]["critical"])}), paired trimmed-minus-raw differences on the
same draws with their own family bound, and a foresight-oracle reachability assertion (lower
bound {f3(OR["lo_simultaneous"])}, cell 8).

## Key new insights and what did we learn from this experiment?

**1. On a year of data, trailing quality persists into the next 60 days.** {len(clear_all)} of 16 signals
clear the simultaneous lower bound of zero on forward 60-day Sharpe; the only one that does not
is 180-day volatility ({f3(rho("all", "vol180"))}, bound {f3(lo("all", "vol180"))}). The strongest are the 180-day
Sharpe and Sortino scores: `sharpe180_f10` {f3(rho("all", "sharpe180_f10"))} (bound {f3(lo("all", "sharpe180_f10"))}),
`sortino180` {f3(rho("all", "sortino180"))} (bound {f3(lo("all", "sortino180"))}), `sharpe180_f00` {f3(rho("all", "sharpe180_f00"))}
(bound {f3(lo("all", "sharpe180_f00"))}); the raw 90-day return score is the weakest that still clears,
{f3(rho("all", "ret90_f00"))} (bound {f3(lo("all", "ret90_f00"))}) (cell 6). The same scores predict forward RETURN at
{f3(rret("all", "sharpe180_f00"))} to {f3(rret("all", "ret90_f10"))} and 30-day forward Sharpe at {f3(r30("all", "sharpe180_f00"))} to
{f3(r30("all", "sharpe180_f10"))}. NB38 saw {f3(n38)} for the 180-day Sharpe on four months at a 30-day horizon and
could not clear a family bound; this screen has three times the decisions, a horizon that holds
enough marks, and a 2025 regime in which persistence is strongest.

**2. Trimming adds nothing that survives a family bound, and trimming a Sharpe score can hurt.**
The return-score trim at 90 days lifts the correlation from {f3(rho("all", "ret90_f00"))} to
{f3(rho("all", "ret90_f10"))} (paired difference {f3(PD["all"][("ret", 90, 0.1)]["difference"])} [{f3(PD["all"][("ret", 90, 0.1)]["ci_lo"])},
{f3(PD["all"][("ret", 90, 0.1)]["ci_hi"])}], add-one p {f3(PD["all"][("ret", 90, 0.1)]["p_two_sided_add_one"])} alone, family bound
{f3(PD["all"][("ret", 90, 0.1)]["lo_simultaneous_family"])}); at 180 days the difference is {f3(PD["all"][("ret", 180, 0.1)]["difference"])}. As in NB38
the trimmed return score takes on a volatility loading (signed correlation with lower forward
volatility {f3(rvol("all", "ret90_f00"))} raw, {f3(rvol("all", "ret90_f10"))} trimmed) and lands where the raw 180-day
scores already are. Trimming the Sharpe score is flat at 10% ({f3(PD["all"][("sharpe", 90, 0.1)]["difference"])},
{f3(PD["all"][("sharpe", 180, 0.1)]["difference"])}) and negative at 25% ({f3(PD["all"][("sharpe", 90, 0.25)]["difference"])},
{f3(PD["all"][("sharpe", 180, 0.25)]["difference"])}); among old vaults the 90-day 25% trim costs
{f3(PD["old"][("sharpe", 90, 0.25)]["difference"])} [{f3(PD["old"][("sharpe", 90, 0.25)]["ci_lo"])}, {f3(PD["old"][("sharpe", 90, 0.25)]["ci_hi"])}] (cell 10). A
Sharpe score already normalises by the size of its jumps; removing them takes information out.

**3. Persistence is strongest in the weekly regime and weakest in the dense one.** Weekly 2025
({BR[WK]["decisions"]:.0f} decisions, {BR[WK]["rows"]:,.0f} rows): `sharpe180_f00` {f3(rho(WK, "sharpe180_f00"))} (bound
{f3(lo(WK, "sharpe180_f00"))}), `sortino180` {f3(rho(WK, "sortino180"))}, every score but `vol180` clears. Transition
({BR[TR]["decisions"]:.0f} decisions): `sharpe180_f10` {f3(rho(TR, "sharpe180_f10"))} (bound {f3(lo(TR, "sharpe180_f10"))}), most
others just above or just below zero. Dense April on ({BR[DN]["decisions"]:.0f} decisions): `sharpe180_f00`
{f3(rho(DN, "sharpe180_f00"))} with bound {f3(lo(DN, "sharpe180_f00"))} - the NB38 picture, a shade below the line
(cell 10). Two readings are consistent with this and the screen cannot separate them: quality
persisted more in 2025's universe (which was {pc(BR[WK]["young_share"])} under a year old), or weekly marks
smooth the outcome so that trailing and forward scores share the same smoothing. The event-time
construction removes the daily-grid artefact but not the fact that a weekly mark is itself a
week's average.

**4. The young cohort carries it.** Young vaults ({pc(P["young_share"])} of rows, {SC["young"]["decisions"]} decisions):
`sharpe180_f00` {f3(rho("young", "sharpe180_f00"))} (bound {f3(lo("young", "sharpe180_f00"))}), `ret90_f10`
{f3(rho("young", "ret90_f10"))} (bound {f3(lo("young", "ret90_f10"))}). Old vaults ({SC["old"]["decisions"]} decisions):
`sharpe180_f00` {f3(rho("old", "sharpe180_f00"))} (bound {f3(lo("old", "sharpe180_f00"))}), `sortino180`
{f3(rho("old", "sortino180"))}, the return scores below the line (cell 10). The incumbent's 360-day CAGR leg
cannot score a young vault at all; the scores that predict best here need 180 days.

**5. What this says about the incumbent's ranker.** Its Sortino leg looks back 45 days and its
CAGR leg 360; this screen has no 45-day window, so the leg itself is not tested, but the pattern
is that 180-day risk-adjusted scores ({f3(rho("all", "sharpe180_f00"))}-{f3(rho("all", "sortino180"))}) predict better
than 90-day ones ({f3(min(rho("all", "sharpe90_f00"), rho("all", "sortino90")))}-{f3(max(rho("all", "sharpe90_f00"), rho("all", "sortino90")))}), and better than raw return
scores at either length. That is a lead for a ranker test, not a result: the effect on a
six-name book is what the standing gates measure, and portfolio consequences are not claimed
here.

## Summary of results

Forward 60-day Sharpe screen, all regimes (cell 6): signed Spearman, simultaneous lower bound
over the 16-signal family (critical {f2(SC["all"]["critical"])}), unadjusted add-one p; the forward volatility
column is signed so positive = the score's good end had LOWER forward volatility.

| signal | rho fwd60 Sharpe | lower bound | p | rho fwd60 return | rho fwd60 vol | rho fwd30 Sharpe |
|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| {s} | {f3(rho('all', s))} | {f3(lo('all', s))} | {f3(p('all', s))} | {f3(rret('all', s))} | {f3(rvol('all', s))} | {f3(r30('all', s))} |"
    for s in T["all"]) + f"""

Paired trimmed-minus-raw on forward 60-day Sharpe (cell 6): per-comparison 95% intervals and
add-one p; simultaneous lower bounds over each 8-comparison family are all below zero.

| | 10% of events removed | 25% of events removed |
|---|---|---|
""" + "\n".join(
    f"| {fam} score, {W} d | {f3(PD['all'][(fam, W, 0.1)]['difference'])} [{f3(PD['all'][(fam, W, 0.1)]['ci_lo'])}, {f3(PD['all'][(fam, W, 0.1)]['ci_hi'])}] p {f3(PD['all'][(fam, W, 0.1)]['p_two_sided_add_one'])} | {f3(PD['all'][(fam, W, 0.25)]['difference'])} [{f3(PD['all'][(fam, W, 0.25)]['ci_lo'])}, {f3(PD['all'][(fam, W, 0.25)]['ci_hi'])}] p {f3(PD['all'][(fam, W, 0.25)]['p_two_sided_add_one'])} |"
    for fam, W in (("ret", 90), ("ret", 180), ("sharpe", 90), ("sharpe", 180))) + f"""

Per regime and cohort, `sharpe180_f00` on forward 60-day Sharpe (cell 10): weekly 2025
{f3(rho(WK, "sharpe180_f00"))} (bound {f3(lo(WK, "sharpe180_f00"))}), transition {f3(rho(TR, "sharpe180_f00"))} ({f3(lo(TR, "sharpe180_f00"))}),
dense {f3(rho(DN, "sharpe180_f00"))} ({f3(lo(DN, "sharpe180_f00"))}), young {f3(rho("young", "sharpe180_f00"))} ({f3(lo("young", "sharpe180_f00"))}),
old {f3(rho("old", "sharpe180_f00"))} ({f3(lo("old", "sharpe180_f00"))}).

## Robustness of results

- Nothing is computed on a daily grid: scores and outcomes are event-time on observed marks,
  eligibility needs a mark within 14 days of T-1 and 8 marks in the window, forward windows
  need 6 (60 d) or 4 (30 d) marks and one within 14 days of the end (cell 4). Inside those
  rules a weekly mark still averages a week; the forward outcome of a weekly vault is a
  60-day return over about nine marks, and its "Sharpe" is a coarse quantity.
- The screen is reachable: a foresight oracle clears the 17-signal bound at
  {f3(OR["lo_simultaneous"])} (cell 8).
- One bootstrap per screen; the regime and cohort screens are separate samples with separate
  bootstraps and their intervals are not comparable across screens in a paired sense.
- {P["decisions"]} decisions two days apart over about a year, each with a 60-day forward window:
  roughly six non-overlapping horizons; the 15-decision date blocks (30 days) are shorter than
  the horizon, so the bootstrap understates dependence between neighbouring blocks somewhat.
  The simultaneous bounds are still the controlled figures.
- Trimmed scores are ranking transformations, not investable returns; forward max drawdown is
  in log units.
- The panel is the archive, not the incumbent's candidate pool; no portfolio claim is made.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB39 heading written: {len(clear_all)}/16 clear; best {best_all} {rho('all', best_all):.3f}; dense sharpe180 bound {lo(DN, 'sharpe180_f00'):.3f}")
