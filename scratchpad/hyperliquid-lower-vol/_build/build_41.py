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
from blocks_sleeve import PARAM_ADDITIONS_SLEEVE, INDICATOR_ADDITIONS_SLEEVE, CELL14_REPLACEMENTS_SLEEVE

HARNESSES = [(BUILD_DIR / n).read_text() for n in (
    "harness_evidence.py", "harness_stability.py", "harness_rules.py", "harness_rules_v2.py", "harness_rules_v3.py",
    "harness_rules_v3_gates.py", "harness_threshold.py", "harness_forensics.py", "harness_trades.py")]

HEADING = """# NB41 - the trades: which vaults, why bought, why sold, what they did

NB40 measured how much of each lead's profit sat in which positions. This notebook names them
and reads each trade: the vault's own share-price path before the strategy bought it, while it
was held, and after it was sold; what the ranker saw on the decision that opened the position
(rank, the 360-day CAGR and 45-day Sortino legs, trailing volatility, the 180-day quality score);
and what closed it (the momentum gate, being outranked - and by whom -, the crash filter, the
quality floor, or the end of the window). Five runs: the incumbent, `thr150` (the crash filter at
1.5), `thr100` (at 1.0), `thr150_n4` (four names, cap off) and `anchor_f10` (the quality floor
at 1.0), reproduced from NB40 at 1e-6.

Entry and exit reasons are a RECONSTRUCTION from the cached indicator set at T-1 and the pool
each decision saw (a threshold run's crash log records the momentum-gated pool before its
filter): the in-trade tie order, deposit-window checks, quarantine and masks are not mirrored,
so a rank can be off by a place where scores tie. Every other figure is read from the runs'
position statistics or the vault's own marks.

**Based on:** [40-backtest-lead-forensics-cash-sleeve.ipynb](40-backtest-lead-forensics-cash-sleeve.ipynb).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "41-research-trade-forensics",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_SLEEVE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR + INDICATOR_ADDITIONS_RULES_FIXES
    + INDICATOR_ADDITIONS_THRESHOLD + INDICATOR_ADDITIONS_SLEEVE,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_SLEEVE)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
for text in HARNESSES:
    cells.append(code(text))

cells.append(md("""## Part 0. Provenance, parity, the five runs
"""))
cells.append(code('''import json
from pathlib import Path
display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
manifest_40 = json.loads(Path("_build/manifest_40.json").read_text())
THR150 = {"crash_vol_threshold_exit": 1.5, "crash_vol_threshold_enter": 1.2}
THR100 = {"crash_vol_threshold_exit": 1.0, "crash_vol_threshold_enter": 0.8}
RUNS = {
    "thr150": ("threshold", dict(THR150)),
    "thr100": ("threshold", dict(THR100)),
    "thr150_n4": ("positions", {**THR150, "max_assets_in_portfolio": 4, "max_concentration_pct": 1.0}),
    "anchor_f10": ("floor", {"quality_floor_on": True, "quality_floor_sharpe": 1.0, "cash_sleeve_slots": 6}),
}
for label, (family, overrides) in RUNS.items():
    run_and_record(label, family, **overrides)
repro = []
for label in ["anchor"] + list(RUNS):
    for metric in ("cagr", "cycle_sharpe", "max_dd"):
        here, there = float(run_by_label[label]["panel"][metric]), float(manifest_40["summary"][label][metric])
        repro.append(abs(here - there))
assert max(repro) < 1e-6, max(repro)
print(f"five runs reproduce NB40 at {max(repro):.1e}")
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 120); pd.set_option("display.max_rows", 200)
'''))

cells.append(md("""## Part 1. The incumbent's trades

Every position, by vault name, with the entry and exit reasons and the vault's own path. Then
the equity curve with the largest positions marked, and each of the ten largest vaults' own
share price with the held intervals shaded.
"""))
cells.append(code('''anchor_ledger = trade_ledger("anchor")
display(anchor_ledger[LEDGER_COLUMNS].round(3))
equity_with_positions("anchor", top=8).show()
TOP_VAULTS = list(dict.fromkeys(anchor_ledger.sort_values("pnl_usd", key=abs, ascending=False)["address"]))[:10]
for addr in TOP_VAULTS:
    vault_figure(addr, ["anchor"]).show()
'''))

cells.append(md("""### 1b. Entry and exit reasons, counted

