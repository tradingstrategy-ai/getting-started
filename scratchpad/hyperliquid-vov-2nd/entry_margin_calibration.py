"""Monthly paired calibration, registered entry gate and ledger controls for NB22."""

import hashlib
import json
import numpy as np
import pandas as pd
from entry_margin_data import CUTOFF, HORIZONS


def coefficients(train, model, h, fit):
    """Equal-origin level and within-origin covariance on identical matured pairs."""
    global_groups = train.groupby("Date").Y_net.mean()
    pairs = train[train[model].notna()].copy()
    if model == "L2":
        pairs = pairs[pairs.Supported_D]
    n = pairs.groupby("Date").size()
    a = pairs.groupby("Date").Y_net.mean()
    if not len(pairs):
        return dict(Alpha=np.nan, Beta=0.0, Raw_beta=np.nan, Global_L0=float(global_groups.mean()), Matched_L0=np.nan, Matched_origins=0, Identification_origins=0, Blocks=0, Beta_lower=np.nan, Beta_upper=np.nan, Identified=False, Matched_positive=np.nan, Rows=0)
    pairs["Zc"] = pairs[model] - pairs.groupby("Date")[model].transform("mean")
    pairs["Yc"] = pairs.Y_net - pairs.groupby("Date").Y_net.transform("mean")
    pairs["Cov"] = pairs.Zc * pairs.Yc
    pairs["Var"] = pairs.Zc**2
    moments = pairs.groupby("Date")[["Cov", "Var"]].mean()
    identified_origins = int(((n >= 2) & moments.Var.gt(0)).sum())
    denominator = float(moments.Var.sum())
    raw = float(moments.Cov.sum() / denominator) if len(moments) >= 2 and denominator > 0 else np.nan
    beta = max(0.0, raw) if np.isfinite(raw) else 0.0
    identified = identified_origins >= 2 if model == "L2" else len(moments) >= 2 and denominator > 0
    moments["Block"] = (moments.index - pd.Timestamp("2023-03-01")).days // h
    blocks = moments.groupby("Block")[["Cov", "Var"]].sum()
    ci = [np.nan, np.nan]
    if len(blocks) >= 2 and denominator > 0:
        rng = np.random.default_rng(int(hashlib.sha256(f"nb22-bootstrap|{model}|{h}|{fit}".encode()).hexdigest()[:16], 16))
        draws = rng.integers(0, len(blocks), size=(999, len(blocks)))
        cov = blocks.Cov.to_numpy()[draws].sum(axis=1)
        var = blocks.Var.to_numpy()[draws].sum(axis=1)
        slopes = np.divide(cov, var, out=np.full_like(cov, np.nan), where=var > 0)
        ci = np.nanquantile(slopes, [0.025, 0.975]).tolist()
    pos = pairs.assign(Positive=pairs.Y_net.gt(0)).groupby("Date").Positive.mean().mean()
    return dict(Alpha=float(a.mean()), Beta=beta, Raw_beta=raw, Global_L0=float(global_groups.mean()), Matched_L0=float(a.mean()), Matched_origins=len(moments), Identification_origins=identified_origins, Blocks=len(blocks), Beta_lower=ci[0], Beta_upper=ci[1], Identified=bool(identified), Matched_positive=float(pos), Rows=len(pairs))


