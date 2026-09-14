import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, INDICATOR_ADDITIONS_PREFILTER, \
    CELL14_REPLACEMENTS_PREFILTER

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()

HEADING = """# NB29 - the stability prefilter, one signal at a time

[NB28](28-research-stability-signal-screen.ipynb) screened thirteen signals for whether they
predict forward stability at all. This backtests the ones that passed, through a single
mechanism: at each decision, among the candidates that reach the ranking step, exclude the
least-stable fraction `q` of those for which the signal is FINITE, then rank and size the
survivors exactly as the incumbent does.

**Verdicts are SHORTLIST or REJECT. There is no ADOPT.** SHORTLIST means admission to the frozen
prospective specification NB31 writes, to be judged on data that does not exist yet. The screen
and this backtest share overlapping 30-day windows, so a passing candidate here is a hypothesis,
not a finding.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) as the anchor,
[28-stable-selection-plan.md](28-stable-selection-plan.md) Draft 2, and NB26's `measured_only`
drop, which this mechanism generalises - `inverse_vol` with a count of 8 reproduces `measured_8`
on every panel metric, verified in
[_build/verify-prefilter.ipynb](_build/verify-prefilter.ipynb). Full window 2026-01-01 to
2026-09-08, in-sample throughout.

## Method

Five exclusion fractions per signal, centre 0.30, permissive - a candidate with no signal value
is KEPT. A strict variant at the centre excludes them instead and is DIAGNOSTIC only: it cannot
inherit the permissive signal's gate-5 pass, because gate 5 is a complete-case statistic and
missingness-as-exclusion is precisely the behaviour it does not test.

Equal `q` is not equal filtering strength: a signal with a higher NaN rate filters a smaller
share of the whole pool at the same `q`. Every run therefore reports its realised exclusion
share, and cross-signal comparisons are made at matched REALISED share, never at matched `q`.

The nine gates of [RESEARCH-RULES.md](RESEARCH-RULES.md) are scored cheapest-first, so an
expensive re-simulation never runs for a candidate that already failed a cheap gate, and every
unexecuted gate is False rather than absent. Gate 9's null permutes the FINITE signal values
within each decision date, leaving every NaN attached to its own vault, and its effectiveness is
asserted on realised CYCLE-RETURN SERIES - NB26's null was one draw repeated ten times and a
count of distinct value maps would not have caught it.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "29-backtest-stability-prefilter",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_PREFILTER},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_PREFILTER)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))

cells.append(md("""## Part 0. Provenance, parity, and what NB28 carried forward

The screen's result is read from `_build/manifest_28.json` rather than re-derived, so gate 5 is
whatever NB28 pre-registered and this notebook cannot quietly re-decide it. The provenance hashes
must match NB28's; if the snapshot moved between the two notebooks, the screen does not describe
this backtest's universe.
"""))
cells.append(code('''import json
from pathlib import Path

display(provenance())
display(assert_anchor_parity_rules())
record_anchor()

manifest_28 = json.loads(Path("_build/manifest_28.json").read_text())
CARRIED = list(manifest_28["carried_to_nb29"])
GATE_5 = {k: bool(v) for k, v in manifest_28["gate_5"].items()}
assert abs(float(manifest_28["delta_annualised_pp"]) - DELTA_ANNUALISED_PP) < 1e-12, \\
    "NB28 screened with a different delta from the one this kernel carries"
print(f"NB28 eligible decisions: {manifest_28['eligible_decisions']} of {manifest_28['logged_decisions']}")
print(f"signals passing gate 5: {[s for s, v in GATE_5.items() if v] or 'none'}")
print(f"carried into NB29: {CARRIED}")
display(pd.DataFrame(manifest_28["screen"]).T[["dates", "stability_clause", "return_clause", "gate_5"]])
'''))

cells.append(md("""## Part 1. The family: five fractions per carried signal

