"""Download top 100 liquid pairs from Uniswap v2, Uniswap v3, Sushi and output OHLCV as CSV, filter with TokenSniffer

- Aggregate output across multiple trading pairs

- See `export-csv-uniswap-v2-v3-ethereum-top-100-sniffer.py` for more details

"""

import logging
from collections import Counter
import os
import sys
from pathlib import Path

import pandas as pd

from tradingstrategy.pair import PandasPairUniverse
from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.timebucket import TimeBucket
from tradingstrategy.utils.time import floor_pandas_week
from tradingstrategy.utils.forward_fill import forward_fill
from tradingstrategy.utils.wrangle import fix_dex_price_data
from tradingstrategy.utils.liquidity_filter import build_liquidity_summary, get_top_liquidity_pairs_by_base_token
from tradingstrategy.utils.token_filter import filter_pairs_default
from tradingstrategy.utils.aggregate_ohlcv import aggregate_ohlcv_across_pairs
from tradingstrategy.utils.wrangle import examine_anomalies
from eth_defi.token_analysis.tokensniffer import CachedTokenSniffer, is_tradeable_token, KNOWN_GOOD_TOKENS


# You can optionally give TokenSniffer API key to check for scam tokens as the part of the process
TOKENSNIFFER_API_KEY = os.environ.get("TOKENSNIFFER_API_KEY")


