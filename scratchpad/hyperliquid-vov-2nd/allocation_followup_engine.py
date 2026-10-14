"""Full source-engine replay of the frozen NB12 exploratory shortlist."""

import datetime
import hashlib
import json
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pandas as pd
from scipy.stats import kurtosis
from tradeexecutor.strategy.alpha_model import AlphaModel, TradingPairSignalFlags
from allocation_followup import ROOT, GENERATION, PERIOD, risk_at, cap_allocate, registry
from sizing_study_data import sparse_window
from portfolio_snapshot_risk import peer_prior, forecast
from portfolio_snapshot_construction import bounded_proportional
from sizing_study_allocation import requested
from portfolio_score_components import percentile
from accepted_dollar_cap import calculate_position_profit_curves
from score_matrix import MatrixIndicators, FEATURES


def components_at(data, t, ids):
    """Use pre-decision NB09 features and eligible-universe transformations."""
    e = data["eligibility"]
    pool = np.unique(np.r_[e.loc[e.origin_at.eq(t) & e.eligible_as_of_origin, "pair_id"].to_numpy(int), np.asarray(ids, int)])
    f = data["engine_features"].reindex(pd.MultiIndex.from_product([[t], pool], names=["origin_at", "pair_id"]))
    r = risk_at(data, t, pool, 180, 60).set_index("pair_id").reindex(pool)
    k = f["max K-ratio"].to_numpy(float)
    valid = np.isfinite(k)
    scale = np.median(np.abs(k[valid & (k != 0)])) if np.any(valid & (k != 0)) else np.nan
    ks = np.full(len(k), np.nan)
    ks[valid] = 0.5 + np.arctan(k[valid] / scale) / np.pi if np.isfinite(scale) else 0.5
    c = pd.DataFrame({"Sh90": percentile(f["90d Sharpe"].to_numpy(float)), "Ca180": percentile(f["180d Calmar"].to_numpy(float)), "V180": np.sqrt(r.prior.to_numpy()) / (np.sqrt(r.predicted.to_numpy()) + np.sqrt(r.prior.to_numpy())), "Kmax": ks}, index=pool)
    return c.reindex(ids)


def sparse_risk_at(data, t, ids):
    """Matched calendar/gap estimators on the expanded two-day calendar."""
    a = data["date_index"][t - pd.Timedelta(days=1)]
    e = data["eligibility"]
    pool = np.unique(np.r_[e.loc[e.origin_at.eq(t) & e.eligible_as_of_origin, "pair_id"].to_numpy(int), np.asarray(ids, int)])
    jj = [data["id_index"][int(pid)] for pid in pool]
    values = [sparse_window(data["arrays"]["raw_nav"][a - 90 : a + 1, j]) for j in jj]
    emp = np.array([r["calendar"] for r in values])
    full = np.array([r["full"] for r in values])
    rows = []
    for i, (pid, r) in enumerate(zip(pool, values)):
        prior, _, _, _ = peer_prior(emp, full, i)
        for name in ("calendar", "gap"):
            rows.append(dict(pair_id=int(pid), estimator=name + "_log", L=90, kappa=30, predicted=forecast(r[name], prior, r["m"], "regularised", 30), prior=prior))
    return pd.DataFrame(rows)


def policy_weights(data, t, ids, p):
    """Calculate weights on the actual source-selected identities this cycle."""
    if p["method"].startswith("cap_"):
        return np.ones(len(ids)) / len(ids), risk_at(data, t, ids).set_index("pair_id").reindex(ids).predicted.to_numpy()
    if p["method"] in ("calendar_log", "gap_log"):
        risk = sparse_risk_at(data, t, ids)
    else:
        risk = risk_at(data, t, ids, p["L"], p["kappa"], p.get("floor") or 1e-8, p["method"] if p["method"] == "raw" else "regular")
    comp = components_at(data, t, ids) if p["method"] == "T18" else pd.DataFrame(index=ids)
    return requested(p, risk, comp)[:2]


