"""Simple profitable-month experiments on the NB22 engine and frozen inputs."""

import itertools
import hashlib
import inspect
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
from tqdm_loggable.auto import tqdm

SCORES = ["positive_reward", "month_balance", "mean_return", "capped_mean"]
STRATWISE = "0x0ff219ac20596b457558341bc410bc7a08a1394c"


def set_single_redemption_fee(trade, pricing_model, timestamp):
    """Price a redemption from gross mid, including partial Hypercore reductions.

    A partial reduction may arrive with an already net planned mid price.
    Re-fetch the gross mid rather than applying a fee to that net value.
    """
    gross = float(pricing_model.get_sell_price(timestamp, trade.pair, abs(trade.planned_quantity)).mid_price)
    fee = float(trade.other_data["backtest_vault_redemption_fee"])
    assert np.isfinite(gross) and gross > 0 and 0 <= fee < 1
    trade.planned_mid_price = gross
    trade.planned_price = gross * (1 - fee)
    trade.other_data["nb23_gross_redemption_mid"] = gross


def month_features(series, decision, lookback):
    """Use completed calendar months, or unannualised partial history if none exist.

    All endpoints strictly precede the decision or month boundary. Missing
    pre-inception months are omitted, never filled with zeros.
    """
    decision = pd.Timestamp(decision)
    observed = series.loc[series.index < decision].dropna()
    if len(observed) < 2 or (observed.index[-1] - observed.index[0]) < pd.Timedelta(days=1):
        return None
    boundary = decision.to_period("M").start_time
    monthly = []
    for offset in range(lookback, 0, -1):
        left = boundary - pd.DateOffset(months=offset)
        right = left + pd.DateOffset(months=1)
        before = observed.loc[observed.index < left]
        after = observed.loc[observed.index < right]
        if len(before) and len(after):
            monthly.append(float(after.iloc[-1] / before.iloc[-1] - 1.0))
    provisional = not monthly
    returns = np.array(monthly if monthly else [float(observed.iloc[-1] / observed.iloc[0] - 1.0)])
    positive = returns[returns > 0]
    p, n, m = len(positive), int((returns < 0).sum()), len(returns)
    gain = float(positive.mean()) if p else 0.0
    growth = float(np.prod(1.0 + returns) - 1.0)
    scores = dict(positive_reward=p / m * gain, month_balance=(p - n) / m * gain, mean_return=float(returns.mean()), capped_mean=float(np.minimum(returns, 0.10).mean()))
    return dict(months=len(monthly), provisional=provisional, positive=p, negative=n, growth=growth, mean_positive=gain, history_days=(decision - observed.index[0]).total_seconds() / 86400, **{k: max(v, 0.0) if growth > 0 else 0.0 for k, v in scores.items()})


def prepare(ns):
    """Precompute causal scores once; shared by every fixed engine run."""
    out = ns["OUT"]
    path = ns["PRICE_PATH"]
    stat = Path(path).stat()
    signature = hashlib.sha256((inspect.getsource(month_features) + str(Path(path).resolve()) + str((stat.st_size, stat.st_mtime_ns)) + str(sorted(ns["off_addresses"]))).encode()).hexdigest()
    signature_file = out / "monthly-features.sha256"
    if signature_file.exists() and signature_file.read_text() == signature and (out / "monthly-features.parquet").exists():
        panel = pd.read_parquet(out / "monthly-features.parquet")
        ns["MONTH_LOOKUP"] = {(r["date"], r["address"], r["lookback"]): r for r in panel.to_dict("records")}
        print(f"Reused {len(panel):,} monthly feature rows with matching source/data signature", flush=True)
        return panel
    raw = pd.read_parquet(path, columns=["address", "share_price"], filters=[("address", "in", sorted(ns["off_addresses"]))])
    groups = {a: g.share_price.sort_index() for a, g in raw.groupby("address")}
    dates = pd.date_range("2025-07-31", "2026-09-08", freq="D")
    records = []
    started = time.monotonic()
    for i, (address, series) in enumerate(tqdm(groups.items(), desc="Monthly score panel")):
        for date in dates:
            for lookback in [3, 6]:
                values = month_features(series, date, lookback)
                if values is not None:
                    records.append(dict(address=address, date=date, lookback=lookback, **values))
        if (i + 1) % 60 == 0:
            print(f"{i+1}/{len(groups)} vaults; estimated minutes remaining {(time.monotonic()-started)/(i+1)*(len(groups)-i-1)/60:.1f}", flush=True)
    panel = pd.DataFrame(records)
    panel.to_parquet(out / "monthly-features.parquet", index=False)
    signature_file.write_text(signature)
    ns["MONTH_LOOKUP"] = {(r["date"], r["address"], r["lookback"]): r for r in records}
    display(panel[panel.address.eq(STRATWISE)].tail(4))
    return panel


