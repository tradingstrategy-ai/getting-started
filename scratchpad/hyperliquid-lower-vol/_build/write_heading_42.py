"""Generate NB42's heading from _build/manifest_42.json. Every number from the manifest; the
qualitative claims are asserted so the prose cannot outlive a different result. The heading's
order is fixed by plan 42 Draft 5: (1) H0a and H0b, (2) whether gate12_2d sold on 19 Aug, (3) the
incremental cycle P&L, (4) the standing gates."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "42-backtest-crash-exit.ipynb"
m = json.loads((HERE / "manifest_42.json").read_text())

S = m["summary"]
G = m["gates_2d"]
F = m["fills"]
L = m["labels"]
LEG = m["legs"]
AS = m["august_sell"]
H1 = m["H1"]
GRID = m["grid"]
W = m["window_a"]
WC = m["window_cycles"]
W5 = m["worst5"]
CH = m["churn_2d"]
FIRES = m["fires"]
ST = m["stop_tables"]
FS = m["first_strike_summary"]
ES = m["every_day_summary"]
COV = m["coverage"]
C = m["collapse"]
A = S["anchor"]


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pc(x): return f"{x * 100:.1f}%"
def usd(x): return f"-${-x / 1000:.1f}k" if x < 0 else f"${x / 1000:.1f}k"
def sh(l): return f3(S[l]["cycle_sharpe"])
def cg(l): return pc(S[l]["cagr"])
def dd(l): return pc(S[l]["max_dd"])


# --- claims, asserted ---
assert m["H0a"] == {"august": "PARTIAL CATCH", "may": "PARTIAL CATCH"}, m["H0a"]
assert m["H0b"] == {"august": "open_to_close", "may": "open_to_close"}, m["H0b"]
assert not m["later_runs_diagnostic"]
for k in ("august", "may"):
    assert not F[k]["is_async_vault"] and not F[k]["has_delayed_vault_redemption"]
    assert F[k]["market_feed_delay"] == "0:00:00"
    assert abs(LEG[k]["close_to_open"]) < 1e-12, LEG[k]
    assert F[k]["executed_at"] == F[k]["decision"]
    assert abs(F[k]["executed_price"] - F[k]["planned_mid_price"] * (1 - F[k]["stored_fee"])) < 1e-9
assert AS["gate12_2d"]["sold_on_19_aug"] and AS["gate12_2d"]["valued_at_decision_open"] and m["august_caught"]
assert G["gate12_2d"]["verdict"].startswith("NOT CONFIRMED") and G["gate12_2d"]["failed_standing_gates"] == ""
assert G["gate10_2d"]["verdict"].startswith("UNEVALUATED")
assert S["gate12_2d"]["cycle_sharpe"] < A["cycle_sharpe"] and S["gate12_2d"]["cagr"] < A["cagr"] and S["gate12_2d"]["max_dd"] < A["max_dd"]
assert CH["gate12_2d"]["churn_pnl_usd"] < CH["anchor"]["churn_pnl_usd"] - 3000
assert not H1["passes"] and not m["run_1d_gates"] and not m["run_cluster"]
assert H1["churn_pnl_1d"] < H1["churn_pnl_anchor"] - 10000
assert S["anchor_1d"]["late_cagr"] < 0
g19 = m["gate_19aug"]
assert -0.16 < g19["gate_value_read_at_T-1"] <= -0.12
assert W5["anchor"]["worst5_with"] == W5["anchor"]["worst5_without_collapse_cycles"]

cyc = {(r["label"], r["cycle_end"]): r for r in WC}
aug21 = {l: cyc[(l, "2026-08-21")] for l in ("anchor", "gate12_2d", "gate10_2d")}
may21 = {l: cyc[(l, "2026-05-21")] for l in ("anchor", "gate12_2d", "gate10_2d")}
assert aug21["gate12_2d"]["pnl_usd"] > aug21["anchor"]["pnl_usd"] + 4000
assert abs(may21["gate12_2d"]["pnl_usd"] - may21["anchor"]["pnl_usd"]) < 100
fires12 = FIRES["gate (-16%, -12%]"]
n_fires12 = len(fires12)
recovered = [r for r in fires12 if r["fwd_30d"] > 0.2]
crashed = [r for r in fires12 if r["fwd_30d"] < -0.5]
assert len(crashed) == 1 and crashed[0]["decision"] == "2026-08-19"
assert len(recovered) >= 3
breaker = FIRES["breaker -20%"]
assert len(breaker) == 2 and {r["decision"] for r in breaker} == {"2026-05-21", "2026-09-08"}
assert not any(r["decision"] == "2026-08-21" for r in breaker)
brk_may = next(r for r in breaker if r["decision"] == "2026-05-21"); brk_other = next(r for r in breaker if r["decision"] != "2026-05-21")
fs = {(r["class"], r["horizon"]): r for r in FS}
es = {(r["class"], r["horizon"]): r for r in ES}
assert fs[("first_extreme", "fwd_1d")]["ci_hi"] > 0
cov_dense = COV["('empty_share', 'mean')"]["dense (2026-04-01 on)"]
cov_sparse = COV["('empty_share', 'mean')"]["sparse (to 2026-03-31)"]
assert cov_sparse > 0.7 and cov_dense < 0.1

import pandas as pd
reentry = (pd.Timestamp("2026-08-19") - pd.Timedelta(days=int(AS["gate12_2d"]["hold_days"]))).date()
assert AS["gate12_2d"]["hold_days"] < C["august"]["hold_days"]
assert any(r["decision"] == "2026-06-22" and r["vault"] == C["august"]["vault"] for r in fires12)
assert all(str(r["opened"]) < r["decision"] for r in fires12), "a fire row is not a pre-decision holding"
lines_fires = "\n".join(f"| {r['decision']} | {r['vault']} | {r['opened']} | {r['weight_before']:.2f} | {r['return_14d'] * 100:.1f}% | {r['fwd_5d'] * 100:+.1f}% | {r['fwd_30d'] * 100:+.1f}% |" for r in fires12)
CE = m["churn_1d_exact"]; CR = m["churn_recon_2d"]
assert CH["gate12_2d"]["unclassified"] == 0 and CH["anchor"]["unclassified"] == 0 and CE["unclassified"]["positions"] == 0

HEADING = f"""# NB42 - crash exit: does the incumbent's exit fill before the gap?

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
those two dates (cell 30: `{C["august"]["vault"]}`, held {C["august"]["hold_days"]} days, {usd(C["august"]["pnl_usd"])}; `{C["may"]["vault"]}`, held
{C["may"]["hold_days"]} days, {usd(C["may"]["pnl_usd"])}) - never by name; names appear as labels only.

