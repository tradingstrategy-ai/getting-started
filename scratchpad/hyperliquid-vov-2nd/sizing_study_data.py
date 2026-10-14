"""Read-only input verification, frozen baskets and causal risk tensors."""

import hashlib
import json
import subprocess
import numpy as np
import pandas as pd
from k_ratio_features import raw_inputs, sha256
from portfolio_snapshot_risk import empirical_window, peer_prior, forecast
from sizing_study_design import ROOT, GENERATION, REFERENCE, START, END, VERSION, SELECTORS, canonical, followups


def read_inputs():
    data = raw_inputs()
    for name in ("vault_prices", "vault_metadata"):
        assert sha256(data["downloads"][name]["path"]) == data["downloads"][name]["sha256"]
    registry = json.loads((GENERATION / "08/registry.json").read_text())
    fm = json.loads((GENERATION / "09/data-manifest.json").read_text())
    assert len(registry) == 139 and len({r["recipe_sha256"] for r in registry}) == 139
    assert fm["module_sha256"] == sha256(ROOT / "k_ratio_features.py")
    assert fm["archive_sha256"] == data["downloads"]["vault_prices"]["sha256"]
    assert fm["operational_audit_sha256"] == sha256(GENERATION / "08/eligibility.parquet")
    reference = json.loads((REFERENCE / "manifest.json").read_text())
    for file, digest in reference["identity"]["source_hashes"].items():
        assert sha256(GENERATION / file) == digest
    for file, digest in reference["identity"]["code"].items():
        assert sha256(ROOT / file) == digest
    assert data["downloads"] == reference["identity"]["inputs"]
    origins = pd.date_range(START, END - pd.Timedelta(days=1), freq="4D")
    e = data["eligibility"]
    e = e[e.origin_at.isin(origins)].copy()
    e["chain_id"] = 9999
    e["feature_cutoff"] = e.origin_at - pd.Timedelta(days=1)
    data.update(eligibility=e, origins=origins, registry=registry, prices=pd.read_parquet(GENERATION / "08/prices.parquet"))
    data["frozen_scores"] = pd.read_parquet(GENERATION / "08/scores.parquet", filters=[("method_id", "in", list(SELECTORS.values())), ("origin_at", ">=", START)])
    data["components"] = pd.read_parquet(REFERENCE / "components.parquet")
    data["arrays"] = {key: data[key].to_numpy() for key in ("nav", "raw_nav", "source")}
    data["arrays"]["actual"] = np.isfinite(data["arrays"]["raw_nav"])
    data["arrays"]["last_observed"] = data["observed"].ffill().to_numpy(dtype="datetime64[ns]")
    data["id_index"] = {int(pid): i for i, pid in enumerate(data["nav"].columns)}
    data["date_index"] = {t: i for i, t in enumerate(data["nav"].index)}
    data["first_index"] = data["nav"].index.get_indexer(data["first"])
    data["last_index"] = data["nav"].index.get_indexer(data["last"])
    data["framework_commits"] = {}
    for name in ("getting-started", "trade-executor", "trading-strategy", "web3-ethereum-defi"):
        p = subprocess.run(["git", "-C", str(ROOT.parents[2] / name), "rev-parse", "HEAD"], capture_output=True, text=True)
        data["framework_commits"][name] = p.stdout.strip() if p.returncode == 0 else "unavailable"
    data["reference_manifest"] = reference
    return data


