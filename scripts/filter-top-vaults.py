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

# Vaults without a known protocol slug are skipped
# (we cannot determine which protocol manages the vault)
REQUIRE_KNOWN_PROTOCOL = True

# Default minimum TVL in USD
DEFAULT_MIN_TVL = 100_000
 
# Hypercore minimum TVL in USD
HYPERCORE_MIN_TVL = 75_000

# Minimum vault age in years
DEFAULT_MIN_AGE = 0.3

# Period used for sorting and ranking vaults: "1M", "3M", or "1Y"
SORT_PERIOD = "1Y"

# Vaults that must always be included (by address lowercase)
MUST_INCLUDE = {
    # Ostium on Arbitrum
    "0x20d419a8e12c45f88fda7c5760bb6923cee27f98",
    # Growi HF on Hypercore
    "0x1e37a337ed460039d1b15bd3bc489de789768d5e",
    # Hyperliquidity Provider (HLP) on Hypercore
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
}

# Vaults to exclude (output as commented-out lines)
EXCLUDED_VAULTS = {
    # Elsewhere on Hypercore
    "0x8fc7c0442e582bca195978c5a4fdec2e7c5bb0f7",
    # Sifu on Hypercore
    "0xf967239debef10dbc78e9bbbb2d8a16b72a614eb",
    # Long LINK Short XRP on Hypercore
    "0x73ce82fb75868af2a687e9889fcf058dd1cf8ce9",
    # Wrapped HLP on HyperEVM (we have native HLP)
    "0x06fd9d03b3d0f18e4919919b72d30c582f0a97e5",
    # BTC/ETH CTA | AIM on Hypercore
    "0xbeebbbe817a69d60dd62e0a942032bc5414dae1c",
    # Sentiment Edge on Hypercore
    "0xb7e7d0fdeff5473ed6ef8d3a762d096a040dbb18",
    # Sentiment Edge on Hypercore
    "0x026a2e082a03200a00a97974b7bf7753ce33540f",
    # ski lambo beach on Hypercore
    "0x66e541024ca4c50b8f6c0934b8947c487d211661",
    # BULBUL2DAO on Hypercore
    "0x65aee08c9235025355ac6c5ad020fb167ecef4fe",
    # Cryptoaddcited on Hypercore
    "0x5108cd0a328ed28c277f958761fe1cda60c21aa8",
    # hidden marko fund on Hypercore
    "0xc497f1f8840dd65affbab1a610b6e558844743d4",
    # Crypto_Lab28 on Hypercore
    "0xb11fe7f2e97bd02b2da909b32f4a5e7fcb0df099",
    # Jade Lotus Capital on Hypercore
    "0xbc5bf88fd012612ba92c5bd96e183955801b7fdc",
    # MOAS on Hypercore
    "0x29b98aaf8eeb316385fe2ed1af564bdc4b03ffd6",
    # Long HYPE & BTC | Short Garbage on Hypercore
    "0xac26cf5f3c46b5e102048c65b977d2551b72a9c7",
    # HyperTwin - Growi HF 2x on Hypercore
    "0x15be61aef0ea4e4dc93c79b668f26b3f1be75a66",
}


@dataclass
class VaultInfo:
    name: str
    address: str
    chain_id: int
    chain_name: str
    denomination: str
    age_years: float
    cagr_periods: dict[str, float | None]
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


TRACKED_PERIODS = ("1M", "3M", "1Y")


