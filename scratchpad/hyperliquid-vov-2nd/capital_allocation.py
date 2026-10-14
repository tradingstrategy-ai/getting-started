"""Frozen full-engine capital-allocation experiment 17."""

import ast
import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm_loggable.auto import tqdm

import waterfall_comparison as reference
import profitable_allocation as engine
from allocation_followup import risk_at
from portfolio_snapshot_construction import risk_weights
from score_matrix import FEATURES, MatrixIndicators
from tradeexecutor.strategy.alpha_model import AlphaModel, TradingPairSignalFlags, SellExecutionClassification
from tradeexecutor.strategy.weighting import weight_passthrouh
from tradeexecutor.strategy.tvl_size_risk import USDTVLSizeRiskModel
from capital_allocation_methods import ARMS, METHODS, OVERFLOW, LIMITS, NUMERICAL, waterfall, proportional, floors, score_lp, joint, mechanism_checks

ROOT = engine.ROOT
PERIODS = engine.PERIODS
LABELS = engine.LABELS
NOTEBOOK = ROOT / "17-backtest-capacity-aware-allocation.ipynb"
SOURCE = Path("/Users/moo/code/strategies/strategy/hyper-ai-v11.py")


def initialise():
    """Verify the NB16 identities and isolate implementation from report caches."""
    data, evaluator = reference.initialise()
    nb = json.loads((ROOT / "16-backtest-waterfall-allocation-vs-v11.ipynb").read_text())
    previous = Path(nb["metadata"]["nb16"]["artifact_generation"])
    saved = json.loads((previous / "manifest.json").read_text())["identity"]
    current = json.loads(json.dumps(data["manifest"]["identity"], default=str))
    assert saved["nb15"] == current["nb15"], "NB16 data/source/framework identity changed"
    files = ["capital_allocation.py", "capital_allocation_methods.py"]
    identity = {"version": "nb17-v1", "nb16_inputs": saved["nb15"], "arms": METHODS, "numerical": NUMERICAL, "code": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in files}, "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/17" / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=fingerprint, nb16_reference=previous, figures=[], risk_cache={}, risk_ledger=[], quote_queries={}, run_context=None, funding_ledger=[], nb17_risk={}, nb17_decisions=[], nb17_targets=[], nb17_solvers=[], nb17_core_checks=[])
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    evaluator.values.clear()
    data["manifest"] = {"identity": identity, "framework": data["framework_commits"], "periods": {p: list(map(str, v)) for p, v in PERIODS.items()}, "nb16_reference": str(previous), "warmup": "All available preceding history; no pre-inception fill", "limitations": ["Researched overlapping periods", "Retrospective universe/guard", "Sparse NAV does not prove executable NAV", "Legacy fee convention primary; corrected partial-fee sensitivity separate"], "implementation": "Compiled pinned source prefix/tail, explicit selection/target policy hooks; original source remains untouched"}
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    checks = mechanism_checks()
    (folder / "algebra-checks.json").write_text(json.dumps(checks, indent=2))
    return data, evaluator


class CoreFirstAlpha(AlphaModel):
    """Preserve the source's executable-sell classification and fund core first."""

    def _cap_buys_by_realisable_sync_cash(self, position_manager, current_positions, redemption_results, frozen_pairs, individual_rebalance_min_threshold, sell_rebalance_min_threshold, sync_cash_headroom_usd):
        originals = {i: float(v.position_adjust_usd) for i, v in self.signals.items() if v.position_adjust_usd > 0 and not v.position_adjust_ignored}
        super()._cap_buys_by_realisable_sync_cash(position_manager, current_positions, redemption_results, frozen_pairs, individual_rebalance_min_threshold, sell_rebalance_min_threshold, sync_cash_headroom_usd)
        if self.policy.arm not in OVERFLOW:
            return
        executable = [v for v in self.iterate_signals() if v.pair.internal_id in originals and self._is_executable_cash_spending_buy(v, position_manager, current_positions, frozen_pairs, individual_rebalance_min_threshold)]
        marked_budget = sum(float(v.position_adjust_usd) for v in executable)
        # Source partial trims apply a second fee to the marked price. Reserve
        # that concrete expected deduction before creating any trade objects.
        deduction = 0.0
        sync_sales = 0.0
        for v in self.iterate_signals():
            if v.position_adjust_usd >= 0 or v.position_adjust_ignored:
                continue
            if position_manager.is_async_vault_sell_pair(v.pair, position_pair=v.synthetic_pair or v.pair):
                continue
            classification = self._classify_sell_execution(v, position_manager, current_positions, redemption_results, frozen_pairs, individual_rebalance_min_threshold, sell_rebalance_min_threshold)
            if classification is SellExecutionClassification.executes_and_funds:
                sync_sales += abs(v.position_adjust_usd)
            if classification is SellExecutionClassification.executes_and_funds and not self._is_full_close_intent(v) and not self.policy.corrected:
                fee = position_manager.pricing_model._vault_redemption_fee_by_pair_id.get(v.pair.internal_id, 0.0)
                deduction += abs(v.position_adjust_usd) * fee
        budget = min(sum(originals[v.pair.internal_id] for v in executable), max(0.0, self._available_same_cycle_cash(position_manager) + sync_sales - sync_cash_headroom_usd - deduction))
        core = [v for v in executable if v.pair.internal_id in self.policy.core]
        extra = [v for v in executable if v not in core]
        core_request = sum(originals[v.pair.internal_id] for v in core)
        core_funded = min(core_request, budget)
        for group, limit in [(core, core_funded), (extra, max(0.0, budget - core_funded))]:
            requested = sum(originals[v.pair.internal_id] for v in group)
            for v in group:
                v.position_adjust_usd = originals[v.pair.internal_id] * min(1.0, limit / requested) if requested else 0.0
                if v.position_adjust_usd < originals[v.pair.internal_id]:
                    v.flags.add(TradingPairSignalFlags.capped_by_sync_cash)
        assert abs(sum(v.position_adjust_usd for v in core) - core_funded) < 1e-6
        assert core_funded >= self.policy.current.get("core_expected_funded", 0.0) - 1e-6, (self.timestamp, core_funded, self.policy.current.get("core_expected_funded"))
        self.policy.data["nb17_core_checks"].append(dict(Period=self.policy.data["run_context"][0], Arm=self.policy.arm, Date=self.timestamp, Pair="funding", Core_requested=core_request, Core_funded=core_funded, Independent_funding_shortfall=max(0.0, core_request - self.policy.current.get("core_expected_funded", core_request)), Shadow_core_funded=self.policy.current.get("core_expected_funded", core_funded), Expected_partial_fee=deduction))


