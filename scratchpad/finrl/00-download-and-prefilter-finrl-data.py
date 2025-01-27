"""Download all Base daily OHLCV and liquidity data and store it in Parquet.

- FinRL prepartion

- Write a Parquet with prepared data for chosen pairs

- As the amount of data is large, do this preparation only once

Output index:

- (pair_id, timestamp)

Output columns:

- ticker
- dex
- fee
- open
- high
- low
- close
- volume
- tvl

To run:

.. code-block:: shell

    python scratchpad/finrl/prefilter-finrl.py

"""

import datetime
import os
from pathlib import Path

import pandas as pd
from IPython.core.display_functions import display

from tradingstrategy.chain import ChainId
from tradingstrategy.client import Client
from tradingstrategy.exchange import ExchangeType
from tradingstrategy.pair import PandasPairUniverse
from tradingstrategy.timebucket import TimeBucket
from tradingstrategy.utils.token_filter import filter_pairs_default
from tradingstrategy.utils.wrangle import fix_dex_price_data


def fill_missing_ohlcv(df, columns_to_zero=['open', 'high', 'low', 'close', 'volume', 'tvl']):
    """
    Fill missing timestamps for each pair_id with zeros for specified columns.

    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame with MultiIndex (pair_id, timestamp)
    columns_to_zero : list, optional
        Columns to fill with zeros when data is missing

    Returns:
    --------
    pandas.DataFrame
        DataFrame with missing timestamps filled with zeros
    """
    # Get full timestamp range across all pair_ids
    full_timestamp_range = df.index.get_level_values('timestamp').unique()

    # Create a new index with all combinations of pair_ids and timestamps
    pair_ids = df.index.get_level_values('pair_id').unique()
    multi_index = pd.MultiIndex.from_product([pair_ids, full_timestamp_range],
                                             names=['pair_id', 'timestamp'])

    # Reindex the original DataFrame
    filled_df = df.reindex(multi_index)

    # Fill specified columns with zeros where data is missing
    # for col in columns_to_zero:
    #    filled_df[col] = filled_df[col]

    return filled_df


