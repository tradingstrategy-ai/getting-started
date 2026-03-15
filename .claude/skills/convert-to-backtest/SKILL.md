---
name: convert-to-backtest
description: Convert an optimiser or grid search notebook into a standalone backtest notebook using the bundled helper script and mapping guidance.
---

# Convert optimiser to backtest

Convert an optimiser or grid search notebook into a standalone backtesting notebook that runs a single backtest with the best parameter values from the optimisation.

## Input

- Path to an optimiser notebook (.ipynb)
- Best parameter values (provided by user or extracted from saved cell outputs)

## Reference files

- Reference backtest notebook: `getting-started/scratchpad/vault-of-vaults/30-waterfall-diversified-larger-universe.ipynb`
- Reference optimiser notebook: `getting-started/scratchpad/vault-of-vaults/33-hyperliquid-only-grid-search-4d-rebalance-profit.ipynb`

## Helper script

A Python script [build_backtest_notebook.py](build_backtest_notebook.py) (in the same directory as this skill) handles the mechanical parts of the conversion: stripping outputs, replacing Categorical parameters, restoring indicator inline calculation, and removing skopt imports. It produces a partial notebook (cells up to the optimiser section) that still needs manual steps for `decide_trades()` simplification, chart registry, and output cells.

## Steps

1. **Read the input optimiser notebook** and the cell-by-cell mapping section below.

2. **Read the reference backtest notebook** (`getting-started/scratchpad/vault-of-vaults/30-waterfall-diversified-larger-universe.ipynb`) — you will copy output cells from this.

3. **Determine best parameter values**: Check the optimiser notebook for saved cell outputs in the results table cell. If the notebook has outputs, extract the best row's parameter values. If there are no saved outputs, **ask the user** to provide the best parameter values for each `Categorical(...)` / `Integer(...)` / `Real(...)` parameter. List all searchable parameters found in the `Parameters` class so the user knows which values to provide.

