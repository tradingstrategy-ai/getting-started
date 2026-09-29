# Claude fable review

Date: 2026-09-13. Requested CLI model: `fable`. Review of the initial draft; subsequent responses and changes are recorded in `plan.md`.

**Verdict: sound in its principles, too heavy in its mechanics.** The plan correctly absorbs the timing correction, the missingness lesson from NB13/NB24 and the "screen earns a backtest" rule. It should proceed after the fixes below, and it should shed roughly a third of its ceremony. Nothing in it needs more history than exists, but several parts silently assume power the dense regime cannot supply.

## Required fixes

1. **Forward downside-risk label rewards stale marking.** "All observations in the downside mean" makes carried or unchanged marks contribute zeros, so a thinly polled vault looks safe. Edit Phase 2: compute forward downside deviation and volatility over fresh, non-carried daily returns only, require a minimum count in the window (suggest 15 of 30), otherwise the label is missing. Report the count beside every risk label. The same rule applies to the 30-day risk features in Phase 3.

2. **A measured zero downside is not a missing one.** The plan guards against missing volatility becoming zero risk, but a young vault with no down day in 30 fresh observations has a real zero, and NB78 shows that signature among blow-ups. Edit: add down-day fraction and downside sample count as first-pass features, floor every risk forecast used for sizing at a fixed daily minimum equivalent to the production `VOL_FLOOR`, and state that the 5% young cap applies regardless of the forecast.

3. **The "plain fixed rank score" revives rejected H1.** NB45 rejected rank blends because ranks discard magnitude, and the plan forbids reviving them under a new name. Edit Phase 5: the transparent comparator is a clipped or z-scored linear score in the production style, and the Ridge prediction is the primary candidate. No cross-sectional rank averaging.

4. **Arm C cannot contain young vaults, so C versus D confounds access with ranking.** Production features are undefined below 360 days. Edit the arm table: run arm D twice, once on the broad pool and once restricted to the incumbent-scorable pool. The restricted D isolates ranking information at portfolio level, matching the Phase 4 split. That is one extra run, not a new axis.

5. **Momentum gate placement is ambiguous.** "Hold execution rules fixed" does not say whether the 14-day return gate applies to arms B to D. NB31 measured its removal at roughly 4.5 pp of CAGR and a much deeper drawdown. Edit: freeze the gate as an eligibility rule in every arm.

6. **Missing-outcome sensitivity is unspecified.** Edit Phase 2: bound vanished-vault outcomes with two fixed assumptions, last mark carried to the horizon and total loss. If the shortlist changes between the bounds, the feature is not robust.

7. **Survivorship needs a decision, not a caveat.** Today's curator excludes 191 deposit-closed and 48 low-peak-TVL vaults, and deposit-closure history is almost certainly not archived. Edit Phase 1 step 2: build the research population from every Hypercore vault with raw price history in the snapshot, apply the TVL floor as-of each date from historical TVL, treat deposit status as unknown before the first archived observation and report results with and without today's closure list. Record the 601 to 339 to 320 funnel with the rule used at each step.

8. **The Phase 6 gate repeats NB25's seven-condition mistake.** Five conditions plus an undefined drawdown margin will fail the anchor's own neighbours. Edit: three gated conditions, net CAGR at least 20%, ulcer at least 15% lower, and observed Sharpe not more than 0.2 below the anchor. Report volatility and drawdown but do not gate on them, since ulcer already captures both. Define the drawdown remark numerically if you keep it, for example within 2 pp absolute. Confirm the anchor passes its own rule trivially before running candidates.

9. **Hidden young-vault penalty must be visible.** The augmented Ridge with training-median imputation and missingness indicators will learn that history-short vaults are worse, which NB13 found. That is legitimate evidence, but it contradicts the fairness aim if it is invisible. Edit Phase 3: report the fitted coefficients on each missingness indicator and the resulting mean prediction gap between cohorts, and compare with the common 30-day model on the same rows.

## Simplify or defer

- **Feature catalogue: cut 150 to about 60.** With three to five independent 30-day blocks in the dense regime, a max-statistic null over 150 configurations and several targets will absorb every real effect. Keep the exact production controls, one 30-day and one 90-day version per family, drop 180-day windows except CAGR/Sharpe, and reduce exponential summaries to price/EMA distance and EWM volatility at two spans. Drop EWM Sharpe as redundant with rolling Sharpe. Drop the alpha-neighbour test.
- **90-day quality targets become descriptive.** A 90-day label plus warm-up leaves one or two independent blocks. Decide on 30-day growth and 30-day downside risk. Report 90-day Sharpe and drawdown for the shortlist only.
- **Path-stability labels: keep max drawdown and ulcer.** Time underwater, positive-week fraction and weekly dispersion add multiplicity without a decision they change.
- **One null, not three.** Blockwise permutation of vault identity, run through the full selection procedure, covers the family-selection null. Drop shifted-outcome histories.
- **One allocation threshold.** "Positive expected growth and acceptable downside" is two thresholds. Gate entry on predicted growth net of an approximate exit fee, and let the downside forecast affect only sizing, or nothing in the first pass.
- **Do not stack the 5% young cap with shrinkage.** The plan warns against stacking and then permits both. Use the hard cap only and defer shrinkage.
- **Common-risk grouping: BTC-beta buckets only.** Three buckets by trailing beta replace correlation clustering. Defer clustering until an adaptive arm actually reaches 15 or more names.
- **Sharpe non-inferiority as a statistical test is unwinnable** with a standard error near 1 on this window. Keep the point comparison, print the paired block interval, and drop "statistically supported pass" for Sharpe.
- **Optional, deferred outright:** catch22/tsfresh second pass, BTC-independent outcome label, the 60-day horizon check unless a family survives, and merging the first two notebooks if the panel build is quick.
- **Set expectations for arm C.** NB09's four-slot core and the production breadth search both favour concentration. The 10% TVL cap at $150,000 requires $225,000 of TVL for a full 15% slot, so capacity rather than features may dominate. The cap-matched production control is essential and should run before any A to D reading.

## Strengths

- Timing contract is right: `available_ts` joins, bar-close alignment, future-perturbation test and framework parity directly address the NB57 correction.
- Return and risk targets are separated, and a risk predictor is allowed to win on risk alone against a volatility control instead of being asked for alpha it never claimed.
- Missingness policy keeps short-window columns independent, refuses global row dropping, and gives young vaults a genuine route through the common 30-day model without a quota.
- Availability-only and low-volatility controls, plus broad versus incumbent-scorable reporting, prevent a repeat of NB24's misnamed comparator.
- Fee semantics are correct: fill at NAV, no generic slippage, the 10 basis point charge labelled an assumption, internalised versus externalised fee modes checked.
- Prospective shadow decisions after a freeze are named as the only uncontaminated test, and the four possible conclusions leave room for "insufficient evidence" without inventing power.
