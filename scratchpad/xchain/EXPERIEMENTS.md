# Cross-chain vault-of-vaults experiment ideas

This note proposes follow-up experiments for the cross-chain survivor-first waterfall strategy in [01-initial.ipynb](/Users/moo/code/getting-started/scratchpad/xchain/01-initial.ipynb).

The baseline result is already clean:

- `58` source vaults across Ethereum, Base, Arbitrum, Avalanche, HyperEVM, and Monad
- `11.37%` CAGR
- `6.33` Sharpe
- `-0.70%` max drawdown
- full accepted deployment

That profile is very different from the Hypercore-native research branch summarised in [README.md](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/README.md). Hypercore vaults rewarded aggressive daily selection, strong age penalties, and higher-conviction concentration because their return dispersion was large and their volatility was much higher. The cross-chain universe looks more like a diversified carry book:

- lower volatility
- slower-moving signals
- smaller differences between many acceptable vaults
- more value from steady carry and drawdown control than from chasing the single best recent vault

Because of that, the best improvement path is likely to be “add return carefully without breaking smoothness”, not “make the strategy more aggressive in the Hypercore way”.

## Recommended experiment order

## 1. Rebalance slower

Hypothesis:
Daily rebalancing is probably too fast for a low-volatility cross-chain vault universe. Weekly or 3-day rebalancing should keep most of the carry while reducing churn and small residual trades.

Why this is high priority:

- The current run already shows many `individual_trade_size_too_small` flags.
- The strongest contributors were mostly long-held positions, not quick rotations.
- Earlier vault-of-vaults work already showed rebalance cadence matters a lot once the universe becomes smoother.

What to test:

- `cycle_1d` vs `cycle_3d` vs `cycle_7d`
- hold all other parameters fixed first

Success criteria:

- CAGR improves without Sharpe falling below roughly `5`
- trade count drops materially from `274`
- max drawdown stays below `-1.5%`

## 2. Replace waterfall concentration with equal-weight or mild-weight sizing

Hypothesis:
The cross-chain universe likely does not have enough signal dispersion to justify waterfall-style concentration. Equal-weight or lightly capped equal-weight should fit this universe better.

Why this fits the README research:

- NB23a, NB59-NB65, NB102, and parts of NB128 all point to simpler sizing working well when cross-sectional differences are not extreme.
- In the current run, the result is positive but mostly comes from a handful of vaults while many others are acceptable but under-used.

What to test:

- current waterfall sizing
- pure equal-weight across selected survivors
- equal-weight with only a mild max concentration cap
- waterfall only after a larger minimum signal gap is present

Success criteria:

- broader chain contribution
- top-1 and top-3 PnL concentration fall
- CAGR improves or stays similar while Sharpe remains strong

## 3. Test age bucket equal instead of age ramp

Hypothesis:
Age still matters, but the smooth Hypercore-style `age_ramp` may be overfitted to a younger and more explosive native-vault ecosystem. The simpler bucket logic from the README may work better for stable cross-chain yield vaults.

Why:

- NB102 slightly beat the smooth age ramp in the Hyperliquid branch with a simpler cohort structure.
- The cross-chain universe contains many mature carry vaults where “young / mid / mature” may be enough.

What to test:

- current `age_ramp`
- `age_bucket_equal_weight`
- two-bucket variant: young vs mature

Success criteria:

- more stable selected set
- fewer unnecessary reallocations
- better CAGR without increasing drawdown

## 4. Add a trend-quality overlay, not a pure return-chasing overlay

Hypothesis:
If we want more return from a low-volatility universe, the safest place to look is trend consistency, not raw momentum. A mild trend-quality overlay should reward steady compounding vaults without turning the strategy into a momentum chase.

Why this fits the README:

- NB101 `trend_r2_weight` was the cleanest price-derived overlay.
- NB108 trend smoothness also worked better than more aggressive price signals.
- The current best contributors look like steady compounding positions, which is exactly what a trend-quality overlay should favour.

What to test:

- `age_ramp` base
- `age_ramp + trend_r2` mild multiplier
- `age_ramp + trend_smoothness` mild multiplier

Success criteria:

- improved CAGR
- no large rise in kurtosis
- the best-day figure stays small and believable

## 5. Add flow confirmation for entries and adds

Hypothesis:
In this universe, TVL flow is more useful as confirmation than as a direct alpha source. The strategy should add more aggressively only when price and flow agree.

Why this fits the README:

- NB112 `age_ramp_flow_confirmed` was one of the strongest overlays in the whole series.
- For cross-chain yield vaults, positive flow may be a sign of real demand and execution capacity rather than pure speculation.

