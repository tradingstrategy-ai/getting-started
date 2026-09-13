# Stability leads plan: what actually stabilised the curve, and can the marks be trusted

- **Status**: EXECUTED, NOTHING ADOPTED. All five notebooks ran clean, NB20-NB24, committed
  individually. No run passes all seven constraints of adoption rule v3. Two runs (`drop_30`,
  `drop_35`) have an empty failure set under constraints 1-6 with the late period holding, and
  neither is plateau-supported, so `simple_rule_eligible` is empty and leave-one-vault-out was
  never triggered anywhere in the plan. Family-wise p = 0.813 over the complete 35-run family.
  The three leads are settled; three limitations of the rule itself are recorded below and were
  NOT retuned after the fact.
- **Track**: `hyperliquid-lower-vol`, notebooks NB20-NB24. Follows
  [14-evidence-weighted-plan.md](14-evidence-weighted-plan.md) (NB14-NB19, NOTHING ADOPTED, all
  seven notebooks independently reviewed) and the age-barrier audit in
  [13-research-age-barrier.ipynb](13-research-age-barrier.ipynb).
- **Baseline to beat**: [02-better-format.ipynb](02-better-format.ipynb), re-run as the anchor in
  every notebook. Full-precision baseline metrics are stored in `_build/harness_stability.py`
  (`BASELINE`) with explicit tolerances; the heading figures 37.90% CAGR, cycle Sharpe 2.160,
  cycle vol 0.1543, ulcer 1.80%, beta 0.046, 578 trades, $186,746 are rounded from those.
- **Every historical result in this plan is exploratory and in-sample.** ADOPT means *admission to
  the frozen prospective shadow protocol* (NB24), not authorisation to deploy capital. The full
  window has informed several rounds of research already; no chronological split inside it is
  out-of-sample.
- **Data provenance**: each notebook prints SHA-256 content hashes of the vault price archive, the
  vault metadata snapshot, the universe cache file and the Binance reference-price store, plus the
  git commit of `_build/`. All NB14-NB19 runs served from one cached download (2026-09-09); a
  refreshed download of the same historical period is not independent evidence, and a changed
  metadata snapshot can change universe membership (deposit-closed status, peak TVL) - a known
  point-in-time limitation of this whole track, stated rather than solved here.
- **Question**: the previous plan found that nothing "smart" beat plain volatility avoidance, that
  the one screen-passing score collapsed in a real backtest, and that the change most likely to
  keep the anchor's return - swapping one leg of the composite - was never run. This plan tests
  those three leads, after first checking that the risk measures they are judged against are
  reading real trading rather than absent reporting.

This file is written to be executed by an agent that has not read the rest of the track.

## The three leads

| # | Lead | Where it came from | What would make it a result |
|---|---|---|---|
| 1 | **The vol-matched drop family, promoted from control to candidate.** `vol_matched_drop_50` delivered vol 9.5%, ulcer 1.45%, beta 0.002, Sharpe 2.01, fully invested, for 17 pp of CAGR - better on every risk axis than any mechanism the previous plan built. It was never plateau- or leave-one-vault-out checked because it was the control. | NB15, NB19 | A contiguous run of N values that all pass constraints 1-6 and the late period, with leave-one-vault-out holding at the centre. Promoting a control after seeing its result is itself a selection; the notebook records a `simple_rule_eligible` flag, and ADOPT still means only admission to the shadow. |
| 2 | **Complementary downside selection, in place of a named exclusion list.** The curve is unstable because the six holdings lose on the same days. Rank by the incumbent composite, take the top P, keep the six with the lowest `P(vault down | cohort down)`, and leave sizing alone. The exclusion-list derivation survives as a read-only diagnostic. | NB15 review, Codex review idea 2 | The centre passes all seven constraints, the late period, the plateau over P and the window sensitivity, leave-one-vault-out holds, AND the realised within-basket joint-loss concentration falls against the anchor. The last of those is the point; passing the constraint table while the basket still sinks together would mean the proxy failed. |
| 3 | **The minimal change nobody ran.** NB14/NB16 found the *evidence-shrunk* CAGR leg hurt; NB31 found the incumbent's *360-day* CAGR leg is load-bearing. Keep the incumbent's CAGR leg and swap only the 45-day Sortino leg for `sortino_shrunk_score`. | NB16 review, NB31 | First, a measurement audit and an identity diagnostic showing the swap actually changes the book; then, only if it does, a local sensitivity sweep and the seven constraints, plateau and leave-one-vault-out. The swap cannot reach young vaults; it re-ranks the old cohort. |

## Rules for the executing agent

The previous plan's rules plus what its seven post-execution reviews and this plan's review taught.

1. **Never select or tune towards a vault by name.** NB22 names vaults only in a read-only
   diagnostic; no run in this plan is configured from a list of identities.
2. **Never change a pre-registered threshold after seeing a result.** Record a badly placed one in
   the Robustness section and leave it.
3. **Build from `_build/`** with a `build_NN.py` importing `builder.py`; never hand-edit a code
   cell. Shared additions go in `_build/blocks_stability.py` and `_build/harness_stability.py`;
   nothing in `blocks_evidence.py`, `harness_evidence.py` or the NB03-track files changes.
   Read-only logging MAY be spliced into `decide_trades` through track-local replacements,
   provided anchor trades and equity remain identical (rule 4).
4. **Anchor parity every notebook**, against `BASELINE` at full precision with its tolerances, not
   against rounded heading figures. If it fails, stop and report.
