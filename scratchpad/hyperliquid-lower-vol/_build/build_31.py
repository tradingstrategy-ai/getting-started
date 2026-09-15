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

HEADING = """# NB31 - close-out, and the frozen prospective specification

Re-runs every configuration NB29 and NB30 executed, in ONE kernel on ONE snapshot, re-derives
every gate from scratch, and cross-checks each run against the manifest it was first recorded in
at 1e-9. A plan's results are only as good as their reproducibility across kernels, and this
track has twice found a figure that moved when it should not have.

**The deliverable is a specification, not a result.** Nothing in NB28-NB31 is adopted, and ADOPT
is not in this batch's vocabulary. The screen chose signals using 30-day forward windows and the
backtests judged portfolios on returns that overlap the same windows; procedural ordering does not
make that out-of-sample, and 126 decisions with a minimum detectable Sharpe difference near 2.50
cannot be split or purged into resolving it. What this notebook produces is a frozen prospective
specification: which signal, which `q`, strict or permissive, the fixed comparator, the monitoring
horizon, the stopping rule, and the literal override dictionary - fixed before new data arrive.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb),
[29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb),
[30-backtest-stability-crossfit.ipynb](30-backtest-stability-crossfit.ipynb) and
[28-stable-selection-plan.md](28-stable-selection-plan.md) Draft 3.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "31-backtest-stability-closeout",
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

cells.append(md("""## Part 0. Provenance and the three manifests

If the data snapshot moved between NB28 and here, the screen does not describe this kernel's
universe and every cross-check below is comparing two different experiments. The hashes are
printed so that is visible rather than assumed.
"""))
cells.append(code('''import json
from pathlib import Path

display(provenance())
display(assert_anchor_parity_rules())
record_anchor()

manifest_28 = json.loads(Path("_build/manifest_28.json").read_text())
manifest_29 = json.loads(Path("_build/manifest_29.json").read_text())
manifest_30 = json.loads(Path("_build/manifest_30.json").read_text())
GATE_5 = {k: bool(v) for k, v in manifest_28["gate_5"].items()}
CARRIED = list(manifest_29["carried"])
CENTRE = float(manifest_29["centre"])
NEIGHBOURS = tuple(manifest_29["neighbours"])
print(f"delta {manifest_28['delta_annualised_pp']} annualised pp; "
      f"eligible decisions {manifest_28['eligible_decisions']}")
print(f"gate-5 passers: {[s for s, v in GATE_5.items() if v] or 'none'}")
print(f"NB29 shortlisted: {manifest_29['shortlisted'] or 'nothing'}")
print(f"NB30 fold stability: {manifest_30['fold_stability']}")
'''))

cells.append(md("""## Part 1. Re-run everything, and cross-check at 1e-9

Every configuration both notebooks executed, reconstructed from the overrides they recorded
rather than from a hand-copied list, so a run cannot be silently left out of the close-out it
should have been re-checked in.

`__lovo` runs carry a `masked` set; it is restored as a set so the leave-one-vault-out
re-simulation masks the same vault it did the first time.
"""))
cells.append(code('''def _restore(overrides: dict) -> dict:
    out = dict(overrides)
    if "masked" in out:
        out["masked"] = set(out["masked"])
    return out


recorded = {}
for source, manifest in (("NB29", manifest_29), ("NB30", manifest_30)):
    for label, record in manifest["all_runs"].items():
        if label in recorded:
            # Both notebooks run `screen_log`; assert they ran it identically rather than
            # letting one silently overwrite the other's overrides.
            assert recorded[label]["overrides"] == record["overrides"], \\
                f"{label} was run with different overrides in NB29 and NB30"
            continue
        recorded[label] = {**record, "source": source}
print(f"configurations to reproduce: {len(recorded)}")

check_rows = []
for label in sorted(recorded):
    record = recorded[label]
    entry = run_and_record(label, record["family"], **_restore(record["overrides"]))
    row = {"label": label, "source": record["source"], "family": record["family"]}
    worst = 0.0
    for metric, expected in record["panel"].items():
        actual = float(entry["panel"][metric])
        row[metric] = actual
        worst = max(worst, abs(actual - float(expected)))
    row["worst_abs_diff"] = worst
    row["reproduces"] = bool(worst <= 1e-9)
    check_rows.append(row)
crosscheck = pd.DataFrame(check_rows).set_index("label")
display(crosscheck[["source", "family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer",
                    "worst_abs_diff", "reproduces"]].round(9))
failures = crosscheck[~crosscheck["reproduces"]]
if len(failures):
    print(f"\\n{len(failures)} configuration(s) did NOT reproduce at 1e-9:")
    display(failures[["source", "worst_abs_diff"]])
else:
    print(f"\\nall {len(crosscheck)} configurations reproduce at 1e-9 across kernels")
'''))

cells.append(md("""## Part 1b. Gate 5, re-derived

