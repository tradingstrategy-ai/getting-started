import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_floor import PARAM_ADDITIONS_FLOOR, INDICATOR_ADDITIONS_FLOOR, CELL14_REPLACEMENTS_FLOOR

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()
HARNESS_RULES_V2 = (BUILD_DIR / "harness_rules_v2.py").read_text()
HARNESS_RULES_V3 = (BUILD_DIR / "harness_rules_v3.py").read_text()

HEADING = """# NB34 - coverage and the two-target screen for the volatility tail exclusion

Gate 5 of [RESEARCH-RULES.md](RESEARCH-RULES.md) under amendments A1 and A2 of plan 34: before
the tail-exclusion mechanism is backtested, its signal read at a decision timestamp must
rank-correlate positively across candidates with those vaults' realised forward volatility AND
forward downside variation over the next 30 days, and the median forward return of the
candidates it keeps must not be materially below that of the eight it removes. Evaluated on
decisions from 2026-04-01, the dense-polling regime, only.

**This notebook chooses nothing.** NB28 chose the signal. This screen is run once, on two
signals - `calm_score`, which is `inverse_vol` behind a fresh-mark guard, and `inverse_vol`
itself - for three things: how many candidates each can score and why the guard masks the rest;
whether the gate-5 association holds on the post-break regime with the concentration target
removed; and whether the SPECIFIC eight candidates the mechanism removes are the ones that
misbehave, which a whole-cross-section Spearman does not establish. Verdict DIAGNOSTIC.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb)
for the machinery, [34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md)
Draft 2 for the rules, [02-better-format.ipynb](02-better-format.ipynb) as the anchor.

## Method

Two logging runs, one per signal, each with exclusion fraction zero, so the candidate pool the
trading code actually ranked at each decision is recorded without being changed; both must
reproduce `BASELINE`. Two further runs at the mechanism's real count of eight, so the offline
exclusion used in the tail contrast can be checked against what the engine excluded.

The panel is every (decision, candidate) pair with a complete 30-day forward window. The
actual-exclusion flag is set on the FULL pool from decision-time information before any row is
dropped for a missing outcome, mirroring the splice's sort. Inference is one two-way cluster
bootstrap - 15-decision circular date blocks, vault clusters - with studentised max-T
simultaneous lower bounds over the evaluated family, complete-family draws only. Three families:
stability (2 signals x 2 targets, gated), returns (2 median contrasts, gated at a margin of
-0.005 in 30-day log return), tails at the actual exclusion (2 x 2, diagnostic).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "34-research-calm-score-screen",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_FLOOR},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_FLOOR)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))
cells.append(code(HARNESS_RULES_V2))
cells.append(code(HARNESS_RULES_V3))

cells.append(md("""## Part 0. Provenance, anchor parity, the frozen constants

The content hashes make "the same snapshot as NB28-NB33" a checkable claim. The parity assertion
proves every `decide_trades` splice is inert on the anchor path. The constants are the ones plan
34 froze before this notebook was built.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
display(pd.DataFrame(SIGNALS).set_index("name"))
constants = pd.Series({
    "exclusion_count": EXCLUSION_COUNT, "post_break_start": str(POST_BREAK_START.date()),
    "return_margin_log_30d": RETURN_MARGIN_LOG, "crash_log_return": CRASH_LOG_RETURN,
    "forward_horizon_days": FORWARD_HORIZON_DAYS, "screen_min_dates": SCREEN_MIN_DATES,
    "screen_min_candidates_per_date": SCREEN_MIN_CANDIDATES, "bootstrap_draws": SCREEN_DRAWS,
    "date_block": SCREEN_DATE_BLOCK, "seed": SCREEN_SEED, "simultaneous_min_draws": SIMULTANEOUS_MIN_DRAWS,
    "stability_targets": ", ".join(STABILITY_TARGETS), "return_target": RETURN_TARGET,
}, name="value")
display(constants.to_frame())
'''))

cells.append(md("""## Part 1. Four runs: two logging, two at the real count

The logging runs exclude nobody and must reproduce `BASELINE` exactly; if they do not, logging
itself is changing the decision. The count-8 runs are the plan's centre (`calm_8`) and its
calendar reference (`measured_8`). They are NOT gated here - that is NB35 - but their logs are
what the offline exclusion is checked against.
"""))
cells.append(code('''log_calm = run_and_record("screen_log_calm", "control", **prefilter_overrides("calm_score", fraction=0.0))
display(assert_anchor_parity(log_calm["panel"]))
log_iv = run_and_record("screen_log_inverse_vol", "control", **prefilter_overrides("inverse_vol", fraction=0.0))
display(assert_anchor_parity(log_iv["panel"]))
for entry in (log_calm, log_iv):
    counts = prefilter_exclusion_frame(entry)
    assert int(counts["excluded"].sum()) == 0, f"{entry['label']} excluded candidates; it is not inert"
    print(f"{entry['label']}: {len(entry['prefilter_log'])} decisions logged, 0 excluded")
