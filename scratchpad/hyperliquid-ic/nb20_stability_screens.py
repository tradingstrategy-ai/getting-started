"""Causal fixed screens and reporting for the NB20 portfolio experiment."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from tqdm_loggable.auto import tqdm

STRAT = "0x0ff219ac20596b457558341bc410bc7a08a1394c"


def make_screens(project, addresses):
    from nb19_entry_forensics import load, metrics

    _, prices, _, _, _ = load(project)
    frames = []
    for address in tqdm(sorted(addresses), desc="Causal screen features (estimated under one minute)"):
        s = prices.get(address)
        if s is None or s.empty:
            continue
        grid = pd.date_range(s.index.min().floor("D"), "2026-09-12", freq="D")
        p = s.reindex(grid, method="ffill")
        r = np.log(p).diff()
        gain = r.clip(lower=0)
        residual = np.expm1(r.rolling(30).sum() - gain.rolling(30).apply(lambda v: np.partition(v, -2)[-2:].sum(), raw=True))
        drawdown = p.rolling(31).apply(lambda v: np.min(v / np.maximum.accumulate(v) - 1), raw=True)
        weeks = pd.concat([p.shift(7 * j) / p.shift(7 * (j + 1)) - 1 for j in range(4)], axis=1)
        weeks.columns = range(4)
        worst = weeks.min(axis=1).where(weeks.notna().all(axis=1))
        weekly_residual = np.expm1(np.log1p(weeks).sum(axis=1) - np.log1p(weeks).max(axis=1).clip(lower=0)).where(weeks.notna().all(axis=1))
        weekly_marks = pd.concat([p.shift(7 * j) for j in reversed(range(5))], axis=1)
        weekly_dd = (weekly_marks / weekly_marks.cummax(axis=1) - 1).min(axis=1).where(weekly_marks.notna().all(axis=1))
        d = pd.DataFrame({"daily_residual": residual, "daily_drawdown": drawdown, "worst_week": worst, "weekly_residual": weekly_residual, "weekly_drawdown": weekly_dd})
        d.index = d.index + pd.Timedelta(days=1)
        d["date"] = d.index
        d["address"] = address
        d["daily_known"] = d[["daily_residual", "daily_drawdown", "worst_week"]].notna().all(axis=1)
        d["weekly_known"] = d[["weekly_residual", "weekly_drawdown", "worst_week"]].notna().all(axis=1)
        d["daily_pass"] = ~d.daily_known | (d.daily_residual.gt(0) & d.daily_drawdown.ge(-0.05) & d.worst_week.ge(-0.03))
        d["weekly_pass"] = ~d.weekly_known | (d.weekly_residual.gt(0) & d.weekly_drawdown.ge(-0.05) & d.worst_week.ge(-0.03))
        frames.append(d.reset_index(drop=True))
    frame = pd.concat(frames, ignore_index=True)
    # Independent scalar NB19 implementation checks matching pre-entry windows and time alignment.
    checks = []
    for a in sorted(addresses & set(prices))[:: max(1, len(addresses) // 10)] + [STRAT]:
        for date in [pd.Timestamp("2026-06-04"), pd.Timestamp("2026-09-04")]:
            scalar = metrics(prices[a], date, 30)
            if not scalar["available"]:
                continue
            row = frame[(frame.address == a) & (frame.date == date)].iloc[0]
            for col, ref in [("daily_residual", "return_without_best2"), ("daily_drawdown", "max_drawdown"), ("worst_week", "worst_week"), ("weekly_residual", "weekly_return_without_best"), ("weekly_drawdown", "weekly_drawdown")]:
                assert np.isclose(row[col], scalar[ref], atol=1e-10), (a, date, col, row[col], scalar[ref])
                checks.append({"address": a, "date": date, "metric": col, "error": row[col] - scalar[ref]})
    return frame, pd.DataFrame(checks)


def curve_metrics(eq):
    r = eq.pct_change().dropna()
    days = (eq.index[-1] - eq.index[0]).days
    weekly = eq.resample("W-SUN").last().pct_change().dropna()
    return {"cagr": (eq.iloc[-1] / eq.iloc[0]) ** (365 / days) - 1, "sharpe": r.mean() / r.std() * np.sqrt(365 / 2) if r.std() > 0 else np.nan, "weekly_sharpe": weekly.mean() / weekly.std() * np.sqrt(52) if weekly.std() > 0 else np.nan, "volatility": r.std() * np.sqrt(365 / 2), "max_drawdown": (eq / eq.cummax() - 1).min(), "best_cycle": r.max(), "kurtosis": r.kurt(), "start": str(eq.index[0].date()), "end": str(eq.index[-1].date())}


def report(project):
    out = project / "_artifacts-stability-screens"
    names = ["anchor", "measured_8", "inverse_vol_q10", "floor15", "floor20", "A0b"]
    rows = []
    for period in ["hyper_ai", "full"]:
        start = pd.Timestamp("2026-01-01" if period == "hyper_ai" else "2025-09-13")
        end = pd.Timestamp("2026-07-08" if period == "hyper_ai" else "2026-09-08")
        control = pd.read_parquet(out / f"curve-{period}-anchor-none.parquet").equity
        dates = control.index[(control.index >= start) & (control.index <= end)]
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        for name, ax in zip(names, axes.ravel()):
            for screen in ["none", "daily", "weekly"]:
                eq = pd.read_parquet(out / f"curve-{period}-{name}-{screen}.parquet").equity
                eq = eq.reindex(eq.index.union(dates)).sort_index().ffill().reindex(dates)
                assert eq.notna().all()
                rows.append({"period": period, "candidate": name, "screen": screen, **curve_metrics(eq)})
                ax.plot(eq.index, eq / eq.iloc[0], label=screen)
            ax.set_title(name)
            ax.legend()
            ax.grid(alpha=0.2)
        fig.suptitle(f"{period}: same-date equity curves, blacklists off")
        fig.tight_layout()
        fig.savefig(out / f"equity-{period}.png", dpi=140)
        plt.show()
    results = pd.DataFrame(rows)
    results.to_csv(out / "matched-metrics.csv", index=False)
    baseline = results[results.screen.eq("none")]
    delta = results[results.screen.ne("none")].merge(baseline, on=["period", "candidate"], suffixes=("", "_baseline"))
    for col in ["cagr", "sharpe", "max_drawdown"]:
        delta[col + "_change"] = delta[col] - delta[col + "_baseline"]
    delta.to_csv(out / "screen-effect.csv", index=False)
    display(delta[["period", "candidate", "screen", "cagr", "cagr_change", "sharpe", "sharpe_change", "max_drawdown"]])
    pos = pd.read_csv(out / "positions.csv")
    tr = pd.read_csv(out / "trades.csv")
    cycles = pd.read_csv(out / "cycle-diagnostics.csv")
    coverage = pd.read_csv(out / "screen-decisions.csv")
    # Reconstruct A0b screen admission without deleting any mark rows.
    ff = pd.read_parquet(project / "_artifacts-rewrite/features.parquet")
    sf = pd.read_parquet(out / "screen-features.parquet")
    ff.date = pd.to_datetime(ff.date).dt.normalize()
    ff.address = ff.address.str.lower()
    ff = ff[ff.address.isin(sf.address.unique())]
    extra = []
    for period in ["hyper_ai", "full"]:
        for screen in ["none", "daily", "weekly"]:
            tr_a = pd.read_parquet(out / f"a0b-trades-{period}-{screen}.parquet")
            cand = ff[ff.date.isin(pd.to_datetime(tr_a.date)) & ff.incumbent_return_gate.gt(-0.16)][["date", "address"]].copy()
            if screen == "none":
                cand["known"] = False
                cand["passed"] = True
            else:
                cand = cand.merge(sf[["date", "address", screen + "_known", screen + "_pass"]], on=["date", "address"], how="left", validate="one_to_one")
                cand["known"] = cand[screen + "_known"].eq(True)
                cand["passed"] = ~cand[screen + "_pass"].eq(False)
            cand["period"] = period
            cand["candidate"] = "A0b"
            cand["screen"] = screen
            extra.append(cand[["date", "address", "known", "passed", "period", "candidate", "screen"]])
    coverage = pd.concat([coverage] + extra, ignore_index=True)
    coverage.to_csv(out / "all-screen-decisions.csv", index=False)
    coverage_summary = coverage.groupby(["period", "candidate", "screen"]).agg(evaluations=("address", "size"), known=("known", "sum"), rejected=("passed", lambda s: (~s).sum())).reset_index()
    coverage_summary.to_csv(out / "screen-coverage.csv", index=False)
    cycles["date"] = pd.to_datetime(cycles.date)
    cycles = cycles[(cycles.period.eq("hyper_ai") & cycles.date.between("2026-01-01", "2026-07-08")) | (cycles.period.eq("full") & cycles.date.between("2025-09-13", "2026-09-08"))]
    deploy = cycles.groupby(["period", "candidate", "screen"]).agg(mean_invested_fraction=("invested_fraction", "mean"), mean_positions=("positions", "mean")).reset_index()
    deploy.to_csv(out / "deployment.csv", index=False)
    display(deploy)
    attr = pos.groupby(["period", "candidate", "screen", "address", "name"], dropna=False).agg(pnl=("pnl", "sum"), positions=("position_id", "size")).reset_index()
    attr.to_csv(out / "vault-attribution.csv", index=False)
    positive = attr.assign(positive=attr.pnl.clip(lower=0)).groupby(["period", "candidate", "screen"]).positive.sum()
    top = attr.sort_values("pnl", ascending=False).groupby(["period", "candidate", "screen"]).head(1).copy()
    top["positive_pnl_share"] = [r.pnl / positive.loc[(r.period, r.candidate, r.screen)] if positive.loc[(r.period, r.candidate, r.screen)] > 0 else np.nan for r in top.itertuples()]
    top.to_csv(out / "largest-contributors.csv", index=False)
    display(top)
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, QUARANTINE_PERIODS

    pos["curator_excluded"] = pos.address.isin(EXCLUDED_VAULTS)
    pos["quarantined_at_entry"] = [any(a == r.address and pd.Timestamp(lo) <= pd.Timestamp(r.opened_at) <= pd.Timestamp(hi) for a, lo, hi, _ in QUARANTINE_PERIODS) for r in pos.itertuples()]
    pos.to_csv(out / "position-risk-audit.csv", index=False)
    # Keep input quality failures separate from real strategy drawdowns.
    keys = ["period", "candidate", "screen", "position_id"]
    tr["funded"] = tr.value.abs().where(tr.quantity.gt(0), 0)
    tr["returned"] = tr.value.abs().where(tr.quantity.lt(0), 0)
    flow = tr.groupby(keys).agg(funded=("funded", "sum"), returned=("returned", "sum")).reset_index().merge(pos[keys + ["closed_at", "address"]], on=keys)
    flow["closed_without_return"] = flow.closed_at.notna() & flow.funded.gt(100) & flow.returned.lt(1)
    flow.to_csv(out / "capital-audit.csv", index=False)
    from tradingstrategy.binance.price import fetch_binance_price

    refs = {symbol: fetch_binance_price(symbol=symbol)["close"] for symbol in ["BTCUSDT", "ETHUSDT"]}
    events = []
    for r in results[results.candidate.ne("A0b")].itertuples():
        eq = pd.read_parquet(out / f"curve-{r.period}-{r.candidate}-{r.screen}.parquet").equity
        rr = eq.pct_change().dropna()
        end = rr.idxmax()
        start = eq.index[eq.index.get_loc(end) - 1]
        item = {"period": r.period, "candidate": r.candidate, "screen": r.screen, "start": start, "end": end, "best_native_cycle": rr.max()}
        for symbol, s in refs.items():
            s = s.copy()
            s.index = pd.DatetimeIndex(s.index).tz_localize(None) + pd.Timedelta(days=1)
            x = s.loc[:start]
            y = s.loc[:end]
            item[symbol] = y.iloc[-1] / x.iloc[-1] - 1 if len(x) and len(y) else np.nan
        events.append(item)
    events = pd.DataFrame(events)
    events.to_csv(out / "best-cycle-market.csv", index=False)
    display(events)
    strat = coverage[coverage.address.eq(STRAT)].copy()
    strat.to_csv(out / "stratwise-screen-decisions.csv", index=False)
    strat_positions = pos[pos.address.eq(STRAT)]
    strat_positions.to_csv(out / "stratwise-positions.csv", index=False)
    strat_a0 = []
    for period in ["hyper_ai", "full"]:
        for screen in ["none", "daily", "weekly"]:
            pool = pd.read_parquet(out / f"a0b-pool-{period}-{screen}.parquet")
            pool = pool[pool.address.eq(STRAT)].copy()
            pool["period"] = period
            pool["screen"] = screen
            strat_a0.append(pool)
    pd.concat(strat_a0, ignore_index=True).to_csv(out / "stratwise-a0b-pool.csv", index=False)
    turnover = tr.groupby(["period", "candidate", "screen"]).agg(executed_trades=("value", "size"), gross_executed_value=("value", lambda s: s.abs().sum())).reset_index()
    turnover["gross_turnover_initial_capital"] = turnover.gross_executed_value / 150_000
    turnover.to_csv(out / "turnover.csv", index=False)
    comparison = attr.pivot_table(index=["period", "candidate", "address", "name"], columns="screen", values="pnl", aggfunc="sum").fillna(0).reset_index()
    for screen in ["daily", "weekly"]:
        comparison[screen + "_pnl_change"] = comparison[screen] - comparison["none"]
    comparison.to_csv(out / "contribution-changes.csv", index=False)
    full = delta[delta.period.eq("full")]
    improved = int(full.sharpe_change.gt(0).sum())
    useful = results[results.period.eq("full") & results.screen.ne("none")].sort_values("sharpe", ascending=False).iloc[0]
    losses = comparison[(comparison.period == "full") & (comparison.candidate == "anchor")].sort_values("weekly_pnl_change").head(6)
    changes_text = losses[["name", "none", "weekly", "weekly_pnl_change"]].to_markdown(index=False)
    strat_summary = coverage[coverage.address.eq(STRAT)].groupby(["period", "candidate", "screen"]).agg(evaluations=("passed", "size"), passed=("passed", "sum"), known=("known", "sum")).reset_index()
    strat_summary.to_csv(out / "stratwise-summary.csv", index=False)
    best = results[results.period.eq("full")].sort_values("sharpe", ascending=False).iloc[0]
    table = results[["period", "candidate", "screen", "cagr", "sharpe", "max_drawdown"]].copy()
    for c in ["cagr", "max_drawdown"]:
        table[c] = table[c].map(lambda x: f"{x:.1%}")
    table.sharpe = table.sharpe.map(lambda x: f"{x:.2f}")
    findings = f"""# Portfolio effects of the StratWise-inspired stability screens

