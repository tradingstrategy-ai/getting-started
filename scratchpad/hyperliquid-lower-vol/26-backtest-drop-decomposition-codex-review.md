# NB26 review

The anchor parity, two-day-cycle risk metrics, paired bootstrap implementation, and the `unmeasured_30` removal log are sound. In particular, Cell 25 shows that `unmeasured_30` actually removed 21.26 unmeasured vaults per decision across 126 logged decisions: its anchor replication is not explained by a no-op branch.

## Findings

1. **Severity: blocking.**  
   **Cell: 14; interpreted in Cell 31 and Cell 0.**  
   **What is wrong:** The “random” null is not ten independent or plausibly uniform random draws. It ranks candidates by

   ```python
   (pair_id * 2654435761 + key) % 4294967291
   ```

   where `key` is only an additive common offset.  
   **Why it is wrong:** For a fixed candidate set, changing a common additive offset merely cyclically rotates one fixed ordering; it does not generate a fresh permutation. Between consecutive two-day decisions, `timestamp.toordinal()` changes by only two, so the ordering will normally remain unchanged unless a hash value crosses the modulus boundary. Seeds 0–9 are similarly spaced by a deterministic 1,000,003 offset. The code therefore neither establishes independent draws nor validates that seeds change selected sets. The indistinguishable rounded null summaries in Cells 31 and 39 are a warning sign, not validation. All p-values and claims based on “all ten random draws” are consequently unsupported.

   **Concrete fix:** Replace the affine rank with a proper deterministic keyed hash of the full `(seed, decision timestamp, pair_id)` tuple, for example a fixed-width BLAKE2 digest converted to an integer. Assert distinct rankings or dropped sets across seeds where candidate composition permits it. Until then, remove the percentile/p-value claims and any conclusion drawn from this null.

2. **Severity: material.**  
   **Cell: 29; interpreted in Cell 0.**  
   **What is wrong:** `measured_8` is presented as a decomposition of `incumbent_30`’s volatility half merely because it matches the incumbent’s *mean* measured-removal count, 8.0 versus 8.74.  
   **Why it is wrong:** The incumbent removes a variable number of measured vaults on each date: it first consumes however many unmeasured vaults are available, then removes the remainder. `measured_8` instead removes exactly eight measured vaults on every eligible decision, including dates on which the incumbent removed none or a different count. Equality of means does not equal treatment matching in date, count, or selected identities. Thus the run is a fixed-strength measured-only variant, not an isolated half of `incumbent_30`.

   **Concrete fix:** Change the claim to: “At a nearby fixed strength, `measured_8` has a +3.07 pp observed CAGR advantage.” To support a decomposition claim, the measured-only branch must use the incumbent’s realised per-decision measured-removal count, while retaining unmeasured candidates.

3. **Severity: material.**  
   **Cell: 43; interpreted in Cell 0.**  
   **What is wrong:** “The volatility half is a small real effect” and “survives every robustness check” overstate the evidence.  
   **Why it is wrong:** The paired Sharpe-difference intervals for `measured_8` versus anchor are approximately `[-0.039, 0.665]` for all three block choices. They clear the pre-specified non-inferiority boundary of −0.10, but contain zero, so they do not establish a positive Sharpe improvement. The candidate also fails the material-ulcer requirement and the late-period check. The random-null evidence cannot repair this because Finding 1 invalidates it.

   **Concrete fix:** Replace “small real effect” with “an observed, in-sample improvement at this fixed setting”; replace “survives every robustness check” with the precise leave-one-vault-out result only.

4. **Severity: material.**  
   **Cell: 25 and Cell 41; interpreted in Cell 0.**  
   **What is wrong:** The heading states that, before April, there were “always more than 30 unmeasured vaults” and therefore no measured vault was removed.  
   **Why it is wrong:** Cell 25 reports only full-window mean pool sizes. Cell 41 reports rounded sparse-period performance, not the logged sparse-period unmeasured-pool minimum or measured-drop count. Neither cited cell verifies the claimed per-date mechanism. Also, the necessary condition is at least 30 unmeasured candidates, not “more than 30”.

   **Concrete fix:** Either remove the mechanism sentence, or print and assert from `incumbent_30`’s own log that every pre-April decision had `unmeasured_pool >= 30` and zero measured drops; separately demonstrate exact sparse-period equity or cycle-return identity.

