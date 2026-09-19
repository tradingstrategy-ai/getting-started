"""Generate NB33's heading FROM manifest_33.json, so every number is read from a result frame."""
import json
from pathlib import Path

here = Path(__file__).parent
m = json.load(open(here / "manifest_33.json"))
A, B, D = m["table_a"], m["table_b"], m["hyper_ai_docstring"]
P = {(r["label"], r["period"]): r for r in m["periods"]}
PR = {(r["window"], r["label"]): r for r in m["paired"]}
prov = next(r for r in m["provenance"] if str(r["file"]).endswith("vault-prices.parquet"))
dens = m["density"]
labels = list(m["configs"])
leads = ["measured_8", "inverse_vol_q10", "floor15", "floor20"]

def pc(x): return f"{x*100:+.1f}%"
def f2(x): return f"{x:.2f}"
def f4(x): return f"{x:.4f}"
def beats_a(l): return A[l]["cumulative_return"] > A["anchor"]["cumulative_return"] and A[l]["cycle_sharpe"] > A["anchor"]["cycle_sharpe"]
def beats_b(l): return B[l]["cumulative_return"] > B["anchor"]["cumulative_return"] and B[l]["cycle_sharpe"] > B["anchor"]["cycle_sharpe"]

row = lambda l, T: f"| `{l}` | {pc(T[l]['cumulative_return'])} | {pc(T[l]['cagr'])} | {f2(T[l]['cycle_sharpe'])} | {f2(T[l]['daily_sharpe'])} | {f4(T[l]['cycle_vol'])} | {f4(T[l]['ulcer'])} | {pc(T[l]['max_dd'])} | {int(T[l]['distinct_vaults'])} |"
prow = lambda l: (f"| `{l}` | {pc(P[(l,'pre-incumbent, sparse')]['cum_return'])} / {f2(P[(l,'pre-incumbent, sparse')]['sharpe'])} "
                  f"| {pc(P[(l,'incumbent window')]['cum_return'])} / {f2(P[(l,'incumbent window')]['sharpe'])} "
                  f"| {pc(P[(l,'after incumbent window')]['cum_return'])} / {f2(P[(l,'after incumbent window')]['sharpe'])} |")
excl_b = [l for l in labels if l != "anchor" and PR[("B: full data period", l)]["excludes_zero"]]
excl_a = [l for l in labels if l != "anchor" and PR[("A: incumbent period", l)]["excludes_zero"]]
both = [l for l in leads if beats_a(l) and beats_b(l)]

