from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).parent


def make(cells):
    nb = nbf.v4.new_notebook()
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}
    nb.cells = [nbf.v4.new_markdown_cell(s) if k == "markdown" else nbf.v4.new_code_cell(s) for k, s in cells]
    return nb


setup = r"""from pathlib import Path
import sys
import json
import math
import hashlib
import numpy as np
import pandas as pd

PROJECT_DIR = Path.cwd() / "scratchpad/hyperliquid-ic" if (Path.cwd() / "scratchpad/hyperliquid-ic").exists() else Path.cwd()
sys.path.insert(0, str(PROJECT_DIR))
ARTIFACTS = PROJECT_DIR / "_artifacts-stable-profit"
ARTIFACTS.mkdir(exist_ok=True)
REWRITE = PROJECT_DIR / "_artifacts-rewrite"
from ic_research import ResearchConfig, completed_daily_window, simulate_allocator, summarise_backtest, daily_feature_ic, write_json
from stable_profit import classification_metrics, paired_block_sharpe_samples, short_core_columns, simulate_stable_policy, walk_forward_loss_predictions, weekly_curve

CONFIG = ResearchConfig()
features = pd.read_parquet(REWRITE / "features.parquet")
labels = pd.read_parquet(REWRITE / "labels.parquet")
observations = pd.read_parquet(REWRITE / "observations.parquet")
evaluation_start, evaluation_end = completed_daily_window(observations)
features = features[features.date.between(evaluation_start - pd.Timedelta(days=CONFIG.training_history_days), evaluation_end)].copy()
labels = labels[labels.date.isin(features.date)].copy()
evaluation = features[features.date.between(evaluation_start, evaluation_end)].copy()
print("Stable-profit panel:", features.shape, "| dates:", features.date.nunique(), "| evaluation:", evaluation_start, "to", evaluation_end)
"""

