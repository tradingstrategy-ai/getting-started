"""NB14: five frozen economic allocation comparisons on the source engine."""

import datetime
import hashlib
import io
import json
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from tqdm_loggable.auto import tqdm

from accepted_dollar_cap import AuditedAlphaModel, calculate_position_profit_curves
from allocation_followup import risk_at
from long_candidate_backtest import initialise as legacy_initialise, replay_one, FOCAL, ROOT, START, END, SHORT_END
from portfolio_snapshot_construction import bounded_proportional, risk_weights
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast
from score_matrix import FEATURES, MatrixIndicators
from tradeexecutor.strategy.alpha_model import AlphaModel, TradingPairSignalFlags
from tradeexecutor.analysis.weights import calculate_asset_weights

PERIODS = {"2026": (datetime.datetime(2026, 1, 1), SHORT_END), "Long": (START, END)}
LABELS = {"2026": "2026-01-01 → 2026-10-05 exclusive (through 4 October, UTC)", "Long": "2023-03-01 → 2026-10-08 exclusive (through 7 October, UTC; final archive day partial)"}
ARMS = {"A": ("Source variance / original allocation", "source", "sequential"), "B": ("Source variance / simultaneous allocation", "source", "simultaneous"), "C": ("Regularised variance / original allocation", "regular", "sequential"), "D": ("Regularised variance / simultaneous allocation", "regular", "simultaneous"), "G": ("Regularised downside / original allocation", "downside", "sequential")}


def raw_history(data):
    """Read genuine intraday NAV marks, retaining no archive publication proxy."""
    ids = data["identities"]
    mapping = ids.set_index("vault_address").pair_id.to_dict()
    table = ds.dataset(data["downloads"]["vault_prices"]["path"], format="parquet")
    raw = table.to_table(columns=["timestamp", "address", "share_price"], filter=(ds.field("chain") == 9999) & ds.field("address").isin(list(mapping))).to_pandas().reset_index()
    raw["timestamp"] = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(None)
    raw = raw[np.isfinite(raw.share_price) & raw.share_price.gt(0)].copy()
    raw["pair_id"] = raw.address.map(mapping).astype(int)
    raw = raw.sort_values(["pair_id", "timestamp"], kind="stable").drop_duplicates(["pair_id", "timestamp"], keep="last")
    arrays = {int(pid): (g.timestamp.to_numpy(dtype="datetime64[ns]").astype("int64"), g.share_price.to_numpy(float)) for pid, g in raw.groupby("pair_id")}
    return raw, arrays


def observed_quote(data, pid, t):
    """Return the latest recorded NAV at or before the requested timestamp."""
    arrays = data["nav_history"].get(int(pid))
    if arrays is None:
        return None
    times, prices = arrays
    k = np.searchsorted(times, pd.Timestamp(t).value, side="right") - 1
    return (float(prices[k]), pd.Timestamp(times[k])) if k >= 0 else None


def audit_trades(data, run, arm, period):
    """Identify genuine uses of later marks, separately from misleading labels."""
    rows = []
    for trade in run["result"].state.portfolio.get_all_trades():
        if not trade.is_success() or not trade.pair.is_vault():
            continue
        t = pd.Timestamp(trade.executed_at or trade.started_at or trade.opened_at)
        pid = int(trade.pair.internal_id)
        known = observed_quote(data, pid, t)
        daily = data["legacy_marks"].get(pid)
        if daily is None:
            continue
        times, prices, observed = daily
        k = np.searchsorted(times, t.floor("D").value, side="right") - 1
        if k < 0:
            continue
        later = pd.Timestamp(observed[k]) > t
        stored_mid = float(trade.planned_mid_price or trade.executed_price or 0)
        fee = float(trade.other_data.get("backtest_vault_redemption_fee", 0))
        fee_adjusted = trade.is_sell() and not trade.closing and fee > 0
        mid = stored_mid / (1 - fee) if fee_adjusted else stored_mid
        matches = bool(np.isclose(mid, prices[k], rtol=1e-9, atol=1e-12))
        causal_matches = known is not None and bool(np.isclose(mid, known[0], rtol=1e-9, atol=1e-12))
        rows.append(dict(Arm=arm, Period=period, Trade=trade.trade_id, Date=t, pair_id=pid, Vault=trade.pair.get_vault_name(), Side="Buy" if trade.is_buy() else "Sell", Mid_price=mid, Stored_mid_price=stored_mid, Fee_adjusted_mid=fee_adjusted, Daily_close=float(prices[k]), Daily_observed_at=pd.Timestamp(observed[k]), Later_daily_mark=later, Uses_later_mark=bool(later and matches and not causal_matches), Known_NAV=known[0] if known else np.nan, Known_observed_at=known[1] if known else pd.NaT, Matches_known_NAV=causal_matches, Known_age_days=(t - known[1]).total_seconds() / 86400 if known else np.nan, Notional=abs(float(trade.executed_reserve or 0))))
    return pd.DataFrame(rows)


