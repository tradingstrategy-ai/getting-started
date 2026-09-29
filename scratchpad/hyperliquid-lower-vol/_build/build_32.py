import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_floor import PARAM_ADDITIONS_FLOOR, INDICATOR_ADDITIONS_FLOOR, CELL14_REPLACEMENTS_FLOOR

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()

HEADING = """# NB32 - return floor, then rank by stability: the practical comparison

**Based on:** [29-backtest-stability-prefilter.ipynb](29-backtest-stability-prefilter.ipynb) for
the harness, and the 2026-09-14 out-of-sample sketch that motivated it. Anchor
[02-better-format.ipynb](02-better-format.ipynb). Full window 2026-01-01 to 2026-09-08,
in-sample throughout.

## Why this notebook exists

The sketch ranked every Hyperliquid vault on a 45-day formation window and held the top six
equal-weight over the next, disjoint 45 days, six times over. One family of rules was positive
in most splits: **a hard annualised return floor, then rank the survivors by a stability
measure.** With a 15% floor and a volatility ranker it returned 27.4% annualised at volatility
0.138 and a 3.8% maximum drawdown, against the anchor's 37.9% / 0.154 / 4.45%. And the height of
the floor, not the choice of stability measure, made the difference: the same ranker behind a 0%
floor earned 2.6%.

That sketch was equal-weight buy-and-hold with no fees, no rebalancing and no momentum gate. This
notebook runs the same idea through the real strategy - two-day rebalancing, inverse-variance
sizing, the TVL and tradability screen, redemption fees - and sweeps the magic numbers the sketch
fixed by hand.

## The mechanism, and why it needs no new code

The strategy already has both halves of the rule as parameters:

- **the floor** is `return_gate`: a candidate is admitted only if its trailing return over
  `gate_lookback_days` exceeds `gate_threshold`. The anchor uses a 14-day lookback and a threshold
  of **-0.16** - it admits anything that has not lost 16% in two weeks, which is drawdown
  insurance, not a return floor. Here the lookback is 45 days and the threshold is set so that
  clearing it means an annualised return above the floor: `(1 + floor)^(45/365) - 1`.
- **the ranker** is `selection_score_indicator`: the anchor ranks by `cagr_sortino_weight`, which
  is 60% CAGR. Here it is swapped for one of four stability scores.

Three of those rankers are new indicators (`calm_score`, `inverse_ulcer_score`,
`inverse_downside_score`) and exist only because the raw `inverse_vol` cannot be a ranker: a
vault whose mark has not moved in 90 days has sigma = 0, is floored, and scores 10,000 - the
calmest vault in the universe, ranked first every cycle. The new scores are NaN unless at least
30 marks moved inside the window.

Sizing is untouched - `inverse_variance` does not read the selection score - so every run below
changes WHICH vaults are held and nothing about how much of each.

## What is swept

| axis | values |
|---|---|
| ranker | incumbent composite, calm (1/vol), inverse ulcer, inverse downside, gain-to-pain, Sortino |
| floor, annualised | none (anchor gate), 0%, 10%, 15%, 20%, 30% |
| `max_assets_in_portfolio` | 4, 6, 8, 10, 12 - at the 15% floor |
| `gate_lookback_days` | 30, 45, 60, 90 - calm ranker, 15% floor |

**This is an exploratory comparison, not a gated candidate.** Nothing here is pre-registered as
a centre, nothing is shortlisted, and every number is in-sample on one window whose minimum
detectable Sharpe difference is about 2.50. The purpose is to see the SHAPE of the trade-off -
where return, volatility and drawdown go as the floor rises and the basket widens - well enough
to write a pre-registration for the next plan.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "32-backtest-return-floor-stability-rank",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_FLOOR},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_FLOOR)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))

cells.append(md("""## Part 0. Provenance, parity, and the grid

The anchor must reproduce `BASELINE` with the three new ranker indicators present: they are
additive and nothing reads them until `selection_score_indicator` names one.

