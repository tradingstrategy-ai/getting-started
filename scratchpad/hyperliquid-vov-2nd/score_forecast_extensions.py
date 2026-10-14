"""Population, observation-basis and market-factor sensitivities for notebook 08."""

import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from score_forecast_data import ARTIFACT_DIR, FOCAL_METHOD_IDS
from score_forecast_statistics import join_method, date_ic, uncertainty

EXTENSION_DIR = ARTIFACT_DIR / "extensions"
HORIZONS = (7, 30, 90)
TARGETS = {"return": "future_log_return", "sharpe": "future_sharpe"}

DESCRIPTIONS = {
    "cohort_summary": "Same frozen scores across eligible, observed, common-score, guard, age and activity cohorts. Guard comparisons use current policy retrospectively within the fixed 514-vault parent universe; they do not recover excluded historical vaults.",
    "cohort_ic_dates": "Within-origin cross-sectional Spearman IC for each focal score and declared cohort. Fewer than ten pairs or five distinct scores remain unsupported.",
    "target_basis_summary": "Causally filled raw NAV targets versus framework guarded/filled prices. Both retain held-NAV assumptions; carried prices are not extra actual observations.",
    "common_origin_summary": "Horizon-specific dates versus dates shared by all three horizons. A second comparison fixes both origin and vault identities across horizons for each target.",
    "market_adjusted_summary": "Raw future log-return IC versus BTC/ETH exposure-adjusted IC on the identical beta-supported population. Betas use the past 90 daily returns with at least 60 supported calendar returns; actual paired observations are counted separately, with no future beta fitting or leading backfill.",
    "market_beta": "Per-origin, per-vault joint BTC/ETH regression betas and fit support. Returns are daily close-to-close log changes from causal NAV carry. Actual observation support is recorded separately. The regression intercept is retained in the future residual so it represents excess profitability rather than being removed.",
    "market_reference_status": "Reference data availability, cache provenance and source fingerprints. Unavailable prices are reported explicitly without substituting another market series.",
    "market_residuals": "Gross vault horizon log return minus past-estimated beta times each reference horizon log return. Raw and adjusted comparisons use the same vault/date rows.",
}


def _summary(frame, target, tags):
    """Keep empty and tied populations explicit instead of manufacturing an IC."""
    paired = np.isfinite(frame.score) & np.isfinite(frame[target]) if len(frame) else np.array([], dtype=bool)
    base = dict(tags, rows=len(frame), paired_rows=int(paired.sum()), paired_vaults=int(frame.loc[paired, "pair_id"].nunique()) if len(frame) else 0, origin_count=int(frame.origin_at.nunique()) if len(frame) else 0)
    if frame.empty:
        return dict(base, mean_ic=np.nan, supported_origins=0, inference_status="empty_cohort"), pd.DataFrame()
    ic = date_ic(frame, target)
    return dict(base, **uncertainty(ic, tags["lookahead_days"], tags["period"])), ic.assign(**tags)


def _common_scores(data):
    scores = data["scores"]
    small = scores.loc[scores.method_id.isin(FOCAL_METHOD_IDS), ["origin_at", "pair_id", "method_id", "score"]]
    finite = small[np.isfinite(small.score)]
    counts = finite.groupby(["origin_at", "pair_id"], observed=True).method_id.nunique()
    return set(counts[counts.eq(len(FOCAL_METHOD_IDS))].index)


def cohort_analysis(data):
    """Compare fixed policies and causal age/activity without altering selectors."""
    common = _common_scores(data)
    first = data["prices"][data["prices"].supported_daily_mark].groupby("pair_id").date.min()
    rows, dates = [], []
    for method in FOCAL_METHOD_IDS:
        for h in HORIZONS:
            full = join_method(data, method, h, "Long", population="observed")
            full["vault_age_days"] = (full.origin_at - full.pair_id.map(first)).dt.total_seconds() / 86400
            common_mask = pd.MultiIndex.from_frame(full[["origin_at", "pair_id"]]).isin(common)
            eligible = full.eligible_as_of_origin.fillna(False)
            masks = {"all_observed_parent_universe": pd.Series(True, index=full.index), "source_compatible_eligible": eligible, "eligible_common_focal_finite_score": eligible & common_mask, "current_guard_allows_only_retrospective": full.current_guard_allows.fillna(False), "current_guard_denies_only_retrospective": ~full.current_guard_allows.fillna(False), "eligible_age_under_360_days": eligible & full.vault_age_days.between(0, 360, inclusive="left"), "eligible_age_360_days_or_more": eligible & full.vault_age_days.ge(360), "eligible_active_at_least_10_of_45": eligible & full.nonflat_45d.ge(10), "eligible_activity_under_10_of_45": eligible & full.nonflat_45d.lt(10)}
            for period, start in [("2026", pd.Timestamp("2026-01-01")), ("Long", pd.Timestamp("2023-03-01"))]:
                for cohort, mask in masks.items():
                    frame = full[mask & full.origin_at.ge(start)]
                    for outcome, target in TARGETS.items():
                        tags = {"method_id": method, "lookahead_days": h, "period": period, "cohort": cohort, "outcome": outcome, "historical_policy_verified": False}
                        summary, ic = _summary(frame, target, tags)
                        rows.append(summary)
                        if not ic.empty:
                            dates.append(ic)
    return {"cohort_summary": pd.DataFrame(rows), "cohort_ic_dates": pd.concat(dates, ignore_index=True) if dates else pd.DataFrame()}