5. **Severity: material.**  
   **Cell: 27 and Cell 43; interpreted in Cell 0.**  
   **What is wrong:** The notebook labels the five incumbent settings as the observed-control family, but this is not the pre-registered family. It omits N = 5, 15, 25, 35, 45, 55, and 60.  
   **Why it is wrong:** Any constraint-7 comparator or “observed control” bootstrap must use the complete stipulated 5-step family. In particular, Cell 43’s comparison of `measured_8` to `incumbent_30` is not demonstrated to be the rule-v3 comparator. The heading’s statement that constraint 7 is inapplicable “for the same reason as NB21” is also incorrect: `measured_8` is not itself a family member, so self-comparison is not the issue.

   **Concrete fix:** Do not call this subset an observed-control family or use it for v3 language. Since NB26 is explicitly diagnostic, retain only the anchor comparison; alternatively use the complete family before making comparator claims.

6. **Severity: material.**  
   **Cell: 37 and Cell 39.**  
   **What is wrong:** The claimed “per-vault” weight charts and concentration statistics group holdings by `token_symbol`, not by vault address.  
   **Why it is wrong:** The notebook’s own strategy code says token symbols are truncated and not unique. Distinct vaults sharing a symbol are silently combined in `rows[ts][name]`, understating holdings and distorting top-one weight, HHI, the “other” bucket, and distinct-vault counts.

   **Concrete fix:** Key the frame by lower-case pool address or pair ID. Maintain a separate display-label map and append an address suffix where symbols collide.

7. **Severity: minor.**  
   **Cell: 26.**  
   **What is wrong:** The markdown says the table reports `passes_v3`, constraints 1–7.  
   **Why it is wrong:** Cell 27 creates and displays `passes_1_to_6` and `failed_1_to_6` only. This is an inaccurate description of the output.  
   **Concrete fix:** Say: “`passes_1_to_6` reports constraints 1–6 only; this diagnostic does not evaluate adoption.”

8. **Severity: minor.**  
   **Cell: 0.**  
   **What is wrong:** The Realist Capital lifetime CAGR, Sharpe, and maximum-drawdown figures have no cited producing cell.  
   **Why it is wrong:** No executed cell computes or displays those figures, contrary to the notebook’s stated requirement that every heading number cite its output.  
   **Concrete fix:** Remove the unsupported sentence, or add a cited output cell that calculates those figures.

9. **Severity: minor.**  
   **Cell: 0 and Cell 37.**  
   **What is wrong:** The heading says there are “38 more stacked-area figures”, despite charting 22 of 40 runs and leaving 18 random-null runs uncharted.  
   **Why it is wrong:** The arithmetic is inconsistent.  
   **Concrete fix:** Say “18 additional stacked-area figures” or “40 figures in total”.

## Claims that are correct but need narrower wording

- The 98% calculation is arithmetically correct: the full CAGR edge is 11.10 pp and the common-mask edge is about 0.22 pp. Cell 43 also correctly uses a full re-simulation and the appropriate masked-anchor proxy, `unmeasured_30__without_top_vault`.

  However, “98% was one holding” is causal attribution the run cannot provide: masking changes future selection, sizing, and trading. Prefer: “98% of the *relative CAGR edge disappears under the common Realist-exclusion counterfactual*.”

- `unmeasured_30`’s reported panel values exactly reproduce the anchor to six decimals, and Cell 25 establishes that it made real removals. “Exactly inert” is justified for the displayed outcome metrics. “Removing them changes no trade at all” is not directly measured; say “changes no reported panel metric” unless trade or basket identity is explicitly compared.

- The leave-one-vault-out edge for `measured_8` does increase from about +3.07 pp to +3.35 pp. That descriptive arithmetic is correct, but it does not by itself establish a robust or general “real effect.”
## Verification of these findings, and what was applied

Every finding was checked against `_build/build_26.py`, `_build/blocks_drop_modes.py` and the
executed cell output before anything was changed. Nine findings: one blocking, five material,
three minor. Eight confirmed, one partial. The notebook was rebuilt and re-run; anchor parity
still holds on all ten `BASELINE` metrics, `incumbent_30` still returns 0.489942 / 2.747391, and
the incumbent, `measured_only` and `unmeasured_only` runs are unchanged to six decimals.

