## Overall verdict

NB32 is still not reliable as executed for the stated fee-free strategy. The recency and ulcer repairs are correct, but the original blocking fee issue remains. The new decomposition also does not genuinely remove the pool cap and therefore cannot support the headline attribution to “rebalancing dynamics”.

## Findings

1. **Blocking — cells 6, 8, 14 and all principal result cells: the fee accounting still contradicts the strategy definition**

   The main grid still charges a 10% performance fee and 10 bps capital fee. Performance fees are already internalised in the supplied NAV series, while the strategy definition specifies NAV settlement without redemption fees. Measuring three fee-off configurations does not correct the other 66 configurations or make their results representative of the stated strategy.

   In particular, the claim that all tested stability rankers fail remains based predominantly on fee-bearing runs; only calm, incumbent-at-15%, and the anchor were rerun without fees.

   **Fix:** make both fee parameters zero for the primary anchor, grid, breadth and sensitivity runs, bypass the artificial net-redemption revaluation, and rerun all dependent outputs. If the old fee-bearing baseline must remain for continuity, label it as a legacy accounting comparator rather than the strategy anchor.

2. **Material — cells 0, 35 and 36: “pool cap off” is not actually cap off**

   `NO_CAP` sets `per_position_cap_of_pool_pct = 1.0`. The size-risk model still computes:

   `accepted_size = min(TVL × cap_pct, asked_size)`

   so this remains a cap at 100% of vault TVL. This is visible in [tvl_size_risk.py](/Users/moo/code/trade-executor/tradeexecutor/strategy/tvl_size_risk.py:161) and the setting is in [build_32.py](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/build_32.py:445). The remaining 19–20% cash in the calm “no-cap” runs makes continued binding particularly plausible, but no cap-hit diagnostic is printed.

   The claim “neither fees nor the pool cap explains the gap” is therefore unsupported.

   **Fix:** disable the size-risk model for this decomposition, or use a demonstrably non-binding ceiling and assert that every requested position size was accepted.

3. **Material — cells 0 and 36: the inference that the remaining gap “is in the dynamics” does not follow**

   Even after a genuine cap removal, the comparison has not eliminated all differences:

   - The sketch used a 45-day formation window, whereas the decomposed calm ranker uses a 90-row volatility window.
   - The engine applies TVL/tradability, quarantine, deposit-window and blacklist rules.
   - The engine retains a 33% portfolio concentration limit, trade thresholds, delayed settlements and 98% target deployment.
   - Fees explain 6.69 percentage points of the calm result, so they explain a material part of the gap even if they do not explain all of it.

   “The sketch, same rule” in cell 36 is consequently false. Cell 31’s 45-row volatility run is closer to the sketch but was not used in the decomposition.

   **Fix:** describe the table as showing that these two parameter changes do not close the gap. Do not assign the unexplained remainder specifically to rebalancing.

4. **Material — cells 21 and 24: the held-volatility comparison still uses different calendar samples**

   The new volatility-only diagnostic fixes the unrelated event-concentration conditioning, but the calm ranker is averaged over 107 dates while the incumbent is averaged over 126. The stated 2.4× comparison therefore combines both portfolio composition and calendar-sample differences.

   This does not support “on a properly covered sample” as written. The first review specifically requested common eligible dates; that part was not implemented.

   **Fix:** compare configurations on the intersection of dates satisfying volatility coverage for every configuration being compared, or label the figures as separate-sample diagnostics.

5. **Material — cell 42: the redemption-fee audit is tautological**

   The audit derives:

   `performance_fee = gross_proceeds × configured_fee − capital_fee`

   and then checks executed proceeds against that same stored `configured_fee`. Although it calculates `released_cost_basis`, it never uses it to verify that the performance component equals 10% of positive redeemed profit.

   Thus the caption “Every vault redemption reconciles to performance fee plus capital fee” proves only that execution honoured the stored aggregate rate, not that the rate was calculated correctly.

   **Fix:** independently calculate:

   `expected_performance_fee = max(gross_proceeds - released_cost_basis, 0) × 0.10`

   and assert both the component fee and net proceeds against that value.

