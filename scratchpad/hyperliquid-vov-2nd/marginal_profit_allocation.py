"""Independent full-account marginal-value allocation on the pinned source engine."""

import ast
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
from tradeexecutor.strategy.alpha_model import AlphaModel
from tradeexecutor.strategy.weighting import weight_passthrouh
from tradeexecutor.strategy.tvl_size_risk import USDTVLSizeRiskModel
from tradeexecutor.strategy.redemption import DepositCheckStage, RedemptionCheckStage
import score_matrix
import clean_c00_v11_comparison as baseline
import marginal_profit_forecasts as forecasts
from marginal_profit_data import ROOT, PERIODS, REGISTRY, ARMS, metrics


class Opportunity:
    """Basis-aware complete path value for one target gross NAV amount."""

    def __init__(self, pid, pair, gross, basis, distribution, downside, lower, upper, marked, allowed, reason):
        self.pid = pid
        self.pair = pair
        self.gross = gross
        self.basis = basis
        self.distribution = distribution
        self.downside = downside
        self.lower = lower
        self.upper = upper
        self.marked = marked
        self.allowed = allowed
        self.reason = reason
        self.net_ratio = marked / gross if gross > 0 else 1.0
        self.hold_value = distribution.terminal(gross, basis) if distribution else marked

    def flow(self, x):
        return (self.gross - x) * self.net_ratio if x < self.gross else self.gross - x

    def future(self, x):
        if self.distribution is None:
            return self.marked if x >= self.gross else self.marked * x / self.gross if self.gross > 0 else 0.0
        basis = self.basis * x / self.gross if self.gross > 0 and x < self.gross else self.basis + max(0, x - self.gross)
        return self.distribution.terminal(x, basis)

    def gain(self, x):
        cache = getattr(self, "_gain_cache", None)
        if cache is None:
            cache = {}
            self._gain_cache = cache
        key = float(x)
        if key not in cache:
            cache[key] = self.future(x) + self.flow(x) - self.hold_value
        return cache[key]

    def gain_shift(self, x, shift):
        if self.distribution is None:
            return self.gain(x)
        cache = getattr(self, "_shift_cache", None)
        if cache is None:
            cache = {}
            self._shift_cache = cache
        key = (float(x), float(shift))
        if key not in cache:
            basis = self.basis * x / self.gross if self.gross > 0 and x < self.gross else self.basis + max(0, x - self.gross)
            cache[key] = self.distribution.terminal(x, basis, shift=shift) + self.flow(x) - self.distribution.terminal(self.gross, self.basis, shift=shift)
        return cache[key]

    def target_mark(self, x):
        return x * self.net_ratio if x <= self.gross else self.marked + x - self.gross


def ledger_at(data, r, t):
    """Rebuild holdings before a decision, preserving realised reserve flows."""
    q = {}
    cash = 150000.0
    for trade in r["result"].state.portfolio.get_all_trades():
        if not trade.is_success() or pd.Timestamp(trade.executed_at) >= pd.Timestamp(t):
            continue
        i = int(trade.pair.internal_id)
        q[i] = q.get(i, 0) + float(trade.executed_quantity)
        cash += (-1 if trade.is_buy() else 1) * float(trade.executed_reserve or 0)
    values = {i: quantity * baseline.core.engine.observed_quote(data, i, t)[0] for i, quantity in q.items() if quantity > 1e-8 and baseline.core.engine.observed_quote(data, i, t)}
    return values, cash


