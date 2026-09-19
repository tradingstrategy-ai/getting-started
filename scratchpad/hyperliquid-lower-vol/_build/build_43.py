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
    "harness_rules_v3_gates.py", "harness_threshold.py", "harness_forensics.py", "harness_trades.py", "harness_crash_exit.py",
    "harness_live.py")]

HEADING = """# NB43 - the live hyper-ai vault beside the backtest

The incumbent's backtest ([02-better-format.ipynb](02-better-format.ipynb), the `anchor` of
NB40-NB42) is quoted at 37.9% CAGR and a -4.5% maximum drawdown on 2026-01-01 to 2026-09-08.
The live `hyper-ai` Lagoon vault on HyperEVM has run since 2026-03-30 and is in a drawdown. This
notebook puts the two side by side and names the differences. It runs no new strategy variant.

Three things are compared. (1) The curves: the live share price - a depositor's return, unaffected
by deposit and redemption flow - against the anchor's equity, rebased on the same dates, over the
whole live period and over the window where the live instance ran the incumbent's own logic. (2) The
books: at every live decision, the vaults the live executor held against the vaults the anchor held
after its decision on the same day, with the anchor's reconstructed rank of each name held on one
side only. (3) The fills: the live executor decides and trades at a drifting time of day, the
backtest at the UTC day's open; for every live fill the vault's own mark at the day's first archive
mark is read against the mark at execution.

The live executor's history is a mix of strategy versions (v1 in March, v3 from late July, v4 and
v5 in mid-August; v6 changed only the backtest's fee accounting). Only from the move to the two-day
cycle on 2026-08-12 does the live instance run the logic the anchor backtests, so the like-for-like
window is 2026-08-12 to 2026-09-08 (the backtest's last day); the live curve is also shown to the
snapshot date.

**Based on:** [42-backtest-crash-exit.ipynb](42-backtest-crash-exit.ipynb) for the machinery,
[02-better-format.ipynb](02-better-format.ipynb) as the anchor. Live state: a dated snapshot of
`https://hyper-ai.tradingstrategy.ai/state`, read only. Names are labels; nothing is selected by name.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "43-research-live-vs-backtest",
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

cells.append(md("""## Part 0. The anchor, parity, the pool logger

The two-day anchor must reproduce NB40's anchor at 1e-9 on five panel metrics. The pool logger is
the anchor with the crash filter's threshold above any volatility (nothing excluded; identical
cycle returns asserted); its log gives the momentum-gated candidate pool at every backtest decision,
from which the anchor's ranking of any vault at any decision is reconstructed (NB41's method).
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
print("anchor reproduces NB40's anchor on five metrics at 1e-9")

POOL_OVERRIDES = {"crash_vol_threshold_exit": 99.0, "crash_vol_threshold_enter": 99.0}
pool_2d = run_and_record("pool_2d", "pool_logger", **POOL_OVERRIDES)
aligned = pd.concat([pool_2d["cycle_returns"].rename("a"), run_by_label["anchor"]["cycle_returns"].rename("b")], axis=1).dropna()
assert len(aligned) == len(run_by_label["anchor"]["cycle_returns"]) and np.allclose(aligned["a"], aligned["b"], atol=1e-12)
assert sum(r["excluded_count"] for r in pool_2d["crash_log"].values()) == 0
POOL_SOURCE = "pool_2d"
print(f"pool_2d is the anchor to 1e-12 on {len(aligned)} cycle returns; {len(pool_2d['crash_log'])} decisions logged")
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 160); pd.set_option("display.max_rows", 300)
'''))

cells.append(md("""## Part 1. The live instance

What the executor snapshot says about itself: launch, size, trade counts, the strategy versions
that have been live (commit dates from the strategies repository; deployment dates are read from
the cadence table - the two-day cycle starts with v4/v5), the share price with NAV and deposit /
redemption flow, monthly returns, and the deepest drawdowns of the share price.
"""))
cells.append(code('''FACTS = live_facts()
display(FACTS.to_frame("live"))
display(VERSION_TIMELINE)
CADENCE = live_cadence()
display(CADENCE)
live_overview_figure().show()
SP = live_share_price_daily()
LIVE_MONTHLY = monthly_returns(SP)
display(LIVE_MONTHLY.rename("live share price return").to_frame().T.round(4))
LIVE_DD = drawdown_table(SP, top=4)
display(LIVE_DD)
FLOWS = live_flows()
FLOW_SUMMARY = {"deposits_usd": float(FLOWS.loc[FLOWS["usd"] > 0, "usd"].sum()), "redemptions_usd": float(-FLOWS.loc[FLOWS["usd"] < 0, "usd"].sum()),
                "net_flow_usd": float(FLOWS["usd"].sum()), "flow_events": int(len(FLOWS)), "largest_deposit_usd": float(FLOWS["usd"].max()),
                "largest_deposit_date": str(FLOWS.loc[FLOWS["usd"].idxmax(), "t"].date())}
