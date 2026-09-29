"""Generate NB40's heading from _build/manifest_40.json. Every number from the manifest; the
qualitative claims are asserted so the prose cannot outlive a different result."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "40-backtest-lead-forensics-cash-sleeve.ipynb"
m = json.loads((HERE / "manifest_40.json").read_text())
G37 = json.loads((HERE / "manifest_37.json").read_text())["gates"]

S = m["summary"]
R = m["risk"]
RR = m["rescue_risk"]
L = m["ledgers"]
MASK = m["mask"]
SECOND = m["second_mask"]
BANDS = m["bands"]
EXCL = m["exclusion_outcomes"]
SPARSE = m["sparse"]
OVERLAP = m["overlap"]
BS = m["band_summary"]
FS = m["floor_summary"]
G = m["gates"]
RP = m["replateau"]
W = m["windows"]
AL = m["anchor_lovo"]
AQ = m["anchor_quality_at_open"]
LD = m["ledger_detail"]
FLD = m["floor_ledger_detail"]
DE = m["drawdown_episodes"]
BA = m["bands_aligned"]
EP = m["engine_positions"]
SC = m["sleeve_check"]
QA = m["quality_log_agreement"]
A = S["anchor"]
WA, WB = "A: incumbent period", "B: full data period"
RANKER = "thr150_cagr_sharpe__inverse_variance"
NALL = "thr150_nall_invvar"


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pc(x): return f"{x * 100:.1f}%"
def usd(x): return f"-${-x / 1000:.1f}k" if x < 0 else f"${x / 1000:.1f}k"
def sh(l): return f3(S[l]["cycle_sharpe"])
def cg(l): return pc(S[l]["cagr"])
def vol(l): return f3(S[l]["cycle_vol"])
def dd(l): return pc(S[l]["max_dd"])
def gap(l): return f"{S[l]['cycle_sharpe'] - A['cycle_sharpe']:+.2f}"


# --- claims the prose makes, asserted against the manifest ---
assert m["reproduction_max_abs_diff"] < 1e-6
top_anchor = AQ[0]
assert top_anchor["vault"] == "0x77fe..1a16" and top_anchor["pnl_share"] > 0.40
assert L["anchor"]["top_vault"] == "0x77fe..1a16"
for l in ("thr150", "measured_8", "thr200", RANKER):
    assert MASK[l]["masked_vault"] == "0x77fe..1a16", l
assert MASK["thr100"]["masked_vault"] != "0x77fe..1a16"
assert SECOND["thr100"]["retention_second"] < 0.5 and SECOND[RANKER]["retention_second"] > 0.85
assert all(EXCL[l]["held_exclusions"] == 0 for l in ("thr100", "thr150", "thr200", "thr150_n4", "thr100_n4"))
band = BANDS[0]
assert band["wide"] == "thr150" and band["tight"] == "thr100" and band["wide_band_pnl_share_of_net"] > 0.6
aligned = BA[0]
assert aligned["wide"] == "thr150" and aligned["tight"] == "thr100"
# thr100 has no position in the engine vault that covers the June-August run
assert not any(str(r["opened"]) <= "2026-06-20" and (r["closed"] is None or str(r["closed"]) >= "2026-08-21") for r in EP["thr100"])
thr100_engine_last_close = max(str(r["closed"]) for r in EP["thr100"] if r["closed"] is not None)
assert all(str(r["opened"]) < "2026-06-20" for r in EP["thr100"])
assert all(QA[k]["mismatches"] == 0 for k in QA)
sleeve_worst_weight = max(SC[k]["largest_realised_weight"] for k in SC)
sleeve_f30 = SC["anchor_f30"]
thr_axis = [S[l]["cycle_sharpe"] for l in ("thr100", "thr125", "thr150", "thr175", "thr200")]
assert thr_axis[1] < thr_axis[0] < thr_axis[2] and abs(thr_axis[2] - thr_axis[3]) < 1e-9 and thr_axis[4] < thr_axis[2]
assert G["thr175"]["verdict"].startswith("NOT CONFIRMED") and G["thr125"]["verdict"] == "REJECT"
assert not RP["thr150"]["passes"] and not RP["nofilter_n4"]["passes"] and not RP["thr150_n4"]["passes"]
assert abs(W[WB]["thr150"]["cycle_sharpe"] - W[WB]["thr175"]["cycle_sharpe"]) > 0.1
for l in ("measured_8", "thr150"):
    assert S[l]["cagr"] >= A["cagr"] and S[l]["cycle_sharpe"] >= A["cycle_sharpe"] and abs(S[l]["max_dd"] - A["max_dd"]) < 0.001, l
ncap = [S[l]["cycle_sharpe"] for l in ("n3cap", "n4cap", "n5cap")]
assert ncap[1] > ncap[2] and ncap[1] > ncap[0] and ncap[1] > A["cycle_sharpe"]
assert G["thr150_n5"]["mask_retention"] < 0.7 and G["thr150_n5"]["gate_2_mask"] is False
assert OVERLAP["nofilter_n4"]["capital_share_in_reference_names"] > 0.99
assert SPARSE[NALL]["sparse_capital_share"] > 2 * SPARSE["anchor"]["sparse_capital_share"]
assert L[NALL]["net_pnl_usd"] < 0.3 * L["anchor"]["net_pnl_usd"]
floors = ["anchor_f10", "anchor_f15", "anchor_f20", "anchor_f25", "anchor_f30"]
assert all(G[l]["verdict"] == "REJECT" for l in floors + [l.replace("anchor", "thr150") for l in floors]
           + ["thr150_n4cap_f10", "thr150_n4cap_f20", "thr150_n4cap_f30", "thr150_nallcap_f10", "thr150_nallcap_f20", "thr150_nallcap_f30"])
assert S["anchor_f10"]["cagr"] < 0.05 and S["anchor_f10"]["sleeve_active_share"] == 0
assert S["thr150_nallcap_f10"]["cycle_vol"] < 0.05 and S["thr150_nallcap_f10"]["cagr"] < 0.10
assert FS["anchor_held_median_quality"]["median"] < 1.5 and FS["anchor_held_clear_f10"]["mean"] < 4
assert S["anchor_f30"]["mean_invested"] < 0.25 and S["anchor_f30"]["sleeve_active_share"] > 0.9
assert not G["thr150_n4cap"]["gate_3_held_vol"] and not G["n4cap"]["gate_3_held_vol"]
assert all(RR[l]["max_dd"] < -0.09 for l in ("thr150_n4cap_f10",))
assert AL["retention"] > 0.7, AL
assert all(G[l]["verdict"] == "REJECT" for l in G if l not in ("thr175", "thr150_nocap")), [l for l in G if G[l]["verdict"] != "REJECT"]
assert G["thr150_nocap"]["verdict"].startswith("UNEVALUATED")

floor_runs = [l for l in G if "_f" in l and l.split("_f")[-1].isdigit()]
floor_gate1_fail = [l for l in floor_runs if not G[l]["gate_1_positive"]]
floor_gate7_fail = [l for l in floor_runs if not G[l]["gate_7_subperiod"]]
assert len(floor_gate7_fail) == len(floor_runs)
capped_n = ["n3cap", "n4cap", "n5cap", "thr150_n3cap", "thr150_n4cap", "thr150_n5cap"]
assert all(not G[l]["gate_3_held_vol"] for l in capped_n)
capped_n_gate6_scored_fail = [l for l in capped_n if G[l]["gate_6_plateau"] is False]
capped_n_gate6_unscored = [l for l in capped_n if G[l]["gate_6_plateau"] is None]
first_dd_n4 = DE["thr150_n4|1"]
first_dd_anchor = DE["anchor|1"]
winners_quality = ", ".join(f"{r['vault']} {r['quality_at_open']:.2f}" if r["quality_at_open"] == r["quality_at_open"] else f"{r['vault']} n/a" for r in AQ[:5])
# The floor at 1.0 and the anchor's engine position: opened at a quality just above the floor, and
# the floor run holds that vault only before and after the run, never through it.
engine_quality = top_anchor["quality_at_open"]
assert 1.0 <= engine_quality < 1.5
f10_engine = [r for r in FLD["anchor_f10"] if r["vault"] == "0x77fe..1a16"]
assert f10_engine and all(not (str(r["opened"]) <= "2026-06-20" and (r["closed"] is None or str(r["closed"]) >= "2026-08-21")) for r in f10_engine)
f10_engine_spans = "; ".join(f"{r['opened']} to {r['closed'] or 'open'} ({usd(r['pnl_usd'])})" for r in sorted(f10_engine, key=lambda r: str(r["opened"])))
f10_engine_reentry = [r for r in f10_engine if str(r["opened"]) > "2026-06-20"]
n4_top = LD["thr150_n4"][0]
assert n4_top["vault"] == "0x77fe..1a16" and n4_top["peak_weight"] > 0.5
nall_top_weight = max(r["peak_weight"] for r in LD[NALL])
nall_top_weight_row = max(LD[NALL], key=lambda r: r["peak_weight"])
assert nall_top_weight > 0.35
n4_loss = min(LD["nofilter_n4"], key=lambda r: r["pnl_usd"])
assert n4_loss["pnl_usd"] < -5000 and n4_loss["peak_weight"] > 0.7


def lead_table():
    rows = [("anchor", "anchor", ""), ("measured_8", "count 8 (NB36)", "NOT CONFIRMED"), ("thr150", "threshold 1.5", "REJECT gate 6"),
            ("thr200", "threshold 2.0", "NOT CONFIRMED"), ("thr100", "threshold 1.0", "REJECT gates 6, 2"),
            (RANKER, "cagr_sharpe ranker, thr 1.5", "REJECT gate 2 (0.68)"), ("nofilter_n4", "N = 4, cap off", "REJECT gates 3, 6"),
            ("thr150_n4", "N = 4, thr 1.5, cap off", "REJECT gates 3, 6"), ("nofilter_n3", "N = 3, cap off", "REJECT gates 3, 6"),
            ("nocap", "cap off", "UNEVALUATED"), (NALL, "unlimited, inverse-variance, cap off", "REJECT gate 7")]
    lines = ["| run | what | recorded verdict | CAGR | Sharpe | max DD | worst 5 cycles | top vault share of +P&L | largest weight | held-book vol |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for l, what, verdict in rows:
        r = R[l]
        lines.append(f"| {l} | {what} | {verdict} | {cg(l)} | {sh(l)} | {dd(l)} | {pc(r['worst5_cycles_sum'])} | {pc(r['top_vault_pnl_share'])} | {f2(r['mean_largest_weight'])} | {r['held_vol_post']:.4f} |")
    return "\n".join(lines)


def axis_table():
    lines = ["| exit threshold | 1.0 | 1.25 | 1.5 | 1.75 | 2.0 | off (anchor) |", "|---|---|---|---|---|---|---|"]
    lines.append("| CAGR | " + " | ".join(cg(l) for l in ("thr100", "thr125", "thr150", "thr175", "thr200", "anchor")) + " |")
    lines.append("| Sharpe | " + " | ".join(sh(l) for l in ("thr100", "thr125", "thr150", "thr175", "thr200", "anchor")) + " |")
    def verdict(l):
        if l == "anchor":
            return "-"
        row = G[l] if l in G else G37[l]
        failed = (row.get("failed_standing_gates") or "").replace("gate_", "").replace("_plateau", "").replace("_mask", "").replace("_held_vol", "").replace("_subperiod", "").replace("_positive", "")
        if l in G:   # a post-hoc grid point: a sensitivity calculation, not a verdict
            return f"would fail ({failed}), exploratory" if failed else "would pass, exploratory"
        text = row["verdict"].split(" (")[0]
        return f"{text} ({failed})" if failed else text
    lines.append("| standing gates (NB37 verdict / NB40 sensitivity) | " + " | ".join(verdict(l) for l in ("thr100", "thr125", "thr150", "thr175", "thr200", "anchor")) + " |")
    return "\n".join(lines)


def n_table():
    lines = ["| N | 3 | 4 | 5 | 6 |", "|---|---|---|---|---|"]
    lines.append("| cap kept, no filter: Sharpe / max DD | " + " | ".join(f"{sh(l)} / {dd(l)}" for l in ("n3cap", "n4cap", "n5cap", "anchor")) + " |")
    lines.append("| cap kept, thr 1.5 | " + " | ".join(f"{sh(l)} / {dd(l)}" for l in ("thr150_n3cap", "thr150_n4cap", "thr150_n5cap", "thr150")) + " |")
    lines.append("| cap off, no filter | " + " | ".join(f"{sh(l)} / {dd(l)}" for l in ("nofilter_n3", "nofilter_n4", "nofilter_n5", "nocap")) + " |")
    lines.append("| cap off, thr 1.5 | " + " | ".join(f"{sh(l)} / {dd(l)}" for l in ("thr150_n3", "thr150_n4", "thr150_n5", "thr150_nocap")) + " |")
    return "\n".join(lines)


def floor_table():
    lines = ["| floor on 180-day event Sharpe | off | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 |", "|---|---|---|---|---|---|---|"]
    for prefix, base, name in (("anchor", "anchor", "incumbent, six slots"), ("thr150", "thr150", "thr 1.5, six slots")):
        cells = [f"{cg(base)} / {sh(base)}"] + [f"{cg(f'{prefix}_{t}')} / {sh(f'{prefix}_{t}')}" for t in ("f10", "f15", "f20", "f25", "f30")]
        lines.append(f"| {name}: CAGR / Sharpe | " + " | ".join(cells) + " |")
    lines.append("| qualifying names per decision (mean / min) | - | " + " | ".join(f"{S[f'anchor_{t}']['qualifying_mean']:.1f} / {S[f'anchor_{t}']['qualifying_min']:.0f}" for t in ("f10", "f15", "f20", "f25", "f30")) + " |")
    lines.append("| mean invested | " + pc(A["mean_invested"]) + " | " + " | ".join(pc(S[f"anchor_{t}"]["mean_invested"]) for t in ("f10", "f15", "f20", "f25", "f30")) + " |")
    lines.append("| thr 1.5, N = 4, cap: CAGR / Sharpe | " + f"{cg('thr150_n4cap')} / {sh('thr150_n4cap')} | " + " | ".join(f"{cg(f'thr150_n4cap_{t}')} / {sh(f'thr150_n4cap_{t}')}" if f"thr150_n4cap_{t}" in S else "-" for t in ("f10", "f15", "f20", "f25", "f30")) + " |")
    lines.append("| thr 1.5, unlimited, cap: CAGR / Sharpe / vol | " + f"{cg('thr150_nallcap')} / {sh('thr150_nallcap')} / {vol('thr150_nallcap')} | " + " | ".join(f"{cg(f'thr150_nallcap_{t}')} / {sh(f'thr150_nallcap_{t}')} / {vol(f'thr150_nallcap_{t}')}" if f"thr150_nallcap_{t}" in S else "-" for t in ("f10", "f15", "f20", "f25", "f30")) + " |")
    return "\n".join(lines)


HEADING = f"""# NB40 - lead forensics and the cash-sleeve rescue