4. **Create the backtest notebook** with these cells in order:

   a. **Title cell** (markdown): Remove "parameter search" / "grid search" / "optimise for ..." from the title. Below the title, add a preface section that includes:
      - A note referencing the source optimiser notebook by filename
      - A markdown table of the selected parameter values, listing each parameter that was a `Categorical`/`Integer`/`Real` in the optimiser and its chosen best value

      Example:
      ```markdown
      # Hyperliquid-only vault of vaults strategy

      - Rerun of the best result from `33-hyperliquid-only-grid-search-4d-rebalance-profit.ipynb`

      | Parameter | Value |
      |-----------|-------|
      | max_assets_in_portfolio | 20 |
      | max_concentration | 0.10 |
      | rolling_returns_bars | 60 |
      | weighting_method | rolling_returns |
      | weight_function | weight_equal |
      | waterfall | True |
      | volatility_window | 180 |
      ```

   b. **Setup cells** (markdown + code): Copy as-is from the optimiser.

   c. **Chain config cells** (markdown + code): Copy as-is from the optimiser.

   d. **Parameters cell** (code): Transform from the optimiser version:
      - Remove `from skopt.space import Categorical` (and `Integer`, `Real` if present)
      - Replace each `Categorical([v1, v2, ...])` with the single best value as a native Python type (`int`, `float`, `str`, or `bool`)
      - Replace each `Integer(low, high)` with the single best integer value
      - Replace each `Real(low, high)` with the single best float value
      - Keep dispatch parameters (`weighting_method`, `weight_function`, `waterfall`, etc.) as fixed values in the class for traceability
      - Remove `display_parameters(parameters)` and its `from tradeexecutor.strategy.parameters import display_parameters` import at the end of the cell
      - If `use_managed_yield = False` was set specifically for the optimiser, ask the user whether to restore it to `True`

   e. **Trading universe cells** (markdown + code): Copy as-is from the optimiser (`create_trading_universe()` function).

   f. **Indicators cell** (markdown + code): Copy from the optimiser but **add back** the `calculate_and_load_indicators_inline()` call at the end of the cell, after `display_indicators(indicators)`:
      ```python
      # Calculate all indicators and store the result on disk
      indicator_data = calculate_and_load_indicators_inline(
          strategy_universe=strategy_universe,
          create_indicators=indicators.create_indicators,
          parameters=parameters,
      )
      ```
      Ensure the import is present at the top of the cell:
      ```python
      from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
      ```

   g. **Trading universe charts cell** (markdown + code): Add a `ChartRegistry` setup cell copied from the reference backtest notebook (cell 13). This cell defines chart functions and registers them. It must come **after** the indicators cell because it uses `indicator_data`. Adapt chart function definitions to match the strategy (e.g. `trading_pair_breakdown_with_chain`, `all_vault_positions_by_profit`).

      **Tip**: If the optimiser notebook has a "Backtesting chart rendering for the best strategy" cell later in the notebook, use its chart function definitions — they are already adapted to the strategy. Move them here instead.

   h. **Pre-backtest visualisation cells**: Copy from the reference backtest notebook — cells for available pairs, inclusion criteria checks, vault TVL data, signal charts, etc. These come after the chart registry cell and before the time range cell.

      **Important — indicator name mismatch**: The reference backtest may use a unified `"signal"` indicator in its chart cells (e.g. `indicator_data.get_indicator_series("signal", pair=pair)`). Optimiser notebooks often do not define a `signal` indicator — they use individual indicators like `"rolling_returns"`, `"rolling_sharpe"`, etc. directly. When copying pre-backtest chart cells, replace any `"signal"` references with the actual indicator name that matches the best `weighting_method`. For example, if `weighting_method = "rolling_returns"`, change `get_indicator_series("signal", ...)` to `get_indicator_series("rolling_returns", ...)`.

   i. **Time range cell** (markdown + code): Copy from the optimiser. If it uses simple `Parameters.backtest_start` / `Parameters.backtest_end`, keep as-is. Optionally restore `indicator_data` references if the reference backtest uses them.

   j. **Strategy cell** (code): Copy `decide_trades()` from the optimiser with these simplifications:

      - **Remove `float()` casts**: Parameters are now native Python types, not `numpy.float64` from `Categorical`. Change `float(parameters.max_concentration)` back to `parameters.max_concentration`.

      - **Simplify dynamic dispatch to direct calls**: If `decide_trades()` dispatches based on string parameters like `weighting_method` or `weight_function`, replace the dispatch with the direct call using the best value. For example, if the best `weight_function` is `"weight_equal"`, replace the entire `weight_func_map` lookup with `alpha_model.assign_weights(method=weight_equal)`. Remove unused branches and dead code (e.g. `pair_volatilities` tracking if `inverse_volatility` was not selected).

      - **Simplify boolean parameters**: If the optimiser passed `waterfall=parameters.waterfall`, replace with the literal best value (e.g. `waterfall=True`).

      - **Add `run_backtest_inline()` call** after `decide_trades()` in the same cell:

        **Critical — cycle duration mismatch**: The grid search internally uses `CycleDuration.from_timebucket(candle_time_bucket)` to determine the cycle duration (e.g. `cycle_1d` for daily candles), which **overrides** `Parameters.cycle_duration`. If Parameters specifies a different cycle (e.g. `cycle_4d`), the grid search ignores it. The `run_backtest_inline()` call must explicitly pass the same cycle duration as the grid search to reproduce results. Use `CycleDuration.from_timebucket(parameters.candle_time_bucket)`.

        ```python
        from tradeexecutor.strategy.cycle import CycleDuration

        result = run_backtest_inline(
            name=parameters.id,
            engine_version="0.5",
            decide_trades=decide_trades,
            create_indicators=indicators.create_indicators,
            cycle_duration=CycleDuration.from_timebucket(parameters.candle_time_bucket),
            client=client,
            universe=strategy_universe,
            parameters=parameters,
            max_workers=1,
            start_at=backtest_start,
            end_at=backtest_end,
        )

        state = result.state

        trade_count = len(list(state.portfolio.get_all_trades()))
        print(f"Backtesting completed, backtested strategy made {trade_count} trades")

        # Add state to the further charts
        chart_renderer = ChartBacktestRenderingSetup(
            registry=charts,
            strategy_input_indicators=indicator_data,
            state=state,
            backtest_start_at=backtest_start,
            backtest_end_at=backtest_end,
        )
        ```

   k. **Backtest output cells**: Copy from the reference backtest notebook (cells 27 onwards). These are heading + code cell pairs:

      | Heading | Description |
      |---------|-------------|
      | `# Performance metrics` | `compare_strategy_backtest_to_multiple_assets()` |
      | `# Equity curve` | `equity_curve_with_benchmark` chart |
      | `## Equity curve with drawdown` | `equity_curve_with_drawdown` chart |
      | `# Asset weights` | Section heading |
      | `## Volatiles only` | `volatile_weights_by_percent` chart |
      | `## Volatiles and non-volatiles` | `volatile_and_non_volatile_percent` chart |
      | `## Portfolio equity curve breakdown by asset` | `equity_curve_by_asset` chart |
      | `## Portfolio equity curve breakdown by chain` | `equity_curve_by_chain` chart |
      | `## Weight allocation statistics` | `weight_allocation_statistics` chart |
      | `# Rolling Sharpe` | Rolling Sharpe ratio calculation |
      | `# Positions at the end` | `positions_at_end` chart |
      | `# Strategy thinking` | `last_messages` chart |
      | `# Alpha model diagnostics data` | `alpha_model_diagnostics` chart |
      | `# Trading pair breakdown` | `trading_pair_breakdown_with_chain` chart |
      | `# Trading metrics` | `trading_metrics` chart |
      | `# Interest accrued` | Section heading |
      | `## Lending pools` | `lending_pool_interest_accrued` chart |
      | `# Vault performance` | Section heading |
      | `## Vault statistics` | `vault_statistics` chart |
      | `## Vault position list` | `all_vault_positions_by_profit` chart |
      | `## Vault individual position timeline` | Vault-specific rendering |

   **Do not** copy any optimiser-specific cells (perform_optimisation, results table, equity curves overlay, parameter analysis, decision tree, feature importance, heatmaps, cluster analysis, parallel coordinates, best candidate equity curve, best pick portfolio/trade/positions sections, or the best strategy chart rendering cells).

