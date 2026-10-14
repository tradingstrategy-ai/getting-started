"""Fixed feedback diagnostics for the in-place experiment-09 amendment."""

import json
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from tqdm_loggable.auto import tqdm

from k_ratio_features import ARTIFACT_DIR, GENERATION, START, END, EXISTING, K_MAIN, HORIZONS, TARGETS, sha256
from k_ratio_forecast_models import target_column
from k_ratio_forecast_statistics import rho, paired_comparison, date_predictions


def cohort_skills(data, models):
    """Compare models and baselines on a common population within each cohort."""
    p = models["predictions"]
    p = p[p.supported & p.phase.eq(0) & p.delay.eq(0) & ~p.source & np.isfinite(p.actual) & p.prediction_space.eq("level")]
    e = data["eligibility"].copy()
    e["gate_cohort"] = e.source_inclusion & e.gate_passes & e.current_guard_allows & ~e.blacklisted & ~e.quarantined
    e["fundable_cohort"] = e.gate_cohort & e.can_deposit
    flags = e[["origin_at", "pair_id", "gate_cohort", "fundable_cohort", "permission_time_unknown"]]
    p = p.merge(flags, on=["origin_at", "pair_id"], how="left", validate="many_to_one")
    cohorts = {"All observed": lambda g: np.ones(len(g), bool), "Recorded history 30–89d": lambda g: g.age_days.ge(30) & g.age_days.lt(90), "Recorded history 90–179d": lambda g: g.age_days.ge(90) & g.age_days.lt(180), "Recorded history ≥180d": lambda g: g.age_days.ge(180), "Partial supported inventory": lambda g: g.supported_inputs.lt(g.supported_input_count), "Complete supported inventory": lambda g: g.supported_inputs.eq(g.supported_input_count), "Current-policy gate": lambda g: g.gate_cohort.fillna(False), "Gate and deposit feasible": lambda g: g.fundable_cohort.fillna(False), "Permission clock unknown": lambda g: g.permission_time_unknown.fillna(True), "Permission clock known": lambda g: ~g.permission_time_unknown.fillna(True), "Low past activity ≥80% flat": lambda g: g.flat_fraction_30.ge(0.8), "Active past ≤20% flat": lambda g: g.flat_fraction_30.le(0.2)}
    rows = []
    for (h, t), g in p.groupby(["horizon", "target"]):
        arms = ["Existing", "Existing + K", "Compact", "Compact + K", "Quality/age", "Constant"] + (["Zero return"] if t == "CAGR" else [])
        key = ["origin_at", "pair_id"]
        matched = g[g.arm.isin(arms)]
        counts = matched.groupby(key).arm.nunique()
        common = counts[counts.eq(len(arms))].reset_index()[key]
        matched = matched.merge(common, on=key, validate="many_to_one")
        for name, mask in cohorts.items():
            selected = matched.loc[mask(matched)]
            if selected.empty:
                continue
            dates = date_predictions(selected)
            for arm, a in dates.groupby("arm"):
                rows.append({"horizon": h, "target": t, "cohort": name, "arm": arm, "mean_IC": a.IC.mean(), "MAE": a.MAE.mean(), "MSE": a.MSE.mean(), "raw_MAE": a.raw_MAE.mean(), "origins": a.origin_at.nunique(), "defined_IC_origins": a.IC.notna().sum(), "paired_rows": int(selected.arm.eq(arm).sum())})
    return pd.DataFrame(rows)


