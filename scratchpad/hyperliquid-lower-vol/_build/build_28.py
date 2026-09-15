import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY
from blocks_prefilter import INDICATOR_ADDITIONS_PREFILTER
from blocks_rules_fixes import PARAM_ADDITIONS_RULES_FIXES, INDICATOR_ADDITIONS_RULES_FIXES, \
    CELL14_REPLACEMENTS_RULES_FIXES

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()
HARNESS_RULES = (BUILD_DIR / "harness_rules.py").read_text()
HARNESS_RULES_V2 = (BUILD_DIR / "harness_rules_v2.py").read_text()

HEADING = """# NB28 - which stability signals predict forward stability?

Gate 5 of [RESEARCH-RULES.md](RESEARCH-RULES.md): *before* a mechanism is backtested, its score
read at a decision timestamp must rank-correlate positively across candidates with those vaults'
REALISED FORWARD stability. Not forward return. A mechanism that fails this is not selecting
stable vaults, and whatever portfolio Sharpe it reaches is incidental.

**Nothing in this notebook or in NB29-NB31 can be adopted, and ADOPT is not in their vocabulary.**
The screen chooses signals using 30-day forward windows and the backtests then judge portfolios
built from those signals on returns that overlap the same windows. Procedural ordering does not
make the screen out-of-sample, and on 126 decisions whose minimum detectable Sharpe difference is
about 2.50 no purge or split repairs that. The deliverable of this batch is a ranked shortlist
and a frozen prospective specification. Verdicts are SHORTLIST / REJECT / DIAGNOSTIC.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) as the anchor, the plan in
[28-stable-selection-plan.md](28-stable-selection-plan.md) Draft 2, and the rejected-experiment
lessons from [25-research-stability-comparison.ipynb](25-research-stability-comparison.ipynb) and
[26-backtest-drop-decomposition.ipynb](26-backtest-drop-decomposition.ipynb). Full window
2026-01-01 to 2026-09-08, in-sample throughout.

## Method

One logging run populates `PREFILTER_LOG` with the candidate pool the trading code actually
ranked at each decision - never reconstructed offline, because a reconstruction cannot mirror
`is_good_pair`, the quarantine list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the momentum gate,
strict admission or the tie order. Thirteen signals are read at T-1 for every candidate on every
eligible decision, and four forward targets are measured over `(T, T + 30 days]` from the NAV
carried at T, so no event straddles the decision.

Inference is ONE two-way cluster bootstrap - circular moving blocks of 15 decisions over dates,
vault clusters resampled together - whose resamples every hypothesis shares, with simultaneous
one-sided max-T bounds over two pre-registered families: 39 stability hypotheses and 13 return
hypotheses. Sharing resamples is what makes the simultaneous bound valid; resampling each
hypothesis separately destroys the dependence a max-statistic is entirely about.

Gate 5's pass rule, pre-registered: all THREE of forward volatility, forward downside variation
and forward fresh-event top-five share show a positive association with the signal's stable end,
with the simultaneous lower bound above zero; AND the simultaneous lower bound on the
stable-versus-unstable forward 30-day return contrast exceeds `-delta`, with `delta = 5`
annualised percentage points.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "28-research-stability-signal-screen",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_RULES_FIXES},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY
    + INDICATOR_ADDITIONS_PREFILTER + INDICATOR_ADDITIONS_RULES_FIXES,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_RULES_FIXES)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))
cells.append(code(HARNESS_RULES))
cells.append(code(HARNESS_RULES_V2))

cells.append(md("""## Part 0. Provenance and anchor parity

Every conclusion below rests on one data snapshot. The content hashes make "the same data as
NB20-NB26" a checkable claim rather than an assumption, and the parity assertion proves all three
`decide_trades` splices are inert on the anchor path.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity_rules())
record_anchor()
print(f"\\ngate 5's non-inferiority margin delta = {DELTA_ANNUALISED_PP} annualised percentage points")
print(f"forward horizon {FORWARD_HORIZON_DAYS} days; tail fraction {TAIL_FRACTION}; "
      f"{SCREEN_DRAWS} bootstrap draws, date block {SCREEN_DATE_BLOCK}, seed {SCREEN_SEED}")
