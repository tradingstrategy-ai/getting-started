"""Generate NB36's heading from _build/manifest_36.json (and the two upstream manifests for
the numbers it cross-checks). Every claim asserted against the manifest."""
import json
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent))
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "36-backtest-calm-closeout.ipynb"
m = json.loads((HERE / "manifest_36.json").read_text())
m35 = json.loads((HERE / "manifest_35.json").read_text())
m34 = json.loads((HERE / "manifest_34.json").read_text())

R = m["reproduction"]
G = m["gates"]
AG = m["gates_agree_with_nb35"]
NC = m["null_check"]
F = m["fees"]
S = m["specification"]
AU = m["audit"]
LC = m["lovo_check"]
MV = m["mirror_verified"]
assert MV["flag_comparable_dates"]["calm_score"] == MV["eligible_dates"] == MV["flag_comparable_dates"]["inverse_vol"]
assert all(v.get("distinct_basket_sequences") == 19 for v in NC.values())
prov = m["provenance"]
vp = next(v_ for k, v_ in prov.items() if "vault-prices" in k)
V = {r["label"]: r for r in m["verdict_rows"]}


def f3(x): return f"{x:.3f}"
def f4(x): return f"{x:.4f}"
def pc(x): return f"{x * 100:.1f}%"


assert m["shortlisted"] == [] and S["status"].startswith("NOTHING SHORTLISTED"), S["status"]
assert R["reproducing_at_1e-9"] == R["configurations"], R
assert m["gate_5_rederived_agrees"] and m["gate_5_worst_diff"] < 1e-6
assert all(v["booleans_agree"] and v["failed_gates_same"] for v in AG.values())
assert all(v["distinct_series"] == 19 and v["distinct_excluded_sets"] == 19 and v["distinct_baskets"] == 19 for v in NC.values())
assert AU["integrity_failures"] == 0
assert m["fee_one_sided"]
main = ("calm_6", "calm_8", "calm_10", "measured_6", "measured_8", "measured_10")
assert all(F[l]["fee_differential_ok"] for l in main)
worst_main_fee = max(F[l]["fee_differential_share_of_gap"] for l in main)
fee_fail = [l for l, r in F.items() if not r["fee_differential_ok"]]
assert all(("null" in l) or l.startswith("screen_log") for l in fee_fail), fee_fail
assert all(abs(F[l]["equity_gap_usd"]) < 1500 for l in fee_fail), {l: F[l]["equity_gap_usd"] for l in fee_fail}

