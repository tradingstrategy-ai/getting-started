"""Date-level feature evidence, paired forecasts and uncertainty for experiment 09."""

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from tqdm_loggable.auto import tqdm

from k_ratio_features import ARTIFACT_DIR, GENERATION, START, END, EXISTING, K_MAIN, K_ALL, HORIZONS, TARGETS, sha256
from k_ratio_forecast_models import target_column


def rho(x, y):
    """Return undefined rather than fabricate IC for a constant/sparse sample."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    good = np.isfinite(x) & np.isfinite(y)
    if good.sum() < 10 or np.unique(x[good]).size < 2 or np.unique(y[good]).size < 2:
        return np.nan
    return float(spearmanr(x[good], y[good]).statistic)


def feature_evidence(data):
    """Each date contributes equally to IC; no filled labels enter this analysis."""
    rows = []
    bins = []
    features = data["features"]
    features = features[features.phase.eq(0) & features.anchor_supported]
    labels = data["labels"][data["labels"].delay.eq(0)]
    columns = EXISTING + K_ALL + ["45d K-ratio"] + [f"{d}d weekly K-ratio" for d in (30, 60, 90, 180)]
    for horizon, target in tqdm([(h, t) for h in HORIZONS for t in TARGETS], desc="09 individual feature IC; estimated 1–2 minutes", mininterval=15):
        frame = features.merge(labels[labels.horizon.eq(horizon)][["origin_at", "pair_id", target_column(target)]], on=["origin_at", "pair_id"], validate="one_to_one")
        for origin, g in frame.groupby("origin_at"):
            y = g[target_column(target)].to_numpy()
            for col in columns:
                x = g[col].to_numpy()
                paired = np.isfinite(x) & np.isfinite(y)
                score = rho(x, y)
                rows.append({"origin_at": origin, "quarter": str(origin.to_period("Q")), "period": "2026" if origin >= START else "Long prior", "feature": col, "horizon": horizon, "target": target, "IC": score, "paired_vaults": int(paired.sum()), "observed_vaults": len(g), "feature_vaults": int(np.isfinite(x).sum()), "label_vaults": int(np.isfinite(y).sum())})
                if col in K_MAIN and np.isfinite(score):
                    ranks = pd.Series(x[paired]).rank(method="average", pct=True).to_numpy()
                    for bucket in range(1, 6):
                        choose = (ranks > (bucket - 1) / 5) & (ranks <= bucket / 5)
                        if choose.any():
                            bins.append({"origin_at": origin, "feature": col, "horizon": horizon, "target": target, "quintile": bucket, "mean_target": float(y[paired][choose].mean()), "vaults": int(choose.sum())})
    dates = pd.DataFrame(rows)
    summary = dates.groupby(["period", "feature", "horizon", "target"], observed=True).agg(mean_IC=("IC", "mean"), median_IC=("IC", "median"), defined_origins=("IC", "count"), scheduled_origins=("origin_at", "nunique"), mean_paired_vaults=("paired_vaults", "mean")).reset_index()
    quarterly = dates.groupby(["quarter", "feature", "horizon", "target"], observed=True).agg(mean_IC=("IC", "mean"), defined_origins=("IC", "count")).reset_index()
    return dates, summary, quarterly, pd.DataFrame(bins)


def date_predictions(predictions):
    """Aggregate prediction errors within each date before averaging dates."""
    primary = predictions[predictions.supported & np.isfinite(predictions.actual)].copy()
    rows = []
    for keys, g in primary.groupby(["horizon", "target", "arm", "phase", "delay", "source", "origin_at"], observed=True):
        x = g.prediction.to_numpy()
        y = g.actual.to_numpy()
        target = keys[1]
        scale = g.target_scale.iloc[0]
        tx = np.arcsinh(x / scale) if target == "K-ratio" else x
        ty = np.arcsinh(y / scale) if target == "K-ratio" else y
        error = tx - ty
        demean = (tx - tx.mean()) - (ty - ty.mean())
        row = dict(zip(["horizon", "target", "arm", "phase", "delay", "source", "origin_at"], keys))
        row.update({"IC": rho(x, y), "MAE": float(np.mean(np.abs(error))), "MSE": float(np.mean(error**2)), "raw_MAE": float(np.mean(np.abs(x - y))), "demeaned_MSE": float(np.mean(demean**2)), "vaults": len(g), "mean_prediction": float(x.mean()), "mean_actual": float(y.mean()), "partial_history_fraction": float((g.supported_inputs < g.supported_input_count).mean()), "young_fraction": float(g.age_days.lt(180).mean())})
        if keys[2].startswith("Rank "):
            for col in ("MAE", "MSE", "raw_MAE", "demeaned_MSE"):
                row[col] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def paired_comparison(predictions, old="Existing", new="Existing + K"):
    """Compare identical target-valid vault/origin rows, never different coverage."""
    p = predictions[predictions.supported & np.isfinite(predictions.actual)]
    a = p[p.arm.eq(old)]
    b = p[p.arm.eq(new)]
    keys = ["origin_at", "pair_id", "horizon", "target", "phase", "delay", "source"]
    joined = a.merge(b, on=keys, suffixes=("_old", "_new"), validate="one_to_one")
    rows = []
    for values, g in joined.groupby(["horizon", "target", "phase", "delay", "source", "origin_at"], observed=True):
        y = g.actual_old.to_numpy()
        x0 = g.prediction_old.to_numpy()
        x1 = g.prediction_new.to_numpy()
        if values[1] == "K-ratio":
            scale = g.target_scale_old.to_numpy()
            yy = np.arcsinh(y / scale)
            a0 = np.arcsinh(x0 / scale)
            a1 = np.arcsinh(x1 / scale)
        else:
            yy, a0, a1 = y, x0, x1
        ic0, ic1 = rho(x0, y), rho(x1, y)
        row = dict(zip(["horizon", "target", "phase", "delay", "source", "origin_at"], values))
        row.update({"old": old, "new": new, "paired_vaults": len(g), "old_IC": ic0, "new_IC": ic1, "delta_IC": ic1 - ic0, "old_MAE": float(np.mean(np.abs(a0 - yy))), "new_MAE": float(np.mean(np.abs(a1 - yy))), "old_MSE": float(np.mean((a0 - yy) ** 2)), "new_MSE": float(np.mean((a1 - yy) ** 2)), "delta_demeaned_MSE": float(np.mean(((a1 - a1.mean()) - (yy - yy.mean())) ** 2) - np.mean(((a0 - a0.mean()) - (yy - yy.mean())) ** 2))})
        if old.startswith("Rank ") or new.startswith("Rank "):
            for col in ("old_MAE", "new_MAE", "old_MSE", "new_MSE", "delta_demeaned_MSE"):
                row[col] = np.nan
        rows.append(row)
    return pd.DataFrame(rows), joined


def block_summary(paired):
    """Report complete calendar blocks; few blocks receive no confidence band."""
    rows = []
    blocks = []
    rng = np.random.default_rng(109)
    groups = ["horizon", "target", "phase", "delay", "source", "old", "new"]
    for values, g in paired.groupby(groups, observed=True):
        h = int(values[0])
        g = g.sort_values("origin_at").copy()
        start = g.origin_at.min()
        full_end = g.origin_at.max() + pd.Timedelta(days=4)
        g["block"] = ((g.origin_at - start).dt.days // h).astype(int)
        goodblocks = []
        for block, b in g.groupby("block"):
            if start + pd.Timedelta(days=(block + 1) * h) > full_end:
                continue
            delta = b.delta_IC.dropna()
            if len(delta):
                mean = float(delta.mean())
                goodblocks.append(mean)
                blocks.append(dict(zip(groups, values)) | {"block": block, "start": start + pd.Timedelta(days=block * h), "delta_IC": mean, "defined_origins": len(delta)})
        diff = g.delta_IC.dropna().to_numpy()
        lower = upper = np.nan
        if len(goodblocks) >= 8:
            draws = rng.choice(np.asarray(goodblocks), size=(2000, len(goodblocks)), replace=True).mean(axis=1)
            lower, upper = np.quantile(draws, [0.025, 0.975])
        old_mae = g.old_MAE.mean()
        rows.append(dict(zip(groups, values)) | {"paired_origins": len(g), "defined_IC_origins": len(diff), "mean_delta_IC": float(np.mean(diff)) if len(diff) else np.nan, "old_mean_IC": g.old_IC.mean(), "new_mean_IC": g.new_IC.mean(), "MAE_change_fraction": g.new_MAE.mean() / old_mae - 1 if old_mae > 0 else np.nan, "calendar_blocks": len(goodblocks), "positive_blocks": int(np.sum(np.asarray(goodblocks) > 0)), "lower_block_band": lower, "upper_block_band": upper, "inference": "exploratory block interval" if len(goodblocks) >= 8 else "insufficient independent evaluation blocks"})
    return pd.DataFrame(rows), pd.DataFrame(blocks)


def coverage_tables(data, models):
    """Keep scheduled, observable, target-valid and fundable counts distinct."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0)]
    rows = []
    for col in EXISTING + K_ALL:
        observed = f[f.anchor_supported]
        rows.append({"feature": col, "scheduled_vault_dates": len(f), "observed_anchor_rows": len(observed), "finite_features": int(np.isfinite(observed[col]).sum()), "coverage": float(np.isfinite(observed[col]).mean()), "missing_among_observed": float((~np.isfinite(observed[col])).mean())})
    feature_coverage = pd.DataFrame(rows)
    labels = data["labels"]
    labels = labels[(labels.origin_at >= START) & labels.delay.eq(0) & labels.origin_at.isin(f.origin_at.unique())]
    labels = labels.merge(f[["origin_at", "pair_id", "anchor_supported"]], on=["origin_at", "pair_id"], validate="many_to_one")
    targets = []
    for h, t in [(h, t) for h in HORIZONS for t in TARGETS]:
        g = labels[labels.horizon.eq(h)]
        obs = g[g.anchor_supported]
        valid = obs[np.isfinite(obs[target_column(t)])]
        targets.append({"horizon": h, "target": t, "scheduled_origins": g.origin_at.nunique(), "valid_origins": valid.origin_at.nunique(), "observed_anchor_rows": len(obs), "valid_labels": len(valid), "label_coverage": len(valid) / len(obs) if len(obs) else np.nan, "right_censored_rows": int(obs.status.eq("administrative_censoring").sum()), "complete_daily_paths": int(obs.status.eq("complete").sum())})
    e = data["eligibility"]
    e = e[e.origin_at >= START].copy()
    e["old05_eligible"] = e.source_inclusion & e.gate_passes & e.current_guard_allows & ~e.blacklisted & ~e.quarantined
    e = e.merge(f[["origin_at", "pair_id", "90d complete"]], on=["origin_at", "pair_id"], validate="one_to_one")
    e["fundable_diagnostic"] = e.old05_eligible & e.can_deposit & e["90d complete"]
    populations = pd.DataFrame([{"Population": name, "Vault/date rows": int(mask.sum()), "Distinct vaults": int(e.loc[mask, "pair_id"].nunique())} for name, mask in [("Scheduled current-snapshot identities", pd.Series(True, index=e.index)), ("Supported daily NAV anchor (may be carried)", e.anchor_supported), ("05 guard/gate eligible (current policy)", e.old05_eligible), ("Permission observation clock unknown", e.permission_time_unknown), ("Eligibility + deposit + 90d sizing history (diagnostic)", e.fundable_diagnostic)]])
    ledger_path = GENERATION / "05/555f345396445f0a/105a4e1ff76ccc45e1ca7082-allocations.csv"
    if ledger_path.exists():
        ledger = pd.read_csv(ledger_path, parse_dates=["Date"])
        allocated = ledger[ledger["Final target (USD)"].gt(0) & ledger.Date.isin(f.origin_at.unique())]
        populations = pd.concat([populations, pd.DataFrame([{"Population": "05 source-equivalent baseline requested positive targets", "Vault/date rows": len(allocated), "Distinct vaults": allocated["Pair id"].nunique()}])], ignore_index=True)
    p = models["predictions"]
    primary = p[p.phase.eq(0) & p.delay.eq(0) & ~p.source]
    model_coverage = primary.groupby(["horizon", "target", "arm", "supported"], observed=True).agg(forecasts=("pair_id", "size"), origins=("origin_at", "nunique"), vaults=("pair_id", "nunique"), partial_history_fraction=("supported_inputs", lambda x: float((x < 30).mean()))).reset_index()
    from k_ratio_forecast_models import ARMS, BASELINES

    inventory = pd.MultiIndex.from_product([HORIZONS, TARGETS, [*ARMS, *BASELINES], [True, False]], names=["horizon", "target", "arm", "supported"])
    model_coverage = model_coverage.set_index(["horizon", "target", "arm", "supported"]).reindex(inventory).reset_index()
    model_coverage[["forecasts", "origins", "vaults"]] = model_coverage[["forecasts", "origins", "vaults"]].fillna(0).astype(int)
    return feature_coverage, pd.DataFrame(targets), populations, model_coverage