def matched_lookbacks(data):
    """Compare K sampling and lookbacks on exactly the same label-valid rows."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    rows = []
    for h, t in [(h, t) for h in HORIZONS for t in TARGETS]:
        col = target_column(t)
        l = data["labels"]
        l = l[l.horizon.eq(h) & l.delay.eq(0)]
        g = f.merge(l[["origin_at", "pair_id", col]], on=["origin_at", "pair_id"])
        families = [("Lookbacks 30/60/90", [f"{d}d K-ratio" for d in (30, 60, 90)]), ("Lookbacks 30/60/90/180", [f"{d}d K-ratio" for d in (30, 60, 90, 180)])]
        for d in (30, 60, 90, 180):
            families.append((f"Daily/weekly {d}d", [f"{d}d K-ratio", f"{d}d weekly K-ratio"]))
        for name, columns in families:
            good = np.isfinite(g[columns + [col]]).all(axis=1)
            selected = g.loc[good]
            for feature in columns:
                vals = [(rho(a[feature], a[col]), len(a)) for _, a in selected.groupby("origin_at")]
                scores = np.array([v[0] for v in vals])
                rows.append({"horizon": h, "target": t, "comparison": name, "feature": feature, "mean_IC": float(np.nanmean(scores)) if np.isfinite(scores).any() else np.nan, "defined_origins": int(np.isfinite(scores).sum()), "paired_rows": len(selected), "mean_paired_vaults": np.mean([v[1] for v in vals]) if vals else np.nan, "first_origin": selected.origin_at.min(), "last_origin": selected.origin_at.max(), "actual_span_days": (int(feature.split("d ")[0]) // 7 * 7 if "weekly" in feature else int(feature.split("d ")[0]))})
    return pd.DataFrame(rows)


def attrition_diagnostics(data):
    """Separate calendar-wide missing marks, activity and operational cohorts."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    e = data["eligibility"]
    cols = [c for c in ["origin_at", "pair_id", "permission_time_unknown", "can_deposit", "blacklisted", "quarantined"] if c in e]
    f = f.merge(e[cols], on=["origin_at", "pair_id"], how="left", validate="one_to_one")
    metadata = json.loads((GENERATION / "inputs/vault-metadata.json").read_text())["vaults"]
    reasons = {v["address"]: v.get("deposit_closed_reason") for v in metadata if v["chain_id"] == 9999}
    f["current_closed_metadata"] = f.vault_address.map(reasons).eq("Vault is permanently closed")
    f["current_leader_disabled_metadata"] = f.vault_address.map(reasons).eq("Vault deposits disabled by leader")
    labels = data["labels"]
    labels = labels[labels.delay.eq(0)]
    g = f.merge(labels, on=["origin_at", "pair_id"], suffixes=("", " label"), validate="one_to_many")
    cohorts = {"All observed": np.ones(len(g), bool), "Recorded history <180d": g.age_days.lt(180), "Past flat ≥80%": g.flat_fraction_30.ge(0.8), "Past active ≤20% flat": g.flat_fraction_30.le(0.2), "Recent daily coverage <95%": g.observed_fraction_90.lt(0.95), "Permission clock unknown": g.permission_time_unknown.fillna(True), "Permission clock known": ~g.permission_time_unknown.fillna(True), "Deposit unavailable": ~g.can_deposit.fillna(False), "Coverage disappearance": g.status.eq("disappearance_or_terminal_coverage"), "Currently permanently closed (snapshot)": g.current_closed_metadata, "Currently leader-disabled (snapshot)": g.current_leader_disabled_metadata}
    rows = []
    bounds = []
    for name, mask in cohorts.items():
        for h, a in g.loc[mask].groupby("horizon"):
            censored = a.status.eq("administrative_censoring")
            for t in TARGETS:
                valid = np.isfinite(a[target_column(t)])
                low = a.nonzero_returns.lt(max(4, int(np.ceil(h / 2)))) & a.status.eq("complete")
                rows.append({"cohort": name, "horizon": h, "target": t, "observed_anchors": len(a), "valid_labels": int(valid.sum()), "missing_fraction": float((~valid).mean()), "right_censored": int(censored.sum()), "low_activity_complete_paths": int(low.sum()), "coverage_disappearance_rows": int(a.status.eq("disappearance_or_terminal_coverage").sum())})
    for h, a in g[~g.status.eq("administrative_censoring")].groupby("horizon"):
        known = a.log_return.notna()
        missing = ~known
        returns = np.expm1(a.log_return)
        for loss, gain in [(-0.5, 0.5), (-0.99, 1.0)]:
            lower = np.where(known, returns, loss)
            upper = np.where(known, returns, gain)
            for label, v in [("pessimistic", lower), ("optimistic", upper)]:
                bydate = pd.Series(v, index=a.index).groupby(a.origin_at).mean()
                bounds.append({"horizon": h, "scenario": label, "assumed_missing_return": loss if label == "pessimistic" else gain, "missing_rows": int(missing.sum()), "mean_horizon_simple_return": bydate.mean(), "origins": len(bydate)})
    daily = data["daily"]
    daily = daily[daily.date >= START]
    calendar = daily.groupby("date").pair_id.nunique().reindex(pd.date_range(START, END - pd.Timedelta(days=1)), fill_value=0).rename("actual_vault_marks").rename_axis("date").reset_index()
    calendar["coverage_vs_snapshot"] = calendar.actual_vault_marks / data["manifest"]["vaults"]
    calendar["change_in_marks"] = calendar.actual_vault_marks.diff()
    return pd.DataFrame(rows), pd.DataFrame(bounds), calendar


