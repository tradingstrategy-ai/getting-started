"""Bounded monthly-score calibration followed by fixed-allocation backtests."""

from pathlib import Path
import itertools
import json
import hashlib
import inspect
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from tqdm_loggable.auto import tqdm

from nb23_profitable_months import STRATWISE, set_single_redemption_fee, verify
from nb20_stability_screens import curve_metrics

CUTOFF = pd.Timestamp("2026-04-01")
END = pd.Timestamp("2026-09-09")
GRID = pd.DataFrame([dict(config=f"C{i:02}", alpha=a, penalty=l, severity=u, tau=t, lookback=b) for i, (a, l, u, t, b) in enumerate(itertools.product([1, 2], [0, 1, 2], [0, 1], [0.01, 0.02], [3, 6]))])


def features(series, date, lookback):
    """Use strictly earlier marks; sparse and short histories remain eligible."""
    s = series.loc[series.index < date].dropna()
    if len(s) < 2 or s.index[-1] - s.index[0] < pd.Timedelta("1d"):
        return None
    boundary = date.to_period("M").start_time
    values = []
    for k in range(lookback, 0, -1):
        left = boundary - pd.DateOffset(months=k)
        right = left + pd.DateOffset(months=1)
        a = s.index.searchsorted(left, side="left") - 1
        b = s.index.searchsorted(right, side="left") - 1
        if a >= 0 and b >= 0:
            values.append(s.iloc[b] / s.iloc[a] - 1)
    provisional = not values
    r = np.asarray(values if values else [s.iloc[-1] / s.iloc[0] - 1])
    pos = r[r > 0]
    gate_index = max(s.index.searchsorted(date - pd.Timedelta("14d"), side="left") - 1, 0)
    return dict(p=float((r > 0).mean()), q=float((r < 0).mean()), gain=float(np.median(pos)) if len(pos) else 0.0, downside=float(-np.minimum(r, 0).mean()), months=len(values), provisional=provisional, age=(date - s.index[0]).total_seconds() / 86400, gate=float(s.iloc[-1] / s.iloc[gate_index] - 1))


def score(frame, config):
    return frame.p ** config["alpha"] * np.minimum(frame.gain / config["tau"], 1) * np.exp(-config["penalty"] * frame.q - config["severity"] * frame.downside / config["tau"])


def check():
    verify()
    d = pd.DataFrame(dict(p=[1, 1, 2 / 3, 2 / 3], q=[0, 0, 1 / 3, 1 / 3], gain=[0.02, 0.01, 0.02, 0.06], downside=[0, 0, 0.01 / 3, 0.1 / 3]))
    v = score(d, dict(alpha=2, penalty=2, severity=1, tau=0.02))
    assert v[0] > v[1] > v[2] > v[3] > 0
    s = pd.Series([1.0, 1.01], index=pd.to_datetime(["2026-07-16", "2026-07-23"]))
    f = features(s, pd.Timestamp("2026-07-24"), 6)
    assert f["provisional"] and f["gate"] > 0
    extended = pd.concat([s, pd.Series([99.0], index=pd.to_datetime(["2026-07-24"]))])
    assert features(extended, pd.Timestamp("2026-07-24"), 6) == f
    assert len(GRID) == 48


