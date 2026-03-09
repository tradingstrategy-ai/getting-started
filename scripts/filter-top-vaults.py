"""Filter top DeFi vaults by chain from the Trading Strategy API.

Fetches vault data from top-defi-vaults.tradingstrategy.ai and filters
by chain, denomination, TVL, age, risk level, and CAGR. Outputs a
formatted vault list ready to paste into a notebook's cross-chain
configuration section.

Usage:
    poetry run python scripts/filter-top-vaults.py
    poetry run python scripts/filter-top-vaults.py --top 15
    poetry run python scripts/filter-top-vaults.py --min-tvl 200000
"""

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass

DATA_URL = "https://top-defi-vaults.tradingstrategy.ai/top_vaults_by_chain.json"

# Chains to include with their ChainId enum name and top-N count
CHAIN_CONFIG = {
    42161: {"name": "Arbitrum", "enum": "ChainId.arbitrum", "top_n": 10},
    8453: {"name": "Base", "enum": "ChainId.base", "top_n": 10},
    1: {"name": "Ethereum", "enum": "ChainId.ethereum", "top_n": 10},
    43114: {"name": "Avalanche", "enum": "ChainId.avalanche", "top_n": 10},
    9999: {"name": "Hypercore", "enum": "HYPERCORE_CHAIN_ID", "top_n": 30},
    999: {"name": "HyperEVM", "enum": "ChainId.hyperliquid", "top_n": 10},
    143: {"name": "Monad", "enum": "ChainId.monad", "top_n": 10, "min_age": 0.1},
}

# Chain display order
CHAIN_ORDER = [1, 8453, 42161, 43114, 9999, 999, 143]

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

# Protocols to exclude (output as commented-out lines with reason)
EXCLUDED_PROTOCOLS = {
    "accountable": "Assets are illiquid for strategies",
}

# Default minimum TVL in USD
DEFAULT_MIN_TVL = 100_000

# Hypercore minimum TVL in USD
HYPERCORE_MIN_TVL = 500_000

# Minimum vault age in years
DEFAULT_MIN_AGE = 0.3

# Vaults that must always be included (by address lowercase)
MUST_INCLUDE = {
    # Ostium on Arbitrum
    "0x20d419a8e12c45f88fda7c5760bb6923cee27f98",
    # Growi HF on Hypercore
    "0x1e37a337ed460039d1b15bd3bc489de789768d5e",
}

# Vaults to exclude (output as commented-out lines)
EXCLUDED_VAULTS = {
    # Elsewhere on Hypercore
    "0x8fc7c0442e582bca195978c5a4fdec2e7c5bb0f7",
    # Sifu on Hypercore
    "0xf967239debef10dbc78e9bbbb2d8a16b72a614eb",
    # Long LINK Short XRP on Hypercore
    "0x73ce82fb75868af2a687e9889fcf058dd1cf8ce9",
}


@dataclass
class VaultInfo:
    name: str
    address: str
    chain_id: int
    chain_name: str
    denomination: str
    age_years: float
    cagr_1y: float | None
    cagr_all: float
    tvl: float
    risk: str | None
    flags: list[str]
    protocol_slug: str
    deposit_closed_reason: str | None
    must_include: bool
    excluded: bool
    excluded_protocol_reason: str | None


def fetch_vaults() -> list[dict]:
    """Fetch vault data from the API."""
    print("Fetching vault data...", file=sys.stderr)
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "filter-top-vaults/1.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    print(f"Fetched {len(data['vaults'])} vaults (generated at {data['generated_at']})", file=sys.stderr)
    return data["vaults"]


def normalise_denomination(denom: str) -> str:
    """Normalise denomination token name for matching."""
    if denom is None:
        return ""
    # Handle special unicode characters
    normalised = denom.upper().strip()
    # USD₮0 variants
    normalised = normalised.replace("₮", "T")
    return normalised


def get_cagr_1y(vault: dict) -> float | None:
    """Extract 1-year CAGR from period_results."""
    for period in vault.get("period_results") or []:
        if period.get("period") == "1Y":
            return period.get("cagr_gross")
    return None


def get_tvl(vault: dict) -> float:
    """Get current TVL (current_nav)."""
    return vault.get("current_nav") or 0.0


def is_denomination_allowed(vault: dict) -> bool:
    """Check if vault denomination is in the allowed set."""
    denom = vault.get("denomination", "")
    normalised = normalise_denomination(denom)
    return normalised in ALLOWED_DENOMINATIONS


