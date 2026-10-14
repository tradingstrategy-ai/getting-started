"""Protected-core conditional allocation through the frozen source engine."""

import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import numpy as np
import pandas as pd
from tqdm_loggable.auto import tqdm
import capital_allocation as parent
import profitable_allocation as engine
import conditional_cash_forecasts as forecasts
from capital_allocation_methods import floors, waterfall
from score_matrix import FEATURES, MatrixIndicators
from tradeexecutor.strategy.weighting import weight_passthrouh
from tradeexecutor.strategy.tvl_size_risk import USDTVLSizeRiskModel

ROOT = parent.ROOT
PERIODS = parent.PERIODS
LABELS = parent.LABELS
METHODS = {"C00": "Exact C-W / corrected fees", "C01": "Admission-aware core / corrected fees", "C02": "Unconditional four-slot overflow / corrected fees", "R00": "Risk-only sleeve", "R01": "Risk sleeve + economic exits", "R02": "Pooled lower-bound gate", "R03": "Score-group positive gate", "R04": "Score-group gate + gradual sizing", "R05": "Gradual sizing / full reference risk"}
REGISTRY = {"forecast_horizon": 30, "diagnostic_horizons": [7, 30, 90], "origins": "NB08 Jan 1 four-day phase", "fit": "monthly start, strict maturity", "bands": list(forecasts.GROUPS), "bootstrap": 500, "lower_quantile": 0.2, "pooled_support": [20, 10, 6], "group_support": [10, 5, 3], "risk_window": 90, "risk_kappa": 30, "anchor_window": 90, "anchor_decisions": 30, "risk_k": {"R05": 1.0, "others": 0.75}, "sleeve_cap": 0.25, "single_cap": 0.05, "total_slots": 12, "sleeve_slots": 6, "partial_fees": "corrected for every account", "initial_cash": 150000, "missing": True}


def initialise():
    data, evaluator = parent.initialise()
    previous = data["artifact"]
    nb17 = previous
    saved = pd.read_csv(nb17 / "fee-sensitivities.csv")
    data["nb17_fee_expected"] = saved
    identity = {"version": "nb18-v1", "nb17_identity": data["manifest"]["identity"], "methods": METHODS, "registry": REGISTRY, "code": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ("conditional_cash_allocation.py", "conditional_cash_forecasts.py")}}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/18" / digest
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=digest, nb17_reference=nb17, nb18_risk={}, nb18_decisions=[], nb18_checks=[], figures=[])
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    data["manifest"] = {"identity": identity, "framework": data["framework_commits"], "periods": {p: list(map(str, v)) for p, v in PERIODS.items()}, "limitations": ["Searched overlapping history, retrospective universe/guard", "Recorded NAV is not proof of executable NAV or publication receipt", "Forecasts condition on resolved labels; unresolved upside unbounded", "Risk reference is hypothetical and adapts; not an approved loss tolerance"], "risk_units": "max regular simple and gap log daily volatility, first-order approximation", "funding": "protected source core, corrected final proceeds", "gross_exposure_safety": "Conservative target/(1-current modelled exit fee); retained and pinned actual NAV exposures checked separately"}
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    forecasts.fixtures().to_csv(folder / "algebra-checks.csv", index=False)
    return data, evaluator


def controls(data, evaluator):
    """Independent corrected controls and parity with saved NB17 sensitivities."""
    runs = {}
    checks = []
    folder = evaluator.folder
    evaluator.folder = data["nb17_reference"] / "engine"
    try:
        # Full C01 is needed before any causal reference/calibration construction.
        for period in ("Long", "2026"):
            for arm, old in [("C01", "M01"), ("C00", "M00"), ("C02", "M05")]:
                print(f"Corrected control {period} / {arm}; approximately 1–3 minutes if uncached", flush=True)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    r = parent.corrected_benchmark(data, evaluator, period) if arm == "C00" else parent.replay(data, evaluator, old, period, corrected=True)
                runs[(period, arm)] = r
                if arm in ("C00", "C02"):
                    expected = data["nb17_fee_expected"].set_index(["Period", "Arm"]).loc[(period, old)]
                    for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)"):
                        error = r["metrics"][metric] - expected[metric]
                        assert abs(error) < (0.01 if "USD" in metric else 2e-6), (arm, period, metric, error)
                        checks.append(dict(Period=period, Arm=arm, Metric=metric, Difference=error))
    finally:
        evaluator.folder = folder
    pd.DataFrame(checks).to_csv(data["artifact"] / "control-parity.csv", index=False)
    data["control_runs"] = runs
    return runs


