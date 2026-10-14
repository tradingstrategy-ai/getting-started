# Experiment 02 — restored-data rerun

## Restored-data results — 7 October 2026

Accepted-dollar caps still underperform: 9.31% CAGR versus 41.20% for the parent, with 51.32% mean cash versus 8.83%. Parent controls reproduce notebook 01 on both periods; the original-request allocation assertions pass.

### Strategy comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Fresh engine backtests on the same pinned publication and merged readers, each starting with $150,000. Full-history runs are retained separately in the saved outputs.

| Strategy | Final equity (USD) | CAGR | Sharpe | Maximum drawdown | Trades | Mean cash |
| --- | --- | --- | --- | --- | --- | --- |
| Short — v11 parent | \$194,520.81 | 41.20% | 1.96 | -6.40% | 581 | 8.83% |
| Short — accepted-dollar cap | \$160,350.69 | 9.31% | 1.31 | -4.22% | 474 | 51.32% |

Both periods completed. Historical benchmark differences are separate from mandatory equality between controls on identical inputs. See [the rerun report](restored-data-rerun-2026-10-07.md) for input and clock provenance.

<details>
<summary>Earlier analysis on the previous publication</summary>

# Experiment 02 — accepted-dollar caps

Parent: [01-initial.ipynb](01-initial.ipynb), using `hyper-ai-v11.py`, the same guard record, full indicator history and execution fixes.

[Executed notebook](02-backtest-accepted-dollar-cap.ipynb).

## Repaired-data results — 7 October 2026

The repaired source gives 33.47% CAGR, 1.63 Sharpe and −9.04% drawdown. This differs from the earlier 41.59% benchmark; the [capacity diagnostic](repaired-data-rerun-2026-10-07.md) explains most of the difference. Historical benchmark checks report differences; mandatory controls on the same repaired inputs pass. Accepted-dollar caps still leave substantial cash and reduce CAGR to 6.19%. Caps are applied to requested targets, with normal execution bands preserved.

### Strategy comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)

Fresh engine executions on the same pinned repaired inputs, with $150,000 initial equity. This is the default short period; full-history runs remain in the saved outputs and isolated artefacts.

| Strategy                    | Final equity (USD)   | CAGR   |   Sharpe | Maximum drawdown   |   Trades |
|:----------------------------|:---------------------|:-------|---------:|:-------------------|---------:|
| Short — v11 parent          | $186,418.03          | 33.47% |     1.63 | -9.04%             |      601 |
| Short — accepted-dollar cap | $156,878.83          | 6.19%  |     0.91 | -5.29%             |      513 |

Both backtesting periods completed without saved errors or warnings. Strategy parameters are unchanged. Legacy permission times remain inferred where independent receipts are unavailable.


<details>
<summary>Historical analysis before the 7 October repaired-data rerun</summary>

These earlier figures used the previous input generation and are retained as dated research history. The updated tables above are the current results.

# Why the accepted-dollar cap underperforms

Investigation of [experiment 02](02-backtest-accepted-dollar-cap.ipynb), using `hyper-ai-v11.py`, $150,000 initial capital and the two experiment 01 periods. All dates are UTC; 5 October 2026 is an exclusive end boundary.

## Conclusion

The cap implements the proposed original-request rule correctly. There is no identified percentage, volatility exponent, lookback or capital-budget unit error. It removes a redistribution step that is important to v11's allocation behaviour. Inverse-variance weights, small vault capacities and execution minimums together leave the treatment cash-heavy and underfund several profitable positions.

The inherited parameters were chosen for v11 with redistribution. Their performance does not transfer automatically to this new allocation rule. This is a strategy interaction, not evidence that a different concentration percentage was accidentally entered.

## What rule was implemented?

For each selected, allocatable vault:

```text
raw weight = 1 / max(90-day daily-return standard deviation, 0.0001)^2
original request = raw weight / sum(selected raw weights) × fresh deployable budget
accepted target = min(original request, 0.33 × fresh budget, 0.33 × vault TVL)
```

Rejected capital remains cash. Later normalisation expresses proportions of the accepted basket; explicit dollar targets prevent that normalisation from restoring full deployment. Operational checks can reduce targets further. Non-redeemable pinned holdings retain the parent's treatment.

This matches the [original accepted-dollar proposal](../hyperliquid-ic/stable-profit-plan-01.md) and the explicit E1 definition in the [rolling notebook plan](../hyperliquid-ic/rolling-profit-risk-notebook-development-plan-01.md). Those plans also request a cash-matched parent; the initial four-run experiment omitted that diagnostic, which has now been added.

The parent instead repeatedly normalises the remaining names, subtracts accepted dollars from remaining capital, and allocates that remainder to the next vault. This happens in `AlphaModel._normalise_weights_size_risk_positions` even with `waterfall=False`. Merely preventing final normalisation from increasing dollars would not reproduce the proposed experiment: v11 already preserves explicit targets at that stage.

## Parameter audit

