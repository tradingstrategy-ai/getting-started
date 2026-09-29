NB29’s REJECT verdict remains correct. Gate booleans and the complete eight-gate failure string in cell 35 agree with the displayed results.

Findings:

- **Material — cells 14, 45, and heading cell 0.** The attribution of the 25.7 bp stored-rate discrepancy to next-bar execution is not established, and cannot explain the reported rate discrepancy as calculated. `refresh_vault_redemption_accounting()` fixes the rate at decision time from its decision-time gross value and cost basis; settlement later applies that stored rate to the settlement-time mid-price. But cell 45 compares the stored rate with a rate recomputed from `planned_mid_price`, i.e. the decision trade’s mid-price. A later settlement price can explain a proceeds difference, not a difference between two decision-time rates. The audit currently conflates price movement and rate/basis mismatch.
  
  Fix: persist decision timestamp, gross value, cost basis and stored rate when refreshing; reconcile stored rate to those fields separately. Then derive settlement mid-price and separately reconcile settlement proceeds. Say “later settlement”, not necessarily “the next bar”.

- **Minor — cell 22.** The prior gate-5 reporting issue is substantially fixed: all real-signal bounds, samples, missingness, complete draws, and the passing `oracle_gate5` are displayed. The reachability conclusion is therefore supported. However, NB29 does not display the oracle’s draw count or its simultaneous-family size; these are only implicit in NB28’s source. 
  
  Fix: include oracle draws, complete draws, and family sizes in `manifest_28.json` and print them in cell 22.

- **Minor — heading cell 0 / `_build/build_29.py`.** The executed heading is generated correctly from manifests after the audit, but `build_29.py` still writes a placeholder heading and does not invoke `write_heading_29.py`. Thus running the named builder alone does not reproduce the reviewed notebook.
  
  Fix: document and automate the post-run heading-generation step as part of the NB29 build pipeline, or make the builder fail clearly until the generated heading is applied.

- **Minor — heading cell 0, insight 1.** “Sharpe falls with [volatility]” is slightly too broad: Sharpe rises from q=.30 to q=.40 (1.1086 to 1.3293), although it remains below q=.10 and the anchor. The preceding “deteriorates beyond q=.10” wording is defensible.
  
  Fix: say that volatility declines monotonically while Sharpe is lower than at q=.10 for every larger exclusion fraction.

What now checks out:

- The per-(date, held-vault) unrounded concentration comparison in cell 35 fixes the aggregate-cancellation issue. Equal finite masks and zero maximum differences support the claim that the original defect is unreachable on these held books.
- Cell 22 now demonstrates that gate 5 is reachable: the joint noisy foresight oracle passes both clauses and the full gate. The zero-of-thirteen result is no longer merely an unexplained universal null.
- All seven executed runs receive integrity and independent fee audits in cell 45, and the audit summary is written back to the manifest before the heading is generated.
- Anchor parity, provenance matching, strict-run path equality, cycle-clock Sharpe/volatility, plateau arithmetic, and the full failure list are correct.