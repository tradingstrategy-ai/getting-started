"""Independent adverse fixtures, warmup reconstruction and source parity."""

import numpy as np
import pandas as pd
from portfolio_score_design import START, END, expression, recipe_id
from portfolio_score_components import percentile, GENERATION
from portfolio_score_recipes import evaluate, sizing_values
from portfolio_score_allocation import score_risk_budget
from portfolio_snapshot_construction import bounded_proportional, fixed_unit_path
from k_ratio_features import window_metrics, k_statistics, forward_fill_nav


def run_fixtures():
    rows = []

    def check(name, passed, detail):
        rows.append(dict(check=name, passed=bool(passed), detail=detail))
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    values = {"S": np.array([0.8, 0.4]), "I": np.array([0.2, 0.9]), "K": np.array([0.6, 0.7])}
    x = expression("A", "S", "I", "K", coefficients=[0.5, 0.25, 0.25])
    q = evaluate(x, values)
    check("Independent composite arithmetic", np.allclose(q["value"], [0.6, 0.6]), "0.5S+0.25I+0.25K gives 0.6 for both vaults")
    # Selected-basket allocation blending gives another answer and violates the fixture.
    bad = 0.5 * values["S"] / values["S"].sum() + 0.25 * values["I"] / values["I"].sum() + 0.25 * values["K"] / values["K"].sum()
    check("Catch separately normalised allocation blend", not np.allclose(bad, [0.5, 0.5]), "The adverse alternative disagrees with equal final Q weights")
    sparse = {"X": np.array([0.8, np.nan, 0.0, np.nan]), "Y": np.array([np.nan, 0.4, 0.0, np.nan])}
    expr = expression("A", "X", "Y")
    zero = evaluate(expr, sparse, "M0")
    neutral = evaluate(expr, sparse, "MN")
    available = evaluate(expr, sparse, "MA")
    check("Missing policies / valid zero", np.allclose(zero["value"], [0.4, 0.2, 0, 0]) and np.allclose(neutral["value"], [0.65, 0.45, 0, 0.5]) and np.allclose(available["value"], [0.8, 0.4, 0, 0]) and zero["available"].tolist() == [True, True, True, False], "M0/MN/MA arithmetic and masks checked independently")
    geo = evaluate(expression("G", "X", "Y"), sparse)
    minimum = evaluate(expression("Min", "X", "Y"), sparse)
    check("Geometric / minimum zeros", np.allclose(geo["value"], 0) and np.allclose(minimum["value"], 0), "Missing-zero and valid-zero remain zeros without epsilon")
    scaled = evaluate(expression("A", "X", "Y", coefficients=[1.0, 0.0]), sparse)
    check("Zero coefficient exclusion", scaled["available"].tolist() == [True, False, True, False], "Unavailable zero-coefficient inputs cannot make an observation scored")
    peer = np.array([0.03, 0.02, 0.09])
    own = np.array([0.02, 0.03, 0.04])
    I = peer / (peer + own)
    V = np.sqrt(peer) / (np.sqrt(peer) + np.sqrt(own))
    check("Peer-relative I/V invariant", np.allclose(percentile(I), percentile(V)) and np.allclose(I, 100 * peer / (100 * peer + 100 * own)), "Same relative-risk order and scale invariance; magnitudes differ")
    check("Midrank ties and singleton", np.allclose(percentile([1, 1, 3]), [1 / 3, 1 / 3, 5 / 6]) and percentile([2])[0] == 0.5, "Independent tie formula")
    soft = sizing_values(dict(value=np.array([0.0, 1.0]), available=np.ones(2, bool)), "softmax")
    check("Sizing odds / power", np.isclose(soft[1] / soft[0], 4) and np.allclose(sizing_values(dict(value=np.array([0.25, 1.0]), available=np.ones(2, bool)), "power", q=0.5), [0.5, 1]), "Full-range softmax 4:1; flattening fixture retained")
    pct = sizing_values(dict(value=np.array([0.2, 0.8, 0.5]), available=np.array([True, True, False])), "percentile", "MN")
    check("Neutral missing percentile", np.allclose(pct, [0.25, 0.75, 0.5]), "Unavailable neutral point is ranked against available reference only")
    cap = bounded_proportional([1.0, 0.0, 0.0], [0.33, 0.33, 0.33], 0.98)
    check("Zero requested names stay unfunded", np.allclose(cap, [0.33, 0, 0]), "One positive name leaves 67% cash; zero names do not receive redistribution")
    p = np.array([[1.0, 2.0], [2.0, 1.0], [3.0, 4.0]])
    check("Fixed-unit path", np.allclose(fixed_unit_path(p, [0.2, 0.3]), [1.0, 1.05, 1.7]), "Hand calculation includes 50% cash and drift")
    carry = forward_fill_nav(np.array([np.nan, 1.0, np.nan, 1.1]))[:, 0]
    check("Sparse fill / no leading backfill", np.isnan(carry[0]) and np.allclose(carry[1:], [1, 1, 1.1]), "Actual count stays two despite three finite calendar marks")
    # Direct OLS using an independent design-matrix solve, not k_statistics twice.
    path = np.exp(np.array([0.0, 0.01, 0.04, 0.02, 0.06, 0.07]))
    n = len(path)
    design = np.column_stack([np.ones(n), np.arange(n)])
    coef = np.linalg.lstsq(design, np.log(path), rcond=None)[0]
    residual = np.log(path) - design @ coef
    se = np.sqrt((residual @ residual) / (n - 2) * np.linalg.inv(design.T @ design)[1, 1])
    expected = coef[1] / se * np.sqrt(365) / n
    check("Independent K OLS", np.isclose(k_statistics(path)["K-ratio"][0], expected, rtol=1e-10), "Intercept OLS and span scaling reconstructed from linear algebra")
    return pd.DataFrame(rows)


