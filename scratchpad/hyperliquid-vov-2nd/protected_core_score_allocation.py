"""NB19 source-authoritative core with absolute score/risk entry tickets."""

import ast
import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr, contextmanager
from copy import deepcopy, copy
from dataclasses import replace
import numpy as np
import pandas as pd
from tqdm_loggable.auto import tqdm
import capital_allocation as parent
import profitable_allocation as engine
import waterfall_comparison as reference
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast
from score_matrix import FEATURES, MatrixIndicators

ROOT = parent.ROOT
PERIODS = parent.PERIODS
LABELS = parent.LABELS
METHODS = {"C00": "Exact corrected C-W", "E00": "Flat tickets / hold units", "R00": "Risk tickets / hold units", "S00": "Score tickets / hold units", "RS00": "Score × risk / hold units", "RS01": "Score × risk / resize", "NRS00": "Normalised score × risk / resize", "RS08": "Score × risk / eight slots", "RS12": "Score × risk / twelve slots", "GF25": "Score floor 0.25 / hold", "CAP10": "Smaller exposure caps / hold"}
PRIMARY = list(METHODS)[:9]
REGISTRY = {"risk_days": 90, "actual_update_shrinkage": 30, "score_floor": 0.5, "single_gross_cap": 0.05, "total_gross_cap": 0.25, "ticket_fraction": 0.5, "core_slots": 6, "entry_rank": 6, "exit_rank": 8, "missing": True, "initial_cash": 150000}


def initialise():
    data, evaluator = parent.initialise()
    previous = data["artifact"]
    identity = {"version": "nb19-v1", "inputs": data["manifest"]["identity"], "methods": METHODS, "registry": REGISTRY, "code": hashlib.sha256((ROOT / "protected_core_score_allocation.py").read_bytes()).hexdigest()}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/19" / key
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=key, nb17_reference=previous, nb19_decisions=[], nb19_candidates=[], nb19_checks=[], nb19_risk={}, nb19_quotes=[], figures=[])
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    install_evaluator_limit(evaluator)
    data["manifest"] = {"identity": identity, "framework": data["framework_commits"], "periods": {p: list(map(str, v)) for p, v in PERIODS.items()}, "limitations": ["Researched overlapping histories, retrospective universe/guard", "NAV observation timestamp assumed available; executable NAV unverified", "Inherited 10% profit and 0.1% capital fee allowances", "Same-state core intentions are protected; future wealth and core membership can change"]}
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data, evaluator


def fixed_risk(data, t, ids):
    """Use a treatment-independent eligible leave-one-out peer pool."""
    t = pd.Timestamp(t)
    a = data["date_index"].get(t - pd.Timedelta(days=1))
    if a is None:
        return pd.DataFrame(index=ids, columns=["predicted", "prior", "risk_multiplier", "updates", "age", "prior_only"])
    cache = data["nb19_risk"]
    if t not in cache:
        e = data["eligibility"]
        pool = sorted(e.loc[e.origin_at.eq(t) & e.eligible_as_of_origin, "pair_id"].astype(int).unique())
        cache[t] = {"pool": pool, "empirical": {}, "rows": {}}
    c = cache[t]

    def emp(i):
        if i not in c["empirical"]:
            j = data["id_index"][i]
            c["empirical"][i] = empirical_window(data["arrays"]["nav"][max(0, a - 90) : a + 1, j], data["arrays"]["actual"][max(0, a - 90) : a + 1, j], 90)
        return c["empirical"][i]

    for i in c["pool"]:
        emp(i)
    for i in ids:
        if i in c["rows"]:
            continue
        v = emp(i)
        peers = [emp(p) for p in c["pool"] if p != i]
        values = np.array([p["empirical"] for p in peers])
        full = np.array([p["full"] for p in peers], bool)
        valid = np.isfinite(values) & (values > 0)
        chosen = values[valid & full] if np.any(valid & full) else values[valid]
        prior = float(np.median(chosen)) if len(chosen) else np.nan
        pred = forecast(v["empirical"], prior, v["m"], "regularised", 30)
        ratio = min(1.0, np.sqrt(prior / pred)) if np.isfinite(pred + prior) and pred > 0 and prior > 0 else np.nan
        last = data["arrays"]["last_observed"][a, data["id_index"][i]]
        c["rows"][i] = dict(predicted=pred, prior=prior, risk_multiplier=ratio, updates=v["m"], age=float((t.to_datetime64() - last) / np.timedelta64(1, "D")), prior_only=not np.isfinite(v["empirical"]), peer_count=len(chosen))
    return pd.DataFrame({i: c["rows"][i] for i in ids}).T