Every portfolio-level lead with a cycle Sharpe above 1.5 on the track window was REJECTED, left
NOT CONFIRMED, or left UNEVALUATED (`nocap`, whose plateau and mask were not run) by a numerical
gate in NB36 and NB37. This notebook reads those rejections
off the trades instead of the numbers: the equity curve, the positions that made and lost the
money, the drawdowns and the worst cycles, the vault behind each single-vault mask, the vaults
that sit in the band between two thresholds when a plateau fails, and whether the crash filter's
exits actually avoided losses. Some positive luck is allowed; the question asked of each lead is
whether it traded too riskily and whether it did what it was built to do.

It then checks whether the N and threshold assumptions the leads were scored under were sensible
(the position family with the 33% cap kept, a finer threshold family around 1.5), and tries one
rescue: a QUALITY FLOOR with a CASH SLEEVE. A candidate is allocated capital only if its trailing
180-day event-time Sharpe - an NB39-derived score: the same ratio as NB39's `sharpe180_f00`, the
strongest predictor of forward 60-day Sharpe on the full archive, except that its first event
starts at the last mark before the window rather than the first mark inside it - clears a floor;
slots no qualifying vault fills stay in cash. The
floor family 1.0 / 1.5 / 2.0 / 2.5 / 3.0 was pre-stated from NB39's candidate distribution before
any run.

