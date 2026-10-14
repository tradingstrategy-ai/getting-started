# Hyperliquid vault strategy research, NB01–NB23

This research develops C00 from the deployed Hyper-AI rules and records the unsuccessful alternatives as well as the leads. It covers ranking, feature forecasting, position sizing, risk estimation, allocation constraints, residual cash and execution accounting.

The strongest retained benchmark is **C00**: four-input performance ranking, regularised 90-day risk and a capacity waterfall, with six positions. Under the latest common accounting, its 2026 replay returns **58.59% CAGR / 2.474 Sharpe / −6.36% drawdown**, versus **49.15% / 2.214 / −6.41%** for v11. Full-history C00 is **33.13% / 1.651 / −9.94%**, versus **18.55% / 1.374 / −7.92%** for v11. These are historical results on inspected, overlapping periods.

## Reading the tables

- **S:** 1 January–4 October 2026 inclusive, `[2026-01-01, 2026-10-05)` UTC.
- **L0:** 1 March 2023–4 October 2026 inclusive, the original full-history period.
- **L:** 1 March 2023–7 October 2026 inclusive, `[2023-03-01, 2026-10-08)`; final archive day partial.
- In a row marked **S / L** or **S / L0**, each metric lists the corresponding short / long result in that order. The experiment overview shows one explicitly named representative per notebook, usually its 2026 result; it is not a table of independent winners.
- **—** means no applicable portfolio CAGR/Sharpe or no headline reported here. Forecast IC, overlapping fixed-unit snapshot returns and hypothetical fixed-ledger sensitivities are not executable strategy metrics.
- Portfolio accounts start with USD 150,000. All preceding indicator history is retained, including 2025 warmup for fresh 2026 accounts. Long accounts carry their own holdings and accumulated profits into 2026.

Results come from the executed notebooks and their exact saved generations, rather than older prose in dated appendices. Accounting evolves across the research: NB01–13 retain the legacy convention; NB14–17 introduce as-of-observation NAV, with the inherited partial-sale treatment; NB18 corrects partial-sale fees; NB19–23 also reset stale entry tax and share final-proceeds funding. Early NB19 historical controls are displayed separately. **Compare methods with the matched control inside their notebook.** The v11 change from 41.20% to 49.15% in later controls is an accounting difference, not evidence that a new scoring method improved v11. The fee-sensitive NB17 exit-delay lead reverses after correction.

## Experiment overview

One row per main notebook. The description identifies the configuration supplying the displayed metrics; complete method coverage follows below.

| ID | Experiment link | Description | Backtesting period | CAGR | Sharpe | Maximum drawdown |
| --- | --- | --- | --- | ---: | ---: | ---: |
| NB01 | [Notebook][nb01] | Source v11 replication: 60/40 CAGR360–Sortino45, six slots, 90-day inverse variance. Exact control for the first research phase. | S; L0 also run | 41.20% | 1.960 | −6.40% |
| NB02 | [Notebook][nb02] | Accepted-dollar cap prevents redistribution above initial requests. Representative capped arm leaves much more cash. | S; L0 also run | 9.31% | 1.310 | −4.22% |
| NB03 | [Notebook][nb03] | Equal, inverse-volatility/equal blend, regularised inverse volatility and correlation risk budgets, under both allocators. Headline: correlation-aware parent. | S; L0 also run | 35.52% | 1.620 | −7.84% |
| NB04 | [Notebook][nb04] | Sparse metric/window matrices; clipping, missingness, blend, breadth and sizing searches. Headline: six-slot 50/50 clipping blend. | S; L0 also run | 41.38% | 2.119 | −4.85% |
| NB05 | [Notebook][nb05] | Hard/smooth clipping, feasible entries, replacement hurdles, tie order and cash refill. Headline: feasible-entry selector. | S; L0 confirmations | 41.83% | 1.99 | −6.39% |
| NB06 | [Notebook][nb06] | 74 fixed two/three/four-input score recipes. Headline: 48/32/10/10 CAGR360–Sortino45–CAGR180–Sortino30. | S; L0 also run | 51.77% | 2.303 | −6.35% |
| NB07 | [Notebook][nb07] | Repeat 74 scores with 6/7/8/10 positions and N/(N+2) entry/exit ranks. Headline: seven-slot Blend46d Sharpe lead. | S; L0 also run | 47.93% | 2.459 | −4.71% |
| NB08 | [Notebook][nb08] | 139 score forecasts; 7/30/90-day labels, learned absolute floors, percentile floors and random vetoes. Headline: unchanged focal six-slot account; learned floors veto no entries. | S; L0 portfolio checks | 51.77% | 2.303 | −6.35% |
| NB09 | [Notebook][nb09] | Individual feature forecasting plus six K-ratio windows, including max history; missing=True and sparse-data repairs. No portfolio backtest. | S; 7/30/90-day targets | — | — | — |
| NB10 | [Notebook][nb10] | Original matched allocation snapshots and expanded 36-arm smoke: risk/K inside ranking or sizing scores, five maps, breadth, covariance and missingness. | S; original 7/30/90d, smoke 30d | — | — | — |
| NB11 | [Notebook][nb11] | 40 fixed-basket sizing policies: 45/90/180-day risk, powers, shrinkage, multi-window and sparse observation models. No trading-engine account. | S; 7/30/90-day snapshots | — | — | — |
| NB12 | [Notebook][nb12] | 12 local sensitivities, eight constrained risk-budget policies and 16 engine replays. Headline: focal gap-log 90-day variance. | S | 47.46% | 2.123 | −7.10% |
| NB13 | [Notebook][nb13] | Ten frozen 2026 leaders plus two controls over full history. Headline: gap-log allocation CAGR leader; focal four-input score leads Sharpe. | L | 27.44% | 1.505 | −10.24% |
| NB14 | [Notebook][nb14] | Factorial source/regularised variance × sequential/simultaneous allocation plus downside sizing. Headline: four-input source-risk A. | S; L also run | 51.77% | 2.304 | −6.35% |
| NB15 | [Notebook][nb15] | A/C/G versus source v11 on matched accounts; investigate September cash and selected-basket capacity. Headline: A. | S; L also run | 51.77% | 2.304 | −6.35% |
| NB16 | [Notebook][nb16] | Risk-priority waterfall for v11/A/C/G. Headline: G-W fresh-2026 leader; C-W is the stronger full-history challenger. | S; L also run | 56.19% | 2.456 | −6.81% |
| NB17 | [Notebook][nb17] | 14 capacity, retention, overflow and optimisation policies, with partial-fee sensitivities. Headline: M05 full-history primary profit leader, before fee correction. | L; S also run | 35.30% | 1.648 | −12.12% |
| NB18 | [Notebook][nb18] | Protected core with risk-limited extra positions, pooled/score gates, gradual exposure and economic exits. Headline: corrected-fee C00 control. | S; L also run | 58.58% | 2.492 | −6.09% |
| NB19 | [Notebook][nb19] | Exact C00 core plus absolute flat/risk/score/combined tickets, hold versus resize and slot/cap sensitivities. Headline: RS01. | S; L also run | 58.84% | 2.475 | −6.45% |
| NB20 | [Notebook][nb20] | Clean C00/v11 comparison with partial-sale correction, entry-tax reset and final-proceeds funding. Headline: C00. | S; L also run | 58.59% | 2.474 | −6.36% |
| NB21 | [Notebook][nb21] | Forecast-driven marginal net-profit allocation, including conditional losses/magnitudes, loss budgets and ablations. Headline: calibrated-score adaptive arm C01. | S; L shortlist | 11.28% | 1.654 | −1.90% |
| NB22 | [Notebook][nb22] | Managed entry attribution and local forecast calibration. Seven-day horizon registered; pre-2026 economic gate failed, so overlay accounts were skipped. | Pre-2026 qualification; S diagnostics; no overlay backtest | — | — | — |
| NB23 | [Notebook][nb23] | C00 in NB160 reporting layout plus separate source v11 comparison. Four fresh accounts reproduce NB20 equity, trades and metrics. | S; L also run | 58.59% | 2.474 | −6.36% |

