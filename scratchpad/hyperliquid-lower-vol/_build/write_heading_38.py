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
OR = m["oracle"]
PF = m["paired_family"]
DR = m["dropped"]
PDall = m["screens"]["all"]["paired"]
PDyoung = m["screens"]["young"]["paired"]


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
assert all(r["lo_simultaneous_18"] < 0 for r in PDall) and all(r["lo_simultaneous_18"] < 0 for r in PDyoung), "a paired difference clears the family bound; rewrite finding 2"
assert OR["lo_simultaneous"] > 0
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
beside it. **Verdict: DIAGNOSTIC. No trimmed score is shown to predict forward Sharpe better
than its raw form under a family-wise bound; the trimmed return score's gain, where it appears,
comes with a strong loading on lower forward volatility.**

**The panel is the archive, not the engine's candidate pool.** Every Hypercore vault with at
least the trailing window of history, a TVL of at least 7,500 USD and five price-changing marks
in the window is a candidate on every second day from 2026-04-01 (the polling-density break) to
the last date with a complete 30-day forward window: {P["rows"]:,} candidate-dates, {P["vaults"]} vaults,
{P["decisions"]} decisions to {P["last"]}, {pc(P["young_share"])} of rows under 360 days old (cell 4). Eligibility is
on OBSERVED marks: a candidate needs a real mark within 3 days of T-1 ({DR["no_recent_mark"]:,} candidate-dates
dropped for having none, {DR["tvl"]:,} for TVL) and a forward window needs at least 10 observed marks
with one in its last 3 days ({DR["forward_marks"]} dropped); the median forward window has
{m["forward_marks_median"]:.0f} of 30 days marked. Stratwise Multi-Asset Public ({m["stratwise_age_days"]} days old) and the
other post-July vaults are too young for any forward outcome and are NOT in the screen; they
are shown in a current-snapshot comparison (cell 12). No vault is selected, masked or tuned by name anywhere. Snapshot
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
PAIRED difference trimmed-minus-raw on the primary target, per (window, k), is computed on the
same draws and controlled as its own family of 18 (critical {f2(PF["all"]["critical"])}); per-comparison
intervals and add-one p-values are descriptive. A noisy foresight oracle through the identical
machinery clears the family-wise bound (lower bound {f3(OR["lo_simultaneous"])}, cell 8), so an all-fail
result is a property of the signals, not of the screen.

## Key new insights and what did we learn from this experiment?

**1. Nothing predicts a vault's next-30-day Sharpe well, and a raw trailing return does not
predict it at all.** The best of thirty signals is the raw 180-day Sharpe at rho
{f3(rho("all", "sharpe180_k0"))} (unadjusted add-one p {f3(p("all", "sharpe180_k0"))}); no signal clears the simultaneous
lower bound of zero over the family (best {f3(lo("all", "sharpe180_k5"))}, `sharpe180_k5`), while the foresight
oracle clears it at {f3(OR["lo_simultaneous"])} (cells 6, 8). Raw trailing return over 45 or 90 days is at
{f3(rho("all", "ret45_k0"))} and {f3(rho("all", "ret90_k0"))} - nothing - and every signal's correlation with forward
RETURN is within {f3(max(abs(T["all"][s]["rho_fwd_return"]) for s in T["all"]))} of zero (cell 6). The incumbent's 45-day
Sharpe leg sits at {f3(rho("all", "sharpe45_k0"))}.

**2. Trimming the return score raises its forward-Sharpe correlation, but not by enough to
establish under a family-wise bound, and the gain arrives with a strong low-volatility
loading.** Removing the best 10 of 90 days lifts the return score from {f3(rho("all", "ret90_k0"))} to
{f3(rho("all", "ret90_k10"))}; the paired difference is {f3(PD["all"][("ret", 90, 10)]["difference"])}
[{f3(PD["all"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 10)]["ci_hi"])}], add-one p
{f3(PD["all"][("ret", 90, 10)]["p_two_sided_add_one"])} on its own, but its simultaneous lower bound over the 18 paired
comparisons is {f3(PD["all"][("ret", 90, 10)]["lo_simultaneous_18"])}; at 45 days the difference is
{f3(PD["all"][("ret", 45, 10)]["difference"])} [{f3(PD["all"][("ret", 45, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 10)]["ci_hi"])}] (cell 6). What
the trimmed score correlates with is forward VOLATILITY (signed {f3(T["all"]["ret90_k10"]["rho_fwd_vol"])} against the raw
score's {f3(T["all"]["ret90_k0"]["rho_fwd_vol"])}) and forward drawdown ({f3(T["all"]["ret90_k10"]["rho_fwd_log_max_dd"])}), a profile close
to `vol90`'s own ({f3(T["all"]["vol90"]["rho_fwd_vol"])} / {f3(T["all"]["vol90"]["rho_fwd_log_max_dd"])}, and {f3(rho("all", "vol90"))} on
forward Sharpe), and its correlation with forward return stays at {f3(T["all"]["ret90_k10"]["rho_fwd_return"])}. At the current
snapshot the raw and k = 10 trimmed 90-day return scores rank the cross-section with a Spearman
agreement of {f3(AG[(90, "ret", 10)])} (cell 12): trimming ten of ninety days re-orders the candidates almost
completely. The result is CONSISTENT with the trimmed score being a stability signal rather than
a cleaner return signal; this notebook does not show that it selects the same vaults as a
volatility ranker, and it makes no portfolio claim.

