"""NB22 - complementary downside selection (lead 2, redirected).

20-stability-leads-plan.md, section "NB22 - research + backtest: complementary downside selection".

Draft 3 of the plan replaced the named-exclusion backtest with this mechanism and kept the
exclusion list's derivation as a READ-ONLY diagnostic (Part A). Nothing in this notebook is
configured from Part A's table.

`joint_loss_frequency` is a per-vault proxy for a basket-level objective: it scores each candidate
against the cohort median, not against the other five names actually chosen. Part C measures that
gap rather than assuming it; Part D characterises what the screen actually selects.
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

HEADING = """# NB22 - research + backtest: complementary downside selection (lead 2, redirected)

The equity curve is unstable because the six holdings lose on the same days. This notebook tests
the cheapest direct attack on that: rank candidates by the incumbent composite, take the top
`complementary_pool_size`, and keep the six with the lowest `joint_loss_frequency` -
`P(vault down | cohort down AND vault reported)` over a rolling window, where the cohort reference
is the cross-sectional median of FRESH vault returns. Sizing and every other rule are untouched;
the screen changes WHICH names are held, not how much of each.

Part A is the derivation half of the named-exclusion backtest this notebook replaced, kept as a
**read-only diagnostic**: who actually leaves the book between `drop_20` and `drop_30`. No run in
this notebook is configured from it.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Lead 2 of [20-stability-leads-plan.md](20-stability-leads-plan.md).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "22-backtest-joint-downside",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_STABILITY)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

# ---------------------------------------------------------------------------------------------
# Provenance and anchor parity
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Provenance and anchor parity

The content hashes below decide what this notebook can conclude. The anchor is the unchanged
`02-better-format.ipynb` configuration, run in this kernel with both stability-track
`decide_trades` splices present but disabled (`vol_matched_drop_count = 0`,
`complementary_pool_size = 0`). `assert_anchor_parity()` asserts full-precision equality against
`BASELINE` **and** that both diagnostic logs are empty afterwards, which is the evidence that
neither splice fired rather than the assumption that it did not.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
record_anchor()
'''))

# =============================================================================================
# PART A
# =============================================================================================
cells.append(md("""# Part A - who the volatility count removes (read-only diagnostic)

Draft 2 of the plan proposed freezing a named exclusion list built from the vaults that leave the
book between `vol_matched_drop_count = 20` and `= 30`. The review's objection stands - that
converts an outcome-selected volatility band into permanent identities - so the backtest was
replaced. The question underneath it is still unanswered, so the derivation survives here as a
diagnostic.

**No run in this notebook is configured from this table.** Part B's runs are the pre-registered
`complementary_pool_size` grid and nothing else; no vault is named, masked, excluded or preferred
anywhere on the basis of what follows. Part A exists to answer "who actually leaves between
N = 20 and N = 30", not to choose anything.

Both counts are read from each run's own `vol_drop_log`, written inside `decide_trades` at the
moment of the decision. An offline reconstruction could not mirror `is_good_pair`, the quarantine
list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the momentum gate or the tie order.

Three properties that are constantly confused are kept strictly apart throughout:

- **No volatility estimate** (`inv_vol == 0.0`): `inverse_vol` needs 90 observations. A vault with
  no estimate sorts to the very front of the ascending-inverse-volatility order and is therefore
  removed *first* - for having no measurement, not for being volatile.
- **Unscored by the composite** (`signal == 0.0`): the composite's CAGR leg needs
  `cagr_lookback_days` = 360 days. An unscored candidate is admitted at signal 0 (the anchor does
  not use strict admission), so a zero signal means "unscored, or scored exactly zero".
- **Young**: fewer than 360 days old at that decision date, from NB13's life cache.

The joint distribution is reported, never three margins read as if they were one.
"""))

cells.append(code('''run_and_record("drop_20", "control", vol_matched_drop_count=20)
run_and_record("drop_30", "control", vol_matched_drop_count=30)
display(pd.DataFrame([run_by_label["drop_20"]["panel"], run_by_label["drop_30"]["panel"]])
        .set_index("label")[["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta",
                             "mean_invested"]])
'''))

cells.append(code('''from pathlib import Path

LIFE_CACHE = Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet")
AGE_BARRIER_DAYS = int(Parameters.cagr_lookback_days)   # 360, the composite's own requirement
LAST_DAY = WINDOW_END - pd.Timedelta(days=1)

if LIFE_CACHE.exists():
    _life = pd.read_parquet(LIFE_CACHE)
    _life.index = _life.index.astype(str).str.lower()
    INCEPTION = _life["inception"]
    print(f"NB13 life cache: {len(INCEPTION)} vaults; age barrier {AGE_BARRIER_DAYS} days.")
else:
    INCEPTION = pd.Series(dtype="datetime64[ns]")
    print("NB13 life cache MISSING - every address will be counted as age-unmatched and reported "
          "as such, never silently dropped.")


def _log_by_timestamp(label: str) -> dict:
    return {pd.Timestamp(ts): entry for ts, entry in run_by_label[label]["vol_drop_log"].items()}


log20, log30 = _log_by_timestamp("drop_20"), _log_by_timestamp("drop_30")
SCHEDULE = pd.DatetimeIndex(sorted(pd.Timestamp(ts) for ts in anchor_equity.index))
band_dates = sorted(set(log20) & set(log30))
print(f"Decision schedule: {len(SCHEDULE)} dates, {SCHEDULE[0].date()} to {SCHEDULE[-1].date()}.")
print(f"drop_20 fired on {len(log20)} dates, drop_30 on {len(log30)}; "
      f"the marginal band is defined on the {len(band_dates)} dates where both fired.")
assert band_dates, "neither drop run logged a decision; Part A cannot be computed"
'''))

cells.append(code('''#: The marginal band M = D30 - D20 at each decision date, plus the reverse leakage D20 - D30.
#: The two runs are separate simulations, so their candidate sets are not guaranteed identical and
#: D20 is not guaranteed to be a subset of D30. Leakage is measured rather than assumed away.
band_records, band_daily = [], []
for ts in band_dates:
    d20 = set(log20[ts]["dropped_addresses"])
    d30 = set(log30[ts]["dropped_addresses"])
    marginal = d30 - d20
    leaked = d20 - d30
    no_estimate_30 = set(log30[ts]["no_estimate_dropped"])
    inv_vol_map, signal_map = log30[ts]["inv_vol"], log30[ts]["signal"]
    band_daily.append({
        "date": ts,
        "pool_size_20": int(log20[ts]["pool_size"]), "pool_size_30": int(log30[ts]["pool_size"]),
        "dropped_20": len(d20), "dropped_30": len(d30),
        "marginal_band": len(marginal), "leakage_d20_not_in_d30": len(leaked),
        "marginal_no_vol_estimate": len(marginal & no_estimate_30),
        "d30_no_vol_estimate": len(no_estimate_30),
    })
    for address in sorted(marginal):
        inv_vol = float(inv_vol_map.get(address, 0.0))
        signal = float(signal_map.get(address, 0.0))
        if address in INCEPTION.index:
            age_days = float((ts - pd.Timestamp(INCEPTION.loc[address])).days)
            age_bucket = f"young (< {AGE_BARRIER_DAYS} d)" if age_days < AGE_BARRIER_DAYS \\
                else f"old (>= {AGE_BARRIER_DAYS} d)"
        else:
            age_days, age_bucket = float("nan"), "age unmatched (not in NB13 life cache)"
        band_records.append({
            "date": ts, "address": address,
            "inv_vol": inv_vol, "signal": signal,
            "volatility_estimate": "available" if inv_vol != 0.0 else "missing (inv_vol == 0)",
            "composite": "scored" if signal != 0.0 else "signal 0 (unscored or scored zero)",
            "age_bucket": age_bucket, "age_days": age_days,
        })

band = pd.DataFrame(band_records)
band_by_date = pd.DataFrame(band_daily).set_index("date")
assert len(band), "the marginal band D30 - D20 is empty on every decision date"
print("Per-decision-date composition of the marginal band:")
display(band_by_date.describe().T)
print("First five and last five decision dates:")
display(pd.concat([band_by_date.head(5), band_by_date.tail(5)]))
'''))

cells.append(code('''#: How often each address appears in the marginal band, over the dates the band is defined on.
frequency = (band.groupby("address").size() / len(band_dates)).sort_values(ascending=False)
frequency_frame = frequency.rename("share_of_dates").to_frame()
frequency_frame["dates_in_band"] = band.groupby("address").size()
frequency_frame["in_life_cache"] = [a in INCEPTION.index for a in frequency_frame.index]
print(f"Distinct addresses that ever entered the marginal band: {len(frequency_frame)} "
      f"over {len(band_dates)} decision dates.")
display(frequency_frame.head(25))

CORE_THRESHOLDS = (0.50, 0.75, 0.90)
core_rows = []
for threshold in CORE_THRESHOLDS:
    members = sorted(frequency.index[frequency >= threshold])
    core_rows.append({
        "threshold": f">= {threshold:.0%} of dates", "vaults": len(members),
        "addresses": ", ".join(members) if members else "(none)",
    })
