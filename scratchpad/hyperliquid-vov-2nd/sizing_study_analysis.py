"""Horizon-independent ledgers, paired fixed-unit outcomes and calibration."""

import json
import time
import numpy as np
import pandas as pd
from portfolio_snapshot_data import future_panel as inherited_future_panel
from portfolio_snapshot_construction import outcome_metrics, bounded_proportional, signed_return_bounds
from portfolio_snapshot_risk import qlike_difference
from portfolio_snapshot_statistics import support_counts
from sizing_study_design import START, END, primary_pairs
from sizing_study_allocation import allocate


def future_panel(data, origin, horizon, ids):
    """Keep inherited NAV targets; attribute the first actual update after anchor."""
    panel = inherited_future_panel(data, origin, horizon, ids)
    if "returns" not in panel:
        return panel
    a = data["date_index"][origin - pd.Timedelta(days=1)]
    jj = [data["id_index"][int(pid)] for pid in ids]
    actual = data["arrays"]["actual"][a + 1 : a + horizon + 1, jj]
    first = np.full(len(ids), np.nan)
    for j in range(len(ids)):
        if not panel["supported"][j]:
            continue
        pos = np.flatnonzero(actual[:, j])
        first[j] = float(panel["paths"][pos[0] + 1, j] / panel["paths"][0, j] - 1) if len(pos) else 0.0
    panel["first_update"] = first
    panel["remaining"] = panel["returns"] - first
    return panel


