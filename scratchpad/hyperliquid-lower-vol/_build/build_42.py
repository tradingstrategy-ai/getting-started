import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_floor import INDICATOR_ADDITIONS_FLOOR
from blocks_rules_fixes import INDICATOR_ADDITIONS_RULES_FIXES
from blocks_threshold import INDICATOR_ADDITIONS_THRESHOLD
from blocks_sleeve import INDICATOR_ADDITIONS_SLEEVE
from blocks_crash_exit import PARAM_ADDITIONS_CRASH_EXIT, INDICATOR_ADDITIONS_CRASH_EXIT, CELL14_REPLACEMENTS_CRASH_EXIT

HARNESSES = [(BUILD_DIR / n).read_text() for n in (
    "harness_evidence.py", "harness_stability.py", "harness_rules.py", "harness_rules_v2.py", "harness_rules_v3.py",
    "harness_rules_v3_gates.py", "harness_threshold.py", "harness_forensics.py", "harness_trades.py", "harness_crash_exit.py")]

HEADING = """# NB42 - crash exit: does the incumbent's exit fill before the gap?

Executes [42-crash-cluster-exit-plan.md](42-crash-cluster-exit-plan.md), Draft 5, after four
Grok reviews. The incumbent's worst episodes are good picks collapsing at the end of a long
hold (NB41). The plan asks the cheapest question first and stops when it is answered: what
PRICE did the backtest give the incumbent's own sells on the two collapse days (H0a), did that
price already skip the collapse bar (H0b), and does a four-point tighter momentum gate at the
incumbent's own 48-hour cadence (`gate12_2d`) sell the August position two days earlier and
survive the standing gates? A one-day cadence is a diagnostic; a cluster exit is a labelled
diagnostic of a T-1 point, run only if the tighter gate did not already sell on 19 Aug.

Every threshold was fixed in the plan before this notebook was built: -12% and -10% for the
gate, -10% x 2-in-3 for the cluster diagnostic, -20% for the breaker fire count. The two
collapse bars are the 21 Aug and 21 May daily candles; the warning bars 19 Aug and 20 May. The
collapse positions are identified by RULE - the incumbent's momentum-gate sells executed on
those two dates - never by name; names appear as labels only.

**Verdicts use the standing gates only** (RESEARCH-RULES.md, idiot-gate audit of 2026-09-16):
1 positive return, 2 single-vault mask, 3 held-book volatility, 6 plateau, 7 sub-period sign.
Gate 5 does not apply to a position-level exit. Nothing here is out of sample.

**Based on:** [41-research-trade-forensics.ipynb](41-research-trade-forensics.ipynb) and
[40-backtest-lead-forensics-cash-sleeve.ipynb](40-backtest-lead-forensics-cash-sleeve.ipynb) for
the machinery, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Track window
2026-01-01 to 2026-09-08.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "42-backtest-crash-exit",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_CRASH_EXIT},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR + INDICATOR_ADDITIONS_RULES_FIXES
    + INDICATOR_ADDITIONS_THRESHOLD + INDICATOR_ADDITIONS_SLEEVE + INDICATOR_ADDITIONS_CRASH_EXIT,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_CRASH_EXIT)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
for text in HARNESSES:
    cells.append(code(text))

cells.append(md("""## Run 1. The anchor, parity, and the pool loggers