def panel(ns):
    """Build causal features and separately matured future-outcome labels."""
    out = ns["OUT"]
    path = ns["PRICE_PATH"]
    stat = path.stat()
    signature = hashlib.sha256((inspect.getsource(features) + inspect.getsource(panel) + str((stat.st_size, stat.st_mtime_ns)) + str(sorted(ns["off_addresses"]))).encode()).hexdigest()
    cache = out / "panel.parquet"
    sig = out / "panel.signature"
    if cache.exists() and sig.exists() and sig.read_text() == signature:
        result = pd.read_parquet(cache)
    else:
        raw = pd.read_parquet(path, columns=["address", "share_price", "total_assets"], filters=[("address", "in", sorted(ns["off_addresses"]))])
        rows = []
        dates = pd.date_range("2025-07-31", "2026-09-08")
        started = time.monotonic()
        for i, (address, g) in enumerate(tqdm(raw.groupby("address"), desc="Calibration features and labels")):
            g = g.sort_index()
            s = g.share_price.dropna()
            idx = s.index
            for date in dates:
                j = idx.searchsorted(date, side="left") - 1
                if j < 1:
                    continue
                assets = g.loc[g.index < date, "total_assets"].dropna()
                eligible_tvl = bool(len(assets) and assets.iloc[-1] >= ns["Parameters"].min_tvl_usd)
                outcomes = {}
                for h in [30, 60]:
                    stop = date + pd.Timedelta(days=h)
                    end = idx.searchsorted(stop, side="left") - 1
                    valid = stop <= END and end > j and date - idx[j] <= pd.Timedelta("7d") and stop - idx[end] <= pd.Timedelta("7d")
                    r = dd = neg = np.nan
                    if valid:
                        path_values = s.iloc[j : end + 1].to_numpy()
                        r = path_values[-1] / path_values[0] - 1
                        dd = float((path_values / np.maximum.accumulate(path_values) - 1).min())
                        endpoints = [s.iloc[j]]
                        for step in range(30, h + 1, 30):
                            cutoff = date + pd.Timedelta(days=step)
                            k = idx.searchsorted(cutoff, side="left") - 1
                            if cutoff - idx[k] > pd.Timedelta("7d"):
                                valid = False
                                break
                            endpoints.append(s.iloc[k])
                        if valid:
                            neg = float((np.diff(endpoints) / np.asarray(endpoints[:-1]) < 0).mean())
                    outcomes.update({f"return_{h}": r if valid else np.nan, f"drawdown_{h}": dd if valid else np.nan, f"negative_blocks_{h}": neg if valid else np.nan})
                for lb in [3, 6]:
                    f = features(s, date, lb)
                    if f is not None:
                        rows.append(dict(address=address, date=date, lookback=lb, tvl_eligible=eligible_tvl, **f, **outcomes))
            if (i + 1) % 60 == 0:
                print(f"{i+1}/360 vaults, elapsed {(time.monotonic()-started)/60:.1f} minutes", flush=True)
        result = pd.DataFrame(rows)
        result.to_parquet(cache, index=False)
        sig.write_text(signature)
    ns["CAL_FEATURES"] = result
    ns["CAL_LOOKUP"] = {(r["date"], r["address"], r["lookback"]): r for r in result[["address", "date", "lookback", "p", "q", "gain", "downside", "months", "provisional", "age", "gate"]].to_dict("records")}
    GRID.to_csv(out / "grid.csv", index=False)
    display(result.groupby("lookback").agg(rows=("address", "size"), vaults=("address", "nunique"), first_date=("date", "min"), last_date=("date", "max")))
    return result


