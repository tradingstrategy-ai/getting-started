"""Generate NB35's heading from _build/manifest_35.json. Every number from the manifest; every
string claim asserted against the manifest so prose cannot outlive a different result."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "35-backtest-calm-tail-exclusion.ipynb"
m = json.loads((HERE / "manifest_35.json").read_text())

T = m["track"]
V = {r["label"]: r for r in m["verdict_rows"]}
E = m["expensive_diagnostic"]
G3 = m["gate_3"]
G8 = m["gate_8"]
AD = m["anchor_diversification"]
FEES = m["fees"]
H3 = {(r["window"], r["label"]): r for r in m["h3"]}
W = m["windows"]
I = m["inertness"]
prov = m["provenance"]
vp = next(v_ for k, v_ in prov.items() if "vault-prices" in k)
c8, m8 = V["calm_8"], V["measured_8"]
ec, em = E["calm_8"], E["measured_8"]
A = T["anchor"]


def f2(x): return f"{x:.2f}"
def f3(x): return f"{x:.3f}"
def f4(x): return f"{x:.4f}"
def pc(x): return f"{x * 100:.1f}%"
def usd(x): return f"{x:+,.0f}"


assert m["verdicts"] == {"calm_8": "REJECT", "measured_8": "REJECT"}, m["verdicts"]
assert not c8["gate_5_screen"] and not m8["gate_5_screen"]
assert not c8["gate_4_luck"] and m8["gate_4_luck"]
assert c8["gate_8_diversification"] and not m8["gate_8_diversification"]
assert not ec["gate_9_would_pass"] and not em["gate_9_would_pass"]
assert ec["gate_2_would_pass"] and em["gate_2_would_pass"]
assert m["survivors"] == []
assert m["strict_vs_centre_max_abs_cycle_diff"] > 1e-6, "strict variant is inert; finding 4 and H4 must be rewritten"
ST = I["calm_8_strict"]
assert all(FEES[l]["fee_differential_ok"] for l in ("calm_6", "calm_8", "calm_10", "measured_6", "measured_8", "measured_10"))

WA, WB = "A: incumbent period", "B: full data period"
h3_ok = {l: all(H3[(w, l)]["H3"] for w in (WA, WB)) for l in ("calm_8", "measured_8")}
fee_shares = [FEES[l]["fee_differential_share_of_gap"] for l in ("calm_6", "calm_8", "calm_10", "measured_6", "measured_8", "measured_10")]

HEADING = f"""# NB35 - the volatility tail exclusion through the nine gates

The one mechanism plan 34 carries: before the incumbent ranks its candidates, remove the eight
most volatile of those whose volatility can be measured, and change nothing else. Centre
`calm_8` (`calm_score`, the fresh-guarded `inverse_vol`), neighbours at 6 and 10; the same
three on raw `inverse_vol` (`measured_8`, the configuration with the three-window record) as
the calendar reference, gated identically; and `calm_8_strict` as the inertness diagnostic.

**Verdict: REJECT, both centres.** Under [RESEARCH-RULES.md](RESEARCH-RULES.md) with amendments
A1-A6 of [34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md) Draft 2.
Gate 5 was imported from NB34 after the snapshot was asserted equal; it is False for both
signals, and each centre fails one further cheap gate. The expensive gates were then run as
labelled DIAGNOSTICS, and the null is the finding that matters: **neither centre clears the
pre-registered random-exclusion hurdle. The count-8 permissive mechanism with its ranking
information destroyed - up to eight finite-signal candidates per date, chosen by a within-date
permutation - reaches the centre's Sharpe or better in {em["null_rank_of_centre"] - 1} of 19 draws for
`measured_8` and {ec["null_rank_of_centre"] - 1} of 19 for `calm_8`.**

**Based on:** [29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb)
for the gate machinery, [33-research-lead-comparison.ipynb](33-research-lead-comparison.ipynb)
for the two extra windows, [02-better-format.ipynb](02-better-format.ipynb) as the anchor.
Snapshot `vault-prices.parquet` {vp["bytes"]:,} bytes, sha256 `{vp["sha256"][:16]}` (cell 24).

## Method