`inverse_vol` always runs, whatever the screen said about it, and is labelled `reference`: it is
the sizing rule's own premise and NB26's `measured_only` drop, so every other signal is read
against it. A signal that failed gate 5 is not backtested at all - that is what "REJECTED without
a backtest" means in the rules.
"""))
cells.append(code('''FRACTIONS = (0.10, 0.20, 0.30, 0.40, 0.50)
CENTRE = 0.30
NEIGHBOURS = (0.20, 0.40)


def label_for(signal: str, fraction: float, suffix: str = "") -> str:
    return f"{signal}_q{int(round(fraction * 100)):02d}{suffix}"


for signal in CARRIED:
    family = "reference" if signal == "inverse_vol" and not GATE_5.get(signal, False) else "candidate"
    for fraction in FRACTIONS:
        run_and_record(label_for(signal, fraction), family,
                       **prefilter_overrides(signal, fraction=fraction))

family_rows = []
for signal in CARRIED:
    for fraction in FRACTIONS:
        label = label_for(signal, fraction)
        entry = run_by_label[label]
        shares = prefilter_exclusion_frame(entry)
        row = entry["panel"].copy()
        row["signal"] = signal
        row["q"] = fraction
        row["realised_excluded_share"] = float(shares["excluded_share"].mean())
        row["mean_excluded"] = float(shares["excluded"].mean())
        row["mean_nan"] = float(shares["nan"].mean())
        row["mean_pool"] = float(shares["pool_size"].mean())
        family_rows.append(row)
family_frame_29 = pd.DataFrame(family_rows).set_index("label")
display(family_frame_29[["signal", "q", "mean_pool", "mean_nan", "mean_excluded",
                         "realised_excluded_share", "cagr", "cycle_sharpe", "cycle_vol",
                         "ulcer", "max_dd", "mean_invested"]].round(4))
'''))

cells.append(md("""## Part 2. Matched realised exclusion share, and inertness

Two things the metrics alone cannot say. First, whether two signals are even being compared at
the same filtering strength - `q = 0.30` of the finite-signal candidates is a different share of
the pool for a signal that scores 40 vaults than for one that scores 140. Second, whether a run
changed anything at all: an inert run's metrics ARE the anchor's, and reading them as a result is
how a no-op gets mistaken for a mechanism.
"""))
cells.append(code('''reference_share = float(
    family_frame_29.loc[label_for("inverse_vol", CENTRE), "realised_excluded_share"]
)
print(f"reference realised exclusion share, inverse_vol at q = {CENTRE}: {reference_share:.4f}")
matched = []
for signal in CARRIED:
    subset = family_frame_29[family_frame_29["signal"] == signal]
    closest = (subset["realised_excluded_share"] - reference_share).abs().idxmin()
    matched.append(subset.loc[closest])
matched_frame = pd.DataFrame(matched)
display(matched_frame[["signal", "q", "realised_excluded_share", "cagr", "cycle_sharpe",
                       "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested"]].round(4))

inert_rows = [inertness(run_by_label[label]) for label in family_frame_29.index]
inert_frame = pd.DataFrame(inert_rows).set_index("label")
display(inert_frame[["decisions_logged", "decisions_with_exclusions",
                     "dates_with_a_different_basket", "share_of_decisions_changed",
                     "excluded_names_the_reference_held", "basket_jaccard_vs_reference",
                     "distinct_vaults", "inert"]].round(4))
if bool(inert_frame["inert"].any()):
    print("\\nINERT runs (identical equity path to the anchor):",
          list(inert_frame[inert_frame["inert"]].index))
else:
    print("\\nno run is inert: every configuration changed the realised equity path")
'''))

cells.append(md("""## Part 3. The strict variant, at the centre only

Strict excludes candidates whose signal is not finite as well as the least-stable measured
fraction. That is a data-availability filter bolted onto a stability filter, and NB21 and NB26
already showed what happens when the two are conflated: 70.9% of the vol-matched drop's removals
at N = 30 have no volatility estimate, and that half is exactly inert.