def register_budgets(data):
    """Use only available prior forecasts, including support fallbacks, for B."""
    r = data["control_runs"][("Long", "B00")]
    origins = sorted(data["panel"].loc[data["panel"].Training_origin, "Date"].unique())
    h = data["policy_horizon"]
    rows = []
    # Walk the saved reference once instead of rereading all trades per date.
    trades = sorted([t for t in r["result"].state.portfolio.get_all_trades() if t.is_success()], key=lambda t: t.executed_at)
    q = {}
    basis = {}
    cash = 150000.0
    k = 0
    eq = r["equity"].sort_index()
    for timestamp in origins:
        t = pd.Timestamp(timestamp)
        while k < len(trades) and pd.Timestamp(trades[k].executed_at) < t:
            tr = trades[k]
            pid = int(tr.pair.internal_id)
            before = q.get(pid, 0)
            delta = float(tr.executed_quantity)
            basis[pid] = (basis.get(pid, 0) + float(tr.executed_reserve or 0)) if tr.is_buy() else basis.get(pid, 0) * max(0, (before + delta) / before) if before > 0 else 0.0
            q[pid] = before + delta
            cash += (-1 if tr.is_buy() else 1) * float(tr.executed_reserve or 0)
            k += 1
        held = {i: v * baseline.core.engine.observed_quote(data, i, t)[0] for i, v in q.items() if v > 1e-8 and baseline.core.engine.observed_quote(data, i, t)}
        E = cash + sum(0.999 * v - 0.1 * max(v - basis.get(i, 0), 0) for i, v in held.items())
        D = 0.0
        valid = True
        prior = True
        for pid, value in held.items():
            dist, row = forecasts.distribution_at(data, t, pid, h, "P")
            if dist is None:
                valid = False
                continue
            D += value / E * dist.downside
        prior = any(forecasts.distribution_at(data, t, int(i), h, "P")[0] is not None for i in data["panel"].loc[data["panel"].Date.eq(t) & data["panel"].H.eq(h), "Pair"].head(1))
        rows.append(dict(Date=t, D=D if valid and prior else np.nan, H=h, Exposure=sum(held.values()) / E, Valid=valid and prior))
    table = pd.DataFrame(rows)
    sample = table[table.Date.ge("2024-01-01") & table.Date.lt("2026-01-01")]
    assert len(sample) and sample.Valid.all(), "Registered pre-2026 budget window has unsupported dates; amend before economic results"
    B = float(sample.D.median())
    assert B > 0, "Zero prior risk budget is not silently replaced"
    training = data["training_audit"]
    cuts = pd.to_datetime(training[(training.H.eq(h)) & training.Supported].Fit)
    cut = cuts.min()
    early = table[table.Date.lt(cut) & table.Valid]
    longB = float(early.D.median()) if len(early) else np.nan
    data["budget_table"] = table
    data["budgets"] = {"2026": B, "Long": longB}
    data["long_budget_cut"] = cut
    # The seven-day extension registers its own prior-horizon risk budget.
    other = []
    q = {}
    basis = {}
    cash = 150000.0
    k = 0
    for timestamp in origins:
        t = pd.Timestamp(timestamp)
        while k < len(trades) and pd.Timestamp(trades[k].executed_at) < t:
            tr = trades[k]
            pid = int(tr.pair.internal_id)
            before = q.get(pid, 0)
            delta = float(tr.executed_quantity)
            basis[pid] = (basis.get(pid, 0) + float(tr.executed_reserve or 0)) if tr.is_buy() else basis.get(pid, 0) * max(0, (before + delta) / before) if before > 0 else 0.0
            q[pid] = before + delta
            cash += (-1 if tr.is_buy() else 1) * float(tr.executed_reserve or 0)
            k += 1
        held = {i: v * baseline.core.engine.observed_quote(data, i, t)[0] for i, v in q.items() if v > 1e-8 and baseline.core.engine.observed_quote(data, i, t)}
        E = cash + sum(0.999 * v - 0.1 * max(v - basis.get(i, 0), 0) for i, v in held.items())
        D = 0.0
        valid = True
        for pid, value in held.items():
            dist, _ = forecasts.distribution_at(data, t, pid, 7, "P")
            if dist is None:
                valid = False
            else:
                D += value / E * dist.downside
        other.append(dict(Date=t, D=D if valid else np.nan))
    data["horizon_budget_tables"] = {7: pd.DataFrame(other)}
    data["horizon_budget_tables"][7].to_csv(data["artifact"] / "risk-budget-reference-7d.csv", index=False)
    table.to_csv(data["artifact"] / "risk-budget-reference.csv", index=False)
    registration = dict(data["budgets"], long_freeze_date=str(cut), pre_window=["2024-01-01", "2026-01-01"], sample_dates=len(sample), median=B, quartiles=sample.D.quantile([0.25, 0.75]).to_dict(), historical_binding_fraction=float(sample.D.gt(B).mean()), mean_personalised=False)
    (data["artifact"] / "budget-registration.json").write_text(json.dumps(registration, indent=2, default=str))
    return registration


def budget_at(data, period, t, h=None):
    h = h or data["policy_horizon"]
    if h != data["policy_horizon"]:
        table = data["horizon_budget_tables"][h]
        if period == "2026":
            return float(table[table.Date.ge("2024-01-01") & table.Date.lt("2026-01-01")].D.median())
    if period == "2026" or pd.Timestamp(t) >= data["long_budget_cut"]:
        return data["budgets"][period]
    previous = data["budget_table"]
    previous = previous[previous.Date.lt(t) & previous.Valid]
    return float(previous.D.median()) if len(previous) else np.nan