## Methods and combinations tried

This table covers the executed method families and named engine treatments. NB10 lists all 36 smoke combinations; NB11 groups its 40 neighbouring parameter policies. Grid coefficients and sensitivity cells remain in their notebooks. The 334-policy NB10 expansion and generalisation across all 139 recipes were registered but **not executed**. They are not counted as results. In NB10 notation, A/G/Min are arithmetic/geometric/minimum aggregations; F/L/B are focal four-input/v11/Blend46d; I/V are inverse-variance/inverse-volatility scores; C/Sh/So/Ca/D/K are CAGR/Sharpe/Sortino/Calmar/drawdown/K components. Missingness codes and constraint projections are defined in the notebook.

| ID | Experiment link | Description | Backtesting period | CAGR | Sharpe | Maximum drawdown |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 01/v11 | [NB01][nb01] | Source inverse variance | S / L0 | 41.20% / 15.77% | 1.960 / 1.238 | -6.40% / -7.92% |
| 02/cap | [NB02][nb02] | Source inverse variance + accepted-dollar cap | S / L0 | 9.31% / 2.08% | 1.310 / 0.355 | -4.22% / -7.92% |
| 03/P1 | [NB03][nb03] | 50/50 inverse volatility plus equal, source redistribution | S / L0 | 34.28% / 14.23% | 1.485 / 1.067 | -9.11% / -8.87% |
| 03/P1-cap | [NB03][nb03] | 50/50 inverse volatility plus equal, accepted-dollar cap | S / L0 | 24.93% / 10.39% | 1.489 / 1.012 | -8.17% / -8.01% |
| 03/P2 | [NB03][nb03] | Equal weights, source redistribution | S / L0 | 35.01% / 13.57% | 1.443 / 0.990 | -9.53% / -11.22% |
| 03/P2-cap | [NB03][nb03] | Equal weights, accepted-dollar cap | S / L0 | 30.10% / 11.49% | 1.509 / 0.977 | -9.35% / -9.29% |
| 03/P3 | [NB03][nb03] | Regularised inverse volatility, source redistribution | S / L0 | 35.43% / 14.98% | 1.606 / 1.140 | -7.69% / -7.92% |
| 03/P3-cap | [NB03][nb03] | Regularised inverse volatility, accepted-dollar cap | S / L0 | 17.40% / 8.23% | 1.278 / 0.943 | -6.68% / -7.92% |
| 03/P4 | [NB03][nb03] | Correlation-aware equal risk budgets, source redistribution | S / L0 | 35.52% / 14.24% | 1.620 / 1.081 | -7.84% / -7.92% |
| 03/P4-cap | [NB03][nb03] | Correlation-aware equal risk budgets, accepted-dollar cap | S / L0 | 19.30% / 8.06% | 1.387 / 0.911 | -6.71% / -7.92% |
| 04/matrix | [NB04][nb04] | Sparse CAGR/Sharpe/Sortino/drawdown/Calmar × 30/46/60/90/120/180/270/360/730d; separate CAGR/Sharpe fits, 50/50 and 60/40 score blends, 4/6/10 slots; equal, score-proportional and source variance sizing. No universal winning family. | S; L0 | — | — | — |
| 04/blend46 | [NB04][nb04] | Named two-input 60/40 CAGR360–Sortino46 recipe with 50/50 clipping-profile blend and source variance sizing. | S / L0 | 41.38% / 15.42% | 2.119 / 1.24 | −4.85% / −8.51% |
| 05/calibration-grid | [NB05][nb05] | 18 calibrations: hard CAGR clips 0.5/1/2 and Sortino 3/7/12, blended 45/46-day profiles, smooth saturation, ratio floors, missing-zero and an activity filter. | S; selected L0 confirmations | — | — | — |
| 05/ties | [NB05][nb05] | Five seeded tie-order controls, seeds 11/23/37/53/71, isolate sensitivity caused by clipping ties without selecting a new score. | S | — | — | — |
| 05/feasible | [NB05][nb05] | Reject deposit-infeasible entrants before incumbent replacement. | S / L0 | 41.83% / 15.87% | 1.99 / 1.25 | −6.39% / −7.92% |
| 05/hurdle | [NB05][nb05] | Replacement improvement thresholds 0, 0.025 and 0.05, with fee/tie diagnostics; 0.05 representative. | S | 41.78% | 1.99 | −6.40% |
| 05/smooth | [NB05][nb05] | Smooth C1/S3 score transformation, compared with hard clips and clipping blends. | S | 31.64% | 1.65 | −5.28% |
| 05/refill | [NB05][nb05] | Residual cash refill after admission checks; source-score representative. | S | 39.56% | 1.88 | −6.44% |
| 05/activity | [NB05][nb05] | Require ten non-flat returns; explicitly tests an activity filter rather than treating flat marks as invalid. | S | 27.39% | 1.31 | −6.75% |
| 06/three | [NB06][nb06] | 36 three-input 48/32/20 recipes with extra metric/window inputs and matched-weight controls. Highest inspected 2026 CAGR representative. | S; L0 | 51.99% | 2.29 | −7.29% |
| 06/four | [NB06][nb06] | 36 four-input 48/32/10/10 recipes; named focal uses CAGR180 and Sortino30 additions. | S / L0 | 51.77% / 22.05% | 2.303 / 1.622 | −6.35% / −8.08% |
| 06/four-peak | [NB06][nb06] | Highest-CAGR four-input support adds Sortino180 and CAGR60 to the 48/32 core; it has worse drawdown than the focal candidate. | S; L0 | 52.30% | 2.23 | −7.62% |
| 06/collapsed | [NB06][nb06] | Collapse added windows into a two-input 58/42 score, preserving total metric weights. | S / L0 | 41.89% / 15.85% | 1.99 / 1.24 | — |
| 07/N7 | [NB07][nb07] | Focal four-input recipe at seven slots; entry rank 7, exit rank 9. | S / L0 | 30.85% / 17.30% | 1.582 / 1.26 | −6.42% / −9.99% |
| 07/N8 | [NB07][nb07] | Same focal recipe at eight slots; entry rank 8, exit rank 10. | S / L0 | 16.24% / 14.88% | 1.04 / 1.12 | −6.57% / −11.91% |
| 07/N10 | [NB07][nb07] | Same focal recipe at ten slots; entry rank 10, exit rank 12. | S / L0 | −3.01% / 8.49% | −0.28 / 0.70 | −6.79% / −17.42% |
| 07/blend7 | [NB07][nb07] | Blend46d at seven slots: separate higher-Sharpe candidate. | S / L0 | 47.93% / 18.40% | 2.459 / 1.395 | −4.71% / −8.08% |
| 08/forecasts | [NB08][nb08] | 139 scores; monthly absolute calibration and rank IC at 7/30/90d, quarter-coloured scatters, trend/threshold, market residual and cohort diagnostics. | S; 7/30/90d targets | — | — | — |
| 08/absolute | [NB08][nb08] | Monthly positive-return floors, with rejected slots held as cash or redistributed within caps. Focal six-slot rule changes no entries. | S / L0 | 51.77% / 22.05% | 2.303 / 1.622 | −6.35% / −8.08% |
| 08/percentile | [NB08][nb08] | 75th-percentile entry floors plus matched random vetoes; v11 six-slot representative has no 2026 effect. | S / L0 | 41.20% / 16.24% | 1.960 / 1.266 | −6.40% / −7.92% |
| 08/missing | [NB08][nb08] | Reject unscored fresh entries; v11 six-slot representative. Sparse/missing scores remain a separate category. | S / L0 | 41.20% / 11.11% | 1.960 / 0.971 | −6.40% / −6.39% |
| 08/cash-yield | [NB08][nb08] | 3%/5% cash-yield overlays on fixed ledgers; descriptive account sensitivities, not executable cash strategies. | S; diagnostic only | — | — | — |
| 09/features | [NB09][nb09] | Individual CAGR/Sharpe/Sortino/drawdown/Calmar and activity/age/missingness controls; monthly matured-label forecasts. No account CAGR. | S; 7/30/90d targets | — | — | — |
| 09/K | [NB09][nb09] | K30/60/90/180/360/max ablations, missing=True, partial histories, imputation and robust scaling. Max K has a small lead; year-only addition hurts. | S; 7/30/90d targets | — | — | — |
| 10/original | [NB10][nb10] | Original fixed-unit snapshots: equal, inverse volatility and inverse variance; raw/peer-shrunk risk, risk windows, 4/6/8/10 slots, caps, covariance budgets and future-risk diagnostic. | S; 7/30/90d snapshots | — | — | — |
| 10/T00 | [NB10][nb10] | Rank L; size source90 → source; N=6, missing=Legacy, constraints=C. Exact source control. | S; 30d snapshots | — | — | — |
| 10/T01 | [NB10][nb10] | Rank F; size constant 1 → equal; N=6, missing=M0, constraints=C. Same-basket equal. | S; 30d snapshots | — | — | — |
| 10/T02 | [NB10][nb10] | Rank F; size F → linear; N=6, missing=M0, constraints=C. Frozen score sizing. | S; 30d snapshots | — | — | — |
| 10/T03 | [NB10][nb10] | Rank F; size I90 → linear; N=6, missing=M0, constraints=C. Inverse variance component. | S; 30d snapshots | — | — | — |
| 10/T04 | [NB10][nb10] | Rank F; size V90 → linear; N=6, missing=M0, constraints=C. Inverse volatility component. | S; 30d snapshots | — | — | — |
| 10/T05 | [NB10][nb10] | Rank F; size A(F,I90) → linear; N=6, missing=M0, constraints=C. Risk in sizing score. | S; 30d snapshots | — | — | — |
| 10/T06 | [NB10][nb10] | Rank A(F,I90); size constant 1 → equal; N=6, missing=M0, constraints=C. Risk in ranking only. | S; 30d snapshots | — | — | — |
| 10/T07 | [NB10][nb10] | Rank A(F,I90); size A(F,I90) → linear; N=6, missing=M0, constraints=C. Risk in both roles. | S; 30d snapshots | — | — | — |
| 10/T08 | [NB10][nb10] | Rank F; size A(F,V90) → linear; N=6, missing=M0, constraints=C. Inverse volatility blend. | S; 30d snapshots | — | — | — |
| 10/T09 | [NB10][nb10] | Rank F; size G(F,I90) → linear; N=6, missing=M0, constraints=C. Geometric agreement. | S; 30d snapshots | — | — | — |
| 10/T10 | [NB10][nb10] | Rank F; size A(F,I90) → power; N=6, missing=M0, constraints=C. Squared conviction. | S; 30d snapshots | — | — | — |
| 10/T11 | [NB10][nb10] | Rank F; size A(F,I90) → softmax; N=6, missing=M0, constraints=C. Softmax conviction. | S; 30d snapshots | — | — | — |
| 10/T12 | [NB10][nb10] | Rank F; size A(F,I90) → percentile; N=6, missing=M0, constraints=C. Ordering-based sizing. | S; 30d snapshots | — | — | — |
| 10/T13 | [NB10][nb10] | Rank F; size A(F,I90,K90) → linear; N=6, missing=M0, constraints=C. K in sizing. | S; 30d snapshots | — | — | — |
| 10/T14 | [NB10][nb10] | Rank A(F,I90,K90); size A(F,I90,K90) → linear; N=6, missing=M0, constraints=C. Three-input joint score. | S; 30d snapshots | — | — | — |
| 10/T15 | [NB10][nb10] | Rank A(F,I90,Kmax); size A(F,I90,Kmax) → linear; N=6, missing=M0, constraints=C. Maximum-history K. | S; 30d snapshots | — | — | — |
| 10/T16 | [NB10][nb10] | Rank A(F,I90,K360); size A(F,I90,K360) → linear; N=6, missing=M0, constraints=C. Long fixed K. | S; 30d snapshots | — | — | — |
| 10/T17 | [NB10][nb10] | Rank B; size G(B,I90,K30+) → linear; N=6, missing=M0, constraints=C. Positive K geometric blend. | S; 30d snapshots | — | — | — |
| 10/T18 | [NB10][nb10] | Rank L; size Min(Sh90,Ca180,V180,Kmax) → linear; N=6, missing=M0, constraints=C. Minimum and zero/fallback probe. | S; 30d snapshots | — | — | — |
| 10/T19 | [NB10][nb10] | Rank A(C180,So30,K90); size A(I90,Kmax,D90) → linear; N=6, missing=M0, constraints=C. Different ranking and sizing features. | S; 30d snapshots | — | — | — |
| 10/T20 | [NB10][nb10] | Rank A(F,I90,K90); size A(F,I90,K90) → linear; N=10, missing=M0, constraints=C. Breadth control. | S; 30d snapshots | — | — | — |
| 10/T21 | [NB10][nb10] | Rank A(F,I90,K90); size A(F,I90,K90) → linear; N=6, missing=MN, constraints=C. Neutral missingness. | S; 30d snapshots | — | — | — |
| 10/T22 | [NB10][nb10] | Rank A(F,I90,K90); size A(F,I90,K90) → linear; N=6, missing=MA, constraints=C. Available-component mean. | S; 30d snapshots | — | — | — |
| 10/T23 | [NB10][nb10] | Rank A(F,I90,K90_conf); size A(F,I90,K90_conf) → linear; N=6, missing=M0, constraints=C. K support confidence. | S; 30d snapshots | — | — | — |
| 10/T24 | [NB10][nb10] | Rank F; size A(F,I90,K90) → risk_budget; N=6, missing=M0, constraints=C. Score risk contributions. | S; 30d snapshots | — | — | — |
| 10/T25 | [NB10][nb10] | Rank A(F,I90,K90); size A(F,I90,K90) → linear; N=6, missing=M0, constraints=P. Uncapped mechanism control. | S; 30d snapshots | — | — | — |
| 10/T26 | [NB10][nb10] | Rank A(F,I90,K90); size A(F,I90) → linear; N=6, missing=M0, constraints=C. K-off sizing on K-on basket. | S; 30d snapshots | — | — | — |
| 10/T27 | [NB10][nb10] | Rank F; size A(F,constant 0.5) → linear; N=6, missing=M0, constraints=C. Neutral-offset flattening control. | S; 30d snapshots | — | — | — |
| 10/T28 | [NB10][nb10] | Rank C30; size C30 → linear; N=6, missing=M0, constraints=C. Short CAGR. | S; 30d snapshots | — | — | — |
| 10/T29 | [NB10][nb10] | Rank C360; size C360 → linear; N=6, missing=M0, constraints=C. Long CAGR. | S; 30d snapshots | — | — | — |
| 10/T30 | [NB10][nb10] | Rank Sh90; size Sh90 → linear; N=6, missing=M0, constraints=C. Short Sharpe. | S; 30d snapshots | — | — | — |
| 10/T31 | [NB10][nb10] | Rank Sh360; size Sh360 → linear; N=6, missing=M0, constraints=C. Long Sharpe. | S; 30d snapshots | — | — | — |
| 10/T32 | [NB10][nb10] | Rank So180; size So180 → linear; N=6, missing=M0, constraints=C. Sortino. | S; 30d snapshots | — | — | — |
| 10/T33 | [NB10][nb10] | Rank D90; size D90 → linear; N=6, missing=M0, constraints=C. Drawdown. | S; 30d snapshots | — | — | — |
| 10/T34 | [NB10][nb10] | Rank Ca360; size Ca360 → linear; N=6, missing=M0, constraints=C. Calmar. | S; 30d snapshots | — | — | — |
| 10/T35 | [NB10][nb10] | Rank Kmax; size Kmax → linear; N=6, missing=M0, constraints=C. K alone. | S; 30d snapshots | — | — | — |
| 11/risk-grid | [NB11][nb11] | 40 policies: 45/90/180d risk; powers 1/1.5/2; κ30 or L/3; raw floor, bounded inverse-risk scores, min-component recipe, median/max multi-window risk, calendar-log and gap-log variance. | S; 7/30/90d snapshots | — | — | — |
| 12/constraints | [NB12][nb12] | Eight matched projected/constrained convex equal-risk or score-risk allocations, plus twelve sensitivities in 75/105d windows, κ10/90 and raw floors. Snapshot comparisons have no strategy CAGR. | S; 30d snapshots | — | — | — |
| 12/S01 | [NB12][nb12] | F:equal; full trading-engine shortlist replay. | S | 37.97% | 1.526 | -11.58% |
| 12/S02 | [NB12][nb12] | L:equal; full trading-engine shortlist replay. | S | 33.63% | 1.376 | -10.56% |
| 12/S03 | [NB12][nb12] | F:regular L90/p2/κ30; full trading-engine shortlist replay. | S | 46.60% | 2.092 | -7.05% |
| 12/S04 | [NB12][nb12] | L:regular L90/p2/κ30; full trading-engine shortlist replay. | S | 33.34% | 1.632 | -6.60% |
| 12/S15 | [NB12][nb12] | L:bounded_V; full trading-engine shortlist replay. | S | 34.25% | 1.464 | -9.95% |
| 12/S16 | [NB12][nb12] | L:T18; full trading-engine shortlist replay. | S | 39.66% | 1.642 | -9.75% |
| 12/S17 | [NB12][nb12] | F:calendar_log L90/p2/κ30; full trading-engine shortlist replay. | S | 47.04% | 2.116 | -7.08% |
| 12/S18 | [NB12][nb12] | F:gap_log L90/p2/κ30; full trading-engine shortlist replay. | S | 47.46% | 2.123 | -7.10% |
| 12/C01 | [NB12][nb12] | F:equal_risk / projected; full trading-engine shortlist replay. | S | 42.98% | 1.916 | -8.26% |
| 12/C02 | [NB12][nb12] | F:equal_risk / constrained_convex; full trading-engine shortlist replay. | S | 42.88% | 1.925 | -8.06% |
| 12/C05 | [NB12][nb12] | L:equal_risk / projected; full trading-engine shortlist replay. | S | 33.49% | 1.574 | -7.68% |
| 12/C06 | [NB12][nb12] | L:equal_risk / constrained_convex; full trading-engine shortlist replay. | S | 33.88% | 1.602 | -7.50% |
| 12/X01 | [NB12][nb12] | F:regular L75/p2/κ30; full trading-engine shortlist replay. | S | 46.92% | 2.123 | -7.08% |
| 12/X08 | [NB12][nb12] | L:regular L90/p2/κ90; full trading-engine shortlist replay. | S | 32.07% | 1.528 | -7.06% |
| 13/shortlist | [NB13][nb13] | Ten 2026-selected configurations replayed over full history: six score/breadth candidates and four regularised/calendar/gap-risk candidates, plus two controls. CAGR leader C07 shown; Sharpe leader C03 is 22.09% / 1.622. | L | 27.44% | 1.505 | −10.24% |
| 14/A | [NB14][nb14] | Four-input ranking; original source 90-day variance and sequential capacity allocation. | S / L | 51.77% / 22.53% | 2.304 / 1.653 | -6.35% / -7.92% |
| 14/B | [NB14][nb14] | Same source-risk basket; simultaneous capped proportional redistribution. | S / L | 50.46% / 22.69% | 2.253 / 1.635 | -6.54% / -7.92% |
| 14/C | [NB14][nb14] | Peer-shrunk 90-day empirical variance with partial-history support; original sequential allocator. | S / L | 47.56% / 27.53% | 2.123 / 1.560 | -6.93% / -10.73% |
| 14/D | [NB14][nb14] | Same regularised variance with simultaneous capped redistribution. | S / L | 46.60% / 27.66% | 2.093 / 1.543 | -7.05% / -10.63% |
| 14/G | [NB14][nb14] | Regularised negative-return second moment instead of total variance; original allocator. | S / L | 47.28% / 27.85% | 2.114 / 1.543 | -7.72% / -11.37% |
| 16/V11-W | [NB16][nb16] | Source v11 risk ordered by waterfall, preserving two-input ranking. | S / L | 31.57% / 15.36% | 1.553 / 1.203 | -6.64% / -8.66% |
| 16/A-W | [NB16][nb16] | Four-input score with source variance priority and waterfall. | S / L | 48.89% / 22.58% | 2.138 / 1.647 | -6.07% / -7.92% |
| 16/C-W | [NB16][nb16] | Four-input score with regularised variance priority and waterfall; predecessor of C00. | S / L | 51.35% / 30.96% | 2.230 / 1.725 | -6.08% / -10.33% |
| 16/G-W | [NB16][nb16] | Four-input score with regularised downside priority and waterfall. | S / L | 56.19% / 29.94% | 2.456 / 1.598 | -6.81% / -12.83% |
| 17/M01 | [NB17][nb17] | Admission-aware risk waterfall | S / L | 46.97% / 30.74% | 2.041 / 1.713 | -6.70% / -10.63% |
| 17/M02 | [NB17][nb17] | Proportional capped risk | S / L | 46.00% / 27.56% | 2.064 / 1.537 | -7.38% / -10.63% |
| 17/M03 | [NB17][nb17] | Score-priority waterfall | S / L | 40.99% / 28.23% | 1.316 / 1.409 | -15.59% / -13.81% |
| 17/M04 | [NB17][nb17] | Core + two score-first overflow | S / L | 40.33% / 28.53% | 1.769 / 1.522 | -7.45% / -14.04% |
| 17/M05 | [NB17][nb17] | Core + four score-first overflow | S / L | 40.13% / 35.30% | 1.760 / 1.648 | -7.60% / -12.12% |
| 17/M06 | [NB17][nb17] | Core + four scored-only overflow | S / L | 40.13% / 27.86% | 1.760 / 1.519 | -7.60% / -10.63% |
| 17/M07 | [NB17][nb17] | Capacity-aware incumbent retention | S / L | 49.18% / 29.32% | 2.200 / 1.619 | -6.70% / -11.01% |
| 17/M08 | [NB17][nb17] | Greedy score-dollar basket | S / L | 33.46% / 14.95% | 1.131 / 0.981 | -15.40% / -13.56% |
| 17/M09 | [NB17][nb17] | Maintained / fee-aware overflow | S / L | 37.61% / 27.92% | 1.719 / 1.359 | -8.48% / -11.79% |
| 17/M10 | [NB17][nb17] | One-decision rank-exit confirmation | S / L | 52.01% / 27.15% | 2.148 / 1.515 | -10.25% / -10.72% |
| 17/M11 | [NB17][nb17] | Joint six-slot score optimiser | S / L | 32.32% / 14.51% | 1.101 / 0.956 | -15.40% / -13.57% |
| 17/M12 | [NB17][nb17] | Legacy capacity extension | S / L | 40.30% / 32.48% | 1.799 / 1.561 | -8.64% / -11.24% |
| 17/M13 | [NB17][nb17] | Fixed ten-name core | S / L | -8.48% / 15.95% | -0.896 / 0.824 | -7.98% / -23.03% |
| 17/fee-M00 | [NB17][nb17] | Same M00 policy with corrected partial-redemption fees; separates accounting from allocation. | S / L | 58.58% / 33.13% | 2.492 / 1.822 | -6.09% / -9.97% |
| 17/fee-M05 | [NB17][nb17] | Same M05 policy with corrected partial-redemption fees; separates accounting from allocation. | S / L | 47.81% / 37.73% | 2.044 / 1.716 | -7.36% / -12.09% |
| 17/fee-M10 | [NB17][nb17] | Same M10 policy with corrected partial-redemption fees; separates accounting from allocation. | S / L | 57.17% / 28.64% | 2.320 / 1.590 | -10.22% / -10.41% |
| 18/C00 | [NB18][nb18] | Exact six-slot regularised-risk waterfall with corrected partial-sale fees. | S / L | 58.58% / 33.13% | 2.492 / 1.822 | -6.09% / -9.97% |
| 18/C01 | [NB18][nb18] | Check usable deposit capacity before constructing the protected six-position core. | S / L | 54.54% / 32.93% | 2.316 / 1.811 | -6.07% / -10.32% |
| 18/C02 | [NB18][nb18] | Spend residual cash on up to four unconditional score-ranked overflow positions. | S / L | 47.81% / 37.73% | 2.044 / 1.716 | -7.36% / -12.09% |
| 18/R00 | [NB18][nb18] | Additional inverse-volatility sleeve under cash, gross exposure and linear risk-headroom limits. | S / L | 52.46% / 31.48% | 2.232 / 1.742 | -6.82% / -10.32% |
| 18/R01 | [NB18][nb18] | Risk-only sleeve plus fee-aware hold-versus-cash exits using matured forecasts. | S / L | 54.09% / 31.48% | 2.302 / 1.736 | -6.07% / -10.32% |
| 18/R02 | [NB18][nb18] | Require a positive pooled lower forecast bound before additional positions are funded. | S / L | 54.54% / 32.50% | 2.316 / 1.797 | -6.07% / -10.32% |
| 18/R03 | [NB18][nb18] | Use positive net forecasts within score/support groups to admit additional positions. | S / L | 54.54% / 32.57% | 2.316 / 1.792 | -6.07% / -10.32% |
| 18/R04 | [NB18][nb18] | Scale admitted sleeve exposure gradually using expected gain and incremental risk. | S / L | 54.54% / 32.50% | 2.316 / 1.797 | -6.07% / -10.32% |
| 18/R05 | [NB18][nb18] | Same gradual policy with the full reference-risk budget instead of the 75% budget. | S / L | 54.54% / 32.23% | 2.316 / 1.783 | -6.07% / -10.32% |
| 19/C00 | [NB19][nb19] | Exact corrected C-W | S / L | 58.59% / 33.13% | 2.474 / 1.651 | -6.36% / -9.94% |
| 19/E00 | [NB19][nb19] | Protected C00 core; fixed additional tickets of 2.5% conservative equity, then hold units. | S / L | 54.53% / 33.52% | 2.310 / 1.666 | -7.30% / -9.94% |
| 19/R00 | [NB19][nb19] | Same tickets multiplied by min(1, sqrt(peer variance / own predicted variance)); hold units. | S / L | 54.63% / 33.41% | 2.319 / 1.662 | -7.29% / -9.94% |
| 19/S00 | [NB19][nb19] | Same tickets multiplied by 0.5 + 0.5 × clipped performance score; hold units. | S / L | 54.39% / 33.49% | 2.308 / 1.664 | -7.29% / -9.94% |
| 19/RS00 | [NB19][nb19] | Multiply absolute tickets by both performance-strength and risk factors; hold units. | S / L | 54.50% / 33.31% | 2.317 / 1.658 | -7.29% / -9.94% |
| 19/RS01 | [NB19][nb19] | Continuously resize the same absolute score × risk tickets rather than hold purchase units. | S / L | 58.84% / 33.66% | 2.475 / 1.673 | -6.45% / -9.94% |
| 19/NRS00 | [NB19][nb19] | Normalise score × risk across extras to spend the residual sleeve budget, with caps. | S / L | 56.49% / 33.05% | 2.350 / 1.643 | -7.29% / -9.94% |
| 19/RS08 | [NB19][nb19] | Combined held-ticket policy with eight total positions; C00 core ranks remain fixed. | S / L | 55.35% / 33.41% | 2.348 / 1.663 | -7.27% / -9.94% |
| 19/RS12 | [NB19][nb19] | Combined held-ticket policy with twelve total positions; C00 core ranks remain fixed. | S / L | 54.64% / 33.24% | 2.320 / 1.654 | -7.29% / -9.94% |
| 19/GF25 | [NB19][nb19] | Reduce the additional-position score floor from 0.5 to 0.25, retaining held tickets. | S / L | 54.42% / 33.26% | 2.315 / 1.656 | -7.29% / -9.94% |
| 19/CAP10 | [NB19][nb19] | Reduce additional gross limits from 5%/25% to 2% per name / 10% overall. | S / L | 57.17% / 33.00% | 2.422 / 1.645 | -6.72% / -9.94% |
| 20/V11 | [NB20][nb20] | Local v11 source with shared corrected partial sales, fresh-entry tax reset and final-proceeds funding. | S / L | 49.15% / 18.55% | 2.214 / 1.374 | -6.41% / -7.92% |
| 20/C00 | [NB20][nb20] | 48/32/10/10 four-input ranking; regularised 90d inverse-risk waterfall; exact six-slot source selector and constraints. | S / L | 58.59% / 33.13% | 2.474 / 1.651 | -6.36% / -9.94% |
| 21/F01 | [NB21][nb21] | Exact C00 with sell rebalance threshold widened from 0.5% to 1%; no new forecasting. | S / L | 58.70% / 33.22% | 2.479 / 1.664 | -6.46% / -9.92% |
| 21/P00 | [NB21][nb21] | Adaptive marginal net-profit targets using support-conditioned pooled gain/loss distributions. | S / L | 10.44% / 5.68% | 1.530 / 0.654 | -2.01% / -14.32% |
| 21/D00 | [NB21][nb21] | Loss-probability feature model plus support-conditioned gain/loss magnitudes and a portfolio downside budget. | S | -2.73% | -1.526 | -2.30% |
| 21/M00 | [NB21][nb21] | Predict gain and loss magnitudes as well as loss probability; optimise fee-aware marginal opportunity value. | S | -39.74% | -1.846 | -32.09% |
| 21/C01 | [NB21][nb21] | Calibrate the C00 score into a net-return forecast; use it for adaptive portfolio targets. | S / L | 11.28% / 0.86% | 1.654 / 0.145 | -1.90% / -18.01% |
| 21/D02 | [NB21][nb21] | Restrict the conditional-downside allocator to at most six positions. | S | -2.73% | -1.526 | -2.30% |
| 21/D03 | [NB21][nb21] | Apply the downside forecast to fresh entries; ablate forecast-driven incumbent sales. | S / L | 3.19% / 8.62% | 0.737 / 1.456 | -2.86% / -4.62% |
| 21/D04 | [NB21][nb21] | Remove the downside-budget constraint from the conditional-downside allocator. | S | -17.85% | -2.127 | -14.55% |
| 21/BHALF | [NB21][nb21] | Half the registered downside budget; otherwise preserve the D00 package. | S | -1.24% | -0.927 | -1.39% |
| 21/BDOUBLE | [NB21][nb21] | Double that downside budget; otherwise preserve the D00 package. | S | -7.53% | -1.303 | -6.37% |
| 21/H07 | [NB21][nb21] | Seven-day forecast and budget package instead of thirty days; a joint horizon sensitivity. | S | -20.21% | -1.515 | -21.35% |
| 21/MARGIN | [NB21][nb21] | Subtract common calibration uncertainty from the marginal-value decision. | S | -0.08% | -0.013 | -1.68% |
| 21/GATE14 | [NB21][nb21] | Restore the source 14-day momentum gate within the forecast-driven package. | S | -2.73% | -1.526 | -2.30% |
| 22/entry-calibration | [NB22][nb22] | Initial-unit managed spell attribution; separate average-level/within-band calibration, 2d/7d horizon alignment, 999 identity/block controls and unresolved-outcome sensitivity. Gate failed; no overlay accounts. | Pre-2026 gate; S diagnostic only | — | — | — |
| 23/replication | [NB23][nb23] | Repackage exact C00 and source v11 in NB160 outline; new four-account replay matches NB20. No strategy change. | S / L | 58.59% / 33.13% | 2.474 / 1.651 | −6.36% / −9.94% |