**This is an EXPLORATORY notebook.** The standing gates (RESEARCH-RULES.md, idiot-gate audit of
2026-09-16: 1 positive return, 2 single-vault mask, 3 held-book volatility, 6 plateau, 7
sub-period sign) are computed for every new run as sensitivity results - "would pass / would
fail these gate calculations" - not as verdicts: the refined threshold grid and the capped
position family were added after `thr150`'s and N = 4's results were seen, and no recorded NB36
or NB37 verdict is revised here. Nothing here is out of sample.

**Based on:** [37-backtest-threshold-crash-filter.ipynb](37-backtest-threshold-crash-filter.ipynb)
and [36-backtest-calm-closeout.ipynb](36-backtest-calm-closeout.ipynb) for the leads and the gate
machinery, [39-research-trimmed-screen-full-history.ipynb](39-research-trimmed-screen-full-history.ipynb)
for the quality score, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Track
window 2026-01-01 to 2026-09-08; windows A and B as in NB33. The eleven leads reproduce their
NB37 / NB36 runs at {m["reproduction_max_abs_diff"]:.1e} on five metrics (cell 28).

## Key new insights and what did we learn from this experiment?

**Verdict: nothing is rescued, and the forensics change what the leads are.** `thr150` and
`measured_8` overlap the anchor on {pc(min(OVERLAP["thr150"]["capital_share_in_reference_names"], OVERLAP["measured_8"]["capital_share_in_reference_names"]))}-{pc(max(OVERLAP["thr150"]["capital_share_in_reference_names"], OVERLAP["measured_8"]["capital_share_in_reference_names"]))} of capital, and they, `thr200` and the `cagr_sharpe`
ranker share its largest position; `thr150_n4` and `nofilter_n4` hold that position at twice
the weight; and the quality floor loses that position and most of the return with it.

