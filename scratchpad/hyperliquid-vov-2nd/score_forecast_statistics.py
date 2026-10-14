"""Causal forecast diagnostics and frozen monthly admission-floor calibration.

Scores are ranking signals. Realised targets and out-of-time calibration remain
separate; no score coefficient or admission rule is chosen on validation output.
"""

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, theilslopes
from tqdm_loggable.auto import tqdm

FOCAL_METHODS = ("v11", "blend_46d", "focal_four")
TARGETS = {"cagr": "future_cagr", "sharpe": "future_sharpe", "volatility": "realised_volatility"}
PERIOD_STARTS = {"2026": pd.Timestamp("2026-01-01"), "Long": pd.Timestamp("2023-03-01")}
END = pd.Timestamp("2026-10-05")
SEED = 108
BOOTSTRAPS = 399
CALIBRATION_VERSION = 2
#: The preceding diagnostic generation differs only in calibration support.
CALIBRATION_MIGRATION_SOURCE = "ea17d71e250e613750edd017dea2eb17f6893c037c622c8744c1dbb7306f4009"
THRESHOLD_RULE = {
    "primary_horizon_days": 30,
    "floors": [round(i / 10, 1) for i in range(11)],
    "min_vaults": 10,
    "min_origins": 20,
    "min_independent_blocks": 3,
    "confidence": 0.95,
    "choose": "lowest floor with simultaneous upper net-log-return bound below zero",
    "monthly_anchor": "first scheduled four-day origin on or after month start",
    "training": "target_observed_at and nav_target_at strictly before calibration origin",
    "secondary": "fixed contemporaneous eligible-score 75th percentile",
    "unknown_scores": "retain source policy; never coerce a missing score to zero",
    "costs": "source-modelled NAV redemption net: 0.1% capital allowance and 10% positive-gain fee; exploratory, not measured live costs",
    "cash_yield": 0.0,
    "allocation": ["slot_to_cash", "renormalise_within_caps"],
}


def artifact_dir(data):
    """Resolve generated output beside the pinned data generation."""
    candidate = data.get("artifact_dir") or data.get("provenance", {}).get("artifact_dir")
    if candidate:
        return Path(candidate)
    return Path(__file__).parent / "_artifacts-restored-2026-10-07" / "08"


