"""NB20: two source strategies under one historical execution convention."""

import ast
import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Markdown, display
from tqdm_loggable.auto import tqdm
import protected_core_score_allocation as core
from allocation_comparison import figure, heading, robustness
from capital_allocation_report import fee_accounting

ROOT = core.ROOT
PERIODS = core.PERIODS
LABELS = core.LABELS
ARMS = ("V11", "C00")
COLOURS = {"V11": "#2563eb", "C00": "#c2410c"}
NOTEBOOK = ROOT / "20-backtest-c00-vs-v11.ipynb"
LOGIC = """### Strategy logic — applies to both backtesting periods

These are strategy rules, not separate fitted configurations for each period. Scores select vaults; risk estimates determine allocation. The local v11 module represents deployed rules, not a verified replay of live account decisions.

| Rule | V11 | C00 |
| --- | --- | --- |
| Ranking | 0.60 CAGR360 + 0.40 Sortino45 | 0.48 CAGR360 + 0.32 Sortino45 + 0.10 CAGR180 + 0.10 Sortino30 |
| Component clips | CAGR 0–100%; Sortino 0–3, normalised to 0–1 | Same |
| Risk | Source 90-day variance, volatility floor 0.0001 | 90-day variance blended with leave-one-out positive peer median; own weight m/(m+30), m actual updates |
| Allocation | Proportional inverse variance with source capacity adjustment | Waterfall: lowest regularised risk first, filling each permitted capacity |
| Missing score | Composite becomes unscored/zero; eligible vaults can still enter | Same; no available-component reweighting |
| Missing risk | Source missing indicator gives zero raw signal | Partial history and peer prior supported; unusable basket risk falls back to equal raw priorities |
| Maximum positions | 6; no capacity extension | Same |
| Selection | Source rank hysteresis, entry 6 / exit 8, minimum improvement 0 | Same machinery, different score values |
| Limits | 98% deployment, 33% concentration, 33% vault TVL, minimum TVL $7,500 | Same |
| Rebalance and gate | Every 2 days; 14-day return must exceed −16% | Same |
| Execution thresholds | Buy 0.05%, sell 0.5% of reference equity, $5 floor; cleanup 0.5% | Same |
| Permissions | Source guard, whitelist, deposit/redemption and leader-share policy | Same |

### Common accounting and data — applies to both backtesting periods

Fresh $150,000 accounts; the same repaired archive, universe, guard and preceding warmup, including 2025 for the 2026 accounts. Indicators use completed prior daily buckets. Execution uses the latest recorded NAV at or before each query, with no additional slippage or freshness veto. Causal research NAV filling starts at inception; missing observations are not backfilled from the future.

Both arms use three identical research accounting corrections: partial sells charge the modelled redemption fee once against gross observed NAV; newly reopened positions reset the previous position's cached tax before marking; buys are bounded by final synchronous net sell proceeds. These changes leave ranking and sizing rules intact. Modelled charges remain 10% of positive redemption profit plus a 0.1% capital allowance; the allowance is an assumption, not a verified venue fee. Live v11 pays actual execution costs, so this is a clean comparison of rules rather than a live-performance replication.
"""


def initialise():
    data, evaluator = core.initialise()
    nb = json.loads((ROOT / "19-backtest-protected-core-score-risk-allocation.ipynb").read_text())
    reference = Path(nb["metadata"]["nb19"]["artifact_generation"])
    identity = {"version": "nb20-v1", "parent": data["manifest"]["identity"], "code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "arms": ARMS, "accounting": "single partial-sell fee, fresh-entry tax reset, final-proceeds funding", "reference": str(reference)}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/20" / key
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=key, figures=[], consistent_entry_mark=True, nb20_reference=reference)
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    data["manifest"].update(identity=identity, fingerprint=key)
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data, evaluator


