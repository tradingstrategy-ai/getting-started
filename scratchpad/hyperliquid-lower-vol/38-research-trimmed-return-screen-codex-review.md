## Blocking

- **Cell 4 — stale vaults are treated as live candidates and outcomes.** The daily grid is forward-filled from each vault’s last mark all the way to the archive’s global `LAST_MARK`. TVL is also forward-filled. A vault can therefore remain eligible at T−1 with an old TVL and produce manufactured zero-return forward days after it stopped reporting. This is precisely the historic “silence is stability” failure mode. The “complete 30-day forward window” test only checks that the forward-filled grid has 30 rows, not that the vault had usable marks.

  **Fix:** retain an `observed_mark` flag before forward-fill; require a recent actual mark for eligibility and an explicit observed-mark coverage rule for forward targets. Do not let forward-filled TVL alone establish tradability.

- **Cells 0, 4 and 6 — the complete null result is not shown reachable.** The headline says no signal clears the simultaneous lower bound, yet there is no end-to-end positive-control/oracle assertion showing that this panel, bootstrap, and max-T implementation can produce a positive simultaneous bound. Given the stale-mark defect, the all-fail shape cannot be safely interpreted as an economic null.

  **Fix:** after repairing panel eligibility, add a non-reportable reachability assertion through the same statistic and bootstrap, such as an oracle diagnostic based on the finite forward-Sharpe target. It must demonstrate a positive family-wise lower bound and print finite-target coverage.

## Material

- **Cell 6 — paired p-values are not add-one corrected.** `p_two_sided` uses raw bootstrap proportions. The one-sided screen p-values use the add-one convention, but the paired differences highlighted in the heading do not. The stated 0.044 and 0.020 therefore are not computed by the claimed standard.

  **Fix:** calculate each tail as `(1 + count) / (draws + 1)`, double the smaller tail, and cap at one.

- **Cells 0 and 6 — the “trimming helps” claim is selected from a family of paired comparisons without multiplicity control.** There are 18 full-sample trimmed-minus-raw comparisons, plus cohort repetitions. The notebook gives the 90-day k=10 comparison special evidential weight because its unadjusted interval excludes zero and its unadjusted p is 0.044. The simultaneous bound applies to the 30 signal levels, not these paired differences.

  **Fix:** describe these paired results as exploratory/descriptive, or apply a pre-specified family correction to the paired-comparison family. Do not call one selected comparison the strongest finding without that qualification.

- **Cell 0, finding 2 — “trimming converts the return leg into a volatility ranker” is overclaimed.** Cell 6 supports a narrower result: `ret90_k10` has little forward-return association (0.004) and substantial signed association with lower forward volatility (0.630) and shallower drawdown (0.567). It does not show that its cross-sectional ranking is equivalent to `vol90`, nor that it selects the same vaults. Their forward-volatility correlations differ (0.630 versus 0.676), and cell 10 only shows disagreement between raw and trimmed return rankings.

  The causal explanation — removing best days “removes most of what distinguishes” high-return from low-volatility vaults — is also not established. The references to NB28–NB37 and a return cost are not evidenced by the cited cells in this notebook.

  **Fix:** state that the result is *consistent with a strong stability/volatility loading*, not that it is a volatility ranker in disguise. Keep any portfolio-return claim out of this standalone notebook.

- **Cell 0, finding 3 — “trimming the Sharpe leg does nothing” treats failure to detect a difference as equivalence.** The reported intervals straddle zero; they do not establish no effect. “A Sharpe already divides by the jumps it is made of” is an unsupported mechanism claim.

  **Fix:** say “no detectable improvement in this sample” and remove the mechanistic explanation unless directly measured.

- **Cell 0, robustness bullet — “70 decisions … are about two independent months” is wrong and not supported by cell 6.** The data span roughly 138 calendar days, so 30-day non-overlapping forward horizons amount to about 4–5, not two. The implementation itself samples five 15-decision/30-calendar-day blocks (`ceil(70 / 15)`).

  **Fix:** describe the strong overlap accurately and avoid assigning an unsupported effective number of independent months.

## Minor

- **Cell 4 — max drawdown is in log units, not the usual percentage drawdown.** `fwd_max_dd` is the minimum cumulative log-return drawdown. This does not change Spearman ranks, but calling it “forward max drawdown” without qualification is misleading.

  **Fix:** label it `fwd_log_max_dd`, or convert it to `exp(log_dd) - 1`.

- **Cells 0 and 10 — the snapshot uses a partial trading day.** `LAST_MARK` is 2026-09-16 07:25, yet cell 10 treats 16 September as a completed daily observation and annualises it like one. The displayed snapshot ranks are therefore an intraday snapshot mixed with full daily observations.

  The numeric Stratwise ranks are supported by cell 10, but “not unusual for the cohort” and “because its peers are more concentrated still” are not: no cohort distribution or concentration measure is printed.

  **Fix:** use the prior completed UTC day, or label the result as intraday and avoid annualised daily-score interpretation; remove unsupported cohort explanations.

- **Cells 0 and 4 — “zero-return day is a real flat day, not a gap” is not established.** The code discards the original mark-presence information before calculating returns, so it cannot distinguish an observed unchanged daily close from a forward-filled missing day.

  **Fix:** preserve and report observed-mark coverage; only make that statement if it is verified from the archive.

- **Cell 4 — trimming is a valid ranking transformation, but its reported “annualised return” needs clearer naming.** Return uses the original 45/90/180-day denominator after removing observations, whereas trimmed Sharpe uses the reduced sample’s mean and standard deviation. This does not affect within-window ranks, but it is not a realised investable return or Sharpe.

  **Fix:** call these “trimmed return score” and “trimmed Sharpe score”, and state the retained-period convention.

## Sections that are otherwise correct

- The trailing signal window ends at T−1; the forward returns use `(T, T+30d]`. There is no direct trailing/forward overlap or T-date signal leakage in cell 4.
- Daily annualisation with 365 and sample standard deviation (`ddof=1`) is internally consistent for this standalone vault-level notebook.
- Cell 6 does resample date blocks and vault clusters, uses the same draws across hypotheses within each screen, and forms the one-sided lower max-T bound with the correct direction for a lower bound.
- The heading’s main quoted values — panel size, best raw 180-day Sharpe correlation, table entries, and Stratwise ranks — match the cited outputs.

## Overall verdict

**DIAGNOSTIC, but not yet trustworthy as evidence.** The stale forward-fill/TVL construction is a blocking panel defect, and the all-fail conclusion is not demonstrated reachable. After those are repaired, the defensible conclusion is narrower: trimming is associated with lower subsequent volatility and somewhat higher forward-Sharpe rank correlations in this sample, but this notebook does not establish that trimming is a superior return ranker or that it has become equivalent to volatility ranking.