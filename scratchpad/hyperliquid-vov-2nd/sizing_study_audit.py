"""Independent mathematics, historical controls and temporal invariance checks."""

import json
import numpy as np
import pandas as pd
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast, qlike_difference
from portfolio_snapshot_construction import risk_weights, bounded_proportional, fixed_unit_path, outcome_metrics, signed_return_bounds
from portfolio_snapshot_data import future_panel
from sizing_study_design import GENERATION, REFERENCE, START, END, main_registry, smoke_registry, followups, primary_pairs
from sizing_study_data import sparse_window
from sizing_study_allocation import allocate, requested


def fixtures():
    rows = []

    def check(name, condition, description):
        assert bool(condition), name
        rows.append(dict(check=name, passed=True, description=description))

    x = empirical_window([np.nan, 100, 110, 110, 121], [False, True, True, False, True], 4)
    check("Partial and sparse simple variance", x["n"] == 3 and x["m"] == 2 and not x["full"] and np.isclose(x["empirical"], 0.01 / 3), "Three elapsed returns [0.1,0,0.1], two actual updates, ddof1")
    flat = empirical_window([100, 100, 100], [True, False, True], 2)
    missing = empirical_window([100, 100, 100], [True, False, False], 2)
    check("Flat versus unavailable", flat["empirical"] == 0 and np.isnan(missing["empirical"]), "An actual update is needed; filled zeros alone are insufficient")
    prior = peer_prior(np.array([999.0, 1.0, 3.0, 0.0, np.nan]), np.array([True, True, False, True, True]), 0)
    check("Positive leave-one-out full prior", prior[0] == 1 and prior[1] == 1 and prior[2] == "full", "Self, flat and missing excluded; complete pool preferred")
    check("Fixed shrinkage and prior-only fallback", np.isclose(forecast(4, 1, 30, "regularised", 30), 2.5) and forecast(np.nan, 1, 30, "regularised", 30) == 1, "Thirty real updates gives half empirical weight; missing gives none")
    check("Inherited kappa companion", np.isclose(forecast(4, 1, 30, "regularised", 60), 2), "L180 inherited strength differs from core kappa30")
    check("Raw floor asymmetry", forecast(0, 1e-12, 30, "raw", 30) == 1e-8 and forecast(0, 1e-12, 30, "regularised", 30) < 1e-8, "Regularised estimator has no raw variance floor")
    check("Log-space allocation power", np.allclose(risk_weights([1, 4], 1), [2 / 3, 1 / 3]) and np.allclose(risk_weights([1, 4], 2), [0.8, 0.2]), "Inverse volatility and variance odds calculated independently")
    check("Whole-basket equal fallback", np.allclose(risk_weights([1, np.nan, 4], 2), np.ones(3) / 3), "Unavailable risk retains every selected name")
    w = bounded_proportional([0.8, 0.2, 0], [0.2, 0.9, 0.9], 0.98)
    check("Zero-request preserving cap projection", np.allclose(w, [0.2, 0.78, 0]), "Cap redistributes only to positive requests and conserves budget")
    prices = np.array([[100, 100], [110, 90], [120, 100]])
    check("Fixed-unit arithmetic", np.allclose(fixed_unit_path(prices, [0.6, 0.3]), [1, 1.03, 1.12]), "Cash0.1 plus initial units, no daily rebalancing")
    bounds = signed_return_bounds([0.2, -0.1], [np.nan, 0.5], [False, True])
    opposite = signed_return_bounds([-0.2, 0.1], [np.nan, 0.5], [False, True])
    check("Signed unresolved bounds", np.isclose(bounds[0], -0.25) and np.isposinf(bounds[1]) and np.isneginf(opposite[0]) and np.isclose(opposite[1], 0.25), "No survivor renormalisation; non-negative NAV only")
    logs = np.array([0, 0.1, 0.05, 0.15])
    sp = sparse_window(np.exp(logs), 3)
    check("Daily-spacing log estimator identity", np.isclose(sp["calendar"], np.var(np.diff(logs), ddof=1)) and np.isclose(sp["calendar"], sp["gap"]), "Gap estimator reduces to sample log variance at one-day spacing")
    sp = sparse_window([100, np.nan, 100 * np.exp(0.2), np.nan, np.nan, 100 * np.exp(0.5)], 5)
    check("Gap-scaled drift centring", np.isclose(sp["gap"], 0, atol=1e-28) and sp["m"] == 2 and sp["n"] == 5, "Constant0.1/day drift across gaps2 and3 has zero model residual variance")
    check("Sparse support and no invented endpoint", np.isnan(sparse_window([100, np.nan, 110, np.nan], 3)["gap"]) and not sparse_window([100, 110, 120, np.nan], 3)["full"], "At least two complete intervals; trailing fill does not create a final mark")
    check("QLIKE permits zero realised risk", np.isclose(float(qlike_difference(2, 1, 0)), np.log(2)), "Zero future variance is valid")
    policies = main_registry()
    f = followups()
    check("Frozen stage and contrast counts", len(policies) == 40 and len(smoke_registry()) == 18 and len(primary_pairs(policies)) == 17 and len(f["sensitivities"]) == 12 and len(f["cap_aware"]) == 8, "No duplicate equal policies; follow-ups registered only")
    # Aggregate forecasts before sizing, which differs from mixing normalised portfolios.
    v = np.array([[1, 100, 4], [4, 1, 100.0]])
    check("Median forecast before weights", np.allclose(risk_weights(np.median(v, axis=1), 2), [0.5, 0.5]) and not np.allclose(np.mean([risk_weights(v[:, j], 2) for j in range(3)], axis=0), [0.5, 0.5]), "Independent multi-window toy calculation")
    return pd.DataFrame(rows)


