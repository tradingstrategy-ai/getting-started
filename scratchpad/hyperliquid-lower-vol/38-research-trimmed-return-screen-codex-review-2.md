## Blocking

None. The first review’s blocking defects are correctly repaired.

- Cell 4 retains observed-mark status before forward-fill, uses the last actual mark’s TVL for eligibility, and applies the stated forward-mark coverage/end-freshness screen.
- Cell 8 runs the oracle through the same panel, bootstrap and 31-member max-T family, prints finite-target coverage, and asserts a positive simultaneous lower bound. This establishes that the all-fail result is not a mechanically unreachable outcome.
- Cell 6 correctly uses shared resamples, add-one paired p-values, and a separate simultaneous 18-comparison paired family.

## Material

- **Cell 0 — “the one signal with any persistence” is false.** The conclusion says only `sharpe180_k0` has persistence into forward Sharpe. Cell 6 reports several other positive associations, including `vol45` (rho 0.099, unadjusted p 0.010) and trimmed-return scores. None clears the family-wise bound, but that is different from having no persistence.

  **Fix:** say “the largest observed forward-Sharpe association is the 180-day raw Sharpe; no signal is separable from zero under the family-wise bound.”

- **Cell 0 — the opening conditional overstates what this screen can establish.** “If it does not at the vault level, no ranker built on it can beat the incumbent at the portfolio level” does not follow from a cross-sectional vault-level correlation screen. Portfolio effects can also depend on sizing, covariance and selection thresholds. The notebook appropriately makes no portfolio claim elsewhere.

  **Fix:** frame this as the pre-registered workflow decision: “A failure here means the idea is not advanced to a portfolio test,” not as an impossibility claim.

## Minor

- **Cells 0 and 4 — “forward outcomes are on observed marks” is too broad.** The repaired panel requires at least ten observed forward marks and a fresh final mark, which addresses the original stopped-reporting defect. But the actual target returns still use a daily forward-filled grid; gaps inside an otherwise eligible 30-day window remain zero returns. The robustness section does disclose this later, so the calculation is not hidden.

  **Fix:** consistently describe these as “coverage-qualified, forward-filled daily outcomes”, rather than observed-mark outcomes. The existing median/5th-percentile coverage reporting supports that wording.

## Checks passed

The first-review wording fixes are otherwise correctly applied: log-drawdown naming, trimmed-score terminology, completed-UTC-day snapshot, cautious volatility-ranker language, no-detectable-improvement language, and the four-to-five non-overlapping-horizon description.

I checked the numeric heading claims against cells 2, 4, 6, 8, 10 and 12; the quoted counts, correlations, intervals, p-values, critical values, oracle bound, dates and Stratwise snapshot values match their cited outputs.

## Overall verdict

**DIAGNOSTIC, technically trustworthy after the two material wording corrections.** The zero family-wise passes are not better explained by the prior stale-mark or mechanically-degenerate-screen defects.