The first build of this notebook imported gate 5 from NB28's manifest and called every gate
"re-derived"; the review caught it. Here the screen panel is rebuilt from this kernel's own
logging run, the joint bootstrap and simultaneous bounds are recomputed, and the resulting gate-5
flags are compared with NB28's before anything downstream uses them.
"""))
cells.append(code('''panel_frame, eligibility = build_screen_panel(run_by_label["screen_log"])
bootstrap = joint_cluster_bootstrap(panel_frame)
screen, detail = screen_table(bootstrap)
GATE_5_REDERIVED = {s: bool(screen.loc[s, "gate_5"]) for s in SIGNAL_NAMES}
comparison = pd.DataFrame({
    "nb28": pd.Series(GATE_5), "here": pd.Series(GATE_5_REDERIVED),
    "nb28_lo_vol": {s: manifest_28["screen"][s]["lo_forward_vol"] for s in SIGNAL_NAMES},
    "here_lo_vol": screen["lo_forward_vol"],
    "nb28_return_lo": {s: manifest_28["screen"][s]["return_lo_pp"] for s in SIGNAL_NAMES},
    "here_return_lo": screen["return_lo_pp"],
})
comparison["agree"] = comparison["nb28"] == comparison["here"]
display(comparison.round(4))
worst_lo = float((comparison["nb28_lo_vol"] - comparison["here_lo_vol"]).abs().max())
print(f"gate-5 flags agree with NB28 on {int(comparison['agree'].sum())} of {len(comparison)} signals; "
      f"largest |difference| in the forward-vol lower bound {worst_lo:.2e} "
      f"(same seed, so anything above floating-point noise means the panel differs)")
assert bool(comparison["agree"].all()), "re-derived gate 5 disagrees with NB28"
GATE_5 = GATE_5_REDERIVED
'''))

cells.append(md("""## Part 2. Every gate, re-derived

Not copied from NB29's manifest. Re-derived from this kernel's runs, with gate 5 from Part 1b, so
a gate that passed there because of a stale cache or a leaked log fails here.
"""))
cells.append(code('''def label_for(signal: str, fraction: float, suffix: str = "") -> str:
    return f"{signal}_q{int(round(fraction * 100)):02d}{suffix}"


NULL_SEEDS = tuple(range(10))
verdict_rows = []
for signal in CARRIED:
    label = label_for(signal, CENTRE)
    if label not in run_by_label:
        continue
    nulls = [f"{label}_null{seed}" for seed in NULL_SEEDS
             if f"{label}_null{seed}" in run_by_label]
    verdict_rows.append(gate_row(
        label, gate_5_by_signal=GATE_5, signal=signal,
        neighbours=[label_for(signal, n) for n in NEIGHBOURS], null_labels=nulls,
    ))
verdicts = verdict_table_rules(verdict_rows)
gate_columns = ["gate_1_positive", "gate_2_lovo", "gate_3_held_book", "gate_4_luck",
                "gate_5_screen", "gate_6_plateau", "gate_7_subperiod",
                "gate_8_diversification", "gate_9_null"]
for label in verdicts.index:
    for k, v in gate_3_corrected(label).items():
        verdicts.loc[label, k] = v
pd.set_option("display.max_colwidth", None)
display(verdicts[["signal", "cycle_sharpe", "cagr", "cycle_vol", "ulcer"] + gate_columns
                 + ["gate_3_corrected", "verdict"]])
print("\\ncomplete failure strings:")
for label, row in verdicts.iterrows():
    print(f"  {label}: {row['failed_gates'] or '(none)'}")

SHORTLISTED = [label for label, row in verdicts.iterrows() if row["verdict"] == "SHORTLIST"]
agreed = set(SHORTLISTED) == set(manifest_29["shortlisted"])
print(f"\\nSHORTLIST here: {SHORTLISTED or 'nothing'}")
print(f"NB29 recorded:  {manifest_29['shortlisted'] or 'nothing'}")
print(f"the two kernels agree: {agreed}")
'''))

cells.append(md("""## Part 3. The family-wise test, and exactly who is in the family