### 1, blocking, the random null - CONFIRMED, and worse than reported

Not "may not generate a fresh permutation": it demonstrably generated none. Every one of the ten
seeds produced a **bit-identical backtest** at both strengths - `manifest_26.json` from the first
run gives all ten `random30_s*` a CAGR of 0.01920359623308676, an ulcer of 0.026543218597739917
and a Sharpe of 0.21245400862532862, and all ten `random9_s*` 0.37036106719497996 /
0.01775943725671113 / 2.065749766027917. That is why `null_median == null_best` on all ten rows of
the old cell 31 and why all ten seeds shared four-decimal weight statistics in the old cell 39.

The cause is exactly the one named. Sorting by `(x_i + K) mod P` is a cyclic rotation of the fixed
order of `x_i = (pair_id * 2654435761) mod P`; the first N are a contiguous arc, and the arc only
moves when some `x_i` falls inside the rotation window. The window the ten seeds and 126 dates
span is about 9.7e6 wide, against a mean gap between the hashed values of ~148 candidates spread
over 4.29e9 of about 2.9e7. A standalone simulation over plausible pair-id ranges reproduced it:
zero distinct sets across the ten seeds, and one distinct set across all 126 decision dates. So
the null was neither ten draws nor a per-cycle draw - it was one fixed arbitrary vault preference
applied at every decision, the "silent degeneration into an arbitrary ordering" failure mode this
track has already hit once.

Fixed in `_build/blocks_drop_modes.py` (NB26-only, so no other notebook is touched): the branch
now sorts candidates by pair id and shuffles with `np.random.default_rng(_key).permutation`, where
`_key = vol_drop_seed * 1000003 + timestamp.toordinal()`. A seeded generator instance keeps the
"no shared RNG state" property the original comment wanted, needs no import, and mixes the key
into every bit. BLAKE2 would work equally well and is more machinery than this needs.

A new cell 27 asserts the null is a null: ten seeds must give ten distinct draw sequences, and
each run must draw a different set on every decision. Both assertions fail on the old code.

**What it changed.** At n = 30 the null median CAGR moved from 1.92% to 5.25% and the best from
1.92% to 16.50%; `incumbent_30` still beats all ten draws on all five metrics. At n = 9 the
consequences are larger: `measured_8` still beats all ten on CAGR and Sharpe, but is beaten by one
draw on Martin (p = 0.1818), by three on ulcer (p = 0.3636) and by nine on beta (p = 0.9091). The
heading's "beats all ten of its random-null draws on CAGR, Martin, Sharpe and ulcer" is now false
and has been rewritten. The segment table also moved: 3 of 10 n = 30 draws are positive in all
three segments, not 0 of 10.

### 2, material, mean-matching of `measured_8` - CONFIRMED

The critique is right and the new cell 27 quantifies it from `VOL_DROP_LOG`: `incumbent_30`
removes 3.93 measured vaults per decision in the sparse regime, 3.17 in the dense one and 22.23 in
the late one, while `measured_8` removes exactly 8 on every decision. They are matched on the mean
and matched on no single date. The heading now says so in the Method section and calls the
comparison a decomposition by analogy rather than an exact one. Codex's code fix - drive
`measured_only` from the incumbent's realised per-date count - is a new experiment and was not
run.

### 3, material, "small real effect" and "survives every robustness check" - CONFIRMED

The paired bootstrap in cell 45 gives `measured_8` a Sharpe difference against the anchor of
+0.213976 with a 95% lower bound of -0.038933, -0.038394 and -0.038548 at blocks 5, 10 and 20.
Every interval contains zero. The heading never mentioned the bootstrap while claiming a real
effect that survives every robustness check, and it also fails constraint 4 and the late-period
check. Rewritten to "a modest in-sample improvement, and only on return", with the interval
quoted.

### 4, material, the sparse-regime mechanism - CONFIRMED, and the stated mechanism is FALSE

