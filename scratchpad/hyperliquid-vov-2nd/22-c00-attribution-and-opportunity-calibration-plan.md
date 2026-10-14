# Experiment 22 — C00 entry-margin calibration

Reviewed research plan, 13 October 2026. Intended notebook: `22-research-c00-entry-margin-calibration.ipynb`. The objective is **higher net profit with an explicit risk trade-off**, using C00 as the unchanged core. This document reports no new experiment results.

## Goal and method for the notebook heading

We have already mapped ranking features, risk estimation, score weighting, allocation methods, cash gates and wider portfolios extensively. The remaining question is whether information near C00's actual admission boundary can identify entries worth declining, without replacing its successful selection and sizing system. Relative discrimination and an absolute positive expected return are separate claims.

The experiment first audits C00's realised entry losses and entry timing using its saved ledgers. It then evaluates existing forecasts on a narrow, causally defined entry-eligible rank band, calibrates their relative spread and level separately, and checks activation on actual C00 proposals. Only a supported, active, pre-registered treatment receives an engine comparison against C00 and whole-entry placebo controls. A component factorial is an optional accounting-reconciliation appendix, not the main research search.

All conclusions remain exploratory on previously researched history. There is no new feature catalogue, score optimiser, risk-budget optimiser, extra-position sleeve or deployment decision.

## Why this differs from earlier work