`cluster_on` is False by default, so the two-day anchor must reproduce `BASELINE` with every
splice present (the parity assertion), and its five panel metrics must equal NB40's anchor -
run with a different splice set - at 1e-9. The pool loggers are the anchor with the crash
filter's threshold set far above any volatility (nothing excluded; identical cycle returns
asserted), so the momentum-gated candidate pool at every decision is logged for the ledgers.
"""))
cells.append(code('''import json
from pathlib import Path
display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
manifest_40 = json.loads(Path("_build/manifest_40.json").read_text())
for metric in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd"):
    here, there = float(run_by_label["anchor"]["panel"][metric]), float(manifest_40["summary"]["anchor"][metric])
    assert abs(here - there) < 1e-9, (metric, here, there)
print("anchor reproduces NB40's anchor on five metrics at 1e-9 with the cluster splice present and off")

POOL_OVERRIDES = {"crash_vol_threshold_exit": 99.0, "crash_vol_threshold_enter": 99.0}
pool_2d = run_and_record("pool_2d", "pool_logger", **POOL_OVERRIDES)
aligned = pd.concat([pool_2d["cycle_returns"].rename("a"), run_by_label["anchor"]["cycle_returns"].rename("b")], axis=1).dropna()
assert len(aligned) == len(run_by_label["anchor"]["cycle_returns"]) and np.allclose(aligned["a"], aligned["b"], atol=1e-12)
assert sum(r["excluded_count"] for r in pool_2d["crash_log"].values()) == 0
print(f"pool_2d is the anchor to 1e-12 on {len(aligned)} cycle returns; {len(pool_2d['crash_log'])} decisions logged")
POOL_SOURCE = "pool_2d"
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 120); pd.set_option("display.max_rows", 200)
'''))

cells.append(md("""## Part 0a. The path, the fire counts, the first-strike table