Based on `18-research-leads-no-blacklists.ipynb` and `19-research-stratwise-entry-forensics.ipynb`.

## Key new insights and what did we learn?

The strongest full-common-period Sharpe is {best.candidate} / {best.screen}: {best.cagr:.1%} CAGR, {best.sharpe:.2f} two-day Sharpe, {best.max_drawdown:.1%} maximum drawdown. This experiment tests portfolio outcomes, not just rejecting known losing vaults.

Of 12 screened-versus-control comparisons on the full common period, {improved} improve Sharpe. The best screened full-period Sharpe is {useful.candidate}/{useful.screen}: {useful.cagr:.1%} CAGR and {useful.sharpe:.2f} Sharpe. These fixed thresholds should be judged by those results, not by the fraction of retrospectively bad entries they exclude.

## Summary of results

{table.to_markdown(index=False)}

Dates are 1 January–8 July 2026 and 13 September 2025–8 September 2026. Native engine full runs begin 1 August 2025; the common full table slices an already-running portfolio. All screens retain the source fees, sizing, forward filling and execution conventions. Independent A0b is not fee/accounting-identical to the engine.

Thirty engine runs and six independent A0b runs compare unchanged, daily and weekly screens across anchor, measured_8, inverse_vol_q10, floor15 and floor20 (A0b receives both screens directly). Blacklists are disabled throughout, matching NB18 off controls. No blacklists-on screened experiment is claimed. Exact source-control parity is saved separately.

