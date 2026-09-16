"""Generate NB38's heading from _build/manifest_38.json; qualitative claims asserted."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "38-research-trimmed-return-screen.ipynb"
m = json.loads((HERE / "manifest_38.json").read_text())

P = m["panel"]
SC = m["screens"]
T = {k: SC[k]["table"] for k in SC}
PD = {k: {(r["family"], r["window"], r["k"]): r for r in SC[k]["paired"]} for k in SC}
AG = {(r["window"], r["family"], r["k"]): r["spearman_raw_vs_trimmed"] for r in m["snapshot_agreement"]}
SW = m["stratwise"]["45"][0]
prov = m["provenance"]


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pc(x): return f"{x * 100:.1f}%"
def rho(k, s): return T[k][s]["rho_fwd_sharpe"]
def lo(k, s): return T[k][s]["lo_sharpe_simultaneous"]
def p(k, s): return T[k][s]["p_sharpe"]


best_all = max(T["all"], key=lambda s: rho("all", s))
assert best_all == "sharpe180_k0", best_all
assert all(lo("all", s) < 0 for s in T["all"]), "some signal clears the simultaneous bound; rewrite finding 1"
assert rho("all", "ret90_k0") < 0.0 and rho("all", "ret45_k0") < 0.0
assert PD["all"][("ret", 90, 10)]["ci_lo"] > 0 and PD["young"][("ret", 90, 3)]["ci_lo"] > 0
assert abs(PD["all"][("sharpe", 90, 5)]["difference"]) < 0.02 and abs(PD["all"][("sharpe", 180, 5)]["difference"]) < 0.02
assert T["all"]["ret90_k10"]["rho_fwd_vol"] > 0.5 and abs(T["all"]["ret90_k0"]["rho_fwd_vol"]) < 0.15
assert AG[(90, "ret", 10)] < 0.2 and AG[(90, "sharpe", 5)] > 0.8
assert SW["ret_k0"] > SW["ret_k5"] > SW["ret_k10"]

HEADING = f"""# NB38 - trimmed trailing returns as a ranker: a vault-level screen

The track's luck diagnostics say the incumbent's result is carried by a few cycles and a few
names, and that vaults are admitted on trailing returns that may themselves be a few jumps.
This notebook asks the decision-time question directly, on vaults rather than portfolios: does
a trailing return computed with the vault's best k days REMOVED predict its forward 30-day
Sharpe better than the raw trailing return does? If it does not at the vault level, no ranker
built on it can beat the incumbent at the portfolio level, and the idea stops here.

**Focus is forward Sharpe**, not forward return: the operator wants steady profit, and a
trimmed score is expected to cost CAGR. Forward return, volatility and drawdown are reported
beside it. **Verdict: DIAGNOSTIC. Trimming does not make a better return ranker; it turns the
return leg into a volatility ranker, which the incumbent already has.**

**The panel is the archive, not the engine's candidate pool.** Every Hypercore vault with at
least the trailing window of history, a TVL of at least 7,500 USD and five price-changing marks
in the window is a candidate on every second day from 2026-04-01 (the polling-density break) to
the last date with a complete 30-day forward window: {P["rows"]:,} candidate-dates, {P["vaults"]} vaults,
{P["decisions"]} decisions to {P["last"]}, {pc(P["young_share"])} of rows under 360 days old (cell 4). Stratwise
Multi-Asset Public ({m["stratwise_age_days"]} days old) and the other post-July vaults are too young for any
forward outcome and are NOT in the screen; they are shown in a current-snapshot comparison
(cell 10). No vault is selected, masked or tuned by name anywhere. Snapshot
`vault-prices.parquet` {prov["bytes"]:,} bytes, sha256 `{prov["sha256"][:16]}`, last mark {prov["last_mark"][:10]} (cell 2).

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb)
and [34-research-calm-score-screen.ipynb](34-research-calm-score-screen.ipynb) for the
two-way cluster bootstrap and simultaneous bounds, re-implemented here without the engine.

## Method

Signals, read at T-1 over trailing windows of 45, 90 and 180 rows: annualised log return (raw
and with the best 3, 5 and 10 daily log returns removed), annualised Sharpe of daily log returns
(raw and trimmed the same way), Sortino, realised volatility. Direction 'high' for return and
Sharpe scores (higher is better), 'low' for volatility. Targets over (T, T + 30 d]: forward
Sharpe (primary), forward log return, forward volatility, forward max drawdown.

Inference: per date, Spearman across that date's candidates, signed so positive means "the
signal's good end had the better outcome", averaged over dates; one two-way cluster bootstrap
(15-decision circular date blocks x vault clusters, {m["constants"]["draws"]} draws, seed
{m["constants"]["seed"]}) shared across every hypothesis; studentised max-T simultaneous lower bounds
over the family of 30 signals on the primary target (critical value {f2(SC["all"]["critical"])}). The
decisive statistic is the PAIRED difference trimmed-minus-raw on the primary target, per
(window, k), on the same draws.

