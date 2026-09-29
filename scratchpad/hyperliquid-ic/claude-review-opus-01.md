# Claude Opus review

Review command: `claude --model opus --effort high --print --dangerously-skip-permissions`

Date: 2026-09-13

The CLI `opus` alias was used for the current Opus model. The review was read-only and covered the plan, shared research module, all four notebooks, README, and generated artefacts.

## Verdict

**Not safe to continue with as-is; it does not yet meet the plan.** The data contract, forward-label alignment and the 82-column inventory are structurally in place and no forbidden follower/leader/social/deposit-flow columns reach the predictors (only `share_price`, `total_assets`, `timestamp`, `written_at` leave `_normalise_raw`). But four defects in `ic_research.py` make the headline results unusable: Sortino/downside-deviation features are computed over negative days only and are ~0% populated, so the production control score is identically zero and both replay arms pick arbitrary vaults; two features leak future returns; the walk-forward has no label purge and a globally-selected shortlist; and the IC fast path never enforces the ten-vault minimum. Everything numeric is additionally descriptive with respect to publication time, because `available_ts` is built but never used. The NAV-only replay's negative result is an artefact of the zero-score ties plus double-charged fees, not evidence about either allocator.

## Notebook-by-notebook

| Notebook | Correctness | Plan coverage | Result sanity | Severity |
| --- | --- | --- | --- | --- |
| 01-data-and-baseline | Panel build correct; `available_ts` = `last_written_at` is recorded but unused downstream. `written_at_start` = 2026-03-23, so all earlier rows are bulk-backfilled. | Partial: freeze/hashes/lag audit done; no hand-checked rows, no future-perturbation test, no framework-parity comparison, no survivorship sensitivity, `manifest.json` replaced by `config.json`. Operational fields (`deposits_open`, `redemption_open`, `performance_fee`, `management_fee`) dropped although the plan needs them for eligibility/fee mode. | 602 vaults, 1,293 days, cohort table plausible. | Important |
| 02-feature-panel | Forward labels align correctly (entry NAV_T, exit NAV_{T+H}, verified synthetically). Sortino/downside_dev, ulcer, weekly features, time_underwater, EMA warm-up are wrong (details below). | 82 predictors + 49 targets match the inventory nominally, but 11 columns are effectively dead (9 at 0% coverage, 2 at 0.04%). Manifest lacks formula/min-obs/role. No terminal-NAV stress scenarios. Young-vault admission works: 14% of eligible rows are under 90 days old. | Labels have heavy tails (5% of 30-day log growth < -0.57, minimum -12): needs a closure/liquidation audit before use. | Blocking |
| 03-ic-screen | `corr()` uses `min_periods=1` so the >=10-vault rule is not enforced (4,536 of 7,084 rows have `min_n_cross_section<10`). Folds have no purge; shortlist chosen on all dates including test folds. | Partial: exhaustive IC table (3,542 of 4,214 cells per panel), gated/ungated views, ICIR, 2 Ridge folds. Absent: bootstrap, placebo null, terciles/upper basket, age-cohort split, controls-vs-family incremental test, horizon rule, `shortlist.json`. | Top ICs (~0.8, `vol_10`/`ewm_10` -> forward variance) are volatility persistence, the plan's control, not a new predictor; survives excluding flat vaults (0.78). Growth IC is approximately zero (OOF +0.16/-0.14). | Important |
| 04-allocation-validation | Both scores are all-zero on every date (checked 2026-06-03: 266 eligible, 0 non-zero for both arms), so selection is sort-order. Redemption fee is charged on buys and sells; stale holdings disappear from equity; CAGR includes years before the first eligible date. | Not the plan: no A-D decomposition, no 15%/10%/5%-young caps, no N_eff/beta buckets, adaptive arm is a rank blend the plan forbids. | -10.7% over 7 active months is approximately $11.6k fees on $9.3M turnover of a $150k book. Uninformative. | Blocking |

## Blocking defects

1. **Sortino and downside deviation average negative days only and require 24 negative days** — `ic_research.py:333,338`. `returns.where(returns < 0)` makes non-negative days NaN, so `rolling(min_periods=24)` needs 24 down days in 30. Coverage on eligible rows: `sortino_45` 0.0%, `sortino_30`/`downside_dev_30` 0.04%. Fix: `returns.clip(upper=0).pow(2).rolling(window, min_periods=mp).mean().pow(0.5)` (keeps NaN for missing days, zero for up days). The same pattern is already correct in the labels (`:429`).
2. **Production control is therefore identically zero** — `_production_score` (`:617`) and `control_prod_composite` in NB03 cell 1. `cagr_360` is 4.4% populated and `sortino_45` 0%, so `_fixed_inverse_variance_weights` (`:653`) picks `head(6)` of tied zeros. Fixed by (1); also treat all-zero cross-sections as “no signal -> hold cash” rather than tie-break selection.
3. **Adaptive replay score is also all-zero and is a forbidden rank blend** — `simulate_allocator` (`:713`): `sortino_30` rank is NaN -> whole sum NaN -> `fillna(0)`. Even when populated it averages cross-sectional ranks, which the plan explicitly rejects. Fix: drop the arm until NB03 freezes a score; if kept, use `.rank(pct=True)` on each term with NaN -> 0.5 and the frozen Ridge prediction instead.
4. **Replay accounting** — `:731,742`: redemption fee is applied to buys and sells (production charges redeemed capital only) -> use `sold_value` only; `:699-704,745`: holdings whose NAV is stale >7 days are removed from equity and from `holdings` (capital deleted) -> mark at last NAV with a stale flag and never drop; `summarise_backtest` (`:761`) should start the clock at the first eligible date (2026-02-09), not 2023-03-01.
5. **Future leakage in F14/F15** — `:352-353`. `resample("7D")` bins are labelled at the block start and `ffill` propagates a block that includes up to six future days. Synthetic check: perturbing returns after day 100 changed `positive_week_frac_90` from day 98. Fix: `weekly = returns.rolling(7, min_periods=7).sum()` then take blocks `weekly.shift(7*k)` for k = 0..12 anchored at T.