def format_tvl(tvl: float) -> str:
    """Format TVL as human-readable string like $500k or $1.2M."""
    if tvl >= 1_000_000:
        value = tvl / 1_000_000
        if value >= 100:
            return f"${value:.0f}M"
        elif value >= 10:
            return f"${value:.1f}M"
        else:
            return f"${value:.1f}M"
    else:
        value = tvl / 1_000
        if value >= 100:
            return f"${value:.0f}k"
        elif value >= 10:
            return f"${value:.0f}k"
        else:
            return f"${value:.1f}k"


def format_pct(value: float | None) -> str:
    """Format a decimal ratio as percentage string."""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def parse_vault(vault: dict) -> VaultInfo | None:
    """Parse a raw vault dict into VaultInfo, or None if not in target chains."""
    chain_id = vault.get("chain_id")
    if chain_id not in CHAIN_CONFIG:
        return None

    address = vault.get("address", "").lower()

    return VaultInfo(
        name=vault.get("name", "Unknown"),
        address=address,
        chain_id=chain_id,
        chain_name=CHAIN_CONFIG[chain_id]["name"],
        denomination=vault.get("denomination", ""),
        age_years=vault.get("years", 0.0) or 0.0,
        cagr_1y=get_cagr_1y(vault),
        cagr_all=vault.get("cagr", 0.0) or 0.0,
        tvl=get_tvl(vault),
        risk=vault.get("risk"),
        flags=vault.get("flags") or [],
        protocol_slug=vault.get("protocol_slug") or "",
        deposit_closed_reason=vault.get("deposit_closed_reason"),
        must_include=address in MUST_INCLUDE,
        excluded=address in EXCLUDED_VAULTS,
        excluded_protocol_reason=EXCLUDED_PROTOCOLS.get(vault.get("protocol_slug") or ""),
    )


def filter_vault(v: VaultInfo, min_tvl: float, min_age: float) -> tuple[bool, str]:
    """Check if vault passes filters. Returns (passes, reason)."""
    # Must-include vaults always pass
    if v.must_include:
        return True, "must-include"

    # Excluded vaults are kept but marked
    if v.excluded:
        return True, "excluded"

    # Risk filter
    if v.risk in EXCLUDED_RISKS:
        return False, f"risk={v.risk}"

    # Flag filter
    bad_flags = set(v.flags) & EXCLUDED_FLAGS
    if bad_flags:
        return False, f"flags={bad_flags}"

    # Denomination filter
    normalised = normalise_denomination(v.denomination)
    if normalised not in ALLOWED_DENOMINATIONS:
        return False, f"denomination={v.denomination} ({normalised})"

    # TVL filter (Hypercore has higher threshold)
    effective_min_tvl = HYPERCORE_MIN_TVL if v.chain_id == 9999 else min_tvl
    if v.tvl < effective_min_tvl:
        return False, f"TVL={format_tvl(v.tvl)} < {format_tvl(effective_min_tvl)}"

    # Age filter (per-chain override supported via min_age in CHAIN_CONFIG)
    effective_min_age = CHAIN_CONFIG.get(v.chain_id, {}).get("min_age", min_age)
    if v.age_years < effective_min_age:
        return False, f"age={v.age_years:.1f}y < {effective_min_age}y"

    return True, "ok"


def sort_key(v: VaultInfo) -> float:
    """Sort key: 1Y CAGR descending (fallback to all-time CAGR)."""
    cagr = v.cagr_1y if v.cagr_1y is not None else v.cagr_all
    return -cagr


def select_top_vaults(
    vaults: list[VaultInfo],
    min_tvl: float,
    min_age: float,
    top_n_override: int | None = None,
) -> dict[int, list[VaultInfo]]:
    """Select top vaults per chain after filtering."""
    # Group by chain
    by_chain: dict[int, list[VaultInfo]] = {cid: [] for cid in CHAIN_CONFIG}
    excluded_by_chain: dict[int, list[VaultInfo]] = {cid: [] for cid in CHAIN_CONFIG}

    stats = {"total": 0, "filtered_out": 0}
    filter_reasons: dict[str, int] = {}

    for v in vaults:
        stats["total"] += 1
        passes, reason = filter_vault(v, min_tvl, min_age)
        if passes:
            if v.excluded:
                excluded_by_chain[v.chain_id].append(v)
            else:
                by_chain[v.chain_id].append(v)
        else:
            stats["filtered_out"] += 1
            category = reason.split("=")[0]
            filter_reasons[category] = filter_reasons.get(category, 0) + 1

    print(f"\nFilter stats: {stats['total']} vaults on target chains, {stats['filtered_out']} filtered out", file=sys.stderr)
    for reason, count in sorted(filter_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}", file=sys.stderr)

    # Sort and select top N per chain
    result: dict[int, list[VaultInfo]] = {}
    for chain_id in CHAIN_ORDER:
        chain_vaults = by_chain[chain_id]
        chain_vaults.sort(key=sort_key)

        top_n = top_n_override or CHAIN_CONFIG[chain_id]["top_n"]

        # Sort all candidates together, then ensure must-includes are in the top N
        must_include = [v for v in chain_vaults if v.must_include]
        regular = [v for v in chain_vaults if not v.must_include]

        # Reserve slots for must-include vaults not in top N
        regular_top = regular[:top_n]
        regular_top_addrs = {v.address for v in regular_top}

        # Must-include vaults that aren't already in the top N
        extra_must = [v for v in must_include if v.address not in regular_top_addrs]

        # Trim regular to make room for extra must-includes
        slots_for_regular = max(0, top_n - len(extra_must))
        selected = regular[:slots_for_regular] + extra_must

        # Add excluded vaults at the end
        for ev in excluded_by_chain[chain_id]:
            selected.append(ev)

        # Re-sort (excluded vaults go to the end)
        non_excluded = [v for v in selected if not v.excluded]
        excluded = [v for v in selected if v.excluded]
        non_excluded.sort(key=sort_key)
        result[chain_id] = non_excluded + excluded

        cfg = CHAIN_CONFIG[chain_id]
        print(f"  {cfg['name']}: {len(non_excluded)} selected + {len(excluded)} excluded (from {len(chain_vaults)} candidates)", file=sys.stderr)

    return result