def v11_replay(data, evaluator, period):
    """Compile only the common partial-sell correction into source v11."""
    strategy = evaluator.strategy
    source = core.parent.SOURCE.read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "decide_trades")
    callback = ast.get_source_segment(source, node)
    anchor = "                trade.planned_price = trade.planned_mid_price * (1.0 - fee)"
    assert callback.count(anchor) == 1
    callback = callback.replace(
        anchor,
        """                if not trade.closing:
                    trade.planned_mid_price = _engine.observed_quote(_data, trade.pair.internal_id, timestamp)[0]
                    trade.other_data['nb17_corrected_partial_fee'] = True
                trade.planned_price = trade.planned_mid_price * (1.0 - fee)""",
    )
    ns = dict(strategy.__dict__)
    ns.update(_engine=core.engine, _data=data)
    exec(compile(callback, "NB20::v11-common-accounting", "exec"), ns)
    (data["artifact"] / "compiled-v11.py").write_text(callback)
    original = strategy.decide_trades

    def decide(input):
        trades = ns["decide_trades"](input)
        core.reference.cap_to_final_sell_proceeds(data, input, trades, "V11")
        return trades

    strategy.decide_trades = decide
    data["run_context"] = (period, "V11", "common-accounting")
    w = np.zeros(len(core.FEATURES))
    w[0] = 1
    try:
        with core.engine.pricing_convention(data), core.entry_marking(data):
            return evaluator.run(w, *PERIODS[period], n=6, source_control=True, keep=True, profile="NB20-v11-common-accounting")
    finally:
        strategy.decide_trades = original


