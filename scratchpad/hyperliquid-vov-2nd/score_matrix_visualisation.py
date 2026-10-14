"""Compact notebook output and parameter-space views for experiment 04."""

from contextlib import contextmanager, redirect_stdout, redirect_stderr
import hashlib
import colorsys
import html
import io
import json
import re
import sys
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import HTML, Markdown, display

from tradeexecutor.analysis.grid_search import render_grid_search_result_table, visualise_heatmap_2d

SIZING = ("equal", "score", "inverse_variance")
SIZING_NAMES = {"equal": "Equal", "score": "Score", "inverse_variance": "Inverse variance"}
FAMILY_ORDER = ("CAGR matrix", "Sharpe matrix", "50/50 blend", "60/40 blend", "Dense equal matrix")
FAMILY_COLOURS = dict(zip(FAMILY_ORDER, ("#2563eb", "#9333ea", "#059669", "#d97706", "#64748b")))
FAMILY_COLOURS.update({"Original v11": "#111827", "Near-v6 360/46 legacy": "#be185d"})
PERCENT_METRICS = {"CAGR", "Max DD", "Maximum drawdown", "Mean cash weight", "Coverage"}


class _StatusStream(io.TextIOBase):
    """Replace accumulating stdout with one periodically updated display."""

    def __init__(self, title, handle):
        self.title = title
        self.handle = handle
        self.last_update = 0.0
        self.latest = ""

    def write(self, text):
        if text.strip():
            self.latest = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text).strip()[-220:]
            if time.monotonic() - self.last_update >= 10:
                message = f"{self.title}: {self.latest}"
                self.handle.update({"text/plain": message, "text/html": f"<small>{html.escape(message)}</small>"}, raw=True)
                self.last_update = time.monotonic()
        return len(text)

    def flush(self):
        pass


class _ProgressStderr(io.TextIOBase):
    """Compact tqdm's stderr progress while passing through real diagnostics."""

    def __init__(self, status, original):
        self.status = status
        self.original = original
        self.last_was_progress = False

    def write(self, text):
        if re.search(r"(?:^|\r)[^\n]*\d{1,3}%\|[^\n]*\d+/\d+", text):
            self.last_was_progress = True
            return self.status.write(text)
        if not text.strip() and self.last_was_progress:
            return len(text)
        self.last_was_progress = False
        return self.original.write(text)

    def flush(self):
        self.original.flush()


@contextmanager
def compact_output(title):
    """Keep live execution observable without retaining progress logs.

    Table and chart displays remain visible. Only recognised tqdm bars are
    redirected on stderr; warnings and failures remain available for inspection.
    """
    message = f"{title} — running"
    handle = display({"text/plain": message, "text/html": f"<small>{html.escape(message)}</small>"}, raw=True, display_id=True)
    stream = _StatusStream(title, handle)
    try:
        with redirect_stdout(stream), redirect_stderr(_ProgressStderr(stream, sys.stderr)):
            yield
    except BaseException:
        handle.update({"text/plain": f"{title} — failed", "text/html": f"<small>{html.escape(title)} — failed</small>"}, raw=True)
        raise
    else:
        message = f"{title} — complete"
        handle.update({"text/plain": message, "text/html": f"<small>{html.escape(message)}</small>"}, raw=True)


def chart_intro(title, description, period):
    """Give every chart a visible Markdown subheading and reading guide."""
    display(Markdown(f"### {title} — {period}\n\n{description}"))


def with_backtest_period(fig, period):
    """Require an explicit backtest window in the saved figure title."""
    fig.update_layout(title=dict(text=f"{fig.layout.title.text}<br><sup>Backtest: {period}</sup>"))
    return fig


def show_static(fig, period):
    """Respect the chart's size and label the requested backtest window."""
    with_backtest_period(fig, period)
    fig.show(width=fig.layout.width, height=fig.layout.height)


def collapsed_table(frame, title):
    """Retain supporting evidence without expanding it by default."""
    display(HTML(f"<details><summary>{html.escape(title)}</summary>{frame.to_html(index=False)}</details>"))