**3. Trimming the Sharpe score shows no detectable improvement.** Raw and trimmed trailing
Sharpe rank the cross-section similarly (agreement {f3(AG[(90, "sharpe", 5)])} at k = 5 on 90 days,
{f3(AG[(180, "sharpe", 3)])} at k = 3 on 180) and their paired differences on forward Sharpe are
{f3(PD["all"][("sharpe", 90, 5)]["difference"])} [{f3(PD["all"][("sharpe", 90, 5)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 5)]["ci_hi"])}] and
{f3(PD["all"][("sharpe", 180, 5)]["difference"])} [{f3(PD["all"][("sharpe", 180, 5)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 5)]["ci_hi"])}] (cell 6): intervals
that straddle zero, which is absence of evidence of a difference, not evidence of none.

**4. The young cohort shows the largest return-trim differences, and they still do not clear
the family bound.** Among vaults under 360 days ({pc(P["young_share"])} of rows), raw 90-day return is
{f3(rho("young", "ret90_k0"))} on forward Sharpe and trimmed k = 10 is {f3(rho("young", "ret90_k10"))}, difference
{f3(PD["young"][("ret", 90, 10)]["difference"])} [{f3(PD["young"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 10)]["ci_hi"])}], add-one p
{f3(PD["young"][("ret", 90, 10)]["p_two_sided_add_one"])}, simultaneous lower bound {f3(PD["young"][("ret", 90, 10)]["lo_simultaneous_18"])} over the cohort's
18 comparisons; among the old ({SC["old"]["rows"]:,} rows, {SC["old"]["decisions"]} dates) every difference is inside
its interval (cell 10). The young and old screens are separate bootstraps on separate samples.

**5. Stratwise, at the snapshot ({m["snapshot_dates"]["45"]}, the last completed UTC day).** At the 45-day
window Stratwise's raw return score is {pc(SW["ret_k0"])} annualised (Sharpe score {f2(SW["sharpe_k0"])}, realised
vol {pc(SW["vol"])}); with its best 5 days removed {pc(SW["ret_k5"])} and with 10 removed {pc(SW["ret_k10"])}, so about
{(1 - SW["ret_k5"] / SW["ret_k0"]) * 100:.0f}% of its 45-day return score is its best five days (cell 12). On the raw return
score it ranks 119 of 221 scorable vaults and on the k = 5 trimmed score 20; on the Sharpe score
13 raw and 16 trimmed (cell 12). Those are snapshot ranks on one window and say nothing about
its forward behaviour: with {m["stratwise_age_days"]} days of history no decision gives it both a trailing
window and a complete forward window.

## Summary of results

Forward-Sharpe screen, all candidates (cell 6): signed Spearman, simultaneous lower bound over
30 signals, unadjusted add-one p; forward volatility column is signed so positive = the score's
good end had LOWER forward volatility.

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

Paired trimmed-minus-raw on forward Sharpe, per-comparison 95% intervals (cell 6; young cohort
cell 10). Simultaneous lower bounds over each 18-comparison family are all below zero.