## What the experiments taught us

### Ranking, exposure and sizing answer different questions

Our score recipes have modest return-ranking information. NB08’s 30-day return IC is about 0.09 for both v11 and the four-input recipe, with calendar-block bands including zero and a reversal from positive Q1 to negative Q3. Historical extra windows improve the portfolio replay, but they do not demonstrate stable broad predictive superiority. Risk forecasts are more informative: NB09’s volatility ranking is around 0.74–0.77 on supported seven/thirty-day cohorts. A signal that ranks risk well still needs a separate economic argument before it controls total exposure.

### What worked

The **four-input ranking** improved the matched source-risk account in both inspected periods. Its collapsed 58/42 two-input control lost most of that gain, suggesting the extra windows matter beyond aggregate CAGR/Sortino balance. The formula remains a historical selection from many inspected candidates.

**Regularised risk plus waterfall allocation** is the main construction lead. Near-flat or sparse histories can otherwise dominate inverse variance, and accepted allocations can differ sharply from requested weights. The regularised-risk waterfall improves its matched C parent in both periods and leads to C00 after shared accounting corrections. Waterfall alone is not generally superior: it hurts v11 and some source-risk comparisons. This is evidence for a particular combined policy, not proof that the 90-day window or shrinkage strength is optimal.

**Explicit source parity and accounting audits** materially changed our conclusions. Single charging of partial redemptions, clearing stale tax on reopened positions and respecting final net sale proceeds prevent spurious comparisons. NB23 reproduces all four NB20 equity paths and successful trade sequences. Holding current assumptions fixed is useful for research, while the 0.1% capital allowance remains an inherited assumption rather than an established venue fee.

