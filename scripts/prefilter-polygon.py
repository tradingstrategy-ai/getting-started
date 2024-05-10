"""Download all Polygon daily OHLCV and liquidity data and store it in Parquet.

- As the amount of data is large, do this only once to speed up the backtesting in liquidity-risk-analysis

- Large amount of RAM needed
"""
from pathlib import Path

import pandas as pd

from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.timebucket import TimeBucket

liquidity_output_fname = Path("/tmp/polygon-liquidity-prefiltered.parquet")
price_output_fname = Path("/tmp/polygon-price-prefiltered.parquet")

# If the pair does not have this liquidity, skip
min_prefilter_liquidity = 10_000

chain_id = ChainId.polygon
time_bucket = TimeBucket.d1
stop_loss_time_bucket = TimeBucket.h1
client = Client.create_jupyter_client()

# We need pair metadata to know which pairs belong to Polygon
print("Downloading/opening pairs dataset")
pairs_df = client.fetch_pair_universe().to_pandas()
our_chain_pair_ids = pairs_df[pairs_df.chain_id == chain_id.value]["pair_id"].unique()

print(f"We have data for {len(our_chain_pair_ids)} trading pairs on {chain_id.name}")

# Download all liquidity data, extract
# trading pairs that exceed our prefiltering threshold
print(f"Downloading/opening liquidity dataset {time_bucket}")
liquidity_df = client.fetch_all_liquidity_samples(time_bucket).to_pandas()
print(f"Filtering out liquidity for chain {chain_id.name}")
liquidity_df = liquidity_df.loc[liquidity_df.pair_id.isin(our_chain_pair_ids)]
liquidity_per_pair = liquidity_df.groupby(liquidity_df.pair_id)
print(f"Chain {chain_id.name} has liquidity data for {len(liquidity_per_pair.groups)}")

passed_pair_ids = set()
liquidity_output_chunks = []

for pair_id, pair_df in liquidity_per_pair:
    if pair_df["high"].max() > min_prefilter_liquidity:
        liquidity_output_chunks.append(pair_df)
        passed_pair_ids.add(pair_id)

print(f"After filtering for {min_prefilter_liquidity:,} USD min liquidity we have {len(passed_pair_ids)} pairs")

liquidity_out_df = pd.concat(liquidity_output_chunks)
liquidity_out_df.to_parquet(liquidity_output_fname)

print(f"Wrote {liquidity_output_fname}, {liquidity_output_fname.stat().st_size:,} bytes")

print(f"Downloading/opening OHLCV dataset for {stop_loss_time_bucket}")
price_df = client.fetch_all_candles(stop_loss_time_bucket).to_pandas()
price_df = price_df.loc[price_df.pair_id.isin(passed_pair_ids)]
price_df.to_parquet(price_output_fname)

print(f"Wrote {price_output_fname}, {price_output_fname.stat().st_size:,} bytes")
