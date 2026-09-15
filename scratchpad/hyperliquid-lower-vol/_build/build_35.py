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

HEADING = """# NB35 - the volatility tail exclusion through the nine gates

The one mechanism plan 34 carries: before the incumbent ranks its candidates, remove the eight
most volatile of those whose volatility can be measured, and change nothing else. Centre
`calm_8` (`calm_score`, the fresh-guarded `inverse_vol`), neighbours at 6 and 10; the same
three on raw `inverse_vol` (`measured_8`, the configuration with the three-window record) as
the calendar reference, gated identically with its own null and leave-one-vault-out runs; and
`calm_8_strict` as the inertness diagnostic.

Verdicts are SHORTLIST / REJECT / DIAGNOSTIC under [RESEARCH-RULES.md](RESEARCH-RULES.md) with
amendments A1-A6 of [34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md)
Draft 2. Gate 5 is imported from NB34's manifest after the snapshot is asserted equal. Every
gate Boolean is listed; every failure string is printed in full; an unexecuted gate is False.

**Based on:** [29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb)
for the gate machinery, [33-research-lead-comparison.ipynb](33-research-lead-comparison.ipynb)
for the two extra windows, [02-better-format.ipynb](02-better-format.ipynb) as the anchor.

## Method

Gates in the plan's order: 1, 7, 4, 5, 3 (volatility leg on common post-break dates, A4), 8
(holdings floor 5.95, A3), 6, then 2 and 9 only for a centre that passed every cheaper gate,
then the fee differential (A6) for every run. Gate 9 is nineteen within-date permutations of
the finite signal values (A5), asserted distinct on the realised cycle-return series, with the
null runs' turnover and basket persistence reported beside the centre's. H3 - the incumbent's
window and the full data period - is a consistency check on overlapping windows, not a gate.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "35-backtest-calm-tail-exclusion",
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

cells.append(md("""## Part 0. Provenance, parity, and gate 5 from NB34

NB34's manifest is used only after its data snapshot is asserted equal to this kernel's. Gate 5
per signal is taken from its post-break screen; the two count-8 runs it recorded are reproduced
here and compared at 1e-9, which is the same-engine check.
"""))
cells.append(code('''import json
from pathlib import Path
display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
manifest_34 = json.loads(Path("_build/manifest_34.json").read_text())
assert_same_snapshot(manifest_34["provenance"], "manifest_34")
GATE_5 = {s: bool(v) for s, v in manifest_34["gate_5"].items()}
print("gate 5 (NB34, post-break, amendments A1-A2):", GATE_5)
print("stability clause:", manifest_34["stability_clause"], " return clause:", manifest_34["return_clause"])
constants = pd.Series({
    "exclusion_count_centre": EXCLUSION_COUNT, "neighbours": "6, 10", "holdings_floor": HOLDINGS_FLOOR,
    "gate_3_scope": f"volatility leg, common dates >= {POST_BREAK_START.date()}, min {GATE_3_MIN_DATES}",
    "null_seeds": NULL_MIN_DISTINCT_V3, "lovo_retention_bar": LOVO_RETENTION_BAR, "plateau_tolerance": PLATEAU_TOLERANCE,
    "fee_differential_max_share": FEE_DIFFERENTIAL_MAX, "indifference_band": INDIFFERENCE_BAND,
}, name="value")
display(constants.to_frame())
'''))

cells.append(md("""## Part 1. Seven runs on the track window

