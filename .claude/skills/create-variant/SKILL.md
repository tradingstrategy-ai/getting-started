---
name: create-variant
description: Create a variant of a backtesting or optimiser notebook.
---

# Create variant

This skill creates a variant of a backtesting or optimiser notebook.

## Input

- Existing notebook file
- Names of parameters we want to change

## Output

- New notebook file: increase the running counter prefix and change the slug
- Update parameters in the notebook with new values. Usually these live in the `Parameters` class, but sometimes they do not, such as when changing the optimiser target function.
- Update the notebook title and description in the first cell to reflect the new variant.
- In the first cell, include the name of the notebook this variant is based on.
- If the notebook heading contains research findings or other inherited results, remove them because they belong to the old notebook, not the new one.

If there is a heatmap and the variant changes the optimiser target, remember to update it:

```
from tradeexecutor.analysis.grid_search_parameters import analyse_parameter_pair_heatmaps

figs = analyse_parameter_pair_heatmaps(df, analysis_metric="Calmar")
for fig in figs:
    fig.show()

```

## Optimiser iterations

If the original notebook uses an optimiser (e.g. `perform_optimisation` with an `iterations` variable), reset `iterations = 18` in the variant so that the initial run does not take too long. The user can increase iterations later once the notebook is confirmed working.

## Verification

After the notebook is created, run it with `jupyter execute` as instructions in CLAUDE.md. Fix any bugs and issues you may have created.

## Analysis

- After the notebook has been successfully run, analyse the experiment result.
- Update the notebook heading with the results.
- Analyse individual positions and jumps in the equity curve. If the result looks lucky because of a single trade on one vault, instead of many vaults moving together during a broader market event, use `curator.py` to quantify that trade.
- Check for other suspicious traits in the results, such as an unusually strong best day or extreme kurtosis. Note that a strong best day can still be valid if BTC and ETH moved sharply on that day.
- Write the "Robustness analysis" in the heading section of the notebook noting any artefacts found during analysis.
- If the analysis is not robust and you think there are gaps, you can increase iterations to 28 and fine-tune parameter search space.

We want to see sections:

- Key new insights and what did we leart from this experiemenet
- Summary of results
- Robustness of results
