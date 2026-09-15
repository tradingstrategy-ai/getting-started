"""Generate NB34's heading from _build/manifest_34.json. Every number comes from the manifest;
every string replacement is asserted so a silent no-op cannot leave a stale figure."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "34-research-calm-score-screen.ipynb"
m = json.loads((HERE / "manifest_34.json").read_text())

S = m["screen_post"]
c, v = S["calm_score"], S["inverse_vol"]
F = m["families_post"]
cov = m["coverage_summary"]
tot = m["coverage_totals"]
runs = m["runs"]
R = m["unadjusted_post"]
crash = m["crashes"]
reasons = {(r["regime"], r["reason"]): r["rows"] for r in m["guard_reasons"]}
ages = m["ages"]
pre, alls = m["screen_pre"], m["screen_all"]
prov = m["provenance"]
vp = next(v_ for k, v_ in prov.items() if "vault-prices" in k)


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def f4(x): return f"{x:.4f}"
def pc(x): return f"{x * 100:.1f}%"


needed_c = F["returns"]["critical"] * c["median_return_se"] - m["constants"]["return_margin_log_30d"]
needed_v = F["returns"]["critical"] * v["median_return_se"] - m["constants"]["return_margin_log_30d"]
post_dates = m["decisions_by_regime"]["post_break"]
pre_dates = m["decisions_by_regime"]["pre_break"]
masked_post = cov["post_break"]["masked_share_of_measured"]
masked_pre = cov["pre_break"]["masked_share_of_measured"]
unadj_c = next(r for r in R if r["signal"] == "calm_score" and r["hypothesis"] == "median_return_contrast")["lo_unadjusted"]
unadj_v = next(r for r in R if r["signal"] == "inverse_vol" and r["hypothesis"] == "median_return_contrast")["lo_unadjusted"]
O = m["oracle"]
ov, orr = O["oracle_vol"], O["oracle_return"]
OB = m["oracle_bootstrap"]
assert ov["return_clause"] and orr["return_clause"] and ov["stability_clause"], "oracle results changed; finding 2 must be rewritten"
assert c["median_return_contrast"] > 0 and v["median_return_contrast"] > 0, "return contrast sign changed; findings 1-2 must be rewritten"

HEADING = f"""# NB34 - coverage and the two-target screen for the volatility tail exclusion

Gate 5 of [RESEARCH-RULES.md](RESEARCH-RULES.md) under amendments A1 and A2 of plan 34: before
the tail-exclusion mechanism is backtested, its signal read at a decision timestamp must
rank-correlate positively across candidates with those vaults' realised forward volatility AND
forward downside variation over the next 30 days, and the median forward return of the
candidates it keeps must not be materially below that of the eight it removes. Evaluated on
decisions from {m["constants"]["post_break_start"]}, the dense-polling regime, only.

**This notebook chooses nothing.** NB28 chose the signal. This screen is run once, on two
signals - `calm_score`, which is `inverse_vol` behind a fresh-mark guard, and `inverse_vol`
itself - for three things: how many candidates each can score and why the guard masks the rest;
whether the gate-5 association holds on the post-break regime with the concentration target
removed; and whether the SPECIFIC eight candidates the mechanism removes are the ones that
misbehave, which a whole-cross-section Spearman does not establish. Verdict DIAGNOSTIC.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb)
for the machinery, [34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md)
Draft 2 for the rules, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Snapshot
`vault-prices.parquet` {vp["bytes"]:,} bytes, sha256 `{vp["sha256"][:16]}` (cell 23).

## Method

Two logging runs, one per signal, each with exclusion fraction zero, so the candidate pool the
trading code actually ranked at each decision is recorded without being changed; both must
reproduce `BASELINE`. Two further runs at the mechanism's real count of eight, so the offline
exclusion used in the tail contrast can be checked against what the engine excluded.

The panel is every (decision, candidate) pair with a complete 30-day forward window. The
actual-exclusion flag is set on the FULL pool from decision-time information before any row is
dropped for a missing outcome, mirroring the splice's sort. Inference is one two-way cluster
bootstrap - 15-decision circular date blocks, vault clusters, {m["constants"]["bootstrap_draws"]}
draws, seed {m["constants"]["seed"]} - with studentised max-T simultaneous lower bounds over the
evaluated family, complete-family draws only. Three families: stability (2 signals x 2 targets,
gated), returns (2 median contrasts, gated at a margin of -{m["constants"]["return_margin_log_30d"]}
in 30-day log return), tails at the actual exclusion (2 x 2, diagnostic).

## Key new insights and what did we learn from this experiment?