Centre and neighbours on both signals, plus the strict variant. Inertness is reported for every
run against the anchor, and the strict variant against `calm_8`: the plan's H4 says excluding
the unmeasured candidates as well changes nothing.
"""))
cells.append(code('''COUNTS = (6, 8, 10)
CENTRE = 8
NEIGHBOURS = (6, 10)


def label_for(signal: str, count: int, strict: bool = False) -> str:
    stem = "calm" if signal == "calm_score" else "measured"
    return f"{stem}_{count}" + ("_strict" if strict else "")


for signal in SIGNAL_NAMES:
    for count in COUNTS:
        run_and_record(label_for(signal, count), "calm" if signal == "calm_score" else "measured",
                       **prefilter_overrides(signal, count=count))
run_and_record(label_for("calm_score", CENTRE, strict=True), "diagnostic",
               **prefilter_overrides("calm_score", count=CENTRE, strict=True))

LABELS = [label_for(s, c) for s in SIGNAL_NAMES for c in COUNTS] + [label_for("calm_score", CENTRE, strict=True)]
METRICS = ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta", "mean_invested",
           "sparse_cagr", "dense_cagr", "late_cagr", "luck_ratio", "top5_gross_share"]
track = pd.DataFrame([run_by_label[l]["panel"] for l in ["anchor"] + LABELS]).set_index("label")[METRICS]
display(track.round(4))

# Same engine, same snapshot: NB34's two count-8 runs must reproduce here at 1e-9.
for label in ("calm_8", "measured_8"):
    for metric in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd"):
        here, there = float(run_by_label[label]["panel"][metric]), float(manifest_34["runs"][label][metric])
        assert abs(here - there) < 1e-9, f"{label} {metric}: {here} here vs {there} in NB34"
print("calm_8 and measured_8 reproduce NB34's runs at 1e-9 on five metrics")

inert = pd.DataFrame([inertness(run_by_label[l]) for l in LABELS]).set_index("label")
display(inert[["decisions_with_exclusions", "dates_with_a_different_basket", "share_of_decisions_changed",
               "excluded_names_the_reference_held", "basket_jaccard_vs_reference", "distinct_vaults",
               "equity_path_identical_to_reference", "inert"]].round(4))
strict_vs_centre = inertness(run_by_label["calm_8_strict"], reference="calm_8")
print("calm_8_strict against calm_8:", {k: strict_vs_centre[k] for k in
      ("dates_with_a_different_basket", "equity_path_identical_to_reference", "inert")})
aligned = pd.concat([run_by_label["calm_8_strict"]["cycle_returns"].rename("strict"),
                     run_by_label["calm_8"]["cycle_returns"].rename("centre")], axis=1).dropna()
print(f"max |cycle return difference| strict vs centre: {float((aligned['strict'] - aligned['centre']).abs().max()):.3e} "
      f"over {len(aligned)} cycles  (H4: inert to 0.0)")
'''))

cells.append(md("""## Part 2. The cheap gates, both centres

