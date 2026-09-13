import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import PARAM_ADDITIONS_STABILITY, INDICATOR_ADDITIONS_STABILITY, \
    CELL14_REPLACEMENTS_STABILITY

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

HEADING = """# NB25 - all stability-leads variants side by side

Every configuration tested in the stability-leads plan, re-run in one kernel and plotted against
the shared anchor: equity curves, underwater curves, the return-versus-smoothness trade-off, and
one combined metrics table. The same view NB12 gave the previous batch.

**Based on:** the variants defined in
[21-backtest-vol-matched-family.ipynb](21-backtest-vol-matched-family.ipynb),
[22-backtest-joint-downside.ipynb](22-backtest-joint-downside.ipynb) and
[23-backtest-sortino-leg-swap.ipynb](23-backtest-sortino-leg-swap.ipynb), with the shared harness
and adoption rule v3 from [20-stability-leads-plan.md](20-stability-leads-plan.md). Full window,
2026-01-01 to 2026-09-08, in-sample throughout.

## Why this notebook exists

[24-backtest-closeout.ipynb](24-backtest-closeout.ipynb) already re-runs every configuration and
re-derives every gate, but it is an adoption document: it plots four equity curves out of
thirty-six and has no underwater comparison. Each experiment notebook, meanwhile, compares its own
family against the anchor and never against the other families. This notebook adds only the
picture. Nothing new is tested, no gate is evaluated, and it cannot change a verdict - NB24 owns
those. It exists so the shape of the results is visible on one axis.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "25-research-stability-comparison",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_STABILITY)
cells.append(md("# Harness\n\n- The anchor, then the evidence- and stability-track additions.\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

cells.append(md("""# Provenance and anchor parity

Same check as every notebook in this plan. If the anchor is not the baseline the other notebooks
ran on, none of the curves below are comparable to theirs and the run stops here.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
record_anchor();
'''))

cells.append(md("""## The full variant set

Every configuration from NB21 to NB23, with the family it belongs to. The volatility-matched
family is listed as a candidate rather than a control, because NB21 promoted it - and it is
labelled "data-availability drop" rather than "volatility drop", because NB21 measured that 70.9%
of its removals at N = 30 are vaults with no volatility estimate at all.
"""))
cells.append(code('''VARIANTS = [
    # family, label, overrides
] + [
    ("NB21 data-availability drop", f"drop_{n}", dict(vol_matched_drop_count=n))
    for n in FAMILY_DROPS
] + [
    ("NB22 joint downside", f"complementary_{p}", dict(complementary_pool_size=p))
    for p in (10, 12, 14, 16, 18, 20, 24)
] + [
    ("NB22 window sensitivity", "complementary_18__window_90",
     dict(complementary_pool_size=18, joint_loss_window_days=90)),
    ("NB22 window sensitivity", "complementary_18__window_270",
     dict(complementary_pool_size=18, joint_loss_window_days=270)),
    ("NB22 window sensitivity", "complementary_18__min_events_5",
     dict(complementary_pool_size=18, joint_loss_min_events=5)),
    ("NB22 window sensitivity", "complementary_18__min_events_20",
     dict(complementary_pool_size=18, joint_loss_min_events=20)),
] + [
    ("NB23 Sortino leg swap", "swap__centre",
     dict(selection_score_indicator="cagr_sortino_shrunk_weight", require_scored_candidates=False)),
] + [
    ("NB23 Sortino leg swap", f"swap__{label}",
     {"selection_score_indicator": "cagr_sortino_shrunk_weight", **override})
    for label, override in [
        ("cagr_weight_0.5", dict(cagr_weight=0.5)), ("cagr_weight_0.7", dict(cagr_weight=0.7)),
        ("t_cap_2", dict(evidence_t_cap=2.0)), ("t_cap_4", dict(evidence_t_cap=4.0)),
        ("prior_30", dict(evidence_prior_strength=30)), ("prior_90", dict(evidence_prior_strength=90)),
        ("min_events_10", dict(evidence_min_events=10)), ("min_events_30", dict(evidence_min_events=30)),
        ("max_events_60", dict(evidence_max_events=60)), ("max_events_120", dict(evidence_max_events=120)),
    ]
] + [
    ("NB23 policy", "swap__require_scored",
     dict(selection_score_indicator="cagr_sortino_shrunk_weight", require_scored_candidates=True)),
]

