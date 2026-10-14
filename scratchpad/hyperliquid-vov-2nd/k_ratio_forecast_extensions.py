"""Bounded quality, persistence, placebo and missing-input checks for experiment 09."""

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from tqdm_loggable.auto import tqdm

from k_ratio_features import ARTIFACT_DIR, START, END, EXISTING, K_MAIN, HORIZONS, TARGETS, sha256
from k_ratio_forecast_models import FoldAdapter, training_weights, target_column
from k_ratio_forecast_statistics import rho, model_diagnostics


def missing_adapter_checks(data, models):
    """Test absent columns, immutable fitting state and actual partial forecasts."""
    train = pd.DataFrame({"30d CAGR": [0.1, 0.2, 0.3, 0.4], "360d CAGR": [np.nan] * 4, "30d K-ratio": [1.0, 2.0, np.nan, 4.0]})
    adapter = FoldAdapter(train.columns.tolist()).fit(train, np.ones(4))
    means = adapter.means.copy()
    medians = adapter.medians.copy()
    young = pd.DataFrame({"30d CAGR": [0.2], "360d CAGR": [np.nan], "30d K-ratio": [np.nan]})
    output = adapter.transform(young)
    extreme = young.copy()
    extreme["30d CAGR"] = 1e6
    adapter.transform(extreme)
    model = Ridge(alpha=10).fit(adapter.transform(train), np.arange(4, dtype=float))
    p = models["predictions"]
    p = p[p.phase.eq(0) & p.delay.eq(0) & ~p.source & p.supported & p.arm.eq("Existing + K")]
    supported = models["support"]
    valid = supported.latest_training_label_at.notna()
    checks = {"missing_360d_does_not_drop_usable_30d": bool(np.isfinite(output).all() and output.shape[0] == 1), "all_missing_column_disabled": bool(not adapter.active[1]), "test_rows_cannot_change_training_means": bool(np.array_equal(means, adapter.means)), "test_rows_cannot_change_training_medians": bool(np.array_equal(medians, adapter.medians)), "partial_input_prediction_is_finite": bool(np.isfinite(model.predict(output)).all()), "all_fits_have_strictly_matured_labels": bool((supported.loc[valid, "latest_training_label_at"] < supported.loc[valid, "refit_at"]).all()), "actual_partial_history_forecasts": int((p.supported_inputs < p.supported_input_count).sum()), "actual_young_recorded_history_forecasts": int(p.age_days.lt(180).sum())}
    assert all(value for value in checks.values() if isinstance(value, bool)), checks
    assert checks["actual_partial_history_forecasts"] > 0
    return pd.DataFrame({"Check": checks.keys(), "Result": [str(v) for v in checks.values()]})


