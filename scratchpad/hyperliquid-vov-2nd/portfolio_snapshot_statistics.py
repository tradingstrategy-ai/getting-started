"""Paired calendar inference and mechanism diagnostics for snapshot portfolios."""

import itertools
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from portfolio_snapshot_data import METHODS, CONFIG, ARTIFACT, PERIODS, START, END, future_panel
from portfolio_snapshot_construction import select_basket, risk_weights, fixed_unit_path


def period_frame(frame, period="2026", h=None, phase=0):
    start, end = PERIODS[period]
    mask = frame.origin_at.ge(start) & frame.origin_at.lt(end)
    if "phase" in frame and phase is not None:
        mask &= frame.phase.eq(phase)
    if h is not None and "h" in frame:
        mask &= frame.h.eq(h)
    if "h" in frame:
        mask &= (frame.origin_at + pd.to_timedelta(frame.h, unit="D")).le(end)
    return frame[mask].copy()


def macro_risk_summary(frame, period="2026"):
    frame = period_frame(frame, period)
    rows = []
    for cohort in ("eligible", "selected"):
        subset = frame if cohort == "eligible" else frame[frame.selected]
        for keys, f in subset.groupby(["score", "estimator", "L", "h"], observed=True):
            per = []
            loss_parts = []
            raw_losses = []
            row_weights = []
            for t, g in f.groupby("origin_at"):
                good = np.isfinite(g.predicted) & np.isfinite(g.realised) & (g.predicted > 0)
                z = g[good]
                n = len(z)
                ic = float(spearmanr(z.predicted, z.realised).statistic) if n >= 3 and z.predicted.nunique() > 1 and z.realised.nunique() > 1 else np.nan
                q = z[np.isfinite(z.qlike_delta)]
                per.append(dict(ic=ic, predicted=z.predicted.mean(), realised=z.realised.mean(), qlike=q.qlike_delta.mean(), mse=((z.predicted - z.realised) ** 2).mean(), n=n))
                if len(q):
                    loss_parts.extend((q.qlike_delta.to_numpy() / len(q)).tolist())
                    raw_losses.extend(q.qlike_delta.tolist())
                    row_weights.extend([1 / len(q)] * len(q))
            d = pd.DataFrame(per)
            loss = np.array(loss_parts)
            n_origins = int(d.qlike.notna().sum())
            weighted = loss / n_origins if n_origins else loss
            k = int(np.ceil(len(weighted) * CONFIG["tail_fraction"]))
            top = np.argsort(np.abs(weighted))[-k:] if k else []
            raw_losses = np.asarray(raw_losses)
            row_weights = np.asarray(row_weights)
            order = np.argsort(raw_losses)
            median_loss = raw_losses[order][np.searchsorted(np.cumsum(row_weights[order]), row_weights.sum() / 2)] if len(order) else np.nan
            positives = f[np.isfinite(f.predicted) & np.isfinite(f.realised) & f.predicted.gt(0) & f.realised.gt(0)]
            rows.append(dict(period=period, score=keys[0], estimator=keys[1], L=keys[2], h=keys[3], cohort=cohort, risk_ic=d.ic.mean(), qlike_delta=d.qlike.mean(), calibration_ratio=d.predicted.mean() / d.realised.mean() if d.realised.mean() > 0 else np.nan, mse=d.mse.mean(), paired_origins=n_origins, ic_origins=int(d.ic.notna().sum()), paired_rows=len(loss), qlike_median=float(median_loss), win_fraction=float(np.average(raw_losses < 0, weights=row_weights)) if len(raw_losses) else np.nan, tail_absolute_share=float(np.abs(weighted[top]).sum() / np.abs(weighted).sum()) if np.abs(weighted).sum() else np.nan, tail_signed_contribution=float(weighted[top].sum()) if len(top) else np.nan, median_log_ratio=float(np.median(np.log(positives.predicted / positives.realised))) if len(positives) else np.nan, zero_realised_fraction=float(f.loc[np.isfinite(f.predicted) & f.predicted.gt(0) & np.isfinite(f.realised), "realised"].eq(0).mean()), omitted_target_rows=int(f.realised.isna().sum())))
    return pd.DataFrame(rows)


