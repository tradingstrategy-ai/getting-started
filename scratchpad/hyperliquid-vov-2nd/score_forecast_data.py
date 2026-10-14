"""Pinned, causal score and forward NAV frames for experiment 08.

Archive write time is not an observation or publication clock. Daily candles
are open-labelled aggregates: their close is the last mark inside that day.
"""

import ast
import datetime
import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from repaired_data_replay import RUN_ROOT, INPUT_DIR, RESEARCH_DIR
from precompute_repaired_singletons import create_evaluator
from score_matrix import FEATURES, PERIODS as FEATURE_PERIODS
from score_input_count_experiment import configurations as input_configurations
from score_calibration_experiment import configurations as calibration_configurations

ARTIFACT_DIR = RUN_ROOT / "08"
PERIODS = {"2026": (datetime.datetime(2026, 1, 1), datetime.datetime(2026, 10, 5)), "Long": (datetime.datetime(2023, 3, 1), datetime.datetime(2026, 10, 5))}
SHORT_PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
LONG_PERIOD = "2023-03-01 → 2026-10-05 (end exclusive, UTC)"
HORIZONS = (7, 30, 90)
DIAGNOSTIC_HORIZONS = (1, 2, 4, 14, 60)
DELAYS = (0, 1, 2)
FOCAL_METHOD_IDS = ("v11", "blend_46d", "focal_four")


def _json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _terms(weights, profile, missing, calmar_cap=5.0, mass=1.0):
    caps = [1.0 if profile == "legacy" else 0.5, 3.0, 3.0 if profile == "legacy" else 7.0, 0.7, calmar_cap]
    return [{"feature": int(i), "period": FEATURES[i][0], "metric": FEATURES[i][1], "days": FEATURE_PERIODS[FEATURES[i][0]], "coefficient": float(mass * weights[i]), "transform": "inverse_drawdown" if i % 5 == 3 else "hard", "cap": caps[i % 5], "ratio_floor": bool(not missing and i % 5 in (1, 2)), "risk_floor": 0.0001 if not missing and i % 5 in (1, 2) else None, "drawdown_floor": 0.01 if i % 5 == 4 else None} for i in np.flatnonzero(weights)]


def _canonical(terms, missing):
    merged = {}
    for term in terms:
        key = json.dumps({k: v for k, v in term.items() if k != "coefficient"}, sort_keys=True)
        merged[key] = merged.get(key, 0.0) + term["coefficient"]
    clean = [{**json.loads(key), "coefficient": round(value, 12)} for key, value in sorted(merged.items())]
    return {"terms": clean, "missing_policy": "propagate" if missing else "component_zero"}


def build_registry(panel):
    """Inventory all implemented composite scores, retaining aliases and exclusions."""
    by_recipe = {}
    excluded = []

    def add(name, terms, missing, source, weights=None, profile=None):
        canonical = _canonical(terms, missing)
        key = _json_hash(canonical)
        if key in by_recipe:
            row = by_recipe[key]
            if name not in row["aliases"]:
                row["aliases"].append(name)
            if source not in row["sources"]:
                row["sources"].append(source)
            return row
        row = {"method_id": "score_" + key[:12], "name": name, "aliases": [name], "sources": [source], "recipe": canonical, "recipe_sha256": key, "missing_policy": canonical["missing_policy"], "inputs": len({t["feature"] for t in canonical["terms"]}), "weights": weights, "profile": profile}
        by_recipe[key] = row
        return row

    rows06 = input_configurations(panel)
    for config in rows06:
        weights = config["Weights"]
        profile = config["Profile"]
        parts = getattr(panel, "score_blend_recipes", {}).get(profile)
        terms = sum((_terms(p["weights"], p["profile"], True, mass=p["mass"]) for p in parts), []) if parts else _terms(weights, profile, True)
        row = add(config["Configuration"], terms, True, "06/07", weights, profile)
        if config["Configuration"] == "Legacy 45d":
            row["method_id"] = "v11"
        if config["Configuration"] == "Blend 46d":
            row["method_id"] = "blend_46d"
        if config["Configuration"] == "Legacy 45d / 4 inputs / 6m CAGR + 1m Sortino":
            row["method_id"] = "focal_four"
    assert len(by_recipe) == 74
    manifest = json.loads((RUN_ROOT / "04" / "run-manifest.json").read_text())
    frozen = json.loads((RUN_ROOT / "04" / "frozen-matrices.json").read_text())
    for name, config in frozen.items():
        for missing in (True, False):
            parts = config.get("Components")
            terms = sum((_terms(p["weights"], p["profile"], missing, mass=p["mass"]) for p in parts), []) if parts else _terms(config["Weights"], config["Profile"], missing)
            add(f"04 {name} / missing={missing}", terms, missing, "04 frozen", config["Weights"], config["Profile"])
    for config in manifest["evaluations"]:
        if config.get("source_control"):
            excluded.append({"name": config["key"], "reason": "Source control uses original v11, already registered."})
            continue
        if np.count_nonzero(config["weights"]) == 1:
            excluded.append({"name": config["key"], "reason": "Single raw-feature diagnostic; not a composite scoring method."})
            continue
        missing = config.get("missing", False)
        parts = manifest["score_blend_recipes"].get(config["profile"])
        terms = sum((_terms(p["weights"], p["profile"], missing, config.get("calmar_cap", 5.0), p["mass"]) for p in parts), []) if parts else _terms(config["weights"], config["profile"], missing, config.get("calmar_cap", 5.0))
        add("04 evaluated " + config["key"], terms, missing, "04 implemented search", config["weights"], config["profile"])
    grid, mechanisms, _ = calibration_configurations()
    for config in grid + mechanisms:
        period = next(p for p, days in FEATURE_PERIODS.items() if days == config.risk_days)
        ci = FEATURES.index(("1y", "CAGR"))
        si = FEATURES.index((period, "Sortino"))

        def term(feature, coefficient, cap, transform):
            value = _terms(np.eye(len(FEATURES))[feature], "legacy", True)[0]
            value.update(coefficient=coefficient, cap=cap, transform=transform, ratio_floor=config.ratio_floor, risk_floor=0.0001 if config.ratio_floor else None)
            return value

        if config.transform == "blend":
            terms = [term(ci, 0.3, 0.5, "hard"), term(ci, 0.3, 1.0, "hard"), term(si, 0.2, 3.0, "hard"), term(si, 0.2, 7.0, "hard")]
        else:
            terms = [term(ci, 0.6, config.cagr_scale, config.transform), term(si, 0.4, config.sortino_scale, config.transform)]
        # The floor affects ratio denominators, never CAGR itself.
        for t in terms:
            if t["metric"] not in ("Sharpe", "Sortino"):
                t.update(ratio_floor=False, risk_floor=None)
        row = add("05 " + config.name, terms, not config.missing_zero, "05 implemented")
        if config.name == "Legacy 46d":
            row["method_id"] = "near_v6"
        if config.minimum_nonflat:
            row.setdefault("cohort_sensitivities", []).append({"name": config.name, "minimum_nonflat": config.minimum_nonflat, "days": config.risk_days})
    registry = list(by_recipe.values())
    assert len({r["method_id"] for r in registry}) == len(registry)
    return registry, excluded


