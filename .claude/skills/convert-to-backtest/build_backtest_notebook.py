"""Build a standalone backtest notebook from an optimiser notebook.

Usage:
    python build_backtest_notebook.py <input_notebook> <output_notebook> <best_params_json>

Example:
    python build_backtest_notebook.py \
        scratchpad/vault-of-vaults/33-hyperliquid-only-grid-search-4d-rebalance-profit.ipynb \
        scratchpad/vault-of-vaults/34-rerun.ipynb \
        '{"max_assets_in_portfolio": 45, "max_concentration": 0.33, "rolling_returns_bars": 60, "volatility_window": 60, "waterfall": true, "weight_function": "weight_1_slash_n", "weighting_method": "rolling_returns"}'

This script handles the mechanical parts of the conversion:
- Copies cells from the optimiser notebook
- Strips cell outputs
- Adds cell IDs (avoids nbformat MissingIDFieldWarning)
- Replaces Categorical/Integer/Real parameters with fixed values in the Parameters cell
- Restores calculate_and_load_indicators_inline() call in the indicators cell
- Removes display_parameters() call from the Parameters cell
- Removes skopt imports from the Parameters cell

The script does NOT handle:
- Simplifying decide_trades() dispatch logic (requires understanding of strategy code)
- Adding run_backtest_inline() call (must include cycle_duration=CycleDuration.from_timebucket()
  to match the grid search's internal cycle duration override)
- Adding ChartRegistry and pre-backtest visualisation cells
- Adding backtest output cells
- Fixing signal indicator name references in chart cells

These must be done manually or by Claude after running this script.
"""

import json
import copy
import re
import sys
import uuid


def make_cell_id():
    """Generate a unique cell ID for nbformat 5."""
    return uuid.uuid4().hex[:8]


def clean_cell(cell):
    """Strip outputs and add cell ID."""
    c = copy.deepcopy(cell)
    if c["cell_type"] == "code":
        c["outputs"] = []
        c["execution_count"] = None
    if "id" not in c:
        c["id"] = make_cell_id()
    return c


def replace_categoricals(source, best_params):
    """Replace Categorical([...]), Integer(...), Real(...) with best values in Parameters cell source."""
    for param_name, value in best_params.items():
        # Match: param_name = Categorical([...])
        pattern = rf'(\s+{re.escape(param_name)}\s*=\s*)Categorical\([^\)]+\)'
        if isinstance(value, str):
            replacement = rf'\1"{value}"'
        elif isinstance(value, bool):
            replacement = rf'\1{value}'
        elif isinstance(value, int):
            replacement = rf'\1{value}'
        elif isinstance(value, float):
            replacement = rf'\1{value}'
        else:
            replacement = rf'\1{value}'
        source = re.sub(pattern, replacement, source)

        # Match: param_name = Integer(low, high)
        pattern = rf'(\s+{re.escape(param_name)}\s*=\s*)Integer\([^\)]+\)'
        source = re.sub(pattern, replacement, source)

        # Match: param_name = Real(low, high)
        pattern = rf'(\s+{re.escape(param_name)}\s*=\s*)Real\([^\)]+\)'
        source = re.sub(pattern, replacement, source)

    return source


def remove_skopt_import(source):
    """Remove skopt import lines."""
    lines = source.split('\n')
    lines = [l for l in lines if 'from skopt.space import' not in l]
    return '\n'.join(lines)


def remove_display_parameters(source):
    """Remove display_parameters() call and its import."""
    lines = source.split('\n')
    lines = [l for l in lines if 'display_parameters(parameters)' not in l
             and 'from tradeexecutor.strategy.parameters import display_parameters' not in l]
    return '\n'.join(lines)


def restore_indicator_inline(source):
    """Add calculate_and_load_indicators_inline() call at end of indicators cell."""
    source = source.rstrip()
    source += "\n\n\n# Calculate all indicators and store the result on disk\n"
    source += "indicator_data = calculate_and_load_indicators_inline(\n"
    source += "    strategy_universe=strategy_universe,\n"
    source += "    create_indicators=indicators.create_indicators,\n"
    source += "    parameters=parameters,\n"
    source += ")\n"
    return source


def build_notebook(input_path, output_path, best_params):
    """Build the backtest notebook from an optimiser notebook.

    Returns the list of cells. Cells before the optimiser section
    (title through decide_trades) are transformed and included.
    Cells from the optimiser section onwards are excluded — they must
    be replaced with backtest output cells manually.
    """
    with open(input_path) as f:
        nb = json.load(f)

    cells = []
    optimiser_cell_found = False

    for i, cell in enumerate(nb['cells']):
        src = ''.join(cell['source'])

        # Stop before optimiser cells
        if '# Optimiser' in src and cell['cell_type'] == 'markdown':
            optimiser_cell_found = True
            break
        if 'perform_optimisation' in src:
            optimiser_cell_found = True
            break

        c = clean_cell(cell)

        # Transform Parameters cell
        if 'class Parameters' in src and ('Categorical(' in src or 'Integer(' in src or 'Real(' in src):
            new_src = replace_categoricals(src, best_params)
            new_src = remove_skopt_import(new_src)
            new_src = remove_display_parameters(new_src)
            c['source'] = [line + '\n' for line in new_src.split('\n')]

        # Transform indicators cell - restore inline calculation
        if 'display_indicators(indicators)' in src and 'calculate_and_load_indicators_inline' not in src:
            # Check if the import exists
            if 'calculate_and_load_indicators_inline' not in src:
                # Import should already be there from the optimiser
                pass
            new_src = restore_indicator_inline(src)
            c['source'] = [line + '\n' for line in new_src.split('\n')]

        cells.append(c)

    if not optimiser_cell_found:
        print("WARNING: Could not find optimiser cell boundary. All cells were included.")

    # Build the notebook (cells only up to optimiser section)
    output_nb = {
        "cells": cells,
        "metadata": nb.get("metadata", {}),
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with open(output_path, 'w') as f:
        json.dump(output_nb, f, indent=1)

    print(f"Written {len(cells)} cells to {output_path}")
    print(f"Optimiser cells excluded from cell {i} onwards ({len(nb['cells']) - i} cells)")
    print()
    print("Remaining manual steps:")
    print("1. Simplify decide_trades() dispatch logic and add run_backtest_inline()")
    print("2. Add ChartRegistry and pre-backtest visualisation cells")
    print("3. Add backtest output cells (from reference backtest notebook)")
    print("4. Fix 'signal' indicator references in chart cells")

    return cells


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    best_params = json.loads(sys.argv[3])

    build_notebook(input_path, output_path, best_params)
