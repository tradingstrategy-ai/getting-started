import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, write_notebook, TRACK_DIR

HEADING = """# NB12 - all variants side by side

Every configuration tested in the `hyperliquid-lower-vol` track, re-run in one kernel and plotted
against the shared anchor: equity curves, underwater curves, the return-versus-smoothness
trade-off, and one combined metrics table.

**Based on:** the variants defined in [04-backtest-vol-target.ipynb](04-backtest-vol-target.ipynb),
[05-backtest-pool-cap.ipynb](05-backtest-pool-cap.ipynb),
[06-backtest-breadth-concentration.ipynb](06-backtest-breadth-concentration.ipynb),
[07-backtest-drawdown-sizing.ipynb](07-backtest-drawdown-sizing.ipynb) and
[09-backtest-consistency-selection.ipynb](09-backtest-consistency-selection.ipynb), with the shared
harness and adoption rule from [03-smoothing-experiment-plan.md](03-smoothing-experiment-plan.md).
Development window (2026-01-01 to 2026-06-30); the hold-out stays closed.

## Why this notebook exists

Each experiment notebook compares its own family against the anchor, so the families were never
placed on a common axis. Two questions only a combined view answers: whether the families fail in
the same way or in different ways, and whether any of them trades return for smoothness on terms
the others do not. Nothing new is tested here - every configuration is one already run - so this
notebook cannot change a verdict, only make the shape of the results visible.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("12-research-variant-comparison")
cells += common_suffix_cells()
cells.append(md("# Run every variant\n\n- Shared harness: the anchor first, then each family.\n"))
cells.append(harness_cell())

cells.append(md("""## The full variant set

Every configuration from NB04 to NB09, with the family it belongs to and the overrides that define
it. `vol_matched_drop_*` is included at the settings that cleared the adoption constraints, since
it turned out to be the track's only candidate rather than the control it was introduced as.
"""))
cells.append(code('''VARIANTS = [
    # family, label, overrides
    ("NB04 vol target",   "target_vol_0.10",        dict(target_portfolio_vol=0.10)),
    ("NB04 vol target",   "target_vol_0.15",        dict(target_portfolio_vol=0.15)),
    ("NB04 vol target",   "target_vol_0.20",        dict(target_portfolio_vol=0.20)),
    ("NB05 capacity",     "pool_cap_0.15",          dict(per_position_cap_of_pool_pct=0.15)),
    ("NB05 capacity",     "pool_cap_0.05",          dict(per_position_cap_of_pool_pct=0.05)),
    ("NB05 capacity",     "min_tvl_25k",            dict(min_tvl_usd=25_000)),
    ("NB05 capacity",     "min_tvl_100k",           dict(min_tvl_usd=100_000)),
    ("NB06 breadth/conc",  "assets_8",              dict(max_assets_in_portfolio=8)),
    ("NB06 breadth/conc",  "assets_10",             dict(max_assets_in_portfolio=10)),
    ("NB06 breadth/conc",  "concentration_0.20",    dict(max_concentration_pct=0.20)),
    ("NB06 breadth/conc",  "concentration_0.25",    dict(max_concentration_pct=0.25)),
    ("NB07 sizing",       "inverse_ulcer",          dict(weighting_method="inverse_ulcer", sizing_risk_indicator="ulcer_index_180")),
    ("NB07 sizing",       "inverse_downside",       dict(weighting_method="inverse_downside", sizing_risk_indicator="downside_deviation_90")),
    ("NB07 sizing",       "risk_contribution",      dict(weighting_method="risk_contribution", residual_correlation_cap=0.40)),
    ("NB09 selection",    "min_window_sortino",     dict(selection_score_indicator="cagr_min_sortino_weight", require_scored_candidates=True)),
    ("NB09 selection",    "positive_window_share",  dict(selection_score_indicator="cagr_positive_window_weight", require_scored_candidates=True)),
    ("NB09 selection",    "downside_score",         dict(selection_score_indicator="cagr_downside_weight", require_scored_candidates=True)),
    ("NB09 selection",    "event_concentration_0.5", dict(event_concentration_lambda=0.5)),
    ("NB09 vol-matched",  "vol_matched_drop_25",    dict(vol_matched_drop_count=25)),
    ("NB09 vol-matched",  "vol_matched_drop_30",    dict(vol_matched_drop_count=30)),
    ("NB09 vol-matched",  "vol_matched_drop_35",    dict(vol_matched_drop_count=35)),
    ("NB09 vol-matched",  "vol_matched_drop_50",    dict(vol_matched_drop_count=50)),
]
print(f"{len(VARIANTS)} variants plus the anchor, across {len({v[0] for v in VARIANTS})} families")
'''))

cells.append(md("## Run them\n"))
cells.append(code('''import time

anchor_cycle_returns, _ = cycle_returns(anchor_equity)

equity_by_label = {"anchor": anchor_equity}
family_by_label = {"anchor": "anchor"}
panel_rows = [anchor_panel]

started = time.time()
for i, (family, label, overrides) in enumerate(VARIANTS, start=1):
    variant_state, variant_equity, variant_returns = run_variant(label, **overrides)
    equity_by_label[label] = variant_equity
    family_by_label[label] = family
    panel_rows.append(panel(label, variant_state, variant_equity, variant_returns, anchor_cycle_returns))
    print(f"[{i}/{len(VARIANTS)}] {family:<20} {label:<24} "
          f"CAGR {panel_rows[-1]['cagr']:>7.2%}  Martin {panel_rows[-1]['martin']:>6.2f}  "
          f"({time.time() - started:.0f}s elapsed)")

comparison = pd.DataFrame(panel_rows).set_index("label")
comparison["family"] = [family_by_label[label] for label in comparison.index]
comparison["passes"] = [
    passes_constraints(row, anchor_panel) if label != "anchor" else True
    for label, row in comparison.iterrows()
]
print(f"\\nDone in {time.time() - started:.0f}s")
'''))

cells.append(md("""# Combined metrics table

