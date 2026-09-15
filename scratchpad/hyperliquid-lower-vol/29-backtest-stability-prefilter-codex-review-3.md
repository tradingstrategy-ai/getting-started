## Review outcome

NB29’s **REJECT** verdict remains correct. The eight-gate failure string in cell 35 matches the displayed gate booleans, and the cycle-clock Sharpe/volatility, plateau arithmetic, provenance check, and all-run integrity screen are sound.

Findings:

- **Material — cells 20, 35 and heading cell 0.** The claimed “per held vault-date” proof that the original and corrected concentration indicators are identical is not implemented. `gate_3_corrected()` compares only capital-weighted, per-date book aggregates; offsetting vault-level differences can cancel. `indicators_same_dates` checks date indexes, not `(date, vault)` coverage.  
  **Fix:** build a frame keyed by decision timestamp and held vault, compare finite masks and unrounded indicator values per row, assert equality, then derive the aggregate comparison from that frame. Until then, soften the heading to “the capital-weighted daily aggregates agree”.

- **Material — cell 22; affects heading cell 0’s universal gate-5 result.** The table now correctly exposes all 13 signals’ estimates, bounds, samples and complete-draw counts; this fixes the prior reporting omission. But the new oracle display does not meet the reachability requirement. It shows only clause Booleans and the return lower bound, omits the oracle definitions/noise construction and stability bounds, and no displayed oracle passes gate 5: `oracle_vol` fails both clauses, `oracle_return` fails stability, and `oracle_all` fails return. Thus it does not establish that the screen can jointly pass a signal, nor that joint passage is impossible for this panel.  
  The observed “0 of 13” is supported, but the notebook does not distinguish a genuine stability/return trade-off from a gate construction or measurement issue.  
  **Fix:** render the complete existing oracle screen output, including construction, directions, all lower bounds, family sizes and draws; do not describe the universal null as explained or “shown unreachable” unless the displayed oracle evidence actually establishes that claim.

- **Material — cells 42–43; partially addressed only for integrity by cell 45.** The redemption-fee audit is still circular and still runs only on the anchor. It defines `performance_fee` from `configured_fee`, then verifies execution against that same configured rate. It never independently checks `max(gross proceeds − released cost basis, 0) × 10% + gross proceeds × 10 bps`; none of the six non-anchor runs receives even this limited fee audit. The heading accurately caveats this, but the audit heading itself overstates what is verified.  
  **Fix:** independently compute both fee components from each trade’s released cost basis, compare them with stored and executed fees, and run that check over every entry in `runs`.

- **Minor — heading cell 0 / `_build/write_heading_29.py`.** The statement that “every run is now audited” is static text in the heading generator, while `manifest_29.json` is written in cell 39 before the all-run integrity audit in cell 45 and contains no audit result. The executed output supports the statement, but it is not actually generated from manifest evidence as claimed.  
  **Fix:** write the completed audit summary into the manifest after cell 45 and generate this sentence conditionally from it.

- **Minor — heading cell 0, insight 6.** “Nothing is inert and everything changes a lot” overstates cell 26: no run is inert, but q=0.10 changes baskets on only 30 of 126 decisions.  
  **Fix:** say that no configuration is inert and report the 30–126 decision range.

What checks out: the second-review provenance discrepancy is fixed; the raw pre-registered gate-5 target is retained for the verdict; strict-run equality is now evidenced by exact cycle-return equality and matching cumulative held-vault sets; gate 3 still fails under both displayed aggregate constructions; and the heading’s performance figures and eight failed gates agree with their cited outputs.