def method_values(panel, row):
    """Evaluate the complete canonical recipe without mutating the source engine."""
    result = np.zeros(panel.raw.shape[:2])
    imputed = np.zeros(panel.raw.shape[:2], dtype=bool)
    for term in row["recipe"]["terms"]:
        feature = term["feature"]
        k, m = divmod(feature, 5)
        raw = panel.floored[:, :, k * 2 + m - 1] if term["ratio_floor"] and m in (1, 2) else panel.raw[:, :, feature]
        if term["transform"] == "inverse_drawdown":
            score = 1 - np.minimum(np.abs(raw), term["cap"]) / term["cap"]
        elif term["transform"] == "smooth":
            positive = np.maximum(raw, 0.0)
            score = positive / (positive + term["cap"])
        else:
            score = np.clip(raw / term["cap"], 0, 1)
        if row["missing_policy"] == "component_zero":
            imputed |= ~np.isfinite(score)
            score = np.nan_to_num(score, nan=0.0)
        result += term["coefficient"] * score
    return result, imputed


def forecast_origins():
    """Extend the Jan 1 four-day grid backwards without restarting its phase."""
    anchor = pd.Timestamp(PERIODS["2026"][0])
    first = pd.Timestamp(PERIODS["Long"][0])
    step = pd.Timedelta(days=4)
    offset = int(np.ceil((first - anchor) / step))
    return pd.date_range(anchor + offset * step, pd.Timestamp(PERIODS["Long"][1]) - pd.Timedelta(days=1), freq=step)


