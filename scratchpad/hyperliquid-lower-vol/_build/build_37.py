import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_floor import INDICATOR_ADDITIONS_FLOOR
from blocks_rules_fixes import INDICATOR_ADDITIONS_RULES_FIXES
from blocks_threshold import PARAM_ADDITIONS_THRESHOLD, INDICATOR_ADDITIONS_THRESHOLD, CELL14_REPLACEMENTS_THRESHOLD

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()
HARNESS_RULES_V2 = (BUILD_DIR / "harness_rules_v2.py").read_text()
HARNESS_RULES_V3 = (BUILD_DIR / "harness_rules_v3.py").read_text()
HARNESS_RULES_V3_GATES = (BUILD_DIR / "harness_rules_v3_gates.py").read_text()
HARNESS_THRESHOLD = (BUILD_DIR / "harness_threshold.py").read_text()

HEADING = """# NB37 - threshold crash filter: max positions, concentration cap, rankers and weighters

Plan 34's `measured_8` removed a fixed COUNT of the most volatile measurable candidates. This
notebook replaces the count with a THRESHOLD on the vault itself: a candidate is not admitted
while its trailing 90-row realised volatility is above 80% annualised, and a held vault is
removed when it rises above 100%. The number comes from a vault-level calibration on the
post-break archive (66 decisions x ~210 candidates): the forward 30-day crash rate is flat
below 50% annualised, 4-6% between 50% and 100%, and triples at 100% (15% in 1.0-1.5, 22% in
1.5-2.0), with the mean 30-day log return falling from about -4% to -17% across the same knee.

Around that filter the notebook varies what the operator asked to see: the concentration cap
removed (`max_concentration_pct` 0.33 -> 1.0); `max_assets_in_portfolio` 1, 2, 3, 4 and 6, and
unlimited (every survivor of the filter held); and the rankers and weighters the track has
already researched, at six names.

**Verdicts use the standing gates only** (RESEARCH-RULES.md, idiot-gate audit of 2026-09-16):
1 positive return, 2 single-vault mask, 3 held-book volatility, 6 plateau, 7 sub-period sign.
Gates 4 and 8 are reported with their tolerances as diagnostics. Nothing here is out of sample.

**Based on:** [35-backtest-calm-tail-exclusion.ipynb](35-backtest-calm-tail-exclusion.ipynb)
for the gate machinery, [32-backtest-return-floor-stability-rank.ipynb](32-backtest-return-floor-stability-rank.ipynb)
for the rankers, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Track window
2026-01-01 to 2026-09-08; windows A (incumbent's period) and B (full data) as in NB33.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "37-backtest-threshold-crash-filter",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_THRESHOLD},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR + INDICATOR_ADDITIONS_RULES_FIXES
    + INDICATOR_ADDITIONS_THRESHOLD,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_THRESHOLD)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))
cells.append(code(HARNESS_RULES_V2))
cells.append(code(HARNESS_RULES_V3))
cells.append(code(HARNESS_RULES_V3_GATES))
cells.append(code(HARNESS_THRESHOLD))

cells.append(md("""## Part 0. Provenance, parity, the filter's constants

The crash filter is off by default (`crash_vol_threshold_exit = 0.0`), so the anchor must still
reproduce `BASELINE` with the splice present: that is the parity assertion.
"""))
cells.append(code('''import json
from pathlib import Path
display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
THR = {"exit": 1.0, "enter": 0.8}
THR_FAMILY = {"thr075": {"exit": 0.75, "enter": 0.6}, "thr100": THR, "thr150": {"exit": 1.5, "enter": 1.2},
              "thr200": {"exit": 2.0, "enter": 1.6}, "thr250": {"exit": 2.5, "enter": 2.0}}
NOCAP = {"max_concentration_pct": 1.0}


def filter_overrides(thr=THR, **extra) -> dict:
    return {"crash_vol_threshold_exit": float(thr["exit"]), "crash_vol_threshold_enter": float(thr["enter"]), **extra}


display(pd.Series({"exit threshold (annualised realised vol)": THR["exit"], "enter threshold": THR["enter"],
                   "family": "0.75, 1.0, 1.5, 2.0, 2.5 (enter = 0.8 x exit)", "volatility estimate": "1 / inverse_vol x sqrt(365), 90 rows",
                   "missing estimate": "kept (permissive)", "indifference band": INDIFFERENCE_BAND}, name="value").to_frame())
'''))

cells.append(md("""## Part 1. The filter on the incumbent

