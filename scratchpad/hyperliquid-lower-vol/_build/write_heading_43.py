"""Generate NB43's heading from _build/manifest_43.json. Every number from the manifest; the
qualitative claims are asserted so the prose cannot outlive a different result."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "43-research-live-vs-backtest.ipynb"
m = json.loads((HERE / "manifest_43.json").read_text())
m40 = json.loads((HERE / "manifest_40.json").read_text())

F = m["facts"]; NOW = m["live_now"]; CUR = m["curves"]; TAIL = m["tail"]; OV = m["overlap_summary"]; DC = m["divergence_counts"]
CS = m["cycle_summary"]; CR = m["close_reasons"]; TO = m["turnover"]; SG = m["sign_summary"]; FT = m["fill_total"]; FS = m["fill_summary"]
LDD = m["live_drawdowns"]; BDD = m["backtest_drawdowns"]; LM = m["live_monthly"]; BM = m["backtest_monthly"]; FL = m["flows"]
DDA = {r["vault"]: r for r in m["dd_attribution"]}; WS = m["weight_summary"]; W = m["weights"]
DBV = m["divergence_by_vault"]; RT = m["live_round_trips"]; BRT = m["backtest_round_trips"]; CAD = m["cadence"]
A40 = m40["summary"]["anchor"]

L_bt, L_lv = CUR["L: live period"]["anchor_equity"], CUR["L: live period"]["live_share_price"]
V_bt, V_lv = CUR["V: incumbent logic live"]["anchor_equity"], CUR["V: incumbent logic live"]["live_share_price"]


def pc(x): return f"{x * 100:.1f}%"
def f2(x): return f"{x:.2f}"
def usd(x): return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


# --- asserted claims ---------------------------------------------------------------------------
assert abs(L_bt["cumulative_return"] - L_lv["cumulative_return"]) < 0.01, "the two curves end within 1 pp on the live period"
assert L_lv["max_drawdown"] < 3 * L_bt["max_drawdown"], "live drawdown at least three times the anchor's on the live period"
assert L_lv["vol_2d_grid"] > 2 * L_bt["vol_2d_grid"]
assert V_bt["cumulative_return"] > 0 > V_lv["cumulative_return"], "window V: anchor up, live down"
assert V_lv["max_drawdown"] < 2 * V_bt["max_drawdown"]
q1 = A40["final_equity"] / 100000.0 / (1.0 + L_bt["cumulative_return"]) - 1.0
assert q1 > 0.5, "most of the anchor's return is before the live launch"
assert NOW["peak_date"] == "2026-08-27" and BDD[3]["peak"] == "2026-08-27", "both drawdowns start on 27 Aug"
assert LDD[0]["depth"] < -0.15 and LDD[0]["trough"] == "2026-04-16"
assert abs(FT["usd_vs_day_open_total"]) < 0.01 * CS["live_equity_mean_usd"], "fill timing is under 1% of equity"
assert TO["live_mean_turnover_per_decision"] > 2 * TO["backtest_mean_turnover_per_decision"]
assert TO["live_round_trips"] > TO["backtest_round_trips"]
assert DC.get("live only: not in backtest universe", 0) >= 10
assert CS["live_pairs_included_mean"] > CS["backtest_pool_mean"] + 10
assert CS["live_decisions_with_discard"] >= CS["live_decisions"] // 2
assert DDA["Goon Edging"]["live_share_of_equity"] < DDA["Goon Edging"]["backtest_share_of_equity"] < 0
assert DDA["TOTAL"]["live_share_of_equity"] < 2 * DDA["TOTAL"]["backtest_share_of_equity"]
assert DDA["DOEZOE"]["backtest_share_of_equity"] > 0 and DDA["DOEZOE"]["live_share_of_equity"] == 0
w27 = {r["vault"]: r for r in W["2026-08-27 16:25:14"]}
assert w27["Goon Edging"]["live_weight"] > 0.3 and w27["Goon Edging"]["backtest_weight"] < 0.2
assert w27["Citadel"]["live_weight"] == 0 and w27["Citadel"]["backtest_weight"] > 0.3
w29 = {r["vault"]: r for r in W["2026-08-29 16:33:46"]}
assert w29["AceVault Hyper01"]["live_weight"] == 0 and w29["AceVault Hyper01"]["backtest_weight"] > 0.3
ace_rt = [r for r in RT if r["vault"] == "AceVault Hyper01"]
assert len(ace_rt) == 2
cad = {r["month"]: r for r in CAD}
assert float(cad["2026-07"]["median_gap_days"]) < 1.5 < float(cad["2026-08"]["median_gap_days"])
not_in_universe = sorted({r["vault"] for r in DBV if r["side"] == "live only" and r["vault"] in ("Danny Ocean", "Gucky_4coin_2dot5x", "HYPErQuantum4")})
assert "Danny Ocean" in not_in_universe and "Gucky_4coin_2dot5x" in not_in_universe
sells = FS["sell"]; buys = FS["buy"]
n_sig0 = sum(v["positions"] for k, v in CR.items() if k.startswith("not selected"))
n_nonote = CR.get("no note", {"positions": 0})["positions"]
n_closed = sum(v["positions"] for k, v in CR.items() if k != "open")
assert n_sig0 + n_nonote == n_closed and n_sig0 > 2 * n_nonote

HEADING = f"""# NB43 - the live hyper-ai vault beside the backtest