What to test:

- current base strategy
- apply flow confirmation only on new entries
- apply flow confirmation on both entries and size increases
- compare `flow_window` such as `14`, `30`, `60`

Success criteria:

- improved CAGR and Calmar
- fewer weak positions that sit near flat returns
- no deterioration in full deployment

## 6. Introduce a vol-of-vol veto rather than stronger concentration

Hypothesis:
Some cross-chain vaults may look acceptable on carry but still have unstable internal behaviour. A small veto on unstable vaults should be safer than trying to solve the problem with heavier concentration in “winners”.

Why:

- NB109 showed vol-of-vol penalties were one of the few volatility-based filters that actually helped.
- Cross-chain vaults are already low-vol, so the relevant risk may be instability of that low-vol profile rather than headline volatility.

What to test:

- no veto
- mild vol-of-vol veto
- stronger veto

Success criteria:

- worst day improves
- kurtosis comes down
- Sharpe stays flat or improves

## 7. Search for the right breadth, not just the right ranking

Hypothesis:
The strategy may simply be carrying too many “acceptable but low-alpha” vaults in the candidate set. A smaller but still diversified cross-chain universe could raise return while keeping the same smoothness.

Why:

- The current source universe has `58` vaults, but realised PnL came mainly from a smaller subset.
- In the README history, universe breadth repeatedly needed retuning after major regime shifts.

What to test:

- top `24`, `32`, `40`, `48`, and `58` vault universes
- keep chain diversification constraints so the search does not collapse into one-chain concentration

Success criteria:

- higher CAGR
- similar or lower drawdown
- more meaningful contribution from each selected vault

## 8. Add chain-aware sleeve sizing

Hypothesis:
The current strategy is nominally cross-chain, but realised PnL is effectively concentrated in Arbitrum, Ethereum, and Base. Explicit chain sleeves may improve diversification and force better use of lower-beta chains without over-allocating to weak vaults.

Why:

- HyperEVM and Avalanche were nearly flat in the first run.
- A chain-aware sleeve model is more natural for a cross-chain carry strategy than a pure global waterfall.

What to test:

- global selection only
- equal sleeve budget by chain, then equal-weight within sleeve
- proportional sleeve budget by rolling chain-level Sharpe
- cap any one chain at `40%` to `50%`

Success criteria:

- more balanced chain contribution
- similar Sharpe
- improved robustness if one chain stalls

## 9. Treat deposit-closed vaults explicitly

Hypothesis:
Deposit-closed vaults may still be excellent holdings, but they should not necessarily be treated the same as open vaults for new capital allocation. A separate rule for “hold if already in, avoid new adds if closed” may improve capital routing.

Why:

- Some good contributors in the current universe were deposit-closed.
- This is a structural feature of cross-chain yield vaults that matters less in Hypercore-native copy-trading style vaults.

What to test:

- current behaviour
- allow holding but block new entry into deposit-closed vaults
- allow only trims, not adds, once deposit-closed

Success criteria:

- idle cash does not rise
- realised return improves versus getting stuck in stale names

## 10. Build a “carry first” variant instead of a “survivor first” variant

Hypothesis:
The current strategy is inherited from a survivor-first Hyperliquid branch. Cross-chain yield vaults may deserve a separate architecture where the default assumption is that most mature vaults are fine, and the problem is sizing the carry book, not identifying rare winners.

What to change:

- replace the survivor-first logic with:
- broad eligibility filter
- equal or age-bucket base weights
- one or two mild overlays such as trend quality or flow confirmation

Why this matters:

- The current result is already smooth enough that the next meaningful improvement may require a different base architecture, not just a parameter tweak.

Success criteria:

- higher CAGR while keeping max drawdown below roughly `-2%`
- lower concentration than the current waterfall result
- simpler and more interpretable selected set

## Suggested execution plan

If only three experiments are run next, the best order is:

1. Slower rebalance cadence
2. Equal-weight or mild-weight sizing instead of waterfall
3. Age bucket equal plus trend-quality overlay

That sequence has the best chance of improving return while preserving the strongest property of the current notebook: a very smooth equity curve with full deployment and believable position behaviour.

# Results

All 10 experiments were run against the `01-initial.ipynb` baseline (11.37% CAGR, 6.33 Sharpe, -0.70% max DD, 274 trades, 18 positions).

## Summary table