class ProtectedAlpha(reference.WaterfallAlpha):
    """Preserve source waterfall and give executable core buys first priority."""

    def _cap_buys_by_realisable_sync_cash(self, pm, current, redemptions, frozen, buy, sell, headroom):
        original = {i: float(s.position_adjust_usd) for i, s in self.signals.items() if s.position_adjust_usd > 0 and not s.position_adjust_ignored}
        super()._cap_buys_by_realisable_sync_cash(pm, current, redemptions, frozen, buy, sell, headroom)
        if not self.adapter.active:
            return
        executable = [s for s in self.iterate_signals() if s.pair.internal_id in original and self._is_executable_cash_spending_buy(s, pm, current, frozen, buy)]
        budget = sum(float(s.position_adjust_usd) for s in executable)
        core = [s for s in executable if s.pair.internal_id in self.adapter.core]
        extra = [s for s in executable if s not in core]
        need = sum(original[s.pair.internal_id] for s in core)
        take = min(need, budget)
        for group, amount in ((core, take), (extra, max(0, budget - take))):
            total = sum(original[s.pair.internal_id] for s in group)
            for s in group:
                s.position_adjust_usd = original[s.pair.internal_id] * min(1, amount / total) if total else 0
        self.adapter.data["nb19_checks"].append(dict(Period=self.adapter.period, Arm=self.adapter.name, Date=self.timestamp, Check="core synchronous funding", Requested=need, Funded=take, Shortfall=max(0, need - take)))