The threshold family 0.75 / 1.0 / 1.5 / 2.0 / 2.5 with the 33% cap kept (the pure filter
effect), the cap removed alone, and the pre-stated 1.0 filter plus cap removed. The crash log
says how many names the filter removed per decision and how often it removed one the book held.
The centre for Parts 2 and 3 is chosen HERE as the family member with the highest cycle Sharpe
- an exploratory choice, made on this window and stated as such; the calibration knee at 1.0
is the pre-stated value and is carried through Parts 2 and 5 regardless.
"""))
cells.append(code('''for label, thr in THR_FAMILY.items():
    run_and_record(label, "filter", **filter_overrides(thr))
run_and_record("nocap", "cap", **NOCAP)
run_and_record("thr100_nocap", "filter", **filter_overrides(**NOCAP))

SUMMARY_COLUMNS = ["family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested", "luck_ratio",
                   "top5_gross_share", "sparse_cagr", "dense_cagr", "late_cagr", "abs_invested_beta", "final_equity",
                   "mean_holdings", "mean_largest_weight", "distinct_vaults", "top_vault_pnl_share",
                   "turnover_per_decision", "trades", "decisions_changed", "share_of_decisions_changed",
                   "crash_excluded_mean", "crash_excluded_min", "crash_excluded_max", "crash_excluded_held_total", "crash_measured_share"]


def summary_table(labels):
    return pd.DataFrame([summary_row(l) for l in labels]).set_index("label")[SUMMARY_COLUMNS]


PART1 = ["anchor"] + list(THR_FAMILY) + ["nocap", "thr100_nocap"]
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
part1 = summary_table(PART1)
display(part1.round(4))
CENTRE = part1.loc[list(THR_FAMILY), "cycle_sharpe"].idxmax()
CENTRE_THR = THR_FAMILY[CENTRE]
print(f"exploratory centre for Parts 2-3: {CENTRE} (exit {CENTRE_THR['exit']}, enter {CENTRE_THR['enter']}), "
      f"cycle Sharpe {part1.loc[CENTRE, 'cycle_sharpe']:.4f}; pre-stated 1.0 has {part1.loc['thr100', 'cycle_sharpe']:.4f}")
'''))

cells.append(md("""## Part 2. Max positions 1 to 4, six, and unlimited

With the cap removed (a one-name book cannot exist under a 33% cap). Each N without the filter,
with the pre-stated 1.0 filter, and with the exploratory centre from Part 1, so the effects can
be told apart. "Unlimited" holds every survivor of the
filter, sized by inverse variance or equally - the ranker is irrelevant there. The TVL size
limit (`per_position_cap_of_pool_pct` 0.33) stays on, because it is liquidity, not policy; its
bite shows up as `mean_invested`.
"""))
cells.append(code('''N_VALUES = (1, 2, 3, 4)
C = CENTRE   # e.g. "thr150"
for n in N_VALUES:
    run_and_record(f"thr100_n{n}", "positions", **filter_overrides(max_assets_in_portfolio=n, **NOCAP))
    run_and_record(f"nofilter_n{n}", "positions", max_assets_in_portfolio=n, **NOCAP)
    if C != "thr100":
        run_and_record(f"{C}_n{n}", "positions", **filter_overrides(CENTRE_THR, max_assets_in_portfolio=n, **NOCAP))
if C != "thr100":
    run_and_record(f"{C}_nocap", "filter", **filter_overrides(CENTRE_THR, **NOCAP))
run_and_record("thr100_nall_invvar", "unlimited", **filter_overrides(max_assets_in_portfolio=999, **NOCAP))
run_and_record("thr100_nall_equal", "unlimited", **filter_overrides(max_assets_in_portfolio=999, weighting_method="equal", **NOCAP))
if C != "thr100":
    run_and_record(f"{C}_nall_invvar", "unlimited", **filter_overrides(CENTRE_THR, max_assets_in_portfolio=999, **NOCAP))
    run_and_record(f"{C}_nall_equal", "unlimited", **filter_overrides(CENTRE_THR, max_assets_in_portfolio=999, weighting_method="equal", **NOCAP))

PART2 = ["anchor", "nocap", "thr100_nocap"] + ([f"{C}_nocap"] if C != "thr100" else []) \\
        + [f"nofilter_n{n}" for n in N_VALUES] + [f"thr100_n{n}" for n in N_VALUES] \\
        + ([f"{C}_n{n}" for n in N_VALUES] if C != "thr100" else []) \\
        + ["thr100_nall_invvar", "thr100_nall_equal"] + ([f"{C}_nall_invvar", f"{C}_nall_equal"] if C != "thr100" else [])
display(summary_table(PART2).round(4))
'''))

cells.append(md("""## Part 3. Rankers and weighters at six names, centre threshold, cap kept