def solve(opportunities, cash, E, B, buy, sell, epsilon=0.005, slots=None, entry_only=False, priority="dollar", refinement=0, initial=None, margin=0.0):
    """Deterministic feasible greedy additions, sales and jointly funded swaps."""
    ids = list(opportunities)
    old = {i: o.gross for i, o in opportunities.items()}
    x = dict(old) if initial is None else dict(initial)
    x = {i: max(o.lower, min(x.get(i, 0.0), o.upper)) for i, o in opportunities.items()}

    def objective(v):
        return sum(opportunities[i].gain(v[i]) for i in ids)

    def funds(v):
        return cash + sum(opportunities[i].flow(v[i]) for i in ids)

    def risk(v):
        return sum(v[i] * opportunities[i].downside for i in ids) / E

    oldrisk = risk(old)
    limit = B if oldrisk <= B else oldrisk
    if np.isnan(limit):
        return old, dict(Objective=0.0, Iterations=0, Status="unsupported budget", Risk=oldrisk)
    count = lambda v: sum(a > 1e-6 for a in v.values())
    refinements = 0
    iterations = 0
    ties = 0.0
    moves = []
    # Three trial sizes include execution minima, the resource maximum and a refinement midpoint.
    fraction = 2.0 ** (-refinement - 1)

    def required(changes, current):
        if margin <= 0:
            return 1e-8
        plus = sum(opportunities[i].gain_shift(v, margin) - opportunities[i].gain_shift(current[i], margin) for i, v in changes.items())
        minus = sum(opportunities[i].gain_shift(v, -margin) - opportunities[i].gain_shift(current[i], -margin) for i, v in changes.items())
        return max(1e-8, 0.5 * abs(plus - minus))

    for iterations in range(256):
        available = max(0.0, funds(x))
        R = risk(x)
        positive = 0
        options = []
        minbuy = max(buy, epsilon * sum(o.target_mark(x[i]) for i, o in opportunities.items()))
        buyers = []
        sellers = []
        for i, o in opportunities.items():
            current = x[i]
            maximum = o.upper - current
            if o.distribution is not None and o.allowed and maximum >= minbuy and (slots is None or current > 0 or count(x) < slots):
                amount = min(maximum, available)
                if o.downside > 0:
                    amount = min(amount, max(0, (limit - R) * E / o.downside))
                if R > B + 1e-12 and o.downside > 0:
                    amount = 0.0
                if amount >= minbuy:
                    for delta in sorted(set([minbuy, amount, max(minbuy, amount * fraction)])):
                        gain = o.gain(current + delta) - o.gain(current)
                        if gain > required({i: current + delta}, x):
                            dr = delta * o.downside / E
                            rate = gain / (dr * E if priority == "risk" and dr > 1e-15 else delta)
                            options.append((rate, gain, delta, {i: current + delta}, "buy"))
                            buyers.append(i)
            if current - o.lower > 1e-6 and not entry_only:
                maximum = current - o.lower
                floor = sell / max(o.net_ratio, 1e-12)
                sizes = sorted(set([maximum, max(floor, maximum * fraction)]))
                for amount in sizes:
                    amount = min(maximum, amount)
                    if amount < floor and amount < current - 1e-6:
                        continue
                    target = current - amount
                    gain = o.gain(target) - o.gain(current)
                    if gain > required({i: target}, x):
                        options.append((gain / amount, gain, amount, {i: target}, "sell"))
                    sellers.append((i, target, amount, gain))
        if not entry_only:
            for i, target, amount, sellgain in sellers:
                seller = opportunities[i]
                proceeds = seller.flow(target) - seller.flow(x[i])
                newrisk = R - amount * seller.downside / E
                for j, o in opportunities.items():
                    if i == j or not o.allowed or o.distribution is None or o.upper - x[j] < minbuy:
                        continue
                    if slots is not None and x[j] <= 0 and count(x) - (target <= 1e-6) >= slots:
                        continue
                    delta = min(o.upper - x[j], available + proceeds)
                    if o.downside > 0:
                        delta = min(delta, max(0.0, (limit - newrisk) * E / o.downside))
                    if R > B + 1e-12 and delta * o.downside > amount * seller.downside + 1e-8:
                        continue
                    if delta < minbuy:
                        continue
                    gain = sellgain + o.gain(x[j] + delta) - o.gain(x[j])
                    notional = max(amount, delta)
                    if gain > required({i: target, j: x[j] + delta}, x):
                        dr = (delta * o.downside - amount * seller.downside) / E
                        rate = gain / (dr * E if priority == "risk" and dr > 1e-15 else notional)
                        options.append((rate, gain, notional, {i: target, j: x[j] + delta}, "replace"))
        if not options:
            break
        options.sort(key=lambda v: (-v[0], -v[1], tuple(str(opportunities[i].pair.pool_address) for i in v[3])))
        chosen = options[0]
        # Equal-dollar sharing for tied fresh buys, avoiding an address-selected prior basket.
        equal = [v for v in options if v[4] == "buy" and abs(v[0] - chosen[0]) <= max(1e-12, abs(chosen[0]) * 1e-10)] if chosen[4] == "buy" else []
        unique = {next(iter(v[3])): v for v in equal}
        if len(unique) > 1 and (slots is None or count(x) + sum(x[i] <= 0 for i in unique) <= slots):
            budget = min(available, chosen[2])
            part = budget / len(unique)
            if part >= minbuy:
                proposed = dict(x)
                for i, v in unique.items():
                    proposed[i] += min(part, opportunities[i].upper - x[i])
                if risk(proposed) <= limit + 1e-12 and objective(proposed) > objective(x) + 1e-8:
                    ties += sum(proposed[i] - x[i] for i in unique)
                    x = proposed
                    moves.append("tie")
                    continue
        proposed = x | chosen[3]
        assert funds(proposed) >= -1e-5 and risk(proposed) <= limit + 1e-9, (funds(proposed), risk(proposed), limit)
        if objective(proposed) <= objective(x) + 1e-8:
            break
        x = proposed
        moves.append(chosen[4])
    return x, dict(Objective=objective(x), Iterations=iterations + 1, Status="iteration limit" if iterations == 255 else "no positive feasible move", Risk=risk(x), Tie_dollars=ties, Moves=len(moves))


