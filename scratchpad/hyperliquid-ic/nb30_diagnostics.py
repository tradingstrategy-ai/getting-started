"""Observed-price measurements and descriptive ranking checks for NB30."""

import numpy as np
import pandas as pd

SPECS = [(7, 30), (14, 30), (7, 60), (14, 60)]
HORIZONS = (30, 60)
DAY = np.timedelta64(1, "D")


def last_mark_per_day(group):
    g = group.sort_values("timestamp", kind="stable").copy()
    g["day"] = g.timestamp.dt.normalize()
    return g.drop_duplicates("day", keep="last").set_index("timestamp").sort_index()


def rolling_row(marks, decision, h, w):
    days = marks.index.to_numpy(dtype="datetime64[ns]")
    prices = marks.share_price.to_numpy(float)
    t = np.datetime64(pd.Timestamp(decision), "ns")
    j = np.searchsorted(days, t, side="left") - 1
    names = ["median_log_rate", "lower_quartile_log_rate", "positive_window_share", "largest_event_containment_share", "largest_event_overlap_only_share", "ordinary_growth_annualised", "volatility", "sharpe_like", "mean_drawdown", "current_drawdown", "history_span_days", "actual_span_min", "actual_span_median", "actual_span_max", "median_nominal_simple_return", "median_mark_gap_days"]
    out = dict.fromkeys(names, np.nan)
    out.update(unique_event_count=0, path_marks=0, exact_median_equals_q25=False, last_observation_ts=pd.NaT, last_mark_age_days=np.nan)
    if j < 0 or (t - days[j]) / DAY > 7:
        return out
    out.update(last_observation_ts=pd.Timestamp(days[j]), last_mark_age_days=float((t - days[j]) / DAY))
    lo = t - np.timedelta64(w, "D")
    ends = np.arange(np.searchsorted(days, lo, side="right"), j + 1)
    requested = days[ends] - np.timedelta64(h, "D")
    starts = np.searchsorted(days, requested, side="right") - 1
    ok = (starts >= 0) & ((requested - days[np.maximum(starts, 0)]) / DAY <= 7)
    starts, ends = starts[ok], ends[ok]
    spans = ((days[ends] - days[starts]) / DAY).astype(float)
    rates = np.log(prices[ends] / prices[starts]) / spans
    if len(rates):
        m, q = np.median(rates), np.quantile(rates, 0.25)
        out.update(median_log_rate=float(m), lower_quartile_log_rate=float(q), positive_window_share=float(np.mean(rates > 0)), unique_event_count=len(rates), exact_median_equals_q25=bool(m == q), actual_span_min=float(spans.min()), actual_span_median=float(np.median(spans)), actual_span_max=float(spans.max()), median_nominal_simple_return=float(np.median(np.expm1(rates * spans))))
        # The event is an observed single-step gain, not an overlapping rolling return.
        event_ends = np.arange(starts.min() + 1, ends.max() + 1)
        gains = np.log(prices[event_ends] / prices[event_ends - 1])
        if gains.max() > 0:
            k = event_ends[np.argmax(gains)]
            contains = (starts <= k - 1) & (ends >= k)
            overlaps = (days[starts] < days[k]) & (days[ends] > days[k - 1])
            out["largest_event_containment_share"] = float(contains.mean())
            out["largest_event_overlap_only_share"] = float((overlaps & ~contains).mean())
    first = max(0, np.searchsorted(days, lo, side="right") - 1)
    # Use a boundary mark only within the same permitted carry window.
    if (lo - days[first]) / DAY > 7:
        first += 1
    pdays, pprices = days[first : j + 1], prices[first : j + 1]
    out["path_marks"] = len(pdays)
    if len(pdays) < 2:
        return out
    dt = ((pdays[1:] - pdays[:-1]) / DAY).astype(float)
    lr = np.diff(np.log(pprices))
    span = float(dt.sum())
    mu = lr.sum() / span
    vol = np.sqrt(365 * np.sum((lr - mu * dt) ** 2) / span) if len(lr) >= 2 else np.nan
    dd = 1 - pprices / np.maximum.accumulate(pprices)
    # Integrate carried drawdown through T, clipping the first segment to W.
    segment_starts = np.maximum(pdays, lo)
    segment_ends = np.r_[pdays[1:], t]
    durations = ((segment_ends - segment_starts) / DAY).astype(float)
    out.update(history_span_days=span, median_mark_gap_days=float(np.median(dt)), ordinary_growth_annualised=float(365 * mu), volatility=float(vol), sharpe_like=float(365 * mu / vol) if np.isfinite(vol) and vol > 1e-12 else np.nan, mean_drawdown=float(np.dot(dd, durations) / durations.sum()), current_drawdown=float(dd[-1]))
    return out