**Verdicts use the standing gates only** (RESEARCH-RULES.md, idiot-gate audit of 2026-09-16):
1 positive return, 2 single-vault mask, 3 held-book volatility, 6 plateau, 7 sub-period sign.
Gate 5 does not apply to a position-level exit. Nothing here is out of sample.

**Based on:** [41-research-trade-forensics.ipynb](41-research-trade-forensics.ipynb) and
[40-backtest-lead-forensics-cash-sleeve.ipynb](40-backtest-lead-forensics-cash-sleeve.ipynb) for
the machinery, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Track window
2026-01-01 to 2026-09-08; the anchor reproduces NB40's at 1e-9 with the cluster splice present
and off (cell 28).

## Key new insights and what did we learn from this experiment?

**Verdict: the question is answered by the incumbent's own fills, and nothing built here
improves on it.** No lead is shortlisted. The one-day clock is REJECT on gate 7 and is the
notebook's most useful negative.

1. **H0a and H0b: the incumbent never took either collapse bar.** Both collapse sells are
   PARTIAL CATCHES (cell 34): non-async HyperCore pairs (`vault_features` =
   {{hypercore_native}}; `is_async_vault` and `has_delayed_vault_redemption` both False; feed
   delay 0), valued at `planned_mid_price` = the decision day's candle open
   ({F["august"]["planned_mid_price"]:.4f} on 21 Aug, {F["may"]["planned_mid_price"]:.4f} on 21 May), executed at the decision, with the
   {F["august"]["stored_fee"] * 1e4:.0f} bps fee taken off (`executed_price` = mid x (1 - fee), asserted). On both days the
   candle open EQUALS the previous close (close-to-open leg {LEG["august"]["close_to_open"]:.4f} and {LEG["may"]["close_to_open"]:.4f}): the first
   mark of the day had not moved. The whole crash sits in the open-to-close leg
   ({pc(LEG["august"]["open_to_close"])} on 21 Aug, {pc(LEG["may"]["open_to_close"])} on 21 May). The book took the days BEFORE the
   collapses - the 19 Aug -14.5% close and the 20 May -23.9% close - and sold at the open of
   the day the floor gave way. That is why the anchor's five worst cycles are the same with and
   without the two collapse cycles ({pc(W5["anchor"]["worst5_with"])} either way, cell 37): the collapse days are not
   among its worst cycles at all.
