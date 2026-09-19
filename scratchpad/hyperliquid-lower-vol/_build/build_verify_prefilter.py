import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, INDICATOR_ADDITIONS_PREFILTER, \
    CELL14_REPLACEMENTS_PREFILTER

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()

HEADING = """# Verification: the stable-selection splices

Not a research notebook. Proves, before NB28-NB31 are built, that:

1. the anchor is bit-identical to `BASELINE` with all three `decide_trades` splices present, and
   none of them fires on the anchor path;
2. `vol_drop_mode = 'measured_only'` at N = 8 still reproduces NB26's `measured_8`
   (0.409685 / 2.373768), so the module chain has not disturbed the earlier track;
3. the new `stability_prefilter` with `inverse_vol` and a count of 8 reproduces `measured_8` on
   EVERY panel metric - the prefilter generalises NB26's drop rather than approximating it;
4. `fresh_event_concentration` is invariant to inserting unchanged marks at new intermediate
   timestamps, which is the only invariance it claims;
5. the offline indicator reads `harness_rules.py` uses for the screen and for gate 3 reproduce
   the values `decide_trades` actually read at T-1, taken from `PREFILTER_LOG`;
6. the within-date permutation null produces genuinely different exclusions across seeds.
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "verify-prefilter",
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

cells.append(md("## 1. Anchor parity, and all three splices inert on the anchor path\n"))
cells.append(code('''display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
print(f"delta = {DELTA_ANNUALISED_PP} annualised percentage points")
'''))

cells.append(md("""## 2. NB26's `measured_8` still reproduces

The drop-mode module is now three links down a chain (`blocks_stability` -> `blocks_drop_modes`
-> `blocks_prefilter`). If any link disturbed the earlier splices this figure moves.
"""))
cells.append(code('''measured = run_and_record("measured_8", "control",
                          vol_drop_mode="measured_only", vol_matched_drop_count=8)
row = measured["panel"]
print(f"measured_8 CAGR {row['cagr']:.6f} (NB26 recorded 0.409685)")
print(f"measured_8 cycle Sharpe {row['cycle_sharpe']:.6f} (NB26 recorded 2.373768)")
assert abs(float(row["cagr"]) - 0.409685) <= 1e-5, "measured_8 CAGR moved"
assert abs(float(row["cycle_sharpe"]) - 2.373768) <= 1e-5, "measured_8 Sharpe moved"
'''))

cells.append(md("""## 3. The prefilter reproduces `measured_8` exactly

`stability_prefilter_signal = 'inverse_vol'`, direction `low`, count 8. The prefilter excludes
the eight FINITE-signal candidates at the least-stable end; `measured_only` drops the eight
lowest `inverse_vol` among candidates whose estimate exists. Those should be the same eight
vaults on every decision, so every panel metric should agree to floating-point noise.

If they disagree, the prefilter is not the generalisation of NB26's drop that NB29 assumes it is,
and the whole family loses its reference point.
"""))
cells.append(code('''prefiltered = run_and_record(
    "prefilter_inverse_vol_8", "control",
    **prefilter_overrides("inverse_vol", count=8),
)
columns = ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta",
           "mean_invested", "late_cagr", "late_ulcer"]
comparison = pd.DataFrame([measured["panel"], prefiltered["panel"]]).set_index("label")[columns]
comparison.loc["abs_diff"] = (comparison.iloc[0] - comparison.iloc[1]).abs()
display(comparison)
worst = float(comparison.loc["abs_diff"].max())
print(f"largest absolute difference across the nine metrics: {worst:.3e}")
assert worst <= 1e-9, "the prefilter does NOT reproduce measured_only; they select different vaults"

log = prefiltered["prefilter_log"]
counts = prefilter_exclusion_frame(prefiltered)
display(counts.describe()[["pool_size", "measured", "nan", "excluded", "excluded_share"]])
print(f"decisions logged: {len(log)}")
'''))

cells.append(md("""## 4. `fresh_event_concentration` is invariant to inserted unchanged marks

The claim under test is narrow and is the only one the plan makes. The indicator is NOT
polling-invariant: the set of events depends on the poll schedule, and a vault polled twice as
often has different events. What it must be invariant to is a mark that repeats the previous
price at a NEW intermediate timestamp, because that is a poll carrying no information.

