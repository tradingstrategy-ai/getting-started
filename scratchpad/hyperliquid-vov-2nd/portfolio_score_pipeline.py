"""Full-2026 smoke execution, fixed-unit targets and descriptive diagnostics."""

import json
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from portfolio_score_design import START, END, recipe_id, label, next_stage_registry
from portfolio_score_recipes import evaluate, sizing_values
from portfolio_score_allocation import project, score_risk_budget
from portfolio_snapshot_data import future_panel
from portfolio_snapshot_construction import risk_weights, bounded_proportional, outcome_metrics


def corr(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    g = np.isfinite(x) & np.isfinite(y)
    return float(spearmanr(x[g], y[g]).statistic) if g.sum() >= 3 and np.ptp(x[g]) > 0 and np.ptp(y[g]) > 0 else np.nan


def execute_smoke(data, tensors, policies):
    """Store ex-ante allocations for all origins; evaluate mature targets only."""
    from tqdm_loggable.auto import tqdm

    folder = data["artifact"]
    started = time.monotonic()
    allocations = []
    candidates = []
    outcomes = []
    scores = []
    ics = []
    diagnostics = []
    attribution = []
    cf = {(t): f.pivot(index="pair_id", columns="component", values="value") for t, f in tensors["components"].groupby("origin_at")}
    rf = {(t, L): f.set_index("pair_id") for (t, L), f in tensors["risk"].groupby(["origin_at", "L"])}
    cache = {}
    score_cache = {}
    basket_cache = {}
    for origin in tqdm(data["origins"], desc="36 score policies × full 2026; estimated 1–3 minutes", mininterval=15):
        eligible = data["eligibility"][data["eligibility"].origin_at.eq(origin) & data["eligibility"].eligible_as_of_origin].copy().set_index("pair_id", drop=False)
        ids = eligible.pair_id.to_numpy(int)
        components = {name: cf[origin].reindex(ids)[name].to_numpy(float) for name in cf[origin].columns}
        mature = bool(origin + pd.Timedelta(days=30) <= END)
        all_future = future_panel(data, origin, 30, ids) if mature else None
        future_index = {int(pid): i for i, pid in enumerate(ids)}
        for policy in policies:
            arm = policy["arm"]
            missing = "M0" if policy["missing"] == "Legacy" else policy["missing"]
            evaluated = []
            for role in ("ranking", "weighting"):
                expr = policy[role]
                if expr == "source90":
                    evaluated.append(None)
                    continue
                key = (origin, recipe_id(expr), missing)
                if key not in score_cache:
                    result = evaluate(expr, components, missing)
                    score_cache[key] = result
                    for i, pid in enumerate(ids):
                        scores.append(dict(origin_at=origin, pair_id=int(pid), recipe_id=key[1], recipe=label(expr), missing=missing, value=float(result["value"][i]), available=bool(result["available"][i]), available_mass=float(result["mass"][i]), imputed_mass=float(1 - result["mass"][i])))
                evaluated.append(score_cache[key])
            R, Q = evaluated
            order = pd.DataFrame(dict(pair_id=ids, tier=np.where(R["available"], 0, 1), score=np.where(R["available"], R["value"], np.nan), chain=eligible.chain_id.to_numpy(), address=eligible.vault_address.str.lower().to_numpy()))
            selected = order.sort_values(["tier", "score", "chain", "address"], ascending=[True, False, True, True], na_position="last", kind="stable").head(policy["N"])
            selected_ids = selected.pair_id.to_numpy(int)
            loc = np.array([future_index[int(pid)] for pid in selected_ids])
            basket = eligible.loc[selected_ids].copy().reset_index(drop=True)
            basket["score"] = selected.score.to_numpy()
            basket["tier"] = selected.tier.to_numpy()
            basket_cache[(origin, arm)] = set(selected_ids)
            risk = rf[(origin, 90)].reindex(selected_ids)
            variances = risk.regularised.to_numpy(float)
            covariance = None
            error = np.nan
            if policy["sizing_map"] == "source":
                desired = risk_weights(risk.source.to_numpy(float), 2)
                status = "source_estimate" if np.isfinite(risk.source).all() else "source_equal_fallback"
                raw_requested = desired.copy()
                weighting_value = np.full(len(selected_ids), np.nan)
                weighting_available = np.zeros(len(selected_ids), bool)
                target_budget = np.full(len(selected_ids), np.nan)
            else:
                raw_requested = sizing_values(Q, policy["sizing_map"], missing, policy["q"], policy["beta"])[loc]
                weighting_value = Q["value"][loc]
                weighting_available = Q["available"][loc]
                if not len(raw_requested):
                    desired = raw_requested
                    status = "empty_cash"
                elif raw_requested.sum() <= 0:
                    desired = np.full(len(raw_requested), 1 / len(raw_requested))
                    status = "all_zero_equal"
                elif policy["sizing_map"] == "risk_budget":
                    desired, status, covariance, error = score_risk_budget(data, origin, selected_ids, variances, raw_requested)
                else:
                    desired = raw_requested / raw_requested.sum()
                    status = "score_map"
                target_budget = raw_requested / raw_requested.sum() if raw_requested.sum() > 0 else desired.copy()
            accepted, caps, unknown = project(data, origin, basket, desired, policy["constraints"])
            budget = float(accepted.sum())
            benchmark = bounded_proportional(np.ones(len(accepted)), caps, budget) if len(accepted) else accepted.copy()
            requested_rc = np.full(len(desired), np.nan)
            accepted_rc = requested_rc.copy()
            if covariance is not None:
                requested_rc = desired * (covariance @ desired)
                requested_rc /= requested_rc.sum()
                accepted_rc = accepted * (covariance @ accepted)
                if accepted_rc.sum() > 0:
                    accepted_rc /= accepted_rc.sum()
            chosen = set(selected_ids)
            for i, pid in enumerate(ids):
                candidates.append(dict(origin_at=origin, arm=arm, pair_id=int(pid), ranking_score=float(R["value"][i]), ranking_available=bool(R["available"][i]), selected=bool(pid in chosen)))
            for k, row in enumerate(basket.itertuples()):
                allocations.append(dict(origin_at=origin, arm=arm, pair_id=int(row.pair_id), vault_address=row.vault_address, vault_name=row.vault_name, rank=k + 1, selected=True, ranking_score=float(R["value"][loc[k]]), ranking_available=bool(R["available"][loc[k]]), weighting_score=float(weighting_value[k]), weighting_available=bool(weighting_available[k]), desired_weight=float(desired[k]), accepted_weight=float(accepted[k]), benchmark_weight=float(benchmark[k]), capacity=float(caps[k]), unknown_state=bool(unknown[k]), cash=1 - budget, positive_position=bool(accepted[k] > 0), fallback=status, target_risk_budget=float(target_budget[k]), requested_risk_contribution=float(requested_rc[k]), accepted_risk_contribution=float(accepted_rc[k]), units=float(accepted[k] / data["arrays"]["nav"][data["date_index"][origin - pd.Timedelta(days=1)], data["id_index"][row.pair_id]])))
            if mature:
                panel = future_panel(data, origin, 30, selected_ids)
                metrics = outcome_metrics(panel, accepted, variances)
                base = outcome_metrics(panel, benchmark, variances)
                matched = bool(metrics["resolved"] and base["resolved"])
                lift = metrics["return"] - base["return"] if matched else np.nan
                if metrics["resolved"]:
                    for k, pid in enumerate(selected_ids):
                        if accepted[k] > 0:
                            attribution.append(dict(origin_at=origin, arm=arm, pair_id=int(pid), contribution=float(accepted[k] * panel["returns"][k]), first_update_contribution=float(accepted[k] * panel["first_update"][k]), weight=float(accepted[k])))
                active = accepted - benchmark
                unsupported = ~panel["supported"]
                unknown_coef = active[unsupported]
                known_active = float(np.nansum(active * panel.get("returns", np.zeros(len(active)))))
                lower = -np.inf if (unknown_coef < 0).any() else known_active - float(np.maximum(unknown_coef, 0).sum())
                upper = np.inf if (unknown_coef > 0).any() else known_active + float(np.abs(np.minimum(unknown_coef, 0)).sum())
            else:
                metrics = dict(return_value=np.nan, resolved=False, cash=1 - budget, unresolved_weight=np.nan, variance=np.nan, drawdown=np.nan, sharpe=np.nan, effective_N=float(1 / np.sum((accepted / budget) ** 2)) if budget else 0.0, max_weight=float(accepted.max()) if len(accepted) else 0.0)
                metrics["return"] = np.nan
                base = {"return": np.nan, "variance": np.nan, "resolved": False}
                matched = False
                lift = np.nan
                lower = upper = np.nan
            outcomes.append(dict(origin_at=origin, arm=arm, mature=mature, status="mature" if mature else "pending", selected_count=len(selected_ids), positive_count=int((accepted > 0).sum()), unscored_selected=int((~R["available"][loc]).sum()), unscored_funded=int(((~R["available"][loc]) & (accepted > 0)).sum()), weighting_unavailable=int((~weighting_available).sum()), zero_requested=int((desired == 0).sum()), fallback=status, risk_budget_error=error, requested_effective_N=float(1 / np.sum(desired**2)) if len(desired) else 0.0, distance_equal=float(0.5 * np.abs(desired - 1 / len(desired)).sum()) if len(desired) else 0.0, **metrics, benchmark_return=base["return"], matched_weighting=matched, weighting_lift=lift, variance_lift=metrics["variance"] - base["variance"], contrast_lower=lower, contrast_upper=upper, label_end=origin + pd.Timedelta(days=29), label_available_at=origin + pd.Timedelta(days=30)))
            for role, result in zip(("ranking", "weighting"), evaluated):
                if result is None:
                    continue
                finite = result["available"]
                value = np.where(finite, result["value"], np.nan)
                future_return = all_future["returns"] if mature else np.full(len(ids), np.nan)
                future_sharpe = all_future["sharpe"] if mature else np.full(len(ids), np.nan)
                support = np.isfinite(value) & np.isfinite(future_return)
                ics.append(dict(origin_at=origin, arm=arm, role=role, mature=mature, return_ic=corr(value, future_return), sharpe_ic=corr(value, future_sharpe), support=int(support.sum()), eligible=len(ids), finite_score=int(finite.sum())))
                for component, values in components.items():
                    diagnostics.append(dict(origin_at=origin, arm=arm, role=role, component=component, component_sd=float(np.nanstd(values)) if np.isfinite(values).any() else np.nan, score_component_ic=corr(value, values)))
    result = {k: pd.DataFrame(v) for k, v in dict(allocations=allocations, candidate_ledger=candidates, outcomes=outcomes, scores=scores, score_ic=ics, component_diagnostics=diagnostics, vault_attribution=attribution).items()}
    out = result["outcomes"]
    summaries = []
    for policy in policies:
        g = out[out.arm.eq(policy["arm"])]
        m = g[g.mature]
        ic = result["score_ic"]
        ic = ic[ic.arm.eq(policy["arm"]) & ic.role.eq("ranking") & ic.mature]
        reference = "T14" if policy["arm"] in ("T20", "T21", "T22", "T23", "T25", "T26") else "T02"
        overlap = [len(basket_cache[(t, policy["arm"])] & basket_cache[(t, reference)]) / len(basket_cache[(t, policy["arm"])] | basket_cache[(t, reference)]) if basket_cache[(t, policy["arm"])] | basket_cache[(t, reference)] else 1.0 for t in data["origins"]]
        summaries.append(
            dict(arm=policy["arm"], ranking=label(policy["ranking"]), weighting=label(policy["weighting"]), map=policy["sizing_map"], N=policy["N"], missing=policy["missing"], constraints=policy["constraints"], scheduled=len(g), mature=int(g.mature.sum()), resolved=int(m.resolved.sum()), paired=int(m.matched_weighting.sum()), mean_return=m["return"].mean(), median_return=m["return"].median(), mean_variance=m.variance.mean(), mean_drawdown=m.drawdown.mean(), weighting_lift=m.weighting_lift.mean(), return_ic=ic.return_ic.mean(), ic_origins=int(ic.return_ic.notna().sum()), mean_cash=m.cash.mean(), effective_N=m.effective_N.mean(), positive_count=m.positive_count.mean(), unresolved_weight=m.unresolved_weight.mean(), fallback_fraction=m.fallback.str.contains("fallback|all_zero").mean(), distance_equal=m.distance_equal.mean(), basket_overlap=float(np.mean(overlap)), overlap_reference=reference, unscored_funded=m.unscored_funded.mean(), risk_budget_max_error=m.risk_budget_error.max())
        )
    result["summary"] = pd.DataFrame(summaries)
    result["quarterly"] = out.assign(quarter=out.origin_at.dt.to_period("Q").astype(str)).groupby(["arm", "quarter"]).agg(scheduled=("mature", "size"), mature=("mature", "sum"), resolved=("resolved", "sum"), mean_return=("return", "mean"), mean_cash=("cash", "mean")).reset_index()
    pairs = [("T05", "T02", "Risk sizing recipe"), ("T05", "T27", "Risk versus neutral offset"), ("T27", "T02", "Neutral-offset flattening"), ("T06", "T01", "Risk ranking / equal sizing"), ("T07", "T06", "Risk score sizing / new basket"), ("T14", "T13", "K ranking / same weighting recipe"), ("T14", "T26", "K weighting / same ranking"), ("T10", "T05", "Squared score sizing"), ("T20", "T14", "Ten versus six"), ("T21", "T14", "Neutral versus zero missing"), ("T22", "T14", "Available-component missing"), ("T23", "T14", "K confidence"), ("T25", "T14", "Uncapped versus constrained")]
    contrasts = []
    dates = []
    common_dates = []
    allocation_lookup = {(t, a): g for (t, a), g in result["allocations"].groupby(["origin_at", "arm"])}
    for arm, control, description in pairs:
        x = out[out.arm.eq(arm) & out.mature].merge(out[out.arm.eq(control) & out.mature], on="origin_at", suffixes=("_new", "_base"))
        good = x.resolved_new & x.resolved_base
        effect = x["return_new"] - x["return_base"]
        effect = effect.where(good)
        for i, row in x.iterrows():
            dates.append(dict(origin_at=row.origin_at, arm=arm, control=control, description=description, paired=bool(good.loc[i]), return_difference=float(effect.loc[i]), cash_difference=float(row.cash_new - row.cash_base)))
        common = []
        for row in x.itertuples():
            budgets = []
            panels = []
            weights = []
            gs = [allocation_lookup[(row.origin_at, a)] for a in (arm, control)]
            budget = min(float(g.accepted_weight.sum()) for g in gs)
            for g in gs:
                w = bounded_proportional(g.desired_weight.to_numpy(), g.capacity.to_numpy(), budget)
                target = future_panel(data, row.origin_at, 30, g.pair_id.to_numpy(int))
                metric = outcome_metrics(target, w)
                budgets.append(w.sum())
                panels.append(metric)
                weights.append(w)
            supported = panels[0]["resolved"] and panels[1]["resolved"]
            value = panels[0]["return"] - panels[1]["return"] if supported else np.nan
            common.append(value)
            common_dates.append(dict(origin_at=row.origin_at, arm=arm, control=control, common_budget=budget, new_invested=float(budgets[0]), base_invested=float(budgets[1]), paired=supported, return_difference=value))
        contrasts.append(dict(arm=arm, control=control, description=description, paired=int(good.sum()), return_difference=effect.mean(), cash_difference=(x.cash_new - x.cash_base)[good].mean(), variance_difference=(x.variance_new - x.variance_base)[good].mean(), common_budget_paired=int(np.isfinite(common).sum()), common_budget_difference=float(np.nanmean(common)) if np.isfinite(common).any() else np.nan))
    result["contrasts"] = pd.DataFrame(contrasts)
    result["contrast_dates"] = pd.DataFrame(dates)
    result["common_budget_dates"] = pd.DataFrame(common_dates)
    # Four-cell interaction is evaluated only on the common resolved calendar.
    p = out[out.mature & out.arm.isin(["T01", "T05", "T06", "T07"])].pivot(index="origin_at", columns="arm", values="return").dropna()
    result["four_cell"] = pd.DataFrame([dict(origins=len(p), selection=(p.T06 - p.T01).mean(), sizing=(p.T05 - p.T01).mean(), interaction=(p.T07 - p.T06 - p.T05 + p.T01).mean(), total=(p.T07 - p.T01).mean())])
    influence = []
    for arm, g in out[out.mature].groupby("arm"):
        good = g[g.resolved]
        mean = good["return"].mean()
        for quarter in ("2026Q1", "2026Q2", "2026Q3", "2026Q4"):
            rest = good[good.origin_at.dt.to_period("Q").astype(str).ne(quarter)]
            influence.append(dict(arm=arm, quarter_removed=quarter, origins=len(rest), mean_return=rest["return"].mean(), difference=rest["return"].mean() - mean))
    result["quarter_influence"] = pd.DataFrame(influence)
    attribution_frame = result["vault_attribution"]
    vault = attribution_frame.groupby(["arm", "pair_id"]).agg(total_contribution=("contribution", "sum"), appearances=("contribution", "size"), first_update=("first_update_contribution", "sum")).reset_index()
    counts = out[out.mature & out.resolved].groupby("arm").size()
    vault["mean_return_contribution"] = vault.total_contribution / vault.arm.map(counts)
    vault = vault.merge(data["identities"][["pair_id", "vault_name"]], on="pair_id", validate="many_to_one")
    result["vault_influence"] = vault
    result["robustness"] = out[out.mature].groupby("arm").agg(mean_return=("return", "mean"), median_return=("return", "median"), worst_origin=("return", "min"), best_origin=("return", "max"), median_cash=("cash", "median"), first_update=("first_update", "mean"), remaining=("remaining", "mean"), carried_anchor_weight=("carried_anchor_weight", "mean"), unresolved_weight=("unresolved_weight", "mean")).reset_index()
    proposed = next_stage_registry(data["registry"])
    proposed["smoke_seconds"] = time.monotonic() - started
    (folder / "next-stage-registry.json").write_text(json.dumps(proposed, indent=2))
    for name, frame in result.items():
        frame.to_parquet(folder / f"{name}.parquet", index=False)
    for name, frame in tensors.items():
        frame.to_parquet(folder / f"{name}.parquet", index=False)
    data["execution_seconds"] = time.monotonic() - started
    (folder / "execution.json").write_text(json.dumps(dict(seconds=data["execution_seconds"], policies=36, origins=70, next_stage=proposed["unique_policies"], status="executed_pending_audit"), indent=2))
    return result
