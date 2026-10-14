"""Isolate legacy capacity consumption after the October permission-clock recovery."""

import datetime
import hashlib
import importlib.util
import json
import os
import pickle
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tradingstrategy.client import Client
from tradeexecutor.strategy.parameters import StrategyParameters
from tradeexecutor.strategy.execution_context import notebook_execution_context
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
from repaired_data_replay import RUN_ROOT, RESEARCH_DIR, INDICATOR_DIR, repaired_indicator_storage
from score_matrix import MatrixBacktester, FEATURES


def main():
    load_dotenv(override=True)
    source = Path("/Users/moo/code/strategies/strategy/hyper-ai-v11.py")
    os.environ["HYPER_AI_GUARD_CONFIG_FILE"] = "/Users/moo/code/strategies/deploy/hyper-ai-v10-new-guard-vault-info.json"
    spec = importlib.util.spec_from_file_location("hyper_ai_v11_repaired_audit", source)
    strategy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy)
    parameters = StrategyParameters.from_class(strategy.Parameters)
    client = Client.create_jupyter_client()
    with (RUN_ROOT / "universe.pickle").open("rb") as handle:
        universe = pickle.load(handle)
    with (RESEARCH_DIR / "_artifacts-calibration-05/universe.pickle").open("rb") as handle:
        prior = pickle.load(handle)
    indicators = calculate_and_load_indicators_inline(strategy_universe=universe, parameters=parameters, create_indicators=strategy.create_indicators, execution_context=notebook_execution_context, max_workers=1, indicator_storage_path=INDICATOR_DIR)
    target = universe.vault_state.copy()
    legacy = prior.vault_state[["pair_id", "timestamp", "max_deposit"]].copy().rename(columns={"timestamp": "legacy_bucket", "max_deposit": "legacy_cap"})
    legacy["legacy_bucket"] = legacy["legacy_bucket"].astype("datetime64[ns]")
    target["timestamp"] = target["timestamp"].astype("datetime64[ns]")
    pieces = []
    for pid, group in target.groupby("pair_id"):
        history = legacy[legacy.pair_id.eq(pid)].drop(columns="pair_id").sort_values("legacy_bucket")
        merged = pd.merge_asof(group.sort_values("timestamp"), history, left_on="timestamp", right_on="legacy_bucket", tolerance=pd.Timedelta("2d"))
        merged["max_deposit"] = merged["legacy_cap"]
        merged["capacity_observed_at"] = merged["legacy_bucket"].where(merged.legacy_cap.notna())
        pieces.append(merged.drop(columns=["legacy_bucket", "legacy_cap"]))
    restored = pd.concat(pieces, ignore_index=True)
    gucky = next(p for p in universe.iterate_pairs() if p.pool_address == "0x3a6747c8e913085e243a2c22d188dafa8c6a612a")
    only = target.copy()
    replacement = restored[restored.pair_id.eq(gucky.internal_id)].set_index("timestamp")
    mask = only.pair_id.eq(gucky.internal_id)
    for column in ["max_deposit", "capacity_observed_at"]:
        only.loc[mask, column] = only.loc[mask, "timestamp"].map(replacement[column]).to_numpy()
    cases = [("Repaired source", universe), ("Diagnostic: legacy Gucky cap only", replace(universe, vault_state=only)), ("Diagnostic: all legacy caps", replace(universe, vault_state=restored))]
    output = RUN_ROOT / "capacity-audit"
    output.mkdir(exist_ok=True)
    weights = np.zeros(len(FEATURES))
    weights[40] = 1
    rows = []
    for label, case in cases:
        print("Running " + label, flush=True)
        digest = hashlib.sha256(Path(__file__).read_bytes() + label.encode() + source.read_bytes()).hexdigest()
        evaluator = MatrixBacktester(strategy, case, indicators, parameters, client, None, output, digest, indicator_storage=repaired_indicator_storage(universe))
        run = evaluator.run(weights, datetime.datetime(2026, 1, 1), parameters.backtest_end, source_control=True, keep=True)
        rows.append({"Case": label, **run["metrics"], "Fingerprint": digest, "Cache key": run["cache_key"]})
        pd.DataFrame(rows).to_csv(output / "results.csv", index=False)
        print(pd.DataFrame(rows)[["Case", "Final equity (USD)", "CAGR", "Sharpe", "Maximum drawdown", "Trades"]].to_string(index=False), flush=True)
    print("Legacy caps are artificial diagnostic interventions; they are not authenticated historical capacity.", flush=True)


if __name__ == "__main__":
    main()