def present_table(element, title, description, period, collapsed=False):
    """Present every report table as a subheading, reading guide and table."""
    chart_intro(title, description, period)
    if collapsed:
        collapsed_table(element, title)
    else:
        display(element)


def profile_name(profile, recipes=None):
    """Replace content hashes with the recorded clipping recipe."""
    recipe = (recipes or {}).get(profile)
    if recipe and len({c["profile"] for c in recipe}) == 1:
        return recipe[0]["profile"]
    return " + ".join(f'{c["mass"]:.0%} {c["profile"]}' for c in recipe) if recipe else profile


def metric_table(frame, caption, recipes=None):
    """Use the existing grid-search table renderer and metric colour gradients."""
    table = frame.copy().rename(columns={"Maximum drawdown": "Max DD", "Mean fold CAGR": "CAGR", "Mean fold Sharpe": "Sharpe", "Worst fold drawdown": "Max DD"})
    assert table.columns.is_unique
    if "Profile" in table:
        table["Profile"] = table.Profile.map(lambda p: profile_name(p, recipes))
    if "Sizing" in table:
        table["Sizing"] = table.Sizing.map(SIZING_NAMES)
    if "CAGR" in table and "Max DD" in table and "Calmar" not in table:
        table["Calmar"] = table.CAGR / table["Max DD"].abs().replace(0, np.nan)
    style = render_grid_search_result_table(table, calmar=True)
    cols = [c for c in ("CAGR", "Sharpe", "Sortino", "Max DD", "Calmar") if c in table]
    style = style.background_gradient(subset=cols, cmap="RdYlGn", axis=0)
    extra = {c: "{:.1%}" if c == "Mean cash weight" else "{:.2%}" for c in PERCENT_METRICS if c in table}
    extra.update({c: "{:.2f}" for c in ("Sharpe", "Sortino", "Calmar") if c in table})
    extra.update({c: "{:.0f}" for c in ("Positions", "Trades", "Active cells", "Iteration") if c in table})
    extra.update({c: "${:,.0f}" for c in table if "(USD)" in str(c)})
    style = style.format(extra, na_rep="—").set_caption(caption)
    return style.set_table_styles(
        [
            {"selector": "caption", "props": [("text-align", "left"), ("font-weight", "bold"), ("padding", "8px 0")]},
            {"selector": "th", "props": [("text-align", "left"), ("white-space", "normal")]},
            {"selector": "td", "props": [("padding", "5px 8px")]},
        ],
        overwrite=False,
    )


def search_table(rows, caption):
    """Show the sparse search's actual performance once per column."""
    frame = pd.DataFrame(rows)
    columns = [c for c in ("Feature", "Search objective", "Iteration", "Active cells", "Sizing", "Missing", "Profile", "Mean fold CAGR", "Mean fold Sharpe", "Worst fold drawdown", "Compression passes") if c in frame]
    return metric_table(frame[columns].reset_index(drop=True), caption)


def unique_factorial(frame, families, recipes=None):
    """Collapse repeated matrix families before drawing the search space."""
    order = {family: i for i, family in enumerate(FAMILY_ORDER)}
    out = frame.copy()
    out["_order"] = out.Family.map(order).fillna(99)

    def signature(family):
        weights, profile = families[family]
        recipe = (recipes or {}).get(profile)
        if recipe and len({c["profile"] for c in recipe}) == 1:
            profile = recipe[0]["profile"]
        return json.dumps({"weights": list(np.asarray(weights).round(10)), "profile": profile}, sort_keys=True)

    out["_matrix"] = [signature(f) for f in out.Family]
    out = out.sort_values("_order").drop_duplicates(["_matrix", "Positions", "Sizing", "Missing"])
    return out.drop(columns=["_order", "_matrix"]).reset_index(drop=True)


