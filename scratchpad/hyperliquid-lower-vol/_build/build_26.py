import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_drop_modes import PARAM_ADDITIONS_DROP_MODES, CELL14_REPLACEMENTS_DROP_MODES

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

HEADING = """# NB26 - was the drop a fluke, or is there a real effect?

`drop_30` is the best single result either plan has produced: 48.99% CAGR against the anchor's
37.90%, ulcer 1.384% against 1.796%, invested BTC beta 0.0011 against 0.0458, and an empty
failure set on constraints 1 to 6. [21-backtest-vol-matched-family.ipynb](21-backtest-vol-matched-family.ipynb)
rejected it because neither neighbour passes, so it is a spike as a *rule* - but that does not
say whether the effect underneath it is real.

It also cannot be interpreted as it stands, because the mechanism does two different things at
once. `inverse_vol` needs 90 observations; a vault without them is stored as `0.0`; and `0.0` is
the smallest possible sort key, so every UNMEASURED vault is removed before any measured one.
NB21 measured that at 70.9% of removals at N = 30. So `drop_30` is roughly 21 data-availability
removals plus 9 genuine volatility removals, and nobody knows which half did the work.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) as the anchor, the family from
[21-backtest-vol-matched-family.ipynb](21-backtest-vol-matched-family.ipynb), and the composition
diagnostic in [22-backtest-joint-downside.ipynb](22-backtest-joint-downside.ipynb) Part A. Full
window 2026-01-01 to 2026-09-08, in-sample throughout.

## Method

Three new `vol_drop_mode` values decompose the incumbent sort. `measured_only` removes the N most
volatile vaults that HAVE an estimate and never an unmeasured one - what the control was always
described as doing. `unmeasured_only` removes vaults with too little history to measure and never
a measured one, however volatile - the other half. `random` removes N candidates by a seeded
deterministic permutation, which is the null the drop has never had: it separates "this filter
selects well" from "holding fewer names on this window happened to help". `incumbent` reproduces
the original sort exactly and is the default, so every earlier notebook is unaffected.

Variants are compared at matched REMOVALS ACTUALLY MADE, not at matched N. Comparing at equal N
would be unfair, because the incumbent's nominal 30 is only about 9 real volatility removals.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "26-backtest-drop-decomposition",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_DROP_MODES},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_DROP_MODES)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

cells.append(md("""# Provenance and anchor parity

The new `vol_drop_mode` branch defaults to `'incumbent'`, which is the original sort verbatim, so
the anchor must be unchanged and `drop_30` must still return 0.489942 / 2.747391. Both are
asserted rather than assumed.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
record_anchor();
'''))

cells.append(md("""# The variants

Five incumbent settings for context, then each half of the mechanism swept on its own, then the
random null at two strengths: 30, matching the incumbent's nominal N, and 9, matching the volatile
removals it actually makes.
"""))
cells.append(code('''INCUMBENT_N = (10, 20, 30, 40, 50)
MEASURED_N = (2, 4, 6, 8, 10, 12, 14, 16, 20)
UNMEASURED_N = (10, 20, 25, 30, 40)
RANDOM_SEEDS = tuple(range(10))

VARIANTS = []
for n in INCUMBENT_N:
    VARIANTS.append(("incumbent", f"incumbent_{n}", dict(vol_matched_drop_count=n)))
for n in MEASURED_N:
    VARIANTS.append(("measured only", f"measured_{n}",
                     dict(vol_matched_drop_count=n, vol_drop_mode="measured_only")))
for n in UNMEASURED_N:
    VARIANTS.append(("unmeasured only", f"unmeasured_{n}",
                     dict(vol_matched_drop_count=n, vol_drop_mode="unmeasured_only")))
for seed in RANDOM_SEEDS:
    VARIANTS.append(("random null n=30", f"random30_s{seed}",
                     dict(vol_matched_drop_count=30, vol_drop_mode="random", vol_drop_seed=seed)))
    VARIANTS.append(("random null n=9", f"random9_s{seed}",
                     dict(vol_matched_drop_count=9, vol_drop_mode="random", vol_drop_seed=seed)))

mode_by_label = {"anchor": "anchor"}
for mode, label, _ in VARIANTS:
    mode_by_label[label] = mode
print(f"{len(VARIANTS)} variants plus the anchor")
display(pd.Series(mode_by_label).value_counts().rename("runs").to_frame())
'''))

cells.append(code('''import time

start = time.time()
for mode, label, overrides in VARIANTS:
    run_and_record(label, mode, **overrides)