### What did not work

**Accepted-dollar caps without redistribution** leave about half the fresh-2026 portfolio in cash and slash CAGR from 41.20% to 9.31% in the early matched comparison. Flatter weights repair part of that failed allocator but do not beat the uncapped parent. Correlation risk budgets and constrained solvers also lose to simpler controls in the tested engine comparisons, despite some favourable snapshot outcomes.

**More positions and more deployment** often reduce profit. The focal recipe falls from 51.77% CAGR at six slots to −3.01% at ten. That intervention also changes entry/exit ranks and later allocations to shared winners; it is not an isolated diversification test. NB17 reduces September cash from roughly 49% to 2–5% with some methods, yet substantially lowers fresh-2026 profit. Waterfall inside six slots cannot absorb more than those vaults’ combined concentration/TVL capacity. In the September audit, capacity explains 96.9% of summed decision shortfalls, while rejected top-ups explain only 2.6%; these are deployment diagnostics, not foregone-profit estimates.

**K-ratio, smoothing and admission floors** supplied no demonstrated portfolio replacement. Max-history K has small incremental forecast leads, but supported uncertainty includes zero; adding the one-year feature alone worsens the tested point estimates. Learned absolute floors often act on no actual entries. Rejecting missing scores harms full-history return: absent long history is not a measured bad opportunity. Filling known NAV after inception improves metric coverage without making carried marks independent observations or reconstructing missing terminal outcomes.

