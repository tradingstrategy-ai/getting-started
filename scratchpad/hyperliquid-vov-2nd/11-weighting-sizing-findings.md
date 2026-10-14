# Experiment 11 — weighting and sizing findings

Period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**. **40 policies, 70 origins, 7/30/90-day targets**; 2025 and earlier indicator warmup retained. Six-vault focal_four and v11 baskets are frozen. These are independent fixed-unit snapshots, not strategy CAGR.

## What was examined

Window45/90/180, allocation power1/1.5/2, fixed versus inherited shrinkage, raw floors, bounded risk scores, multi-window risk and a matched sparse-mark observation model. Source90, focal equal and regularised inverse-variance controls reproduce saved NB10.

## Hypotheses and primary outcomes

Risk weighting might benefit from a stable neighbourhood rather than one lucky window; matched sparse estimators might improve risk forecasts; T18 may chiefly represent bounded V180 sizing. All hypotheses are descriptive because the primary horizon has only eight complete blocks.

| Arm | Method | Mean 30-day return | Mean daily variance | Mean window drawdown | Cash |
| --- | --- | ---: | ---: | ---: | ---: |
| S01 | F:equal | 1.716% | 0.000196 | -6.193% | 3.315% |
| S02 | L:equal | 1.929% | 0.000169 | -5.698% | 3.008% |
| S03 | F:regular L90/p2/κ30 | 2.512% | 0.000120 | -4.191% | 3.315% |
| S04 | L:regular L90/p2/κ30 | 1.992% | 0.000100 | -3.777% | 3.008% |
| S05 | F:regular L45/p1/κ30 | 1.960% | 0.000131 | -4.729% | 3.315% |
| S06 | L:regular L45/p1/κ30 | 1.755% | 0.000115 | -4.349% | 3.008% |
| S07 | F:regular L180/p1.5/κ30 | 2.033% | 0.000146 | -5.048% | 3.315% |
| S08 | L:regular L180/p1.5/κ30 | 1.969% | 0.000121 | -4.588% | 3.008% |
| S09 | F:raw L90/p2/κ30 | 2.353% | 0.000118 | -4.178% | 3.315% |
| S10 | L:raw L90/p2/κ30 | 1.467% | 0.000100 | -3.973% | 3.008% |
| S11 | F:bounded_I | 2.377% | 0.000134 | -4.637% | 3.315% |
| S12 | L:bounded_I | 2.048% | 0.000113 | -4.204% | 3.008% |
| S13 | F:source | 2.353% | 0.000118 | -4.178% | 3.315% |
| S14 | L:source | 1.467% | 0.000100 | -3.973% | 3.008% |
| S15 | L:bounded_V | 2.031% | 0.000144 | -5.028% | 3.008% |
| S16 | L:T18 | 2.390% | 0.000147 | -5.003% | 3.008% |
| S17 | F:calendar_log L90/p2/κ30 | 2.413% | 0.000124 | -4.250% | 3.315% |
| S18 | F:gap_log L90/p2/κ30 | 2.579% | 0.000121 | -4.183% | 3.315% |
| M19 | F:regular L45/p1.5/κ30 | 2.117% | 0.000123 | -4.436% | 3.315% |
| M20 | F:regular L45/p2/κ30 | 2.274% | 0.000119 | -4.268% | 3.315% |
| M21 | F:regular L90/p1/κ30 | 2.159% | 0.000135 | -4.668% | 3.315% |
| M22 | F:regular L90/p1.5/κ30 | 2.357% | 0.000124 | -4.357% | 3.315% |
| M23 | F:regular L180/p1/κ30 | 1.990% | 0.000153 | -5.163% | 3.315% |
| M24 | F:regular L180/p2/κ30 | 2.043% | 0.000142 | -5.025% | 3.315% |
| M25 | L:regular L45/p1.5/κ30 | 1.762% | 0.000107 | -4.087% | 3.008% |
| M26 | L:regular L45/p2/κ30 | 1.825% | 0.000103 | -3.940% | 3.008% |
| M27 | L:regular L90/p1/κ30 | 1.973% | 0.000112 | -4.208% | 3.008% |
| M28 | L:regular L90/p1.5/κ30 | 1.990% | 0.000103 | -3.929% | 3.008% |
| M29 | L:regular L180/p1/κ30 | 2.018% | 0.000126 | -4.686% | 3.008% |
| M30 | L:regular L180/p2/κ30 | 1.883% | 0.000120 | -4.584% | 3.008% |
| M31 | F:regular L45/p2/κ15 | 2.405% | 0.000113 | -4.047% | 3.315% |
| M32 | F:regular L180/p2/κ60 | 2.137% | 0.000146 | -5.043% | 3.315% |
| M33 | L:regular L45/p2/κ15 | 1.870% | 0.000098 | -3.747% | 3.008% |
| M34 | L:regular L180/p2/κ60 | 2.044% | 0.000123 | -4.584% | 3.008% |
| M35 | F:median | 2.366% | 0.000117 | -4.194% | 3.315% |
| M36 | F:maximum | 2.364% | 0.000137 | -4.877% | 3.315% |
| M37 | L:median | 1.885% | 0.000098 | -3.806% | 3.008% |
| M38 | L:maximum | 1.969% | 0.000119 | -4.489% | 3.008% |
| M39 | L:calendar_log L90/p2/κ30 | 1.968% | 0.000099 | -3.782% | 3.008% |
| M40 | L:gap_log L90/p2/κ30 | 2.007% | 0.000104 | -3.831% | 3.008% |

