"""NB24 - close-out of the stability-leads plan (20-stability-leads-plan.md).

Re-runs, in ONE kernel and on ONE data snapshot, every backtest that NB21, NB22 and NB23
executed: the anchor, the twelve-member volatility-matched family, NB22's seven pool sizes and
four window-sensitivity runs, and NB23's centre, ten neighbours and one policy alternative.
Thirty-five variant runs plus the anchor.

Nothing here trusts a source notebook's verdict flag. Every gate is recomputed from
`harness_stability.py` in this kernel, and every run's cycle Sharpe and CAGR is cross-checked
against the literal recorded in `_build/manifest_21.json`, `_build/manifest_22.json` and
`_build/manifest_23.json`.
"""
import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import PARAM_ADDITIONS_STABILITY, INDICATOR_ADDITIONS_STABILITY, \
    CELL14_REPLACEMENTS_STABILITY

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

HEADING = """# NB24 - close-out of the stability-leads plan

The plan's overall verdict, recomputed rather than assembled. Every backtest NB21, NB22 and NB23
executed is re-run here in a single kernel on a single data snapshot - the anchor, the
twelve-member volatility-matched family, the seven complementary pool sizes and their four
window-sensitivity runs, and the Sortino-leg swap's centre, ten neighbours and policy
alternative. Thirty-five variant runs. No source notebook's verdict flag is trusted: every
constraint, plateau Boolean and late-period test is recomputed from `harness_stability.py` in
this kernel, and every run's cycle Sharpe and CAGR is cross-checked against the literal frozen in
that notebook's manifest.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Close-out of [20-stability-leads-plan.md](20-stability-leads-plan.md), covering
[20-research-mark-quality.ipynb](20-research-mark-quality.ipynb),
[21-backtest-vol-matched-family.ipynb](21-backtest-vol-matched-family.ipynb),
[22-backtest-joint-downside.ipynb](22-backtest-joint-downside.ipynb) and
[23-backtest-sortino-leg-swap.ipynb](23-backtest-sortino-leg-swap.ipynb).

_Cell numbers below are zero-based indices into this notebook, as printed by the execution
runner._

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "24-backtest-closeout",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_STABILITY)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

# ---------------------------------------------------------------------------------------------
# 1. Provenance and anchor parity
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Provenance and anchor parity

The content hashes below decide what this notebook can conclude. If they differ from the ones
NB21-NB23 printed, the snapshot moved under the plan and the cross-check further down is the
place that will say so.

The anchor is the unchanged `02-better-format.ipynb` configuration, run in this kernel with both
stability-track `decide_trades` splices present but disabled. `assert_anchor_parity()` asserts
that both diagnostic logs are empty afterwards, which is the evidence that neither splice fired
rather than the assumption that it did not.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
#: Trailing semicolon only: `record_anchor()` returns the whole run entry, and letting Jupyter
#: echo it prints the anchor's full equity, returns and cycle-return series into the notebook.
record_anchor();
'''))

# ---------------------------------------------------------------------------------------------
# 2. Manifests
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The frozen manifests

Each of NB21, NB22 and NB23 wrote a manifest at the end of its own run: the verdict, the gate
Booleans, and the full-precision cycle Sharpe and CAGR of every run it executed. They are loaded
here as the *expected* values for the cross-check, and as the source of the run inventory that
this notebook must reproduce. They are **not** loaded as verdicts - every gate below is
recomputed.

NB20 wrote no manifest: it is a read-only diagnostic that executed no variant run. Its findings
enter this notebook as the ulcer-reading ceiling further down, with the figures quoted from its
own cells.
"""))
cells.append(code('''import json

MANIFESTS = {}
for number in (21, 22, 23):
    path = Path(f"_build/manifest_{number}.json")
    assert path.exists(), f"missing manifest: {path.resolve()}"
    MANIFESTS[number] = json.loads(path.read_text())

manifest_summary = pd.DataFrame([
    {
        "manifest": f"manifest_{number}.json",
        "notebook": m["notebook"],
        "recorded_verdict": m["verdict"],
        "runs_recorded": len(m["runs"]),
    }
    for number, m in MANIFESTS.items()
]).set_index("manifest")
display(manifest_summary)

#: Every run label the plan actually executed, and which notebook is authoritative for it.
#: `drop_N` appears in all three manifests - NB21 ran the family as its candidate set, NB22 and
#: NB23 re-ran it as the constraint-7 comparator - so it is checked against all three.
EXPECTED = {}
for number, m in MANIFESTS.items():
    for label, record in m["runs"].items():
        entry = EXPECTED.setdefault(label, {"sources": [], "overrides": record["overrides"], "values": {}})
        entry["sources"].append(f"NB{number}")
        entry["values"][f"NB{number}"] = (record["cycle_sharpe"], record["cagr"])
        assert entry["overrides"] == record["overrides"], (
            f"{label} carries different overrides in NB{number} than in {entry['sources'][0]}"
        )

#: Cross-manifest agreement, before this kernel is compared against anything. Three notebooks ran
#: the same twelve drop labels in three different orders; if their recorded numbers disagree with
#: each other, the run order or the snapshot mattered and nothing below is comparable.
cross_manifest = []
for label, entry in EXPECTED.items():
    sharpes = [v[0] for v in entry["values"].values()]
    cagrs = [v[1] for v in entry["values"].values()]
    cross_manifest.append({
        "label": label, "sources": " ".join(entry["sources"]),
        "sharpe_spread": max(sharpes) - min(sharpes),
        "cagr_spread": max(cagrs) - min(cagrs),
        "agree": bool(max(sharpes) - min(sharpes) == 0.0 and max(cagrs) - min(cagrs) == 0.0),
    })
cross_manifest = pd.DataFrame(cross_manifest).set_index("label")
MANIFESTS_AGREE = bool(cross_manifest["agree"].all())
display(cross_manifest[cross_manifest["sources"].str.contains(" ")])
print(f"Labels recorded by more than one notebook agree bit-for-bit: {MANIFESTS_AGREE}")
print(f"Distinct run labels across the whole plan: {len(EXPECTED)} "
      f"({len(EXPECTED) - 1} variant runs plus the anchor).")
'''))

# ---------------------------------------------------------------------------------------------
# 3. Re-run everything in one kernel
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Re-running the whole plan in one kernel

Three groups, in one kernel, on one snapshot:

1. **`build_family()`** - `drop_5` through `drop_60` at 5-step spacing. This is simultaneously
   NB21's candidate set (lead 1) and the constraint-7 comparator for NB22 and NB23. It is
   recorded with `family="control"` because that is its role in the adoption rule; the source
   column added below records that NB21 evaluated the same runs as candidates.
2. **NB22's runs** - the seven `complementary_P` pool sizes and the four centre window-sensitivity
   runs. NB22 also ran `drop_20` and `drop_30` for its Part A diagnostic; those are the same
   configurations as the family members, so `build_family()` above already produced them and
   re-running them would be a duplicate label.
3. **NB23's runs** - the centre, its ten neighbours and the strict-admission policy alternative.