Runs are recorded slim - the panel, equity, cycle returns, diversification and the largest
contributor are kept and the backtest state is released - because sixty-odd retained states
would exhaust memory before the grid finished.
"""))
cells.append(code('''import json
from pathlib import Path
import plotly.graph_objects as go

display(provenance())
display(assert_anchor_parity_rules())
record_anchor()

FLOOR_LOOKBACK = 45


def floor_threshold(annual: float, days: int = FLOOR_LOOKBACK) -> float:
    """Trailing-return threshold over `days` that corresponds to an annualised return floor."""
    return (1.0 + annual) ** (days / 365.0) - 1.0


#: ranker key -> (indicator name, require_scored_candidates)
RANKERS = {
    "incumbent": ("cagr_sortino_weight", False),
    "calm":      ("calm_score", True),
    "ulcer":     ("inverse_ulcer_score", True),
    "downside":  ("inverse_downside_score", True),
    "gtp":       ("gain_to_pain_score", True),
    "sortino":   ("sortino_score", True),
}
#: floor key -> annualised floor, or None for the anchor's own -16% / 14-day drawdown gate
FLOORS = {"none": None, "0": 0.0, "10": 0.10, "15": 0.15, "20": 0.20, "30": 0.30}
SIZES = (4, 6, 8, 10, 12)

print("thresholds over a 45-day lookback:")
for key, annual in FLOORS.items():
    if annual is not None:
        print(f"  {key:>4}% annualised -> gate_threshold {floor_threshold(annual):+.5f}")


def overrides_for(ranker: str, floor: str, size: int = 6, lookback: int = FLOOR_LOOKBACK, **extra) -> dict:
    indicator, require_scored = RANKERS[ranker]
    out = {"selection_score_indicator": indicator, "require_scored_candidates": require_scored,
           "max_assets_in_portfolio": int(size)}
    if FLOORS[floor] is not None:
        out["gate_lookback_days"] = int(lookback)
        out["gate_threshold"] = floor_threshold(FLOORS[floor], lookback)
    out.update(extra)
    return out


def label_for(ranker: str, floor: str, size: int = 6, suffix: str = "") -> str:
    return f"{ranker}__floor{floor}__n{size}{suffix}"


def held_vol_only(state_) -> dict:
    """Capital-weighted own daily volatility of what was held, with its OWN coverage.

    `held_book_character()` in harness_rules.py drops a date when EITHER volatility or event
    concentration covers less than 75% of held weight, so its `held_vol` is conditioned on the
    concentration indicator's missingness, which is unrelated to volatility and severe. This
    measures volatility alone, on every date where volatility alone covers 75% of the weight,
    and reports how many dates that is.
    """
    weights = _position_weights(state_)
    by_date, dropped = {}, []
    for timestamp in sorted(weights):
        holdings = weights[timestamp]
        total = sum(share for _p, share in holdings)
        if total <= 0:
            continue
        accumulated, covered = 0.0, 0.0
        for pair, share in holdings:
            inverse = value_at_prior(indicator_series("inverse_vol", pair), timestamp)
            if np.isfinite(inverse) and inverse > 0:
                accumulated += share * (1.0 / inverse)
                covered += share
        dropped.append(1.0 - covered / total)
        if covered / total >= 0.75:
            by_date[pd.Timestamp(timestamp)] = accumulated / covered
    series = pd.Series(by_date, dtype=float).sort_index()
    return {"held_vol_only": float(series.mean()) if len(series) else np.nan,
            "held_vol_dates": int(len(series)),
            "held_vol_dropped_weight": float(np.mean(dropped)) if dropped else np.nan,
            "held_vol_series": series}


def held_vol_common(labels: list) -> pd.DataFrame:
    """Held volatility for several configurations on the INTERSECTION of their covered dates.

    Averaging each configuration over its own covered dates mixes a composition difference with
    a calendar-sample difference; the first review asked for this and the second found it still
    missing. One row per label, all on the same dates.
    """
    series = {label: run_by_label[label]["held_only"]["held_vol_series"] for label in labels}
    common = None
    for s_ in series.values():
        common = s_.index if common is None else common.intersection(s_.index)
    rows = [{"label": label, "held_vol_common_dates": float(s_.reindex(common).mean()),
             "own_dates": int(len(s_)), "common_dates": int(len(common))} for label, s_ in series.items()]
    return pd.DataFrame(rows).set_index("label")


def invested_basket_vol(state_, equity_) -> dict:
    """Annualised cycle volatility of the INVESTED part of the book: cycle return divided by the
    prior cycle's invested fraction, so cash does not mechanically lower it. Same construction as
    `invested_basket_beta()` in harness.py."""
    r, periods = cycle_returns(equity_)
    rows = {pd.Timestamp(s.calculated_at): 1.0 - float(s.free_cash or 0.0) / float(s.total_equity)
            for s in state_.stats.portfolio if s.total_equity}
    invested = pd.Series(rows).sort_index()
    invested = invested[~invested.index.duplicated()].reindex(r.index).ffill()
    usable = invested.shift(1) > 0.2
    scaled = (r / invested.shift(1)).where(usable).dropna()
    return {"invested_vol": float(scaled.std(ddof=1) * np.sqrt(periods)) if len(scaled) > 10 else np.nan,
            "invested_vol_cycles": int(len(scaled)), "invested_vol_excluded": int(len(r) - len(scaled)),
            "invested_scaled_series": scaled, "raw_cycle_series": r}


def invested_vol_common(labels: list) -> pd.DataFrame:
    """Raw and invested-basket volatility for several configurations on the SAME cycles.

    The third review found the invested-basket diagnostic compared 106 usable cycles for the
    calm ranker against 124 for the anchor, so the difference mixed cash with calendar. This
    intersects the usable cycles first and reports both volatilities on that common set.
    """
    common = None
    for label in labels:
        idx = run_by_label[label]["invested_scaled_series"].index
        common = idx if common is None else common.intersection(idx)
    rows = []
    for label in labels:
        e = run_by_label[label]
        raw = e["raw_cycle_series"].reindex(common)
        scaled = e["invested_scaled_series"].reindex(common)
        rows.append({"label": label, "common_cycles": int(len(common)),
                     "raw_vol_common": float(raw.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR)),
                     "invested_vol_common": float(scaled.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))})
    frame = pd.DataFrame(rows).set_index("label")
    return frame


def run_slim(label: str, family: str, ranker: str, floor: str, size: int = 6, **extra) -> dict:
    """Run, record, extract what the tables need, and release the state."""
    if label in run_by_label:
        return run_by_label[label]
    entry = run_and_record(label, family, **overrides_for(ranker, floor, size, **extra))
    entry["ranker"], entry["floor"], entry["size"] = ranker, floor, int(size)
    entry["diversification"] = diversification_cached(entry)
    entry["inertness"] = inertness(entry)
    entry["character"] = held_book_character_cached(entry)
    entry["held_only"] = held_vol_only(entry["state"])
    entry.update(invested_basket_vol(entry["state"], entry["equity"]))
    entry["largest_vault"] = largest_contributing_vault(entry["state"])
    entry["state"] = None
    return entry


def grid_frame(labels) -> pd.DataFrame:
    rows = []
    for label in labels:
        e = run_by_label[label]
        row = e["panel"].copy()
        row["ranker"] = e.get("ranker", "incumbent")
        row["floor"] = e.get("floor", "none")
        row["size"] = e.get("size", 6)
        for k, v in (e.get("diversification") or {}).items():
            row[k] = v
        row["inert"] = (e.get("inertness") or {}).get("inert", False)
        row["held_vol"] = (e.get("character") or {}).get("held_vol", np.nan)
        row["held_dates_used"] = (e.get("character") or {}).get("dates_used", np.nan)
        row["held_vol_only"] = (e.get("held_only") or {}).get("held_vol_only", np.nan)
        row["held_vol_dates"] = (e.get("held_only") or {}).get("held_vol_dates", np.nan)
        row["invested_vol"] = e.get("invested_vol", np.nan)
        row["invested_vol_cycles"] = e.get("invested_vol_cycles", np.nan)
        rows.append(row)
    frame = pd.DataFrame(rows).set_index("label")
    return frame[~frame.index.duplicated()]


# The anchor is the incumbent ranker behind its own gate with six names.
anchor_entry = run_by_label["anchor"]
anchor_entry["ranker"], anchor_entry["floor"], anchor_entry["size"] = "incumbent", "none", 6
anchor_entry["diversification"] = diversification_cached(anchor_entry)
anchor_entry["inertness"] = {"inert": True}
anchor_entry["character"] = held_book_character_cached(anchor_entry)
anchor_entry["held_only"] = held_vol_only(anchor_entry["state"])
anchor_entry.update(invested_basket_vol(anchor_entry["state"], anchor_entry["equity"]))
anchor_entry["largest_vault"] = largest_contributing_vault(anchor_entry["state"])
run_by_label[label_for("incumbent", "none", 6)] = anchor_entry
'''))

cells.append(md("""## Part 1. The main grid: six rankers by six floors, six names