def summarise_policies(result, period="2026"):
    f = period_frame(result["outcomes"], period)
    summary = (
        f.groupby(["policy_id", "h"], observed=True)
        .agg(
            origins=("resolved", "size"),
            resolved_origins=("resolved", "sum"),
            mean_return=("return", "mean"),
            median_return=("return", "median"),
            mean_variance=("variance", "mean"),
            mean_drawdown=("drawdown", "mean"),
            weighting_lift=("weighting_lift", "mean"),
            variance_lift=("variance_lift", "mean"),
            drawdown_lift=("drawdown_lift", "mean"),
            selection_lift=("selection_lift", "mean"),
            universe_resolved=("universe_supported", "sum"),
            mean_cash=("cash", "mean"),
            effective_N=("effective_N", "mean"),
            max_weight=("max_weight", "mean"),
            unresolved_weight=("unresolved_weight", "mean"),
            fallback_fraction=("risk_fallback_equal", "mean"),
            unscored_selected=("unscored_selected", "mean"),
            first_update_lift=("first_update_lift", "mean"),
            remaining_lift=("remaining_lift", "mean"),
            carried_anchor_weight=("carried_anchor_weight", "mean"),
            carried_endpoint_weight=("carried_endpoint_weight", "mean"),
            no_update_weight=("no_update_weight", "mean"),
            mean_forecast_variance=("forecast_variance", "mean"),
            mean_covariance_forecast_variance=("covariance_forecast_variance", "mean"),
        )
        .reset_index()
        .merge(result["policies"], on="policy_id", validate="many_to_one")
    )
    summary["period"] = period
    return summary


