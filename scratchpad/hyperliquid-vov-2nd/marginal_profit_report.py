"""Separate, period-labelled figures and economic interpretation for NB21."""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from IPython.display import Markdown, display
from scipy.stats import spearmanr
from matplotlib import font_manager
from pathlib import Path

_unicode_font = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
if _unicode_font.exists():
    font_manager.fontManager.addfont(str(_unicode_font))
    plt.rcParams["font.family"] = ["DejaVu Sans", "Arial Unicode MS"]
from marginal_profit_data import ROOT, LABELS, ARMS, REGISTRY
from allocation_comparison import figure, heading, robustness
from capital_allocation_report import fee_accounting, heatmap

PALETTE = {a: plt.get_cmap("tab20")(j) for j, a in enumerate(ARMS)}
for j, a in enumerate(("BHALF", "BDOUBLE", "H07", "MARGIN", "GATE14")):
    PALETTE[a] = plt.get_cmap("Dark2")(j)
QUARTERS = {"2026Q1": "#2563eb", "2026Q2": "#e69f00", "2026Q3": "#009e73", "2026Q4": "#cc79a7"}


def table(f, hide=False):
    formats = {c: "${:,.0f}" if "(USD)" in str(c) or "usd" in str(c).lower() else "{:.1%}" if c in ["CAGR", "Maximum drawdown", "Cumulative return", "Mean cash weight", "September cash", "Largest vault weight"] else "{:.3f}" for c in f.select_dtypes("number")}
    s = f.style.format(formats, na_rep="—")
    for c in ("CAGR", "Sharpe", "Maximum drawdown", "Net profit (USD)", "Profit difference (USD)"):
        if c in f:
            s = s.background_gradient(subset=[c], cmap="RdYlGn")
    if hide:
        s = s.hide(axis="index")
    display(s)


def control_audit(data, results, spells, checks):
    heading("Exact control replication", "Complete daily equity paths reproduce NB20, under the same source/accounting identity. Both calendars are shown here solely as the control audit.", "2026")
    table(pd.read_csv(data["artifact"] / "control-parity.csv"), True)
    heading("Independent algebra and feasibility examples", "Check exact liquidation values across basis kinks, partial sales/top-ups, missing inception and allocation beyond six names.", "2026")
    table(checks, True)
    heading("Control fees and liabilities", "Paid modelled sell fees and still-open liquidation liabilities are distinct. Their difference from gross profit explains the economic cost of trading.", "2026")
    f = data["fee_audit"].query("Period == '2026'").copy()
    m = results.query("Period == '2026'").set_index("Arm")
    f["Net profit (USD)"] = f.Arm.map(m["Net profit (USD)"])
    f["Gross profit (USD)"] = f["Net profit (USD)"] + f["Paid sell deductions (USD)"] + f["Open performance liability (USD)"] + f["Open capital allowance (USD)"]
    table(f.drop(columns=["Period"]), True)
    heading("Holding duration and net PnL", "Duration by trade count differs from dollar-day exposure. Open spells are censored and shown separately. The horizon decision is frozen before challenger results.", "2026")
    f = spells[spells.Period.eq("2026")].groupby(["Arm", "Bucket", "Open"]).agg(Positions=("Position", "size"), Net_profit_usd=("Net_profit", "sum"), Dollar_days=("Dollar_days", "sum"), Median_days=("Days", "median")).reset_index()
    table(f, True)
    heading("Strategy logic comparison", "Controls retain their source score, risk weighting and six-slot machinery. Main challengers use complete marginal path values; one input or action restriction changes in each ablation.", "2026")
    display(Markdown("""| Arm | Signal | Sizing and cash | Admission / exits |
| --- | --- | --- | --- |
| B00 | 48% CAGR360 + 32% Sortino45 + 10% CAGR180 + 10% Sortino30 | Regularised 90-day risk waterfall; source 98% deployment | Six slots, source hysteresis and 14-day gate |
| B01 | 60% CAGR360 + 40% Sortino45 | Source inverse 90-day variance; source 98% deployment | Six slots, source hysteresis and 14-day gate |
| F01 | Same as B00 | Same as B00; 1% sell band | Same as B00 |
| P00 | Support-conditioned return distribution | Marginal net value, common loss budget, cash alternative | Adaptive breadth and full-account replacement |
| D00 | Conditional negative-return probability | Same as P00 | Same as P00 |
| M00 | D probability plus conditional gain/loss magnitudes | Same as P00 | Same as P00 |
| C01 | Calibrated original C00 scalar score | Same as P00 | Same as P00 |
| D02 | Same as D00 | Same as D00 | Six-slot ablation |
| D03 | Same as D00 | Same as D00 | New capital only; inherited operational/dust handling |
| D04 | Same as D00 | No aggregate loss budget; physical caps retained | Same as D00 |
"""))
    heading("Registered policy horizon", "Short spells must dominate both capital and absolute profit in both controls to justify shortening the default 30-day policy horizon.", "2026")
    table(data["horizon_audit"].rename(columns={"Dollar_days": "Short-spell capital share", "Abs_profit": "Short-spell absolute PnL share"}))


def panel_audit(data):
    f = data["panel"]
    q = f[f.Date.ge("2026-01-01") & f.Date.lt("2026-10-05") & f.operational_pool]
    heading("Learning evidence versus carried marks", "Metrics use causal forward fill. Learning endpoints require an actual mark within the last day of the horizon; unresolved returns are not confirmed zero outcomes.", "2026")
    rows = []
    for h, g in q.groupby("H"):
        rows.append(dict(Horizon=h, Rows=len(g), Vaults=g.Pair.nunique(), Resolved_fraction=g.Resolved.mean(), Young_under_45_days=g.recorded_age.lt(45).mean(), Missing_score=g.c00_score.isna().mean(), Permission_clock_unknown=g.permission_unknown.mean(), Median_quote_age_days=g.quote_age.median()))
    table(pd.DataFrame(rows), True)
    heading("Observation-frequency coverage", "Reporting-frequency groups show whether fixed-horizon resolution selects frequent reporters. These are diagnostics, not vault admission filters.", "2026")
    f0 = q[q.H.eq(data["policy_horizon"])].copy()
    f0["Reporting_group"] = pd.qcut(data["panel"].loc[f0.index, "updates_30"], 10, duplicates="drop")
    table(f0.groupby("Reporting_group", observed=True).agg(Rows=("Pair", "size"), Resolved_fraction=("Resolved", "mean"), Young_fraction=("recorded_age", lambda x: x.lt(45).mean())).reset_index(), True)
    permission = f0.groupby(f0.Date.dt.to_period("Q")).agg(Rows=("Pair", "size"), Unknown_fraction=("permission_unknown", "mean"), Deposit_open_fraction=("can_deposit", "mean"))
    table(permission)


def training_audit(data, registration):
    heading("Chronological model support", "Monthly fits use matured prior labels. The penalty is selected from three purged folds once per horizon/calendar year; monthly coefficients still refit.", "2026")
    audit = data["training_audit"]
    f = audit[pd.to_datetime(audit.Fit).ge("2026-01-01")]
    table(f, True)
    heading("Frozen risk budget", "The loss budget uses a common support model, not personalised performance forecasts. It is an estimated expected-downside quantity, not a maximum-loss guarantee.", "2026")
    table(pd.DataFrame([{"Period": "2026", "B": registration["2026"], "Historical binding fraction": registration["historical_binding_fraction"]}, {"Period": "Long", "B": registration["Long"], "Historical binding fraction": np.nan}]), True)


