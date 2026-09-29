# Grok review of rolling typical profitability plan

Requested Grok CLI model: `grok-4.6`; reasoning effort: `xhigh`. Review of the pre-revision draft and ten embedded prior notebook excerpts, not a full code audit.

I'll read the remaining plan excerpt first, then write the review from the supplied material only.**Verdict: revise.** The diagnostic is worth running and is not another search grid, but as written it cannot answer its own incremental question. Residualisation omits profitable-window frequency and mishandles Sharpe; mixed-span simple returns make the median incomparable to ordinary growth; formation and label edges are not pinned tightly enough to guarantee T−1 alignment. Those are specification defects, not missing data. After the small fixes below, implement. Do not add gates, new series, or a portfolio arm.

## What already matches the brief

The objective is a vault-level test of typical rolling-return magnitude, not a 20% CAGR proof and not an incumbent-beating contest (`Objective and scope`, `Interpretation and stopping`). Young and weekly vaults stay in; missing features are coverage, not rejection; ranks are not rewritten after label masking (`Frozen data` 3–4, `Forward outcomes`, `Analysis` 1). Drawdown is a separate conditional diagnostic, not a new underwater grid. All four `(h,W)` pairs are pre-declared. Stopping rules (redundant / risk-only / incremental / inconclusive) avoid NB28-style unpassable conjunctions. Follow-up, if any, is a later matched ranking backtest, not this notebook.

## Prioritised findings

**1. Residualisation does not test the stated objective (`Objective and scope`, `Analysis` 3).**\
The question is information beyond ordinary return, profitable-window share, Sharpe and volatility. The OLS residualises M/Q ranks only on G and V. P is built from the same unique nominal-h intervals as M/Q; leaving it out lets a restated positive-window score look “incremental.” S is approximately a function of G and V, so putting S in the same design as G and V is rank-deficient by construction, but omitting P still leaves the objective unanswered. A/D are residualised on G, V and M, which does not answer “drawdown given profitability and risk” without M in the way.

**2. Mixed-span simple returns confound M/Q with interval length (`Features and exact timing`).**\
Nominal-h returns allow ±7-day carry, distinct marks, and positive elapsed time. A “7-day” simple return can be ~1–14 days. G is already log growth per elapsed day; M/Q are medians of unscaled `P_end/P_start−1`. On weekly vaults that comparison is magnitude-plus-span, not typical holding-period return. Deduplicating `(start_mark, end_mark)` stops double-counting the same carried pair; it does not put returns on a common horizon. The plan correctly refuses to annualise short intervals; it still needs a per-day (or per-h) log return before the median, with raw simple returns kept for examples.

**3. Median does not reliably suppress lucky jumps (`Features and exact timing`, last paragraph).**\
The synthetic jump-and-flat path is necessary and should stay. Overlap, not the median, is the issue. For dense data, a mid-window jump sits inside about `h` of ~`W−h` intervals: ~30% at `(7,30)`, ~80% at `(14,30)`. When more than half the unique pairs contain the jump, the median *is* the jump. Weekly `(7,30)` is only a handful of consecutive week returns (close to IC NB19’s median week). Q diverges from M only with enough distinct outcomes; n=1 or n=2 makes Q=M. Treat `(h,W)` robustness partly as an overlap test; tag the one-outcome cohort; do not describe M as jump-robust.

**4. Time alignment is almost right, but window edges are underspecified (`Frozen data` 2, `Features and exact timing`, `Forward outcomes`).**\
Strictly before UTC midnight T, no future interpolation, seven-day carry, stored mark timestamps, and the T−1 mutation test are the right skeleton (same spirit as NB28’s `(T, T+H]` from the mark carried at T). Pin three edges: (a) T is UTC midnight exclusive, so the last mark of calendar day T−1 is usable and a mark at or after T is not; (b) formation endpoints s lie in a stated interval such as `(T−W, T)`; (c) the label start mark *is* the last formation-eligible mark, so the forward interval does not overlap the windows that produced M. Independent “last mark known at T” versus “last mark in W” can otherwise diverge. Drawdown integration “through T−1” must use the same exclusive boundary.

**5. Quintiles and residual ranks must not become a coverage filter (`Frozen data` 4, `Forward outcomes`, `Analysis` 2–3).**\
Keeping rows before the label mask is correct (NB24). State explicitly: percentile ranks and fractional top-quintile weights are computed on the contemporaneous opportunity set with available *features*; missing forward labels are dropped only when scoring outcomes; coverage is reported for top versus rest. Average ranks for ties in Spearman/OLS; fractional membership for the quintile cut. Address tie-breaks are not allowed. If one score saturates the cross-section, the quintile contrast is uninformative and maps to **Inconclusive**, not to a lead.