def build_contrasts(result):
    p = result["policies"]
    out = result["outcomes"]
    rows = []
    attributions = []

    def policy(score, N, estimator, power):
        z = p[(p.score == score) & (p.N == N) & (p.estimator == estimator) & (p.p == power) & (p.L == 90) & (p.branch == "pure") & (p.variant == "main")]
        assert len(z) == 1
        return z.policy_id.iloc[0]

    relevant = result["policies"][result["policies"].branch.eq("pure") & result["policies"].variant.eq("main") & result["policies"].L.eq(90)]
    weights = {(t, pid): g.set_index("pair_id").accepted_weight for (t, pid), g in result["allocations"][result["allocations"].policy_id.isin(relevant.policy_id)].groupby(["origin_at", "policy_id"])}
    families = {}
    for score in METHODS:
        families[score] = [("power_1_minus_2", policy(score, 6, "raw", 1), policy(score, 6, "raw", 2)), ("regularised_minus_raw", policy(score, 6, "regularised", 2), policy(score, 6, "raw", 2)), ("breadth_10_minus_6", policy(score, 10, "regularised", 2), policy(score, 6, "regularised", 2))]
        for name, left, right in families[score]:
            a = out[out.policy_id == left]
            b = out[out.policy_id == right]
            paired = a.merge(b, on=["origin_at", "h", "phase"], suffixes=("_a", "_b"), validate="one_to_one")
            valid = paired.resolved_a & paired.resolved_b
            for row in paired.itertuples():
                ok = bool(row.resolved_a and row.resolved_b)
                wa = weights.get((row.origin_at, left), pd.Series(dtype=float))
                wb = weights.get((row.origin_at, right), pd.Series(dtype=float))
                ids = wa.index.union(wb.index).to_numpy(dtype=int)
                panel = future_panel(result["_data"], row.origin_at, row.h, ids)
                active = wa.reindex(ids, fill_value=0).to_numpy() - wb.reindex(ids, fill_value=0).to_numpy()
                from portfolio_snapshot_construction import signed_return_bounds

                bounds = signed_return_bounds(active, panel["returns"], panel["supported"])
                for target in ("return", "variance"):
                    rows.append(dict(origin_at=row.origin_at, h=row.h, phase=row.phase, comparison_id=score + "|" + name + "|" + target, score=score, comparison=name, target=target, effect=getattr(row, target + "_a") - getattr(row, target + "_b") if ok else np.nan, paired=ok, conditional_active=not row.risk_fallback_equal_a and not row.risk_fallback_equal_b, actual_breadth_changed=row.N_actual_a != row.N_actual_b, unresolved_weight=max(row.unresolved_weight_a, row.unresolved_weight_b), lower_bound=bounds[0] if target == "return" else (getattr(row, target + "_a") - getattr(row, target + "_b") if ok else -np.inf), upper_bound=bounds[1] if target == "return" else (getattr(row, target + "_a") - getattr(row, target + "_b") if ok else np.inf)))
    contrasts = pd.DataFrame(rows)
    # Exact nested basket attribution at the fixed original notional.
    alloc = result["allocations"]
    for score in METHODS:
        for estimator in ("raw", "regularised"):
            for power in (0, 1, 2):
                est = "equal" if power == 0 else estimator
                if power == 0 and estimator == "regularised":
                    continue
                core = policy(score, 6, est, power)
                for N in (4, 8, 10):
                    wider = policy(score, N, est, power)
                    a = alloc[(alloc.policy_id == wider) & alloc.phase.eq(0)]
                    b = alloc[(alloc.policy_id == core) & alloc.phase.eq(0)]
                    for t in sorted(out[out.policy_id.eq(wider) & out.phase.eq(0)].origin_at.unique()):
                        t = pd.Timestamp(t)
                        ga = a[a.origin_at.eq(t)]
                        gb = b[b.origin_at == t]
                        wa = ga.set_index("pair_id").accepted_weight
                        wb = gb.set_index("pair_id").accepted_weight
                        ids = wa.index.union(wb.index).to_numpy()
                        for h in (7, 30, 90):
                            if t + pd.Timedelta(days=h) > END:
                                continue
                            target = future_panel(result["_data"], t, h, ids)
                            x = wa.reindex(ids, fill_value=0).to_numpy()
                            y = wb.reindex(ids, fill_value=0).to_numpy()
                            active = (x > 0) | (y > 0)
                            ok = bool(target["supported"][active].all())
                            shared = np.isin(ids, wa.index) & np.isin(ids, wb.index)
                            added = np.isin(ids, wa.index) & ~np.isin(ids, wb.index)
                            removed = ~np.isin(ids, wa.index) & np.isin(ids, wb.index)
                            terms = [float(np.dot((x - y)[mask], target["returns"][mask])) if ok else np.nan for mask in (shared, added, removed)]
                            total = float(np.dot((x - y)[active], target["returns"][active])) if ok else np.nan
                            assert not ok or np.isclose(sum(terms), total, atol=1e-10)
                            attributions.append(dict(origin_at=t, h=h, phase=0, score=score, estimator=est, p=power, N=N, shared_reweighting=terms[0], new_names=terms[1], removed_names=terms[2], cash_contribution=0, total=total, resolved=ok))
    return contrasts, pd.DataFrame(attributions)


def support_counts(frame, start, end, horizon, block):
    schedule = pd.date_range(start, end - pd.Timedelta(days=horizon), freq="D")
    values = frame.set_index("origin_at").effect.reindex(schedule)
    scheduled = frame.origin_at.to_numpy()
    finite = frame[np.isfinite(frame.effect)].sort_values("origin_at")
    nonoverlap = 0
    last_end = pd.Timestamp.min
    for t in finite.origin_at:
        anchor = t - pd.Timedelta(days=1)
        if anchor >= last_end:
            nonoverlap += 1
            last_end = anchor + pd.Timedelta(days=horizon)
    complete_blocks = 0
    for i in range(0, len(schedule) - block + 1, block):
        lo = schedule[i]
        hi = schedule[i + block - 1]
        g = frame[(frame.origin_at >= lo) & (frame.origin_at <= hi)]
        if len(g) and g.effect.notna().all():
            complete_blocks += 1
    return values, nonoverlap, complete_blocks