def evaluate(ns):
    """Rank before masking unavailable labels; every date has equal weight."""
    f = ns["CAL_FEATURES"]
    daily = []
    for cfg in tqdm(GRID.to_dict("records"), desc="48 ranking calibrations"):
        base = f[(f.lookback == cfg["lookback"]) & f.tvl_eligible & f.gate.gt(0) & f.date.ge("2025-09-13")].copy()
        base["score"] = score(base, cfg)
        for cohort in ["all", "young", "mature"]:
            d = base if cohort == "all" else base[base.age.lt(90) if cohort == "young" else base.age.ge(90)]
            d = d.sort_values(["date", "score", "address"], ascending=[True, False, True]).copy()
            size = d.groupby("date").address.transform("size")
            d["top"] = d.groupby("date").cumcount() < np.ceil(size * 0.2)
            for h in [30, 60]:
                mature = d.date + pd.Timedelta(days=h) <= END
                x = d[mature].copy()
                x["split"] = np.where(x.date + pd.Timedelta(days=h) <= CUTOFF, "train", np.where(x.date >= CUTOFF, "later", "embargo"))
                x = x[x.split != "embargo"]
                x["ret"] = x[f"return_{h}"]
                x["dd"] = x[f"drawdown_{h}"]
                x["negative_blocks"] = x[f"negative_blocks_{h}"]
                x["positive"] = np.where(x.ret.notna(), (x.ret > 0).astype(float), np.nan)
                x["loss"] = x.ret.clip(upper=0)
                for target in ["ret", "dd"]:
                    valid = x[target].notna()
                    rank_s = x.loc[valid].groupby("date").score.rank()
                    rank_y = x.loc[valid].groupby("date")[target].rank()
                    z = pd.DataFrame({"date": x.loc[valid, "date"], "a": rank_s, "b": rank_y})
                    z["a"] = z.a - z.groupby("date").a.transform("mean")
                    z["b"] = z.b - z.groupby("date").b.transform("mean")
                    sums = z.assign(ab=z.a * z.b, aa=z.a**2, bb=z.b**2).groupby("date")[["ab", "aa", "bb"]].sum()
                    ic = sums.ab / np.sqrt(sums.aa * sums.bb)
                    x[f"ic_{target}"] = x.date.map(ic)
                for date, g in x.groupby("date"):
                    if g.ret.notna().sum() < 5:
                        continue
                    top = g[g.top]
                    rest = g[~g.top]
                    if not top.ret.notna().any() or not rest.ret.notna().any():
                        continue
                    r = dict(config=cfg["config"], cohort=cohort, horizon=h, date=date, split=g.split.iloc[0], pool=len(g), labelled=int(g.ret.notna().sum()), top_coverage=float(top.ret.notna().mean()), rest_coverage=float(rest.ret.notna().mean()), unique_scores=g.score.nunique(), ic_return=g.ic_ret.iloc[0], ic_drawdown=g.ic_dd.iloc[0])
                    for name in ["ret", "dd", "positive", "loss", "negative_blocks"]:
                        r[f"top_{name}"] = top[name].mean()
                        r[f"rest_{name}"] = rest[name].mean()
                        r[f"lift_{name}"] = r[f"top_{name}"] - r[f"rest_{name}"]
                    daily.append(r)
    daily = pd.DataFrame(daily)
    daily.to_csv(ns["OUT"] / "daily-ranking-results.csv", index=False)
    columns = [c for c in daily.select_dtypes("number").columns if c != "horizon"]
    summary = daily.groupby(["config", "cohort", "horizon", "split"])[columns].mean().reset_index()
    counts = daily.groupby(["config", "cohort", "horizon", "split"]).size().rename("dates").reset_index()
    summary = summary.merge(counts).merge(GRID, on="config")
    summary.to_csv(ns["OUT"] / "ranking-summary.csv", index=False)
    train = summary[(summary.cohort == "all") & (summary.split == "train")]
    candidates = train.groupby("config").agg(horizons=("horizon", "nunique"), min_return=("top_ret", "min"), min_positive_lift=("lift_positive", "min"), worst_dd_lift=("lift_dd", "min"), min_dates=("dates", "min")).reset_index().merge(GRID)
    assert candidates.horizons.eq(2).all()
    dimensions = ["alpha", "penalty", "severity", "tau", "lookback"]
    stability = []
    for row in candidates.to_dict("records"):
        distance = (candidates[dimensions] != pd.Series({k: row[k] for k in dimensions})).sum(axis=1)
        neighbours = candidates[(distance <= 1) & ((candidates.penalty - row["penalty"]).abs() <= 1)]
        stability.append(neighbours.worst_dd_lift.median())
    candidates["neighbour_median_dd_lift"] = stability
    candidates["qualifies"] = (candidates.min_return > 0) & (candidates.min_positive_lift >= 0) & (candidates.worst_dd_lift > 0) & (candidates.neighbour_median_dd_lift > 0)
    candidates = candidates.sort_values(["qualifies", "neighbour_median_dd_lift", "worst_dd_lift", "config"], ascending=[False, False, False, True])
    chosen = candidates.head(3).copy()
    chosen["status"] = np.where(chosen.qualifies, "training lead", "diagnostic only: failed training criteria")
    candidates.to_csv(ns["OUT"] / "training-selection.csv", index=False)
    chosen.to_csv(ns["OUT"] / "shortlist.csv", index=False)
    ns["SHORTLIST"] = chosen
    display(chosen)
    display(summary[(summary.config.isin(chosen.config)) & (summary.cohort == "all")])
    return summary


