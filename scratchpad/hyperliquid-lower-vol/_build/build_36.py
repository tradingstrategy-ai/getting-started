import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_floor import PARAM_ADDITIONS_FLOOR, INDICATOR_ADDITIONS_FLOOR, CELL14_REPLACEMENTS_FLOOR
from blocks_rules_fixes import INDICATOR_ADDITIONS_RULES_FIXES

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()
HARNESS_RULES_V2 = (BUILD_DIR / "harness_rules_v2.py").read_text()
HARNESS_RULES_V3 = (BUILD_DIR / "harness_rules_v3.py").read_text()
HARNESS_RULES_V3_GATES = (BUILD_DIR / "harness_rules_v3_gates.py").read_text()

HEADING = """# NB36 - close-out of the volatility tail exclusion, and the frozen specification

Re-runs every configuration NB35 executed in ONE kernel on ONE snapshot, re-derives gate 5 from
a rebuilt panel and every other gate from the re-run states, cross-checks each run against the
manifest it was first recorded in at 1e-9, audits every run for integrity, recomputes the
redemption fee independently and reports the candidate-minus-anchor differential against the
equity gap, and writes the frozen prospective specification.

**The deliverable is a specification, not a result.** Nothing in NB34-NB36 is adopted; ADOPT is
not in the vocabulary. The count of eight was found by search on this same data and the three
windows it has been run on overlap. A SHORTLIST here is admission to a prospective shadow with
a fixed comparator and a stated monitoring protocol, and the deployment decision after it is
the operator's.

**Based on:** [34-research-calm-score-screen.ipynb](34-research-calm-score-screen.ipynb),
[35-backtest-calm-tail-exclusion.ipynb](35-backtest-calm-tail-exclusion.ipynb) and
[34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md) Draft 2.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "36-backtest-calm-closeout",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_FLOOR},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR + INDICATOR_ADDITIONS_RULES_FIXES,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_FLOOR)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))
cells.append(code(HARNESS_RULES_V2))
cells.append(code(HARNESS_RULES_V3))
cells.append(code(HARNESS_RULES_V3_GATES))

cells.append(md("""## Part 0. Provenance and the two manifests

Both upstream manifests are asserted to have been produced on this kernel's data snapshot
before anything in them is used. If either differs, the cross-checks below would be comparing
two different experiments.
"""))
cells.append(code('''import json
from pathlib import Path
display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
manifest_34 = json.loads(Path("_build/manifest_34.json").read_text())
manifest_35 = json.loads(Path("_build/manifest_35.json").read_text())
assert_same_snapshot(manifest_34["provenance"], "manifest_34")
assert_same_snapshot(manifest_35["provenance"], "manifest_35")
GATE_5_NB34 = {s: bool(v) for s, v in manifest_34["gate_5"].items()}
print("NB34 gate 5:", GATE_5_NB34, " NB35 verdicts:", manifest_35["verdicts"])
'''))

cells.append(md("""## Part 1. Re-run everything, and cross-check at 1e-9

