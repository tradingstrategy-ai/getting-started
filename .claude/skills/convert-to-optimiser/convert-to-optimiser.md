---
name: convert-to-optimiser
description: Convert a backtesting notebook to a parameter optimisation notebook
---

# Convert backtest to optimiser

Convert a single backtesting notebook into an optimiser notebook that optimises strategy parameters using scikit-optimize's Gaussian Process.

## Input

- Path to a backtesting notebook (.ipynb)

## Reference files

- Reference optimiser notebook: `getting-started/scratchpad/vault-of-vaults/32-waterfall-diversified-larger-universe-grid-search-4d-rebalance-profit.ipynb`
- Reference backtest notebook: `getting-started/scratchpad/bnb-ath-2/11-bnb-ath-2h-rerun.ipynb`
- Transformation mapping: Read `backtest-to-optimiser.md` next to this skill file for the full mapping details

## Steps

1. **Read the input backtest notebook** and the transformation mapping file (`backtest-to-optimiser.md` in the same directory as this skill).

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
   - Test run: `poetry run ipython {output-notebook}.ipynb`