## Key new insights and what did we learn from this experiment?

**1. Nothing predicts a vault's next-30-day Sharpe well, and a raw trailing return does not
predict it at all.** The best of thirty signals is the raw 180-day Sharpe at rho
{f3(rho("all", "sharpe180_k0"))} (unadjusted p {f3(p("all", "sharpe180_k0"))}); no signal clears the simultaneous
lower bound of zero over the family (best {f3(lo("all", "sharpe180_k0"))}). Raw trailing return over 45 or 90
days is at {f3(rho("all", "ret45_k0"))} and {f3(rho("all", "ret90_k0"))} - nothing - and every signal's correlation
with forward RETURN is within {f3(max(abs(T["all"][s]["rho_fwd_return"]) for s in T["all"]))} of zero (cell 6). A month
of a vault's Sharpe is mostly not in its past. The incumbent's ranker legs (45-day Sharpe,
360-day CAGR) are not in the top of this table either: `sharpe45_k0` sits at
{f3(rho("all", "sharpe45_k0"))}.

**2. Trimming the return leg helps - and the help is volatility, not return.** Removing the
best 10 of 90 days lifts the return signal from {f3(rho("all", "ret90_k0"))} to {f3(rho("all", "ret90_k10"))}
on forward Sharpe; the paired difference is {f3(PD["all"][("ret", 90, 10)]["difference"])}
[{f3(PD["all"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 10)]["ci_hi"])}], p {f3(PD["all"][("ret", 90, 10)]["p_two_sided"])}, and
at 45 days {f3(PD["all"][("ret", 45, 10)]["difference"])} [{f3(PD["all"][("ret", 45, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 10)]["ci_hi"])}] (cell 6).
But look at what the trimmed score correlates with: forward VOLATILITY at
{f3(T["all"]["ret90_k10"]["rho_fwd_vol"])} (raw: {f3(T["all"]["ret90_k0"]["rho_fwd_vol"])}) and forward drawdown at
{f3(T["all"]["ret90_k10"]["rho_fwd_max_dd"])}, exactly the profile of `vol90` itself ({f3(T["all"]["vol90"]["rho_fwd_vol"])} /
{f3(T["all"]["vol90"]["rho_fwd_max_dd"])}, and {f3(rho("all", "vol90"))} on forward Sharpe, the same as the trimmed
return). Removing a vault's best days removes most of what distinguishes a high-return vault
from a low-volatility one: the cross-sectional rank agreement between the raw and the k = 10
trimmed 90-day return at the current snapshot is {f3(AG[(90, "ret", 10)])} (cell 10) - a different
ordering, not a cleaned one. The trimmed return is a low-volatility ranker in disguise, and
NB28-NB37 already established what a volatility ranker does: it predicts forward volatility
(rho 0.7) and forward crashes, and it costs return when used to rank.

**3. Trimming the Sharpe leg does nothing.** Raw and trimmed trailing Sharpe rank the
cross-section almost identically (agreement {f3(AG[(90, "sharpe", 5)])} at k = 5, {f3(AG[(180, "sharpe", 3)])} at k = 3
on 180 days) and predict forward Sharpe identically: paired differences
{f3(PD["all"][("sharpe", 90, 5)]["difference"])} and {f3(PD["all"][("sharpe", 180, 5)]["difference"])} with intervals
straddling zero (cell 6). A Sharpe already divides by the jumps it is made of.

**4. The young cohort is where the return trim "works", for the same reason.** Among vaults
under 360 days ({pc(P["young_share"])} of rows), raw 90-day return is {f3(rho("young", "ret90_k0"))} on forward Sharpe and
trimmed k = 10 is {f3(rho("young", "ret90_k10"))}, difference {f3(PD["young"][("ret", 90, 10)]["difference"])}
[{f3(PD["young"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 10)]["ci_hi"])}], p {f3(PD["young"][("ret", 90, 10)]["p_two_sided"])}; among the
old ({SC["old"]["rows"]:,} rows, {SC["old"]["decisions"]} dates) every difference is inside its interval (cell 8). Young
vaults are where a few jumps most dominate a trailing return, so trimming re-orders them most -
towards low volatility.