def format_output(selected: dict[int, list[VaultInfo]]) -> str:
    """Format selected vaults as Python code for the notebook."""
    lines = []

    for chain_id in CHAIN_ORDER:
        vaults = selected.get(chain_id, [])
        cfg = CHAIN_CONFIG[chain_id]
        chain_enum = cfg["enum"]
        chain_name = cfg["name"]
        # For Hypercore, exclude deposit-closed vaults from the count
        # (we cannot allocate to them from the strategy)
        if chain_id == 9999:
            non_excluded = [v for v in vaults if not v.excluded and v.deposit_closed_reason is None]
        else:
            non_excluded = [v for v in vaults if not v.excluded]
        top_n = cfg["top_n"]

        min_tvl_str = format_tvl(HYPERCORE_MIN_TVL) if chain_id == 9999 else format_tvl(DEFAULT_MIN_TVL)
        min_age = cfg.get("min_age", DEFAULT_MIN_AGE)

        lines.append(f"")
        lines.append(f"            # {chain_name} ({len(non_excluded)} vaults, sorted by 1y CAGR)")
        lines.append(
            f"            # Filter: min TVL {min_tvl_str}, min age {min_age}y, "
            f"denomination in (USDC, USDC.e, crvUSD, USDS, USDT/USD₮0), "
            f"exclude Blacklisted/Dangerous"
        )

        for v in vaults:
            # Hypercore deposit-closed vaults are excluded entirely
            # (we cannot allocate to them from the strategy)
            if v.chain_id == 9999 and v.deposit_closed_reason is not None:
                continue

            cagr_1y_str = format_pct(v.cagr_1y)
            cagr_all_str = format_pct(v.cagr_all)
            comment = (
                f"[{v.denomination}] {v.name} "
                f"(age={v.age_years:.1f}y, "
                f"CAGR 1y={cagr_1y_str}, "
                f"CAGR all={cagr_all_str}, "
                f"TVL={format_tvl(v.tvl)})"
            )
            commented_out = v.excluded or v.deposit_closed_reason is not None or v.excluded_protocol_reason is not None
            if v.excluded_protocol_reason is not None:
                lines.append(f"            # Excluded protocol ({v.protocol_slug}): {v.excluded_protocol_reason}")
            if v.deposit_closed_reason is not None:
                lines.append(f"            # Deposits disabled: {v.deposit_closed_reason}")
            prefix = "            # " if commented_out else "            "
            line = f'{prefix}({chain_enum}, "{v.address}"),  # {comment}'
            lines.append(line)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Filter top DeFi vaults by chain")
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

    raw_vaults = fetch_vaults()

    # Parse only target chain vaults
    parsed = []
    for rv in raw_vaults:
        v = parse_vault(rv)
        if v is not None:
            parsed.append(v)

    print(f"Parsed {len(parsed)} vaults on target chains", file=sys.stderr)

    selected = select_top_vaults(parsed, args.min_tvl, args.min_age, args.top)

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
                    "cagr_1y": round(v.cagr_1y, 4) if v.cagr_1y is not None else None,
                    "cagr_all": round(v.cagr_all, 4),
                    "tvl": round(v.tvl, 2),
                    "deposit_closed_reason": v.deposit_closed_reason,
                    "must_include": v.must_include,
                    "excluded": v.excluded,
                })
        print(json.dumps(output, indent=2))
    else:
        print(format_output(selected))


if __name__ == "__main__":
    main()