def prepare(data, evaluator):
    forecasts.build_panel(data, evaluator, data["control_runs"][("Long", "C01")])
    forecasts.build_anchor(data, data["control_runs"][("Long", "C01")])
    forecasts.build_forecasts(data)
    shadows(data)


def proposal(data, t, f, k=0.75, slots=6, totalcap=0.25, single=0.05, gate="none"):
    """Fresh-proposal mechanism shadow, without retained-sleeve feedback."""
    q = f.set_index("Pair id")
    core = list(q[q.Role.eq("core")].index)
    ids = list(q.index)
    B = float(q["Deployable budget (USD)"].iloc[0])
    E = B / 0.98
    rr = forecasts.risk(data, t, ids)
    sig = rr.sigma.to_dict()
    A, n = forecasts.anchor_at(data, t)
    T = k * A
    target = q["Core-only target (USD)"].to_dict()
    L = sum(target[i] / E * sig[i] for i in core) if all(np.isfinite(sig[i]) for i in core) else np.nan
    R = max(0, B - sum(target.values())) / E
    J = max(0, T - L) if np.isfinite(T + L) else 0.0
    model = forecasts.forecast_at(data, t)
    cand = q[~q.index.isin(core) & q["Capacity ceiling (USD)"].gt(0)].sort_values(["Ranking score", "Address"], ascending=[False, True])
    available = []
    for i, row in cand.iterrows():
        g = forecasts.group(row["Ranking score"] if row["Score available"] else np.nan)
        ok = gate == "none" or model["supported"] and (model["lower"] > 0 if gate == "pooled" else model["groups"][g]["z"] > 0)
        if ok and np.isfinite(sig[i]) and sig[i] > 0:
            available.append(int(i))
    selected = available[:slots] if slots is not None else available
    cap = {i: min(single, float(q.loc[i, "Capacity ceiling (USD)"]) / E) for i in selected}
    x = forecasts.capped_inverse_volatility(selected, cap, sig, min(R, totalcap), J)
    G = sum(x[i] * model["groups"][forecasts.group(q.loc[i, "Ranking score"] if q.loc[i, "Score available"] else np.nan)]["z"] for i in x) if model["supported"] else np.nan
    extra = sum(x[i] * sig[i] for i in x)
    a = forecasts.alpha(G, L, extra)
    topcaps = {i: max(0, float(q.loc[i, "Capacity ceiling (USD)"]) - target[i]) / E for i in core}
    top = forecasts.capped_inverse_volatility(core, topcaps, sig, min(R, totalcap), J)
    return dict(Date=t, k=k, Slots="unlimited" if slots is None else str(slots), Sleeve_cap=totalcap, Single_cap=single, Gate=gate, Anchor=A, Anchor_support=n, Core_risk=L, Risk_headroom=J, Cash_headroom=R, Proposed=sum(x.values()), Proposed_risk=extra, Alpha=a, Gradual=sum(x.values()) * a, Forecast_supported=model["supported"], Pooled_positive=bool(model["supported"] and model["lower"] > 0), Available=len(available), Core_topup=sum(top.values()), Stress50=0.5 * sum(x.values()), Stress100=sum(x.values()))


def shadows(data):
    f = data["control_runs"][("2026", "C01")]["allocation_df"]
    rows = []
    for t, g in f.groupby("Date"):
        for k in (0.75, 1.0):
            for gate in ("none", "pooled", "group"):
                rows.append(proposal(data, pd.Timestamp(t), g, k, gate=gate))
        for slots, total, single in ((4, 0.25, 0.05), (None, 0.25, 0.05), (6, 0.10, 0.02), (6, 1.0, 1.0)):
            rows.append(proposal(data, pd.Timestamp(t), g, slots=slots, totalcap=total, single=single))
    data["shadows"] = pd.DataFrame(rows)
    data["shadows"].to_parquet(data["artifact"] / "fresh-proposal-shadows.parquet", index=False)


