---
name: convert-to-optimiser
description: Convert a backtesting notebook to a parameter optimisation notebook and use the bundled transformation mapping to choose searchable parameters and rewrite the notebook.
---

# Convert backtest to optimiser

Convert a single backtesting notebook into an optimiser notebook that optimises strategy parameters using scikit-optimize's Gaussian Process.

## Input

- Path to a backtesting notebook (.ipynb)

## Reference files

- Reference optimiser notebook: `getting-started/scratchpad/vault-of-vaults/32-waterfall-diversified-larger-universe-grid-search-4d-rebalance-profit.ipynb`
- Reference backtest notebook: `getting-started/scratchpad/bnb-ath-2/11-bnb-ath-2h-rerun.ipynb`

## Steps

1. **Read the input backtest notebook** and the cell-by-cell mapping section below.

2. **Read the reference optimiser notebook** (`getting-started/scratchpad/vault-of-vaults/32-waterfall-diversified-larger-universe-grid-search-4d-rebalance-profit.ipynb`) — you will copy output cells from this.

3. **Identify tuneable parameters**: Look at the `Parameters` class in the backtest notebook. Identify strategy-specific parameters that could be searched (signal/indicator params, portfolio sizing, risk params). Exclude structural parameters like `chain_id`, `exchanges`, `candle_time_bucket`, `cycle_duration`, `routing`, `backtest_start/end`, `initial_cash`, `min_volume`, `min_tvl`, rolling window calculations, and yield settings.

4. **Ask the user** which parameters to make searchable and what value ranges to use. Suggest ranges centred on the current fixed values. The original value must be included in every range.

5. **Create the optimiser notebook** with these cells in order:

   a. **Title cell** (markdown): Change title to `# {Strategy name} parameter search`

   b. **Setup cell** (code): Copy as-is from backtest

   c. **Chain config cell** (code): Copy as-is from backtest

   d. **Parameters cell** (code): Transform from the backtest version:
      - Add `from skopt.space import Categorical` to imports
      - Replace chosen tuneable parameters with `Categorical([...])` ranges
      - Set `use_managed_yield = False`
      - Add at the end:
        ```python
        from tradeexecutor.strategy.parameters import display_parameters
        display_parameters(parameters)
        ```

   e. **Trading universe cell** (code): Copy as-is from backtest (the `create_trading_universe()` function)

   f. **Token map cell** (code): Copy as-is from backtest

   g. **Indicators cell** (code): Copy from backtest but **remove the `calculate_and_load_indicators_inline()` call** at the end of the cell (and its preceding comment). Keep `display_indicators(indicators)` if present. The optimiser calculates indicators itself for each parameter combination — calling `calculate_and_load_indicators_inline()` with Categorical parameter values will crash with `AssertionError: Detected scikit-optimize Dimension as a parameter value`.

   h. **Backtest time range cell** (markdown + code): Copy from backtest, but **remove any reference to `indicator_data`** since that variable no longer exists (the inline indicator calculation was removed in step g). Simplify to use `Parameters.backtest_start` and `Parameters.backtest_end` directly. Example:
      ```python
      backtest_start = Parameters.backtest_start
      backtest_end = Parameters.backtest_end
      print(f"Time range is {backtest_start} - {backtest_end}")
      ```

   i. **Strategy cell** (code): Copy `decide_trades()` (and `create_yield_rules()` if present) from the backtest. **Important**: If `run_backtest_inline()` is in the same cell as `decide_trades()`, remove the `run_backtest_inline()` call and everything after it. The strategy function must be in its own cell without the backtest execution.

      **numpy.float64 fix**: scikit-optimize's `Categorical` returns `numpy.float64` instead of native Python `float`. If `decide_trades()` passes any Categorical float parameter to `alpha_model.normalise_weights()` as `max_weight`, the waterfall code path will crash with `AssertionError: Got <class 'numpy.float64'> instead of float`. Wrap such values with `float()`. For example, change:
      ```python
      max_weight = parameters.max_concentration
      ```
      to:
      ```python
      max_weight = float(parameters.max_concentration)
      ```
      Apply the same `float()` cast to any other parameter value that ends up passed to a function expecting a native Python `float` (common with `max_weight`, `per_position_cap`, etc.).

   j. **Optimiser and output cells**: Copy cells from the reference optimiser notebook (`32-waterfall-diversified-larger-universe-grid-search-4d-rebalance-profit.ipynb`). These are heading + code cell pairs:

      | Heading | Cells |
      |---------|-------|
      | `# Optimiser` | markdown + code |
      | `# Results` | markdown + code |
      | `## Equity curves` | markdown + code |
      | `# Parameter analysis` | markdown only |
      | `## Decision tree visualisation` | markdown + code |
      | `## Feature importance analysis` | markdown + code |
      | `## Heatmaps for parameter pairs` | markdown + code |
      | `## Cluster analysis` | markdown + code |
      | `## Parallel coordinates plot` | markdown + code |
      | `# The best candidate equity curve` | markdown + code |
      | `# Portfolio performance (best pick)` | markdown + code |
      | `# Trade summary (best pick)` | markdown + code |
      | `# Trading pair performance breakdown` | markdown + code |
      | `# Best positions` | markdown + code |
      | `# Rolling sharpe` | markdown + code |
      | `# Data diagnostics` | markdown + 3 code cells |

      **Equity curves cell**: The `## Equity curves` code cell overlays all optimiser results on a single chart with buy-and-hold benchmarks. It must extract `GridSearchResult` instances from the optimiser results and pass them to `visualise_grid_search_equity_curves`. Use `group_by` and `group_by_secondary` to colour and style curves by parameter values — pick two of the searchable `Categorical` parameters from the strategy's `Parameters` class:
      ```python
      from tradeexecutor.visual.grid_search_basic import visualise_grid_search_equity_curves
      from tradeexecutor.analysis.multi_asset_benchmark import get_benchmark_data

      benchmark_indexes = get_benchmark_data(
          strategy_universe,
          cumulative_with_initial_cash=Parameters.initial_cash,
      )

      grid_search_results = [r.result for r in optimiser_result.results if not r.filtered]

      fig = visualise_grid_search_equity_curves(
          grid_search_results,
          benchmark_indexes=benchmark_indexes,
          log_y=False,
          group_by="<primary_categorical_param>",       # colour family per value
          group_by_secondary="<secondary_categorical_param>",  # dash style per value
      )
      fig.show()
      ```

   **Do not** copy any cells from the backtest that are not listed above (no chart registry, no pre-backtest visualisations, no single-backtest output cells like equity curves, weight charts, positions, trading metrics, vault performance).