def execute(data, baskets, risk, policies, horizons, reuse=None):
    from tqdm_loggable.auto import tqdm

    start = time.monotonic()
    ledger = []
    outcomes = []
    attribution = []
    rg = {t: g for t, g in risk.groupby("origin_at")}
    bg = {(t, s): g.sort_values("rank") for (t, s), g in baskets.groupby(["origin_at", "selector"])}
    cg = {t: g.pivot(index="pair_id", columns="component", values="value") for t, g in data["components"].groupby("origin_at")}
    reused = 0
    for t in tqdm(data["origins"], desc=f'NB11 {data["stage"]}: {len(policies)} policies × 70 dates', mininterval=15):
        targets = {}
        for policy in policies:
            arm = policy["arm"]
            s = policy["selector"]
            basket = bg[(t, s)]
            ids = basket.pair_id.to_numpy(int)
            component = cg[t].reindex(ids)
            old = None if reuse is None else reuse["allocations"].query("origin_at == @t and arm == @arm").sort_values("rank")
            if old is not None and len(old):
                old = old.set_index("pair_id").reindex(ids).reset_index()
                reused += 1
                allocation = dict(desired=old.desired_weight.to_numpy(), accepted=old.accepted_weight.to_numpy(), caps=old.capacity.to_numpy(), unknown=old.unknown_state.to_numpy(), shadow=old.shadow_weight.to_numpy(), variances=old.risk_forecast.to_numpy(), status=old.fallback.iloc[0], cash=old.cash.iloc[0], distortion=old.cap_distortion.iloc[0])
            else:
                allocation = allocate(data, t, basket, policy, rg[t], component)
            u = allocation["desired"]
            w = allocation["accepted"]
            cap = allocation["caps"]
            B = w.sum()
            shadow = allocation["shadow"]
            benchmark = bounded_proportional(np.ones(len(ids)), cap, B)
            diagnostic_method = "regular" if policy["method"] in ("bounded_I", "bounded_V") else policy["method"]
            diagnostic = rg[t][(rg[t].estimator == diagnostic_method) & (rg[t].L == policy["L"]) & (rg[t].kappa == policy["kappa"])].set_index("pair_id").reindex(ids)
            selected_risk = rg[t][(rg[t].estimator.eq("regular")) & (rg[t].L.eq(90)) & (rg[t].kappa.eq(30))].set_index("pair_id").reindex(ids)
            for k, row in enumerate(basket.itertuples()):
                ledger.append(
                    dict(
                        origin_at=t,
                        arm=arm,
                        policy_id=policy["policy_id"],
                        selector=s,
                        rank=int(row.rank),
                        pair_id=int(row.pair_id),
                        vault_name=row.vault_name,
                        ranking_score=row.score,
                        ranking_tier=int(row.tier),
                        risk_forecast=float(allocation["variances"][k]),
                        desired_weight=float(u[k]),
                        accepted_weight=float(w[k]),
                        benchmark_weight=float(benchmark[k]),
                        shadow_weight=float(shadow[k]),
                        capacity=float(cap[k]),
                        unknown_state=bool(allocation["unknown"][k]),
                        cash=allocation["cash"],
                        fallback=allocation["status"],
                        cap_distortion=allocation["distortion"],
                        requested_effective_N=float(1 / np.sum(u * u)),
                        shadow_effective_N=float(1 / np.sum(u * u)),
                        accepted_effective_N=float(B * B / np.sum(w * w)) if B else 0,
                        max_weight_change=float(w.max() - shadow.max()),
                        effective_N_change=float(B * B / np.sum(w * w) - 1 / np.sum(u * u)) if B else 0,
                        original_actual_updates=float(selected_risk.m.iloc[k]),
                        original_actual_fraction=float(selected_risk.actual_fraction.iloc[k]),
                        original_anchor_age=float(selected_risk.anchor_age.iloc[k]),
                        original_longest_gap=float(selected_risk.longest_gap.iloc[k]),
                        history_age=float(selected_risk.history_age.iloc[k]),
                        original_risk_status=str(selected_risk.status.iloc[k]),
                        risk_method=policy["method"],
                        risk_L=policy["L"],
                        risk_p=policy["p"],
                        risk_kappa=policy["kappa"],
                        risk_units="log" if policy["method"] in ("calendar_log", "gap_log") else "simple",
                        risk_status=str(diagnostic.status.iloc[k]) if diagnostic_method in rg[t].estimator.values else allocation["status"],
                        fingerprint=data["fingerprint"],
                    )
                )
            for h in horizons:
                mature = bool(t + pd.Timedelta(days=h) <= END)
                if mature:
                    if (s, h) not in targets:
                        targets[(s, h)] = future_panel(data, t, h, ids)
                    panel = targets[(s, h)]
                    metric = outcome_metrics(panel, w)
                    base = outcome_metrics(panel, benchmark)
                    matched = metric["resolved"] and base["resolved"]
                    lift = metric["return"] - base["return"] if matched else np.nan
                    lower, upper = signed_return_bounds(w - benchmark, panel["returns"], panel["supported"])
                    if metric["resolved"]:
                        for k, pid in enumerate(ids):
                            attribution.append(dict(origin_at=t, arm=arm, selector=s, h=h, pair_id=int(pid), contribution=float(w[k] * panel["returns"][k]), first_update_contribution=float(w[k] * panel["first_update"][k]), weight=float(w[k])))
                else:
                    metric = dict(resolved=False, unresolved_weight=np.nan, cash=1 - B, effective_N=float(B * B / np.sum(w * w)) if B else 0, max_weight=float(w.max()), variance=np.nan, drawdown=np.nan, sharpe=np.nan, first_update=np.nan, remaining=np.nan, lower_return_bound=np.nan, upper_return_bound=np.nan, known_return_contribution=np.nan, carried_anchor_weight=np.nan, carried_endpoint_weight=np.nan, anchor_age_weighted=np.nan, endpoint_age_weighted=np.nan, no_update_weight=np.nan)
                    metric["return"] = np.nan
                    base = {"return": np.nan, "variance": np.nan, "drawdown": np.nan}
                    matched = False
                    lift = np.nan
                    lower = upper = np.nan
                outcomes.append(dict(origin_at=t, arm=arm, selector=s, h=h, mature=mature, status="mature" if mature else "pending", fallback=allocation["status"], selected_count=len(ids), positive_count=int((w > 0).sum()), unscored_selected=int(basket.tier.sum()), weighting_lift=lift, benchmark_return=base["return"], benchmark_variance=base["variance"], matched_equal_budget=matched, active_lower=lower, active_upper=upper, requested_effective_N=float(1 / np.sum(u * u)), cap_distortion=allocation["distortion"], label_end=t + pd.Timedelta(days=h - 1), **metric))
    result = dict(allocations=pd.DataFrame(ledger), outcomes=pd.DataFrame(outcomes), vault_attribution=pd.DataFrame(attribution), policies=pd.DataFrame(policies))
    result["risk"] = risk
    result["baskets"] = baskets
    result["calibration_rows"], result["calibration"] = calibration(data, baskets, risk, horizons)
    result.update(analyse(data, result, policies, horizons))
    for name, frame in result.items():
        frame.to_parquet(data["artifact"] / f"{name}.parquet", index=False)
    data["execution_seconds"] = time.monotonic() - start
    (data["artifact"] / "execution.json").write_text(json.dumps(dict(stage=data["stage"], policies=len(policies), origins=70, allocations=len(policies) * 70, allocation_vault_rows=len(ledger), scheduled_targets=len(outcomes), horizons=horizons, reused_smoke_allocations=reused, seconds=data["execution_seconds"], status="pending_audit"), indent=2))
    return result


