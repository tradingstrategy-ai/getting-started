"""Independent raw-observation checks for the forecast notebook's target labels."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds


def independent_label_audit(data, folder, sample_count=50):
    """Recompute sampled targets directly from raw rows, independently of shifts.

    Carry the latest actual NAV on the daily calendar without backfilling.
    Censor endpoints beyond the last actual observation. Actual timestamps
    remain the provenance of carried marks; archive write dates are not used.
    """
    folder = Path(folder)
    labels = data["labels"]
    primary = labels[labels.lookahead_days.isin([7, 30, 90]) & labels.delay_days.eq(0)]
    selections = []
    for (h, status), group in primary.groupby(["lookahead_days", "target_status"], observed=True):
        selections.append(group.sample(min(1, len(group)), random_state=108 + h))
    delayed = labels[labels.lookahead_days.isin([7, 30, 90]) & labels.delay_days.isin([1, 2]) & np.isfinite(labels.future_log_return)]
    for (h, delay), group in delayed.groupby(["lookahead_days", "delay_days"]):
        selections.append(group.sample(min(1, len(group)), random_state=108 + h + delay))
    guarded_ids = data["prices"].loc[data["prices"].price_guard_divergence, "pair_id"].unique()
    collapsed = primary[primary.pair_id.isin(guarded_ids) & np.isfinite(primary.future_log_return)].sort_values("future_log_return")
    selections.append(collapsed.groupby("pair_id", sort=False).head(1))
    supported = primary[np.isfinite(primary.future_log_return)]
    selections.append(supported.sample(min(sample_count, len(supported)), random_state=108))
    chosen = pd.concat(selections).drop_duplicates(["origin_at", "pair_id", "lookahead_days", "delay_days"]).head(sample_count)
    addresses = data["prices"][["pair_id", "vault_address"]].drop_duplicates().set_index("pair_id").vault_address
    wanted = addresses.reindex(chosen.pair_id.unique()).dropna().tolist()
    source = data["provenance"]["inputs"]["vault_prices"]["path"]
    dataset = ds.dataset(source, format="parquet")
    raw = dataset.to_table(columns=["timestamp", "address", "share_price"], filter=(ds.field("chain") == 9999) & ds.field("address").isin(wanted)).to_pandas().reset_index()
    raw["timestamp"] = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(None)
    raw["date"] = raw.timestamp.dt.floor("D")
    raw = raw[np.isfinite(raw.share_price) & raw.share_price.gt(0)]
    raw = raw.sort_values(["address", "timestamp"], kind="stable")
    daily = raw.groupby(["address", "date"], sort=False).tail(1).set_index(["address", "date"])
    rows = []
    for record in chosen.to_dict("records"):
        address = addresses.loc[record["pair_id"]]
        origin = pd.Timestamp(record["origin_at"])
        h = int(record["lookahead_days"])
        delay = int(record["delay_days"])
        anchor = origin - pd.Timedelta(days=1) + pd.Timedelta(days=delay)
        endpoint = anchor + pd.Timedelta(days=h)
        assert pd.Timestamp(record["nav_anchor_at"]) == anchor
        assert pd.Timestamp(record["nav_target_at"]) == endpoint
        if "label_available_at" in record:
            assert pd.Timestamp(record["label_available_at"]) == endpoint + pd.Timedelta(days=1)
        administratively_valid = endpoint < pd.Timestamp("2026-10-05")
        path = pd.date_range(anchor, endpoint)
        if address in daily.index.get_level_values(0):
            marks = daily.loc[address].sort_index()
            calendar = pd.date_range(marks.index.min(), max(endpoint, marks.index.max()))
            observed = marks.reindex(calendar).ffill().reindex(path)
            nav = observed.share_price
            if endpoint > marks.index.max():
                nav = nav * np.nan
        else:
            observed = pd.DataFrame(index=path, columns=["share_price", "timestamp"])
            nav = observed.share_price.astype(float)
        endpoints_good = administratively_valid and pd.notna(nav.iloc[0]) and pd.notna(nav.iloc[-1])
        return_value = float(nav.iloc[-1] / nav.iloc[0] - 1) if endpoints_good else np.nan
        log_value = float(np.log(nav.iloc[-1]) - np.log(nav.iloc[0])) if endpoints_good else np.nan
        complete = endpoints_good and nav.notna().all()
        daily_returns = np.diff(nav.to_numpy(dtype=float)) / nav.to_numpy(dtype=float)[:-1] if complete else np.array([])
        sigma = daily_returns.std(ddof=1) if len(daily_returns) > 1 else np.nan
        sharpe = float(np.mean(daily_returns) / sigma * np.sqrt(365)) if np.isfinite(sigma) and sigma > 0 else np.nan
        with np.errstate(over="ignore"):
            cagr = float(np.expm1(log_value * 365 / h)) if endpoints_good else np.nan
        if not np.isfinite(cagr):
            cagr = np.nan
        candidates = [("future_return", return_value), ("future_log_return", log_value), ("future_cagr", cagr), ("future_sharpe", sharpe)]
        matches = {}
        errors = {}
        for target, recomputed in candidates:
            actual = float(record[target])
            matches[target] = bool((np.isnan(actual) and np.isnan(recomputed)) or np.isclose(actual, recomputed, atol=1e-9, rtol=1e-9))
            errors[target] = abs(actual - recomputed) if np.isfinite(actual) and np.isfinite(recomputed) else np.nan
        clocks_good = True
        if endpoints_good:
            clocks_good = bool(observed.timestamp.iloc[0] < origin + pd.Timedelta(days=delay) and observed.timestamp.iloc[-1] < endpoint + pd.Timedelta(days=1))
        row = {"origin_at": origin, "pair_id": record["pair_id"], "vault_address": address, "lookahead_days": h, "delay_days": delay, "status": record["target_status"], "raw_endpoint_support": bool(endpoints_good), "supported_calendar_path": bool(complete), "observation_clocks_match": clocks_good, **{k + "_matches": v for k, v in matches.items()}, **{k + "_absolute_error": v for k, v in errors.items()}}
        rows.append(row)
    frame = pd.DataFrame(rows)
    checks = [c for c in frame if c.endswith("_matches")]
    assert frame[checks].all().all(), frame.loc[~frame[checks].all(axis=1)].to_dict("records")
    assert frame.observation_clocks_match.all(), "Raw observation clock violation"
    report = {"samples": len(frame), "all_targets_match": True, "complete_paths": int(frame.supported_calendar_path.sum()), "endpoint_only_paths": int((frame.raw_endpoint_support & ~frame.supported_calendar_path).sum()), "unsupported_or_censored_paths": int((~frame.raw_endpoint_support).sum()), "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "data_fingerprint": data["provenance"]["fingerprint"]}
    frame.to_csv(folder / "independent-label-audit.csv", index=False)
    (folder / "independent-label-audit.json").write_text(json.dumps(report, indent=2))
    return frame, report
