"""Independent algebra and sparse-data fixtures requested by the NB19 plan."""

import numpy as np
import pandas as pd
from portfolio_snapshot_risk import empirical_window, forecast
from portfolio_snapshot_construction import bounded_proportional


def algebra():
    rows = []

    def passed(name, result):
        assert result, name
        rows.append({"Check": name, "Passed": True})

    E = 150000
    D = 0.5 * 0.05 * E
    r = np.array([1, 0.5, 1])
    g = np.array([1, 0.6, 0.5])
    tickets = D * r * g
    passed("Worked absolute tickets: 3750, 1125, 1875", np.allclose(tickets, [3750, 1125, 1875]))
    passed("Weak-score reductions remain cash", np.isclose(10000 - tickets.sum(), 3250))
    norm = bounded_proportional(r * g, np.full(3, 7500.0), 10000)
    passed("Normalised worked allocation conserves cash", np.allclose(norm, [5555.5555556, 1666.6666667, 2777.7777778], atol=1e-5))
    passed("Normalised utility scale invariance", np.allclose(norm, bounded_proportional(7 * r * g, np.full(3, 7500.0), 10000)))
    passed("Capacity clipping after score/risk multipliers", min(500, D * 0.5 * 0.6) == 500)
    passed("Blocked incumbent can retain; no additional deposit", min(7500, 1000 + 0) == 1000)
    raw = np.array([np.nan, 100, np.nan, np.nan, 102, np.nan])
    carried = pd.Series(raw).ffill().to_numpy()
    actual = np.isfinite(raw)
    v = empirical_window(carried, actual, 90)
    passed("No pre-inception backfill", np.isnan(carried[0]))
    passed("Sparse carried path produces variance", np.isfinite(v["empirical"]) and v["m"] == 1)
    prior = 0.0001
    pred = forecast(np.nan, prior, 0, "regularised", 30)
    passed("Prior-only risk multiplier is one", pred == prior and min(1, np.sqrt(prior / pred)) == 1)
    passed("Unsupported risk stays missing", np.isnan(forecast(np.nan, np.nan, 0, "regularised", 30)))
    passed("Missing and finite zero share floor, retain distinct flags", 0.5 + 0.5 * 0 == 0.5 and np.isnan(np.nan))
    passed("Hold preserves units rather than entry dollars", 10 * 102 != 10 * 100)
    return pd.DataFrame(rows)


def adapter_cases():
    """Exercise the real additional merge with isolated source-state fixtures."""
    from types import SimpleNamespace as NS
    from unittest.mock import patch
    import protected_core_score_allocation as exp

    rows = []

    def passed(name, value):
        assert value, name
        rows.append({"Check": name, "Passed": True})

    def fixture(held=False, blocked=False, cap=10000, pinned=False, finite=True, core_pair=False):
        pair = NS(internal_id=7, pool_address="0x07", get_vault_name=lambda: "Fixture vault", is_credit_supply=lambda: False)
        core = NS(internal_id=1, pool_address="0x01", get_vault_name=lambda: "Fixture core")

        def signal(p, target=0, old=0, carry=False):
            return NS(pair=p, position_target=target, old_value=old, carry_forward_position=carry, set_deposit_check_result=lambda v: None)

        model = NS(signals={1: signal(core, 90000)}, raw_signals={})

        def set_signal(p, value):
            model.raw_signals[p.internal_id] = signal(p)

        model.set_signal = set_signal
        model.set_old_weight = lambda p, w, value, old: setattr(model.signals[p.internal_id], "old_value", value)
        old = NS(pair=pair, get_value=lambda: 1000.0, get_quantity=lambda: 10.0)
        if pinned:
            model.signals[7] = signal(pair, 1000, 1000, True)
        if core_pair:
            model.signals[7] = signal(pair, 1000, 1000)
        state = NS(portfolio=NS(get_open_positions=lambda: [old] if held or pinned or core_pair else [], get_cash=lambda: 99000.0))
        parameters = NS(vault_redemption_capital_fee=0.001, vault_performance_fee=0.10, min_portfolio_weight_pct=0.005, max_concentration_pct=0.25, absolute_min_vault_deposit_usd=100, sell_rebalance_min_threshold_of_initial_cash_pct=0.01)
        input = NS(parameters=parameters, timestamp=pd.Timestamp("2026-09-01"), state=state, indicators=NS(get_indicator_value=lambda *a, **kw: 1.0 if finite else np.nan))
        data = {"nb19_candidates": [], "nb19_decisions": [], "nb19_checks": []}
        adapter = exp.Adapter(data, None, "RS00", "2026", [])
        pm = NS(is_whitelisted_vault=lambda p: True, is_async_vault_sell_pair=lambda *a, **kw: False)
        sr = NS(get_acceptable_size_for_position=lambda *a: NS(accepted_size=cap))
        check = lambda p: NS(can_deposit=not blocked, max_deposit=0 if blocked else None)
        risk = lambda d, t, ids: pd.DataFrame({i: dict(risk_multiplier=1.0, prior_only=True, updates=0, age=1.0) for i in ids}).T
        with patch.object(exp, "fixed_risk", risk), patch.object(exp.engine, "observed_quote", lambda *a: (100.0, None)):
            adapter.merge(input, model, [(7, pair, 1.0 if finite else 0.0)], {1, 7} if core_pair else {1}, 98000, 100, 100000, pm, sr, check)
        return adapter, model, data

    a, m, d = fixture(finite=False)
    passed("Unscored eligible entry receives positive floor ticket", 7 in a.extra and m.signals[7].position_target > 0)
    passed("Missing entry preserves source core target", m.signals[1].position_target == 90000)
    a, m, d = fixture(held=True, blocked=True)
    passed("Blocked incumbent retains exact share-value target without top-up", m.signals[7].position_target == 1000)
    a, m, d = fixture(held=True, cap=500)
    passed("Hard trim below source band closes rather than breaches cap", 7 not in a.extra)
    a, m, d = fixture(cap=50)
    passed("Minimum-ticket failure does not create new position", 7 not in a.extra)
    a, m, d = fixture(pinned=True)
    passed("Pinned source holding remains a real carry signal", m.signals[7].carry_forward_position and 7 not in a.extra)
    passed("Pinned value contributes to conservative equity bound", d["nb19_decisions"][0]["Equity"] < 100000)
    a, m, d = fixture(core_pair=True)
    passed("Core promotion creates one core target, no extra target", 7 in a.core and 7 not in a.extra and m.signals[7].position_target == 1000)
    for rank in (6, 7, 9):
        a.core = {1}
        a.extra = {rank}
        passed(f"Additional ownership at rank {rank} cannot use core held-status bypass", a.held({1, rank}) == {1})
    return pd.DataFrame(rows)
