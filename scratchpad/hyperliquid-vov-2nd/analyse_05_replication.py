"""Isolate the experiment 04/05 discrepancy using saved inputs and fresh source runs."""

import datetime
import hashlib
import importlib.util
import json
import os
import pickle
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tradingstrategy.client import Client
from tradingstrategy.alternative_data.vault import read_vault_price_history_parquet, convert_vault_prices_to_candles, convert_vault_prices_to_vault_state, VAULT_STATE_COLUMNS
from tradingstrategy.candle import GroupedCandleUniverse
from tradingstrategy.liquidity import GroupedLiquidityUniverse
from tradeexecutor.strategy.parameters import StrategyParameters
from tradeexecutor.strategy.execution_context import notebook_execution_context
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline

RESEARCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RESEARCH_DIR))
from score_matrix import MatrixBacktester, FEATURES


def main():
    load_dotenv(override=True)
    source = Path("/Users/moo/code/strategies/strategy/hyper-ai-v11.py")
    guard = Path("/Users/moo/code/strategies/deploy/hyper-ai-v10-new-guard-vault-info.json")
    os.environ["HYPER_AI_GUARD_CONFIG_FILE"] = str(guard)
    spec = importlib.util.spec_from_file_location("hyper_ai_v11_replication_audit", source)
    strategy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy)
    parameters = StrategyParameters.from_class(strategy.Parameters)
    client = Client.create_jupyter_client()
    output = RESEARCH_DIR / "_artifacts-root-cause-05"
    output.mkdir(exist_ok=True)
    snapshot = RESEARCH_DIR / "_artifacts-calibration-05/universe.pickle"
    with snapshot.open("rb") as handle:
        original = pickle.load(handle)
    old_prices = Path("/Users/moo/code/strategies/cache/hyper-ai/vaults/downloads/vault-prices.parquet")
    lower = datetime.datetime(2026, 9, 15)
    upper = datetime.datetime(2026, 9, 28)
    pairs = original.data_universe.pairs.df
    raw = read_vault_price_history_parquet(old_prices, vault_pairs_df=pairs, start_at=lower, end_at=upper - datetime.timedelta(microseconds=1), columns=["chain", "address", "timestamp", "share_price", "total_assets", *VAULT_STATE_COLUMNS, "written_at"])
    states = convert_vault_prices_to_vault_state(raw, "1d")
    prices, tvl = convert_vault_prices_to_candles(raw, "1d")
    vault_ids = {p.internal_id for p in original.iterate_pairs() if p.is_vault()}

    def splice(frame, addition):
        frame = frame.reset_index(drop=True).drop(columns=["index"], errors="ignore")
        mask = frame.pair_id.isin(vault_ids) & frame.timestamp.ge(lower) & frame.timestamp.lt(upper)
        addition = addition.reset_index(drop=True)
        addition["forward_filled"] = False
        return pd.concat([frame[~mask], addition], ignore_index=True).sort_values(["pair_id", "timestamp"])

    candle_frame = splice(original.data_universe.candles.df, prices)
    liquidity_frame = splice(original.data_universe.liquidity.df, tvl)
    candle_universe = GroupedCandleUniverse(candle_frame, time_bucket=parameters.candle_time_bucket, fix_wick_threshold=None, fix_inbetween_threshold=None, remove_candles_with_zero_volume=False, bad_open_close_threshold=None, min_max_price=None)
    candle_universe.df = candle_universe.df.set_index(["pair_id", "timestamp"], drop=False)
    candle_universe.pairs = candle_universe.df.groupby(candle_universe.df["pair_id"])
    tvl_universe = GroupedLiquidityUniverse(liquidity_frame, time_bucket=parameters.candle_time_bucket)
    tvl_universe.df = tvl_universe.df.set_index(["pair_id", "timestamp"], drop=False)
    tvl_universe.pairs = tvl_universe.df.groupby(tvl_universe.df["pair_id"])
    state_frame = splice(original.vault_state, states).drop(columns=["forward_filled"], errors="ignore")
    restored = replace(original, data_universe=replace(original.data_universe, candles=candle_universe, liquidity=tvl_universe), vault_state=state_frame, other_data={**original.other_data, "indicator_cache_fingerprint": "replication-audit-dense-september-v2"})
    print("Calculating the frozen 05 source indicators.", flush=True)
    indicators = calculate_and_load_indicators_inline(strategy_universe=original, parameters=parameters, create_indicators=strategy.create_indicators, execution_context=notebook_execution_context, max_workers=1)
    print("Calculating indicators after restoring dense 15–27 September inputs.", flush=True)
    restored_indicators = calculate_and_load_indicators_inline(strategy_universe=restored, parameters=parameters, create_indicators=strategy.create_indicators, execution_context=notebook_execution_context, max_workers=1)
    cases = [
        ("Fresh 05 source", original, indicators),
        ("Dense candles; 05 indicators and state", replace(original, data_universe=replace(original.data_universe, candles=candle_universe)), indicators),
        ("Dense candles and recalculated indicators; 05 TVL and state", replace(original, data_universe=replace(original.data_universe, candles=candle_universe)), restored_indicators),
        ("Earlier deposit state only; 05 prices and indicators", replace(original, vault_state=state_frame), indicators),
        ("Dense candles, indicators, TVL and state", restored, restored_indicators),
    ]
    rows = []
    weights = np.zeros(len(FEATURES))
    weights[40] = 1
    for label, universe, indicator_data in cases:
        print("Running uncached source case: " + label, flush=True)
        # Separate run identities from notebook 05, including this script and both input files.
        digest = hashlib.sha256(Path(__file__).read_bytes() + label.encode() + source.read_bytes() + snapshot.read_bytes() + old_prices.read_bytes()).hexdigest()
        engine = MatrixBacktester(strategy, universe, indicator_data, parameters, client, None, output, digest)
        result = engine.run(weights, datetime.datetime(2026, 1, 1), parameters.backtest_end, n=6, sizing="inverse_variance", missing=True, source_control=True, keep=True)
        rows.append({"Case": label, **result["metrics"], "Engine calls": engine.engine_calls, "Cache key": result["cache_key"], "Fingerprint": digest})
        result["equity"].to_csv(output / (digest[:16] + "-equity.csv"))
        pd.DataFrame(rows).to_csv(output / "input-swap-results.csv", index=False)
        print(pd.DataFrame(rows)[["Case", "Final equity (USD)", "CAGR", "Sharpe", "Maximum drawdown"]].to_string(index=False), flush=True)
    return rows


if __name__ == "__main__":
    main()