def stage_folder(data, policies, stage):
    files = list(ROOT.glob("sizing_study_*.py")) + [ROOT / "create_sizing_study_notebook.py"]
    code = {p.name: sha256(p) for p in files}
    code.update(data["reference_manifest"]["identity"]["code"])
    identity = dict(version=VERSION, code=code, downloads=data["downloads"], reference_manifest_sha256=sha256(REFERENCE / "manifest.json"), reference_files={name: sha256(REFERENCE / name) for name in ("allocations.parquet", "outcomes.parquet", "components.parquet")}, original_reference_files={name: sha256(GENERATION / "10" / name) for name in ("policies.parquet", "allocations.parquet", "outcomes.parquet")}, policies=policies, stage=stage, horizons=[30] if stage == "smoke" else [7, 30, 90], calendar=list(map(str, data["origins"])))
    key = hashlib.sha256(canonical(identity).encode()).hexdigest()
    folder = GENERATION / "11" / stage / key
    folder.mkdir(parents=True, exist_ok=True)
    manifest = dict(identity=identity, fingerprint=key, framework_commits=data["framework_commits"], nav_start=str(data["daily"].date.min()), warmup="All available 2025 and earlier observations retained", assumptions="Frozen NB10 selection and source-report-only projection; NAV-only causal fill", limitations=["Current inventory/guard restrictions not historically complete", "Retrospective archive publication clocks unverified", "Unknown permission clocks retain archived state", "Snapshot fill at T-1 is not an executable T decision fill", "Retrospective searched history; no fresh holdout"])
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    (folder / "followups.json").write_text(json.dumps(followups(), indent=2))
    data.update(artifact=folder, fingerprint=key, stage=stage)
    return folder


def freeze_baskets(data):
    rows = []
    scores = {(t, m): g.set_index("pair_id") for (t, m), g in data["frozen_scores"].groupby(["origin_at", "method_id"], observed=True)}
    for t in data["origins"]:
        e = data["eligibility"][data["eligibility"].origin_at.eq(t) & data["eligibility"].eligible_as_of_origin].copy()
        for selector, method in SELECTORS.items():
            f = e.copy()
            f["score"] = f.pair_id.map(scores[(t, method)].score)
            f["tier"] = np.where(np.isfinite(f.score), 0, 1)
            f["address"] = f.vault_address.str.lower()
            f = f.sort_values(["tier", "score", "chain_id", "address"], ascending=[True, False, True, True], na_position="last", kind="stable").head(6)
            f["selector"] = selector
            f["rank"] = np.arange(1, len(f) + 1)
            rows.append(f)
    return pd.concat(rows, ignore_index=True)


def sparse_window(raw, L=90):
    """Matched complete intervals; no synthetic marks at either boundary."""
    raw = np.asarray(raw, float)[-(L + 1) :]
    ii = np.flatnonzero(np.isfinite(raw) & (raw > 0))
    m = max(0, len(ii) - 1)
    full = bool(len(ii) >= 2 and ii[0] == 0 and ii[-1] == L)
    result = dict(calendar=np.nan, gap=np.nan, m=m, n=int(ii[-1] - ii[0]) if len(ii) else 0, full=full, longest_gap=int(np.diff(ii).max()) if m else np.nan, last_mark_age=int(len(raw) - 1 - ii[-1]) if len(ii) else np.nan)
    if m < 2:
        return result
    days = np.diff(ii).astype(float)
    x = np.diff(np.log(raw[ii]))
    drift = x.sum() / days.sum()
    calendar = pd.Series(raw[ii], index=ii).reindex(range(ii[0], ii[-1] + 1)).ffill().to_numpy()
    result.update(calendar=float(np.var(np.diff(np.log(calendar)), ddof=1)), gap=float(np.sum((x - drift * days) ** 2 / days) / (m - 1)))
    return result


