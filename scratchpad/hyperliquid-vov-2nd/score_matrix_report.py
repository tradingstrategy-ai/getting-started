"""Read the saved experiment snapshot without refreshing its market dataset."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tradeexecutor.backtest.backtest_runner import BacktestResult
from tradeexecutor.state.state import State
from tradeexecutor.visual.equity_curve import calculate_equity_curve, calculate_returns
from score_matrix import MatrixConfig, ScorePanel


class SavedExperiment:
    """Use only recorded engine results from the original experiment fingerprint.

    A presentation refresh must not replace the universe or silently execute
    a new configuration against a newer remote dataset.
    """

    def __init__(self, folder, parameters):
        self.root = Path(folder)
        self.manifest = json.loads((self.root / "run-manifest.json").read_text())
        self.short_manifest = json.loads((self.root / "chart-2026-manifest.json").read_text())
        assert self.manifest["fingerprint"] == self.short_manifest["fingerprint"]
        self.folder = self.root / self.manifest["fingerprint"][:16]
        self.parameters = parameters
        self.records = {r["key"]: r for r in self.manifest["evaluations"]}
        self.engine_calls = 0
        self.available = list(self.manifest["evaluations"]) + list(self.short_manifest["evaluations"])
        feature = self.manifest["inputs"]["feature_panel"]
        panel = ScorePanel.__new__(ScorePanel)
        panel.config = MatrixConfig()
        panel.fingerprint = feature
        with np.load(self.root / f"features-{feature}.npz") as stored:
            panel.raw, panel.floored, panel.valid, panel.nonflat = [stored[k] for k in ["raw", "floored", "valid", "nonflat"]]
        start, end = self.manifest["period"]
        panel.dates = pd.date_range(pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1))
        panel.date_index = {ts: i for i, ts in enumerate(panel.dates)}
        panel.pair_index = {}
        self.panel = panel
        self.name_index = {name: i for i, name in enumerate(pd.read_csv(self.root / "v6-score-preflight.csv").Vault)}
        assert len(self.name_index) == panel.raw.shape[1]

    def find(self, weights, start, end, n=6, sizing="equal", allocator="parent", source_control=False, calmar_cap=5.0, missing=False, profile="requested"):
        """Find the exact saved configuration, including its period and source flag."""
        w = np.asarray(weights)
        matches = [r for r in self.available if pd.Timestamp(r["start"]) == pd.Timestamp(start) and pd.Timestamp(r["end"]) == pd.Timestamp(end) and r["positions"] == n and r["sizing"] == sizing and r["allocator"] == allocator and r["source_control"] == source_control and r["missing"] == missing and r["profile"] == profile and float(r["calmar_cap"]) == float(calmar_cap) and np.allclose(r["weights"], w, rtol=0, atol=1e-10)]
        if not matches:
            raise ValueError("Configuration has no saved replay in the frozen experiment snapshot. Run a separate data refresh before requesting a new backtest.")
        # Numerically identical integer/float cap values can have different
        # cache keys; prefer the record that also retains its complete state.
        return max(matches, key=lambda r: (self.folder / f'{r["key"]}-state.json').exists())

    def run(self, weights, start, end, n=6, sizing="equal", allocator="parent", keep=False, source_control=False, calmar_cap=5.0, missing=False, profile="requested"):
        """Return the recorded metrics and, when requested, the full saved state."""
        record = self.find(weights, start, end, n, sizing, allocator, source_control, calmar_cap, missing, profile)
        key = record["key"]
        metrics = json.loads((self.folder / f"{key}.json").read_text())
        self.records[key] = record
        if not keep:
            return metrics
        state = State.read_json_file(self.folder / f"{key}-state.json")
        ledger_path = self.folder / f"{key}-allocations.csv"
        ledger = pd.read_csv(ledger_path, parse_dates=["Date"]) if not source_control and ledger_path.exists() else pd.DataFrame()
        if len(ledger):
            for pid, name in ledger[["Pair id", "Vault"]].drop_duplicates().itertuples(index=False, name=None):
                self.panel.pair_index[int(pid)] = self.name_index[name]
        parameters = deepcopy(self.parameters)
        parameters["backtest_start"] = pd.Timestamp(start).to_pydatetime()
        parameters["backtest_end"] = pd.Timestamp(end).to_pydatetime()
        parameters["max_assets_in_portfolio"] = parameters["max_capacity_assets"] = n
        parameters["entry_rank"] = n
        parameters["exit_rank"] = n + 2
        parameters["weighting_method"] = sizing
        result = BacktestResult(state, None, {}, None)
        equity = calculate_equity_curve(state)
        daily = calculate_returns(equity).resample("1D").sum(min_count=1).fillna(0)
        return {"result": result, "parameters": parameters, "equity": equity, "daily_returns": daily, "metrics": metrics, "allocation_df": ledger, "cache_key": key}

    def remaining(self, jobs):
        """Saved replays require no engine execution."""
        return 0.0