1. **One position is the largest contributor to the 2026 result.** `0x77fe..1a16`, held 2026-06-20 to 08-21, delivers
   {pc(top_anchor["pnl_share"])} of the anchor's net P&L ({usd(top_anchor["pnl_usd"])} of {usd(L["anchor"]["net_pnl_usd"])}) and
   {pc(MASK["thr150"]["anchor_share_of_positive_pnl"])} of its positive P&L (cells 34, 38). `thr150`, `measured_8`, `thr200` and the
   `cagr_sharpe` ranker - `measured_8` removes the eight lowest finite `inverse_vol` values per
   date, `thr150` applies a fixed threshold; they change {pc(S["measured_8"]["share_of_decisions_changed"])} and {pc(S["thr150"]["share_of_decisions_changed"])} of decisions and
   are different rules - all hold the same position; it is {pc(MASK["thr150"]["lead_share_of_positive_pnl"])}, {pc(MASK["measured_8"]["lead_share_of_positive_pnl"])},
   {pc(MASK["thr200"]["lead_share_of_positive_pnl"])} and {pc(MASK[RANKER]["lead_share_of_positive_pnl"])} of their positive P&L. Their books overlap the
   anchor's on {pc(OVERLAP["thr150"]["capital_share_in_reference_names"])} ({f2(OVERLAP["thr150"]["mean_jaccard_vs_reference"])} Jaccard) of capital (cell 42). The anchor under its own
   mask retains {f3(AL["retention"])} of its Sharpe (cell 38). The ranker lead retains {f2(MASK[RANKER]["recorded_mask_retention"])} under the same mask,
   below the anchor's own figure; that vault is {pc(MASK[RANKER]["lead_share_of_positive_pnl"])} of its positive P&L against {pc(MASK[RANKER]["anchor_share_of_positive_pnl"])} of the
   anchor's, and masking its second vault instead retains {f2(SECOND[RANKER]["retention_second"])} - the same one name.
