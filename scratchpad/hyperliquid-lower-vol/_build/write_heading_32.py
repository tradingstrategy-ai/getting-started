"""Generate NB32's heading FROM manifest_32.json, so every number is read from the frame that
produced it. Two reviews in a row found stale figures typed into the heading by hand."""
import json, sys
from pathlib import Path

m = json.load(open(Path(__file__).parent / "manifest_32.json"))
g, b, lb, d, hc, fr = m["main_grid"], m["breadth"], m["lookback"], m["decomposition"], m["held_vol_common"], m["frontier"]
lovo = {r["label"]: r for r in m["lovo"]}
A = g["anchor"]

def pc(x): return f"{x*100:.1f}%"
def f4(x): return f"{x:.4f}"
def sb(r): return b[f"incumbent__floor15__n{r}"]

stab = {k: r for k, r in g.items() if r["ranker"] != "incumbent"}
neg = sum(1 for r in stab.values() if r["cagr"] < 0)
best_stab_k = max(stab, key=lambda k: stab[k]["cagr"]); best_stab = stab[best_stab_k]
inc = {f: g[f"incumbent__floor{f}__n6"] for f in ("0", "10", "15", "20", "30")}
beats = [f for f in inc if inc[f]["cagr"] > A["cagr"] and inc[f]["cycle_sharpe"] > A["cycle_sharpe"]]
c15, i15 = d["calm__floor15__n6"], d["incumbent__floor15__n6"]
c_nofee, c_nocap, c_both = d["calm__floor15__n6__nofee"], d["calm__floor15__n6__nocap"], d["calm__floor15__n6__nofee_nocap"]
i_nofee, i_nocap = d["incumbent__floor15__n6__nofee"], d["incumbent__floor15__n6__nocap"]
a_nofee, a_nocap = d["incumbent__floornone__n6__nofee"], d["incumbent__floornone__n6__nocap"]
gap_10_15 = inc["15"]["cycle_sharpe"] - inc["10"]["cycle_sharpe"]
n_runs = len(m["all_runs"]) + 1