print(f"{len(VARIANTS)} variants in {time.time() - start:.0f}s")

# `incumbent_30` must reproduce NB21's drop_30 exactly - same configuration, different label.
inc30 = run_by_label["incumbent_30"]["panel"]
print(f"incumbent_30 CAGR {inc30['cagr']:.6f} (NB21 drop_30: 0.489942), "
      f"Sharpe {inc30['cycle_sharpe']:.6f} (2.747391)")
assert abs(inc30["cagr"] - 0.489942) < 1e-5 and abs(inc30["cycle_sharpe"] - 2.747391) < 1e-5, \\
    "incumbent_30 does not reproduce NB21's drop_30; the mode branch is not inert"
'''))

cells.append(md("""# How many removals each mode actually makes

The whole point of the decomposition. `vol_matched_drop_count` is a nominal setting; what matters
is how many vaults were removed and of what kind, read from the trading code's own
`VOL_DROP_LOG` rather than reconstructed.
"""))
cells.append(code('''rows = []
for entry in runs:
    log = entry["vol_drop_log"]
    if not log:
        continue
    removed = [len(v["dropped_ids"]) for v in log.values()]
    no_estimate = [len(v["no_estimate_dropped"]) for v in log.values()]
    rows.append({
        "label": entry["label"], "mode": entry["family"],
        "nominal_n": entry["overrides"].get("vol_matched_drop_count"),
        "decisions": len(log),
        "mean_pool": np.mean([v["pool_size"] for v in log.values()]),
        "mean_measured_pool": np.mean([v["measured_pool"] for v in log.values()]),
        "mean_unmeasured_pool": np.mean([v["unmeasured_pool"] for v in log.values()]),
        "mean_removed": np.mean(removed),
        "mean_removed_no_estimate": np.mean(no_estimate),
        "mean_removed_measured": np.mean(removed) - np.mean(no_estimate),
    })
composition = pd.DataFrame(rows).set_index("label")
display(composition.round(2))
print("The incumbent's effective volatility strength is `mean_removed_measured`, not its nominal N.")
'''))

cells.append(md("""# Portfolio key metrics

Every variant against the anchor, sorted by Martin ratio. `passes_v3` is constraints 1 to 7; as
in NB25 it is not adoption, which also needs a plateau, leave-one-vault-out and the late period.
"""))
cells.append(code('''# `family_frame()` looks for labels named `drop_N`; this notebook names them `incumbent_N`, so
# the comparator family is built directly from the incumbent runs. They are the same
# configurations NB21 ran, and they are the right observed control here: the question is whether
# either half beats the conflated mechanism it was cut out of.
family = pd.DataFrame([run_by_label[f"incumbent_{n}"]["panel"] for n in INCUMBENT_N]).set_index("label")
family["drop_n"] = list(INCUMBENT_N)

comparison = pd.DataFrame([e["panel"] for e in runs]).set_index("label")
comparison["mode"] = [mode_by_label[l] for l in comparison.index]
comparison["mean_removed"] = composition["mean_removed"].reindex(comparison.index)
comparison["mean_removed_measured"] = composition["mean_removed_measured"].reindex(comparison.index)
comparison["failed_1_to_6"] = [
    failing_constraints_v3(r, anchor_panel, None, skip_placebo=True)
    for _, r in comparison.iterrows()
]
comparison["passes_1_to_6"] = comparison["failed_1_to_6"] == ""
comparison["late_ok"] = [late_period_ok_v3(r, anchor_panel) for _, r in comparison.iterrows()]

COLS = ["mode", "nominal", "mean_removed", "mean_removed_measured", "cagr", "ulcer", "martin",
        "cycle_vol", "cycle_sharpe", "abs_invested_beta", "mean_invested",
        "sparse_cagr", "dense_cagr", "late_cagr", "late_ok", "passes_1_to_6", "failed_1_to_6"]
comparison["nominal"] = [
    run_by_label[l]["overrides"].get("vol_matched_drop_count", 0) for l in comparison.index
]
display_dataframe_with_html(
    comparison[COLS].sort_values("martin", ascending=False).style.format({
        "mean_removed": "{:.1f}", "mean_removed_measured": "{:.1f}", "cagr": "{:.2%}",
        "ulcer": "{:.2%}", "martin": "{:.1f}", "cycle_vol": "{:.2%}", "cycle_sharpe": "{:.2f}",
        "abs_invested_beta": "{:.4f}", "mean_invested": "{:.1%}",
        "sparse_cagr": "{:.1%}", "dense_cagr": "{:.1%}", "late_cagr": "{:.1%}",
    }).background_gradient(subset=["martin"], cmap="RdYlGn")
)
'''))

cells.append(md("""# Which half did the work?

The direct comparison. `incumbent_30` against the `measured_only` run closest to its effective
volatility strength, and against the `unmeasured_only` run closest to its data-availability
removals. If one half reproduces the incumbent and the other does not, the effect has a location.
"""))
cells.append(code('''target_measured = float(composition.loc["incumbent_30", "mean_removed_measured"])
target_unmeasured = float(composition.loc["incumbent_30", "mean_removed_no_estimate"])