Rankers the track has researched: the incumbent `cagr_sortino_weight`, the original
`cagr_sharpe_weight`, `cagr_downside_weight`, and `calm_score` as the one pure stability ranker
(NB32 found stability rankers destroy return; the filter may change that, or not). Weighters:
`inverse_variance` (incumbent), `equal`, `inverse_vol`.
"""))
cells.append(code('''RANKERS = ["cagr_sortino_weight", "cagr_sharpe_weight", "cagr_downside_weight", "calm_score"]
WEIGHTERS = ["inverse_variance", "equal", "inverse_vol"]
# At the exploratory centre threshold, with the 33% cap KEPT: Part 1 shows what removing the cap
# does to inverse-variance sizing, and the ranker/weighter question is cleaner with it on.
PART3 = ["anchor", C]
for ranker in RANKERS:
    for weighter in WEIGHTERS:
        if ranker == "cagr_sortino_weight" and weighter == "inverse_variance":
            continue   # that is the centre itself
        label = f"{C}_{ranker.replace('_weight', '').replace('_score', '')}__{weighter}"
        run_and_record(label, "ranker_weighter", **filter_overrides(CENTRE_THR, selection_score_indicator=ranker, weighting_method=weighter))
        PART3.append(label)
display(summary_table(PART3).round(4))
'''))

cells.append(md("""## Part 4. Standing gates

