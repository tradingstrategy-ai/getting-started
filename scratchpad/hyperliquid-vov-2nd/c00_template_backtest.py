"""C00 backtest and NB160 reports with the corrected NB20 accounting."""

import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display
from tqdm_loggable.auto import tqdm

import clean_c00_v11_comparison as common
from allocation_comparison import robustness
from capital_allocation_report import fee_accounting
from tradeexecutor.state.state import State
from tradeexecutor.strategy.execution_context import notebook_execution_context
from tradeexecutor.strategy.chart.renderer import ChartBacktestRenderingSetup
from tradeexecutor.strategy.chart.standard.alpha_model import alpha_model_diagnostics
from tradeexecutor.strategy.chart.standard.weight import weight_allocation_statistics
from tradeexecutor.strategy.chart.standard.trading_metrics import trading_metrics
from tradeexecutor.strategy.chart.standard.interest import vault_statistics

ROOT = common.ROOT
PERIODS = common.PERIODS
LABELS = common.LABELS
NOTEBOOK = ROOT / "23-backtest-c00.ipynb"
COLOURS = common.COLOURS
METRICS = ["Final equity (USD)", "Net profit (USD)", "Cumulative return", "CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown"]


def initialise():
    """Keep frozen inputs and write this notebook's artefacts separately."""
    data, evaluator = common.initialise()
    reference_notebook = json.loads(common.NOTEBOOK.read_text())
    reference = Path(reference_notebook["metadata"]["nb20"]["artifact_generation"])
    saved = json.loads((reference / "manifest.json").read_text())
    assert json.loads(json.dumps(data["manifest"]["identity"], default=str)) == saved["identity"], "NB20 inputs or source changed"
    identity = {"version": "nb23-v1", "nb20": saved["identity"], "reference": str(reference), "template": "scratchpad/vault-of-vaults/160-backtest-hyperliquid-low-value-treasury-test.ipynb", "code": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in ["c00_template_backtest.py", "create_c00_template_notebook.py"]}}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/23" / key
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=key, figures=[], nb23_reference=reference)
    data["manifest"].update(identity=identity, fingerprint=key)
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data, evaluator


