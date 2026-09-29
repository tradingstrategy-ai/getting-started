## 1. Do the heading's claims match the outputs?

### Key new insights

- “Every sizing method fails, including the null” is supported. Cell 29 reports `passes_v2=False` for all five variants; Cell 37 confirms both `sizing_equal` and `sizing_evidence` are `False`.

- The stated reason is materially incomplete and partly contradicted. The heading says every variant clears beta and placebo constraints, failing only Sharpe, volatility and ulcer. Cell 29 shows the opposite:
  - Anchor absolute invested beta: `0.045797`
  - Blend: `0.058039`; equal: `0.103472`; evidence: `0.115060`; all are worse, so all fail the strict beta constraint.
  - Every variant has `placebo_ref = NaN`. Cell 23 shows the non-dominated placebo envelope ends at volatility `0.149229`; every sizing variant has higher volatility, including equal weight at `0.154656`. Under the implemented rule, out-of-range placebo values explicitly fail as “not evaluable”.
  - Deployment does pass: all variants are above the 90% floor (`0.913630` to `0.960072`). CAGR also passes the 20% floor.

- “Equal weight also fails, so this is not about evidence sizing specifically” is too strong. Equal weight failing establishes that inverse variance beats this equal-weight null under the rule. It does not establish that evidence sizing is not additionally poor, nor that inverse variance is a local optimum. The only justified result is: none of the tested alternatives clears the rule.

- “`sizing_blend` is the closest miss of anything in the whole plan” is unsupported by this notebook, which contains no NB16/NB18 comparison. It is also misleading within NB17. Blend misses Sharpe by `0.011246` against the `2.059792` floor and volatility by `0.003351`, as claimed, but it also fails the ulcer requirement, beta requirement and the unevaluable placebo requirement. Its `1.48` pp CAGR sacrifice is not “an order of magnitude smaller” than the next-best NB17 sacrifice of `3.47` pp.

- “Concentration is capped, not chosen, regardless of method” is not supported. Cell 31 does support the reported range of maximum realised shares: `0.323948` to `0.328831`, and the means reported in the heading are correctly rounded. It does not show that the concentration ceiling bound in each run. In particular, equal weighting supplies raw weights of one-sixth, so the 33% target-weight cap cannot be the cause of its allocation. The observed maximum can instead reflect value drift, timing relative to rebalance, soft-band non-trading, or pool-cap effects.

- “No leave-one-vault-out or bootstrap was run” is supported by Cell 33: `sizing_evidence: skipped (diagnostic_only - SELECTION was not itself adopted in NB16)`. However, “rather than because it failed a check” is false as a counterfactual: Cell 29 shows that it also fails v2, and the next `elif` would have skipped it for that reason if `diagnostic_only` were false.

### Summary of results

- The table’s CAGR, Sharpe, volatility, ulcer and CAGR-sacrifice figures accurately round Cell 29’s results. The anchor is also corroborated by Cell 16: 37.8971% CAGR, 2.159792 cycle Sharpe, 0.154278 cycle volatility, 1.7964% ulcer, and 578 trades.

- “Every variant clears the CAGR floor and beta and deployment constraints” is false. They clear CAGR and deployment, but all fail beta; all also fail the placebo condition because `placebo_ref` is `NaN`.

- “Every variant fails on the same three” is false. The common failures are at least Sharpe non-inferiority, volatility, ulcer, beta, and unevaluable placebo. Equal-weight volatility is only `0.000378` over the anchor, but it is still over the literal rule.

### Robustness

- The floor results are correctly transcribed from Cell 29: Sharpe is `1.171`, `1.498`, and `1.565` at floors `0.0`, `0.25`, and `0.5`, respectively. The observed three-point sequence is monotonic.

- “Trends cleanly towards the equal-weight null” is only a descriptive interpretation. A floor of 0.5 does not make the weights equal; it merely raises weights below half the pre-floor mean. The notebook does not output per-cycle raw or normalised weights, score distributions, or a distance-to-equal statistic.

- The claim that lower floors prove evidence is worse is over-interpreted from three correlated in-sample runs. It is an observed pattern, not evidence of a general floor-response relationship.

- The young-vault assertion is not demonstrated. The incumbent score has a 360-day CAGR leg, but `require_scored_candidates=False` means unscored names remain candidates at signal zero. There is no per-cycle selected-ID or age output proving that no young vault entered a basket.

## 2. Correctness of the code that produced the numbers

The primary backtest path appears internally coherent.

- The evidence score is read through `get_indicator_value('sortino_shrunk_score', pair=pair)`. The repository’s alignment documentation establishes that this framework path reads the bar before the decision timestamp. The rolling/event-time score construction is backward-looking, and I found no new one-bar look-ahead in the evidence sizing path.

- `SELECTION = {}` is correctly implemented in Cell 25, and the generated run loop varies only `weighting_method` and the two floor neighbours. `DIAGNOSTIC_ONLY = (SELECTION == {})` matches the plan’s stated convention. This notebook alone cannot independently prove NB16 printed that exact empty dictionary, but the local implementation is correct.

- The evidence branch is mechanically sound for finite scores: it maps missing/NaN scores to zero, clips negative values to zero, applies the floor, and lets the existing normalisation and size-risk machinery apply caps.

