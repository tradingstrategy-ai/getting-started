## 1. Do the heading's claims match the outputs?

- “All 41 non-anchor candidates fail `passes_v2`” is supported. Cell 25 reports `41 variant runs completed`, and cell 27 reports `Any non-anchor run passes v2: False`.

- The family-wise figures are correctly transcribed from cell 31: best observed Sharpe improvement `-0.111246`, null 95th percentile `2.684094`, and reported p-value `1.000000`.

- “The best candidate underperforms the anchor’s Sharpe” is supported: `sizing_blend` has 2.048546 versus the anchor’s 2.159792 in cell 27.

- The claim that the family-wise result is “unambiguous” is not justified statistically. It is unambiguous only descriptively: no sampled candidate beat the anchor’s Sharpe. It is not strong evidence that no modest improvement exists; see section 3.

- The `sizing_blend` claim is numerically supported: 36.42% CAGR, 1.48pp sacrifice, Sharpe 2.049 below the 2.060 floor, higher volatility, and worse ulcer (cell 27). However, the heading understates its failures. Cell 37 gives its complete list: “Sharpe non-inferiority, volatility, ulcer (not material), beta, placebo (not evaluable)”.

- The best-per-family labels are supported by cell 33:
  `{'NB16': 'sortino_shrunk__t_cap_4', 'NB17': 'sizing_blend', 'NB18': 'core_0.7_n3'}`.

- “`core_0.7_n3` [is] the only candidate to clear the CAGR floor” is contradicted. All five NB17 sizing candidates clear 20%; cell 27 shows CAGRs from 23.43% to 36.42%. It is only the NB18 candidate to clear the floor.

- “Every mechanism shares the same three-constraint failure signature” is contradicted. That describes NB17, not the whole family. For example, `sortino_shrunk__t_cap_4` fails CAGR, Sharpe, ulcer, deployment and placebo, but not volatility; `core_0.7_n3` also fails beta, deployment and placebo. The summary table’s “Failed” column is therefore incomplete where it implies an exhaustive list.

- The placebo explanation is supported. Cell 23 shows `vol_matched_drop_30` at Sharpe 2.747391 and volatility 0.149229, below the anchor’s 0.154278. Cell 27 shows the anchor failing placebo evaluation because the Pareto envelope no longer covers its volatility.

- “Fresh snapshot” and “every family-best figure matches its source notebook” are not demonstrated by an NB19 comparison cell. The source executed notebooks do contain the same rounded family-best figures, but NB19 itself does not test or print that comparison.

- The shadow statement is supported by cell 35: no candidate is scheduled for shadow deployment, and it states a 45-cycle side-by-side protocol.

## 2. Correctness of the code that produced the numbers

The 41 adoption-candidate overrides match the source builders exactly.

| Family | NB19 | Source builder | Result |
|---|---:|---:|---|
| NB16 | 29 | 29 | Exact match: three score families, all centre/neighbour/control configurations |
| NB17 | 5 | 5 | Exact match: `evidence`, `blend`, `equal`, and floors 0.0/0.5 |
| NB18 | 7 | 7 | Exact match: four `n4` fractions, `0.7_n3`, `0.7_n5`, and `1.0_n6_no_satellite` |

There is one additional NB18 run in the source notebook: `core_0.7_n4__without_top_vault`. It is a robustness simulation of the NB18 centre, not an alternative parameter point selected for adoption. Excluding it from the 41-member candidate family is the right primary call. It should, however, be described accurately: there are 41 candidate configurations plus one source-notebook robustness run, not “41, not 43 or 44”.

The more serious issue is that NB19 does not re-run NB18’s leave-one-vault-out check or enforce robustness gates in its own final adoption code, despite the plan saying it would re-verify them. Its winner logic is:

```python
if bool(vt.loc[label, "passes_v2"]) and bool(vt.loc[label, "late_ok"]):
    winner = label
```

It ignores plateau, leave-one-vault-out, and `diagnostic_only`. This does not alter this run’s “nothing adopted” result, because every candidate already fails `passes_v2`; it would be an adoption bug if any candidate passed the seven constraints.

The earlier NB18 diagnostic collision was real and is repaired in the executed code. The framework still writes:

```python
state.visualisation.add_calculations(timestamp, {'unallocatable_signals': alpha_model.get_unallocatable_signals()})
```

at the same timestamp. The replacement correctly stores sleeve diagnostics separately in `SLEEVE_LOG[timestamp]`, avoiding the overwrite. This affects sleeve attribution diagnostics, not the return calculations driving NB19’s ranking.

Feature alignment appears correct: the strategy accesses indicators through `get_indicator_value(...)`, whose established framework behaviour is the prior daily bar (`index=-1`). The evidence indicators’ forward-filled values are therefore read as of the bar before the decision date, not the open decision-day bar.

