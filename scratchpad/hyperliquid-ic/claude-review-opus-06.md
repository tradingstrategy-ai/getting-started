## Final post-fix review — Hyperliquid vault IC research (Opus 5, read-only)

All headline facts re-derived from `_artifacts/`, not from the narrative: 602 vaults / 647 panel dates / 64 eligible dates from 2026-05-10 to 2026-09-13 / 16,425 eligible rows (227–271 per date); 88 predictor columns = 82 catalogue + 6 `ema_seed_weight_*`, 91 `__missing` flags; 49 outcomes; 6,972 IC rows over 8,428 grid cells (1,456 unavailable, recorded); minimum cross-section 147; 2 folds (train 05-10→07-07 / test 07-09→08-04; train →08-04 / test 08-06→09-01), purge to `test_start − 30d` verified (06-09, 07-07); 57 Ridge rows = 19 matured test dates × 3 targets; both arms 64 rows at $150,000, `active=False` everywhere, 0 positions, 0 trades. Zero error outputs in all four notebooks; `py_compile` passes; 40-vault full-generator prefix check passed (NB02 cell 5); eligible rows have `observed_history_days ≥ 30`, `fresh_nav_coverage_30 ≥ 24`, `tvl ≥ 7,500`, no `cagr_360`/`cagr_180`/`sortino_360`. `forward_log_growth_{7,30}` equals `log(P[d+H]/P[d])` exactly on all 15,364 / 12,707 eligible labelled rows. No follower/leader/social/deposit-flow column exists in `features.parquet`, `vault-metadata.csv` or `_load_universe_json` (`ic_research.py:152-156`). `config.json` records `code_revision` d40e06d and `hyper_ai_sha256` 3ac527…, which matches the current file; the engine NaN→0 / `(-signal, pair_id)` sort at `hyper-ai.py:884-895` is as documented.

### 1. Verdict

**Proceed with prospective collection now.** The Phase 1 data-gap branch is complete: `historical_point_in_time_reconstructable: false`, first visible NAV under the two-day clock is 2026-04-09, April is 36.7% masked (May 8.0%, September 0.06%), and `prospective-collection-spec.md` now covers raw polls, BTC bar/hash, engine basket/weights, immutable snapshots and the prefix test.

**Phase 4 shortlist gate stays open.** Nothing blocks the collector, but no model, horizon or allocator may be frozen: bootstrap/null, incremental lift versus `vol_30`, the horizon rule and arms B/D are all still deferred, and fold 1 has only five matured test dates. The result remains volatility persistence (OOF variance IC 0.72, downside 0.68, growth −0.07 and sign-unstable), not an edge. No production change is justified.

### 2. Notebook table

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
|---|---|---|---|---|
| NB01 data/baseline | Panel, lag audit, `available_ts`, git SHA and `hyper-ai.py` hash correct. `files_sha256` is stale for NB02–04 outputs (it hashes every parquet present *before* the rerun — e.g. `features.parquet` recorded 58231afc…, actual 221e32c6…). Recorded SHA d40e06d does not contain the research code: `scratchpad/hyperliquid-ic/` is still untracked. | Thin (no funnel / hand-checked rows / survivorship sensitivity), unchanged from last review. | 1,293 days × 602 vaults; 247 currently eligible; p95 lag 40.8 h. | Low |
| NB02 feature panel | 30-day history gate applied (`ic_research.py:526`); causal on the full-generator prefix; labels exact. | 82 + 6 + 49 as declared; manifest still generic. | 64 dates, 227–271 eligible; max observed history 157 d, so no 180/360-day column exists on any eligible row. | Low |
| NB03 IC screen | Purge, fold-local selection, pairwise minimum, equal date weighting all verified. Stale comment "68 eligible decision dates" in cell 3 (artefact: 64). | Exhaustive table + grid audit present; bootstrap, null, incremental control, horizon rule, upper-bucket baskets deferred. | Fold 1 Ridge has 5 test dates; growth IC −0.00 / −0.26 across folds; `shortlist.json` horizon 30 is a default, not a selection. | Medium, deferred |
| NB04 replay | Accounting consistent; cash is the correct coverage outcome. Docstring/code mismatch in `_production_score` (below). | A and C only; B/D correctly deferred. | Flat $150,000, no trades. | Low now |

### 3. Remaining defects and limitations

**Blocking:** none.

**Important (fix before the first shadow decision, not before collection)**

1. **The freeze is not committed.** `config.json.code_revision` = d40e06d, but `git status` shows `?? scratchpad/hyperliquid-ic/`; the SHA cannot reproduce `ic_research.py`, the notebooks or the spec. The spec's "code/configuration hash" requirement is unmet for the research side.
2. **`_production_score` does not do what its docstring says.** `ic_research.py:715-723` claims per-vault abstention but ends with `.fillna(0.0)`; cash arises only because `_fixed_inverse_variance_weights`/`_adaptive_weights` return empty when `ranked.max() <= 0` (`:733`, `:755`). Identical result on this panel (all composites NaN→0), but once any vault reaches a 360-day leg (earliest ≈ 2027-04-04) a vault with one missing leg is ranked at zero, not abstained — neither the documented abstention nor engine parity. Low effort; no rerun needed now.

**Minor (next rerun)**

3. `config.json.files_sha256` mixes fresh NB01 outputs with stale NB02–04 outputs (NB01 cell 2, `ARTIFACTS.glob('*.parquet')`). Hash only NB01's outputs or write a final manifest after NB04.
4. NB03 cell 3 comment "68 eligible decision dates" contradicts the 64 in `eligibility.parquet`/`folds.json`.
5. `feature-manifest.csv` `minimum_observations` is `max(lookback, 24)` for every column (e.g. `vol_10` actually uses 8); formulas still point generically at the module.

**Acceptable documented limitations**

- Two-day publication cutoff with `available_ts = last_written_at` per day (conservative; masks a day whose last poll was a bulk re-ingestion).
- Labels use publication-masked NAV (`label_nav = nav.ffill(limit=7)`, `ic_research.py:490`); previously quantified as immaterial.
- `time_since_last_nav` is 0 on every eligible row by construction (eligibility requires a same-day mark).
- 64 dates, two underpowered folds, no long-history controls, NAV-only replay, ~1,300 pandas `FutureWarning`/`RuntimeWarning` lines (benign, not errors).

### 4. Three minimal next actions before shadow decisions

1. **Commit `scratchpad/hyperliquid-ic/` and rerun NB01 only**, so `code_revision` points at a commit containing `ic_research.py` and the spec, and restrict `files_sha256` to NB01's own outputs (or add a post-NB04 manifest step).
2. **Make `_production_score` return NaN when either leg is missing** (matching its docstring), keeping an explicit, separately labelled engine-parity path (NaN→0, `pair_id` tie-break, six-slot fill) for the later exact replay; fix the "68 dates" comment. No result change expected on this panel.
3. **Start the collector per `prospective-collection-spec.md` immediately and keep the model unfrozen.** As the panel grows, run the deferred Phase 4 items in order — paired date-block bootstrap and intact-bundle null against `vol_30`, fold-local incremental Ridge lift, then the predeclared horizon rule — before any B/D arm or shadow decision.