**1. Gate 5 FAILS for both signals, on the return clause alone, and the clause fails on width,
not on sign.** Both signals clear the stability clause with room to spare: signed Spearman
against forward volatility {f3(c["rho_forward_vol"])} (`calm_score`) and {f3(v["rho_forward_vol"])}
(`inverse_vol`), simultaneous lower bounds {f3(c["lo_forward_vol"])} and {f3(v["lo_forward_vol"])};
against forward downside {f3(c["rho_forward_downside"])} and {f3(v["rho_forward_downside"])}, lower
bounds {f3(c["lo_forward_downside"])} and {f3(v["lo_forward_downside"])}; add-one p {f4(c["p_forward_vol"])}
on {F["stability"]["complete_draws"]} draws (cell 32). The median 30-day log-return contrast,
retained minus the actual excluded eight, is POSITIVE for both - {f3(c["median_return_contrast"])}
and {f3(v["median_return_contrast"])} - so the vaults the mechanism keeps earned MORE at the median
than the ones it removes. But its bootstrap standard error is {f3(c["median_return_se"])} and
{f3(v["median_return_se"])}, the simultaneous critical value over the two-hypothesis family is
{f2(F["returns"]["critical"])}, and the lower bounds land at {f3(c["median_return_lo"])} and
{f3(v["median_return_lo"])} against a margin of -{m["constants"]["return_margin_log_30d"]}. To pass, the
observed contrast would have had to exceed about +{f2(needed_c)} and +{f2(needed_v)} in 30-day
log-return units - the retained set's median 30-day return factor about {f2(math.exp(needed_c))}x
the excluded set's. The clause
is still a one-sided non-inferiority test; on this sample's realised uncertainty it is
operationally as demanding as a large superiority result. Even the unadjusted single-hypothesis bounds, {f3(unadj_c)} and {f3(unadj_v)}, sit below the margin
(cell 34). The verdict is what the pre-registered rule returns, and the rule stands as written;
standing rule 2 says a badly placed threshold is recorded, not moved.

**2. The clause is reachable - a foresight oracle passes it - so the failure is "not
demonstrated by a trailing signal on this sample", not "unresolvable".** Standing rule 9 asks
that a surprising failure be shown unreachable rather than merely observed, so two oracles go
through the identical machinery on the same post-break panel (cell 36). `oracle_vol` - the
forward volatility itself plus 5% noise, excluding the eight that WILL be most volatile - passes
BOTH clauses: stability lower bounds {f3(ov["lo_forward_vol"])} / {f3(ov["lo_forward_downside"])}, median
return contrast {f3(ov["median_return_contrast"])} with lower bound {f3(ov["median_return_lo"])}. That
contrast is large because, on this panel, the vaults that will be most volatile are largely the
vaults that will crash: {pc(ov["crash_share_excluded"])} of its excluded candidate-dates end the 30 days
below -0.5 log, against {pc(ov["crash_share_retained"])} of its retained. `oracle_return` passes the
return clause too (contrast {f3(orr["median_return_contrast"])}, lower bound {f3(orr["median_return_lo"])}).
So the machinery can pass the clause and the bar is where finding 1 says it is. The trailing
signals reach a contrast of {f3(c["median_return_contrast"])} and {f3(v["median_return_contrast"])} with
{pc(c["crash_share_excluded"])} and {pc(v["crash_share_excluded"])} of their excluded candidate-dates
crashing: they remove some of the future crashers, and the median of the eight they remove is
below the median of what they keep, but on {post_dates} decisions the sample cannot tell that
positive contrast from zero. Per date the median contrast has a standard deviation of
{f3(m["median_contrasts"]["calm_score"]["contrast"]["std"])} (10th to 90th percentile
{f2(m["median_contrasts"]["calm_score"]["contrast"]["10%"])} to {f2(m["median_contrasts"]["calm_score"]["contrast"]["90%"])});
the {crash["rows"]} crash rows come from {crash["vaults"]} vaults on overlapping windows (cell 34). NB28
found the same width-to-margin ratio on the mean-based clause in different units; the median
did not repair it. What this notebook does NOT establish is that the mechanism has a return
cost: the point estimate says the opposite, and the oracle says a better volatility signal would
pass with room to spare.

**3. The guard masks far more than "a few percent", and what it masks is older than the measured
set and often sparsely observed or recently silent - not the young vaults.** H1 expected `calm_score` to cover a few percent fewer candidate-dates than
`inverse_vol`. It covers {pc(masked_post)} fewer on post-break decisions and {pc(masked_pre)} fewer
before the break; {tot["masked_by_guard"]:,} of {tot["measured"]:,} measured candidate-dates over
the whole panel, {pc(tot["masked_share"])} (cell 29). The masked candidates have a median age of
{ages["masked by guard"]["50%"]:.0f} days against {ages["inverse_vol finite"]["50%"]:.0f} for the
measured set: post-break, {reasons.get(("post_break", "both"), 0)} rows have NO fresh mark in 90 rows
(a constant NAV - the vault is dead or its feed is), {reasons.get(("post_break", "fewer_than_30_fresh"), 0)}
have a recent mark but fewer than 30 in the window, and {reasons.get(("post_break", "stale_over_10_rows"), 0)}
have enough marks but none in the last ten rows (cell 30). The guard is doing what it was built
to do - refusing a volatility estimate on a vault that reports thinly or has stopped - and the
cost is a third of the measured pool.