def nearest(mode_name, column, target):
    subset = composition[composition["mode"] == mode_name]
    return (subset[column] - target).abs().idxmin()

m_match = nearest("measured only", "mean_removed", target_measured)
u_match = nearest("unmeasured only", "mean_removed", target_unmeasured)
print(f"incumbent_30 removes {target_measured:.1f} measured and {target_unmeasured:.1f} unmeasured per decision")
print(f"closest measured-only run:   {m_match} ({composition.loc[m_match, 'mean_removed']:.1f} removed)")
print(f"closest unmeasured-only run: {u_match} ({composition.loc[u_match, 'mean_removed']:.1f} removed)")

HEAD = ["cagr", "ulcer", "martin", "cycle_vol", "cycle_sharpe", "abs_invested_beta",
        "sparse_cagr", "dense_cagr", "late_cagr", "late_ok", "failed_1_to_6"]
display(comparison.loc[["anchor", "incumbent_30", m_match, u_match], HEAD])
'''))

cells.append(md("""# The random null

Ten seeded draws at each strength. This is the test the drop has never had: if removing N
candidates at random reproduces the incumbent's numbers, the filter is not selecting anything and
the result is a property of holding a smaller book on this window.

Reported as a percentile with the add-one correction, `p = (1 + #{null >= observed}) / (B + 1)`,
one-sided in the direction that would favour the candidate. Ten draws give a resolution of 0.09,
so a p of 0.09 is the strongest statement this can make; it is a benchmark percentile, not a
significance test.
"""))
cells.append(code('''def null_percentile(observed_label, null_mode, metric, higher_is_better=True):
    nulls = comparison[comparison["mode"] == null_mode][metric]
    observed = float(comparison.loc[observed_label, metric])
    count = int((nulls >= observed).sum() if higher_is_better else (nulls <= observed).sum())
    return {
        "run": observed_label, "null": null_mode, "metric": metric, "observed": observed,
        "null_median": float(nulls.median()), "null_best": float(nulls.max() if higher_is_better else nulls.min()),
        "exceedances": count, "draws": len(nulls), "p": (1 + count) / (len(nulls) + 1),
    }

null_rows = []
for label, null_mode in (("incumbent_30", "random null n=30"), (m_match, "random null n=9")):
    for metric, better_high in (("cagr", True), ("martin", True), ("cycle_sharpe", True),
                                ("ulcer", False), ("abs_invested_beta", False)):
        null_rows.append(null_percentile(label, null_mode, metric, better_high))
display(pd.DataFrame(null_rows).set_index(["run", "metric"]).round(4))
'''))

cells.append(md("""# Equity curves
"""))
cells.append(code('''import plotly.graph_objects as go

MODE_COLOURS = {
    "anchor": "#111111", "incumbent": "#1f77b4", "measured only": "#2ca02c",
    "unmeasured only": "#d62728", "random null n=30": "#bbbbbb", "random null n=9": "#dddddd",
}
equity_by_label = {e["label"]: e["equity"] for e in runs}

def equity_figure(labels, title):
    fig = go.Figure()
    for label in labels:
        curve = equity_by_label[label]
        is_anchor = label == "anchor"
        fig.add_trace(go.Scatter(
            x=curve.index, y=curve.to_numpy(), name=label, mode="lines",
            line=dict(color=MODE_COLOURS.get(mode_by_label[label], "#888888"),
                      width=4 if is_anchor else 1.6),
            opacity=1.0 if is_anchor else 0.75, legendgroup=mode_by_label[label],
            hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(title=title, hovermode="x unified", legend=dict(font=dict(size=9)))
    fig.update_yaxes(title="Equity (USD)", tickformat="$,.0f")
    fig.update_xaxes(title="Time")
    return fig

equity_figure(list(equity_by_label), "Every variant against the anchor").show()
equity_figure(["anchor", "incumbent_30", m_match, u_match],
              "The decomposition: incumbent_30 against each half alone").show()
for mode_name in ("incumbent", "measured only", "unmeasured only"):
    labels = ["anchor"] + [l for l, m in mode_by_label.items() if m == mode_name]
    equity_figure(labels, f"{mode_name} against the anchor").show()
equity_figure(["anchor", "incumbent_30"] + [l for l, m in mode_by_label.items()
              if m == "random null n=30"], "incumbent_30 against its random null").show()
'''))

cells.append(md("""# Underwater curves
"""))
cells.append(code('''fig = go.Figure()
for label, curve in equity_by_label.items():
    drawdown = curve / curve.cummax() - 1.0
    is_anchor = label == "anchor"
    fig.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown.to_numpy(), name=label, mode="lines",
        line=dict(color=MODE_COLOURS.get(mode_by_label[label], "#888888"),
                  width=4 if is_anchor else 1.2),
        opacity=1.0 if is_anchor else 0.6, legendgroup=mode_by_label[label],
        hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}<br>%{y:.2%}<extra></extra>",
    ))
