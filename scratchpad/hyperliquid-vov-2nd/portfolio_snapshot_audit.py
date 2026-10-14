"""Independent reconstruction and numerical checks for experiment 10.

Expected values in this module use a separately read original archive and
straightforward pandas/NumPy arithmetic. They do not call production path,
risk or allocation helpers to construct their expected answers.
"""

import hashlib
import json
import contextlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent
GENERATION = ROOT / "_artifacts-restored-2026-10-07"
END = pd.Timestamp("2026-10-05")


def independent_calendar(addresses, downloads=None):
    """Read final valid daily marks directly from the pinned original archive."""
    if downloads is None:
        downloads = json.loads((GENERATION / "inputs/downloads.json").read_text())
    path = Path(downloads["vault_prices"]["path"])
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    assert digest == downloads["vault_prices"]["sha256"], "Original archive fingerprint changed"
    table = ds.dataset(path, format="parquet").to_table(columns=["timestamp", "address", "share_price"], filter=(ds.field("chain") == 9999) & ds.field("address").isin(list(addresses)))
    raw = table.to_pandas().reset_index()
    raw["timestamp"] = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(None)
    rejected = raw[~np.isfinite(raw.share_price) | raw.share_price.le(0)].copy()
    raw = raw[np.isfinite(raw.share_price) & raw.share_price.gt(0) & raw.timestamp.lt(END)].copy()
    raw["date"] = raw.timestamp.dt.floor("D")
    raw = raw.sort_values(["address", "timestamp"], kind="stable")
    daily = raw.groupby(["address", "date"], sort=False).tail(1)
    series = {}
    for address, group in daily.groupby("address", sort=False):
        marks = group.set_index("date")[["share_price", "timestamp"]].sort_index()
        calendar = pd.date_range(marks.index.min(), END - pd.Timedelta(days=1))
        actual = marks.reindex(calendar)
        carried = actual.ffill()
        carried["actual"] = actual.share_price.notna()
        series[address] = {"daily": carried, "first": marks.index.min(), "last": marks.index.max()}
    return series, rejected


def independent_path(series, origin, horizon):
    """Build one censored held-NAV path, retaining its real mark provenance."""
    anchor = pd.Timestamp(origin) - pd.Timedelta(days=1)
    target = anchor + pd.Timedelta(days=int(horizon))
    dates = pd.date_range(anchor, target)
    if series is None:
        return {"resolved": False, "reason": "no_positive_nav", "path": np.full(len(dates), np.nan)}
    values = series["daily"].reindex(dates)
    nav = values.share_price.to_numpy(dtype=float)
    supported = target < END and target <= series["last"] and np.isfinite(nav).all()
    if not supported:
        return {"resolved": False, "reason": "terminal_or_leading_or_administrative", "path": nav}
    returns = nav[1:] / nav[:-1] - 1
    variance = np.var(returns, ddof=1)
    actual = values.actual.eq(True).to_numpy(dtype=bool)
    first = 0 if actual[0] else next((k for k in range(1, len(actual)) if actual[k]), None)
    first_component = (nav[first] - nav[0]) / nav[0] if first is not None else np.nan
    remaining = (nav[-1] - nav[first]) / nav[0] if first is not None else np.nan
    return {"resolved": True, "reason": "resolved", "path": nav, "return": nav[-1] / nav[0] - 1, "variance": variance, "actual_updates": int(actual[1:].sum()), "first_update_component": first_component, "remaining_mark_component": remaining, "anchor_observed_at": values.timestamp.iloc[0], "target_observed_at": values.timestamp.iloc[-1]}


def independent_empirical(series, origin, lookback):
    """Use an elapsed calendar segment and actual updates, including carried anchors."""
    anchor = pd.Timestamp(origin) - pd.Timedelta(days=1)
    start = anchor - pd.Timedelta(days=int(lookback))
    if series is None or series["first"] > anchor:
        return {"empirical_variance": np.nan, "calendar_returns": 0, "actual_updates": 0}
    start = max(start, series["first"])
    marks = series["daily"].loc[start:anchor]
    nav = marks.share_price.to_numpy(dtype=float)
    n = len(nav) - 1
    m = int(marks.actual.iloc[1:].sum())
    actual_times = marks.timestamp.dropna().dt.floor("D").unique()
    supported = n >= 2 and len(actual_times) >= 2 and m >= 1 and np.isfinite(nav).all()
    variance = np.var(nav[1:] / nav[:-1] - 1, ddof=1) if supported else np.nan
    return {"empirical_variance": variance, "calendar_returns": n, "actual_updates": m}


def independent_units(prices, weights, cash=0.0):
    """Hand-style fixed-unit arithmetic, with original notional retained."""
    prices = np.asarray(prices, dtype=float)
    weights = np.asarray(weights, dtype=float)
    path = cash + (prices / prices[0] * weights).sum(axis=1)
    daily = path[1:] / path[:-1] - 1
    return {"path": path, "return": path[-1] - 1.0, "variance": np.var(daily, ddof=1), "max_drawdown": np.min(path / np.maximum.accumulate(path) - 1.0)}


def reference_checks():
    """Verify independent expectations on deliberately adverse tiny fixtures."""
    calendar = pd.date_range("2026-01-01", periods=8)
    raw = pd.Series([np.nan, 10.0, np.nan, np.nan, 12.0, np.nan, 12.0, np.nan], index=calendar)
    marks = pd.DataFrame({"share_price": raw, "timestamp": calendar.where(raw.notna()), "actual": raw.notna()})
    marks[["share_price", "timestamp"]] = marks[["share_price", "timestamp"]].ffill()
    series = {"daily": marks, "first": calendar[1], "last": calendar[6]}
    assert np.isnan(marks.share_price.iloc[0])
    expected = independent_empirical(series, calendar[7], 5)
    assert expected["calendar_returns"] == 5 and expected["actual_updates"] == 2
    assert independent_path(series, calendar[5], 2)["resolved"]
    assert not independent_path(series, calendar[5], 3)["resolved"]
    single = {"daily": marks.assign(share_price=10.0, timestamp=calendar[1], actual=False), "first": calendar[1], "last": calendar[1]}
    assert np.isnan(independent_empirical(single, calendar[7], 5)["empirical_variance"])
    prices = np.array([[1.0, 1.0], [2.0, 0.5], [1.0, 1.0]])
    fixed = independent_units(prices, [0.5, 0.5])
    constant_mix = np.prod(1 + ((prices[1:] / prices[:-1] - 1) * [0.5, 0.5]).sum(axis=1)) - 1
    assert fixed["return"] == 0 and np.isclose(constant_mix, 0.5625)
    zero_qlike = np.log(0.02) + 0 / 0.02
    assert np.isfinite(zero_qlike)
    w = np.array([0.6, 0.3, 0.1])
    realised = np.array([0.2, -0.1, 0.3])
    active = w - 1 / 3
    assert np.isclose(active @ realised, 3 * np.cov(active, realised, ddof=0)[0, 1])
    return [{"check": "Independent adverse fixture expectations", "status": "pass", "detail": "Leading gap; carried-anchor actual counts; terminal censoring; fixed units ≠ daily mixing; zero QLIKE; covariance identity"}]