NaN handling in `passes_constraints_v2()` is also correct: an unevaluable placebo reference is a failure, rather than a silent pass.

The family-wise test is not correctly specified for its stated inferential question. It ignores candidate returns when creating its null, apart from using their labels and observed Sharpes:

```python
for _label in observed:
    ...
    sample = anchor_r[idx]
    draw_max = max(draw_max, sample_sharpe - anchor_sharpe)
```

Thus each label receives an independent bootstrap draw from the anchor distribution. This does produce a maximum of 41 independent noise draws, exactly as coded. But it is not a valid White-style reality check for this highly correlated strategy family.

A valid family null should preserve the joint dependence between candidates and anchor: align their cycle return differentials, re-centre each differential under the no-outperformance null, and resample common time blocks across all candidates. The current construction assumes 41 independent copies of the anchor, which is neither the actual candidate dependence structure nor a standard “best parameterisation of related strategies” null. Calling it “conservative and standard” is incorrect.

The right-tail direction is correct for a positive-improvement alternative:

```python
p_value = mean(null_max >= observed_max)
```

With observed maximum `-0.111`, a p-value rounded to 1.000 is unsurprising. It is not evidence in favour of the anchor; it is principally a consequence of no candidate showing even a positive in-sample Sharpe improvement.

## 3. Statistical interpretation

The pre-registered deterministic rule supports rejection: every candidate fails at least one of the seven constraints, so none can be adopted. That conclusion does not need the family-wise test.

The statistical interpretation in the heading is over-claimed.

With roughly 125 two-day observations and 182.5 annualisation periods, the per-cycle Sharpe is approximately:

\[
2.16 / \sqrt{182.5} \approx 0.160.
\]

Under a basic IID approximation, the standard error of an annualised Sharpe is approximately:

\[
\sqrt{\frac{182.5}{125}(1 + 0.5 \times 0.160^2)} \approx 1.21.
\]

For 41 independent standard-noise Sharpe draws, the expected maximum is roughly \(2.17 \times 1.21 \approx 2.6\) Sharpe. A 95th-percentile maximum is nearer \(3.0 \times 1.21 \approx 3.6\), before allowing for serial dependence or non-normality.

Therefore +2.684 is in the correct annualised order of magnitude and does not itself indicate an annualisation/scaling bug. It is closer to a rough expected maximum than to an IID 95th percentile, so it should be checked by printing the one-label bootstrap standard deviation and quantiles. Negative autocorrelation, the particular realised return distribution, and the block bootstrap can make it lower than the IID estimate.

But the implication is clear: this test has essentially no power to detect an improvement of 0.3 annualised Sharpe. Under its own independent-noise null, a best-of-41 improvement of +0.3 would almost always be exceeded by at least one null draw. A threshold around +2.68 cannot distinguish a modest economically meaningful improvement on this sample.

So the correct reading is: p = 1.000 mostly reflects that the observed best Sharpe difference is negative. The heading should say the family-wise test is low-powered on this in-sample, single-regime-break window, not “unambiguous”.

The one polling-regime break compounds this: nominally there are about 125 cycles, but the sparse and dense periods are structurally different and the returns are not independent. The seven-constraint rejection is a valid in-sample screen; it is not a reliable estimate of the absence of future benefit.

## 4. What should be re-run or checked before these results are trusted

1. Correct `family_wise_reality_check()` before using or reporting its p-value. Bootstrap jointly aligned, re-centred candidate-minus-anchor cycle returns with common block indices across every candidate.

2. Report the single-strategy bootstrap Sharpe standard deviation, the maximum-null distribution, effective correlation/family size, and sensitivity to block length. Do not call the current result a White reality check.

3. Repair NB19’s adoption logic so it enforces all required gates: seven constraints, plateau, leave-one-vault-out, late-period condition, and eligibility status.

4. For any future candidate based on `core_0.7_n3`, run that candidate’s own plateau and leave-one-vault-out test. The source NB18 explicitly says it is a single plateau neighbour and lacks its own leave-one-out test.

5. Regenerate the heading from the final table, or manually correct it: distinguish “only NB18 candidate above 20% CAGR”; list all failed constraints where a table column is labelled “Failed”; remove the false shared-three-failures claim.

6. Retain the current “nothing adopted” decision pending the corrected statistical work. Do not infer that the strategy family has been decisively disproved.

## 5. Verdict

RESULTS STAND WITH CAVEATS

- The executed configurations are complete and match the source builders.
- The numerical finding that no candidate passes rule v2 is supported.
- The family-wise p-value is not a valid calibrated test for this correlated candidate family.
- “Unambiguous” is statistically unjustified; the test has negligible power for a modest Sharpe improvement on this window.
- NB19’s final adoption logic is incomplete, though harmless here because no candidate reaches the first gate.