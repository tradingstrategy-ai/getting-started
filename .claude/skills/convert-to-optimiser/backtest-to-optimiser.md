# Backtest to optimiser notebook mapping

Reference notebooks (in `getting-started/scratchpad/bnb-ath-2/`):
- Backtest: `11-bnb-ath-2h-rerun.ipynb`
- Optimiser: `10-bnb-ath-optimise-sharpe.ipynb`

## What stays the same

These cells are copied verbatim from the backtest notebook:

- **Setup cell**: `Client.create_jupyter_client()` + `setup_charting_and_output()`
- **Chain config cell**: Exchange/pair/vault configuration
- **Trading universe cell**: `create_trading_universe()` function
- **Token map cell**: `token_map`, `benchmark_pair_ids`, `category_pair_ids`
- **Indicators cell**: All indicator functions (`local_high`, `full_history_ath`, `volatility`, `signal`, etc.) — but see "Remove inline indicator calculation" below
- **Backtest time range cell**: Start/end date calculation — but see "Fix indicator_data references" below
- **`decide_trades()` function**: Core strategy logic (but separated from `run_backtest_inline` call) — but see "numpy.float64 cast" below

## What changes

### 1. Title cell

- Backtest: `# BNB local high strategy` with description
- Optimiser: `# {Strategy name} parameter search`

### 2. Parameters cell

Add import:
```python
from skopt.space import Categorical
```

Wrap tuneable strategy parameters in `Categorical([...])`. The original value must be included in the list. Example:

```python
# Backtest (fixed)
local_high_delay_bars = 12
local_high_window_bars = 2160

# Optimiser (searchable)
local_high_delay_bars = Categorical([12, 60, 144, 200, 360, 500])
local_high_window_bars = Categorical([10, 25, 50, 100, 150, 360, 800, 720, 2160, 4320])
```

Other changes:
- Set `use_managed_yield = False`
- Add at end: `display_parameters(parameters)` (with import `from tradeexecutor.strategy.parameters import display_parameters`)

Parameters that are **not searchable** (structural):
- `id`, `candle_time_bucket`, `cycle_duration`, `chain_id`, `exchanges`
- `rolling_volume_bars`, `rolling_volatility_bars`, `tvl_ewm_span`
- `min_volume`, `min_tvl`, `min_tvl_prefilter`, `min_token_sniffer_score`
- `routing`, `required_history_period`, `slippage_tolerance`
- `backtest_start`, `backtest_end`, `initial_cash`
- `yield_flow_dust_threshold`, `directional_trade_yield_buffer_pct`
- `assummed_liquidity_when_data_missings`

Parameters typically made searchable:
- Signal/indicator parameters (delay, window, threshold, span)
- Portfolio sizing parameters (max_assets, allocation, max_concentration)
- Risk parameters (stop_loss, per_position_cap)
- Filter thresholds (min_from_full_history_ath)

### 3. Remove inline indicator calculation

The backtest indicators cell typically ends with:
```python
indicator_data = calculate_and_load_indicators_inline(
    strategy_universe=strategy_universe,
    create_indicators=indicators.create_indicators,
    parameters=parameters,
)
```

**Remove this call** (and any preceding comment like `# Calculate all indicators...`). The optimiser calculates indicators for each parameter combination internally. Passing `Categorical` parameter values to `calculate_and_load_indicators_inline()` causes:
```
AssertionError: Detected scikit-optimize Dimension as a parameter value: rolling_returns_bars: Categorical(...)
```

Keep `display_indicators(indicators)` if present — it only describes the indicator definitions, it does not calculate them.

### 4. Fix indicator_data references in time range cell

The backtest time range cell may reference `indicator_data` (e.g. `indicator_data.get_indicator_series(...)`). Since `indicator_data` no longer exists after step 3, simplify the cell to use static `Parameters` values:
```python
backtest_start = Parameters.backtest_start
backtest_end = Parameters.backtest_end
print(f"Time range is {backtest_start} - {backtest_end}")
```

### 5. Remove charts cell and pre-backtest visualisations

The backtest notebook has:
- Charts cell: `ChartRegistry` setup with 20+ chart registrations
- Pre-backtest visualisation cells: available pairs, inclusion criteria, signals, volatility, price vs signal, local high

All of these are **removed** from the optimiser notebook.

### 6. Replace `run_backtest_inline` with `perform_optimisation`

The backtest runs a single backtest:
```python
result = run_backtest_inline(
    name=parameters.id,
    engine_version="0.5",
    decide_trades=decide_trades,
    ...
)
state = result.state
```

The optimiser replaces this with:
```python
from tradeexecutor.backtest.optimiser import perform_optimisation, prepare_optimiser_parameters, MinTradeCountFilter
from tradeexecutor.backtest.optimiser_functions import optimise_sharpe

iterations = 4
search_func = optimise_sharpe

optimiser_result = perform_optimisation(
    iterations=iterations,
    search_func=search_func,
    decide_trades=decide_trades,
    strategy_universe=strategy_universe,
    parameters=prepare_optimiser_parameters(Parameters),
    create_indicators=indicators.create_indicators,
    result_filter=MinTradeCountFilter(50),
    timeout=70*60,
    batch_size=5,
    ignore_wallet_errors=True,
)
```

### 7. Cast numpy.float64 to float in decide_trades

scikit-optimize's `Categorical` returns `numpy.float64` for float values, not native Python `float`. The `alpha_model.normalise_weights()` waterfall code path has a strict type check:
```python
assert type(max_weight) == float, f"Got {type(max_weight)} instead of float"
```

If `decide_trades()` passes a Categorical float parameter (e.g. `parameters.max_concentration`) as `max_weight`, wrap it with `float()`:
```python
# Before (crashes with numpy.float64)
max_weight = parameters.max_concentration

# After
max_weight = float(parameters.max_concentration)
```

Apply the same `float()` cast to any parameter value passed to functions that assert native Python types. Common cases: `max_weight`, `per_position_cap`, `allocation`.

### 8. Replace backtest output cells with optimiser analysis cells

All backtest output cells (performance metrics, equity curves, weights, positions, trading metrics, vault performance) are **removed**.

Replaced with these heading + code cell pairs (copied from reference optimiser notebook cells 18-48):

| # | Heading | Description |
|---|---------|-------------|
| 1 | `# Optimiser` | `perform_optimisation()` call |
| 2 | `# Results` | `analyse_optimiser_result()` + `render_grid_search_result_table()` |
| 3 | `# Parameter analysis` | Section heading only |
| 4 | `## Decision tree visualisation` | sklearn `DecisionTreeRegressor` on parameter combinations |
| 5 | `## Feature importance analysis` | sklearn `RandomForestRegressor` feature importances |
| 6 | `## Heatmaps for parameter pairs` | plotly `go.Heatmap` for parameter pair interactions |
| 7 | `## Cluster analysis` | sklearn `KMeans` + PCA 3D scatter |
| 8 | `## Parallel coordinates plot` | plotly `px.parallel_coordinates` |
| 9 | `# The best candidate equity curve` | `visualise_single_grid_search_result_benchmark()` |
| 10 | `# Portfolio performance (best pick)` | `compare_strategy_backtest_to_multiple_assets()` |
| 11 | `# Trade summary (best pick)` | `best_pick.summary.to_dataframe()` |
| 12 | `# Trading pair performance breakdown` | `analyse_multipair()` |
| 13 | `# Best positions` | Top 5 positions sorted by profit |
| 14 | `# Rolling sharpe` | `calculate_rolling_sharpe()` with 180-day window |
| 15 | `# Data diagnostics` | Commented-out debug cells |