DIAGNOSTIC only. A strict run cannot inherit its permissive sibling's gate-5 pass.
"""))
cells.append(code('''for signal in CARRIED:
    run_and_record(label_for(signal, CENTRE, "_strict"), "diagnostic",
                   **prefilter_overrides(signal, fraction=CENTRE, strict=True))

strict_rows = []
for signal in CARRIED:
    for label in (label_for(signal, CENTRE), label_for(signal, CENTRE, "_strict")):
        entry = run_by_label[label]
        shares = prefilter_exclusion_frame(entry)
        row = entry["panel"].copy()
        row["signal"] = signal
        row["strict"] = label.endswith("_strict")
        row["realised_excluded_share"] = float(shares["excluded_share"].mean())
        strict_rows.append(row)
display(pd.DataFrame(strict_rows).set_index("label")[
    ["signal", "strict", "realised_excluded_share", "cagr", "cycle_sharpe", "cycle_vol",
     "ulcer", "abs_invested_beta", "mean_invested"]].round(4))
'''))

cells.append(md("""## Part 4. The cheap gates at the centre

Gates 1, 3, 4, 6, 7 and 8 need no re-simulation. Scoring them first means the expensive gates -
leave-one-vault-out and the ten-seed null - never run for a candidate that has already failed,
which is the plan's ordering rule and not an optimisation added afterwards.
"""))
cells.append(code('''anchor_entry = run_by_label["anchor"]
anchor_character = held_book_character_cached(anchor_entry)
anchor_measures = diversification_cached(anchor_entry)
print("anchor held-book character:", {k: round(v, 6) if isinstance(v, float) else v
                                      for k, v in anchor_character.items()})
print("anchor diversification:    ", {k: round(v, 6) if isinstance(v, float) else v
                                      for k, v in anchor_measures.items()})
print(f"anchor luck_ratio {float(anchor_panel['luck_ratio']):.4f}, "
      f"top5_gross_share {float(anchor_panel['top5_gross_share']):.4f}")

cheap_rows = []
for signal in CARRIED:
    label = label_for(signal, CENTRE)
    entry = run_by_label[label]
    row = entry["panel"]
    character = held_book_character_cached(entry)
    measures = diversification_cached(entry)
    plateau = plateau_gate(label, [label_for(signal, n) for n in NEIGHBOURS])
    segments = [float(row.get(f"{r}_cagr", np.nan)) for r in ("sparse", "dense", "late")]
    failures = []
    for name, larger_is_worse in DIVERSIFICATION_MEASURES.items():
        value, reference = measures[name], anchor_measures[name]
        if not (np.isfinite(value) and np.isfinite(reference)):
            failures.append(f"{name} not finite")
        elif (larger_is_worse and value > reference) or (not larger_is_worse and value < reference):
            failures.append(name)
    cheap_rows.append({
        "label": label, "signal": signal,
        "gate_1_positive": bool(np.isfinite(row["cagr"]) and float(row["cagr"]) > 0),
        "gate_3_held_book": bool(
            np.isfinite(character["held_vol"]) and np.isfinite(character["held_concentration"])
            and character["held_vol"] < anchor_character["held_vol"]
            and character["held_concentration"] < anchor_character["held_concentration"]),
        "held_vol": character["held_vol"], "held_concentration": character["held_concentration"],
        "held_dates_used": character["dates_used"], "held_dates_excluded": character["dates_excluded"],
        "gate_4_luck": bool(
            np.isfinite(row["luck_ratio"]) and np.isfinite(row["top5_gross_share"])
            and float(row["luck_ratio"]) >= float(anchor_panel["luck_ratio"])
            and float(row["top5_gross_share"]) <= float(anchor_panel["top5_gross_share"])),
        "gate_5_screen": bool(GATE_5.get(signal, False)),
        "gate_6_plateau": plateau["passes"],
        "gate_7_subperiod": bool(all(np.isfinite(s) and s > 0 for s in segments)),
        "gate_8_diversification": not failures,
        "diversification_failures": ", ".join(failures),
    })
cheap = pd.DataFrame(cheap_rows).set_index("label")
CHEAP_GATES = ["gate_1_positive", "gate_3_held_book", "gate_4_luck", "gate_5_screen",
               "gate_6_plateau", "gate_7_subperiod", "gate_8_diversification"]
cheap["all_cheap_gates"] = cheap[CHEAP_GATES].all(axis=1)
pd.set_option("display.max_colwidth", None)
display(cheap[["signal"] + CHEAP_GATES + ["all_cheap_gates", "diversification_failures"]])
display(cheap[["held_vol", "held_concentration", "held_dates_used", "held_dates_excluded"]].round(6))
for signal in CARRIED:
    display(plateau_gate(label_for(signal, CENTRE),
                         [label_for(signal, n) for n in NEIGHBOURS])["detail"].assign(signal=signal))
'''))

cells.append(md("""## Part 5. The expensive gates, for whatever survived

