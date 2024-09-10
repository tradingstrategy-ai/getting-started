"""Download top 100 liquid pairs from Uniswap v2, Uniswap v3, Sushi and output OHLCV as CSV, filter with TokenSniffer

- Factors for survivorship-bias by sorting top 100 by their maximum historical liquidity, not the current liquidity

- Filter out bad known untradeable tokens like OHM (rebase)

- Filter out non-volatile pairs like USDT/USDC

- Uses TokenSniffer to filter out ponzis, honeypots and such: TokenSniffer API key needed

- See `export-csv-uniswap-v2-v3-ethereum-top-100.py` for more details

"""

from collections import Counter
import os
from pathlib import Path

import pandas as pd

from tradingstrategy.pair import DEXPair
from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.timebucket import TimeBucket
from tradingstrategy.utils.time import floor_pandas_week
from tradingstrategy.utils.forward_fill import forward_fill
from tradingstrategy.utils.wrangle import fix_dex_price_data
from tradingstrategy.utils.liquidity_filter import build_liquidity_summary
from tradingstrategy.utils.token_filter import filter_pairs_default
from eth_defi.token_analysis.tokensniffer import CachedTokenSniffer, is_tradeable_token, KNOWN_GOOD_TOKENS


TOKENSNIFFER_API_KEY = os.environ.get("TOKENSNIFFER_API_KEY")
assert TOKENSNIFFER_API_KEY, "TOKENSNIFFER_API_KEY env missing"


def make_full_ticker(row: pd.Series) -> str:
    """Generate a base-quote ticker for a pair."""
    return row["base_token_symbol"] + "-" + row["quote_token_symbol"] + "-" + row["exchange_slug"] + "-" + str(row["fee"]) + "bps"


def make_simple_ticker(row: pd.Series) -> str:
    """Generate a ticker for a pair with fee and DEX info."""
    return row["base_token_symbol"] + "-" + row["quote_token_symbol"]


def make_base_symbol(row: pd.Series) -> str:
    """Generate a base symbol."""
    return row["base_token_symbol"] 


def make_link(row: pd.Series) -> str:
    """Get TradingStrategy.ai explorer link for the trading data"""
    chain_slug = ChainId(row.chain_id).get_slug()
    return f"https://tradingstrategy.ai/trading-view/{chain_slug}/{row.exchange_slug}/{row.pair_slug}"