class Policy:
    """Own core membership and target decisions within one independent account."""

    def __init__(self, data, strategy, arm, ledger, corrected=False):
        self.data = data
        self.strategy = strategy
        self.arm = arm
        self.ledger = ledger
        self.corrected = corrected
        self.core = set()
        self.exit_previous = set()
        self.current = None

    def select(self, input, pm, ordered, held, checks, check_entry, reference_equity):
        """Apply exact source hysteresis, separating roles only for overflow policies."""
        p = input.parameters
        t = pd.Timestamp(input.timestamp)
        ordered = [(int(i), replace(pair, internal_id=int(pair.internal_id)), float(s)) for i, pair, s in ordered]
        pairs = {i: pair for i, pair, s in ordered}
        score = {i: s for i, pair, s in ordered}
        addr = {i: str(pair.pool_address).lower() for i, pair, s in ordered}
        rank = {i: k + 1 for k, (i, pair, s) in enumerate(ordered)}
        model = CoreFirstAlpha(input.timestamp, close_position_weight_epsilon=p.min_portfolio_weight_pct)
        model.policy = self
        pinned = model.carry_forward_non_redeemable_positions(pm)
        locked = {i for i, s in model.raw_signals.items() if s.carry_forward_position}
        B = float(self.strategy.calculate_v11_fresh_deployable_capital(pm, pinned, float(p.allocation_pct)))
        buy = max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.individual_rebalance_min_threshold_of_initial_cash_pct))
        sell = max(float(p.absolute_min_vault_deposit_usd), reference_equity * float(p.sell_rebalance_min_threshold_of_initial_cash_pct))
        old = {i: float(pos.get_value()) for i in pairs for pos in [pm.get_current_position_for_pair(pairs[i])] if pos is not None}
        old = {i: old.get(i, 0.0) for i in pairs}
        sr = USDTVLSizeRiskModel(pricing_model=input.pricing_model, per_position_cap=float(p.per_position_cap_of_pool_pct))
        cap = {}
        tvlcap = {}
        deposit = {}
        reasons = {}
        reported = {}
        for i, pair, s in ordered:
            check = check_entry(pair)
            allowed = check.can_deposit and pm.is_whitelisted_vault(pair)
            amount = check.max_deposit
            headroom = max(0.0, float(amount)) if allowed and amount is not None else float("inf") if allowed else 0.0
            reported[i] = float(amount) if amount is not None else np.nan
            ceiling = float(sr.get_acceptable_size_for_position(input.timestamp, pair, float(p.max_concentration_pct) * B).accepted_size)
            tvlcap[i] = ceiling
            deposit[i] = headroom
            cap[i] = min(ceiling, old[i] + headroom)
            if i in locked:
                cap[i] = 0.0
            reasons[i] = "accepted" if allowed else "guard" if not pm.is_whitelisted_vault(pair) else str(getattr(check.reason_code, "value", check.reason_code))
        incumbent = (self.core & held) if self.arm in OVERFLOW else held
        best = max([s for i, pair, s in ordered if i not in incumbent and rank[i] <= int(p.entry_rank)], default=-np.inf)
        retained = {i for i in incumbent if i in rank and rank[i] <= int(p.exit_rank) and not best > score[i] + float(p.minimum_score_improvement)}
        core_limit = (10 if self.arm == "M13" else 6) - len(locked)
        core_limit = max(0, core_limit)
        selected = []
        skipped = set()
        for i, pair, s in ordered:
            if i in retained and i not in locked and len(selected) < core_limit:
                selected.append(i)
        for i, pair, s in ordered:
            if len(selected) >= core_limit:
                break
            if i in selected or i in locked:
                continue
            if i not in held and not checks[i].can_deposit:
                skipped.add(i)
                continue
            selected.append(i)
        shadow = selected.copy()
        eligible = set(pairs) - locked
        outgoing = (held - set(shadow)) & eligible
        delayed = 0
        if self.arm == "M10":
            protected = sorted(outgoing - self.exit_previous, key=lambda i: (-score[i], addr[i]))
            selected = (protected + [i for i in shadow if i not in protected])[:core_limit]
            delayed = len(set(selected) & set(protected))
            self.exit_previous = outgoing
        key = (t, tuple(sorted(pairs)))
        if key not in self.data["nb17_risk"]:
            self.data["nb17_risk"][key] = risk_at(self.data, t, list(pairs)).set_index("pair_id")
        risks = self.data["nb17_risk"][key].reindex(list(pairs)).copy()

        def raw(ids):
            if not ids:
                return {}
            w, r = engine.research_weights(self.data, t, ids, "regular")
            for i in ids:
                for column in r.columns:
                    if column in risks.columns:
                        risks.loc[i, column] = r.loc[i, column]
            return {int(i): float(v) for i, v in w.items()}

        available = {i: np.isfinite(input.indicators.get_indicator_value("matrix_score", pair=pair)) for i, pair, s in ordered}
        c = dict(reference_equity=reference_equity, input=input, pm=pm, p=p, t=t, pairs=pairs, score=score, addr=addr, rank=rank, old=old, model=model, pinned=pinned, locked=locked, B=B, buy=buy, sell=sell, cap=cap, tvlcap=tvlcap, deposit=deposit, reason=reasons, reported=reported, risk=risks, raw=raw, held=held, incumbent=incumbent, shadow=shadow, selected=selected, core_limit=core_limit, available=available, retained=retained, delayed=delayed, reversed=0, objective=np.nan, iterations=0, core_floor_lost=0.0, floor_removed=[], extension=[])
        if self.arm == "M07":
            while True:
                base = min(B, sum(cap[i] for i in selected))
                poss = []
                for i in outgoing - set(selected):
                    if rank[i] > int(p.exit_rank):
                        continue
                    for j in set(selected) - held:
                        gain = min(B, sum(cap[k] for k in selected if k != j) + cap[i]) - base
                        if gain > 1e-6:
                            poss.append((gain, -abs(old[i] - cap[i]) - old[j], addr[i], addr[j], i, j))
                if not poss:
                    break
                _, _, _, _, i, j = sorted(poss, key=lambda v: (-v[0], -v[1], v[2], v[3]))[0]
                selected[selected.index(j)] = i
                c["reversed"] += 1
        if self.arm == "M08" and B > 0:

            def trial(ids):
                x, _ = floors(ids, lambda active: score_lp(active, cap, score, old, B, addr), cap, old, buy, float(p.min_portfolio_weight_pct))
                return x, sum(score[i] * v for i, v in x.items()) / B

            x, J = trial(selected)
            visited = {tuple(sorted(selected))}
            while True:
                best_swap = None
                for i in eligible - set(selected):
                    if old[i] == 0 and (not checks[i].can_deposit or cap[i] < buy):
                        continue
                    for j in selected:
                        trial_ids = [k for k in selected if k != j] + [i]
                        key = tuple(sorted(trial_ids))
                        if key in visited:
                            continue
                        xx, jj = trial(trial_ids)
                        if jj > J + NUMERICAL["objective_tolerance"]:
                            turn = sum(abs(xx.get(k, 0) - old[k]) for k in eligible)
                            candidate = (jj, -turn, addr[i], addr[j], trial_ids, xx)
                            if best_swap is None or (-candidate[0], -candidate[1], candidate[2], candidate[3]) < (-best_swap[0], -best_swap[1], best_swap[2], best_swap[3]):
                                best_swap = candidate
                if best_swap is None:
                    break
                J, _, _, _, selected, x = best_swap
                visited.add(tuple(sorted(selected)))
                c["iterations"] += 1
            c["greedy_targets"] = x
            c["objective"] = J
        c["selected"] = selected
        self.current = c
        return [(i, pairs[i], score[i]) for i in selected], skipped

    def protect_funding(self, c, core, extension):
        """Release maintained overflow until the independently funded core fits."""
        fees = c["input"].pricing_model._vault_redemption_fee_by_pair_id
        positions = {int(p.pair.internal_id): p for p in c["input"].state.portfolio.get_open_positions() if not p.pair.is_credit_supply()}
        cash = float(c["pm"].get_current_cash())
        headroom = max(0.50, c["reference_equity"] * 0.0005)

        def funding(target):
            proceeds = 0.0
            for i, pos in positions.items():
                if i in c["locked"] or c["pm"].is_problematic_pair(pos.pair):
                    continue
                old = float(pos.get_value())
                final = float(target.get(i, 0.0))
                reduction = old - final
                if reduction <= 0 or (final > 0 and reduction < c["sell"]):
                    continue
                if c["pm"].is_async_vault_sell_pair(pos.pair, position_pair=pos.pair):
                    continue
                net = reduction * (1 - fees.get(i, 0.0)) if final > 0 and not self.corrected else reduction
                proceeds += net
            return max(0.0, cash + proceeds - headroom)

        requested = sum(max(0.0, v - c["old"][i]) for i, v in core.items() if v - c["old"][i] >= c["buy"])
        expected = min(requested, funding(core))
        ext = extension.copy()
        released = 0.0
        for _ in range(len(ext) + 1):
            actual = funding(core | ext)
            if actual >= expected - 1e-6:
                break
            # Only retained overflow can withhold redemption proceeds. A new
            # overflow buy is already subordinate in the executable guard.
            held = [i for i in ext if c["old"][i] > 0]
            if not held:
                raise RuntimeError("Core funding constraint cannot be restored by overflow")
            i = min(held, key=lambda i: (fees.get(i, 0.0) if self.arm == "M09" else 0.0, c["score"][i], c["addr"][i]))
            old = c["old"][i]
            already = max(0.0, old - ext[i])
            fee = 0.0 if self.corrected else fees.get(i, 0.0)
            cut = min(ext[i], max((expected - actual) / (1 - fee), max(0.0, c["sell"] - already)))
            before = ext[i]
            ext[i] -= cut
            if ext[i] < 0.005 * (sum(core.values()) + sum(ext.values())) or ext[i] <= 1e-6:
                del ext[i]
            released += before - ext.get(i, 0.0)
        assert funding(core | ext) >= expected - 1e-6
        c["core_expected_funded"] = expected
        c["overflow_funding_release"] = released
        return ext

    def allocate(self):
        """Create final-dollar targets and retain the engine's source trade stage."""
        c = self.current
        p = c["p"]
        B = c["B"]
        ids = c["selected"]
        cap = c["cap"]
        old = c["old"]
        addr = c["addr"]
        score = c["score"]
        if self.arm == "M11":
            try:
                x, diag = joint(list(c["pairs"]), cap, score, old, B, c["core_limit"], c["buy"], float(p.min_portfolio_weight_pct), addr)
            except RuntimeError as exc:
                x, _ = floors(ids, lambda active: waterfall(active, cap, c["raw"](active), B, addr), cap, old, c["buy"], float(p.min_portfolio_weight_pct))
                diag = {"Status": "M01 fallback: " + str(exc), "Runtime": 0.0, "Gap": np.nan, "Objective": np.nan, "Stages": 0}
            self.data["nb17_solvers"].append(dict(Period=self.data["run_context"][0], Arm=self.arm, Date=c["t"], **diag))
            ids = list(x)
            c["selected"] = ids
            c["objective"] = diag["Objective"]
        elif self.arm == "M08":
            x = c["greedy_targets"]
        else:
            raw = c["raw"](ids)

            def allocate(active):
                if self.arm == "M02":
                    return proportional(active, cap, raw, B)
                return waterfall(active, cap, score if self.arm == "M03" else raw, B, addr)

            x, removed = floors(ids, allocate, cap, old, c["buy"], float(p.min_portfolio_weight_pct))
            c["floor_removed"] = removed
        x = {i: v for i, v in x.items() if v > 0}
        core = x.copy()
        core_ids = ids.copy()
        extensions = []
        if self.arm in OVERFLOW:
            epsilon = float(p.min_portfolio_weight_pct)
            T = sum(core.values())
            R = max(0.0, B - T)
            if core:
                protected = max(0.0, min(v / epsilon for v in core.values()) - T)
                c["core_floor_lost"] = max(0.0, R - protected)
                R = min(R, protected)
            extra_slots = min(OVERFLOW[self.arm], max(0, LIMITS[self.arm] - len(core_ids) - len(c["locked"])))
            candidates = [i for i in c["pairs"] if i not in core_ids and i not in c["locked"] and cap[i] > 0 and (old[i] > 0 or cap[i] >= c["buy"])]
            if self.arm == "M06":
                candidates = [i for i in candidates if c["available"][i]]
            candidates = sorted(candidates, key=lambda i: (-score[i], addr[i]))
            ext = {}
            if self.arm == "M09":
                held = [i for i in candidates if old[i] > 0][:extra_slots]
                ext = {i: min(old[i], cap[i]) for i in held}
                excess = max(0.0, sum(ext.values()) - R)
                fees = c["input"].pricing_model._vault_redemption_fee_by_pair_id
                for i in sorted(held, key=lambda i: (fees.get(i, float(p.vault_redemption_capital_fee)), score[i], addr[i])):
                    if excess <= 0:
                        break
                    cut = min(ext[i], max(excess, c["sell"]))
                    ext[i] -= cut
                    excess = max(0.0, excess - cut)
                ext = {i: v for i, v in ext.items() if v > 0}
            remaining = max(0.0, R - sum(ext.values()))
            for i in candidates:
                if i not in ext and len(ext) >= extra_slots:
                    continue
                add = min(cap[i] - ext.get(i, 0.0), remaining)
                # Do not undo a same-decision maintenance trim.
                if self.arm == "M09" and i in c["held"] and ext.get(i, 0.0) < min(old[i], cap[i]):
                    continue
                v = ext.get(i, 0.0) + add
                if v <= 0 or v < epsilon * (T + sum(ext.values()) + add) - 1e-8 or (old[i] == 0 and v < c["buy"]):
                    continue
                ext[i] = v
                remaining -= add
            rejected = set()
            for _ in range(len(candidates) + 1):
                dust = {i for i in ext if ext[i] < epsilon * (T + sum(ext.values())) - 1e-8}
                if not dust:
                    break
                rejected.update(dust)
                for i in dust:
                    del ext[i]
                remaining = max(0.0, R - sum(ext.values()))
                for i in candidates:
                    if i in rejected or (i not in ext and len(ext) >= extra_slots):
                        continue
                    if self.arm == "M09" and i in c["held"] and ext.get(i, 0.0) < min(old[i], cap[i]):
                        continue
                    add = min(cap[i] - ext.get(i, 0.0), remaining)
                    v = ext.get(i, 0.0) + add
                    if v <= 0 or (old[i] == 0 and v < c["buy"]) or v < epsilon * (T + sum(ext.values()) + add) - 1e-8:
                        continue
                    ext[i] = v
                    remaining -= add
            ext = self.protect_funding(c, core, ext)
            extensions = list(ext)
            x.update(ext)
            c["extension"] = extensions
        model = c["model"]
        raw = c["raw"](core_ids)
        for i in x:
            model.set_signal(c["pairs"][i], max(raw.get(i, score[i]), 1e-12))
        model.select_top_signals(count=len(model.raw_signals))
        model.assign_weights(method=weight_passthrouh)
        model.update_old_weights(c["input"].state.portfolio, ignore_credit=False)
        for i, signal in model.signals.items():
            if signal.carry_forward_position:
                continue
            signal.position_target = float(x.get(i, 0.0))
            signal.normalised_weight = float(x.get(i, 0.0)) / sum(x.values()) if sum(x.values()) else 0.0
            if i in c["pairs"]:
                signal.position_size_risk = USDTVLSizeRiskModel(pricing_model=c["input"].pricing_model, per_position_cap=float(p.per_position_cap_of_pool_pct)).get_acceptable_size_for_position(c["input"].timestamp, signal.pair, float(x.get(i, 0.0)))
        model.investable_equity = B
        model.accepted_investable_equity = sum(x.values())
        model.size_risk_discarded_value = max(0.0, B - sum(x.values()))
        assert sum(x.values()) <= B + 1e-6
        assert all(v <= cap[i] + 1e-6 for i, v in x.items())
        assert len(x) + len(c["locked"]) <= LIMITS[self.arm]
        for i in c["pairs"]:
            role = "core" if i in core_ids else "overflow" if i in extensions else "pinned" if i in c["locked"] else "candidate"
            row = {"Date": c["t"], "Period": self.data["run_context"][0], "Arm": self.arm, "Pair id": i, "Address": addr[i], "Vault": c["pairs"][i].get_vault_name(), "Role": role, "Ranking score": score[i], "Score available": c["available"][i], "Rank": c["rank"][i], "Old value (USD)": old[i], "Deployable budget (USD)": B, "TVL capacity (USD)": c["tvlcap"][i], "Capacity ceiling (USD)": cap[i], "Deposit headroom (USD)": c["deposit"][i], "Deposit reason": c["reason"][i], "Reported max deposit": c["reported"][i], "Accepted allocation (USD)": x.get(i, 0.0), "Final target (USD)": x.get(i, 0.0), "Risk": float(c["risk"].loc[i, "predicted"]), "Actual updates": int(c["risk"].loc[i, "m"]), "Risk status": c["risk"].loc[i, "status"], "Core-only target (USD)": core.get(i, 0.0)}
            self.ledger.append(row)
        positive = sum(x.values())
        poolcap = sum(cap.values())
        corecap = sum(cap[i] for i in core_ids)
        actual_inband = [i for i in c["incumbent"] if i in c["rank"] and 6 < c["rank"][i] <= 8]
        self.data["nb17_decisions"].append(
            {
                "Period": self.data["run_context"][0],
                "Arm": self.arm,
                "Date": c["t"],
                "Budget": B,
                "Accepted": positive,
                "Basket cap deficit": max(0.0, B - corecap),
                "Allocator/floor slack": max(0.0, min(B, corecap) - sum(core.values())),
                "Denied top-up opportunity": sum(max(0.0, c["tvlcap"][i] - cap[i]) for i in core_ids),
                "Universe shortfall": max(0.0, B - poolcap),
                "Overflow dollars": sum(x.get(i, 0.0) for i in extensions),
                "Core floor restricted dollars": c["core_floor_lost"],
                "Overflow funding release": c.get("overflow_funding_release", 0.0),
                "Core positions": len(core_ids),
                "Overflow positions": len(extensions),
                "Capacity reversals": c["reversed"],
                "Delayed rank exits": c["delayed"],
                "Greedy swaps": c["iterations"],
                "Objective": c["objective"],
                "In-band incumbents": len(actual_inband),
                "Tie/predicate protected": sum(i in c["retained"] for i in actual_inband),
                "Actual band replacements": sum(i not in c["shadow"] for i in actual_inband),
                "Strict relative screen admits": sum(c["available"][i] and score[i] >= min([score[j] for j in core_ids if c["available"][j]], default=np.inf) for i in c["pairs"] if i not in core_ids),
                "Pinned slots": len(c["locked"]),
                "Pinned dollars": c["pinned"],
            }
        )
        if self.arm in OVERFLOW:
            for i, v in core.items():
                assert x[i] == v
                self.data["nb17_core_checks"].append(dict(Period=self.data["run_context"][0], Arm=self.arm, Date=c["t"], Pair=i, Core_target=v, Merged_target=x[i]))
        self.core = set(core_ids) & set(x)
        return model, core_ids, extensions, B, c["pinned"], c["buy"]

    def fund(self, input, trades):
        """Keep overflow buys subordinate to the actual net-proceeds budget."""
        cash = Decimal(str(input.state.portfolio.get_cash()))
        proceeds = sum((abs(t.planned_quantity * Decimal(t.planned_price)) for t in trades if t.is_sell()), Decimal(0))
        buys = [t for t in trades if t.is_buy()]
        requested = sum((t.planned_reserve for t in buys), Decimal(0))
        available = cash + proceeds
        if requested <= available:
            return
        reserve = input.state.portfolio.get_default_reserve_asset()[0]
        left = max(available - reserve.convert_to_decimal(10), Decimal(0))
        if self.arm in OVERFLOW:
            core = [t for t in buys if t.pair.internal_id in self.core]
            extra = [t for t in buys if t not in core]
            base = sum((t.planned_reserve for t in core), Decimal(0))
            groups = [(core, min(left, base)), (extra, max(0, left - base))]
        else:
            groups = [(buys, left)]
        for group, budget in groups:
            amount = sum((t.planned_reserve for t in group), Decimal(0))
            if amount > budget:
                for trade in group:
                    trade.planned_reserve *= budget / amount
                    trade.planned_quantity *= budget / amount
        zero = [t for t in trades if t.is_buy() and t.planned_reserve == 0]
        for trade in zero:
            # The planned trade already belongs to a pending position; a zero
            # execution preserves bookkeeping without fabricating funding.
            raise RuntimeError("Overflow funding would create a zero buy; regenerate targets before trading")
        funded = sum((t.planned_reserve for t in buys), Decimal(0))
        assert funded <= available
        self.data["funding_ledger"].append(dict(Period=self.data["run_context"][0], Arm=self.arm, Date=input.timestamp, Requested=float(requested), Funded=float(funded), Reduction=float(requested - funded), Core_reduced=bool(self.arm in OVERFLOW and base > left)))