The starting evidence is [the audit of 418 notebook files](ranking-exposure-sizing-audit.md), plus [NB21's assessed implementation review](21-marginal-profit-implementation-review.md).

| Earlier work | Already learnt | The precise change here |
| --- | --- | --- |
| IC25–29; VOV66–86 | Ranking, exposure and sizing can already be separated | Reuse those distinctions; do not describe them as novel |
| Waterfall38–51; vault-model04–09 | Better broad IC need not improve the actual basket; learned ranks and young sleeves can fail | Fit/evaluate around a C00-derived entry-eligible boundary and report actual entrants separately |
| NB08 | The absolute floor rejected zero actual proposals | Activation and funded dollars are checked before additional accounts |
| NB10–16 | Constraints and estimator/allocator interactions matter | Preserve C00 sizing/caps rather than install a new optimiser |
| NB17–19 | More cash use often finances weaker exposures | A rejected new entry leaves cash; no mandatory refill, overflow or incumbent sale |
| NB21 | Profitable C00 cohort predicted negative; broad-pool level calibration and magnitude tails are unresolved | Separate the shared return level from within-band ordering, and shrink towards a same-population pooled estimate |
| NB15/16/20 | Six of eight score/risk/allocator combinations already exist, but not all share the latest accounting | Optional matched reconciliation; no claim of six new methods |

## Registered questions

- H1: There is economically relevant downside headroom in fresh C00 entries, beyond merely delaying their admission.
- H2: Existing prediction ordering adds information within the entry-eligible band, and its absolute net-return levels can be calibrated there.
- H3: A selective entry veto improves net account economics beyond causal whole-entry random vetoes and the unchanged C00 control.

Do not use a single CAGR or Sharpe cutoff to declare success. Report profit, Sharpe, drawdown, fees, capital utilisation, contributor dependence and treatment activation together. A profitable but riskier treatment is a trade-off, not automatically a replacement. A treatment inside the placebo range has no identified selective advantage; a treatment outside five placebo runs is only an exploratory lead, not a significance claim.

## Fixed data, periods and execution

- **Primary:** fresh USD 150,000, `2026-01-01 ≤ T < 2026-10-05`, through 4 October UTC; all earlier warm-up, including 2025.
- **Long diagnostic:** independent fresh USD 150,000, `2023-03-01 ≤ T < 2026-10-08`, through 7 October; final archive day partial. Its2026 segment carries earlier wealth and is not the fresh 2026 account.
- Freeze the repaired input generation used by NB20/21. Do not refresh data or repositories during the experiment. If inputs already changed locally, resolve and record the common available generation before results; do not claim old parity across changed inputs.
- The primary baseline is exact C00 under NB20's common corrections: one partial-redemption fee, reopened-position tax reset and buys funded from final synchronous net sale proceeds. Keep paid charges and open-position liabilities separate.
- Preserve the inherited 10% positive-profit fee plus 0.1% capital allowance for comparability, but label them as assumptions. No invented vault slippage. Gross and net labels appear side by side; zero-extra-fee labels are a cheap sensitivity, not another engine search.
- Same source universe, curator/guards, TVL/deposit constraints, six slots, hysteresis,14-day return gate, native 2-day cadence, buy/sell bands and cleanup rules. This is a rule comparison, not verified live account replication.
- Known historical permission fields survive missing independent clocks. Unknown availability is reported explicitly. Archive write times do not certify receipt times.

Features use completed T−1 daily buckets. Quotes use recorded observations at/before the decision. Causal NAV filling starts at inception; no leading backfill. Actual observation/update counts, quote age, calendar history and undefined ratios remain separate. Young or unscored vaults are not excluded merely for missing long histories. An unsupported forecast leaves the source entry unchanged.

## Stage 0 — ledger check before any new economic accounts

Read the NB20 C00 equity/trade/position ledgers and source/data fingerprints. Compare reference identities; a fresh C00 replay is allowed later only if required for control parity or missing ledger fields. This stage is deliberately cheap.

### Entry-loss headroom and management

Define an entry spell from an actual newly opened C00 position until it fully closes; reopening starts another spell. Record initial units, top-ups, partial sales, realised fees and remaining units. Show both total-spell economics and the initial-entry cohort's economics. Do not treat all later top-ups as the initial purchase.

For initial units u0, split every actual sale and remaining holding proportionally between tagged initial units and top-ups; allocate the **actual modelled net proceeds/charges** on the same basis. Fees in the engine use remaining weighted-average basis: do not introduce a FIFO fee model. Top-up and partial-sale tags are accounting attribution, not a claim that removing an entry would preserve subsequent trades.

`y_spell = (allocated realised net proceeds + allocated ending net liquidation value − initial entry cash spent) / initial entry cash spent`.

Reconcile tag totals to actual net sale cash plus open liquidation value. Report fully closed spells separately from open/censored ones. Capital-weighted and equal-spell lifetime distributions are both required: the previous four-day median counts positions, not invested dollars.

Compute `L = sum_e q_e * max(−y_spell_e,0)` separately for closed and marked-open spells. This is **frozen-ledger hindsight loss headroom**, not an upper bound on a portfolio veto policy: changed cash, subsequent purchases, rank retention, fees and compounding can exceed or reverse it. Show its size relative to C00 profit and observed quarter losses, without an invented “materiality” cutoff.

Also count entry proposals by decision, whether whole-entry randomisation can distinguish names on that date, and losses concentrated in one vault/update. Report subsequent re-entry within one/two native cycles and first-time versus repeated top-six appearances. This assesses the non-fitted “confirm one cycle before buying” idea without adding a trading arm.

### Horizon registration using past data only

The admission decision is revisited every 2 days. Existing models provide H∈{2,7,30}. Use H2/H7 as the two permissible primary candidates, with H30 diagnostic only.

On **fully matured pre-2026 entries**, compare their fee-aware buy/hold/liquidate labels against initial-unit managed spell returns on exactly common support. Within each entry date, weight absolute discrepancy by initial entry cash, then give dates equal weight. Choose the H2/H7 label with lower discrepancy under that fixed weighting; tie favours H2 as the native decision interval. Record both equal-spell and dollar-weighted discrepancies, separately for winning/losing spells, plus closed-spell coverage and censored exposure. This alignment selection uses neither2026 profit nor prospective labels. Freeze H before 2026 calibration/results.

If no common pre-2026 cohort exists, use registered H7 as an explicit approximation and make no alignment claim. Spell selection is conditional on closure, so report its limits. H30 remains a separate diagnostic; never choose it because it yields a better backtest.

NB21's H2 penalty selection reported unsupported folds. If H2 is chosen, reproduce the existing causal penalty/fallback exactly and label its selection unsupported; do not claim the old validation worked or silently retune it. If a concrete temporal/fit defect prevents causal predictions, stop for a written amendment.

## Stage 1 — narrow rank-band forecasts without portfolio state leakage

### Define the population before labels

At every native decision, build the **new-entry-eligible universe** using source historical TVL/recent-return checks, new-entry whitelist/guards and deposit policy, without assuming holdings or spending cash. Rank by frozen C00 score descending, then canonical address. Retain ranks1–8; eight is the inherited exit boundary, not an optimised width. This is a derived entry-eligible band, **not an exact reconstruction of the incumbent-sensitive source candidate ranking**.

Keep unscored entries with source tie behaviour. Risk absence is a feature/support issue, not an automatic exclusion. Maintain source requested membership, actual funded membership and this derived band as separate ledgers.

A homogeneous-fee, fresh-entry per-dollar target does not require an executable USD 1 trade. It is a mathematical normalisation. Label all band rows with supported NAV endpoints. Separately flag whether a real minimum-sized ticket could enter under the account's current capacity and permissions. Those flags depend on actual account state and are for evaluation, not for selecting the fitting sample.

Evaluate forecasts on (a) the full derived band, (b) exact actual C00 new proposals/fills, (c) actual next-ranked non-core candidates. Show origin/vault/dollar coverage and score dispersion. Show past history cohorts and actual update support; do not fit independent young/mature models or introduce a minimum vault age.

Predict on band ∪ actual proposals, centring prediction signals on the band only. Show any actual proposals outside the derived band; they are diagnostic predictions and **pass through C00 for trading**, because the calibration was not validated outside that band. Investigate their source-versus-derived eligibility/rank differences before interpreting the study.

For boundary opportunities distinguish **add** (residual cash available), **replacement** (an actual source proposed purchase could be redirected) and **not currently fundable**. These are diagnostics only. Do not assume a sale of the core, extra slots or liquid cash from a blocked redemption. No boundary purchase is made by the primary policy.

### Labels and availability

For a fresh unit of cash and source entry shares/basis, use the exact shared fee helper to compute terminal net value at H. With no entry charge and basis1, the inherited model simplifies to:

`y_net(r) = (1−c)(1+r) − f*max(r,0) − 1`, where c=.001 and f=.10.

Use the actual helper for rounding/entry conventions; never charge the performance fee on the expected return instead of the return distribution. Gross return and net return are separate outputs.

Primary NAV labels carry marks after inception on the calendar grid, but require continued actual reporting supporting the endpoint before archive end. Record origin/terminal quote times, actual updates, endpoint age, the first later observation supporting continued reporting and **Mature_at**, the latest date needed to construct/confirm the label. Training may use it only after Mature_at. Do not interpolate a later price backwards.

Do not inherit NB21's hidden≤1-day endpoint-freshness rule as a silent exclusion. Report native carried/source views and fresh-endpoint diagnostics separately. Labels beyond the last actual report remain unresolved; `mark-only` values are a declared sensitivity, not a realised payout. Future redemption restrictions/lockups remain economic feasibility flags. A calculated NAV return is not proof of an executable liquidation.

Retain every opportunity row before outcome masking. Report count and actual-entry dollars unresolved and last-report/closure cohorts. For an entry veto, loss-to-zero is a **favourable** missing-outcome scenario: it increases avoided losses. Mark-only carry is a distinct scenario, not a guaranteed adverse bound. Positive unknown outcomes hurt a veto, and there is no known finite upper bound. For closed-spell label value V_res and unresolved vetoed initial dollars Q_U, show `V(z)=V_res−Q_U*z` and the break-even missing mean `z*=V_res/Q_U` when Q_U>0. Carry, loss-to-zero and this break-even display retain their separate meanings. No fixed finite upper return is invented for unknown outcomes. Do not fit disappeared outcomes as zero. If resolved-versus-unresolved selection can reverse an apparent gate benefit, withhold the economic interpretation.

### Frozen forecasts and calibration

No feature or penalty optimiser. L0 is an expanding equal-origin weighted pooled **net-return level** for this derived band. L1 uses the C00 score as its relative signal. L2 uses the existing causal NB21 D distribution converted once into expected net return. L2 is the registered primary; L1 is a diagnostic, not a rescue policy if L2 fails.

For H and model z, fit a common level and a within-origin slope from historical **out-of-time** predictions:

- For each model use matured, signal-available paired band rows for both alpha and beta. `alpha = equal_origin_weighted_mean(y_net)` on those rows; show the matched-cohort L0 comparator and the global-band L0 separately;
- Centre both z and y over the **same matured, signal-available rows** in each training origin;
- `beta = max(0, sum_t mean_i[z_centered*y_centered] / sum_t mean_i[z_centered²])`;
- `y_hat_i,T = max(−1, alpha + beta*(z_i,T − mean_band(z_T)))`.

Each training origin receives equal weight. β is not clipped above1: NB21 may have compressed useful spreads, and a cap1 would prevent correcting that. Report raw/conditional slope uncertainty and any physical−1 prediction clipping. This is a **direct net-value calibration**, not a reconstructed gross-return distribution; do not reapply fees to y_hat. No magnitude-based position sizing uses it.

Historical z values must be generated by a model fitted using only earlier matured observations. Do not train an NB21 head on all development dates and backscore them. L1's score is itself fixed and causal. Record each underlying fit generation and training cutoff. Permission-era extrapolation and constant/near-constant signals are explicitly audited; no new metadata predictor is added.

Fit/refit monthly on expanding matured data. Define mathematical existence separately from claimed credibility:

- no matured origin: no forecast;
- at least one matured origin: L0 can be reported as provisional;
- slope requires at least two distinct matured origin dates and positive within-origin signal variance; otherwise β=0;
- no useful variation/support for a row: use L0, with fallback reason.

These are identification rules, not evidence of reliable forecasting. Report vault counts, horizon-length independent calendar blocks, coefficient instability, and block-bootstrap intervals. Young vaults use the common fit/missing flags. Missing score does not supply a measured zero value: distinguish an unscored group, and use L0 when no relative signal exists. Training uses matched matured pairs; prediction centres on the current signal-available band. Report their masses, excluded groups and each recent training origin’s matured fraction. Partial maturity can favour frequently updated vaults; equal-origin weighting does not remove that selection.

For **relative-D identification**, require at least two matured origins, each with at least two supported non-pool D rows and positive within-origin signal variance. The general two-date algebraic rule does not substitute for this. Record the matched origins and counts; this is identification, not a statistical reliability guarantee.

Critically, distinguish a supported **underlying D forecast** from its pooled cold-start output. Pool-only D or unavailable D provides no relative D signal and cannot trigger L2 vetoes; it falls back to C00 pass-through for trading. A provisional L0 or mathematically identified slope does not alone authorise an entry veto.

### Calibration, activation and attribution checks

Produce out-of-time pre-2026 validation and2026 prequential reports. Update using matured past 2026 labels only, labelled exploratory research. Compare L1/L2 with L0 on common support: net-return mean error/MAE, calibration slope, rank IC and sign reliability; do not use0.25 as an automatic Brier baseline. Include zero-return and unchanged raw-D controls.

Evaluate the fixed≤0 veto rule on actual C00 proposal ledgers. Trading additionally requires alpha>0, beta>0 and at least two supported signal-available band rows at the decision. Otherwise pass through with a recorded reason. A negative pooled level is not authorised to shut down the core. Report `dev*=−alpha/beta`, the implied current threshold, and band/proposal fractions below it; an uncapped large beta can turn this into below-mean selection. This experiment tests relative selective admission around a positive level, not an aggregate exposure policy. Show proposed dollars vetoed, labelled loss avoided, positive returns missed, delayed/repeated proposals and unresolved dollars. Those calculations are frozen-ledger signal diagnostics, not causal account PnL.

A same-state placebo randomises existing relative signals across band identities within an origin before evaluating actual proposed entries. Permute over band ∪ proposals within support/missingness groups, keeping the common level fixed and recomputing the band mean after each permutation. Only in-band actionable proposals can be vetoed. Preserve proposal identities, amounts and source ordering. Also use calendar-block reassignment of signal deviations within past-history regimes, because dates with one proposed entry have no within-date identity contest. Use 999 ledger permutations with fixed seeds. Calendar reassignment uses calendar quarters and the recorded underlying-D support era as groups, with block length at least H; report long managed-spell dependence and sparse effective blocks. Report empirical resolution and reused-history limitations; these are cheap diagnostics, not999 engine runs. Quarter and largest-vault deletion hold the original ledger fixed and are labelled accordingly.

The qualification label is **initial-unit managed y_spell for fully closed pre-2026 entries**, whose close/outcome availability precedes the cutoff. H-label value is secondary. Form proposed/veto identities before masking outcomes. Compare informed and placebo values on the same resolved opportunity universe, report totals and per resolved vetoed initial dollar (`sum(−q*y_spell)/sum(q)`, undefined when no resolved veto dollars). The per-dollar comparison is conditional on outcome support; disclose unresolved vetoed dollar fractions for every method.

Before expensive accounts, require: valid chronological/control identities; the defined supported relative-D identification; out-of-time pre-2026 selective managed-spell value **per resolved vetoed dollar** positive and above the median declared ledger placebo on common support; at least one actual pre-2026 executable proposal affected; and no reversal in the declared pre-2026 mark-only carry scenario. Loss-to-zero is not an adverse test. If unknown positive outcomes could reverse the lead, display their break-even level and call qualification conditional, not robust to all missing outcomes. Report total pre-2026 activation and its uncertainty instead of inventing a “meaningful number” threshold. An interval including zero is inconclusive, not an automatic failure or evidence of no skill. The gate requires a working supported D model plus enough variation for a causal validation comparison, not merely two rows satisfying algebraic existence.

Save a `stage2-registration.json` go/stop record with the pre-2026 metrics, horizon and policy before opening any 2026 prequential outcome/label-value tables. A2026 proposal activation count may be examined without its outcomes. If these conditions fail, stop at the completed ledger/calibration notebook. If the frozen rule then affects no 2026 proposals, report a no-op rather than tune the floor. No score-percentile, loss-confidence or horizon search rescues it.

## Stage 2 — conditional whole-entry comparisons

Maximum primary 2026 matrix: C00 control plus one informed entry policy and five placebo policies. The same fixed matrix is evaluated on the long calendar if this stage is reached; do not use2026 profit to decide whether to run the long comparison.

| Arm | Treatment | Scope |
| --- | --- | --- |
| C00 | Exact unchanged source-authoritative core | Control/parity; reuse identical saved output when possible |
| O1 | Veto a supported fresh buy if calibrated L2 expected net value≤0 | New positions only; no change to top-ups, incumbent trims/exits or core sizing |
| R01–R05 | Seeded whole-entry random veto with causal reference rate | Five descriptive controls; counts/exposure audited, not assumed matched |

### Veto implementation

Apply the veto **after source selection, allocation and executable funding**, leaving that selected slot empty for the current decision and preserving all other intended targets. Follow the same position-state semantics as an unfunded/minimum-buy-floor selected target: no phantom holding, persistent slot reservation, pending buy or incumbent protection. Future source incumbency is determined by actually held positions. O1 and each R arm must be trade-identical to C00 up to their first veto; a zero-veto2026 rule must reproduce the entire C00 trade/equity path. Zero/remove only the affected fresh buy. Do not veto through `check_entry_candidate`: the source would fill the slot with the next-ranked vault. Do not renormalise remaining targets, raise the position count or recycle the withheld dollars. Recheck funded trade feasibility and keep sells/settlements unchanged. Explicitly log proposed, suppressed and executed buys. All source cleanup/bands apply to unsuppressed trades; next-cycle holdings can legitimately change later core decisions.

Unsupported or pool-only D predictions pass through C00. Existing positions are never force-sold by a new-entry forecast. No beta/concentration cap, risk-budget change or tighter cash reserve is introduced.

### Causal random-veto rate

R arms must not use O1's realised full-period veto frequency. At decision T, compute π_T from **earlier actionable proposed fresh entries** on a frozen C00 reference schedule, through T−2, using the same contemporaneous registered L2 rule. Initialise from prior supported pre-2026 reference proposals for the 2026 account. For the long account use only earlier proposals from its causal reference history; no earlier support means no veto. Preserve every forecast cutoff in this reference ledger.

`pi_T = previous vetoed actionable reference-proposal count / previous actionable reference-proposal count`.

Use the same actionability checks as O1 (in-band, supported non-pool D, identified positive beta, positive alpha and at least two signal-available band rows). Past rate denominators count those same actionable reference proposals. Unsupported/non-actionable proposals pass through. For an actionable current fresh entry, veto if deterministic `U(seed, date, canonical address) < pi_T`. Repeated proposals get new date keys; report that this may delay rather than eliminate entry. Unsupported proposals pass through. Engine seeds are exactly 1–5 for R01–R05. U uses a stable SHA-256 key containing `nb22`, seed, naive-UTC decision date and lower-case canonical address, converted to a uniform value using its first 64 bits; never use Python’s process-dependent hash. Ledger seeds are 1–999 in a separate `nb22-ledger` namespace. These seed/count choices are computational conventions, not tuned economic parameters.

This matches a **causal rate rule**, not exact realised trade counts, invested dollars or exposure paths. Report count- and dollar-weighted veto rates, support calendars, actual cash/holdings and fees. A rate mismatch, minimum-ticket effects or nonlinear feedback prevents calling O1−R a pure selection effect; use the exact same-state ledger placebo for that mechanism and full engine results for complete policy economics. Dates with pi_T=0 give C00 copies and no placebo information. Five runs give a descriptive range, not a formal tail probability. Do not retrospectively add seeds until significance appears.

Report O1 versus C00 and all placebo runs, with supported-treatment periods separated from pass-through history. Long-account early unsupported years remain in headline metrics and cannot be credited to the forecast. Use identical complete calendars for all methods. The H2/H7 choice and qualification are selected using pre-2026 data: applying that frozen configuration on the long calendar is retrospective configuration evaluation, not a historically chosen policy or an independent validation. Every long-date model fit, slope, outcome maturity and random rate must still use strictly earlier information. Pre-2026 qualification does not make 2026 or the long diagnostic untouched validation.

## Optional appendix — component reconciliation

Do not start this appendix automatically. It addresses attribution, not the primary entry hypothesis, and may be implemented later without changing the registered entry experiment. The genuinely new cells are v11 score with regularised risk under the two allocators. Earlier six cells predate some common accounting corrections; never mix their old profits with new profits to calculate interactions.

| Cell | Score | Risk package | Allocator | Previous economic version |
| --- | --- | --- | --- | --- |
| F000 | v11 | source | proportional | NB15/20 V11 |
| F100 | four-input | source | proportional | NB15 A |
| F010 | v11 | regularised | proportional | New combination |
| F001 | v11 | source | waterfall | NB16 V11-W |
| F110 | four-input | regularised | proportional | NB15 C |
| F101 | four-input | source | waterfall | NB16 A-W |
| F011 | v11 | regularised | waterfall | New combination |
| F111 | four-input | regularised | waterfall | NB16 C-W; corrected NB20 C00 |

If only F010/F011 plus current F000/F111 are compared, show the available four-cell conditional contrasts only. A full interaction table requires all eight cells under the same frozen data/accounting,16 accounts across both complete calendars. Do not infer missing cells or apply old CAGR differences to current profits. No Shapley chart is needed.

Risk factor means the whole package: lookback/support, source floor, partial history, actual-update confidence, eligible peer pool plus selected incumbents, shrinkage and fallback. Raw risk absence yields weight0. With inclusive zero selection, that name can keep its slot; proportional funding gives zero while waterfall can fund it last. C00's risk helper can instead assign equal raw weights to the entire basket if any selected risk is unusable; waterfall then follows existing insertion order. Score ties also affect incumbent eviction.

Log zero-weight slots/funded dollars, basket equal fallback, waterfall order, boundary score ties and requested/funded membership. Any “allocation-only” result must disclose membership effects. Compare same-state shadow targets separately from path-dependent accounts. Reproduce F000 through the matrix harness against NB20's independent source callback, including trade signatures, before attributing factor effects. R1 is not shrinkage alone; A1 is not always measured-risk ordering.

## Output structure and visual acceptance

All main tables, figures and narrative comparisons default to2026. Every chart title includes exact dates and target horizon where applicable. Each element has its own sentence-case subheading, clear description, then table/figure; no image collations.

1. Goal, prior evidence, fixed rules and stage matrix.
2. Input/source/accounting identity and reference parity/status.
3. Entry spell lifetime/count/dollar tables; loss-headroom contributions; separate closed/open charts and pre-2026 horizon-registration table.
4. Opportunity funnel: entry-eligible band→signals→capacity/minimum-feasible→actual C00 proposal→filled→resolved. Label coverage includes calendar and invested dollars.
5. Separate forecast/realised scatter for L1/L2 at each H, quarter-coloured, zero/identity/calibration lines. A separate centred scatter shows within-origin discrimination. Overlap and samples are explicit; headlines average origins.
6. Net-level calibration and sign reliability heatmaps/tables, alongside raw-D/L0/zero controls. Show risk/support, young/unscored and vanished-report cohorts. Do not silently colour missing values as good outcomes.
7. Actual-proposal activation, avoided/missed outcomes and ledger-placebo distribution; re-entry delays and inference limits.
8. If Stage 2 activates: colourised side-by-side profit/CAGR/Sharpe/Sortino/maxDD/fees/turnover/cash/count table; shared equity curve, drawdown/cash curves and separate absolute asset-weight charts including cash. All placebo curves use one lighter colour family.
9. Quarterly profit and return heatmaps, partial quarters marked; largest profit differences and matching NAV/account intervals. BTC/ETH returns are percentages, using `fetch_binance_price()` if needed.
10. Long diagnostic in a separate section, with supported-versus-pass-through phases. Optional factorial appendix clearly marked executed/unexecuted.
11. Hypothesis verdicts, economic trade-offs, mechanisms demonstrated and limitations.

Static saved outputs must render in VS Code; visually inspect every separate saved image. Suppress per-cycle stdout/widget bars in saved outputs. Use the observable runner with terminal progress when implemented, following repository docs. Charts need not be numerous if a compact table answers the question.

## Implementation and stop rules

Reuse the clean NB20 accounting/strategy harness, shared quote/redemption helpers, C00 score/regularised risk and NB21 causal D models. Add small NB22 helpers for entry/band ledgers, out-of-time calibration, veto application and reporting. Inspect `profitable_allocation.py`, `waterfall_comparison.py` and `portfolio_snapshot_construction.py` as well as the obvious NB20/NB21 modules. Do not fix unrelated NB21 sensitivities or edit existing notebooks as an incidental project.

Cache identities include all feature/label observations, maturity/support calendars, monthly fits, calibration inputs and policy-specific histories; a code hash alone is inadequate. No cached MARGIN uncertainty is used. If underlying D calibration inputs changed, regenerate its causal forecasts for this plan and document the difference; do not silently treat the changed head as frozen.

Stop if unchanged-input C00/source parity fails; if only pooled D/no identified relative signal exists; if causal validation/activation is absent; if the declared **pre-2026** mark-only scenario reverses its qualification lead; or if2026 activation is zero. Unbounded unknown upside is disclosed through break-even analysis, not falsely certified away. Complete the notebook's existing stages and explain the stop. Do not hide a stopped stage behind successful-looking empty charts. No additional thresholds/models/seeds are introduced after outcomes.

Generated outputs, logs, ledgers and reviews belong in ignored `_artifacts-restored-2026-10-07/22/` and `22-plan-review/`. Notebook/helpers/findings/summary notes remain reviewable outside generated directories. The planning task ends with this reviewed document; notebook implementation is a separate task.

## Claude contribution and unresolved limitations

The first CLI contribution used exact `claude-opus-5-5`, high effort, read-only tools. It inspected the draft, audit and relevant strategy/helper code. Its main accepted contributions: reduce the repetitive factorial; ledger-first headroom; broaden only to the existing rank-8 boundary; distinguish levels/ordering; whole-ticket controls; horizon alignment; and explicit missing-risk/score-tie mechanism logs.

We corrected four proposed details: frozen-ledger losses are not a portfolio upper bound; FIFO is not the engine's fee basis; β must not be capped at1 if compression is a hypothesis; random-veto rates cannot use future O1 frequency. A zero-containing interval is inconclusive rather than automatic proof the approach cannot help. The focused second review returned “approve with bounded revisions”. Its eight concrete rule gaps are addressed here: positive-level/variation actionability; correctly signed unknown-outcome scenarios; explicit relative-D support and managed-spell qualification; matched training centring; dollar-weighted horizon alignment; source-equivalent state and pre-veto parity; out-of-band prediction/pass-through; and per-dollar placebo qualification. The mark-only scenario remains a scenario, not a universal adverse bound. Details are recorded in `22-c00-entry-margin-review.md`.

Still unidentifiable: untraded candidates' source-managed spell outcomes; exact selective account attribution when feedback changes exposure; economic NAV/fees/permission truth and disappeared outcomes; independent generalisation; and the full current-accounting factorial unless its appendix executes. No successful result is presumed.
