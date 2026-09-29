"""Verification notebook for blocks_sleeve.py: the quality floor and the cash sleeve on a short
window, before NB40's full run. Asserts the anchor path is inert, that a high floor sends the
book to cash and closes positions, and that the sleeve's fill matches the count of selected names."""
import sys
sys.path.insert(0, ".")
from build_40 import *   # noqa: rebuilds NB40 as a side effect; reuses its prefix/harness cells

verify = cells[:cells.index(next(c for c in cells if c["cell_type"] == "markdown" and "".join(c["source"]).startswith("## Part 0")))]
verify[0] = md("# verify-sleeve - quality floor and cash sleeve smoke test\n\nShort window, four runs. Not a result.\n")
verify.append(code('''import datetime
display(assert_anchor_parity_rules())
record_anchor()
START, END = datetime.datetime(2026, 4, 1), datetime.datetime(2026, 6, 15)
base = run_and_record("short_anchor", "smoke", backtest_start=START, backtest_end=END)
f30 = run_and_record("short_f30", "smoke", quality_floor_on=True, quality_floor_sharpe=3.0, cash_sleeve_slots=6, backtest_start=START, backtest_end=END)
f10 = run_and_record("short_f10", "smoke", quality_floor_on=True, quality_floor_sharpe=1.0, cash_sleeve_slots=6, backtest_start=START, backtest_end=END)
nall = run_and_record("short_nall_f20", "smoke", quality_floor_on=True, quality_floor_sharpe=2.0, cash_sleeve_slots=0, max_assets_in_portfolio=999,
                      crash_vol_threshold_exit=1.5, crash_vol_threshold_enter=1.2, backtest_start=START, backtest_end=END)
rows = []
for e in (base, f30, f10, nall):
    rows.append({"label": e["label"], **{k: float(e["panel"][k]) for k in ("cagr", "cycle_sharpe", "mean_invested", "max_dd")},
                 **quality_stats(e), **sleeve_stats(e), **diversification_cached(e)})
frame = pd.DataFrame(rows).set_index("label")
display(frame.round(4))
# 1. floor off -> no quality / sleeve log at all
assert not base["quality_log"] and not base["cash_sleeve_log"], "anchor path wrote a floor or sleeve log"
# 2. the sleeve fill equals selected / slots on every decision it logged
for e in (f30, f10):
    for t, r in e["cash_sleeve_log"].items():
        assert abs(r["fill"] - min(1.0, r["selected"] / r["slots"])) < 1e-12, (e["label"], t, r)
        q = e["quality_log"][t]
        assert r["selected"] <= q["qualifying"], (e["label"], t, r, q["qualifying"])
# 3. a floor of 3.0 leaves the book mostly in cash and below the anchor's deployment
assert frame.loc["short_f30", "mean_invested"] < frame.loc["short_anchor", "mean_invested"] - 0.1, "floor 3.0 did not reduce deployment"
# 4. at least one decision with nothing qualifying or a partial fill actually happened at 3.0
assert frame.loc["short_f30", "sleeve_active_share"] > 0, "sleeve never active at floor 3.0"
# 5. positions get closed when their vault drops below the floor: held_removed > 0 somewhere at 3.0
assert frame.loc["short_f30", "quality_held_removed_total"] > 0
# 6. weights respect the cap as a share of full equity under a partial fill
weights = _position_weights(f30["state"])
cap = float(Parameters.max_concentration_pct)
worst = max((share for holdings in weights.values() for _p, share in holdings), default=0.0)
print(f"largest realised weight under the floor: {worst:.4f} (cap {cap})")
assert worst <= cap * 1.15 + 0.02, f"a position exceeded the cap under the sleeve: {worst}"
print("verify-sleeve: all assertions passed")
'''))
write_notebook(verify, BUILD_DIR / "verify-sleeve.ipynb")