def unique_runs(runs):
    """Keep canonical names for identical equity and trade paths."""
    priorities = {name: i for i, name in enumerate(("Original v11", "Near-v6 360/46 legacy", "CAGR matrix", "50/50 blend", "60/40 blend", "Dense equal matrix"))}
    selected = {}
    seen = set()
    for label, run in sorted(runs.items(), key=lambda item: (item[1]["mode"] != "parent", priorities.get(item[1]["family"], 99))):
        digest = hashlib.sha256(pd.util.hash_pandas_object(run["equity"]).values.tobytes())
        trades = [(t.pair.pool_address, str(t.opened_at), str(t.executed_quantity), str(t.executed_reserve)) for t in run["result"].state.portfolio.get_all_trades()]
        digest.update(json.dumps(trades).encode())
        key = digest.hexdigest()
        if key not in seen:
            selected[label] = run
            seen.add(key)
    return selected


def run_title(run):
    """Short, readable chart identity without internal cache hashes."""
    mode = " / dollar cap" if run["mode"] != "parent" else ""
    return f'{run["family"]}{mode} · {run["positions"]} vaults · {SIZING_NAMES[run["sizing"]]} · missing={run["missing"]}'


def factorial_heatmap(frame, metric):
    """Draw every unique factorial setting with the framework heatmap renderer."""
    data = frame.rename(columns={"Maximum drawdown": "Max DD"}).copy()
    data["Matrix / vaults"] = [f"{f} · {n} vaults" for f, n in zip(data.Family, data.Positions)]
    data["Sizing / missing"] = [f"{SIZING_NAMES[s]}<br>missing={m}" for s, m in zip(data.Sizing, data.Missing)]
    fig = visualise_heatmap_2d(data.set_index(["Matrix / vaults", "Sizing / missing"])[[metric]], "Matrix / vaults", "Sizing / missing", metric, color_continuous_scale="RdYlGn", continuous_scale=False)
    rows = [f"{family} · {n} vaults" for family in FAMILY_ORDER if family in set(frame.Family) for n in (4, 6, 10)]
    cols = [f"{SIZING_NAMES[s]}<br>missing={m}" for s in SIZING for m in (False, True)]
    fig.update_yaxes(categoryorder="array", categoryarray=rows, autorange="reversed", title=None)
    fig.update_xaxes(categoryorder="array", categoryarray=cols, title=None, tickangle=0, side="top")
    fig.update_traces(textfont=dict(shadow="auto"))
    if metric in ("CAGR", "Max DD"):
        fig.update_layout(coloraxis_colorbar_tickformat=".0%")
    fig.update_layout(title=f"{metric} across matrix, breadth, sizing and missingness", height=760, width=1400, margin=dict(l=230, r=70, t=130, b=35))
    return fig


def singleton_heatmaps(screen, features):
    """Compare full backtests of one ranking feature, not the feature's own value."""
    rows = [r for r in screen if r["Active cells"] == 1]
    periods = list(dict.fromkeys(p for p, m in features if p != "45d compatibility"))
    metrics = list(dict.fromkeys(m for p, m in features))
    fig = make_subplots(rows=2, cols=2, subplot_titles=[f"Portfolio {metric} · missing={missing}" for metric in ("CAGR", "Sharpe") for missing in (False, True)], horizontal_spacing=0.12, vertical_spacing=0.20)
    for row, metric in enumerate(("CAGR", "Sharpe"), start=1):
        field = f"Mean fold {metric}"
        values = [r[field] for r in rows]
        for col, missing in enumerate((False, True), start=1):
            grid = pd.DataFrame(np.nan, index=metrics, columns=periods)
            for r in rows:
                if r["Missing"] == missing:
                    p, m = features[int(np.flatnonzero(r["Weights"])[0])]
                    grid.loc[m, p] = r[field]
            texts = grid.map(lambda v: f"{v:.1%}" if metric == "CAGR" else f"{v:.2f}")
            fig.add_trace(go.Heatmap(z=grid.values, x=periods, y=metrics, coloraxis=f"coloraxis{row if row>1 else ''}", text=texts.values, texttemplate="%{text}", hovertemplate="%{y} / %{x}: %{text}<extra></extra>"), row=row, col=col)
        fig.update_layout(**{f"coloraxis{row if row>1 else ''}": dict(colorscale="RdYlGn", cmin=min(values), cmax=max(values), colorbar=dict(title=metric, len=0.35, y=0.79 if row == 1 else 0.21, tickformat=".0%" if metric == "CAGR" else ".1f"))})
    fig.update_xaxes(title="Lookback window")
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(textfont=dict(shadow="auto"))
    fig.update_layout(title="Which single period / metric makes a useful ranking signal?", height=850, width=1400, margin=dict(t=110, l=110, r=90, b=60))
    return fig