The collapse positions by rule: the anchor's momentum-gate sells executed on the two collapse
dates. Then the vaults' own paths from the raw archive (last mark per UTC day, and 4-hour
buckets), the 19 Aug reconstructed gate value beside the 19 Aug daily close, the single-day
stop table on the anchor's ledger, the tighter gate's and the breaker's fire counts on the
anchor's held book, and the first-strike table. Nothing here is a backtest.
"""))
cells.append(code('''anchor_ledger = trade_ledger("anchor")
COLLAPSE = {}
for key, date in COLLAPSE_DATES.items():
    hits = anchor_ledger[(anchor_ledger["closed"].astype(str) == str(date.date())) & anchor_ledger["exit_reason"].str.startswith("momentum gate")]
    assert len(hits) == 1, f"{key}: expected exactly one momentum-gate sell on {date.date()}, found {len(hits)}"
    COLLAPSE[key] = {"address": hits.iloc[0]["address"], "vault": hits.iloc[0]["vault"], "opened": str(hits.iloc[0]["opened"]),
                     "pnl_usd": float(hits.iloc[0]["pnl_usd"]), "exit_reason": hits.iloc[0]["exit_reason"], "hold_days": int(hits.iloc[0]["days"])}
display(pd.DataFrame(COLLAPSE).T)

# 1. The paths, daily and 4-hour, from the raw archive.
for key, c in COLLAPSE.items():
    date = COLLAPSE_DATES[key]
    print(f"\\n{key}: {c['vault']} daily (last mark per UTC day), {(date - pd.Timedelta(days=7)).date()} to {(date + pd.Timedelta(days=3)).date()}")
    display(archive_daily(c["address"], date - pd.Timedelta(days=7), date + pd.Timedelta(days=3)).round(4))
    print(f"{key}: 4-hour buckets, {(date - pd.Timedelta(days=2)).date()} to {(date + pd.Timedelta(days=1)).date()}")
    display(archive_4h(c["address"], date - pd.Timedelta(days=2), date + pd.Timedelta(days=1)).round(4))

# The 19 Aug gate value (T-1 read) beside the 19 Aug daily close: two different numbers that coincide.
aug = PAIR_BY_ADDRESS[COLLAPSE["august"]["address"]]
gate_series = indicator_series("return_gate", aug)
gate_dec = value_at_prior(gate_series, WARNING_DATES["august"])
gate_idx = gate_series.index[gate_series.index.searchsorted(WARNING_DATES["august"], side="left") - 1]
close_aug = close_series(aug)
i19 = close_aug.index.searchsorted(WARNING_DATES["august"] + pd.Timedelta(days=1), side="left") - 1
daily_19 = float(np.log(close_aug.iloc[i19] / close_aug.iloc[i19 - 1]))
GATE_19AUG = {"decision": str(WARNING_DATES["august"].date()), "gate_value_read_at_T-1": float(gate_dec), "gate_row_timestamp": str(gate_idx),
              "gate_threshold": float(Parameters.gate_threshold), "daily_log_return_on_19_aug": daily_19, "close_row_timestamp": str(close_aug.index[i19])}
display(pd.Series(GATE_19AUG, name="value").to_frame())
assert gate_dec <= -0.12 and gate_dec > -0.16, "the plan's premise: the 19 Aug T-1 gate value sits in (-16%, -12%]"
'''))
cells.append(code('''# 2. The single-day stop table on the anchor's ledger (the ad-hoc read, reproduced).
def stop_table(ledger: pd.DataFrame, thresh: float) -> pd.DataFrame:
    rows = []
    for _, r in ledger.iterrows():
        d = archive_daily(r["address"], pd.Timestamp(r["opened"]), pd.Timestamp(r["closed"]) if r["closed"] else WINDOW_END)
        dret = d["log_return"].dropna()
        breaches = dret[dret <= thresh]
        rows.append({"vault": r["vault"], "opened": r["opened"], "closed": r["closed"], "pnl_usd": r["pnl_usd"],
                     "first_breach": breaches.index.min().date() if len(breaches) else None,
                     "first_breach_return": float(breaches.iloc[0]) if len(breaches) else np.nan})
    return pd.DataFrame(rows)


STOP_TABLES = {}
for thresh in (-0.10, -0.15):
    st = stop_table(anchor_ledger, thresh)
    trig = st[st["first_breach"].notna()]
    STOP_TABLES[thresh] = {"triggered": int(len(trig)), "winners": int((trig["pnl_usd"] > 0).sum()), "winners_pnl": float(trig[trig["pnl_usd"] > 0]["pnl_usd"].sum()),
                           "losers": int((trig["pnl_usd"] < 0).sum()), "losers_pnl": float(trig[trig["pnl_usd"] < 0]["pnl_usd"].sum())}
    print(f"\\nsingle-day stop at {thresh:.0%}: {STOP_TABLES[thresh]}")
    display(trig.round(3))

# 3. 4-hour coverage per held vault by regime.
cov = []
for addr in anchor_ledger["address"].unique():
    for regime, (a, b) in {"sparse (to 2026-03-31)": (WINDOW_START, REGIME_BREAK - pd.Timedelta(days=1)), "dense (2026-04-01 on)": (REGIME_BREAK, WINDOW_END)}.items():
        c = bucket_coverage(addr, a, b, "4h")
        cov.append({"vault": vault_name(addr), "regime": regime, **c})
coverage = pd.DataFrame(cov)
COVERAGE_SUMMARY = coverage.groupby("regime")[["empty_share", "marks_per_bucket"]].agg(["mean", "median", "max"])
display(COVERAGE_SUMMARY.round(3))
for key, c in COLLAPSE.items():
    d = COLLAPSE_DATES[key]
    print(f"{key} collapse window 4h coverage:", bucket_coverage(c["address"], d - pd.Timedelta(days=2), d + pd.Timedelta(days=1), "4h"))
'''))
cells.append(code('''# 4. Fire counts on the anchor's PRE-decision held book (positions opened before the decision and
# not closed before it): the tighter gate (2b) and the breaker (2c).
FIRES = {}
for lo, hi, name in ((-0.16, -0.12, "gate (-16%, -12%]"), (-0.16, -0.10, "gate (-16%, -10%]")):
    f = gate_fire_count("anchor", lo, hi)
    FIRES[name] = f
    print(f"\\n{name}: {len(f)} held-vault decisions would be sold by the tighter gate and not by -16%")
    display(f.round(4))
breaker = breaker_fire_count("anchor", -0.20)
FIRES["breaker -20%"] = breaker
print(f"\\nbreaker -20%: {len(breaker)} held-vault decisions with a T-1 daily log return at or below -20%")
display(breaker.round(4))

# 5. The first-strike table on UTC days, first-entry rows per vault per class; every-day appendix.
first, every = first_strike_table("pool_2d")
def class_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cls, g in frame.groupby("class"):
        for h in ("fwd_1d", "fwd_2d"):
            m, lo, hi = block_bootstrap_mean(g[h], g["date"])
            rows.append({"class": cls, "horizon": h, "rows": int(len(g)), "mean": m, "ci_lo": lo, "ci_hi": hi, "median": float(g[h].median())})
    return pd.DataFrame(rows)


FIRST_SUMMARY = class_summary(first)
EVERY_SUMMARY = class_summary(every)
print("first-entry rows per vault per class (the primary table; the first `first_extreme` row is the morning AFTER the extreme close)")
display(FIRST_SUMMARY.round(4))
for key, c in COLLAPSE.items():
    print(f"{key} vault's first-entry rows:")
    display(first[first["address"] == c["address"]].round(4))
print("every-day classification (appendix; contains aftermath rows)")
display(EVERY_SUMMARY.round(4))

# 6. The in-sample percentile of each fixed threshold among candidate-day daily returns (diagnostic).
cand_returns = every["last_return"].dropna()
PERCENTILES = {str(t): float((cand_returns <= t).mean()) for t in (-0.10, -0.12, -0.16, -0.20)}
display(pd.Series(PERCENTILES, name="share of candidate-days at or below").to_frame())
'''))

cells.append(md("""## Part 0b. The fill assertion (the kill-switch)