def get_cagr_periods(vault: dict) -> dict[str, float | None]:
    """Extract CAGR for all tracked periods from period_results."""
    result: dict[str, float | None] = {p: None for p in TRACKED_PERIODS}
    for period in vault.get("period_results") or []:
        key = period.get("period")
        if key in result:
            result[key] = period.get("cagr_gross")
    return result


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
        cagr_periods=get_cagr_periods(vault),
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

    # Name filter: Compounder vaults are Yearn substrategies and not directly investable
    if "Compounder" in v.name:
        return False, f"name_compounder={v.name}"

    # Protocol filter
    if REQUIRE_KNOWN_PROTOCOL and (not v.protocol_slug or "<" in v.protocol_slug or "not-yet-identified" in v.protocol_slug):
        return False, f"unknown_protocol={v.protocol_slug!r}"

    # Hyperliquid chains (Hypercore + HyperEVM): both 3m and 1y CAGR must be positive
    if v.chain_id in (9999, 999):
        cagr_3m = v.cagr_periods.get("3M")
        cagr_1y = v.cagr_periods.get("1Y")
        if cagr_3m is not None and cagr_3m <= 0:
            return False, f"negative_3m_cagr={cagr_3m:.2%}"
        if cagr_1y is not None and cagr_1y <= 0:
            return False, f"negative_1y_cagr={cagr_1y:.2%}"

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
    """Sort key: SORT_PERIOD CAGR descending (fallback to all-time CAGR)."""
    cagr = v.cagr_periods.get(SORT_PERIOD)
    if cagr is None:
        cagr = v.cagr_all
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

        # Hypercore deposit-closed vaults are excluded entirely
        # (we cannot allocate to them from the strategy)
        if v.chain_id == 9999 and v.deposit_closed_reason is not None:
            stats["filtered_out"] += 1
            filter_reasons["deposit_closed"] = filter_reasons.get("deposit_closed", 0) + 1
            continue

        passes, reason = filter_vault(v, min_tvl, min_age)
        if passes:
            if v.excluded or v.excluded_protocol_reason is not None:
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
        non_excluded = [v for v in selected if not v.excluded and v.excluded_protocol_reason is None]
        excluded = [v for v in selected if v.excluded or v.excluded_protocol_reason is not None]
        non_excluded.sort(key=sort_key)
        result[chain_id] = non_excluded + excluded

        cfg = CHAIN_CONFIG[chain_id]
        active = [v for v in non_excluded if v.deposit_closed_reason is None]
        deposit_closed = [v for v in non_excluded if v.deposit_closed_reason is not None]
        parts = [f"{len(active)} active"]
        if deposit_closed:
            parts.append(f"{len(deposit_closed)} deposit-closed")
        if excluded:
            parts.append(f"{len(excluded)} excluded")
        print(f"  {cfg['name']}: {' + '.join(parts)} (from {len(chain_vaults)} candidates)", file=sys.stderr)

    return result


def format_output(selected: dict[int, list[VaultInfo]]) -> str:
    """Format selected vaults as Python code for the notebook."""
    lines = []

    for chain_id in CHAIN_ORDER:
        vaults = selected.get(chain_id, [])
        cfg = CHAIN_CONFIG[chain_id]
        chain_enum = cfg["enum"]
        chain_name = cfg["name"]
        # Count only truly active vaults (exclude deposit-closed, excluded, excluded-protocol)
        non_excluded = [v for v in vaults if not v.excluded and v.excluded_protocol_reason is None and v.deposit_closed_reason is None]
        min_tvl_str = format_tvl(HYPERCORE_MIN_TVL) if chain_id == 9999 else format_tvl(DEFAULT_MIN_TVL)
        min_age = cfg.get("min_age", DEFAULT_MIN_AGE)

        lines.append(f"")
        lines.append(f"            #")
        lines.append(f"            # {chain_name}")
        lines.append(f"            #")
        sort_label = SORT_PERIOD.lower()
        lines.append(f"            # {len(non_excluded)} vaults, sorted by {sort_label} CAGR")
        lines.append(
            f"            # Filter: min TVL {min_tvl_str}, min age {min_age}y, "
            f"denomination in (USDC, USDC.e, crvUSD, USDS, USDT/USD₮0), "
            f"exclude Blacklisted/Dangerous"
        )
        lines.append(f"            #")

        # Sort so that active vaults come first, then deposit-closed, then excluded/commented-out at the end
        active = [v for v in vaults if not v.excluded and v.excluded_protocol_reason is None and v.deposit_closed_reason is None]
        deposit_closed = [v for v in vaults if v.deposit_closed_reason is not None and not v.excluded and v.excluded_protocol_reason is None]
        commented = [v for v in vaults if v.excluded or v.excluded_protocol_reason is not None]
        ordered_vaults = active + deposit_closed + commented

        for v in ordered_vaults:
            # Hypercore deposit-closed vaults are excluded entirely
            # (we cannot allocate to them from the strategy)
            if v.chain_id == 9999 and v.deposit_closed_reason is not None:
                continue

            cagr_parts = ", ".join(
                f"CAGR {p.lower()}={format_pct(v.cagr_periods.get(p))}"
                for p in TRACKED_PERIODS
            )
            cagr_all_str = format_pct(v.cagr_all)
            comment = (
                f"[{v.denomination}] {v.name} "
                f"(protocol={v.protocol_slug}, "
                f"age={v.age_years:.1f}y, "
                f"{cagr_parts}, "
                f"CAGR all={cagr_all_str}, "
                f"TVL={format_tvl(v.tvl)})"
            )
            commented_out = v.excluded or v.excluded_protocol_reason is not None
            prefix = "            # " if commented_out else "            "
            lines.append(f"")
            lines.append(f"{prefix}# {comment}")
            if v.excluded_protocol_reason is not None:
                lines.append(f"{prefix}# Excluded protocol ({v.protocol_slug}): {v.excluded_protocol_reason}")
            if v.deposit_closed_reason is not None:
                lines.append(f"{prefix}# Deposits disabled: {v.deposit_closed_reason}")
            if v.excluded:
                lines.append(f"{prefix}# Excluded vault")
            lines.append(f'{prefix}({chain_enum}, "{v.address}"),')

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
        print(format_output(selected))


if __name__ == "__main__":
    main()
