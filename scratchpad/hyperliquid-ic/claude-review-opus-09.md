## Final read-only review — Hyperliquid vault IC research (Opus 5, `claude-opus-5`)

**Facts re-derived from `_artifacts/`, not the narrative.** 602 vaults / 647 panel dates / 64 eligible dates 2026-05-10 → 2026-09-13 / 16,425 eligible rows (227–271 per date); 82 catalogue predictors + 6 `ema_seed_weight_*` + 91 `__missing` flags; 49 outcomes; 86 screened predictors; **7,084 IC rows** over 8,428 grid cells (1,344 unavailable, recorded) — the prompt's 6,972 is the pre-BTC-fix figure, as review 08 already noted; 2 purged folds (`train_end_used` 06-09 / 07-07); 57 Ridge rows = 19 matured dates × 3 targets; both arms 64 rows at $150,000, `active=False`, 0 positions, 0 trades. `btc_beta_30`/`btc_residual_vol_30`/`beta_btc_return_30`/`abs_beta_btc_vol_30` populated on 99.99 % of eligible rows, 90-day versions 62.75 %, `cagr_360` 0 %. Zero error outputs in all four notebooks (NB02 stderr is benign `FutureWarning`/`RuntimeWarning`); `py_compile` passes; 40-vault full-generator prefix check passed (NB02 cell 5); `research_source_sha256` 9259d7…, `hyper_ai_sha256` 3ac527… and all eight `files_sha256` match the current files; mtimes confirm `ic_research.py` 22:34:54 → NB01 22:35:14 → NB02 22:35:50 → NB03 22:38:15 → NB04 22:38:22. No follower/leader/social/deposit-flow column in `features.parquet`, `labels.parquet`, `raw-observations.parquet` or `vault-metadata.csv`.

**F32–F35 correction verified.** On 400 random eligible rows × {30, 90}, `btc_beta_L`, `btc_residual_vol_L`, `beta_btc_return_L` and `abs_beta_btc_vol_L` match an independent `np.polyfit` OLS with intercept, residual d.o.f. n−2, and the same-window BTC log return / volatility to ≤ 9e-15, with identical availability. `_rolling_slope`/`_rolling_r2` no longer crash on a series that starts with data. `forward_log_growth_30` equals `log(P[d+30]/P[d])` to 2e-15; no eligible label at any horizon has a dropped catch-up return or a missing exit NAV; no label is non-null past the panel end.

### 1. Verdict

**Prospective collection: proceed.** The Phase 1 data-gap branch is complete and internally consistent: `historical_point_in_time_reconstructable: false`, `written_at_start` 2026-03-23, two-day publication clock with 35,901 masked source cells, and `prospective-collection-spec.md` now defines label entry at the first executable NAV at/after the recorded boundary. Nothing in the artefacts contradicts a previously fixed issue.

**Research gate: Phase 4 shortlist gate stays open; nothing may be frozen and no `hyper-ai.py` change is justified.** OOF Ridge: variance IC 0.756 / 0.604, downside 0.748 / 0.526, growth 0.002 / −0.207 (fold 1 has five matured dates). The vol-persistence IC survives excluding flat vaults (`vol_30` → `forward_variance_30` 0.80 both with and without the 1,260 zero-vol / 930 zero-label rows) and shifting entry to NAV_{T+2} changes headline ICs by ≤ 0.03. This is risk persistence, not an edge.

### 2. Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
|---|---|---|---|---|
| NB01 data/baseline | Panel, lag audit, `available_ts = last_written_at`, git SHA + dirty flag, own-file and source hashes all verified. | Still thin: no raw→TVL→eligible→labelled funnel, hand-checked rows, survivorship sensitivity or Stratwise display; `deposits_open`/`redemption_open` null for all 2,234 metadata rows; writes `config.json` not the plan's `manifest.json` (plan.md:350). Acceptable for the data-gap branch. | 1,293 d × 602; p95 lag 40.8 h; cohorts plausible. | Low |
| NB02 feature panel | Labels exact; generator causal on prefix check; 30-day history gate in force; BTC family now a true per-window OLS. **Fixed-window 90-day features do not enforce the plan's complete-elapsed-window rule (item 1).** | 82 + 6 + 49 as declared; manifest `minimum_observations` still generic (`lookback.clip(24)`); F13/F16 definition drift unchanged. | 64 dates, 227–271 eligible; 7.7 % of eligible rows have a dead-flat 30-day NAV. | Medium, non-blocking |
| NB03 IC screen | Purge, fold-local selection (labels ≤ `train_end` mature by `test_start`), equal date weighting, grid audit verified; min cross-section 160. | Exhaustive table present; bootstrap/null, incremental control vs `vol_30`/availability-only, horizon rule, terciles/upper bucket, cohort splits all deferred (Phase 4). `shortlist.json` horizon 30 is the default, not a selection. | Top cells `vol_10`/`ewm_return_vol_10` → forward variance ≈ 0.85; growth ≈ 0. `beta_btc_return_30` (−0.047) is now distinct from `btc_beta_30` (0.312); the 90-day pair is still an exact mirror (BTC 90-day return negative on every date). | Medium, deferred |
| NB04 replay | Abstention semantics match `_production_score`; cash is the coverage outcome. | A and C only; B/D correctly deferred. | Flat $150,000. | Low |