def archive_zero_audit(data):
    """Count zero-price observations without assuming empty vaults suffered losses."""
    path = GENERATION / "inputs/vault-prices.parquet"
    addresses = data["features"].vault_address.unique().tolist()
    dataset = ds.dataset(path)
    f = dataset.to_table(columns=["timestamp", "address", "share_price", "total_assets", "total_supply"], filter=(ds.field("chain") == 9999) & ds.field("address").isin(addresses) & (ds.field("share_price") <= 0)).to_pandas().reset_index()
    return f.groupby("address").agg(rows=("share_price", "size"), min_price=("share_price", "min"), first_mark=("timestamp", "min"), last_mark=("timestamp", "max"), max_assets=("total_assets", "max"), max_supply=("total_supply", "max")).reset_index()


def extrapolation_diagnostics(models):
    """Expose the full numerical range and applied bounds, including illustrations."""
    p = models["predictions"]
    p = p[p.phase.eq(0) & p.delay.eq(0) & ~p.source]
    return p.groupby(["horizon", "target", "arm", "supported"]).agg(predictions=("prediction", "size"), min_prediction=("prediction", "min"), max_prediction=("prediction", "max"), output_clipped_fraction=("output_clipped", "mean"), mean_input_clipped_fraction=("input_clipped_fraction", "mean")).reset_index()


def run_feedback(data, models, stats):
    """Persist fixed additions separately from the principal paired comparison."""
    fingerprint = sha256(__file__) + sha256(GENERATION / "inputs/vault-metadata.json") + data["manifest"]["module_sha256"] + sha256(__file__.replace("feedback", "models")) + sha256(__file__.replace("feedback", "statistics"))
    manifest = ARTIFACT_DIR / "feedback-manifest.json"
    names = ["cohort_skill", "matched_lookbacks", "attrition", "missing_scenarios", "calendar_marks", "zero_nav", "extrapolation", "before_after", "universe_audit", "distribution", "numerical_quality"]
    if manifest.exists() and json.loads(manifest.read_text()).get("fingerprint") == fingerprint:
        return {name: pd.read_parquet(ARTIFACT_DIR / f"feedback-{name}.parquet") for name in names}
    skill = cohort_skills(data, models)
    lookbacks = matched_lookbacks(data)
    attrition, bounds, calendar = attrition_diagnostics(data)
    zero = archive_zero_audit(data)
    extra = extrapolation_diagnostics(models)
    old = GENERATION / "09-before-robust-amendment/predictions.parquet"
    rows = []
    if old.exists():
        previous = pd.read_parquet(old)
        new = models["predictions"]
        for arm in ("Existing", "Existing + K", "Compact", "Compact + K"):
            aa = previous[previous.arm.eq(arm) & previous.phase.eq(0) & previous.delay.eq(0) & ~previous.source]
            bb = new[new.arm.eq(arm) & new.phase.eq(0) & new.delay.eq(0) & ~new.source].copy()
            aa = aa.copy()
            aa["arm"] = "Before"
            bb["arm"] = "After"
            pair, _ = paired_comparison(pd.concat([aa, bb], ignore_index=True), "Before", "After")
            for (h, t), g in pair.groupby(["horizon", "target"]):
                rows.append({"horizon": h, "target": t, "arm": arm, "before_IC": g.old_IC.mean(), "after_IC": g.new_IC.mean(), "before_MAE": g.old_MAE.mean(), "after_MAE": g.new_MAE.mean(), "before_MSE": g.old_MSE.mean(), "after_MSE": g.new_MSE.mean(), "paired_origins": len(g)})
    universe = universe_audit(data)
    distribution = feature_outcome_distributions(data)
    numerical = numerical_quality_diagnostics(data, models)
    result = dict(zip(names, [skill, lookbacks, attrition, bounds, calendar, zero, extra, pd.DataFrame(rows), universe, distribution, numerical]))
    for name, frame in result.items():
        frame.to_parquet(ARTIFACT_DIR / f"feedback-{name}.parquet", index=False)
    manifest.write_text(json.dumps({"fingerprint": fingerprint, "status": "fixed post-review diagnostics; already researched history; no hyperparameter search"}, indent=2))
    return result


