# Stability leads plan: three cheap tests of what actually stabilised the curve

- **Status**: DRAFT 2, revised after Codex CLI review (`gpt-6-astra`,
  [20-stability-leads-plan-codex-review.md](20-stability-leads-plan-codex-review.md)). Two of the
  review's recommendations change the operator's stated scope (replace lead 2; add a mark-quality
  precursor) and are NOT applied - they are listed under "Decisions for the operator" at the end.
  Everything else the review found is applied; see the review log.
- **Track**: `hyperliquid-lower-vol`, notebooks NB20-NB23. Follows
  [14-evidence-weighted-plan.md](14-evidence-weighted-plan.md) (NB14-NB19, NOTHING ADOPTED, all
  seven notebooks independently reviewed) and the age-barrier audit in
  [13-research-age-barrier.ipynb](13-research-age-barrier.ipynb).
- **Baseline to beat**: [02-better-format.ipynb](02-better-format.ipynb), re-run as the anchor in
  every notebook. Full-precision baseline metrics are stored in `_build/harness_stability.py`
  (`BASELINE`) with explicit tolerances; the heading figures 37.90% CAGR, cycle Sharpe 2.160,
  cycle vol 0.1543, ulcer 1.80%, beta 0.046, 578 trades, $186,746 are rounded from those.
- **Every historical result in this plan is exploratory and in-sample.** ADOPT means *admission to
  the frozen prospective shadow protocol* (NB23), not authorisation to deploy capital. The full
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
  exactly those three leads.

This file is written to be executed by an agent that has not read the rest of the track.

## The three leads

| # | Lead | Where it came from | What would make it a result |
|---|---|---|---|
| 1 | **The vol-matched drop family, promoted from control to candidate.** `vol_matched_drop_50` delivered vol 9.5%, ulcer 1.45%, beta 0.002, Sharpe 2.01, fully invested, for 17 pp of CAGR - better on every risk axis than any mechanism the previous plan built. It was never plateau- or leave-one-vault-out checked because it was the control. | NB15, NB19 | A contiguous run of N values that all pass constraints 1-6 and the late period, with leave-one-vault-out holding at the centre. Promoting a control after seeing its result is itself a selection; the notebook records a `simple_rule_eligible` flag, and ADOPT still means only admission to the shadow. |
| 2 | **A named exclusion list instead of a volatility count.** `drop_30` is a spike as a *rule*; nobody has looked at which vaults leave between N = 20 and N = 30. If a stable set of names does the work, a curated exclusion list is a different mechanism, and `MASKED_VAULTS` already implements it. | NB15 review, NB12 | A list frozen on the derivation window whose exclusion, evaluated from a common July cash start, passes all seven constraints on the evaluation segment, holds across list sizes, and beats BOTH a uniform random-list null and a matched static-list null. The review is right that this is an outcome-informed hypothesis with a chronological diagnostic, not independent validation; it is labelled exploratory throughout. |
| 3 | **The minimal change nobody ran.** NB14/NB16 found the *evidence-shrunk* CAGR leg hurt; NB31 found the incumbent's *360-day* CAGR leg is load-bearing. Keep the incumbent's CAGR leg and swap only the 45-day Sortino leg for `sortino_shrunk_score`. | NB16 review, NB31 | First, a measurement audit and an identity diagnostic showing the swap actually changes the book; then, only if it does, a local sensitivity sweep and the seven constraints, plateau and leave-one-vault-out. The swap cannot reach young vaults; it re-ranks the old cohort. |

## Rules for the executing agent

The previous plan's rules plus what its seven post-execution reviews and this plan's review taught.

1. **Never select or tune towards a vault by name** - except in NB21, where a frozen list of names
   is the mechanism under test, derived by the pre-registered procedure on the derivation window
   before any evaluation output is produced.
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
7. **`runs = [(label, state, equity, returns, panel), ...]`** plus `run_by_label` is the only
   source for every table; unique labels; every control (frontier points included) goes through
   the same `run_and_record()` so it retains state, equity and returns.
8. **Diagnostic logs** (`VOL_DROP_LOG`, `SLEEVE_LOG`) are cleared before each run and snapshotted
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
family**, so for NB20 constraint 7 is a self-comparison (a retained member would need
`S >= S + 0.10`) and is **not applied** (review finding 6: inapplicable, not vacuous); NB20 reports
`passes_1_to_6`, `failed_1_to_6` and `simple_rule_eligible`, never `passes_v2`. NB21 and NB22 must
clear it: a named list and a re-ranked composite are additional mechanisms and carry a complexity
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
still cannot erase the adaptive research history behind the family, and NB23 says so.