def _raw_daily(evaluator, manifest):
    """Preserve actual observation clocks and verify the share-price candle mapping."""
    dataset = ds.dataset(manifest["vault_prices"]["path"], format="parquet")
    columns = ["timestamp", "address", "share_price", "written_at", "total_assets", "total_supply", "permission_observed_at", "capacity_observed_at", "max_deposit", "leader_fraction", "daily_deposit_usd", "daily_withdrawal_usd", "hypercore_source", "permission_provenance"]
    columns = [c for c in columns if c in dataset.schema.names]
    frame = dataset.to_table(columns=columns, filter=(ds.field("chain") == 9999) & ds.field("address").isin(list(evaluator.panel.addresses.values()))).to_pandas().reset_index()
    frame["address"] = frame.address.str.lower()
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True).dt.tz_convert(None)
    frame = frame.sort_values(["address", "timestamp"], kind="stable")
    frame["date"] = frame.timestamp.dt.floor("D")
    valid = frame.share_price.gt(0) & np.isfinite(frame.share_price)
    frame = frame.loc[valid]
    count = frame.groupby(["address", "date"]).size().rename("raw_observations")
    daily = frame.groupby(["address", "date"], sort=False).tail(1).set_index(["address", "date"])
    daily = daily.join(count).reset_index()
    id_by_address = {address: pid for pid, address in evaluator.panel.addresses.items()}
    daily["pair_id"] = daily.address.map(id_by_address)
    daily = daily.rename(columns={"timestamp": "observed_at", "address": "vault_address", "share_price": "raw_close"})
    pairs = []
    for pid in evaluator.panel.pair_ids:
        candle = evaluator.universe.data_universe.candles.get_candles_by_pair(pid).copy()
        candle = candle[~candle.index.duplicated(keep="last")]
        piece = pd.DataFrame({"date": candle.index, "pair_id": pid, "close": candle.close.to_numpy(), "forward_filled": candle.get("forward_filled", pd.Series(False, index=candle.index)).to_numpy()})
        piece = piece[piece.date < pd.Timestamp(PERIODS["Long"][1])]
        pairs.append(piece)
    prices = pd.concat(pairs, ignore_index=True).merge(daily.drop(columns=["vault_address"]), on=["pair_id", "date"], how="left")
    prices["vault_address"] = prices.pair_id.map(evaluator.panel.addresses)
    prices["raw_observations"] = prices.raw_observations.fillna(0).astype("int32")
    finite = prices.raw_close.notna()
    equal = np.isclose(prices.loc[finite, "close"], prices.loc[finite, "raw_close"], rtol=1e-10, atol=1e-12)
    prices["mapping_matches"] = False
    prices.loc[finite, "mapping_matches"] = equal
    prices["source_close"] = prices.close
    prices = prices.sort_values(["pair_id", "date"])
    prices["close"] = prices.groupby("pair_id", sort=False).raw_close.ffill()
    prices["metric_forward_filled"] = prices.close.notna() & prices.raw_close.isna()
    prices["metric_observed_at"] = prices.groupby("pair_id", sort=False).observed_at.ffill()
    prices["price_guard_divergence"] = prices.raw_observations.gt(0) & ~prices.mapping_matches
    prices["supported_daily_mark"] = prices.raw_observations.gt(0) & prices.raw_close.gt(0)
    prices["candle_start_at"] = prices.date
    prices["candle_end_at"] = prices.date + pd.Timedelta(days=1)
    prices["publication_time_unknown"] = True
    prices["observation_age_at_close_hours"] = (prices.candle_end_at - prices.metric_observed_at).dt.total_seconds() / 3600
    prices = prices.sort_index()
    audit = {"raw_observation_rows": int(len(frame)), "daily_raw_rows": int(len(daily)), "compared_candle_closes": int(finite.sum()), "close_mismatches": int((~equal).sum()), "non_carried_close_mismatches": int(((~equal) & ~prices.loc[finite, "forward_filled"]).sum()), "mismatch_vaults": int(prices.loc[finite].loc[~equal, "pair_id"].nunique()), "max_close_absolute_error": float(np.abs(prices.loc[finite, "source_close"].to_numpy() - prices.loc[finite, "raw_close"].to_numpy()).max()), "clock_convention": "Daily label D aggregates observations in [D,D+1d); close equals last raw share_price. Forecast T anchor close D=T-1d is complete at T.", "publication_caveat": "written_at is archive update/write time, not an independently observed publication receipt. Publication history cannot be reconstructed.", "value_caveat": "share_price is cleaned per-share NAV; raw total_assets/total_supply diagnostics may differ because reconstruction removes cash flows."}
    prices.loc[finite].loc[~equal].to_csv(ARTIFACT_DIR / "candle-mapping-mismatches.csv", index=False)
    assert audit["non_carried_close_mismatches"] == 0, audit
    assert (prices.loc[finite, "observed_at"] < prices.loc[finite, "candle_end_at"]).all()
    return prices, audit