def quality_diagnostics(data, models, stats):
    """Separate endpoint convention, stale marks and volatility persistence."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    labels = data["labels"]
    labels = labels[labels.delay.eq(0) & labels.origin_at.isin(f.origin_at.unique())]
    decomposition = []
    endpoints = []
    for h in HORIZONS:
        joined = f.merge(labels[labels.horizon.eq(h)][["origin_at", "pair_id", "mean_return", "volatility", "K-ratio", "K-ends-only"]], on=["origin_at", "pair_id"])
        for date, g in joined.groupby("origin_at"):
            endpoints.append({"horizon": h, "origin_at": date, "K_endpoint_convention_rho": rho(g["K-ratio"], g["K-ends-only"]), "paired_K_labels": int((np.isfinite(g["K-ratio"]) & np.isfinite(g["K-ends-only"])).sum())})
            for feature in ("30d K-ratio", "30d Sharpe", "30d CAGR", "volatility_30", "ewma_volatility_30", "flat_fraction_30", "autocorrelation_30"):
                for outcome in ("mean_return", "volatility"):
                    value = rho(g[feature], g[outcome])
                    decomposition.append({"horizon": h, "origin_at": date, "feature": feature, "future_component": outcome, "IC": value})
    comp = pd.DataFrame(decomposition).groupby(["horizon", "feature", "future_component"]).agg(mean_IC=("IC", "mean"), defined_origins=("IC", "count")).reset_index()
    ends = pd.DataFrame(endpoints).groupby("horizon").agg(mean_K_convention_rho=("K_endpoint_convention_rho", "mean"), defined_origins=("K_endpoint_convention_rho", "count"), paired_K_labels=("paired_K_labels", "sum")).reset_index()
    influence = stats["influence"].groupby(["horizon", "target"]).agg(minimum_leave_vault_IC_delta=("mean_delta_IC", "min"), maximum_leave_vault_IC_delta=("mean_delta_IC", "max"), removed_vaults=("removed_vault", "nunique")).reset_index()
    blocks = stats["blocks"]
    blocks = blocks[blocks.old.eq("Existing") & blocks.phase.eq(0) & blocks.delay.eq(0) & ~blocks.source]
    leaveblock = []
    for (h, t), g in blocks.groupby(["horizon", "target"]):
        values = g.delta_IC.to_numpy()
        if len(values) > 1:
            reduced = (values.sum() - values) / (len(values) - 1)
            leaveblock.append({"horizon": h, "target": t, "minimum_leave_block_delta": reduced.min(), "maximum_leave_block_delta": reduced.max(), "calendar_blocks": len(values)})
    return comp, ends, influence, pd.DataFrame(leaveblock)


def path_placebo(data, seeds=8):
    """Shuffle entire vault target paths, preserving dates and serial dependence.

    This is an exploratory negative control, not an independent-sample test.
    Original and shuffled labels use the same paired rows for each draw.
    """
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    labels = data["labels"]
    labels = labels[labels.origin_at.isin(f.origin_at.unique()) & labels.delay.eq(0)]
    ids = np.sort(f.pair_id.unique())
    results = []
    for seed in tqdm(range(seeds), desc="09 whole-vault-path placebo; estimated 1 minute", mininterval=15):
        mapping = dict(zip(ids, np.random.default_rng(109 + seed).permutation(ids)))
        altered = labels.copy()
        altered["pair_id"] = altered.pair_id.map(mapping)
        for h in HORIZONS:
            original = labels[labels.horizon.eq(h)]
            shuffled = altered[altered.horizon.eq(h)]
            g = f[["origin_at", "pair_id", *K_MAIN]].merge(original[["origin_at", "pair_id", "log_return", "Sharpe", "K-ratio"]], on=["origin_at", "pair_id"])
            g = g.merge(shuffled[["origin_at", "pair_id", "log_return", "Sharpe", "K-ratio"]], on=["origin_at", "pair_id"], suffixes=("", " shuffled"))
            for date, piece in g.groupby("origin_at"):
                for target in TARGETS:
                    col = target_column(target)
                    y0 = piece[col].to_numpy()
                    y1 = piece[col + " shuffled"].to_numpy()
                    for feature in K_MAIN:
                        x = piece[feature].to_numpy()
                        good = np.isfinite(x) & np.isfinite(y0) & np.isfinite(y1)
                        results.append({"seed": seed, "origin_at": date, "horizon": h, "target": target, "feature": feature, "paired_vaults": int(good.sum()), "original_IC": rho(x[good], y0[good]), "shuffled_IC": rho(x[good], y1[good])})
    frame = pd.DataFrame(results)
    return frame.groupby(["horizon", "target", "feature"]).agg(mean_original_IC=("original_IC", "mean"), mean_shuffled_IC=("shuffled_IC", "mean"), defined_draw_origins=("shuffled_IC", "count")).reset_index()


def run_extensions(data, models, stats):
    """Persist small extensions separately from the shared forecast calculations."""
    fingerprint = sha256(__file__) + data["manifest"]["module_sha256"] + sha256(__file__.replace("extensions", "models")) + sha256(__file__.replace("extensions", "statistics"))
    manifest = ARTIFACT_DIR / "extensions-manifest.json"
    names = ("missing_checks", "calibration", "baseline_pairs", "volatility_components", "endpoint_convention", "leave_vault", "leave_block", "path_placebo", "dependence", "redundancy_support", "target_attrition")
    if manifest.exists() and json.loads(manifest.read_text()).get("fingerprint") == fingerprint:
        return {name: pd.read_parquet(ARTIFACT_DIR / f"extension-{name}.parquet") for name in names}
    missing = missing_adapter_checks(data, models)
    calibration, baseline = model_diagnostics(models)
    components, ends, influence, blocks = quality_diagnostics(data, models, stats)
    placebo = path_placebo(data)
    dependence = dependence_sensitivity(stats)
    redundancy = redundancy_support(data)
    attrition = target_attrition(data)
    result = dict(zip(names, (missing, calibration, baseline, components, ends, influence, blocks, placebo, dependence, redundancy, attrition)))
    for name, frame in result.items():
        frame.to_parquet(ARTIFACT_DIR / f"extension-{name}.parquet", index=False)
    manifest.write_text(json.dumps({"fingerprint": fingerprint, "placebo": "Eight whole-vault-path permutations; date and serial dependence preserved; exploratory, not a p-value."}, indent=2))
    return result


def dependence_sensitivity(stats):
    """Expose overlapping-target sensitivity without treating vault rows as independent."""
    dates = stats["paired_dates"]
    dates = dates[dates.old.eq("Existing") & dates.phase.eq(0) & dates.delay.eq(0) & ~dates.source]
    rows = []
    for (h, t), g in dates.groupby(["horizon", "target"]):
        g = g.sort_values("origin_at")
        chosen = []
        next_origin = g.origin_at.min()
        for r in g.itertuples(index=False):
            if r.origin_at >= next_origin:
                chosen.append(r.delta_IC)
                next_origin = r.origin_at + pd.Timedelta(days=int(h))
        for multiplier in (1, 2):
            length = int(h) * multiplier
            start = g.origin_at.min()
            full_end = g.origin_at.max() + pd.Timedelta(days=4)
            values = []
            numbered = ((g.origin_at - start).dt.days // length).astype(int)
            for number, b in g.groupby(numbered):
                if start + pd.Timedelta(days=(number + 1) * length) <= full_end and b.delta_IC.notna().any():
                    values.append(b.delta_IC.mean())
            lower = upper = np.nan
            if len(values) >= 8:
                draws = np.random.default_rng(209).choice(values, size=(2000, len(values)), replace=True).mean(axis=1)
                lower, upper = np.quantile(draws, [0.025, 0.975])
            rows.append({"horizon": h, "target": t, "block_days": length, "complete_blocks": len(values), "mean_block_delta_IC": np.mean(values) if values else np.nan, "lower_band": lower, "upper_band": upper, "nonoverlapping_origins": len(chosen), "nonoverlapping_mean_delta_IC": np.nanmean(chosen) if chosen else np.nan})
    return pd.DataFrame(rows)


def redundancy_support(data):
    """Show pairwise counts beside a common-cohort redundancy companion."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    rows = []
    for days in (30, 90, 180):
        columns = [f"{days}d {m}" for m in ("CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar", "K-ratio")]
        for _, g in f.groupby("origin_at"):
            common = g[np.isfinite(g[columns]).all(axis=1)]
            for metric in ("CAGR", "Sharpe", "Calmar"):
                x, y = f"{days}d K-ratio", f"{days}d {metric}"
                count = int((np.isfinite(g[x]) & np.isfinite(g[y])).sum())
                rows.append({"days": days, "pair": f"K / {metric}", "pairwise_rho": rho(g[x], g[y]), "paired_vaults": count, "common_rho": rho(common[x], common[y]), "common_vaults": len(common)})
    return pd.DataFrame(rows).groupby(["days", "pair"]).agg(pairwise_rho=("pairwise_rho", "mean"), pairwise_defined_origins=("pairwise_rho", "count"), mean_paired_vaults=("paired_vaults", "mean"), common_cohort_rho=("common_rho", "mean"), common_defined_origins=("common_rho", "count"), mean_common_vaults=("common_vaults", "mean")).reset_index()


def target_attrition(data):
    """Quantify missing outcomes without inventing closure or redemption proceeds."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    l = data["labels"]
    l = l[l.delay.eq(0)].merge(f[["origin_at", "pair_id", "age_days"]], on=["origin_at", "pair_id"])
    l["history_cohort"] = np.where(l.age_days < 180, "Recorded history <180d", "Recorded history ≥180d")
    rows = []
    for (h, cohort), g in l.groupby(["horizon", "history_cohort"]):
        for target in TARGETS:
            valid = np.isfinite(g[target_column(target)])
            censor = g.status.eq("administrative_censoring")
            rows.append({"horizon": h, "target": target, "history_cohort": cohort, "observed_anchors": len(g), "valid_labels": int(valid.sum()), "missing_fraction": float((~valid).mean()), "right_censored": int(censor.sum()), "other_missing_labels": int((~valid & ~censor).sum())})
    return pd.DataFrame(rows)