def audit_archive_panel(data, artefact_dir):
    """Reconstruct a stratified original-archive sample without the main reader.

    :param data: Shared panel containing ``nav``, ``raw_nav``, ``observed`` and identities.
    :param artefact_dir: Ignored audit output directory.
    """
    nav, raw_nav, observed = data["nav"], data["raw_nav"], data["observed"]
    identities = data["identities"].set_index("pair_id")
    actual_counts = raw_nav.notna().sum()
    first = raw_nav.apply(lambda s: s.first_valid_index())
    last = raw_nav.apply(lambda s: s.last_valid_index())
    minimum = raw_nav.min()
    picked = set(actual_counts.sort_values().head(4).index)
    picked.update(minimum.sort_values().head(4).index)
    picked.update(first.sort_values(ascending=False).head(4).index)
    picked.update(last.sort_values().head(4).index)
    picked.update(actual_counts.sort_values(ascending=False).head(4).index)
    chosen = sorted(picked)
    mapping = identities.vault_address.to_dict()
    archive, rejected = independent_calendar([mapping[pair_id] for pair_id in chosen], data.get("downloads"))
    rows = []
    for pair_id in chosen:
        address = mapping[pair_id]
        reference = archive.get(address)
        expected = reference["daily"].reindex(nav.index) if reference else pd.DataFrame(index=nav.index)
        expected_nav = expected.get("share_price", pd.Series(np.nan, index=nav.index)).to_numpy(dtype=float)
        actual_nav = nav[pair_id].to_numpy(dtype=float)
        np.testing.assert_allclose(actual_nav, expected_nav, rtol=1e-12, atol=0.0, equal_nan=True)
        actual_mask = raw_nav[pair_id].notna().to_numpy()
        expected_mask = expected.get("actual", pd.Series(False, index=nav.index)).eq(True).to_numpy(dtype=bool)
        assert np.array_equal(actual_mask, expected_mask), f"Actual mark mask differs: {pair_id}"
        expected_times = expected.get("timestamp", pd.Series(pd.NaT, index=nav.index))
        main_times = observed[pair_id].ffill()
        assert ((main_times == expected_times) | (main_times.isna() & expected_times.isna())).all(), f"Actual timestamp differs: {pair_id}"
        rows.append({"pair_id": pair_id, "vault_address": address, "minimum_actual_nav": minimum.loc[pair_id], "actual_observations": int(actual_counts.loc[pair_id]), "first_actual_date": first.loc[pair_id], "last_actual_date": last.loc[pair_id], "calendar_matches": True, "actual_mask_matches": True, "actual_timestamp_matches": True})
    frame = pd.DataFrame(rows)
    output = Path(artefact_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "independent-calendar-checks.csv", index=False)
    rejected[["timestamp", "address", "share_price"]].to_csv(output / "rejected-nonpositive-nav-sample.csv", index=False)
    report = {"stratified_vaults": len(frame), "calendar_rows_checked": len(nav) * len(frame), "rejected_nonpositive_or_nonfinite_records": len(rejected), "all_calendars_match": True, "strata": "Least/most observed, tiny NAV, latest first mark, earliest final mark"}
    (output / "independent-calendar-checks.json").write_text(json.dumps(report, indent=2))
    return frame, archive


def audit_risk_primitives():
    """Compare estimator primitives against hand-specified fixture results."""
    from portfolio_snapshot_risk import empirical_window, peer_prior, forecast, qlike_difference

    nav = np.array([10.0, 10.0, 10.0, 12.0, 12.0, 12.0])
    actual = np.array([True, False, False, True, False, True])
    measured = empirical_window(nav, actual, 5)
    expected_returns = np.array([0.0, 0.0, 0.2, 0.0, 0.0])
    assert measured["n"] == 5 and measured["m"] == 2 and measured["full"]
    assert np.isclose(measured["empirical"], expected_returns.var(ddof=1))
    measured = empirical_window(np.array([np.nan, np.nan, 10.0, 10.0, 12.0]), np.array([False, False, True, False, True]), 5)
    assert measured["n"] == 2 and measured["m"] == 1 and not measured["full"]
    assert np.isclose(measured["empirical"], 0.02)
    assert np.isnan(empirical_window(np.ones(8), np.zeros(8, bool), 7)["empirical"])
    measured = empirical_window(np.ones(8), np.ones(8, bool), 7)
    assert measured["empirical"] == 0 and measured["m"] == 7
    empirical = np.array([0.01, 0.03, 0.05, 0.9, 0.0, np.nan])
    full = np.array([True, True, False, True, True, False])
    prior, count, pool, _ = peer_prior(empirical, full, 3)
    assert np.isclose(prior, 0.02) and count == 2 and pool == "full"
    prior, count, pool, _ = peer_prior(empirical, full, 3, gate=3)
    assert prior == 0.03 and count == 3 and pool == "partial"
    assert np.isnan(peer_prior(empirical, full, 3, gate=5)[0])
    assert np.isclose(forecast(0.01, 0.04, 10, "regularised", 30), 0.0325)
    assert forecast(np.nan, 0.04, 0, "regularised", 30) == 0.04
    assert forecast(0.01, np.nan, 5, "regularised", 30) == 0.01
    assert np.isnan(forecast(0.0, np.nan, 5, "regularised", 30))
    assert forecast(0.0, np.nan, 5, "raw", 30) == 1e-8
    assert np.isnan(forecast(np.nan, np.nan, 0, "raw", 30))
    diff = qlike_difference([0.02, 0.0, np.nan], [0.01, 0.01, 0.01], [0.0, 0.01, 0.01])
    assert np.isclose(diff[0], np.log(2)) and np.isnan(diff[1:]).all()
    return [{"check": "Risk estimator fixtures", "status": "pass", "detail": "Elapsed partial history; carried-anchor real updates; observed-flat vs unknown-flat; leave-one-out/full/partial/gated priors; variance floors; shrinkage; zero-target QLIKE"}]