def _eligibility(evaluator, origins, prices):
    """Separate candidate indicators, current policy guards and entry permission."""
    from tradeexecutor.curator.curator import is_quarantined
    from tradeexecutor.backtest.backtest_pricing import BacktestPricing
    from tradeexecutor.backtest.backtest_routing import BacktestRoutingIgnoredModel
    from tradeexecutor.strategy.redemption import DepositCheckStage
    from tradeexecutor.backtest.backtest_pricing import HYPERCORE_DEPOSIT_STATE_CUTOFF

    panel = evaluator.panel
    strategy = evaluator.strategy
    guard = strategy.load_hypercore_vault_whitelist(strategy._guard_record_file())
    lookup = replace(evaluator.indicators, timestamp=None)
    reserve = evaluator.universe.reserve_assets[0].address
    pricing = BacktestPricing(evaluator.universe, BacktestRoutingIgnoredModel(reserve), data_delay_tolerance=pd.Timedelta(days=2), vault_state=evaluator.universe.vault_state)
    rows = []
    marked = prices.set_index(["date", "pair_id"])
    for date in origins:
        lookup.prepare_decision_cycle(0, date)
        included = lookup.get_indicator_value("inclusion_criteria", na_conversion=False)
        included = set([] if included is None else included)
        for pid in panel.pair_ids:
            pair = evaluator.universe.get_pair_by_id(pid)
            address = panel.addresses[pid]
            in_universe = pid in included
            gate = lookup.get_indicator_value("return_gate", pair=pair) if in_universe else np.nan
            gate_ok = gate is not None and np.isfinite(gate) and gate > evaluator.parameters.gate_threshold
            quarantine = bool(is_quarantined(address, date))
            blacklist = address in strategy.MANUAL_BLACKLIST or address in strategy.MASKED_VAULTS
            whitelisted = bool(guard.allows(address))
            check = pricing.check_deposit(date, pair, stage=DepositCheckStage.buy_rebalance)
            state = pricing._lookup_vault_state(date, pair)
            permission_clock = None if state is None else state.get("permission_observed_at")
            capacity_clock = None if state is None else state.get("capacity_observed_at")
            unknown_permission = date < HYPERCORE_DEPOSIT_STATE_CUTOFF or pd.isna(permission_clock)
            reasons = [name for name, rejected in [("not_source_inclusion", not in_universe), ("return_gate", not gate_ok), ("current_guard", not whitelisted), ("blacklist", blacklist), ("quarantine", quarantine), ("deposit_unavailable", not check.can_deposit)] if rejected]
            anchor = date - pd.Timedelta(days=1)
            key = (anchor, pid)
            raw = marked.loc[key] if key in marked.index else None
            origin_i = panel.date_index[date]
            j = panel.pair_index[pid]
            rows.append(
                {
                    "origin_at": date,
                    "feature_cutoff": date,
                    "pair_id": pid,
                    "vault_address": address,
                    "vault_name": panel.names[pid],
                    "origin_quarter": str(date.to_period("Q")),
                    "source_inclusion": in_universe,
                    "gate_value": gate,
                    "gate_passes": bool(gate_ok),
                    "current_guard_allows": whitelisted,
                    "blacklisted": blacklist,
                    "quarantined": quarantine,
                    "can_deposit": bool(check.can_deposit),
                    "deposit_reason": None if check.reason_code is None else check.reason_code.value,
                    "eligible_as_of_origin": not reasons,
                    "eligibility_reason": ", ".join(reasons) or "source_compatible_entry",
                    "eligibility_time_unknown": True,
                    "permission_time_unknown": bool(unknown_permission),
                    "guard_history_unknown": True,
                    "historical_confident_entry": False,
                    "permission_observed_at": permission_clock,
                    "capacity_observed_at": capacity_clock,
                    "max_deposit": None if state is None else state.get("max_deposit"),
                    "leader_fraction": None if state is None else state.get("leader_fraction"),
                    "anchor_observed_at": pd.NaT if raw is None else raw.metric_observed_at,
                    "anchor_supported": False if raw is None else bool(np.isfinite(raw.close)),
                    "anchor_actually_observed": False if raw is None else bool(raw.supported_daily_mark),
                    "anchor_forward_filled": False if raw is None else bool(raw.metric_forward_filled),
                    "nonflat_45d": int(panel.nonflat[origin_i, j, list(FEATURE_PERIODS).index("45d compatibility")]),
                    "entry_fee": 0.0,
                    "exit_fee": float(evaluator.parameters.vault_redemption_capital_fee),
                    "performance_fee": float(evaluator.parameters.vault_performance_fee),
                    "cost_known": False,
                    "source_modelled_costs": True,
                }
            )
    return pd.DataFrame(rows)