**6. Paired inference is declared but not named (`Analysis` 2, 4–5).**\
Date-equal weights, date-block bootstrap with vaults kept together, a non-overlapping H-phase (untuned), block counts, and leave-one-vault sensitivity are enough for a descriptive diagnostic. Do not add family-wise tests, two-way clustering, or extra phases. Pre-declare the paired statistics on matched complete rows: Spearman(M, y)−Spearman(G, y), M−P, M−S, and the same for top-quintile mean return and path drawdown. A date-cluster interval is not independent confirmation; the plan already says that.

**7. Sparse and young coverage can answer the question if interpreted as coverage, not as invented M (`Features`, `Analysis` 1, 4).**\
No median before h days; provisional available-history growth is not M; one-outcome rows are labelled; no minimum-count admission. Keep that. H=30 on weekly marks is a few observations (NB39 used 60d for that reason). Do not swap the primary horizon. If sparse H=30 is mostly missing or one-mark paths, say **Inconclusive** for that cohort and read H=60 / dense-only as the sensitivity they already are.

## Duplication

This is adjacent to prior work, not a repeat grid, if P, S and G stay comparators and no hard screen or floor-then-calmness portfolio appears.

- **P vs NB09 / NB28 / IC NB11:** positive-window frequency is an existing comparator. NB09’s consistency leg failed on return (excerpt: `positive_window_share` 24.33% CAGR vs anchor 37.90%). NB28 found it predicts forward vol/downside (excerpt ICs ~0.43/0.41); the old gate-5 failure is not absence of information. Rediscovering that P is risk-persistent is **Risk-only**, not a new lead.
- **M vs IC NB19/20:** median week / worst week / drawdown *described* StratWise; 0/12 full-period Sharpe screens improved. Example charts are not evidence. h=7 M on weekly marks *is* median week. The new work is residualised magnitude versus G/P/S/V, not another name-fitted exclusion.
- **M vs NB39:** trimming best events did not beat raw scores; trailing Sharpe still associated with forward Sharpe, with few independent blocks. Median-of-windows is another robust location statistic. Do not reopen a trim search.
- **A/D vs NB90 / NB07 / NB78:** underwater geometry and inverse-downside sizing already failed as allocation ideas. Flawless upward-only paths fooled Sharpe (NB78 excerpt: ~1.1% down-day share, zero downside deviation). High M/P/S will look the same if overlapping windows all contain the ratchet. Joint forward return *and* path DD is the check; do not treat high M as steadiness.
- **IC NB25–29 / NB32:** raw rolling growth and return-floor+stability ranking already failed as portfolios. This notebook must not complete those missing arms or launch a new grid. Reuse the frozen NB25 snapshot/controls only.

Cross-experiment return leaderboards remain invalid (`Prior evidence` table).

## Minimal concrete fixes

1. **Primary residualisation (`Analysis` 3):** M (and Q) on `[1, G rank, V rank, P rank]`. Never G+V+S together. Report rank correlations of M/Q with G, P, S, −V (already intended). Optional second residual: M on S alone. For drawdown, residualise −A/−D on G, V, P first; add M only as a second view. n<10 or rank-deficient → unavailable, with excluded-young coverage.
2. **Define M/Q on log return per actual elapsed day** (or scaled to h), still unannualised. Store raw simple returns, actual spans, unique-pair counts. Keep the dense-only sensitivity.
3. **Pin timing:** T = UTC midnight exclusive; s ∈ `(T−W, T)`; both marks ≤7 days stale vs requested bounds; label start = last formation mark; label end = last mark ≤ T+H with the same carry; A/D stop before T. Mutation test unchanged.
4. **Ranks before labels; average ranks; fractional quintiles.** Pre-declare matched M−G, M−P, M−S contrasts for Spearman and top-quintile return/DD.
5. **Report when Q=M** (n<4 or heavy ties) and when >50% of unique pairs contain the largest gain, so median-as-robustness is an empirical flag, not a claim.

No extra features, no helper framework, no new acceptance conjunction, no NAV provenance programme.

## Missing ideas (two)

1. **Jump-containment table:** on each vault-date, the share of unique nominal-h intervals that include the largest simple gain, plus the fraction of dates where that share ≥0.5. This answers “does the median avoid lucky jumps?” on the frozen panel, not only on the synthetic path.
2. **Joint quadrant counts** (not a utility): top-quintile versus rest, share with above-median forward return *and* below-median forward path DD, with coverage. That is the “profitable and steady” readout the stopping rule needs.

## Can this diagnostic answer the objective?

Yes, as a **descriptive ranking panel**, after the fixes: whether M/Q order future holding-period return and path drawdown beyond G, P, S and V, with honest young/sparse coverage. It cannot certify a ~20% CAGR strategy, beat the incumbent, or produce independent holdout skill on dates already used in NB09–NB39 and IC NB19–NB29. Limited or conflicting ICs are **Inconclusive** or **Redundant**, not a code failure. A completed notebook is not economic validation (`Deliverables and verification`).

**Do not implement until fixes 1–4 are in the spec.** Then proceed with one notebook, frozen NB25 inputs, and the four pre-declared settings.