**Forecast-driven exposure and marginal-profit optimisation** performed poorly. NB21’s best score-calibrated adaptive forecast account gives 11.28% CAGR in 2026; conditional magnitude allocation gives −39.74%. The profitable C00 cohort is often predicted negative, so increasing solver sophistication does not fix miscalibrated opportunity values. Restricting downside portfolios to six names or removing the loss budget does not rescue them.

NB22 corrects seven-day average bias from −0.91 to −0.19 percentage points, yet ranking remains weak, with IC −0.065 and roughly 49% sign accuracy. Closed pre-2026 vetoes appear to avoid USD 6,133, but the 1.09% value per resolved veto dollar loses to the 1.19% calendar-block median and reverses to −USD 4,742 when available open-position marks are included. The planned qualification gate therefore stops the overlay accounts. There is no unexecuted strategy-performance claim.

### Smaller leads and important qualifications

NB19’s **absolute score × risk resize sleeve** adds only USD 255 in fresh 2026, with slightly worse drawdown. Role attribution assigns negative profit to extras and a positive gain to core feedback; it does not establish profitable extra positions in isolation. NB21’s **1% sell band** adds about USD 116 in 2026 and USD 1,025 over full history. These are small execution leads, not significant confirmed improvements over C00.

Returns are concentrated. Realist Capital supplies about 35.4% of C00’s positive 2026 vault profit, and the largest account update is +6.46%. Its NAV and Goon Edging rise roughly 14% over two observed days while BTC/ETH fall over the same intervals. Curator and market checks help interpret the move; they do not prove a continuously executable NAV. Full-history large updates also include week-long reporting intervals. Fixed-ledger deletion or zeroing the best day measures influence, not the performance of an executable alternative portfolio.