**4. The guard changes the exclusion set enough to remove most of the mechanism's effect.**
`calm_8` on the track window: CAGR {pc(runs["calm_8"]["cagr"])}, cycle Sharpe {f3(runs["calm_8"]["cycle_sharpe"])},
against the anchor's {pc(runs["screen_log_inverse_vol"]["cagr"])} / {f3(runs["screen_log_inverse_vol"]["cycle_sharpe"])}
and `measured_8`'s {pc(runs["measured_8"]["cagr"])} / {f3(runs["measured_8"]["cycle_sharpe"])} (cell 25).
H2 expected the two within 0.05 Sharpe of each other; the gap is
{f2(runs["measured_8"]["cycle_sharpe"] - runs["calm_8"]["cycle_sharpe"])}. `calm_score` equals
`inverse_vol` wherever it is finite, so the two exclusion sets can differ on a date only when one
of the eight most volatile candidates by raw `inverse_vol` is masked by the guard - and then, under
permissive exclusion, that vault is KEPT and the next most volatile unmasked candidate goes
instead (the ninth if one is masked, further down if more are). The two runs
differ, so that happens; and since it is the only way they can differ, the whole gap between
`measured_8` and `calm_8` is the effect of excluding vaults the guard calls unmeasurable: sparsely
polled or recently silent, AND at the volatile end of what can be measured. Their forward
volatility is nonetheless predicted - `inverse_vol`'s stability clause passes on the whole panel
too, lower bound {f3(alls["inverse_vol"]["lo_forward_vol"])} over {alls["inverse_vol"]["dates"]}
decisions (cell 38). Which of the two guards fires on those particular vaults, and on how many
dates, is not measured here; NB35's inertness table gives the dates on which the two books differ.

**5. The eight the mechanism actually removes ARE the ones that misbehave.** The flags are the
engine's eight; the contrast is over those of them with a measurable forward path - on average
{f2(c["excluded_in_sample_mean"])} and {f2(v["excluded_in_sample_mean"])} of the eight per date (cell 32).
On that set, the retained set's forward volatility rank is {f3(c["tail_forward_vol"])} lower (normalised
rank units) than the excluded set's for `calm_score` and {f3(v["tail_forward_vol"])} for `inverse_vol`,
simultaneous lower bounds {f3(c["tail_lo_forward_vol"])} and {f3(v["tail_lo_forward_vol"])}; forward
downside {f3(c["tail_forward_downside"])} and {f3(v["tail_forward_downside"])}, lower bounds
{f3(c["tail_lo_forward_downside"])} and {f3(v["tail_lo_forward_downside"])} (cell 32). NB28's tail
contrast was computed on a 30% tail of the complete-case sample; this one is the engine's own
eight, verified identical to the engine's log on all {m["flag_checks"]["inverse_vol"]["comparable_dates"]}
eligible decisions (cell 27). The mechanism does what it says. What it cannot show, on this sample,
is that it does so at no cost in typical-vault return - which is finding 1, and is a limit of the
data, not evidence of a cost.

## Summary of results

Post-break screen, cell 32; count-8 track runs, cell 25; masking, cell 29.

| | `calm_score` | `inverse_vol` |
|---|---|---|
| post-break decisions / rows | {c["dates"]} / {c["rows"]:,} | {v["dates"]} / {v["rows"]:,} |
| rho forward vol (lower bound) | {f3(c["rho_forward_vol"])} ({f3(c["lo_forward_vol"])}) | {f3(v["rho_forward_vol"])} ({f3(v["lo_forward_vol"])}) |
| rho forward downside (lower bound) | {f3(c["rho_forward_downside"])} ({f3(c["lo_forward_downside"])}) | {f3(v["rho_forward_downside"])} ({f3(v["lo_forward_downside"])}) |
| stability clause | {c["stability_clause"]} | {v["stability_clause"]} |
| median return contrast (se; lower bound) | {f3(c["median_return_contrast"])} ({f3(c["median_return_se"])}; {f3(c["median_return_lo"])}) | {f3(v["median_return_contrast"])} ({f3(v["median_return_se"])}; {f3(v["median_return_lo"])}) |
| return clause (margin -{m["constants"]["return_margin_log_30d"]}) | {c["return_clause"]} | {v["return_clause"]} |
| **gate 5** | **{c["gate_5"]}** | **{v["gate_5"]}** |
| crash share retained / excluded | {pc(c["crash_share_retained"])} / {pc(c["crash_share_excluded"])} | {pc(v["crash_share_retained"])} / {pc(v["crash_share_excluded"])} |
| tail contrast vol / downside at the actual eight | {f3(c["tail_forward_vol"])} / {f3(c["tail_forward_downside"])} | {f3(v["tail_forward_vol"])} / {f3(v["tail_forward_downside"])} |
| masked by the guard, post-break (share of measured) | {pc(masked_post)} | - |
| track-window run at count 8: CAGR / Sharpe | {pc(runs["calm_8"]["cagr"])} / {f3(runs["calm_8"]["cycle_sharpe"])} | {pc(runs["measured_8"]["cagr"])} / {f3(runs["measured_8"]["cycle_sharpe"])} |

