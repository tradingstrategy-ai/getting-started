# Rolling profit and risk notebook development plan

## Purpose and relationship to the earlier plan

Turn [rolling-profit-risk-plan-01.md](rolling-profit-risk-plan-01.md) into separate, executable research notebooks. This document is the implementation specification for the first wave; the older plan supplies motivation and deferred options. Do not implement its optional alternatives as additional first-wave runs.

Objective: high Sharpe, steady positive profit and reasonable CAGR around 20%, not beating hyper-ai. Use direct rolling price metrics. Young and weekly-observed vaults stay eligible; operational constraints still apply. StratWise and Systemic L/S Grids are explanatory examples, never names to select by construction. Blacklists remain off in primary comparisons. No new monthly/weekly gates, long-history admission barriers or concentration acceptance gates.

Status: design only. Notebooks have not been created or executed for this track. Proposed numbers 25–29 are free in the current folder; recheck before implementation.

## Experiment map

| Notebook | Single research question | Parent / inputs | Output consumed by |
|---|---|---|---|
| `25-research-rolling-metrics-controls.ipynb` | Can the intended feature and allocation path operate, and does the control reproduce? | Corrected NB24/NB23 engine and input snapshot | All later notebooks |
| `26-research-rolling-ranking-access.ipynb` | What do short-history ranking and short-history sizing each change? | NB25 panel/control; a four-arm factorial | NB27 and synthesis |
| `27-research-rolling-sizing.ipynb` | What happens when the same requested selections get different sizing? | A fixed NB26 candidate schedule | Synthesis; optional NB28 companion |
| `28-research-rolling-exposure.ipynb` | Can soft risk reduction improve exposure without hard exclusions? | NB25 original-policy control, independent of NB26 success | Synthesis |
| `29-research-rolling-track-synthesis.ipynb` | Which mechanisms survived, and what remains uncertain? | Saved artefacts from 25–28 | Track summary and one frozen follow-up |

This is a dependency chain, not five independent optimisation searches. NB28 can be developed once NB25 passes. NB27 uses a predeclared diagnostic parent, not whichever full-period result looks best. NB29 introduces no new parameters or winning formula.

## Anti-repetition register

Every notebook must include this ancestry in its first cell and state its actual change.

| Earlier experiment and result | What must not be repeated | What is different here |
|---|---|---|
| Lower-vol NB28/34: strong risk persistence; some old rejection gates later corrected | Another broad IC search to rediscover that volatility predicts volatility | NB25 checks coverage and behaviour, not a discovery gate |
| Lower-vol NB32: return floor + pure calmness ranking; 26/30 configurations negative | Renaming a calmness ranker as a new stable-profit idea | NB26 ranks growth and separates risk sizing in a factorial |
| Lower-vol NB38/39: trimming did not improve untrimmed scores; long-history Sharpe signal has limitations | Another best-day removal grid or a 180-day requirement for young vaults | Untrimmed, available-calendar-history features; no long-history admission |
| IC NB19/20: attractive example screens failed in broader portfolios and removed winners | Hard drawdown/weekly screens or a threshold fitted to the example names | NB28 changes requested exposure continuously, not eligibility |
| IC NB21/22: flexibility changed the sizing mechanism; original steady-selection interpretation withdrawn | Simultaneously relaxing number, weight and capacity limits | Limits remain fixed for attribution; unrestricted breadth is deferred |
| IC NB23/24: monthly aggregate risk blindness and saturated scores; corrected fees matter | Another monthly score calibration; treating access as profitable selection | No month buckets; actual funding and subsequent outcomes are reported |
| Waterfall NB69: sizing comparison already established material effects on the incumbent basket | Claiming generic inverse-volatility sizing is new | NB27 tests a different, fixed short-history selection schedule and only runs missing comparisons |
| Earlier IC accepted-dollar cap: cash-heavy and contributor-sensitive | Presenting no-refill as untested or a new source of selection skill | NB28 first establishes whether this exact corrected engine actually redistributes dollars; otherwise skip the duplicate/no-op |
| Waterfall cadence trials | Adding cadence variation to every candidate | Cadence is frozen; follow-up only if new results identify a specific unresolved cost mechanism |

Before running a new arm, search existing manifests for the same inputs, engine, universe, dates and policy. Reuse identical validated results. If an older result has different accounting/universe, label the new run a corrected reproduction or transport test, not a new hypothesis. Include `prior_experiment`, `mechanism_delta`, `why_not_duplicate` in each arm manifest.

## Shared development contract

Create small shared modules next to the notebooks: `rolling_track_features.py`, `rolling_track_simulation.py`, `rolling_track_reporting.py`. Reuse existing loaders and fee-correct simulation functions where possible. No generic framework, new dependencies, optimizer or copied engine per notebook. A shared configuration record holds named arms. Notebooks explain experiments and render tables/charts; modules hold reusable arithmetic.

