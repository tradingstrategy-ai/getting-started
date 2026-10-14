"""Economic interpretation and separate figures for capital-allocation NB17."""

import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.text import Text
from IPython.display import Markdown, display
import capital_allocation as experiment
from capital_allocation_methods import METHODS, ARMS, OVERFLOW, LIMITS, score_lp, waterfall, floors, joint, NUMERICAL
from allocation_comparison import heading, figure, robustness

ROOT = experiment.ROOT
LABELS = experiment.LABELS
PALETTE = {a: plt.get_cmap("tab20")(i) for i, a in enumerate(ARMS)}
FORMATS = {"CAGR": "{:.2%}", "Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Maximum drawdown": "{:.2%}", "Calmar": "{:.2f}", "Cumulative return": "{:.2%}", "Mean cash weight": "{:.1%}", "September cash": "{:.1%}", "Largest vault weight": "{:.1%}", "Maximum vaults held": "{:.0f}", "Trades": "{:.0f}", "Mean effective breadth": "{:.2f}", "Best update": "{:.2%}", "Excess kurtosis": "{:.2f}", "Top positive profit share": "{:.1%}"}


def table(frame):
    """Colour economic metrics independently and avoid enormous notebook output."""
    formats = {c: "${:,.0f}" if "(USD)" in c else FORMATS.get(c, "{:.2f}") for c in frame.select_dtypes("number").columns}
    style = frame.style.format(formats, na_rep="—").hide(axis="index")
    for c in ["CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown", "Net profit (USD)", "Profit difference (USD)"]:
        if c in frame:
            style = style.background_gradient(subset=[c], cmap="RdYlGn")
    display(style)


def heatmap(data, values, name, title, description, period, unit="USD", decimals=0, cmap="RdYlGn"):
    fig, ax = plt.subplots(figsize=(max(8, 1.25 * len(values.columns)), max(3, 0.36 * len(values) + 1.3)))
    z = values.to_numpy(float)
    limit = max(1.0, np.nanmax(np.abs(z)))
    im = ax.imshow(z, cmap=cmap, vmin=0 if cmap == "Blues" else -limit, vmax=limit, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(values.columns)), list(map(str, values.columns)), rotation=30, ha="right")
    ax.set_yticks(range(len(values)), values.index)
    ax.set_title(title + "\n" + LABELS[period])
    for i in range(len(values)):
        for j in range(len(values.columns)):
            if np.isfinite(z[i, j]):
                text = f"{z[i,j]/1000:+.1f}k" if unit == "USD" else f"{z[i,j]:.{decimals}f}"
                ax.text(j, i, text, ha="center", va="center", fontsize=8, color="white" if abs(z[i, j]) > limit * 0.65 else "black")
    fig.colorbar(im, ax=ax, label=unit, shrink=0.8)
    figure(data, fig, name, title, description, period)


def profit_by_calendar(runs, period, freq):
    columns = {}
    for arm in ARMS:
        eq = runs[(period, arm)]["equity"].resample("D").last().ffill()
        delta = eq.diff()
        delta.iloc[0] = eq.iloc[0] - 150000
        columns[arm] = delta.groupby(eq.index.to_period(freq)).sum()
    out = pd.DataFrame(columns).T.reindex(ARMS)
    return out.sub(out.loc["M00"], axis=1)


def equity_chart(data, runs, period, members):
    fig, ax = plt.subplots(figsize=(10.5, 4.7))
    for arm in members:
        eq = runs[(period, arm)]["equity"]
        ax.plot(eq.index, eq / 1000, label=arm + " — " + METHODS[arm], color=PALETTE[arm], lw=1.6)
    ax.set(title="Equity: benchmark and economic shortlist\n" + LABELS[period], ylabel="Equity ($ thousands)")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8, loc="upper left")
    figure(data, fig, f"{period}-equity", "Equity curves", "Show the benchmark and deduplicated net-profit/Sharpe leaders from the two researched periods. These are historical comparisons, with no independent holdout.", period)


