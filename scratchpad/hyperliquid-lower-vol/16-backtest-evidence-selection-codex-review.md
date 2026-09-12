## 1. Do the heading's claims match the outputs?

### Key new insights

- “All 29 variants fail”: supported. Cell 27 reports `29 variant runs completed`, and Cell 29 shows `passes_v2=False` for every variant.

- “27 of 29 fail five or more constraints”: contradicted by the displayed values and rule implementation. All 29 fail at least five. For example, `sortino_shrunk__t_cap_4` fails CAGR, Sharpe, ulcer, investment and placebo; every composite fails at least six. The heading understates the failure count.

- `evidence_composite_06__no_shrink` at volatility 0.396, 2.6× the anchor, CAGR -41.8%: supported by Cell 29 (`0.395809`, `-0.418159`) against Cell 16’s anchor volatility `0.154278`.

- Best Sharpe variant `sortino_shrunk__t_cap_4` at 3.2% CAGR and 0.49 Sharpe: supported by Cell 29 (`0.032330`, `0.489856`). “Best-performing” should say “highest-Sharpe”; `no_shrink` has the higher CAGR, 4.52%.

- The description of NB14’s static screen is not independently supported in this notebook. Cell 25 only establishes the carried-over gate map:
  > `GATE_PASSED = {'sortino_shrunk': True, 'evidence_composite_0.6': False, 'evidence_composite_0.3': False}`

- Reach figures are supported by Cell 33: young-position shares are 50.5%, 79.2%, and 75.9%; young-position P&L is -$6,122, -$28,362, and -$7,703 respectively. The associated capital shares, 40.8% and 67.9%, are computed as cumulative successful-buy notional, not portfolio capital held over time; the heading should not describe them simply as “capital” without that qualification.

- “The CAGR leg makes it categorically worse” has a numerical error. Cell 29 gives:
  - `evidence_composite_06__centre`: -32.33% CAGR, -1.000 Sharpe;
  - `evidence_composite_03__centre`: **-19.52% CAGR, -0.926 Sharpe**;
  - `sortino_shrunk__centre`: -6.06% CAGR, -0.514 Sharpe.

  Thus the heading’s parenthetical “same numbers” for the 0.3 centre is false. It is the *0.6 `cagr_weight_alt`* that duplicates the 0.3 centre. Nor are the composites worse on literally every reported axis: both have positive late-period CAGR while the Sortino centre has -23.9% late CAGR.

- The comparison of `sortino_shrunk__no_shrink` with `t_cap_4` is numerically correct: Cell 29 gives Sharpe 0.487 versus 0.490 and CAGR 4.52% versus 3.23%. The causal conclusion is too strong. `no_shrink` differs sharply from the centre (-6.06%, -0.514), while `t_cap_4` changes a different parameter. The results show that no tested setting is adoptable, not that shrinkage is immaterial or that “risk-adjusted ranking at all” is the failed mechanism.

### Summary of results

- The summary table is accurate, including the anchor values from Cell 16 and the three chosen best-Sharpe variants from Cell 29.

- The claims about the worst Sortino variant (-1.52), all 0.6-composite variants being below -0.57 Sharpe, and its unshrunk control reaching -1.16 Sharpe at 2.6× anchor volatility are supported by Cell 29.

- LOVO and the paired bootstrap were correctly skipped under the implemented workflow. Cell 36 says:
  > `sortino_shrunk: skipped (centre fails v2: CAGR < 20%, Sharpe non-inferiority, ulcer (not material), invested < 90%, placebo)`  
  > `evidence_composite_06: skipped (diagnostic_only)`  
  > `evidence_composite_03: skipped (diagnostic_only)`

### Robustness

