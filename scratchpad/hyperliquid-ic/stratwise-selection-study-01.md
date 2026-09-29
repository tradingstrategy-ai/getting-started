# Reverse engineering steady-return vault selection

## Scope and evidence

Manual visual discovery using the frozen research NAV observations through 12 September 2026. The matched recent window is 16 July–12 September (59 daily marks, 58 elapsed days), matching StratWise's available history. These are descriptive, retrospectively chosen examples, not an out-of-sample portfolio or deployment shortlist. The broad numerical discovery screen (growth 8–150% annualised, volatility below 30%, drawdown above -10%, TVL at least $7,500, daily coverage at least 80%, at least 20 observed days) was used to make a manageable chart set, not proposed as the production rule. Nineteen distinct curves were plotted and visually inspected. Sparse vaults excluded from this discovery screen remain an unreviewed population, not rejected investment candidates.

Identity was matched by address against local metadata. StratWise is missing by name in the frozen research metadata but its observations exist at `0x0ff219ac20596b457558341bc410bc7a08a1394c`. Its identity was verified against https://tradingstrategy.ai/vaults/stratwise-multi-asset-public on 15 September 2026. The live page reports history starting 16 July and externalised performance fees; its updated numbers differ from our frozen September 12 endpoint. Other names use local cached metadata, not live availability verification.

## Manual examples

All recent metrics below are gross share-price statistics, before investor-level external fees. Annualisation of 58 days describes recent pace, not an expected annual return. Daily observed closes are used without inserting missing-day zero returns. Full-history drawdowns are observed-mark drawdowns; sparse earlier sampling can conceal intervening risk.

| Vault | Recent cumulative return | Annualised pace | Annualised daily volatility | Recent max drawdown | Full observed max drawdown | Visual judgement |
|---|---:|---:|---:|---:|---:|---|
| StratWise | 4.04% | 28.3% | 3.9% | -0.65% | -0.65% | Reference: gradual gains with a few steps, small setbacks; only 59 days observed. |
| PF1 | 4.93% | 35.4% | 3.5% | -0.58% | -13.52% | Closest recent visual match; earlier substantial drawdowns, particularly June. |
| Passivbot Canon | 3.95% | 27.6% | 3.9% | -0.89% | -13.85% | Recent gradual rise after a flat start; January–February history much rougher. |
| FuturAI Labs — High Sharpe, Medium Volatility | 1.71% | 11.3% | 1.2% | -0.12% | -6.02% | Very smooth recent curve but slower growth; abrupt June drop. |
| FuturAI Labs — High Sharpe, Low Volatility | 1.56% | 10.2% | 1.3% | -0.14% | -3.36% | Similar defensive example; same June disturbance. |

PF1 address: `0xa1b6d8efbcb2fb750a84dbc05649fa4968034f04`.
Passivbot Canon: `0x490af7d4a048a81db0f677517ed6373565b42349`.
FuturAI Medium: `0x53375ca9a649f337d83d0834fec0db97640a2a06`.
FuturAI Low: `0xb65dd7c56afbf3b272ab5fc49be44b47dca18003`.

The top three positive daily returns contribute 36% of gross positive-return sum for StratWise, 24% for PF1 and 34% for Passivbot. This is not the share of net profit. A rule demanding perfectly even daily profits would reject the intended reference. FuturAI Medium and Low have recent daily correlation 0.87; they should not count as two independent portfolio diversifiers.

Counterexamples matter: Citadel has a superficially attractive upward curve, but 62% of its summed positive daily returns are in its three largest gains and its chart is dominated by a jump followed by a plateau. Satori Quantum and HyperTwin also show concentrated August rallies. HYPErQuantum4 has consistent growth after an initial sharp drop, but roughly 10.5% recent volatility; it is a higher-risk adjacent example rather than the closest match.

The older falls need raw-price/repair-status checks before attributing their cause to actual trading losses. This study establishes visible path behaviour, not strategy type or the absence of tail risk.

## Candidate selection rule to test

Use a small set of interpretable measures. The values below are initial hypotheses, chosen after looking at examples; freeze them before evaluating subsequent data. Do not optimise them to guarantee these particular vaults are selected.