display(pd.Series(FLOW_SUMMARY, name="flows").to_frame())
peak_t = SP.idxmax()
LIVE_NOW = {"peak_date": str(peak_t.date()), "peak": float(SP.max()), "last": float(SP.iloc[-1]), "from_peak": float(SP.iloc[-1] / SP.max() - 1.0),
            "since_launch": float(SP.iloc[-1] / SP.iloc[0] - 1.0), "launch_price": float(SP.iloc[0]), "last_date": str(SP.index[-1].date())}
display(pd.Series(LIVE_NOW, name="live share price").to_frame())
'''))

cells.append(md("""## Part 2. The curves on the same dates

Rebased at the window start: the anchor's equity and the live share price. Window L is the whole
live period to the backtest's last day; window V is from the first two-day live decision (the
incumbent's logic live) to the backtest's last day; the live-only tail runs to the snapshot.
Volatility and Sharpe for both curves are computed on the anchor's two-day decision grid.
"""))
cells.append(code('''WINDOWS = {"L: live period": (LIVE_LAUNCH, BACKTEST_END), "V: incumbent logic live": (LIVE_2D_START, BACKTEST_END)}
CURVES = {}
for name, (a, b) in WINDOWS.items():
    rebased, stats = curve_comparison("anchor", a, b)
    CURVES[name] = stats
    curve_figure(rebased, f"{name}: anchor equity vs live share price, rebased at {a.date()}").show()
    display(stats.round(4))
tail = SP.loc[LIVE_2D_START:]
TAIL = {"start": str(tail.index[0].date()), "end": str(tail.index[-1].date()), "cumulative_return": float(tail.iloc[-1] / tail.iloc[0] - 1.0),
        "max_drawdown": float((tail / tail.cummax() - 1.0).min())}
display(pd.Series(TAIL, name="live only, 2-day cadence to snapshot").to_frame())
bt_daily = backtest_equity_daily("anchor")
BT_MONTHLY = monthly_returns(bt_daily.loc[LIVE_LAUNCH:])
display(pd.concat([BT_MONTHLY.rename("anchor"), LIVE_MONTHLY.rename("live")], axis=1).round(4).T)
BT_DD = drawdown_episodes("anchor", top=4)
display(BT_DD)
'''))

cells.append(md("""## Part 3. The books at each live decision

For every live decision from 2026-08-12: the vaults held live after the decision against the vaults
the anchor held after its decision on the same day (the last backtest decision at or before the
live one). Names held on one side only carry the anchor's reconstructed rank at that decision, or
"not in pool" (the momentum gate or the inclusion criteria removed it in the backtest) or "not in
backtest universe". Then the same at name level, counted by class, and the live cycle diagnostics
the executor wrote at each decision: candidate counts, cash, the allocation the size-risk model
discarded, and the signal flags.
"""))
cells.append(code('''OVERLAP = book_overlap("anchor", LIVE_2D_START, BACKTEST_END)
display(OVERLAP)
DIVERGENCE = name_level_divergence("anchor", LIVE_2D_START, BACKTEST_END)
DIV_COUNTS = DIVERGENCE.groupby("class").size().rename("decision-vault pairs").to_frame()
display(DIV_COUNTS)
DIV_BY_VAULT = DIVERGENCE.groupby(["side", "vault"]).size().rename("decisions").reset_index().sort_values(["side", "decisions"], ascending=[True, False])
display(DIV_BY_VAULT)
OVERLAP_SUMMARY = {"decisions": int(len(OVERLAP)), "mean_jaccard": float(OVERLAP["jaccard"].mean()), "median_jaccard": float(OVERLAP["jaccard"].median()),
                   "mean_live_n": float(OVERLAP["live_n"].mean()), "mean_backtest_n": float(OVERLAP["backtest_n"].mean()), "mean_both": float(OVERLAP["both"].mean())}
