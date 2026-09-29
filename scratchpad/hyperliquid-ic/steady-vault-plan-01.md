# Steady-vault portfolio experiments

## Objective and authority

Maximise net portfolio Sharpe with reasonable net CAGR around 20%. Do not require beating production, preserving its return, or exceeding 30% CAGR. Show the full return/risk frontier: use 18% CAGR as a provisional feasibility floor, highlight 18–25%, and retain higher-return qualifying strategies without giving additional return a selection bonus. The floor is a screening convention, not a promise or a statistically established future return.

This plan governs a new notebook series, 10–17. It does not overwrite earlier experiments. A0b remains an independent simulator; production is a reference. Daily decisions, causal forward-filled valuations, young-vault access and weekly/sparse observations remain requirements. No blanket 90/180/360-day history requirement. No follower counts or other popularity features. NAV, BTC reference returns, vault age, TVL and operational availability are permitted. Known manager identity is used only to avoid concentration.

## Starting evidence

Read `stratwise-selection-study-01.md`, its recent and full-history charts, `production-candidate-vs-research-reproduction-differences.md`, `summary-02.md`, `summary-03.md`, and the saved current metrics. Summary-04 and portions of earlier summaries are stale after forward-fill corrections; CSV artefacts take precedence.

- StratWise, PF1 and Passivbot have attractive recent curves, but PF1 and Passivbot show roughly 13–14% earlier observed drawdowns. Raw mark/repair checks must precede interpreting those events as genuine trading losses.
- FuturAI Medium and Low have slower recent growth and correlation about 0.87. They are related examples, not independent diversifiers.
- Recent volatility predicts future risk strongly; complex growth models have not demonstrated incremental value over simple low-downside controls.
- Old A0 portfolio results are not A0b results. The A0b change was a production-style allowlist plus the manual data-quality blacklist, using the same independent simulator.
- The earlier lower-vol NB32 experiment found that replacing the incumbent ranker with stability ranking performed poorly, while adding a 15% return floor to the incumbent improved its full-window CAGR and Sharpe. Part of the stability rankers' lower volatility reflected cash. This series specifically tests short-history access, repetition of profits, evidence-aware sizing and independent groups. Include that earlier result in the final interpretation; do not claim the general idea is new.

The discovery examples are retrospective and must not become an address whitelist, privileged slots or training labels for a fitted classifier. Looking at these dates has consumed them for discovery; historical walk-forward results remain retrospective validation. No new ML model or optimiser is needed for this series.

## Common experimental contract

Implement one reusable A0b universe loader and configuration in the existing research modules. Freeze the actual allowlist, blacklist, metadata and raw input hashes; record their timestamps. The later allowlist is applied retrospectively, so results are conditional on that snapshot, not a survivor-free point-in-time backtest. Add a full-universe sensitivity for finalists rather than silently changing universes.

Use $150,000 starting cash and two separate cold-start portfolios:

- Full backfilled period: 2025-09-13 through 2026-09-12 inclusive.
- Hyper-ai period: 2026-01-01 through 2026-07-08 inclusive.

Preserve pre-start feature history and the last genuinely available pre-start NAV. First reproduce notebook 08 exactly with its existing input convention; if fixing initial marks changes its output, report the bridge explicitly and version the corrected baseline rather than mislabelling it as exact parity. A no-op arm in each experiment must match the shared baseline's daily equity and target/trade ledgers within numerical tolerance.

NB10 must separate holdings valuation from candidate eligibility: the current simulator updates `last_marks` from eligible feature rows, so a held vault disappearing from that panel can freeze despite later observed NAVs. Maintain a causal mark ledger for every held address using raw observation availability, independent of TVL/admission. If selection eligibility is lost, target zero and redeem at the next execution opportunity permitted by the declared model; do not fabricate a fresh mark, immediate liquidity or an exit at a stale price. Truly dark holdings remain visibly valued at last available NAV, with age, value share and stress sensitivity reported. Preserve the original A0b as a reproduction control; label this corrected version `A0b-v2` and use it for every new main arm. Bridge valuation, fee and initialisation changes separately.

Resolve fees in NB10 using verified per-vault fee metadata and internalised/externalised status, not a blanket 10% charge. Do not assume the cleaned observation file contains fee columns. Unknown schedules use a declared fallback and are flagged. In the corrected main contract, remove the inherited undocumented 10 bp deduction and retain it as a fee sensitivity. Apply the same fee assumptions to qualification and portfolio accounting. Do not change only the candidates while leaving their baseline under old accounting.

Add a minimal explicit target-weight or candidate-selection hook to the independent simulator, defaulting to existing behaviour; it must reach names outside the old top-N. A no-op hook must reproduce the applicable baseline. Full ledger conservation and fee checks remain necessary.