| | k = 3 | k = 5 | k = 10 |
|---|---|---|---|
| return, 45 d | {f3(PD["all"][("ret", 45, 3)]["difference"])} [{f3(PD["all"][("ret", 45, 3)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 3)]["ci_hi"])}] | {f3(PD["all"][("ret", 45, 5)]["difference"])} [{f3(PD["all"][("ret", 45, 5)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 5)]["ci_hi"])}] | {f3(PD["all"][("ret", 45, 10)]["difference"])} [{f3(PD["all"][("ret", 45, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 45, 10)]["ci_hi"])}] |
| return, 90 d | {f3(PD["all"][("ret", 90, 3)]["difference"])} [{f3(PD["all"][("ret", 90, 3)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 3)]["ci_hi"])}] | {f3(PD["all"][("ret", 90, 5)]["difference"])} [{f3(PD["all"][("ret", 90, 5)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 5)]["ci_hi"])}] | {f3(PD["all"][("ret", 90, 10)]["difference"])} [{f3(PD["all"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 90, 10)]["ci_hi"])}] |
| return, 180 d | {f3(PD["all"][("ret", 180, 3)]["difference"])} [{f3(PD["all"][("ret", 180, 3)]["ci_lo"])}, {f3(PD["all"][("ret", 180, 3)]["ci_hi"])}] | {f3(PD["all"][("ret", 180, 5)]["difference"])} [{f3(PD["all"][("ret", 180, 5)]["ci_lo"])}, {f3(PD["all"][("ret", 180, 5)]["ci_hi"])}] | {f3(PD["all"][("ret", 180, 10)]["difference"])} [{f3(PD["all"][("ret", 180, 10)]["ci_lo"])}, {f3(PD["all"][("ret", 180, 10)]["ci_hi"])}] |
| Sharpe, 90 d | {f3(PD["all"][("sharpe", 90, 3)]["difference"])} [{f3(PD["all"][("sharpe", 90, 3)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 3)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 90, 5)]["difference"])} [{f3(PD["all"][("sharpe", 90, 5)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 5)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 90, 10)]["difference"])} [{f3(PD["all"][("sharpe", 90, 10)]["ci_lo"])}, {f3(PD["all"][("sharpe", 90, 10)]["ci_hi"])}] |
| Sharpe, 180 d | {f3(PD["all"][("sharpe", 180, 3)]["difference"])} [{f3(PD["all"][("sharpe", 180, 3)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 3)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 180, 5)]["difference"])} [{f3(PD["all"][("sharpe", 180, 5)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 5)]["ci_hi"])}] | {f3(PD["all"][("sharpe", 180, 10)]["difference"])} [{f3(PD["all"][("sharpe", 180, 10)]["ci_lo"])}, {f3(PD["all"][("sharpe", 180, 10)]["ci_hi"])}] |
| return, 90 d, young only | {f3(PD["young"][("ret", 90, 3)]["difference"])} [{f3(PD["young"][("ret", 90, 3)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 3)]["ci_hi"])}] | {f3(PD["young"][("ret", 90, 5)]["difference"])} [{f3(PD["young"][("ret", 90, 5)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 5)]["ci_hi"])}] | {f3(PD["young"][("ret", 90, 10)]["difference"])} [{f3(PD["young"][("ret", 90, 10)]["ci_lo"])}, {f3(PD["young"][("ret", 90, 10)]["ci_hi"])}] |

**What this means for the ranker.** The screen does not establish that a trimmed return score
predicts forward Sharpe better than the raw one, and where it looks better the score has taken
on a strong low-volatility loading, so a trimmed-CAGR leg would be closer to a second stability
leg than to a cleaner return leg. The idea stops at the vault level, as the plan for it said it
should if the screen did not clear. The one signal with any persistence into next month's
Sharpe is the 180-day Sharpe itself - weak, and not separable from zero under a family-wise
bound. Portfolio consequences are not claimed here.

## Robustness of results

- The panel is built from the archive with a fixed rule (TVL, history, fresh marks, a recent
  observed mark) and no engine; it is therefore NOT the incumbent's candidate pool (no inclusion
  criteria, quarantine or momentum gate), and its per-date pools are larger
  (~{P["rows"] / P["decisions"]:.0f} candidates). The question asked is about vaults, so that is the right
  population; portfolio consequences are not claimed.
- Eligibility and forward outcomes are on observed marks (cell 4): no candidate is admitted on a
  forward-filled TVL or a stale price, and every forward window in the panel has a real mark in
  its last 3 days and a median of {m["forward_marks_median"]:.0f} marked days of 30. Inside a window a day
  without a mark is still forward-filled to a zero return, which is what the trailing and
  forward series both do.
- The screen is shown reachable: a noisy foresight oracle clears the 31-signal family-wise
  bound at {f3(OR["lo_simultaneous"])} (cell 8).
- Every hypothesis shares one bootstrap; paired differences are differences of the same draws,
  so their intervals are paired intervals, and the 18 paired comparisons carry their own
  simultaneous bound. Per-comparison p-values are add-one corrected and descriptive.
- 70 decisions two days apart over about 138 calendar days, each with a 30-day forward window,
  hold roughly four to five non-overlapping forward horizons; the date-block bootstrap uses
  15-decision blocks, and the intervals reflect that overlap.
- Forward max drawdown is in log units (`fwd_log_max_dd`); ranks are unaffected. Trimmed
  scores are ranking transformations, not investable returns.
- Stratwise's figures are a current snapshot at one window on the last completed UTC day and
  are not evidence about its forward behaviour; the rule against selecting or tuning by name
  is unchanged.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB38 heading written: best signal {best_all} rho {rho('all', best_all):.3f}; ret90 raw {rho('all', 'ret90_k0'):.3f} -> k10 {rho('all', 'ret90_k10'):.3f}")