def missing_effect_heatmaps(frame):
    """Pair settings so each difference changes only the missing flag."""
    keys = ["Family", "Positions", "Sizing"]
    metrics = ("CAGR", "Sharpe", "Maximum drawdown")
    pair = frame.pivot(index=keys, columns="Missing", values=list(metrics))
    assert pair.notna().all().all()
    names = [f"{f} · {n} vaults" for f in FAMILY_ORDER if f in set(frame.Family) for n in (4, 6, 10)]
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Δ CAGR (percentage points)", "Δ Sharpe", "Δ max DD (percentage points)"), horizontal_spacing=0.12)
    for col, metric in enumerate(metrics, start=1):
        difference = pair[(metric, True)] - pair[(metric, False)]
        data = difference.rename("Delta").reset_index()
        data["Setting"] = [f"{f} · {n} vaults" for f, n in zip(data.Family, data.Positions)]
        grid = data.pivot(index="Setting", columns="Sizing", values="Delta").reindex(index=names, columns=SIZING)
        multiplier = 1 if metric == "Sharpe" else 100
        z = grid.values * multiplier
        bound = max(float(np.abs(z).max()), 1e-9)
        texts = np.vectorize(lambda v: f"{v:+.2f}")(z)
        fig.add_trace(go.Heatmap(z=z, x=[SIZING_NAMES[s] for s in SIZING], y=names, colorscale="RdYlGn", zmin=-bound, zmax=bound, text=texts, texttemplate="%{text}", showscale=False), row=1, col=col)
        fig.update_yaxes(autorange="reversed", showticklabels=col == 1, row=1, col=col)
        fig.update_xaxes(tickangle=-25, row=1, col=col)
    fig.update_traces(textfont=dict(shadow="auto"))
    fig.update_layout(title="Effect of enabling v6 missingness: True minus False", height=750, width=1450, margin=dict(t=110, l=230, r=30, b=70))
    return fig


def weight_fingerprints(families, features, recipes):
    """Show marginal coefficient weights and explicitly label clipping profiles."""
    names = [f for f in FAMILY_ORDER if f in families]
    periods = list(dict.fromkeys(p for p, m in features if p != "45d compatibility"))
    metrics = list(dict.fromkeys(m for p, m in features))
    labels = [f"{f}<br>{profile_name(families[f][1],recipes)}" for f in names]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Weight by metric, summed across windows", "Weight by window, summed across metrics"), column_widths=[0.38, 0.62], horizontal_spacing=0.08)
    for col, keys, axis in [(1, metrics, 1), (2, periods, 0)]:
        values = [[sum(w for (p, m), w in zip(features, families[f][0]) if (p, m)[axis] == key) for key in keys] for f in names]
        texts = [[f"{v:.0%}" for v in row] for row in values]
        fig.add_trace(go.Heatmap(z=values, x=keys, y=labels, coloraxis="coloraxis", text=texts, texttemplate="%{text}"), row=1, col=col)
        fig.update_yaxes(autorange="reversed", showticklabels=col == 1, row=1, col=col)
    fig.update_xaxes(tickvals=metrics, ticktext=["CAGR", "Sharpe", "Sortino", "Max DD", "Calmar"], row=1, col=1)
    fig.update_traces(textfont=dict(shadow="auto"))
    fig.update_layout(title="Matrix fingerprints: metric and lookback weights", coloraxis=dict(colorscale="Blues", cmin=0, cmax=1, colorbar=dict(title="Weight", tickformat=".0%")), height=580, width=1450, margin=dict(l=330, t=100, r=80, b=60))
    return fig


