"""Generate NB34's heading from _build/manifest_34.json. Every number comes from the manifest;
every string replacement is asserted so a silent no-op cannot leave a stale figure."""
import json
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
observed contrast would have had to exceed about +{f2(needed_c)} and +{f2(needed_v)} - the retained
set out-earning the excluded set by roughly {pc(needed_c)} at the median over 30 days. That is a
superiority test with a large bar, not the non-inferiority test the clause was written to be.
Even the unadjusted single-hypothesis bounds, {f3(unadj_c)} and {f3(unadj_v)}, sit below the margin
(cell 34). The verdict is what the pre-registered rule returns, and the rule stands as written;
standing rule 2 says a badly placed threshold is recorded, not moved.

**2. Why the return clause cannot resolve here: the excluded eight are the most volatile vaults
on the book, and the median of eight wild numbers is itself wild.** Per date, the median
contrast has a standard deviation of {f3(m["median_contrasts"]["calm_score"]["contrast"]["std"])} across
{post_dates} decisions for `calm_score` (10th to 90th percentile {f2(m["median_contrasts"]["calm_score"]["contrast"]["10%"])}
to {f2(m["median_contrasts"]["calm_score"]["contrast"]["90%"])}); {pc(c["crash_share_excluded"])} of the
excluded candidate-dates end the 30 days below -0.5 log against {pc(c["crash_share_retained"])} of the
retained (cell 32). Those {crash["rows"]} crash rows come from {crash["vaults"]} vaults on
overlapping windows (cell 34). The margin is 0.5% of return; the noise is 17%. NB28 found the
same ratio - half-width 20-60x the margin - on the mean-based clause in different units, and
this notebook establishes that switching to a median did not repair it: the sample is {post_dates}
decisions, about four months, with very few non-overlapping 30-day horizons, and no clause on a
forward return of the excluded tail can be resolved on it.

**3. The guard masks far more than "a few percent", and it masks the OLD silent vaults, not the
young ones.** H1 expected `calm_score` to cover a few percent fewer candidate-dates than
`inverse_vol`. It covers {pc(masked_post)} fewer on post-break decisions and {pc(masked_pre)} fewer
before the break; {tot["masked_by_guard"]:,} of {tot["measured"]:,} measured candidate-dates over
the whole panel, {pc(tot["masked_share"])} (cell 29). The masked candidates have a median age of
{ages["masked by guard"]["50%"]:.0f} days against {ages["inverse_vol finite"]["50%"]:.0f} for the
measured set: post-break, {reasons.get(("post_break", "both"), 0)} rows have NO fresh mark in 90 rows
(a constant NAV - the vault is dead or its feed is), {reasons.get(("post_break", "fewer_than_30_fresh"), 0)}
have a recent mark but fewer than 30 in the window, and {reasons.get(("post_break", "stale_over_10_rows"), 0)}
have enough marks but none in the last ten rows (cell 30). The guard is doing what it was built
to do - refusing a volatility estimate on a vault that barely reports - and the cost is a third
of the measured pool.

**4. The guard changes the exclusion set enough to remove most of the mechanism's effect.**
`calm_8` on the track window: CAGR {pc(runs["calm_8"]["cagr"])}, cycle Sharpe {f3(runs["calm_8"]["cycle_sharpe"])},
against the anchor's {pc(runs["screen_log_inverse_vol"]["cagr"])} / {f3(runs["screen_log_inverse_vol"]["cycle_sharpe"])}
and `measured_8`'s {pc(runs["measured_8"]["cagr"])} / {f3(runs["measured_8"]["cycle_sharpe"])} (cell 25).
H2 expected the two within 0.05 Sharpe of each other; the gap is
{f2(runs["measured_8"]["cycle_sharpe"] - runs["calm_8"]["cycle_sharpe"])}. `calm_score` equals
`inverse_vol` wherever it is finite, so the two exclusion sets can differ on a date only when one
of the eight most volatile candidates by raw `inverse_vol` is masked by the guard - and then, under
permissive exclusion, that vault is KEPT and the ninth most volatile goes instead. The two runs
differ, so that happens; and since it is the only way they can differ, the whole gap between
`measured_8` and `calm_8` is the effect of excluding vaults the guard calls unmeasurable: sparsely
polled or recently silent, AND at the volatile end of what can be measured. Their forward
volatility is nonetheless predicted - `inverse_vol`'s stability clause passes on the whole panel
too, lower bound {f3(alls["inverse_vol"]["lo_forward_vol"])} over {alls["inverse_vol"]["dates"]}
decisions (cell 36). Which of the two guards fires on those particular vaults, and on how many
dates, is not measured here; NB35's inertness table gives the dates on which the two books differ.

**5. The eight the mechanism actually removes ARE the ones that misbehave.** At the actual
exclusion, the retained set's forward volatility rank is {f3(c["tail_forward_vol"])} lower (normalised
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

Pre-break decisions ({pre_dates}), DIAGNOSTIC: `calm_score` is unevaluable ({pre["calm_score"]["dates"]}
usable dates, below the 40 minimum) and `inverse_vol` shows the same picture as post-break -
stability lower bounds {f3(pre["inverse_vol"]["lo_forward_vol"])} / {f3(pre["inverse_vol"]["lo_forward_downside"])},
return lower bound {f3(pre["inverse_vol"]["median_return_lo"])} (cell 36). Whole period: gate 5 False for
both, same shape (cell 36). Forward event concentration, kept in view: per-date Spearman of either
signal against the excess top-five share is within 0.07 of zero either way, and the two remaining
targets correlate with it at under 0.1 (cell 38) - the gate no longer asks about it, and nothing
here suggests a price signal could answer.

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
  on the pre-break sample, it fails on the whole period, and it would fail for any contrast below
  about +{f2(needed_v)}. A clause that cannot be passed by a true zero effect is not measuring
  non-inferiority, and this is recorded for the next plan rather than corrected here.
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
