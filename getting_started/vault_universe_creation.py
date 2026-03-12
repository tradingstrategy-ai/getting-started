"""Common functions for filtering and selecting top DeFi vaults.

Shared by scripts/filter-top-vaults.py and scripts/larger-filter-top-vaults.py.
"""

import json
import sys
import urllib.request
from dataclasses import dataclass

from getting_started.curator import EXCLUDED_PROTOCOLS, EXCLUDED_VAULTS, MUST_INCLUDE


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
    peak_tvl: float
    risk: str | None
    flags: list[str]
    protocol_slug: str
    deposit_closed_reason: str | None
    must_include: bool
    excluded: bool
    excluded_protocol_reason: str | None


def fetch_vaults(data_url: str) -> list[dict]:
    """Fetch vault data from the API."""
    print("Fetching vault data...", file=sys.stderr)
    req = urllib.request.Request(data_url, headers={"User-Agent": "filter-top-vaults/1.0"})
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


def get_cagr_periods(vault: dict, tracked_periods: tuple[str, ...]) -> dict[str, float | None]:
    """Extract CAGR for all tracked periods from period_results."""
    result: dict[str, float | None] = {p: None for p in tracked_periods}
    for period in vault.get("period_results") or []:
        key = period.get("period")
        if key in result:
            result[key] = period.get("cagr_gross")
    return result


def get_tvl(vault: dict) -> float:
    """Get current TVL (current_nav)."""
    return vault.get("current_nav") or 0.0


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


def parse_vault(
    vault: dict,
    chain_config: dict,
    tracked_periods: tuple[str, ...],
) -> VaultInfo | None:
    """Parse a raw vault dict into VaultInfo, or None if not in target chains."""
    chain_id = vault.get("chain_id")
    if chain_id not in chain_config:
        return None

    address = vault.get("address", "").lower()

    return VaultInfo(
        name=vault.get("name", "Unknown"),
        address=address,
        chain_id=chain_id,
        chain_name=chain_config[chain_id]["name"],
        denomination=vault.get("denomination", ""),
        age_years=vault.get("years", 0.0) or 0.0,
        cagr_periods=get_cagr_periods(vault, tracked_periods),
        cagr_all=vault.get("cagr", 0.0) or 0.0,
        tvl=get_tvl(vault),
        peak_tvl=vault.get("peak_nav") or 0.0,
        risk=vault.get("risk"),
        flags=vault.get("flags") or [],
        protocol_slug=vault.get("protocol_slug") or "",
        deposit_closed_reason=vault.get("deposit_closed_reason"),
        must_include=address in MUST_INCLUDE,
        excluded=address in EXCLUDED_VAULTS,
        excluded_protocol_reason=EXCLUDED_PROTOCOLS.get(vault.get("protocol_slug") or ""),
    )


def filter_vault(
    v: VaultInfo,
    min_tvl: float,
    min_age: float,
    chain_config: dict,
    *,
    allowed_denominations: set[str],
    excluded_risks: set[str],
    excluded_flags: set[str],
    require_known_protocol: bool,
    hypercore_min_tvl: float,
    skip_cagr_filter: bool = False,
    use_peak_tvl: bool = False,
) -> tuple[bool, str]:
    """Check if vault passes filters. Returns (passes, reason)."""
    # Must-include vaults always pass
    if v.must_include:
        return True, "must-include"

    # Excluded vaults are kept but marked
    if v.excluded:
        return True, "excluded"

    # Risk filter
    if v.risk in excluded_risks:
        return False, f"risk={v.risk}"

    # Flag filter
    bad_flags = set(v.flags) & excluded_flags
    if bad_flags:
        return False, f"flags={bad_flags}"

    # Name filter: Compounder vaults are Yearn substrategies and not directly investable
    if "Compounder" in v.name:
        return False, f"name_compounder={v.name}"

    # Protocol filter
    if require_known_protocol and (not v.protocol_slug or "<" in v.protocol_slug or "not-yet-identified" in v.protocol_slug):
        return False, f"unknown_protocol={v.protocol_slug!r}"

    # Hyperliquid chains (Hypercore + HyperEVM): both 3m and 1y CAGR must be positive
    if not skip_cagr_filter and v.chain_id in (9999, 999):
        cagr_3m = v.cagr_periods.get("3M")
        cagr_1y = v.cagr_periods.get("1Y")
        if cagr_3m is not None and cagr_3m <= 0:
            return False, f"negative_3m_cagr={cagr_3m:.2%}"
        if cagr_1y is not None and cagr_1y <= 0:
            return False, f"negative_1y_cagr={cagr_1y:.2%}"

    # Denomination filter
    normalised = normalise_denomination(v.denomination)
    if normalised not in allowed_denominations:
        return False, f"denomination={v.denomination} ({normalised})"

    # TVL filter (Hypercore has higher threshold).
    # When use_peak_tvl=True, check all-time peak TVL instead of current TVL
    # to include vaults that have ever crossed the threshold — this eliminates
    # survivorship bias in backtesting.
    effective_min_tvl = hypercore_min_tvl if v.chain_id == 9999 else min_tvl
    check_tvl = v.peak_tvl if use_peak_tvl else v.tvl
    if check_tvl < effective_min_tvl:
        return False, f"TVL={format_tvl(check_tvl)} < {format_tvl(effective_min_tvl)}"

    # Age filter (per-chain override supported via min_age in CHAIN_CONFIG)
    effective_min_age = chain_config.get(v.chain_id, {}).get("min_age", min_age)
    if v.age_years < effective_min_age:
        return False, f"age={v.age_years:.1f}y < {effective_min_age}y"

    return True, "ok"