def build_risk(data):
    from tqdm_loggable.auto import tqdm

    rows = []
    support = []
    for t in tqdm(data["origins"], desc="NB11 causal risk windows; estimated under two minutes", mininterval=15):
        a = data["date_index"][t - pd.Timedelta(days=1)]
        e = data["eligibility"][data["eligibility"].origin_at.eq(t) & data["eligibility"].eligible_as_of_origin]
        ids = e.pair_id.to_numpy(int)
        jj = [data["id_index"][int(pid)] for pid in ids]
        for L in (45, 90, 180):
            vals = [empirical_window(data["arrays"]["nav"][a - L : a + 1, j], data["arrays"]["actual"][a - L : a + 1, j], L) for j in jj]
            emp = np.array([v["empirical"] for v in vals])
            full = np.array([v["full"] for v in vals])
            for i, (pid, j, v) in enumerate(zip(ids, jj, vals)):
                prior, count, pool, disp = peer_prior(emp, full, i)
                marks = np.flatnonzero(data["arrays"]["actual"][a - L : a + 1, j])
                longest = int(np.diff(marks).max()) if len(marks) > 1 else np.nan
                anchor_age = float((t.to_datetime64() - data["arrays"]["last_observed"][a, j]) / np.timedelta64(1, "D"))
                source = np.nan
                if L == 90:
                    p = data["arrays"]["source"][a - L : a + 1, j]
                    if len(p) == 91 and np.isfinite(p).all() and (p > 0).all():
                        source = max(float(np.var(p[1:] / p[:-1] - 1, ddof=1)), 1e-8)
                for kappa in sorted({30.0, L / 3}):
                    pred = forecast(emp[i], prior, v["m"], "regularised", kappa)
                    rows.append(dict(origin_at=t, pair_id=int(pid), estimator="regular", units="simple", L=L, kappa=kappa, **v, prior=prior, prior_count=count, prior_pool=pool, prior_dispersion=disp, predicted=pred, weak_prior=count < 5, prior_only=not np.isfinite(emp[i]), floor_active=False, shrinkage=v["m"] / (v["m"] + kappa) if np.isfinite(emp[i]) else 0, source=source, anchor_age=anchor_age, longest_gap=longest, history_age=a - data["first_index"][j], actual_fraction=v["m"] / L))
                if L == 90:
                    for name, pred in [("raw", forecast(emp[i], prior, v["m"], "raw", 30)), ("source", source)]:
                        rows.append(dict(rows[-1], estimator=name, kappa=30, predicted=pred, floor_active=bool(np.isfinite(pred) and pred == 1e-8), shrinkage=1.0))
            support.append(dict(origin_at=t, convention="original", L=L, eligible=len(ids), full_count=int(full.sum()), positive_full_count=int((full & np.isfinite(emp) & (emp > 0)).sum())))
        sparse = [sparse_window(data["arrays"]["raw_nav"][a - 90 : a + 1, j]) for j in jj]
        emp = np.array([v["calendar"] for v in sparse])
        full = np.array([v["full"] for v in sparse])
        support.append(dict(origin_at=t, convention="strict_actual_endpoints", L=90, eligible=len(ids), full_count=int(full.sum()), positive_full_count=int((full & np.isfinite(emp) & (emp > 0)).sum())))
        for i, (pid, j, v) in enumerate(zip(ids, jj, sparse)):
            prior, count, pool, disp = peer_prior(emp, full, i)
            original = empirical_window(data["arrays"]["nav"][a - 90 : a + 1, j], data["arrays"]["actual"][a - 90 : a + 1, j], 90)
            for name in ("calendar", "gap"):
                value = v[name]
                pred = forecast(value, prior, v["m"], "regularised", 30)
                rows.append(dict(origin_at=t, pair_id=int(pid), estimator=name + "_log", units="log", L=90, kappa=30, empirical=value, n=v["n"], m=v["m"], full=v["full"], status="unavailable" if not np.isfinite(value) else "observed_flat" if value == 0 else "matched_intervals", prior=prior, prior_count=count, prior_pool=pool, prior_dispersion=disp, predicted=pred, weak_prior=count < 5, prior_only=not np.isfinite(value), floor_active=False, shrinkage=v["m"] / (v["m"] + 30) if np.isfinite(value) else 0, source=np.nan, anchor_age=float((t.to_datetime64() - data["arrays"]["last_observed"][a, j]) / np.timedelta64(1, "D")), last_mark_calendar_age=v["last_mark_age"], longest_gap=v["longest_gap"], history_age=a - data["first_index"][j], actual_fraction=original["m"] / 90, original_updates=original["m"]))
    return pd.DataFrame(rows), pd.DataFrame(support)