Gates 1, 7, 4, 5, 3, 8 and 6 need no further simulation. Gate 3 under A4 is scored on the
volatility leg on the dates common to candidate and anchor from 2026-04-01; the count of those
dates, the same comparison on dates whose entire 90-row lookback is post-break, and both
concentration indicators with their coverage are printed beside it.
"""))
cells.append(code('''anchor_entry = run_by_label["anchor"]
anchor_measures = diversification_cached(anchor_entry)
print("anchor diversification:", {k: round(v, 4) if isinstance(v, float) else v for k, v in anchor_measures.items()})
print(f"anchor luck_ratio {float(anchor_panel['luck_ratio']):.4f}, top5_gross_share {float(anchor_panel['top5_gross_share']):.4f}")

cheap_rows, g3_rows, g8_rows = [], [], []
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    entry = run_by_label[label]
    row = entry["panel"]
    g3 = gate_3_v3(label)
    g8 = gate_8_v3(entry, anchor_entry)
    plateau = plateau_gate(label, [label_for(signal, n) for n in NEIGHBOURS])
    segments = [float(row.get(f"{r}_cagr", np.nan)) for r in ("sparse", "dense", "late")]
    cheap_rows.append({
        "label": label, "signal": signal,
        "gate_1_positive": bool(np.isfinite(row["cagr"]) and float(row["cagr"]) > 0),
        "gate_7_subperiod": bool(all(np.isfinite(s) and s > 0 for s in segments)),
        "gate_4_luck": bool(np.isfinite(row["luck_ratio"]) and np.isfinite(row["top5_gross_share"])
                            and float(row["luck_ratio"]) >= float(anchor_panel["luck_ratio"])
                            and float(row["top5_gross_share"]) <= float(anchor_panel["top5_gross_share"])),
        "gate_5_screen": bool(GATE_5.get(signal, False)),
        "gate_3_held_book": g3["gate_3_volatility"],
        "gate_8_diversification": g8["gate_8_diversification"],
        "gate_6_plateau": plateau["passes"],
        "diversification_failures": g8["diversification_failures"],
    })
    g3_rows.append({"label": label, **g3})
    g8_rows.append({"label": label, **{k: g8[k] for k in list(DIVERSIFICATION_MEASURES) + ["mean_holdings_vs_anchor"]}})
cheap = pd.DataFrame(cheap_rows).set_index("label")
CHEAP_GATES = ["gate_1_positive", "gate_7_subperiod", "gate_4_luck", "gate_5_screen",
               "gate_3_held_book", "gate_8_diversification", "gate_6_plateau"]
cheap["all_cheap_gates"] = cheap[CHEAP_GATES].all(axis=1)
pd.set_option("display.max_colwidth", None)
display(cheap[["signal"] + CHEAP_GATES + ["all_cheap_gates", "diversification_failures"]])

gate3 = pd.DataFrame(g3_rows).set_index("label")
print("\\ngate 3 (A4) - volatility leg on common post-break dates, with the full-lookback and whole-window comparisons:")
display(gate3[["gate_3_volatility", "gate_3_evaluable", "gate_3_dates", "held_vol_post", "anchor_held_vol_post",
               "full_lookback_dates", "held_vol_full_lookback", "anchor_held_vol_full_lookback", "gate_3_full_lookback_lower",
               "all_common_dates", "held_vol_all_dates", "anchor_held_vol_all_dates"]].round(6))
print("\\nconcentration legs, DIAGNOSTIC (180-row indicators are not identifiable before late September):")
display(gate3[["conc_post_dates", "conc_full_lookback_dates", "held_conc_post", "anchor_held_conc_post", "conc_lower_post",
               "conc_pos_post_dates", "held_conc_pos_post", "anchor_held_conc_pos_post", "conc_pos_lower_post"]].round(6))
print("\\ngate 8 (A3):")
display(pd.DataFrame(g8_rows).set_index("label").round(4))
for signal in SIGNAL_NAMES:
    display(plateau_gate(label_for(signal, CENTRE), [label_for(signal, n) for n in NEIGHBOURS])["detail"].assign(signal=signal))
'''))

cells.append(md("""## Part 3. The expensive gates - protocol, then diagnostic

PROTOCOL: leave-one-vault-out on the centre and both neighbours of every signal that passed all
seven cheap gates, then nineteen null seeds at each such centre. A centre that failed a cheaper
gate gets no gate-2 or gate-9 run and both are False in its verdict row.

DIAGNOSTIC, in the next cells and labelled as such: the same runs for BOTH centres regardless.
Gate 5's return clause is the one gate this plan has never been able to resolve on this sample,
and if it is what fails, the plan's genuinely open questions - the null and the mask - would
otherwise go unanswered. The verdict is not changed by a diagnostic; the reader can see what
the gates WOULD have said.

