Update the crosschain configuration in  notebook to contain top 10 vaults based on one year returns from

- Arbitrum
- Base 
- Ethereum
- Avalanche
- Hypercore (Hyperliquid native) - use chain id 9999 
- HyperEVM - use chain id 999
- Monad

Run the helper script to get the filtered vault list:

```shell
poetry run python scripts/larger-filter-top-vaults.py
```

The script output will be long, so use files to copy-paste stuff around.

Replace the VAULTS = [...] entries in the cross-chain configuration section of the notebook with the script output.

Update the comment header above VAULTS with today's date.

Include "deposit closed" vaults but have a separate line comment why they are closed above the vault. Except for Hypercore vaults, they we cannot allocate and need to exclude from the notebook.

Don't run the notebook at the end of the update.