On the anchor's trade objects: the two collapse sells and the first rank-exit sell, in calendar
order, of a position held under four days. The valuation price is `planned_mid_price` (before
the redemption fee); the reference is the `open` and `close` of the decision date's row in the
backtest candle universe. The 4-way label applies to the two collapse sells only. H0b: which
leg of the collapse day holds the crash.
"""))
cells.append(code('''FILLS, LABELS, LEGS = {}, {}, {}
for key, c in COLLAPSE.items():
    rec = fill_record("anchor", c["address"], COLLAPSE_DATES[key])
    assert rec is not None, f"{key}: no sell trade on {COLLAPSE_DATES[key].date()}"
    pair = PAIR_BY_ADDRESS[c["address"]]
    FILLS[key] = rec
    LABELS[key] = classify_fill(rec, pair, COLLAPSE_DATES[key])
    LEGS[key] = crash_leg(pair, COLLAPSE_DATES[key])
    warn = candle_row(pair, WARNING_DATES[key])
    LEGS[key]["warning_bar_open"] = warn["open"]
fills = pd.DataFrame(FILLS).T
display(fills)
display(pd.DataFrame(LABELS).T)
display(pd.DataFrame(LEGS).T)

# The pre-registered rank-churn sell: first rank exit, calendar order, hold under four days.
churn_rows = anchor_ledger[anchor_ledger["exit_reason"].str.startswith("outranked") & (anchor_ledger["days"] < 4)].sort_values("closed")
CHURN_EXAMPLE = fill_record("anchor", churn_rows.iloc[0]["address"], pd.Timestamp(churn_rows.iloc[0]["closed"]))
display(pd.Series(CHURN_EXAMPLE, name="value").to_frame())

# Lock-up: both collapse holds are past the 1-day and 4-day live lock-ups.
for key in COLLAPSE:
    assert FILLS[key]["hold_days"] > 4, (key, FILLS[key]["hold_days"])
print("both collapse holds exceed the 1-day (leader) and 4-day (HLP) live lock-ups:", {k: FILLS[k]["hold_days"] for k in FILLS})

H0A = {k: LABELS[k]["label"] for k in LABELS}
H0B = {k: LEGS[k]["crash_leg"] for k in LEGS}
assert all(v != "UNCLASSIFIED" for v in H0A.values()), f"UNCLASSIFIED fill; the notebook stops here: {H0A}"
LATER_RUNS_DIAGNOSTIC = any(v == "MISS" for v in H0A.values())
print(f"H0a: {H0A}; H0b: {H0B}; later runs diagnostic: {LATER_RUNS_DIAGNOSTIC}")
'''))

cells.append(md("""## Run 2. The tighter gate at the incumbent's cadence