persistent_core = pd.DataFrame(core_rows).set_index("threshold")
print("The persistent core of the marginal band:")
display(persistent_core)
'''))

cells.append(code('''#: Monthly membership stability: the union of the band each calendar month, and the Jaccard
#: overlap with the previous month. Two empty months are undefined and reported as missing.
band["month"] = band["date"].dt.to_period("M")
monthly_sets = band.groupby("month")["address"].agg(lambda s: set(s))
monthly_rows, previous = [], None
for month, members in monthly_sets.items():
    if previous is None:
        overlap = float("nan")
    elif not members and not previous:
        overlap = float("nan")
    elif not members or not previous:
        overlap = 0.0
    else:
        overlap = len(members & previous) / len(members | previous)
    monthly_rows.append({
        "month": str(month), "band_members": len(members),
        "dates_in_month": int(band[band["month"] == month]["date"].nunique()),
        "jaccard_vs_previous_month": overlap,
        "new_this_month": float("nan") if previous is None else len(members - previous),
        "left_this_month": float("nan") if previous is None else len(previous - members),
    })
    previous = members
monthly = pd.DataFrame(monthly_rows).set_index("month")
print("Monthly membership stability of the marginal band. Descriptive only - not a stopping rule.")
display(monthly)
'''))

cells.append(code('''#: The top 15 by frequency, cross-tabbed by age at that date and by whether the composite scored
#: them. These are (address, date) records, so a vault crossing the 360-day barrier mid-window
#: contributes to both age rows - which is the point of tabulating age AT THAT DATE.
TOP_K = 15
top_addresses = list(frequency.head(TOP_K).index)
top_band = band[band["address"].isin(top_addresses)]

print(f"Top {TOP_K} addresses by marginal-band frequency: per-address summary.")
top_summary = pd.DataFrame({
    "share_of_dates": frequency.loc[top_addresses],
    "dates_in_band": band[band["address"].isin(top_addresses)].groupby("address").size(),
    "first_date": top_band.groupby("address")["date"].min(),
    "last_date": top_band.groupby("address")["date"].max(),
    "mean_inv_vol": top_band.groupby("address")["inv_vol"].mean(),
    "no_vol_estimate_share": top_band.groupby("address")["volatility_estimate"].apply(
        lambda s: float((s != "available").mean())),
    "scored_share": top_band.groupby("address")["composite"].apply(
        lambda s: float((s == "scored").mean())),
    "in_life_cache": pd.Series({a: a in INCEPTION.index for a in top_addresses}),
    "age_days_at_first": top_band.groupby("address")["age_days"].first(),
    "age_days_at_last": top_band.groupby("address")["age_days"].last(),
}).loc[top_addresses]
display(top_summary)

print("Cross-tab of the top 15's band records: age at that date x composite availability.")
top_crosstab = pd.crosstab(top_band["age_bucket"], top_band["composite"])
display(top_crosstab)
print("The same, with the volatility-estimate axis as well (the three properties jointly):")
display(top_band.groupby(["volatility_estimate", "composite", "age_bucket"]).size()
        .rename("records").to_frame()
        .assign(share=lambda f: f["records"] / f["records"].sum()))

unmatched_addresses = sorted(set(band["address"]) - set(INCEPTION.index))
unmatched_records = int((band["age_bucket"].str.startswith("age unmatched")).sum())
print(f"Marginal-band addresses not in the NB13 life cache: {len(unmatched_addresses)} of "
      f"{band['address'].nunique()} distinct addresses, {unmatched_records} of {len(band)} records "
      f"({unmatched_records / len(band):.2%}). Counted and reported, never dropped.")
print(f"Of the top {TOP_K}: {sum(1 for a in top_addresses if a not in INCEPTION.index)} unmatched.")
'''))

cells.append(code('''#: How much of the marginal band is "no volatility estimate at all" rather than "volatile".
#: This is the single most misread number in the whole drop family, so it is reported per date,
#: pooled, and at the first decision specifically.
no_estimate_records = int((band["volatility_estimate"] != "available").sum())
first_date = band_dates[0]
first_row = band_by_date.loc[first_date]
print(f"Marginal-band records with NO volatility estimate: {no_estimate_records} of {len(band)} "
      f"({no_estimate_records / len(band):.2%}).")
print(f"Distinct addresses that were ever in the band with no estimate: "
      f"{band[band['volatility_estimate'] != 'available']['address'].nunique()} of "
      f"{band['address'].nunique()}.")
print(f"At the first decision ({first_date.date()}): drop_30 removed {int(first_row['dropped_30'])} "
      f"vaults of which {int(first_row['d30_no_vol_estimate'])} had no volatility estimate; the "
      f"marginal band was {int(first_row['marginal_band'])} of which "
      f"{int(first_row['marginal_no_vol_estimate'])} had none.")
print("Per-date share of the marginal band with no volatility estimate:")
display((band_by_date["marginal_no_vol_estimate"] / band_by_date["marginal_band"].replace(0, np.nan))
        .describe().to_frame("share_of_marginal_band_with_no_vol_estimate"))
print("'No volatility estimate' (needs 90 observations), 'unscored by the composite' (needs 360 "
      "days) and 'young' are THREE DIFFERENT properties. The joint table above is the answer; the "
      "three margins are not interchangeable.")
'''))

cells.append(code('''#: Did the marginal band ever displace a FUNDED anchor position? A position counts as funded only
#: if it has at least one successful buy; the overlap is between the dates the address sat in the
#: band and the dates the anchor actually held it.
anchor_position_rows = []
for position in anchor_state.portfolio.get_all_positions():
    if position.is_credit_supply():
        continue
    buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
    if not buys:
        continue
    anchor_position_rows.append({
        "address": str(position.pair.pool_address).lower(),
        "opened_at": pd.Timestamp(position.opened_at),
        "closed_at": pd.Timestamp(position.closed_at) if position.closed_at else LAST_DAY + pd.Timedelta(days=1),
        "entry_capital_usd": float(sum(t.get_value() for t in buys)),
        "pnl_usd": float(position.get_total_profit_usd() or 0.0),
    })
anchor_positions = pd.DataFrame(anchor_position_rows)
print(f"Anchor funded positions: {len(anchor_positions)} across "
      f"{anchor_positions['address'].nunique()} distinct vaults.")

displacement_rows = []
for address in top_addresses:
    dates_in_band = set(band[band["address"] == address]["date"])
    held = anchor_positions[anchor_positions["address"] == address]
    overlap = 0
    for ts in dates_in_band:
        if len(held) and bool(((held["opened_at"] <= ts) & (ts < held["closed_at"])).any()):
            overlap += 1
    displacement_rows.append({
        "address": address,
        "share_of_dates_in_band": float(frequency.loc[address]),
        "anchor_funded_positions": int(len(held)),
        "anchor_entry_capital_usd": float(held["entry_capital_usd"].sum()) if len(held) else 0.0,
        "anchor_pnl_usd": float(held["pnl_usd"].sum()) if len(held) else 0.0,
        "band_dates_while_anchor_held_it": overlap,
        "ever_displaced_a_funded_anchor_position": bool(overlap > 0),
    })
displacement = pd.DataFrame(displacement_rows).set_index("address")
display(displacement)
print(f"Of the top {TOP_K} marginal-band vaults, "
      f"{int(displacement['ever_displaced_a_funded_anchor_position'].sum())} ever displaced a "
      f"funded anchor position; "
      f"{int((displacement['anchor_funded_positions'] > 0).sum())} were ever funded by the anchor "
      f"at any time.")
print("PART A IS READ-ONLY. No run below is configured from any of these tables, and no vault is "
      "named, masked, preferred or excluded anywhere in this notebook on the basis of them.")
'''))

# =============================================================================================
# PART B
# =============================================================================================
cells.append(md("""# Part B - the plateau over `complementary_pool_size`

`complementary_pool_size = P` takes the top P candidates by the incumbent composite and keeps the
`max_assets_in_portfolio` (6) with the lowest `joint_loss_frequency`. NaN sorts last: no estimate
is not evidence of complementarity. Sizing, the momentum gate, the quarantine list, the deposit
window and the minimum hold are all untouched.

P = 18 is the pre-registered centre; {10, 12, 14, 16, 20, 24} is the pre-registered plateau. Then
window sensitivity at the centre: `joint_loss_window_days` in {90, 270} and `joint_loss_min_events`
in {5, 20}. The volatility-matched family is the constraint-7 comparator (the best observed
control at or below the candidate's own volatility, plus a 0.10 Sharpe complexity premium). That
asymmetry is deliberate: a co-movement screen is an additional mechanism and has to beat the best
simple de-risking that took no more risk than it did.
"""))

cells.append(code('''COMPLEMENTARY_CENTRE = 18
COMPLEMENTARY_GRID = (10, 12, 14, 16, 18, 20, 24)
for p in COMPLEMENTARY_GRID:
    run_and_record(f"complementary_{p}", "candidate", complementary_pool_size=p)
print(f"{len(COMPLEMENTARY_GRID)} pool-size runs recorded.")
'''))

cells.append(code('''WINDOW_SENSITIVITY = {
    "complementary_18__window_90": dict(complementary_pool_size=18, joint_loss_window_days=90),
    "complementary_18__window_270": dict(complementary_pool_size=18, joint_loss_window_days=270),
    "complementary_18__min_events_5": dict(complementary_pool_size=18, joint_loss_min_events=5),
    "complementary_18__min_events_20": dict(complementary_pool_size=18, joint_loss_min_events=20),
}
for label, overrides in WINDOW_SENSITIVITY.items():
    run_and_record(label, "candidate", **overrides)