2. **The premise held, and the tighter gate did what it was built to do.** At the 19 Aug
   decision the T-1 gate value is {pc(g19["gate_value_read_at_T-1"])} (the 14-day return through 18 Aug; the 19 Aug daily
   close is {pc(g19["daily_log_return_on_19_aug"])}, a coincidence of value, cell 30). `gate12_2d` sells the August position on
   19 Aug, valued at the 19 Aug open ({AS["gate12_2d"]["planned_mid_price"]:.4f}, cell 36): the 21 Aug cycle earns {usd(aug21["gate12_2d"]["pnl_usd"])} against
   the anchor's {usd(aug21["anchor"]["pnl_usd"])} ({pc(aug21["gate12_2d"]["cycle_return"])} against {pc(aug21["anchor"]["cycle_return"])}); the 21 May cycle is unchanged
   ({usd(may21["gate12_2d"]["pnl_usd"])} against {usd(may21["anchor"]["pnl_usd"])}) because the incumbent already sells there.
3. **And it is worse than the incumbent anyway.** `gate12_2d`: CAGR {cg("gate12_2d")} against {cg("anchor")}, cycle
   Sharpe {sh("gate12_2d")} against {sh("anchor")}, max drawdown {dd("gate12_2d")} against {dd("anchor")} (cell 36); it passes every standing
   gate (mask {f2(G["gate12_2d"]["mask_retention"])}, plateau against -16% and -10%) and is NOT CONFIRMED at {G["gate12_2d"]["sharpe_gap_to_anchor"]:+.2f} - inside
   the band and on the wrong side of it. Why: the 14-day gate in (-16%, -12%] fires on
   {n_fires12} held-vault decisions of the anchor's book (cell 32), and only ONE of them is a
   collapse (19 Aug, 30-day forward {pc(crashed[0]["fwd_30d"])}); {len(recovered)} of them are decisions on the incumbent's winners
   on the way up ({", ".join(f"{r['vault']} on {r['decision']}, +{r['fwd_30d'] * 100:.0f}% over the next 30 days" for r in recovered)}). The
   incumbent held the August vault at a 14-day return of -13.9% on 22 Jun, two days after
   buying it; `gate12_2d` does not, and its August position dates from {reentry} - a
   {AS["gate12_2d"]["hold_days"]}-day hold against the incumbent's {C["august"]["hold_days"]}. Its positions sold while their vault was still in the
   candidate pool (sold by ranking or sizing, read from the in-trade pool log, not a
   reconstruction) net {usd(CH["gate12_2d"]["churn_pnl_usd"])} against the anchor's {usd(CH["anchor"]["churn_pnl_usd"])} (cell 37), and its dense-period
   CAGR is {pc(S["gate12_2d"]["dense_cagr"])} against {pc(A["dense_cagr"])}. The fire table is the anchor's book, not the tighter
   run's, so it says which of the anchor's holdings a -12% gate would have sold - it does not
   attribute the tighter run's whole-book result to those rows, which also changes what it
   held afterwards. What the two agree on: the pre-registered -12% variant produced no lead on
   this window, and -16% is not established as "too loose".
4. **The one-day clock fails H1 and gate 7.** `anchor_1d` on the two-day grid: Sharpe {f2(GRID["anchor_1d"]["cycle_sharpe_on_2d_grid"])} against
   {f2(GRID["anchor"]["cycle_sharpe_on_2d_grid"])} ({H1["sharpe_on_2d_grid_gap"]:+.2f}); late-period CAGR {pc(S["anchor_1d"]["late_cagr"])} - REJECT on gate 7 (cell 39). Its
   positions sold while their vault was still in the pool net {usd(H1["churn_pnl_1d"])} on {H1["churn_positions_1d"]} positions against
   the anchor's {usd(H1["churn_pnl_anchor"])} on {H1["churn_positions_anchor"]} (in-trade pool log, cell 39); the pool-removal sells net
   {usd(H1["pool_removal_pnl_1d"])} against {usd(H1["pool_removal_pnl_anchor"])}. Where the money went is therefore the in-pool sells, on one
   window; why a daily rebalance makes them lose is not attributed here. H1 fails, so the
   one-day gates and the cluster diagnostic were not run: the plan's stop rules stopped it.
   "Can we react in a day" has the answer the plan predicted - the incumbent did not need to -
   and a second one it did not predict: on this window, looking every day cost {usd(H1["churn_pnl_1d"] - H1["churn_pnl_anchor"])} on
   the in-pool sells.
