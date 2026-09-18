import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_floor import INDICATOR_ADDITIONS_FLOOR
from blocks_rules_fixes import INDICATOR_ADDITIONS_RULES_FIXES
from blocks_threshold import INDICATOR_ADDITIONS_THRESHOLD
from blocks_sleeve import PARAM_ADDITIONS_SLEEVE, INDICATOR_ADDITIONS_SLEEVE, CELL14_REPLACEMENTS_SLEEVE

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()
HARNESS_RULES_V2 = (BUILD_DIR / "harness_rules_v2.py").read_text()
HARNESS_RULES_V3 = (BUILD_DIR / "harness_rules_v3.py").read_text()
HARNESS_RULES_V3_GATES = (BUILD_DIR / "harness_rules_v3_gates.py").read_text()
HARNESS_THRESHOLD = (BUILD_DIR / "harness_threshold.py").read_text()
HARNESS_FORENSICS = (BUILD_DIR / "harness_forensics.py").read_text()

HEADING = """# NB40 - lead forensics and the cash-sleeve rescue

Every portfolio-level lead with a cycle Sharpe above 1.5 on the track window was REJECTED or
left NOT CONFIRMED by a numerical gate in NB36 and NB37. This notebook reads those rejections
off the trades instead of the numbers: the equity curve, the positions that made and lost the
money, the drawdowns and the worst cycles, the vault behind each single-vault mask, the vaults
that sit in the band between two thresholds when a plateau fails, and whether the crash filter's
exits actually avoided losses. Some positive luck is allowed; the question asked of each lead is
whether it traded too riskily and whether it did what it was built to do.

It then checks whether the N and threshold assumptions the leads were scored under were sensible
(the position family with the 33% cap kept, a finer threshold family around 1.5), and tries one
rescue: a QUALITY FLOOR with a CASH SLEEVE. A candidate is allocated capital only if its trailing
180-day event-time Sharpe - the score NB39 found to be the strongest predictor of forward 60-day
Sharpe on the full archive - clears a floor; slots no qualifying vault fills stay in cash. The
floor family 1.0 / 1.5 / 2.0 / 2.5 / 3.0 is pre-stated here from NB39's candidate distribution
(median 31, 11 and 3 vaults per decision clear 1.0, 2.0 and 3.0), before any run.

**Verdicts use the standing gates only** (RESEARCH-RULES.md, idiot-gate audit of 2026-09-16):
1 positive return, 2 single-vault mask, 3 held-book volatility, 6 plateau, 7 sub-period sign.
Nothing here is out of sample; a rescued lead is a candidate for a pre-registered plan, not a
result. If a lead looks sound on its trades and can be rescued, the question of whether the gate
that rejected it was itself wrong is for that plan, not this notebook.

**Based on:** [37-backtest-threshold-crash-filter.ipynb](37-backtest-threshold-crash-filter.ipynb)
and [36-backtest-calm-closeout.ipynb](36-backtest-calm-closeout.ipynb) for the leads and the gate
machinery, [39-research-trimmed-screen-full-history.ipynb](39-research-trimmed-screen-full-history.ipynb)
for the quality score, [02-better-format.ipynb](02-better-format.ipynb) as the anchor. Track
window 2026-01-01 to 2026-09-08; windows A and B as in NB33.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "40-backtest-lead-forensics-cash-sleeve",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_SLEEVE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_FLOOR + INDICATOR_ADDITIONS_RULES_FIXES
    + INDICATOR_ADDITIONS_THRESHOLD + INDICATOR_ADDITIONS_SLEEVE,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_SLEEVE)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))
cells.append(code(HARNESS_RULES_V2))
cells.append(code(HARNESS_RULES_V3))
cells.append(code(HARNESS_RULES_V3_GATES))
cells.append(code(HARNESS_THRESHOLD))
cells.append(code(HARNESS_FORENSICS))

cells.append(md("""## Part 0. Provenance, parity, the pre-stated families