Thirty-five backtests plus the anchor. Read the pivots by row (a ranker across rising floors)
and by column (rankers at one floor). The sketch's prediction is that the FLOOR column matters
more than the RANKER row.
"""))
cells.append(code('''MAIN = []
for ranker in RANKERS:
    for floor in FLOORS:
        label = label_for(ranker, floor, 6)
        run_slim(label, "anchor" if label == label_for("incumbent", "none", 6) else "exploratory",
                 ranker, floor, 6)
        MAIN.append(label)
main = grid_frame(MAIN)
COLUMNS = ["ranker", "floor", "cagr", "cycle_sharpe", "cycle_vol", "invested_vol", "ulcer", "max_dd",
           "mean_invested", "mean_holdings", "distinct_vaults", "top_vault_pnl_share",
           "held_vol_only", "held_vol_dates", "sparse_cagr", "dense_cagr", "late_cagr", "inert"]
pd.set_option("display.width", 250)
display(main[COLUMNS].round(4))
'''))

cells.append(code('''floor_order = list(FLOORS)
ranker_order = list(RANKERS)


def pivot(frame, metric):
    p = frame.pivot(index="ranker", columns="floor", values=metric)
    return p.reindex(index=ranker_order, columns=floor_order)


for metric in ("cycle_sharpe", "cagr", "cycle_vol", "invested_vol", "invested_vol_cycles", "mean_invested",
               "ulcer", "max_dd", "mean_holdings", "distinct_vaults", "top_vault_pnl_share",
               "held_vol_only", "held_vol_dates"):
    print(f"\\n=== {metric}  (rows: ranker, columns: annualised floor) ===")
    display(pivot(main, metric).round(4))

# Held volatility on COMMON dates: each grid run against the anchor on the dates both cover.
common_rows = []
for label in main.index:
    if label == "anchor":
        continue
    pair_frame = held_vol_common([label, "anchor"])
    common_rows.append({"label": label, "ranker": main.loc[label, "ranker"], "floor": main.loc[label, "floor"],
                        "held_vol_common": pair_frame.loc[label, "held_vol_common_dates"],
                        "anchor_on_same_dates": pair_frame.loc["anchor", "held_vol_common_dates"],
                        "common_dates": pair_frame.loc[label, "common_dates"]})
common_frame = pd.DataFrame(common_rows).set_index("label")
common_frame["ratio_to_anchor"] = common_frame["held_vol_common"] / common_frame["anchor_on_same_dates"]
print("\\n=== held volatility on dates common to the run AND the anchor (daily sigma) ===")
display(common_frame.pivot(index="ranker", columns="floor", values="ratio_to_anchor")
        .reindex(index=ranker_order, columns=floor_order).round(3))
display(common_frame.pivot(index="ranker", columns="floor", values="common_dates")
        .reindex(index=ranker_order, columns=floor_order))
'''))

cells.append(md("""## Part 2. Equity curves

