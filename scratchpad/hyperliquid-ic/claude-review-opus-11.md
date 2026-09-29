## Final read-only review — Hyperliquid vault IC research (Opus 5)

**Re-derived from `_artifacts/`, not the narrative.** 602 vaults × 647 two-day panel dates; 64 eligible dates 2026-05-10 → 2026-09-13; 16,425 eligible rows (227–271 per date); `min(observed_history_days)` = 30, max = 157. 82 catalogue predictors + 6 `ema_seed_weight_*` + 91 `__missing` flags; 86 screened predictors (82 + 4 controls) × 49 outcomes; **7,028 IC rows** (3,514 per panel) over **8,428** grid cells, 1,400 unavailable cells recorded (98 each for the ten 180/360-day columns and `time_since_last_nav`). Two purged folds (`train_end_used` 06-09 / 07-07; 14 + 5 matured test dates), **57 Ridge rows**. Both NB04 arms: 64 rows, $150,000 flat, `active=False`, 0 positions, `cagr_360` null on 100 % of eligible rows. `py_compile` passes; zero error outputs in all four notebooks (NB02 stderr is benign `FutureWarning`/`RuntimeWarning`); 40-vault full-generator prefix check passed (NB02 cell 5); all nine `files_sha256` incl. `btc-reference.parquet`, `research_source_sha256` and `hyper_ai_sha256` match current files. BTC 30-day family present on 16,424/16,425 eligible rows; 90-day family on 7,918 rows, zero rows with history < 90; `fresh_nav_coverage_90` present on 8,471 rows with history < 90 (exemption now honoured); `vol_30` never present below 30 days. `forward_log_growth_{30,60,90}` equals `log(P[T+H]/P[T])` on every valid eligible row (0 mismatches, 0 missing exits). Rank-then-pairwise-Pearson IC within 0.006 of exact Spearman on spot cells. No follower/leader/social/deposit-flow column in `features.parquet`, `labels.parquet`, `raw-observations.parquet` or `vault-metadata.csv`; `metadata` contributes only `start_date`, which is never later than the first raw observation (549 vaults checked).

### 1. Verdict

**Prospective collection: proceed.** Phase 1's data-gap branch is complete and internally consistent: `historical_point_in_time_reconstructable: false`; visible fresh cells are 0 until 2026-04-09 (the April break) and eligibility correctly begins 30 days later; in-window publication lag is p50 1.4 h / p95 4.8 h, so the two-day cutoff is a conservative, documented cache approximation (7,414 in-window rows written > 48 h late are masked, not used). The spec's label-entry rule (first executable NAV at/after the boundary) is correctly distinguished from the diagnostic `NAV_T` entry in README:9. One spec addition is warranted before the first snapshot (item 1 below); it does not change the verdict.

**Research gate: Phase 4 shortlist gate stays open; nothing may be frozen and no `hyper-ai.py` change is justified.** OOF Ridge rank IC: variance 0.66 / 0.77, downside 0.54 / 0.74, growth **0.07 / −0.18** (fold 1 = five dates). Top univariate cells (`vol_10`, `ewm_return_vol_10` → `forward_variance_7` ≈ 0.85, ICIR ~30) are volatility persistence. `shortlist.csv` is full-sample descriptive; `shortlist.json` horizon 30 is the default, not a selection.

### 2. Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
|---|---|---|---|---|
| NB01 data/baseline | Panel, lag audit, `available_ts = last_written_at`, BTC frozen + hashed, own-file hashes, git SHA + dirty flag all verified. No mixed null/non-null `written_at` within any vault-day, so `groupby.last()` picks the NAV row's own `written_at`. | Thin vs plan.md:59-67: no raw→TVL→eligible→labelled funnel, no explicit April-break table, no Stratwise row, no cleaning-version field (plan.md:59); `deposits_open`/`redemption_open` null for all rows. Acceptable for the data-gap branch. | 1,293 d × 602; cohorts plausible. | Low |
| NB02 feature panel | Labels exact; generator causal on prefix; 30-day history gate, elapsed masking, per-window OLS, coverage-control exemption, null-`available_ts` counting (43,288) all confirmed. | 82 + 6 + 49 as declared. Definition drift persists (F13 fraction, F16 Herfindahl, F25 std of log-diffs, F29 days not hours, F14/F15 blocks anchored to panel start with unbounded `ffill`, `ic_research.py:413-415`). | 64 dates; 1,260 eligible rows dead-flat over 30 days (Sharpe 0 / Sortino NaN). | Low |
| NB03 IC screen | Purge, fold-local selection, equal date weighting, `min_periods=10`, grid audit correct; min cross-section 148. | Exhaustive table present. Bootstrap/null, incremental control vs `vol_30`/availability-only, horizon rule, terciles/upper bucket, cohort splits, missing-outcome stress scenarios, `label_available_ts` columns — all deferred Phase 2/4 work. | 90-day-feature × 60/90-day-label cells rest on 4 dates; `time_since_last_nav` is 0 on every eligible row, hence its 98 unavailable cells. | Medium, deferred |
| NB04 replay | Abstention semantics match `_production_score` (`ic_research.py:761-770`); cash is the coverage outcome, `eligible_count` 227–271. | A and C only; B/D correctly deferred. | Flat $150,000, no trades. | Low |

