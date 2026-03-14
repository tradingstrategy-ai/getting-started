---
name: create-variant
description: Create variant of backtesting/optimizer notebook
---

# Create variant

This skill create a variant of backtesting/optimizer notebook.

## Input

- Existing notebook file
- Names of parameters we want to change

## Output

- New notebook file: 1) increase running counter prefix 2) change the slug
- Update parameters in the notebook with new values - usually in `Parameters` class. Sometimes they are not, like when we ask to change the optimiser optimisation function.
- Update notebook title and description in the first cell to reflect the new variant - what did we change
- In the first cell, include the name of the notebook this variant is based
- If the notebook has Research findings and such data at its heading, remove those, because they are relevant for the old notebook, not the new one

If there is a heatmap element, and the variant changes the optimiser target, remember to update it:

```
from tradeexecutor.analysis.grid_search_parameters import analyse_parameter_pair_heatmaps

figs = analyse_parameter_pair_heatmaps(df, analysis_metric="Calmar")
for fig in figs:
    fig.show()

```

## Optimiser iterations

If the original notebook uses an optimiser (e.g. `perform_optimisation` with an `iterations` variable), reset `iterations = 10` in the variant so that the initial run does not take too long. The user can increase iterations later once the notebook is confirmed working.

## Verification

After the notebook is created, run it with `jupyter execute` as instructions in CLAUDE.md. Fix any bugs and issues you may have created.
