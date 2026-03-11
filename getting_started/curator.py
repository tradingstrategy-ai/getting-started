"""Curated vault lists for vault-of-vault filtering scripts."""

# Vaults that must always be included (by address lowercase)
MUST_INCLUDE = {
    # Ostium on Arbitrum
    "0x20d419a8e12c45f88fda7c5760bb6923cee27f98",
    # Growi HF on Hypercore
    "0x1e37a337ed460039d1b15bd3bc489de789768d5e",
    # Hyperliquidity Provider (HLP) on Hypercore
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
}

# Vaults to exclude (output as commented-out lines)
EXCLUDED_VAULTS = {
    # Elsewhere on Hypercore
    "0x8fc7c0442e582bca195978c5a4fdec2e7c5bb0f7",
    # Sifu on Hypercore
    "0xf967239debef10dbc78e9bbbb2d8a16b72a614eb",
    # Long LINK Short XRP on Hypercore
    "0x73ce82fb75868af2a687e9889fcf058dd1cf8ce9",
    # Wrapped HLP on HyperEVM (we have native HLP)
    "0x06fd9d03b3d0f18e4919919b72d30c582f0a97e5",
    # BTC/ETH CTA | AIM on Hypercore
    "0xbeebbbe817a69d60dd62e0a942032bc5414dae1c",
    # Sentiment Edge on Hypercore
    "0xb7e7d0fdeff5473ed6ef8d3a762d096a040dbb18",
    # Sentiment Edge on Hypercore
    "0x026a2e082a03200a00a97974b7bf7753ce33540f",
    # ski lambo beach on Hypercore
    "0x66e541024ca4c50b8f6c0934b8947c487d211661",
    # BULBUL2DAO on Hypercore
    "0x65aee08c9235025355ac6c5ad020fb167ecef4fe",
    # Cryptoaddcited on Hypercore
    "0x5108cd0a328ed28c277f958761fe1cda60c21aa8",
    # hidden marko fund on Hypercore
    "0xc497f1f8840dd65affbab1a610b6e558844743d4",
    # Crypto_Lab28 on Hypercore
    "0xb11fe7f2e97bd02b2da909b32f4a5e7fcb0df099",
    # Jade Lotus Capital on Hypercore
    "0xbc5bf88fd012612ba92c5bd96e183955801b7fdc",
    # MOAS on Hypercore
    "0x29b98aaf8eeb316385fe2ed1af564bdc4b03ffd6",
    # Long HYPE & BTC | Short Garbage on Hypercore
    "0xac26cf5f3c46b5e102048c65b977d2551b72a9c7",
    # HyperTwin - Growi HF 2x on Hypercore
    "0x15be61aef0ea4e4dc93c79b668f26b3f1be75a66",
    # +convexity on Hypercore
    "0x5661a070eb13c7c55ac3210b2447d4bea426cbf5",
}

# Protocols to exclude (output as commented-out lines with reason)
EXCLUDED_PROTOCOLS = {
    "accountable": "Assets are illiquid for strategies",
}