- The two duplicate patterns are supported by Cell 29 and by the construction in `_build/blocks_evidence.py`.

  - 0.6’s alternate CAGR weight is exactly 0.3, the 0.3 centre; conversely for 0.3’s alternate weight. The displayed metrics coincide.
  - Both composite `no_early_vol` rows coincide with their centres. This follows because a composite is NaN before `expanding_cagr_score` reaches `cagr_min_days=90`, while ordinary `inverse_vol` is available by then.

  “Byte-for-byte identical” is not demonstrated: there is no equality assertion over equity curves, trades, or states. The outputs establish equality to displayed precision and the code establishes why the effective parameterisation is identical.

- The Sortino `no_early_vol` variant is genuinely different, as claimed: Cell 29 gives -0.459 versus -0.514 Sharpe for the centre.

- The statement that skipping further robustness “could add nothing” is an opinion, not an output-supported result. It is fair for an adoption decision because the centre is far below every required threshold; it is not evidence that the broader mechanism is conclusively unsound.

- The claimed “many more, smaller, younger positions simultaneously” is not measured. Cell 33 counts completed/lifetime positions and cumulative buy notional, not concurrent positions or per-cycle weights. The heading correctly concedes that the volatility attribution was not separated.

## 2. Correctness of the code that produced the numbers

The run wiring is sound.

- Cell 27 uses unique labels, correctly merges each neighbour with `**{**common, **override}`, and derives `diagnostic_only` from the NB14 map. The resulting 9 Sortino and 10+10 composite runs equal 29.
- Plateau excludes only the two controls, includes the centre and every one-step neighbour, and correctly reports false for every score in Cell 31.
- The seven quantitative v2 constraints in `_build/harness_evidence.py` match the pre-registered rule: 20% CAGR, Sharpe ≥2.06, no higher volatility, 15% ulcer improvement, lower invested beta, ≥90% invested, and placebo margin.
- The default indicator accessor is safe from one-bar look-ahead. Its documented and implemented default is `index=-1`, i.e. the prior daily bar. Consequently, `sortino_cross_sectional_prior` takes a contemporaneous median at the indicator’s date, but the decision reads that prior date, not today’s unfinished bar. I found no look-ahead in the cross-sectional prior.

The strict-scoring path is also implemented as intended:

```python
if not scored and bool(getattr(parameters, 'require_scored_candidates', False)):
    continue
```

The early-vol replacement is correctly only a fallback:

```python
inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)
if inv_vol is None or inv_vol != inv_vol:
    inv_vol = indicators.get_indicator_value('inverse_vol_early', pair=pair)
```

However, there are material silent failure modes.

1. If every candidate is filtered out, the strategy returns no trades:

```python
if not candidates:
    return []
```

That also leaves existing positions open. It contradicts the nearby claim that a gated-out vault is “therefore sold”. With `require_scored_candidates=True`, this can retain an unscored or gate-failing portfolio precisely when the rule has no valid replacements. The extract does not expose per-cycle candidate counts, so its realised incidence is unknown.

2. A vault can be score-eligible after 20 fresh events but unsizeable until 45 fresh events. It remains in `selected`, receives `inv_vol=0`, consumes one of six selected slots, and can receive zero weight. This confounds the claimed isolation of selection: the Sortino runs change both candidate admission and practical deployment. The centre’s 84.2% mean investment in Cell 29 is consistent with this being important.

3. `inverse_vol_early` gates on fresh-event count correctly, but estimates volatility over the ordinary 90 calendar-day return series, including stale zero returns. Therefore stale marks still depress estimated volatility and can inflate inverse-variance weights. The fresh-count gate avoids falsely calling stale rows observations; it does not make the volatility estimator event-time.

4. There is a source/extract provenance mismatch around the already-known NB18 diagnostic overwrite. The executed extract contains both:

```python
state.visualisation.add_calculations(timestamp, {
```

for sleeve diagnostics, and later:

```python
state.visualisation.add_calculations(timestamp, {'unallocatable_signals': alpha_model.get_unallocatable_signals()})
```

