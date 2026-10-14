"""Chronological, partial-history individual-feature forecasts for experiment 09."""

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits
from tqdm_loggable.auto import tqdm

from k_ratio_features import ARTIFACT_DIR, START, END, EXISTING, K_MAIN, K_ALL, K_SHORT, K_YEAR, K_MAX, HORIZONS, TARGETS, WINDOWS, sha256

COMPACT = ["30d Sharpe", "90d Sharpe", "180d Sharpe", "90d CAGR", "90d Max drawdown"]
DECOMPOSITION = [f"{days}d {metric}" for days in (30, 60, 90, 180) for metric in ("slope", "residual_scale")]
PATH = ["autocorrelation_30", "variance_ratio_30", "positive_fraction_30", "flat_fraction_30"]
CONTROLS = ["log_age", "observed_fraction_90", "freshness_hours", "longest_recent_flat_run", "available_windows", "flat_fraction_30"]
ARMS = {"Existing": EXISTING, "Existing + K": EXISTING + K_MAIN, "Existing + short K": EXISTING + K_SHORT, "Existing + short K + year": EXISTING + K_SHORT + [K_YEAR], "Existing + short K + max": EXISTING + K_SHORT + [K_MAX], "Compact": COMPACT, "Compact + K": COMPACT + K_MAIN, "K alone": K_MAIN, "Decomposition": EXISTING + DECOMPOSITION, "Expanded K": EXISTING + K_ALL, "Path shape": EXISTING + PATH, "Residual K": EXISTING + ["residual_K_30"], "Persistence + existing": EXISTING, "Persistence + existing + K": EXISTING + K_MAIN, "Quality/age": [], "Existing missing=False": EXISTING, "Existing + K missing=False": EXISTING + K_MAIN, "Existing complete-case": EXISTING, "Existing + K complete-case": EXISTING + K_MAIN}
SUPPORTED_INVENTORY = [c for c in EXISTING if int(c.split("d ")[0]) <= 180]
COMPLETE_INVENTORY = [f"{d}d {m}" for d in (30, 60, 90) for m in ("CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar")]
ARMS.update({"Rank existing": EXISTING, "Rank existing + K": EXISTING + K_MAIN, "Activity existing": EXISTING, "Activity existing + K": EXISTING + K_MAIN, "Compact controls existing": EXISTING, "Compact controls existing + K": EXISTING + K_MAIN})
ARMS["Existing complete-case"] = COMPLETE_INVENTORY
ARMS["Existing + K complete-case"] = COMPLETE_INVENTORY + [f"{d}d K-ratio" for d in (30, 60, 90)]
BASELINES = ("Constant", "Zero return", "Persistence")


def target_column(target):
    """CAGR forecasts are fitted in horizon log-return units."""
    return "log_return" if target == "CAGR" else target


def training_weights(origins):
    """Give each date unit total weight, keeping ridge regularisation fixed."""
    counts = pd.Series(origins).value_counts()
    return pd.Series(origins).map(1 / counts).to_numpy()


def transform_scale(values):
    """Use only finite non-zero training observations to set an asinh scale."""
    values = np.asarray(values, dtype=float)
    good = values[np.isfinite(values) & (values != 0)]
    return float(np.median(np.abs(good))) if len(good) else np.nan


