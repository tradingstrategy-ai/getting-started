"""Download all Uniswap v3 hourly OHLCV and liquidity Ethereum and store it in Parquet.

- Daily candles

- See `prefilter-uniswap-v2-v3-ethereum.py` for more information

"""
import os
from pathlib import Path

import pandas as pd

from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.timebucket import TimeBucket


client = Client.create_jupyter_client()
cache_path = client.transport.cache_path

#
# Set up filtering and output parameters
#

chain_id = ChainId.ethereum
time_bucket = TimeBucket.d1
# TVL data for Uniswap v3 is only sampled daily.
# more fine granular is not needed
liquidity_time_bucket = TimeBucket.d1
exchange_slugs = {"uniswap-v3", "uniswap-v2"}
# If the pair does not have this liquidity USD ever, skip the trading pair
# to keep the dataset smaller
min_prefilter_liquidity = 10_000
fname = "uniswap-v2-v3-ethereum"
compression_level = 15

os.makedirs(f"{cache_path}/prefiltered", exist_ok=True)
liquidity_output_fname = Path(f"{cache_path}/prefiltered/liquidity-{fname}-{liquidity_time_bucket.value}.parquet")
price_output_fname = Path(f"{cache_path}/prefiltered/price-{fname}-{time_bucket.value}.parquet")

#
# Download - process - save
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
our_chain_pair_ids = pairs_df[(pairs_df.chain_id == chain_id.value) & (pairs_df.exchange_id.isin(exchange_ids))]["pair_id"].unique()

print(f"We have data for {len(our_chain_pair_ids)} trading pairs on {fname}")

# Download all liquidity data, extract
# trading pairs that exceed our prefiltering threshold
print(f"Downloading/opening TVL/liquidity dataset {liquidity_time_bucket}")
liquidity_df = client.fetch_all_liquidity_samples(liquidity_time_bucket).to_pandas()
print(f"Filtering out liquidity for chain {chain_id.name}")
liquidity_df = liquidity_df.loc[liquidity_df.pair_id.isin(our_chain_pair_ids)]
liquidity_per_pair = liquidity_df.groupby(liquidity_df.pair_id)
print(f"Chain {chain_id.name} has liquidity data for {len(liquidity_per_pair.groups)}")

# Check that the highest peak of the pair liquidity filled our threshold
passed_pair_ids = set()
liquidity_output_chunks = []

for pair_id, pair_df in liquidity_per_pair:
    if pair_df["high"].max() > min_prefilter_liquidity:
        liquidity_output_chunks.append(pair_df)
        passed_pair_ids.add(pair_id)

print(f"After filtering for {min_prefilter_liquidity:,} USD min liquidity we have {len(passed_pair_ids)} pairs")

liquidity_out_df = pd.concat(liquidity_output_chunks)
liquidity_out_df.to_parquet(
  liquidity_output_fname,
  engine='pyarrow', 
  compression='zstd', 
  compression_level=compression_level,      
)

print(f"Wrote {liquidity_output_fname}, {liquidity_output_fname.stat().st_size:,} bytes")

# After we know pair ids that fill the liquidity criteria,
# we can build OHLCV dataset for these pairs
print(f"Downloading/opening OHLCV dataset {time_bucket}")
price_df = client.fetch_all_candles(time_bucket).to_pandas()
print(f"Filtering out {len(passed_pair_ids)} pairs")
price_df = price_df.loc[price_df.pair_id.isin(passed_pair_ids)]
print(f"Writing Parquet")
price_df.to_parquet(
  price_output_fname,
  engine='pyarrow', 
  compression='zstd', 
  compression_level=compression_level,  
)

print(f"Wrote {price_output_fname}, {price_output_fname.stat().st_size:,} bytes")