Every track-window configuration NB35 executed, reconstructed from the overrides it recorded
rather than from a hand-copied list. `__lovo` runs carry a `masked` set, restored as a set so
the same vault is masked.
"""))
cells.append(code('''def _restore(overrides: dict) -> dict:
    out = dict(overrides)
    if "masked" in out:
        out["masked"] = set(out["masked"])
    return out


recorded = manifest_35["all_runs"]
print(f"configurations to reproduce: {len(recorded)}")
check_rows = []
for label in sorted(recorded):
    record = recorded[label]
    entry = run_and_record(label, record["family"], **_restore(record["overrides"]))
    row = {"label": label, "family": record["family"]}
    worst = 0.0
    for metric, expected in record["panel"].items():
        actual, expected = float(entry["panel"][metric]), float(expected)
        row[metric] = actual
        if np.isfinite(actual) != np.isfinite(expected):
            worst = float("inf")   # a finite-to-NaN mismatch is a failed reproduction, never a zero difference
        elif np.isfinite(actual):
            worst = max(worst, abs(actual - expected))
    row["worst_abs_diff"] = worst
    row["reproduces"] = bool(worst <= 1e-9)
    check_rows.append(row)
crosscheck = pd.DataFrame(check_rows).set_index("label")
display(crosscheck[["family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "worst_abs_diff", "reproduces"]].round(9))
failures = crosscheck[~crosscheck["reproduces"]]
if len(failures):
    print(f"\\n{len(failures)} configuration(s) did NOT reproduce at 1e-9:")
    display(failures[["family", "worst_abs_diff"]])
else:
    print(f"\\nall {len(crosscheck)} configurations reproduce at 1e-9 across kernels")
'''))

cells.append(md("""## Part 2. Gate 5, re-derived

The screen panel is rebuilt from this kernel's own logging runs, the offline reads and the
offline eight are verified against the engine's in-trade reads and the re-run count-8 runs'
exclusions in this kernel, the exclusion flags are set on the full pool, the joint bootstrap
and simultaneous bounds are recomputed on post-break decisions, and every persisted numeric
field is compared with NB34's before the flags are used.
"""))
cells.append(code('''log_iv = run_and_record("screen_log_inverse_vol", "control", **prefilter_overrides("inverse_vol", fraction=0.0))
display(assert_anchor_parity(log_iv["panel"]))
log_calm = run_and_record("screen_log_calm", "control", **prefilter_overrides("calm_score", fraction=0.0))
display(assert_anchor_parity(log_calm["panel"]))
panel_frame, eligibility = build_screen_panel(log_iv)
panel_frame["regime"] = np.where(panel_frame["date"] >= POST_BREAK_START, "post_break", "pre_break")
add_exclusion_flags(panel_frame)
# The offline mirror is verified against the engine in THIS kernel, not inherited from NB34: the
# panel's T-1 reads must equal the in-trade reads, and the offline eight must equal the re-run
# count-8 runs' engine exclusions on every comparable date.
reads_checked = {"calm_score": verify_signal_reads(panel_frame, log_calm, "calm_score"),
                 "inverse_vol": verify_signal_reads(panel_frame, log_iv, "inverse_vol")}
flag_checks = {"calm_score": verify_exclusion_flags(panel_frame, run_by_label["calm_8"], "calm_score"),
               "inverse_vol": verify_exclusion_flags(panel_frame, run_by_label["measured_8"], "inverse_vol")}
n_eligible = int(panel_frame["date"].nunique())
for name, frame in flag_checks.items():
    assert int(frame["comparable_pool"].sum()) == n_eligible, f"{name}: only {int(frame['comparable_pool'].sum())} of {n_eligible} dates comparable"
print(f"engine mirror verified in this kernel: {reads_checked} reads equal in-trade; exclusions equal the engine on all {n_eligible} eligible dates")
post = panel_frame[panel_frame["regime"] == "post_break"].copy()
screen_post, detail_post, _ = run_screen_v3(post, verbose=False)
GATE_5_REDERIVED = {s: bool(screen_post.loc[s, "gate_5"]) for s in SIGNAL_NAMES}
nb34 = pd.DataFrame(manifest_34["screen_post"]).T
numeric = [c for c in screen_post.columns if screen_post[c].dtype.kind in "fi" and c in nb34.columns]
booleans = [c for c in ("evaluated", "enough_dates", "stability_clause", "return_clause", "gate_5") if c in nb34.columns]
diffs = (screen_post[numeric].astype(float) - nb34[numeric].astype(float)).abs()
bool_agree = pd.DataFrame({c: screen_post[c].astype(bool) == nb34[c].astype(bool) for c in booleans}).all(axis=1)
comparison = pd.DataFrame({"nb34": pd.Series(GATE_5_NB34), "here": pd.Series(GATE_5_REDERIVED),
                           "max_abs_diff_any_field": diffs.max(axis=1), "all_booleans_agree": bool_agree})
comparison["agree"] = (comparison["nb34"] == comparison["here"]) & comparison["all_booleans_agree"]
display(comparison.round(10))
fam = family_summary(detail_post)
fam_34 = pd.DataFrame(manifest_34["families_post"]).T
for name in fam.index:
    for col in ("hypotheses_used", "hypotheses_total", "complete_draws", "incomplete_draws"):
        assert int(fam.loc[name, col]) == int(fam_34.loc[name, col]), f"{name} {col} differs from NB34"
    # The manifest stores the family summary rounded to six decimals; compare at that resolution.
    assert abs(float(fam.loc[name, "critical"]) - float(fam_34.loc[name, "critical"])) < 1e-6, f"{name} critical differs from NB34"
worst = float(diffs.to_numpy().max())
print(f"largest |difference| over {len(numeric)} numeric fields x {len(SIGNAL_NAMES)} signals: {worst:.2e} (manifest fields are "
      f"rounded to 6 decimals); families agree on all counts and on critical values to 1e-6")
assert bool(comparison["agree"].all()), "re-derived gate 5 disagrees with NB34"
assert worst < 1e-6, f"re-derived screen differs from NB34 by {worst:.2e}"
GATE_5 = GATE_5_REDERIVED
'''))

cells.append(md("""## Part 3. Every gate, re-derived

