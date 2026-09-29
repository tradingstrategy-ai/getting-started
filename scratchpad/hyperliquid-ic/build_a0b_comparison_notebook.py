from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "08-research-a0b-production-comparison.ipynb"


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source)


def code(source: str):
    return nbf.v4.new_code_cell(source)


cells = [
    markdown("""# A0b production-universe comparison

This is a variant of `07-stable-profit-validation.ipynb`.

The experiment compares the independent forward-filled simulator (A0), the same simulator restricted to the current production-style Hyperliquid vault universe (A0b), and the production candidate. A0b changes only the candidate universe and the documented data-quality blacklist; it does not import the production engine's stateful execution or sizing code. That keeps it useful as an independent data and accounting check.

Two windows are reported:

* the recorded production candidate period, 2026-01-01 through 2026-07-08 inclusive;
* the full completed backfilled research period, 2025-09-13 through 2026-09-12 inclusive.

The archived production report retained headline metrics but not its daily equity series. The notebook therefore plots the two independent daily curves and marks the archived production endpoint; it does not invent a production curve. A current-source production-engine replay is included in the metrics table where an existing verification run recorded it.
"""),
    code("""from pathlib import Path
import json
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_DIR = Path.cwd() / "scratchpad/hyperliquid-ic" if (Path.cwd() / "scratchpad/hyperliquid-ic").exists() else Path.cwd()
sys.path.insert(0, str(PROJECT_DIR))
REWRITE = PROJECT_DIR / "_artifacts-rewrite"
ARTIFACTS = PROJECT_DIR / "_artifacts-a0b"
ARTIFACTS.mkdir(exist_ok=True)

from ic_research import ResearchConfig, summarise_backtest
from stable_profit import simulate_stable_policy

features = pd.read_parquet(REWRITE / "features.parquet")
observations = pd.read_parquet(REWRITE / "observations.parquet")
metadata = pd.read_csv(REWRITE / "vault-metadata.csv", usecols=["address", "name", "vault_slug"])
features["date"] = pd.to_datetime(features["date"]).dt.normalize()
observations["timestamp"] = pd.to_datetime(observations["timestamp"])
observations["address"] = observations["address"].str.lower()
features["address"] = features["address"].str.lower()
metadata["address"] = metadata["address"].str.lower()

UNIVERSE_CACHE = Path("/Users/moo/.cache/indicators/vault-universe-tvl7500-top9999-age0.0-sort1Y-curbbf10d84.json")
production_allowlist = {
    item["address"].lower() for item in json.loads(UNIVERSE_CACHE.read_text())
}
manual_blacklist = {"0x5290ab34acb59cfe1371baa5782eba14433d308f"}
production_style_allowlist = production_allowlist - manual_blacklist

PERIODS = {
    "production_candidate_period": (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-08")),
    "full_backfilled_history": (pd.Timestamp("2025-09-13"), pd.Timestamp("2026-09-12")),
}
CONFIG = ResearchConfig()
print({"features": features.shape, "observations": observations.shape, "production_cache_vaults": len(production_allowlist), "a0b_allowlist_vaults": len(production_style_allowlist)})
"""),
    markdown("""## Definitions and provenance

`A0` uses every address represented in the independent feature panel for the selected dates. `A0b` uses the intersection of that panel with the current cached production universe, excluding the one manual data-quality blacklist entry in `hyper-ai-v6.py` (Scared Money). The cache is a point-in-time snapshot of the production-style `min_tvl=7,500`, `min_age=0`, `top_n=9999` universe; its timestamp and path are written to the manifest.

The recorded production candidate values come from the 2026-08-21 production archive/header. The current-source engine replay values come from `_build/verify-hyperai-window.ipynb`, which used the same current strategy source and current cached data but does not persist its equity series. A missing production equity path is represented as missing data rather than reconstructed from an endpoint.
"""),
    code("""def run_variant(period_name: str, start: pd.Timestamp, end: pd.Timestamp, variant: str):
    period_features = features[features.date.between(start, end)].copy()
    addresses = set(period_features.address)
    if variant == "A0":
        selected_addresses = addresses
    elif variant == "A0b":
        selected_addresses = addresses & production_style_allowlist
    else:
        raise ValueError(variant)
    period_features = period_features[period_features.address.isin(selected_addresses)].copy()
    period_observations = observations[
        observations.timestamp.dt.normalize().between(start, end)
        & observations.address.isin(selected_addresses)
    ].copy()
    equity, trades, pool = simulate_stable_policy(
        period_features,
        period_observations,
        policy_name=variant,
        config=CONFIG,
        max_positions=6,
    )
    equity.to_parquet(ARTIFACTS / f"equity-{variant}-{period_name}.parquet", index=False)
    trades.to_parquet(ARTIFACTS / f"trades-{variant}-{period_name}.parquet", index=False)
    pool.to_parquet(ARTIFACTS / f"pool-{variant}-{period_name}.parquet", index=False)
    metrics = summarise_backtest(equity)
    metrics.update({
        "period": period_name,
        "variant": variant,
        "panel_vaults": len(addresses),
        "simulated_vaults": len(selected_addresses),
        "selected_vaults": int(pool.loc[pool.target_dollars.gt(0), "address"].nunique()) if not pool.empty else 0,
        "equity_curve_available": True,
        "source": "independent forward-filled simulator",
    })
    return equity, trades, pool, metrics


curves = {}
trade_ledgers = {}
pool_ledgers = {}
metric_rows = []
for period_name, (start, end) in PERIODS.items():
    for variant in ("A0", "A0b"):
        curves[(variant, period_name)], trade_ledgers[(variant, period_name)], pool_ledgers[(variant, period_name)], row = run_variant(period_name, start, end, variant)
        metric_rows.append(row)

# Archived production headline metrics for the exact candidate period. The source reported
# 27.76% cumulative return; the endpoint and $150,000 start imply 27.63%, so retain both facts.
metric_rows.extend([
    {
        "period": "production_candidate_period", "variant": "Production candidate (recorded archive)",
        "start": "2026-01-01", "end": "2026-07-08", "final_equity": 191446.1458,
        "cumulative_return": 0.2776, "endpoint_implied_cumulative_return": 191446.1458 / 150000 - 1,
        "cagr": 0.6172, "volatility": np.nan, "sharpe": 2.88, "max_drawdown": -0.0444,
        "equity_curve_available": False, "source": "hyper-ai-v6.py archive/header 2026-08-21",
        "notes": "Daily engine equity series was not retained.",
    },
    {
        "period": "production_candidate_period", "variant": "Production candidate (current-source replay)",
        "start": "2026-01-01", "end": "2026-07-08", "final_equity": 190095.033156,
        "cumulative_return": 0.268543, "cagr": 0.586961,
        "volatility": np.nan, "sharpe": 2.874441, "max_drawdown": -0.039052,
        "equity_curve_available": False, "source": "_build/verify-hyperai-window.ipynb, run 2026-09-15",
        "notes": "Current-source engine replay; only summary output was retained.",
    },
    {
        "period": "full_backfilled_history", "variant": "Production candidate",
        "start": "2025-09-13", "end": "2026-09-12", "final_equity": np.nan,
        "cumulative_return": np.nan, "cagr": np.nan, "volatility": np.nan, "sharpe": np.nan,
        "max_drawdown": np.nan, "equity_curve_available": False,
        "source": "unavailable: matching archived production engine input was not retained",
        "notes": "Do not compare this missing row as a result; A0/A0b are the independent full-history comparison.",
    },
])
metrics = pd.DataFrame(metric_rows)
metrics.to_csv(ARTIFACTS / "a0-a0b-production-metrics.csv", index=False)
display(metrics[["period", "variant", "final_equity", "cumulative_return", "cagr", "volatility", "sharpe", "max_drawdown", "selected_vaults", "equity_curve_available", "source"]].round(4))
"""),
    markdown("""## Equity curves

The production-period plot includes the archived production endpoint as a marker. The independent curves are daily forward-filled equity paths. The full-history panel deliberately has no fabricated production line because its engine series was not retained."""),
    code("""fig, axes = plt.subplots(1, 2, figsize=(17, 5), constrained_layout=True)
for axis, (period_name, (start, end)) in zip(axes, PERIODS.items()):
    for variant, colour in (("A0", "#1f77b4"), ("A0b", "#d62728")):
        curve = curves[(variant, period_name)]
        axis.plot(curve.date, curve.equity / curve.equity.iloc[0], label=variant, color=colour, linewidth=1.8)
    if period_name == "production_candidate_period":
        axis.scatter(
            [end], [191446.1458 / 150000], color="#111111", marker="x", s=70,
            label="Production candidate (recorded endpoint)", zorder=5,
        )
    axis.set_title(period_name.replace("_", " "))
    axis.set_ylabel("equity, normalised to 1.0")
    axis.grid(alpha=0.25)
    axis.legend()
plt.show()
"""),
    markdown("""## Vault inclusion and exclusion

The membership table is built from every address present in either comparison window. `A0` includes an address when it is present in the independent panel. `A0b` additionally requires the production-style allowlist and the blacklist check. `selected_*` records whether the simulator actually allocated a non-zero target at least once in the production candidate period. The complete table is saved as a CSV so excluded addresses can be audited without truncation."""),
    code("""all_addresses = sorted(set(features.address))
name_map = metadata.drop_duplicates("address").set_index("address")
production_selected = {}
for variant in ("A0", "A0b"):
    pool = pool_ledgers[(variant, "production_candidate_period")]
    production_selected[variant] = set(pool.loc[pool.target_dollars.gt(0), "address"]) if not pool.empty else set()

membership = pd.DataFrame({"address": all_addresses})
membership["name"] = membership.address.map(name_map["name"])
membership["vault_slug"] = membership.address.map(name_map["vault_slug"])
membership["in_production_style_allowlist"] = membership.address.isin(production_style_allowlist)
membership["manual_blacklist"] = membership.address.isin(manual_blacklist)
membership["in_A0_panel"] = True
membership["in_A0b_panel"] = membership.in_production_style_allowlist & ~membership.manual_blacklist
membership["selected_A0_production_period"] = membership.address.isin(production_selected["A0"])
membership["selected_A0b_production_period"] = membership.address.isin(production_selected["A0b"])
membership["status"] = np.select(
    [membership.manual_blacklist, ~membership.in_production_style_allowlist, membership.selected_A0b_production_period, membership.selected_A0_production_period],
    ["excluded: manual blacklist", "excluded: outside production-style allowlist", "included and selected by A0b", "included in A0 but not selected by A0b"],
    default="included in A0 panel; not selected",
)
membership.to_csv(ARTIFACTS / "a0-a0b-vault-membership.csv", index=False)
membership_summary = membership.groupby("status", dropna=False).size().rename("vaults").reset_index()
display(membership_summary)
display(membership.sort_values(["status", "name", "address"])[["address", "name", "in_production_style_allowlist", "manual_blacklist", "selected_A0_production_period", "selected_A0b_production_period", "status"]])
"""),
    markdown("""## Stability and concentration checks

The comparison is interpreted as a universe reconciliation, not as a fresh parameter search. The checks below identify whether a close endpoint is driven by a single allocation and report the largest target-dollar contributors. A0b is only considered close to production if the production-period endpoint, drawdown and Sharpe move in the same direction without a single-vault explanation."""),
    code("""concentration_rows = []
for variant in ("A0", "A0b"):
    pool = pool_ledgers[(variant, "production_candidate_period")]
    selected = pool[pool.target_dollars.gt(0)].copy()
    totals = selected.groupby("address").target_dollars.sum().sort_values(ascending=False)
    total = totals.sum()
    concentration_rows.append({
        "variant": variant,
        "selected_vaults": int(len(totals)),
        "top_vault": totals.index[0] if len(totals) else None,
        "top_vault_target_dollars": float(totals.iloc[0]) if len(totals) else np.nan,
        "top_vault_share_of_target": float(totals.iloc[0] / total) if total else np.nan,
        "top5_share_of_target": float(totals.head(5).sum() / total) if total else np.nan,
    })
concentration = pd.DataFrame(concentration_rows)
concentration.to_csv(ARTIFACTS / "a0-a0b-concentration.csv", index=False)
display(concentration.round(4))
for variant in ("A0", "A0b"):
    print(f"{variant} largest contributors")
    display(
        pool_ledgers[(variant, "production_candidate_period")]
        .query("target_dollars > 0")
        .groupby("address", as_index=False)["target_dollars"].sum()
        .sort_values("target_dollars", ascending=False)
        .head(10)
        .merge(metadata, on="address", how="left")
    )
"""),
    code("""manifest = {
    "variant": "A0b",
    "source_notebook": "07-stable-profit-validation.ipynb",
    "universe_cache": str(UNIVERSE_CACHE),
    "universe_cache_mtime": pd.Timestamp(UNIVERSE_CACHE.stat().st_mtime, unit="s").isoformat(),
    "production_allowlist_count": len(production_allowlist),
    "manual_blacklist": sorted(manual_blacklist),
    "a0_definition": "all independent feature-panel addresses in the period",
    "a0b_definition": "A0 with current production-style allowlist and manual blacklist",
    "periods": {name: [str(start.date()), str(end.date())] for name, (start, end) in PERIODS.items()},
    "forward_fill": True,
    "max_positions": 6,
    "production_curve_note": "Archived production series was not retained; endpoint-only marker used.",
}
(ARTIFACTS / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\\n")
print(json.dumps(manifest, indent=2))
"""),
]

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "pygments_lexer": "ipython3"},
}
nbf.write(nb, OUTPUT)
print(OUTPUT)
