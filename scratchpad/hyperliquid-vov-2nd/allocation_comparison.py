"""NB15: compare frozen NB14 candidates with the deployed v11 source rules."""

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

from profitable_allocation import ROOT, PERIODS, LABELS, initialise as initialise_reference, replay, pricing_convention, analyse_run, audit_trades, observed_quote

ARMS = ("V11", "A", "C", "G")
NAMES = {"V11": "Deployed v11 rules", "A": "Four-input / source variance", "C": "Four-input / regularised variance", "G": "Four-input / regularised downside"}
COLOURS = {"V11": "#2563eb", "A": "#111827", "C": "#7c3aed", "G": "#059669"}
NOTEBOOK = ROOT / "15-backtest-allocation-vs-v11.ipynb"
LOGIC = """## Strategy logic comparison

This table describes the rules replayed in both periods. A is the research benchmark; v11 is the deployed strategy's source configuration. The historical simulation uses the shared repaired archive and current frozen universe/guard, rather than a replay of recorded live decisions.

| Strategy | Ranking and score | Position sizing | Parent and change | Missing and sparse history |
|:--|:--|:--|:--|:--|
| **V11: deployed rules** | 60% 360-day CAGR + 40% 45-day Sortino. CAGR is clipped to 0–100% and Sortino to 0–3; each component is mapped to 0–1. | Original inverse variance, using the source 90-day volatility indicator. | Source `hyper-ai-v11.py` decision callback and parameters, apart from the two replay date ranges. The existing local edit only relaxes a backtest floating-point assertion. | Missing composite scores become zero in source selection; eligible unscored vaults can still enter through the normal ranking. Source risk fallback is retained. |
| **A: research benchmark** | 48% 360-day CAGR + 32% 45-day Sortino + 10% 180-day CAGR + 10% 30-day Sortino. Same clips as v11. | Original source 90-day inverse variance, exactly as v11. | NB14 A: changes the ranking formula from v11 while retaining source sizing and the original allocator. | `missing=True`: retain the source unscored-entry behaviour; do not invent a score for unavailable active components. Source risk fallback is retained. |
| **C: historical challenger** | Same four-input score as A. | Inverse regularised 90-day variance: empirical variance is blended with a positive leave-one-out peer median. Empirical weight is `m / (m + 30)`, where `m` counts actual daily observation updates. | NB14 C, derived from A: changes the risk estimator package while retaining the original allocator. | Causal daily NAV forward filling starts at the first observation. Partial histories are allowed; actual updates determine confidence. Missing risk uses peer support; an unusable basket forecast falls back to equal sizing. |
| **G: downside challenger** | Same four-input score as A. | Inverse regularised 90-day downside moment: mean squared negative returns, including zero contributions from non-negative days. Uses the same observation-count shrinkage. | NB14 G, derived from C: replaces individual and peer total variance with downside risk. | Same partial-history support as C. A loss-free vault receives positive peer risk where available; use total-variance peer support if downside support is unavailable, then the existing basket fallback. |

### Shared portfolio and execution rules

Every strategy uses a six-position limit, two-day decisions, entry rank 6, incumbent exit rank 8, a 98% deployment target, 33% concentration and pool-size caps, $7,500 minimum TVL and a 14-day return gate above −16%. Source deposit/redemption permissions, guard checks, leader-share policy, rank hysteresis and trade thresholds are retained. There is no additional dollar-cap allocator or quote-freshness veto in this comparison.

New capital is blocked when observed leader share is below 5.5%. The source buy and sell thresholds start at $75 and $750 respectively for the $150,000 account, with the source equity-scaling behaviour retained. Redemption modelling retains 10% of positive realised profit plus a 0.1% gross redemption allowance; this allowance is an assumption, not a verified venue fee. No additional vault slippage is imposed.

All strategies use NAV observations timestamped at or before each price query, and indicators from completed prior daily buckets. This NB14 timing convention is shared by v11 as well: it is a research execution model, not a change to v11's live trading rules. Last-known NAV does not establish the actual executable NAV during an archive gap. The inherited partial-trim fee calculation can apply a fee twice and is retained for comparison; differing turnover can affect its impact.
"""


