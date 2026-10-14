# Experiment 09 — amended K-ratio feature forecasts

Based on experiment 09 and its Claude Opus 5.5 implementation review. The original notebook, helper sources, headline results and prospective design are preserved under the ignored `09-before-robust-amendment` namespace. The corrected notebook is edited and rerun in place, as requested.

## Fixed method before rerunning

- Use the same pinned archive, 514 snapshot identities, 2026 evaluation, four-day origins, monthly expanding fits and strictly matured labels. These are previously inspected dates, not an untouched holdout.
- Replace annualised CAGR model inputs with their exact lookback log returns. Use fold-local median-absolute asinh scales for continuous inputs, then weighted standardisation. Bound transformed test inputs to the intersection of the training range and ±5 standard deviations. Keep missing indicators binary. Record clipping and active columns.
- Fit CAGR in horizon log-return units and K in fold-scaled asinh units with ridge alpha 10. Fit raw Sharpe with a scaled pseudo-Huber loss and ridge alpha 10. Apply a fixed training 0.5%–99.5% target-range bound to level predictions, including K before inverse sinh; record affected predictions. Actual labels and statistical errors remain untrimmed. Report baseline forecasts without bounds so the treatment is explicit.
- Keep paired missing=True median imputation and zero-fill-with-indicators sensitivity. Complete-case requires the fixed 30/60/90-day inventory rather than unavailable 730-day history. Show shorter-recorded-history accuracy against the same-row baselines. Do not equate archive age with inception.
- Add matched old/K ranking companions: causal within-origin input percentiles and matured within-origin rank targets. Treat their predictions as ranking scores; do not calculate level error for those arms. Add compact availability controls as a separate paired sensitivity.
- Add a predeclared low-activity sensitivity for Sharpe/K: at least max(4, ceil(window/2)) non-zero returns with tolerance 1e-12, in feature and outcome windows. This is an exploratory cohort criterion, not proof that unchanged observed NAVs are stale. Keep the original actual-observation validity rule as primary. Future activity is a retrospective sensitivity-label validity criterion, never a forecast or entry eligibility rule; predictions are emitted using historical inputs alone.
- Evaluate paired skill within current-policy gate cohorts, disclose unknown observation clocks; compare lookbacks and daily/weekly K on identical origin/vault rows. Add activity/gap/permission/closure attrition and pessimistic/optimistic missing-outcome scenarios, explicitly conditional assumptions.
- Generate verdicts from saved result tables. Show horizon log-return forecast scatter as primary CAGR display, separate original feature scatters via the original catalogue, scientific notation for tail errors and pair counts on correlation maps.
- Audit zero NAVs and historical snapshot conditioning; do not fabricate −100% losses for empty zero-supply vaults. True inception and historical listing completeness remain unverified where metadata cannot establish them.

## Prospective status

This is an amendment on already researched data. Archive publication is not a receipt clock. Prospective confirmation remains conditional on recording genuine observation and receipt clocks, collecting sufficient complete blocks and measuring model support. Freeze this amended specification and its hashes before examining later outcomes; do not claim the future collection pipeline has been implemented.

## Numerical quality cohort supplement

Declared before its calculation: compare individual K associations under historical log-NAV RMS ≥1e−8 and OLS residual/total variance ≥1e−6. Future Sharpe/K labels additionally need daily volatility ≥1e−8 and K labels the same residual fraction. Report counts and IC against the unchanged primary validity rule. Compare existing old/K forecasts on the screened outcome cohort without refitting; this is a descriptive sensitivity, not a new trained model or an entry filter. Thresholds are not asserted to be validated data-quality standards.


## Longer K lookbacks (2026-10-09)

At the user's request, rerun experiment 09 in place with six main K inputs: 30/60/90/180/360 days and max (full recorded history). One year follows the existing 360-day convention. Max fits every actual daily NAV from the first positive recorded mark through T−1, with at least three points; any intervening missing calendar mark keeps K missing. Do not substitute a shorter trailing uninterrupted segment or compress gaps. The archive may not contain a usable year, and a young vault's max can be shorter than 180 days. Report the actual duration and availability. Recorded history is not certified inception.

Retain the four-window K arm and add year-only, max-only and both comparisons on identical target-valid observations, with shared missingness controls. Keep the model, future horizons (7/30/90 days), four-day cadence, label maturity gates and missing=True policy fixed. The complete-case sensitivity deliberately retains its supported 30/60/90-day inventory. Cache fingerprints force recomputation. The preceding corrected run, source and key results are archived in the ignored `09-before-long-k` namespace; no data refresh is performed. This amendment is exploratory on previously researched history.

## Sparse daily NAV support (2026-10-10)

At the user's request, apply causal forward filling to **all** metric features and 7/30/90-day targets. Carry only a previously observed positive NAV; retain calendar spacing and never backfill before the first mark. Fixed lookbacks still need enough elapsed recorded history. Max K starts at the first recorded mark and needs at least three fitted daily points. Flat or zero-denominator ratios stay undefined.

Historical features can carry through T−1, with actual observation age and 90-day observation fraction retained as controls. Future targets remain censored beyond each vault's last actual observation and the archive end. Preserve actual daily masks, counts and clocks separately from filled paths. Refit and recompute every affected forecast, diagnostic, scatter and verdict in place; do not refresh the archive or alter portfolio rules. Prior results and source are preserved under `08-before-sparse-fill` and `09-before-sparse-fill`. The old complete-observation verdicts are superseded by this rerun.
