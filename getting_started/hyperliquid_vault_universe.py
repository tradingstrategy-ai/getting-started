"""Dynamic Hyperliquid (Hypercore) vault universe construction with caching.

Fetches all qualifying Hypercore vaults from the Trading Strategy API,
filters them using the same logic as scripts/hyperliquid-filter-top-vaults.py,
and caches the result based on filter parameters.

Cache is stored in ~/.cache/indicators/ alongside indicator caches,
so it is cleared by the existing /clear-backtesting-cache skill.
"""

import hashlib
import json
import sys
from pathlib import Path

from tradingstrategy.chain import ChainId

from getting_started.curator import EXCLUDED_PROTOCOLS, EXCLUDED_VAULTS, MUST_INCLUDE
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


def _curator_fingerprint() -> str:
    """Short hash of curator lists so cache invalidates on changes."""
    parts = sorted(EXCLUDED_VAULTS) + sorted(MUST_INCLUDE) + sorted(EXCLUDED_PROTOCOLS.keys())
    digest = hashlib.md5("|".join(parts).encode()).hexdigest()[:8]
    return digest


def _make_cache_key(min_tvl: float, top_n: int | None, min_age: float, sort_period: str, include_closed_vaults: bool) -> str:
    """Derive a cache key from filter parameters."""
    top_part = "topall" if top_n is None else f"top{top_n}"
    closed_part = "-closed" if include_closed_vaults else ""
    return f"tvl{int(min_tvl)}-{top_part}-age{min_age}-sort{sort_period}{closed_part}-cur{_curator_fingerprint()}"


def _cache_path(cache_key: str) -> Path:
    return CACHE_DIR / f"vault-universe-{cache_key}.json"


def _load_cache(cache_key: str) -> list[tuple[ChainId, str]] | None:
    """Load cached vault universe if it exists."""
    path = _cache_path(cache_key)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return [(ChainId(entry["chain_id"]), entry["address"]) for entry in data]


def _save_cache(cache_key: str, vaults: list[tuple[ChainId, str]]) -> None:
    """Save vault universe to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = [{"chain_id": chain_id.value, "address": address} for chain_id, address in vaults]
    with open(_cache_path(cache_key), "w") as f:
        json.dump(data, f, indent=2)


def build_hyperliquid_vault_universe(
    min_tvl: float = 10_000,
    top_n: int | None = None,
    min_age: float = 0.15,
    sort_period: str = "1Y",
    include_closed_vaults: bool = False,
) -> list[tuple[ChainId, str]]:
    """Build a filtered Hypercore vault universe, cached by parameters.

    Fetches all Hypercore vaults from the Trading Strategy API, applies
    quality filters (denomination, risk, flags, TVL, age), and returns
    a list of (ChainId, address) tuples ready for ``limit_to_vaults()``.

    Uses ``skip_cagr_filter=True`` and ``use_peak_tvl=True`` to
    eliminate survivorship bias in backtesting: vaults are included
    if their all-time peak TVL ever crossed ``min_tvl``, even if
    their current TVL has since dropped below the threshold.

    Cache key is derived from the filter parameters, so notebooks
    with identical parameters share a single cache file.

    :param min_tvl:
        Minimum TVL in USD.  Checked against all-time peak TVL
        (``peak_nav``) to avoid excluding once-active vaults.
    :param top_n:
        Maximum number of vaults to include.  **Should not be used
        for backtesting** — truncating to the current top-N by CAGR
        introduces survivorship bias (only today's winners are
        selected).  Default ``None`` returns all qualifying vaults.
    :param min_age:
        Minimum vault age in years.
    :param sort_period:
        CAGR period used for ranking (``"1M"``, ``"3M"``, or ``"1Y"``).
    :param include_closed_vaults:
        Include Hyperliquid vaults that currently do not accept
        deposits.  We currently lack historical data on when
        Hyperliquid vaults opened or closed deposits, so we cannot
        determine their status at any given backtest timestamp.
        Set to ``True`` to include them anyway for a broader
        backtesting universe.
    :return:
        List of ``(ChainId.hypercore, "0x...")`` tuples.
    """
    cache_key = _make_cache_key(min_tvl, top_n, min_age, sort_period, include_closed_vaults)
    cached = _load_cache(cache_key)
    if cached is not None:
        print(f"Loaded {len(cached)} cached Hypercore vaults ({cache_key})", file=sys.stderr)
        return cached

    chain_config = dict(CHAIN_CONFIG)
    if top_n is not None:
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
        use_peak_tvl=True,
        include_closed_vaults=include_closed_vaults,
    )

    result = []
    for chain_id in CHAIN_ORDER:
        for v in selected.get(chain_id, []):
            if not v.excluded and v.excluded_protocol_reason is None:
                result.append((ChainId.hypercore, v.address))

    top_label = f"top {top_n}" if top_n is not None else "all"
    print(f"Selected {len(result)} Hypercore vaults (peak TVL >= ${min_tvl:,.0f}, {top_label})", file=sys.stderr)

    _save_cache(cache_key, result)
    return result
