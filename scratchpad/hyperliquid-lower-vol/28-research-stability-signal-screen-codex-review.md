## Review outcome

The notebook’s logged pool, T−1 signal access, forward-window handling, anchor parity, cycle-clock metrics, and most headline point estimates are sound. However, I would not accept the gate-5 verdicts or the “nothing predicts event concentration” conclusion as currently supported.

| Severity | Cell | Finding and concrete fix |
|---|---:|---|
| **Blocking** | 19 / 28 | `simultaneous_ci()` uses `np.nanmax()` across hypotheses. If a bootstrap replicate is non-finite for a hypothesis, it silently drops that hypothesis from that draw’s max-T statistic, reducing the multiplicity burden. This invalidates the claimed simultaneous 39-hypothesis lower bounds. The 499 finite paired draws in cell 36 demonstrate that non-finite replicates occur. Fix: retain only draws finite for the complete family when constructing the max-T critical value, or make every hypothesis estimable in every retained replicate; fail closed if too few remain. |
| **Material** | 19 / 32 | `add_one_p()` counts non-finite bootstrap draws as non-exceedances but retains all 500 in its denominator. Thus the reported add-one p-values are too small whenever a statistic is missing in a replicate. Fix: calculate numerator and denominator on each hypothesis’s finite bootstrap draws only. |
| **Blocking** | 0, 25–32 | The surprising all-zero gate-5 result is merely observed, not shown unreachable as required. There is no reachability/calibration demonstration that the event-concentration target and bootstrap can ever clear the specified lower-bound rule on this panel. Moreover, `forward_event_top5` is structurally dependent on the number of positive forward events: with exactly eight positive events its share is bounded below by 5/8, while a frequently reporting vault can have many more events and a much lower attainable share. The target therefore mixes activity/reporting frequency with concentration. The 38% missingness compounds this. The conclusion should be restricted to: “none of these thirteen signals passed this implementation of gate 5”; it cannot conclude that spikiness does not persist or that gate 5 is intrinsically unsatisfiable. |
| **Material** | 36; echoed in cell 0 | The calendar-versus-fresh comparison is not actually paired at the observation level. `fresh_event_concentration` uses 51 usable dates and `residual_event_concentration` uses 60, with different complete-case candidate sets. Shared random resamples do not repair a difference in estimands/samples. Fix: compute both statistics on one common `(date, vault)` complete-case sample before forming a paired difference, or label cell 36 as an unpaired descriptive comparison. |
| **Material** | 0 | The reported simultaneous critical values are wrong. Cell 0 and the summary table say 3.0463 for stability and 3.1377 for return; cell 28 prints **2.9035** and **3.0512**, respectively. Fix the generated heading and summary from the executed cell output. |
| **Material** | 0 | “The return clause cannot discriminate … and would not have rejected anything either” contradicts cell 29: `return_clause` is `False` for all thirteen signals. It rejects every signal, indiscriminately. Fix wording to say that it has no useful discriminatory resolution, while acknowledging that it rejects all thirteen under the stated rule. |
| **Minor** | 0 | “Spikiness does not persist here” overstates the evidence. The result is failure to establish positive association for this target under the current, count-confounded and missingness-selected measurement. Fix to “the screen did not establish persistence under this target definition.” |

## Checks that passed

- Cells 21 and 23 correctly establish anchor parity and an inert logging run.
- Cells 25–26 correctly report complete-window eligibility and target/signal missingness.
- The T−1 access pattern is causal; the deliberately forward-looking targets begin from the carried NAV at T.
- The two-way bootstrap does resample date blocks and vault clusters, and the resample stream is shared across hypotheses.
- The sign orientation and tail ordering are internally consistent.
- Cell 34 correctly shows sign agreement between the complete-case tail diagnostic and Spearman diagnostic; it does not rescue the gate-5 conclusion.
- Cell 40 faithfully reflects the computed table, subject to the invalid simultaneous-inference construction above.

So: the numerical observation “0 of 13 passed the implemented screen” is reproduced, but the stronger headline interpretation is not yet justified.