Artefacts: `_artifacts-rolling-profit-risk/{manifest.json,inputs,nb25,nb26,nb27,nb28,nb29}`. Store input fingerprints/references rather than unnecessary copies of large data. Record source hashes and environment versions. Do not invalidate caches merely because documentation changed; feature/engine/data changes do invalidate affected outputs.

Use the corrected NB24 engine control and the same frozen inputs. Record the current `hyper-ai.py` source hash and differences, but do not silently change the baseline to match a newer production file. A0b remains an independent optional reference. Preserve the existing single-redemption-fee correction. Never import old A0 or pre-fix fee figures into a new comparison table.

Primary common windows: 13 September 2025–8 September 2026 (full), 1 January–8 July 2026 (hyper-ai). Preserve native starts so slicing is not confused with cold starting. The hyper-ai comparison is its separately initialised January run, not a January–July slice of the August-start full simulation. Those portfolios have different holdings, cash and fee bases; report any optional ongoing-portfolio slice separately. Also run 1 April–8 September 2026 as a later cold start. These overlap and are not three independent confirmations. The history is reused, so none is a pristine holdout.

Daily features use strictly earlier observations; keep the parent's trade cadence, return gate, exits, historical capacity, six-name limit and 33% weight cap fixed for paired attribution. These caps are diagnostic controls, not the intended final portfolio requirements. Local name blacklists off; operational availability unchanged. Keep shared cash/fee conventions. No new TVL or social predictive factors.

Use British English, naive UTC, `poetry run python`, and the repository observable notebook runner. Read notebook-execution.md and the create-variant skill at implementation. Each notebook heading names its parent, then receives its own findings after execution. Do not copy parent results into a new heading.

## Feature and missing-history specification

Primary lookback 30 calendar days; 14/60 are separate sensitivity runs. Forecast diagnostics use subsequent 14/30/60 days. No completed months/weeks are required.

Let `r_i=log(P_i/P_{i-1})`, `dt_i` be actual elapsed days and `T=sum(dt_i)`:

- Growth `g=sum(r_i)/T` (per day). Ranking by annualised `365*g` is identical; do not compare them as two strategies.
- Interval risk `v=sqrt(365*sum((r_i-g*dt_i)^2)/T)`.
- Downside `d=sqrt(365*sum(min(r_i,0)^2)/T)`.
- Drawdown `D=max(1-P_i/running_max(P))` on the available observed path.
- Trend slope/residual dispersion are plots only, not extra rankers.

Retain one last available observation per UTC day for the primary calculation. Include an available boundary observation before the nominal window and report the actual span; never fabricate a boundary price. Use shorter available history for young vaults. A single return interval gives growth, but `v` is underdetermined and must be missing rather than algebraically zero. This is mathematical availability, not a vault admission condition. No prior observation means no price-derived signal is possible.

Risk from irregular intervals is an approximation. Report counts/spans, sparse/dense cohorts and seven-day sampling sensitivity; do not treat carried daily prices as independent observations of low risk. Valuation still forward fills. Fixed 5% annualised volatility floor limits inverse weights, with its binding rate reported; it is not a learned threshold or safety claim.

For new sizing, finite raw weight is `1/max(v,0.05)^k` with k=1 or 2. Missing risk receives the median finite raw weight in the selected set; if all are missing, equal raw weights. Apply existing capacity/normalisation afterwards. Label fallback allocations. No zero-risk imputation, automatic young-vault rejection or hidden fallback from future data.

## NB25 — rolling metrics and controls

Development cells: purpose/ancestry → configuration/hashes → input loading → feature definitions → coverage tables → original engine replay → ledger checks → historical example charts → reusable outputs.

Required checks: prefix-invariance when future prices are appended; irregular weekly intervals; a two-price young history; identical prices and the risk floor; missing forecast endpoints; partial/full redemption accounting; exact control equity/date-index reproduction within the recorded tolerance. Use independent scalar calculations for a few cases, not tests that copy vectorised code.

Save daily feature panel, source/method manifest, operational candidate schedule and the full decision ledger: score, candidate rank, selected state, raw weight, requested dollars, cap reductions, accepted target and executed position. Reproduce two saved NB24 control periods, and calculate the later cold-start control once.

Coverage audit must identify whether the inherited return gate blocks young histories before sizing. If it does, retain the exact legacy replay and add a separately named common young-compatible gate for the factorial: same threshold, available-history return when the full lookback is missing, no other change. Apply it to all four factorial arms and reproduce its own original/original control. Never fix only the preferred candidate. Freeze this decision before NB26. Name the exact legacy controls `LEGACY_full`, `LEGACY_hyper_ai`, `LEGACY_later`. If the common gate changes, all four B arms use it and B00 is a NEW control: three additional B00 runs, not reuse of LEGACY. If the gate does not change, reuse LEGACY as B00. Do not also run a second four-arm factorial. Preserve the legacy −16% threshold; do not substitute NB24’s positive-return diagnostic gate.