5. **Print the `failed` column in full** and **write every heading claim from the full string**.
   Report the complete failure set for every row; a `first_failure` summary field is optional.
   Fail closed on any non-finite required metric and name it in the failure string.
6. **Every numeric claim in a heading cites the cell it comes from.**
7. **`runs` plus `run_by_label` is the only source for every table**; unique labels; every
   control and every family member goes through the same `run_and_record()`, so each retains its
   state, equity, returns and diagnostic logs.
8. **Diagnostic logs** (`VOL_DROP_LOG`, `COMPLEMENT_LOG`, `SLEEVE_LOG`) are cleared before each run and snapshotted
   into that run's record afterwards; assert unique decision timestamps and expected coverage.
9. **Adoption logic complete from the first run**: eligibility, constraints, late period, plateau,
   leave-one-vault-out, with each Boolean listed separately. A required robustness run that was
   skipped, failed or is unavailable cannot produce a passing flag.
10. **Run with the observable runner** from the repository root (command in the previous plan);
    at most three notebooks concurrently.
11. **Headings** carry the three standard sections, UK English, sentence case, verdict word in the
    first insight bullet, the provenance hashes, and are reviewed independently after the run
    before anything is called a result. Commit per notebook; post nothing to the PR unless asked.

## Objective and adoption rule (v3 for this plan)

Constraints 1-6 are adoption rule v2's, unchanged, via `_build/harness_evidence.py`: CAGR >= 20%;
cycle Sharpe >= anchor - 0.10; cycle vol <= anchor; ulcer <= 0.85 x anchor; invested-basket beta <
anchor; mean invested >= 0.90. Robustness: plateau, leave-one-vault-out by full re-simulation with
the largest contributing vault masked, `late_cagr > 0` and `late_ulcer < anchor late_ulcer`. All
of these apply to the centre, to every specified neighbour, and to the masked centre; the
notebook lists each Boolean separately.

**Constraint 7 is redefined for this plan** (review finding 7: the previous linear interpolation
between realised strategies is neither an observed control nor an executable mixture, and its
"not evaluable" region excluded the near-anchor volatility band from comparison). The comparator
is the **best observed control at or below the candidate's volatility**:

```python
def placebo_ref_observed(family: pd.DataFrame, vol: float) -> float:
    """Highest cycle Sharpe among vol-matched family members with cycle_vol <= vol.

    No interpolation. A candidate quieter than every family member is compared against the
    quietest member (the closest observed control), never marked unevaluable; a candidate noisier
    than every member is compared against all of them. `family` is the pre-registered vol-matched
    family at 5-step spacing, N in {0, 5, ..., 60} (61 members is the 5-step grid; N=0 is the
    anchor), run through `run_and_record()` in the same kernel as the candidates.
    """
    at_or_below = family[family["cycle_vol"] <= vol]
    if len(at_or_below) == 0:
        at_or_below = family.nsmallest(1, "cycle_vol")
    return float(at_or_below["cycle_sharpe"].max())
```

Constraint 7: `cycle_sharpe >= placebo_ref_observed(family, cycle_vol) + 0.10`. The same
definition and the same family are used in every notebook of this plan. **Lead 1 is the
family**, so for NB21 constraint 7 is a self-comparison (a retained member would need
`S >= S + 0.10`) and is **not applied** (review finding 6: inapplicable, not vacuous); NB21 reports
`passes_1_to_6`, `failed_1_to_6` and `simple_rule_eligible`, never `passes_v3`. NB22 and NB23 must
clear it: a co-movement screen and a re-ranked composite are additional mechanisms and carry a complexity
premium of 0.10 Sharpe over the best observed simple de-risking at their own risk level. That
asymmetry is deliberate and is stated in each notebook's first bullet.

**Uncertainty on the margins that matter.** For every eligible centre (not only near-misses),
report block-bootstrap intervals of the paired cycle-Sharpe difference, with common block indices
across the aligned return matrix, against (a) the anchor - the decision boundary is **-0.10** -
and (b) the observed placebo comparator actually used by constraint 7 - the boundary is **+0.10**.
Block length 10 by default, sensitivity at 5 and 20, seed and draw count printed; regime
sub-period intervals reported as diagnostics, not as independent replications.

**The family-wise check is replaced** (review finding 14). `family_wise_joint()` resamples common
block indices across the aligned matrix of anchor and every candidate's cycle returns, computes
each candidate's Sharpe difference from the anchor per draw, centres each candidate's bootstrap
distribution on its observed difference (the no-difference null), takes the maximum across the
family per draw, and reports `p = (1 + #{max_null >= observed_max}) / (B + 1)` with B = 999 and
the exact family printed. It preserves candidate-anchor and candidate-candidate dependence. It
still cannot erase the adaptive research history behind the family, and NB24 says so.

Verdict words: ADOPT (= admission to shadow) / REJECT / CONTROL / DIAGNOSTIC.

## Shared additions

Both modules are written and verified before any notebook is built:
`_build/verify-stability-splices.ipynb` reproduces `BASELINE`, proves both `decide_trades`
splices are inert on the anchor path, and exercises each new mechanism once.

### `_build/blocks_stability.py`

Adds three things on top of `blocks_evidence.py`, which every stability notebook also splices
(the Sortino leg of lead 3 lives there).