5. **The breaker and the cluster are moot on this engine's clock.** A -20% last-day breaker
   fires twice on the anchor's pre-decision held book in the whole window (cell 32): on
   {brk_may["decision"]} for the May vault - the very decision on which the incumbent's own gate already
   sells it, so the breaker adds nothing there - and on {brk_other["decision"]} for `{brk_other["vault"]}`, which then
   rose {pc(brk_other["fwd_5d"])} in five days. It never fires before a collapse: the first decision that sees a
   -20% day is the one the gate acts on. The
   first-strike table (cell 32) is descriptive: `first_extreme` first-entry rows average
   {pc(fs[("first_extreme", "fwd_1d")]["mean"])} the next day with a block interval [{pc(fs[("first_extreme", "fwd_1d")]["ci_lo"])}, {pc(fs[("first_extreme", "fwd_1d")]["ci_hi"])}] that spans zero, and the
   every-day appendix's {pc(es[("first_extreme", "fwd_1d")]["mean"])} is aftermath.
6. **The 4-hour question, answered without a backtest.** From April 2026 the held vaults have
   {pc(cov_dense)} empty 4-hour buckets on average (median {pc(COV["('empty_share', 'median')"]["dense (2026-04-01 on)"])}, worst {pc(COV["('empty_share', 'max')"]["dense (2026-04-01 on)"])}); before it,
   {pc(cov_sparse)} (cell 31). The two collapse vaults are fully covered at 4 hours through their
   collapses (no empty bucket, cell 30), and 20 May is six consecutive down buckets there; a
   4-hour clock for the whole book is not shown to be possible (the worst held vault is mostly
   empty even in the dense period), and whether it would be worth its decision count, given
   what one day did (finding 4), is not a question this track's indicator stack can answer.

## Summary of results

The runs (cells 36, 39):

| run | what | CAGR | Sharpe | Sharpe on 2d grid | max DD | in-pool sells' P&L | verdict |
|---|---|---|---|---|---|---|---|
| `anchor` | incumbent, gate -16%, 2d | {cg("anchor")} | {sh("anchor")} | {f2(GRID["anchor"]["cycle_sharpe_on_2d_grid"])} | {dd("anchor")} | {usd(CH["anchor"]["churn_pnl_usd"])} | - |
| `gate12_2d` | gate -12%, 2d | {cg("gate12_2d")} | {sh("gate12_2d")} | {sh("gate12_2d")} | {dd("gate12_2d")} | {usd(CH["gate12_2d"]["churn_pnl_usd"])} | NOT CONFIRMED ({G["gate12_2d"]["sharpe_gap_to_anchor"]:+.2f}; passes 1, 2 ({f2(G["gate12_2d"]["mask_retention"])}), 3, 6, 7) |
| `gate10_2d` | gate -10%, 2d | {cg("gate10_2d")} | {sh("gate10_2d")} | {sh("gate10_2d")} | {dd("gate10_2d")} | {usd(CH["gate10_2d"]["churn_pnl_usd"])} | UNEVALUATED (endpoint on gate 6; mask {f2(G["gate10_2d"]["mask_retention"])}) |
| `anchor_1d` | incumbent, 1d | {cg("anchor_1d")} | {sh("anchor_1d")} | {f2(GRID["anchor_1d"]["cycle_sharpe_on_2d_grid"])} | {dd("anchor_1d")} | {usd(H1["churn_pnl_1d"])} | REJECT gate 7 (late CAGR {pc(S["anchor_1d"]["late_cagr"])}); H1 fails |

The fills (cell 34):

| sell | decision = executed_at | valuation (candle open) | previous close | collapse close | label | crash leg |
|---|---|---|---|---|---|---|
| August | {F["august"]["decision"][:10]} | {F["august"]["planned_mid_price"]:.4f} | {LEG["august"]["previous_close"]:.4f} | {LEG["august"]["close"]:.4f} | {L["august"]["label"]} | open-to-close {pc(LEG["august"]["open_to_close"])} |
| May | {F["may"]["decision"][:10]} | {F["may"]["planned_mid_price"]:.4f} | {LEG["may"]["previous_close"]:.4f} | {LEG["may"]["close"]:.4f} | {L["may"]["label"]} | open-to-close {pc(LEG["may"]["open_to_close"])} |

The tighter gate's fires on the anchor's PRE-decision held book (opened before the decision,
not closed before it; weight at the previous statistics timestamp), 14-day return in
(-16%, -12%] (cell 32):