The null permutes the finite signal values within each date, so it destroys ranking information
AND temporal persistence; the persistence and turnover columns show how far the null's books are
from the centre's, which is what a pass does and does not mean.
"""))
cells.append(code('''SURVIVORS = [s for s in SIGNAL_NAMES if bool(cheap.loc[label_for(s, CENTRE), "all_cheap_gates"])]
print(f"signals reaching the expensive gates: {SURVIVORS or 'none'}")

lovo_rows = []
for signal in SURVIVORS:
    for count in (CENTRE,) + NEIGHBOURS:
        lovo_rows.append(lovo_gate(label_for(signal, count)))
if lovo_rows:
    display(pd.DataFrame(lovo_rows).set_index("label").round(6))
else:
    print("no leave-one-vault-out run executed; gate 2 is False for every candidate")
'''))

cells.append(code('''NULL_SEEDS = tuple(range(NULL_MIN_DISTINCT_V3))
for signal in SURVIVORS:
    for seed in NULL_SEEDS:
        run_and_record(f"{label_for(signal, CENTRE)}_null{seed}", "null",
                       **prefilter_overrides(signal, count=CENTRE, seed=seed))

null_rows = []
for signal in SURVIVORS:
    labels = [f"{label_for(signal, CENTRE)}_null{seed}" for seed in NULL_SEEDS]
    result = null_effectiveness_v3(label_for(signal, CENTRE), labels)
    result["signal"] = signal
    null_rows.append(result)
if null_rows:
    null_table = pd.DataFrame(null_rows).set_index("centre")
    display(null_table[["signal", "draws", "distinct_cycle_return_series", "distinct_baskets", "distinct_excluded_sets",
                        "centre_sharpe", "null_best", "null_median", "null_sharpe_rank_of_centre", "add_one_p_if_beats_all", "passes"]].round(6))
    display(null_table[["centre_persistence", "null_persistence_mean", "centre_turnover", "null_turnover_mean",
                        "centre_trades", "null_trades_mean"]].round(4))
    null_detail = pd.DataFrame([
        {"label": label, **{k: float(run_by_label[label]["panel"][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd")},
         **turnover_and_persistence(run_by_label[label])}
        for signal in SURVIVORS for label in [f"{label_for(signal, CENTRE)}_null{seed}" for seed in NULL_SEEDS]
    ]).set_index("label")
    display(null_detail.round(6))
else:
    print("no null executed; gate 9 is False for every candidate")
'''))

cells.append(md("""### Diagnostic: the mask and the null for both centres, whatever the cheap gates said

Labelled DIAGNOSTIC. Identical runs to the protocol's, cached by label so a centre that did
survive is not run twice. The `would_pass` columns are what gates 2 and 9 would have returned;
they do not enter the verdict.
"""))
cells.append(code('''DIAG_SIGNALS = [s for s in SIGNAL_NAMES if s not in SURVIVORS]
print(f"diagnostic expensive runs for: {DIAG_SIGNALS or 'none (every centre survived the cheap gates)'}")
diag_lovo_rows = []
for signal in DIAG_SIGNALS:
    for count in (CENTRE,) + NEIGHBOURS:
        diag_lovo_rows.append(lovo_gate(label_for(signal, count)))
for signal in DIAG_SIGNALS:
    for seed in NULL_SEEDS:
        run_and_record(f"{label_for(signal, CENTRE)}_null{seed}", "null_diagnostic",
                       **prefilter_overrides(signal, count=CENTRE, seed=seed))
diag_null_rows = []
for signal in DIAG_SIGNALS:
    labels = [f"{label_for(signal, CENTRE)}_null{seed}" for seed in NULL_SEEDS]
    result = null_effectiveness_v3(label_for(signal, CENTRE), labels)
    result["signal"] = signal
    diag_null_rows.append(result)

expensive_diag = []
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    lovo_row = next((r for r in lovo_rows + diag_lovo_rows if r["label"] == label), None)
    null_row = next((r for r in null_rows + diag_null_rows if r["centre"] == label), None)
    expensive_diag.append({
        "label": label, "protocol_survivor": signal in SURVIVORS,
        "lovo_masked": lovo_row["masked"] if lovo_row else None,
        "lovo_retention": lovo_row["retention"] if lovo_row else np.nan,
        "gate_2_would_pass": bool(lovo_row["passes"]) if lovo_row else False,
        "null_draws": null_row["draws"] if null_row else 0,
        "distinct_cycle_return_series": null_row["distinct_cycle_return_series"] if null_row else 0,
        "centre_sharpe": null_row["centre_sharpe"] if null_row else np.nan,
        "null_best": null_row["null_best"] if null_row else np.nan,
        "null_median": null_row["null_median"] if null_row else np.nan,
        "null_rank_of_centre": null_row["null_sharpe_rank_of_centre"] if null_row else None,
        "gate_9_would_pass": bool(null_row["passes"]) if null_row else False,
        "centre_persistence": null_row["centre_persistence"] if null_row else np.nan,
        "null_persistence_mean": null_row["null_persistence_mean"] if null_row else np.nan,
        "centre_turnover": null_row["centre_turnover"] if null_row else np.nan,
        "null_turnover_mean": null_row["null_turnover_mean"] if null_row else np.nan,
    })
expensive_diag = pd.DataFrame(expensive_diag).set_index("label")
print("DIAGNOSTIC - gates 2 and 9 as they WOULD have scored; not part of any verdict:")
display(expensive_diag.round(4))
if diag_lovo_rows:
    display(pd.DataFrame(diag_lovo_rows).set_index("label").round(6))
all_null_labels = [l for l in run_by_label if "_null" in l]
if all_null_labels:
    null_detail_all = pd.DataFrame([
        {"label": label, "family": run_by_label[label]["family"],
         **{k: float(run_by_label[label]["panel"][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd")},
         **turnover_and_persistence(run_by_label[label])}
        for label in all_null_labels]).set_index("label")
    display(null_detail_all.round(6))
'''))

cells.append(md("""## Part 4. The fee differential and the verdict table