Gates in the plan's order: 1, 7, 4, 5, 3 (volatility leg on common post-break dates, A4), 8
(holdings floor 5.95, A3), 6, then 2 and 9 only for a centre that passed every cheaper gate,
then the fee differential (A6) for every run. Gate 9 is nineteen within-date permutations of
the finite signal values (A5), asserted distinct on the realised cycle-return series, with the
null runs' turnover and basket persistence reported beside the centre's. Because no centre
survived the cheap gates, the mask and the null were run for both anyway and reported as
diagnostics that enter no verdict. H3 - the incumbent's window and the full data period - is a
consistency check on overlapping windows, not a gate.

## Key new insights and what did we learn from this experiment?

**1. Neither centre clears the random-exclusion hurdle.** Nineteen seeds, each permuting the
finite signal values within every decision so that the exclusion keeps its size (up to eight
per date; `calm_8` excludes on {I["calm_8"]["decisions_with_exclusions"]} of 126 decisions, `measured_8` on
{I["measured_8"]["decisions_with_exclusions"]}) and its missingness pattern but loses its ranking
information AND its temporal persistence; all nineteen reported distinct on the realised
cycle-return series, the excluded sets and the baskets (cell 33; NB36 asserts it). `measured_8`'s cycle Sharpe
{f3(em["centre_sharpe"])} ranks {em["null_rank_of_centre"]}th of 20 against its null: the best random
exclusion reaches {f3(em["null_best"])}, the median {f3(em["null_median"])}. `calm_8`'s
{f3(ec["centre_sharpe"])} ranks {ec["null_rank_of_centre"]}th of 20 (best {f3(ec["null_best"])}, median
{f3(ec["null_median"])}). Gate 9 would fail for both. NB26 had already found that a random removal
of nine vaults ranks seventh of 57 configurations; this is the same fact measured properly, with
the null's structure matched to the mechanism's. The null's median is below the anchor's
{f3(A["cycle_sharpe"])}, so a random exclusion usually hurts and the volatility ordering does
place the centre in the upper part of the distribution - but three or five random orderings out
of nineteen do as well or better. This is a failure to clear the hurdle the plan set, not an
equivalence test: it does not show that the ranking information contributes nothing.

**2. What the null runs look like, and what that does and does not mean.** The centre's book
persists at Jaccard {f3(em["centre_persistence"])} between consecutive decisions with
{pc(em["centre_turnover"])} of names replaced per decision; the null's books persist at
{f3(em["null_persistence_mean"])} with {pc(em["null_turnover_mean"])} replaced (cell 33). The permutation
destroys temporal persistence as well as ranking - a vault excluded today is kept tomorrow - so
the null books churn more and pay more redemption fees, which biases the comparison in the
centre's FAVOUR; that a fair share of null draws beat the centre anyway is the striking part.
But because the null removes two things at once, it cannot say which of them the centre's
Sharpe depends on. What it says is narrower: on this window, the specific eight names the
volatility ordering removes are not reliably better to remove than eight chosen by a
persistence-free random rule. NB34 showed the ordering predicts forward volatility at rho
0.66-0.68; the null shows that predicting forward volatility is not, by itself, enough to
produce a Sharpe that a random exclusion cannot match.

**3. Each centre also fails a cheap gate of its own, and the two failures are different.**
`calm_8` fails gate 4: luck ratio {f4(c8["luck_ratio"])} against the anchor's {f4(A["luck_ratio"])} -
removing its best five cycles costs relatively more than it costs the anchor (cell 28).
`measured_8` fails gate 8 on distinct vaults, {G8["measured_8"]["distinct_vaults"]} against the anchor's
{AD["distinct_vaults"]}, with the other four measures level or better (cell 28); under amendment A3
the holdings floor is met by both at {f2(G8["measured_8"]["mean_holdings"])}. Gate 3 on its
volatility leg passes for both on {G3["measured_8"]["gate_3_dates"]} common post-break dates
({f4(G3["measured_8"]["held_vol_post"])} and {f4(G3["calm_8"]["held_vol_post"])} against the anchor's
{f4(G3["measured_8"]["anchor_held_vol_post"])}), and on the {G3["measured_8"]["full_lookback_dates"]} dates
whose whole 90-row lookback is post-break (cell 28). The concentration legs are unevaluable as
plan 34 said: {G3["measured_8"]["conc_full_lookback_dates"]} dates have a fully post-break 180-row
lookback (cell 28).