def simultaneous_intervals(contrasts, period="2026", block_multiplier=1):
    """Shared moving daily blocks preserve gaps and the frozen 18-member family."""
    f = period_frame(contrasts, period, h=30)
    start, end = PERIODS[period]
    block = 30 * block_multiplier
    ids = sorted(f.comparison_id.unique())
    assert len(ids) == 18
    schedule = pd.date_range(start, end - pd.Timedelta(days=30), freq="D")
    matrix = f.pivot(index="origin_at", columns="comparison_id", values="effect").reindex(index=schedule, columns=ids).to_numpy()
    theta = np.array([np.mean(col[np.isfinite(col)]) if np.isfinite(col).any() else np.nan for col in matrix.T])
    counts = [support_counts(f[f.comparison_id == cid], start, end, 30, block) for cid in ids]
    gate = np.array([x[2] >= 10 for x in counts])
    status = "exploratory simultaneous" if gate.all() else "descriptive; insufficient blocks"
    lower = upper = np.full(18, np.nan)
    marginal_low = marginal_high = np.full(18, np.nan)
    invalid = 1999
    degenerate = np.zeros(18, bool)
    if gate.all() and len(schedule) >= block:
        rng = np.random.default_rng(1010)
        boot = np.full((1999, 18), np.nan)
        nb = int(np.ceil(len(schedule) / block))
        offset = np.arange(block)
        for i in range(1999):
            indices = (rng.integers(0, len(schedule) - block + 1, size=nb)[:, None] + offset).ravel()[: len(schedule)]
            sample = matrix[indices]
            denom = np.isfinite(sample).sum(axis=0)
            boot[i] = np.divide(np.nansum(sample, axis=0), denom, out=np.full(18, np.nan), where=denom > 0)
        valid = np.isfinite(boot).all(axis=1)
        invalid = int((~valid).sum())
        sd = np.nanstd(boot, axis=0, ddof=1)
        degenerate = sd == 0
        marginal_low, marginal_high = np.nanquantile(boot, [0.025, 0.975], axis=0)
        if valid.mean() >= 0.95:
            z = np.divide(boot[valid] - theta, sd, out=np.zeros_like(boot[valid]), where=sd > 0)
            q = np.quantile(np.max(np.abs(z), axis=1), 0.95)
            lower = theta - q * sd
            upper = theta + q * sd
        else:
            status = "descriptive; joint draw gate failed"
    rows = []
    for j, cid in enumerate(ids):
        g = f[f.comparison_id == cid]
        active = g[g.conditional_active]
        breadth = g[g.actual_breadth_changed]
        rows.append(dict(period=period, comparison_id=cid, mean=theta[j], median=g.effect.median(), paired_origins=int(g.effect.notna().sum()), nonoverlapping_windows=counts[j][1], complete_blocks=counts[j][2], block_days=block, status=status, lower=lower[j], upper=upper[j], marginal_lower=marginal_low[j], marginal_upper=marginal_high[j], invalid_joint_draws=invalid, degenerate=degenerate[j], conditional_active_mean=active.effect.mean(), conditional_active_origins=int(active.effect.notna().sum()), changed_breadth_mean=breadth.effect.mean(), changed_breadth_origins=int(breadth.effect.notna().sum())))
    return pd.DataFrame(rows)