def signal_report(data):
    f = data["predictions"]
    q = f[f.Date.ge("2026-01-01") & f.Date.lt("2026-10-05") & f.operational_pool & f.Resolved & f.Prior_available].copy()
    q["Realised net"] = 0.999 * q.Y - 0.1 * np.maximum(q.Y, 0) - 0.001
    q["Quarter"] = q.Date.dt.to_period("Q").astype(str)
    records = []
    for (h, model), g in q.groupby(["H", "Model"], sort=True):
        w = 1 / g.groupby("Date").Date.transform("size")
        y = g.Y.lt(0).astype(float)
        records.append(dict(Horizon=h, Model=model, Rows=len(g), Origins=g.Date.nunique(), Time_blocks=((g.Date - pd.Timestamp("2026-01-01")).dt.days // h).nunique(), Brier=float(np.average((g.p - y) ** 2, weights=w)), Net_MAE=float(np.average(abs(g.net - g["Realised net"]), weights=w)), Mean_forecast=float(np.average(g.net, weights=w)), Mean_outcome=float(np.average(g["Realised net"], weights=w)), Supported_fraction=g.Supported.mean()))
        fig, ax = plt.subplots(figsize=(9.3, 4.8))
        for quarter, color in QUARTERS.items():
            part = g[g.Quarter.eq(quarter)]
            if not len(part):
                continue
            ax.scatter(part.net * 100, part["Realised net"] * 100, s=7, alpha=0.20, color=color, label=quarter, rasterized=True)
        bins = pd.qcut(g.net, 10, duplicates="drop")
        means = []
        rng = np.random.default_rng(2121 + h)
        for key, part in g.groupby(bins, observed=True):
            weights = 1 / g.groupby("Date").Date.transform("size").loc[part.index]
            x = float(np.average(part.net, weights=weights))
            y = float(np.average(part["Realised net"], weights=weights))
            block = (part.Date - pd.Timestamp("2026-01-01")).dt.days // (2 * h)
            b = part.assign(w=weights, wy=part["Realised net"] * weights).groupby(block).agg(w=("w", "sum"), wy=("wy", "sum"))
            lo = hi = np.nan
            if len(b) >= 10:
                indices = rng.integers(0, len(b), size=(499, len(b)))
                samples = b.wy.to_numpy()[indices].sum(axis=1) / b.w.to_numpy()[indices].sum(axis=1)
                lo, hi = np.quantile(samples, [0.025, 0.975])
            means.append((x, y, lo, hi))
        means = pd.DataFrame(means, columns=["x", "y", "lo", "hi"]).sort_values("x")
        if len(means):
            ax.plot(means.x * 100, means.y * 100, "ko-", ms=4, lw=1.4, label="Equal-date binned means")
            valid = means.lo.notna()
            if valid.any():
                ax.fill_between(means.loc[valid, "x"] * 100, means.loc[valid, "lo"] * 100, means.loc[valid, "hi"] * 100, color="black", alpha=0.12, label="Exploratory block band")
            else:
                ax.text(0.02, 0.96, "Too few calendar blocks for uncertainty bands", transform=ax.transAxes, va="top", fontsize=8)

        ax.axhline(0, color="#555555", lw=0.8)
        ax.axvline(0, color="#555555", lw=0.8)
        ax.set_yscale("symlog", linthresh=2)
        ax.set(title=f"{model}: predicted versus realised net return, {h}-day horizon\n" + LABELS["2026"], xlabel="Forecast fresh net return (%)", ylabel="Realised fresh net return (%) — symlog")
        ax.legend(fontsize=8, loc="best")
        ax.grid(alpha=0.15)
        figure(data, fig, f"2026-{model}-{h}-scatter", f"{model}: net-return forecast, {h} days", "Quarter-coloured eligible vault observations; black points are descriptive score-bin means. Symlog retains extreme losses and gains. Overlapping targets and reporting-dependent resolution prevent row-wise significance claims.", "2026")
        if model == "M":
            continue
        fig, ax = plt.subplots(figsize=(8, 4.5))
        edges = np.linspace(0, 1, 11)
        g = g.copy()
        g["Bin"] = pd.cut(g.p, edges, include_lowest=True)
        g["Negative"] = g.Y.lt(0)
        for quarter, color in QUARTERS.items():
            part = g[g.Quarter.eq(quarter)].groupby("Bin", observed=True).agg(p=("p", "mean"), y=("Negative", "mean"), n=("Pair", "size"))
            if len(part):
                ax.plot(part.p, part.y, "-", color=color, label=quarter, lw=1.0)
                ax.scatter(part.p, part.y, s=12 + 45 * np.sqrt(part.n / part.n.max()), color=color)
                for row in part.itertuples():
                    if row.n < 30:
                        ax.annotate(f"n={row.n}", (row.p, row.y), xytext=(3, -10 if row.y > 0.9 else 4), textcoords="offset points", fontsize=7, color=color)
        ax.plot([0, 1], [0, 1], "--", color="#555555", lw=1, label="Calibrated")
        ax.set(xlim=(0, 1), ylim=(-0.025, 1.06), xlabel="Forecast probability of negative gross return", ylabel="Observed negative-return fraction", title=f"{model}: probability calibration, {h}-day horizon\n" + LABELS["2026"])
        ax.legend(fontsize=8)
        ax.grid(alpha=0.15)
        figure(data, fig, f"2026-{model}-{h}-reliability", f"{model}: downside probability, {h} days", "Probability reliability uses supported fixed-horizon outcomes. A more frequent win is not necessarily profitable after loss magnitudes and costs. Small bins remain descriptive.", "2026")
    summary = pd.DataFrame(records)
    summary.to_csv(data["artifact"] / "signal-metrics.csv", index=False)
    data["signal_metrics"] = summary
    heading("Signal accuracy and economic levels", "Compare proper probability errors, net-return error and realised levels on the same supported opportunity population. Strong IC alone is insufficient.", "2026")
    table(summary, True)
    heading("Calibrated score versus new downside features", "The C score comparator uses the same allocator as D. This separates forecast information from changes in construction.", "2026")
    h = data["policy_horizon"]
    subset = q[q.H.eq(h)]
    ic = []
    for (model, t), g in subset.groupby(["Model", "Date"]):
        if len(g) >= 3 and g.net.nunique() > 1 and g["Realised net"].nunique() > 1:
            ic.append(dict(Model=model, Date=t, IC=spearmanr(g.net, g["Realised net"]).statistic))
    ics = pd.DataFrame(ic)
    table(ics.groupby("Model").agg(Mean_IC=("IC", "mean"), Origins=("IC", "size")).reset_index(), True)
    # Inspect calibration where the benchmark actually puts capital, not only across the catalog.
    core = data["control_runs"][("2026", "B00")]["allocation_df"]
    ids = set(zip(pd.to_datetime(core.loc[core["Final target (USD)"].gt(0), "Date"]), core.loc[core["Final target (USD)"].gt(0), "Pair id"].astype(int)))
    dates = set(pd.to_datetime(core.Date))
    paired = subset[subset.Date.isin(dates)].copy()
    paired["In_C00"] = [(t, int(i)) in ids for t, i in zip(paired.Date, paired.Pair)]
    rows = []
    for (model, in_core), g in paired.groupby(["Model", "In_C00"]):
        w = 1 / g.groupby("Date").Date.transform("size")
        rows.append(dict(Model=model, Population="C00 selected names" if in_core else "Other feasible names", Rows=len(g), Origins=g.Date.nunique(), Mean_forecast_net=np.average(g.net, weights=w), Mean_realised_net=np.average(g["Realised net"], weights=w), Positive_forecast_fraction=np.average(g.net.gt(0), weights=w)))
    cohort = pd.DataFrame(rows)
    cohort.to_csv(data["artifact"] / "benchmark-cohort-calibration.csv", index=False)
    heading("Forecast calibration at the benchmark selection", f"Compare {h}-day fresh-unit outcomes on C00’s contemporaneous selected names with other eligible names on the same decision dates. This is a marked opportunity diagnostic, not causal account attribution.", "2026")
    table(cohort, True)
    interval_risk_diagnostic(data)
    # Descriptive sign decisions are evaluated on the full feasible opportunity set.
    rows = []
    for model, g in subset.groupby("Model"):
        actual = g["Realised net"]
        reject = g.net.le(0)
        rows.append(dict(Model=model, Rejected_fraction=reject.mean(), Avoided_loss_per_1000=1000 * float(-actual[reject & actual.lt(0)].sum() / len(g)), Missed_profit_per_1000=1000 * float(actual[reject & actual.gt(0)].sum() / len(g)), Rejected_rows=int(reject.sum())))
    heading("Loss avoidance and missed winners", "Per-USD-1,000 opportunity diagnostics use equal fresh tickets, not actual invested dollars. Actual execution activation is shown in the allocation audit.", "2026")
    table(pd.DataFrame(rows), True)


def portfolio_report(data, results, runs, attrs, weights, period):
    f = results[results.Period.eq(period)].copy()
    members = list(f.Arm)
    display(Markdown(f'## {"2026" if period=="2026" else "Full-history"} portfolio comparison\n\n{LABELS[period]}. Fresh USD 150,000 accounts; source accounting and operational restrictions are common.'))
    heading("Key metrics side by side", "Compare net profit, CAGR, Sharpe and drawdown. Green is the better value within a metric; lower cash alone is not success.", period)
    metrics = ["Final equity (USD)", "Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Mean cash weight", "September cash", "Mean vaults held", "Maximum vaults held", "Trades"]
    side = f.set_index("Arm")[metrics].T
    style = side.style.format("{:.2f}", na_rep="—")
    for m in side.index:
        fmt = "${:,.0f}" if "(USD)" in m else "{:.1%}" if m in ["CAGR", "Maximum drawdown", "Mean cash weight", "September cash"] else "{:.2f}"
        style = style.format(fmt, subset=pd.IndexSlice[[m], :])
    for m in ["Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown"]:
        style = style.background_gradient(subset=pd.IndexSlice[[m], :], axis=1, cmap="RdYlGn")
    display(style)
    base = f.set_index("Arm").loc["B00"]
    d = f[f.Arm.ne("B00")].copy()
    d["Profit difference (USD)"] = d["Net profit (USD)"] - base["Net profit (USD)"]
    d["Sharpe difference"] = d.Sharpe - base.Sharpe
    d["DD difference pp"] = (d["Maximum drawdown"] - base["Maximum drawdown"]) * 100
    heading("Incremental outcomes versus C00", "Dollar gains include all account feedback and fees. They are not an independently attributed sleeve return.", period)
    table(d[["Arm", "Method", "Profit difference (USD)", "Sharpe difference", "DD difference pp"]], True)
    fig, ax = plt.subplots(figsize=(11, 5))
    for arm in [a for a in members if a in list(ARMS)[:10]]:
        r = runs[(period, arm)]
        ax.plot(r["equity"].index, r["equity"] / 1000, label=arm, color=PALETTE.get(arm, plt.get_cmap("Dark2")(members.index(arm) % 8)), lw=2.0 if arm in ("B00", "B01", "F01") else 1.35, ls="--" if arm in ("F01", "D02") else "-")
    ax.set(title="Net account equity\n" + LABELS[period], ylabel="Equity (USD thousands)")
    ax.grid(alpha=0.2)
    ax.legend(ncol=5, fontsize=8, loc="upper left")
    figure(data, fig, f"{period}-equity", "Common equity curves", "Every arm starts from cash. All cold-start days are included. Long and short calendars overlap and have already been researched.", period)
    fig, ax = plt.subplots(figsize=(10.5, 4.5))
    for arm in [a for a in members if a in list(ARMS)[:10]]:
        eq = runs[(period, arm)]["equity"].resample("D").last().ffill()
        ax.plot(eq.index, (eq / eq.cummax() - 1) * 100, label=arm, lw=1.5 if arm in ("B00", "B01", "F01") else 1.1, color=PALETTE[arm], ls="--" if arm in ("F01", "D02") else "-")
    ax.set(title="Account drawdown\n" + LABELS[period], ylabel="Drawdown (%)")
    ax.legend(ncol=5, fontsize=8)
    ax.grid(alpha=0.2)
    figure(data, fig, f"{period}-drawdown", "Drawdown paths", "A higher profit may carry worse losses from the account’s own peak. Sparse marks can bunch valuation changes.", period)
    if period == "2026":
        sensitivity = [a for a in members if a not in list(ARMS)[:10]]
        for kind in ("equity", "drawdown"):
            fig, ax = plt.subplots(figsize=(10.5, 4.5))
            for arm in ["B00", "D00"] + sensitivity:
                eq = runs[(period, arm)]["equity"].resample("D").last().ffill()
                value = eq / 1000 if kind == "equity" else (eq / eq.cummax() - 1) * 100
                ax.plot(eq.index, value, label=arm, color=PALETTE[arm], lw=1.6)
            ax.set(title=f"Registered sensitivity {kind}\n" + LABELS[period], ylabel="Equity (USD thousands)" if kind == "equity" else "Drawdown (%)")
            ax.legend(ncol=4, fontsize=8)
            ax.grid(alpha=0.2)
            figure(data, fig, f"{period}-sensitivity-{kind}", f"Registered sensitivity {kind}", "Compare the fixed budget, horizon, margin and gate checks with C00 and the primary downside policy. Colours are consistent with all other portfolio charts.", period)
    q = {}
    for arm in members:
        eq = runs[(period, arm)]["equity"].resample("D").last().ffill()
        p = eq.diff()
        p.iloc[0] = eq.iloc[0] - 150000
        q[arm] = p.groupby(p.index.to_period("Q")).sum()
    quarters = pd.DataFrame(q).T
    from marginal_profit_data import PERIODS

    start, end = map(pd.Timestamp, PERIODS[period])
    quarters.columns = [str(z) + ("*" if start > z.start_time or end - pd.Timedelta(days=1) < z.end_time.floor("D") else "") for z in quarters.columns]
    heatmap(data, quarters, f"{period}-quarters", "Quarterly net account PnL", "Net dollar PnL includes paid and marked fees. An asterisk marks a partial quarter.", period)
    # Same colours for vault identities across every arm, separate images per account.
    reserve = runs[(period, members[0])]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
    names = sorted(set(v for w0 in weights.values() for v in w0.drop(columns=reserve).mean().nlargest(15).index))
    colors = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors) + list(plt.get_cmap("tab20c").colors)
    palette = {v: colors[j % len(colors)] for j, v in enumerate(names)}
    palette.update(Cash="#e5e7eb", Other="#64748b")
    for arm in members:
        w = weights[(period, arm)]
        held = w.drop(columns=reserve)
        top = list(held.mean().nlargest(15 if arm == "H07" else 9).index)
        plot = held[top].copy()
        other = held.drop(columns=top).sum(axis=1)
        if other.max() > 1e-9:
            plot["Other"] = other
        plot["Cash"] = w[reserve]
        fig, ax = plt.subplots(figsize=(10.5, 4.5))
        ax.stackplot(plot.index, *[plot[c].to_numpy() * 100 for c in plot], labels=plot.columns, colors=[palette[c] for c in plot])
        ax.set(ylim=(0, 100), ylabel="Weight / total equity (%)", title=f"{arm}: absolute asset weights\n" + LABELS[period])
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=6))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=7, frameon=False)
        figure(data, fig, f"{period}-{arm}-weights", f"{arm}: absolute asset weights", "Cash is included and exposures are not renormalised to invested capital. The largest average vault exposures are separate (15 for H07, nine otherwise); smaller holdings are grouped as Other.", period)
    fig, axes = plt.subplots(1, 1, figsize=(10.5, 4.5))
    for arm in members:
        w = weights[(period, arm)]
        axes.plot(w.index, w.drop(columns=reserve).gt(1e-8).sum(axis=1), label=arm, lw=1.15, color=PALETTE[arm])
    axes.set(title="Actual vaults held\n" + LABELS[period], ylabel="Vault count")
    axes.axhline(6, color="grey", ls="--", lw=1)
    axes.legend(ncol=5, fontsize=8)
    axes.grid(alpha=0.2)
    figure(data, fig, f"{period}-count", "Actual portfolio breadth", "The source six-slot ceiling is shown as a reference. Caps, forecasts, minimum tickets and the loss budget can still determine effective breadth.", period)
    leaders = f[~f.Arm.isin(["B00", "B01"])].nlargest(3, "Net profit (USD)").Arm.tolist()
    heading("Largest profit contributors", "Vault profit combines multiple positions, including open marked outcomes. Concentration in one vault can make a historical leader fragile.", period)
    pieces = []
    for arm in ["B00", "B01"] + leaders:
        v = attrs[(period, arm)].sort_values(ascending=False)
        pieces.append(pd.DataFrame({"Arm": arm, "Vault": v.head(5).index, "Profit (USD)": v.head(5).values}))
    table(pd.concat(pieces, ignore_index=True), True)


