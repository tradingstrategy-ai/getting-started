"""Feature diagnostics, figures and completed research conclusions for notebook 05."""

from pathlib import Path
import json

import nbformat
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from score_matrix import FEATURES, PERIODS
from accepted_dollar_cap import calculate_position_profit_curves
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe
from tradeexecutor.visual.equity_curve import calculate_returns
from tradeexecutor.curator.curator import EXCLUDED_VAULTS, get_hyperliquid_concentration_tweak, is_quarantined


def metrics_frame(runs):
    """Return one row per actual experiment, including mechanism metadata."""
    return pd.DataFrame([{"Configuration": name, **run["config"].__dict__, **run["metrics"]} for name, run in runs.items()])


def grid_figure(frame):
    """Show every hard-clip combination with other strategy parameters fixed."""
    data = frame[(frame["transform"] == "hard") & frame.name.str.startswith("Hard C") & ~frame.refill & frame.risk_days.eq(45)]
    fig = make_subplots(rows=1, cols=3, subplot_titles=["CAGR (%)", "Sharpe", "Maximum drawdown (%)"], horizontal_spacing=0.12)
    for col, metric in enumerate(["CAGR", "Sharpe", "Maximum drawdown"], 1):
        grid = data.pivot(index="cagr_scale", columns="sortino_scale", values=metric).sort_index()
        z = grid.to_numpy() * (1 if metric == "Sharpe" else 100)
        text = np.array([[f"{v:.2f}" for v in row] for row in z])
        fig.add_trace(go.Heatmap(z=z, x=[str(v) for v in grid.columns], y=[f"{v:.0%}" for v in grid.index], text=text, texttemplate="%{text}", textfont=dict(shadow="auto"), colorscale="RdYlGn", showscale=False), row=1, col=col)
        fig.update_xaxes(title="Sortino upper cap", row=1, col=col)
        fig.update_yaxes(title="CAGR upper cap" if col == 1 else None, autorange="reversed", row=1, col=col)
    fig.update_layout(title="Independent CAGR and Sortino clip grid", width=1450, height=480, margin=dict(t=120, b=75, l=85, r=40), template="plotly_white")
    return fig


def ic_figure(summary, outcome):
    """Compare forward feature associations at three label horizons."""
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"{h}-day {outcome.lower()}" for h in (14, 30, 60)], horizontal_spacing=0.09)
    periods = [p for p in PERIODS if p != "45d compatibility"]
    metrics = ["CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar"]
    for col, horizon in enumerate((14, 30, 60), 1):
        data = summary[(summary.Outcome == outcome) & summary.Horizon.eq(horizon)]
        grid = data.pivot(index="Metric", columns="Period", values="Mean IC").reindex(index=metrics, columns=periods)
        counts = data.pivot(index="Metric", columns="Period", values="Decision dates").reindex(index=metrics, columns=periods)
        text = np.array([[f"{v:+.2f}" if np.isfinite(v) else "—" for v in row] for row in grid.to_numpy()])
        fig.add_trace(go.Heatmap(z=grid.to_numpy(), x=periods, y=metrics, text=text, texttemplate="%{text}", textfont=dict(shadow="auto"), customdata=counts.to_numpy(), hovertemplate="%{y} / %{x}<br>Mean date IC %{z:.3f}<br>Decision dates %{customdata}<extra></extra>", coloraxis="coloraxis"), row=1, col=col)
        fig.update_yaxes(autorange="reversed", showticklabels=col == 1, row=1, col=col)
        fig.update_xaxes(tickangle=-35, row=1, col=col)
    fig.update_layout(title=f'Which features rank future vault {"returns" if outcome=="Forward return" else "Sharpe"}?', coloraxis=dict(colorscale="RdBu", cmin=-1, cmax=1, cmid=0, colorbar=dict(title="Mean IC")), width=1550, height=510, template="plotly_white", margin=dict(t=125, b=75, l=115, r=90))
    return fig