### 3. Defects and limitations

**Blocking:** none.

**Important — amend the spec before the first snapshot (not a collection blocker)**

1. **The research NAV is a provider-repaired series, and its provenance is not captured.** In the HL cache, `share_price` ≠ `raw_share_price` on 1,486,290 of 1,495,896 rows (median |relative diff| 24 %, tail unbounded where raw ≈ 0); `hypercore_repair_status` is `approximated_pnl_nav` (487k), `approximated_pnl_nav_carried` (1.01M — always equal to the previous poll), `_lag_repaired` (268), `deferred_pnl_nav_outlier` (60), `_clipped`, `_wipe_out`. This is the "cleaning version" plan.md:59 requires freezing, yet `config.json` records none, NB01 cell 2 (line 40) drops these columns from `raw-observations.parquet`, `build_daily_panel` counts every poll as an observation (`ic_research.py:186-192`), and `prospective-collection-spec.md` lists per-poll `share_price` only. Current results are unaffected (99.9 % of in-window daily endpoints are non-carried `approximated_pnl_nav`, source `hf`, median 17 polls/day), but retroactive repairs are real (7,414 in-window rows published > 48 h late) and could rewrite history in a later bulk cache. Add to the spec: save `raw_share_price`, `hypercore_repair_status`, `hypercore_source` and the provider repair/cleaning version per poll; treat `_carried` rows as non-fresh in the loader.

**Pre-shadow freeze actions (documentation/provenance)**

2. `claude-review-opus-11.md` is 0 bytes while README:7 and plan.md:390 already cite its verdict; the scratchpad is untracked (`?? scratchpad/hyperliquid-ic/`) and `config.json` records `d40e06d` with `git_worktree_dirty: true`, so the recorded revision cannot reproduce the code.

**Acceptable, documented limitations**

- Two-day cutoff; zero visible cells 03-23 → 04-08; max observed history 157 d, so 180/360-day columns, `cagr_360`, the `>=360` cohort and all 90×90 cells are structurally unavailable and recorded; two underpowered folds; NAV-only replay; deposit availability unknown; diagnostic `NAV_T` entry vs the `T+2` information clock (README:9).
- BTC reference ends 2026-09-12, so the 09-13 BTC return is a forward-filled zero (`ic_research.py:471-472`) — final decision date only, no label affected; the spec already requires the completed bar per snapshot.
- `sharpe_L` floors zero std to 1e-4 (`ic_research.py:390`) while `sortino_L` returns NaN (`:394`) — inconsistent on the 1,260 flat rows, rank-neutral.
- `ema_seed_weight_*` counts fresh NAVs, not calendar EMA steps (`ic_research.py:513-514`) — diagnostic only.
- `control_nb36_cagr_sharpe` uses `fillna(0)` (NB03 cell 1) and is unavailable anyway.

### 4. Three minimal next actions before shadow decisions

1. **Start the collector now**, with one added spec bullet (item 1: per-poll `raw_share_price`, `hypercore_repair_status`, `hypercore_source`, provider repair version; `_carried` = non-fresh). In the same step commit the scratchpad, save this review into `claude-review-opus-11.md`, and rerun NB01 once so `config.json` records a clean revision.
2. **Record the cleaning provenance in the diagnostic panel** at the next rerun: keep the three repair columns in `raw-observations.parquet`, count `_carried` rows in NB01's audit, and add the repair-version string to `config.json`. No change in conclusions is expected.
3. **Run the deferred Phase 4 set on the corrected panel, preferably on the first prospective snapshots:** date-block bootstrap and intact-bundle null over the 86 × 21 grid, incremental Ridge versus `vol_30` and the availability-only control, zero-variance-label reporting, missing-outcome stress scenarios and the predeclared horizon rule — and only then freeze horizon/model/allocator and open arms B/D.
