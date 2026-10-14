"""Separate, economically labelled notebook evidence for experiment 18."""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
import conditional_cash_allocation as experiment
import conditional_cash_forecasts as forecasts
from allocation_comparison import heading, figure, robustness
from capital_allocation_report import fee_accounting

ROOT = experiment.ROOT
LABELS = experiment.LABELS
ARMS = list(experiment.METHODS)
COLOURS = {a: plt.get_cmap("tab10")(i) for i, a in enumerate(ARMS)}


def table(frame):
    """Colour economics and show small forecast/risk values without rounding away."""
    percent = {"CAGR", "Maximum drawdown", "Mean cash weight", "September cash", "Worst 7-day return", "Worst 30-day return", "Top positive profit share", "Best update", "NAV_return", "BTCUSDT return", "ETHUSDT return", "Pooled_net", "Pooled_lower", "Unresolved_weight", "Lower_net_bound", "First_update_fraction", "raw_z", "z", "lower", "rho", "Mean_retained", "Mean_sleeve_gross", "Mean_fresh", "Maximum_sleeve", "Largest_residual", "Mean_proposal", "Maximum_proposal", "Mean_gradual", "Mean_core_topup", "Mean_50pct_loss", "Maximum_100pct_loss", "Fixed_pre2026_mean", "Adaptive_mean", "Realised_net", "Net", "Lower"}
    formats = {c: "${:,.0f}" if "(USD)" in c or c in ("Requested", "Accepted", "Resolved_dollars", "Forward_net_profit") else "{:.2%}" if c in percent else "{:.5f}" if "risk" in c.lower() or "headroom" in c.lower() else "{:.2f}" for c in frame.select_dtypes("number").columns}
    for c in frame.select_dtypes("integer").columns:
        formats[c] = "{:,.0f}"
    for c in ("Capital_weighted_net", "First_update_weight", "Mean_HLP_weight", "Maximum_HLP_weight", "Mean_predicted", "Mean_realised", "Underestimation_rate", "Worst_static_daily"):
        if c in frame:
            formats[c] = "{:.3%}"
    style = frame.style.format(formats, na_rep="—").hide(axis="index")
    for c in ("CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown", "Net profit (USD)", "Profit difference (USD)"):
        if c in frame:
            style = style.background_gradient(subset=[c], cmap="RdYlGn")
    display(style)


def execution_audit(data, runs):
    """Reconstruct executed share quantities and check gross sleeve exposure."""
    rows = []
    decisions = pd.DataFrame(data["nb18_decisions"])
    decisions.Date = pd.to_datetime(decisions.Date)
    for (period, arm), r in runs.items():
        if not arm.startswith("R"):
            continue
        ledger = r["allocation_df"]
        quantities = {}
        trades = sorted([t for t in r["result"].state.portfolio.get_all_trades() if t.is_success()], key=lambda t: t.executed_at)
        j = 0
        ds = decisions[(decisions.Period == period) & (decisions.Arm == arm)].set_index("Date")
        for t, f in ledger.groupby("Date"):
            t = pd.Timestamp(t)
            while j < len(trades) and pd.Timestamp(trades[j].executed_at) <= t:
                tr = trades[j]
                pid = int(tr.pair.internal_id)
                quantities[pid] = quantities.get(pid, 0) + float(tr.executed_quantity)
                j += 1
            E = float(r["equity"].loc[:t].iloc[-1])
            roles = f.set_index("Pair id").Role.to_dict()
            held = {i: q for i, q in quantities.items() if q > 1e-6}
            rr = forecasts.risk(data, t, list(held))
            core = {}
            extra = {}
            unknown = False
            for i, q in held.items():
                quote = experiment.engine.observed_quote(data, i, t)
                v = q * quote[0] / E if quote else np.nan
                if not np.isfinite(v) or not np.isfinite(rr.loc[i, "sigma"]):
                    unknown = True
                (core if roles.get(i) in ("core", "pinned") else extra)[i] = v
            Lcore = sum(core[i] * rr.loc[i, "sigma"] for i in core)
            Lextra = sum(extra[i] * rr.loc[i, "sigma"] for i in extra)
            d = ds.loc[t]
            J = max(0, float(d.Target_risk) - Lcore) if not unknown and np.isfinite(d.Target_risk) else 0.0
            rows.append(dict(Period=period, Arm=arm, Date=t, Executed_core_risk=Lcore, Executed_sleeve_risk=Lextra, Executed_headroom=J, Executed_sleeve=sum(extra.values()), Largest_sleeve=max(extra.values(), default=0), Sleeve_positions=len(extra), Total_positions=len(held), Risk_breach=bool(Lextra > J + 1e-7), Exposure_breach=bool(sum(extra.values()) > 0.25 + 1e-6 or max(extra.values(), default=0) > 0.05 + 1e-6), Unknown=unknown, Fee_bound_valid=bool(E + 1e-6 >= d.Equity)))
    out = pd.DataFrame(rows)
    out.to_parquet(data["artifact"] / "executed-risk-audit.parquet", index=False)
    assert out.Fee_bound_valid.all(), "Post-trade equity must stay above the source-fee-derived risk denominator"
    assert not out.Risk_breach.any() and not out.Exposure_breach.any(), "Hard sleeve limits need executable handling"
    assert out.Total_positions.le(12).all() and out.Sleeve_positions.le(6).all()
    return out


def logic():
    descriptions = {"C00": ("Exact C-W source selector", "None", "Source"), "C01": ("Admission-aware protected core", "None", "Source"), "C02": ("Same core plus four overflow slots", "Score-ordered unconditional remainder", "NB17 overflow"), "R00": ("Same C01 core; twelve total/six sleeve ceiling", "Risk-only capped inverse volatility", "Mandatory/source/funding/risk"), "R01": ("Same as R00", "Same risk-only entry", "R00 plus scenario economic exit"), "R02": ("Same as R01", "Pooled 80% lower net estimate > 0", "Common economic exit"), "R03": ("Same as R01", "Current score-group central net > 0", "Common economic exit"), "R04": ("Same as R03", "Same relative mix; alpha scales fresh buys", "Common economic exit; retained first"), "R05": ("Same as R04", "k=1 instead of .75; same alpha", "Common economic exit; retained first")}
    return pd.DataFrame([dict(Arm=a, Method=experiment.METHODS[a], Core=d[0], Admission_and_sizing=d[1], Exits=d[2]) for a, d in descriptions.items()])


def frontier(data, f, x, y, name, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(9.5, 5))
    groups = {}
    for row in f.itertuples(index=False):
        d = row._asdict()
    for _, r in f.iterrows():
        groups.setdefault((round(float(r[x]), 9), round(float(r[y]), 9)), []).append(r.Arm)
    for j, ((xx, yy), members) in enumerate(groups.items()):
        mx = 100 if x in ("CAGR", "September cash", "Maximum drawdown") else 1
        my = 100 if y == "CAGR" else 0.001 if y == "Net profit (USD)" else 1
        ax.scatter(xx * mx, yy * my, s=85, color=COLOURS[members[0]], marker="s" if members[0].startswith("C") else "o")
        offset = -18 if members[0] == "R00" or members[0] == "R01" and x == "Maximum drawdown" else 12 if members[0] == "R01" else 10 if j % 2 else -17
        ax.annotate("/".join(members), (xx * mx, yy * my), xytext=(9, offset), textcoords="offset points", fontsize=9, arrowprops={"arrowstyle": "-", "lw": 0.6, "color": "grey"})
    ax.margins(0.18)
    ax.grid(alpha=0.2)
    ax.set(xlabel=xlabel, ylabel=ylabel, title=name + "\n" + LABELS["2026"])
    figure(data, fig, "2026-" + name.lower().replace(" ", "-"), name, "Each point is an independent corrected-fee account. Squares are controls; circles are risk-budgeted treatments (.75 except R05 at 1.00). Coincident points share a label; tables retain all methods. Lower cash alone cannot establish a better strategy.", "2026")