display(pd.DataFrame(SIGNALS).set_index("name"))
'''))

cells.append(md("""## Part 1. The logging run

`stability_prefilter_signal = 'inverse_vol'` with `fraction = 0.0`: the block runs, reads and
logs every candidate's signal, and excludes nobody. It must therefore reproduce `BASELINE` on
every metric. If it does not, the logging itself is changing the decision and the pool recorded
below is not the pool the anchor ranked.
"""))
cells.append(code('''logging_run = run_and_record("screen_log", "control",
                             **prefilter_overrides("inverse_vol", fraction=0.0))
parity = assert_anchor_parity(logging_run["panel"])
display(parity)
log = logging_run["prefilter_log"]
counts = prefilter_exclusion_frame(logging_run)
print(f"decisions logged: {len(log)}")
assert int(counts["excluded"].sum()) == 0, "the logging run excluded candidates; it is not inert"
display(counts[["pool_size", "measured", "nan", "excluded", "remaining"]].describe().round(3))
'''))

cells.append(md("""## Part 2. The panel, its eligibility and what is missing from it

Only decisions whose FULL 30-day forward window lies inside the archive are eligible. The rest
are dropped and counted rather than evaluated on a truncated window, which would make a
late-window vault look artificially calm. The notebook never claims 126 decisions.

Every target carries an explicit missing-reason code. The event-concentration target needs at
least 8 positive residual events in the window. The gate target is the EXCESS of the top-five
share over the uniform-events value `min(5, n)/n`: the raw share is bounded below by 5/n - 0.625
at eight events, 0.10 at fifty - so it partly measured how often a vault reported, which the
first review of this notebook caught. The raw share and the event count are kept as diagnostics.
"""))
cells.append(code('''panel_frame, eligibility = build_screen_panel(logging_run)
display(eligibility.groupby("eligible").agg(decisions=("date", "size"),
                                            first=("date", "min"), last=("date", "max")))
display(missing_reason_table(panel_frame))
'''))

cells.append(code('''# Per-signal NaN rate on the tradable pool, and the fresh-event window spans.
pairs_by_id = {pid: strategy_universe.get_pair_by_id(pid) for pid in panel_frame["pair_id"].unique()}
nan_rows = []
for name in SIGNAL_NAMES:
    finite = np.isfinite(panel_frame[name])
    nan_rows.append({
        "signal": name, "finite_reads": int(finite.sum()),
        "nan_reads": int((~finite).sum()),
        "nan_rate": float((~finite).mean()),
        "distinct_vaults_with_a_value": int(panel_frame.loc[finite, "pair_id"].nunique()),
    })
display(pd.DataFrame(nan_rows).set_index("signal").sort_values("nan_rate"))

spans = []
for pair_id, date in zip(panel_frame["pair_id"], panel_frame["date"]):
    spans.append(value_at_prior(indicator_series("fresh_event_window_span", pairs_by_id[pair_id]), date))
panel_frame["fresh_event_span_days"] = spans
finite_spans = panel_frame["fresh_event_span_days"].dropna()
print(f"fresh-event window calendar spans over {len(finite_spans)} reads with a value:")
display(finite_spans.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).round(1).to_frame("days"))
'''))

cells.append(md("""## Part 3. The screen

One bootstrap, shared resamples, two pre-registered families with simultaneous max-T bounds. The
estimand is stated rather than implied: the equal-weight mean association on a TYPICAL decision
date - per date, Spearman across that date's candidates, signed so positive means the signal's
stable end had the more stable outcome, then averaged over eligible dates.

The sample is complete-case per signal, over the signal and all four targets together, so a
signal's four correlations describe the same candidates. It differs BETWEEN signals, so the row
and date counts are printed beside every estimate and a signal with fewer than 40 usable dates is
not evaluated at all.
"""))
cells.append(code('''# Two screens from ONE panel. The PRE-REGISTERED screen uses the raw forward top-five share, as the
# plan and harness_rules.py specified, and gives the gate-5 verdict. The CORRECTED screen uses the
# excess over the uniform-events value, which the first review showed removes a 5/n floor; it was
# introduced after results were known, so it is a post-review diagnostic and not the gate.
PRE_TARGETS = ["forward_vol", "forward_downside", "forward_event_top5"]
COR_TARGETS = ["forward_vol", "forward_downside", "forward_event_top5_excess"]
print("pre-registered screen (raw top-five share):")
screen, detail, bootstrap = run_screen(panel_frame, "pre_registered")
print(f"  stability family: {detail['stability']['family_size_used']} of {detail['stability']['family_size_total']} "
      f"hypotheses evaluated; critical {detail['stability']['critical']:.4f} on "
      f"{detail['stability']['n_draws']} complete draws of {detail['stability']['n_draws_total']}")