H = f"""# NB33 - the incumbent and the best leads, side by side, on two windows

**Based on:** [26-backtest-drop-decomposition.ipynb](26-backtest-drop-decomposition.ipynb),
[29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb) and
[32-backtest-return-floor-stability-rank.ipynb](32-backtest-return-floor-stability-rank.ipynb)
for the leads; [02-better-format.ipynb](02-better-format.ipynb) for the anchor. The anchor is
parameter-for-parameter `~/code/strategies/strategy/hyper-ai.py` (v6) with a later
`backtest_end`, verified in [_build/verify-hyperai-window.ipynb](_build/verify-hyperai-window.ipynb).
This heading is generated from `_build/manifest_33.json` by `_build/write_heading_33.py`.

## What this notebook is

A comparison, not a test. It re-runs the incumbent and every lead the track has produced through
one kernel on one snapshot, on two windows, and puts the equity curves on one chart. Nothing here
is gated, pre-registered or shortlisted; the leads' own robustness checks live in their own
notebooks and are not repeated. Fourteen backtests (cell 26).

**Window A - the incumbent's own period**, 2026-01-01 to 2026-07-10, the window `hyper-ai.py`
reports in its docstring. Every configuration is run fresh on exactly that window.

**Window B - the full data period**, 2025-08-01 to 2026-09-09, the earliest start the earlier
`hyper-ai` generations used. Before 2026-04 most Hyperliquid vaults were polled roughly weekly:
the archive holds {int(dens['2025-08']['rows']):,} rows across {int(dens['2025-08']['vaults'])} vaults in August 2025 against
{int(dens['2026-08']['rows']):,} across {int(dens['2026-08']['vaults'])} in August 2026, and {int(dens['2025-08']['fresh_marks']):,} fresh marks in the
month against {int(dens['2026-08']['fresh_marks']):,} (cell 22). The strategy's daily series is forward-filled across the
gaps, so a stale mark is an exact zero return. A window-B figure is one number over two data
regimes; the sub-period table is the more honest reading.

## Configurations

| label | what | source | status there |
|---|---|---|---|
| `anchor` | `hyper-ai.py` as deployed | NB02 | reference |
| `measured_8` | drop the 8 most volatile vaults that HAVE a volatility estimate, then rank as the incumbent | NB26 | best leave-one-vault-out retention in the track |
| `inverse_vol_q10` | drop the least-stable 10% of finite-signal candidates (same family) | NB29 | not the pre-registered centre |
| `floor15` | incumbent composite behind a 15% annualised return floor over 45 days | NB32 | highest Sharpe in its grid; spike on basket size |
| `floor20` | the same with a 20% floor | NB32 | best single-vault survival in the track |
| `drop_30` | drop the 30 lowest `inverse_vol` (21 of them unmeasured) | NB21 | REJECTED - one vault carries 98% of its edge |
| `combo_floor15_measured8` | `floor15` and `measured_8` together | none | NOT a lead - a combination proposed for the next pre-registration, shown for scale |

## Key new insights and what did we learn from this experiment?

**1. The incumbent's docstring is its best six months.** On its own window this archive gives
`hyper-ai.py` {pc(A['anchor']['cumulative_return'])} cumulative, {pc(A['anchor']['cagr'])} CAGR, daily
Sharpe {f2(A['anchor']['daily_sharpe'])} (cell 28) against the docstring's {pc(D['cumulative_return'])},
{pc(D['cagr'])}, {f2(D['daily_sharpe'])} on the older archive - the same strategy to within a point. On
the full data period the same strategy is {pc(B['anchor']['cumulative_return'])} cumulative over
{int(B['anchor']['cycles'])} cycles, {pc(B['anchor']['cagr'])} CAGR, cycle Sharpe
{f2(B['anchor']['cycle_sharpe'])}, max drawdown {pc(B['anchor']['max_dd'])} (cell 31). Its path
(cell 33) is {pc(P[('anchor','pre-incumbent, sparse')]['cum_return'])} over the five sparse months before
the docstring's window, {pc(P[('anchor','incumbent window')]['cum_return'])} inside it, and
{pc(P[('anchor','after incumbent window')]['cum_return'])} in the two months after.

**2. The volatility-drop family beats the incumbent on both windows, and it is the only family
that does.** {', '.join(f'`{l}`' for l in both) if both else 'No lead'} beat{'s' if len(both) == 1 else ''} the anchor on
both cumulative return and cycle Sharpe on window A AND window B (cell 28, cell 31).
`measured_8` on the incumbent's window: {pc(A['measured_8']['cumulative_return'])} / Sharpe
{f2(A['measured_8']['cycle_sharpe'])} / max drawdown {pc(A['measured_8']['max_dd'])} against
{pc(A['anchor']['cumulative_return'])} / {f2(A['anchor']['cycle_sharpe'])} / {pc(A['anchor']['max_dd'])}; on
the full period {pc(B['measured_8']['cumulative_return'])} / {f2(B['measured_8']['cycle_sharpe'])} /
{pc(B['measured_8']['max_dd'])} against {pc(B['anchor']['cumulative_return'])} / {f2(B['anchor']['cycle_sharpe'])}
/ {pc(B['anchor']['max_dd'])}. This is the same direction NB26 and NB29 found on the track window:
three windows, one sign.

**3. The return floor is not a lead on the incumbent's window, and it is knife-edge on the full
one.** `floor15` is {pc(A['floor15']['cumulative_return'])} / Sharpe {f2(A['floor15']['cycle_sharpe'])} on
window A - WORSE than the anchor on both - and its full-window edge (NB32) came from
July-September, where it returned {pc(P[('floor15','after incumbent window')]['cum_return'])} against the
anchor's {pc(P[('anchor','after incumbent window')]['cum_return'])} (cell 33). On window B `floor15` is
the best lead ({pc(B['floor15']['cumulative_return'])}, Sharpe {f2(B['floor15']['cycle_sharpe'])}) and
`floor20` the worst ({pc(B['floor20']['cumulative_return'])}, Sharpe {f2(B['floor20']['cycle_sharpe'])}, max
drawdown {pc(B['floor20']['max_dd'])}); on window A the order reverses. A five-point change in the
floor flips which side of the anchor it lands on, on both windows. That is noise, not a lever.

**4. The proposed combination is bad, and this is the notebook that found out.**
`floor15 + measured_8` returns {pc(A['combo_floor15_measured8']['cumulative_return'])} at Sharpe
{f2(A['combo_floor15_measured8']['cycle_sharpe'])} on the incumbent's window (cell 28). It is worse
than `measured_8` alone ({pc(A['measured_8']['cumulative_return'])} / {f2(A['measured_8']['cycle_sharpe'])})
and worse than `floor15` alone ({pc(A['floor15']['cumulative_return'])} / {f2(A['floor15']['cycle_sharpe'])}),
and `floor15` itself does not beat the anchor on this window (finding 3). The floor and the drop
remove overlapping candidates and leave too thin a pool. It was proposed for the next
pre-registration in the previous message of this track; it should not be.

**5. `drop_30` looks ordinary on the incumbent's window and is the only configuration whose
paired interval excludes zero on the full one.** Window A: {pc(A['drop_30']['cumulative_return'])} /
Sharpe {f2(A['drop_30']['cycle_sharpe'])}, inside the pack. Window B: {pc(B['drop_30']['cumulative_return'])} /
{f2(B['drop_30']['cycle_sharpe'])}, paired Sharpe difference {PR[('B: full data period','drop_30')]['sharpe_diff']:+.2f}
with interval [{PR[('B: full data period','drop_30')]['ci_lo']:+.2f}, {PR[('B: full data period','drop_30')]['ci_hi']:+.2f}]
(cell 35). NB26 showed 98% of its track-window edge was one vault and it fails the plateau; a
longer window does not change that, it only adds more of the same vault's history.

**6. The volatility drop helps INSIDE the incumbent's window and not after it; the floor helps
outside it and not inside.** In the sparse months `floor15` returned {pc(P[('floor15','pre-incumbent, sparse')]['cum_return'])}
against `measured_8`'s {pc(P[('measured_8','pre-incumbent, sparse')]['cum_return'])}; after July 10,
{pc(P[('floor15','after incumbent window')]['cum_return'])} against {pc(P[('measured_8','after incumbent window')]['cum_return'])};
inside, {pc(P[('floor15','incumbent window')]['cum_return'])} against {pc(P[('measured_8','incumbent window')]['cum_return'])}
(cell 33). They are complementary in time, which is why the combination looked attractive - and
point 4 is what happens when they are simply stacked.

## Summary of results

**Window A - the incumbent's period, 2026-01-01 to 2026-07-10 (cell 28)**

| configuration | cumulative | CAGR | cycle Sharpe | daily Sharpe | vol | ulcer | max DD | vaults |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(row(l, A) for l in labels) + f"""
| *hyper-ai.py docstring, archive 2026-08-21* | {pc(D['cumulative_return'])} | {pc(D['cagr'])} | - | {f2(D['daily_sharpe'])} | - | - | {pc(D['max_dd'])} | - |