display(pd.Series(OVERLAP_SUMMARY, name="overlap").to_frame())
CYCLES = live_cycles()
CYC_V = CYCLES[CYCLES["t"] >= LIVE_2D_START].reset_index(drop=True)
show_cols = [c for c in ["t", "cycle", "positions", "trades_decided", "pairs_included", "candidates", "survivors", "equity", "cash", "discarded_liquidity_usd",
             "top_signal", "flag_capped_by_pool_size", "flag_capped_by_concentration", "flag_cannot_deposit", "flag_closed", "flag_close_weight_limit", "flag_trade_too_small"] if c in CYC_V.columns]
display(CYC_V[show_cols])
pool_sizes = [len(pool_at(t)) for t in _decision_timestamps("anchor") if pd.Timestamp(t) >= LIVE_2D_START]
CYCLE_SUMMARY = {"live_pairs_included_mean": float(CYC_V["pairs_included"].mean()), "live_candidates_mean": float(CYC_V["candidates"].mean()),
                 "backtest_pool_mean": float(np.mean(pool_sizes)), "live_discarded_liquidity_mean_usd": float(CYC_V["discarded_liquidity_usd"].mean()),
                 "live_decisions_with_discard": int((CYC_V["discarded_liquidity_usd"] > 0).sum()), "live_decisions": int(len(CYC_V)),
                 "live_equity_mean_usd": float(CYC_V["equity"].mean())}
display(pd.Series(CYCLE_SUMMARY, name="pools").to_frame())
'''))

cells.append(md("""## Part 4. Positions, churn and turnover

The live positions since the two-day cycle began, with the executor's own close reason (a position
closes when its signal is zero: the vault was not in the selected set at that decision). Beside
them, the anchor's positions over the same dates from NB41's ledger. Then the round trips - the
same vault sold in full and bought back within four days - on each side, and turnover per decision.
"""))
cells.append(code('''LIVE_POS = live_positions()
LIVE_V = LIVE_POS[(LIVE_POS["closed"].isna()) | (LIVE_POS["closed"] >= LIVE_2D_START)].copy()
LIVE_V = LIVE_V[LIVE_V["bought_usd"] > 0]
display(LIVE_V[["vault", "opened", "closed", "days", "bought_usd", "pnl_usd", "return_on_bought", "trades", "zero_value_trades", "close_reason"]].round(3))
CLOSE_REASONS = LIVE_V.groupby("close_reason").agg(positions=("position", "size"), pnl_usd=("pnl_usd", "sum")).round(0)
display(CLOSE_REASONS)
anchor_ledger = trade_ledger("anchor")
BT_V = anchor_ledger[(anchor_ledger["closed"].isna()) | (pd.to_datetime(anchor_ledger["closed"]) >= LIVE_2D_START)].copy()
BT_V = BT_V[pd.to_datetime(BT_V["opened"]) <= BACKTEST_END].sort_values("opened")
display(BT_V[["vault", "opened", "closed", "days", "pnl_usd", "peak_weight", "entry_rank", "pool_size", "exit_rank", "exit_reason"]].round(3))

