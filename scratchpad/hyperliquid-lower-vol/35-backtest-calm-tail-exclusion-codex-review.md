## Findings

- **Material — cell 0 (findings 1–2; robustness)**  
  The null result is overstated as “not distinguishable from random” and as proving that volatility-ranking information “is not what produces” the Sharpe. The defined null deliberately destroys temporal persistence as well as rank information; cell 33 confirms substantially higher turnover and more trades. It is therefore not a ranking-only null and is not an equivalence test.  
  **Fix:** say that both centres *did not clear the pre-registered, persistence-destroying random-exclusion hurdle*. Do not infer that ranking information has no contribution or name the causal mechanism.

- **Material — cell 0, robustness bullet on null churn**  
  “The null’s extra churn … makes the null HARDER to beat on transaction cost” is backwards. More turnover and trades incur more redemption fees, lowering null performance and making the centre easier to beat. Failing despite this may be noteworthy, but it does not repair the persistence confound.  
  **Fix:** state that null churn creates an extra-cost bias in favour of the centre, alongside the fact that the null also changes basket persistence.

- **Minor — cell 33 / cell 0**  
  The heading says the 19 null series are “asserted distinct”, but the code only reports `distinct_cycle_return_series`; it never asserts it. The displayed result is 19 for each centre, so this did not alter the result.  
  **Fix:** explicitly assert 19 distinct realised cycle-return series, excluded-set digests, and basket digests before making that wording.

- **Minor — cell 0 / cell 26**  
  “Random exclusion of eight measured vaults” is imprecise for `calm_8`. The splice is `min(8, measured)`; cell 26 shows `calm_8` has exclusions on only 107 of 126 decisions. The null correctly mirrors the mechanism, but it is not literally an eight-name exclusion on every date.  
  **Fix:** describe it as the “count-8 permissive mechanism: up to eight finite-signal candidates per date”.

## Checks that pass

- Cycle Sharpe and volatility use two-day cycle returns, not zero-filled daily returns. The daily Sharpe in cell 38 is clearly labelled diagnostic and does not drive H3.
- The within-date permutation retains finite-value multiplicity and NaN attachment, uses independent seeded permutations by date, and the centre rank calculation is correct: `1 +` the number of null Sharpes at least as large.
- Gate 3 correctly intersects candidate and anchor dates and reads T-1 indicator values. Its 90-row post-break diagnostic is valid here because the source is a daily forward-filled grid; the 90-day cut-off corresponds to the 90 daily rows.
- Gate 8 implements A3 correctly: the 5.95 floor replaces only the anchor-relative holdings comparison.
- The fee differential uses the correct candidate-minus-anchor signed discrepancy and fails closed when the equity gap is zero/non-finite.
- The NB34 reachability check is genuine: its bespoke oracle uses the v3 screen, creates actual-exclusion flags, and shows the return clause can pass. Thus the imported gate-5 failure is not a mechanical all-signals failure.
- Numeric heading claims checked against cells 24, 26, 28, 33, 35, 36, and 38 are otherwise consistent. Diagnostic mask/null outcomes do not enter either verdict.

## Overall verdict

**No blocking code or arithmetic defect found.** The two REJECT verdicts are correct: both fail imported gate 5, and `calm_8` additionally fails gate 4 while `measured_8` fails gate 8. The null interpretation needs the material wording corrections above; it supports failure of the specified hurdle, not causal equivalence to random removal.