def verify():
    """Check causal month boundaries, missing history and loss arithmetic."""
    from types import SimpleNamespace

    for incoming_mid in [100.0, 99.9, 95.0]:
        for fee in [0.001, 0.05]:
            trade = SimpleNamespace(pair=object(), planned_quantity=-2.0, planned_mid_price=incoming_mid, other_data={"backtest_vault_redemption_fee": fee})
            pricing = SimpleNamespace(get_sell_price=lambda *args: SimpleNamespace(mid_price=100.0))
            set_single_redemption_fee(trade, pricing, None)
            assert trade.planned_price == 100.0 * (1 - fee)
            set_single_redemption_fee(trade, pricing, None)
            assert trade.planned_price == 100.0 * (1 - fee), "Repeated application must not compound fees"
    s = pd.Series([1.0, 1.02, 1.0404, 1.061208], index=pd.to_datetime(["2025-12-31 12:00", "2026-01-31 12:00", "2026-02-28 12:00", "2026-03-31 12:00"]))
    r = month_features(s, "2026-04-01", 6)
    assert r["months"] == 3 and np.isclose(r["month_balance"], 0.02)
    future = pd.concat([s, pd.Series([99.0], index=pd.to_datetime(["2026-04-01"]))])
    assert month_features(future, "2026-04-01", 6) == r
    losing = pd.Series([1.0, 1.02, 1.0404, 0.7], index=s.index)
    assert all(month_features(losing, "2026-04-01", 6)[k] == 0 for k in SCORES)
    young = pd.Series([1.0, 1.01], index=pd.to_datetime(["2026-07-16", "2026-07-23"]))
    y = month_features(young, "2026-07-24", 6)
    assert y["provisional"] and y["months"] == 0 and y["month_balance"] > 0
    assert month_features(s.iloc[:2], "2026-02-01", 6)["months"] == 1