Verdict words: ADOPT (= admission to shadow) / REJECT / CONTROL / DIAGNOSTIC.

## Shared additions

### `_build/blocks_stability.py`

```python
"""Stability-leads track additions (20-stability-leads-plan.md), NB20-NB23."""

INDICATOR_ADDITIONS_STABILITY = '''
#: --- stability-leads track additions (see 20-stability-leads-plan.md) ---

#: Per-cycle record of what the vol-matched drop actually removed, written by decide_trades (see
#: CELL14_REPLACEMENTS_STABILITY). Cleared and snapshotted per run by run_and_record().
VOL_DROP_LOG: dict = {}


@indicators.define(
    dependencies=(cagr_score, sortino_shrunk_score),
    source=IndicatorSource.dependencies_only_per_pair,
)
def cagr_sortino_shrunk_weight(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    cagr_lookback_days: int = 360,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
    evidence_prior_strength: int = 60,
    evidence_t_cap: float = 3.0,
    cagr_weight: float = 0.6,
) -> pd.Series:
    """The incumbent composite with ONLY its Sortino leg swapped (NB22, lead 3).

    `cagr_weight x cagr_score(360d) + (1 - cagr_weight) x sortino_shrunk_score`. The 360-day CAGR
    leg is the incumbent's own, untouched, so the composite still needs 360 days of history and
    cannot reach young vaults. It is a component replacement, not an isolated test of shrinkage
    or of event time: the replacement leg changes horizon (up to 90 mark events instead of 45
    calendar days), shrinkage, scaling and saturation at once, and its NaN behaviour differs
    from `sortino_score`'s, so admission is NOT guaranteed identical even though the CAGR gate is
    (review finding 10). NB22's audit cell measures exactly how much the selected book changes.
    """
    cagr_component = dependency_resolver.get_indicator_data(
        'cagr_score', pair=pair, parameters={'cagr_lookback_days': cagr_lookback_days},
    )
    sortino_component = dependency_resolver.get_indicator_data(
        'sortino_shrunk_score', pair=pair,
        parameters={
            'evidence_max_events': evidence_max_events,
            'evidence_min_events': evidence_min_events,
            'evidence_min_down_events': evidence_min_down_events,
            'evidence_prior_strength': evidence_prior_strength,
            'evidence_t_cap': evidence_t_cap,
        },
    )
    return cagr_weight * cagr_component + (1.0 - cagr_weight) * sortino_component
'''

#: Read-only logging of the vol-matched drop, spliced after the existing drop block in
#: cell14_enhanced.py. Anchor trades and equity must be identical with and without it (rule 4).
#: Anchor string verified unique in cell14_enhanced.py on 2026-09-13.
CELL14_REPLACEMENTS_STABILITY = {
    "        dropped_ids = {item[0] for item in by_vol[:vol_matched_drop]}\n":
    "        dropped_ids = {item[0] for item in by_vol[:vol_matched_drop]}\n"
    "        # Stability-leads track: record what was actually dropped, so the offline diagnostic\n"
    "        # reads the trading pipeline's own decision rather than reconstructing it.\n"
    "        VOL_DROP_LOG[timestamp] = {\n"
    "            'pre_drop_candidates': [item[0] for item in candidates],\n"
    "            'inv_vol': {item[0]: inv_vol_by_id.get(item[0], 0.0) for item in candidates},\n"
    "            'scored': {item[0]: bool(item[2] != 0.0) for item in candidates},\n"
    "            'dropped_ids': sorted(dropped_ids),\n"
    "            'no_estimate_dropped': sorted(pid for pid in dropped_ids if inv_vol_by_id.get(pid, 0.0) == 0.0),\n"
    "        }\n",
}
```

The log is written only when the drop branch executes (`vol_matched_drop > 0 and len(candidates)
> vol_matched_drop`); when the gated pool has at most N members the trading code drops nothing,
and the diagnostic reports that frequency explicitly (review finding 8). `no_estimate_dropped`
identifies missing volatility, which is not the same as "unscored by the 360-day CAGR leg" (90
versus 360 days) and not the same as "young": the diagnostic cross-tabulates all three and never
uses them interchangeably.

### `_build/harness_stability.py`