class ConditionalPolicy(parent.Policy):
    """Reuse core-role hysteresis and protected funding, replacing only sleeve targets."""

    def __init__(self, data, strategy, method, ledger):
        # M05 is an internal adapter key enabling the unchanged core-first engine
        # callbacks. The public method and all saved ledgers use the NB18 ID.
        super().__init__(data, strategy, "M05", ledger, corrected=True)
        self.method = method
        self.sleeve = set()

    def allocate(self):
        c = self.current
        start = len(self.ledger)
        decision_start = len(self.data["nb17_decisions"])
        self.arm = "M01"
        try:
            model, core_ids, _, B, pinned, buy = super().allocate()
        finally:
            self.arm = "M05"
        core = {i: float(model.signals[i].position_target) for i in core_ids if i in model.signals and model.signals[i].position_target > 0}
        core_ids = list(core)
        self.core = set(core)
        t = c["t"]
        p = c["p"]
        old = c["old"]
        cap = c["cap"]
        epsilon = float(p.min_portfolio_weight_pct)
        actual_positions = {int(pos.pair.internal_id): pos for pos in c["input"].state.portfolio.get_open_positions() if not pos.pair.is_credit_supply()}
        ids = list(set(c["pairs"]) | set(actual_positions))
        rr = forecasts.risk(self.data, t, ids)
        sigma = rr.sigma.to_dict()
        fees = c["input"].pricing_model._vault_redemption_fee_by_pair_id
        marked_equity = float(c["pm"].get_current_portfolio().get_total_equity())
        pricing = c["input"].pricing_model
        from tradeexecutor.backtest.backtest_pricing import BacktestPricing

        # The framework builds a separate valuation pricing instance, without
        # the source's instance-level redemption wrapper. Use the unwrapped
        # class implementation to mirror that post-trade valuation convention.
        valuation_quote = lambda pair, quantity: BacktestPricing.get_sell_price(pricing.route(pair), c["input"].timestamp, pair, quantity)
        valuation_equity = float(c["pm"].get_current_cash())
        for i, pos in actual_positions.items():
            valuation_equity += float(pos.get_quantity()) * float(valuation_quote(pos.pair, pos.get_quantity()).price)
        marking_rates = {}
        for i, pair in c["pairs"].items():
            quote = engine.observed_quote(self.data, i, t)
            priced = float(valuation_quote(pair, Decimal(1)).price)
            marking_rates[i] = max(0, 1 - priced / quote[0])
        core_fee_bound = sum(max(0, v - old[i]) * marking_rates[i] for i, v in core.items())
        possible = [i for i in c["pairs"] if i not in core and i not in c["locked"] and cap[i] > 0]
        sleeve_fee_bound = 0.25 * valuation_equity * max([marking_rates[i] for i in possible], default=0.0)
        # Source reference_equity precedes the current accrued-fee refresh.
        # Subsequent buys can also be marked with the current exit-tax rate.
        # Bound that marking deduction using actual modelled rates, rather
        # than introducing a numerical buffer or changing protected core.
        # Generic post-trade valuation uses a separate unwrapped pricing model,
        # unlike the source's single-fee instance wrapper. Price opening holdings
        # through that generic quote before bounding additional buy marks.
        E = valuation_equity - core_fee_bound - sleeve_fee_bound
        assert E > 0
        factor = {i: 1 / (1 - float(fees.get(i, 0.001))) for i in ids}
        # Targets use source marked-equity dollars. Convert conservatively to
        # gross NAV exposure; source accrued fee can otherwise hide risk/caps.
        core_exposure = {i: core[i] * factor[i] for i in core}
        for i in core:
            delta = core[i] - old[i]
            if delta < 0 and -delta < c["sell"]:
                pos = actual_positions.get(i)
                quote = engine.observed_quote(self.data, i, t)
                if pos and quote:
                    core_exposure[i] = max(core_exposure[i], float(pos.get_quantity()) * quote[0])
        for i in c["locked"]:
            pos = actual_positions.get(i)
            quote = engine.observed_quote(self.data, i, t)
            core_exposure[i] = float(pos.get_quantity()) * quote[0] if pos and quote else np.nan
        known = all(np.isfinite(sigma.get(i, np.nan)) and sigma[i] > 0 and np.isfinite(v) for i, v in core_exposure.items())
        L = sum(v / E * sigma[i] for i, v in core_exposure.items()) if known else np.nan
        A, n = forecasts.anchor_at(self.data, t)
        k = 1.0 if self.method == "R05" else 0.75
        J = max(0, k * A - L) if known and np.isfinite(A) else 0.0
        R = max(0, B - sum(core.values()))
        if core:
            R = min(R, max(0, min(v / epsilon for v in core.values()) - sum(core.values())))
        cash_limit = min(R, 0.25 * E)
        risk_limit = J * E
        slots = min(6, max(0, 12 - len(core) - len(c["locked"])))
        model_fit = forecasts.forecast_at(self.data, t)
        retained = {}
        exit_reasons = {}
        forecast_delta = {}
        ordered = sorted(c["pairs"], key=lambda i: (-c["score"][i], c["addr"][i]))
        for i in sorted((self.sleeve | c["held"]) - c["locked"] - set(core), key=lambda i: (-c["score"].get(i, 0), c["addr"].get(i, ""))):
            if i not in c["pairs"] or not np.isfinite(sigma.get(i, np.nan)) or sigma[i] <= 0:
                exit_reasons[i] = "source or unknown risk"
                continue
            limit = min(cap[i], 0.05 * E / factor[i])
            v = min(old[i], limit)
            if v <= 0:
                exit_reasons[i] = "capacity"
                continue
            if self.method != "R00" and model_fit["supported"] and i in actual_positions:
                pos = actual_positions[i]
                quote = engine.observed_quote(self.data, i, t)
                value = float(pos.get_quantity()) * quote[0]
                basis = self.strategy.get_remaining_cost_basis(pos)
                g = forecasts.group(c["score"][i] if c["available"][i] else np.nan)
                delta = forecasts.expected_hold(model_fit, g, value, basis)
                forecast_delta[i] = delta
                if delta < 0:
                    exit_reasons[i] = "negative hold payoff"
                    continue
            if len(retained) >= slots:
                exit_reasons[i] = "slot"
                continue
            retained[i] = v

        def weight_total(x):
            return sum(x[i] * factor[i] for i in x)

        def risk_total(x):
            return sum(x[i] * factor[i] * sigma[i] for i in x)

        # Hard reductions precede retention; suppressed small trims become full
        # closes rather than weakening the declared gross-exposure risk ceiling.
        for i in sorted(retained, key=lambda i: (c["score"][i], c["addr"][i])):
            excess_cash = max(0, weight_total(retained) - cash_limit)
            excess_risk = max(0, risk_total(retained) - risk_limit)
            need = max(excess_cash / factor[i], excess_risk / (sigma[i] * factor[i]))
            if need <= 1e-8:
                continue
            retained[i] -= min(retained[i], need)
            if 0 < old[i] - retained[i] < c["sell"] or retained[i] < epsilon * (sum(core.values()) + sum(retained.values())):
                retained[i] = 0.0
            exit_reasons[i] = "hard risk/exposure"
        retained = {i: v for i, v in retained.items() if v > 0}
        for i in list(retained):
            if 0 < old[i] - retained[i] < c["sell"]:
                del retained[i]
                exit_reasons[i] = "mandatory trim below sell ticket: full close"
        retained = self.protect_funding(c, core, retained)
        room_cash = max(0, cash_limit - weight_total(retained))
        room_risk = max(0, risk_limit - risk_total(retained))
        candidates = []
        reasons = {}
        forecasts_net = {}
        groups = {}
        for i in ordered:
            if i in core or i in c["locked"]:
                continue
            g = forecasts.group(c["score"][i] if c["available"][i] else np.nan)
            groups[i] = g
            mean = model_fit["groups"].get(g, {}).get("z", np.nan)
            forecasts_net[i] = mean
            reason = "admitted"
            if cap[i] <= retained.get(i, 0):
                reason = "capacity/permission"
            elif not np.isfinite(sigma.get(i, np.nan)) or sigma[i] <= 0:
                reason = "unknown risk"
            elif not np.isfinite(A):
                reason = "unsupported risk anchor"
            elif self.method in ("R02", "R03", "R04", "R05") and not model_fit["supported"]:
                reason = "unsupported forecast"
            elif self.method == "R02" and model_fit["lower"] <= 0:
                reason = "pooled lower not positive"
            elif self.method in ("R03", "R04", "R05") and mean <= 0:
                reason = "group net not positive"
            elif i in exit_reasons:
                reason = "retention exit: " + exit_reasons[i]
            if reason == "admitted":
                candidates.append(i)
            reasons[i] = reason
        admitted = list(retained)
        increments = {}
        rejected = set()
        raw_full = {}
        a = 1.0
        G = 0.0
        extra = 0.0
        # Gate before slot admission. Dust removal/backfill is deterministic.
        for _ in range(len(candidates) + 1):
            admitted = list(retained) + [i for i in candidates if i not in retained and i not in rejected][: max(0, slots - len(retained))]
            increment_ids = [i for i in admitted if i in candidates and i not in rejected]
            caps = {i: max(0, min(cap[i], 0.05 * E / factor[i]) - retained.get(i, 0)) * factor[i] for i in increment_ids}
            gross = forecasts.capped_inverse_volatility(increment_ids, caps, sigma, room_cash, room_risk)
            raw_full = {i: v / factor[i] for i, v in gross.items()}
            G = sum(v / E * forecasts_net[i] for i, v in raw_full.items()) if model_fit["supported"] else np.nan
            extra = sum(v / E * sigma[i] for i, v in gross.items())
            base = L + risk_total(retained) / E if np.isfinite(L) else np.nan
            a = forecasts.alpha(G, base, extra) if self.method in ("R04", "R05") else 1.0
            increments = {i: a * v for i, v in raw_full.items() if a * v > 0}
            dust = {i for i, v in increments.items() if v < buy or retained.get(i, 0) + v < epsilon * (sum(core.values()) + sum(retained.values()) + sum(increments.values())) - 1e-8}
            if not dust:
                break
            rejected.update(dust)
            for i in dust:
                reasons[i] = "minimum ticket/floor"
        ext = retained.copy()
        for i, v in increments.items():
            ext[i] = ext.get(i, 0) + v
        for i in list(ext):
            if ext[i] < epsilon * (sum(core.values()) + sum(ext.values())) - 1e-8:
                del ext[i]
                reasons[i] = "global floor"
        ext = self.protect_funding(c, core, ext)
        x = core | ext
        extensions = list(ext)
        self.sleeve = set(ext)
        c["extension"] = extensions
        model = parent.CoreFirstAlpha(c["input"].timestamp, close_position_weight_epsilon=epsilon)
        model.policy = self
        model.carry_forward_non_redeemable_positions(c["pm"])
        raw = c["raw"](core_ids)
        for i in x:
            model.set_signal(c["pairs"][i], max(raw.get(i, c["score"][i]), 1e-12))
        model.select_top_signals(count=len(model.raw_signals))
        model.assign_weights(method=weight_passthrouh)
        model.update_old_weights(c["input"].state.portfolio, ignore_credit=False)
        size = USDTVLSizeRiskModel(pricing_model=c["input"].pricing_model, per_position_cap=float(p.per_position_cap_of_pool_pct))
        for i, s in model.signals.items():
            if s.carry_forward_position:
                continue
            s.position_target = float(x.get(i, 0))
            s.normalised_weight = float(x.get(i, 0)) / sum(x.values()) if sum(x.values()) else 0.0
            s.position_size_risk = size.get_acceptable_size_for_position(c["input"].timestamp, s.pair, float(x.get(i, 0)))
        model.investable_equity = B
        model.accepted_investable_equity = sum(x.values())
        model.size_risk_discarded_value = max(0, B - sum(x.values()))
        c["model"] = model
        assert sum(x.values()) <= B + 1e-6 and len(x) + len(c["locked"]) <= 12
        assert len(ext) <= 6 and all(v <= cap[i] + 1e-6 for i, v in x.items())
        assert weight_total(ext) <= cash_limit + 1e-6 and risk_total(ext) <= risk_limit + 1e-6, (t, self.method, risk_total(ext), risk_limit)
        assert all(ext[i] * factor[i] <= 0.05 * E + 1e-6 for i in ext)
        for row in self.ledger[start:]:
            i = row["Pair id"]
            row.update(Arm=self.method, Role="core" if i in core else "overflow" if i in ext else row["Role"] if row["Role"] == "pinned" else "candidate", **{"Accepted allocation (USD)": x.get(i, 0), "Final target (USD)": x.get(i, 0), "Sigma": sigma.get(i, np.nan), "Score group": groups.get(i, forecasts.group(row["Ranking score"] if row["Score available"] else np.nan)), "Net forecast": forecasts_net.get(i, np.nan), "Reason": reasons.get(i, "protected core"), "Retained target (USD)": retained.get(i, 0), "Fresh increment (USD)": increments.get(i, 0), "Hold advantage (USD)": forecast_delta.get(i, np.nan), "Risk age": rr.loc[i, "age"], "Prior only": rr.loc[i, "prior_only"], "Forecast supported": model_fit["supported"]})
        for row in self.data["nb17_decisions"][decision_start:]:
            row["Arm"] = self.method
        decision = dict(Period=self.data["run_context"][0], Arm=self.method, Date=t, Equity=E, Marked_equity=marked_equity, Valuation_equity=valuation_equity, Fee_marking_bound=core_fee_bound + sleeve_fee_bound, Anchor=A, Anchor_support=n, k=k, Core_risk=L, Target_risk=k * A, Headroom=J, Retained_risk=risk_total(retained) / E, Sleeve_risk=risk_total(ext) / E, Sleeve_gross=weight_total(ext) / E, Sleeve_target=sum(ext.values()) / E, Retained=sum(retained.values()) / E, Fresh=sum(increments.values()) / E, Full_fresh=sum(raw_full.values()) / E, Alpha=a, Advantage=G, Extra_risk=extra, Core_target=sum(core.values()), Residual=R, Forecast_supported=model_fit["supported"], Pooled_lower=model_fit["lower"], Economic_exits=sum(v == "negative hold payoff" for v in exit_reasons.values()), Hard_exits=sum(v == "hard risk/exposure" for v in exit_reasons.values()), Pinned=len(c["locked"]), Unknown_core=not known, Slots=len(ext), Core_funding_release=c.get("overflow_funding_release", 0))
        self.data["nb18_decisions"].append(decision)
        self.data["nb18_checks"].append(dict(Period=decision["Period"], Arm=self.method, Date=t, Core_preserved=all(x[i] == core[i] for i in core), Risk_valid=risk_total(ext) <= risk_limit + 1e-6, Capacity_valid=all(v <= cap[i] + 1e-6 for i, v in x.items()), Retained_counted_once=True, Slot_valid=len(x) + len(c["locked"]) <= 12))
        return model, core_ids, extensions, B, pinned, buy