def equity(data, runs, period, members):
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    groups = []
    for a in members:
        s = runs[(period, a)]["equity"]
        match = next((v for v in groups if s.equals(v[1])), None)
        if match is None:
            groups.append(([a], s))
        else:
            match[0].append(a)
    for aliases, s in groups:
        ax.plot(s.index, s / 1000, label="/".join(aliases) + " — " + experiment.METHODS[aliases[0]], color=COLOURS[aliases[0]], lw=1.5)
    ax.set(ylabel="Equity ($ thousands)", title="Corrected-fee equity curves\n" + LABELS[period])
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    figure(data, fig, period + "-equity", "Equity curves", "Independent fresh-capital accounts. The displayed shortlist includes all controls and distinct treatment profit/Sharpe leaders; full-history capital is never reset at year boundaries.", period)


def weights_chart(data, weights, period, a, palette):
    w = weights[(period, a)]
    reserve = next(c for c in w if c in ("USDC", "USDT", "USD"))
    v = w.drop(columns=reserve)
    names = list(v.mean().nlargest(9).index)
    plot = v[names].copy()
    other = v.drop(columns=names).sum(axis=1)
    if other.max() > 1e-8:
        plot["Other vaults"] = other
    plot["Cash"] = w[reserve]
    palette = palette | {"Cash": "#d1d5db", "Other vaults": "#9ca3af"}
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.stackplot(plot.index, *[plot[c].to_numpy() * 100 for c in plot], labels=plot.columns, colors=[palette[c] for c in plot])
    ax.set(ylim=(0, 100), ylabel="Share of total equity (%)", title=a + ": absolute asset weights\n" + LABELS[period])
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    figure(data, fig, period + "-" + a + "-weights", a + ": absolute asset weights", "Absolute weights include grey cash; largest nine average vault exposures are separate. Consistent vault colours across accounts. Marked equity includes the source open redemption liabilities; this is not a percentage of invested capital.", period)