`gate_row_v3()` on the re-run states with the re-derived gate 5, null labels from the re-run
set, and every Boolean compared field by field with NB35's verdict rows.
"""))
cells.append(code('''COUNTS, CENTRE, NEIGHBOURS = (6, 8, 10), 8, (6, 10)


def label_for(signal: str, count: int, strict: bool = False) -> str:
    stem = "calm" if signal == "calm_score" else "measured"
    return f"{stem}_{count}" + ("_strict" if strict else "")


verdict_rows = []
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    nulls = sorted(l for l in run_by_label if l.startswith(f"{label}_null"))
    verdict_rows.append(gate_row_v3(label, gate_5_by_signal=GATE_5, signal=signal,
                                    neighbours=[label_for(signal, n) for n in NEIGHBOURS], null_labels=nulls))
verdicts = verdict_table_rules(verdict_rows)
GATE_COLUMNS = ["gate_1_positive", "gate_2_lovo", "gate_3_held_book", "gate_4_luck", "gate_5_screen",
                "gate_6_plateau", "gate_7_subperiod", "gate_8_diversification", "gate_9_null"]
pd.set_option("display.max_colwidth", None)
display(verdicts[["signal", "cycle_sharpe", "cagr"] + GATE_COLUMNS + ["fee_differential_ok", "verdict"]])
for label, row in verdicts.iterrows():
    print(f"  {label}: failed_gates = {row['failed_gates']!r}; diversification_failures = {row['diversification_failures']!r}; "
          f"fee share {row['fee_differential_share_of_gap']:.4f}")

nb35_rows = {r["label"]: r for r in manifest_35["verdict_rows"]}
agree_rows = []
for label, row in verdicts.iterrows():
    there = nb35_rows[label]
    booleans_agree = all(bool(row[g]) == bool(there[g]) for g in GATE_COLUMNS + ["fee_differential_ok"])
    numeric_fields = [k for k, v in there.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
                      and k in row.index and isinstance(row[k], (int, float, np.floating, np.integer))]
    worst_num = 0.0
    for k in numeric_fields:
        here_v, there_v = float(row[k]), float(there[k])
        if np.isfinite(here_v) != np.isfinite(there_v):
            worst_num = float("inf")   # finite-to-NaN is a disagreement, not a skipped field
        elif np.isfinite(here_v):
            worst_num = max(worst_num, abs(here_v - there_v))
    agree_rows.append({"label": label, "verdict_here": row["verdict"], "verdict_nb35": there["verdict"],
                       "booleans_agree": booleans_agree, "numeric_fields": len(numeric_fields), "worst_numeric_diff": worst_num,
                       "failed_gates_same": row["failed_gates"] == there["failed_gates"]})
agreement = pd.DataFrame(agree_rows).set_index("label")
display(agreement)
assert bool(agreement["booleans_agree"].all()) and bool((agreement["verdict_here"] == agreement["verdict_nb35"]).all()), \\
    "re-derived gates disagree with NB35"
assert float(agreement["worst_numeric_diff"].max()) < 1e-6, "re-derived gate numerics differ from NB35"
SHORTLISTED = [l for l, r in verdicts.iterrows() if r["verdict"] == "SHORTLIST"]
print(f"\\nshortlisted: {SHORTLISTED or 'nothing'}")
if len(SHORTLISTED) == 2:
    print("tie-break:", tie_break(SHORTLISTED[0], SHORTLISTED[1]))
'''))

cells.append(md("""### The null, re-derived and asserted distinct