def run_all(ns):
    from nb20_stability_screens import curve_metrics

    out = ns["OUT"]
    metrics = []
    positions = []
    trades = []
    allocations = []
    fee_audit = []
    anchor_changes = []
    jobs = [(period, score, lb) for period in ["hyper_ai", "full"] for score, lb in [("anchor", 6), ("equal_profit", 6)] + list(itertools.product(SCORES, [3, 6]))]
    started = time.monotonic()
    for i, (period, score, lb) in enumerate(tqdm(jobs, desc="Profitable-month backtests")):
        print(f"Run {i+1}/{len(jobs)}: {period}/{score}/{lb}; elapsed {(time.monotonic()-started)/60:.1f} min", flush=True)
        ns["MONTH_RULE"] = score
        ns["MONTH_LOOKBACK"] = lb
        ns["MONTH_LOG"].clear()
        ns["CYCLE_LOG"].clear()
        ns["SCREEN_LOG"].clear()
        start, end = ns["WINDOWS"][period]
        overrides = {} if score == "anchor" else dict(max_assets_in_portfolio=len(ns["off_addresses"]), max_concentration_pct=1.0, weighting_method="equal" if score == "equal_profit" else "composite")
        with ns["patch"]("tradeexecutor.strategy.pandas_trader.position_manager.PositionManager.is_problematic_pair", return_value=False):
            state, eq, ret = ns["run_variant"](f"months-{period}-{score}-{lb}", backtest_start=start, backtest_end=end, **overrides)
        keys = dict(period=period, rule=score, lookback=lb)
        eq.attrs = {}
        eq.rename("equity").to_frame().to_parquet(out / f"curve-{period}-{score}-{lb}.parquet")
        common_start = "2026-01-01" if period == "hyper_ai" else "2025-09-13"
        common_end = "2026-07-08" if period == "hyper_ai" else "2026-09-08"
        metrics.append({**keys, **curve_metrics(eq.loc[common_start:common_end])})
        if score == "anchor":
            previous = pd.read_parquet(ns["PROJECT"] / "_artifacts-allocation-decomposition" / f"curve-{period}-all-N0W0V0.parquet").equity
            assert eq.index.equals(previous.index), "Anchor dates changed"
            anchor_changes.append({**keys, "old_final_equity": previous.iloc[-1], "corrected_final_equity": eq.iloc[-1], "max_absolute_equity_change": float((eq - previous).abs().max())})
        for position in state.portfolio.get_all_positions():
            if position.is_credit_supply():
                continue
            address = str(position.pair.pool_address).lower()
            positions.append({**keys, "position_id": position.position_id, "address": address, "name": ns["META"].get(address, {}).get("name"), "opened_at": position.opened_at, "closed_at": position.closed_at, "pnl": float(position.get_total_profit_usd() or 0)})
            for trade in position.trades.values():
                trades.append({**keys, "position_id": position.position_id, "address": address, "date": trade.executed_at, "quantity": float(trade.executed_quantity or 0), "value": float(trade.get_executed_value() or 0)})
                if trade.is_sell() and trade.executed_at is not None:
                    gross = trade.other_data["nb23_gross_redemption_mid"]
                    fee = trade.other_data["backtest_vault_redemption_fee"]
                    expected = gross * (1 - fee)
                    actual = float(trade.executed_price)
                    assert np.isclose(actual, expected, rtol=1e-9, atol=1e-12), (trade.trade_id, actual, expected)
                    fee_audit.append({**keys, "trade_id": trade.trade_id, "date": trade.executed_at, "address": address, "gross_mid": gross, "fee_rate": fee, "expected_net_price": expected, "executed_price": actual})
        allocations.extend([{**keys, **r} for r in ns["CYCLE_LOG"]])
        pd.DataFrame(ns["MONTH_LOG"]).to_parquet(out / f"decisions-{period}-{score}-{lb}.parquet", index=False)
        for file, rows in [("metrics", metrics), ("positions", positions), ("trades", trades), ("allocations", allocations), ("redemption-fee-audit", fee_audit), ("anchor-fee-correction", anchor_changes)]:
            pd.DataFrame(rows).to_csv(out / f"{file}.csv", index=False)
        del state
    display(pd.DataFrame(metrics))