def run_accounts(data, evaluator, run_c00):
    """Run the declared C00 callback and source v11 under the common convention."""
    records, runs, attribution, weights, audits, parity = [], {}, {}, {}, [], []
    expected = pd.read_csv(data["nb23_reference"] / "results.csv").set_index(["Period", "Arm"])
    for period, arm in tqdm([(p, a) for p in PERIODS for a in ("C00", "V11")], desc="C00 and v11 backtests", mininterval=15):
        print(f"{period} / {arm}; estimated remaining {max(0.1, evaluator.remaining(4-len(records))):.1f} minutes", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            run = run_c00(period) if arm == "C00" else common.v11_replay(data, evaluator, period)
        metrics, vaults, absolute = common.core.engine.analyse_run(data, run, arm, period)
        metrics["Cumulative return"] = metrics["Final equity (USD)"] / 150000 - 1
        metrics["Calmar"] = metrics["CAGR"] / abs(metrics["Maximum drawdown"]) if metrics["Maximum drawdown"] < 0 else np.nan
        reserve = run["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        metrics["September cash"] = float(absolute.loc["2026-09-01":"2026-09-30", reserve].mean())
        metrics["Mean vaults held"] = float(absolute.drop(columns=reserve).gt(1e-8).sum(axis=1).mean())
        assert metrics["Maximum vaults held"] <= 6
        old_equity = pd.read_csv(data["nb23_reference"] / f"{period}-{arm}-equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
        new_equity = run["equity"].resample("D").last().ffill()
        assert old_equity.index.equals(new_equity.index)
        error = float((old_equity - new_equity).abs().max())
        assert error < 1e-6, (period, arm, error)
        for metric in METRICS:
            assert abs(metrics[metric] - expected.loc[(period, arm), metric]) < 1e-6, (period, arm, metric)
        old_state = State.read_json_file(data["nb23_reference"] / "engine" / f'{run["cache_key"]}-state.json')
        signature = common.core.trade_signature(run)
        assert signature == common.core.trade_signature({"result": type("SavedResult", (), {"state": old_state})()}), (period, arm, "trade parity")
        parity.append({"Period": period, "Strategy": arm, "Maximum equity difference (USD)": error, "Matching successful trades": len(signature), "All metrics match": True})
        records.append(dict(Period=period, Arm=arm, **metrics))
        runs[(period, arm)], attribution[(period, arm)], weights[(period, arm)] = run, vaults, absolute
        audits.append(common.core.parent.audit(data, run, arm, period))
        pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
    pd.concat(audits, ignore_index=True).to_csv(data["artifact"] / "fill-audit.csv", index=False)
    pd.DataFrame(parity).to_csv(data["artifact"] / "nb20-parity.csv", index=False)
    pd.DataFrame(data["funding_ledger"]).to_csv(data["artifact"] / "funding.csv", index=False)
    return pd.DataFrame(records), runs, attribution, weights


def prepare(data, evaluator, results, runs, attribution, weights):
    """Use framework accounting, charts and curator checks for the reports."""
    robust, tails = robustness(data, results, runs, attribution)
    fees = fee_accounting(data, runs)
    renderers = {}
    for key, run in runs.items():
        period, arm = key
        registry = evaluator.strategy.create_charts(None, run["parameters"], evaluator.universe, notebook_execution_context)
        renderers[key] = ChartBacktestRenderingSetup(registry=registry, strategy_input_indicators=evaluator.indicators, state=run["result"].state, backtest_start_at=PERIODS[period][0], backtest_end_at=PERIODS[period][1])
    return dict(data=data, evaluator=evaluator, results=results, runs=runs, attribution=attribution, weights=weights, robust=robust, tails=tails, fees=fees, renderers=renderers)


def show_table(frame, formats=None, limit=None):
    """Render compact tables while keeping full rows in the artefact files."""
    if not isinstance(frame, pd.DataFrame):
        display(frame)
        return
    if not isinstance(frame.index, pd.RangeIndex) or frame.index.name is not None:
        frame = frame.reset_index()
    if limit and len(frame) > limit:
        frame = pd.concat([frame.head(limit // 2), frame.tail(limit - limit // 2)])
    display(frame.style.format(formats or {}, na_rep="Unavailable").hide(axis="index"))


def table(context, kind, period="2026"):
    data, run = context["data"], context["runs"][(period, "C00")]
    state, w = run["result"].state, context["weights"][(period, "C00")]
    metrics = context["results"].query('Period == @period and Arm == "C00"').iloc[0]
    if kind == "metrics":
        f = metrics[METRICS].to_frame("C00")
        display(metric_style(f))
    elif kind == "cash":
        positions = [p for p in state.portfolio.get_open_positions() if not p.is_credit_supply()]
        cash, invested = float(state.portfolio.get_cash()), sum(float(p.get_value()) for p in positions)
        assert abs(cash + invested - run["equity"].iloc[-1]) < 0.02
        show_table(pd.DataFrame([{"Final date": str(run["equity"].index[-1].date()), "Cash (USD)": cash, "Invested (USD)": invested, "Equity (USD)": cash + invested, "Cash weight": cash / (cash + invested), "Open vaults": len(positions)}]), {"Cash (USD)": "USD {:,.2f}", "Invested (USD)": "USD {:,.2f}", "Equity (USD)": "USD {:,.2f}", "Cash weight": "{:.1%}"})
    elif kind == "utilisation":
        show_table(pd.DataFrame([{"Mean cash": metrics["Mean cash weight"], "September cash": metrics["September cash"], "Mean vaults held": metrics["Mean vaults held"], "Maximum vaults held": metrics["Maximum vaults held"], "Largest vault weight": metrics["Largest vault weight"]}]), {"Mean cash": "{:.1%}", "September cash": "{:.1%}", "Mean vaults held": "{:.2f}", "Largest vault weight": "{:.1%}"})
    elif kind == "weights":
        show_table(context["renderers"][(period, "C00")].render(weight_allocation_statistics))
    elif kind == "positions":
        rows = [{"Position": p.position_id, "Vault": p.pair.get_vault_name(), "Opened": str(p.opened_at.date()), "Value (USD)": float(p.get_value()), "Weight": float(p.get_value()) / run["equity"].iloc[-1]} for p in state.portfolio.get_open_positions() if not p.is_credit_supply()]
        show_table(pd.DataFrame(rows).sort_values("Value (USD)", ascending=False), {"Value (USD)": "USD {:,.2f}", "Weight": "{:.1%}"})
    elif kind == "thinking":
        from IPython.display import Markdown

        messages = state.visualisation.get_messages_tail(1)
        display(Markdown("<details><summary>Last decision log</summary>\n\n```text\n" + "\n".join(str(v) for v in messages.values()) + "\n```\n\n</details>"))
    elif kind == "alpha":
        f = context["renderers"][(period, "C00")].render(alpha_model_diagnostics)
        if f.empty:
            ledger = run["allocation_df"]
            f = ledger.loc[ledger.Date.eq(ledger.Date.max())].copy()
        if isinstance(f.columns, pd.MultiIndex):
            f.columns = [" ".join(str(x) for x in col if str(x)) for col in f.columns]
        show_table(f, limit=12)
    elif kind == "trades":
        f = context["renderers"][(period, "C00")].render(trading_metrics)
        show_table(f, limit=24)
    elif kind == "vaults":
        f = context["renderers"][(period, "C00")].render(vault_statistics)
        show_table(f, limit=12)
    elif kind == "profit":
        f = context["attribution"][(period, "C00")].sort_values(ascending=False).rename("Profit (USD)").rename_axis("Vault").reset_index()
        show_table(f, {"Profit (USD)": "USD {:+,.2f}"}, limit=16)
    elif kind == "position_list":
        f = pd.read_parquet(data["artifact"] / f"{period}-C00-positions.parquet").sort_values("Final profit (USD)", ascending=False)
        show_table(f, {"Final profit (USD)": "USD {:+,.2f}"}, limit=16)
    elif kind == "fees":
        f = context["fees"].query('Period == @period and Arm == "C00"').drop(columns=["Period", "Arm"]).T
        f.columns = ["C00"]
        display(f.style.format("USD {:,.2f}"))
    elif kind == "robust":
        f = context["robust"].query('Period == @period and Arm == "C00"').drop(columns=["Period", "Arm"])
        show_table(f, {"Best update": "{:.2%}", "Excess kurtosis": "{:.2f}", "Top positive profit share": "{:.1%}"})
    elif kind == "tail":
        f = context["tails"].query('Period == @period and Arm == "C00"').drop(columns=["Period", "Arm", "First_mark", "Last_mark"])
        show_table(f, {"Update profit (USD)": "USD {:,.0f}", "NAV_return": "{:+.2%}", "Interval_days": "{:.2f}", "BTCUSDT return": "{:+.2%}", "ETHUSDT return": "{:+.2%}"})
    elif kind == "comparison":
        f = context["results"].query("Period == @period").set_index("Arm").loc[["C00", "V11"], METRICS].T
        display(metric_style(f, colour=True))
    elif kind == "comparison_cash":
        names = ["Mean cash weight", "September cash", "Mean vaults held", "Maximum vaults held", "Largest vault weight", "Trades", "Gross trade turnover (USD)"]
        f = context["results"].query("Period == @period").set_index("Arm").loc[["C00", "V11"], names].T
        display(metric_style(f))
    elif kind == "parity":
        show_table(pd.read_csv(data["artifact"] / "nb20-parity.csv"), {"Maximum equity difference (USD)": "USD {:.9f}"})
    else:
        raise ValueError(kind)


def metric_style(frame, colour=False):
    style = frame.style
    percentages = {"Cumulative return", "CAGR", "Maximum drawdown", "Mean cash weight", "September cash", "Largest vault weight"}
    for name in frame.index:
        fmt = "USD {:,.2f}" if "(USD)" in name else "{:.2%}" if name in percentages else "{:,.0f}" if name in {"Trades", "Maximum vaults held"} else "{:.3f}"
        style = style.format(fmt, subset=pd.IndexSlice[[name], :])
        if colour and name in METRICS:
            style = style.background_gradient(cmap="RdYlGn", axis=1, subset=pd.IndexSlice[[name], :])
    return style


def save_figure(context, fig, name, period):
    fig.tight_layout()
    path = context["data"]["artifact"] / f"{period}-{name}.png"
    fig.savefig(path, dpi=115, bbox_inches="tight")
    display(fig)
    plt.close(fig)
    context["data"]["figures"].append(str(path))


def chart(context, kind, period="2026", arm="C00", compare=False):
    run = context["runs"][(period, arm)]
    w = context["weights"][(period, arm)]
    reserve = run["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
    title = f"{arm}: " + LABELS[period]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    if kind in ("equity", "drawdown", "cash", "rolling_return", "rolling_sharpe"):
        for a in ("C00", "V11") if compare else (arm,):
            r = context["runs"][(period, a)]
            eq, returns = r["equity"], r["daily_returns"]
            if kind == "equity":
                series = eq / 1000
            elif kind == "drawdown":
                series = (eq / eq.cummax() - 1) * 100
            elif kind == "cash":
                series = context["weights"][(period, a)][reserve] * 100
            elif kind == "rolling_return":
                series = ((1 + returns).rolling(90, min_periods=90).apply(np.prod, raw=True) - 1) * 100
            else:
                window = returns.rolling(90, min_periods=90)
                series = (window.mean() / window.std(ddof=1) * np.sqrt(365)).where(window.std(ddof=1) > 0)
            ax.plot(series.index, series, label=a, color=COLOURS[a], lw=1.6)
        labels = {"equity": ("Equity curve", "Equity (USD thousands)"), "drawdown": ("Drawdown", "Drawdown (%)"), "cash": ("Unallocated cash", "Cash / equity (%)"), "rolling_return": ("90-day compounded return", "Return (%)"), "rolling_sharpe": ("90-day Sharpe", "Sharpe")}
        title, ylabel = labels[kind]
        ax.set(ylabel=ylabel)
        if kind == "cash":
            ax.set_ylim(0, 100)
        if compare:
            ax.legend()
    elif kind in ("asset", "absolute"):
        # Same vault order and colours make comparison of the two accounts readable.
        pooled = pd.concat([context["weights"][(period, a)].drop(columns=reserve).mean() for a in ("C00", "V11")], axis=1).fillna(0).mean(axis=1)
        names = list(pooled.nlargest(8).index)
        panel = w.reindex(columns=names, fill_value=0).copy()
        panel["Other vaults"] = w.drop(columns=names + [reserve], errors="ignore").sum(axis=1)
        panel["Cash"] = w[reserve]
        assert np.allclose(panel.sum(axis=1), 1, atol=1e-6)
        colours = [plt.get_cmap("tab20")(i) for i in range(len(names))] + ["#9ca3af", "#e5e7eb"]
        if kind == "asset":
            panel = panel.mul(run["equity"].resample("D").last().ffill(), axis=0) / 1000
        else:
            panel = panel * 100
        ax.stackplot(panel.index, *[panel[c].to_numpy() for c in panel], labels=panel.columns, colors=colours, step="post")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
        ax.set(ylabel="Equity (USD thousands)" if kind == "asset" else "Holding / total equity (%)")
        if kind == "absolute":
            ax.set_ylim(0, 100)
        title = f"{arm}: " + ("Equity by asset" if kind == "asset" else "Absolute asset weights")
    elif kind == "chain":
        # The simulated account has a single chain; supporting benchmark pairs are not holdings.
        ax.plot(run["equity"].index, run["equity"] / 1000, label="Hyperliquid", color=COLOURS[arm])
        ax.set(ylabel="Equity (USD thousands)")
        ax.legend()
        title = "Equity by chain"
    elif kind in ("monthly", "quarterly"):
        start, end = map(pd.Timestamp, PERIODS[period])
        returns = run["daily_returns"].loc[lambda series: (series.index >= start) & (series.index < end)]
        if kind == "monthly":
            values = (1 + returns).groupby(returns.index.to_period("M")).prod() - 1
            f = values.rename("Return").to_frame()
            f["Year"] = f.index.year
            f["Month"] = f.index.month
            matrix = f.pivot(index="Year", columns="Month", values="Return").reindex(columns=range(1, 13))
            xlabels = list("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())
            ylabels = list(matrix.index.astype(str))
            title = "Monthly returns"
        else:
            matrix = pd.DataFrame({a: (1 + context["runs"][(period, a)]["daily_returns"]).groupby(context["runs"][(period, a)]["daily_returns"].index.to_period("Q")).prod() - 1 for a in ("C00", "V11")}).T
            start, end = map(pd.Timestamp, PERIODS[period])
            xlabels = [str(t) + ("*" if start > t.start_time or end - pd.Timedelta(days=1) < t.end_time.floor("D") else "") for t in matrix.columns]
            ylabels = list(matrix.index)
            title = "Quarterly returns"
        z = matrix.to_numpy() * 100
        fig.set_size_inches(11, max(2.5, 1.5 + 0.55 * len(matrix)))
        limit = max(1, float(np.nanmax(np.abs(z))))
        cmap = plt.get_cmap("RdYlGn").copy()
        cmap.set_bad("#ececec")
        im = ax.imshow(z, cmap=cmap, vmin=-limit, vmax=limit, aspect="auto")
        ax.grid(False)
        ax.set_xticks(range(len(xlabels)), xlabels, rotation=35 if kind == "quarterly" else 0, ha="right" if kind == "quarterly" else "center")
        ax.set_yticks(range(len(ylabels)), ylabels)
        for i in range(z.shape[0]):
            for j in range(z.shape[1]):
                if np.isfinite(z[i, j]):
                    rgba = cmap(im.norm(z[i, j]))
                    light = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
                    ax.text(j, i, f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=9, color="white" if light < 0.5 else "black")
        fig.colorbar(im, ax=ax, label="Return (%)")
    elif kind == "selection":
        counts = w.drop(columns=reserve).gt(1e-8).sum(axis=1)
        ax.step(counts.index, counts, where="post", label="Funded vaults", color=COLOURS[arm])
        ax.axhline(6, color="#6b7280", ls="--", label="Maximum positions")
        ax.set(ylim=(0, 7), ylabel="Vault count")
        ax.legend()
        title = "Funded positions"
    elif kind == "contributors":
        gap = context["attribution"][(period, "C00")].subtract(context["attribution"][(period, "V11")], fill_value=0)
        chosen = gap.loc[gap.abs().nlargest(10).index].sort_values()
        ax.barh(chosen.index, chosen / 1000, color=np.where(chosen >= 0, COLOURS["C00"], COLOURS["V11"]))
        ax.axvline(0, color="#555", lw=0.8)
        ax.set(xlabel="C00 minus v11 profit (USD thousands)")
        title = "Vault profit difference"
    else:
        raise ValueError(kind)
    if kind not in ("monthly", "quarterly"):
        ax.grid(alpha=0.2)
    ax.set_title(title + "\n" + LABELS[period])
    save_figure(context, fig, f"{arm}-{kind}" + ("-comparison" if compare else ""), period)


def finish(context):
    """Write findings and the exact generation for notebook finalisation."""
    from IPython.display import Markdown

    data = context["data"]
    f = context["results"].set_index(["Period", "Arm"])
    rows = []
    for period in PERIODS:
        for arm in ("C00", "V11"):
            r = f.loc[(period, arm)]
            rows.append(f'| {period} | {arm} | USD {r["Final equity (USD)"]:,.0f} | {r.CAGR:.2%} | {r.Sharpe:.3f} | {r["Maximum drawdown"]:.2%} |')
    robust = context["robust"].query('Arm == "C00"').set_index("Period")
    header = """# C00 Hyperliquid vault strategy

Based on [NB20](20-backtest-c00-vs-v11.ipynb), using the outline of [NB160](../vault-of-vaults/160-backtest-hyperliquid-low-value-treasury-test.ipynb).

C00 ranks vaults with four clipped performance components and allocates to up to six vaults using a regularised 90-day risk estimate and a capacity waterfall. This notebook presents its fixed rules and compares them with `hyper-ai-v11.py`.

Each account starts with USD 150,000. The 2026 backtest runs from **1 January to 4 October 2026**; full history runs from **1 March 2023 to 7 October 2026**, with a partial final archive day. Both retain all preceding indicator warmup.

## Key new insights

All four accounts reproduce NB20's complete equity paths, successful trade sequences and key metrics. This notebook adds a single-strategy reporting layout; it introduces no new strategy configuration.

C00 earns more and has higher Sharpe in both periods. Its full-history drawdown is deeper. The comparison changes ranking, risk estimation and allocation together, so it does not identify which change produced the gain.

## Summary of results

| Period | Strategy | Final equity | CAGR | Sharpe | Maximum drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
""" + "\n".join(rows) + "\n\n## Robustness of results\n\n"
    for period in PERIODS:
        r = robust.loc[period]
        header += f'{period} C00: {r.Top_vault} contributes {r["Top positive profit share"]:.1%} of positive vault profit. The best daily update is {r["Best update"]:.2%}; excess kurtosis is {r["Excess kurtosis"]:.1f}.\n\n'
    header += """The strongest NAV updates are compared with BTC and ETH over the actual observation intervals and checked against curator exclusions and quarantine. Sparse NAV can bunch returns, and the recorded NAV does not establish the live executable price. These are previously researched, overlapping periods with retrospective universe and guard selection.

Both strategies use the same partial-sale fee correction, entry-tax reset and final-proceeds funding. Charges model 10% of positive redemption profit plus a 0.1% capital allowance; that allowance is an inherited assumption. The v11 comparison runs the local module's rules with these shared research corrections, rather than reproducing recorded live decisions.
"""
    (data["artifact"] / "final-header.md").write_text(header)
    (ROOT / "23-c00-backtest-findings.md").write_text(header)
    (data["artifact"] / "figures.json").write_text(json.dumps(data["figures"], indent=2))
    (data["artifact"] / "complete.json").write_text(json.dumps({"status": "complete", "accounts": 4, "engine_calls": context["evaluator"].engine_calls, "figures": len(data["figures"])}, indent=2))
    display(Markdown(f'<!-- nb23-generation: {data["artifact"]} -->\n\nCompleted four matched accounts and NB20 replication checks.'))