2. **The threshold cliff is consistent with that position.** `0x77fe..1a16` is one of the {band["band_vaults"]} names
   `thr100`'s filter excluded on dates `thr150` held them; `thr100`'s last position in it closed
   on {thr100_engine_last_close} and it never re-entered (cell 40, every position listed). On the disputed
   cycles alone - those on which `thr100`'s filter excluded a name `thr150` was holding -
   `thr150` earned {usd(aligned["wide_disputed_pnl_usd"])}, {pc(aligned["wide_disputed_pnl_share_of_net"])} of its net P&L over {aligned["wide_disputed_cycles"]} cycles, and the anchor
   {usd(aligned["reference_disputed_pnl_usd"])} ({pc(aligned["reference_disputed_pnl_share_of_net"])}) over its own {aligned["reference_disputed_cycles"]} disputed cycles (cell 40). Both are aligned P&L
   contributions, not counterfactuals: they say where the money was earned, not what excluding a
   name caused, because the tighter filter also changes the rest of the basket and the sizing.
   The whole-window P&L of the band names is {pc(band["wide_band_pnl_share_of_net"])} of `thr150`'s, a looser association.
   `thr100` differs from the anchor on {pc(S["thr100"]["share_of_decisions_changed"])} of decisions, so the cliff is not one
   position alone; its top vault is
   `{MASK["thr100"]["masked_vault"]}` at {pc(MASK["thr100"]["lead_share_of_positive_pnl"])} and masking its SECOND vault retains only {f2(SECOND["thr100"]["retention_second"])} - a thin
   book, not a diversified one. The exit branch
   never fired on the six-name and four-name threshold runs: held-name exclusions are
   {EXCL["thr100"]["held_exclusions"]}, {EXCL["thr150"]["held_exclusions"]} and {EXCL["thr200"]["held_exclusions"]} at 1.0, 1.5 and 2.0 and {EXCL["thr150_n4"]["held_exclusions"]} and {EXCL["thr100_n4"]["held_exclusions"]} at N = 4 (the unlimited book has
   {EXCL[NALL]["held_exclusions"]}) - on those runs the filter is an ADMISSION filter and nothing else, so "did the exits
   avoid losses" has no data. The anchor's capital sits {pc(BS["anchor_cap_0.0-0.5"]["mean over decisions"])} below 0.5 annualised volatility and {pc(BS["anchor_cap_0.5-1.0"]["mean over decisions"])} in
   0.5-1.0; only {pc(BS["anchor_cap_1.0-1.25"]["mean over decisions"] + BS["anchor_cap_1.25-1.5"]["mean over decisions"])} is in 1.0-1.5 at any decision (cell 44), which is why the
   thresholds at 1.5 and above barely change the book and the ones below do.