def initialise():
    """Reuse pinned NB13 inputs, reproduce controls and perform the timing preflight."""
    data, evaluator, chosen, _ = legacy_initialise()
    legacy_folder = data["artifact"]
    data["legacy_folder"] = legacy_folder
    raw, history = raw_history(data)
    data["raw_history"] = raw
    data["nav_history"] = history
    data["legacy_marks"] = {int(pid): (g.date.to_numpy(dtype="datetime64[ns]").astype("int64"), g.share_price.to_numpy(float), g.timestamp.to_numpy(dtype="datetime64[ns]")) for pid, g in data["daily"].sort_values("date").groupby("pair_id")}
    a = chosen[chosen["Score name"].eq(FOCAL) & chosen.Positions.eq(6) & chosen.Kind.eq("score")].iloc[0].to_dict()
    d = dict(Kind="allocation", Policy="S03")
    references = {}
    audits = []
    parity = []
    expected_long = pd.read_csv(legacy_folder / "long-results.csv").set_index("Candidate")
    expected_short = {"A": (0.517666, 2.303466), "D": (0.466005, 2.091681)}
    for period, (start, end) in PERIODS.items():
        for arm, row in [("A", a), ("D", d)]:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                r = replay_one(data, evaluator, row, start, end)
            references[(period, arm)] = r
            audits.append(audit_trades(data, r, arm, period))
            expected = expected_short[arm] if period == "2026" else tuple(expected_long.loc["C03" if arm == "A" else "B02", ["CAGR", "Sharpe"]])
            for metric, value in zip(("CAGR", "Sharpe"), expected):
                error = r["metrics"][metric] - float(value)
                assert abs(error) < 2e-6, (period, arm, metric, error)
                parity.append(dict(Period=period, Arm=arm, Metric=metric, Expected=value, Observed=r["metrics"][metric], Difference=error))
    preflight = pd.concat(audits, ignore_index=True)
    confirmed = int(preflight.Uses_later_mark.sum())
    convention = "as_of_observation" if confirmed else "legacy_daily_close"
    files = [ROOT / n for n in ("profitable_allocation.py", "profitable_allocation_report.py", "create_profitable_allocation_notebook.py")]
    identity = dict(version="nb14-v1", code={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, nb13_identity=data["manifest"]["identity"], arms=ARMS, periods={k: [str(t) for t in v] for k, v in PERIODS.items()}, pricing=convention, sensitivity="fresh_quote_within_source_two_day_cycle", initial_cash=150000)
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/14" / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    data.update(artifact=folder, fingerprint=fingerprint, figures=[], references=references, pricing_convention=convention, risk_cache={}, risk_ledger=[], quote_queries={}, fresh_blocks=[], run_context=None)
    data["manifest"] = dict(identity=identity, fingerprint=fingerprint, legacy_folder=str(legacy_folder), timing_preflight=dict(successful_trades=len(preflight), uses_later_mark=confirmed, convention=convention, interpretation="Trace confirms later intraday NAV consumption, not merely a midnight label" if confirmed else "No confirmed later NAV consumption in reference trades"), limitations=["NAV timestamp is assumed to be its effective observation time; historical publication availability remains unverified", "As-of recorded NAV marking/fills are a model; sparse observations do not establish the actual executable NAV", "No forward independent holdout; inventory/guard history remains the inherited retrospective universe"], framework=data["framework_commits"])
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    pd.DataFrame(parity).to_csv(folder / "legacy-replication.csv", index=False)
    preflight.to_parquet(folder / "legacy-trade-timing.parquet", index=False)
    # Every score and risk input ends no later than the previous daily bucket.
    assert (data["daily"].timestamp < data["daily"].date + pd.Timedelta(days=1)).all()
    return data, evaluator, preflight


def downside_risk(data, t, ids):
    """Match regularised variance support while replacing its risk functional."""
    t = pd.Timestamp(t)
    a = data["date_index"][t - pd.Timedelta(days=1)]
    e = data["eligibility"]
    pool = np.unique(np.r_[e.loc[e.origin_at.eq(t) & e.eligible_as_of_origin, "pair_id"].to_numpy(int), np.asarray(ids, int)])
    rows = []
    vals = []
    downs = []
    for pid in pool:
        j = data["id_index"][int(pid)]
        p = data["arrays"]["nav"][max(0, a - 90) : a + 1, j]
        actual = data["arrays"]["actual"][max(0, a - 90) : a + 1, j]
        v = empirical_window(p, actual, 90)
        vals.append(v)
        finite = np.flatnonzero(np.isfinite(p) & (p > 0))
        path = p[finite[0] :] if len(finite) else np.array([])
        ret = path[1:] / path[:-1] - 1 if np.isfinite(v["empirical"]) else np.array([])
        downs.append(float(np.mean(np.minimum(ret, 0) ** 2)) if len(ret) else np.nan)
    emp = np.array([v["empirical"] for v in vals])
    down = np.array(downs)
    full = np.array([v["full"] for v in vals])
    for i, (pid, v) in enumerate(zip(pool, vals)):
        prior, count, poolname, _ = peer_prior(down, full, i)
        fallback = False
        if not np.isfinite(prior):
            prior, count, poolname, _ = peer_prior(emp, full, i)
            fallback = np.isfinite(prior)
        predicted = forecast(down[i], prior, v["m"], "regularised", 30)
        state = "unavailable" if not np.isfinite(down[i]) else "observed_flat" if v["empirical"] == 0 else "zero_downside_nonflat" if down[i] == 0 else "observed_downside"
        if np.isfinite(prior):
            assert predicted >= prior * 0.25 - 1e-15 and v["m"] <= 90
        rows.append(dict(origin_at=t, pair_id=int(pid), predicted=predicted, empirical=down[i], total_variance=v["empirical"], prior=prior, prior_count=count, prior_pool=poolname, prior_only=not np.isfinite(down[i]), variance_prior_fallback=bool(fallback), status=state, n=v["n"], m=v["m"], full=v["full"]))
    return pd.DataFrame(rows)


def research_weights(data, t, ids, method):
    """Estimate only from the frozen pre-decision eligible pool and selected incumbents."""
    key = (pd.Timestamp(t), tuple(sorted(map(int, ids))), method)
    if key not in data["risk_cache"]:
        r = downside_risk(data, t, ids) if method == "downside" else risk_at(data, pd.Timestamp(t), ids)
        data["risk_cache"][key] = r.set_index("pair_id")
    r = data["risk_cache"][key].reindex(ids)
    v = r.predicted.to_numpy(float)
    u = risk_weights(v, 2)
    r = r.copy()
    r["raw_weight"] = u
    r["basket_equal_fallback"] = not (np.isfinite(v) & (v > 0)).all()
    return dict(zip(ids, u)), r


class SimultaneousAlpha(AuditedAlphaModel):
    """Redistribute the same positive raw signals simultaneously within source caps."""

    def _normalise_weights_size_risk_positions(self, max_positions, max_weight=1.0, investable_equity=None, size_risk_model=None, epsilon_usd=5.0, max_weight_function=None):
        budget = float(investable_equity)
        signals = [s for s in self._get_allocatable_signals() if s.raw_weight > 0]
        if not signals or budget <= 0:
            self.investable_equity = budget
            self.accepted_investable_equity = 0.0
            self.size_risk_discarded_value = budget
            return
        # Match NB12's final-signal risk calculation; B retains the source weights exactly.
        if getattr(self, "nb14_method", "source") != "source":
            by_id, _ = research_weights(self.nb14_data, self.timestamp, [s.pair.internal_id for s in signals], self.nb14_method)
            raw = np.array([by_id[s.pair.internal_id] for s in signals])
        else:
            raw = np.array([float(s.raw_weight) for s in signals])
        u = raw / raw.sum()
        caps = []
        for s in signals:
            limit = max_weight_function(s) if max_weight_function else max_weight
            limit = max_weight if limit is None else limit
            caps.append(float(size_risk_model.get_acceptable_size_for_position(self.timestamp, s.pair, float(limit * budget)).accepted_size) / budget)
        caps = np.array(caps)
        w = bounded_proportional(u, caps, 1.0)
        self.investable_equity = budget
        self.accepted_investable_equity = float(w.sum() * budget)
        self.size_risk_discarded_value = budget - self.accepted_investable_equity
        ids = {s.pair.internal_id for s in signals}
        for i, s in enumerate(signals):
            target = float(w[i] * budget)
            sr = size_risk_model.get_acceptable_size_for_position(self.timestamp, s.pair, target)
            assert target <= float(sr.accepted_size) + 1e-6 and w[i] <= caps[i] + 1e-9
            s.position_size_risk = sr
            s.position_target = target
            s.normalised_weight = target / self.accepted_investable_equity if self.accepted_investable_equity else 0.0
            if abs(w[i] - caps[i]) < 1e-9:
                s.flags.add(TradingPairSignalFlags.capped_by_pool_size)
            row = dict(Date=self.timestamp, **{"Pair id": s.pair.internal_id, "Vault": s.pair.get_vault_name(), "Deployable budget (USD)": budget, "Raw weight": float(raw[i]), "Original weight": float(u[i]), "Old value (USD)": float(s.old_value), "Accepted allocation (USD)": target, "Final target (USD)": target, "Capacity fraction": float(caps[i])})
            self._audit_rows.append(row)
            self._allocation_ledger.append(row)
        for s in self.signals.values():
            if s.pair.internal_id not in ids and not s.carry_forward_position:
                s.position_target = 0.0
                s.normalised_weight = 0.0


class FreshSlotMixin:
    """Reserve portfolio slots for positions pinned by the sensitivity gate."""

    def select_top_signals(self, count, threshold=0.0):
        pinned = sum(s.carry_forward_position for s in self.raw_signals.values())
        return super().select_top_signals(max(0, count - pinned), threshold)


class FreshSequentialAlpha(FreshSlotMixin, AuditedAlphaModel):
    pass


class FreshSimultaneousAlpha(FreshSlotMixin, SimultaneousAlpha):
    pass


def decision_factory(data, strategy, panel, values, arm, ledger):
    """Preserve source selection and trade generation, replacing allocation only."""
    method, allocator = ARMS[arm][1:]
    source = strategy.decide_trades

    def decide(input):
        compute = strategy.compute_sizing_weights
        factory = strategy.AlphaModel
        models = []
        t = pd.Timestamp(input.timestamp)

        def weights(selected_pair_ids, inv_vol_by_id, signal_by_id, **kwargs):
            if method == "source":
                return compute(selected_pair_ids, inv_vol_by_id, signal_by_id, **kwargs)
            w, r = research_weights(data, t, selected_pair_ids, method)
            data["risk_ledger"].append(r.reset_index().assign(Arm=arm, Period=data["run_context"][0], Variant=data["run_context"][2]))
            return {pid: max(float(value), 1e-12) for pid, value in w.items()}

        def make(*args, **kwargs):
            if data["run_context"][2] == "fresh":
                cls = FreshSimultaneousAlpha if allocator == "simultaneous" else FreshSequentialAlpha
            else:
                cls = SimultaneousAlpha if allocator == "simultaneous" else AuditedAlphaModel
            model = cls(*args, sizing_mode="parent", allocation_ledger=ledger, **kwargs)
            model.nb14_data = data
            model.nb14_method = method
            models.append(model)
            return model

        strategy.compute_sizing_weights = weights
        strategy.AlphaModel = make
        try:
            proxy = MatrixIndicators(input.indicators, panel, values, t)
            trades = source(replace(input, indicators=proxy))
            for model in models:
                for row in model._audit_rows:
                    signal = model.signals[row["Pair id"]]
                    row["Final target (USD)"] = float(signal.position_target or 0)
                    row["Ranking score"] = proxy.get_indicator_value("matrix_score", pair=signal.pair)
                    row["Normalised accepted weight"] = float(signal.normalised_weight or 0)
            return trades
        finally:
            strategy.compute_sizing_weights = compute
            strategy.AlphaModel = factory

    return decide


class ObservationPriceProxy:
    """Price vaults from actual marks available at the requested instant."""

    def __init__(self, original, data):
        self.original = original
        self.data = data

    def __getattr__(self, name):
        return getattr(self.original, name)

    def get_price_with_tolerance(self, pair_id, when, *args, **kwargs):
        if int(pair_id) not in self.data["nav_history"]:
            return self.original.get_price_with_tolerance(pair_id, when, *args, **kwargs)
        quote = observed_quote(self.data, pair_id, when)
        if quote is None:
            from tradingstrategy.candle import CandleSampleUnavailable

            raise CandleSampleUnavailable(f"No observed NAV at {when} for vault {pair_id}")
        price, observed = quote
        assert observed <= pd.Timestamp(when)
        self.data["quote_queries"][(self.data["run_context"], int(pair_id), pd.Timestamp(when))] = dict(Context=self.data["run_context"], pair_id=int(pair_id), Date=pd.Timestamp(when), Observed_at=observed, Price=price, Age_days=(pd.Timestamp(when) - observed).total_seconds() / 86400)
        return price, pd.Timestamp(when) - observed


@contextmanager
def pricing_convention(data, fresh=False):
    """Apply a scoped research pricing adapter without changing installed packages."""
    from tradeexecutor.backtest.backtest_pricing import BacktestPricing

    init = BacktestPricing.__init__
    deposit = BacktestPricing.check_deposit
    redeem = BacktestPricing.check_redemption

    def initialise_price(self, *args, **kwargs):
        init(self, *args, **kwargs)
        if data["pricing_convention"] == "as_of_observation":
            self.candle_universe = ObservationPriceProxy(self.candle_universe, data)

    def stale(pair, t):
        q = observed_quote(data, pair.internal_id, t)
        return pair.is_vault() and (q is None or pd.Timestamp(t) - q[1] > pd.Timedelta(days=2))

    def check_deposit(self, ts, pair, *args, **kwargs):
        result = deposit(self, ts, pair, *args, **kwargs)
        if fresh and stale(pair, ts) and result.can_deposit:
            data["fresh_blocks"].append(dict(Context=data["run_context"], Date=ts, pair_id=pair.internal_id, Side="Buy"))
            result = replace(result, can_deposit=False, message="NB14 sensitivity: no actual NAV within one source two-day cycle")
        return result

    def check_redemption(self, ts, pair, *args, **kwargs):
        result = redeem(self, ts, pair, *args, **kwargs)
        if fresh and stale(pair, ts) and result.can_redeem:
            data["fresh_blocks"].append(dict(Context=data["run_context"], Date=ts, pair_id=pair.internal_id, Side="Sell"))
            result = replace(result, can_redeem=False, message="NB14 sensitivity: no actual NAV within one source two-day cycle")
        return result

    BacktestPricing.__init__ = initialise_price
    BacktestPricing.check_deposit = check_deposit
    BacktestPricing.check_redemption = check_redemption
    try:
        yield
    finally:
        BacktestPricing.__init__ = init
        BacktestPricing.check_deposit = deposit
        BacktestPricing.check_redemption = redeem


def replay(data, evaluator, arm, period, fresh=False):
    """Run a frozen arm under the shared pricing convention and isolated cache."""
    import score_matrix

    original = score_matrix.make_matrix_decision
    values = evaluator.panel.score_values
    weight = np.zeros(len(FEATURES))
    weight[0] = 1
    evaluator.panel.score_values = lambda *args, **kwargs: data["focal_values"]
    score_matrix.make_matrix_decision = lambda strategy, panel, values, sizing, allocator, ledger, **kwargs: decision_factory(data, strategy, panel, values, arm, ledger)
    data["run_context"] = (period, arm, "fresh" if fresh else "primary")
    try:
        with pricing_convention(data, fresh):
            return evaluator.run(weight, *PERIODS[period], n=6, sizing="inverse_variance", missing=True, profile=f"NB14-{arm}-" + ("fresh" if fresh else data["pricing_convention"]), keep=True)
    finally:
        score_matrix.make_matrix_decision = original
        evaluator.panel.score_values = values


def analyse_run(data, run, arm, period):
    """Reconcile economic outcomes, absolute exposure and vault profit."""
    state = run["result"].state
    eq = run["equity"].resample("1D").last().ffill()
    curves, positions = calculate_position_profit_curves(state, eq.index)
    residual = float(curves.sum(axis=1).iloc[-1] - (eq.iloc[-1] - 150000))
    assert abs(residual) < 1
    weights = calculate_asset_weights(state).unstack(fill_value=0).fillna(0).resample("1D").last().reindex(eq.index).ffill().fillna(0)
    assert np.allclose(weights.sum(axis=1), eq, atol=0.02, rtol=1e-8)
    reserve = state.portfolio.get_default_reserve_asset()[0].token_symbol
    absolute = weights.div(eq, axis=0)
    held = absolute.drop(columns=[reserve])
    m = {**run["metrics"], "Net profit (USD)": float(eq.iloc[-1] - 150000), "Mean cash weight": float(absolute[reserve].mean()), "Mean largest vault weight": float(held.max(axis=1).mean()), "Largest vault weight": float(held.max(axis=1).max()), "PnL residual (USD)": residual, "Best update": float(run["daily_returns"].max()), "Excess kurtosis": float(run["daily_returns"].kurt())}
    vault = positions.groupby("Vault")["Final profit (USD)"].sum()
    prefix = f"{period}-{arm}"
    curves.index.name = "date"
    curves.columns.name = "position_id"
    positions.index.name = None
    absolute.index.name = "date"
    curves.to_parquet(data["artifact"] / f"{prefix}-position-curves.parquet")
    positions.to_parquet(data["artifact"] / f"{prefix}-positions.parquet")
    absolute.to_parquet(data["artifact"] / f"{prefix}-absolute-weights.parquet")
    eq.to_csv(data["artifact"] / f"{prefix}-equity.csv")
    return m, vault, absolute


def run(data, evaluator):
    """Execute all five methods on both calendars, then two timing sensitivities."""
    records = []
    runs = {}
    attribution = {}
    weights = {}
    audits = []
    print("Ten required full engine results, then up to four sparse-price sensitivities; estimated 8–20 minutes.", flush=True)
    for period, arm in tqdm([(p, a) for p in PERIODS for a in ARMS], desc="NB14 engine replays", mininterval=15):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = replay(data, evaluator, arm, period)
        m, v, w = analyse_run(data, r, arm, period)
        runs[(period, arm)] = r
        attribution[(period, arm)] = v
        weights[(period, arm)] = w
        records.append(dict(Period=period, Arm=arm, Method=ARMS[arm][0], Pricing=data["pricing_convention"], **m))
        a = audit_trades(data, r, arm, period)
        audits.append(a)
        if data["pricing_convention"] == "as_of_observation":
            assert a.Matches_known_NAV.all(), a[~a.Matches_known_NAV].head()
        pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
    results = pd.DataFrame(records)
    # Trading only when a NAV was actually observed in the past source cycle is a sensitivity,
    # not a claim that older marks imply closed deposits or redemptions in the real protocol.
    sens = []
    for period in PERIODS:
        leader = results[results.Period.eq(period) & results.Arm.ne("A")].sort_values("Net profit (USD)", ascending=False).iloc[0].Arm
        for arm in ["A", leader]:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                r = replay(data, evaluator, arm, period, fresh=True)
            m, _, _ = analyse_run(data, r, arm, period + "-fresh")
            sens.append(dict(Period=period, Arm=arm, Method=ARMS[arm][0], **m))
    pd.DataFrame(sens).to_csv(data["artifact"] / "freshness-sensitivity.csv", index=False)
    pd.concat(audits, ignore_index=True).to_parquet(data["artifact"] / "trade-timing.parquet", index=False)
    if data["risk_ledger"]:
        pd.concat(data["risk_ledger"], ignore_index=True).to_parquet(data["artifact"] / "risk-ledger.parquet", index=False)
    queries = pd.DataFrame(data["quote_queries"].values())
    queries["Context"] = queries.Context.astype(str)
    queries.to_parquet(data["artifact"] / "quote-queries.parquet", index=False)
    pd.DataFrame(data["fresh_blocks"]).to_csv(data["artifact"] / "freshness-blocks.csv", index=False)
    return results, runs, attribution, weights, pd.DataFrame(sens)