family_by_label = {"anchor": "anchor"}
for family, label, _overrides in VARIANTS:
    family_by_label[label] = family
print(f"{len(VARIANTS)} variants plus the anchor, in {len(set(family_by_label.values()))} families")
display(pd.Series(family_by_label).value_counts().rename("runs").to_frame())
'''))

cells.append(md("""## Run them

Through the same `run_and_record()` every notebook in this plan uses, so `runs` / `run_by_label`
is the single source for every table and chart below. About twenty seconds each.
"""))
cells.append(code('''import time

start = time.time()
for family, label, overrides in VARIANTS:
    run_and_record(label, family, **overrides)
print(f"{len(VARIANTS)} variants in {time.time() - start:.0f}s")

equity_by_label = {entry["label"]: entry["equity"] for entry in runs}
family = family_frame()
comparison = pd.DataFrame([entry["panel"] for entry in runs]).set_index("label")
comparison["family"] = [family_by_label[label] for label in comparison.index]
comparison["passes_v3"] = [
    passes_constraints_v3(row, anchor_panel, family) for _, row in comparison.iterrows()
]
comparison["failed"] = [
    failing_constraints_v3(row, anchor_panel, family) for _, row in comparison.iterrows()
]
comparison["late_ok"] = [late_period_ok_v3(row, anchor_panel) for _, row in comparison.iterrows()]
print(f"{len(comparison)} rows, {int(comparison['passes_v3'].sum())} passing all seven constraints")
'''))

cells.append(md("""# Combined metrics table

Sorted by Martin ratio, the ranking metric the track has used throughout. `passes_v3` is the full
seven-constraint adoption rule: CAGR at least 20%, cycle Sharpe within 0.10 of the anchor's,
volatility no worse, ulcer at least 15% better, invested-basket BTC beta lower, deployment at
least 90%, and cycle Sharpe at least 0.10 above the best observed control no noisier than the
candidate. `failed` is never truncated.

Passing every constraint is NOT adoption. A candidate also needs a plateau, a surviving
leave-one-vault-out and the late period, and NB21 to NB24 evaluate those. Read this table as the
shape of the results, not as a verdict.
"""))
cells.append(code('''TABLE_COLS = ["family", "cagr", "ulcer", "martin", "cycle_vol", "abs_invested_beta",
              "mean_invested", "max_dd", "cycle_sharpe", "late_ok", "passes_v3", "failed"]
table = comparison[TABLE_COLS].sort_values("martin", ascending=False)

styled = (
    table.style
    .format({
        "cagr": "{:.2%}", "ulcer": "{:.2%}", "martin": "{:.2f}", "cycle_vol": "{:.2%}",
        "abs_invested_beta": "{:.4f}", "mean_invested": "{:.1%}", "max_dd": "{:.2%}",
        "cycle_sharpe": "{:.2f}",
    })
    .background_gradient(subset=["martin"], cmap="RdYlGn")
    .apply(lambda s: ["font-weight: bold" if i == "anchor" else "" for i in s.index], axis=0)
)
display_dataframe_with_html(styled)
'''))

cells.append(md("""# Equity curves

The anchor in black, every variant coloured by family. All runs start from the same $150,000 on
the same day, so the curves are directly comparable.
"""))
cells.append(code('''import plotly.graph_objects as go