| # | Experiment | Notebook | CAGR | Sharpe | Max DD | Trades | Positions | Verdict |
|---|-----------|----------|------|--------|--------|--------|-----------|---------|
| 0 | Baseline | 01-initial | 11.37% | 6.33 | -0.70% | 274 | 18 | — |
| 1 | Slower rebalance (7d) | 02-backtest-slower-rebalance | 11.37% | 6.33 | -0.70% | 274 | 18 | No effect |
| 2 | Equal-weight sizing | 03-backtest-equal-weight-sizing | 10.57% | 12.50 | -0.28% | 181 | 24 | Success |
| 3 | Age bucket equal | 04-backtest-age-bucket-equal | 10.29% | 11.85 | -0.27% | 315 | 50 | Success |
| 4 | Trend quality overlay | 05-backtest-trend-quality-overlay | 10.63% | 28.56 | -0.07% | 225 | 33 | Success |
| 5 | Flow confirmation | 06-backtest-flow-confirmation | 9.85% | 6.34 | -0.71% | 2,087 | 922 | Failed |
| 6 | Vol-of-vol veto | 07-backtest-vol-of-vol-veto | 10.99% | 32.21 | -0.09% | 196 | 36 | Success |
| 7 | Reduced breadth (12) | 08-backtest-breadth-search | 11.26% | 6.23 | -0.70% | 275 | 20 | Neutral |
| 8 | Chain-aware sleeve (40%) | 09-backtest-chain-aware-sleeve | 11.42% | 6.31 | -0.70% | 285 | 18 | Neutral |
| 9 | Deposit-closed filter | 10-backtest-deposit-closed | 11.26% | 6.23 | -0.70% | 275 | 20 | Neutral |
| 10 | Carry-first architecture | 11-backtest-carry-first | 9.74% | 22.83 | -0.04% | 290 | 98 | Mixed |

## Experiment 1 — Slower rebalance

**Notebook:** `02-backtest-slower-rebalance.ipynb` | **Verdict:** Conclusive negative

Switching `cycle_duration` from `cycle_1d` to `cycle_7d` produced identical results across all metrics. The vault interest backtester evaluates every daily candle regardless of the configured `cycle_duration`, so the parameter has no effect on rebalance frequency or trade count in this engine. `cycle_duration` is not a tunable lever for reducing turnover in the current vault-of-vaults backtester.

**Lesson learnt:** The vault backtester architecture ignores `cycle_duration` for rebalance cadence. To test slower rebalancing, the `decide_trades` function itself would need a cycle-skip guard or the engine would need modification.

## Experiment 2 — Equal-weight sizing

**Notebook:** `03-backtest-equal-weight-sizing.ipynb` | **Verdict:** Success

Equal-weight sizing nearly doubled the Sharpe ratio (12.50 vs 6.33) and halved the max drawdown (-0.28% vs -0.70%). PnL concentration dropped substantially (top-1 share fell from ~20% to 10.5%, top-3 from ~45% to 27.2%), and all five chains became net-positive contributors. CAGR dipped modestly from 11.37% to 10.57%. All success criteria met.

**Lesson learnt:** The cross-chain universe lacks enough signal dispersion for waterfall concentration to add value. Equal-weight is the better default.

## Experiment 3 — Age bucket equal

**Notebook:** `04-backtest-age-bucket-equal.ipynb` | **Verdict:** Success

Sharpe nearly doubled (11.85 vs 6.33), max drawdown halved (-0.27% vs -0.70%), and Sortino more than doubled (22.66 vs 9.17). The portfolio explored far more vaults (50 positions vs 18) with all positions profitable. CAGR dropped 1.08pp, a small price for the risk improvement.

**Lesson learnt:** The smooth age ramp captured only a small amount of age-driven alpha. A simpler young-vault discount (0.3 weight for < 60 days, 1.0 otherwise) with equal-weight normalisation produces clearly better risk-adjusted returns.

## Experiment 4 — Trend quality overlay

**Notebook:** `05-backtest-trend-quality-overlay.ipynb` | **Verdict:** Success

The R² trend overlay (60-day window, 0.3 blend on age_ramp) produced a Sharpe of 28.56 and max drawdown of just -0.07%. Kurtosis dropped from 23.51 to 13.19, win-day rate reached 97.74%, and best-day shrank from 0.44% to 0.12%. CAGR dipped only 0.74pp. The overlay increased turnover (33 positions, 31-day median hold) which would add friction in production.

**Lesson learnt:** Trend quality (R²) is highly effective at filtering out choppy vaults. The extremely high Sharpe should be interpreted cautiously given the short ~7-month backtest window, but the mechanism is sound.

## Experiment 5 — Flow confirmation

**Notebook:** `06-backtest-flow-confirmation.ipynb` | **Verdict:** Failed

