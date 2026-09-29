I would revise this plan before execution. NB20 is a worthwhile follow-up; NB21 does not establish the independence or name-specific effect it claims; NB22 is a useful ablation, but needs measurement and indicator checks before a nine-run sweep.

I read [the plan](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/20-stability-leads-plan.md) in full, the supplied reviews, the three notebook headings and the reused code. No notebooks were run and no files were modified.

## 1. Flaws and risks in the plan as written

1. **NB21’s derivation/evaluation split does not prevent outcome fitting.**

   > “names - derived without looking at the evaluation period”

   > “`late_ok` holds (the evaluation period - this is the one that counts, since the list was derived on the other half)”

   Restricting the address-frequency calculation to January–June prevents **direct use of July–September observations in that calculation**. It does not undo the use of full-window outcomes to choose `drop_30`, the 20-to-30 marginal band, this mechanism or the follow-up neighbourhood. July–September has already informed several rounds of research.

   The previous plan explicitly says the hold-out was retired; [the harness](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/harness.py:14) still describes the full window as in-sample. This is an outcome-informed hypothesis with a chronological diagnostic, not independent validation. A frozen prospective evaluation is still needed.

   There is also a contradiction: the lead table promises constraints 1–7 on the second half, whereas the detailed verdict applies them to the **full window**, requiring only positive CAGR and lower ulcer in the late segment. Those are substantially different tests. January–June and July–early September are not equal halves either.

2. **Applying June’s list from January contaminates the simulated starting state for July.**

   > `run_and_record(f"exclude_top{k}", masked=set(EXCLUSION_LIST[:k]))`

   `run_variant()` applies the mask from the first backtest cycle. A list learnt by June therefore changes January trades, subsequent capital, holdings, cost bases and potentially deposit availability for existing positions.

   Merely slicing that equity curve in July does not simulate introducing the list in July. Either start all evaluation strategies from the same cash state on the first scheduled July decision, with historical indicators warmed up, or switch from a common June-end portfolio using explicit transition trades. Keep the full-window exclusion backtest as a retrospective counterfactual.

3. **The random-exclusion null answers a weaker question than NB21 claims.**

   > “20 draws of k = 10 addresses sampled from the set of candidates that were *ever* in the gated pool during the derivation window with a valid `inverse_vol`”

   This is a reasonable control for “does this list beat arbitrary removal from this population?” It is not sufficient for “do these particular identities matter beyond volatility avoidance?”

   The proposed list contains repeatedly marginal, relatively volatile candidates. Uniform random lists can contain vaults that were briefly eligible, never competitive for a basket slot, or still unscored by the 360-day composite. Removing them can leave the anchor almost unchanged. Valid volatility is not equivalent to being selectable or economically influential.

   Retain the uniform null as a descriptive baseline, but add a **matched static-list null** using derivation-only volatility rank, gated eligibility frequency, composite-score availability and anchor target exposure. Compare directly with the dynamic drop rule as well. Otherwise a “name effect” can simply be persistent exposure to a particular risk or eligibility cohort.

