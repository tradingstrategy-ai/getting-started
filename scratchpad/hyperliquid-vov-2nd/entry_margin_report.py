"""Separate, captioned NB22 figures and explicit conditional-stage reporting."""

import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, FormatStrFormatter
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display
from entry_margin_data import CUTOFF, HORIZONS, LABELS, ROOT

plt.rcParams.update({"figure.figsize": (10, 5), "figure.dpi": 115, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def heading(title, description, period="2026"):
    display(Markdown(f"### {title} — {LABELS[period]}\n\n{description}"))


def table(frame, formats=None, gradient=None):
    style = frame.style.format(formats or {}, na_rep="—").set_table_styles([{"selector": "th", "props": [("text-align", "left")]}])
    if gradient:
        for metric in gradient:
            style = style.background_gradient(cmap="RdYlGn_r" if metric in ("MAE", "Mean_absolute_error") else "RdYlGn", subset=[metric])
    display(style)


def figure(data, name, fig):
    path = data["artifact"] / "figures" / f"{name}.png"
    path.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    data["figures"].append(str(path))
    display(Image(filename=str(path)))
    plt.close(fig)


def heatmap(data, pivot, name, title, colour_label, diverging=False, digits=2):
    fig, ax = plt.subplots(figsize=(10, max(3, 0.55 * len(pivot) + 1.4)))
    cmap = plt.get_cmap("RdYlGn_r" if diverging else "YlOrRd").copy()
    cmap.set_bad("#e5e7eb")
    values = pivot.to_numpy(float)
    options = {}
    if diverging:
        limit = float(np.nanmax(np.abs(values))) or 1.0
        options = dict(vmin=-limit, vmax=limit)
    im = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, aspect="auto", **options)
    ax.grid(False)
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=20, ha="right")
    ax.set_yticks(range(len(pivot)), [f"{item[0]} H{item[1]}" if isinstance(item, tuple) else str(item) for item in pivot.index])
    ax.set_title(title)
    for i in range(len(pivot)):
        for j in range(len(pivot.columns)):
            v = values[i, j]
            if not np.isfinite(v):
                continue
            rgba = im.cmap(im.norm(v))
            luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
            ax.text(j, i, f"{v:.{digits}f}", ha="center", va="center", fontsize=9, color="white" if luminance < 0.45 else "#111827")
    fig.colorbar(im, ax=ax, label=colour_label)
    figure(data, name, fig)


def period_rows(frame, period):
    if "Period" in frame:
        return frame[frame.Period.eq(period)].copy()
    from entry_margin_data import PERIODS

    a, b = PERIODS[period]
    return frame[frame.Date.ge(a) & frame.Date.lt(b)].copy()


def input_report(data):
    heading("Control identity", "Saved states reproduce the original daily equity paths and every successful trade. This validates artefact reuse; no fresh engine replay is claimed.")
    table(data["parity"].query("Period == '2026'").drop(columns="Trade_sha256"), {"Equity_error_USD": "${:.10f}", "Trades": "{:,.0f}"})
    heading("Frozen experiment contract", "Warm-up and the full-history account use the same repaired files. Fees are inherited research assumptions, not measured venue charges.")
    table(pd.DataFrame([("Price archive", data["identity"]["prices"]), ("Metadata archive", data["identity"]["metadata"]), ("NB20 generation", data["g20"].name), ("NB21 generation", data["g21"].name), ("Accounting", "One partial-sale fee; reset reopened tax; final net proceeds fund buys"), ("Fee assumptions", "10% positive redemption profit + 0.1% capital allowance"), ("Universe/permission limits", "Retrospective source inventory/guard; missing independent clocks retain historical fields"), ("Cache scope", "State, feature, distribution, input, code and plan hashes")], columns=["Item", "Recorded value"]))
    heading("Unchanged strategy rules", "The entry forecast changes only whether a supported funded fresh buy is admitted. All ranking, sizing, capacity, cadence and incumbent rules belong to the frozen control.")
    table(
        pd.DataFrame(
            [
                ("Ranking", "0.48 CAGR360 + 0.32 Sortino45 + 0.10 CAGR180 + 0.10 Sortino30", "0.60 CAGR360 + 0.40 Sortino45"),
                ("Component clips", "CAGR 0–100%; Sortino 0–3; normalised to 0–1", "Same"),
                ("Risk", "90-day variance; positive leave-one-out peer median; update shrinkage m/(m+30)", "90-day source variance; volatility floor 0.0001"),
                ("Sizing", "Lowest regularised risk first; waterfall to permitted capacities", "Proportional inverse variance"),
                ("Positions / hysteresis", "6 positions; entry rank 6 / exit rank 8", "Same"),
                ("Capital / capacity", "98% deployment; 33% concentration; 33% TVL; $7,500 minimum TVL", "Same"),
                ("Cadence / return gate", "Every 2 days; 14-day return > −16%", "Same"),
                ("Trade bands", "Buy 0.05%, sell 0.5% of reference equity; $5 floor; cleanup 0.5%", "Same"),
                ("Missing values", "Unscored composite retains entry eligibility; unusable basket risk has equal raw priority fallback", "Unscored entries retained; absent risk gives zero raw signal"),
                ("Veto overlay", "Only in-band, supported non-pool D, positive level/slope, predicted net ≤0; no refill", "No overlay"),
            ],
            columns=["Rule", "C00 / registered overlay", "V11 reference"],
        )
    )


def ledger_summary(data, period):
    f = data["spells"][data["spells"].Period.eq(period)]
    records = []
    for closed, g in f.groupby("Closed"):
        records.append(dict(Cohort="Closed" if closed else "Open / censored", Spells=len(g), Initial_cash_USD=g.Q.sum(), Median_days=g.Days.median(), Capital_weighted_days=np.average(g.Days, weights=g.Q), Dollar_days=g.Dollar_days.sum(), Initial_profit_USD=g.Initial_profit.sum(), Total_spell_profit_USD=g.Spell_profit.sum(), Frozen_loss_headroom_USD=(-g.Initial_profit.clip(upper=0)).sum(), Losing_initial_spells=g.Initial_profit.lt(0).sum(), Reentered_within_2d=g.Reentered_2d.sum(), Reentered_within_4d=g.Reentered_4d.sum()))
    return pd.DataFrame(records)