print(f"  return family:    {detail['returns']['family_size_used']} of {detail['returns']['family_size_total']} "
      f"hypotheses evaluated; critical {detail['returns']['critical']:.4f} on "
      f"{detail['returns']['n_draws']} complete draws")
print("\\ncorrected screen (excess over uniform):")
screen_cor, detail_cor, bootstrap_cor = run_screen(panel_frame, "corrected", verbose=False)
print(f"  stability family: {detail_cor['stability']['family_size_used']} of {detail_cor['stability']['family_size_total']}; "
      f"critical {detail_cor['stability']['critical']:.4f} on {detail_cor['stability']['n_draws']} complete draws")
print("\\nPRE-REGISTERED screen:")
display(screen[["rows", "dates", "evaluated", "rho_forward_vol", "lo_forward_vol", "rho_forward_downside",
                "lo_forward_downside", "rho_forward_event_top5", "lo_forward_event_top5"]].round(4))
print("\\nCORRECTED screen (post-review diagnostic):")
display(screen_cor[["rows", "dates", "evaluated", "rho_forward_event_top5_excess", "lo_forward_event_top5_excess",
                    "stability_clause", "return_clause", "gate_5"]].round(4))
'''))

cells.append(code('''display(screen[["direction", "time_base", "dates", "enough_dates", "rho_forward_return",
                "return_contrast_pp", "return_lo_pp", "stability_clause", "return_clause",
                "gate_5"]].round(4))
passers = [s for s in SIGNAL_NAMES if bool(screen.loc[s, "gate_5"])]
print(f"\\nsignals passing gate 5 ({len(passers)} of {len(SIGNAL_NAMES)}): "
      f"{', '.join(passers) if passers else 'none'}")
print(f"delta = {detail['delta']} annualised pp; the return clause needs the simultaneous lower "
      f"bound above {-detail['delta']:.1f}")
'''))

cells.append(md("""### Why gate 5 resolved as it did

A verdict of "fails gate 5" is not one fact but up to four, and reporting it as one is how this
track has under-reported failures before. This decomposes it: which of the three stability targets
each signal cleared, and how wide the return interval actually is relative to the 5-point margin.

A margin can only discriminate if it is large relative to the uncertainty it is being compared
against. The half-width column says whether that is true here.
"""))
cells.append(code('''rows = []
for i, name in enumerate(SIGNAL_NAMES):
    cleared = [t for j, t in enumerate(PRE_TARGETS)
               if np.isfinite(detail["stability"]["lower_simultaneous"][i, j])
               and detail["stability"]["lower_simultaneous"][i, j] > 0]
    contrast = detail["returns"]["observed"][i, 0]
    lower = detail["returns"]["lower_simultaneous"][i, 0]
    rows.append({
        "signal": name,
        "stability_targets_cleared": f"{len(cleared)}/3",
        "which": ", ".join(t.replace("forward_", "") for t in cleared) or "-",
        "missing": ", ".join(t.replace("forward_", "") for t in PRE_TARGETS
                             if t not in cleared) or "-",
        "return_contrast_pp": contrast,
        "return_lo_pp": lower,
        "return_half_width_pp": contrast - lower,
        "margin_pp": -detail["delta"],
        "margin_as_share_of_half_width": abs(detail["delta"]) / (contrast - lower)
        if np.isfinite(contrast - lower) and (contrast - lower) > 0 else np.nan,
    })
decomposition = pd.DataFrame(rows).set_index("signal")
display(decomposition.round(4))