## Important defects

6. **No label purge in walk-forward and shortlist leakage** — `make_time_folds`/`walk_forward_ridge` (`:535-575`), NB03 cell 3. Training ends 2026-06-07, test starts 06-09, so 30-day training labels overlap the test window; the 12 Ridge inputs were chosen from IC over all 109 dates including both test folds. Fix: `train = frame[frame.date <= test_start - Timedelta(days=H)]`; build the shortlist from IC computed on `date <= train_end` per fold. Also `min_train_days=60` is 60 decision dates (approximately 120 calendar days), while plan.md and README call these “60-day folds”.
7. **Ten-vault minimum is not enforced in the fast IC path** — `compute_ic_table` (`:503`). Fix: `ranked.corr(method="pearson", min_periods=10)`; `min_n_cross_section` should be the pairwise count.
8. **Ulcer index is the forbidden nested-rolling construction** — `:342-343` (needs approximately 2L days; `ulcer_90` 34% coverage versus `max_dd_90` 72%). Fix: compute inside `_rolling_max_drawdown`'s window as `sqrt(mean((v/cummax(v)-1)^2))`.
9. **EMA/EWM require `span` observations** — `:405-406`, `min_periods=span`. Spans 270/360 are 0% populated, 180 is 17%. Plan: admit on the common 24/30 rule and expose seed weight. Fix: `min_periods=24` plus a `(1-alpha)**n_obs` seed-weight column.
10. **Downside label converts NaN returns to zero** — `:429,436` `.fillna(0)` before the forward mean, giving 48,509 downside labels versus 48,290 growth labels at H=7 (gaps counted as zero risk). Fix: `label_returns.clip(upper=0).pow(2)` and let `min_periods=window` govern.
11. **`time_underwater` is not F13** — `:355-357` is the fraction of days below the since-inception high, not calendar days since the in-window maximum. Rename or reimplement.
12. **Publication clock never applied** — `available_ts` is written by NB01 but `generate_feature_panels` keys everything on `timestamp` date. Minimal fix: mask `observations`/`nav` where `last_written_at > decision_ts` before feature generation and report the changed IC as the causality-repair delta.

## Acceptable limitations

- Pre-2026-03-23 rows are bulk-backfilled; no eligible decision exists before 2026-02-09 anyway. Sample sizes are correctly reported: 602 vaults, 647 dates, 109 eligible dates (all consecutive, February-September 2026, minimum 18 / median 262 vaults), 49 targets, 7 horizons. Only approximately 64 dates carry a 90-day label, so the “three non-overlapping blocks” goal is unmet for horizons >=60.
- `cagr_360`/`sharpe_360` sparsity is a genuine data limit (dense polling starts approximately February 2026), not a bug.
- `_rolling_slope`/`_rolling_r2` silently require full windows; `positive_gain_concentration` is a Herfindahl, not max/sum; `tvl_variability` is standard deviation of log-TVL changes; `beta_btc_return` uses time-varying beta. Minor definition drift.
- No deposit-availability or fee-mode eligibility; no terminal-NAV stress scenarios; feature manifest is thin.

## What is descriptive only

All of it. No result in NB03/NB04 is publication-time causal: approximately 21 of the 109 eligible dates precede the first `written_at`, and for the rest the panel ignores a p95 approximately 41-hour publication lag against a two-day decision step. The 0.8 variance ICs are trailing-volatility persistence (the plan's own control), the growth ICs are indistinguishable from zero, and the negative replay is a fee/tie-break artefact. None of these say anything about the production strategy.

## Next three actions

1. Apply fixes 1, 5, 8, 9, 10 in `ic_research.py`, re-run NB02, and confirm coverage of `sortino_45`, `downside_dev_*`, `ulcer_90`, and `ema_*_360` on eligible rows is non-trivial and the future-perturbation check passes for every column.
2. Re-run NB03 with `min_periods=10`, per-horizon label purge and fold-local shortlist; add the paired `vol_30` control-versus-family Ridge comparison on the same rows so risk-predictor claims are relative to the control named in the plan.
3. Re-run NB04 only as the production anchor with corrected score, redeem-only fees, stale-holding carry and the eligible-window clock; defer any adaptive arm until NB03 freezes a score and a horizon.
