import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE, \
    CELL14_REPLACEMENTS_EVIDENCE

HARNESS_EVIDENCE = (Path(__file__).parent / "harness_evidence.py").read_text()

HEADING = """# NB16 - backtest: evidence-weighted selection

Does replacing the incumbent composite with an evidence-weighted one - so young vaults are ranked
once their record is strong enough - improve Sharpe at a CAGR above 20%? Every score NB14 screened
is backtested here regardless of its gate result (NB14's gate is descriptive, not a hard admission
bar - see [14-evidence-weighted-plan.md](14-evidence-weighted-plan.md)); a score that failed the
gate is labelled `diagnostic_only` and is ineligible for ADOPT from this notebook.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) / [14-research-evidence-screen.ipynb](14-research-evidence-screen.ipynb),
full window (2026-01-01 to 2026-09-08). Part of
[14-evidence-weighted-plan.md](14-evidence-weighted-plan.md).

## What this notebook does

For each of the three scores NB14 screened (`sortino_shrunk`, `evidence_composite_0.6`,
`evidence_composite_0.3`): a centre point, its plateau neighbours (one parameter moved at a time),
a no-shrinkage control (`evidence_prior_strength=1`, reproducing NB13 section 6's naive-window
comparison with this notebook's own indicators), and a no-early-vol control (isolating what NB13's
second barrier costs on its own). Sizing is unchanged (`inverse_variance`) throughout - this
notebook isolates the selection question; NB17 isolates sizing.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "16-backtest-evidence-selection",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_EVIDENCE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_EVIDENCE)
cells.append(md("# Backtest\n\n- Shared harness (anchor), then the evidence-track additions, then the placebo frontier.\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells += integrity_and_audit_cells()

cells.append(md("# Placebo frontier\n\nRebuilt fresh in this notebook (own snapshot), not imported from NB15.\n"))
cells.append(code('''anchor_cycle_returns, _ = cycle_returns(anchor_equity)
frontier, cyc_returns_by_label = build_placebo_frontier(anchor_cycle_returns)
display(frontier[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer"]])
'''))

cells.append(md("""# NB14's gate result

Carried over from [14-research-evidence-screen.ipynb](14-research-evidence-screen.ipynb)'s output,
not re-derived here (that screen is descriptive and NB16 does not repeat it).
"""))
cells.append(code('''GATE_PASSED = {"sortino_shrunk": True, "evidence_composite_0.6": False, "evidence_composite_0.3": False}
print(f"GATE_PASSED = {GATE_PASSED}")
'''))

cells.append(md("""# Runs