**5. Stratwise, at the snapshot.** At the 45-day window on {m["snapshot_dates"]["45"]}, Stratwise's raw
annualised return is {pc(SW["ret_k0"])} (Sharpe {f2(SW["sharpe_k0"])}, realised vol {pc(SW["vol"])}); with its
best 5 days removed {pc(SW["ret_k5"])} and with 10 removed {pc(SW["ret_k10"])} - about {(1 - SW["ret_k5"] / SW["ret_k0"]) * 100:.0f}% of its
45-day return is its best five days (cell 10). That is not unusual for the cohort, which is the point:
trimming demotes everyone, and on trimmed return Stratwise RISES from rank 122 to 18 of 220
because its peers are more concentrated still, while on Sharpe it sits at rank 13 raw and 17
trimmed. It cannot be screened for forward behaviour yet: {m["stratwise_age_days"]} days of history give no
decision with both a trailing window and a complete forward window.

## Summary of results

Forward-Sharpe screen, all candidates (cell 6): signed Spearman, simultaneous lower bound over
30 signals, unadjusted add-one p.

| signal | rho fwd Sharpe | lower bound | p | rho fwd return | rho fwd vol (signed) |
|---|---|---|---|---|---|
| ret45 raw / k3 / k5 / k10 | {f3(rho("all", "ret45_k0"))} / {f3(rho("all", "ret45_k3"))} / {f3(rho("all", "ret45_k5"))} / {f3(rho("all", "ret45_k10"))} | {f3(lo("all", "ret45_k10"))} (k10) | {f3(p("all", "ret45_k10"))} | {f3(T["all"]["ret45_k10"]["rho_fwd_return"])} | {f3(T["all"]["ret45_k0"]["rho_fwd_vol"])} -> {f3(T["all"]["ret45_k10"]["rho_fwd_vol"])} |
| ret90 raw / k3 / k5 / k10 | {f3(rho("all", "ret90_k0"))} / {f3(rho("all", "ret90_k3"))} / {f3(rho("all", "ret90_k5"))} / {f3(rho("all", "ret90_k10"))} | {f3(lo("all", "ret90_k10"))} (k10) | {f3(p("all", "ret90_k10"))} | {f3(T["all"]["ret90_k10"]["rho_fwd_return"])} | {f3(T["all"]["ret90_k0"]["rho_fwd_vol"])} -> {f3(T["all"]["ret90_k10"]["rho_fwd_vol"])} |
| ret180 raw / k10 | {f3(rho("all", "ret180_k0"))} / {f3(rho("all", "ret180_k10"))} | {f3(lo("all", "ret180_k0"))} | {f3(p("all", "ret180_k0"))} | {f3(T["all"]["ret180_k0"]["rho_fwd_return"])} | {f3(T["all"]["ret180_k0"]["rho_fwd_vol"])} -> {f3(T["all"]["ret180_k10"]["rho_fwd_vol"])} |
| sharpe45 raw / k5 | {f3(rho("all", "sharpe45_k0"))} / {f3(rho("all", "sharpe45_k5"))} | {f3(lo("all", "sharpe45_k0"))} | {f3(p("all", "sharpe45_k0"))} | {f3(T["all"]["sharpe45_k0"]["rho_fwd_return"])} | {f3(T["all"]["sharpe45_k0"]["rho_fwd_vol"])} |
| sharpe90 raw / k5 | {f3(rho("all", "sharpe90_k0"))} / {f3(rho("all", "sharpe90_k5"))} | {f3(lo("all", "sharpe90_k0"))} | {f3(p("all", "sharpe90_k0"))} | {f3(T["all"]["sharpe90_k0"]["rho_fwd_return"])} | {f3(T["all"]["sharpe90_k0"]["rho_fwd_vol"])} |
| **sharpe180 raw / k5** | **{f3(rho("all", "sharpe180_k0"))} / {f3(rho("all", "sharpe180_k5"))}** | {f3(lo("all", "sharpe180_k0"))} | {f3(p("all", "sharpe180_k0"))} | {f3(T["all"]["sharpe180_k0"]["rho_fwd_return"])} | {f3(T["all"]["sharpe180_k0"]["rho_fwd_vol"])} |
| sortino 45 / 90 / 180 | {f3(rho("all", "sortino45"))} / {f3(rho("all", "sortino90"))} / {f3(rho("all", "sortino180"))} | {f3(lo("all", "sortino180"))} (180) | {f3(p("all", "sortino180"))} | {f3(T["all"]["sortino180"]["rho_fwd_return"])} | {f3(T["all"]["sortino180"]["rho_fwd_vol"])} |
| vol 45 / 90 / 180 (low is good) | {f3(rho("all", "vol45"))} / {f3(rho("all", "vol90"))} / {f3(rho("all", "vol180"))} | {f3(lo("all", "vol45"))} (45) | {f3(p("all", "vol45"))} | {f3(T["all"]["vol45"]["rho_fwd_return"])} | {f3(T["all"]["vol45"]["rho_fwd_vol"])} |

Paired trimmed-minus-raw on forward Sharpe (cell 6; young cohort cell 8):

