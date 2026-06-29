# Vault selection

This note is for selecting ERC-4626 and native vault universes for backtest notebooks.

## How to download vault data

Use the Trading Strategy client to download the public R2-backed vault universe and cleaned vault price history.

```shell
poetry run python - <<'PY'
from tradingstrategy.client import Client
from tradingstrategy.alternative_data.vault import DEFAULT_VAULT_DOWNLOAD_ROOT

client = Client.create_jupyter_client()

vault_universe = client.fetch_vault_universe()
price_history = client.fetch_vault_price_history()

print(f"download root: {DEFAULT_VAULT_DOWNLOAD_ROOT}")
print(f"vaults: {len(vault_universe.vaults)}")
print(f"price rows: {len(price_history)}")
PY
```

Default local cache:

```text
~/.tradingstrategy/vaults/downloads/vault-universe.json
~/.tradingstrategy/vaults/downloads/vault-price-history.parquet
~/.tradingstrategy/vaults/downloads/vault-price-history.parquet.metadata.json
```

The client downloads from these public R2-backed URLs defined in `tradingstrategy.alternative_data.vault`:

```text
https://top-defi-vaults.tradingstrategy.ai/top_vaults_by_chain.json
https://vault-protocol-metadata.tradingstrategy.ai/cleaned-vault-prices-1h.parquet
```

If a notebook needs API credentials, source or load `/home/mikko/local-test.env`, but do not print secrets.

## Cross-reference to vault data docs and fields

Canonical producer-side documentation is in the editable `web3-ethereum-defi` checkout:

```text
/home/mikko/code/trade-executor/deps/web3-ethereum-defi/scripts/erc-4626/README-vault-scripts.md
```

Relevant sections:

- `export-data-files.py`: uploads production vault files to Cloudflare R2.
- `vault-analysis-json.py`: generates `top_vaults_by_chain.json`.
- `scan-vaults-all-chains.py`, `scan-prices.py`, `post-process-prices.py`: scanner pipeline.
- Sticky export notes: explains `vault-export-state.json`, `sticky_export`, stale rows, and blacklist suppression.

Client-side loader and field mapping:

```text
/home/mikko/code/trade-executor/deps/trading-strategy/tradingstrategy/alternative_data/vault.py
```

The JSON top level contains:

- `generated_at`
- `metadata`
- `core3_protocols`
- `curators`
- `vaults`

Common per-vault fields used for filtering:

- Identity: `chain_id`, `chain`, `address`, `name`, `vault_slug`
- Protocol: `protocol`, `protocol_slug`, `curator_name`, `curator_slug`
- Denomination: `denomination`, `normalised_denomination`, `denomination_token_address`
- Risk: `risk`, `risk_numeric`, `flags`, `vault_display_flags`, `notes`
- Returns: `one_month_cagr`, `three_months_cagr`, `cagr`, plus `_net` variants
- Samples: `one_month_samples`, `three_months_samples`, `lifetime_samples`
- Size and liquidity: `current_nav`, `peak_nav`, `available_liquidity`, `utilisation`
- Deposit/redemption state: `deposit_closed_reason`, `redemption_closed_reason`, `deposit_next_open`, `redemption_next_open`
- Fees: `management_fee`, `performance_fee`, `deposit_fee`, `withdraw_fee`, `fee_mode`, `fee_label`

For Morpho vault selection, inspect `flags`, `vault_display_flags`, `notes`, and any `core3` fields. Do not include Morpho vaults with red flags such as `deposit_disabled`, `short_timelock`, `illiquid`, blacklisted/critical warnings, or similar red severity annotations.

For cross-chain notebooks, prefer USDC-denominated vaults unless the notebook explicitly supports multiple denominations and matching routing/reserve handling.

## Available scripts

Run Python scripts with Poetry.

```shell
poetry run python scripts/filter-top-vaults.py
poetry run python scripts/filter-top-vaults.py --morpho-vault-flag-ignore red-and-yellow
```

Available vault selection helpers:

- `scripts/filter-top-vaults.py`
  - Baseline top vault selector.
  - Fetches `top_vaults_by_chain.json`.
  - Filters by chain, denomination, TVL, age, risk, flags, and known protocol.
  - Use `--morpho-vault-flag-ignore none|red-only|red-and-yellow` to filter out vaults with matching Morpho display flags.
  - `--morpho-vault-flag-filter` is accepted as a compatibility alias for the same setting.
  - Outputs notebook-ready Python code or JSON with `--json`.
  - Defaults to Ethereum, Base, Arbitrum, Avalanche, Hypercore, HyperEVM, and Monad.
- `scripts/larger-filter-top-vaults.py`
  - Larger-universe variant of `filter-top-vaults.py`.
  - Uses higher per-chain top-N counts and lower default TVL than the baseline.
  - Useful when building broad cross-chain universes.
- `scripts/hyperliquid-filter-top-vaults.py`
  - Hypercore-only selector.
  - Designed for Hyperliquid native vault notebooks.
- `scripts/erc-4626/top-vaults-by-monthly-returns.py`
  - Exploratory script for viewing top monthly-return vaults.
- `scripts/analyse-losing-vault-positions.py`
  - Post-backtest diagnostic helper for losing vault positions.

Shared selection implementation is imported from:

```text
getting_started.vault_universe_creation
```

which aliases:

```text
tradeexecutor.curator.vault_universe_creation
```

When a task has custom criteria that the scripts do not expose, use a short one-off `poetry run python` snippet against `~/.tradingstrategy/vaults/downloads/vault-universe.json`. Keep the criteria explicit in the final answer.

## Existing vault notebooks to look as an example

Cross-chain CCTP notebooks:

- `scratchpad/xchain2/01-initial.ipynb`
- `scratchpad/xchain2/02-initial-cleaned.ipynb`
- `scratchpad/xchain/01-initial.ipynb`
- `scratchpad/xchain/10-backtest-deposit-closed.ipynb`
- `scratchpad/xchain/11-backtest-carry-first.ipynb`

Vault-of-vaults research notebooks:

- `scratchpad/vault-of-vaults/README.md`
- `scratchpad/vault-of-vaults/06-cross-chain-universe.ipynb`
- `scratchpad/vault-of-vaults/13-cross-chain-more-diversified.ipynb`
- `scratchpad/vault-of-vaults/14-cross-hyperliquid.ipynb`
- `scratchpad/vault-of-vaults/77-cross-chain-dual-signal-parameter-tuning.ipynb`
- `scratchpad/vault-of-vaults/129-hyperliquid-final-age-ramp-backtest.ipynb`
- `scratchpad/vault-of-vaults/158-backtest-hyperliquid-waterfall-release-candidate.ipynb`

Other useful examples:

- `scratchpad/bnb-ath-2/04-vault-enabled.ipynb`

Before changing a notebook universe, read the notebook's existing `SOURCE_VAULTS` or `VAULTS` block and its routing assumptions. Some notebooks are USDC-only, some handle Hypercore native vaults, and some rely on CCTP bridge generation.