class Adapter:
    """Own only core roles and the additional allocation hook."""

    def __init__(self, data, strategy, name, period, ledger, active=True):
        self.data = data
        self.strategy = strategy
        self.name = name
        self.period = period
        self.ledger = ledger
        self.core = set()
        self.extra = set()
        self.active = active
        self.models = []
        self.intent = None
        self.forced_held = None

    def held(self, actual):
        if self.forced_held is not None:
            return self.forced_held
        return actual if not self.active or not self.core and not self.extra else actual & self.core

    def merge(self, input, model, ordered, core_ids, B, buy, reference_equity, pm, sr, check_entry):
        self.core = set(core_ids)
        self.intent = {i: float(model.signals[i].position_target or 0) for i in core_ids}
        if not self.active:
            for i, signal in model.signals.items():
                self.ledger.append({"Date": pd.Timestamp(input.timestamp), "Pair id": int(i), "Address": str(signal.pair.pool_address).lower(), "Vault": signal.pair.get_vault_name(), "Role": "core" if i in self.core else "pinned" if signal.carry_forward_position else "exit", "Final target (USD)": float(signal.position_target or 0), "Old value (USD)": float(signal.old_value or 0), "Deployable budget (USD)": B})
            return
        p = input.parameters
        t = pd.Timestamp(input.timestamp)
        old = {int(v.pair.internal_id): v for v in input.state.portfolio.get_open_positions() if not v.pair.is_credit_supply()}
        pinned = {i for i, s in model.signals.items() if s.carry_forward_position}
        before = {i: float(model.signals[i].position_target or 0) for i in core_ids}
        core_total = sum(float(s.position_target or 0) for s in model.signals.values() if not s.carry_forward_position)
        residual = max(0, B - core_total)
        # Conservative gross denominator allows every open positive NAV to lose 10.1% on exit.
        gross_cash = float(input.state.portfolio.get_cash())
        gross_old = {i: float(v.get_quantity()) * engine.observed_quote(self.data, i, t)[0] for i, v in old.items()}
        capital_fee = float(p.vault_redemption_capital_fee)
        performance_fee = float(p.vault_performance_fee)
        E = min(reference_equity, (1 - capital_fee) * (gross_cash + (1 - performance_fee - capital_fee) * sum(gross_old.values())))
        E = max(0, E)
        single = 0.02 if self.name == "CAP10" else 0.05
        totalcap = 0.10 if self.name == "CAP10" else 0.25
        floor = 0.25 if self.name == "GF25" else 0.5
        budget = min(residual, totalcap * E)
        epsilon = float(p.min_portfolio_weight_pct)
        if core_total > 0:
            positive = [v for v in before.values() if v >= epsilon * core_total and v > 0]
            if positive:
                budget = min(budget, max(0, min(positive) / epsilon - core_total))
        candidates = {int(i): (pair, float(score)) for i, pair, score in ordered if i not in self.core and i not in pinned}
        ids = list(candidates)
        risk = fixed_risk(self.data, t, ids)
        slots = 2 if self.name == "RS08" else 6 if self.name == "RS12" else 4
        slots = min(slots, max(0, 6 + slots - len(self.core | pinned)))
        selected = {}
        proposal = []
        retained = sorted((set(old) & set(candidates)) - pinned, key=lambda i: (-candidates[i][1], str(candidates[i][0].pool_address)))
        fresh = [i for i in ids if i not in old]
        demoted = [i for i in ids if i in old and i not in retained]
        sequence = retained + demoted + fresh
        resize = self.name in ("RS01", "NRS00")
        for i in sequence:
            pair, score = candidates[i]
            previous = float(old[i].get_value()) if i in old else 0.0
            gross = gross_old.get(i, 0.0)
            finite = np.isfinite(input.indicators.get_indicator_value("matrix_score", pair=pair))
            g = floor + (1 - floor) * np.clip(score, 0, 1) if finite else floor
            r = float(risk.loc[i, "risk_multiplier"])
            supported = np.isfinite(r) and r > 0
            allowed = pm.is_whitelisted_vault(pair)
            check = check_entry(pair)
            allowed = allowed and check.can_deposit
            head = max(0, float(check.max_deposit)) if allowed and check.max_deposit is not None else float("inf") if allowed else 0.0
            capacity = float(sr.get_acceptable_size_for_position(t, pair, float(p.max_concentration_pct) * B).accepted_size)
            cap = min(capacity, single * E, gross + head)
            multiplier = 1.0 if self.name == "E00" else r if self.name == "R00" else g if self.name == "S00" else g * r
            D = 0.5 * single * E
            ticket = min(cap, D * multiplier) if supported else 0
            reason = "accepted"
            if len(selected) >= slots:
                reason = "slots"
            elif not allowed and previous <= 0:
                reason = "permission"
            elif not supported:
                reason = "risk unsupported"
            elif cap <= 0:
                reason = "capacity"
            value = min(gross, cap) if previous > 0 and not resize else ticket
            if previous > 0 and not resize and value < gross - 1e-6 and previous - value * (previous / gross) < max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.sell_rebalance_min_threshold_of_initial_cash_pct)):
                value = 0
                reason = "hard cap requires close"
            if previous > 0 and gross > cap + 1e-6:
                hard_reduction = previous - cap * (previous / gross)
                hard_band = max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.sell_rebalance_min_threshold_of_initial_cash_pct))
                if hard_reduction < hard_band:
                    value = 0
                    reason = "hard cap requires close"
            if previous > 0 and not allowed:
                value = min(value, gross)
            if reason == "accepted" and value > budget + 1e-6:
                value = min(value, budget)
                if previous > 0 and previous - value * (previous / gross) < max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.sell_rebalance_min_threshold_of_initial_cash_pct)):
                    value = 0
                    reason = "hard budget requires close"
            marked = value * (previous / gross) if gross > 0 else value
            if reason == "accepted" and marked < epsilon * (core_total + marked):
                reason = "cleanup floor"
            if reason == "accepted" and previous <= 0 and value < buy:
                reason = "buy floor"
            if reason == "accepted" and value > 0:
                selected[i] = dict(pair=pair, gross=value, target=marked, score=score, g=g, r=r, cap=cap, old=previous, finite=finite, units=float(old[i].get_quantity()) if i in old else 0)
                budget -= value
            proposal.append(dict(Period=self.period, Arm=self.name, Date=t, Pair_id=i, Vault=pair.get_vault_name(), Score=score, Finite=finite, G=g, R=r, Prior_only=bool(risk.loc[i, "prior_only"]), Updates=risk.loc[i, "updates"], Age=risk.loc[i, "age"], Cap=cap, Ticket=ticket, Accepted=selected.get(i, {}).get("gross", 0), Reason=reason, Incumbent=i in old))
        if self.name == "NRS00" and selected:
            from portfolio_snapshot_construction import bounded_proportional

            keys = list(selected)
            caps = np.array([selected[i]["cap"] for i in keys])
            raw = np.array([selected[i]["g"] * selected[i]["r"] for i in keys])
            amount = min(residual, totalcap * E)
            vals = bounded_proportional(raw, caps, amount)
            for i, v in zip(keys, vals):
                s = selected[i]
                s["gross"] = float(v)
                s["target"] = float(v) * (s["old"] / gross_old[i] if gross_old.get(i, 0) > 0 else 1)
        # Recall lowest-score retained holdings until core buys have the same sale funding as core-only.
        sell = max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.sell_rebalance_min_threshold_of_initial_cash_pct))
        headroom = max(0.5, reference_equity * 0.0005)

        def proceeds(extras):
            value = gross_cash
            for i, pos in old.items():
                sig = model.signals.get(i)
                if i in pinned or pm.is_async_vault_sell_pair(pos.pair, position_pair=pos.pair):
                    continue
                target = before.get(i, extras.get(i, {}).get("target", 0))
                reduction = float(pos.get_value()) - target
                if reduction > 0 and (target <= 0 or reduction >= sell):
                    value += reduction
            return max(0, value - headroom)

        need = sum(max(0, v - float(old[i].get_value()) if i in old else v) for i, v in before.items() if (v - float(old[i].get_value()) if i in old else v) >= buy)
        expected = min(need, proceeds({}))
        recalls = 0
        for i in sorted(selected, key=lambda i: (selected[i]["score"], str(selected[i]["pair"].pool_address))):
            if proceeds(selected) >= expected - 1e-6:
                break
            if i in old:
                del selected[i]
                recalls += 1
        assert proceeds(selected) >= expected - 1e-6, (t, self.name, "core funding")
        for i, s in selected.items():
            if i not in model.signals:
                model.set_signal(s["pair"], 1.0)
                model.signals[i] = model.raw_signals[i]
                model.set_old_weight(s["pair"], 0.0, s["old"], s["pair"])
            signal = model.signals[i]
            signal.signal = 1.0
            signal.position_target = s["target"]
            signal.set_deposit_check_result(check_entry(s["pair"]))
        for i, v in before.items():
            assert model.signals[i].position_target == v
        self.extra = set(selected)
        self.data["nb19_candidates"].extend(proposal)
        self.data["nb19_decisions"].append(dict(Period=self.period, Arm=self.name, Date=t, Equity=E, Budget=B, Core_target=core_total, Residual=residual, Extra_gross=sum(s["gross"] for s in selected.values()), Extra_positions=len(selected), Core_positions=len(self.core), Pinned_positions=len(pinned), Funding_recall=recalls, Core_funding_expected=expected, Core_requested=need))
        for i, s in model.signals.items():
            self.ledger.append({"Date": t, "Pair id": int(i), "Address": str(s.pair.pool_address).lower(), "Vault": s.pair.get_vault_name(), "Role": "core" if i in self.core else "additional" if i in self.extra else "pinned" if s.carry_forward_position else "exit", "Final target (USD)": float(s.position_target or 0), "Core-only target (USD)": before.get(i, 0), "Old value (USD)": float(s.old_value or 0), "Deployable budget (USD)": B})
        self.data["nb19_checks"].append(dict(Period=self.period, Arm=self.name, Date=t, Check="source core targets unchanged", Requested=sum(before.values()), Funded=sum(model.signals[i].position_target for i in before), Shortfall=0.0))