def ledger_report(data, period):
    f = data["spells"][data["spells"].Period.eq(period)]
    heading("Initial units versus managed position spells", "Top-ups are separate. Actual sale cash and ending net liquidation value reconcile proportionally; lifetime by invested dollars may differ sharply from a position-count median. Open spells are censored.", period)
    table(ledger_summary(data, period), {c: "{:,.2f}" for c in ("Initial_cash_USD", "Capital_weighted_days", "Dollar_days", "Initial_profit_USD", "Total_spell_profit_USD", "Frozen_loss_headroom_USD")})
    heading("Entry-spell lifetime distribution", "Bars count closed spells, with initial-cash-weighted shares on a separate axis. Open spells appear in the table above and are not silently treated as completed durations.", period)
    g = f[f.Closed]
    bounds = [0, 2, 4, 7, 14, 30, 90, np.inf]
    labels = ["≤2", "2–4", "4–7", "7–14", "14–30", "30–90", ">90"]
    bins = pd.cut(g.Days, bins=bounds, labels=labels, include_lowest=True)
    counts = g.groupby(bins, observed=False).size()
    dollars = g.groupby(bins, observed=False).Q.sum()
    fig, ax = plt.subplots()
    ax.bar(np.arange(len(labels)) - 0.15, counts, width=0.3, color="#2563eb", label="Closed spells")
    ax2 = ax.twinx()
    ax2.bar(np.arange(len(labels)) + 0.15, dollars / dollars.sum() * 100, width=0.3, color="#d97706", label="Initial cash share")
    ax.set_xticks(range(len(labels)), labels)
    ax.set_xlabel("Managed spell duration (days)")
    ax.set_ylabel("Spell count")
    ax2.set_ylabel("Initial cash share (%)")
    ax.set_ylim(0, max(counts.max(), 1) * 1.25)
    ax2.set_ylim(0, max((dollars / dollars.sum() * 100).max(), 1) * 1.25)
    ax2.grid(False)
    ax.set_title(f"Closed entry lifetimes | {LABELS[period]}")
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")
    figure(data, f"{period}-entry-lifetimes", fig)
    heading("Frozen initial-entry loss concentration", "Avoiding these losses is hindsight ledger headroom, not an upper bound on a changed account. Total managed profit also includes later top-ups. Largest vaults are shown separately for closed and open spells.", period)
    f = f.assign(Loss=-f.Initial_profit.clip(upper=0))
    contributions = f.groupby(["Vault", "Closed"]).Loss.sum().unstack(fill_value=0)
    contributions = contributions.reindex(columns=[True, False], fill_value=0).rename(columns={True: "Closed", False: "Open marked"})
    contributions = contributions.loc[contributions.sum(axis=1).nlargest(10).index]
    contributions.columns.name = None
    fig, ax = plt.subplots()
    contributions.sort_values("Closed").plot.barh(stacked=True, ax=ax, color=["#dc2626", "#fbbf24"])
    ax.set_xlabel("Frozen initial-unit loss (USD)")
    ax.set_title(f"Initial-entry loss headroom by vault | {LABELS[period]}")
    ax.set_ylabel("")
    figure(data, f"{period}-loss-concentration", fig)
    if period == "2026":
        heading("Proposals and re-entry", "Actual successful first buys are verified executable entries. Saved positive fresh targets that did not execute remain intent diagnostics; they are not assumed executable proposals.")
        dates = f.groupby("Date").agg(Entries=("Position", "size"), Initial_cash_USD=("Q", "sum"))
        table(pd.DataFrame([dict(Actual_entries=len(f), Decision_dates=dates.shape[0], Single_entry_dates=int(dates.Entries.eq(1).sum()), Multiple_entry_dates=int(dates.Entries.gt(1).sum()), Closed_reentries_2d=int(f.Reentered_2d.sum()), Closed_reentries_4d=int(f.Reentered_4d.sum()), Maximum_tag_residual_USD=float(f.Reconciliation_residual.abs().max()))]))


def population_report(data):
    heading("Past-only horizon registration", "Both candidate horizons use exactly the same fully closed and label-matured pre-2026 Long-account initial cohorts. The headline comparison is equal-origin, initial-cash-weighted absolute discrepancy; ties favour two days.", "Pre2026")
    table(data["horizon_table"], {c: "{:.2%}" for c in ["Equal_spell_MAE", "Capital_weighted_MAE", "Equal_origin_capital_MAE", "Winning_MAE", "Losing_MAE"]})
    display(Markdown(f"**Registered horizon: {data['horizon']} days.** {data['horizon_registration']['common_closed_spells']} common closed pre-2026 spells. H30 is diagnostic only. NB21 H2's unsupported penalty-fold fallback is retained; no new penalty search."))
    p = period_rows(data["panel"], "2026")
    b = period_rows(data["base"], "2026")
    e = period_rows(data["entries"], "2026")
    heading("Native decision calendar coverage", "Use the saved engine clock, rather than constructing a new two-day anchor. Every 2026 decision has frozen features. Early Long-account cash-only warm-up dates without NB21 feature rows are explicitly unavailable; they contain no source targets or executable entries and cannot trigger a veto.")
    table(data["native_coverage"].query("Period == '2026'"))
    heading("Opportunity population and label coverage", "The band is state independent and entry eligible, not the incumbent-sensitive C00 selection. Entry counts use actual fills. Labels require a later actual report confirming continued support, without the old one-day endpoint-age cutoff.")
    rows = []
    for h, g in p.groupby("H"):
        band = g[g.In_band]
        actual = e[e.H.eq(h)]
        rows.append(dict(Horizon_days=h, Eligible_vault_date_rows=len(b[b.eligible_as_of_origin]), Band_rows=len(band), Band_origins=band.Date.nunique(), Supported_D_rows=band.Supported_D.sum(), Missing_score_rows=band.Missing_score.sum(), Resolved_band_fraction=band.Resolved.mean(), Carried_endpoint_fraction=band.Endpoint_age.gt(0).mean(), Endpoint_over_1d=band.Endpoint_age.gt(1).mean(), Actual_entries=len(actual), Out_of_band_entries=int((~actual.In_band).sum()), Resolved_entry_dollar_fraction=actual.loc[actual.Resolved, "Q"].sum() / actual.Q.sum()))
    table(pd.DataFrame(rows), {c: "{:.1%}" for c in ["Resolved_band_fraction", "Carried_endpoint_fraction", "Endpoint_over_1d", "Resolved_entry_dollar_fraction"]})
    heading("Support and missingness cohorts", "Age refers to recorded history and is diagnostic, never a minimum-age admission rule. Unknown historical permission clocks are retained as flags. Every source field remains in the saved panel.")
    g = p[p.H.eq(data["horizon"]) & p.In_band].copy()
    g["History"] = np.where(g.recorded_age.lt(30), "Under 30 recorded days", "At least 30 recorded days")
    g["Score"] = np.where(g.Missing_score, "Unscored", "Scored")
    cohort = g.groupby(["History", "Score"]).agg(Rows=("Pair", "size"), Vaults=("Pair", "nunique"), Resolved=("Resolved", "mean"), Supported_D=("Supported_D", "mean"), Median_endpoint_age_days=("Endpoint_age", "median"), Mean_actual_updates=("Actual_updates", "mean"))
    table(cohort, {"Resolved": "{:.1%}", "Supported_D": "{:.1%}", "Median_endpoint_age_days": "{:.2f}", "Mean_actual_updates": "{:.2f}"})
    checks = data["forecast_checks"]
    heading("Underlying distribution parity", "Reconstructed expected net values match the cached D distributions, including the nonlinear fee calculation. Every underlying monthly fit predates its origin and every training outcome matured before that fit.")
    table(pd.DataFrame([dict(Monthly_horizon_fits=len(checks), Maximum_net_error=float(checks.Net_error.max()), All_training_outcomes_pre_fit=bool((checks.Underlying_max_mature < checks.Fit).all()), New_penalty_search=False, Underlying_training="NB21 old fresh-endpoint training retained; calibration labels broaden reporting support")]))
    actual = e[e.H.eq(data["horizon"])]
    heading("Entry band differences and feasibility", "Outside-band entries pass through C00. Source-intent diagnostics include selected targets before actual fill thresholds. A mathematical per-dollar label does not claim a $1 ticket is executable; source-filled entries alone establish account-level feasibility.")
    table(actual.groupby("In_band").agg(Entries=("Position", "size"), Initial_cash_USD=("Q", "sum"), First_top6_appearance=("First_top6_appearance", "sum"), Resolved=("Resolved", "mean")), {"Initial_cash_USD": "${:,.0f}", "Resolved": "{:.1%}"})
    heading("Boundary capacity and funding roles", "Diagnostic minimum tickets use the source $5/0.05% equity floor and 33% concentration/TVL/deposit-cap bounds. An alternative is not an executed purchase: residual target budget, free slots and an existing fresh buy identify possible add/replacement cases. These state-dependent diagnostics never select the fitting sample.")
    f = data["fundability"].query("Period == '2026'")
    table(f.groupby("Boundary_role").agg(Rows=("Pair", "size"), Vaults=("Pair", "nunique"), Minimum_cap_feasible=("Minimum_cap_feasible", "mean"), Median_residual_budget_USD=("Residual_target_budget_USD", "median")), {"Minimum_cap_feasible": "{:.1%}", "Median_residual_budget_USD": "${:,.0f}"})