def target_basis_analysis(data):
    """Separate exact raw support from the parent's interpolation convention."""
    rows, dates = [], []
    for method in FOCAL_METHOD_IDS:
        for h in HORIZONS:
            full = join_method(data, method, h, "Long")
            for period, mask in [("2026", full.origin_at.ge("2026-01-01")), ("Long", full.origin_at.ge("2023-03-01")), ("Pre-2026", full.origin_at.lt("2026-01-01"))]:
                frame = full[mask]
                for outcome, target in TARGETS.items():
                    alternative = "framework_" + target
                    common = np.isfinite(frame[target]) & np.isfinite(frame[alternative])
                    cohorts = [("causally_filled_raw_own_valid", frame, target), ("framework_filled_own_valid_approximation", frame, alternative), ("causally_filled_raw_common_valid", frame[common], target), ("framework_filled_common_valid_approximation", frame[common], alternative)]
                    for basis, population, column in cohorts:
                        # Pre-2026 inherits long-history inference support rules.
                        tags = {"method_id": method, "lookahead_days": h, "period": "Long" if period == "Pre-2026" else period, "report_period": period, "basis": basis, "outcome": outcome}
                        summary, ic = _summary(population, column, tags)
                        rows.append(summary)
                        if not ic.empty:
                            dates.append(ic)
    return {"target_basis_summary": pd.DataFrame(rows), "target_basis_ic_dates": pd.concat(dates, ignore_index=True) if dates else pd.DataFrame()}


def common_origin_analysis(data):
    """Compare equal forecast dates and equal vault/date pairs across horizons."""
    rows = []
    for method in FOCAL_METHOD_IDS:
        frames = {h: join_method(data, method, h, "2026") for h in HORIZONS}
        for outcome, target in TARGETS.items():
            origin_sets = []
            pair_sets = []
            for h, frame in frames.items():
                valid = frame[np.isfinite(frame.score) & np.isfinite(frame[target])]
                origin_sets.append(set(valid.origin_at))
                pair_sets.append(set(pd.MultiIndex.from_frame(valid[["origin_at", "pair_id"]])))
            common_dates = set.intersection(*origin_sets)
            common_pairs = set.intersection(*pair_sets)
            for h, frame in frames.items():
                index = pd.MultiIndex.from_frame(frame[["origin_at", "pair_id"]])
                cases = [("horizon_specific_origins", frame), ("common_origins_all_horizons", frame[frame.origin_at.isin(common_dates)]), ("common_origins_and_vaults_all_horizons", frame[index.isin(common_pairs)])]
                for cohort, population in cases:
                    tags = {"method_id": method, "lookahead_days": h, "period": "2026", "cohort": cohort, "outcome": outcome}
                    summary, _ = _summary(population, target, tags)
                    rows.append(summary)
    return {"common_origin_summary": pd.DataFrame(rows)}