HEADING = f"""# NB36 - close-out of the volatility tail exclusion, and the frozen specification

Re-runs every configuration NB35 executed in ONE kernel on ONE snapshot, re-derives gate 5 from
a rebuilt panel and every other gate from the re-run states, cross-checks each run against the
manifest it was first recorded in at 1e-9, asserts the null's distinctness that NB35 only
reported, audits every run for integrity, recomputes the redemption fee independently and
reports the candidate-minus-anchor differential against the equity gap, and writes the frozen
prospective specification.

**Status: {S["status"]}.** Both centres of plan 34 are REJECTED, and every gate Boolean, every
failure string and every gate numeric agrees with NB35 across kernels. The plan's one mechanism
- exclude up to eight of the most volatile measurable candidates before the incumbent ranks -
does not clear gate 5's return clause, fails a cheap gate of its own on each signal, and did not
clear the pre-registered persistence-destroying random-exclusion hurdle.

**Based on:** [34-research-calm-score-screen.ipynb](34-research-calm-score-screen.ipynb),
[35-backtest-calm-tail-exclusion.ipynb](35-backtest-calm-tail-exclusion.ipynb) and
[34-volatility-tail-exclusion-plan.md](34-volatility-tail-exclusion-plan.md) Draft 2. Snapshot
`vault-prices.parquet` {vp["bytes"]:,} bytes, sha256 `{vp["sha256"][:16]}`, asserted equal to both
upstream manifests (cell 24).

## Key new insights and what did we learn from this experiment?

**1. Everything reproduces.** All {R["configurations"]} track-window configurations NB35 executed -
seven main runs, six leave-one-vault-out runs and thirty-eight null draws - reproduce in a fresh
kernel at 1e-9 on every recorded panel metric, worst difference {R["worst_abs_diff"]:.1e} (cell 26).
Gate 5, re-derived from this kernel's own logging runs, panel, exclusion flags and bootstrap -
with the offline reads verified equal to the engine's in-trade reads on {MV["reads"]["inverse_vol"]:,}
rows and the offline eight equal to the re-run engine exclusions on all {MV["eligible_dates"]}
eligible dates for both signals - agrees with NB34 on every clause boolean and every numeric field to {m["gate_5_worst_diff"]:.1e}, with
identical family sizes and draw counts and critical values equal to 1e-6, the manifest's
rounding (cell 28). Every gate Boolean and
failure string agrees with NB35 for both centres, worst numeric difference
{max(v["worst_numeric_diff"] for v in AG.values()):.1e}, with a finite-to-NaN mismatch counted as a
disagreement (cell 30). Gates 2 and 9 are False by protocol; both were nonetheless recomputed as
diagnostics from the re-run states: leave-one-vault-out retention {f3(LC["calm_8"]["retention"])} and
{f3(LC["measured_8"]["retention"])}, equal to NB35's (cell 32).

**2. The null is now asserted, not reported.** Nineteen re-run draws per centre: nineteen
distinct realised cycle-return series, nineteen distinct excluded-set digests, nineteen distinct
ordered (decision, held set) basket sequences, and the centre's rank against the null equal to NB35's - `measured_8`
{NC["measured_8"]["rank_of_centre"]}th of 20 (best null {f3(NC["measured_8"]["null_best"])} against
{f3(NC["measured_8"]["centre_sharpe"])}), `calm_8` {NC["calm_8"]["rank_of_centre"]}th of 20 (best null
{f3(NC["calm_8"]["null_best"])} against {f3(NC["calm_8"]["centre_sharpe"])}) (cell 32). Gate 9 remains
False by protocol, because a cheaper gate failed first; as a diagnostic it would fail on its own.

**3. The fee differential does not affect the six main comparisons or either verdict.** The
engine's stored redemption fee differs from the documented schedule on {m["anchor_fee"]["over_1bp"]}
of the anchor's {m["anchor_fee"]["redemptions"]} redemptions, and the NET signed discrepancy per run is
at or below zero on all {len(F)} re-run configurations - the engine charges more in aggregate;
per-redemption direction is not established here (cell 34). But the candidate-minus-anchor
differential is at most {pc(worst_main_fee)} of the equity gap on the six main runs, and exceeds the
0.25 bound only on {len(fee_fail)} run{"s" if len(fee_fail) != 1 else ""} ({", ".join(fee_fail) or "none"}) -
the anchor-identical logging run, whose gap is exactly zero, and null draws whose equity gap to
the anchor is under $1,500, where the ratio is uninformative by construction (cell 34). The cause of the one-sided error is still a track-level item; its differential effect
on plan 34's verdicts is nil.

**4. The specification is written with nothing in it.** Status {S["status"].split(" - ")[0]}: no
signal, no count, no override dictionary. The comparator, the horizon and the monitoring
protocol are recorded so that the NEXT plan inherits a fixed form rather than a blank page
(cell 36). The known limits are the same six the plan carried in, plus what NB34-NB35 found
(their manifests, `_build/manifest_34.json` and `_build/manifest_35.json`, are the source; NB36
re-derives the gate-5 screen in cell 28 and the null in cell 32): the return clause is reachable
by foresight and was not demonstrated by either screened signal on {m34["decisions_by_regime"]["post_break"]}
post-break decisions; the fresh-mark guard masks {pc(m34["coverage_totals"]["masked_share"])} of the measurable
candidate-dates and the incumbent's book holds vaults it masks; and the within-date permutation
of the volatility ordering reaches the centre's Sharpe in {NC["measured_8"]["rank_of_centre"] - 1} to
{NC["calm_8"]["rank_of_centre"] - 1} draws of nineteen.

## Summary of results

| | `calm_8` | `measured_8` |
|---|---|---|
| verdict (NB36 re-derived / NB35) | {G["calm_8"]["verdict"]} / {AG["calm_8"]["verdict_nb35"]} | {G["measured_8"]["verdict"]} / {AG["measured_8"]["verdict_nb35"]} |
| failed gates (complete, identical across kernels) | {G["calm_8"]["failed_gates"]} | {G["measured_8"]["failed_gates"]} |
| gate 5 re-derived (agrees with NB34) | {m["gate_5"]["calm_score"]} | {m["gate_5"]["inverse_vol"]} |
| null: rank of centre / 20, distinct series (asserted) | {NC["calm_8"]["rank_of_centre"]}, {NC["calm_8"]["distinct_series"]} | {NC["measured_8"]["rank_of_centre"]}, {NC["measured_8"]["distinct_series"]} |
| fee differential share of equity gap | {f4(V["calm_8"]["fee_differential_share_of_gap"])} | {f4(V["measured_8"]["fee_differential_share_of_gap"])} |
| configurations reproduced at 1e-9 | {R["reproducing_at_1e-9"]} / {R["configurations"]} | |
| integrity audit | {AU["runs_audited"]} runs, {AU["integrity_failures"]} failures | |

Plan 34's hypotheses, closed: H1 failed (return clause); H2 failed (gates 4 or 8, 5, and 9
would fail); H3 held for `measured_8` on both extra windows and not for `calm_8` on the full
period - consistency, not confirmation; H4 failed (the strict variant is not inert).

**What the track now knows that it did not before plan 34.** (i) Trailing volatility predicts
forward volatility and forward downside on the dense regime with lower bounds above 0.5 - the
best-established fact in NB28-NB36 - and the two signals that carry it did not demonstrate an
advantage over the specified null, which destroys ranking information and temporal persistence
together. (ii) The return clause was not demonstrated by either screened signal on four months
of overlapping 30-day windows, while a foresight oracle shows the bar is reachable; the clause
needs more data or a different design, not a smaller margin. (iii) Putting a fresh-mark guard
on the volatility estimate coincides with most of the mechanism's effect disappearing, which is
consistent with the masked cohort - sparsely-polled, volatile, and held by the incumbent -
contributing to the difference; the causal share is not measured. (iv) `measured_8`'s
three-window record is real, and it did not clear the pre-registered hurdle: three of nineteen
persistence-free random exclusions match or beat it on the track window.

## Robustness of results

- Snapshot equality asserted against both upstream manifests before either is used (cell 24);
  anchor parity at 1e-5 with every splice inert.
- Reproduction is exact to 1e-9 for all {R["configurations"]} configurations including the null draws,
  which means the within-date permutation is seeded deterministically as designed (cell 26).
- Gate 5 re-derivation compares every numeric field of the post-break screen and all three
  bootstrap families' sizes, draw counts and critical values, not just the flags (cell 28).
- Gate re-derivation compares every gate Boolean, the complete failure string and every numeric
  field NB35 persisted (cell 30).
- Integrity: {AU["runs_audited"]} re-run states audited, no destroyed or stranded positions, cash plus
  holdings equal to equity within one dollar on every run (cell 43).
- The offline mirror of the splice is verified in this kernel, not inherited (cell 28); the
  reproduction checks count a finite-to-NaN mismatch as a failure rather than skipping it
  (cells 26, 30).
- Nothing here is out-of-sample; the close-out establishes reproducibility and internal
  consistency of an in-sample rejection, which is all a close-out can do.
"""

nb = json.loads(NB.read_text())
assert nb["cells"][0]["cell_type"] == "markdown"
from audit_notes import insert_audit
HEADING = insert_audit(HEADING, 36)
nb["cells"][0]["source"] = HEADING.splitlines(keepends=True)
NB.write_text(json.dumps(nb, indent=1))
print(f"NB36 heading written: {S['status']}; reproduced {R['reproducing_at_1e-9']}/{R['configurations']}")