# The raw magnitudes the return contrast is built from, so its scale can be checked rather than
# trusted. A mean over a heavy-tailed cross-section is dominated by its tail, and the median is
# printed beside it to make that visible.
forward = panel_frame["forward_return"].replace([np.inf, -np.inf], np.nan).dropna()
print(f"forward 30-day log NAV return over {len(forward)} (candidate, date) rows:")
display(forward.describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).round(4).to_frame("log return"))
print(f"annualising factor applied to the contrast: 365/{FORWARD_HORIZON_DAYS} x 100 = "
      f"{365.0 / FORWARD_HORIZON_DAYS * 100:.1f}")
print(f"so a 1 percentage-point 30-day gap reads as {365.0 / FORWARD_HORIZON_DAYS:.2f} "
      f"annualised percentage points")
'''))

cells.append(code('''# Unadjusted per-hypothesis bounds, DESCRIPTIVE only, for the pre-registered screen. Printed
# because the simultaneous bound over 39 hypotheses is conservative and the gap between the two
# is worth seeing; no verdict is written from this table.
rows = []
for i, name in enumerate(SIGNAL_NAMES):
    for j, target in enumerate(PRE_TARGETS):
        rows.append({
            "signal": name, "target": target,
            "rho": detail["stability"]["observed"][i, j],
            "se": detail["stability"]["se"][i, j],
            "lo_unadjusted": detail["stability"]["lower_unadjusted"][i, j],
            "lo_simultaneous": detail["stability"]["lower_simultaneous"][i, j],
            "p_add_one": detail["stability"]["p"][i, j],
        })
unadjusted = pd.DataFrame(rows).set_index(["signal", "target"])
display(unadjusted.round(4))
'''))

cells.append(md("""### Can this screen pass anything? Near-perfect-foresight oracles

Standing rule 9: a surprising null must be shown unreachable, not merely unobserved. Three oracle
signals are appended to the panel and run through the same bootstrap and simultaneous bounds:

- `oracle_vol`: the forward volatility itself plus 5% noise (direction 'high').
- `oracle_return`: the forward return itself plus 5% noise (direction 'low').
- `oracle_all`: the per-date mean rank of ALL THREE forward stability targets plus noise
  (direction 'high') - a signal that knows every target the stability clause requires.

The noise is there because a signal that equals its target has a bootstrap standard error of
exactly zero, which the studentised max-T cannot evaluate; a first version without it was
dropped from the family as unevaluable. If `oracle_all` passes the stability clause, the clause
is reachable on this panel and the thirteen real signals failed it on their merits. If
`oracle_vol` fails it, no amount of volatility foresight satisfies a conjunction that includes
event concentration - which says something about the gate's design, not about the signals.
"""))
cells.append(code('''def oracle_reachability_v3(panel_frame, concentration="pre_registered", draws=200, seed=SCREEN_SEED + 1):
    """Three noisy oracles through the same screen. Defined here, not in harness_rules_v2.py, so
    NB29-NB31, which embed that module, stay regenerable."""
    global SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION
    saved = (SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION)
    rng = np.random.default_rng(seed)
    frame = panel_frame.copy()
    target_conc = CONCENTRATION_TARGETS[concentration]

    def jitter(series):
        scale = 0.05 * float(series.std())
        return series + rng.normal(0.0, scale, len(series))

    frame["oracle_vol"] = jitter(frame["forward_vol"])
    frame["oracle_return"] = jitter(frame["forward_return"])
    # Per-date mean rank across the three targets the stability clause names, higher = less stable.
    ranks = frame.groupby("date")[["forward_vol", "forward_downside", target_conc]].rank(pct=True)
    frame["oracle_all"] = jitter(ranks.mean(axis=1))
    SIGNALS = list(SIGNALS) + [
        {"name": "oracle_vol", "direction": "high", "time_base": "foresight", "note": "= forward_vol + noise"},
        {"name": "oracle_return", "direction": "low", "time_base": "foresight", "note": "= forward_return + noise"},
        {"name": "oracle_all", "direction": "high", "time_base": "foresight", "note": "= mean rank of three targets + noise"},
    ]
    SIGNAL_NAMES = [s["name"] for s in SIGNALS]
    SIGNAL_DIRECTION = {s["name"]: s["direction"] for s in SIGNALS}
    try:
        table, detail, _ = run_screen(frame, concentration, draws=draws, seed=seed, verbose=False)
    finally:
        SIGNALS, SIGNAL_NAMES, SIGNAL_DIRECTION = saved
    keep = ["dates", "evaluated"] + [c for c in table.columns if c.startswith("rho_") or c.startswith("lo_")] + \\
           ["return_contrast_pp", "return_lo_pp", "stability_clause", "return_clause", "gate_5"]
    return table.loc[["oracle_vol", "oracle_return", "oracle_all"], keep].copy()