def audit(data, result, policies, horizons, reuse=None):
    rows = []
    parity = []

    def check(name, condition, description):
        assert bool(condition), name
        rows.append(dict(check=name, passed=True, description=description))

    a = result["allocations"]
    o = result["outcomes"]
    r = result["risk"]
    b = result["baskets"]
    check("Complete origin-policy and horizon grid", a.groupby(["arm", "origin_at"]).ngroups == len(policies) * 70 and len(o) == len(policies) * 70 * len(horizons), "Every scheduled origin retained; one shared allocation across horizons")
    for h in horizons:
        expected = {7: 68, 30: 62, 90: 47}[h]
        check(f"{h}-day maturity", o[o.h == h].groupby("arm").mature.sum().eq(expected).all(), f"{expected} mature before vault-specific support")
    check("Unique allocation and risk keys", not a.duplicated(["origin_at", "arm", "pair_id"]).any() and not r.duplicated(["origin_at", "pair_id", "estimator", "L", "kappa"]).any(), "No repeated forecast counts across powers/transforms")
    check("Budget and capacity conservation", (a.accepted_weight >= 0).all() and (a.accepted_weight <= a.capacity + 1e-10).all() and a.groupby(["arm", "origin_at"]).accepted_weight.sum().le(0.98 + 1e-10).all(), "Accepted weights non-negative and inside exact source-report-only caps")
    check("Units and shadow consistency", np.allclose(a.shadow_weight, a.desired_weight * (1 - a.cash)) and (a[(a.desired_weight == 0)].accepted_weight == 0).all(), "Same-budget shadow is a mechanical diagnostic only")
    keys = ["origin_at", "pair_id"]
    pairs = [("S02", "S04"), ("S01", "S03")]
    for left, right in pairs:
        x = a[a.arm == left]
        y = a[a.arm == right]
        z = x.merge(y, on=keys, validate="one_to_one")
        check(f"{left}/{right} identical basket", len(z) == len(x) == len(y), "Risk sizing cannot alter frozen selection")
    check("Frozen baskets across all policies", all(len(a[(a.arm == p["arm"])].merge(b[b.selector == p["selector"]], on=keys)) == len(a[a.arm == p["arm"]]) for p in policies), "Selection and tie-breaking identical across every sizing method")
    mature = o[o.mature & ~o.resolved]
    check("Unresolved returns are not fabricated", mature["return"].isna().all() and o[~o.mature]["return"].isna().all(), "Pending and terminal-unsupported capital is never zero-filled")
    check("NAV mapping and retained warmup", data["raw_mapping_checks"] > 0 and data["daily"].date.min() < pd.Timestamp("2025-01-01"), "Raw archive positive marks match audited NB08 source observations")
    # Saved controls independent of the new implementation.
    olda = pd.read_parquet(REFERENCE / "allocations.parquet")
    oldo = pd.read_parquet(REFERENCE / "outcomes.parquet")
    for arm, reference_arm in [("S01", "T01"), ("S14", "T00"), ("S11", "T03"), ("S16", "T18")]:
        x = a[a.arm == arm]
        y = olda[olda.arm == reference_arm]
        z = x.merge(y, on=keys, suffixes=("_new", "_old"), validate="one_to_one")
        weights = len(z) == len(x) == len(y) and np.allclose(z.desired_weight_new, z.desired_weight_old, atol=1e-10, rtol=1e-9) and np.allclose(z.accepted_weight_new, z.accepted_weight_old, atol=1e-10, rtol=1e-9)
        p = o[(o.arm == arm) & (o.h == 30) & o.mature].merge(oldo[(oldo.arm == reference_arm) & oldo.mature], on="origin_at", suffixes=("_new", "_old"), validate="one_to_one")
        economics = len(p) == 62 and np.array_equal(p.resolved_new, p.resolved_old) and all(np.allclose(p[k + "_new"], p[k + "_old"], atol=1e-10, rtol=1e-9, equal_nan=True) for k in ("variance", "drawdown")) and np.allclose(p["return_new"], p["return_old"], atol=1e-10, rtol=1e-9, equal_nan=True) and np.allclose(p.cash_new, p.cash_old, atol=1e-10)
        check(f"{arm} expanded NB10 parity", weights and economics, "Exact desired/accepted weights and 62 mature outcomes on unchanged inputs")
        parity.append(dict(arm=arm, reference=reference_arm, reference_origins=y.origin_at.nunique(), new_origins=x.origin_at.nunique(), outcomes=len(p), weights_match=weights, outcomes_match=economics, mean_return=p["return_new"].mean()))
    oldp = pd.read_parquet(GENERATION / "10/policies.parquet")
    legacy_a = pd.read_parquet(GENERATION / "10/allocations.parquet")
    legacy_o = pd.read_parquet(GENERATION / "10/outcomes.parquet")
    ref = oldp[(oldp.score == "focal_four") & (oldp.N == 6) & (oldp.L == 90) & (oldp.p == 2) & (oldp.estimator == "regularised") & (oldp.state == "source_report_only") & (oldp.variant == "main")]
    assert len(ref) == 1
    pid = ref.policy_id.iloc[0]
    y = legacy_a[(legacy_a.policy_id == pid) & legacy_a.origin_at.isin(data["origins"])]
    x = a[(a.arm == "S03") & a.origin_at.isin(y.origin_at)]
    z = x.merge(y, on=keys, suffixes=("_new", "_old"), validate="one_to_one")
    p = o[(o.arm == "S03") & (o.h == 30) & o.mature].merge(legacy_o[(legacy_o.policy_id == pid) & (legacy_o.h == 30)], on="origin_at", suffixes=("_new", "_old"))
    exact = len(z) == len(x) == len(y) and np.allclose(z.accepted_weight_new, z.accepted_weight_old, atol=1e-10, rtol=1e-9) and len(p) == 62 and np.allclose(p["return_new"], p["return_old"], atol=1e-10, equal_nan=True)
    check("S03 original regularised inverse-variance parity", exact, "Exact saved original NB10 benchmark, not rounded reported numbers")
    parity.append(dict(arm="S03", reference=pid, reference_origins=y.origin_at.nunique(), new_origins=70, outcomes=len(p), weights_match=exact, outcomes_match=exact, mean_return=p["return_new"].mean()))
    # Direct scalar calculation of first-origin risk from causal raw archive arrays.
    t = data["origins"][0]
    ai = data["date_index"][t - pd.Timedelta(days=1)]
    first = r[(r.origin_at == t) & (r.estimator == "regular") & (r.L == 90) & (r.kappa == 30)]
    matches = []
    for row in first.itertuples():
        j = data["id_index"][row.pair_id]
        path = data["arrays"]["nav"][ai - 90 : ai + 1, j]
        good = np.flatnonzero(np.isfinite(path))
        updates = data["arrays"]["actual"][ai - 90 : ai + 1, j]
        scalar = np.nan
        if len(good):
            pp = path[good[0] :]
            changes = [pp[k] / pp[k - 1] - 1 for k in range(1, len(pp))]
            if len(changes) >= 2 and updates[good[0] + 1 :].any():
                scalar = sum((x - np.mean(changes)) ** 2 for x in changes) / (len(changes) - 1)
        matches.append(np.isclose(scalar, row.empirical, atol=1e-14, equal_nan=True))
    check("Independent first-origin sample variance", all(matches), "L+1 prices, L returns, causal fill and scalar ddof1 arithmetic")
    # Perturb every NAV/source/state observation after T-1. It must not enter the first allocation.
    copied = dict(data)
    copied["arrays"] = {k: v.copy() for k, v in data["arrays"].items()}
    copied["prices"] = data["prices"].copy()
    copied["_tvl_state_cache"] = {}
    for key in ("nav", "source", "raw_nav"):
        copied["arrays"][key][ai + 1 :] *= 123
    copied["prices"].loc[copied["prices"].date > t - pd.Timedelta(days=1), "total_assets"] = 0
    for p in policies:
        basket = b[(b.origin_at == t) & (b.selector == p["selector"])].sort_values("rank")
        ids = basket.pair_id.to_numpy(int)
        comp = data["components"][data["components"].origin_at == t].pivot(index="pair_id", columns="component", values="value").reindex(ids)
        before = allocate(data, t, basket, p, r[r.origin_at == t], comp)
        after = allocate(copied, t, basket, p, r[r.origin_at == t], comp)
        assert np.allclose(before["accepted"], after["accepted"])
    check("Future NAV/source/state mutation invariant", True, "Post-cutoff archive mutation leaves allocations unchanged; no forward support controls selection")
    active = result["vault_attribution"].groupby(["origin_at", "arm", "h"]).contribution.sum().reset_index()
    match = active.merge(o, on=["origin_at", "arm", "h"])
    check("Vault contribution reconciliation", np.allclose(match.contribution, match["return"], atol=1e-10), "Fixed initial capital contributions sum to each resolved portfolio return")
    check("Non-negative decision-time observation ages", r.anchor_age.dropna().ge(0).all(), "Age is measured from decision T to last actual intraday mark, not anchor midnight")
    dates = result["contrast_dates"]
    ca = result["contrast_attribution"].groupby(["origin_at", "arm", "control", "h"]).contribution.sum().reset_index()
    cm = ca.merge(dates, on=["origin_at", "arm", "control", "h"])
    check("Paired vault effect reconciliation", np.allclose(cm.contribution, cm.return_difference, atol=1e-10), "Signed accepted-weight differences times vault returns sum to matched portfolio effects")
    check("Common-budget effect reconciliation", np.allclose(dates.loc[dates.paired, "common_budget_difference"], dates.loc[dates.paired, "return_difference"], atol=1e-10), "All registered methods invest the same total capital within each frozen selector; explicit reprojection agrees")
    check("First-post-anchor contribution partition", np.allclose(o.loc[o.mature & o.resolved, "first_update"] + o.loc[o.mature & o.resolved, "remaining"], o.loc[o.mature & o.resolved, "return"], atol=1e-10), "First update excludes the initial anchor mark; no future updates means zero NAV change")
    if reuse is not None:
        z = a.merge(reuse["allocations"], on=["origin_at", "arm", "pair_id"], suffixes=("_main", "_smoke"))
        check("Main reuses all smoke allocations", len(z) == len(reuse["allocations"]) and np.allclose(z.accepted_weight_main, z.accepted_weight_smoke), "Smoke reused without return-based screening")
    if len(policies) == 40:
        check("Primary frozen family", len(result["contrasts"].query('h==30 and family=="primary"')) == 17, "51 outcome statistics remain descriptive because 30-day complete-block count is below ten")
    frame = pd.DataFrame(rows)
    result["parity"] = pd.DataFrame(parity)
    frame.to_parquet(data["artifact"] / "audit.parquet", index=False)
    result["parity"].to_parquet(data["artifact"] / "parity.parquet", index=False)
    status = json.loads((data["artifact"] / "execution.json").read_text())
    status.update(status="audit_passed", audit_checks=len(frame))
    (data["artifact"] / "execution.json").write_text(json.dumps(status, indent=2))
    return frame