print(f"{len(WINDOW_SENSITIVITY)} window-sensitivity runs recorded.")
'''))

cells.append(code('''family = build_family()
display(family[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer", "abs_invested_beta",
                "mean_invested"]])
'''))

cells.append(md("""## Reference values on this snapshot

The three previous-plan reference values and the `complementary_18` smoke-test value. These are a
sanity check on the data snapshot, not an adoption gate, so they are displayed rather than
asserted - but if any of them fails to reproduce, nothing below is comparable with the rest of the
track and the notebook's conclusions do not stand.
"""))
cells.append(code('''REFERENCE_VALUES = {
    "anchor": (0.378971, 2.159792),
    "drop_30": (0.489942, 2.747391),
    "drop_50": (0.206149, 2.014857),
    "complementary_18": (-0.177391, -1.176589),
}
reference_rows = []
for label, (expected_cagr, expected_sharpe) in REFERENCE_VALUES.items():
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
REFERENCES_REPRODUCED = bool(reference_check["reproduced"].all())
print(f"Every reference value reproduced: {REFERENCES_REPRODUCED}")
'''))

cells.append(md("""## Verdict table

Adoption rule v3: CAGR >= 20%; cycle Sharpe >= anchor - 0.10; cycle volatility <= anchor; ulcer
<= 0.85 x anchor; invested-basket beta < anchor; mean invested >= 0.90; and constraint 7, cycle
Sharpe >= the best observed control at or below this row's volatility, plus 0.10.

The `failed` column carries the COMPLETE failure set for every row and is never truncated
(`harness_evidence.py` sets `display.max_colwidth = None`). A row failing five constraints is
never summarised as failing one.
"""))
cells.append(code('''VERDICT_COLUMNS = [
    "family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
    "late_cagr", "late_ulcer", "cagr_sacrifice_pp", "control_ref", "passes_v3", "failed", "late_ok",
]
verdict = verdict_table_v3(family=family)
print("Every recorded run, sorted by cycle Sharpe:")
display(verdict[VERDICT_COLUMNS])

candidate_order = ["anchor"] + [f"complementary_{p}" for p in COMPLEMENTARY_GRID] + list(WINDOW_SENSITIVITY)
print("The candidates in pre-registered order:")
display(verdict.loc[candidate_order, VERDICT_COLUMNS])

print("Complete failure set of the pre-registered centre complementary_18:")
print(f"  {failing_constraints_v3(run_by_label['complementary_18']['panel'], anchor_panel, family) or '(none)'}")
'''))

cells.append(md("""## Plateau

A result that exists only at one setting of a dial is a coincidence, not a mechanism. Every
neighbour is a separate Boolean, and a run that is absent is False, never True.
"""))
cells.append(code('''def row_ok(label: str) -> bool:
    """Adoption rule v3 plus the late period for one recorded run. Missing run -> False."""
    entry = run_by_label.get(label)
    if entry is None:
        return False
    row = entry["panel"]
    return bool(passes_constraints_v3(row, anchor_panel, family)
                and late_period_ok_v3(row, anchor_panel))


plateau_flags = {}
plateau_rows = []
for p in COMPLEMENTARY_GRID:
    label = f"complementary_{p}"
    entry = run_by_label[label]
    ok = row_ok(label)
    plateau_flags[label] = ok
    plateau_rows.append({
        "p": p, "label": label, "role": "centre" if p == COMPLEMENTARY_CENTRE else "neighbour",
        "run_present": label in run_by_label,
        "passes_v3": bool(passes_constraints_v3(entry["panel"], anchor_panel, family)),
        "late_ok": bool(late_period_ok_v3(entry["panel"], anchor_panel)),
        "neighbour_ok": ok,
        "failed": failing_constraints_v3(entry["panel"], anchor_panel, family),
    })
plateau = pd.DataFrame(plateau_rows).set_index("p")
CENTRE_LABEL = f"complementary_{COMPLEMENTARY_CENTRE}"
CENTRE_OK = plateau_flags[CENTRE_LABEL]
NEIGHBOURS_OK = bool(all(v for k, v in plateau_flags.items() if k != CENTRE_LABEL))
PLATEAU_OK = bool(CENTRE_OK and NEIGHBOURS_OK)
display(plateau)
print(f"centre_ok (P = {COMPLEMENTARY_CENTRE}): {CENTRE_OK}")
for p in COMPLEMENTARY_GRID:
    if p != COMPLEMENTARY_CENTRE:
        print(f"  neighbour_ok P = {p}: {plateau_flags[f'complementary_{p}']}")
print(f"plateau_ok (centre and every neighbour): {PLATEAU_OK}")
'''))

cells.append(md("""## Window sensitivity at the centre

Reported beside the plateau, per the plan. These four runs are not part of the pre-registered
plateau gate; they say whether the centre's result is a property of the mechanism or of the
particular rolling window and event minimum chosen for it.
"""))
cells.append(code('''window_rows = []
for label, overrides in WINDOW_SENSITIVITY.items():
    entry = run_by_label[label]
    row = entry["panel"]
    window_rows.append({
        "label": label, "overrides": str(overrides),
        "cagr": float(row["cagr"]), "cycle_sharpe": float(row["cycle_sharpe"]),
        "cycle_vol": float(row["cycle_vol"]), "ulcer": float(row["ulcer"]),
        "abs_invested_beta": float(row["abs_invested_beta"]),
        "mean_invested": float(row["mean_invested"]),
        "passes_v3": bool(passes_constraints_v3(row, anchor_panel, family)),
        "late_ok": bool(late_period_ok_v3(row, anchor_panel)),
        "failed": failing_constraints_v3(row, anchor_panel, family),
    })
window_sensitivity = pd.DataFrame(window_rows).set_index("label")
display(window_sensitivity)
WINDOW_OK = bool((window_sensitivity["passes_v3"] & window_sensitivity["late_ok"]).all())
print(f"window_sensitivity_ok (all four): {WINDOW_OK}")
'''))

cells.append(md("""## Leave-one-vault-out

Run ONLY if the centre and every plateau neighbour pass. A robustness run that was never executed
cannot produce a passing flag, so an unrun leave-one-vault-out is recorded as absent and treated
as a fail by the verdict cell.
"""))
cells.append(code('''LOVO_LABEL = f"{CENTRE_LABEL}__without_top_vault"
LOVO_OK, LOVO_MASKED_VAULT = False, None
if not PLATEAU_OK:
    print("The centre and/or a plateau neighbour failed, so leave-one-vault-out is NOT executed. "
          "It is recorded as ABSENT, which the verdict cell treats as a fail - an unexecuted "
          "robustness run can never produce a passing flag.")
else:
    LOVO_MASKED_VAULT = largest_contributing_vault(run_by_label[CENTRE_LABEL]["state"])
    lovo_entry = run_and_record(
        LOVO_LABEL, "robustness",
        complementary_pool_size=COMPLEMENTARY_CENTRE, masked={LOVO_MASKED_VAULT},
    )
    LOVO_OK = row_ok(LOVO_LABEL)
    display(pd.DataFrame([{
        "label": LOVO_LABEL, "masked_vault": LOVO_MASKED_VAULT,
        "cagr": float(lovo_entry["panel"]["cagr"]),
        "cycle_sharpe": float(lovo_entry["panel"]["cycle_sharpe"]),
        "passes_v3": bool(passes_constraints_v3(lovo_entry["panel"], anchor_panel, family)),
        "late_ok": bool(late_period_ok_v3(lovo_entry["panel"], anchor_panel)),
        "failed": failing_constraints_v3(lovo_entry["panel"], anchor_panel, family),
    }]).set_index("label"))
    print(f"leave_one_vault_out_ok: {LOVO_OK}")
'''))

cells.append(md("""## Bootstrap margins at the centre

Paired block-bootstrap intervals of the cycle-Sharpe difference, common block indices across the
aligned return matrix so each draw compares both strategies on the same market days. Against the
anchor the boundary is **-0.10**; against the observed control actually used by constraint 7 it is
**+0.10**. Block lengths 5, 10 and 20.
"""))
cells.append(code('''display(bootstrap_margin_table(CENTRE_LABEL, family))
'''))

# =============================================================================================
# PART C
# =============================================================================================
cells.append(md("""# Part C - the gap between the proxy and the objective

`joint_loss_frequency` scores each candidate against the cohort median, not against the other
five names actually chosen, so it cannot see two vaults that are each complementary to the cohort
but identical to each other. That gap is measured here, not assumed.

The **pairwise** joint-loss frequency of a pair of vaults is computed directly from the mark
series: over the trailing `joint_loss_window_days` ending at the decision date, restricted to days
on which BOTH vaults posted a fresh mark, the share on which both were down. A basket's
concentration is the mean over its 15 pairs. High means the basket sinks together, which is
exactly the property the mechanism claims to attack.

If the within-basket concentration is no better than the anchor's, the proxy failed even where a
constraint table might have passed.
"""))

cells.append(code('''#: Daily mark matrix straight from the Hyperliquid poll archive, cached under a fingerprint of the
#: archive's size and modification time so a re-download invalidates it. Marks are resampled to one
#: observation per calendar day (last poll), reindexed onto a common calendar from the vault's own
#: first poll and forward-filled; NaN before a vault's first poll. A zero daily return is a stale
#: mark - the strategy cannot tell "polled and unchanged" from "not polled", and neither can this.
raw_price_path = Path("~/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet").expanduser()
_archive = raw_price_path.stat()
MARK_CACHE = Path(f"/tmp/hyperliquid-lower-vol-nb22-marks-{_archive.st_size}-"
                  f"{int(_archive.st_mtime)}-{Parameters.backtest_end:%Y%m%d}.parquet")
