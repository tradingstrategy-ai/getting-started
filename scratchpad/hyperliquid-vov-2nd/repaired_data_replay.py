"""Load one pinned repaired input generation across the existing experiments."""

import hashlib
import json
import pickle
import shutil

from tradingstrategy.client import Client
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent
RUN_ROOT = RESEARCH_DIR / "_artifacts-restored-2026-10-07"
INPUT_DIR = RUN_ROOT / "inputs"
INDICATOR_DIR = RUN_ROOT / "indicators"


def load_repaired_universe(strategy, request):
    """Share the source universe while preserving independent portfolio executions."""
    manifest = json.loads((INPUT_DIR / "downloads.json").read_text())
    prices = Path(manifest["vault_prices"]["path"])
    assert hashlib.sha256(prices.read_bytes()).hexdigest() == manifest["vault_prices"]["sha256"]
    metadata = Path(manifest["vault_metadata"]["path"])
    assert hashlib.sha256(metadata.read_bytes()).hexdigest() == manifest["vault_metadata"]["sha256"]
    # Pin metadata in a private client cache alongside the verified price input.
    cache = RUN_ROOT / "client-cache"
    destination = cache / "vaults" / "downloads" / "vault-metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(metadata, destination)
    request.client = Client.create_jupyter_client(cache_path=str(cache))
    request.universe_options.vault_price_snapshot = prices
    snapshot = RUN_ROOT / "universe.pickle"
    if snapshot.exists():
        with snapshot.open("rb") as handle:
            return pickle.load(handle)
    universe = strategy.create_trading_universe(request)
    with snapshot.open("wb") as handle:
        pickle.dump(universe, handle, pickle.HIGHEST_PROTOCOL)
    return universe


def save_metrics(runs, folder):
    """Save comparison metrics outside notebook outputs in the ignored run folder."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metrics.json").write_text(json.dumps({label: run["metrics"] for label, run in runs.items()}, indent=2))
    for index, (label, run) in enumerate(runs.items()):
        run["equity"].to_csv(folder / f"{index:02d}-equity.csv")
        run["result"].state.write_json_file(folder / f"{index:02d}-state.json")


def repaired_indicator_storage(universe):
    """Use the same indicator directory for preparation and engine loading."""
    from tradeexecutor.strategy.pandas_trader.indicator import DiskIndicatorStorage

    return DiskIndicatorStorage(INDICATOR_DIR, universe.get_cache_key())