def run_backtests(ns):
    """Only ranking varies among matched arms; anchors are lineage references."""
    out = ns["OUT"]
    metrics = []
    positions = []
    allocations = []
    fees = []
    picks = []
    configs = {r["config"]: r for r in ns["SHORTLIST"].to_dict("records")}
    windows = {"hyper_ai": ("2026-01-01", "2026-07-10"), "full": ("2025-08-01", "2026-09-09"), "later": ("2026-04-01", "2026-09-09")}
    jobs = [(period, rule, set()) for period in windows for rule in ["matched_original"] + list(configs)]
    jobs = [("hyper_ai", "anchor", set()), ("full", "anchor", set())] + jobs
    first = next(iter(configs))
    baseline_states = {}

    def run(period, rule, masked):
        ns["CAL_RULE"] = rule
        ns["CAL_CONFIG"] = configs.get(rule)
        ns["MONTH_RULE"] = "anchor"
        ns["CYCLE_LOG"].clear()
        ns["SCREEN_LOG"].clear()
        ns["CAL_LOG"].clear()
        start, end = windows[period]
        overrides = {} if rule == "anchor" else {"weighting_method": "equal"}
        with ns["patch"]("tradeexecutor.strategy.pandas_trader.position_manager.PositionManager.is_problematic_pair", return_value=False):
            state, eq, _ = ns["run_variant"](f"calibration-{period}-{rule}", masked=masked, backtest_start=pd.Timestamp(start).to_pydatetime(), backtest_end=pd.Timestamp(end).to_pydatetime(), **overrides)
        label = rule + ("_leader_out" if masked else "")
        keys = {"period": period, "rule": label}
        eq.attrs = {}
        eq.rename("equity").to_frame().to_parquet(out / f"curve-{period}-{label}.parquet")
        begins = "2025-09-13" if period == "full" else start
        ends = "2026-07-08" if period == "hyper_ai" else "2026-09-08"
        metrics.append({**keys, **curve_metrics(eq.loc[begins:ends])})
        if rule == "anchor":
            old = pd.read_parquet(ns["PROJECT"] / "_artifacts-profitable-months" / f"curve-{period}-anchor-6.parquet").equity
            assert eq.index.equals(old.index) and np.allclose(eq, old, rtol=0, atol=1e-7)
        local = []
        for pos in state.portfolio.get_all_positions():
            if pos.is_credit_supply():
                continue
            address = str(pos.pair.pool_address).lower()
            r = {**keys, "address": address, "name": ns["META"].get(address, {}).get("name"), "position_id": pos.position_id, "opened_at": pos.opened_at, "pnl": float(pos.get_total_profit_usd() or 0)}
            local.append(r)
            positions.append(r)
            for trade in pos.trades.values():
                if trade.is_sell() and trade.executed_at is not None:
                    expected = trade.other_data["nb23_gross_redemption_mid"] * (1 - trade.other_data["backtest_vault_redemption_fee"])
                    assert np.isclose(trade.executed_price, expected, rtol=1e-9, atol=1e-12)
                    fees.append({**keys, "trade_id": trade.trade_id, "expected": expected, "actual": trade.executed_price})
        allocations.extend([{**keys, **r} for r in ns["CYCLE_LOG"]])
        picks.extend([{**keys, **r} for r in ns["CAL_LOG"]])
        for filename, rows in [("portfolio-metrics", metrics), ("positions", positions), ("allocations", allocations), ("redemption-checks", fees), ("selection-log", picks)]:
            pd.DataFrame(rows).to_csv(out / f"{filename}.csv", index=False)
        return pd.DataFrame(local)

    for i, (period, rule, mask) in enumerate(tqdm(jobs, desc="Fixed-allocation backtests")):
        print(f"Backtest {i+1}/{len(jobs)}: {period}/{rule}", flush=True)
        local = run(period, rule, mask)
        if period == "later" and rule == first:
            baseline_states["positions"] = local
    attribution = baseline_states["positions"].groupby("address").pnl.sum()
    leader = attribution.idxmax()
    print(f"Validation stress: remove leading contributor {leader} from {first} and re-simulate", flush=True)
    (out / "leader-stress.json").write_text(json.dumps(dict(config=first, excluded=leader, original_pnl=float(attribution.max()))))
    run("later", first, {leader})
    display(pd.DataFrame(metrics))