- `VOL_DROP_LOG`, a read-only per-cycle record of what the pre-registered vol-matched drop
  actually removed: pool size, dropped ids and addresses, the inverse-volatility and signal of
  every candidate, and which of the dropped had no volatility estimate at all. NB21's diagnostics
  and NB22's Part A read this rather than reconstructing the decision offline. The review found a
  reconstruction could not mirror `decide_trades` - it would miss `is_good_pair`, the quarantine
  list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, strict admission and the tie order.
- `fresh_daily_return`, `cohort_down_flag` and `joint_loss_frequency`, plus a
  `complementary_pool_size` block in `decide_trades` and `COMPLEMENT_LOG`. NB22's mechanism.
  `joint_loss_frequency` is `P(vault down | cohort down)` over a rolling window, where the cohort
  reference is the cross-sectional median vault return, built the same way as
  `sortino_cross_sectional_prior`. NaN sorts last: no estimate is not evidence of
  complementarity.
- `cagr_sortino_shrunk_weight`, the incumbent composite with only its Sortino leg swapped for
  `sortino_shrunk_score`. NB23's mechanism. It is a component replacement, not an isolated test
  of shrinkage or of event time: the replacement leg changes horizon, shrinkage, scaling and
  saturation at once, and its NaN behaviour differs, so the admitted set is not guaranteed
  identical even though the CAGR gate is.

Both `decide_trades` splices are disabled at their defaults (`vol_matched_drop_count = 0`,
`complementary_pool_size = 0`), so the anchor path never reaches either branch.
`assert_anchor_parity()` asserts that both logs are empty after the anchor run, which is the
evidence rather than the assumption.

### `_build/harness_stability.py`

Appended as its own cell after `harness_evidence.py`'s. Defines `BASELINE` and
`assert_anchor_parity()`; `provenance()` (SHA-256 content hashes of the price archive, metadata
snapshot, Binance store and BTC cache, plus the git commit); `placebo_ref_observed()`;
`passes_constraints_v3()` / `failing_constraints_v3()` / `passes_1_to_6()`, all failing closed on
any non-finite required metric; `late_period_ok_v3()`; `verdict_table_v3()`, which reads `runs`
directly so an executed run cannot be left out of the table that should have judged it;
`bootstrap_paired_sharpe_diff()` and `bootstrap_margin_table()` (common block indices, both
decision boundaries, block lengths 5 / 10 / 20); `family_wise_joint()`; and the run bookkeeping -
`runs`, `run_by_label`, `record_anchor()`, `build_family()`, `family_frame()` and
`run_and_record()`, which clears and snapshots all three diagnostic logs around every run and
asserts unique decision timestamps.

## Experiment track

### NB20 - research: reporting versus trading inactivity (precursor)

**File**: `20-research-mark-quality.ipynb`, `_build/build_20.py`. Verdict word: DIAGNOSTIC.

**Question.** Every risk number in this track - ulcer, cycle volatility, invested beta, Sortino -
is computed from a share-price series that stops moving when a vault stops reporting. A vault
that goes quiet therefore looks stable. Until stale reporting is separated from genuinely flat
trading, the objective function all three leads are judged against may be describing missing
observations rather than economic experience. The review rated this the highest information per
effort on its list, and it costs no backtests beyond the anchor.

**Sections.** A polling-gap census across the tradable cohort, split at the NB57 regime break on
2026-04-01, reporting gap-length distributions and endpoint mark age. Whether a gap predicts a
loss: for every gap of two or more days that ends in a fresh mark, the resuming return, bucketed
by preceding gap length, against the unconditional distribution, with a block-bootstrap interval
and no significance claim from overlapping samples. Recovery shape after a long gap that resumes
negative. How much of this reaches the anchor's own book, by position count, capital and profit.
Finally a sensitivity: the anchor's ulcer and volatility recomputed with cycles that sat inside a
stale window dropped, reported as a sensitivity and never as a corrected value.

**Adopts nothing.** If gaps do predict losses, that finding is a constraint on how every later
notebook's ulcer improvement may be read, and NB24 carries it forward.

### NB21 - backtest: the vol-matched family as a candidate (lead 1)

**File**: `21-backtest-vol-matched-family.ipynb`, `_build/build_21.py`.

**Question.** Is there a stable member of the family that beat everything else? Not "does
de-risking work" - it does - but "is there an N at which it clears Sharpe non-inferiority, holds
across neighbours, and survives leave-one-vault-out". The first bullet of the heading states that
this family is the control the previous plan used, that constraint 7 is inapplicable to it, that
promoting it after seeing its result is a selection, and that ADOPT here means admission to the
shadow only.

**Runs.** The anchor, then `build_family()` - N in {5, 10, ..., 60}, twelve runs, each through
`run_and_record(f"drop_{n}", "candidate", vol_matched_drop_count=n)`. Eligible plateau centres are
N in {10, ..., 55}; 5 and 60 are boundary neighbours only. For every eligible N whose centre and
both 5-step neighbours pass `passes_1_to_6` and `late_ok`, leave-one-vault-out:
`run_and_record(f"drop_{n}__without_top_vault", "robustness", vol_matched_drop_count=n,
masked={largest_contributing_vault(run_by_label[f"drop_{n}"]["state"])})`, which must also pass
`passes_1_to_6` and `late_ok`.