Generate signals daily; retain the A0b two-day execution cadence for main arms. A signal uses only data known at the decision. Preserve and document A0b's execution timestamp convention; if it uses an idealised same-mark fill, label that and test one-observation-delay execution for finalists. Do not add a silently different fill model. Preserve NAV fee treatment, settlement approximations, capacity and state limitations; NAV deposits/redemptions have no invented slippage. Audit external performance fees versus fees already in NAV and separately disclose any inherited 10 bp capital deduction.

Primary ranking uses weekly net excess-return Sharpe with a declared zero reference rate; daily Sharpe is secondary. Report a 5% annual reference-rate sensitivity with no assumed cash yield. Use feasible-first ranking on the declared 18% net CAGR floor. All main arms use the same valuation clock, data and accounting. Compute daily and weekly portfolio metrics separately. Carrying a NAV is valid for valuation; it is not a new observation for estimating risk or evidence.

Report raw mark cadence and repaired-price provenance. Do not infer fresh independent marks from repeated provider writes. Audit mark timestamps versus written-at timestamps and repair statuses, and disclose whether each dataset is reconstructed economic history or a publication-time record. Later writing of backfilled data is not automatically economic lookahead; do not impose an arbitrary written-at <= mark+1-day requirement. Test causal feature cut-offs and identify repairs that use future observations; isolate them with a sensitivity or exclude affected observations where causality cannot be supported. Do not call a constant fresh NAV stale solely because its value is unchanged. Price precision and repairs can distort curves and must be visible.

## Metrics and minimum definitions

Use 30 and 60 calendar days for the main economic metrics, a 14-day early-history view, and up to 180 days of stress context where present. No exhaustive cross-product of windows. Calculate over available history and return missing with a reason when a statistic is not identifiable.

| Purpose | Definition | Use |
|---|---|---|
| Profitability | Actual compounded return and log growth per elapsed year; net liquidation return after applicable external fees for a hypothetical fresh investor | Qualify candidates; do not treat annualised short returns as forecasts |
| Growth spread | First-half and second-half returns over available formation history, with actual observed endpoints and durations | Identify gains isolated in one half; never substitute zero for missing halves |
| Weekly consistency | Positive fraction of non-overlapping, approximately seven-day observed-endpoint returns; require 5–10-day durations and report uncovered weeks | Descriptive repeatability; no overlapping-week sample inflation |
| Event concentration | Largest observed positive log-return event divided by sum of positive log-return events; best-event-removed compounded return | Common sparse-compatible definition; separately report dense top-three-day share for the manual examples |
| Downside | Annualised square root of sum of squared negative interval log returns divided by elapsed years | Downside proxy, not an invariant diffusion estimator; compare within cadence and report interval count |
| Volatility | Dense observed consecutive-daily standard deviation; for sparse data use duration-aware interval estimates with explicit assumptions | Risk sensitivity; never zero-fill to manufacture low volatility |
| Drawdown and ulcer | Observed-NAV peak-to-trough drawdown; square root of duration-weighted squared drawdowns | Recent severity and persistence; carrying marks is only an approximation of unobserved paths |
| Stress memory | Worst observed drawdown and longest unrecovered drawdown in available last 180 days, alongside current drawdown | Separate past loss evidence from missing history |
| Evidence | Distinct intervals, span, typical/max gap, NAV age, precision, repair status | Exposure limits and explanation, not a popularity score |
| Diversity | Correlation of synchronised weekly returns and simultaneous-negative-week fraction; same-manager groups | Group budgets; unavailable dependence estimates do not mean independence |

At least two genuine price marks separated by a day permit an eligibility row and basic growth. Do not impose that tiny evidence requirement on every metric: downside, halves and correlation may be unavailable. Keep these names visible and eligible for a bounded provisional sleeve, rather than pretending their unmeasured risk is zero. A profitable path with no losses has zero observed downside but uncertain future downside; use a sizing floor.

Sparse event concentration depends on observation spacing. Evaluate it within cadence buckets and include a no-event-veto arm. Do not rank a weekly event against a daily event as interchangeable. Joint-loss fraction is conditional on paired observed weeks and must report sample counts; zero joint losses with few pairs is not safety.

## Notebook sequence and bounded options

Every notebook begins with sources, question and changes; ends with results, failed cases and robustness. Save per-date eligibility reasons, signals, targets, accepted dollars, cash, equity and attribution. Feature catalogues and broad grid searches are out of scope.

### 10-research-steady-vault-data-and-a0b.ipynb