def correlation_figure(frame):
    """Average per-date eligible-universe feature correlations, including Sortino."""
    fig = make_subplots(rows=1, cols=3, subplot_titles=["45-day metrics", "90-day metrics", "360-day metrics"], horizontal_spacing=0.10)
    metrics = ["CAGR", "Sharpe", "Sortino", "Max drawdown", "Calmar"]
    for col, period in enumerate(("45d compatibility", "3m", "1y"), 1):
        data = frame[frame.Period == period].groupby(["Row", "Column"]).Rho.mean().unstack().reindex(index=metrics, columns=metrics)
        text = np.array([[f"{v:.2f}" if np.isfinite(v) else "—" for v in row] for row in data.to_numpy()])
        fig.add_trace(go.Heatmap(z=data.to_numpy(), x=metrics, y=metrics, text=text, texttemplate="%{text}", textfont=dict(shadow="auto"), coloraxis="coloraxis"), row=1, col=col)
        fig.update_xaxes(tickangle=-35, row=1, col=col)
        fig.update_yaxes(autorange="reversed", showticklabels=col == 1, row=1, col=col)
    fig.update_layout(title="Feature redundancy within each decision-date candidate universe", coloraxis=dict(colorscale="RdBu", cmin=-1, cmax=1, colorbar=dict(title="Mean Spearman ρ")), width=1500, height=540, template="plotly_white", margin=dict(t=125, b=95, l=120, r=90))
    return fig


def quintile_figure(bins):
    """Check whether feature ranks order subsequent 30-day returns monotonically."""
    choices = [("1y", "CAGR"), ("46d", "Sortino"), ("3m", "Sharpe")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"{p} {m}" for p, m in choices], horizontal_spacing=0.10)
    for col, (period, metric) in enumerate(choices, 1):
        data = bins[(bins.Period == period) & (bins.Metric == metric) & bins.Horizon.eq(30)].groupby("Score quintile")["Mean forward return"].mean()
        fig.add_trace(go.Bar(x=[str(q) for q in data.index], y=data.values * 100, text=[f"{v:.1%}" for v in data], textposition="outside", marker_color="#2563eb", showlegend=False), row=1, col=col)
        fig.update_xaxes(title="Feature-rank quintile (5 = highest)", row=1, col=col)
        fig.update_yaxes(title="Mean 30-day NAV return (%)" if col == 1 else None, row=1, col=col)
    values = [float(v) for trace in fig.data for v in trace.y]
    fig.update_yaxes(range=[min(min(values), 0) - 2, max(max(values), 0) + 2], zeroline=True, zerolinecolor="#94a3b8")
    fig.update_layout(title="Do larger feature values lead to larger subsequent returns?", width=1450, height=510, template="plotly_white", margin=dict(t=125, b=80, l=90, r=40))
    return fig


def saturation_audit(panel, run, start, end):
    """Measure clipping on all finite vault-days and the fixed baseline funding ledger."""
    mask = (panel.dates >= start) & (panel.dates < end)
    ledger = run["allocation_df"]
    funded = ledger[ledger["Final target (USD)"] > 0]
    rows = []
    for period, metric, caps in [("1y", "CAGR", (0.5, 1.0, 2.0)), ("45d compatibility", "Sortino", (3.0, 7.0, 12.0)), ("3m", "Sharpe", (3.0,)), ("3m", "Max drawdown", (0.7,)), ("3m", "Calmar", (5.0,))]:
        idx = FEATURES.index((period, metric))
        selected = np.array([panel.raw[panel.date_index[pd.Timestamp(d)], panel.pair_index[int(pid)], idx] for d, pid in zip(funded.Date, funded["Pair id"])])
        for scope, values in [("All finite vault-days", panel.raw[mask, :, idx].ravel()), ("Fixed baseline funded observations", selected)]:
            values = values[np.isfinite(values)]
            oriented = np.abs(values) if metric == "Max drawdown" else values
            for cap in caps:
                rows.append({"Feature": f"{period} {metric}", "Scope": scope, "Cap": cap, "Finite observations": len(values), "At or above cap": float((oriented >= cap).mean()), "Zero or negative": float((values <= 0).mean()), "Median raw metric": float(np.median(values))})
    scores = funded["Ranking score"]
    joint = funded.assign(Maximum_score=np.isclose(scores, 1.0))
    ties = joint.groupby("Date").Maximum_score.sum()
    return pd.DataFrame(rows), {"Funded rows": len(funded), "Maximum score fraction": float(joint.Maximum_score.mean()), "Dates with at least two funded maximum-score vaults": float((ties >= 2).mean())}


