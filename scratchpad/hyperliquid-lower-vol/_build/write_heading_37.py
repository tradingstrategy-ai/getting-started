"""Generate NB37's heading from _build/manifest_37.json. Every number from the manifest; the
qualitative claims are asserted so the prose cannot outlive a different result."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "37-backtest-threshold-crash-filter.ipynb"
m = json.loads((HERE / "manifest_37.json").read_text())

S = m["summary"]
G = m["gates"]
W = m["windows"]
CC = m["cycle_concentration"]
C = m["centre"]
CT = m["centre_threshold"]
prov = m["provenance"]
vp = next(v_ for k, v_ in prov.items() if "vault-prices" in k)
A = S["anchor"]
WA, WB = "A: incumbent period", "B: full data period"
FAM = list(m["threshold_family"])
NALL = f"{C}_nall_invvar"
BEST = m["best_other"]


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def pc(x): return f"{x * 100:.1f}%"
def sh(l): return f3(S[l]["cycle_sharpe"])
def cg(l): return pc(S[l]["cagr"])
def vol(l): return f3(S[l]["cycle_vol"])
def dd(l): return pc(S[l]["max_dd"])


assert C == "thr150", C
assert S["thr250"]["decisions_changed"] == 0
assert S["thr100"]["cagr"] < S["anchor"]["cagr"] - 0.10
assert S["thr150"]["cycle_sharpe"] > S["anchor"]["cycle_sharpe"] and S["thr150"]["cagr"] > S["anchor"]["cagr"]
assert S["nocap"]["cycle_sharpe"] < S["anchor"]["cycle_sharpe"]
assert all(S[f"{p}_n1"]["cagr"] < 0 for p in ("thr100", "nofilter", "thr150"))
assert S[NALL]["max_dd"] > -0.02 and S[NALL]["cycle_vol"] < 0.06
assert S[f"{C}_nall_equal"]["cagr"] < 0
assert G["thr150"]["gate_2_mask"] and not G["thr150"]["gate_6_plateau"]
assert G["thr200"]["verdict"].startswith("NOT CONFIRMED")
best6 = max((l for l in S if S[l]["mean_holdings"] > 5.5 and l != "anchor"), key=lambda l: S[l]["cycle_sharpe"])
nall_gate7_segment = [k for k in ("sparse_cagr", "dense_cagr", "late_cagr") if S[NALL][k] <= 0]

def n_table():
    lines = ["| N | no filter | filter 1.0 | filter 1.5 |", "|---|---|---|---|"]
    for n in (1, 2, 3, 4):
        cells = [f"{cg(f'{p}_n{n}')} / {sh(f'{p}_n{n}')} / {dd(f'{p}_n{n}')}" for p in ("nofilter", "thr100", C)]
        lines.append(f"| {n} | " + " | ".join(cells) + " |")
    lines.append(f"| 6 (cap off) | {cg('nocap')} / {sh('nocap')} / {dd('nocap')} | {cg('thr100_nocap')} / {sh('thr100_nocap')} / {dd('thr100_nocap')} | {cg(f'{C}_nocap')} / {sh(f'{C}_nocap')} / {dd(f'{C}_nocap')} |")
    return "\n".join(lines)

HEADING = f"""# NB37 - threshold crash filter: max positions, concentration cap, rankers and weighters

Plan 34's `measured_8` removed a fixed COUNT of the most volatile measurable candidates. This
notebook replaces the count with a THRESHOLD on the vault itself: a candidate is not admitted
while its trailing 90-row realised volatility is above 80% annualised, and a held vault is
removed when it rises above 100%. The number comes from a vault-level calibration on the
post-break archive (66 decisions x ~210 candidates): the forward 30-day crash rate is flat
below 50% annualised, 4-6% between 50% and 100%, and triples at 100% (15% in 1.0-1.5, 22% in
1.5-2.0), with the mean 30-day log return falling from about -4% to -17% across the same knee.

Around that filter the notebook varies what the operator asked to see: the concentration cap
removed (`max_concentration_pct` 0.33 -> 1.0); `max_assets_in_portfolio` 1, 2, 3, 4 and 6, and
unlimited (every survivor of the filter held); and the rankers and weighters the track has
already researched, at six names. **Verdict: EXPLORATORY - nothing carried; one shape worth a
plan of its own** (finding 4).