def initialise():
    """Pin the NB14 environment and establish an isolated eight-run generation."""
    data, evaluator, preflight = initialise_reference()
    saved_notebook = json.loads((ROOT / "14-backtest-profitable-allocation.ipynb").read_text())
    reference = Path(saved_notebook["metadata"]["nb14"]["artifact_generation"])
    saved_identity = json.loads((reference / "manifest.json").read_text())["identity"]
    current_identity = json.loads(json.dumps(data["manifest"]["identity"], default=str))
    for key in saved_identity:
        if key != "code":
            assert saved_identity[key] == current_identity[key], ("NB14 inputs changed", key)
    assert saved_identity["code"]["profitable_allocation.py"] == current_identity["code"]["profitable_allocation.py"]
    assert (reference / "results.csv").exists(), "Completed NB14 reference is required"
    source = Path("/Users/moo/code/strategies/strategy/hyper-ai-v11.py")
    p = evaluator.parameters
    assert p.max_assets_in_portfolio == p.max_capacity_assets == 6
    assert p.selection_score_indicator == "cagr_sortino_weight" and p.cagr_weight == 0.6
    assert p.inverse_vol_window == 90 and p.sharpe_lookback_days == 45 and p.cagr_lookback_days == 360
    identity = dict(version="nb15-v1", nb14=data["manifest"]["identity"], source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), code={n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in ["allocation_comparison.py", "create_allocation_comparison_notebook.py"]}, arms=list(ARMS), initial_cash=150000, periods={k: [str(t) for t in v] for k, v in PERIODS.items()}, pricing="as_of_observation")
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/15" / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=fingerprint, figures=[], risk_cache={}, risk_ledger=[], quote_queries={}, run_context=None, nb14_reference=reference, pricing_convention="as_of_observation")
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    evaluator.values.clear()
    data["manifest"] = dict(identity=identity, fingerprint=fingerprint, nb14_reference=str(reference), framework=data["framework_commits"], warmup="All available pre-decision observations; no backward fill before vault launch", execution="Common as-of-observation NAV; no quote freshness veto; source fee conventions", limitations=["Current inventory and guard applied retrospectively", "Previously searched history; no independent holdout", "Sparse recorded NAV is not proof of actual fill NAV", "Inherited partial-trim fee issue retained"])
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data, evaluator


def run(data, evaluator):
    """Execute eight independent accounts and reconcile trades, cash and profit."""
    from score_matrix import FEATURES

    runs = {}
    records = []
    attribution = {}
    weights = {}
    audits = []
    parity = []
    expected = pd.read_csv(data["nb14_reference"] / "results.csv").set_index(["Period", "Arm"])
    weight = np.zeros(len(FEATURES))
    weight[0] = 1
    print("Eight full-engine replays; estimated 4–12 minutes, serial execution.", flush=True)
    for period, arm in tqdm([(p, a) for p in PERIODS for a in ARMS], desc="NB15 four strategies × two periods", mininterval=15):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if arm == "V11":
                data["run_context"] = (period, arm, "primary")
                with pricing_convention(data):
                    r = evaluator.run(weight, *PERIODS[period], n=6, source_control=True, keep=True, profile="NB15-v11-as-of-observation")
            else:
                r = replay(data, evaluator, arm, period)
        m, v, w = analyse_run(data, r, arm, period)
        m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
        m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"]) if m["Maximum drawdown"] < 0 else np.nan
        runs[(period, arm)] = r
        attribution[(period, arm)] = v
        weights[(period, arm)] = w
        records.append(dict(Period=period, Arm=arm, Strategy=NAMES[arm], **m))
        a = audit_trades(data, r, arm, period)
        assert a.Matches_known_NAV.all(), a[~a.Matches_known_NAV].head()
        audits.append(a)
        if arm != "V11":
            for metric in ["CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)"]:
                value = float(expected.loc[(period, arm), metric])
                error = m[metric] - value
                assert abs(error) < (0.01 if "(USD)" in metric else 2e-6), (period, arm, metric, error)
                parity.append(dict(Period=period, Arm=arm, Metric=metric, Expected=value, Observed=m[metric], Difference=error))
        pd.DataFrame(records).to_csv(data["artifact"] / "results.csv", index=False)
    pd.DataFrame(parity).to_csv(data["artifact"] / "nb14-parity.csv", index=False)
    audit = pd.concat(audits, ignore_index=True)
    audit.to_parquet(data["artifact"] / "trade-timing.parquet", index=False)
    if data["risk_ledger"]:
        pd.concat(data["risk_ledger"], ignore_index=True).to_parquet(data["artifact"] / "risk-ledger.parquet", index=False)
    (data["artifact"] / "complete.json").write_text(json.dumps(dict(status="complete", strategies=4, periods=2, nav_checks=len(audit), nb14_parity_checks=len(parity)), indent=2))
    return pd.DataFrame(records), runs, attribution, weights