def round_trips(frame: pd.DataFrame, opened_col: str, closed_col: str, max_gap_days: int = 4) -> pd.DataFrame:
    rows = []
    f = frame.dropna(subset=[closed_col]).copy()
    f[opened_col] = pd.to_datetime(f[opened_col]); f[closed_col] = pd.to_datetime(f[closed_col])
    for addr, g in frame.assign(**{opened_col: pd.to_datetime(frame[opened_col])}).groupby("address"):
        closes = f[f["address"] == addr].sort_values(closed_col)
        for _, c in closes.iterrows():
            reopen = g[(g[opened_col] > c[closed_col]) & (g[opened_col] <= c[closed_col] + pd.Timedelta(days=max_gap_days))]
            if not reopen.empty:
                rows.append({"vault": c["vault"], "closed": c[closed_col], "reopened": reopen[opened_col].min(), "gap_days": float((reopen[opened_col].min() - c[closed_col]).total_seconds() / 86400.0),
                             "closed_position_pnl": float(c["pnl_usd"])})
    return pd.DataFrame(rows)

LIVE_RT = round_trips(LIVE_V, "opened", "closed")
BT_RT = round_trips(BT_V, "opened", "closed")
print("live round trips (closed and re-bought within 4 days):"); display(LIVE_RT)
print("anchor round trips:"); display(BT_RT)
LIVE_TO = live_turnover(LIVE_2D_START, BACKTEST_END)
BT_TO = backtest_turnover("anchor", LIVE_2D_START, BACKTEST_END)
TURNOVER = {"live_mean_turnover_per_decision": float(LIVE_TO["turnover"].mean()), "backtest_mean_turnover_per_decision": float(BT_TO["turnover"].mean()),
            "live_decisions": int(len(LIVE_TO)), "backtest_decisions": int(len(BT_TO)),
            "live_round_trips": int(len(LIVE_RT)), "backtest_round_trips": int(len(BT_RT)),
            "live_positions_window": int(len(LIVE_V)), "backtest_positions_window": int(len(BT_V)),
            "live_zero_value_trades_window": int(LIVE_V["zero_value_trades"].sum())}
display(pd.Series(TURNOVER, name="turnover").to_frame())
display(LIVE_TO.round(3))
'''))

cells.append(md("""## Part 5. The same vaults, both sides

Net P&L per vault over the like-for-like window, live and backtest, for positions closed in or
open at the end of the window; the two live books hold roughly a quarter of the backtest's
capital, so the shape - sign and rank - is the comparison, not the dollar amount. Then the
vaults' own paths with both sides' held intervals for the largest differences.
"""))
cells.append(code('''PER_VAULT = per_vault_pnl("anchor", LIVE_2D_START, BACKTEST_END)
display(PER_VAULT.round(0))
SIGN = PER_VAULT[(PER_VAULT["live_positions"] > 0) & (PER_VAULT["backtest_positions"] > 0)]
SIGN_SUMMARY = {"vaults_on_both_sides": int(len(SIGN)), "same_sign": int((np.sign(SIGN["live_pnl"]) == np.sign(SIGN["backtest_pnl"])).sum()),
                "live_only_vaults": int(((PER_VAULT["live_positions"] > 0) & (PER_VAULT["backtest_positions"] == 0)).sum()),
                "backtest_only_vaults": int(((PER_VAULT["live_positions"] == 0) & (PER_VAULT["backtest_positions"] > 0)).sum()),
                "live_net_pnl_window": float(PER_VAULT["live_pnl"].sum()), "backtest_net_pnl_window": float(PER_VAULT["backtest_pnl"].sum())}
display(pd.Series(SIGN_SUMMARY, name="per vault").to_frame())