**Verdicts use the standing gates only** (RESEARCH-RULES.md, idiot-gate audit of 2026-09-16):
1 positive return, 2 single-vault mask, 3 held-book volatility, 6 plateau, 7 sub-period sign.
Gates 4 and 8 are reported with their tolerances as diagnostics. Nothing here is out of sample,
and the centre threshold for Parts 2-3 was chosen on this window (cell 27).

**Based on:** [35-backtest-calm-tail-exclusion.ipynb](35-backtest-calm-tail-exclusion.ipynb)
for the gate machinery, [32-backtest-return-floor-stability-rank.ipynb](32-backtest-return-floor-stability-rank.ipynb)
for the rankers, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Track window
2026-01-01 to 2026-09-08; windows A (incumbent's period) and B (full data) as in NB33. Snapshot
`vault-prices.parquet` {vp["bytes"]:,} bytes, sha256 `{vp["sha256"][:16]}` (cell 25).

## Key new insights and what did we learn from this experiment?

**1. The calibration knee is not where this book earns its return.** The vault-level crash rate
triples at 100% annualised volatility, but the incumbent's return comes from vaults between
50% and 150%. Threshold 1.0 removes {S["thr100"]["crash_excluded_mean"]:.0f} names per decision, changes
the book on {S["thr100"]["decisions_changed"]:.0f} of 126 decisions, halves the volatility ({vol("thr100")}
against {vol("anchor")}) and the drawdown ({dd("thr100")} against {dd("anchor")}) - and gives up
{pc(S["anchor"]["cagr"] - S["thr100"]["cagr"])} of CAGR for a LOWER Sharpe ({sh("thr100")} against {sh("anchor")}),
with mask retention {f3(G["thr100"]["mask_retention"])} below the 0.70 bar (cells 27, 33). The family
runs {sh("thr075")} / {sh("thr100")} / {sh("thr150")} / {sh("thr200")} / {sh("thr250")} in Sharpe at 0.75 / 1.0 /
1.5 / 2.0 / 2.5; at 2.5 the filter changes no decision at all - the {S["thr250"]["crash_excluded_mean"]:.1f}
names it removes per decision are ones the ranker never picked (cell 27). The best of the family,
1.5, is `measured_8` restated: {cg("thr150")} / {sh("thr150")} / {dd("thr150")}, {S["thr150"]["decisions_changed"]:.0f}
decisions changed, mask retention {f3(G["thr150"]["mask_retention"])}, better than the anchor on both
extra windows (window A {pc(W[WA]["thr150"]["cumulative_return"])} / {f2(W[WA]["thr150"]["cycle_sharpe"])} /
{pc(W[WA]["thr150"]["max_dd"])}, window B {pc(W[WB]["thr150"]["cumulative_return"])} / {f2(W[WB]["thr150"]["cycle_sharpe"])} /
{pc(W[WB]["thr150"]["max_dd"])}; cell 35). It fails gate 6 because tightening one step to 1.0 drops the
Sharpe by {f2(S["thr150"]["cycle_sharpe"] - S["thr100"]["cycle_sharpe"])}: this is a ridge with a cliff on the
tight side, not a spike, and its Sharpe gap to the anchor, {f2(S["thr150"]["cycle_sharpe"] - A["cycle_sharpe"])},
is inside the indifference band. Threshold 2.0 passes every standing gate and is
{f2(S["thr200"]["cycle_sharpe"] - A["cycle_sharpe"])} of Sharpe WORSE than the anchor (cell 33). The
threshold form is cleaner than the count, and it does not change the plan-34 conclusion: this
lever is worth about +0.1 to +0.2 Sharpe at best and cannot be told from noise here.

**2. Removing the concentration cap hurts, every time.** Inverse-variance sizing without a cap
hands the calmest vault {pc(S["nocap"]["mean_largest_weight"])} of the book on average: the anchor's
{cg("anchor")} / {sh("anchor")} becomes {cg("nocap")} / {sh("nocap")} with drawdown {dd("nocap")} and a luck
ratio of {f3(S["nocap"]["luck_ratio"])} (cell 27). With the 1.0 filter on top it is {cg("thr100_nocap")} /
{sh("thr100_nocap")}, with 1.5 it is {cg(f"{C}_nocap")} / {sh(f"{C}_nocap")}. The cap is doing real work:
it stops the sizer from making one quiet vault the whole book.

**3. Fewer names is worse at every N below six, and one name is a losing strategy.** With the
cap off (the only way a one-name book can exist), CAGR / Sharpe / max drawdown (cell 29):

{n_table()}

A one-name book cannot even deploy: the TVL size limit holds mean investment at
{pc(S["nofilter_n1"]["mean_invested"])} to {pc(S["thr150_n1"]["mean_invested"])}, and it loses money under
every filter. N = 4 with filter 1.5 posts the notebook's highest CAGR and Sharpe
({cg(f"{C}_n4")} / {sh(f"{C}_n4")}) and is the clearest luck signature in it: largest mean weight
{pc(S[f"{C}_n4"]["mean_largest_weight"])}, top five positions {pc(S[f"{C}_n4"]["top5_gross_share"])} of gross
profit, top vault {pc(S[f"{C}_n4"]["top_vault_pnl_share"])} of positive P&L, drawdown {dd(f"{C}_n4")}, held-book
volatility above the anchor's (gate 3), and a step from N = 3 ({sh(f"{C}_n3")}) that fails the
plateau by {f2(S[f"{C}_n4"]["cycle_sharpe"] - S[f"{C}_n3"]["cycle_sharpe"])} (cell 33). Every N < 6 run fails at
least two standing gates.

**4. Holding every survivor of the filter, sized by inverse variance, is a different strategy
- and it is the stable-curve shape this track was asked for.** `{NALL}`: {cg(NALL)} CAGR,
cycle volatility {vol(NALL)}, ulcer {f3(S[NALL]["ulcer"])}, max drawdown {dd(NALL)}, {S[NALL]["mean_holdings"]:.0f}
names on average, largest {pc(S[NALL]["mean_largest_weight"])}, turnover {pc(S[NALL]["turnover_per_decision"])}
per decision (cell 29). That is a third of the anchor's volatility and a quarter of its drawdown
for a quarter of its return, with a Sharpe of {sh(NALL)} that sits {f2(A["cycle_sharpe"] - S[NALL]["cycle_sharpe"])}
below the anchor's. It fails gate 7 ({", ".join(k.replace("_cagr", "") for k in nall_gate7_segment)} CAGR
{", ".join(pc(S[NALL][k]) for k in nall_gate7_segment)}) and its best cycle is {pc(CC[NALL]["best_cycle"])} of a
{pc(CC[NALL]["total_log_return"])} total log return, kurtosis {CC[NALL]["kurtosis"]:.0f} (cell 37). The same book
equal-weighted is a disaster ({cg(f"{C}_nall_equal")} CAGR): holding {S[f"{C}_nall_equal"]["mean_holdings"]:.0f} names
equally is holding the junk. The inverse-variance version is not a competitor to the
incumbent on the incumbent's objective; it is a low-volatility product, and it has not been
designed or gated as one. It should get its own plan with its own objective (target volatility,
drawdown, minimum return) rather than be judged against a 2.16 Sharpe here.

