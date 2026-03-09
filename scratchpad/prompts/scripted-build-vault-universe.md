Update the crosschain configuration in  notebook to contain top 10 vaults based on one year returns from

- Arbitrum
- Base 
- Ethereum
- Avalanche
- Hypercore (Hyperliquid native) - use chain id 9999 - for this chain get top 30 vaults
- HyperEVM - use chain id 999
- Monad

Run the helper script to get the filtered vault list:

```shell
poetry run python scripts/filter-top-vaults.py
```

Replace the VAULTS = [...] entries in the cross-chain configuration section of the notebook with the script output.

Update the comment header above VAULTS with today's date.

Include "deposit closed" vaults but have a separate line comment why they are closed above the vault. Except for Hypercore vaults, they we cannot allocate and need to exclude from the notebook.

If the must-include or excluded vault lists need changing, edit the MUST_INCLUDE and EXCLUDED_VAULTS sets in `scripts/filter-top-vaults.py` before running. 
