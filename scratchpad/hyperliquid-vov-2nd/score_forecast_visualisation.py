"""Compact, period-labelled visualisations for the forecast research notebook."""

import base64
import hashlib
import html
import json
import io
from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import SymmetricalLogLocator, NullLocator
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import HuberRegressor
from IPython.display import HTML, Image, Markdown, display

SHORT_PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
LONG_PERIOD = "2023-03-01 → 2026-10-05 (end exclusive, UTC)"
QUARTER_COLOURS = {"Q1": "#2563eb", "Q2": "#059669", "Q3": "#d97706", "Q4": "#dc2626"}
FOCAL_METHODS = ("v11", "blend_46d", "focal_four")


def method_records(data):
    """Normalise the registry without changing its scoring definitions."""
    registry = data["registry"]
    if isinstance(registry, dict):
        records = registry.get("methods", registry.get("configurations", registry))
        if isinstance(records, dict):
            return [dict(row, method_id=key) for key, row in records.items()]
        return records
    return registry


def method_name(data, method_id):
    """Resolve readable method names from the frozen registry."""
    row = next(r for r in method_records(data) if r["method_id"] == method_id)
    focal_names = {"v11": "v11 (legacy 45d)", "blend_46d": "Blend 46d (two inputs)", "focal_four": "Four inputs (180d CAGR + 30d Sortino)"}
    if method_id in focal_names:
        return focal_names[method_id]
    name = row.get("name", row.get("Configuration", method_id))
    if name.startswith("04 evaluated "):
        terms = row["recipe"]["terms"]
        detail = " + ".join(f"{t['coefficient']:.0%} {t['period']} {t['metric']}" for t in terms)
        name = f"04 {detail} · {row['missing_policy']}"
    return name


def intro(title, description, period=SHORT_PERIOD):
    """Introduce each element using the same reading order."""
    display(Markdown(f"### {title} — {period}\n\n{description}"))


def styled_table(frame, title, description, period=SHORT_PERIOD, collapsed=False):
    """Colour relationship and performance tables with explicit metric units."""
    if len(frame) > 36:
        description += f" Showing the first 36 of {len(frame):,} rows to keep the notebook renderable; the complete analysis remains in its cached dataframe."
        frame = frame.iloc[:36].copy()
    intro(title, description, period)
    frame = frame.reset_index(drop=True)
    formats = {}
    for c in frame:
        if pd.api.types.is_float_dtype(frame[c]):
            formats[c] = "{:.3f}"
            if any(word in str(c).lower() for word in ("cagr", "drawdown", "cash_weight", "cash weight", "loss_rate", "loss_probability", "return", "coverage", "fraction", "yield")) and "log" not in str(c).lower():
                formats[c] = "{:.2%}"
        if pd.api.types.is_datetime64_any_dtype(frame[c]):
            formats[c] = "{:%Y-%m-%d}"
        if "usd" in str(c).lower() or "(USD)" in str(c):
            formats[c] = "${:,.0f}"
    style = frame.style.format(formats, na_rep="—").hide(axis="index")
    colour = [c for c in frame if pd.api.types.is_numeric_dtype(frame[c]) and np.isfinite(frame[c].to_numpy(dtype=float, na_value=np.nan)).any() and any(word in str(c).lower() for word in ("mean_ic", "median_ic", "cagr", "sharpe", "drawdown", "brier", "mae", "loss_rate"))]
    if colour and len(frame):
        higher = [c for c in colour if not any(word in str(c).lower() for word in ("brier", "mae", "loss_rate"))]
        lower = [c for c in colour if c not in higher]
        if higher:
            style = style.background_gradient(subset=higher, cmap="RdYlGn", axis=0)
        if lower:
            style = style.background_gradient(subset=lower, cmap="RdYlGn_r", axis=0)
    style = style.set_table_styles(
        [
            {"selector": "th", "props": [("text-align", "left"), ("white-space", "normal")]},
            {"selector": "td", "props": [("padding", "5px 8px")]},
        ]
    )
    if collapsed:
        display(HTML(f'<details><summary>{html.escape(title)}</summary><div style="overflow-x:auto;max-width:100%">{style.to_html()}</div></details>'))
    else:
        display(HTML('<div style="overflow-x:auto;max-width:100%">' + style.to_html() + "</div>"))