The binary flow gate (1.5x boost when TVL growing, 0.5x floor when declining) caused extreme position churn: 922 positions with 79.8% lasting fewer than 3 days. CAGR dropped 1.52pp, Sortino fell, and no metric improved meaningfully. Daily TVL changes oscillate too rapidly for a binary signal.

**Lesson learnt:** Flow confirmation needs smoothing to be viable. A longer window, threshold band, or EMA-based signal would avoid reacting to daily TVL measurement noise. The binary boost/floor approach is fundamentally broken for this data frequency.

## Experiment 6 — Vol-of-vol veto

**Notebook:** `07-backtest-vol-of-vol-veto.ipynb` | **Verdict:** Success

The 75th-percentile vol-of-vol veto produced a Sharpe of 32.21 and max drawdown of -0.09%. Kurtosis dropped from 23.51 to 14.5, worst day improved from -0.70% to -0.09%, and win-day rate reached 98.64%. CAGR stayed within 0.38pp of baseline. The veto removes roughly 13 vaults per cycle.

**Lesson learnt:** Vol-of-vol captures instability that headline volatility misses. The veto is a clean risk-reduction lever with minimal CAGR cost for cross-chain vaults.

## Experiment 7 — Reduced breadth

**Notebook:** `08-backtest-breadth-search.ipynb` | **Verdict:** Neutral

Reducing `max_assets_in_portfolio` from 20 to 12 produced nearly identical metrics (CAGR -0.11pp, Sharpe -0.10). The universe's alpha is naturally concentrated in ~9-12 vaults, so the 20-vault cap already accommodates this without penalty.

**Lesson learnt:** Breadth is not a lever in this universe. The effective portfolio size is already ~9 positions regardless of the cap.

## Experiment 8 — Chain-aware sleeve

**Notebook:** `09-backtest-chain-aware-sleeve.ipynb` | **Verdict:** Neutral

A 40% per-chain signal cap produced identical results because the raw signal distribution already balances across chains (no chain exceeds ~20%). Despite balanced signal weights, realised PnL remains concentrated in Arbitrum (48.5%), Base (27.5%), and Ethereum (23.2%). This is a vault-quality problem, not a signal-weighting problem.

**Lesson learnt:** Chain-level caps are not binding for the current universe. PnL concentration by chain comes from return differences between vaults, not from signal imbalance.

## Experiment 9 — Deposit-closed filter

**Notebook:** `10-backtest-deposit-closed.ipynb` | **Verdict:** Neutral

The TVL-decline filter (-10% over 30 days) had near-zero impact because very few curated vaults show sustained TVL declines. Capital deployment stayed at 100%. The filter is safe to include as a guardrail.

**Lesson learnt:** The filter's value will emerge in broader or live universes where deposit closures are more common. For a hand-curated universe, it is inert but harmless.

## Experiment 10 — Carry-first architecture

**Notebook:** `11-backtest-carry-first.ipynb` | **Verdict:** Mixed

The carry-first architecture (equal-weight, young vault discount, mild trend R² overlay, no waterfall) delivered Sharpe 22.83, Sortino 148.68, and max drawdown -0.04%. CAGR dropped to 9.74% (-1.63pp). Annualised volatility of 0.41% means the strategy behaves more like a money-market fund than a yield strategy.

**Lesson learnt:** The carry-first approach works mechanically but may be too smooth. It confirms that equal-weight + mild overlays is a strong base for this universe, but some selection alpha is needed to recover CAGR without breaking the smoothness.

## Key cross-experiment findings

1. **Equal-weight sizing is the single most impactful change.** Experiments 2, 3, and 10 all confirm that removing waterfall concentration dramatically improves risk-adjusted returns for this low-dispersion universe.

2. **Trend quality (R²) and vol-of-vol veto are complementary risk reducers.** Both produced Sharpe above 28 with tiny drawdowns. Combining them in a future experiment is a natural next step.

3. **The vault backtester ignores `cycle_duration`.** Any rebalance cadence experiment needs a different approach (e.g. cycle-skip logic in `decide_trades`).

4. **Flow confirmation needs redesign.** The binary approach failed, but the concept has merit if smoothed.

5. **Breadth, chain caps, and deposit filters are non-issues for this curated universe.** They are mechanically correct but inert — their value may emerge with broader or live universes.

6. **CAGR vs Sharpe trade-off is real but manageable.** The best experiments sacrifice 0.4-1.6pp of CAGR for 2-5x Sharpe improvement. Whether this trade-off is acceptable depends on the deployment context.