def final_report(data, results, runs, attrs, weights):
    from marginal_profit_allocation import solver_bounds
    from create_marginal_profit_notebook import HEADER

    fees = fee_accounting(data, runs)
    robust, tails = robustness(data, results, runs, attrs)
    downside = worst_update_audit(data, runs)
    heading("Executed allocation and constraint activation", "Only changes to actual dollars can support an allocation finding. Cold-start, projection and drift breaches remain visible.", "2026")
    decisions = pd.DataFrame(data["nb21_decisions"])
    candidates = pd.DataFrame(data["nb21_candidates"])
    checks = pd.DataFrame(data["nb21_checks"])
    d = decisions[decisions.Period.eq("2026")]
    summary = d.groupby("Arm").agg(Decisions=("Date", "size"), Mean_names=("Names", "mean"), Converged_fraction=("Converged", "mean"), Mean_projection_L1_usd=("Projected_executed_L1", "mean"), Soft_breach_fraction=("Soft_breach", "mean"), Mean_calibration_SE=("Calibration_SE", "mean"), Prior_names=("Prior_names", "mean"))
    table(summary.reset_index(), True)
    q = candidates[candidates.Period.eq("2026")]
    activation = q.groupby("Arm").agg(Positive_changes=("Change_gross", lambda z: int(z.gt(1e-6).sum())), Negative_changes=("Change_gross", lambda z: int(z.lt(-1e-6).sum())), Target_change_usd=("Change_gross", lambda z: float(z.abs().sum())), Unknown_score_fraction=("Missing_score", "mean"), Prior_only_fraction=("Forecast_supported", lambda z: 1 - z.mean()), Mean_quote_age=("Quote_age", "mean"))
    table(activation.reset_index(), True)
    heading("Same-state continuous optimisation diagnostic", "Continuous relaxations ignore ticket/count restrictions and bound a sampled concave path-value envelope. Gaps measure possible solver limitations, not profit that was realised.", "2026")
    bounds = solver_bounds(data)
    table(bounds, True)
    heading("Modelled fees and still-open liabilities", "The new policy’s turnover can change the effect of inherited fee assumptions. Fee shadows are diagnostics; changing a strategy conclusion requires both accounts to be rerun under identical changed costs.", "2026")
    table(fees[fees.Period.eq("2026")].drop(columns="Period"), True)
    heading("Largest updates and market context", "Attribute each account’s strongest marked day to genuine NAV intervals, curator exclusions/quarantine, and BTC/ETH changes over those intervals.", "2026")
    table(robust[robust.Period.eq("2026")].drop(columns="Period"), True)
    table(tails[tails.Period.eq("2026")].drop(columns="Period").head(30), True)
    # Fixed-ledger contributor deletion is explicitly descriptive.
    deletion = []
    for (period, arm), r in runs.items():
        curves = pd.read_parquet(data["artifact"] / f"{period}-{arm}-position-curves.parquet")
        meta = pd.read_parquet(data["artifact"] / f"{period}-{arm}-positions.parquet")
        v = attrs[(period, arm)]
        if not len(v):
            continue
        winner = v.idxmax()
        ids = meta.loc[meta.Vault.eq(winner), "Position id"]
        removed = float(curves[ids].iloc[-1].sum())
        deletion.append(dict(Period=period, Arm=arm, Contributor=winner, Removed_profit_usd=removed, Fixed_ledger_profit_without_usd=float(r["equity"].iloc[-1] - 150000 - removed)))
    deletion = pd.DataFrame(deletion)
    deletion.to_csv(data["artifact"] / "fixed-ledger-deletion.csv", index=False)
    heading("Contributor deletion on a fixed ledger", "Subtracting a vault’s recorded PnL does not simulate a replacement allocation or later wealth feedback. It reveals reliance, not a causal strategy result.", "2026")
    table(deletion[deletion.Period.eq("2026")].drop(columns="Period"), True)
    decision_diagnostics(data, runs)
    stress = []
    for (period, arm), w in weights.items():
        reserve = next(c for c in w if c in ("USDC", "USDT", "USD"))
        held = w.drop(columns=reserve)
        stress.append(dict(Period=period, Arm=arm, Largest_50pct_loss=float(held.max(axis=1).max()) * 0.5, Largest_100pct_loss=float(held.max(axis=1).max()), Two_largest_100pct=float(held.apply(lambda z: z.nlargest(2).sum(), axis=1).max())))
    heading("Vault failure stress", "50%/100% loss of the largest holding and simultaneous wipeout of the two largest are mechanical stresses, not calibrated probabilities.", "2026")
    table(pd.DataFrame(stress).query("Period == '2026'").drop(columns="Period"), True)
    # Pairwise profit differences and common-calendar blocked summaries.
    paired = []
    for period in ["2026", "Long"]:
        base = runs[(period, "B00")]["equity"].resample("D").last().ffill()
        for (p, arm), r in runs.items():
            if p != period or arm == "B00":
                continue
            eq = r["equity"].resample("D").last().ffill()
            delta = (eq - base).diff().fillna(eq.iloc[0] - base.iloc[0])
            for block in (7, 30):
                b = delta.groupby(np.arange(len(delta)) // block).sum()
                paired.append(dict(Period=p, Arm=arm, Block_days=block, Blocks=len(b), Positive_block_fraction=float(b.gt(0).mean()), Profit_difference_usd=float(eq.iloc[-1] - base.iloc[-1])))
    paired = pd.DataFrame(paired)
    paired.to_csv(data["artifact"] / "paired-calendar-blocks.csv", index=False)
    heading("Paired profit stability", "The calendars were previously researched. Block counts and sign consistency are descriptive and do not establish an independent significant improvement.", "2026")
    table(paired[paired.Period.eq("2026")].drop(columns="Period"), True)
    primary = results[results.Period.eq("2026") & results.Arm.isin(list(ARMS)[:10])]
    base = primary.set_index("Arm").loc["B00"]
    new = primary[~primary.Arm.isin(["B00", "B01", "F01"])]
    leader = new.sort_values(["Net profit (USD)", "Sharpe"], ascending=False).iloc[0]
    profitgap = leader["Net profit (USD)"] - base["Net profit (USD)"]
    better = bool(profitgap > 0 and leader.Sharpe > base.Sharpe)
    long = results[results.Period.eq("Long")]
    longbase = long.set_index("Arm").loc["B00"]
    longleaders = long[~long.Arm.isin(["B00", "B01", "F01"])].sort_values("Net profit (USD)", ascending=False)
    longlead = longleaders.iloc[0] if len(longleaders) else longbase
    sig = data.get("signal_metrics", pd.DataFrame())
    h = data["policy_horizon"]
    p0 = sig[(sig.Horizon.eq(h)) & sig.Model.eq("P")].iloc[0]
    d0 = sig[(sig.Horizon.eq(h)) & sig.Model.eq("D")].iloc[0]
    verdicts = pd.DataFrame(
        [
            {"Hypothesis": "H1: churn optimisation", "Verdict": "Historical gain" if primary.set_index("Arm").loc["F01", "Net profit (USD)"] > base["Net profit (USD)"] else "Not supported", "Reason": "One fixed wider-band account isolates net execution effects under the inherited fee model."},
            {"Hypothesis": "H2: conditional downside", "Verdict": "Probability gain" if d0.Brier < p0.Brier else "Not supported", "Reason": f"{h}d Brier P/D {p0.Brier:.4f}/{d0.Brier:.4f}; economic value must also beat P00."},
            {"Hypothesis": "H3: conditional magnitudes", "Verdict": "Historical gain" if primary.set_index("Arm").loc["M00", "Net profit (USD)"] > primary.set_index("Arm").loc["D00", "Net profit (USD)"] else "Not supported", "Reason": "M00 versus D00 holds the probability head, risk budget and allocator constant."},
            {"Hypothesis": "H4: new construction beats C00", "Verdict": "Historical lead" if better else "Not confirmed", "Reason": f"Best required new-construction row {leader.Arm}: profit difference USD {profitgap:+,.0f}, Sharpe {leader.Sharpe:.3f} versus {base.Sharpe:.3f}."},
            {"Hypothesis": "H5: incumbent decisions", "Verdict": "Historical gain" if primary.set_index("Arm").loc["D00", "Net profit (USD)"] > primary.set_index("Arm").loc["D03", "Net profit (USD)"] else "Not supported", "Reason": "Compare joint portfolio decisions with entry-only capital deployment."},
            {"Hypothesis": "H6: missing/young participation", "Verdict": "Implemented; utility conditional", "Reason": "Masks, global fit/pooled fallback and actual allocations are reported; undefined metrics are not losses."},
            {"Hypothesis": "H7: robustness", "Verdict": "Exploratory", "Reason": "No independent holdout; budget, horizon and margin extensions plus contributor/fee/solver diagnostics remain conditional."},
        ]
    )
    verdicts.to_csv(data["artifact"] / "hypothesis-verdicts.csv", index=False)
    heading("Hypothesis verdicts", "Separate measured historical effects from general predictive or deployment claims.", "2026")
    display(verdicts.style.hide(axis="index"))
    draw = int(data["control_results"].query("Period == '2026' and Arm == 'B00'")["Trades"].iloc[0])
    insights = f"""The strongest required challenger is **{leader.Arm}**, with {leader.CAGR:.2%} CAGR, {leader.Sharpe:.3f} Sharpe and {leader['Maximum drawdown']:.2%} maximum drawdown, versus C00’s {base.CAGR:.2%}, {base.Sharpe:.3f} and {base['Maximum drawdown']:.2%}. Its net account profit difference is **USD {profitgap:+,.0f}**. This is a researched historical comparison, not independent evidence of future profitability.\n\nConditional downside probability has {h}-day Brier error {d0.Brier:.4f}, versus the support prior’s {p0.Brier:.4f}. The signal ladder and calibrated-score control distinguish feature value from construction. The highest-profit long new-construction challenger is {longlead.Arm}, CAGR {longlead.CAGR:.2%}, Sharpe {longlead.Sharpe:.3f}, compared with C00 {longbase.CAGR:.2%}/{longbase.Sharpe:.3f}.\n\nThe notebook evaluates adaptive breadth, incumbent replacement and cash decisions under complete basis-aware path values. The risk-budget-free arm exposes whether the new budget merely restrains profitable exposure. Main weights are not prescribed by inverse variance. Caps, ticket minima and weak forecasts can still determine the realised basket.\n"""
    cohort = pd.read_csv(data["artifact"] / "benchmark-cohort-calibration.csv").query("Population == 'C00 selected names'").set_index("Model")
    fshort = primary.set_index("Arm").loc["F01"]
    flong = long.set_index("Arm").loc["F01"]
    extensions = results.query("Period == '2026'").set_index("Arm")
    breadth = extensions.loc["H07"]
    insights += f"""\nThe wider sell band F01 adds only **USD {fshort['Net profit (USD)']-base['Net profit (USD)']:,.0f}** in 2026 and **USD {flong['Net profit (USD)']-longbase['Net profit (USD)']:,.0f}** over the long calendar. Its 2026 drawdown is slightly worse; the long gain is not explained solely by lower paid fees. This is a small execution lead, not a substantial improvement.\n\nAt C00’s selected names, the supported {h}-day fresh-unit net outcome averages **{cohort.loc['D','Mean_realised_net']:.2%}**, while D forecasts **{cohort.loc['D','Mean_forecast_net']:.2%}**. Population-wide probability improvements therefore do not imply useful calibration at the profitable investment margin. These overlapping observations are an opportunity diagnostic, not account attribution.\n\nThe H07 sensitivity reaches **{int(breadth['Maximum vaults held'])} vaults**, with **{1-breadth['September cash']:.2%}** average September investment, yet loses **USD {-breadth['Net profit (USD)']:,.0f}**. Removing the risk budget also loses money, and D02 exactly matches D00: six slots were not the binding constraint in that comparison. Retaining incumbents helps D03 relative to D00, but leaves it far behind C00. Better cash use requires better marginal forecasts, not merely more slots or looser risk limits.\n"""
    bad = downside[downside.Arm.eq("M00")].iloc[0]
    longhold = long.set_index("Arm").loc["D03"]
    insights += f"""\nM00’s largest marked loss is concentrated in **{bad.Vault}**, on **{bad.Update}**, with USD {bad['Vault update (USD)']:,.0f} attributed to that vault. The NAV interval, curator status and BTC/ETH context are reported below; a major single-vault loss is not evidence that probability calibration alone controlled tail severity.\n\nThe long D03 retention account reaches {longhold['Largest vault weight']:.2%} in one vault through inherited position drift. Its better retention result does not demonstrate concentration control; failure stresses must consider the actual grown exposure.\n"""
    formatted = primary[["Arm", "CAGR", "Sharpe", "Maximum drawdown", "Net profit (USD)", "September cash", "Maximum vaults held"]].copy()
    for c in ("CAGR", "Maximum drawdown", "September cash"):
        formatted[c] = formatted[c].map(lambda v: f"{v:.2%}")
    formatted["Sharpe"] = formatted.Sharpe.map(lambda v: f"{v:.3f}")
    formatted["Net profit (USD)"] = formatted["Net profit (USD)"].map(lambda v: f"${v:,.0f}")
    body = formatted.to_markdown(index=False)
    full = long[["Arm", "CAGR", "Sharpe", "Maximum drawdown", "Net profit (USD)"]].copy()
    for c in ("CAGR", "Maximum drawdown"):
        full[c] = full[c].map(lambda v: f"{v:.2%}")
    full["Sharpe"] = full.Sharpe.map(lambda v: f"{v:.3f}")
    full["Net profit (USD)"] = full["Net profit (USD)"].map(lambda v: f"${v:,.0f}")
    long_body = "### Full-history comparison — " + LABELS["Long"] + "\n\nThe frozen three-candidate shortlist, both controls and the wider-band diagnostic use fresh accounts and genuine historical model cold starts.\n\n" + full.to_markdown(index=False)
    robustness_text = f"""Independent source controls match NB20 daily equity and every trade; all daily equity paths match to below USD 0.000001. Independent fee/basis and sparse-fill examples passed, and every successful fill was checked against as-of NAV. Engine decision dates and forecast dates are explicitly aligned on both calendars; forecasts are not shifted backwards from a future date. Additional long prediction origins and the last completed feature bucket use the same archive, with the original training and budget samples retained. The base policy horizon is {h} days; the short-holding audit includes dollar-days and censored open positions.\n\nForecasts refit monthly with matured prior labels. Penalties are selected once per horizon/year using preceding purged probability folds; magnitude heads share that penalty, a disclosed computational compromise. Learning endpoints use actual marks; carried engine outcomes are a sensitivity. The margin arm addresses common calibration uncertainty only, not full personalised coefficient uncertainty.\n\nThe allocator is a numerical greedy approximation. Convergence, projection differences and continuous same-state bounds are reported; the frozen denominator and later marked-equity changes can leave inherited cap drift. Gain/loss heads retain the full date measure when conditioning; their mixture passes an exact weighted-mean fixture. The simple loss budget does not provide a guaranteed tail bound or reward diversification by itself.\n\nFees remain the inherited 10% positive-profit charge plus 0.1% capital allowance, rather than verified live fees. Universe and guard history are retrospective. Largest contributors and strongest NAV intervals are checked with curator flags and BTC/ETH context; fixed-ledger contributor deletion and failure stresses are descriptive. No independent significance or deployment claim is made."""
    header = HEADER.split("## Key new insights")[0] + f"## Key new insights\n\n{insights}\n## Summary of results\n\n### Required comparisons — 2026-01-01 → 2026-10-05 exclusive\n\nAll ten registered smoke rows; fees are included in net account outcomes.\n\n{body}\n\n{long_body}\n\n## Robustness of results\n\n{robustness_text}\n"
    finding = f"""# Experiment 21 — marginal profitability and adaptive portfolio allocation\n\n## What was examined\n\n{HEADER.split('**Goal:**')[1].split('## Key')[0]}\n\n## Hypotheses and verdicts\n\n{verdicts.to_markdown(index=False)}\n\n## Results\n\n{insights}\n{body}\n\n{long_body}\n\n## Useful leads\n\nPreserve C00 as the economic benchmark. Investigate calibration on the feasible selection margin and a reliable asymmetric loss model before giving these forecasts control of the portfolio. Distinguish prior-dominated young vaults from well-supported names without discarding missing features. The conditional-magnitude model requires tail and extrapolation diagnostics after its large loss. A wider sell band merits a small execution follow-up; additional numerical optimiser complexity is a lower priority because the sampled same-state solver gaps are negligible. Separate incumbent sell decisions from fresh-entry forecasts: D03’s retention ablation helped, but did not establish an improved strategy. Increasing breadth or removing downside restraint alone did not solve profitability.\n\n## Robustness\n\n{robustness_text}\n"""
    (data["artifact"] / "final-header.md").write_text(header)
    (data["artifact"] / "findings.md").write_text(finding)
    (data["artifact"] / "complete.json").write_text(json.dumps(dict(economic_accounts=len(runs), figures=len(data["figures"]), smoke_accounts=10, full_history_accounts=int(results.Period.eq("Long").sum()), sensitivity_accounts=5), indent=2))
    data["manifest"]["status"] = "complete"
    (data["artifact"] / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return finding


def fresh_control_checks(data, evaluator):
    """Replay all four source controls independently and match every trade."""
    import io
    from contextlib import redirect_stdout, redirect_stderr
    import clean_c00_v11_comparison as baseline

    folder = evaluator.folder
    fresh = data["feature_artifact"] / "fresh-control-engine"
    fresh.mkdir(exist_ok=True)
    rows = []
    for period in ("2026", "Long"):
        for original, arm in [("C00", "B00"), ("V11", "B01")]:
            print(f"Independent control replay {period}/{arm}; approximately 1–3 minutes remaining", flush=True)
            evaluator.folder = fresh
            try:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    r = baseline.v11_replay(data, evaluator, period) if original == "V11" else baseline.core.replay(data, evaluator, "C00", period, active=False)
            finally:
                evaluator.folder = folder
            saved = data["control_runs"][(period, arm)]
            a = r["equity"].resample("D").last().ffill()
            b = saved["equity"].resample("D").last().ffill()
            error = float((a - b).abs().max())
            assert error < 1e-6
            identical = baseline.core.trade_signature(r) == baseline.core.trade_signature(saved)
            assert identical, (period, arm, "fresh trade signature")
            rows.append(dict(Period=period, Arm=arm, Equity_error_usd=error, Trades_match=identical, Trades=len(baseline.core.trade_signature(r))))
    out = pd.DataFrame(rows)
    out.to_csv(data["artifact"] / "fresh-control-parity.csv", index=False)
    heading("Independent source-control replay", "Four separate engine accounts match the archived equity and complete trade signatures. Subsequent reruns may reuse this verified cache.", "2026")
    table(out, True)
    return out


def extra_fee_control(data, evaluator, results, runs, attrs, weights):
    """Check the sole positive smoke control over history without another search."""
    import io
    from contextlib import redirect_stdout, redirect_stderr
    import clean_c00_v11_comparison as baseline
    from marginal_profit_allocation import add

    records = results.to_dict("records")
    old = evaluator.parameters.sell_rebalance_min_threshold_of_initial_cash_pct
    print("Additional full-history fee control F01; approximately 1–3 minutes", flush=True)
    evaluator.parameters["sell_rebalance_min_threshold_of_initial_cash_pct"] = 0.01
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            r = baseline.core.replay(data, evaluator, "F01", "Long", active=False)
    finally:
        evaluator.parameters["sell_rebalance_min_threshold_of_initial_cash_pct"] = old
    add(data, r, "F01", "Long", records, runs, attrs, weights)
    return pd.DataFrame(records), runs, attrs, weights


def decision_diagnostics(data, runs):
    """Actual monetary exit opportunities, numerical similarity and honest capacity shadows."""
    from tradeexecutor.backtest.backtest_pricing import BacktestPricing
    from tradeexecutor.backtest.backtest_routing import BacktestRoutingIgnoredModel
    from tradeexecutor.strategy.tvl_size_risk import USDTVLSizeRiskModel

    q = pd.DataFrame(data["nb21_candidates"])
    q = q[q.Period.eq("2026")].copy()
    h = data["policy_horizon"]
    f = data["predictions"]
    f = f[f.H.eq(h)].copy()
    models = q.Arm.map(lambda a: "P" if a == "P00" else "M" if a == "M00" else "C" if a == "C01" else "D")
    q["Model"] = models
    labels = f[["Date", "Pair", "Model", "Y", "Resolved"]]
    q = q.merge(labels, on=["Date", "Pair", "Model"], how="left", validate="many_to_one")
    # Seven-day policies must use their own targets rather than the primary horizon.
    seven = q.Arm.eq("H07")
    l7 = data["predictions"].query("H == 7 and Model == 'D'").set_index(["Date", "Pair"])
    keys = pd.MultiIndex.from_frame(q.loc[seven, ["Date", "Pair"]])
    q.loc[seven, "Y"] = l7.Y.reindex(keys).to_numpy()
    q.loc[seven, "Resolved"] = l7.Resolved.reindex(keys).fillna(False).to_numpy()
    actual = q.Gross_old > 0
    known = q.Resolved.fillna(False) & q.Y.notna()
    q["Sold_fraction"] = np.where(actual, np.maximum(q.Gross_old - q.Executed_gross, 0) / q.Gross_old.replace(0, np.nan), 0)
    later = 0.999 * q.Gross_old * (1 + q.Y) - 0.1 * np.maximum(q.Gross_old * (1 + q.Y) - q.Basis, 0)
    now = 0.999 * q.Gross_old - 0.1 * np.maximum(q.Gross_old - q.Basis, 0)
    q["Hold_opportunity"] = later - now
    q["Exit_opportunity"] = -q.Sold_fraction * q.Hold_opportunity
    exits = q[actual & known & q.Sold_fraction.gt(1e-8)]
    rows = []
    for arm, g in exits.groupby("Arm"):
        rows.append(dict(Arm=arm, Resolved_exit_rows=len(g), Avoided_loss_usd=float(g.Exit_opportunity.clip(lower=0).sum()), Missed_hold_gain_usd=float((-g.Exit_opportunity.clip(upper=0)).sum()), Net_same_state_exit_opportunity_usd=float(g.Exit_opportunity.sum())))
    heading("Executed exits: avoided loss and missed continuation gains", f"Monetary effects use the actually planned/executed sold fraction and supported {h}-day NAV endpoints, relative to keeping the same shares. These overlapping same-state opportunities do not sum to a causal account PnL; seven-day policies use seven-day labels.", "2026")
    table(pd.DataFrame(rows), True)
    pd.DataFrame(rows).to_csv(data["artifact"] / "exit-opportunities.csv", index=False)
    decisions = pd.DataFrame(data["nb21_decisions"])
    decisions = decisions[decisions.Period.eq("2026")].set_index(["Arm", "Date"])
    reason = []
    for (arm, t), g in q.groupby(["Arm", "Date"]):
        row = decisions.loc[(arm, t)]
        fresh = g[g.Gross_old.le(1e-8) & g.Deposit_open & g.Prior_available]
        positive = fresh.net.gt(0)
        why = "no matured prior" if row.Prior_names == 0 else "no positive fresh net forecast" if len(fresh) and not positive.any() else "no feasible fresh deposits" if not len(fresh) else "calibration margin" if arm == "MARGIN" and row.Calibration_SE > 0 else "estimated downside budget" if np.isfinite(row.B) and row.Risk >= row.B * 0.99 else "capacity, tickets or retained capital"
        reason.append(dict(Arm=arm, Date=t, Reason=why, Fresh_candidates=len(fresh), Positive_fresh=int(positive.sum())))
    reasons = pd.DataFrame(reason)
    reasons.to_csv(data["artifact"] / "cash-opportunity-reasons.csv", index=False)
    heading("September fresh-capital opportunity reasons", "Reasons describe the fresh-deposit margin. Top-ups and retained holdings have different basis economics, so this is not a complete causal decomposition of cash.", "2026")
    sep = reasons[reasons.Date.ge("2026-09-01") & reasons.Date.lt("2026-10-01")]
    table(sep.groupby(["Arm", "Reason"]).size().rename("Decisions").reset_index(), True)
    # Compare pure weighting on the same positive target names, avoiding selection conflation.
    source = data["panel"].query("H == @h").set_index(["Date", "Pair"])
    similar = []
    for (arm, t), g in q.groupby(["Arm", "Date"]):
        selected = g[g.Target_gross.gt(1e-8)].copy()
        keys = pd.MultiIndex.from_frame(selected[["Date", "Pair"]])
        sigma = source.risk_90.reindex(keys).to_numpy(float)
        target = selected.Target_gross.to_numpy(float)
        ok = np.isfinite(sigma) & (sigma > 0)
        if ok.sum() < 3:
            continue
        a = target[ok] / target[ok].sum()
        b = 1 / sigma[ok] ** 2
        b /= b.sum()
        cor = spearmanr(a, b).statistic if np.ptp(a) > 0 and np.ptp(b) > 0 else np.nan
        similar.append(dict(Arm=arm, Date=t, Names=int(ok.sum()), Rank_correlation=cor, Normalised_L1=float(abs(a - b).sum())))
    similarity = pd.DataFrame(similar)
    similarity.to_csv(data["artifact"] / "inverse-variance-similarity.csv", index=False)
    heading("Weight similarity on identical selected vaults", "Compare desired gross proportions with regularised inverse-variance proportions on the same names. Similarity is descriptive; it does not automatically discard an economic result.", "2026")
    table(similarity.groupby("Arm").agg(Dates=("Date", "size"), Mean_rank_correlation=("Rank_correlation", "mean"), Mean_normalised_L1=("Normalised_L1", "mean")).reset_index(), True)
    # Verify pinning from the recorded values rather than accepting diagnostic labels.
    pins = q[q.Pinned]
    assert np.allclose(pins.Gross_old, pins.Target_gross, atol=1e-5)
    assert np.allclose(pins.Gross_old, pins.Executed_gross, atol=1e-5)
    data["pin_verification"] = dict(rows=len(pins), target_and_execution_match=True)
    # Fees varied on the identical recorded action vector; these are forecasts, not account replays.
    fee_rows = []
    for arm, g in q.groupby("Arm"):
        active = g[(g.Target_gross - g.Gross_old).abs().gt(1e-6) & g.Prior_available]
        for pf, cf, name in [(0.1, 0.001, "Base"), (0.0, 0.001, "No profit fee"), (0.1, 0.0, "No capital allowance"), (0.0, 0.0, "Zero modelled charges")]:
            total = 0.0
            notional = 0.0
            for row in active.itertuples():
                from marginal_profit_forecasts import distribution_at

                dist, _ = distribution_at(data, row.Date, int(row.Pair), 7 if arm == "H07" else h, row.Model)
                old = row.Gross_old
                x = row.Target_gross
                b = row.Basis
                basis = b * x / old if old > 0 and x < old else b + max(0, x - old)
                netratio = 1 - cf - pf * max(old - b, 0) / old if old > 0 else 1.0
                flow = (old - x) * netratio if x < old else old - x
                total += dist.terminal(x, basis, performance=pf, capital=cf) + flow - dist.terminal(old, b, performance=pf, capital=cf)
                notional += abs(x - old)
            fee_rows.append(dict(Arm=arm, Cost_model=name, Expected_gain_per_1000_changed=1000 * total / notional if notional else np.nan))
    fees = pd.DataFrame(fee_rows)
    fees.to_csv(data["artifact"] / "same-state-fee-shadows.csv", index=False)
    heading("Fee assumptions and action value", "Expected incremental value per USD 1,000 of changed capital on the same recorded proposals. These are overlapping forecast opportunities and do not establish performance under changed fees.", "2026")
    table(fees.pivot(index="Arm", columns="Cost_model", values="Expected_gain_per_1000_changed"))
    # Keep vault-TVL and protocol headroom fixed while scaling the account.
    universe = runs[("2026", "B00")]["result"].strategy_universe
    pricing = BacktestPricing(universe, BacktestRoutingIgnoredModel(universe.reserve_assets[0].address), data_delay_tolerance=pd.Timedelta(days=2), vault_state=universe.vault_state, liquidity_universe=universe.data_universe.liquidity)
    size = USDTVLSizeRiskModel(pricing_model=pricing, per_position_cap=0.33)
    pool = {}
    elig = data["eligibility"].set_index(["origin_at", "pair_id"])
    rows = []
    for arm, g in q.groupby("Arm"):
        for cap in (0.2, 0.33, 0.5):
            for capital in (75000, 150000, 300000):
                values = []
                for t, z in g[g.Date.ge("2026-09-01") & g.Date.lt("2026-10-01")].groupby("Date"):
                    E = float(decisions.loc[(arm, t), "E"]) * capital / 150000
                    available = 0.0
                    for row in z.itertuples():
                        key = (t, int(row.Pair))
                        if key not in pool:
                            pool[key] = float(size.get_acceptable_size_for_position(t, universe.get_pair_by_id(int(row.Pair)), 1e15).accepted_size)
                        state = elig.loc[key] if key in elig.index else None
                        head = state.max_deposit if state is not None else np.nan
                        head = max(0, float(head)) if row.Deposit_open and pd.notna(head) else np.inf if row.Deposit_open else 0.0
                        available += min(cap * E, pool[key], row.Gross_old * capital / 150000 + head)
                    values.append(min(1.0, available / E))
                rows.append(dict(Arm=arm, Account_cap=cap, Initial_cash=capital, Mean_same_state_capacity=float(np.mean(values)) if values else np.nan))
    shadows = pd.DataFrame(rows)
    shadows.to_csv(data["artifact"] / "capacity-shadows-correct.csv", index=False)
    heading("Capacity at different account sizes", "Vault TVL and archived deposit headroom stay fixed; account equity and owned exposure scale. These ceilings show available capacity, not optimal deployment or realised profit.", "2026")
    table(shadows[shadows.Account_cap.eq(0.33)], True)
    data["decision_diagnostics"] = {"exits": pd.read_csv(data["artifact"] / "exit-opportunities.csv"), "reasons": reasons, "similarity": similarity, "fees": fees}
    return reasons


def interval_risk_diagnostic(data):
    """Matched signal-only sensitivity to gap-adjusted historical risk."""
    from sizing_study_data import sparse_window
    from portfolio_snapshot_risk import peer_prior, forecast
    from marginal_profit_forecasts import fit_snapshot, predict_snapshot, Distribution, date_weights
    from tqdm_loggable.auto import tqdm

    h = data["policy_horizon"]
    panel = data["panel"][data["panel"].H.eq(h)].copy()
    risk = []
    for t, g in tqdm(panel.groupby("Date"), desc="NB21 interval-risk signal diagnostic", mininterval=15):
        a = data["date_index"][t - pd.Timedelta(days=1)]
        pool = g[g.operational_pool]
        values = [sparse_window(data["arrays"]["raw_nav"][max(0, a - 90) : a + 1, data["id_index"][int(i)]], 90) for i in pool.Pair]
        empirical = np.array([v["calendar"] for v in values])
        full = np.array([v["full"] for v in values], bool)
        predicted = {}
        for j, (pid, v) in enumerate(zip(pool.Pair, values)):
            prior, *_ = peer_prior(empirical, full, j)
            value = forecast(v["gap"], prior, v["m"], "regularised", 30)
            predicted[int(pid)] = np.sqrt(value) if np.isfinite(value) and value >= 0 else np.nan
        for idx, pid in zip(g.index, g.Pair):
            risk.append((idx, predicted.get(int(pid), np.nan)))
    panel["risk_90"] = pd.Series(dict(risk))
    rows = []
    for fit in sorted(pd.to_datetime(data["training_audit"].query("H == @h").Fit)):
        if fit < pd.Timestamp("2026-01-01"):
            continue
        base = data["snapshots"].get((h, fit))
        current = panel[panel.Date.dt.to_period("M").eq(fit.to_period("M")) & panel.operational_pool & panel.Resolved]
        if not base or not len(current):
            continue
        train = panel[panel.operational_pool & panel.Resolved & panel.Mature_at.lt(fit)]
        snap = fit_snapshot(train, h, base["alpha"], base["supported"])
        for model in ("P", "D", "M", "C"):
            values = predict_snapshot(snap, current, model)
            ds = [Distribution(*v, snap["positive"], snap["negative"]) for v in values]
            p = np.array([d.p for d in ds])
            net = np.array([d.terminal(1, 1) - 1 for d in ds])
            y = current.Y.to_numpy()
            weights = date_weights(current)
            rows.append(dict(Model=model, Fit=fit, Rows=len(current), Brier=np.average((p - (y < 0)) ** 2, weights=weights), Net_MAE=np.average(abs(net - (0.999 * y - 0.1 * np.maximum(y, 0) - 0.001)), weights=weights), Positive_forecast_fraction=np.average(net > 0, weights=weights)))
    result = pd.DataFrame(rows)
    result.to_csv(data["artifact"] / "interval-risk-signal-diagnostic.csv", index=False)
    heading("Actual-interval risk input sensitivity", f"Refit the {h}-day signal models using gap-adjusted log-return risk with the same penalty and targets. This changes the risk input package, not portfolio weights; it is a signal diagnostic, not an extra account backtest.", "2026")
    table(result.groupby("Model").agg(Months=("Fit", "size"), Brier=("Brier", "mean"), Net_MAE=("Net_MAE", "mean"), Positive_forecast_fraction=("Positive_forecast_fraction", "mean")).reset_index(), True)
    return result


def calendar_alignment(data, evaluator):
    """Audit decision origins and retain only provably unchanged cached accounts."""
    import hashlib
    import os
    from pathlib import Path
    from marginal_profit_data import PERIODS

    required = {period: set(pd.to_datetime(data["control_runs"][(period, "B00")]["allocation_df"].Date.unique())) for period in PERIODS}
    available = set(pd.to_datetime(data["predictions"].Date.unique()))
    for period, dates in required.items():
        assert dates.issubset(available), (period, sorted(dates - available)[:5])
    rows = []
    for period, dates in required.items():
        f = data["predictions"].query("H == 30 and Model == 'P'")
        f = f[f.Date.isin(dates)]
        for year, g in f.groupby(f.Date.dt.year):
            rows.append(dict(Period=period, Year=year, Origins=g.Date.nunique(), Prior_available_fraction=g.Prior_available.mean()))
    audit = pd.DataFrame(rows)
    audit.to_csv(data["artifact"] / "decision-forecast-alignment.csv", index=False)
    heading("Engine and forecast calendar alignment", "Both engine calendars have explicit same-date forecasts. Additional long-period prediction origins retain T−1 features; the original training-origin sample stays fixed. Early genuine model cold starts remain cash.", "2026")
    table(audit, True)
    # Optional reuse requires identical short forecasts, empirical shapes and frozen economic inputs.
    previous = ROOT / "_artifacts-restored-2026-10-07/21/f8f4aa2a79c1e79d0e3038ae001ff96d86e124d80f7c9f9f8852b404f8faf6e6"
    if not previous.exists():
        return
    old = json.loads((previous / "manifest.json").read_text())["identity"]
    assert old["parent"] == data["manifest"]["identity"]["parent"]
    assert old["code"]["marginal_profit_checks.py"] == data["manifest"]["identity"]["code"]["marginal_profit_checks.py"]
    source = (ROOT / "marginal_profit_allocation.py").read_text().replace("origins=sorted(data['panel'].loc[data['panel'].Training_origin,'Date'].unique())", "origins=sorted(data['panel'].Date.unique())")
    assert hashlib.sha256(source.encode()).hexdigest() == old["code"]["marginal_profit_allocation.py"]
    previous_budgets = json.loads((previous / "budget-registration.json").read_text())
    assert all(data["budgets"][period] == previous_budgets[period] for period in PERIODS)
    economics = {n: d for n, d in old["code"].items() if n not in ("marginal_profit_report.py", "create_marginal_profit_notebook.py")}
    oldkey = hashlib.sha256(json.dumps(dict(parent=old["parent"], code=economics, registry=old["registry"]), sort_keys=True).encode()).hexdigest()
    oldengine = previous.parent / "cache" / oldkey / "engine"
    inputkey = hashlib.sha256((old["code"]["marginal_profit_data.py"] + json.dumps(old["parent"], sort_keys=True)).encode()).hexdigest()
    feature = previous.parent / "cache" / inputkey
    forecastkey = hashlib.sha256((old["code"]["marginal_profit_forecasts.py"] + str(feature)).encode()).hexdigest()
    oldforecast = feature / forecastkey
    if not (oldforecast / "forecasts.parquet").exists():
        return

    def short(f):
        return f[f.Date.ge("2026-01-01") & f.Date.lt("2026-10-05")].drop(columns=["Y", "Y_mark", "Resolved", "Mature_at", "Endpoint_age"]).sort_values(["Date", "H", "Model", "Pair"]).reset_index(drop=True)

    try:
        pd.testing.assert_frame_equal(short(pd.read_parquet(oldforecast / "forecasts.parquet")), short(data["predictions"]), check_exact=True)
    except AssertionError:
        (data["artifact"] / "short-cache-compatibility.json").write_text(json.dumps(dict(accounts=0, short_forecasts_exact=False, action="Recalculate every account"), indent=2))
        return
    import joblib

    snapshots = joblib.load(oldforecast / "forecast-snapshots.joblib")
    for key, snapshot in data["snapshots"].items():
        if key[1].year == 2026 and key in snapshots:
            for field in ("positive", "negative"):
                for member in ("z", "w"):
                    assert np.array_equal(getattr(snapshot[field], member), getattr(snapshots[key][field], member))
    prefixes = []
    for path in oldengine.glob("*-diagnostics.json"):
        payload = json.loads(path.read_text())
        dates = payload.get("nb21_decisions", [])
        if dates and all(row["Period"] == "2026" for row in dates):
            prefixes.append(path.name.split("-")[0])
    for prefix in prefixes:
        for path in oldengine.glob(prefix + "*"):
            target = evaluator.folder / path.name
            if not target.exists():
                os.link(path, target)
    (data["artifact"] / "short-cache-compatibility.json").write_text(json.dumps(dict(accounts=len(prefixes), short_forecasts_exact=True, distribution_shapes_exact=True, label_maturity="Unmatured archive-end outcomes are censored; realised labels never enter account decisions", excluded="All long adaptive accounts; long calendars now receive explicit forecasts"), indent=2))


def worst_update_audit(data, runs):
    """Attribute the largest negative marked day to actual NAV intervals."""
    from tradingstrategy.binance.price import fetch_binance_price
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined
    import clean_c00_v11_comparison as baseline

    market = {symbol: fetch_binance_price(symbol=symbol, request_timeout=10.0) for symbol in ("BTCUSDT", "ETHUSDT")}
    identities = data["identities"].set_index("vault_address")
    rows = []
    for (period, arm), r in runs.items():
        if period != "2026":
            continue
        eq = r["equity"].resample("D").last().ffill()
        date = eq.diff().idxmin()
        curves = pd.read_parquet(data["artifact"] / f"{period}-{arm}-position-curves.parquet")
        meta = pd.read_parquet(data["artifact"] / f"{period}-{arm}-positions.parquet").set_index("Position id")
        if curves.empty:
            continue
        changes = curves.diff().loc[date].groupby(meta.Vault).sum()
        vault = changes.idxmin()
        address = meta[meta.Vault.eq(vault)].iloc[0].Address
        pid = int(identities.loc[address, "pair_id"])
        first = baseline.core.engine.observed_quote(data, pid, date - pd.Timedelta(days=1))
        last = baseline.core.engine.observed_quote(data, pid, date)
        row = dict(Arm=arm, Update=str(date.date()), Vault=vault, **{"Account update (USD)": float(eq.diff().loc[date]), "Vault update (USD)": float(changes.loc[vault])}, Excluded=address in EXCLUDED_VAULTS, Quarantined=is_quarantined(address, date))
        if first and last:
            row.update(NAV_return=last[0] / first[0] - 1, Interval_days=(last[1] - first[1]).total_seconds() / 86400)
            for symbol, frame in market.items():
                q = frame.loc[first[1].floor("D") : last[1].floor("D"), "close"]
                row[symbol + " return"] = float(q.iloc[-1] / q.iloc[0] - 1) if len(q) else np.nan
        rows.append(row)
    f = pd.DataFrame(rows)
    f.to_csv(data["artifact"] / "worst-update-audit.csv", index=False)
    heading("Largest negative updates and market context", "The largest negative daily account update is attributed to its biggest losing vault. NAV and BTC/ETH returns use the actual observation interval; marked losses and reporting jumps do not by themselves establish a data error.", "2026")
    table(f, True)
    return f