def pareto_chart(frame, baseline, x_metric="CAGR", y_metric="Sharpe"):
    """Map parameter groups and the nondominated frontier for two metrics.

    Drawdown is signed: values nearer zero are better, so all three metrics
    can use the same higher-is-better frontier calculation.
    """
    fig = go.Figure()
    labels = {"CAGR": "CAGR", "Sharpe": "Sharpe", "Maximum drawdown": "Max DD"}
    formats = {"CAGR": ".2%", "Sharpe": ".2f", "Maximum drawdown": ".2%"}
    symbols = {"equal": "circle", "score": "diamond", "inverse_variance": "square"}
    palette = FAMILY_COLOURS
    for family in FAMILY_ORDER:
        for sizing in SIZING:
            data = frame[(frame.Family == family) & (frame.Sizing == sizing)]
            if not len(data):
                continue
            text = [f'{family}<br>{SIZING_NAMES[sizing]} · {r.Positions} vaults · missing={r.Missing}<br>CAGR {r.CAGR:.2%} · Sharpe {r.Sharpe:.2f}<br>Max DD {r["Maximum drawdown"]:.2%}' for _, r in data.iterrows()]
            fig.add_trace(go.Scatter(x=data[x_metric], y=data[y_metric], mode="markers", name=f"{family} / {SIZING_NAMES[sizing]}", marker=dict(color=palette[family], symbol=symbols[sizing], size=7 + data.Positions, opacity=0.8, line=dict(width=1, color="white")), text=text, hovertemplate="%{text}<extra></extra>"))
    points = frame[[x_metric, y_metric]].drop_duplicates().to_numpy()
    frontier = [p for p in points if not any((q >= p).all() and (q > p).any() for q in points)]
    frontier = np.asarray(sorted(frontier, key=lambda p: p[0]))
    fig.add_trace(go.Scatter(x=frontier[:, 0], y=frontier[:, 1], mode="lines+markers", marker=dict(symbol="circle-open", size=24, color="#111827", line=dict(width=2)), line=dict(color="#111827", width=2, dash="dash"), name=f"{labels[x_metric]}/{labels[y_metric]} frontier (grid only)", hovertemplate=f"{labels[x_metric]} %{{x:{formats[x_metric]}}}<br>{labels[y_metric]} %{{y:{formats[y_metric]}}}<extra>Grid frontier</extra>"))
    fig.add_trace(go.Scatter(x=[baseline[x_metric]], y=[baseline[y_metric]], mode="markers", marker=dict(symbol="star", size=22, color="#dc2626", line=dict(color="black", width=1)), name="Original v11", hovertemplate=f"{labels[x_metric]} %{{x:{formats[x_metric]}}}<br>{labels[y_metric]} %{{y:{formats[y_metric]}}}<extra>Original v11</extra>"))
    fig.add_hline(y=baseline[y_metric], line_dash="dot", line_color="#dc2626")
    fig.add_vline(x=baseline[x_metric], line_dash="dot", line_color="#dc2626")
    for count in (4, 6, 10):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=7 + count, color="#9ca3af"), name=f"Size: {count} vaults", hoverinfo="skip"))
    fig.update_layout(title=f"{labels[x_metric]} / {labels[y_metric]} parameter clusters", xaxis=dict(title=labels[x_metric], tickformat=".2f" if x_metric == "Sharpe" else ".0%"), yaxis=dict(title=labels[y_metric], tickformat=".2f" if y_metric == "Sharpe" else ".0%"), height=770, width=1450, legend=dict(font=dict(size=11)), margin=dict(t=80, b=60))
    return fig


