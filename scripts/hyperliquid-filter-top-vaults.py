"""Filter top Hypercore (Hyperliquid native) vaults from the Trading Strategy API.

Based on larger-filter-top-vaults.py - Hypercore only, no CAGR profitability
filter to avoid survivorship bias.

Usage::

    python scripts/hyperliquid-filter-top-vaults.py
"""

import argparse
import json
import sys

from getting_started.vault_universe_creation import (
    fetch_vaults,
    format_output,
    parse_vault,
    select_top_vaults,
)

DATA_URL = "https://top-defi-vaults.tradingstrategy.ai/top_vaults_by_chain.json"

# Hypercore only
CHAIN_CONFIG = {
    9999: {"name": "Hypercore", "enum": "HYPERCORE_CHAIN_ID", "top_n": 120},
}

# Chain display order
CHAIN_ORDER = [9999]

# Allowed denomination tokens (normalised to uppercase for matching)
ALLOWED_DENOMINATIONS = {
    "USDC", "USDC.E",
    "USDT", "USD₮0", "USDT0", "USDT.E",
    "CRVUSD",
    "USDS",
}

# Risk levels to exclude
EXCLUDED_RISKS = {"Blacklisted", "Dangerous"}

# Flags to exclude (vault-level flags indicating problematic vaults)
EXCLUDED_FLAGS = {"malicious", "broken"}

# Vaults without a known protocol slug are skipped
# (we cannot determine which protocol manages the vault)
REQUIRE_KNOWN_PROTOCOL = True

# Default minimum TVL in USD
DEFAULT_MIN_TVL = 50_000

# Hypercore minimum TVL in USD
HYPERCORE_MIN_TVL = 50_000

# Minimum vault age in years
DEFAULT_MIN_AGE = 0.15

# Period used for sorting and ranking vaults: "1M", "3M", or "1Y"
SORT_PERIOD = "1Y"

TRACKED_PERIODS = ("1M", "3M", "1Y")


def main():
    parser = argparse.ArgumentParser(description="Filter top Hypercore vaults")
    parser.add_argument(
        "--top", type=int, default=None,
        help="Override top-N count for all chains (default: per-chain config)",
    )
    parser.add_argument(
        "--min-tvl", type=float, default=DEFAULT_MIN_TVL,
        help=f"Minimum TVL in USD (default: {DEFAULT_MIN_TVL})",
    )
    parser.add_argument(
        "--min-age", type=float, default=DEFAULT_MIN_AGE,
        help=f"Minimum vault age in years (default: {DEFAULT_MIN_AGE})",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of Python code",
    )
    args = parser.parse_args()

    raw_vaults = fetch_vaults(DATA_URL)

    # Parse only target chain vaults
    parsed = []
    for rv in raw_vaults:
        v = parse_vault(rv, CHAIN_CONFIG, TRACKED_PERIODS)
        if v is not None:
            parsed.append(v)

    print(f"Parsed {len(parsed)} vaults on target chains", file=sys.stderr)

    selected = select_top_vaults(
        parsed, args.min_tvl, args.min_age, CHAIN_CONFIG, CHAIN_ORDER, SORT_PERIOD,
        allowed_denominations=ALLOWED_DENOMINATIONS,
        excluded_risks=EXCLUDED_RISKS,
        excluded_flags=EXCLUDED_FLAGS,
        require_known_protocol=REQUIRE_KNOWN_PROTOCOL,
        hypercore_min_tvl=HYPERCORE_MIN_TVL,
        top_n_override=args.top,
        skip_cagr_filter=True,
    )

    if args.json:
        output = []
        for chain_id in CHAIN_ORDER:
            for v in selected.get(chain_id, []):
                output.append({
                    "chain_id": v.chain_id,
                    "chain": v.chain_name,
                    "address": v.address,
                    "name": v.name,
                    "denomination": v.denomination,
                    "age_years": round(v.age_years, 2),
                    "cagr_periods": {
                        p: round(c, 4) if c is not None else None
                        for p, c in v.cagr_periods.items()
                    },
                    "cagr_all": round(v.cagr_all, 4),
                    "tvl": round(v.tvl, 2),
                    "deposit_closed_reason": v.deposit_closed_reason,
                    "must_include": v.must_include,
                    "excluded": v.excluded,
                })
        print(json.dumps(output, indent=2))
    else:
        print(format_output(
            selected, CHAIN_CONFIG, CHAIN_ORDER,
            hypercore_min_tvl=HYPERCORE_MIN_TVL,
            default_min_tvl=DEFAULT_MIN_TVL,
            default_min_age=DEFAULT_MIN_AGE,
            sort_period=SORT_PERIOD,
            tracked_periods=TRACKED_PERIODS,
        ))


if __name__ == "__main__":
    main()