5. **Write the output notebook** as `{NN+1}-rerun.ipynb` in the same directory as the input notebook. The number prefix should be the next sequential number after the highest existing notebook number in the directory.

6. **Verify** the notebook structure:
   - Parameters class has fixed scalar values (no `Categorical`, `Integer`, or `Real`)
   - No `from skopt.space import Categorical` import
   - `calculate_and_load_indicators_inline()` is present at the end of the indicators cell
   - `run_backtest_inline()` is present in the strategy cell
   - `ChartRegistry` and `ChartBacktestRenderingSetup` are properly set up
   - No `float()` casts around parameter values that are now native Python types
   - No dynamic dispatch for parameters that are now fixed values
   - All chart rendering cells reference `chart_renderer`
   - Test run: `poetry run jupyter execute {output-notebook}.ipynb --inplace --timeout=900`

7. **Verify results match the optimiser's best pick**: After running the notebook, compare the backtest metrics (CAGR, Sharpe, max drawdown) with the optimiser's best result. The values should match exactly or near-exactly:
   - **CAGR**: Should match to within 1% absolute (e.g. 40.8% vs 40.8%).
   - **Sharpe ratio**: Should match to within 0.1 (e.g. 2.22 vs 2.22).
   - **Max drawdown**: Should match to within 1 percentage point (e.g. -6.00% vs -5.85%).
   - **Trade count**: May differ slightly but should be the same order of magnitude.

   If the results differ significantly (e.g. CAGR off by more than 10% relative), check these common pitfalls in order:

   1. **Cycle duration mismatch** (most common cause): The grid search overrides `Parameters.cycle_duration` with `CycleDuration.from_timebucket(candle_time_bucket)`. For daily candles this means `cycle_1d`, even if Parameters says `cycle_4d`. Ensure `run_backtest_inline()` passes `cycle_duration=CycleDuration.from_timebucket(parameters.candle_time_bucket)`. This was the root cause of a 41% vs 22% CAGR mismatch in the first application of this skill.
   2. **decide_trades() simplified incorrectly**: Did you accidentally change the strategy logic? Compare line by line with the original.
   3. **Wrong parameter values**: Are all parameters set to the correct best values from the optimiser?
   4. **Indicator name mismatch**: Is the indicator used for signal selection correct (e.g. `"rolling_returns"` vs `"signal"`)?
   5. **Weight function mismatch**: Is the weight function correct (e.g. `weight_by_1_slash_n` vs `weight_equal`)?

## Cell-by-cell mapping

Reference notebooks (in `getting-started/scratchpad/vault-of-vaults/`):
- Optimiser: `33-hyperliquid-only-grid-search-4d-rebalance-profit.ipynb`
- Backtest: `30-waterfall-diversified-larger-universe.ipynb`