def main():

    #
    # Set up filtering and output parameters
    #

    chain_id = ChainId.ethereum
    time_bucket = TimeBucket.d1  # OHCLV data frequency
    liquidity_time_bucket = TimeBucket.d1  # TVL data for Uniswap v3 is only sampled daily, more fine granular is not needed
    exchange_slugs = {"uniswap-v3", "uniswap-v2", "sushi"}
    exported_top_pair_count = 100
    liquidity_comparison_date = floor_pandas_week(pd.Timestamp.now() - pd.Timedelta(days=7))  # What date we use to select top 100 liquid pairs
    tokensniffer_threshold = 24  # We want our TokenSniffer score to be higher than this for base tokens
    min_liquidity_threshold = 4_000_000  # Prefilter pairs with this liquidity before calling token sniffer
    allowed_pairs_for_token_sniffer = 250  # How many pairs we let to go through TokenSniffer filtering process (even if still above min_liquidity_threshold)

    #
    # Set up output files - use Trading Strategy client's cache folder
    #
    client = Client.create_jupyter_client()
    cache_path = client.transport.cache_path
    fname = "uniswap-v2-v3-ethereum-top-100-sniffed"
    os.makedirs(f"{cache_path}/prefiltered", exist_ok=True)
    liquidity_output_fname = Path(f"{cache_path}/prefiltered/liquidity-{fname}.csv")
    price_output_fname = Path(f"{cache_path}/prefiltered/price-{fname}.csv")

    #
    # Setup TokenSniffer
    #

    db_file = Path(cache_path) / "tokensniffer.sqlite"

    sniffer = CachedTokenSniffer(
        db_file,
        TOKENSNIFFER_API_KEY,
    )

    #
    # Set out trading pair universe
    #

    print("Downloading/opening exchange dataset")
    exchange_universe = client.fetch_exchange_universe()

    # Resolve uniswap-v3 internal id
    exchanges = [exchange_universe.get_by_chain_and_slug(chain_id, exchange_slug) for exchange_slug in exchange_slugs]
    exchange_ids = [exchange.exchange_id for exchange in exchanges]
    print(f"Exchange {exchange_slugs} ids are {exchange_ids}")

    # We need pair metadata to know which pairs belong to Polygon
    print("Downloading/opening pairs dataset")
    pairs_df = client.fetch_pair_universe().to_pandas()
    
    pairs_df = filter_pairs_default(
        pairs_df,
        chain_id=chain_id,
        exchange_ids=exchange_ids,
    )
    our_chain_pair_ids = pairs_df["pair_id"]
        
    print(f"We have data for {len(our_chain_pair_ids)} trading pairs on {fname} set")
    print("Building pair metadata map")
    pairs_df = pairs_df.set_index("pair_id")
    pair_metadata = {pair_id: row for pair_id, row in pairs_df.iterrows()}
    uni_v3_pair_metadata = {pair_id: row for pair_id, row in pairs_df.iterrows() if row["exchange_slug"] == "uniswap-v3"}
    print(f"From this, Uniswap v3 data has {len(uni_v3_pair_metadata)} pairs")

    #
    # Filter by liquidity
    #    

    # Download all liquidity data, extract
    # trading pairs that exceed our prefiltering threshold
    print(f"Downloading/opening TVL/liquidity dataset {liquidity_time_bucket}")
    liquidity_df = client.fetch_all_liquidity_samples(liquidity_time_bucket).to_pandas()
    print(f"Setting up per-pair liquidity filtering, raw liquidity data os {len(liquidity_df):,} entries")
    liquidity_df = liquidity_df.loc[liquidity_df.pair_id.isin(our_chain_pair_ids)]
    liquidity_df = liquidity_df.set_index("timestamp").groupby("pair_id")
    print(f"Forward-filling liquidity, before forward-fill the size is {len(liquidity_df)} samples, target frequency is {liquidity_time_bucket.to_frequency()}")
    liquidity_df = forward_fill(liquidity_df, liquidity_time_bucket.to_frequency(), columns=("close",))  # Only daily close liq needed for analysis, don't bother resample other cols
    
    # Get top liquidity for all of our pairs
    print(f"Filtering out historical liquidity of pairs")    
    pair_liquidity_max_historical, pair_liquidity_today = build_liquidity_summary(liquidity_df, our_chain_pair_ids)
    print(f"Chain {chain_id.name} has liquidity data for {len(pair_liquidity_max_historical)} pairs at {liquidity_comparison_date}")
    
    # Check how many pairs did not have good values for liquidity
    broken_pairs = {pair_id for pair_id, liquidity in pair_liquidity_max_historical.items() if liquidity < 0}
    print(f"Liquidity data is broken for {len(broken_pairs)} trading pairs")
    
    uniswap_v3_liquidity_pairs = {pair_id for pair_id in pair_liquidity_max_historical.keys() if pair_id in uni_v3_pair_metadata}
    print(f"From this, Uniswap v3 is {len(uniswap_v3_liquidity_pairs)} pairs")
    assert len(uniswap_v3_liquidity_pairs) > 0, "No Uniswap v3 liquidity detected"
    
    # Remove duplicate pairs
    print("Prefiltering and removing duplicate pairs")
    top_liquid_pairs_filtered = Counter()
    processed_base_tokens = set()
    for pair_id, liquidity in pair_liquidity_max_historical.most_common():
        base_token_symbol = make_base_symbol(pair_metadata[pair_id])
        if liquidity < min_liquidity_threshold:
            # Prefilter pairs
            continue
        if base_token_symbol in processed_base_tokens:
            # This pair is already in the dataset under a different pool
            # with more liquidity
            continue
        top_liquid_pairs_filtered[pair_id] = liquidity
        processed_base_tokens.add(base_token_symbol)

    print(f"After prefilter, we have {len(top_liquid_pairs_filtered):,} pairs left")

    # Remove tokens failing sniff test
    print(f"Sniffing out bad trading pairs, max allowed {allowed_pairs_for_token_sniffer}")
    safe_top_liquid_pairs_filtered = Counter()
    for pair_id, liquidity in top_liquid_pairs_filtered.most_common(allowed_pairs_for_token_sniffer):
        ticker = make_full_ticker(pair_metadata[pair_id])        
        pair_row = pair_metadata[pair_id]
        dex_pair = DEXPair.from_series(pair_id, pair_row)
        base_token_symbol = dex_pair.base_token_symbol
        address = dex_pair.base_token_address
        try:
            sniffed_data = sniffer.fetch_token_info(chain_id.value, address)
        except Exception as e:
            
            if "404" in str(e):
                # No idea what's going on with these ones
                # RuntimeError: Could not verify OLAS-WETH-uniswap-v2-30bps, address 0x0001a500a6b18995b03f44bb040a5ffc28e45cb0: TokeSniffer replied: <Response [404]>: {"message":"Contract not found"}
                print(f"WARN: TokenSniffer 404 not found {ticker}, address {address} as the TokenSniffer score {score} is below our risk threshold, liquidity is {liquidity:,.2f} USD")
                continue
            
            raise RuntimeError(f"Could not sniff {ticker}, address {address}: {e}") from e
        
        if not is_tradeable_token(
            sniffed_data, 
            symbol=base_token_symbol,
            risk_score_threshold=tokensniffer_threshold):
            score = sniffed_data["score"]
            whitelisted = base_token_symbol in KNOWN_GOOD_TOKENS
            print(f"WARN: Skipping pair {ticker}, address {address} as the TokenSniffer score {score} (whitelisted {whitelisted}) is below our risk threshold, liquidity is {liquidity:,.2f} USD")
            continue

        safe_top_liquid_pairs_filtered[pair_id] = liquidity

    skipped_tokens = len(top_liquid_pairs_filtered) - len(safe_top_liquid_pairs_filtered)
    print(f"We skip {skipped_tokens:,} in TokenSniffer filter")
    print(f"Token sniffer info is:\n{sniffer.get_diagnostics()}")

    print(f"Top liquid 10 pairs (historically)")
    for idx, tpl in enumerate(safe_top_liquid_pairs_filtered.most_common(10), start=1):
        pair_id, liquidity = tpl
        ticker = make_full_ticker(pair_metadata[pair_id])
        print(f"{idx}. {ticker}: {liquidity:,.2f} USD")

    top_liquid_pair_ids = {key for key, _ in safe_top_liquid_pairs_filtered.most_common(exported_top_pair_count)}

    def is_uniswap_v3(pair_id):
        metadata = pair_metadata[pair_id]
        return metadata["exchange_slug"] == "uniswap-v3"
    
    assert any([is_uniswap_v3(pair_id) for pair_id in top_liquid_pair_ids]), "Top liquid pars did not contain a single Uni v3 pair"

    # Check how much liquidity we can address
    total_liq = 0
    for pair_id in top_liquid_pair_ids:
        total_liq += pair_liquidity_max_historical[pair_id]
    print(f"Historical tradeable liquidity for {len(top_liquid_pair_ids)} pairs is {total_liq:,.2f} USD")    
    total_liq = 0
    for pair_id in top_liquid_pair_ids:
        total_liq += pair_liquidity_today[pair_id]
    print(f"Today's tradeable liquidity for {len(top_liquid_pair_ids)} pairs is {total_liq:,.2f} USD")
    
    # Clamp liquidity output to only 100 top pairs
    # TODO: wrangle liquidity data for spikes and massage them out
    liquidity_df = liquidity_df.obj
    liquidity_out_df = liquidity_df[liquidity_df.index.get_level_values(0).isin(top_liquid_pair_ids)]  # Select from (pair id, timestamp) MultiIndex
    liquidity_out_df.to_csv(liquidity_output_fname)
    print(f"Wrote {liquidity_output_fname}, {liquidity_output_fname.stat().st_size:,} bytes")

    # After we know pair ids that fill the liquidity criteria,
    # we can build OHLCV dataset for these pairs
    print(f"Downloading/opening OHLCV dataset {time_bucket}")
    price_df = client.fetch_all_candles(time_bucket).to_pandas()
    print(f"Filtering out {len(top_liquid_pair_ids)} pairs")
    price_df = price_df.loc[price_df.pair_id.isin(top_liquid_pair_ids)]

    print("Wrangling DEX price data")
    price_df = price_df.set_index("timestamp", drop=False).groupby("pair_id")
    price_df = fix_dex_price_data(
        price_df,
        freq=time_bucket.to_frequency(),
        forward_fill=True,
    )

    print(f"Retrofitting OHLCV columns for human readability")
    price_df = price_df.obj
    price_df["pair_id"] = price_df.index.get_level_values(0)
    price_df["ticker"] = price_df["pair_id"].apply(lambda pair_id: make_full_ticker(pair_metadata[pair_id]))
    price_df["link"] = price_df["pair_id"].apply(lambda pair_id: make_link(pair_metadata[pair_id]))
    price_df["base"] = price_df["pair_id"].apply(lambda pair_id: pair_metadata[pair_id]["base_token_symbol"])
    price_df["quote"] = price_df["pair_id"].apply(lambda pair_id: pair_metadata[pair_id]["quote_token_symbol"])
    price_df["fee"] = price_df["pair_id"].apply(lambda pair_id: pair_metadata[pair_id]["fee"])

    # Export data, make sure we got columns in an order we want
    print(f"Writing OHLCV CSV")
    del price_df["timestamp"]
    del price_df["pair_id"]
    price_df = price_df.reset_index()
    column_order = (
        "ticker",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "base",
        "quote",
        "fee",
        "link",
        "pair_id",
    )
    price_df = price_df.reindex(columns=column_order)  # Sort columns in a specific order
    price_df.to_csv(
        price_output_fname,
    )
    print(f"Wrote {price_output_fname}, {price_output_fname.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