6. **Write the output notebook** as `{original-notebook-name}-optimiser.ipynb` in the same directory as the input notebook.

7. **Verify** the notebook structure:
   - Parameters class has `Categorical` values for the chosen searchable params
   - `create_trading_universe()` and `decide_trades()` are unchanged from the backtest
   - Optimiser cell uses `perform_optimisation` with `prepare_optimiser_parameters(Parameters)`
   - All output cells match the reference optimiser structure
   - Test run: `poetry run jupyter execute {output-notebook}.ipynb --inplace --timeout=-1`

## Cell-by-cell mapping

Reference notebooks (in `getting-started/scratchpad/bnb-ath-2/`):
- Backtest: `11-bnb-ath-2h-rerun.ipynb`
- Optimiser: `10-bnb-ath-optimise-sharpe.ipynb`

### What stays the same

These cells are copied verbatim from the backtest notebook:

- **Setup cell**: `Client.create_jupyter_client()` + `setup_charting_and_output()`
- **Chain config cell**: Exchange/pair/vault configuration
- **Trading universe cell**: `create_trading_universe()` function
- **Token map cell**: `token_map`, `benchmark_pair_ids`, `category_pair_ids`
- **Indicators cell**: All indicator functions (`local_high`, `full_history_ath`, `volatility`, `signal`, etc.) — but see "Remove inline indicator calculation" below
- **Backtest time range cell**: Start/end date calculation — but see "Fix indicator_data references" below
- **`decide_trades()` function**: Core strategy logic (but separated from `run_backtest_inline` call) — but see "numpy.float64 cast" below

### What changes

#### 1. Title cell

- Backtest: `# BNB local high strategy` with description
- Optimiser: `# {Strategy name} parameter search`

#### 2. Parameters cell

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

#### 3. Remove inline indicator calculation

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

#### 4. Fix indicator_data references in time range cell

The backtest time range cell may reference `indicator_data` (e.g. `indicator_data.get_indicator_series(...)`). Since `indicator_data` no longer exists after step 3, simplify the cell to use static `Parameters` values:
```python
backtest_start = Parameters.backtest_start
backtest_end = Parameters.backtest_end
print(f"Time range is {backtest_start} - {backtest_end}")
```

#### 5. Remove charts cell and pre-backtest visualisations

The backtest notebook has:
- Charts cell: `ChartRegistry` setup with 20+ chart registrations
- Pre-backtest visualisation cells: available pairs, inclusion criteria, signals, volatility, price vs signal, local high

All of these are **removed** from the optimiser notebook.

#### 6. Replace `run_backtest_inline` with `perform_optimisation`

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

#### 7. Cast numpy.float64 to float in decide_trades

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

#### 8. Replace backtest output cells with optimiser analysis cells

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