TVL_CACHE = Path(str(MARK_CACHE).replace("-marks-", "-tvl-"))

CALENDAR_START = WINDOW_START - pd.Timedelta(days=400)
CALENDAR = pd.date_range(CALENDAR_START, LAST_DAY, freq="1D")

if MARK_CACHE.exists() and TVL_CACHE.exists():
    MARKS = pd.read_parquet(MARK_CACHE)
    TVL = pd.read_parquet(TVL_CACHE)
    print(f"Loaded the NB22 mark matrix from {MARK_CACHE.name}")
else:
    polls = pd.read_parquet(
        raw_price_path,
        columns=["chain", "address", "share_price", "total_assets"],
        filters=[("chain", "==", ChainId.hypercore.value)],
    )
    polls["address"] = polls["address"].astype(str).str.lower()
    polls = polls[polls.index < Parameters.backtest_end]
    price_columns, tvl_columns = {}, {}
    for address, group in polls.groupby("address", sort=False):
        prices = group["share_price"].astype(float)
        prices = prices[prices > 0].dropna()
        if len(prices) < 5:
            continue
        daily = prices.resample("1D").last()
        if daily.index[-1] < CALENDAR_START:
            continue
        price_columns[address] = daily.reindex(daily.index.union(CALENDAR)).ffill().reindex(CALENDAR)
        assets = group["total_assets"].astype(float).dropna()
        if len(assets):
            assets_daily = assets.resample("1D").last()
            tvl_columns[address] = assets_daily.reindex(
                assets_daily.index.union(CALENDAR)).ffill().reindex(CALENDAR)
    MARKS = pd.DataFrame(price_columns).sort_index(axis=1)
    TVL = pd.DataFrame(tvl_columns).reindex(columns=MARKS.columns)
    MARKS.to_parquet(MARK_CACHE)
    TVL.to_parquet(TVL_CACHE)
    print(f"Built the NB22 mark matrix: {MARKS.shape[1]} vaults x {MARKS.shape[0]} calendar days.")

#: The mark matrix is on a midnight calendar; a decision timestamp is normalised to its calendar
#: day before any lookup, so an intra-day cycle clock can never raise a KeyError or silently shift.
def mark_day(ts) -> pd.Timestamp:
    return pd.Timestamp(ts).normalize()


RET = MARKS.pct_change()
FRESH = (RET.notna() & (RET != 0.0))
OBSERVED = RET.notna()
DOWN = (RET < 0.0)
JOINT_WINDOW = int(Parameters.joint_loss_window_days)
FRESH_ROLL = FRESH.astype(float).rolling(JOINT_WINDOW, min_periods=1).sum()
OBSERVED_ROLL = OBSERVED.astype(float).rolling(JOINT_WINDOW, min_periods=1).sum()
STALE_SHARE_ROLL = 1.0 - FRESH_ROLL / OBSERVED_ROLL.replace(0.0, np.nan)
print(f"Mark matrix: {MARKS.shape[1]} vaults, {MARKS.index[0].date()} to {MARKS.index[-1].date()}; "
      f"trailing window {JOINT_WINDOW} days.")
_missing_days = [ts for ts in SCHEDULE if mark_day(ts) not in MARKS.index]
assert not _missing_days, f"{len(_missing_days)} decision dates are not on the mark calendar"
print(f"Every one of the {len(SCHEDULE)} decision dates is on the mark calendar.")
'''))

cells.append(code('''MARK_COLUMNS = set(MARKS.columns)
PAIR_MIN_EVENTS = int(Parameters.joint_loss_min_events)


def pairwise_joint_loss(addresses, end_ts, window_days: int = JOINT_WINDOW,
                        min_events: int = PAIR_MIN_EVENTS) -> dict:
    """Mean pairwise `P(both down | both reported)` inside one basket at one decision date.

    Restricted to days on which BOTH vaults posted a fresh mark, for the same reason the per-vault
    indicator restricts its denominator: a vault that simply stopped reporting would otherwise
    register as never losing with anybody.
    """
    usable = [a for a in addresses if a in MARK_COLUMNS]
    end_day = mark_day(end_ts)
    start = end_day - pd.Timedelta(days=window_days)
    window = RET.loc[(RET.index > start) & (RET.index <= end_day), usable] if usable else None
    total_pairs = len(usable) * (len(usable) - 1) // 2
    if window is None or total_pairs == 0:
        return {"mean_pairwise_joint_loss": float("nan"), "pairs_defined": 0,
                "pairs_total": total_pairs, "addresses_missing": len(addresses) - len(usable)}
    reported = window.notna() & (window != 0.0)
    down = window < 0.0
    values, benchmarks = [], []
    for i, a in enumerate(usable):
        for b in usable[i + 1:]:
            both = reported[a] & reported[b]
            n = int(both.sum())
            if n < min_events:
                continue
            values.append(float((down[a] & down[b] & both).sum()) / n)
            # Independence benchmark on EXACTLY the same conditioning set, so the level of the
            # co-loss statistic can be split into "these names lose less often" and "these names
            # lose together less often". Both marginals are measured over the same both-fresh
            # days as the joint count, so `observed - p_a * p_b` is the sample covariance of the
            # two down indicators over that set - the part that is genuinely co-movement.
            p_a = float((down[a] & both).sum()) / n
            p_b = float((down[b] & both).sum()) / n
            benchmarks.append(p_a * p_b)
    return {
        "mean_pairwise_joint_loss": float(np.mean(values)) if values else float("nan"),
        "mean_pairwise_independent": float(np.mean(benchmarks)) if benchmarks else float("nan"),
        "mean_pairwise_excess": float(np.mean(values) - np.mean(benchmarks)) if values else float("nan"),
        "pairs_defined": len(values), "pairs_total": total_pairs,
        "addresses_missing": len(addresses) - len(usable),
    }


def funded_positions(state_) -> pd.DataFrame:
    rows = []
    for position in state_.portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
        if not buys:
            continue
        rows.append({
            "address": str(position.pair.pool_address).lower(),
            "opened_at": pd.Timestamp(position.opened_at),
            "closed_at": pd.Timestamp(position.closed_at) if position.closed_at
                         else LAST_DAY + pd.Timedelta(days=1),
        })
    return pd.DataFrame(rows)


def holdings_at(position_frame: pd.DataFrame, ts) -> list:
    if not len(position_frame):
        return []
    open_now = position_frame[(position_frame["opened_at"] <= ts) & (ts < position_frame["closed_at"])]
    return sorted(set(open_now["address"]))


anchor_funded = funded_positions(anchor_state)
centre_funded = funded_positions(run_by_label[CENTRE_LABEL]["state"])
print(f"Funded positions - anchor: {len(anchor_funded)}, {CENTRE_LABEL}: {len(centre_funded)}.")
'''))

cells.append(code('''#: Realised within-basket concentration: the baskets actually HELD at each decision date, for the
#: centre and for the anchor. This is the objective the mechanism claims to move.
concentration_rows = []
for ts in SCHEDULE:
    for label, frame in (("anchor", anchor_funded), (CENTRE_LABEL, centre_funded)):
        held = holdings_at(frame, ts)
        result = pairwise_joint_loss(held, ts)
        concentration_rows.append({
            "date": ts, "run": label, "holdings": len(held), **result,
        })
concentration = pd.DataFrame(concentration_rows)
concentration_summary = concentration.groupby("run").agg(
    decision_dates=("date", "nunique"),
    mean_holdings=("holdings", "mean"),
    mean_pairwise_joint_loss=("mean_pairwise_joint_loss", "mean"),
    median_pairwise_joint_loss=("mean_pairwise_joint_loss", "median"),
    mean_pairwise_independent=("mean_pairwise_independent", "mean"),
    mean_pairwise_excess=("mean_pairwise_excess", "mean"),
    dates_with_an_estimate=("mean_pairwise_joint_loss", lambda s: int(s.notna().sum())),
    mean_pairs_defined=("pairs_defined", "mean"),
    mean_pairs_total=("pairs_total", "mean"),
)
print("Within-basket pairwise joint-loss concentration of the REALISED holdings.")
print("`mean_pairwise_independent` is the product of the two marginal down rates measured over "
      "the SAME both-fresh days; `mean_pairwise_excess` is the co-loss LEVEL minus that "
      "benchmark, i.e. the part that is co-movement rather than each name simply losing less "
      "often. A screen that only lowers the marginal loss rate lowers the level and leaves the "
      "excess alone.")
display(concentration_summary)