### Registered matched contrasts — 2026 period, 30-day horizon

| New − control | Paired origins | Return difference | Variance ratio | Drawdown difference |
| --- | ---: | ---: | ---: | ---: |
| S05 − S03 | 62 | -0.552 pp | 1.098 | -0.538 pp |
| S07 − S03 | 62 | -0.479 pp | 1.220 | -0.857 pp |
| M19 − S03 | 62 | -0.395 pp | 1.027 | -0.246 pp |
| M20 − S03 | 62 | -0.238 pp | 0.995 | -0.077 pp |
| M21 − S03 | 62 | -0.353 pp | 1.133 | -0.478 pp |
| M22 − S03 | 62 | -0.155 pp | 1.039 | -0.167 pp |
| M23 − S03 | 62 | -0.522 pp | 1.279 | -0.972 pp |
| M24 − S03 | 62 | -0.469 pp | 1.191 | -0.834 pp |
| S06 − S04 | 62 | -0.237 pp | 1.148 | -0.571 pp |
| S08 − S04 | 62 | -0.023 pp | 1.217 | -0.811 pp |
| M25 − S04 | 62 | -0.230 pp | 1.071 | -0.310 pp |
| M26 − S04 | 62 | -0.167 pp | 1.037 | -0.163 pp |
| M27 − S04 | 62 | -0.019 pp | 1.122 | -0.431 pp |
| M28 − S04 | 62 | -0.002 pp | 1.037 | -0.151 pp |
| M29 − S04 | 62 | +0.026 pp | 1.268 | -0.909 pp |
| M30 − S04 | 62 | -0.110 pp | 1.201 | -0.807 pp |
| S16 − S15 | 62 | +0.359 pp | 1.027 | +0.025 pp |

### F research lead — 2026 period, 30-day horizon

Largest descriptive mean: **S18, F:gap_log L90/p2/κ30**, 2.579%, versus 2.512% for its regularised90/p2 baseline. This is a searched historical comparison, not evidence of a production improvement. Inspect adjacent cells, variance, drawdown and attribution before an engine replay.

### L research lead — 2026 period, 30-day horizon

Largest descriptive mean: **S16, L:T18**, 2.390%, versus 1.992% for its regularised90/p2 baseline. This is a searched historical comparison, not evidence of a production improvement. Inspect adjacent cells, variance, drawdown and attribution before an engine replay.

### T18 mechanism — 2026 period, 30-day horizon

T18 minus bounded V180: +0.359 percentage points, variance ratio 1.027. The single-component control uses inherited kappa60 and identical v11 selection. Minimum-component activity is reported separately, with tied minima split.

## Risk prediction and sparse-data interpretation

QLIKE comparisons are equally weighted by origin and deduplicated across allocation powers/transforms. Future zero variance remains valid. Sparse pair uses the same actual endpoints, complete interval counts and calendar-log prior; gap scaling assumes variance proportional to elapsed days. Comparing it to daily-simple baseline also changes return units, endpoints and support. Kappa30 means intervals in the pair versus actual updates in the original estimator. Neither observation model is economic ground truth.