nb05 = make(
    [
        ("markdown", "# Stable-profit selection\n\nPool diagnostics, the fixed severe-loss classifier and three pre-registered risk vetoes."),
        ("code", setup),
        (
            "code",
            r"""evaluation = features[features.date.between(evaluation_start, evaluation_end)].copy()
evaluation_labels = labels[labels.date.between(evaluation_start, evaluation_end)].copy()
incumbent = evaluation[(evaluation.nav_age_days <= 1) & evaluation.incumbent_return_gate.gt(-.16)].copy()
score_stats = incumbent.groupby("date").agg(pool=("address", "size"), finite_score=("incumbent_score", "count"), zero_score=("incumbent_score", lambda s: int((s.fillna(0) == 0).sum())), distinct_score=("incumbent_score", "nunique")).reset_index()
score_stats["tie_fraction"] = 1 - score_stats.distinct_score / score_stats.pool.clip(lower=1)
score_stats.to_csv(ARTIFACTS / "incumbent-score-saturation.csv", index=False)

common = evaluation.merge(evaluation_labels[["date", "address", "forward_log_growth_raw_30"]], on=["date", "address"], how="inner")
common = common[common.forward_log_growth_raw_30.notna() & common.interval_downside_dev_30.notna()].copy()
common["downside_quintile"] = common.groupby("date").interval_downside_dev_30.transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) + 1 if len(s) >= 5 else np.nan)
common["incumbent_neighbourhood"] = common.incumbent_score.notna() | common.incumbent_return_gate.gt(-.16)
q = common.groupby("downside_quintile", observed=False).agg(rows=("address", "size"), dates=("date", "nunique"), mean_growth=("forward_log_growth_raw_30", "mean"), loss_probability=("forward_log_growth_raw_30", lambda s: float((s < math.log(.9)).mean()))).reset_index()
q.to_csv(ARTIFACTS / "downside-quintile-forward.csv", index=False)
common[common.incumbent_neighbourhood].groupby("downside_quintile", observed=False).agg(rows=("address", "size"), mean_growth=("forward_log_growth_raw_30", "mean"), loss_probability=("forward_log_growth_raw_30", lambda s: float((s < math.log(.9)).mean()))).reset_index().to_csv(ARTIFACTS / "downside-quintile-incumbent-neighbourhood.csv", index=False)

beta = common.dropna(subset=["btc_beta_30", "interval_downside_dev_30"]).copy()
beta["risk_q"] = beta.groupby("date").interval_downside_dev_30.transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=False) + 1 if len(s) >= 3 else np.nan)
beta["abs_beta_q"] = beta.groupby("date").btc_beta_30.transform(lambda s: pd.qcut(s.abs().rank(method="first"), 3, labels=False) + 1 if len(s) >= 3 else np.nan)
beta.groupby(["risk_q", "abs_beta_q"], observed=False).agg(rows=("address", "size"), mean_growth=("forward_log_growth_raw_30", "mean"), loss_probability=("forward_log_growth_raw_30", lambda s: float((s < math.log(.9)).mean()))).reset_index().to_csv(ARTIFACTS / "risk-beta-double-sort.csv", index=False)

cohorts = evaluation.copy()
cohorts["history_cohort"] = pd.cut(cohorts.available_history_days, [-np.inf, 7, 14, 30, 90, 180, 360, np.inf], labels=["<7", "7-13", "14-29", "30-89", "90-179", "180-359", "360+"], right=False)
cohorts["sampling_cohort"] = np.select([cohorts.is_sparse_prediction.fillna(False), cohorts.last_interval_days.gt(2), cohorts.last_interval_days.gt(1)], ["weekly-plus", "irregular", "two-day"], default="daily")
cohorts.groupby(["history_cohort", "sampling_cohort"], observed=False).agg(rows=("address", "size"), dates=("date", "nunique"), vaults=("address", "nunique"), median_nav_age=("nav_age_days", "median")).reset_index().to_csv(ARTIFACTS / "age-sampling-cohorts.csv", index=False)
pd.DataFrame([{"horizon": h, "feature_rows": len(features), "raw_growth_labels": int(labels[f"forward_log_growth_raw_{h}"].notna().sum()), "downside_labels": int(labels[f"forward_downside_semivariance_{h}"].notna().sum()), "unique_outcomes": int(labels[f"outcome_id_{h}"].nunique())} for h in CONFIG.forecast_horizons]).to_csv(ARTIFACTS / "label-attrition.csv", index=False)
display(score_stats.describe())
display(q)

""",
        ),
        (
            "code",
            r"""core = short_core_columns(features)
predictions = walk_forward_loss_predictions(features, labels, feature_columns=core, horizon=30, evaluation_dates=pd.DatetimeIndex(sorted(evaluation.date.unique())), min_train_dates=60, c=1.0)
predictions.to_parquet(ARTIFACTS / "loss-predictions-30.parquet", index=False)
write_json(ARTIFACTS / "loss-classifier-metrics.json", classification_metrics(predictions))
calibration = predictions[(predictions.status == "predicted") & predictions.loss_probability.notna() & predictions.actual_loss.notna()].copy()
calibration["probability_bin"] = pd.qcut(calibration.loss_probability.rank(method="first"), 10, labels=False) + 1 if len(calibration) >= 10 else np.nan
calibration.groupby("probability_bin", observed=False).agg(rows=("address", "size"), mean_probability=("loss_probability", "mean"), realised_loss_rate=("actual_loss", "mean"), mean_growth=("actual", "mean")).reset_index().to_csv(ARTIFACTS / "loss-calibration.csv", index=False)
display(pd.DataFrame([classification_metrics(predictions)]))

# Compare all three veto scores on identical finite rows and retain the
# outcome-free permutation controls used by the plan.
finite_rows = common.dropna(subset=["interval_downside_dev_30", "btc_beta_30"]).merge(
    predictions[["date", "address", "loss_probability"]], on=["date", "address"], how="inner"
)
finite_rows["abs_btc_beta_30"] = finite_rows.btc_beta_30.abs()
tail_rows = []
for date, group in finite_rows.groupby("date", sort=True):
    count = math.floor(.2 * len(group))
    if count < 1:
        continue
    row = {"date": date, "rows": len(group), "excluded_rows": count}
    for name, score in [("a1", "interval_downside_dev_30"), ("a2", "loss_probability"), ("a3", "abs_btc_beta_30")]:
        selected = group.sort_values([score, "address"], ascending=[False, True], kind="stable").head(count)
        row[f"{name}_tail_growth"] = float(selected.forward_log_growth_raw_30.mean())
        row[f"{name}_tail_loss_probability"] = float((selected.forward_log_growth_raw_30 < math.log(.9)).mean())
    tail_rows.append(row)
matched = pd.DataFrame(tail_rows)
matched.to_csv(ARTIFACTS / "matched-finite-veto-rows.csv", index=False)
rng = np.random.default_rng(41)
null_rows = []
for draw in range(20):
    selected = []
    for _, group in finite_rows.groupby("date"):
        count = math.floor(.2 * len(group))
        if count:
            selected.extend(rng.choice(group.index.to_numpy(), size=count, replace=False))
    sample = finite_rows.loc[selected]
    null_rows.append({"draw": draw, "excluded_rows": len(sample), "excluded_mean_growth": sample.forward_log_growth_raw_30.mean(), "excluded_loss_probability": float((sample.forward_log_growth_raw_30 < math.log(.9)).mean()) if len(sample) else np.nan})
pd.DataFrame(null_rows).to_csv(ARTIFACTS / "veto-permutation-null.csv", index=False)
diagnostic_loss_metrics = []
for horizon in (14, 45):
    diagnostic = walk_forward_loss_predictions(
        features, labels, feature_columns=core, horizon=horizon,
        evaluation_dates=pd.DatetimeIndex(sorted(evaluation.date.unique())),
        min_train_dates=60, c=1.0,
    )
    diagnostic.to_parquet(ARTIFACTS / f"loss-predictions-{horizon}.parquet", index=False)
    diagnostic_loss_metrics.append({"horizon": horizon, **classification_metrics(diagnostic)})
pd.DataFrame(diagnostic_loss_metrics).to_csv(ARTIFACTS / "loss-classifier-horizon-sensitivities.csv", index=False)
""",
        ),
        (
            "code",
            r"""base = evaluation.copy()
a1_veto_score = base.interval_downside_dev_30.copy()
zero_measured_downside = base.observed_interval_count_30.ge(3) & a1_veto_score.isna()
a1_veto_score.loc[zero_measured_downside] = 0.0
policy_inputs = {
    "A0": (None, None),
    "A1": (base[["date", "address"]].assign(veto_score=a1_veto_score), "veto_score"),
    "A2": (predictions[["date", "address", "loss_probability"]].rename(columns={"loss_probability": "veto_score"}), "veto_score"),
    "A3": (base[["date", "address"]].assign(veto_score=base.btc_beta_30.abs()), "veto_score"),
}
curves, trades, pools, rows = {}, {}, {}, []
for name, (scores, veto_column) in policy_inputs.items():
    curve, trade, pool = simulate_stable_policy(base, observations, policy_name=name, veto_scores=scores, config=CONFIG, max_positions=6, veto_feature=veto_column, veto_fraction=.20)
    curves[name], trades[name], pools[name] = curve, trade, pool
    curve.to_parquet(ARTIFACTS / f"equity-{name}.parquet", index=False)
    trade.to_parquet(ARTIFACTS / f"trades-{name}.parquet", index=False)
    pool.to_parquet(ARTIFACTS / f"pool-{name}.parquet", index=False)
    row = summarise_backtest(curve)
    row.update({"arm": name, "veto_rows": int(pool.vetoed.sum()) if not pool.empty else 0, "veto_active_dates": int(trade.veto_active.sum()) if not trade.empty else 0})
    rows.append(row)
metrics = pd.DataFrame(rows).set_index("arm")
metrics.to_csv(ARTIFACTS / "primary-policy-metrics.csv")
pd.concat({name: curve.set_index("date").equity for name, curve in curves.items()}, axis=1).to_parquet(ARTIFACTS / "primary-equity-comparison.parquet")
display(metrics)
""",
        ),
        (
            "code",
            r"""old_curve, old_trades = simulate_allocator(base, pd.DataFrame(columns=["date", "address", "prediction"]), observations=observations, config=CONFIG, mode="incumbent", max_positions=6)
new_curve = curves["A0"].set_index("date").reindex(old_curve.date).reset_index()
parity = {"rows_old": int(len(old_curve)), "rows_new": int(len(new_curve)), "max_abs_equity_difference": float(np.nanmax(np.abs(old_curve.equity.to_numpy() - new_curve.equity.to_numpy()))), "max_abs_cash_difference": float(np.nanmax(np.abs(old_curve.cash.to_numpy() - new_curve.cash.to_numpy()))), "old_trades": int(len(old_trades)), "new_trades": int(len(trades["A0"])), "same_dates": bool(old_curve.date.equals(new_curve.date))}
write_json(ARTIFACTS / "no-op-parity.json", parity)
print(parity)
assert parity["max_abs_equity_difference"] < 1e-6
assert parity["max_abs_cash_difference"] < 1e-6
""",
        ),
    ]
)