Neither notebook's leave-one-vault-out run appears here, because neither was ever triggered: in
both cases the plateau failed first. An unexecuted robustness run cannot produce a passing flag,
so the verdict cell counts every masked result as absent, which is a fail.
"""))
cells.append(code('''family = build_family()
display(family[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer", "abs_invested_beta",
                "mean_invested", "late_cagr", "late_ulcer"]])
'''))

cells.append(code('''#: NB22, lead 2. Exactly the grid and the window sensitivity that notebook ran.
COMPLEMENTARY_CENTRE = 18
COMPLEMENTARY_GRID = (10, 12, 14, 16, 18, 20, 24)
for p in COMPLEMENTARY_GRID:
    run_and_record(f"complementary_{p}", "candidate", complementary_pool_size=p)

WINDOW_SENSITIVITY = {
    "complementary_18__window_90": dict(complementary_pool_size=18, joint_loss_window_days=90),
    "complementary_18__window_270": dict(complementary_pool_size=18, joint_loss_window_days=270),
    "complementary_18__min_events_5": dict(complementary_pool_size=18, joint_loss_min_events=5),
    "complementary_18__min_events_20": dict(complementary_pool_size=18, joint_loss_min_events=20),
}
for label, overrides in WINDOW_SENSITIVITY.items():
    run_and_record(label, "candidate", **overrides)
print(f"NB22: {len(COMPLEMENTARY_GRID)} pool sizes and {len(WINDOW_SENSITIVITY)} "
      f"window-sensitivity runs recorded.")
'''))

cells.append(code('''#: NB23, lead 3. The centre carries `require_scored_candidates=False` explicitly - the anchor's
#: own admission policy - because the strict-admission alternative below is the same run with
#: that one flag flipped, and the pair only means anything if both state it.
SELECTION_INDICATOR = "cagr_sortino_shrunk_weight"
SWAP_NEIGHBOURS = [
    ("cagr_weight_0.5", dict(cagr_weight=0.5)),
    ("cagr_weight_0.7", dict(cagr_weight=0.7)),
    ("t_cap_2", dict(evidence_t_cap=2.0)),
    ("t_cap_4", dict(evidence_t_cap=4.0)),
    ("prior_30", dict(evidence_prior_strength=30)),
    ("prior_90", dict(evidence_prior_strength=90)),
    ("min_events_10", dict(evidence_min_events=10)),
    ("min_events_30", dict(evidence_min_events=30)),
    ("max_events_60", dict(evidence_max_events=60)),
    ("max_events_120", dict(evidence_max_events=120)),
]
SWAP_CENTRE_LABEL = "swap__centre"
SWAP_NEIGHBOUR_LABELS = [f"swap__{label}" for label, _ in SWAP_NEIGHBOURS]
SWAP_POLICY_LABEL = "swap__require_scored"

swap_common = dict(selection_score_indicator=SELECTION_INDICATOR)
run_and_record(SWAP_CENTRE_LABEL, "candidate", **swap_common, require_scored_candidates=False)
for label, override in SWAP_NEIGHBOURS:
    run_and_record(f"swap__{label}", "candidate", **{**swap_common, **override})
run_and_record(SWAP_POLICY_LABEL, "policy", **{**swap_common, "require_scored_candidates": True})
print(f"NB23: the centre, {len(SWAP_NEIGHBOURS)} neighbours and the strict-admission policy "
      f"alternative recorded.")
'''))

cells.append(code('''#: Which notebook each label belongs to, for the tables and the frontier chart. The family is
#: labelled once, with both of its roles, because it has both.
SOURCE_OF = {"anchor": "anchor"}
for n in FAMILY_DROPS:
    SOURCE_OF[f"drop_{n}"] = "NB21 family (lead 1) / constraint-7 comparator"
for p in COMPLEMENTARY_GRID:
    SOURCE_OF[f"complementary_{p}"] = "NB22 complementary (lead 2)"
for label in WINDOW_SENSITIVITY:
    SOURCE_OF[label] = "NB22 window sensitivity"
for label in [SWAP_CENTRE_LABEL] + SWAP_NEIGHBOUR_LABELS + [SWAP_POLICY_LABEL]:
    SOURCE_OF[label] = "NB23 Sortino leg swap (lead 3)"

executed = [entry["label"] for entry in runs]
missing = sorted(set(EXPECTED) - set(executed))
extra = sorted(set(executed) - set(EXPECTED))
RUN_INVENTORY_OK = not missing and not extra
print(f"Runs executed in this kernel: {len(executed)} ({len(executed) - 1} variants plus the anchor).")
print(f"Recorded by the three manifests: {len(EXPECTED)}.")
print(f"In a manifest but not re-run here: {missing or 'none'}")
print(f"Re-run here but in no manifest:   {extra or 'none'}")
print(f"Run inventory reproduces the plan exactly: {RUN_INVENTORY_OK}")
assert all(label in SOURCE_OF for label in executed), \\
    f"unclassified run labels: {sorted(set(executed) - set(SOURCE_OF))}"
'''))

# ---------------------------------------------------------------------------------------------
# 4. Cross-check
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Cross-check against the frozen manifests

Every run, not only the centres. Each row's cycle Sharpe and CAGR in *this* kernel against the
literal frozen in the manifest of the notebook that ran it, at an absolute tolerance of **1e-9** -
these are the same code path on the same snapshot, so this is a reproduction check, not a
rounding allowance. Where a label appears in more than one manifest, the strictest (largest)
difference across them is reported. Each row's override dictionary is compared as well, so a
matching number produced by a different configuration would be caught rather than pass.

**Scope.** The source manifests froze two metrics per run, so two metrics per run is what can be
checked. This does not compare states, trades, equity paths, diagnostic logs or the remaining
panel columns; "reproduces" below means those two metrics and the overrides, nothing wider.

A mismatch is not silently absorbed. It is printed as a banner here, carried into
`CROSS_CHECK_OK`, written into this notebook's own manifest, and printed as a second banner under
the verdict in cell 53. It is not raised, so the remaining analysis still completes. Cell 0 is
static markdown and would not rewrite itself, so the banners rather than the heading are what a
future reader has to be looking at.
""".rstrip() + "\n"))
cells.append(code('''CROSS_CHECK_TOLERANCE = 1e-9

cross_rows = []
for entry in runs:
    label = entry["label"]
    if label not in EXPECTED:
        continue
    actual_sharpe = float(entry["panel"]["cycle_sharpe"])
    actual_cagr = float(entry["panel"]["cagr"])
    expected = EXPECTED[label]["values"]
    sharpe_diff = max(abs(actual_sharpe - v[0]) for v in expected.values())
    cagr_diff = max(abs(actual_cagr - v[1]) for v in expected.values())
    one = next(iter(expected.values()))
    cross_rows.append({
        "label": label,
        "source": " ".join(EXPECTED[label]["sources"]),
        "expected_cycle_sharpe": one[0], "actual_cycle_sharpe": actual_sharpe,
        "sharpe_abs_diff": sharpe_diff,
        "expected_cagr": one[1], "actual_cagr": actual_cagr,
        "cagr_abs_diff": cagr_diff,
        #: The two metrics agreeing is only a reproduction if they were produced by the SAME
        #: configuration. Comparing the override dictionary this kernel actually ran against the
        #: one the manifest recorded is what rules out "the right number from the wrong run".
        "overrides_match": bool(entry["overrides"] == EXPECTED[label]["overrides"]),
        "reproduced": bool(sharpe_diff <= CROSS_CHECK_TOLERANCE and cagr_diff <= CROSS_CHECK_TOLERANCE),
        "finite": bool(np.isfinite(actual_sharpe) and np.isfinite(actual_cagr)),
    })
cross_check = pd.DataFrame(cross_rows).set_index("label")
display(cross_check)

failures = cross_check[
    ~cross_check["reproduced"] | ~cross_check["finite"] | ~cross_check["overrides_match"]
]
OVERRIDES_MATCH = bool(cross_check["overrides_match"].all())
CROSS_CHECK_OK = bool(len(failures) == 0 and RUN_INVENTORY_OK and MANIFESTS_AGREE)
print(f"Worst cycle-Sharpe difference across all {len(cross_check)} runs: "
      f"{cross_check['sharpe_abs_diff'].max():.3e}")
print(f"Worst CAGR difference across all {len(cross_check)} runs:        "
      f"{cross_check['cagr_abs_diff'].max():.3e}")
if len(failures):
    print()
    print("!" * 100)
    print("CROSS-CHECK MISMATCH. This kernel does not reproduce what the source notebooks recorded.")
    print("Every conclusion below is against a different snapshot from the one the plan ran on.")
    print("!" * 100)
    display(failures)
print()
print(f"Every run reproduced its manifest literal at +/-{CROSS_CHECK_TOLERANCE:g}: "
      f"{bool(len(failures) == 0)}")
print(f"Every run's override dictionary matches the one its manifest recorded: {OVERRIDES_MATCH}")
print("Scope: this compares the TWO metrics each manifest froze - cycle Sharpe and CAGR - plus")
print("the override dictionary. It does not compare states, trades, equity paths, diagnostic")
print("logs or the other panel metrics, none of which the source manifests carry.")
print(f"CROSS_CHECK_OK (reproduction AND overrides AND run inventory AND cross-manifest agreement): {CROSS_CHECK_OK}")
'''))

# ---------------------------------------------------------------------------------------------
# 5. Combined verdict table
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Combined verdict table

`verdict_table_v3()` reads `runs` directly, so an executed run cannot be left out of the table
that should have judged it. Adoption rule v3: CAGR >= 20%; cycle Sharpe >= anchor - 0.10; cycle
volatility <= anchor; ulcer <= 0.85 x anchor; invested-basket beta < anchor; mean invested
>= 0.90; and constraint 7, cycle Sharpe >= the best observed control at or below the row's own
volatility, plus 0.10.

The `failed` column is printed **in full** for every row. A row that failed six constraints says
six; nothing here is summarised down to a first failure.