Appended as its own cell after `harness_evidence.py`'s cell. Defines: `BASELINE` (full-precision
anchor metrics and tolerances, and `assert_anchor_parity()`); `provenance()` (SHA-256 of the
price archive, metadata snapshot, universe cache and Binance store, plus the `_build/` git
commit; printed in every notebook's first output cell); `placebo_ref_observed()` as above;
`passes_constraints_v3()` / `failing_constraints_v3()` (constraints 1-6 from
`harness_evidence.py` plus the observed-control constraint 7, with a `skip_placebo=True` switch
for NB20); `passes_1_to_6()`; `bootstrap_paired_sharpe_diff()` (common block indices, margins,
block-length sensitivity); `family_wise_joint()`; `verdict_table_v3()`; and `run_and_record()`
itself, so that every notebook shares one implementation that clears and snapshots the diagnostic
logs:

```python
def run_and_record(label, family, **overrides):
    VOL_DROP_LOG.clear(); SLEEVE_LOG.clear()
    s, e, r = run_variant(label, **overrides)
    p = panel(label, s, e, r, anchor_cycle_returns)
    entry = dict(label=label, state=s, equity=e, returns=r, panel=p, family=family,
                 overrides=dict(overrides), vol_drop_log=dict(VOL_DROP_LOG), sleeve_log=dict(SLEEVE_LOG))
    assert len(set(entry["vol_drop_log"])) == len(entry["vol_drop_log"])
    runs.append(entry); run_by_label[label] = entry
    return entry
```

`build_family()` runs the 5-step vol-matched family (N in {5, ..., 60}; N = 0 is the anchor's own
entry) through `run_and_record(..., family="control")`, once per notebook, in the same kernel as
the candidates.

Before any notebook runs: splice both files through `builder.py`, compile every cell, run the
anchor with the logging replacement in place and `vol_matched_drop_count = 0`, and assert parity
against `BASELINE` - the logging branch never executes on the anchor path, and the assertion
proves it. Reuse `_build/verify-plan14-draft2.ipynb`'s pattern.

## Experiment track

### NB20 - backtest: the vol-matched family as a candidate

**File**: `20-backtest-vol-matched-family.ipynb`, `_build/build_20.py`.

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
removed ids by (volatility available / missing) x (composite scored / unscored) x (age < 360 d /
>= 360 d at that date, from NB13's life cache); the Jaccard overlap of `dropped_ids` between
consecutive decision dates (two empty sets = missing, one empty = 0), reported as a description of
how stable the removed set is - never as a stopping rule.

**Outputs.** `verdict_table_v3(..., skip_placebo=True)` with `passes_1_to_6`, `failed_1_to_6`,
`late_ok`, and `placebo_ref` shown for information; the plateau table (N, N-5, N+5 each
Boolean); `simple_rule_eligible` per N; bootstrap intervals vs the anchor for every eligible
centre (boundary -0.10); the chart of CAGR, Sharpe, vol, ulcer against N; the diagnostic tables;
equity curves of the anchor and every N with `passes_1_to_6`.

**Verdict.** ADOPT (to shadow) the **smallest** N for which the centre, both neighbours and the
masked centre all pass `passes_1_to_6` and `late_ok`; if several qualify, the smallest N is the
single shadow candidate and the others are listed. Otherwise REJECT, with the binding constraint
per N. If the family clears every risk constraint but Sharpe non-inferiority at every N, the
heading says that de-risking at these settings costs Sharpe *on this window under this rule* -
not that it does so in general, and not if any N failed on CAGR, deployment or plateau instead.

### NB21 - research + backtest: a named exclusion list (exploratory)

**File**: `21-backtest-exclusion-list.ipynb`, `_build/build_21.py`.

**Question.** Is the `drop_30` effect carried by a stable set of names? If so, does excluding those
names - frozen on the derivation window, evaluated from a common cash start on the evaluation
window - do what the volatility count does, and beat removing a matched set of *other* names?

**Status of this notebook.** Exploratory. The window is in-sample, `drop_30` and the 20-to-30 band
were chosen after seeing full-window results, and a chronological split inside the window is a
diagnostic, not validation (review finding 1). The heading's first bullet says this.

**Derivation (on 2026-01-01 to 2026-06-30 only).** Run `drop_20` and `drop_30` with the logging
splice. For every decision date in the derivation window, `D20, U20 = drop_set(20)`, `D30, U30 =
drop_set(30)` read from the two runs' `vol_drop_log`; `M = (D30 - D20) - U30` (the marginal band,
volatile part only). `frequency[address] = #dates address in M / #dates`. Order by descending
`frequency`, then ascending frequency of being in `D20`, then lower-case address. Report: the
frequency table; a persistent-core table (addresses in M on >= 50% / 75% / 90% of dates);
monthly membership stability; stability of the top-15 under 20 blocked resamples of the
derivation dates (block = 10 dates); the cross-tab of top-15 members by age and score
availability at the derivation cutoff; how many top-15 members ever displaced a *funded* anchor
position (from the anchor run's positions). Any k for which fewer than k addresses have positive
frequency is marked unavailable, not padded. Freeze the ordered list, the cutoff, the frequency
table and the input hashes in a printed manifest **before** any evaluation cell runs.

**Evaluation (2026-07-01 to 2026-09-08, from a common cash start).** Every evaluation run starts
from $150,000 cash at the first scheduled decision on or after 2026-07-01 with full indicator
history (`run_and_record(..., backtest_start=datetime.datetime(2026, 7, 1))`; the universe
loader already carries the pre-July history). Runs: `anchor_jul` (the comparator);
`family_jul` (N in {5, ..., 60}, twelve runs, the constraint-7 family for this segment);
`exclude_top{k}_jul` for k in {5, 10, 15} with `masked=set(EXCLUSION_LIST[:k])`; the two nulls
below; and, if `exclude_top10_jul` passes, the masked robustness run with
`masked=set(EXCLUSION_LIST[:10]) | {top_contributor_of_exclude_top10_jul}`. Full-window masked
runs (`exclude_top{k}_full`) are also produced, labelled **retrospective counterfactuals**, and
are not used for the verdict (review finding 2). All seven constraints are evaluated on the
evaluation segment against `anchor_jul` and `family_jul`; `late_*` columns are redundant here and
the late-period check is replaced by the segment itself.

**Two nulls, both k = 10, B = 49 draws each** (empirical resolution 0.02; 199 would be better and
is a noted trade-off against ~50 minutes of compute):

- *Uniform*: sampled without replacement from the sorted, frozen population of addresses that
  were in the gated pool with valid `inverse_vol` on any derivation date, `np.random.default_rng
  (seed)`, every list printed. A weak baseline (review finding 3: uniform lists contain
  never-competitive names).
- *Matched static-list*: sampled from the same population stratified into fixed bins on
  derivation-only volatility rank (quintile), composite-score availability (ever scored / never),
  gated-eligibility frequency (tercile) and anchor exposure (ever funded by the anchor / never);
  each draw matches the candidate list's bin counts; fallback to the nearest bin if a bin is
  exhausted, recorded. This is the null that asks whether *these identities* matter beyond
  their risk-and-eligibility cohort.

Primary null statistic: **negative evaluation-segment ulcer** (stability, the operator's
objective); CAGR-floor and deployment eligibility enforced separately as constraints; CAGR and
Sharpe ranks reported as secondary diagnostics. `p = (1 + #{T_random >= T_candidate}) / (B + 1)`,
ties against the candidate, numerator and denominator printed. Call it a random-list benchmark
percentile, not a significance test.

**Verdict.** ADOPT (to shadow) `exclude_top10` only if, on the evaluation segment: it passes all
seven constraints (v3, comparator = `family_jul`); `exclude_top5` and `exclude_top15` pass all
seven; the masked robustness run passes all seven; and its ulcer-based p <= 0.10 against BOTH
nulls. Otherwise REJECT with the complete failure set. If the derivation produces no address with
frequency >= 0.5, the notebook still runs `exclude_top10` (the derivation tables are the finding
either way) but says in the first bullet that no persistent core exists.

### NB22 - backtest: the incumbent composite with only its Sortino leg swapped

**File**: `22-backtest-sortino-leg-swap.ipynb`, `_build/build_22.py`.

**Question.** Does the event-time, shrunk Sortino leg re-rank the old cohort better than the
incumbent's 45-day rolling Sortino? Two stages: first establish that the swap changes the book and
that the score is measuring what it claims; only then sweep.

**Stage 1 - measurement audit of `sortino_shrunk_score` on the candidate pool** (review findings
11-12). Over every decision date and every gated candidate: score validity rate; elapsed
calendar span of the event window (the 90 mark events cover different durations per vault -
report its dispersion across candidates); age of the last *valid* evidence at each read; **how
often the forward-fill in `_event_time_stats` bridges an event date that failed the down-count
mask** (a later event window with too few down-events inherits an older valid score - the review
found this in the helper) - if that bridging affects more than 2% of (candidate, date) reads,
define a `_v2` indicator chain in `blocks_stability.py` that masks before reindexing and use it
for every run in this notebook, recording the change; clipping frequency at the [0, 1] cap;
selected positions whose score was NaN (admitted at signal 0).

**Stage 1 - identity diagnostic.** Run `swap__centre` (`selection_score_indicator=
"cagr_sortino_shrunk_weight"`, admission as the anchor's: `require_scored_candidates=False`).
Against the anchor, per decision date: target-weight L1 distance and realised-weight L1 distance
(from `state.stats.positions` values over equity), whether the traded top-6 sets differ, the
symmetric difference size, the active cycle return, and turnover. Summarise: share of decision
dates on which the traded book differs; mean L1 distance; the contribution of changed holdings to
the largest five drawdowns. If the traded book is identical on every date, the notebook stops
with DIAGNOSTIC: the swap is a mechanical replication of the anchor and the sweep has no
information value (the remaining budget goes to the operator's decision on idea 3 below).

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
centre if the centre and plateau pass. Bootstrap intervals for the centre vs the anchor (-0.10)
and vs the observed placebo comparator (+0.10), block-length sensitivity included.

**Verdict.** ADOPT (to shadow) only if the centre passes all seven (v3) and `late_ok`, all ten
neighbours pass all seven and `late_ok`, and leave-one-vault-out passes. Otherwise REJECT with
the complete failure set. A near-anchor replication that fails only the 15% ulcer reduction is
reported as exactly that.

### NB23 - close-out

**File**: `23-backtest-closeout.ipynb`, `_build/build_23.py`.

Loads each notebook's frozen manifest (centre labels, neighbours, masks, eligibility flags, the
NB21 list and null results, NB22's stage-1 outcome), re-runs in one kernel the anchor, the 5-step
family, every NB20 `drop_N`, NB21's evaluation-segment runs if NB21 reached stage 2 (from the July
start, with their own `anchor_jul`), every NB22 run that was executed, and every triggered
robustness run; reproduces every gate from the manifests (it does not trust the source
notebooks' verdict flags); asserts each centre's Sharpe against a literal copied from the source
notebook; prints the combined `verdict_table_v3()`; the frontier chart with every run overlaid;
`family_wise_joint()` over the complete executed family with its exact membership printed and the
statement that it cannot correct for the adaptive history; equity curves; and the prospective
shadow specification - start date, fixed comparator (the unchanged anchor on the same decision
dates), monitoring horizon, stopping conditions and decision rule, all fixed before new data
arrive, with the literal override dictionary for any ADOPT. If more than one lead reaches ADOPT,
the shadow runs them side by side; the plan does not rank them. If NB21 is DIAGNOSTIC-only it is
recorded as ineligible, not assumed to have a centre.

**Verdict.** ADOPT `<labels>` (to shadow) or NOTHING ADOPTED, plus one sentence per lead on what
it settled and one on what it could not.

## Order, cost, and what would change my mind

```
verify splice + anchor parity   (~2 min)
NB20                             (1 + 12 + robustness, ~8 min)
NB21                             (derivation 2 runs; evaluation 1 + 12 + 3 + 98 nulls + robustness, ~45 min)
NB22                             (stage 1: 1 run + audit; stage 2 if triggered: 11 + robustness, ~8 min)
NB23                             (~40-60 runs, ~20 min)
```

Three concurrent at most; NB21's null draws are the cost driver and are the reason B = 49 rather
than 199. Build all four `build_NN.py` before running any.

What I expect, stated before running: NB20 clears every risk constraint at N >= 45 and fails
Sharpe non-inferiority everywhere except an isolated N near 30 - a REJECT that quantifies the
de-risking trade exactly. NB21 most likely finds a small persistent core (4-6 names) inside an
unstable band, and the matched null is the check that decides whether those names matter. NB22
most likely changes the traded book on a minority of dates and lands within the paired interval
of the anchor - the interesting outcome would be a passing centre with a holding plateau, the
first mechanism in either plan to clear the rule.

## Decisions for the operator

The review recommends two scope changes that this draft does not make, because leads 1-3 were
the stated scope:

1. **Displace NB21 with "complementary downside selection"** (review idea 2): from the incumbent's
   top-18 candidates, choose six with the lowest joint-loss frequency, keeping the incumbent's
   sizing. The review's argument: a named exclusion list converts an outcome-selected volatility
   band into permanent identities, whereas joint-downside selection is a generalisable mechanism
   tied directly to equity-curve stability. Its cheapest first test is one fixed six-from-18
   construction compared with the anchor's joint-loss concentration.
2. **Precede all three leads with a reporting-versus-trading-inactivity audit** (review idea 1):
   tabulate, for anchor-held vaults, the next observed loss and recovery by preceding
   polling-gap length, separately before and after April, with endpoint mark age. The argument:
   until stale reporting is separated from genuinely flat trading, the risk measures every lead
   is judged on may describe missing observations rather than economic experience. The review
   rates this the highest information-per-effort item on its list.

The review's other ideas, ranked by its expected value of information: retention-and-exit
attribution (does the 14-day momentum gate cause sell-and-rebuy churn); perp-position screening
for hidden tail risk; robust positive drift across independent calendar blocks; drawdown-recovery
shape; direct small-basket path optimisation; regime-conditional selection; capacity and
withdrawal-pressure signals; manager commitment metadata; hierarchical pooling by leader or
strategy family. Each has a cheapest-first-test in the review file.

## Definition of done

- [ ] `_build/blocks_stability.py` and `_build/harness_stability.py` exist; the splice
      verification notebook reproduces `BASELINE` with the logging replacement in place.
- [ ] `build_20.py` ... `build_23.py` exist and build without assertion errors.
- [ ] Every notebook prints provenance hashes and passes `assert_anchor_parity()`.
- [ ] NB20: plateau table over N, `simple_rule_eligible`, the removed-set cross-tab and
      no-drop-branch frequency, bootstrap intervals at -0.10.
- [ ] NB21: frozen manifest printed before evaluation; both nulls with `(numerator, denominator)`;
      evaluation from the July cash start; retrospective counterfactuals labelled as such.
- [ ] NB22: stage-1 audit and identity diagnostic; stage-2 only if triggered, with the trigger
      value printed.
- [ ] NB23: manifests loaded, gates reproduced, cross-check asserted, `family_wise_joint()` with
      family printed, shadow specification frozen.
- [ ] Each notebook independently reviewed after its run, findings checked against the cited
      cells, corrections applied, before the status line is set to EXECUTED.
- [ ] One commit per notebook.

## Review log

- **Draft 1**. Written from the NB14-NB19 results and their seven post-execution reviews.
- **Codex CLI review** (`gpt-6-astra`, [20-stability-leads-plan-codex-review.md](20-stability-leads-plan-codex-review.md)).
  Sixteen findings, a 38-item executability table, eleven creative alternatives ranked by
  information per effort, and two displacement recommendations.
- **Draft 2** (this file). Applied: NB21 relabelled exploratory, evaluated from a common July cash
  start with all seven constraints on the evaluation segment, list frozen in a manifest, a matched
  static-list null added beside the uniform one, the null statistic changed to evaluation-segment
  ulcer with `p = (1 + count) / (B + 1)`, Jaccard demoted to descriptive; drop-set diagnostics now
  read a logging splice (`VOL_DROP_LOG`) instead of an offline reconstruction, with the no-drop
  branch, actual removed counts, and a missing-volatility / unscored / age cross-tab; constraint 7
  redefined as the best observed control at or below the candidate's volatility (no
  interpolation, nothing "not evaluable"), inapplicable to NB20 by explicit statement with a
  `simple_rule_eligible` flag, applied to NB21/NB22 as a stated complexity premium; the
  5-step family fixed as the comparator everywhere; NB22 restructured into a measurement audit
  and identity diagnostic before any sweep, with the Sortino helper's forward-fill-past-
  invalidation behaviour to be measured and fixed if material, `cagr_weight = 0.7` and
  `evidence_max_events` neighbours added, strict admission moved out of the plateau; bootstrap
  intervals for every eligible centre with common block indices against the -0.10 and +0.10
  boundaries; the family-wise check replaced by a jointly resampled, centred maximum statistic;
  provenance by content hash and the point-in-time membership limitation stated; ADOPT defined
  as admission to shadow; robustness Booleans listed separately with skipped runs failing closed;
  manifests handed to NB23. Not applied (scope): the two displacement recommendations, recorded
  under "Decisions for the operator".