def calibration(data, baskets, risk, horizons):
    rows = []
    rgroup = {t: g for t, g in risk.groupby("origin_at")}
    for t in data["origins"]:
        for s in ("F", "L"):
            ids = baskets[(baskets.origin_at == t) & (baskets.selector == s)].pair_id.to_numpy(int)
            r = rgroup[t][rgroup[t].pair_id.isin(ids)]
            for h in horizons:
                if t + pd.Timedelta(days=h) > END:
                    continue
                panel = future_panel(data, t, h, ids)
                loc = {int(pid): i for i, pid in enumerate(ids)}
                lr = np.diff(np.log(panel["paths"]), axis=0)
                lv = np.var(lr, axis=0, ddof=1)
                for v in r.itertuples():
                    j = loc[v.pair_id]
                    real = float(lv[j] if v.units == "log" else panel["variance"][j]) if panel["supported"][j] else np.nan
                    loss = float(qlike_difference(v.predicted, v.prior, real))
                    rows.append(dict(origin_at=t, selector=s, h=h, pair_id=v.pair_id, estimator=v.estimator, L=v.L, kappa=v.kappa, units=v.units, predicted=v.predicted, reference=v.prior, realised=real, qlike_delta=loss, actual_updates=v.m, anchor_age=v.anchor_age, history_age=v.history_age, prior_only=v.prior_only, floor_active=v.floor_active, prior_count=v.prior_count, prior_pool=v.prior_pool))
    frame = pd.DataFrame(rows)
    summaries = []
    keys = ["selector", "h", "estimator", "L", "kappa", "units"]
    for k, g in frame.groupby(keys):
        z = g[np.isfinite(g.predicted) & g.predicted.gt(0) & np.isfinite(g.realised) & g.realised.ge(0) & np.isfinite(g.qlike_delta)]
        per = z.groupby("origin_at").agg(predicted=("predicted", "mean"), realised=("realised", "mean"), loss=("qlike_delta", "mean"), median_loss=("qlike_delta", "median"), prior_only=("prior_only", "mean"), floor_active=("floor_active", "mean"), peer_count=("prior_count", "mean"), count=("pair_id", "size"))
        summaries.append(dict(zip(keys, k), origins=len(per), paired_vault_dates=len(z), qlike_delta=per.loss.mean(), median_origin_median_loss=per.median_loss.median(), calibration_ratio=per.realised.mean() / per.predicted.mean() if per.predicted.mean() > 0 else np.nan, prior_only_fraction=per.prior_only.mean(), floor_fraction=per.floor_active.mean(), mean_peer_count=per.peer_count.mean(), zero_realised_fraction=float(z.realised.eq(0).mean())))
    return frame, pd.DataFrame(summaries)


