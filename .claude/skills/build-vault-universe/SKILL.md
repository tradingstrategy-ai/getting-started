---
name: build-vault-universe
description: Update a notebook's cross-chain vault universe to the top 10 vaults by one-year return using the helper script output.
---

Update the target notebook so its vault configuration contains the top 10 vaults by one-year return.

Run the helper script to get the filtered vault list:

```shell
# Create a copy of this file if you need to change the default parameters
poetry run python scripts/larger-filter-top-vaults.py
```

The script output will be long, so use files to move the data around.

Replace the VAULTS = [...] entries in the cross-chain configuration section of the notebook with the script output.

Update the comment header above VAULTS with today's date.

Include "deposit closed" vaults, but add a separate comment line above each one explaining why deposits are closed. Exclude Hypercore vaults because we cannot allocate to them.

Don't run the notebook at the end of the update.

## Default configured chains

See the script file for the default chain set. Typical chains are:

- Arbitrum
- Base
- Ethereum
- Avalanche
- Hypercore (Hyperliquid native) - use chain id 9999
- HyperEVM - use chain id 999
- Monad
