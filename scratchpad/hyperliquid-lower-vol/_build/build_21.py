"""NB21 - the volatility-matched drop family, promoted from control to candidate (lead 1).

20-stability-leads-plan.md, section "NB21 - backtest: the vol-matched family as a candidate".

The family that NB15/NB19 used as the pre-registered CONTROL is here the candidate set. That is
why constraint 7 (best observed control at or below the candidate's volatility, plus 0.10) is
INAPPLICABLE rather than merely unevaluated: every member would be compared against itself and
asked for `S >= S + 0.10`. This notebook therefore reports `passes_1_to_6` and never `passes_v3`.
"""
import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import PARAM_ADDITIONS_STABILITY, INDICATOR_ADDITIONS_STABILITY, \
    CELL14_REPLACEMENTS_STABILITY

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

HEADING = """# NB21 - backtest: the volatility-matched family as a candidate (lead 1)

The pre-registered `vol_matched_drop_count` family - drop the N highest-volatility candidates
before ranking, change nothing else - was the CONTROL in the previous plan. `drop_50` there
delivered better volatility, ulcer and beta than any mechanism that plan built, for 17 percentage
points of CAGR, and it was never plateau-checked or leave-one-vault-out checked because a control
does not need to be. This notebook runs the whole family at 5-step spacing and puts it through the
adoption machinery as a candidate.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Lead 1 of [20-stability-leads-plan.md](20-stability-leads-plan.md).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "21-backtest-vol-matched-family",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_STABILITY)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

# ---------------------------------------------------------------------------------------------
# 1. Provenance and anchor parity
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Provenance and anchor parity

The content hashes below decide what this notebook can conclude. The anchor is the unchanged
`02-better-format.ipynb` configuration, run in this kernel with both stability-track
`decide_trades` splices present but disabled - `assert_anchor_parity()` asserts that both
diagnostic logs are empty afterwards, which is the evidence that neither splice fired rather
than the assumption that it did not.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
#: Trailing semicolon only: `record_anchor()` returns the whole run entry, and letting Jupyter
#: echo it prints the anchor's full equity, returns and cycle-return series into the notebook.
record_anchor();
'''))

# ---------------------------------------------------------------------------------------------
# 2. The family
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The volatility-matched family

Twelve runs, `drop_5` through `drop_60` in steps of 5, each through `run_and_record()` in this
same kernel. `build_family()` labels them `control` because that is what they are everywhere else
in this plan - in NB22 and NB23 this same family is the constraint-7 comparator. In THIS notebook
they are the candidates under test, so they are relabelled immediately below and the consequence
for constraint 7 is printed rather than left implicit.

The three reference values from the previous plan (NB15/NB19, same configuration, 10-step
spacing) are checked against the corresponding members here. They are a sanity check on the data
snapshot, not an adoption gate, so they are displayed rather than asserted.
"""))
cells.append(code('''family = build_family()

for n in FAMILY_DROPS:
    run_by_label[f"drop_{n}"]["family"] = "candidate"

print("In NB21 the volatility-matched family IS the candidate set, so constraint 7 would compare "
      "each member against itself and require S >= S + 0.10. It is inapplicable here, not merely "
      "unevaluated, so this notebook reports passes_1_to_6 and never passes_v3.")

display(family[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "cycle_sortino", "ulcer",
                "abs_invested_beta", "mean_invested", "late_cagr", "late_ulcer"]])
'''))