Amendment A6: the independent recomputation's net signed fee discrepancy, candidate minus
anchor, as a share of the candidate-minus-anchor final-equity difference, for every run. Then
every gate Boolean, every failure named in full, and the fee condition; SHORTLIST is the
strongest verdict available.
"""))
cells.append(code('''fee_rows = []
for entry in runs:
    if entry["label"] == "anchor" or entry.get("state") is None:
        continue
    fee_rows.append({"label": entry["label"], "family": entry["family"], **fee_differential(entry["label"])})
fees = pd.DataFrame(fee_rows).set_index("label")
anchor_fee = fee_audit_cached("anchor")
print(f"anchor: {anchor_fee['redemptions']} redemptions, {anchor_fee['over_1bp']} over 1 bp, net signed "
      f"{anchor_fee['net_signed_proceeds_diff_usd']:+.2f} USD, final equity {float(run_by_label['anchor']['equity'].iloc[-1]):,.2f}")
display(fees[["family", "fee_redemptions", "fee_over_1bp", "fee_net_signed_usd", "fee_differential_usd", "equity_gap_usd",
              "fee_differential_share_of_gap", "fee_differential_ok"]].round(4))
'''))

cells.append(code('''verdict_rows = []
for signal in SIGNAL_NAMES:
    label = label_for(signal, CENTRE)
    nulls = [f"{label}_null{seed}" for seed in NULL_SEEDS] if signal in SURVIVORS else []
    verdict_rows.append(gate_row_v3(label, gate_5_by_signal=GATE_5, signal=signal,
                                    neighbours=[label_for(signal, n) for n in NEIGHBOURS], null_labels=nulls))
verdicts = verdict_table_rules(verdict_rows)
GATE_COLUMNS = ["gate_1_positive", "gate_2_lovo", "gate_3_held_book", "gate_4_luck", "gate_5_screen",
                "gate_6_plateau", "gate_7_subperiod", "gate_8_diversification", "gate_9_null"]
display(verdicts[["signal", "cycle_sharpe", "cagr"] + GATE_COLUMNS + ["fee_differential_ok", "verdict"]])
print("\\nfailure strings, complete:")
for label, row in verdicts.iterrows():
    print(f"  {label}: failed_gates = {row['failed_gates']!r}; diversification_failures = {row['diversification_failures']!r}; "
          f"lovo_masked = {row['lovo_masked']!r}; fee share {row['fee_differential_share_of_gap']:.4f}")
display(verdicts[["lovo_retention", "null_draws", "distinct_cycle_return_series", "null_best", "fee_differential_usd",
                  "equity_gap_usd", "fee_differential_share_of_gap"]].round(6))

shortlisted = [l for l, r in verdicts.iterrows() if r["verdict"] == "SHORTLIST"]
if len(shortlisted) == 2:
    tb = tie_break(shortlisted[0], shortlisted[1])
    print("\\ntie-break:", tb)
elif len(shortlisted) == 1:
    print(f"\\nonly {shortlisted[0]} is shortlisted" + (" - the guard is not adopted" if shortlisted[0] == "measured_8" else ""))
else:
    print("\\nnothing shortlisted")
'''))

cells.append(md("""## Part 5. H3 - the incumbent's window and the full data period