Do not launch a new IC grid. Small forward-outcome tables and StratWise/L/S Grids/ATM examples explain behaviour only; future labels do not define eligibility or ranking.

## NB26 — ranking and access factorial

Four predeclared arms:

| Arm | Ranking | Sizing |
|---|---|---|
| B00 | Original composite | Original 90-day inverse variance |
| B10 | Available-history growth | Original sizing |
| B01 | Original composite | 30-day/available interval inverse variance |
| B11 | Available-history growth | 30-day/available interval inverse variance |

All other settings identical, including whichever common gate NB25 established. Preserve original score-missing semantics in original-ranking arms. Growth arms rank finite `g` descending; retain the common gate rather than adding an undeclared positive-growth gate. Report the number of negative-growth selections if any. Use the original deterministic tie-break, descending score then pair ID, across arms. This experiment isolates a rank change, not a combined rank/admission change.

Compare B10−B00 and B11−B01 for ranking, B01−B00 and B11−B10 for sizing, then show interaction. Call the sizing factor a **sizing-path change**: it bundles interval versus carried-price estimation, lookback, floor and missing-risk fallback. This factorial does not identify their individual effects. B01 retains original missing-SCORE semantics but uses NEW risk sizing; only B00/B10 keep original missing-volatility semantics. A zero young weight under old sizing is an allocation limitation, not a negative return observation.

Save all requested candidate-membership schedules before sizing, plus every candidate's actual funding and forward outcomes. Run the primary factorial on the three windows, reusing NB25 controls when identical. Maximum 9 incremental runs when B00 is reusable; a distinct common-gate control may add at most 3. Do not run 14/60 here yet.

## NB27 — sizing the requested selections

Use **B11’s 30-day ranking schedule by declaration**, whether it wins or loses. This is a diagnostic parent, not a full-history-selected winner. Existing B11 inverse-variance output is reusable only if schedule replay matches its original live requested membership exactly.

Compare equal raw weights, inverse volatility (k=1) and inverse variance (k=2), with identical requested membership and common 5% risk floor/fallback semantics. No score-proportional variant or new gate. A stored membership schedule may use only causal decisions; do not carry parent dollar holdings or future state into siblings. Each simulation maintains its own cash, costs and trades.

The B11 schedule is a causal **parent-policy intervention**, not a state-independent ranking snapshot: its membership can reflect that parent’s earlier fills and holding protections. State this limitation and also save the stateless eligible ranking each date. Actual held positions may diverge due to minimum trades, lockups or fills. Quantify divergence. If replay cannot reproduce the parent exactly, resolve the cause before interpreting sizing effects, or explicitly report a desired-membership diagnostic rather than claim fixed actual holdings.

Two new sizers × three windows = at most 6 incremental primary runs when B11 replay is reusable. If not, document why a separate replay control is necessary. Report exact overlap with the original requested selection schedule. If the schedules are identical, relabel this as a corrected transport of NB69 rather than a new short-history basket test and check for reusable matched results. Near-equality alone is not proof of equivalence: a few changed selections can drive outcomes. Do not pick an arbitrary Jaccard threshold after seeing profits.

## NB28 — separate exposure experiments

Primary parent is the reproduced original-policy engine control, declared before results. Do not choose the best NB26/NB27 result. A companion on B11 is deferred until synthesis identifies a reason.

E0: parent. E1: no refill after operational/capacity clipping. E2: first compute the parent allocator’s accepted target dollars using this simulation’s own pre-trade state; then apply `target_i *= exp(-D_i/0.10)` with released capital left in cash. This preserves the parent’s allocation/cap logic before the isolated risk haircut. Subsequent operational checks may reduce targets further, never refill them. Apply to desired target holdings, not as an extra forced-exit gate. Missing D means multiplier 1 with an explicit unknown flag. Keep E1 and E2 separate; do not combine them into a winning candidate. E2 must preserve reduced dollar targets through execution without normalising them back to the original invested budget. Record names retaining a slot with near-zero target dollars; this can reduce effective holdings without changing the nominal six selections.

E1 begins with a code/ledger check: name the exact redistribution step to remove. If the parent already leaves clipped dollars in cash, record no-op and skip its backtests. The reviewed allocator contains a concrete candidate redistribution step: `tradeexecutor/strategy/alpha_model.py`, `AlphaModel._normalise_weights_size_risk_positions`, recalculates weights on remaining names and subtracts accepted dollars from `equity_left`. Verify that this path is actually invoked by the frozen NB24 harness and quantify the changed dollars. E1 assigns each selected name its initial normalised share of the original budget, applies the same caps once and leaves residual cash; no later renormalisation may restore the released budget. Do not invent a different cap, remove initial normalisation or borrow historical A0-cap results as proof the current engine refills.

