## Overall verdict

NB32 is not reliable as executed. The floor arithmetic, cycle-clock statistics, causal indicator reads, slim recorder and leave-one-out reconstruction are correct. However, one blocking accounting error directly biases the comparison against high-turnover stability rankers, and the fresh guard does not fully prevent stale vaults being rewarded.

## Findings

1. **Blocking — cells 6, 14 and 40: redemption fees contradict the strategy’s accounting model**

   The notebook charges a 10% performance fee on profitable redemptions plus 10 bps of redeemed capital. The supplied strategy definition says performance fees are already internalised in NAV and deposits/redemptions fill at NAV without slippage. This therefore double-counts performance fees and invents a capital fee.

   The bias is differential: stability configurations rotate through more vaults, so they incur more artificial redemption charges. Consequently, “ranking by stability fails” and the claimed sketch/engine gap cannot be interpreted from these runs. Anchor parity only proves reproduction of the same fee-bearing baseline; it does not validate the accounting assumption.

   **Fix:** set both vault fee parameters to zero and bypass the sell-tax/performance-fee adjustment for vaults, then regenerate the notebook outputs. The fee audit should instead assert NAV settlement.

2. **Material — cell 10: the freshness guard still rewards a vault after it stops reporting**

   `_fresh_count()` only requires 30 movements anywhere in the trailing 90 rows. A vault can move on the first 30 rows, then remain unchanged for the latest 60, and still score. Those 60 zeros suppress volatility and downside deviation, potentially moving the stopped vault towards the top of the ranking. `require_scored_candidates=True` does not help because the score remains finite.

   Thus the guard blocks a vault silent for the entire 90-row window, but does not generally prevent a stale vault ranking first. This is the same reward-silence failure class highlighted in the review context.

   **Fix:** combine the count guard with an explicit last-fresh-mark recency condition. Alternatively, calculate the risk statistic on fresh event returns and retain a separate recency gate.

3. **Material — cell 10: `inverse_ulcer_score` is not a 90-row statistic**

   It first calculates drawdown using a 90-row rolling maximum, then applies another 90-row rolling mean to those drawdowns. The first score therefore requires approximately 179 rows, and the final value depends on roughly 179 rows of prices with changing reference maxima.

   This contradicts `stability_rank_window = 90` and makes the ulcer ranker’s admission history materially stricter than the calm and downside rankers under `require_scored_candidates=True`.

   **Fix:** calculate the complete ulcer statistic in one 90-row rolling operation, using the explicitly intended within-window drawdown definition.

4. **Material — cells 19, 24 and 34: the held-volatility comparison is conditioned on unrelated missingness**

   `held_book_character()` excludes a date from both metrics when either volatility or event concentration lacks sufficient coverage. Consequently, `held_vol` is measured only on dates where residual event concentration also happens to be available.

   Cell 34 shows the anchor uses just 49 of 126 dates and has mean dropped weight of 52%. Different strategies can use different subsets of dates, while the coverage for the stability rankers is not printed. This does not support the heading’s claim that they hold calmer vaults “by a factor of five to twenty”, nor that the direction is reliable.

   **Fix:** validate volatility and concentration coverage separately, and compare held volatility on common eligible dates across configurations. Until corrected, describe these figures as incomplete-sample diagnostics.

5. **Material — cell 0, claim 3: cash attribution is asserted, not measured**

   Cell 23 establishes that the calm runs invest only 69–73% of equity. It does not establish that “a third of the low volatility is cash”, that the pool cap caused the cash balance, or that the advantage is smaller “after netting this out”. No cash-adjusted volatility or size-risk rejection diagnostic is shown. The uncited “Stratwise is $303k” figure is also absent from the cited cell.

   **Fix:** state only that roughly 27–31% of capital remained in cash and therefore raw portfolio volatility is not directly comparable. Remove the causal and quantitative attribution, and remove or properly source the Stratwise figure.

6. **Material — cell 0, claim 4 and summary: the “only configuration” and floor-versus-ranker claims are false**

   Three configurations beat the anchor on both observed CAGR and cycle Sharpe:

   - incumbent, 15% floor: 0.4223 / 2.3356
   - incumbent, 20% floor: 0.3972 / 2.2741
   - incumbent, 30% floor: 0.4105 / 2.1652

   None dominates the anchor on every reported risk measure, so “beat” is otherwise undefined. In addition, the tables do not confirm that the floor matters more than the ranker: at the 15% floor, CAGR spans roughly −24% to +42% across rankers, much more than the incumbent’s variation across floors.

   **Fix:** say the 15% incumbent run has the highest observed Sharpe, while three incumbent-floor runs exceed the anchor on CAGR and Sharpe. Remove the claim about which axis matters unless a defined comparison supports it.

7. **Material — cell 0, claim 6: the dependence conclusion is contradicted by its own diagnostics**

   The same vault is the largest contributor, but that does not mean dependence is unchanged. Relative to the anchor:

   - 15% floor Sharpe retention improves from 0.8248 to 0.8479.
   - 20% and 30% retention improves to 0.9297 and 0.9716.
   - Top-vault P&L share falls from 0.4192 to 0.3248, 0.2550 and 0.1484.

   **Fix:** distinguish contributor identity from contribution dependence: the same address remains largest, while several dependence measures improve.

8. **Minor — cell 0, claim 1: the negative-run count uses the wrong denominator**

   There are 22 negative-CAGR runs among all 30 stability-ranker configurations. Eighteen is the count among the 25 configurations with an explicit 0–30% floor, excluding the five “none” runs.

   **Fix:** write either “22 of 30” or “18 of 25 explicit-floor configurations”.

9. **Minor — cells 0 and 36: the backtest count is off by one**

   Cell 36 reports 69 non-anchor runs in `manifest["all_runs"]`. Including the anchor, the notebook executed 70 backtests.

   **Fix:** say “70 backtests, comprising the anchor and 69 additional runs”.

## Poor wording rather than a separate computation error

- Cell 0’s “45-day lookback is not a magic number” conflicts with the evidence immediately following it: 45 days is the only tested positive result and fails all tested neighbouring lookbacks. “Only the tested 45-day lookback was positive, making the result fragile” is accurate.
- “The largest Sharpe difference is 0.18” should be “the largest positive improvement over the anchor is 0.18”; many negative differences are much larger in absolute magnitude.
- “Stability rankers are REJECTED as selection mechanisms” generalises beyond one in-sample window and one implementation. “These tested configurations performed poorly in this window” matches the evidence.

## Checks that passed

- Cell 21’s annual-to-45-day thresholds are correct.
- “Floor = none” leaves the anchor’s 14-day, −0.16 gate intact; the incumbent/no-floor alias exactly represents the anchor configuration.
- The new indicators are causal and are read at T−1.
- Cycle Sharpe and volatility use the two-day strategy clock with sample standard deviations.
- Cell 34’s paired bootstrap shares block indices between candidate and anchor and uses cycle returns.
- The slim recorder calculates every state-dependent diagnostic before releasing state.
- Cell 33 reconstructs leave-one-out runs from the original stored overrides and the correct largest-contributor mask.
- NB32 never invokes the gate-5 screen, two-way cluster bootstrap, max-T bounds or add-one p-values. The “zero of thirteen signals” result is therefore not present here and cannot explain NB32’s results.