def both_sides_figure(address: str) -> go.Figure:
    fig = vault_figure(address, ["anchor"], start=LIVE_2D_START - pd.Timedelta(days=30), end=SP.index[-1])
    for _, p in LIVE_POS[LIVE_POS["address"] == address].iterrows():
        if p["bought_usd"] <= 0:
            continue
        b = p["closed"] if p["closed"] is not None and not pd.isna(p["closed"]) else SP.index[-1]
        fig.add_vrect(x0=p["opened"], x1=b, fillcolor="rgba(255,127,14,0.18)", line_width=0,
                      annotation_text=f"live {p['pnl_usd']:+,.0f}", annotation_position="bottom left", annotation_font_size=10)
    fig.update_layout(title=f"{vault_name(address)}: anchor held intervals (blue) and live positions (orange)")
    return fig

PER_VAULT["abs_gap"] = (PER_VAULT["live_pnl"] / max(CYCLE_SUMMARY["live_equity_mean_usd"], 1.0) - PER_VAULT["backtest_pnl"] / float(run_by_label["anchor"]["equity"].loc[LIVE_2D_START:].mean())).abs()
for addr in PER_VAULT.sort_values("abs_gap", ascending=False)["address"].head(6):
    if addr in PAIR_BY_ADDRESS:
        both_sides_figure(addr).show()
'''))

cells.append(md("""### 5b. The current drawdown, both sides

The live share price peaked on 2026-08-27 and the anchor's last drawdown starts on the same day.
P&L change per vault from the 27 Aug peak to the backtest's last day, each side as a share of its
own equity at the peak, and the held weights after each live decision in the drawdown beside the
anchor's weights after its decision on the same day.
"""))
cells.append(code('''DD_START, DD_END = pd.Timestamp("2026-08-27"), BACKTEST_END
DD_ATTRIB = pnl_change_both_sides("anchor", DD_START, DD_END)
display(DD_ATTRIB.round(4))
WEIGHTS = {}
for t in CYC_V.loc[(CYC_V["t"] >= DD_START) & (CYC_V["t"] <= DD_END), "t"]:
    w = weights_both_sides("anchor", t)
    WEIGHTS[str(t)] = w
    print(f"live decision {t} (backtest decision {backtest_decision_at_or_before('anchor', t).date()})")
    display(w.round(3))
WEIGHT_SUMMARY = {"live_max_weight_mean": float(np.mean([w["live_weight"].max() for w in WEIGHTS.values()])),
                  "backtest_max_weight_mean": float(np.mean([w["backtest_weight"].max() for w in WEIGHTS.values()])),
                  "live_top2_weight_mean": float(np.mean([w["live_weight"].nlargest(2).sum() for w in WEIGHTS.values()])),
                  "backtest_top2_weight_mean": float(np.mean([w["backtest_weight"].nlargest(2).sum() for w in WEIGHTS.values()])),
                  "live_names_mean": float(np.mean([(w["live_weight"] > 0).sum() for w in WEIGHTS.values()])),
                  "backtest_names_mean": float(np.mean([(w["backtest_weight"] > 0).sum() for w in WEIGHTS.values()]))}
display(pd.Series(WEIGHT_SUMMARY, name="weights in the drawdown").to_frame())
'''))

cells.append(md("""## Part 6. When the fills happened

The backtest fills at the UTC day's open (NB42: the two collapse sells filled at the unmoved open).
The live executor decides at a drifting hour and fills minutes later. For every live fill with
value in the like-for-like window: the vault's own mark at the day's first archive mark and at
the last mark before execution, the move between them, and the USD the live fill gained (+) or
lost (-) against filling at the day's first mark. Sells and buys are summed separately.
"""))
cells.append(code('''FILLS = fill_timing(LIVE_2D_START, SP.index[-1])
display(FILLS[["executed_at", "vault", "side", "usd", "day_open", "at_fill", "move", "usd_vs_day_open", "marks_before_fill"]].round(4))
FILL_SUMMARY = FILLS.groupby("side").agg(fills=("usd", "size"), usd=("usd", "sum"), usd_vs_day_open=("usd_vs_day_open", "sum"),
                                         mean_move=("move", "mean"), unmeasured=("day_open", lambda s: int(s.isna().sum())))