def analyse(data, result, policies, horizons):
    out = result["outcomes"]
    ledger = result["allocations"]
    registry = {p["arm"]: p for p in policies}
    summary = []
    for (arm, h), g in out.groupby(["arm", "h"], sort=False):
        m = g[g.mature & g.resolved]
        a = ledger[ledger.arm == arm]
        p = registry[arm]
        summary.append(dict(arm=arm, label=p["label"], selector=p["selector"], method=p["method"], L=p["L"], p=p["p"], kappa=p["kappa"], h=h, scheduled=len(g), mature=int(g.mature.sum()), pending=int((~g.mature).sum()), resolved=len(m), mean_return=m["return"].mean(), median_return=m["return"].median(), mean_variance=m.variance.mean(), mean_drawdown=m.drawdown.mean(), mean_cash=m.cash.mean(), effective_N=m.effective_N.mean(), max_weight=m.max_weight.mean(), fallback_fraction=g.fallback.str.contains("equal").mean() if p["method"] != "equal" else 0, mean_distortion=a.groupby("origin_at").cap_distortion.first().mean(), weighting_lift=m.weighting_lift.mean(), worst_origin=m["return"].min(), best_origin=m["return"].max(), first_update=m.first_update.mean(), remaining=m.remaining.mean()))
    summary = pd.DataFrame(summary)
    contrast_dates = []
    contrasts = []
    if len(policies) == 40:
        primary = primary_pairs(policies)
    else:
        primary = [("S16", "S15", "primary")]
    # Every arm is also compared with its selector's frozen 90-day baseline.
    pairs = list(primary)
    existing = {(a, b) for a, b, _ in pairs}
    for p in policies:
        base = "S03" if p["selector"] == "F" else "S04"
        if p["arm"] != base and (p["arm"], base) not in existing:
            pairs.append((p["arm"], base, "secondary"))
    mechanistic = [("S18", "S17"), ("M40", "M39"), ("M31", "M20"), ("M32", "M24"), ("M33", "M26"), ("M34", "M30")]
    mechanistic += [(a, b) for a in ("M35", "M36") for b in ("M20", "M24")]
    mechanistic += [(a, b) for a in ("M37", "M38") for b in ("M26", "M30")]
    available = {p["arm"] for p in policies}
    seen = {(a, b) for a, b, _ in pairs}
    for a, b in mechanistic:
        if a in available and b in available and (a, b) not in seen:
            pairs.append((a, b, "secondary"))
            seen.add((a, b))
    allocation_lookup = {(t, arm): g.set_index("pair_id") for (t, arm), g in ledger.groupby(["origin_at", "arm"])}
    contrast_attribution = []
    for arm, base, family in pairs:
        for h in horizons:
            x = out[(out.arm == arm) & (out.h == h) & out.mature].merge(out[(out.arm == base) & (out.h == h) & out.mature], on="origin_at", suffixes=("_new", "_base"), validate="one_to_one")
            ok = x.resolved_new & x.resolved_base
            effect = (x["return_new"] - x["return_base"]).where(ok)
            support_frame = pd.DataFrame({"origin_at": x.origin_at, "effect": effect})
            counts = support_counts(support_frame, START, END, h, h)
            paired = x[ok]
            rat = paired.variance_new.mean() / paired.variance_base.mean() if paired.variance_base.mean() > 0 else np.nan
            contrasts.append(dict(arm=arm, control=base, family=family, h=h, paired=int(ok.sum()), return_difference=effect.mean(), median_difference=effect.median(), variance_difference=(x.variance_new - x.variance_base)[ok].mean(), variance_ratio=rat, drawdown_difference=(x.drawdown_new - x.drawdown_base)[ok].mean(), cash_difference=(x.cash_new - x.cash_base)[ok].mean(), wins=int((effect > 1e-12).sum()), ties=int((effect.abs() <= 1e-12).sum()), losses=int((effect < -1e-12).sum()), complete_blocks=counts[2], inference_gate=counts[2] >= 10, interval_status="descriptive only: primary 51-statistic family fails 30-day block gate" if h == 30 else "secondary descriptive only: shared 51-statistic family not supported at primary horizon"))
            common = []
            for i, row in x.iterrows():
                aa = allocation_lookup[(row.origin_at, arm)]
                bb = allocation_lookup[(row.origin_at, base)].reindex(aa.index)
                ids = aa.index.to_numpy(int)
                target = future_panel(data, row.origin_at, h, ids)
                coef = aa.accepted_weight.to_numpy() - bb.accepted_weight.to_numpy()
                lower, upper = signed_return_bounds(coef, target["returns"], target["supported"])
                budget = min(aa.accepted_weight.sum(), bb.accepted_weight.sum())
                wa = bounded_proportional(aa.desired_weight.to_numpy(), aa.capacity.to_numpy(), budget)
                wb = bounded_proportional(bb.desired_weight.to_numpy(), bb.capacity.to_numpy(), budget)
                ma = outcome_metrics(target, wa)
                mb = outcome_metrics(target, wb)
                comm = ma["return"] - mb["return"] if ma["resolved"] and mb["resolved"] else np.nan
                common.append(comm)
                if ok.loc[i]:
                    for j, pid in enumerate(ids):
                        contrast_attribution.append(dict(origin_at=row.origin_at, arm=arm, control=base, h=h, pair_id=int(pid), contribution=float(coef[j] * target["returns"][j]), first_update_contribution=float(coef[j] * target["first_update"][j])))
                contrast_dates.append(dict(origin_at=row.origin_at, arm=arm, control=base, family=family, h=h, paired=bool(ok.loc[i]), active_lower=float(lower), active_upper=float(upper), common_budget=float(budget), common_budget_difference=float(comm), return_difference=float(effect.loc[i]), variance_difference=float(row.variance_new - row.variance_base) if ok.loc[i] else np.nan, drawdown_difference=float(row.drawdown_new - row.drawdown_base) if ok.loc[i] else np.nan, cash_difference=float(row.cash_new - row.cash_base), first_update_difference=float(row.first_update_new - row.first_update_base) if ok.loc[i] else np.nan))
            contrasts[-1]["common_budget_difference"] = float(np.nanmean(common)) if np.isfinite(common).any() else np.nan
            contrasts[-1]["common_budget_paired"] = int(np.isfinite(common).sum())
    q = out.assign(quarter=out.origin_at.dt.to_period("Q").astype(str))
    quarter = []
    for (arm, h, period), g in q.groupby(["arm", "h", "quarter"]):
        m = g[g.mature & g.resolved]
        quarter.append(dict(arm=arm, h=h, quarter=period, scheduled=len(g), mature=int(g.mature.sum()), resolved=len(m), mean_return=m["return"].mean(), mean_cash=m.cash.mean()))
    influence = []
    for (arm, h), g in out[out.mature & out.resolved].groupby(["arm", "h"]):
        for quarter_id in ("2026Q1", "2026Q2", "2026Q3", "2026Q4"):
            included = g.origin_at.dt.to_period("Q").astype(str).eq(quarter_id)
            rest = g[~included]
            influence.append(dict(arm=arm, h=h, quarter_removed=quarter_id, removed=int(included.sum()), remaining_origins=len(rest), difference=rest["return"].mean() - g["return"].mean() if included.any() else np.nan))
    att = result["vault_attribution"]
    vault = att.groupby(["arm", "h", "pair_id"]).agg(contribution_sum=("contribution", "sum"), held=("contribution", "size"), conditional_contribution=("contribution", "mean"), first_update_sum=("first_update_contribution", "sum")).reset_index()
    n = out[out.mature & out.resolved].groupby(["arm", "h"]).size()
    vault["mean_contribution"] = [row.contribution_sum / n.loc[(row.arm, row.h)] for row in vault.itertuples()]
    vault = vault.merge(data["identities"][["pair_id", "vault_name"]], on="pair_id", validate="many_to_one")
    overlap = []
    ties = []
    for t in data["origins"]:
        f = ledger[(ledger.origin_at == t) & (ledger.arm == "S03")].set_index("pair_id")
        l = ledger[(ledger.origin_at == t) & (ledger.arm == "S04")].set_index("pair_id")
        shared = f.index.intersection(l.index)
        union = f.index.union(l.index)
        overlap.append(dict(origin_at=t, jaccard=len(shared) / len(union), shared_accepted_weight=float(np.minimum(f.accepted_weight.reindex(union, fill_value=0), l.accepted_weight.reindex(union, fill_value=0)).sum())))
        for p in policies:
            base = "S03" if p["selector"] == "F" else "S04"
            g = ledger[(ledger.origin_at == t) & (ledger.arm == p["arm"])].set_index("pair_id")
            b = ledger[(ledger.origin_at == t) & (ledger.arm == base)].set_index("pair_id").reindex(g.index)
            ties.append(dict(origin_at=t, arm=p["arm"], control=base, requested_L1=float(np.abs(g.desired_weight - b.desired_weight).sum()), accepted_L1=float(np.abs(g.accepted_weight - b.accepted_weight).sum()), same_accepted=bool(np.allclose(g.accepted_weight, b.accepted_weight, atol=1e-12, rtol=0))))
    return dict(summary=summary, contrasts=pd.DataFrame(contrasts), contrast_dates=pd.DataFrame(contrast_dates), contrast_attribution=pd.DataFrame(contrast_attribution), quarterly=pd.DataFrame(quarter), quarter_influence=pd.DataFrame(influence), vault_influence=vault, selector_overlap=pd.DataFrame(overlap), cap_ties=pd.DataFrame(ties))