def model_diagnostics(models):
    """Calibration, same-row baseline errors and concentration diagnostics."""
    p = models["predictions"]
    p = p[p.phase.eq(0) & p.delay.eq(0) & ~p.source & p.supported & np.isfinite(p.actual)]
    rows = []
    for (h, t, arm), g in p.groupby(["horizon", "target", "arm"], observed=True):
        counts = g.origin_at.value_counts()
        weights = g.origin_at.map(1 / counts).to_numpy()
        pred = g.prediction.to_numpy()
        actual = g.actual.to_numpy()
        scale = g.target_scale.to_numpy()
        if arm.startswith("Rank ") or arm in ("Constant", "Zero return"):
            continue
        if t == "K-ratio":
            pred = np.arcsinh(pred / scale)
            actual = np.arcsinh(actual / scale)
        centered = pred - np.average(pred, weights=weights)
        variance = np.average(centered**2, weights=weights)
        slope = np.average(centered * (actual - np.average(actual, weights=weights)), weights=weights) / variance if variance > 1e-12 else np.nan
        intercept = np.average(actual, weights=weights) - slope * np.average(pred, weights=weights)
        rows.append({"horizon": h, "target": t, "arm": arm, "calibration_slope": slope, "calibration_intercept": intercept, "observations": len(g), "origins": g.origin_at.nunique()})
    controls = []
    for baseline in ("Constant", "Zero return", "Persistence", "Quality/age"):
        dates, _ = paired_comparison(p, baseline, "Existing + K")
        for (h, t), g in dates.groupby(["horizon", "target"], observed=True):
            controls.append({"horizon": h, "target": t, "baseline": baseline, "paired_origins": len(g), "baseline_MAE": g.old_MAE.mean(), "K_model_MAE": g.new_MAE.mean(), "MAE_change_fraction": g.new_MAE.mean() / g.old_MAE.mean() - 1 if g.old_MAE.mean() > 0 else np.nan})
    return pd.DataFrame(rows), pd.DataFrame(controls)