def report(ns):
    out = ns["OUT"]
    m = pd.read_csv(out / "metrics.csv")
    pos = pd.read_csv(out / "positions.csv")
    tr = pd.read_csv(out / "trades.csv")
    assert len(m) == 20 and not m.duplicated(["period", "rule", "lookback"]).any()
    keys = ["period", "rule", "lookback"]
    allocation = pd.read_csv(out / "allocations.csv")
    allocation["date"] = pd.to_datetime(allocation.date)
    allocation = allocation[((allocation.period == "full") & allocation.date.between("2025-09-13", "2026-09-08")) | ((allocation.period == "hyper_ai") & allocation.date.between("2026-01-01", "2026-07-08"))]
    stats = allocation.groupby(keys).agg(mean_invested=("invested", "mean"), mean_positions=("positions", "mean"), peak_weight=("max_weight", "max")).reset_index()
    stats.to_csv(out / "allocation-summary.csv", index=False)
    attr = pos.groupby(keys + ["address", "name"], dropna=False).pnl.sum().reset_index()
    attr.to_csv(out / "vault-attribution.csv", index=False)
    top = attr.sort_values("pnl", ascending=False).groupby(keys).head(1).copy()
    gross = attr.assign(gross=attr.pnl.clip(lower=0)).groupby(keys).gross.sum()
    top["positive_pnl_share"] = [r.pnl / gross.loc[(r.period, r.rule, r.lookback)] if gross.loc[(r.period, r.rule, r.lookback)] > 0 else np.nan for r in top.itertuples()]
    top.to_csv(out / "top-contributors.csv", index=False)
    young = pos[pos.address.eq(STRATWISE)].groupby(keys).agg(first_entry=("opened_at", "min"), positions=("position_id", "size"), pnl=("pnl", "sum")).reset_index()
    young.to_csv(out / "stratwise-allocation.csv", index=False)
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, QUARANTINE_PERIODS

    pos["curator_excluded"] = pos.address.isin(EXCLUDED_VAULTS)
    pos["quarantined_entry"] = [any(r.address == a and pd.Timestamp(lo) <= pd.Timestamp(r.opened_at) <= pd.Timestamp(hi) for a, lo, hi, _ in QUARANTINE_PERIODS) for r in pos.itertuples()]
    pos.to_csv(out / "position-audit.csv", index=False)
    from tradingstrategy.binance.price import fetch_binance_price

    refs = {s: fetch_binance_price(symbol=s)["close"] for s in ["BTCUSDT", "ETHUSDT"]}
    jumps = []
    for row in m.itertuples():
        eq = pd.read_parquet(out / f"curve-{row.period}-{row.rule}-{row.lookback}.parquet").equity.loc[row.start : row.end]
        returns = eq.pct_change().dropna()
        end = returns.idxmax()
        start = eq.index[eq.index.get_loc(end) - 1]
        item = {k: getattr(row, k) for k in keys}
        item.update(start=start, end=end, portfolio_return=returns.max(), kurtosis=returns.kurt())
        for symbol, s in refs.items():
            s = s.copy()
            s.index = pd.DatetimeIndex(s.index).tz_localize(None) + pd.Timedelta(days=1)
            item[symbol] = s.loc[:end].iloc[-1] / s.loc[:start].iloc[-1] - 1
        jumps.append(item)
    jump_table = pd.DataFrame(jumps)
    jump_table.to_csv(out / "best-cycle-market.csv", index=False)
    flagged = pos[pos.curator_excluded | pos.quarantined_entry].groupby(keys).agg(flagged_positions=("position_id", "size"), flagged_pnl=("pnl", "sum")).reset_index()
    display(jump_table)
    display(flagged)
    for period in ["hyper_ai", "full"]:
        fig, ax = plt.subplots(figsize=(14, 6))
        for r in m[m.period.eq(period)].itertuples():
            eq = pd.read_parquet(out / f"curve-{r.period}-{r.rule}-{r.lookback}.parquet").equity.loc[r.start : r.end]
            ax.plot(eq.index, eq / eq.iloc[0], label=f"{r.rule}/{r.lookback}m")
        ax.set_title(f"Profitable-month variants: {period}")
        ax.legend(ncol=2)
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(out / f"equity-{period}.png", dpi=140)
        plt.show()
    table = m[keys + ["cagr", "sharpe", "weekly_sharpe", "max_drawdown"]].copy()
    for c in ["cagr", "max_drawdown"]:
        table[c] = table[c].map(lambda v: f"{v:.1%}")
    for c in ["sharpe", "weekly_sharpe"]:
        table[c] = table[c].round(2)
    display(table)
    display(stats)
    display(top)
    display(young)
    findings = []
    for period in ["hyper_ai", "full"]:
        candidates = m[m.period.eq(period) & m.rule.isin(SCORES)]
        feasible = candidates[candidates.cagr >= 0.20]
        if feasible.empty:
            findings.append(f"No monthly-score arm reaches 20% CAGR in {period}.")
        else:
            best = feasible.sort_values("sharpe", ascending=False).iloc[0]
            findings.append(f"Among monthly-score arms reaching 20% CAGR in {period}, {best.rule}/{best.lookback}m has the highest cycle Sharpe: {best.sharpe:.2f}, with {best.cagr:.1%} CAGR and {best.max_drawdown:.1%} maximum drawdown.")
    findings.append(f"StratWise has actual positions in {len(young)} of the 20 runs; see the table for periods and variants. Admission alone does not imply a meaningful portfolio weight.")
    new = m[m.rule.ne("anchor")]
    if new.cagr.lt(0).all():
        findings.append("Every new arm loses money in both periods, including the equal-weight profitability control. These standalone monthly policies do not meet the objective of high Sharpe with roughly 20% CAGR. This does not isolate whether the monthly feature itself lacks value: selection, sizing and the removal of the recent-return gate all change relative to the anchor.")
    findings.append("The count score is still a return-chasing score: multiplying by mean positive return allows large winning months to dominate modest steady gains. A positive trailing compounded return also admits many vaults whose recent performance has deteriorated. Completed-month scores do not react to a reversal within the current month. These are mechanisms to investigate, not separately proven causal attributions.")
    indexed = m.set_index(keys)
    cap_improves = all(indexed.loc[(period, "capped_mean", lb), "cagr"] > indexed.loc[(period, "mean_return", lb), "cagr"] and indexed.loc[(period, "capped_mean", lb), "max_drawdown"] > indexed.loc[(period, "mean_return", lb), "max_drawdown"] for period in ["hyper_ai", "full"] for lb in [3, 6])
    if cap_improves:
        findings.append("The 10% cap improves CAGR and drawdown versus uncapped mean-return sizing at both lookbacks in both periods. This does not establish an investable strategy or isolate ranking skill.")
    if len(young):
        findings.append(f"StratWise is purchased in {len(young)} configurations, with native-window P&L from ${young.pnl.min():.2f} to ${young.pnl.max():.2f} on $150,000 initial capital. It has no history in the Hyper-ai period. Young-vault access is distinct from meaningful allocation to steady vaults.")
    old = pd.read_csv(ns["PROJECT"] / "_artifacts-profitable-months-before-fee-fix/metrics.csv")
    comparison = m.merge(old, on=keys, suffixes=("_corrected", "_before"))
    comparison["cagr_change_pp"] = 100 * (comparison.cagr_corrected - comparison.cagr_before)
    comparison = comparison[keys + ["cagr_before", "cagr_corrected", "cagr_change_pp", "sharpe_before", "sharpe_corrected", "max_drawdown_before", "max_drawdown_corrected"]]
    comparison.to_csv(out / "fee-fix-comparison.csv", index=False)
    display(comparison)
    audit = pd.read_csv(out / "redemption-fee-audit.csv")
    assert np.allclose(audit.executed_price, audit.expected_net_price, rtol=1e-9, atol=1e-12)
    interpretation = "\n\n".join(findings)
    worst = attr[(attr.period == "full") & (attr.rule == "capped_mean") & (attr.lookback == 6)].sort_values("pnl").head(8)
    text = f"""# Profitable-month selection variants

Executed notebook: [23-research-profitable-months.ipynb](23-research-profitable-months.ipynb).

Based on `22-research-allocation-decomposition.ipynb`. Twenty fixed engine runs on its frozen inputs; all blacklists remain disabled. The experiment changes monthly selection and score-based sizing together, with an equal-weight profitability control. It is historical exploratory research, not an out-of-sample strategy discovery.

## Key new insights

{interpretation}

Four simple rules are tested at three and six completed calendar months. Let P/N be positive/negative month counts, M all available completed months including zeros, and G the mean positive-month return.

| Rule | Formula | Meaning |
|---|---|---|
| positive_reward | P/M × G | Reward frequent and larger profitable months; losses dilute frequency |
| month_balance | (P−N)/M × G | Losing months explicitly penalise desirability |
| mean_return | Mean monthly return | Include the size of losses as well as gains |
| capped_mean | Mean(min(monthly return, 10%)) | Limit the influence of exceptional positive months; retain losses in full |
| equal_profit | Equal weights for positive compounded growth, six months | Sizing/selection reference without the monthly ranking |
| anchor | Original six-position CAGR/Sortino + inverse variance | NB22 policy with corrected redemption accounting |

All new arms require positive compounded growth and a positive score. Relative scores determine weights across all qualifying, deposit-eligible vaults; no fixed position count or portfolio-weight ceiling. The inherited 33% historical vault-TVL capacity, 98% deployment target, 0.5% minimum position weight, small-trade thresholds and engine fee/settlement model remain. A tiny positive score does not guarantee an executed position. Monthly arms replace the old 14-day gate and long-lookback score; inverse variance is not used. Thus comparison with the original anchor is a full-policy comparison, not an isolated score substitution. Rebalancing retains the parent's two-day engine cycle; completed-month scores normally change monthly, while provisional scores can change each cycle.

All 20 runs, including anchors, now price redemptions from the gross quoted mid and apply the fee once. Partial reductions previously supplied an already-net planned mid, causing a second deduction. The extra accrued-fee cash buffer has been removed: every arm uses the same inherited cash headroom. Original outputs are preserved in `_artifacts-profitable-months-before-fee-fix/`; corrected anchors intentionally no longer match the defective NB22 equity curves. Strategy rules and frozen data remain unchanged.

The inherited $750 sell-rebalance threshold can suppress trims in the smaller monthly-rule positions, so realised weights can drift from targets. A monthly arm with no qualifying candidates liquidates, whereas the inherited anchor retains its original empty-candidate behaviour.

Completed calendar months exclude the current incomplete month and the inception partial month. If no completed month exists, use unannualised since-inception return as one provisional observation after two marks at least a day apart; the month count remains zero. No 90/360-day sizing requirement, minimum monthly evidence count or daily-reporting gate. Older vaults are normalised by available month count, not rewarded just for age. A month with zero return gives no positive reward. Provisional history is shorter and less comparable; it is disclosed rather than assigned fake completed months.

## Summary of results

{table.to_markdown(index=False)}

Full common period: 13 September 2025–8 September 2026. Hyper-ai common period: 1 January–8 July 2026. Native full engine run starts 1 August (initial equity point 31 July). Full metrics slice already-running portfolios. Two-day and weekly Sharpe are separately reported; no assumption of annual returns persisting.

### Actual StratWise allocations

{young.to_markdown(index=False) if len(young) else 'No StratWise positions were executed; inspect the saved decision logs for the admission and sizing outcome.'}

### Allocation and leading contributors

{stats.to_markdown(index=False)}

{top.to_markdown(index=False)}

### Largest losses in the six-month capped rule

{worst.to_markdown(index=False)}

These position P&Ls cover the native engine run, including the period before the full-period common metrics slice. They should not be summed to reconcile the sliced CAGR.

## Robustness of results

### Largest cycles and market comparison

{jump_table.to_markdown(index=False)}

### Curator-flagged executed positions

{flagged.to_markdown(index=False) if len(flagged) else 'No executed positions matched the curator exclusions or quarantine entry periods.'}

Anchor dates must still match NB22; equity differences from corrected fees are exported to `anchor-fee-correction.csv`. Every executed redemption is checked against gross mid times one minus its fee, with {len(audit):,} checked sells in `redemption-fee-audit.csv`. Month-cutoff and young-history assertions run before the score panel. Every decision uses strictly earlier prices; weekly observations can be carried to month boundaries. Scores and decisions are exported, as are trades, per-vault P&L, curator annotations and the best two-day return alongside BTC/ETH. All universe arms share the same frozen file paths. Reporting and repair limitations of that snapshot persist.

The largest positive cycles and BTC/ETH comparisons appear above; they are not evidence of steady returns. Curator-flagged vault P&L and leading-contributor shares are retained so unusually large gains are visible without treating them as proof of selection skill.

### Change after fixing fees

{comparison.round(4).to_markdown(index=False)}

This comparison comes from full re-simulations, not adding estimated fees back to equity. Changed cash balances can alter later allocations and trades.

The 10% positive-month cap is a declared sensitivity, not an optimised threshold. The equal-profit control helps show whether scoring adds value, but different positive-score sets also change holdings. Cumulative buy value is turnover, not time-weighted allocation. Individual P&L covers the native engine window. No winner chosen on these reused dates constitutes independent validation; young-vault access is checked through actual trades.
"""
    (ns["PROJECT"] / "profitable-months-summary-01.md").write_text(text)
    (out / "heading-results.md").write_text(text)
    return text