3. **The threshold axis is jagged, and gate 6 depends on the grid.** Sharpe at exit 1.0 / 1.25
   / 1.5 / 1.75 / 2.0 is {" / ".join(f3(x) for x in thr_axis)} (cell 46): 1.75 has identical displayed track-window
   metrics to 1.5 (its survivor count differs slightly, so the books are not shown to be the
   same), so it WOULD pass the plateau calculation against 1.5 and 2.0 while 1.5 fails it
   against 1.25; it would pass every standing-gate calculation (Sharpe {gap("thr175")} to the anchor, inside
   the indifference band; mask {f2(G["thr175"]["mask_retention"])}). That is a sensitivity result on a grid point inserted after
   `thr150`'s result was seen, not a verdict, and NB37's REJECT of `thr150` stands as recorded. On
   window B the two rules no longer produce identical realised results ({f2(W[WB]["thr175"]["cycle_sharpe"])} against {f2(W[WB]["thr150"]["cycle_sharpe"])},
   cell 52). What the axis
   shows is that gate 6's answer for a threshold between 1.25 and 2.0 depends on which
   neighbours are pre-registered - a property of the test, recorded here for the rules.
4. **N = 4 is the anchor's names at about twice the weight.** `0x77fe..1a16` at {f2(n4_top["peak_weight"])} peak weight is
   {pc(L["thr150_n4"]["top_vault_pnl_share_of_positive"])} of `thr150_n4`'s positive P&L and {pc(L["nofilter_n4"]["top_vault_pnl_share_of_positive"])} of `nofilter_n4`'s; the two largest position
   losses inside their {pc(first_dd_n4["depth"])} drawdown ({first_dd_n4["peak"]} to {first_dd_n4["trough"]}) are that vault and `0x4dec..27f6`
   (cell 36), and `nofilter_n4` lost {usd(-n4_loss["pnl_usd"])} on `{n4_loss["vault"]}` at a {f2(n4_loss["peak_weight"])} peak weight over its last
   {n4_loss["days"]} days (cell 34). {pc(OVERLAP["nofilter_n4"]["capital_share_in_reference_names"])} of the four-name books' capital is in names the anchor holds,
   at weights near twice the anchor's, which is consistent with concentration being the major
   contributor to the extra return - the overlap does not isolate it from subset choice or
   trade timing. With the cap KEPT the family is
   {" / ".join(f3(x) for x in ncap)} / {sh("anchor")} at N = 3 / 4 / 5 / 6 (cell 46) - N = 4 stands above both neighbours in
   the capped family as in the uncapped one, N = 5 with the filter masks at {f2(G["thr150_n5"]["mask_retention"])}, and every
   N < 6 fails gate 3. This is the risky trading the operator asked about: a {R["thr150_n4"]["mean_holdings"]:.1f}-name book in
   which one position is about two thirds of the positive P&L and two positions most of the
   deepest drawdown.
5. **The unlimited inverse-variance book is consistent with the sizing rule's stale-mark bias.** {pc(SPARSE[NALL]["sparse_capital_share"])} of its
   capital sits in names with fewer than 30 moved marks in 90 rows against the anchor's
   {pc(SPARSE["anchor"]["sparse_capital_share"])} (cell 42); with the cap off, `{nall_top_weight_row["vault"]}` reached a {f2(nall_top_weight)} weight over
   {nall_top_weight_row["days"]} days (cell 34); late-period P&L per vault is within a thousand dollars (cell 42). Its
   {cg(NALL)} at {vol(NALL)} volatility is a near-cash book, not a low-volatility strategy. The run also changes
   capacity and removes the cap, so the sparse-mark share is a consistent reading, not an
   isolated cause.
