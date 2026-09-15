# Addendum for plan 34 (NB34-NB36): what changed since NB28-NB33

Read the shared context above first. This addendum states what plan 34 changed and what the
reviewer should scrutinise. The plan file `34-volatility-tail-exclusion-plan.md` (Draft 2) and
the amended `RESEARCH-RULES.md` are included below.

## The mechanism under test

One mechanism, never a ranker: before the incumbent ranks its candidates, exclude the eight with
the lowest finite stability signal (the eight most volatile of those that can be measured) and
let the incumbent rank and size the rest exactly as before. Centre `calm_8` uses `calm_score` -
`inverse_vol` masked to NaN unless at least 30 of the trailing 90 rows are price-changing marks
and the last one is within 10 rows. Calendar reference `measured_8` uses raw `inverse_vol`. Both
are permissive: an unmeasured candidate is kept. The count of eight was found by search in
NB26 and is frozen as an exploratory choice; the plan says so.

## The six rule amendments (A1-A6), frozen BEFORE NB34 was built, after a Codex review of the plan

- A1. Gate 5 stability targets: forward volatility and forward downside only. Forward event
  concentration is dropped as a target (its measurement is compromised on sparse data) and kept
  as a diagnostic.
- A2. Gate 5 return clause: per date, the MEDIAN forward 30-day log NAV return of the retained
  set minus that of the excluded set at the mechanism's ACTUAL exclusion (the eight, determined
  on the full pool from decision-time information before any row is dropped for a missing
  outcome), averaged over dates; the simultaneous lower bound must exceed -0.005. A
  catastrophic-loss share (forward return < -0.5 log) is reported beside it as a diagnostic.
- A3. Gate 8: `mean_holdings >= 5.95` (absolute) instead of >= the anchor's 6.00.
- A4. Gate 3 is scored on its VOLATILITY leg only, on dates common to candidate and anchor from
  2026-04-01, unevaluable (= fail) below 40 such dates; both concentration indicators are
  reported as diagnostics with coverage.
- A5. Gate 9: at least 19 distinct null draws (add-one p = 0.05); null runs' turnover and basket
  persistence reported beside the centre's.
- A6. Fee differential: the independent redemption-fee recomputation's net signed discrepancy,
  candidate minus anchor, as a share of the candidate-minus-anchor final-equity difference, must
  be below 0.25 in absolute value for a SHORTLIST; otherwise DIAGNOSTIC.
- Scope: gate 5 is evaluated on decisions on or after 2026-04-01 only (the polling-density
  break); pre-break decisions are screened as a diagnostic.

## What the code adds

- `_build/harness_rules_v3.py` (loaded after `harness_rules.py` and `harness_rules_v2.py`,
  redefining by name): two-signal family, two targets, `actual_exclusion_flags()` mirroring the
  splice's sort `(sign * value, pair_id)`, `verify_exclusion_flags()` against a real count-8
  run's log on dates where the pools are identical, `verify_signal_reads()` against the in-trade
  values, a nine-statistic `_statistics_from()` (2 signed Spearman, return Spearman, 2 tail
  contrasts at the actual exclusion, median return contrast, two crash shares, excluded rows in
  sample), `screen_table_v3()` with three families (stability and returns gated, tails
  diagnostic), coverage and guard-reason tables.
- `_build/harness_rules_v3_gates.py` (NB35, NB36): `gate_3_v3`, `gate_8_v3`,
  `null_effectiveness_v3`, `turnover_and_persistence`, `independent_fee_audit_v3` (the NB31
  recomputation unchanged), `fee_differential`, `gate_row_v3`.
- `_build/blocks_floor.py` (from NB32) supplies `calm_score`.

## Things to check hard

1. The median return contrast: is it computed on the sample it claims (complete-case rows with
   the exclusion flag set on the FULL pool), is the bootstrap's vault-cluster repeat handled
   correctly when a median is taken over repeated rows, and is the simultaneous bound formed
   over the right family? The observed clause fails on WIDTH (lower bound around -0.29 against a
   margin of -0.005 with a positive observed contrast). The heading says the clause as written
   is effectively a superiority test at about +0.38. Is that arithmetic right, and is the
   conclusion that "no clause on the excluded tail's forward return can be resolved on this
   sample" justified or overstated?
2. `actual_exclusion_flags()` versus the splice: tie order, the `min(count, measured)` rule,
   direction sign, and whether the panel's `value_at_prior` read really equals the in-trade
   `get_indicator_value` read (the notebook asserts 0.0 difference on every row - check the
   assertion is doing what it says).
3. The coverage finding: `calm_score` masks 17.7% of measured candidate-dates post-break and
   70.9% pre-break, not "a few percent" as the plan expected. The heading says masked vaults are
   OLDER than measured ones and explains why the masked set changes the exclusion enough to
   remove most of `measured_8`'s edge (`calm_8` Sharpe 2.171 vs `measured_8` 2.374 vs anchor
   2.160). Is the deduction in finding 4 (the two exclusion sets can only differ when one of the
   raw bottom eight is masked) logically sound given the code?
4. Standing rule 2: the return clause is pre-registered and stands; the notebooks report the
   failure and do not move it. Check that no threshold was moved after results and that the
   diagnostic sections are labelled and do not leak into verdicts.
5. Everything in the earlier calibration list: cycle clock, look-ahead, ddof, rows vs days,
   silent no-op string replacements in heading generators, elided failure strings.
