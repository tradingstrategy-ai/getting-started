"""Chronological sign/magnitude forecasts and exact empirical liquidation values."""

import hashlib
import json
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from threadpoolctl import threadpool_limits
from tqdm_loggable.auto import tqdm
from marginal_profit_data import PERFORMANCE, SUPPORT, REGISTRY

MODELS = ("P", "D", "M", "C")


def date_weights(frame):
    return 1 / frame.groupby("Date").Date.transform("size").to_numpy(float)


class Head:
    """Training-only asinh transformation, masks and regularised predictions."""

    def __init__(self, columns, alpha=1.0, classification=False):
        self.columns = list(columns)
        self.alpha = alpha
        self.classification = classification

    def features(self, frame, fit=False):
        x = frame[self.columns].to_numpy(float)
        mask = ~np.isfinite(x)
        if fit:
            self.medians = np.array([np.median(v[np.isfinite(v)]) if np.isfinite(v).any() else 0.0 for v in x.T])
            self.scales = np.array([np.median(np.abs(v[np.isfinite(v)])) if np.isfinite(v).any() else 1.0 for v in x.T])
            self.scales = np.maximum(self.scales, 1e-8)
        x = np.where(mask, self.medians, x)
        x = np.arcsinh(x / self.scales)
        if fit:
            self.means = x.mean(axis=0)
            self.std = np.maximum(x.std(axis=0), 1e-8)
        return np.c_[(x - self.means) / self.std, mask.astype(float)]

    def fit(self, frame, y):
        X = self.features(frame, True)
        weights = frame["Date_weight"].to_numpy(float).copy() if "Date_weight" in frame else date_weights(frame)
        weights *= len(weights) / weights.sum()
        # Sum-weight normalisation and the n-scaled penalty implement mean loss plus L2.
        self.constant = float(np.average(y, weights=weights))
        self.model = None
        if self.classification and len(np.unique(y)) > 1:
            self.model = LogisticRegression(C=1 / (self.alpha * len(y)), max_iter=500, solver="lbfgs", tol=1e-7).fit(X, y, sample_weight=weights)
        elif not self.classification and len(y) > 1:
            self.model = Ridge(alpha=self.alpha * len(y), solver="cholesky").fit(X, y, sample_weight=weights)
        return self

    def predict(self, frame):
        if self.model is None:
            return np.full(len(frame), self.constant)
        X = self.features(frame)
        return self.model.predict_proba(X)[:, 1] if self.classification else self.model.predict(X)


def weighted_shape(y, weights):
    """Keep the full empirical tail and normalise its weighted mean to one."""
    order = np.argsort(y, kind="stable")
    y = np.asarray(y, float)[order]
    w = np.asarray(weights, float)[order]
    w /= w.sum()
    mean = float(np.dot(y, w))
    if mean <= 0:
        return np.array([0.0]), np.array([1.0])
    return y / mean, w


@dataclass
class Shape:
    z: np.ndarray
    w: np.ndarray

    def __post_init__(self):
        self.cw = np.r_[0, np.cumsum(self.w)]
        self.cz = np.r_[0, np.cumsum(self.z * self.w)]
        self.cw[-1] = 1.0

    def below(self, k):
        j = np.searchsorted(self.z, k, side="left")
        return self.cw[j], self.cz[j]

    def call(self, scale, strike):
        if scale <= 0:
            return max(-strike, 0.0)
        w, z = self.below(strike / scale)
        return max(0.0, scale * (self.cz[-1] - z) - strike * (1 - w))


@dataclass
class Distribution:
    """Same-sign scale mixture with physical negative-return bounds."""

    p: float
    g: float
    ell: float
    positive: Shape
    negative: Shape

    def __post_init__(self):
        self.p = float(np.clip(self.p, 0, 1))
        self.g = max(0, float(self.g))
        self.ell = float(np.clip(self.ell, 0, 1))
        w, z = self.negative.below(1 / self.ell) if self.ell > 0 else (1.0, self.negative.cz[-1])
        self.loss = self.ell * z + 1 - w
        self.mu = (1 - self.p) * self.g * self.positive.cz[-1] - self.p * self.loss
        self.downside = self.p * self.loss

    def call(self, strike):
        pos = self.positive.call(self.g, strike)
        if strike >= 0:
            neg = 0.0
        elif strike <= -1:
            neg = -self.loss - strike
        elif self.ell <= 0:
            neg = -strike
        else:
            w, z = self.negative.below(-strike / self.ell)
            neg = -self.ell * z - strike * w
        return (1 - self.p) * pos + self.p * max(0.0, neg)

    def terminal(self, gross, basis, performance=0.10, capital=0.001, shift=0.0):
        if gross <= 0:
            return 0.0
        floor_correction = self.call(-1 - shift) - self.mu - 1 - shift
        return (1 - capital) * gross * (1 + self.mu + shift + max(0.0, floor_correction)) - performance * gross * self.call(basis / gross - 1 - shift)

    def profit_probability(self):
        if self.g <= 0:
            return 0.0
        w, _ = self.positive.below(0.001 / 0.899 / self.g)
        return (1 - self.p) * (1 - w)

    def serial(self):
        return dict(p=self.p, g=self.g, ell=self.ell, mu=self.mu, downside=self.downside, net=self.terminal(1.0, 1.0) - 1, profit_probability=self.profit_probability(), loss_bound_adjustment=self.ell - self.loss)