cells.append(code('''#: Reference values from the previous plan on this same configuration (15-backtest-placebo-frontier
#: and 19-backtest-closeout). If these do not reproduce, the data snapshot moved under the track
#: and nothing below is comparable with NB15-NB19.
REFERENCE_FROM_PREVIOUS_PLAN = {
    "anchor":  (0.378971, 2.159792),
    "drop_30": (0.489942, 2.747391),
    "drop_50": (0.206149, 2.014857),
    "drop_60": (0.116576, 1.472421),
}
reference_rows = []
for label, (expected_cagr, expected_sharpe) in REFERENCE_FROM_PREVIOUS_PLAN.items():
    row = run_by_label[label]["panel"]
    reference_rows.append({
        "label": label,
        "expected_cagr": expected_cagr, "actual_cagr": float(row["cagr"]),
        "cagr_abs_diff": abs(float(row["cagr"]) - expected_cagr),
        "expected_cycle_sharpe": expected_sharpe, "actual_cycle_sharpe": float(row["cycle_sharpe"]),
        "sharpe_abs_diff": abs(float(row["cycle_sharpe"]) - expected_sharpe),
        "reproduced": bool(abs(float(row["cagr"]) - expected_cagr) <= 1e-5
                           and abs(float(row["cycle_sharpe"]) - expected_sharpe) <= 1e-5),
    })
reference_check = pd.DataFrame(reference_rows).set_index("label")
display(reference_check)
print(f"Every previous-plan reference value reproduced: {bool(reference_check['reproduced'].all())}")
'''))

# ---------------------------------------------------------------------------------------------
# 3. Verdict table
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Verdict table

Constraints 1-6 of adoption rule v3 (identical to v2's): CAGR >= 20%; cycle Sharpe >= anchor
- 0.10; cycle volatility <= anchor; ulcer <= 0.85 x anchor; invested-basket beta < anchor; mean
invested >= 0.90. Constraint 7 is inapplicable, as printed above, so the verdict column is
`passes_1_to_6`.

`control_ref` - the best observed cycle Sharpe among family members no noisier than the row - is
shown **for information only**. Every family member is in its own at-or-below set, so
`control_ref >= cycle_sharpe` on every family row and no member can ever clear it by 0.10. That
is the definitional impossibility, made visible. The comparator is the row *itself* only where no
quieter member has a higher Sharpe: `drop_30` and `drop_35` are referenced against themselves,
while `drop_25` is referenced against `drop_30`. Either way the 0.10 margin is unreachable.

The `failed` column is never truncated (`harness_evidence.py` sets `display.max_colwidth = None`).
Two views: by Sharpe, and by drop count, so the shape over N is readable.
"""))
cells.append(code('''VERDICT_COLUMNS = [
    "family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
    "cagr_sacrifice_pp", "control_ref", "passes_1_to_6", "failed", "late_ok",
]
verdict = verdict_table_v3(family=family, skip_placebo=True)
print("Sorted by cycle Sharpe:")
display(verdict[VERDICT_COLUMNS])

by_n = ["anchor"] + [f"drop_{n}" for n in FAMILY_DROPS]
print("Sorted by drop count (the shape over N):")
display(verdict.loc[by_n, VERDICT_COLUMNS])
'''))

# ---------------------------------------------------------------------------------------------
# 4. Plateau and eligibility
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Plateau and eligibility

A result that exists only at one setting of a dial is a coincidence, not a mechanism. A centre
qualifies only if it and both of its 5-step neighbours pass constraints 1-6 **and** the late
period (`late_cagr > 0` and `late_ulcer < anchor late_ulcer`).

`FAMILY_CENTRES` is N in {10, 15, ..., 55}. **N = 5 and N = 60 are boundary members of the
family: they can serve as a neighbour but never as a centre**, because a centre needs a
neighbour on both sides and the family stops at 5 and 60. A centre whose required neighbour run
is missing is False, never True - `centre_ok_of()` returns False for any label that is not in
`run_by_label`, so an unexecuted run can never produce a passing flag.

`simple_rule_eligible` is exactly `plateau_ok`: eligibility to be considered at all, before the
leave-one-vault-out re-simulation below.
"""))
cells.append(code('''def centre_ok_of(label: str) -> bool:
    """Constraints 1-6 and the late period for one recorded run. Missing run -> False, never True."""
    entry = run_by_label.get(label)
    if entry is None:
        return False
    row = entry["panel"]
    return bool(passes_1_to_6(row, anchor_panel) and late_period_ok_v3(row, anchor_panel))


plateau_rows = []
for n in FAMILY_CENTRES:
    lower, upper = f"drop_{n - 5}", f"drop_{n + 5}"
    centre_ok, lower_ok, upper_ok = centre_ok_of(f"drop_{n}"), centre_ok_of(lower), centre_ok_of(upper)
    plateau_rows.append({
        "n": n,
        "centre_ok": centre_ok,
        "lower_neighbour": lower, "lower_run_present": lower in run_by_label, "lower_ok": lower_ok,
        "upper_neighbour": upper, "upper_run_present": upper in run_by_label, "upper_ok": upper_ok,
        "plateau_ok": bool(centre_ok and lower_ok and upper_ok),
    })
plateau = pd.DataFrame(plateau_rows).set_index("n")
plateau["simple_rule_eligible"] = plateau["plateau_ok"]
display(plateau)

print(f"Eligible centres (simple_rule_eligible): "
      f"{[int(n) for n in plateau.index[plateau['simple_rule_eligible']]] or 'none'}")
print("N = 5 and N = 60 are boundary members of the family. They are neighbours only and are "
      "never evaluated as a centre, because a centre requires a neighbour on both sides.")
'''))