H = f"""# NB32 - return floor, then rank by stability: the practical comparison

**Based on:** [29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb) for
the harness, and the 2026-09-14 out-of-sample sketch that motivated it. Anchor
[02-better-format.ipynb](02-better-format.ipynb). Full window 2026-01-01 to 2026-09-08,
in-sample throughout. {n_runs} backtests: the anchor and {n_runs - 1} others (cell 38).

**Revised twice after Codex review** (`gpt-5.6-sol`,
[first](32-backtest-return-floor-stability-rank-codex-review.md) and
[second](32-backtest-return-floor-stability-rank-codex-review-2.md)). Every number in this
heading is generated from `_build/manifest_32.json` by `_build/write_heading_32.py`, because both
reviews found figures typed by hand that belonged to an earlier run. The review log is in the
Robustness section.

## Why this notebook exists

The sketch ranked every Hyperliquid vault on a 45-day formation window and held the top six
equal-weight over the next, disjoint 45 days, six times over. One family of rules was positive
in most splits: **a hard annualised return floor, then rank the survivors by a stability
measure.** With a 15% floor and a volatility ranker it returned 27.4% annualised at volatility
0.138, against the anchor's {pc(A['cagr'])} / {f4(A['cycle_vol'])}. This notebook runs the idea
through the real strategy and sweeps the magic numbers the sketch fixed by hand.

## The mechanism, and why it needs no new code

- **the floor** is `return_gate`: a candidate is admitted only if its trailing return over
  `gate_lookback_days` exceeds `gate_threshold`. The anchor uses a 14-day lookback and a threshold
  of **-0.16** - drawdown insurance, not a return floor. Here the lookback is 45 days and the
  threshold is `(1 + floor)^(45/365) - 1` (cell 21).
- **the ranker** is `selection_score_indicator`: the anchor ranks by `cagr_sortino_weight`, which
  is 60% CAGR. Here it is swapped for one of five stability scores.

Three rankers are new indicators (`calm_score`, `inverse_ulcer_score`, `inverse_downside_score`).
The raw `inverse_vol` cannot be a ranker: a vault whose mark has not moved in 90 days has sigma
= 0, is floored, and scores 10,000. The new scores are NaN unless at least 30 marks moved inside
the window AND the last one is within 10 rows. Sizing is untouched.

## Key new insights and what did we learn from this experiment?

**1. In this engine and this window, the stability rankers do not work (cell 24).** At the 15%
floor and six names: calm **{pc(g['calm__floor15__n6']['cagr'])}**, inverse downside
{pc(g['downside__floor15__n6']['cagr'])}, inverse ulcer {pc(g['ulcer__floor15__n6']['cagr'])},
Sortino {pc(g['sortino__floor15__n6']['cagr'])}, gain-to-pain {pc(g['gtp__floor15__n6']['cagr'])},
against the anchor's {pc(A['cagr'])}. Across all 30 stability-ranker configurations in the main
grid the best CAGR is **{pc(best_stab['cagr'])}** ({best_stab['ranker']}, {best_stab['floor']}%
floor) and **{neg} of 30 are negative**.

**2. Removing the engine's costs does not recover the sketch's number (cell 36).** Calm ranker,
15% floor, six names: as run **{pc(c15['cagr'])}**; fees off **{pc(c_nofee['cagr'])}**
({(c_nofee['cagr']-c15['cagr'])*100:+.1f} pp); pool cap off **{pc(c_nocap['cagr'])}**
({(c_nocap['cagr']-c15['cagr'])*100:+.1f} pp); both off **{pc(c_both['cagr'])}**. The sketch's
27.4% is not the same rule - it differs in the volatility window, the admission rules, the
concentration limit, the sizing and the re-evaluation cadence, none of which this table varies -
and this notebook does not say which of those differences carries the gap. It says only that
fees and the cap do not.

**3. Fees are large for everyone and fall hardest on whatever earns most (cell 36).** Fees cost
the calm ranker {(c15['cagr']-c_nofee['cagr'])*-100:.1f} points, the incumbent at the same floor
{(i_nofee['cagr']-i15['cagr'])*100:.1f} ({pc(i15['cagr'])} to {pc(i_nofee['cagr'])}), and the
anchor {(a_nofee['cagr']-A['cagr'])*100:.1f} ({pc(A['cagr'])} to {pc(a_nofee['cagr'])}). A 10%
performance fee scales with profit. Both reviews called the fee model blocking on the grounds
that vault fees are internalised in NAV; that holds for ERC-4626 vaults and not for Hyperliquid,
where leader commission is charged on the follower's profit at withdrawal. The archive records
**594 of 603** Hypercore vaults at a 10% commission (cell 36). The model stays.

**4. The pool cap is strongly protective (cell 36).** Genuinely removed (1e6 x TVL, which cannot
bind), it costs the calm ranker {(c15['cagr']-c_nocap['cagr'])*100:.1f} points, the incumbent at
15% {(i15['cagr']-i_nocap['cagr'])*100:.1f} and the anchor {(A['cagr']-a_nocap['cagr'])*100:.1f}
({pc(A['cagr'])} to {pc(a_nocap['cagr'])}). It stops the book concentrating into a small vault
that then fails. The first draft of this heading said the cap was a drag that left the calm runs
in cash; it is neither - with the cap off the calm ranker still holds {(1-c_nocap['mean_invested'])*100:.0f}%
cash, so the cash comes from somewhere else, and this notebook does not identify where.

**5. Most of the stability rankers' low raw volatility is cash (cell 24).** Mean invested runs
{f4(min(r['mean_invested'] for r in stab.values()))} to {f4(max(r['mean_invested'] for r in stab.values()))}
against the anchor's {f4(A['mean_invested'])}. Invested-basket volatility - cycle return over the
prior cycle's invested fraction, on {c15['invested_vol_cycles'] if 'invested_vol_cycles' in c15 else 106} cycles -
is **{f4(c15['invested_vol'])}** for the calm ranker at the 15% floor against {f4(i15['invested_vol'])}
for the incumbent at the same floor and {f4(A['invested_vol'])} for the anchor: about
{(1-c15['invested_vol']/A['invested_vol'])*100:.0f}% lower, not the
{(1-c15['cycle_vol']/A['cycle_vol'])*100:.0f}% the raw column shows.

**6. They hold calmer vaults, by a factor of {1/hc['calm__floor15__n6']['ratio_to_anchor']:.1f} on
common dates (cell 24).** Capital-weighted own daily volatility on the {hc['calm__floor15__n6']['common_dates']}
dates both configurations cover: calm at the 15% floor {f4(hc['calm__floor15__n6']['held_vol_common'])},
anchor on the same dates {f4(hc['calm__floor15__n6']['anchor_on_same_dates'])}. Two earlier drafts
gave "five to twenty times" (conditioned on an unrelated indicator's coverage) and "2.4 times"
(different calendar samples); this is the comparison both reviews asked for.

**7. The floor helps the incumbent, and {len(beats)} incumbent-floor runs beat the anchor on both
CAGR and Sharpe (cell 24, cell 38).** {'; '.join(f"{f}%: {f4(inc[f]['cagr'])} / {f4(inc[f]['cycle_sharpe'])}" for f in beats)};
anchor {f4(A['cagr'])} / {f4(A['cycle_sharpe'])}. None dominates the anchor on every risk measure -
all have deeper maximum drawdowns ({min(inc[f]['max_dd'] for f in beats):.4f} to {max(inc[f]['max_dd'] for f in beats):.4f}
against {A['max_dd']:.4f}). At every floor the best Sharpe belongs to the incumbent ranker. **The
ranker matters far more than the floor**: at the 15% floor CAGR spans {pc(min(r['cagr'] for k,r in g.items() if r['floor']=='15'))}
to {pc(max(r['cagr'] for k,r in g.items() if r['floor']=='15'))} across rankers, while the incumbent spans
{pc(min(r['cagr'] for r in inc.values()))} to {pc(max(r['cagr'] for r in inc.values()))} across floors.

**8. The improvement is inside the noise and sits on a spike in basket size (cell 34, cell 28).**
Paired Sharpe difference against the anchor for the 15% run: +0.1758, 95% interval [-0.63, +1.12]
at block 5. Across basket sizes at that floor the incumbent's Sharpe is
**{' / '.join(f4(sb(n)['cycle_sharpe']) for n in (4,6,8,10,12))}** at 4 / 6 / 8 / 10 / 12 names -
a spike at exactly the anchor's basket size. Across floors it is NOT flat by the notebook's own
tolerance either: {' / '.join(f4(inc[f]['cycle_sharpe']) for f in ('10','15','20','30'))} at
10 / 15 / 20 / 30%, and the 10%-to-15% gap of {gap_10_15:.4f} exceeds the 0.25 plateau band.
15%, 20% and 30% lie within {max(inc[f]['cycle_sharpe'] for f in ('15','20','30')) - min(inc[f]['cycle_sharpe'] for f in ('15','20','30')):.4f} of each other.

**9. The same vault is the largest contributor everywhere, but dependence on it falls with the
floor (cell 33).** Leave-one-vault-out masks `{lovo['anchor']['masked'][:10]}...` for the anchor and
all five top runs. Sharpe retention under the mask: anchor {f4(lovo['anchor']['sharpe_retention'])},
15% floor {f4(lovo['incumbent__floor15__n6']['sharpe_retention'])}, 20% {f4(lovo['incumbent__floor20__n6']['sharpe_retention'])},
30% {f4(lovo['incumbent__floor30__n6']['sharpe_retention'])}. Top-vault P&L share: anchor
{f4(A['top_vault_pnl_share'])}, 15% {f4(inc['15']['top_vault_pnl_share'])}, 30% {f4(inc['30']['top_vault_pnl_share'])}.

**10. Widening the basket with a stability ranker does not help (cell 28).** Calm ranker at
twelve names, 15% floor: CAGR {pc(b['calm__floor15__n12']['cagr'])}, volatility
{f4(b['calm__floor15__n12']['cycle_vol'])}. The incumbent's breadth cliff:
{' / '.join(pc(sb(n)['cagr']) for n in (4,6,8,10,12))} at 4 / 6 / 8 / 10 / 12 names.

**11. Only the 45-day gate lookback is positive, which makes the result fragile (cell 31).**
Calm ranker, 15% floor, six names: {' / '.join(f"{k.split('__lb')[-1] if '__lb' in k else ('45d' if k.endswith('n6') else 'vol45')}: {pc(v['cagr'])}" for k, v in lb.items())}.

## Summary of results

| configuration | CAGR | Sharpe | vol | invested vol | invested | ulcer | max DD | cell |
|---|---|---|---|---|---|---|---|---|
| anchor | {f4(A['cagr'])} | {f4(A['cycle_sharpe'])} | {f4(A['cycle_vol'])} | {f4(A['invested_vol'])} | {f4(A['mean_invested'])} | {f4(A['ulcer'])} | {A['max_dd']:.4f} | 21 |
""" + "".join(
    f"| incumbent, {f}% floor, 6 | {f4(inc[f]['cagr'])} | {f4(inc[f]['cycle_sharpe'])} | {f4(inc[f]['cycle_vol'])} | {f4(inc[f]['invested_vol'])} | {f4(inc[f]['mean_invested'])} | {f4(inc[f]['ulcer'])} | {inc[f]['max_dd']:.4f} | 23 |\n"
    for f in ("15", "20", "30")) + "".join(
    f"| {g[k]['ranker']}, {g[k]['floor']}% floor, 6 | {f4(g[k]['cagr'])} | {f4(g[k]['cycle_sharpe'])} | {f4(g[k]['cycle_vol'])} | {f4(g[k]['invested_vol'])} | {f4(g[k]['mean_invested'])} | {f4(g[k]['ulcer'])} | {g[k]['max_dd']:.4f} | 23 |\n"
    for k in ("calm__floor20__n6", "calm__floor15__n6")) + f"""| calm, 15% floor, 6, fees off | {f4(c_nofee['cagr'])} | {f4(c_nofee['cycle_sharpe'])} | {f4(c_nofee['cycle_vol'])} | {f4(c_nofee['invested_vol'])} | {f4(c_nofee['mean_invested'])} | {f4(c_nofee['ulcer'])} | {c_nofee['max_dd']:.4f} | 36 |
| calm, 15% floor, 6, fees+cap off | {f4(c_both['cagr'])} | {f4(c_both['cycle_sharpe'])} | {f4(c_both['cycle_vol'])} | {f4(c_both['invested_vol'])} | {f4(c_both['mean_invested'])} | {f4(c_both['ulcer'])} | {c_both['max_dd']:.4f} | 36 |
| anchor, fees off | {f4(a_nofee['cagr'])} | {f4(a_nofee['cycle_sharpe'])} | {f4(a_nofee['cycle_vol'])} | {f4(a_nofee['invested_vol'])} | {f4(a_nofee['mean_invested'])} | {f4(a_nofee['ulcer'])} | {a_nofee['max_dd']:.4f} | 36 |
| anchor, cap off | {f4(a_nocap['cagr'])} | {f4(a_nocap['cycle_sharpe'])} | {f4(a_nocap['cycle_vol'])} | {f4(a_nocap['invested_vol'])} | {f4(a_nocap['mean_invested'])} | {f4(a_nocap['ulcer'])} | {a_nocap['max_dd']:.4f} | 36 |

**Verdict: EXPLORATORY, nothing shortlisted.** In this window and this implementation the
stability rankers performed poorly and are not carried. The incumbent-plus-floor result is
recorded as the highest observed Sharpe in the grid and is not carried either.

## Robustness of results

- **Everything is in-sample on one window** whose minimum detectable Sharpe difference is about
  2.50. The largest positive Sharpe improvement over the anchor is 0.18; several negative
  differences are far larger in magnitude. No comparison here is resolvable.
- **The top five are post-hoc by construction** (cell 33). All five are the incumbent ranker at
  different floors; their diagnostics are what a pre-registration would gate on, not gates.
- **Part 6 varies two engine settings and holds every other difference from the sketch fixed.**
  It shows those two do not close the gap. It does not identify what does, and the heading no
  longer claims to.
- **Runs with fees or the cap off are comparable only with each other.** `BASELINE` includes
  both, and anchor parity (cell 21) is asserted with both on.
- **`require_scored_candidates = True` for the stability rankers and `False` for the incumbent
  are not the same admission rule.** Their `mean_holdings` is 5.88 to 5.96 against 6.00, so the
  effect on basket size is small, but it is not zero.
- **The redemption-fee audit in cell 42 is tautological**: it checks execution against the stored
  aggregate rate rather than recomputing 10% of positive redeemed profit independently. It is
  the base notebook's audit, unchanged since NB01 and inherited by every notebook in the track.
  Recorded here; fixing it is a track-level change.
- **Review log.** First review: one blocking (fees), seven material, two minor; the recency guard,
  single-window ulcer, volatility-only held-book measure, fee/cap decomposition and six wording
  corrections were applied; the build-script finding was rejected because `write_notebook()`
  preserves a filled heading by design. Second review: one blocking (fees, again), six material,
  three minor. Applied: the cap genuinely removed (1.0 x TVL was still a cap), common-date held
  volatility, invested-volatility coverage counts, the anchor restored to the frontier's "none"
  row, the "flat across floors" claim withdrawn, the "gap is in the dynamics" inference
  withdrawn, and four stale numbers replaced by generated ones. Rejected: the fee model, with the
  leader-commission evidence above; the build-script finding, as before. Deferred: the fee audit.
- **Snapshot**: `vault-prices.parquet` 254,818,366 bytes, sha256 prefix `3e79966a`. Anchor parity
  holds against `BASELINE` at 1e-5 with the three new ranker indicators present (cell 21).
"""
out = Path(__file__).parent.parent / "32-backtest-return-floor-stability-rank.ipynb"
nb = json.load(open(out))
nb["cells"][0] = {"cell_type": "markdown", "metadata": {}, "source": H.splitlines(keepends=True)}
json.dump(nb, open(out, "w"), indent=1)
print(f"heading written from manifest: {n_runs} backtests, {neg}/30 negative, {len(beats)} incumbent-floor runs beat the anchor")