def quarters(data, runs, period):
    vals = {}
    for a in ARMS:
        e = runs[(period, a)]["equity"].resample("D").last().ffill()
        p = e.diff()
        p.iloc[0] = e.iloc[0] - 150000
        vals[a] = p.groupby(p.index.to_period("Q" if period == "2026" else "Y")).sum()
    absolute = pd.DataFrame(vals).T
    difference = absolute.sub(absolute.loc["C01"], axis=1)
    difference.to_csv(data["artifact"] / f"{period}-incremental-profit.csv")
    labels = [str(c) + ("*" if c == difference.columns[-1] or period == "Long" and c == difference.columns[0] else "") for c in difference]
    fig, ax = plt.subplots(figsize=(max(9, len(labels) * 1.1), 4.5))
    z = difference.to_numpy() / 1000
    limit = max(1, np.max(np.abs(z)))
    im = ax.imshow(z, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    ax.set_yticks(range(len(ARMS)), ARMS)
    ax.set_title("Incremental net profit versus C01 ($ thousands)\n" + LABELS[period])
    for i in range(len(ARMS)):
        for j in range(len(labels)):
            ax.text(j, i, f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=9, color="white" if abs(z[i, j]) > limit * 0.65 else "black")
    fig.colorbar(im, ax=ax, label="Incremental profit ($ thousands)", shrink=0.8)
    figure(data, fig, period + "-incremental-profit", "Quarterly incremental profit" if period == "2026" else "Annual incremental profit", "Account-dollar contribution differences against the matched C01 core. Asterisk denotes partial calendar coverage; differences include capital compounding and holdings carried from earlier periods.", period)
    return absolute


def period_report(data, results, runs, attribution, weights, fees, robust, tails, period, members, palette):
    f = results[results.Period.eq(period)].copy()
    base = f.set_index("Arm").loc["C01"]
    f["Profit difference (USD)"] = f["Net profit (USD)"] - base["Net profit (USD)"]
    heading("Key economic metrics", "All nine corrected-fee methods side by side. Green favours greater profit/CAGR/Sharpe and less negative drawdown. C01 is the matched core; C00 is exact historical C-W.", period)
    metrics = ["Final equity (USD)", "Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Calmar"]
    wide = f.set_index("Arm").loc[ARMS, metrics].T
    style = wide.style.format("{:.2f}")
    for metric in metrics:
        style = style.format("${:,.0f}" if "USD" in metric else "{:.2%}" if metric in ("CAGR", "Maximum drawdown") else "{:.2f}", subset=pd.IndexSlice[[metric], :])
        style = style.background_gradient(subset=pd.IndexSlice[[metric], :], axis=1, cmap="RdYlGn")
    display(style)
    heading("Cash, breadth and trading", "Cash is a mechanism measure. Effective breadth accounts for uneven vault weights. Worst-window returns use the marked daily equity series; sparse prices can bunch changes into later updates.", period)
    table(f[["Arm", "Profit difference (USD)", "Mean cash weight", "September cash", "Maximum vaults held", "Mean effective breadth", "Trades", "Gross trade turnover (USD)", "Worst 7-day return", "Worst 30-day return"]])
    equity(data, runs, period, members)
    quarters(data, runs, period)
    for a in members:
        weights_chart(data, weights, period, a, palette)
    heading("Fees paid and open exit liabilities", "Actual sell deductions are reconciled against known gross NAV. Open performance/capital exit liabilities are shown separately; estimated liquidation equity is a fee convention, not a guarantee of immediate redemption.", period)
    table(fees[fees.Period.eq(period)][["Arm", "Paid sell deductions (USD)", "Open performance liability (USD)", "Open capital allowance (USD)", "Gross NAV equity (USD)", "Estimated liquidation equity (USD)", "Reported marked equity (USD)"]])
    heading("Contributor concentration and extremes", "Largest positive vault contribution divided by all positive contributions. A strong update can be a delayed sparse NAV observation rather than broad contemporaneous performance.", period)
    table(robust[robust.Period.eq(period)].drop(columns="Period"))
    heading("Observation intervals and BTC/ETH context", "Largest contributing vault behind each shortlisted account’s strongest update, with curator/quarantine and BTC/ETH moves over the actual observed-NAV interval. This context does not establish executable prices in gaps.", period)
    t = tails[tails.Period.eq(period) & tails.Arm.isin(members)].groupby("Arm").head(1)
    table(t[["Arm", "Update", "Vault", "Update profit (USD)", "NAV_return", "Interval_days", "BTCUSDT return", "ETHUSDT return", "Excluded", "Quarantined"]])
    heading("Leading vault profit contributions", "Top three contributors per shortlisted account. These reconcile to account PnL but role promotions prevent an exact causal split between core and sleeve.", period)
    rows = []
    for a in members:
        for v, p in attribution[(period, a)].nlargest(3).items():
            rows.append(dict(Arm=a, Vault=v, **{"Profit (USD)": p}))
    table(pd.DataFrame(rows))
    return f


def forecast_report(data):
    c = data["calibration"]
    f = c[c.H.eq(30) & c.Fit_date.between("2026-01-01", "2026-10-01")]
    latest = f[f.Fit_date.eq(f.Fit_date.max())].set_index("Group").reindex(forecasts.GROUPS)
    fig, ax = plt.subplots(figsize=(9.5, 4.7))
    x = np.arange(len(latest))
    ax.scatter(x, latest.z * 100, label="Shrunk central net forecast", color="#2563eb", s=60)
    ax.scatter(x, latest.raw_z * 100, label="Unshrunk group mean", color="#d97706", marker="x", s=50)
    ax.vlines(x, latest.lower * 100, latest.z * 100, color="#2563eb", lw=2)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xticks(x, latest.index)
    ax.set(ylabel="Expected 30-day net return (%)", title="Score-band calibration: fit frozen 1 October 2026\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    ax.set_xticks(x, [str(g) + "\n" + str(int(latest.loc[g, "origins"])) + " origins" + ("\npooled fallback" if latest.loc[g, "rho"] == 0 else "") for g in latest.index])
    figure(data, fig, "2026-calibration", "Score-band future net returns", "Date-weighted resolved marginal-candidate outcomes. Blue stems connect the central mean to the one-sided 80% lower estimate; they are not individual-return prediction intervals. Labels mark groups without enough support, whose blue estimate is the pooled fallback; their orange raw estimate is not used for trading. Missing scores retain their own support rules.", "2026")
    heading("Actually used monthly profitable regions", "Primary 30-day calibration only. A pooled lower-bound switch affects the entire sleeve; group-positive regions need not form a monotonic threshold. No future October outcomes enter the 1 October fit.", "2026")
    records = []
    for t, g in f.groupby("Fit_date"):
        r = g.iloc[0]
        records.append(dict(Fit_date=str(t.date()), Supported=bool(r.Supported), Origins=r.Pooled_origins, Vaults=r.Pooled_vaults, Blocks=r.Pooled_blocks, Pooled_net=r.Pooled_net, Pooled_lower=r.Pooled_lower, Positive_groups=", ".join(g.loc[g.z.gt(0), "Group"])))
    table(pd.DataFrame(records))
    heading("Calibration support by score group", "Latest actually used monthly fit. Missing is an explicit bucket; zero is in the first finite bucket. rho is the frozen group confidence share; rho=0 means pooled fallback.", "2026")
    table(latest.reset_index()[["Group", "origins", "vaults", "blocks", "rho", "raw_z", "z", "lower"]])
    panel = data["calibration_panel"]
    p = panel[panel.H.eq(30) & panel.Marginal & panel.Date.between("2026-01-01", "2026-10-04")].copy()
    heading("Unresolved marginal outcomes and sparse endpoints", "Unresolved observations are never converted to zero returns. Bounds put unresolved gross/net return at complete loss for the lower bound and allow unbounded upside; these are partial-identification bounds, not forecasts. Resolved fits may have survivorship bias.", "2026")
    rows = []
    for g, v in p.groupby("Group"):
        dateweights = 1 / v.groupby("Date").Date.transform("size") / v.Date.nunique()
        unresolved = float(dateweights[~v.Resolved].sum())
        known = float((dateweights[v.Resolved] * v.loc[v.Resolved, "Z"]).sum())
        rows.append(dict(Group=g, Rows=len(v), Resolved=int(v.Resolved.sum()), Unresolved_weight=unresolved, Lower_net_bound=known - unresolved, Upper_net_bound="unbounded" if unresolved else str(known), Median_endpoint_age=float(v.loc[v.Resolved, "Endpoint_age"].median()), First_update_fraction=float(v.loc[v.Resolved, "First_update"].mean())))
    table(pd.DataFrame(rows))
    # Actual marginal proposals: account R03, decision origins that match panel.
    ledger = pd.read_csv(data["artifact"] / "2026-R03-target-ledger.csv", parse_dates=["Date"])
    ledger = ledger[~ledger.Role.eq("core")].copy()
    merged = ledger.merge(p[["Date", "Pair", "Z", "Resolved"]], left_on=["Date", "Pair id"], right_on=["Date", "Pair"], how="inner")
    merged = merged[merged.Resolved & merged["Score available"]]
    fig, ax = plt.subplots(figsize=(9.5, 5))
    colours = ["#2563eb", "#16a34a", "#d97706", "#9333ea"]
    for j, (quarter, g) in enumerate(merged.groupby(merged.Date.dt.to_period("Q"))):
        admitted = g["Fresh increment (USD)"].gt(0)
        if (~admitted).any():
            ax.scatter(g.loc[~admitted, "Ranking score"], g.loc[~admitted, "Z"] * 100, s=18, color=colours[j % 4], alpha=0.35, label=str(quarter) + " no fresh admission")
        if admitted.any():
            ax.scatter(g.loc[admitted, "Ranking score"], g.loc[admitted, "Z"] * 100, s=40, marker="^", color=colours[j % 4], edgecolor="black", linewidth=0.4, label=str(quarter) + " fresh admitted")
    if len(merged) > 2 and merged["Ranking score"].std() > 0:
        coefficient = np.polyfit(merged["Ranking score"], merged.Z * 100, 1)
        xx = np.linspace(merged["Ranking score"].min(), merged["Ranking score"].max(), 100)
        ax.plot(xx, np.polyval(coefficient, xx), color="#111827", lw=1.4, ls="--", label="Descriptive linear trend")
    ax.axhline(0, color="grey", lw=0.7)
    ax.set(xlabel="Four-input score", ylabel="Observed subsequent 30-day net return (%)", title="Actual R03 marginal opportunities\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7, ncol=2)
    figure(data, fig, "2026-opportunity-scatter", "Marginal opportunity scatter", "Current R03 non-core candidates matched to resolved four-day-origin labels, coloured by quarter. Triangles received fresh deposits; dots did not. Unresolved and missing-score observations are disclosed separately, never plotted as zero. This is realised conditional performance, not an untouched forecast test.", "2026")
    fig, ax = plt.subplots(figsize=(9.5, 5))
    for j, (quarter, g) in enumerate(merged.groupby(merged.Date.dt.to_period("Q"))):
        ax.scatter(g["Ranking score"], g.Z * 100, s=18, color=colours[j % 4], alpha=0.35, label=str(quarter))
    ax.set_yscale("symlog", linthresh=5)
    ax.set_yticks([-100, -10, -5, 0, 5, 10, 100], ["−100", "−10", "−5", "0", "5", "10", "100"])
    ax.axhline(0, color="grey", lw=0.8)
    ax.set(xlabel="Four-input score", ylabel="30-day net return (%; symmetric log scale)", title="Marginal opportunities: centre and tails\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    figure(data, fig, "2026-opportunity-detail", "Marginal opportunities: centre and tails", "A separate symmetric-log view of the same resolved observations. The central ±5 percentage points are linear; tails are compressed, preserving every observation rather than clipping extreme losses or gains. Missing-score buckets remain in the support tables.", "2026")
    heading("Horizon and block diagnostics", "7/90-day horizons are diagnostics, not alternative selected trading targets. Ninety-day bootstrap blocks and leave-one-vault-out range describe calibration sensitivity using the final 2026 monthly fit.", "2026")
    table(pd.read_csv(data["artifact"] / "calibration-sensitivities.csv"))
    fixed = data["fixed_forecast"]
    records = []
    for t, g in p[p.Resolved].groupby(p.loc[p.Resolved, "Date"].dt.to_period("Q")):
        prediction = g.Group.map({name: v["z"] for name, v in fixed["groups"].items()})
        adaptive = []
        for row in g.itertuples():
            adaptive.append(forecasts.forecast_at(data, row.Date)["groups"].get(row.Group, {}).get("z", np.nan))
        records.append(dict(Quarter=str(t), Resolved_rows=len(g), Fixed_pre2026_mean=float(prediction.groupby(g.Date).mean().mean()), Adaptive_mean=float(pd.Series(adaptive, index=g.index).groupby(g.Date).mean().mean()), Realised_net=float(g.groupby("Date").Z.mean().mean())))
    heading("Fixed pre-2026 calibration diagnostic", "Freeze the 1 January fit and compare its predictions with adaptively updated monthly fits on resolved 2026 marginal candidates. These are forecast diagnostics; no additional account is claimed.", "2026")
    table(pd.DataFrame(records))


def mechanisms(data, runs, audit):
    d = pd.DataFrame(data["nb18_decisions"])
    d.Date = pd.to_datetime(d.Date)
    f = d[d.Period.eq("2026")]
    heading("Activation and sizing activity", "Count actual treatment decisions. Anchor support and forecast support differ; risk-only entry remains usable without a return forecast. Alpha limits new capital and does not force retained positions to match a one-step optimum.", "2026")
    rows = []
    for a, g in f.groupby("Arm"):
        rows.append(dict(Arm=a, Decisions=len(g), Anchor_active=int(g.Anchor.notna().sum()), Forecast_active=int(g.Forecast_supported.sum()), Fresh_buy_decisions=int(g.Fresh.gt(0).sum()), Interior_alpha=int(g.Alpha.between(1e-8, 1 - 1e-8).sum()), Alpha_zero=int(g.Alpha.lt(1e-8).sum()), Economic_exits=int(g.Economic_exits.sum()), Hard_exits=int(g.Hard_exits.sum()), Mean_retained=g.Retained.mean(), Mean_sleeve_gross=g.Sleeve_gross.mean(), Mean_fresh=g.Fresh.mean()))
    table(pd.DataFrame(rows))
    for name, col, label in [("risk-budget", "Sleeve_risk", "Additional daily volatility measure"), ("deployment", "Sleeve_gross", "Gross residual sleeve / equity (%)"), ("alpha", "Alpha", "Fresh-deployment scaling alpha")]:
        fig, ax = plt.subplots(figsize=(10.5, 4.5))
        selected = f[f.Arm.isin(["R04", "R05"])] if name == "alpha" else f
        lines = []
        for a, g in selected.groupby("Arm"):
            series = g.set_index("Date")[col] * (100 if name == "deployment" else 1)
            match = next((v for v in lines if series.equals(v[1])), None)
            if match is None:
                lines.append(([a], series))
            else:
                match[0].append(a)
        for aliases, series in lines:
            ax.plot(series.index, series, label="/".join(aliases), color=COLOURS[aliases[0]], lw=1.3)
        if name == "alpha":
            ax.set_ylim(-0.03, 1.03)
            ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
            if selected.Alpha.eq(0).all():
                ax.text(0.5, 0.55, "No fresh sizing activation: alpha = 0 on every decision", ha="center", transform=ax.transAxes, color="#475569")
        if name == "risk-budget":
            anchor = f[f.Arm.eq("R00")]
            ax.plot(anchor.Date, anchor.Headroom, label="R00 available headroom", color="black", ls="--", lw=1)
        ax.set(ylabel=label, title=name.replace("-", " ").capitalize() + "\n" + LABELS["2026"])
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8, ncol=4)
        figure(data, fig, "2026-" + name, name.replace("-", " ").capitalize(), "Decision-time conservative proposal values. Retained holdings consume the sleeve budget before fresh buys; R05 alone uses the full lagged reference allowance. The source core is never trimmed merely to fit this additional-risk ceiling.", "2026")
    heading("Executed gross exposure and risk checks", "Reconstruct actual executed share quantities, price them at the latest as-of NAV, and compare sleeve exposure with current core risk and the shared lagged allowance. Counts distinguish proposal success from an executed guarantee; unknown inherited exposures block new buys.", "2026")
    table(audit[audit.Period.eq("2026")].groupby("Arm").agg(Decisions=("Date", "size"), Risk_breaches=("Risk_breach", "sum"), Exposure_breaches=("Exposure_breach", "sum"), Unknown=("Unknown", "sum"), Maximum_sleeve=("Executed_sleeve", "max"), Largest_residual=("Largest_sleeve", "max"), Maximum_total_positions=("Total_positions", "max")).reset_index())
    heading("Protected core and execution checks", "Proposal journals check that sleeve allocation preserves core dollar targets, accounts for retained holdings once, and obeys capacity and slot limits. Independent executed checks above use actual shares and the engine equity denominator, including the separate generic valuation model’s deductions.", "2026")
    checks = pd.DataFrame(data["nb18_checks"])
    short_checks = checks[checks.Period.eq("2026")]
    table(short_checks.groupby("Arm").agg(Decisions=("Date", "size"), Core_preserved=("Core_preserved", "all"), Risk_valid=("Risk_valid", "all"), Capacity_valid=("Capacity_valid", "all"), Retained_counted_once=("Retained_counted_once", "all"), Slot_valid=("Slot_valid", "all")).reset_index())
    heading("Cash and spending constraints", "Overlapping mean decision snapshots, not an additive cash waterfall. The 2% source reserve is retained; core capacity, sleeve exposure/risk limits, admission gates and trade floors can all leave additional cash. Pending proceeds are excluded by the inherited engine funding rules, never assumed spendable.", "2026")
    table(f.groupby("Arm").agg(**{"Mean protected core targets (USD)": ("Core_target", "mean"), "Mean executable residual (USD)": ("Residual", "mean"), "Mean conservative marking bound (USD)": ("Fee_marking_bound", "mean")}, No_risk_headroom=("Headroom", lambda x: int(x.le(0).sum())), Unknown_core_decisions=("Unknown_core", "sum"), Maximum_sleeve_slots=("Slots", "max")).reset_index())
    shadows = data["shadows"]
    heading("Fresh-proposal shadows across risk/gate methods", "Mean proposal weights over all full-2026 C01 states. No retained feedback, trade execution or performance claim. Gross-exposure safety conversion and source minimum tickets are authoritative only in engine treatments; shadows describe continuous mechanisms.", "2026")
    primary = shadows[shadows.Slots.eq("6") & shadows.Sleeve_cap.eq(0.25) & shadows.Single_cap.eq(0.05)]
    table(primary.groupby(["k", "Gate"]).agg(Decisions=("Date", "size"), Positive_proposals=("Proposed", lambda x: int((x > 0).sum())), Mean_proposal=("Proposed", "mean"), Mean_alpha=("Alpha", "mean"), Mean_gradual=("Gradual", "mean"), Mean_core_topup=("Core_topup", "mean"), Mean_risk_headroom=("Risk_headroom", "mean")).reset_index())
    heading("Slot, exposure-limit and mechanical stress shadows", "Same-state proposals with no feedback. Slots mean additional slots, so four/six/unlimited correspond to ten/twelve/no total ceiling when all six core slots are used. The loss stresses are arithmetic, without invented probabilities.", "2026")
    table(shadows[shadows.k.eq(0.75) & shadows.Gate.eq("none")].groupby(["Slots", "Sleeve_cap", "Single_cap"], dropna=False).agg(Mean_proposal=("Proposed", "mean"), Maximum_proposal=("Proposed", "max"), Mean_core_topup=("Core_topup", "mean"), Mean_50pct_loss=("Stress50", "mean"), Maximum_100pct_loss=("Stress100", "max")).reset_index())
    heading("Admission reasons and candidate support", "Overlapping repeated decision snapshots, not cumulative distinct rejected dollars or an additive cash waterfall. A vault-specific permission failure does not prohibit other vaults. Missing/prior-only targets are shown separately below.", "2026")
    rows = []
    support = []
    for a in ARMS[3:]:
        q = pd.read_csv(data["artifact"] / f"2026-{a}-target-ledger.csv")
        v = q[~q.Role.isin(["core", "pinned"])]
        nd = q.Date.nunique()
        for reason, g in v.groupby("Reason"):
            rows.append(dict(Arm=a, Reason=reason, Candidate_snapshots=len(g), **{"Mean feasible capacity snapshots (USD)": g["Capacity ceiling (USD)"].sum() / nd}))
        allocated = q[q.Role.eq("overflow") & q["Final target (USD)"].gt(0)]
        support.append(dict(Arm=a, **{"Mean missing target (USD)": allocated.loc[~allocated["Score available"], "Final target (USD)"].sum() / nd, "Mean prior-only target (USD)": allocated.loc[allocated["Prior only"], "Final target (USD)"].sum() / nd, "Mean <30-update target (USD)": allocated.loc[allocated["Actual updates"] < 30, "Final target (USD)"].sum() / nd}, Median_mark_age=allocated["Risk age"].median()))
    table(pd.DataFrame(rows))
    heading("Sparse and missing sleeve support", "Dollar targets averaged across all treatment decisions; carried NAV does not count as an independent update. Missing scores and prior-only risk are different conditions.", "2026")
    table(pd.DataFrame(support))
    # Match the gated dollar budget against ungated and deterministic random
    # candidate mixes on the same R03 dates, with identical risk/cap limits.
    random_rows = []
    q = pd.read_csv(data["artifact"] / "2026-R03-target-ledger.csv", parse_dates=["Date"])
    for t, g in q.groupby("Date"):
        r = f[(f.Arm == "R03") & f.Date.eq(t)].iloc[0]
        budget = float(r.Fresh) * float(r.Equity)
        if budget <= 0:
            continue
        cand = g[~g.Role.isin(["core", "pinned"]) & g.Sigma.gt(0) & g["Capacity ceiling (USD)"].gt(0)].copy()
        ids = list(cand["Pair id"].astype(int))
        sig = cand.set_index("Pair id").Sigma.to_dict()
        caps = (cand.set_index("Pair id")["Capacity ceiling (USD)"].clip(upper=0.05 * r.Equity)).to_dict()
        if not ids:
            continue
        ordered = cand.sort_values(["Ranking score", "Address"], ascending=[False, True])["Pair id"].astype(int).tolist()
        rng = np.random.default_rng(int(t.value // 86400000000000) + 18)
        random = rng.permutation(ids).tolist()
        for name, chosen in [("ungated", ordered), ("random", random)]:
            chosen = chosen[:6]
            x = forecasts.capped_inverse_volatility(chosen, caps, sig, budget, max(0, float(r.Headroom - r.Retained_risk)) * float(r.Equity))
            resolved = 0.0
            profit = 0.0
            for i, v in x.items():
                y = forecasts.label(data, i, t, 30)
                if y["Resolved"]:
                    resolved += v
                    profit += v * y["Z"]
            random_rows.append(dict(Date=t, Diagnostic=name, Requested=budget, Accepted=sum(x.values()), Resolved_dollars=resolved, Forward_net_profit=profit))
    m = pd.DataFrame(random_rows)
    m.to_csv(data["artifact"] / "matched-admission-shadows.csv", index=False)
    heading("Matched-budget admission shadows", "R03’s actual fresh dollar budget is offered to ungated source-order and deterministic random candidates using the same continuous risk/cap envelope. These are one-decision shadows, not independent portfolios; underdeployment/support mismatches are displayed instead of claiming exact exposure matching.", "2026")
    if len(m):
        table(m.groupby("Diagnostic").agg(Decisions=("Date", "size"), Requested=("Requested", "sum"), Accepted=("Accepted", "sum"), Resolved_dollars=("Resolved_dollars", "sum"), Forward_net_profit=("Forward_net_profit", "sum")).reset_index())
    else:
        display(Markdown("No R03 fresh proposals: admission cannot establish predictive value."))
    heading("Pooled-switch exposure-matching feasibility", "R02 uses a portfolio-wide switch, so the meaningful comparator is an ungated proposal with the same fresh dollar budget. A zero accepted budget makes both shadows zero and cannot test ranking skill.", "2026")
    r02 = f[f.Arm.eq("R02")]
    if not r02.Fresh.gt(0).any():
        display(Markdown("R02 made no fresh sleeve proposals in 2026. Its exposure-matched ungated shadow is therefore also zero; no predictive-value claim follows."))
    else:
        display(Markdown("R02 has positive fresh budgets; interpret its matched R01 economic contrast as an exposure-changing policy comparison, not a test of cross-sectional ranking."))
    return d


def turnover(data, runs):
    rows = []
    for (p, a), r in runs.items():
        state = r["result"].state
        by = {}
        dur = []
        roundtrips = 0
        for pos in state.portfolio.get_all_positions():
            if pos.closed_at:
                dur.append((pd.Timestamp(pos.closed_at) - pd.Timestamp(pos.opened_at)).total_seconds() / 86400)
                by.setdefault(str(pos.pair.pool_address), []).append((pd.Timestamp(pos.opened_at), pd.Timestamp(pos.closed_at)))
        for address, parts in by.items():
            starts = [pd.Timestamp(pos.opened_at) for pos in state.portfolio.get_all_positions() if str(pos.pair.pool_address) == address]
            for opened, closed in parts:
                roundtrips += int(any(closed < s <= closed + pd.Timedelta(days=4) for s in starts))
        rows.append(dict(Period=p, Arm=a, Closed_positions=len(dur), Median_closed_duration=float(np.median(dur)) if dur else np.nan, Under7_days=sum(x < 7 for x in dur), Repurchases_within4_days=roundtrips))
    out = pd.DataFrame(rows)
    out.to_csv(data["artifact"] / "holding-duration.csv", index=False)
    return out


def supplementary(data, results, runs, attribution, weights):
    """Capital-weighted outcomes, support sensitivity and independent reconciliations."""
    cash = []
    outcomes = []
    deleted = []
    hlp = []
    risk_rows = []
    for (period, a), r in runs.items():
        trades = [t for t in r["result"].state.portfolio.get_all_trades() if t.is_success()]
        expected = 150000 + sum((-1 if t.is_buy() else 1) * abs(float(t.executed_reserve or 0)) for t in trades)
        error = expected - float(r["result"].state.portfolio.get_cash())
        assert abs(error) < 0.05, (period, a, error)
        cash.append(dict(Period=period, Arm=a, **{"Cash reconciliation error (USD)": error, "Position PnL residual (USD)": results.set_index(["Period", "Arm"]).loc[(period, a), "PnL residual (USD)"]}))
        pnl = attribution[(period, a)]
        name = pnl.idxmax()
        profit = float(pnl.max())
        deleted.append(dict(Period=period, Arm=a, Largest_vault=name, **{"Largest contribution (USD)": profit, "Profit after fixed-ledger deletion (USD)": float(results.set_index(["Period", "Arm"]).loc[(period, a), "Net profit (USD)"]) - profit}))
        w = weights[(period, a)]
        names = [name for name in w if "hlp" in name.lower() or "hyperliquidity" in name.lower()]
        v = w[names].sum(axis=1) if names else pd.Series(0.0, index=w.index)
        hlp.append(dict(Period=period, Arm=a, Vaults=", ".join(names) or "none", Mean_HLP_weight=float(v.mean()), Maximum_HLP_weight=float(v.max())))
        if not a.startswith("R"):
            continue
        ledger = r["allocation_df"].copy()
        ledger.Date = pd.to_datetime(ledger.Date)
        lookup = ledger.set_index(["Date", "Pair id"])
        for tr in trades:
            t = pd.Timestamp(tr.executed_at)
            pid = int(tr.pair.internal_id)
            key = (t, pid)
            if not tr.is_buy() or key not in lookup.index or lookup.loc[key, "Role"] != "overflow":
                continue
            row = lookup.loc[key]
            lab = forecasts.label(data, pid, t, 30)
            amount = abs(float(tr.executed_reserve or 0))
            outcomes.append(dict(Period=period, Arm=a, Date=t, Pair=pid, Group=row["Score group"], Dollar_amount=amount, **lab))
    cash = pd.DataFrame(cash)
    cash.to_csv(data["artifact"] / "cash-reconciliation.csv", index=False)
    heading("Cash and profit reconciliation", "Independent cash-flow check: initial reserve plus successful net sells minus successful buys equals final cash. Position-profit curves reconcile to final account profit.", "2026")
    table(cash[cash.Period.eq("2026")].drop(columns="Period"))
    out = pd.DataFrame(outcomes)
    out.to_parquet(data["artifact"] / "fresh-capital-outcomes.parquet", index=False)
    heading("Future outcomes weighted by actual extra capital", "Actual executed fresh sleeve buys, rather than target or equal-vault weights. Horizons overlap and dollars can be redeployed, so these are fixed-horizon diagnostic outcomes, not a sleeve PnL decomposition. Unresolved capital is disclosed.", "2026")
    rows = []
    for a, g in out[out.Period.eq("2026")].groupby("Arm"):
        good = g.Resolved
        resolved = g.loc[good, "Dollar_amount"].sum()
        total = g.Dollar_amount.sum()
        profit = (g.loc[good, "Dollar_amount"] * g.loc[good, "Z"]).sum()
        rows.append(dict(Arm=a, Buys=len(g), **{"Gross fresh buys (USD)": total, "Resolved buys (USD)": resolved, "Diagnostic horizon profit (USD)": profit}, Capital_weighted_net=profit / resolved if resolved else np.nan, Unresolved_weight=1 - resolved / total if total else np.nan, First_update_weight=g.loc[good & g.First_update, "Dollar_amount"].sum() / resolved if resolved else np.nan))
    table(pd.DataFrame(rows))
    panel = data["calibration_panel"]
    p = panel[panel.H.eq(30) & panel.Marginal & panel.Date.between("2026-01-01", "2026-10-04") & panel.Resolved]
    heading("Dense endpoints and first-update sensitivity", "Resolved 2026 marginal outcomes, date-weighted. Dense sensitivity requires endpoint mark age at most two days; this is a diagnostic, not a new admission veto. Sparse filtering can change the vault population, so differences are descriptive.", "2026")
    rows = []
    for name, v in [("All resolved", p), ("Endpoint age ≤2 days", p[p.Endpoint_age.le(2)]), ("Exclude first-update labels", p[~p.First_update])]:
        rows.append(dict(Population=name, Rows=len(v), Vaults=v.Pair.nunique(), Origins=v.Date.nunique(), Net=float(v.groupby("Date").Z.mean().mean())))
    table(pd.DataFrame(rows))
    heading("Largest-vault fixed-ledger deletion", "Subtract the largest contributor from each account’s fixed historical PnL. This does not reallocate its capital or rerun selection, and is not an executable exclusion strategy.", "2026")
    deleted = pd.DataFrame(deleted)
    deleted.to_csv(data["artifact"] / "largest-vault-deletion.csv", index=False)
    table(deleted[deleted.Period.eq("2026")].drop(columns="Period"))
    heading("HLP exposure is ordinary risky vault exposure", "HLP and Hyperliquidity holdings, if present, are counted as vault risk. They are never classified as cash or a guaranteed-yield instrument.", "2026")
    hlp = pd.DataFrame(hlp)
    hlp.to_csv(data["artifact"] / "hlp-exposure.csv", index=False)
    table(hlp[hlp.Period.eq("2026")].drop(columns="Period"))
    # Static holdings risk: compare each one-decision sleeve proposal with its
    # resolved forward daily return path; no claim of realised dynamic risk.
    d = pd.DataFrame(data["nb18_decisions"])
    d.Date = pd.to_datetime(d.Date)
    for a in ARMS[3:]:
        ledger = runs[("2026", a)]["allocation_df"]
        ledger = ledger[ledger.Role.eq("overflow") & ledger["Final target (USD)"].gt(0)]
        for t, g in ledger.groupby("Date"):
            t = pd.Timestamp(t)
            row = d[(d.Period == "2026") & (d.Arm == a) & d.Date.eq(t)].iloc[0]
            returns = []
            weight = 0.0
            supported = True
            for record in g.to_dict("records"):
                pid = int(record["Pair id"])
                lab = forecasts.label(data, pid, t, 30)
                if not lab["Resolved"]:
                    supported = False
                    break
                marks = [experiment.engine.observed_quote(data, pid, t + pd.Timedelta(days=k))[0] for k in range(31)]
                ret = np.array(marks[1:]) / np.array(marks[:-1]) - 1
                w = float(record["Final target (USD)"]) / float(row.Equity)
                returns.append(w * ret)
                weight += w
            if supported and returns:
                r = np.sum(returns, axis=0)
                risk_rows.append(dict(Arm=a, Date=t, Predicted=float(row.Sleeve_risk), Realised_static_daily_sigma=float(np.std(r, ddof=1)), Worst_static_daily=float(r.min()), Sleeve_target_weight=weight))
    rr = pd.DataFrame(risk_rows)
    rr.to_csv(data["artifact"] / "static-sleeve-risk-outcomes.csv", index=False)
    heading("Forecast versus subsequent static-sleeve volatility", "Freeze each decision’s proposed sleeve weights for 30 days and use resolved as-of NAV returns. Perfect-correlation predicted risk is compared with observed static daily volatility, not the changing portfolio. Unknown terminal outcomes remain excluded and disclosed above.", "2026")
    if len(rr):
        table(rr.groupby("Arm").agg(Resolved_decisions=("Date", "size"), Mean_predicted=("Predicted", "mean"), Mean_realised=("Realised_static_daily_sigma", "mean"), Underestimation_rate=("Predicted", lambda x: float((rr.loc[x.index, "Realised_static_daily_sigma"] > x).mean())), Worst_static_daily=("Worst_static_daily", "min")).reset_index())
    else:
        display(Markdown("No resolved positive sleeve snapshots."))


def findings(data, results, runs, attribution, audit, decisions, robust):
    short = results[results.Period.eq("2026")].set_index("Arm")
    long = results[results.Period.eq("Long")].set_index("Arm")
    lines = []
    durations = pd.read_csv(data["artifact"] / "holding-duration.csv").set_index(["Period", "Arm"])
    core_duration = float(durations.loc[("2026", "C01"), "Median_closed_duration"])
    for period, f in [("2026", short), ("Long", long)]:
        leader = f["Net profit (USD)"].idxmax()
        r = f.loc[leader]
        b = f.loc["C01"]
        lines.append(f'- **{LABELS[period]}:** {leader} leads with **{r.CAGR:.2%} CAGR**, **{r.Sharpe:.2f} Sharpe**, **{r["Maximum drawdown"]:.2%} drawdown**, and **\\${r["Net profit (USD)"]:,.0f} profit**; **\\${r["Net profit (USD)"]-b["Net profit (USD)"]:+,.0f}** versus C01. September cash is {r["September cash"]:.1%}.')
    comparisons = []
    for a, b in [("C01", "C00"), ("R00", "C02"), ("R01", "R00"), ("R02", "R01"), ("R03", "R01"), ("R04", "R03"), ("R05", "R04")]:
        comparisons.append(dict(Method=a, Control=b, **{"2026 profit difference (USD)": short.loc[a, "Net profit (USD)"] - short.loc[b, "Net profit (USD)"], "Long profit difference (USD)": long.loc[a, "Net profit (USD)"] - long.loc[b, "Net profit (USD)"]}))
    contrast = pd.DataFrame(comparisons)
    contrast.to_csv(data["artifact"] / "paired-contrasts.csv", index=False)
    successes = [a for a in ARMS[3:] if all(f.loc[a, "Net profit (USD)"] > f.loc["C01", "Net profit (USD)"] and f.loc[a, "Sharpe"] >= f.loc["C01", "Sharpe"] and f.loc[a, "Maximum drawdown"] >= f.loc["C01", "Maximum drawdown"] for f in (short, long))]
    active = decisions[decisions.Period.eq("2026")]
    interior = int(active[active.Arm.isin(["R04", "R05"])].Alpha.between(1e-8, 1 - 1e-8).sum())
    breaches = int(audit.Risk_breach.sum() + audit.Exposure_breach.sum())
    top = robust.sort_values("Top positive profit share", ascending=False).iloc[0]
    verdicts = []
    for h, a, b, claim in [("H1", "R00", "C02", "Risk-limited package beats unconditional overflow"), ("H2", "R03", "R01", "Score admission improves the same risk sleeve"), ("H3", "R04", "R03", "Gradual sizing improves binary admission"), ("H4", "R00", "C01", "Additional positions complement the core")]:
        differences = [f.loc[a, "Net profit (USD)"] - f.loc[b, "Net profit (USD)"] for f in (short, long)]
        verdict = "supported on both researched periods" if min(differences) > 0 else "rejected on both researched periods" if max(differences) < 0 else "mixed / not established"
        if max(abs(x) for x in differences) < 0.01:
            verdict = "not identified: economically inactive or identical"
        if h == "H2" and not active[active.Arm.eq("R03")].Fresh.gt(0).any():
            verdict += "; 2026 benefit, if any, is avoiding exposure, not identifying profitable admissions"
        verdicts.append(f"| {h}: {claim} | {verdict} | {a}−{b}: 2026 \\${differences[0]:+,.0f}; full history \\${differences[1]:+,.0f}. |")
    verdicts.append(f'| H5: robustness to support/cost/concentration | qualified, not independently confirmed | Corrected-fee controls reproduce; {breaches} executed risk/exposure breach flags. Highest positive-vault concentration is {top["Top positive profit share"]:.1%} ({top.Arm}, {top.Period}). Retrospective universe and unresolved labels remain limitations. |')
    text = (
        """## Key new insights

"""
        + ("\n".join(lines))
        + f"""

- A method wins only through net economics, not cash usage. {'Candidates improving profit, Sharpe and drawdown against C01 in both periods: '+', '.join(successes)+'.' if successes else 'No conditional method improves profit, Sharpe and drawdown against C01 on both periods.'}
- The gradual treatments produced {interior} genuinely interior alpha decisions in fresh 2026. Zero/full scaling and minimum tickets can make a continuous formula economically discrete; inspect the activation table before crediting forecast precision.
- Score calibration is conditional on resolved marginal outcomes. Missing scores remain eligible through their own supported group or pooled fallback, and unknown terminal outcomes are not flat zero returns.
- The gross-exposure safety conversion reserves current modelled accrued exit charges, because source targets use marked-equity dollars. Core risk includes suppressed small trims and pinned gross holdings; new cash cannot borrow artificial risk headroom from net marks.
- Adding the economic exit changes profit by **\\${short.loc['R01','Net profit (USD)']-short.loc['R00','Net profit (USD)']:+,.0f}** in 2026 and **\\${long.loc['R01','Net profit (USD)']-long.loc['R00','Net profit (USD)']:+,.0f}** over full history. The admission-aware C01 core itself differs from exact C-W by **\\${short.loc['C01','Net profit (USD)']-short.loc['C00','Net profit (USD)']:+,.0f}** in 2026, before any new sleeve is added.
- A profitable score threshold is **not established** if its gate admits no new dollars. Keeping cash can outperform an unprofitable sleeve without demonstrating which extra vaults to buy.
- The matched core's median closed-position lifetime is **{core_duration:g} days** in 2026, versus the registered **30-day** forecast horizon. These lifetimes include core positions and are not an exact sleeve holding-period estimate, but the mismatch is a concrete lead for a small horizon-alignment study rather than more score bands.

## Summary of results

All eighteen registered accounts use corrected partial-trim fees and the same pinned inputs. Fresh 2026 is the default; the full-history account starts in 2023, shares a causal full-history C01 risk reference, and carries early profits into 2026. Controls retain six/ten slots; all new methods permit at most twelve total and six residual names. Forecast-free R00 is the primary check on the value of estimation.

### Hypothesis verdicts

Profit differences use matched controls; risk-budgeted R00 versus C02 is a package contrast, not an isolated risk coefficient test.

| Hypothesis | Verdict | Evidence |
|:--|:--|:--|
"""
        + ("\n".join(verdicts))
        + """

## Robustness of results

- The two periods overlap and were researched earlier. Neither monthly causal fitting nor full-history replay makes them untouched validation.
- Daily NAV is carried only after inception; actual update counts determine confidence. Recorded as-of NAV does not prove executable NAV, and publication availability remains unverified.
- Thirty-day labels require a terminal supporting observation, with its availability included in maturity. Resolved training can still favour surviving vaults; unresolved lower bounds assume complete loss and upper sensitivity is unbounded.
- The shared risk anchor is a lagged median of a hypothetical 98%-invested reference mix; it may be infeasible under dollar capacity and adapts to persistent volatility. The perfect-correlation measure is conditional on imperfect marginal estimates, not a maximum-loss guarantee. Core exposure is not reduced to enforce an overall account risk tolerance.
- Economic exit forecasts apply fees to every scenario using remaining cost basis. The fixed-horizon hold-versus-cash model omits reinvestment/optimal stopping. Paid charges and still-open liabilities are shown separately.
- Corrected partial trims reproduce the registered controls, but generic post-trade valuation uses the protocol pricing route rather than the source’s instance-level wrapper. Cached pair exit-tax rates can persist on a closed vault and affect the mark when it is reopened, while the fresh source wrapper uses its fallback rate for that pair. The sleeve mirrors the generic route’s actual quote and verifies a conservative post-trade denominator; gross NAV, estimated single-fee liquidation and engine marks are displayed separately. This is not a claim that all inherited valuation conventions are economically correct.
- Fresh-proposal, matched random/ungated and cap/slot diagnostics lack sleeve feedback. They do not establish independent strategy performance or an optimal number of positions.

## Smallest useful next step

Keep the simpler control unless a treatment improves the economic trade-off in a genuinely later period. Calibrate a small, frozen marginal-opportunity population that actually survives risk limits and minimum tickets, then inspect forecast support and accepted dollars before another engine search. The current calibration includes all feasible non-core deposits, not only the next executable slot; its negative pooled forecast need not mean every possible extra vault is unprofitable. Explicitly choose tolerable loss/exposure limits before changing production. Six positions remains a baseline; this experiment does not prove its optimality.
"""
    )
    (ROOT / "18-conditional-cash-allocation-findings.md").write_text("# Experiment 18 findings\n\n" + text)
    original = json.loads((ROOT / "18-backtest-conditional-cash-allocation.ipynb").read_text())["cells"][0]["source"]
    original = "".join(original) if isinstance(original, list) else original
    header = original.split("Results will be inserted after execution.")[0].split("## Key new insights")[0] + text
    (data["artifact"] / "final-header.md").write_text(header)
    summary = ROOT / "summary.md"
    existing = summary.read_text()
    marker = "## Experiment 18 — conditional cash allocation"
    section = "\n\n" + marker + "\n\n" + text.replace("## ", "### ")
    if marker in existing:
        existing = existing[: existing.index(marker)].rstrip()
    summary.write_text(existing + section + "\n")
    return text, contrast


def report(data, results, runs, attribution, weights):
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 10})
    data["figures"] = []
    assert len(results) == 18
    robust, tails = robustness(data, results, runs, attribution)
    fees = fee_accounting(data, runs)
    audit = execution_audit(data, runs)
    durations = turnover(data, runs)
    leaders = {results[(results.Period == p) & results.Arm.str.startswith("R")].sort_values(metric, ascending=False).iloc[0].Arm for p in experiment.PERIODS for metric in ("Net profit (USD)", "Sharpe")}
    members = ["C00", "C01", "C02", "R00", "R01"] + sorted(leaders - {"R00", "R01"})
    names = sorted(set(c for w in weights.values() for c in w.columns if c not in ("USDC", "USDT", "USD")))
    colours = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors) + list(plt.get_cmap("tab20c").colors)
    palette = {n: colours[i % len(colours)] for i, n in enumerate(names)}
    display(Markdown("## Fresh 2026 comparison\n\nComplete 2026 history with prior warmup. Every displayed account uses corrected partial-redemption fees."))
    heading("Strategy logic", "Core, admission/sizing and exit rules separate the matched mechanisms; original core regularised inverse variance is fixed. All new sleeves use capped inverse volatility, a fixed peer pool and source ordering.", "2026")
    table(logic())
    heading("Fixed and researched parameters", "The numerical registry is predeclared in the reviewed plan. These are research assumptions, not inferred live risk tolerance.", "2026")
    display(pd.DataFrame([{"Parameter": k, "Value": str(v)} for k, v in experiment.REGISTRY.items()]).style.hide(axis="index"))
    f = period_report(data, results, runs, attribution, weights, fees, robust, tails, "2026", members, palette)
    frontier(data, f, "CAGR", "Sharpe", "CAGR versus Sharpe", "CAGR (%)", "Sharpe")
    frontier(data, f, "September cash", "Net profit (USD)", "Profit versus September cash", "Mean September cash (%)", "Net profit ($ thousands)")
    frontier(data, f, "Maximum drawdown", "Net profit (USD)", "Profit versus drawdown", "Maximum drawdown (%)", "Net profit ($ thousands)")
    for name in ("cash", "positions"):
        fig, ax = plt.subplots(figsize=(10.5, 4.7))
        lines = []
        for a in members:
            w = weights[("2026", a)]
            reserve = next(c for c in w if c in ("USDC", "USDT", "USD"))
            v = w[reserve] * 100 if name == "cash" else w.drop(columns=reserve).gt(1e-9).sum(axis=1)
            match = next((line for line in lines if v.equals(line[1])), None)
            if match is None:
                lines.append(([a], v))
            else:
                match[0].append(a)
        for aliases, v in lines:
            ax.plot(v.index, v, label="/".join(aliases), color=COLOURS[aliases[0]], lw=1.4)
        ax.set(ylabel="Cash / equity (%)" if name == "cash" else "Vaults with positive exposure", title="Daily " + name + "\n" + LABELS["2026"])
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8, ncol=4)
        figure(data, fig, "2026-daily-" + name, "Daily " + name, "Controls and distinct treatment leaders. Cash contains the 2% source reserve and constraints on spending; higher position counts are permitted when marginal risk/capacity allow, not forced to hit a target.", "2026")
    forecasts_report = forecast_report(data)
    decisions = mechanisms(data, runs, audit)
    supplementary(data, results, runs, attribution, weights)
    heading("Holding durations and rapid repurchases", "Closed position lifetimes, with full closes followed by repurchase within four days. These are position-level diagnostics and include core trades; the registered 30-day forecast need not match the actual exit time.", "2026")
    table(durations[durations.Period.eq("2026")].drop(columns="Period"))
    heading("Control parity and mathematical checks", "Saved corrected C-W/M05 metrics match the prior notebook. Separate fixtures cover payoff, sparse maturity, unavailable risk and interior alpha. Gross NAV fill checks and position-profit reconciliation cover all accounts.", "2026")
    table(pd.read_csv(data["artifact"] / "control-parity.csv").query('Period == "2026"').drop(columns="Period"))
    heading("Numerical mechanism fixtures", "Every listed check passed before engine treatments. These checks are separate from executed risk diagnostics.", "2026")
    display(pd.read_csv(data["artifact"] / "algebra-checks.csv").style.hide(axis="index"))
    heading("Legacy fee figures are historical context", "Saved NB17 primary figures used the older partial-trim fee convention. They are shown here beside the corrected controls to explain changed headline results; they are not additional NB18 accounts or interchangeable performance estimates.", "2026")
    legacy = pd.read_csv(data["nb17_reference"] / "results.csv")
    fee_rows = []
    for a, old in [("C00", "M00"), ("C02", "M05")]:
        previous = legacy[(legacy.Period == "2026") & (legacy.Arm == old)].iloc[0]
        current = results[(results.Period == "2026") & (results.Arm == a)].iloc[0]
        fee_rows.extend([dict(Arm=a, Convention="Saved legacy partial fees", CAGR=previous.CAGR, Sharpe=previous.Sharpe, **{"Net profit (USD)": previous["Net profit (USD)"]}), dict(Arm=a, Convention="NB18 corrected partial fees", CAGR=current.CAGR, Sharpe=current.Sharpe, **{"Net profit (USD)": current["Net profit (USD)"]})])
    table(pd.DataFrame(fee_rows))
    display(Markdown("## Full-history comparison\n\nFresh capital on 1 March 2023, all earlier available history retained, no annual reset; final archive day partial. This period overlaps the 2026 comparison."))
    period_report(data, results, runs, attribution, weights, fees, robust, tails, "Long", members, palette)
    heading("Full-history activation calendar", "Early unsupported dates run only the protected core. Reference risk support and forecast support are separate; risk-only R00 does not require a return forecast.", "Long")
    rows = []
    for a, g in decisions[decisions.Period.eq("Long")].groupby("Arm"):
        dates = g[g.Anchor.notna()].Date
        fit = g[g.Forecast_supported].Date
        fresh = g[g.Fresh.gt(0)].Date
        rows.append(dict(Arm=a, First_anchor=str(dates.min()), First_forecast=str(fit.min()), First_sleeve_buy=str(fresh.min()), Decisions=len(g), Anchor_inactive=int(g.Anchor.isna().sum()), Forecast_inactive=int((~g.Forecast_supported).sum())))
    table(pd.DataFrame(rows))
    text, contrasts = findings(data, results, runs, attribution, audit, decisions, robust)
    heading("Fresh 2026 matched contrasts", "Registered treatment differences isolate economic exit, pooled/group admission, gradual sizing and risk allowance. The full-history differences are discussed separately in the findings.", "2026")
    table(contrasts.drop(columns="Long profit difference (USD)"))
    display(Markdown(text))
    (data["artifact"] / "figure-manifest.json").write_text(json.dumps(data["figures"], indent=2))
    (data["artifact"] / "complete.json").write_text(json.dumps(dict(status="complete", accounts=18, nav_fill_checks=len(pd.read_csv(data["artifact"] / "fill-audit.csv")), figures=len(data["figures"]), executed_risk_breaches=int(audit.Risk_breach.sum()), executed_exposure_breaches=int(audit.Exposure_breach.sum())), indent=2))
    return text