# ---------------------------------------------------------------------------------------------
# 5. Leave-one-vault-out
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Leave-one-vault-out

For every N that reached `plateau_ok`, the vault with the largest total P&L in that run is masked
from the first cycle (`MASKED_VAULTS`, through `run_variant(masked=...)`) and the whole backtest
is re-simulated, so substitution actually happens rather than the vault's realised profit merely
being subtracted afterwards. The masked run must itself pass constraints 1-6 and the late period.

A robustness run that was never executed can never produce a passing flag: if no N reaches
`plateau_ok`, nothing runs here and the verdict cell treats every centre's masked result as
absent, which is a fail.
"""))
cells.append(code('''def vault_profit_in(state_, address: str) -> float:
    """Total realised + unrealised P&L attributed to one pool address in one run."""
    total = 0.0
    for position in state_.portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        if str(position.pair.pool_address).lower() == address:
            total += float(position.get_total_profit_usd() or 0.0)
    return total


plateau_centres = [int(n) for n in plateau.index[plateau["plateau_ok"]]]
lovo_rows = []
if not plateau_centres:
    print("NO N REACHED plateau_ok, so no leave-one-vault-out run is executed in this notebook. "
          "Every centre's masked result is therefore ABSENT, which the verdict cell treats as a "
          "fail - an unexecuted robustness run cannot produce a passing flag.")
else:
    for n in plateau_centres:
        base = run_by_label[f"drop_{n}"]
        top = largest_contributing_vault(base["state"])
        masked_entry = run_and_record(
            f"drop_{n}__without_top_vault", "robustness", vol_matched_drop_count=n, masked={top},
        )
        row = masked_entry["panel"]
        lovo_rows.append({
            "n": n,
            "masked_vault": top,
            "masked_vault_profit_usd_unmasked_run": vault_profit_in(base["state"], top),
            "cagr": float(row["cagr"]), "cycle_sharpe": float(row["cycle_sharpe"]),
            "cycle_vol": float(row["cycle_vol"]), "ulcer": float(row["ulcer"]),
            "abs_invested_beta": float(row["abs_invested_beta"]),
            "mean_invested": float(row["mean_invested"]),
            "passes_1_to_6": bool(passes_1_to_6(row, anchor_panel)),
            "failed": failing_constraints_v3(row, anchor_panel, None, skip_placebo=True),
            "late_ok": bool(late_period_ok_v3(row, anchor_panel)),
        })
    display(pd.DataFrame(lovo_rows).set_index("n"))
'''))

# ---------------------------------------------------------------------------------------------
# 6. What the drop actually removed
# ---------------------------------------------------------------------------------------------
cells.append(md("""# What the drop actually removed

Read from each run's own `vol_drop_log`, written inside `decide_trades` at the moment of the
decision - **not** an offline reconstruction, which could not mirror `is_good_pair`, the
quarantine list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the momentum gate, strict admission or the
tie order.

Three things that are constantly confused and are kept strictly apart here:

- **No volatility estimate** (`inv_vol == 0.0` in the log): `inverse_vol` needs 90 observations.
  A vault with no estimate sorts to the very front of the ascending-inverse-volatility order, so
  it is removed *first* - and it is removed for having no measurement, not for being volatile.