anchor_conc = float(concentration_summary.loc["anchor", "mean_pairwise_joint_loss"])
centre_conc = float(concentration_summary.loc[CENTRE_LABEL, "mean_pairwise_joint_loss"])
assert np.isfinite(anchor_conc) and np.isfinite(centre_conc), \\
    "within-basket concentration is not finite for one of the two runs; failing closed"
CONCENTRATION_FALLS = bool(centre_conc < anchor_conc)
print(f"Anchor {anchor_conc:.6f} against {CENTRE_LABEL} {centre_conc:.6f}; "
      f"difference {centre_conc - anchor_conc:+.6f}.")
print(f"within_basket_concentration_falls: {CONCENTRATION_FALLS}")

#: Paired per-date difference, so the comparison is on the same market days.
paired = concentration.pivot(index="date", columns="run", values="mean_pairwise_joint_loss").dropna()
paired_difference = paired[CENTRE_LABEL] - paired["anchor"]
ci_lo, ci_hi = block_bootstrap_ci(paired_difference, block=10)
print(f"Paired per-date difference in the co-loss LEVEL over {len(paired_difference)} dates: "
      f"mean {paired_difference.mean():+.6f}, 95% block-bootstrap CI "
      f"[{ci_lo:+.6f}, {ci_hi:+.6f}] (block 10).")

#: The same paired test on the EXCESS over independence. This is the one that answers the
#: mechanism's actual claim - "the six holdings lose on the same days" is a statement about
#: dependence, not about how often each of them loses.
paired_excess = concentration.pivot(index="date", columns="run", values="mean_pairwise_excess").dropna()
excess_difference = paired_excess[CENTRE_LABEL] - paired_excess["anchor"]
ci_lo_excess, ci_hi_excess = block_bootstrap_ci(excess_difference, block=10)
anchor_excess = float(concentration_summary.loc["anchor", "mean_pairwise_excess"])
centre_excess = float(concentration_summary.loc[CENTRE_LABEL, "mean_pairwise_excess"])
print(f"Excess over the independence benchmark - anchor {anchor_excess:+.6f}, {CENTRE_LABEL} "
      f"{centre_excess:+.6f}.")
print(f"Paired per-date difference in the EXCESS over {len(excess_difference)} dates: "
      f"mean {excess_difference.mean():+.6f}, 95% block-bootstrap CI "
      f"[{ci_lo_excess:+.6f}, {ci_hi_excess:+.6f}] (block 10).")
EXCESS_FALLS = bool(centre_excess < anchor_excess)
print(f"within_basket_EXCESS_falls (dependence, not level): {EXCESS_FALLS}. The pre-registered "
      f"gate is the LEVEL and is unchanged; this is reported beside it, not substituted for it.")
'''))

cells.append(code('''#: The same measure on the screen's OWN decision, from complement_log: the six it kept against the
#: six the incumbent composite would have held out of the same pool. This isolates the screen from
#: every downstream effect (deposit window, minimum hold, path dependence).
centre_log = {pd.Timestamp(ts): entry
              for ts, entry in run_by_label[CENTRE_LABEL]["complement_log"].items()}
print(f"complement_log covers {len(centre_log)} decision dates of {len(SCHEDULE)} on the schedule.")

log_rows = []
for ts, entry in sorted(centre_log.items()):
    kept, incumbent = list(entry["kept"]), list(entry["incumbent_top"])
    kept_result = pairwise_joint_loss(kept, ts)
    incumbent_result = pairwise_joint_loss(incumbent, ts)
    log_rows.append({
        "date": ts,
        "pool_size": int(entry["pool_size"]),
        "screened_pool": len(entry["screened_pool"]),
        "missing_estimates": int(entry["missing_estimates"]),
        "basket_changed": bool(set(kept) != set(incumbent)),
        "overlap_with_incumbent_top": len(set(kept) & set(incumbent)),
        "kept_pairwise_joint_loss": kept_result["mean_pairwise_joint_loss"],
        "incumbent_pairwise_joint_loss": incumbent_result["mean_pairwise_joint_loss"],
        "kept_pairwise_excess": kept_result["mean_pairwise_excess"],
        "incumbent_pairwise_excess": incumbent_result["mean_pairwise_excess"],
    })
screen = pd.DataFrame(log_rows).set_index("date")
display(screen.describe().T)

CHANGED_SHARE = float(screen["basket_changed"].mean())
POOL_READS = int(screen["screened_pool"].sum())
MISSING_READS = int(screen["missing_estimates"].sum())
KEPT_CONC = float(screen["kept_pairwise_joint_loss"].mean())
INCUMBENT_CONC = float(screen["incumbent_pairwise_joint_loss"].mean())
print(f"Share of decision dates on which the screen changed the basket: {CHANGED_SHARE:.2%} "
      f"({int(screen['basket_changed'].sum())} of {len(screen)}).")
print(f"Mean overlap between the kept six and the incumbent top six: "
      f"{screen['overlap_with_incumbent_top'].mean():.2f} of 6.")
print(f"Pool reads with no joint-loss estimate: {MISSING_READS} of {POOL_READS} "
      f"({MISSING_READS / POOL_READS:.2%}).")
print(f"Mean within-basket pairwise joint loss - kept {KEPT_CONC:.6f}, "
      f"incumbent top six {INCUMBENT_CONC:.6f}, difference {KEPT_CONC - INCUMBENT_CONC:+.6f}.")
KEPT_EXCESS = float(screen["kept_pairwise_excess"].mean())
INCUMBENT_EXCESS = float(screen["incumbent_pairwise_excess"].mean())
print(f"Mean EXCESS over the independence benchmark - kept {KEPT_EXCESS:+.6f}, incumbent top six "
      f"{INCUMBENT_EXCESS:+.6f}, difference {KEPT_EXCESS - INCUMBENT_EXCESS:+.6f}. The level and "
      f"the excess do not have to move together, and which of them moved is what decides whether "
      f"the screen reduced co-movement or only the rate at which the names it holds lose.")
'''))

cells.append(code('''#: The realised objective: how often four or more of the six holdings lost together over a cycle.
#: Cycle returns are taken from the mark matrix between consecutive decision dates, so a holding
#: whose mark did not move counts as neither a winner nor a loser and is reported separately.
coloss_rows = []
for label, frame in (("anchor", anchor_funded), (CENTRE_LABEL, centre_funded)):
    for start_ts, end_ts in zip(SCHEDULE, SCHEDULE[1:]):
        held = [a for a in holdings_at(frame, start_ts) if a in MARK_COLUMNS]
        if not held:
            coloss_rows.append({"run": label, "date": start_ts, "holdings": 0, "priced": 0,
                                "losers": 0, "unmoved": 0, "four_or_more_losers": False})
            continue
        begin = MARKS.loc[mark_day(start_ts), held]
        finish = MARKS.loc[mark_day(end_ts), held]
        change = (finish / begin - 1.0).dropna()
        coloss_rows.append({
            "run": label, "date": start_ts, "holdings": len(held), "priced": int(len(change)),
            "losers": int((change < 0).sum()), "unmoved": int((change == 0).sum()),
            "four_or_more_losers": bool(int((change < 0).sum()) >= 4),
        })
coloss = pd.DataFrame(coloss_rows)
coloss_summary = coloss.groupby("run").agg(
    cycles=("date", "nunique"),
    mean_holdings=("holdings", "mean"),
    mean_priced=("priced", "mean"),
    mean_losers=("losers", "mean"),
    mean_unmoved=("unmoved", "mean"),
    share_of_cycles_with_4plus_losers=("four_or_more_losers", "mean"),
)
print("Realised co-loss: cycles in which four or more of the CURRENTLY HELD names lost together.")
print("Not 'four of six': the centre does not always hold six. The denominator of this flag is "
      "whatever the run held that cycle, so a cycle with five holdings needs four of five and is "
      "mechanically less likely to trip the flag than a cycle with six. The unrestricted numbers "
      "below are therefore confounded with basket size and the restricted ones beside them are "
      "the comparable pair.")
display(coloss_summary)
COLOSS_ANCHOR = float(coloss_summary.loc["anchor", "share_of_cycles_with_4plus_losers"])
COLOSS_CENTRE = float(coloss_summary.loc[CENTRE_LABEL, "share_of_cycles_with_4plus_losers"])
print(f"Unrestricted, four or more of however many were held: anchor {COLOSS_ANCHOR:.2%} of "
      f"cycles against {CENTRE_LABEL} {COLOSS_CENTRE:.2%}.")

#: The size-controlled version: only cycles on which BOTH runs priced exactly six holdings, so
#: "four of six" means the same thing on both sides. Restricting on the centre's basket size is
#: itself a selection on the centre's cycles and is reported as such rather than presented as the
#: unconditional number.
priced_by_run = coloss.pivot(index="date", columns="run", values="priced")
six_both = priced_by_run.index[(priced_by_run["anchor"] == 6) & (priced_by_run[CENTRE_LABEL] == 6)]
flag_by_run = coloss.pivot(index="date", columns="run", values="four_or_more_losers")
losers_by_run = coloss.pivot(index="date", columns="run", values="losers")
COLOSS_SIX_CYCLES = int(len(six_both))
if COLOSS_SIX_CYCLES:
    COLOSS_ANCHOR_SIX = float(flag_by_run.loc[six_both, "anchor"].mean())
    COLOSS_CENTRE_SIX = float(flag_by_run.loc[six_both, CENTRE_LABEL].mean())
