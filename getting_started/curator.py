"""Curated vault lists for vault-of-vault filtering scripts."""

import datetime
import enum

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
    # Hyperliquidity Trader (HLT) on Hypercore - unstable share price action
    "0x5a733b25a17dc0f26b862ca9e32b439801b1a8c7",
    # BitCorn50xLong on Hypercore
    "0x368eafa587cdc5b5f79eb40eae18c62286ab8f9d",
    # HyperTwin - Blue Whale on Hypercore - no copy trading
    "0x9a3006e0b7ffacf11729103098ff16fa6e17bd24",
    # Test vault on Hypercore
    "0x4692441b5a9e26a690eea6d2f36139679add737b",
    # AILab Test Ultra 2 on Hypercore - test vault
    "0x780825f3f0ad6799e304fb843387934c1fa06e70",
    "0x21edf2d791f626ee69352120e7f6e2fbb0f48cf1",
    # Overdose on Hypercore - erratic profits
    "0xe67dbf2d051106b42104c1a6631af5e5a458b682",
}

# Protocols to exclude (output as commented-out lines with reason)
EXCLUDED_PROTOCOLS = {
    "accountable": "Assets are illiquid for strategies",
}

# Quarantine periods: vaults with unreliable price data during specific windows.
# Format: (address, start_date, end_date, reason)
# Vaults are excluded from trading signals during quarantine but remain in the universe.
QUARANTINE_PERIODS = [
    # Satori Quantum HF Vault - 164% share price spike on 2025-10-15,
    # then sustained at ~3.5x until crash in Feb 2026.
    (
        "0xbbf7d7a9d0eaeab4115f022a6863450296112422",
        datetime.datetime(2025, 10, 1),
        datetime.datetime(2026, 2, 15),
        "Share price spike 164% on 2025-10-15, unreliable price data",
    ),
]


class VaultQuality(enum.Enum):
    """Quality tier for Hyperliquid vaults, used for concentration tweaks."""
    gold = "gold"
    high = "high"
    medium = "medium"


# Manually curated address -> quality mapping for known good Hyperliquid vaults
_HYPERLIQUID_QUALITY_MAP: dict[str, VaultQuality] = {
    # Gold: HLP
    "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303": VaultQuality.gold,
    # High: [ Systemic Strategies ] L/S Grids
    "0x07fd993f0fa3a185f7207adccd29f7a87404689d": VaultQuality.high,
    # High: Growi HF
    "0x1e37a337ed460039d1b15bd3bc489de789768d5e": VaultQuality.high,
    # High: pmalt
    "0x4dec0a851849056e259128464ef28ce78afa27f6": VaultQuality.high,
    # High: L/S Momentum Strategy
    "0x394c57ac43a9cbd5fffce1c7e681c650154a2b0b": VaultQuality.high,
    # High: Satori Quantum HF Vault
    "0xbbf7d7a9d0eaeab4115f022a6863450296112422": VaultQuality.high,
    # High: Satori Quantum Vault
    "0x149b47e62de45cd73b67054eaca8d2e77bab4c38": VaultQuality.high,
    # Medium: Delta Neutral | R Tech
    "0xf182de5226dc4fe2f134c9b375281a6f50309416": VaultQuality.medium,
    # Medium: Loop Fund
    "0xfeab64de8cdf9dcebc0f49812499e396273efc06": VaultQuality.medium,
    # Medium: Nero Quant Capital
    "0x497f213095ca5dc149cc1e03caf0338b5fe4a3f9": VaultQuality.medium,
}

def get_hyperliquid_concentration_tweak() -> dict[str, VaultQuality]:
    """Return address -> VaultQuality for Hyperliquid vaults known to be good.

    Used to give higher max concentration to trusted vaults.
    Manually curated — update ``_HYPERLIQUID_QUALITY_MAP`` to add new vaults.

    :return:
        Dict of lowercase address -> VaultQuality.
    """
    return dict(_HYPERLIQUID_QUALITY_MAP)


def is_quarantined(address: str, timestamp: datetime.datetime) -> bool:
    """Check if a vault address is quarantined at a given timestamp."""
    address = address.lower()
    for q_address, q_start, q_end, _reason in QUARANTINE_PERIODS:
        if q_address.lower() == address and q_start <= timestamp <= q_end:
            return True
    return False
