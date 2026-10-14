"""Freeze ten repaired-data leaders and replay their unchanged rules over all history."""

import datetime
import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import kurtosis
from tqdm_loggable.auto import tqdm
from accepted_dollar_cap import calculate_position_profit_curves
from allocation_followup import registry
from allocation_followup_engine import decision_factory
from precompute_repaired_singletons import create_evaluator
from score_input_count_experiment import configurations
from score_forecast_data import _eligibility, method_values
from score_matrix import FEATURES
from sizing_study_data import read_inputs
from repaired_data_replay import RUN_ROOT, RESEARCH_DIR
from tradeexecutor.analysis.weights import calculate_asset_weights

ROOT = RESEARCH_DIR
NB12 = RUN_ROOT / "12/465e3b8cf13b49e11f635d12c951268318e3b2c39e120f25b89190dd66606be5"
START = datetime.datetime(2023, 3, 1)
SHORT_END = datetime.datetime(2026, 10, 5)
END = datetime.datetime(2026, 10, 8)
PERIOD = "2023-03-01 → 2026-10-08 (end exclusive, UTC; final archive day partial)"
SHORT = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
FOCAL = "Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino"


def inventory():
    """Read executable repaired-data results; snapshot means are not CAGR."""
    old = pd.read_csv(RUN_ROOT / "07/2026-results.csv")
    old["Name"] = old.Configuration
    old["Origin"] = "NB06–07"
    old["Kind"] = "score"
    old["Score name"] = old.Score
    new = pd.read_parquet(NB12 / "engine_summary.parquet")
    new = new[~new.Arm.str.startswith("source")].copy()
    new["Name"] = "NB12 " + new.Arm + " " + new.Method
    new["Origin"] = "NB12"
    new["Kind"] = "allocation"
    new["Positions"] = 6
    new["Score name"] = FOCAL
    new["Policy"] = new.Arm
    # Earlier controls and calibration mechanisms remain eligible in the inventory.
    earlier = []
    for f, label, name in [("03/summary.csv", "NB01–03", "Run"), ("04/chart-2026-detailed-results.csv", "NB04", "Run"), ("05/2026-results.csv", "NB05", "Configuration")]:
        d = pd.read_csv(RUN_ROOT / f)
        if "Period" in d:
            d = d[d.Period.eq("Short") | d.Period.eq("2026")]
        d["Name"] = label + " " + d[name].astype(str)
        d["Origin"] = label
        d["Kind"] = "earlier"
        earlier.append(d)
    f = pd.read_csv(RUN_ROOT / "08/execution/2026-results.csv")
    # No-floor and inactive thresholds alias NB06–07. Random vetoes are placebos.
    f = f[(f["Rejected entry proposals"] > 0) & f.Seed.isna()].copy()
    f["Name"] = "NB08 " + f.Method + " / N" + f.Positions.astype(str) + " / " + f["Threshold policy"] + " / " + f.Treatment
    f["Origin"] = "NB08"
    f["Kind"] = "threshold"
    earlier.append(f)
    pool = pd.concat([old, new, *earlier], ignore_index=True)
    assert pool.Name.is_unique
    pool["CAGR rank"] = pool.CAGR.rank(ascending=False, method="min")
    pool["Sharpe rank"] = pool.Sharpe.rank(ascending=False, method="min")
    pool["Rank sum"] = pool["CAGR rank"] + pool["Sharpe rank"]
    ordered = pool.sort_values(["Rank sum", "CAGR", "Sharpe", "Name"], ascending=[True, False, False, True])
    primary = set(pool.nlargest(5, "CAGR").Name) | set(pool.nlargest(5, "Sharpe").Name)
    names = list(ordered[ordered.Name.isin(primary)].Name)
    names += list(ordered[~ordered.Name.isin(primary)].Name.head(10 - len(names)))
    chosen = pool.set_index("Name").loc[names].reset_index()
    assert len(chosen) == 10 and set(chosen.Kind) == {"score", "allocation"}, chosen[["Name", "Kind"]]
    chosen["Candidate"] = [f"C{i:02d}" for i in range(1, 11)]
    chosen["Selection reason"] = np.where(chosen.Name.isin(primary), "Top five CAGR and/or Sharpe", "Fill by equal-weight rank sum")
    return pool, chosen