def select_top_vaults(
    vaults: list[VaultInfo],
    min_tvl: float,
    min_age: float,
    chain_config: dict,
    chain_order: list[int],
    sort_period: str,
    *,
    allowed_denominations: set[str],
    excluded_risks: set[str],
    excluded_flags: set[str],
    require_known_protocol: bool,
    hypercore_min_tvl: float,
    top_n_override: int | None = None,
    skip_cagr_filter: bool = False,
    use_peak_tvl: bool = False,
    include_closed_vaults: bool = False,
) -> dict[int, list[VaultInfo]]:
    """Select top vaults per chain after filtering."""

    def sort_key(v: VaultInfo) -> float:
        """Sort key: sort_period CAGR descending (fallback to all-time CAGR)."""
        cagr = v.cagr_periods.get(sort_period)
        if cagr is None:
            cagr = v.cagr_all
        return -cagr

    filter_kwargs = dict(
        allowed_denominations=allowed_denominations,
        excluded_risks=excluded_risks,
        excluded_flags=excluded_flags,
        require_known_protocol=require_known_protocol,
        hypercore_min_tvl=hypercore_min_tvl,
        skip_cagr_filter=skip_cagr_filter,
        use_peak_tvl=use_peak_tvl,
    )

    # Group by chain
    by_chain: dict[int, list[VaultInfo]] = {cid: [] for cid in chain_config}
    excluded_by_chain: dict[int, list[VaultInfo]] = {cid: [] for cid in chain_config}

    stats = {"total": 0, "filtered_out": 0}
    filter_reasons: dict[str, int] = {}

    for v in vaults:
        stats["total"] += 1

        # Hypercore deposit-closed vaults are excluded by default
        # (we cannot allocate to them from the strategy).
        # When include_closed_vaults=True, keep them in the universe
        # for backtesting — we currently lack historical data on when
        # Hyperliquid vaults opened or closed deposits, so we cannot
        # easily determine this during the backtest timeline.
        if not include_closed_vaults and not v.must_include and v.chain_id == 9999 and v.deposit_closed_reason is not None:
            stats["filtered_out"] += 1
            filter_reasons["deposit_closed"] = filter_reasons.get("deposit_closed", 0) + 1
            continue

        passes, reason = filter_vault(v, min_tvl, min_age, chain_config, **filter_kwargs)
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
    for chain_id in chain_order:
        chain_vaults = by_chain[chain_id]
        chain_vaults.sort(key=sort_key)

        top_n = top_n_override if top_n_override is not None else chain_config[chain_id].get("top_n")

        if top_n is None:
            # No truncation — return all qualifying vaults
            selected = list(chain_vaults)
        else:
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

        cfg = chain_config[chain_id]
        active = [v for v in non_excluded if v.deposit_closed_reason is None]
        deposit_closed = [v for v in non_excluded if v.deposit_closed_reason is not None]
        parts = [f"{len(active)} active"]
        if deposit_closed:
            parts.append(f"{len(deposit_closed)} deposit-closed")
        if excluded:
            parts.append(f"{len(excluded)} excluded")
        print(f"  {cfg['name']}: {' + '.join(parts)} (from {len(chain_vaults)} candidates)", file=sys.stderr)

    return result


def format_output(
    selected: dict[int, list[VaultInfo]],
    chain_config: dict,
    chain_order: list[int],
    *,
    hypercore_min_tvl: float,
    default_min_tvl: float,
    default_min_age: float,
    sort_period: str,
    tracked_periods: tuple[str, ...],
) -> str:
    """Format selected vaults as Python code for the notebook."""
    lines = []

    for chain_id in chain_order:
        vaults = selected.get(chain_id, [])
        cfg = chain_config[chain_id]
        chain_enum = cfg["enum"]
        chain_name = cfg["name"]
        # Count only truly active vaults (exclude deposit-closed, excluded, excluded-protocol)
        non_excluded = [v for v in vaults if not v.excluded and v.excluded_protocol_reason is None and v.deposit_closed_reason is None]
        min_tvl_str = format_tvl(hypercore_min_tvl) if chain_id == 9999 else format_tvl(default_min_tvl)
        min_age = cfg.get("min_age", default_min_age)

        lines.append(f"")
        lines.append(f"            #")
        lines.append(f"            # {chain_name}")
        lines.append(f"            #")
        sort_label = sort_period.lower()
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
                for p in tracked_periods
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
            lines.append(f'{prefix}# https://tradingstrategy.ai/trading-view/vaults/address/{v.address}')

    return "\n".join(lines)