def _labels(evaluator, origins, prices):
    """Causally filled future windows, terminal censoring and delayed starts."""
    panel = evaluator.panel
    dates = pd.date_range(min(prices.date.min(), origins.min() - pd.Timedelta(days=1)), PERIODS["Long"][1] - datetime.timedelta(days=1))
    piv = prices.pivot(index="date", columns="pair_id", values="raw_close").reindex(index=dates, columns=panel.pair_ids).ffill()
    sup = prices.pivot(index="date", columns="pair_id", values="supported_daily_mark").reindex(index=dates, columns=panel.pair_ids).astype("boolean").fillna(False).astype(bool)
    obs = prices.pivot(index="date", columns="pair_id", values="observed_at").reindex(index=dates, columns=panel.pair_ids).ffill()
    filled = piv.notna() & ~sup
    source_piv = prices.pivot(index="date", columns="pair_id", values="source_close").reindex(index=dates, columns=panel.pair_ids)
    source_nav = source_piv.to_numpy()
    source_ret = source_piv.pct_change(fill_method=None).to_numpy()
    nav = piv.to_numpy()
    supported = sup.to_numpy(dtype=bool)
    observed = obs.to_numpy(dtype="datetime64[ns]")
    ret = piv.pct_change(fill_method=None).to_numpy()
    last_raw = prices[prices.supported_daily_mark].groupby("pair_id").date.max().reindex(panel.pair_ids).to_numpy(dtype="datetime64[ns]")
    chunks = []
    for h in HORIZONS + DIAGNOSTIC_HORIZONS:
        for delay in (DELAYS + (30,) if h == 30 else DELAYS if h in HORIZONS else (0,)):
            for origin in origins:
                anchor = origin - pd.Timedelta(days=1) + pd.Timedelta(days=delay)
                endpoint = anchor + pd.Timedelta(days=h)
                status = np.full(len(panel.pair_ids), "administrative_censoring", dtype=object)
                cagr = np.full(len(panel.pair_ids), np.nan)
                forward = cagr.copy()
                logret = cagr.copy()
                sharpe = cagr.copy()
                vol = cagr.copy()
                low = np.zeros(len(panel.pair_ids), bool)
                anchor_nav = cagr.copy()
                target_nav = cagr.copy()
                observed_count = np.zeros(len(panel.pair_ids), "int32")
                target_observed = np.full(len(panel.pair_ids), np.datetime64("NaT"), dtype="datetime64[ns]")
                anchor_observed = target_observed.copy()
                flat = np.zeros(len(panel.pair_ids), "int32")
                carried = flat.copy()
                if anchor in dates and endpoint in dates:
                    ai = dates.get_loc(anchor)
                    ei = ai + h
                    window = nav[ai : ei + 1]
                    supported_window = supported[ai : ei + 1]
                    terminal = np.isnat(last_raw) | (endpoint.to_datetime64() > last_raw)
                    good = np.isfinite(window).all(axis=0) & (window > 0).all(axis=0) & ~terminal
                    anchor_nav = nav[ai]
                    target_nav = nav[ei]
                    target_observed = observed[ei]
                    anchor_observed = observed[ai]
                    status[:] = "unsupported_daily_gap"
                    status[np.isnat(last_raw) | (endpoint.to_datetime64() > last_raw)] = "vault_disappearance_or_terminal_coverage"
                    status[~np.isfinite(anchor_nav)] = "anchor_missing_or_prelaunch"
                    endpoints = np.isfinite(anchor_nav) & np.isfinite(target_nav) & (anchor_nav > 0) & (target_nav > 0) & ~terminal
                    status[endpoints] = "endpoints_only"
                    status[good] = "complete"
                    observed_count = supported_window.sum(axis=0).astype("int32")
                    if endpoints.any():
                        endpoint_ratio = target_nav[endpoints] / anchor_nav[endpoints]
                        forward[endpoints] = endpoint_ratio - 1
                        logret[endpoints] = np.log(endpoint_ratio)
                        with np.errstate(over="ignore"):
                            cagr[endpoints] = np.expm1(logret[endpoints] * 365 / h)
                    daily = ret[ai + 1 : ei + 1]
                    selected = daily[:, good]
                    if good.any():
                        means = selected.mean(axis=0)
                        sigma = selected.std(axis=0, ddof=1) if h > 1 else np.full(selected.shape[1], np.nan)
                        ratio = target_nav[good] / anchor_nav[good]
                        forward[good] = ratio - 1.0
                        logret[good] = np.log(ratio)
                        with np.errstate(over="ignore"):
                            cagr[good] = np.expm1(logret[good] * 365 / h)
                        valid_sigma = sigma > 0
                        current = np.full(len(sigma), np.nan)
                        current[valid_sigma] = means[valid_sigma] / sigma[valid_sigma] * np.sqrt(365)
                        sharpe[good] = current
                        vol[good] = sigma * np.sqrt(365)
                        low[good] = sigma < 0.0001
                        flat[good] = (np.abs(selected) <= 1e-12).sum(axis=0)
                    carried = filled.iloc[ai : ei + 1].sum().to_numpy(dtype="int32")
                ratio = np.exp(logret)
                capital = float(evaluator.parameters.vault_redemption_capital_fee)
                performance = float(evaluator.parameters.vault_performance_fee)
                net = ratio * (1 - capital) - performance * np.maximum(ratio - 1, 0)
                chunk = pd.DataFrame(
                    {
                        "origin_at": origin,
                        "pair_id": panel.pair_ids,
                        "lookahead_days": h,
                        "delay_days": delay,
                        "nav_anchor_at": anchor,
                        "nav_target_at": endpoint,
                        "label_available_at": endpoint + pd.Timedelta(days=1),
                        "anchor_observed_at": anchor_observed,
                        "target_observed_at": target_observed,
                        "anchor_nav": anchor_nav,
                        "target_nav": target_nav,
                        "future_return": forward,
                        "future_log_return": logret,
                        "future_cagr": cagr,
                        "future_sharpe": sharpe,
                        "realised_volatility": vol,
                        "target_status": status,
                        "return_supported": np.isfinite(logret),
                        "sharpe_supported": np.isfinite(sharpe),
                        "sharpe_path_supported": status == "complete",
                        "actual_complete_path": observed_count == h + 1,
                        "target_daily_observation_count": observed_count,
                        "target_daily_observation_fraction": observed_count / (h + 1),
                        "low_variance": low,
                        "flat_return_days": flat,
                        "carried_mark_days": carried,
                        "future_net_log_return": np.log(net),
                        "entry_fee": 0.0,
                        "exit_fee": capital,
                        "performance_fee": performance,
                        "cost_known": False,
                        "source_modelled_costs": True,
                    }
                )
                approx_return = np.full(len(panel.pair_ids), np.nan)
                approx_sharpe = approx_return.copy()
                approx_logret = approx_return.copy()
                approx_status = np.full(len(panel.pair_ids), "administrative_censoring", dtype=object)
                if anchor in dates and endpoint in dates:
                    ai = dates.get_loc(anchor)
                    ei = ai + h
                    source_window = source_nav[ai : ei + 1]
                    approximate = np.isfinite(source_window).all(axis=0) & (source_window > 0).all(axis=0)
                    approximate &= ~np.isnat(last_raw) & (endpoint.to_datetime64() <= last_raw)
                    approx_status[:] = "missing_or_terminal_source_coverage"
                    approx_status[approximate] = "framework_daily_marks_approximate"
                    approx_status[approximate & (status == "complete")] = "actual_daily_observations"
                    ratio = source_nav[ei, approximate] / source_nav[ai, approximate]
                    approx_return[approximate] = ratio - 1
                    approx_logret[approximate] = np.log(ratio)
                    daily = source_ret[ai + 1 : ei + 1, approximate]
                    if h > 1 and approximate.any():
                        sigma = daily.std(axis=0, ddof=1)
                        mu = daily.mean(axis=0)
                        valid_sigma = sigma > 0
                        ss = np.full(len(sigma), np.nan)
                        ss[valid_sigma] = mu[valid_sigma] / sigma[valid_sigma] * np.sqrt(365)
                        approx_sharpe[approximate] = ss
                chunk["framework_future_return"] = approx_return
                chunk["framework_future_log_return"] = approx_logret
                with np.errstate(over="ignore"):
                    chunk["framework_future_cagr"] = np.expm1(chunk.framework_future_log_return * 365 / h)
                chunk["framework_future_sharpe"] = approx_sharpe
                chunk["framework_target_status"] = approx_status
                chunk["annualisation_overflow"] = np.isinf(chunk.future_cagr)
                chunk["future_cagr"] = chunk.future_cagr.replace([np.inf, -np.inf], np.nan)
                chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)