# The two logging runs saw the same pools, by construction; assert it rather than assume it.
pools_calm = {t: tuple(r["candidate_ids"]) for t, r in log_calm["prefilter_log"].items()}
pools_iv = {t: tuple(r["candidate_ids"]) for t, r in log_iv["prefilter_log"].items()}
assert pools_calm == pools_iv, "the two logging runs recorded different candidate pools"

calm_8 = run_and_record("calm_8", "calm", **prefilter_overrides("calm_score", count=EXCLUSION_COUNT))
measured_8 = run_and_record("measured_8", "measured", **prefilter_overrides("inverse_vol", count=EXCLUSION_COUNT))
display(pd.DataFrame([e["panel"] for e in (log_iv, calm_8, measured_8)])
        .set_index("label")[["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested", "luck_ratio", "top5_gross_share"]].round(4))
'''))

cells.append(md("""## Part 2. The panel, and what each signal can see

Only decisions whose full 30-day forward window is inside the archive are eligible. The
actual-exclusion flag is set per date on the full pool: the eight lowest finite signal values,
ties broken by pair id exactly as the splice does. Two checks follow. The offline signal reads
must equal what the splice read in-trade, per candidate. And on every date where the count-8
run's pool is identical to the logging pool, the offline eight must be the engine's eight.
"""))
cells.append(code('''panel_frame, eligibility = build_screen_panel(log_iv)
display(eligibility.groupby("eligible").agg(decisions=("date", "size"), first=("date", "min"), last=("date", "max")))
panel_frame["regime"] = np.where(panel_frame["date"] >= POST_BREAK_START, "post_break", "pre_break")
pairs_by_id = {pid: strategy_universe.get_pair_by_id(pid) for pid in panel_frame["pair_id"].unique()}
panel_frame["age_days"] = vault_age_days(pairs_by_id, panel_frame)
add_exclusion_flags(panel_frame)

verify_signal_reads(panel_frame, log_calm, "calm_score")
verify_signal_reads(panel_frame, log_iv, "inverse_vol")
flag_check_calm = verify_exclusion_flags(panel_frame, calm_8, "calm_score")
flag_check_iv = verify_exclusion_flags(panel_frame, measured_8, "inverse_vol")
display(missing_reason_table(panel_frame))
print(f"panel rows {len(panel_frame)}; eligible decisions {panel_frame['date'].nunique()}; "
      f"post-break {panel_frame.loc[panel_frame['regime'] == 'post_break', 'date'].nunique()}, "
      f"pre-break {panel_frame.loc[panel_frame['regime'] == 'pre_break', 'date'].nunique()}")