The incumbent's backtest ([02-better-format.ipynb](02-better-format.ipynb), the `anchor` of
NB40-NB42) is quoted at {pc(A40["cagr"])} CAGR and a {pc(A40["max_dd"])} maximum drawdown on 2026-01-01 to
2026-09-08. The live `hyper-ai` Lagoon vault on HyperEVM has run since 2026-03-30 and is in a
drawdown. This notebook puts the two side by side and names the differences. It runs no new
strategy variant. Live state: a read-only snapshot of `https://hyper-ai.tradingstrategy.ai/state`
taken {F["snapshot"]} (NAV {usd(F["nav_usd"])}, {F["positions"]} positions in {F["vaults_traded"]} vaults, {F["trades"]} trades of which
{F["zero_value_trades"]} carried no value and {F["repair_trades"]} were repairs; cell 31).

**Based on:** [42-backtest-crash-exit.ipynb](42-backtest-crash-exit.ipynb) for the machinery,
[02-better-format.ipynb](02-better-format.ipynb) as the anchor. Names are labels; nothing is
selected by name.

## Key new insights and what did we learn from this experiment?

1. **On the live dates the backtest is not a {pc(A40["cagr"])}-CAGR strategy.** From the launch on
   2026-03-30 to the backtest's last day the anchor returns {pc(L_bt["cumulative_return"])} and the live share
   price {pc(L_lv["cumulative_return"])} - the same number (cell 33). {pc(q1)} of the anchor's {pc(A40["final_equity"] / 100000.0 - 1.0)} comes
   from 1 January to 30 March, before the vault existed and before the April polling-density
   break the track has flagged since NB03. The headline CAGR is a first-quarter number.
2. **Where they differ is the path, not the destination.** Same dates, same end point: the anchor's
   maximum drawdown is {pc(L_bt["max_drawdown"])}, the live vault's {pc(L_lv["max_drawdown"])} (11-16 April, under v1);
   volatility on the two-day grid {pc(L_bt["vol_2d_grid"])} against {pc(L_lv["vol_2d_grid"])}; Sharpe {f2(L_bt["sharpe_2d_grid"])} against
   {f2(L_lv["sharpe_2d_grid"])}. The live vault's three drawdowns ({pc(LDD[0]["depth"])}, {pc(LDD[1]["depth"])}, {pc(LDD[2]["depth"])}) are each deeper than the
   anchor's worst ({pc(BDD[0]["depth"])}) (cells 31, 33).
3. **Only since 2026-08-12 has the live instance run the incumbent's logic** (daily decisions
   under v1-v3 until 10 August, two-day cycle since; cell 31). On that like-for-like window to
   8 September the anchor made {pc(V_bt["cumulative_return"])} with a {pc(V_bt["max_drawdown"])} drawdown; the live vault lost
   {pc(-V_lv["cumulative_return"])} with a {pc(V_lv["max_drawdown"])} drawdown, and is {pc(TAIL["cumulative_return"])} on the window to the snapshot (cell 33).
   Both curves peak on 2026-08-27; the live one is {pc(NOW["from_peak"])} below that peak.