- **Unscored by the composite** (`signal == 0.0` in the log): the incumbent composite's CAGR leg
  needs `cagr_lookback_days` = 360 days. A candidate whose composite is NaN is admitted at signal
  0 (the anchor does not use strict admission), so a zero signal means "unscored, or scored
  exactly zero".
- **Young**: fewer than 360 days old at that decision date, from NB13's life cache.

These are three different properties and the joint distribution is reported, not three margins.
The Jaccard overlap of the removed set between consecutive decision dates is a *description* of
how stable the removed set is. It is not a stopping rule and is not used as one anywhere in this
notebook.
"""))
cells.append(code('''from pathlib import Path

LIFE_CACHE = Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet")
AGE_BARRIER_DAYS = int(Parameters.cagr_lookback_days)   # 360, the composite's own requirement

if LIFE_CACHE.exists():
    _life = pd.read_parquet(LIFE_CACHE)
    _life.index = _life.index.astype(str).str.lower()
    INCEPTION = _life["inception"]
    print(f"NB13 life cache: {len(INCEPTION)} vaults, age barrier {AGE_BARRIER_DAYS} days.")
else:
    INCEPTION = pd.Series(dtype="datetime64[ns]")
    print("NB13 life cache MISSING - every removal will be counted as age-unmatched and reported "
          "as such, never silently dropped.")

#: The complete decision schedule, from the anchor's own equity-curve index (one point per
#: strategy cycle). The vol-drop branch only executes when the drop is enabled AND the pre-drop
#: pool is larger than N, so a decision date absent from a run's log is a date the branch did not
#: fire at all.
SCHEDULE = pd.DatetimeIndex(sorted(pd.Timestamp(ts) for ts in anchor_equity.index))
print(f"Decision schedule: {len(SCHEDULE)} dates, {SCHEDULE[0].date()} to {SCHEDULE[-1].date()}.")
'''))

cells.append(code('''def _log_by_timestamp(label: str) -> dict:
    return {pd.Timestamp(ts): entry for ts, entry in run_by_label[label]["vol_drop_log"].items()}


schedule_set = set(SCHEDULE)
drop_summary_rows, removal_records, jaccard_rows = [], [], []

for n in FAMILY_DROPS:
    log = _log_by_timestamp(f"drop_{n}")
    fired_dates = sorted(log)
    off_schedule = [ts for ts in fired_dates if ts not in schedule_set]
    absent = [ts for ts in SCHEDULE if ts not in log]
    pool_le_n = [ts for ts, e in log.items() if int(e["pool_size"]) <= n]

    pool_sizes = [int(e["pool_size"]) for e in log.values()]
    removed = [len(e["dropped_ids"]) for e in log.values()]
    no_estimate = [len(e["no_estimate_dropped"]) for e in log.values()]
    volatile_removals = [a - b for a, b in zip(removed, no_estimate)]

    drop_summary_rows.append({
        "n": n,
        "decision_dates": len(SCHEDULE),
        "branch_fired": len(fired_dates),
        "no_drop_branch_dates": len(absent) + len(pool_le_n),
        "no_drop_branch_share": (len(absent) + len(pool_le_n)) / len(SCHEDULE),
        "log_dates_off_schedule": len(off_schedule),
        "mean_pre_drop_pool_size": float(np.mean(pool_sizes)) if pool_sizes else float("nan"),
        "min_pre_drop_pool_size": float(np.min(pool_sizes)) if pool_sizes else float("nan"),
        "mean_removed": float(np.mean(removed)) if removed else float("nan"),
        "mean_removed_no_vol_estimate": float(np.mean(no_estimate)) if no_estimate else float("nan"),
        "mean_volatile_removals": float(np.mean(volatile_removals)) if volatile_removals else float("nan"),
        "no_vol_estimate_share_of_removals": (
            float(np.sum(no_estimate)) / float(np.sum(removed)) if np.sum(removed) else float("nan")
        ),
    })

    for ts, entry in log.items():
        inv_vol_map, signal_map = entry["inv_vol"], entry["signal"]
        for address in entry["dropped_addresses"]:
            inv_vol = float(inv_vol_map.get(address, 0.0))
            signal = float(signal_map.get(address, 0.0))
            if address in INCEPTION.index:
                age_days = (ts - pd.Timestamp(INCEPTION.loc[address])).days
                age_bucket = ("young (< %d d)" % AGE_BARRIER_DAYS) if age_days < AGE_BARRIER_DAYS \\
                    else ("old (>= %d d)" % AGE_BARRIER_DAYS)
            else:
                age_days, age_bucket = float("nan"), "age unmatched (not in NB13 life cache)"
            removal_records.append({
                "n": n, "timestamp": ts, "address": address,
                "volatility_estimate": "available" if inv_vol != 0.0 else "missing (inv_vol == 0)",
                "composite": "scored" if signal != 0.0 else "signal 0 (unscored or scored zero)",
                "age_bucket": age_bucket, "age_days": age_days,
            })

    # Jaccard overlap between CONSECUTIVE decision dates on the full schedule, so a date the
    # branch skipped counts as an empty removed set rather than being quietly stepped over.
    values = []
    both_empty = one_empty = 0
    for previous, current in zip(SCHEDULE, SCHEDULE[1:]):
        a = set(log[previous]["dropped_addresses"]) if previous in log else set()
        b = set(log[current]["dropped_addresses"]) if current in log else set()
        if not a and not b:
            both_empty += 1              # undefined, reported as missing - NOT 1.0
            continue
        if not a or not b:
            one_empty += 1
            values.append(0.0)
            continue
        values.append(len(a & b) / len(a | b))
    jaccard_rows.append({
        "n": n, "consecutive_pairs": len(SCHEDULE) - 1,
        "defined_pairs": len(values), "undefined_both_empty": both_empty,
        "one_empty_scored_zero": one_empty,
        "mean_jaccard": float(np.mean(values)) if values else float("nan"),
        "median_jaccard": float(np.median(values)) if values else float("nan"),
        "min_jaccard": float(np.min(values)) if values else float("nan"),
        "max_jaccard": float(np.max(values)) if values else float("nan"),
    })

drop_summary = pd.DataFrame(drop_summary_rows).set_index("n")
removals = pd.DataFrame(removal_records)
jaccard = pd.DataFrame(jaccard_rows).set_index("n")

print("Per-N drop composition, from each run's own vol_drop_log:")
display(drop_summary)
assert int(drop_summary["log_dates_off_schedule"].sum()) == 0, \\
    "a vol_drop_log timestamp is not on the anchor's decision schedule; the schedule derivation is wrong"
'''))

cells.append(code('''#: The joint distribution of what was removed. Three separate axes, never used interchangeably:
#: a volatility estimate exists or does not; the composite scored the vault or the signal was 0;
#: the vault was under or over the composite's own 360-day age requirement at that date.
if len(removals):
    joint = (
        removals.groupby(["volatility_estimate", "composite", "age_bucket", "n"]).size()
        .unstack("n", fill_value=0).sort_index()
    )
    print("Removals by (volatility estimate) x (composite) x (age), counts, one column per N:")
    display(joint)
    print("The same, as a share of that N's total removals:")
    display((joint / joint.sum(axis=0)).round(4))

    print("Pooled across the whole family, the three axes marginally and jointly:")
    display(removals.groupby(["volatility_estimate", "composite", "age_bucket"]).size()
            .rename("removals").to_frame().assign(
                share=lambda f: f["removals"] / f["removals"].sum()))

    unmatched = removals[removals["age_bucket"].str.startswith("age unmatched")]
    print(f"Removals whose vault is not in the NB13 life cache: {len(unmatched)} of {len(removals)} "
          f"({len(unmatched) / len(removals):.2%}), across "
          f"{unmatched['address'].nunique()} distinct addresses. Counted and reported, never dropped.")
else:
    print("No removals were logged at any N - the vol-matched drop branch never fired.")
'''))

cells.append(code('''print("Jaccard overlap of the removed address set between consecutive decision dates.")
print("Two empty sets are undefined and reported as missing, never as 1.0; one empty set is 0.0.")
print("This DESCRIBES how stable the removed set is. It is not a stopping rule and is not used as one.")
display(jaccard)
'''))

# ---------------------------------------------------------------------------------------------
# 7. Bootstrap margins
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Bootstrap margins on the decision that matters

For every centre with `centre_ok` True - not only the near-misses - the paired block-bootstrap
interval of the cycle-Sharpe difference, with common block indices across the aligned return
matrix so each draw compares both strategies on the same market days. Block lengths 5, 10 and 20
appear as separate rows, so a conclusion that depends on the block choice is visible as one. The
seed (0) and the draw count (1000) are fixed in `harness_stability.py`; they are NOT columns of
the table below.

**Against the anchor the decision boundary is -0.10** - the pre-registered Sharpe non-inferiority
tolerance. The interval either clears it or it does not; there is no third answer and no
adjustment of the boundary after seeing it.

The table also prints an "observed control" row, because `bootstrap_margin_table()` computes both
boundaries for every plan in this track. For both runs printed below that row is a
**self-comparison** - the `against` column names the run itself, because its own volatility puts
it in its own at-or-below set - and it is inapplicable here for exactly the reason printed in the
family cell. Read the anchor row.
"""))
cells.append(code('''centre_ok_centres = [int(n) for n in plateau.index[plateau["centre_ok"]]]
if not centre_ok_centres:
    print("No centre has centre_ok True, so there is no eligible centre to bootstrap. The margins "
          "for every family member against the anchor are still shown below for information.")
    for n in FAMILY_DROPS:
        display(bootstrap_margin_table(f"drop_{n}", family))
else:
    for n in centre_ok_centres:
        display(bootstrap_margin_table(f"drop_{n}", family))
'''))

