import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_crossfit import PARAM_ADDITIONS_CROSSFIT, CELL14_REPLACEMENTS_CROSSFIT
from blocks_rules_fixes import INDICATOR_ADDITIONS_RULES_FIXES

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()
HARNESS_RULES_V2 = (BUILD_DIR / "harness_rules_v2.py").read_text()

HEADING = """# NB30 - cross-fitted evaluation of the leading signal

A DIAGNOSTIC. It replaces the combined mechanism the plan's first draft proposed, which was
undefined and would have added a third selection layer on top of two that already share the same
returns.

Five contiguous folds over the decision schedule. For each fold, gate 5 is re-run using only
dates outside that fold **and outside a 30-day purge either side**, the leading signal is
re-chosen from that reduced screen, and the prefilter runs with the fold's own choice active only
during that fold. Stitching the five out-of-fold segments gives one equity path in which no
segment was scored by a screen that saw it.

**This is not a clean out-of-sample test and is not reported as one.** The folds share vaults and
they share a market regime; the purge removes temporal contamination but nothing removes
cross-sectional contamination, because the same 320 vaults appear in every fold. It is the best
this window supports.

The question it answers is narrower and more useful than a performance number: **does the same
signal win in all five folds?** If the leading signal is not stable across folds, the screen is
fitting noise and this notebook says so.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb),
[29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb) and
[28-stable-selection-plan.md](28-stable-selection-plan.md) Draft 2. Full window 2026-01-01 to
2026-09-08.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "30-backtest-stability-crossfit",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_CROSSFIT},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_RULES_FIXES,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_CROSSFIT)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))
cells.append(code(HARNESS_RULES_V2))

cells.append(md("""## Part 0. Provenance, parity, and the activation window

NB30 adds one parameter to the prefilter: an activation window, so the mechanism can be live
during one fold and inert everywhere else. Both ends default to empty, which means "always", so
NB29's runs are unaffected - and the anchor, whose `stability_prefilter_signal` is itself empty,
still never reaches the block at all.
"""))
cells.append(code('''import json
from pathlib import Path

display(provenance())
display(assert_anchor_parity_rules())
record_anchor()

manifest_28 = json.loads(Path("_build/manifest_28.json").read_text())
manifest_29 = json.loads(Path("_build/manifest_29.json").read_text())
CENTRE = float(manifest_29["centre"])
print(f"NB29 centre q = {CENTRE}; shortlisted: {manifest_29['shortlisted'] or 'nothing'}")
print(f"folds {CROSSFIT_FOLDS}, purge {CROSSFIT_PURGE_DAYS} days, "
      f"{CROSSFIT_DRAWS} bootstrap draws per fold screen")
'''))

cells.append(md("""## Part 1. The panel, rebuilt

The screen panel is rebuilt in this kernel rather than loaded, so the fold screens run on exactly
the data this notebook's backtests run on. The logging run must reproduce `BASELINE`, as it did
in NB28.
"""))
cells.append(code('''logging_run = run_and_record("screen_log", "control",
                             **prefilter_overrides("inverse_vol", fraction=0.0))
display(assert_anchor_parity(logging_run["panel"]))
panel_frame, eligibility = build_screen_panel(logging_run)
eligible_dates = sorted(eligibility[eligibility["eligible"]]["date"])
print(f"eligible decisions: {len(eligible_dates)}, "
      f"{eligible_dates[0].date()} to {eligible_dates[-1].date()}")

# The full-sample screen, reproduced here so the fold screens have something to be compared
# against in the same kernel and on the same resamples machinery.
full_bootstrap = joint_cluster_bootstrap(panel_frame, draws=CROSSFIT_DRAWS)
full_screen, full_detail = screen_table(full_bootstrap)
FULL_LEADER = leading_signal(full_screen)
print(f"full-sample leading signal at {CROSSFIT_DRAWS} draws: {FULL_LEADER}")
print(f"NB28 recorded gate-5 passers: {[s for s, v in manifest_28['gate_5'].items() if v] or 'none'}")
display(full_screen[["dates", "stability_clause", "return_clause", "gate_5"]])
'''))

cells.append(md("""## Part 2. Five folds, each with its own screen

Training is WALK-FORWARD: only decisions strictly before the fold, minus a 30-day embargo so no
training decision's forward window reaches into the fold. The first build of this notebook also
used dates AFTER the fold, purged by 30 days - which covers the forward targets and nothing else,
because the signals use trailing windows of 45 to 360 rows and a date after the fold carries the
fold's returns inside its signal values. The review caught that. Walk-forward means the earliest
folds have too little history to screen on and are marked unevaluable rather than screened.