class FoldAdapter:
    """Fit causal robust transforms and explicit extrapolation bounds.

    :param legacy: Zero-fill with indicators and the earlier ratio floors.
    :param ranked: Within-origin performance percentiles computed before label joins.
    :param persistence_target: Metric schema for the matched persistence input.
    """

    def __init__(self, columns, legacy=False, ranked=False, persistence_target=None):
        self.columns = list(columns)
        self.legacy = legacy
        self.ranked = ranked
        self.persistence_target = persistence_target

    def _raw(self, frame):
        arr = frame[self.columns].to_numpy(dtype=float).copy()
        for i, name in enumerate(self.columns):
            if name.endswith(" CAGR") and not name.startswith("missing "):
                exact = name.replace(" CAGR", " log_return")
                if exact in frame:
                    arr[:, i] = frame[exact].to_numpy(dtype=float)
                else:
                    days = int(name.split("d ")[0])
                    with np.errstate(divide="ignore", invalid="ignore"):
                        arr[:, i] = np.log1p(arr[:, i]) * days / 365
            if self.legacy and name.endswith((" Sharpe", " Sortino")) and not name.startswith("missing "):
                floor = name + " floor"
                if floor in frame:
                    arr[:, i] = frame[floor].to_numpy(dtype=float)
            if self.ranked and "rank " + name in frame and not name.startswith("missing "):
                arr[:, i] = frame["rank " + name].to_numpy(dtype=float)
        arr[~np.isfinite(arr)] = np.nan
        return arr

    def fit(self, frame, weights):
        arr = self._raw(frame)
        self.continuous = np.array([not c.startswith("missing ") for c in self.columns])
        self.scales = np.ones(arr.shape[1])
        for i in np.flatnonzero(self.continuous):
            scale = transform_scale(arr[:, i])
            self.scales[i] = scale if np.isfinite(scale) and scale > 0 else 1.0
            arr[:, i] = np.arcsinh(arr[:, i] / self.scales[i])
        self.active = np.isfinite(arr).any(axis=0)
        self.medians = np.zeros(arr.shape[1])
        self.low = np.zeros(arr.shape[1])
        self.high = np.zeros(arr.shape[1])
        for i in np.flatnonzero(self.active):
            finite = arr[np.isfinite(arr[:, i]), i]
            self.medians[i] = 0.0 if self.legacy else np.median(finite)
            self.low[i] = finite.min()
            self.high[i] = finite.max()
        arr = np.where(np.isfinite(arr), arr, self.medians)
        self.means = np.average(arr, axis=0, weights=weights)
        self.std = np.sqrt(np.average((arr - self.means) ** 2, axis=0, weights=weights))
        self.active &= self.std > 1e-12
        self.std = np.where(self.std > 1e-12, self.std, 1.0)
        self.low = np.maximum((self.low - self.means) / self.std, -5.0)
        self.high = np.minimum((self.high - self.means) / self.std, 5.0)
        return self

    def transform(self, frame):
        arr = self._raw(frame)
        for i in np.flatnonzero(self.continuous):
            arr[:, i] = np.arcsinh(arr[:, i] / self.scales[i])
        arr = np.where(np.isfinite(arr), arr, self.medians)
        z = (arr - self.means) / self.std
        clipped = np.clip(z, self.low, self.high)
        self.last_clipped_fraction = float(np.mean(np.abs(z[:, self.active] - clipped[:, self.active]) > 1e-12)) if self.active.any() else 0.0
        return clipped[:, self.active]


def robust_sharpe_fit(x, y, weights, x_test):
    """Fit a fixed pseudo-Huber objective with an unpenalised intercept.

    The target scale is learned solely from the training fold. The regulariser
    matches ridge alpha 10; each origin has unit total fitting weight.
    """
    scale = transform_scale(y)
    scale = scale if np.isfinite(scale) and scale > 0 else 1.0
    yy = y / scale
    xx = np.column_stack([np.ones(len(x)), x])
    delta = 1.35

    def objective(beta):
        residual = xx @ beta - yy
        root = np.sqrt(1 + (residual / delta) ** 2)
        loss = np.sum(weights * delta**2 * (root - 1)) + 0.5 * 10 * np.dot(beta[1:], beta[1:])
        gradient = xx.T @ (weights * residual / root)
        gradient[1:] += 10 * beta[1:]
        return loss, gradient

    initial = np.zeros(xx.shape[1])
    initial[0] = np.median(yy)
    result = minimize(objective, initial, jac=True, method="L-BFGS-B", options={"maxiter": 1000, "ftol": 1e-10, "gtol": 1e-6})
    if not result.success:
        raise RuntimeError("Pseudo-Huber fitting did not converge: " + result.message)
    return (result.x[0] + x_test @ result.x[1:]) * scale, int(result.nit)


