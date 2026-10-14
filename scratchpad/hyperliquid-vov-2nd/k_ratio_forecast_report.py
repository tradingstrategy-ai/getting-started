"""Separate, period-labelled figures and readable results for experiment 09."""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, FixedLocator
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, HTML, display
import nbformat

from k_ratio_features import ROOT, GENERATION, ARTIFACT_DIR, START, END, PERIOD, LONG_PERIOD, WINDOWS, METRICS, EXISTING, K_MAIN, K_ALL, HORIZONS, TARGETS
from k_ratio_forecast_models import target_column
from k_ratio_forecast_statistics import rho

FIGURES = ARTIFACT_DIR / "figures"
QUARTERS = {"2026Q1": "#2563eb", "2026Q2": "#059669", "2026Q3": "#d97706", "2026Q4": "#dc2626"}


def table(frame, heading, description, period=PERIOD, limit=40):
    """Use an explicit heading and description before every bounded table."""
    display(Markdown(f"### {heading}\n\n{period}. {description}"))
    if frame.empty:
        display(Markdown("No supported observations for this table."))
        return
    if len(frame) > limit:
        display(Markdown(f"Showing {limit} of {len(frame):,} rows; complete results are retained in the experiment artefacts."))
    shown = frame.head(limit).copy()
    style = shown.style.hide(axis="index").format(precision=3, na_rep="—")
    ic_formats = {c: "{:.4f}" for c in shown if pd.api.types.is_numeric_dtype(shown[c]) and (c == "IC" or c.endswith("_IC"))}
    if ic_formats:
        style = style.format(ic_formats, na_rep="—")
    fractions = {c: "{:.1%}" for c in shown if pd.api.types.is_numeric_dtype(shown[c]) and ("fraction" in c or "coverage" in c)}
    if fractions:
        style = style.format(fractions, na_rep="—")
    scientific = {c: "{:.3e}" for c in shown if pd.api.types.is_numeric_dtype(shown[c]) and any(w in c for w in ("MAE", "MSE", "prediction")) and shown[c].abs().max() > 1000}
    if scientific:
        style = style.format(scientific, na_rep="—")
    cols = [c for c in shown if pd.api.types.is_numeric_dtype(shown[c]) and any(w in c for w in ("IC", "MAE", "coverage")) and np.isfinite(shown[c]).any()]
    for col in cols:
        if "delta" in col or "change" in col:
            extent = max(float(shown[col].abs().max()), 1e-6)
            style = style.background_gradient(subset=[col], cmap="RdYlGn_r" if "MAE" in col else "RdYlGn", axis=0, vmin=-extent, vmax=extent)
        else:
            style = style.background_gradient(subset=[col], cmap="RdYlGn_r" if "MAE" in col else "RdYlGn", axis=0)
    display(HTML('<div style="overflow-x:auto">' + style.to_html() + "</div>"))