def universe_audit(data):
    """Audit archive conditioning without certifying a historical listing."""
    dataset = ds.dataset(GENERATION / "inputs/vault-prices.parquet")
    f = dataset.to_table(columns=["address", "timestamp"], filter=ds.field("chain") == 9999).to_pandas().reset_index()
    f = f[pd.to_datetime(f.timestamp) < END]
    first = f.groupby("address").timestamp.min()
    selected = set(data["features"].vault_address.unique())
    metadata = json.loads((GENERATION / "inputs/vault-metadata.json").read_text())["vaults"]
    meta = [v for v in metadata if v["chain_id"] == 9999]
    rows = []
    for origin in pd.to_datetime(["2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01"]):
        seen = first[first < origin]
        rows.append({"as_of": origin, "archived_addresses_seen": len(seen), "selected_addresses_seen": int(seen.index.isin(selected).sum()), "omitted_addresses_seen": int((~seen.index.isin(selected)).sum()), "snapshot_metadata_vaults": len(meta), "metadata_with_deployment_date": sum(v.get("deployment") is not None for v in meta), "start_date_equals_first_updated": sum(v.get("start_date") == v.get("first_updated_at") for v in meta)})
    return pd.DataFrame(rows)


def feature_outcome_distributions(data):
    """Show forward distributions and finite cohort support without annualisation."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    l = data["labels"]
    l = l[l.horizon.eq(30) & l.delay.eq(0)]
    g = f.merge(l[["origin_at", "pair_id", "log_return", "Sharpe", "K-ratio"]], on=["origin_at", "pair_id"])
    rows = []
    for feature in ["30d K-ratio", "90d K-ratio", "30d Sharpe", "90d CAGR"]:
        for target in TARGETS:
            col = target_column(target)
            selected = g[np.isfinite(g[feature]) & np.isfinite(g[col])].copy()
            selected["bucket"] = np.minimum(5, np.ceil(selected.groupby("origin_at")[feature].rank(method="average", pct=True) * 5)).astype(int)
            for bucket, a in selected.groupby("bucket"):
                dated = a.groupby("origin_at")[col].agg(median="median", p10=lambda v: v.quantile(0.1), p90=lambda v: v.quantile(0.9))
                rows.append({"feature": feature, "horizon": 30, "target": target, "quintile": bucket, "median_outcome": dated["median"].mean(), "p10_outcome": dated.p10.mean(), "p90_outcome": dated.p90.mean(), "origins": len(dated), "paired_rows": len(a)})
    return pd.DataFrame(rows)


def numerical_quality_diagnostics(data, models):
    """Test fixed precision and near-linearity screens as descriptive cohorts.

    :param data: Actual observations; no missing NAV or outcome is filled.
    :param models: Existing forecasts, not refitted or selected on these cohorts.
    """
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    labels = data["labels"]
    labels = labels[labels.delay.eq(0)]
    rows = []
    for h in HORIZONS:
        g = f.merge(labels[labels.horizon.eq(h)][["origin_at", "pair_id", "log_return", "Sharpe", "K-ratio", "volatility"]], on=["origin_at", "pair_id"])
        for target in TARGETS:
            col = target_column(target)
            for feature in K_MAIN:
                days = g["max days"] if feature == "max K-ratio" else int(feature.split("d ")[0])
                n = days + 1
                prefix = "max" if feature == "max K-ratio" else f"{days}d"
                slope = g[f"{prefix} slope"]
                resid = g[f"{prefix} residual_scale"]
                rms = np.sqrt((slope**2 * n * (n * n - 1) / 12 + (n - 2) * resid**2) / n)
                tstat = g[feature] * n / np.sqrt(365)
                residual_fraction = (n - 2) / (n - 2 + tstat**2)
                mask = rms.ge(1e-8) & residual_fraction.ge(1e-6)
                if target in ("Sharpe", "K-ratio"):
                    mask &= g.volatility.ge(1e-8)
                if target == "K-ratio":
                    tt = g["K-ratio"] * (h + 1) / np.sqrt(365)
                    mask &= ((h - 1) / (h - 1 + tt**2)).ge(1e-6)
                values = []
                counts = []
                for _, a in g.groupby("origin_at"):
                    valid = np.isfinite(a[feature]) & np.isfinite(a[col])
                    strict = valid & mask.loc[a.index]
                    values.append((rho(a.loc[valid, feature], a.loc[valid, col]), rho(a.loc[strict, feature], a.loc[strict, col])))
                    counts.append((int(valid.sum()), int(strict.sum())))
                values = np.array(values)
                counts = np.array(counts)
                rows.append({"kind": "Individual feature", "horizon": h, "target": target, "feature": feature, "primary_IC": float(np.nanmean(values[:, 0])) if np.isfinite(values[:, 0]).any() else np.nan, "strict_IC": float(np.nanmean(values[:, 1])) if np.isfinite(values[:, 1]).any() else np.nan, "primary_pairs": int(counts[:, 0].sum()), "strict_pairs": int(counts[:, 1].sum()), "strict_defined_origins": int(np.isfinite(values[:, 1]).sum())})
    p = models["predictions"]
    p = p[p.phase.eq(0) & p.delay.eq(0) & ~p.source]
    _, joined = paired_comparison(p)
    quality = labels[["origin_at", "pair_id", "horizon", "volatility"]]
    joined = joined.merge(quality, on=["origin_at", "pair_id", "horizon"], how="left", validate="many_to_one")
    for (h, t), g in joined.groupby(["horizon", "target"]):
        mask = np.ones(len(g), bool)
        if t in ("Sharpe", "K-ratio"):
            mask &= g.volatility.ge(1e-8).to_numpy()
        if t == "K-ratio":
            tt = g.actual_old * (h + 1) / np.sqrt(365)
            mask &= ((h - 1) / (h - 1 + tt**2)).ge(1e-6).to_numpy()
        a = g.loc[mask]
        orig = [rho(x.prediction_new, x.actual_old) - rho(x.prediction_old, x.actual_old) for _, x in g.groupby("origin_at")]
        strict = [rho(x.prediction_new, x.actual_old) - rho(x.prediction_old, x.actual_old) for _, x in a.groupby("origin_at")]
        rows.append({"kind": "Paired K increment", "horizon": h, "target": t, "feature": "Same fitted forecasts", "primary_IC": np.nanmean(orig) if np.isfinite(orig).any() else np.nan, "strict_IC": np.nanmean(strict) if np.isfinite(strict).any() else np.nan, "primary_pairs": len(g), "strict_pairs": len(a), "strict_defined_origins": int(np.isfinite(strict).sum())})
    return pd.DataFrame(rows)