def compile_policy(strategy, policy):
    """Reuse pinned source candidate/fee/trade code through two explicit hooks."""
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "decide_trades")
    source = ast.get_source_segment(SOURCE.read_text(), node)
    first = source.index("    # Keep eligible incumbents")
    last = source.index("    total_accepted = sum(", first)
    hook = """    selected, skipped_entry_ids = _policy.select(input, position_manager, ordered, held_pair_ids, entry_checks, check_entry_candidate, reference_equity)
    alpha_model, core_ids, extension_ids, fresh_capital, pinned_value, buy_threshold = _policy.allocate()
"""
    source = source[:first] + hook + source[last:]
    source = source.replace("    return trades", "    _policy.fund(input, trades)\n    return trades")
    if policy.corrected:
        line = "                trade.planned_price = trade.planned_mid_price * (1.0 - fee)"
        assert source.count(line) == 1
        source = source.replace(
            line,
            """                if not trade.closing:
                    gross = engine.observed_quote(_policy.data, trade.pair.internal_id, timestamp)[0]
                    trade.other_data["nb17_original_partial_mid"] = trade.planned_mid_price
                    trade.planned_mid_price = gross
                    trade.other_data["nb17_corrected_partial_fee"] = True
                trade.planned_price = trade.planned_mid_price * (1.0 - fee)""",
        )
    namespace = dict(strategy.__dict__)
    namespace.update(_policy=policy, engine=engine)
    exec(compile(source, str(ROOT / "capital_allocation.py") + "::pinned-source", "exec"), namespace)
    return namespace["decide_trades"]