def compile_adapter(strategy, adapter, save=True):
    text = parent.SOURCE.read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "decide_trades")
    source = ast.get_source_segment(text, node)
    source = source.replace("    def check_entry_candidate(", "    held_pair_ids = _adapter.held(held_pair_ids)\n\n    def check_entry_candidate(", 1)
    anchor = "    total_accepted = sum("
    at = source.index(anchor)
    source = source[:at] + """    _adapter.merge(input, alpha_model, ordered, core_ids, float(fresh_capital), buy_threshold, reference_equity, position_manager, size_risk_model, check_entry_candidate)
""" + source[at:]
    line = "                trade.planned_price = trade.planned_mid_price * (1.0 - fee)"
    source = source.replace(
        line,
        """                if not trade.closing:
                    trade.planned_mid_price = engine.observed_quote(_adapter.data, trade.pair.internal_id, timestamp)[0]
                    trade.other_data['nb17_corrected_partial_fee'] = True
                trade.planned_price = trade.planned_mid_price * (1.0 - fee)""",
    )
    ns = dict(strategy.__dict__)
    ns.update(_adapter=adapter, engine=engine)

    def make(*a, **kw):
        m = ProtectedAlpha(*a, sizing_mode="parent", allocation_ledger=[], **kw)
        m.adapter = adapter
        adapter.models.append(m)
        return m

    def weights(ids, inv, signals, **kw):
        return {int(i): max(float(v), 1e-12) for i, v in engine.research_weights(adapter.data, adapter.timestamp, ids, "regular")[0].items()}

    ns.update(AlphaModel=make, compute_sizing_weights=weights)
    exec(compile(source, str(ROOT / "protected_core_score_allocation.py") + "::source-adapter", "exec"), ns)
    if save:
        (adapter.data["artifact"] / "compiled-source.py").write_text(source)
    return ns["decide_trades"]