How the incumbent's positions were opened and closed, and what the vault did afterwards: the
momentum gate's record (did the vault keep falling after the gate sold it?), and the outranked
exits (did the vault the ranker moved to do better than the one it dropped?).
"""))
cells.append(code('''def reason_class(text: str) -> str:
    for key in ("momentum gate", "outranked", "crash filter", "quality floor", "still open", "left the tradable", "in the top"):
        if isinstance(text, str) and text.startswith(key):
            return key
    return "other"


def reason_summary(label: str) -> pd.DataFrame:
    ledger = trade_ledger(label).copy()
    ledger["exit_class"] = ledger["exit_reason"].map(reason_class)
    g = ledger.groupby("exit_class")
    out = pd.DataFrame({"positions": g.size(), "pnl_usd": g["pnl_usd"].sum(), "win_rate": g["pnl_usd"].apply(lambda s: float((s > 0).mean())),
                        "median_days": g["days"].median(), "vault_return_30d_after_exit_median": g["vault_return_30d_after"].median(),
                        "vault_return_30d_after_exit_mean": g["vault_return_30d_after"].mean(),
                        "share_vault_fell_after_exit": g["vault_return_30d_after"].apply(lambda s: float((s.dropna() < 0).mean()) if s.notna().any() else np.nan)})
    out.index.name = label
    return out


display(reason_summary("anchor").round(3))
entry_view = anchor_ledger.copy()
entry_view["entry_rank_bucket"] = pd.cut(entry_view["entry_rank"], [0, 1, 3, 6, 999], labels=["#1", "#2-3", "#4-6", "below 6"])
display(entry_view.groupby("entry_rank_bucket", observed=True).agg(positions=("pnl_usd", "size"), pnl_usd=("pnl_usd", "sum"), win_rate=("pnl_usd", lambda s: float((s > 0).mean())),
                                                                   vault_return_90d_before_median=("vault_return_90d_before", "median"),
                                                                   vault_return_while_held_median=("vault_return_while_held", "median"),
                                                                   entry_vol_median=("entry_vol", "median")).round(3))
print("the pattern the ranker buys: the vault's own 90-day return before entry vs while held, all positions")
display(anchor_ledger[["vault_return_90d_before", "vault_return_while_held", "vault_return_30d_after", "vault_max_dd_while_held"]].describe().round(3))
'''))

cells.append(md("""### 1c. Where the profit came from: the vault's own return or the rebalancing

Each position's P&L split into what buying and holding the opening value would have made (the
vault's own share-price return over the holding) and the remainder, which is what the two-day
rebalancing did: under the 33% cap and inverse-variance sizing the strategy trims a name after
it rises and adds after it falls. On a mean-reverting or noisy mark that harvests the swings; on
a trending one it gives return away. The split matters because a harvested profit is only as
real as the marks: a stale or erroneous mark that is "bought" low and "sold" recovered is a
fictitious gain, which NB20 found the archive can contain.
"""))
cells.append(code('''def rebalancing_summary(label: str) -> dict:
    ledger = trade_ledger(label)
    return {"label": label, "positions": int(len(ledger)), "pnl_usd": float(ledger["pnl_usd"].sum()),
            "buy_and_hold_pnl_usd": float(ledger["buy_and_hold_pnl_usd"].sum()), "rebalancing_pnl_usd": float(ledger["rebalancing_pnl_usd"].sum()),
            "rebalancing_share_of_pnl": float(ledger["rebalancing_pnl_usd"].sum() / ledger["pnl_usd"].sum()) if ledger["pnl_usd"].sum() else np.nan,
            "positions_where_rebalancing_exceeds_vault_return": int((ledger["rebalancing_pnl_usd"] > ledger["buy_and_hold_pnl_usd"].abs()).sum())}


display(pd.DataFrame([rebalancing_summary("anchor")]).set_index("label").round(3))
print("the ten largest positions: vault return vs rebalancing")
display(anchor_ledger[["vault", "opened", "closed", "days", "pnl_usd", "opening_value_usd", "vault_return_while_held", "vault_max_dd_while_held", "buy_and_hold_pnl_usd", "rebalancing_pnl_usd"]].head(10).round(2))
'''))

cells.append(md("""## Part 2. What each lead did differently

For `thr150`, `thr100`, `thr150_n4` and `anchor_f10`: the ledger, the positions that exist in the
lead but not in the incumbent (and the reverse), and the vault figures for those names with both
runs' held intervals shaded.
"""))
cells.append(code('''def position_keys(ledger: pd.DataFrame) -> set:
    return {(r["address"], str(r["opened"])) for _, r in ledger.iterrows()}


ledgers = {"anchor": anchor_ledger}
diffs = {}
for label in RUNS:
    ledgers[label] = trade_ledger(label)
    mine, theirs = position_keys(ledgers[label]), position_keys(anchor_ledger)
    only_lead = ledgers[label][[(r["address"], str(r["opened"])) in (mine - theirs) for _, r in ledgers[label].iterrows()]]
    only_anchor = anchor_ledger[[(r["address"], str(r["opened"])) in (theirs - mine) for _, r in anchor_ledger.iterrows()]]
    diffs[label] = {"only_lead": only_lead, "only_anchor": only_anchor}
    print(f"\\n{'=' * 100}\\n{label}: {len(ledgers[label])} positions; {len(only_lead)} opened on dates the incumbent did not, {len(only_anchor)} of the incumbent's it did not open")
    display(reason_summary(label).round(3))
    print(f"\\n{label}: positions the incumbent does not have")
    display(only_lead[LEDGER_COLUMNS].round(3))
    print(f"\\n{label}: the incumbent's positions this run does not have")
    display(only_anchor[LEDGER_COLUMNS].round(3))
    equity_with_positions(label, top=6).show()
    for addr in list(dict.fromkeys(list(only_lead["address"]) + list(only_anchor["address"])))[:6]:
        vault_figure(addr, ["anchor", label]).show()
'''))

cells.append(md("""## Part 3. The engine vault and the four-name book, read closely