1. **Enough recent profitability:** estimate growth over available trailing 30 and 60 calendar days, with a 14-day early-history view. Look for roughly 15% or better annualised net growth and positive growth in both halves of the available formation window. Rank profitability only up to the desired 20–30% range, so an explosive winner does not automatically outrank a steady earner. A trailing threshold is not a forecast or a portfolio return guarantee. FuturAI may fail this floor and remain a defensive comparator.
2. **Low downside:** among profitable candidates, favour low observed downside deviation and shallow drawdown. A provisional dense-data screen is annualised volatility below 8% and 60-day drawdown no deeper than 3%. Treat longer-history stress losses as additional evidence requiring lower weight or review; inspect the last 180 days when present, without requiring 180 days for entry.
3. **Distributed profits:** use positive weekly-return frequency and the share of positive gains contributed by the largest observations. Start with at least 70% positive observed seven-day windows and no more than 50% of positive-return sum in the three largest daily gains, only where daily data supports that definition. Also report growth after removing the best gain and growth separately in each half. Overlapping windows are descriptive, not independent observations.
4. **Honest treatment of sparse/young evidence:** a missing 60/180/360-day feature is missing, not zero and not rejection. Use the available span and disclose observed intervals, elapsed days, freshness, and price precision. Weekly data needs calendar-aligned multiweek growth and interval-based risk; do not apply dense daily-volatility or top-three-day thresholds to weekly marks. Until those equivalents are validated, mark the evidence provisional and limit exposure rather than inventing daily observations. A fresh unchanged NAV and a carried stale NAV are distinct.
5. **Diversity after selection:** group very similar return paths and known same-manager vaults. Manager identity is a diversification constraint, not a return predictor. Count the two FuturAI examples as one group unless stronger evidence supports independence. Measure BTC exposure as a diagnostic; low daily volatility alone does not establish market neutrality.

For young vaults with too little evidence even for the short measures, produce an eligibility/explanation row and watchlist status rather than claim confidence. This is not a global long-history barrier.

## Portfolio construction hypothesis

Start with equal weights across qualifying independent groups, split a group's weight across its members, and cap individual-vault exposure at 20% and provisional young/sparse exposure at 5%. Apply NAV/TVL capacity and actual deposit eligibility afterwards; retain excess in cash rather than automatically adding weak candidates. These illustrative caps must be tested, especially if many qualifying vaults are young: the constraints may make the 20% portfolio CAGR objective infeasible.

This is intentionally an initial construction rule, not a measured optimal allocation. Compare one alternative using inverse-downside sizing with a risk floor to avoid infinite weights. Avoid pure inverse-variance initially: the FuturAI examples demonstrate how the lowest-volatility names could absorb most capital despite only 10–11% recent annualised growth. Portfolio breadth follows qualifying independent opportunities, not a requirement to fill a fixed number of slots.

Do not report a portfolio of these retrospectively selected names over this discovery window as proof. A hindsight illustration, if produced, must be labelled as such.

## Next validation

- Apply the same manual rubric at earlier cut-off dates with all later prices hidden, including candidates that later failed; do not select examples only from today's survivors.
- Audit the older June/February falls against original marks and the reconstruction's repair flags.
- Evaluate candidate selection against the following 14, 30 and 60 days, using observed outcomes and explicit coverage; assess net growth, downside and concentration jointly.
- Replay the frozen selection rule in the shared independent A0b setup over both standard periods, preserving the separate prospective universe limitation of its retrospective allowlist. Audit whether named examples are excluded by that list.
- Freeze discovery labels and thresholds; maximise portfolio Sharpe subject to a reasonable roughly 20% net CAGR objective. Retain less profitable defensive variants as comparators rather than forcing the target through leverage or concentration.

## Artefacts

- [Recent curves, page 1](_artifacts-stratwise/curve-review-1.png)
- [Recent curves, page 2](_artifacts-stratwise/curve-review-2.png)
- [Full histories of manual examples](_artifacts-stratwise/manual-full-histories.png)
- [All discovery metrics](_artifacts-stratwise/all-curves.csv)
- [Candidate correlations](_artifacts-stratwise/manual-candidate-correlations.csv)
- [Reproduction script](stratwise_curve_study.py)