fig.update_layout(title="Drawdown from running peak", hovermode="x unified",
                  legend=dict(font=dict(size=9)))
fig.update_yaxes(title="Drawdown", tickformat=".1%")
fig.update_xaxes(title="Time")
fig.show()
'''))

cells.append(md("""# Asset weights

Per-vault share of total equity at every decision, from `state.stats.positions` valued against
`state.stats.portfolio` equity at the same timestamp. This is the realised book, not the target
weights, so it already reflects the minimum-hold rule and any blocked deposit window.
"""))
cells.append(code('''def weight_frame(label: str) -> pd.DataFrame:
    """Realised per-vault weight over time, columns are vault names, rows are decision dates."""
    state_ = run_by_label[label]["state"]
    equity_at = {}
    for stat in state_.stats.portfolio:
        if stat.total_equity:
            equity_at[pd.Timestamp(stat.calculated_at)] = float(stat.total_equity)
    rows = {}
    for position_id, series in state_.stats.positions.items():
        position = state_.portfolio.get_position_by_id(position_id)
        if position.is_credit_supply():
            continue
        base = getattr(position.pair, "base", None)
        symbol = getattr(base, "token_symbol", None) if base is not None else None
        name = str(symbol) if symbol else str(position.pair.pool_address)[:10]
        for stat in series:
            ts = pd.Timestamp(stat.calculated_at)
            equity = equity_at.get(ts)
            if not equity:
                continue
            rows.setdefault(ts, {})
            rows[ts][name] = rows[ts].get(name, 0.0) + float(stat.value) / equity
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).T.sort_index().fillna(0.0)
    return frame.loc[:, frame.max().sort_values(ascending=False).index]


def weight_chart(label: str, top: int = 12):
    frame = weight_frame(label)
    if frame.empty:
        print(f"{label}: no position statistics")
        return
    keep = list(frame.columns[:top])
    plot = frame[keep].copy()
    if len(frame.columns) > top:
        plot["other"] = frame[frame.columns[top:]].sum(axis=1)
    fig = go.Figure()
    for column in plot.columns:
        fig.add_trace(go.Scatter(
            x=plot.index, y=plot[column].to_numpy(), name=str(column), mode="lines",
            stackgroup="one", line=dict(width=0.5),
            hovertemplate="%{fullData.name}<br>%{x|%Y-%m-%d}<br>%{y:.1%}<extra></extra>",
        ))
    fig.update_layout(title=f"Asset weights: {label} (top {top} by peak weight, rest stacked as 'other')",
                      hovermode="x unified", legend=dict(font=dict(size=8)))
    fig.update_yaxes(title="Share of total equity", tickformat=".0%")
    fig.update_xaxes(title="Time")
    fig.show()


WEIGHT_CHART_LABELS = (["anchor"]
                       + [l for l, m in mode_by_label.items() if m in ("incumbent", "measured only", "unmeasured only")]
                       + ["random30_s0", "random9_s0"])
print(f"Stacked weight charts for {len(WEIGHT_CHART_LABELS)} variants. The remaining "
      f"{len(RANDOM_SEEDS) * 2 - 2} random-null draws are summarised numerically below instead of "
      f"charted: they are a null, they differ only by seed, and 38 stacked-area figures would "
      f"make the notebook unreadable and very large.")
for label in WEIGHT_CHART_LABELS:
    weight_chart(label)