def audit_risk_archive(data, risk, archive, artefact_dir):
    """Recalculate original-archive empirical/source risk on matched rows."""
    addresses = data["identities"].set_index("pair_id").vault_address
    available = addresses[addresses.isin(archive)].index
    supported = risk[risk.pair_id.isin(available)]
    selections = [supported.groupby("status", group_keys=False).head(3)]
    selections += [group.sample(min(3, len(group)), random_state=1010 + int(L)) for L, group in supported.groupby("L")]
    chosen = pd.concat(selections).drop_duplicates(["origin_at", "pair_id", "L"])
    rows = []
    for row in chosen.to_dict("records"):
        expected = independent_empirical(archive[addresses.loc[row["pair_id"]]], row["origin_at"], row["L"])
        a, b = expected["empirical_variance"], row["empirical"]
        assert (np.isnan(a) and np.isnan(b)) or np.isclose(a, b, rtol=1e-10, atol=1e-15)
        assert expected["calendar_returns"] == row["n"] and expected["actual_updates"] == row["m"]
        peers = risk[(risk.origin_at == row["origin_at"]) & risk.L.eq(row["L"]) & risk.pair_id.ne(row["pair_id"])]
        complete = peers[np.isfinite(peers.empirical) & peers.empirical.gt(0) & peers.full]
        partial = peers[np.isfinite(peers.empirical) & peers.empirical.gt(0)]
        pool = complete if len(complete) else partial
        prior = pool.empirical.median() if len(pool) else np.nan
        assert len(pool) == row["prior_count"]
        assert (np.isnan(prior) and np.isnan(row["prior"])) or np.isclose(prior, row["prior"], rtol=1e-12, atol=0.0)
        raw = max(a if np.isfinite(a) else prior, 1e-8) if np.isfinite(a) or np.isfinite(prior) else np.nan
        if np.isfinite(prior):
            confidence = row["m"] / (row["m"] + row["L"] / 3) if np.isfinite(a) else 0.0
            regularised = confidence * (a if np.isfinite(a) else 0) + (1 - confidence) * prior
        else:
            regularised = a if np.isfinite(a) and a > 0 else np.nan
        np.testing.assert_allclose([row["raw"], row["regularised"]], [raw, regularised], rtol=1e-10, atol=0.0, equal_nan=True)
        source_match = None
        if row["L"] == 90:
            anchor = pd.Timestamp(row["origin_at"]) - pd.Timedelta(days=1)
            source = data["source"][row["pair_id"]].loc[anchor - pd.Timedelta(days=90) : anchor]
            valid = len(source) == 91 and source.notna().all() and source.gt(0).all()
            direct = max(source.pct_change(fill_method=None).iloc[1:].var(ddof=1), 1e-8) if valid else np.nan
            source_match = bool((np.isnan(direct) and np.isnan(row["source"])) or np.isclose(direct, row["source"], rtol=1e-10, atol=1e-15))
            assert source_match
        rows.append({"origin_at": row["origin_at"], "pair_id": row["pair_id"], "L": row["L"], "empirical_matches": True, "calendar_and_actual_counts_match": True, "leave_one_out_prior_matches": True, "raw_and_regularised_forecasts_match": True, "source_variance_matches": source_match})
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(artefact_dir) / "independent-risk-checks.csv", index=False)
    return frame


def audit_future_archive(data, archive, artefact_dir):
    """Check targets, censoring and boundary attribution directly from marks."""
    from portfolio_snapshot_data import future_panel

    identities = data["identities"].set_index("pair_id")
    chosen = identities[identities.vault_address.isin(archive)]
    originals = pd.DatetimeIndex(data["eligibility"].origin_at.unique()).sort_values()
    originals = originals[((originals - pd.Timestamp("2026-01-01")).days % 4) == 0]
    labels = pd.read_parquet(GENERATION / "08/labels.parquet", filters=[("pair_id", "in", chosen.index.tolist()), ("delay_days", "==", 0), ("lookahead_days", "in", [7, 30, 90])]).set_index(["origin_at", "pair_id", "lookahead_days"])
    rows = []
    for pair_id, identity in chosen.iterrows():
        series = archive[identity.vault_address]
        nearest_first = originals[np.argmin(np.abs(originals - series["first"]))]
        nearest_last = originals[np.argmin(np.abs(originals - series["last"]))]
        dates = set([originals[0], pd.Timestamp("2026-01-01"), nearest_first, nearest_last])
        for origin in sorted(dates):
            for horizon in (7, 30, 90):
                expected = independent_path(series, origin, horizon)
                actual = future_panel(data, origin, horizon, [int(pair_id)])
                assert bool(actual["supported"][0]) == expected["resolved"], f"Target support: {pair_id}/{origin}/{horizon}"
                if expected["resolved"]:
                    np.testing.assert_allclose(actual["paths"][:, 0], expected["path"], rtol=1e-12, atol=0.0)
                    for field, reference in [("returns", "return"), ("variance", "variance"), ("first_update", "first_update_component"), ("remaining", "remaining_mark_component")]:
                        np.testing.assert_allclose(actual[field][0], expected[reference], rtol=1e-10, atol=1e-14, equal_nan=True)
                    assert actual["future_updates"][0] == expected["actual_updates"]
                    if np.isfinite(expected["first_update_component"]):
                        assert np.isclose(expected["return"], expected["first_update_component"] + expected["remaining_mark_component"])
                key = (origin, int(pair_id), horizon)
                cache_matches = None
                if key in labels.index:
                    previous = labels.loc[key]
                    cache_matches = bool(previous.return_supported == expected["resolved"])
                    if expected["resolved"]:
                        cache_matches &= bool(np.isclose(previous.future_return, expected["return"], rtol=1e-10, atol=1e-12))
                    assert cache_matches, f"Post-fix NB08 target: {key}"
                rows.append({"origin_at": origin, "pair_id": pair_id, "horizon": horizon, "resolved": expected["resolved"], "status": expected["reason"], "original_archive_path_matches": True, "post_fix_nb08_matches": cache_matches})
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(artefact_dir) / "independent-target-checks.csv", index=False)
    return frame