def heading(title, description, period):
    display(Markdown(f"### {title} — {LABELS[period]}\n\n{description}"))


def metric_table(frame, metrics):
    """Display strategies side by side, colouring each metric independently."""
    f = frame.set_index("Arm").loc[list(ARMS), metrics].T
    formats = {m: "${:,.0f}" if "(USD)" in m else "{:.2%}" if m in ["CAGR", "Cumulative return", "Maximum drawdown", "Mean cash weight", "Largest vault weight", "Best update", "Top positive profit share"] else "{:.0f}" if m in ["Trades", "Maximum vaults held"] else "{:.2f}" for m in f.index}
    style = f.style.format(lambda x: f"{x:.2f}", na_rep="Unavailable")
    for m in f.index:
        style = style.format(formats[m], subset=pd.IndexSlice[[m], :])
    for m in ["Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown"]:
        if m in f.index:
            style = style.background_gradient(subset=pd.IndexSlice[[m], :], axis=1, cmap="RdYlGn")
    display(style)


def figure(data, fig, name, title, description, period):
    heading(title, description, period)
    fig.tight_layout()
    path = data["artifact"] / f"{name}.png"
    fig.savefig(path, dpi=115, bbox_inches="tight")
    display(fig)
    plt.close(fig)
    data["figures"].append(str(path))


def robustness(data, results, runs, attribution):
    """Attribute extreme updates to vault marks and common market intervals."""
    from tradingstrategy.binance.price import fetch_binance_price
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined

    market = {s: fetch_binance_price(symbol=s, request_timeout=10.0) for s in ["BTCUSDT", "ETHUSDT"]}
    rows = []
    tail = []
    for (period, arm), r in runs.items():
        pnl = attribution[(period, arm)]
        positive = pnl[pnl > 0].sort_values(ascending=False)
        daily = r["daily_returns"]
        best = daily.idxmax()
        rows.append(dict(Period=period, Arm=arm, **{"Best update": float(daily.max()), "Excess kurtosis": float(daily.kurt()), "Top positive profit share": float(positive.iloc[0] / positive.sum()) if len(positive) else np.nan}, Top_vault=positive.index[0] if len(positive) else "None", Best_date=str(best.date())))
        curves = pd.read_parquet(data["artifact"] / f"{period}-{arm}-position-curves.parquet")
        meta = pd.read_parquet(data["artifact"] / f"{period}-{arm}-positions.parquet").set_index("Position id")
        changes = curves.diff().loc[best].groupby(meta.Vault).sum().sort_values(ascending=False)
        earlier = r["equity"].index[r["equity"].index < best]
        if not len(earlier):
            continue
        previous = earlier[-1]
        for vault, profit in changes.head(3).items():
            address = meta[meta.Vault.eq(vault)].iloc[0].Address
            pid = data["identities"].set_index("vault_address").loc[address, "pair_id"]
            first = observed_quote(data, pid, previous)
            last = observed_quote(data, pid, best)
            if first is None or last is None:
                continue
            row = dict(Period=period, Arm=arm, Update=str(best.date()), Vault=vault, **{"Update profit (USD)": profit}, NAV_return=last[0] / first[0] - 1, Interval_days=(last[1] - first[1]).total_seconds() / 86400, First_mark=str(first[1]), Last_mark=str(last[1]), Excluded=address in EXCLUDED_VAULTS, Quarantined=is_quarantined(address, best))
            for symbol, df in market.items():
                q = df.loc[first[1].floor("D") : last[1].floor("D"), "close"]
                row[symbol + " return"] = float(q.iloc[-1] / q.iloc[0] - 1) if len(q) else np.nan
            tail.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(data["artifact"] / "robustness.csv", index=False)
    tails = pd.DataFrame(tail)
    tails.to_csv(data["artifact"] / "tail-audit.csv", index=False)
    return frame, tails


