"""Filter top DeFi vaults by chain from the Trading Strategy API.

Based on filter-top-vaults.py - capture more vaults for larger backteest.
Usage::

    python scripts/larger-filter-top-vaults.py
    python scripts/larger-filter-top-vaults.py --morpho-vault-flag-ignore red-and-yellow
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from getting_started.vault_universe_creation import (
    fetch_vaults,
    filter_vault,
    format_output,
    format_pct,
    parse_vault,
    select_top_vaults,
)
from tradingstrategy.alternative_data.vault import DEFAULT_VAULT_DOWNLOAD_ROOT
from tradingstrategy.alternative_data.vault import read_vault_price_history_parquet

DATA_URL = "https://top-defi-vaults.tradingstrategy.ai/top_vaults_by_chain.json"

# Chains to include with their ChainId enum name and top-N count
CHAIN_CONFIG = {
    42161: {"name": "Arbitrum", "enum": "ChainId.arbitrum", "top_n": 20},
    8453: {"name": "Base", "enum": "ChainId.base", "top_n": 20},
    1: {"name": "Ethereum", "enum": "ChainId.ethereum", "top_n": 20},
    43114: {"name": "Avalanche", "enum": "ChainId.avalanche", "top_n": 20},
    9999: {"name": "Hypercore", "enum": "HYPERCORE_CHAIN_ID", "top_n": 60},
    999: {"name": "HyperEVM", "enum": "ChainId.hyperliquid", "top_n": 20},
    143: {"name": "Monad", "enum": "ChainId.monad", "top_n": 20, "min_age": 0.1},
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

# Risk levels to exclude for the legacy current-snapshot selector.
EXCLUDED_RISKS = {"Blacklisted", "Dangerous"}

# Risk levels to exclude for the rolling historical selector.
ROLLING_EXCLUDED_RISKS = {"Severe", "Blacklisted", "Dangerous"}

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
DEFAULT_MIN_AGE = 0.3

# Period used for sorting and ranking vaults: "1M", "3M", or "1Y"
SORT_PERIOD = "1Y"

TRACKED_PERIODS = ("1M", "3M", "1Y")
MORPHO_VAULT_FLAG_FILTER_CHOICES = ("none", "red-only", "red-and-yellow")
DEFAULT_ROLLING_PRICE_HISTORY = DEFAULT_VAULT_DOWNLOAD_ROOT / "vault-price-history.parquet"
DEFAULT_ROLLING_TOP_PER_CHAIN = 25
DEFAULT_ROLLING_WINDOW_DAYS = 90
DEFAULT_ROLLING_LIMIT = None
DEFAULT_ALWAYS_INCLUDE_TERMS = ("ostium", "gains", "plutus", "ember", "d2")


def parse_chain_ids(raw: str | None) -> tuple[list[int], dict[int, dict]]:
    """Parse a comma-separated chain id list and return matching config."""
    if not raw:
        chain_ids = list(CHAIN_ORDER)
    else:
        chain_ids = [int(part.strip()) for part in raw.split(",") if part.strip()]

    unknown = [chain_id for chain_id in chain_ids if chain_id not in CHAIN_CONFIG]
    if unknown:
        raise ValueError(f"Unsupported chain ids: {unknown}")

    return chain_ids, {chain_id: CHAIN_CONFIG[chain_id] for chain_id in chain_ids}


def has_any_morpho_flags(raw_vault: dict) -> bool:
    """Check whether a Morpho vault has any Morpho flag metadata."""
    other_data = raw_vault.get("other_data") or {}
    flag_fields = (
        "vault_display_flags",
        "morpho_vault_flags",
        "morpho_market_flags",
        "morpho_red_flags",
        "morpho_yellow_flags",
    )
    for field in flag_fields:
        flags = raw_vault.get(field)
        if flags is None:
            flags = other_data.get(field)
        if flags:
            return True
    return False


def matches_always_include(v, always_include_terms: tuple[str, ...]) -> str | None:
    """Return the matching always-include term for a vault."""
    haystack = " ".join(
        [
            v.name,
            v.protocol_slug,
        ]
    ).lower()
    for term in always_include_terms:
        if term and term.lower() in haystack:
            return term
    return None


def build_candidate_frame(
    vaults: list,
    raw_by_key: dict,
    min_tvl: float,
    min_age: float,
    chain_config: dict,
    always_include_terms: tuple[str, ...],
    allowed_denominations: set[str],
) -> pd.DataFrame:
    """Build filtered vault candidates for rolling top detection."""
    rows = []
    filter_kwargs = dict(
        allowed_denominations=allowed_denominations,
        excluded_risks=ROLLING_EXCLUDED_RISKS,
        excluded_flags=EXCLUDED_FLAGS,
        require_known_protocol=REQUIRE_KNOWN_PROTOCOL,
        hypercore_min_tvl=HYPERCORE_MIN_TVL,
        morpho_vault_flag_filter="none",
        skip_cagr_filter=True,
        use_peak_tvl=False,
    )

    for v in vaults:
        key = (v.chain_id, v.address)
        raw_vault = raw_by_key[key]
        always_include_term = matches_always_include(v, always_include_terms)

        if v.excluded or v.excluded_protocol_reason is not None:
            continue
        if v.protocol_slug == "morpho" and has_any_morpho_flags(raw_vault):
            continue
        if always_include_term is None and (v.risk is None or v.risk == "Unknown"):
            continue

        # Rolling mode applies TVL and age on each historical monthly snapshot.
        # Use only metadata-level filters here.
        passes, _reason = filter_vault(
            v,
            0,
            0,
            chain_config,
            **filter_kwargs,
        )
        if not passes and always_include_term is None:
            continue

        if always_include_term is not None:
            hard_filter_kwargs = dict(filter_kwargs)
            hard_filter_kwargs["excluded_risks"] = {"Blacklisted", "Dangerous"}
            passes_hard, _reason = filter_vault(
                v,
                0,
                0,
                chain_config,
                **hard_filter_kwargs,
            )
            if not passes_hard:
                continue

        rows.append(
            {
                "id": f"{v.chain_id}-{v.address}",
                "chain_id": v.chain_id,
                "chain": v.chain_name,
                "address": v.address,
                "name": v.name,
                "protocol": v.protocol_slug,
                "denomination": v.denomination,
                "risk": v.risk or "Unknown",
                "tvl": v.tvl,
                "current_apy": v.cagr_periods.get("3M"),
                "current_apy_1m": v.cagr_periods.get("1M"),
                "cagr_all": v.cagr_all,
                "always_include": always_include_term or "",
                "deposit_closed_reason": v.deposit_closed_reason,
            }
        )

    return pd.DataFrame(rows)


def calculate_rolling_top_appearances(
    candidates: pd.DataFrame,
    price_history_path: Path,
    *,
    min_tvl: float,
    min_age: float,
    chain_config: dict,
    window_days: int,
    top_per_chain: int,
) -> pd.DataFrame:
    """Calculate first historical monthly top-list appearance for candidate vaults.

    For every chain/month, rank vaults by their 90-day CAGR at the latest
    available daily observation in that month. TVL and age filters are evaluated
    at the same monthly snapshot. The returned set is the union of all vaults
    that ever appear in the monthly top-N list.
    """
    if candidates.empty:
        return candidates

    pairs_df = candidates[["chain_id", "address"]].copy()
    prices = read_vault_price_history_parquet(
        price_history_path,
        vault_pairs_df=pairs_df,
        columns=["timestamp", "chain", "address", "share_price", "total_assets"],
    )
    if prices.empty:
        return candidates.assign(first_top_at=pd.NaT, original_top_apy=None, original_top_rank=None)

    rolling_rows = []
    for (chain_id, address), group in prices.groupby(["chain", "address"], sort=False):
        group = group.sort_values("timestamp")
        daily = (
            group
            .set_index("timestamp")[["share_price", "total_assets"]]
            .resample("1D")
            .last()
            .dropna(subset=["share_price"])
        )
        if len(daily) <= window_days:
            continue

        share_price = daily["share_price"].astype(float)
        start_price = share_price.shift(window_days)
        total_assets = daily["total_assets"].astype(float)
        monthly_frame = pd.DataFrame(
            {
                "share_price": share_price,
                "start_price": start_price,
                "total_assets": total_assets,
            }
        )
        monthly_frame["rolling_cagr"] = (share_price / start_price) ** (365 / window_days) - 1
        monthly_frame = monthly_frame.replace([float("inf"), float("-inf")], pd.NA)
        monthly_frame = monthly_frame.dropna(subset=["rolling_cagr", "total_assets"])
        if monthly_frame.empty:
            continue

        effective_min_tvl = HYPERCORE_MIN_TVL if int(chain_id) == 9999 else min_tvl
        effective_min_age = chain_config.get(int(chain_id), {}).get("min_age", min_age)
        age_years = (monthly_frame.index - monthly_frame.index.min()) / pd.Timedelta(days=365.25)
        monthly_frame["age_years"] = age_years
        monthly_frame = monthly_frame[
            (monthly_frame["share_price"] > 0)
            & (monthly_frame["start_price"] > 0)
            & (monthly_frame["total_assets"] >= effective_min_tvl)
            & (monthly_frame["age_years"] >= effective_min_age)
        ].copy()
        if monthly_frame.empty:
            continue

        monthly_frame["month"] = monthly_frame.index.to_period("M").to_timestamp("M")
        frame = (
            monthly_frame
            .reset_index(names="timestamp")
            .sort_values("timestamp")
            .groupby("month", as_index=False)
            .tail(1)
            [["timestamp", "month", "rolling_cagr", "total_assets", "age_years"]]
        )
        frame["chain_id"] = int(chain_id)
        frame["address"] = str(address).lower()
        rolling_rows.append(frame)

    if not rolling_rows:
        return candidates.assign(first_top_at=pd.NaT, original_top_apy=None, original_top_rank=None)

    rolling_df = pd.concat(rolling_rows, ignore_index=True)
    rolling_df["rank"] = (
        rolling_df
        .groupby(["chain_id", "month"])["rolling_cagr"]
        .rank(method="first", ascending=False)
    )
    top_hits = rolling_df[rolling_df["rank"] <= top_per_chain].sort_values(["chain_id", "address", "month"])
    first_hits = top_hits.groupby(["chain_id", "address"], as_index=False).first()
    first_hits = first_hits.rename(
        columns={
            "timestamp": "first_top_at",
            "month": "first_top_month",
            "rolling_cagr": "original_top_apy",
            "rank": "original_top_rank",
            "total_assets": "original_top_tvl",
            "age_years": "original_top_age_years",
        }
    )

    selected = candidates.merge(first_hits, on=["chain_id", "address"], how="left")
    selected = selected[
        selected["first_top_at"].notna()
        | selected["always_include"].astype(bool)
    ].copy()

    selected["selection_reason"] = f"historical_top_{top_per_chain}"
    selected.loc[selected["always_include"].astype(bool), "selection_reason"] = (
        "always_include:" + selected.loc[selected["always_include"].astype(bool), "always_include"]
    )
    selected["sort_apy"] = (
        pd.to_numeric(selected["original_top_apy"], errors="coerce")
        .combine_first(pd.to_numeric(selected["current_apy"], errors="coerce"))
        .combine_first(pd.to_numeric(selected["cagr_all"], errors="coerce"))
    )
    return selected.sort_values(["chain_id", "first_top_at", "sort_apy"], ascending=[True, True, False])


def format_markdown_table(df: pd.DataFrame, limit: int | None) -> str:
    """Format rolling selected vaults as a Markdown table."""
    if limit is not None:
        df = df.head(limit)

    rows = []
    for _, row in df.iterrows():
        first_top_at = row.get("first_top_at")
        if pd.isna(first_top_at):
            first_top_at_value = "always include"
        else:
            first_top_at_value = pd.Timestamp(first_top_at).date().isoformat()
        rows.append(
            {
                "chain": row["chain"],
                "name": row["name"],
                "protocol": row["protocol"],
                "risk": row["risk"],
                "first appear in the top list": first_top_at_value,
                "original top APY": format_pct(row.get("original_top_apy")),
                "original top TVL": f"${row['original_top_tvl']:,.0f}" if pd.notna(row.get("original_top_tvl")) else "",
                "current APY": format_pct(row.get("current_apy")),
                "current TVL": f"${row['tvl']:,.0f}",
                "reason": row["selection_reason"],
                "address": row["address"],
            }
        )

    table = pd.DataFrame(rows)
    return table.to_markdown(index=False)


def run_rolling_top_detection(args) -> None:
    """Run rolling historical vault top-list selection."""
    chain_order, chain_config = parse_chain_ids(args.chain_ids)
    raw_vaults = fetch_vaults(DATA_URL)

    parsed = []
    raw_by_key = {}
    for rv in raw_vaults:
        v = parse_vault(rv, chain_config, TRACKED_PERIODS)
        if v is not None:
            parsed.append(v)
            raw_by_key[(v.chain_id, v.address)] = rv

    print(f"Parsed {len(parsed)} vaults on target chains", file=sys.stderr)
    always_include_terms = tuple(term.strip().lower() for term in args.always_include.split(",") if term.strip())
    allowed_denominations = {
        denomination.strip().upper()
        for denomination in args.denominations.split(",")
        if denomination.strip()
    }
    candidates = build_candidate_frame(
        parsed,
        raw_by_key,
        args.min_tvl,
        args.min_age,
        chain_config,
        always_include_terms,
        allowed_denominations,
    )
    print(f"Rolling candidates after metadata filters: {len(candidates)}", file=sys.stderr)

    selected = calculate_rolling_top_appearances(
        candidates,
        args.price_history,
        min_tvl=args.min_tvl,
        min_age=args.min_age,
        chain_config=chain_config,
        window_days=args.rolling_window_days,
        top_per_chain=args.rolling_top_per_chain,
    )
    print(f"Selected {len(selected)} rolling candidates", file=sys.stderr)

    if args.json:
        output = selected.copy()
        for column in ("first_top_at", "first_top_month"):
            if column in output.columns:
                output[column] = output[column].apply(lambda value: None if pd.isna(value) else pd.Timestamp(value).isoformat())
        print(output.to_json(orient="records", indent=2))
    else:
        print(format_markdown_table(selected, args.limit))


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
    parser.add_argument(
        "--rolling-top-detection", action="store_true",
        help="Use historical vault price data to select vaults that appeared in the rolling top list.",
    )
    parser.add_argument(
        "--price-history", type=Path, default=DEFAULT_ROLLING_PRICE_HISTORY,
        help=f"Vault price history parquet for --rolling-top-detection (default: {DEFAULT_ROLLING_PRICE_HISTORY})",
    )
    parser.add_argument(
        "--rolling-window-days", type=int, default=DEFAULT_ROLLING_WINDOW_DAYS,
        help=f"Rolling CAGR window in days (default: {DEFAULT_ROLLING_WINDOW_DAYS})",
    )
    parser.add_argument(
        "--rolling-top-per-chain", type=int, default=DEFAULT_ROLLING_TOP_PER_CHAIN,
        help=f"Historical top-N cutoff per chain (default: {DEFAULT_ROLLING_TOP_PER_CHAIN})",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_ROLLING_LIMIT,
        help="Maximum rows for Markdown table output in --rolling-top-detection mode (default: unlimited)",
    )
    parser.add_argument(
        "--chain-ids", default=None,
        help="Comma-separated chain ids to include, e.g. 1,8453,42161,999,143. Defaults to all configured chains.",
    )
    parser.add_argument(
        "--denominations", default=",".join(sorted(ALLOWED_DENOMINATIONS)),
        help="Comma-separated denomination symbols for --rolling-top-detection mode.",
    )
    parser.add_argument(
        "--always-include", default=",".join(DEFAULT_ALWAYS_INCLUDE_TERMS),
        help="Comma-separated name/protocol fragments to always include in --rolling-top-detection mode.",
    )
    parser.add_argument(
        "--morpho-vault-flag-ignore",
        "--morpho-vault-flag-filter",
        dest="morpho_vault_flag_filter",
        choices=MORPHO_VAULT_FLAG_FILTER_CHOICES,
        default="none",
        help=(
            "Filter out vaults with Morpho vault display flags by severity: "
            "none keeps current behaviour, red-only excludes red flags, "
            "red-and-yellow excludes red and yellow flags."
        ),
    )
    args = parser.parse_args()

    if args.rolling_top_detection:
        run_rolling_top_detection(args)
        return

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
        morpho_vault_flag_filter=args.morpho_vault_flag_filter,
        top_n_override=args.top,
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
                    "vault_display_flags": v.vault_display_flags,
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
            morpho_vault_flag_filter=args.morpho_vault_flag_filter,
        ))


if __name__ == "__main__":
    main()