Constraint 7 is **inapplicable** to the family itself, since those rows *are* the observed-control
set and would each be compared against themselves - so `passes_1_to_6` and `failed_1_to_6` are
reported alongside, and the family's verdict is read from those. For NB22's and NB23's runs the
v3 columns are the operative ones.
"""))
cells.append(code('''pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", None)

#: The literal call the plan asks for, with the complete executed run set and the complete
#: failure string, sorted by cycle Sharpe.
combined = verdict_table_v3(family=family)
display(combined)
'''))
cells.append(code('''#: The same table, annotated with the source notebook and with the constraints-1-to-6 verdict
#: that the family must be read on, since constraint 7 is a self-comparison for those rows.
combined["source"] = [SOURCE_OF[label] for label in combined.index]
combined["passes_1_to_6"] = [
    bool(passes_1_to_6(run_by_label[label]["panel"], anchor_panel)) for label in combined.index
]
combined["failed_1_to_6"] = [
    failing_constraints_v3(run_by_label[label]["panel"], anchor_panel, None, skip_placebo=True)
    for label in combined.index
]

COMBINED_COLUMNS = [
    "source", "family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta",
    "mean_invested", "late_cagr", "late_ulcer", "cagr_sacrifice_pp", "control_ref",
    "passes_v3", "failed", "passes_1_to_6", "failed_1_to_6", "late_ok",
]
display(combined[COMBINED_COLUMNS])

non_anchor = combined[combined.index != "anchor"]
print(f"Runs passing all seven v3 constraints:      "
      f"{list(non_anchor.index[non_anchor['passes_v3']]) or 'none'}")
print(f"Runs passing constraints 1-6:               "
      f"{list(non_anchor.index[non_anchor['passes_1_to_6']]) or 'none'}")
print(f"Runs passing constraints 1-6 AND late_ok:   "
      f"{list(non_anchor.index[non_anchor['passes_1_to_6'] & non_anchor['late_ok']]) or 'none'}")
print(f"Runs with an EMPTY failure set under 1-6:   "
      f"{list(non_anchor.index[non_anchor['failed_1_to_6'] == '']) or 'none'}")
'''))

# ---------------------------------------------------------------------------------------------
# 6. Per-notebook plateau summary
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Per-notebook plateau summary

Each lead's own plateau rule, recomputed here from this kernel's runs and then compared against
the Boolean the source notebook froze in its manifest. A disagreement would mean the source
notebook's plateau logic and this one differ, which matters more than either result.

- **Lead 1 (NB21)**: a centre N qualifies only if it and both 5-step neighbours pass constraints
  1-6 and the late period. N = 5 and N = 60 are boundary members: neighbours only, never centres.
- **Lead 2 (NB22)**: the centre is `complementary_18`; the plateau is every point of the
  {10, 12, 14, 16, 18, 20, 24} grid passing v3 and the late period, and the four
  window-sensitivity runs are reported beside it.
- **Lead 3 (NB23)**: the centre is `swap__centre`; the plateau is all ten neighbours passing v3
  and the late period. `swap__require_scored` is a policy alternative reported beside the
  plateau, never part of it.
"""))
cells.append(code('''def ok_1_to_6_and_late(label: str) -> bool:
    """Constraints 1-6 plus the late period. A missing run is False, never True."""
    entry = run_by_label.get(label)
    if entry is None:
        return False
    return bool(passes_1_to_6(entry["panel"], anchor_panel)
                and late_period_ok_v3(entry["panel"], anchor_panel))


def ok_v3_and_late(label: str) -> bool:
    """All seven v3 constraints plus the late period. A missing run is False, never True."""
    entry = run_by_label.get(label)
    if entry is None:
        return False
    return bool(passes_constraints_v3(entry["panel"], anchor_panel, family)
                and late_period_ok_v3(entry["panel"], anchor_panel))


nb21_rows = []
for n in FAMILY_CENTRES:
    centre_ok = ok_1_to_6_and_late(f"drop_{n}")
    lower_ok, upper_ok = ok_1_to_6_and_late(f"drop_{n - 5}"), ok_1_to_6_and_late(f"drop_{n + 5}")
    recorded = MANIFESTS[21]["plateau"][str(int(n))]
    nb21_rows.append({
        "n": n, "centre_ok": centre_ok, "lower_ok": lower_ok, "upper_ok": upper_ok,
        "plateau_ok": bool(centre_ok and lower_ok and upper_ok),
        "simple_rule_eligible": bool(centre_ok and lower_ok and upper_ok),
        "masked_centre_run_present": f"drop_{n}__without_top_vault" in run_by_label,
        "manifest_plateau_ok": bool(recorded["plateau_ok"]),
        "agrees_with_manifest": bool(bool(centre_ok and lower_ok and upper_ok) == recorded["plateau_ok"]),
        #: The COMPLETE reason the centre is not ok, never a prefix of it. The first draft
        #: appended "late period" only when the 1-6 string was empty, so a centre that failed
        #: both a constraint and the late period was reported as failing only the constraint -
        #: the exact under-reporting this track has made three times before.
        "binding_constraints": ", ".join(
            part for part in (
                failing_constraints_v3(
                    run_by_label[f"drop_{n}"]["panel"], anchor_panel, None, skip_placebo=True
                ),
                "" if late_period_ok_v3(run_by_label[f"drop_{n}"]["panel"], anchor_panel)
                else "late period",
            ) if part
        ),
    })
nb21_plateau = pd.DataFrame(nb21_rows).set_index("n")
print("Lead 1 (NB21) - the volatility-matched family, constraints 1-6 and the late period:")
display(nb21_plateau)
NB21_ELIGIBLE = [int(n) for n in nb21_plateau.index[nb21_plateau["simple_rule_eligible"]]]
print(f"simple_rule_eligible centres: {NB21_ELIGIBLE or 'none'}   "
      f"(manifest recorded {MANIFESTS[21]['eligible_centres'] or 'none'})")
'''))
cells.append(code('''#: NB22's manifest records the grid as `passes_v3 AND late_ok` under `plateau.booleans`, and the
#: window-sensitivity runs as `passes_v3` alone under `window_sensitivity`. The comparison below
#: is made against whichever of the two each row's manifest entry actually means, so an agreement
#: here is a real agreement rather than two different Booleans that happen to be both False.
nb22_rows = []
for p in COMPLEMENTARY_GRID:
    label = f"complementary_{p}"
    nb22_rows.append({
        "label": label, "is_centre": p == COMPLEMENTARY_CENTRE,
        "passes_v3": bool(passes_constraints_v3(run_by_label[label]["panel"], anchor_panel, family)),
        "late_ok": bool(late_period_ok_v3(run_by_label[label]["panel"], anchor_panel)),
        "point_ok": ok_v3_and_late(label),
        "manifest_means": "passes_v3 and late_ok",
        "manifest_boolean": bool(MANIFESTS[22]["plateau"]["booleans"][label]),
        "recomputed_equivalent": ok_v3_and_late(label),
        "failed": failing_constraints_v3(run_by_label[label]["panel"], anchor_panel, family),
    })
for label in WINDOW_SENSITIVITY:
    nb22_rows.append({
        "label": label, "is_centre": False,
        "passes_v3": bool(passes_constraints_v3(run_by_label[label]["panel"], anchor_panel, family)),
        "late_ok": bool(late_period_ok_v3(run_by_label[label]["panel"], anchor_panel)),
        "point_ok": ok_v3_and_late(label),
        "manifest_means": "passes_v3 only",
        "manifest_boolean": bool(MANIFESTS[22]["window_sensitivity"][label]["passes_v3"]),
        "recomputed_equivalent": bool(
            passes_constraints_v3(run_by_label[label]["panel"], anchor_panel, family)
        ),
        "failed": failing_constraints_v3(run_by_label[label]["panel"], anchor_panel, family),
    })
nb22_plateau = pd.DataFrame(nb22_rows).set_index("label")
nb22_plateau["agrees_with_manifest"] = (
    nb22_plateau["recomputed_equivalent"] == nb22_plateau["manifest_boolean"]
)
print("Lead 2 (NB22) - complementary downside selection, adoption rule v3 with the family as the "
      "constraint-7 comparator:")
display(nb22_plateau)
NB22_CENTRE_OK = ok_v3_and_late(f"complementary_{COMPLEMENTARY_CENTRE}")
NB22_PLATEAU_OK = all(ok_v3_and_late(f"complementary_{p}") for p in COMPLEMENTARY_GRID)
NB22_WINDOW_OK = all(ok_v3_and_late(label) for label in WINDOW_SENSITIVITY)
NB22_LOVO_PRESENT = "complementary_18__without_top_vault" in run_by_label
print(f"centre_ok={NB22_CENTRE_OK}  plateau_ok={NB22_PLATEAU_OK}  "
      f"window_sensitivity_ok={NB22_WINDOW_OK}  leave_one_vault_out_present={NB22_LOVO_PRESENT}")
print(f"(manifest recorded plateau_ok={MANIFESTS[22]['gates']['plateau_ok']}, "
      f"window_sensitivity_ok={MANIFESTS[22]['window_sensitivity_ok']}, "
      f"leave_one_vault_out executed={MANIFESTS[22]['leave_one_vault_out']['executed']})")
'''))
cells.append(code('''nb23_rows = []
for label in [SWAP_CENTRE_LABEL] + SWAP_NEIGHBOUR_LABELS + [SWAP_POLICY_LABEL]:
    key = ("centre" if label == SWAP_CENTRE_LABEL
           else label.replace("swap__", "") if label in SWAP_NEIGHBOUR_LABELS else None)
    recorded = MANIFESTS[23]["plateau"].get(key) if key is not None else \\
        MANIFESTS[23]["policy_alternative"]["passes"]
    nb23_rows.append({
        "label": label,
        "role": ("centre" if label == SWAP_CENTRE_LABEL
                 else "policy alternative (never part of the plateau)"
                 if label == SWAP_POLICY_LABEL else "plateau neighbour"),
        "passes_v3": bool(passes_constraints_v3(run_by_label[label]["panel"], anchor_panel, family)),
        "late_ok": bool(late_period_ok_v3(run_by_label[label]["panel"], anchor_panel)),
        "point_ok": ok_v3_and_late(label),
        "manifest_boolean": bool(recorded),
        "failed": failing_constraints_v3(run_by_label[label]["panel"], anchor_panel, family),
    })
nb23_plateau = pd.DataFrame(nb23_rows).set_index("label")
nb23_plateau["agrees_with_manifest"] = nb23_plateau["point_ok"] == nb23_plateau["manifest_boolean"]
print("Lead 3 (NB23) - the incumbent composite with only its Sortino leg swapped:")
display(nb23_plateau)
NB23_CENTRE_OK = ok_v3_and_late(SWAP_CENTRE_LABEL)
NB23_PLATEAU_OK = all(ok_v3_and_late(label) for label in SWAP_NEIGHBOUR_LABELS)
NB23_LOVO_PRESENT = "swap__centre__without_top_vault" in run_by_label
print(f"centre_ok={NB23_CENTRE_OK}  plateau_ok={NB23_PLATEAU_OK}  "
      f"leave_one_vault_out_present={NB23_LOVO_PRESENT}")
print(f"(manifest recorded plateau_ok={MANIFESTS[23]['plateau']['plateau_ok']}, "
      f"leave_one_vault_out executed={MANIFESTS[23]['leave_one_vault_out']['executed']})")

PLATEAU_AGREEMENT = bool(
    nb21_plateau["agrees_with_manifest"].all()
    and nb22_plateau["agrees_with_manifest"].all()
    and nb23_plateau["agrees_with_manifest"].all()
)
print(f"\\nEvery recomputed plateau Boolean agrees with the frozen manifest: {PLATEAU_AGREEMENT}")
'''))

# ---------------------------------------------------------------------------------------------
# 7. Family-wise joint test
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Family-wise test over the complete executed family