A consistency check on overlapping windows, not a gate and not independent confirmation. The
anchor, `calm_8` and `measured_8` on 2026-01-01 to 2026-07-10 (the incumbent's docstring
window) and on 2025-08-01 to 2026-09-09 (everything). Runs are slim; the cost-basis helper is
redefined with a relative tolerance for the full window exactly as NB33 did.
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
WINDOW_CONFIGS = {"anchor": {}, "calm_8": prefilter_overrides("calm_score", count=CENTRE),
                  "measured_8": prefilter_overrides("inverse_vol", count=CENTRE)}
WINDOW_RESULTS = {}


def run_window(label: str, window, **overrides) -> dict:
    name, start, end = window
    VOL_DROP_LOG.clear(); COMPLEMENT_LOG.clear(); SLEEVE_LOG.clear(); PREFILTER_LOG.clear()
    state_, equity_, returns_ = run_variant(f"{label} [{name}]", backtest_start=start, backtest_end=end, **overrides)
    rc, _ppy = cycle_returns(equity_)
    daily = equity_.resample("1D").last().ffill().pct_change().dropna()
    row = panel(f"{label} [{name}]", state_, equity_, returns_)
    row["daily_sharpe"] = float(daily.mean() / daily.std() * (365 ** 0.5)) if daily.std() > 0 else float("nan")
    row["cumulative_return"] = float(equity_.iloc[-1] / equity_.iloc[0] - 1.0)
    row["final_equity"] = float(equity_.iloc[-1])
    row["cycles"] = int(len(rc))
    row["fee_net_signed_usd"] = independent_fee_audit_v3(state_)["net_signed_proceeds_diff_usd"]
    entry = {"label": label, "window": name, "equity": equity_, "cycle_returns": rc, "panel": row}
    WINDOW_RESULTS[(label, name)] = entry
    return entry


for window in (WINDOW_A, WINDOW_B):
    for label, overrides in WINDOW_CONFIGS.items():
        run_window(label, window, **overrides)

WINDOW_COLUMNS = ["cumulative_return", "cagr", "cycle_sharpe", "daily_sharpe", "cycle_vol", "ulcer", "max_dd",
                  "mean_invested", "luck_ratio", "top5_gross_share", "cycles", "final_equity", "fee_net_signed_usd"]
h3_rows = []
for window in (WINDOW_A, WINDOW_B):
    name = window[0]
    frame = pd.DataFrame([WINDOW_RESULTS[(l, name)]["panel"] for l in WINDOW_CONFIGS]).set_index("label")[WINDOW_COLUMNS]
    frame.index = list(WINDOW_CONFIGS)
    print(f"\\n{name}:")
    display(frame.round(4))
    for label in ("calm_8", "measured_8"):
        c, a = frame.loc[label], frame.loc["anchor"]
        h3_rows.append({"window": name, "label": label,
                        "sharpe_better": bool(c["cycle_sharpe"] > a["cycle_sharpe"]),
                        "vol_lower": bool(c["cycle_vol"] < a["cycle_vol"]),
                        "max_dd_shallower": bool(c["max_dd"] > a["max_dd"]),
                        "return_higher": bool(c["cumulative_return"] > a["cumulative_return"]),
                        "fee_differential_usd": float(c["fee_net_signed_usd"] - a["fee_net_signed_usd"]),
                        "equity_gap_usd": float(c["final_equity"] - a["final_equity"])})