else:
    COLOSS_ANCHOR_SIX = COLOSS_CENTRE_SIX = float("nan")
print(f"Restricted to the {COLOSS_SIX_CYCLES} of {len(flag_by_run)} cycles on which BOTH runs "
      f"priced six holdings: anchor {COLOSS_ANCHOR_SIX:.2%} against {CENTRE_LABEL} "
      f"{COLOSS_CENTRE_SIX:.2%}.")

#: The per-name loss rate underneath both of those, which is what a four-of-six count is mostly
#: driven by. If this is what fell, the co-loss flag fell because each holding lost less often,
#: not because the holdings stopped losing together.
loss_rate_rows = []
for label in ("anchor", CENTRE_LABEL):
    sub = coloss[(coloss["run"] == label) & (coloss["priced"] > 0)]
    loss_rate_rows.append({
        "run": label,
        "per_name_loss_rate_all_cycles": float(sub["losers"].sum() / sub["priced"].sum()),
        "per_name_loss_rate_six_name_cycles": float(
            losers_by_run.loc[six_both, label].sum() / (6 * COLOSS_SIX_CYCLES))
            if COLOSS_SIX_CYCLES else float("nan"),
    })
display(pd.DataFrame(loss_rate_rows).set_index("run"))
'''))

# =============================================================================================
# PART D
# =============================================================================================
cells.append(md("""# Part D - why it fails

The smoke test said the mechanism is destructive, not marginal. The valuable question is therefore
not whether it can be rescued but what it actually selects. For the centre, on every decision date,
the six vaults the screen KEPT are compared against the six the incumbent composite WOULD have held
out of the same pool (`kept` against `incumbent_top` in `complement_log`).

Three candidate explanations are TESTED rather than asserted:

1. the screen discards the composite ranking almost entirely;
2. a low trailing joint-loss frequency mean-reverts, so it does not predict the next cycle;
3. it selects thin, rarely-reporting vaults whose apparent independence is measurement sparsity -
   the NB20 concern, which found a mark going stale for 5+ days predicts a resuming return 119 bps
   below average.

**Measurement note.** `complement_log` records the screened pool in composite-descending ORDER but
not the composite VALUE, so the composite is characterised by rank within the pool rather than by
score. `incumbent_top` is ranks 0-5 by construction, so its mean rank is 2.5 exactly; the kept
group's mean rank is the informative number. `incumbent_top` is also the composite's top six of the
pool BEFORE the minimum-hold reordering and the deposit-window skip, so it is what the incumbent
ranking would have handed on, not necessarily what the anchor traded.
"""))

cells.append(code('''#: One row per (decision date, group, address), with everything Part D compares.
def next_decision(ts):
    """The next date on the strategy's own decision schedule, or None at the last one.

    Located by searching the schedule rather than by a dictionary keyed on exact timestamps, so a
    `complement_log` key that is not bit-identical to an equity-curve index entry still resolves.
    """
    position = int(SCHEDULE.searchsorted(pd.Timestamp(ts), side="right"))
    return SCHEDULE[position] if position < len(SCHEDULE) else None


def forward_cycle_return(address: str, ts) -> float:
    next_ts = next_decision(ts)
    if next_ts is None or address not in MARK_COLUMNS:
        return float("nan")
    begin, finish = MARKS.loc[mark_day(ts), address], MARKS.loc[mark_day(next_ts), address]
    if not (np.isfinite(begin) and np.isfinite(finish)) or begin <= 0:
        return float("nan")
    return float(finish / begin - 1.0)


def address_features(address: str, ts, rank: int, joint_loss: float) -> dict:
    in_matrix = address in MARK_COLUMNS
    day = mark_day(ts)
    return {
        "date": ts, "address": address, "composite_rank": rank,
        "joint_loss": joint_loss,
        "fresh_marks_in_window": float(FRESH_ROLL.loc[day, address]) if in_matrix else float("nan"),
        "observed_days_in_window": float(OBSERVED_ROLL.loc[day, address]) if in_matrix else float("nan"),
        "stale_share_in_window": float(STALE_SHARE_ROLL.loc[day, address]) if in_matrix else float("nan"),
        "age_days": float((day - pd.Timestamp(INCEPTION.loc[address])).days)
                    if address in INCEPTION.index else float("nan"),
        "tvl_usd": float(TVL.loc[day, address]) if (in_matrix and address in TVL.columns) else float("nan"),
        "forward_cycle_return": forward_cycle_return(address, ts),
        "in_mark_matrix": in_matrix,
        "in_life_cache": address in INCEPTION.index,
    }


group_rows, pool_rows = [], []
for ts, entry in sorted(centre_log.items()):
    pool = list(entry["screened_pool"])
    rank_of = {address: i for i, address in enumerate(pool)}
    joint_loss_map = entry["joint_loss"]
    for group, members in (("kept", entry["kept"]), ("incumbent_top", entry["incumbent_top"])):
        for address in members:
            row = address_features(address, ts, rank_of.get(address, -1),
                                   float(joint_loss_map.get(address, float("nan"))))
            row["group"] = group
            group_rows.append(row)
    for address in pool:
        row = address_features(address, ts, rank_of[address],
                               float(joint_loss_map.get(address, float("nan"))))
        row["kept"] = address in set(entry["kept"])
        pool_rows.append(row)

groups = pd.DataFrame(group_rows)
pool_reads = pd.DataFrame(pool_rows)
print(f"{len(groups)} group records over {groups['date'].nunique()} decision dates; "
      f"{len(pool_reads)} pool reads.")
print(f"Group records not in the mark matrix: {int((~groups['in_mark_matrix']).sum())}; "
      f"not in the NB13 life cache: {int((~groups['in_life_cache']).sum())}. "
      f"Counted, never dropped.")
'''))

cells.append(code('''COMPARE_COLUMNS = ["composite_rank", "joint_loss", "fresh_marks_in_window",
                   "observed_days_in_window", "stale_share_in_window", "age_days", "tvl_usd",
                   "forward_cycle_return"]
comparison = groups.groupby("group")[COMPARE_COLUMNS].agg(["mean", "median", "count"])
print("What the screen KEPT against what the incumbent composite WOULD have held:")
display(comparison)

difference = pd.DataFrame({
    "kept_mean": groups[groups["group"] == "kept"][COMPARE_COLUMNS].mean(),
    "incumbent_top_mean": groups[groups["group"] == "incumbent_top"][COMPARE_COLUMNS].mean(),
})
difference["difference"] = difference["kept_mean"] - difference["incumbent_top_mean"]
difference["kept_median"] = groups[groups["group"] == "kept"][COMPARE_COLUMNS].median()
difference["incumbent_top_median"] = groups[groups["group"] == "incumbent_top"][COMPARE_COLUMNS].median()
display(difference)
'''))

cells.append(code('''#: Explanation 1: does the screen discard the composite ranking?
kept_ranks = groups[groups["group"] == "kept"]["composite_rank"]
print(f"Mean composite rank of the kept six: {kept_ranks.mean():.2f} "
      f"(the incumbent top six is 2.5 by construction, and the pool runs 0 to "
      f"{COMPLEMENTARY_CENTRE - 1}).")
print(f"Share of kept slots drawn from outside the incumbent top six (rank >= 6): "
      f"{float((kept_ranks >= 6).mean()):.2%}.")
print(f"Share drawn from the bottom third of the pool (rank >= {int(COMPLEMENTARY_CENTRE * 2 / 3)}): "
      f"{float((kept_ranks >= int(COMPLEMENTARY_CENTRE * 2 / 3)).mean()):.2%}.")
display(kept_ranks.value_counts().sort_index().rename("kept slots").to_frame()
        .assign(share=lambda f: f["kept slots"] / f["kept slots"].sum()))
'''))

cells.append(code('''#: Explanation 2: does a low trailing joint-loss frequency predict anything forward?
#: Every pool read with an estimate, bucketed by trailing joint-loss quintile against the realised
#: return over the FOLLOWING cycle. If the lowest bucket does not out-earn the highest, the screen
#: is sorting on a statistic that does not survive one cycle.
estimated = pool_reads[np.isfinite(pool_reads["joint_loss"])
                       & np.isfinite(pool_reads["forward_cycle_return"])].copy()
print(f"Pool reads with both a joint-loss estimate and a forward return: {len(estimated)} of "
      f"{len(pool_reads)}.")
if len(estimated) >= 50:
    estimated["joint_loss_quintile"] = pd.qcut(estimated["joint_loss"], 5, duplicates="drop")
    quintiles = estimated.groupby("joint_loss_quintile", observed=True).agg(
        reads=("forward_cycle_return", "size"),
        mean_joint_loss=("joint_loss", "mean"),
        mean_forward_cycle_return_bps=("forward_cycle_return", lambda s: float(s.mean() * 1e4)),
        median_forward_cycle_return_bps=("forward_cycle_return", lambda s: float(s.median() * 1e4)),
        share_negative=("forward_cycle_return", lambda s: float((s < 0).mean())),
        mean_fresh_marks=("fresh_marks_in_window", "mean"),
        mean_stale_share=("stale_share_in_window", "mean"),
        mean_age_days=("age_days", "mean"),
    )
    display(quintiles)
    correlation = float(estimated["joint_loss"].corr(estimated["forward_cycle_return"]))
    print(f"Correlation of trailing joint-loss frequency with the next cycle's return: "
          f"{correlation:+.4f}. A NEGATIVE correlation would mean a low trailing joint-loss "
          f"frequency predicts a HIGHER forward return, which is what the screen assumes.")