def main():

    chain_id = ChainId.ethereum
    time_bucket = TimeBucket.d1
    liquidity_time_bucket = TimeBucket.d1
    exchange_slugs = {"uniswap-v3", "uniswap-v2"}
    min_prefilter_liquidity = 10_000_000
    client = Client.create_jupyter_client()
    start = datetime.datetime(2023, 1, 1)
    end = datetime.datetime(2025, 1, 1)
    cache_path = client.transport.cache_path
    compression_level = 15

    # Default location is ~/.cache/tradingstrategy/ethereum-price-tvl-prefiltered.parquet
    combined_output_fname = Path(f"{cache_path}/{chain_id.get_slug()}-price-tvl-prefiltered.parquet")


    # If the pair does not have this liquidity USD ever, skip the trading pair
    # to keep the dataset smaller

    os.makedirs(f"{cache_path}/prefiltered", exist_ok=True)
    #liquidity_output_fname = Path(f"{cache_path}/prefiltered/liquidity-{fname}.parquet")
    #price_output_fname = Path(f"{cache_path}/prefiltered/price-{fname}.parquet")

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

    # We need pair metadata to know which pairs belong to Polygon
    print("Downloading/opening pairs dataset")
    pairs_df = client.fetch_pair_universe().to_pandas()

    pairs_df = filter_pairs_default(
        pairs_df,
        chain_id=chain_id,
        exchange_ids=exchange_ids,
    )

    our_chain_pair_ids = pairs_df["pair_id"].drop_duplicates()

    print(f"We have data for {len(our_chain_pair_ids)} trading pairs")

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
    liquidity_df = pd.concat(liquidity_output_chunks)

    # Resample liquidity to the higher timeframe
    liquidity_df = liquidity_df[["pair_id", "timestamp", "close"]]

    # Crop to range
    liquidity_df = liquidity_df[
        (liquidity_df['timestamp'] >= start) &
        (liquidity_df['timestamp'] <= end)
    ]

    liquidity_df = liquidity_df.drop_duplicates(subset=['pair_id', 'timestamp'], keep='first')
    if time_bucket != liquidity_time_bucket:
        liquidity_df = liquidity_df.groupby('pair_id').apply(lambda x: x.set_index("timestamp").resample(time_bucket.to_frequency()).ffill())
        liquidity_df = liquidity_df.drop(columns=["pair_id"])
    else:
        liquidity_df = liquidity_df.set_index(["pair_id", "timestamp"])

    #                                     close
    # pair_id timestamp
    # 1       2020-05-05 00:00:00  9.890000e-01
    #         2020-05-05 04:00:00  9.890000e-01
    #         2020-05-05 08:00:00  9.890000e-01

    #
    # Find timestamps when the pair exceeds min TVL threshold and can be added to the index
    #

    filtered_df = liquidity_df[liquidity_df['close'] >= min_prefilter_liquidity]

    # Step 2: Group by pair_id and find the first timestamp for each group
    trading_allowed_ats_df = (
        filtered_df
        .reset_index()  # Reset index to access timestamp as a column
        .groupby('pair_id')['timestamp']
        .first()  # Get the first timestamp for each group
        .reset_index()  # Convert to DataFrame
    )

    # Rename columns for clarity
    trading_allowed_ats_df.columns = ['pair_id', 'trading_allowed_at_above_threshold']
    trading_allowed_ats_df = trading_allowed_ats_df.set_index("pair_id")

    # Create pair_id -> timestamp map
    # pair_id
    # 1         2020-05-19
    # 7         2023-11-07
    # 9         2020-06-01
    trading_allowed_ats_series = trading_allowed_ats_df['trading_allowed_at_above_threshold']

    # After we know pair ids that fill the liquidity criteria,
    # we can build OHLCV dataset for these pairs
    print(f"Downloading/opening OHLCV dataset {time_bucket}")
    price_df = client.fetch_all_candles(time_bucket).to_pandas()
    print(f"Filtering out {len(passed_pair_ids)} pairs")
    price_df = price_df.loc[price_df.pair_id.isin(passed_pair_ids)]

    # Crop to range
    price_df = price_df[
        (price_df['timestamp'] >= start) &
        (price_df['timestamp'] <= end)
    ]

    # price_df = price_df.set_index(["pair_id", "timestamp"])

    # Fix price data, forward will sparse OHLCV data
    print("Wrangling price data")
    price_dfgb = price_df.groupby("pair_id")
    price_dfgb = fix_dex_price_data(
        price_dfgb,
        freq=time_bucket.to_frequency(),
        forward_fill_until=end,
    )

    price_df = price_dfgb.obj.set_index(["pair_id", "timestamp"])

    # Merge price and TVL data
    liquidity_df = liquidity_df.rename(columns={'close': 'tvl'})
    merged_df = price_df.join(liquidity_df, how='outer')

    print(f"Merged data contains {len(merged_df):,} rows")

    #
    # Purge data that appears before our trading threshold
    #

    # Reset index to access pair_id and timestamp as columns
    merged_df = merged_df.reset_index()

    # Make sure we do not have any pair OHLCV data until the pair reached trading TVL threshold.
    merged_df['trading_allowed_at'] = merged_df['pair_id'].map(trading_allowed_ats_series)
    merged_df = merged_df[merged_df['timestamp'] >= merged_df['trading_allowed_at']]

    # Will break sklearn fit_transfom()
    del merged_df['trading_allowed_at']

    print(f"After cropping data to TVL threshold, we have {len(merged_df):,} rows")

    # FinRL wants all pair data in equal length.
    # For non-existing data, with set OHLCV zero
    # https://github.com/AI4Finance-Foundation/FinRL/discussions/1314
    merged_df = merged_df.set_index(["pair_id", "timestamp"])
    filled_df = fill_missing_ohlcv(merged_df)

    #                              open  high  low  close  volume  tvl
    # pair_id timestamp
    # 523     2023-01-01 00:00:00   0.0   0.0  0.0    0.0     0.0  0.0
    #         2023-01-01 04:00:00   0.0   0.0  0.0    0.0     0.0  0.0
    #         2023-01-01 08:00:00   0.0   0.0  0.0    0.0     0.0  0.0
    #         2023-01-01 12:00:00   0.0   0.0  0.0    0.0     0.0  0.0
    #         2023-01-01 16:00:00   0.0   0.0  0.0    0.0     0.0  0.0
    merged_df = filled_df

    if merged_df.index.duplicated().any():
        duplicate_rows = merged_df[merged_df.index.duplicated(keep=False)].sort_index()
        display(duplicate_rows)
        assert merged_df.index.duplicated().any(), f"Contains duplicates"

    # These are already in indexes
    merged_df = merged_df.reset_index()

    def _ticker(pair_id):
        pair = pair_universe.get_pair_by_id(pair_id)
        match pair.dex_type:
            case ExchangeType.uniswap_v2:
                dex_type = "v2"
            case ExchangeType.uniswap_v3:
                dex_type = "v3"
            case _:
                raise NotImplementedError(f"Unknown DEX {pair}")

        return f"{pair.get_ticker()}-{dex_type}-{pair.fee}"

    # Add metadata to every row
    pair_universe = PandasPairUniverse(pairs_df)
    merged_df["ticker"] = merged_df["pair_id"].apply(_ticker)
    merged_df["dex"] = merged_df["pair_id"].apply(lambda pair_id: pair_universe.get_pair_by_id(pair_id).dex_type)
    merged_df["fee"] = merged_df["pair_id"].apply(lambda pair_id: pair_universe.get_pair_by_id(pair_id).fee)

    pair_id_unique = merged_df["pair_id"].unique()
    print(f"In the end we have {len(pair_id_unique)} unique pairs")
    print(f"In the end we have {len(merged_df):,} rows")

    print(f"Writing Parquet {combined_output_fname}")
    merged_df.to_parquet(
      combined_output_fname,
      engine='pyarrow',
      compression='zstd',
      compression_level=compression_level,
    )

    print(f"Wrote {combined_output_fname}, {combined_output_fname.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()