The fold's leading signal is chosen by a rule pre-registered before any fold ran: among gate-5
passers, the one whose WEAKEST simultaneous lower bound across the three stability targets is
largest, ties broken by name. Not the largest correlation: gate 5 requires all three targets, so
the binding evidence for a signal is its weakest leg.
"""))
cells.append(code('''folds = fold_schedule(eligible_dates)
fold_rows = []
for fold in folds:
    training = set(fold["training_dates"])
    if not fold["evaluable"]:
        # Walk-forward: the earliest folds have too little history before them to screen on.
        # They are reported as unevaluable, not screened on a handful of dates.
        fold["screen"], fold["chosen"] = None, None
        fold_rows.append({
            "fold": fold["fold"], "start": fold["start"], "end_inclusive": fold["end_inclusive"],
            "fold_decisions": len(fold["fold_dates"]), "training_decisions": len(fold["training_dates"]),
            "evaluable": False, "gate_5_passers": "(unevaluable)", "leading_signal": "(unevaluable)",
        })
        continue
    subset = panel_frame[panel_frame["date"].isin(training)]
    bootstrap = joint_cluster_bootstrap(subset, draws=CROSSFIT_DRAWS, verbose=False)
    screen, detail = screen_table(bootstrap)
    chosen = leading_signal(screen)
    fold_rows.append({
        "fold": fold["fold"], "start": fold["start"], "end_inclusive": fold["end_inclusive"],
        "fold_decisions": len(fold["fold_dates"]), "training_decisions": len(fold["training_dates"]),
        "evaluable": True,
        "gate_5_passers": ", ".join(s for s in screen.index if bool(screen.loc[s, "gate_5"])) or "(none)",
        "leading_signal": chosen if chosen else "(none)",
    })
    fold["screen"] = screen
    fold["chosen"] = chosen
    print(f"fold {fold['fold']}: {fold['start'].date()} to {fold['end_inclusive'].date()}, "
          f"leader {chosen}")
fold_table = pd.DataFrame(fold_rows).set_index("fold")
display(fold_table)

chosen_signals = [f["chosen"] for f in folds]
distinct = sorted({s for s in chosen_signals if s})
print(f"\\ndistinct leading signals across the five folds: {distinct or 'none'}")
print(f"same signal in every fold: {len(distinct) == 1 and all(chosen_signals)}")
'''))

cells.append(md("""## Part 3. The stitched out-of-fold path

Each fold gets its own backtest, with the prefilter active only during that fold. Before the fold
starts the run is bit-identical to the anchor, so the fold's returns begin from a book the
mechanism did not build - which is what makes the five segments stitchable into one coherent
path.

A fold whose screen chose no signal contributes the anchor's own returns for that segment, and
that is stated rather than hidden: a fold with nothing to run is not evidence for the mechanism.
"""))
cells.append(code('''segments, segment_rows = [], []
for fold in folds:
    start, end = fold["start"], fold["end_exclusive"]
    if fold["chosen"] is None:
        source = run_by_label["anchor"]
        label = ("anchor (fold unevaluable - too little prior history)" if not fold["evaluable"]
                 else "anchor (no signal passed this fold's screen)")
    else:
        label = f"fold{fold['fold']}_{fold['chosen']}"
        source = run_and_record(
            label, "diagnostic",
            **prefilter_overrides(fold["chosen"], fraction=CENTRE),
            stability_prefilter_active_from=str(start.date()),
            stability_prefilter_active_to=str(end.date()),
        )
        active = prefilter_exclusion_frame(source)
        assert len(active) == 0 or (
            active["date"].min() >= start and active["date"].max() < end
        ), f"{label} logged a decision outside its own fold"
        print(f"{label}: {len(active)} decisions inside the fold, "
              f"mean realised exclusion share {active['excluded_share'].mean():.4f}"
              if len(active) else f"{label}: the prefilter never fired inside its fold")
    series = source["cycle_returns"]
    segment = series[(series.index >= start) & (series.index < end)]
    segments.append(segment)
    anchor_segment = anchor_cycle_returns[
        (anchor_cycle_returns.index >= start) & (anchor_cycle_returns.index < end)
    ]
    identical = bool(
        len(segment) == len(anchor_segment)
        and np.allclose(segment.to_numpy(), anchor_segment.to_numpy(), atol=1e-12)
    )
    segment_rows.append({
        "fold": fold["fold"], "source": label, "cycles": len(segment),
        "segment_return": float((1.0 + segment).prod() - 1.0),
        "anchor_segment_return": float((1.0 + anchor_segment).prod() - 1.0),
        "identical_to_anchor": identical,
    })
display(pd.DataFrame(segment_rows).set_index("fold").round(6))
'''))

cells.append(code('''stitched = pd.concat(segments).sort_index()
stitched = stitched[~stitched.index.duplicated()]
anchor_same = anchor_cycle_returns.reindex(stitched.index).dropna()
common = stitched.index.intersection(anchor_same.index)
stitched, anchor_same = stitched.loc[common], anchor_same.loc[common]


def _sharpe(series):
    deviation = series.std(ddof=1)
    return float(series.mean() / deviation * np.sqrt(PERIODS_PER_YEAR)) if deviation > 0 else np.nan


def _cagr(series):
    days = (series.index[-1] - series.index[0]).days
    return float((1.0 + series).prod() ** (365.0 / max(days, 1)) - 1.0)


comparison = pd.DataFrame([
    {"path": "stitched out-of-fold", "cycles": len(stitched), "sharpe": _sharpe(stitched),
     "cagr": _cagr(stitched), "vol": float(stitched.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)),
     "total_return": float((1.0 + stitched).prod() - 1.0)},
    {"path": "anchor, same cycles", "cycles": len(anchor_same), "sharpe": _sharpe(anchor_same),
     "cagr": _cagr(anchor_same), "vol": float(anchor_same.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)),
     "total_return": float((1.0 + anchor_same).prod() - 1.0)},
]).set_index("path")
display(comparison.round(6))

paired = bootstrap_paired_sharpe_diff(stitched, anchor_same)
print(f"paired Sharpe difference (stitched - anchor): {paired['observed']:+.4f}, "
      f"95% interval [{paired['lo']:+.4f}, {paired['hi']:+.4f}] on {paired['n']} cycles")
print("Reported for context. This window cannot resolve Sharpe differences of this size - the "
      "minimum detectable difference is about 2.50 - and the interval is not a gate.")
'''))

cells.append(md("""## Part 4. What the fold instability means