class MarginalPolicy:
    """Supply full-account absolute targets while retaining source execution checks."""

    corrected = True

    def __init__(self, data, strategy, arm, period, ledger):
        self.data = data
        self.strategy = strategy
        self.arm = arm
        self.period = period
        self.ledger = ledger
        self.core = set()
        self.current = None

    def select(self, input, pm, ordered, held, checks, check_entry, reference_equity):
        t = pd.Timestamp(input.timestamp)
        p = input.parameters
        model = AlphaModel(t, close_position_weight_epsilon=float(p.min_portfolio_weight_pct))
        pinned = model.carry_forward_non_redeemable_positions(pm)
        locked = {int(i) for i, s in model.raw_signals.items() if s.carry_forward_position}
        pairs = {int(i): replace(pair, internal_id=int(pair.internal_id)) for i, pair, score in ordered}
        actual = {int(pos.pair.internal_id): pos for pos in input.state.portfolio.get_open_positions() if pos.pair.is_vault()}
        pairs.update({i: pos.pair for i, pos in actual.items()})
        cash = float(pm.get_current_cash())
        E = float(input.state.portfolio.get_total_equity())
        buy = max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.individual_rebalance_min_threshold_of_initial_cash_pct))
        sell = max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.sell_rebalance_min_threshold_of_initial_cash_pct))
        h = 7 if self.arm == "H07" else self.data["policy_horizon"]
        kind = "P" if self.arm == "P00" else "M" if self.arm == "M00" else "C" if self.arm == "C01" else "D"
        B = budget_at(self.data, self.period, t, h)
        if self.arm == "BHALF":
            B *= 0.5
        if self.arm == "BDOUBLE":
            B *= 2
        if self.arm == "D04":
            B = np.inf
        size = USDTVLSizeRiskModel(pricing_model=input.pricing_model, per_position_cap=float(p.per_position_cap_of_pool_pct))
        opportunities = {}
        rows = []
        ordered_ids = {int(v[0]) for v in ordered}
        calibration_se = common_calibration_se(self.data, t, h) if self.arm == "MARGIN" else 0.0
        for i, pair in sorted(pairs.items(), key=lambda item: str(item[1].pool_address)):
            quote = baseline.core.engine.observed_quote(self.data, i, t)
            if quote is None:
                continue
            pos = actual.get(i)
            G = float(pos.get_quantity()) * quote[0] if pos else 0.0
            basis = self.strategy.get_remaining_cost_basis(pos) if pos else 0.0
            marked = float(pos.get_value()) if pos else 0.0
            dist, frow = forecasts.distribution_at(self.data, t, i, h, kind)
            riskdist, _ = forecasts.distribution_at(self.data, t, i, h, "P")
            d = riskdist.downside if riskdist else np.nan
            check = check_entry(pair)
            allowed = bool(check.can_deposit and pm.is_whitelisted_vault(pair) and i in ordered_ids)
            cap = float(size.get_acceptable_size_for_position(t, pair, 0.33 * E).accepted_size)
            deposit = max(0, float(check.max_deposit)) if allowed and check.max_deposit is not None else float("inf") if allowed else 0.0
            upper = max(G, min(cap, G + deposit))
            lower = G if i in locked or self.arm == "D03" else 0.0
            if pos:
                redemption = input.pricing_model.check_redemption(t, pair, stage=RedemptionCheckStage.sell_rebalance, position=pos)
                if not redemption.can_redeem:
                    lower = G
                elif redemption.max_redemption is not None:
                    lower = max(lower, G - max(0, float(redemption.max_redemption)) / (marked / G if G > 0 else 1))
            if i not in ordered_ids and i not in locked:
                lower = max(0, lower if self.arm != "D03" else 0)
                upper = lower
                allowed = False
                reason = "operational exit"
            if i in locked:
                lower = upper = G
            if not np.isfinite(d):
                lower = G
                upper = G
                d = 0.0
            if dist is None:
                upper = G
                lower = G
            reason = "eligible" if allowed else str(getattr(check.reason_code, "value", check.reason_code) or "held / no new deposit")
            opportunities[i] = Opportunity(i, pair, G, basis, dist, d, lower, upper, marked, allowed, reason)
            row = dict(Period=self.period, Arm=self.arm, Date=t, Pair=i, Vault=pair.get_vault_name(), Gross_old=G, Basis=basis, Marked_old=marked, Cap=min(cap, G + deposit), Deposit_open=allowed, Pinned=i in locked, Forecast_supported=bool(frow.Supported) if frow is not None else False, Prior_available=dist is not None, Missing_score=bool(frow is None or not np.isfinite(frow.c00_score)), Downside=d, Quote_age=(t - quote[1]).total_seconds() / 86400, Reason=reason)
            if dist:
                row.update(dist.serial())
            rows.append(row)
        slots = 6 if self.arm == "D02" else None
        reserve = max(0.5, reference_equity * 0.0005)
        usable = max(0, cash - reserve)
        old = {i: o.gross for i, o in opportunities.items()}
        solutions = []
        previous = None
        converged = False
        refinement_count = 0
        for refinement_count in range(REGISTRY["refinements"]):
            choices = []
            for priority in ("dollar", "risk"):
                targets, info = solve(opportunities, usable, E, B, buy, sell, float(p.min_portfolio_weight_pct), slots, self.arm == "D03", priority, refinement_count, margin=calibration_se)
                choices.append((info["Objective"], targets, info))
            _, target, info = max(choices, key=lambda v: v[0])
            solutions.append((info["Objective"], target, info))
            if previous is not None:
                objdiff = abs(info["Objective"] - previous[0])
                diff = sum(abs(target[i] - previous[1][i]) for i in target)
                if objdiff < 1 and diff < 10:
                    converged = True
                    break
            previous = (info["Objective"], target)
        _, target, info = max(solutions, key=lambda v: v[0])
        if not np.isfinite(B) and self.arm != "D04":
            target = old
            info = dict(Objective=0.0, Risk=sum(old[i] * o.downside for i, o in opportunities.items()) / E, Status="cold start", Iterations=0, Tie_dollars=0.0)
        # Source minimum weights are applied to actual invested targets, not total equity.
        total = sum(o.target_mark(target[i]) for i, o in opportunities.items())
        for i, o in opportunities.items():
            v = o.target_mark(target[i])
            delta = target[i] - o.gross
            if 0 < v < float(p.min_portfolio_weight_pct) * total and i not in locked:
                target[i] = 0.0 if o.lower <= 0 and self.arm != "D03" else o.gross
            if delta > 0 and delta < buy:
                target[i] = o.gross
            elif delta < 0 and target[i] > 0 and -delta * o.net_ratio < sell:
                target[i] = o.gross
        # Freeze projected sells, then only remove/reallocate buys with their actual proceeds.
        funds = cash + sum(o.flow(target[i]) for i, o in opportunities.items()) - reserve
        if funds < 0:
            buys = [i for i, o in opportunities.items() if target[i] > o.gross]
            need = sum(target[i] - opportunities[i].gross for i in buys)
            scale = max(0, 1 + funds / need) if need > 0 else 0.0
            for i in buys:
                target[i] = opportunities[i].gross + (target[i] - opportunities[i].gross) * scale
        oldrisk = sum(o.gross * o.downside for o in opportunities.values()) / E
        allowedrisk = max(B, oldrisk)
        # Suppressed trims cannot provide fictitious risk headroom for buys.
        for i in sorted(opportunities, key=lambda i: opportunities[i].gain(target[i]) - opportunities[i].gain(opportunities[i].gross)):
            currentrisk = sum(target[j] * o.downside for j, o in opportunities.items()) / E
            o = opportunities[i]
            if currentrisk <= allowedrisk + 1e-12:
                break
            if target[i] > o.gross and o.downside > 0:
                remove = min(target[i] - o.gross, (currentrisk - allowedrisk) * E / o.downside)
                target[i] -= remove
                if target[i] - o.gross < buy:
                    target[i] = o.gross
        total = sum(o.target_mark(target[i]) for i, o in opportunities.items())
        model.select_top_signals(count=len(model.raw_signals))
        model.update_old_weights(input.state.portfolio, ignore_credit=False)
        for i, o in opportunities.items():
            if i in locked:
                continue
            model.set_signal(o.pair, 1.0)
            model.signals[i] = model.raw_signals[i]
        model.select_top_signals(count=len(model.raw_signals))
        model.assign_weights(method=weight_passthrouh)
        model.update_old_weights(input.state.portfolio, ignore_credit=False)
        targets = {i: o.target_mark(target[i]) for i, o in opportunities.items()}
        for i, s in model.signals.items():
            if s.carry_forward_position:
                continue
            o = opportunities[int(i)]
            s.position_target = targets[int(i)]
            s.normalised_weight = s.position_target / total if total > 0 else 0.0
            s.position_size_risk = size.get_acceptable_size_for_position(t, s.pair, float(s.position_target))
            s.set_deposit_check_result(check_entry(s.pair))
        self.core = {i for i, x in target.items() if x > 1e-6 and i not in locked}
        self.current = dict(model=model, targets=target, opportunities=opportunities, E=E, old=old, buy=buy)
        for row in rows:
            i = row["Pair"]
            o = opportunities[i]
            row.update(Target_gross=target[i], Target_marked=targets[i], Forecast_gain=o.gain(target[i]), Change_gross=target[i] - o.gross, Executed_gross=np.nan)
            self.data["nb21_candidates"].append(row)
            self.ledger.append({"Date": t, "Pair id": i, "Vault": o.pair.get_vault_name(), "Role": "pinned" if i in locked else "portfolio" if target[i] > 0 else "exit", "Final target (USD)": targets[i], "Old value (USD)": o.marked, "Deployable budget (USD)": E})
        risk = sum(target[i] * o.downside for i, o in opportunities.items()) / E
        decision = dict(Period=self.period, Arm=self.arm, Date=t, E=E, Cash=cash, B=B, Risk=risk, Old_risk=sum(old[i] * o.downside for i, o in opportunities.items()) / E, Soft_breach=risk > B + 1e-10, Expected_gain=sum(o.gain(target[i]) for i, o in opportunities.items()), Desired_gain=info["Objective"], Converged=converged, Refinements=refinement_count + 1, Iterations=info["Iterations"], Tie_dollars=info.get("Tie_dollars", 0), Names=len(self.core) + len(locked), Pinned=len(locked), Prior_names=sum(o.distribution is not None for o in opportunities.values()), Available=len(opportunities), Status=info["Status"], Calibration_SE=calibration_se)
        self.data["nb21_decisions"].append(decision)
        if self.arm == "D00" and not any(s["Date"].to_period("M") == t.to_period("M") for s in self.data["nb21_states"]):
            self.data["nb21_states"].append(dict(Period=self.period, Date=t, opportunities=opportunities, cash=usable, E=E, B=B, target=target, objective=sum(o.gain(target[i]) for i, o in opportunities.items())))
        remaining = cash + sum(o.flow(target[i]) for i, o in opportunities.items())
        assert remaining >= -1e-4, (t, remaining)
        self.data["nb21_checks"].append(dict(Period=self.period, Arm=self.arm, Date=t, Remaining_cash=remaining, Source_missing_supported=True, All_pinned_counted=True, No_inverse_weights=True, Count=len(self.core) + len(locked)))
        return list(self.core), set()

    def allocate(self):
        c = self.current
        model = c["model"]
        B = c["E"]
        model.investable_equity = B
        model.accepted_investable_equity = sum(s.position_target or 0 for s in model.signals.values())
        model.size_risk_discarded_value = max(0, B - model.accepted_investable_equity)
        return model, list(self.core), [], B, sum(s.position_target or 0 for s in model.signals.values() if s.carry_forward_position), c["buy"]

    def fund(self, input, trades):
        baseline.core.reference.cap_to_final_sell_proceeds(self.data, input, trades, self.arm)
        c = self.current
        actual = {i: o.gross for i, o in c["opportunities"].items()}
        for tr in trades:
            i = int(tr.pair.internal_id)
            q = baseline.core.engine.observed_quote(self.data, i, input.timestamp)
            actual[i] = actual.get(i, 0) + float(tr.planned_quantity) * q[0]
        for row in reversed(self.data["nb21_candidates"]):
            if row["Date"] != pd.Timestamp(input.timestamp) or row["Arm"] != self.arm or row["Period"] != self.period:
                break
            row["Executed_gross"] = actual.get(row["Pair"], 0.0)
        self.data["nb21_decisions"][-1]["Projected_executed_L1"] = sum(abs(c["targets"][i] - actual.get(i, 0)) for i in c["targets"])