### 3. Defects and limitations

**Blocking:** none.

**Important — fix before any 90-day family or sizing input is frozen, not before collection**

1. **Fixed-window L-day features are computed on incomplete elapsed windows.** plan.md:146 requires "a complete elapsed L-day window for fixed-window features" with the 80 % coverage rule applied *independently*; `ic_research.py:213-218, 387-410` implement only the coverage rule (`min_periods = 0.8·L`). Of 10,306 eligible rows with `vol_90`, **2,388 (23 %) have only 72–89 days of observed history**; the same applies to `sharpe_90`, `sortino_90`, `downside_dev_90`, `max_dd_90`, `ulcer_90`, `worst_day_90`, `btc_residual_vol_90`, `tvl_*_90`, etc. Only `cagr_L` (via `shift(L)`) enforces the elapsed rule (7,912 rows, min history 90), so one "90-day family" has two admission rules, breaking the plan's common-row comparisons. Fold 1's shortlist contains five 90-day columns and `vol_90` is the replay sizing input. Not leakage, and ranks are robust, but the column names overstate the window (cf. plan.md:248 "do not call a 58-day expanding estimate CAGR-360"). One-line fix: mask each fixed-window feature where `observed_history_days < L`, or rename/document as "≥ 0.8·L".

**Pre-shadow freeze actions (not collection blockers)**

2. `claude-review-opus-09.md` is 0 bytes while README:7 and plan.md:390 already cite its verdict — the same pattern flagged for 07 and 08.
3. Scratchpad is untracked (`?? scratchpad/hyperliquid-ic/`); `config.json` records `code_revision` d40e06d with `git_worktree_dirty: true`, so the recorded revision cannot reproduce `ic_research.py` or the notebooks.
4. README/plan still do not state that diagnostic labels enter at NAV_T (`ic_research.py:298, 534`) while the information set corresponds to a T+2 decision (review 08 action 2). Measured effect ≤ 0.03 IC; the spec is correct for prospective data.
5. Spec omission: the vault's inception/creation timestamp *as reported at the snapshot* is not explicitly listed (only "address, chain and vault identity"); F26 vault age versus F27 observed history needs it.

**Acceptable, documented limitations**

- Two-day publication cutoff; April 2026 heavily masked; first eligible date 05-10; two underpowered folds; NAV-only replay; deposit availability unknown.
- `sharpe_L` floors a zero std to 1e-4 (`ic_research.py:390`) rather than NaN as plan.md:151 requires: 1,260 eligible rows with `vol_30 == 0` get Sharpe 0 while Sortino is NaN — inconsistent but rank-neutral.
- `control_nb36_cagr_sharpe` uses `fillna(0)` (NB03 cell 1): 7 cells over 3 dates, descriptive only.
- `time_since_last_nav` is 0 on every eligible row by construction; catch-up returns across >7-day gaps are dropped from trailing 90-day features on 10 rows / 2 vaults (0.1 %); 90-day features × 90-day labels have no valid cells (14 per feature, recorded).

### 4. Three minimal next actions before shadow decisions

1. **Start the collector now per the spec**, adding the per-snapshot inception timestamp field; commit the scratchpad and save this review into the empty `claude-review-opus-09.md` so the README/plan references resolve.
2. **Before freezing any family:** mask fixed-window features where `observed_history_days < L` (or relabel them), add the one-sentence NAV_T diagnostic-entry note to README/plan, rerun NB02→NB04 and re-freeze hashes — expect no change to the volatility-persistence conclusion.
3. **Run the deferred Phase 4 set on the corrected panel** — date-block bootstrap and intact-bundle null over the 86 × 21 grid, incremental Ridge versus `vol_30` and the availability-only control, zero-variance-label reporting, the predeclared horizon rule — and only then freeze horizon/model/allocator and open arms B/D, preferably on the first prospective snapshots.