6. **The quality floor loses the June-to-August engine position and most of the return.** The anchor's held names have a median
   trailing 180-day event-time Sharpe of {f2(FS["anchor_held_median_quality"]["median"])}; only {f2(FS["anchor_held_clear_f10"]["mean"])} of six clear 1.0 and
   {f2(FS["anchor_held_clear_f20"]["mean"])} clear 2.0 on a mean decision (cell 44). Its five largest positions had quality at
   entry of {winners_quality}. A floor of 1.0 leaves {S["anchor_f10"]["qualifying_mean"]:.0f} qualifying names per decision - the
   sleeve never activates - and takes the incumbent from {cg("anchor")} to {cg("anchor_f10")} ({sh("anchor")} to {sh("anchor_f10")} Sharpe);
   higher floors go negative and the sleeve holds up to {pc(1 - S["anchor_f30"]["mean_invested"])} cash at 3.0 (cell 48). The
   engine position of finding 1 opened at a quality of {f2(engine_quality)}, a hair above the floor, and the
   floor run holds that vault only {f10_engine_spans} - the position is absent from
   June 18 to August 17, the whole of the run, and returns for {f10_engine_reentry[0]["days"] if f10_engine_reentry else 0} days (cell 48; the log entry
   that closed it is not printed, so whether the floor or another eligibility condition closed it
   on that date is not shown). The winners' scores sit at the floor family's bottom and the
   floor has no hysteresis. The unlimited-capacity capped book with the floor at 1.0 ({S["thr150_nallcap_f10"]["qualifying_mean"]:.1f} names
   qualify per decision, {S["thr150_nallcap_f10"]["mean_holdings"]:.1f} are held) earns {cg("thr150_nallcap_f10")} at {vol("thr150_nallcap_f10")} volatility, Sharpe {sh("thr150_nallcap_f10")},
   against {cg("thr150_nallcap")} / {sh("thr150_nallcap")} for the same book without the floor - in this implementation the
   floor lowered the return of the unlimited book as well (one anchor winner, `0x4dec..27f6`,
   entered at a quality of {AQ[1]["quality_at_open"]:.2f}, so qualification and return are not simply opposed). Every
   one of the {len(floor_runs)} floor runs
   fails the gate 7 calculation and {len(floor_gate1_fail)} of them fail gate 1 (cell 50). This tests a FLOOR on NB39's score, not a ranker on
   it: the floor-and-sleeve construction is what failed. NB39's universe-wide rank correlation of
   about 0.25 stands as measured; what it does at the top of a six-name book is untested, and a
   floor WITH hysteresis below 1.0 is a different, untested rule.
7. **The sleeve behaved as built and had nothing to rescue.** The smoke test
   (`_build/verify-sleeve.ipynb`) asserted fill == selected / slots and the cap under a partial
   fill; on the full runs, independently of the sleeve's own log, the largest realised position
   weight across every floor run is {f2(sleeve_worst_weight)} against a 0.33 cap, and a floor of 3.0 leaves the
   book {pc(sleeve_f30["mean_invested_realised"])} invested against an intended {pc(sleeve_f30["sleeve_mean_allocation_intended"])} ({S["anchor_f30"]["decisions_none_qualifying"]:.0f} decisions with nothing
   qualifying), and the floor's logged qualifying counts match an offline reconstruction on all
   126 decisions for each of the ten six-slot runs checked (cell 48). What is verified is that
   mean realised deployment was no greater than mean intended deployment; the construction that failed is the floor AND the
   sleeve together, and this notebook does not separate their contributions.

## Summary of results

The leads as re-run, with the risk panel (cells 28, 32, 34):

{lead_table()}

The threshold axis, refined (cells 46, 50):

{axis_table()}

The position family, cap kept and cap off, Sharpe / max drawdown (cells 46, 28):

{n_table()}

The rescue (cell 48):

{floor_table()}

Standing-gate calculations for the new runs, as sensitivity results (cell 50): `thr175` would
pass every gate (Sharpe {gap("thr175")} to the anchor, inside the indifference band; mask {f2(G["thr175"]["mask_retention"])});
`thr150_nocap` is unevaluable on gate 6 (a family endpoint; mask {f2(G["thr150_nocap"]["mask_retention"])}, Sharpe {gap("thr150_nocap")}); every other
new run fails at least one gate - the capped position family fails gate 3 on all six runs and
gate 6 on the {len(capped_n_gate6_scored_fail)} where it is scored ({", ".join(capped_n_gate6_unscored)} unscored as endpoints; {", ".join(f"`{l}`" for l in capped_n if not G[l]["gate_7_subperiod"])}
also fail gate 7), `thr125` fails gate 6, N = 5 uncapped fails gate 6 (and gate 2 with the filter), every floor
run fails gate 7 and {len(floor_gate1_fail)} of {len(floor_runs)} fail gate 1. Gate 6 is scored only where both pre-registered
neighbours exist. Re-reading the old leads' plateaus against the refined and capped neighbours
changes none of them (cell 50).