def replay(data, evaluator, arm, period, corrected=False):
    """Run one independent account and persist policy diagnostics with its state."""
    import score_matrix

    original = score_matrix.make_matrix_decision
    values = evaluator.panel.score_values
    n = LIMITS[arm]
    weight = np.zeros(len(FEATURES))
    weight[0] = 1
    policy = None
    starts = {k: len(data[k]) for k in ("nb17_decisions", "nb17_solvers", "nb17_core_checks", "funding_ledger")}
    data["run_context"] = (period, arm, "corrected" if corrected else "primary")
    evaluator.panel.score_values = lambda *a, **kw: data["focal_values"]

    def factory(strategy, panel, vals, sizing, allocator, ledger, **kwargs):
        nonlocal policy
        policy = Policy(data, strategy, arm, ledger, corrected)
        callback = compile_policy(strategy, policy)

        def decide(input):
            parameters = deepcopy(input.parameters)
            parameters["max_assets_in_portfolio"] = 10 if arm == "M13" else 6
            parameters["max_capacity_assets"] = n
            parameters["entry_rank"] = 10 if arm == "M13" else 6
            parameters["exit_rank"] = 12 if arm == "M13" else 8
            proxy = MatrixIndicators(input.indicators, panel, vals, input.timestamp)
            return callback(replace(input, indicators=proxy, parameters=parameters))

        return decide

    if arm == "M12":
        # The exact source extension remains non-waterfall; only core mode changes.
        def factory(strategy, panel, vals, sizing, allocator, ledger, **kwargs):
            def decide(input):
                parameters = deepcopy(input.parameters)
                parameters["max_assets_in_portfolio"] = 6
                parameters["max_capacity_assets"] = 10
                parameters["entry_rank"] = 6
                parameters["exit_rank"] = 8
                first_model = []

                def make(*a, **kw):
                    model = reference.WaterfallAlpha(*a, sizing_mode="parent", allocation_ledger=ledger, **kw) if not first_model else engine.AuditedAlphaModel(*a, sizing_mode="parent", allocation_ledger=ledger, **kw)
                    original_signal = model.set_signal

                    def safe_signal(pair, *args, **kw):
                        return original_signal(replace(pair, internal_id=int(pair.internal_id)), *args, **kw)

                    model.set_signal = safe_signal
                    first_model.append(model)
                    return model

                # Use a scoped copy of source globals, keeping both source allocators.
                namespace = dict(strategy.__dict__)
                namespace["AlphaModel"] = make

                def compute(ids, inv, signals, **opts):
                    return {int(i): float(v) for i, v in engine.research_weights(data, input.timestamp, list(map(int, ids)), "regular")[0].items()}

                namespace["compute_sizing_weights"] = compute
                node = next(v for v in ast.parse(SOURCE.read_text()).body if isinstance(v, ast.FunctionDef) and v.name == "decide_trades")
                source_text = ast.get_source_segment(SOURCE.read_text(), node).replace("alpha_model.signals[pair_id] = signal", "alpha_model.signals[int(pair_id)] = signal")
                exec(compile(source_text, str(SOURCE), "exec"), namespace)
                trades = namespace["decide_trades"](replace(input, parameters=parameters, indicators=MatrixIndicators(input.indicators, panel, vals, input.timestamp)))
                if corrected:
                    for trade in trades:
                        if trade.is_sell() and not trade.closing:
                            fee = float(trade.other_data["backtest_vault_redemption_fee"])
                            trade.planned_mid_price = engine.observed_quote(data, trade.pair.internal_id, input.timestamp)[0]
                            trade.planned_price = trade.planned_mid_price * (1 - fee)
                            trade.other_data["nb17_corrected_partial_fee"] = True
                reference.cap_to_final_sell_proceeds(data, input, trades, arm)
                return trades

            return decide

    score_matrix.make_matrix_decision = factory
    try:
        with engine.pricing_convention(data):
            r = evaluator.run(weight, *PERIODS[period], n=n, sizing="inverse_variance", missing=True, keep=True, profile=f"NB17-{arm}-" + ("corrected-trim" if corrected else "legacy-trim"))
        path = evaluator.folder / f'{r["cache_key"]}-diagnostics.json'
        if policy is None and path.exists():
            for key, rows in json.loads(path.read_text()).items():
                data[key].extend(rows)
        else:
            diag = {key: data[key][start:] for key, start in starts.items()}
            path.write_text(json.dumps(diag, default=str))
        return r
    finally:
        score_matrix.make_matrix_decision = original
        evaluator.panel.score_values = values