def audit_future_mutation(data, artefact_dir):
    """Re-run actual historical risk construction after a severe future mutation.

    Frozen eligibility and recipes are inspected separately; this test checks
    that the main risk builder never reads future prices or reporting masks.
    """
    import portfolio_snapshot_risk as risk_module
    from portfolio_snapshot_data import future_panel

    origin = pd.Timestamp("2026-01-01")
    candidates = data["eligibility"][(data["eligibility"].origin_at == origin) & data["eligibility"].eligible_as_of_origin].head(12)
    assert len(candidates) >= 3, "Mutation audit needs an eligible cross-section"
    audit_data = data.copy()
    audit_data["eligibility"] = candidates.copy()
    future_data = audit_data.copy()
    future_data["arrays"] = {key: np.array(value, copy=True) for key, value in data["arrays"].items()}
    cut = data["date_index"][origin - pd.Timedelta(days=1)] + 1
    future_data["arrays"]["nav"][cut:] *= 1234.0
    future_data["arrays"]["source"][cut:] *= 0.007
    future_data["arrays"]["actual"][cut:] = ~future_data["arrays"]["actual"][cut:]
    previous_path = risk_module.ARTIFACT
    risk_module.ARTIFACT = Path(artefact_dir)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            before = risk_module.build_risk(audit_data)
            after = risk_module.build_risk(future_data)
        pd.testing.assert_frame_equal(before, after, check_exact=True)
    finally:
        risk_module.ARTIFACT = previous_path
    ids = candidates.pair_id.to_numpy(dtype=int)
    baseline = future_panel(data, origin, 30, ids)
    available = np.flatnonzero(baseline["supported"])
    assert len(available), "Endpoint audit needs a supported target"
    pid = int(ids[available[0]])
    mutated = data.copy()
    mutated["arrays"] = dict(data["arrays"])
    mutated["arrays"]["nav"] = data["arrays"]["nav"].copy()
    endpoint = data["date_index"][origin - pd.Timedelta(days=1)] + 30
    mutated["arrays"]["nav"][endpoint, data["id_index"][pid]] *= 2
    changed = future_panel(mutated, origin, 30, [pid])
    initial = future_panel(data, origin, 30, [pid])
    assert not np.isclose(changed["returns"][0], initial["returns"][0])
    return [{"check": "Future-price and reporting-mask mutation", "status": "pass", "detail": f"{len(before)} historical risk/prior rows identical after severe future NAV/source/mask changes; endpoint mutation changes its target"}]


def audit_construction_primitives():
    """Test membership, budgets and paths using independently stated answers."""
    from types import SimpleNamespace
    from portfolio_snapshot_construction import select_basket, risk_weights, bounded_proportional, fixed_unit_path, outcome_metrics, capacity_limits

    candidates = pd.DataFrame({"pair_id": [1, 2, 3, 4], "vault_address": ["0xD", "0xC", "0xB", "0xA"], "score": [np.nan, 0.0, 0.5, 0.5], "eligible_as_of_origin": [True] * 4})
    assert select_basket(candidates, 4).pair_id.tolist() == [4, 3, 2, 1]
    assert select_basket(candidates, 4, exclude_unscored=True).pair_id.tolist() == [4, 3, 2]
    variance = np.array([0.04, 0.01, 0.09])
    np.testing.assert_allclose(risk_weights(variance, 0), [1 / 3] * 3)
    np.testing.assert_allclose(risk_weights([np.nan, 0.01, 0.09], 2), [1 / 3] * 3)
    reference = np.array([25.0, 100.0, 100 / 9])
    reference /= reference.sum()
    np.testing.assert_allclose(risk_weights(variance, 2), reference)
    for power in (0.5, 1.0, 2.0):
        weights = risk_weights(variance, power)
        assert np.array_equal(np.argsort(weights), np.argsort(1 / variance))
        np.testing.assert_allclose(weights, risk_weights(variance * 1e-8, power), atol=1e-14)
    np.testing.assert_allclose(bounded_proportional([0.9, 0.1], [0.2, 0.8], 0.98), [0.2, 0.78])
    np.testing.assert_allclose(bounded_proportional([0.9, 0.1], [0.1, 0.2], 0.98), [0.1, 0.2])
    np.testing.assert_allclose(bounded_proportional([0.0, 1.0], [0.9, 0.2], 0.98), [0.0, 0.2])
    np.testing.assert_allclose(bounded_proportional([], [], 0.98), [])
    prices = np.array([[1.0, 1.0], [2.0, 0.5], [1.0, 1.0]])
    np.testing.assert_allclose(fixed_unit_path(prices, [0.5, 0.5]), [1.0, 1.25, 1.0])
    np.testing.assert_allclose(fixed_unit_path(prices, [0.3, 0.2]), [1.0, 1.2, 1.0])
    panel = {"supported": np.array([True, False]), "paths": np.array([[1.0, 1.0], [1.1, np.nan], [1.2, np.nan]]), "returns": np.array([0.2, np.nan])}
    outcome = outcome_metrics(panel, np.array([0.7, 0.3]))
    assert not outcome["resolved"] and np.isnan(outcome["return"])
    assert outcome["unresolved_weight"] == 0.3
    assert np.isclose(outcome["lower_return_bound"], -0.16) and np.isposinf(outcome["upper_return_bound"])
    origin = pd.Timestamp("2026-01-05")
    price = pd.DataFrame({"date": [origin - pd.Timedelta(days=2), origin - pd.Timedelta(days=1)], "pair_id": [1, 1], "total_assets": [15000.0, np.nan]})
    basket = pd.DataFrame({"pair_id": [1], "max_deposit": [np.nan], "capacity_observed_at": [pd.NaT], "permission_time_unknown": [True]})
    caps, unknown = capacity_limits({"prices": price}, origin, basket, SimpleNamespace(account=150000, cap=0.33, state="permissive"))
    assert np.isclose(caps[0], 0.033), "A finite TVL inside the declared carry window was lost"
    assert unknown[0], "Unknown capacity/permission clocks must remain flagged"
    conservative, unknown = capacity_limits({"prices": price}, origin, basket, SimpleNamespace(account=150000, cap=0.33, state="known_only"))
    assert conservative[0] == 0 and unknown[0]
    return [{"check": "Construction and capacity fixtures", "status": "pass", "detail": "Finite zero vs unscored; canonical ties; whole-basket risk fallback; powers/scale invariants; water-fill budgets; fixed units; no survivor renormalisation; terminal bounds; independent TVL carry and unknown-state policies"}]