Build the shared experiment contract and reproduce A0b over both periods. Audit StratWise identity and panel/allowlist membership by address; it was absent by name in the frozen metadata despite NAV history being present. Include PF1, Passivbot, both FuturAI vaults and jump/plateau counterexamples. Show 14/30/60-day and full histories with the same units and both standardised and absolute return axes. Audit older severe drops against raw/repaired marks. Label each example: recent steady, older stress, jump-dominated, low-return, or insufficient evidence. Keep manual labels descriptive only.

Deliver an input manifest, A0b parity report, coverage table and reviewed example sheet. No strategy search here.

### 11-research-profitability-and-repeatability.ipynb

Construct three diagnostic selection arms, all with identical equal-weight sizing, individual 20% equity cap, existing TVL limits, and residual cash:

- P0: positive estimated net growth only.
- P1: estimated net growth at least 15% annualised, with positive returns in both measured halves.
- P2: P1 plus at least 70% positive measured weeks, largest-event positive-gain share at most 50%, and positive growth after removing the largest gain. Evaluate concentration only within cadence strata.

Use available 60-day history, falling back to 30/14-day views, with actual spans disclosed. Do not demand all three windows exist. Missing repeatability statistics go to the provisional sleeve defined in NB14, not the fully evidenced set. If no measured weekly outcomes exist, no weekly conclusion is made.

Rank excess qualified names by capped net growth (cap the ranking contribution at 30%), then lower downside, then address. No fixed desired position count; operational maximum 20 names keeps tiny positions manageable. Holders blocked from redemption continue to consume capital and caps; disclose infeasible targets. Each arm gets both period backtests and forward 14/30/60-day selected-versus-rejected diagnostics, restricted to comparable available outcomes. Run these three arms on both the frozen allowlist and the full research panel from NB11, with the same data-quality exclusions, to expose universe-selection sensitivity early. Also run a sizing-only control using the incumbent gate/ranking with the same equal-weight, 20%-cap and cash rules. All arms run regardless of whether they beat A0b. Parent configurations remain frozen even if a universe sensitivity changes sign; record that weakness rather than imposing a new gate or selecting a replacement retrospectively.

### 12-research-downside-and-stress-selection.ipynb

Use P1 as the frozen parent (not the best NB11 result). Compare:

- D0: no additional downside screen.
- D1: observed 60-day drawdown no deeper than 3%.
- D2: D1 plus dense annualised volatility at most 8%, using the longest available 14/30/60-day window with at least 80% consecutive observed daily-return coverage and disclosing the chosen span; sparse risk remains provisional until a cadence-matched equivalent is supported.
- D3: D1 plus halve target weights when an observed drawdown in available 180-day history exceeds 8%; retain released capital as cash.

Use the same parent sizing and cap rules. Report D1/D2 pass rates by age and cadence. Compare historical stress penalty with an age-matched control: older vaults have had more opportunities to reveal losses. A young vault with missing stress history gets its evidence cap, not a fabricated clean record. No permanent blacklist for a legitimate loss; raw-data errors have a separate documented exclusion process.

### 13-research-steady-vault-sizing.ipynb

Use P1+D1 as the frozen selection parent. Compare three allocation rules:

- Equal weights across eligible vaults.
- Inverse downside with 5% annualised downside floor.
- Capped-growth divided by floored downside: multiply inverse downside by min(net annualised growth, 30%)/30%.

All weights are target fractions of portfolio equity before capacity/evidence clipping. Keep clipped dollars in cash in the main arms; run one equal-weight redistribution control to distinguish clipping from selection. Individual cap 20%, existing TVL cap and provisional caps apply. Do not silently renormalise after caps. Report cash and invested-basket risk separately; neither raw lower volatility nor fewer nonzero daily returns proves better selection.

### 14-research-young-and-sparse-evidence.ipynb

Use P1+D1 with equal weights as the frozen parent. Reuse the small common evidence policy from earlier notebooks and test alternatives here:

- E0: 5% per-vault provisional cap and 20% aggregate provisional sleeve. Provisional means <30 days available history, fewer than four measured weekly outcomes, or material missing risk/consistency evidence. Basic positive net growth still required.
- E1: 2% per-vault cap, same aggregate sleeve.
- E2: gradual per-vault cap from 2% to 10% as observed interval count rises from 2 to 20, with the same 20% aggregate sleeve while provisional. Show span/cadence separately; event count alone cannot certify independence.

Fully evidenced does not require 360 days. Missing thresholds cannot be bypassed with a zero placeholder. Explicitly report opportunity cost and whether caps prevent reaching ~20% portfolio growth. Use hypothetical weekly-sampled versions of dense curves as a measurement sensitivity, preserving the real observations for performance. Never let the next weekly mark influence preceding daily decisions.

### 15-research-independent-groups.ipynb

Freeze P1+D1, equal weights and E0. Compare:

- G0: no correlation grouping, individual caps only.
- G1: same-manager combined cap 25%.
- G2: G1 plus weekly correlation grouping at 0.75 using at least eight paired weeks in available 90 days. Use deterministic complete-link grouping so every pair in a cluster meets the threshold; missing pairs are not eligible to merge on correlation evidence alone.

Give equal budgets to groups, then equal member weights; cap group exposure at 25% and individual exposure at 20%, with no final redistribution. Unknown-dependence names retain the declared provisional caps only for the grouping arm; report this additional uncertainty cap separately from age-related caps, with one singleton/ordinary-cap sensitivity to measure its cost. They remain eligible. Freeze a verified manager mapping where available; do not infer common management from a vague name-prefix match. Unverified identity is unknown, with FuturAI documented as a manual mapping only if verified. Show sensitivity to the eight-week correlation requirement without turning it into vault admission gating. Report joint-loss frequency and BTC beta as diagnostics, not additional searched filters. Fetch BTC through `tradingstrategy.binance.price.fetch_binance_price()` or reuse the hashed cached reference.

### 16-research-steady-vault-portfolio-validation.ipynb

Compare A0b and no more than four final recipes: fixed simple P1+D1/equal/E0, its P2 repeatability version, its inverse-downside sizing version, and its G2 grouping version. Do not stack every winning switch. Show both cold-start periods and monthly/quarterly segments. Add the pre-discovery segment through 2026-07-15 and the July 16 onward discovery segment as diagnostics; neither is a clean holdout given the earlier research across these dates. Keep the full-period feasibility criterion fixed and report whether the pre-discovery and Hyper-ai periods also meet it. Do not silently replace the primary period with whichever passes. Include the previous floor15 engine result as an explicitly external reference, not a same-simulator selection control. Report daily and weekly Sharpe, net CAGR, volatility, max drawdown, ulcer, cash, turnover, effective position count (1/sum of squared invested-normalised weights), group concentration and fee burden.

Run leader-removal full resimulations, best-event attribution (clearly distinct from a tradable counterfactual), matched-cash controls, one-observation-delay execution and full-universe sensitivity on these finalists only. Report paired block uncertainty with 30/60-day blocks as sensitivity, recognising few independent blocks; bootstrap significance versus A0b is not an adoption hurdle. Also report uncertainty in absolute Sharpe and CAGR, without calling retrospectively chosen finalists independent validation. Report return-target feasibility separately from rank by Sharpe.

### 17-research-steady-vault-selection-explanation.ipynb

Produce the final human-readable decision sheet: each manually reviewed example's eligibility, metric values, rejection/provisional reason, group, requested weight and accepted allocation through time. Show nearest false positives and false negatives, and whether selected baskets actually have better subsequent growth/downside/repeatability on matched outcome rows. Explain the remaining gap to ~20% CAGR if none succeeds. Export `steady-vault-summary-01.md` from saved artefacts, not hand-copied numbers.

## Execution and stopping rules

Implement and execute in sequence with `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent ...`, saving outputs. No prerequisite that an earlier notebook beat A0b; only data/accounting failures block subsequent experiments. The base arms imply roughly 20–25 unique configurations over two windows, plus the NB11 full-universe and sizing-only controls and one grouping-uncertainty sensitivity; reuse identical parent runs by input/config hash. Robustness reruns are limited to the four fixed final recipes. If none meets the return objective, document the shortfall and the closest frontier rather than expanding a parameter search automatically.

Every result must identify its universe, period, starting capital, feature cut-off, fee model, valuation clock and configuration hash. Preserve old artefacts. Test causal feature cut-offs, weekly-mark behaviour, cap/cash conservation, no-op A0b parity and separate-period initialisation. Assertions for known example membership must check identity/data plumbing, not force selection.

This series completes when all defined options have recorded results (including infeasible/missing-evidence outcomes), the final comparison and explanation sheets exist, and the summary distinguishes evidence from proposed future testing. A prospective shadow run after freezing the recipe is the next validation stage, not something these historical notebooks can manufacture.

## Fable review disposition

Reviewed with Claude CLI `--model fable` (session metadata: `claude-fable-5-1`). See [review and disposition](claude-review-fable-steady-vault-plan-01.md). Applied: early universe sensitivity, eligibility-independent held-NAV valuation, versioned corrected baseline, per-vault fees, short-window volatility fallback, sizing-only control, explicit primary Sharpe clock, NB32 correction, target-weight hook, manager provenance, age diagnostics and repair-causality audit. Adapted: no synthetic forced liquidation, no new universe-sign adoption gate, no clean-holdout claim for old dates, and no arbitrary publication-lag cutoff. Historical discovery cannot establish prospective performance.