Every ranker at the 15% floor, against the anchor. The 15% floor is shown because it is what the
sketch used - it is not chosen from Part 1's table.
"""))
cells.append(code('''COLOURS = {"incumbent": "#111111", "calm": "#1f77b4", "ulcer": "#2ca02c",
           "downside": "#9467bd", "gtp": "#ff7f0e", "sortino": "#d62728"}


def equity_figure(labels, title):
    fig = go.Figure()
    for label in ["anchor"] + [l for l in labels if l != "anchor"]:
        e = run_by_label[label]
        curve = e["equity"] / float(e["equity"].iloc[0])
        is_anchor = label == "anchor"
        fig.add_trace(go.Scatter(
            x=curve.index, y=curve.to_numpy(), mode="lines",
            name=f"{label}  ({float(e['panel']['cagr'])*100:.1f}% / vol {float(e['panel']['cycle_vol']):.3f})",
            line=dict(color="#111111" if is_anchor else COLOURS.get(e.get("ranker"), "#888"),
                      width=4 if is_anchor else 1.8),
            opacity=1.0 if is_anchor else 0.8,
        ))
    fig.update_layout(title=title, height=560, yaxis_title="equity, normalised to 1.0",
                      legend=dict(orientation="v", x=0.01, y=0.99), template="plotly_white")
    fig.show()


equity_figure([label_for(r, "15", 6) for r in RANKERS], "Every ranker at a 15% annualised floor, six names, vs the anchor")
equity_figure([label_for("calm", f, 6) for f in FLOORS], "Calm ranker across floors, six names, vs the anchor")
'''))

cells.append(md("""## Part 3. Breadth: 4 to 12 names at the 15% floor