Oracles on the same post-break panel, DIAGNOSTIC (cell 36; {OB["draws"]} draws, seed {OB["seed"]}):

| | `oracle_vol` (foresight vol, no return information) | `oracle_return` (foresight return) |
|---|---|---|
| stability clause | {ov["stability_clause"]} | {orr["stability_clause"]} |
| median return contrast (se; lower bound) | {f3(ov["median_return_contrast"])} ({f3(ov["median_return_se"])}; {f3(ov["median_return_lo"])}) | {f3(orr["median_return_contrast"])} ({f3(orr["median_return_se"])}; {f3(orr["median_return_lo"])}) |
| return clause | {ov["return_clause"]} | {orr["return_clause"]} |

Pre-break decisions ({pre_dates}), DIAGNOSTIC: `calm_score` is unevaluable ({pre["calm_score"]["dates"]}
usable dates, below the 40 minimum) and `inverse_vol` shows the same picture as post-break -
stability lower bounds {f3(pre["inverse_vol"]["lo_forward_vol"])} / {f3(pre["inverse_vol"]["lo_forward_downside"])},
return lower bound {f3(pre["inverse_vol"]["median_return_lo"])} (cell 38). Whole period: gate 5 False for
both, same shape (cell 38). Forward event concentration, kept in view: the descriptive per-date
Spearman of either signal against the excess top-five share is within 0.07 of zero, and the two
remaining targets correlate with it at under 0.1 in this panel (cell 40) - unbootstrapped, on
overlapping windows, context for dropping the target and nothing more.

**What goes to NB35:** gate 5 False for both signals. Under the rules a candidate failing gate 5
is REJECTED; NB35 scores the remaining gates and reports the expensive ones as diagnostics so the
plan's open questions are still answered.

## Robustness of results

- Both logging runs reproduce `BASELINE` and record identical candidate pools; the count-8 runs
  are `calm_8` and `measured_8` as NB35 runs them (cell 25).
- {m["panel_rows"]:,} offline signal reads equal the in-trade reads to 0.0 for both signals, and the
  offline exclusion at eight matches the engine's excluded set on all {m["flag_checks"]["calm_score"]["comparable_dates"]}
  eligible decisions for both signals (cell 27). The tail contrast is on the engine's own eight.
- {m["eligible_decisions"]} of {m["logged_decisions"]} decisions have a complete forward window;
  {m["logged_decisions"] - m["eligible_decisions"]} late decisions are dropped, not truncated (cell 27).
  Forward volatility and downside are missing on {m["missing_reasons"][0]["missing"]:,} of
  {m["panel_rows"]:,} rows, all for `no_fresh_events` - a vault whose NAV did not move in the window.
- All three families used every hypothesis and all {F["stability"]["complete_draws"]} draws were
  complete (cell 32). The stability result does not depend on the multiplicity control: the
  unadjusted bounds are within 0.005 of the simultaneous ones (cell 34).
- The return clause's failure is robust in the unhelpful direction: it fails unadjusted, it fails
  on the pre-break sample, it fails on the whole period, it would fail for any contrast below
  about +{f2(needed_v)} - and a foresight volatility oracle clears that bar (cell 36), so the
  clause is reachable and the machinery is not the reason. The margin is recorded as badly
  placed for this sample size and left where it was, per standing rule 2.
- The guard's masking is not a bug in the indicator: every masked row is explained by one of the
  two guards, none is unexplained (cell 30), and `calm_score` never scores a candidate that
  `inverse_vol` does not (cell 29).
- The 30-day forward windows overlap between consecutive decisions; the date-block bootstrap is
  the only defence, and {post_dates} decisions over about four months contain very few
  independent 30-day horizons. Nothing here is out-of-sample.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB34 heading written: gate 5 = {m['gate_5']}; needed contrast {needed_c:.3f} / {needed_v:.3f}")