def freeze_threshold_rule(data):
    """Write the predeclared selection rule before inspecting validation results."""
    folder = artifact_dir(data)
    folder.mkdir(parents=True, exist_ok=True)
    payload = dict(THRESHOLD_RULE, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    path = folder / "threshold-rule.json"
    path.write_text(json.dumps(payload, indent=2))
    return payload


def join_method(data, method_id, h, period="2026", delay=0, population="eligible"):
    """Join one score recipe to shared causal labels without dropping missing scores."""
    scores = data["scores"]
    mask = scores.method_id.eq(method_id) & scores.origin_at.ge(PERIOD_STARTS[period]) & scores.origin_at.lt(END)
    frame = scores.loc[mask].copy()
    labels = data["labels"]
    labels = labels[labels.lookahead_days.eq(h) & labels.delay_days.eq(delay)]
    frame = frame.merge(labels, on=["origin_at", "pair_id"], how="left", validate="one_to_one")
    eligibility = data.get("eligibility")
    if eligibility is not None:
        extra = [c for c in eligibility.columns if c not in frame.columns or c in ("origin_at", "pair_id")]
        if len(extra) > 2:
            frame = frame.merge(eligibility[extra], on=["origin_at", "pair_id"], how="left", validate="one_to_one")
    if "eligible_as_of_origin" not in frame:
        frame["eligible_as_of_origin"] = False
    if population == "eligible":
        frame = frame[frame.eligible_as_of_origin.fillna(False)].copy()
    elif population != "observed":
        raise ValueError(f"Unknown population: {population}")
    frame["score_missing"] = ~np.isfinite(frame.score)
    frame["origin_quarter"] = frame.origin_at.dt.to_period("Q").astype(str)
    # Average ranks preserve ties rather than arbitrarily filling rank buckets.
    frame["rank_percentile"] = frame.groupby("origin_at").score.rank(method="average", pct=True)
    frame["rank"] = frame.groupby("origin_at").score.rank(method="average", ascending=False)
    return frame


def finite_pair(frame, target):
    """Keep genuine finite pairs; zero scores and zero returns are valid."""
    return frame[np.isfinite(frame.score) & np.isfinite(frame[target])].copy()


def matured_before(frame, origin):
    """Require completed-candle availability as well as a known endpoint mark."""
    mask = frame.origin_at.lt(origin) & frame.nav_target_at.lt(origin) & frame.target_observed_at.lt(origin)
    if "label_available_at" in frame:
        mask &= frame.label_available_at.lt(origin)
    return mask


def correlations(x, y):
    """Return descriptive correlations without unadjusted IID significance."""
    good = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[good], np.asarray(y)[good]
    if len(x) < 3 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return np.nan, np.nan
    rho = float(spearmanr(x, y).statistic)
    # Scale before centring, then explicitly mark numerically constant vectors.
    # A score can have genuine ranks but insufficient precision for Pearson.
    xs, ys = np.max(np.abs(x)), np.max(np.abs(y))
    a, b = x / (xs if xs else 1.0), y / (ys if ys else 1.0)
    am, bm = np.mean(a), np.mean(b)
    a, b = a - am, b - bm
    an, bn = np.linalg.norm(a), np.linalg.norm(b)
    precision = np.finfo(float).eps ** 0.75
    if an == 0 or bn == 0 or an < precision * abs(am) or bn < precision * abs(bm):
        return rho, np.nan
    return rho, float(np.clip(np.dot(a / an, b / bn), -1.0, 1.0))


def finite_median(values):
    """Return missing for an unsupported median without calling an empty reducer."""
    array = np.asarray(values)
    valid = array[np.isfinite(array)]
    return float(np.median(valid)) if len(valid) else np.nan


def date_ic(frame, target):
    """Measure within-date ranking with explicit thin/tied-cohort support."""
    # At a fixed horizon CAGR and log return have the same mathematical ranks.
    # Log space prevents exponent overflow or rounded-to-minus-one loss ties.
    rank_target = "future_log_return" if target == "future_cagr" else target
    rows = []
    for date, group in frame.groupby("origin_at", sort=True):
        paired = finite_pair(group, rank_target)
        count = len(paired)
        distinct = paired.score.nunique()
        rho, _ = correlations(paired.score.to_numpy(), paired[rank_target].to_numpy())
        supported = count >= 10 and distinct >= 5 and np.isfinite(rho)
        reason = "supported" if supported else ("fewer_than_10_vaults" if count < 10 else "fewer_than_5_score_ranks" if distinct < 5 else "constant_target")
        rows.append({"origin_at": date, "origin_quarter": str(date.to_period("Q")), "ic": rho, "paired_vaults": count, "distinct_scores": distinct, "tie_fraction": 1 - distinct / count if count else np.nan, "supported": supported, "support_flag": reason, "rank_target": rank_target})
    return pd.DataFrame(rows)


def regular_series(dates, values):
    """Retain absent four-day baskets instead of compressing calendar gaps."""
    if len(dates) == 0:
        return np.array([])
    series = pd.Series(np.asarray(values), index=pd.DatetimeIndex(dates)).sort_index()
    return series.reindex(pd.date_range(series.index.min(), series.index.max(), freq="4D")).to_numpy()


def block_length(values, h):
    """Use at least one target horizon and extend for persistent date-level IC."""
    minimum = int(np.ceil(h / 4))
    maximum = max(minimum, min(len(values) // 3, minimum * 3))
    selected = minimum
    for lag in range(minimum, maximum + 1):
        a, b = values[:-lag], values[lag:]
        mask = np.isfinite(a) & np.isfinite(b)
        if mask.sum() < 10 or np.std(a[mask]) == 0 or np.std(b[mask]) == 0:
            break
        correlation = np.corrcoef(a[mask], b[mask])[0, 1]
        if correlation > 0.1:
            selected = lag + 1
        else:
            break
    return min(maximum, selected)


def moving_draws(matrix, block, rng, draws=BOOTSTRAPS):
    """Resample whole origin baskets jointly, retaining all within-date dependence."""
    matrix = np.asarray(matrix)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    n = len(matrix)
    starts = rng.integers(0, max(n - block + 1, 1), size=(draws, int(np.ceil(n / block))))
    index = (starts[:, :, None] + np.arange(block)).reshape(draws, -1)[:, :n]
    index = np.minimum(index, n - 1)
    # Empty candidate bins can be absent on sampled baskets; preserve that absence.
    sampled = matrix[index]
    denominator = np.isfinite(sampled).sum(axis=1)
    numerator = np.nansum(sampled, axis=1)
    return np.divide(numerator, denominator, out=np.full(numerator.shape, np.nan), where=denominator > 0)


def uncertainty(ic, h, period, seed=SEED):
    """Summarise supported IC with moving blocks and a HAC cross-check."""
    valid = ic[ic.supported & np.isfinite(ic.ic)].copy()
    base = {"mean_ic": valid.ic.mean(), "median_ic": finite_median(valid.ic), "positive_date_fraction": valid.ic.gt(0).mean() if len(valid) else np.nan, "supported_origins": len(valid), "paired_origins": int(ic.paired_vaults.gt(0).sum()), "mean_paired_vaults": valid.paired_vaults.mean(), "mean_tie_fraction": valid.tie_fraction.mean(), "ic_lower": np.nan, "ic_upper": np.nan, "hac_se": np.nan, "effective_origins": np.nan, "minimum_detectable_ic": np.nan, "nonoverlap_mean_ic": np.nan, "nonoverlap_origins": 0, "independent_blocks": 0, "block_origins": int(np.ceil(h / 4)), "inference_status": "insufficient_support"}
    if valid.empty:
        return base
    values = regular_series(valid.origin_at, valid.ic)
    block = block_length(values, h)
    independent = len(values) // block
    base.update(block_origins=block, independent_blocks=independent)
    previous = None
    selected = []
    for row in valid.itertuples():
        if previous is None or (row.origin_at - previous).days >= h:
            selected.append(row.ic)
            previous = row.origin_at
    base.update(nonoverlap_mean_ic=float(np.mean(selected)), nonoverlap_origins=len(selected))
    if period == "2026" and h == 90:
        base["inference_status"] = "short_90_day_descriptive_only"
        return base
    if independent < 3 or len(valid) < 20:
        return base
    draws = moving_draws(values, block, np.random.default_rng(seed))[:, 0]
    lo, hi = np.nanquantile(draws, [0.025, 0.975])
    mean = np.nanmean(values)
    residual = values - mean
    variance = np.nanmean(residual**2)
    long_run = variance
    for lag in range(1, min(block, len(values) - 1) + 1):
        a, b = residual[:-lag], residual[lag:]
        mask = np.isfinite(a) & np.isfinite(b)
        if mask.any():
            long_run += 2 * (1 - lag / (block + 1)) * np.mean(a[mask] * b[mask])
    se = np.sqrt(max(long_run, 0) / len(valid))
    effective = min(len(valid), variance / se**2) if se > 0 else np.nan
    base.update(ic_lower=lo, ic_upper=hi, hac_se=se, effective_origins=effective, minimum_detectable_ic=2.8 * se, inference_status="conditional_exploratory_block_interval")
    return base


def pooled_summary(frame, target):
    """Supplement date IC with pooled, log-space and equal-vault sensitivity."""
    paired = finite_pair(frame, target)
    rho, pearson = correlations(paired.score.to_numpy(), paired[target].to_numpy())
    log_pair = finite_pair(frame, "future_log_return")
    _, log_pearson = correlations(log_pair.score.to_numpy(), log_pair.future_log_return.to_numpy())
    vault_means = paired.groupby("pair_id")[["score", target]].mean()
    vault_rho, _ = correlations(vault_means.score.to_numpy(), vault_means[target].to_numpy())
    slope = np.nan
    # A bounded deterministic sample prevents quadratic Theil--Sen work on the full panel.
    if len(log_pair) >= 3 and log_pair.score.nunique() > 1:
        sampled = log_pair.iloc[np.linspace(0, len(log_pair) - 1, min(len(log_pair), 500), dtype=int)]
        slope = float(theilslopes(sampled.future_log_return, sampled.score).slope)
    return {"pooled_spearman": rho, "pooled_pearson": pearson, "log_return_pearson": log_pearson, "equal_vault_mean_spearman": vault_rho, "robust_log_slope": slope, "paired_rows": len(paired), "distinct_vaults": paired.pair_id.nunique()}


def bin_summary(frame, kind="score"):
    """Summarise fixed absolute bins or tie-preserving rank bands."""
    frame = frame[np.isfinite(frame.score)].copy()
    if kind == "score":
        frame["bin"] = np.minimum(np.floor(frame.score * 10), 9).astype(int)
    else:
        frame["bin"] = pd.cut(frame["rank"], bins=[0, 6, 7, 8, 10, np.inf], labels=["1–6", "7", "8", "9–10", ">10"]).astype(str)
    rows = []
    for bucket, group in frame.groupby("bin", observed=True):
        valid = group[np.isfinite(group.future_return)]
        dates = valid.groupby("origin_at").future_return.mean()
        rows.append({"bin": bucket, "rows": len(group), "target_rows": len(valid), "origin_count": valid.origin_at.nunique(), "vault_count": valid.pair_id.nunique(), "mean_return": valid.future_return.mean(), "equal_date_mean_return": dates.mean(), "median_return": finite_median(valid.future_return), "mean_cagr": valid.future_cagr.mean(), "median_cagr": finite_median(valid.future_cagr), "mean_sharpe": valid.future_sharpe.replace([np.inf, -np.inf], np.nan).mean(), "median_sharpe": finite_median(valid.future_sharpe), "loss_probability": valid.future_return.lt(0).mean() if len(valid) else np.nan, "material_loss_probability": valid.future_return.le(-0.10).mean() if len(valid) else np.nan, "return_q05": valid.future_return.quantile(0.05), "target_attrition_fraction": 1 - len(valid) / len(group) if len(group) else np.nan, "mean_score": group.score.mean()})
    return pd.DataFrame(rows)


def coverage_summary(frame):
    """Keep zero scores, missing scores and missing/flat targets as separate cohorts."""
    rows = []
    for name, group in [("all", frame), ("valid_score", frame[np.isfinite(frame.score)]), ("missing_score", frame[~np.isfinite(frame.score)]), ("zero_score", frame[frame.score.eq(0)])]:
        valid = group[np.isfinite(group.future_return)]
        rows.append({"cohort": name, "rows": len(group), "origin_count": group.origin_at.nunique(), "vault_count": group.pair_id.nunique(), "matured_return_rows": len(valid), "matured_sharpe_rows": int(np.isfinite(group.future_sharpe).sum()), "mean_return": valid.future_return.mean(), "median_return": finite_median(valid.future_return), "loss_probability": valid.future_return.lt(0).mean() if len(valid) else np.nan, "score_fraction": np.isfinite(group.score).mean() if len(group) else np.nan, "low_variance_rows": int(group.low_variance.fillna(False).sum()), "last_matured_origin": valid.origin_at.max(), "unknown_eligibility_rows": int(group.get("eligibility_time_unknown", pd.Series(False, index=group.index)).fillna(False).sum())})
    return pd.DataFrame(rows)


def sensitivity_summary(frame, h):
    """Reveal quarter/vault concentration and low-variance Sharpe dependence."""
    rows = []
    for outcome in ("cagr", "sharpe"):
        target = TARGETS[outcome]
        initial = date_ic(frame, target)
        mean = initial.loc[initial.supported, "ic"].mean()
        for quarter in sorted(frame.origin_quarter.unique()):
            ic = date_ic(frame[frame.origin_quarter.ne(quarter)], target)
            value = ic.loc[ic.supported, "ic"].mean()
            rows.append({"sensitivity": "leave_quarter_out", "excluded": quarter, "outcome": outcome, "mean_ic": value, "baseline_ic": mean, "difference": value - mean, "supported_origins": int(ic.supported.sum())})
        if outcome == "sharpe":
            ic = date_ic(frame[~frame.low_variance.fillna(False)], target)
            value = ic.loc[ic.supported, "ic"].mean()
            rows.append({"sensitivity": "exclude_low_variance", "excluded": "daily_sigma_below_0.0001", "outcome": outcome, "mean_ic": value, "baseline_ic": mean, "difference": value - mean, "supported_origins": int(ic.supported.sum())})
        # Rank correlations use averaged ranks. Re-rank after removing a vault,
        # rather than pretending that frozen ranks give an exact leave-out result.
        leave_target = "future_log_return" if outcome == "cagr" else target
        valid = finite_pair(frame, leave_target)
        influences = []
        for date, group in valid.groupby("origin_at"):
            if len(group) < 11 or group.score.nunique() < 5:
                continue
            x, y = group.score.to_numpy(), group[leave_target].to_numpy()
            # Removing a tied observation shifts higher ranks by one and other
            # members of its tie by one half. This is exact averaged re-ranking.
            xr = pd.Series(x).rank(method="average").to_numpy()
            yr = pd.Series(y).rank(method="average").to_numpy()
            a = xr[None, :] - (x[:, None] < x[None, :]) - 0.5 * (x[:, None] == x[None, :])
            b = yr[None, :] - (y[:, None] < y[None, :]) - 0.5 * (y[:, None] == y[None, :])
            np.fill_diagonal(a, np.nan)
            np.fill_diagonal(b, np.nan)
            a -= np.nanmean(a, axis=1, keepdims=True)
            b -= np.nanmean(b, axis=1, keepdims=True)
            denominator = np.sqrt(np.nansum(a * a, axis=1) * np.nansum(b * b, axis=1))
            correlations_without = np.divide(np.nansum(a * b, axis=1), denominator, out=np.full(len(x), np.nan), where=denominator > 0)
            counts = pd.Series(x).value_counts()
            for index, pair in enumerate(group.pair_id):
                distinct_after = len(counts) - int(counts.loc[x[index]] == 1)
                if distinct_after >= 5 and np.isfinite(correlations_without[index]):
                    influences.append((pair, date, correlations_without[index]))
        if influences:
            influence = pd.DataFrame(influences, columns=["pair_id", "origin_at", "ic"])
            # Missing dates retain their baseline IC; affected date IC is recomputed.
            baseline = initial[initial.supported].set_index("origin_at").ic
            for pair, group in influence.groupby("pair_id"):
                changed = baseline.copy()
                changed.loc[group.origin_at] = group.ic.to_numpy()
                value = changed.mean()
                rows.append({"sensitivity": "leave_vault_out", "excluded": str(pair), "outcome": outcome, "mean_ic": value, "baseline_ic": mean, "difference": value - mean, "supported_origins": len(changed)})
    return pd.DataFrame(rows)


def isotonic_fit(x, y, weights, increasing=True):
    """Fit a small weighted PAV model with score ties combined before fitting."""
    work = pd.DataFrame({"x": x, "wy": y * weights, "w": weights}).groupby("x").sum().sort_index()
    levels = (work.wy / work.w).to_numpy() * (1 if increasing else -1)
    masses = work.w.to_numpy()
    blocks = []
    for i, (level, mass) in enumerate(zip(levels, masses)):
        blocks.append([i, i, float(level), float(mass)])
        while len(blocks) >= 2 and blocks[-2][2] > blocks[-1][2]:
            b, a = blocks.pop(), blocks.pop()
            weight = a[3] + b[3]
            blocks.append([a[0], b[1], (a[2] * a[3] + b[2] * b[3]) / weight, weight])
    fitted = np.empty(len(work))
    for first, last, level, _ in blocks:
        fitted[first : last + 1] = level * (1 if increasing else -1)
    return work.index.to_numpy(), fitted


def calibration_forecasts(frame, method_id, h):
    """Fit monthly mappings only to labels known before each validation origin."""
    rows = []
    origins = sorted(frame.origin_at.unique())
    monthly = {}
    for date in origins:
        date = pd.Timestamp(date)
        monthly.setdefault(str(date.to_period("M")), date)
    for month, origin in monthly.items():
        train = frame[matured_before(frame, origin) & np.isfinite(frame.score)].copy()
        validation = frame[frame.origin_at.dt.to_period("M").astype(str).eq(month) & np.isfinite(frame.score)].copy()
        if train.origin_at.nunique() < 20 or train.pair_id.nunique() < 10:
            continue
        for outcome, target in [("log_return", "future_log_return"), ("sharpe", "future_sharpe"), ("loss", "future_return")]:
            training = train[np.isfinite(train[target])].copy()
            if len(training) < 100 or training.score.nunique() < 2 or training.origin_at.nunique() < 20 or training.pair_id.nunique() < 10:
                continue
            y = training[target].to_numpy()
            if outcome == "loss":
                y = (y < 0).astype(float)
            elif outcome == "sharpe":
                # Winsorisation is learnt inside the training fold only; validation
                # errors still use every finite realised Sharpe without clipping.
                y = np.clip(y, *np.quantile(y, [0.01, 0.99]))
            x = training.score.to_numpy()
            weights = (1 / training.groupby("origin_at").score.transform("size")).to_numpy()
            weights = weights / weights.sum()
            constant = float(np.sum(y * weights))
            design = np.column_stack([np.ones(len(x)), x])
            beta = np.linalg.lstsq(design * np.sqrt(weights[:, None]), y * np.sqrt(weights), rcond=None)[0]
            iso_x, iso_y = isotonic_fit(x, y, weights, increasing=outcome != "loss")
            vx = validation.score.to_numpy()
            forecasts = {"constant": np.full(len(vx), constant), "linear": beta[0] + beta[1] * vx, "isotonic": np.interp(vx, iso_x, iso_y)}
            actual = validation[target].to_numpy()
            if outcome == "loss":
                actual = np.where(np.isfinite(actual), (actual < 0).astype(float), np.nan)
            for model, prediction in forecasts.items():
                if outcome == "loss":
                    prediction = np.clip(prediction, 0, 1)
                for index, row in enumerate(validation.itertuples()):
                    rows.append({"method_id": method_id, "lookahead_days": h, "origin_at": row.origin_at, "pair_id": row.pair_id, "calibration_at": origin, "outcome": outcome, "model": model, "prediction": prediction[index], "actual": actual[index], "training_origins": training.origin_at.nunique(), "training_vaults": training.pair_id.nunique(), "latest_training_target": training.nav_target_at.max(), "latest_training_available": training.label_available_at.max() if "label_available_at" in training else training.target_observed_at.max(), "latest_training_observed": training.target_observed_at.max()})
    return pd.DataFrame(rows)


def calibration_metrics(predictions):
    """Evaluate conditional chronological predictions on equal-weight date baskets."""
    predictions = predictions[predictions.training_origins.ge(20) & predictions.training_vaults.ge(10)]
    rows = []
    for period, start in PERIOD_STARTS.items():
        subset = predictions[predictions.origin_at.ge(start)]
        for keys, group in subset.groupby(["method_id", "lookahead_days", "outcome", "model"]):
            group = group[np.isfinite(group.actual) & np.isfinite(group.prediction)].copy()
            if group.empty:
                continue
            group["squared_error"] = (group.prediction - group.actual) ** 2
            group["absolute_error"] = abs(group.prediction - group.actual)
            by_date = group.groupby("origin_at")[["squared_error", "absolute_error"]].mean()
            rows.append(dict(zip(["method_id", "lookahead_days", "outcome", "model"], keys), period=period, rows=len(group), origin_count=group.origin_at.nunique(), vault_count=group.pair_id.nunique(), equal_date_mse=by_date.squared_error.mean(), equal_date_mae=by_date.absolute_error.mean(), median_absolute_error=finite_median(group.absolute_error), brier_score=by_date.squared_error.mean() if keys[2] == "loss" else np.nan, validation_status="conditional_chronological_not_untouched"))
    return pd.DataFrame(rows)


def calibration_support(predictions):
    """Label retained thin forecasts and count actual supported validation origins."""
    predictions = predictions.copy()
    if predictions.empty:
        return predictions, pd.DataFrame()
    predictions["training_supported"] = predictions.training_origins.ge(20) & predictions.training_vaults.ge(10)
    predictions["forecast_status"] = np.where(predictions.training_supported, "supported_training", "thin_training_exploratory")
    rows = []
    baseline = predictions[predictions.model.eq("constant")]
    for period, start in PERIOD_STARTS.items():
        subset = baseline[baseline.origin_at.ge(start)]
        for keys, group in subset.groupby(["method_id", "lookahead_days", "outcome"]):
            actual = group[np.isfinite(group.actual) & np.isfinite(group.prediction)]
            supported = actual[actual.training_supported]
            thin = actual[~actual.training_supported]
            count = supported.origin_at.nunique()
            rows.append(dict(zip(["method_id", "lookahead_days", "outcome"], keys), period=period, validation_origins=actual.origin_at.nunique(), supported_origins=count, excluded_origins=thin.origin_at.nunique(), supported_rows=len(supported), excluded_rows=len(thin), min_training_origins=actual.training_origins.min(), status="no_supported_validation" if count == 0 else "too_few_supported_validation_origins" if count < 3 else "conditional_chronological_not_untouched"))
    return predictions, pd.DataFrame(rows)


def threshold_training(train, origin, method_id, h=30):
    """Select the lowest supported floor using simultaneous training-only bounds."""
    floors = np.asarray(THRESHOLD_RULE["floors"])
    dates = pd.date_range(train.origin_at.min(), train.origin_at.max(), freq="4D") if len(train) else pd.DatetimeIndex([])
    matrix = np.full((len(dates), len(floors)), np.nan)
    records = []
    fee_known = "future_net_log_return" in train and np.isfinite(train.future_net_log_return).any()
    for column, floor in enumerate(floors):
        below = train[np.isfinite(train.score) & train.score.lt(floor) & np.isfinite(train.future_log_return)]
        net = below[np.isfinite(below.future_net_log_return)] if fee_known else below.iloc[:0]
        date_means = net.groupby("origin_at").future_net_log_return.mean() if fee_known else pd.Series(dtype=float)
        if len(dates):
            matrix[:, column] = date_means.reindex(dates).to_numpy()
        origins = date_means.size
        span = (date_means.index.max() - date_means.index.min()).days + 4 if origins else 0
        blocks = min(span // h, origins // int(np.ceil(h / 4)))
        support = origins >= 20 and net.pair_id.nunique() >= 10 and blocks >= 3
        records.append({"method_id": method_id, "lookahead_days": h, "calibration_at": origin, "floor": floor, "training_rows": len(below), "training_origins": origins, "training_vaults": net.pair_id.nunique(), "independent_blocks": blocks, "supported": support, "mean_gross_log_return": below.groupby("origin_at").future_log_return.mean().mean(), "mean_net_log_return": date_means.mean(), "simultaneous_upper": np.nan, "fees_known": False, "source_modelled_costs": fee_known, "costs_status": "source_modelled_net_exploratory" if fee_known else "unknown_costs", "training_target_latest": train.nav_target_at.max() if len(train) else pd.NaT})
    supported = np.array([r["supported"] for r in records])
    if supported.any():
        draws = moving_draws(matrix[:, supported], int(np.ceil(h / 4)), np.random.default_rng(SEED + origin.year * 12 + origin.month))
        estimates = np.nanmean(matrix[:, supported], axis=0)
        sigma = np.nanstd(draws, axis=0, ddof=1)
        valid = sigma > 0
        standardized = np.divide(draws - estimates, sigma, out=np.zeros_like(draws), where=valid)
        available = np.isfinite(standardized)
        maximum = np.max(np.where(available, standardized, -np.inf), axis=1)
        maximum = maximum[np.isfinite(maximum)]
        critical = max(float(np.quantile(maximum, 0.95)), 0) if len(maximum) else np.inf
        for index, mean, deviation in zip(np.flatnonzero(supported), estimates, sigma):
            records[index]["simultaneous_upper"] = mean + critical * deviation
    acceptable = [r for r in records if r["supported"] and np.isfinite(r["simultaneous_upper"]) and r["simultaneous_upper"] < 0]
    chosen = min((r["floor"] for r in acceptable), default=np.nan)
    reason = "negative_simultaneous_net_upper_bound" if acceptable else "no_supported_negative_net_cohort"
    threshold = {"method_id": method_id, "lookahead_days": h, "calibration_at": origin, "floor": chosen, "active": bool(np.isfinite(chosen)), "support_flag": reason, "policy": "monthly_absolute", "percentile": np.nan, "latest_training_target": train.nav_target_at.max() if len(train) else pd.NaT, "latest_training_target_at": train.nav_target_at.max() if len(train) else pd.NaT, "latest_training_observed": train.target_observed_at.max() if len(train) else pd.NaT, "latest_training_available": train.label_available_at.max() if len(train) and "label_available_at" in train else pd.NaT, "costs_status": "source_modelled_net_exploratory" if fee_known else "unknown_costs", "training_origins": train.origin_at.nunique(), "training_vaults": train.pair_id.nunique()}
    return threshold, records


def monthly_thresholds(frame, method_id):
    """Freeze full-history monthly floors, with 2026 selected only for display."""
    origins = pd.DatetimeIndex(sorted(frame.origin_at.unique()))
    monthly = {}
    for origin in origins:
        monthly.setdefault(str(origin.to_period("M")), origin)
    thresholds, training_rows = [], []
    for origin in monthly.values():
        train = frame[matured_before(frame, origin) & np.isfinite(frame.score) & np.isfinite(frame.future_log_return)].copy()
        threshold, evidence = threshold_training(train, origin, method_id)
        thresholds.append(threshold)
        training_rows.extend(evidence)
        thresholds.append(dict(threshold, policy="percentile_75", percentile=0.75, floor=np.nan, active=True, support_flag="predeclared_not_fitted"))
    return pd.DataFrame(thresholds), pd.DataFrame(training_rows)


def joint_null(data, method_ids, h, period):
    """Joint circular shifts on a genuinely common paired population.

    Rotation of each entire date basket preserves cross-sectional dependence and
    serial ordering except at the wrap. This is a regime-sensitive exploratory
    null, not evidence of an untouched strategy discovery.
    """
    if period == "2026" and h == 90:
        return pd.DataFrame([{"period": period, "lookahead_days": h, "status": "short_90_day_descriptive_only"}])
    scores = data["scores"]
    scores = scores[scores.method_id.isin(method_ids) & scores.origin_at.ge(PERIOD_STARTS[period]) & scores.eligible_as_of_origin]
    wide = scores.pivot(index=["origin_at", "pair_id"], columns="method_id", values="score").dropna()
    # Method IDs are stored categorically for memory. Pandas column joins must
    # use a plain Index to avoid CategoricalIndex membership-slice failures.
    wide.columns = pd.Index(wide.columns.astype(str), dtype=object)
    labels = data["labels"]
    labels = labels[labels.lookahead_days.eq(h) & labels.delay_days.eq(0)]
    joined = wide.join(labels.set_index(["origin_at", "pair_id"])[["future_log_return"]]).dropna()
    if joined.empty:
        return pd.DataFrame([{"period": period, "lookahead_days": h, "status": "no_common_valid_population"}])
    origins = pd.date_range(joined.index.get_level_values("origin_at").min(), joined.index.get_level_values("origin_at").max(), freq="4D")
    if len(origins) * 4 // h < 3:
        return pd.DataFrame([{"period": period, "lookahead_days": h, "status": "fewer_than_three_independent_blocks", "common_rows": len(joined)}])
    # Full common vault paths are needed for a membership-preserving rotation.
    target = joined.future_log_return.unstack("pair_id").reindex(origins)
    persistent = target.columns[target.notna().all()]
    if len(persistent) < 10:
        return pd.DataFrame([{"period": period, "lookahead_days": h, "status": "common_complete_vault_paths_below_10", "common_rows": len(joined), "persistent_vaults": len(persistent)}])
    y = target[persistent].to_numpy()
    yr = pd.DataFrame(y).rank(axis=1, method="average").to_numpy()
    score_ranks = []
    method_ok = []
    for method in method_ids:
        x = joined[method].unstack("pair_id").reindex(index=origins, columns=persistent).to_numpy()
        if not np.isfinite(x).all():
            continue
        if sum(np.unique(row).size >= 5 for row in x) < 20:
            continue
        rank = pd.DataFrame(x).rank(axis=1, method="average").to_numpy()
        score_ranks.append(rank)
        method_ok.append(method)

    def ic_mean(x, target_ranks):
        a = x - x.mean(axis=1, keepdims=True)
        b = target_ranks - target_ranks.mean(axis=1, keepdims=True)
        den = np.sqrt((a * a).sum(axis=1) * (b * b).sum(axis=1))
        values = np.divide((a * b).sum(axis=1), den, out=np.full(len(x), np.nan), where=den > 0)
        return np.nanmean(values) if np.isfinite(values).any() else np.nan

    minimum_shift = int(np.ceil(h / 4)) + 1
    offsets = np.arange(minimum_shift, len(origins) - minimum_shift)
    if len(offsets) < 10 or not method_ok:
        return pd.DataFrame([{"period": period, "lookahead_days": h, "status": "too_few_valid_joint_offsets", "common_rows": len(joined)}])
    offsets = np.random.default_rng(SEED + h).choice(offsets, min(199, len(offsets)), replace=False)
    observed = np.array([ic_mean(x, yr) for x in score_ranks])
    draws = np.array([[ic_mean(x, np.roll(yr, int(offset), axis=0)) for x in score_ranks] for offset in offsets])
    maximum = np.nanmax(draws, axis=1)
    return pd.DataFrame([{"method_id": method, "period": period, "lookahead_days": h, "common_population_ic": value, "family_max_p": (1 + (maximum >= value).sum()) / (len(maximum) + 1), "joint_draws": len(offsets), "common_rows": len(origins) * len(persistent), "persistent_vaults": len(persistent), "status": "exploratory_membership_preserving_circular_shift"} for method, value in zip(method_ok, observed)])


def supplementary_analyses(data):
    """Measure signal decay, delayed starts and stale-score placebos for controls."""
    decay, placebo, incremental = [], [], []
    available_horizons = set(data["labels"].lookahead_days.unique())
    for method in FOCAL_METHODS:
        for h in (1, 2, 4, 7, 14, 30, 60, 90):
            if h not in available_horizons:
                continue
            full = join_method(data, method, h, "Long")
            for period, start in PERIOD_STARTS.items():
                frame = full[full.origin_at.ge(start)]
                for outcome, target in [("log_return", "future_log_return"), ("sharpe", "future_sharpe")]:
                    ic = date_ic(frame, target)
                    if ic.empty:
                        continue
                    decay.append(dict(method_id=method, lookahead_days=h, period=period, delay_days=0, outcome=outcome, **uncertainty(ic, h, period)))
        if data["labels"].delay_days.eq(30).any():
            full = join_method(data, method, 30, "Long", delay=30)
            for period, start in PERIOD_STARTS.items():
                frame = full[full.origin_at.ge(start)]
                ic = date_ic(frame, "future_log_return")
                if not ic.empty:
                    decay.append(dict(method_id=method, lookahead_days=30, period=period, delay_days=30, outcome="log_return", **uncertainty(ic, 60, period)))
        scores = data["scores"][data["scores"].method_id.eq(method)][["origin_at", "pair_id", "score"]]
        full = join_method(data, method, 30, "Long")
        for requested, actual in [(30, 32), (60, 60)]:
            lagged = scores.copy()
            lagged["origin_at"] += pd.Timedelta(days=actual)
            frame = full.drop(columns=["score"]).merge(lagged, on=["origin_at", "pair_id"], how="left", validate="one_to_one")
            for period, start in PERIOD_STARTS.items():
                ic = date_ic(frame[frame.origin_at.ge(start)], "future_log_return")
                if not ic.empty:
                    placebo.append(dict(method_id=method, lookahead_days=30, period=period, requested_lag_days=requested, actual_lag_days=actual, lag_reason="last available four-day score at or before requested lag", **uncertainty(ic, 30, period)))
    focal = join_method(data, "focal_four", 30, "Long")
    core = data["scores"][data["scores"].method_id.eq("v11")][["origin_at", "pair_id", "score"]].rename(columns={"score": "core_score"})
    paired = focal.merge(core, on=["origin_at", "pair_id"], how="left", validate="one_to_one")
    for date, group in paired.groupby("origin_at"):
        for outcome, target in [("log_return", "future_log_return"), ("sharpe", "future_sharpe")]:
            good = group[np.isfinite(group.score) & np.isfinite(group.core_score) & np.isfinite(group[target])]
            if len(good) < 10 or good.core_score.nunique() < 5:
                continue
            design = np.column_stack([np.ones(len(good)), good.core_score])
            x = good.score.to_numpy()
            y = good[target].to_numpy()
            residual_x = x - design @ np.linalg.lstsq(design, x, rcond=None)[0]
            residual_y = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
            rho, _ = correlations(residual_x, residual_y)
            incremental.append({"origin_at": date, "outcome": outcome, "partial_rank_ic": rho, "vault_count": len(good), "method_id": "focal_four", "core_method_id": "v11", "status": "descriptive_linear_core_residual_not_causal"})
    return {"ic_decay": pd.DataFrame(decay), "lagged_score": pd.DataFrame(placebo), "incremental_information": pd.DataFrame(incremental)}


def analyse_data(data, force=False):
    """Compute and persist shared diagnostics, returning compact result frames."""
    folder = artifact_dir(data)
    folder.mkdir(parents=True, exist_ok=True)
    rule = freeze_threshold_rule(data)
    source = data.get("provenance", {}).get("fingerprint", "")
    fingerprint = hashlib.sha256((str(source) + rule["source_sha256"]).encode()).hexdigest()
    completion = folder / "statistics-completed.json"
    if not force and completion.exists():
        old = json.loads(completion.read_text())
        cached_source = old.get("rule", {}).get("source_sha256")
        expected_old = hashlib.sha256((str(source) + str(cached_source)).encode()).hexdigest()
        cached_rule = {k: v for k, v in old.get("rule", {}).items() if k != "source_sha256"}
        migratable = cached_source == CALIBRATION_MIGRATION_SOURCE and old.get("fingerprint") == expected_old and cached_rule == THRESHOLD_RULE
        if old.get("fingerprint") == fingerprint or migratable:
            result = {}
            for name in old["frames"]:
                frame = pd.read_parquet(folder / f'{name.replace("_", "-")}.parquet')
                result[name] = frame
            if migratable or old.get("calibration_version") != CALIBRATION_VERSION:
                predictions, support = calibration_support(result["calibration_predictions"])
                result["calibration_predictions"] = predictions
                result["calibration_support"] = support
                result["calibration_metrics"] = calibration_metrics(predictions) if not predictions.empty else pd.DataFrame()
                for name in ("calibration_predictions", "calibration_support", "calibration_metrics"):
                    frame = result[name]
                    path = folder / f'{name.replace("_", "-")}.parquet'
                    frame.to_parquet(path, index=False)
                    if name != "calibration_predictions":
                        with np.errstate(invalid="ignore"):
                            frame.to_csv(path.with_suffix(".csv"), index=False)
                migration = {"from_fingerprint": old["fingerprint"], "to_fingerprint": fingerprint, "data_fingerprint": str(source), "calibration_version": CALIBRATION_VERSION, "derivation": "Retain old thin forecasts as exploratory; evaluate only per-outcome training >=20 origins and >=10 vaults. Core diagnostics and frozen thresholds unchanged; no refit."}
                (folder / "calibration-cache-migration.json").write_text(json.dumps(migration, indent=2))
                completion.write_text(json.dumps({"fingerprint": fingerprint, "frames": list(result), "rule": rule, "calibration_version": CALIBRATION_VERSION, "cache_migration": migration}, indent=2))
            return result
    method_ids = [row["method_id"] for row in data["registry"]]
    store = {key: [] for key in ("ic_summary", "ic_dates", "quarterly_ic", "coverage", "score_bins", "rank_bands", "robustness", "clipping", "delayed_anchor", "calibration_predictions", "monthly_thresholds", "threshold_training", "joint_null")}
    total = len(PERIOD_STARTS) * len(method_ids) * 3
    progress = tqdm(total=total, desc="Score forecast statistics", mininterval=10)
    started = time.monotonic()
    last_checkpoint = started

    def mark_completed(period, method_id, h):
        nonlocal last_checkpoint
        progress.update(1)
        now = time.monotonic()
        if now - last_checkpoint >= 15 or progress.n == total:
            elapsed = now - started
            (folder / "statistics-progress.json").write_text(
                json.dumps(
                    {
                        "fingerprint": fingerprint,
                        "completed_jobs": progress.n,
                        "total_jobs": total,
                        "period": period,
                        "method_id": method_id,
                        "lookahead_days": h,
                        "elapsed_seconds": elapsed,
                        "estimated_remaining_seconds": elapsed * (total - progress.n) / max(progress.n, 1),
                        "status": "method_diagnostics" if progress.n < total else "joint_null_and_supplementary",
                    },
                    indent=2,
                )
            )
            last_checkpoint = now

    for period in PERIOD_STARTS:
        for method_id in method_ids:
            for h in (7, 30, 90):
                progress.set_postfix(period=period, horizon=h, refresh=False)
                frame = join_method(data, method_id, h, period)
                tags = {"method_id": method_id, "lookahead_days": h, "period": period, "population": "eligible"}
                if frame.empty:
                    store["ic_summary"].append(pd.DataFrame([dict(tags, outcome=outcome, inference_status="empty_population") for outcome in TARGETS]))
                    mark_completed(period, method_id, h)
                    continue
                store["coverage"].append(coverage_summary(frame).assign(**tags))
                store["score_bins"].append(bin_summary(frame).assign(**tags))
                if method_id in FOCAL_METHODS:
                    store["rank_bands"].append(bin_summary(frame, "rank").assign(**tags))
                clipped = frame[np.isfinite(frame.score)]
                store["clipping"].append(pd.DataFrame([dict(tags, rows=len(clipped), zero_fraction=clipped.score.eq(0).mean(), one_fraction=clipped.score.eq(1).mean(), distinct_scores=clipped.score.nunique(), same_date_mean_tie_fraction=clipped.groupby("origin_at").score.apply(lambda s: 1 - s.nunique() / len(s)).mean())]))
                for outcome, target in TARGETS.items():
                    ic = date_ic(frame, target)
                    store["ic_dates"].append(ic.assign(**tags, outcome=outcome))
                    summary = dict(tags, outcome=outcome, **uncertainty(ic, h, period), **pooled_summary(frame, target))
                    store["ic_summary"].append(pd.DataFrame([summary]))
                    for quarter, group in ic.groupby("origin_quarter"):
                        supported = group[group.supported]
                        store["quarterly_ic"].append(pd.DataFrame([dict(tags, outcome=outcome, origin_quarter=quarter, mean_ic=supported.ic.mean(), origin_count=len(supported), paired_origins=int(group.paired_vaults.gt(0).sum()), status="partial_origin_quarter" if h == 90 and quarter == "2026Q3" else "descriptive")]))
                if method_id in FOCAL_METHODS:
                    store["robustness"].append(sensitivity_summary(frame, h).assign(**tags))
                    for delay in (1, 2):
                        delayed = join_method(data, method_id, h, period, delay)
                        for outcome in ("cagr", "sharpe"):
                            ic = date_ic(delayed, TARGETS[outcome])
                            store["delayed_anchor"].append(pd.DataFrame([dict(tags, delay_days=delay, outcome=outcome, **uncertainty(ic, h, period))]))
                    if period == "Long":
                        predictions = calibration_forecasts(frame, method_id, h)
                        store["calibration_predictions"].append(predictions)
                        if h == 30:
                            thresholds, evidence = monthly_thresholds(frame, method_id)
                            store["monthly_thresholds"].append(thresholds)
                            store["threshold_training"].append(evidence)
                mark_completed(period, method_id, h)
        for h in (7, 30, 90):
            # The 74-method family commonly loses almost all complete rows. Report
            # that limitation instead of quietly substituting a hand-picked cohort.
            store["joint_null"].append(joint_null(data, method_ids, h, period).assign(family_scope="registry_all"))
            store["joint_null"].append(joint_null(data, list(FOCAL_METHODS), h, period).assign(family_scope="focal_frozen_controls"))
    progress.close()
    result = {name: pd.concat([f for f in frames if not f.empty], ignore_index=True) if any(not f.empty for f in frames) else pd.DataFrame() for name, frames in store.items()}
    predictions = result["calibration_predictions"]
    predictions, support = calibration_support(predictions)
    result["calibration_predictions"] = predictions
    result["calibration_support"] = support
    result["calibration_metrics"] = calibration_metrics(predictions) if not predictions.empty else pd.DataFrame()
    result.update(supplementary_analyses(data))
    for name, frame in result.items():
        path = folder / f'{name.replace("_", "-")}.parquet'
        frame.to_parquet(path, index=False)
        if name != "calibration_predictions":
            # NumPy casts missing numeric cells to empty CSV fields; this local
            # conversion must not produce notebook warning output.
            with np.errstate(invalid="ignore"):
                frame.to_csv(path.with_suffix(".csv"), index=False)
    completion.write_text(json.dumps({"fingerprint": fingerprint, "frames": list(result), "rule": rule, "calibration_version": CALIBRATION_VERSION}, indent=2))
    (folder / "statistics-progress.json").write_text(json.dumps({"fingerprint": fingerprint, "completed_jobs": total, "total_jobs": total, "status": "complete", "elapsed_seconds": time.monotonic() - started}, indent=2))
    return result