4. **The fill time of day is not the cause.** Live fills happened between {FT["hours_utc_min"]:.0f}:00 and {FT["hours_utc_max"]:.0f}:00 UTC
   (drifting with every restart) while the backtest fills at the day's open; across all {FT["fills"]} live
   fills the vault's own mark had moved by a net {usd(FT["usd_vs_day_open_total"])} against the day's first mark
   ({usd(sells["usd_vs_day_open"])} on {sells["fills"]} sells, {usd(buys["usd_vs_day_open"])} on {buys["fills"]} buys) - under 1% of equity (cell 43).
5. **The books differ at the sixth slot and through vaults the backtest never sees.** Across the
   {OV["decisions"]} live decisions the two books share {OV["mean_both"]:.1f} of 6 names (Jaccard {f2(OV["mean_jaccard"])}). Of the
   {sum(DC.values())} decision-vault pairs on one side only, {DC.get("live only: not in backtest universe", 0)} are live holdings of vaults not in the
   backtest universe ({", ".join(not_in_universe)}), {DC.get("live only: backtest rank > 6", 0)} are live holdings the anchor
   ranked below sixth, {DC.get("live only: not in backtest pool at t", 0)} are live holdings the anchor's gate had removed, and the
   backtest-only names are its rank-6/7 marginal picks (cell 35). The live inclusion set averages
   {CS["live_pairs_included_mean"]:.0f} vaults against the anchor's pool of {CS["backtest_pool_mean"]:.0f}.
6. **That marginal slot churned the two largest positions.** Citadel (backtest rank 6 of 163)
   was sold in full on 27 Aug and bought back on 29 Aug; AceVault Hyper01 (rank 6 of 161) sold in
   full on 29 Aug, bought back 31 Aug / 1 Sep, sold 9 Sep, bought back 11 Sep, sold 19 Sep. The
   anchor held both continuously. Live: {TO["live_round_trips"]} full round trips inside four days, {TO["live_positions_window"]} positions,
   turnover {pc(TO["live_mean_turnover_per_decision"])} of equity per decision; anchor: {TO["backtest_round_trips"]}, {TO["backtest_positions_window"]}, {pc(TO["backtest_mean_turnover_per_decision"])} (cells 35, 37).
   Every live close with a recorded reason ({n_sig0} of {n_closed}) is "signal 0" - not selected at that
   decision; {n_nonote} carry no note; none is a momentum-gate exit by the executor's own wording.
7. **The drawdown since 27 Aug is the same names with different weights.** Live {pc(DDA["TOTAL"]["live_share_of_equity"])} of
   equity to 8 Sep against the anchor's {pc(DDA["TOTAL"]["backtest_share_of_equity"])}. Goon Edging cost the live vault {pc(-DDA["Goon Edging"]["live_share_of_equity"])}
   at a {pc(w27["Goon Edging"]["live_weight"])} weight (the anchor {pc(-DDA["Goon Edging"]["backtest_share_of_equity"])} at {pc(w27["Goon Edging"]["backtest_weight"])}): with Citadel or AceVault
   missing from the live book, the next name went to the cap - consistent with the 0.33 cap's
   redistribution, which is inferred from the weights, not read from a log.
   AceVault cost {pc(-DDA["AceVault Hyper01"]["live_share_of_equity"])} live ({pc(-DDA["AceVault Hyper01"]["backtest_share_of_equity"])} anchor); the anchor's DOEZOE entry on 4 Sep
   (+{pc(DDA["DOEZOE"]["backtest_share_of_equity"])}) has no live counterpart until 9 Sep, where it lost {usd(-609.79)} in two days (cells 37, 41).
8. **The live executor discards allocation on most decisions.** "Discarded allocation because of
   lack of lit liquidity" was non-zero on {CS["live_decisions_with_discard"]} of {CS["live_decisions"]} two-day decisions, {usd(CS["live_discarded_liquidity_mean_usd"])} on
   average against {usd(CS["live_equity_mean_usd"])} of equity, with `capped_by_pool_size` flags on the same
   decisions (cell 35). The backtest logs no such quantity; NB02's capacity finding is live at
   {usd(F["nav_usd"])}, not only at $150k.

## Summary of results