Gates 1, 7, 3 and 6 for every run; gate 2 (a full re-simulation) for the two filter
configurations on the incumbent and for the three best remaining runs by cycle Sharpe that
pass the cheap standing gates. Plateau neighbours: the threshold family on 0.75 / 1.5, the
position family on N +/- 1, the ranker-weighter family has no ordered axis and gate 6 is not
scored for it. Gates 4 and 8 with their tolerances are diagnostics.
"""))
cells.append(code('''FAMILY_ORDER = list(THR_FAMILY)
NEIGHBOURS = {}
for i, label in enumerate(FAMILY_ORDER):
    NEIGHBOURS[label] = [FAMILY_ORDER[j] for j in (i - 1, i + 1) if 0 <= j < len(FAMILY_ORDER)]
NEIGHBOURS["thr100_nocap"] = ["thr075", "thr150"]
for stem, six in (("thr100", "thr100_nocap"), ("nofilter", "nocap")) + (((C, f"{C}_nocap"),) if C != "thr100" else ()):
    NEIGHBOURS[f"{stem}_n1"] = [f"{stem}_n2"]
    NEIGHBOURS[f"{stem}_n2"] = [f"{stem}_n1", f"{stem}_n3"]
    NEIGHBOURS[f"{stem}_n3"] = [f"{stem}_n2", f"{stem}_n4"]
    NEIGHBOURS[f"{stem}_n4"] = [f"{stem}_n3", six]
if C != "thr100":
    NEIGHBOURS[f"{C}_nocap"] = NEIGHBOURS[C]
ALL = [e["label"] for e in runs if e["label"] != "anchor"]
cheap = pd.DataFrame([standing_gates(l, NEIGHBOURS.get(l, [])) for l in ALL]).set_index("label")
CHEAP = ["gate_1_positive", "gate_7_subperiod", "gate_3_held_vol"]
cheap["cheap_pass"] = cheap[CHEAP].all(axis=1)
ranked = cheap[cheap["cheap_pass"]].sort_values("sharpe_gap_to_anchor", ascending=False)
LOVO_LABELS = list(dict.fromkeys(["thr100", C, f"{C}_nall_invvar" if C != "thr100" else "thr100_nall_invvar"]
                                 + [l for l in ranked.index if l not in ("thr100", C)][:3]))
print(f"leave-one-vault-out for: {LOVO_LABELS}")
gates = pd.DataFrame([standing_gates(l, NEIGHBOURS.get(l, []), run_lovo=(l in LOVO_LABELS)) for l in ALL]).set_index("label")
pd.set_option("display.max_colwidth", None)
display(gates[["gate_1_positive", "gate_7_subperiod", "gate_3_held_vol", "gate_6_plateau", "gate_2_mask", "mask_retention",
               "diag_4_luck_within_tolerance", "diag_8_distinct_within_tolerance", "sharpe_gap_to_anchor",
               "failed_standing_gates", "verdict"]].round(4))
for label in LOVO_LABELS:
    print(f"  {label}: masked {gates.loc[label, 'masked']}, retention {gates.loc[label, 'mask_retention']:.3f}")
'''))

cells.append(md("""## Part 5. Windows A and B

The incumbent's docstring window (2026-01-01 to 07-10) and the full data period (2025-08-01 to
09-09) for the anchor, the filter with and without the cap, and the best run of Parts 2-3 by
track Sharpe among those passing the cheap standing gates. Slim runs; the cost-basis helper is
redefined with a relative tolerance exactly as NB33 and NB35 did.
"""))
cells.append(code('''import datetime


def get_remaining_cost_basis(position) -> float:
    quantity = 0.0
    cost_basis = 0.0
    for trade in sorted(position.get_successful_trades(), key=lambda trade: trade.executed_at):
        trade_quantity = abs(float(trade.get_position_quantity()))
        if trade.is_buy():
            quantity += trade_quantity
            cost_basis += trade_quantity * float(trade.executed_price)
        elif trade.is_sell():
            assert quantity > 0, f"Cannot sell without a cost basis: {trade}"
            sold_quantity = min(trade_quantity, quantity)
            cost_basis *= (quantity - sold_quantity) / quantity
            quantity -= sold_quantity
    held = float(position.get_quantity())
    assert abs(quantity - held) <= 1e-8 * max(1.0, abs(held)), (
        f"Cost-basis quantity mismatch for {position}: {quantity} vs {position.get_quantity()}")
    return cost_basis


WINDOW_A = ("A: incumbent period", datetime.datetime(2026, 1, 1), datetime.datetime(2026, 7, 10))
WINDOW_B = ("B: full data period", datetime.datetime(2025, 8, 1), datetime.datetime(2026, 9, 9))
best_other = next((l for l in ranked.index if l not in set(THR_FAMILY) | {"thr100_nocap", "nocap", f"{C}_nocap"}), None)
WINDOW_LABELS = list(dict.fromkeys(["anchor", "thr100", C, f"{C}_nall_invvar" if C != "thr100" else "thr100_nall_invvar"]
                                   + ([best_other] if best_other else [])))
print(f"window runs for: {WINDOW_LABELS}")
WINDOW_RESULTS = {}


def run_window(label: str, window) -> dict:
    name, start, end = window
    overrides = dict(run_by_label[label]["overrides"]) if label != "anchor" else {}
    VOL_DROP_LOG.clear(); COMPLEMENT_LOG.clear(); SLEEVE_LOG.clear(); PREFILTER_LOG.clear(); CRASH_LOG.clear()
    state_, equity_, returns_ = run_variant(f"{label} [{name}]", backtest_start=start, backtest_end=end, **overrides)
    rc, _ppy = cycle_returns(equity_)
    row = panel(f"{label} [{name}]", state_, equity_, returns_)
    row["cumulative_return"] = float(equity_.iloc[-1] / equity_.iloc[0] - 1.0)
    row["final_equity"] = float(equity_.iloc[-1])
    row["cycles"] = int(len(rc))
    row["crash_excluded_mean"] = float(np.mean([r["excluded_count"] for r in CRASH_LOG.values()])) if CRASH_LOG else float("nan")
    WINDOW_RESULTS[(label, name)] = {"label": label, "window": name, "equity": equity_, "cycle_returns": rc, "panel": row}
    return WINDOW_RESULTS[(label, name)]


for window in (WINDOW_A, WINDOW_B):
    for label in WINDOW_LABELS:
        run_window(label, window)
WINDOW_COLUMNS = ["cumulative_return", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested",
                  "luck_ratio", "top5_gross_share", "cycles", "crash_excluded_mean"]
window_tables = {}
for window in (WINDOW_A, WINDOW_B):
    name = window[0]
    frame = pd.DataFrame([WINDOW_RESULTS[(l, name)]["panel"] for l in WINDOW_LABELS]).set_index("label")[WINDOW_COLUMNS]
    frame.index = WINDOW_LABELS
    window_tables[name] = frame
    print(f"\\n{name}:")
    display(frame.round(4))
'''))

cells.append(md("""## Part 6. Equity curves