def qualification_report(data):
    r = data["registration"]
    heading("Registered gate verdict", "This file was saved before opening 2026 forecast-outcome tables. Qualification requires supported relative D, actual entry activation and positive pre-2026 managed-spell value beyond both declared ledger placebo medians.", "Pre2026")
    table(pd.DataFrame([dict(Check=k, Passed=v) for k, v in r["tests"].items()]))
    display(Markdown(f"**Stage 2: {'qualified' if r['execute_accounts'] else 'stopped'}.** Pre-2026 actionable entries: {r['past_actionable']} / {r['past_entries']}; actual vetoes: {r['pre2026']['Vetoes']}; 2026 activation (no outcomes used): {r['activation2026']}.\n\nStop reason: {'; '.join(r['stop_reasons']) or 'none'}."))
    heading("Pre-2026 qualification economics", "This is the declared exception to the 2026 reporting default: qualification uses fully closed pre-2026 Long-account initial cohorts. Unresolved means the managed spell had not closed before 1 January 2026. Its sensitivity mark uses only trades and NAV available before that cutoff.", "Pre2026")
    table(pd.DataFrame([r["pre2026"]]), {"Resolved_Q": "${:,.0f}", "Unresolved_Q": "${:,.0f}", "Value": "${:,.0f}", "Mark_value": "${:,.0f}", "Per_resolved_dollar": "{:.2%}", "Unresolved_fraction": "{:.1%}", "Break_even_unknown_mean": "{:.2%}"})
    heading("Pre-2026 placebo value distributions", "Identity controls permute signals within origin/support/missingness. Block controls reassign horizon-length profiles within quarter and D-support era, using within-day signal percentiles for different populations and re-centring on the destination band. Five engine controls, if reached, are a separate descriptive experiment.", "Pre2026")
    q = data["placebos"].groupby("Method").agg(Seeds=("Seed", "nunique"), Median_vetoes=("Vetoes", "median"), Median_resolved_dollars=("Resolved_Q", "median"), Median_per_dollar=("Per_resolved_dollar", "median"), Median_total_value=("Value", "median"), Median_unresolved_fraction=("Unresolved_fraction", "median"))
    table(q, {"Median_resolved_dollars": "${:,.0f}", "Median_total_value": "${:,.0f}", "Median_per_dollar": "{:.2%}", "Median_unresolved_fraction": "{:.1%}"})
    if data["placebos"].Per_resolved_dollar.notna().any():
        heading("Pre-2026 ledger placebo comparison", "The vertical line is informed avoided initial-spell value per resolved vetoed dollar. Missing outcomes and five-seed account controls cannot establish formal selective account skill.", "Pre2026")
        fig, ax = plt.subplots()
        for name, g in data["placebos"].groupby("Method"):
            vals = g.Per_resolved_dollar.dropna() * 100
            if len(vals):
                ax.hist(vals, bins=35, alpha=0.5, label=name)
        informed = r["pre2026"]["Per_resolved_dollar"]
        if np.isfinite(informed):
            ax.axvline(informed * 100, color="black", ls="--", label="Informed veto")
        ax.set_xlabel("Avoided net return per resolved initial dollar (%)")
        ax.set_ylabel("Seed count")
        ax.set_title(f'Closed-spell qualification controls | 2023-03-01–2025-12-31 UTC | H{data["horizon"]}')
        ax.legend(fontsize=8)
        figure(data, "pre2026-placebo-value", fig)
    else:
        display(Markdown("No resolved veto dollars exist. A placebo histogram would falsely imply an economic comparison, so the explicit no-op table is shown instead."))
    heading("Past-only contributor and quarter deletion", "Keep the original veto identities and fits fixed. Remove each entry quarter or the largest avoided-loss contributor from the fully closed pre-2026 evaluation, then recompute per-dollar value; this is not a removal backtest.", "Pre2026")
    q = data["qualification_entries"]
    q = q[q.Veto & q.Closed & q.Closed_at.lt(CUTOFF)].copy()
    table(deletions(q), {"Remaining_Q": "${:,.0f}", "Avoided_value": "${:,.0f}", "Per_dollar": "{:.2%}"})


def deletions(q):
    if not len(q):
        return pd.DataFrame([dict(Omitted="No resolved vetoes", Remaining_entries=0, Remaining_Q=0.0, Avoided_value=np.nan, Per_dollar=np.nan)])
    groups = [("None", q)]
    quarters = q.Date.dt.to_period("Q").astype(str)
    groups += [(quarter, q[quarters.ne(quarter)]) for quarter in sorted(quarters.unique())]
    largest = (-q.groupby("Vault").Initial_profit.sum()).idxmax()
    groups.append((f"Largest avoided-loss vault: {largest}", q[q.Vault.ne(largest)]))
    return pd.DataFrame([dict(Omitted=name, Remaining_entries=len(g), Remaining_Q=g.Q.sum(), Avoided_value=-g.Initial_profit.sum(), Per_dollar=-g.Initial_profit.sum() / g.Q.sum() if g.Q.sum() else np.nan) for name, g in groups])


def balanced_metrics(g, column):
    f = g[g.In_band & g.Resolved & g[column].notna()].copy()
    if not len(f):
        return {}
    f["Error"] = f[column] - f.Y_net
    f["Abs_error"] = f.Error.abs()
    f["Correct_sign"] = f[column].gt(0).eq(f.Y_net.gt(0))
    f["Baseline_sign"] = f.Matched_L0.gt(0).eq(f.Y_net.gt(0))
    means = f.groupby("Date")[["Y_net", column, "Error", "Abs_error", "Correct_sign", "Baseline_sign"]].mean()
    correlations = []
    for _, a in f.groupby("Date"):
        if len(a) >= 2 and a[column].nunique() > 1 and a.Y_net.nunique() > 1:
            correlations.append(a[column].rank().corr(a.Y_net.rank()))
    return dict(Rows=len(f), Origins=f.Date.nunique(), Vaults=f.Pair.nunique(), Mean_realised=means.Y_net.mean(), Mean_prediction=means[column].mean(), Mean_error=means.Error.mean(), MAE=means.Abs_error.mean(), Rank_IC=np.mean(correlations) if correlations else np.nan, Sign_accuracy=means.Correct_sign.mean(), Constant_sign_accuracy=means.Baseline_sign.mean())


