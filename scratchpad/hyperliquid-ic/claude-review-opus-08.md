## Final read-only review — Hyperliquid vault IC research (Opus 5)

Facts re-derived from `_artifacts/` (not the narrative): 602 vaults / 647 decision dates / 64 eligible dates 2026-05-10 → 2026-09-13 / 16,425 eligible rows (227–271 per date); 82 core predictors + 6 `ema_seed_weight_*` + 91 `__missing` flags; 49 outcomes; 86 screened predictors; **7,084 IC rows over 8,428 grid cells (1,344 unavailable, recorded)** — not the 6,972 / 1,456 in the prompt, which are pre-fix figures (the BTC fix made 112 more cells available); 2 purged folds (`train_end_used` 06-09 / 07-07); 57 Ridge rows = 19 matured dates × 3 targets; both arms 64 rows at $150,000, `active=False`, 0 positions, 0 trades. `btc_beta_30`/`btc_residual_vol_30`/`beta_btc_return_30`/`abs_beta_btc_vol_30` populated on 99.99% of eligible rows, 90-day versions 62.75%, `cagr_360` 0%. Zero error outputs in all four notebooks (NB02 stderr is benign `FutureWarning`/`RuntimeWarning`); `py_compile` passes; 40-vault full-generator prefix check passed (NB02 cell 5); `research_source_sha256` 4189f6…, `hyper_ai_sha256` 3ac527… and all eight `files_sha256` match the current files; mtimes confirm `ic_research.py` 22:21:53 → NB01 22:22:18 → NB02 22:22:54 → NB03 22:25:21 → NB04 22:25:29. No follower/leader/social/deposit-flow column in `features.parquet`, `labels.parquet`, `raw-observations.parquet` or `vault-metadata.csv`. Eligible-row invariants hold (history ≥ 30, fresh ≥ 24, TVL ≥ 7,500, same-day NAV); `forward_log_growth_30` equals `log(P[d+30]/P[d])` on the masked, 7-day-carried panel (max diff 2e-15); no label is non-null past the panel end.

### 1. Verdict

**Prospective collection: proceed.** The Phase 1 data-gap branch is complete: `historical_point_in_time_reconstructable: false`, `written_at_start` 2026-03-23, two-day publication clock with 35,901 masked source cells, and `prospective-collection-spec.md` now covers raw polls, `available_ts`, BTC bar/hash, fee modes, unknown-not-open deposit status, engine outputs, immutable snapshots, the prefix test and label entry at the first executable NAV at/after the decision boundary. Nothing in the artefacts contradicts the previously fixed issues.

**Research gate: Phase 4 shortlist gate stays open; nothing may be frozen.** OOF Ridge: variance IC 0.77/0.59, downside 0.76/0.50, growth −0.01/−0.21 (fold 1 has five matured dates). This is volatility persistence, not an edge. The one material code finding below is a feature-implementation defect, not a collection blocker.

### 2. Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
|---|---|---|---|---|
| NB01 data/baseline | Panel, lag audit, `available_ts = last_written_at`, git SHA, dirty flag, own-file and source hashes verified. | Still thin: no raw→TVL→eligible→labelled funnel, hand-checked rows, survivorship sensitivity or Stratwise display; `deposits_open`/`redemption_open` null in metadata. Acceptable for the data-gap branch — the spec covers these prospectively. | 1,293 d × 602; p95 lag 40.8 h; cohorts plausible. | Low |
| NB02 feature panel | Labels exact; generator causal on prefix check; 30-day history gate in force; BTC family no longer has an age barrier (availability matches a true per-window OLS on 600 sampled rows). **But F32–F35 are not one OLS per window (item 1).** Latent crash in slope/R² helpers (item 2). | 82 + 6 + 49 as declared; manifest formulas generic; F13/F16 definition drift unchanged. | 64 dates, 227–271 eligible. | Medium, non-blocking |
| NB03 IC screen | Purge, fold-local selection, equal date weighting, grid audit verified; min cross-section 149. | Exhaustive table present; bootstrap/null, incremental control vs `vol_30`, horizon rule, terciles/upper bucket deferred (Phase 4). | Top: `vol_10`/`ewm_return_vol_10` vs forward variance 0.85; growth ≈ 0. `beta_btc_return_90` = −`btc_beta_90` (0.2268) is a mechanical mirror (BTC 90-day return negative on all 28 dates), not information. | Medium, deferred |
| NB04 replay | Abstention semantics match code; cash is the coverage outcome. | A and C only; B/D correctly deferred. | Flat $150,000. | Low |