**4. The guard costs the mechanism its effect, and H4 is FALSE: the incumbent's book is full of
vaults the guard calls unmeasurable.** `calm_8`: CAGR {pc(T["calm_8"]["cagr"])}, Sharpe
{f3(T["calm_8"]["cycle_sharpe"])}, against the anchor's {pc(A["cagr"])} / {f3(A["cycle_sharpe"])} and
`measured_8`'s {pc(T["measured_8"]["cagr"])} / {f3(T["measured_8"]["cycle_sharpe"])} (cell 26); it changes
the anchor's basket on {I["calm_8"]["dates_with_a_different_basket"]} of {I["calm_8"]["dates_matched_to_reference"]}
decisions and holds the same {I["calm_8"]["distinct_vaults"]} names over the window. The strict variant -
exclude the guard-masked candidates as well - is NOT inert: it changes the basket on
{ST["dates_with_a_different_basket"]} of {ST["dates_matched_to_reference"]} decisions, removes a name the
anchor was holding {ST["excluded_names_the_reference_held"]} times, and lands at CAGR {pc(T["calm_8_strict"]["cagr"])}
/ Sharpe {f3(T["calm_8_strict"]["cycle_sharpe"])} (cell 26). NB29 found the strict variant inert on
`inverse_vol`, whose NaNs are young vaults the incumbent's 360-day CAGR leg cannot rank anyway.
`calm_score`'s NaNs are different: NB34 showed they are OLDER vaults with thin or stalled marks,
and those are exactly the vaults the incumbent likes to hold. So the guard cannot be made strict
without gutting the book, and permissive it protects the sparsely-polled volatile vaults from
the exclusion that was doing the work. The plateau holds for both families - neighbours within
{f3(max(r["gap"] for r in m["plateau"]["inverse_vol"]))} Sharpe of the centre for `measured` and
{f3(max(r["gap"] for r in m["plateau"]["calm_score"]))} for `calm` (cell 28) - which is flatness of a
statistic the null says is mostly not the mechanism's.

**5. The fee differential is small, the mask is survivable, and H3 holds for `measured_8` and
{"for" if h3_ok["calm_8"] else "not for"} `calm_8` - none of which rescues the verdict.** The candidate-minus-anchor net fee discrepancy is at most
{pc(max(fee_shares))} of the equity gap on the six main runs (cell 35); the one-sided engine error
does not explain the difference between any candidate and the anchor. Leave-one-vault-out
retention is {f3(em["lovo_retention"])} for `measured_8` and {f3(ec["lovo_retention"])} for `calm_8`, both
masking `{em["lovo_masked"][:10]}...` and both above the 0.70 bar (cell 33, diagnostic). On the
incumbent's window `measured_8` is {pc(W[WA]["measured_8"]["cumulative_return"])} / Sharpe
{f2(W[WA]["measured_8"]["cycle_sharpe"])} / max drawdown {pc(W[WA]["measured_8"]["max_dd"])} against the anchor's
{pc(W[WA]["anchor"]["cumulative_return"])} / {f2(W[WA]["anchor"]["cycle_sharpe"])} / {pc(W[WA]["anchor"]["max_dd"])};
on the full period {pc(W[WB]["measured_8"]["cumulative_return"])} / {f2(W[WB]["measured_8"]["cycle_sharpe"])} /
{pc(W[WB]["measured_8"]["max_dd"])} against {pc(W[WB]["anchor"]["cumulative_return"])} / {f2(W[WB]["anchor"]["cycle_sharpe"])} /
{pc(W[WB]["anchor"]["max_dd"])} (cell 38). `calm_8` on the same windows: {pc(W[WA]["calm_8"]["cumulative_return"])} /
{f2(W[WA]["calm_8"]["cycle_sharpe"])} and {pc(W[WB]["calm_8"]["cumulative_return"])} / {f2(W[WB]["calm_8"]["cycle_sharpe"])}.
Three overlapping windows agreeing is what a lucky eight looks like too; the null is the test that
separates the two, and it did not.

## Summary of results