Track window: the anchor, the filter with and without the cap, the best run from Parts 2-3, and
the unlimited book. Normalised to 1.0 at the start.
"""))
cells.append(code('''import plotly.graph_objects as go
PLOT = list(dict.fromkeys(["anchor", "thr100", C, f"{C}_nall_invvar" if C != "thr100" else "thr100_nall_invvar"]
                          + ([best_other] if best_other else [])))
fig = go.Figure()
for label in PLOT:
    eq = run_by_label[label]["equity"]
    fig.add_trace(go.Scatter(x=eq.index, y=eq / eq.iloc[0], mode="lines", name=label))
fig.update_layout(title="Track window equity, normalised", height=480, template="plotly_white", yaxis_title="equity / initial")
fig.show()

# Largest single-cycle contributions, so a lucky jump is visible rather than inferred.
rows = []
for label in PLOT:
    rc = run_by_label[label]["cycle_returns"].sort_values(ascending=False)
    rows.append({"label": label, "best_cycle": float(rc.iloc[0]), "best_cycle_date": str(rc.index[0].date()),
                 "top5_cycles_sum": float(rc.iloc[:5].sum()), "total_log_return": float(np.log1p(run_by_label[label]["cycle_returns"]).sum()),
                 "worst_cycle": float(rc.iloc[-1]), "worst_cycle_date": str(rc.index[-1].date()),
                 "kurtosis": float(run_by_label[label]["cycle_returns"].kurt())})
display(pd.DataFrame(rows).set_index("label").round(4))
'''))

cells.append(md("""## Part 7. Manifest
"""))
cells.append(code('''all_summary = summary_table(["anchor"] + ALL)
manifest = {
    "verdict": "see heading",
    "threshold": THR, "threshold_family": THR_FAMILY, "centre": C, "centre_threshold": CENTRE_THR,
    "provenance": provenance_record(),
    "summary": all_summary.round(10).to_dict(orient="index"),
    "gates": gates.round(10).to_dict(orient="index"),
    "lovo_labels": LOVO_LABELS,
    "best_other": best_other,
    "windows": {name: frame.round(10).to_dict(orient="index") for name, frame in window_tables.items()},
    "cycle_concentration": pd.DataFrame(rows).set_index("label").round(10).to_dict(orient="index"),
    "all_runs": {e["label"]: {"family": e["family"],
                              "overrides": {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in e["overrides"].items()},
                              "panel": {k: float(e["panel"][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd")}}
                 for e in runs if e["label"] != "anchor"},
}
Path("_build/manifest_37.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_37.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "37-backtest-threshold-crash-filter.ipynb")