nb06 = make(
    [
        ("markdown", "# Repeatability and direction\n\nBounded gain concentration, sampling and BTC-direction diagnostics. These features remain diagnostic."),
        ("code", setup),
        (
            "code",
            r"""obs = observations.sort_values(["address", "timestamp"]).copy()
obs["prev_timestamp"] = obs.groupby("address").timestamp.shift()
obs["prev_price"] = obs.groupby("address").share_price.shift()
obs["duration_days"] = (obs.timestamp - obs.prev_timestamp).dt.total_seconds() / 86400
obs["log_return"] = np.log(obs.share_price / obs.prev_price)
obs = obs[obs.duration_days.gt(0)].copy()
by_address = {address: group.reset_index(drop=True) for address, group in obs.groupby("address", sort=False)}
rows = []
for row in features.itertuples(index=False):
    history = by_address.get(row.address)
    if history is None:
        continue
    end = pd.Timestamp(row.last_observation_ts)
    values = history[history.timestamp <= end]
    item = {"date": row.date, "address": row.address}
    for window in (30, 60):
        subset = values[values.timestamp > end - pd.Timedelta(days=window)]
        returns = subset.log_return.to_numpy(dtype=float)
        positive = returns[returns > 0]
        total = positive.sum()
        item[f"gain_share_{window}"] = float(positive.max() / total) if len(positive) and total > 0 else (0.0 if len(positive) == 0 and len(returns) >= 4 else np.nan)
        item[f"top3_gain_share_{window}"] = float(np.sort(positive)[-3:].sum() / total) if len(positive) >= 4 and total > 0 else np.nan
        item[f"growth_ex_best_{window}"] = float(returns.sum() - (positive.max() if len(positive) else 0)) if len(returns) else np.nan
        item[f"negative_fraction_{window}"] = float(np.mean(returns < 0)) if len(returns) >= 4 else np.nan
        item[f"interval_count_{window}"] = int(len(returns))
        item[f"covered_days_{window}"] = float(subset.duration_days.sum()) if len(returns) else 0.0
    rows.append(item)
bounded = pd.DataFrame(rows)
bounded.to_parquet(ARTIFACTS / "bounded-path-features.parquet", index=False)
print("Bounded path diagnostics:", bounded.shape)
""",
        ),
        (
            "code",
            r"""merged = features[["date", "address", "tvl_current", "observed_interval_count_30", "interval_downside_dev_30", "daily_vol_30", "btc_beta_30"]].merge(bounded, on=["date", "address"], how="inner").merge(labels[["date", "address", "forward_log_growth_raw_30"]], on=["date", "address"], how="inner")
merged = merged[merged.date.between(evaluation_start, evaluation_end)].copy()
rows = []
for feature in ["gain_share_30", "top3_gain_share_30", "growth_ex_best_30", "negative_fraction_30", "btc_beta_30", "gain_share_60", "top3_gain_share_60", "growth_ex_best_60", "negative_fraction_60"]:
    data = merged[["date", "address", feature, "forward_log_growth_raw_30", "observed_interval_count_30"]].rename(columns={"forward_log_growth_raw_30": "target"})
    data["eligible"] = True
    ic = daily_feature_ic(data, data, feature=feature, target="target", sign=1.0)
    if not ic.empty:
        rows.append({"feature": feature, "dates": len(ic), "mean_rank_ic": ic.rank_ic.mean(), "median_rank_ic": ic.rank_ic.median(), "positive_date_fraction": float((ic.rank_ic > 0).mean())})
diagnostic_ic = pd.DataFrame(rows).sort_values("mean_rank_ic", ascending=False)
diagnostic_ic.to_csv(ARTIFACTS / "bounded-diagnostic-ic.csv", index=False)
display(diagnostic_ic)
""",
        ),
        (
            "code",
            r"""base_index = features.set_index(["date", "address"])
merged["available_history_days"] = base_index.reindex(merged.set_index(["date", "address"]).index).available_history_days.to_numpy()
merged["btc_beta_abs"] = merged.btc_beta_30.abs()
merged["history_cohort"] = pd.cut(merged.available_history_days, [-np.inf, 30, 90, 180, 360, np.inf], labels=["<30", "30-89", "90-179", "180-359", "360+"], right=False)
cohorts = merged.groupby("history_cohort", observed=False).agg(rows=("address", "size"), mean_growth=("forward_log_growth_raw_30", "mean"), loss_probability=("forward_log_growth_raw_30", lambda s: float((s < math.log(.9)).mean())), mean_beta_abs=("btc_beta_abs", "mean")).reset_index()
cohorts.to_csv(ARTIFACTS / "direction-sampling-cohorts.csv", index=False)
family_columns = short_core_columns(features) + [c for c in ["gain_share_30", "top3_gain_share_30", "growth_ex_best_30", "negative_fraction_30"] if c in bounded]
family_features = features.merge(bounded, on=["date", "address"], how="left")
family_predictions = walk_forward_loss_predictions(family_features, labels, feature_columns=family_columns, horizon=30, evaluation_dates=pd.DatetimeIndex(sorted(evaluation.date.unique())), min_train_dates=60, c=1.0)
family_predictions.to_parquet(ARTIFACTS / "family-loss-predictions-30.parquet", index=False)
write_json(ARTIFACTS / "family-loss-classifier-metrics.json", classification_metrics(family_predictions))
display(cohorts)
""",
        ),
    ]
)