def save(fig, name):
    """Write individual PNGs with export metadata under the ignored namespace."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{name}.png"
    fig.savefig(path, dpi=115, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def show(path, heading, description, period=PERIOD):
    """Never collate images: each figure has its own reading structure."""
    display(Markdown(f"### {heading}\n\n{period}. {description}"))
    display(Image(filename=str(path)))


def heatmap(grid, title, name, description="", vmin=-1, vmax=1, counts=None, period=PERIOD, cmap="RdBu", percent=False, barlabel=None, digits=None):
    """Mask undefined tiles, print units/counts and colour on a stated scale."""
    grid = grid.astype(float)
    fig, ax = plt.subplots(figsize=(max(8, 0.82 * len(grid.columns) + 3), max(3.7, 0.48 * len(grid.index) + 2)))
    masked = np.ma.masked_invalid(grid.to_numpy())
    colour = plt.get_cmap(cmap).copy()
    colour.set_bad("#eeeeee")
    im = ax.imshow(masked, aspect="auto", cmap=colour, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(grid.columns)), grid.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(grid.index)), grid.index)
    ax.set_title(f"{title}\n{period}", fontsize=11, pad=14)
    for i in range(len(grid.index)):
        for j in range(len(grid.columns)):
            value = grid.iloc[i, j]
            text = "—" if not np.isfinite(value) else (f"{value:+.1%}" if vmin < 0 else f"{value:.0%}") if percent else f"{value:+.3f}" if vmax <= 0.1 else f"{value:+.2f}"
            if digits is not None and np.isfinite(value):
                text = f"{value:+.{digits}f}"
            if counts is not None and np.isfinite(value):
                text += f"\nn={int(counts.iloc[i,j])}"
            ax.text(j, i, text, ha="center", va="center", fontsize=8, color="black", bbox={"facecolor": "white", "alpha": 0.68, "edgecolor": "none", "pad": 1})
    fig.colorbar(im, ax=ax, shrink=0.8, label=barlabel or ("Fraction" if percent else "Spearman IC / correlation" if vmin == -1 and vmax == 1 else "Paired change"))
    fig.text(0.02, 0.01, description, fontsize=8, color="#475569", wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return save(fig, name)


def ic_map(statistics, horizon, target, long=False):
    """One target/horizon image, with feature metrics across lookbacks."""
    f = statistics["feature_summary"]
    f = f[f.horizon.eq(horizon) & f.target.eq(target) & f.period.eq("Long prior" if long else "2026")].copy()
    f["days"] = f.feature.str.extract(r"^(\d+d|max) ")[0]
    f["metric"] = f.feature.str.replace(r"^(\d+d|max) ", "", regex=True)
    lookbacks = [f"{d}d" for d in WINDOWS] + ["max"]
    f = f[f.metric.isin([*METRICS, "K-ratio"]) & f.days.isin(lookbacks)]
    grid = f.pivot(index="metric", columns="days", values="mean_IC").reindex(index=[*METRICS, "K-ratio"], columns=lookbacks)
    counts = f.pivot(index="metric", columns="days", values="defined_origins").reindex_like(grid)
    return heatmap(grid, f"{horizon}-day future {target}: individual feature rank IC", f"ic-{horizon}-{target}-" + ("prior" if long else "2026"), "Each tile averages within-origin IC equally. n=defined forecast origins; grey=undefined/uninventoried. Max is K only. Researched history, not a holdout.", counts=counts, period="2023-03-01 → 2026-01-01 (end exclusive, UTC)" if long else PERIOD)


def feature_scatter(data, feature, horizon, target):
    """Plot raw feature against realised future target, never a composite score."""
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    labels = data["labels"]
    labels = labels[labels.horizon.eq(horizon) & labels.delay.eq(0)]
    frame = f[["origin_at", "pair_id", "origin_quarter", feature]].merge(labels[["origin_at", "pair_id", target_column(target)]], on=["origin_at", "pair_id"])
    x = frame[feature].to_numpy(dtype=float)
    y = frame[target_column(target)].to_numpy(dtype=float)
    display_target = "Log return" if target == "CAGR" else target
    return scatter(x, y, frame.origin_quarter.to_numpy(), f"{feature} vs {horizon}-day future {target}" + (" (log-return view)" if target == "CAGR" else ""), f"feature-{feature}-{horizon}-{target}", feature, f"Realised {horizon}-day " + display_target, display_target)


def scatter(x, y, quarters, title, name, xlabel, ylabel, target, identity=False, display_tail=0.005):
    """Use explicit display cropping; all statistics retain full observations."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x, y, quarters = x[finite], y[finite], np.asarray(quarters)[finite]
    fig, ax = plt.subplots(figsize=(9.3, 6.1))
    if not len(x):
        ax.text(0.5, 0.5, "No supported paired observations\nMissing history/labels are not zeros.", ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        if len(x) >= 100 and np.unique(x).size > 1 and np.unique(y).size > 1:
            xl = np.quantile(x, [display_tail, 1 - display_tail])
            yl = np.quantile(y, [display_tail, 1 - display_tail])
            xxpad = max((xl[1] - xl[0]) * 0.05, 1e-5)
            yypad = max((yl[1] - yl[0]) * 0.05, 1e-5)
            limits = (xl[0] - xxpad, xl[1] + xxpad, yl[0] - yypad, yl[1] + yypad)
        else:
            limits = (x.min() - 1, x.max() + 1, y.min() - 1, y.max() + 1)
        if target == "CAGR":
            limits = (max(-1.02, limits[0]) if identity else limits[0], limits[1], max(-1.02, limits[2]), limits[3])
        visible = (x >= limits[0]) & (x <= limits[1]) & (y >= limits[2]) & (y <= limits[3])
        for quarter in sorted(set(quarters)):
            q = (quarters == quarter) & visible
            ax.scatter(x[q], y[q], s=10, alpha=0.25, color=QUARTERS.get(quarter, "#64748b"), label=f"{quarter} (n={int((quarters==quarter).sum()):,})", rasterized=True, edgecolors="none")
        ax.set_xlim(limits[:2])
        ax.set_ylim(limits[2:])
        ax.set_xscale("linear" if target == "Log return" and identity else "symlog", **({} if target == "Log return" and identity else {"linthresh": 0.5 if "CAGR" in xlabel else 1}))
        ax.set_yscale("linear" if target == "Log return" else "symlog", **({} if target == "Log return" else {"linthresh": 0.5 if target == "CAGR" else 1}))
        if target == "CAGR":

            def percentage_axis(axis, lo, hi):
                #: Sparse ticks retain the full extreme range without unreadable annualised percentages.
                positive = [1.0, 10.0, 100.0]
                if hi > 100:
                    positive.extend(np.geomspace(1000, max(1000, 10 ** np.floor(np.log10(hi))), 3))
                ticks = [v for v in [-1.0, 0.0, 1.0, *positive] if lo <= v <= hi]
                axis.set_major_locator(FixedLocator(sorted(set(ticks))))
                axis.set_major_formatter(FuncFormatter(lambda value, _: f"{value*100:.0f}%" if abs(value) < 1000 else f"{value*100:.0e}%"))

            percentage_axis(ax.yaxis, limits[2], limits[3])
            if identity:
                percentage_axis(ax.xaxis, limits[0], limits[1])
        if np.unique(x).size >= 5:
            ranks = pd.Series(x).rank(method="average", pct=True).to_numpy()
            trend = []
            for lo in np.arange(0, 1, 0.1):
                pick = (ranks > lo) & (ranks <= lo + 0.1)
                if pick.any():
                    trend.append((np.median(x[pick]), np.median(y[pick])))
            if len(trend) > 1:
                line = np.array(trend)
                ax.plot(line[:, 0], line[:, 1], color="#111827", linewidth=2, label="Descriptive decile-median trend")
        if identity:
            lo = max(limits[0], limits[2])
            hi = min(limits[1], limits[3])
            if hi > lo:
                ax.plot([lo, hi], [lo, hi], "--", color="#64748b", linewidth=1, label="Identity (perfect forecast)")
        ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, framealpha=0.9)
        ax.text(0.02, 0.98, f"Full paired observations: {len(x):,}\nDisplay tails outside view: {int((~visible).sum()):,}", transform=ax.transAxes, ha="left", va="top", fontsize=8, bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#cbd5e1"})
    ax.set_title(f"{title}\n{PERIOD}", fontsize=11, pad=12)
    ax.set_xlabel(xlabel + (" (linear scale)" if target == "Log return" and identity else " (symmetric log scale)"))
    ax.set_ylabel(ylabel + (" (linear scale)" if target == "Log return" else " (symmetric log scale)"))
    ax.grid(alpha=0.15)
    fig.tight_layout()
    return save(fig, name.replace("/", "-"))


def forecast_scatter(models, horizon, target, supported_only=True):
    """Show only supported forecasts, or an explicit support notice."""
    p = models["predictions"]
    p = p[p.horizon.eq(horizon) & p.target.eq(target) & p.arm.eq("Existing + K") & p.phase.eq(0) & p.delay.eq(0) & ~p.source]
    p = p[p.supported] if supported_only else p[~p.supported]
    x = p.prediction.to_numpy()
    y = p.actual.to_numpy()
    display_target = "Log return" if target == "CAGR" else target
    qualifier = "supported forecasts" if supported_only else "illustrative forecasts; insufficient training support"
    return scatter(x, y, p.origin_quarter.to_numpy(), f"{horizon}-day {target}: {qualifier}" + (" (log-return view)" if target == "CAGR" else ""), f"forecast-{horizon}-{target}", f"Predicted {display_target}", f"Realised {horizon}-day {display_target}", display_target, identity=True, display_tail=0.005)


def report_overview(data, models, stats):
    """Present coverage, paired results and shared feature redundancy."""
    table(stats["populations"], "Forecast population versus funding feasibility", "Primary predictors use observed NAV and age/quality only. Current guard/permission checks are separate diagnostic assumptions.")
    table(stats["target_coverage"], "Future label support by target and horizon", "All targets use causal forward-filled daily NAV; no backfill before first mark or target after last actual mark. Administrative censoring and undefined ratios are not zero outcomes.")
    f = data["features"]
    anchors = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    sparse = pd.DataFrame([{"Supported daily anchors": len(anchors), "Actual daily anchors": int(anchors.anchor_actually_observed.sum()), "Carried daily anchors": int(anchors.anchor_forward_filled.sum()), "Median actual daily coverage (90d)": anchors.observed_fraction_90.median(), "Median NAV observation age (hours)": anchors.freshness_hours.median(), "Max K rows using carried days": int((anchors["max K-ratio"].notna() & anchors["max filled_marks"].gt(0)).sum())}])
    table(sparse, "Sparse NAV support and observation quality", "Forward filling carries the latest known price; it does not add observations. Actual mark counts and ages remain quality controls. No leading backfill or future labels beyond the last actual vault mark are permitted.")
    if (GENERATION / "09-before-sparse-fill/features.parquet").exists():
        from audit_sparse_metrics import audit

        sparse_audit, sparse_coverage = audit()
        table(sparse_coverage, "Metric coverage before and after sparse support", "Identical 24,605 actual-observation anchors isolate the calculation change from admitting carried anchors. Every metric family is covered; fixed lookbacks and degenerate ratios retain legitimate missing values.")
    cov = stats["feature_coverage"].copy()
    cov["days"] = cov.feature.str.extract(r"^(\d+d|max) ")[0]
    cov["metric"] = cov.feature.str.replace(r"^(\d+d|max) ", "", regex=True)
    grid = cov.pivot(index="metric", columns="days", values="coverage").reindex(index=[*METRICS, "K-ratio"], columns=[f"{d}d" for d in WINDOWS] + ["max"])
    show(heatmap(grid, "Feature availability among supported daily anchors", "feature-coverage", "Denominator=observable vault/origin rows, not future survivors. Max is K only; other max tiles are not inventoried. Missing paths stay unavailable.", vmin=0, vmax=1, cmap="Greens", percent=True), "Daily metric feature availability", "Each tile shows finite-input coverage at four-day origins. Young vaults retain their available shorter features.")
    f = data["features"]
    anchors = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    long_cov = stats["feature_coverage"].query('feature in ["360d K-ratio", "max K-ratio"]')[["feature", "observed_anchor_rows", "finite_features", "coverage"]].copy()
    valid = anchors.loc[anchors["max K-ratio"].notna(), "max days"]
    long_cov["minimum_lookback_days"] = [360, valid.min()]
    long_cov["median_lookback_days"] = [360, valid.median()]
    long_cov["maximum_lookback_days"] = [360, valid.max()]
    table(long_cov, "One-year and all-history K coverage", "One year means 360 days. Max starts at the first actual positive NAV and ends at T−1; missing days carry the latest known positive NAV. Its length differs by vault/date and can be shorter than 180 days for young vaults. Missing paths stay missing; archive age is not inception.")
    selected_origins = f[(f.origin_at >= START) & f.phase.eq(0)].origin_at.unique()
    reasons = data["reasons"]
    reasons = reasons[reasons.origin_at.isin(selected_origins) & reasons.metric.eq("K-ratio") & reasons.days.isin(WINDOWS)]
    rg = reasons.groupby(["reason", "days"]).vaults.sum().unstack().reindex(columns=WINDOWS).fillna(0)
    rg.columns = [f"{d}d" for d in rg.columns]
    max_reasons = f[f.origin_at.isin(selected_origins)]["max reason"].value_counts()
    rg = rg.reindex(rg.index.union(max_reasons.index), fill_value=0)
    rg["max"] = max_reasons.reindex(rg.index, fill_value=0)
    rg = rg / rg.sum(axis=0)
    rg = rg.groupby(rg.index.to_series().replace({"insufficient_recorded_history": "insufficient_age"})).sum()
    rg.index = [{"defined": "Defined K", "insufficient_age": "Insufficient recorded history", "missing_daily_observations": "Missing actual daily marks", "zero_or_numerically_degenerate_slope_se": "Degenerate slope standard error"}.get(name, name) for name in rg.index]
    show(heatmap(rg, "K-ratio availability and missing reasons", "k-missing-reasons", "Includes prelaunch/current-snapshot rows; not the supported-anchor denominator.", vmin=0, vmax=1, cmap="Greens", percent=True), "Why K-ratio is missing", "Reasons distinguish insufficient age, missing daily observations and a degenerate slope standard error. These are not negative performance signals. Missing calendar days now use causal NAV carry; leading prelaunch history remains unavailable.")
    support = models["support"]
    support = support[support.phase.eq(0) & support.delay.eq(0) & ~support.source]
    table(support.groupby(["horizon", "target"]).agg(first_supported_refit=("refit_at", lambda x: support.loc[x.index].loc[support.loc[x.index, "supported"], "refit_at"].min()), supported_refits=("supported", "sum"), max_training_origins=("training_origins", "max"), max_training_blocks=("training_calendar_blocks", "max")).reset_index(), "Chronological model support", "A supported refit needs 20 target-valid origins, ten vaults and three calendar blocks. Thin-support outputs are excluded from headline forecast comparisons.")
    paired = stats["paired_summary"]
    primary = paired[paired.old.eq("Existing") & paired.phase.eq(0) & paired.delay.eq(0) & ~paired.source]
    table(primary[["horizon", "target", "paired_origins", "defined_IC_origins", "old_mean_IC", "new_mean_IC", "mean_delta_IC", "MAE_change_fraction", "calendar_blocks", "positive_blocks", "lower_block_band", "upper_block_band"]], "Does K improve the same-observation forecast?", "Positive delta IC improves within-date discrimination. Negative MAE change improves level error. Bands require eight full evaluation blocks; all results use researched history.")
    long = stats["long_k_summary"]
    long = long[long.phase.eq(0) & long.delay.eq(0) & ~long.source]
    table(long[["new", "horizon", "target", "paired_origins", "old_mean_IC", "new_mean_IC", "mean_delta_IC", "MAE_change_fraction", "calendar_blocks", "lower_block_band", "upper_block_band"]], "Do longer K inputs improve on the original four windows?", "The reference adds K over 30/60/90/180 days. Year adds 360 days; max adds full recorded history; Existing + K adds both. Each comparison fixes the same vault/date rows and shared missingness controls. An unavailable training column cannot improve its forecast.", limit=30)
    for target in TARGETS:
        selected = long[long.target.eq(target)]
        grid = selected.pivot(index="new", columns="horizon", values="mean_delta_IC").reindex(columns=HORIZONS)
        counts = selected.pivot(index="new", columns="horizon", values="paired_origins").reindex_like(grid)
        labels = {"Existing + K": "+ year and max", "Existing + short K + max": "+ max", "Existing + short K + year": "+ year (input unavailable)" if not stats["feature_coverage"].query('feature == "360d K-ratio"').finite_features.sum() else "+ year"}
        grid = grid.rename(index=labels)
        counts = counts.rename(index=labels)
        colour_limit = max(0.003, float(np.ceil(np.nanmax(np.abs(grid.to_numpy())) * 1000) / 1000))
        show(heatmap(grid, target + ": longer K versus four-window K", "long-k-" + target, "Same-row rank IC change; n=paired origins; grey=unsupported. Year=360 days; max=full recorded history. Symmetric colour range covers all measured cells.", vmin=-colour_limit, vmax=colour_limit, counts=counts, digits=4), target + " and the longer-lookback increment", "Positive values favour adding the longer inputs. All arms share missingness controls; the year-only comparison should be zero when no year input exists.")
    for value, title in [("mean_delta_IC", "K incremental rank IC"), ("MAE_change_fraction", "K proportional change in forecast MAE")]:
        grid = primary.pivot(index="target", columns="horizon", values=value).reindex(index=TARGETS, columns=HORIZONS)
        show(heatmap(grid, title, f"paired-{value}", "Same models, identical target-valid vault/date rows. Grey=unsupported.", vmin=-0.03, vmax=0.03, cmap="RdBu" if value == "mean_delta_IC" else "RdBu_r", percent=value == "MAE_change_fraction"), title, "Columns are the requested horizons. These are paired changes, not independently selected winners; undefined cells reflect lack of model support.")
    observed = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    for days in (30, 90, 180):
        columns = [f"{days}d {m}" for m in (*METRICS, "K-ratio", "slope", "residual_scale")]
        dates = [g[columns].corr(method="spearman", min_periods=10) for _, g in observed.groupby("origin_at")]
        grid = sum(x.fillna(0) for x in dates) / sum(x.notna().astype(int) for x in dates).replace(0, np.nan)
        pair_counts = sum((g[columns].notna().astype(int).T @ g[columns].notna().astype(int)) for _, g in observed.groupby("origin_at"))
        pair_counts.index = [c.replace(f"{days}d ", "") for c in pair_counts.index]
        pair_counts.columns = pair_counts.index
        grid.index = [c.replace(f"{days}d ", "") for c in grid.index]
        grid.columns = grid.index
        show(heatmap(grid, f"{days}-day feature redundancy", f"redundancy-{days}", "Equal-origin pairwise Spearman correlation; n=total paired vault/origin rows; pair coverage differs.", counts=pair_counts), f"{days}-day feature redundancy", "Correlation between historical inputs is not prediction of future performance. K and signed R² have an exact fixed-sample ordering identity; slope and residual scale help interpret it.")


def write_catalogue(data):
    """Embed each individual K scatter in a small, separate saved notebook."""
    folder = ROOT / "09-feature-scatter-catalogue"
    folder.mkdir(exist_ok=True)
    links = []
    paths = []
    for feature in [*K_ALL, "45d K-ratio"]:
        cells = [nbformat.v4.new_markdown_cell(f"# Experiment 09 — {feature} forward relationships\n\n{PERIOD}. Each image is independent. These are raw feature relationships, not composite scores or position weights.\n\n[Main notebook](../09-research-k-ratio-feature-forecasts.ipynb).")]
        for h in HORIZONS:
            for target in TARGETS:
                cells.append(nbformat.v4.new_markdown_cell(f"## {feature} versus {h}-day future {target}\n\nOne point is a vault/forecast-origin observation, coloured by origin quarter. Axis scales are stated on the chart; CAGR is shown as horizon log return; the line connects full-sample decile medians and is descriptive. Display tails are disclosed in the chart; computations retain all observations. Missing feature/target values are excluded, not set to zero. {PERIOD}."))
                finite_features = data["features"].loc[(data["features"].origin_at >= START) & data["features"].phase.eq(0), feature].notna().sum()
                if not finite_features:
                    cells.append(nbformat.v4.new_markdown_cell(f"No finite **{feature}** inputs exist at the scheduled 2026 origins under the causal daily NAV policy. The archive does not supply this full lookback. An empty scatter would not provide evidence about predictive power; this combination remains inventoried."))
                    stale = FIGURES / f"feature-{feature}-{h}-{target}.png"
                    if stale.exists():
                        stale.unlink()
                    continue
                observed = data["features"]
                observed = observed[(observed.origin_at >= START) & observed.phase.eq(0) & observed.anchor_supported & observed[feature].notna()]
                valid_labels = data["labels"]
                valid_labels = valid_labels[valid_labels.horizon.eq(h) & valid_labels.delay.eq(0) & np.isfinite(valid_labels[target_column(target)])]
                paired = observed[["origin_at", "pair_id"]].merge(valid_labels[["origin_at", "pair_id"]], on=["origin_at", "pair_id"])
                if paired.empty:
                    cells.append(nbformat.v4.new_markdown_cell(f"Historical **{feature}** values exist, but no same-origin vault observations have a valid matured **{h}-day {target}** label. The combined feature lookback and future horizon exceed the supported calendar history. This is missing evidence, not zero predictive power."))
                    stale = FIGURES / f"feature-{feature}-{h}-{target}.png"
                    if stale.exists():
                        stale.unlink()
                    continue
                path = feature_scatter(data, feature, h, target)
                cell = nbformat.v4.new_code_cell("#: Saved static research output; the main notebook rebuilds this catalogue.")
                from base64 import b64encode

                cell.outputs = [nbformat.v4.new_output("display_data", data={"image/png": b64encode(path.read_bytes()).decode()}, metadata={})]
                cell.execution_count = 1
                cells.append(cell)
                paths.append(str(path))
        notebook = nbformat.v4.new_notebook(cells=cells)
        notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
        filename = "09-features-max.ipynb" if feature == "max K-ratio" else f'09-features-{feature.split("d ")[0]}d.ipynb'
        nbformat.write(notebook, folder / filename)
        links.append(f"- [{feature}: nine target/horizon sections](09-feature-scatter-catalogue/{filename})")
    (ARTIFACT_DIR / "catalogue-manifest.json").write_text(json.dumps({"separate_images": paths, "notebooks": len(links), "visual_review": "pending"}, indent=2))
    return "\n".join(links)


def robustness_report(data, models, stats, extensions):
    """Separate quarter, input-quality, baseline and missingness diagnostics."""
    table(extensions["missing_checks"], "Missing-input and maturity checks", "Synthetic adapter checks verify that absent long windows do not poison a usable short window and that future test rows cannot change fitting statistics. Actual partial-history forecasts are counted separately.")
    table(extensions["redundancy_support"], "Redundancy on paired and common cohorts", "Pairwise correlations use available inputs; the common cohort requires all six metrics at that lookback. Counts are per origin, averaged equally. Recorded-history age is archive coverage, not verified vault inception.")
    table(extensions["dependence"], "Non-overlapping forecasts and longer calendar blocks", "Select origins at least one target horizon apart, and also double the block length. Bands remain exploratory and require eight complete blocks; adjacent target windows can cross block boundaries.")
    table(extensions["target_attrition"], "Missing outcomes by recorded-history cohort", "Administrative censoring is separate from gaps, absent endpoints and undefined ratios. A disappeared observation is not a verified closure or cash payout. These missing outcomes can bias surviving-row comparisons; terminally censored targets and unknown proceeds are not filled.")
    table(extensions["baseline_pairs"], "Same-row comparisons with simple forecasts", "Existing + K errors are paired with each baseline on identical target-valid observations. A negative change improves MAE; target persistence can have different coverage.", limit=40)
    table(extensions["calibration"], "Forecast calibration on the evaluation sample", "An ideally calibrated model has slope one and intercept zero on the modelling scale. These are retrospective diagnostics, not an extra fitted calibration used for forecasting.", limit=24)
    table(extensions["leave_vault"], "Does one vault drive the K increment?", "The range recomputes paired IC after removing each vault in turn. A sign change indicates concentration; these are sensitivity estimates, not independent replications.")
    table(extensions["leave_block"], "Does one calendar block drive the K increment?", "Remove each complete horizon-length block from the block-average effect. Three 30-day blocks remain too little evidence for a precise confidence interval.")
    table(extensions["endpoint_convention"], "K fitted-endpoint convention sensitivity", "Both conventions use the same actual target paths. The primary includes the anchor; the ends-only convention ignores the effect of the first return. High correlation does not make the definitions identical.")
    table(extensions["path_placebo"], "Whole-vault-path negative control", "Eight fixed vault-path permutations preserve calendar dates and serial dependence. Original and shuffled IC use matched finite rows per draw. This is descriptive, not a p-value.", limit=24)
    paired = stats["paired_dates"]
    paired = paired[paired.old.eq("Existing") & paired.phase.eq(0) & paired.delay.eq(0) & ~paired.source].copy()
    paired["quarter"] = paired.origin_at.dt.to_period("Q").astype(str)
    for target in TARGETS:
        q = paired[paired.target.eq(target)].groupby(["horizon", "quarter"]).agg(delta=("delta_IC", "mean"), n=("delta_IC", "count")).reset_index()
        grid = q.pivot(index="horizon", columns="quarter", values="delta").reindex(index=HORIZONS, columns=list(QUARTERS))
        counts = q.pivot(index="horizon", columns="quarter", values="n").reindex_like(grid)
        show(heatmap(grid, f"{target}: K incremental IC by origin quarter", f"quarter-{target}", "Rows=horizon days; n=paired defined origins. Blank quarters lack supported models/mature labels.", vmin=-0.1, vmax=0.1, counts=counts), target + " incremental prediction across quarters", "Quarter changes show whether an apparent K contribution is stable. No model is selected or refitted using these evaluation differences.")
        f = stats["feature_summary"]
        rows = []
        for days in (30, 60, 90, 180):
            for metric in ("K-ratio", "weekly K-ratio"):
                values = f[f.period.eq("2026") & f.horizon.eq(30) & f.target.eq(target) & f.feature.eq(f"{days}d {metric}")]
                rows.append({"days": days, "sampling": metric, "IC": values.mean_IC.iloc[0] if len(values) else np.nan, "count": values.defined_origins.iloc[0] if len(values) else 0})
        grid = pd.DataFrame(rows).pivot(index="days", columns="sampling", values="IC")
        counts = pd.DataFrame(rows).pivot(index="days", columns="sampling", values="count")
        show(heatmap(grid, f"30-day future {target}: daily versus weekly K inputs", f"weekly-{target}", "n=defined origins; cohorts differ here; matched-row companion follows.", counts=counts), target + " and daily versus weekly K", "Weekly fits use actual seven-day-spaced marks, 365/7 frequency and spans 28/56/84/175 days for nominal 30/60/90/180. See the matched-row companion; raw K magnitudes are not interchangeable.")
        bins = stats["bins"]
        bins = bins[(bins.origin_at >= START) & bins.horizon.eq(30) & bins.target.eq(target)]
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        for feature, g in bins.groupby("feature"):
            grouped = g.groupby("quintile").mean_target.mean()
            ax.plot(grouped.index, grouped.values, marker="o", label=feature)
        ylabel = "Mean 30-day log return (CAGR modelling scale)" if target == "CAGR" else f"Mean realised 30-day {target}"
        ax.set_title(f"30-day future {target}: historical K quintiles\n{PERIOD}", fontsize=11, pad=12)
        ax.set_xlabel("Within-origin historical K quintile (5 = highest)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(1, 6))
        ax.axhline(0, color="#94a3b8", linewidth=1)
        ax.grid(alpha=0.15)
        ax.legend(fontsize=9)
        fig.tight_layout()
        show(save(fig, f"quintiles-{target}"), target + " outcomes across historical K quintiles", "Quintiles use tie-aware within-date ranks, then average each origin equally. Empty tied bins stay empty. Window curves have different vault/date populations; use the matched-row companion to compare lookbacks. CAGR is shown as mean horizon log return, with no misleading conversion to a mean annualised CAGR.")
    components = extensions["volatility_components"]
    for outcome in ("mean_return", "volatility"):
        selected = components[components.future_component.eq(outcome)]
        grid = selected.pivot(index="feature", columns="horizon", values="mean_IC").reindex(columns=HORIZONS)
        counts = selected.pivot(index="feature", columns="horizon", values="defined_origins").reindex_like(grid)
        show(heatmap(grid, "Future daily " + outcome.replace("_", " ") + " predictability", f"component-{outcome}", "These two component diagnostics distinguish return information from persistence of volatility/marking smoothness.", counts=counts), "Predicting future " + outcome.replace("_", " "), "IC ranks the realised daily mean or daily volatility within each origin. A predictable denominator can make Sharpe/K predictable without reliably forecasting profitable growth.")


def write_findings(stats, models, data, extensions=None, feedback=None):
    """Generate every empirical verdict from the saved result tables."""
    pairs = stats["paired_summary"]
    p = pairs[pairs.old.eq("Existing") & pairs.phase.eq(0) & pairs.delay.eq(0) & ~pairs.source]
    positive = int(p.mean_delta_IC.gt(0).sum())
    lines = ["# Experiment 09 — K-ratio feature forecast findings", "", f"Default period: **{PERIOD}**. In-place post-review amendment; original results archived separately. No data refresh or portfolio-rule change.", "", "## Key new insights", "", f"All historical metrics and realised targets now use causal daily forward fill; the unchanged archive and pre-fill results are preserved in `09-before-sparse-fill`. Adding six K inputs (30/60/90/180/360 days and max recorded history) improves primary mean rank IC in **{positive} of {len(p)}** supported target/horizon comparisons. This is a measured result of fixed amended models on previously researched history, not a general claim about K or an untouched holdout.", ""]
    for row in p.itertuples(index=False):
        band = f"Exploratory block band [{row.lower_block_band:+.3f}, {row.upper_block_band:+.3f}]." if np.isfinite(row.lower_block_band) else "Too few blocks for an uncertainty band."
        lines.append(f"- **{row.horizon}-day {row.target}:** Existing/Existing + K rank IC {row.old_mean_IC:.3f}/{row.new_mean_IC:.3f}; delta {row.mean_delta_IC:+.3f}; modelling-scale MAE change {row.MAE_change_fraction:+.1%}; {row.paired_origins} origins, {row.calendar_blocks} complete blocks. {band}")
    if not p.horizon.eq(90).any():
        lines.append("- **90 days:** no supported paired forecast comparison. Illustrative forecasts and descriptive feature relationships do not establish model skill.")
    lines += ["", "## One-year and all-history amendment", "", "One year follows the existing 360-day convention. Max uses calendar-day NAV from the first actual positive mark through T−1, causally carrying prices over gaps, with at least three fitted marks and no backfill or gap compression. Recorded history is not certified inception. Short-window ablations keep shared missingness controls fixed, so the longer K values can be assessed separately from history availability. The previous four-window run is archived under `09-before-long-k`.", ""]
    for row in stats["feature_coverage"].query('feature in ["360d K-ratio", "max K-ratio"]').itertuples(index=False):
        lines.append(f"- **{row.feature}:** {row.finite_features:,}/{row.observed_anchor_rows:,} supported-anchor rows have a finite input ({row.coverage:.1%}).")
    durations = data["features"]
    durations = durations.loc[durations.origin_at.ge(START) & durations.phase.eq(0) & durations.anchor_supported & durations["max K-ratio"].notna(), "max days"]
    lines.append(f"- **Available max durations:** {durations.min():.0f}–{durations.max():.0f} days, median {durations.median():.0f} days; {int(durations.ge(180).sum()):,} of {len(durations):,} finite max rows span at least 180 days. Max is not necessarily a longer input for young vaults. One-year availability is measured separately above; young vaults retain usable shorter inputs.")
    longer = stats["long_k_summary"]
    longer = longer[longer.phase.eq(0) & longer.delay.eq(0) & ~longer.source]
    for row in longer.itertuples(index=False):
        lines.append(f"- **{row.new}, {row.horizon}-day {row.target}:** versus four-window K, same-row rank IC {row.old_mean_IC:.4f} → {row.new_mean_IC:.4f}; delta {row.mean_delta_IC:+.4f}; MAE change {row.MAE_change_fraction:+.1%}; {row.paired_origins} origins, {row.calendar_blocks} blocks.")
    lines += ["", "## Sensitivities", ""]
    for old in ("Compact", "Rank existing", "Activity existing", "Compact controls existing", "Existing complete-case", "Existing missing=False"):
        g = pairs[pairs.old.eq(old) & pairs.phase.eq(0) & pairs.delay.eq(0) & ~pairs.source]
        if len(g):
            lines.append(f"- **{old}:** positive K delta in {int(g.mean_delta_IC.gt(0).sum())}/{len(g)} supported cells; observed delta range {g.mean_delta_IC.min():+.3f} to {g.mean_delta_IC.max():+.3f}. This range is not a confidence bound.")
            if "complete-case" in old:
                for row in g.itertuples(index=False):
                    lines.append(f"  - {row.horizon}-day {row.target}: {row.paired_origins} target-valid paired origins, {row.defined_IC_origins} defined IC origins. Sparse later-calendar subsets cannot confirm incremental skill.")
        else:
            lines.append(f"- **{old}:** no supported paired comparison.")
    for (h, t), g in pairs[pairs.old.eq("Existing") & ~pairs.source].groupby(["horizon", "target"]):
        lines.append(f"- **{h}-day {t}, cadence/delay:** {int(g.mean_delta_IC.gt(0).sum())}/{len(g)} positive point estimates; range {g.mean_delta_IC.min():+.3f} to {g.mean_delta_IC.max():+.3f}.")
    lines += ["", "## Baselines and calibration", ""]
    if extensions is not None:
        for row in extensions["baseline_pairs"].itertuples(index=False):
            lines.append(f"- **{row.horizon}-day {row.target} versus {row.baseline}:** same-row modelling-scale MAE change {row.MAE_change_fraction:+.1%} ({row.paired_origins} origins).")
    if feedback is not None:
        for row in feedback["before_after"].query('arm == "Existing + K"').itertuples(index=False):
            lines.append(f"- **{row.horizon}-day {row.target}, original versus amended:** same-row MSE {row.before_MSE:.3e} → {row.after_MSE:.3e}; IC {row.before_IC:.3f} → {row.after_IC:.3f}.")
        extra = feedback["extrapolation"]
        extra = extra[extra.arm.eq("Existing + K") & extra.supported]
        for row in extra.itertuples(index=False):
            lines.append(f"- **{row.horizon}-day {row.target}, amended prediction range:** [{row.min_prediction:.3e}, {row.max_prediction:.3e}]; output bound applied to {row.output_clipped_fraction:.1%} of forecasts.")
        skill = feedback["cohort_skill"]
        gate = skill[skill.cohort.eq("Current-policy gate") & skill.arm.isin(["Existing", "Existing + K"])]
        for (h, t), g in gate.groupby(["horizon", "target"]):
            old = g[g.arm.eq("Existing")]
            new = g[g.arm.eq("Existing + K")]
            if len(old) and len(new):
                lines.append(f"- **Current-policy gate, {h}-day {t}:** paired K IC delta {new.mean_IC.iloc[0]-old.mean_IC.iloc[0]:+.3f}; {int(new.defined_IC_origins.iloc[0])} defined origins. Membership is caveated, not historically certified.")
    if feedback is not None:
        lines += ["", "## Matched lookback and sampling evidence", ""]
        m = feedback["matched_lookbacks"]
        for row in m[(m.horizon == 30) & m.comparison.eq("Lookbacks 30/60/90")].itertuples(index=False):
            lines.append(f"- **{row.feature} → 30-day {row.target}:** common-row IC {row.mean_IC:.3f}; {row.defined_origins} defined origins and {row.paired_rows:,} rows, identical within this lookback comparison.")
        u = feedback["universe_audit"].iloc[-1]
        lines.append(f"- **Snapshot conditioning:** {u.omitted_addresses_seen} of {u.archived_addresses_seen} already archived addresses are outside the selected universe at {u.as_of.date()}; this is a conditional study, not a complete historical-vault evaluation.")
    lines += [
        "",
        "## Method and robustness",
        "",
        "All continuous model inputs use training-only median-absolute asinh scales and explicit training-range/±5z bounds. CAGR inputs use exact lookback log returns. Sharpe fits a fixed scaled pseudo-Huber objective; K fits fold-scaled asinh targets. Level predictions use training 0.5%–99.5% target bounds before inverse transformation; labels and calculation tails remain untrimmed. Baselines are unbounded. Ranking companions have IC only, not level error.",
        "",
        "Complete-case uses the fixed 30/60/90-day inventory, while partial history is measured over the supported ≤180-day inventory. Archive age is not inception. Missing=True is mechanical support for usable shorter inputs; same-row cohort errors separately assess usefulness. Zero-fill keeps shared indicators and is not a legacy selector replay.",
        "",
        "The low-activity sensitivity requires max(4, ceil(window/2)) non-zero returns for Sharpe/K windows. Actual unchanged marks are valid primary observations. Discrete Sharpe/K stripes can reflect inactivity or precision; they do not prove stale prices. Activity sensitivity predictions use historical information only; realised future activity defines label validity afterwards, not forecast or entry eligibility. Calendar mark coverage and attrition are reported without inventing payouts.",
        "",
        "Cadence phases, one-day delay, source-filled feature prices, quarterly stability, matched lookbacks/weekly sampling, calendar dependence, leave-vault/leave-block checks and explicit missing-outcome scenarios are exploratory. Bands do not eliminate dependence; the measured number of usable calendar blocks determines horizon support.",
        "",
        "Current snapshot identities are not a certified historical listing. Zero assets/zero supply marks do not establish −100% investor loss. Inception, historical universe completeness and actual receipt/publication clocks remain unverified; no prospective collection pipeline is claimed. No strategy performance or deployment decision follows.",
        "",
        "## Reproducibility",
        "",
        "[Executed notebook](09-research-k-ratio-feature-forecasts.ipynb) · [Amendment](09-k-ratio-feature-forecast-amendment.md) · [Original implementation review](09-k-ratio-feature-forecast-implementation-review.md). Original code/notebook/headline outputs are preserved in the ignored `09-before-robust-amendment` namespace; current results and folds are under `09`.",
        "",
    ]
    text = "\n".join(lines)
    (ROOT / "09-k-ratio-feature-forecast-findings.md").write_text(text)
    return text


def freeze_design(data):
    """Predeclare the next confirmation origins and minimum maturity dates."""
    first = START + pd.Timedelta(days=int(np.ceil((pd.Timestamp("2026-10-10") - START).days / 4)) * 4)
    rows = []
    for h in HORIZONS:
        end = first + pd.Timedelta(days=8 * h)
        last = first + pd.Timedelta(days=4 * ((8 * h - 1) // 4))
        rows.append({"horizon": h, "first_origin": first, "origin_window_end_exclusive": end, "last_scheduled_origin": last, "earliest_all_labels_mature": last + pd.Timedelta(days=h), "required_complete_blocks": 8, "block_days": h})
    frame = pd.DataFrame(rows)
    record = {
        "frozen_on": "2026-10-10",
        "cadence_days": 4,
        "refit": "monthly, expanding, strictly matured labels",
        "arms": ["Existing", "Existing + K"],
        "protocol_amendment": "09-k-ratio-feature-forecast-amendment.md",
        "preprocessing": "CAGR log inputs; continuous fold-local asinh; training range/±5z bounds; output q0.005/q0.995 bounds",
        "Sharpe_loss": "scaled pseudo-Huber delta 1.35",
        "ranking_companion": "within-origin ranks, IC only",
        "alpha": 10,
        "missing": True,
        "K_inputs": K_MAIN,
        "targets": TARGETS,
        "horizons": HORIZONS,
        "minimum_evaluation_blocks": 8,
        "archive": data["manifest"],
        "helper_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob("k_ratio_*.py")},
        "confirmation_windows": json.loads(frame.to_json(orient="records", date_format="iso")),
        "required_future_record_fields": ["vault_address", "as_of", "observed_at", "received_at", "share_price", "schema_version", "archive_hash"],
        "collection_pipeline_status": "Not implemented by this research notebook; recording receipt clocks is required before genuine prospective inference.",
        "limitations": "Dates assume uninterrupted observations, supported paired fits and eight complete blocks; they do not guarantee power. All later data must retain actual observation and publication provenance. No new archive was fetched.",
    }
    (ARTIFACT_DIR / "prospective-design.json").write_text(json.dumps(record, indent=2, default=str))
    return frame


def feedback_report(data, models, stats, extensions, feedback):
    """Show the corrected comparisons with explicit support and period context."""
    primary = stats["paired_summary"]
    primary = primary[primary.phase.eq(0) & primary.delay.eq(0) & ~primary.source]
    table(primary[["old", "horizon", "target", "paired_origins", "defined_IC_origins", "old_mean_IC", "new_mean_IC", "mean_delta_IC", "MAE_change_fraction", "calendar_blocks"]], "Robust level models and ranking companions", "Primary and other partial-history pairs add six K inputs, including year and max; complete-case deliberately retains 30/60/90-day inputs. Rank arms have no level MAE. Activity arms are fixed sensitivities.", limit=60)
    for target in TARGETS:
        selected = primary[primary.target.eq(target)]
        grid = selected.pivot(index="old", columns="horizon", values="mean_delta_IC").reindex(columns=HORIZONS)
        count = selected.pivot(index="old", columns="horizon", values="paired_origins").reindex_like(grid)
        show(heatmap(grid, target + ": K increment across amended methods", "feedback-arms-" + target, "Same rows within each pair; n=target-valid paired origins; sparse complete-case results are not confirmation.", vmin=-0.03, vmax=0.03, counts=count), target + " and alternative forecast methods", "Positive values improve rank IC. Sensitivities are fixed comparisons, not independently selected winners; grey cells are unsupported.")
    table(feedback["before_after"], "Original versus corrected forecasts on identical rows", "The pre-review run is archived. Changes include robust inputs, prediction bounds, robust Sharpe loss and the year/max K amendment. The archive is unchanged; the separate four-window comparison isolates longer K values.", limit=30)
    table(extensions["calibration"].query('arm in ["Existing", "Existing + K", "Compact", "Compact + K", "Quality/age"]'), "Amended model calibration", "Slopes use equal-origin weights in the modelling units; 1 is the ideal reference, not a pass criterion. Constant forecasts have no meaningful within-date calibration slope.", limit=40)
    extra = feedback["extrapolation"]
    table(extra[extra.arm.eq("Existing + K")], "Full prediction ranges and applied bounds", "Includes illustrative unsupported models. Unlike chart cropping, these fixed bounds are part of the model. No calculation tail is removed; baselines are unbounded.")
    skill = feedback["cohort_skill"]
    names = ["All observed", "Recorded history 30–89d", "Recorded history 90–179d", "Recorded history ≥180d", "Current-policy gate", "Gate and deposit feasible"]
    for h in (7, 30):
        for target in TARGETS:
            a = skill[skill.horizon.eq(h) & skill.target.eq(target) & skill.cohort.isin(names)]
            grid = a.pivot(index="cohort", columns="arm", values="mean_IC").reindex(index=names)
            grid = grid.dropna(axis=1, how="all")
            counts = a.pivot(index="cohort", columns="arm", values="defined_IC_origins").reindex_like(grid)
            show(heatmap(grid, f"{h}-day {target}: same-row cohort forecast skill", f"feedback-cohort-{h}-{target}", "Shared rows including table baselines; n=defined origins. Constant predictions have no rank IC.", counts=counts, vmin=-0.3, vmax=0.3, barlabel="Mean within-origin rank IC"), f"{h}-day {target}: cohort discrimination", "Young refers to recorded history, not inception. Cohort differences are descriptive, not causal; sparse cross-sections have undefined IC.")
            table(a[["cohort", "arm", "MAE", "MSE", "paired_rows", "origins", "defined_IC_origins"]], f"{h}-day {target}: cohort error and support", "Errors use the same rows for every model within each cohort. CAGR uses horizon log return; K uses fold-scaled asinh.", limit=45)
    matched = feedback["matched_lookbacks"]
    table(matched[matched.horizon.eq(30)], "Lookback and weekly comparisons on shared rows", "Every comparison fixes both dates and vaults across its displayed features. Actual weekly spans are 28/56/84/175 days; availability is not confused with window performance.", limit=50)
    for target in TARGETS:
        a = matched[matched.horizon.eq(30) & matched.target.eq(target) & matched.comparison.str.startswith("Daily/weekly")].copy()
        a["days"] = a.feature.str.extract(r"^(\d+)d")[0].astype(int)
        a["sampling"] = np.where(a.feature.str.contains("weekly"), "Weekly", "Daily")
        grid = a.pivot(index="days", columns="sampling", values="mean_IC")
        counts = a.pivot(index="days", columns="sampling", values="paired_rows").reindex_like(grid)
        show(heatmap(grid, "30-day " + target + ": matched daily and weekly K", "feedback-weekly-" + target, "n=total paired vault/origin rows, same within each row. Cross-row populations can still differ.", counts=counts, vmin=-0.3, vmax=0.3, barlabel="Mean within-origin rank IC"), target + " and matched daily/weekly sampling", "Same rows remove the main sampling availability confound. Different true spans and fitted point counts remain explicit.")
    for target in TARGETS:
        q = stats["quarterly"]
        q = q[q.quarter.str.startswith("2026") & q.horizon.eq(30) & q.target.eq(target) & q.feature.isin(K_MAIN)]
        grid = q.pivot(index="feature", columns="quarter", values="mean_IC").reindex(index=K_MAIN)
        counts = q.pivot(index="feature", columns="quarter", values="defined_origins").reindex_like(grid)
        show(heatmap(grid, "30-day " + target + ": individual K quarter stability", "feedback-feature-quarter-" + target, "n=defined origins; missing history and late label censoring can remove entire quarters.", counts=counts, vmin=-0.3, vmax=0.3, barlabel="Mean within-origin rank IC"), target + " and individual K stability", "This displays the previously unreported quarterly feature evidence. Features with longer lookbacks first become available in later quarters.")
    for h in HORIZONS:
        attr = feedback["attrition"]
        attr = attr[attr.horizon.eq(h) & attr.cohort.isin(["All observed", "Past flat ≥80%", "Past active ≤20% flat", "Recent daily coverage <95%", "Coverage disappearance", "Currently permanently closed (snapshot)", "Currently leader-disabled (snapshot)"])]
        table(attr, f"{h}-day activity and archive-gap label attrition", "Unknown outcomes stay unknown. Current closure metadata is retrospective cohort membership, not point-in-time truth. Coverage disappearance is not verified bankruptcy. Genuine unchanged NAV remains valid.", limit=25)
    table(feedback["missing_scenarios"], "Missing-outcome scenario sensitivity", "Not identified bounds: impose −50%/+50% or −99%/+100% on missing non-censored horizon outcomes, retaining observed returns. Equal-origin means expose how conclusions depend on unverifiable assumptions.")
    marks = feedback["calendar_marks"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(marks.date, marks.actual_vault_marks, color="#2563eb")
    ax.set_title("Actual daily archive coverage\n" + PERIOD, fontsize=11)
    ax.set_ylabel("Vaults with an actual positive daily NAV mark")
    ax.set_xlabel("UTC date")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    show(save(fig, "feedback-calendar-marks"), "Calendar-wide observation coverage", "Drops can indicate collection gaps or changes in the observed population; this chart alone cannot attribute a specific outage. Snapshot size includes vaults not yet observed at earlier dates.")
    table(feedback["zero_nav"], "Zero NAV observations and terminal interpretation", "Zero assets and zero supply identify an empty or undefined-share-price state, not a verified full investor loss. No terminal payout is fabricated.")
    for h in HORIZONS:
        numerical = feedback["numerical_quality"]
        table(numerical[numerical.horizon.eq(h)], f"{h}-day precision and near-linearity sensitivity", "Descriptive cohort screens: historical log-NAV RMS ≥1e−8 and K OLS residual/total variance ≥1e−6; future Sharpe/K daily volatility ≥1e−8. The paired rows reuse the fitted forecasts; future quality only defines evaluable labels, never entry eligibility. These thresholds are sensitivities, not certified price-quality standards.", limit=20)
    table(feedback["universe_audit"], "Archived population versus selected snapshot identities", "Counts are addresses already observed in this archive by each date, not an independent historical listing. Metadata start_date equals first_updated_at, and deployment dates are absent, so true inception cannot be certified.")
    for target in TARGETS:
        table(feedback["distribution"].query("target == @target"), "30-day " + target + ": outcome distributions by historical input quintile", "Within-origin tie-aware quintiles; average date medians and 10th/90th percentiles. CAGR uses horizon log return. Different features may have different available cohorts.", limit=25)
    f = data["features"]
    f = f[(f.origin_at >= START) & f.phase.eq(0) & f.anchor_supported]
    cal = []
    for d in (30, 90, 180):
        floor = f[f"{d}d Calmar"]
        raw = f[f"{d}d Calmar unfloored"]
        cal.append({"days": d, "finite_floored": int(np.isfinite(floor).sum()), "finite_unfloored": int(np.isfinite(raw).sum()), "unfloored_median": raw.median(), "unfloored_p99": raw.quantile(0.99), "unfloored_max": raw.max()})
    table(pd.DataFrame(cal), "Unfloored Calmar tail and availability", "The existing Calmar floor is retained for compatibility. This diagnostic exposes the numerical tails; robust transforms and bounds act on all model inputs.")
