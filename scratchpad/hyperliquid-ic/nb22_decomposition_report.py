"""Factorial and path-averaged allocation attribution, using saved engine results."""

import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

COMMON_WINDOWS = {
    "hyper_ai": (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-08")),
    "full": (pd.Timestamp("2025-09-13"), pd.Timestamp("2026-09-08")),
}


def calculate_mark_quality_audit(out, trades):
    """Measure sparse-mark exposure using only the frozen price snapshot.

    ``funded_low_fresh_share`` is exact for the recorded trades. The two
    end-value shares reconstruct open position value from recorded trade
    quantities and the frozen terminal mark; they are a mark-quality exposure
    diagnostic and deliberately do not claim exact portfolio equity, because
    reserve and fee accounting remain in the engine state.
    """
    raw = pd.read_parquet(
        out / "inputs/vault-prices.parquet",
        columns=["address", "share_price"],
    )
    raw["address"] = raw["address"].str.lower()
    raw = raw[raw.address.isin(set(trades.address))]
    price_by_address = {address: frame.share_price.sort_index() for address, frame in raw.groupby("address")}
    rows = []
    vault_rows = []
    for (period, mask, arm), arm_trades in trades.groupby(["period", "mask", "arm"]):
        start, end = COMMON_WINDOWS[period]
        arm_trades = arm_trades.copy()
        arm_trades["date"] = pd.to_datetime(arm_trades.date)
        arm_trades = arm_trades[arm_trades.date <= end]
        funded = arm_trades.assign(funded=arm_trades.value.where(arm_trades.quantity.gt(0), 0.0)).groupby("address").funded.sum()
        net_quantity = arm_trades.groupby(["position_id", "address"]).quantity.sum()
        address_value = {}
        freshness = {}
        for address in funded.index:
            daily = price_by_address[address].resample("D").last().ffill().loc[start:end]
            moved = daily.pct_change().ne(0.0).iloc[1:]
            moved_dates = moved.index[moved]
            mark_age_days = (end - moved_dates[-1]).days if len(moved_dates) else len(daily)
            freshness[address] = {
                "fresh_day_share": float(moved.mean()),
                "mark_age_days": mark_age_days,
            }
            remaining_quantity = sum(quantity for (position_id, position_address), quantity in net_quantity.items() if position_address == address and quantity > 0.0)
            address_value[address] = remaining_quantity * daily.iloc[-1]
            vault_rows.append(
                {
                    "period": period,
                    "mask": mask,
                    "arm": arm,
                    "address": address,
                    "funded": funded[address],
                    "reconstructed_end_mark_value": address_value[address],
                    **freshness[address],
                }
            )
        total_funded = funded.sum()
        total_value = sum(address_value.values())
        low_fresh_funded = sum(funded[address] for address in funded.index if freshness[address]["fresh_day_share"] < 0.30)
        stale30_value = sum(address_value[address] for address in funded.index if freshness[address]["mark_age_days"] > 30)
        stale60_value = sum(address_value[address] for address in funded.index if freshness[address]["mark_age_days"] > 60)
        rows.append(
            {
                "period": period,
                "mask": mask,
                "arm": arm,
                "funded_low_fresh_share": low_fresh_funded / total_funded if total_funded else np.nan,
                "stale_over_30d_end_mark_share": stale30_value / total_value if total_value else np.nan,
                "stale_over_60d_end_mark_share": stale60_value / total_value if total_value else np.nan,
            }
        )
    audit = pd.DataFrame(rows)
    by_vault = pd.DataFrame(vault_rows)
    audit.to_csv(out / "mark-quality-audit.csv", index=False)
    by_vault.to_csv(out / "mark-quality-by-vault.csv", index=False)
    return audit, by_vault


def report(project):
    out = project / "_artifacts-allocation-decomposition"
    metrics = pd.read_csv(out / "metrics.csv")
    positions = pd.read_csv(out / "positions.csv")
    trades = pd.read_csv(out / "trades.csv")
    cycles = pd.read_csv(out / "cycles.csv")
    assert len(metrics) == 32
    cycles.date = pd.to_datetime(cycles.date)
    cycles = cycles[(cycles.period.eq("hyper_ai") & cycles.date.between("2026-01-01", "2026-07-08")) | (cycles.period.eq("full") & cycles.date.between("2025-09-13", "2026-09-08"))]
    allocation = cycles.groupby(["period", "mask", "arm"]).agg(mean_invested=("invested_fraction", "mean"), mean_positions=("positions", "mean"), max_positions=("positions", "max"), peak_weight=("max_weight", "max"), effective_positions=("effective_positions", "mean")).reset_index()
    allocation.to_csv(out / "allocation.csv", index=False)
    effects = []
    shapley = []
    interactions = []
    for (period, mask), g in metrics.groupby(["period", "mask"]):
        lookup = {tuple(int(getattr(row, f)) for f in "NWV"): row for row in g.itertuples()}
        for metric in ["cagr", "sharpe", "volatility", "max_drawdown"]:
            for j, factor in enumerate("NWV"):
                differences = []
                for bits in itertools.product([0, 1], repeat=3):
                    if bits[j]:
                        continue
                    higher = list(bits)
                    higher[j] = 1
                    delta = getattr(lookup[tuple(higher)], metric) - getattr(lookup[bits], metric)
                    effects.append({"period": period, "mask": mask, "metric": metric, "factor": factor, "from_arm": lookup[bits].arm, "to_arm": lookup[tuple(higher)].arm, "change": delta})
            contributions = {f: [] for f in "NWV"}
            for order in itertools.permutations(range(3)):
                bits = [0, 0, 0]
                for j in order:
                    before = getattr(lookup[tuple(bits)], metric)
                    bits[j] = 1
                    contributions["NWV"[j]].append(getattr(lookup[tuple(bits)], metric) - before)
            total = getattr(lookup[(1, 1, 1)], metric) - getattr(lookup[(0, 0, 0)], metric)
            assert np.isclose(sum(np.mean(v) for v in contributions.values()), total)
            for f, v in contributions.items():
                shapley.append({"period": period, "mask": mask, "metric": metric, "factor": f, "contribution": np.mean(v), "total_change": total})
            # Factorial interaction contrasts: effect of one switch depends on the other switches.
            for i, j in itertools.combinations(range(3), 2):
                k = next(k for k in range(3) if k not in [i, j])
                for fixed in [0, 1]:
                    value = 0.0
                    for a, b in itertools.product([0, 1], repeat=2):
                        bits = [0, 0, 0]
                        bits[i] = a
                        bits[j] = b
                        bits[k] = fixed
                        value += (-1) ** (2 - a - b) * getattr(lookup[tuple(bits)], metric)
                    interactions.append({"period": period, "mask": mask, "metric": metric, "interaction": "NWV"[i] + "NWV"[j], "other_factor": "NWV"[k], "other_value": fixed, "contrast": value})
    effects = pd.DataFrame(effects)
    shapley = pd.DataFrame(shapley)
    effects.to_csv(out / "conditional-effects.csv", index=False)
    shapley.to_csv(out / "shapley-decomposition.csv", index=False)
    pd.DataFrame(interactions).to_csv(out / "interactions.csv", index=False)
    display(metrics)
    display(shapley[shapley.metric.isin(["cagr", "sharpe"])])
    display(allocation)
    for period in ["hyper_ai", "full"]:
        fig, axes = plt.subplots(1, 2, figsize=(18, 6))
        for mask, ax in zip(["all", "leader_out"], axes):
            for arm in metrics.arm.unique():
                eq = pd.read_parquet(out / f"curve-{period}-{mask}-{arm}.parquet").equity
                start = "2026-01-01" if period == "hyper_ai" else "2025-09-13"
                end = "2026-07-08" if period == "hyper_ai" else "2026-09-08"
                eq = eq.loc[start:end]
                ax.plot(eq.index, eq / eq.iloc[0], label=arm)
            ax.set_title(period + " / " + mask)
            ax.legend(fontsize=8, ncol=2)
            ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(out / f"equity-{period}.png", dpi=140)
        plt.show()
    attr = positions.groupby(["period", "mask", "arm", "address", "name"], dropna=False).agg(pnl=("pnl", "sum"), positions=("position_id", "size")).reset_index()
    attr.to_csv(out / "vault-attribution.csv", index=False)
    positive = attr.assign(positive=attr.pnl.clip(lower=0)).groupby(["period", "mask", "arm"]).positive.sum()
    top = attr.sort_values("pnl", ascending=False).groupby(["period", "mask", "arm"]).head(1).copy()
    top["positive_share"] = [r.pnl / positive.loc[(r.period, r.mask, r.arm)] if positive.loc[(r.period, r.mask, r.arm)] > 0 else np.nan for r in top.itertuples()]
    top.to_csv(out / "largest-contributors.csv", index=False)
    display(top)
    raw_diagnostics = []
    fig, ax = plt.subplots(figsize=(12, 5))
    for address, name in top[["address", "name"]].drop_duplicates().itertuples(index=False, name=None):
        raw = pd.read_parquet(out / "inputs/vault-prices.parquet", filters=[("address", "=", address)], columns=["share_price", "timestamp"]).sort_index()
        daily = raw.share_price.resample("D").last().ffill().loc["2025-09-13":"2026-09-08"]
        if len(daily) < 2:
            continue
        ax.plot(daily.index, daily / daily.iloc[0], label=name)
        for period, start, end in [("hyper_ai", "2026-01-01", "2026-07-08"), ("full", "2025-09-13", "2026-09-08")]:
            returns = daily.loc[start:end].pct_change().dropna()
            raw_diagnostics.append({"address": address, "name": name, "period": period, "best_marked_day": returns.max(), "worst_marked_day": returns.min(), "best_day": returns.idxmax(), "marked_daily_kurtosis": returns.kurt()})
    raw_diagnostics = pd.DataFrame(raw_diagnostics)
    raw_diagnostics.to_csv(out / "leading-vault-nav-diagnostics.csv", index=False)
    ax.set_title("Leading contributors: normalised NAV (daily last mark, forward filled)")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(out / "leading-vault-nav.png", dpi=140)
    plt.show()
    display(raw_diagnostics)

    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, QUARANTINE_PERIODS

    positions["curator_excluded"] = positions.address.isin(EXCLUDED_VAULTS)
    positions["quarantined_entry"] = [any(r.address == a and pd.Timestamp(lo) <= pd.Timestamp(r.opened_at) <= pd.Timestamp(hi) for a, lo, hi, _ in QUARANTINE_PERIODS) for r in positions.itertuples()]
    positions.to_csv(out / "position-risk-audit.csv", index=False)
    positions.sort_values("pnl", ascending=False).groupby(["period", "mask", "arm"]).head(3).to_csv(out / "largest-individual-positions.csv", index=False)
    keys = ["period", "mask", "arm", "position_id"]
    trades["funded"] = trades.value.abs().where(trades.quantity.gt(0), 0)
    trades["returned"] = trades.value.abs().where(trades.quantity.lt(0), 0)
    flow = trades.groupby(keys).agg(funded=("funded", "sum"), returned=("returned", "sum")).reset_index().merge(positions[keys + ["closed_at", "address"]], on=keys)
    flow["lost_all_capital"] = flow.closed_at.notna() & flow.funded.gt(100) & flow.returned.lt(1)
    flow.to_csv(out / "capital-audit.csv", index=False)
    mark_audit, mark_by_vault = calculate_mark_quality_audit(out, trades)
    mark_table = mark_audit.merge(metrics[["period", "mask", "arm", "kurtosis"]], on=["period", "mask", "arm"]).query("period == 'full' and mask == 'all'")[["arm", "funded_low_fresh_share", "stale_over_30d_end_mark_share", "stale_over_60d_end_mark_share", "kurtosis"]].sort_values("arm")
    display(mark_table)
    from tradingstrategy.binance.price import fetch_binance_price

    refs = {sym: fetch_binance_price(symbol=sym)["close"] for sym in ["BTCUSDT", "ETHUSDT"]}
    events = []
    for row in metrics.itertuples():
        eq = pd.read_parquet(out / f"curve-{row.period}-{row.mask}-{row.arm}.parquet").equity.loc[row.start : row.end]
        ret = eq.pct_change().dropna()
        end = ret.idxmax()
        start = eq.index[eq.index.get_loc(end) - 1]
        item = {"period": row.period, "mask": row.mask, "arm": row.arm, "start": start, "end": end, "best_cycle": ret.max(), "kurtosis": ret.kurt()}
        for sym, s in refs.items():
            s = s.copy()
            s.index = pd.DatetimeIndex(s.index).tz_localize(None) + pd.Timedelta(days=1)
            before = s.loc[:start]
            after = s.loc[:end]
            item[sym] = after.iloc[-1] / before.iloc[-1] - 1 if len(before) and len(after) else np.nan
        events.append(item)
    events = pd.DataFrame(events)
    events.to_csv(out / "best-cycle-market.csv", index=False)
    display(events)
    table = metrics[["period", "mask", "arm", "cagr", "sharpe", "max_drawdown"]].copy()
    for c in ["cagr", "max_drawdown"]:
        table[c] = table[c].map(lambda x: f"{x:.1%}")
    table.sharpe = table.sharpe.map(lambda x: f"{x:.2f}")
    main = shapley[(shapley.period == "full") & (shapley.metric == "sharpe")]
    parity = pd.read_csv(out / "parity.csv")
    assert len(parity) == 6

    def metric_row(period, mask, arm):
        return metrics[(metrics.period == period) & (metrics["mask"] == mask) & (metrics.arm == arm)].iloc[0]

    full_base = metric_row("full", "all", "N0W0V0")
    full_n = metric_row("full", "all", "N1W0V0")
    full_w = metric_row("full", "all", "N0W1V0")
    full_v = metric_row("full", "all", "N0W0V1")
    full_nv = metric_row("full", "all", "N1W0V1")
    full_n_leader_out = metric_row("full", "leader_out", "N1W0V0")
    full_nv_leader_out = metric_row("full", "leader_out", "N1W0V1")
    short_w = metric_row("hyper_ai", "all", "N0W1V0")
    short_w_top = top[(top.period == "hyper_ai") & (top["mask"] == "all") & (top.arm == "N0W1V0")].iloc[0]
    full_n_marks = mark_table[mark_table.arm == "N1W0V0"].iloc[0]
    full_nv_marks = mark_table[mark_table.arm == "N1W0V1"].iloc[0]
    findings = f"""# Allocation-limit decomposition

Based on `21-research-quality-only-portfolios.ipynb`. Thirty-two fixed engine-anchor simulations: eight allocation combinations, two periods and two universe treatments. No search for a winning threshold; no A0b or other ranker generalisation is claimed.

## Key new insights and what did we learn?

This factorial separates three simultaneous NB21 changes. N changes the position maximum from 6 to the full eligible universe (360 vault addresses in this snapshot); W changes maximum portfolio weight from 33% to 100%; V changes historical vault-TVL capacity from 33% to 100%. A 1 means relaxed, a 0 means original. All primary runs retain blacklists off; leader_out excludes only intothecryptoverse.com from inception as a diagnostic counterfactual.

**The N result is not evidence that flexible portfolio size improves risk.** N alone changes full-period CAGR from {full_base.cagr:.2%} to {full_n.cagr:.2%}, Sharpe from {full_base.sharpe:.3f} to {full_n.sharpe:.3f} and maximum drawdown from {full_base.max_drawdown:.2%} to {full_n.max_drawdown:.2%}. But N raises the ceiling from six to 360 addresses: the ranker still orders candidates, yet every gate-passing candidate can enter sizing. The unchanged inverse-variance sizing then favours low-volatility share-price histories, including stale marks. In N1W0V0, {full_n_marks.funded_low_fresh_share:.1%} of funded dollars went to vaults whose daily price moved on fewer than 30% of common-window days; {full_n_marks.stale_over_30d_end_mark_share:.1%} of reconstructed terminal marked value was older than 30 days, and kurtosis was {full_n_marks['kurtosis']:.1f}. Its measured risk statistics cannot therefore be compared with the N0 arms as evidence of steadier economic returns.

**The apparent diversification is mark-quality confounded.** Mean effective holdings rise under N, but the relevant distinction is between independently re-marked holdings and a book with flat NAVs that later catch up. The allocation table remains a correct description of engine weights; it is not proof that the additional vaults are StratWise-like or that the lower measured drawdown is real. The raw diagnostics in `mark-quality-audit.csv` and `mark-quality-by-vault.csv` must accompany any N comparison.

**Removing the portfolio-weight cap is not a stable-return result.** The short-period W-only result ({short_w.cagr:.2%} CAGR, {short_w.sharpe:.3f} Sharpe) weakens to {full_w.cagr:.2%} CAGR, {full_w.sharpe:.3f} Sharpe and {full_w.max_drawdown:.2%} drawdown in the full period. {short_w_top['name']} supplies {short_w_top.positive_share:.1%} of its positive per-vault P&L in that short run (${short_w_top.pnl:,.0f} across {int(short_w_top.positions)} positions). The full-period Shapley W contribution includes this N0 concentrated path, so it does not contradict the small conditional effect of W after N is relaxed.

**Relaxing vault-TVL capacity is also dark-holding and leader dependent.** With N relaxed and W retained, it changes unmasked full CAGR from {full_n.cagr:.2%} to {full_nv.cagr:.2%}, while the low-fresh funded share rises from {full_n_marks.funded_low_fresh_share:.1%} to {full_nv_marks.funded_low_fresh_share:.1%} and stale-over-30-day terminal marked value rises from {full_n_marks.stale_over_30d_end_mark_share:.1%} to {full_nv_marks.stale_over_30d_end_mark_share:.1%}. Removing intothecryptoverse.com changes the same pair to {full_n_leader_out.cagr:.2%} and {full_nv_leader_out.cagr:.2%} CAGR. It is not a robust capacity improvement.

**Conclusion:** this experiment does not identify an allocation-limit change to carry forward for the stable-vault objective. It confirms that W-only return is concentrated and that V relaxation is not robust, but it withdraws the former N recommendation. A later experiment may test freshness-aware, age-aware sizing, including young vaults fairly; it must measure mark freshness and terminal stale-value exposure before interpreting Sharpe or drawdown. We have not demonstrated robust ~20% CAGR, steady StratWise-like selection, or a reason to introduce a new hard age barrier.

[Full-period equity curves](_artifacts-allocation-decomposition/equity-full.png) · [Hyper-ai-period equity curves](_artifacts-allocation-decomposition/equity-hyper_ai.png) · [Leading-vault NAV](_artifacts-allocation-decomposition/leading-vault-nav.png).

Full-period Sharpe attribution, averaged over all six orders of applying the switches:

{main[['mask','factor','contribution','total_change']].to_markdown(index=False)}

These Shapley contributions sum exactly to the N0W0V0→N1W1V1 change. They allocate interaction effects across factors; they are not independent effect sizes, statistical significance or estimates of live-market causality. Inspect conditional-effects.csv for every single-switch comparison and interactions.csv for dependence between switches.

## Summary of results

{table.to_markdown(index=False)}

Common periods: 1 January–8 July 2026 and 13 September 2025–8 September 2026. Full engine runs begin 1 August; full-common figures are slices of already-running portfolios. Sharpe uses two-day marks. Weekly Sharpe, volatility, best-cycle return and kurtosis are also exported.

## Allocation outcomes

{allocation.to_markdown(index=False)}

Holdings are marked before each rebalance. Effective positions equal inverse concentration of invested weights; holding count can include small residuals. Cash policy, execution thresholds, inverse-variance sizing, the CAGR/Sortino ranking, the 14-day return gate, fees and historical data are unchanged. N changes admission into sizing: at 360, all gate-passing candidates can enter, so the ranking does not impose a practical selection limit. V is a capacity assumption, not proof that depositing an entire historical vault TVL is practical.

## Mark-quality audit

{mark_table.to_markdown(index=False)}

`funded_low_fresh_share` is the share of recorded positive trade value in vaults whose daily NAV moved on fewer than 30% of common-window days. Terminal stale-value shares reconstruct the remaining trade quantities at the frozen terminal share price; they are an exposure diagnostic, not a replacement for engine equity accounting. The marked-NAV kurtosis is reported on the same two-day portfolio-return series as the results table. High stale-value exposure means low measured volatility or drawdown cannot be read as a stable equity curve.

## Leading-vault NAV diagnostics

{raw_diagnostics.to_markdown(index=False)}

These are marked NAV changes, not evidence of fresh daily observations. Forward filling preserves stale marks; jumps can incorporate several days of trading. See `leading-vault-nav.png`.

## Robustness of results

Vault metadata and prices refreshed since NB21. NB22 freezes both input files in its inputs directory and patches downloads to these files for every universe load. All 32 arms, including both endpoints, are freshly rerun on that snapshot. input-drift.csv records old/new hashes; parity.csv records equity differences against six historical endpoints, without assuming parity across different datasets. The maximum absolute equity difference across those six historical checks is ${parity.maximum_equity_difference.max():.8f}. Other source and feature hashes are checked before execution. Historical endpoint drift is separate from allocation effects within this batch. Leader exclusion is a full resimulation with substitutes, not subtraction of realised profit. The full factorial is repeated under exclusion to expose changes driven by that known NAV jump; choosing the highest remaining row still does not provide out-of-sample evidence.

Individual positions, full per-vault P&L, curator flags, positive-P&L concentration, best-cycle BTC/ETH returns, kurtosis and mark-quality exposure are saved. Native position P&L covers the original engine window, which starts earlier than the common full curve slice. Closed positions funded above $100 with less than $1 returned: {int(flow.lost_all_capital.sum())}. The N arms materially increase sparse/stale-mark exposure, so their Sharpe and drawdown remain descriptive outputs, not evidence of a lower-risk allocation. A high Sharpe caused by a few large gains or stale-to-catch-up marks is not the steady-profit objective. Prior research documented the intothecryptoverse.com jump; excluding it does not establish that other contributors are free of the same issue.

No new hard quality filters or short-history sizing rules are introduced. This experiment answers which allocation-limit changes matter inside the frozen anchor, not whether young-vault selection now works or whether 20% CAGR is reliably achievable.
"""
    (project / "allocation-decomposition-summary-01.md").write_text(findings)
    (out / "heading-results.md").write_text(findings)
    return findings