def replay(data, evaluator, arm, period):
    import score_matrix

    original = score_matrix.make_matrix_decision
    values = evaluator.panel.score_values
    policy = None
    starts = {k: len(data[k]) for k in ("nb18_decisions", "nb18_checks", "nb17_core_checks", "funding_ledger")}
    data["run_context"] = (period, arm, "corrected")
    evaluator.panel.score_values = lambda *a, **kw: data["focal_values"]
    weight = np.zeros(len(FEATURES))
    weight[0] = 1

    def factory(strategy, panel, vals, sizing, allocator, ledger, **kwargs):
        nonlocal policy
        policy = ConditionalPolicy(data, strategy, arm, ledger)
        callback = parent.compile_policy(strategy, policy)

        def decide(input):
            parameters = deepcopy(input.parameters)
            parameters["max_assets_in_portfolio"] = 6
            parameters["max_capacity_assets"] = 12
            parameters["entry_rank"] = 6
            parameters["exit_rank"] = 8
            return callback(replace(input, indicators=MatrixIndicators(input.indicators, panel, vals, input.timestamp), parameters=parameters))

        return decide

    score_matrix.make_matrix_decision = factory
    try:
        with engine.pricing_convention(data):
            r = evaluator.run(weight, *PERIODS[period], n=12, sizing="inverse_variance", missing=True, keep=True, profile="NB18-" + arm)
        path = evaluator.folder / f'{r["cache_key"]}-diagnostics.json'
        if policy is None:
            assert path.exists(), "Cached state needs its mechanism ledger"
            for key, rows in json.loads(path.read_text()).items():
                data[key].extend(rows)
        else:
            path.write_text(json.dumps({k: data[k][n:] for k, n in starts.items()}, default=str))
        return r
    finally:
        score_matrix.make_matrix_decision = original
        evaluator.panel.score_values = values


def run(data, evaluator):
    records = []
    runs = {}
    attribution = {}
    weights = {}
    audits = []
    for period, arm in tqdm([(p, a) for p in PERIODS for a in METHODS], desc="NB18 corrected accounts", mininterval=15):
        print(f"{period} / {arm}; approximately {evaluator.remaining(18-len(records)):.1f} minutes remaining", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = data["control_runs"][(period, arm)] if arm.startswith("C") else replay(data, evaluator, arm, period)
        m, v, w = engine.analyse_run(data, r, arm, period)
        m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
        m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"]) if m["Maximum drawdown"] < 0 else np.nan
        reserve = r["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        sep = w.loc["2026-09-01":"2026-09-30", reserve]
        m["September cash"] = float(sep.mean()) if len(sep) else np.nan
        held = w.drop(columns=reserve)
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
        for key in ("nb18_decisions", "nb18_checks", "nb17_core_checks", "funding_ledger"):
            pd.DataFrame(data[key]).to_csv(data["artifact"] / (key + ".csv"), index=False)
    pd.concat(audits, ignore_index=True).to_csv(data["artifact"] / "fill-audit.csv", index=False)
    return pd.DataFrame(records), runs, attribution, weights