def _score_audit(evaluator, registry, origins):
    """Compare original v11 against its source indicator, including missingness."""
    panel = evaluator.panel
    row = next(r for r in registry if r["method_id"] == "v11")
    values, _ = method_values(panel, row)
    lookup = replace(evaluator.indicators, timestamp=None)
    rows = []
    chosen = origins[:: max(1, len(origins) // 20)]
    for date in chosen:
        lookup.prepare_decision_cycle(0, date)
        for pid in panel.pair_ids[:: max(1, len(panel.pair_ids) // 25)]:
            pair = evaluator.universe.get_pair_by_id(pid)
            original = lookup.get_indicator_value(evaluator.parameters.selection_score_indicator, pair=pair)
            original = np.nan if original is None else float(original)
            candidate = values[panel.date_index[date], panel.pair_index[pid]]
            same = bool((np.isnan(original) and np.isnan(candidate)) or np.isclose(original, candidate, rtol=1e-9, atol=1e-10))
            rows.append({"origin_at": date, "pair_id": pid, "source_score": original, "registry_score": candidate, "matches": same})
    frame = pd.DataFrame(rows)
    frame.to_csv(ARTIFACT_DIR / "source-score-audit.csv", index=False)
    assert frame.matches.all(), frame[~frame.matches].head().to_dict("records")
    return {"observations": len(frame), "finite": int(frame.source_score.notna().sum()), "missing": int(frame.source_score.isna().sum()), "all_match": bool(frame.matches.all())}


# Original generation identity retained only for this display-only filename migration.
ORIGINAL_GENERATION_SHA256 = "fefb9c10222213a387974371b21afb55076b23ffc020fba59a98ccf1084c57e1"
ORIGINAL_DATA_FINGERPRINT = "1771b0a1df256221a02e499ac706db7a8cd0b1f2f3cf516206d9d7dbaafdc749"
APPROVED_PIPELINE_AST_SHA256 = "f1cd4ee50c0d93cf7b299c0190a67ff777fcca90ebc1391e6fe282f83ff4dcae"


def target_coverage(labels):
    """Summarise observed NAV target support independently of score-method coverage."""
    records = []
    for period, (start, end) in PERIODS.items():
        for h in HORIZONS:
            sub = labels[(labels.origin_at >= start) & (labels.origin_at < end) & labels.lookahead_days.eq(h) & labels.delay_days.eq(0)]
            complete = sub.target_status.eq("complete")
            matured = sub.target_status.ne("administrative_censoring")
            records.append({"period": period, "lookahead_days": h, "scheduled_origins": sub.origin_at.nunique(), "matured_origins": sub.loc[matured, "origin_at"].nunique(), "last_matured_origin": str(sub.loc[matured, "origin_at"].max()), "complete_pairs": int(complete.sum()), "return_endpoint_pairs": int(sub.return_supported.sum()), "sharpe_finite_pairs": int(sub.sharpe_supported.sum()), "endpoint_only_pairs": int(sub.target_status.eq("endpoints_only").sum()), "framework_approximate_pairs": int(sub.framework_future_return.notna().sum()), "vaults_with_complete_target": sub.loc[complete, "pair_id"].nunique(), "complete_fraction_all_vault_origins": complete.mean(), "administrative_censoring_fraction": (~matured).mean(), "flat_target_fraction_complete": sub.loc[complete, "flat_return_days"].eq(h).mean(), "low_variance_fraction_complete": sub.loc[complete, "low_variance"].mean()})
    return pd.DataFrame(records)


def _pipeline_ast_hash(source=None):
    """Hash all frame derivation code and constants outside reader-only helpers.

    The complete :func:`prepare_data` orchestration is included deliberately:
    even a later display edit there must be reviewed before reusing old frames.
    Comments and formatting do not affect the semantic AST identity.
    """
    tree = ast.parse(Path(__file__).read_text() if source is None else source)
    excluded_functions = {"target_coverage", "load_data", "_cache_identity_matches", "_record_reader_migration", "_pipeline_ast_hash"}
    excluded_constants = {"ORIGINAL_GENERATION_SHA256", "ORIGINAL_DATA_FINGERPRINT", "APPROVED_PIPELINE_AST_SHA256"}
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in excluded_functions:
            continue
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) and t.id in excluded_constants for t in node.targets):
            continue
        if isinstance(node, ast.If) and ast.unparse(node.test) == "__name__ == '__main__'":
            continue
        nodes.append(node)
    semantic_tree = ast.Module(body=nodes, type_ignores=[])
    return hashlib.sha256(ast.dump(semantic_tree, include_attributes=False).encode()).hexdigest()


def _cache_identity_matches(provenance, manifest, source_hash, reader_hash):
    """Accept this reader's generation or the single approved display-only migration."""
    generation_hash = provenance.get("module_sha256")
    allowed = generation_hash == reader_hash or (generation_hash == ORIGINAL_GENERATION_SHA256 and provenance.get("fingerprint") == ORIGINAL_DATA_FINGERPRINT and _pipeline_ast_hash() == APPROVED_PIPELINE_AST_SHA256)
    expected = _json_hash({"design": generation_hash, "source": source_hash, "input": manifest})
    return bool(allowed and provenance.get("fingerprint") == expected and provenance.get("source_fingerprint") == source_hash and provenance.get("inputs") == manifest)


def _record_reader_migration(provenance, reader_hash):
    """Record reader identity without changing the immutable frame-generation identity."""
    provenance["original_generation_sha256"] = provenance["module_sha256"]
    provenance["reader_sha256"] = reader_hash
    if provenance["module_sha256"] != reader_hash:
        provenance["reader_cache_migration"] = {"reason": "Display-only coverage filename collision repair; score, label, eligibility and price frames unchanged.", "from_generation_sha256": provenance["module_sha256"], "to_reader_sha256": reader_hash, "preserved_data_fingerprint": provenance["fingerprint"], "target_coverage_path": "target-coverage.csv", "approved_pipeline_ast_sha256": APPROVED_PIPELINE_AST_SHA256, "reader_pipeline_ast_sha256": _pipeline_ast_hash()}
    (ARTIFACT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))


def load_data():
    """Load the immutable lightweight artefacts without preparing an evaluator."""
    result = {"registry": json.loads((ARTIFACT_DIR / "registry.json").read_text()), "provenance": json.loads((ARTIFACT_DIR / "provenance.json").read_text())}
    for name in ("scores", "labels", "eligibility", "prices"):
        result[name] = pd.read_parquet(ARTIFACT_DIR / f"{name}.parquet")
    manifest = json.loads((INPUT_DIR / "downloads.json").read_text())
    frozen = json.loads((ARTIFACT_DIR / "frozen-design.json").read_text())
    reader_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if not _cache_identity_matches(result["provenance"], manifest, frozen["source_fingerprint"], reader_hash):
        raise ValueError("Forecast cache identity is not a recognised generation; call prepare_data() to rebuild.")
    if frozen["fingerprint"] != result["provenance"]["fingerprint"] or frozen["module_sha256"] != result["provenance"]["module_sha256"]:
        raise ValueError("Forecast frozen design and frame provenance differ.")
    # Statistics owns coverage.csv. Always derive this small display summary from labels.
    result["coverage"] = target_coverage(result["labels"])
    result["coverage"].to_csv(ARTIFACT_DIR / "target-coverage.csv", index=False)
    _record_reader_migration(result["provenance"], reader_hash)
    return result


def prepare_data(force=False):
    """Verify the pinned inputs, freeze this module and persist reusable frames."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((INPUT_DIR / "downloads.json").read_text())
    for key in ("vault_prices", "vault_metadata"):
        assert hashlib.sha256(Path(manifest[key]["path"]).read_bytes()).hexdigest() == manifest[key]["sha256"]
    design_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        evaluator, _, _, source_hash = create_evaluator()
    fingerprint = _json_hash({"design": design_hash, "source": source_hash, "input": manifest})
    previous = ARTIFACT_DIR / "provenance.json"
    if not force and previous.exists() and _cache_identity_matches(json.loads(previous.read_text()), manifest, source_hash, design_hash):
        result = load_data()
        result["evaluator"] = evaluator
        # Register composite profiles before execution workers reuse the evaluator.
        input_configurations(evaluator.panel)
        return result
    (ARTIFACT_DIR / "frozen-design.json").write_text(json.dumps({"fingerprint": fingerprint, "module_sha256": design_hash, "source_fingerprint": source_hash}, indent=2))
    registry, excluded = build_registry(evaluator.panel)
    origins = forecast_origins()
    prices, raw_audit = _raw_daily(evaluator, manifest)
    eligibility = _eligibility(evaluator, origins, prices)
    labels = _labels(evaluator, origins, prices)
    audit = _score_audit(evaluator, registry, origins)
    base = eligibility[["origin_at", "pair_id", "vault_address", "origin_quarter", "eligible_as_of_origin", "eligibility_time_unknown"]].copy()
    for col in ("vault_address", "origin_quarter"):
        base[col] = base[col].astype("category")
    ii = [evaluator.panel.date_index[t] for t in origins]
    chunks = []
    for row in registry:
        values, imputed = method_values(evaluator.panel, row)
        piece = base.copy()
        piece["method_id"] = row["method_id"]
        piece["score"] = values[ii].reshape(-1)
        piece["score_imputed"] = imputed[ii].reshape(-1)
        piece["score_missing_reason"] = np.where(piece.score.isna(), "component_unavailable_or_undefined", "")
        piece["rank_percentile"] = piece.score.where(piece.eligible_as_of_origin).groupby(piece.origin_at).rank(method="average", pct=True)
        piece["score_saturated"] = piece.score.ge(1 - 1e-12)
        chunks.append(piece)
    scores = pd.concat(chunks, ignore_index=True)
    for col in ("method_id", "score_missing_reason"):
        scores[col] = scores[col].astype("category")
    coverage = target_coverage(labels)
    provenance = {
        "fingerprint": fingerprint,
        "module_sha256": design_hash,
        "original_generation_sha256": design_hash,
        "reader_sha256": design_hash,
        "source_fingerprint": source_hash,
        "inputs": manifest,
        "methods": len(registry),
        "expected_scatter_figures": 3 * len(registry),
        "original_06_methods": 74,
        "excluded": excluded,
        "source_score_audit": audit,
        "raw_mapping_audit": raw_audit,
        "feature_lookbacks": FEATURE_PERIODS,
        "periods": {key: list(map(str, values)) for key, values in PERIODS.items()},
        "origin_anchor": "2026-01-01 UTC, every four calendar days extended backwards",
        "origins": list(map(str, origins)),
        "universe_pairs": len(evaluator.panel.pair_ids),
        "guard_history_unknown": True,
        "historically_complete_universe_verified": False,
        "fee_model": "Source estimated 0.1% capital redemption allowance plus 10% of positive profit; not measured charges. No extra management/performance fee double-counting.",
        "caveats": ["Current universe/guard snapshots lack historical admission receipts; eligibility is source-compatible, not proven historically known.", "Unknown independent permission/capacity clocks preserved; no conversion to zero cap.", "Archive contains cleaned/reconstructed NAV. Written-at proves archive writing, not contemporaneous publication.", "All primary metrics use positive raw NAV causally forward-filled on calendar days; no backfill before first mark or labels after last actual mark/archive end. Actual observation counts and carried marks remain separate. Flat ratios remain undefined. Positive tiny collapse prices suppressed by framework guards remain in targets. Framework guarded prices are a separate sensitivity.", "Both history periods were used for method selection before this research; no untouched holdout."],
    }
    for name, frame in [("scores", scores), ("labels", labels), ("eligibility", eligibility), ("prices", prices)]:
        frame.to_parquet(ARTIFACT_DIR / f"{name}.parquet", index=False)
    coverage.to_csv(ARTIFACT_DIR / "target-coverage.csv", index=False)
    (ARTIFACT_DIR / "registry.json").write_text(json.dumps(registry, indent=2))
    (ARTIFACT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2))
    return {"registry": registry, "scores": scores, "labels": labels, "eligibility": eligibility, "prices": prices, "coverage": coverage, "provenance": provenance, "evaluator": evaluator}


if __name__ == "__main__":
    data = prepare_data()
    print(json.dumps({"methods": len(data["registry"]), "scores": len(data["scores"]), "labels": len(data["labels"]), "coverage": data["coverage"].to_dict("records")}, indent=2))