There are important silent behaviours:

1. Missing evidence and zero evidence are conflated:

   ```python
   evidence_by_id[pair_id] = float(evidence_value) if evidence_value is not None and evidence_value == evidence_value else 0.0
   ```

   A vault with insufficient observations receives the same score as one with zero evidence of profit. With the default `weight_floor_fraction=0.25`, either receives a positive floor weight whenever another selected vault has positive evidence. If every score is zero, the branch returns equal weights. Thus the heading’s claim that the rule can give a quiet loser “nothing” is not true for the default run, and not true in the all-zero fallback.

2. “Holding selection fixed” is true for the ranking rule, but not proven for realised holdings. Deposit availability treats an already-held vault differently from a new vault, and a zero-sized evidence signal can change whether a position remains held. No selected-ID audit verifies identical basket membership across methods.

3. `largest_position_weights()` uses a better approach than positional list alignment: grouping `PositionStatistics` by `calculated_at` is the right basic reconstruction. But it silently drops every portfolio timestamp with no exact position timestamp:

   ```python
   values = values_by_ts.get(ts)
   if values:
       weights.append(max(values) / equity)
   ```

   It does not report coverage, unmatched timestamps, duplicates, whether values are pre- or post-rebalance, or whether position statistics include non-vault/credit positions. If portfolio and position snapshots have different timestamp precision, time zones, or write order, the result can be biased without an error. A duplicate portfolio timestamp is also silently overwritten by:

   ```python
   equity_by_ts = {s.calculated_at: s.total_equity for s in state_.stats.portfolio if s.total_equity}
   ```

4. The Cell 31 statistic is realised share of total equity at recorded valuation times, not the capped normalised target weight. It cannot establish cap binding. That claim requires the decision-time `AlphaModel` target weights and cap flags.

The NB18 diagnostic collision is real, but does not corrupt these NB17 performance metrics. The unsafe line in the shared base is:

```python
state.visualisation.add_calculations(timestamp, {'unallocatable_signals': alpha_model.get_unallocatable_signals()})
```

The framework overwrites, rather than merges, an existing dictionary for that timestamp. NB17 does not write its concentration diagnostic into that dictionary, so Cell 31 is unaffected; NB18 required its separate `SLEEVE_LOG` repair.

## 3. Statistical interpretation

The procedural verdict is a reject. Under the implemented pre-registered rule, blend misses the Sharpe floor (`2.048546 < 2.059792`) and volatility ceiling (`0.157629 > 0.154278`), and it also fails ulcer, beta and placebo evaluation. The other variants fail more decisively. `diagnostic_only=True` independently prevents treating any row as an adoption result.

“Clean REJECT” is acceptable only as a literal rule outcome. It should not be read as a statistically precise finding that blend is inferior: around 125 overlapping two-day cycles, with a polling-regime break and entirely in-sample evaluation, a 0.011 Sharpe gap and 0.0033 volatility gap are not separately resolved by this notebook. There is no uncertainty interval for either comparison.

“Closest miss in the plan” is not justified. The claim is not evidenced against the full candidate family, and blend is not close on every requirement: it has worse ulcer and beta than the anchor and lies beyond the eligible placebo envelope. Calling it a natural target for more in-sample tuning would increase selection bias.

The three-point floor sweep is useful as a pre-specified descriptive plateau check, but cannot identify a causal or stable relationship between the floor and Sharpe. The points share the same market path and selection rule; they are not independent evidence. The family-wise p-value of 1.000 in NB19 reinforces that nothing should be elevated from this family, though it is not itself a per-variant test.

## 4. What should be re-run or checked before these results are trusted

1. Rebuild Cell 29’s verdict table with one explicit Boolean column for each of the seven v2 constraints, their thresholds, and full-precision margins. Correct the heading: beta and placebo do not pass.

2. Audit every decision cycle for each sizing method: previous-bar feature timestamp, selected IDs, actually held IDs, evidence score, fresh-event count, raw weight, floor-adjusted weight, normalised target weight, concentration-cap flag, pool-cap flag, and executed target value.

3. Reconstruct concentration with assertions: canonicalised timestamps, one portfolio snapshot per timestamp, counts of matched/unmatched/duplicate snapshots, active-position identity, and exclusion of credit-supply positions. Report pre-trade and post-trade values separately.

4. Demonstrate whether the 33% cap actually binds from `AlphaModel` decision-time data. Do not infer it from ex-post largest-position shares; explicitly show that equal weighting is not cap-bound.

5. Verify realised basket membership is identical across runs, or quantify each divergence caused by deposit windows, minimum holdings, zero weights, pool caps, or execution thresholds.

6. After those checks, re-run the anchor, five variants and placebo frontier from a clean process and retain the audit artefacts. If any result changes, re-run NB19’s full family-wise calculation on the corrected candidate family.

7. Treat the floor sweep as descriptive unless a separately pre-registered prospective/shadow evaluation tests it across both polling regimes.

## 5. Verdict

**RESULTS STAND WITH CAVEATS**

The core result—none of the five sizing variants meets the implemented adoption rule—stands. The heading, however, materially misstates why: all variants also fail beta and placebo evaluation. The claimed universal concentration-cap binding is unproven and likely false for equal weighting, and the evidence-versus-inverse-variance interpretation is overstated.