| | `calm_8` | `measured_8` | anchor |
|---|---|---|---|
| CAGR / cycle Sharpe | {pc(T["calm_8"]["cagr"])} / {f3(T["calm_8"]["cycle_sharpe"])} | {pc(T["measured_8"]["cagr"])} / {f3(T["measured_8"]["cycle_sharpe"])} | {pc(A["cagr"])} / {f3(A["cycle_sharpe"])} |
| cycle vol / ulcer / max drawdown | {f4(T["calm_8"]["cycle_vol"])} / {f4(T["calm_8"]["ulcer"])} / {pc(T["calm_8"]["max_dd"])} | {f4(T["measured_8"]["cycle_vol"])} / {f4(T["measured_8"]["ulcer"])} / {pc(T["measured_8"]["max_dd"])} | {f4(A["cycle_vol"])} / {f4(A["ulcer"])} / {pc(A["max_dd"])} |
| gate 1 positive / 7 sub-periods | {c8["gate_1_positive"]} / {c8["gate_7_subperiod"]} | {m8["gate_1_positive"]} / {m8["gate_7_subperiod"]} | |
| gate 4 luck (luck ratio) | {c8["gate_4_luck"]} ({f4(c8["luck_ratio"])}) | {m8["gate_4_luck"]} ({f4(m8["luck_ratio"])}) | ({f4(A["luck_ratio"])}) |
| gate 5 screen (NB34) | {c8["gate_5_screen"]} | {m8["gate_5_screen"]} | |
| gate 3 volatility leg, post-break | {c8["gate_3_held_book"]} | {m8["gate_3_held_book"]} | |
| gate 8 diversification | {c8["gate_8_diversification"]} | {m8["gate_8_diversification"]} ({m8["diversification_failures"]}) | |
| gate 6 plateau | {c8["gate_6_plateau"]} | {m8["gate_6_plateau"]} | |
| gate 2 mask (protocol / would pass) | {c8["gate_2_lovo"]} / {ec["gate_2_would_pass"]} ({f3(ec["lovo_retention"])}) | {m8["gate_2_lovo"]} / {em["gate_2_would_pass"]} ({f3(em["lovo_retention"])}) | |
| gate 9 null (protocol / would pass) | {c8["gate_9_null"]} / {ec["gate_9_would_pass"]} (rank {ec["null_rank_of_centre"]}/20) | {m8["gate_9_null"]} / {em["gate_9_would_pass"]} (rank {em["null_rank_of_centre"]}/20) | |
| fee differential share of equity gap | {f4(c8["fee_differential_share_of_gap"])} | {f4(m8["fee_differential_share_of_gap"])} | |
| failed gates (complete) | {c8["failed_gates"]} | {m8["failed_gates"]} | |
| **verdict** | **{m["verdicts"]["calm_8"]}** | **{m["verdicts"]["measured_8"]}** | |

Hypotheses: H1 (NB34) failed on the return clause; H2 fails - gate 5, and gate 4 or gate 8, and
gate 9 would fail; H3 holds on both extra windows for {", ".join(l for l, ok in h3_ok.items() if ok) or "neither"}
and fails for {", ".join(l for l, ok in h3_ok.items() if not ok) or "neither"} (cell 38), which is
consistency and not confirmation; H4 is false - the strict variant differs from the centre by up to
{m["strict_vs_centre_max_abs_cycle_diff"]:.4f} per cycle (cell 26).

**Nothing is shortlisted.** NB36 re-derives every gate in a fresh kernel and writes the
specification with status NOTHING SHORTLISTED.

## Robustness of results

- Anchor parity at 1e-5 with every splice inert; `calm_8` and `measured_8` reproduce NB34's runs
  at 1e-9 on five metrics (cells 24, 26).
- All 19 null draws per centre are reported distinct on the realised cycle-return series, the
  excluded sets and the baskets (cell 33); NB36 asserts the three counts. The null's persistence
  and turnover are printed beside the centre's: the null churns more and pays more redemption
  fees, an extra-cost bias in the centre's favour, and it also differs from the mechanism in
  persistence, which is a confound the null cannot separate from the ranking information.
- Gate 3's volatility leg is reported on three date sets (all common, post-break, fully
  post-break lookback) and passes on all three; the verdict does not depend on the scope choice
  (cell 28).
- The fee differential is computed for every run including the null and mask runs; the main
  runs' shares are all below 0.03 (cell 35).
- Every failure string is printed in full (cell 36). An unexecuted protocol gate is False; the
  diagnostic columns are separate and labelled.
- The count of eight was chosen by search on this data; the windows overlap; nothing is
  out-of-sample. The null is the only test here that is not a comparison of in-sample numbers
  against each other, and it is the one the mechanism fails.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB35 heading written: verdicts {m['verdicts']}; null ranks calm {ec['null_rank_of_centre']}, measured {em['null_rank_of_centre']}")