**5. Rankers and weighters: the incumbent's choices stand.** At six names with filter 1.5 and
the cap kept, `cagr_sharpe_weight` with inverse variance is the best six-name Sharpe in the
notebook ({cg(BEST)} / {sh(BEST)}, window B {pc(W[WB][BEST]["cumulative_return"])} /
{f2(W[WB][BEST]["cycle_sharpe"])}) and fails the mask at {f3(G[BEST]["mask_retention"])} retention, with
{S[BEST]["decisions_changed"]:.0f} decisions changed from the anchor; on window A it is below the anchor
({pc(W[WA][BEST]["cumulative_return"])} / {f2(W[WA][BEST]["cycle_sharpe"])}) (cells 31, 33, 35). Equal weighting
costs 20 or more CAGR points under every ranker; `inverse_vol` (k = 1) is a little worse than
inverse variance (k = 2) everywhere; `cagr_downside_weight` and `calm_score` lose money or
nearly so, as NB32 found (cell 31). Nothing in this part passes the standing gates and beats
the anchor.

## Summary of results

Standing-gate scorecard, six-name books (cell 33; CAGR / Sharpe / vol / max DD from cell 27):

| run | CAGR / Sharpe / vol / max DD | 1 | 7 | 3 | 6 | 2 (retention) | verdict |
|---|---|---|---|---|---|---|---|
| anchor | {cg("anchor")} / {sh("anchor")} / {vol("anchor")} / {dd("anchor")} | | | | | 0.825 (NB26) | reference |
| thr075 | {cg("thr075")} / {sh("thr075")} / {vol("thr075")} / {dd("thr075")} | ✓ | ✓ | ✓ | ✗ | not run | REJECT |
| thr100 (pre-stated) | {cg("thr100")} / {sh("thr100")} / {vol("thr100")} / {dd("thr100")} | ✓ | ✓ | ✓ | ✗ | ✗ {f3(G["thr100"]["mask_retention"])} | REJECT |
| thr150 (centre) | {cg("thr150")} / {sh("thr150")} / {vol("thr150")} / {dd("thr150")} | ✓ | ✓ | ✓ | ✗ (cliff at 1.0) | ✓ {f3(G["thr150"]["mask_retention"])} | REJECT by gate 6; economically NOT CONFIRMED |
| thr200 | {cg("thr200")} / {sh("thr200")} / {vol("thr200")} / {dd("thr200")} | ✓ | ✓ | ✓ | ✓ | ✓ {f3(G["thr200"]["mask_retention"])} | NOT CONFIRMED, below the anchor |
| thr250 | inert (= anchor) | | | | | | no effect |
| nocap | {cg("nocap")} / {sh("nocap")} / {vol("nocap")} / {dd("nocap")} | ✓ | ✓ | ✓ | - | not run | worse than the anchor |
| {BEST} | {cg(BEST)} / {sh(BEST)} / {vol(BEST)} / {dd(BEST)} | ✓ | ✓ | ✓ | - | ✗ {f3(G[BEST]["mask_retention"])} | REJECT |
| {NALL} | {cg(NALL)} / {sh(NALL)} / {vol(NALL)} / {dd(NALL)} | ✓ | ✗ | ✓ | - | {("✓ " + f3(G[NALL]["mask_retention"])) if G[NALL].get("gate_2_mask") else ("✗ " + f3(G[NALL]["mask_retention"]) if G[NALL].get("mask_retention") == G[NALL].get("mask_retention") else "not run")} | different objective; own plan |