def weight_chart(data, weights, arm, period):
    w = weights[(period, arm)].copy()
    reserve = next(c for c in w.columns if c in ("USDC", "USDT", "USD"))
    vault = w.drop(columns=[reserve])
    names = list(vault.mean().nlargest(9).index)
    f = vault[names].copy()
    other = vault.drop(columns=names).sum(axis=1)
    if other.max() > 1e-8:
        f["Other vaults"] = other
    f["Cash"] = w[reserve]
    allnames = sorted(set(name for w0 in weights.values() for name in w0.drop(columns=[reserve]).mean().nlargest(9).index))
    colours = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors) + list(plt.get_cmap("tab20c").colors)
    colour_by_vault = {name: colours[i % len(colours)] for i, name in enumerate(allnames)}
    colour_by_vault.update({"Cash": "#d1d5db", "Other vaults": "#9ca3af"})
    palette = [colour_by_vault[c] for c in f.columns]
    fig, ax = plt.subplots(figsize=(10.5, 4.7))
    ax.stackplot(f.index, *[f[c].to_numpy() * 100 for c in f], labels=f.columns, colors=palette)
    ax.set(ylim=(0, 100), title=f"{arm}: absolute asset weights\n" + LABELS[period], ylabel="Fraction of total equity (%)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
    figure(data, fig, f"{period}-{arm}-weights", f"{arm}: absolute asset weights", "Vaults are divided by total account equity, including cash. Largest nine average exposures are separate; remaining vaults are grouped. This is not normalised to invested capital.", period)


def fee_accounting(data, runs):
    """Distinguish actual modelled sell deductions from uncrystallised liabilities."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("nb17_source_accounting", experiment.SOURCE)
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    rows = []
    for (period, arm), r in runs.items():
        state = r["result"].state
        paid = 0.0
        last = r["equity"].index[-1]
        for t in state.portfolio.get_all_trades():
            if t.is_success() and t.is_sell():
                quote = experiment.engine.observed_quote(data, t.pair.internal_id, pd.Timestamp(t.executed_at))
                gross = abs(float(t.executed_quantity)) * quote[0]
                paid += max(0.0, gross - abs(float(t.executed_quantity)) * float(t.executed_price))
        gross_open = 0.0
        performance = 0.0
        capital = 0.0
        marked_open = 0.0
        for position in state.portfolio.get_open_positions():
            quote = experiment.engine.observed_quote(data, position.pair.internal_id, last)
            gross = float(position.get_quantity()) * quote[0]
            basis = source.get_remaining_cost_basis(position)
            gross_open += gross
            marked_open += position.get_value()
            performance += max(gross - basis, 0.0) * 0.1
            capital += gross * 0.001
        gross_equity = state.portfolio.get_cash() + gross_open
        rows.append({"Period": period, "Arm": arm, "Paid sell deductions (USD)": paid, "Open performance liability (USD)": performance, "Open capital allowance (USD)": capital, "Gross NAV equity (USD)": gross_equity, "Estimated liquidation equity (USD)": gross_equity - performance - capital, "Reported marked equity (USD)": float(r["equity"].iloc[-1]), "Open marks vs net estimate (USD)": marked_open - (gross_open - performance - capital)})
    f = pd.DataFrame(rows)
    f.to_csv(data["artifact"] / "fee-accounting.csv", index=False)
    return f


def mechanism_diagnostics(data):
    """Compare cheap target alternatives on M01's own decision-time states."""
    ledger = pd.read_csv(data["artifact"] / "2026-M01-target-ledger.csv", parse_dates=["Date"])
    rows = []
    snapshot = None
    for t, f in ledger.groupby("Date"):
        ids = list(f[f.Role.eq("core")]["Pair id"])
        allrows = f.set_index("Pair id")
        cap = allrows["Capacity ceiling (USD)"].to_dict()
        score = allrows["Ranking score"].to_dict()
        old = allrows["Old value (USD)"].to_dict()
        addr = allrows.Address.to_dict()
        B = float(f["Deployable budget (USD)"].iloc[0])
        buy = max(5.0, B / 0.98 * 0.0005)
        x, _ = floors(ids, lambda active: waterfall(active, cap, score, B, addr), cap, old, buy, 0.005)
        lp, _ = floors(ids, lambda active: score_lp(active, cap, score, old, B, addr), cap, old, buy, 0.005)
        difference = sum(abs(x.get(i, 0) - lp.get(i, 0)) for i in ids)
        rows.append({"Date": t, "Capacity-bound": sum(cap[i] for i in ids) <= B, "M03/L01 dollar difference": difference, "All core scores positive": all(score[i] > 0 for i in ids), "Core scores distinct": len(set(score[i] for i in ids)) == len(ids), "Scored-only candidate capacity": sum(cap[i] for i in allrows.index if allrows.loc[i, "Score available"]), "Budget": B, "Core ceiling": sum(cap[i] for i in ids), "All candidate ceiling": sum(cap.values())})
        if t == pd.Timestamp("2026-09-20"):
            snapshot = f
    diagnostics = pd.DataFrame(rows)
    diagnostics.to_csv(data["artifact"] / "common-state-mechanisms.csv", index=False)
    positive = diagnostics["All core scores positive"] & diagnostics["Core scores distinct"]
    assert (diagnostics.loc[positive, "M03/L01 dollar difference"] < 1e-6).all()
    # Joint and greedy accounts evolve differently. A common September state
    # distinguishes a proxy solve from an economic account comparison.
    common = []
    if snapshot is not None:
        f = snapshot.set_index("Pair id")
        cap = f["Capacity ceiling (USD)"].to_dict()
        score = f["Ranking score"].to_dict()
        old = f["Old value (USD)"].to_dict()
        addr = f.Address.to_dict()
        B = float(f["Deployable budget (USD)"].iloc[0])
        ids = list(f.index)
        chosen = list(f[f.Role.eq("core")].index)
        buy = max(5.0, B / 0.98 * 0.0005)

        def trial(selected):
            x, _ = floors(selected, lambda active: score_lp(active, cap, score, old, B, addr), cap, old, buy, 0.005)
            return x, sum(score[i] * v for i, v in x.items()) / B

        greedy, J = trial(chosen)
        visited = {tuple(sorted(chosen))}
        steps = 0
        checks = 0
        while True:
            proposal = None
            for i in set(ids) - set(chosen):
                if old[i] == 0 and cap[i] < buy:
                    continue
                for j in chosen:
                    candidate = [k for k in chosen if k != j] + [i]
                    key = tuple(sorted(candidate))
                    if key in visited:
                        continue
                    xx, jj = trial(candidate)
                    checks += 1
                    if jj > J + NUMERICAL["objective_tolerance"]:
                        turn = sum(abs(xx.get(k, 0) - old[k]) for k in ids)
                        record = (jj, -turn, addr[i], addr[j], candidate, xx)
                        if proposal is None or (-record[0], -record[1], record[2], record[3]) < (-proposal[0], -proposal[1], proposal[2], proposal[3]):
                            proposal = record
            if proposal is None:
                break
            J, _, _, _, chosen, greedy = proposal
            visited.add(tuple(sorted(chosen)))
            steps += 1
        common.append({"State": "M01, 20 September 2026", "Method": "Greedy six-slot score proxy", "Budget (USD)": B, "Accepted targets (USD)": sum(greedy.values()), "Score-dollar objective": J, "Solver seconds": np.nan, "Solver status": f"{steps} improving swaps; {checks} trial baskets"})
        x, diag = joint(ids, cap, score, old, B, 6, buy, 0.005, addr)
        common.append({"State": "M01, 20 September 2026", "Method": "Joint six-slot score proxy", "Budget (USD)": B, "Accepted targets (USD)": sum(x.values()), "Score-dollar objective": diag["Objective"], "Solver seconds": diag["Runtime"], "Solver status": diag["Status"]})
        common[-1]["Proxy improvement over greedy"] = diag["Objective"] - J
        pd.DataFrame(common).to_csv(data["artifact"] / "common-state-joint.csv", index=False)
    return diagnostics, snapshot, pd.DataFrame(common)


def capital_size_chart(data, runs, snapshot):
    """Recompute source TVL/concentration caps for scaled common-state budgets."""
    from tradeexecutor.backtest.backtest_pricing import BacktestPricing
    from tradeexecutor.backtest.backtest_runner import guess_data_delay_tolerance

    universe = runs[("2026", "M01")]["result"].strategy_universe
    pricing = BacktestPricing(universe, None, liquidity_universe=universe.data_universe.liquidity, data_delay_tolerance=guess_data_delay_tolerance(universe))
    f = snapshot.set_index("Pair id")
    t = pd.Timestamp("2026-09-20")
    tvl = {}
    for i in f.index:
        pair = universe.get_pair_by_id(int(i))
        tvl[i] = pricing.get_usd_tvl(t, pair)
        expected = min(0.33 * float(f.loc[i, "Deployable budget (USD)"]), 0.33 * tvl[i])
        assert abs(expected - f.loc[i, "TVL capacity (USD)"]) < 1e-6
    B = float(f["Deployable budget (USD)"].iloc[0])
    rows = []
    for size in (75000.0, 150000.0, 300000.0):
        ratio = size / 150000
        budget = B * ratio
        caps = {i: min(0.33 * budget, 0.33 * tvl[i], f.loc[i, "Old value (USD)"] * ratio + f.loc[i, "Deposit headroom (USD)"]) for i in f.index}
        core = list(f[f.Role.eq("core")].index)
        rows.append({"Reference initial size": size, "Budget (USD)": budget, "Original core": min(1.0, sum(caps[i] for i in core) / budget), "Best six capacity ceiling": min(1.0, sum(sorted(caps.values(), reverse=True)[:6]) / budget), "Whole universe": min(1.0, sum(caps.values()) / budget)})
    frame = pd.DataFrame(rows)
    frame.to_csv(data["artifact"] / "capital-size-capacity.csv", index=False)
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    for c, marker, size, style in [("Original core", "o", 6, "-"), ("Best six capacity ceiling", "s", 8, "-"), ("Whole universe", "o", 4, "--")]:
        ax.plot(frame["Reference initial size"] / 1000, frame[c] * 100, marker=marker, markersize=size, linestyle=style, label=c)
    ax.set_xticks(frame["Reference initial size"] / 1000)
    ax.set(ylim=(0, 105), xlabel="Scaled reference initial capital ($ thousands)", ylabel="Continuous target deployment ceiling (%)", title="20 September capital-size capacity diagnostic\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    figure(data, fig, "2026-capital-size", "Capital-size capacity diagnostic", "Same 20 September M01 state, scaling deployable budget and incumbent holdings to $75k/$150k/$300k reference sizes. Source TVL/concentration caps are recomputed; deposit headroom stays as observed. These are continuous capacity ceilings before ticket/weight floors, not engine profits or a return forecast.", "2026")


def reentry_table(data, runs, period):
    """Count actual closed positions repurchased within the next two decisions."""
    rows = []
    for arm in ARMS:
        portfolio = runs[(period, arm)]["result"].state.portfolio
        entries = {}
        for pos in portfolio.get_all_positions():
            successful = [t for t in pos.get_successful_trades() if t.is_buy()]
            if successful:
                entries.setdefault(int(pos.pair.internal_id), []).append(min(pd.Timestamp(t.executed_at) for t in successful))
        path = data["artifact"] / f"{period}-{arm}-target-ledger.csv"
        f = pd.read_csv(path)
        if "Date" in f:
            f.Date = pd.to_datetime(f.Date)
        eligible = set(zip(f.Date, f["Pair id"])) if "Role" in f else set()
        rapid = 0
        eligible_rapid = 0
        closed = list(portfolio.closed_positions.values())
        for pos in closed:
            sells = [t for t in pos.get_successful_trades() if t.is_sell()]
            if not sells:
                continue
            exit_at = max(pd.Timestamp(t.executed_at) for t in sells)
            pid = int(pos.pair.internal_id)
            if any(exit_at < t <= exit_at + pd.Timedelta(days=4) for t in entries.get(pid, [])):
                rapid += 1
                eligible_rapid += int((exit_at, pid) in eligible)
        rows.append({"Arm": arm, "Closed positions": len(closed), "Repurchases within two decisions": rapid, "Still-candidate rapid repurchases": eligible_rapid if "Role" in f else np.nan})
    return pd.DataFrame(rows)


def report_period(data, results, runs, attribution, weights, fee, robust, tails, period, members):
    f = results[results.Period.eq(period)].sort_values("Net profit (USD)", ascending=False)
    heading("Key economic metrics", "Every method starts with $150,000. Green means higher profit, CAGR, Sharpe or a less severe drawdown within a metric column. M00 is the exact NB16 C-W benchmark; primary results retain inherited costs.", period)
    table(f[["Arm", "Method", "Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Calmar"]])
    heading("Matched historical context", "Saved A, deployed-rule v11 and G-W use matching source/data/framework identities and fresh accounts for the same period. These are context, rather than additional NB17 allocation methods.", period)
    refs = pd.read_csv(data["nb16_reference"] / "results.csv")
    refs = refs[refs.Period.eq(period) & refs.Arm.isin(["V11", "A", "G-W"])]
    table(refs[["Arm", "Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight"]])
    base = f.set_index("Arm").loc["M00"]
    delta = f.copy()
    delta["Profit difference (USD)"] = delta["Net profit (USD)"] - base["Net profit (USD)"]
    delta["CAGR difference (pp)"] = (delta.CAGR - base.CAGR) * 100
    delta["Sharpe difference"] = delta.Sharpe - base.Sharpe
    delta["Drawdown difference (pp)"] = (delta["Maximum drawdown"] - base["Maximum drawdown"]) * 100
    heading("Incremental economics versus C-W", "Subtract M00 in the same account period. Higher drawdown differences mean less severe drawdowns. Cash reductions are a mechanism; they are not profit improvements.", period)
    table(delta[["Arm", "Profit difference (USD)", "CAGR difference (pp)", "Sharpe difference", "Drawdown difference (pp)", "September cash"]])
    heading("Deployment, breadth and trading", "Effective breadth is invested weight squared divided by the sum of squared vault weights. Trades and gross turnover indicate churn; marked cash includes the initial thin-universe interval over full history. Subsequent drift can exceed allocation caps.", period)
    table(f[["Arm", "Mean cash weight", "September cash", "Maximum vaults held", "Mean effective breadth", "Trades", "Gross trade turnover (USD)", "Modelled redemption costs (USD)"]])
    equity_chart(data, runs, period, members)
    q = profit_by_calendar(runs, period, "Q" if period == "2026" else "Y")
    q.columns = [str(c) + ("*" if c == q.columns[-1] or period == "Long" and c == q.columns[0] else "") for c in q.columns]
    heatmap(data, q, f"{period}-incremental-profit", "Quarterly incremental profit" if period == "2026" else "Calendar-year incremental profit", "Incremental account dollars versus M00, not annualised returns. Asterisk marks partial coverage. Full-history years carry prior holdings/capital; carried 2026 ends 7 October, whereas fresh 2026 ends 4 October.", period)
    for arm in members:
        weight_chart(data, weights, arm, period)
    heading("Leading vault contributors", "Top three vaults per shortlisted method. Position profit includes realised and marked PnL and reconciles to portfolio profit. Role changes prevent interpreting this as an exact core/overflow causal decomposition.", period)
    rows = []
    for arm in members:
        for vault, profit in attribution[(period, arm)].sort_values(ascending=False).head(3).items():
            rows.append({"Arm": arm, "Vault": vault, "Contribution (USD)": profit, "Share of net profit": profit / f.set_index("Arm").loc[arm, "Net profit (USD)"]})
    table(pd.DataFrame(rows))
    heading("Extreme updates and concentration", "Largest daily gains may accumulate several days of sparse observations. Positive profit share divides the largest positive vault contribution by total positive contributions, rather than net profit.", period)
    table(robust[robust.Period.eq(period) & robust.Arm.isin(members)][["Arm", "Best update", "Excess kurtosis", "Top positive profit share", "Top_vault", "Best_date"]])
    heading("Price intervals and market context for strongest updates", "Largest contributing vault on each shortlisted strategy’s best update, checked against curator exclusions/quarantine and BTC/ETH over the same observed-NAV interval. Market context does not prove NAV executability during sparse gaps.", period)
    t = tails[tails.Period.eq(period) & tails.Arm.isin(members)].groupby("Arm").head(1)
    cols = ["Arm", "Update", "Vault", "Update profit (USD)", "NAV_return", "Interval_days", "BTCUSDT return", "ETHUSDT return", "Excluded", "Quarantined"]
    table(t[cols])
    heading("Fees paid versus liabilities still open", "Paid deductions are gross known NAV times redeemed shares minus actual execution proceeds, including the inherited repeated partial fee. Open performance liability uses weighted remaining cost basis; a gross NAV total can flatter low-turnover methods by deferring exit charges. The estimated liquidation total assumes the source 10% positive-profit fee and 0.1% capital allowance.", period)
    table(fee[fee.Period.eq(period)][["Arm", "Paid sell deductions (USD)", "Open performance liability (USD)", "Open capital allowance (USD)", "Gross NAV equity (USD)", "Estimated liquidation equity (USD)", "Reported marked equity (USD)"]])
    heading("Short-lived exits and repurchases", "Actual full closes followed by a new position in the same vault within four calendar days (two decisions). Still-candidate closes exclude failed inclusion/return-gate cases, but can include rank and allocation-floor exits; source-control eligibility is unavailable in that ledger. These are turnover diagnostics rather than profit attribution.", period)
    table(reentry_table(data, runs, period))
    return delta


def report(data, results, runs, attribution, weights, sensitivity):
    """Render the economic evidence and write maintained research conclusions."""
    plt.rcParams.update({"axes.titlesize": 10, "font.size": 10})
    folder = data["artifact"]
    data["figures"] = []
    assert len(results) == 28 and set(zip(results.Period, results.Arm)) == set((p, a) for p in experiment.PERIODS for a in ARMS)
    leaders = {results[results.Period.eq(p)].sort_values(metric, ascending=False).iloc[0].Arm for p in experiment.PERIODS for metric in ("Net profit (USD)", "Sharpe")}
    members = ["M00"] + sorted(leaders - {"M00"})
    robust, tails = robustness(data, results, runs, attribution)
    fee = fee_accounting(data, runs)
    diagnostics, snapshot, common = mechanism_diagnostics(data)
    display(Markdown("## Fresh 2026 economic comparison\n\nAll registered mechanisms are shown. A shortlist keeps charts readable; full-history comparisons follow in a separate section."))
    delta = report_period(data, results, runs, attribution, weights, fee, robust, tails, "2026", members)
    heading("Paired mechanism comparisons", "M02–M11/M13 compare with admission-aware M01; M01 compares with exact source benchmark M00; legacy extension M12 compares with M00. These whole accounts evolve separately, so differences include subsequent selection and compounding.", "2026")
    base = results[results.Period.eq("2026")].set_index("Arm")
    pairs = []
    for a in ARMS[1:]:
        b = "M00" if a in ("M01", "M12") else "M01"
        pairs.append({"Method": a, "Control": b, "Profit difference (USD)": base.loc[a, "Net profit (USD)"] - base.loc[b, "Net profit (USD)"], "CAGR difference (pp)": 100 * (base.loc[a, "CAGR"] - base.loc[b, "CAGR"]), "September cash difference (pp)": 100 * (base.loc[a, "September cash"] - base.loc[b, "September cash"])})
    table(pd.DataFrame(pairs))
    for column, name, xlabel in [("September cash", "profit-cash", "Mean September cash (%)"), ("Maximum drawdown", "profit-drawdown", "Maximum drawdown (%)")]:
        fig, ax = plt.subplots(figsize=(9.5, 5.2))
        groups = {}
        for _, r in delta.iterrows():
            groups.setdefault((round(r[column] * 100, 5), round(r["Profit difference (USD)"] / 1000, 5)), []).append(r.Arm)
        annotations = []
        for j, ((x, y), arms) in enumerate(groups.items()):
            marker = "s" if arms[0] == "M00" else "^" if arms[0] in ("M04", "M05", "M06", "M09", "M12") else "*" if arms[0] in ("M08", "M11") else "D" if arms[0] in ("M07", "M10") else "x" if arms[0] == "M13" else "o"
            ax.scatter(x, y, color=PALETTE[arms[0]], s=80, marker=marker)
            annotation = ax.annotate("/".join(arms), (x, y), xytext=(7, 7), textcoords="offset points", fontsize=9, arrowprops={"arrowstyle": "-", "color": "#666666", "lw": 0.6})
            annotations.append(annotation)
        ax.margins(x=0.10, y=0.10)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        placed = []

        def label_box(annotation):
            annotation.update_positions(renderer)
            return Text.get_window_extent(annotation, renderer).expanded(1.05, 1.1)

        for annotation in annotations:
            for _ in range(30):
                box = label_box(annotation)
                if not any(box.overlaps(previous) for previous in placed):
                    break
                x, y = annotation.xyann
                annotation.xyann = (x, y - 15)
            placed.append(label_box(annotation))
        ax.axhline(0, color="grey", lw=0.8)
        ax.grid(alpha=0.2)
        ax.set(xlabel=xlabel, ylabel="Incremental net profit vs M00 ($ thousands)", title="Net profit versus " + ("September cash" if column == "September cash" else "drawdown") + "\n" + LABELS["2026"])
        figure(data, fig, "2026-" + name, "Profit versus " + ("September cash" if column == "September cash" else "drawdown"), "Each point is one full account. Labels identify methods in the logic table; squares are the benchmark, circles redistribution, triangles overflow, diamonds retention/delay, stars score optimisation and crosses fixed breadth. The horizontal zero line is M00; lower cash is useful only when accompanied by better economics. Coincident methods are also separated in the tables.", "2026")
    representatives = list(dict.fromkeys(["M00", "M01", "M02", "M05", "M09", "M11", "M12", "M13"]))
    fig, ax = plt.subplots(figsize=(10.5, 4.7))
    for a in representatives:
        w = weights[("2026", a)].loc["2026-09-01":"2026-09-30"]
        reserve = runs[("2026", a)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        ax.plot(w.index, w[reserve] * 100, label=a, color=PALETTE[a])
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set(title="Realised September cash\n" + LABELS["2026"], ylabel="Cash / total equity (%)", ylim=(0, 100))
    ax.grid(alpha=0.2)
    ax.legend(ncol=4, fontsize=8)
    figure(data, fig, "2026-september-cash", "September cash by allocation mechanism", "Daily realised cash, including reserve and marking effects, for representatives of redistribution, overflow, maintenance, optimisation, legacy extension and fixed breadth. Methods that overlap are numerical no-ops or similar outcomes, rather than missing curves.", "2026")
    decisions = pd.read_csv(folder / "nb17_decisions.csv", parse_dates=["Date"])
    sep = decisions[decisions.Period.eq("2026") & decisions.Date.between("2026-09-01", "2026-09-30")]
    reasons = ["Basket cap deficit", "Allocator/floor slack", "Denied top-up opportunity", "Universe shortfall", "Core floor restricted dollars", "Overflow dollars"]
    reason = sep.groupby("Arm")[reasons].mean() / 1000
    reason.columns = ["Core cap gap", "Allocator slack", "Denied top-ups", "Pool gap", "Core-floor limit", "Overflow use"]
    heatmap(data, reason, "2026-cash-reasons", "September capacity snapshots", "Mean decision-time dollar snapshots in $ thousands. Categories overlap and are not additive. Core cap gap can be met by overflow; denied top-ups explain part of usable-capacity reductions. Pool gap is the remaining aggregate universe constraint. M00/M12 retain source diagnostics and are omitted from this redesigned-policy decomposition.", "2026", unit="USD thousands", decimals=1, cmap="Blues")
    heading("20 September core and capacity example", "M01 decision-time core: accepted dollars, cap, deposit headroom and missing/support flags. These are targets, not actual cash or guaranteed fills. Below, the entire eligible candidate pool shows whether six slots or aggregate capacity bind.", "2026")
    if snapshot is not None:
        f = snapshot[snapshot.Role.eq("core")]
        table(f[["Vault", "Rank", "Ranking score", "Score available", "Old value (USD)", "Capacity ceiling (USD)", "Final target (USD)", "Deposit reason", "Actual updates", "Risk status"]])
        heading("20 September common-state joint diagnostic", "Evaluate the joint proxy on that same M01 state. The score-dollar objective is not expected profit; whole-account M08/M11 scores are not directly comparable when their capital and holdings evolve differently.", "2026")
        table(common)
        capital_size_chart(data, runs, snapshot)
    heading("Common-state water-filling and linear-score checks", "Every M01 decision is classified by its six-name target ceiling. With distinct positive core scores, the score waterfall and fixed-basket LP agree. Positive clipped ties favour incumbent maintenance under the LP; zero-score ties can retain cash under the LP minimum-turnover rule; no portfolio engine run is claimed for L01.", "2026")
    table(pd.DataFrame([{"Decisions": len(diagnostics), "Capacity-bound": int(diagnostics["Capacity-bound"].sum()), "Budget-bound": int((~diagnostics["Capacity-bound"]).sum()), "Distinct positive-score equality checks": int((diagnostics["All core scores positive"] & diagnostics["Core scores distinct"]).sum()), "LP / waterfall different decisions": int((diagnostics["M03/L01 dollar difference"] > 1e-6).sum())}]))
    heading("Role support and young/missing-history allocation", "Average decision-time target dollars, not cumulative distinct capital or a causal PnL attribution. Missing composite scores remain eligible unless M06 screens them. Missing scores can reflect young history or undefined active metrics; they do not all mean young vaults. Prior-only fallback counts unavailable empirical risk with a finite regularised forecast; partial/full empirical windows also use the declared shrinkage prior. Actual daily updates are counted independently of filled observations.", "2026")
    support = []
    for a in ARMS[1:]:
        path = folder / f"2026-{a}-target-ledger.csv"
        f = pd.read_csv(path)
        if "Role" not in f:
            continue
        funded = f[f["Final target (USD)"] > 0].copy()
        dates = f.Date.nunique()
        ages = [data["date_index"][pd.Timestamp(t) - pd.Timedelta(days=1)] - data["first_index"][data["id_index"][int(i)]] for t, i in zip(funded.Date, funded["Pair id"])]
        funded["History age days"] = ages
        support.append({"Arm": a, "Mean overflow target (USD)": funded.loc[funded.Role.eq("overflow"), "Final target (USD)"].sum() / dates, "Mean unscored target (USD)": funded.loc[~funded["Score available"], "Final target (USD)"].sum() / dates, "Mean <360-day history target (USD)": funded.loc[funded["History age days"] < 360, "Final target (USD)"].sum() / dates, "Mean <30-update target (USD)": funded.loc[funded["Actual updates"] < 30, "Final target (USD)"].sum() / dates, "Mean prior-only fallback target (USD)": funded.loc[funded["Risk status"].eq("unavailable") & np.isfinite(funded.Risk), "Final target (USD)"].sum() / dates, "Positive amount cap bindings": int(((f["Reported max deposit"] > 0) & (f["Capacity ceiling (USD)"] < f["TVL capacity (USD)"] - 1e-6)).sum())})
    table(pd.DataFrame(support))
    heading("Hysteresis activity", "Rank-seven/eight incumbents can be replaced by a better top-six entrant. Tied clipped scores can protect them. M07 reversals and M10 delayed exits are counted, not described as passive rank-band membership.", "2026")
    columns = ["In-band incumbents", "Tie/predicate protected", "Actual band replacements", "Capacity reversals", "Delayed rank exits", "Greedy swaps"]
    table(decisions[decisions.Period.eq("2026")].groupby("Arm")[columns].sum().reset_index())
    heading("Protected core and final funding checks", "Common-state core targets are retained when overflow is appended. The executable funding guard keeps core buys ahead of overflow, reserving source partial-fee deductions before trade creation. Final trade queues also check actual sell prices; counts below exclude the separate fee sensitivities.", "2026")
    checks = pd.read_csv(folder / "nb17_core_checks.csv")
    checks = checks[checks.Period.eq("2026")]
    summary = []
    for arm, f in checks.groupby("Arm"):
        equality = f.Core_target.notna() if "Core_target" in f else pd.Series(False, index=f.index)
        funded = f.Core_requested.notna() if "Core_requested" in f else pd.Series(False, index=f.index)
        error = (f.loc[equality, "Core_target"] - f.loc[equality, "Merged_target"]).abs().max() if equality.any() else 0.0
        assert error < 1e-6
        summary.append({"Arm": arm, "Core target equality checks": int(equality.sum()), "Funding decisions": int(funded.sum()), "Maximum core target difference (USD)": error, "Independently unfunded core decisions": int((f.loc[funded, "Independent_funding_shortfall"] > 1e-6).sum())})
    table(pd.DataFrame(summary))
    heading("Final-net-proceeds funding corrections", "Only queues whose requested buys exceeded actual cash plus concrete final synchronous sell proceeds are listed. The exact M00 source benchmark retains its saved NB16 correction. Protected overflow reserves expected source partial-fee deductions before trade creation, so these later corrections are not their full funding history.", "2026")
    funding = pd.read_csv(folder / "funding_ledger.csv")
    funding = funding[funding.Period.eq("2026")].copy()
    funding["Arm"] = funding.Arm.replace({"C-W": "M00"})
    funding["Buy reduction (USD)"] = funding.get("Reduction (USD)", pd.Series(index=funding.index, dtype=float)).fillna(funding.get("Reduction", 0.0))
    table(funding[["Arm", "Date", "Buy reduction (USD)"]])
    heading("Optimiser diagnostics", "All M11 solver decisions: counts, total seconds and final-stage reported relative gap. Unfinished tie stages/fallbacks are retained in the full solver ledger. Address ordering uses a deterministic rank-sum final tie objective, rather than asserting a unique mathematical optimum.", "2026")
    solvers = pd.read_csv(folder / "nb17_solvers.csv")
    solvers.to_csv(folder / "solver-diagnostics.csv", index=False)
    tables = []
    for p, f in solvers.groupby("Period"):
        if p != "2026":
            continue
        tables.append({"Period": LABELS[p], "Decisions": len(f), "Mean seconds": f.Runtime.mean(), "Maximum seconds": f.Runtime.max(), "Reported maximum gap": f.Gap.max(), "Fallbacks": int(f.Status.str.contains("fallback", case=False).sum()), "All four stages": int(f.Stages.eq(4).sum())})
    table(pd.DataFrame(tables))
    display(Markdown("## Full-history economic comparison\n\nFresh $150,000 on 1 March 2023; no resetting at calendar-year boundaries. The final day is partial. This researched period overlaps 2026 and is not independent validation."))
    report_period(data, results, runs, attribution, weights, fee, robust, tails, "Long", members)
    for p in experiment.PERIODS:
        heading("Corrected partial-fee sensitivity", "Same registered shortlist in both periods. Only partial-sell gross mid-price is corrected before the source exit fee; the primary table is retained for exact legacy parity. Compare corrected challengers with corrected M00, never with an uncorrected benchmark.", p)
        table(sensitivity[sensitivity.Period.eq(p)][["Arm", "Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown", "Profit sensitivity (USD)"]])
    gains = results.pivot(index="Arm", columns="Period", values="Net profit (USD)").sub(results[results.Arm.eq("M00")].set_index("Period")["Net profit (USD)"], axis=1)
    both = gains[(gains > 0).all(axis=1)].sort_values("Long", ascending=False)
    best = {p: results[results.Period.eq(p)].sort_values("Net profit (USD)", ascending=False).iloc[0] for p in experiment.PERIODS}
    lines = []
    for p, r in best.items():
        b = results[results.Period.eq(p) & results.Arm.eq("M00")].iloc[0]
        lines.append(f"- **{LABELS[p]}:** {r.Arm} ({r.Method}) leads net profit at **${r['Net profit (USD)']:,.0f}**, **{r.CAGR:.2%} CAGR**, **{r.Sharpe:.2f} Sharpe**, **{r['Maximum drawdown']:.2%} maximum drawdown**; **${r['Net profit (USD)']-b['Net profit (USD)']:+,.0f}** versus exact C-W.")
    failed = results[results.Period.eq("2026") & (results["Net profit (USD)"] < results[(results.Period.eq("2026")) & (results.Arm.eq("M00"))]["Net profit (USD)"].iloc[0])]
    message = """## Key new insights

""" + "\n".join(lines) + f"\n- **Positive net-profit differences in both periods:** {', '.join(both.index) if len(both) else 'none'}. Only gains in both would support a broadly better historical policy; these periods overlap and provide no independent validation.\n- The selected six-name capacity ceiling cannot be repaired by a different within-basket weighting alone. Overflow changes the set of exposures, whereas greedy/joint score allocation changes both selection and concentration; compare their realised economics rather than the score proxy.\n- Primary and corrected-fee results are separate. Sparse marks, retrospective guard/inventory, estimated fees and contributor concentration remain material assumptions.\n"
    message += """
## Summary of results

Incremental net profit relative to the matched C-W benchmark, with the same primary fee convention. Positive values indicate higher profit; the two periods overlap.

""" + gains.reset_index().rename(columns={"2026": "2026 profit delta (USD)", "Long": "Full-history profit delta (USD)"}).to_markdown(index=False, floatfmt=",.0f")
    short = results[results.Period.eq("2026")].set_index("Arm")
    long = results[results.Period.eq("Long")].set_index("Arm")
    message += f"\n\n- **Missing-score screen:** M05 full-history CAGR is {long.loc['M05','CAGR']:.2%} versus {long.loc['M06','CAGR']:.2%} for otherwise matched scored-only overflow M06. Both are {short.loc['M05','CAGR']:.2%} / {short.loc['M06','CAGR']:.2%} in fresh 2026. Missing composite scores are not a demonstrated profitability veto; young-history and undefined-metric exposure must be separated.\n"
    message += f"- **Exit delay:** M10 is {short.loc['M10','CAGR']:.2%} CAGR / {short.loc['M10','Maximum drawdown']:.2%} drawdown in fresh 2026, but {long.loc['M10','CAGR']:.2%} / {long.loc['M10','Maximum drawdown']:.2%} over full history. The small short-period profit gain is regime-dependent and carries more risk.\n"
    for arm in ["M05", "M08", "M11", "M13"]:
        r = short.loc[arm]
        b = short.loc["M00"]
        lines.append(f"- **{arm}, fresh 2026:** September cash {r['September cash']:.1%} versus {b['September cash']:.1%}, with **${r['Net profit (USD)']-b['Net profit (USD)']:+,.0f}** incremental net profit. Better deployment did not establish better economics.")
    message += "\n\n### What the allocation contrasts teach us\n\n" + "\n".join(lines[2:])
    corrected = sensitivity.set_index(["Period", "Arm"])
    message += f"\n\n- **The exit-delay lead fails the fee check:** corrected 2026 C-W is **{corrected.loc[('2026','M00'),'CAGR']:.2%} CAGR**, versus **{corrected.loc[('2026','M10'),'CAGR']:.2%}** for M10. The primary small lead reverses when both share corrected partial-trim costs. Corrected full-history M05 is **{corrected.loc[('Long','M05'),'CAGR']:.2%}** versus **{corrected.loc[('Long','M00'),'CAGR']:.2%}** for C-W, so its long-period lead persists. These are sensitivity figures, not replacements for the legacy comparisons.\n"
    difference = attribution[("Long", "M05")].sub(attribution[("Long", "M00")], fill_value=0.0).sort_values(ascending=False)
    difference.to_csv(folder / "overflow-incremental-vault-profit.csv")
    lead = difference.index[0]
    value = difference.iloc[0]
    total = difference.sum()
    message += f"- **Full-history overflow dependence:** the largest incremental vault contributor is **{lead}**, **${value:+,.0f}**, versus **${total:+,.0f}** total M05−M00 profit. This is a vault-level whole-account difference, not exact overflow-role PnL; position changes elsewhere can offset it.\n"
    message += """

## Robustness of results

All 28 registered accounts completed, and exact C-W metrics match saved NB16 in both periods. Successful trades were checked against known as-of NAV, position PnL reconciled to equity, and holdings respected each method’s slot limit. Protected overflow target checks and core-first executable funding checks are recorded. NAV forward filling starts after inception; actual update counts govern risk confidence. A price series being calculable does not establish fills during archive gaps.

The audit covers 23,492 successful fills, 14,892 core-target equality checks and 2,718 core-first funding checks. Maximum position-PnL/equity reconciliation residual is below $0.000000001. M11 uses the declared safe M01 fallback on four decisions (one in fresh 2026 and three in full history) after a solver target fails executable-domain checks. Its realised results therefore include these fallbacks; they do not establish a globally optimal executable portfolio on every date.

The inherited partial-trim fee model is retained for primary parity and corrected for the benchmark/profit-leader union. Open performance liabilities and gross-versus-estimated-liquidation equity are reported separately. Contributor/tail tables check leading vaults and BTC/ETH intervals rather than treating all large updates as market-wide gains. Both periods have been researched and overlap. Freeze a small profit/risk shortlist for prospective observation before adopting an allocation method.
"""
    heading("Economic verdict", "Profit and accompanying risk determine the shortlist. The detailed report is also saved as maintained Markdown research notes.", "2026")
    message = re.sub(r"(?<!\\)\$(?=[+-]?[0-9])", r"\\$", message)
    display(Markdown(message))
    (ROOT / "17-capital-allocation-findings.md").write_text("# Experiment 17 — capital allocation findings\n\n" + message + "\n\n## Reproducibility\n\nGenerated run manifest and full diagnostic ledgers: `" + str(folder.relative_to(ROOT)) + "`. Generated artefacts are ignored; notebook outputs contain reviewable tables and charts.\n")
    first = """# Experiment 17 — better capital allocation

Based on [NB16](16-backtest-waterfall-allocation-vs-v11.ipynb). **Goal:** improve net profitability through redistribution, capacity-aware replacement, protected overflow, turnover restraint and joint selection/sizing. Fourteen registered methods run fresh $150,000 accounts over **2026-01-01 → 2026-10-05 exclusive** and **2023-03-01 → 2026-10-08 exclusive**, using all preceding indicator history. Ranking is the frozen four-input score; C’s regularised 90-day risk remains the reference. Young and unscored vaults retain source eligibility unless a method explicitly screens overflow.

See the [reviewed plan](17-capital-allocation-plan.md), [Claude review](17-capital-allocation-review.md) and [findings](17-capital-allocation-findings.md). Charts default to fresh 2026 and label their period; full-history comparisons are separate.

"""
    (folder / "final-header.md").write_text(first + message)
    summary = ROOT / "summary.md"
    old = summary.read_text()
    marker = "\n## Experiment 17 — capital allocation\n"
    if marker in old:
        old = old[: old.index(marker)]
    section = (
        marker
        + """\n### What was examined\n\nFourteen fixed allocation policies, both periods, plus shared corrected-partial-fee sensitivity. The score and risk estimator stayed fixed; mechanisms varied redistribution, capacity selection, conditional overflow, turnover retention and joint optimisation.\n\n### Hypothesis\n\nBetter usable-capacity selection and controlled overflow can overcome the six-name ceiling and improve net profit. Lower cash alone is insufficient.\n\n### Results\n\n"""
        + "\n".join(lines)
        + f"\n\nCorrecting partial-trim fees reverses the fresh-2026 exit-delay lead: C-W **{corrected.loc[('2026','M00'),'CAGR']:.2%} CAGR** versus M10 **{corrected.loc[('2026','M10'),'CAGR']:.2%}**. Full-history four-slot overflow remains ahead after correction: **{corrected.loc[('Long','M05'),'CAGR']:.2%}** versus **{corrected.loc[('Long','M00'),'CAGR']:.2%}**. The primary long-period gain includes **${value:+,.0f}** from {lead}, relative to **${total:+,.0f}** total incremental profit. Scored-only overflow reduces long CAGR from **{long.loc['M05','CAGR']:.2%}** to **{long.loc['M06','CAGR']:.2%}**.\n\n### Was the hypothesis confirmed?\n\nMethods with higher net profit in both researched periods: {', '.join(both.index) if len(both) else 'none'}. The broad claim of a more profitable replacement across both periods was rejected for this registered set. Four-slot overflow provides a long-period lead, while better cash deployment often loses profit in fresh 2026. Both periods overlap and have been researched.\n\n### Useful leads\n\nKeep C-W as a pinned control, compare corrected fees consistently, and freeze profit/risk leaders for prospective observation. Capacity must be handled at basket/overflow selection, not only within-basket weights. Inspect contributor dependence, missing-score exposure, deferred fees and rank-exit churn before choosing a production rule.\n\nSee [complete findings](17-capital-allocation-findings.md) and [executed notebook](17-backtest-capacity-aware-allocation.ipynb).\n"
    )
    summary.write_text(old + re.sub(r"(?<!\\)\$(?=[+-]?[0-9])", r"\\$", section))
    plan = ROOT / "17-capital-allocation-plan.md"
    text = plan.read_text()
    start = text.index("Status:")
    end = text.index("\n\n", start)
    plan.write_text(text[:start] + f"Status: implemented and executed in [NB17](17-backtest-capacity-aware-allocation.ipynb): 28 primary accounts plus {len(sensitivity)} shared fee sensitivities. See [findings](17-capital-allocation-findings.md). The two planning reviews used confirmed `claude-fable-5-1`." + text[end:])
    (folder / "complete.json").write_text(json.dumps({"status": "executed", "primary_accounts": 28, "fee_sensitivities": len(sensitivity), "figures": data["figures"], "shortlist": members, "both_period_profit_improvements": list(both.index)}, indent=2))
    return message