4. **The null’s endpoint and empirical p-value need correction.**

   > “late-period CAGR ranks in the top 2 of the 20 random draws (empirical p <= 0.10)”

   CAGR is not the operator’s primary stability objective. A list can win this comparison by retaining a volatile winner. The random-null test should primarily assess a pre-specified stability statistic, with the CAGR and deployment floors enforced separately.

   For 20 random draws, define the upper-tail Monte Carlo rank explicitly:

   \[
   p=\frac{1+\#\{T_{\mathrm{random}}\geq T_{\mathrm{candidate}}\}}{21}.
   \]

   For \(p\leq0.10\), at most **one** random draw may equal or exceed the candidate. Two exceedances give \(3/21=0.143\). Ties count against the candidate. Twenty draws give very coarse resolution; 199 would be more useful if this remains a decisive gate.

   Even then, call this a random-list benchmark percentile unless the required exchangeability assumptions are defended. Randomly generating controls does not automatically make the candidate’s identity list a randomised treatment.

5. **Adjacent-date Jaccard is not an adequate test of whether a useful static list exists.**

   > “If the derivation finds no stable set at all (median consecutive-date Jaccard of `M` below 0.5), stop”

   Consider ten-name marginal sets containing four permanent names and six changing names. Consecutive Jaccard can be \(4/16=0.25\), despite a persistent four-name core. Conversely, high adjacent overlap can coexist with complete replacement over several months.

   The threshold also measures persistence of a **volatility-rank band**, not whether excluding its members improves the portfolio. High frequency does not establish harmfulness.

   Report persistent-core coverage, monthly membership stability, exclusion-list stability under blocked derivation resamples, and how often the proposed exclusions actually displace a funded position. Jaccard alone should not terminate the backtests.

6. **Constraint 7 is inapplicable to NB20 as a self-comparison, not vacuous.**

   > “Constraint 7 is vacuous for lead 1 - the candidate IS the placebo mechanism.”

   At a retained frontier point, the rule effectively demands \(S\geq S+0.10\), which is impossible. Other family members can fail through domination or interpolation. Waiving self-superiority is sensible, but this is an explicit change in the adoption rule.

   The asymmetry needs explaining: NB20 can qualify through six constraints, while NB21/NB22 must outperform an outcome-selected volatility family by another 0.10 Sharpe. This is defensible as a **complexity premium** for additional mechanisms. It is not evidence that NB20 has passed the old rule unchanged.

   Promoting a previously excluded control after observing its attractive result also creates selection bias. Report a separate `simple_rule_eligible` decision and reserve ADOPT for a clearly defined prospective step.

7. **The inherited placebo envelope remains a questionable adoption benchmark.**

   > “Sharpe >= placebo envelope + 0.10 at the candidate’s volatility, failing … off the envelope’s range”

   [The implementation](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/harness_evidence.py:74) linearly interpolates Sharpes between realised strategies. That line is neither an observed control nor generally the return of an executable mixture. The previous NB15 review already identified this.

   Moreover, removing dominated points makes the envelope end at `drop_30`, below the anchor’s volatility. A near-anchor candidate consequently fails as “not evaluable”, although there is an observed lower-volatility control available for comparison.

   Choose one interpretation before running:

   - A descriptive, explicitly synthetic interpolation; or
   - The best observed control at or below the risk budget; or
   - A frozen executable comparator selected using derivation data.

   These are different hypotheses. For the second, a candidate above the maximum retained frontier volatility remains comparable with that maximum’s strategy; it is not intrinsically unevaluable.

   NB20 also introduces intermediate N values. The plan must say whether those update the comparator for NB21/NB22 or remain separate exploratory candidates.

8. **The no-estimate-first interpretation is partly correct but overgeneralised.**

   > “at N = 30 the drop removes every young, unscored candidate before it removes any old volatile one”

   Missing inverse volatility sorts first. But volatility availability requires approximately **90 days**, whereas the CAGR score requires **360 days**. Many unscored vaults therefore have valid volatility and sit among the supposedly “volatile” removals. Conversely, missing volatility need not uniquely identify a young vault.

   Nor does N=30 necessarily remove *every* missing estimate: there could be more than 30.

   > “mean effective volatile drop (N minus no-estimate count)”

   This is wrong when the gated pool has at most N members: the trading code then drops **nothing**. Use `len(dropped_ids - no_estimate_ids)`, and report the no-drop branch frequency. Near that boundary, increasing N can abruptly disable exclusion.

   For NB21, the post-April-launch check is useful, but its expected result depends on the 90-day window and exact last derivation feature date. It does not follow from “volatile-only” alone. First archived observation must also be distinguished from verified launch date.

9. **The proposed reconstruction does not “mirror `decide_trades` exactly”.**

   > “The offline reconstruction, used by both notebooks, mirrors `decide_trades` exactly”

   Comparing it with [the actual candidate loop](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/cell14_enhanced.py:348) reveals:

   - Missing `state.is_good_pair()` and quarantine checks.
   - Missing `MASKED_VAULTS`, relevant to masked robustness runs.
   - Missing strict-score admission when that option is enabled.
   - No demonstrated equivalence between `.asof(at)` and the framework accessor. Pandas `.asof()` skips NaNs and returns an earlier valid value, potentially reviving an invalid current indicator. [Pandas documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.asof.html?highlight=merge).
   - No assertion that equal-volatility ties preserve the trading loop’s candidate order.
   - No state argument through which state-dependent eligibility could be reproduced.

   Also:

   > “the anchor path … never reads `inverse_vol_early`”

   The evidence splice **does read it whenever ordinary inverse volatility is missing**. At defaults it is expected not to supply an earlier usable estimate. “Read but inert” is the accurate claim.

   Log the actual pre-drop candidates, indicator values and dropped IDs during simulation, then assert reconstruction parity. Deposit-window filtering happens **after** dropping, so it must not be moved into the reconstructed pre-drop pool.

10. **NB22 changes more than the wording “same admission” suggests.**

    > “same CAGR leg, same admission (360 days of history), same sizing, same gate”

    Keeping the CAGR leg retains its score-availability barrier. It does not guarantee identical admission or selected cohorts. The replacement Sortino has different observation requirements and NaN behaviour. With `require_scored_candidates=False`, an unscored candidate still enters with signal zero and can win a degenerate ranking.

    The replacement also changes the horizon from 45 calendar days to up to 90 **mark events**, whose elapsed duration differs across vaults. It changes shrinkage, scaling and saturation simultaneously. This is a valid component replacement, but it cannot isolate “shrinkage helps” or “event-time helps”.

11. **The reused Sortino helper has material behaviours the plan does not acknowledge.**

    > “swap only the 45-day Sortino leg for `sortino_shrunk_score`”

    In [the event-time helper](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/blocks_evidence.py:126), the downside-count mask is followed by `.reindex(full_index).ffill()`. Consequently, a later event window that fails the minimum downside count can inherit an older valid score. The forward fill bridges both unpolled dates **and newly invalid event dates**.

    Other limitations remain:

    - Unequal-duration catch-up returns are treated as interchangeable events.
    - Annualisation uses the calendar trading-days constant rather than each vault’s event rate.
    - The effective-sample-size adjustment is a heuristic, not a calibrated Sortino uncertainty estimate.
    - Linear shrinkage of an unbounded raw ratio does not prevent a thin sample reaching the final cap.
    - Forward-filled evidence can remain apparently valid through a long reporting gap.

    These do not prove NB22 will fail. They do mean its score must be treated as a heuristic and audited for age, invalidation and saturation before interpreting the backtest.

12. **NB22 can be distinguished mechanically; its economic advantage may remain unresolved.**

    > “If … the two composites select the same top 6 on more than 90% of dates … the result is a near-replication”

    Whole-pool Spearman correlation can be dominated by irrelevant low ranks and tied zero scores. Identical raw top-six sets do not guarantee identical holdings after deposit checks, state dependence and execution thresholds. A small number of substitutions can also account for most risk.

    Measure actual target-weight differences, realised-weight differences, active returns, changed decision dates, turnover and the contribution of changed holdings to drawdowns.

    With approximately 125 cycles, a rough IID standard error for an individual annualised Sharpe is about 1.2. **That is not the standard error of the paired difference**: highly correlated strategies can have a much narrower difference interval. Estimate it instead of declaring NB22 unidentifiable solely from sample size.

    Exact equality of holdings, weights and returns establishes mechanical replication. Otherwise, failure to reject a zero difference does not establish equivalence. A near-anchor replication would also retain roughly the anchor’s ulcer and therefore fail the required 15% reduction.

13. **The bootstrap does not directly address the stated decision margins.**

    > “the heading must say whether the interval contains zero”

    For anchor non-inferiority, the relevant boundary for \(\Delta S=S_c-S_a\) is **−0.10**, not zero. For placebo superiority it is **+0.10**, against the comparator actually used by the rule.

    The nearest raw placebo can be dominated and need not equal the interpolated reference. Its interval therefore does not validate constraint 7.

    Bootstrapping only near-misses also omits uncertainty for apparently strong winners selected from the sweep. Report intervals for every eligible centre. The default ten-cycle blocks give only about twelve block-lengths over the full sample and three to four in July–September; pooling across April additionally assumes away the reporting-regime break. Report block-length sensitivity and regime-specific diagnostics without presenting them as independent replications.

14. **The family-wise calculation is misspecified, not merely low-powered.**

    > “NB23 runs it … a check that the best result is not obviously noise”

    [The helper](/Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/_build/harness_evidence.py:249) independently resamples the anchor once per candidate label. It does not preserve candidate–anchor or candidate–candidate dependence when constructing the null.

    Its +2.7 figure therefore cannot establish the power of an appropriately paired test for these strategies. Repeating the disclaimer does not calibrate its p-value.

    Use common block indices across the aligned strategy-return matrix and a centred maximum statistic matching the chosen estimand. For Sharpe differences, centre the bootstrapped **Sharpe-difference statistics**, or use an appropriate influence-function method; subtracting mean return differentials alone does not define a Sharpe-equality null. Any such calculation still cannot erase the earlier adaptive research history.

15. **Plateau, robustness and close-out decisions remain incompletely specified.**

    > “`cagr_weight` has no upper neighbour (NB92 fixed 0.6 as the top of its searched range)”

    An earlier search boundary is not an economic reason that 0.7 is inadmissible. Likewise, strict admission is a different policy, not merely a local numeric neighbour; no maximum-event-window neighbour is included.

    > “all three centres are eligible in this plan”

    NB20 has multiple possible centres; NB21 may stop before producing one. NB23 does not explicitly carry forward NB21’s random-null gate or rerun its random controls. It also lacks a multiple-winner rule.

    NB20 requires late-period success for neighbours, whereas NB21/NB22 require it only for the centre. Leave-one-vault-out late-period requirements are unclear. Testing removal of only the largest profitable vault is a useful concentration stress, but not comprehensive leave-one-out robustness or a correction for selection.

    Finally:

    > “that is the finding that de-risking costs Sharpe on this window, and it settles lead 1”

    Failure of this finite grid settles eligibility under this rule on this dataset. It does not establish a general Sharpe cost, especially if some points fail deployment, CAGR or plateau rather than Sharpe.

16. **Reproducibility and the measured objective need stronger boundaries.**

    > “prints that fingerprint … do not describe any run as a ‘fresh’ or ‘independent’ snapshot unless the fingerprint has changed”

    Size and mtime do not identify file contents. A changed download containing the same historical period is also not independent evidence. Freeze content hashes for prices, metadata, universe membership, reference prices and code.

    NB13 reports universe filtering using a metadata snapshot, including deposit closure and peak TVL. The plan does not establish point-in-time membership. A later snapshot can exclude vaults that were investable earlier, creating survivorship or availability bias even when indicator reads are correctly lagged.

    Finally, lower volatility and ulcer measured from stale NAVs can reflect delayed recognition of risk. Serially smoothed returns can understate economic volatility and inflate Sharpe; that is a measurement concern, not evidence that Hyperliquid managers deliberately smooth returns. [Getmansky, Lo and Makarov](https://www.nber.org/papers/w9571). The research needs a mark-quality sensitivity alongside its equity-curve objective.

## 2. Can a less capable agent execute it verbatim?

**No.** The experiment outline is clear, but several decision branches require methodological invention. These are the sentences I would add before execution; substantive changes should be recorded as a new draft before any runs.

| Ambiguity or missing instruction | Sentence to add |
|---|---|
| Historical versus prospective status | “All historical results are exploratory and in-sample; ADOPT means admission to the frozen prospective shadow protocol, not authorisation to deploy capital.” |
| NB21 evaluation dates and constraints | “Evaluate NB21 separately from the first scheduled decision on or after 2026-07-01 through the existing backtest end, applying all seven constraints against comparators evaluated over that same period.” |
| NB21 initial state | “Start every NB21 evaluation run from $150,000 cash on the unchanged decision clock, retain pre-July indicator history, and label full-window masked runs retrospective counterfactuals.” |
| Freezing the list | “Before producing evaluation outputs, record the ordered lower-case address list, derivation cutoff, frequency table, extraction-code hash and input hashes in an immutable manifest.” |
| Missing reconstruction helpers | “Include complete definitions of `indicator_series_for`, `inclusion_series`, `ONE_BAR`, `GATE` and the decision-date sequence in `blocks_stability.py`, with explicit indicator parameter keys.” |
| Reconstruction parity | “Record actual pre-drop candidates, gate values, inverse-volatility values and dropped IDs for every decision and assert equality with the offline reconstruction, including masks, quarantine, bad-pair status and tie ordering.” |
| Instrumentation versus ‘no change’ | “Read-only logging may be spliced into `decide_trades` through track-local replacements, provided anchor trades and equity remain identical.” |
| Diagnostic logs | “Clear diagnostic logs before each run, snapshot them into that run’s record afterwards, and assert unique decision timestamps and expected coverage.” |
| Tuple subtraction in `M` | “Unpack `D_n, U_n = drop_set(when, n)` and compute `M = (D_30 - D_20) - U_30`.” |
| No-drop branch | “Report actual removed counts and the frequency of `pool_size <= N`; never substitute N for the number removed.” |
| Missing versus unscored | “Cross-tabulate removed vaults by volatility validity, composite-score validity and age; do not use these categories interchangeably.” |
| Empty sets and Jaccard | “Treat Jaccard for two empty sets as missing, report excluded comparisons, and report one-empty-set comparisons as zero.” |
| Jaccard stopping rule | “Use Jaccard as descriptive evidence only; do not cancel the exclusion backtests solely because adjacent-date median Jaccard is below 0.5.” |
| Frequency ties and list length | “Sort by descending marginal frequency, ascending drop-20 frequency, then lower-case address, and mark any k with fewer than k positive-frequency addresses unavailable without padding.” |
| Random-list reproducibility | “Sample without replacement within each list from a sorted, derivation-frozen population using `np.random.default_rng(seed)`, and print every sampled list.” |
| Matched null | “Retain uniform random lists as a weak baseline and specify a second static-list sampler matched on derivation-only volatility rank, score availability, eligibility frequency and anchor exposure, with fixed bins and fallback rules.” |
| Null statistic | “Use negative evaluation-period ulcer as the primary random-list statistic, report CAGR and deployment eligibility separately, and retain CAGR and Sharpe ranks as secondary diagnostics.” |
| Empirical tail calculation | “Compute `p = (1 + count(T_random >= T_candidate)) / (B + 1)`, count ties against the candidate, and report the numerator and denominator.” |
| Frontier construction | “State explicitly whether NB20’s intermediate N values enter the comparator and whether constraint 7 uses synthetic interpolation or an observed-control rule; use the same definition in every notebook.” |
| Single source of run data | “Implement a track-local frontier builder through `run_and_record()` so every control retains state, equity, returns and panel, and reuse identical parameter-and-mask configurations.” |
| NB20 verdict columns | “Add `passes_1_to_6` and `failed_1_to_6`, mark constraint 7 as not applicable to the simple-rule decision, and do not use `passes_v2` as NB20’s adoption flag.” |
| NB20 eligible centres | “Only N in `{25,30,35,40,45,50,55}` can qualify as plateau centres; 20 and 60 are boundary neighbours, and if several centres qualify select the smallest N for the single shadow specification.” |
| Robustness consistency | “For every family, require the centre, specified neighbours and masked centre to meet the family’s applicable constraints and `late_ok`; list each Boolean separately.” |
| Combining masks | “For NB21’s robustness run use `set(EXCLUSION_LIST[:10]) \| {top_contributor}`, where the contributor is computed from that candidate’s evaluation state.” |
| Missing robustness runs | “A required run that was skipped, failed or is unavailable cannot produce a passing robustness flag.” |
| NB22 scoring audit | “Before interpreting NB22, report score validity, elapsed event-window length, age of last valid evidence, clipping frequency and selected unscored positions, including a synthetic check of later downside-count invalidation.” |
| NB22 identity diagnostic | “Compare actual target and realised weights, cycle returns and changed decision dates, using the trading pipeline’s tie-breaking and deposit checks, rather than raw top-six ranks alone.” |
| Bootstrap specification | “Use aligned cycle returns and common block indices, report draw count, seed and block length, and compare intervals with −0.10 against the anchor and +0.10 against the chosen placebo.” |
| Family-wise test | “Replace the independent-anchor null with a jointly resampled, centred maximum statistic and print the exact distinct candidate family included; do not call the legacy simulation a calibrated reality check.” |
| NB23 hand-off | “Load frozen per-notebook manifests containing every centre, neighbours, mask, eligibility flag and random-null result, and reproduce every gate before assigning the final verdict.” |
| NB21 skipped in NB23 | “If NB21 is diagnostic-only, omit its absent curves and centre checks and record it as ineligible rather than assuming three eligible centres exist.” |
| Failed-column inconsistencies | “Report the complete failure set for every row, with the first failure optionally identified as an additional summary field.” |
| NaNs | “Fail closed on non-finite required metrics and include each missing metric in the failure string.” |
| Anchor parity precision | “Store full-precision baseline metrics and explicit tolerances; compare against those values rather than rounded heading figures.” |
| Snapshot provenance | “Hash all price, metadata, universe and reference-price inputs and record code versions; changed metadata or a refreshed historical download does not create independent evaluation data.” |
| Build order and costs | “Build notebook templates before execution, inject subsequent frozen result manifests without changing logic, and print the exact run manifest and count including frontiers, random controls and robustness runs.” |
| Prospective completion | “Specify the shadow start, fixed comparator, monitoring horizon, stopping conditions and decision rule before future data arrive, and do not treat 45 cycles automatically as adequate statistical power.” |

## 3. Creative alternatives: how else could one pick vaults with STABLE profit for this allocation?

I would shift attention from ranking historical smoothness to three questions: **is the profit observable, what risks generate it, and does it diversify the risks already in the book?**

The following are research hypotheses, ranked by my expected **information gained per unit of effort**, not predicted backtest Sharpe. For initial tests, retain the incumbent’s profitable-candidate shortlist, six slots, capacity limits and deployment floor. This makes it harder for an alternative to “succeed” merely by admitting quiet losers.

Metadata availability needs auditing first. The project’s upstream vault model exposes leader identity and fraction, commission, followers, deposit flags and parent relationships, but a field’s presence does not establish historical availability. [Vault data-model documentation](https://web3-ethereum-defi.readthedocs.io/vaults/hyperliquid/_autosummary_hyperliquid/eth_defi.hyperliquid.vault.html). Latest-only fields belong in prospective collection, not backfilled historical selectors.

| Idea | Mechanism | Why it might find stable-profit vaults where the tried approaches did not | What could go wrong | Cheapest first test |
|---|---|---|---|---|
| **1. Separate reporting inactivity from trading inactivity** | Model actual poll arrivals, unchanged polled NAVs, unpolled gaps and catch-up returns separately; add a penalty for stale evidence or unusually large catch-up losses after long gaps. Control for platform-wide polling outages. | Tests whether “steadiness” reflects observable profit or simply missing observations. Staleness becomes a measurement variable rather than zero return or discarded data. | Poll frequency may reflect the collector’s priorities, TVL or popularity. Without raw poll timestamps, flat and stale observations are not identifiable. | For anchor-held vaults, tabulate next observed loss and recovery by preceding gap length, separately before and after April; include endpoint mark age. |
| **2. Select complementary downside exposure** | From the incumbent’s top 18 candidates, greedily choose six with low joint-loss frequency or downside covariance, retaining incumbent sizing. Use aligned multi-day intervals with adequately fresh endpoints. | Six individually steady vaults can lose together. A moderately volatile vault can stabilise the basket if its losses occur at different times. This tests joint selection, beyond a scalar beta or post-selection correlation cap. | Asynchronous marks can manufacture low correlation; tail dependence is poorly estimated. Missing covariance must not be treated as zero. | Compare the anchor’s joint-loss concentration with one fixed six-from-18 construction; first inspect whether correlated groups actually drive portfolio drawdowns. |
| **3. Make retention and exits respond to new evidence** | Keep incumbents through small rank changes; allow rank-driven replacement only after a pre-specified number of new marks. Separately test whether the 14-day momentum exit causes repeated sell-and-rebuy cycles. | Profit may be steady at the manager’s horizon but disrupted by allocation churn. A stale 14-day return can jump from benign to negative in one catch-up mark. | Delaying exits can retain a failing manager. A minimum hold must not override genuine risk or withdrawal constraints. | Attribute exits to rank loss, momentum, availability and risk; measure re-entry frequency and subsequent observed NAV paths, then run one retention-only and one exit-only ablation. |
| **4. Screen the underlying positions for hidden tail risk** | Use historical perp snapshots to measure gross leverage, net directional exposure, concentration, liquidation distance and increasing exposure after losses; distinguish hedged carry from leveraged directional profit. | Return ratios cannot reliably distinguish persistent trading income from a short-volatility strategy before its first crash. Position structure can reveal that difference earlier. | Snapshots miss intraday leverage and external hedges; apparent hedging can disappear in stress. Historical coverage may be unavailable. | Audit archived snapshot coverage, then compare pre-loss exposures for major anchor drawdowns with ordinary periods; if unavailable, start prospective logging. |
| **5. Require positive drift across independent calendar blocks** | Estimate robust log-NAV growth using actual fresh endpoints over fixed calendar horizons; use median-of-block estimates or robust slopes, with explicit endpoint-age limits and positive-growth requirements. | Preserves elapsed time and profit magnitude while reducing dependence on a few extreme marks. It differs from positive-window counts and ratios whose denominators reward missing downside. | Robust estimators can discard real jump profits; overlapping blocks create false sample size; excluding poor endpoints can select observations. | On existing candidates, compare pre-decision robust growth estimates with the next non-overlapping 28-day return, reporting coverage and sparse/dense results separately. |
| **6. Learn drawdown recovery shape** | Measure depth, elapsed and observed-event time underwater, speed of recovery and repeated failure to regain peaks; treat unfinished drawdowns as censored rather than dropping them. | Two vaults can have similar volatility but very different equity experiences: brief recoveries versus prolonged erosion. This targets the path the operator experiences. | There may be few completed drawdowns; stale marks hide depth and duration; ranking only recovered episodes creates survivor bias. | Build a drawdown-episode table for historically selectable vaults and test whether prior recovery behaviour predicts subsequent underwater time. |
| **7. Optimise a small basket directly for path stability** | Compare a limited set of feasible six-vault baskets using trailing portfolio drawdown area or conditional drawdown loss, with turnover and capacity penalties and a retained profit-quality screen. | The operator wants a stable portfolio curve; optimising individual ratios only indirectly targets that outcome. Interactions between weights and simultaneous losses become explicit. | Portfolio-level path optimisation can overfit even faster than score tuning, particularly with few stress episodes. | Restrict to single substitutions from the anchor basket within its top 12 candidates; evaluate one pre-fixed objective and verify whether benefits survive deletion of the worst historical episode. |
| **8. Select conditional on an observable market state** | Use one simple lagged state, such as high versus low BTC volatility, and prefer vaults with comparatively resilient returns or exposures in the current state; pool estimates heavily. | A strategy’s profit can be steady within its operating regime but unstable when regimes change. An unconditional Sortino mixes those behaviours. | Too many states exhaust the sample; polling changes can masquerade as market regimes; regimes are known imperfectly in real time. | Construct a two-state descriptive table using `fetch_binance_price()` and lagged classifications; test interactions before adding a switching strategy. |
| **9. Detect capacity deterioration and withdrawal pressure** | Use lagged net flows, follower concentration, TVL growth relative to trading volume, and changes in deposit status. Prefer managers whose profit persists as capital scales and whose investor base is less fragile. | Smooth historical profit may cease after rapid inflows overwhelm strategy capacity; concentrated withdrawals can disrupt underlying trading. | Flows chase returns, follower counts can mislead, and dollar account P&L is size-dependent. TVL changes must be decomposed into performance and flows. | Reconcile TVL/account-value changes with P&L and flows, then compare forward performance after inflow surges or concentrated withdrawals at matched prior return and TVL. |
| **10. Measure manager commitment and business-model consistency** | Use changes in leader ownership, absolute leader capital, commission policy, follower tenure and flow-adjusted account P&L relative to incremental trading volume; combine with deposit-closure history. | Adds information about incentives and how profits are generated, instead of recycling NAV ratios. Stable commission and capital commitment may help identify a consistent operating model. | Ownership fraction falls mechanically when followers deposit; fees may have little cross-sectional variation; follower growth is not skill; account P&L can include unrealised risk. | Audit variation and timestamp coverage first, then test one variable at a time after controlling for age, size, polling and past return. Avoid a metadata composite initially. |
| **11. Pool evidence across economically related vaults** | Build a hierarchical model by verified leader, parent relationship or position-based strategy family; estimate probability of positive net growth and damaging drawdowns, with a shared family risk component. | The previous shrinkage target was a cross-sectional median ratio. Family pooling can borrow relevant evidence while recognising that several apparently separate vaults share one manager or trade. | Misclassified families contaminate estimates; copied strategies are not independent evidence; a strong prior can hide regime change or a failed manager. | Map verified relationships and report family exposure and loss concentration first; compare leave-one-vault-out predictions from a global prior and a simple family prior. |

For ideas involving withdrawals, there is a concrete mechanism worth investigating: Hyperliquid documents that withdrawals can lead to cancellation of orders and closure of positions when margin is insufficient. That supports examining flow pressure, without assuming slippage on the allocation strategy’s NAV deposits or redemptions. [Hyperliquid’s vault-leader documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults/for-vault-leaders-legacy).

Across these ideas, do not interpolate missing NAVs into an artificially smooth “true” curve. Missing observations create uncertainty about the path. Preserve that uncertainty, and report both observed performance and mark coverage. Likewise, 90% invested in vault shares does not establish that the underlying vaults are economically deployed; position data can reveal internal cash or negligible exposure.

## 4. Prioritised top-five changes to the plan

1. **Repair NB21’s claim and evaluation design.** Label it exploratory; freeze the list; use a common July starting state; evaluate all constraints on the same segment; replace the weak name-effect inference with matched controls.

2. **Establish drop-set parity before interpreting either NB20 or NB21.** Log the actual trading pipeline, separate missing volatility from unscored CAGR, and handle the no-drop branch using actual counts.

3. **Separate simple-rule qualification from incremental-mechanism qualification.** Make NB20’s exemption explicit, choose an executable or precisely defined placebo benchmark, and specify how new N values affect that benchmark.

4. **Replace the statistical machinery that answers the wrong questions.** Use paired uncertainty around the relevant margins, a dependence-preserving family statistic, and actual active-weight/return diagnostics for NB22; audit the inherited Sortino invalidation behaviour.

5. **Spend the main research budget on observation quality and portfolio stability.** Make mark-quality analysis shared infrastructure, replace NB21’s large exclusion sweep with a joint-downside selection experiment, and freeze a prospective shadow protocol before further historical optimisation.

## 5. Which of your creative ideas, if any, should displace one of the three leads, and why

**Idea 2, complementary downside selection, should displace NB21’s full named-exclusion experiment.** It offers a generalisable allocation mechanism tied directly to equity-curve stability. NB21 instead converts an outcome-selected volatility band into permanent identities, then compares them with largely unmatched removals. Keep its frequency and membership tables as a cheap NB20 attribution diagnostic.

**Idea 1, reporting-versus-trading inactivity, should precede all three leads.** It determines whether their risk measurements describe the economic experience the operator wants. This need not become a large modelling project: a reliable poll/mark distinction, endpoint-age audit and catch-up-loss table would already be valuable.

**Retain NB20**, after the parity and adoption-rule corrections. It tests the clearest empirical lead and makes the return–stability trade-off explicit.

**Reduce NB22 initially to the centre plus its measurement audit.** If it produces effectively identical weights and returns, the remaining neighbour sweep has little information value; use that budget for **idea 3, retention and exit attribution**. If it creates material substitutions, complete a corrected, pre-specified local sensitivity test and report what changed in the book.