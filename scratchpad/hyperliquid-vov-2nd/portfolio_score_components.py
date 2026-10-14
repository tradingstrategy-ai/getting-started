"""Pinned full-history inputs and eligible-universe score components."""

import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from k_ratio_features import raw_inputs, sha256, window_metrics, k_statistics
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast
from portfolio_score_design import ROOT, START, END, VERSION, smoke_registry, canonical

GENERATION = ROOT / "_artifacts-restored-2026-10-07"
BASE_NAMES = {"L": "v11", "B": "blend_46d", "F": "focal_four"}


def read_inputs():
    """Verify existing generations; retain all warmup and source eligibility."""
    data = raw_inputs()
    for name in ("vault_prices", "vault_metadata"):
        assert sha256(data["downloads"][name]["path"]) == data["downloads"][name]["sha256"]
    registry = json.loads((GENERATION / "08/registry.json").read_text())
    assert len(registry) == 139 and len({r["recipe_sha256"] for r in registry}) == 139
    feature_manifest = json.loads((GENERATION / "09/data-manifest.json").read_text())
    assert feature_manifest["module_sha256"] == sha256(ROOT / "k_ratio_features.py")
    assert feature_manifest["archive_sha256"] == data["downloads"]["vault_prices"]["sha256"]
    assert feature_manifest["operational_audit_sha256"] == sha256(GENERATION / "08/eligibility.parquet")
    origins = pd.date_range(START, END - pd.Timedelta(days=1), freq="4D")
    assert len(origins) == 70 and int((origins + pd.Timedelta(days=30) <= END).sum()) == 62
    e = data["eligibility"]
    e = e[e.origin_at.isin(origins)].copy()
    assert set(e.origin_at) == set(origins) and not e.duplicated(["origin_at", "pair_id"]).any()
    assert (e.feature_cutoff == e.origin_at).all()
    e["feature_cutoff"] = e.origin_at - pd.Timedelta(days=1)
    e["chain_id"] = 9999
    data.update(eligibility=e, origins=origins, registry=registry, prices=pd.read_parquet(GENERATION / "08/prices.parquet"))
    data["frozen_scores"] = pd.read_parquet(GENERATION / "08/scores.parquet", filters=[("method_id", "in", list(BASE_NAMES.values())), ("origin_at", ">=", START)])
    data["features"] = pd.read_parquet(GENERATION / "09/features.parquet", filters=[("origin_at", ">=", START)])
    data["arrays"] = {key: data[key].to_numpy() for key in ("nav", "raw_nav", "source")}
    data["arrays"]["actual"] = np.isfinite(data["arrays"]["raw_nav"])
    data["arrays"]["last_observed"] = data["observed"].ffill().to_numpy(dtype="datetime64[ns]")
    data["id_index"] = {int(pid): i for i, pid in enumerate(data["nav"].columns)}
    data["date_index"] = {t: i for i, t in enumerate(data["nav"].index)}
    data["first_index"] = data["nav"].index.get_indexer(data["first"])
    data["last_index"] = data["nav"].index.get_indexer(data["last"])
    assert data["nav"].index.min() < pd.Timestamp("2025-01-01")
    current = {}
    for name in ("getting-started", "trade-executor", "trading-strategy", "web3-ethereum-defi"):
        repo = Path.home() / "code" / name
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
        current[name] = p.stdout.strip() if p.returncode == 0 else "unavailable"
    sources = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(ROOT.glob("portfolio_score_*.py"))}
    sources.update({str(p.relative_to(ROOT)): sha256(p) for p in sorted(ROOT.glob("portfolio_snapshot_*.py"))})
    sources["k_ratio_features.py"] = sha256(ROOT / "k_ratio_features.py")
    source_files = ["08/registry.json", "08/scores.parquet", "08/eligibility.parquet", "08/prices.parquet", "09/features.parquet", "09/data-manifest.json"]
    source_hashes = {name: sha256(GENERATION / name) for name in source_files}
    identity = dict(version=VERSION, code=sources, inputs=data["downloads"], source_hashes=source_hashes, policies=smoke_registry(), origins=list(map(str, origins)))
    key = hashlib.sha256(canonical(identity).encode()).hexdigest()
    folder = GENERATION / "10-expanded/smoke" / key
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=key, manifest=dict(identity=identity, current_framework_commits=current, feature_generation=feature_manifest, warmup="All recorded observations retained; 2025 minimum, older history for Kmax/730d", origin_count=70, mature_30d=62, pending_30d=8, observed_data_start=str(data["daily"].date.min()), nav_calendar_start=str(data["nav"].index.min()), full_registry_count=139, limitations=["Current guard/inventory eligibility is not proven historically complete", "Unknown permission/capacity clocks retain recorded state; NAV filling does not fill those fields", "Repaired historical NAV is retrospective; publication time unverified", "No independent holdout; overlapping snapshots do not produce strategy CAGR"]))
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data