def run_audit(data, tensors, result, policies):
    rows = run_fixtures().to_dict("records")

    def check(name, passed, detail):
        rows.append(dict(check=name, passed=bool(passed), detail=detail))
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    # Compare first-origin metrics directly with retained original NAV; future edits cannot enter slice.
    feat = data["features"].set_index(["origin_at", "pair_id"])
    a = data["date_index"][START - pd.Timedelta(days=1)]
    comp = tensors["components"]
    warm_matches = []
    causal = []
    first = comp[comp.origin_at.eq(START)]
    for name, L, metric in [("C30", 30, "CAGR"), ("C360", 360, "CAGR"), ("Sh90", 90, "Sharpe"), ("So180", 180, "Sortino"), ("Ca360", 360, "Calmar")]:
        for pid in first[first.component.eq(name)].pair_id.iloc[::7]:
            j = data["id_index"][int(pid)]
            raw = data["arrays"]["raw_nav"][:, j].copy()
            filled = forward_fill_nav(raw)[:, 0]
            actual = window_metrics(filled[a - L : a + 1])[metric][0]
            cached = feat.loc[(START, pid), f"{L}d {metric}"]
            warm_matches.append(np.isclose(actual, cached, rtol=1e-9, atol=1e-10, equal_nan=True))
            raw[a + 1 :] = 1000000.0
            changed = forward_fill_nav(raw)[:, 0]
            again = window_metrics(changed[a - L : a + 1])[metric][0]
            causal.append(np.isclose(actual, again, equal_nan=True))
    check("2025 warmup / first-origin metric parity", all(warm_matches), "Direct original NAV reconstruction matches NB09 at first 2026 origin")
    check("Future mutation invariance", all(causal), "Changing all post-cutoff NAV cannot change historical metrics")
    # Max-K and confidence counts independently use original daily marks.
    k_matches = []
    for pid in first[first.component.eq("Kmax")].pair_id.iloc[::9]:
        j = data["id_index"][int(pid)]
        f = data["first_index"][j]
        raw = data["arrays"]["raw_nav"][f : a + 1, j]
        expected = k_statistics(raw)["K-ratio"][0]
        record = first[first.component.eq("Kmax") & first.pair_id.eq(pid)].iloc[0]
        k_matches.append(np.isclose(record.raw_value, expected, equal_nan=True) and record.actual_count == np.isfinite(raw[1:]).sum())
    check("Maximum-history K / true update count", all(k_matches), "First recorded anchor retained; forward-filled marks do not increase support")
    out = result["outcomes"]
    ledger = result["allocations"]
    scheduled = out.groupby("arm").size()
    mature = out.groupby("arm").mature.sum()
    check("Full 2026 calendar", scheduled.eq(70).all() and mature.eq(62).all(), "All 36 arms have 70 scheduled / 62 mature / 8 pending origins")
    check("Finite non-negative weights and caps", np.isfinite(ledger[["desired_weight", "accepted_weight"]]).all().all() and ledger.desired_weight.ge(0).all() and ledger.accepted_weight.ge(0).all() and (ledger.accepted_weight <= ledger.capacity + 1e-10).all(), "All allocations checked, including zeros and cap saturation")
    sumweights = ledger.groupby(["origin_at", "arm"]).accepted_weight.sum().rename("invested").reset_index().merge(out[["origin_at", "arm", "cash"]], on=["origin_at", "arm"], validate="one_to_one")
    check("Budget reconciliation", np.allclose(sumweights.invested + sumweights.cash, 1.0, atol=1e-10), "Cash plus accepted weights equals one per origin")
    # Same ranking must select the same basket when only sizing changes.
    lists = ledger.groupby(["origin_at", "arm"]).pair_id.apply(tuple)
    pairs = [("T01", "T02"), ("T02", "T05"), ("T05", "T27"), ("T13", "T24"), ("T14", "T26")]
    check("Ranking / sizing separation", all(lists.loc[(t, x)] == lists.loc[(t, y)] for t in data["origins"] for x, y in pairs), "Matched ranking controls retain identical selected identities")
    # Registry expressions deduplicated before basket choice.
    check("Component-before-selection ledger", not comp.duplicated(["origin_at", "pair_id", "component"]).any() and not result["scores"].duplicated(["origin_at", "pair_id", "recipe_id", "missing"]).any(), "One eligible-universe tensor reused across all N/maps")
    rb = ledger[ledger.arm.eq("T24") & ledger.fallback.str.startswith("score_risk_budget")]
    check("Score risk-budget contributions", len(rb) > 0 and (rb.requested_risk_contribution - rb.target_risk_budget).abs().max() < 1e-5, "Independent contribution ledger check before caps; achieved contributions after caps retained")
    # Equal risk budgets on diagonal covariance have analytic inverse-volatility solution.
    synthetic = dict(nav=pd.DataFrame(index=pd.date_range("2025-10-01", "2026-01-01")), date_index={t: i for i, t in enumerate(pd.date_range("2025-10-01", "2026-01-01"))}, first_index=np.array([90, 90]), id_index={1: 0, 2: 1}, arrays=dict(nav=np.ones((93, 2)), actual=np.zeros((93, 2), bool)))
    w, status, C, error = score_risk_budget(synthetic, START, [1, 2], [0.01, 0.04], [1, 1])
    check("Analytic equal risk budget", np.allclose(w, [2 / 3, 1 / 3], atol=1e-5), "Diagonal equal budgets recover inverse volatility")
    common = result["common_budget_dates"]
    check("Common invested-budget controls", np.allclose(common.new_invested, common.base_invested, atol=1e-10) and np.allclose(common.new_invested, common.common_budget, atol=1e-10), "Both ex-ante allocations are reprojected to identical feasible budgets")
    attributed = result["vault_attribution"].groupby(["origin_at", "arm"]).contribution.sum().rename("contribution").reset_index()
    realised = result["outcomes"]
    match = attributed.merge(realised[realised.mature & realised.resolved][["origin_at", "arm", "return"]], on=["origin_at", "arm"], validate="one_to_one")
    check("Independent vault contribution reconciliation", np.allclose(match.contribution, match["return"], atol=1e-10), "Initial accepted notional times each held NAV return sums to portfolio return")
    # Compare against original saved NB10, using exact per-origin reference ledgers.
    old = GENERATION / "10"
    oldp = pd.read_parquet(old / "policies.parquet")
    oldl = pd.read_parquet(old / "allocations.parquet")
    oldo = pd.read_parquet(old / "outcomes.parquet")
    ref0 = oldp[oldp.score.eq("v11") & oldp.N.eq(6) & oldp.estimator.eq("source") & oldp.variant.eq("source_entry_caps")]
    if ref0.empty:
        ref0 = oldp[oldp.score.eq("v11") & oldp.N.eq(6) & oldp.estimator.eq("source") & oldp.policy_id.str.endswith("source-entry-caps")]
    ref1 = oldp[oldp.score.eq("focal_four") & oldp.N.eq(6) & oldp.estimator.eq("equal") & oldp.state.eq("source_report_only") & oldp.variant.eq("main")]
    parity = []
    for arm, ref in [("T00", ref0), ("T01", ref1)]:
        assert len(ref) == 1, (arm, ref.to_dict("records"))
        pid = ref.iloc[0].policy_id
        oldrows = oldl[oldl.policy_id.eq(pid) & oldl.origin_at.isin(data["origins"])]
        reference_origins = oldrows.origin_at.unique()
        new = ledger[ledger.arm.eq(arm) & ledger.origin_at.isin(reference_origins)]
        compare = new.merge(oldrows, on=["origin_at", "pair_id"], suffixes=("_new", "_old"), validate="one_to_one")
        equal_keys = len(compare) == len(new) == len(oldrows)
        weights = np.allclose(compare.accepted_weight_new, compare.accepted_weight_old, rtol=1e-9, atol=1e-10)
        aout = out[out.arm.eq(arm) & out.mature]
        b = oldo[oldo.policy_id.eq(pid) & oldo.h.eq(30) & oldo.origin_at.isin(data["origins"])]
        c = aout.merge(b, on="origin_at", suffixes=("_new", "_old"), validate="one_to_one")
        economics = len(c) == 62 and np.array_equal(c.resolved_new, c.resolved_old) and np.allclose(c["return_new"], c["return_old"], rtol=1e-9, atol=1e-10, equal_nan=True) and np.allclose(c.cash_new, c.cash_old, rtol=1e-9, atol=1e-10)
        parity.append(dict(arm=arm, reference_policy=pid, weight_rows=len(compare), reference_scheduled_origins=len(reference_origins), origins=len(c), weights_match=weights, economics_match=economics, mean_return=c["return_new"].mean(), mean_cash=c.cash_new.mean()))
        check(arm + " saved NB10 parity", equal_keys and weights and economics, "Exact shared-date identities/weights and all 62 mature returns; new-only pending dates audited separately")
    result["parity"] = pd.DataFrame(parity)
    frame = pd.DataFrame(rows)
    import json

    execution = json.loads((data["artifact"] / "execution.json").read_text())
    execution.update(status="audit_passed", audit_checks=len(frame))
    (data["artifact"] / "execution.json").write_text(json.dumps(execution, indent=2))
    frame.to_csv(data["artifact"] / "audit.csv", index=False)
    result["parity"].to_parquet(data["artifact"] / "parity.parquet", index=False)
    return frame
