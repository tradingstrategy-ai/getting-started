"""Refresh the daily DOEZOE deposit audit from the pinned repaired publication."""

import pandas as pd
import pyarrow.dataset as ds

from tradeexecutor.backtest.backtest_pricing import BacktestPricing
from tradeexecutor.ethereum.vault.hypercore_vault import create_hypercore_vault_pair
from tradeexecutor.state.identifier import AssetIdentifier
from tradingstrategy.alternative_data.vault import convert_vault_prices_to_vault_state, HYPERCORE_DEPOSIT_STATE_CUTOFF
from tradingstrategy.candle import GroupedCandleUniverse

from repaired_data_replay import RESEARCH_DIR, RUN_ROOT
from score_matrix_analysis import markdown_table


def main():
    """Compare recorded flags with actual admission, retaining missing policy data."""
    address = "0xcae0d1558b70b92ee9fd0acb20cb639c8c28ae69"
    raw = (
        ds.dataset(RUN_ROOT / "inputs/vault-prices.parquet")
        .to_table(
            filter=(ds.field("chain") == 9999) & (ds.field("address") == address),
        )
        .to_pandas(ignore_metadata=True)
    )
    state = convert_vault_prices_to_vault_state(raw, "1d")
    pricing = BacktestPricing(GroupedCandleUniverse.create_empty(), None, data_delay_tolerance=pd.Timedelta(days=2), vault_state=state)
    pair = create_hypercore_vault_pair(AssetIdentifier(999, "0x" + "2" * 40, "USDC", 6), address, internal_id=int(state.pair_id.iloc[0]))
    days = pd.date_range("2026-01-01", raw.timestamp.max().normalize())
    counts = raw.groupby(raw.timestamp.dt.normalize()).size()
    rows = []
    for day in days:
        selected = pricing._lookup_vault_state(day, pair)
        selected = {} if selected is None else selected
        gate = pricing.check_deposit(day, pair)
        assert pricing.can_deposit(day, pair) == gate.can_deposit
        flag = selected.get("deposits_open")
        status = "Unknown" if flag is None or pd.isna(flag) or flag == -1 else "Open" if bool(flag) else "Closed"
        display_value = lambda value: "NULL" if value is None or pd.isna(value) else str(value)
        rows.append({"Day (UTC)": str(day.date()), "Price rows": int(counts.get(day, 0)), "Permission": status, "Admission": "Assumed open" if day < HYPERCORE_DEPOSIT_STATE_CUTOFF and gate.can_deposit else "Allowed" if gate.can_deposit else "Blocked", "Reason": str(gate.reason_code), "Leader share": display_value(selected.get("leader_fraction")), "Policy cap (USD)": display_value(selected.get("max_deposit")), "Original permission time": display_value(selected.get("permission_observed_at")), "Independent capacity time": display_value(selected.get("capacity_observed_at")), "Provenance": display_value(selected.get("permission_provenance"))})
    frame = pd.DataFrame(rows)
    frame.to_csv(RUN_ROOT / "doezoe-daily-admission.csv", index=False)
    september = frame[frame["Day (UTC)"].between("2026-09-13", "2026-09-26")]
    note = (
        "# DOEZOE daily deposit status after leader-share recovery\n\n"
        "This audit uses the pinned 7 October publication and the merged trading-strategy/executor readers. "
        "It calls both actual deposit-admission APIs at midnight UTC. Price rows count projected observations, not independent permission receipts. "
        "Open permission and a zero policy cap are separate facts; missing values remain NULL. Before 11 April the source applies its established assumed-open policy. "
        "The independent permission endpoint returned HTTP 404, so this report uses the published price projection.\n\n"
        "## September transition\n\nOriginal permission clocks determine age; publication and repeated price updates do not refresh them. "
        "A missing independent capacity clock does not remove a recorded share or explicit policy cap.\n\n" + markdown_table(september) + "\n\n<details>\n<summary>One row per day for all available 2026 dates</summary>\n\n" + markdown_table(frame) + "\n\n</details>\n\n"
        "[Backtest rerun and input hashes](restored-data-rerun-2026-10-07.md).\n"
    )
    (RESEARCH_DIR / "doezoe-deposit-status.md").write_text(note)
    print(september[["Day (UTC)", "Permission", "Admission", "Policy cap (USD)"]].to_string(index=False))
    print(f"Saved {len(frame)} daily rows; admission APIs agree throughout.")


if __name__ == "__main__":
    main()