display(FILL_SUMMARY.round(4))
FILL_TOTAL = {"usd_vs_day_open_total": float(FILLS["usd_vs_day_open"].sum()), "fills": int(len(FILLS)), "unmeasured": int(FILLS["day_open"].isna().sum()),
              "hours_utc_min": float(FILLS["executed_at"].dt.hour.min()), "hours_utc_max": float(FILLS["executed_at"].dt.hour.max()),
              "worst_sell": jsonable(FILLS[FILLS["side"] == "sell"].sort_values("usd_vs_day_open").head(1)[["executed_at", "vault", "usd", "move", "usd_vs_day_open"]].to_dict(orient="records"))}
display(pd.Series(FILL_TOTAL, name="fill timing").to_frame())
'''))

cells.append(md("""## Part 7. Manifest
"""))
cells.append(code('''manifest = {
    "provenance": provenance_record(),
    "live_state": {"url": LIVE_STATE_URL, "snapshot": LIVE_STATE_DATE, "path": str(LIVE_STATE_PATH)},
    "facts": jsonable(FACTS.to_dict()), "version_timeline": jsonable(VERSION_TIMELINE.to_dict(orient="records")),
    "cadence": jsonable(CADENCE.reset_index().astype(str).to_dict(orient="records")),
    "live_monthly": jsonable({str(k.date()): v for k, v in LIVE_MONTHLY.items()}), "backtest_monthly": jsonable({str(k.date()): v for k, v in BT_MONTHLY.items()}),
    "live_drawdowns": jsonable(LIVE_DD.to_dict(orient="records")), "backtest_drawdowns": jsonable(BT_DD.to_dict(orient="records")),
    "flows": FLOW_SUMMARY, "live_now": LIVE_NOW,
    "curves": {k: jsonable(v.to_dict()) for k, v in CURVES.items()}, "tail": TAIL,
    "overlap": jsonable(OVERLAP.to_dict(orient="records")), "overlap_summary": OVERLAP_SUMMARY,
    "divergence_counts": jsonable(DIV_COUNTS["decision-vault pairs"].to_dict()), "divergence_by_vault": jsonable(DIV_BY_VAULT.to_dict(orient="records")),
    "cycles": jsonable(CYC_V[show_cols].to_dict(orient="records")), "cycle_summary": CYCLE_SUMMARY,
    "live_positions": jsonable(LIVE_V.to_dict(orient="records")), "backtest_positions": jsonable(BT_V[["vault", "address", "opened", "closed", "days", "pnl_usd", "peak_weight", "entry_rank", "exit_reason"]].to_dict(orient="records")),
    "close_reasons": jsonable(CLOSE_REASONS.to_dict(orient="index")),
    "live_round_trips": jsonable(LIVE_RT.to_dict(orient="records")), "backtest_round_trips": jsonable(BT_RT.to_dict(orient="records")),
    "turnover": TURNOVER, "per_vault": jsonable(PER_VAULT.to_dict(orient="records")), "sign_summary": SIGN_SUMMARY,
    "dd_attribution": jsonable(DD_ATTRIB.reset_index().to_dict(orient="records")), "weights": {k: jsonable(v.to_dict(orient="records")) for k, v in WEIGHTS.items()}, "weight_summary": WEIGHT_SUMMARY,
    "fills": jsonable(FILLS.to_dict(orient="records")), "fill_summary": jsonable(FILL_SUMMARY.to_dict(orient="index")), "fill_total": FILL_TOTAL,
}
Path("_build/manifest_43.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_43.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "43-research-live-vs-backtest.ipynb")