### 3. Defects and limitations

**Blocking:** none.

**Important — fix before any family is frozen, not before collection**

1. **F32–F35 still are not "one trailing OLS per window".** `ic_research.py:480-486` centres each day's return by its *own* trailing rolling mean (`x_mean`, `y_mean` are rolling series), then sums the products over the window; that is Σ(x_t−x̄_t)(y_t−ȳ_t), not Σ(x_t−x̄_T)(y_t−ȳ_T). Verified against `np.polyfit` on synthetic data and on 600 eligible rows: 30-day beta Spearman 0.988, residual vol 0.991, median |Δβ| 0.012, max |Δβ| 1.98; 90-day 0.999. Ranks barely move, so no current conclusion changes, but README:13 and plan.md:11,390 ("one trailing OLS per window") overstate what the code does, and `btc_residual_vol_30` sits in both fold shortlists. Fix is three lines: `sxx = Σx² − n·x̄²`, `sxy = Σxy − n·x̄·ȳ`, `syy = Σy² − n·ȳ²` using the window-end means; residual d.o.f. handling at line 488 is already right.
2. **`_rolling_slope`/`_rolling_r2` crash on a panel that starts with data** (`ic_research.py:264-287`): pandas passes truncated windows for the first `window−1` rows, and `np.dot(x, values)` raises `ValueError: shapes (30,) and (24,)` once a vault has ≥24 valid NAVs in the first 29 grid rows. Never triggered on the cache (leading rows are NaN for every vault, masked or not), but a prospective loader whose date grid begins at collection start will hit it. Guard with `len(values) != window → NaN`.

**Pre-shadow freeze actions (not collection blockers)**

3. Scratchpad is untracked (`?? scratchpad/hyperliquid-ic/`); `config.json` records `code_revision` d40e06d with `git_worktree_dirty: true`, so the revision cannot reproduce `ic_research.py` or the notebooks.
4. `claude-review-opus-08.md` is 0 bytes while README:7 and plan.md:390 already state its verdict — the same pattern flagged for opus-07 last round.

**Acceptable, documented limitations**

- Two-day publication cutoff; `available_ts = last_written_at`; April 2026 heavily masked; first eligible date 05-10.
- Diagnostic labels still enter at NAV_T (`ic_research.py:294,520`) while the information set is consistent with a T+2 decision; the spec is now correct for prospective data, but README/plan do not record the diagnostic convention (effect ≤0.02 IC per the prior measurement).
- `control_nb36_cagr_sharpe` uses `fillna(0)` (NB03 cell 1), so it is available on only 7 dates and is inconsistent with the C03 abstention semantics — descriptive only.
- `time_since_last_nav` is 0 on every eligible row by construction; `sortino_45` min-36-observation parity gap; deposit availability unknown; two underpowered folds; NAV-only replay.

### 4. Three minimal next actions before shadow decisions

1. Replace the rolling-mean centring in the BTC block with window-end sums and guard the slope/R² helpers, rerun NB02→NB04, re-freeze hashes; correct the "one OLS per window" sentence only once the code matches it.
2. Commit the scratchpad, save this review into the empty `claude-review-opus-08.md`, and add one sentence to README/plan stating that diagnostic labels enter at NAV_T whereas the spec's prospective labels enter at the first executable NAV after the boundary.
3. Start the collector per the spec now; before the first shadow decision run the deferred Phase 4 set on the corrected panel — date-block bootstrap and intact-bundle null over the 86 × 21 grid, incremental Ridge versus `vol_30` and the availability-only control, the predeclared horizon rule — and only then freeze horizon/model/allocator and open B/D.
