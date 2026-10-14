"""Pinned causal input tensors and forward paths for experiment 10."""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from k_ratio_features import raw_inputs, sha256

ROOT = Path(__file__).resolve().parent
GENERATION = ROOT / "_artifacts-restored-2026-10-07"
ARTIFACT = GENERATION / "10"
METHODS = ("v11", "blend_46d", "focal_four")
START = pd.Timestamp("2026-01-01")
LONG_START = pd.Timestamp("2023-03-01")
END = pd.Timestamp("2026-10-05")
HORIZONS = (7, 30, 90)
PERIODS = {"2026": (START, END), "Long": (LONG_START, END), "Pre-2026": (LONG_START, START)}
CONFIG = dict(version="10-v1", cadence_days=4, horizons=HORIZONS, windows=(30, 60, 90, 180), local_windows=(75, 105), powers=(0, 0.5, 1, 2), positions=(4, 6, 8, 10), daily_sigma_floor=0.0001, kappa_ratio=1 / 3, kappa_sensitivities=(10, 30, 90), prior_gates=(1, 5, 10), annualisation=365, ddof=1, bootstrap_draws=1999, bootstrap_seed=1010, assignment_draws=999, assignment_seed=2010, tie_seed=3010, block_gate=10, joint_valid_fraction=0.95, account_usd=150000, budget=0.98, concentration=0.33, pool_cap=0.33, state_age_days=2, covariance_min_returns=30, covariance_min_updates=3, covariance_sensitivity_returns=60, matrix_tolerance=1e-10, solver_tolerance=1e-9, solver_iterations=10000, risk_contribution_tolerance=1e-5, tail_fraction=0.05, erc_objective_tolerance=1e-12, positive_solver_bound=1e-12, minimum_calendar_returns=2, minimum_actual_dates=2, tie_comparison_relative_tolerance=1e-10, numerical_jitter_relative=1e-10)


def fingerprint():
    files = sorted(ROOT.glob("portfolio_snapshot_*.py")) + [ROOT / "create_portfolio_snapshot_notebook.py"]
    return {p.name: sha256(p) for p in files if p.exists()}