## Robustness and verdict

All **26 main audit checks** pass, including exact historical controls, fixed baskets, 70-date smoke reuse, terminal support, capacity conservation, scalar variance and future-state mutation. There are **8,400 scheduled outcomes**, including pending dates. No fabricated future prices or survivor renormalisation. The 30-day 51-statistic family cannot pass the ten-block gate; seven-day views remain secondary descriptive diagnostics.

Quarter/vault attribution, worst/best windows, first-update contribution, actual-update support, cap-induced ties, requested/accepted breadth and same-budget shadow distortions are saved and shown. Historical publication clocks and current-inventory restrictions remain limitations. Snapshot entry at T−1 is inherited for parity, not an executable decision-time fill.

## Useful leads and next steps

Use the displayed neighbourhood and calibration evidence to choose a small interpretable shortlist for an actual engine replay. Include equal and original90/p2 controls, changing holdings, two-day rebalance timing, trade thresholds and capacities. Fresh observations are needed for confirmation. Twelve sensitivity and eight cap-aware policies are registered but unexecuted.

Generation: `b64b9738eff5af379f16d62b65e0147ce2ee4ab8143505b6fb42c864e37f161c`. Main allocation/outcome execution: 26.5 seconds. Notebook: [NB11](11-research-weighting-sizing.ipynb).

## Interpretation of the hypotheses — 2026 period, 30-day horizon

**Window and allocation strength:** the focal 90/p2 benchmark leads all nine core L×p cells. Increasing p improves focal mean return within each window;180 days produces worse drawdown and variance than90 days for both selectors. The v11 mean-return surface is flatter at90/180 days, but its90-day baseline has better risk than180 days. This does not establish a universal optimal horizon or a broad stable peak.

**Regularisation:** regularised90/p2 minus raw90/p2 is +0.159 pp for focal and +0.525 pp for v11. Source90 and raw90 produce identical accepted weights on these selected baskets. The floor/observation conventions remain separately recorded.

**Sparse estimator:** focal gap minus matched-calendar log sizing is +0.166 pp. Gap minus original simple90 baseline is +0.067 pp, with median30-day return 2.106% versus 2.620%. Mean improvement does not improve the median. All three mature origin quarters have a positive gap/baseline mean difference, but vault effects offset strongly: pmalt contributes about+0.177pp and Hyperrr about−0.177pp to that overall mean difference.

**Calibration versus allocation:** L45 has the most favourable QLIKE improvements against its own window-specific prior, yet does not produce the best portfolio outcome. Those QLIKE references differ by window, so these are not an absolute ranking of forecast losses. Within the matched sparse pair, gap improves focal mean QLIKE modestly; v11 mean QLIKE worsens slightly despite its positive30-day return difference. Calibration ratios move closer to 1 for both. Risk prediction quality and profitable weighting are different questions.

**Multi-window and shrinkage:** median/max alternatives do not beat the focal 90/p2 mean; maximum has higher realised variance and worse drawdown despite using a more conservative marginal forecast. Kappa=L/3 improves mean return over fixed 30 at both 45 and 180 days for both selectors, but only45 days also improves mean drawdown consistently. Larger marginal forecasts can reduce an account’s diversification after normalisation and caps.

**T18:** the other score components still matter even though V180 is the minimum about79% of selected rows. Its+0.359pp overall mean uplift over V180 comes from Q1 (+1.106pp); Q2 is−0.135pp andQ3 approximately flat. It is a regime-sensitive lead, not evidence that four inputs help consistently.

**Cash and constraints:** all 40 methods invest identical total capital within each selector, including explicit common-budget reprojection. Cash cannot explain their differences here. Baseline sum-absolute shadow distortion averages about45% of account capital; about22.6%is transferred between names, half that L1 sum. Cap-aware allocation remains a meaningful separate question.

**Missing support:** the17 January90-day target for Dobutsu–Alpha Club extends beyond its final actual mark. All policies retain that unresolved invested weight;46 of 47 administratively mature90-day baskets resolve. There is only one complete paired90-day block after censoring, not the theoretical maximum of two.

Verdict: retain original90/p2 as the benchmark. The matched sparse gap method merits a controlled engine replay, and T18 merits attribution-aware comparison on v11 baskets. Neither has earned a production change from this retrospective snapshot study.
