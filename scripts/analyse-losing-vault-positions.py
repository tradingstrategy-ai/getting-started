"""Analyse losing vaults from Hyperliquid vault-of-vaults backtest (notebook 33).

Determines which quantitative filters would have caught losing vaults
before allocation, and measures false positive rates against good performers.

Literature-informed filters tested:
- Maximum drawdown (institutional risk metric, Calmar ratio basis)
- Rolling Sharpe minimum (fund-of-funds screening standard)
- TVL decline (on-chain smart money exit signal)
- Volatility spike (regime detection proxy)
- Share price below ATH (momentum decay detection)

Usage::

    poetry run python scripts/analyse-losing-vault-positions.py
"""

import datetime
import warnings

import numpy as np
import pandas as pd

from eth_defi.vault.base import VaultSpec
from eth_defi.vault.vaultdb import DEFAULT_VAULT_DATABASE, DEFAULT_RAW_PRICE_DATABASE
from tradingstrategy.utils.flexible_pickle import flexible_load


HYPERCORE_CHAIN_ID = 9999

BACKTEST_START = datetime.datetime(2025, 3, 1)
BACKTEST_END = datetime.datetime(2026, 3, 11)


# Bottom 10 losing vaults from notebook 33 Trading Pair Breakdown,
# sorted by total return % (worst first)
LOSING_VAULTS = {
    "AnnA": "0x4391c22edeece3a9aa5b8f3c1a3a25378980ff10",
    "OnlyUP": "0x7cd7ea8a61e48fc48f5a18502c0622e53d159347",
    "Satori Quantum HF Vault": "0xbbf7d7a9d0eaeab4115f022a6863450296112422",
    "AceVault Hyper01": "0x9e02aca9865e1859bb7865f6f64801e804a173df",
    "Scott Phillips Trading Vault": "0x1840bdb83caff17de910ec407cafb817678786b5",
    "Ultron": "0x45e7014f092c5f9c39482caec131346f13ac5e73",
    "Aquila Chrysaetos": "0x50e2fe552727a4b8692c192b4f96d1a6b0d44394",
    "Black Ops": "0x49a648936441b22f28f069d3c088928682b277ae",
    "22Cap": "0xba939edf38c0ae0cc689c98b492e0535f43e4550",
    "Edge & Hedge": "0x060d01aa996003b3731a992462d7f0ba68bf3b04",
}

LOSING_ADDRESSES = set(LOSING_VAULTS.values())


