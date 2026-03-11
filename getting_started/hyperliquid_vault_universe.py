"""Dynamic Hyperliquid (Hypercore) vault universe construction with caching.

Fetches all qualifying Hypercore vaults from the Trading Strategy API,
filters them using the same logic as scripts/hyperliquid-filter-top-vaults.py,
and caches the result per notebook ID.

Cache is stored in ~/.cache/indicators/ alongside indicator caches,
so it is cleared by the existing /clear-backtesting-cache skill.
"""

import json
import sys
from pathlib import Path

from tradingstrategy.chain import ChainId

from getting_started.vault_universe_creation import (
    fetch_vaults,
    parse_vault,
    select_top_vaults,
)

DATA_URL = "https://top-defi-vaults.tradingstrategy.ai/top_vaults_by_chain.json"

CHAIN_CONFIG = {
    9999: {"name": "Hypercore", "enum": "HYPERCORE_CHAIN_ID", "top_n": 120},
}

CHAIN_ORDER = [9999]

ALLOWED_DENOMINATIONS = {
    "USDC", "USDC.E",
    "USDT", "USD₮0", "USDT0", "USDT.E",
    "CRVUSD",
    "USDS",
}

EXCLUDED_RISKS = {"Blacklisted", "Dangerous"}
EXCLUDED_FLAGS = {"malicious", "broken"}
REQUIRE_KNOWN_PROTOCOL = True

TRACKED_PERIODS = ("1M", "3M", "1Y")

CACHE_DIR = Path.home() / ".cache" / "indicators"


def _cache_path(notebook_id: str) -> Path:
    return CACHE_DIR / f"{notebook_id}-vault-universe.json"


def _load_cache(notebook_id: str) -> list[tuple[ChainId, str]] | None:
    """Load cached vault universe if it exists."""
    path = _cache_path(notebook_id)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return [(ChainId(entry["chain_id"]), entry["address"]) for entry in data]


def _save_cache(notebook_id: str, vaults: list[tuple[ChainId, str]]) -> None:
    """Save vault universe to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = [{"chain_id": chain_id.value, "address": address} for chain_id, address in vaults]
    with open(_cache_path(notebook_id), "w") as f:
        json.dump(data, f, indent=2)


def build_hyperliquid_vault_universe(
    notebook_id: str,
    min_tvl: float = 10_000,
    top_n: int = 120,
    min_age: float = 0.15,
    sort_period: str = "1Y",
) -> list[tuple[ChainId, str]]:
    """Build a filtered Hypercore vault universe, cached per notebook.

    Fetches all Hypercore vaults from the Trading Strategy API, applies
    quality filters (denomination, risk, flags, TVL, age), and returns
    a list of (ChainId, address) tuples ready for ``limit_to_vaults()``.

    Uses ``skip_cagr_filter=True`` to avoid survivorship bias in
    backtesting.

    :param notebook_id:
        Notebook identifier (from ``get_notebook_id(globals())``).
        Used as cache key.
    :param min_tvl:
        Minimum TVL in USD.
    :param top_n:
        Maximum number of vaults to include.
    :param min_age:
        Minimum vault age in years.
    :param sort_period:
        CAGR period used for ranking (``"1M"``, ``"3M"``, or ``"1Y"``).
    :return:
        List of ``(ChainId.hypercore, "0x...")`` tuples.
    """
    cached = _load_cache(notebook_id)
    if cached is not None:
        print(f"Loaded {len(cached)} cached Hypercore vaults for {notebook_id}", file=sys.stderr)
        return cached

    chain_config = dict(CHAIN_CONFIG)
    chain_config[9999] = {**chain_config[9999], "top_n": top_n}

    raw_vaults = fetch_vaults(DATA_URL)

    parsed = []
    for rv in raw_vaults:
        v = parse_vault(rv, chain_config, TRACKED_PERIODS)
        if v is not None:
            parsed.append(v)

    print(f"Parsed {len(parsed)} Hypercore vaults from API", file=sys.stderr)

    selected = select_top_vaults(
        parsed,
        min_tvl,
        min_age,
        chain_config,
        CHAIN_ORDER,
        sort_period,
        allowed_denominations=ALLOWED_DENOMINATIONS,
        excluded_risks=EXCLUDED_RISKS,
        excluded_flags=EXCLUDED_FLAGS,
        require_known_protocol=REQUIRE_KNOWN_PROTOCOL,
        hypercore_min_tvl=min_tvl,
        top_n_override=top_n,
        skip_cagr_filter=True,
    )

    result = []
    for chain_id in CHAIN_ORDER:
        for v in selected.get(chain_id, []):
            if not v.excluded and v.excluded_protocol_reason is None:
                result.append((ChainId.hypercore, v.address))

    print(f"Selected {len(result)} Hypercore vaults (min TVL ${min_tvl:,.0f}, top {top_n})", file=sys.stderr)

    _save_cache(notebook_id, result)
    return result