Daily screen: prior 30-day return remains positive after deleting the two best daily log gains; trailing maximum drawdown at most 5%; worst of four completed non-overlapping weeks at least -3%. Weekly screen uses four completed weeks, deletes the best week's log gain and measures drawdown on weekly marks, retaining the -3% worst-week bound. Both screen existing holdings as well as new purchases. Thresholds are fixed from NB19, not searched here.

Missing screen history is UNKNOWN and passes through the existing selection rules, rather than creating a new age barrier. The weekly screen becomes measurable after 28 days; daily needs 30 days, both ending at the previous midnight. Existing incumbent score/sizing history requirements are unchanged. Passing the screen is not a promise of selection or allocation for young vaults. See screen-coverage.csv and stratwise-screen-decisions.csv. These include engine and A0b candidate evaluations; A0b actual selections and target dollars are separately saved in stratwise-a0b-pool.csv.

Mean invested fraction and position counts over the same common periods:

{deploy.to_markdown(index=False)}

## What changed in the portfolio?

Largest adverse changes in full-period anchor per-vault contributions under the weekly screen (native engine period, dollars):

{changes_text}

These include changed entry/exit timing and capital allocation, not simply omitted trades. Replacement positions can lose even if a screen removes some previously losing vaults. The measured_8 filter still removes eight measured high-volatility names AFTER the new screen, so the filters can leave very few investable candidates. Portfolio cash is an outcome of the experiment, not a matched-volatility control. Gross executed turnover is exported separately to expose additional churn.

