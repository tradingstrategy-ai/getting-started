## Review outcome

**REJECT is correct.** The centre’s complete six-constraint failure set and late-period failure are accurately reported. I found no blocking error that could turn NB22 into an adoption candidate. However, the headline “dissociation” and the causal explanation are overstated and need correction before this notebook is treated as evidence about why the mechanism failed.

## Findings

- **Material — cell 10 (`joint_loss_frequency`)**  
  `reported = (r != 0.0).astype(float)` counts `NaN` returns as reported, because `NaN != 0.0` is `True` in pandas. This contradicts the stated denominator, “cohort-down days on which THIS vault also reported”, and can reward missing marks by enlarging the denominator without allowing a loss in the numerator.  
  **Fix:** use `reported = (r.notna() & r.ne(0.0)).astype(float)` and apply the same explicit freshness predicate wherever this statistic is calculated. Re-run the affected selection results after checking whether any candidate-window observations were NaN.

- **Material — cells 48–50**  
  The within-basket diagnostic includes the mark at decision date `T` (`end_ts = ts`), whereas `decide_trades` reads indicators at `T-1`. Thus cell 49’s headline co-loss statistic is not calculated on the information set that selected the basket. This does not leak into the backtest itself, but it weakens the claim that the screen “worked on its own terms”.  
  **Fix:** calculate the selection-aligned diagnostic through the prior available bar, or explicitly label cell 49 as an ex-post realised-mark diagnostic rather than evidence about the selection signal.

- **Material — cells 49 and 51**  
  The pairwise statistic is a valid paired, per-decision-date comparison of the defined quantity; differing numbers of holdings do not mechanically lower a *mean* across pairs. The bootstrap is also correctly paired on dates, not pairs.  
  But the “four-of-six co-loss cycles” claim is not comparable: `complementary_18` holds only 5.76 names on average and has five names on 23.8% of dates. Cell 51 counts “at least four losers” regardless of whether there are five or six holdings. It therefore includes “four of five” cycles while describing them as “four of six”.  
  **Fix:** either restrict this comparison to cycles where both arms hold six names, or relabel it as “at least four current holdings lost”. Do not use the present 20% versus 24% result as a standardised six-name co-loss reduction.

- **Material — cell 14, with insufficient audit in cell 50**  
  NaNs sort last, and cell 50 shows that all-NaN degeneration did not occur for the centre: at most six of 18 reads lack an estimate. That is good. However, exact finite ties are broken by pair ID. With a ratio based on integer event counts and a minimum denominator of ten, ties at the selection cutoff are plausible. No output shows whether the six selected names were materially determined by pair-ID tie-breaking.  
  **Fix:** log the cutoff score, the number tied at and below it, and which selected slots were resolved by pair ID. If ties are material, report that the implementation partially selects arbitrary internal-ID order rather than complementarity alone.

- **Material — cells 56, 58 and 60; heading cell 0**  
  The forward pairing is correct: each score belongs to the same vault and decision date, and the return is for the following cycle. But “a statistic with no forward information” and “it fails because” overreach. The 2,106 reads contain repeated vaults and highly overlapping 180-day features; the Pearson correlation and quintile table are descriptive, not an independence-supported test. Further, the equal-weighted swap difference is −17.50 bps but its block interval includes zero, and it is not the strategy’s inverse-variance-weighted counterfactual.  
  **Fix:** say: “In this pooled in-sample diagnostic, trailing joint loss showed no clear monotone one-cycle association with return.” Describe rank displacement and the equal-weighted comparison as consistent with, not demonstrative of, the proposed failure mechanism.

- **Minor — cells 54–57; heading cell 0**  
  The staleness figures support a modest descriptive tilt towards less-frequently marked vaults: kept names have fewer fresh marks and higher stale share, while lower joint loss is associated with fewer fresh marks. But the lower extreme-thin-reporter rate among kept names cuts against a simple “the screen selected sparse reporters” story. “Measurement sparsity is a contributing tilt, not the mechanism of failure” is causal language unsupported by these summaries.  
  **Fix:** call this a mixed descriptive association, not a quantified contribution to the loss.

- **Minor — cells 25 and 29; heading cell 0**  
  The explicit result is correct: none of the **top 15** marginal-band addresses was ever funded by the anchor, and the code checks actual successful buys rather than candidacy. The broader wording that the abandoned exclusion list “would have been a list of vaults the anchor never owned” is not established for all 124 band addresses, because only the top 15 are tested in cell 29.  
  **Fix:** limit the statement to the top 15, or calculate the overlap for the complete band.

## Sections that are clean

- Anchor parity, cycle-clock Sharpe/volatility, and the paired Sharpe bootstrap are correctly implemented and reported.
- The centre’s stated failure set is complete: CAGR, Sharpe non-inferiority, volatility, ulcer, beta, and observed control; deployment passes. The late-period failure is also correctly stated.
- Part A’s set arithmetic is correct: `D20 ⊂ D30` on all 126 dates, producing a ten-address marginal band with zero reverse leakage.
- The backfill mechanism is real. Cell 14 restricts candidates to six before deposit-window filtering, so any new candidate rejected by `can_deposit()` cannot be replaced. Cell 59 correctly shows the resulting under-filled realised basket. It does not, however, quantify how much of the return loss that mechanism caused.