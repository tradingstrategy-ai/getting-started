"""Compare published HyperCore inputs across the two authorised repair reruns."""

import json
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

from repaired_data_replay import RUN_ROOT, RESEARCH_DIR


def main():
    """Record matched policy/economic changes without modifying either archive."""
    columns = ["address", "timestamp", "share_price", "total_assets", "total_supply", "written_at", "leader_fraction", "max_deposit", "deposits_open", "permission_observed_at", "capacity_observed_at"]
    sources = {
        "Before leader repair": RESEARCH_DIR / "_artifacts-repaired-2026-10-07/inputs/vault-prices.parquet",
        "Restored publication": RUN_ROOT / "inputs/vault-prices.parquet",
    }
    frames = {}
    summary = []
    for label, path in sources.items():
        frame = ds.dataset(path).to_table(columns=columns, filter=ds.field("chain") == 9999).to_pandas(ignore_metadata=True)
        assert not frame.duplicated(["address", "timestamp"]).any()
        frames[label] = frame.set_index(["address", "timestamp"])
        for period, mask in [("All published history", pd.Series(True, index=frame.index)), ("2026-01-01 to 2026-10-05 exclusive", frame.timestamp.between("2026-01-01", "2026-10-05", inclusive="left"))]:
            part = frame.loc[mask]
            summary.append({"Generation": label, "Period": period, "Rows": len(part), "Known leader shares": int(part.leader_fraction.notna().sum()), "Known caps": int(part.max_deposit.notna().sum()), "Zero caps": int(part.max_deposit.eq(0).sum()), "Independent capacity clocks": int(part.capacity_observed_at.notna().sum())})
    before, after = frames.values()
    keys = before.index.intersection(after.index)
    a, b = before.loc[keys], after.loc[keys]
    changes = []
    for column in a:
        same = a[column].eq(b[column]) | (a[column].isna() & b[column].isna())
        changes.append({"Field": column, "Matched rows": len(keys), "Changed": int((~same).sum()), "NULL to known": int((a[column].isna() & b[column].notna()).sum()), "Known to NULL": int((a[column].notna() & b[column].isna()).sum()), "Changed known values": int((a[column].notna() & b[column].notna() & ~same).sum())})
    pd.DataFrame(summary).to_csv(RUN_ROOT / "input-policy-counts.csv", index=False)
    pd.DataFrame(changes).to_csv(RUN_ROOT / "matched-input-changes.csv", index=False)
    (RUN_ROOT / "input-row-audit.json").write_text(
        json.dumps(
            {
                "matched": len(keys),
                "new": len(after.index.difference(before.index)),
                "removed": len(before.index.difference(after.index)),
            },
            indent=2,
        )
    )
    print(pd.DataFrame(summary).to_string(index=False))
    print(pd.DataFrame(changes).to_string(index=False))


if __name__ == "__main__":
    main()
