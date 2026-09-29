# Final Opus 5 review — Hyperliquid vault IC research (post-rerun)

All headline facts were re-derived from the artefacts, not taken from the narrative: 602 vaults / 647 dates / 68 eligible dates / 17,683 eligible rows; 82 predictors + 6 `ema_seed_weight_*` controls; 49 outcomes; 6,972 IC rows (minimum cross-section 147); 8,428 grid cells with 1,456 unavailable cells recorded; 2 folds / 69 Ridge rows; OOF IC growth 0.035, downside 0.640, variance 0.696; `cagr_360` (and `sharpe_360`, `sortino_360`, `cagr_180`) null on every eligible row; both arms flat at $150,000 with zero positions; zero error outputs in all four notebooks; `py_compile` passes. No follower/leader/social field enters `_load_universe_json` (`ic_research.py:152-155`), `vault-metadata.csv`, or feature generation.

## 1. Verdict

**Proceed with prospective collection.** Phase 1 passes only via its data-gap branch: `historical_point_in_time_reconstructable: false`, the first visible NAV under the two-day clock is 2026-04-09 (not the 2026-03-23 `written_at_start`), and 36.7% of April observations are still masked. Feature, eligibility and label causality holds on the real generator (NB02 cell 5, 40 vaults, features + eligibility + matured labels). I additionally confirmed `forward_log_growth_H` equals `log(P[d+H]/P[d])` exactly on all 16,612 / 13,945 / 6,106 eligible rows (H = 7/30/90) and that publication masking inside eligible label windows is sparse (mean 0.1 masked days of 30, maximum 4) and uncorrelated with the risk labels (per-date IC approximately -0.03).

**Phase 4 shortlist gate remains open** — no bootstrap, no intact-bundle null, no control incremental lift, no horizon selection, no B/D arms. The result is risk persistence, not an edge. One labelling defect (engine parity) and one specification ambiguity should be fixed before the first shadow decision, but neither blocks starting the collector.

## 2. Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
|---|---|---|---|---|
| NB01 data/baseline | Panel, hashes, lag audit and `available_ts` correct. `config.json` lacks the code revision and `hyper-ai.py` hash required by plan §Phase 1.1; the whole `scratchpad/hyperliquid-ic/` tree is untracked, so the freeze is not committed. | Thin: no funnel, hand-checked rows, April polling check, survivorship sensitivity or indicator-parity comparison. | 602 vaults, 1,293 days, 247 currently eligible: plausible. | Low, deferred |
| NB02 feature panel | Causal on the executed prefix check; labels, purge inputs, EWM `adjust=True`, gap/unchanged fixes verified. Eligibility does not enforce the plan's 30-day observed-history rule: 1,258 eligible rows (7.1%) have fewer than 30 visible days, almost all on 2026-05-02…05-08 where every vault's window is truncated by the 2026-04-09 visibility boundary. | 82 + 6 + 49 as declared. Several features deviate from their plan definitions; see §3. Manifest is still generic. | 229–280 eligible vaults per date; no long-history columns. Zero missing 30/90-day labels among eligible rows, so terminal-NAV stress scenarios are vacuous here. | Low–Medium |
| NB03 IC screen | Purge, fold-local selection, pairwise minimum and equal date weighting enforced. The pct-rank/pairwise-Pearson shortcut differs from exact Spearman by at most 0.025 per date. | Exhaustive table + grid audit exist. Deferred: bootstrap, null, upper-bucket baskets, cohort splits, incremental lift, horizon rule and non-negative risk forecasts. | Volatility persistence dominates; growth OOF IC flips sign across folds (+0.14 / -0.13). 7.3% of 30-day labels have exactly zero variance and median forward growth is 0.0; `unchanged_nav_frac_30` alone scores IC -0.43 on forward variance. | Medium, deferred |
| NB04 replay | Accounting consistent; cash is the correct research outcome. | A and C only; B/D correctly deferred. | Cash is a coverage outcome. | Important (labelling) |

## 3. Remaining defects and acceptable limitations

**Important (fix before shadow decisions)**

1. Engine-parity wording must say research abstention. The live engine (`hyper-ai.py:874-883`) coerces a NaN composite to `0.0`, keeps the vault, sorts by `(-signal, pair_id)` and fills six slots — on this window it would hold the six lowest-`pair_id` gated vaults sized by inverse variance, rather than cash. The research Sortino also uses a 36-observation minimum while production uses the full 45-day window. These are documented research gaps, not production changes.
2. The prospective specification must require every raw poll since the previous snapshot, the BTC daily bar and hash, and the engine's actual selected basket and weights so later exact-engine replay is checkable.

**Minor (record and fix at the next rerun)**

3. First four eligible dates use 24–29-day windows for 30-day features. Starting eligibility at first-visible + 30 removes this boundary case.
4. Some feature formulas drift from their plan definitions while remaining causal: time-varying BTC beta, Herfindahl positive-gain concentration, fraction-below-peak underwater time, log-TVL-change variability and panel-start weekly blocks. Label these definitions.
5. NB03's whole-period `shortlist.csv` includes both test windows and is descriptive only; `shortlist.json` is fold-local.
6. `shortlist.json` records a 30-day default horizon, not a selected horizon under the plan's horizon rule.

**Acceptable documented limitations**

- Two-day cutoff is an ingestion-clock approximation; label entry is the day-d close rather than a d+2 fill.
- Labels use publication-masked NAV; the masking effect was quantified as immaterial.
- `time_since_last_nav` is zero on eligible rows by construction.
- The 68-date panel has two underpowered folds, absent long-history controls and NAV-only replay; `manifest.json` is written as `config.json`.

## 4. Recommended next actions

1. Replace faithful/parity wording with research abstention and record the live engine's NaN-to-zero / `pair_id` tie-break and Sortino-window gap.
2. Amend the collection specification to store all raw polls, the BTC daily bar/hash and the engine's selected basket/weights; add the git SHA and `hyper-ai.py` SHA-256 to `config.json`.
3. Start eligibility at first-visible + 30 days, then run the paired date-block bootstrap and intact-bundle null against the `vol_30` control before choosing a horizon or freezing a model.