Sorted by Martin ratio, the track's pre-registered ranking metric. `passes` is the full
five-constraint adoption rule: CAGR at least 30%, volatility no worse than the anchor's, ulcer index
lower, invested-basket BTC beta lower, deployment at least 45%.
"""))
cells.append(code('''TABLE_COLS = ["family", "cagr", "ulcer", "martin", "cycle_vol", "abs_invested_beta",
              "mean_invested", "max_dd", "cycle_sharpe", "top5_gross_share", "passes"]
table = comparison[TABLE_COLS].sort_values("martin", ascending=False)

styled = (
    table.style
    .format({
        "cagr": "{:.2%}", "ulcer": "{:.2%}", "martin": "{:.2f}", "cycle_vol": "{:.2%}",
        "abs_invested_beta": "{:.4f}", "mean_invested": "{:.1%}", "max_dd": "{:.2%}",
        "cycle_sharpe": "{:.2f}", "top5_gross_share": "{:.1%}",
    })
    .background_gradient(subset=["martin"], cmap="RdYlGn")
    .apply(lambda s: ["font-weight: bold" if i == "anchor" else "" for i in s.index], axis=0)
)
display_dataframe_with_html(styled)
'''))

cells.append(md("""# Equity curves

The anchor in black, every variant coloured by family. All runs start from the same $150,000 on the
same day, so the curves are directly comparable.
"""))
cells.append(code('''import plotly.graph_objects as go

FAMILY_COLOURS = {
    "anchor": "#111111",
    "NB04 vol target": "#1f77b4",
    "NB05 capacity": "#ff7f0e",
    "NB06 breadth/conc": "#2ca02c",
    "NB07 sizing": "#d62728",
    "NB09 selection": "#9467bd",
    "NB09 vol-matched": "#17becf",
}

def equity_figure(labels, title):
    fig = go.Figure()
    for label in labels:
        curve = equity_by_label[label]
        is_anchor = label == "anchor"
        fig.add_trace(go.Scatter(
            x=curve.index, y=curve.to_numpy(), name=label, mode="lines",
            line=dict(
                color=FAMILY_COLOURS.get(family_by_label[label], "#888888"),
                width=4 if is_anchor else 1.5,
                dash=None if is_anchor else "solid",
            ),
            opacity=1.0 if is_anchor else 0.75,
            legendgroup=family_by_label[label],
            hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(title=title, hovermode="x unified", legend=dict(font=dict(size=9)))
    fig.update_yaxes(title="Equity (USD)", tickformat="$,.0f")
    fig.update_xaxes(title="Time")
    return fig


equity_figure(list(equity_by_label), "All variants against the anchor").show()
'''))

cells.append(md("""## One family at a time

The combined chart is crowded by design - the point of it is the spread. These separate the
families so each can be read against the anchor on its own.
"""))
cells.append(code('''for family in ["NB04 vol target", "NB05 capacity", "NB06 breadth/conc",
               "NB07 sizing", "NB09 selection", "NB09 vol-matched"]:
    labels = ["anchor"] + [l for l, f in family_by_label.items() if f == family]
    equity_figure(labels, f"{family} against the anchor").show()
'''))

cells.append(md("""# Underwater curves