def parallel_coordinates(frame):
    """Build an interactive configuration filter with categorical axis labels."""
    names = [f for f in FAMILY_ORDER if f in set(frame.Family)]
    family_values = frame.Family.map({f: i for i, f in enumerate(names)})
    sizing_values = frame.Sizing.map({s: i for i, s in enumerate(SIZING)})
    dimensions = [
        dict(label="Matrix", values=family_values, tickvals=list(range(len(names))), ticktext=names, range=[0, len(names) - 1]),
        dict(label="Vaults", values=frame.Positions, tickvals=[4, 6, 10], range=[4, 10]),
        dict(label="Sizing", values=sizing_values, tickvals=[0, 1, 2], ticktext=[SIZING_NAMES[s] for s in SIZING], range=[0, 2]),
        dict(label="Missing", values=frame.Missing.astype(int), tickvals=[0, 1], ticktext=["False", "True"], range=[0, 1]),
        dict(label="CAGR (%)", values=100 * frame.CAGR, tickformat=".1f"),
        dict(label="Sharpe", values=frame.Sharpe, tickformat=".2f"),
        dict(label="Max DD (%)", values=100 * frame["Maximum drawdown"], tickformat=".1f"),
        dict(label="Cash (%)", values=100 * frame["Mean cash weight"], tickformat=".1f"),
    ]
    fig = go.Figure(go.Parcoords(line=dict(color=frame.Sharpe, colorscale="RdYlGn", showscale=True, cmin=float(frame.Sharpe.min()), cmax=float(frame.Sharpe.max()), colorbar=dict(title="Sharpe", tickformat=".1f", x=1.04, thickness=22)), dimensions=dimensions, labelangle=-15))
    fig.update_layout(title="Interactive parameter explorer — brush axes to filter combinations", height=650, width=1400, margin=dict(l=170, r=145, t=125, b=70))
    return fig


def quarterly_colour_limit(runs):
    """Use a common symmetric scale for all compounded quarterly returns."""
    return max(max(abs((1 + run["daily_returns"]).resample("QE").prod() - 1)) for run in runs.values())


def style_quarterly_returns(fig, limit, title, period):
    """Keep the framework calculation and improve label contrast and comparability."""
    from matplotlib.colors import TwoSlopeNorm
    from matplotlib.ticker import PercentFormatter

    ax = fig.axes[0]
    tile = ax.images[0]
    tile.set_norm(TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit))
    tile.colorbar.formatter = PercentFormatter(xmax=1, decimals=0)
    tile.colorbar.update_ticks()
    ax.grid(False)
    ax.set_xticks(range(4), ["Q1", "Q2", "Q3", "Q4 (partial)"])
    for annotation in ax.texts:
        col, row = annotation.get_position()
        value = tile.get_array()[int(row), int(col)]
        r, g, b, _ = tile.cmap(tile.norm(value))
        annotation.set_color("white" if 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.48 else "black")
        annotation.set_fontsize(12)
        annotation.set_fontweight("bold")
    ax.set_title(f"{title}\nBacktest: {period}")
    fig.tight_layout()
    return fig


def allocation_colours(figures):
    """Give every vault a stable colour across the complete set of figures."""
    names = sorted({trace.name for fig in figures for trace in fig.data if trace.name != "USDC"})
    colours = {"USDC": "#a3a3a3"}
    for i, name in enumerate(names):
        rgb = colorsys.hls_to_rgb((i * 0.61803398875) % 1, 0.47 + (i % 3) * 0.07, 0.65)
        colours[name] = "rgb(" + ",".join(str(round(c * 255)) for c in rgb) + ")"
    return colours


def style_allocation(fig, colours, ceiling):
    """Remove decorative hatching and align absolute USD axes across strategies."""
    for trace in fig.data:
        trace.update(line=dict(color=colours[trace.name], width=0.5), fillcolor=colours[trace.name], fillpattern=dict(shape=""))
    fig.update_layout(template="plotly_white", legend=dict(title="Vault / cash", font=dict(size=12)), margin=dict(t=100, r=300, b=65, l=85))
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="Portfolio value (USD)", range=[0, ceiling], tickprefix="$", tickformat=",.0f")
    return fig


def tidy_saved_outputs(path):
    """Remove residual stdout and incidental file-write return values after a run."""
    import nbformat

    notebook = nbformat.read(path, as_version=4)
    removed = 0
    for cell in notebook.cells:
        if cell.cell_type == "markdown":
            cell.source = re.sub(r"(?<!\\)\$(?=\d)", r"\\$", cell.source)
            continue
        if cell.cell_type != "code":
            continue
        keep = []
        for output in cell.outputs:
            noise = output.output_type == "stream" and output.name == "stdout" and not re.search(r"warning|error|traceback", output.text, re.I)
            noise |= output.output_type == "execute_result" and re.fullmatch(r"\d+", output.get("data", {}).get("text/plain", "")) is not None
            if noise:
                removed += 1
            else:
                keep.append(output)
        cell.outputs = keep
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    return removed