`gate12_2d` and `gate10_2d`: the incumbent with `gate_threshold` -12% and -10%. Did `gate12_2d`
sell the August position on the 19 Aug decision at the H0a price kind? The cycle P&L of the
cycles ending on the collapse and warning dates, per run. Then the standing gates, with -16%
(`anchor`) and -10% as the plateau neighbours of -12%.
"""))
cells.append(code('''run_and_record("gate12_2d", "gate", gate_threshold=-0.12)
run_and_record("gate10_2d", "gate", gate_threshold=-0.10)
AUGUST_SELL = {}
for label in ("gate12_2d", "gate10_2d"):
    rec = fill_record(label, COLLAPSE["august"]["address"], WARNING_DATES["august"])
    if rec is None:
        AUGUST_SELL[label] = {"sold_on_19_aug": False}
        continue
    same_kind = np.isfinite(rec["planned_mid_price"]) and abs(rec["planned_mid_price"] - rec["decision_bar_open"]) <= REL_TOL * rec["decision_bar_open"]
    AUGUST_SELL[label] = {"sold_on_19_aug": True, "decision": str(rec["decision"]), "planned_mid_price": rec["planned_mid_price"],
                          "decision_bar_open": rec["decision_bar_open"], "valued_at_decision_open": bool(same_kind), "hold_days": rec["hold_days"]}
display(pd.DataFrame(AUGUST_SELL).T)
AUGUST_CAUGHT = bool(AUGUST_SELL["gate12_2d"].get("sold_on_19_aug") and AUGUST_SELL["gate12_2d"].get("valued_at_decision_open")) and not LATER_RUNS_DIAGNOSTIC
print(f"gate12_2d sold the August position on 19 Aug at the H0a price kind: {AUGUST_CAUGHT}")

CYCLE_DATES = [WARNING_DATES["august"], COLLAPSE_DATES["august"], COLLAPSE_DATES["august"] + pd.Timedelta(days=2),
               WARNING_DATES["may"] - pd.Timedelta(days=1), COLLAPSE_DATES["may"], COLLAPSE_DATES["may"] + pd.Timedelta(days=2)]
WINDOW_CYCLES = date_window_cycles(["anchor", "gate12_2d", "gate10_2d"], CYCLE_DATES)
display(WINDOW_CYCLES.pivot(index="cycle_end", columns="label", values=["cycle_return", "pnl_usd"]).round(4))

SUMMARY_COLUMNS = ["family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested", "luck_ratio", "top5_gross_share",
                   "sparse_cagr", "dense_cagr", "late_cagr", "final_equity", "mean_holdings", "mean_largest_weight", "distinct_vaults",
                   "top_vault_pnl_share", "turnover_per_decision", "trades", "share_of_decisions_changed"]


def summary_table(labels):
    return pd.DataFrame([summary_row_40(l) for l in labels]).set_index("label")[SUMMARY_COLUMNS]


display(summary_table(["anchor", "gate12_2d", "gate10_2d"]).round(4))
'''))
cells.append(code('''# Worst five cycles with and without the two collapse windows (the gate-2 diagnostic).
EXCLUDE = {pd.Timestamp(r["cycle_end"]) for _, r in WINDOW_CYCLES.iterrows() if r["cycle_end"] in (COLLAPSE_DATES["august"].date(), COLLAPSE_DATES["may"].date())}


def worst_five(label: str, exclude=frozenset()) -> float:
    rc = run_by_label[label]["cycle_returns"]
    rc = rc[~rc.index.isin(exclude)]
    return float(rc.sort_values().iloc[:5].sum())


WORST5 = pd.DataFrame([{"label": l, "worst5_with": worst_five(l), "worst5_without_collapse_cycles": worst_five(l, EXCLUDE)} for l in ("anchor", "gate12_2d", "gate10_2d")]).set_index("label")
display(WORST5.round(4))

# Standing gates: -12% with -16% (anchor) and -10% as neighbours; -10% is an endpoint.
NEIGHBOURS = {"gate12_2d": ["anchor", "gate10_2d"], "gate10_2d": ["gate12_2d"]}
cheap = pd.DataFrame([standing_gates_40(l, NEIGHBOURS[l]) for l in NEIGHBOURS]).set_index("label")
LOVO_2D = [l for l in NEIGHBOURS if cheap.loc[l, ["gate_1_positive", "gate_7_subperiod", "gate_3_held_vol"]].all()]
gates_2d = pd.DataFrame([standing_gates_40(l, NEIGHBOURS[l], run_lovo=(l in LOVO_2D)) for l in NEIGHBOURS]).set_index("label")
display(gates_2d[["gate_1_positive", "gate_7_subperiod", "gate_3_held_vol", "gate_6_plateau", "plateau_neighbours", "gate_2_mask", "mask_retention",
                  "diag_4_luck_within_tolerance", "diag_8_distinct_within_tolerance", "sharpe_gap_to_anchor", "failed_standing_gates", "standing_gates_not_run", "verdict"]].round(4))
for l in LOVO_2D:
    print(f"  {l}: masked {gates_2d.loc[l, 'masked']}, retention {gates_2d.loc[l, 'mask_retention']:.3f}")
# Churn, exactly: a position sold at a decision on which its vault was STILL in the in-trade
# candidate pool (the pool logger, which runs the anchor's -16% gate) was sold by ranking or
# sizing; one whose vault had left the pool was removed by the momentum gate or the universe
# screen. For the tighter-gate runs a candidate at or below their own threshold at T-1 is a
# pool removal. No rank reconstruction.
CHURN_EXACT = {"anchor": churn_pnl_exact("anchor", "pool_2d"), "gate12_2d": churn_pnl_exact("gate12_2d", "pool_2d", gate_threshold=-0.12),
               "gate10_2d": churn_pnl_exact("gate10_2d", "pool_2d", gate_threshold=-0.10)}
CHURN_2D = pd.DataFrame({l: {"churn_positions": v["churn"]["positions"], "churn_pnl_usd": v["churn"]["pnl_usd"], "churn_median_days": v["churn"]["median_days"],
                             "pool_removal_positions": v["pool_removal"]["positions"], "pool_removal_pnl_usd": v["pool_removal"]["pnl_usd"],
                             "open_positions": v["open"]["positions"], "open_pnl_usd": v["open"]["pnl_usd"], "unclassified": v["unclassified"]["positions"]}
                         for l, v in CHURN_EXACT.items()}).T
display(CHURN_2D.round(2))
# The ranking-based reconstruction of NB41, for comparison only.
CHURN_RECON_2D = pd.DataFrame([churn_pnl(l) for l in ("anchor", "gate12_2d", "gate10_2d")]).set_index("label")
display(CHURN_RECON_2D.round(2))
FEES_2D = pd.DataFrame([fee_differential(l) for l in ("gate12_2d", "gate10_2d")])
display(FEES_2D.round(4))
'''))

cells.append(md("""## Run 3. The one-day clock, as a diagnostic