`runs` collects every `(label, state, equity, returns, panel)` tuple; every table and chart below
is built only from it, never from a fresh `run_variant()` call with the same label.
"""))
cells.append(code('''runs = [("anchor", anchor_state, anchor_equity, anchor_returns, anchor_panel)]
run_score = {}          # label -> score name, for the verdict table
run_diagnostic = {}     # label -> bool
run_by_label = {"anchor": ("anchor", anchor_state, anchor_equity, anchor_returns, anchor_panel)}

def run_and_record(label, score_name, diagnostic_only, **overrides):
    s, e, r = run_variant(label, **overrides)
    p = panel(label, s, e, r, anchor_cycle_returns)
    entry = (label, s, e, r, p)
    runs.append(entry)
    run_by_label[label] = entry
    run_score[label] = score_name
    run_diagnostic[label] = diagnostic_only
    return s, e, r, p


SCORES = {
    "sortino_shrunk": dict(selection_score_indicator="sortino_shrunk_score"),
    "evidence_composite_06": dict(selection_score_indicator="evidence_composite", cagr_weight=0.6),
    "evidence_composite_03": dict(selection_score_indicator="evidence_composite", cagr_weight=0.3),
}
GATE_KEY = {"sortino_shrunk": "sortino_shrunk", "evidence_composite_06": "evidence_composite_0.6",
            "evidence_composite_03": "evidence_composite_0.3"}

centre_states = {}   # score_name -> state, for leave-one-vault-out
for score_name, score_overrides in SCORES.items():
    diagnostic = not GATE_PASSED.get(GATE_KEY[score_name], False)
    common = dict(require_scored_candidates=True, inverse_vol_min_periods=45, **score_overrides)
    prefix = score_name

    s, e, r, p = run_and_record(f"{prefix}__centre", score_name, diagnostic, **common)
    centre_states[score_name] = s

    neighbours = [
        ("t_cap_2", dict(evidence_t_cap=2.0)),
        ("t_cap_4", dict(evidence_t_cap=4.0)),
        ("prior_30", dict(evidence_prior_strength=30)),
        ("prior_90", dict(evidence_prior_strength=90)),
        ("min_events_10", dict(evidence_min_events=10)),
        ("min_events_30", dict(evidence_min_events=30)),
    ]
    if "cagr_weight" in score_overrides:
        alt_weight = 0.3 if score_overrides["cagr_weight"] == 0.6 else 0.6
        neighbours.append(("cagr_weight_alt", dict(cagr_weight=alt_weight)))
    for label, override in neighbours:
        run_and_record(f"{prefix}__{label}", score_name, diagnostic, **{**common, **override})

    # NB13 section 6's naive control, reproduced with this notebook's own indicators: shrinkage
    # effectively removed (prior_strength=1 means n_eff/(n_eff+1) is close to 1 for any real
    # sample), so the value the shrinkage step adds is visible directly.
    run_and_record(f"{prefix}__no_shrink", score_name, diagnostic, **{**common, "evidence_prior_strength": 1})

    # Sizing barrier isolated: centre point with the early-vol fallback OFF.
    run_and_record(f"{prefix}__no_early_vol", score_name, diagnostic, **{**common, "inverse_vol_min_periods": 90})

print(f"{len(runs) - 1} variant runs completed across {len(SCORES)} scores.")
'''))

cells.append(md("""# Verdict table
"""))
cells.append(code('''vt = verdict_table([p for _l, _s, _e, _r, p in runs], anchor_panel, frontier)
vt["score"] = [run_score.get(l, "-") for l in vt.index]
vt["diagnostic_only"] = [run_diagnostic.get(l, False) for l in vt.index]
display(vt[["score", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta",
            "mean_invested", "placebo_ref", "cagr_sacrifice_pp", "late_cagr", "passes_v2",
            "diagnostic_only", "failed", "late_ok"]])
'''))

cells.append(md("""# Per-score plateau