def replay(data, evaluator, name, period, active=True):
    import score_matrix

    original = score_matrix.make_matrix_decision
    values = evaluator.panel.score_values
    adapter = None
    starts = {k: len(data[k]) for k in ("nb19_decisions", "nb19_candidates", "nb19_checks", "nb19_quotes", "funding_ledger")}
    evaluator.nb19_total_limit = 6 if not active else 8 if name == "RS08" else 12 if name == "RS12" else 10
    data["run_context"] = (period, name, "primary")
    evaluator.panel.score_values = lambda *a, **kw: data["focal_values"]
    w = np.zeros(len(FEATURES))
    w[0] = 1

    def factory(strategy, panel, vals, sizing, allocator, ledger, **kw):
        nonlocal adapter
        adapter = Adapter(data, strategy, name, period, ledger, active)
        callback = compile_adapter(strategy, adapter)
        shadow = Adapter(data, strategy, "shadow", period, [], active=False)
        shadow_callback = compile_adapter(strategy, shadow, save=False)

        def decide(input):
            p = deepcopy(input.parameters)
            p["max_assets_in_portfolio"] = p["max_capacity_assets"] = 6
            p["entry_rank"] = 6
            p["exit_rank"] = 8
            adapter.timestamp = input.timestamp
            proposed = replace(input, parameters=p, indicators=MatrixIndicators(input.indicators, panel, vals, input.timestamp))
            if active:
                actual = {int(v.pair.internal_id) for v in input.state.portfolio.get_open_positions() if not v.pair.is_credit_supply()}
                shadow.forced_held = adapter.held(actual)
                shadow.timestamp = input.timestamp
                shadow.intent = None
                shadow.models.clear()
                state = copy(input.state)
                state.portfolio = copy(input.state.portfolio)
                state.portfolio.open_positions = deepcopy(input.state.portfolio.open_positions)
                state.portfolio.closed_positions = dict(input.state.portfolio.closed_positions)
                pricing = copy(input.pricing_model)
                shadow_callback(replace(proposed, state=state, pricing_model=pricing))
            adapter.intent = None
            adapter.models.clear()
            trades = callback(proposed)
            if active:
                assert adapter.intent == shadow.intent, (input.timestamp, name, "independent same-state core intention")
                data["nb19_checks"].append(dict(Period=period, Arm=name, Date=input.timestamp, Check="independent source core intention", Requested=sum((shadow.intent or {}).values()), Funded=sum((adapter.intent or {}).values()), Shortfall=0.0))
            reference.cap_to_final_sell_proceeds(data, input, trades, name)
            return trades

        return decide

    score_matrix.make_matrix_decision = factory
    evaluator.run.__func__.__globals__["make_matrix_decision"] = factory
    try:
        with engine.pricing_convention(data), entry_marking(data):
            r = evaluator.run(w, *PERIODS[period], n=6, sizing="inverse_variance", missing=True, keep=True, profile="NB19-" + name + ("-zero" if not active else "") + ("-shared-entry-mark" if data.get("consistent_entry_mark") else "-legacy-entry-mark"))
        path = evaluator.folder / f'{r["cache_key"]}-diagnostics.json'
        if adapter is None:
            assert path.exists()
            for k, rows in json.loads(path.read_text()).items():
                data[k].extend(rows)
        else:
            path.write_text(json.dumps({k: data[k][n:] for k, n in starts.items()}, default=str))
        return r
    finally:
        score_matrix.make_matrix_decision = original
        evaluator.run.__func__.__globals__["make_matrix_decision"] = original
        evaluator.panel.score_values = values


