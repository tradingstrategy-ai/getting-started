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
CACHE_DIRECTORY = f'~/.cache/trading-strategy/binance-all-spot-candles-{TIME_BUCKET.value}'

def fetch_binance_candles_for_all_pairs(
    time_bucket: TimeBucket,
    cache_directory=CACHE_DIRECTORY, 
) -> None:
    """Downloads all Binance spot pairs and saves them as parquet separate files.
    It is highly recommended to use a different cache directory for each time bucket.
    
    :param time_bucket: Time bucket for the candles.
    :param cache_directory: Directory to store the parquet files.
    :return: None
    """
    cache_directory = Path(os.path.expanduser(cache_directory))
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
    """Read all parquet files in the cache directory as a single dataframe. 
    
    :param cache_directory: Directory where the parquet files are stored.
    :param time_bucket: Time bucket for the candles.
    :param write: If true, combine parquet files into a single parquet file.
    :param file_name: Name of the parquet file to write.
    """
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