def extend_evaluator(evaluator):
    """Load all pinned archive rows while freezing the existing vault identities."""
    import pickle
    import shutil
    from copy import deepcopy
    from tradingstrategy.client import Client
    from tradeexecutor.strategy.execution_context import notebook_execution_context
    from tradeexecutor.strategy.universe_model import UniverseOptions
    from tradeexecutor.strategy.pandas_trader.trading_universe_input import CreateTradingUniverseInput
    from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline, DiskIndicatorStorage
    from score_matrix import ScorePanel, MatrixConfig

    params = deepcopy(evaluator.parameters)
    params["backtest_start"] = START
    params["backtest_end"] = END
    folder = RUN_ROOT / "13/extended-inputs"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RUN_ROOT / "inputs/downloads.json").read_text())
    cache = folder / "client-cache"
    metadata = cache / "vaults/downloads/vault-metadata.json"
    metadata.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest["vault_metadata"]["path"], metadata)
    client = Client.create_jupyter_client(cache_path=str(cache))
    options = UniverseOptions.from_strategy_parameters_class(params, notebook_execution_context)
    options.vault_price_snapshot = Path(manifest["vault_prices"]["path"])
    original = evaluator.universe
    from tradingstrategy.chain import ChainId

    specs = [(ChainId(p.chain_id), p.pool_address) for p in original.iterate_pairs() if p.is_vault()]
    key = hashlib.sha256(json.dumps(dict(downloads=manifest, end=str(END), specs=[(c.value, a) for c, a in specs]), sort_keys=True).encode()).hexdigest()
    snapshot = folder / f"universe-{key}.pickle"
    if snapshot.exists():
        with snapshot.open("rb") as handle:
            universe = pickle.load(handle)
    else:
        factory = evaluator.strategy.build_hyperliquid_vault_universe
        evaluator.strategy.build_hyperliquid_vault_universe = lambda **kwargs: specs
        try:
            request = CreateTradingUniverseInput(client=client, timestamp=None, parameters=params, execution_context=notebook_execution_context, execution_model=None, universe_options=options)
            universe = evaluator.strategy.create_trading_universe(request)
        finally:
            evaluator.strategy.build_hyperliquid_vault_universe = factory
        with snapshot.open("wb") as handle:
            pickle.dump(universe, handle, pickle.HIGHEST_PROTOCOL)
    before = {p.internal_id: str(p.pool_address).lower() for p in original.iterate_pairs() if p.is_vault()}
    after = {p.internal_id: str(p.pool_address).lower() for p in universe.iterate_pairs() if p.is_vault()}
    assert before == after, "Extending dates must not change the vault universe"
    indicators_dir = folder / "indicators"
    indicators_dir.mkdir(exist_ok=True)
    indicators = calculate_and_load_indicators_inline(strategy_universe=universe, parameters=params, create_indicators=evaluator.strategy.create_indicators, execution_context=notebook_execution_context, max_workers=1, indicator_storage_path=indicators_dir)
    panel = ScorePanel(universe, START, END, MatrixConfig(), folder)
    evaluator.universe = universe
    evaluator.parameters = params
    evaluator.indicators = indicators
    evaluator.panel = panel
    evaluator.client = client
    evaluator.indicator_storage = DiskIndicatorStorage(indicators_dir, universe.get_cache_key())
    return key