def forward_row(marks, decision, horizon):
    days = marks.index.to_numpy(dtype="datetime64[ns]")
    prices = marks.share_price.to_numpy(float)
    t = np.datetime64(pd.Timestamp(decision), "ns")
    end = t + np.timedelta64(horizon, "D")
    i = np.searchsorted(days, t, side="left") - 1
    j = np.searchsorted(days, end, side="right") - 1
    out = dict.fromkeys(["return", "drawdown", "actual_days", "volatility", "sharpe_like", "max_gap_days", "negative_return"], np.nan)
    out.update(entry_ts=pd.NaT, exit_ts=pd.NaT)
    if i < 0 or (t - days[i]) / DAY > 7:
        return out
    out["entry_ts"] = pd.Timestamp(days[i])
    if j <= i or days[j] <= t or (end - days[j]) / DAY > 7:
        return out
    # Clip at the horizon BEFORE daily aggregation: a later intraday observation
    # must not hide a valid midnight exit or otherwise change this label.
    calendar = days[i : j + 1].astype("datetime64[D]")
    indices = np.r_[i + np.flatnonzero(calendar[:-1] != calendar[1:]), j]
    indices = np.unique(np.r_[i, indices])
    p = prices[indices]
    dt = ((days[indices[1:]] - days[indices[:-1]]) / DAY).astype(float)
    total = float(dt.sum())
    ret = float(p[-1] / p[0] - 1)
    out["return"] = ret
    out.update(actual_days=total, exit_ts=pd.Timestamp(days[j]), negative_return=float(ret < 0), max_gap_days=float(dt.max()))
    # Endpoint return remains measurable with sparse history. Path outcomes need weekly coverage.
    if dt.max() <= 7:
        out["drawdown"] = float(np.min(p / np.maximum.accumulate(p) - 1))
        if len(dt) >= 2:
            lr = np.diff(np.log(p))
            mu = lr.sum() / total
            vol = float(np.sqrt(365 * np.sum((lr - mu * dt) ** 2) / total))
            out["volatility"] = vol
            out["sharpe_like"] = float(365 * mu / vol) if vol > 1e-12 else np.nan
    return out


def score_columns(h, w):
    s = f"{h}_{w}"
    return {k: (f"{c}_{s}", high) for k, c, high in [("M", "median_log_rate", True), ("Q25", "lower_quartile_log_rate", True), ("P", "positive_window_share", True), ("G", "ordinary_growth_annualised", True), ("S", "sharpe_like", True), ("-V", "volatility", False), ("-A", "mean_drawdown", False), ("-D", "current_drawdown", False)]}


def rank(values, higher=True):
    return values.rank(method="average", ascending=higher, pct=True)


def membership(values, higher=True):
    out = pd.Series(0.0, index=values.index)
    v = values.dropna()
    if not len(v):
        return out
    better = v.rank(method="min", ascending=not higher) - 1
    ties = v.groupby(v).transform("size")
    out.loc[v.index] = ((0.2 * len(v) - better) / ties).clip(0, 1)
    return out


def correlation(x, y, min_rows=5):
    good = x.notna() & y.notna()
    x, y = x[good], y[good]
    if len(x) < min_rows or x.nunique() < 2 or y.nunique() < 2:
        return np.nan
    return float(np.corrcoef(x.rank(), y.rank())[0, 1])


def group_outcome(y, weights):
    valid = y.notna()
    mass = weights.sum()
    observed = weights[valid].sum()
    return (float(np.dot(y[valid], weights[valid]) / observed) if observed > 0 else np.nan, float(observed / mass) if mass > 0 else np.nan)


