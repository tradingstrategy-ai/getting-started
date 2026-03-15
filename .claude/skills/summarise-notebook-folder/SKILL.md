---
name: summarise-notebook-folder
description: Read through all experiement notebooks in a folder and write a summary.
---

Create or update README.md summary of experiement notbeooks.

# Input

- Folder path

# Output

- README.md updated in that folder

# Process

Read all notebooks in vault-of-vault folders and write a summary markdown README.md. - If there are any notebooks that are not run yet, or partially run, attempt to run them. Use max 3 subagents for this.

From each notebook summarise the output and update README.md accordingly. We call notebooks NB1, NB2, etc. Some numbers might have duplicates so them call notebooks NB1a, NB1b.

README should have sections for:

- List of notebooks: number and short summary of minimum 4 sentences of the experiement. Use at least three sentences for the summary. Include backtest range. Include the type of the asset universe: single chain, multichain, vaults only, something else. the peak number of assets in available trading universe. If the notebook has backtest have CAGR, Sharpe, maxDD written down. Mark if the notebook does not run. If the notebook was based on another notebook include this information as well.

- Reference of all indicators used across notebooks - reference to the notebook where they appeard first time like NBxx For each indicator include function name and 2 sentence summary of its docstring. If no good docstring is available, read the code and summarise it. If there is resarch and post links about the indicators in the notebook heading comments or docstring itself, add them as well.

- Reference of weighting methods used across notebooks - what they do and why, reference to the notebook where they appeard first time like NBxx

- Reference to analytics charts and tables we use - reference to the notebook where they appeard first time like NBxx. One sentence summary of each chart/table function and why it is being used and what it is good for.

For procesing each notebook, spawn an agent. Use max 3 agents and process notebooks in batches. The subagent does the task and passes the information for the main agent to be added to the README.

Start from the newest (highest notebook number) or go to the lowest.

# Metric extraction

**Before reading the notebook body**, each subagent must run the helper script to extract CAGR/Sharpe/MaxDD:

```bash
python3 BASE_DIR/extract_metrics.py NOTEBOOK.ipynb
```

where `BASE_DIR` is the directory containing this skill file (`skill.md`). The script outputs one line per notebook: `filename.ipynb  CAGR=X%  Sharpe=X  MaxDD=-X%` or `NO_RESULTS`.

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