def trade_signature(r):
    return [(str(t.executed_at), str(t.pair.pool_address), float(t.executed_quantity), float(t.executed_price), float(t.executed_reserve)) for t in r["result"].state.portfolio.get_all_trades() if t.is_success()]


def controls(data, evaluator):
    runs = {}
    checks = []
    folder = evaluator.folder
    for period in PERIODS:
        print("Historical and zero-slot parity:", period, flush=True)
        evaluator.folder = data["nb17_reference"] / "engine"
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                baseline = parent.corrected_benchmark(data, evaluator, period)
        finally:
            evaluator.folder = folder
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            zero = replay(data, evaluator, "P00", period, active=False)
        assert baseline["equity"].equals(zero["equity"]), (period, "zero adapter equity")
        assert trade_signature(baseline) == trade_signature(zero), (period, "zero adapter trades")
        checks.append(dict(Period=period, Equity_identical=True, Trades_identical=True, Trades=len(trade_signature(zero))))
        data.setdefault("historical_runs", {})[(period, "C00")] = baseline
        data["consistent_entry_mark"] = True
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            common = replay(data, evaluator, "C00", period, active=False)
        runs[(period, "C00")] = common
        data["consistent_entry_mark"] = False
    pd.DataFrame(checks).to_csv(data["artifact"] / "control-parity.csv", index=False)
    data["control_runs"] = runs
    data["consistent_entry_mark"] = True
    return runs