`family_wise_joint()` stacks the anchor and every candidate into one aligned matrix of cycle
returns and resamples them with **common block indices**, so a draw is one bootstrap history
experienced by all of them and candidate-candidate dependence is preserved. Each candidate's
bootstrap distribution of (its Sharpe - the anchor's Sharpe) is centred on its observed
difference, which is the no-difference null, and the maximum across the family is taken per draw.
`p = (1 + #{max_null >= observed_max}) / (draws + 1)`, B = 999, block 10, seed 0.

The family passed in is **every non-anchor run this notebook executed** - all 35, including the
runs that failed badly and including the policy alternative. Passing only the survivors is what
this test exists to prevent. The exact membership is printed below.

**What it cannot do.** It corrects for having tried 35 configurations. It cannot correct for the
adaptive research history that chose *which mechanisms to try at all*: NB14-NB19 ran a different
25-odd configurations before this plan existed, the three leads here were selected by reading
those results, and lead 1 in particular was promoted from control to candidate precisely because
its control result looked good. No resampling of these 126 cycles can price that in. A small
p-value here would mean "the best of these 35 is unlikely under the no-difference null", not "the
best of these 35 is a real effect".
"""))
cells.append(code('''FAMILY_WISE_MEMBERSHIP = [entry["label"] for entry in runs if entry["label"] != "anchor"]
print(f"Family size: {len(FAMILY_WISE_MEMBERSHIP)}")
print("Exact membership:")
display(pd.DataFrame({
    "label": FAMILY_WISE_MEMBERSHIP,
    "source": [SOURCE_OF[label] for label in FAMILY_WISE_MEMBERSHIP],
    "role": [run_by_label[label]["family"] for label in FAMILY_WISE_MEMBERSHIP],
    "cycle_sharpe": [float(run_by_label[label]["panel"]["cycle_sharpe"]) for label in FAMILY_WISE_MEMBERSHIP],
}).set_index("label"))

fw_summary, fw_observed = family_wise_joint(FAMILY_WISE_MEMBERSHIP)
display(fw_summary.set_index("metric"))
print("Per-candidate observed Sharpe difference from the anchor, best first:")
display(fw_observed.to_frame("sharpe_minus_anchor"))
FAMILY_WISE_P = float(fw_summary.set_index("metric").loc["Family-wise p-value", "value"])
FAMILY_WISE_BEST = float(fw_summary.set_index("metric").loc["Best observed Sharpe improvement", "value"])
print(f"\\nFamily-wise p-value over {len(FAMILY_WISE_MEMBERSHIP)} candidates: {FAMILY_WISE_P:.4f}")
print("This corrects for the 35 configurations tried here. It does NOT correct for the adaptive")
print("research history that chose which three mechanisms were worth trying at all, nor for lead 1")
print("having been promoted from control to candidate after its control result was seen.")
'''))

# ---------------------------------------------------------------------------------------------
# 8. Charts
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The frontier: every run in the plan

Cycle Sharpe against cycle volatility, every executed run overlaid, coloured by source notebook.
The volatility-matched family is drawn as a line in the order of its drop count, which is the
shape constraint 7 compares against; the anchor is marked separately.
"""))
cells.append(code('''import plotly.graph_objects as go

plot_frame = combined.reset_index()
fig = px.scatter(
    plot_frame[plot_frame["label"] != "anchor"],
    x="cycle_vol", y="cycle_sharpe", color="source", hover_name="label",
    title="Every run in the stability-leads plan against the volatility-matched family",
)
family_line = family.sort_values("cycle_vol")
fig.add_trace(go.Scatter(
    x=family_line["cycle_vol"], y=family_line["cycle_sharpe"], mode="lines",
    name="volatility-matched family (line)", line=dict(color="grey", dash="dash"),
))
fig.add_trace(go.Scatter(
    x=[float(anchor_panel["cycle_vol"])], y=[float(anchor_panel["cycle_sharpe"])],
    mode="markers+text", name="anchor", text=["anchor"], textposition="top center",
    marker=dict(size=18, symbol="star", color="black"),
))
fig.update_layout(xaxis_title="cycle volatility", yaxis_title="cycle Sharpe")
fig.show()
'''))

cells.append(md("""# Equity curves: the anchor and each lead's centre

The anchor, `drop_30` (lead 1's best single point, and the row that sets constraint 7's bar),
`complementary_18` (lead 2's pre-registered centre) and `swap__centre` (lead 3's centre). Log
scale, because two of the four lose a fifth of the book.
"""))
cells.append(code('''CURVE_LABELS = ["anchor", "drop_30", f"complementary_{COMPLEMENTARY_CENTRE}", SWAP_CENTRE_LABEL]
fig = go.Figure()
for label in CURVE_LABELS:
    eq = run_by_label[label]["equity"]
    fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name=label, mode="lines"))
for name, x in (("regime break", "2026-04-01"), ("late period start", "2026-07-01")):
    #: `add_vline()` raises a TypeError on a datetime x-axis here - its annotation-position
    #: averaging does integer arithmetic on Timestamps. `add_shape()` plus `add_annotation()` is
    #: the equivalent lower-level call that avoids it.
    fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, xref="x", yref="paper",
                  line=dict(dash="dot", color="grey"))
    fig.add_annotation(x=x, y=1, yref="paper", text=name, showarrow=False, yanchor="bottom")
fig.update_layout(title="Anchor against each lead's centre", yaxis_type="log",
                  yaxis_title="equity (USD, log scale)")
fig.show()

display(pd.DataFrame([
    {
        "label": label,
        "final_equity_usd": float(run_by_label[label]["equity"].iloc[-1]),
        "cagr": float(run_by_label[label]["panel"]["cagr"]),
        "cycle_sharpe": float(run_by_label[label]["panel"]["cycle_sharpe"]),
        "ulcer": float(run_by_label[label]["panel"]["ulcer"]),
        "max_dd": float(run_by_label[label]["panel"]["max_dd"]),
    }
    for label in CURVE_LABELS
]).set_index("label"))
'''))

# ---------------------------------------------------------------------------------------------
# 9. Limitation A - the comparator is misnamed
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Limitation 1: the comparator is misnamed

The `vol_matched_drop_count` family has been called *volatility avoidance* since NB15, and it is
constraint 7's comparator throughout this plan. NB21 found that most of what it removes is not
volatile: `inverse_vol` needs 90 observations, a vault that does not have them gets exactly 0.0,
and 0.0 sorts to the front of the ascending inverse-volatility order. The drop therefore removes
the **unmeasured** before it removes the volatile.

Recomputed below from this kernel's own `VOL_DROP_LOG` - the record `decide_trades` writes at the
moment of the decision, not an offline reconstruction, which could not mirror `is_good_pair`, the
quarantine list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the momentum gate, strict admission or the
tie order.