`RESEARCH-RULES.md` consequence 3 recorded that widening the anchor's basket costs 27 to 37 points
of CAGR. That was measured with the incumbent ranker, whose seventh-best name by CAGR-composite
is a much worse vault than its sixth. A stability ranker behind a return floor may have a
flatter tail - or a steeper one. Five sizes per ranker.
"""))
cells.append(code('''BREADTH = []
for ranker in RANKERS:
    for size in SIZES:
        label = label_for(ranker, "15", size)
        run_slim(label, "exploratory", ranker, "15", size)
        BREADTH.append(label)
breadth = grid_frame(BREADTH)
display(breadth[COLUMNS].round(4))

for metric in ("cycle_sharpe", "cagr", "cycle_vol", "ulcer", "max_dd", "mean_holdings",
               "distinct_vaults", "top_vault_pnl_share"):
    print(f"\\n=== {metric}  (rows: ranker, columns: max_assets_in_portfolio, 15% floor) ===")
    display(breadth.pivot(index="ranker", columns="size", values=metric)
            .reindex(index=ranker_order, columns=list(SIZES)).round(4))
'''))

cells.append(code('''equity_figure([label_for("calm", "15", s) for s in SIZES], "Calm ranker, 15% floor, basket size 4 to 12, vs the anchor")
equity_figure([label_for("ulcer", "15", s) for s in SIZES], "Inverse-ulcer ranker, 15% floor, basket size 4 to 12, vs the anchor")
'''))

cells.append(md("""## Part 4. Lookback sensitivity

The sketch's 45-day formation window is a magic number. The calm ranker at the 15% floor with
the gate measured over 30, 60 and 90 days instead - the threshold is recomputed for each so the
annualised floor stays at 15% - and one run with the volatility window shortened to 45 days.
"""))
cells.append(code('''LOOKBACK = []
for lookback in (30, 45, 60, 90):
    label = label_for("calm", "15", 6, f"__lb{lookback}")
    if lookback == 45:
        run_by_label[label] = run_by_label[label_for("calm", "15", 6)]
    else:
        run_slim(label, "exploratory", "calm", "15", 6, lookback=lookback)
    LOOKBACK.append(label)
label = label_for("calm", "15", 6, "__vol45")
run_slim(label, "exploratory", "calm", "15", 6, inverse_vol_window=45)
LOOKBACK.append(label)
lookback_frame = grid_frame(LOOKBACK)
lookback_frame["gate_lookback_days"] = [run_by_label[l]["overrides"].get("gate_lookback_days", 14) for l in LOOKBACK]
lookback_frame["inverse_vol_window"] = [run_by_label[l]["overrides"].get("inverse_vol_window", 90) for l in LOOKBACK]
display(lookback_frame[["gate_lookback_days", "inverse_vol_window", "cagr", "cycle_sharpe", "cycle_vol",
                        "ulcer", "max_dd", "mean_holdings", "distinct_vaults", "top_vault_pnl_share"]].round(4))
'''))

cells.append(md("""## Part 5. What the best-looking configurations are made of