### What stays the same

These cells are copied verbatim from the optimiser notebook:

- **Setup cell**: `Client.create_jupyter_client()` + `setup_charting_and_output()`
- **Chain config cell**: Exchange/pair/vault configuration
- **Trading universe cell**: `create_trading_universe()` function
- **Indicators cell**: All indicator function definitions — but see "Restore inline indicator calculation" below
- **Backtest time range cell**: Start/end date calculation (may already use `Parameters.backtest_start/end`)

### What changes

#### 1. Title cell

- Optimiser: `# Hyperliquid-only vault of vaults parameter search - optimise for profit`
- Backtest: `# Hyperliquid-only vault of vaults strategy`

Remove "parameter search", "grid search", "optimise for ..." from the title. Below the title, add a preface section with:
1. A note referencing the source optimiser notebook by filename
2. A markdown table listing each parameter that was searchable (`Categorical`/`Integer`/`Real`) and its chosen best value

Example:
```markdown
# Hyperliquid-only vault of vaults strategy

- Rerun of the best result from `33-hyperliquid-only-grid-search-4d-rebalance-profit.ipynb`

| Parameter | Value |
|-----------|-------|
| max_assets_in_portfolio | 20 |
| max_concentration | 0.10 |
| rolling_returns_bars | 60 |
| weighting_method | rolling_returns |
| weight_function | weight_equal |
| waterfall | True |
| volatility_window | 180 |
```

#### 2. Parameters cell

Remove imports:
```python
from skopt.space import Categorical  # Remove
from skopt.space import Integer      # Remove if present
from skopt.space import Real         # Remove if present
```

Replace `Categorical([...])` with the single best value. The value must be the native Python type. Example:

```python
# Optimiser (searchable)
max_assets_in_portfolio = Categorical([5, 10, 20, 35, 45])
max_concentration = Categorical([0.05, 0.10, 0.15, 0.20, 0.33])
rolling_returns_bars = Categorical([30, 60, 120, 240, 480])
weighting_method = Categorical(["rolling_returns", "rolling_sharpe", "rolling_sortino", "inverse_volatility"])
weight_function = Categorical(["weight_equal", "weight_1_slash_n"])
waterfall = Categorical([True, False])
volatility_window = Categorical([30, 60, 180, 240])

# Backtest (fixed, using best values from optimisation)
max_assets_in_portfolio = 20
max_concentration = 0.10
rolling_returns_bars = 60
weighting_method = "rolling_returns"
weight_function = "weight_equal"
waterfall = True
volatility_window = 180
```

Keep dispatch parameters (`weighting_method`, `weight_function`, `waterfall`, etc.) as fixed values in the `Parameters` class for traceability, even if `decide_trades()` is simplified to not reference them.

Other changes:
- Remove `display_parameters(parameters)` and its `from tradeexecutor.strategy.parameters import display_parameters` import at the end of the cell
- If `use_managed_yield = False` was set for the optimiser, ask the user whether to restore to `True`

#### 3. Restore inline indicator calculation

The optimiser indicators cell ends without `calculate_and_load_indicators_inline()` because the optimiser calculates indicators for each parameter combination internally. The backtest needs this call restored.

Add at the end of the indicators cell (after `display_indicators(indicators)`):
```python
# Calculate all indicators and store the result on disk
indicator_data = calculate_and_load_indicators_inline(
    strategy_universe=strategy_universe,
    create_indicators=indicators.create_indicators,
    parameters=parameters,
)
```

Ensure the import is at the top of the cell:
```python
from tradeexecutor.strategy.pandas_trader.indicator import calculate_and_load_indicators_inline
```

This is safe because parameters are now fixed scalar values, not `Categorical` instances.

#### 4. Add ChartRegistry and pre-backtest visualisations

The optimiser notebook has no `ChartRegistry` before the backtest. The backtest notebook needs one.

Add a charts cell (based on reference backtest cell 13) that:
1. Imports chart functions from `tradeexecutor.strategy.chart.standard.*`
2. Defines custom chart wrapper functions (e.g. `trading_pair_breakdown_with_chain`, `all_vault_positions_by_profit`)
3. Creates a `ChartRegistry` and registers all charts
4. Creates a pre-backtest `ChartBacktestRenderingSetup` with `indicator_data` (no `state` yet — state comes after `run_backtest_inline`)

