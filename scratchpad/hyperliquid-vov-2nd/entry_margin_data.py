"""Frozen NB22 inputs, proportional entry attribution and sparse-aware labels."""

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from tradeexecutor.state.state import State
from tradeexecutor.visual.equity_curve import calculate_equity_curve

ROOT = Path(__file__).resolve().parent
PERIODS = {"2026": ("2026-01-01", "2026-10-05"), "Long": ("2023-03-01", "2026-10-08")}
LABELS = {"2026": "2026-01-01–2026-10-04 UTC", "Long": "2023-03-01–2026-10-07 UTC (final day partial)"}
LABELS["Pre2026"] = "2023-03-01–2025-12-31 UTC (past-only qualification)"
CUTOFF = pd.Timestamp("2026-01-01")
HORIZONS = (2, 7, 30)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_generation(number, notebook):
    nb = json.loads((ROOT / notebook).read_text())
    path = Path(nb["metadata"][f"nb{number}"]["artifact_generation"])
    assert path.is_relative_to(ROOT / "_artifacts-restored-2026-10-07"), path
    return path


def initialise():
    """Validate saved inputs and controls without executing a new account."""
    g20 = read_generation(20, "20-backtest-c00-vs-v11.ipynb")
    g21 = read_generation(21, "21-research-marginal-profit-allocation.ipynb")
    m20 = json.loads((g20 / "manifest.json").read_text())
    m21 = json.loads((g21 / "manifest.json").read_text())
    assert m21["identity"]["parent"] == m20["identity"], "NB20/NB21 parent identity"
    for name in ("marginal_profit_data.py", "marginal_profit_forecasts.py"):
        assert sha(ROOT / name) == m21["identity"]["code"][name], f"Frozen forecast input changed: {name}"
    assert sha(ROOT / "clean_c00_v11_comparison.py") == m20["identity"]["code"], "NB20 accounting changed"
    ikey = hashlib.sha256((m21["identity"]["code"]["marginal_profit_data.py"] + json.dumps(m21["identity"]["parent"], sort_keys=True)).encode()).hexdigest()
    feature = g21.parent / "cache" / ikey
    pkey = hashlib.sha256((m21["identity"]["code"]["marginal_profit_forecasts.py"] + str(feature)).encode()).hexdigest()
    forecast = feature / pkey
    downloads = json.loads((ROOT / "_artifacts-restored-2026-10-07/inputs/downloads.json").read_text())
    for name in ("vault_prices", "vault_metadata"):
        assert sha(downloads[name]["path"]) == downloads[name]["sha256"], f"Pinned {name} changed"
    refs = pd.read_csv(g21 / "control-parity.csv").set_index(["Period", "Arm"])
    keys = {("2026", "C00"): "5069fa4abb1b51e73c44bc9f", ("2026", "V11"): "ad45a94c6f34c8c24587def1", ("Long", "C00"): "5fd7f48c3c8ec285ede7bac1", ("Long", "V11"): "93d11e32f55e3bc26e2c1333"}
    inputs = [g20 / "manifest.json", g21 / "manifest.json", feature / "opportunity-panel.parquet", forecast / "forecasts.parquet", forecast / "forecast-snapshots.joblib"]
    inputs += [g20 / "engine" / f"{key}-state.json" for key in keys.values()]
    inputs += [g20 / "engine" / f'{keys[(p,"C00")]}-allocations.csv' for p in PERIODS]
    inputs += [g20 / "robustness.csv", g20 / "tail-audit.csv", g20 / "fee-accounting.csv"]
    identity = dict(version="nb22-v1", parent=m21["identity"], files={str(p): sha(p) for p in inputs}, code={p.name: sha(p) for p in sorted(ROOT.glob("entry_margin_*.py")) + [ROOT / "create_entry_margin_notebook.py"]}, plan=sha(ROOT / "22-c00-attribution-and-opportunity-calibration-plan.md"), periods=PERIODS, prices=downloads["vault_prices"]["sha256"], metadata=downloads["vault_metadata"]["sha256"], ledger_seeds=list(range(1, 1000)), engine_seeds=list(range(1, 6)))
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/22" / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    data = dict(artifact=folder, fingerprint=fingerprint, identity=identity, g20=g20, g21=g21, features=feature, forecasts=forecast, downloads=downloads, keys=keys, states={}, equity={}, allocations={}, figures=[])
    parity = []
    expected_metrics = pd.read_csv(g20 / "results.csv").set_index(["Period", "Arm"])
    for (period, arm), key in keys.items():
        state = State.read_json_file(g20 / "engine" / f"{key}-state.json")
        eq = calculate_equity_curve(state).resample("D").last().ffill()
        saved = pd.read_csv(g20 / f"{period}-{arm}-equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
        assert eq.index.equals(saved.index), (period, arm, "equity calendar")
        error = float((eq - saved).abs().max())
        assert error < 1e-6
        trades = [(str(t.executed_at), str(t.pair.pool_address), float(t.executed_quantity), float(t.executed_price), float(t.executed_reserve)) for t in state.portfolio.get_all_trades() if t.is_success()]
        signature = hashlib.sha256(json.dumps(trades).encode()).hexdigest()
        ref = refs.loc[(period, "B00" if arm == "C00" else "B01")]
        assert signature == ref.Trade_sha256 and len(trades) == ref.Trades, (period, arm, "trade identity")
        assert abs(eq.iloc[-1] - expected_metrics.loc[(period, arm), "Final equity (USD)"]) < 1e-6
        parity.append(dict(Period=period, Arm=arm, Equity_error_USD=error, Trades=len(trades), Trade_sha256=signature))
        data["states"][period, arm] = state
        data["equity"][period, arm] = eq
        if arm == "C00":
            all_trades = list(state.portfolio.get_all_trades())
            assert all(t.is_success() and t.opened_at == t.executed_at for t in all_trades), "Unexecuted/delayed proposal requires a fresh ledger replay"
            assert all(t.planned_reserve == t.executed_reserve for t in all_trades if t.is_buy()), "Funded proposal dollars differ from fills"
            data["allocations"][period] = pd.read_csv(g20 / "engine" / f"{key}-allocations.csv", parse_dates=["Date"])
    data["parity"] = pd.DataFrame(parity)
    data["metrics"] = expected_metrics.reset_index()
    data["parity"].to_csv(folder / "control-parity.csv", index=False)
    (folder / "manifest.json").write_text(json.dumps(dict(identity=identity, fingerprint=fingerprint, reference20=str(g20), reference21=str(g21), status="input/control parity verified"), indent=2, default=str))
    return data


def entry_spells(data):
    """Split actual net sales and held values in proportion to remaining units."""
    rows = []
    sales = []
    intents = []
    for period in PERIODS:
        state = data["states"][period, "C00"]
        end = data["equity"][period, "C00"].index[-1]
        for pos in state.portfolio.get_all_positions():
            if not pos.pair.is_vault():
                continue
            trades = sorted(pos.get_successful_trades(), key=lambda t: (t.executed_at, t.trade_id))
            buys = [t for t in trades if t.is_buy()]
            if not buys:
                continue
            first = buys[0]
            initial_cash = float(first.executed_reserve)
            initial_units = float(first.executed_quantity)
            tagged = 0.0
            added = 0.0
            initial_proceeds = 0.0
            topup_proceeds = 0.0
            topup_cash = 0.0
            paid = 0.0
            for t in trades:
                quantity = float(t.executed_quantity)
                if t.is_buy():
                    if t.trade_id == first.trade_id:
                        tagged += quantity
                    else:
                        added += quantity
                        topup_cash += float(t.executed_reserve)
                    continue
                units = tagged + added
                assert units > 0, (period, pos.position_id, "sale without attributed units")
                fraction = tagged / units
                sold = min(abs(quantity), units)
                proceeds = float(t.executed_reserve)
                initial_proceeds += proceeds * fraction
                topup_proceeds += proceeds * (1 - fraction)
                tagged = max(0.0, tagged - sold * fraction)
                added = max(0.0, added - sold * (1 - fraction))
                gross = abs(quantity) * float(t.planned_mid_price or t.executed_price)
                fee = max(0.0, gross - proceeds)
                paid += fee
                sales.append(dict(Period=period, Position=pos.position_id, Date=pd.Timestamp(t.executed_at), Pair=int(t.pair.internal_id), Initial_fraction=fraction, Actual_net_proceeds=proceeds, Initial_net_proceeds=proceeds * fraction, Topup_net_proceeds=proceeds * (1 - fraction), Modelled_charge=fee))
            value = float(pos.get_value()) if not pos.is_closed() else 0.0
            fraction = tagged / (tagged + added) if tagged + added > 0 else 0.0
            initial_value = value * fraction
            topup_value = value * (1 - fraction)
            total_buy = sum(float(t.executed_reserve) for t in buys)
            total_sale = sum(float(t.executed_reserve) for t in trades if t.is_sell())
            pnl = total_sale + value - total_buy
            tagged_pnl = initial_proceeds + initial_value - initial_cash
            added_pnl = topup_proceeds + topup_value - topup_cash
            residual = tagged_pnl + added_pnl - pnl
            assert abs(residual) < max(1e-7, abs(pnl) * 1e-10), (period, pos.position_id, residual)
            finish = pd.Timestamp(pos.closed_at) if pos.closed_at else end
            opened = pd.Timestamp(first.executed_at)
            dd = 0.0
            previous = opened
            previous_value = 0.0
            for snap in sorted(state.stats.positions.get(pos.position_id, []), key=lambda s: s.calculated_at):
                at = pd.Timestamp(snap.calculated_at)
                dd += previous_value * max(0.0, (at - previous).total_seconds() / 86400)
                previous = at
                previous_value = float(snap.value)
            dd += previous_value * max(0.0, (finish - previous).total_seconds() / 86400)
            rows.append(dict(Period=period, Position=pos.position_id, Date=opened, Pair=int(pos.pair.internal_id), Address=str(pos.pair.pool_address).lower(), Vault=pos.pair.get_vault_name(), Closed=pos.is_closed(), Closed_at=pd.Timestamp(pos.closed_at) if pos.closed_at else pd.NaT, End=finish, Days=(finish - opened).total_seconds() / 86400, Q=initial_cash, Initial_units=initial_units, Topup_cash=topup_cash, Initial_proceeds=initial_proceeds, Initial_value=initial_value, Topup_value=topup_value, Initial_profit=tagged_pnl, Spell_profit=pnl, Y_spell=tagged_pnl / initial_cash, Modelled_paid_charges=paid, Dollar_days=dd, Reconciliation_residual=residual))
        a = data["allocations"][period].copy()
        a = a[a["Old value (USD)"].le(1e-8) & a["Final target (USD)"].gt(0)]
        a["Period"] = period
        intents.append(a)
    spells = pd.DataFrame(rows).sort_values(["Period", "Address", "Date"]).reset_index(drop=True)
    next_open = spells.groupby(["Period", "Address"]).Date.shift(-1)
    spells["Reentry_days"] = (next_open - spells.Closed_at).dt.total_seconds() / 86400
    spells["Reentered_2d"] = spells.Closed & spells.Reentry_days.between(0, 2)
    spells["Reentered_4d"] = spells.Closed & spells.Reentry_days.between(0, 4)
    assert spells[["Reconciliation_residual"]].abs().max().iloc[0] < 1e-6
    spells.to_parquet(data["artifact"] / "entry-spells.parquet", index=False)
    pd.DataFrame(sales).to_parquet(data["artifact"] / "tagged-sales.parquet", index=False)
    pd.concat(intents, ignore_index=True).to_parquet(data["artifact"] / "unfunded-inclusive-source-intents.parquet", index=False)
    data.update(spells=spells, source_intents=pd.concat(intents, ignore_index=True))
    return spells


def nav_history(data, identities):
    """Actual positive NAV observations; duplicate timestamps retain the last row."""
    mapping = identities.set_index("vault_address").pair_id.to_dict()
    raw = ds.dataset(data["downloads"]["vault_prices"]["path"], format="parquet").to_table(columns=["timestamp", "address", "share_price"], filter=(ds.field("chain") == 9999) & ds.field("address").isin(list(mapping))).to_pandas().reset_index()
    raw["timestamp"] = pd.to_datetime(raw.timestamp, utc=True).dt.tz_convert(None)
    raw = raw[np.isfinite(raw.share_price) & raw.share_price.gt(0)].copy()
    raw["pair_id"] = raw.address.map(mapping).astype(int)
    raw = raw.sort_values(["pair_id", "timestamp"], kind="stable").drop_duplicates(["pair_id", "timestamp"], keep="last")
    return {int(pid): (g.timestamp.to_numpy(dtype="datetime64[ns]").astype("int64"), g.share_price.to_numpy(float)) for pid, g in raw.groupby("pair_id")}


def fresh_labels(history, pid, t, h):
    """Causal carried marks with future report confirmation and explicit maturity."""
    empty = dict(Gross=np.nan, Y_net=np.nan, Y_mark=np.nan, Resolved=False, Mature_at=pd.NaT, Origin_observed_at=pd.NaT, Endpoint_observed_at=pd.NaT, Support_observed_at=pd.NaT, Endpoint_age=np.nan, Actual_updates=0)
    if int(pid) not in history:
        return empty
    times, prices = history[int(pid)]
    start = pd.Timestamp(t)
    end = start + pd.Timedelta(days=h)
    i = np.searchsorted(times, start.value, side="right") - 1
    j = np.searchsorted(times, end.value, side="right") - 1
    if i < 0 or j < 0:
        return empty
    r = float(prices[j] / prices[i] - 1)
    net = fresh_net_return(r)
    support = np.searchsorted(times, end.value, side="left")
    resolved = support < len(times)
    mature = max(end, pd.Timestamp(times[support])) if resolved else pd.NaT
    return dict(Gross=r, Y_net=net if resolved else np.nan, Y_mark=net, Resolved=resolved, Mature_at=mature, Origin_observed_at=pd.Timestamp(times[i]), Endpoint_observed_at=pd.Timestamp(times[j]), Support_observed_at=pd.Timestamp(times[support]) if resolved else pd.NaT, Endpoint_age=(end.value - times[j]) / 86400e9, Actual_updates=int(np.searchsorted(times, end.value, side="right") - np.searchsorted(times, start.value, side="right")))


def fresh_net_return(gross_return):
    """Use the frozen empirical liquidation helper for a deterministic fresh entry."""
    from marginal_profit_forecasts import Distribution, Shape

    one = Shape(np.array([1.0]), np.array([1.0]))
    r = float(gross_return)
    return Distribution(float(r < 0), max(r, 0), max(-r, 0), one, one).terminal(1.0, 1.0) - 1


def build_panel(data):
    """Freeze population before joining outcomes; keep actual entries outside the band."""
    panel = pd.read_parquet(data["features"] / "opportunity-panel.parquet")
    base = panel[panel.H.eq(2)].copy()
    assert not base.duplicated(["Date", "Pair"]).any()
    # Source cycles are aligned by the engine, not by a new date_range anchor.
    # Preserve each saved account's actual native decision timestamps.
    schedules = {}
    coverage = []
    for p, (start, end) in PERIODS.items():
        ticks = pd.DatetimeIndex([s.calculated_at for s in data["states"][p, "C00"].stats.portfolio])
        ticks = ticks[(ticks >= start) & (ticks < end)].unique().sort_values()
        schedules[p] = ticks
        missing = ticks.difference(base.Date.unique())
        entries = data["spells"].loc[data["spells"].Period.eq(p), "Date"]
        assert not entries.isin(missing).any(), "An executable proposal lacks frozen causal features"
        allocations = pd.DatetimeIndex(data["allocations"][p].Date.unique())
        assert not missing.isin(allocations).any(), "A source target date lacks frozen causal features"
        coverage.append(dict(Period=p, Native_decisions=len(ticks), Feature_covered_decisions=len(ticks) - len(missing), Unavailable_warmup_decisions=len(missing), Actual_proposals_on_unavailable_dates=0, Handling="No frozen feature/forecast rows; no source targets or executable entries; pass through C00"))
    data["native_coverage"] = pd.DataFrame(coverage)
    data["native_coverage"].to_csv(data["artifact"] / "native-calendar-coverage.csv", index=False)
    native = set().union(*(set(v) for v in schedules.values()))
    base = base[base.Date.isin(native)].copy()
    ranked = base[base.eligible_as_of_origin].copy()
    ranked["Ranking_score"] = ranked.c00_score.fillna(0)
    ranked = ranked.sort_values(["Date", "Ranking_score", "vault_address"], ascending=[True, False, True], kind="stable")
    ranked["Rank"] = ranked.groupby("Date").cumcount() + 1
    bands = ranked[ranked.Rank.le(8)][["Date", "Pair", "Rank"]].copy()
    bands["In_band"] = True
    entries = data["spells"][["Period", "Position", "Date", "Pair", "Q", "Closed", "Closed_at", "Y_spell", "Days", "Vault", "Address", "Initial_profit"]].copy()
    selected = entries[["Date", "Pair"]].drop_duplicates().merge(bands, on=["Date", "Pair"], how="outer")
    selected["In_band"] = selected.In_band.astype("boolean").fillna(False).astype(bool)
    features = selected.merge(base.drop(columns=["H", "Y", "Y_mark", "Resolved", "Mature_at", "Endpoint_age"]), on=["Date", "Pair"], how="left", validate="one_to_one")
    assert features.feature_cutoff.dropna().lt(features.Date[features.feature_cutoff.notna()]).all(), "T−1 features"
    ids = base[["pair_id", "vault_address", "vault_name"]].drop_duplicates("pair_id")
    data["nav_history"] = nav_history(data, ids)
    # Unknown-at-cutoff spells use only then-known trades and NAV in the mark scenario.
    pre_marks = {}
    for pos in data["states"]["Long", "C00"].portfolio.get_all_positions():
        if not pos.pair.is_vault():
            continue
        trades = sorted([t for t in pos.get_successful_trades() if pd.Timestamp(t.executed_at) < CUTOFF], key=lambda t: (t.executed_at, t.trade_id))
        if not trades or not trades[0].is_buy():
            continue
        initial = float(trades[0].executed_reserve)
        tagged = 0.0
        added = 0.0
        basis = 0.0
        proceeds = 0.0
        for t in trades:
            q = float(t.executed_quantity)
            if t.is_buy():
                if t.trade_id == trades[0].trade_id:
                    tagged += q
                else:
                    added += q
                basis += float(t.executed_reserve)
            else:
                units = tagged + added
                fraction = tagged / units
                remaining = max(0.0, 1 - abs(q) / units)
                proceeds += float(t.executed_reserve) * fraction
                tagged *= remaining
                added *= remaining
                basis *= remaining
        units = tagged + added
        mark = 0.0
        if units > 0:
            times, prices = data["nav_history"][int(pos.pair.internal_id)]
            i = np.searchsorted(times, CUTOFF.value, side="left") - 1
            assert i >= 0
            gross = units * prices[i]
            net = (1 - 0.001) * gross - 0.10 * max(gross - basis, 0)
            mark = net * tagged / units
        pre_marks[pos.position_id] = (proceeds + mark - initial) / initial
    entries["Pre2026_mark_Y"] = entries.Position.map(pre_marks).where(entries.Period.eq("Long"))
    expansions = []
    for h in HORIZONS:
        f = features.copy()
        f["H"] = h
        labels = pd.DataFrame([fresh_labels(data["nav_history"], pid, t, h) for t, pid in f[["Date", "Pair"]].itertuples(index=False, name=None)], index=f.index)
        expansions.append(pd.concat([f, labels], axis=1))
    out = pd.concat(expansions, ignore_index=True)
    forecast = pd.read_parquet(data["forecasts"] / "forecasts.parquet", filters=[("Model", "==", "D")])
    cols = ["Date", "Pair", "H", "Fit", "Supported", "Prior_available", "Magnitude_fallback", "p", "g", "ell", "net", "profit_probability"]
    out = out.merge(forecast[cols], on=["Date", "Pair", "H"], how="left", validate="one_to_one")
    out["Supported"] = out.Supported.astype("boolean").fillna(False).astype(bool)
    out["Prior_available"] = out.Prior_available.astype("boolean").fillna(False).astype(bool)
    out["L1"] = out.c00_score
    out["L2"] = out.net.where(out.Supported)
    out["Missing_score"] = out.c00_score.isna()
    out["Supported_D"] = out.Supported & out.net.notna()
    # Cached D predictions are regenerated from each frozen distribution before reuse.
    from marginal_profit_forecasts import Distribution, predict_snapshot

    snapshots = joblib.load(data["forecasts"] / "forecast-snapshots.joblib")
    checks = []
    for (h, fit), f in out[out.Prior_available & out.Fit.notna()].groupby(["H", "Fit"]):
        snap = snapshots[int(h), pd.Timestamp(fit)]
        assert snap is not None and snap["max_mature"] < fit and fit <= f.Date.min()
        triples = predict_snapshot(snap, f, "D")
        net = np.array([Distribution(*v, snap["positive"], snap["negative"]).terminal(1.0, 1.0) - 1 for v in triples])
        error = float(np.max(np.abs(net - f.net.to_numpy(float))))
        assert error < 1e-10, (h, fit, "D distribution parity", error)
        checks.append(dict(H=h, Fit=fit, Rows=len(f), Underlying_max_mature=snap["max_mature"], Net_error=error, Supported=snap["supported"]))
    data.update(panel=out, base=base, ranked=ranked, schedules=schedules, forecast_checks=pd.DataFrame(checks))
    # Actual executed new entries are an executable subset; unfilled targets are not called executable.
    ep = entries.merge(out, on=["Date", "Pair"], how="left", suffixes=("", "_feature"))
    assert ep.H.notna().all(), "Actual entry absent from frozen feature panel"
    data["entries"] = ep
    appearances = ranked[ranked.Rank.le(6)].groupby("Pair").Date.min()
    data["entries"]["First_top6_appearance"] = data["entries"].Date.eq(data["entries"].Pair.map(appearances))
    out.to_parquet(data["artifact"] / "opportunities.parquet", index=False)
    ep.to_parquet(data["artifact"] / "actual-entries.parquet", index=False)
    data["forecast_checks"].to_csv(data["artifact"] / "frozen-D-parity.csv", index=False)
    training = pd.read_csv(data["forecasts"] / "training-audit.csv")
    data["underlying_training_audit"] = training
    data["fundability"] = boundary_fundability(data)
    data["fundability"].to_parquet(data["artifact"] / "boundary-fundability.parquet", index=False)
    return out


def boundary_fundability(data):
    """Diagnostic cap/ticket bounds; never an executable alternative trade claim."""
    rows = []
    for period in PERIODS:
        state = data["states"][period, "C00"]
        trades = sorted([t for t in state.portfolio.get_all_trades() if t.is_success()], key=lambda t: (t.executed_at, t.trade_id))
        positions = {p.position_id: p for p in state.portfolio.get_all_positions() if p.pair.is_vault()}
        band = data["panel"][data["panel"].H.eq(2) & data["panel"].In_band & data["panel"].Date.isin(data["schedules"][period])]
        units = {}
        basis = {}
        cash = 150000.0
        cursor = 0
        for date, f in band.groupby("Date"):
            while cursor < len(trades) and pd.Timestamp(trades[cursor].executed_at) < date:
                t = trades[cursor]
                cursor += 1
                i = t.position_id
                before = units.get(i, 0.0)
                q = float(t.executed_quantity)
                if t.is_buy():
                    basis[i] = basis.get(i, 0.0) + float(t.executed_reserve)
                elif before > 0:
                    basis[i] = basis.get(i, 0.0) * max(0.0, 1 - abs(q) / before)
                units[i] = max(0.0, before + q)
                cash += float(t.executed_reserve) * (-1 if t.is_buy() else 1)
            held = set()
            equity = cash
            for i, q in units.items():
                p = positions[i]
                if q <= 0 or p.closed_at and pd.Timestamp(p.closed_at) < date:
                    continue
                pid = int(p.pair.internal_id)
                held.add(pid)
                times, prices = data["nav_history"][pid]
                k = np.searchsorted(times, date.value, side="right") - 1
                assert k >= 0
                gross = q * prices[k]
                equity += (1 - 0.001) * gross - 0.10 * max(gross - basis.get(i, 0.0), 0)
            a = data["allocations"][period]
            a = a[a.Date.eq(date)]
            B = float(a["Deployable budget (USD)"].iloc[0]) if len(a) else 0.98 * equity
            residual = max(0.0, B - a["Final target (USD)"].sum())
            actual = data["spells"][data["spells"].Period.eq(period) & data["spells"].Date.eq(date)]
            minimum = max(5.0, 0.0005 * max(0.0, equity))
            for row in f.itertuples():
                pid = int(row.Pair)
                tvl = np.expm1(row.log_tvl) if np.isfinite(row.log_tvl) else np.nan
                cap = min(0.33 * B, 0.33 * tvl) if np.isfinite(tvl) else np.nan
                if np.isfinite(row.max_deposit):
                    cap = min(cap, float(row.max_deposit))
                feasible = bool(row.can_deposit == 1 and np.isfinite(cap) and cap >= minimum)
                is_held = pid in held
                is_actual = pid in set(actual.Pair)
                kind = "held / not a fresh opportunity" if is_held else "actual executed new entry" if is_actual else "not minimum-cap-feasible" if not feasible else "add: residual budget and free slot" if residual >= minimum and len(held) < 6 else "replacement: actual new entry could be redirected" if len(actual) else "not currently fundable under unchanged slots/budget"
                rows.append(dict(Period=period, Date=date, Pair=pid, Rank=row.Rank, Minimum_ticket_USD=minimum, Static_cap_USD=cap, Minimum_cap_feasible=feasible, Predecision_cash_USD=cash, Predecision_equity_USD=equity, Held_slots=len(held), Residual_target_budget_USD=residual, Actual_entry=is_actual, Boundary_role=kind))
    return pd.DataFrame(rows)


def register_horizon(data):
    """Select H2/H7 using fully closed pre-2026 initial-unit spells only."""
    e = data["entries"]
    past = e[e.Period.eq("Long") & e.Closed & e.Closed_at.lt(CUTOFF) & e.Mature_at.lt(CUTOFF) & e.H.isin([2, 7]) & e.Resolved].copy()
    common = past.groupby("Position").H.nunique().eq(2)
    past = past[past.Position.isin(common[common].index)]
    rows = []
    for h, g in past.groupby("H"):
        error = (g.Y_net - g.Y_spell).abs()
        f = g.assign(Error=error)
        date = f.groupby("Date").apply(lambda x: np.average(x.Error, weights=x.Q), include_groups=False)
        rows.append(dict(H=int(h), Closed_spells=len(g), Origins=g.Date.nunique(), Equal_spell_MAE=float(error.mean()), Capital_weighted_MAE=float(np.average(error, weights=g.Q)), Equal_origin_capital_MAE=float(date.mean()), Winning_MAE=float(error[g.Y_spell.ge(0)].mean()), Losing_MAE=float(error[g.Y_spell.lt(0)].mean())))
    table = pd.DataFrame(rows)
    h = int(table.sort_values(["Equal_origin_capital_MAE", "H"]).iloc[0].H) if len(table) else 7
    registration = dict(horizon=h, common_closed_spells=int(past.Position.nunique()), cutoff=str(CUTOFF), rule="Lowest equal-origin cash-weighted discrepancy on common closed pre-2026 spells; tie H2", approximation=not len(table), h2_penalty_warning="NB21 H2 prior-fold penalty selection was unsupported; frozen fallback retained", engine_stage="not yet qualified")
    (data["artifact"] / "horizon-registration.json").write_text(json.dumps(registration, indent=2))
    table.to_csv(data["artifact"] / "horizon-alignment.csv", index=False)
    data.update(horizon=h, horizon_registration=registration, horizon_table=table)
    return registration