'''))

cells.append(md("""### Coverage

Per decision: how many candidates `inverse_vol` scores, how many `calm_score` scores, and the
difference, which is exactly the set the guard masks. `calm_score` cannot cover more than
`inverse_vol`; the question is how much less, and whether the masked candidates are the young
ones or the silent ones.
"""))
cells.append(code('''coverage = coverage_by_date(panel_frame)
coverage_summary = coverage.groupby("regime").agg(
    decisions=("pool", "size"), pool_mean=("pool", "mean"), inverse_vol_mean=("inverse_vol", "mean"),
    calm_score_mean=("calm_score", "mean"), masked_by_guard_mean=("masked_by_guard", "mean"),
    neither_mean=("neither", "mean"))
coverage_summary["inverse_vol_share"] = coverage_summary["inverse_vol_mean"] / coverage_summary["pool_mean"]
coverage_summary["calm_score_share"] = coverage_summary["calm_score_mean"] / coverage_summary["pool_mean"]
coverage_summary["masked_share_of_measured"] = coverage_summary["masked_by_guard_mean"] / coverage_summary["inverse_vol_mean"]
display(coverage_summary.round(3))
assert int(coverage["calm_only"].sum()) == 0, "calm_score scored a candidate inverse_vol did not; the guard is not a subset"
masked_total = int(coverage["masked_by_guard"].sum())
measured_total = int(coverage["inverse_vol"].sum())
print(f"candidate-dates with finite inverse_vol: {measured_total}; of those masked by the guard: {masked_total} "
      f"({masked_total / measured_total:.1%})")
display(coverage[["pool", "inverse_vol", "calm_score", "masked_by_guard", "neither"]].describe().round(2))
'''))

cells.append(code('''reasons = guard_reasons(panel_frame, pairs_by_id)
if len(reasons):
    display(reasons.groupby(["regime", "reason"]).agg(rows=("address", "size"), vaults=("address", "nunique"),
                                                      age_median=("age_days", "median"),
                                                      fresh_median=("fresh_in_window", "median"),
                                                      stale_median=("rows_since_fresh", "median")).round(1))
    assert not (reasons["reason"] == "unexplained").any(), "a masked candidate satisfies both guards; the reason logic is wrong"
else:
    print("the guard masked nothing")

# Age and fresh-mark distributions: the pool, the measured, the guard-masked, the unmeasured.
frames = {
    "pool": panel_frame,
    "inverse_vol finite": panel_frame[np.isfinite(panel_frame["inverse_vol"])],
    "calm_score finite": panel_frame[np.isfinite(panel_frame["calm_score"])],
    "masked by guard": panel_frame[np.isfinite(panel_frame["inverse_vol"]) & ~np.isfinite(panel_frame["calm_score"])],
    "neither": panel_frame[~np.isfinite(panel_frame["inverse_vol"])],
}
ages = pd.DataFrame({k: v["age_days"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]) for k, v in frames.items()}).T
display(ages.round(0))
'''))

cells.append(md("""## Part 3. The post-break screen - the verdict

Decisions from 2026-04-01 only. The stability family is gated: both targets must clear a
simultaneous lower bound of zero. The return family is gated at the margin: the median
30-day log-return contrast, retained minus excluded at the actual eight, must have a
simultaneous lower bound above -0.005. The crash shares are printed beside it because a median
cannot see a minority of catastrophic outcomes, and the clause does not claim to.
"""))
cells.append(code('''post = panel_frame[panel_frame["regime"] == "post_break"].copy()
print(f"post-break panel: {len(post)} rows over {post['date'].nunique()} decisions "
      f"{post['date'].min().date()} to {post['date'].max().date()}")
screen_post, detail_post, boot_post = run_screen_v3(post)
display(family_summary(detail_post).round(4))
print("\\nstability family (GATED):")
display(screen_post[["rows", "dates", "evaluated", "rho_forward_vol", "lo_forward_vol", "p_forward_vol",
                     "rho_forward_downside", "lo_forward_downside", "p_forward_downside", "stability_clause"]].round(4))