else:
    print("Too few estimated pool reads to bucket; reported rather than forced.")
'''))

cells.append(code('''#: Explanation 3: is a low joint-loss frequency really a proxy for reporting rarely?
print("Correlations across every pool read with an estimate:")
correlation_rows = []
for column in ("fresh_marks_in_window", "observed_days_in_window", "stale_share_in_window",
               "age_days", "tvl_usd"):
    sub = pool_reads[np.isfinite(pool_reads["joint_loss"]) & np.isfinite(pool_reads[column])]
    correlation_rows.append({
        "against": column, "reads": len(sub),
        "pearson_with_joint_loss": float(sub["joint_loss"].corr(sub[column])) if len(sub) > 10 else float("nan"),
        "spearman_with_joint_loss": float(sub["joint_loss"].corr(sub[column], method="spearman")) if len(sub) > 10 else float("nan"),
    })
display(pd.DataFrame(correlation_rows).set_index("against"))

#: The NB20 concern stated directly: are the kept six thinner reporters than the incumbent six?
reporting = groups.groupby("group").agg(
    mean_fresh_marks_in_window=("fresh_marks_in_window", "mean"),
    median_fresh_marks_in_window=("fresh_marks_in_window", "median"),
    mean_stale_share=("stale_share_in_window", "mean"),
    share_with_under_20_fresh_marks=("fresh_marks_in_window", lambda s: float((s < 20).mean())),
    mean_tvl_usd=("tvl_usd", "mean"),
    median_tvl_usd=("tvl_usd", "median"),
    mean_age_days=("age_days", "mean"),
)
display(reporting)
print("NB20 found a mark going stale for 5+ days predicts a resuming return 119 bps below "
      "average, concentrated in the post-April dense-polling regime, with only 46% of such losses "
      "recovering within 30 days. If the kept six report materially less often than the incumbent "
      "six, the screen is buying that penalty deliberately.")
'''))

cells.append(code('''#: The realised P&L difference attributable to the swap. Equal-weighted over the six names, which
#: is a PROXY: the strategy sizes by inverse volatility, and complement_log does not record the
#: weights. The realised CAGR gap between the two full simulations is shown beside it as the
#: number that actually matters.
by_date = groups.pivot_table(index="date", columns="group", values="forward_cycle_return",
                             aggfunc="mean")
by_date = by_date.dropna()
swap_difference = by_date["kept"] - by_date["incumbent_top"]
ci_lo_swap, ci_hi_swap = block_bootstrap_ci(swap_difference, block=10)
compounded_kept = float((1.0 + by_date["kept"]).prod() - 1.0)
compounded_incumbent = float((1.0 + by_date["incumbent_top"]).prod() - 1.0)
print(f"Equal-weighted forward-cycle return over {len(by_date)} cycles:")
print(f"  kept          mean {by_date['kept'].mean() * 1e4:+.2f} bps per cycle, "
      f"compounded {compounded_kept:+.2%}")
print(f"  incumbent_top mean {by_date['incumbent_top'].mean() * 1e4:+.2f} bps per cycle, "
      f"compounded {compounded_incumbent:+.2%}")
print(f"  difference    mean {swap_difference.mean() * 1e4:+.2f} bps per cycle, "
      f"95% block-bootstrap CI [{ci_lo_swap * 1e4:+.2f}, {ci_hi_swap * 1e4:+.2f}] bps (block 10)")
print(f"  share of cycles on which the swap lost money against the incumbent six: "
      f"{float((swap_difference < 0).mean()):.2%}")
print(f"Realised full-simulation gap: {CENTRE_LABEL} CAGR "
      f"{float(run_by_label[CENTRE_LABEL]['panel']['cagr']):.6f} against anchor "
      f"{float(anchor_panel['cagr']):.6f}; ulcer "
      f"{float(run_by_label[CENTRE_LABEL]['panel']['ulcer']):.6f} against "
      f"{float(anchor_panel['ulcer']):.6f}.")
SWAP_BPS = float(swap_difference.mean() * 1e4)
'''))

cells.append(code('''#: A fourth mechanism, cheap to check and easy to miss: the screen hands `decide_trades` exactly
#: six candidates, so the deposit-window skip and the minimum-hold reordering downstream have
#: nothing left to backfill with. If the centre holds fewer names than the anchor, part of the
#: damage is deployment rather than selection.
basket_rows = []
for label, frame in (("anchor", anchor_funded), (CENTRE_LABEL, centre_funded)):
    counts = [len(holdings_at(frame, ts)) for ts in SCHEDULE]
    basket_rows.append({
        "run": label, "mean_holdings": float(np.mean(counts)),
        "median_holdings": float(np.median(counts)),
        "share_of_dates_with_6": float(np.mean([c >= 6 for c in counts])),
        "share_of_dates_under_6": float(np.mean([c < 6 for c in counts])),
        "min_holdings": int(np.min(counts)),
        "mean_invested": float(run_by_label[label]["panel"]["mean_invested"]),
    })
display(pd.DataFrame(basket_rows).set_index("run"))
'''))

cells.append(code('''#: Part D in one table, and the mechanism of failure stated from these numbers.
MECHANISM = pd.DataFrame([
    {"explanation": "1. the screen discards the composite ranking",
     "measure": "mean composite rank of the kept six (incumbent = 2.5)",
     "value": float(kept_ranks.mean()),
     "supporting": f"{float((kept_ranks >= 6).mean()):.2%} of kept slots come from rank >= 6"},
    {"explanation": "2. trailing joint loss does not survive one cycle",
     "measure": "correlation of trailing joint loss with the next cycle's return",
     "value": float(estimated["joint_loss"].corr(estimated["forward_cycle_return"]))
              if len(estimated) >= 50 else float("nan"),
     "supporting": "negative would support the screen; positive or near zero refutes it"},
    {"explanation": "3. it selects thin, rarely-reporting vaults",
     "measure": "kept minus incumbent mean fresh marks in the trailing window",
     "value": float(reporting.loc["kept", "mean_fresh_marks_in_window"]
                    - reporting.loc["incumbent_top", "mean_fresh_marks_in_window"]),
     "supporting": f"kept stale share {float(reporting.loc['kept', 'mean_stale_share']):.4f} "
                   f"against {float(reporting.loc['incumbent_top', 'mean_stale_share']):.4f}"},
    {"explanation": "4. the basket cannot be backfilled after the screen",
     "measure": "mean holdings, centre minus anchor",
     "value": float(np.mean([len(holdings_at(centre_funded, ts)) for ts in SCHEDULE])
                    - np.mean([len(holdings_at(anchor_funded, ts)) for ts in SCHEDULE])),
     "supporting": f"mean invested {float(run_by_label[CENTRE_LABEL]['panel']['mean_invested']):.4f} "
                   f"against {float(anchor_panel['mean_invested']):.4f}"},
    {"explanation": "the cost of the swap itself",
     "measure": "equal-weighted forward-cycle return, kept minus incumbent, bps",
     "value": SWAP_BPS,
     "supporting": f"95% CI [{ci_lo_swap * 1e4:+.2f}, {ci_hi_swap * 1e4:+.2f}] bps"},
]).set_index("explanation")
display(MECHANISM)
print("Any NaN above is a measurement that could not be made on this snapshot; it is reported "
      "here rather than hidden, and the explanation it belongs to is left unsupported.")
'''))

# =============================================================================================
# Verdict and manifest
# =============================================================================================
cells.append(md("""# Verdict

ADOPT - which means **admission to the prospective shadow protocol of NB24, not authorisation to
deploy capital** - only if the centre passes all seven constraints of adoption rule v3 and the
late period, every plateau neighbour passes, leave-one-vault-out passes, AND the realised
within-basket joint-loss concentration falls against the anchor. The last of those is the point of
the mechanism: passing a constraint table while the basket still sinks together would mean the
proxy failed.

Otherwise REJECT, with the complete failure set for every row.
"""))
cells.append(code('''import json

GATES = {
    "centre_passes_v3_and_late": CENTRE_OK,
    "every_plateau_neighbour_passes": NEIGHBOURS_OK,
    "plateau_ok": PLATEAU_OK,
    "leave_one_vault_out_ok": LOVO_OK,
    "within_basket_concentration_falls": CONCENTRATION_FALLS,
}
gate_frame = pd.DataFrame([{"gate": k, "passed": bool(v)} for k, v in GATES.items()]).set_index("gate")
display(gate_frame)

VERDICT = "ADOPT" if all(GATES.values()) else "REJECT"
if VERDICT == "ADOPT":
    print(f"VERDICT: ADOPT {CENTRE_LABEL} - admission to the NB24 prospective shadow protocol, "
          f"NOT authorisation to deploy capital.")