The plan pre-registered what to conclude from this, so the conclusion is not written from the
number after seeing it: **if the leading signal is not stable across folds, the screen is fitting
noise.**

A signal chosen because of which 20% of the window was hidden is a signal chosen by the sample,
not by the vaults.
"""))
cells.append(code('''stability_rows = []
for signal in SIGNAL_NAMES:
    chosen_in = [f["fold"] for f in folds if f["chosen"] == signal]
    passed_in = [f["fold"] for f in folds if f["screen"] is not None and bool(f["screen"].loc[signal, "gate_5"])]
    stability_rows.append({
        "signal": signal,
        "folds_passing_gate_5": len(passed_in),
        "folds_leading": len(chosen_in),
        "leading_in": ", ".join(str(f) for f in chosen_in) or "-",
        "full_sample_gate_5": bool(manifest_28["gate_5"].get(signal, False)),
    })
display(pd.DataFrame(stability_rows).set_index("signal").sort_values(
    ["folds_leading", "folds_passing_gate_5"], ascending=False))

n_distinct = len(distinct)
n_chose = sum(1 for s in chosen_signals if s)
n_evaluable = sum(1 for f in folds if f["evaluable"])
if n_evaluable == 0:
    verdict = "UNEVALUABLE - no fold has enough prior history to screen walk-forward"
elif n_chose == 0:
    verdict = (f"VACUOUS - {n_evaluable} of {len(folds)} folds were evaluable walk-forward and none "
               f"selected any signal, so there is no mechanism to cross-fit and the stitched path "
               f"is the anchor's own")
elif n_chose < len(folds):
    verdict = (f"UNSTABLE - {len(folds) - n_chose} of {len(folds)} folds selected no signal "
               f"at all; the folds that did chose {n_distinct} distinct signal(s)")
elif n_distinct == 1:
    verdict = f"STABLE - {distinct[0]} led in all {len(folds)} folds"
else:
    verdict = f"UNSTABLE - {n_distinct} different signals led across {len(folds)} folds"
print(verdict)

manifest = {
    "verdict": "DIAGNOSTIC",
    "fold_stability": verdict,
    "folds_evaluable": n_evaluable,
    "folds": CROSSFIT_FOLDS, "purge_days": CROSSFIT_PURGE_DAYS, "draws": CROSSFIT_DRAWS,
    "centre": CENTRE,
    "full_sample_leader": FULL_LEADER,
    "fold_table": fold_table.to_dict(orient="index"),
    "segments": pd.DataFrame(segment_rows).set_index("fold").round(6).to_dict(orient="index"),
    "stitched": comparison.round(6).to_dict(orient="index"),
    "paired_sharpe": {k: (float(v) if isinstance(v, (int, float)) else v)
                      for k, v in paired.items()},
    "signal_stability": pd.DataFrame(stability_rows).set_index("signal").to_dict(orient="index"),
    "all_runs": {
        entry["label"]: {
            "family": entry["family"],
            "overrides": {k: (sorted(v) if isinstance(v, (set, frozenset)) else v)
                          for k, v in entry["overrides"].items()},
            "panel": {k: float(entry["panel"][k]) for k in
                      ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd",
                       "abs_invested_beta", "mean_invested")},
        }
        for entry in runs if entry["label"] != "anchor"
    },
}
Path("_build/manifest_30.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_30.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "30-backtest-stability-crossfit.ipynb")