NB35 REPORTED the distinct-draw counts; this asserts them: nineteen distinct realised
cycle-return series, nineteen distinct excluded-set digests and nineteen distinct basket
digests per centre, and the centre's rank against the re-run null equal to NB35's.
"""))
cells.append(code('''null_check_rows = []
nb35_diag = manifest_35["expensive_diagnostic"]
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    labels = sorted(l for l in run_by_label if l.startswith(f"{label}_null"))
    assert len(labels) == NULL_MIN_DISTINCT_V3, f"{label}: {len(labels)} null runs re-run, expected {NULL_MIN_DISTINCT_V3}"
    result = null_effectiveness_v3(label, labels)
    assert result["distinct_cycle_return_series"] == len(labels), f"{label}: null cycle-return series are not all distinct"
    assert result["distinct_excluded_sets"] == len(labels), f"{label}: null excluded sets are not all distinct"
    assert result["distinct_baskets"] == len(labels), f"{label}: null baskets are not all distinct"
    assert result["null_sharpe_rank_of_centre"] == nb35_diag[label]["null_rank_of_centre"], \\
        f"{label}: rank {result['null_sharpe_rank_of_centre']} here vs {nb35_diag[label]['null_rank_of_centre']} in NB35"
    assert abs(result["null_best"] - nb35_diag[label]["null_best"]) < 1e-9
    null_check_rows.append({"label": label, "draws": len(labels), "distinct_series": result["distinct_cycle_return_series"],
                            "distinct_excluded_sets": result["distinct_excluded_sets"], "distinct_baskets": result["distinct_baskets"],
                            "centre_sharpe": result["centre_sharpe"], "null_best": result["null_best"], "null_median": result["null_median"],
                            "rank_of_centre": result["null_sharpe_rank_of_centre"], "would_pass": result["passes"],
                            "centre_persistence": result["centre_persistence"], "null_persistence_mean": result["null_persistence_mean"]})
null_check = pd.DataFrame(null_check_rows).set_index("label")
display(null_check.round(6))
print("all three distinctness counts asserted at 19 for both centres; ranks equal NB35's (DIAGNOSTIC - gate 9 is False by protocol)")

# `null_effectiveness()`'s basket digest summarises positions opened per address over the whole
# run, not the date-by-date book (NB36 review). The ordered (decision date, held set) sequence is
# digested here and asserted distinct as well.
import hashlib
def basket_sequence_digest(entry):
    weights = _position_weights(entry["state"])
    sequence = [(str(t), sorted(str(p.pool_address).lower() for p, _s in weights[t])) for t in sorted(weights)]
    return hashlib.sha256(repr(sequence).encode()).hexdigest()[:16]
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    labels = sorted(l for l in run_by_label if l.startswith(f"{label}_null"))
    digests = {basket_sequence_digest(run_by_label[l]) for l in labels}
    assert len(digests) == len(labels), f"{label}: only {len(digests)} distinct basket sequences over {len(labels)} null draws"
    null_check.loc[label, "distinct_basket_sequences"] = len(digests)
print("ordered basket sequences also distinct on all 19 draws for both centres")

# Gate 2 is False by protocol for both centres; the leave-one-vault-out runs were re-run above,
# so their retention is recomputed here as the diagnostic NB35 reported, and compared.
lovo_check_rows = []
for signal in SIGNAL_NAMES:
    for count in (CENTRE,) + NEIGHBOURS:
        label = label_for(signal, count)
        result = lovo_gate(label, verbose=False)
        lovo_check_rows.append({"label": label, **{k: result[k] for k in ("masked", "sharpe", "lovo_sharpe", "lovo_cagr", "retention", "passes")}})
lovo_check = pd.DataFrame(lovo_check_rows).set_index("label")
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    assert abs(float(lovo_check.loc[label, "retention"]) - float(nb35_diag[label]["lovo_retention"])) < 1e-9, label
    assert lovo_check.loc[label, "masked"] == nb35_diag[label]["lovo_masked"], label
display(lovo_check.round(6))
print("leave-one-vault-out retention recomputed from the re-run states equals NB35's for both centres (DIAGNOSTIC - gate 2 is False by protocol)")
'''))

cells.append(md("""## Part 4. The fee differential, every run