Membership is stated rather than assembled by convenience: **every configuration evaluated as
potentially shortlistable**, including failed centres and failed neighbours, excluding the
anchor, reference-only runs, leave-one-vault-out runs and null runs.

It cannot correct for the thirteen alternatives screened upstream in NB28, nor for the research
history that decided which mechanisms were worth building at all. It corrects for the multiplicity
of THIS family only, and the notebook says so rather than letting a p-value imply more.
"""))
cells.append(code('''FRACTIONS = tuple(manifest_29["fractions"])
family_labels = [
    label_for(signal, fraction)
    for signal in CARRIED if GATE_5.get(signal, False)
    for fraction in FRACTIONS
    if label_for(signal, fraction) in run_by_label
]
excluded_labels = sorted(set(run_by_label) - set(family_labels) - {"anchor"})
print(f"family members ({len(family_labels)}): {family_labels or 'none'}")
print(f"\\nexcluded from the family ({len(excluded_labels)}):")
for label in excluded_labels:
    print(f"  {label} - {run_by_label[label]['family']}")

if family_labels:
    summary, per_candidate = family_wise_joint(family_labels)
    display(summary)
    display(per_candidate.to_frame("sharpe_improvement_over_anchor").round(6))
    print("This p-value corrects for the multiplicity of the backtested family only. It does not "
          "correct for the thirteen signals screened in NB28, nor for the research history that "
          "chose which mechanisms to build.")
else:
    print("\\nno signal passed gate 5, so the backtested candidate family is empty and there is "
          "nothing for a family-wise test to correct.")
'''))

cells.append(md("""## Part 4. The tie-break, if there is anything to break

The operator indifference band, then Pareto dominance on the five diversification measures. A
DECISION POLICY: below a 0.25 Sharpe difference the more diversified candidate is preferred, and
that is not a statistical resolution claim - this window's minimum detectable Sharpe difference is
about 2.50. If neither candidate dominates, the comparison is UNRESOLVED and both are carried.
"""))
cells.append(code('''if len(SHORTLISTED) >= 2:
    pairs = []
    for i, left in enumerate(SHORTLISTED):
        for right in SHORTLISTED[i + 1:]:
            result = tie_break(left, right)
            pairs.append({"left": left, "right": right, **result})
    display(pd.DataFrame(pairs))
elif len(SHORTLISTED) == 1:
    print(f"one candidate shortlisted ({SHORTLISTED[0]}); nothing to break.")
else:
    print("nothing shortlisted; no tie-break.")

if SHORTLISTED:
    display(pd.DataFrame(
        [{"label": label, **diversification_cached(run_by_label[label])} for label in SHORTLISTED]
    ).set_index("label").round(6))
'''))

cells.append(md("""## Part 5. The frozen prospective specification