def support(frame, h, blocks=6):
    if not len(frame):
        return False
    b = (frame.Date - pd.Timestamp("2023-03-01")).dt.days // h
    return bool(b.nunique() >= blocks and frame.Pair.nunique() >= 30 and b[frame.Y.lt(0)].nunique() >= 3 and b[frame.Y.ge(0)].nunique() >= 3)


def fit_snapshot(train, h, alpha, supported):
    train = train.copy()
    train["Date_weight"] = date_weights(train)
    y = train.Y.to_numpy(float)
    weights = train["Date_weight"].to_numpy(float)
    neg = y < 0
    pos = ~neg
    positive = Shape(*weighted_shape(y[pos], weights[pos]))
    negative = Shape(*weighted_shape(-y[neg], weights[neg]))
    snapshot = dict(positive=positive, negative=negative, heads={}, supported=supported, train_rows=len(train), train_vaults=train.Pair.nunique(), max_mature=train.Mature_at.max(), max_origin=train.Date.max(), alpha=alpha)
    p = float(np.average(neg, weights=weights))
    g = float(np.average(y[pos], weights=weights[pos]))
    ell = float(np.average(-y[neg], weights=weights[neg]))
    snapshot["constants"] = dict(p=p, g=g, ell=ell)
    if supported:
        with threadpool_limits(limits=1):
            for name, cols, target, part, classification in [("p_P", SUPPORT, neg, train, True), ("p_D", SUPPORT + PERFORMANCE, neg, train, True), ("p_C", SUPPORT + ("c00_score",), neg, train, True), ("g_P", SUPPORT, y[pos], train[pos], False), ("ell_P", SUPPORT, -y[neg], train[neg], False), ("g_M", SUPPORT + PERFORMANCE, y[pos], train[pos], False), ("ell_M", SUPPORT + PERFORMANCE, -y[neg], train[neg], False)]:
                snapshot["heads"][name] = Head(cols, alpha, classification).fit(part, target)
    return snapshot


def predict_snapshot(snapshot, frame, model, with_flags=False):
    if not len(frame):
        return np.empty((0, 3))
    if not snapshot["supported"]:
        values = np.tile([snapshot["constants"][k] for k in ("p", "g", "ell")], (len(frame), 1))
        return (values, np.zeros(len(frame), bool)) if with_flags else values
    heads = snapshot["heads"]
    p = heads["p_" + ("D" if model == "M" else model)].predict(frame)
    g = heads["g_" + ("M" if model == "M" else "P")].predict(frame)
    ell = heads["ell_" + ("M" if model == "M" else "P")].predict(frame)
    ghead = heads["g_" + ("M" if model == "M" else "P")]
    lhead = heads["ell_" + ("M" if model == "M" else "P")]
    fallback = (g < 0) | (ell <= 0)
    g = np.where(g < 0, ghead.constant, g)
    ell = np.where(ell <= 0, lhead.constant, ell)
    values = np.c_[p, np.maximum(g, 0), np.clip(ell, 0, 1)]
    return (values, fallback) if with_flags else values


def select_penalty(train, h):
    """Choose once per calendar year from prior folds, then refit monthly."""
    dates = sorted(train.Date.unique())
    cut = pd.Timestamp(dates[-1]) - pd.Timedelta(days=3 * h)
    folds = []
    for k in range(3):
        start = cut + pd.Timedelta(days=k * h)
        end = start + pd.Timedelta(days=h)
        a = train[train.Mature_at.lt(start)]
        b = train[train.Date.ge(start) & train.Date.lt(end)]
        if not support(a, h) or not len(b):
            return 1.0, "unsupported prior folds"
        folds.append((a, b))
    losses = []
    for alpha in REGISTRY["penalties"]:
        score = 0.0
        for a, b in folds:
            with threadpool_limits(limits=1):
                head = Head(SUPPORT + PERFORMANCE, alpha, True).fit(a, a.Y.lt(0).to_numpy())
            p = np.clip(head.predict(b), 1e-10, 1 - 1e-10)
            y = b.Y.lt(0).to_numpy()
            w = date_weights(b)
            score += float(np.average(-(y * np.log(p) + (1 - y) * np.log1p(-p)), weights=w))
        losses.append((score, alpha))
    return min(losses)[1], "three purged probability folds; same penalty shared by heads"


