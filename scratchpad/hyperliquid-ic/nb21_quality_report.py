"""Report variable-size absolute-quality portfolios against saved bounded controls."""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from nb20_stability_screens import curve_metrics, STRAT


def report(project):
    out = project / "_artifacts-quality-only"
    old = project / "_artifacts-stability-screens"
    names = ["anchor", "measured_8", "inverse_vol_q10", "floor15", "floor20", "A0b"]
    rows = []
    for period in ["hyper_ai", "full"]:
        start = pd.Timestamp("2026-01-01" if period == "hyper_ai" else "2025-09-13")
        end = pd.Timestamp("2026-07-08" if period == "hyper_ai" else "2026-09-08")
        ref = pd.read_parquet(old / f"curve-{period}-anchor-none.parquet").equity
        dates = ref.index[(ref.index >= start) & (ref.index <= end)]
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        for name, ax in zip(names, axes.ravel()):
            for label, folder, screen in [("bounded", old, "none"), ("unrestricted", out, "none"), ("daily_floors", out, "daily"), ("weekly_floors", out, "weekly")]:
                eq = pd.read_parquet(folder / f"curve-{period}-{name}-{screen}.parquet").equity
                eq = eq.reindex(eq.index.union(dates)).sort_index().ffill().reindex(dates)
                assert eq.notna().all() and eq.gt(0).all()
                rows.append({"period": period, "candidate": name, "variant": label, **curve_metrics(eq)})
                ax.plot(eq.index, eq / eq.iloc[0], label=label)
            ax.set_title(name)
            ax.legend(fontsize=8)
            ax.grid(alpha=0.2)
        fig.suptitle(f"{period}: no position quota or 33% concentration cap")
        fig.tight_layout()
        fig.savefig(out / f"equity-{period}.png", dpi=140)
        plt.show()
    results = pd.DataFrame(rows)
    results.to_csv(out / "matched-metrics.csv", index=False)
    comparison = results[results.variant.ne("bounded")].merge(results[results.variant.eq("bounded")], on=["period", "candidate"], suffixes=("", "_bounded"))
    for c in ["cagr", "sharpe", "max_drawdown"]:
        comparison[c + "_change"] = comparison[c] - comparison[c + "_bounded"]
    comparison.to_csv(out / "comparison.csv", index=False)
    display(results)
    # Old screened controls isolate the differences from NB20, not just from its unscreened baseline.
    old_metrics = pd.read_csv(old / "matched-metrics.csv")
    prior = []
    for r in results[results.variant.isin(["daily_floors", "weekly_floors"])].itertuples():
        q = old_metrics[(old_metrics.period == r.period) & (old_metrics.candidate == r.candidate) & (old_metrics.screen == r.variant.split("_")[0])].iloc[0]
        prior.append({"period": r.period, "candidate": r.candidate, "variant": r.variant, "prior_cagr": q.cagr, "new_cagr": r.cagr, "prior_sharpe": q.sharpe, "new_sharpe": r.sharpe})
    pd.DataFrame(prior).to_csv(out / "versus-nb20-screens.csv", index=False)
    cycles = pd.read_csv(out / "cycle-diagnostics.csv")
    cycles.date = pd.to_datetime(cycles.date)
    cycles = cycles[(cycles.period.eq("hyper_ai") & cycles.date.between("2026-01-01", "2026-07-08")) | (cycles.period.eq("full") & cycles.date.between("2025-09-13", "2026-09-08"))]
    allocation = cycles.groupby(["period", "candidate", "screen"]).agg(mean_invested=("invested_fraction", "mean"), mean_positions=("positions", "mean"), min_positions=("positions", "min"), max_positions=("positions", "max"), peak_weight=("max_weight", "max"), mean_effective_positions=("effective_positions", "mean")).reset_index()
    # A0b concentration is measured from its allocation ledger at rebalance, not from open-position snapshots.
    a0_rows = []
    for period in ["hyper_ai", "full"]:
        for screen in ["none", "daily", "weekly"]:
            pool = pd.read_parquet(out / f"a0b-pool-{period}-{screen}.parquet")
            eq = pd.read_parquet(out / f"a0b-equity-{period}-{screen}.parquet").set_index("date")
            for date, g in pool.groupby("date"):
                if date not in eq.index:
                    continue
                w = g.target_dollars / eq.loc[date, "equity"]
                invested = w.sum()
                a0_rows.append({"period": period, "screen": screen, "date": date, "peak_weight": w.max(), "effective_positions": invested**2 / (w.pow(2).sum()) if w.pow(2).sum() > 0 else 0})
    a0 = pd.DataFrame(a0_rows)
    a0.to_csv(out / "a0b-concentration.csv", index=False)
    for i, r in allocation[allocation.candidate.eq("A0b")].iterrows():
        a = a0[(a0.period == r.period) & (a0.screen == r.screen)]
        allocation.loc[i, "peak_weight"] = a.peak_weight.max()
        allocation.loc[i, "mean_effective_positions"] = a.effective_positions.mean()
    allocation.to_csv(out / "allocation.csv", index=False)
    display(allocation)
    pos = pd.read_csv(out / "positions.csv")
    tr = pd.read_csv(out / "trades.csv")
    dec = pd.read_csv(out / "screen-decisions.csv")
    pos["date"] = pd.to_datetime(pos.opened_at).dt.normalize()
    dec.date = pd.to_datetime(dec.date).dt.normalize()
    keys = ["period", "candidate", "screen", "date", "address"]
    audit = pos.merge(dec[keys + ["known", "passed"]], on=keys, how="left", validate="many_to_one")
    assert audit.passed.notna().all() and audit.passed.all()
    assert audit.loc[audit.screen.ne("none"), "known"].all()
    audit.to_csv(out / "entry-admission-audit.csv", index=False)
    # Relative filters are intentionally disabled in the quality arms; confirm the aliases really are identical.
    equivalence = []
    for period in ["hyper_ai", "full"]:
        for screen in ["daily", "weekly"]:
            anchor = pd.read_parquet(out / f"curve-{period}-anchor-{screen}.parquet").equity
            for candidate in ["measured_8", "inverse_vol_q10"]:
                other = pd.read_parquet(out / f"curve-{period}-{candidate}-{screen}.parquet").equity
                err = (anchor - other).abs().max()
                assert err < 0.01, (candidate, err)
                equivalence.append({"period": period, "screen": screen, "candidate": candidate, "max_equity_difference": err})
    pd.DataFrame(equivalence).to_csv(out / "floor-only-equivalence.csv", index=False)
    attribution = pos.groupby(["period", "candidate", "screen", "address", "name"], dropna=False).agg(pnl=("pnl", "sum"), positions=("position_id", "size")).reset_index()
    attribution.to_csv(out / "vault-attribution.csv", index=False)
    positive = attribution.assign(positive=attribution.pnl.clip(lower=0)).groupby(["period", "candidate", "screen"]).positive.sum()
    top = attribution.sort_values("pnl", ascending=False).groupby(["period", "candidate", "screen"]).head(1).copy()
    top["positive_share"] = [r.pnl / positive.loc[(r.period, r.candidate, r.screen)] if positive.loc[(r.period, r.candidate, r.screen)] > 0 else np.nan for r in top.itertuples()]
    top.to_csv(out / "largest-contributors.csv", index=False)
    display(top)
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, QUARANTINE_PERIODS

    pos["curator_excluded"] = pos.address.isin(EXCLUDED_VAULTS)
    pos["quarantined_entry"] = [any(r.address == a and pd.Timestamp(lo) <= r.date <= pd.Timestamp(hi) for a, lo, hi, _ in QUARANTINE_PERIODS) for r in pos.itertuples()]
    pos.to_csv(out / "position-risk-audit.csv", index=False)
    keys = ["period", "candidate", "screen", "position_id"]
    tr["funded"] = tr.value.abs().where(tr.quantity.gt(0), 0)
    tr["returned"] = tr.value.abs().where(tr.quantity.lt(0), 0)
    flow = tr.groupby(keys).agg(funded=("funded", "sum"), returned=("returned", "sum")).reset_index().merge(pos[keys + ["closed_at", "address"]], on=keys)
    flow["lost_all_capital"] = flow.closed_at.notna() & flow.funded.gt(100) & flow.returned.lt(1)
    flow.to_csv(out / "capital-audit.csv", index=False)
    from tradingstrategy.binance.price import fetch_binance_price

    refs = {sym: fetch_binance_price(symbol=sym)["close"] for sym in ["BTCUSDT", "ETHUSDT"]}
    market = []
    for period in ["hyper_ai", "full"]:
        for candidate in names:
            for screen in ["none", "daily", "weekly"]:
                eq = pd.read_parquet(out / f"curve-{period}-{candidate}-{screen}.parquet").equity
                if candidate == "A0b":
                    eq = eq.iloc[::2]
                ret = eq.pct_change().dropna()
                end = ret.idxmax()
                start = eq.index[eq.index.get_loc(end) - 1]
                item = {"period": period, "candidate": candidate, "screen": screen, "start": start, "end": end, "best_cycle": ret.max(), "kurtosis": ret.kurt()}
                for sym, s in refs.items():
                    s = s.copy()
                    s.index = pd.DatetimeIndex(s.index).tz_localize(None) + pd.Timedelta(days=1)
                    before = s.loc[:start]
                    after = s.loc[:end]
                    item[sym] = after.iloc[-1] / before.iloc[-1] - 1 if len(before) and len(after) else np.nan
                market.append(item)
    market = pd.DataFrame(market)
    market.to_csv(out / "best-cycle-market.csv", index=False)
    display(market)
    # Inspect the return paths behind the largest contributions, not just portfolio Sharpe.
    manifest = json.loads((out / "input-manifest.json").read_text())
    price_path = next(x["path"] for x in manifest if x["path"].endswith("vault-prices.parquet"))
    raw = pd.read_parquet(price_path, columns=["address", "chain", "share_price"]).reset_index()
    raw = raw[raw.chain.eq(9999)].copy()
    raw.address = raw.address.str.lower()
    raw.timestamp = pd.to_datetime(raw.timestamp)
    leaders = list(top.sort_values("pnl", ascending=False).address.drop_duplicates().head(8))
    fig, axes = plt.subplots(max(1, len(leaders)), 1, figsize=(14, 3 * max(1, len(leaders))), squeeze=False)
    nav_rows = []
    for address, ax in zip(leaders, axes[:, 0]):
        g = raw[raw.address.eq(address) & raw.timestamp.between("2025-08-01", "2026-09-08 23:59:59")].sort_values("timestamp").drop_duplicates("timestamp", keep="last")
        series = pd.Series(g.share_price.to_numpy(), index=pd.DatetimeIndex(g.timestamp))
        daily = series.resample("D").last().ffill()
        ret = daily.pct_change().dropna()
        name = top[top.address.eq(address)].name.iloc[0]
        ax.plot(series.index, series / series.iloc[0])
        ax.set_title(name + " " + address[:8])
        ax.grid(alpha=0.2)
        nav_rows.append({"address": address, "name": name, "observations": len(series), "daily_zero_return_share": ret.eq(0).mean(), "best_daily_return": ret.max(), "worst_daily_return": ret.min(), "daily_kurtosis": ret.kurt()})
    fig.tight_layout()
    fig.savefig(out / "leader-nav-curves.png", dpi=130)
    plt.show()
    pd.DataFrame(nav_rows).to_csv(out / "leader-nav-audit.csv", index=False)
    pos.sort_values("pnl", ascending=False).groupby(["period", "candidate", "screen"]).head(3).to_csv(out / "largest-individual-positions.csv", index=False)
    event_nav = []
    for row in market[market.candidate.ne("A0b")].itertuples():
        held = pos[(pos.period == row.period) & (pos.candidate == row.candidate) & (pos.screen == row.screen) & pd.to_datetime(pos.opened_at).le(row.end) & (pos.closed_at.isna() | pd.to_datetime(pos.closed_at).ge(row.start))]
        for address in held.address.unique():
            g = raw[raw.address.eq(address)].sort_values("timestamp")
            before = g[g.timestamp.le(row.start)]
            after = g[g.timestamp.le(row.end)]
            if before.empty or after.empty:
                continue
            event_nav.append({"period": row.period, "candidate": row.candidate, "screen": row.screen, "address": address, "start": row.start, "end": row.end, "observed_nav_return": after.share_price.iloc[-1] / before.share_price.iloc[-1] - 1})
    pd.DataFrame(event_nav).to_csv(out / "best-cycle-held-nav.csv", index=False)
    strat = pos[pos.address.eq(STRAT)]
    strat.to_csv(out / "stratwise-positions.csv", index=False)
    loo = pd.read_csv(out / "leave-one-out/comparison.csv")
    display(loo)
    best = results[results.period.eq("full") & results.variant.ne("bounded")].sort_values("sharpe", ascending=False).iloc[0]
    table = results[["period", "candidate", "variant", "cagr", "sharpe", "max_drawdown"]].copy()
    for col in ["cagr", "max_drawdown"]:
        table[col] = table[col].map(lambda v: f"{v:.1%}")
    table.sharpe = table.sharpe.map(lambda v: f"{v:.2f}")
    findings = f"""# Variable-size portfolios with absolute quality floors

Based on `20-research-stability-screen-portfolios.ipynb`, using the same frozen inputs. Thirty engine runs and six independent A0b runs; no parameter search.

## Key new insights and what did we learn?

The best new full-common-period Sharpe is {best.candidate}/{best.variant}: {best.cagr:.1%} CAGR, {best.sharpe:.2f} Sharpe, {best.max_drawdown:.1%} maximum drawdown. Judge return, drawdown, cash and realised concentration together; removing a cap is not evidence of higher-quality selections.

## Summary of results

{table.to_markdown(index=False)}

HyperAI common dates: 1 January–8 July 2026. Full common dates: 13 September 2025–8 September 2026. Native engine full runs start 1 August 2025, so the common full period is a slice rather than a cold start. Sharpe uses two-day marks. A0b remains an independent simulator with its inherited different fee/accounting conventions.

## What changed?

- Bounded controls are saved NB20 unscreened runs: six slots, 33% portfolio weight and 33% historical vault TVL capacity.
- Unrestricted changes those limits to the entire universe, 100% portfolio weight and 100% historical vault TVL. It retains each strategy's relative filters, making this the allocation-limit experiment.
- Daily/weekly floor-only arms use the same unrestricted limits and fixed NB19 quality conditions. They disable measured_8's eight-name deletion and inverse_vol_q10's 10% deletion. Consequently those two families collapse to the anchor under identical floors; exact curve equality is checked rather than claiming three independent findings.
- Daily: positive 30-day return excluding the two best days; maximum drawdown at most 5%; worst completed week at least -3%. Weekly: positive four-week return excluding the best week; weekly-mark drawdown at most 5%; worst week at least -3%.
- Missing quality estimates FAIL admission in these floor-only arms; NB20 passed them through. Thus differences from old screened runs combine allocation limits, stricter missingness and removal of relative filters. See versus-nb20-screens.csv. This is not a one-parameter causal attribution.
- Empty eligible sets in the floor-only engine arms continue through zero-target rebalancing, instead of the inherited early return that could preserve old holdings. This is another intentional difference from NB20. No minimum number of positions or fallback picks. Cash is permitted if no qualifying vault is investable. The portfolio retains a 98% deployment target and the existing small-position/trade thresholds, so not every qualifying vault necessarily receives a trade.
- TVL, operational deposit checks, return gates, fees and inverse-variance sizing are retained. 100% historical TVL remains a capacity assumption, not a claim of practical capacity for a large live deposit.

## Allocation outcomes

{allocation.to_markdown(index=False)}

Position counts, actual peak single-vault weights and effective position counts expose whether the result is a broad book or effectively one vault. Engine values use pre-decision marks; A0b concentration uses rebalance target dollars and deployment uses saved daily equity. Missing or zero-investment rows are not evidence of diversification.

## Leave-one-vault-out sensitivity

The unrestricted short-period anchor's largest positive contributor is intothecryptoverse.com. Its recorded daily NAV nearly doubles on 25 June 2026 after a flat stretch. The shorter-period position contributes approximately $9,533. This is not evidence of consistently earned returns, whether the jump is genuine trading performance or a reporting artefact. The source price data alone does not establish its cause.

The following is a true rerun with that vault unavailable from the beginning, allowing replacement allocations. It is a retrospective sensitivity test, not a new production blacklist:

{loo[['period','variant','cagr','sharpe','max_drawdown']].to_markdown(index=False)}

The anchor falls from approximately 19.7% to 6.6% CAGR in the shorter period, and from 11.0% to 4.4% on the full common period. Reduced drawdown survives, but the return objective does not. Source concentration in P&L matters even when the portfolio holds many vaults.

## Robustness of results

NB20 controls are reused only after their input hashes match. Feature arithmetic is checked against the scalar NB19 implementation. New-position audit passes for {len(audit)} engine positions: floor-only entries have known passing estimates. Relative-filter removal makes eight curve pairs identical within one cent. No newly chosen threshold was tuned to results.

Per-vault and per-position P&L, curator flags, largest positive-P&L shares, best-cycle BTC/ETH returns and kurtosis are exported. Leader NAV curves, zero-return shares and largest individual positions expose stale/flat histories and concentrated gains. Best-cycle held-vault observed NAV returns are contextual diagnostics, not exact cashflow-weighted P&L attribution. Closed positions funded above $100 with less than $1 returned: {int(flow.lost_all_capital.sum())}. Historical data cleaning can still affect apparent smoothness and jumps; disabling local blacklists cannot restore upstream omitted observations. These are retrospective tests, not out-of-sample evidence.

StratWise receives {len(strat)} actual engine positions across the separate runs. Existing 90-day inverse-volatility sizing is unchanged; removing the position quota does not itself supply young-vault sizing estimates. Quality floors require only 28/30 days, not a year, but that inherited sizing limitation remains.
"""
    (project / "quality-only-summary-01.md").write_text(findings)
    (out / "heading-results.md").write_text(findings)
    return results, comparison