def load_inputs(include_phases=True):
    """Read frozen scores; calculate only missing phase inputs, never new recipes."""
    ARTIFACT.mkdir(exist_ok=True)
    data = raw_inputs()
    for key in ("vault_prices", "vault_metadata"):
        assert sha256(data["downloads"][key]["path"]) == data["downloads"][key]["sha256"]
    cache = GENERATION / "08"
    registry = [r for r in json.loads((cache / "registry.json").read_text()) if r["method_id"] in METHODS]
    scores = pd.read_parquet(cache / "scores.parquet", filters=[("method_id", "in", list(METHODS))])
    eligibility = data["eligibility"].copy()
    # NB08 feature_cutoff means decision timestamp, not the NAV candle label.
    assert (eligibility.feature_cutoff == eligibility.origin_at).all()
    eligibility["decision_at"] = eligibility.feature_cutoff
    eligibility["feature_cutoff"] = eligibility.origin_at - pd.Timedelta(days=1)
    original_origins = pd.DatetimeIndex(eligibility.origin_at.unique()).sort_values()
    phase_manifest = ARTIFACT / "phase-input-manifest.json"
    identity = {"scores": sha256(cache / "scores.parquet"), "eligibility": sha256(cache / "eligibility.parquet"), "registry": registry}
    identity_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    if include_phases:
        if phase_manifest.exists() and json.loads(phase_manifest.read_text()).get("fingerprint") == identity_hash:
            extra_e = pd.read_parquet(ARTIFACT / "phase-eligibility.parquet")
            extra_s = pd.read_parquet(ARTIFACT / "phase-scores.parquet")
        else:
            from precompute_repaired_singletons import create_evaluator
            from score_forecast_data import _eligibility, method_values, input_configurations
            from tqdm_loggable.auto import tqdm

            evaluator, _, _, _ = create_evaluator()
            input_configurations(evaluator.panel)
            extra = pd.date_range(LONG_START, END - pd.Timedelta(days=1)).difference(original_origins)
            pieces = []
            for chunk in tqdm(np.array_split(extra, 12), desc="Phase eligibility; approximately 3–6 minutes"):
                pieces.append(_eligibility(evaluator, pd.DatetimeIndex(chunk), pd.read_parquet(cache / "prices.parquet")))
            extra_e = pd.concat(pieces, ignore_index=True)
            extra_e["decision_at"] = extra_e.feature_cutoff
            extra_e["feature_cutoff"] = extra_e.origin_at - pd.Timedelta(days=1)
            base = extra_e[["origin_at", "pair_id", "vault_address", "eligible_as_of_origin"]]
            ii = [evaluator.panel.date_index[t] for t in extra]
            parts = []
            for recipe in registry:
                values, imputed = method_values(evaluator.panel, recipe)
                part = base.copy()
                part["method_id"] = recipe["method_id"]
                part["score"] = values[ii].reshape(-1)
                part["score_imputed"] = imputed[ii].reshape(-1)
                part["score_missing_reason"] = np.where(part.score.isna(), "component_unavailable_or_undefined", "")
                parts.append(part)
            extra_s = pd.concat(parts, ignore_index=True)
            extra_e.to_parquet(ARTIFACT / "phase-eligibility.parquet", index=False)
            extra_s.to_parquet(ARTIFACT / "phase-scores.parquet", index=False)
            phase_manifest.write_text(json.dumps({"fingerprint": identity_hash}, indent=2))
        eligibility = pd.concat([eligibility, extra_e], ignore_index=True)
        scores = pd.concat([scores, extra_s], ignore_index=True)
    assert not eligibility.duplicated(["origin_at", "pair_id"]).any()
    assert not scores.duplicated(["origin_at", "pair_id", "method_id"]).any()
    eligibility["phase"] = ((eligibility.origin_at - START).dt.days % 4).astype(int)
    prices = pd.read_parquet(cache / "prices.parquet")
    # No ffill of permission fields: source state is taken coherently from eligibility.
    # TVL is a separate completed source candle series, with a declared two-day carry.
    data.update(registry=registry, scores=scores, eligibility=eligibility, candidates=eligibility[eligibility.eligible_as_of_origin].merge(scores[["origin_at", "pair_id", "method_id", "score", "score_imputed", "score_missing_reason"]], on=["origin_at", "pair_id"], validate="one_to_many"), prices=prices, origins=pd.DataFrame({"origin_at": sorted(eligibility.origin_at.unique())}))
    data["origins"]["feature_cutoff"] = data["origins"].origin_at - pd.Timedelta(days=1)
    data["origins"]["phase"] = ((data["origins"].origin_at - START).dt.days % 4).astype(int)
    data["arrays"] = {key: data[key].to_numpy() for key in ("nav", "raw_nav", "source")}
    data["arrays"]["actual"] = data["raw_nav"].notna().to_numpy()
    data["arrays"]["last_observed"] = data["observed"].ffill().to_numpy(dtype="datetime64[ns]")
    data["id_index"] = {int(pid): i for i, pid in enumerate(data["nav"].columns)}
    data["date_index"] = {date: i for i, date in enumerate(data["nav"].index)}
    data["last_index"] = data["nav"].index.get_indexer(data["last"])
    data["first_index"] = data["nav"].index.get_indexer(data["first"])
    data["provenance"] = json.loads((cache / "provenance.json").read_text())
    manifest = dict(config=CONFIG, inputs=data["downloads"], source_provenance=data["provenance"], recipes=registry, code=fingerprint(), cutoff_correction="NB08 feature_cutoff is T; actual trailing tensor ends at A=T-1", original_origins=len(original_origins), phases=include_phases)
    (ARTIFACT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    return data


def future_panel(data, origin, horizon, ids):
    """Keep ex-ante identities and censor beyond each final actual positive mark."""
    ids = np.asarray(ids, dtype=int)
    jj = np.array([data["id_index"][int(i)] for i in ids], dtype=int)
    a = data["date_index"][pd.Timestamp(origin) - pd.Timedelta(days=1)]
    end = a + horizon
    supported = (data["last_index"][jj] >= end) & np.isfinite(data["arrays"]["nav"][a, jj])
    if end >= len(data["nav"]):
        supported[:] = False
        return {"ids": ids, "supported": supported, "paths": np.full((horizon + 1, len(ids)), np.nan)}
    paths = data["arrays"]["nav"][a : end + 1, jj]
    supported &= np.isfinite(paths).all(axis=0) & (paths > 0).all(axis=0)
    returns = paths[-1] / paths[0] - 1
    dr = paths[1:] / paths[:-1] - 1
    variance = np.var(dr, axis=0, ddof=1)
    sigma = np.sqrt(variance)
    sharpe = np.divide(dr.mean(axis=0) * np.sqrt(365), sigma, out=np.full(len(ids), np.nan), where=sigma > 0)
    actual = data["arrays"]["actual"][a : end + 1, jj]
    first_update = np.full(len(ids), np.nan)
    for j in range(len(ids)):
        positions = np.flatnonzero(actual[:, j])
        if len(positions):
            first_update[j] = paths[positions[0], j] / paths[0, j] - 1
    remaining = returns - first_update
    lastobs = data["arrays"]["last_observed"]
    anchor_age = (data["nav"].index[a].to_datetime64() + np.timedelta64(1, "D") - lastobs[a, jj]) / np.timedelta64(1, "D")
    endpoint_age = (data["nav"].index[end].to_datetime64() + np.timedelta64(1, "D") - lastobs[end, jj]) / np.timedelta64(1, "D")
    for x in (returns, variance, sharpe, first_update, remaining):
        x[~supported] = np.nan
    return dict(ids=ids, supported=supported, paths=paths, returns=returns, variance=variance, sharpe=sharpe, first_update=first_update, remaining=remaining, anchor_age=anchor_age, endpoint_age=endpoint_age, anchor_carried=~actual[0], endpoint_carried=~actual[-1], future_updates=actual[1:].sum(axis=0), label_end=data["nav"].index[end], label_available_at=data["nav"].index[end] + pd.Timedelta(days=1))