def percentile(values):
    """Midrank percentile on finite eligible values, preserving missing masks."""
    x = np.asarray(values, float)
    out = np.full(len(x), np.nan)
    good = np.isfinite(x)
    if good.any():
        out[good] = (pd.Series(x[good]).rank(method="average").to_numpy() - 0.5) / good.sum()
    return out


def components_needed(policies):
    result = set()

    def walk(x):
        if isinstance(x, str):
            result.add(x)
        elif isinstance(x, dict):
            for a in x["args"]:
                walk(a)

    for p in policies:
        walk(p["ranking"])
        walk(p["weighting"])
    return sorted(result - {"source90"})


def build_components(data, policies):
    """Build scores for every eligible vault before any basket is chosen."""
    from tqdm_loggable.auto import tqdm

    needed = components_needed(policies)
    rows = []
    risk_rows = []
    warm = []
    inventory = []
    fg = {(t, m): g.set_index("pair_id") for (t, m), g in data["frozen_scores"].groupby(["origin_at", "method_id"], observed=True)}
    features = data["features"].set_index(["origin_at", "pair_id"])
    for origin in tqdm(data["origins"], desc="Eligible-universe components; estimated under 2 minutes", mininterval=15):
        candidates = data["eligibility"][data["eligibility"].origin_at.eq(origin) & data["eligibility"].eligible_as_of_origin]
        ids = candidates.pair_id.to_numpy(int)
        jj = np.array([data["id_index"][int(i)] for i in ids])
        a = data["date_index"][origin - pd.Timedelta(days=1)]
        feat = features.reindex(pd.MultiIndex.from_product([[origin], ids], names=["origin_at", "pair_id"]))
        risk = {}
        for L in (90, 180):
            vals = [empirical_window(data["arrays"]["nav"][max(0, a - L) : a + 1, j], data["arrays"]["actual"][max(0, a - L) : a + 1, j], L) for j in jj]
            emp = np.array([v["empirical"] for v in vals])
            full = np.array([v["full"] for v in vals])
            priors = []
            pred = []
            counts = []
            for i, (pid, j, v) in enumerate(zip(ids, jj, vals)):
                prior, count, pool, disp = peer_prior(emp, full, i)
                regular = forecast(emp[i], prior, v["m"], "regularised", L / 3)
                raw = forecast(emp[i], prior, v["m"], "raw", L / 3)
                p = data["arrays"]["source"][max(0, a - L) : a + 1, j]
                source = np.nan
                if L == 90 and len(p) == 91 and np.isfinite(p).all() and (p > 0).all():
                    source = max(float(np.var(p[1:] / p[:-1] - 1, ddof=1)), 1e-8)
                row = dict(origin_at=origin, pair_id=int(pid), L=L, **v, prior=prior, prior_count=count, prior_pool=pool, prior_dispersion=disp, regularised=regular, raw=raw, source=source)
                risk_rows.append(row)
                priors.append(prior)
                pred.append(regular)
                counts.append(count)
            risk[L] = dict(prior=np.array(priors), pred=np.array(pred), counts=np.array(counts), vals=vals)
        for name in needed:
            raw = np.full(len(ids), np.nan)
            score = raw.copy()
            scale = np.full(len(ids), np.nan)
            scale_n = np.zeros(len(ids), int)
            age = feat["age_days"].to_numpy(float)
            count = np.zeros(len(ids), int)
            prior_status = np.full(len(ids), "empirical", object)
            reason = np.full(len(ids), "undefined_or_insufficient_elapsed_history", object)
            if name in BASE_NAMES:
                g = fg[(origin, BASE_NAMES[name])].reindex(ids)
                raw = g.score.to_numpy(float)
                score = raw.copy()
                assert np.all((score[np.isfinite(score)] >= 0) & (score[np.isfinite(score)] <= 1 + 1e-12))
                reason = g.score_missing_reason.fillna("").to_numpy(str)
                count = np.full(len(ids), np.nan)
                age = np.full(len(ids), np.nan)
                scale_n = np.full(len(ids), np.nan)
            elif name.startswith(("I", "V")):
                L = int(name[1:])
                r = risk[L]
                raw = r["pred"]
                scale = r["prior"]
                scale_n = r["counts"]
                good = np.isfinite(raw) & np.isfinite(scale) & (scale > 0) & (raw >= 0)
                score[good] = scale[good] / (raw[good] + scale[good]) if name[0] == "I" else np.sqrt(scale[good]) / (np.sqrt(raw[good]) + np.sqrt(scale[good]))
                count = np.array([v["m"] for v in r["vals"]])
                age = np.array([v["n"] for v in r["vals"]])
                prior_status = np.array(["prior_only" if not np.isfinite(v["empirical"]) else "regularised_empirical" for v in r["vals"]])
            elif name.startswith("K"):
                window = "max" if name.startswith("Kmax") else name[1:].split("_")[0].replace("+", "") + "d"
                raw = feat[f"{window} K-ratio"].to_numpy(float)
                L = None if window == "max" else int(window[:-1])
                for i, j in enumerate(jj):
                    first = data["first_index"][j] if L is None else max(0, a - L)
                    count[i] = int(data["arrays"]["actual"][first + 1 : a + 1, j].sum()) if first >= 0 else 0
                age = feat["max days"].to_numpy(float) if L is None else np.full(len(ids), L, float)
                valid = np.isfinite(raw)
                positive_abs = np.abs(raw[valid & (raw != 0)])
                k0 = float(np.median(positive_abs)) if len(positive_abs) else np.nan
                scale[:] = k0
                scale_n[:] = len(positive_abs)
                if len(positive_abs):
                    if name.endswith("+"):
                        positive = np.maximum(raw[valid], 0)
                        score[valid] = positive / (positive + k0)
                    else:
                        score[valid] = 0.5 + np.arctan(raw[valid] / k0) / np.pi
                elif valid.any():
                    score[valid] = 0.0 if name.endswith("+") else 0.5
                if name.endswith("_conf"):
                    score[valid] = 0.5 + count[valid] / (count[valid] + 30) * (score[valid] - 0.5)
                reason = feat[f"{window} reason"].fillna("undefined").to_numpy(str) if f"{window} reason" in feat else reason
            else:
                prefix = next(x for x in ("Sh", "So", "Ca", "C", "D") if name.startswith(x))
                L = int(name[len(prefix) :])
                metric = {"Sh": "Sharpe", "So": "Sortino", "Ca": "Calmar", "C": "CAGR", "D": "Max drawdown"}[prefix]
                raw = feat[f"{L}d {metric}"].to_numpy(float)
                score = percentile(raw)
                age = np.full(len(ids), L, float)
                count = np.array([data["arrays"]["actual"][max(0, a - L) + 1 : a + 1, j].sum() for j in jj])
                scale_n[:] = np.isfinite(raw).sum()
            finite = np.isfinite(score)
            assert np.all((score[finite] >= 0) & (score[finite] <= 1 + 1e-12))
            for i, pid in enumerate(ids):
                rows.append(dict(origin_at=origin, pair_id=int(pid), component=name, value=float(score[i]), raw_value=float(raw[i]), available=bool(finite[i]), prior_status=prior_status[i], actual_count=float(count[i]), history_span=float(age[i]), scale=float(scale[i]), scale_support=float(scale_n[i]), reason="defined" if finite[i] else reason[i]))
            if origin == START:
                warm.append(dict(component=name, eligible=len(ids), finite=int(finite.sum()), missing=int((~finite).sum()), retained_history_start=str(data["daily"].date.min()), feature_cutoff=str(origin - pd.Timedelta(days=1))))
    frame = pd.DataFrame(rows)
    rf = pd.DataFrame(risk_rows)
    assert not frame.duplicated(["origin_at", "pair_id", "component"]).any()
    for name in needed:
        sub = frame[frame.component.eq(name)]
        inventory.append(dict(component=name, status="loaded_verified" if name in BASE_NAMES or name[0] not in "IV" else "computed_causally", observations=len(sub), finite=int(sub.available.sum()), origins=sub.origin_at.nunique()))
    return dict(components=frame, risk=rf, warmup=pd.DataFrame(warm), feature_inventory=pd.DataFrame(inventory))