class AllocationAlphaModel(AlphaModel):
    """Apply paired simultaneous targets within actual engine size-risk limits."""

    def __init__(self, *args, data, policy, scores, ledger, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.policy = policy
        self.scores = scores
        self.ledger = ledger

    def _normalise_weights_size_risk_positions(self, max_positions, max_weight=1.0, investable_equity=None, size_risk_model=None, epsilon_usd=5.0, max_weight_function=None):
        budget = float(investable_equity)
        signals = [s for s in self._get_allocatable_signals() if float(s.raw_weight) > 0]
        t = pd.Timestamp(self.timestamp)
        ids = np.array([s.pair.internal_id for s in signals], int)
        if not len(ids) or budget <= 0:
            self.investable_equity = budget
            self.accepted_investable_equity = 0.0
            self.size_risk_discarded_value = budget
            return
        caps = []
        for s in signals:
            limit = max_weight_function(s) if max_weight_function else max_weight
            limit = max_weight if limit is None else limit
            cap = float(size_risk_model.get_acceptable_size_for_position(self.timestamp, s.pair, float(limit * budget)).accepted_size) / budget
            caps.append(cap)
        caps = np.array(caps)
        p = self.policy
        u, v = policy_weights(self.data, t, ids, p)
        status = "research_weighting"
        if p["method"].startswith("cap_"):
            # Fractions are relative to the live deployable budget, already reduced by allocation_pct.
            # Use the identical frozen .98 convention only in the snapshot; engine fraction budget is1.
            original_caps = caps * 0.98
            projected, new, u, diag = cap_allocate(self.data, t, ids, v, [self.scores.get(int(pid), 0.0) for pid in ids], original_caps, p["target"])
            w = (new if p["method"] == "cap_constrained_convex" else projected) * (0.98**-1)
            status = diag["status"]
            self.data["engine_solver_diagnostics"].append(dict(arm=p["arm"], origin_at=t, **diag))
        else:
            w = bounded_proportional(u, caps, 1.0)
        accepted = float(w.sum() * budget)
        self.investable_equity = budget
        self.accepted_investable_equity = accepted
        self.size_risk_discarded_value = budget - accepted
        for i, s in enumerate(signals):
            target = float(w[i] * budget)
            sr = size_risk_model.get_acceptable_size_for_position(self.timestamp, s.pair, target)
            assert target <= float(sr.accepted_size) + 1e-6 and w[i] <= caps[i] + 1e-9, (p["arm"], t, ids[i], target, float(sr.accepted_size), w[i], caps[i])
            s.position_size_risk = sr
            s.position_target = target
            s.normalised_weight = target / accepted if accepted else 0.0
            if abs(w[i] - caps[i]) < 1e-9:
                s.flags.add(TradingPairSignalFlags.capped_by_pool_size)
            self.ledger.append(dict(Date=t, Arm=p["arm"], pair_id=int(ids[i]), vault=s.pair.get_vault_name(), desired_weight=float(u[i]), accepted_weight=float(w[i]), capacity=float(caps[i]), budget_usd=budget, target_usd=target, old_value=float(s.old_value), score=self.scores.get(int(ids[i]), np.nan), status=status))
        for s in self.signals.values():
            if s.pair.internal_id not in ids and not s.carry_forward_position:
                s.position_target = 0.0
                s.normalised_weight = 0.0


def decision_factory(strategy, panel, values, p, data, ledger):
    """Keep source selection and trade generation; replace only research sizing."""
    source = strategy.decide_trades

    def decide(input):
        old_compute = strategy.compute_sizing_weights
        old_factory = strategy.AlphaModel
        t = pd.Timestamp(input.timestamp)
        scores = {}

        def weights(selected_pair_ids, inv_vol_by_id, signal_by_id, **kwargs):
            scores.update(signal_by_id)
            u, _ = policy_weights(data, t, selected_pair_ids, p)
            # AlphaModel does not retain zero signals; reserve positive placeholders until allocation.
            return {pid: float(max(value, 1e-12)) for pid, value in zip(selected_pair_ids, u)}

        def factory(*args, **kwargs):
            return AllocationAlphaModel(*args, data=data, policy=p, scores=scores, ledger=ledger, **kwargs)

        strategy.compute_sizing_weights = weights
        strategy.AlphaModel = factory
        try:
            return source(replace(input, indicators=MatrixIndicators(input.indicators, panel, values, t)))
        finally:
            strategy.compute_sizing_weights = old_compute
            strategy.AlphaModel = old_factory

    return decide


def run_shortlist(data, result, policies):
    """Freeze shortlist before observing executable outcomes; run serially."""
    from precompute_repaired_singletons import create_evaluator
    from score_forecast_data import _eligibility, method_values
    from tqdm_loggable.auto import tqdm
    import score_matrix

    fixed = ["S01", "S02", "S03", "S04", "S15", "S16", "S17", "S18", "C01", "C02", "C05", "C06"]
    ss = result["summary"].query('h == 30 and arm.str.startswith("X")', engine="python")
    chosen = [ss[ss.selector == s].sort_values(["mean_return", "arm"], ascending=[False, True]).iloc[0].arm for s in ("F", "L")]
    lookup = {p["arm"]: p for p in policies}
    shortlist = [lookup[a] for a in fixed + chosen]
    (data["artifact"] / "engine-shortlist.json").write_text(json.dumps(dict(arms=fixed + chosen + ["source_focal", "source_v11"], selection_rule="Eight benchmark/mechanism controls, four equal-risk paired cap methods, best mean30-day registered sensitivity per selector, unchanged source v11", historical_search=True), indent=2))
    evaluator, parameters, _, fingerprint = create_evaluator(private_label="nb12")
    data["engine_features"] = pd.read_parquet(GENERATION / "09/features.parquet", filters=[("origin_at", ">=", pd.Timestamp("2026-01-01"))]).set_index(["origin_at", "pair_id"])
    origins = pd.date_range("2026-01-01", "2026-10-04", freq="2D")
    data["eligibility"] = _eligibility(evaluator, origins, data["prices"])
    data["engine_solver_diagnostics"] = []
    rows = {r["method_id"]: r for r in data["registry"] if r["method_id"] in ("focal_four", "v11")}
    score_values = {s: method_values(evaluator.panel, rows[m])[0] for s, m in [("F", "focal_four"), ("L", "v11")]}
    # Check the two-day extension against frozen score observations, including NaN masks.
    frozen = data["frozen_scores"]
    for s, m in [("F", "focal_four"), ("L", "v11")]:
        g = frozen[frozen.method_id.eq(m)]
        computed = np.array([score_values[s][evaluator.panel.date_index[r.origin_at], evaluator.panel.pair_index[r.pair_id]] for r in g.itertuples()])
        assert np.allclose(computed, g.score.to_numpy(), atol=1e-12, rtol=0, equal_nan=True)
    evaluator.folder = data["artifact"] / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    data["engine_fingerprint"] = fingerprint
    original_factory = score_matrix.make_matrix_decision
    original_values = evaluator.panel.score_values
    runs = {}
    records = []
    weight = np.zeros(len(FEATURES))
    weight[0] = 1.0
    try:
        for p in tqdm(shortlist, desc="NB12 14 research engine replays; estimated three–eight minutes", mininterval=15):
            values = score_values[p["selector"]]
            evaluator.panel.score_values = lambda *args, **kwargs: values
            score_matrix.make_matrix_decision = lambda strategy, panel, values, sizing, allocator, ledger, **kwargs: decision_factory(strategy, panel, values, p, data, ledger)
            run = evaluator.run(weight, datetime.datetime(2026, 1, 1), datetime.datetime(2026, 10, 5), n=6, sizing="inverse_variance", missing=True, profile=p["arm"], keep=True)
            runs[p["arm"]] = run
            records.append(dict(Arm=p["arm"], Method=p["label"], Selector=p["selector"], **run["metrics"]))
        score_matrix.make_matrix_decision = original_factory
        evaluator.panel.score_values = lambda *args, **kwargs: score_values["F"]
        run = evaluator.run(weight, datetime.datetime(2026, 1, 1), datetime.datetime(2026, 10, 5), n=6, sizing="inverse_variance", missing=True, profile="source_focal", keep=True)
        runs["source_focal"] = run
        records.append(dict(Arm="source_focal", Method="Focal score / original source sizing and allocator", Selector="F", **run["metrics"]))
        run = evaluator.run(weight, datetime.datetime(2026, 1, 1), datetime.datetime(2026, 10, 5), n=6, keep=True, source_control=True)
        runs["source_v11"] = run
        records.append(dict(Arm="source_v11", Method="Unchanged v11 source", Selector="L", **run["metrics"]))
    finally:
        score_matrix.make_matrix_decision = original_factory
        evaluator.panel.score_values = original_values
    frame = pd.DataFrame(records)
    frame.to_parquet(data["artifact"] / "engine_summary.parquet", index=False)
    robust = []
    vaults = []
    positions = []
    for arm, run in runs.items():
        equity = run["equity"].resample("1D").last().ffill()
        daily = equity.pct_change(fill_method=None).fillna(0)
        curves, meta = calculate_position_profit_curves(run["result"].state, equity.index)
        aggregate = curves.sum(axis=1)
        residual = float(aggregate.iloc[-1] - (equity.iloc[-1] - 150000))
        totals = meta.groupby("Vault")["Final profit (USD)"].sum().sort_values(ascending=False)
        positive = totals[totals > 0]
        robust.append(dict(Arm=arm, **{"Best day": daily.max(), "Worst day": daily.min(), "Best day date": str(daily.idxmax().date()), "Excess kurtosis": float(kurtosis(daily, fisher=True)), "Top positive vault": totals.index[0], "Top positive vault share": float(positive.iloc[0] / positive.sum()) if len(positive) else np.nan, "PnL residual (USD)": residual}))
        meta["Arm"] = arm
        positions.append(meta)
        for name, pnl in totals.items():
            vaults.append(dict(Arm=arm, Vault=name, PnL=pnl))
        curves.index.name = "date"
        curves.to_parquet(data["artifact"] / "engine" / f"{arm}-position-curves.parquet")
    robust = pd.DataFrame(robust)
    robust.to_parquet(data["artifact"] / "engine_robustness.parquet", index=False)
    pd.DataFrame(vaults).to_parquet(data["artifact"] / "engine_vault_attribution.parquet", index=False)
    pd.concat(positions).to_parquet(data["artifact"] / "engine_position_attribution.parquet", index=False)
    if data["engine_solver_diagnostics"] or (data["artifact"] / "engine_solver_diagnostics.parquet").exists():
        sd = pd.DataFrame(data["engine_solver_diagnostics"]) if data["engine_solver_diagnostics"] else pd.read_parquet(data["artifact"] / "engine_solver_diagnostics.parquet")
        sd.to_parquet(data["artifact"] / "engine_solver_diagnostics.parquet", index=False)
        assert not sd.status.str.contains("failed").any(), sd[sd.status.str.contains("failed")]
    assert len(frame) == 16 and frame["Maximum vaults held"].max() <= 6
    assert np.abs(robust["PnL residual (USD)"]).max() < 1.0, robust[["Arm", "PnL residual (USD)"]]
    (data["artifact"] / "engine-complete.json").write_text(json.dumps(dict(status="complete", runs=16, shortlist=chosen, fingerprint=fingerprint, nav_fills="source engine NAV timing", research_projection="simultaneous bounded proportional / constrained solve", fees="source applies performance and estimated redemption costs"), indent=2))
    return frame, runs, robust


def write_findings(data, result, frame, runs, robust):
    """Persist interpretable evidence after all stages complete."""
    x = result["summary"].query("h == 30")
    metrics = frame.set_index("Arm")
    lines = ["# Experiment 12 — allocation follow-up findings", f"\nPeriod: **{PERIOD}**; all2025 and earlier warmup retained. **12 sensitivities + eight cap-aware methods + ten controls; 16 full engine replays.**", "\n## What was examined", "\nLocal risk windows, prior strength, raw floors and constrained risk-budget allocations on fixed six-vault baskets. The engine shortlist then carries holdings with source two-day rebalancing, actual fill timing, hysteresis, permissions and fees.", "\n## Hypotheses and snapshot results", "\nA useful sizing method should survive nearby parameters; including capacity constraints inside the convex objective may improve allocation. Snapshot results use 62 resolved30-day origins, eight complete blocks; all comparisons are descriptive."]
    lines.append(x[["arm", "label", "mean_return", "mean_drawdown", "mean_cash"]].to_markdown(index=False, floatfmt=".6f"))
    lines += ["\n## Full engine results", "\nEngine CAGR is directly executable in the simulation. Research methods share simultaneous cap allocation; source_v11 uses its untouched original sequential allocator. Caps are relative to the current deployable budget, unlike fixed-account snapshot caps. Missing scores keep source selection behaviour; young risk histories use causal partial histories and peer fallbacks."]
    lines.append(frame[["Arm", "Method", "CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)", "Mean cash weight", "Trades"]].to_markdown(index=False, floatfmt=".6f"))
    lines += ["\n## Key new insights"]
    for s, base in [("F", "S03"), ("L", "S04")]:
        sens = x[x.selector.eq(s) & x.arm.str.startswith("X")].sort_values("mean_return", ascending=False).iloc[0]
        b = x[x.arm.eq(base)].iloc[0]
        lines.append(f"\n- {s} best registered sensitivity {sens.arm} has mean30-day return {sens.mean_return:.3%} versus {b.mean_return:.3%} for the regularised90-day benchmark. Its engine replay CAGR is {metrics.loc[sens.arm,'CAGR']:.2%} versus {metrics.loc[base,'CAGR']:.2%}; this sensitivity was selected retrospectively.")
    for a, b in [("C02", "C01"), ("C04", "C03"), ("C06", "C05"), ("C08", "C07")]:
        aa = x[x.arm.eq(a)].iloc[0]
        bb = x[x.arm.eq(b)].iloc[0]
        lines.append(f"\n- Constrained {a} minus projected {b}: {(aa.mean_return-bb.mean_return)*100:+.3f} percentage points mean30-day return, {(aa.mean_drawdown-bb.mean_drawdown)*100:+.3f} points mean drawdown. Same snapshot invested budget.")
    lines += ["\n## Robustness of results", "\nAll ten NB11 reference controls reproduce accepted weights and all horizon outcomes. Mathematical fixtures, cap feasibility, solver KKT/objective checks and paired-budget checks pass. One mature90-day basket remains unresolved without survivor renormalisation. Only eight independent primary30-day blocks and repeatedly searched history prevent confirmation claims. Source inventory/guard history and archive publication clocks remain limitations.", "\nPosition curves reconcile to total portfolio PnL within $1. Tail statistics and vault contribution tables are saved and shown. Concentration and quarter influence must be assessed alongside aggregate metrics."]
    lines.append(robust.to_markdown(index=False, floatfmt=".6f"))
    path = ROOT / "12-allocation-followup-findings.md"
    path.write_text("\n".join(lines) + "\n")
    return path