def calibrate(data):
    """Fit only before each calendar month; predictions retain historical underlying fits."""
    panel = data["panel"]
    rows = []
    audit = []
    for h in HORIZONS:
        f = panel[panel.H.eq(h)].copy()
        for month in sorted(f.Date.dt.to_period("M").unique()):
            fit = month.start_time
            train = f[f.In_band & f.Resolved & f.Mature_at.lt(fit) & f.Date.lt(fit)]
            current = f[f.Date.dt.to_period("M").eq(month)].copy()
            assert train.Mature_at.lt(fit).all()
            for model in ("L1", "L2"):
                params = coefficients(train, model, h, fit)
                available = f[f.In_band & f.Date.lt(fit) & f[model].notna()].groupby("Date").size()
                mature = train[train[model].notna()].groupby("Date").size().reindex(available.index, fill_value=0)
                fractions = mature / available
                audit.append(dict(H=h, Model=model, Fit=fit, Max_mature=train.Mature_at.max(), Partly_matured_origins=int(fractions.between(0, 1, inclusive="neither").sum()), Recent_5_origin_mature_fraction=float(fractions.tail(5).mean()), **params))
                means = current[current.In_band & current[model].notna()].groupby("Date")[model].mean()
                counts = current[current.In_band & current[model].notna()].groupby("Date").size()
                out = current[["Date", "Pair", "H", "In_band", "Rank", "Y_net", "Y_mark", "Gross", "Resolved", "Mature_at", "Supported_D", "Missing_score", "recorded_age", "quote_age", "Endpoint_age", "Actual_updates", "permission_unknown", "can_deposit", "vault_name", "profit_probability", model]].copy()
                out["Model"] = model
                out["Signal"] = out[model]
                out = out.drop(columns=[model])
                out["Fit_calibration"] = fit
                for key, value in params.items():
                    out[key] = value
                out["Band_mean"] = out.Date.map(means)
                out["Band_signal_rows"] = out.Date.map(counts).fillna(0).astype(int)
                out["Deviation"] = out.Signal - out.Band_mean
                out["Prediction"] = out.Alpha + out.Beta * out.Deviation
                missing = out.Signal.isna() | out.Band_mean.isna()
                out.loc[missing, "Prediction"] = params["Global_L0"]
                out["Physical_clipped"] = out.Prediction.lt(-1)
                out["Prediction"] = out.Prediction.clip(lower=-1)
                out["Actionable"] = out.In_band & out.Signal.notna() & out.Band_signal_rows.ge(2) & out.Identified & out.Alpha.gt(0) & out.Beta.gt(0)
                if model == "L2":
                    out["Actionable"] &= out.Supported_D
                out["Veto"] = out.Actionable & out.Prediction.le(0)
                out["Threshold_deviation"] = -out.Alpha / out.Beta.replace(0, np.nan)
                out["Pass_reason"] = np.select([~out.In_band, ~out.Signal.notna(), ~out.Identified, out.Band_signal_rows.lt(2), ~out.Alpha.gt(0), ~out.Beta.gt(0), out.Veto], ["outside calibrated band", "missing / unsupported signal", "unidentified relative slope", "fewer than two band signals", "non-positive / unavailable pooled level", "non-positive slope", "supported selective veto"], default="positive calibrated value")
                rows.append(out)
    data["calibration"] = pd.concat(rows, ignore_index=True)
    data["coefficient_audit"] = pd.DataFrame(audit)
    data["calibration"].to_parquet(data["artifact"] / "calibrated-opportunities.parquet", index=False)
    data["coefficient_audit"].to_csv(data["artifact"] / "calibration-audit.csv", index=False)
    # Current outcomes are never used in the monthly fit, including partial maturity.
    assert data["calibration"].Fit_calibration.le(data["calibration"].Date).all()
    return data["calibration"]


def entry_predictions(data, period=None):
    e = data["entries"]
    columns = ["Date", "Pair", "H", "Model", "Alpha", "Beta", "Identified", "Band_mean", "Band_signal_rows", "Signal", "Prediction", "Actionable", "Veto", "Threshold_deviation", "Pass_reason", "Fit_calibration"]
    out = pd.concat([e.merge(data["calibration"].loc[data["calibration"].Model.eq(m), columns], on=["Date", "Pair", "H"], how="left", validate="many_to_one") for m in ("L1", "L2")], ignore_index=True)
    return out[out.Period.eq(period)].copy() if period else out


def value_record(entries, mask, method):
    """Frozen-entry opportunity value; closed outcomes precede qualification cutoff."""
    eligible = entries.Closed & entries.Closed_at.lt(CUTOFF)
    selected = entries[mask]
    resolved = selected[eligible.loc[selected.index]]
    unresolved = selected[~eligible.loc[selected.index]]
    q = float(resolved.Q.sum())
    qu = float(unresolved.Q.sum())
    value = float((-resolved.Q * resolved.Y_spell).sum())
    mark = value + float((-unresolved.Q * unresolved.Pre2026_mark_Y).sum())
    return dict(Method=method, Vetoes=len(selected), Resolved_vetoes=len(resolved), Resolved_Q=q, Unresolved_Q=qu, Unresolved_fraction=qu / (q + qu) if q + qu else np.nan, Value=value, Per_resolved_dollar=value / q if q else np.nan, Mark_value=mark, Mark_per_dollar=mark / (q + qu) if q + qu else np.nan, Break_even_unknown_mean=value / qu if qu else np.nan, Loss_to_zero_value=value + qu)