Post-hoc by construction - these are the top configurations by cycle Sharpe in an exploratory
grid, and are labelled as such. The checks are the ones that have caught every false positive in
this track: the sub-period signs, luck and concentration measures, leave-one-vault-out by full
re-simulation, and the paired bootstrap against the anchor. None of them is a gate here; all of
them are what a pre-registration for the next plan would gate on.
"""))
cells.append(code('''everything = grid_frame(sorted(set(MAIN + BREADTH + LOOKBACK)))
everything = everything[~everything["inert"]]
ranked = everything.sort_values("cycle_sharpe", ascending=False)
TOP = list(ranked.index[:5])
print("top five by cycle Sharpe (exploratory, in-sample, post-hoc):")
display(ranked.loc[TOP, ["ranker", "floor", "size", "cagr", "cycle_sharpe", "cycle_vol", "ulcer",
                         "max_dd", "sparse_cagr", "dense_cagr", "late_cagr", "luck_ratio",
                         "top5_gross_share", "mean_holdings", "distinct_vaults",
                         "top_vault_pnl_share"]].round(4))

# Leave-one-vault-out by full re-simulation, largest total-P&L contributor masked.
lovo_rows = []
for label in TOP:
    e = run_by_label[label]
    masked = e["largest_vault"]
    lovo_label = f"{label}__lovo"
    if lovo_label not in run_by_label:
        entry = run_and_record(lovo_label, "robustness", masked={masked}, **e["overrides"])
        entry["state"] = None
    l = run_by_label[lovo_label]
    lovo_rows.append({
        "label": label, "masked": masked,
        "cagr": float(e["panel"]["cagr"]), "lovo_cagr": float(l["panel"]["cagr"]),
        "cagr_retention": float(l["panel"]["cagr"]) / float(e["panel"]["cagr"]) if float(e["panel"]["cagr"]) > 0 else np.nan,
        "sharpe": float(e["panel"]["cycle_sharpe"]), "lovo_sharpe": float(l["panel"]["cycle_sharpe"]),
        "sharpe_retention": float(l["panel"]["cycle_sharpe"]) / float(e["panel"]["cycle_sharpe"]) if float(e["panel"]["cycle_sharpe"]) > 0 else np.nan,
    })
anchor_lovo_label = "anchor__lovo"
if anchor_lovo_label not in run_by_label:
    entry = run_and_record(anchor_lovo_label, "robustness", masked={anchor_entry["largest_vault"]})
    entry["state"] = None
l = run_by_label[anchor_lovo_label]
lovo_rows.append({"label": "anchor", "masked": anchor_entry["largest_vault"],
                  "cagr": float(anchor_panel["cagr"]), "lovo_cagr": float(l["panel"]["cagr"]),
                  "cagr_retention": float(l["panel"]["cagr"]) / float(anchor_panel["cagr"]),
                  "sharpe": float(anchor_panel["cycle_sharpe"]), "lovo_sharpe": float(l["panel"]["cycle_sharpe"]),
                  "sharpe_retention": float(l["panel"]["cycle_sharpe"]) / float(anchor_panel["cycle_sharpe"])})
print("\\nleave-one-vault-out, largest contributor masked, full re-simulation:")
display(pd.DataFrame(lovo_rows).set_index("label").round(4))
'''))

cells.append(code('''rows = []
for label in TOP:
    for block in (5, 10, 20):
        r = bootstrap_paired_sharpe_diff(run_by_label[label]["cycle_returns"], anchor_cycle_returns, block=block)
        rows.append({"run": label, "block": block, "observed_diff": r["observed"],
                     "ci_lo": r["lo"], "ci_hi": r["hi"],
                     "excludes_zero": bool(np.isfinite(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0))})
print("paired block bootstrap on cycle Sharpe against the anchor - context, not a gate:")
display(pd.DataFrame(rows).round(4))

# Held-book character for the top five and the anchor: does the rule actually hold calmer vaults?
character_rows = [{"label": label, **run_by_label[label]["character"]} for label in ["anchor"] + TOP]
print("\\ncapital-weighted own volatility and event concentration of what was HELD (daily sigma):")
display(pd.DataFrame(character_rows).set_index("label").round(6))
'''))

cells.append(md("""## Part 6. Why the sketch and the engine disagree: fees and the pool cap

The sketch had no redemption fees and no pool cap. The engine charges a 10% performance fee on
profitable redemptions plus 10 bps of redeemed capital - a track-wide assumption since NB01, kept
here for comparability with the anchor - and caps each slot at 33% of the vault's pool. Both
bear differentially on a stability ranker: it rotates through more vaults, so it pays more
redemption fees, and it favours small calm vaults, so the cap binds and cash accumulates.