The floor and the sleeve are off by default, so the anchor must still reproduce `BASELINE` with
both splices present: that is the parity assertion. The families below are fixed before any run.
"""))
cells.append(code('''import json
from pathlib import Path
display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
manifest_37 = json.loads(Path("_build/manifest_37.json").read_text())
manifest_36 = json.loads(Path("_build/manifest_36.json").read_text())
manifest_35 = json.loads(Path("_build/manifest_35.json").read_text())

THR_FAMILY = {"thr100": {"exit": 1.0, "enter": 0.8}, "thr125": {"exit": 1.25, "enter": 1.0}, "thr150": {"exit": 1.5, "enter": 1.2},
              "thr175": {"exit": 1.75, "enter": 1.4}, "thr200": {"exit": 2.0, "enter": 1.6}}
NOCAP = {"max_concentration_pct": 1.0}
FLOORS = (1.0, 1.5, 2.0, 2.5, 3.0)          # six-name books
FLOORS_SHORT = (1.0, 2.0, 3.0)              # the N = 4 and unlimited books
N_SLOTS = 6


def filter_overrides(thr, **extra) -> dict:
    return {"crash_vol_threshold_exit": float(thr["exit"]), "crash_vol_threshold_enter": float(thr["enter"]), **extra}


def floor_overrides(floor: float, slots: int, **extra) -> dict:
    return {"quality_floor_on": True, "quality_floor_sharpe": float(floor), "cash_sleeve_slots": int(slots), **extra}


def ftag(floor: float) -> str:
    return f"f{int(round(floor * 10)):02d}"


# The leads: every NB37 / NB36 run with cycle Sharpe > 1.5 that is not the anchor's twin, with the
# overrides NB37 recorded for it. `thr250` is the anchor path (nothing above 2.5) and is omitted.
LEADS = {
    "measured_8": ("count exclusion", prefilter_overrides("inverse_vol", count=8)),
    "thr100": ("threshold", filter_overrides(THR_FAMILY["thr100"])),
    "thr150": ("threshold", filter_overrides(THR_FAMILY["thr150"])),
    "thr200": ("threshold", filter_overrides(THR_FAMILY["thr200"])),
    "nocap": ("cap", dict(NOCAP)),
    "nofilter_n3": ("positions", {"max_assets_in_portfolio": 3, **NOCAP}),
    "nofilter_n4": ("positions", {"max_assets_in_portfolio": 4, **NOCAP}),
    "thr100_n4": ("positions", filter_overrides(THR_FAMILY["thr100"], max_assets_in_portfolio=4, **NOCAP)),
    "thr150_n4": ("positions", filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=4, **NOCAP)),
    "thr150_cagr_sharpe__inverse_variance": ("ranker", filter_overrides(THR_FAMILY["thr150"], selection_score_indicator="cagr_sharpe_weight", weighting_method="inverse_variance")),
    "thr150_nall_invvar": ("unlimited", filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=999, **NOCAP)),
}
display(pd.Series({"leads": len(LEADS), "threshold family": ", ".join(f"{k} (exit {v['exit']}, enter {v['enter']})" for k, v in THR_FAMILY.items()),
                   "floors, six names": FLOORS, "floors, N = 4 and unlimited": FLOORS_SHORT, "sleeve slots": N_SLOTS,
                   "quality score": "quality_sharpe: 180-row event-time Sharpe, >= 9 moved marks, last within 14 rows, window spanned",
                   "indifference band": INDIFFERENCE_BAND}, name="value").to_frame())
'''))

cells.append(md("""## Part 1. The leads, reproduced

Each lead is re-run here so its state is available for forensics. Same engine, same snapshot:
the five panel metrics must reproduce NB37 (and NB36 for `measured_8`) at 1e-6.
"""))
cells.append(code('''for label, (family, overrides) in LEADS.items():
    run_and_record(label, family, **overrides)

REFERENCE = {label: manifest_37["summary"][label] for label in LEADS if label in manifest_37["summary"]}
REFERENCE["measured_8"] = next(r for r in manifest_36["verdict_rows"] if r["label"] == "measured_8")
REPRO_METRICS = ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd")
repro = []
for label in LEADS:
    for metric in REPRO_METRICS:
        here, there = float(run_by_label[label]["panel"][metric]), float(REFERENCE[label][metric])
        repro.append({"label": label, "metric": metric, "here": here, "reference": there, "abs_diff": abs(here - there)})
repro = pd.DataFrame(repro)
worst = repro["abs_diff"].max()
assert worst < 1e-6, f"a lead does not reproduce its NB37/NB36 run: max abs diff {worst}"
print(f"{len(LEADS)} leads reproduce NB37/NB36 on {len(REPRO_METRICS)} metrics; max abs diff {worst:.2e}")

SUMMARY_COLUMNS = ["family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested", "luck_ratio",
                   "top5_gross_share", "sparse_cagr", "dense_cagr", "late_cagr", "final_equity", "mean_holdings",
                   "mean_largest_weight", "distinct_vaults", "top_vault_pnl_share", "turnover_per_decision", "trades",
                   "share_of_decisions_changed", "crash_survivors_mean", "crash_excluded_held_total",
                   "qualifying_mean", "qualifying_min", "decisions_none_qualifying", "quality_held_removed_total",
                   "sleeve_active_share", "sleeve_mean_fill"]


def summary_table(labels):
    return pd.DataFrame([summary_row_40(l) for l in labels]).set_index("label")[SUMMARY_COLUMNS]


pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", None)
LEAD_LABELS = ["anchor"] + list(LEADS)
display(summary_table(LEAD_LABELS).round(4))
NB37_VERDICTS = {l: manifest_37["gates"].get(l, {}).get("verdict") for l in LEADS}
NB37_VERDICTS["measured_8"] = "NOT CONFIRMED (conditionally positive) - RESEARCH-RULES.md audit"
NB37_FAILED = {l: manifest_37["gates"].get(l, {}).get("failed_standing_gates") for l in LEADS}
display(pd.DataFrame({"verdict as recorded": NB37_VERDICTS, "failed standing gates": NB37_FAILED}))
'''))

cells.append(md("""## Part 2. Forensics

### 2a. Equity curves

Three groups: the six-name filters, the position family, and the ranker / unlimited / uncapped
books. Normalised to 1.0 at the start.
"""))
cells.append(code('''import plotly.graph_objects as go
GROUPS = {"six-name filters": ["anchor", "measured_8", "thr100", "thr150", "thr200"],
          "position family (cap removed)": ["anchor", "nofilter_n3", "nofilter_n4", "thr100_n4", "thr150_n4"],
          "ranker, unlimited, uncapped": ["anchor", "thr150_cagr_sharpe__inverse_variance", "thr150_nall_invvar", "nocap"]}


def equity_figure(title, labels):
    fig = go.Figure()
    for label in labels:
        eq = run_by_label[label]["equity"]
        fig.add_trace(go.Scatter(x=eq.index, y=eq / eq.iloc[0], mode="lines", name=label))
    fig.update_layout(title=title, height=440, template="plotly_white", yaxis_title="equity / initial")
    return fig


for title, labels in GROUPS.items():
    equity_figure(f"Track window equity, {title}", labels).show()
'''))

cells.append(md("""### 2b. Risk panel

