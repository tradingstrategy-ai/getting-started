"""Find top ERC-4626 vaults by monthly returns for cross-chain strategy.

- Loads vault metadata and price data
- Calculates lifetime metrics including monthly returns
- Filters out dangerous and blacklisted vaults
- Filters to stablecoin-denominated vaults only
- Shows top vaults for Base, Arbitrum, and Ethereum sorted by 1-month CAGR
- Outputs vault addresses in a format suitable for ChainId.cross_chain configuration
"""

import warnings
from pathlib import Path

import pandas as pd

from eth_defi.research.vault_metrics import (
    calculate_lifetime_metrics,
    clean_lifetime_metrics,
    format_lifetime_table,
)
from eth_defi.token import is_stablecoin_like
from eth_defi.vault.risk import VaultTechnicalRisk
from eth_defi.vault.vaultdb import DEFAULT_VAULT_DATABASE, DEFAULT_RAW_PRICE_DATABASE, VaultDatabase
from tradingstrategy.utils.flexible_pickle import flexible_load, filter_broken_enum_values

# Chains we are interested in (integer chain IDs)
TARGET_CHAINS = {
    1: "Ethereum",
    8453: "Base",
    42161: "Arbitrum",
}

# Minimum TVL to consider a vault investable
MIN_TVL = 50_000

# How many top vaults to show per chain
TOP_PER_CHAIN = 25


def main():
    with open(DEFAULT_VAULT_DATABASE, "rb") as f:
        vault_db: VaultDatabase = flexible_load(f)
    prices_df = pd.read_parquet(DEFAULT_RAW_PRICE_DATABASE)

    # Clean broken enum values left by flexible_load
    for spec, row in vault_db.items():
        detection = row.get("_detection_data")
        if detection is not None and hasattr(detection, "features") and detection.features is not None:
            object.__setattr__(detection, "features", filter_broken_enum_values(detection.features))

    print(f"Loaded {len(vault_db):,} vaults in metadata database")
    print(f"Loaded {len(prices_df):,} price rows")

    # Filter prices to target chains only
    prices_df = prices_df[prices_df["chain"].isin(TARGET_CHAINS.keys())]
    print(f"After chain filter: {len(prices_df):,} price rows")

    # Filter to stablecoin-denominated vaults only
    stablecoin_vault_specs = set()
    for spec, row in vault_db.items():
        if is_stablecoin_like(row["Denomination"]):
            stablecoin_vault_specs.add(spec)

    stablecoin_vault_ids = set()
    for spec in stablecoin_vault_specs:
        vault_id = f"{spec.chain_id}-{spec.vault_address}"
        stablecoin_vault_ids.add(vault_id)

    prices_df = prices_df[prices_df["id"].isin(stablecoin_vault_ids)]
    print(f"After stablecoin filter: {len(prices_df):,} price rows")

    # Calculate metrics per chain and combine
    combined_dfs = []

    for chain_id, chain_name in TARGET_CHAINS.items():
        print(f"\nCalculating metrics for {chain_name} (chain_id={chain_id})...")

        vault_db_filtered = {
            spec: vault for spec, vault in vault_db.items()
            if spec.chain_id == chain_id
        }
        chain_prices = prices_df[prices_df["chain"] == chain_id]

        if not vault_db_filtered or chain_prices.empty:
            print(f"  No data for {chain_name}, skipping")
            continue

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            warnings.simplefilter("ignore", RuntimeWarning)
            lifetime_df = calculate_lifetime_metrics(chain_prices, vault_db_filtered)

        lifetime_df = clean_lifetime_metrics(
            lifetime_df,
            max_annualised_return=0.50,
        )

        print(f"  {len(lifetime_df):,} vaults after cleaning")
        combined_dfs.append(lifetime_df)

    if not combined_dfs:
        print("No vault data found.")
        return

    all_df = pd.concat(combined_dfs)

    # Filter out dangerous and blacklisted vaults
    before = len(all_df)
    all_df = all_df[~all_df["risk"].isin([
        VaultTechnicalRisk.dangerous,
        VaultTechnicalRisk.blacklisted,
    ])]
    print(f"\nFiltered out {before - len(all_df)} dangerous/blacklisted vaults")

    # Filter by minimum TVL
    before = len(all_df)
    all_df = all_df[all_df["current_nav"] >= MIN_TVL]
    print(f"Filtered out {before - len(all_df)} vaults below ${MIN_TVL:,} TVL")

    # Drop vaults without monthly return data
    all_df = all_df.dropna(subset=["one_month_cagr"])

    print(f"\nTotal vaults after all filters: {len(all_df):,}")

    # Show top vaults per chain
    for chain_id, chain_name in TARGET_CHAINS.items():
        chain_df = all_df[all_df["chain_id"] == chain_id].copy()
        if chain_df.empty:
            print(f"\n{'='*80}")
            print(f"  {chain_name}: No qualifying vaults")
            continue

        chain_df = chain_df.sort_values("one_month_cagr", ascending=False)
        top = chain_df.head(TOP_PER_CHAIN)

        print(f"\n{'='*80}")
        print(f"  Top {len(top)} vaults on {chain_name} by 1-month CAGR (not dangerous)")
        print(f"{'='*80}")

        formatted = format_lifetime_table(
            top.copy(),
            add_index=True,
            add_address=True,
        )
        with pd.option_context(
            "display.max_columns", None,
            "display.width", 200,
            "display.max_colwidth", 30,
        ):
            print(formatted.to_string())

        # Print vault addresses for copy-paste into notebook configuration
        print(f"\n# {chain_name} vaults for ChainId.cross_chain configuration:")
        chain_id_name = {1: "ethereum", 8453: "base", 42161: "arbitrum"}[chain_id]
        for _, row in top.iterrows():
            risk_label = row["risk"].name if row["risk"] else "unknown"
            print(
                f'    (ChainId.{chain_id_name}, "{row["address"]}"),  '
                f'# {row["name"]} ({row["protocol"]}, {row["denomination"]}, '
                f'risk={risk_label}, 1m_cagr={row["one_month_cagr"]:.1%})'
            )


if __name__ == "__main__":
    main()