Fixed here, before any new data arrive. Its purpose is to make the next decision
non-discretionary: when the archive extends past 2026-09-08, this specification is run unchanged
and its result is compared against the comparator named below, on the horizon named below, under
the stopping rule named below. Nothing in the specification may be re-tuned after seeing that
result - re-tuning would make the prospective period another in-sample window, which is exactly
the failure this whole batch is structured to avoid.
"""))
cells.append(code('''if SHORTLISTED:
    chosen_label = verdicts.loc[SHORTLISTED]["cycle_sharpe"].idxmax()
    chosen_signal = str(verdicts.loc[chosen_label, "signal"])
    overrides = dict(run_by_label[chosen_label]["overrides"])
    status = "SHORTLISTED - carried to a prospective shadow"
else:
    chosen_label, chosen_signal, overrides = None, None, {}
    status = "NOTHING SHORTLISTED - no mechanism is carried"

specification = {
    "status": status,
    "signal": chosen_signal,
    "run_label": chosen_label,
    "exclusion_fraction_q": CENTRE if chosen_label else None,
    "missingness": "permissive - a candidate with no signal value is KEPT",
    "override_dictionary": overrides,
    "comparator": "the anchor of 02-better-format.ipynb, run on the same new data, same kernel",
    "monitoring_horizon": "the first 90 calendar days of decisions after 2026-09-08",
    "primary_statistic": "cycle Sharpe of the candidate minus the anchor's, on the shared cycle clock",
    "stopping_rule": (
        "abandon if the candidate's CAGR is negative over the prospective window, or if its cycle "
        "Sharpe falls more than 0.50 below the anchor's on the same cycles, or if the prefilter is "
        "inert (no decision changes the selected basket) on more than 80% of prospective decisions"
    ),
    "what_may_not_change": (
        "the signal, q, the direction, the permissive missingness handling, the comparator and "
        "the horizon. Re-tuning any of them after seeing prospective data makes that window "
        "in-sample and voids the exercise."
    ),
    "known_limits": [
        "The screen and the backtests share overlapping 30-day windows; nothing here is "
        "out-of-sample.",
        "NB30's cross-fit is a diagnostic: the folds share vaults and one market regime, and the "
        "purge removes temporal but not cross-sectional contamination.",
        "Gate 4 means 'no worse than the anchor', not 'luck-free'. The anchor's own luck_ratio is "
        f"{float(anchor_panel['luck_ratio']):.4f} and its top five positions deliver "
        f"{float(anchor_panel['top5_gross_share']) * 100:.1f}% of gross profit.",
        "Concentration is set by max_assets_in_portfolio and inverse-volatility sizing, not by "
        "selection; gate 8 therefore excludes only mechanisms that make it worse.",
    ],
}
display(pd.Series({k: v for k, v in specification.items() if k != "known_limits"}).to_frame("value"))
print("\\nknown limits:")
for limit in specification["known_limits"]:
    print(f"  - {limit}")
'''))

cells.append(code('''manifest = {
    "verdict": specification["status"],
    "shortlisted": SHORTLISTED,
    "kernels_agree_with_nb29": bool(agreed),
    "reproduction": {
        "configurations": int(len(crosscheck)),
        "reproducing_at_1e-9": int(crosscheck["reproduces"].sum()),
        "worst_abs_diff": float(crosscheck["worst_abs_diff"].max()),
    },
    "family_membership": family_labels,
    "family_excluded": {label: run_by_label[label]["family"] for label in excluded_labels},
    "gates": verdicts[["signal"] + gate_columns + ["gate_3_corrected", "failed_gates", "verdict"]].to_dict(orient="index"),
    "gate_5_rederived_agrees": bool(comparison["agree"].all()),
    "gate_5_worst_lo_diff": worst_lo,
    "specification": specification,
    "upstream": {
        "nb28_gate_5": GATE_5,
        "nb29_shortlisted": manifest_29["shortlisted"],
        "nb30_fold_stability": manifest_30["fold_stability"],
    },
}
Path("_build/manifest_31.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_31.json")
display(pd.Series({
    "verdict": manifest["verdict"],
    "configurations reproduced": f"{manifest['reproduction']['reproducing_at_1e-9']}"
                                 f"/{manifest['reproduction']['configurations']}",
    "family size": len(family_labels),
    "shortlisted": ", ".join(SHORTLISTED) or "nothing",
}).to_frame("value"))
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "31-backtest-stability-closeout.ipynb")