`__centre` and its neighbours only, per score.
"""))
cells.append(code('''for score_name in SCORES:
    sub = vt[vt["score"] == score_name]
    plateau_rows = sub[~sub.index.str.endswith(("no_shrink", "no_early_vol"))]
    plateau_holds = bool(plateau_rows["passes_v2"].all())
    print(f"{score_name}: plateau holds = {plateau_holds} (diagnostic_only={run_diagnostic.get(f'{score_name}__centre')})")
    display(plateau_rows[["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "passes_v2", "failed"]])
'''))

cells.append(md("""# Hidden-cohort reach: anchor against every centre point
"""))
cells.append(code('''reach_rows = {"anchor": hidden_cohort_reach(anchor_state)}
for score_name, state_ in centre_states.items():
    reach_rows[f"{score_name}__centre"] = hidden_cohort_reach(state_)
display(pd.DataFrame(reach_rows).T)
'''))

cells.append(code('''age_rows = []
for label, state_ in [("anchor", anchor_state)] + [(f"{n}__centre", s) for n, s in centre_states.items()]:
    from pathlib import Path as _Path
    life = pd.read_parquet(_Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet"))
    for position in state_.portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        address = str(position.pair.pool_address).lower()
        if address not in life.index:
            continue
        age = (pd.Timestamp(position.opened_at) - life.loc[address, "inception"]).days
        age_rows.append({"run": label, "age_at_entry": age})
age_df = pd.DataFrame(age_rows)
fig = px.histogram(age_df, x="age_at_entry", color="run", barmode="overlay", nbins=40,
                    title="Age at entry: anchor against every score's centre point")
fig.add_vline(x=360, line_dash="dash", annotation_text="incumbent 360d cutoff")
fig.show()
'''))

cells.append(md("""# Leave-one-vault-out and bootstrap, for every non-diagnostic centre that passes v2 and whose plateau holds
"""))
cells.append(code('''lovo_rows = []
for score_name in SCORES:
    centre_label = f"{score_name}__centre"
    if run_diagnostic.get(centre_label, True):
        print(f"{score_name}: skipped (diagnostic_only)")
        continue
    if not bool(vt.loc[centre_label, "passes_v2"]):
        print(f"{score_name}: skipped (centre fails v2: {vt.loc[centre_label, 'failed']})")
        continue
    sub = vt[(vt["score"] == score_name) & ~vt.index.str.endswith(("no_shrink", "no_early_vol"))]
    if not bool(sub["passes_v2"].all()):
        print(f"{score_name}: skipped (plateau does not hold)")
        continue
    common = dict(require_scored_candidates=True, inverse_vol_min_periods=45, **SCORES[score_name])
    top_vault = largest_contributing_vault(centre_states[score_name])
    s, e, r, p = run_and_record(f"{score_name}__without_top_vault", score_name, False, masked={top_vault}, **common)
    lovo_ok = bool(passes_constraints_v2(p, anchor_panel, frontier))
    print(f"{score_name}: leave-one-vault-out (excluding {top_vault}) passes v2 = {lovo_ok}")
    lovo_rows.append(p)

    nearest = nearest_placebo_label(frontier, float(vt.loc[centre_label, "cycle_vol"]))
    candidate_r, periods_per_year = cycle_returns(run_by_label[centre_label][2])
    lo, hi = bootstrap_sharpe_diff_vs_control(candidate_r, cyc_returns_by_label[nearest], periods_per_year)
    print(f"{score_name}: Sharpe advantage over nearest placebo ({nearest}), 95% CI: [{lo:.3f}, {hi:.3f}]")

if lovo_rows:
    display(pd.DataFrame(lovo_rows).set_index("label"))
'''))

cells.append(md("""# Frontier overlay
"""))
cells.append(code('''import plotly.express as px_
fig = px_.scatter(
    vt.reset_index(), x="cycle_vol", y="cycle_sharpe", color="score", symbol="diagnostic_only",
    hover_name="label", title="Every NB16 run against the placebo frontier",
)
fig.add_trace(px_.line(frontier.sort_values("cycle_vol"), x="cycle_vol", y="cycle_sharpe").data[0])
fig.show()
'''))

cells.append(md("""# What to carry forward

`NB16_SELECTION_OVERRIDES`: the winning `__centre` run's selection overrides if any score reached
ADOPT (gate passed, centre and every plateau neighbour pass v2, leave-one-vault-out passes v2,
`late_ok` True); otherwise the empty dict (anchor selection). Printed literally so NB17 and NB19
can copy it verbatim.
"""))
cells.append(code('''NB16_SELECTION_OVERRIDES = {}
NB16_WINNER = None
for score_name in SCORES:
    centre_label = f"{score_name}__centre"
    without_label = f"{score_name}__without_top_vault"
    if run_diagnostic.get(centre_label, True):
        continue
    if not bool(vt.loc[centre_label, "passes_v2"]):
        continue
    sub = vt[(vt["score"] == score_name) & ~vt.index.str.endswith(("no_shrink", "no_early_vol"))]
    if not bool(sub["passes_v2"].all()):
        continue
    if without_label not in vt.index or not bool(passes_constraints_v2(vt.loc[without_label], anchor_panel, frontier)):
        continue
    if not bool(vt.loc[centre_label, "late_ok"]):
        continue
    NB16_WINNER = score_name
    NB16_SELECTION_OVERRIDES = dict(require_scored_candidates=True, inverse_vol_min_periods=45, **SCORES[score_name])
    break

print(f"NB16_WINNER = {NB16_WINNER!r}")
print(f"NB16_SELECTION_OVERRIDES = {NB16_SELECTION_OVERRIDES!r}")
if NB16_WINNER is None:
    print("No score reached ADOPT. NB17 and NB19 use the anchor's incumbent selection.")
'''))

write_notebook(cells, TRACK_DIR / "16-backtest-evidence-selection.ipynb")
