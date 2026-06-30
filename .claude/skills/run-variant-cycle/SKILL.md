---
name: run-variant-cycle
description: Create and run a variant of a backtesting or optimiser notebook.
---

# Run variant cycle

This skill creates a variant of a backtesting or optimiser notebook, 
runs it and reports result back.

## 1. Input notebook

Usually you determine this from the conversation context and it is a previous experiment notebook, or a notebook linked by the user.

Then the user tells you how they want to modify the notebook.

Changes include 

- Names of parameters we want to change
- Backtesting methodology we want to try
- How to change the trading universe

For further examples you can use:

- For search and optimiser use `scratchpad/vault-of-vaults/67-hyperliquid-dual-signal-parameter-tuning.ipynb`
- For a single backtest use `scratchpad/vault-of-vaults/40-hyperliquid-august-start.ipynb`

## 2. New notebook

Based on this we create a new notebook.

### 2.a) Outputted notebook file

- New notebook file: increase the running counter prefix and change the slug
  - This is a backtest call the file {number}-backtest-{slug}.ipynb
  - This is a optimiser call the file {number}-opt-{slug}.ipynb
  - If it is other research call {number}-research-{slug}.ipynb
- Update parameters in the notebook with new values. Usually these live in the `Parameters` class, but sometimes they do not, such as when changing the optimiser target function.
- Update the notebook title and description in the first cell to reflect the new variant.
- In the first cell, include the name of the notebook this variant is based on.
- If the notebook heading contains research findings or other inherited results, remove them because they belong to the old notebook, not the new one.
- If the trading universe was re-created or changed, and this was done by LLM agent with a prompt, include the comment and ruels that re-created the trading universe in the Markdown cell heading the trading universe code


### 2.b) Optimiser iterations

If the original notebook uses an optimiser (e.g. `perform_optimisation` with an `iterations` variable), reset `iterations = 18` in the variant so that the initial run does not take too long. The user can increase iterations later once the notebook is confirmed working.

## 3. Execute notebook

Run the notebook using as described in CLAUDE.md using a subagent.
If there are any bugs, make sure subagent fixed them and rerun the notebook again.

## 4. Analysis

From each backtest run, we should get 

- equity curve 
- key portfolio metrics minimum.

Reflect changes in the notebook

- After the notebook has been successfully run, analyse the experiment result.
- Update the notebook head section with the a Markdown table of summary of results.

- Analyse individual positions and jumps in the equity curve. If the result looks lucky because of a single trade on one vault, instead of many vaults moving together during a broader market event, use `curator.py` to quantify that trade.
- Check for other suspicious traits in the results, such as an unusually strong best day or extreme kurtosis. Note that a strong best day can still be valid if BTC and ETH moved sharply on that day.

## 5. Posting results as a PR comment

We must have a worktree, branch and Github PR open.

- Create a new PR comment that is titled with the notebook name
- Include the summary of the results 
- Include the equity curve and other charts extracted from the 

Mention the Github PR comment link in the chat.

## 6. Posting results as a chat comment

- Post the same results to LLM chat as you posted to Github
- If the chat supports images, add the equity curve chart as a chat message

## 7. Verification

Check that Github PR comment correctly contains

- New title
- Equity curve(s)
- Key metrics table
- All images render correctly