This measures each effect by switching it off, for the calm ranker and the incumbent at the 15%
floor, and for the anchor. A run with fees off is NOT comparable with the anchor's `BASELINE`;
it is comparable only with the other fee-off runs in this table.
"""))
cells.append(code('''NO_FEE = dict(vault_performance_fee=0.0, vault_redemption_capital_fee=0.0)
# 1.0 is NOT "cap off": the size-risk model takes min(TVL x cap, asked), so 1.0 still caps a slot
# at the vault's whole TVL, which binds for any vault smaller than a slot. 1e6 cannot bind for
# any vault with more than a few dollars of TVL against a book of about $190k.
NO_CAP = dict(per_position_cap_of_pool_pct=1_000_000.0)
DECOMP = []
for ranker, floor in (("calm", "15"), ("incumbent", "15"), ("incumbent", "none")):
    base = label_for(ranker, floor, 6)
    DECOMP.append(base if base != label_for("incumbent", "none", 6) else "anchor")
    for suffix, extra in (("__nofee", NO_FEE), ("__nocap", NO_CAP), ("__nofee_nocap", {**NO_FEE, **NO_CAP})):
        label = label_for(ranker, floor, 6, suffix)
        run_slim(label, "diagnostic", ranker, floor, 6, **extra)
        DECOMP.append(label)
decomp = grid_frame(DECOMP)
decomp["fees"] = ["off" if "nofee" in l else "on" for l in decomp.index]
decomp["pool_cap"] = ["off (1e6 x TVL)" if "nocap" in l else "0.33 x TVL" for l in decomp.index]
display(decomp[["ranker", "floor", "fees", "pool_cap", "cagr", "cycle_sharpe", "cycle_vol",
                "invested_vol", "mean_invested", "ulcer", "max_dd", "distinct_vaults"]].round(4))

calm_on = float(decomp.loc[label_for("calm", "15", 6), "cagr"])
calm_nofee = float(decomp.loc[label_for("calm", "15", 6, "__nofee"), "cagr"])
calm_nocap = float(decomp.loc[label_for("calm", "15", 6, "__nocap"), "cagr"])
calm_both = float(decomp.loc[label_for("calm", "15", 6, "__nofee_nocap"), "cagr"])
print(f"\\ncalm ranker, 15% floor, six names - CAGR:")
print(f"  as run (fees on, cap 0.33) : {calm_on*100:6.2f}%")
print(f"  fees off                   : {calm_nofee*100:6.2f}%   ({(calm_nofee-calm_on)*100:+.2f} pp)")
print(f"  pool cap off               : {calm_nocap*100:6.2f}%   ({(calm_nocap-calm_on)*100:+.2f} pp)")
print(f"  both off                   : {calm_both*100:6.2f}%   ({(calm_both-calm_on)*100:+.2f} pp)")
print(f"  the sketch's figure        :  27.37%   (equal weight, 45-day hold, 45-day vol window, no engine)")
print("  the sketch is NOT the same rule: it differs in the volatility window, admission rules,")
print("  concentration limit, sizing and re-evaluation cadence, none of which this table varies.")

# Why the fee model stays: Hyperliquid vaults charge a leader commission on follower profit at
# withdrawal, which is NOT in the share price. The archive records it per vault.
_fees = pd.read_parquet(PROVENANCE_PATHS[0], columns=["address", "chain", "leader_commission"]).reset_index()
_fees = _fees[_fees["chain"] == 9999].groupby("address", observed=True)["leader_commission"].last()
print(f"\\nHyperliquid leader_commission in the archive, last value per vault ({len(_fees)} vaults):")
display(_fees.value_counts().rename("vaults").to_frame())
print("This table shows the REPORTED commission rates. That the commission is charged on follower")
print("profit at withdrawal, rather than internalised in the NAV series, is Hyperliquid's documented")
print("mechanism (hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults) and how the local")
print("exporter models it (eth_defi/hyperliquid/vault_data_export.py); this cell does not test that.")
print("The zero-commission vaults are the HLP protocol family. The notebook charges every vault 10%")
print("plus a 10 bp capital fee inherited from NB01; the capital fee has no documented basis.")

display(held_vol_common([label_for("calm", "15", 6), label_for("incumbent", "15", 6), "anchor"]).round(6))
display(decomp[["invested_vol", "invested_vol_cycles"]].round(4))

# Raw and invested-basket volatility on the SAME cycles, so the cash share is a like-for-like number.
invested_common = invested_vol_common([label_for("calm", "15", 6), label_for("calm", "20", 6),
                                       label_for("incumbent", "15", 6), "anchor"])
invested_common["reduction_raw_vs_anchor"] = 1.0 - invested_common["raw_vol_common"] / invested_common.loc["anchor", "raw_vol_common"]
invested_common["reduction_invested_vs_anchor"] = 1.0 - invested_common["invested_vol_common"] / invested_common.loc["anchor", "invested_vol_common"]
print("\\nraw and invested-basket volatility on common cycles (the cash share is the gap between the two reductions):")
display(invested_common.round(4))
'''))

cells.append(md("""## Part 7. Summary and manifest