Amendment A6 in full: the independent recomputation for every re-run configuration, the
anchor's, the differential and its share of the equity gap. The cause of the underlying
discrepancy is outside this plan; its differential effect is not.
"""))
cells.append(code('''fee_rows = []
for entry in runs:
    if entry["label"] == "anchor" or entry.get("state") is None:
        continue
    fee_rows.append({"label": entry["label"], "family": entry["family"], **fee_differential(entry["label"])})
fees = pd.DataFrame(fee_rows).set_index("label")
anchor_fee = fee_audit_cached("anchor")
print(f"anchor: {anchor_fee['redemptions']} redemptions, {anchor_fee['over_1bp']} over 1 bp, net signed "
      f"{anchor_fee['net_signed_proceeds_diff_usd']:+.2f} USD")
display(fees[["family", "fee_redemptions", "fee_over_1bp", "fee_net_signed_usd", "fee_differential_usd", "equity_gap_usd",
              "fee_differential_share_of_gap", "fee_differential_ok"]].round(4))
one_sided = bool((fees["fee_net_signed_usd"] <= 0).all())
print(f"every run's net signed discrepancy is <= 0 (engine charges more, never less): {one_sided}")
'''))

cells.append(md("""## Part 5. The frozen prospective specification

Fixed here, before any new data arrive. When the archive extends past 2026-09-08 the
specification is run unchanged, compared against the comparator on the horizon named, under the
protocol named. The 90-day horizon is a monitoring choice, not a claim of statistical
resolution.
"""))
cells.append(code('''if SHORTLISTED:
    chosen_label = SHORTLISTED[0] if len(SHORTLISTED) == 1 else (tie_break(SHORTLISTED[0], SHORTLISTED[1])["winner"] or "measured_8")
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
    "exclusion_count": CENTRE if chosen_label else None,
    "missingness": "permissive - a candidate with no signal value is KEPT",
    "override_dictionary": overrides,
    "comparator": "the anchor of 02-better-format.ipynb, run on the same new data, same kernel",
    "monitoring_horizon": "the first 90 calendar days of decisions after 2026-09-08",
    "primary_statistic": "cycle Sharpe of the candidate minus the anchor's, on the shared cycle clock; max drawdown beside it",
    "decision_at_90_days": (
        "EXTEND for another 90 days if the candidate's cycle Sharpe is within 0.5 of the anchor's on the same "
        "cycles and its max drawdown is no deeper; REJECT if it is worse than that on both; otherwise another "
        "90 days. A deployment decision on 90 days of two-day cycles is the operator's judgement, not the data's."
    ),
    "stopping_rule": (
        "abandon early if the candidate's CAGR is negative over the prospective window, or if its cycle Sharpe "
        "falls more than 0.50 below the anchor's on the same cycles, or if the prefilter is inert on more than "
        "80% of prospective decisions"
    ),
    "what_may_not_change": (
        "the signal, the count, the direction, the permissive missingness handling, the comparator and the "
        "horizon. Re-tuning any of them after seeing prospective data makes that window in-sample."
    ),
    "known_limits": [
        "The count of eight was selected exploratorily on this data; the three windows it has been run on overlap.",
        "The screen and the backtests share overlapping 30-day windows; nothing here is out-of-sample.",
        "Gate 3 is scored on its volatility leg only; the concentration indicators are not identifiable on this archive.",
        "Gate 4 means 'no worse than the anchor', not 'luck-free'.",
        "The engine's redemption fee differs from the documented schedule on a large share of redemptions, always in "
        "the engine's favour, cause undetermined; only its DIFFERENTIAL effect is bounded here.",
        "The fee schedule itself - a universal 10% performance fee and an undocumented 10 bps - is a track-level assumption.",
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
    "reproduction": {"configurations": int(len(crosscheck)), "reproducing_at_1e-9": int(crosscheck["reproduces"].sum()),
                     "worst_abs_diff": float(crosscheck["worst_abs_diff"].max())},
    "gate_5_rederived_agrees": bool(comparison["agree"].all()),
    "gate_5_worst_diff": worst,
    "gate_5": GATE_5,
    "gates": verdicts[["signal"] + GATE_COLUMNS + ["fee_differential_ok", "failed_gates", "verdict"]].to_dict(orient="index"),
    "gates_agree_with_nb35": agreement.to_dict(orient="index"),
    "verdict_rows": [{k: v for k, v in r.items() if k != "plateau_detail"} for r in verdict_rows],
    "fees": fees.round(10).to_dict(orient="index"),
    "anchor_fee": anchor_fee,
    "fee_one_sided": one_sided,
    "null_check": null_check.round(10).to_dict(orient="index"),
    "lovo_check": lovo_check.round(10).to_dict(orient="index"),
    "mirror_verified": {"reads": reads_checked, "flag_comparable_dates": {k: int(v["comparable_pool"].sum()) for k, v in flag_checks.items()},
                        "eligible_dates": n_eligible},
    "provenance": provenance_record(),
    "specification": specification,
}
Path("_build/manifest_36.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_36.json")
'''))

cells += integrity_and_audit_cells()
cells.append(md("""## Integrity audit, every re-run configuration
"""))
cells.append(code('''audit_rows = []
for entry in runs:
    if entry.get("state") is None:
        continue
    audit_rows.append({"label": entry["label"], "family": entry["family"], **audit_portfolio(entry["state"].portfolio)})
audit_all = pd.DataFrame(audit_rows).set_index("label")
display(audit_all)
bad = audit_all[(audit_all["destroyed"] > 0) | (audit_all["stranded"] > 0) | (audit_all["cash + holdings - equity"].abs() > 1.0)]
print(f"runs audited: {len(audit_all)}; failing: {len(bad)}")
assert len(bad) == 0, f"integrity screen failed for: {list(bad.index)}"
manifest_path = Path("_build/manifest_36.json")
manifest_now = json.loads(manifest_path.read_text())
manifest_now["audit"] = {"runs_audited": int(len(audit_all)), "integrity_failures": int(len(bad))}
manifest_path.write_text(json.dumps(manifest_now, indent=1, default=str))
print("manifest updated with audit results")
'''))
write_notebook(cells, TRACK_DIR / "36-backtest-calm-closeout.ipynb")