Leave-one-vault-out on the centre AND both neighbours, then the ten-seed null at the centre.
Gate 2 is scored on the centre's retention; the neighbours' are reported because a plateau whose
members all collapse under a single mask is a plateau in a statistic, not in the mechanism.
"""))
cells.append(code('''SURVIVORS = [s for s in CARRIED if bool(cheap.loc[label_for(s, CENTRE), "all_cheap_gates"])]
print(f"signals reaching the expensive gates: {SURVIVORS or 'none'}")

lovo_rows = []
for signal in SURVIVORS:
    for fraction in (CENTRE,) + NEIGHBOURS:
        lovo_rows.append(lovo_gate(label_for(signal, fraction)))
if lovo_rows:
    display(pd.DataFrame(lovo_rows).set_index("label").round(6))
else:
    print("no leave-one-vault-out run executed; gate 2 is False for every candidate")
'''))

cells.append(code('''NULL_SEEDS = tuple(range(10))
for signal in SURVIVORS:
    for seed in NULL_SEEDS:
        run_and_record(f"{label_for(signal, CENTRE)}_null{seed}", "null",
                       **prefilter_overrides(signal, fraction=CENTRE, seed=seed))

null_rows = []
for signal in SURVIVORS:
    labels = [f"{label_for(signal, CENTRE)}_null{seed}" for seed in NULL_SEEDS]
    result = null_effectiveness(label_for(signal, CENTRE), labels)
    result["signal"] = signal
    null_rows.append(result)
if null_rows:
    display(pd.DataFrame(null_rows).set_index("centre").round(6))
    null_detail = pd.DataFrame([
        {"label": label, **{k: float(run_by_label[label]["panel"][k])
                            for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer")}}
        for signal in SURVIVORS for label in
        [f"{label_for(signal, CENTRE)}_null{seed}" for seed in NULL_SEEDS]
    ]).set_index("label")
    display(null_detail.round(6))
else:
    print("no null executed; gate 9 is False for every candidate")
'''))

cells.append(md("""## Part 6. The verdict table

Every gate Boolean listed separately, every failure named in full, and an unexecuted gate False
rather than absent. SHORTLIST is the strongest verdict available.
"""))
cells.append(code('''verdict_rows = []
for signal in CARRIED:
    label = label_for(signal, CENTRE)
    nulls = ([f"{label}_null{seed}" for seed in NULL_SEEDS] if signal in SURVIVORS else [])
    verdict_rows.append(gate_row(
        label, gate_5_by_signal=GATE_5, signal=signal,
        neighbours=[label_for(signal, n) for n in NEIGHBOURS], null_labels=nulls,
    ))
verdicts = verdict_table_rules(verdict_rows)
gate_columns = ["gate_1_positive", "gate_2_lovo", "gate_3_held_book", "gate_4_luck",
                "gate_5_screen", "gate_6_plateau", "gate_7_subperiod",
                "gate_8_diversification", "gate_9_null"]
display(verdicts[["signal", "cycle_sharpe", "cagr", "cycle_vol", "ulcer"] + gate_columns
                 + ["verdict"]])
print("\\ncomplete failure strings:")
for label, row in verdicts.iterrows():
    print(f"  {label}: {row['failed_gates'] or '(none)'}")
SHORTLISTED = [label for label, row in verdicts.iterrows() if row["verdict"] == "SHORTLIST"]
print(f"\\nSHORTLIST: {SHORTLISTED or 'nothing'}")
'''))

cells.append(code('''display(verdicts[["signal", "sparse_cagr", "dense_cagr", "late_cagr", "luck_ratio",
                  "top5_gross_share", "lovo_retention", "lovo_masked", "mean_holdings",
                  "mean_largest_weight", "mean_herfindahl", "distinct_vaults",
                  "top_vault_pnl_share"]].round(4))

# The anchor's own values on the same measures, for continuity with NB03-NB26.
reference_row = {
    "cycle_sharpe": float(anchor_panel["cycle_sharpe"]), "cagr": float(anchor_panel["cagr"]),
    "cycle_vol": float(anchor_panel["cycle_vol"]), "ulcer": float(anchor_panel["ulcer"]),
    "luck_ratio": float(anchor_panel["luck_ratio"]),
    "top5_gross_share": float(anchor_panel["top5_gross_share"]),
    **anchor_measures, **{f"held_{k}": v for k, v in anchor_character.items()},
}
display(pd.Series(reference_row).to_frame("anchor").round(6))
'''))

cells.append(md("""## Part 7. Paired uncertainty against the anchor, for context