**What this changes and what it does not.** The mechanism should be described as a
**data-availability filter with a volatility tail**, not as volatility avoidance. It remains a
legitimate comparator: it is the simplest thing that reliably de-risks this book, it needs one
integer, and a new mechanism that cannot beat it has not earned its complexity. What was wrong
was the description, and the description is what a reader uses to decide whether a result
generalises. "Dropping the 30 most volatile candidates earns 11 points of CAGR" would be an
economic claim; "dropping the 30 least-measurable candidates earns 11 points of CAGR" is a claim
about this archive's reporting behaviour, and it is the second one that the data supports.
"""))
cells.append(code('''drop_rows = []
for n in FAMILY_DROPS:
    log = run_by_label[f"drop_{n}"]["vol_drop_log"]
    if not log:
        drop_rows.append({"n": n, "decision_dates": 0})
        continue
    pool = np.array([record["pool_size"] for record in log.values()], dtype=float)
    dropped = np.array([len(record["dropped_ids"]) for record in log.values()], dtype=float)
    no_estimate = np.array([len(record["no_estimate_dropped"]) for record in log.values()], dtype=float)
    drop_rows.append({
        "n": n,
        "decision_dates": len(log),
        "mean_pool_size": float(pool.mean()),
        "mean_dropped": float(dropped.mean()),
        "mean_no_volatility_estimate": float(no_estimate.mean()),
        "mean_measured_removals": float((dropped - no_estimate).mean()),
        "share_of_removals_with_no_estimate": float(no_estimate.sum() / dropped.sum())
        if dropped.sum() else float("nan"),
        "no_drop_branch_share": float((pool <= n).mean()),
    })
drop_composition = pd.DataFrame(drop_rows).set_index("n")
display(drop_composition)

total_removals = float(sum(
    len(record["dropped_ids"])
    for n in FAMILY_DROPS for record in run_by_label[f"drop_{n}"]["vol_drop_log"].values()
))
total_no_estimate = float(sum(
    len(record["no_estimate_dropped"])
    for n in FAMILY_DROPS for record in run_by_label[f"drop_{n}"]["vol_drop_log"].values()
))
N30_NO_ESTIMATE_SHARE = float(drop_composition.loc[30, "share_of_removals_with_no_estimate"])
POOLED_NO_ESTIMATE_SHARE = total_no_estimate / total_removals
print(f"At N = 30, {drop_composition.loc[30, 'mean_no_volatility_estimate']:.2f} of "
      f"{drop_composition.loc[30, 'mean_dropped']:.2f} removals per decision date "
      f"({N30_NO_ESTIMATE_SHARE:.1%}) have NO volatility estimate at all.")
print(f"Pooled over all {int(total_removals):,} removals in the twelve-member family, "
      f"{POOLED_NO_ESTIMATE_SHARE:.2%} had no volatility estimate.")
print(f"The no-drop branch (pool <= N) fired on "
      f"{drop_composition['no_drop_branch_share'].max():.1%} of decision dates at worst.")
print()
print("The comparator is a data-availability filter with a volatility tail. It is kept as the")
print("constraint-7 bar because it is the best simple thing available, but calling it")
print("'volatility avoidance' overstates what the mechanism is doing.")
'''))

# ---------------------------------------------------------------------------------------------
# 10. Limitation B - constraint 7 was not discriminating
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Limitation 2: constraint 7 was not discriminating on this snapshot

Constraint 7 is `cycle_sharpe >= placebo_ref_observed(family, cycle_vol) + 0.10`: the best
observed control at or below the candidate's own volatility, plus a 0.10 Sharpe complexity
premium. It was pre-registered in the plan before any of these runs existed, and it stays exactly
as written. **Rule 2 forbids retuning a threshold after seeing a result**, so nothing below
changes it; this section records that it was badly placed and says what should replace it in a
future plan.

The comparator turns out to be a **single isolated point**. `drop_30` posts a cycle Sharpe far
above every other family member, and it is quieter than the anchor, so it sets the bar for almost
the whole volatility range the plan operates in. The bar is therefore roughly 2.85 - a level the
**anchor itself** does not reach, and neither does any other family member. A constraint that the
incumbent fails is not separating good candidates from bad ones; it is a constant.

It did not change any verdict here: NB22's and NB23's centres fail five or six other constraints
first, and constraint 7 is inapplicable to NB21. That is luck, not design.
"""))
cells.append(code('''anchor_vol = float(anchor_panel["cycle_vol"])
at_or_below = family[family["cycle_vol"] <= anchor_vol]
comparator_label = at_or_below["cycle_sharpe"].idxmax() if len(at_or_below) else family["cycle_vol"].idxmin()
anchor_reference = placebo_ref_observed(family, anchor_vol)

print(f"Anchor cycle volatility {anchor_vol:.6f}, cycle Sharpe {float(anchor_panel['cycle_sharpe']):.6f}")
print(f"Family members at or below that volatility: {len(at_or_below)} of {len(family)}")
print(f"Constraint-7 comparator for the anchor: {comparator_label} at cycle Sharpe {anchor_reference:.6f}")
print(f"Bar the anchor would have to clear:      {anchor_reference + PLACEBO_MARGIN_V3:.6f}")
print(f"Does the ANCHOR ITSELF pass constraint 7 against this family? "
      f"{bool(float(anchor_panel['cycle_sharpe']) >= anchor_reference + PLACEBO_MARGIN_V3)}")
print()

constraint7 = []
for label in ["anchor"] + [f"drop_{n}" for n in FAMILY_DROPS]:
    row = run_by_label[label]["panel"]
    reference = placebo_ref_observed(family, float(row["cycle_vol"]))
    constraint7.append({
        "label": label, "cycle_vol": float(row["cycle_vol"]),
        "cycle_sharpe": float(row["cycle_sharpe"]),
        "control_ref": reference, "bar": reference + PLACEBO_MARGIN_V3,
        "clears_constraint_7": bool(float(row["cycle_sharpe"]) >= reference + PLACEBO_MARGIN_V3),
    })
constraint7 = pd.DataFrame(constraint7).set_index("label")
display(constraint7)
print(f"Family members (or the anchor) that clear constraint 7 against their own family: "
      f"{list(constraint7.index[constraint7['clears_constraint_7']]) or 'none'}")
print()
comparator_n = int(str(comparator_label).replace("drop_", ""))
neighbour_labels = [f"drop_{comparator_n - 5}", f"drop_{comparator_n + 5}"]
neighbour_ok = {label: ok_1_to_6_and_late(label) for label in neighbour_labels}
print(f"The comparator is set by a SINGLE point: {comparator_label} at cycle Sharpe "
      f"{float(family.loc[comparator_label, 'cycle_sharpe']):.4f}, against a family median of "
      f"{float(family['cycle_sharpe'].median()):.4f}.")
print(f"Its own 5-step neighbours, on constraints 1-6 plus the late period: "
      + ", ".join(
          f"{label} at cycle Sharpe {float(family.loc[label, 'cycle_sharpe']):.4f}, "
          f"{'passes' if neighbour_ok[label] else 'FAILS'}"
          for label in neighbour_labels
      ) + ".")
print(f"Both neighbours pass: {all(neighbour_ok.values())}. The point that sets the bar is "
      f"therefore {'plateau-supported' if all(neighbour_ok.values()) else 'NOT plateau-supported'}"
      f" - the same test every candidate in this plan had to meet.")
print()
print("RECOMMENDED REPLACEMENT FOR A FUTURE PLAN - not applied here, recorded only:")
print("  1. Require the comparator point to be PLATEAU-SUPPORTED: the reference is the best")
print("     observed control at or below the candidate's volatility WHOSE OWN 5-STEP NEIGHBOURS")
print("     also pass constraints 1-6, falling back to the MEDIAN cycle Sharpe of the members at")
print("     or below that volatility when no member qualifies (as none does here). An isolated")
print("     spike then cannot set the bar for the whole range, which is the actual defect - a")
print("     single lucky N is exactly the kind of result the plateau rule exists to distrust")
print("     everywhere else in this plan.")
print("  2. Include N = 0 in the comparator family explicitly. The plan's own docstring says the")
print("     grid is N in {0, 5, ..., 60}, but FAMILY_DROPS starts at 5. It happens not to matter")
print("     here only because drop_5 is bit-identical to the anchor, which is an accident of this")
print("     snapshot rather than a property of the design.")
print("  3. State the bar as a NUMBER at pre-registration time, computed from the previous plan's")
print("     frozen family, rather than as a formula evaluated against a family that the same")
print("     notebook is about to run. A comparator that moves with the data cannot be checked for")
print("     placement before results exist, which is how this one got past review.")
'''))

# ---------------------------------------------------------------------------------------------
# 11. Limitation C - NB20's ceiling on reading an ulcer improvement
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Limitation 3: NB20's ceiling on how any ulcer improvement may be read

NB20 measured what stale reporting does to the anchor's own risk numbers. Dropping the 11 of 126
cycles on which a majority of the invested book sat inside a five-day-plus gap moves the anchor's
ulcer index from 0.017964 to 0.018759, **+4.4%**, and cycle volatility from 0.154278 to 0.160916,
+4.3% (NB20 cell 39). Loosening the criterion to a three-day gap gives +10.4% and loosening the
majority threshold to a quarter of the book gives +11.1% (NB20 cell 39). Maximum drawdown is
unchanged at -4.45% in every variant, so the anchor's worst drawdown did not happen inside a
stale window.

Adoption rule v3 requires a **15%** ulcer improvement. The staleness sensitivity spans
**+4.4% to +11.2%** of the anchor's ulcer (NB20's heading rounds the upper end to +11.1%) -
between a quarter and three-quarters of that whole decision margin. Both quantities are
percentages of the anchor's measured ulcer, so a margin over the bar and a point on the band are
directly comparable. **A candidate that clears the ulcer constraint by less than that band is
wide cannot be read as clean evidence of a risk reduction.**

What this does *not* establish: NB20 re-measured the **anchor** only. It never measured the
candidate-minus-anchor difference in reporting bias, and it is that difference, not the anchor's
own level, that would have to move for a candidate's ulcer improvement to be an artefact. The
band is therefore a limit on how the improvement may be read, not a demonstration that the
improvement is spurious. Limitation 1 is what makes a differential plausible - the mechanism
selects on measurement availability - and that is a mechanism, not a measurement.

