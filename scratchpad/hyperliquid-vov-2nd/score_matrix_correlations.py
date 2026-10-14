"""Describe rolling feature redundancy in the frozen experiment snapshot."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def feature_correlations(panel, features, start, end, min_observations=100):
    """Calculate pairwise Spearman correlations over finite vault/date pairs.

    Missing metrics remain missing, including undefined zero-risk Sharpe.
    Each pair is ranked on its own common observations. The recorded counts
    describe dependent rolling observations, not independent sample sizes.
    """
    mask = (panel.dates >= pd.Timestamp(start)) & (panel.dates < pd.Timestamp(end))
    indices = [i for i, (period, metric) in enumerate(features) if period != "45d compatibility" and metric in ("CAGR", "Sharpe")]
    columns = pd.MultiIndex.from_tuples([features[i] for i in indices], names=["Lookback", "Metric"])
    sources = {"Raw metrics": panel.raw[mask][:, :, indices].reshape(-1, len(indices))}
    for profile, label in [("requested", "Requested clips"), ("legacy", "Legacy clips")]:
        sources[label] = np.column_stack([panel.cell_scores(i, missing=True, profile=profile)[mask].ravel() for i in indices])
    results = {}
    for label, values in sources.items():
        frame = pd.DataFrame(values, index=None, columns=columns).replace([np.inf, -np.inf], np.nan)
        finite = frame.notna().to_numpy(dtype=np.int64)
        counts = pd.DataFrame(finite.T @ finite, index=columns, columns=columns)
        results[label] = {"correlation": frame.corr(method="spearman", min_periods=min_observations), "counts": counts}
    return results


def correlation_heatmap(results, metric, title):
    """Render within-metric or cross-metric redundancy with pair counts.

    :param metric:
        ``CAGR``, ``Sharpe`` or ``CAGR / Sharpe`` for cross-metric panels.
    """
    cross = metric == "CAGR / Sharpe"
    panels = ["Requested clips", "Legacy clips"] if cross else ["Raw metrics", "Requested clips", "Legacy clips"] if metric == "CAGR" else ["Raw metrics", "Requested clips"]
    labels = {"Raw metrics": "Raw rolling metrics", "Requested clips": "CAGR clip 50%; Sharpe clip 3", "Legacy clips": "CAGR clip 100%; Sharpe clip 3"} if cross else {"Raw metrics": "Raw rolling metrics", "Requested clips": "CAGR clip 50%" if metric == "CAGR" else "Sharpe clip 3", "Legacy clips": "CAGR clip 100%"}
    fig = make_subplots(rows=1, cols=len(panels), subplot_titles=[labels[p] for p in panels], horizontal_spacing=0.07)
    rows_metric = "CAGR" if cross else metric
    cols_metric = "Sharpe" if cross else metric
    for col, label in enumerate(panels, start=1):
        matrix = results[label]["correlation"]
        rows = [key for key in matrix.index if key[1] == rows_metric]
        columns = [key for key in matrix.columns if key[1] == cols_metric]
        values = matrix.loc[rows, columns].to_numpy()
        counts = results[label]["counts"].loc[rows, columns].to_numpy()
        text = np.array([[f"{value:.2f}<br>{count/1000:.1f}k" if np.isfinite(value) else "—" for value, count in zip(v, n)] for v, n in zip(values, counts)])
        names = lambda keys: [f"{p} (360d)" if p == "1y" else f"{p} (730d)" if p == "2y" else p for p, m in keys]
        fig.add_trace(go.Heatmap(z=values, x=names(columns), y=names(rows), text=text, texttemplate="%{text}", textfont=dict(size=11, shadow="auto"), customdata=counts, coloraxis="coloraxis", hovertemplate="Row %{y} / column %{x}<br>Spearman ρ: %{z:.3f}<br>Finite paired vault-days: %{customdata:,}<extra></extra>"), row=1, col=col)
        fig.update_xaxes(title=f"{cols_metric} lookback", tickangle=-40, row=1, col=col)
        fig.update_yaxes(title=f"{rows_metric} lookback" if col == 1 else None, autorange="reversed", row=1, col=col)
    fig.update_layout(title=title, coloraxis=dict(colorscale="RdBu", cmin=-1, cmax=1, cmid=0, colorbar=dict(title="Spearman ρ", tickvals=[-1, -0.5, 0, 0.5, 1])), plot_bgcolor="#e5e7eb", template="plotly_white", width=1600 if len(panels) == 3 else 1450, height=710, margin=dict(t=125, l=95, r=95, b=90))
    return fig


def correlation_records(results):
    """Retain exact pair counts and coefficients in an ignored CSV artefact."""
    rows = []
    for label, result in results.items():
        for a in result["correlation"].index:
            for b in result["correlation"].columns:
                rows.append({"Representation": label, "Row lookback": a[0], "Row metric": a[1], "Column lookback": b[0], "Column metric": b[1], "Spearman rho": result["correlation"].loc[a, b], "Paired vault-days": result["counts"].loc[a, b]})
    return pd.DataFrame(rows)