def run(data, evaluator):
    records = []
    runs = {}
    attribution = {}
    weights = {}
    audits = []
    jobs = [(p, a) for p in PERIODS for a in PRIMARY]
    for period, arm in tqdm(jobs, desc="NB19 full-engine accounts", mininterval=15):
        print(period, arm, flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = data["control_runs"][(period, arm)] if arm == "C00" else replay(data, evaluator, arm, period)
        add_result(data, r, arm, period, records, runs, attribution, weights, audits)
    candidates = pd.DataFrame(data["nb19_candidates"])
    if len(candidates) and candidates.loc[candidates.Arm.eq("RS00") & ~candidates.Incumbent, "Accepted"].gt(0).any():
        for period in PERIODS:
            for arm in ("GF25", "CAP10"):
                print("Registered sensitivity", period, arm, flush=True)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    r = replay(data, evaluator, arm, period)
                add_result(data, r, arm, period, records, runs, attribution, weights, audits)
    pd.concat(audits, ignore_index=True).to_csv(data["artifact"] / "fill-audit.csv", index=False)
    return pd.DataFrame(records), runs, attribution, weights


def add_result(data, r, arm, period, records, runs, attribution, weights, audits):
    m, v, w = engine.analyse_run(data, r, arm, period)
    m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
    m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"])
    cash = w[next(c for c in w if c in ("USDC", "USDT", "USD"))]
    m["September cash"] = float(cash.loc["2026-09-01":"2026-09-30"].mean())
    held = w.drop(columns=cash.name)
    m["Mean effective breadth"] = float((held.sum(axis=1) ** 2 / held.pow(2).sum(axis=1).replace(0, np.nan)).mean())
    for h in (7, 30):
        m[f"Worst {h}-day return"] = float(r["equity"].resample("D").last().ffill().pct_change(h).min())
    records.append(dict(Period=period, Arm=arm, Method=METHODS[arm], **m))
    runs[(period, arm)] = r
    attribution[(period, arm)] = v
    weights[(period, arm)] = w
    audits.append(parent.audit(data, r, arm, period))
    r["allocation_df"].to_csv(data["artifact"] / f"{period}-{arm}-target-ledger.csv", index=False)
    pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
    for k in ("nb19_decisions", "nb19_candidates", "nb19_checks", "funding_ledger"):
        pd.DataFrame(data[k]).to_csv(data["artifact"] / (k + ".csv"), index=False)


@contextmanager
def entry_marking(data):
    """Reset a fresh entry's cached tax, leaving held top-up accounting intact."""
    from tradeexecutor.backtest.backtest_pricing import BacktestPricing

    original = BacktestPricing.get_buy_price

    def quote(self, ts, pair, *args, **kwargs):
        rates = getattr(self, "_vault_redemption_fee_by_pair_id", {})
        if pair.is_vault() and pair.internal_id not in rates:
            cached = float(pair.base.get_sell_tax() or 0)
            fallback = 0.001
            data["nb19_quotes"].append(dict(Period=data["run_context"][0], Arm=data["run_context"][1], Date=str(ts), Pair_id=int(pair.internal_id), Cached=cached, Fallback=fallback, Gap=cached - fallback, Corrected=bool(data.get("consistent_entry_mark"))))
            if data.get("consistent_entry_mark"):
                pair.base.other_data["sell_tax"] = fallback
        return original(self, ts, pair, *args, **kwargs)

    BacktestPricing.get_buy_price = quote
    try:
        yield
    finally:
        BacktestPricing.get_buy_price = original


def install_evaluator_limit(evaluator):
    """Change only the local evaluator holding assertion; source n stays six."""
    import inspect
    import textwrap
    from types import MethodType

    original = type(evaluator).run
    source = textwrap.dedent(inspect.getsource(original))
    old = 'assert metrics["Maximum vaults held"]<=n, (key,metrics["Maximum vaults held"],n)'
    new = 'assert metrics["Maximum vaults held"]<=getattr(self,"nb19_total_limit",n), (key,metrics["Maximum vaults held"],getattr(self,"nb19_total_limit",n))'
    assert source.count(old) == 1
    namespace = original.__globals__
    exec(compile(source.replace(old, new), "NB19::local-evaluator-limit", "exec"), namespace)
    evaluator.run = MethodType(namespace["run"], evaluator)
    evaluator.nb19_total_limit = 6