else:
    print("VERDICT: REJECT.")
    print(f"Gates failed: {[k for k, v in GATES.items() if not v]}")
    print("The complete failure set for every candidate:")
    display(verdict.loc[candidate_order, ["cagr", "cycle_sharpe", "passes_v3", "failed", "late_ok"]])
'''))

cells.append(code('''MANIFEST_PATH = Path("_build/manifest_22.json")

manifest = {
    "notebook": "22-backtest-joint-downside.ipynb",
    "plan": "20-stability-leads-plan.md",
    "lead": "2 - complementary downside selection, replacing the named-exclusion backtest",
    "verdict": VERDICT,
    "centre_label": CENTRE_LABEL,
    "adoption_rule": "v3, constraint 7 comparator = the 5-step volatility-matched family",
    "gates": {k: bool(v) for k, v in GATES.items()},
    "references_reproduced": REFERENCES_REPRODUCED,
    "reference_check": {
        label: {
            "expected_cagr": float(row["expected_cagr"]), "actual_cagr": float(row["actual_cagr"]),
            "expected_cycle_sharpe": float(row["expected_cycle_sharpe"]),
            "actual_cycle_sharpe": float(row["actual_cycle_sharpe"]),
            "reproduced": bool(row["reproduced"]),
        }
        for label, row in reference_check.iterrows()
    },
    "part_a_read_only_diagnostic": {
        "decision_dates_with_both_logs": len(band_dates),
        "distinct_addresses_in_band": int(band["address"].nunique()),
        "mean_marginal_band_size": float(band_by_date["marginal_band"].mean()),
        "mean_leakage_d20_not_in_d30": float(band_by_date["leakage_d20_not_in_d30"].mean()),
        "no_vol_estimate_share_of_band_records": float(
            (band["volatility_estimate"] != "available").mean()),
        "first_decision": {
            "date": str(band_dates[0].date()),
            "dropped_30": int(band_by_date.iloc[0]["dropped_30"]),
            "d30_no_vol_estimate": int(band_by_date.iloc[0]["d30_no_vol_estimate"]),
            "marginal_band": int(band_by_date.iloc[0]["marginal_band"]),
            "marginal_no_vol_estimate": int(band_by_date.iloc[0]["marginal_no_vol_estimate"]),
        },
        "persistent_core": {
            row["threshold"]: {"vaults": int(row["vaults"]), "addresses": row["addresses"]}
            for _label, row in persistent_core.reset_index().iterrows()
        },
        "frequency_table_top_15": {
            address: {
                "share_of_dates": float(top_summary.loc[address, "share_of_dates"]),
                "dates_in_band": int(top_summary.loc[address, "dates_in_band"]),
                "no_vol_estimate_share": float(top_summary.loc[address, "no_vol_estimate_share"]),
                "scored_share": float(top_summary.loc[address, "scored_share"]),
                "in_life_cache": bool(top_summary.loc[address, "in_life_cache"]),
                "ever_displaced_a_funded_anchor_position": bool(
                    displacement.loc[address, "ever_displaced_a_funded_anchor_position"]),
                "band_dates_while_anchor_held_it": int(
                    displacement.loc[address, "band_dates_while_anchor_held_it"]),
            }
            for address in top_addresses
        },
        "top_15_ever_displacing_a_funded_anchor_position": int(
            displacement["ever_displaced_a_funded_anchor_position"].sum()),
        "monthly_membership_stability": {
            str(month): {
                "band_members": int(row["band_members"]),
                "jaccard_vs_previous_month": None if not np.isfinite(row["jaccard_vs_previous_month"])
                                             else float(row["jaccard_vs_previous_month"]),
            }
            for month, row in monthly.iterrows()
        },
        "used_to_configure_any_run": False,
    },
    "plateau": {
        "centre": COMPLEMENTARY_CENTRE,
        "grid": [int(p) for p in COMPLEMENTARY_GRID],
        "booleans": {f"complementary_{p}": bool(plateau_flags[f"complementary_{p}"])
                     for p in COMPLEMENTARY_GRID},
        "plateau_ok": PLATEAU_OK,
        "centre_failed": failing_constraints_v3(
            run_by_label[CENTRE_LABEL]["panel"], anchor_panel, family),
    },
    "window_sensitivity": {
        label: {
            "overrides": overrides,
            "passes_v3": bool(window_sensitivity.loc[label, "passes_v3"]),
            "late_ok": bool(window_sensitivity.loc[label, "late_ok"]),
            "failed": str(window_sensitivity.loc[label, "failed"]),
        }
        for label, overrides in WINDOW_SENSITIVITY.items()
    },
    "window_sensitivity_ok": WINDOW_OK,
    "leave_one_vault_out": {
        "executed": LOVO_LABEL in run_by_label,
        "masked_vault": LOVO_MASKED_VAULT,
        "passed": LOVO_OK,
    },
    "part_c_within_basket_concentration": {
        "definition": "mean pairwise P(both down | both reported fresh) over the trailing "
                      f"{JOINT_WINDOW} days, averaged over the basket's pairs and over decision dates",
        "anchor_realised": anchor_conc,
        "centre_realised": centre_conc,
        "difference_centre_minus_anchor": centre_conc - anchor_conc,
        "falls": CONCENTRATION_FALLS,
        "paired_difference_mean": float(paired_difference.mean()),
        "paired_difference_ci": [float(ci_lo), float(ci_hi)],
        "independence_decomposition": {
            "definition": "co-loss LEVEL minus the product of the two marginal down rates over "
                          "the same both-fresh days; the residual is the co-movement part",
            "anchor_excess": anchor_excess,
            "centre_excess": centre_excess,
            "paired_excess_difference_mean": float(excess_difference.mean()),
            "paired_excess_difference_ci": [float(ci_lo_excess), float(ci_hi_excess)],
            "excess_falls": EXCESS_FALLS,
            "kept_excess": KEPT_EXCESS,
            "incumbent_top_excess": INCUMBENT_EXCESS,
        },
        "screen_kept_vs_incumbent_top": {
            "kept": KEPT_CONC, "incumbent_top": INCUMBENT_CONC,
            "difference": KEPT_CONC - INCUMBENT_CONC,
        },
        "share_of_dates_basket_changed": CHANGED_SHARE,
        "pool_reads": POOL_READS,
        "pool_reads_with_no_estimate": MISSING_READS,
        "share_of_cycles_with_4plus_losers": {
            "definition": "four or more of however many names the run actually held that cycle; "
                          "confounded with basket size because the centre holds six less often",
            "anchor": COLOSS_ANCHOR, "centre": COLOSS_CENTRE,
        },
        "share_of_cycles_with_4plus_losers_six_name_cycles_only": {
            "cycles": COLOSS_SIX_CYCLES,
            "anchor": COLOSS_ANCHOR_SIX, "centre": COLOSS_CENTRE_SIX,
        },
    },
    "part_d_summary": {
        "mean_composite_rank_kept": float(kept_ranks.mean()),
        "share_of_kept_slots_from_rank_6_or_worse": float((kept_ranks >= 6).mean()),
        "correlation_joint_loss_with_forward_cycle_return": (
            float(estimated["joint_loss"].corr(estimated["forward_cycle_return"]))
            if len(estimated) >= 50 else None),
        "kept_mean_fresh_marks_in_window": float(reporting.loc["kept", "mean_fresh_marks_in_window"]),
        "incumbent_mean_fresh_marks_in_window": float(
            reporting.loc["incumbent_top", "mean_fresh_marks_in_window"]),
        "kept_mean_stale_share": float(reporting.loc["kept", "mean_stale_share"]),
        "incumbent_mean_stale_share": float(reporting.loc["incumbent_top", "mean_stale_share"]),
        "kept_mean_age_days": float(reporting.loc["kept", "mean_age_days"]),
        "incumbent_mean_age_days": float(reporting.loc["incumbent_top", "mean_age_days"]),
        "kept_mean_tvl_usd": float(reporting.loc["kept", "mean_tvl_usd"]),
        "incumbent_mean_tvl_usd": float(reporting.loc["incumbent_top", "mean_tvl_usd"]),
        "swap_forward_return_difference_bps_per_cycle": SWAP_BPS,
        "swap_forward_return_difference_ci_bps": [float(ci_lo_swap * 1e4), float(ci_hi_swap * 1e4)],
        "mechanism_table": json.loads(MECHANISM.reset_index().to_json(orient="records")),
    },
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
            "passes_v3": bool(passes_constraints_v3(entry["panel"], anchor_panel, family)),
            "failed": failing_constraints_v3(entry["panel"], anchor_panel, family),
            "late_ok": bool(late_period_ok_v3(entry["panel"], anchor_panel)),
        }
        for entry in runs
    },
    "baseline_parity": {metric: float(anchor_panel[metric]) for metric in BASELINE},
}

MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=False))
print(f"Wrote the frozen manifest for NB24 to {MANIFEST_PATH.resolve()}")
print(json.dumps({k: v for k, v in manifest.items() if k not in ("runs", "part_a_read_only_diagnostic")},
                 indent=1, sort_keys=False))
'''))

cells += integrity_and_audit_cells()

write_notebook(cells, TRACK_DIR / "22-backtest-joint-downside.ipynb")
