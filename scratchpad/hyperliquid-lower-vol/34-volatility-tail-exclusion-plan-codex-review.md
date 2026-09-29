**The plan makes sense as exploratory research, but its claim to be “the one lead, gated properly” is premature.** There is credible evidence that trailing volatility predicts subsequent volatility, and a plausible reason to exclude an extreme tail while preserving the incumbent’s return ranking. That warrants freezing a candidate for prospective evaluation. It does **not** establish that eight exclusions improve portfolio performance: the three windows substantially overlap, the configuration was selected after extensive exploration, and the amendments respond to known rejection reasons. Revising defective rules is legitimate, but rerunning familiar data under revised rules is not independent confirmation. I would revise this draft before execution: its sparse-polling justification is overstated, the return clause changes the economic question, the null supports a narrower conclusion than claimed, and the fee discrepancy cannot simply be declared irrelevant.

## Findings

References below identify plan sections and the supplied notebook cells. This is a plan review, not a verification of all notebook outputs.

### 1. Material — the mechanism has support; the selected configuration remains exploratory

**Location:** “What the previous research established”; H2–H3; NB28 cells 32 and 37; NB33 cells 31 and 33.

NB28 supports **volatility persistence across vaults**. It does not establish that excluding exactly eight vaults improves the incumbent’s portfolio. Those are different propositions, especially when ranking and sizing already select against some volatile candidates.

The “three-window record” is particularly weak as confirmation:

- The incumbent window is largely contained in the track window.
- The full window contains both.
- NB33’s post-July-10 segment has `measured_8` returning **−2.3% versus −2.1%** for the anchor.

That last comparison does not disprove the mechanism, but it undermines the suggestion that the benefit travels consistently across time.

**Fix:** Describe eight as an **exploratorily selected count, now frozen**. Treat the overlapping windows as sensitivity checks. It is entirely legitimate to pre-register this configuration for future data; no amount of prior confirmation is required to register a hypothesis. Registration does not rehabilitate its historical evidence.

### 2. Material — accept some rule revisions, but reject the claim that their timing makes them non-adaptive

**Location:** “Rule changes, pre-registered”.

Writing amendments before NB34 runs prevents further tuning during NB34. It does not undo their dependence on NB28–NB33.

| Amendment | Judgement |
|---|---|
| Drop forward concentration | **Defensible narrowing of the objective**, because the measurement is compromised. Not justified by claiming no price signal can predict it. |
| Replace the mean-return clause | **Defensible change of estimand**, but not an equivalent repair. The median answers a different question. |
| Allow 0.10 fewer holdings | **Reasonable possible policy tolerance**, but not a numerical arithmetic correction. |

On concentration, NB28 explicitly says **failure to establish**, not evidence of absence. Its oracle establishes reachability; it does not prove that all three targets are necessary for every passing score, or that no historical price signal could succeed.

On holdings, **5.992 is genuinely below 6.000** unless an accounting error caused it. A tolerance of 0.10 is **12.5 times the observed shortfall**. It permits a real reduction in breadth.

**Fix:** Call these evidence-informed rule revisions and preserve the old verdicts. Justify the holdings tolerance in operational terms, such as acceptable frequency of five-name books, rather than calling it floating-point housekeeping.

### 3. Material — “calendar variance is unbiased under sparse polling” is only conditionally true

**Location:** Findings table; “The mechanism”.

For uncorrelated, zero-mean log-return increments over correctly bounded intervals,

\[
E[(r_1+\cdots+r_k)^2]=\sum_i E[r_i^2].
\]

That is the legitimate intuition behind “each jump carries its interval’s variance”. It is an expectation under assumptions, not preservation of the realised path.

With drift, serial dependence, noisy marks or stale endpoints, the argument does not automatically hold. Furthermore, the actual [`calm_score` implementation](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/blocks_floor.py:72) uses **demeaned sample standard deviation of simple percentage returns**, then an inverse and a floor. The identity above does not establish unbiasedness of that statistic—or its cross-sectional ranking.

