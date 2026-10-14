"""Economic and mechanism evidence for NB19, with separate labelled figures."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
import protected_core_score_allocation as experiment
import conditional_cash_report as charts
from allocation_comparison import heading, figure, robustness
from capital_allocation_report import fee_accounting
from conditional_cash_forecasts import label

ROOT = experiment.ROOT
LABELS = experiment.LABELS


def table(f):
    formats = {c: "${:,.0f}" if c.endswith("(USD)") or c.endswith("_USD") else "{:.2%}" if c in ("CAGR", "Maximum drawdown", "September cash", "Mean cash weight", "Best update", "Top positive profit share", "Worst 7-day return", "Worst 30-day return", "Historical_CAGR", "Common_CAGR", "NAV_return", "BTCUSDT return", "ETHUSDT return", "Mean_equity_fraction", "Worst_50pct_loss", "Worst_100pct_loss") else "{:.6f}" if "dollar-day" in c else "{:.3f}" for c in f.select_dtypes("number")}
    for c in f.select_dtypes("integer"):
        formats[c] = "{:,.0f}"
    for c in f.select_dtypes("number"):
        if c in ("Mean_regular_risk", "Mean_gap_risk", "Maximum_prior_tax"):
            formats[c] = "{:.4%}"
    s = f.style.format(formats, na_rep="—").hide(axis="index")
    for c in ("CAGR", "Sharpe", "Maximum drawdown", "Net profit (USD)", "Incremental profit (USD)"):
        if c in f:
            s = s.background_gradient(subset=c, cmap="RdYlGn")
    display(s)


def heatmap(data, f, name, title, description, period, unit="USD thousands"):
    z = f.to_numpy(float)
    limit = max(0.01, np.nanmax(abs(z)))
    fig, ax = plt.subplots(figsize=(max(9, len(f.columns) * 0.75), max(4, len(f) * 0.36)))
    im = ax.imshow(z, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(len(f.columns)), f.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(f)), f.index)
    ax.grid(False)
    ax.set_title(title + "\n" + LABELS[period])
    if len(f.columns) <= 16:
        for i in range(len(f)):
            for j in range(len(f.columns)):
                ax.text(j, i, "—" if not np.isfinite(z[i, j]) else f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=8, color="white" if abs(z[i, j]) > 0.7 * limit else "black")
    fig.colorbar(im, ax=ax, label=unit, shrink=0.8)
    figure(data, fig, period + "-" + name, title, description, period)


def scatter(data, f, x, y, title, name, period):
    fig, ax = plt.subplots(figsize=(10, 5.3))
    xm = 100 if x in ("CAGR", "Maximum drawdown", "September cash") else 1
    ym = 100 if y in ("CAGR", "Maximum drawdown") else 0.001 if y == "Net profit (USD)" else 1
    groups = {}
    for _, r in f.iterrows():
        groups.setdefault((round(r[x] * xm, 7), round(r[y] * ym, 7)), []).append(r.Arm)
    colours = [plt.get_cmap("tab20")(i) for i in [0, 2, 4, 6, 8, 10, 12, 16, 18, 1, 3]]
    colour_by_arm = dict(zip(experiment.METHODS, colours))
    for j, ((xx, yy), members) in enumerate(sorted(groups.items(), key=lambda item: item[0][1], reverse=True)):
        ax.scatter(xx, yy, s=75, marker="s" if "C00" in members else "o", color=colour_by_arm[members[0]], label="/".join(members))
    ax.legend(title="Independent account", loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9, frameon=False)
    ax.margins(0.2)
    ax.grid(alpha=0.2)
    ax.set(xlabel=x + (" (%)" if xm == 100 else ""), ylabel=y + (" (%)" if ym == 100 else " ($ thousands)" if ym == 0.001 else ""), title=title + "\n" + LABELS[period])
    figure(data, fig, period + "-" + name, title, "Each point is an independent account; coincident points share labels. Profit, risk and cash are outcomes, not independent experiments. C00 uses the common entry-marking correction.", period)


def execution(data, runs):
    """Rebuild quantities and roles at each executed decision."""
    rows = []
    role_rows = []
    recalls = []
    ds = pd.DataFrame(data["nb19_decisions"])
    ds.Date = pd.to_datetime(ds.Date)
    for (period, arm), r in runs.items():
        if arm == "C00":
            continue
        ledger = r["allocation_df"]
        trades = sorted([t for t in r["result"].state.portfolio.get_all_trades() if t.is_success()], key=lambda t: t.executed_at)
        q = {}
        j = 0
        previous_roles = {}
        context = ds[ds.Period.eq(period) & ds.Arm.eq(arm)].set_index("Date")
        for t, f in ledger.groupby("Date"):
            t = pd.Timestamp(t)
            roles = f.set_index("Pair id").Role.to_dict()
            now = []
            while j < len(trades) and pd.Timestamp(trades[j].executed_at) <= t:
                tr = trades[j]
                i = int(tr.pair.internal_id)
                q[i] = q.get(i, 0) + float(tr.executed_quantity)
                now.append(tr)
                j += 1
            d = context.loc[t]
            E = float(r["equity"].loc[:t].iloc[-1])
            extra = {i: v * experiment.engine.observed_quote(data, i, t)[0] for i, v in q.items() if v > 1e-6 and roles.get(i) == "additional"}
            held = {i: v for i, v in q.items() if v > 1e-6}
            cap = 0.02 if arm == "CAP10" else 0.05
            total = 0.10 if arm == "CAP10" else 0.25
            slots = 2 if arm == "RS08" else 6 if arm == "RS12" else 4
            rows.append(dict(Period=period, Arm=arm, Date=t, Equity=E, Safe_equity=d.Equity, Extra_gross=sum(extra.values()), Maximum_extra=max(extra.values(), default=0), Extra_positions=len(extra), Total_positions=len(held), Single_breach=max(extra.values(), default=0) > cap * E + 0.1, Total_breach=sum(extra.values()) > total * E + 0.1, Slot_breach=len(extra) > slots or len(held) > 6 + slots, Safe_equity_valid=d.Equity <= E + 0.1, Extra_loss_50pct=sum(extra.values()) * 0.5 / E, Extra_loss_100pct=sum(extra.values()) / E))
            for i in held:
                role = roles.get(i, "exit")
                oldrole = previous_roles.get(i)
                role_rows.append(dict(Period=period, Arm=arm, Date=t, Pair_id=i, Role=role, Previous_role=oldrole, Quantity=q[i], Gross_value=q[i] * experiment.engine.observed_quote(data, i, t)[0], Promotion=oldrole == "additional" and role == "core", Demotion=oldrole == "core" and role == "additional"))
            previous_roles = roles
    out = pd.DataFrame(rows)
    out.to_csv(data["artifact"] / "executed-exposure.csv", index=False)
    pd.DataFrame(role_rows).to_parquet(data["artifact"] / "role-ledger.parquet", index=False)
    assert not out[["Single_breach", "Total_breach", "Slot_breach"]].any().any(), out[out[["Single_breach", "Total_breach", "Slot_breach"]].any(axis=1)].to_dict("records")[:3]
    assert out.Safe_equity_valid.all()
    return out, pd.DataFrame(role_rows)


def period_report(data, results, runs, attr, weights, fees, robust, tails, period):
    f = results[results.Period.eq(period)].copy()
    arms = list(f.Arm)
    base = f.set_index("Arm").loc["C00"]
    f["Incremental profit (USD)"] = f["Net profit (USD)"] - base["Net profit (USD)"]
    display(Markdown("## " + ("2026 economic results" if period == "2026" else "Full-history economic results") + "\n\nFresh $150,000 accounts, " + LABELS[period] + ". All arms use the common fresh-entry cached-tax reset and corrected partial trims. Full history overlaps the short period."))
    heading("Key metrics side by side", "Each row is one metric, each column one strategy. Colouring compares only the same metric. C00 is the exact source-authoritative six-slot core with the shared valuation correction.", period)
    metrics = ["Net profit (USD)", "Cumulative return", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Calmar"]
    wide = f.set_index("Arm")[metrics].T
    s = wide.style.format("{:.2f}", na_rep="—")
    for metric in metrics:
        s = s.format("${:,.0f}" if "USD" in metric else "{:.2%}" if metric in ("CAGR", "Maximum drawdown", "Cumulative return") else "{:.2f}", subset=pd.IndexSlice[[metric], :]).background_gradient(subset=pd.IndexSlice[[metric], :], axis=1, cmap="RdYlGn")
    display(s)
    heading("Deployment, breadth and trading", "Additional tickets are limited allocations, not a request to invest all cash. Mean cash includes unavailable early history. Effective breadth discounts concentration. Incremental profit includes core feedback and costs.", period)
    table(f[["Arm", "Incremental profit (USD)", "Mean cash weight", "September cash", "Maximum vaults held", "Mean effective breadth", "Mean vaults held", "Trades", "Gross trade turnover (USD)", "Worst 7-day return", "Worst 30-day return"]])
    charts.experiment = experiment
    charts.COLOURS = {a: plt.get_cmap("tab20")(i) for i, a in enumerate(arms)}
    charts.equity(data, runs, period, arms)
    incremental_equity(data, runs, period)
    vals = {}
    for a in arms:
        e = runs[(period, a)]["equity"].resample("D").last().ffill()
        p = e.diff()
        p.iloc[0] = e.iloc[0] - 150000
        vals[a] = p.groupby(p.index.to_period("Q")).sum()
    quarterly = pd.DataFrame(vals).T
    delta = quarterly.sub(quarterly.loc["C00"], axis=1) / 1000
    delta.columns = [str(c) + ("*" if j == len(delta.columns) - 1 or period == "Long" and j == 0 else "") for j, c in enumerate(delta.columns)]
    heatmap(data, delta, "quarter-profit", "Quarterly incremental profit versus C00", "Account-dollar profit difference; * marks partial calendar coverage, including October. Differences include compounding and role changes. These quarters are descriptive, not independent validation.", period)
    visible = set()
    for w in weights.values():
        visible.update(w.drop(columns=[c for c in w if c in ("USD", "USDC", "USDT")]).mean().nlargest(9).index)
    names = sorted(visible)
    colours = [plt.get_cmap("tab20")(i) for i in [0, 2, 4, 6, 8, 10, 12, 16, 18, 1, 3, 5, 7, 9, 11, 13, 17, 19]]
    palette = {c: colours[i] if i < len(colours) else plt.get_cmap("turbo")((i - len(colours) + 1) / (len(names) - len(colours) + 2)) for i, c in enumerate(names)}
    for a in arms:
        charts.weights_chart(data, weights, period, a, palette)
    heading("Paid costs and final open liabilities", "Sell deductions use actual recorded quantities and gross observed NAV. Open performance and capital exit allowances are distinct from fees already paid. These are inherited modelling assumptions, not verified additional venue fees.", period)
    table(fees[fees.Period.eq(period)].drop(columns="Period"))
    heading("Contributor concentration and strongest update", "Largest positive vault share, kurtosis and strongest marked update. A sparse catch-up may bunch profits into a later date. This cannot establish that execution at the recorded NAV was available.", period)
    table(robust[robust.Period.eq(period)].drop(columns="Period"))
    heading("Strongest-update market and curator context", "Leading vault behind the strongest update in each account, compared with BTC/ETH during the actual NAV observation interval. Curator flags are retrospective context.", period)
    table(tails[tails.Period.eq(period)].groupby("Arm").head(1)[["Arm", "Update", "Vault", "Update profit (USD)", "NAV_return", "Interval_days", "BTCUSDT return", "ETHUSDT return", "Excluded", "Quarantined"]])
    heading("Leading contributors and fixed-ledger removal", "Removing the largest positive contributor is a descriptive robustness check without rebalancing or changing later membership. It is not a replay of a tradable replacement strategy.", period)
    rows = []
    for a in arms:
        v = attr[(period, a)]
        largest = float(v.max())
        rows.append(dict(Arm=a, Top_vault=v.idxmax(), **{"Largest contribution (USD)": largest, "Profit after deleting largest (USD)": float(v.sum() - largest)}))
    table(pd.DataFrame(rows))
    deletions = []
    for arm in arms:
        e = runs[(period, arm)]["equity"].resample("D").last().ffill()
        updates = e.diff()
        updates.iloc[0] = e.iloc[0] - 150000
        best = float(updates.max())
        q = updates.groupby(updates.index.to_period("Q")).sum()
        deletions.append(dict(Arm=arm, **{"Profit excluding best daily update (USD)": float(updates.sum() - best), "Lowest profit after excluding one quarter (USD)": float(updates.sum() - q.max()), "Highest profit after excluding one quarter (USD)": float(updates.sum() - q.min())}))
    heading("Best-update and quarter deletion sensitivity", "Remove one booked daily update or one calendar quarter from each fixed account ledger. No reinvestment or replacement is simulated; these dollar sensitivities are not recalculated CAGR or independent validation. Partial quarters remain included.", period)
    table(pd.DataFrame(deletions))
    pd.DataFrame(deletions).to_csv(data["artifact"] / f"{period}-deletion-sensitivity.csv", index=False)
    return f


def mechanisms(data, results, runs, weights, audit, roles):
    ds = pd.DataFrame(data["nb19_decisions"])
    ds.Date = pd.to_datetime(ds.Date)
    c = pd.DataFrame(data["nb19_candidates"])
    c.Date = pd.to_datetime(c.Date)
    c.Finite = c.Finite.map(lambda v: str(v).lower() in ("true", "1"))
    c["History_age_days"] = [data["date_index"][t - pd.Timedelta(days=1)] - data["first_index"][data["id_index"][int(i)]] for t, i in zip(c.Date, c.Pair_id)]
    support = []
    for t, group in c.groupby("Date"):
        rr = experiment.fixed_risk(data, t, list(map(int, group.Pair_id.unique()))).reset_index(names="Pair_id")
        rr["Date"] = t
        support.append(rr[["Date", "Pair_id", "predicted", "prior", "peer_count"]])
    c = c.merge(pd.concat(support, ignore_index=True), on=["Date", "Pair_id"], how="left", validate="many_to_one")
    c.to_parquet(data["artifact"] / "candidate-support-enriched.parquet", index=False)
    d = ds[ds.Period.eq("2026")]
    f = c[c.Period.eq("2026")]
    a = audit[audit.Period.eq("2026")]
    heading("Source core protection and executed limits", "The source six-slot proposal is captured before merging; its target values remain unchanged. Separate executed audits rebuild holdings and check single/total gross caps and slot ceilings. This proves conditional intentions and limit compliance; future independent C00 trajectories can differ.", "2026")
    checks = pd.DataFrame(data["nb19_checks"])
    x = checks[checks.Period.eq("2026")].groupby(["Arm", "Check"]).agg(Decisions=("Date", "size"), Maximum_shortfall=("Shortfall", "max")).reset_index()
    table(x)
    heading("Capital, slots and mechanical loss stress", "Gross exposure after executed trades. Loss stress assumes all additional NAV loses 50% or 100% immediately, without selling, fees or core feedback; it is not a probability forecast.", "2026")
    table(a.groupby("Arm").agg(Decisions=("Date", "size"), Mean_extra_gross_USD=("Extra_gross", "mean"), Maximum_extra_positions=("Extra_positions", "max"), Maximum_total_positions=("Total_positions", "max"), Worst_50pct_loss=("Extra_loss_50pct", "max"), Worst_100pct_loss=("Extra_loss_100pct", "max"), Single_breaches=("Single_breach", "sum"), Total_breaches=("Total_breach", "sum"), Slot_breaches=("Slot_breach", "sum")).reset_index())
    heading("Score-sensitive ticket activation", "Count fresh accepted proposals at the floor, strictly intermediate score multiplier and one. Accepted dollars are intentions; a separate execution mapping checks actual buys. Missing and finite zero remain different labels.", "2026")
    rows = []
    for arm, ff in f.groupby("Arm"):
        fresh = ff[~ff.Incumbent & ff.Accepted.gt(0)]
        floor = 0.25 if arm == "GF25" else 0.5
        rows.append(dict(Arm=arm, Fresh_proposals=len(fresh), Missing=int((~fresh.Finite).sum()), Finite_zero=int((fresh.Finite & fresh.Score.eq(0)).sum()), Floor=int(np.isclose(fresh.G, floor).sum()), Interior=int(((fresh.G > floor + 1e-9) & (fresh.G < 1 - 1e-9)).sum()), At_one=int(np.isclose(fresh.G, 1).sum()), Accepted_USD=fresh.Accepted.sum()))
    table(pd.DataFrame(rows))
    fresh = f[f.Arm.eq("RS00") & ~f.Incumbent].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    equity = d[d.Arm.eq("RS00")].set_index("Date").Equity
    riskonly = np.minimum(fresh.Cap, 0.5 * 0.05 * fresh.Date.map(equity) * fresh.R)
    for finite, colour, name in [(True, "#2563eb", "Finite score"), (False, "#d97706", "Missing score")]:
        mask = fresh.Finite.eq(finite)
        ax.scatter(riskonly[mask] / 1000, fresh.loc[mask, "Ticket"] / 1000, c=colour, s=20, alpha=0.45, label=name)
    high = max(1, riskonly.max() / 1000)
    ax.plot([0, high], [0, high], color="grey", ls="--", label="Identical ticket")
    ax.legend(fontsize=9)
    ax.set(xlabel="Capacity-clipped risk-only ticket ($ thousands)", ylabel="Combined ticket before execution ($ thousands)", title="RS00: score attenuation before source capacity\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    figure(data, fig, "2026-ticket-attenuation", "Score attenuation and capacity", "Blue finite scores, orange missing. Both tickets apply the multiplier before the same capacity ceiling. Coincident tickets reveal cap saturation despite different utilities; the diagonal is identical sizing. Points on zero include infeasible candidates.", "2026")
    executed = []
    lookup = f.set_index(["Arm", "Date", "Pair_id"])
    for (period, arm), r in runs.items():
        if period != "2026" or arm == "C00":
            continue
        for t in r["result"].state.portfolio.get_all_trades():
            if not t.is_success() or not t.is_buy():
                continue
            key = (arm, pd.Timestamp(t.executed_at), int(t.pair.internal_id))
            if key not in lookup.index:
                continue
            row = lookup.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
            if row.Accepted <= 0:
                continue
            E = float(r["equity"].loc[: pd.Timestamp(t.executed_at)].iloc[-1])
            executed.append(dict(Arm=arm, Date=t.executed_at, Score=row.Score, Finite=row.Finite, G=row.G, Reserve=float(t.executed_reserve), Weight=float(t.executed_reserve) / E, Quarter=str(pd.Timestamp(t.executed_at).to_period("Q"))))
    ex = pd.DataFrame(executed)
    ex.to_csv(data["artifact"] / "score-sensitive-execution.csv", index=False)
    fig, ax = plt.subplots(figsize=(9.5, 5))
    for quarter, ff in ex[ex.Arm.eq("RS00")].groupby("Quarter"):
        ax.scatter(ff.Score, ff.Weight * 100, label=quarter, s=30, alpha=0.7)
    ax.set(xlabel="Source composite score (missing maps to numeric zero)", ylabel="Executed buy reserve / marked equity (%)", title="RS00: score versus executed additional buy\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend()
    figure(data, fig, "2026-score-execution", "Score versus executed additional buys", "Actual reserves spent, not target weights. Missing entries share numeric zero under the source rank rule; their separate flags and counts are retained in the activation table. Colours show quarter.", "2026")
    fig, ax = plt.subplots(figsize=(10, 4.7))
    groups = []
    for arm, ff in a.groupby("Arm"):
        series = ff.set_index("Date").Extra_positions
        match = next((g for g in groups if g[1].equals(series)), None)
        if match is None:
            groups.append(([arm], series))
        else:
            match[0].append(arm)
    for aliases, series in groups:
        ax.step(series.index, series, label="/".join(aliases), lw=1.2, where="post")
    ax.set_yticks(range(7))
    ax.set(ylabel="Additional vaults held", title="Executed additional breadth\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend(ncol=5, fontsize=8)
    figure(data, fig, "2026-breadth", "Funded breadth over time", "Executed holdings can be below slot ceilings because permissions, capacity, floors and retained holdings constrain admission. This is not effective concentration-based breadth.", "2026")
    reasons = f.groupby(["Arm", "Reason"]).size().unstack(fill_value=0)
    heading("Ordered candidate rejection counts", "Each candidate receives one primary reason in the admission sequence. Counts are candidate/date observations, not additive dollars; retained candidates are included. The complete ledger stores capacities, tickets, ages and update support.", "2026")
    table(reasons.reset_index())
    heading("Mandatory recalls and role transitions", "Recall counts refer to held extras closed to restore the core-only funding opportunity. Promotions/demotions preserve positions and cost basis, rather than requiring sell-and-rebuy.", "2026")
    trans = roles[roles.Period.eq("2026")].groupby("Arm").agg(Promotions=("Promotion", "sum"), Demotions=("Demotion", "sum"))
    rr = d.groupby("Arm").Funding_recall.sum().rename("Funding_recalls")
    table(trans.join(rr).reset_index())
    heading("Asymmetric resizing bands", "Source buy/sell bands are preserved. Small requested reductions can be suppressed while larger increases execute. Count targets and signed executed reserves separately; mandatory exits are reported in recall/role ledgers.", "2026")
    table(resize_diagnostics(data, runs))
    heading("Missing/young risk support in accepted targets", "Accepted proposal observations, not distinct capital. Prior-only risk uses r=1 when a positive peer prior exists; score floors and exposure caps provide attenuation. Update age is retained independently from carried NAV.", "2026")
    ff = f[f.Accepted.gt(0)]
    table(ff.groupby("Arm").agg(Accepted_observations=("Date", "size"), Missing_score=("Finite", lambda v: (~v).sum()), Young_under_360_days=("History_age_days", lambda v: (v < 360).sum()), Median_positive_peer_count=("peer_count", "median"), Prior_only=("Prior_only", "sum"), Median_actual_updates=("Updates", "median"), Median_quote_age_days=("Age", "median")).reset_index())
    locked = []
    for (arm, t), ff in f.groupby(["Arm", "Date"]):
        blocked = ff[ff.Reason.eq("slots") & ~ff.Incumbent & ff.Finite & ff.Cap.ge(ff.Ticket) & ff.Ticket.gt(0)]
        inc = ff[ff.Incumbent & ff.Accepted.gt(0) & ff.Finite]
        if len(blocked) == 0 or len(inc) == 0:
            continue
        low = inc.sort_values(["Score", "Pair_id"]).iloc[0]
        for row in blocked.itertuples():
            if row.Score <= low.Score:
                continue
            for h in (7, 30):
                xx = label(data, int(row.Pair_id), t, h)
                yy = label(data, int(low.Pair_id), t, h)
                resolved = xx["Resolved"] and yy["Resolved"]
                locked.append(dict(Arm=arm, Date=t, H=h, Fresh_score=row.Score, Incumbent_score=low.Score, Resolved=resolved, Fresh_return=xx["Y"], Incumbent_return=yy["Y"], Difference=xx["Y"] - yy["Y"] if resolved else np.nan))
    ll = pd.DataFrame(locked)
    ll.to_csv(data["artifact"] / "locked-slot-counterfactual.csv", index=False)
    heading("Locked-slot counterfactual opportunities", "Finite higher-score fresh candidates blocked by occupied slots versus the lowest-score finite incumbent. As-of NAV outcomes require observed terminal support; unresolved pairs stay missing. Overlapping opportunities are not independent, nor executed replacement profits.", "2026")
    if len(ll):
        table(ll.groupby(["Arm", "H"]).agg(Pairs=("Date", "size"), Resolved=("Resolved", "sum"), Mean_return_difference=("Difference", "mean")).reset_index())
    else:
        display(Markdown("No qualifying higher-score finite candidate/incumbent pairs."))
    return ds, c, ex


def findings(data, results, attr, robust, ex, audit):
    text = ["# Experiment 19 — protected core with score and risk sizing", "", "## Key new insights", "", "The experiment preserves the source-authoritative C-W core and adds limited absolute tickets. Extra holdings influence future account wealth, fees and core decisions; incremental account profit is not a causal sleeve-only return."]
    for period in experiment.PERIODS:
        f = results[results.Period.eq(period)].set_index("Arm")
        b = f.loc["C00"]
        best = f.CAGR.idxmax()
        sh = f.Sharpe.idxmax()
        text += ["", "## " + ("2026 results" if period == "2026" else "Full-history results"), "", LABELS[period] + ". Fresh $150,000; common corrected entry valuation.", "", "| Method | Net profit | CAGR | Sharpe | Max drawdown | September cash |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for arm, r in f.iterrows():
            text.append(f'| {arm} | ${r["Net profit (USD)"]:,.0f} | {r.CAGR:.2%} | {r.Sharpe:.2f} | {r["Maximum drawdown"]:.2%} | {r["September cash"]:.2%} |')
        rs = f.loc["RS00"]
        text += ["", f'CAGR leader: **{best}**. Sharpe leader: **{sh}**. RS00 versus C00 changes net profit by ${rs["Net profit (USD)"]-b["Net profit (USD)"]:+,.0f}, CAGR by {(rs.CAGR-b.CAGR)*100:+.2f} percentage points and Sharpe by {rs.Sharpe-b.Sharpe:+.2f}.', f'Holding versus resizing combined tickets: RS01 − RS00 profit ${f.loc["RS01","Net profit (USD)"]-rs["Net profit (USD)"]:+,.0f}. Normalising versus absolute resize: NRS00 − RS01 ${f.loc["NRS00","Net profit (USD)"]-f.loc["RS01","Net profit (USD)"]:+,.0f}.']
    text += ["", "## Hypotheses and interpretation", ""]
    for h, desc, left, right in [("H1", "Extra breadth", "E00", "C00"), ("H2", "Combined score/risk versus risk alone", "RS00", "R00"), ("H3", "Absolute versus normalised resizing", "RS01", "NRS00"), ("H4", "Hold versus resize", "RS00", "RS01"), ("H5", "Twelve versus eight slots", "RS12", "RS08")]:
        vals = []
        for p in experiment.PERIODS:
            f = results[results.Period.eq(p)].set_index("Arm")
            vals.append(f.loc[left, "Net profit (USD)"] - f.loc[right, "Net profit (USD)"])
        verdict = "supported on both inspected histories" if min(vals) > 0 else "rejected on both inspected histories" if max(vals) < 0 else "mixed across histories"
        text.append(f"- **{h} — {desc}:** {left} − {right} ${vals[0]:+,.0f} in 2026 / ${vals[1]:+,.0f} full history; {verdict}. These are package comparisons, not independent statistical confirmations.")
    fshort = results[results.Period.eq("2026")].set_index("Arm")
    flong = results[results.Period.eq("Long")].set_index("Arm")
    if "GF25" in fshort.index:
        text += ["", f'**H6 — local assumptions:** lower floor GF25 − RS00 profit ${fshort.loc["GF25","Net profit (USD)"]-fshort.loc["RS00","Net profit (USD)"]:+,.0f} / ${flong.loc["GF25","Net profit (USD)"]-flong.loc["RS00","Net profit (USD)"]:+,.0f}; smaller-cap CAP10 − RS00 ${fshort.loc["CAP10","Net profit (USD)"]-fshort.loc["RS00","Net profit (USD)"]:+,.0f} / ${flong.loc["CAP10","Net profit (USD)"]-flong.loc["RS00","Net profit (USD)"]:+,.0f}. Neither floor nor caps are established as optimal.']
    leader = fshort.CAGR.idxmax()
    text += ["", f"**Practical shortlist:** {leader} leads inspected 2026 CAGR. RS01 is the direct management contrast to the primary held-ticket method. Compare its full-history profit, drawdown, contributors and costs before considering further observations. More cash use alone is not a reason to promote a strategy."]
    role = pd.read_csv(data["artifact"] / "role-productivity.csv").set_index("Arm")
    rsrole = role.loc["RS01"]
    delta = fshort.loc["RS01", "Net profit (USD)"] - fshort.loc["C00", "Net profit (USD)"]
    text += ["", f'**Economic attribution:** RS01 gains only ${delta:+,.0f} in fresh 2026. Interval-start role bookkeeping assigns ${rsrole["Additional-role booked PnL (USD)"]:+,.0f} to additional holdings and ${rsrole["Core/other booked PnL (USD)"]-fshort.loc["C00","Net profit (USD)"]:+,.0f} to core/other feedback. This does not show profitable extras in isolation. Its September cash is {fshort.loc["RS01","September cash"]:.1%}, versus {fshort.loc["C00","September cash"]:.1%}; substantial cash remains.']
    text += ["", "**Timing and concentration:** economic accounts are identical before the first additional opportunities in late 2025 in the long account. The fresh-2026 common strongest update is 26 June: Realist Capital and Goon Edging each gain about 14% over roughly two observed days while BTC/ETH fall about 4.7%/6.0%. Realist contributes about 35% of positive 2026 vault profit. The long strongest update, 13 November 2024, precedes any additional allocation and therefore cannot explain a treatment advantage. These are sparse recorded-NAV updates, not demonstrated executable fills at every intervening timestamp."]
    text += [
        "",
        "## Robustness of results",
        "",
        "Complete historical versus zero-extra equity and trade parity is required. The source core targets are unchanged by the merge and executed gross exposure/slot checks pass. A common fresh-entry cached-tax reset isolates the previously identified close/reopen marking inconsistency; historical control metrics are shown separately. Daily-resampled Sharpe includes off-cycle zero bins.",
        "",
        "Contributor deletion, strongest-update curator/BTC/ETH context, overlapping quarter differences, sparse actual-update support, locked-slot counterfactuals and mechanical sleeve loss stress appear in the notebook. The hard-cap audit caught and repaired a suppressed trim: marked-to-gross conversion now uses each holding’s actual ratio, with a full close when the required reduction is below the source band. All accounts were rerun under the new identity. The conservative denominator includes both existing-position liquidation allowances and a possible new-entry capital allowance; initial all-cash snapshots are checked as well. No untouched holdout exists. Recorded NAV is not proof of an executable quote, and the inherited fee assumptions remain economically unverified.",
        "",
        "## Next action",
        "",
        "Treat improved historical profit and risk as a shortlist criterion. Require a later observation period and verified fee/permission conventions before production changes. Do not optimise floor, slot count or exposure limits using this same result table.",
    ]
    result = ("\n".join(text) + "\n").replace("$", r"\$")
    (ROOT / "19-protected-core-score-risk-allocation-findings.md").write_text(result)
    header = ROOT / "19-backtest-protected-core-score-risk-allocation.ipynb"
    import nbformat

    intro = nbformat.read(header, 4).cells[0].source.split("Results pending execution.")[0].split("## Key new insights")[0].replace(r"\$", "$")
    f = results[results.Period.eq("2026")].set_index("Arm")
    b = f.loc["C00"]
    r = f.loc["RS00"]
    lead = f.loc["RS01"]
    long = results[results.Period.eq("Long")].set_index("Arm")
    head = intro + f"""## Key new insights