| Setting | Experiment 01 and both primary experiment 02 arms | Finding |
| --- | --- | --- |
| Initial capital / allocation budget | $150,000 / 98% of net allocatable equity, after settlement obligations and pinned holdings | The budget is not just new cash or the buy increment |
| Decision cycle / maximum vaults | Two days / six | Preserved; maximum holdings checks pass |
| Concentration / vault TVL fraction | 0.33 / 0.33 | Correct fractional units; these are separate limits |
| Ranking / gate | 360-day CAGR + 45-day Sortino, 60/40 blend; 14-day return > −16% | Preserved |
| Sizing | Inverse variance, 90-day window, daily sigma floor 0.0001 | Correctly squares inverse volatility once; floor is 0.01% daily |
| Residual-capacity extension | Maximum capacity assets = six | Disabled in both arms, as in v11 |
| Buy / sell bands | 0.05% / 0.5% of current gross reference equity, each with $5 absolute minimum | About $75 / $750 initially; preserved |
| Tiny-position cleanup | 0.5% of the accepted basket | Preserved; can suppress positive cap targets |
| Fees | 10% of positive profit at redemption plus 0.1% capital friction | Identical source accounting in all runs |

The 33% concentration ceiling applies to the fresh budget. With 98% deployment and no other deductions, that is 32.34% of equity. Changing the denominator to gross equity would be a small policy change, not an explanation for the large performance gap.

Both parent controls still reproduce experiment 01 across all 20 metric/count comparisons. All primary cap targets satisfy final target ≤ accepted target ≤ original request. The four primary results remain unchanged after adding the diagnostics.

## Cash explains part of the loss, but allocation proportions also matter

The additional control calculates the strict cap total on its own pre-trade state, then scales the parent's accepted target proportions down to that total. This is a causal decision-time deployment control, not an exact match of realised cash paths or positions.

| Period | Strategy | CAGR | Sharpe | Maximum drawdown | Mean cash |
| --- | --- | ---: | ---: | ---: | ---: |
| Jan–Oct 2026 | Parent | 41.59% | 2.00 | −6.40% | 8.83% |
| Jan–Oct 2026 | Original-request cap | 9.33% | 1.31 | −4.22% | 51.39% |
| Jan–Oct 2026 | Cash-matched parent | 19.54% | 1.94 | −3.38% | 50.14% |
| Mar 2023–Oct 2026 | Parent | 15.82% | 1.25 | −7.92% | 41.81% |
| Mar 2023–Oct 2026 | Original-request cap | 2.10% | 0.36 | −7.92% | 70.57% |
| Mar 2023–Oct 2026 | Cash-matched parent | 3.95% | 0.60 | −7.92% | 71.32% |

The parent's allocation proportions perform better than the strict cap at broadly similar average deployment. The gap cannot be attributed solely to holding cash. Because trade paths and holdings affect subsequent decisions, these controls do not provide an exact additive decomposition into cash and weighting effects.

## The mechanism: near-flat vaults consume the initial weighting budget

On 15 April 2026, AJ Pro's preceding 90 daily returns contained 87 exactly flat observations. Measured daily standard deviation was 0.000006214%, below the source's 0.01% floor. Its raw inverse-variance weight was consequently 100,000,000. The floor prevents an infinity but still permits extreme relative weights.

AJ Pro received 99.9946% of the treatment's initial normalised budget: a $153,743.84 request. With TVL of $13,178.29, the 33% TVL limit accepted only $4,348.84.

| Selected vault | Original requested dollars | Parent acceptance on the same treatment state | Cap acceptance |
| --- | ---: | ---: | ---: |
| AJ Pro | $153,743.84 | $4,348.84 | $4,348.84 |
| pmalt | $3.95 | $50,738.20 | $3.95 |
| Realist Capital | $2.18 | $49,438.75 | $2.18 |
| Citadel | $1.08 | $24,522.30 | $1.08 |
| Delta_01 | $0.59 | $13,425.98 | $0.59 |
| Hyperrr | $0.50 | $11,278.05 | $0.50 |

The cap behaves as specified: the other five names cannot use AJ Pro's rejected budget. Their sub-$5 targets are also too small to fund meaningful positions. Flat historical returns may reflect inactivity or carried NAV; they do not establish low future risk. This investigation does not prove that AJ Pro's price data are incorrect.

The largest original weight exceeded 90% in 11.51% of short and 41.83% of long positive-weight sizing cycles. This interaction is particularly frequent over the long history.

## Which trades explain the performance gap?

Attribution uses actual USDC trade flows and marked holdings, reconciled to equity. The figures below aggregate every position in each vault, including losses and open holdings.

| Period | Vault | Parent net PnL | Cap net PnL | Parent minus cap |
| --- | --- | ---: | ---: | ---: |
| Short | Realist Capital | $24,196 | $1,562 | $22,635 |
| Short | DOEZOE | $11,075 | −$64 | $11,139 |
| Short | pmalt | $6,624 | $4,257 | $2,366 |
| Long | Delta_01 | $24,920 | $511 | $24,410 |
| Long | Realist Capital | $25,184 | $1,574 | $23,610 |
| Long | HLP | $18,005 | $3,923 | $14,082 |
| Long | DOEZOE | $11,077 | −$64 | $11,141 |