Verified rather than reworded, because the log carries the answer. Cell 27 shows the smallest
pre-April unmeasured pool for `incumbent_30` is **17**, not "always more than 30", and that it
removes 3.93 measured vaults per decision before April, with 13 on one date. So the sentence "it
removes no volatile vault at all" is simply wrong. The sparse-regime CAGR identity itself survives
at the four decimals cell 43 reports, but for a different reason, and the heading now gives the
mechanism the log actually supports: the unmeasured pool floor falls from 17 to 2 in the late
period, so 22.2 of the 30 removals become measured ones exactly when the edge appears. Codex is
also right that the necessary condition is "at least 30", not "more than 30".

### 5, material, the comparator family - PARTIAL

Confirmed on the facts: `FAMILY_DROPS` is `range(5, 61, 5)`, twelve members, and NB21 ran all
twelve, so cell 27's old comment "the same configurations NB21 ran" was wrong for five of twelve.
Both the comment and the Robustness bullet now say it is a 10-step subset used as a diagnostic
reference only.

Rejected in part on the consequence and on the reason. No number moves: the comparator
`bootstrap_margin_table()` picks for `measured_8` (cycle vol 0.149361) is the highest-Sharpe
member at or below that volatility, which is `incumbent_30` at 0.149229 / 2.747391 - and 2.747391
was the highest cycle Sharpe in NB21's complete twelve-member family, so the full family would
select the same comparator. And the heading's reason for skipping constraint 7 - "the comparator
family is drawn from the runs under test" - is true as stated; Codex read it as a claim about
self-comparison, which is a different argument.

### 6, material, weight frames keyed by token symbol - CONFIRMED, and it did bite

`weight_frame()` summed positions into `rows[ts][name]` where `name` was the base token symbol, so
two vaults sharing a symbol merged into one column. Now keyed by lower-case pool address, with the
symbol kept as the display label and an address suffix added wherever a symbol is shared. The
anchor needed no suffix, but `distinct_vaults_held` moved from 32 to 33 for `incumbent_40` and
from 33 to 34 for `incumbent_50`, so at least one collision exists in this universe and the old
count was a count of symbols. No other weight statistic moved, because the colliding vaults were
never held at the same time.

One thing checked and found CORRECT in the same function, which Codex did not raise: the
timestamp alignment and the denominator. `weights["mean_invested"]`, computed from
`state.stats.positions` over `state.stats.portfolio` equity, reproduces the panel's
`mean_invested` to four decimals on every one of the 40 runs, including 0.9311 for a random draw
that is materially less invested than the anchor. Credit-supply positions are excluded and the
`other` bucket and the concentration metrics are all computed on the same row-normalised
denominator.

### 7, minor, `passes_v3` named in the markdown - CONFIRMED

Cell 28's markdown promised `passes_v3` over constraints 1 to 7; cell 29 creates `passes_1_to_6`
and `failed_1_to_6`. Markdown corrected.

### 8, minor, Realist Capital's lifetime figures - CONFIRMED

105.5% lifetime CAGR, 1.24 lifetime Sharpe and 68.3% lifetime maximum drawdown appear in no cell
of this notebook, and are not in NB13's age-barrier tables either. Removed. The point they were
making is now made with this notebook's own number: masking that vault costs the anchor-equivalent
`unmeasured_30` 14.0 percentage points of CAGR.

### 9, minor, "38 stacked-area figures" - CONFIRMED

22 charted plus 18 uncharted is 40. Corrected in the cell and in the heading, and the print now
derives it from `len(runs)`.

### Also checked and found correct

- Claim 1 is not a no-op branch, as Codex says: 126 logged decisions with 21.26 removals each, and
  `unmeasured_40` removes 24.25 of a mean pool of 25.66 and still reproduces the anchor. The
  heading no longer says "removing them changes no trade at all", which was never measured, only
  that no reported metric moves.
- Every cell citation in the old heading was correct, including the ones that looked like
  off-by-ones. All citations were re-derived after two cells were inserted.
- Every other numeric claim in the old heading matched its cited cell: 11.10 pp, 0.22 pp, the 98%
  arithmetic, the segment figures, the leave-one-vault-out figures, the 4.6% ulcer improvement,
  and the 767-second run time.

### Open, not an error

`comparison` is built before the three leave-one-vault-out runs are recorded, so `manifest_26.json`
carries the 40 main runs and not the masked ones - the headline single-vault numbers are in the
notebook output but not in the manifest. Fixing that would reorder the notebook for no analytical
gain, so it is recorded here instead.
