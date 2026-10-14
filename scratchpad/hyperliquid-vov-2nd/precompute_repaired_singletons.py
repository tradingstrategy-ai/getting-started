"""Execute independent 2026 singleton controls alongside the long-history fit."""

import datetime
import hashlib
import importlib.util
import io
import json
import os
import pickle
import time
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from tradingstrategy.client import Client
from tradeexecutor.strategy.execution_context import notebook_execution_context
from tradeexecutor.strategy.parameters import StrategyParameters
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
from repaired_data_replay import RESEARCH_DIR, RUN_ROOT, INDICATOR_DIR, repaired_indicator_storage
from score_matrix import MatrixConfig, ScorePanel, MatrixBacktester, FEATURES, SEARCH_FEATURES
from score_matrix_blends import register_score_blend


def create_evaluator(private_label=None):
    load_dotenv(override=True)
    source = Path("/Users/moo/code/strategies/strategy/hyper-ai-v11.py")
    guard = Path("/Users/moo/code/strategies/deploy/hyper-ai-v10-new-guard-vault-info.json")
    os.environ["HYPER_AI_GUARD_CONFIG_FILE"] = str(guard)
    spec = importlib.util.spec_from_file_location("hyper_ai_v11_short_singletons", source)
    strategy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(strategy)
    parameters = StrategyParameters.from_class(strategy.Parameters)
    client = Client.create_jupyter_client()
    folder = RUN_ROOT / "04"
    with (RUN_ROOT / "universe.pickle").open("rb") as handle:
        universe = pickle.load(handle)
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        indicators = calculate_and_load_indicators_inline(strategy_universe=universe, parameters=parameters, create_indicators=strategy.create_indicators, execution_context=notebook_execution_context, max_workers=1, indicator_storage_path=INDICATOR_DIR)
        panel = ScorePanel(universe, datetime.datetime(2023, 3, 1), parameters.backtest_end, MatrixConfig(), folder)
    framework = [Path("/Users/moo/code/trade-executor/tradeexecutor") / p for p in ["strategy/alpha_model.py", "strategy/runner.py", "backtest/backtest_runner.py", "backtest/backtest_execution.py", "visual/equity_curve.py", "strategy/pandas_trader/position_manager.py", "backtest/backtest_pricing.py", "strategy/trading_strategy_universe.py"]]
    framework += [Path("/Users/moo/code/trade-executor/deps/trading-strategy/tradingstrategy") / p for p in ["alternative_data/vault.py", "vault_permission.py"]]
    inputs = {"feature_panel": panel.fingerprint, "strategy": hashlib.sha256(source.read_bytes()).hexdigest(), "v6": hashlib.sha256(Path("/Users/moo/code/strategies/strategy/hyper-ai-v6.py").read_bytes()).hexdigest(), "guard": hashlib.sha256(guard.read_bytes()).hexdigest(), "cap_harness": hashlib.sha256((RESEARCH_DIR / "accepted_dollar_cap.py").read_bytes()).hexdigest(), "repaired_inputs": json.loads((RUN_ROOT / "inputs/downloads.json").read_text()), **{str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in framework}}
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    assert (folder / fingerprint[:16]).is_dir(), "Input generation must match the active notebook"
    destination = folder if private_label is None else folder / private_label
    destination.mkdir(exist_ok=True)
    evaluator = MatrixBacktester(strategy, universe, indicators, parameters, client, panel, destination, fingerprint, indicator_storage=repaired_indicator_storage(universe))
    return evaluator, parameters, folder, fingerprint


def main():
    evaluator, parameters, folder, fingerprint = create_evaluator()
    jobs = [(i, missing) for i in SEARCH_FEATURES for missing in [False, True]]
    timings = []
    for index, (feature, missing) in enumerate(jobs, 1):
        started = time.monotonic()
        weights = np.zeros(len(FEATURES))
        weights[feature] = 1
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            metrics = evaluator.run(weights, datetime.datetime(2026, 1, 1), parameters.backtest_end, missing=missing)
        timings.append(time.monotonic() - started)
        remaining = np.mean(timings[-10:]) * (len(jobs) - index) / 60
        print(f'{index}/{len(jobs)}: {FEATURES[feature]}, missing={missing}, CAGR={metrics["CAGR"]:.2%}, Sharpe={metrics["Sharpe"]:.2f}; remaining ~{remaining:.1f} min', flush=True)
        (folder / "short-singleton-worker.json").write_text(json.dumps({"fingerprint": fingerprint, "engine_calls": evaluator.engine_calls, "completed": index, "total": len(jobs), "evaluations": list(evaluator.records.values())}, indent=2))


if __name__ == "__main__":
    main()