`anchor_1d`: the incumbent on `cycle_1d`, nothing else changed. H1 on the two-day grid: the
one-day equity reindexed onto the anchor's decision timestamps. The one-day gates run only if
H1 passes AND run 2 did not sell the August position on 19 Aug.
"""))
cells.append(code('''run_and_record("anchor_1d", "cadence", cycle_duration=CycleDuration.cycle_1d)
pool_1d = run_and_record("pool_1d", "pool_logger", cycle_duration=CycleDuration.cycle_1d, **POOL_OVERRIDES)
aligned = pd.concat([pool_1d["cycle_returns"].rename("a"), run_by_label["anchor_1d"]["cycle_returns"].rename("b")], axis=1).dropna()
assert len(aligned) == len(run_by_label["anchor_1d"]["cycle_returns"]) and np.allclose(aligned["a"], aligned["b"], atol=1e-12)
GRID = pd.DataFrame([sharpe_on_2d_grid("anchor"), sharpe_on_2d_grid("anchor_1d")]).set_index("label")
display(GRID.round(4))
churn_1d_exact = churn_pnl_exact("anchor_1d", "pool_1d")
POOL_SOURCE = "pool_1d"
churn_1d_recon = churn_pnl("anchor_1d")
POOL_SOURCE = "pool_2d"
display(pd.DataFrame({"exact (in-trade pool)": {"churn_positions": churn_1d_exact["churn"]["positions"], "churn_pnl_usd": churn_1d_exact["churn"]["pnl_usd"],
                                                "pool_removal_positions": churn_1d_exact["pool_removal"]["positions"], "pool_removal_pnl_usd": churn_1d_exact["pool_removal"]["pnl_usd"],
                                                "open_pnl_usd": churn_1d_exact["open"]["pnl_usd"]},
                      "reconstructed (ranking)": {"churn_positions": churn_1d_recon["churn_positions"], "churn_pnl_usd": churn_1d_recon["churn_pnl_usd"]}}).round(2))
H1 = {"sharpe_on_2d_grid_gap": float(GRID.loc["anchor_1d", "cycle_sharpe_on_2d_grid"] - GRID.loc["anchor", "cycle_sharpe_on_2d_grid"]),
      "max_dd_gap_pp": float((run_by_label["anchor_1d"]["panel"]["max_dd"] - run_by_label["anchor"]["panel"]["max_dd"]) * 100),
      "churn_pnl_1d": churn_1d_exact["churn"]["pnl_usd"], "churn_pnl_anchor": float(CHURN_2D.loc["anchor", "churn_pnl_usd"]),
      "churn_positions_1d": churn_1d_exact["churn"]["positions"], "churn_positions_anchor": int(CHURN_2D.loc["anchor", "churn_positions"]),
      "pool_removal_pnl_1d": churn_1d_exact["pool_removal"]["pnl_usd"], "pool_removal_pnl_anchor": float(CHURN_2D.loc["anchor", "pool_removal_pnl_usd"])}
H1["passes"] = bool(abs(H1["sharpe_on_2d_grid_gap"]) <= INDIFFERENCE_BAND and H1["max_dd_gap_pp"] >= -1.0 and H1["churn_pnl_1d"] >= H1["churn_pnl_anchor"] - 1000.0)
display(pd.Series(H1, name="value").to_frame())
display(summary_table(["anchor", "anchor_1d"]).round(4))
FEES_1D = fee_differential("anchor_1d")
display(pd.Series(FEES_1D, name="value").to_frame())
cheap_1d = standing_gates_40("anchor_1d", [])
print({k: cheap_1d[k] for k in ("gate_1_positive", "gate_7_subperiod", "gate_3_held_vol", "held_vol_post", "anchor_held_vol_post")})

RUN_1D_GATES = bool(H1["passes"] and not AUGUST_CAUGHT)
RUN_CLUSTER = bool(not AUGUST_CAUGHT and not LATER_RUNS_DIAGNOSTIC)
print(f"one-day gates run: {RUN_1D_GATES}; cluster diagnostic run: {RUN_CLUSTER}")
gates_1d = None
if RUN_1D_GATES:
    run_and_record("gate12_1d", "gate_1d", cycle_duration=CycleDuration.cycle_1d, gate_threshold=-0.12)
    run_and_record("gate10_1d", "gate_1d", cycle_duration=CycleDuration.cycle_1d, gate_threshold=-0.10)
    gates_1d = pd.DataFrame([standing_gates_40("gate12_1d", ["anchor_1d", "gate10_1d"], anchor_label="anchor_1d"),
                             standing_gates_40("gate10_1d", ["gate12_1d"], anchor_label="anchor_1d")]).set_index("label")
    display(gates_1d.round(4))
cluster_row = None
if RUN_CLUSTER:
    run_and_record("cluster_1d", "cluster_diagnostic", cycle_duration=CycleDuration.cycle_1d, cluster_on=True, strike_threshold=-0.10, cluster_window=3)
    cluster_row = standing_gates_40("cluster_1d", [], anchor_label="anchor_1d")
    display(pd.Series(cluster_row, name="value").to_frame())
    log = run_by_label["cluster_1d"]["cluster_log"]
    cuts = [(str(t.date()), vault_name(a)) for t, r in sorted(log.items()) for a in r["cut"]]
    print(f"cluster exits: {len(cuts)}: {cuts}")
'''))

cells.append(md("""## Window A