def assignment_placebo(data, result):
    """Exact date permutations and persistent identity-priority pooled nulls."""
    policies = result["policies"]
    a = result["allocations"]
    out = result["outcomes"]
    date_rows = []
    pooled = []
    rng = np.random.default_rng(2010)
    ids_all = data["identities"].pair_id.to_numpy()
    idmap = {int(pid): i for i, pid in enumerate(ids_all)}
    # A seeded random priority per identity/draw is a stable coherent mapping.
    priorities = rng.random((999, len(ids_all)))
    controls = policies[(policies.N == 6) & (policies.L == 90) & policies.p.isin([1, 2]) & policies.estimator.eq("regularised") & policies.variant.eq("main") & policies.branch.eq("pure")]
    for policy in controls.itertuples():
        available = a[(a.policy_id == policy.policy_id) & a.phase.eq(0)]
        for period in PERIODS:
            start, end = PERIODS[period]
            null_r = []
            null_v = []
            observed = []
            for t, g in available.groupby("origin_at"):
                if t < start or t + pd.Timedelta(days=30) > end:
                    continue
                ids = g.pair_id.to_numpy()
                w = g.accepted_weight.to_numpy()
                N = len(w)
                panel = future_panel(data, t, 30, ids)
                if not N or not panel["supported"].all():
                    continue
                permutations = np.array(list(itertools.permutations(w.tolist())))
                ret = permutations @ panel["returns"]
                eq = float(np.mean(panel["returns"]))
                actual = float(w @ panel["returns"])
                assert np.isclose(ret.mean(), eq, atol=1e-10)
                growth = panel["paths"] / panel["paths"][0]
                path = growth @ permutations.T
                var = np.var(path[1:] / path[:-1] - 1, axis=0, ddof=1)
                actual_path = growth @ w
                actual_var = float(np.var(actual_path[1:] / actual_path[:-1] - 1, ddof=1))
                return_tol = CONFIG["tie_comparison_relative_tolerance"] * max(abs(actual), float(np.abs(ret).max()), np.finfo(float).tiny)
                variance_tol = CONFIG["tie_comparison_relative_tolerance"] * max(abs(actual_var), float(np.abs(var).max()), np.finfo(float).tiny)
                date_rows.append(dict(period=period, origin_at=t, policy_id=policy.policy_id, score=policy.score, p=policy.p, h=30, N_actual=N, observed_lift=actual - eq, return_percentile=float(np.mean(ret < actual - return_tol) + 0.5 * np.mean(np.abs(ret - actual) <= return_tol)), variance_percentile=float(np.mean(var < actual_var - variance_tol) + 0.5 * np.mean(np.abs(var - actual_var) <= variance_tol)), degenerate_return=bool(np.ptp(ret) <= return_tol), degenerate_variance=bool(np.ptp(var) <= variance_tol), permutations=len(permutations)))
                orders = np.argsort(priorities[:, [idmap[int(pid)] for pid in ids]], axis=1)
                random_weights = np.zeros((999, N))
                np.put_along_axis(random_weights, orders, np.broadcast_to(np.sort(w)[::-1], (999, N)), axis=1)
                null_r.append(random_weights @ panel["returns"] - eq)
                paths = growth @ random_weights.T
                null_v.append(np.var(paths[1:] / paths[:-1] - 1, axis=0, ddof=1))
                observed.append((actual - eq, actual_var))
            if observed:
                nr = np.mean(null_r, axis=0)
                nv = np.mean(null_v, axis=0)
                obs = np.mean(observed, axis=0)
                prob = float(np.mean(nr >= obs[0]))
                pooled.append(dict(period=period, policy_id=policy.policy_id, score=policy.score, p=policy.p, h=30, origins=len(observed), observed_lift=obs[0], null_mean=nr.mean(), null_low=np.quantile(nr, 0.025), null_high=np.quantile(nr, 0.975), fraction_null_above=prob, monte_carlo_se=np.sqrt(prob * (1 - prob) / 999), observed_variance=obs[1], null_variance_mean=nv.mean()))
    return pd.DataFrame(date_rows), pd.DataFrame(pooled)


