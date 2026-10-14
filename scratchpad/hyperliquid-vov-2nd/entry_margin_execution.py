"""Conditional source-equivalent funded fresh-entry vetoes for NB22."""

import io
import json
from contextlib import redirect_stdout, redirect_stderr
import numpy as np
import pandas as pd
from entry_margin_calibration import uniform


def discard_planned_entry(state, trade):
    """Remove an unstarted fresh buy, its empty position and unused tail counters."""
    assert trade.started_at is None and trade.executed_at is None
    portfolio = state.portfolio
    pos = portfolio.open_positions[trade.position_id]
    assert not list(pos.get_successful_trades()), "A fresh-entry veto cannot touch an incumbent"
    assert set(pos.trades) == {trade.trade_id}, "Unexpected additional trade in a new entry"
    del pos.trades[trade.trade_id]
    del portfolio.open_positions[pos.position_id]
    assert pos.position_id not in portfolio.pending_positions
    assert pos.position_id not in state.stats.positions
    remaining = list(portfolio.get_all_positions(pending=True))
    portfolio.next_position_id = max((p.position_id for p in remaining), default=0) + 1
    portfolio.next_trade_id = max((t.trade_id for p in remaining for t in p.trades.values()), default=0) + 1


def run_accounts(data):
    """Run the registered two-calendar matrix only after an explicit go record."""
    assert data["registration"]["execute_accounts"]
    import clean_c00_v11_comparison as baseline
    from tradeexecutor.visual.equity_curve import calculate_equity_curve

    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        engine_data, evaluator = baseline.initialise()
    assert engine_data["manifest"]["identity"] == data["identity"]["parent"]["parent"], "Fresh engine/input identity changed"
    core = baseline.core
    engine_data["artifact"] = data["artifact"]
    engine_data["figures"] = []
    evaluator.folder = data["artifact"] / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    lookup = data["calibration"].query("Model == 'L2'")
    lookup = lookup[lookup.H.eq(data["horizon"])].set_index(["Date", "Pair"])
    rates = data["rates"].set_index(["Period", "Date"]).Pi
    metrics = data["metrics"].to_dict("records")
    runs = {}
    ledger = []
    parity = []
    original = core.reference.cap_to_final_sell_proceeds
    for period in ("2026", "Long"):
        print(f"NB22 fresh C00 parity: {period}", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            zero = core.replay(engine_data, evaluator, "C00", period, active=False)
        saved = data["states"][period, "C00"]
        signature = lambda s: [(str(t.executed_at), str(t.pair.pool_address), float(t.executed_quantity), float(t.executed_price), float(t.executed_reserve)) for t in s.portfolio.get_all_trades() if t.is_success()]
        assert signature(zero["result"].state) == signature(saved), "Fresh unchanged C00 trade parity"
        assert (zero["equity"].resample("D").last().ffill() - data["equity"][period, "C00"]).abs().max() < 1e-6
        for arm in ["O1", "R01", "R02", "R03", "R04", "R05"]:
            print(f"NB22 {period} / {arm}: complete calendar, no refill", flush=True)
            start = len(ledger)

            def funded(data_, input, trades, arm_, current_arm=arm, current_period=period):
                original(data_, input, trades, arm_)
                # All selected targets and final synchronous funding are now fixed.
                remove = []
                for trade in list(trades):
                    if not trade.is_buy():
                        continue
                    pos = input.state.portfolio.open_positions[trade.position_id]
                    if list(pos.get_successful_trades()):
                        continue
                    t = pd.Timestamp(input.timestamp)
                    pid = int(trade.pair.internal_id)
                    key = (t, pid)
                    row = lookup.loc[key] if key in lookup.index else None
                    actionable = bool(row is not None and row.Actionable)
                    pi = float(rates.get((current_period, t), 0.0))
                    veto = actionable and (bool(row.Veto) if current_arm == "O1" else uniform(int(current_arm[1:]), t, trade.pair.pool_address) < pi)
                    ledger.append(dict(Period=current_period, Arm=current_arm, Date=t, Pair=pid, Address=str(trade.pair.pool_address).lower(), Proposed_USD=float(trade.planned_reserve), Actionable=actionable, Prediction=float(row.Prediction) if row is not None else np.nan, Pi=pi, Veto=veto, Reason="supported selective veto" if veto else str(row.Pass_reason) if row is not None else "outside calibrated population"))
                    if veto:
                        remove.append(trade)
                for trade in remove:
                    discard_planned_entry(input.state, trade)
                    trades.remove(trade)
                input.state.perform_integrity_check()

            core.reference.cap_to_final_sell_proceeds = funded
            try:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    r = core.replay(engine_data, evaluator, arm, period, active=False)
            finally:
                core.reference.cap_to_final_sell_proceeds = original
            lp = evaluator.folder / f'{r["cache_key"]}-entry-vetoes.csv'
            if len(ledger) > start:
                pd.DataFrame(ledger[start:]).to_csv(lp, index=False)
            elif lp.exists():
                ledger.extend(pd.read_csv(lp, parse_dates=["Date"]).to_dict("records"))
            else:
                raise AssertionError("Conditional replay lacks its proposal ledger")
            decisions = pd.DataFrame(ledger[start:])
            vetoes = decisions[decisions.Veto]
            first = vetoes.Date.min() if len(vetoes) else None
            actual = signature(r["result"].state)
            expected = signature(saved)
            if first is None:
                assert actual == expected
                assert (r["equity"].resample("D").last().ffill() - data["equity"][period, "C00"]).abs().max() < 1e-6
            else:
                assert [v for v in actual if pd.Timestamp(v[0]) < first] == [v for v in expected if pd.Timestamp(v[0]) < first], "Trade parity until first veto"
                before = r["equity"].resample("D").last().ffill().loc[: first - pd.Timedelta(days=1)]
                assert (before - data["equity"][period, "C00"].reindex(before.index)).abs().max() < 1e-6
            parity.append(dict(Period=period, Arm=arm, First_veto=first, Vetoes=len(vetoes), Pre_veto_trade_parity=True))
            m, _, w = core.engine.analyse_run(engine_data, r, arm, period)
            metrics.append(dict(Period=period, Arm=arm, **m))
            data["equity"][period, arm] = r["equity"].resample("D").last().ffill()
            runs[period, arm] = r
    data["account_metrics"] = pd.DataFrame(metrics)
    data["account_metrics"].to_csv(data["artifact"] / "account-results.csv", index=False)
    data["veto_ledger"] = pd.DataFrame(ledger)
    data["veto_ledger"].to_csv(data["artifact"] / "engine-proposals.csv", index=False)
    pd.DataFrame(parity).to_csv(data["artifact"] / "engine-parity.csv", index=False)
    data["engine_status"] = "Executed informed plus five causal-rate controls on both calendars"
    return runs