| | k = 3 | k = 5 | k = 10 |
|---|---|---|---|
| return, 45 d | {f3(PD["all"][("ret", 45, 3)]["difference"])} [{f3(PD["all"][("ret", 45, 3)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 3)]["ci_hi"])}] | {f3(PD["all"][("ret", 45, 5)]["difference"])} [{f3(PD["all"][("ret", 45, 5)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 5)]["ci_hi"])}] | {f3(PD["all"][("ret", 45, 10)]["difference"])} [{f3(PD["all"][("ret", 45, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 10)]["ci_hi"])}] |
| return, 90 d | {f3(PD["all"][("ret", 90, 3)]["difference"])} [{f3(PD["all"][("ret", 90, 3)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 3)]["ci_hi"])}] | {f3(PD["all"][("ret", 90, 5)]["difference"])} [{f3(PD["all"][("ret", 90, 5)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 5)]["ci_hi"])}] | {f3(PD["all"][("ret", 90, 10)]["difference"])} [{f3(PD["all"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 10)]["ci_hi"])}] |
| return, 180 d | {f3(PD["all"][("ret", 180, 3)]["difference"])} [{f3(PD["all"][("ret", 180, 3)]["ci_lo"])}, {f3(PD["all"][("ret", 180, 3)]["ci_hi"])}] | {f3(PD["all"][("ret", 180, 5)]["difference"])} [{f3(PD["all"][("ret", 180, 5)]["ci_lo"])}, {f3(PD["all"][("ret", 180, 5)]["ci_hi"])}] | {f3(PD["all"][("ret", 180, 10)]["difference"])} [{f3(PD["all"][("ret", 180, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 180, 10)]["ci_hi"])}] |
| Sharpe, 90 d | {f3(PD["all"][("sharpe", 90, 3)]["difference"])} [{f3(PD["all"][("sharpe", 90, 3)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 3)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 90, 5)]["difference"])} [{f3(PD["all"][("sharpe", 90, 5)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 5)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 90, 10)]["difference"])} [{f3(PD["all"][("sharpe", 90, 10)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 10)]["ci_hi"])}] |
| Sharpe, 180 d | {f3(PD["all"][("sharpe", 180, 3)]["difference"])} [{f3(PD["all"][("sharpe", 180, 3)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 3)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 180, 5)]["difference"])} [{f3(PD["all"][("sharpe", 180, 5)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 5)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 180, 10)]["difference"])} [{f3(PD["all"][("sharpe", 180, 10)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 10)]["ci_hi"])}] |
| return, 90 d, young only | {f3(PD["young"][("ret", 90, 3)]["difference"])} [{f3(PD["young"][("ret", 90, 3)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 3)]["ci_hi"])}] | {f3(PD["young"][("ret", 90, 5)]["difference"])} [{f3(PD["young"][("ret", 90, 5)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 5)]["ci_hi"])}] | {f3(PD["young"][("ret", 90, 10)]["difference"])} [{f3(PD["young"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 10)]["ci_hi"])}] |

**What this means for the ranker.** A trimmed-CAGR leg would not be a cleaner return leg; it
would be a second volatility leg beside the Sortino and the inverse-variance sizer, and NB32 and
NB37 have shown what ranking on stability does to return. The idea stops here, as the plan for
it said it should. The one signal with any persistence into next month's Sharpe is the 180-day
Sharpe itself - weak, and not separable from zero under a family-wise bound.

## Robustness of results

- The panel is built from the archive with a fixed rule (TVL, history, fresh marks) and no
  engine; it is therefore NOT the incumbent's candidate pool (no inclusion criteria, quarantine
  or momentum gate), and its per-date pools are larger (~{P["rows"] / P["decisions"]:.0f} candidates). The
  question asked is about vaults, so that is the right population; portfolio consequences are
  not claimed.
- Forward Sharpe is computed on 30 daily log returns of forward-filled marks; on post-break
  polling (15-17 marks a day) a zero-return day is a real flat day, not a gap, which is why the
  screen is restricted to decisions from 2026-04-01.
- Every hypothesis shares one bootstrap; paired differences are differences of the same draws,
  so their intervals are paired intervals. Simultaneous bounds are over the 30-signal family on
  the primary target only; the other targets are descriptive.
- 70 decisions of overlapping 30-day windows are about two independent months; the intervals
  say so. The young cohort's return-trim result (p 0.02) is the strongest single finding and it
  is explained by the volatility loading, not by cleaner return information.
- Stratwise's figures are a current snapshot at one window and are not evidence about its
  forward behaviour; the rule against selecting or tuning by name is unchanged.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB38 heading written: best signal {best_all} rho {rho('all', best_all):.3f}; ret90 raw {rho('all', 'ret90_k0'):.3f} -> k10 {rho('all', 'ret90_k10'):.3f}")