def tie_sensitivity(data, risk, draws=999):
    """Seeded tie priorities change membership only inside identical-score tiers."""
    rng = np.random.default_rng(3010)
    rows = []
    risk_lookup = {(t, L): f.set_index("pair_id") for (t, L), f in risk.groupby(["origin_at", "L"])}
    idmap = data["id_index"]
    priorities = rng.random((draws, len(idmap)))
    from portfolio_snapshot_construction import outcome_metrics

    for (t, score), g in data["candidates"].groupby(["origin_at", "method_id"], observed=True):
        if t < START or t + pd.Timedelta(days=30) > END or (t - START).days % 4:
            continue
        original = select_basket(g, 6)
        cut = original.score.iloc[-1] if len(original) else np.nan
        at_boundary = g[g.score.eq(cut)] if np.isfinite(cut) else g[g.score.isna()]
        if len(at_boundary) <= 1:
            continue
        rf = risk_lookup[(t, 90)]
        effects = []
        membership = []
        cache = {}
        for draw in range(draws):
            tie = {addr: priorities[draw, idmap[int(pid)]] for addr, pid in zip(g.vault_address, g.pair_id)}
            chosen = select_basket(g, 6, tie_priorities=tie)
            ids = tuple(sorted(chosen.pair_id.to_numpy()))
            if ids not in cache:
                v = rf.reindex(ids).regularised.to_numpy()
                panel = future_panel(data, t, 30, ids)
                cache[ids] = outcome_metrics(panel, risk_weights(v, 2))["return"]
            effects.append(cache[ids])
            membership.append(len(set(ids) ^ set(original.pair_id)) / 2)
        values = np.array(effects)
        finite = values[np.isfinite(values)]
        rows.append(dict(origin_at=t, score=score, h=30, tie_mass=len(at_boundary), draws=draws, resolved_draws=len(finite), return_low=np.quantile(finite, 0.025) if len(finite) else np.nan, return_high=np.quantile(finite, 0.975) if len(finite) else np.nan, return_mean=np.mean(finite) if len(finite) else np.nan, changed_names=np.mean(membership), unique_baskets=len(cache)))
    return pd.DataFrame(rows)


def synthetic_reporting(data=None):
    """Known dense paths challenge sparse risk claims without imputing latent risk."""
    from portfolio_snapshot_risk import empirical_window, forecast

    rng = np.random.default_rng(1010)
    rows = []
    for process in ("diffusive", "alternating", "catch_up_jump"):
        for replicate in range(100):
            r = rng.normal(0.0002, 0.01, 180) if process == "diffusive" else 0.01 * (-1.0) ** np.arange(180) if process == "alternating" else np.where(np.arange(180) % 31 == 0, 0.07, 0)
            p = np.exp(np.r_[0, np.cumsum(r)])
            true = np.var(p[1:] / p[:-1] - 1, ddof=1)
            for spacing in (1, 2, 7, "empirical"):
                if spacing == "empirical":
                    j = replicate % len(data["nav"].columns) if data is not None else 0
                    actual = data["arrays"]["actual"][-len(p) :, j].copy() if data is not None else rng.random(len(p)) < 0.3
                else:
                    actual = np.arange(len(p)) % spacing == 0
                actual[0] = True
                observed = np.where(actual, p, np.nan)
                filled = pd.Series(observed).ffill().to_numpy()
                val = empirical_window(filled, actual, 180)
                for estimator in ("raw", "regularised"):
                    pred = forecast(val["empirical"], true, val["m"], estimator, 60)
                    rows.append(dict(process=process, replicate=replicate, spacing_days=str(spacing), estimator=estimator, ratio=pred / true, empirical_supported=bool(np.isfinite(val["empirical"])), actual_updates=val["m"], prior="known dense variance for mechanism isolation"))
    return pd.DataFrame(rows)