What the operator is worried about, per lead: drawdown depth, ulcer, the worst cycles, time
under water, held-book own volatility (post-break, gate 3's statistic), concentration, luck.
"""))
cells.append(code('''risk = pd.DataFrame([risk_row(l) for l in LEAD_LABELS]).set_index("label")
display(risk.round(4))
'''))

cells.append(md("""### 2c. Positions

Ledger summary for every lead, then the eight largest positions by absolute P&L for the leads a
gate rejected. `pnl_share` is the position's share of the run's NET P&L.
"""))
cells.append(code('''ledgers = pd.DataFrame([ledger_summary(l) for l in LEAD_LABELS]).set_index("label")
display(ledgers.round(4))
LEDGER_DETAIL = ["anchor", "thr150", "thr100", "thr150_n4", "nofilter_n4", "thr150_cagr_sharpe__inverse_variance", "thr150_nall_invvar"]
for label in LEDGER_DETAIL:
    print(f"\\n{label}: largest positions")
    display(position_ledger(label).head(8).round(4))
'''))

cells.append(md("""### 2d. Drawdowns and worst cycles

The three deepest drawdowns per lead, the positions that lost the money inside the deepest one,
and the five worst cycles with the vault that fell most in each.
"""))
cells.append(code('''DRAWDOWN_DETAIL = ["anchor", "thr150", "thr150_n4", "nofilter_n4", "nofilter_n3", "thr150_cagr_sharpe__inverse_variance", "thr150_nall_invvar"]
episode_rows = []
for label in DRAWDOWN_DETAIL:
    episodes = drawdown_episodes(label, top=3)
    for i, row in episodes.iterrows():
        episode_rows.append({"label": label, "rank": i + 1, **row.to_dict()})
episodes_table = pd.DataFrame(episode_rows).set_index(["label", "rank"])
display(episodes_table.round(4))
for label in DRAWDOWN_DETAIL:
    deepest = drawdown_episodes(label, top=1).iloc[0]
    print(f"\\n{label}: deepest drawdown {deepest['depth']:.2%} from {deepest['peak']} to {deepest['trough']} - positions that lost most")
    display(episode_attribution(label, deepest["peak"], deepest["trough"], top=5).round(2))
for label in ["thr150_n4", "nofilter_n4", "thr150_nall_invvar"]:
    print(f"\\n{label}: worst cycles")
    display(worst_cycles(label, n=5).round(4))
'''))

cells.append(md("""### 2e. Gate 2 - the single-vault mask, read as a vault

First the anchor under its own mask, which the 0.70 bar was set above. Then, for the leads whose
mask retention sat near or below the bar, and the three that passed: the masked vault, its share
of the lead's positive P&L, the same vault's share of the ANCHOR's positive P&L (an inherited
dependence is not the lead's doing), and the recorded retention. Then one new run per marginal
lead: mask the SECOND largest contributor instead, to see whether the dependence is one name or a
thin book.
"""))
cells.append(code('''def vault_pnl_shares(label: str) -> pd.Series:
    ledger = position_ledger(label)
    by_vault = ledger.groupby("address")["pnl_usd"].sum()
    positive = by_vault[by_vault > 0].sum()
    return (by_vault / positive).sort_values(ascending=False) if positive > 0 else by_vault * np.nan


MASK_LEADS = ["thr150_cagr_sharpe__inverse_variance", "thr100", "thr150", "measured_8", "thr200"]
anchor_shares = vault_pnl_shares("anchor")
# The anchor under its own mask, for reference: the bar (0.70) is judged against this.
anchor_lovo = lovo_gate("anchor", verbose=True)
mask_rows = []
for label in MASK_LEADS:
    shares = vault_pnl_shares(label)
    masked = largest_contributing_vault(run_by_label[label]["state"])
    recorded = manifest_37["gates"].get(label, {}).get("mask_retention")
    if label == "measured_8":
        recorded = next(r["retention"] for r in manifest_35["diag_lovo"] if r["label"] == "measured_8")
    mask_rows.append({"label": label, "masked_vault": short(masked), "lead_share_of_positive_pnl": float(shares.get(masked, np.nan)),
                      "anchor_share_of_positive_pnl": float(anchor_shares.get(masked, np.nan)),
                      "anchor_rank_of_this_vault": int(anchor_shares.index.get_loc(masked)) + 1 if masked in anchor_shares.index else None,
                      "second_vault": short(shares.index[1]), "second_share": float(shares.iloc[1]),
                      "recorded_mask_retention": float(recorded) if recorded is not None else np.nan})
mask_table = pd.DataFrame(mask_rows).set_index("label")
display(mask_table.round(4))

# Second-largest contributor masked, for the two marginal leads.
second_mask = []
for label in ["thr150_cagr_sharpe__inverse_variance", "thr100"]:
    shares = vault_pnl_shares(label)
    second = shares.index[1]
    entry = run_by_label[label]
    lovo2 = run_and_record(f"{label}__lovo2", "robustness", masked={second}, **entry["overrides"])
    second_mask.append({"label": label, "masked_second": short(second), "sharpe": float(entry["panel"]["cycle_sharpe"]),
                        "sharpe_masked_second": float(lovo2["panel"]["cycle_sharpe"]),
                        "retention_second": float(lovo2["panel"]["cycle_sharpe"]) / float(entry["panel"]["cycle_sharpe"]),
                        "cagr_masked_second": float(lovo2["panel"]["cagr"])})
display(pd.DataFrame(second_mask).set_index("label").round(4))
'''))

cells.append(md("""### 2f. Gate 6 - the threshold cliff, read as a list of vaults

`thr150` fails the plateau because `thr100` sits 0.33 below it. The vaults in the band are the
names `thr150` held on dates when `thr100`'s filter excluded them. Two attributions: the whole-
window P&L of those names (an association), and the P&L earned only on the cycles in which the
tight run's filter excluded a name the wide run was holding (the disputed dates). Then, for every threshold run: each
time the filter removed a HELD name, the vault's own forward 30-day log return afterwards. A
filter that is doing its job removes names that go on to lose; one that is not forgoes gains.
"""))
cells.append(code('''bands = pd.DataFrame([band_attribution("thr150", "thr100"), band_attribution("thr200", "thr150"), band_attribution("thr150_n4", "thr100_n4")])
print("whole-window P&L of the band addresses (an association: every position of those names, on every date)")
display(bands.drop(columns=["band_addresses"]).set_index(["wide", "tight"]).round(4))
print("band vaults thr150 vs thr100:", ", ".join(short(a) for a in bands.iloc[0]["band_addresses"]))
print("\\nP&L earned ONLY on the cycles in which the tight run's filter excluded a name the wide run (or the anchor) held")
bands_aligned = pd.DataFrame([band_attribution_aligned("thr150", "thr100"), band_attribution_aligned("thr200", "thr150"), band_attribution_aligned("thr150_n4", "thr100_n4")])
display(bands_aligned.set_index(["wide", "tight"]).round(4))
ENGINE = "0x77fee2df7bad4f1db93052fa82bf78eaab771a16"
engine_positions = {l: positions_in_address(l, ENGINE) for l in LEAD_LABELS}
print("\\nevery position in the engine vault, per lead")
display(pd.DataFrame([{"label": l, "positions": len(v), "spans": "; ".join(f"{r['opened']}..{r['closed'] or 'open'} ({r['pnl_usd']:.0f})" for r in v)} for l, v in engine_positions.items()]).set_index("label"))

exclusion_summary = pd.DataFrame([exclusion_outcome_summary(l) for l in ["thr100", "thr150", "thr200", "thr150_n4", "thr100_n4", "thr150_nall_invvar"]]).set_index("label")
display(exclusion_summary.round(4))
for label in ["thr150", "thr150_nall_invvar"]:
    print(f"\\n{label}: every held-name exclusion ({len(held_exclusion_outcomes(label))} rows)")
    display(held_exclusion_outcomes(label).drop(columns=["address"]).round(4))
'''))

cells.append(md("""### 2g. Gate 7 and gate 3 - the unlimited book and the four-name book

The unlimited inverse-variance book earned 9% and turned negative in the late period. The sizing
rule's known bias is towards names whose marks rarely move; the capital-weighted count of moved
marks in the trailing 90 rows, and the share of capital in names with fewer than 30, make that
visible against the anchor. Then the late-period P&L by vault. For the four-name books: how much
of their capital sat in names the anchor also held, so gate 3's higher held-book volatility can
be read as "the same names, bigger" or "different names".
"""))
cells.append(code('''sparse = pd.DataFrame([sparse_capital_share(l) for l in ["anchor", "thr150", "thr150_nall_invvar", "thr150_n4", "nofilter_n4"]]).set_index("label")
display(sparse.round(4))
for label in ["thr150_nall_invvar", "anchor"]:
    print(f"\\n{label}: late-period (from {LATE_START.date()}) P&L by vault, largest losers and winners")
    display(regime_pnl_by_vault(label, LATE_START, LATE_END, top=5).round(2))
overlap = pd.DataFrame([book_overlap(l) for l in ["thr150", "measured_8", "nofilter_n4", "thr150_n4", "nofilter_n3", "thr150_nall_invvar"]]).set_index("label")
display(overlap.round(4))
'''))

cells.append(md("""### 2h. Were the thresholds and the floor sensibly placed?

From `thr150`'s crash log, every candidate's trailing volatility at every decision: the share of
candidates and the share of the ANCHOR's capital in each volatility band. The threshold family's
step from 1.0 to 1.5 is sensible only if a material share of the anchor's book sits in that band
- otherwise the two runs could not differ by what they did. Then the quality score's population:
how many candidates clear each floor per decision, read offline from the cached indicator at T-1
over the same candidate sets, so the floor family can be checked against the book it will be
applied to before the rescue runs.
"""))
cells.append(code('''BANDS = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.25), (1.25, 1.5), (1.5, 2.0), (2.0, 99.0)]
crash_log_150 = run_by_label["thr150"]["crash_log"]
anchor_held = held_addresses_by_date(run_by_label["anchor"])
band_rows = []
for t, rec in sorted(crash_log_150.items()):
    vols = {a: v for a, v in rec["vol"].items() if np.isfinite(v)}
    held = anchor_held.get(pd.Timestamp(t), {})
    held_total = sum(held.values())
    row = {"decision": pd.Timestamp(t), "candidates": rec["pool_size"], "measured": len(vols)}
    for lo, hi in BANDS:
        in_band = {a for a, v in vols.items() if lo <= v < hi}
        row[f"cand_{lo}-{hi}"] = len(in_band) / max(len(vols), 1)
        row[f"anchor_cap_{lo}-{hi}"] = sum(w for a, w in held.items() if a in in_band) / held_total if held_total > 0 else np.nan
    row["anchor_cap_unmeasured"] = sum(w for a, w in held.items() if a not in vols) / held_total if held_total > 0 else np.nan
    band_rows.append(row)
band_frame = pd.DataFrame(band_rows).set_index("decision")
band_summary = pd.DataFrame({"mean over decisions": band_frame.drop(columns=["candidates", "measured"]).mean(),
                             "post-break mean": band_frame.loc[band_frame.index >= POST_BREAK_START].drop(columns=["candidates", "measured"]).mean()})
display(band_summary.round(4))

# Quality score population, offline at T-1. Two populations, because the floor runs after the
# crash filter: the whole candidate pool (what the anchor floor family sees; the crash log's
# `candidate_addresses` is written BEFORE the filter) and thr150's survivors (what the thr150
# floor family sees; `candidate_addresses` minus `excluded_addresses`).
floor_rows = []
for t, rec in sorted(crash_log_150.items()):
    q = {}
    for addr in rec["candidate_addresses"]:
        pair = PAIR_BY_ADDRESS.get(addr)
        q[addr] = value_at_prior(indicator_series("quality_sharpe", pair), t) if pair is not None else np.nan
    survivors = set(rec["candidate_addresses"]) - set(rec["excluded_addresses"])
    finite = {a: v for a, v in q.items() if np.isfinite(v)}
    finite_surv = {a: v for a, v in finite.items() if a in survivors}
    held = anchor_held.get(pd.Timestamp(t), {})
    row = {"decision": pd.Timestamp(t), "candidates": len(q), "measured": len(finite),
           "thr150_survivors": len(survivors), "thr150_survivors_measured": len(finite_surv),
           "anchor_held_measured": sum(1 for a in held if np.isfinite(q.get(a, np.nan))), "anchor_held": len(held),
           "anchor_held_median_quality": float(np.median([q[a] for a in held if np.isfinite(q.get(a, np.nan))])) if any(np.isfinite(q.get(a, np.nan)) for a in held) else np.nan}
    for f in FLOORS:
        row[f"clear_{ftag(f)}"] = sum(1 for v in finite.values() if v >= f)
        row[f"thr150_survivors_clear_{ftag(f)}"] = sum(1 for v in finite_surv.values() if v >= f)
        row[f"anchor_held_clear_{ftag(f)}"] = sum(1 for a in held if np.isfinite(q.get(a, np.nan)) and q[a] >= f)
    floor_rows.append(row)
floor_frame = pd.DataFrame(floor_rows).set_index("decision")
floor_summary = pd.DataFrame({"min": floor_frame.min(), "p10": floor_frame.quantile(0.1), "median": floor_frame.median(), "mean": floor_frame.mean()})
display(floor_summary.round(3))
print(f"decisions: {len(floor_frame)}; quality measured on a mean {floor_frame['measured'].mean():.1f} of {floor_frame['candidates'].mean():.1f} candidates; "
      f"anchor held names measured {floor_frame['anchor_held_measured'].sum()} of {floor_frame['anchor_held'].sum()} holding-decisions")
print("\\nanchor: largest positions with the vault's quality score at the opening decision")
display(ledger_with_quality("anchor", top=8).round(4))
'''))

cells.append(md("""## Part 3. Were N and the thresholds sensible? New runs

NB37 scored the position family with the cap REMOVED, so its N = 3 neighbour was a 99%-invested
three-name book and the N = 4 plateau was judged against it. Here the family is re-run with the
33% cap kept (N = 3, 4, 5, with and without the 1.5 filter), plus N = 3 and 5 uncapped with the
filter and the uncapped six-name filtered book as the missing neighbours, the unlimited filtered
book with the cap KEPT as the comparator for Part 4's unlimited floor family, and the threshold
family is refined to 1.25 and 1.75 around 1.5. These are checks on
the assumptions the verdicts rested on; a plateau that appears under a finer or a capped family
is reported as such, not as a new verdict on the old runs.
"""))
cells.append(code('''for label in ("thr125", "thr175"):
    run_and_record(label, "threshold", **filter_overrides(THR_FAMILY[label]))
for n in (3, 4, 5):
    run_and_record(f"n{n}cap", "positions_cap", max_assets_in_portfolio=n)
    run_and_record(f"thr150_n{n}cap", "positions_cap", **filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=n))
run_and_record("nofilter_n5", "positions", max_assets_in_portfolio=5, **NOCAP)
run_and_record("thr150_n5", "positions", **filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=5, **NOCAP))
run_and_record("thr150_n3", "positions", **filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=3, **NOCAP))
run_and_record("thr150_nocap", "cap", **filter_overrides(THR_FAMILY["thr150"], **NOCAP))
# The un-floored comparator of the unlimited floor family: unlimited AND the cap kept.
run_and_record("thr150_nallcap", "unlimited", **filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=999))
PART3 = ["anchor", "thr100", "thr125", "thr150", "thr175", "thr200",
         "nofilter_n3", "nofilter_n4", "nofilter_n5", "nocap", "n3cap", "n4cap", "n5cap",
         "thr150_n3", "thr150_n4", "thr150_n5", "thr150_nocap", "thr150_n3cap", "thr150_n4cap", "thr150_n5cap",
         "thr150_nall_invvar", "thr150_nallcap"]
display(summary_table(PART3).round(4))
'''))

cells.append(md("""## Part 4. The rescue: quality floor with a cash sleeve

Four books, each with the floor family: the incumbent (six slots), `thr150` (six slots), the
four-name `thr150` book with the cap kept (four slots), and the unlimited `thr150` book with the
cap kept (no slots: with no fixed N the cap itself is the sleeve, so at most three names can fill
the book). The quality/sleeve columns say what the mechanism did: how many names qualified per
decision, how often nothing did, how often the sleeve held cash and how much.
"""))
cells.append(code('''for f in FLOORS:
    run_and_record(f"anchor_{ftag(f)}", "floor_anchor", **floor_overrides(f, N_SLOTS))
    run_and_record(f"thr150_{ftag(f)}", "floor_thr150", **floor_overrides(f, N_SLOTS, **filter_overrides(THR_FAMILY["thr150"])))
for f in FLOORS_SHORT:
    run_and_record(f"thr150_n4cap_{ftag(f)}", "floor_n4", **floor_overrides(f, 4, **filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=4)))
    run_and_record(f"thr150_nallcap_{ftag(f)}", "floor_unlimited", **floor_overrides(f, 0, **filter_overrides(THR_FAMILY["thr150"], max_assets_in_portfolio=999)))
RESCUE = [f"anchor_{ftag(f)}" for f in FLOORS] + [f"thr150_{ftag(f)}" for f in FLOORS] \\
         + [f"thr150_n4cap_{ftag(f)}" for f in FLOORS_SHORT] + [f"thr150_nallcap_{ftag(f)}" for f in FLOORS_SHORT]
display(summary_table(["anchor", "thr150", "thr150_n4cap", "thr150_nallcap"] + RESCUE).round(4))
rescue_risk = pd.DataFrame([risk_row(l) for l in ["anchor", "thr150", "thr150_n4cap", "thr150_nallcap"] + RESCUE]).set_index("label")
display(rescue_risk.round(4))
# Independent of the sleeve's own log: realised deployment and the largest realised weight.
sleeve_check = pd.DataFrame([sleeve_realised_check(l) for l in RESCUE]).set_index("label")
display(sleeve_check.round(4))
# The floor runs' logged qualifying counts against an offline reconstruction from the cached
# indicator at T-1. The anchor family's population is the whole pool (cell 44's `clear_*`); a
# thr150 floor run's population is ITS OWN crash log's survivors - the filter's hysteresis reads
# the held set, so a floor run's survivors can differ from thr150's on a few dates.
agreement = []
for f in FLOORS:
    log = run_by_label[f"anchor_{ftag(f)}"]["quality_log"]
    logged = pd.Series({pd.Timestamp(t): r["qualifying"] for t, r in log.items()}).sort_index()
    offline = floor_frame[f"clear_{ftag(f)}"].reindex(logged.index)
    agreement.append({"run": f"anchor_{ftag(f)}", "decisions": len(logged), "mismatches": int((logged != offline).sum()),
                      "max_abs_diff": float((logged - offline).abs().max())})
for f in FLOORS:
    entry = run_by_label[f"thr150_{ftag(f)}"]
    logged = pd.Series({pd.Timestamp(t): r["qualifying"] for t, r in entry["quality_log"].items()}).sort_index()
    offline = {}
    for t, rec in entry["crash_log"].items():
        survivors = set(rec["candidate_addresses"]) - set(rec["excluded_addresses"])
        count = 0
        for addr in survivors:
            pair = PAIR_BY_ADDRESS.get(addr)
            v = value_at_prior(indicator_series("quality_sharpe", pair), t) if pair is not None else np.nan
            count += int(np.isfinite(v) and v >= f)
        offline[pd.Timestamp(t)] = count
    offline = pd.Series(offline).reindex(logged.index)
    agreement.append({"run": f"thr150_{ftag(f)}", "decisions": len(logged), "mismatches": int((logged != offline).sum()),
                      "max_abs_diff": float((logged - offline).abs().max())})
agreement = pd.DataFrame(agreement).set_index("run")
display(agreement)
assert agreement["mismatches"].sum() == 0, "the floor's in-trade qualifying counts do not match the offline reconstruction"
for label in ["anchor_f10", "thr150_nallcap_f10"]:
    print(f"\\n{label}: largest positions, with the quality score at the opening decision")
    display(ledger_with_quality(label, top=8).round(4))
for title, labels in {"floor on the incumbent": ["anchor"] + [f"anchor_{ftag(f)}" for f in FLOORS],
                      "floor on thr150": ["anchor", "thr150"] + [f"thr150_{ftag(f)}" for f in FLOORS],
                      "floor on the four-name and unlimited books": ["anchor", "thr150_n4cap", "thr150_nallcap"] + [f"thr150_n4cap_{ftag(f)}" for f in FLOORS_SHORT] + [f"thr150_nallcap_{ftag(f)}" for f in FLOORS_SHORT]}.items():
    equity_figure(f"Track window equity, {title}", labels).show()
'''))

cells.append(md("""## Part 5. Standing gates for Parts 3 and 4

Gates 1, 7, 3 and 6 for every new run; gate 2 (a full re-simulation) for the three new runs
with the largest Sharpe gap to the anchor among those passing gates 1, 7 and 3. Plateau
neighbours: the threshold family on its refined axis (1.0 / 1.25 / 1.5 / 1.75 / 2.0); the capped
position family on N +/- 1 with six = the anchor (or `thr150`); the uncapped family on N +/- 1
with six = `nocap` (or `thr150_nocap` with the filter); the floor families along the floor axis, the un-floored book as the lowest
floor's outer neighbour. Gate 6 is scored ONLY where both pre-registered neighbours exist: a
family endpoint has one, so its plateau is not run and the row is UNEVALUATED on gate 6 rather
than passed one-sided (`standing_gates_40`). Gates 4 and 8 with their tolerances are diagnostics.
"""))
cells.append(code('''NEIGHBOURS = {}
THR_ORDER = list(THR_FAMILY)
for i, label in enumerate(THR_ORDER):
    NEIGHBOURS[label] = [THR_ORDER[j] for j in (i - 1, i + 1) if 0 <= j < len(THR_ORDER)]
NEIGHBOURS["n3cap"] = ["n4cap"]; NEIGHBOURS["n4cap"] = ["n3cap", "n5cap"]; NEIGHBOURS["n5cap"] = ["n4cap", "anchor"]
NEIGHBOURS["thr150_n3cap"] = ["thr150_n4cap"]; NEIGHBOURS["thr150_n4cap"] = ["thr150_n3cap", "thr150_n5cap"]; NEIGHBOURS["thr150_n5cap"] = ["thr150_n4cap", "thr150"]
NEIGHBOURS["nofilter_n5"] = ["nofilter_n4", "nocap"]; NEIGHBOURS["nofilter_n4"] = ["nofilter_n3", "nofilter_n5"]
NEIGHBOURS["thr150_n5"] = ["thr150_n4", "thr150_nocap"]; NEIGHBOURS["thr150_n4"] = ["thr150_n3", "thr150_n5"]; NEIGHBOURS["thr150_n3"] = ["thr150_n4"]
NEIGHBOURS["thr150_nocap"] = ["thr150_n5"]


def floor_chain(prefix: str, base: str, floors):
    tags = [ftag(f) for f in floors]
    for i, tag in enumerate(tags):
        left = f"{prefix}_{tags[i - 1]}" if i > 0 else base
        right = [f"{prefix}_{tags[i + 1]}"] if i + 1 < len(tags) else []
        NEIGHBOURS[f"{prefix}_{tag}"] = [left] + right


floor_chain("anchor", "anchor", FLOORS)
floor_chain("thr150", "thr150", FLOORS)
floor_chain("thr150_n4cap", "thr150_n4cap", FLOORS_SHORT)
floor_chain("thr150_nallcap", "thr150_nallcap", FLOORS_SHORT)
NEW = [l for l in PART3 + RESCUE if l not in LEADS and l != "anchor"]
NEW = list(dict.fromkeys(NEW))
cheap = pd.DataFrame([standing_gates_40(l, NEIGHBOURS.get(l, [])) for l in NEW]).set_index("label")
CHEAP = ["gate_1_positive", "gate_7_subperiod", "gate_3_held_vol"]
cheap["cheap_pass"] = cheap[CHEAP].all(axis=1)
ranked = cheap[cheap["cheap_pass"]].sort_values("sharpe_gap_to_anchor", ascending=False)
LOVO_LABELS = list(ranked.index[:3])
print(f"leave-one-vault-out for: {LOVO_LABELS}")
gates = pd.DataFrame([standing_gates_40(l, NEIGHBOURS.get(l, []), run_lovo=(l in LOVO_LABELS)) for l in NEW]).set_index("label")
display(gates[["gate_1_positive", "gate_7_subperiod", "gate_3_held_vol", "gate_6_plateau", "plateau_neighbours", "gate_2_mask", "mask_retention",
               "diag_4_luck_within_tolerance", "diag_8_distinct_within_tolerance", "sharpe_gap_to_anchor",
               "failed_standing_gates", "standing_gates_not_run", "verdict"]].round(4))
for label in LOVO_LABELS:
    print(f"  {label}: masked {gates.loc[label, 'masked']}, retention {gates.loc[label, 'mask_retention']:.3f}")

# The old leads' plateaus re-read against the refined / capped neighbours: a check on the
# assumption, reported beside the recorded verdict, not a replacement for it.
replateau = pd.DataFrame([{"label": l, "recorded_verdict": NB37_VERDICTS.get(l), "neighbours_here": ", ".join(NEIGHBOURS[l]),
                           **{k: v for k, v in plateau_gate(l, NEIGHBOURS[l]).items() if k != "detail"}}
                          for l in ["thr150", "nofilter_n4", "thr150_n4"]]).set_index("label")
display(replateau.round(4))
'''))

cells.append(md("""## Part 6. Windows A and B

The incumbent's docstring window (2026-01-01 to 07-10) and the full data period (2025-08-01 to
09-09) for the anchor, `thr150`, and the two best new runs by track Sharpe gap among those
passing the cheap standing gates. Slim runs; the cost-basis helper is redefined with a relative
tolerance exactly as NB33, NB35 and NB37 did.
"""))
cells.append(code('''import datetime


def get_remaining_cost_basis(position) -> float:
    quantity = 0.0
    cost_basis = 0.0
    for trade in sorted(position.get_successful_trades(), key=lambda trade: trade.executed_at):
        trade_quantity = abs(float(trade.get_position_quantity()))
        if trade.is_buy():
            quantity += trade_quantity
            cost_basis += trade_quantity * float(trade.executed_price)
        elif trade.is_sell():
            assert quantity > 0, f"Cannot sell without a cost basis: {trade}"
            sold_quantity = min(trade_quantity, quantity)
            cost_basis *= (quantity - sold_quantity) / quantity
            quantity -= sold_quantity
    held = float(position.get_quantity())
    assert abs(quantity - held) <= 1e-8 * max(1.0, abs(held)), (
        f"Cost-basis quantity mismatch for {position}: {quantity} vs {position.get_quantity()}")
    return cost_basis


WINDOW_A = ("A: incumbent period", datetime.datetime(2026, 1, 1), datetime.datetime(2026, 7, 10))
WINDOW_B = ("B: full data period", datetime.datetime(2025, 8, 1), datetime.datetime(2026, 9, 9))
BEST_NEW = list(ranked.index[:2])
WINDOW_LABELS = list(dict.fromkeys(["anchor", "thr150"] + BEST_NEW))
print(f"window runs for: {WINDOW_LABELS}")
WINDOW_RESULTS = {}


def run_window(label: str, window) -> dict:
    name, start, end = window
    overrides = dict(run_by_label[label]["overrides"]) if label != "anchor" else {}
    VOL_DROP_LOG.clear(); COMPLEMENT_LOG.clear(); SLEEVE_LOG.clear(); PREFILTER_LOG.clear(); CRASH_LOG.clear(); QUALITY_LOG.clear(); CASH_SLEEVE_LOG.clear()
    state_, equity_, returns_ = run_variant(f"{label} [{name}]", backtest_start=start, backtest_end=end, **overrides)
    rc, _ppy = cycle_returns(equity_)
    row = panel(f"{label} [{name}]", state_, equity_, returns_)
    row["cumulative_return"] = float(equity_.iloc[-1] / equity_.iloc[0] - 1.0)
    row["final_equity"] = float(equity_.iloc[-1])
    row["cycles"] = int(len(rc))
    fills = [r["fill"] for r in CASH_SLEEVE_LOG.values()]
    row["sleeve_mean_fill"] = float(np.mean(fills)) if fills else float("nan")
    qual = [r["qualifying"] for r in QUALITY_LOG.values()]
    row["qualifying_mean"] = float(np.mean(qual)) if qual else float("nan")
    WINDOW_RESULTS[(label, name)] = {"label": label, "window": name, "equity": equity_, "cycle_returns": rc, "panel": row}
    return WINDOW_RESULTS[(label, name)]


for window in (WINDOW_A, WINDOW_B):
    for label in WINDOW_LABELS:
        run_window(label, window)
WINDOW_COLUMNS = ["cumulative_return", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "mean_invested",
                  "luck_ratio", "top5_gross_share", "cycles", "qualifying_mean", "sleeve_mean_fill"]
window_tables = {}
for window in (WINDOW_A, WINDOW_B):
    name = window[0]
    frame = pd.DataFrame([WINDOW_RESULTS[(l, name)]["panel"] for l in WINDOW_LABELS]).set_index("label")[WINDOW_COLUMNS]
    frame.index = WINDOW_LABELS
    window_tables[name] = frame
    print(f"\\n{name}:")
    display(frame.round(4))
'''))

cells.append(md("""## Part 7. Manifest
"""))
cells.append(code('''ALL = [e["label"] for e in runs if e["label"] != "anchor"]
all_summary = summary_table(["anchor"] + [l for l in ALL if "__lovo" not in l])
manifest = {
    "verdict": "see heading",
    "threshold_family": THR_FAMILY, "floors": list(FLOORS), "floors_short": list(FLOORS_SHORT), "slots": N_SLOTS,
    "leads": {l: {"family": f, "overrides": o} for l, (f, o) in LEADS.items()},
    "reproduction_max_abs_diff": float(worst),
    "provenance": provenance_record(),
    "summary": all_summary.round(10).to_dict(orient="index"),
    "risk": risk.round(10).to_dict(orient="index"),
    "rescue_risk": rescue_risk.round(10).to_dict(orient="index"),
    "ledgers": ledgers.round(10).to_dict(orient="index"),
    "ledger_detail": {l: position_ledger(l).head(8).round(10).to_dict(orient="records") for l in LEDGER_DETAIL},
    "drawdown_episodes": {f"{l}|{r}": {k: (str(v) if not isinstance(v, (int, float)) else v) for k, v in row.items()} for (l, r), row in episodes_table.iterrows()},
    "mask": mask_table.round(10).to_dict(orient="index"),
    "anchor_lovo": {k: v for k, v in anchor_lovo.items()},
    "anchor_quality_at_open": ledger_with_quality("anchor", top=8).round(10).to_dict(orient="records"),
    "floor_ledger_detail": {l: ledger_with_quality(l, top=8).round(10).to_dict(orient="records") for l in ("anchor_f10", "thr150_nallcap_f10")},
    "second_mask": pd.DataFrame(second_mask).set_index("label").round(10).to_dict(orient="index"),
    "bands": bands.drop(columns=["band_addresses"]).round(10).to_dict(orient="records"),
    "bands_aligned": bands_aligned.round(10).to_dict(orient="records"),
    "engine_positions": engine_positions,
    "sleeve_check": sleeve_check.round(10).to_dict(orient="index"),
    "quality_log_agreement": agreement.to_dict(orient="index"),
    "band_addresses_thr150_vs_thr100": bands.iloc[0]["band_addresses"],
    "exclusion_outcomes": exclusion_summary.round(10).to_dict(orient="index"),
    "sparse": sparse.round(10).to_dict(orient="index"),
    "overlap": overlap.round(10).to_dict(orient="index"),
    "band_summary": band_summary.round(10).to_dict(orient="index"),
    "floor_summary": floor_summary.round(10).to_dict(orient="index"),
    "gates": gates.round(10).to_dict(orient="index"),
    "replateau": replateau.round(10).to_dict(orient="index"),
    "lovo_labels": LOVO_LABELS, "best_new": BEST_NEW,
    "windows": {name: frame.round(10).to_dict(orient="index") for name, frame in window_tables.items()},
    "all_runs": {e["label"]: {"family": e["family"],
                              "overrides": {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in e["overrides"].items()},
                              "panel": {k: float(e["panel"][k]) for k in ("cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd")}}
                 for e in runs if e["label"] != "anchor"},
}
Path("_build/manifest_40.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_40.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "40-backtest-lead-forensics-cash-sleeve.ipynb")
