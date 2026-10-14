"""Source risk controls under the same declared entry-capacity projection."""

import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
from portfolio_snapshot_data import ARTIFACT, METHODS, sha256, future_panel
from portfolio_snapshot_construction import capacity_limits, bounded_proportional, outcome_metrics, signed_return_bounds


def add_source_capacity_controls(data, risk, result):
    """Reuse ex-ante pure baskets; add source/raw caps without rerunning the core."""
    variant = "source_capacity_control"
    policies = result["policies"]
    existing = policies[policies.variant.eq(variant)].policy_id
    for name in ("allocations", "outcomes", "stability"):
        result[name] = result[name][~result[name].policy_id.isin(existing)].copy()
    policies = policies[~policies.variant.eq(variant)].copy()
    groups = {(t, p): g for (t, p), g in result["allocations"].groupby(["origin_at", "policy_id"])}
    outcomes = result["outcomes"]
    rr = {(t, L): g.set_index("pair_id") for (t, L), g in risk.groupby(["origin_at", "L"])}
    candidates = {(t, m): g.set_index("pair_id") for (t, m), g in data["candidates"].groupby(["origin_at", "method_id"], observed=True)}
    additions = []
    alloc = []
    out = []
    for method in METHODS:
        for est, power in (("raw", 1), ("raw", 2), ("source", 2)):
            base = policies[policies.score.eq(method) & policies.N.eq(6) & policies.L.eq(90) & policies.p.eq(power) & policies.estimator.eq(est) & policies.branch.eq("pure") & policies.variant.eq("main" if est == "raw" else "source_candle_control")].iloc[0].to_dict()
            original = base["policy_id"]
            base.update(branch="capacity", variant=variant, state="source_report_only", redistribute=True)
            base["policy_id"] = original + "|source-entry-caps"
            additions.append(base)
            policy = SimpleNamespace(**base)
            for template in outcomes[outcomes.policy_id.eq(original) & outcomes.phase.eq(0)].itertuples(index=False, name=None):
                row = dict(zip(outcomes.columns, template))
                t = row["origin_at"]
                h = row["h"]
                g = groups.get((t, original), result["allocations"].iloc[:0])
                ids = g.pair_id.to_numpy()
                w0 = g.desired_weight.to_numpy()
                basket = candidates.get((t, method), data["candidates"].iloc[:0].set_index("pair_id")).reindex(ids).reset_index()
                caps, unknown = capacity_limits(data, t, basket, policy)
                w = bounded_proportional(w0, caps, 0.98)
                benchmark = bounded_proportional(np.ones(len(ids)), caps, w.sum())
                v = rr[(t, 90)].reindex(ids)[est].to_numpy() if len(ids) else np.array([])
                panel = future_panel(data, t, h, ids)
                metrics = outcome_metrics(panel, w, v)
                equal = outcome_metrics(panel, benchmark, v)
                lo, hi = signed_return_bounds(w - benchmark, panel["returns"], panel["supported"])
                first = metrics["first_update"] - equal["first_update"]
                remaining = metrics["remaining"] - equal["remaining"]
                lift = metrics["return"] - equal["return"]
                assert not np.isfinite(first) or np.isclose(first + remaining, lift, atol=1e-10)
                coef = float((w - benchmark)[~panel["supported"]].sum())
                known = float(np.nansum((w - benchmark) * panel["returns"]))
                row.update(policy_id=policy.policy_id, **metrics, weighting_lift=lift, variance_lift=metrics["variance"] - equal["variance"], drawdown_lift=metrics["drawdown"] - equal["drawdown"], benchmark_return=equal["return"], benchmark_variance=equal["variance"], first_update_lift=first, remaining_lift=remaining, selection_lift=np.nan, total_lift=np.nan, missing_active_coefficient=coef, known_active_contribution=known, break_even_missing_return=-known / coef if coef else np.nan, contrast_lower=lo, contrast_upper=hi)
                out.append(row)
                if h == 7:  # One allocation ledger row per origin/policy, independent of outcome horizon.
                    for i, original_row in enumerate(g.to_dict("records")):
                        original_row.update(policy_id=policy.policy_id, accepted_weight=w[i], benchmark_weight=benchmark[i], cash=1 - w.sum(), capacity=caps[i], unknown_state=unknown[i], units=original_row["units"] * w[i] / w0[i] if w0[i] > 0 else 0)
                        alloc.append(original_row)
    result["policies"] = pd.concat([policies, pd.DataFrame(additions)], ignore_index=True)
    result["allocations"] = pd.concat([result["allocations"], pd.DataFrame(alloc)], ignore_index=True)
    result["outcomes"] = pd.concat([result["outcomes"], pd.DataFrame(out)], ignore_index=True)
    for name in ("policies", "allocations", "outcomes"):
        result[name].to_parquet(ARTIFACT / f"{name}.parquet", index=False)
    (ARTIFACT / "source-capacity-controls.json").write_text(json.dumps({"module_sha256": sha256(__file__), "policies": len(additions), "outcomes": len(out), "purpose": "Source/raw requested risk weights under source-report-only stateless entry caps"}, indent=2))
    return result