def score_placebos(data, result):
    """Date exchangeability and pre-origin age/quality stratified assignment nulls."""
    rng = np.random.default_rng(2010)
    rows = []
    risk = result["_risk"]
    rf = risk[risk.L.eq(90)].set_index(["origin_at", "pair_id"])
    for method in METHODS:
        nulls = {mode: [] for mode in ("exchangeable", "age_quality_stratified")}
        obs = []
        for (t, m), g in data["candidates"].groupby(["origin_at", "method_id"], observed=True):
            if m != method or t < START or t + pd.Timedelta(days=30) > END or (t - START).days % 4:
                continue
            panel = future_panel(data, t, 30, g.pair_id.to_numpy())
            good = np.isfinite(g.score.to_numpy()) & np.isfinite(panel["returns"])
            ss = g.score.to_numpy()[good]
            yy = panel["returns"][good]
            if len(ss) < 3 or np.ptp(ss) == 0 or np.ptp(yy) == 0:
                continue
            sr = pd.Series(ss).rank().to_numpy()
            yr = pd.Series(yy).rank().to_numpy()
            yr = (yr - yr.mean()) / np.linalg.norm(yr - yr.mean())
            sr = sr - sr.mean()
            sr /= np.linalg.norm(sr)
            obs.append(float(sr @ yr))
            sub = g.iloc[np.flatnonzero(good)]
            rrows = rf.loc[[(t, int(pid)) for pid in sub.pair_id]]
            age = pd.qcut(rrows.history_age.rank(method="first"), 3, labels=False, duplicates="drop").to_numpy()
            quality = pd.qcut(rrows.actual_fraction.rank(method="first"), 3, labels=False, duplicates="drop").to_numpy()
            strata = age * 3 + quality
            for mode in nulls:
                arr = np.empty(999)
                for draw in range(999):
                    perm = sr.copy()
                    if mode == "exchangeable":
                        rng.shuffle(perm)
                    else:
                        for s in np.unique(strata):
                            idx = np.flatnonzero(strata == s)
                            perm[idx] = rng.permutation(perm[idx])
                    arr[draw] = perm @ yr
                nulls[mode].append(arr)
        for mode, arrays in nulls.items():
            if arrays:
                null = np.mean(arrays, axis=0)
                observed = np.mean(obs)
                rows.append(dict(score=method, h=30, mode=mode, origins=len(obs), observed_ic=observed, null_low=np.quantile(null, 0.025), null_high=np.quantile(null, 0.975), fraction_null_above=np.mean(null >= observed), caveat="conditional exchangeability null; independently permuted dates, not persistent policy inference"))
    return pd.DataFrame(rows)


def run_statistics(data, risk, result):
    from tqdm_loggable.auto import tqdm

    result["_data"] = data
    result["_risk"] = risk
    print("Exact paired contrasts and breadth attribution; approximately30seconds", flush=True)
    contrasts, breadth = build_contrasts(result)
    summaries = pd.concat([summarise_policies(result, p) for p in PERIODS], ignore_index=True)
    risk_summary = pd.concat([macro_risk_summary(result["risk_evaluation"], p) for p in tqdm(PERIODS, desc="Risk-loss summaries; approximately one minute")], ignore_index=True)
    intervals = pd.concat([simultaneous_intervals(contrasts, p, b) for p in PERIODS for b in (1, 2)], ignore_index=True)
    print("Companion diagnostics: assignment, ties and score nulls; approximately 3–6 minutes", flush=True)
    date_placebo, pooled_placebo = assignment_placebo(data, result)
    ties = tie_sensitivity(data, risk)
    synthetic = synthetic_reporting(data)
    score_null = score_placebos(data, result)
    frames = dict(contrasts=contrasts, breadth_attribution=breadth, summaries=summaries, risk_summary=risk_summary, intervals=intervals, assignment_dates=date_placebo, assignment_pooled=pooled_placebo, ties=ties, synthetic=synthetic, score_null=score_null)
    for name, frame in frames.items():
        frame.to_parquet(ARTIFACT / f"{name}.parquet", index=False)
    result.update(frames)
    return result
