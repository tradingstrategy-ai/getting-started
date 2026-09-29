NB29’s **REJECT** remains supported: the centre demonstrably fails gates 3, 4, 5, 6, 7 and 8; gates 2 and 9 correctly fail closed when unexecuted. The complete eight-gate failure string is correctly printed in cell 35.

Findings:

- **Material — cells 0 and 22.** The first review’s gate-5 evidence finding is not fixed. Cell 22 imports and displays only dates and Boolean clauses; it omits estimates, simultaneous lower bounds, complete-family draw counts, return contrasts, and the binding target. Thus “0 passed gate 5” remains merely reported, not shown to be unreachable rather than a measurement failure.  
  **Fix:** display NB28’s complete imported screen frame, decomposition, missingness, and `draws_complete` in cell 22.

- **Material — cells 20 and 22.** `forward_event_top5_excess` is a sensible correction to the raw top-five-share target: subtracting `min(5, n)/n` removes its mechanical dependence on the number of positive events. But it is a changed gate-5 construct, introduced in `harness_rules_v2.py` after the original pre-registration, while NB29/NB28 continue to call the resulting gate “pre-registered”. The original harness and plan specified raw `forward_event_top5`.  
  **Fix:** label this as a corrected post-review reanalysis, retain/report the original raw-target gate result separately, and do not describe the revised result as the original pre-registered gate.

- **Material — cells 0, 35 and 39.** The claimed proof that the corrected and original concentration indicators are “IDENTICAL … on every held vault-date” does not exist. Cell 35 only shows two aggregate means; cell 39 rounds them to six decimals before `write_heading_29.py` tests equality at `1e-9`. Equal rounded aggregates neither prove per-vault-date equality nor full-precision equality.  
  **Fix:** calculate and display a per-held-vault-date comparison for both runs, assert equal coverage and values at full precision, and feed unrounded results plus the assertion into the manifest. Otherwise say only that the displayed aggregates agree to the stated precision.

- **Material — cells 41 and 43.** The integrity and fee audits still inspect only the anchor aliases, `state`/`equity`. None of the five prefilter runs or the strict run is audited. The heading acknowledges this rather than resolving it, so the first review finding remains.  
  **Fix:** iterate over applicable `runs` entries, audit each state, label each result, and fail on any run’s reconciliation failure.

- **Material — cell 43.** Even for the anchor, the redemption audit verifies only that execution matched the fee stored in `trade.other_data`. It never checks that the stored fee equals `10% × max(gross proceeds − released cost basis, 0) + 10 bps × gross proceeds`. Therefore its heading promises more than the audit establishes.  
  **Fix:** independently calculate the expected performance and capital fee from cost basis and gross proceeds, compare each component and total to the configured/stored fee, then assert the reconciliation.

- **Material — cells 0 and 22.** The provenance claim is wrong and the asserted cross-notebook comparison is absent. The heading hard-codes a 254,818,366-byte `3e79966a` vault snapshot, whereas cell 22 reports 255,136,297 bytes and `8bce13191183c7d4`. `manifest_28.json` contains no provenance fingerprint, so NB29 cannot establish that the imported screen and rerun used the same snapshot.  
  **Fix:** persist all provenance hashes in NB28’s manifest and assert equality in NB29; generate the heading’s snapshot line from the displayed provenance result.

- **Minor — cells 0, 28 and 39.** The strict-run claim is improved but not fully established. The heading says “inert” and infers that unmeasured vaults “were never going to be selected”, yet it compares only seven rounded-to-ten-decimal panel measures. It does not compare equity paths, cycle returns, or realised baskets.  
  **Fix:** store and display full-precision metric differences, an equity/cycle-return equality assertion, and strict-versus-permissive basket differences. Cite that output, not cell 28’s four-decimal table.

- **Minor — cell 0 citing cell 24.** “Sharpe falls with [volatility]” and “destroys return” overstate the displayed family: `q=0.10` improves CAGR and Sharpe versus the anchor. The later paragraph notes the exception, but the earlier summary remains misleading.  
  **Fix:** say that volatility falls monotonically, while return and Sharpe deteriorate beyond `q=0.10`.

What checks out: the v2 return-Spearman orientation is corrected; the compounded-annual-return contrast implements the stated CAGR-point estimand; the centre’s plateau arithmetic, gate-8 arithmetic, full failure string, strict exclusion-share change, and cycle-clock Sharpe calculations are all consistent with the shown outputs.