def main():

    # Configure logging using basicConfig
    logging.basicConfig(
        level=logging.WARNING,  # Set logging level to WARNING or above
        format='%(asctime)s - %(levelname)s - %(message)s',  # Set the format of the log message
        stream=sys.stdout  # Direct logs to stdout
    )
    
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
    fname = "uniswap-v2-v3-ethereum-top-100-sniffed-agg"
    os.makedirs(f"{cache_path}/prefiltered", exist_ok=True)
    price_output_fname = Path(f"{cache_path}/prefiltered/price-{fname}.csv")

    #
    # Setup TokenSniffer
    #

    db_file = Path(cache_path) / "tokensniffer.sqlite"

    if TOKENSNIFFER_API_KEY:
        sniffer = CachedTokenSniffer(
            db_file,
            TOKENSNIFFER_API_KEY,
        )
    else:
        sniffer = None

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
    
    pair_universe = PandasPairUniverse(pairs_df)
        
    print(f"We have data for {len(our_chain_pair_ids)} trading pairs on {fname} set")

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
       
    # Remove duplicate pairs
    print("Prefiltering and removing duplicate pairs")
    top_liquid_pairs_filtered = Counter()
    processed_base_tokens = set()
    
    # List of base token addresses that have reached the threshold.
    # Is ordered.
    all_base_tokens = list()
    
    for pair_id, liquidity in pair_liquidity_max_historical.most_common():
        pair_metadata = pair_universe.get_pair_by_id(pair_id)
        base_token_symbol = pair_metadata.base_token_symbol
        if liquidity < min_liquidity_threshold:
            # Prefilter pairs
            continue
        if base_token_symbol in processed_base_tokens:
            # This pair is already in the dataset under a different pool
            # with more liquidity
            continue
        top_liquid_pairs_filtered[pair_id] = liquidity
        all_base_tokens.append(pair_metadata.base_token_address)
        
    # Remove duplicat base tokens, maintain the list order
    seen = set()
    included_base_tokens = [x for x in all_base_tokens if not (x in seen or seen.add(x))]        

    print(f"After prefilter, we have {len(top_liquid_pairs_filtered):,} pairs left")
    print(f"This is {len(all_base_tokens)} pairs with {len(included_base_tokens)} included base tokens")

    safe_top_liquid_pairs_filtered = Counter()
    
    base_token_liquidity = get_top_liquidity_pairs_by_base_token(
        pair_universe,
        top_liquid_pairs_filtered,
        good_base_tokens=included_base_tokens,
        count=allowed_pairs_for_token_sniffer
    )
    
    print(f"Base token mapped liquidity has {len(base_token_liquidity)} pairs")

    if TOKENSNIFFER_API_KEY:
        # Remove tokens failing sniff test
        print(f"Sniffing out bad trading pairs, max allowed {allowed_pairs_for_token_sniffer}")
    else:
        print(f"TokenSniffer DISABLED. Give TOKENSNIFFER_API_KEY env.")
    
    for pair_id, liquidity in base_token_liquidity:
        dex_pair = pair_universe.get_pair_by_id(pair_id)
        ticker = dex_pair.get_ticker()
        base_token_symbol = dex_pair.base_token_symbol
        address = dex_pair.base_token_address

        if sniffer:
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
                risk_score_threshold=tokensniffer_threshold
            ):
                score = sniffed_data["score"]
                whitelisted = base_token_symbol in KNOWN_GOOD_TOKENS
                print(f"WARN: Skipping pair {ticker}, address {address} as the TokenSniffer score {score} (whitelisted {whitelisted}) is below our risk threshold, liquidity is {liquidity:,.2f} USD")
                continue

        safe_top_liquid_pairs_filtered[pair_id] = liquidity

    skipped_tokens = len(top_liquid_pairs_filtered) - len(safe_top_liquid_pairs_filtered)
    print(f"We skip {skipped_tokens:,} in TokenSniffer filter")
    if sniffer:
        print(f"Token sniffer info is:\n{sniffer.get_diagnostics()}")

    print(f"Top liquid 10 pairs (historically), sorted by base token")
    for idx, tpl in enumerate(safe_top_liquid_pairs_filtered.most_common(10), start=1):
        pair_id, liquidity = tpl
        pair_metadata = pair_universe.get_pair_by_id(pair_id)
        ticker = f"{pair_metadata.get_ticker()} with fee {pair_metadata.fee} BPS on {pair_metadata.exchange_slug}"
        print(f"{idx}. {ticker}: {liquidity:,.2f} USD")

    top_liquid_pair_ids = {key for key, _ in safe_top_liquid_pairs_filtered.most_common(exported_top_pair_count)}

    # Check how much liquidity we can address
    total_liq = 0
    for pair_id in top_liquid_pair_ids:
        total_liq += pair_liquidity_max_historical[pair_id]
    print(f"Historical tradeable liquidity for {len(top_liquid_pair_ids)} pairs is {total_liq:,.2f} USD")    
    total_liq = 0
    for pair_id in top_liquid_pair_ids:
        total_liq += pair_liquidity_today[pair_id]
    print(f"Today's tradeable liquidity for {len(top_liquid_pair_ids)} pairs is {total_liq:,.2f} USD")
    
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
    
    pair_universe_left = pair_universe.limit_to_pairs(top_liquid_pair_ids)

    print(f"Building OHLCVL aggregate data across {pair_universe_left.get_count()} pairs, down from {pair_universe.get_count()} pairs")

    agg_df = aggregate_ohlcv_across_pairs(
        pair_universe_left,
        price_df,
        liquidity_df["close"],
    )
    
    # Convert pair id list to comma-separated strings
    agg_df["pair_ids"] = agg_df["pair_ids"].apply(lambda x: str(x))
    
    # Moved to notebook.
    #
    # See scratchpad/bad-data
    #
    # print("Checking aggregate data issues")
    # examine_anomalies(
    #     None,
    #     agg_df,
    #     pair_id_column="aggregate_id",
    # )

    print(f"The aggregate price/liquidity dataset contains total {len(agg_df['base'].unique())} base tokens, {len(agg_df):,} rows")
    
    # Export data, make sure we got columns in an order we want
    print(f"Writing OHLCV CSV")
    column_order = (
        "base",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "liquidity",
        "aggregate_id",
        "pair_ids"
    )
    agg_df = agg_df.reindex(columns=column_order)  # Sort columns in a specific order
    agg_df.to_csv(
        price_output_fname,
    )
    print(f"Wrote {price_output_fname}, {price_output_fname.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