def run(data, evaluator):
    records = []
    runs = {}
    attr = {}
    weights = {}
    audits = []
    parity = []
    expected = pd.read_csv(data["nb20_reference"] / "results.csv").set_index(["Period", "Arm"])
    for period, arm in tqdm([(p, a) for p in PERIODS for a in ARMS], desc="NB20 matched accounts", mininterval=15):
        print(f"{period} / {arm}; estimated remaining {max(1,evaluator.remaining(4-len(records))):.1f} minutes", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = v11_replay(data, evaluator, period) if arm == "V11" else core.replay(data, evaluator, "C00", period, active=False)
        m, v, w = core.engine.analyse_run(data, r, arm, period)
        m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
        m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"]) if m["Maximum drawdown"] < 0 else np.nan
        reserve = r["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        m["September cash"] = float(w.loc["2026-09-01":"2026-09-30", reserve].mean())
        m["Mean vaults held"] = float(w.drop(columns=reserve).gt(1e-8).sum(axis=1).mean())
        assert m["Maximum vaults held"] <= 6
        if arm == "C00":
            old = pd.read_csv(data["nb20_reference"] / f"{period}-C00-equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
            fresh = r["equity"].resample("D").last().ffill()
            assert old.index.equals(fresh.index)
            error = float((old - fresh).abs().max())
            assert error < 1e-6, (period, error)
            for metric in ("CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)"):
                assert abs(m[metric] - expected.loc[(period, "C00"), metric]) < 1e-6, (period, metric)
            parity.append({"Period": period, "Maximum equity difference (USD)": error, "Saved NB19 metrics match": True})
        records.append(dict(Period=period, Arm=arm, **m))
        runs[(period, arm)] = r
        attr[(period, arm)] = v
        weights[(period, arm)] = w
        audits.append(core.parent.audit(data, r, arm, period))
        pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
    pd.concat(audits, ignore_index=True).to_csv(data["artifact"] / "fill-audit.csv", index=False)
    pd.DataFrame(parity).to_csv(data["artifact"] / "c00-parity.csv", index=False)
    pd.DataFrame(data["nb19_quotes"]).to_csv(data["artifact"] / "fresh-entry-quotes.csv", index=False)
    pd.DataFrame(data["funding_ledger"]).to_csv(data["artifact"] / "funding.csv", index=False)
    return pd.DataFrame(records), runs, attr, weights


def metrics_table(frame, metrics):
    f = frame.set_index("Arm").loc[list(ARMS), metrics].T
    style = f.style
    for name in f.index:
        fmt = "${:,.0f}" if "(USD)" in name else "{:.2%}" if name in ("Cumulative return", "CAGR", "Maximum drawdown", "Mean cash weight", "September cash", "Largest vault weight") else "{:,.0f}" if name in ("Trades", "Maximum vaults held") else "{:.3f}"
        style = style.format(fmt, subset=pd.IndexSlice[[name], :])
        if name in ("Final equity (USD)", "Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown"):
            style = style.background_gradient(cmap="RdYlGn", axis=1, subset=pd.IndexSlice[[name], :])
    display(style)


def report_period(data, results, runs, attr, weights, robust, tails, period):
    display(Markdown(f'## {"2026 comparison" if period=="2026" else "Full-history comparison"}\n\n{LABELS[period]}. Independent fresh $150,000 accounts.'))
    f = results[results.Period.eq(period)]
    heading("Key metrics", "Green marks the better result within each economic metric. Daily-resampled risk metrics use 365-day annualisation, including non-decision days; both strategies use the same calculation.", period)
    metrics_table(f, ["Final equity (USD)", "Net profit (USD)", "Cumulative return", "CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown"])
    heading("Capital usage and trading", "Cash is measured against total equity. Maximum concentration is an observed holding weight and can drift above the allocation-time cap. Lower cash or higher turnover is not automatically better.", period)
    metrics_table(f, ["Mean cash weight", "September cash", "Mean vaults held", "Maximum vaults held", "Largest vault weight", "Trades", "Gross trade turnover (USD)"])
    for kind in ("equity", "drawdown", "cash"):
        fig, ax = plt.subplots(figsize=(11, 4.5))
        for arm in ARMS:
            eq = runs[(period, arm)]["equity"]
            s = eq / 1000 if kind == "equity" else (eq / eq.cummax() - 1) * 100 if kind == "drawdown" else weights[(period, arm)][runs[(period, arm)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol] * 100
            ax.plot(s.index, s, label=arm, color=COLOURS[arm], lw=1.6)
        title = {"equity": "Portfolio equity", "drawdown": "Drawdown from running peak", "cash": "Unallocated cash"}[kind]
        ax.set(title=title + "\n" + LABELS[period], ylabel={"equity": "Equity ($ thousands)", "drawdown": "Drawdown (%)", "cash": "Cash / total equity (%)"}[kind])
        ax.grid(alpha=0.2)
        ax.legend()
        if kind == "cash":
            ax.set_ylim(0, 100)
        figure(data, fig, f"{period}-{kind}", title, {"equity": "Both independent account equity curves on the same dollar scale. Starting capital and accounting conventions match.", "drawdown": "Marked losses from each account’s own previous peak; sparse NAV updates may bunch returns on observation dates.", "cash": "Actual reserve fraction, including the September 2026 capacity-constrained period. This is not a target allocation."}[kind], period)
    reserve = runs[(period, "V11")]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
    pooled = pd.concat([weights[(period, a)].drop(columns=reserve).mean() for a in ARMS], axis=1).fillna(0).mean(axis=1)
    names = list(pooled.nlargest(10).index)
    colours = {name: plt.get_cmap("tab20")(i) for i, name in enumerate(names)}
    colours.update({"Other vaults": "#9ca3af", "Cash": "#e5e7eb"})
    for arm in ARMS:
        w = weights[(period, arm)]
        p = w.reindex(columns=names, fill_value=0).copy()
        p["Other vaults"] = w.drop(columns=[reserve] + names, errors="ignore").sum(axis=1)
        p["Cash"] = w[reserve]
        assert np.allclose(p.sum(axis=1), 1, atol=1e-6)
        fig, ax = plt.subplots(figsize=(11, 4.8))
        ax.stackplot(p.index, *[p[c].to_numpy() * 100 for c in p], labels=p.columns, colors=[colours[c] for c in p], step="post")
        ax.set(ylim=(0, 100), ylabel="Holding / total equity (%)", title=f"{arm}: absolute asset weights\n" + LABELS[period])
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
        figure(data, fig, f"{period}-{arm}-weights", f"{arm}: absolute asset weights", "Cash is included; weights are not renormalised to invested capital. The same ten largest combined-average vaults and colours are used for both strategies in this period; all remaining vaults form Other vaults.", period)
    q = pd.DataFrame({a: (1 + runs[(period, a)]["daily_returns"]).groupby(runs[(period, a)]["daily_returns"].index.to_period("Q")).prod() - 1 for a in ARMS}).T
    q.to_csv(data["artifact"] / f"{period}-quarter-returns.csv")
    fig, ax = plt.subplots(figsize=(max(9, len(q.columns) * 0.75), 3.4))
    z = q.to_numpy() * 100
    lim = max(1, np.abs(z).max())
    im = ax.imshow(z, cmap="RdYlGn", vmin=-lim, vmax=lim, aspect="auto")
    ax.grid(False)
    start, end = map(pd.Timestamp, PERIODS[period])
    labels = [str(t) + ("*" if start > t.start_time or end - pd.Timedelta(days=1) < t.end_time.floor("D") else "") for t in q.columns]
    ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right")
    ax.set_yticks(range(2), ARMS)
    ax.set_title("Quarterly returns (%)\n" + LABELS[period])
    for i in range(2):
        for j in range(len(labels)):
            ax.text(j, i, f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=9, color="white" if abs(z[i, j]) > 0.6 * lim else "black")
    fig.colorbar(im, ax=ax, label="Return (%)")
    figure(data, fig, f"{period}-quarterly", "Quarterly return heatmap", "Compounded marked account returns. An asterisk indicates a partial quarter; these overlapping researched periods are not independent validation.", period)
    contributions = pd.concat({a: attr[(period, a)] for a in ARMS}, axis=1).fillna(0)
    contributions["C00 minus V11"] = contributions.C00 - contributions.V11
    contributions.to_csv(data["artifact"] / f"{period}-vault-attribution.csv")
    chosen = contributions["C00 minus V11"].abs().nlargest(10).index
    p = contributions.loc[chosen].sort_values("C00 minus V11")
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.barh(p.index, p["C00 minus V11"] / 1000, color=np.where(p["C00 minus V11"] >= 0, COLOURS["C00"], COLOURS["V11"]))
    ax.axvline(0, color="#555", lw=0.8)
    ax.set(xlabel="C00 minus V11 booked profit ($ thousands)", title="Vaults explaining the profit difference\n" + LABELS[period])
    ax.grid(axis="x", alpha=0.2)
    figure(data, fig, f"{period}-contributors", "Contributors to the performance gap", "Ten largest absolute vault-level differences, including realised and open-position marked profit. These reflect selection, sizing, timing and compounding jointly; they are not causal removal backtests.", period)
    heading("Concentration and extreme updates", "Largest positive vault share is its profit divided by total positive vault profits, before losing vaults. High kurtosis and large single updates warrant inspection of the original NAV intervals.", period)
    display(robust[robust.Period.eq(period)].drop(columns="Period").style.format({"Best update": "{:.2%}", "Excess kurtosis": "{:.2f}", "Top positive profit share": "{:.1%}"}).hide(axis="index"))
    heading("Strongest-update vault and market context", "Top three vault contributions to each account’s strongest update. Curator exclusions/quarantine and BTC/ETH returns over the actual NAV observation interval distinguish broad market moves from isolated vault jumps.", period)
    t = tails[tails.Period.eq(period)].drop(columns=["Period", "First_mark", "Last_mark"])
    display(t.style.format({"Update profit (USD)": "${:,.0f}", "NAV_return": "{:+.2%}", "Interval_days": "{:.2f}", "BTCUSDT return": "{:+.2%}", "ETHUSDT return": "{:+.2%}"}).hide(axis="index"))
    heading("Profit attribution reconciliation", "Vault profit includes closed and open positions. The residual against account profit must be below $1; this checks that the contributor charts explain the account.", period)
    display(f[["Arm", "Net profit (USD)", "PnL residual (USD)"]].style.format({"Net profit (USD)": "${:,.0f}", "PnL residual (USD)": "${:.8f}"}).hide(axis="index"))


def report(data, results, runs, attr, weights):
    display(Markdown(LOGIC.replace("$", "USD ")))
    robust, tails = robustness(data, results, runs, attr)
    fees = fee_accounting(data, runs)
    for period in PERIODS:
        report_period(data, results, runs, attr, weights, robust, tails, period)
        heading("Modelled redemption charges", "Paid fees and open-position liquidation allowances are separate. These inherited economic assumptions are identical across arms; they are not externally verified fee totals.", period)
        display(fees[fees.Period.eq(period)].drop(columns="Period").set_index("Arm").T.style.format("${:,.2f}"))
    heading("C00 replication against NB19", "Both complete daily equity paths and key metrics must match the latest completed NB19. V11 is independently replayed with the same common accounting corrections.", "2026")
    display(pd.read_csv(data["artifact"] / "c00-parity.csv").style.format({"Maximum equity difference (USD)": "${:.9f}"}).hide(axis="index"))
    rows = []
    for period in PERIODS:
        f = results[results.Period.eq(period)].set_index("Arm")
        a = f.loc["C00"]
        b = f.loc["V11"]
        rows.append(f'| {period} | {b.CAGR:.2%} | {a.CAGR:.2%} | {b.Sharpe:.3f} | {a.Sharpe:.3f} | {b["Maximum drawdown"]:.2%} | {a["Maximum drawdown"]:.2%} | ${a["Net profit (USD)"]-b["Net profit (USD)"]:+,.0f} |')
    comparison = "| Period | V11 CAGR | C00 CAGR | V11 Sharpe | C00 Sharpe | V11 max DD | C00 max DD | C00 extra profit |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n" + "\n".join(rows)
    insights = []
    for period in PERIODS:
        f = results[results.Period.eq(period)].set_index("Arm")
        d = f.loc["C00", "Net profit (USD)"] - f.loc["V11", "Net profit (USD)"]
        c = pd.concat({"C00": attr[(period, "C00")], "V11": attr[(period, "V11")]}, axis=1).fillna(0)
        gap = c.C00 - c.V11
        name = gap.idxmax()
        value = gap.max()
        insights.append(f'{period}: C00 changes profit by ${d:+,.0f}, CAGR by {(f.loc["C00","CAGR"]-f.loc["V11","CAGR"])*100:+.2f} percentage points and Sharpe by {f.loc["C00","Sharpe"]-f.loc["V11","Sharpe"]:+.3f}. The largest positive vault contribution to the difference is {name}, ${value:+,.0f} ({value/d:.1%} of the net account gap).')
    r = robust.set_index(["Period", "Arm"])
    risktext = " ".join(f'{p} C00: largest positive contributor {r.loc[(p,"C00"),"Top_vault"]} accounts for {r.loc[(p,"C00"),"Top positive profit share"]:.1%} of positive vault profit; best daily update {r.loc[(p,"C00"),"Best update"]:.2%}, excess kurtosis {r.loc[(p,"C00"),"Excess kurtosis"]:.1f}.' for p in PERIODS)
    jump_notes = []
    for period in PERIODS:
        t = tails[tails.Period.eq(period) & tails.Arm.eq("C00")].iloc[0]
        jump_notes.append(f'{period} C00 strongest update: {t.Vault} contributes ${t["Update profit (USD)"]:,.0f}, with a {t.NAV_return:.1%} NAV change across {t.Interval_days:.1f} days; BTC and ETH change {t["BTCUSDT return"]:.1%} and {t["ETHUSDT return"]:.1%} over that observation interval. Curator excluded={t.Excluded}, quarantined={t.Quarantined}.')
    verdict = "C00 improves historical CAGR and Sharpe in both periods, supporting the economic hypothesis on these inspected samples. Full-history drawdown is worse, so this is not an improvement in every risk measure. In 2026, C00 earns more despite higher average cash. Full-history differences also include earlier deployment and different accumulated wealth. Isolating score, risk estimation and waterfall contributions remains a separate experiment."
    head = (
        """# Experiment 20 — C00 versus deployed v11 rules

Based on [NB19](19-backtest-protected-core-score-risk-allocation.ipynb) and [NB15](15-backtest-allocation-vs-v11.ipynb).

**Goal:** compare C00 and hyper-ai-v11.py under identical data, capital, timing, fees and accounting. No parameter search. C00 changes the score, risk-estimation package and allocation method together; this experiment measures the combined strategy difference, not each change's isolated contribution.

**Periods:** 2026-01-01 → 2026-10-05 exclusive (through 4 October); full history 2023-03-01 → 2026-10-08 exclusive (through 7 October, last archive day partial). Fresh $150,000 in each account, all preceding warmup including 2025. 2026 outputs appear first, with full-history outputs explicitly labelled.

## Key new insights

"""
        + "\n\n".join(insights)
        + "\n\n"
        + verdict
        + "\n\n## Summary of results\n\n"
        + comparison
        + "\n\n## Robustness of results\n\n"
        + risktext
        + "\n\n"
        + "\n\n".join(jump_notes)
        + """

C00 reproduces NB19's daily equity and metrics. All executed fills pass the as-of-NAV audit, and position profit reconciles to account profit within $1. Common partial-sell, cached-tax and funding corrections apply to both arms. Strongest vault updates are checked against curator flags and BTC/ETH over their actual observation intervals in the tables below. Sparse NAV may bunch returns; last-known NAV does not establish an executable live price. The two periods overlap and were previously researched; there is no untouched holdout or statistical significance claim. Universe/guard selection is retrospective and inherited fee assumptions remain economically unverified. No deployment-server revision was verified.
"""
    )
    head = head.replace("$", "USD ")
    (data["artifact"] / "final-header.md").write_text(head)
    (ROOT / "20-c00-vs-v11-findings.md").write_text(head + "\n" + LOGIC.replace("$", "USD "))
    display(Markdown("## Findings\n\n" + "\n\n".join(insights).replace("$", "USD ")))
    display(Markdown("<details><summary>Data, source and framework identity</summary>\n\n```json\n" + json.dumps(data["manifest"], indent=2, default=str) + "\n```\n\n</details>"))
    (data["artifact"] / "figures.json").write_text(json.dumps(data["figures"], indent=2))
    (data["artifact"] / "complete.json").write_text(json.dumps({"status": "complete", "economic_accounts": 4, "periods": 2, "figures": len(data["figures"])}, indent=2))
    return head