Source-authoritative core parity passes. More positions are sized with absolute tickets rather than rewriting the core selector. Score/cap/trade-floor interactions determine whether score multipliers reach execution.

Resizing combined tickets RS01 gives a small profit/CAGR/Sharpe lead over C00 in both researched periods; holding those tickets loses in 2026. Combined score/risk holding also loses to risk-only holding in both periods, so this does not establish extra predictive value from the score multiplier. More slots and more deployment are not consistently more profitable.

## Summary of results

2026 C00: CAGR **{b.CAGR:.2%}**, Sharpe **{b.Sharpe:.2f}**, drawdown **{b['Maximum drawdown']:.2%}**. Combined held tickets RS00: **{r.CAGR:.2%}**, **{r.Sharpe:.2f}**, **{r['Maximum drawdown']:.2%}**, incremental net profit **${r['Net profit (USD)']-b['Net profit (USD)']:+,.0f}**. Full-history results and every method appear below. [Detailed findings](19-protected-core-score-risk-allocation-findings.md).

RS01: **{lead.CAGR:.2%} CAGR**, **{lead.Sharpe:.2f} Sharpe**, **{lead['Maximum drawdown']:.2%} drawdown**, **${lead['Net profit (USD)']-b['Net profit (USD)']:+,.0f}** profit versus C00 in 2026. Full history: **{long.loc['RS01','CAGR']:.2%}** versus C00 **{long.loc['C00','CAGR']:.2%}**, **${long.loc['RS01','Net profit (USD)']-long.loc['C00','Net profit (USD)']:+,.0f}** incremental profit. September cash remains **{lead['September cash']:.1%}** in fresh 2026. The small 2026 gain comes with slightly worse drawdown.