NB20's own Robustness section is explicit that this is a sensitivity and not a correction: it
removes observations rather than recovering an unobserved path, and because the archive cannot
separate "not polled" from "polled and unchanged", the figure is an upper bound on this test
rather than a central estimate. It is used here only as a **band of indistinguishability**, never
as an estimate of true risk.
"""))
cells.append(code('''#: NB20 cell 39, the stale-cycle sensitivity. Quoted, not recomputed: NB20 executed no variant
#: run, and re-deriving its archive analysis here would be a second implementation of the same
#: measurement rather than a check on it.
NB20_ULCER_SENSITIVITY = {
    "as measured": 0.017964,
    "drop >50% stale (5+ d), the pre-registered criterion": 0.018759,
    "drop >75% stale (5+ d)": 0.018640,
    "drop >25% stale (5+ d)": 0.019971,
    "drop >50% stale (3+ d)": 0.019835,
}
sensitivity = pd.DataFrame([
    {"variant": name, "ulcer": value,
     "pct_of_measured_ulcer": (value / NB20_ULCER_SENSITIVITY["as measured"] - 1.0) * 100.0}
    for name, value in NB20_ULCER_SENSITIVITY.items()
]).set_index("variant")
display(sensitivity)

STALE_BAND_LOW = float(sensitivity.loc["drop >50% stale (5+ d), the pre-registered criterion",
                                       "pct_of_measured_ulcer"])
STALE_BAND_HIGH = float(sensitivity["pct_of_measured_ulcer"].max())
REQUIRED_ULCER_IMPROVEMENT_PCT = ULCER_IMPROVEMENT_FRAC * 100.0
print(f"Staleness band on the anchor's ulcer: +{STALE_BAND_LOW:.1f}% to +{STALE_BAND_HIGH:.1f}%")
print(f"Adoption rule v3 requires an ulcer improvement of {REQUIRED_ULCER_IMPROVEMENT_PCT:.0f}%")
print(f"The band is {STALE_BAND_LOW / REQUIRED_ULCER_IMPROVEMENT_PCT:.0%} to "
      f"{STALE_BAND_HIGH / REQUIRED_ULCER_IMPROVEMENT_PCT:.0%} of the decision margin.")
print()

anchor_ulcer = float(anchor_panel["ulcer"])
ulcer_rows = []
for entry in runs:
    if entry["label"] == "anchor":
        continue
    ulcer = float(entry["panel"]["ulcer"])
    improvement = (anchor_ulcer - ulcer) / anchor_ulcer * 100.0
    margin = improvement - REQUIRED_ULCER_IMPROVEMENT_PCT
    ulcer_rows.append({
        "label": entry["label"], "source": SOURCE_OF[entry["label"]], "ulcer": ulcer,
        "ulcer_improvement_pct": improvement,
        "clears_the_15pct_bar": bool(improvement >= REQUIRED_ULCER_IMPROVEMENT_PCT),
        "margin_over_the_bar_pp": margin,
        #: Named for what the test actually is. The comparison is margin <= the TOP of the band,
        #: so a margin BELOW the band's lower end qualifies too - drop_50's +4.33 pp is below
        #: +4.4%, not inside +4.4% to +11.2%. "Inside the band" was the wrong word for it.
        "margin_no_larger_than_the_top_of_the_band": bool(
            improvement >= REQUIRED_ULCER_IMPROVEMENT_PCT and margin <= STALE_BAND_HIGH
        ),
    })
ulcer_reading = pd.DataFrame(ulcer_rows).set_index("label").sort_values(
    "ulcer_improvement_pct", ascending=False)
display(ulcer_reading)

clearing = ulcer_reading[ulcer_reading["clears_the_15pct_bar"]]
affected = ulcer_reading[ulcer_reading["margin_no_larger_than_the_top_of_the_band"]]
print(f"Runs clearing the 15% ulcer bar: {list(clearing.index) or 'none'}")
print(f"Of those, runs whose margin over the bar is no larger than the TOP of the staleness")
print(f"band (+{STALE_BAND_HIGH:.1f}%): {list(affected.index) or 'none'}")
print()
print("AFFECTED. Lead 1's ulcer improvements are the results this ceiling bites on: every run")
print("that clears the 15% bar is a family member, and every one of them clears it by a")
print(f"single-digit margin - +{clearing['margin_over_the_bar_pp'].min():.2f} to "
      f"+{clearing['margin_over_the_bar_pp'].max():.2f} pp of the anchor's ulcer - which is the")
print(f"same order as the +{STALE_BAND_LOW:.1f}% to +{STALE_BAND_HIGH:.1f}% the anchor's own ulcer")
print("moves under NB20's staleness variants. Both quantities are percentages of the anchor's")
print("measured ulcer, so they are on the same scale and the comparison is arithmetically valid.")
print()
print("WHAT THAT DOES AND DOES NOT ESTABLISH. NB20 re-measured the ANCHOR only. It did not measure")
print("the candidate-minus-anchor difference in reporting bias, and it is that difference, not the")
print("anchor's own level, that would have to move for these improvements to be an artefact. So")
print("the correct statement is the weaker one: a sensitivity of this size on the anchor alone is")
print("large enough relative to these margins that the ulcer improvement cannot be read as clean")
print("evidence of a risk reduction. It is NOT a demonstration that the improvement IS a reporting")
print("artefact. Limitation 1 - the mechanism selects on measurement availability - is what makes")
print("a differential plausible, and it is a mechanism, not a measurement.")
print()
print("NOT AFFECTED. Leads 2 and 3 are nowhere near the band. Their ulcers are WORSE than the")
print("anchor's, not better, by a multiple rather than by a few points, so no plausible")
print("re-measurement of staleness turns either into a pass. Their rejections stand independently")
print("of NB20. The same is true of the CAGR, Sharpe and beta failures throughout the plan:")
print("NB20's finding constrains the reading of an ulcer IMPROVEMENT and nothing else.")
'''))

# ---------------------------------------------------------------------------------------------
# 12. Prospective shadow specification
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The prospective shadow specification

Fixed here, before any new data arrives, and written whether or not there is a winner. The
expected outcome of this plan is that nothing is adopted; this section is what *would* be used if
a future candidate qualified, and freezing it now is the only way it can be a prospective test
rather than another in-sample one.

ADOPT in this plan means **admission to this shadow protocol**, not authorisation to deploy
capital. Everything below the freeze line is monitoring evidence about whether a mechanism
behaves as backtested; none of it is a deployment proof.
"""))
cells.append(code('''SHADOW_SPECIFICATION = {
    "purpose": (
        "Admission to a prospective shadow run. ADOPT never means capital is deployed; it means "
        "the candidate is simulated forward on data that did not exist when it was chosen."
    ),
    "start_date": "the first strategy decision cycle on or after 2026-09-15",
    "why_that_date": (
        "The archive this plan ran on ends 2026-09-08 and the plan closes 2026-09-13. A start on "
        "2026-09-15 leaves no overlap with any cycle any notebook in this track has seen."
    ),
    "comparator": (
        "the UNCHANGED anchor configuration of 02-better-format.ipynb, run on the SAME decision "
        "dates as the candidate, in the same kernel, from the same universe snapshot. Not a "
        "re-run of the historical anchor, and not a fixed number copied from BASELINE - a "
        "same-clock comparator is the only thing a shadow comparison can be made against."
    ),
    "monitoring_horizon": {
        "minimum_before_any_comparison_is_drawn": "45 decision cycles (90 days)",
        "decision_point": "90 decision cycles (180 days)",
        "why": (
            "The strategy runs a 2-day clock. 90 cycles is the same order as the 126 cycles the "
            "whole backtest window carries, so a shadow read at 90 cycles has roughly the "
            "in-sample window's power and no more. Reading it earlier than 45 cycles is reading "
            "noise, and this specification forbids it."
        ),
    },
    "recorded_every_cycle_not_only_equity": [
        "realised deposit availability (can_deposit() at each attempted entry)",
        "pool-cap fills (whether USDTVLSizeRiskModel bound)",
        "turnover and redemption fees actually paid",
        "mean invested fraction and the count of dates the basket was short of six names",
        "for any candidate with a screen: the screen's own log, per decision date",
        "mark staleness of the held book, per NB20's definition, so an ulcer read can be "
        "discounted by the same measurement the close-out used",
    ],
    "stopping_conditions_any_one_ends_the_shadow_early": [
        "shadow CAGR < 0 over any trailing 45-cycle window after cycle 45",
        "shadow ulcer index > the shadow anchor's ulcer over the same cycles, after cycle 45",
        "mean invested fraction < 0.90 over any trailing 45-cycle window",
        "the data provenance hashes change in a way that alters universe membership, in which "
        "case the shadow restarts rather than continues",
        "a code change to decide_trades, the indicator chain or the parameter defaults - the "
        "frozen override dictionary and the commit that produced it are the shadow, and editing "
        "either starts a new one",
    ],
    "constraint_7_comparator_in_shadow": (
        "constraint 7 needs an observed control family, not only an anchor, so the shadow runs "
        "drop_5 through drop_60 at 5-step spacing alongside the candidate and the anchor, on the "
        "same decision dates in the same kernel, from the frozen code commit. The reference is "
        "placebo_ref_observed() unchanged: the highest cycle Sharpe among shadow family members "
        "whose shadow cycle volatility is at or below the candidate's, plus 0.10. Constraint 7 "
        "applies to any candidate that is NOT itself a member of that family; for a family "
        "member it is a self-comparison and constraints 1-6 are the operative set, exactly as in "
        "this plan. The bar is computed on the shadow window's own family, never carried over "
        "from this notebook's 2.847."
    ),
    "universe_and_provenance_restart_rule": (
        "the four PROVENANCE_PATHS files are hashed at freeze time and at every shadow read. "
        "vault-prices.parquet and binance-price.duckdb are expected to change, because they "
        "append new candles; that alone never restarts the shadow. vault-metadata.json decides "
        "universe membership through deposit-closed status and peak TVL, so a change to it is "
        "checked by re-deriving the admitted address set: an identical set continues the shadow "
        "and any difference restarts it from the next decision cycle. The frozen metadata file "
        "is kept beside the freeze record so this is a diff, not a judgement."
    ),
    "decision_rule_at_90_cycles": [
        "apply adoption rule v3 to the SHADOW window's own panel, with the shadow anchor as the "
        "comparator for constraints 2, 3, 4 and 5, the fixed floors for constraints 1 and 6, and "
        "the shadow family for constraint 7 as defined above",
        "require the paired block-bootstrap lower bound of the candidate-minus-anchor cycle "
        "Sharpe difference to clear -0.10 at block lengths 5, 10 and 20 (common block indices, "
        "seed 0, 1000 draws)",
        "require the ulcer improvement to exceed 15% BY MORE THAN the staleness band measured on "
        "the shadow window itself (NB20's method), not merely to exceed 15%",
        "the staleness band on the shadow window is measured exactly as cell 48 measures it here: "
        "NB20's four variants recomputed on the shadow anchor, the band running from the "
        "pre-registered >50% stale (5+ d) variant to the largest of the four",
        "a pass is monitoring evidence that the mechanism behaves as backtested. It is not a "
        "deployment decision and this plan does not make one.",
    ],
    "what_a_stopping_condition_means": (
        "any stopping condition firing ends the shadow as a REJECT. There is no decision at 90 "
        "cycles for a shadow that stopped, and a stopped shadow is not restarted with the same "
        "candidate on a later window."
    ),
    "if_more_than_one_candidate_qualifies": (
        "they run side by side against the same anchor. The plan does not rank them and this "
        "notebook does not choose between them."
    ),
}
print(json.dumps(SHADOW_SPECIFICATION, indent=1))
'''))
cells.append(code('''#: The literal format an ADOPT would be frozen in. Everything a later reader needs to reproduce
#: the run: the override dictionary exactly as `run_variant()` takes it, the code commit, and the
#: content hashes of every data snapshot the choice was made on.
SHADOW_FREEZE_FORMAT = {
    "label": "<the run label from this plan, e.g. drop_30>",
    "lead": "<1, 2 or 3>",
    "overrides": {"<Parameters attribute>": "<value>"},
    "masked": [],
    "code_commit": "<git rev-parse HEAD of _build/ at freeze time>",
    "data_snapshot_sha256": {"<provenance path>": "<sha256>"},
    "frozen_at": "<YYYY-MM-DD, before the start date above>",
    "shadow_start": "<first decision cycle on or after 2026-09-15>",
    "comparator_overrides": {},
}
print("Freeze format:")
print(json.dumps(SHADOW_FREEZE_FORMAT, indent=1))
print()

#: A worked example, so the format is unambiguous. `drop_30` is the plan's best single result and
#: it is NOT adopted: it failed the plateau, so no leave-one-vault-out run was ever triggered.
#: This is what the entry WOULD look like, not an entry.
PROVENANCE = provenance()
provenance_hashes = {
    row["file"]: row["sha256"] for _i, row in PROVENANCE.iterrows() if row["file"] != "git HEAD"
}
WORKED_EXAMPLE_NOT_ADOPTED = {
    "label": "drop_30",
    "lead": 1,
    "overrides": {"vol_matched_drop_count": 30},
    "masked": [],
    "code_commit": str(PROVENANCE.set_index("file").loc["git HEAD", "sha256"]),
    "data_snapshot_sha256": provenance_hashes,
    "frozen_at": "NOT FROZEN - drop_30 is not adopted",
    "shadow_start": "NOT SCHEDULED",
    "comparator_overrides": {},
    "why_not_adopted": (
        "drop_30 passes all six applicable constraints with an empty failure set, but neither "
        "5-step neighbour does, so plateau_ok is False, no leave-one-vault-out run was triggered, "
        "and an unexecuted robustness run cannot produce a passing flag."
    ),
}
print("Worked example (NOT an adoption):")
print(json.dumps(WORKED_EXAMPLE_NOT_ADOPTED, indent=1))
'''))