FAMILY_COLOURS = {
    "anchor": "#111111",
    "NB21 data-availability drop": "#1f77b4",
    "NB22 joint downside": "#d62728",
    "NB22 window sensitivity": "#ff7f0e",
    "NB23 Sortino leg swap": "#9467bd",
    "NB23 policy": "#8c564b",
}

def equity_figure(labels, title, log_y=False):
    fig = go.Figure()
    for label in labels:
        curve = equity_by_label[label]
        is_anchor = label == "anchor"
        fig.add_trace(go.Scatter(
            x=curve.index, y=curve.to_numpy(), name=label, mode="lines",
            line=dict(color=FAMILY_COLOURS.get(family_by_label[label], "#888888"),
                      width=4 if is_anchor else 1.5),
            opacity=1.0 if is_anchor else 0.7,
            legendgroup=family_by_label[label],
            hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(title=title, hovermode="x unified", legend=dict(font=dict(size=9)))
    fig.update_yaxes(title="Equity (USD)", tickformat="$,.0f", type="log" if log_y else "linear")
    fig.update_xaxes(title="Time")
    return fig


equity_figure(list(equity_by_label), "All stability-leads variants against the anchor").show()
'''))

cells.append(md("""## One family at a time

The combined chart is crowded by design - the spread is the point. These separate the families so
each can be read against the anchor on its own.
"""))
cells.append(code('''for name in ["NB21 data-availability drop", "NB22 joint downside",
             "NB22 window sensitivity", "NB23 Sortino leg swap", "NB23 policy"]:
    labels = ["anchor"] + [l for l, f in family_by_label.items() if f == name]
    equity_figure(labels, f"{name} against the anchor").show()
'''))

cells.append(md("""# Underwater curves

Drawdown from each run's own running peak. This is the shape the plan was trying to improve, and
the ulcer index in the table above is the root-mean-square of these depths.

Read these against NB20: a vault whose mark goes stale contributes a flat line rather than a real
recovery, and dropping the eleven cycles where most of the invested book was stale moves the
anchor's ulcer by 4.4%. The differences between curves that are smaller than that are not
distinguishable from reporting behaviour.
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
fig.update_layout(title="Drawdown from running peak", hovermode="x unified",
                  legend=dict(font=dict(size=9)))
fig.update_yaxes(title="Drawdown", tickformat=".1%")
fig.update_xaxes(title="Time")
fig.show()
'''))

cells.append(md("""# The trade-off the plan is actually about

Return against smoothness. Up and to the left is better: higher CAGR, lower ulcer index. The
dashed lines are the anchor's position, so the top-left quadrant beats it on both axes at once.
Marker size is invested-basket BTC beta, the plan's second risk goal, so a small marker in the
top-left quadrant is what the plan was looking for.
"""))
cells.append(code('''plot_df = comparison.reset_index()

fig = go.Figure()
for name in plot_df["family"].unique():
    subset = plot_df[plot_df["family"] == name]
    fig.add_trace(go.Scatter(
        x=subset["ulcer"], y=subset["cagr"], mode="markers+text",
        name=name, text=subset["label"], textposition="top center", textfont=dict(size=8),
        marker=dict(size=8 + 260 * subset["abs_invested_beta"],
                    color=FAMILY_COLOURS.get(name, "#888888"),
                    line=dict(width=1, color="white"), opacity=0.85),
        hovertemplate=("%{text}<br>CAGR %{y:.2%}<br>Ulcer %{x:.2%}"
                       "<br>Beta %{customdata:.4f}<extra></extra>"),
        customdata=subset["abs_invested_beta"],
    ))

fig.add_hline(y=float(anchor_panel["cagr"]), line=dict(dash="dash", color="#111111", width=1))
fig.add_vline(x=float(anchor_panel["ulcer"]), line=dict(dash="dash", color="#111111", width=1))
fig.add_hline(y=CAGR_FLOOR_V2, line=dict(dash="dot", color="#999999", width=1),
              annotation_text="20% CAGR floor", annotation_position="bottom right")
fig.add_vline(x=float(anchor_panel["ulcer"]) * (1.0 - ULCER_IMPROVEMENT_FRAC),
              line=dict(dash="dot", color="#999999", width=1),
              annotation_text="15% ulcer improvement", annotation_position="top left")
fig.update_layout(title="Return against smoothness (marker size = BTC beta)",
                  legend=dict(font=dict(size=9)))
fig.update_yaxes(title="CAGR", tickformat=".0%")
fig.update_xaxes(title="Ulcer index (lower is smoother)", tickformat=".1%")
fig.show()

better_both = comparison[
    (comparison["cagr"] > anchor_panel["cagr"]) & (comparison["ulcer"] < anchor_panel["ulcer"])
]
print("Runs beating the anchor on BOTH return and smoothness:")
display(better_both[["family", "cagr", "ulcer", "martin", "abs_invested_beta",
                     "late_ok", "passes_v3", "failed"]]
        if len(better_both) else "  none")
'''))