## Robustness of results

Historical zero-extra complete equity/trade parity passes; common fresh-entry cached-tax reset applies to all economic arms. Recorded NAV, researched overlapping periods, retrospective guard/universe and inherited exit charges qualify conclusions. Contributor concentration, sparse observation support, costs, locked-slot outcomes and mechanical loss stress are reported separately. Independent C00 trajectories can diverge after sleeve PnL changes wealth.
"""
    (data["artifact"] / "final-header.md").write_text(head.replace("$", r"\$"))
    return result


def report(data, results, runs, attr, weights, evaluator=None):
    for (period, arm), w in weights.items():
        reserve = next(c for c in w if c in ("USDC", "USDT", "USD"))
        results.loc[results.Period.eq(period) & results.Arm.eq(arm), "Mean vaults held"] = float(w.drop(columns=reserve).gt(1e-8).sum(axis=1).mean())
    results.to_csv(data["artifact"] / "results.csv", index=False)
    from protected_core_score_checks import adapter_cases

    cases = adapter_cases()
    cases.to_csv(data["artifact"] / "adapter-case-checks.csv", index=False)
    heading("Isolated source-state adapter cases", "The real additional-allocation merge is exercised with synthetic source states for unscored entry, blocked top-up, hard trim, minimum tickets, pinning, promotion and held-role isolation. These fixtures complement complete source replay parity; they do not validate asynchronous venue settlement.", "2026")
    table(cases)
    display(Markdown("<details><summary>Source, data and framework fingerprints</summary>\n\n```json\n" + json.dumps(data["manifest"], indent=2, default=str) + "\n```\n\n</details>"))
    heading("Strategy logic comparison", "Frozen core score/selector/waterfall in all methods. Only additional ticket utility, management and slot/exposure limits vary. Missing inputs retain positive score floors and supported peer risk.", "2026")
    logic = pd.DataFrame([dict(Arm=a, Method=experiment.METHODS[a], Core="Source C-W; six; entry6/exit8", Extra_slots=0 if a == "C00" else 2 if a == "RS08" else 6 if a == "RS12" else 4, Management="source" if a == "C00" else "resize" if a in ("RS01", "NRS00") else "hold units", Single_cap="—" if a == "C00" else "2%" if a == "CAP10" else "5%", Total_cap="—" if a == "C00" else "10%" if a == "CAP10" else "25%") for a in results[results.Period.eq("2026")].Arm])
    table(logic)
    historical = []
    for (p, a), r in data["historical_runs"].items():
        new = results[results.Period.eq(p) & results.Arm.eq(a)].iloc[0]
        historical.append(dict(Period=p, Historical_CAGR=r["metrics"]["CAGR"], Common_CAGR=new.CAGR, Historical_Sharpe=r["metrics"]["Sharpe"], Common_Sharpe=new.Sharpe, **{"Profit change (USD)": new["Final equity (USD)"] - r["metrics"]["Final equity (USD)"]}))
    pd.DataFrame(historical).to_csv(data["artifact"] / "valuation-control-difference.csv", index=False)
    heading("Common entry valuation versus historical C00", "Historical source parity is preserved as a replication. Fresh entry resets the cached previous-position tax to the source 0.1% fallback before the generic valuation sees the newly opened position; current held top-ups retain refreshed fees. This affects marking and potentially future sizing. No archive update occurred during NB19; this comparison isolates a code/accounting convention change.", "2026")
    table(pd.DataFrame(historical).query('Period == "2026"').drop(columns="Period"))
    fees = fee_accounting(data, runs)
    robust, tails = robustness(data, results, runs, attr)
    audit, roles = execution(data, runs)
    f = period_report(data, results, runs, attr, weights, fees, robust, tails, "2026")
    for x, y, title, name in [("CAGR", "Sharpe", "CAGR versus Sharpe", "cagr-sharpe"), ("Maximum drawdown", "CAGR", "CAGR versus drawdown", "cagr-dd"), ("Maximum drawdown", "Sharpe", "Sharpe versus drawdown", "sharpe-dd"), ("September cash", "Net profit (USD)", "Cash versus profit", "cash-profit")]:
        scatter(data, f, x, y, title, name, "2026")
    ds, c, ex = mechanisms(data, results, runs, weights, audit, roles)
    if evaluator is not None:
        from conditional_cash_forecasts import build_anchor

        build_anchor(data, runs[("Long", "C00")])
        c00_shadow_diagnostics(data, evaluator, runs[("2026", "C00")])
    additional_diagnostics(data, results, runs, attr, audit, roles, c)
    heading("Registered local sensitivity outcomes", "Only registered combinations are displayed. Eight/ten/twelve slots share the combined hold utility. GF25 changes all score floors; CAP10 changes single/total caps and ticket size together. This is not a full factorial grid.", "2026")
    table(f[f.Arm.isin(["RS08", "RS00", "RS12", "RS01", "NRS00", "GF25", "CAP10"])][["Arm", "Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown", "September cash"]])
    period_report(data, results, runs, attr, weights, fees, robust, tails, "Long")
    text = findings(data, results, attr, robust, ex, audit)
    display(Markdown("## Verdict and next step\n\n" + text.split("## Hypotheses and interpretation")[1]))
    (data["artifact"] / "figures.json").write_text(json.dumps(data["figures"], indent=2))
    import hashlib

    (data["artifact"] / "complete.json").write_text(json.dumps(dict(status="complete", economic_accounts=len(results), periods=2, figures=len(data["figures"]), adapter_fixture_checks=len(cases), executed_limit_breaches=int(audit[["Single_breach", "Total_breach", "Slot_breach"]].sum().sum()), safe_equity_checks=int(audit.Safe_equity_valid.sum()), report_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2))
    return text


def additional_diagnostics(data, results, runs, attr, audit, roles, candidates):
    """Explain valuation routes, turnover and interacting core/sleeve contributions."""
    heading("Reopened-position entry quote audit", "One fresh-entry quote per vault/date. Cached rates above the 0.1% source fallback belong to an earlier position. The local reset occurs before the generic entry valuation. Tax-gap dollar-days are exposure diagnostics, not an exact performance adjustment.", "2026")
    qq = pd.DataFrame(data["nb19_quotes"])
    qq.Date = pd.to_datetime(qq.Date)
    qq = qq[qq.Period.eq("2026")].drop_duplicates(["Arm", "Date", "Pair_id", "Cached"])
    rows = []
    for arm, f in qq.groupby("Arm"):
        positive = f[f.Gap.gt(1e-9)]
        dollar_days = 0.0
        final = 0
        if ("2026", arm) in runs:
            r = runs[("2026", arm)]
            trades = [t for t in r["result"].state.portfolio.get_all_trades() if t.is_success() and t.is_buy()]
            for v in positive.itertuples():
                buys = [t for t in trades if t.pair.internal_id == v.Pair_id and pd.Timestamp(t.executed_at) == v.Date]
                gross = sum(float(t.executed_reserve) for t in buys)
                days = min(2.0, max(0, (r["equity"].index[-1] - v.Date).total_seconds() / 86400))
                dollar_days += gross * v.Gap * days
                final += int(v.Date + pd.Timedelta(days=2) > r["equity"].index[-1])
        rows.append(dict(Arm=arm, Unique_fresh_quotes=len(f), Prior_tax_quotes=len(positive), Maximum_prior_tax=float(f.Cached.max()), Tax_gap_dollar_days=dollar_days, Final_window_entries=final))
    table(pd.DataFrame(rows))
    heading("Holding duration and fast repurchases", "Position-level durations include core and additional roles. Promotions do not restart the clock. A repurchase within four days follows a completed close; overlapping metrics are descriptive.", "2026")
    turnover = []
    durations = []
    for (period, arm), r in runs.items():
        if period != "2026":
            continue
        closed = list(r["result"].state.portfolio.closed_positions.values())
        opened = list(r["result"].state.portfolio.get_all_positions())
        days = [(pd.Timestamp(p.closed_at) - pd.Timestamp(p.opened_at)).total_seconds() / 86400 for p in closed if p.closed_at]
        rebuys = sum(any(p.pair.pool_address == q.pair.pool_address and pd.Timestamp(p.closed_at) < pd.Timestamp(q.opened_at) <= pd.Timestamp(p.closed_at) + pd.Timedelta(days=4) for q in opened) for p in closed if p.closed_at)
        turnover.append(dict(Arm=arm, Closed=len(closed), Median_days=np.median(days) if days else np.nan, Repurchases_within_four_days=rebuys))
        if arm in ("C00", "RS00", "RS01", "NRS00"):
            durations.extend(dict(Arm=arm, Days=d) for d in days)
    table(pd.DataFrame(turnover))
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    dd = pd.DataFrame(durations)
    for arm, f in dd.groupby("Arm"):
        ax.hist(f.Days, bins=[0, 2, 4, 8, 16, 32, 64, 128, 256, 512], histtype="step", lw=1.5, label=arm)
    ax.set(xscale="symlog", xlabel="Closed-position duration (days; logarithmic after 2)", ylabel="Positions", title="Holding duration versus resizing\n" + LABELS["2026"])
    ax.legend()
    ax.grid(alpha=0.2)
    figure(data, fig, "2026-holding-duration", "Holding durations", "Each closed position contributes once. Different account exposure paths and selection histories affect durations; this is not a fee-only causal contrast.", "2026")
    heading("Whole-account shared-vault and additional-only profit", "Shared means a vault also held by independent C00 at some time. This decomposition reconciles incremental final account PnL and exposes feedback; shared vaults can also be additional at other times. It is not causal core-versus-sleeve attribution.", "2026")
    baseline = attr[("2026", "C00")]
    rows = []
    for (period, arm), pnl in attr.items():
        if period != "2026":
            continue
        shared = pnl.index.intersection(baseline.index)
        rows.append(dict(Arm=arm, **{"Shared-vault profit difference (USD)": float(pnl.reindex(baseline.index, fill_value=0).sum() - baseline.sum()), "Additional-only vault profit (USD)": float(pnl.loc[pnl.index.difference(baseline.index)].sum()), "Account difference (USD)": float(pnl.sum() - baseline.sum())}))
    table(pd.DataFrame(rows))
    heading("Role exposure and mechanical dollar-day productivity", "PnL changes are booked to the last known role at the start of each daily interval; close costs follow the prior role. Gross exposure carries the last observation after inception. This bookkeeping reconciles total PnL but does not establish causal sleeve profit: role changes, costs and compounding interact. The saved position curves and role ledger support forensic analysis.", "2026")
    role = roles[roles.Period.eq("2026") & roles.Role.eq("additional")]
    table(role_productivity(data, runs, roles))
    heading("Common-basket allocation shadows and score placebo", "RS00 source-time candidates, same four-name feasible basket and smaller common budget. Normalised utilities are reprojected to caps. A deterministic address-order reversal of scores diagnoses assignment sensitivity; these are proposal mechanics, not executed profits or a new strategy.", "2026")
    from portfolio_snapshot_construction import bounded_proportional

    cf = candidates[candidates.Period.eq("2026") & candidates.Arm.eq("RS00") & candidates.Accepted.gt(0)]
    shadows = []
    for t, f in cf.groupby("Date"):
        raw = f.G.to_numpy() * f.R.to_numpy()
        caps = f.Cap.to_numpy()
        budget = float(f.Accepted.sum())
        risk = bounded_proportional(f.R.to_numpy(), caps, budget)
        combined = bounded_proportional(raw, caps, budget)
        placebo = bounded_proportional(f.G.to_numpy()[::-1] * f.R.to_numpy(), caps, budget)
        assert abs(risk.sum() - combined.sum()) < 1e-6
        scaled = bounded_proportional(raw * 7, caps, budget)
        assert np.allclose(combined, scaled, atol=1e-6)
        shadows.append(dict(Date=t, Budget=budget, Names=len(f), Risk_score_L1=float(abs(risk - combined).sum()), Placebo_L1=float(abs(placebo - combined).sum()), Saturated=int(np.isclose(combined, caps, atol=1e-6).sum())))
    sh = pd.DataFrame(shadows)
    sh.to_csv(data["artifact"] / "common-basket-shadows.csv", index=False)
    table(pd.DataFrame([dict(Snapshots=len(sh), Unsaturated=int((sh.Saturated < sh.Names).sum()), Mean_common_budget_USD=sh.Budget.mean(), Mean_score_reallocation_USD=sh.Risk_score_L1.mean(), Mean_placebo_reallocation_USD=sh.Placebo_L1.mean())]))


def role_productivity(data, runs, roles):
    """Reconcile descriptive interval-start role accounting to complete PnL."""
    rows = []
    address_ids = data["identities"].set_index("vault_address").pair_id.to_dict()
    for (period, arm), r in runs.items():
        if period != "2026" or arm == "C00":
            continue
        rr = roles[roles.Period.eq(period) & roles.Arm.eq(arm)]
        daily = r["equity"].resample("D").last().ffill().index
        role = rr.pivot(index="Date", columns="Pair_id", values="Role").replace("exit", np.nan).reindex(daily).ffill().shift(1)
        exposure = rr.assign(Value=rr.Gross_value.where(rr.Role.eq("additional"), 0)).pivot(index="Date", columns="Pair_id", values="Value").reindex(daily).ffill().fillna(0)
        curves = pd.read_parquet(data["artifact"] / f"{period}-{arm}-position-curves.parquet")
        meta = pd.read_parquet(data["artifact"] / f"{period}-{arm}-positions.parquet").set_index("Position id")
        changes = curves.diff()
        changes.iloc[0] = curves.iloc[0]
        changes.index = pd.to_datetime(changes.index)
        total = 0.0
        extra = 0.0
        for position in changes:
            pid = int(address_ids[meta.loc[position, "Address"]])
            series = changes[position]
            total += series.sum()
            classification = role[pid].reindex(series.index).fillna("core") if pid in role else pd.Series("core", index=series.index)
            extra += series[classification.eq("additional")].sum()
        profit = float(r["equity"].iloc[-1] - 150000)
        assert abs(total - profit) < 1
        dd = float(exposure.sum().sum())
        rows.append(dict(Arm=arm, **{"Additional-role booked PnL (USD)": extra, "Core/other booked PnL (USD)": total - extra, "Total booked PnL (USD)": total, "Gross additional dollar-days": dd, "Additional PnL / dollar-day": extra / dd if dd else np.nan}))
    out = pd.DataFrame(rows)
    out.to_csv(data["artifact"] / "role-productivity.csv", index=False)
    return out


def c00_shadow_diagnostics(data, evaluator, reference_run):
    """Capture feasible alternative allocations on exact common C00 states."""
    from portfolio_snapshot_construction import bounded_proportional

    original = experiment.Adapter.merge
    rows = []
    snapshots = []
    capital_rows = []

    def capture(adapter, input, model, ordered, core_ids, B, buy, reference_equity, pm, sr, check_entry):
        original(adapter, input, model, ordered, core_ids, B, buy, reference_equity, pm, sr, check_entry)
        if adapter.name != "C00-diagnostic":
            return
        t = pd.Timestamp(input.timestamp)
        p = input.parameters
        targets = {i: float(model.signals[i].position_target or 0) for i in core_ids}
        core = sum(float(s.position_target or 0) for s in model.signals.values() if not s.carry_forward_position)
        E = max(0, min(reference_equity, (1 - float(p.vault_redemption_capital_fee)) * (float(input.state.portfolio.get_cash()) + (1 - float(p.vault_performance_fee) - float(p.vault_redemption_capital_fee)) * sum(float(v.get_quantity()) * experiment.engine.observed_quote(data, int(v.pair.internal_id), t)[0] for v in input.state.portfolio.get_open_positions()))))
        residual = max(0, B - core)
        ids = [int(i) for i, pair, score in ordered if i not in core_ids]
        risk = experiment.fixed_risk(data, t, ids)
        feasible = []
        scale_caps = {scale: {} for scale in (0.5, 1.0, 2.0)}
        from conditional_cash_forecasts import risk as gap_risk

        diagnostic_risk = gap_risk(data, t, ids + list(core_ids))
        for i, pair, score in ordered:
            if i in core_ids:
                continue
            check = check_entry(pair)
            if not pm.is_whitelisted_vault(pair) or not check.can_deposit:
                continue
            cap = float(sr.get_acceptable_size_for_position(t, pair, float(p.max_concentration_pct) * B).accepted_size)
            cap = min(cap, float(check.max_deposit)) if check.max_deposit is not None else cap
            r = float(risk.loc[i, "risk_multiplier"])
            g = 0.5 + 0.5 * np.clip(score, 0, 1)
            finite = np.isfinite(input.indicators.get_indicator_value("matrix_score", pair=pair))
            if not np.isfinite(r) or r <= 0:
                continue
            feasible.append(dict(Pair_id=i, Cap=cap, R=r, G=g, Score=score, Finite=finite, Sigma=np.sqrt(risk.loc[i, "predicted"]), Gap_sigma=float(diagnostic_risk.loc[i, "sigma"])))
            for scale in scale_caps:
                scaled = float(sr.get_acceptable_size_for_position(t, pair, float(p.max_concentration_pct) * B * scale).accepted_size)
                scale_caps[scale][i] = min(scaled, float(check.max_deposit)) if check.max_deposit is not None else scaled
        snapshots.append(dict(Date=t, Residual=residual, Equity=E, Feasible=len(feasible), Core_target=core, Buy_floor=buy))
        for scale, capacity in scale_caps.items():
            basket = feasible[:4]
            budget = min(residual * scale, 0.25 * E * scale)
            caps = np.array([min(capacity[v["Pair_id"]], 0.05 * E * scale) for v in basket])
            u = np.array([v["R"] * v["G"] for v in basket])
            ticket = np.minimum(caps, 0.5 * 0.05 * E * scale * u)
            remaining = budget
            for j in range(len(ticket)):
                ticket[j] = min(ticket[j], remaining)
                remaining -= ticket[j]
            ticket = np.where(ticket >= max(buy * scale, float(p.min_portfolio_weight_pct) * (core * scale + ticket.sum())), ticket, 0)
            capital_rows.append(dict(Date=t, Starting_capital=150000 * scale, Equity=E * scale, Residual=residual * scale, Proposed=float(ticket.sum()), Proposal_equity_fraction=float(ticket.sum()) / (E * scale) if E else 0, Names=int((ticket > 0).sum())))
        for slot_label, slots in [("2", 2), ("4", 4), ("6", 6), ("unlimited", len(feasible))]:
            for utility in ("flat", "risk", "score", "combined", "normalised risk", "normalised combined", "squared risk", "score reversed", "eta one"):
                basket = feasible[:slots]
                caps = np.array([min(v["Cap"], 0.05 * E) for v in basket])
                rr = np.array([v["R"] for v in basket])
                gg = np.array([v["G"] for v in basket])
                budget = min(residual, 0.25 * E)
                u = np.ones(len(basket)) if utility == "flat" else rr if utility in ("risk", "normalised risk") else gg if utility == "score" else rr**2 * gg if utility == "squared risk" else rr * gg[::-1] if utility == "score reversed" else rr * gg
                if utility.startswith("normalised"):
                    alloc = bounded_proportional(u, caps, budget) if len(basket) else np.array([])
                else:
                    alloc = np.minimum(caps, (1 if utility == "eta one" else 0.5) * 0.05 * E * u)
                    remaining = budget
                    for j in range(len(alloc)):
                        alloc[j] = min(alloc[j], remaining)
                        remaining -= alloc[j]
                alloc = np.where(alloc >= max(buy, float(p.min_portfolio_weight_pct) * (core + alloc.sum())), alloc, 0)
                gapload = sum(float(x) * v["Gap_sigma"] / E for x, v in zip(alloc, basket)) if E else 0
                from conditional_cash_forecasts import anchor_at

                A, support = anchor_at(data, t)
                rates = input.pricing_model._vault_redemption_fee_by_pair_id
                coreload = sum(targets[i] / max(1e-9, 1 - rates.get(i, 0.001)) / E * float(diagnostic_risk.loc[i, "sigma"]) for i in core_ids) if E else 0
                brake75 = min(1, max(0, 0.75 * A - coreload) / gapload) if gapload > 0 and np.isfinite(A) else 0
                brake100 = min(1, max(0, A - coreload) / gapload) if gapload > 0 and np.isfinite(A) else 0
                rows.append(dict(Date=t, Slots=slot_label, Utility=utility, Gap_ex_ante_risk=gapload, Anchor_support=support, Brake_75_proposed=float(alloc.sum()) * brake75, Brake_100_proposed=float(alloc.sum()) * brake100, Proposed=float(alloc.sum()), Names=int((alloc > 0).sum()), Residual=residual, Ex_ante_risk=sum(float(x) * v["Sigma"] / E for x, v in zip(alloc, basket)) if E else 0))

    experiment.Adapter.merge = capture
    try:
        with experiment.redirect_stdout(experiment.io.StringIO()), experiment.redirect_stderr(experiment.io.StringIO()):
            diagnostic = experiment.replay(data, evaluator, "C00-diagnostic", "2026", active=False)
    finally:
        experiment.Adapter.merge = original
    assert diagnostic["equity"].equals(reference_run["equity"])
    assert experiment.trade_signature(diagnostic) == experiment.trade_signature(reference_run)
    # Diagnostic replay is quick and intentionally uncached so its callback-derived rows survive reruns.
    for path in evaluator.folder.glob(diagnostic["cache_key"] + "*"):
        path.unlink()
    f = pd.DataFrame(rows).drop_duplicates(["Date", "Slots", "Utility"])
    s = pd.DataFrame(snapshots)
    f.to_csv(data["artifact"] / "c00-common-state-shadows.csv", index=False)
    s.to_csv(data["artifact"] / "c00-opportunity-calendar.csv", index=False)
    heading("Exact C00 residual opportunity calendar", "One diagnostic replay captures alternatives before C00 trade generation and proves complete equity/trade equality. A positive source target residual is not necessarily an executable ticket. Tiny residuals, permissions and floors reduce opportunities.", "2026")
    table(pd.DataFrame([dict(Decisions=len(s), Positive_target_residual=int(s.Residual.gt(1e-6).sum()), Residual_above_buy_floor=int(s.Residual.ge(s.Buy_floor).sum()), Median_positive_residual_USD=s.loc[s.Residual.gt(1e-6), "Residual"].median())]))
    pivot = f.groupby(["Utility", "Slots"]).Proposed.mean().unstack() / 1000
    heatmap(data, pivot, "c00-slot-utility-shadows", "C00 common-state allocation utilities", "Average proposed gross additional dollars at every source decision, in $ thousands. Columns are extra slots; core ranks stay fixed. Unlimited normalisation spreads the same budget so widely that source minimum tickets remove nearly all proposals. This is a floor interaction, not evidence of lower unconstrained capacity. The score-reversed diagnostic is a deterministic same-basket placebo, not a profit backtest.", "2026")
    capital = pd.DataFrame(capital_rows)
    capital.to_csv(data["artifact"] / "capital-size-shadows.csv", index=False)
    heading("Capital-size capacity shadows", "Scale C00 wealth, core targets, residual and portfolio-derived floors to initial USD 75k/150k/300k equivalents at the same dates. Recalculate concentration/TVL ceilings while keeping actual deposit headroom, scores and risk fixed. These four-slot combined fresh-ticket proposals omit incumbent feedback and changed fee bases; they are not capital-size engine backtests.", "2026")
    table(capital.groupby("Starting_capital").agg(Decisions=("Date", "size"), Mean_proposed_USD=("Proposed", "mean"), Mean_equity_fraction=("Proposal_equity_fraction", "mean"), Mean_names=("Names", "mean")).reset_index().rename(columns={"Starting_capital": "Starting capital (USD)"}))
    fig, ax = plt.subplots(figsize=(10, 4.7))
    ax.plot(s.Date, s.Residual / 1000, label="Source target residual", color="grey")
    for utility in ("risk", "combined", "normalised combined"):
        x = f[f.Slots.eq("4") & f.Utility.eq(utility)]
        ax.plot(x.Date, x.Proposed / 1000, label=utility)
    ax.set(ylabel="Gross additional proposal ($ thousands)", title="C00 opportunity and four-slot ticket amounts\n" + LABELS["2026"])
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    figure(data, fig, "2026-c00-opportunity", "Where extra allocation can activate", "These alternatives share C00 account state rather than their own compounding. Score multipliers can change dollar amounts while caps/cleanup remove differences. No additional holdings execute in this diagnostic replay.", "2026")
    heading("Gap-aware risk sensitivity on common C00 states", "Regular daily-simple risk drives trading; max(regular,gap) is only a diagnostic. Sparse observation jumps can imply higher risk than carried daily marks. These are exposure-weighted ex-ante volatility proxies, not covariance forecasts. Brake columns scale common proposals to remaining NB18-style k=0.75/1 risk allowances, using a strictly lagged 90-day C00 anchor with at least 30 decisions and earlier full-history warmup; this is a sizing diagnostic, not the full NB18 trading policy.", "2026")
    table(f[f.Slots.eq("4")].groupby("Utility").agg(Mean_regular_risk=("Ex_ante_risk", "mean"), Mean_gap_risk=("Gap_ex_ante_risk", "mean"), Mean_proposed_USD=("Proposed", "mean"), NB18_k075_USD=("Brake_75_proposed", "mean"), NB18_k100_USD=("Brake_100_proposed", "mean")).reset_index())
    return f, s


def resize_diagnostics(data, runs):
    """Separate requested, executed and band-suppressed additional changes."""
    rows = []
    for arm in ("RS00", "RS01", "NRS00"):
        r = runs[("2026", arm)]
        f = r["allocation_df"]
        extra = f[f.Role.eq("additional")].copy()
        extra["Change"] = extra["Final target (USD)"] - extra["Old value (USD)"]
        signed = {}
        for tr in r["result"].state.portfolio.get_all_trades():
            if tr.is_success():
                signed[(pd.Timestamp(tr.executed_at), int(tr.pair.internal_id))] = signed.get((pd.Timestamp(tr.executed_at), int(tr.pair.internal_id)), 0) + float(tr.executed_reserve) * (1 if tr.is_buy() else -1)
        ex = np.array([signed.get((pd.Timestamp(t), int(i)), 0) for t, i in zip(extra.Date, extra["Pair id"])])
        change = extra.Change.to_numpy()
        up = change > 1e-6
        down = change < -1e-6
        rows.append(dict(Arm=arm, Requested_increases=int(up.sum()), Executed_increases=int((ex > 1e-6).sum()), Requested_reductions=int(down.sum()), Executed_reductions=int((ex < -1e-6).sum()), Suppressed_reductions=int((down & (ex >= -1e-6)).sum()), **{"Requested increase (USD)": change[up].sum(), "Requested reduction (USD)": -change[down].sum(), "Executed buy reserve (USD)": ex[ex > 0].sum(), "Executed sale reserve (USD)": -ex[ex < 0].sum()}))
    return pd.DataFrame(rows)


def incremental_equity(data, runs, period):
    """Show small account differences that the absolute equity scale conceals."""
    base = runs[(period, "C00")]["equity"]
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    for arm in ("E00", "R00", "RS00", "RS01", "NRS00", "RS08"):
        e = runs[(period, arm)]["equity"]
        aligned = pd.concat([base.rename("C00"), e.rename(arm)], axis=1).ffill()
        ax.plot(aligned.index, (aligned[arm] - aligned.C00) / 1000, label=arm, lw=1.5)
    ax.axhline(0, color="black", lw=0.8)
    ax.set(ylabel="Equity difference vs C00 ($ thousands)", title="Incremental account equity: construction contrasts\n" + LABELS[period])
    ax.grid(alpha=0.2)
    ax.legend(ncol=3, fontsize=9)
    figure(data, fig, period + "-incremental-equity", "Incremental equity paths", "Subtracts the independent common-valuation C00 account. The expanded scale reveals small leads hidden in the absolute equity curves. Differences include core feedback and compounding, not only extra-role profits.", period)