# ---------------------------------------------------------------------------------------------
# 13. Verdict
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Overall verdict

Recomputed from this kernel's runs, not read from a manifest. Each lead's own adoption rule is
applied in full: eligibility, the seven constraints (six for lead 1, where constraint 7 is
inapplicable), the late period, the plateau, and leave-one-vault-out by full re-simulation. A
robustness run that was never executed counts as absent, which is a fail.
"""))
cells.append(code('''lead_rows = []

#: Lead 1. The smallest N whose centre, both 5-step neighbours and masked centre all pass
#: constraints 1-6 and the late period.
nb21_qualifying = [
    n for n in NB21_ELIGIBLE
    if ok_1_to_6_and_late(f"drop_{n}__without_top_vault")
]
lead_rows.append({
    "lead": "1 - volatility-matched family (NB21)",
    "centre": "smallest qualifying N",
    "eligible_centres": str(NB21_ELIGIBLE or "none"),
    "plateau_ok": bool(NB21_ELIGIBLE),
    "leave_one_vault_out_ok": bool(nb21_qualifying),
    "within_basket_concentration_ok": "n/a (lead 2 only)",
    "adopt": bool(nb21_qualifying),
    "shadow_candidate": f"drop_{min(nb21_qualifying)}" if nb21_qualifying else None,
})

#: Lead 2. The centre must pass all seven constraints and the late period, every plateau point
#: and every window-sensitivity run must pass, leave-one-vault-out must pass, AND the realised
#: within-basket joint-loss concentration must fall against the anchor. That last gate is the
#: plan's leads table verbatim - "passing the constraint table while the basket still sinks
#: together would mean the proxy failed" - and the first draft of this cell left it out entirely.
#: It needs NB22 Part A's mark matrix, which this close-out does not rebuild, so it is NOT
#: recomputed here and rule 9 applies exactly as it does to an unexecuted masked run: a gate this
#: kernel did not evaluate cannot produce a passing flag. NB22 itself measured the concentration
#: as falling (0.2143 to 0.1876), so this False is "not re-derived here", not "the proxy failed";
#: had the other lead-2 gates passed, this notebook would have had to re-derive it before ADOPT.
NB22_CONCENTRATION_RECOMPUTED_HERE = False
nb22_lovo_ok = ok_v3_and_late("complementary_18__without_top_vault")
lead_rows.append({
    "lead": "2 - complementary downside selection (NB22)",
    "centre": f"complementary_{COMPLEMENTARY_CENTRE}",
    "eligible_centres": f"complementary_{COMPLEMENTARY_CENTRE}",
    "plateau_ok": bool(NB22_CENTRE_OK and NB22_PLATEAU_OK),
    "leave_one_vault_out_ok": bool(nb22_lovo_ok),
    "within_basket_concentration_ok": "False - NOT recomputed in this kernel, fail closed",
    "adopt": bool(NB22_CENTRE_OK and NB22_PLATEAU_OK and NB22_WINDOW_OK and nb22_lovo_ok
                  and NB22_CONCENTRATION_RECOMPUTED_HERE),
    "shadow_candidate": None,
})

#: Lead 3. The centre and all ten neighbours must pass all seven constraints and the late period,
#: and leave-one-vault-out must pass.
nb23_lovo_ok = ok_v3_and_late("swap__centre__without_top_vault")
lead_rows.append({
    "lead": "3 - Sortino leg swap (NB23)",
    "centre": SWAP_CENTRE_LABEL,
    "eligible_centres": SWAP_CENTRE_LABEL,
    "plateau_ok": bool(NB23_CENTRE_OK and NB23_PLATEAU_OK),
    "leave_one_vault_out_ok": bool(nb23_lovo_ok),
    "within_basket_concentration_ok": "n/a (lead 2 only)",
    "adopt": bool(NB23_CENTRE_OK and NB23_PLATEAU_OK and nb23_lovo_ok),
    "shadow_candidate": None,
})

lead_verdicts = pd.DataFrame(lead_rows).set_index("lead")
display(lead_verdicts)

ADOPTED = [row["shadow_candidate"] for row in lead_rows if row["adopt"] and row["shadow_candidate"]]
VERDICT = f"ADOPT {', '.join(ADOPTED)} (to shadow)" if ADOPTED else "NOTHING ADOPTED"
print(f"VERDICT: {VERDICT}")
if not CROSS_CHECK_OK:
    print()
    print("!" * 100)
    print("The cross-check above did NOT reproduce the source notebooks. Read this verdict as")
    print("conditional on a snapshot that differs from the one NB21-NB23 ran on.")
    print("!" * 100)
'''))

cells.append(md("""# What each lead settled, and what it could not