# ---------------------------------------------------------------------------------------------
# 8. Charts
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The shape of the trade over N

CAGR, cycle Sharpe, cycle volatility and ulcer index against the number of highest-volatility
candidates dropped, with the anchor's own level marked on each. Then the equity curves of the
anchor and of every N that passed constraints 1-6, on a log axis.
"""))
cells.append(code('''import plotly.graph_objects as go

chart_frame = family.copy()
chart_frame = chart_frame.sort_values("drop_n")

METRIC_PANELS = [
    ("cagr", "CAGR"),
    ("cycle_sharpe", "Cycle Sharpe"),
    ("cycle_vol", "Cycle volatility"),
    ("ulcer", "Ulcer index"),
]
for column, title in METRIC_PANELS:
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=chart_frame["drop_n"], y=chart_frame[column], mode="lines+markers",
        name=f"vol_matched_drop_N ({column})", line=dict(color="steelblue"),
    ))
    figure.add_trace(go.Scatter(
        x=chart_frame["drop_n"], y=[float(anchor_panel[column])] * len(chart_frame), mode="lines",
        name=f"anchor {column} = {float(anchor_panel[column]):.4f}",
        line=dict(color="black", dash="dash"),
    ))
    figure.update_layout(
        title=f"{title} against the number of highest-volatility candidates dropped",
        xaxis_title="vol_matched_drop_count (N)", yaxis_title=column,
    )
    figure.show()
'''))

cells.append(code('''passing = [f"drop_{n}" for n in FAMILY_DROPS
            if bool(passes_1_to_6(run_by_label[f"drop_{n}"]["panel"], anchor_panel))]
print(f"Members passing constraints 1-6: {passing or 'none'}")

figure = go.Figure()
figure.add_trace(go.Scatter(
    x=anchor_equity.index, y=anchor_equity.values, mode="lines", name="anchor",
    line=dict(color="black", width=2),
))
for label in passing:
    equity_curve = run_by_label[label]["equity"]
    figure.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve.values, mode="lines", name=label))
# add_vline() raises on a datetime x axis in this environment (its annotation-position averaging
# does integer arithmetic on Timestamps); add_shape() plus add_annotation() is the equivalent call.
for name, x in (("regime break", "2026-04-01"), ("late period start", "2026-07-01")):
    figure.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, xref="x", yref="paper",
                     line=dict(dash="dot", color="grey"))
    figure.add_annotation(x=x, y=1, yref="paper", text=name, showarrow=False, yanchor="bottom")
figure.update_layout(
    title="Anchor and every family member passing constraints 1-6", yaxis_type="log",
    yaxis_title="equity (USD, log)",
)
figure.show()
'''))

# ---------------------------------------------------------------------------------------------
# 9. Verdict and frozen manifest
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Verdict

ADOPT - which means **admission to the prospective shadow protocol of NB24, not authorisation to
deploy capital** - the SMALLEST N for which the centre, both 5-step neighbours and the masked
centre all pass constraints 1-6 and the late period. If several qualify, the smallest is the
single shadow candidate and the others are listed. Otherwise REJECT, with the binding constraint
printed for every N.

The decision is computed here in code from `runs` / `run_by_label`, not asserted in prose, and
the frozen manifest below is what NB24 loads - it reproduces every gate from these numbers rather
than trusting this notebook's verdict word.
"""))
cells.append(code('''import json

qualifying, blocking_rows = [], []
for n in FAMILY_CENTRES:
    row = plateau.loc[n]
    centre_entry = run_by_label[f"drop_{n}"]
    masked_label = f"drop_{n}__without_top_vault"
    masked_entry = run_by_label.get(masked_label)
    masked_pass = bool(
        masked_entry is not None
        and passes_1_to_6(masked_entry["panel"], anchor_panel)
        and late_period_ok_v3(masked_entry["panel"], anchor_panel)
    )
    reasons = []
    if not bool(row["centre_ok"]):
        failed = failing_constraints_v3(centre_entry["panel"], anchor_panel, None, skip_placebo=True)
        reasons.append(f"centre fails: {failed or '(constraints 1-6 pass)'}"
                       + ("" if late_period_ok_v3(centre_entry["panel"], anchor_panel) else "; late period"))
    if not bool(row["lower_ok"]):
        reasons.append(f"lower neighbour {row['lower_neighbour']} fails")
    if not bool(row["upper_ok"]):
        reasons.append(f"upper neighbour {row['upper_neighbour']} fails")
    if not masked_pass:
        reasons.append("leave-one-vault-out absent (plateau never reached)" if masked_entry is None
                       else f"leave-one-vault-out fails: "
                            f"{failing_constraints_v3(masked_entry['panel'], anchor_panel, None, skip_placebo=True)}"
                            f"{'' if late_period_ok_v3(masked_entry['panel'], anchor_panel) else '; late period'}")
    if not reasons:
        qualifying.append(n)
    blocking_rows.append({
        "n": n, "centre_ok": bool(row["centre_ok"]), "lower_ok": bool(row["lower_ok"]),
        "upper_ok": bool(row["upper_ok"]), "plateau_ok": bool(row["plateau_ok"]),
        "masked_centre_ok": masked_pass, "qualifies": not reasons,
        "binding_constraints": "; ".join(reasons),
    })

blocking = pd.DataFrame(blocking_rows).set_index("n")
display(blocking)

#: The boundary members can never be a centre, but their own constraint result is part of the
#: complete picture, so it is printed too.
boundary = pd.DataFrame([
    {"n": n, "role": "boundary member (neighbour only, never a centre)",
     "passes_1_to_6": bool(passes_1_to_6(run_by_label[f"drop_{n}"]["panel"], anchor_panel)),
     "failed": failing_constraints_v3(run_by_label[f"drop_{n}"]["panel"], anchor_panel, None, skip_placebo=True),
     "late_ok": bool(late_period_ok_v3(run_by_label[f"drop_{n}"]["panel"], anchor_panel))}
    for n in (5, 60)
]).set_index("n")
display(boundary)

if qualifying:
    VERDICT = "ADOPT"
    shadow_candidate = min(qualifying)
    print(f"VERDICT: ADOPT drop_{shadow_candidate} - admission to the NB24 prospective shadow "
          f"protocol, NOT authorisation to deploy capital.")
    if len(qualifying) > 1:
        print(f"Also qualifying, listed but not the shadow candidate: "
              f"{[f'drop_{m}' for m in qualifying if m != shadow_candidate]}")
else:
    VERDICT = "REJECT"
    shadow_candidate = None
    print("VERDICT: REJECT. No N has a centre, both neighbours and a passing leave-one-vault-out "
          "re-simulation. The binding constraint for every N is in the table above; the complete "
          "failure set for every run is in the verdict table.")
'''))