def prepare_frame(data, horizon, delay=0, phase=0, source=False):
    """Join only operationally unfiltered historical feature/label rows."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(phase) & f.anchor_supported].copy()
    if source:
        alternate = data["source_features"].set_index(["origin_at", "pair_id"])
        key = pd.MultiIndex.from_frame(f[["origin_at", "pair_id"]])
        for col in EXISTING:
            f[col] = alternate.loc[key, col].to_numpy()
            if col.endswith(" CAGR"):
                with np.errstate(divide="ignore", invalid="ignore"):
                    f[col.replace(" CAGR", " log_return")] = np.log1p(f[col]) * int(col.split("d ")[0]) / 365
    ranks = f.groupby("origin_at")[EXISTING + K_ALL].rank(method="average", pct=True) - 0.5
    ranks.columns = ["rank " + c for c in ranks.columns]
    f = pd.concat([f, ranks], axis=1)
    f["supported_inputs"] = np.isfinite(f[SUPPORTED_INVENTORY]).sum(axis=1)
    f["supported_input_count"] = len(SUPPORTED_INVENTORY)
    f["log_age"] = np.log1p(np.maximum(f.age_days, 0))
    availability = pd.DataFrame((~np.isfinite(f[EXISTING + K_ALL])).to_numpy(dtype=float), index=f.index, columns=["missing " + name for name in EXISTING + K_ALL])
    f = pd.concat([f, availability], axis=1).copy()
    labels = data["labels"]
    labels = labels[(labels.horizon == horizon) & (labels.delay == delay)]
    f = f.merge(labels, on=["origin_at", "pair_id"], suffixes=("", " target"), validate="one_to_one")
    return f


def target_persistence(frame, horizon, target, data):
    """Compute the matched past target before the origin, including seven days."""
    if horizon in (7, 30, 90):
        if target == "CAGR":
            if "_daily_nav_index" not in data:
                data["_daily_nav_index"] = data["daily"].set_index(["date", "pair_id"]).share_price
            nav = data["_daily_nav_index"]
            anchor = frame.origin_at - pd.Timedelta(days=1)
            past = pd.MultiIndex.from_arrays([anchor - pd.Timedelta(days=horizon), frame.pair_id])
            current = pd.MultiIndex.from_arrays([anchor, frame.pair_id])
            return np.log(nav.reindex(current).to_numpy()) - np.log(nav.reindex(past).to_numpy())
        return frame[f"{horizon}d {target}"].to_numpy(dtype=float)
    raise ValueError(horizon)


def residual_k(train, test, weights):
    """Condition transformed 30-day K on 30-day Sharpe using training only."""
    train = train.copy()
    test = test.copy()
    train["residual_K_30"] = np.nan
    test["residual_K_30"] = np.nan
    scale = transform_scale(train["30d K-ratio"])
    mask = np.isfinite(train["30d K-ratio"]) & np.isfinite(train["30d Sharpe"])
    target_mask = np.isfinite(test["30d K-ratio"]) & np.isfinite(test["30d Sharpe"])
    if mask.sum() >= 20 and np.isfinite(scale) and scale > 0:
        model = Ridge(alpha=10)
        ss = transform_scale(train.loc[mask, "30d Sharpe"])
        ss = ss if np.isfinite(ss) and ss > 0 else 1.0
        x = np.column_stack([np.arcsinh(train.loc[mask, "30d Sharpe"] / ss), np.ones(mask.sum())])
        y = np.arcsinh(train.loc[mask, "30d K-ratio"] / scale)
        model.fit(x[:, :1], y, sample_weight=weights[mask])
        train.loc[mask, "residual_K_30"] = y - model.predict(x[:, :1])
        xx = np.arcsinh(test.loc[target_mask, ["30d Sharpe"]].to_numpy() / ss)
        xx = np.clip(xx, x[:, 0].min(), x[:, 0].max())
        test.loc[target_mask, "residual_K_30"] = np.arcsinh(test.loc[target_mask, "30d K-ratio"] / scale) - model.predict(xx)
    return train, test


def run_horizon(data, horizon, target, phase=0, delay=0, source=False, small=False):
    """Refit monthly using only target-specific labels matured before fitting."""
    frame = prepare_frame(data, horizon, delay, phase, source)
    target_col = target_column(target)
    predictions = []
    supports = []
    fold_details = []
    arms = {name: cols for name, cols in ARMS.items() if not small or name in ("Existing", "Existing + K", "Quality/age")}
    mask_columns = ["missing " + col for col in EXISTING + K_ALL]
    for refit in pd.date_range(START, END - pd.Timedelta(days=1), freq="MS"):
        test = frame[(frame.origin_at >= refit) & (frame.origin_at < refit + pd.offsets.MonthBegin(1))].copy()
        train = frame[(frame.label_available_at < refit) & np.isfinite(frame[target_col])].copy()
        if test.empty:
            continue
        origins = train.origin_at.nunique()
        vaults = train.pair_id.nunique()
        block_count = 0 if train.empty else int((train.origin_at.max() - train.origin_at.min()).days // horizon)
        supported = origins >= 20 and vaults >= 10 and block_count >= 3
        illustrative = origins >= 5 and vaults >= 10
        supports.append({"horizon": horizon, "target": target, "refit_at": refit, "training_origins": origins, "training_vaults": vaults, "training_calendar_blocks": block_count, "supported": supported, "evaluation_origins": test.origin_at.nunique(), "phase": phase, "delay": delay, "source": source, "latest_training_label_at": train.label_available_at.max() if len(train) else pd.NaT})
        if not illustrative:
            continue
        assert train.label_available_at.max() < refit
        weights = training_weights(train.origin_at)
        train["past_target"] = target_persistence(train, horizon, target, data)
        test["past_target"] = target_persistence(test, horizon, target, data)
        train["missing past_target"] = ~np.isfinite(train.past_target)
        test["missing past_target"] = ~np.isfinite(test.past_target)
        train, test = residual_k(train, test, weights)
        y_raw = train[target_col].to_numpy(dtype=float)
        scale = transform_scale(y_raw) if target == "K-ratio" else 1.0
        if not np.isfinite(scale) or scale <= 0:
            continue
        y = np.arcsinh(y_raw / scale) if target == "K-ratio" else y_raw
        constant = float(np.average(y, weights=weights))
        metadata = ["origin_at", "pair_id", "vault_name", "origin_quarter", "age_days", "observed_inputs", "available_windows", "observed_fraction_90", "freshness_hours", "status", "daily_marks", "supported_inputs", "supported_input_count", "nonzero_returns", "longest_recent_flat_run", "flat_fraction_30"]

        def add(name, pred, eligible=None, active_columns=None, bounds=None, arm_supported=None, input_clipping=0.0, iterations=0):
            eligible = np.ones(len(test), bool) if eligible is None else eligible
            if not eligible.any():
                return
            raw_pred = np.asarray(pred, dtype=float).copy()
            clipped = np.zeros(len(raw_pred), bool)
            ranking = name.startswith("Rank ")
            if bounds is not None and not ranking:
                clipped = (raw_pred < bounds[0]) | (raw_pred > bounds[1])
                raw_pred = np.clip(raw_pred, *bounds)
            if target == "K-ratio" and not ranking:
                with np.errstate(over="ignore"):
                    raw_pred = np.sinh(raw_pred) * scale
            raw_pred[~np.isfinite(raw_pred)] = np.nan
            selected = eligible & np.isfinite(raw_pred)
            out = test.loc[selected, metadata].copy()
            out["prediction"] = raw_pred[selected]
            out["actual"] = test.loc[selected, target_col].to_numpy(dtype=float)
            if name.startswith("Activity ") and target in ("Sharpe", "K-ratio"):
                #: Outcome activity defines sensitivity-label validity, never entry eligibility.
                quality = test.loc[selected, "nonzero_returns"].ge(max(4, int(np.ceil(horizon / 2)))).to_numpy()
                out.loc[~quality, "actual"] = np.nan
            out["target_scale"] = scale
            out["horizon"] = horizon
            out["target"] = target
            out["arm"] = name
            out["refit_at"] = refit
            out["supported"] = supported if arm_supported is None else arm_supported
            out["prediction_space"] = "rank score" if ranking else "level"
            out["output_clipped"] = clipped[selected]
            out["input_clipped_fraction"] = input_clipping
            out["phase"] = phase
            out["delay"] = delay
            out["source"] = source
            predictions.append(out)
            if active_columns is not None:
                fold_details.append({"target": target, "horizon": horizon, "arm": name, "refit_at": str(refit), "phase": phase, "source": source, "delay": delay, "active_columns": active_columns, "output_bounds": list(bounds) if bounds is not None else None, "input_clipped_fraction": input_clipping, "fit_iterations": iterations})

        add("Constant", np.repeat(constant, len(test)))
        if target == "CAGR":
            add("Zero return", np.zeros(len(test)))
        past = test.past_target.to_numpy(dtype=float)
        if target == "K-ratio":
            past = np.arcsinh(past / scale)
        add("Persistence", past)
        for name, perf_columns in arms.items():
            perf_columns = list(perf_columns)
            persistence = name.startswith("Persistence +")
            if persistence:
                perf_columns += ["past_target"]
            compact_controls = name.startswith("Compact controls")
            columns = list(dict.fromkeys(perf_columns + CONTROLS + ([] if compact_controls else mask_columns) + (["missing past_target"] if persistence else [])))
            legacy = "missing=False" in name
            complete_case = "complete-case" in name
            activity = name.startswith("Activity ")
            ranking = name.startswith("Rank ")
            local_train = train.copy() if activity else train
            local_test = test.copy() if activity else test
            if activity:
                for col in EXISTING + K_ALL:
                    if col.endswith((" Sharpe", " Sortino", " K-ratio")):
                        days = None if col == K_MAX else int(col.split("d ")[0])
                        valid = "max nonzero_returns" if col == K_MAX else f"{days}d nonzero_returns"
                        for piece in (local_train, local_test):
                            required = np.maximum(4, np.ceil(piece["max days"] / 2)) if col == K_MAX else max(4, int(np.ceil(days / 2)))
                            piece.loc[piece[valid] < required, col] = np.nan
                            if "missing " + col in piece:
                                piece["missing " + col] = ~np.isfinite(piece[col])
            complete = np.ones(len(train), bool)
            if complete_case:
                complete &= np.isfinite(local_train[perf_columns]).all(axis=1)
            if activity and target in ("Sharpe", "K-ratio"):
                complete &= local_train.nonzero_returns.ge(max(4, int(np.ceil(horizon / 2)))).to_numpy()
            fit = local_train.loc[complete]
            if fit.origin_at.nunique() < 5 or fit.pair_id.nunique() < 10:
                continue
            fit_weights = training_weights(fit.origin_at)
            fit_y = y[complete]
            if ranking:
                fit_y = fit.groupby("origin_at")[target_col].rank(method="average", pct=True).to_numpy() - 0.5
            adapter = FoldAdapter(columns, legacy, ranking, target).fit(fit, fit_weights)
            active_perf = [col for col, active in zip(columns, adapter.active) if active and col in perf_columns]
            eligible = np.ones(len(test), bool) if name == "Quality/age" else np.isfinite(local_test[active_perf]).any(axis=1).to_numpy() if active_perf else np.zeros(len(test), bool)
            if complete_case:
                eligible &= np.isfinite(local_test[perf_columns]).all(axis=1).to_numpy()
            x = adapter.transform(fit)
            if not x.shape[1] or not eligible.any():
                continue
            x_test = adapter.transform(local_test)
            clipping = adapter.last_clipped_fraction
            iterations = 0
            with threadpool_limits(limits=1):
                if target == "Sharpe" and not ranking:
                    pred, iterations = robust_sharpe_fit(x, fit_y, fit_weights, x_test)
                else:
                    model = Ridge(alpha=10, solver="cholesky")
                    model.fit(x, fit_y, sample_weight=fit_weights)
                    pred = model.predict(x_test)
            bounds = tuple(np.quantile(fit_y, [0.005, 0.995])) if not ranking else None
            fit_blocks = int((fit.origin_at.max() - fit.origin_at.min()).days // horizon)
            arm_supported = fit.origin_at.nunique() >= 20 and fit.pair_id.nunique() >= 10 and fit_blocks >= 3
            add(name, pred, eligible, [c for c, a in zip(columns, adapter.active) if a], bounds, arm_supported, clipping, iterations)
    return (pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame(), pd.DataFrame(supports), fold_details)


def run_models(data):
    """Run fixed arms, all cadence phases and labelled input/delay sensitivities."""
    fingerprint = sha256(__file__) + data["manifest"]["module_sha256"]
    cache = ARTIFACT_DIR / "models-manifest.json"
    if cache.exists() and json.loads(cache.read_text()).get("fingerprint") == fingerprint:
        return {"predictions": pd.read_parquet(ARTIFACT_DIR / "predictions.parquet"), "support": pd.read_parquet(ARTIFACT_DIR / "model-support.parquet"), "folds": json.loads((ARTIFACT_DIR / "model-folds.json").read_text())}
    jobs = [(h, t, phase, delay, source) for h in HORIZONS for t in TARGETS for phase, delay, source in [(0, 0, False), (1, 0, False), (2, 0, False), (3, 0, False), (0, 1, False), (0, 0, True)]]
    predictions = []
    supports = []
    folds = []
    for h, target, phase, delay, source in tqdm(jobs, desc="09 fixed monthly forecasts; estimated 3–6 minutes", mininterval=15):
        p, s, f = run_horizon(data, h, target, phase, delay, source, small=phase != 0 or delay != 0 or source)
        if not p.empty:
            predictions.append(p)
        supports.append(s)
        folds.extend(f)
    result = {"predictions": pd.concat(predictions, ignore_index=True), "support": pd.concat(supports, ignore_index=True), "folds": folds}
    result["predictions"].to_parquet(ARTIFACT_DIR / "predictions.parquet", index=False)
    result["support"].to_parquet(ARTIFACT_DIR / "model-support.parquet", index=False)
    (ARTIFACT_DIR / "model-folds.json").write_text(json.dumps(folds, indent=2))
    cache.write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "ridge_alpha": 10,
                "weights": "sum=distinct training dates",
                "primary_forecast_days": 4,
                "target_maturity": "strictly earlier than monthly refit",
                "illustrative_minimum": "5 origins / 10 vaults; excluded from supported comparisons",
                "primary_models": "CAGR log return/K asinh ridge; raw Sharpe scaled pseudo-Huber; no tuning",
                "input_policy": "continuous median-absolute asinh; CAGR exact lookback log return; training-only range and +/-5z bounds",
                "output_policy": "training 0.5%-99.5% target bounds before K inverse; baselines unbounded",
                "ranking_companion": "causal within-date input percentiles and matured target ranks; IC only",
                "activity_rule": "ratio feature/label nonzero count >=max(4,ceil(days/2)); exploratory only",
                "complete_case_inventory": COMPLETE_INVENTORY,
                "primary_k_inputs": K_MAIN,
                "long_k_ablation": "Original four K inputs versus +360d, +max, and both; shared availability controls",
                "amendment": "09-k-ratio-feature-forecast-amendment.md",
            },
            indent=2,
        )
    )
    return result