`Realist Capital` (`0x77fe..1a16`) is the largest position in every six-name run. Its full
history: every held interval of every run, the ranking it had at each of those decisions, and
its own path. Then `thr150_n4`'s book decision by decision through July, when the two-name
drawdown happened.
"""))
cells.append(code('''ENGINE = "0x77fee2df7bad4f1db93052fa82bf78eaab771a16"
print(vault_name(ENGINE))
vault_figure(ENGINE, ["anchor", "thr100", "thr150_n4", "anchor_f10"], start="2025-12-01").show()
rows = []
for label in ["anchor"] + list(RUNS):
    for (a, b, pnl) in held_intervals(label, ENGINE):
        r_in = _row_for(ranking_at(a), ENGINE)
        r_out = _row_for(ranking_at(b), ENGINE) if b is not None else None
        rows.append({"run": label, "opened": a.date(), "closed": b.date() if b is not None else None, "pnl_usd": pnl,
                     "entry_rank": int(r_in["rank"]) if r_in is not None else None, "entry_vol": float(r_in["vol"]) if r_in is not None else np.nan,
                     "entry_quality": float(r_in["quality_180d"]) if r_in is not None else np.nan,
                     "exit_rank": int(r_out["rank"]) if r_out is not None else None, "exit_return_14d": float(r_out["return_14d"]) if r_out is not None else np.nan,
                     "exit_reason": exit_reason(label, next(p for p in _vault_positions(run_by_label[label]["state"]) if str(p.pair.pool_address).lower() == ENGINE and pd.Timestamp(p.opened_at) == a))["exit_reason"]})
engine_intervals = pd.DataFrame(rows)
display(engine_intervals.round(3))
# The engine vault's rank, volatility, gate and quality at every decision from May to September.
timeline = []
for t in _decision_timestamps("anchor"):
    if t < pd.Timestamp("2026-05-15"):
        continue
    r = _row_for(ranking_at(t), ENGINE)
    held = {label: ENGINE in held_addresses_by_date(run_by_label[label]).get(t, {}) for label in ["anchor", "thr100", "thr150_n4", "anchor_f10"]}
    timeline.append({"decision": t.date(), "in_pool": r is not None, "rank": int(r["rank"]) if r is not None else None,
                     "vol": float(r["vol"]) if r is not None else np.nan, "return_14d": float(r["return_14d"]) if r is not None else np.nan,
                     "quality_180d": float(r["quality_180d"]) if r is not None else np.nan, **{f"held_{k}": v for k, v in held.items()}})
display(pd.DataFrame(timeline).round(3))
'''))
cells.append(code('''# thr150_n4 through July: the book at each decision with weights, and the cycle return.
n4 = run_by_label["thr150_n4"]
weights = _position_weights(n4["state"])
rc = n4["cycle_returns"]
rows = []
for t in sorted(weights):
    if not (pd.Timestamp("2026-06-15") <= t <= pd.Timestamp("2026-08-05")):
        continue
    book = sorted(((vault_name(str(p.pool_address)), share) for p, share in weights[t]), key=lambda x: -x[1])
    rows.append({"decision": t.date(), "cycle_return": float(rc.get(t, np.nan)), "book": "; ".join(f"{n} {s:.0%}" for n, s in book)})
display(pd.DataFrame(rows).round(4))
'''))

cells.append(md("""## Part 4. Manifest
"""))
cells.append(code('''def records(frame: pd.DataFrame) -> list:
    out = frame.copy()
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].map(lambda v: str(v) if v is not None and not isinstance(v, (str, float, int)) else v)
    return json.loads(out.round(6).to_json(orient="records", date_format="iso"))


manifest = {
    "provenance": provenance_record(),
    "reproduction_max_abs_diff": float(max(repro)),
    "ledgers": {label: records(frame) for label, frame in ledgers.items()},
    "reason_summary": {label: reason_summary(label).round(6).to_dict(orient="index") for label in ledgers},
    "rebalancing": {label: rebalancing_summary(label) for label in ledgers},
    "n4_july_book": records(pd.DataFrame(rows)),
    "diffs": {label: {k: records(v) for k, v in d.items()} for label, d in diffs.items()},
    "engine": {"address": ENGINE, "name": vault_name(ENGINE), "intervals": records(engine_intervals),
               "timeline": records(pd.DataFrame(timeline))},
    "top_vaults": [{"address": a, "name": vault_name(a)} for a in TOP_VAULTS],
}
Path("_build/manifest_41.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_41.json")
'''))
write_notebook(cells, TRACK_DIR / "41-research-trade-forensics.ipynb")