Drawdown from each run's own running peak. This is the shape the track was trying to improve, and
the ulcer index in the table above is the root-mean-square of these depths.
"""))
cells.append(code('''fig = go.Figure()
for label, curve in equity_by_label.items():
    drawdown = curve / curve.cummax() - 1.0
    is_anchor = label == "anchor"
    fig.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown.to_numpy(), name=label, mode="lines",
        line=dict(color=FAMILY_COLOURS.get(family_by_label[label], "#888888"),
                  width=4 if is_anchor else 1.2),
        opacity=1.0 if is_anchor else 0.6,
        legendgroup=family_by_label[label],
        hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}<br>%{y:.2%}<extra></extra>",
    ))
fig.update_layout(title="Drawdown from running peak", hovermode="x unified", legend=dict(font=dict(size=9)))
fig.update_yaxes(title="Drawdown", tickformat=".1%")
fig.update_xaxes(title="Time")
fig.show()
'''))

cells.append(md("""# The trade-off the track is actually about

Return against smoothness. Up and to the left is better: higher CAGR, lower ulcer index. The dashed
lines are the anchor's position, so the top-left quadrant is the region that beats it on both axes
at once. Marker size is invested-basket BTC beta - the second goal - so a small marker in the
top-left quadrant is what the track was looking for.
"""))
cells.append(code('''plot_df = comparison.reset_index()

fig = go.Figure()
for family in plot_df["family"].unique():
    subset = plot_df[plot_df["family"] == family]
    fig.add_trace(go.Scatter(
        x=subset["ulcer"], y=subset["cagr"], mode="markers+text",
        name=family, text=subset["label"], textposition="top center",
        textfont=dict(size=8),
        marker=dict(
            size=8 + 260 * subset["abs_invested_beta"],
            color=FAMILY_COLOURS.get(family, "#888888"),
            line=dict(width=1, color="white"),
            opacity=0.85,
        ),
        hovertemplate=("%{text}<br>CAGR %{y:.2%}<br>Ulcer %{x:.2%}"
                       "<br>Beta %{customdata:.4f}<extra></extra>"),
        customdata=subset["abs_invested_beta"],
    ))

fig.add_hline(y=float(anchor_panel["cagr"]), line=dict(dash="dash", color="#111111", width=1))
fig.add_vline(x=float(anchor_panel["ulcer"]), line=dict(dash="dash", color="#111111", width=1))
fig.add_hline(y=0.30, line=dict(dash="dot", color="#999999", width=1),
              annotation_text="30% CAGR floor", annotation_position="bottom right")
fig.update_layout(title="Return against smoothness (marker size = BTC beta)",
                  legend=dict(font=dict(size=9)))
fig.update_yaxes(title="CAGR", tickformat=".0%")
fig.update_xaxes(title="Ulcer index (lower is smoother)", tickformat=".1%")
fig.show()

better_both = comparison[
    (comparison["cagr"] > anchor_panel["cagr"]) & (comparison["ulcer"] < anchor_panel["ulcer"])
]
print("Variants beating the anchor on BOTH return and smoothness:")
print(better_both[["cagr", "ulcer", "martin", "abs_invested_beta", "passes"]].to_string()
      if len(better_both) else "  none")
'''))

cells.append(md("""# How each family fails

The adoption rule has five constraints and a variant needs all of them. This counts which
constraint each variant misses, so the families can be compared by failure mode rather than by
degree.
"""))
cells.append(code('''def failed_constraints(row):
    if row.name == "anchor":
        return []
    failures = []
    if not row["cagr"] >= 0.30:
        failures.append("CAGR < 30%")
    if not row["cycle_vol"] <= anchor_panel["cycle_vol"]:
        failures.append("volatility")
    if not row["ulcer"] < anchor_panel["ulcer"]:
        failures.append("ulcer")
    if not row["abs_invested_beta"] < anchor_panel["abs_invested_beta"]:
        failures.append("beta")
    if not row["mean_invested"] >= 0.45:
        failures.append("deployment")
    return failures

failure_rows = []
for label, row in comparison.iterrows():
    failures = failed_constraints(row)
    failure_rows.append({
        "label": label,
        "family": row["family"],
        "n_failed": len(failures),
        "failed": ", ".join(failures) if failures else "-- passes all --",
    })
failure_df = pd.DataFrame(failure_rows).set_index("label").sort_values(["n_failed", "family"])
display(failure_df)

print()
print("Constraint failure counts across all variants:")
counts = {}
for row in failure_rows:
    for f in row["failed"].split(", "):
        if f.startswith("--"):
            continue
        counts[f] = counts.get(f, 0) + 1
for constraint, n in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"  {constraint:<12} {n} of {len(VARIANTS)} variants")
'''))

write_notebook(cells, TRACK_DIR / "12-research-variant-comparison.ipynb")