Not a gate. `RESEARCH-RULES.md` is explicit that this window cannot resolve the Sharpe
differences involved, and pretending otherwise was the mistake the retired constraint 7 made.
Reported so the size of the uncertainty is visible beside the point estimates.
"""))
cells.append(code('''rows = []
for signal in CARRIED:
    label = label_for(signal, CENTRE)
    for block in (5, 10, 20):
        result = bootstrap_paired_sharpe_diff(
            run_by_label[label]["cycle_returns"], anchor_cycle_returns, block=block,
        )
        rows.append({"run": label, "block": block, "observed_diff": result["observed"],
                     "ci_lo": result["lo"], "ci_hi": result["hi"],
                     "excludes_zero": bool(np.isfinite(result["lo"]) and result["lo"] > 0)})
display(pd.DataFrame(rows).round(4))
'''))

cells.append(code('''summary = {
    "verdict": "SHORTLIST" if SHORTLISTED else "REJECT - nothing shortlisted",
    "shortlisted": SHORTLISTED,
    "carried": CARRIED,
    "survivors_of_cheap_gates": SURVIVORS,
    "centre": CENTRE, "fractions": list(FRACTIONS), "neighbours": list(NEIGHBOURS),
    "reference_realised_share": reference_share,
    "family": family_frame_29[["signal", "q", "realised_excluded_share", "cagr", "cycle_sharpe",
                               "cycle_vol", "ulcer", "max_dd", "abs_invested_beta",
                               "mean_invested", "sparse_cagr", "dense_cagr", "late_cagr"]]
        .round(6).to_dict(orient="index"),
    "inertness": inert_frame.round(6).to_dict(orient="index"),
    "gates": verdicts[["signal"] + gate_columns + ["failed_gates", "verdict"]].to_dict(orient="index"),
    "nulls": [{k: v for k, v in row.items()} for row in null_rows],
    "lovo": [{k: v for k, v in row.items()} for row in lovo_rows],
    # Every executed configuration, with the overrides needed to reproduce it. NB31 re-runs from
    # this rather than from a hand-copied list, so a configuration cannot be silently left out of
    # the close-out it should have been re-checked in.
    "all_runs": {
        entry["label"]: {
            "family": entry["family"],
            "overrides": {
                k: (sorted(v) if isinstance(v, (set, frozenset)) else v)
                for k, v in entry["overrides"].items()
            },
            "panel": {k: float(entry["panel"][k]) for k in
                      ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd",
                       "abs_invested_beta", "mean_invested")},
        }
        for entry in runs if entry["label"] != "anchor"
    },
}
Path("_build/manifest_29.json").write_text(json.dumps(summary, indent=1, default=str))
print("wrote _build/manifest_29.json")
display(pd.Series({k: v for k, v in summary.items()
                   if k in ("verdict", "shortlisted", "carried", "survivors_of_cheap_gates")}).to_frame("value"))
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "29-backtest-stability-prefilter.ipynb")