def initialise():
    """Freeze shortlist and provenance before evaluating the long-history outcomes."""
    pool, chosen = inventory()
    evaluator, parameters, _, source_hash = create_evaluator(private_label="nb13")
    extension = extend_evaluator(evaluator)
    import k_ratio_features

    old_end = k_ratio_features.END
    k_ratio_features.END = pd.Timestamp(END)
    try:
        data = read_inputs()
    finally:
        k_ratio_features.END = old_end
    rows = configurations(evaluator.panel)
    data["score_configs"] = {r["Configuration"]: r for r in rows}
    data["policy_configs"] = {p["arm"]: p for p in registry()}
    origins = pd.date_range(START, END - datetime.timedelta(days=1), freq="2D").union(pd.date_range("2026-01-01", "2026-10-04", freq="2D"))
    data["eligibility"] = _eligibility(evaluator, origins, data["prices"])
    data["engine_solver_diagnostics"] = []
    method = next(r for r in data["registry"] if r["method_id"] == "focal_four")
    data["focal_values"] = method_values(evaluator.panel, method)[0]
    source_paths = [ROOT / n for n in ["long_candidate_backtest.py", "score_matrix.py", "allocation_followup.py", "allocation_followup_engine.py", "portfolio_snapshot_risk.py", "sizing_study_data.py"]]
    identity = dict(source_fingerprint=source_hash, extended_universe_fingerprint=extension, feature_panel=evaluator.panel.fingerprint, code={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}, shortlist=chosen[["Candidate", "Name", "Positions", "Kind", "Score name", "Policy"]].fillna("").to_dict("records"), shortlist_data={str(p.relative_to(RUN_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [RUN_ROOT / "07/2026-results.csv", NB12 / "engine_summary.parquet"]}, downloads=data["downloads"], start=str(START), end=str(END), control_arms=["v11", "regular90"])
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = RUN_ROOT / "13" / key
    folder.mkdir(parents=True, exist_ok=True)
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    pool.to_csv(folder / "inventory.csv", index=False)
    chosen.to_csv(folder / "shortlist.csv", index=False)
    first = pd.Timestamp(data["daily"].date.min())
    last = pd.Timestamp(data["daily"].date.max())
    # Preserve the existing calendar's empty lead-in; no positive observation precedes it.
    assert first >= pd.Timestamp(START) and last < pd.Timestamp(END), (first, last)
    manifest = dict(
        identity=identity,
        fingerprint=key,
        selection_rule="Union of top five 2026 CAGR and top five 2026 Sharpe; fill ten by ascending rank sum, descending CAGR, descending Sharpe and identity",
        observation_start=str(first),
        observation_end=str(last),
        warmup="All available pre-decision observations; no pre-launch price backfill",
        excluded_aliases="NB06 duplicated in NB07; NB12 original controls duplicated in NB07; NB08 no-floor/inactive thresholds duplicate NB06–07; random vetoes are placebo controls",
        no_engine_results="NB09–11 feature and snapshot studies have no comparable executable CAGR; all implemented NB11 engine controls are included through NB12",
        hypotheses="2026 leaders retain relative gains over source v11 and regular90 across full history",
        initial_cash=150000,
        missing=True,
        rebalancing="source two-day engine",
        nav_only_fill=True,
        concentration_cap=0.33,
        allocation_pct=0.98,
        caveats=["Long history was previously searched; overlapping 2026 selection is not a holdout", "Current inventory and guard history are not historically complete", "Archived permission clocks are retained without inventing receipts", "Daily grid equity returns contain two-day valuation changes"],
    )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    data.update(artifact=folder, figures=[], manifest=manifest)
    return data, evaluator, chosen, pool


def replay_one(data, evaluator, row, start, end):
    """Apply exactly the selected score/allocator, including source missing handling."""
    import score_matrix

    original = score_matrix.make_matrix_decision
    score_values = evaluator.panel.score_values
    weight = np.zeros(len(FEATURES))
    weight[0] = 1.0
    try:
        if row["Kind"] == "control_source":
            return evaluator.run(weight, start, end, n=6, source_control=True, keep=True)
        if row["Kind"] == "allocation":
            policy = data["policy_configs"][row["Policy"]]
            evaluator.panel.score_values = lambda *args, **kwargs: data["focal_values"]
            score_matrix.make_matrix_decision = lambda strategy, panel, values, sizing, allocator, ledger, **kwargs: decision_factory(strategy, panel, values, policy, data, ledger)
            return evaluator.run(weight, start, end, n=6, sizing="inverse_variance", missing=True, profile="NB13-" + policy["arm"], keep=True)
        config = data["score_configs"][row["Score name"]]
        return evaluator.run(config["Weights"], start, end, n=int(row["Positions"]), sizing="inverse_variance", missing=True, profile=config["Profile"], keep=True)
    finally:
        score_matrix.make_matrix_decision = original
        evaluator.panel.score_values = score_values


def run(data, evaluator, chosen):
    """Check 2026 parity, then run ten frozen candidates plus two explicit controls."""
    controls = [dict(Candidate="B01", Name="Unchanged v11", Kind="control_source", Positions=6, CAGR=0.4120044377, Sharpe=1.95958994), dict(Candidate="B02", Name="Focal regularised90 benchmark", Kind="allocation", Policy="S03", Positions=6, CAGR=0.466005, Sharpe=2.091681)]
    records = chosen.to_dict("records") + controls
    parity = []
    runs = {}
    metrics = []
    print("12 source-equivalence checks plus 12 full-history engine replays; estimated 8–18 minutes, serial execution.", flush=True)
    for row in tqdm(records, desc="NB13 source-equivalence and long engine replays", mininterval=15):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            short = replay_one(data, evaluator, row, datetime.datetime(2026, 1, 1), SHORT_END)
        for metric in ("CAGR", "Sharpe"):
            error = short["metrics"][metric] - float(row[metric])
            assert abs(error) < 2e-6, (row["Name"], metric, error)
            parity.append(dict(Candidate=row["Candidate"], Metric=metric, Expected=row[metric], Observed=short["metrics"][metric], Difference=error))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            long = replay_one(data, evaluator, row, START, END)
        name = row["Candidate"]
        runs[name] = long
        m = dict(Candidate=name, Name=row["Name"], Positions=row["Positions"], Origin=row.get("Origin", "Benchmark"), Kind=row["Kind"], **long["metrics"], **{"2026 CAGR": short["metrics"]["CAGR"], "2026 Sharpe": short["metrics"]["Sharpe"]}, cache_key=long["cache_key"])
        metrics.append(m)
        pd.DataFrame(metrics).to_csv(data["artifact"] / "long-results.csv", index=False)
    parity = pd.DataFrame(parity)
    parity.to_csv(data["artifact"] / "replication.csv", index=False)
    summary = pd.DataFrame(metrics)
    robustness = []
    attribution = []
    tail = []
    weights = {}
    quarter = {}
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined
    from tradingstrategy.binance.price import fetch_binance_price

    market = {s: fetch_binance_price(symbol=s, request_timeout=10.0) for s in ("BTCUSDT", "ETHUSDT")}
    for name, result in runs.items():
        state = result["result"].state
        eq = result["equity"].resample("1D").last().ffill()
        dr = result["daily_returns"]
        curves, meta = calculate_position_profit_curves(state, eq.index)
        residual = curves.sum(axis=1).iloc[-1] - (eq.iloc[-1] - 150000)
        assert abs(residual) < 1.0, (name, residual)
        totals = meta.groupby("Vault")["Final profit (USD)"].sum().sort_values(ascending=False)
        positive = totals[totals > 0]
        best = dr.idxmax()
        zeroed = dr.copy()
        zeroed.loc[best] = 0.0
        from tradeexecutor.statistics.key_metric import calculate_sharpe

        robustness.append(dict(Candidate=name, **{"Best update": dr.max(), "Worst update": dr.min(), "Best update date": str(best.date()), "Excess kurtosis": kurtosis(dr, fisher=True), "Top vault": totals.index[0], "Top positive profit share": positive.iloc[0] / positive.sum(), "Sharpe with best update zeroed": calculate_sharpe(zeroed, periods=365), "PnL residual (USD)": residual}))
        for vault, pnl in totals.items():
            attribution.append(dict(Candidate=name, Vault=vault, PnL=pnl))
        previous = result["equity"].index[result["equity"].index < best].max()
        anchor = (pd.Timestamp(previous) - pd.Timedelta(days=1)).floor("D")
        end = (best - pd.Timedelta(days=1)).floor("D")
        profit_change = curves.diff().loc[best].groupby(meta.set_index("Position id").Vault).sum().sort_values(ascending=False)
        for vault, delta in profit_change.head(3).items():
            address = meta[meta.Vault.eq(vault)].iloc[0].Address
            marks = data["daily"][data["daily"].address.eq(address) & data["daily"].date.between(anchor, end)].set_index("date").share_price
            tail.append(dict(Candidate=name, Update=best, Asset=vault, PnL=delta, Anchor=anchor, Endpoint=end, Actual_marks=len(marks), NAV_return=float(marks.iloc[-1] / marks.iloc[0] - 1) if len(marks) > 1 else np.nan, Curator_excluded=address in EXCLUDED_VAULTS, Quarantined=is_quarantined(address, best)))
        for symbol, df in market.items():
            p = df.loc[anchor:end, "close"]
            tail.append(dict(Candidate=name, Update=best, Asset=symbol, PnL=np.nan, Anchor=anchor, Endpoint=end, Actual_marks=len(p), NAV_return=float(p.iloc[-1] / p.iloc[0] - 1) if len(p) > 1 else np.nan, Curator_excluded=False, Quarantined=False))
        frame = calculate_asset_weights(state).unstack(fill_value=0).fillna(0).resample("1D").last().reindex(eq.index).ffill().fillna(0)
        assert np.allclose(frame.sum(axis=1), eq, atol=0.02, rtol=1e-8), (name, (frame.sum(axis=1) - eq).abs().max())
        weights[name] = frame
        frame.index.name = "date"
        frame.to_parquet(data["artifact"] / f"{name}-absolute-weights.parquet")
        curves.index.name = "date"
        curves.to_parquet(data["artifact"] / f"{name}-position-curves.parquet")
        meta["Candidate"] = name
        meta.to_parquet(data["artifact"] / f"{name}-positions.parquet", index=False)
        quarter[name] = (1 + dr).groupby(dr.index.to_period("Q")).prod() - 1
    robustness = pd.DataFrame(robustness)
    robustness.to_csv(data["artifact"] / "robustness.csv", index=False)
    pd.DataFrame(attribution).to_csv(data["artifact"] / "vault-attribution.csv", index=False)
    pd.DataFrame(tail).to_csv(data["artifact"] / "tail-audit.csv", index=False)
    quarter = pd.DataFrame(quarter)
    quarter.to_csv(data["artifact"] / "quarter-returns.csv")
    (data["artifact"] / "complete.json").write_text(json.dumps(dict(status="complete", candidates=10, benchmarks=2, parity_checks=len(parity), period=PERIOD, pnl_reconciled=True), indent=2))
    return summary, runs, robustness, weights, quarter