**Window B - the full data period, 2025-08-01 to 2026-09-09 (cell 31)**

| configuration | cumulative | CAGR | cycle Sharpe | daily Sharpe | vol | ulcer | max DD | vaults |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(row(l, B) for l in labels) + f"""

**Sub-periods of the window-B path (cell 33)** - cumulative return / cycle Sharpe

| configuration | sparse, 2025-08 to 2025-12 | incumbent window | after, 2026-07-10 on |
|---|---|---|---|
""" + "\n".join(prow(l) for l in labels) + f"""

Paired Sharpe intervals against the same-window anchor exclude zero for
{', '.join(f'`{l}`' for l in excl_a) if excl_a else 'nothing'} on window A and
{', '.join(f'`{l}`' for l in excl_b) if excl_b else 'nothing'} on window B (cell 35).

## Robustness of results

- **Everything is in-sample and nothing is gated.** The nine gates of `RESEARCH-RULES.md` were
  not run here; each lead's own notebook records what it passed and failed on the track window.
  Window B is the first time any of them has been run on 2025 data.
- **Window B's first five months are on weekly-ish polling with forward-filled gaps** (cell 22).
  Returns there are mostly stale-mark zeros with occasional jumps; `cagr_score` needs 360 days of
  history that few vaults had, so admission was thin. The pre-incumbent sub-period figures should
  be read as "what the mechanism did on sparse data", not as a third independent test.
- **One engine assertion was relaxed for window B** (cell 24). `get_remaining_cost_basis()`
  checks its replayed share count against the position's to an absolute 1e-8; a vault with 118
  million shares misses that by 1.3e-8, the float64 resolution at that magnitude. The function is
  redefined here with a relative tolerance and is otherwise identical. It never triggered on the
  track window.
- **The two windows share the same six months**, so agreement between them is not independent
  confirmation; the informative comparisons are window A against the docstring and the three
  sub-periods against each other.
- **`inverse_vol_q10` and `measured_8` are the same mechanism at slightly different strengths**
  (10% of ~122 measured candidates is about 12 names against 8), and they move together on every
  window. Count them as one lead.
- **Snapshot**: `vault-prices.parquet` {int(prov['bytes']):,} bytes, sha256 prefix `{prov['sha256']}` (cell 20).
  Anchor parity holds against `BASELINE` at 1e-5 on the track window (cell 20).
"""
out = here.parent / "33-research-lead-comparison.ipynb"
nb = json.load(open(out))
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"NB33 heading written: beats both windows = {both}; excludes zero A={excl_a} B={excl_b}")
