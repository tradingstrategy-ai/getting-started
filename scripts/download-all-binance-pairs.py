"""Download all binance spot pairs and save them as separate parquet files.
When reading the parquet files, combine them into a single dataframe.
"""

from tradingstrategy.binance.downloader import BinanceDownloader
from tradingstrategy.timebucket import TimeBucket
from pathlib import Path
import os
import pyarrow.parquet as pq
import pandas as pd

TIME_BUCKET = TimeBucket.d1
CACHE_DIRECTORY = Path(os.path.expanduser(f'~/.cache/trading-strategy/binance-all-spot-candles-{TIME_BUCKET.value}'))

def fetch_binance_candles_for_all_pairs(
    time_bucket: TimeBucket,
    cache_directory=CACHE_DIRECTORY, 
):
    print(f"Downloading all Binance spot pairs with a time bucket of {time_bucket.value}")
    x = BinanceDownloader(cache_directory=cache_directory)
    assert isinstance(time_bucket, TimeBucket)

    assets = x.fetch_all_spot_symbols()
    spot_symbols = list(assets)
    
    for i, symbol in enumerate(spot_symbols):
        df = x.fetch_candlestick_data(symbol, time_bucket=time_bucket)
    
    print("finished downloading all spot pairs")

    return df


def read_all_parquet_files(
    cache_directory=CACHE_DIRECTORY,
    time_bucket=TIME_BUCKET, 
    write=False, 
    file_name='all_spot_pairs.parquet'
):
    print("Loading all parquet files")
    parquet_files = [f for f in os.listdir(cache_directory) if f.endswith('.parquet')]
    dataframes = []
    
    for file in parquet_files:
        if not time_bucket in file:
            print("Warning: Skipping file that does not match the time bucket")
            continue

        file_path = os.path.join(cache_directory, file)
        df = pq.read_table(file_path).to_pandas()
        dataframes.append(df)
    
    combined_df = pd.concat(dataframes, ignore_index=True)

    if write:
        assert file_name, 'Please provide a file name'
        combined_df.to_parquet(file_name)
        print("Combined dataframes written to parquet file")

    return combined_df

fetch_binance_candles_for_all_pairs(
    time_bucket=TIME_BUCKET,
    cache_directory=CACHE_DIRECTORY,
)

read_all_parquet_files(write=True)