def audit_frozen_score_timing(data, artefact_dir):
    """Recompute the three frozen formulae from source NAV through T−1."""
    recipes = {row["method_id"]: row for row in data["registry"]}
    rows = []
    for method, group in data["scores"].groupby("method_id", sort=False, observed=True):
        recipe = recipes[method]
        chosen = pd.concat([group[group.score.isna()].head(3), group[np.isfinite(group.score) & group.score.eq(0)].head(3), group[np.isfinite(group.score) & group.score.gt(0)].sample(min(12, int((np.isfinite(group.score) & group.score.gt(0)).sum())), random_state=1010)]).drop_duplicates(["origin_at", "pair_id"])
        for row in chosen.itertuples():
            anchor = row.origin_at - pd.Timedelta(days=1)
            total = 0.0
            for term in recipe["recipe"]["terms"]:
                L = int(term["days"])
                values = data["source"][row.pair_id].loc[anchor - pd.Timedelta(days=L) : anchor].to_numpy(dtype=float)
                valid = len(values) == L + 1 and np.isfinite(values).all() and (values > 0).all()
                raw = np.nan
                if valid:
                    daily = values[1:] / values[:-1] - 1
                    if term["metric"] == "CAGR":
                        raw = (values[-1] / values[0]) ** (365 / L) - 1
                    elif term["metric"] == "Sortino":
                        denominator = np.sqrt(np.mean(np.minimum(daily, 0.0) ** 2))
                        if term["ratio_floor"]:
                            denominator = max(denominator, term["risk_floor"] or 1e-4)
                        raw = daily.mean() * np.sqrt(365) / denominator if denominator > 0 else np.nan
                    else:
                        raise AssertionError(f"Unexpected focal metric: {term}")
                score = np.clip(raw / term["cap"], 0.0, 1.0)
                if recipe["missing_policy"] == "component_zero" and not np.isfinite(score):
                    score = 0.0
                total += term["coefficient"] * score
            matches = (np.isnan(total) and np.isnan(row.score)) or np.isclose(total, row.score, atol=1e-10, rtol=1e-10)
            assert matches, f"Frozen score differs at completed candle A: {method}/{row.origin_at}/{row.pair_id}; {total} vs {row.score}"
            rows.append({"origin_at": row.origin_at, "feature_cutoff": anchor, "pair_id": row.pair_id, "method_id": method, "phase": int((row.origin_at - pd.Timestamp("2026-01-01")).days % 4), "score": row.score, "recalculated_score": total, "completed_candle_score_matches": True})
    result = pd.DataFrame(rows)
    result.to_csv(Path(artefact_dir) / "independent-score-cutoff-checks.csv", index=False)
    return result