oracle = oracle_reachability_v3(panel_frame, "pre_registered", draws=200)
display(oracle.round(4))
for name in ("oracle_vol", "oracle_all"):
    print(f"{name:>14}: evaluated {bool(oracle.loc[name, 'evaluated'])}, stability clause "
          f"{bool(oracle.loc[name, 'stability_clause'])}  (lower bounds vol {oracle.loc[name, 'lo_forward_vol']:+.3f}, "
          f"downside {oracle.loc[name, 'lo_forward_downside']:+.3f}, concentration {oracle.loc[name, 'lo_forward_event_top5']:+.3f})")
print(f" oracle_return: evaluated {bool(oracle.loc['oracle_return', 'evaluated'])}, return clause "
      f"{bool(oracle.loc['oracle_return', 'return_clause'])}  (contrast {oracle.loc['oracle_return', 'return_contrast_pp']:+.1f} pp, "
      f"lower bound {oracle.loc['oracle_return', 'return_lo_pp']:+.1f} pp, margin -{DELTA_ANNUALISED_PP:.0f})")
print(f"\\nforward volatility foresight vs forward event concentration: rho {oracle.loc['oracle_vol', 'rho_forward_event_top5']:+.4f} "
      f"- the two targets are {'nearly orthogonal' if abs(oracle.loc['oracle_vol', 'rho_forward_event_top5']) < 0.2 else 'related'} on this panel")
'''))

cells.append(md("""## Part 4. The tail-aligned contrast

The Spearman satisfies the rule; this tests the mechanism. At each date the exact set that WOULD
be excluded at `q = 0.30` is compared against the retained set on each forward target. A monotone
association across the whole cross-section does not guarantee that the specific 30% the
mechanism removes is the part that misbehaves.

Stability contrasts are in normalised-rank units and are reported as a DIAGNOSTIC with their own
simultaneous control. The RETURN contrast, in annualised percentage points, is the pre-registered
family gate 5's non-inferiority clause is written on.

One limitation, stated rather than discovered later: the contrast is computed on the complete-case
screen sample, so it approximates the mechanism's tail rather than reproducing it. The mechanism
excludes among every finite-signal candidate in the pool, including those whose forward targets
are missing.
"""))
cells.append(code('''rows = []
for i, name in enumerate(SIGNAL_NAMES):
    row = {"signal": name}
    for j, target in enumerate(PRE_TARGETS):
        row[f"tail_{target}"] = detail["tails"]["observed"][i, j]
        row[f"lo_{target}"] = detail["tails"]["lower_simultaneous"][i, j]
    row["return_contrast_pp"] = detail["returns"]["observed"][i, 0]
    row["return_lo_pp"] = detail["returns"]["lower_simultaneous"][i, 0]
    rows.append(row)
tail_table = pd.DataFrame(rows).set_index("signal")
display(tail_table.round(4))
print(f"stability tail family critical value: {detail['tails']['critical']:.4f} (DIAGNOSTIC)")

agreement = pd.DataFrame({
    "spearman_positive": [bool(screen.loc[s, "rho_forward_vol"] > 0) for s in SIGNAL_NAMES],
    "tail_positive": [bool(tail_table.loc[s, "tail_forward_vol"] > 0) for s in SIGNAL_NAMES],
}, index=SIGNAL_NAMES)
print("\\nsignals where the rule and the mechanism disagree in sign on forward volatility:")
display(agreement[agreement["spearman_positive"] != agreement["tail_positive"]])
'''))

cells.append(md("""## Part 5. The calendar clock against the fresh-event clock

`residual_event_concentration` asks how much of the last 180 DAYS' upside came from five days.
`fresh_event_concentration` asks how much of the last 90 price MOVES' upside came from five
moves. On a cohort where most vaults are stale on most days those are different questions.

This is a PAIRED DIFFERENCE on the same resamples, not two intervals side by side. Two
overlapping intervals do not establish that the underlying quantities are equal, and two disjoint
ones on dependent estimates overstate how strongly they differ. The heading reports the
difference and its interval. It does not say the question is settled.
"""))
cells.append(code('''# On ONE common (date, vault) sample where both signals are finite, with its own bootstrap.
# Sharing resamples across two different complete-case samples - what the first build did - is
# not a paired comparison; the review was right.
difference, bootstrap_common, common_rows = paired_measure_difference_common(
    panel_frame, "fresh_event_concentration", "residual_event_concentration")