def save_figure(fig, folder, name):
    """Save chart exports only under the ignored research artefact tree."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    fig.savefig(path, dpi=135, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def show_png(path, title, description, period=SHORT_PERIOD):
    """Keep chart headings separate from the saved raster output."""
    intro(title, description, period)
    display(Image(filename=str(path)))


def figure_style():
    """Apply a local, readable research style without global notebook warnings."""
    return plt.rc_context({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.18, "figure.facecolor": "white"})


def _safe_fit(x, y):
    good = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[good], np.asarray(y)[good]
    if len(x) < 3 or np.unique(x).size < 2 or np.ptp(x) < 1e-12:
        return None
    return np.polyfit(x, y, 1)


def _robust_fit(x, y):
    good = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[good], np.asarray(y)[good]
    if len(x) < 5 or np.unique(x).size < 2 or np.ptp(x) < 1e-12:
        return None
    model = HuberRegressor(max_iter=1000).fit(x.reshape(-1, 1), y)
    return model


def scatter_description(target, view, horizon):
    """Describe scale, support and trend interpretation for one target."""
    description = "X is the frozen vault score; Y is the realised outcome on causally filled daily NAV. Each dot is one eligible vault/forecast date, coloured by origin quarter. " "Scores and all fitted trends use every finite pair; repeated and overlapping observations are not independent. " "Black is the robust trend; purple shows score-bin medians, with interquartile ranges in the zoomed view. " "A bin needs at least 20 pairs and five origins to appear. These ranges describe outcomes, not confidence intervals. "
    if target == "future_cagr" and view == "focus":
        description += "The shared linear display range is −100% to +300% CAGR. Counts above that range are printed on the plot; " "the separate full-range chart immediately below shows those observations. Raw-CAGR OLS is shown only in that full-range audit because extremes can dominate it. "
    elif target == "future_cagr":
        description += "This signed-log audit shows every finite annualised CAGR, including extreme tails. The dashed raw-CAGR OLS line can be dominated by a few extremes. "
    else:
        description += "A signed-log Sharpe axis expands the ordinary range and retains every extreme. The dashed line is descriptive pooled OLS. "
    if horizon == 90:
        description += "Ninety-day 2026 relationships have too few independent windows for inferential claims."
    return description


def scatter_figure(data, method_id, horizon, frame, folder, period="2026", target="future_cagr", view="focus"):
    """Render one outcome on one axis, separating the useful range from tail audits."""
    text_period = SHORT_PERIOD if period == "2026" else LONG_PERIOD
    name = method_name(data, method_id)
    source = frame[np.isfinite(frame["score"]) & np.isfinite(frame[target])].copy()
    source["quarter_number"] = pd.to_datetime(source.origin_at).dt.quarter
    is_cagr = target == "future_cagr"
    factor = 100 if is_cagr else 1
    label = "Realised CAGR (%)" if is_cagr else "Realised Sharpe"
    scale = "zoomed linear view" if is_cagr and view == "focus" else "full range · signed-log scale"
    with figure_style():
        fig, ax = plt.subplots(figsize=(9.5, 6.3))
        title = f"{name} · {horizon}-day lookahead · {label}\n{scale}\n{text_period}"
        ax.set_title("\n".join(textwrap.wrap(title.split("\n")[0], 82)) + "\n" + "\n".join(title.split("\n")[1:]), fontsize=11, pad=35)
        for q in range(1, 5):
            group = source[source.quarter_number.eq(q)]
            if len(group):
                ax.scatter(group.score, group[target] * factor, s=13, alpha=0.48, c=QUARTER_COLOURS[f"Q{q}"], edgecolors="none", rasterized=True, label=f"Q{q} · {group.origin_at.nunique()} dates")
        x = source.score.to_numpy(dtype=float)
        y = source[target].to_numpy(dtype=float) * factor
        if len(source) and np.unique(x).size > 1:
            grid = np.linspace(float(x.min()), float(x.max()), 150)
            if not is_cagr or view == "full":
                fit = _safe_fit(x, y)
                if fit is not None:
                    predicted = np.polyval(fit, grid)
                    if is_cagr:
                        predicted = np.where(predicted >= -100, predicted, np.nan)
                    ax.plot(grid, predicted, "--", color="#64748b", lw=1.1, label="Pooled OLS")
            robust_target = source.future_log_return.to_numpy() if is_cagr else y
            robust = _robust_fit(x, robust_target)
            if robust is not None:
                predicted = robust.predict(grid.reshape(-1, 1))
                if is_cagr:
                    predicted = np.expm1(predicted * 365 / horizon) * 100
                ax.plot(grid, predicted, color="#111827", lw=2.2, label="Robust trend", zorder=4)
            buckets = pd.cut(source.score, np.linspace(0, 1, 11), include_lowest=True)
            grouped = source.assign(bucket=buckets).groupby("bucket", observed=True)
            medians = grouped.agg(score=("score", "median"), target=(target, "median"), pairs=(target, "size"), origins=("origin_at", "nunique"))
            medians["q25"] = grouped[target].quantile(0.25)
            medians["q75"] = grouped[target].quantile(0.75)
            supported = medians.pairs.ge(20) & medians.origins.ge(5)
            # Missing bins remain gaps; lines do not bridge unsupported regions.
            plotted = medians.where(supported)
            ax.plot(plotted.score, plotted.target * factor, "o-", color="#9333ea", lw=1.5, ms=5, label="Supported bin median", zorder=5)
            if is_cagr and view == "focus":
                good = medians[supported]
                ax.vlines(good.score, good.q25 * factor, good.q75 * factor, color="#9333ea", alpha=0.35, lw=2, zorder=3)
        elif not len(source):
            ax.text(0.5, 0.5, "No supported finite score/outcome pairs", ha="center", va="center", transform=ax.transAxes)
        ax.axhline(0, lw=0.9, color="#475569", alpha=0.7)
        ax.set_xlabel("Composite score (higher ranks first)")
        ax.set_ylabel(label)
        ax.set_xlim(-0.025, 1.025)
        ax.set_xticks(np.linspace(0, 1, 6))
        if is_cagr and view == "focus":
            ax.set_ylim(-105, 305)
            ax.set_yticks([-100, 0, 100, 200, 300])
            omitted = int((y > 300).sum())
            note = f"{omitted:,} / {len(source):,} pairs above +300%; shown in the separate full-range audit"
        else:
            ax.set_yscale("symlog", linthresh=25 if is_cagr else 3)
            locator = SymmetricalLogLocator(base=10, linthresh=25 if is_cagr else 3)
            locator.set_params(numticks=9)
            ax.yaxis.set_major_locator(locator)
            ax.yaxis.set_minor_locator(NullLocator())
            if is_cagr:
                ax.set_ylim(bottom=-105)
                # A very long positive tail compresses near-zero log ticks onto each other.
                exponent = int(np.ceil(np.log10(max(float(np.max(y)) if len(y) else 100, 100))))
                if exponent > 8:
                    step = max(2, int(np.ceil(exponent / 6)))
                    ax.set_yticks([0] + [10.0**e for e in range(step, exponent + 1, step)])
            else:
                # Shared per-horizon ranges prevent magnifying small differences between methods.
                limits = {7: (-50, 80), 30: (-18, 26), 90: (-10, 10)}
                ax.set_ylim(*limits[horizon])
                ax.set_yticks([v for v in [-40, -20, -10, -5, -2, 0, 2, 5, 10, 20, 40, 80] if limits[horizon][0] <= v <= limits[horizon][1]])
                from matplotlib.ticker import ScalarFormatter

                ax.yaxis.set_major_formatter(ScalarFormatter())
            note = "Every finite outcome shown; nonlinear vertical scale keeps extreme observations visible"
        rho = spearmanr(x, y).statistic if len(source) > 2 and np.unique(x).size > 1 and np.unique(y).size > 1 else np.nan
        support = f"{len(source):,} pairs · {source.origin_at.nunique()} dates · {source.pair_id.nunique()} vaults · pooled Spearman {rho:+.2f} (descriptive)"
        ax.text(0, 1.025, support, transform=ax.transAxes, fontsize=8.5, color="#475569")
        if horizon == 90:
            note += "\n90-day sample: descriptive only; insufficient independent windows"
        fig.text(0.5, 0.015, note, ha="center", fontsize=8, color="#475569")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False, fontsize=8.5)
        fig.tight_layout(rect=[0, 0.105, 1, 0.97])
        stem = f'{period}-{method_id}-h{horizon}-{"cagr" if is_cagr else "sharpe"}-{view}'
        return save_figure(fig, folder, stem)


def interactive_scatter(data, method_id, horizon, frame, target="future_cagr"):
    """Provide one zoomable target per chart with an informative initial range."""
    import plotly.graph_objects as go

    source = frame[np.isfinite(frame.score) & np.isfinite(frame[target])].copy()
    source["quarter_number"] = pd.to_datetime(source.origin_at).dt.quarter
    is_cagr = target == "future_cagr"
    factor = 100 if is_cagr else 1
    label = "Realised CAGR (%)" if is_cagr else "Realised Sharpe"
    fig = go.Figure()
    for q in range(1, 5):
        group = source[source.quarter_number.eq(q)]
        if group.empty:
            continue
        custom = np.column_stack([group.pair_id, pd.to_datetime(group.origin_at).dt.strftime("%Y-%m-%d")])
        fig.add_trace(go.Scattergl(x=group.score, y=group[target] * factor, mode="markers", marker=dict(color=QUARTER_COLOURS[f"Q{q}"], size=5, opacity=0.5), name=f"Q{q}", customdata=custom, hovertemplate="Pair %{customdata[0]} · %{customdata[1]}<br>Score %{x:.3f}<br>Outcome %{y:.3f}<extra></extra>"))
    if len(source) > 5:
        robust = _robust_fit(source.score.to_numpy(), source.future_log_return.to_numpy() if is_cagr else source[target].to_numpy())
        if robust is not None:
            grid = np.linspace(float(source.score.min()), float(source.score.max()), 150)
            y = robust.predict(grid.reshape(-1, 1))
            y = np.expm1(y * 365 / horizon) * 100 if is_cagr else y
            fig.add_trace(go.Scatter(x=grid, y=y, mode="lines", line=dict(color="#111827"), name="Robust trend"))
    fig.update_layout(title=f"{method_name(data, method_id)} · {horizon}-day lookahead · {label}<br><sup>{SHORT_PERIOD}</sup>", template="plotly_white", height=570, width=1000, legend=dict(orientation="h", y=-0.15), xaxis=dict(title="Composite score", range=[-0.025, 1.025]), yaxis=dict(title=label, range=[-105, 305] if is_cagr else [-10, 10]), margin=dict(t=110, b=90))
    return fig


def render_method_appendix(data, method_ids, folder, display_output=True):
    """Display each outcome/view as a separate native image with its own heading."""
    from score_forecast_statistics import join_method

    records = []
    for method_id in method_ids:
        name = method_name(data, method_id)
        for horizon in (7, 30, 90):
            frame = join_method(data, method_id, horizon, period="2026")
            for target, view in [("future_cagr", "focus"), ("future_cagr", "full"), ("future_sharpe", "full")]:
                path = scatter_figure(data, method_id, horizon, frame, folder, target=target, view=view)
                from PIL import Image as PILImage

                preview = io.BytesIO()
                with PILImage.open(path) as raster:
                    raster.thumbnail((1000, 1000), PILImage.Resampling.LANCZOS)
                    raster.convert("RGB").save(preview, format="JPEG", quality=82, optimize=True)
                label = "CAGR: zoomed view" if view == "focus" else "CAGR: full-range audit" if target == "future_cagr" else "Sharpe"
                if display_output:
                    intro(f"{name} · {horizon}-day lookahead · {label}", scatter_description(target, view, horizon))
                    display(Image(data=preview.getvalue(), format="jpeg", width=1000))
                records.append({"method_id": method_id, "lookahead_days": horizon, "outcome": target, "view": view, "period": "2026", "path": str(path), "pairs": int((np.isfinite(frame.score) & np.isfinite(frame[target])).sum()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "preview_sha256": hashlib.sha256(preview.getvalue()).hexdigest()})
    return records


def heatmap_figure(grid, title, folder, name, period=SHORT_PERIOD, centre=0, fmt="+.2f", limits=None, cmap="RdBu", annotations=None, note="", colour_label=""):
    """Render a single readable matrix with explicit limits and missing cells."""
    from matplotlib.ticker import MaxNLocator

    nrows, ncols = grid.shape
    labels = ["\n".join(textwrap.wrap(str(x), 48)) for x in grid.index]
    row_height = max(0.42, max((label.count("\n") + 1 for label in labels), default=1) * 0.23)
    with figure_style():
        fig, ax = plt.subplots(figsize=(11.5, max(4.5, nrows * row_height + 1.8)))
        values = grid.to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        if limits is None:
            extent = max(np.max(np.abs(finite)) if len(finite) else 1, 0.05)
            limits = (-extent, extent) if centre == 0 else (0, extent)
        palette = plt.get_cmap(cmap).copy()
        palette.set_bad("#e2e8f0")
        image = ax.imshow(np.ma.masked_invalid(values), aspect="auto", cmap=palette, vmin=limits[0], vmax=limits[1])
        ax.set_xticks(np.arange(ncols), [str(x).replace(" ", "\n", 1) for x in grid.columns], rotation=0, fontsize=9)
        ax.set_yticks(np.arange(nrows), labels, fontsize=9)
        ax.grid(False)
        for i in range(nrows):
            for j in range(ncols):
                value = values[i, j]
                clipped = np.isfinite(value) and (value < limits[0] or value > limits[1])
                text = annotations.iloc[i, j] if annotations is not None else format(value, fmt) if np.isfinite(value) else "No labels"
                if clipped:
                    text += "*"
                ax.text(j, i, text, ha="center", va="center", fontsize=8.5, color="white" if np.isfinite(value) and abs(value) > 0.65 * max(abs(limits[0]), abs(limits[1])) else "#111827")
        extends = "both" if len(finite) and ((finite < limits[0]).any() or (finite > limits[1]).any()) else "neither"
        bar = fig.colorbar(image, ax=ax, shrink=0.65, pad=0.02, extend=extends)
        bar.set_label(colour_label or "Value")
        bar.locator = MaxNLocator(nbins=5)
        bar.update_ticks()
        ax.set_title("\n".join(textwrap.wrap(title, 85)) + "\n" + period, fontsize=11, pad=18)
        if note:
            fig.text(0.5, 0.012, note, ha="center", fontsize=8, color="#475569")
        fig.tight_layout(rect=[0, 0.045 if note else 0, 1, 1])
        return save_figure(fig, folder, name)


def line_panels(frames, x, targets, title, folder, name, period=SHORT_PERIOD, labels=None, percent_targets=()):
    """Return one separate image per metric, with shared method colours and support."""
    paths = []
    colours = ["#2563eb", "#d97706", "#059669"]
    for target in targets:
        with figure_style():
            fig, ax = plt.subplots(figsize=(9.2, 5.5))
            for index, (label, frame) in enumerate(frames.items()):
                if target not in frame or x not in frame:
                    continue
                ordered = frame.sort_values(x).copy()
                if x == "bin":
                    order = {"1–6": 0, "7": 1, "8": 2, "9–10": 3, ">10": 4}
                    ordered = ordered.sort_values(x, key=lambda v: v.map(order))
                factor = 100 if target in percent_targets else 1
                supported = pd.Series(True, index=ordered.index)
                if "target_rows" in ordered:
                    supported &= ordered.target_rows.ge(20)
                if "origin_count" in ordered:
                    supported &= ordered.origin_count.ge(5)
                plotted = ordered[target].where(supported) * factor
                ax.plot(ordered[x], plotted, "o-", ms=5, lw=1.7, color=colours[index % len(colours)], label=label)
                if "target_rows" in ordered:
                    good = ordered[supported]
                    sizes = np.clip(np.sqrt(good.target_rows.to_numpy()) * 2, 20, 100)
                    ax.scatter(good[x], good[target] * factor, s=sizes, color=colours[index % len(colours)], zorder=3)
            axis_names = {"mean_score": "Mean score within fixed 0.1-wide score bins", "bin": "Candidate rank band (1 = highest score)", "delay_days": "Entry anchor delay (days)", "lookahead_days": "Lookahead (days)"}
            ax.set_xlabel(axis_names.get(x, x.replace("_", " ")))
            ax.set_ylabel((labels or {}).get(target, target.replace("_", " ")))
            if "probability" in target:
                ax.axhline(50, lw=0.9, ls="--", color="#64748b", label="50% loss frequency")
            else:
                ax.axhline(0, lw=0.9, color="#64748b")
            if x == "delay_days":
                ax.set_xticks([0, 1, 2])
            if x == "mean_score":
                ax.set_xlim(-0.025, 1.025)
                ax.set_xticks(np.linspace(0, 1, 6))
            if target == "mean_ic":
                ax.set_ylim(bottom=min(0, ax.get_ylim()[0]))
            caption = "Larger markers mean more supported outcome pairs; unsupported bins are gaps." if x in ("mean_score", "bin") else "Longer lookaheads have fewer matured dates; this is not a matched-sample comparison." if x == "lookahead_days" else ""
            ax.set_title(title + "\n" + (labels or {}).get(target, target.replace("_", " ")) + "\n" + period, fontsize=11, pad=16)
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=8.5, ncol=2)
            if caption:
                fig.text(0.5, 0.012, caption, ha="center", fontsize=8, color="#475569")
            fig.tight_layout(rect=[0, 0.1, 1, 1])
            paths.append(save_figure(fig, folder, name + "-" + target))
    return paths


def contact_sheets(paths, folder, columns=3, rows=4):
    """Create readable preview sheets covering every saved chart for visual review."""
    from PIL import Image as PILImage, ImageDraw

    paths = list(dict.fromkeys(map(str, paths)))
    pages = []
    width, height = 680, 370
    for start in range(0, len(paths), columns * rows):
        page = PILImage.new("RGB", (columns * width, rows * (height + 28)), "white")
        draw = ImageDraw.Draw(page)
        for offset, path in enumerate(paths[start : start + columns * rows]):
            img = PILImage.open(path).convert("RGB")
            img.thumbnail((width, height))
            x, y = offset % columns * width, offset // columns * (height + 28)
            page.paste(img, (x + (width - img.width) // 2, y))
            draw.text((x + 5, y + height + 4), Path(path).name[:95], fill="#111827")
        dest = Path(folder) / f"contact-{start // (columns * rows):03d}.png"
        page.save(dest)
        pages.append(dest)
    return pages