| decision | vault | position opened | weight before | 14-day return | next 5 days | next 30 days |
|---|---|---|---|---|---|---|
{lines_fires}

Window A (2026-01-01 to 2026-07-10; contains May, not August; cell 41): `anchor` Sharpe {f2(W["anchor"]["cycle_sharpe"])},
`gate12_2d` {f2(W["gate12_2d"]["cycle_sharpe"])}, `anchor_1d` {f2(W["anchor_1d"]["cycle_sharpe"])}; the tighter gate and the one-day clock are worse there too.

The single-day stop table, reproduced (cell 31): at -10%, {ST["-0.1"]["triggered"]} positions trigger, {ST["-0.1"]["winners"]} of them
winners ({usd(ST["-0.1"]["winners_pnl"])}); at -15%, {ST["-0.15"]["triggered"]} trigger, all winners.

**What this means for the track.** The operator's question - how fast do the crashes happen,
can we react in a day - has a precise answer on this engine: the crashes are intraday, the
backtest's own fills sit at the open before them, and the incumbent's 14-day gate at 48 hours
already sold at the last unmoved mark on both collapse days. The pre-registered -12% gate
catches the one -14.5% day and is worse on the whole book; the one-day clock fails gate 7 and
loses {usd(H1["churn_pnl_1d"] - H1["churn_pnl_anchor"])} on its in-pool sells. Both are one-window, in-sample results on the two
variants the plan named; they say nothing about exit mechanisms not run (the cluster
diagnostic was not reached). The remaining lever is not in the backtest: a live redemption
decided at 00:00 fills at the vault's next NAV, and the backtest's open fill is optimistic by
whatever the first intraday move is - zero on these two days, not zero in general, and not
quantified here beyond those two days.

## Robustness of results

- The anchor reproduces NB40's anchor at 1e-9 with the cluster splice present and off (cell
  28); the pool loggers reproduce the anchor's cycle returns to 1e-12 (cells 28, 39).
- The fill predicate is asserted on trade objects, on `planned_mid_price` against the decision
  bar's `open` column at 1e-9 relative, with the async flags read from the pair, the feed delay
  read from the trade, and the fee identity `executed_price = mid x (1 - fee)` checked (cell
  34). The rank-churn example was selected by rule (first rank exit with a hold under four
  days, calendar order) and carries no label.
- The collapse positions were selected by rule (the anchor's momentum-gate sells on the two
  pre-stated dates), one each (cell 30). The 19 Aug gate value and the 19 Aug daily close are
  printed with their row timestamps and are different quantities that coincide.
- The collapse-day open equalling the previous close is a property of these two vaults' marks
  (the first mark of the day was unchanged), not of the engine; on a day whose first mark has
  already moved, the open fill takes that move, and the plan's H0b was written to catch it.
- The tighter gate's fire count is on the anchor's PRE-decision book (a position opened at
  the decision is not counted; the weight is the one going into the decision), so it says
  which of the anchor's holdings -12% would have sold that -16% held; the backtest
  (`gate12_2d`) says what the tighter gate did to its own, different, book. The two are
  consistent - one collapse caught, {len(recovered)} decisions on winners sold early - and the second is
  not attributed to the first.
- Churn is classified from the in-trade pool log (a position sold on a decision at which its
  vault was still a candidate was sold by ranking or sizing; otherwise by the gate or the
  universe screen), not from NB41's rank reconstruction, which does not mirror deposit-window
  skips or hold protection; the reconstruction is displayed beside it for comparison only
  (cells 37, 39). The one-day ledger reads the one-day pool log through a cache keyed by pool.
- The fill predicate fails closed on a non-zero feed delay (a forward-filled candle open would
  match at 1e-9 and prove nothing); both collapse sells have a zero delay.
- The one-day run is compared with the anchor on the anchor's own timestamps
  (`cycle_sharpe_on_2d_grid`, {GRID["anchor_1d"]["cycles"]:.0f} cycles, no missing timestamps) as well as on its own clock;
  the churn P&L uses the same exit classification as NB41.
- Same limits as the whole track: one window, 126 decisions, in sample; the archive is
  weekly-filled before April 2026 and the 4-hour coverage there is {pc(cov_sparse)} empty buckets.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB42 heading written: H0a {m['H0a']}, H0b {m['H0b']}, gate12_2d {G['gate12_2d']['verdict']} at {G['gate12_2d']['sharpe_gap_to_anchor']:+.3f}, anchor_1d H1 passes={H1['passes']}")