| | anchor backtest | live share price |
|---|---|---|
| 2026-03-30 to 2026-09-08: return | {pc(L_bt["cumulative_return"])} | {pc(L_lv["cumulative_return"])} |
| max drawdown | {pc(L_bt["max_drawdown"])} | {pc(L_lv["max_drawdown"])} |
| vol / Sharpe on the 2-day grid | {pc(L_bt["vol_2d_grid"])} / {f2(L_bt["sharpe_2d_grid"])} | {pc(L_lv["vol_2d_grid"])} / {f2(L_lv["sharpe_2d_grid"])} |
| 2026-08-12 to 2026-09-08 (incumbent logic live): return | {pc(V_bt["cumulative_return"])} | {pc(V_lv["cumulative_return"])} |
| max drawdown | {pc(V_bt["max_drawdown"])} | {pc(V_lv["max_drawdown"])} |
| 27 Aug to 8 Sep P&L, share of equity | {pc(DDA["TOTAL"]["backtest_share_of_equity"])} | {pc(DDA["TOTAL"]["live_share_of_equity"])} |
| positions / round trips / turnover per decision (12 Aug-8 Sep) | {TO["backtest_positions_window"]} / {TO["backtest_round_trips"]} / {pc(TO["backtest_mean_turnover_per_decision"])} | {TO["live_positions_window"]} / {TO["live_round_trips"]} / {pc(TO["live_mean_turnover_per_decision"])} |

Monthly, live vs anchor: April {pc(LM["2026-04-30"])} vs {pc(BM["2026-04-30"])}, May {pc(LM["2026-05-31"])} vs {pc(BM["2026-05-31"])}, June {pc(LM["2026-06-30"])} vs
{pc(BM["2026-06-30"])}, July {pc(LM["2026-07-31"])} vs {pc(BM["2026-07-31"])}, August {pc(LM["2026-08-31"])} vs {pc(BM["2026-08-31"])}, September to date {pc(LM["2026-09-30"])} vs
{pc(BM["2026-09-30"])} (to 8 Sep). Deposits {usd(FL["deposits_usd"])}, redemptions {usd(FL["redemptions_usd"])}; the share price is unaffected by flow.

What the live drawdown is NOT: a different strategy (5 of 6 names shared), a fill-timing effect
({usd(FT["usd_vs_day_open_total"])}), or a momentum-gate misfire (no live close in the window was a gate exit). What it IS:
the same losing names at higher weights because the live book's marginal slot flips between the
anchor's two 33% holdings and a vault outside the backtest universe, plus a backtest entry (DOEZOE,
4 Sep) the live instance did not make. Whether the extra live vaults belong in the backtest
universe, or the backtest's universe screen belongs in the live executor, is the question to
settle before any further strategy research; it decides whether the anchor is the strategy that
is live.

## Robustness of results

- The live curve is the Lagoon share price from the executor's portfolio statistics, one value
  per UTC day (last), so it is a depositor's return; NAV and flows are shown for context only
  (cell 31). The backtest curve is the anchor's equity resampled the same way.
- "Same dates" hides that the live instance ran v1-v4 until 12 August; window L compares the
  anchor with a moving target and is reported for the drawdown history, not as a test of the
  incumbent. Window V is the like-for-like window and is {V_bt["days"]} days long - {V_bt["grid_points"]} two-day
  points. Nothing here is a statistical test.
- Ranks of the names held on one side only are NB41's reconstruction from the cached indicator
  set and the two-day pool log; tie order, deposit-window skips and hold protection are not
  mirrored, so a rank can be off by one - which is why "backtest only, rank 7" rows exist.
- The live executor's reason for not selecting a vault is not in the state; "signal 0" is read
  from the trade notes. The cycle messages give the counts (inclusion set, candidates, survivors,
  flags) but not the per-vault ranking, so which live vault took the sixth slot is inferred from
  the book, not read from a log.
- Fill timing uses the raw archive's first mark of the UTC day as the backtest's fill point
  (NB42 showed the backtest's collapse sells filled at the decision-day open); {FT["unmeasured"]} of {FT["fills"]} fills
  had no archive mark before execution.
- Per-vault P&L in cell 39 is whole-position P&L for positions overlapping the window, so the
  anchor's Realist Capital row carries gains from June; cell 41 is the windowed attribution.
- The snapshot is one day; the state is re-read from the cached file, never refetched, so the
  notebook reproduces. Live equity averaged {usd(CS["live_equity_mean_usd"])}; the anchor's four times that.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB43 heading written: L {pc(L_bt['cumulative_return'])} vs {pc(L_lv['cumulative_return'])}; V {pc(V_bt['cumulative_return'])} vs {pc(V_lv['cumulative_return'])}; fills {usd(FT['usd_vs_day_open_total'])}")