print("\\nreturn clause (GATED) and crash diagnostic:")
display(screen_post[["rho_forward_return", "median_return_contrast", "median_return_se", "median_return_lo",
                     "crash_share_retained", "crash_share_excluded", "excluded_in_sample_mean", "return_clause"]].round(4))
print(f"margin: lower bound must exceed {-RETURN_MARGIN_LOG:+.3f} (30-day log return)")
print("\\ntail contrast at the actual exclusion (DIAGNOSTIC, own simultaneous control):")
display(screen_post[["tail_forward_vol", "tail_lo_forward_vol", "tail_forward_downside", "tail_lo_forward_downside"]].round(4))
print("\\nGATE 5, post-break:")
display(screen_post[["evaluated", "stability_clause", "return_clause", "gate_5"]])
'''))

cells.append(md("""### What the return clause is made of

The per-date median contrasts, so the clause's scale can be checked rather than trusted; the
unadjusted single-hypothesis bounds beside the simultaneous ones; and every crash observation
with its vault, so the diagnostic's provenance is visible. A vault that appears in the crash
list many times on overlapping windows is one event, not many.
"""))
cells.append(code('''def per_date_medians(panel, signal):
    rows = []
    column = exclusion_flag_column(signal)
    usable = panel[np.isfinite(panel[[signal] + SCREEN_TARGETS]).all(axis=1)]
    for date, group in usable.groupby("date"):
        if len(group) < SCREEN_MIN_CANDIDATES:
            continue
        excluded = group[group[column]]
        retained = group[~group[column]]
        if len(excluded) == 0 or len(retained) == 0:
            continue
        rows.append({"date": pd.Timestamp(date), "n": len(group), "n_excluded": len(excluded),
                     "median_retained": float(retained["forward_return"].median()),
                     "median_excluded": float(excluded["forward_return"].median()),
                     "contrast": float(retained["forward_return"].median() - excluded["forward_return"].median()),
                     "mean_contrast": float(retained["forward_return"].mean() - excluded["forward_return"].mean())})
    return pd.DataFrame(rows).set_index("date")

medians = {s: per_date_medians(post, s) for s in SIGNAL_NAMES}
for s in SIGNAL_NAMES:
    print(f"{s}: {len(medians[s])} dates; per-date median contrast:")
    display(medians[s][["n", "n_excluded", "contrast", "mean_contrast"]].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).round(4))

unadj = []
for i, s in enumerate(SIGNAL_NAMES):
    for j, t in enumerate(STABILITY_TARGETS):
        unadj.append({"signal": s, "hypothesis": f"spearman_{t}", "observed": detail_post["stability"]["observed"][i, j],
                      "se": detail_post["stability"]["se"][i, j], "lo_unadjusted": detail_post["stability"]["lower_unadjusted"][i, j],
                      "lo_simultaneous": detail_post["stability"]["lower_simultaneous"][i, j]})
    unadj.append({"signal": s, "hypothesis": "median_return_contrast", "observed": detail_post["returns"]["observed"][i, 0],
                  "se": detail_post["returns"]["se"][i, 0], "lo_unadjusted": detail_post["returns"]["lower_unadjusted"][i, 0],
                  "lo_simultaneous": detail_post["returns"]["lower_simultaneous"][i, 0]})
unadjusted_post = pd.DataFrame(unadj).set_index(["signal", "hypothesis"])
display(unadjusted_post.round(4))

crashes = post[post["forward_return"] < CRASH_LOG_RETURN].copy()
crash_by_vault = crashes.groupby("address").agg(
    rows=("date", "size"), first=("date", "min"), last=("date", "max"), worst=("forward_return", "min"),
    excluded_calm=(exclusion_flag_column("calm_score"), "mean"), excluded_iv=(exclusion_flag_column("inverse_vol"), "mean"),
    calm_finite=("calm_score", lambda s: float(np.isfinite(s).mean())),
    iv_finite=("inverse_vol", lambda s: float(np.isfinite(s).mean()))).sort_values("rows", ascending=False)