def calibration_diagnostics(ns):
    """Expose saturated rankings and balanced one-parameter contrasts."""
    out = ns["OUT"]
    f = pd.read_parquet(out / "panel.parquet")
    rows = []
    for c in GRID.to_dict("records"):
        d = f[(f.lookback == c["lookback"]) & f.tvl_eligible & f.gate.gt(0) & f.date.ge("2025-09-13")].copy()
        d["score"] = score(d, c)
        d["saturated"] = np.isclose(d.score, 1, atol=1e-12, rtol=0)
        z = d.groupby("date").agg(pool=("address", "size"), saturated=("saturated", "sum"))
        for split, cond in [("train", z.index + pd.Timedelta("60d") <= CUTOFF), ("later", z.index >= CUTOFF)]:
            t = z.loc[cond]
            rows.append(dict(config=c["config"], split=split, mean_saturated=t.saturated.mean(), mean_saturated_fraction=(t.saturated / t.pool).mean(), fraction_dates_at_least_six=(t.saturated >= 6).mean()))
    saturation = pd.DataFrame(rows)
    saturation.to_csv(out / "score-saturation.csv", index=False)
    summary = pd.read_csv(out / "ranking-summary.csv")
    s = summary[summary.cohort.eq("all")]
    effects = []
    dimensions = ["alpha", "penalty", "severity", "tau", "lookback"]
    outcomes = ["top_ret", "lift_positive", "lift_dd", "ic_return", "ic_drawdown"]
    for dimension, low, high in [("alpha", 1, 2), ("penalty", 0, 1), ("penalty", 1, 2), ("severity", 0, 1), ("tau", 0.02, 0.01), ("lookback", 6, 3)]:
        join = ["split", "horizon"] + [c for c in dimensions if c != dimension]
        pairs = s[s[dimension].eq(low)].merge(s[s[dimension].eq(high)], on=join, suffixes=("_low", "_high"))
        for (split, horizon), g in pairs.groupby(["split", "horizon"]):
            effects.append(dict(parameter=dimension, change=f"{low} -> {high}", split=split, horizon=horizon, pairs=len(g), **{f"delta_{c}": float((g[c + "_high"] - g[c + "_low"]).mean()) for c in outcomes}))
    effects = pd.DataFrame(effects)
    effects.to_csv(out / "paired-parameter-effects.csv", index=False)
    return saturation, effects