The incumbent's own window (2026-01-01 to 2026-07-10), which contains May and NOT August, for
`anchor`, `anchor_1d` and `gate12_2d`. It cannot confirm an August-only effect.
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
WINDOW_RESULTS = {}
for label in ("anchor", "anchor_1d", "gate12_2d"):
    name, start, end = WINDOW_A
    overrides = dict(run_by_label[label]["overrides"]) if label != "anchor" else {}
    for log in (VOL_DROP_LOG, COMPLEMENT_LOG, SLEEVE_LOG, PREFILTER_LOG, CRASH_LOG, QUALITY_LOG, CASH_SLEEVE_LOG, CLUSTER_LOG):
        log.clear()
    state_, equity_, returns_ = run_variant(f"{label} [{name}]", backtest_start=start, backtest_end=end, **overrides)
    rc, _ppy = cycle_returns(equity_)
    row = panel(f"{label} [{name}]", state_, equity_, returns_)
    row["cumulative_return"] = float(equity_.iloc[-1] / equity_.iloc[0] - 1.0)
    row["cycles"] = int(len(rc))
    WINDOW_RESULTS[label] = row
window_a = pd.DataFrame(WINDOW_RESULTS).T[["cumulative_return", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested", "luck_ratio", "top5_gross_share", "cycles"]]
display(window_a.astype(float).round(4))
'''))

cells.append(md("""## Manifest
"""))
cells.append(code('''def jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return str(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


ALL = [e["label"] for e in runs if e["label"] != "anchor" and "__lovo" not in e["label"] and not e["label"].startswith("pool_")]
manifest = {
    "provenance": provenance_record(),
    "collapse": jsonable(COLLAPSE), "collapse_dates": {k: str(v.date()) for k, v in COLLAPSE_DATES.items()}, "warning_dates": {k: str(v.date()) for k, v in WARNING_DATES.items()},
    "gate_19aug": jsonable(GATE_19AUG),
    "stop_tables": {str(k): v for k, v in STOP_TABLES.items()},
    "coverage": jsonable(COVERAGE_SUMMARY.to_dict()),
    "fires": {k: jsonable(v.to_dict(orient="records")) for k, v in FIRES.items()},
    "first_strike_summary": jsonable(FIRST_SUMMARY.to_dict(orient="records")), "every_day_summary": jsonable(EVERY_SUMMARY.to_dict(orient="records")),
    "first_strike_collapse_rows": {k: jsonable(first[first["address"] == c["address"]].to_dict(orient="records")) for k, c in COLLAPSE.items()},
    "percentiles": PERCENTILES,
    "fills": jsonable(FILLS), "labels": jsonable(LABELS), "legs": jsonable(LEGS), "churn_example": jsonable(CHURN_EXAMPLE),
    "H0a": H0A, "H0b": H0B, "later_runs_diagnostic": LATER_RUNS_DIAGNOSTIC,
    "august_sell": jsonable(AUGUST_SELL), "august_caught": AUGUST_CAUGHT,
    "window_cycles": jsonable(WINDOW_CYCLES.to_dict(orient="records")), "worst5": jsonable(WORST5.to_dict(orient="index")),
    "summary": jsonable(summary_table(["anchor"] + ALL).round(10).to_dict(orient="index")),
    "gates_2d": jsonable(gates_2d.round(10).to_dict(orient="index")), "lovo_2d": LOVO_2D,
    "churn_2d": jsonable(CHURN_2D.to_dict(orient="index")), "churn_recon_2d": jsonable(CHURN_RECON_2D.to_dict(orient="index")),
    "churn_1d_exact": jsonable(churn_1d_exact), "churn_1d_recon": jsonable(churn_1d_recon),
    "fees_2d": jsonable(FEES_2D.to_dict(orient="records")), "fees_1d": jsonable(FEES_1D),
    "grid": jsonable(GRID.to_dict(orient="index")), "H1": jsonable(H1), "anchor_1d_cheap_gates": jsonable({k: cheap_1d[k] for k in ("gate_1_positive", "gate_7_subperiod", "gate_3_held_vol", "held_vol_post", "anchor_held_vol_post")}),
    "run_1d_gates": RUN_1D_GATES, "run_cluster": RUN_CLUSTER,
    "gates_1d": jsonable(gates_1d.round(10).to_dict(orient="index")) if gates_1d is not None else None,
    "cluster": jsonable(cluster_row) if cluster_row is not None else None,
    "window_a": jsonable(window_a.astype(float).round(10).to_dict(orient="index")),
    "anchor_ledger_summary": jsonable(ledger_summary("anchor")),
}
Path("_build/manifest_42.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_42.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "42-backtest-crash-exit.ipynb")