**Tip**: If the optimiser notebook has a "Backtesting chart rendering for the best strategy" cell (typically near the end), reuse its chart function definitions — they are already adapted to this strategy. Move them to the pre-backtest position.

Then add pre-backtest visualisation cells (based on reference backtest cells 14-22):
- Available pairs
- Inclusion criteria checks
- Vault TVL and share price data
- Signal by chain

**Important — indicator name mismatch**: The reference backtest's signal chart cells use `indicator_data.get_indicator_series("signal", pair=pair)`, referencing a unified `signal` indicator. Optimiser notebooks often do not define a `signal` indicator — they use individual indicators like `"rolling_returns"`, `"rolling_sharpe"`, etc. directly. When copying signal chart cells, replace `"signal"` with the actual indicator name matching the best `weighting_method` (e.g. `"rolling_returns"`).

#### 5. Simplify decide_trades() and add run_backtest_inline()

The optimiser's `decide_trades()` has patterns that should be simplified when parameter values are fixed.

##### a. Remove float() casts

```python
# Optimiser (numpy.float64 workaround)
max_weight = float(parameters.max_concentration)

# Backtest (native Python float, no cast needed)
max_weight = parameters.max_concentration
```

##### b. Simplify dynamic signal indicator dispatch

The optimiser dispatches based on `parameters.weighting_method`:
```python
weighting_method = parameters.weighting_method
if weighting_method == "rolling_returns" or weighting_method == "inverse_volatility":
    signal_indicator_name = "rolling_returns"
elif weighting_method == "rolling_sharpe":
    signal_indicator_name = "rolling_sharpe"
...
pair_signal = indicators.get_indicator_value(signal_indicator_name, pair=pair)
```

If the best `weighting_method` is `"rolling_returns"`, simplify to a direct call:
```python
pair_signal = indicators.get_indicator_value("rolling_returns", pair=pair)
```

**Note**: If the backtest reference uses a unified `signal` indicator that wraps the underlying metric, use that instead.

##### c. Simplify dynamic weight function dispatch

The optimiser has:
```python
if weighting_method == "inverse_volatility":
    for pair_id, signal_obj in alpha_model.signals.items():
        if pair_id in pair_volatilities:
            signal_obj.signal = pair_volatilities[pair_id]
    alpha_model.assign_weights(method=weight_by_1_slash_signal)
else:
    weight_func_map = {
        "weight_equal": weight_equal,
        "weight_1_slash_n": weight_by_1_slash_n,
    }
    weight_func = weight_func_map[parameters.weight_function]
    alpha_model.assign_weights(method=weight_func)
```

If the best values are `weighting_method="rolling_returns"` and `weight_function="weight_equal"`, simplify to:
```python
alpha_model.assign_weights(method=weight_equal)
```

Remove the `pair_volatilities` dict, the `weight_func_map` lookup, and any unused weight function imports.

##### d. Simplify boolean/enum parameters

```python
# Optimiser
waterfall=parameters.waterfall,

# Backtest (if best value is True)
waterfall=True,
```

##### e. Add run_backtest_inline() call

**Critical — cycle duration mismatch**: The grid search internally uses `CycleDuration.from_timebucket(candle_time_bucket)` to determine the cycle duration, which **overrides** `Parameters.cycle_duration`. For example, with `TimeBucket.d1` candles, the grid search always runs with `cycle_1d` (daily rebalancing), even if Parameters specifies `cycle_4d`. The `run_backtest_inline()` call must explicitly pass the same cycle duration to reproduce results.

After `decide_trades()`, in the same cell, add:
```python
from tradeexecutor.strategy.cycle import CycleDuration

result = run_backtest_inline(
    name=parameters.id,
    engine_version="0.5",
    decide_trades=decide_trades,
    create_indicators=indicators.create_indicators,
    cycle_duration=CycleDuration.from_timebucket(parameters.candle_time_bucket),
    client=client,
    universe=strategy_universe,
    parameters=parameters,
    max_workers=1,
    start_at=backtest_start,
    end_at=backtest_end,
)

state = result.state

trade_count = len(list(state.portfolio.get_all_trades()))
print(f"Backtesting completed, backtested strategy made {trade_count} trades")

# Add state to the further charts
chart_renderer = ChartBacktestRenderingSetup(
    registry=charts,
    strategy_input_indicators=indicator_data,
    state=state,
    backtest_start_at=backtest_start,
    backtest_end_at=backtest_end,
)
```

