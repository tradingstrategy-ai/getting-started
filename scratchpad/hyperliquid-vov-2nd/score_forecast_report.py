"""Assemble forecast diagnostics and recorded conclusions for experiment 08."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import HTML, Markdown, display

from score_forecast_visualisation import (
    SHORT_PERIOD,
    LONG_PERIOD,
    FOCAL_METHODS,
    method_name,
    method_records,
    intro,
    styled_table,
    show_png,
    heatmap_figure,
    line_panels,
)


def focal_ic_table(data, statistics, period="2026"):
    """Compare predeclared methods without selecting on observed maxima."""
    source = statistics["ic_summary"]
    source = source[source.period.eq(period) & source.method_id.isin(FOCAL_METHODS) & source.outcome.isin(["cagr", "sharpe"])].copy()
    source["method"] = source.method_id.map(lambda m: method_name(data, m))
    cols = ["method", "lookahead_days", "outcome", "mean_ic", "ic_lower", "ic_upper", "supported_origins", "distinct_vaults", "paired_rows", "inference_status"]
    return source[[c for c in cols if c in source]].sort_values(["method", "lookahead_days", "outcome"])


def overview_figures(data, statistics, folder):
    """Produce matrix, stability, calibration and risk views of the 2026 sample."""
    paths = []
    summary = statistics["ic_summary"]
    summary = summary[summary.period.eq("2026") & summary.outcome.isin(["cagr", "sharpe"])].copy()
    registry = method_records(data)
    ids = [r["method_id"] for r in registry]
    # Chunk all registered methods; no observed-performance selection is made.
    for start in range(0, len(ids), 25):
        subset = summary[summary.method_id.isin(ids[start : start + 25])].copy()
        subset["axis"] = subset.lookahead_days.astype(str) + "d " + subset.outcome.replace({"cagr": "CAGR", "sharpe": "Sharpe"})
        grid = subset.pivot(index="method_id", columns="axis", values="mean_ic").reindex(ids[start : start + 25])
        grid = grid.reindex(columns=["7d CAGR", "7d Sharpe", "30d CAGR", "30d Sharpe", "90d CAGR", "90d Sharpe"])
        grid.columns = ["7d CAGR", "7d Sharpe", "30d CAGR", "30d Sharpe", "90d CAGR †", "90d Sharpe †"]
        grid.index = [method_name(data, m).replace(" / ", " · ") for m in grid.index]
        path = heatmap_figure(grid, f"Same-date predictive rank IC · methods {start + 1}–{min(start + 25, len(ids))}", folder, f"ic-methods-{start // 25:02d}", limits=(-0.3, 0.3), colour_label="Equal-date mean rank IC", note="Shared colour scale: −0.30 to +0.30; * colour saturated, numeric value unchanged. † 90-day descriptive only.")
        show_png(path, "Predictive relationships across methods and horizons", "Equal-date mean Spearman correlation within eligible candidates: positive means higher scores ranked better future outcomes. " "Rows follow the frozen registry, not a winner sort. Dashes indicate insufficient support. " "The shared colour range is −0.30 to +0.30 so small differences remain visible; starred cells exceed the colour range but retain their true numbers. " "The 90-day short-history column is descriptive only; overlapping dots are not independent samples.")
        paths.append(path)
    from score_forecast_visualisation import figure_style, save_figure
    import matplotlib.pyplot as plt

    for outcome in ("cagr", "sharpe"):
        chosen = summary[summary.method_id.isin(FOCAL_METHODS) & summary.lookahead_days.eq(30) & summary.outcome.eq(outcome)].set_index("method_id").reindex(FOCAL_METHODS)
        with figure_style():
            fig, ax = plt.subplots(figsize=(9.5, 4.5))
            for i, (_, row) in enumerate(chosen.iterrows()):
                if np.isfinite(row.mean_ic):
                    ax.plot(row.mean_ic, i, "o", color="#111827", ms=7)
                if np.isfinite(row.ic_lower) and np.isfinite(row.ic_upper):
                    ax.hlines(i, row.ic_lower, row.ic_upper, color="#2563eb", lw=3)
            ax.set_yticks(range(len(chosen)), [method_name(data, m) for m in chosen.index])
            ax.axvline(0, lw=1, color="#64748b", ls="--")
            ax.set_xlabel("Equal-date mean rank IC; interval allows dependence between dates")
            ax.set_title(f'30-day future {"CAGR" if outcome == "cagr" else "Sharpe"}: predictive strength and uncertainty\n{SHORT_PERIOD}', fontsize=11, pad=18)
            ax.set_ylim(-0.5, len(chosen) - 0.5)
            ax.invert_yaxis()
            fig.tight_layout()
            path = save_figure(fig, folder, f"focal-uncertainty-{outcome}")
        show_png(path, f'30-day {"CAGR" if outcome == "cagr" else "Sharpe"} ranking: strength and uncertainty', "Dots are equal-date mean Spearman IC; lines are the saved dependence-aware uncertainty intervals. " "An interval crossing zero does not establish a positive predictive relationship. These methods were researched on previously inspected history.")
        paths.append(path)
    quarters = statistics["quarterly_ic"]
    quarters = quarters[quarters.period.eq("2026") & quarters.method_id.isin(FOCAL_METHODS) & quarters.outcome.eq("cagr")].copy()
    quarters["row"] = quarters.method_id.map(lambda m: method_name(data, m)) + " · " + quarters.lookahead_days.astype(str) + "d"
    grid = quarters.pivot(index="row", columns="origin_quarter", values="mean_ic").reindex(columns=["2026Q1", "2026Q2", "2026Q3", "2026Q4"])
    counts = quarters.pivot(index="row", columns="origin_quarter", values="origin_count").reindex(index=grid.index, columns=grid.columns)
    annotations = grid.copy().astype(object)
    for row in grid.index:
        for column in grid.columns:
            value, count = grid.loc[row, column], counts.loc[row, column]
            annotations.loc[row, column] = f"{value:+.2f}\nn={int(count)} dates" if np.isfinite(value) and np.isfinite(count) else "No labels"
    path = heatmap_figure(grid, "Quarter stability of future-return ranking", folder, "quarter-stability", limits=(-0.3, 0.3), annotations=annotations, colour_label="Equal-date mean rank IC", note="Counts are supported forecast dates, not independent windows. Long horizons have fewer matured dates; counts are printed in each cell.")
    show_png(path, "Quarter stability", "Quarter is the forecast origin. The final quarter has no matured labels; Long horizons have fewer matured origins. " "These columns are not equal-length evaluation periods. Supported origin counts appear in the table below.")
    paths.append(path)
    styled_table(quarters[["row", "origin_quarter", "mean_ic", "origin_count", "paired_origins", "status"]], "Quarter coverage behind the colour map", "Count supported and merely paired origins before interpreting a quarterly correlation.", collapsed=True)
    bins = statistics["score_bins"]
    bins = bins[bins.period.eq("2026") & bins.lookahead_days.eq(30) & bins.method_id.isin(FOCAL_METHODS)]
    frames = {method_name(data, m): bins[bins.method_id.eq(m)] for m in FOCAL_METHODS}
    metric_paths = line_panels(frames, "mean_score", ["median_return", "loss_probability", "return_q05"], "30-day score calibration and downside", folder, "score-calibration-tail", labels={"median_return": "Median 30-day return (%)", "loss_probability": "Probability of loss (%)", "return_q05": "5th-percentile return (%)"}, percent_targets=("median_return", "loss_probability", "return_q05"))
    for path in metric_paths:
        show_png(path, "Score calibration and tail risk: " + path.stem.split("score-calibration-tail-")[-1].replace("_", " "), "Fixed score bins retain ties. Median return, loss frequency and the lower tail answer different questions. " "Curves are retrospective diagnostics, not fitted live forecasts; counts and attrition are shown separately.")
    paths.extend(metric_paths)
    ranks = statistics["rank_bands"]
    ranks = ranks[ranks.period.eq("2026") & ranks.lookahead_days.eq(30)]
    if len(ranks):
        x = "mean_rank" if "mean_rank" in ranks else "bin"
        frames = {method_name(data, m): ranks[ranks.method_id.eq(m)] for m in FOCAL_METHODS}
        metric_paths = line_panels(frames, x, ["median_return", "loss_probability"], "30-day outcomes by candidate rank", folder, "marginal-rank", labels={"median_return": "Median 30-day return (%)", "loss_probability": "Probability of loss (%)"}, percent_targets=("median_return", "loss_probability"))
        for path in metric_paths:
            show_png(path, "Candidate rank: " + path.stem.split("marginal-rank-")[-1].replace("_", " "), "Compare the upper candidate ranks with lower-ranked candidates. " "Candidate ranks use average ranks for ties; held-position hysteresis means these are not necessarily the actual marginal entries.")
        paths.extend(metric_paths)
    delayed = statistics["delayed_anchor"]
    delayed = delayed[delayed.period.eq("2026") & delayed.lookahead_days.eq(30) & delayed.outcome.eq("cagr")].copy()
    base = summary[summary.method_id.isin(FOCAL_METHODS) & summary.lookahead_days.eq(30) & summary.outcome.eq("cagr")].copy()
    base["delay_days"] = 0
    delayed = pd.concat([base, delayed], ignore_index=True)
    metric_paths = line_panels({method_name(data, m): delayed[delayed.method_id.eq(m)] for m in FOCAL_METHODS}, "delay_days", ["mean_ic"], "30-day predictive ranking with delayed entry anchors", folder, "delayed-anchor", labels={"mean_ic": "Equal-date mean rank IC"})
    for path in metric_paths:
        show_png(path, "Entry timing and stale-mark sensitivity", "Keep the score fixed while delaying the NAV anchor one or two days. " "A disappearing relationship would suggest dependence on shared endpoints or timing, rather than persistent forward information.")
    paths.extend(metric_paths)
    decay = statistics.get("ic_decay", pd.DataFrame())
    if len(decay):
        selected = decay[decay.period.eq("2026") & decay.outcome.eq("log_return") & decay.delay_days.eq(0)]
        metric_paths = line_panels({method_name(data, m): selected[selected.method_id.eq(m)] for m in FOCAL_METHODS}, "lookahead_days", ["mean_ic"], "Exploratory information decay by lookahead", folder, "ic-decay", labels={"mean_ic": "Equal-date mean return-rank IC"})
        for path in metric_paths:
            show_png(path, "How long does the score information persist?", "Additional horizons diagnose information decay; they do not replace the required 7/30/90-day charts. " "Long horizons have fewer matured origins, so this is not a matched-sample comparison.")
        paths.extend(metric_paths)
    return paths


def display_calibration(data, statistics, folder):
    """Explain chronological calibration performance and saved threshold decisions."""
    metrics = statistics["calibration_metrics"]
    metrics = metrics[metrics.period.eq("2026")].copy() if len(metrics) else metrics
    for horizon in (30, 7, 90):
        shown = metrics[metrics.lookahead_days.eq(horizon)].copy() if len(metrics) else metrics
        if len(shown):
            shown["method"] = shown.method_id.map(lambda m: method_name(data, m))
            styled_table(shown[[c for c in ["method", "lookahead_days", "outcome", "model", "equal_date_mae", "equal_date_mse", "brier_score", "origin_count", "vault_count"] if c in shown]], f"{horizon}-day chronological forecast errors", "Monthly models use only earlier labels whose full future windows had become observable. " "Main estimates require at least 20 actual training origins and 10 vaults for the specific outcome. " "Lower MAE/MSE/Brier is better; outcome units differ. Forecast dates overlap; the support table reports training and evaluation counts.", collapsed=horizon != 30)
    support = statistics.get("calibration_support", pd.DataFrame())
    if len(support):
        shown = support[support.period.eq("2026")]
        styled_table(shown, "Calibration training and evaluation support", "Thin earlier fits remain archived as exploratory and are excluded from the main error comparison. " "Large cross-sectional row counts cannot replace independent dates; inspect horizon-specific support.", collapsed=True)
    thresholds = statistics["monthly_thresholds"]
    thresholds = thresholds[pd.to_datetime(thresholds.calibration_at).ge("2026-01-01")].copy()
    thresholds["method"] = thresholds.method_id.map(lambda m: method_name(data, m))
    cols = ["method", "calibration_at", "policy", "floor", "active", "support_flag", "training_origins", "training_vaults", "costs_status"]
    styled_table(thresholds[[c for c in cols if c in thresholds]], "Frozen monthly entry rules", "The absolute rule selects the lowest supported floor whose below-floor mean source-modelled net log return has a negative simultaneous upper bound. " "No supported floor means no restriction. The 75th-percentile rule is fixed in advance and recomputed from current eligible scores; it is not an optimised numeric cutoff.", collapsed=True)
    null = statistics["joint_null"]
    if len(null):
        selected = null[null.period.eq("2026")]
        styled_table(selected, "Joint family-level null and support", "Joint serial-dependence-preserving shifts compare the family maximum on common valid populations. " "The full registry may have too little shared two-year history; the separately labelled focal-family comparison is narrower. " "Short-period 90-day inference is deliberately absent.", collapsed=True)
    return []


def display_execution(data, execution, folder):
    """Display actual policy replays separately from diagnostic target returns."""
    from score_forecast_visualisation import figure_style, save_figure
    import matplotlib.pyplot as plt

    primary = execution["2026"]
    policies = primary[primary["Seed"].isna()].copy()
    cols = ["Method", "Positions", "Threshold policy", "Treatment", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Mean vaults held", "Trades", "Rejected entry proposals", "Rejected entry dollars (USD)", "Floor-active decision fraction", "No-floor equivalent"]
    meaningful = policies[policies["Threshold policy"].eq("none") | ~policies["No-floor equivalent"].astype(bool)]
    styled_table(meaningful[[c for c in cols if c in meaningful]], "Distinct net portfolio performance side by side", "Fresh $150,000 replays keep the source two-day cadence, 90-day inverse variance, caps, guards, hysteresis and estimated costs. " "Slot-to-cash preserves the surviving proposed dollar targets; renormalisation redistributes among the remaining selected holdings. " "A no-floor-equivalent row rejected no entries and is not a new successful strategy.")
    styled_table(policies[[c for c in cols if c in policies]], "Complete primary policy arms", "All 30 non-random arms are retained, including verified no-entry-change duplicates. The compact comparison above shows only baseline and binding policies.", collapsed=True)
    paths = []
    import matplotlib.dates as mdates

    # All strategy/position-count charts share one scale for an honest comparison.
    shared_limits = (95, 145)
    policy_colours = {"Baseline": "#2563eb", "75% floor / cash": "#f97316", "75% floor / capped redistribution": "#16a34a"}
    for method in FOCAL_METHODS:
        for n in (6, 7):
            with figure_style():
                fig, ax = plt.subplots(figsize=(9.5, 5.7))
                rows = policies[policies.Method.eq(method) & policies.Positions.eq(n)]
                seen = set()
                baseline_curve = None
                distinct_curves = []
                for row in rows.to_dict("records"):
                    from score_forecast_execution import ARTIFACT_DIR

                    curve = pd.read_csv(ARTIFACT_DIR / row["cache_key"] / "equity.csv", index_col="Date", parse_dates=True)
                    if row["Threshold policy"] == "none":
                        baseline_curve = curve
                        baseline_row = row
                    signature = curve.equity.round(6).to_numpy().tobytes()
                    if signature in seen:
                        continue
                    seen.add(signature)
                    label = "Baseline" if row["Threshold policy"] == "none" else "75% floor / " + ("cash" if row["Treatment"] == "slot_to_cash" else "capped redistribution")
                    ax.plot(curve.index, curve.equity / curve.equity.iloc[0] * 100, label=label, color=policy_colours[label], lw=1.8)
                    distinct_curves.append((label, curve))
                ax.set_title(f"{method_name(data, method)} · {n} positions · net equity\n{SHORT_PERIOD}", fontsize=11, pad=18)
                ax.set_ylabel("Equity index (start = 100)")
                ax.set_ylim(*shared_limits)
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
                ax.set_xlabel("2026 decision date (UTC)")
                note = f'Baseline CAGR {baseline_row["CAGR"]:.2%} · Sharpe {baseline_row["Sharpe"]:.2f} · drawdown {baseline_row["Maximum drawdown"]:.2%}'
                if len(distinct_curves) == 1:
                    note += "\nAll tested non-random entry floors have the same equity path."
                fig.text(0.5, 0.015, note, ha="center", fontsize=8.5, color="#475569")
                ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False, fontsize=8.5)
                fig.tight_layout(rect=[0, 0.12, 1, 1])
                path = save_figure(fig, folder, f"portfolio-{method}-n{n}")
            show_png(path, f"Executable entry-floor equity: {method_name(data, method)}, {n} positions", "All six method/position charts use the same equity scale. Identical paths appear once. " "Costs and cash usage are included; the printed metrics describe the unchanged baseline.")
            paths.append(path)
            if len(distinct_curves) > 1:
                with figure_style():
                    fig, ax = plt.subplots(figsize=(9.5, 5.5))
                    for label, curve in distinct_curves:
                        if label != "Baseline":
                            excess = (curve.equity / baseline_curve.equity - 1) * 10000
                            ax.plot(curve.index, excess, label=label, color=policy_colours[label], lw=1.7)
                    ax.axhline(0, color="#64748b", lw=0.9)
                    ax.set_title(f"{method_name(data, method)} · {n} positions · admission-floor effect\n{SHORT_PERIOD}", fontsize=11, pad=18)
                    ax.set_ylabel("Equity difference versus baseline (basis points)")
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
                    ax.set_xlabel("2026 decision date (UTC)")
                    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=8.5)
                    fig.tight_layout(rect=[0, 0.08, 1, 1])
                    path = save_figure(fig, folder, f"portfolio-{method}-n{n}-difference")
                show_png(path, f"Admission-floor effect: {method_name(data, method)}, {n} positions", "A separate difference plot reveals lines that overlap in the equity chart. One basis point is 0.01%. " "A small gain from one changed entry is not evidence of a stable forecasting advantage.")
                paths.append(path)
    randoms = execution.get("random_controls", pd.DataFrame())
    if len(randoms):
        period_column = "Period" if "Period" in randoms else "period"
        selected = randoms[randoms[period_column].eq("2026")]
        styled_table(selected, "Matched random admission controls", "Three predeclared seeds reject the same number of proposed new entrants and approximately match their dollars. " "Each random arm develops its own later portfolio state, so this is a conditional control rather than an exact path counterfactual.", collapsed=True)
    robust = execution.get("robustness", pd.DataFrame())
    if len(robust):
        selected = robust[robust.Period.eq("2026") & robust.Seed.isna()]
        styled_table(selected, "Portfolio robustness and PnL concentration", "A strong best day and leading-vault share reveal dependence on a few outcomes. " "Zeroing a day or removing vault PnL from a fixed ledger is a sensitivity, not a new executable strategy.", collapsed=True)
    quarterly = execution.get("quarterly", pd.DataFrame())
    if len(quarterly):
        selected = quarterly[quarterly.Period.eq("2026") & quarterly.Seed.isna()].copy()
        identities = meaningful[["Method", "Positions", "Threshold policy", "Treatment"]]
        selected = selected.merge(identities, on=["Method", "Positions", "Threshold policy", "Treatment"], validate="many_to_one")
        if "Quarter" in selected and "Quarter return" in selected:
            selected["row"] = selected.apply(lambda r: method_name(data, r.Method) + f" · {r.Positions} positions · " + ("baseline" if r["Threshold policy"] == "none" else "75% floor / " + ("cash" if r.Treatment == "slot_to_cash" else "capped redistribution")), axis=1)
            grid = selected.pivot(index="row", columns="Quarter", values="Quarter return") * 100
            grid.columns = [str(c) + (" (partial)" if str(c).endswith("Q4") else "") for c in grid.columns]
            path = heatmap_figure(grid, "Executable portfolio profit by quarter (%)", folder, "portfolio-quarterly", fmt="+.1f", colour_label="Net quarter return (%)")
            show_png(path, "Portfolio profit heatmap by quarter", "Quarterly compounded net portfolio returns use actual replay equity. " "The final quarter is partial. No-entry-change duplicates are omitted; this heatmap is different from quarter-coloured forward labels.")
            paths.append(path)
    long = execution["Long"]
    styled_table(long[long.Seed.isna()][[c for c in cols if c in long]], "Secondary full-history portfolio comparison", "Identical policy rules over the longer history. This period overlaps 2026 and was already used in earlier research, so it is not independent confirmation.", period=LONG_PERIOD, collapsed=True)
    styled_table(cash_yield_sensitivity(execution), "Assumed cash-yield sensitivity", "Zero yield is the actual source replay. The 3%/5% annual scenarios add hypothetical daily yield to prior cash weights on a fixed ledger, without changing sizing or fees. They are attribution scenarios, not executable cash-sweep backtests.", collapsed=True)
    return paths


def cash_yield_sensitivity(execution):
    """Add assumed reserve yield to the fixed baseline ledger, without resizing."""
    from score_forecast_execution import ARTIFACT_DIR
    from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe

    rows = []
    for record in execution["2026"].query("`Threshold policy` == 'none'").to_dict("records"):
        curve = pd.read_csv(ARTIFACT_DIR / record["cache_key"] / "equity.csv", index_col="Date", parse_dates=["Date"])
        assert isinstance(curve.index, pd.DatetimeIndex)
        assert curve.index.to_series().diff().dropna().eq(pd.Timedelta(days=1)).all()
        cash = curve.cash_weight.shift(1).fillna(1.0)
        for annual_yield in (0.0, 0.03, 0.05):
            daily = curve.daily_return + cash * ((1 + annual_yield) ** (1 / 365) - 1)
            wealth = (1 + daily).cumprod()
            rows.append({"Method": record["Method"], "Positions": record["Positions"], "Assumed annual cash yield": annual_yield, "Fixed-ledger CAGR": float(calculate_cagr(daily)), "Fixed-ledger Sharpe": float(calculate_sharpe(daily, periods=365)), "Fixed-ledger maximum drawdown": float((wealth / wealth.cummax() - 1).min())})
    return pd.DataFrame(rows)


def write_findings(data, statistics, execution, notebook):
    """Write current verdicts directly from recomputed sparse-data tables."""
    folder = Path(notebook).parent
    primary = focal_ic_table(data, statistics)
    portfolios = execution["2026"]
    plain = portfolios[portfolios.Seed.isna()].copy()
    monthly = statistics["monthly_thresholds"]
    absolute = monthly[monthly.policy.eq("monthly_absolute") & pd.to_datetime(monthly.calibration_at).ge("2026-01-01")]
    best = plain.sort_values(["CAGR", "Sharpe"], ascending=False).iloc[0]
    ic30 = primary[primary.lookahead_days.eq(30) & primary.outcome.eq("cagr")]
    sh30 = primary[primary.lookahead_days.eq(30) & primary.outcome.eq("sharpe")]
    metrics = statistics["calibration_metrics"]
    metrics = metrics[metrics.period.eq("2026")].copy()
    constants = metrics[metrics.model.eq("constant")][["method_id", "lookahead_days", "outcome", "equal_date_mse"]].rename(columns={"equal_date_mse": "constant_mse"})
    learned = metrics[metrics.model.isin(["linear", "isotonic"])].merge(constants, on=["method_id", "lookahead_days", "outcome"])
    learned["MSE change vs constant"] = learned.equal_date_mse / learned.constant_mse - 1
    rejected = int(plain[plain["Threshold policy"].eq("monthly_absolute")]["Rejected entry proposals"].sum())
    changed = plain[plain["Threshold policy"].eq("none") | ~plain["No-floor equivalent"].astype(bool)].copy()
    columns = ["Method", "Positions", "Threshold policy", "Treatment", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Rejected entry proposals"]
    for col in ("CAGR", "Maximum drawdown", "Mean cash weight"):
        changed[col] = changed[col].map(lambda v: f"{v:.2%}")
    lines = [
        "# Experiment 08: scores, forecasts and admission floors",
        "",
        f"[Executed notebook]({Path(notebook).name}). Primary period: **{SHORT_PERIOD}**. Updated 10 October 2026; in-place sparse-data rerun.",
        "",
        "## Key new insights",
        "",
        f"- Recomputed all 139 score recipes at 7/30/90-day horizons. Primary targets use the latest actual positive NAV carried forward on calendar days; observation counts remain separate. No leading backfill or labels beyond each vault’s last actual mark/archive end. The source score and portfolio machinery is unchanged.",
        f"- Primary 30-day return rank IC ranges from **{ic30.mean_ic.min():.3f} to {ic30.mean_ic.max():.3f}**; Sharpe rank IC ranges from **{sh30.mean_ic.min():.3f} to {sh30.mean_ic.max():.3f}** across the three frozen methods. Inspect the intervals and origin counts below before interpreting these point estimates.",
        f'- Of {len(learned)} supported linear/isotonic method–horizon–target comparisons, **{int(learned["MSE change vs constant"].lt(0).sum())}** have lower equal-date MSE than the same-row historical constant. This does not by itself establish forecast or portfolio skill.',
        f"- The absolute floor is active in **{int(absolute.active.sum())}/{len(absolute)}** 2026 method-months and rejects **{rejected}** proposed entries across the replay treatments.",
        f'- The highest non-random replay is **{best["Method"]}, {int(best["Positions"])} positions, {best["Threshold policy"]} / {best["Treatment"]}**: CAGR **{best["CAGR"]:.2%}**, Sharpe **{best["Sharpe"]:.2f}**, drawdown **{best["Maximum drawdown"]:.2%}**. This is a descriptive maximum on previously researched history.',
        "",
        f"## Focal ranking evidence — {SHORT_PERIOD}",
        "",
        "Equal-date cross-sectional Spearman IC measures score discrimination among eligible candidates. CAGR and horizon-return ranks coincide at a fixed horizon. Future paths can contain carried marks, which may alter risk metrics.",
        "",
        primary.to_markdown(index=False),
        "",
        f"## Forecast calibration against constants — {SHORT_PERIOD}",
        "",
        "Negative MSE change is better. Monthly training uses only matured labels and requires at least 20 training origins and ten vaults for each outcome. Dates overlap; reported rows are not independent samples.",
        "",
        learned[["method_id", "lookahead_days", "outcome", "model", "origin_count", "equal_date_mse", "constant_mse", "MSE change vs constant"]].to_markdown(index=False),
        "",
        f"## Target coverage — {SHORT_PERIOD}",
        "",
        "The denominator includes all snapshot vaults and scheduled origins. Supported calendar paths can include carried NAV; undefined ratios and immature/terminal outcomes stay missing.",
        "",
        data["coverage"].query("period == '2026'").to_markdown(index=False),
        "",
        f"## Net portfolio rules — {SHORT_PERIOD}",
        "",
        "Fresh $150,000 replays preserve guards, capacity, inverse variance, two-day trading and source-modelled redemption costs. Thresholds use recomputed matured labels; no-floor controls retain their original rules.",
        "",
        changed[columns].to_markdown(index=False),
        "",
        "## Interpretation and next research",
        "",
        "Compare changed entry proposals, cash and net portfolio results with each method’s own no-floor control. A score relationship or lower forecast error is insufficient to justify an admission floor. Freeze promising rules and collect later observations before declaring superiority.",
        "",
        "Forward filling removes the incorrect complete-observation requirement. It assumes NAV is held at the last reported level between observations; reported returns can arrive as jumps. Inspect actual coverage, observation age, low activity and dense-observation sensitivity alongside the primary results.",
        "",
        "## Robustness and reproducibility",
        "",
        "- Four-day origins overlap. Confidence procedures use date baskets; 90-day estimates remain descriptive with too few independent windows. Both periods were previously used for research.",
        "- The 514-vault inventory and current guards are snapshot policy assumptions. Archived write times are not receipt clocks. No new input archive was fetched.",
        "- Raw-price targets retain positive tiny collapse prices, while framework guarded prices remain a separate sensitivity. Actual observations and carried marks are never conflated.",
        "- Missing scores, component-imputed scores and finite zero scores stay distinct. Fees retain the v11 model; gross vault outcomes are separate from executable portfolio PnL.",
        "- Independent target recomputation, source-score replication, equity/trade controls and chart manifests are retained under ignored artefacts. Pre-fill notebook, code and results are in `08-before-sparse-fill`.",
        f'- Data fingerprint: `{data["provenance"]["fingerprint"]}`.',
        "",
    ]
    text = "\n".join(lines)
    (folder / "08-score-forecast-findings.md").write_text(text)
    return text