h3 = pd.DataFrame(h3_rows).set_index(["window", "label"])
h3["fee_share_of_gap"] = (h3["fee_differential_usd"].abs() / h3["equity_gap_usd"].abs()).replace([np.inf], np.nan)
h3["H3"] = h3[["sharpe_better", "vol_lower", "max_dd_shallower"]].all(axis=1)
display(h3.round(4))
'''))

cells.append(md("""## Part 6. Manifest

Everything NB36 re-derives is written here with the provenance it was produced on.
"""))
cells.append(code('''def plain(row: dict) -> dict:
    return {k: (v.to_dict(orient="records") if isinstance(v, pd.DataFrame) else v) for k, v in row.items()}

manifest = {
    "verdicts": {l: r["verdict"] for l, r in verdicts.iterrows()},
    "shortlisted": shortlisted,
    "gate_5_imported": GATE_5,
    "constants": {k: (v if isinstance(v, (int, float, str)) else str(v)) for k, v in constants.items()},
    "provenance": provenance_record(),
    "track": track.round(10).to_dict(orient="index"),
    "inertness": inert.round(10).to_dict(orient="index"),
    "strict_vs_centre_max_abs_cycle_diff": float((aligned["strict"] - aligned["centre"]).abs().max()),
    "cheap_gates": cheap.to_dict(orient="index"),
    "gate_3": gate3.round(10).to_dict(orient="index"),
    "gate_8": pd.DataFrame(g8_rows).set_index("label").round(10).to_dict(orient="index"),
    "anchor_diversification": anchor_measures,
    "plateau": {s: plateau_gate(label_for(s, CENTRE), [label_for(s, n) for n in NEIGHBOURS])["detail"].to_dict(orient="records")
                for s in SIGNAL_NAMES},
    "survivors": SURVIVORS,
    "lovo": [plain(r) for r in lovo_rows],
    "nulls": [plain(r) for r in null_rows],
    "null_detail": (null_detail.round(10).to_dict(orient="index") if null_rows else {}),
    "expensive_diagnostic": expensive_diag.round(10).to_dict(orient="index"),
    "diag_lovo": [plain(r) for r in diag_lovo_rows],
    "diag_nulls": [plain(r) for r in diag_null_rows],
    "null_detail_all": (null_detail_all.round(10).to_dict(orient="index") if all_null_labels else {}),
    "fees": fees.round(10).to_dict(orient="index"),
    "anchor_fee": anchor_fee,
    "verdict_rows": [plain({k: v for k, v in r.items() if k != "plateau_detail"}) for r in verdict_rows],
    "h3": h3.round(10).reset_index().to_dict(orient="records"),
    "windows": {name: {l: {k: float(v) if isinstance(v, (int, float, np.floating, np.integer)) else str(v)
                           for k, v in WINDOW_RESULTS[(l, name)]["panel"].items()} for l in WINDOW_CONFIGS}
                for name in (WINDOW_A[0], WINDOW_B[0])},
    "run_labels": [e["label"] for e in runs],
    "all_runs": {e["label"]: {"family": e["family"],
                              "overrides": {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in e["overrides"].items()},
                              "panel": {k: float(e["panel"][k]) for k in METRICS}}
                 for e in runs if e["label"] != "anchor"},
}
Path("_build/manifest_35.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_35.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "35-backtest-calm-tail-exclusion.ipynb")