The `chart_renderer` is re-created here with the `state` parameter, overwriting the pre-backtest renderer.

#### 6. Remove optimiser-specific cells

All of these cells from the optimiser are **removed**:

| Optimiser cells | Description |
|----------------|-------------|
| `# Optimiser` (markdown + code) | `perform_optimisation()` call |
| `# Results` (markdown + code) | `analyse_optimiser_result()` + `render_grid_search_result_table()` |
| `## Equity curves` (markdown + code) | `visualise_grid_search_equity_curves()` overlay |
| `# Parameter analysis` (markdown) | Section heading |
| `## Decision tree visualisation` (markdown + code) | `analyse_decision_tree()` |
| `## Feature importance analysis` (markdown + code) | `analyse_feature_importance()` |
| `## Heatmaps for parameter pairs` (markdown + code) | `analyse_parameter_pair_heatmaps()` |
| `## Cluster analysis` (markdown + code) | `KMeans` + PCA (if present) |
| `## Parallel coordinates plot` (markdown + code) | `px.parallel_coordinates` (if present) |
| `# The best candidate equity curve` (markdown + code) | `visualise_single_grid_search_result_benchmark()` |
| `# Portfolio performance (best pick)` (markdown + code) | `compare_strategy_backtest_to_multiple_assets()` on best pick |
| `# Trade summary (best pick)` (markdown + code) | `best_pick.summary` |
| `# Trading pair performance breakdown` (markdown + code) | `analyse_multipair()` on best pick |
| `# Best positions` (markdown + code) | Sorted positions from best pick |
| `# Rolling sharpe` (markdown + code) | Rolling Sharpe on best pick |
| `# Backtesting chart rendering for the best strategy` (markdown + code) | `ChartRegistry` for best pick (reuse chart definitions, see step 4) |
| All subsequent best-strategy chart cells | Available pairs, trading pair breakdown, vault stats, rolling Sharpe, asset weights |

#### 7. Add backtest output cells

Replace the removed optimiser cells with standard backtest output cells. Copy from the reference backtest notebook (cells 27-65):

| # | Heading | Chart/function used |
|---|---------|---------------------|
| 1 | `# Performance metrics` | `performance_metrics` chart + `compare_strategy_backtest_to_multiple_assets()` |
| 2 | `# Equity curve` | `equity_curve_with_benchmark` chart |
| 3 | `## Equity curve with drawdown` | `equity_curve_with_drawdown` chart |
| 4 | `# Asset weights` | Section heading only |
| 5 | `## Volatiles only` | `volatile_weights_by_percent` chart |
| 6 | `## Volatiles and non-volatiles` | `volatile_and_non_volatile_percent` chart |
| 7 | `## Portfolio equity curve breakdown by asset` | `equity_curve_by_asset` chart |
| 8 | `## Portfolio equity curve breakdown by chain` | `equity_curve_by_chain` chart |
| 9 | `## Weight allocation statistics` | `weight_allocation_statistics` chart |
| 10 | `# Rolling Sharpe` | `calculate_rolling_sharpe()` with plotly |
| 11 | `# Positions at the end` | `positions_at_end` chart |
| 12 | `# Strategy thinking` | `last_messages` chart |
| 13 | `# Alpha model diagnostics data` | `alpha_model_diagnostics` chart |
| 14 | `# Trading pair breakdown` | `trading_pair_breakdown_with_chain` chart |
| 15 | `# Trading metrics` | `trading_metrics` chart |
| 16 | `# Interest accrued` | Section heading |
| 17 | `## Lending pools` | `lending_pool_interest_accrued` chart |
| 18 | `# Vault performance` | Section heading |
| 19 | `## Vault statistics` | `vault_statistics` chart |
| 20 | `## Vault position list` | `all_vault_positions_by_profit` chart |
| 21 | `## Vault individual position timeline` | `vault_position_timeline` + pair-specific rendering |

### Naming convention

Output file: `{NN+1}-rerun.ipynb`

- `NN+1` is the next sequential number after the highest numbered notebook in the same directory
- Example: `33-hyperliquid-only-grid-search-4d-rebalance-profit.ipynb` -> `34-rerun.ipynb`