Realist and DOEZOE explain 97.73% of the net $34,559.43 short-period gap. Delta_01, Realist, HLP and DOEZOE explain 78.88% of the $92,852.23 long-period gap. These are retrospective contributors, not evidence that their future gains were predictable.

### Realist: meaningful entry versus tiny entry

On 20 June 2026, both primary arms had the same 0.2672% original weight for Realist. The parent bought $27,602.50 after redistribution; the cap bought $405.38. On 22 June, the parent added $12,152.89 versus $91.46 for the cap. Both then saw the same vault gains, but the cap had much less capital exposed. The cash-matched parent initially bought $12,107.12, illustrating that proportional cash reduction can preserve more participation than the original-request cap.

The parent's main Realist position earned $23,284.93 between 20 June and 21 August. As already documented in the notebook, several large gains were concentrated in this vault while BTC and ETH declined over matching snapshot intervals. The parent's advantage remains contributor-sensitive.

### DOEZOE: cleanup suppresses an otherwise permitted request

On 18 September 2026, the parent bought $19,184.68. The cap's desired target was $200.32: above its dollar buy minimum, but only 0.4768% of the accepted basket. The unchanged 0.5% cleanup rule suppressed the entry. It bought only $214.26 on 20 September and closed that small position on 30 September. This is a documented interaction with a shared threshold, not a decimal error in the cap.

### Delta_01: the cap exits before a profitable stretch

On 1 December 2024, the long parent bought $50,901.27; the cap bought $844.03. On 5 December the cap's original-request target collapsed to $0.36, and the cleanup rule closed its $831.31 holding. The parent remained invested. The parent earned materially more through the subsequent December gains, including the large 25 December move. The cap re-entered with only $965.36 on 19 December.

The treatment also avoided losses: short-period gaspedal losses fell from $2,804.67 to $1,013.30, and Satori losses from $2,004.99 to $599.96. These savings were smaller than the missed profitable allocations.

## Trade minimums and realised cap tolerances

| Diagnostic | Short parent | Short cap | Long parent | Long cap |
| --- | ---: | ---: | ---: | ---: |
| Buy / sell trades | 337 / 245 | 289 / 186 | 614 / 460 | 536 / 376 |
| Positive target rows below 0.5% basket cleanup | 0 | 59 | 0 | 597 |
| Positive targets below approximate dollar buy minimum | 0 | 41 | 0 | 556 |
| Modelled redemption costs | $13,078.21 | $5,944.79 | $32,359.50 | $10,795.24 |

Costs include the source's capital friction and performance fee, reconstructed from successful sell quantities, mid prices and recorded fee rates. The cap trades less capital and pays less, so excess fee drag does not explain the result. A count of ignored positive targets alone would be misleading because some unchanged holdings correctly require no trade.

The caps constrain desired targets, not instant realised holdings. Actual post-trade holdings exceeded targets by more than $1 on 265 short and 746 long ledger rows. Maximum individual excess was $783.26 and $789.85 respectively, and all excesses fit inside the approximate inherited sell band. The engine does not force every sub-threshold trim. Enforcing an absolute cap on realised holdings would require a distinct execution-rule change.

## Are different parameters likely to resolve this?

The following are same-state sizing calculations on the cap's existing selection ledger. They preserve the observed names, prices and budget. They do not rerun selection, execution, hysteresis or fees and therefore say nothing directly about alternative returns.

| Sizing calculation | Short mean accepted / fresh budget | Long mean accepted / fresh budget |
| --- | ---: | ---: |
| Current inverse variance, 33% concentration / 33% TVL | 49.63% | 32.21% |
| Same weights, 50% concentration | 55.69% | 38.10% |
| Same weights, no concentration clip | 61.40% | 47.13% |
| Same weights, no TVL clip | 69.63% | 53.81% |
| Inverse volatility, same 33% limits | 66.38% | 41.45% |
| Equal weights, same 33% limits | 78.35% | 55.39% |
| Inverse variance, daily volatility floor raised to 0.1% | 49.84% | 32.57% |

Changing 33% to 50% alone does not address the fundamental interaction. Raising the volatility floor tenfold also barely changes aggregate deployment. Flatter weights are more consequential in these calculations, but vault capacity still constrains them.

The useful next experiment would compare no-refill inverse-volatility and equal-weight sizing against the existing cap and its cash-matched control, with identical ranking and both periods. It should keep the current 33% risk limits initially, rather than increase risk limits to recover CAGR. Any change to the cleanup threshold should be isolated separately. None of those alternative returns has been established here.

## Limits

The windows overlap; this is not independent holdout evidence. Current universe membership and static guard permissions apply retrospectively, and historical deposit-state coverage starts on 11 April 2026. Initial cash-only warm-up contributes to long-period cash averages. Two-day snapshots affect daily metric timing. Full trade, allocation, sizing and executed-holdings ledgers are generated under the Git-ignored `_artifacts-analysis/` directory; the reusable diagnostics and saved table outputs are in the notebook.

</details>


</details>