For each active E arm, add a causal uniform-scaling control of the parent's desired weights to that arm's pre-trade invested fraction. Express schedules as fractions, not hindsight absolute dollars from a different equity path. Compute treatment and scaling target using information known before the decision. Capacity/fill differences may prevent achieved cash equality: report the error and do not call it exactly cash-matched if it is not.

E2 + its scaling control × three windows = 6 new runs. E1 + control add 6 only if E1 has a real, previously untested effect on this exact parent. No threshold sweep. If loss reductions also remove profitable exposure, quantify both rather than declare a failed risk forecast.

## NB29 — synthesis, not another search

Read saved validated artefacts; do not resimulate every notebook for presentation. Produce:

- A lineage/results table identifying new tests versus corrected reproductions or no-ops.
- Same-date equity curves and CAGR, Sharpe, volatility, max drawdown, turnover, invested fraction, effective holdings and contributor shares.
- Selected-vault future return/risk versus whole-portfolio risk, with sampling/history cohorts and selection-before-label-masking coverage.
- StratWise/L/S Grids selection and actual-dollar timelines; historical losing cases for explanation, never success requirements.
- Separate ranking, sizing, cash, turnover and operational effects. Confidence claims must acknowledge overlapping daily labels and reused history.

Bounded robustness runs are predeclared, not selected by later-period Sharpe:

1. Repeat the B01/B11 paired ranking contrast with their new interval lookbacks changed together from 30 to 14 and 60 days. Original-composite ranking remains unchanged in B01. Two arms × two lookbacks × three windows = 12 runs. Skip only for documented implementation invalidity; do not suppress an unprofitable sensitivity.
2. Remove the full-period largest positive contributor of B11, by identity, and fully rerun that same B11 policy on both primary comparison windows. Two runs. Label this retrospective sensitivity, not a proposed blacklist or an unbiased estimate.
3. If a different mechanism is recommended, give it the same contributor-removal check before claiming robustness; explain any additional run count.

Do not optimise a combined score or choose a feature after inspecting later labels. It is acceptable to conclude that access works but loses, risk sizing helps without better selection, or nothing is promising. ~20% CAGR is the intended return region, not a compulsory threshold in every period. Lower risk need not predict higher return to be useful.

## Development and review sequence

For each notebook: write the minimal implementation → review code and causal/experiment contract → fix concrete errors → execute via `TQDM_LOGGABLE_FORCE=stdout poetry run jupyter-execute-agent <path> --timeout=3600` → inspect saved outputs and ledger invariants → independently review result interpretation → fix/rerun only affected notebooks → update that notebook's own heading and summary. Use Grok CLI 4.6 for independent reviews unless the user specifies otherwise; provide source, parent differences, relevant failed attempts and actual outputs. Validate a completed terminal event; never treat cancellation as approval.

Reviews must focus on code correctness and whether the experiment actually tests its declared change. Reject advice that reintroduces forbidden factors, mandatory long histories, fit-to-name rules or beat-incumbent gates. Record disposition rather than silently applying every suggestion. No notebook run is authorised by this planning document alone; implementation follows the user's next instruction.

Shared changes rerun affected consumers: feature semantics → 25 and downstream arms; execution/fees → all affected controls and comparisons; one arm's sizing → its own runs and synthesis; presentation only → reporting cells. Hash dependencies and never compare old/new source results in the same table without disclosure.

First-wave primary budget: 3 control runs, up to 9 factorial additions, 6 sizing additions and 6 soft-exposure additions = **24 unique runs**, plus up to 6 no-refill and up to 3 common-gate controls. Synthesis adds 14 predeclared sensitivity runs. Cache/reuse validated identical runs; do not pad counts with duplicate controls. If membership replay needs an extra control, revise the manifest before execution. No optimizer sweep.

Deliverables: five executed notebooks, shared modules, manifests, metric/selection/position tables, standalone equity charts, per-notebook reviews/dispositions and `rolling-profit-risk-track-summary-01.md`. A short track index points to each notebook and states what has actually run.

## Plan review

Completed with Grok CLI 4.6 on 17 September 2026. The historical packet supplied the relevant earlier notebook narratives/results, previous synthesis and author disposition; Grok also inspected current strategy and allocator source. The first run read the packet but reached its turn limit before answering. A resumed response in the same context completed with `end_turn`, actual backend `grok-4.6-build`.

Read [the review](grok-46-notebook-development-review-01.md) and [accepted/rejected feedback](grok-46-notebook-development-disposition-01.md). Original draft, exact supplied source list, prompts, raw investigation/completion logs and validation are in `_review/rolling-track-plan-02/`. The final author corrections were not submitted for another review. No notebook has been created or executed by this planning task.