# All 52 active Hypercore vault addresses from notebook 33
ALL_VAULT_ADDRESSES = [
    "0x697bc3dd77539fa84156d0e1c95287ea5524fd6b",  # Probot 5/9/12
    "0xe67dbf2d051106b42104c1a6631af5e5a458b682",  # Overdose
    "0x4dec0a851849056e259128464ef28ce78afa27f6",  # pmalt
    "0xfeab64de8cdf9dcebc0f49812499e396273efc06",  # Loop Fund
    "0x8c7bd04cf8d00d68ce8bc7d2f3f02f98d16a5ab0",  # Archangel Quant Fund I
    "0xbbf7d7a9d0eaeab4115f022a6863450296112422",  # Satori Quantum HF Vault
    "0x61b1cf5c2d7c4bf6d5db14f36651b2242e7cba0a",  # OnlyShorts
    "0x2431edfcb662e6ff6deab113cc91878a0b53fb0f",  # Goon Edging
    "0xda51323fe9800c8365646ad5c7ade0dd17fdc167",  # Citadel
    "0x07fd993f0fa3a185f7207adccd29f7a87404689d",  # [ Systemic Strategies ] L/S Grids
    "0x21edf2d791f626ee69352120e7f6e2fbb0f48cf1",  # AILAB TEST URTRA'
    "0x9114a5161f18739ced233190861ea275c8b3a99b",  # Symphony
    "0x82eba5dc675279cb5967952f0c4b5184505eb17c",  # JizzJazz
    "0x1e37a337ed460039d1b15bd3bc489de789768d5e",  # Growi HF
    "0x9a28b01435ca5c4b39a79ae2c27fce01292a7f39",  # ASTEROID
    "0xa844d7ac9fa3424c4fd38a25baa23e460ec3e802",  # 69 Jump Street
    "0x540b6833c05442335aed721af5cadaa6c5b0236a",  # LONG quality - SHORT unlocks
    "0x50e2fe552727a4b8692c192b4f96d1a6b0d44394",  # Aquila Chrysaetos
    "0x241ba250828c6a1289330aeec301e7bdcef31a43",  # -VectorZero-
    "0x8bb033130be354eed1110ce7228d7095f001d9fe",  # HyperNeutral #1
    "0x131ab0c5032079bb9286ffc1828e11d5931e77bb",  # [ Tachyon ] HYPE
    "0x51b62b4bf8df6f2795b3da30cb46aa47f9f230a8",  # Crypto Trading Channel
    "0xba939edf38c0ae0cc689c98b492e0535f43e4550",  # 22Cap
    "0x3b4f22366857da94f9346f88eac84718c8a8d48d",  # Jay Pennies to Jay Dollars
    "0x9e02aca9865e1859bb7865f6f64801e804a173df",  # AceVault Hyper01
    "0xd57c9295947b5a616a3933344ef03a1ad67318ea",  # LowRiskCryptoGainer
    "0x4078582c42fdb547b1397fabb5d5a4beab81be9e",  # Hyperdash Vault #1
    "0xa7f152a5f79bb5483c079610203d8fc03fd77c8e",  # Winwin
    "0x77a0f8bae276f489f0f7cc2752322805317dcbb1",  # R-1
    "0x780825f3f0ad6799e304fb843387934c1fa06e70",  # AILAB TEST ULTRA
    "0x0e008684ae576f280c5426a89d3f5e1da1fc7398",  # Akka Hyper AI
    "0xa0cbceaac4dc736c457b7c340865695e2b3d0fc9",  # 100x
    "0x7cd7ea8a61e48fc48f5a18502c0622e53d159347",  # OnlyUP
    "0x1840bdb83caff17de910ec407cafb817678786b5",  # Scott Phillips Trading Vault
    "0xd914c5164bc253676386269d90dcf56b441cf75b",  # Tortoise Fund
    "0x5ba4c8d16464621608b7333fd44b1e74a1b8d189",  # Liquidar Momentum Vault
    "0xa6a34f0bf2ccea9a1ddf9e9a973f17c498dc5e40",  # FC Genesis - Quantum
    "0x22a60014185f1486afb045219f76e4007fb71e4e",  # Pulse@Evo-α
    "0x45e7014f092c5f9c39482caec131346f13ac5e73",  # Ultron
    "0x4391c22edeece3a9aa5b8f3c1a3a25378980ff10",  # AnnA
    "0xce56eb8261493462e3eb00a72c2bda2cb5fdccee",  # Fund Inception
    "0x060d01aa996003b3731a992462d7f0ba68bf3b04",  # Edge & Hedge
    "0x797327122c5ed1b1530e452b7f8723ba834b4c6a",  # reverse mid curver
    "0x49a648936441b22f28f069d3c088928682b277ae",  # Black Ops
    "0x3f4f05e0fec7b8d6aad2e48ab74f80c8ca77eca3",  # FFLGN
    "0x914434e8a235cb608a94a5f70ab8c40927152a24",  # MC Recovery Fund
    "0x5a733b25a17dc0f26b862ca9e32b439801b1a8c7",  # DailyTradeAI  Low risk (alt addr)
    "0x44ff912d0f88e27419ec0ddc950096609a9b6997",  # DailyTradeAI  Low risk
    "0xc179e03922afe8fa9533d3f896338b9fb87ce0c8",  # drkmttr
    "0x15a141990fc6591838646467273c41c92999772f",  # Tera Liquid
    "0x8b0f84433ca5f287f0f09f84c5a378beb9d11b05",  # Tenety
    "0x4a01f1097a03495ac0054a845c991d9749f81a00",  # FKA - FK Capital Alpha Fund
    "0xfb7b73ff7c93f5552541de37454ffa0f8b76462a",  # Opportunistic Fund 1
]


def load_data():
    """Load vault metadata and price data for Hypercore vaults.

    Returns:
        vault_db: VaultDatabase with vault metadata
        prices_df: DataFrame of hourly price/TVL data filtered to our vaults
    """
    with open(DEFAULT_VAULT_DATABASE, "rb") as f:
        vault_db = flexible_load(f)

    prices_df = pd.read_parquet(DEFAULT_RAW_PRICE_DATABASE)

    # Filter to Hypercore chain and our vault addresses
    prices_df = prices_df[prices_df["chain"] == HYPERCORE_CHAIN_ID]
    prices_df = prices_df[prices_df["address"].isin(ALL_VAULT_ADDRESSES)]

    print(f"Loaded {len(vault_db):,} vaults in metadata database")
    print(f"Loaded {len(prices_df):,} Hypercore price rows for {prices_df['address'].nunique()} vaults")

    return vault_db, prices_df