def report(ns):
    out = ns["OUT"]
    summary = pd.read_csv(out / "ranking-summary.csv")
    chosen = pd.read_csv(out / "shortlist.csv")
    metrics = pd.read_csv(out / "portfolio-metrics.csv")
    pos = pd.read_csv(out / "positions.csv")
    a = pd.read_csv(out / "allocations.csv")
    assert len(metrics) == 15
    saturation, effects = calibration_diagnostics(ns)
    diagnostic = pd.read_csv(out / "training-selection.csv")
    stress = json.loads((out / "leader-stress.json").read_text())
    assert not pos.loc[(pos.period == "later") & pos.rule.eq(stress["config"] + "_leader_out"), "address"].eq(stress["excluded"]).any()
    attribution = pos.groupby(["period", "rule", "address", "name"], dropna=False).pnl.sum().reset_index()
    attribution.to_csv(out / "vault-attribution.csv", index=False)
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, QUARANTINE_PERIODS

    pos["curator_excluded"] = pos.address.isin(EXCLUDED_VAULTS)
    pos["quarantined_entry"] = [any(r.address == address and pd.Timestamp(lo) <= pd.Timestamp(r.opened_at) <= pd.Timestamp(hi) for address, lo, hi, _ in QUARANTINE_PERIODS) for r in pos.itertuples()]
    pos.to_csv(out / "position-audit.csv", index=False)
    top = attribution.sort_values("pnl", ascending=False).groupby(["period", "rule"]).head(1).copy()
    gross = attribution.assign(positive=attribution.pnl.clip(lower=0)).groupby(["period", "rule"]).positive.sum()
    top["positive_pnl_share"] = [r.pnl / gross.loc[(r.period, r.rule)] if gross.loc[(r.period, r.rule)] > 0 else np.nan for r in top.itertuples()]
    top.to_csv(out / "leading-contributors.csv", index=False)
    young = pos[pos.address.eq(STRATWISE)].groupby(["period", "rule"]).agg(first_entry=("opened_at", "min"), positions=("position_id", "size"), pnl=("pnl", "sum")).reset_index()
    young.to_csv(out / "stratwise.csv", index=False)
    allocation = a.groupby(["period", "rule"]).agg(mean_positions=("positions", "mean"), mean_invested=("invested", "mean"), peak_weight=("max_weight", "max")).reset_index()
    allocation.to_csv(out / "allocation-summary.csv", index=False)
    from tradingstrategy.binance.price import fetch_binance_price

    refs = {symbol: fetch_binance_price(symbol=symbol)["close"] for symbol in ["BTCUSDT", "ETHUSDT"]}
    jumps = []
    for r in metrics.itertuples():
        eq = pd.read_parquet(out / f"curve-{r.period}-{r.rule}.parquet").equity.loc[r.start : r.end]
        ret = eq.pct_change().dropna()
        end = ret.idxmax()
        start = eq.index[eq.index.get_loc(end) - 1]
        item = dict(period=r.period, rule=r.rule, start=start, end=end, best_cycle=ret.max(), kurtosis=ret.kurt())
        for symbol, s in refs.items():
            s = s.copy()
            s.index = pd.DatetimeIndex(s.index).tz_localize(None) + pd.Timedelta("1d")
            item[symbol] = s.loc[:end].iloc[-1] / s.loc[:start].iloc[-1] - 1
        jumps.append(item)
    pd.DataFrame(jumps).to_csv(out / "best-cycle-market.csv", index=False)
    for period in ["hyper_ai", "full", "later"]:
        fig, ax = plt.subplots(figsize=(13, 5))
        for r in metrics[metrics.period.eq(period)].itertuples():
            eq = pd.read_parquet(out / f"curve-{period}-{r.rule}.parquet").equity.loc[r.start : r.end]
            ax.plot(eq.index, eq / eq.iloc[0], label=r.rule)
        ax.set_title(f"Monthly calibration: {period}")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(out / f"equity-{period}.png", dpi=130)
        plt.show()
    later = summary[(summary.cohort == "all") & (summary.split == "later")]
    figure, ax = plt.subplots(figsize=(11, 5))
    for h in [30, 60]:
        g = later[later.horizon == h]
        ax.scatter(g.lift_dd, g.top_ret, label=f"{h} days", alpha=0.65)
    ax.axvline(0, color="grey")
    ax.axhline(0, color="grey")
    ax.set_xlabel("Top-group minus rest future drawdown (higher is better)")
    ax.set_ylabel("Top-group future return")
    ax.legend()
    figure.tight_layout()
    figure.savefig(out / "calibration-tradeoff.png", dpi=130)
    plt.show()
    selected = summary[summary.config.isin(chosen.config) & summary.cohort.eq("all")][["config", "horizon", "split", "dates", "ic_return", "ic_drawdown", "top_ret", "lift_ret", "lift_dd", "lift_positive", "lift_negative_blocks", "top_coverage", "rest_coverage"]]
    cohort_table = summary[summary.config.eq(chosen.config.iloc[0]) & summary.split.eq("later")][["cohort", "horizon", "dates", "top_ret", "lift_dd", "lift_positive", "top_coverage", "rest_coverage"]]
    entry_features = pd.read_parquet(out / "panel.parquet")
    worst_entries = pos[pos.period.eq("later") & pos.rule.eq(chosen.config.iloc[0])].nsmallest(5, "pnl").copy()
    worst_entries["opened_at"] = pd.to_datetime(worst_entries.opened_at)
    worst_entries = worst_entries.merge(entry_features[entry_features.lookback.eq(int(chosen.lookback.iloc[0]))], left_on=["address", "opened_at"], right_on=["address", "date"], how="left")
    worst_entries = worst_entries[["name", "address", "opened_at", "pnl", "months", "provisional", "age", "p", "q", "gain", "downside", "curator_excluded", "quarantined_entry"]]
    worst_entries.to_csv(out / "largest-loss-entry-features.csv", index=False)
    display(chosen)
    display(selected)
    display(cohort_table)
    display(metrics)
    display(young)
    display(top)
    display(pd.DataFrame(jumps))
    lines = [f"{int(diagnostic.qualifies.sum())} of all 48 settings and {int(chosen.qualifies.sum())} of the three shortlisted settings pass the predeclared training criteria. Non-qualifying settings are diagnostic runs, not endorsed leads."]
    selected_saturation = saturation[saturation.config.isin(chosen.config)]
    if selected_saturation.fraction_dates_at_least_six.eq(1).all():
        lines.append("All three shortlisted settings have at least six score-1 vaults on every diagnostic date. The bounded gain reward and perfect positive-month fraction saturate the score: loss penalties cannot reorder those vaults. Deterministic tie-breaking, deposit availability and incumbent holding rules then choose among them. These are not three independent confirmations of a preferred coefficient balance.")
    equal_curves = []
    for period in ["hyper_ai", "full", "later"]:
        curves = [pd.read_parquet(out / f"curve-{period}-{c}.parquet").equity for c in chosen.config]
        if all(curves[0].equals(c) for c in curves[1:]):
            equal_curves.append(period)
    if equal_curves:
        lines.append("All three shortlisted equity curves are exactly identical in: " + ", ".join(equal_curves) + ". The experiment has not identified a uniquely useful penalty coefficient within this saturated region.")
    selections = pd.read_csv(out / "selection-log.csv")
    selected_scores = selections[selections.rule.isin(chosen.config)].score
    if np.isclose(selected_scores, 1, atol=1e-12, rtol=0).all():
        lines.append("Every selected vault in all three shortlisted strategies has score exactly 1. This is confirmed from actual engine selection logs, not inferred from the calibration pool. The shortlisted loss penalties are inactive at the selection boundary because these winners have no recorded negative months in their chosen history.")
    cohort60 = cohort_table[cohort_table.horizon.eq(60)].set_index("cohort")
    if {"young", "mature"} <= set(cohort60.index):
        lines.append(f"For the first shortlisted setting, separately ranked later-period mature-history top groups average {cohort60.loc['mature','top_ret']:.1%} over 60 days, versus {cohort60.loc['young','top_ret']:.1%} for young-history top groups. This motivates testing confidence in short histories; the cohort comparison does not isolate the provisional fallback or establish a causal age effect, and does not justify a long-history admission barrier.")
    original = metrics[(metrics.period == "later") & metrics.rule.eq(stress["config"])].iloc[0]
    excluded = metrics[(metrics.period == "later") & metrics.rule.eq(stress["config"] + "_leader_out")].iloc[0]
    lines.append(f"Removing the leading contributor from the first shortlisted later-period run changes CAGR from {original.cagr:.1%} to {excluded.cagr:.1%}, and Sharpe from {original.sharpe:.2f} to {excluded.sharpe:.2f}. This full re-simulation does not reveal a robust profitable portfolio.")
    eligible = metrics[(metrics.period == "later") & metrics.rule.isin(chosen.config) & metrics.cagr.ge(0.20)]
    if len(eligible):
        best = eligible.sort_values("sharpe", ascending=False).iloc[0]
        lines.append(f"Among shortlisted cold-start later runs above 20% CAGR, {best.rule} has the highest Sharpe: {best.sharpe:.2f}, CAGR {best.cagr:.1%}, drawdown {best.max_drawdown:.1%}. This is an exploratory later-period result on previously examined history.")
    else:
        lines.append("No shortlisted cold-start later-period portfolio reaches 20% CAGR. There is no qualifying strategy to promote from this experiment.")
    text = (
        """# Monthly stability calibration

Parent: [23-research-profitable-months.ipynb](23-research-profitable-months.ipynb), using its corrected single-fee accounting. Executed notebook: [24-research-monthly-calibration.ipynb](24-research-monthly-calibration.ipynb).

## Key new insights

"""
        + "\n\n".join(lines)
        + """

## Experiment design

Score = p^alpha × min(median_positive_month_return/tau, 1) × exp(−penalty × negative_month_fraction − severity × downside/tau). Downside is the sum of absolute negative monthly returns divided by available month count. Zero months contribute to the denominator. The 48 settings use alpha {1,2}, penalty {0,1,2}, severity {0,1}, tau {1%,2%}, and history {3,6 months}. No score parameter is chosen from portfolio backtest outcomes.

Completed calendar months only; missing inception history is omitted. With no complete month, unannualised observed partial return is used after two observations at least one day apart. Weekly observations work. This is a monthly consistency score, not an intramonth smoothness score.

Daily ranking diagnostics use historical TVL ≥ $7,500 and positive trailing 14-day return, falling back to available inception history for young vaults. This common gate is independent of the monthly score. Rankings are formed BEFORE future labels are masked. The top fifth is compared with the remaining vaults, ties resolved deterministically by address. Execution additionally checks the inherited deposit availability/capacity rules; the diagnostic pool is not an exact executed-portfolio reconstruction.

Outcomes: future 30/60-day return, positive-return frequency, observed-path maximum drawdown, negative endpoint return, and fraction of negative non-overlapping 30-day blocks (monthly proxies, not calendar months). Endpoints use earlier marks with up to seven days of carry for sparse observations. Incomplete or missing future outcomes are not zero-filled; coverage is exported. Young (<90 days of observed history) and mature cohorts are separately reported. The five-labelled-vault threshold applies to cross-sectional statistics, not vault admission.

Training decision labels must fully mature by 1 April 2026. Later diagnostics start on 1 April; intervening overlapping labels are embargoed. Three settings are selected by training-only worst-horizon drawdown lift and the median lift of one-parameter neighbours. Qualification requires positive top-group return, nonnegative positive-return lift and positive drawdown lift at BOTH horizons, plus positive neighbourhood median drawdown lift. If fewer than three qualify, remaining backtests are clearly diagnostic. No minimum-history admission requirement is introduced.

Matched portfolio arms all use six positions, equal weighting, 33% portfolio cap, 33% historical vault-TVL capacity, the same young-compatible recent-return gate, cash policy, fees and trade thresholds. Only ranking varies: original CAGR/Sortino versus the three shortlisted monthly scores. Zero-score candidates are not given an extra exclusion; the common recent-return gate handles eligibility. Equal weighting avoids the inherited 90-day inverse-volatility sizing barrier. These fixed limits isolate ranking; they are not a proposed production allocation policy. Separate original inverse-variance anchors reproduce corrected NB23 exactly in both native periods.

Three portfolio periods: Hyper-ai, full-history and a cold start on 1 April through 8 September. The first two are historical diagnostics because the shortlist was trained on part of those dates. The cold-start later run uses no pre-April holdings. All dates have been researched previously: no untouched holdout or statistical discovery claim is made.

## Summary of results

### Training-only shortlist

"""
        + chosen.round(5).to_markdown(index=False)
        + """

### Score saturation

"""
        + selected_saturation.round(4).to_markdown(index=False)
        + """

These diagnostic opportunity sets precede execution checks. Score ties are resolved by address in the ranking analysis and by pair id in the inherited engine. Neither tie-break is evidence of trading quality.

### Future-outcome evidence

"""
        + selected.round(5).to_markdown(index=False)
        + """

Daily labels overlap strongly; date counts are not independent sample counts. No p-values or annualised claims are inferred from these label averages. Values above are fractions, not percentages.

### Young versus mature observed histories

"""
        + cohort_table.round(5).to_markdown(index=False)
        + """

These are independently ranked cohorts for the first training-shortlisted setting. They are descriptive comparisons, not an age treatment or justification for excluding young vaults. Different date counts are shown. Available history below one completed month can receive a perfect score after a small gain, despite much less evidence of persistence.

### One-parameter changes across the grid

"""
        + effects[effects.split.eq("later")].round(5).to_markdown(index=False)
        + """

Each row averages matched parameter pairs with all other parameters held fixed. Positive drawdown lift means shallower future drawdown relative to the rest of the pool; it is not portfolio Sharpe. These later-period diagnostics did not choose the shortlist. Tau changes both profit saturation and the scale of the downside penalty, so its effect cannot be attributed solely to the profit cap. Small differences are not established significant effects.

### Portfolio metrics

"""
        + metrics[["period", "rule", "cagr", "sharpe", "weekly_sharpe", "max_drawdown", "start", "end"]].round(4).to_markdown(index=False)
        + """

### Actual StratWise positions

"""
        + (young.round(3).to_markdown(index=False) if len(young) else "No executed StratWise positions.")
        + """

## Robustness of results

Both corrected NB23 anchors must reproduce to absolute equity tolerance 1e-7. Every executed redemption is checked for single-fee pricing. Source/data signatures guard the feature cache. The same frozen universe and blacklists-off setting are used throughout; inherited current-metadata universe filtering remains a limitation.

Neighbour comparisons and young-vault tables cover all 48 settings, including failed settings. Stable-looking monthly outcomes do not prove intramonth safety. The best positive-profit contributor is removed from the FIRST training-shortlisted setting in a complete cold-start later-period re-simulation; this stress is diagnostic, not another selection criterion. Portfolio outcomes and rankings for the remaining shortlisted settings are retained even if they look worse.

### Leading contributors

"""
        + top.round(4).to_markdown(index=False)
        + """

### Largest cycles versus BTC and ETH

"""
        + pd.DataFrame(jumps).round(4).to_markdown(index=False)
        + """

### Largest losing positions and their entry histories

"""
        + worst_entries.round(4).to_markdown(index=False)
        + """

These are individual position P&Ls for the first training-shortlisted later-period run. Perfect positive-month histories and zero downside penalties can precede severe losses. A large positive median month saturates the same reward as modest steady gains; a cap removes extra reward but does not distinguish their risk. Provisional short-history gains can saturate it too. This is an observed failure mode of the score, not evidence that a different loss-penalty coefficient would have prevented those entries.

Curator flags and quarantine-at-entry checks are saved in `position-audit.csv`. P&L and allocation averages cover each native run, whereas full-history headline metrics begin 13 September 2025. The $750 trim threshold and 0.5% minimum position weight remain fixed and can cause realised weights to differ from targets. Higher returns alone are not evidence of steady-vault selection.
"""
    )
    (ns["PROJECT"] / "monthly-calibration-summary-01.md").write_text(text)
    (out / "heading-results.md").write_text(text)
    return text