print(f"\\ncrash observations (forward 30-day log return < {CRASH_LOG_RETURN}): {len(crashes)} rows, "
      f"{crashes['address'].nunique()} vaults, of {len(post)} post-break rows")
display(crash_by_vault.round(3))
'''))

cells.append(md("""### Can the return clause be passed at all? Two foresight oracles

Standing rule 9: a surprising null must be shown unreachable, not merely unobserved. Two
oracle signals go through the identical machinery on the post-break panel - exclusion flags
set at eight on the full pool, same families, same margin:

- `oracle_vol`: the forward volatility itself plus 5% noise, direction 'high', so the eight
  excluded are the eight that WILL be most volatile. It carries no return information beyond
  what forward volatility carries. If the clause fails for it, the clause fails for a signal
  with essentially zero return cost by construction: the failure is resolution, not cost.
- `oracle_return`: the forward return itself plus 5% noise, direction 'low', so the eight
  excluded are the eight that WILL earn least - among the same pool as `oracle_vol`, rows
  whose forward volatility is finite, so both oracles exclude eight of the same candidates. If the clause passes for it, the machinery can
  pass the clause on this panel, and the bar is simply where finding 1 says it is.

The noise is there because a signal equal to its target has a bootstrap standard error of
exactly zero, which the studentised max-T cannot evaluate. Both are DIAGNOSTIC.
"""))
cells.append(code('''def oracle_return_clause(panel, draws=200, seed=SCREEN_SEED + 1):
    """Two noisy foresight oracles through the v3 screen. Defined here, not in the module, so
    NB35 and NB36, which embed harness_rules_v3.py, stay regenerable."""
    global SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION
    saved = (SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION)
    rng = np.random.default_rng(seed)
    frame = panel.copy()

    def jitter(series):
        scale = 0.05 * float(series.std())
        return series + rng.normal(0.0, scale, len(series))

    # Both oracles are defined on the SAME pool: rows whose forward volatility is finite. The
    # forward return is finite on every row, so an unmasked return oracle would exclude rows
    # that are later dropped for a missing stability target and its complete-case statistic
    # would carry fewer than eight excluded rows (second review).
    measurable = np.isfinite(frame["forward_vol"])
    frame["oracle_vol"] = jitter(frame["forward_vol"]).where(measurable)
    frame["oracle_return"] = jitter(frame["forward_return"]).where(measurable)
    SIGNALS = [
        {"name": "oracle_vol", "direction": "high", "time_base": "foresight", "note": "= forward_vol + noise; no return information"},
        {"name": "oracle_return", "direction": "low", "time_base": "foresight", "note": "= forward_return + noise"},
    ]
    SIGNAL_NAMES = [s["name"] for s in SIGNALS]
    SIGNAL_DIRECTION = {s["name"]: s["direction"] for s in SIGNALS}
    try:
        add_exclusion_flags(frame)
        for name in SIGNAL_NAMES:
            per_date = frame.groupby("date").apply(
                lambda g, n=name: int(g[exclusion_flag_column(n)].sum()) == min(EXCLUSION_COUNT, int(np.isfinite(g[n]).sum())))
            assert bool(per_date.all()), f"{name}: exclusion flags are not min(8, measurable) on every date"
        table, detail, _ = run_screen_v3(frame, draws=draws, seed=seed, verbose=False)
    finally:
        SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION = saved
    return table, detail


oracle, oracle_detail = oracle_return_clause(post)
display(oracle[["rows", "dates", "evaluated", "rho_forward_vol", "lo_forward_vol", "rho_forward_downside", "lo_forward_downside",
                "stability_clause"]].round(4))
display(oracle[["rho_forward_return", "median_return_contrast", "median_return_se", "median_return_lo",
                "crash_share_retained", "crash_share_excluded", "return_clause", "gate_5"]].round(4))
print(f"oracle return family: critical {oracle_detail['returns']['critical']:.4f} on {oracle_detail['returns']['n_draws']} complete draws of 200; "
      f"margin {-RETURN_MARGIN_LOG:+.3f}")