print(f"common sample: {common_rows} (date, vault) rows where both signals are finite")
display(difference.round(4))

# The corrected calendar indicator, as a DESCRIPTIVE diagnostic outside the pre-registered
# thirteen: per-date Spearman against each target, no bootstrap, no multiplicity control.
panel_frame["residual_event_concentration_positive"] = [
    value_at_prior(indicator_series("residual_event_concentration_positive", pairs_by_id[pid]), d)
    for pid, d in zip(panel_frame["pair_id"], panel_frame["date"])
]
rows = []
for target in PRE_TARGETS + ["forward_event_top5_excess", "forward_return"]:
    values = []
    for _d, group in panel_frame.groupby("date"):
        joined = group[["residual_event_concentration_positive", target]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(joined) >= SCREEN_MIN_CANDIDATES and joined.iloc[:, 0].nunique() > 1 and joined.iloc[:, 1].nunique() > 1:
            values.append(joined.iloc[:, 0].corr(joined.iloc[:, 1], method="spearman"))
    # direction 'high' for concentration: positive raw Spearman = spiky vaults have MORE forward vol
    rows.append({"target": target, "mean_raw_spearman": float(np.mean(values)) if values else np.nan,
                 "signed_as_screen": float(np.mean(values)) if values else np.nan, "dates": len(values)})
corrected_diag = pd.DataFrame(rows).set_index("target")
print("\\nresidual_event_concentration_positive (corrected NB08 indicator), descriptive only:")
display(corrected_diag.round(4))
'''))

cells.append(md("""## Part 6. Persistence, and the two confounds

Rank persistence across consecutive decisions is a DIAGNOSTIC, not a filter. A signal that does
not persist across two days cannot be selecting a durable property - but persistence is not
evidence of predictiveness either: the staleness control persists almost perfectly.

The two confounds this track already knows about are staleness and size. NB20 found staleness
correlates -0.46 with TVL, and the gap-to-loss effect vanishes above the $7,500 screen. A
"stability" signal that is really a size proxy would reproduce that pattern.
"""))
cells.append(code('''display(rank_persistence(panel_frame).round(4))

panel_frame["tvl"] = [
    value_at_prior(indicator_series("tvl", pairs_by_id[pid]), d)
    for pid, d in zip(panel_frame["pair_id"], panel_frame["date"])
]
rows_confound = []
for name in SIGNAL_NAMES:
    staleness, size = [], []
    for _date, group in panel_frame.groupby("date"):
        for column, sink in (("fresh_observation_count", staleness), ("tvl", size)):
            if column == name:
                # `fresh_observation_count` is itself one of the thirteen signals. Selecting it
                # twice returns a DataFrame, not a Series, and its self-correlation is 1.0 by
                # construction and says nothing; skip it rather than report a trivial figure.
                continue
            joined = group[[name, column]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(joined) >= SCREEN_MIN_CANDIDATES and joined[name].nunique() > 1 \\
                    and joined[column].nunique() > 1:
                sink.append(joined[name].corr(joined[column], method="spearman"))
    rows_confound.append({
        "signal": name,
        "rho_vs_fresh_observation_count": (float(np.mean(staleness)) if staleness
                                           else (1.0 if name == "fresh_observation_count" else np.nan)),
        "rho_vs_tvl": float(np.mean(size)) if size else np.nan,
        "dates": len(size),
    })
display(pd.DataFrame(rows_confound).set_index("signal").round(4))
'''))

cells.append(md("""## Part 7. What the screen leaves for NB29

A DIAGNOSTIC notebook: it produces no verdict on any portfolio, only the pre-registered gate-5
result each signal carries forward. A signal failing gate 5 is REJECTED without a backtest;
`inverse_vol` is carried into NB29 as the reference whatever it does here, labelled as such,
because it is the sizing rule's own premise and NB26's `measured_only` drop.
"""))
cells.append(code('''summary = screen[["dates", "rows", "stability_clause", "return_clause", "gate_5"]].copy()
summary["carried_to_nb29"] = [bool(screen.loc[s, "gate_5"]) or s == "inverse_vol"
                              for s in summary.index]
summary["role"] = ["reference" if s == "inverse_vol" else
                   ("candidate" if bool(screen.loc[s, "gate_5"]) else "rejected at gate 5")
                   for s in summary.index]
display(summary)

import json
from pathlib import Path
manifest = {
    "verdict": "DIAGNOSTIC - a screen, not a result",
    "delta_annualised_pp": float(DELTA_ANNUALISED_PP),
    "forward_horizon_days": int(FORWARD_HORIZON_DAYS),
    "tail_fraction": float(TAIL_FRACTION),
    "bootstrap": {"draws": int(SCREEN_DRAWS), "date_block": int(SCREEN_DATE_BLOCK),
                  "seed": int(SCREEN_SEED),
                  "stability_critical": float(detail["stability"]["critical"]),
                  "return_critical": float(detail["returns"]["critical"]),
                  "tail_critical": float(detail["tails"]["critical"]),
                  "stability_family_used": int(detail["stability"]["family_size_used"]),
                  "return_family_used": int(detail["returns"]["family_size_used"])},
    "eligible_decisions": int(eligibility["eligible"].sum()),
    "logged_decisions": int(len(eligibility)),
    "panel_rows": int(len(panel_frame)),
    "provenance": provenance_record(),
    "gate_5": {s: bool(screen.loc[s, "gate_5"]) for s in SIGNAL_NAMES},
    "gate_5_corrected_target": {s: bool(screen_cor.loc[s, "gate_5"]) for s in SIGNAL_NAMES},
    "screen_full": screen.to_dict(orient="index"),
    "screen_corrected": screen_cor.round(6).to_dict(orient="index"),
    "screen_corrected_bootstrap": {"stability_critical": float(detail_cor["stability"]["critical"]),
                                   "n_draws": int(detail_cor["stability"]["n_draws"]),
                                   "family_size_used": int(detail_cor["stability"]["family_size_used"])},
    "oracle": oracle.to_dict(orient="index"),
    "targets_pre_registered": PRE_TARGETS, "targets_corrected": COR_TARGETS,
    "carried_to_nb29": [s for s in summary.index if bool(summary.loc[s, "carried_to_nb29"])],
    "screen": screen.round(6).to_dict(orient="index"),
    "tails": tail_table.round(6).to_dict(orient="index"),
    "calendar_vs_fresh": difference.round(6).to_dict(orient="index"),
    "calendar_vs_fresh_common_rows": int(common_rows),
    "decomposition": decomposition.round(6).to_dict(orient="index"),
    "unadjusted": unadjusted.round(6).reset_index().to_dict(orient="records"),
    "missing_reasons": missing_reason_table(panel_frame).to_dict(orient="records"),
    "nan_rates": pd.DataFrame(nan_rows).set_index("signal").round(6).to_dict(orient="index"),
    "spans": finite_spans.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).round(2).to_dict(),
    "persistence": rank_persistence(panel_frame).round(6).to_dict(orient="index"),
    "confounds": pd.DataFrame(rows_confound).set_index("signal").round(6).to_dict(orient="index"),
    "forward_return_describe": forward.describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).round(6).to_dict(),
    "corrected_concentration_diagnostic": corrected_diag.round(6).to_dict(orient="index"),
    "draws_complete": {"stability": int(detail["stability"]["n_draws"]), "returns": int(detail["returns"]["n_draws"]),
                       "tails": int(detail["tails"]["n_draws"]), "total": int(detail["stability"]["n_draws_total"])},
}
Path("_build/manifest_28.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_28.json")
'''))

cells += integrity_and_audit_cells()
write_notebook(cells, TRACK_DIR / "28-research-stability-signal-screen.ipynb")