def baseline(data, evaluator, period):
    """Load the exact NB16 C-W account and establish metric parity."""
    folder = evaluator.folder
    evaluator.folder = data["nb16_reference"] / "engine"
    try:
        r = reference.replay_waterfall(data, evaluator, "C", period)
    finally:
        evaluator.folder = folder
    expected = pd.read_csv(data["nb16_reference"] / "results.csv").set_index(["Period", "Arm"]).loc[(period, "C-W")]
    for name in ["CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)"]:
        assert abs(r["metrics"][name] - expected[name]) < (0.01 if "USD" in name else 2e-6), (period, name)
    return r


def audit(data, r, arm, period):
    """Check gross execution NAV under both inherited and corrected trim prices."""
    rows = []
    for t in r["result"].state.portfolio.get_all_trades():
        if not t.is_success():
            continue
        when = pd.Timestamp(t.executed_at)
        q = engine.observed_quote(data, t.pair.internal_id, when)
        fee = float(t.other_data.get("backtest_vault_redemption_fee", 0))
        mid = float(t.planned_mid_price)
        if t.is_sell() and not t.closing and not t.other_data.get("nb17_corrected_partial_fee"):
            mid /= 1 - fee
        valid = q is not None and q[1] <= when and np.isclose(mid, q[0], rtol=1e-9, atol=1e-12)
        rows.append(dict(Period=period, Arm=arm, Date=when, Trade=t.trade_id, Vault=t.pair.get_vault_name(), Matches_known_NAV=valid))
    f = pd.DataFrame(rows)
    assert f.empty or f.Matches_known_NAV.all(), f[~f.Matches_known_NAV].head()
    return f