All periods have been researched repeatedly and the long period overlaps 2026. Sparse observations, current inventory/guard applied retrospectively, incomplete historical permission clocks, resolved-label selection and terminal censoring limit generalisation. Unknown outcomes are not assumed zero, and confidence from forward-filled calendar rows is tracked separately from actual updates.

## Likely future leads

The [follow-up prioritisation and proposed NB24 matrix](next-research-leads.md) reviews these leads against the completed work. It is a proposed research design, with no new measured results.

1. **Freeze C00 and observe later data.** Retain matched v11 and the small RS01/sell-band leads without selecting another winner from the same history. The current figures establish historical trade-offs, not an untouched confirmation.
2. **Align prediction with managed trades.** Forecast net outcomes for actual executable fresh entries, with exits, re-entry, cost basis and unresolved positions accounted for. NB22’s four-day median versus 11.4-day capital-weighted life explains why a generic 30-day hold label can miss the decision’s economics; even the better aligned seven-day label remains approximate.
3. **Develop downside calibration before exposure control.** Require a filter to beat identity and timing controls and retain its value under unfinished-outcome scenarios. Unsupported young/missing observations should retain an explicit fallback to the trusted core rather than automatically force cash.
4. **Refine risk and capacity jointly on fixed core rules.** Use nearby risk-window/shrinkage controls, requested-versus-accepted attribution and scarce-capacity examples. Covariance diversification remains a possible targeted lead; the limited tested designs do not exhaust it. Avoid treating a solver optimum for a score surrogate as maximum executable profit.
5. **Allocate residual cash only with an evidenced marginal advantage.** Preserve core selection and targets, account for slot/TVL limits and whole-account feedback, and compare extras with cash. More deployment is worthwhile only when it improves net profit at an acceptable risk trade-off.
6. **Improve observation evidence.** Retain archived state when its independent clock is unknown, distinguish observation time from export/write time, audit isolated jumps and confirm real fee/permission behaviour. Keep causal fills, actual-update confidence and young-vault support explicit.