def report_period(data, results, runs, attribution, weights, robust, tails, period):
    f = results[results.Period.eq(period)]
    display(Markdown(f'## {"2026 comparison" if period=="2026" else "Full-history comparison"}\n\nFresh $150,000 accounts for {LABELS[period]}. A, C and G reproduce NB14; v11 uses its own source ranking and sizing.'))
    heading("Key metrics", "Compare net economic outcomes in the same table. Green indicates the better value within each row. A is the benchmark; V11 is the deployed-rule control. Calmar is CAGR divided by absolute maximum drawdown.", period)
    metric_table(f, ["Final equity (USD)", "Net profit (USD)", "Cumulative return", "CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown"])
    heading("Deployment and trading", "Cash and turnover explain implementation differences. Recorded redemption costs are the inherited source estimate, not independently reconciled total fees. Cash includes early empty-universe periods in the full-history account. The 33% cap applies when allocating deployable capital; subsequent value drift can produce a higher observed equity weight.", period)
    metric_table(f, ["Mean cash weight", "Largest vault weight", "Maximum vaults held", "Trades", "Gross trade turnover (USD)", "Modelled redemption costs (USD)"])
    heading("Incremental performance versus v11", "Each row subtracts v11 on the identical period, capital and pricing convention. Positive drawdown differences mean a less severe drawdown; negative differences mean a worse drawdown.", period)
    base = f.set_index("Arm").loc["V11"]
    d = f[f.Arm.ne("V11")].copy()
    d["Profit difference (USD)"] = d["Net profit (USD)"] - base["Net profit (USD)"]
    d["CAGR difference (pp)"] = (d.CAGR - base.CAGR) * 100
    d["Sharpe difference"] = d.Sharpe - base.Sharpe
    d["Drawdown difference (pp)"] = (d["Maximum drawdown"] - base["Maximum drawdown"]) * 100
    display(d[["Arm", "Profit difference (USD)", "CAGR difference (pp)", "Sharpe difference", "Drawdown difference (pp)"]].style.format({"Profit difference (USD)": "${:+,.0f}", "CAGR difference (pp)": "{:+.2f}", "Sharpe difference": "{:+.2f}", "Drawdown difference (pp)": "{:+.2f}"}).hide(axis="index"))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for arm in ARMS:
        eq = runs[(period, arm)]["equity"]
        ax.plot(eq.index, eq / 1000, label=arm + " — " + NAMES[arm], color=COLOURS[arm], lw=1.7)
    ax.set(title="Portfolio equity\n" + LABELS[period], ylabel="Equity ($ thousands)")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8, loc="upper left")
    figure(data, fig, f"{period}-equity", "Equity curves", "Compare all four accounts on the same dollar scale. Full-history differences carry forward through compounding; they are not fresh-start annual comparisons.", period)
    q = {arm: (1 + runs[(period, arm)]["daily_returns"]).groupby(runs[(period, arm)]["daily_returns"].index.to_period("Q")).prod() - 1 for arm in ARMS}
    q = pd.DataFrame(q).T.reindex(ARMS)
    q.to_csv(data["artifact"] / f"{period}-quarter-returns.csv")
    fig, ax = plt.subplots(figsize=(max(9, len(q.columns) * 1.1), 3.5))
    z = q.to_numpy(float) * 100
    limit = max(np.nanmax(np.abs(z)), 1)
    im = ax.imshow(z, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    ax.grid(False)
    start, end = PERIODS[period]
    quarters = pd.PeriodIndex(q.columns, freq="Q")
    quarter_labels = [str(t) + ("*" if pd.Timestamp(start) > t.start_time or pd.Timestamp(end) - pd.Timedelta(days=1) < t.end_time.floor("D") else "") for t in quarters]
    ax.set_xticks(range(len(q.columns)), quarter_labels, rotation=35, ha="right")
    ax.set_yticks(range(4), list(ARMS))
    ax.set_title("Quarterly portfolio returns (%)\n" + LABELS[period])
    for i in range(4):
        for j in range(len(q.columns)):
            ax.text(j, i, f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=9, color="white" if abs(z[i, j]) > limit * 0.6 else "black")
    fig.colorbar(im, ax=ax, label="Return (%)", shrink=0.8)
    figure(data, fig, f"{period}-quarters", "Quarterly return heatmap", "Compounded account returns by quarter show when the advantage occurred. An asterisk marks a partial quarter; consult the period dates for its actual coverage. The final quarter is partial.", period)
    for arm in ARMS:
        w = weights[(period, arm)]
        reserve = runs[(period, arm)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        vault = w.drop(columns=[reserve])
        names = list(vault.mean().nlargest(10).index)
        plotted = vault[names].copy()
        other = vault.drop(columns=names).sum(axis=1)
        if other.max() > 1e-9:
            plotted["Other vaults"] = other
        plotted["Cash"] = w[reserve]
        allnames = sorted(set(n for x in weights.values() for n in x.drop(columns=[reserve]).mean().nlargest(10).index))
        colours = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors) + list(plt.get_cmap("tab20c").colors)
        palette = {n: colours[i % len(colours)] for i, n in enumerate(allnames)}
        palette.update({"Cash": "#d1d5db", "Other vaults": "#9ca3af"})
        fig, ax = plt.subplots(figsize=(10.5, 4.5))
        ax.stackplot(plotted.index, *[plotted[c].to_numpy() * 100 for c in plotted], labels=plotted.columns, colors=[palette[c] for c in plotted])
        ax.set(ylim=(0, 100), ylabel="Fraction of total equity (%)", title=f"{arm} — {NAMES[arm]}: absolute asset weights\n" + LABELS[period])
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
        figure(data, fig, f"{period}-{arm}-weights", f"{arm}: absolute asset weights", "Each vault is measured against total account equity, including cash. Ten largest average vault exposures are shown separately; smaller exposures are grouped. No rescaling to invested capital.", period)
    heading("Concentration and extreme updates", "Largest daily account updates may incorporate several days of sparse NAV changes. Positive profit share is the largest vault contribution divided by the sum of positive vault contributions, before subtracting losing vaults.", period)
    r = robust[robust.Period.eq(period)].merge(f[["Arm", "PnL residual (USD)"]], on="Arm")
    display(r.drop(columns=["Period"]).style.format({"Best update": "{:.2%}", "Excess kurtosis": "{:.2f}", "Top positive profit share": "{:.1%}", "PnL residual (USD)": "${:.6f}"}).hide(axis="index"))
    heading("Vault contributions behind the strongest updates", "The three largest vault contributions on each strategy’s best account update. NAV returns and BTC/ETH context use the actual observation interval, which may span a week. Curator flags identify existing exclusions or quarantine; a large return alone does not establish a data error.", period)
    t = tails[tails.Period.eq(period)].drop(columns=["Period", "First_mark", "Last_mark"])
    display(t.style.format({"Update profit (USD)": "${:,.0f}", "NAV_return": "{:+.2%}", "Interval_days": "{:.2f}", "BTCUSDT return": "{:+.2%}", "ETHUSDT return": "{:+.2%}"}).hide(axis="index"))


def conclusion(results, robust):
    lines = ["## Summary of results", ""]
    for period in PERIODS:
        lines.extend([f"### {LABELS[period]}", "", "| Strategy | Net profit | CAGR | Sharpe | Max drawdown |", "|:--|--:|--:|--:|--:|"])
        f = results[results.Period.eq(period)].set_index("Arm")
        for arm in ARMS:
            r = f.loc[arm]
            lines.append(f"| {arm} | ${r['Net profit (USD)']:,.0f} | {r.CAGR:.2%} | {r.Sharpe:.2f} | {r['Maximum drawdown']:.2%} |")
        lines.append("")
    lines.extend(["## Key new insights", ""])
    for period in PERIODS:
        f = results[results.Period.eq(period)].set_index("Arm")
        leader = f["Net profit (USD)"].idxmax()
        lines.append(f"- **{'2026' if period=='2026' else 'Full history'}:** {leader} has the highest profit (${f.loc[leader,'Net profit (USD)']:,.0f}), with {f.loc[leader,'CAGR']:.2%} CAGR, {f.loc[leader,'Sharpe']:.2f} Sharpe and {f.loc[leader,'Maximum drawdown']:.2%} maximum drawdown.")
        for arm, parent in [("A", "V11"), ("C", "A"), ("G", "C")]:
            lines.append(f"  - {arm} versus {parent}: profit ${f.loc[arm,'Net profit (USD)']-f.loc[parent,'Net profit (USD)']:+,.0f}; CAGR {(f.loc[arm,'CAGR']-f.loc[parent,'CAGR'])*100:+.2f} percentage points; Sharpe {f.loc[arm,'Sharpe']-f.loc[parent,'Sharpe']:+.2f}; drawdown {(f.loc[arm,'Maximum drawdown']-f.loc[parent,'Maximum drawdown'])*100:+.2f} percentage points.")
    lines += [
        "",
        "A versus V11 changes the ranking formula with source sizing held fixed. C versus A changes a risk-estimation package, including partial-history support and filling, so its advantage cannot be attributed to shrinkage alone. G versus C changes the downside functional and its peer prior. These are historical comparisons, not independent statistical confirmation.",
        "",
        "## Robustness of results",
        "",
        "All eight accounts reconcile asset weights to equity and position profit to net account profit. A/C/G reproduce NB14 metrics under the shared NAV timing convention. Every successful vault fill matches an observation at or before its query, after undoing the inherited partial-trim fee adjustment for the timing check. Maximum positions remain six.",
        "",
        "The full-history results include young vaults, sparse observations, empty-universe cash periods and previously searched years. Current universe/guard membership is retrospective. No quote-freshness veto is imposed. The inherited partial-trim fee issue and assumed redemption allowance remain material limitations.",
        "",
        f"Across the eight accounts, the largest single account update is {robust['Best update'].max():.2%}; the largest positive-profit concentration in one vault is {robust['Top positive profit share'].max():.1%}. The tables below attribute the strongest updates to actual NAV intervals and market context.",
    ]
    return "\n".join(lines)


def report(data, results, runs, attribution, weights):
    robust, tails = robustness(data, results, runs, attribution)
    for period in PERIODS:
        report_period(data, results, runs, attribution, weights, robust, tails, period)
    text = conclusion(results, robust)
    display(Markdown(text))
    (ROOT / "15-allocation-comparison-findings.md").write_text("# Experiment 15 — allocation candidates versus deployed v11\n\n" + text + "\n\n" + LOGIC + "\n")
    nb = __import__("nbformat").read(NOTEBOOK, as_version=4)
    nb.cells[0].source = nb.cells[0].source.split("<!-- Results -->")[0] + "<!-- Results -->\n\n" + text
    nb.metadata["nb15"] = dict(status="complete", artifact_generation=str(data["artifact"]), strategies=4, periods=2)
    # The observable runner owns the live notebook; save the heading separately for finalisation.
    (data["artifact"] / "final-header.md").write_text(nb.cells[0].source)
    (data["artifact"] / "presentation.json").write_text(json.dumps(dict(figures=data["figures"], separate_images=True), indent=2))
    return text