**Every diagnostic figure in this table is QUOTED from the source notebook named in its row, not
recomputed here.** This close-out re-runs the backtests and re-derives the adoption gates; it does
not rebuild NB20's mark archive, NB22's Part A mark matrix or NB23's stage-1 audit. The two
metrics per run that the manifests froze, cycle Sharpe and CAGR, are the only source figures this
kernel checks (cell 29). Read every number below as "NB2x reported this", with NB2x's own
Robustness section attached.
"""))
cells.append(code('''LEAD_SUMMARY = [
    {
        "lead": "0 - mark quality (NB20, DIAGNOSTIC)",
        "settled": (
            "Stale reporting is pervasive but its effect on this track's headline risk numbers is "
            "a low-double-digit percentage rather than a factor: 34.9% of tradable vault-days sit "
            "inside a five-day-plus gap, yet dropping every anchor cycle whose invested book was "
            "mostly stale moves the ulcer index only +4.4% and cycle volatility +4.3%."
        ),
        "could_not": (
            "It cannot recover the unobserved path behind an unmoved mark, and the archive cannot "
            "separate 'not polled' from 'polled and unchanged', so the +4.4% is an upper bound on "
            "that test rather than an estimate of true risk, and no adoption decision may cite it "
            "as one."
        ),
    },
    {
        "lead": "1 - volatility-matched family (NB21, REJECT)",
        "settled": (
            "That the previous plan's control is not a stable mechanism: drop_30 is the best "
            "single number in two plans - 48.99% CAGR at cycle Sharpe 2.747 with an empty failure "
            "set - and one 5-step move in either direction breaks it, so plateau_ok is False at "
            "all ten eligible centres and no leave-one-vault-out run was ever triggered. It also "
            "settled what the mechanism actually does: 70.9% of its removals at N = 30 have no "
            "volatility estimate at all."
        ),
        "could_not": (
            "It cannot say whether drop_30 is a real effect or the best of thirteen draws, because "
            "the family was promoted from control to candidate after its control result had been "
            "seen. It also cannot separate 'holds less volatile vaults' from 'holds vaults that "
            "report often enough to be measured', which is the same confound the ulcer ceiling "
            "describes."
        ),
    },
    {
        "lead": "2 - complementary downside selection (NB22, REJECT)",
        "settled": (
            "That the proxy works and the strategy still fails: within-basket pairwise co-loss "
            "falls from 0.2143 to 0.1876, paired difference -0.0267 with a 95% interval of "
            "[-0.0501, -0.0019], and four-of-six co-loss cycles fall from 24.0% to 20.0% - while "
            "CAGR goes to -17.74%. The mechanism of failure is measured, not guessed: trailing "
            "joint-loss frequency correlates +0.013 with the next cycle's return over heavily "
            "overlapping trailing-window reads, so the screen spends the composite ranking (mean "
            "rank 7.73 of 0-17) on a statistic with no measurable forward association in this "
            "sample - which is a descriptive result on overlapping observations, not a test that "
            "establishes the absence of predictive information. Handing decide_trades exactly "
            "six candidates removes backfill and drops deployment to 92.79%."
        ),
        "could_not": (
            "It cannot test the basket-level version of the idea. joint_loss_frequency scores each "
            "candidate against the cohort median, never against the other five names chosen, so "
            "two vaults that are each complementary to the cohort but identical to each other are "
            "invisible to it. A pairwise-greedy basket search needs a co-movement matrix inside "
            "decide_trades and remains untested."
        ),
    },
    {
        "lead": "3 - Sortino leg swap (NB23, REJECT)",
        "settled": (
            "That the minimal change nobody had run is not a near-anchor replication: it re-ranks "
            "the traded book on 113 of 126 dates (89.68%, mean weight L1 distance 0.720) and lands "
            "at 7.91% CAGR and cycle Sharpe 0.584 with an ulcer of 0.035943, twice the anchor's. "
            "It also settled two measurement questions: the pre-registered forward-fill defect does "
            "not occur on this pool (0 of 18,651 reads, against a 2% trigger), and the '90 mark "
            "event' window is not one horizon - it spans a median 113 calendar days with a 48-520 "
            "day 5th-95th range and a 57.3x dispersion across the cross-section."
        ),
        "could_not": (
            "It cannot attribute the failure to any one property of the replacement leg. Swapping "
            "the component changes horizon, shrinkage, scaling, saturation and NaN behaviour at "
            "once, so nothing here may be read as 'shrinkage hurts' or 'event time hurts'. Because "
            "the 360-day CAGR leg is untouched, it also says nothing about the young cohort that "
            "NB13 found the composite cannot reach."
        ),
    },
]
display(pd.DataFrame(LEAD_SUMMARY).set_index("lead"))
'''))

# ---------------------------------------------------------------------------------------------
# 14. Manifest
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The close-out manifest

Everything a later reader needs without re-running this notebook: the combined verdict, the
cross-check result for every run, and the full-precision metrics of all thirty-six.
"""))
cells.append(code('''MANIFEST_PATH = Path("_build/manifest_24.json")

manifest = {
    "notebook": "24-backtest-closeout.ipynb",
    "plan": "20-stability-leads-plan.md",
    "role": "close-out: every executed run of NB21-NB23 re-run in one kernel, every gate recomputed",
    "verdict": VERDICT,
    "adopted": ADOPTED,
    "source_notebooks": {
        "NB20": "20-research-mark-quality.ipynb - DIAGNOSTIC, no variant runs, no manifest",
        "NB21": MANIFESTS[21]["notebook"],
        "NB22": MANIFESTS[22]["notebook"],
        "NB23": MANIFESTS[23]["notebook"],
    },
    "recorded_source_verdicts": {f"NB{n}": MANIFESTS[n]["verdict"] for n in (21, 22, 23)},
    "anchor_parity": {
        "baseline": {metric: float(value) for metric, value in BASELINE.items()},
        "actual": {metric: float(anchor_panel[metric]) for metric in BASELINE},
        "tolerance": BASELINE_TOLERANCE,
        "worst_abs_diff": float(max(abs(float(anchor_panel[m]) - v) for m, v in BASELINE.items())),
    },
    "cross_check": {
        "tolerance": CROSS_CHECK_TOLERANCE,
        "manifests_agree_with_each_other": MANIFESTS_AGREE,
        "run_inventory_ok": RUN_INVENTORY_OK,
        "all_reproduced": bool(cross_check["reproduced"].all()),
        "cross_check_ok": CROSS_CHECK_OK,
        "worst_sharpe_abs_diff": float(cross_check["sharpe_abs_diff"].max()),
        "worst_cagr_abs_diff": float(cross_check["cagr_abs_diff"].max()),
        "mismatches": [
            {"label": label, "sharpe_abs_diff": float(row["sharpe_abs_diff"]),
             "cagr_abs_diff": float(row["cagr_abs_diff"])}
            for label, row in cross_check[~cross_check["reproduced"]].iterrows()
        ],
    },
    "plateau_agreement_with_source_manifests": PLATEAU_AGREEMENT,
    "lead_verdicts": {
        row["lead"]: {
            "centre": row["centre"], "eligible_centres": row["eligible_centres"],
            "plateau_ok": bool(row["plateau_ok"]),
            "leave_one_vault_out_ok": bool(row["leave_one_vault_out_ok"]),
            "adopt": bool(row["adopt"]), "shadow_candidate": row["shadow_candidate"],
        }
        for row in lead_rows
    },
    "family_wise_joint": {
        "membership": FAMILY_WISE_MEMBERSHIP,
        "family_size": len(FAMILY_WISE_MEMBERSHIP),
        "block": BOOTSTRAP_BLOCK, "draws": 999, "seed": BOOTSTRAP_SEED,
        "best_observed_sharpe_improvement": FAMILY_WISE_BEST,
        "p_value": FAMILY_WISE_P,
        "caveat": (
            "corrects for the 35 configurations executed in this plan; cannot correct for the "
            "adaptive research history that chose which mechanisms to try, nor for lead 1 having "
            "been promoted from control to candidate after its control result was seen"
        ),
    },
    "limitations": {
        "comparator_is_misnamed": {
            "statement": (
                "the vol-matched family is a data-availability filter with a volatility tail, not "
                "volatility avoidance; it is retained as constraint 7's comparator because it is "
                "the best simple mechanism available, but the description was wrong"
            ),
            "share_of_removals_with_no_volatility_estimate_at_n30": N30_NO_ESTIMATE_SHARE,
            "pooled_share_over_the_whole_family": POOLED_NO_ESTIMATE_SHARE,
        },
        "constraint_7_not_discriminating": {
            "statement": (
                "the comparator is the isolated drop_30 spike, so the bar is about 2.85 and the "
                "ANCHOR ITSELF fails it, as does every family member. Pre-registered and left "
                "unchanged (rule 2 forbids retuning after seeing results); a replacement is "
                "recommended for a future plan"
            ),
            "comparator_label": str(comparator_label),
            "comparator_cycle_sharpe": float(anchor_reference),
            "bar": float(anchor_reference + PLACEBO_MARGIN_V3),
            "anchor_cycle_sharpe": float(anchor_panel["cycle_sharpe"]),
            "anchor_clears_constraint_7": bool(
                float(anchor_panel["cycle_sharpe"]) >= anchor_reference + PLACEBO_MARGIN_V3
            ),
            "family_members_clearing_it": [
                str(label) for label in constraint7.index[constraint7["clears_constraint_7"]]
            ],
        },
        "nb20_ulcer_reading_ceiling": {
            "statement": (
                "NB20's stale-cycle sensitivity moves the ANCHOR's ulcer +4.4% to +11.2%, between "
                "a quarter and three-quarters of the adoption rule's 15% ulcer margin, and the "
                "five runs that clear the ulcer constraint clear it by less than that, so their "
                "ulcer improvement cannot be read as clean evidence of a risk reduction. NB20 "
                "re-measured the anchor only and did not measure the candidate-minus-anchor "
                "difference in reporting bias, so this is a limit on the reading, NOT a "
                "demonstration that the improvement IS a reporting artefact"
            ),
            "staleness_band_pct": [STALE_BAND_LOW, STALE_BAND_HIGH],
            "required_improvement_pct": REQUIRED_ULCER_IMPROVEMENT_PCT,
            "runs_clearing_the_bar": [str(label) for label in clearing.index],
            "runs_with_margin_no_larger_than_the_top_of_the_band": [
                str(label) for label in affected.index
            ],
            "affects": "lead 1's ulcer improvements",
            "does_not_affect": (
                "leads 2 and 3, whose ulcers are worse than the anchor's by a multiple, and every "
                "CAGR, Sharpe and beta failure in the plan"
            ),
        },
    },
    "shadow_specification": SHADOW_SPECIFICATION,
    "shadow_freeze_format": SHADOW_FREEZE_FORMAT,
    "lead_summary": LEAD_SUMMARY,
    "runs": {
        entry["label"]: {
            "source": SOURCE_OF[entry["label"]],
            "family": entry["family"],
            "overrides": {k: sorted(v) if isinstance(v, (set, frozenset)) else v
                          for k, v in entry["overrides"].items()},
            "cycle_sharpe": float(entry["panel"]["cycle_sharpe"]),
            "cycle_sortino": float(entry["panel"]["cycle_sortino"]),
            "cycle_vol": float(entry["panel"]["cycle_vol"]),
            "cagr": float(entry["panel"]["cagr"]),
            "ulcer": float(entry["panel"]["ulcer"]),
            "max_dd": float(entry["panel"]["max_dd"]),
            "abs_invested_beta": float(entry["panel"]["abs_invested_beta"]),
            "mean_invested": float(entry["panel"]["mean_invested"]),
            "late_cagr": float(entry["panel"]["late_cagr"]),
            "late_ulcer": float(entry["panel"]["late_ulcer"]),
            "passes_v3": bool(passes_constraints_v3(entry["panel"], anchor_panel, family)),
            "failed_v3": failing_constraints_v3(entry["panel"], anchor_panel, family),
            "passes_1_to_6": bool(passes_1_to_6(entry["panel"], anchor_panel)),
            "failed_1_to_6": failing_constraints_v3(entry["panel"], anchor_panel, None, skip_placebo=True),
            "late_ok": bool(late_period_ok_v3(entry["panel"], anchor_panel)),
            "cross_check": {
                "sources": EXPECTED[entry["label"]]["sources"],
                "expected_cycle_sharpe": float(cross_check.loc[entry["label"], "expected_cycle_sharpe"]),
                "expected_cagr": float(cross_check.loc[entry["label"], "expected_cagr"]),
                "sharpe_abs_diff": float(cross_check.loc[entry["label"], "sharpe_abs_diff"]),
                "cagr_abs_diff": float(cross_check.loc[entry["label"], "cagr_abs_diff"]),
                "reproduced": bool(cross_check.loc[entry["label"], "reproduced"]),
            } if entry["label"] in cross_check.index else {"sources": [], "reproduced": False,
                                                           "note": "no manifest entry for this label"},
        }
        for entry in runs
    },
    "vol_drop_composition": {
        str(int(n)): {
            column: (None if pd.isna(drop_composition.loc[n, column])
                     else float(drop_composition.loc[n, column]))
            for column in drop_composition.columns
        }
        for n in FAMILY_DROPS
    },
    "provenance": PROVENANCE.to_dict(orient="records"),
}

MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=False, default=str))
print(f"Wrote {MANIFEST_PATH.resolve()} ({MANIFEST_PATH.stat().st_size:,} bytes)")
print(f"VERDICT: {VERDICT}")
print(f"Cross-check OK: {CROSS_CHECK_OK}   plateau agreement: {PLATEAU_AGREEMENT}   "
      f"family-wise p: {FAMILY_WISE_P:.4f} over {len(FAMILY_WISE_MEMBERSHIP)} candidates")
'''))

cells += integrity_and_audit_cells()

write_notebook(cells, TRACK_DIR / "24-backtest-closeout.ipynb")