nb07 = make(
    [
        ("markdown", "# Stable-profit validation\n\nWeekly valuation, young access, sizing and a conservative shortlist verdict."),
        ("code", setup),
        (
            "code",
            r"""primary_metrics = pd.read_csv(ARTIFACTS / "primary-policy-metrics.csv", index_col="arm")
curves = {arm: pd.read_parquet(ARTIFACTS / f"equity-{arm}.parquet") for arm in ["A0", "A1", "A2", "A3"]}
weekly_rows = []
for arm, curve in curves.items():
    weekly = weekly_curve(curve)
    weekly.to_parquet(ARTIFACTS / f"weekly-equity-{arm}.parquet", index=False)
    row = summarise_backtest(weekly, periods_per_year=52.0)
    row["arm"] = arm
    weekly_rows.append(row)
weekly_metrics = pd.DataFrame(weekly_rows).set_index("arm")
weekly_metrics.to_csv(ARTIFACTS / "weekly-policy-metrics.csv")
display(primary_metrics[["cagr", "volatility", "sharpe", "max_drawdown", "mean_cash_fraction", "mean_stale_positions", "mean_carried_positions"]])
display(weekly_metrics[["cagr", "volatility", "sharpe", "max_drawdown"]])
classifier_metrics = json.loads((ARTIFACTS / "loss-classifier-metrics.json").read_text())
family_classifier_metrics = json.loads((ARTIFACTS / "family-loss-classifier-metrics.json").read_text())
a3_trades = pd.read_parquet(ARTIFACTS / "trades-A3.parquet")
a3_active = a3_trades[a3_trades.veto_active]
a3_active_start = a3_active.date.min() if not a3_active.empty else pd.NaT
a3_active_end = a3_active.date.max() if not a3_active.empty else pd.NaT
btc_reference = pd.read_parquet(REWRITE / "btc-reference.parquet")
btc_reference.index = pd.to_datetime(btc_reference.index).tz_localize(None).normalize()
btc_reference = btc_reference[~btc_reference.index.duplicated(keep="last")].sort_index()
btc_regime = pd.DataFrame({"date": btc_reference.index, "btc_return": btc_reference.close.pct_change().to_numpy()})
btc_regime["btc_regime"] = np.select(
    [btc_regime.btc_return.gt(0), btc_regime.btc_return.lt(0)],
    ["up", "down"],
    default=pd.NA,
)
regime_rows = []
for arm, curve in curves.items():
    joined = curve.merge(btc_regime[["date", "btc_regime"]], on="date", how="inner")
    for regime, subset in joined.dropna(subset=["btc_regime"]).groupby("btc_regime"):
        returns = subset["return"].dropna()
        deviation = returns.std(ddof=1)
        regime_rows.append({
            "arm": arm,
            "btc_regime": regime,
            "start": str(subset.date.min()),
            "end": str(subset.date.max()),
            "dates": int(subset.date.nunique()),
            "return_observations": int(len(returns)),
            "mean_return": float(returns.mean()) if len(returns) else np.nan,
            "volatility": float(deviation * math.sqrt(365.0)) if pd.notna(deviation) else np.nan,
            "sharpe": float(returns.mean() / deviation * math.sqrt(365.0)) if pd.notna(deviation) and deviation > 0 else np.nan,
            "mean_positions": float(subset.n_positions.mean()),
            "mean_cash_fraction": float((subset.cash / subset.equity).mean()),
            "mean_stale_positions": float(subset.stale_positions.mean()),
            "mean_carried_positions": float(subset.carried_positions.mean()),
        })
pd.DataFrame(regime_rows).to_csv(ARTIFACTS / "btc-regime-policy-metrics.csv", index=False)
""",
        ),
        (
            "code",
            r"""features_young = features.copy()
features_young["young_proxy"] = features_young.interval_log_growth_30 / features_young.observed_covered_days_30.replace(0, np.nan)
features_young["young_proxy"] = features_young["young_proxy"].combine_first(features_young.interval_log_growth_14 / features_young.observed_covered_days_14.replace(0, np.nan)).combine_first(features_young.interval_log_growth_7 / features_young.observed_covered_days_7.replace(0, np.nan))
features_young["young_score"] = features_young.incumbent_score

# Freeze the empirical mapping at each month boundary and give dates equal
# weight.  The CDF and quantile arrays are precomputed once per month; doing a
# groupby for every young row makes the otherwise small diagnostic needlessly
# expensive on the 100k-row panel.
for period in sorted(features_young.date.dt.to_period("M").unique()):
    month_start = pd.Timestamp(period.start_time)
    prior = features_young[features_young.date < month_start]
    current = features_young.date.dt.to_period("M").eq(period) & features_young.available_history_days.lt(90) & features_young.incumbent_score.isna()
    if not current.any():
        continue
    proxy_groups = [np.sort(group.to_numpy(dtype=float)) for _, group in prior.dropna(subset=["young_proxy"]).groupby("date")["young_proxy"] if len(group)]
    score_groups = [group.to_numpy(dtype=float) for _, group in prior.dropna(subset=["incumbent_score"]).groupby("date")["incumbent_score"] if len(group)]
    if prior.dropna(subset=["young_proxy"]).date.nunique() < 20 or prior.dropna(subset=["incumbent_score"]).date.nunique() < 20 or not proxy_groups or not score_groups:
        continue
    indices = features_young.index[current]
    values = features_young.loc[indices, "young_proxy"].to_numpy(dtype=float)
    valid = np.isfinite(values)
    if not valid.any():
        continue
    ranks = np.zeros(valid.sum(), dtype=float)
    for group in proxy_groups:
        ranks += np.searchsorted(group, values[valid], side="right") / len(group)
    ranks /= len(proxy_groups)
    mapped = np.zeros(len(ranks), dtype=float)
    for group in score_groups:
        mapped += np.quantile(group, np.clip(ranks, 0, 1))
    mapped /= len(score_groups)
    mapped[values[valid] <= 0] = 0.0
    features_young.loc[indices[valid], "young_score"] = mapped
features_young["young_score"] = features_young["young_score"].fillna(0.0)
features_young = features_young[features_young.date.between(evaluation_start, evaluation_end)].copy()
predictions = pd.read_parquet(ARTIFACTS / "loss-predictions-30.parquet")
a2_scores = predictions[["date", "address", "loss_probability"]].rename(columns={"loss_probability": "veto_score"})
young_results, young_trades, young_pools = {}, {}, {}
for name, scores, veto in [("A0-young", None, None), ("A2-young", a2_scores, "veto_score")]:
    curve, trade, pool = simulate_stable_policy(features_young, observations, policy_name=name, veto_scores=scores, config=CONFIG, max_positions=6, veto_feature=veto, veto_fraction=.20, young_extension=True)
    young_results[name], young_trades[name], young_pools[name] = curve, trade, pool
    curve.to_parquet(ARTIFACTS / f"equity-{name}.parquet", index=False)
    trade.to_parquet(ARTIFACTS / f"trades-{name}.parquet", index=False)
    pool.to_parquet(ARTIFACTS / f"pool-{name}.parquet", index=False)

# Match A0-young's final capped allocation to A2-young's realised deployment
# fraction so cash dilution is separated from the loss-veto effect.
a2_deployment = young_trades["A2-young"].set_index("date")["invested_fraction"]
cash_curve, cash_trade, cash_pool = simulate_stable_policy(
    features_young, observations, policy_name="A0-young-cash-matched", config=CONFIG,
    max_positions=6, young_extension=True, matched_invested_fraction_by_date=a2_deployment,
)
young_results["A0-young-cash-matched"] = cash_curve
young_trades["A0-young-cash-matched"], young_pools["A0-young-cash-matched"] = cash_trade, cash_pool
cash_curve.to_parquet(ARTIFACTS / "equity-A0-young-cash-matched.parquet", index=False)
cash_trade.to_parquet(ARTIFACTS / "trades-A0-young-cash-matched.parquet", index=False)
cash_pool.to_parquet(ARTIFACTS / "pool-A0-young-cash-matched.parquet", index=False)
young_metrics = pd.DataFrame([dict(summarise_backtest(curve), arm=name) for name, curve in young_results.items()]).set_index("arm")
young_metrics.to_csv(ARTIFACTS / "young-policy-metrics.csv")
display(young_metrics[["cagr", "volatility", "sharpe", "max_drawdown", "mean_cash_fraction"]])
young_attribution = young_pools["A0-young"].merge(
    features[["date", "address", "is_sparse_prediction", "last_interval_days"]],
    on=["date", "address"], how="left",
).merge(labels[["date", "address", "forward_log_growth_raw_30"]], on=["date", "address"], how="left")
young_attribution["age_cohort"] = pd.cut(
    young_attribution.available_history_days,
    [-np.inf, 30, 90, 180, 360, np.inf],
    labels=["<30", "30-89", "90-179", "180-359", "360+"], right=False,
)
young_attribution["sampling_cohort"] = np.select(
    [young_attribution.is_sparse_prediction.fillna(False), young_attribution.last_interval_days.gt(2)],
    ["weekly-plus", "irregular"], default="daily",
)
selected_young = young_attribution[young_attribution.selected].copy()
selected_young["gross_pnl_proxy"] = selected_young.target_dollars * np.expm1(selected_young.forward_log_growth_raw_30)
young_selection_summary = selected_young.groupby(["age_cohort", "sampling_cohort"], observed=False).agg(
    selected_rows=("address", "size"),
    selected_vaults=("address", "nunique"),
    target_dollars=("target_dollars", "sum"),
    gross_pnl_proxy=("gross_pnl_proxy", "sum"),
    loss_probability=("forward_log_growth_raw_30", lambda s: float((s < math.log(.9)).mean())),
).reset_index()
young_selection_summary.to_csv(ARTIFACTS / "young-selection-attribution.csv", index=False)

# Dynamic accepted-dollar sensitivity: cap each arm at its own current
# pre-cap requested allocation, so greedy redistribution cannot create a new
# concentration as equity changes.
cap_results, cap_trades, cap_pools = {}, {}, {}
for name, scores, veto in [("A0-cap", None, None), ("A2-cap", a2_scores, "veto_score")]:
    curve, trade, pool = simulate_stable_policy(
        evaluation, observations, policy_name=name, veto_scores=scores,
        config=CONFIG, max_positions=6, veto_feature=veto, veto_fraction=.20,
        cap_at_requested_allocation=True,
    )
    cap_results[name], cap_trades[name], cap_pools[name] = curve, trade, pool
    curve.to_parquet(ARTIFACTS / f"equity-{name}.parquet", index=False)
    trade.to_parquet(ARTIFACTS / f"trades-{name}.parquet", index=False)
    pool.to_parquet(ARTIFACTS / f"pool-{name}.parquet", index=False)

# Sizing cash-matched A0: scale final capped weights towards A2-cap's realised
# investment fraction for the same A0 ranking and dynamic cap policy.
a2_cap_deployment = cap_trades["A2-cap"].set_index("date")["invested_fraction"]
cash_curve, cash_trade, cash_pool = simulate_stable_policy(
    evaluation, observations, policy_name="A0-cap-cash-matched", config=CONFIG,
    max_positions=6, cap_at_requested_allocation=True,
    matched_invested_fraction_by_date=a2_cap_deployment,
)
cap_results["A0-cap-cash-matched"], cap_trades["A0-cap-cash-matched"], cap_pools["A0-cap-cash-matched"] = cash_curve, cash_trade, cash_pool
cash_curve.to_parquet(ARTIFACTS / "equity-A0-cap-cash-matched.parquet", index=False)
cash_trade.to_parquet(ARTIFACTS / "trades-A0-cap-cash-matched.parquet", index=False)
cash_pool.to_parquet(ARTIFACTS / "pool-A0-cap-cash-matched.parquet", index=False)

# Contributor removal is a diagnostic, not a new candidate.  Remove the
# largest cumulative selected-capital address from the beginning and rerun.
leader = cap_pools["A0-cap"].groupby("address").target_dollars.sum().idxmax()
leader_curve, leader_trade, leader_pool = simulate_stable_policy(
    evaluation[evaluation.address.ne(leader)].copy(), observations,
    policy_name="A0-cap-without-leader", config=CONFIG, max_positions=6,
    cap_at_requested_allocation=True,
)
cap_results["A0-cap-without-leader"], cap_trades["A0-cap-without-leader"], cap_pools["A0-cap-without-leader"] = leader_curve, leader_trade, leader_pool
leader_curve.to_parquet(ARTIFACTS / "equity-A0-cap-without-leader.parquet", index=False)
leader_trade.to_parquet(ARTIFACTS / "trades-A0-cap-without-leader.parquet", index=False)
leader_pool.to_parquet(ARTIFACTS / "pool-A0-cap-without-leader.parquet", index=False)
a2_leader = cap_pools["A2-cap"].groupby("address").target_dollars.sum().idxmax()
a2_leader_curve, a2_leader_trade, a2_leader_pool = simulate_stable_policy(
    evaluation[evaluation.address.ne(a2_leader)].copy(), observations,
    policy_name="A2-cap-without-leader", veto_scores=a2_scores, config=CONFIG,
    max_positions=6, veto_feature="veto_score", veto_fraction=.20,
    cap_at_requested_allocation=True,
)
cap_results["A2-cap-without-leader"], cap_trades["A2-cap-without-leader"], cap_pools["A2-cap-without-leader"] = a2_leader_curve, a2_leader_trade, a2_leader_pool
a2_leader_curve.to_parquet(ARTIFACTS / "equity-A2-cap-without-leader.parquet", index=False)
a2_leader_trade.to_parquet(ARTIFACTS / "trades-A2-cap-without-leader.parquet", index=False)
a2_leader_pool.to_parquet(ARTIFACTS / "pool-A2-cap-without-leader.parquet", index=False)
cap_metrics = pd.DataFrame([dict(summarise_backtest(curve), arm=name) for name, curve in cap_results.items()]).set_index("arm")
cap_metrics.to_csv(ARTIFACTS / "accepted-dollar-cap-metrics.csv")
display(cap_metrics[["cagr", "volatility", "sharpe", "max_drawdown", "mean_cash_fraction"]])
def cash_match_diagnostics(trade, reference):
    joined = trade[["date", "invested_fraction", "matched_invested_fraction"]].merge(
        reference[["date", "invested_fraction"]].rename(columns={"invested_fraction": "reference_invested_fraction"}),
        on="date", how="inner",
    )
    gap = joined.invested_fraction - joined.reference_invested_fraction
    positive_reference = joined.reference_invested_fraction.gt(1e-9)
    return {
        "dates": int(len(joined)),
        "actual_mean_invested_fraction": float(joined.invested_fraction.mean()),
        "reference_mean_invested_fraction": float(joined.reference_invested_fraction.mean()),
        "mean_gap": float(gap.mean()),
        "mean_absolute_gap": float(gap.abs().mean()),
        "cap_limited_dates": int((positive_reference & gap.lt(-1e-9)).sum()),
        "matched_dates": int((positive_reference & gap.abs().le(1e-9)).sum()),
        "zero_reference_dates": int((~positive_reference).sum()),
    }
write_json(ARTIFACTS / "cap-diagnostic-manifest.json", {
    "leader_address": leader,
    "candidate_leader_address": a2_leader,
    "cap_definition": "current arm pre-cap requested weights times current investable budget",
    "cash_match_reference": "A2-cap realised invested fraction",
    "cash_match_method": "scale final capped weights down when A0 cannot exceed the reference; cap-limited dates remain below it",
    "cap_cash_match": cash_match_diagnostics(cap_trades["A0-cap-cash-matched"], cap_trades["A2-cap"]),
    "young_cash_match": cash_match_diagnostics(young_trades["A0-young-cash-matched"], young_trades["A2-young"]),
})
""",
        ),
        (
            "code",
            r"""uncertainty = []
for block in [44, 88]:
    samples_by_arm, point_by_arm, dates_by_arm = {}, {}, {}
    for arm in ["A1", "A2", "A3"]:
        point, samples, dates = paired_block_sharpe_samples(curves[arm], curves["A0"], block_days=block, seed=10_000 + block)
        point_by_arm[arm], samples_by_arm[arm], dates_by_arm[arm] = point, samples, dates
    assert len(set(dates_by_arm.values())) == 1, dates_by_arm
    raw_matrix = np.column_stack([samples_by_arm[arm] for arm in ["A1", "A2", "A3"]])
    joint_finite = np.isfinite(raw_matrix).all(axis=1)
    matrix = raw_matrix[joint_finite]
    valid_draws = len(matrix)
    if valid_draws:
        points = np.asarray([point_by_arm[arm] for arm in ["A1", "A2", "A3"]], dtype=float)
        simultaneous_radius = float(np.quantile(np.max(np.abs(matrix - points), axis=1), .95))
    else:
        matrix, simultaneous_radius = np.empty((0, 3)), np.nan
    for column, arm in enumerate(["A1", "A2", "A3"]):
        point = point_by_arm[arm]
        samples = matrix[:, column] if valid_draws else np.array([], dtype=float)
        paired = curves[arm][["date", "return"]].merge(curves["A0"][["date", "return"]], on="date", suffixes=("_left", "_right")).dropna()
        differences = paired.return_left.to_numpy() - paired.return_right.to_numpy()
        uncertainty.append({
            "arm": arm,
            "block_days": block,
            "dates": dates_by_arm[arm],
            "blocks": math.ceil(dates_by_arm[arm] / block) if dates_by_arm[arm] else 0,
            "valid_resamples": len(samples),
            "mean_return_difference": float(differences.mean()) if len(differences) else np.nan,
            "mean_sharpe_difference": point,
            "bootstrap_p05": float(np.quantile(samples, .05)) if len(samples) else np.nan,
            "bootstrap_p95": float(np.quantile(samples, .95)) if len(samples) else np.nan,
            "simultaneous_p05": float(point - simultaneous_radius) if np.isfinite(simultaneous_radius) else np.nan,
            "simultaneous_p95": float(point + simultaneous_radius) if np.isfinite(simultaneous_radius) else np.nan,
        })
pd.DataFrame(uncertainty).to_csv(ARTIFACTS / "paired-block-uncertainty.csv", index=False)

def counterfactual_curve(curve, variant):
    source = curve.sort_values("date").copy()
    original_returns = source["return"].fillna(0.0)
    if variant == "remove-best-day":
        keep = source.index
        adjusted = original_returns.copy()
        best_index = original_returns.iloc[1:].idxmax() if len(original_returns) > 1 else None
        if best_index is not None:
            adjusted.loc[best_index] = 0.0
    elif variant == "exclude-February":
        keep = source.index[source.date.dt.month != 2]
        adjusted = original_returns.loc[keep]
    else:
        raise ValueError(variant)
    result = source.loc[keep].copy()
    result["return"] = adjusted.to_numpy(dtype=float)
    result["equity"] = float(source.equity.iloc[0]) * (1 + result["return"]).cumprod()
    result["drawdown"] = result.equity / result.equity.cummax() - 1
    return result

def summarise_counterfactual(curve):
    result = summarise_backtest(curve)
    observations = curve["return"].dropna()
    years = max(len(observations) / 365.0, 1 / 365.0)
    result["effective_years"] = years
    result["cagr"] = float((curve.equity.iloc[-1] / curve.equity.iloc[0]) ** (1 / years) - 1)
    return result

falsification = []
for arm, curve in {**curves, **young_results, **cap_results}.items():
    for variant in ["remove-best-day", "exclude-February"]:
        counterfactual = counterfactual_curve(curve, variant)
        falsification.append({"arm": arm, "variant": variant, **summarise_counterfactual(counterfactual)})
falsification_table = pd.DataFrame(falsification)
falsification_table.to_csv(ARTIFACTS / "falsification-sensitivities.csv", index=False)
""",
        ),
        (
            "code",
            r"""rows = []
def excess_sharpe(curve, periods_per_year=365.0, annual_reference=0.05):
    returns = curve["return"].dropna().to_numpy(dtype=float)
    if len(returns) < 2:
        return np.nan
    volatility = returns.std(ddof=1) * np.sqrt(periods_per_year)
    return float((returns.mean() * periods_per_year - annual_reference) / volatility) if volatility > 0 else np.nan

excess_rows = []
for arm, curve in curves.items():
    excess_rows.append({"arm": arm, "clock": "daily", "excess_sharpe_5pct": excess_sharpe(curve)})
for arm in curves:
    excess_rows.append({"arm": arm, "clock": "weekly", "excess_sharpe_5pct": excess_sharpe(weekly_curve(pd.read_parquet(ARTIFACTS / f"equity-{arm}.parquet")), periods_per_year=52.0)})
excess_sharpe_table = pd.DataFrame(excess_rows)
excess_sharpe_table.to_csv(ARTIFACTS / "excess-sharpe-5pct.csv", index=False)
for arm in ["A1", "A2", "A3"]:
    candidate, anchor = primary_metrics.loc[arm], primary_metrics.loc["A0"]
    rows.append({"arm": arm, "higher_sharpe": bool(candidate.sharpe > anchor.sharpe), "no_higher_volatility": bool(candidate.volatility <= anchor.volatility), "no_deeper_drawdown": bool(candidate.max_drawdown >= anchor.max_drawdown), "cagr_floor_10pct": bool(candidate.cagr >= .10), "within_5pp_of_anchor": bool(candidate.cagr >= anchor.cagr - .05), "point_estimate_pass": bool(candidate.sharpe > anchor.sharpe and candidate.volatility <= anchor.volatility and candidate.max_drawdown >= anchor.max_drawdown and candidate.cagr >= .10 and candidate.cagr >= anchor.cagr - .05)})
verdict = pd.DataFrame(rows).set_index("arm")
verdict.to_csv(ARTIFACTS / "shortlist-verdict.csv")
matched_control = pd.read_csv(ARTIFACTS / "matched-finite-veto-rows.csv")
null_control = pd.read_csv(ARTIFACTS / "veto-permutation-null.csv")
matched_dates = pd.to_datetime(matched_control["date"])
common_pool = evaluation.merge(
    labels[["date", "address", "forward_log_growth_raw_30"]], on=["date", "address"], how="inner"
)
common_pool = common_pool[
    common_pool.forward_log_growth_raw_30.notna()
    & common_pool.interval_downside_dev_30.notna()
].copy()
finite_common = common_pool.dropna(subset=["btc_beta_30"])
common_dense_fraction = float((common_pool.last_interval_days > 2).mean())
finite_dense_fraction = float((finite_common.last_interval_days > 2).mean())
endpoint_errors = pd.to_numeric(evaluation["btc_endpoint_error_days_30"], errors="coerce").dropna().abs()
endpoint_median_hours = float(endpoint_errors.median() * 24) if not endpoint_errors.empty else np.nan
endpoint_max_hours = float(endpoint_errors.max() * 24) if not endpoint_errors.empty else np.nan
control_summary = {
    "A1": (matched_control.a1_tail_growth.mean(), matched_control.a1_tail_loss_probability.mean()),
    "A2": (matched_control.a2_tail_growth.mean(), matched_control.a2_tail_loss_probability.mean()),
    "A3": (matched_control.a3_tail_growth.mean(), matched_control.a3_tail_loss_probability.mean()),
}
null_growth = float(null_control.excluded_mean_growth.mean())
null_loss = float(null_control.excluded_loss_probability.mean())
falsification_lookup = falsification_table.set_index(["arm", "variant"])
a0_best_day = falsification_lookup.loc[("A0", "remove-best-day")]
a0_ex_february = falsification_lookup.loc[("A0", "exclude-February")]
classifier_text = (
    f"The A2 classifier is used rank-only for vetoing (ROC AUC {classifier_metrics.get('roc_auc', np.nan):.3f}, "
    f"PR AUC {classifier_metrics.get('pr_auc', np.nan):.3f}); its log loss {classifier_metrics.get('log_loss', np.nan):.3f} "
    f"versus base-rate {classifier_metrics.get('base_rate_log_loss', np.nan):.3f} is not a calibrated probability claim. "
    f"The optional family bundle is scored separately (ROC AUC {family_classifier_metrics.get('roc_auc', np.nan):.3f}) in `family-loss-classifier-metrics.json`."
)
source_hashes = {
    name: hashlib.sha256((PROJECT_DIR / name).read_bytes()).hexdigest()
    for name in ["ic_research.py", "stable_profit.py", "build_stable_profit_notebooks.py"]
}
write_json(ARTIFACTS / "run-manifest.json", {"plan": "stable-profit-plan-01", "primary_horizon": 30, "primary_arms": ["A0", "A1", "A2", "A3"], "veto_fraction": .20, "min_train_dates": 60, "logistic_C": 1.0, "decision_frequency": "daily", "daily_block_lengths": [44, 88], "config": CONFIG.__dict__, "source_hashes": source_hashes, "note": "Existing year is retrospective development evidence; no production promotion."})
summary = PROJECT_DIR / "summary-03.md"
summary.write_text(
    "# Stable-profit experiment results\n\n"
    f"The stable-profit track preserved the production return ranking and compared fixed 30-day tail vetoes: observed interval downside (A1), a sparse-compatible severe-loss classifier (A2), and endpoint-aligned absolute BTC beta (A3). A0 is the production replay anchor. The BTC beta rebuild uses actual sparse interval endpoints with a 12-hour reference tolerance; rows with aligned pairs have a median endpoint error of about {endpoint_median_hours:.1f} hours and a maximum of about {endpoint_max_hours:.1f} hours, all within tolerance. This removes the earlier dense-period-only artefact.\n\n"
    "## Primary results\n\n"
    + primary_metrics[["cagr", "volatility", "sharpe", "max_drawdown", "mean_cash_fraction", "mean_stale_positions", "mean_carried_positions"]].round(4).to_markdown()
    + "\n\nWeekly metrics use recomputed weekly equity returns and 52 periods per year:\n\n"
    + weekly_metrics[["cagr", "volatility", "sharpe", "max_drawdown"]].round(4).to_markdown()
    + f"\n\nA3's BTC-beta veto was active on {len(a3_active)} dates from {a3_active_start.date() if pd.notna(a3_active_start) else 'n/a'} to {a3_active_end.date() if pd.notna(a3_active_end) else 'n/a'}; its full-period metric includes the earlier A0 replay window.\n\n"
    + classifier_text
    + "\n\n"
    + "\n\n## Young and sizing checks\n\n"
    + young_metrics[["cagr", "volatility", "sharpe", "max_drawdown", "mean_cash_fraction"]].round(4).to_markdown()
    + "\n\nYoung access, age and sampling attribution (including selected capital and forward-loss P&L proxies) is saved in `young-selection-attribution.csv`. Young arms apply the 5% cap to under-90-day names and to names with intervals longer than two days; short proxy spans are labelled in the young pool ledgers.\n\n"
    + "\n\nThe cash-scaled A0-young arm scales final capped weights down towards the realised A2-young decision-time investment fraction, separating cash dilution from selection where the young caps permit it. Cap-limited dates remain below the reference and are recorded in `cap-diagnostic-manifest.json`. The sizing diagnostic applies each arm's current pre-cap requested allocation before redistribution:\n\n"
    + cap_metrics[["cagr", "volatility", "sharpe", "max_drawdown", "mean_cash_fraction"]].round(4).to_markdown()
    + "\n\nA0-cap's cash-heavy result is a sizing/exposure diagnostic, not a production candidate; the leader-removal and cash-scaled controls are saved with the cap artefacts. Cash matching is cap-feasible rather than exact when A0's TVL or per-vault limits bind.\n\n"
    "## Uncertainty and falsification\n\n"
    + f"Paired 44/88-day daily-return block bootstraps include pointwise and simultaneous Sharpe-difference bounds in `_artifacts-stable-profit/paired-block-uncertainty.csv`. The A0 remove-best-day counterfactual has CAGR {a0_best_day.cagr:.3f}, while excluding February has CAGR {a0_ex_february.cagr:.3f}; these are attribution sensitivities, not new tuning targets. The 5% annual-reference excess-Sharpe sensitivity is saved in `excess-sharpe-5pct.csv`, and conditional-return volatility/Sharpe by BTC up/down regime is saved in `btc-regime-policy-metrics.csv`.\n\n"
    + f"On identical finite rows, the comparison has {len(matched_control)} dates with at least one excluded row from {matched_dates.min().date()} to {matched_dates.max().date()} (the finite BTC-beta intersection begins {finite_common.date.min().date() if not finite_common.empty else 'n/a'}). Its long-interval share is {finite_dense_fraction:.1%}, versus {common_dense_fraction:.1%} in the full evaluation pool, so this is a near-daily subset rather than a complete sparse comparison. Mean excluded growth/loss rates are A1 {control_summary['A1'][0]:.3f}/{control_summary['A1'][1]:.1%}, A2 {control_summary['A2'][0]:.3f}/{control_summary['A2'][1]:.1%}, and A3 {control_summary['A3'][0]:.3f}/{control_summary['A3'][1]:.1%}, versus permutation-null {null_growth:.3f}/{null_loss:.1%}; the learned veto does not beat the simple downside control.\n\n"
    "## Decision\n\n"
    + verdict.to_markdown()
    + f"\n\nThe policy replay forward-fills each vault's latest causally available NAV, matching the production universe's daily candle convention. `mean_carried_positions` identifies the exposure marked from such carried values; it does not reveal an unobserved intra-interval path. The no-op A0 replay remains exactly equal to the incumbent path, but neither replay is yet identical to the trade-executor engine. No production promotion follows without unseen-time validation and exact engine reconciliation.\n"
)
display(verdict)
print(summary)
""",
        ),
    ]
)

for filename, nb in [("05-stable-profit-selection.ipynb", nb05), ("06-repeatability-and-direction.ipynb", nb06), ("07-stable-profit-validation.ipynb", nb07)]:
    nbf.write(nb, ROOT / filename)
    print("wrote", ROOT / filename)