cells.append(code('''MANIFEST_PATH = Path("_build/manifest_21.json")

manifest = {
    "notebook": "21-backtest-vol-matched-family.ipynb",
    "plan": "20-stability-leads-plan.md",
    "lead": "1 - the volatility-matched drop family, promoted from control to candidate",
    "verdict": VERDICT,
    "shadow_candidate": None if shadow_candidate is None else f"drop_{shadow_candidate}",
    "constraint_7": "INAPPLICABLE - the candidate set IS the observed-control family, so the "
                    "comparison is a self-comparison requiring S >= S + 0.10",
    "adoption_columns_reported": ["passes_1_to_6", "late_ok", "simple_rule_eligible"],
    "family_drops": [int(n) for n in FAMILY_DROPS],
    "family_centres": [int(n) for n in FAMILY_CENTRES],
    "boundary_members": [5, 60],
    "eligible_centres": [int(n) for n in plateau.index[plateau["simple_rule_eligible"]]],
    "qualifying_centres": [int(n) for n in qualifying],
    "plateau": {
        str(int(n)): {
            "centre_ok": bool(plateau.loc[n, "centre_ok"]),
            "lower_ok": bool(plateau.loc[n, "lower_ok"]),
            "upper_ok": bool(plateau.loc[n, "upper_ok"]),
            "plateau_ok": bool(plateau.loc[n, "plateau_ok"]),
            "simple_rule_eligible": bool(plateau.loc[n, "simple_rule_eligible"]),
            "masked_centre_ok": bool(blocking.loc[n, "masked_centre_ok"]),
            "binding_constraints": str(blocking.loc[n, "binding_constraints"]),
        }
        for n in FAMILY_CENTRES
    },
    "masked_runs": [
        {
            "label": f"drop_{row['n']}__without_top_vault",
            "n": int(row["n"]),
            "masked_vault": row["masked_vault"],
            "masked_vault_profit_usd_unmasked_run": float(row["masked_vault_profit_usd_unmasked_run"]),
            "passes_1_to_6": bool(row["passes_1_to_6"]),
            "failed": row["failed"],
            "late_ok": bool(row["late_ok"]),
        }
        for row in lovo_rows
    ],
    "runs": {
        entry["label"]: {
            "family": entry["family"],
            "overrides": {k: sorted(v) if isinstance(v, (set, frozenset)) else v
                          for k, v in entry["overrides"].items()},
            "cycle_sharpe": float(entry["panel"]["cycle_sharpe"]),
            "cagr": float(entry["panel"]["cagr"]),
            "cycle_vol": float(entry["panel"]["cycle_vol"]),
            "ulcer": float(entry["panel"]["ulcer"]),
            "abs_invested_beta": float(entry["panel"]["abs_invested_beta"]),
            "mean_invested": float(entry["panel"]["mean_invested"]),
            "late_cagr": float(entry["panel"]["late_cagr"]),
            "late_ulcer": float(entry["panel"]["late_ulcer"]),
            "passes_1_to_6": bool(passes_1_to_6(entry["panel"], anchor_panel)),
            "failed_1_to_6": failing_constraints_v3(entry["panel"], anchor_panel, None, skip_placebo=True),
            "late_ok": bool(late_period_ok_v3(entry["panel"], anchor_panel)),
        }
        for entry in runs
    },
    "baseline_parity": {metric: float(anchor_panel[metric]) for metric in BASELINE},
    "previous_plan_reference_reproduced": bool(reference_check["reproduced"].all()),
}

MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=False))
print(json.dumps(manifest, indent=1, sort_keys=False))
print(f"\\nWrote the frozen manifest for NB24 to {MANIFEST_PATH.resolve()}")
'''))

cells += integrity_and_audit_cells()

write_notebook(cells, TRACK_DIR / "21-backtest-vol-matched-family.ipynb")