def cash_summary(runs):
    """Summarise causal target-budget reductions separately from realised cash."""
    rows = []
    for name, run in runs.items():
        ledger = run["cash_ledger"]
        if not len(ledger):
            continue
        positive = ledger[ledger["Budget (USD)"] > 0]
        budget = positive["Budget (USD)"]
        rows.append({"Configuration": name, "Mean cash weight": run["metrics"]["Mean cash weight"], "Mean residual before / budget": float((positive["Residual before refill (USD)"] / budget).mean()), "Mean blocked top-ups / budget": float((positive["Blocked top-ups (USD)"] / budget).mean()), "Mean recovered target / budget": float((positive["Recovered target (USD)"] / budget).mean()), "Mean residual after / budget": float((positive["Residual after refill (USD)"] / budget).mean()), "Refill decisions": int(positive["Recovered target (USD)"].gt(0).sum())})
    return pd.DataFrame(rows)


def attribution(runs, market):
    """Reconcile position PnL and identify vault-concentrated days and profits."""
    rows = []
    contributors = []
    jumps = []
    positions = []
    quality = get_hyperliquid_concentration_tweak()
    for name, run in runs.items():
        state = run["result"].state
        daily = run["daily_returns"]
        equity = run["equity"].resample("1D").last().reindex(daily.index).ffill()
        curves, metadata = calculate_position_profit_curves(state, daily.index)
        residual = curves.sum(axis=1) - (equity - float(run["parameters"].initial_cash))
        assert residual.abs().max() < 0.01, (name, residual.abs().max())
        vaults = pd.DataFrame({a: curves[g["Position id"]].sum(axis=1) for a, g in metadata.groupby("Address")})
        profits = vaults.iloc[-1].sort_values(ascending=False)
        leader = profits.index[0]
        names = metadata.groupby("Address").Vault.first()
        best = daily.idxmax()
        removed = daily.copy()
        removed.loc[best] = 0.0
        no_leader = calculate_returns(equity - vaults[leader])
        rows.append({"Configuration": name, "Best day": best, "Best day return": daily.loc[best], "Excess kurtosis": daily.kurt(), "Leading vault": names[leader], "Leading vault profit (USD)": profits.iloc[0], "Leader share of positive vault PnL": profits.iloc[0] / profits.clip(lower=0).sum(), "Sharpe with best day zeroed": calculate_sharpe(removed, periods=365), "Sharpe without leader (fixed ledger)": calculate_sharpe(no_leader, periods=365), "CAGR without leader (fixed ledger)": calculate_cagr(no_leader), "Attribution residual (USD)": residual.abs().max()})
        for address, value in profits.head(5).items():
            contributors.append({"Configuration": name, "Vault": names[address], "Address": address, "Profit (USD)": value, "Curator quality": getattr(quality.get(address), "value", "unrated"), "Curator excluded": address in EXCLUDED_VAULTS})
        pnl = vaults.diff().fillna(vaults.iloc[0])
        snapshots = pd.DatetimeIndex(run["equity"].index).normalize()
        for date in daily.nlargest(3).index:
            prior = snapshots[snapshots < date]
            previous = prior[-1] if len(prior) else date - pd.Timedelta(days=1)
            gains = pnl.loc[date].sort_values(ascending=False)
            top = gains.index[0]
            row = {"Configuration": name, "Date": date, "Previous valuation": previous, "Portfolio return": daily.loc[date], "Leading vault": names[top], "Leading vault PnL (USD)": gains.iloc[0], "Leading share of positive day PnL": gains.iloc[0] / gains.clip(lower=0).sum() if gains.clip(lower=0).sum() else np.nan, "Quarantined": is_quarantined(top, date), "Curator excluded": top in EXCLUDED_VAULTS}
            for symbol, prices in market.items():
                row[symbol + " interval return"] = prices.asof(date) / prices.asof(previous) - 1
            jumps.append(row)
        metadata["Configuration"] = name
        positions.append(metadata.sort_values("Final profit (USD)", ascending=False).head(3))
    return pd.DataFrame(rows), pd.DataFrame(contributors), pd.DataFrame(jumps), pd.concat(positions, ignore_index=True)


def quarter_frame(runs):
    """Use compounded daily returns, with the partial final quarter retained."""
    return pd.DataFrame({name: (1 + run["daily_returns"]).resample("QE").prod() - 1 for name, run in runs.items()}).T


