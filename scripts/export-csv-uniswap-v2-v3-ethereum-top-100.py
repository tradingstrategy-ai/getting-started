"""Download top 100 liquid pairs from Uniswap v2 + Uniswap v3 and output OHLCV as CSV

- This is a data preprocessing script

- Downloads full DEX data dumps (price, liquidity) from Trading Strategy server

- Limit the dataset to Ethereum mainnet, Uniswap v2 and Uniswap v3 DEXes

- The data is "wrangled" for algorithmic trading by massaging out any extraction artifacts, like bad high/low/close values caused by MEV

- Take top 100 pairs by the liquidity of the start of the current week

- Filter out pairs that trade on multiple venues

- For price data output, merge pairs metadata so that the output CSV has human readable "ticker" column 

- The result CSV output is not sorted

- Large amount of RAM and disk space is needed, dataset being processed are in gigabytes.
  It is recommend you do the processing on a development server off-band and
  then transfer files to your local development laptop.

To run this script on getting-started environment:

.. code-block:: shell

  poetry shell
  python scripts/export-csv-uniswap-v2-v3-ethereum-top-100.py
  
If you run this script on a development server with more RAM, to transfer the generated files to local computer:

.. code-block:: shell

    rsync -av --inplace --progress "yourserver:.cache/tradingstrategy/prefiltered/*" ~/.cache/tradingstrategy/prefiltered/

"""
from collections import Counter
import os
from pathlib import Path

import pandas as pd

from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.timebucket import TimeBucket
from tradingstrategy.utils.time import floor_pandas_week
from tradingstrategy.utils.forward_fill import forward_fill 
from tradingstrategy.utils.wrangle import fix_dex_price_data 


def make_full_ticker(row: pd.Series) -> str:
    """Generate a base-quote ticker for a pair."""
    return row["base_token_symbol"] + "-" + row["quote_token_symbol"] + "-" + row["exchange_slug"] + "-" + str(row["fee"]) + "bps"


def make_simple_ticker(row: pd.Series) -> str:
    """Generate a ticker for a pair with fee and DEX info."""
    return row["base_token_symbol"] + "-" + row["quote_token_symbol"] 


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
  exchange_slugs = {"uniswap-v3", "uniswap-v2"}
  exported_top_pair_count = 100
  liquidity_comparison_date = floor_pandas_week(pd.Timestamp.now() - pd.Timedelta(days=7))  # What date we use to select top 100 liquid pairs

  # 
  # Set up output files - use Trading Strategy client's cache folder
  #
  client = Client.create_jupyter_client()
  cache_path = client.transport.cache_path
  fname = "uniswap-v2-v3-ethereum-top-100"
  os.makedirs(f"{cache_path}/prefiltered", exist_ok=True)
  liquidity_output_fname = Path(f"{cache_path}/prefiltered/liquidity-{fname}.csv")
  price_output_fname = Path(f"{cache_path}/prefiltered/price-{fname}.csv")

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
  print(f"We have data for {len(our_chain_pair_ids)} trading pairs on {fname} set")
  pairs_df = pairs_df.set_index("pair_id")
  pair_metadata = {pair_id: row for pair_id, row in pairs_df.iterrows()}

  # Download all liquidity data, extract
  # trading pairs that exceed our prefiltering threshold
  print(f"Downloading/opening TVL/liquidity dataset {liquidity_time_bucket}")
  liquidity_df = client.fetch_all_liquidity_samples(liquidity_time_bucket).to_pandas()
  print("Setting up per-pair liquidity filtering")
  liquidity_df = liquidity_df.loc[liquidity_df.pair_id.isin(our_chain_pair_ids)]
  liquidity_df = liquidity_df.set_index("timestamp").groupby("pair_id")
  print(f"Forward-filling liquidity, before forward-fill the size is {len(liquidity_df)} samples, target frequency is {liquidity_time_bucket.to_frequency()}")  
  liquidity_df = forward_fill(liquidity_df, liquidity_time_bucket.to_frequency(), columns=("close",))

  print(f"Filtering out liquidity for chain {chain_id.name}")
  # Find top 100 liquid pairs on a given date
  pair_liquidity_map = Counter()
  for pair_id in our_chain_pair_ids:
      try:
        # Access data using MultiIndex (pair, timestamp)[column]
        liquidity_sample = liquidity_df.obj.loc[pair_id, liquidity_comparison_date]["close"]
      except KeyError:
          # Pair not available, because liquidity data is not there, or zero, or broken
          continue
      pair_liquidity_map[pair_id] = liquidity_sample

  print(f"Chain {chain_id.name} has liquidity data for {len(pair_liquidity_map)} pairs at {liquidity_comparison_date}")

  # Remove duplicate pairs
  top_liquid_pairs_filtered = Counter()
  for pair_id, liquidity in pair_liquidity_map.items():
      ticker = make_simple_ticker(pair_metadata[pair_id])
      if ticker in top_liquid_pairs_filtered:
          # This pair is already in the dataset under a different pool
          # with more liquidity
          continue
      top_liquid_pairs_filtered[pair_id] = liquidity

  print("Top liquid 10 pairs at {liquidity_comparison_date}")
  for idx, tpl in enumerate(top_liquid_pairs_filtered.most_common(10), start=1):
      pair_id, liquidity = tpl
      ticker = make_full_ticker(pair_metadata[pair_id])
      print(f"{idx}. {ticker}: {liquidity:,.2f} USD")

  top_liquid_pair_ids = {key for key, _ in top_liquid_pairs_filtered.most_common(exported_top_pair_count)}

  # Check how much liquidity we can address
  total_liq = 0
  for pair_id in top_liquid_pair_ids:
      total_liq += pair_liquidity_map[pair_id]
  print(f"Total available tradeable liquidity at {liquidity_comparison_date} for {len(top_liquid_pair_ids)} pairs is {total_liq:,.2f} USD")

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
  price_df["ticker"] = price_df.apply(lambda row: make_full_ticker(pair_metadata[row.pair_id]), axis=1)
  price_df["link"] = price_df.apply(lambda row: make_link(pair_metadata[row.pair_id]), axis=1)

  print(f"Writing OHLCV CSV")
  column_order = ('ticker', 'open', 'high', 'low', 'close', 'volume', 'link', 'pair_id',)
  price_df = price_df.reindex(columns=column_order)  # Sort columns in a specific order
  price_df.to_csv(
    price_output_fname,
  )
  print(f"Wrote {price_output_fname}, {price_output_fname.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()