def get_vault_name(vault_db, address):
    """Look up vault name from the database."""
    spec = VaultSpec(chain_id=HYPERCORE_CHAIN_ID, vault_address=address)
    row = vault_db.rows.get(spec)
    if row:
        return row.get("Name", address[:10])
    return address[:10]


def get_vault_price_series(prices_df, address):
    """Extract daily close share price series for a single vault.

    Resamples hourly data to daily using last observation.

    Returns:
        pd.Series with DatetimeIndex and share price values, or empty Series
    """
    vault_prices = prices_df[prices_df["address"] == address].copy()
    if vault_prices.empty:
        return pd.Series(dtype=float)

    series = vault_prices["share_price"].dropna()
    if series.empty:
        return pd.Series(dtype=float)

    # Resample to daily (last value per day)
    daily = series.resample("1D").last().dropna()
    return daily


def get_vault_tvl_series(prices_df, address):
    """Extract daily TVL series for a single vault.

    Returns:
        pd.Series with DatetimeIndex and TVL (total_assets) values
    """
    vault_prices = prices_df[prices_df["address"] == address].copy()
    if vault_prices.empty:
        return pd.Series(dtype=float)

    series = vault_prices["total_assets"].dropna()
    if series.empty:
        return pd.Series(dtype=float)

    daily = series.resample("1D").last().dropna()
    return daily


def get_vault_flow_series(prices_df, address):
    """Extract daily deposit/withdrawal flow data for a vault.

    Returns:
        tuple of (daily_deposit_usd, daily_withdrawal_usd) as pd.Series
    """
    vault_prices = prices_df[prices_df["address"] == address].copy()
    if vault_prices.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    deposits = vault_prices["daily_deposit_usd"].dropna()
    withdrawals = vault_prices["daily_withdrawal_usd"].dropna()

    if not deposits.empty:
        deposits = deposits.resample("1D").sum()
    if not withdrawals.empty:
        withdrawals = withdrawals.resample("1D").sum()

    return deposits, withdrawals


def calculate_rolling_returns(close, window=60, min_periods=7):
    """Calculate annualised rolling returns.

    Replicates the indicator from notebook 33.
    """
    first_price = close.rolling(
        window=window,
        min_periods=min_periods,
    ).apply(lambda x: x.iloc[0], raw=False)

    actual_days = close.rolling(
        window=window,
        min_periods=min_periods,
    ).apply(lambda x: len(x), raw=True)

    period_return = close / first_price - 1
    annualised = (1 + period_return) ** (365 / actual_days) - 1
    return annualised


def calculate_rolling_volatility(close, window=180, min_periods=14):
    """Calculate annualised rolling volatility.

    Replicates the indicator from notebook 33.
    """
    daily_returns = close.pct_change()
    rolling_std = daily_returns.rolling(
        window=window,
        min_periods=min_periods,
    ).std()
    annualised = rolling_std * (365 ** 0.5)
    return annualised


def calculate_rolling_sharpe(close, window=180, min_periods=14):
    """Calculate rolling Sharpe ratio.

    Replicates the indicator from notebook 33.
    """
    daily_returns = close.pct_change()

    rolling_mean = daily_returns.rolling(
        window=window,
        min_periods=min_periods,
    ).mean()

    rolling_std = daily_returns.rolling(
        window=window,
        min_periods=min_periods,
    ).std()

    sharpe = (rolling_mean * 365) / (rolling_std * (365 ** 0.5))
    return sharpe


def calculate_rolling_sortino(close, window=180, min_periods=14):
    """Calculate rolling Sortino ratio.

    Replicates the indicator from notebook 33.
    """
    daily_returns = close.pct_change()

    rolling_mean = daily_returns.rolling(
        window=window,
        min_periods=min_periods,
    ).mean()

    downside_returns = daily_returns.clip(upper=0)
    rolling_downside_std = downside_returns.rolling(
        window=window,
        min_periods=min_periods,
    ).std()

    sortino = (rolling_mean * 365) / (rolling_downside_std * (365 ** 0.5))
    return sortino


def calculate_max_drawdown_series(close):
    """Calculate running maximum drawdown from peak at each point in time.

    Returns:
        pd.Series of drawdown values (negative, e.g. -0.20 = 20% drawdown)
    """
    cummax = close.cummax()
    drawdown = close / cummax - 1
    return drawdown