def market_analysis(data):
    """Use official cached reference closes and strictly past joint market betas."""
    from tradingstrategy.binance.price import fetch_binance_price
    import duckdb

    status = []
    references = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        try:
            frame = fetch_binance_price(symbol=symbol, start=datetime.datetime(2025, 10, 1), request_timeout=8.0)
        except (requests.exceptions.RequestException, duckdb.IOException) as error:
            status.append({"symbol": symbol, "status": "unavailable", "error_type": type(error).__name__, "message": str(error)[:300]})
            continue
        frame = frame[frame.index < pd.Timestamp("2026-10-05")].copy()
        references[symbol] = frame.close
        digest = hashlib.sha256(pd.util.hash_pandas_object(frame[["close"]], index=True).to_numpy().tobytes()).hexdigest()
        status.append({"symbol": symbol, "status": "available", "daily_candles": len(frame), "first_daily_label": str(frame.index.min()), "last_daily_label": str(frame.index.max()), "reference_sha256": digest, "timestamp_convention": "UTC open-labelled daily candle; its close is completed at label+1d."})
        frame.to_parquet(EXTENSION_DIR / f"{symbol.lower()}-reference.parquet")
    status_frame = pd.DataFrame(status)
    empty = {"market_reference_status": status_frame, "market_adjusted_summary": pd.DataFrame(), "market_beta": pd.DataFrame(), "market_residuals": pd.DataFrame()}
    if len(references) != 2:
        return empty
    refs = pd.DataFrame(references).sort_index()
    reference_calendar = pd.date_range(refs.index.min(), pd.Timestamp("2026-10-04"))
    last_reference_marks = refs.apply(lambda col: col.last_valid_index())
    refs = refs.reindex(reference_calendar).ffill()
    for symbol in refs:
        refs.loc[refs.index > last_reference_marks[symbol], symbol] = np.nan
        references[symbol] = refs[symbol]
    ref_log = np.log(refs).diff()
    prices = data["prices"]
    vault = prices.pivot(index="date", columns="pair_id", values="close").sort_index()
    daily = pd.date_range("2025-10-01", "2026-10-04")
    vault = vault.reindex(daily).ffill()
    actual = prices.pivot(index="date", columns="pair_id", values="supported_daily_mark").reindex(index=daily, columns=vault.columns).astype("boolean").fillna(False).astype(bool)
    actual_return_pairs = actual & actual.shift(1, fill_value=False)
    vault_log = np.log(vault).diff()
    ref_log = ref_log.reindex(daily)
    origins = sorted(data["eligibility"].loc[data["eligibility"].origin_at.ge("2026-01-01"), "origin_at"].unique())
    beta_rows = []
    for date in origins:
        origin = pd.Timestamp(date)
        window = pd.date_range(origin - pd.Timedelta(days=90), origin - pd.Timedelta(days=1))
        factors = ref_log.reindex(window).to_numpy()
        y_matrix = vault_log.reindex(window).to_numpy()
        actual_matrix = actual_return_pairs.reindex(window).fillna(False).to_numpy(dtype=bool)
        for j, pid in enumerate(vault.columns):
            y = y_matrix[:, j]
            good = np.isfinite(y) & np.isfinite(factors).all(axis=1)
            count = int(good.sum())
            row = {"origin_at": origin, "pair_id": int(pid), "past_return_days": 90, "paired_calendar_daily_returns": count, "paired_actual_daily_returns": int((good & actual_matrix[:, j]).sum()), "carried_return_days": int((good & ~actual_matrix[:, j]).sum()), "beta_supported": False, "beta_btc": np.nan, "beta_eth": np.nan, "past_intercept_daily_log": np.nan, "condition_number": np.nan, "fit_r_squared": np.nan, "beta_status": "fewer_than_60_supported_calendar_returns"}
            if count >= 60:
                design = np.column_stack([np.ones(count), factors[good]])
                condition = float(np.linalg.cond(design))
                row["condition_number"] = condition
                if condition <= 1e8:
                    coef = np.linalg.lstsq(design, y[good], rcond=None)[0]
                    residual = y[good] - design @ coef
                    variance = np.sum((y[good] - y[good].mean()) ** 2)
                    row.update(beta_supported=True, beta_btc=float(coef[1]), beta_eth=float(coef[2]), past_intercept_daily_log=float(coef[0]), fit_r_squared=1 - float(residual @ residual) / variance if variance > 0 else np.nan, beta_status="supported")
                else:
                    row["beta_status"] = "ill_conditioned_past_market_design"
            beta_rows.append(row)
    betas = pd.DataFrame(beta_rows)
    labels = data["labels"]
    labels = labels[labels.origin_at.ge("2026-01-01") & labels.lookahead_days.isin(HORIZONS) & labels.delay_days.eq(0)]
    outcomes = labels[["origin_at", "pair_id", "lookahead_days", "nav_anchor_at", "nav_target_at", "future_log_return"]].merge(betas, on=["origin_at", "pair_id"], how="left")
    for symbol, factor in [("BTCUSDT", "btc"), ("ETHUSDT", "eth")]:
        values = references[symbol]
        begin = outcomes.nav_anchor_at.map(values)
        end = outcomes.nav_target_at.map(values)
        outcomes["future_" + factor + "_log_return"] = np.log(end / begin)
    outcomes["future_market_residual_log_return"] = outcomes.future_log_return - outcomes.beta_btc * outcomes.future_btc_log_return - outcomes.beta_eth * outcomes.future_eth_log_return
    outcomes.loc[~outcomes.beta_supported.fillna(False), "future_market_residual_log_return"] = np.nan
    rows = []
    for method in FOCAL_METHOD_IDS:
        for h in HORIZONS:
            frame = join_method(data, method, h, "2026").merge(outcomes[outcomes.lookahead_days.eq(h)][["origin_at", "pair_id", "future_market_residual_log_return"]], on=["origin_at", "pair_id"], how="left", validate="one_to_one")
            good = np.isfinite(frame.future_log_return) & np.isfinite(frame.future_market_residual_log_return)
            for basis, population, target in [("raw_all_eligible", frame, "future_log_return"), ("raw_same_beta_supported_population", frame[good], "future_log_return"), ("market_adjusted_same_population", frame[good], "future_market_residual_log_return")]:
                tags = {"method_id": method, "lookahead_days": h, "period": "2026", "basis": basis, "outcome": "log_return"}
                summary, _ = _summary(population, target, tags)
                rows.append(summary)
    return {"market_reference_status": status_frame, "market_adjusted_summary": pd.DataFrame(rows), "market_beta": betas, "market_residuals": outcomes}