Both ordinary realised variance and downside variation depend on sampling resolution; the theoretical justification involves assumptions and increasingly fine observations. [Bollerslev’s review](https://public.econ.duke.edu/~boller/Papers/SemiVar.pdf) makes that distinction explicit.

**Fix:** Replace “unbiased” with a conditional statement. Describe the fresh-mark guard as a heuristic for observation adequacy, not a correction that establishes estimator validity. Keeping the calendar clock is reasonable; this argument does not prove it superior.

### 4. Blocking — the post-April restriction does not repair gate 3’s trailing measurements

**Location:** Scope statement; NB35 gate 3.

The missing-path argument is substantially right: a fall and recovery between identical endpoints cannot be reconstructed from those endpoints. Drawdown, downside variation and event concentration are not identifiable at daily resolution inside an unobserved gap. Ordinary realised variance also loses realised-path information.

Restricting **forward** measurements to decisions after a documented polling improvement is defensible, subject to actual observation coverage. However:

- A recent decision does not make its **trailing 180-row** concentration indicator dense.
- On a daily grid, a wholly post-April 180-row history becomes available only around late September.
- The supplied backtests end before then.

NB35 also silently extends a scope statement explicitly about **gate 5** to **gate 3**. That changes another gate’s evaluation sample.

**Fix:** Register gate 3’s scope explicitly and assess coverage over each metric’s actual lookback. If its required historical metric cannot be evaluated honestly on these data, report that limitation. Forty decision dates with contaminated histories do not solve it.

### 5. Material — the median clause is sensible for typical returns, but its margin materially relaxes the policy

**Location:** Amendment 2; NB34 step 4.

The proposed statistic is interpretable: does the typical retained vault earn materially less than the typical excluded vault? Avoiding unstable annual compounding is also sensible.

But a median can ignore catastrophic losses affecting a minority of vaults. Those losses still matter to portfolio wealth. Wide mean-return intervals may reflect insufficient information about economically important tails, not merely an inconvenient statistic. The −13 log-return observations also need their economic and data provenance established.

The margin is not trivial:

- **0.01 per 30 days is about 0.122 annual log-return units.**
- Repeated mechanically, that represents roughly an **11.5% relative annual wealth disadvantage**.

This is a scale illustration, not an annualisation of the median contrast. It nevertheless shows why the new margin is not equivalent to the previous five-annual-percentage-point allowance. “One tenth of the IQR” explains its statistical scale, not its economic acceptability.

**Fix:** Name the clause “typical-vault return non-inferiority”. State explicitly that it does not protect expected portfolio returns or crash exposure. Justify −0.01 as an acceptable economic sacrifice; do not present it as a technical consequence of using medians.

### 6. Material — the null is useful, but cannot establish the claimed mechanism by itself

**Location:** Gate 9; “What would refute”; “What I expect”.

Permuting finite values within each date is a reasonable control for **randomly excluding eight measurable candidates at each decision**, while preserving missingness and downstream ranking. That is directly relevant.

However, fresh permutations also destroy the signal’s **temporal persistence**. A persistent volatility exclusion and an independently refreshed random exclusion can produce different turnover and holding histories. Beating this null therefore need not isolate volatility information alone.

Ten seeds provide a coarse hurdle. Even under a valid exchangeability argument, beating all ten gives an add-one permutation p-value of **1/11 ≈ 0.091**, before accounting for historical selection. [Phipson and Smyth](https://gksmyth.github.io/pubs/PermPValuesPreprint.pdf) explain the finite-permutation correction.

NB26’s random removal ranking seventh of 57 is a warning, **not an estimated null distribution**. It neither proves nor makes quantifiably likely that `measured_8` is indistinguishable from random removal.

**Fix:** Retain the null, but state its exact scope and report its induced turnover and basket persistence. A failure means **“did not clear this random-exclusion hurdle”**, not “the exclusion selects on no information”. A pass is likewise not proof of the volatility mechanism.

### 7. Blocking — a common fee bug need not cancel between configurations

**Location:** Findings table; “Out of scope”; NB36.

“They affect every configuration equally and cannot change a comparison” is false.

A common erroneous formula can impose different errors on strategies with different redemption dates, profits, quantities and turnover. Those differences can change return and Sharpe rankings. NB36 independently recomputing fees is useful, but an audit alone does not necessarily correct wealth paths and subsequent allocations.

**Fix:** Establish the intended fee convention and quantify the **differential** error between each candidate and its comparator before accepting performance-based verdicts. If material, correct the calculation or bound its impact. This cannot be dismissed merely because the anchor uses the same engine.

### 8. Material — the guard hypothesis contradicts its definition and expected outcome

**Location:** H1; “The mechanism”; “What I expect”.

If `calm_score` is the same finite score with additional observations masked, its coverage cannot increase. H1’s “at least as many” therefore requires equality, while “What I expect” explicitly predicts fewer.

The guard also does not prevent holding unmeasured vaults. Under permissive exclusion, it **protects them from exclusion**. That can be appropriate when estimates are unreliable, but it is not a general defence against stale vault exposure.

**Fix:** Separate coverage loss from the guard’s intended benefit: preventing unreliable estimates from determining exclusions. Remove the claim that the guard “bought coverage”. Any difference in finite coverage beyond masking needs an implementation explanation.

### 9. Material — the protocol is incomplete precisely where candidate selection happens

**Location:** NB34–NB36.

Several details need to be explicit:

- **Actual tail:** NB28’s supportive tail contrast used 30%, whereas this mechanism removes eight. Report stability outcomes for the actual excluded eight. Determine exclusions using decision-time information **before** dropping rows with missing future outcomes.
- **Backup candidate:** `measured_8` can be shortlisted, but its own null and leave-one-vault-out runs are not clearly scheduled. Historical retention figures cannot substitute for the current gate protocol.
- **Return multiplicity:** Specify the simultaneous family for both return contrasts.
- **Dependence:** Retain complete forward windows and shared date-block/vault resampling explicitly. Post-break coverage leaves only roughly four months of eligible decisions—very few non-overlapping 30-day horizons.
- **Prospective decision:** A 90-day monitoring horizon is a monitoring choice, not demonstrated statistical resolution. State what evidence at its end can support deployment, extension or rejection.

**Fix:** Resolve these in the written protocol before execution. No additional mechanism search is needed.

## What is unnecessary, and what is sound?

**Unnecessary:** Repeating a noisy oracle reachability exercise adds little unless the revised implementation needs a validation check. NB28 already established that the previous machinery could emit passes. Oracle success cannot validate target relevance or realistic statistical power.

**Sound:** Freezing one exclusion family, preserving incumbent ranking and sizing, testing neighbouring counts, full re-simulation after masking, checking null effectiveness, auditing provenance, and limiting the verdict to SHORTLIST are all worthwhile. Keeping cadence and return-floor changes outside this plan also makes sense.

One source correction: NB33 finding 4 says both components beat the anchor on its own window, but its table shows `floor15` did not. The poor combination result stands; that explanation needs correcting.

## Is “What I expect” honest?

**Mostly honest in tone, but inconsistent and overconfident in interpretation.** Explicitly anticipating a null failure is good. Giving expected magnitudes is useful. Calling gate 9 the only genuine unknown understates the unresolved guard behaviour, gate-3 measurement and fees.

The final sentence crosses the line: failing this hurdle would establish **failure to demonstrate an advantage under this protocol**, not establish equivalence to random removal.

**My recommendation:** keep the research question and the frozen count. Revise the measurement claims, gate definitions and rejection language. The next rerun can produce a defensible exploratory shortlist; it cannot turn this accumulated historical search into confirmation.