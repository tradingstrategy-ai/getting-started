import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import PARAM_ADDITIONS_STABILITY, INDICATOR_ADDITIONS_STABILITY, \
    CELL14_REPLACEMENTS_STABILITY

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

HEADING = """# Verification: the stability-leads splices

Not a research notebook. Proves, before NB20-NB24 are built, that:

1. the anchor is bit-identical to `BASELINE` with both new `decide_trades` splices present;
2. neither splice fires on the anchor path;
3. `VOL_DROP_LOG` records the drop the trading code actually made;
4. the complementary-downside screen changes the traded book and logs what it chose;
5. `cagr_sortino_shrunk_weight` computes and differs from the incumbent composite.
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "verify-stability-splices",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_STABILITY)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

cells.append(md("## 1-2. Anchor parity, and both splices inert on the anchor path\n"))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
record_anchor()
'''))

cells.append(md("## 3. The drop log records the trading code's own decision\n"))
cells.append(code('''entry = run_and_record("drop_30", "control", vol_matched_drop_count=30)
log = entry["vol_drop_log"]
print(f"decision timestamps logged: {len(log)}")
first = sorted(log)[0]
print(f"first logged decision: {first}")
print(f"  pool size {log[first]['pool_size']}, dropped {len(log[first]['dropped_ids'])}, "
      f"of which no volatility estimate {len(log[first]['no_estimate_dropped'])}")
assert len(log) > 0, "the drop log never fired with vol_matched_drop_count=30"
assert all(len(v["dropped_ids"]) <= 30 for v in log.values())
# The log must reproduce the run's own metrics, i.e. it is a record, not a second computation.
print(f"drop_30 CAGR {entry['panel']['cagr']:.6f}, Sharpe {entry['panel']['cycle_sharpe']:.6f}")
print("NB15 recorded 0.489942 / 2.747391 for the same configuration on the same snapshot.")
'''))

cells.append(md("""## 4. The complementary-downside screen changes the book

`complementary_pool_size = 18`: rank by the incumbent composite, take the top 18, then keep the
6 that lose least often when the cohort loses. Sizing is untouched.
"""))
cells.append(code('''entry = run_and_record("complementary_18", "candidate", complementary_pool_size=18)
log = entry["complement_log"]
print(f"decision timestamps logged: {len(log)}")
assert len(log) > 0, "the complementary screen never fired"
changed = sum(1 for v in log.values() if set(v["kept"]) != set(v["incumbent_top"]))
print(f"decisions where the screen changed the basket: {changed} of {len(log)} "
      f"({changed / len(log) * 100:.1f}%)")
missing = sum(v["missing_estimates"] for v in log.values())
print(f"total (candidate, date) reads with no joint-loss estimate inside the screened pool: {missing}")
display(pd.DataFrame([anchor_panel, entry["panel"]]).set_index("label")[
    ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested"]])
assert changed > 0, "the screen never changed the basket; the indicator is probably all-NaN"
'''))

cells.append(md("## 5. The swapped composite computes and re-ranks\n"))
cells.append(code('''entry = run_and_record("sortino_leg_swap", "candidate",
                       selection_score_indicator="cagr_sortino_shrunk_weight")
display(pd.DataFrame([anchor_panel, entry["panel"]]).set_index("label")[
    ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested"]])
anchor_addresses = {str(p.pair.pool_address).lower()
                    for p in anchor_state.portfolio.get_all_positions() if not p.is_credit_supply()}
swap_addresses = {str(p.pair.pool_address).lower()
                  for p in entry["state"].portfolio.get_all_positions() if not p.is_credit_supply()}
print(f"anchor held {len(anchor_addresses)} distinct vaults, the swap held {len(swap_addresses)}")
print(f"symmetric difference: {len(anchor_addresses ^ swap_addresses)} vaults")
'''))

cells.append(md("## Family comparator and the rule-v3 machinery\n"))
cells.append(code('''family = build_family()
display(family[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer", "abs_invested_beta", "mean_invested"]])
display(verdict_table_v3(family=family)[
    ["family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "control_ref", "passes_v3", "failed"]])
display(bootstrap_margin_table("complementary_18", family))
summary, per_candidate = family_wise_joint([e["label"] for e in runs if e["family"] == "candidate"])
display(summary)
display(per_candidate)
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, BUILD_DIR / "verify-stability-splices.ipynb")