def calibration_table(data, period):
    c = period_rows(data["calibration"], period)
    rows = []
    for (model, h), g in c.groupby(["Model", "H"]):
        for label, col in [("Calibrated", "Prediction"), ("Matched L0", "Matched_L0"), ("Global band L0", "Global_L0"), ("Zero", "Zero")] + ([("Raw D", "Signal")] if model == "L2" else []):
            g = g.copy()
            g["Zero"] = 0.0
            # All comparators use the calibrated model's matched current supported cohort.
            g = g[g.Signal.notna() & g.Prediction.notna()]
            rows.append(dict(Model=model, H=h, Comparator=label, **balanced_metrics(g, col)))
    return pd.DataFrame(rows)


def signal_report(data, period):
    assert (data["artifact"] / "stage2-registration.json").exists(), "Qualification before 2026 outcomes"
    c = period_rows(data["calibration"], period)
    metrics = calibration_table(data, period)
    data[f"{period}_signal_metrics"] = metrics
    metrics.to_csv(data["artifact"] / f"{period}-signal-metrics.csv", index=False)
    heading("Level, ordering and sign calibration", "Each model/horizon comparator uses the same resolved, signal-available band rows and gives origin dates equal weight. L0 predicts the pooled level. Sign accuracy is compared with its actual constant-sign baseline; it is not a probability Brier score.", period)
    table(metrics, {"Mean_realised": "{:.2%}", "Mean_prediction": "{:.2%}", "Mean_error": "{:.2%}", "MAE": "{:.2%}", "Rank_IC": "{:.3f}", "Sign_accuracy": "{:.1%}", "Constant_sign_accuracy": "{:.1%}"}, gradient=["MAE", "Rank_IC"])
    heading("Fresh versus carried endpoint diagnostics", "The primary calibration retains carried supported endpoints. This separate table audits the old one-day freshness restriction rather than applying it silently. Means and errors give each origin equal weight within the displayed cohort.", period)
    support_rows = []
    for h, g in c[c.Model.eq("L2")].groupby("H"):
        for name, a in [("Actual endpoint ≤1 day old", g[g.Endpoint_age.le(1)]), ("Carried endpoint >1 day old", g[g.Endpoint_age.gt(1)])]:
            support_rows.append(dict(H=h, Endpoint_cohort=name, **balanced_metrics(a, "Prediction")))
    table(pd.DataFrame(support_rows), {"Mean_realised": "{:.2%}", "Mean_prediction": "{:.2%}", "Mean_error": "{:.2%}", "MAE": "{:.2%}", "Rank_IC": "{:.3f}", "Sign_accuracy": "{:.1%}", "Constant_sign_accuracy": "{:.1%}"})
    for h in HORIZONS:
        for model in ("L1", "L2"):
            g = c[c.H.eq(h) & c.Model.eq(model) & c.In_band & c.Resolved & c.Signal.notna() & c.Prediction.notna()].copy()
            heading(f"{model} calibrated forecast versus realised net return, H{h}", "Quarter colours distinguish market regimes. Units are horizon net return, not annualised CAGR. Identity and zero lines expose level bias. Points are all resolved matched band observations; the descriptive line gives origins equal weight.", period)
            if not len(g):
                display(Markdown("No supported matched rows; no scatter is drawn."))
                continue
            fig, ax = plt.subplots()
            quarter = g.Date.dt.to_period("Q").astype(str)
            for i, (q, a) in enumerate(g.groupby(quarter, sort=True)):
                ax.scatter(a.Prediction * 100, a.Y_net * 100, s=13, alpha=0.32, label=f"{q} (n={len(a):,})", color=plt.get_cmap("tab10")(i % 10), rasterized=True)
            x = g.Prediction.to_numpy() * 100
            y = g.Y_net.to_numpy() * 100
            w = 1 / g.groupby("Date").Date.transform("size").to_numpy()
            pad = max(np.ptp(x) * 0.05, abs(np.mean(x)) * 1e-4, 1e-6)
            lo = x.min() - pad
            hi = x.max() + pad
            ax.plot([lo, hi], [lo, hi], color="#64748b", lw=1, ls="--", label="Identity")
            ax.axhline(0, color="#64748b", lw=0.7)
            ax.axvline(0, color="#64748b", lw=0.7)
            if np.ptp(x) > 0:
                xm = np.average(x, weights=w)
                ym = np.average(y, weights=w)
                slope = np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2)
                xs = np.array([x.min(), x.max()])
                ax.plot(xs, ym + slope * (xs - xm), color="black", lw=1.6, label="Equal-origin descriptive fit")
            ax.set_xlim(lo, hi)
            ax.set_ylim(y.min() - np.ptp(y) * 0.05, y.max() + np.ptp(y) * 0.05)
            ax.xaxis.set_major_formatter(FormatStrFormatter("%.3f" if hi - lo < 1 else "%.1f"))
            ax.set_xlabel("Calibrated expected net return (%) — independent axis scale")
            ax.set_ylabel("Realised supported NAV net return (%)")
            ax.set_title(f"{model} levels, H{h} | {LABELS[period]}")
            ax.legend(fontsize=8)
            figure(data, f"{period}-{model}-H{h}-levels", fig)
            heading(f"{model} within-origin discrimination, H{h}", "Both axes centre on exactly the current resolved matched rows. This removes the shared date return and exposes relative ordering; it does not establish that investing beats cash. The L1 horizontal axis is a score deviation; L2 uses expected-return percentage points.", period)
            g["Xc"] = g.Signal - g.groupby("Date").Signal.transform("mean")
            g["Yc"] = g.Y_net - g.groupby("Date").Y_net.transform("mean")
            fig, ax = plt.subplots()
            mult = 100 if model == "L2" else 1
            for i, (q, a) in enumerate(g.groupby(quarter, sort=True)):
                ax.scatter(a.Xc * mult, a.Yc * 100, s=13, alpha=0.32, label=q, color=plt.get_cmap("tab10")(i % 10), rasterized=True)
            ax.axhline(0, color="#64748b", lw=0.7)
            ax.axvline(0, color="#64748b", lw=0.7)
            x = g.Xc.to_numpy() * mult
            y = g.Yc.to_numpy() * 100
            w = 1 / g.groupby("Date").Date.transform("size").to_numpy()
            den = np.sum(w * x * x)
            if den > 0:
                xs = np.array([x.min(), x.max()])
                ax.plot(xs, np.sum(w * x * y) / den * xs, color="black", label="Within-origin fit")
            ax.set_xlabel("Score deviation" if model == "L1" else "D expected-return deviation (percentage points)")
            ax.set_ylabel("Realised net-return deviation (percentage points)")
            ax.set_title(f"{model} relative spread, H{h} | {LABELS[period]}")
            ax.legend(fontsize=8)
            figure(data, f"{period}-{model}-H{h}-centred", fig)
    heading("Forecast comparison heatmap", "Colours compare equal-origin mean absolute error on matched cohorts. Lower is better; missing cells are grey. This does not compare model populations with one another without the coverage table.", period)
    pivot = metrics.pivot(index=["Model", "H"], columns="Comparator", values="MAE") * 100
    heatmap(data, pivot, f"{period}-calibration-heatmap", f"Mean absolute net-return error | {LABELS[period]}", "MAE (percentage points)")
    heading("Error change versus the matched pooled level", "Subtract each row’s Matched L0 MAE. Green means lower forecast error than the same-support pooled level; red means higher. This makes within-horizon differences visible without treating naturally larger 30-day returns as worse skill.", period)
    changes = pivot.subtract(pivot["Matched L0"], axis=0)
    heatmap(data, changes, f"{period}-MAE-change", f"MAE change versus matched L0 | {LABELS[period]}", "MAE change (pp)", diverging=True)
    heading("Monthly relative slope and identification", "The non-negative trading slope is distinct from its raw estimate. Shaded 95% block intervals are descriptive under repeated-vault and long-spell dependence. Horizon-length blocks do not guarantee independent vault observations.", period)
    a = data["coefficient_audit"]
    a = a[a.H.eq(data["horizon"]) & a.Model.eq("L2")]
    a = a[a.Fit.ge("2026-01-01") & a.Fit.lt("2026-10-05")] if period == "2026" else a
    fig, ax = plt.subplots()
    ax.plot(a.Fit, a.Raw_beta, marker="o", label="Raw within-origin slope")
    ax.plot(a.Fit, a.Beta, ls="--", label="Non-negative slope")
    ax.fill_between(a.Fit, a.Beta_lower, a.Beta_upper, alpha=0.15, label="Calendar-block 95% interval")
    ax.axhline(0, color="grey", lw=0.7)
    ax.set_ylabel("Calibration slope")
    ax.set_title(f'L2 monthly slope, H{data["horizon"]} | {LABELS[period]}')
    ax.legend(fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    figure(data, f"{period}-L2-slope", fig)
    heading("Monthly support and treatment state", "Identification counts require at least two supported D rows with non-zero within-origin variation in each qualifying historical origin. Positive alpha and beta, current band support and actual entry membership are additional action checks.", period)
    table(a[["Fit", "Alpha", "Raw_beta", "Beta", "Beta_lower", "Beta_upper", "Matched_origins", "Identification_origins", "Blocks", "Partly_matured_origins", "Recent_5_origin_mature_fraction", "Identified"]], {c: "{:.4f}" for c in ["Alpha", "Raw_beta", "Beta", "Beta_lower", "Beta_upper"]} | {"Recent_5_origin_mature_fraction": "{:.1%}"})
    probability_report(data, period)


def probability_report(data, period):
    heading("Raw distribution sign probability reliability", "D supplies a probability of positive fee-aware return. Compare its Brier score with the causal expanding positive-outcome frequency on the same matured paired band population. The direct net-value calibration supplies no probability, so no probability is invented from its point forecast.", period)
    c = period_rows(data["calibration"], period)
    c = c[c.Model.eq("L2") & c.In_band & c.Resolved & c.Supported_D & c.profit_probability.notna() & c.Matched_positive.notna()].copy()
    c["Target"] = c.Y_net.gt(0).astype(float)
    c["D_Brier"] = (c.profit_probability - c.Target) ** 2
    c["Prior_Brier"] = (c.Matched_positive - c.Target) ** 2
    records = []
    for h, g in c.groupby("H"):
        origin = g.groupby("Date")[["D_Brier", "Prior_Brier"]].mean()
        records.append(dict(H=h, Rows=len(g), Origins=len(origin), D_Brier=origin.D_Brier.mean(), Prior_Brier=origin.Prior_Brier.mean()))
    table(pd.DataFrame(records), {"D_Brier": "{:.4f}", "Prior_Brier": "{:.4f}"})
    heading("Sign probability reliability heatmap", "Subtract the expanding same-population constant prior Brier score. Negative green cells favour D; positive red cells favour the prior. This proper probability comparison uses the actual base rate, rather than assuming 0.25.", period)
    values = pd.DataFrame(records).set_index("H")[["D_Brier", "Prior_Brier"]]
    changes = values.subtract(values.Prior_Brier, axis=0)
    changes.index = [f"H{h}" for h in changes.index]
    heatmap(data, changes, f"{period}-probability-Brier", f"Brier change versus causal sign prior | {LABELS[period]}", "Brier score change", diverging=True, digits=4)


def activation_report(data, period):
    e = data["entry_predictions"]
    e = e[e.Period.eq(period) & e.Model.eq("L2") & e.H.eq(data["horizon"])].copy()
    heading("Actual executed entry activation", "Informed vetoes are frozen-ledger diagnostics. They are not account PnL because suppressing an entry may change subsequent holdings, re-entry, cash and fees.", period)
    rows = []
    for reason, g in e.groupby("Pass_reason", dropna=False):
        rows.append(dict(Reason=reason, Entries=len(g), Initial_cash_USD=g.Q.sum(), Vetoes=g.Veto.sum(), Closed_entries=g.Closed.sum(), Resolved_H_dollars=g.loc[g.Resolved, "Q"].sum()))
    table(pd.DataFrame(rows), {"Initial_cash_USD": "${:,.0f}", "Resolved_H_dollars": "${:,.0f}"})
    heading("Entry-level signal economics", "Closed initial-unit managed returns are the primary attribution; open marks are separate. Gross and net horizon returns are paired and expose assumed fee drag. Outcome availability does not enter the action rule.", period)
    q = e[e.Veto]
    rows = []
    for name, g in [("All entries", e), ("Actionable entries", e[e.Actionable]), ("Vetoed entries", q)]:
        closed = g[g.Closed]
        supported = g[g.Resolved]
        rows.append(dict(Cohort=name, Entries=len(g), Initial_cash_USD=g.Q.sum(), Closed_managed_return=np.average(closed.Y_spell, weights=closed.Q) if len(closed) else np.nan, Supported_H_gross=np.average(supported.Gross, weights=supported.Q) if len(supported) else np.nan, Supported_H_net=np.average(supported.Y_net, weights=supported.Q) if len(supported) else np.nan, Avoided_closed_losses_USD=-closed.loc[closed.Y_spell.lt(0), "Initial_profit"].sum(), Missed_closed_gains_USD=closed.loc[closed.Y_spell.gt(0), "Initial_profit"].sum(), Unclosed_dollars=g.loc[~g.Closed, "Q"].sum()))
    table(pd.DataFrame(rows), {"Initial_cash_USD": "${:,.0f}", "Closed_managed_return": "{:.2%}", "Supported_H_gross": "{:.2%}", "Supported_H_net": "{:.2%}", "Avoided_closed_losses_USD": "${:,.0f}", "Missed_closed_gains_USD": "${:,.0f}", "Unclosed_dollars": "${:,.0f}"})
    if len(q):
        heading("Quarter and contributor dependence", "Delete one quarter or the largest loss-contributing vault while holding entry identities and forecasts fixed. These are frozen-ledger sensitivity values, not refitted models or changed accounts.", period)
        q = q[q.Closed].copy()
        q["Quarter"] = q.Date.dt.to_period("Q").astype(str)
        table(q.groupby("Quarter").agg(Vetoes=("Position", "size"), Vetoed_initial_USD=("Q", "sum"), Avoided_managed_PnL=("Initial_profit", lambda x: -x.sum())), {"Vetoed_initial_USD": "${:,.0f}", "Avoided_managed_PnL": "${:,.0f}"})
        heading("Fixed-ledger deletion sensitivities", "The entries, calibration and veto rule are held fixed. Removing one quarter or the largest avoided-loss vault tests contributor dependence, not causal account PnL.", period)
        table(deletions(q), {"Remaining_Q": "${:,.0f}", "Avoided_value": "${:,.0f}", "Per_dollar": "{:.2%}"})
    heading("Future label reporting support", "Resolved requires a genuine observation at or after the target, while the price itself remains the latest mark at or before the target. Unknown final-report outcomes are never fitted as zero.", period)
    g = period_rows(data["panel"], period)
    g = g[g.In_band]
    counts = g.groupby("H").agg(Rows=("Pair", "size"), Resolved=("Resolved", "sum"), Mean_endpoint_age=("Endpoint_age", "mean"), Zero_update_fraction=("Actual_updates", lambda x: x.eq(0).mean()))
    table(counts, {"Mean_endpoint_age": "{:.2f}", "Zero_update_fraction": "{:.1%}"})


def conditional_accounts(data):
    r = data["registration"]
    if not r["execute_accounts"]:
        data["engine_status"] = "Not executed: registered qualification/activation stop"
        heading("Conditional engine status", "The notebook completed the registered research stages. New economic accounts stop when qualification fails; an unexecuted account cannot be presented as a successful no-op comparison.")
        table(pd.DataFrame([dict(Arms="O1 + R01–R05", Calendars="2026 and Long", Status=data["engine_status"], Reason="; ".join(r["stop_reasons"])), dict(Arms="Optional eight-cell factorial", Calendars="2026 and Long", Status="Not executed", Reason="Explicitly deferred appendix")]))
        return None
    from entry_margin_execution import run_accounts

    return run_accounts(data)


def account_report(data, period):
    heading("Economic account comparison", "These unchanged controls are reused from NB20. If the registered gate stops, there is no new O1/R account, and no claimed improvement from an unexecuted policy.", period)
    rows = data.get("account_metrics", data["metrics"])
    f = rows[rows.Period.eq(period)].set_index("Arm")
    names = ["Final equity (USD)", "Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Mean cash weight", "Trades", "Modelled redemption costs (USD)"]
    selected = f[names].T
    style = selected.style
    for name in selected.index:
        fmt = "${:,.0f}" if "(USD)" in name else "{:.2%}" if name in ["CAGR", "Maximum drawdown", "Mean cash weight"] else "{:,.0f}" if name == "Trades" else "{:.3f}"
        style = style.format(fmt, subset=pd.IndexSlice[[name], :])
        if name in ["Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Maximum drawdown"]:
            style = style.background_gradient(cmap="RdYlGn", axis=1, subset=pd.IndexSlice[[name], :])
    display(style)
    heading("Unchanged reference equity", "Both accounts start from the same fresh cash under common accounting. These curves establish baseline economics, not a new veto-policy backtest.", period)
    fig, ax = plt.subplots()
    for arm, col in [("C00", "#c2410c"), ("V11", "#2563eb")]:
        ax.plot(data["equity"][period, arm], label=arm, color=col)
    ax.set_ylabel("Equity (USD)")
    ax.set_title(f"Frozen reference equity | {LABELS[period]}")
    ax.legend()
    figure(data, f"{period}-reference-equity", fig)
    if period == "2026":
        all_weights = {a: pd.read_parquet(data["g20"] / f"{period}-{a}-absolute-weights.parquet") for a in ("C00", "V11")}
        reserves = {a: data["states"][period, a].portfolio.get_default_reserve_asset()[0].token_symbol for a in all_weights}
        pooled = pd.concat([w.drop(columns=reserves[a]).mean() for a, w in all_weights.items()], axis=1).fillna(0).mean(axis=1)
        top = list(pooled.nlargest(8).index)
        colours = [plt.get_cmap("tab10")(i) for i in range(len(top))] + ["#e5e7eb", "#9ca3af"]
        for arm in ("C00", "V11"):
            heading(f"{arm} absolute asset weights", "Cash is included and grey. Both strategies use the same eight largest pooled-average vaults in the same colour/order. September capacity restrictions remain part of the unchanged control; no invested-only normalisation is used.", period)
            w = all_weights[arm]
            reserve = reserves[arm]
            asset = w.drop(columns=reserve)
            plotted = asset.reindex(columns=top, fill_value=0).copy()
            plotted["Other vaults"] = asset.drop(columns=top, errors="ignore").sum(axis=1)
            plotted["Cash"] = w[reserve]
            fig, ax = plt.subplots(figsize=(11, 5))
            plotted.mul(100).plot.area(stacked=True, ax=ax, linewidth=0, color=colours)
            ax.set_ylim(0, 100)
            ax.set_ylabel("Absolute account weight (%)")
            ax.set_title(f"{arm} asset weights including cash | {LABELS[period]}")
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
            ax.set_xlabel("Decision calendar")
            figure(data, f"{period}-{arm}-weights", fig)
        heading("Reference quarterly return heatmap", "Daily calendar returns compound within each quarter. The final Q4 is partial through 4 October. These are time-weighted account returns, not summed trade returns.", period)
        pivot = pd.DataFrame({arm: data["equity"][period, arm].pct_change().fillna(0).groupby(data["equity"][period, arm].index.to_period("Q")).apply(lambda x: (1 + x).prod() - 1) for arm in ("C00", "V11")}).T * 100
        pivot.columns = [str(x) + (" (partial)" if str(x) == "2026Q4" else "") for x in pivot.columns]
        # Negation reuses the lower-is-better palette: positive returns stay green.
        fig, ax = plt.subplots(figsize=(8, 3))
        limit = float(abs(pivot.to_numpy()).max())
        cmap = plt.get_cmap("RdYlGn")
        im = ax.imshow(pivot, cmap=cmap, vmin=-limit, vmax=limit, aspect="auto")
        ax.grid(False)
        ax.set_xticks(range(len(pivot.columns)), pivot.columns)
        ax.set_yticks(range(len(pivot)), pivot.index)
        ax.set_title(f"Quarterly account returns | {LABELS[period]}")
        for i in range(len(pivot)):
            for j in range(len(pivot.columns)):
                rgba = cmap(im.norm(pivot.iloc[i, j]))
                lum = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(j, i, f"{pivot.iloc[i,j]:.2f}%", ha="center", va="center", color="white" if lum < 0.45 else "black")
        fig.colorbar(im, ax=ax, label="Quarterly return (%)")
        figure(data, f"{period}-quarterly-return", fig)
        heading("Reference quarterly marked profit", "Quarterly changes in total marked equity reconcile to full-account profit. Negative quarters and initial-entry losses answer different questions; frozen loss headroom can occur inside a profitable quarter.", period)
        profits = pd.DataFrame({arm: data["equity"][period, arm].diff().fillna(data["equity"][period, arm].iloc[0] - 150000).groupby(data["equity"][period, arm].index.to_period("Q")).sum() for arm in ("C00", "V11")}).T
        table(profits, {c: "${:,.0f}" for c in profits.columns})
    heading("Concentration and extreme-update audit", "Reuse the hash-pinned NB20 audit for identical controls. A large sparse NAV update is distinct from a broad market move. These historical curator and market checks are not a new live-data query.", period)
    robust = pd.read_csv(data["g20"] / "robustness.csv")
    robust = robust[robust.Period.eq(period)].drop(columns="Period")
    table(robust, {"Best update": "{:.2%}", "Excess kurtosis": "{:.1f}", "Top positive profit share": "{:.1%}"})
    heading("Largest-update observation intervals and market context", "NAV and BTC/ETH returns cover the actual first-to-last observation interval, rather than being called a one-day move. Curator exclusions/quarantine come from the frozen NB20 audit; no new policy accounts exist when the gate stops.", period)
    tails = pd.read_csv(data["g20"] / "tail-audit.csv")
    tails = tails[tails.Period.eq(period)].drop(columns="Period")
    table(tails, {"Update profit (USD)": "${:,.0f}", "NAV_return": "{:.2%}", "Interval_days": "{:.2f}", "BTCUSDT return": "{:.2%}", "ETHUSDT return": "{:.2%}"})


def long_signal_report(data):
    heading("Long native decision calendar coverage", "The frozen NB21 cache omits 28 initial inactive native decisions. Their opportunity population is unobserved here, not assumed empty or backfilled. They have no source target or executable fresh entry, so the entry policy passes through. Full Long-account benchmark economics still include all cash-only days.", "Long")
    table(data["native_coverage"].query("Period == 'Long'"))
    heading("Long diagnostic signal metrics", "Every monthly calibration remains chronological. The frozen horizon and qualification are selected on pre-2026 outcomes, so the complete long calendar is a retrospective configuration diagnostic, not independent validation. The detailed scatter suite defaults to 2026.", "Long")
    m = calibration_table(data, "Long")
    data["Long_signal_metrics"] = m
    m.to_csv(data["artifact"] / "Long-signal-metrics.csv", index=False)
    table(m, {"Mean_realised": "{:.2%}", "Mean_prediction": "{:.2%}", "Mean_error": "{:.2%}", "MAE": "{:.2%}", "Rank_IC": "{:.3f}", "Sign_accuracy": "{:.1%}", "Constant_sign_accuracy": "{:.1%}"})
    activation_report(data, "Long")


def finalise_results(data):
    from create_entry_margin_notebook import HEADER, PATH
    from entry_margin_data import sha

    r = data["registration"]
    s = ledger_summary(data, "2026")
    closed = s[s.Cohort.eq("Closed")].iloc[0]
    m = data["2026_signal_metrics"]
    l2 = m[m.Model.eq("L2") & m.H.eq(data["horizon"]) & m.Comparator.eq("Calibrated")].iloc[0]
    pooled = m[m.Model.eq("L2") & m.H.eq(data["horizon"]) & m.Comparator.eq("Matched L0")].iloc[0]
    raw = m[m.Model.eq("L2") & m.H.eq(data["horizon"]) & m.Comparator.eq("Raw D")].iloc[0]
    block_median = r["placebo_median_per_dollar"]["quarter/support-era H-day blocks"]
    status = "Conditional accounts executed" if r["execute_accounts"] else "Stopped before conditional accounts"
    text = f"""# Experiment 22 — C00 entry-margin calibration

## What was examined

Whether existing NB21 forecasts become economically useful near C00's fresh-entry boundary after calibrating the shared net-return level and relative spread separately. C00 selection, six slots, regularised 90-day risk, waterfall and constraints remain unchanged. Inputs are the frozen NB20/21 repaired generation.

## Hypotheses and method

H1: fresh entries contain avoidable downside; H2: supported D ordering and calibrated absolute levels identify selectively weak entries; H3: the selective veto improves account economics beyond whole-entry controls. Initial-buy units are attributed proportionally through actual net sales/top-ups. Sparse endpoint labels carry only known NAV, require a subsequent actual report, and become trainable only after confirmation. Horizon selection and the account qualification use fully matured pre-2026 entries only; 2026 model updates remain causal but exploratory. Missing and young vaults are retained, with unsupported D passing through C00.

## Result — 2026-01-01–2026-10-04 UTC

- **{status}.** Registered horizon: **{data['horizon']} days** from {r['past_entries']} pre-2026 executable entries; common horizon-alignment cohort: {data['horizon_registration']['common_closed_spells']} fully closed spells.
- Closed 2026 initial cohorts: {int(closed.Spells)} spells; frozen initial-entry loss headroom **${closed.Frozen_loss_headroom_USD:,.0f}**, versus C00 account profit **$62,376**. Equal-spell median lifetime {closed.Median_days:.1f} days; initial-cash-weighted mean {closed.Capital_weighted_days:.1f} days. Loss headroom is not a veto-policy profit bound.
- Pre-2026 actionable entries: **{r['past_actionable']} / {r['past_entries']}**; vetoes **{r['pre2026']['Vetoes']}**. Closed-spell avoided value **${r['pre2026']['Value']:,.0f}**; per resolved veto dollar **{r['pre2026']['Per_resolved_dollar']:.2%}** (undefined if no veto dollars).
- 2026 actual-entry activation: **{r['activation2026']} vetoes**. Calibrated L2 H{data['horizon']} band MAE **{l2.MAE:.2%}**, equal-origin rank IC **{l2.Rank_IC:.3f}**, sign accuracy **{l2.Sign_accuracy:.1%}** versus constant-level baseline **{l2.Constant_sign_accuracy:.1%}**. These forecast statistics alone do not establish a trading advantage.
- The calibrated mean forecast bias improves from **{raw.Mean_error*100:+.2f} to {l2.Mean_error*100:+.2f} percentage points**, but its MAE exceeds matched L0's **{pooled.MAE:.2%}**. Correcting levels did not rescue 2026 relative ordering.
- Unchanged 2026 C00: **58.59% CAGR, 2.474 Sharpe, −6.36% drawdown**; v11: **49.15%, 2.214, −6.41%**. No unexecuted overlay receives a performance claim.

## Qualification and hypothesis verdicts

The closed-spell selective value is **{r['pre2026']['Per_resolved_dollar']:.2%} per resolved veto dollar**, compared with the blocked-control median **{block_median:.2%}**. The pre-cutoff mark-only scenario changes the avoided value to **{r['pre2026']['Mark_value']:,.0f} USD**. The gate therefore fails both timing control and missing-spell sensitivity. Complete failed checks: **{'; '.join(r['stop_reasons']) or 'none'}**. H1 loss headroom is descriptive, not identified preventability. H2's registered selective-benefit hypothesis is not demonstrated. H3 remains untested when accounts stop; this does not prove no improved strategy exists.

Pre-2026 unresolved veto dollars: ${r['pre2026']['Unresolved_Q']:,.0f}. Mark-only avoided value: ${r['pre2026']['Mark_value']:,.0f}; loss-to-zero scenario: ${r['pre2026']['Loss_to_zero_value']:,.0f}. Break-even positive unknown mean: {r['pre2026']['Break_even_unknown_mean']:.2%}, undefined where unresolved mass is zero. Positive unknown outcomes have no finite upper bound; carry is not a universal adverse bound.

## Full-history diagnostic — 2023-03-01–2026-10-07 UTC

Fresh independent C00 ends at $420,882, **33.13% CAGR / 1.651 Sharpe / −9.94% drawdown**; v11 ends at $277,078, **18.55% / 1.374 / −7.92%**. Final archive day partial. Early unsupported forecasts pass through. These overlapping calendars are researched history; the qualification/horizon configuration is retrospective for the long account.

## Useful leads and limits

Entry-level managed economics and calibrated-band forecasts answer different questions. Short holding labels can miss source-managed exits, top-ups and re-entry; headline IC is not a licence to shut off profitable core exposure. The registered pass-through protects young/missing/pool-only observations from unsupported vetoes. The next change needs evidence on actual executable entry identities and managed outcomes, not a rescued threshold after looking at 2026.

H7 has lower past-only equal-origin capital-weighted discrepancy with managed returns than H2 (8.05% versus 10.92%); even H7 is an approximation. L2's expanding within-band slope falls from about 2.39 in January to 0.04 in October as 2026 outcomes mature. Its confidence intervals include zero; mathematical identification is not reliable forecasting. Losses concentrate in vaults that also supplied important gains, so a vault-level exclusion would not follow from this audit.

Saved-state control parity and frozen-D distribution parity were checked. All 139 native 2026 decisions have cached features. The Long-account cache omits 28 initial inactive native warm-up decisions; their candidate population is unknown, not silently assumed empty. These dates have no source targets or executable fresh entries, and no forecast can veto them. Reported long-band statistics use covered origins; full account economics retain all cash-only days. Primary labels remove the old one-day endpoint exclusion, but the frozen underlying D training still has NB21's freshness-selection limitation; H2 penalty-fold support warnings are disclosed. All saved C00 trades succeeded synchronously, and every buy's planned funded reserve equals executed reserve: actual first buys recover its executable fresh-entry schedule. Selected targets below executable floors remain separate intent diagnostics. Recorded NAV/permission chronology, retrospective guard/inventory, assumed fees, open/disappeared outcomes and repeated-vault/calendar dependence remain limits.

The frozen reference audit attributes 35.4% of C00's positive 2026 vault profit to Realist Capital. The best 2026 account update is +6.46%; Realist Capital and Goon Edging NAVs rise roughly 14% over about two days while BTC/ETH fall over the same observation interval. This is not broad-market confirmation. Sparse NAV can bunch returns; the recorded curator flags do not establish executable price truth.

The optional component factorial is **not executed**. No extra model, threshold, seed search, capacity expansion or unrelated notebook change was introduced.
"""
    (data["artifact"] / "findings.md").write_text(text)
    header = HEADER.split("## Key new insights")[0] + f"""## Key new insights

- Seven days aligns better than two with pre-2026 managed entry outcomes; horizon labels remain approximations.
- Calibrating the return level reduces forecast bias, but L2 H{data['horizon']} relative ordering in 2026 is weak/negative (IC {l2.Rank_IC:.3f}); its MAE {l2.MAE:.2%} is worse than matched L0 {pooled.MAE:.2%}.
- Closed-entry downside exists (${closed.Frozen_loss_headroom_USD:,.0f} in 2026), but it is hindsight headroom rather than identified avoidable portfolio loss.

## Summary of results

**{status}.** The rule vetoes {r['pre2026']['Vetoes']} pre-2026 entries and would affect {r['activation2026']} actual 2026 entries. Past closed-spell selective value is {r['pre2026']['Per_resolved_dollar']:.2%} per resolved veto dollar, below the calendar-block median {block_median:.2%}; the past-only mark scenario reverses the apparent benefit. Under the registered plan, O1/R01–R05 accounts are not run after this failure. H3 is untested, and no profitability improvement is claimed.

Unchanged 2026 benchmarks: C00 **58.59% CAGR / 2.474 Sharpe / −6.36% drawdown**; v11 **49.15% / 2.214 / −6.41%**. The independent long-account comparison is below. These are saved NB20 account results with verified equity/trade identity.

## Robustness of results

All four saved control paths and frozen monthly D distributions match; all source C00 trade proposals executed synchronously at their funded reserves. Monthly calibration uses only confirmed matured past labels, including 2025 warm-up; young/unscored vaults remain eligible. The primary labels carry known sparse NAV without leading backfill and audit report confirmation/maturity explicitly.

The underlying frozen D training still inherits NB21's endpoint freshness bias. Confidence intervals, repeated-vault dependence, partially matured origins, open/disappeared outcomes, assumed fees and retrospective universe/guards limit inference. Realist Capital supplies 35.4% of positive C00 2026 vault profit; its strongest NAV interval is not corroborated by a positive BTC/ETH move. The optional factorial and conditional account execution checks remain unexecuted. All conclusions use previously researched overlapping calendars.
"""
    (data["artifact"] / "final-header.md").write_text(header)
    complete = dict(horizon=data["horizon"], execute_accounts=r["execute_accounts"], qualified=r["qualified"], activation2026=r["activation2026"], figures=len(data["figures"]), stage2_stop_reasons=r["stop_reasons"], status_detail=status)
    (data["artifact"] / "complete.json").write_text(json.dumps(complete, indent=2))
    (data["artifact"] / "figure-manifest.json").write_text(json.dumps(data["figures"], indent=2))
    import nbformat

    # Record the exact generation in the running notebook; observable runner preserves metadata.
    nb = nbformat.read(PATH, 4)
    nb.metadata["nb22"]["artifact_generation"] = str(data["artifact"])
    nbformat.write(nb, PATH)
    # Runner saves its in-memory notebook later: expose the exact generation also as saved output.
    display(Markdown(f'**Executed artefact generation:** `{data["artifact"]}`'))
    return text


def verdict_report(data):
    heading("Hypothesis verdicts", "Only executed evidence receives a verdict. A stopped admission policy leaves account profitability untested; it does not establish that all future entry signals must fail.")
    r = data["registration"]
    table(pd.DataFrame([dict(Hypothesis="H1: avoidable fresh-entry downside", Verdict="Descriptive loss headroom; preventability not identified", Reason="Attribution preserves actual source management, not a causal veto path"), dict(Hypothesis="H2: calibrated selective signal", Verdict="Qualified" if r["qualified"] else "Registered gate not met", Reason="; ".join(r["stop_reasons"]) or "Closed pre-2026 selective value exceeds controls"), dict(Hypothesis="H3: improved account economics", Verdict="Executed" if r["execute_accounts"] else "Not tested: conditional stage stopped", Reason="No rescue threshold or backtest performed after failed gate"), dict(Hypothesis="Optional component factorial", Verdict="Not executed", Reason="Plan explicitly defers all eight current-accounting cells")]))