cells.append(md("""# Sharpe against volatility, with the observed-control frontier

Constraint 7 compares a candidate against the best observed control no noisier than it is. This
is that comparison drawn: the data-availability drop family as a line, every other run as a point.
A candidate has to sit 0.10 of a Sharpe above the line at its own volatility.
"""))
cells.append(code('''frontier = family.sort_values("cycle_vol")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=frontier["cycle_vol"], y=frontier["cycle_sharpe"], mode="lines+markers",
    name="Data-availability drop family", line=dict(color="#1f77b4"),
    text=[f"drop {int(n)}" for n in frontier["drop_n"]],
    hovertemplate="%{text}<br>vol %{x:.2%}<br>Sharpe %{y:.3f}<extra></extra>",
))
for name in ("NB22 joint downside", "NB22 window sensitivity",
             "NB23 Sortino leg swap", "NB23 policy"):
    subset = comparison[comparison["family"] == name]
    fig.add_trace(go.Scatter(
        x=subset["cycle_vol"], y=subset["cycle_sharpe"], mode="markers", name=name,
        marker=dict(size=9, color=FAMILY_COLOURS.get(name, "#888888"), opacity=0.85),
        text=subset.index, hovertemplate="%{text}<br>vol %{x:.2%}<br>Sharpe %{y:.3f}<extra></extra>",
    ))
fig.add_trace(go.Scatter(
    x=[anchor_panel["cycle_vol"]], y=[anchor_panel["cycle_sharpe"]], mode="markers",
    name="Anchor", marker=dict(color="#111111", size=14, symbol="star"),
))
fig.update_layout(title="Cycle Sharpe against cycle volatility", legend=dict(font=dict(size=9)))
fig.update_yaxes(title="Cycle Sharpe")
fig.update_xaxes(title="Cycle volatility", tickformat=".1%")
fig.show()
'''))

cells.append(md("""# How each family fails

One row per family: how many runs it contains, how many pass all seven constraints, and which
constraint binds most often. The plan's question was whether the families fail in the same way or
in different ways.
"""))
cells.append(code('''from collections import Counter

rows = []
for name, group in comparison.groupby("family"):
    counter = Counter()
    for failed in group["failed"]:
        for constraint in (c.strip() for c in failed.split(",") if c.strip()):
            counter[constraint] += 1
    rows.append({
        "family": name,
        "runs": len(group),
        "passing all seven": int(group["passes_v3"].sum()),
        "late period holds": int(group["late_ok"].sum()),
        "median CAGR": group["cagr"].median(),
        "median ulcer": group["ulcer"].median(),
        "most common failure": counter.most_common(1)[0][0] if counter else "none",
        "how often": counter.most_common(1)[0][1] if counter else 0,
        "every failure seen": "; ".join(f"{c} x{n}" for c, n in counter.most_common()),
    })
display(pd.DataFrame(rows).set_index("family"))
'''))

write_notebook(cells, TRACK_DIR / "25-research-stability-comparison.ipynb")