The frontier the sketch predicted, read off the real strategy: for each floor, the best cycle
Sharpe and the lowest volatility any ranker reached, and what they cost in CAGR.
"""))
cells.append(code('''frontier = []
for floor in FLOORS:
    # The anchor is marked inert only so Part 5 cannot pick it as a "top" candidate; it belongs
    # in the frontier, as the incumbent at floor "none".
    sub = main[(main["floor"] == floor) & (~main["inert"] | (main.index == "anchor"))]
    if not len(sub):
        continue
    best = sub["cycle_sharpe"].idxmax(); calmest = sub["cycle_vol"].idxmin()
    frontier.append({
        "floor": floor,
        "best_sharpe_ranker": main.loc[best, "ranker"], "best_sharpe": float(main.loc[best, "cycle_sharpe"]),
        "its_cagr": float(main.loc[best, "cagr"]), "its_vol": float(main.loc[best, "cycle_vol"]),
        "calmest_ranker": main.loc[calmest, "ranker"], "lowest_vol": float(main.loc[calmest, "cycle_vol"]),
        "calmest_cagr": float(main.loc[calmest, "cagr"]), "calmest_sharpe": float(main.loc[calmest, "cycle_sharpe"]),
    })
frontier = pd.DataFrame(frontier).set_index("floor")
display(frontier.round(4))
print(f"\\nanchor: CAGR {float(anchor_panel['cagr']):.4f}, Sharpe {float(anchor_panel['cycle_sharpe']):.4f}, "
      f"vol {float(anchor_panel['cycle_vol']):.4f}, ulcer {float(anchor_panel['ulcer']):.4f}, max DD {float(anchor_panel['max_dd']):.4f}")

manifest = {
    "verdict": "EXPLORATORY - nothing shortlisted; input to the next pre-registration",
    "floor_lookback_days": FLOOR_LOOKBACK,
    "thresholds": {k: floor_threshold(v) for k, v in FLOORS.items() if v is not None},
    "main_grid": main[COLUMNS + ["luck_ratio", "top5_gross_share", "abs_invested_beta"]].round(6).to_dict(orient="index"),
    "breadth": breadth[COLUMNS].round(6).to_dict(orient="index"),
    "lookback": lookback_frame.round(6).to_dict(orient="index"),
    "top_by_sharpe": TOP,
    "held_vol_common": common_frame.round(6).to_dict(orient="index"),
    "decomposition": decomp[["ranker", "floor", "fees", "pool_cap", "cagr", "cycle_sharpe", "cycle_vol",
                             "invested_vol", "invested_vol_cycles", "mean_invested", "ulcer", "max_dd"]].round(6).to_dict(orient="index"),
    "invested_vol_common": invested_common.round(6).to_dict(orient="index"),
    "lovo": lovo_rows,
    "frontier": frontier.round(6).to_dict(orient="index"),
    "all_runs": {
        e["label"]: {"family": e["family"],
                     "overrides": {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in e["overrides"].items()},
                     "panel": {k: float(e["panel"][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta", "mean_invested")}}
        for e in runs if e["label"] != "anchor"
    },
}
Path("_build/manifest_32.json").write_text(json.dumps(manifest, indent=1, default=str))
print(f"wrote _build/manifest_32.json with {len(manifest['all_runs'])} runs")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "32-backtest-return-floor-stability-rank.ipynb")