for name in ("oracle_vol", "oracle_return"):
    r = oracle.loc[name]
    print(f"{name:>14}: stability clause {bool(r['stability_clause'])}, median contrast {r['median_return_contrast']:+.4f} "
          f"(se {r['median_return_se']:.4f}, lower bound {r['median_return_lo']:+.4f}), return clause {bool(r['return_clause'])}, "
          f"GATE 5 {bool(r['gate_5'])}")
'''))

cells.append(md("""## Part 4. The pre-break decisions and the whole period - DIAGNOSTIC

Before 2026-04-01 a 30-day forward path is mostly unobserved, so the downside target is not the
quantity the gate names. Screened anyway, and labelled, so the post-break restriction is seen to
be a choice with a visible cost and not a way of hiding an inconvenient regime. The whole-period
screen is the continuity check against NB28's `inverse_vol` row.
"""))
cells.append(code('''pre = panel_frame[panel_frame["regime"] == "pre_break"].copy()
print(f"pre-break panel: {len(pre)} rows over {pre['date'].nunique()} decisions")
screen_pre, detail_pre, _ = run_screen_v3(pre, verbose=False)
print("pre-break (DIAGNOSTIC):")
display(screen_pre[["rows", "dates", "evaluated", "rho_forward_vol", "lo_forward_vol", "rho_forward_downside",
                    "lo_forward_downside", "median_return_contrast", "median_return_lo",
                    "crash_share_retained", "crash_share_excluded", "stability_clause", "return_clause", "gate_5"]].round(4))
print(f"\\nwhole period: {len(panel_frame)} rows over {panel_frame['date'].nunique()} decisions")
screen_all, detail_all, _ = run_screen_v3(panel_frame, verbose=False)
print("whole period (DIAGNOSTIC):")
display(screen_all[["rows", "dates", "evaluated", "rho_forward_vol", "lo_forward_vol", "rho_forward_downside",
                    "lo_forward_downside", "median_return_contrast", "median_return_lo",
                    "crash_share_retained", "crash_share_excluded", "stability_clause", "return_clause", "gate_5"]].round(4))

regimes = pd.DataFrame({
    "post_break (verdict)": screen_post["gate_5"], "pre_break (diag)": screen_pre["gate_5"], "whole (diag)": screen_all["gate_5"]})