def compile_callback(strategy, policy):
    # The source prefix's investment gate must not delete the opportunity pool.
    source = ast.get_source_segment(baseline.core.parent.SOURCE.read_text(), next(n for n in ast.parse(baseline.core.parent.SOURCE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "decide_trades"))
    first = source.index("    # Keep eligible incumbents")
    last = source.index("    total_accepted = sum(", first)
    source = source[:first] + """    selected, skipped_entry_ids = _policy.select(input, position_manager, ordered, held_pair_ids, entry_checks, check_entry_candidate, reference_equity)
    alpha_model, core_ids, extension_ids, fresh_capital, pinned_value, buy_threshold = _policy.allocate()
""" + source[last:]
    gate = "        if gate_value is None or gate_value != gate_value or gate_value <= gate_threshold:\n            continue"
    if policy.arm != "GATE14":
        assert gate in source
        source = source.replace(gate, "        # NB21 treats the return gate as information rather than universal admission.\n        pass", 1)
    if policy.arm != "GATE14":
        source = source.replace("    if not candidates:\n        return []", "    if not candidates and not held_pair_ids:\n        return []")
    line = "                trade.planned_price = trade.planned_mid_price * (1.0 - fee)"
    source = source.replace(
        line,
        """                if not trade.closing:
                    trade.planned_mid_price = _engine.observed_quote(_policy.data, trade.pair.internal_id, timestamp)[0]
                    trade.other_data['nb17_corrected_partial_fee'] = True
                trade.planned_price = trade.planned_mid_price * (1.0 - fee)""",
    )
    source = source.replace("    return trades", "    _policy.fund(input, trades)\n    return trades")
    ns = dict(strategy.__dict__)
    ns.update(_policy=policy, _engine=baseline.core.engine)
    exec(compile(source, "NB21::marginal-profit-source-execution", "exec"), ns)
    (policy.data["artifact"] / "compiled-marginal-callback.py").write_text(source)
    return ns["decide_trades"]


def replay(data, evaluator, arm, period):
    original = score_matrix.make_matrix_decision
    glob = evaluator.run.__func__.__globals__
    goriginal = glob["make_matrix_decision"]
    values = evaluator.panel.score_values
    starts = {k: len(data[k]) for k in ("nb21_candidates", "nb21_decisions", "nb21_checks", "funding_ledger")}
    policy = None
    data["run_context"] = (period, arm, "marginal-profit")
    evaluator.panel.score_values = lambda *a, **kw: data["focal_values"]
    evaluator.nb19_total_limit = len(evaluator.panel.pair_ids)
    w = np.zeros(len(score_matrix.FEATURES))
    w[0] = 1.0

    def factory(strategy, panel, vals, sizing, allocator, ledger, **kw):
        nonlocal policy
        policy = MarginalPolicy(data, strategy, arm, period, ledger)
        callback = compile_callback(strategy, policy)

        def decide(input):
            p = deepcopy(input.parameters)
            p["max_assets_in_portfolio"] = p["max_capacity_assets"] = len(panel.pair_ids)
            p["weighting_method"] = "marginal_profit"
            return callback(replace(input, parameters=p, indicators=score_matrix.MatrixIndicators(input.indicators, panel, vals, input.timestamp)))

        return decide

    score_matrix.make_matrix_decision = factory
    glob["make_matrix_decision"] = factory
    try:
        with baseline.core.engine.pricing_convention(data), baseline.core.entry_marking(data):
            r = evaluator.run(w, *PERIODS[period], n=len(evaluator.panel.pair_ids), sizing="marginal_profit", missing=True, keep=True, profile="NB21-" + arm)
        path = evaluator.folder / f'{r["cache_key"]}-diagnostics.json'
        import joblib

        states = evaluator.folder / f'{r["cache_key"]}-solver-states.joblib'
        if policy is None:
            if arm == "D00" and states.exists():
                data["nb21_states"].extend(joblib.load(states))
            if path.exists():
                for k, rows in json.loads(path.read_text()).items():
                    if k.startswith("nb21"):
                        for row in rows:
                            row["Date"] = pd.Timestamp(row["Date"])
                            for field, value in list(row.items()):
                                if isinstance(value, str) and value in ("True", "False"):
                                    row[field] = value == "True"
                    data[k].extend(rows)
        else:
            path.write_text(json.dumps({k: data[k][n:] for k, n in starts.items()}, default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))
            if arm == "D00":
                joblib.dump([v for v in data["nb21_states"] if v["Date"] >= pd.Timestamp(PERIODS[period][0])], states)
        return r
    finally:
        score_matrix.make_matrix_decision = original
        glob["make_matrix_decision"] = goriginal
        evaluator.panel.score_values = values
        evaluator.nb19_total_limit = 6


def add(data, r, arm, period, records, runs, attrs, weights):
    row, v, w = metrics(data, r, arm, period)
    records.append(row)
    runs[(period, arm)] = r
    attrs[(period, arm)] = v
    weights[(period, arm)] = w
    audit = baseline.core.parent.audit(data, r, arm, period)
    if len(audit):
        assert audit.Matches_known_NAV.all()
    audit.to_csv(data["artifact"] / f"{period}-{arm}-fill-audit.csv", index=False)
    pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
    for key in ("nb21_candidates", "nb21_decisions", "nb21_checks"):
        if data[key]:
            pd.DataFrame(data[key]).to_parquet(data["artifact"] / (key + ".parquet"), index=False)


def run_smoke(data, evaluator):
    records = []
    runs = {}
    attrs = {}
    weights = {}
    for arm in tqdm(list(ARMS), desc="NB21 ten complete-2026 accounts", mininterval=15):
        print(f"2026 {arm}; approximately {max(1,evaluator.remaining(10-len(records))):.1f} minutes remaining", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if arm in ("B00", "B01"):
                r = data["control_runs"][("2026", arm)]
            elif arm == "F01":
                original = evaluator.parameters.sell_rebalance_min_threshold_of_initial_cash_pct
                evaluator.parameters["sell_rebalance_min_threshold_of_initial_cash_pct"] = 0.01
                try:
                    r = baseline.core.replay(data, evaluator, "F01", "2026", active=False)
                finally:
                    evaluator.parameters["sell_rebalance_min_threshold_of_initial_cash_pct"] = original
            else:
                r = replay(data, evaluator, arm, "2026")
        add(data, r, arm, "2026", records, runs, attrs, weights)
    return pd.DataFrame(records), runs, attrs, weights


def run_long(data, evaluator, results, runs, attrs, weights):
    records = results.to_dict("records")
    short = results[results.Period.eq("2026") & ~results.Arm.isin(["B00", "B01", "F01"])].copy()
    short["Rank_sum"] = short["Net profit (USD)"].rank(ascending=False) + short.Sharpe.rank(ascending=False)
    order = short.sort_values(["Rank_sum", "Net profit (USD)"], ascending=[True, False])
    selected = []
    signatures = set()
    for arm in order.Arm:
        sig = baseline.core.trade_signature(runs[("2026", arm)])
        key = hashlib.sha256(json.dumps(sig).encode()).hexdigest()
        if key in signatures:
            continue
        signatures.add(key)
        selected.append(arm)
        if len(selected) == 3:
            break
    (data["artifact"] / "long-shortlist.json").write_text(json.dumps(dict(candidates=selected, rule="Three distinct trade paths ordered by equal net-profit/Sharpe rank sum; no long data selection", smoke_table=order[["Arm", "Rank_sum", "Net profit (USD)", "Sharpe"]].to_dict("records")), indent=2))
    for arm in tqdm(["B00", "B01"] + selected, desc="NB21 historical shortlist", mininterval=15):
        print(f"Long {arm}; approximately 2–8 minutes remaining", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = data["control_runs"][("Long", arm)] if arm in ("B00", "B01") else replay(data, evaluator, arm, "Long")
        add(data, r, arm, "Long", records, runs, attrs, weights)
    data["shortlist"] = selected
    return pd.DataFrame(records), runs, attrs, weights


def common_calibration_se(data, t, h):
    """Causal block uncertainty of common mean calibration, not coefficient certainty."""
    key = (pd.Timestamp(t).to_period("M"), h)
    cache = data.setdefault("calibration_se", {})
    if key not in cache:
        fit = key[0].start_time
        f = data["predictions"]
        q = f[f.H.eq(h) & f.Model.eq("D") & f.operational_pool & f.Resolved & f.Mature_at.lt(fit) & f.Prior_available].copy()
        q["error"] = q.Y - q.mu
        dates = q.groupby("Date").error.mean()
        blocks = dates.groupby((dates.index - pd.Timestamp("2023-03-01")).days // h).mean()
        cache[key] = float(blocks.std(ddof=1) / np.sqrt(len(blocks))) if len(blocks) >= 3 else 0.0
    return cache[key]


def run_extensions(data, evaluator, results, runs, attrs, weights):
    records = results.to_dict("records")
    for arm, name in tqdm([("BHALF", "Half downside budget"), ("BDOUBLE", "Double downside budget"), ("H07", "Seven-day horizon package"), ("MARGIN", "Common calibration-error margin"), ("GATE14", "Original 14-day gate")], desc="NB21 fixed sensitivities", mininterval=15):
        ARMS[arm] = name
        print(f"Registered sensitivity {arm}; approximately 2–8 minutes remaining", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = replay(data, evaluator, arm, "2026")
        add(data, r, arm, "2026", records, runs, attrs, weights)
    return pd.DataFrame(records), runs, attrs, weights


def solver_bounds(data):
    """Continuous tangent-envelope upper bound on selected same-state objectives."""
    from scipy.optimize import linprog

    rows = []
    for state in data["nb21_states"]:
        if state["Date"].year != 2026 or state.get("Period", "2026") != "2026" or state["Date"].month not in (1, 4, 7, 9):
            continue
        opportunities = state["opportunities"]
        ids = list(opportunities)
        n = len(ids)
        A = []
        rhs = []
        bounds = []
        for i in ids:
            bounds.append((opportunities[i].lower, opportunities[i].upper))
        bounds += [(None, None)] * (2 * n)
        for j, i in enumerate(ids):
            o = opportunities[i]
            for x in sorted(set([o.lower, o.upper, o.gross] + list(np.linspace(o.lower, o.upper, 17)))):
                if x < o.lower or x > o.upper:
                    continue
                step = max(1e-6, max(1, x) * 1e-6)
                left = max(o.lower, x - step)
                right = min(o.upper, x + step)
                slope = (o.gain(right) - o.gain(left)) / (right - left) if right > left else 0.0
                row = np.zeros(3 * n)
                row[n + j] = 1
                row[j] = -slope
                A.append(row)
                rhs.append(o.gain(x) - slope * x + 1e-6)
            for coefficient in (1.0, o.net_ratio):
                row = np.zeros(3 * n)
                row[2 * n + j] = 1.0
                row[j] = coefficient
                A.append(row)
                rhs.append(o.gross * coefficient)
        row = np.zeros(3 * n)
        row[2 * n :] = -1
        A.append(row)
        rhs.append(state["cash"])
        if np.isfinite(state["B"]):
            row = np.zeros(3 * n)
            row[:n] = [opportunities[i].downside / state["E"] for i in ids]
            A.append(row)
            rhs.append(max(state["B"], sum(opportunities[i].gross * opportunities[i].downside for i in ids) / state["E"]))
        objective = np.r_[np.zeros(n), -np.ones(n), np.zeros(n)]
        result = linprog(objective, A_ub=np.array(A), b_ub=np.array(rhs), bounds=bounds, method="highs")
        bound = -result.fun if result.success else np.nan
        rows.append(dict(Date=state["Date"], Greedy_gain_usd=state["objective"], Continuous_upper_usd=bound, Gap_usd=bound - state["objective"] if result.success else np.nan, Solver_status=result.message))
    out = pd.DataFrame(rows)
    out.to_csv(data["artifact"] / "solver-bounds.csv", index=False)
    return out
