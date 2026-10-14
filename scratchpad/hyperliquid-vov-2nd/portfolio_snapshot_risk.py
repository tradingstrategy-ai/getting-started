"""Explicit partial-history risk forecasts and leave-one-out priors."""

import numpy as np
import pandas as pd
from portfolio_snapshot_data import CONFIG, ARTIFACT

WINDOWS = (30, 60, 75, 90, 105, 180)


def empirical_window(nav, actual, L):
    """Sample risk on available calendar marks, counting actual updates separately."""
    nav = np.asarray(nav, float)[-(L + 1) :]
    actual = np.asarray(actual, bool)[-(L + 1) :]
    finite = np.isfinite(nav) & (nav > 0)
    first = np.flatnonzero(finite)
    if not len(first):
        return dict(empirical=np.nan, n=0, m=0, full=False, status="unavailable")
    start = first[0]
    p = nav[start:]
    m = int(actual[start + 1 :].sum())
    n = len(p) - 1
    valid = n >= 2 and m >= 1 and np.isfinite(p).all()
    empirical = float(np.var(p[1:] / p[:-1] - 1, ddof=1)) if valid else np.nan
    if not np.isfinite(empirical):
        empirical = np.nan
    full = start == 0 and len(nav) == L + 1
    status = "unavailable" if np.isnan(empirical) else "observed_flat" if empirical == 0 else "full_window" if full else "partial_window"
    return dict(empirical=empirical, n=n, m=m, full=full, status=status)


def peer_prior(empirical, full, index, gate=1):
    """Exclude the target itself from each full/partial positive peer pool."""
    good = np.isfinite(empirical) & (empirical > 0)
    good[index] = False
    for mask, name in ((good & full, "full"), (good, "partial")):
        values = empirical[mask]
        if len(values) >= gate:
            return float(np.median(values)), len(values), name, float(np.subtract(*np.percentile(values, [75, 25])))
    return np.nan, 0, "unavailable", np.nan


def forecast(empirical, prior, m, estimator, kappa, floor=1e-8):
    """Missing empirical risk is distinct from the final forecast fallback."""
    if estimator == "raw":
        value = empirical if np.isfinite(empirical) else prior
        return max(value, floor) if np.isfinite(value) else np.nan
    if np.isfinite(prior) and prior > 0:
        c = m / (m + kappa) if np.isfinite(empirical) else 0
        return c * (empirical if np.isfinite(empirical) else 0) + (1 - c) * prior
    return empirical if np.isfinite(empirical) and empirical > 0 else np.nan


def qlike_difference(predicted, reference, realised):
    """Paired QLIKE, allowing realised variance of exactly zero."""
    a, b, y = np.broadcast_arrays(predicted, reference, realised)
    good = np.isfinite(a) & np.isfinite(b) & np.isfinite(y) & (a > 0) & (b > 0) & (y >= 0)
    out = np.full(a.shape, np.nan)
    out[good] = np.log(a[good] / b[good]) + y[good] * (1 / a[good] - 1 / b[good])
    return out


def build_risk(data):
    from tqdm_loggable.auto import tqdm

    groups = data["eligibility"][data["eligibility"].eligible_as_of_origin].groupby("origin_at", sort=True)
    rows = []
    for origin, candidates in tqdm(groups, desc="Risk tensors; approximately 1–2 minutes"):
        a = data["date_index"][origin - pd.Timedelta(days=1)]
        ids = candidates.pair_id.to_numpy()
        jj = np.array([data["id_index"][int(pid)] for pid in ids])
        for L in WINDOWS:
            values = [empirical_window(data["arrays"]["nav"][max(0, a - L) : a + 1, j], data["arrays"]["actual"][max(0, a - L) : a + 1, j], L) for j in jj]
            emp = np.array([v["empirical"] for v in values])
            full = np.array([v["full"] for v in values])
            for i, (pid, j, val) in enumerate(zip(ids, jj, values)):
                prior, count, pool, dispersion = peer_prior(emp, full, i)
                p5, n5, pool5, _ = peer_prior(emp, full, i, 5)
                p10, n10, pool10, _ = peer_prior(emp, full, i, 10)
                source = np.nan
                if L == 90:
                    p = data["arrays"]["source"][max(0, a - L) : a + 1, j]
                    if len(p) == L + 1 and np.isfinite(p).all() and (p > 0).all():
                        source = max(float(np.var(p[1:] / p[:-1] - 1, ddof=1)), 1e-8)
                age = int(a - data["first_index"][j])
                obs = data["arrays"]["last_observed"][a, j]
                obs_age = float((data["nav"].index[a].to_datetime64() + np.timedelta64(1, "D") - obs) / np.timedelta64(1, "D"))
                rows.append(dict(origin_at=origin, pair_id=int(pid), L=L, **val, prior=prior, prior_count=count, prior_pool=pool, prior_dispersion=dispersion, prior_weak=count < 5, prior5=p5, prior10=p10, source=source, raw=forecast(emp[i], prior, val["m"], "raw", L / 3), regularised=forecast(emp[i], prior, val["m"], "regularised", L / 3), kappa30=forecast(emp[i], prior, val["m"], "regularised", 30), kappa10=forecast(emp[i], prior, val["m"], "regularised", 10), kappa90=forecast(emp[i], prior, val["m"], "regularised", 90), gate5=forecast(emp[i], p5, val["m"], "regularised", L / 3), gate10=forecast(emp[i], p10, val["m"], "regularised", L / 3), floor_low=forecast(emp[i], prior, val["m"], "raw", L / 3, 1e-10), floor_high=forecast(emp[i], prior, val["m"], "raw", L / 3, 1e-6), history_age=age, anchor_age=obs_age, actual_fraction=val["m"] / val["n"] if val["n"] else 0))
    frame = pd.DataFrame(rows)
    assert not frame.duplicated(["origin_at", "pair_id", "L"]).any()
    frame.to_parquet(ARTIFACT / "risk.parquet", index=False)
    return frame