## Publication contents and execution prerequisites

The PR includes the 23 main notebooks, presentation appendices, reusable Python helpers, plans, reviews and written conclusions. Numeric tables and Markdown results are retained. NB23’s 24 static charts remain embedded; bitmap payloads elsewhere and bundled runtime JavaScript are removed from the publication copy. Full local outputs remain in the original working folder.

No datasets, price archives, standalone images, engine states, parquet/CSV outputs, pickles, DuckDB files, logs or generated manifests are committed. The research `.gitignore` protects those files. The original working tree’s editor and notebook-runner changes are outside this PR.

These are archived research notebooks. Rerunning needs the recorded repaired archive, matching external `strategies`/`trade-executor`/`trading-strategy` checkouts and the local research input/cache generations referenced by the code. Those prerequisites are intentionally not bundled. Python is formatted in the PR copy as required by the repository’s PR rules; semantic AST parity was checked. Recorded execution fingerprints describe the measured pre-publication sources, so presentation formatting can invalidate byte-hash caches. Preserve the recorded results and regenerate identities/caches for a new run rather than relabelling old measurements.

[Detailed experiment notes](summary.md) include individual hypotheses, verdicts and limitations. [NB23][nb23] is the clean C00 reference; [NB20][nb20] gives its matched accounting comparison.