def cohort_and_influence(predictions):
    """Paired age/quality cohorts and leave-vault-out/event-block sensitivities."""
    primary = predictions[predictions.phase.eq(0) & predictions.delay.eq(0) & ~predictions.source]
    paired, joined = paired_comparison(primary)
    rows = []
    for cohort, mask in [("All paired", np.ones(len(joined), bool)), ("Recorded history <180d", joined.age_days_old.lt(180)), ("Recorded history >=180d", joined.age_days_old.ge(180)), ("High observed coverage", joined.observed_fraction_90_old.ge(0.95)), ("Partial supported inventory", joined.supported_inputs_old.lt(joined.supported_input_count_old)), ("Complete supported inventory", joined.supported_inputs_old.eq(joined.supported_input_count_old))]:
        selected = joined.loc[mask]
        for (h, t), g in selected.groupby(["horizon", "target"], observed=True):
            values = [rho(d.prediction_new, d.actual_new) - rho(d.prediction_old, d.actual_old) for _, d in g.groupby("origin_at")]
            rows.append({"cohort": cohort, "horizon": h, "target": t, "paired_rows": len(g), "origins": g.origin_at.nunique(), "mean_delta_IC": float(np.nanmean(values)) if np.isfinite(values).any() else np.nan})
    influence = []
    for (h, t), g in joined.groupby(["horizon", "target"], observed=True):
        by_date = []
        for origin, d in g.groupby("origin_at"):
            base = rho(d.prediction_new, d.actual_new) - rho(d.prediction_old, d.actual_old)
            by_date.append((origin, base))
        for pid in g.pair_id.unique():
            values = []
            for origin, d in g.groupby("origin_at"):
                reduced = d[d.pair_id != pid]
                values.append(rho(reduced.prediction_new, reduced.actual_new) - rho(reduced.prediction_old, reduced.actual_old))
            finite = np.asarray(values)[np.isfinite(values)]
            if len(finite):
                influence.append({"horizon": h, "target": t, "removed_vault": pid, "mean_delta_IC": float(finite.mean())})
    return pd.DataFrame(rows), pd.DataFrame(influence)