def build_forecasts(data):
    """Monthly causal fits with model-specific forecasts at every archived origin."""
    import joblib
    from pathlib import Path
    from k_ratio_features import sha256

    cachekey = hashlib.sha256((sha256(Path(__file__)) + str(data["feature_artifact"])).encode()).hexdigest()
    folder = data["feature_artifact"] / cachekey
    folder.mkdir(exist_ok=True)
    data["forecast_artifact"] = folder
    path = folder / "forecasts.parquet"
    sp = folder / "forecast-snapshots.joblib"
    if path.exists() and sp.exists():
        data["predictions"] = pd.read_parquet(path)
        data["snapshots"] = joblib.load(sp)
        data["training_audit"] = pd.read_csv(folder / "training-audit.csv")
        return data["predictions"]
    panel = data["panel"]
    all_parts = []
    snapshots = {}
    audit = []
    penalties = {}
    jobs = [(h, month) for h in (2, 7, 30) for month in sorted(panel.Date.dt.to_period("M").unique())]
    for h, month in tqdm(jobs, desc="NB21 causal monthly forecasts", mininterval=15):
        fit = month.start_time
        current = panel[panel.H.eq(h) & panel.Date.dt.to_period("M").eq(month)].copy()
        if not len(current):
            continue
        train = panel[panel.Training_origin & panel.H.eq(h) & panel.operational_pool & panel.Resolved & panel.Mature_at.lt(fit)].copy()
        minimal = len(train) and ((train.Date - pd.Timestamp("2023-03-01")).dt.days // h).nunique() >= 1 and train.Y.lt(0).any() and train.Y.ge(0).any()
        supported = support(train, h) if minimal else False
        annual = (h, fit.year)
        if minimal and supported and annual not in penalties:
            penalties[annual] = select_penalty(train, h)
        alpha, reason = penalties.get(annual, (1.0, "pooled/unsupported fit"))
        snap = fit_snapshot(train, h, alpha, supported) if minimal else None
        snapshots[(h, fit)] = snap
        audit.append(dict(H=h, Fit=fit, Rows=len(train), Vaults=train.Pair.nunique(), Supported=supported, Prior_available=bool(minimal), Alpha=alpha, Penalty_reason=reason, Train_max_mature=train.Mature_at.max(), Train_max_origin=train.Date.max()))
        if snap:
            assert snap["max_mature"] < fit
        for model in MODELS:
            f = current[["Date", "Pair", "Vault", "H", "Y", "Y_mark", "Resolved", "Mature_at", "Endpoint_age", "operational_pool", "can_deposit", "recorded_age", "quote_age", "permission_unknown", "c00_score"]].copy()
            f["Model"] = model
            f["Fit"] = fit
            f["Supported"] = supported
            f["Prior_available"] = bool(minimal)
            if snap:
                triples, fallback = predict_snapshot(snap, current, model, with_flags=True)
                f["Magnitude_fallback"] = fallback
                distributions = [Distribution(*v, snap["positive"], snap["negative"]) for v in triples]
                stats = pd.DataFrame([d.serial() for d in distributions], index=f.index)
                for c in stats:
                    f[c] = stats[c]
            else:
                f["Magnitude_fallback"] = False
                for c in ("p", "g", "ell", "mu", "downside", "net", "profit_probability", "loss_bound_adjustment"):
                    f[c] = np.nan
            all_parts.append(f)
        print(f"Forecast {h}d / {month}: {len(train):,} matured labels; approximately {max(1,(len(jobs)-len(audit))*.06):.0f} minutes remaining", flush=True)
    out = pd.concat(all_parts, ignore_index=True)
    out.to_parquet(path, index=False)
    joblib.dump(snapshots, sp)
    audit = pd.DataFrame(audit)
    audit.to_csv(folder / "training-audit.csv", index=False)
    data.update(predictions=out, snapshots=snapshots, training_audit=audit)
    # Same-year penalty selection is an explicitly registered computational limit.
    (folder / "forecast-registration.json").write_text(json.dumps(dict(penalty_schedule="Once per horizon/year at first supported fit, frozen for that year; monthly refits", penalties={str(k): v for k, v in penalties.items()}, mean_heads="Ridge mean fits on original magnitude scale; probability proper log-loss; one shared penalty", shape="Full date-weighted empirical components; no tail quantile truncation"), indent=2))
    data["forecast_lookup"] = {}
    return out


def distribution_at(data, t, pid, h, model):
    key = (pd.Timestamp(t), h, model)
    cache = data.setdefault("forecast_lookup", {})
    if key not in cache:
        indexed = data.get("forecast_index")
        if indexed is None:
            indexed = data["predictions"].set_index(["Date", "H", "Model", "Pair"]).sort_index()
            data["forecast_index"] = indexed
        try:
            cache[key] = indexed.loc[(key[0], h, model)]
        except KeyError:
            cache[key] = pd.DataFrame()
    f = cache[key]
    if pid not in f.index:
        return None, None
    row = f.loc[pid]
    if not row.Prior_available:
        return None, row
    snap = data["snapshots"][(h, pd.Timestamp(row.Fit))]
    return Distribution(row.p, row.g, row.ell, snap["positive"], snap["negative"]), row