def run(data, evaluator):
    """Run the fixed matrix in both periods and save after every account."""
    records = []
    runs = {}
    attribution = {}
    weights = {}
    audits = []
    for period, arm in tqdm([(p, a) for p in PERIODS for a in ARMS], desc="NB17 capital allocation", mininterval=15):
        print(f"{period} / {arm}; remaining approximately {evaluator.remaining(28-len(records)):.1f} minutes", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = baseline(data, evaluator, period) if arm == "M00" else replay(data, evaluator, arm, period)
        m, v, w = engine.analyse_run(data, r, arm, period)
        m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
        m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"]) if m["Maximum drawdown"] < 0 else np.nan
        reserve = r["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        sep = w.loc["2026-09-01":"2026-09-30", reserve]
        m["September cash"] = float(sep.mean()) if len(sep) else np.nan
        held = w.drop(columns=reserve)
        m["Mean effective breadth"] = float((held.sum(axis=1) ** 2 / held.pow(2).sum(axis=1).replace(0, np.nan)).mean())
        assert m["Maximum vaults held"] <= LIMITS[arm]
        records.append(dict(Period=period, Arm=arm, Method=METHODS[arm], **m))
        runs[(period, arm)] = r
        attribution[(period, arm)] = v
        weights[(period, arm)] = w
        audits.append(audit(data, r, arm, period))
        snapshots = {}
        state = r["result"].state
        positions = {p.position_id: p for p in state.portfolio.get_all_positions()}
        for position_id, stats in state.stats.positions.items():
            for stat in stats:
                key = (pd.Timestamp(stat.calculated_at), int(positions[position_id].pair.internal_id))
                snapshots[key] = snapshots.get(key, 0.0) + float(stat.value)
        ledger = r["allocation_df"].copy()
        if len(ledger):
            ledger["Executed holding (USD)"] = [snapshots.get((pd.Timestamp(t), int(i)), 0.0) for t, i in zip(ledger.Date, ledger["Pair id"])]
        ledger.to_csv(data["artifact"] / f"{period}-{arm}-target-ledger.csv", index=False)
        pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
        for key in ("nb17_decisions", "nb17_solvers", "nb17_core_checks", "funding_ledger"):
            pd.DataFrame(data[key]).to_csv(data["artifact"] / (key + ".csv"), index=False)
    pd.concat(audits, ignore_index=True).to_csv(data["artifact"] / "fill-audit.csv", index=False)
    return pd.DataFrame(records), runs, attribution, weights


def sensitivities(data, evaluator, results):
    """Correct only repeated partial-trim fees for the registered primary shortlist."""
    leaders = {results[results.Period.eq(p)].sort_values("Net profit (USD)", ascending=False).iloc[0].Arm for p in PERIODS}
    members = sorted(leaders | {"M00"})
    records = []
    for period, arm in tqdm([(p, a) for p in PERIODS for a in members], desc="NB17 corrected-trim sensitivities", mininterval=15):
        print(f"{period} / {arm}: corrected partial trim; approximately 1–3 minutes per account", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if arm == "M00":
                r = corrected_benchmark(data, evaluator, period)
            else:
                r = replay(data, evaluator, arm, period, corrected=True)
        m, _, _ = engine.analyse_run(data, r, arm, period + "-corrected")
        audit(data, r, arm, period + "-corrected")
        original = results.set_index(["Period", "Arm"]).loc[(period, arm)]
        records.append(dict(Period=period, Arm=arm, **m, **{"Profit sensitivity (USD)": m["Net profit (USD)"] - original["Net profit (USD)"]}))
        pd.DataFrame(records).to_csv(data["artifact"] / "fee-sensitivities.csv", index=False)
    return pd.DataFrame(records)


def corrected_benchmark(data, evaluator, period):
    """Keep exact C-W allocation while correcting its final partial-sell quote."""
    source = evaluator.strategy.decide_trades
    folder = evaluator.folder
    evaluator.folder = folder / "corrected-M00"
    evaluator.folder.mkdir(exist_ok=True)

    def wrapped(input):
        trades = source(input)
        for t in trades:
            if t.is_sell() and not t.closing:
                fee = float(t.other_data["backtest_vault_redemption_fee"])
                gross = engine.observed_quote(data, t.pair.internal_id, input.timestamp)[0]
                t.planned_mid_price = gross
                t.planned_price = gross * (1 - fee)
                t.other_data["nb17_corrected_partial_fee"] = True
        return trades

    evaluator.strategy.decide_trades = wrapped
    try:
        return reference.replay_waterfall(data, evaluator, "C", period)
    finally:
        evaluator.strategy.decide_trades = source
        evaluator.folder = folder