def _presentation(result, include_details):
    """Keep large point-level artefacts out of default notebook table output."""
    summary_names = {"cohort_summary", "target_basis_summary", "common_origin_summary", "market_adjusted_summary", "market_reference_status"}
    visible = dict(result) if include_details else {name: frame for name, frame in result.items() if name in summary_names}
    visible["descriptions"] = DESCRIPTIONS
    return visible


def run_extensions(data, statistics=None, force=False, include_details=False):
    """Persist all extension frames, returning concise notebook summaries by default.

    :param include_details: Include generated per-date IC, beta and residual frames.
    """
    EXTENSION_DIR.mkdir(parents=True, exist_ok=True)
    source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    stats_source = hashlib.sha256((Path(__file__).parent / "score_forecast_statistics.py").read_bytes()).hexdigest()
    fingerprint = hashlib.sha256((source + stats_source + data["provenance"]["fingerprint"]).encode()).hexdigest()
    manifest_file = EXTENSION_DIR / "completed.json"
    if not force and manifest_file.exists():
        manifest = json.loads(manifest_file.read_text())
        if manifest["fingerprint"] == fingerprint:
            result = {name: pd.read_parquet(EXTENSION_DIR / f"{name}.parquet") for name in manifest["frames"]}
            return _presentation(result, include_details)
    result = {}
    result.update(cohort_analysis(data))
    result.update(target_basis_analysis(data))
    result.update(common_origin_analysis(data))
    result.update(market_analysis(data))
    for name, frame in result.items():
        frame.to_parquet(EXTENSION_DIR / f"{name}.parquet", index=False)
        if name not in ("cohort_ic_dates", "target_basis_ic_dates", "market_residuals", "market_beta"):
            with np.errstate(invalid="ignore"):
                frame.to_csv(EXTENSION_DIR / f"{name}.csv", index=False)
    manifest_file.write_text(json.dumps({"fingerprint": fingerprint, "module_sha256": source, "statistics_source_sha256": stats_source, "data_fingerprint": data["provenance"]["fingerprint"], "frames": list(result), "method_ids": list(FOCAL_METHOD_IDS), "period_default": "2026", "market_reference_status": result["market_reference_status"].to_dict("records"), "caveats": ["Frozen current parent universe excludes some earlier vaults; all-observed means all 514 parent members.", "Current guards/curator policy have no independently recorded historical admission timestamps.", "Pre-2026 actual observations are sparse; primary daily metrics use a held-NAV carry assumption, with actual masks retained.", "Vault observations are intraday last marks whereas reference close is midnight UTC; factor residuals inherit this timing noise.", "Betas are simple retrospective diagnostics of frozen signals, not traded hedge returns."]}, indent=2))
    return _presentation(result, include_details)


if __name__ == "__main__":
    from score_forecast_data import load_data

    data = load_data()
    result = run_extensions(data)
    print(json.dumps({name: len(frame) for name, frame in result.items() if isinstance(frame, pd.DataFrame)}, indent=2))