def quarterly_figure(runs):
    """Compare predeclared paths using a shared zero-centred quarterly colour scale."""
    frame = quarter_frame(runs)
    labels = [f"{d.year} Q{d.quarter}" + (" (partial)" if d.quarter == 4 else "") for d in frame.columns]
    z = frame.values * 100
    text = np.array([[f"{v:.1f}%" for v in row] for row in z])
    bound = max(np.nanmax(np.abs(z)), 1e-6)
    return go.Figure(go.Heatmap(z=z, x=labels, y=frame.index, text=text, texttemplate="%{text}", textfont=dict(shadow="auto"), colorscale="RdYlGn", zmin=-bound, zmax=bound, colorbar=dict(title="Return (%)"))).update_layout(title="Quarterly portfolio returns of predeclared paths", width=1450, height=550, template="plotly_white", yaxis=dict(autorange="reversed"), margin=dict(t=100, l=230, b=60, r=90))


def update_findings(path, frame, control, drift, robustness, ties, cash, ic, long_count, benchmark_note=None):
    """Write findings only from completed experiment 05 executions."""
    import html

    period = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
    primary = frame[~frame.name.str.startswith("Tie seed")]
    best = primary.sort_values("CAGR", ascending=False).iloc[0]
    best_sharpe = primary.sort_values("Sharpe", ascending=False).iloc[0]
    baseline = control["metrics"]
    joint = primary[(primary.CAGR > baseline["CAGR"]) & (primary.Sharpe > baseline["Sharpe"]) & (primary["Maximum drawdown"] >= baseline["Maximum drawdown"])]
    baseline_name = control["config"].name
    findings = f"""## Key new insights

- **Same-data benchmark:** the fresh original-formula control has {baseline['CAGR']:.2%} CAGR, {baseline['Sharpe']:.2f} Sharpe and {baseline['Maximum drawdown']:.2%} maximum drawdown. It reproduces source v11 equity and every trade.
- **Highest observed CAGR:** {best['Configuration']} gives {best.CAGR:.2%} CAGR, {best.Sharpe:.2f} Sharpe and {best['Maximum drawdown']:.2%} drawdown. This ranking excludes tie-seed diagnostics.
- **Highest observed Sharpe:** {best_sharpe['Configuration']} gives {best_sharpe.Sharpe:.2f} Sharpe and {best_sharpe.CAGR:.2%} CAGR. {len(joint)} tested treatment rows improve CAGR and Sharpe with no worse drawdown than the current control; equivalent paths may repeat.
- **Clipping ties:** {ties['Maximum score fraction']:.1%} of baseline funded observations have maximum composite score; {ties['Dates with at least two funded maximum-score vaults']:.1%} of decisions fund at least two such vaults. Tie ordering must be treated as a robustness check.
- **Benchmark discrepancy:** {benchmark_note or 'The current source differs from the earlier saved benchmark. Compare matched raw inputs, readers and deposit admission before attributing the difference to strategy rules.'}

## Summary of results

### Matched strategy comparisons — {period}

Completed real engine backtests with six inverse-variance positions. Includes the source-equivalent control, predeclared scoring/cash pairs and the strongest observed treatment; tie seeds are excluded from winner selection. All metrics are net of source-modelled costs.

"""
    names = [baseline_name, "Blend 46d", "Smooth C1 S3", baseline_name + " / refill", "Blend 46d / refill", "Smooth C1 S3 / refill", best["Configuration"], best_sharpe["Configuration"]]
    view = frame.set_index("Configuration").loc[list(dict.fromkeys(names)), ["CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Trades"]].reset_index()
    for c in ["CAGR", "Maximum drawdown", "Mean cash weight"]:
        view[c] = view[c].map(lambda v: f"{v:.2%}")
    view.Sharpe = view.Sharpe.map(lambda v: f"{v:.2f}")

    def table(df):
        return "| " + " | ".join(df.columns) + " |\n| " + " | ".join(["---"] * len(df.columns)) + " |\n" + "\n".join("| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |" for row in df.itertuples(index=False, name=None))

    findings += table(view)
    findings += f"""\n\n## Robustness of results

The 18 score calibrations, 11 mechanism diagnostics and {long_count} predeclared full-history confirmations completed. Default tables and charts use the 2026 period; full-history performance is retained separately. Results are exploratory comparisons over previously inspected history, not an untouched holdout. Feature labels use strictly future NAV outcomes, are censored at the report end and are never used to tune backtest parameters in this notebook. Feature IC uncertainty bands resample overlapping decision dates in blocks and remain exploratory.

Source replication passes the equity and complete-ledger checks. Every backtest holds at most six vaults. Refill targets remain within the source fresh budget and concentration/TVL ceilings; deposit checks, pinned holdings and ordinary execution bands can prevent intended dollars from becoming realised exposure. Position attribution reconciles to equity with a largest residual of {robustness['Attribution residual (USD)'].max():.2e} USD.

"""
    for name in list(dict.fromkeys([baseline_name, best["Configuration"], best_sharpe["Configuration"]])):
        r = robustness[robustness.Configuration.eq(name)].iloc[0]
        findings += f"- **{name}:** leading vault {r['Leading vault']} supplies {r['Leader share of positive vault PnL']:.1%} of positive vault profits. Best day {str(r['Best day'])[:10]} returns {r['Best day return']:.2%}; excess kurtosis {r['Excess kurtosis']:.2f}. Zeroing that return gives Sharpe {r['Sharpe with best day zeroed']:.2f}; removing the leader PnL on the fixed ledger gives Sharpe {r['Sharpe without leader (fixed ledger)']:.2f}. These sensitivities retain the original trading path.\n"
    refill = cash[cash.Configuration.str.endswith("/ refill")]
    findings += "\n"
    for _, r in refill.iterrows():
        findings += f"- **{r.Configuration}:** mean recovered target is {r['Mean recovered target / budget']:.2%} of fresh budget, on {int(r['Refill decisions'])} decisions; realised mean cash is {r['Mean cash weight']:.2%}. A target-budget recovery is not a guaranteed reduction in realised cash.\n"
    findings += "\nThe expanded attribution tables show the largest days alongside matching Binance BTC/ETH intervals and curator annotations. Gross NAV labels do not include the strategy's redemption costs. Flat or carried NAV, weak long-window coverage, current membership/guard assumptions and incomplete historical deposit permissions can affect feature diagnostics. The clip, selector and tie grid is bounded; no claim of a global optimum is made.\n"
    notebook = nbformat.read(path, 4)
    notebook.cells[0].source = notebook.cells[0].source.split("## Key new insights")[0] + findings
    nbformat.write(notebook, path)
    Path(path).with_suffix(".md").write_text("# Experiment 05 — scoring, selection and cash deployment\n\n[Executed notebook](" + Path(path).name + ").\n\n" + findings)
    return best["Configuration"]


