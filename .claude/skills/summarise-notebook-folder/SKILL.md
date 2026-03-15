---
name: summarise-notebook-folder
description: Read through all experiment notebooks in a folder and write a summary README.
---

Create or update a `README.md` summary of experiment notebooks.

# Input

- Folder path

# Output

- README.md updated in that folder

# Process

Read all notebooks in the target folder and write a summary `README.md`. If any notebooks have not been run yet, or were only partially run, attempt to run them. Use at most 3 subagents for this.

Summarise each notebook's output and update `README.md` accordingly. Refer to notebooks as `NB1`, `NB2`, and so on. If some numbers are duplicated, use labels like `NB1a` and `NB1b`.

README should have sections for:

- List of notebooks: notebook number and a short summary of at least four sentences for each experiment. Include the decision cycle such as `1h`, `1d`, or `1w`; the backtest range; the asset universe type such as single-chain, multichain, or vault-only; and the peak number of assets in the available trading universe. If the notebook has backtest results, include CAGR, Sharpe, and max drawdown. Mark notebooks that do not run. If a notebook is based on another notebook, include that information as well.

- Reference of all indicators used across notebooks: include the notebook where each one first appeared, such as `NBxx`. For each indicator, include the function name and a two-sentence summary of its docstring. If no good docstring is available, read the code and summarise it. If there are research notes or post links about the indicator in the notebook heading comments or docstring, include them as well.

- Reference of weighting methods used across notebooks: explain what they do, why they are used, and where they first appeared, such as `NBxx`.

- Reference to the analytics charts and tables used across the notebooks: note where each one first appeared, such as `NBxx`. Include a one-sentence summary of each chart or table function, why it is used, and what it is good for.

For processing each notebook, spawn a subagent. Use at most 3 subagents and process notebooks in batches. Each subagent should do the notebook-level work and pass the information back for the main agent to add to the README.

Start from the newest (highest notebook number) or go to the lowest.

# Metric extraction

**Before reading the notebook body**, each subagent must run the helper script to extract CAGR/Sharpe/MaxDD:

```bash
python3 BASE_DIR/extract_metrics.py NOTEBOOK.ipynb
```

where `BASE_DIR` is the directory containing this skill file (`SKILL.md`). The script outputs one line per notebook: `filename.ipynb  CAGR=X%  Sharpe=X  MaxDD=-X%` or `NO_RESULTS`.

You can also pass a folder to extract all notebooks at once:

```bash
python3 BASE_DIR/extract_metrics.py /path/to/notebook/folder/
```

## Why this script is needed

Do NOT try to extract metrics by reading notebooks with `Read` or by grepping:

1. **Read tool line limit**: Notebooks are 10k–142k lines. Results appear at line ~6000+. The Read tool default (2000 lines) only shows imports and boilerplate.
2. **Grep noise**: Notebooks embed the full Plotly JS library in output cells. Grepping for `CAGR` or `Sharpe` matches thousands of lines in minified JS, producing truncated 35KB+ output that buries the actual metrics.
3. **Multiple occurrences**: A single notebook contains CAGR in four places — grid search table (ALL combinations), best-result summary, QuantStats table (Strategy + benchmark columns), and trade summary (annualised return ≠ CAGR). Only the script correctly identifies the best-pick strategy value.
4. **Unicode**: QuantStats uses `CAGR﹪` (U+FE6A small percent sign), not `CAGR%`.

The script parses the notebook JSON structure and extracts from the QuantStats `text/plain` output (first column = Strategy) with fallback to the grid search "best result found" summary line.
