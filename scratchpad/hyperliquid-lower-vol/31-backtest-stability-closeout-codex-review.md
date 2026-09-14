Review findings:

1. **Blocking — cells 21, 25 and heading cell 0:** Gate 5 is not re-derived or reproduced. Cell 21 assigns `GATE_5` directly from `manifest_28`; cell 25 consumes that value. NB31 never calls `build_screen_panel()`, `joint_cluster_bootstrap()`, or `screen_table()`. Therefore “every gate re-derived” and “every result in this batch reproduces” are false: the decisive zero-of-thirteen screen is trusted, not checked. It also fails the standing requirement to show this surprisingly complete null is reachable rather than merely observed.

   Fix: rebuild the panel from the re-run `screen_log`, re-run the fixed bootstrap and screen, compare its complete output to manifest 28, and use the newly calculated Gate 5 flags. Add a fail-closed reachability assertion/diagnostic for the Gate 5 machinery.

2. **Material — cell 19, `simultaneous_ci()`:** `np.nanmax(studentised, axis=1)` silently removes invalid hypotheses from individual max-T draws. Thus each draw can maximise over a different subset of the simultaneous family, making the critical value potentially too small and the lower bounds anti-conservative. This violates both simultaneous-family coverage and the stated fail-closed rule.

   Fix: retain a draw only when every hypothesis in that family has a finite studentised statistic; otherwise discard the whole draw, report the retained count, and fail the screen if the required number is unavailable.

3. **Material — cell 19, `_statistics_from()`:** `tail_forward_return_pp` is labelled “annualised percentage points” but is calculated as an annualised difference in mean log returns:

   ```python
   (mean(log return retained) - mean(log return excluded)) * 365 / 30 * 100
   ```

   Gate 5’s margin is defined in annualised percentage points and calibrated against CAGR, not continuously compounded log-return points. Those are not the same unit.

   Fix: either define `delta` explicitly in annualised log-return points, or convert each group’s mean log return to compounded annual return before differencing, e.g. `expm1(mean_log_return * 365 / 30) * 100`.

4. **Material interpretation error — heading cell 0, Summary bullet 2:** “Nothing predicts forward event concentration” does not follow from all simultaneous lower bounds being negative. It means none of the thirteen signals established a positive association at this conservative criterion. Indeed, the saved estimates for several signals are positive; their lower bounds cross zero. This is failure to establish predictiveness, not evidence of no predictiveness.

   Fix wording: “No screened signal established positive forward-event-concentration association under the pre-registered simultaneous lower-bound criterion.”

5. **Minor wording issue — heading cell 0, insight 2:** “`inverse_vol_q30` fails the same eight gates … with every gate re-derived” overstates the output. Gate 5 is imported; gates 2 and 9 are forced false because no robustness/null runs exist. The later robustness text explains this correctly, but the headline should stand alone.

   Fix wording: “It has eight false gate flags; Gate 5 is inherited from NB28, while gates 2 and 9 were not evaluated and therefore fail closed.”

What is sound:

- Cell 16 calculates Sharpe and volatility on the native two-day cycle returns, with sample standard deviation; it does not use zero-filled daily returns.
- The strict-prior signal accessor and causal beta construction in cell 19 do not show an apparent decision-time look-ahead.
- Cell 25 prints the complete failure string; it does not truncate the eight false gate flags.
- Given an actually validated empty Gate 5 family, cell 27 correctly avoids inventing a family-wise p-value or tie-break.