def calculate_share_price_vs_ath(close):
    """Calculate share price as a ratio of all-time high at each point.

    Returns:
        pd.Series of values 0-1, where 1.0 = at ATH
    """
    return close / close.cummax()


def calculate_tvl_trend(tvl, window=14):
    """Calculate TVL trend as rolling percentage change over window days."""
    return tvl.pct_change(periods=window)


def build_vault_metrics(prices_df, vault_db, address):
    """Calculate all metrics for a single vault.

    Returns dict with computed indicators and summary statistics.
    """
    name = get_vault_name(vault_db, address)
    close = get_vault_price_series(prices_df, address)
    tvl = get_vault_tvl_series(prices_df, address)
    deposits, withdrawals = get_vault_flow_series(prices_df, address)

    if close.empty or len(close) < 14:
        return {
            "name": name,
            "address": address,
            "data_points": len(close),
            "has_data": False,
        }

    # Compute indicators
    rolling_ret = calculate_rolling_returns(close)
    rolling_vol = calculate_rolling_volatility(close)
    rolling_sh = calculate_rolling_sharpe(close)
    rolling_so = calculate_rolling_sortino(close)
    dd_series = calculate_max_drawdown_series(close)
    price_vs_ath = calculate_share_price_vs_ath(close)
    tvl_trend = calculate_tvl_trend(tvl) if not tvl.empty else pd.Series(dtype=float)

    # Net flows
    net_flow = pd.Series(dtype=float)
    if not deposits.empty and not withdrawals.empty:
        common_idx = deposits.index.intersection(withdrawals.index)
        if len(common_idx) > 0:
            net_flow = deposits.reindex(common_idx).fillna(0) - withdrawals.reindex(common_idx).fillna(0)

    # Summary statistics
    max_dd = dd_series.min() if not dd_series.empty else np.nan
    min_price_vs_ath = price_vs_ath.min() if not price_vs_ath.empty else np.nan
    last_price_vs_ath = price_vs_ath.iloc[-1] if not price_vs_ath.empty else np.nan

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        avg_vol = rolling_vol.mean() if not rolling_vol.dropna().empty else np.nan
        last_vol = rolling_vol.dropna().iloc[-1] if not rolling_vol.dropna().empty else np.nan
        avg_sharpe = rolling_sh.mean() if not rolling_sh.dropna().empty else np.nan
        min_sharpe = rolling_sh.min() if not rolling_sh.dropna().empty else np.nan
        last_sharpe = rolling_sh.dropna().iloc[-1] if not rolling_sh.dropna().empty else np.nan
        avg_sortino = rolling_so.mean() if not rolling_so.dropna().empty else np.nan

    tvl_first = tvl.iloc[0] if not tvl.empty else np.nan
    tvl_last = tvl.iloc[-1] if not tvl.empty else np.nan
    tvl_peak = tvl.max() if not tvl.empty else np.nan
    tvl_change_pct = (tvl_last / tvl_first - 1) if (not np.isnan(tvl_first) and tvl_first > 0) else np.nan
    tvl_min_trend = tvl_trend.min() if not tvl_trend.dropna().empty else np.nan

    total_net_flow = net_flow.sum() if not net_flow.empty else np.nan

    # Overall return
    overall_return = (close.iloc[-1] / close.iloc[0] - 1) if len(close) >= 2 else np.nan

    return {
        "name": name,
        "address": address,
        "has_data": True,
        "data_points": len(close),
        "overall_return": overall_return,
        "max_drawdown": max_dd,
        "avg_volatility": avg_vol,
        "last_volatility": last_vol,
        "avg_sharpe": avg_sharpe,
        "min_sharpe": min_sharpe,
        "last_sharpe": last_sharpe,
        "avg_sortino": avg_sortino,
        "min_price_vs_ath": min_price_vs_ath,
        "last_price_vs_ath": last_price_vs_ath,
        "tvl_first": tvl_first,
        "tvl_last": tvl_last,
        "tvl_peak": tvl_peak,
        "tvl_change_pct": tvl_change_pct,
        "tvl_min_trend_14d": tvl_min_trend,
        "total_net_flow": total_net_flow,
        "close_series": close,
        "tvl_series": tvl,
        "dd_series": dd_series,
        "rolling_sharpe_series": rolling_sh,
        "rolling_vol_series": rolling_vol,
        "price_vs_ath_series": price_vs_ath,
    }


