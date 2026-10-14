"""Audit sparse-data handling across the nine Hyperliquid research notebooks."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
GENERATION = ROOT / "_artifacts-restored-2026-10-07"
PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"


def audit():
    """Measure gaps at metric inputs, preserving real observation provenance."""
    prices = pd.read_parquet(GENERATION / "08/prices.parquet")
    source = prices.pivot(index="date", columns="pair_id", values="source_close").sort_index()
    source = source.reindex(pd.date_range(source.index.min(), source.index.max()))
    positive = source.where(source > 0)
    started = positive.notna().cummax()
    interior_gaps = started & positive.isna()
    filled = positive.ffill()
    assert not interior_gaps.any().any(), "Existing framework-fed metric panels contain gaps after first NAV"
    assert np.allclose(positive.to_numpy(), filled.to_numpy(), equal_nan=True)
    #: Earlier scoring, variance and covariance consume these same filled candles.
    returns = positive.pct_change(fill_method=None)
    expected_returns = filled.pct_change(fill_method=None)
    assert np.allclose(returns.to_numpy(), expected_returns.to_numpy(), equal_nan=True)
    actual = prices.pivot(index="date", columns="pair_id", values="supported_daily_mark").reindex_like(source).astype("boolean").fillna(False).astype(bool)
    old = pd.read_parquet(GENERATION / "09-before-sparse-fill/features.parquet")
    new = pd.read_parquet(GENERATION / "09/features.parquet")
    old = old[old.origin_at.ge("2026-01-01") & old.phase.eq(0) & old.anchor_supported]
    aligned = new.set_index(["origin_at", "pair_id"]).reindex(old.set_index(["origin_at", "pair_id"]).index)
    columns = ["30d CAGR", "30d Sharpe", "30d Sortino", "30d Max drawdown", "30d Calmar", "30d K-ratio", "360d K-ratio", "max K-ratio"]
    coverage = pd.DataFrame({"Feature": columns, "Actual-anchor rows": len(old), "Before finite fraction": old[columns].notna().mean().to_numpy(), "After finite fraction (same rows)": aligned[columns].notna().mean().to_numpy()})
    result = {"coverage_comparison_period": PERIOD, "source_audit_period": [str(source.index.min()), str(source.index.max())], "source_vaults": source.shape[1], "source_calendar_days": len(source), "source_missing_marks_after_first_positive_NAV": int(interior_gaps.sum().sum()), "extra_forward_fill_changes_existing_source_candles": False, "source_returns_match_explicit_daily_forward_fill": True, "actual_daily_marks": int(actual.sum().sum()), "source_carried_daily_marks": int((started & ~actual).sum().sum()), "audited_metrics": ["CAGR", "Sharpe", "Sortino", "maximum drawdown", "Calmar", "K-ratio", "inverse variance", "regularised volatility", "correlation/covariance", "EWMA volatility", "autocorrelation", "variance ratio", "weekly K", "BTC/ETH beta and residuals"], "scope": "NB01–NB09 metric inputs and supporting research modules; not every unrelated repository notebook"}
    destination = GENERATION / "sparse-metrics-audit"
    destination.mkdir(exist_ok=True)
    coverage.to_csv(destination / "same-anchor-coverage.csv", index=False)
    (destination / "audit.json").write_text(json.dumps(result, indent=2))
    return result, coverage


if __name__ == "__main__":
    result, coverage = audit()
    print(json.dumps(result, indent=2))
    print(coverage.to_string(index=False))


def refresh_foregone_targets(data, execution):
    """Recompute foregone NAV outcomes without changing frozen portfolio paths.

    The economic state cache retains its original actual-endpoint diagnostic.
    This derived layer replaces the notebook summary and writes separately
    fingerprinted labels, so it cannot change trading or portfolio results.
    """
    import hashlib

    prices = data["prices"]
    nav = prices.pivot(index="date", columns="pair_id", values="raw_close").sort_index()
    calendar = pd.date_range(nav.index.min(), nav.index.max())
    nav = nav.reindex(calendar).ffill()
    actual = prices.pivot(index="date", columns="pair_id", values="supported_daily_mark").reindex_like(nav).astype("boolean").fillna(False).astype(bool)
    clocks = prices.pivot(index="date", columns="pair_id", values="observed_at").reindex_like(nav).ffill()
    last = prices[prices.supported_daily_mark].groupby("pair_id").date.max()
    summaries = []
    label_frames = []
    for record in execution["manifest"].to_dict("records"):
        folder = Path(record["Artefact directory"])
        ledger = pd.read_csv(folder / "allocations.csv")
        if ledger.empty:
            continue
        rejected = ledger[ledger.Rejected].copy()
        rows = []
        for index, row in rejected.iterrows():
            pid = int(row["Pair id"])
            anchor = pd.Timestamp(row["Date"]).normalize() - pd.Timedelta(days=1)
            endpoint = anchor + pd.Timedelta(days=30)
            marks = nav[pid].reindex([anchor, endpoint])
            known = actual[pid].reindex([anchor, endpoint]).fillna(False)
            supported = bool(marks.notna().all() and marks.gt(0).all() and endpoint <= last.get(pid, pd.Timestamp.min) and endpoint < pd.Timestamp("2026-10-05"))
            outcome = float(marks.iloc[-1] / marks.iloc[0] - 1) if supported else np.nan
            if supported:
                assert clocks.loc[anchor, pid] < anchor + pd.Timedelta(days=1)
                assert clocks.loc[endpoint, pid] < endpoint + pd.Timedelta(days=1)
            rows.append({"ledger_index": index, "Date": row["Date"], "Pair id": pid, "Foregone 30d gross return": outcome, "Foregone 30d gross marked PnL (USD)": float(row["Rejected target (USD)"]) * outcome, "Foregone target status": ("actual raw endpoints" if known.all() else "causally carried raw endpoints") if supported else "prelaunch/terminal/censored", "Foregone anchor at": anchor, "Foregone target at": endpoint, "Foregone actual endpoint count": int(known.sum()), "Foregone valuation source": "positive raw NAV; causal daily carry; no leading backfill or terminal extension"})
        if not rows:
            continue
        labels = pd.DataFrame(rows)
        labels.to_csv(folder / "sparse-foregone-labels.csv", index=False)
        identity = {key: record[key] for key in ("Period", "Method", "Positions", "Threshold policy", "Treatment", "Seed")}
        label_frames.append(labels.assign(**identity))
        summaries.append({**identity, "Rejected proposals": len(labels), "Matured foregone labels": int(labels["Foregone 30d gross return"].notna().sum()), "Carried endpoint labels": int(labels["Foregone target status"].eq("causally carried raw endpoints").sum()), "Foregone 30d gross return, unweighted": float(labels["Foregone 30d gross return"].mean()), "Foregone 30d gross marked PnL (USD)": float(labels["Foregone 30d gross marked PnL (USD)"].sum(min_count=1))})
    result = dict(execution)
    result["rejected_outcomes"] = pd.DataFrame(summaries)
    destination = GENERATION / "08/execution"
    result["rejected_outcomes"].to_csv(destination / "rejected_outcomes.csv", index=False)
    if label_frames:
        pd.concat(label_frames, ignore_index=True).to_parquet(destination / "sparse-foregone-labels.parquet", index=False)
    (destination / "sparse-foregone-manifest.json").write_text(json.dumps({"data_fingerprint": data["provenance"]["fingerprint"], "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "portfolio_arms": len(execution["manifest"]), "economic_paths_unchanged": True, "source_observation_policy": "Causal daily positive NAV carry; no leading backfill or labels after last actual mark/archive end"}, indent=2))
    return result