def audit_statistics_primitives():
    """Check calendar support and descriptive inference gates independently."""
    from portfolio_snapshot_statistics import support_counts, simultaneous_intervals, macro_risk_summary

    start, end = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-10")
    frame = pd.DataFrame({"origin_at": pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-09"]), "effect": [1.0, np.nan, 3.0]})
    values, windows, blocks = support_counts(frame, start, end, 7, 10)
    assert len(values) == 34 and values.notna().sum() == 2
    assert np.isnan(values.loc[pd.Timestamp("2026-01-05")])
    assert windows == 2 and blocks == 0
    dates = pd.date_range("2026-01-01", "2026-09-05", freq="4D")
    rows = [{"origin_at": date, "h": 30, "phase": 0, "comparison_id": f"fixture_{j}", "effect": float(j), "conditional_active": True, "actual_breadth_changed": False} for date in dates for j in range(18)]
    intervals = simultaneous_intervals(pd.DataFrame(rows), "2026")
    assert len(intervals) == 18 and intervals.complete_blocks.max() < 10
    assert intervals.lower.isna().all() and intervals.upper.isna().all()
    assert intervals.status.eq("descriptive; insufficient blocks").all()
    losses = pd.DataFrame({"origin_at": pd.to_datetime(["2026-01-01"] * 3 + ["2026-01-05"] * 2), "score": ["v11"] * 5, "estimator": ["raw"] * 5, "L": [90] * 5, "h": [30] * 5, "phase": [0] * 5, "selected": [True] * 5, "predicted": [0.1, 0.2, 0.3, 0.1, 0.4], "realised": [1.0, 0.0, 2.0, 4.0, np.nan], "qlike_delta": [-1.0, -1.0, 100.0, 0.5, np.nan]})
    aggregate = macro_risk_summary(losses, "2026")
    np.testing.assert_allclose(aggregate.qlike_delta, [(98 / 3 + 0.5) / 2] * 2)
    np.testing.assert_allclose(aggregate.win_fraction, [1 / 3] * 2)
    np.testing.assert_allclose(aggregate.qlike_median, [0.5] * 2)
    np.testing.assert_allclose(aggregate.zero_realised_fraction, [0.25] * 2)
    assert aggregate.omitted_target_rows.eq(1).all()
    return [{"check": "Calendar support and inference fixtures", "status": "pass", "detail": "Calendar gaps retained; non-overlapping intervals counted; 2026 gate withholds all 18 intervals; raw QLIKE median/win macro weights and finite-target zero denominator verified"}]


def audit_covariance_primitives():
    """Verify diagonal closed forms and supported covariance risk budgets."""
    from portfolio_snapshot_construction import covariance_weights, CONFIG
    from sklearn.covariance import LedoitWolf

    dates = pd.date_range("2026-01-01", periods=61)
    origin = dates[-1] + pd.Timedelta(days=1)
    t = np.arange(60)
    returns = np.column_stack([0.002 * np.sin(t), 0.003 * np.cos(t * 0.8), 0.001 * np.sin(t) + 0.004 * np.cos(t * 0.6)])
    prices = np.vstack([np.ones(3), np.cumprod(1 + returns, axis=0)])
    data = {"date_index": {date: k for k, date in enumerate(dates)}, "id_index": {1: 0, 2: 1, 3: 2}, "first_index": np.zeros(3, dtype=int), "arrays": {"nav": prices, "actual": np.zeros_like(prices, dtype=bool)}}
    variance = np.array([1.0, 4.0, 9.0])
    mv, status, _, _ = covariance_weights(data, origin, [1, 2, 3], variance, "minimum_variance")
    assert status == "correlation_prior_identity"
    np.testing.assert_allclose(mv, [36 / 49, 9 / 49, 4 / 49], atol=2e-5)
    erc, status, _, _ = covariance_weights(data, origin, [1, 2, 3], variance, "equal_risk_contribution")
    assert status == "correlation_prior_identity"
    np.testing.assert_allclose(erc, [6 / 11, 3 / 11, 2 / 11], atol=2e-5)
    equal, status, _, _ = covariance_weights(data, origin, [1, 2, 3], [1.0, np.nan, 9.0], "minimum_variance")
    assert status == "risk_fallback_equal"
    np.testing.assert_allclose(equal, [1 / 3] * 3)
    data["arrays"]["actual"][:] = True
    variance = np.var(returns, axis=0, ddof=1)
    vendor = LedoitWolf(assume_centered=False).fit(returns)
    cov = vendor.covariance_
    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sd, sd)
    marginal_cov = corr * np.sqrt(np.outer(variance, variance))
    scaled = marginal_cov / np.diag(marginal_cov).mean()
    baselines = {}
    for method in ("minimum_variance", "equal_risk_contribution"):
        weights, status, shrinkage, jitter = covariance_weights(data, origin, [1, 2, 3], variance, method)
        assert status == "estimated_correlation" and np.isclose(shrinkage, vendor.shrinkage_)
        assert np.all(weights >= 0) and np.isclose(weights.sum(), 1.0) and jitter == 0
        if method == "equal_risk_contribution":
            contribution = weights * (scaled @ weights)
            np.testing.assert_allclose(contribution / contribution.sum(), [1 / 3] * 3, atol=1e-5)
        else:
            objective = float(weights @ scaled @ weights)
            for a in np.linspace(0, 1, 51):
                for b in np.linspace(0, 1 - a, 51):
                    competitor = np.array([a, b, 1 - a - b])
                    assert objective <= competitor @ scaled @ competitor + 1e-6
        multiplied, status2, _, _ = covariance_weights(data, origin, [1, 2, 3], variance * 1e6, method)
        assert status2 == status
        np.testing.assert_allclose(multiplied, weights, atol=1e-8)
        baselines[method] = weights
    names = ("matrix_tolerance", "solver_tolerance", "erc_objective_tolerance", "risk_contribution_tolerance", "positive_solver_bound")
    originals = {name: CONFIG[name] for name in names}
    largest_change = 0.0
    try:
        for factor in (0.1, 10.0):
            CONFIG.update({name: value * factor for name, value in originals.items()})
            for method, baseline in baselines.items():
                weights, status, _, _ = covariance_weights(data, origin, [1, 2, 3], variance, method)
                assert status == "estimated_correlation"
                largest_change = max(largest_change, float(np.max(np.abs(weights - baseline))))
                np.testing.assert_allclose(weights, baseline, atol=1e-4)
    finally:
        CONFIG.update(originals)
    return [{"check": "Covariance allocation fixtures", "status": "pass", "detail": f"Analytical diagonal/MV/ERC; unknown-risk fallback; fitted shrinkage; budget/grid optimum/risk contributions/scale checks; 0.1×/10× tolerances change weights at most {largest_change:.2g}"}]


def audit_signed_bounds():
    """Check unresolved positive, negative, mixed and zero active coefficients."""
    from portfolio_snapshot_construction import signed_return_bounds

    lower, upper = signed_return_bounds([-0.3, 0.3], [0.2, np.nan], [True, False])
    assert np.isclose(lower, -0.36) and np.isposinf(upper)
    lower, upper = signed_return_bounds([0.3, -0.3], [0.2, np.nan], [True, False])
    assert np.isneginf(lower) and np.isclose(upper, 0.36)
    lower, upper = signed_return_bounds([0.1, 0.3, -0.4], [0.2, np.nan, np.nan], [True, False, False])
    assert np.isneginf(lower) and np.isposinf(upper)
    lower, upper = signed_return_bounds([0.3, 0.0], [0.2, np.nan], [True, False])
    assert np.isclose(lower, 0.06) and np.isclose(upper, 0.06)
    lower, upper = signed_return_bounds([0.3, -0.3], [0.2, -0.1], [True, True])
    assert np.isclose(lower, 0.09) and np.isclose(upper, 0.09)
    return [{"check": "Signed missing-return bounds", "status": "pass", "detail": "Positive/negative unknown active weights produce the correct unbounded side; mixed signs are vacuous; zero coefficients preserve exact known contrasts"}]


def audit_synthetic_reporting():
    """A dense history must reproduce itself and empty update masks need priors."""
    from portfolio_snapshot_statistics import synthetic_reporting

    default = synthetic_reporting()
    dense = default[default.spacing_days.eq("1")]
    assert len(dense) and dense.empirical_supported.all()
    np.testing.assert_allclose(dense.ratio, 1.0, rtol=1e-12, atol=1e-12)
    assert dense.actual_updates.eq(180).all()
    no_updates = {"nav": pd.DataFrame(np.ones((181, 1))), "arrays": {"actual": np.zeros((181, 1), dtype=bool)}}
    prior = synthetic_reporting(no_updates)
    unobserved = prior[prior.spacing_days.eq("empirical")]
    assert not unobserved.empirical_supported.any() and unobserved.actual_updates.eq(0).all()
    np.testing.assert_allclose(unobserved.ratio, 1.0, rtol=1e-12, atol=1e-12)
    assert np.isfinite(default.ratio).all() and np.isfinite(prior.ratio).all()
    return [{"check": "Synthetic reporting invariants", "status": "pass", "detail": "180 returns / 181 NAV anchors align; every dense estimator ratio is exactly 1; default-call works; no-update masks use the declared prior instead of 0×NaN"}]


def audit_saved_snapshots(data, risk, allocations, outcomes, artefact_dir, policies=None):
    """Reconstruct selected allocation ledgers from original marks and units."""
    from portfolio_snapshot_construction import policy_registry

    assert not allocations.duplicated(["origin_at", "policy_id", "pair_id"]).any()
    assert not outcomes.duplicated(["origin_at", "policy_id", "h"]).any()
    policies = (policy_registry() if policies is None else policies).set_index("policy_id")
    budgets = allocations.groupby(["origin_at", "policy_id"], observed=True).agg(accepted=("accepted_weight", "sum"), benchmark=("benchmark_weight", "sum"), desired=("desired_weight", "sum"), cash=("cash", "first"))
    np.testing.assert_allclose(budgets.accepted, budgets.benchmark, atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(budgets.accepted + budgets.cash, 1.0, atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(budgets.desired, 1.0, atol=1e-10, rtol=1e-10)
    assert allocations.accepted_weight.ge(-1e-10).all()
    assert (allocations.accepted_weight <= allocations.capacity + 1e-10).all()
    eligible = outcomes[outcomes.N_actual.gt(0) & outcomes.phase.eq(0)]
    pieces = []
    for (horizon, resolved), group in eligible.groupby(["h", "resolved"]):
        pieces.append(group.sample(min(4, len(group)), random_state=1010 + int(horizon)))
    for method in ("v11", "blend_46d", "focal_four"):
        for branch in ("pure", "capacity"):
            ids = policies[(policies.score == method) & (policies.branch == branch)].index
            group = eligible[eligible.policy_id.isin(ids) & eligible.h.eq(30)]
            if len(group):
                pieces.append(group.sample(min(3, len(group)), random_state=2010))
    source_ids = policies[policies.estimator.eq("source")].index
    pieces.append(eligible[eligible.policy_id.isin(source_ids)].head(3))
    for pid in policies[policies.variant.eq("source_capacity_control")].index:
        group = eligible[eligible.policy_id.eq(pid) & eligible.h.eq(30)]
        if len(group):
            pieces.append(group.sample(min(2, len(group)), random_state=3010))
    sample = pd.concat(pieces).drop_duplicates(["origin_at", "policy_id", "h"])
    keys = pd.MultiIndex.from_frame(sample[["origin_at", "policy_id"]].drop_duplicates())
    ledger = allocations.set_index(["origin_at", "policy_id"])
    wanted = ledger.loc[ledger.index.isin(keys)]
    identities = data["identities"].set_index("pair_id")
    addresses = identities.loc[wanted.pair_id.unique()].vault_address.tolist()
    archive, _ = independent_calendar(addresses, data.get("downloads"))
    rows = []
    for row in sample.to_dict("records"):
        group = ledger.loc[[(row["origin_at"], row["policy_id"])]].sort_values("rank")
        ids = group.pair_id.to_numpy(dtype=int)
        w = group.accepted_weight.to_numpy(dtype=float)
        references = [independent_path(archive.get(identities.loc[pid].vault_address), row["origin_at"], row["h"]) for pid in ids]
        support = np.array([r["resolved"] for r in references])
        active = w > 0
        resolved = bool(support[active].all())
        assert resolved == row["resolved"]
        assert np.isclose(w[active & ~support].sum(), row["unresolved_weight"])
        anchor = pd.Timestamp(row["origin_at"]) - pd.Timedelta(days=1)
        assert pd.Timestamp(row["label_end"]) == anchor + pd.Timedelta(days=row["h"])
        assert pd.Timestamp(row["label_available_at"]) == anchor + pd.Timedelta(days=row["h"] + 1)
        initial = np.array([archive[identities.loc[pid].vault_address]["daily"].reindex([anchor]).share_price.iloc[0] for pid in ids])
        np.testing.assert_allclose(group.units.to_numpy(dtype=float), w / initial, rtol=1e-12, atol=1e-12)
        if resolved:
            if active.any():
                prices = np.column_stack([r["path"] for r in references])[:, active]
                expected = independent_units(prices, w[active], 1 - w.sum())
            else:
                expected = {"return": 0.0, "variance": 0.0, "max_drawdown": 0.0}
            for actual_name, reference_name in [("return", "return"), ("variance", "variance"), ("drawdown", "max_drawdown")]:
                np.testing.assert_allclose(row[actual_name], expected[reference_name], rtol=1e-10, atol=1e-12)
            benchmark = group.benchmark_weight.to_numpy(dtype=float)
            if support[benchmark > 0].all():
                expected_base = sum(weight * r["return"] for weight, r in zip(benchmark, references) if weight > 0)
                assert np.isclose(row["weighting_lift"], expected["return"] - expected_base, atol=1e-10)
        if "contrast_lower" in row:
            active_weights = w - group.benchmark_weight.to_numpy(dtype=float)
            known = sum(coefficient * reference["return"] for coefficient, reference in zip(active_weights, references) if reference["resolved"])
            unknown = active_weights[~support]
            expected_lower = -np.inf if (unknown < 0).any() else known - float(unknown[unknown > 0].sum())
            expected_upper = np.inf if (unknown > 0).any() else known - float(unknown[unknown < 0].sum())
            np.testing.assert_allclose([row["contrast_lower"], row["contrast_upper"]], [expected_lower, expected_upper], atol=1e-10)
        policy = policies.loc[row["policy_id"]]
        if policy.estimator == "source":
            direct = []
            for pid in ids:
                source = data["source"][pid].loc[anchor - pd.Timedelta(days=90) : anchor]
                good = len(source) == 91 and source.notna().all() and source.gt(0).all()
                direct.append(max(source.pct_change(fill_method=None).iloc[1:].var(ddof=1), 1e-8) if good else np.nan)
            direct = np.array(direct)
            expected_weights = (1 / direct) / (1 / direct).sum() if np.isfinite(direct).all() else np.full(len(direct), 1 / len(direct))
            np.testing.assert_allclose(group.desired_weight, expected_weights, rtol=1e-10, atol=1e-12)
        rows.append({"origin_at": row["origin_at"], "policy_id": row["policy_id"], "h": row["h"], "resolved": resolved, "original_units_match": True, "original_fixed_unit_path_matches": True, "snapshot_target_matches": True, "source_control_checked": policy.estimator == "source"})
    frame = pd.DataFrame(rows)
    frame.to_csv(Path(artefact_dir) / "independent-snapshot-checks.csv", index=False)
    return frame


def independent_projection(desired, limits, budget):
    """Solve the bounded proportional allocation by an independent scalar search."""
    u = np.asarray(desired, dtype=float)
    c = np.asarray(limits, dtype=float)
    positive = u > 0
    target = min(float(budget), float(c[positive].sum()))
    if not positive.any() or target <= 0:
        return np.zeros_like(u)
    left = 0.0
    right = max(float(np.max(c[positive] / u[positive])), 1.0)
    for _ in range(120):
        mid = (left + right) / 2
        if np.minimum(c, mid * u).sum() < target:
            left = mid
        else:
            right = mid
    return np.minimum(c, ((left + right) / 2) * u)


def audit_source_capacity_controls(data, result, artefact_dir):
    """Verify companions preserve baskets and only apply their declared entry caps."""
    policies = result["policies"]
    added = policies[policies.variant.eq("source_capacity_control")]
    if not len(added):
        return []
    assert len(added) == 9 and added.policy_id.is_unique
    assert added.branch.eq("capacity").all() and added.state.eq("source_report_only").all()
    assert added.redistribute.all() and added.N.eq(6).all() and added.L.eq(90).all()
    ledger = {(t, p): g.sort_values("rank") for (t, p), g in result["allocations"].groupby(["origin_at", "policy_id"])}
    candidates = {(t, m): g.set_index("pair_id") for (t, m), g in data["candidates"].groupby(["origin_at", "method_id"], observed=True)}
    outcomes_by_policy = {(t, p): g for (t, p), g in result["outcomes"].groupby(["origin_at", "policy_id"])}
    tvl_states = {}
    checked = []
    for policy in added.itertuples():
        original = policy.policy_id.removesuffix("|source-entry-caps")
        parent = policies[policies.policy_id.eq(original)].iloc[0]
        assert parent.branch == "pure"
        for field in ("score", "N", "L", "p", "estimator", "cap", "account", "satellite"):
            assert getattr(policy, field) == parent[field]
        control_ledger = [(key, g) for key, g in ledger.items() if key[1] == policy.policy_id]
        for key, g in control_ledger:
            t, pid = key
            base = ledger[(t, original)]
            np.testing.assert_array_equal(g.pair_id, base.pair_id)
            np.testing.assert_allclose(g.desired_weight, base.desired_weight, atol=0, rtol=0)
            np.testing.assert_array_equal(g.status, base.status)
            assert g.phase.eq(0).all()
            if t not in tvl_states:
                a = pd.Timestamp(t) - pd.Timedelta(days=1)
                p = data["prices"]
                p = p[(p.date <= a) & (p.date >= a - pd.Timedelta(days=2)) & np.isfinite(p.total_assets)]
                tvl_states[t] = p.sort_values("date").groupby("pair_id").tail(1).set_index("pair_id").total_assets
            tvls = tvl_states[t].reindex(g.pair_id).to_numpy(dtype=float)
            limits = np.where(np.isfinite(tvls), np.minimum(policy.cap, np.maximum(tvls, 0) * 0.33 / policy.account), policy.cap)
            expected = independent_projection(base.desired_weight, limits, 0.98)
            benchmark = independent_projection(np.ones(len(g)), limits, float(expected.sum()))
            np.testing.assert_allclose(g.capacity, limits, rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(g.accepted_weight, expected, rtol=1e-11, atol=1e-12)
            np.testing.assert_allclose(g.benchmark_weight, benchmark, rtol=1e-11, atol=1e-12)
            np.testing.assert_allclose(g.cash, 1 - expected.sum(), rtol=1e-11, atol=1e-12)
            desired = base.desired_weight.to_numpy(dtype=float)
            units = np.divide(base.units.to_numpy(dtype=float) * expected, desired, out=np.zeros(len(g)), where=desired > 0)
            np.testing.assert_allclose(g.units, units, rtol=1e-11, atol=1e-12)
            basket = candidates[(t, policy.score)].reindex(g.pair_id)
            fresh_capacity = np.array([pd.notna(v) and pd.Timedelta(0) <= pd.Timestamp(t) - pd.Timestamp(v) <= pd.Timedelta(days=2) for v in basket.capacity_observed_at])
            fresh_permission = np.array([pd.notna(v) and pd.Timedelta(0) <= pd.Timestamp(t) - pd.Timestamp(v) <= pd.Timedelta(days=2) for v in basket.permission_observed_at])
            unknown = ~(np.isfinite(basket.max_deposit.to_numpy(dtype=float)) & fresh_capacity & ~basket.permission_time_unknown.to_numpy(dtype=bool) & fresh_permission & np.isfinite(tvls))
            np.testing.assert_array_equal(g.unknown_state, unknown)
            control = outcomes_by_policy[(t, pid)]
            parent_rows = outcomes_by_policy[(t, original)]
            np.testing.assert_array_equal(np.sort(control.h), np.sort(parent_rows.h))
            for row in control.itertuples():
                reference = parent_rows[parent_rows.h.eq(row.h)].iloc[0]
                for field in ("N_actual", "unscored_selected", "boundary_tie", "label_end", "label_available_at", "risk_fallback_equal", "conditional_active"):
                    assert getattr(row, field) == reference[field]
                assert pd.isna(row.selection_lift) and pd.isna(row.total_lift)
            checked.append({"origin_at": t, "policy_id": pid, "basket_frozen": True, "desired_frozen": True, "independent_projection": True, "matched_benchmark_budget": True, "clock_flags": True, "horizons": len(control)})
    frame = pd.DataFrame(checked)
    frame.to_csv(Path(artefact_dir) / "independent-source-capacity-controls.csv", index=False)
    return [{"check": "Source capacity companion controls", "status": "pass", "detail": f"All 9 companion arms; {len(frame):,} ledgers preserve baskets/requested weights; independent scalar water-fill, TVL caps, unknown clocks, units, matched benchmarks and target clocks"}]


def run_audit(data, risk, result, artefact_dir=None):
    """Run the independent audit and save compact, reviewable evidence."""
    output = Path(artefact_dir or GENERATION / "10/audit")
    if output.name != "audit":
        output = output / "audit"
    output.mkdir(parents=True, exist_ok=True)
    rows = reference_checks() + audit_risk_primitives() + audit_construction_primitives() + audit_statistics_primitives() + audit_covariance_primitives() + audit_signed_bounds() + audit_synthetic_reporting()
    calendar, archive = audit_archive_panel(data, output)
    empirical = audit_risk_archive(data, risk, archive, output)
    targets = audit_future_archive(data, archive, output)
    cutoff = audit_frozen_score_timing(data, output)
    rows += audit_future_mutation(data, output)
    snapshots = audit_saved_snapshots(data, risk, result["allocations"], result["outcomes"], output, result["policies"])
    rows += audit_source_capacity_controls(data, result, output)
    for name, frame in [("Original archive calendar", calendar), ("Original archive risk", empirical), ("Original archive and NB08 targets", targets), ("Frozen source score cutoff", cutoff), ("Original fixed-unit snapshot ledger", snapshots)]:
        rows.append({"check": name, "status": "pass", "detail": f"{len(frame):,} independently reconstructed rows/cases"})
    result = pd.DataFrame(rows)
    result.to_csv(output / "audit-summary.csv", index=False)
    (output / "audit-summary.json").write_text(json.dumps({"checks": rows, "audit_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2))
    return result