def build_all_vault_metrics(prices_df, vault_db):
    """Build metrics for all vaults in the universe.

    Returns dict mapping address -> metrics dict.
    """
    all_metrics = {}
    for address in ALL_VAULT_ADDRESSES:
        metrics = build_vault_metrics(prices_df, vault_db, address)
        all_metrics[address] = metrics
    return all_metrics


def evaluate_max_drawdown_filter(all_metrics, threshold):
    """Exclude vaults where max drawdown exceeds threshold.

    Args:
        threshold: negative float, e.g. -0.20 means exclude if drawdown > 20%

    Returns:
        (excluded_losers, excluded_winners) sets of addresses
    """
    excluded_losers = set()
    excluded_winners = set()
    for addr, m in all_metrics.items():
        if not m["has_data"]:
            continue
        if m["max_drawdown"] < threshold:
            if addr in LOSING_ADDRESSES:
                excluded_losers.add(addr)
            else:
                excluded_winners.add(addr)
    return excluded_losers, excluded_winners


def evaluate_min_sharpe_filter(all_metrics, min_sharpe):
    """Exclude vaults where average rolling Sharpe is below threshold."""
    excluded_losers = set()
    excluded_winners = set()
    for addr, m in all_metrics.items():
        if not m["has_data"]:
            continue
        if np.isnan(m["avg_sharpe"]) or m["avg_sharpe"] < min_sharpe:
            if addr in LOSING_ADDRESSES:
                excluded_losers.add(addr)
            else:
                excluded_winners.add(addr)
    return excluded_losers, excluded_winners


def evaluate_tvl_decline_filter(all_metrics, decline_threshold):
    """Exclude vaults where worst 14-day TVL decline exceeds threshold.

    Args:
        decline_threshold: negative float, e.g. -0.20 means exclude if TVL dropped > 20%
    """
    excluded_losers = set()
    excluded_winners = set()
    for addr, m in all_metrics.items():
        if not m["has_data"]:
            continue
        min_trend = m["tvl_min_trend_14d"]
        if not np.isnan(min_trend) and min_trend < decline_threshold:
            if addr in LOSING_ADDRESSES:
                excluded_losers.add(addr)
            else:
                excluded_winners.add(addr)
    return excluded_losers, excluded_winners


def evaluate_volatility_filter(all_metrics, max_volatility):
    """Exclude vaults where average annualised volatility exceeds threshold."""
    excluded_losers = set()
    excluded_winners = set()
    for addr, m in all_metrics.items():
        if not m["has_data"]:
            continue
        if not np.isnan(m["avg_volatility"]) and m["avg_volatility"] > max_volatility:
            if addr in LOSING_ADDRESSES:
                excluded_losers.add(addr)
            else:
                excluded_winners.add(addr)
    return excluded_losers, excluded_winners


def evaluate_price_vs_ath_filter(all_metrics, min_pct_of_ath):
    """Exclude vaults where share price ever dropped below X% of ATH."""
    excluded_losers = set()
    excluded_winners = set()
    for addr, m in all_metrics.items():
        if not m["has_data"]:
            continue
        if not np.isnan(m["min_price_vs_ath"]) and m["min_price_vs_ath"] < min_pct_of_ath:
            if addr in LOSING_ADDRESSES:
                excluded_losers.add(addr)
            else:
                excluded_winners.add(addr)
    return excluded_losers, excluded_winners


def display_losing_vault_summary(all_metrics, vault_db):
    """Display summary table of all losing vault metrics."""
    rows = []
    for name, address in LOSING_VAULTS.items():
        m = all_metrics.get(address, {})
        if not m.get("has_data"):
            rows.append({
                "Vault": name,
                "Address": address[:10] + "...",
                "Data": "No data",
            })
            continue

        rows.append({
            "Vault": name,
            "Address": address[:10] + "...",
            "Overall return": f"{m['overall_return']:.1%}" if not np.isnan(m['overall_return']) else "N/A",
            "Max drawdown": f"{m['max_drawdown']:.1%}" if not np.isnan(m['max_drawdown']) else "N/A",
            "Avg volatility": f"{m['avg_volatility']:.0%}" if not np.isnan(m['avg_volatility']) else "N/A",
            "Avg Sharpe": f"{m['avg_sharpe']:.2f}" if not np.isnan(m['avg_sharpe']) else "N/A",
            "Min Sharpe": f"{m['min_sharpe']:.2f}" if not np.isnan(m['min_sharpe']) else "N/A",
            "TVL last": f"${m['tvl_last']:,.0f}" if not np.isnan(m['tvl_last']) else "N/A",
            "TVL change": f"{m['tvl_change_pct']:.0%}" if not np.isnan(m['tvl_change_pct']) else "N/A",
            "Min price/ATH": f"{m['min_price_vs_ath']:.1%}" if not np.isnan(m['min_price_vs_ath']) else "N/A",
            "Net flow": f"${m['total_net_flow']:,.0f}" if not np.isnan(m['total_net_flow']) else "N/A",
        })

    df = pd.DataFrame(rows)
    return df