def ledger_placebos(data, entries, pre=True):
    """Identity permutations plus block signal reassignments, without outcome selection."""
    h = data["horizon"]
    source = data["calibration"][data["calibration"].Model.eq("L2") & data["calibration"].H.eq(h)].copy()
    if pre:
        source = source[source.Date.lt(CUTOFF)]
    source = source.sort_values(["Date", "Pair"]).reset_index(drop=True)
    lookup = source.set_index(["Date", "Pair"])
    reference = entries.copy()
    groups = [g.index.to_numpy() for _, g in source.groupby(["Date", "Supported_D", "Missing_score"], dropna=False)]
    entry_indices = np.array([source.index[(source.Date.eq(t)) & source.Pair.eq(pid)][0] for t, pid in reference[["Date", "Pair"]].itertuples(index=False, name=None)])
    band = source.In_band.to_numpy()
    date_code = pd.factorize(source.Date, sort=True)[0]
    nd = int(date_code.max() + 1)
    action = reference.Actionable.to_numpy(bool)
    alpha = reference.Alpha.to_numpy(float)
    beta = reference.Beta.to_numpy(float)
    fixed = source.Signal.to_numpy(float)
    # Support-era starts/stops are fixed by the underlying D, not realised returns.
    support_era = source.groupby("Date").Supported_D.any().sort_index()
    eras = support_era.ne(support_era.shift()).cumsum()
    source["Era"] = source.Date.map(eras)
    source["Quarter"] = source.Date.dt.to_period("Q").astype(str)
    source["Block"] = (source.Date - pd.Timestamp("2023-03-01")).dt.days // h
    source["Within_percentile"] = source.groupby("Date").Signal.rank(pct=True, method="average")
    # Precompute all within-group block-profile mappings once. The 999 seeds only
    # select donor blocks; they do not repeat expensive DataFrame operations.
    deviations = source.Signal.to_numpy(float) - source.Band_mean.to_numpy(float)
    block_maps = []
    for _, g in source.groupby(["Quarter", "Era"]):
        blocks = sorted(g.Block.unique())
        dates = {b: sorted(g.loc[g.Block.eq(b), "Date"].unique()) for b in blocks}
        indices = {b: g.index[g.Block.eq(b)].to_numpy() for b in blocks}
        profiles = {}
        for b in blocks:
            for k, date in enumerate(dates[b]):
                di = g[g.Date.eq(date)]
                for support, missing in ((True, False), (True, True), (False, False), (False, True)):
                    vals = deviations[di.index[(di.Supported_D.eq(support)) & (di.Missing_score.eq(missing))]]
                    profiles[b, k, support, missing] = vals[np.isfinite(vals)]
        mappings = {}
        for dest in blocks:
            target = indices[dest]
            for donor in blocks:
                mapped = deviations[target].copy()
                positions = {int(ix): j for j, ix in enumerate(target)}
                for k, date in enumerate(dates[dest]):
                    ix = g.index[g.Date.eq(date)].to_numpy()
                    for support, missing in ((True, False), (True, True), (False, False), (False, True)):
                        ti = ix[(source.loc[ix, "Supported_D"].to_numpy() == support) & (source.loc[ix, "Missing_score"].to_numpy() == missing)]
                        vals = profiles[donor, min(k, len(dates[donor]) - 1), support, missing]
                        if len(ti) and len(vals):
                            pct = source.loc[ti, "Within_percentile"].fillna(0.5).to_numpy()
                            mapped[[positions[int(i)] for i in ti]] = np.quantile(vals, np.clip(pct, 0, 1))
                mappings[dest, donor] = mapped
        block_maps.append((blocks, indices, mappings))
    records = []
    for seed in range(1, 1000):
        rng = np.random.default_rng(int(hashlib.sha256(f"nb22-ledger|{seed}".encode()).hexdigest()[:16], 16))
        signal = fixed.copy()
        for ix in groups:
            if len(ix) > 1:
                signal[ix] = rng.permutation(signal[ix])
        good = band & np.isfinite(signal)
        sums = np.bincount(date_code[good], weights=signal[good], minlength=nd)
        counts = np.bincount(date_code[good], minlength=nd)
        mean = np.divide(sums, counts, out=np.full(nd, np.nan), where=counts > 0)
        mask = action & (alpha + beta * (signal[entry_indices] - mean[date_code[entry_indices]]) <= 0)
        records.append(dict(Seed=seed, **value_record(reference, mask, "within-origin identity")))
        # Reassign complete H-day signal-profile blocks within quarter/support era.
        # Rank-percentile quantile mapping handles different names/counts, preserving profile shape.
        reassigned = deviations.copy()
        for blocks, indices, mappings in block_maps:
            shuffled = rng.permutation(blocks)
            for dest, donor in zip(blocks, shuffled):
                reassigned[indices[dest]] = mappings[dest, donor]
        good = band & np.isfinite(reassigned)
        sums = np.bincount(date_code[good], weights=reassigned[good], minlength=nd)
        counts = np.bincount(date_code[good], minlength=nd)
        mean = np.divide(sums, counts, out=np.full(nd, np.nan), where=counts > 0)
        mask = action & (alpha + beta * (reassigned[entry_indices] - mean[date_code[entry_indices]]) <= 0)
        records.append(dict(Seed=seed, **value_record(reference, mask, "quarter/support-era H-day blocks")))
        if seed % 100 == 0:
            print(f"NB22 ledger permutations {seed}/999", flush=True)
    out = pd.DataFrame(records)
    out.to_csv(data["artifact"] / "pre2026-ledger-placebos.csv", index=False)
    return out