def search_space_figure(frame):
    """Show risk/return trade-offs with mechanism families and tied-score probes."""
    frame = frame.copy()
    frame["Family"] = np.select([frame.name.str.startswith("Tie seed"), frame.refill, frame.feasible_entry, frame.ratio_floor | frame.missing_zero | frame.minimum_nonflat.gt(0)], ["Tie sensitivity", "Cash refill", "Selector", "Data policy"], default="Scoring")
    colours = {"Scoring": "#2563eb", "Cash refill": "#ea580c", "Selector": "#16a34a", "Data policy": "#9333ea", "Tie sensitivity": "#737373"}
    pairs = [("CAGR", "Sharpe"), ("CAGR", "Maximum drawdown"), ("Sharpe", "Maximum drawdown")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=["CAGR / Sharpe", "CAGR / maximum drawdown", "Sharpe / maximum drawdown"], horizontal_spacing=0.1)
    for col, (x, y) in enumerate(pairs, 1):
        for family, group in frame.groupby("Family", sort=False):
            xv = group[x] * (1 if x == "Sharpe" else 100)
            yv = group[y] * (1 if y == "Sharpe" else 100)
            fig.add_trace(go.Scatter(x=xv, y=yv, mode="markers", name=family, legendgroup=family, showlegend=col == 1, text=group.Configuration, hovertemplate="%{text}<br>x=%{x:.2f}; y=%{y:.2f}<extra></extra>", marker=dict(color=colours[family], size=11, symbol="circle-open" if family == "Tie sensitivity" else "circle", line=dict(width=1))), row=1, col=col)
        control = frame[frame.Configuration.eq("Hard C1 S3")].iloc[0]
        fig.add_trace(go.Scatter(x=[control[x] * (1 if x == "Sharpe" else 100)], y=[control[y] * (1 if y == "Sharpe" else 100)], mode="markers", name="Exact source control", legendgroup="control", showlegend=col == 1, marker=dict(size=17, color="black", symbol="star")), row=1, col=col)
        fig.update_xaxes(title=x + (" (%)" if x != "Sharpe" else ""), row=1, col=col)
        fig.update_yaxes(title=y + (" (%)" if y != "Sharpe" else ""), row=1, col=col)
    fig.update_layout(title="Scoring, cash and selector risk/return clusters", width=1500, height=600, template="plotly_white", legend=dict(orientation="h", y=-0.2), margin=dict(t=120, b=130, l=90, r=40))
    return fig