'''))

cells.append(md("""## Weight concentration, every variant

The numeric summary that covers the runs not charted above, and makes the charts comparable.
`mean_holdings` is how many vaults were actually funded, `mean_top1` the largest single weight,
and `mean_hhi` the Herfindahl index of the weight vector - 1/6 is a perfectly even six-name book,
1.0 is everything in one name.
"""))
cells.append(code('''rows = []
for entry in runs:
    frame = weight_frame(entry["label"])
    if frame.empty:
        continue
    invested = frame.sum(axis=1).replace(0.0, np.nan)
    normalised = frame.div(invested, axis=0).fillna(0.0)
    rows.append({
        "label": entry["label"], "mode": entry["family"],
        "mean_holdings": float((frame > 1e-9).sum(axis=1).mean()),
        "mean_top1": float(normalised.max(axis=1).mean()),
        "mean_hhi": float((normalised ** 2).sum(axis=1).mean()),
        "distinct_vaults_held": int((frame > 1e-9).any().sum()),
        "mean_invested": float(invested.mean()),
    })
weights = pd.DataFrame(rows).set_index("label")
display(weights.round(4).sort_values("mean_hhi"))
display(weights.groupby("mode")[["mean_holdings", "mean_top1", "mean_hhi",
                                 "distinct_vaults_held"]].median().round(4))
'''))

cells.append(md("""# Sub-period stability

A real effect should survive being cut in time. The plan's three segments are the sparse polling
regime before April, the dense regime to the end of June, and the late period from July.
"""))
cells.append(code('''SEG = ["sparse_cagr", "sparse_ulcer", "dense_cagr", "dense_ulcer", "late_cagr", "late_ulcer"]
focus = ["anchor", "incumbent_30", m_match, u_match]
display(comparison.loc[focus, SEG].round(4))

segment_rows = []
for mode_name in ("incumbent", "measured only", "unmeasured only", "random null n=30", "random null n=9"):
    subset = comparison[comparison["mode"] == mode_name]
    segment_rows.append({
        "mode": mode_name, "runs": len(subset),
        **{c: float(subset[c].median()) for c in SEG},
        "positive in all three": int(((subset["sparse_cagr"] > 0) & (subset["dense_cagr"] > 0)
                                      & (subset["late_cagr"] > 0)).sum()),
    })
display(pd.DataFrame(segment_rows).set_index("mode").round(4))
'''))

cells.append(md("""# Uncertainty and leave-one-vault-out

Paired block bootstrap against the anchor for the three focus runs, then a full re-simulation of
each with its largest contributing vault masked. A result that disappears when one vault is
removed was that vault.
"""))
cells.append(code('''for label in ("incumbent_30", m_match, u_match):
    display(bootstrap_margin_table(label, family))

for label in ("incumbent_30", m_match, u_match):
    top = largest_contributing_vault(run_by_label[label]["state"])
    masked_label = f"{label}__without_top_vault"
    run_and_record(masked_label, "robustness", masked={top}, **run_by_label[label]["overrides"])
    before, after = run_by_label[label]["panel"], run_by_label[masked_label]["panel"]
    print(f"{label}: masked {top}")
    display(pd.DataFrame([before, after]).set_index("label")[
        ["cagr", "ulcer", "martin", "cycle_vol", "cycle_sharpe", "abs_invested_beta", "late_cagr"]])
'''))

cells.append(md("""# Verdict
"""))
cells.append(code('''summary = {
    "incumbent_30 CAGR": float(comparison.loc["incumbent_30", "cagr"]),
    f"{m_match} (measured half) CAGR": float(comparison.loc[m_match, "cagr"]),
    f"{u_match} (unmeasured half) CAGR": float(comparison.loc[u_match, "cagr"]),
    "anchor CAGR": float(anchor_panel["cagr"]),
    "random n=30 median CAGR": float(comparison[comparison["mode"] == "random null n=30"]["cagr"].median()),
    "random n=30 best CAGR": float(comparison[comparison["mode"] == "random null n=30"]["cagr"].max()),
}
display(pd.Series(summary).round(4).to_frame("value"))

import json
from pathlib import Path
manifest = {
    "verdict": "see the heading",
    "measured_match": m_match, "unmeasured_match": u_match,
    "composition": composition.round(6).to_dict(orient="index"),
    "metrics": comparison[["mode", "cagr", "ulcer", "martin", "cycle_vol", "cycle_sharpe",
                           "abs_invested_beta", "mean_invested", "late_cagr", "late_ok",
                           "passes_1_to_6", "failed_1_to_6"]].to_dict(orient="index"),
    "null_percentiles": null_rows,
    "weights": weights.round(6).to_dict(orient="index"),
}
Path("_build/manifest_26.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_26.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "26-backtest-drop-decomposition.ipynb")