def display_winning_vault_summary(all_metrics, vault_db):
    """Display summary table of winning vault metrics for comparison."""
    rows = []
    for addr, m in all_metrics.items():
        if addr in LOSING_ADDRESSES:
            continue
        if not m.get("has_data"):
            continue

        rows.append({
            "Vault": m["name"],
            "Address": addr[:10] + "...",
            "Overall return": m["overall_return"],
            "Max drawdown": m["max_drawdown"],
            "Avg volatility": m["avg_volatility"],
            "Avg Sharpe": m["avg_sharpe"],
            "Min Sharpe": m["min_sharpe"],
            "TVL last": m["tvl_last"],
            "TVL change": m["tvl_change_pct"],
            "Min price/ATH": m["min_price_vs_ath"],
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Overall return", ascending=False)
    return df


def run_filter_evaluation(all_metrics):
    """Evaluate all candidate filters and return results table."""
    total_losers = len(LOSING_ADDRESSES)
    total_winners = sum(
        1 for addr, m in all_metrics.items()
        if addr not in LOSING_ADDRESSES and m.get("has_data")
    )

    results = []

    # 1. Maximum drawdown filter
    for threshold in [-0.05, -0.10, -0.15, -0.20, -0.25, -0.30]:
        exc_l, exc_w = evaluate_max_drawdown_filter(all_metrics, threshold)
        results.append({
            "Filter": "Max drawdown",
            "Threshold": f"{threshold:.0%}",
            "Losers caught": len(exc_l),
            "Losers caught %": f"{len(exc_l)/total_losers:.0%}",
            "Winners excluded": len(exc_w),
            "Winners excluded %": f"{len(exc_w)/total_winners:.0%}" if total_winners > 0 else "N/A",
            "Precision": f"{len(exc_l)/(len(exc_l)+len(exc_w)):.0%}" if (len(exc_l)+len(exc_w)) > 0 else "N/A",
        })

    # 2. Rolling Sharpe minimum
    for min_sh in [0.0, 0.5, 1.0, 1.5, 2.0]:
        exc_l, exc_w = evaluate_min_sharpe_filter(all_metrics, min_sh)
        results.append({
            "Filter": "Min avg Sharpe",
            "Threshold": f"{min_sh:.1f}",
            "Losers caught": len(exc_l),
            "Losers caught %": f"{len(exc_l)/total_losers:.0%}",
            "Winners excluded": len(exc_w),
            "Winners excluded %": f"{len(exc_w)/total_winners:.0%}" if total_winners > 0 else "N/A",
            "Precision": f"{len(exc_l)/(len(exc_l)+len(exc_w)):.0%}" if (len(exc_l)+len(exc_w)) > 0 else "N/A",
        })

    # 3. TVL decline filter
    for decline in [-0.10, -0.20, -0.30, -0.50, -0.70]:
        exc_l, exc_w = evaluate_tvl_decline_filter(all_metrics, decline)
        results.append({
            "Filter": "TVL decline 14d",
            "Threshold": f"{decline:.0%}",
            "Losers caught": len(exc_l),
            "Losers caught %": f"{len(exc_l)/total_losers:.0%}",
            "Winners excluded": len(exc_w),
            "Winners excluded %": f"{len(exc_w)/total_winners:.0%}" if total_winners > 0 else "N/A",
            "Precision": f"{len(exc_l)/(len(exc_l)+len(exc_w)):.0%}" if (len(exc_l)+len(exc_w)) > 0 else "N/A",
        })

    # 4. Volatility spike filter
    for max_vol in [0.50, 0.75, 1.00, 1.50, 2.00]:
        exc_l, exc_w = evaluate_volatility_filter(all_metrics, max_vol)
        results.append({
            "Filter": "Max avg volatility",
            "Threshold": f"{max_vol:.0%}",
            "Losers caught": len(exc_l),
            "Losers caught %": f"{len(exc_l)/total_losers:.0%}",
            "Winners excluded": len(exc_w),
            "Winners excluded %": f"{len(exc_w)/total_winners:.0%}" if total_winners > 0 else "N/A",
            "Precision": f"{len(exc_l)/(len(exc_l)+len(exc_w)):.0%}" if (len(exc_l)+len(exc_w)) > 0 else "N/A",
        })

    # 5. Share price below ATH filter
    for min_pct in [0.70, 0.80, 0.85, 0.90, 0.95]:
        exc_l, exc_w = evaluate_price_vs_ath_filter(all_metrics, min_pct)
        results.append({
            "Filter": "Min price/ATH",
            "Threshold": f"{min_pct:.0%}",
            "Losers caught": len(exc_l),
            "Losers caught %": f"{len(exc_l)/total_losers:.0%}",
            "Winners excluded": len(exc_w),
            "Winners excluded %": f"{len(exc_w)/total_winners:.0%}" if total_winners > 0 else "N/A",
            "Precision": f"{len(exc_l)/(len(exc_l)+len(exc_w)):.0%}" if (len(exc_l)+len(exc_w)) > 0 else "N/A",
        })

    return pd.DataFrame(results)


def main():
    print("Analyse losing vault positions from Hyperliquid vault-of-vaults backtest")
    print("=" * 80)
    print(f"Backtest period: {BACKTEST_START.date()} to {BACKTEST_END.date()}")
    print(f"Losing vaults: {len(LOSING_VAULTS)}")
    print(f"Total universe: {len(ALL_VAULT_ADDRESSES)} vaults")
    print()

    # Load data
    vault_db, prices_df = load_data()
    print()

    # Build metrics for all vaults
    print("Calculating metrics for all vaults...")
    all_metrics = build_all_vault_metrics(prices_df, vault_db)

    vaults_with_data = sum(1 for m in all_metrics.values() if m.get("has_data"))
    print(f"Vaults with sufficient data: {vaults_with_data}/{len(ALL_VAULT_ADDRESSES)}")
    print()

    # Display losing vault summary
    print("=" * 80)
    print("LOSING VAULT METRICS SUMMARY")
    print("=" * 80)
    losing_df = display_losing_vault_summary(all_metrics, vault_db)
    with pd.option_context("display.max_columns", None, "display.width", 220, "display.max_colwidth", 25):
        print(losing_df.to_string(index=False))
    print()

    # Display winning vault summary for comparison
    print("=" * 80)
    print("WINNING VAULT METRICS SUMMARY (for false positive comparison)")
    print("=" * 80)
    winning_df = display_winning_vault_summary(all_metrics, vault_db)
    if not winning_df.empty:
        fmt_df = winning_df.copy()
        for col in ["Overall return", "Max drawdown", "Avg volatility", "TVL change", "Min price/ATH"]:
            if col in fmt_df.columns:
                fmt_df[col] = fmt_df[col].apply(lambda x: f"{x:.1%}" if not np.isnan(x) else "N/A")
        for col in ["Avg Sharpe", "Min Sharpe"]:
            if col in fmt_df.columns:
                fmt_df[col] = fmt_df[col].apply(lambda x: f"{x:.2f}" if not np.isnan(x) else "N/A")
        if "TVL last" in fmt_df.columns:
            fmt_df["TVL last"] = fmt_df["TVL last"].apply(lambda x: f"${x:,.0f}" if not np.isnan(x) else "N/A")
        with pd.option_context("display.max_columns", None, "display.width", 220, "display.max_colwidth", 25):
            print(fmt_df.to_string(index=False))
    print()

    # Run filter evaluation
    print("=" * 80)
    print("FILTER EVALUATION")
    print("=" * 80)
    print()
    print("For each filter and threshold, shows how many of the 10 losers would be")
    print("excluded (recall) and how many winners would be incorrectly excluded (false positives).")
    print("Precision = losers caught / (losers caught + winners excluded).")
    print()

    filter_df = run_filter_evaluation(all_metrics)

    # Display by filter type
    for filter_name in filter_df["Filter"].unique():
        subset = filter_df[filter_df["Filter"] == filter_name]
        print(f"\n{filter_name}:")
        print("-" * 80)
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(subset.to_string(index=False))
        print()

    # Summary: best threshold per filter
    print("=" * 80)
    print("RECOMMENDED FILTERS")
    print("=" * 80)
    print()
    print("Based on the analysis, potential filters to add to the strategy:")
    print()
    print("Quantitative filters that catch losing vaults while minimising false positives:")
    print()

    # Find best threshold per filter (highest losers caught with lowest winners excluded)
    for filter_name in filter_df["Filter"].unique():
        subset = filter_df[filter_df["Filter"] == filter_name].copy()
        # Score: losers caught - 2 * winners excluded (penalise false positives)
        subset = subset.copy()
        subset["score"] = subset["Losers caught"] - 2 * subset["Winners excluded"]
        best = subset.loc[subset["score"].idxmax()]
        print(f"  {filter_name} at {best['Threshold']}: "
              f"catches {best['Losers caught']}/10 losers, "
              f"excludes {best['Winners excluded']} winners "
              f"(precision {best['Precision']})")

    # Key findings analysis
    print()
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    print()

    # Classify all vaults by overall return
    losers_positive_overall = []
    losers_negative_overall = []
    for name, addr in LOSING_VAULTS.items():
        m = all_metrics.get(addr, {})
        if m.get("has_data") and not np.isnan(m.get("overall_return", np.nan)):
            if m["overall_return"] > 0:
                losers_positive_overall.append((name, m["overall_return"]))
            else:
                losers_negative_overall.append((name, m["overall_return"]))

    winners_negative_overall = []
    winners_positive_overall = []
    for addr, m in all_metrics.items():
        if addr in LOSING_ADDRESSES or not m.get("has_data"):
            continue
        if not np.isnan(m.get("overall_return", np.nan)):
            if m["overall_return"] < 0:
                winners_negative_overall.append((m["name"], m["overall_return"]))
            else:
                winners_positive_overall.append((m["name"], m["overall_return"]))

    print("1. BACKTEST PnL vs OVERALL VAULT RETURN:")
    print()
    print(f"   Of the 10 backtest losers:")
    print(f"     {len(losers_negative_overall)} have negative overall returns (genuinely bad vaults)")
    for name, ret in sorted(losers_negative_overall, key=lambda x: x[1]):
        print(f"       - {name}: {ret:.1%}")
    print(f"     {len(losers_positive_overall)} have positive overall returns (bad timing by strategy)")
    for name, ret in sorted(losers_positive_overall, key=lambda x: x[1], reverse=True):
        print(f"       - {name}: {ret:.1%}")
    print()
    print(f"   Of the {len(winners_negative_overall) + len(winners_positive_overall)} backtest winners:")
    print(f"     {len(winners_negative_overall)} have negative overall returns (alpha model timed entries well)")
    print(f"     {len(winners_positive_overall)} have positive overall returns")
    print()

    print("2. FILTER IMPLICATIONS:")
    print()
    print("   Static universe filters (applied once) have high false positive rates because")
    print("   the alpha model already handles timing well — many 'bad' vaults are profitable")
    print("   when entered at the right time.")
    print()
    print("   More effective approach: DYNAMIC filters applied at each rebalance cycle:")
    print("   - Rolling Sharpe < 0 at entry → skip vault for this cycle")
    print("   - Current drawdown from peak > 20% → skip vault for this cycle")
    print("   - 14-day TVL decline > 20% → skip vault for this cycle")
    print("   - Current annualised volatility > 200% AND TVL < $1M → skip (already partially implemented)")
    print()
    print("   These are evaluated at the MOMENT of allocation, not as universe filters.")
    print()

    print("3. LITERATURE-INFORMED RECOMMENDATIONS:")
    print()
    print("   a) Drawdown-based exit trigger (momentum decay detection):")
    print("      If vault share price drops >15% from recent peak, close position early.")
    print("      Academic research shows strategy Sharpe decays ~50% post-publication;")
    print("      drawdown triggers catch this decay in real-time.")
    print()
    print("   b) Rolling Sharpe gate (fund-of-funds standard):")
    print("      Only enter vaults with rolling 30-day Sharpe > 0.")
    print("      The existing rolling_sharpe/sortino weighting methods partially do this,")
    print("      but a hard minimum would prevent entries during decay periods.")
    print()
    print("   c) TVL flow confirmation (DeFi-specific signal):")
    print("      Require stable or growing TVL before entry.")
    print("      Declining TVL signals smart money exiting — a leading indicator.")
    print()
    print("   d) Volatility regime filter (crypto market research):")
    print("      During high-volatility regimes (vault vol > 2x average),")
    print("      reduce allocation or skip entirely.")
    print()


if __name__ == "__main__":
    main()