at the same timestamp. The latter overwrites the former. Current `_build/blocks_evidence.py` replaces this with `SLEEVE_LOG`, but the executed NB16 extract still has the old code. It is inert here because `core_fraction=None`, so it does not invalidate NB16’s selection figures; it does mean the current generator is not an exact provenance match for the executed source.

5. `hidden_cohort_reach()` calls cumulative successful buys `entry_capital_usd`. This is not entry capital if the position was subsequently topped up. The young-share and young-P&L figures are valid under the function’s definition, but the capital-share label is misleading.

## 3. Statistical interpretation

The rejection is justified under the pre-registered rule as implemented.

- `sortino_shrunk` is the only non-diagnostic score, and its centre misses five constraints. Its plateau is false. Therefore no LOVO or bootstrap is required before rejecting it.
- Both composites are diagnostic-only because Cell 25 says they failed NB14’s descriptive gate; independently, their centres and plateau rows also fail v2 decisively.
- The code appropriately keeps `passes_v2` separate from diagnostic status, plateau, LOVO and late-period status. Cell 40 correctly returns `NB16_WINNER = None`.

The result does not justify stronger causal language.

- About 125 decision cycles, one polling-regime break, and a wholly in-sample window are enough to reject adoption of these 29 configurations, especially given their large shortfalls. They are not enough to establish that evidence-weighted allocation cannot work generally.

- The young-cohort table supports the observation that young-position P&L was negative. It does not isolate that as the cause of the collapse. The notebook does not decompose return or volatility into young versus older positions, turnover, concentrated weights, zero-weight slot blockage, or the altered sizing availability. The volatility rise to 0.396 could have several causes.

- The CAGR-leg attribution is especially under-identified. Adding the composite’s CAGR leg also introduces the 90-day score-availability gate and changes the admissible population. There is no controlled ablation that holds the candidate set and sizing behaviour fixed while changing only the CAGR weight.

- NB19’s family-wise p=1.000 is background information, not evidence computed in this notebook. It should not be used to make this notebook’s conclusions appear independently out-of-sample or multiplicity-adjusted.

## 4. What should be re-run or checked before these results are trusted

1. Freeze and compare the exact executed notebook source against a freshly generated NB16. Resolve the `SLEEVE_LOG` versus `add_calculations()` discrepancy and record the commit/hash used for the run.

2. Instrument `decide_trades` to record, per cycle: eligible candidates, scored candidates, selected zero-volatility candidates, zero-weight signals, and whether `not candidates` occurred while positions were open. Decide explicitly whether that condition should liquidate positions.

3. Require a valid positive sizing input before a candidate can consume a selection slot, or make the score admission threshold consistent with the 45-fresh-event sizing threshold. Re-run all 29 variants if either policy changes.

4. Recompute early volatility using fresh-event returns, or demonstrate that calendar-zero volatility is the intended live-trading risk measure. Then re-run the Sortino score and its early-vol control.

5. Add assertions comparing duplicate runs’ equity curves, trade lists, and panels exactly, rather than calling displayed equality “byte-for-byte”.

6. Rework the reach diagnostic to report time-weighted realised portfolio exposure and a young/old P&L and volatility decomposition. Keep cumulative buy notional as a separate turnover measure.

7. Reproduce NB14’s gate table in an immutable artefact and verify the hard-coded `GATE_PASSED` transcription.

8. Treat any future positive result as provisional until evaluated prospectively or on a genuinely untouched period; the current full-window result is in-sample.

## 5. Verdict

**RESULTS STAND WITH CAVEATS**

The central result stands: none of the 29 tested variants is adoptable, and the code has no detected feature look-ahead in the score or cross-sectional prior.

Caveats: the heading contains one incorrect composite-centre comparison and an undercount of five-or-more-constraint failures; its causal explanations overreach; the reach capital-share label is inaccurate; and strict scoring can silently retain invalid positions or allocate zero-weight slots. These issues do not plausibly turn this decisive rejection into an adoption, but they must be fixed before using the notebook to explain *why* the strategies failed.