def analyse(data, models):
    """Persist reusable complete results, with bounded presentation downstream."""
    fingerprint = sha256(__file__) + data["manifest"]["module_sha256"] + sha256(__file__.replace("statistics", "models"))
    manifest = ARTIFACT_DIR / "statistics-manifest.json"
    names = ("feature_dates", "feature_summary", "quarterly", "bins", "model_dates", "model_summary", "paired_dates", "paired_summary", "blocks", "feature_coverage", "target_coverage", "populations", "model_coverage", "cohorts", "influence", "long_k_summary")
    if manifest.exists() and json.loads(manifest.read_text()).get("fingerprint") == fingerprint:
        return {name: pd.read_parquet(ARTIFACT_DIR / f"{name}.parquet") for name in names}
    fd, fs, q, b = feature_evidence(data)
    md = date_predictions(models["predictions"])
    summary = md.groupby(["horizon", "target", "arm", "phase", "delay", "source"], observed=True).agg(mean_IC=("IC", "mean"), MAE=("MAE", "mean"), MSE=("MSE", "mean"), raw_MAE=("raw_MAE", "mean"), demeaned_MSE=("demeaned_MSE", "mean"), evaluation_origins=("origin_at", "nunique"), defined_IC_origins=("IC", "count"), mean_vaults=("vaults", "mean")).reset_index()
    pairframes = []
    for a, c in [("Existing", "Existing + K"), ("Compact", "Compact + K"), ("Persistence + existing", "Persistence + existing + K"), ("Existing missing=False", "Existing + K missing=False"), ("Existing complete-case", "Existing + K complete-case"), ("Rank existing", "Rank existing + K"), ("Activity existing", "Activity existing + K"), ("Compact controls existing", "Compact controls existing + K")]:
        p, _ = paired_comparison(models["predictions"], a, c)
        if len(p):
            pairframes.append(p)
    pairs = pd.concat(pairframes, ignore_index=True)
    ps, blocks = block_summary(pairs)
    long_pairs = []
    for arm in ("Existing + short K + year", "Existing + short K + max", "Existing + K"):
        comparison, _ = paired_comparison(models["predictions"], "Existing + short K", arm)
        if len(comparison):
            long_pairs.append(comparison)
    long_summary, _ = block_summary(pd.concat(long_pairs, ignore_index=True))
    fc, tc, pop, mc = coverage_tables(data, models)
    cohorts, influence = cohort_and_influence(models["predictions"])
    result = dict(zip(names, (fd, fs, q, b, md, summary, pairs, ps, blocks, fc, tc, pop, mc, cohorts, influence, long_summary)))
    for name, frame in result.items():
        frame.to_parquet(ARTIFACT_DIR / f"{name}.parquet", index=False)
    manifest.write_text(json.dumps({"fingerprint": fingerprint, "formal_p_values": False, "uncertainty": "Exploratory calendar-block bands only where >=8 full blocks. No uncorrected multiple-test significance claims."}, indent=2))
    return result