**Diagnostic, from `VOL_DROP_LOG`, not from a reconstruction.** Per N: mean pre-drop pool size;
frequency of the no-drop branch (pool <= N); mean actual removed count `len(dropped_ids)`; mean
`len(dropped_ids) - len(no_estimate_dropped)` (volatile removals actually made); a cross-tab of
removed vaults by (volatility available / missing) x (composite scored / unscored) x (age < 360 d
/ >= 360 d at that date, from NB13's life cache); the Jaccard overlap of `dropped_addresses`
between consecutive decision dates (two empty sets = missing, one empty = 0), reported as a
description of how stable the removed set is - never as a stopping rule.

**Outputs.** `verdict_table_v3(..., skip_placebo=True)` with `passes_1_to_6`, the full `failed`
string, `late_ok`, and `control_ref` shown for information; the plateau table (N, N-5, N+5 each
Boolean); `simple_rule_eligible` per N; `bootstrap_margin_table()` for every eligible centre;
the chart of CAGR, Sharpe, vol, ulcer against N; the diagnostic tables; equity curves of the
anchor and every N with `passes_1_to_6`.

**Verdict.** ADOPT (to shadow) the **smallest** N for which the centre, both neighbours and the
masked centre all pass `passes_1_to_6` and `late_ok`; if several qualify, the smallest N is the
single shadow candidate and the others are listed. Otherwise REJECT, with the binding constraint
per N. If the family clears every risk constraint but Sharpe non-inferiority at every N, the
heading says that de-risking at these settings costs Sharpe *on this window under this rule* -
not that it does so in general, and not if any N failed on CAGR, deployment or plateau instead.

### NB22 - research + backtest: complementary downside selection (lead 2, redirected)

**File**: `22-backtest-joint-downside.ipynb`, `_build/build_22.py`.

**What changed and why.** Draft 2 proposed freezing a named exclusion list derived from the
vaults that leave the book between `drop_20` and `drop_30`. The review's objection stands: that
converts an outcome-selected volatility band into permanent identities, and its own evaluation
design could not separate the names from their risk cohort. The mechanism that survives is the
question underneath it - the equity curve is unstable because the six holdings lose on the same
days - and that is testable directly, generalisably, and without naming anyone. The derivation
work is kept, as a read-only diagnostic, because "who actually leaves between N = 20 and N = 30"
is still an unanswered question about the book.

**Part A, diagnostic: who the volatility count removes.** Run `drop_20` and `drop_30` and read
both `vol_drop_log`s. Report the marginal band `M = (D30 - D20)` per decision date, the frequency
with which each address appears in it, the persistent core at 50 / 75 / 90% of dates, monthly
membership stability, and the cross-tab of the top-15 by age and score availability. Report how
many of them ever displaced a *funded* anchor position. No run is configured from this table.

**Part B, the mechanism.** `joint_loss_frequency` measures, per vault over a rolling window,
`P(vault down | cohort down)` where the cohort reference is the cross-sectional median vault
return. Low means the vault holds up when the rest of the cohort is losing. The
`complementary_pool_size` parameter takes the top P candidates by the incumbent composite and
keeps the `max_assets_in_portfolio` with the lowest joint-loss frequency, leaving sizing and
every other rule untouched. It changes *which* names are held, not how much of each.

**Runs.** The anchor; `build_family()` as the constraint-7 comparator; then
`run_and_record(f"complementary_{p}", "candidate", complementary_pool_size=p)` for P in
{10, 12, 14, 16, 18, 20, 24}, with P = 18 as the pre-registered centre and the rest as the
plateau. Window sensitivity at the centre: `joint_loss_window_days` in {90, 270} and
`joint_loss_min_events` in {5, 20}, four more runs, reported beside the plateau. Leave-one-vault-out
on the centre if the centre and plateau pass.

**The gap between the proxy and the objective, measured not assumed.** `joint_loss_frequency`
scores each candidate against the cohort, not against the other five names actually chosen, so it
cannot see two vaults that are each complementary to the cohort but identical to each other. From
`complement_log` and the realised returns, report for the centre and the anchor: the mean pairwise
joint-loss frequency *within* the chosen basket, the share of decision dates on which the screen
changed the basket, the count of reads with no estimate, and the realised share of cycles in which
four or more of six holdings lost together. If the within-basket concentration is no better than
the anchor's, the proxy failed even where the constraint table passes, and the heading says so.

**Verdict.** ADOPT (to shadow) the centre only if it passes all seven constraints (v3, comparator
= the family), `late_ok`, every plateau neighbour passes, and leave-one-vault-out passes.
Otherwise REJECT with the complete failure set. Report Part A regardless.

### NB23 - backtest: the incumbent composite with only its Sortino leg swapped (lead 3)

**File**: `23-backtest-sortino-leg-swap.ipynb`, `_build/build_23.py`.

**Question.** Does the event-time, shrunk Sortino leg re-rank the old cohort better than the
incumbent's 45-day rolling Sortino? Two stages: first establish that the swap changes the book and
that the score is measuring what it claims; only then sweep.

**Stage 1 - measurement audit of `sortino_shrunk_score` on the candidate pool** (review findings
11-12). Over every decision date and every gated candidate: score validity rate; elapsed
calendar span of the event window (the 90 mark events cover different durations per vault -
report its dispersion across candidates); age of the last *valid* evidence at each read; **how
often the forward-fill in `_event_time_stats` bridges an event date that failed the down-count
mask** (a later window with too few down-events inherits an older valid score - the review found
this in the helper) - if that bridging affects more than 2% of (candidate, date) reads, define a
`_v2` indicator chain in `blocks_stability.py` that masks AFTER the reindex, so an invalidated
window becomes NaN instead of inheriting an older score, and use it for every run in this
notebook, recording the change; clipping frequency at the [0, 1] cap; selected
positions whose score was NaN (admitted at signal 0).

**Stage 1 - identity diagnostic.** Run `swap__centre`
(`selection_score_indicator="cagr_sortino_shrunk_weight"`, admission as the anchor's:
`require_scored_candidates=False`). Against the anchor, per decision date: target-weight L1
distance and realised-weight L1 distance (from `state.stats.positions` values over equity),
whether the traded top-6 sets differ, the symmetric difference size, the active cycle return, and
turnover. Summarise: share of decision dates on which the traded book differs; mean L1 distance;
the contribution of changed holdings to the largest five drawdowns. If the traded book is
identical on every date, the notebook stops with DIAGNOSTIC: the swap is a mechanical replication
of the anchor and the sweep has no information value.

**Stage 2 - sweep, only if the book differs on more than 10% of dates.**

```python
common = dict(selection_score_indicator="cagr_sortino_shrunk_weight")
for label, override in [
    ("cagr_weight_0.5", dict(cagr_weight=0.5)), ("cagr_weight_0.7", dict(cagr_weight=0.7)),
    ("t_cap_2", dict(evidence_t_cap=2.0)), ("t_cap_4", dict(evidence_t_cap=4.0)),
    ("prior_30", dict(evidence_prior_strength=30)), ("prior_90", dict(evidence_prior_strength=90)),
    ("min_events_10", dict(evidence_min_events=10)), ("min_events_30", dict(evidence_min_events=30)),
    ("max_events_60", dict(evidence_max_events=60)), ("max_events_120", dict(evidence_max_events=120)),
]:
    run_and_record(f"swap__{label}", "candidate", **{**common, **override})
run_and_record("swap__require_scored", "policy", **{**common, "require_scored_candidates": True})
```

`cagr_weight` now has an upper neighbour (0.7): an earlier search boundary is not an economic
reason to exclude it. Strict admission is a policy alternative, reported beside the plateau but
not part of it. Plateau = all ten neighbours pass v3 and `late_ok`. Leave-one-vault-out on the
centre if the centre and plateau pass. `bootstrap_margin_table()` for the centre.

**Verdict.** ADOPT (to shadow) only if the centre passes all seven (v3) and `late_ok`, all ten
neighbours pass all seven and `late_ok`, and leave-one-vault-out passes. Otherwise REJECT with
the complete failure set. A near-anchor replication that fails only the 15% ulcer reduction is
reported as exactly that.

### NB24 - close-out

**File**: `24-backtest-closeout.ipynb`, `_build/build_24.py`.

Loads each notebook's frozen manifest (centre labels, neighbours, masks, eligibility flags, NB20's
mark-quality verdict, NB22's Part A table and within-basket result, NB23's stage-1 outcome),
re-runs in one kernel the anchor, the 5-step family, every NB21 `drop_N`, every NB22 and NB23 run
that was executed, and every triggered robustness run; reproduces every gate from the manifests
(it does not trust the source notebooks' verdict flags); asserts each centre's Sharpe against a
literal copied from the source notebook; prints the combined `verdict_table_v3()`; the frontier
chart with every run overlaid; `family_wise_joint()` over the complete executed family with its
exact membership printed and the statement that it cannot correct for the adaptive history;
equity curves; NB20's constraint on how any ulcer improvement may be read; and the prospective
shadow specification - start date, fixed comparator (the unchanged anchor on the same decision
dates), monitoring horizon, stopping conditions and decision rule, all fixed before new data
arrive, with the literal override dictionary for any ADOPT. If more than one lead reaches ADOPT,
the shadow runs them side by side; the plan does not rank them.

**Verdict.** ADOPT `<labels>` (to shadow) or NOTHING ADOPTED, plus one sentence per lead on what
it settled and one on what it could not.

## Results

Every figure below is reproduced in NB24 from its own kernel, cross-checked against the frozen
manifests of NB21-NB23 at a tolerance of 1e-9, and matched at a worst difference of exactly zero.

### What each lead settled

| Lead | Verdict | What it settled | What it could not |
|---|---|---|---|
| 0, mark quality (NB20) | DIAGNOSTIC | Stale reporting hides real losses. A gap of five days or more is followed by a resuming mark 119.2 bps below the unconditional mean, CI [-279.5, -14.9], and only 46.0% of those losses recover within 30 days against 74.9% for losses after no gap. | Whether the effect is causal or a reporting convention, and whether the sparse regime differs from the dense one. Its own review corrected an earlier "entirely post-April" reading: sparse is -56.8 bps, the SAME sign, CI [-265.0, +83.5], wide enough to contain a larger effect than dense. That is an absence of power, not an absence of effect. Roughly half the non-recovery may also be definitional, since a vault that stops printing has a forward-filled mark that cannot exceed its pre-gap level by construction. |
| 1, the vol-matched family (NB21) | REJECT | `drop_30` is a spike, not a rule. It has an empty failure set and gains 11.10 pp of CAGR over the anchor (48.99% against 37.90%, Sharpe 2.747 against 2.160, ulcer 1.384% against 1.796%, beta 0.001), and its lower neighbour fails on ulcer and the late period while `drop_40` fails on three constraints. **[26-backtest-drop-decomposition.ipynb](26-backtest-drop-decomposition.ipynb) then settled what was underneath it**, as corrected by its own independent review: the data-availability half reproduces the anchor to six decimals on every reported metric while genuinely removing 21.26 vaults per decision; the volatility half is worth +3.07 pp of CAGR and its edge widens to +3.35 pp under leave-one-vault-out, but its paired bootstrap Sharpe interval against the anchor contains zero at every block length, and three of ten random draws reach a lower ulcer, so only the RETURN edge is attributable to selection. Masking Realist Capital takes `drop_30` to 24.12% against a masked anchor of 23.90%, collapsing an 11.10 pp edge to 0.22 pp - arithmetically decisive, though masking re-simulates every later allocation rather than subtracting one vault's P&L, so it bounds the dependence rather than attributing it. The advantage is confined to the late quarter, and NOT because no volatile vault is removed early: the smallest pre-April unmeasured pool is 17 and `drop_30` removes about 3.9 measured vaults per decision then. The mechanism the log supports is that the unmeasured pool floor falls from 17 to 2 by July, so 22.2 of 30 removals become measured ones exactly when the edge appears. | Whether a plateau exists at a finer spacing than 5. The family was run at 5-step spacing only, and NB26's `measured_only` sweep has had no plateau test or pre-registration. |
| 2, complementary downside selection (NB22) | REJECT | The screen does not reduce co-movement at all. Within-basket pairwise co-loss does fall, 0.2143 to 0.1876, but its review decomposed that against a matched independence benchmark and the WHOLE fall is the marginal down rates dropping: excess over independence is +0.000059 for the anchor, essentially independent, against +0.011750 for the centre, paired difference +0.0117 CI [+0.0040, +0.0228], excluding zero in the WRONG direction. The selected basket co-loses MORE than chance. The portfolio returned -17.74% at Sharpe -1.177. | Whether a pairwise-greedy basket search would do better. The per-vault proxy was tested, and it failed on its own terms, which is the plan's stated worry realised rather than avoided. |
| 3, the Sortino leg swap (NB23) | REJECT | The swap is a real change that makes things worse. The traded book differs on 113 of 126 dates (89.68%) with a mean weight L1 distance of 0.720, and the centre returns 7.91% at Sharpe 0.584 with double the anchor's ulcer. | Which of the four things the leg changes at once - horizon, shrinkage, scaling, saturation - is responsible. It is a component replacement, not a controlled test. |

### Why lead 2 failed, in one sentence

It spends the composite ranking, dropping from a mean pool rank of 2.5 to 7.73, to buy a statistic
that shows no measurable forward information on this sample: trailing joint-loss frequency
correlates +0.013 with next-cycle return over 2,106 reads and its quintile means are non-monotone.
That is one pooled correlation over repeated-vault, heavily overlapping observations with no
independence correction, so it does not establish that no information exists - only that none was
detected here. Handing `decide_trades` exactly six candidates also removes backfill, so deployment
falls to 92.79% from 97.20%.

### Three limitations of the rule, recorded and NOT retuned

1. **The comparator is misnamed, and most of it does nothing.** The vol-matched family is a
   data-availability filter with a volatility tail, not volatility avoidance - and NB26 showed the
   data-availability part is not merely mislabelled but *inert*, reproducing the anchor exactly.
   The comparator's entire content is the roughly 30% of its removals that have a volatility
   estimate. At N = 30, 21.26 of 30 removals per date (70.9%)
   have no volatility estimate at all, because `inverse_vol` needs 90 observations and a vault
   without them scores exactly 0.0 and sorts to the front of the ascending order. Pooled over
   49,140 removals the share is 59.76%, falling monotonically from 96.5% at N = 5 to 42.8% at
   N = 60 and saturating at 25.66 unmeasured removals from N = 55. It is retained as the bar
   because it is still the best simple thing available, but the previous plan's description of it
   was wrong.
2. **Constraint 7 was not discriminating on this snapshot.** Its comparator is the `drop_30` spike
   at Sharpe 2.747, so the bar is 2.847 - which the ANCHOR ITSELF fails at 2.160, along with every
   family member. Zero of thirteen rows clear it against their own family. Rule 2 forbids retuning
   a pre-registered threshold after seeing results, so it stands. Three replacements are
   recommended for a future plan and recorded in NB24 cell 46: require the comparator to be
   plateau-supported with a median fallback; include N = 0 in the family as this plan's own
   docstring already specifies; and state the bar as a number at pre-registration time rather than
   as a formula whose value is unknown until the family runs.
3. **NB20 gives context for reading any ulcer improvement, and it is weaker than first stated.**
   The staleness sensitivity moves the anchor's ulcer by +4.4% to +11.2%, comparable in scale to
   the margins by which five runs clear the 15% bar (`drop_30` +22.94%, `drop_35` +22.84%,
   `drop_45` +22.52%, `drop_60` +22.41%, `drop_50` +19.33% - the last of which sits BELOW the
   band's lower end). Both quantities are percentages of the anchor's measured ulcer, so they are
   on the same scale and the comparison is valid. But the reviews of NB20 and NB24 both found the
   original conclusion overstated: the sensitivity perturbs the ANCHOR ONLY. A candidate holds
   different vaults at different weights on different dates, and what would have to move for its
   improvement to be an artefact is the candidate-minus-anchor DIFFERENCE in reporting bias, which
   no notebook measured. The band is context for reading an improvement, not an error bar around
   one, and it is not a bound in either direction, because dropping cycles can raise or lower an
   ulcer index depending on where they sit in the drawdown path. Leads 2 and 3 are unaffected
   regardless: their ulcers are 2.0x and 4.2x the anchor's and every other failure stands alone.

### Family-wise

`family_wise_joint()` over the complete 35-run family, 125 aligned cycles, block 10, 999 draws,
seed 0: best observed Sharpe improvement +0.587599 (`drop_30`), null 95th percentile 3.191, 812
exceedances, **p = 0.813**. The improvement figure is now exactly `drop_30`'s panel cycle Sharpe
minus the anchor's, 2.747391 - 2.159792, which is what the `ddof` realignment was for; the
p-value did not move. A null 95th percentile of 3.191 against a best observed improvement of
0.588 means this test has almost no power, which is a different statement from "no effect". It cannot correct for the adaptive research history that chose which
mechanisms to try, and lead 1's promotion from control to candidate is the specific uncorrectable
selection in this plan.

### What the derivation diagnostic showed about the abandoned lead

NB22 Part A vindicates dropping the named-exclusion backtest. The marginal band between `drop_20`
and `drop_30` is exactly 10 vaults on every one of the 126 decision dates, but drawn from 124
distinct addresses with no persistent core at all - nothing reaches 50% of dates, the maximum
frequency is 31.7%, and monthly Jaccard overlap runs 0.167 to 0.514. Decisively, none of the top
15 was ever funded by the anchor. A frozen exclusion list would have named a rotating population
the book never touched, so masking it could not have changed the result.


## Order, cost, and what would change my mind

```
verify splices + anchor parity   (_build/verify-stability-splices.ipynb)
NB20   mark quality              (anchor only, plus archive analysis)
NB21   vol-matched family        (1 + 12 + robustness)
NB22   joint downside            (1 + 12 family + 2 drop runs + 7 + 4 + robustness)
NB23   Sortino leg swap          (stage 1: 1 run + audit; stage 2 if triggered: 11 + robustness)
NB24   close-out                 (every executed run, in one kernel)
```

Three notebooks running at most. The first run rebuilt the whole indicator cache because the
vault archive was re-downloaded; every later notebook serves from that warm cache.

What I expect, stated before running: NB20 finds material stale reporting and a negative skew on
resuming marks, which would put a ceiling on how any ulcer improvement in NB21-NB23 may be read.
NB21 clears every risk constraint at N >= 45 and fails Sharpe non-inferiority everywhere except an
isolated N near 30 - a REJECT that quantifies the de-risking trade exactly. NB22 changes the
basket on a majority of dates and reduces within-basket joint-loss concentration; whether that
survives the ulcer and Sharpe constraints together is the open question, and it is the first
mechanism in either plan aimed directly at the operator's objective. NB23 most likely changes the
traded book on a minority of dates and lands inside the paired interval of the anchor.

## Decisions for the operator

Draft 3 already applies the review's two scope recommendations. What is left for the operator:

1. **The named exclusion list is not being backtested.** Draft 2 specifies it in full - derivation
   window, frozen manifest, common July cash start, uniform and matched static-list nulls,
   evaluation-segment constraints - and it can be run as written. NB22's Part A produces the
   derivation table either way, so the decision can be made after seeing who actually leaves the
   book between N = 20 and N = 30.
2. **`joint_loss_frequency` is a per-vault proxy for a basket-level objective.** It scores each
   candidate against the cohort, not against the other five names chosen. A true pairwise-greedy
   basket search needs a co-movement matrix inside `decide_trades`. NB22 measures the gap; if the
   within-basket concentration barely moves while the per-vault scores do, the greedy version is
   the obvious next notebook.

The review's remaining ideas, ranked by its own expected value of information:
retention-and-exit attribution (does the 14-day momentum gate cause sell-and-rebuy churn);
perp-position screening for hidden tail risk; robust positive drift across independent calendar
blocks; drawdown-recovery shape; direct small-basket path optimisation; regime-conditional
selection; capacity and withdrawal-pressure signals; manager commitment metadata; hierarchical
pooling by leader or strategy family. Each has a cheapest-first-test in the review file.

## Definition of done

- [x] `_build/blocks_stability.py` and `_build/harness_stability.py` exist; the splice
      verification notebook reproduces `BASELINE` with both replacements in place and shows both
      branches inert on the anchor.
- [x] `build_20.py` ... `build_24.py` exist and build without assertion errors.
- [x] Every notebook prints provenance hashes and passes `assert_anchor_parity()` (worst
      difference 4.0e-7 against a 1e-5 tolerance, in every one of the five).
- [x] NB20: gap census, resuming-return buckets with intervals, anchor-book exposure, and the
      stale-cycle sensitivity clearly labelled as a sensitivity.
- [x] NB21: plateau table over N, `simple_rule_eligible`, the removed-set cross-tab and
      no-drop-branch frequency, bootstrap margins at -0.10.
- [x] NB22: Part A derivation table; Part B plateau over `complementary_pool_size` and the window
      sensitivity; within-basket joint-loss concentration against the anchor.
- [x] NB23: stage-1 audit and identity diagnostic; stage-2 ran, with the trigger value printed
      (89.68% against a 10% floor) and the forward-fill share measured at 0 of 18,651 reads.
- [x] NB24: manifests loaded, gates reproduced from scratch, cross-check asserted at 1e-9 and
      matched at exactly zero across all 36 runs, `family_wise_joint()` with the family printed,
      NB20's constraint carried forward, shadow specification frozen.
- [x] Each notebook independently reviewed after its run, findings checked against the cited
      cells, corrections applied. Done with Codex CLI (`gpt-5.6-terra`, reasoning effort high),
      one reviewer per notebook, reviews committed beside each notebook.
- [x] One commit per notebook.

## Review log

- **Draft 1**. Written from the NB14-NB19 results and their seven post-execution reviews.
- **Codex CLI review** (`gpt-6-astra`, [20-stability-leads-plan-codex-review.md](20-stability-leads-plan-codex-review.md)).
  Sixteen findings, a 38-item executability table, eleven creative alternatives ranked by
  information per effort, and two displacement recommendations.
- **Draft 2**. Applied the review's findings while keeping leads 1-3 as the stated scope. NB21
  relabelled exploratory and evaluated from a common July cash start with a matched static-list
  null; drop-set diagnostics moved to a logging splice; constraint 7 redefined as the best
  observed control at or below the candidate's volatility; NB22 restructured into a measurement
  audit and identity diagnostic before any sweep; bootstrap margins on both boundaries with common
  block indices; the family-wise check replaced by a jointly resampled, centred maximum statistic;
  provenance by content hash; ADOPT defined as admission to shadow.
- **Draft 3** (this file). Adopts the two scope recommendations Draft 2 had deferred. A
  mark-quality precursor (NB20) now runs before the three leads, because stale reporting would
  otherwise contaminate the objective every lead is judged against. Complementary downside
  selection replaces the named-exclusion backtest, keeping its derivation as a read-only
  diagnostic in NB22 Part A. Notebooks renumbered NB20-NB24. The shared-additions section now
  describes the code as built rather than as specified, and the verification notebook has run.
  One further fact was discovered during verification and is not a plan decision: **the vault
  price archive was re-downloaded on 2026-09-13 and its content changed** (253,789,435 bytes to
  254,300,668). NB14-NB19 ran on the earlier snapshot. Every figure in this plan's `BASELINE` came
  from the earlier one, so anchor parity is the first thing every notebook checks, and if it fails
  the whole track is re-baselined on the new snapshot with the difference reported rather than
  absorbed.
- **Executed** on 2026-09-13, NB20-NB24, five notebooks, zero failed cells, one commit each.
  Two bugs were caught by the splice verification BEFORE any research notebook used them, and
  both are recorded in commit `f582c94`: the co-movement indicator's cohort reference took a
  cross-sectional median over every vault including stale marks, so after the polling-density
  break the median was exactly zero, the cohort never registered a down day, the indicator was
  NaN everywhere and the selection block silently degenerated into keeping the six lowest pair
  ids; and the same indicator rewarded silence, because a vault that stops reporting never
  records a loss and so scored as perfectly complementary. The first is why every notebook in
  this plan runs a verification pass before it is built. NB20 was rebuilt and re-run afterwards
  so it regenerates from the frozen modules; all 1,346 of its printed numbers were unchanged.
  What was NOT done: independent post-execution review of the five notebooks. The previous plan's
  reviews caught real errors in five of seven notebooks, so these results should be treated as
  unreviewed until that pass runs.
- **Independently reviewed** on 2026-09-13, one Codex CLI reviewer per notebook (`gpt-5.6-terra`,
  reasoning effort high, read-only sandbox), each given this plan, the notebook's build script,
  the shared modules and the de-noised executed notebook. Reviews are committed as
  `2N-*-codex-review.md`. Across the five, 41 findings were raised: 30 confirmed, 5 rejected on
  inspection, 5 partial, and 4 more found by the verifying agents that the reviewer missed.
  Every finding was checked against the cited cell before anything was changed; the rejections
  matter as much as the confirmations, and two of them were the SAME wrong claim about a pandas
  row lookup, raised independently by two reviewers and disproved in a REPL by both agents.

  Three headline claims were corrected. NB20's "the effect is entirely post-April" became "the
  sparse regime is unresolved, not null", because its interval is wide enough to contain a larger
  effect. NB20's ulcer band was demoted from an error bar to context, because it perturbs the
  anchor only. NB22's "the mechanism worked and the portfolio still lost" was RETRACTED: the
  fall in within-basket co-loss is entirely explained by the marginal down rates, and against a
  matched independence benchmark the selected basket co-loses MORE than chance. NB23's zero
  forward-fill measurement, which looked like the kind of null that is usually a measurement bug,
  survived every axis of scrutiny and was strengthened by a new measurement showing the mask is
  unreachable on this cohort rather than merely unhit.

  Two shared-module defects were fixed in commit `328c8de` and all five notebooks re-run against
  them: `bootstrap_paired_sharpe_diff()` and `family_wise_joint()` standardised Sharpe with the
  population deviation while the adoption rule's constraint 2 is defined on the sample deviation,
  so every reported observed Sharpe difference sat `sqrt(125/124)` = 1.00402x away from the
  difference of the panel Sharpes printed beside it; and `joint_loss_frequency` counted a missing
  observation as a reported day, because a NaN is not equal to 0.0. Both were immaterial - after
  the fix every observed difference equals the corresponding panel Sharpe difference to the last
  digit, no `clears_boundary` flag moved on any row of any notebook, and no backtest metric,
  manifest value or verdict changed anywhere. They were fixed and re-run anyway, so that the
  committed code reproduces the committed notebooks and the next plan does not inherit them.