The test preserves every original price-change endpoint and the BTC path, inserts a repeated mark
halfway between each pair of consecutive original timestamps, and then asserts equality of the
value, of the finite/NaN mask and of the reported window span at the original timestamps.
"""))
cells.append(code('''def _insert_unchanged_marks(series: pd.Series) -> pd.Series:
    """Repeat each mark at the midpoint to the next timestamp. Every original endpoint survives."""
    rows = {}
    for a, b in zip(series.index, series.index[1:]):
        rows[a] = float(series.loc[a])
        midpoint = a + (b - a) / 2
        if midpoint != a and midpoint != b:
            rows[midpoint] = float(series.loc[a])
    rows[series.index[-1]] = float(series.iloc[-1])
    return pd.Series(rows).sort_index()


tested, skipped = [], 0
for pair_id in sorted({pid for t in log for pid in log[t]["candidate_ids"]}):
    pair = strategy_universe.get_pair_by_id(pair_id)
    original = fresh_event_concentration_frame(close_series(pair))
    if not np.isfinite(original["concentration"]).any():
        skipped += 1
        continue
    perturbed = fresh_event_concentration_frame(
        _insert_unchanged_marks(close_series(pair))
    ).reindex(original.index)
    value_ok = np.allclose(
        original["concentration"].to_numpy(), perturbed["concentration"].to_numpy(),
        rtol=0, atol=1e-12, equal_nan=True,
    )
    mask_ok = bool(
        (np.isfinite(original["concentration"]) == np.isfinite(perturbed["concentration"])).all()
    )
    span_ok = np.allclose(
        original["span_days"].to_numpy(), perturbed["span_days"].to_numpy(),
        rtol=0, atol=1e-12, equal_nan=True,
    )
    tested.append({"pair_id": pair_id, "finite_values": int(np.isfinite(original["concentration"]).sum()),
                   "value_ok": value_ok, "mask_ok": mask_ok, "span_ok": span_ok})

result = pd.DataFrame(tested)
print(f"vaults with a computable fresh-event concentration: {len(result)}; "
      f"skipped for having none: {skipped}")
display(result.head(10))
assert len(result) > 0, "no vault had a computable fresh-event concentration; the indicator is inert"
assert bool(result[["value_ok", "mask_ok", "span_ok"]].all().all()), \\
    f"inserted-mark invariance FAILED:\\n{result[~result[['value_ok','mask_ok','span_ok']].all(axis=1)]}"
print("inserted-mark invariance holds on every tested vault, for value, NaN mask and window span.")
'''))

cells.append(md("""## 5. The offline indicator reads reproduce what `decide_trades` read

`harness_rules.py` reads cached indicator series outside the backtest, for the screen and for
gate 3. If that read does not reproduce `get_indicator_value(..., index=-1)` exactly, the screen
is measuring a different signal from the one the mechanism trades on - and would do so silently.

`PREFILTER_LOG` carries the value the trading code actually read for every candidate on every
decision, so this is a direct comparison rather than an argument.
"""))
cells.append(code('''rows = []
for timestamp in sorted(log):
    record = log[timestamp]
    for pair_id, address in zip(record["candidate_ids"], record["candidate_addresses"]):
        pair = strategy_universe.get_pair_by_id(pair_id)
        rows.append({
            "date": pd.Timestamp(timestamp), "address": address,
            "in_trade": record["values"][address],
            "offline": value_at_prior(indicator_series("inverse_vol", pair), timestamp),
        })
reads = pd.DataFrame(rows)
both_nan = ~np.isfinite(reads["in_trade"]) & ~np.isfinite(reads["offline"])
agree = both_nan | np.isclose(reads["in_trade"], reads["offline"], rtol=0, atol=1e-12)
print(f"(candidate, date) reads compared: {len(reads)}")
print(f"agreeing: {int(agree.sum())}   disagreeing: {int((~agree).sum())}")
print(f"of which both NaN: {int(both_nan.sum())}")
if not bool(agree.all()):
    display(reads[~agree].head(20))
assert bool(agree.all()), "the offline read does NOT reproduce the in-trade read"
'''))

cells.append(md("""## 6. The within-date permutation null actually permutes

NB26's null was one draw repeated ten times and the tell - `null_median == null_best` on every
metric - was printed and missed. Two seeds are enough to show the mechanism is not degenerate;
NB29 runs ten and asserts on realised cycle-return series rather than on value maps, because two
different permutations can still produce identical baskets.
"""))
cells.append(code('''null_a = run_and_record("null_seed_0", "null",
                        **prefilter_overrides("inverse_vol", fraction=0.30, seed=0))
null_b = run_and_record("null_seed_1", "null",
                        **prefilter_overrides("inverse_vol", fraction=0.30, seed=1))
real = run_and_record("prefilter_inverse_vol_030", "candidate",
                      **prefilter_overrides("inverse_vol", fraction=0.30))

def excluded_history(entry):
    return [(str(t), entry["prefilter_log"][t]["excluded_addresses"]) for t in sorted(entry["prefilter_log"])]

a, b, r = excluded_history(null_a), excluded_history(null_b), excluded_history(real)
differing = sum(1 for x, y in zip(a, b) if x[1] != y[1])
print(f"decisions where seed 0 and seed 1 excluded a different set: {differing} of {len(a)}")
print(f"decisions where seed 0 differs from the real signal:       "
      f"{sum(1 for x, y in zip(a, r) if x[1] != y[1])} of {len(a)}")
assert differing > 0, "the two null seeds drew the same exclusions on every decision"

display(pd.DataFrame([anchor_panel, real["panel"], null_a["panel"], null_b["panel"]]).set_index("label")[
    ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested"]])
display(pd.DataFrame([inertness(real), inertness(null_a)]).set_index("label").T)
'''))

cells.append(md("""## 7. The gate machinery runs end to end

Not a verdict - `prefilter_inverse_vol_030` has no screen behind it yet, so gate 5 is False by
construction here. This only proves the gate functions execute, name their failures in full and
return False for anything unevaluated.
"""))
cells.append(code('''row = gate_row(
    "prefilter_inverse_vol_030",
    gate_5_by_signal={},
    signal="inverse_vol",
    neighbours=[],
    null_labels=["null_seed_0", "null_seed_1"],
)
display(pd.Series({k: v for k, v in row.items() if k != "plateau_detail"}).to_frame("value"))
print("failed gates:", row["failed_gates"])
print("verdict:", row["verdict"])
assert row["verdict"] == "REJECT", "a candidate with no screen behind it must not pass gate 5"
display(held_book_character_cached(run_by_label["anchor"]))
display(diversification_cached(run_by_label["anchor"]))
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, BUILD_DIR / "verify-prefilter.ipynb")
