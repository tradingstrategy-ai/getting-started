## Overall verdict

NB32’s second-round repairs are mostly correct, but the notebook is still not reliable under the exact stated accounting model. The earlier reviewers were wrong that Hyperliquid’s ordinary 10% leader commission is already internalised in NAV; however, NB32 replaces that mistaken blanket assumption with another: it charges every vault 10% plus an unsupported 10 bp capital fee.

I found one blocking, two material and two minor issues.

## Findings

1. **Blocking — cells 6, 8, 14, 35–36 and all principal results: the revised fee defence is only partly correct**

Hyperliquid’s ordinary vault commission is externalised. Its documentation says the leader receives 10% of followers’ profits, and its withdrawal example deducts that profit share when the follower withdraws. [Hyperliquid vault documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults), [withdrawal example](https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults/for-vault-depositors-legacy). The local data implementation agrees: normal vaults use a 10% externalised performance fee, while protocol vaults have no fee ([constants.py](/Users/moo/code/trade-executor/deps/web3-ethereum-defi/eth_defi/hyperliquid/constants.py:40), [vault_data_export.py](/Users/moo/code/trade-executor/deps/web3-ethereum-defi/eth_defi/hyperliquid/vault_data_export.py:275)).

But NB32 still implements the wrong fee schedule:

- The parameter is a universal 10%, although cell 36 itself shows 9 of 603 vaults at zero commission.
- Protocol vaults are explicitly fee-free in the local source.
- The additional 10 bp redemption-capital fee is not supported by the Hyperliquid documentation and the local exporter records zero withdrawal fee.
- Cell 36’s archive distribution establishes reported commission rates, not whether the commission is internalised in NAV. That separate conclusion is supported by the documentation and local implementation, not by the displayed table.

Because fee exposure is path- and turnover-dependent, this affects every primary comparison and cannot be repaired by interpreting the existing figures more cautiously.

**Concrete fix:** use each vault’s actual fee metadata: 10% for ordinary user vaults, zero for protocol/zero-commission vaults, and zero capital redemption fee. Then regenerate all dependent outputs. The broad underperformance of several rankers may remain, but the current exact results are not valid.

2. **Material — cells 0, 35–36: the claimed pool-cap mechanism is not demonstrated**

The new `1_000_000 × TVL` setting is, in practice, a genuine cap removal; the second-round implementation fix is correct.

Cell 36 nevertheless establishes only that removing the cap worsened the three tested configurations. It does not establish the heading’s explanation that the cap:

> stops the book concentrating into a small vault that then fails

No cap-hit counts, resulting position weights, selected small vault, or failure path are shown. Part 6 also says stability ranking favours small vaults and the cap binds, neither of which is measured there.

**Concrete fix:** remove the causal mechanism and say only that removing the TVL cap materially worsened these configurations. The current output supports direction and magnitude, not the proposed cause.

3. **Material — cells 0, 21 and 24: “most of the low volatility is cash” still compares different cycle samples**

`invested_basket_vol()` correctly uses two-day cycle returns and `ddof=1`, and usable-cycle counts are now printed. Those counts reveal the remaining problem:

- Calm: 106 usable cycles.
- Incumbent and anchor: 124 usable cycles.

The heading compares calm’s 0.1282 with the anchor’s 0.1608 and contrasts that with full-period raw volatility, even though the adjusted figures cover different calendars. Cycles with investment at or below 20% are selectively removed, so the difference cannot be attributed solely to cash.

**Concrete fix:** calculate raw and invested volatility for both configurations on the same intersection of usable cycle dates. Until then, say that the conditional invested-basket diagnostic narrows the difference, but does not quantify how much is caused by cash.

4. **Minor — cell 0 claim 5, cell 38 and `_build/write_heading_32.py`: one heading number is still hard-coded**

The generator says every number comes from `manifest_32.json`, but the decomposition manifest omits `invested_vol_cycles`. The heading therefore obtains “106 cycles” from this fallback:

```python
c15['invested_vol_cycles'] if 'invested_vol_cycles' in c15 else 106
```

The number currently matches cell 24, but only accidentally; another run could change it without changing the heading.

**Concrete fix:** write `invested_vol_cycles` into the decomposition manifest and access it without a fallback.

5. **Minor — cell 0: two numeric citations point to cells that do not display the cited values**

- Claim 6 cites cell 24 for held volatilities 0.0075 and 0.0188. Cell 24 prints only their ratio and common-date count; the underlying values appear in cell 36.
- The summary cites cell 21 for the anchor’s invested volatility of 0.1608. Cell 21 computes it but does not display it; cells 24 and 36 do.

**Concrete fix:** correct the citations or display the cited fields in the named cells.

## Earlier-review dispositions

- **Recency guard:** correctly fixed.
- **Single-window ulcer calculation:** correctly fixed.
- **Common-date held volatility:** correctly fixed. The calm/anchor factor is about 2.52 on the same 107 dates.
- **Cap removal:** correctly fixed.
- **Invested-volatility coverage reporting:** implemented, although it exposes finding 3.
- **Frontier anchor row:** correctly fixed.
- **Generated counts and figures:** 26 of 30 negative stability configurations, 79 total backtests, and the revised lookback figures match the outputs.
- **Placeholder/build-script rejection:** accepted. `write_notebook()` preserves an already completed heading; the earlier claim that an ordinary rebuild necessarily erases it was incorrect.
- **Fee-model rejection:** accepted only for the ordinary 10% externalised leader commission. Rejected for the universal rate and separate 10 bp charge.
- **Redemption-fee audit:** still tautological, exactly as the notebook now discloses. Cell 41’s stronger “verify exactly” wording remains inaccurate, but this is the explicitly deferred track-level issue.

## Interpretation wording

“The stability rankers do not work” is broader than the evidence. Four stability configurations have positive CAGR, although all substantially underperform the incumbent. A more accurate sentence is:

> In this window, these tested stability-ranker configurations underperformed the incumbent ranker.

Likewise, “fees fall hardest on whatever earns most” is too mechanical: the fee is profit-linked, but reported CAGR differences also include compounding and altered future allocations.

## Checks that passed

- Floor conversion arithmetic is correct.
- Sharpe, raw volatility and invested volatility use the native two-day cycle clock and sample standard deviations.
- Cell 34’s paired bootstrap uses shared cycle-return block indices.
- The new rankers are causal when read at T−1.
- No silent all-NaN or stale-vault degeneration remains in the three new rankers.
- Leave-one-vault-out is a full re-simulation with the intended mask and stored overrides.
- Anchor parity holds at full precision.

NB32 does not execute the gate-5 screen, two-way cluster bootstrap, simultaneous max-T bounds, add-one p-values or the ten-draw null. The “zero of thirteen signals” result is absent, so standing rule 9’s unreachable-null requirement is not applicable to this notebook. Merely loading those definitions in cell 19 provides neither evidence for nor an explanation of that result.