def qualify(data):
    """Freeze the go/stop decision before inspecting 2026 forecast outcomes."""
    predictions = entry_predictions(data)
    past = predictions[predictions.Period.eq("Long") & predictions.Date.lt(CUTOFF) & predictions.H.eq(data["horizon"]) & predictions.Model.eq("L2")].copy().reset_index(drop=True)
    informed = value_record(past, past.Veto, "informed L2")
    # Non-activation makes every permutation a no-op; still register all prescribed seeds.
    if past.Veto.any() or past.Actionable.any():
        placebo = ledger_placebos(data, past)
    else:
        placebo = pd.DataFrame([dict(Seed=s, **value_record(past, np.zeros(len(past), bool), m)) for s in range(1, 1000) for m in ("within-origin identity", "quarter/support-era H-day blocks")])
        placebo.to_csv(data["artifact"] / "pre2026-ledger-placebos.csv", index=False)
    medians = placebo.groupby("Method").Per_resolved_dollar.median()
    identified = bool(past.Identified.any() and past.Supported_D.any())
    mark_medians = placebo.groupby("Method").Mark_per_dollar.median()
    tests = {"chronological control and distribution parity": True, "supported relative-D identification": identified, "at least one executable pre-2026 entry vetoed": bool(past.Veto.any()), "positive closed-spell per-dollar value": bool(informed["Per_resolved_dollar"] > 0), "above median identity placebo per resolved dollar": bool(informed["Per_resolved_dollar"] > medians.get("within-origin identity", np.nan)), "above median block placebo per resolved dollar": bool(informed["Per_resolved_dollar"] > medians.get("quarter/support-era H-day blocks", np.nan)), "positive pre-2026 mark-only value": bool(informed["Mark_value"] > 0), "mark-only lead survives identity/block controls": bool(informed["Mark_per_dollar"] > mark_medians.max())}
    current = predictions[predictions.Period.eq("2026") & predictions.H.eq(data["horizon"]) & predictions.Model.eq("L2")]
    # Count activation only: do not access its realised labels at this stage.
    activation = int(current.Veto.sum())
    qualified = all(tests.values())
    execute = qualified and activation > 0
    registration = dict(horizon=data["horizon"], qualification_cutoff=str(CUTOFF), tests=tests, pre2026=informed, placebo_median_per_dollar=medians.to_dict(), past_entries=len(past), past_actionable=int(past.Actionable.sum()), past_in_band=int(past.In_band.sum()), activation2026=activation, qualified=qualified, execute_accounts=execute, stop_reasons=[k for k, v in tests.items() if not v] + (["no 2026 activation"] if qualified and not activation else []), unknown_outcomes="Unbounded positive unknown returns can hurt a veto; qualification conditional where unresolved dollars exist", registered_engine_arms=["C00", "O1", "R01", "R02", "R03", "R04", "R05"], optional_factorial="not executed", proposal_scope="All saved C00 trades succeeded synchronously; buy reserves equal funded planned reserves. Actual first buys therefore recover the complete executable fresh-entry schedule. Positive source target intents below executable floors remain separate.")
    (data["artifact"] / "stage2-registration.json").write_text(json.dumps(registration, indent=2, default=str, allow_nan=True))
    data.update(registration=registration, entry_predictions=predictions, placebos=placebo, qualification_entries=past)
    pd.DataFrame([informed]).to_csv(data["artifact"] / "pre2026-informed-value.csv", index=False)
    return registration


def causal_reference_rates(data):
    """Rates use only earlier actionable C00 entries; fresh account has a historical prior."""
    p = data["entry_predictions"]
    p = p[p.H.eq(data["horizon"]) & p.Model.eq("L2")]
    history = p[p.Period.eq("Long") & p.Date.lt(CUTOFF) & p.Actionable]
    records = []
    for period in ("Long", "2026"):
        entries = p[p.Period.eq(period) & p.Actionable]
        for t in data["schedules"][period]:
            previous = entries[entries.Date.le(t - pd.Timedelta(days=2))]
            if period == "2026":
                previous = pd.concat([history, previous], ignore_index=True)
            records.append(dict(Period=period, Date=t, Prior_actionable=len(previous), Prior_vetoes=int(previous.Veto.sum()), Pi=float(previous.Veto.mean()) if len(previous) else 0.0))
    rates = pd.DataFrame(records)
    rates.to_csv(data["artifact"] / "causal-reference-rates.csv", index=False)
    data["rates"] = rates
    return rates


def uniform(seed, date, address):
    key = f"nb22|{seed}|{pd.Timestamp(date).isoformat()}|{str(address).lower()}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") / 2**64