[nb15]: 15-backtest-allocation-vs-v11.ipynb
[nb17]: 17-backtest-capacity-aware-allocation.ipynb
[nb04]: 04-opt-score-matrix.ipynb
[nb09]: 09-research-k-ratio-feature-forecasts.ipynb
[nb11]: 11-research-weighting-sizing.ipynb
[nb16]: 16-backtest-waterfall-allocation-vs-v11.ipynb
[nb13]: 13-backtest-leading-candidates.ipynb
[nb07]: 07-opt-score-position-count.ipynb
[nb21]: 21-research-marginal-profit-allocation.ipynb
[nb20]: 20-backtest-c00-vs-v11.ipynb
[nb12]: 12-research-allocation-followup.ipynb
[nb14]: 14-backtest-profitable-allocation.ipynb
[nb05]: 05-opt-score-calibration-selection-cash.ipynb
[nb02]: 02-backtest-accepted-dollar-cap.ipynb
[nb22]: 22-research-c00-entry-margin-calibration.ipynb
[nb23]: 23-backtest-c00.ipynb
[nb01]: 01-initial.ipynb
[nb18]: 18-backtest-conditional-cash-allocation.ipynb
[nb19]: 19-backtest-protected-core-score-risk-allocation.ipynb
[nb08]: 08-research-score-forecast-thresholds.ipynb
[nb10]: 10-research-portfolio-snapshots.ipynb
[nb06]: 06-opt-score-3-4-inputs.ipynb
[nb03]: 03-backtest-alternative-weighting.ipynb