display(regimes)
'''))

cells.append(md("""## Part 5. The concentration target, kept in view

Amendment A1 removed forward event concentration from the gate because its measurement is
compromised, not because it does not matter. Descriptive only: the per-date Spearman of each
signal against the excess top-five share on post-break decisions, and the correlation between
the two remaining targets and that share, so the reader can see what the gate no longer asks.
"""))
cells.append(code('''rows = []
for s in SIGNAL_NAMES + ["forward_vol", "forward_downside"]:
    for t in ["forward_event_top5_excess", "forward_event_top5"]:
        values = []
        for _d, group in post.groupby("date"):
            joined = group[[s, t]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(joined) >= SCREEN_MIN_CANDIDATES and joined[s].nunique() > 1 and joined[t].nunique() > 1:
                values.append(joined[s].corr(joined[t], method="spearman"))
        sign = -1.0 if s in SIGNAL_DIRECTION and SIGNAL_DIRECTION[s] == "low" else 1.0
        rows.append({"column": s, "target": t, "dates": len(values), "rows_used": int(np.isfinite(post[[s, t]]).all(axis=1).sum()),
                     "mean_raw_spearman": float(np.mean(values)) if values else np.nan,
                     "signed_stable_end_less_concentrated": (sign * float(np.mean(values))) if values else np.nan})
concentration_diag = pd.DataFrame(rows).set_index(["column", "target"])
display(concentration_diag.round(4))
print("for forward_vol / forward_downside rows the 'signed' column is the raw correlation between two targets, not a signal orientation")
'''))

cells.append(md("""## Part 6. What goes to NB35

The gate-5 verdict per signal, the coverage numbers H1 is written on, and the run panels of the
two count-8 configurations, which NB35 re-runs and gates. Nothing here is a portfolio verdict.
"""))
cells.append(code('''summary = screen_post[["dates", "rows", "evaluated", "stability_clause", "return_clause", "gate_5"]].copy()
summary["role"] = ["centre" if s == "calm_score" else "calendar reference" for s in summary.index]
summary["carried_to_nb35"] = True
display(summary)

import json
from pathlib import Path
manifest = {
    "verdict": "DIAGNOSTIC - a screen, not a result",
    "constants": {k: (v if isinstance(v, (int, float, str)) else str(v)) for k, v in constants.items()},
    "provenance": provenance_record(),
    "eligible_decisions": int(eligibility["eligible"].sum()),
    "logged_decisions": int(len(eligibility)),
    "panel_rows": int(len(panel_frame)),
    "decisions_by_regime": panel_frame.groupby("regime")["date"].nunique().to_dict(),
    "gate_5": {s: bool(screen_post.loc[s, "gate_5"]) for s in SIGNAL_NAMES},
    "stability_clause": {s: bool(screen_post.loc[s, "stability_clause"]) for s in SIGNAL_NAMES},
    "return_clause": {s: bool(screen_post.loc[s, "return_clause"]) for s in SIGNAL_NAMES},
    "screen_post": screen_post.round(6).to_dict(orient="index"),
    "screen_pre": screen_pre.round(6).to_dict(orient="index"),
    "screen_all": screen_all.round(6).to_dict(orient="index"),
    "families_post": family_summary(detail_post).round(6).to_dict(orient="index"),
    "families_pre": family_summary(detail_pre).round(6).to_dict(orient="index"),
    "families_all": family_summary(detail_all).round(6).to_dict(orient="index"),
    "unadjusted_post": unadjusted_post.round(6).reset_index().to_dict(orient="records"),
    "coverage_summary": coverage_summary.round(6).to_dict(orient="index"),
    "coverage_totals": {"measured": measured_total, "masked_by_guard": masked_total,
                        "masked_share": masked_total / measured_total if measured_total else None,
                        "calm_only": int(coverage["calm_only"].sum())},
    "guard_reasons": (reasons.groupby(["regime", "reason"]).size().reset_index(name="rows")
                      .to_dict(orient="records") if len(reasons) else []),
    "ages": ages.round(2).to_dict(orient="index"),
    "median_contrasts": {s: medians[s][["contrast", "mean_contrast"]].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).round(6).to_dict()
                         for s in SIGNAL_NAMES},
    "crashes": {"rows": int(len(crashes)), "vaults": int(crashes["address"].nunique()), "post_rows": int(len(post)),
                "by_vault": crash_by_vault.round(6).reset_index().to_dict(orient="records")},
    "concentration_diagnostic": concentration_diag.round(6).reset_index().to_dict(orient="records"),
    "oracle": oracle.round(6).to_dict(orient="index"),
    "oracle_bootstrap": {"draws": 200, "seed": int(SCREEN_SEED + 1),
                         "return_critical": float(oracle_detail["returns"]["critical"]),
                         "return_complete_draws": int(oracle_detail["returns"]["n_draws"])},
    "missing_reasons": missing_reason_table(panel_frame).to_dict(orient="records"),
    "flag_checks": {"calm_score": {"comparable_dates": int(flag_check_calm["comparable_pool"].sum()), "dates": int(len(flag_check_calm))},
                    "inverse_vol": {"comparable_dates": int(flag_check_iv["comparable_pool"].sum()), "dates": int(len(flag_check_iv))}},
    "runs": {e["label"]: {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else str(v))
                          for k, v in e["panel"].items()} for e in (log_iv, calm_8, measured_8)},
}
Path("_build/manifest_34.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_34.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "34-research-calm-score-screen.ipynb")
