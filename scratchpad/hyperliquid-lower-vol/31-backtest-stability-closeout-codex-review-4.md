## Findings

1. **Material — cell 41; heading cell 0:** The independent redemption-fee audit cannot support its causal attribution. It recomputes `expected_rate` from `trade.planned_mid_price` (the decision/request price), while comparing proceeds to `executed_price` (the later settlement price). This mixes price drift with fee-rate error. Moreover, a fee fixed at decision time does not itself explain a non-zero *rate* difference when the audit’s reference gross is also decision-time gross.

   The source does confirm the mechanism: cell 14’s `refresh_vault_redemption_accounting()` fixes the rate at the decision timestamp, and the executor later applies that stored rate to the settlement-time mid price. But the reported 25.7 bps / $93.49 figures do not isolate that mechanism, so “not an accounting error” is unsupported.

   Fix: record the decision gross value and cost basis on the trade, and audit separately:
   - decision-time rate versus its recorded inputs;
   - settlement-time rate versus settlement gross and released basis;
   - settlement price drift.
   
   Replace the heading’s conclusion with a neutral statement that the current audit finds a discrepancy but does not yet decompose it.

2. **Material — cell 26; heading cell 0:** The claimed agreement on “all three bootstrap families’ diagnostics” is incomplete. The comparison asserts only `critical`, complete-draw count, and used-family size. It does not compare `n_draws_total`, `n_draws_incomplete`, or `family_size_total`, although NB28 persists all of them.

   This does not alter the reproduced all-false Gate 5 flags, but it does not fully satisfy the third-round requirement or support an “every diagnostic” claim.

   Fix: compare and assert every persisted diagnostic for stability, returns, and tails; include the incomplete-draw counts in the displayed table and manifest.

3. **Minor — heading cell 0:** The opening says gates “1–4 and 6–9” are re-derived from re-run states. Cell 28 shows gates 2 and 9 were not evaluated and were instead fail-closed; Gate 5 comes from the rebuilt screen, not state-derived gate logic.

   Fix: say gates 1, 3, 4, 6, 7, and 8 are re-derived from states; Gate 5 is re-derived from the panel; gates 2 and 9 fail closed as unexecuted.

4. **Minor — NB28 cell 35, cited by NB31’s conclusion:** The oracle section says “Three oracle signals” but constructs and runs four: `oracle_vol`, `oracle_return`, `oracle_all`, and `oracle_gate5`.

   Fix: change “Three” to “Four” in the cell and generated NB28 heading.

## What is now sound

- The previous imported-Gate-5 defect is fixed: NB31 rebuilds the panel, reruns the raw pre-registered screen, and uses the re-derived flags downstream.
- The full `oracle_gate5` construction is directionally correct: low values represent the unstable/low-return end, and it passes both clauses. This demonstrates that the implemented Gate 5 can emit a pass; the zero-of-thirteen result is not an all-NaN or mechanically impossible screen.
- Native two-day-cycle Sharpe and volatility, complete-family max-T handling, raw-target verdict distinction, provenance checks, full failure string, and the cautious “failed to establish” event-concentration wording are all correct.