StratWise passing these new rules does not fix the inherited incumbent's long-history ranking and sizing: its 360-day composite cannot yet be complete and its 90-day inverse-volatility estimate is unavailable on this sample. The engine inverse-variance sizing gives a missing estimate zero raw weight. This experiment intentionally measures the rules as overlays; it does not implement a separate young-vault allocation policy. Check the actual position and pool ledgers before claiming that any strategy now buys StratWise.

## Robustness of results

Inputs are hash-checked against NB18 and the vectorised daily/weekly feature calculations are checked against the independent scalar NB19 implementation. All marks are causal as-of marks; nothing is backfilled. Weekly screens mitigate reporting-cadence differences but cannot reveal losses between sparse observations. These are retrospective in-sample tests of thresholds motivated by known vault histories.

Deployment and number of positions are reported: reduced volatility can reflect more cash. There is no matched-exposure causal decomposition. Largest contributor shares, full position P&L, trades, curator flags and best-cycle BTC/ETH returns are exported. There are {int(flow.closed_without_return.sum())} closed positions funded above $100 with less than $1 returned in executed trade value. Large positive-P&L shares do not establish leave-one-vault-out results. Current source exclusions are disabled locally; upstream removed data cannot be recovered.

StratWise has {len(strat_positions)} engine positions across the separate runs; these are not independent observations. Screen logs count candidate evaluations after the incumbent return gate, not the complete source universe. Engine deployment is marked before each decision; A0b deployment uses its saved post-decision equity rows. The same two-day clock is used for comparative Sharpe, with weekly Sharpe also exported.
"""
    (project / "stability-screens-summary-01.md").write_text(findings)
    (out / "heading-results.md").write_text(findings)
    return results, delta