def outcome_stats(y, ranks, weights):
    top, tc = group_outcome(y, weights)
    rest, rc = group_outcome(y, 1 - weights)
    # Group means in a comparison must refer to the same evaluated dates.
    if not (np.isfinite(top) and np.isfinite(rest)):
        top = rest = np.nan
    return {"rho": correlation(ranks, y), "top": top, "rest": rest, "spread": top - rest, "top_coverage": tc, "rest_coverage": rc, "labelled_rows": int(y.notna().sum())}


def marginal_stats(data, label, column, higher, horizon):
    rows, memberships = [], []
    for date, group in data.groupby("date"):
        g = group.loc[group[column].notna()]
        if not len(g):
            continue
        r, weights = rank(g[column], higher), membership(g[column], higher)
        for target in ["return", "drawdown", "negative_return", "volatility", "sharpe_like"]:
            rows.append(dict(score=label, horizon=horizon, date=date, target=target, feature_rows=len(g), **outcome_stats(g[f"forward_{target}_{horizon}"], r, weights)))
        memberships.append(g[["date", "address"]].assign(score=label, membership=weights))
    return pd.DataFrame(rows), pd.concat(memberships, ignore_index=True)


def residual_stats(data, label, setting, horizon):
    rows = []
    cols = score_columns(*setting)
    candidate, high = cols[label]
    for date, g in data.groupby("date"):
        ranks = pd.DataFrame({k: rank(g[c], hi) for k, (c, hi) in cols.items()})
        views = [(label, ["G", "P", "-V"], "G_P_V"), (label, ["S", "P"], "S_P")]
        views += [(metric, controls, name) for metric, name0 in [("-A", "mean_drawdown"), ("-D", "current_drawdown")] for controls, name in [(["G", "P", "-V"], name0 + "_base"), (["G", "P", "-V", label], name0 + "_plus_candidate")]]
        for metric, controls, view in views:
            f = ranks[[metric] + controls].dropna()
            if len(f) < 10:
                continue
            x = np.column_stack([np.ones(len(f)), f[controls]])
            if np.linalg.matrix_rank(x) < x.shape[1]:
                continue
            residual = pd.Series(f[metric].to_numpy() - x @ np.linalg.lstsq(x, f[metric], rcond=None)[0], index=f.index)
            if residual.std() < 1e-10:
                continue
            for target in ["return", "drawdown"]:
                y = g.loc[f.index, f"forward_{target}_{horizon}"]
                rows.append(dict(score=f"{label}_{setting[0]}_{setting[1]}", horizon=horizon, date=date, target=target, view=view, rho=correlation(residual, y, 10), rows=int(y.notna().sum())))
    return rows


def bootstrap(values, block_days=60, draws=200):
    values = values.sort_index()
    # Preserve actual calendar spacing, including unscored dates inside sampled blocks.
    v = values.reindex(pd.date_range(values.index.min(), values.index.max())).to_numpy(float)
    if np.isfinite(v).sum() < 8:
        return np.nan, np.nan
    rng = np.random.default_rng(3030)
    means = []
    for _ in range(draws):
        starts = rng.integers(0, len(v), size=int(np.ceil(len(v) / block_days)))
        indices = ((starts[:, None] + np.arange(block_days)) % len(v)).ravel()[: len(v)]
        sample = v[indices]
        means.append(np.nanmean(sample) if np.isfinite(sample).any() else np.nan)
    return tuple(np.nanquantile(means, [0.025, 0.975]))


def paired_stats(data, setting):
    rows = []
    cols = score_columns(*setting)
    for candidate in ["M", "Q25"]:
        for comparator in ["G", "P", "S", "-V"]:
            cc, ch = cols[candidate]
            rc, rh = cols[comparator]
            for date, g in data.groupby("date"):
                f = g.dropna(subset=[cc, rc])
                if len(f) < 5:
                    continue
                cr, rr = rank(f[cc], ch), rank(f[rc], rh)
                cw, rw = membership(f[cc], ch), membership(f[rc], rh)
                for horizon in HORIZONS:
                    for target in ["return", "drawdown"]:
                        y = f[f"forward_{target}_{horizon}"]
                        a, b = outcome_stats(y, cr, cw), outcome_stats(y, rr, rw)
                        rows.append(dict(setting=f"{setting[0]}_{setting[1]}", candidate=candidate, comparator=comparator, date=date, horizon=horizon, target=target, rho_difference=a["rho"] - b["rho"], spread_difference=a["spread"] - b["spread"]))
    return rows