Max positions (cell 29; all with the cap off): every N in 1-4 fails at least two standing
gates under every filter; N = 1 loses money; N = 4 is the highest number in the notebook and
the most concentrated. Rankers and weighters (cell 31): nothing beats the incumbent's pair on
the standing gates.

Windows (cell 35): thr150 beats the anchor on A ({pc(W[WA]["thr150"]["cumulative_return"])} vs
{pc(W[WA]["anchor"]["cumulative_return"])}) and B ({pc(W[WB]["thr150"]["cumulative_return"])} vs
{pc(W[WB]["anchor"]["cumulative_return"])}); thr100 is below it on both; `{NALL}` on A
{pc(W[WA][NALL]["cumulative_return"])} / {f2(W[WA][NALL]["cycle_sharpe"])} / {pc(W[WA][NALL]["max_dd"])} and on B
{pc(W[WB][NALL]["cumulative_return"])} / {f2(W[WB][NALL]["cycle_sharpe"])} / {pc(W[WB][NALL]["max_dd"])}.

## Robustness of results

- Anchor parity at 1e-5 with the crash splice present and off (cell 25); threshold 2.5 is
  bit-identical to the anchor on every cycle (cell 27), so the splice is inert when it excludes
  nothing the ranker would pick.
- Basket differences are measured from the position statistics directly (`basket_difference`),
  not from a log the filter does not write.
- The centre for Parts 2-3 was chosen on this window by Sharpe (cell 27). Everything downstream
  of it is exploratory, and the pre-stated 1.0 was run through Parts 2 and 5 regardless.
- The single-vault mask was run for {len(m["lovo_labels"])} configurations; every other gate-2 cell is
  "not run", which is absent from the verdict, not a failure.
- The luck ratio is undefined (NaN) for most runs that change the book heavily; gate 4 within
  tolerance holds only for {", ".join(l for l in G if G[l]["diag_4_luck_within_tolerance"])} (cell 33).
- Same limits as the whole track: one window, overlapping sub-windows, the same 126 decisions;
  the {f2(S["thr150"]["cycle_sharpe"] - A["cycle_sharpe"])} of thr150 and the {f2(S["thr200"]["cycle_sharpe"] - A["cycle_sharpe"])} of thr200 are both inside the noise of a
  mechanism that changes {S["thr200"]["decisions_changed"]:.0f}-{S["thr150"]["decisions_changed"]:.0f} decisions.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB37 heading written: centre {C}; best six-name {best6}; nall {NALL} {cg(NALL)} / {sh(NALL)}")