6. **Material — cell 0 against cell 24: the floor axis is not flat under the notebook’s own tolerance**

   The heading calls the incumbent result flat across floors while listing Sharpes 1.9904, 2.3356, 2.2741 and 2.1652. The 10%-to-15% gap is 0.3452, greater than the pre-registered 0.25 plateau tolerance.

   **Fix:** say the 15%-to-20%-to-30% region is locally close, but the 10% neighbour fails the stated plateau tolerance.

7. **Material — cell 0 and the build script: the executed interpretation is not reproducible from the generator**

   The executed cell 0 contains the full revised findings, but [build_32.py](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/build_32.py:72) still contains “To be filled in after the run” placeholders. Rebuilding the notebook would erase the reviewed interpretation. This violates the repository’s generated-notebook discipline.

   **Fix:** place the final heading text in `HEADING`, regenerate the notebook, and confirm the generated cell matches.

8. **Minor — cell 0 against cells 24, 31 and 38: several corrected numbers are again wrong**

   - There are **26**, not 22, negative-CAGR runs among the 30 non-incumbent main-grid configurations.
   - Cell 38 writes 78 entries to `manifest["all_runs"]`, and that comprehension explicitly excludes the anchor. The total is therefore **79 backtests: anchor plus 78 others**, not 78.
   - The 60-day lookback CAGR is **−0.33%**, not −0.2%.
   - The 90-day lookback CAGR is **−2.60%**, not −2.8%.

   **Fix:** regenerate these statements directly from the current result frames after the rerun.

9. **Minor — cell 21: invested-basket volatility lacks coverage reporting**

   Its clock, sample standard deviation and prior-cycle invested fraction are correct. The `> 0.2` mask is a defensible guard against unstable division, but it makes the statistic conditional and the notebook does not report how many cycles survive. That matters when the diagnostic supports the claim that “most” of the volatility difference is cash.

   **Fix:** return and print the usable-cycle count and excluded-cycle count alongside `invested_vol`.

10. **Minor — cell 38: the `none` frontier row silently excludes the anchor**

   Because the canonical anchor is manually marked `inert`, `~main["inert"]` removes the incumbent/no-floor observation. The row therefore reports Sortino at −0.4206 as the “best Sharpe” even though the incumbent/no-floor anchor is 2.1598.

   **Fix:** retain the canonical anchor in this frontier, or label the table explicitly as the best non-anchor configuration.

## Checks that passed

- The recency guard is correct: the first row is not treated as a move, a never-moving series remains unscorable, and a move on the last row produces zero rows since fresh.
- `inverse_ulcer_score` now uses exactly one 90-price rolling window. With `raw=True`, `_window_ulcer` receives the intended NumPy window and calculates drawdown from its internal running high.
- The annual-to-45-day floor conversion is correct.
- Cycle Sharpe, cycle volatility and invested volatility use the native two-day clock and sample standard deviations.
- The paired Sharpe bootstrap resamples candidate and anchor with shared block indices.
- The new rankers remain causal when read by `decide_trades`; the decision reads their T−1 value.
- Within the custom redemption path, setting both fee parameters to zero does remove the modelled redemption fee: asynchronous settlement uses the stored zero rate. The problem is that most primary runs do not use those zero settings.
- Leave-one-vault-out remains a full re-simulation with the correct stored overrides.
- The revised “three incumbent runs beat the anchor”, dependence, and 45-day fragility directions are correct, subject to the numeric corrections above.

NB32 does not execute gate 5, the two-way cluster bootstrap, max-T bounds, or add-one p-values. The “zero of thirteen signals” result is not present here, so standing rule 9’s unreachable-null requirement is not applicable to NB32. Merely loading those function definitions in cell 19 does not run or validate that screen.