Windows A and B (cell 52): on the incumbent's window `thr150` and `thr175` are identical
({f2(W[WA]["thr150"]["cycle_sharpe"])} against the anchor's {f2(W[WA]["anchor"]["cycle_sharpe"])}); on the full data period `thr150` holds {f2(W[WB]["thr150"]["cycle_sharpe"])}
against {f2(W[WB]["anchor"]["cycle_sharpe"])} and `thr175` {f2(W[WB]["thr175"]["cycle_sharpe"])}.

**What this means for the track.** No lead is established as a selection improvement on this
window. The two rules no worse than the anchor on CAGR and cycle Sharpe (max drawdown within
0.1 percentage points of it) - `measured_8` (NOT CONFIRMED,
conditionally positive, as recorded after NB36; {S["measured_8"]["share_of_decisions_changed"] * 126:.0f} of 126 decisions changed) and an
admission threshold near 1.5 annualised trailing volatility (`thr150`, {S["thr150"]["share_of_decisions_changed"] * 126:.0f} decisions changed,
REJECT on gate 6 as recorded; `thr175` would pass the same calculations on the refined grid) -
are different rules that share the anchor's exposures - {pc(OVERLAP["thr150"]["capital_share_in_reference_names"])} and {pc(OVERLAP["measured_8"]["capital_share_in_reference_names"])} of capital in the
same names, the same largest position at {pc(MASK["thr150"]["lead_share_of_positive_pnl"])} and {pc(MASK["measured_8"]["lead_share_of_positive_pnl"])} of positive P&L. Whether to carry
either is the operator's call on priors. The high-return four-name cap-off variants buy return with
books in which the largest vault is {pc(L["thr150_n4"]["top_vault_pnl_share_of_positive"])}-{pc(L["nofilter_n4"]["top_vault_pnl_share_of_positive"])} of positive P&L, and fail the risk gates on
the trades, not on a technicality. The quality-floor rescue, in the form built here (a floor without
hysteresis on the 180-day event-time Sharpe, with a cash sleeve), would fail the standing-gate
calculations on every run; ranking on that score is untested. If a lead's gate is to be re-examined, it is gate 6's dependence on grid spacing
(finding 3), and the place for that is RESEARCH-RULES.md, not a re-scored verdict.

## Robustness of results

- Anchor parity holds with the floor and sleeve splices present (cell 26); the eleven leads
  reproduce NB37 / NB36 at {m["reproduction_max_abs_diff"]:.1e} (cell 28); the smoke test `_build/verify-sleeve.ipynb`
  asserted the anchor path writes no floor or sleeve log, fill == selected / slots, positions
  close when their vault drops below the floor, and the cap holds under a partial fill.
- The forensics are position statistics of the same runs, not new estimates: P&L from
  `get_total_profit_usd()`, drawdown attribution from per-cycle cumulative `profit_usd`, band
  membership from the crash log, quality at entry from the cached indicator at T-1. The
  whole-window band P&L is an association and the disputed-cycle attribution (cell 40) is an
  aligned P&L contribution; neither is a counterfactual, and the heading says so.
- The quality-population table (cell 44) is drawn from two populations - the whole candidate
  pool the anchor floor family sees and `thr150`'s survivors the `thr150` floor family sees -
  and the ten six-slot floor runs' logged qualifying counts match that reconstruction on every
  decision (the N = 4 and unlimited floor runs are not checked).
- The floor family was stated in cell 26 before any floor run; the refined threshold grid and
  the capped position family are post-hoc sensitivity checks on results already seen, and their
  gate calculations are reported as such, never as verdicts. That `thr175` and `thr150` no
  longer produce identical results on window B is reported beside it.
- Held-name exclusions are zero on every six-name and four-name threshold run; the unlimited
  run supplies one exit observation ({EXCL[NALL]["held_exclusions"]} held-name exclusion, cell 40), not enough to assess the
  exit threshold, and the hysteresis is unverified by any result in this track.
- The floor's score is measured on a mean {FS["measured"]["mean"]:.0f} of {FS["candidates"]["mean"]:.0f} candidates per decision (cell 44): a vault
  younger than 180 days, or one whose marks do not span the window, can never qualify. The
  anchor's own held names are measured on {FS["anchor_held_measured"]["mean"] * 126:.0f} of {FS["anchor_held"]["mean"] * 126:.0f} holding-decisions and the engine
  position was measured at its opening; the displayed output cannot distinguish a below-floor
  score, a later missing score, or another eligibility change at its June 18 exit, and every
  unmeasured candidate is excluded by design, so coverage is part of the construction's effect.
- Same limits as the whole track: one window, 126 decisions, in sample throughout; the luck
  ratio is undefined for most runs that change the book heavily.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB40 heading written: thr175 {G['thr175']['verdict']}; anchor_f10 {cg('anchor_f10')}; anchor mask retention {AL['retention']:.3f}")
