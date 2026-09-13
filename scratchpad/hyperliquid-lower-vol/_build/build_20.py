"""NB20 - reporting-versus-trading inactivity (mark quality).

Diagnostic notebook. Measures how much of this track's risk measurement rests on marks that did
not move, and whether a quiet mark is the same thing as a quiet vault.

Built on the same shared cells as every other notebook in the track; the raw-poll loading pattern
is build_13.py's, with its own separately fingerprinted cache (NB13 owns the legacy path).
"""
import sys
sys.path.insert(0, ".")
from pathlib import Path
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR, INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import PARAM_ADDITIONS_STABILITY, INDICATOR_ADDITIONS_STABILITY, \
    CELL14_REPLACEMENTS_STABILITY

HARNESS_EVIDENCE = (BUILD_DIR / "harness_evidence.py").read_text()
HARNESS_STABILITY = (BUILD_DIR / "harness_stability.py").read_text()

#: Flipped to False only if `assert_anchor_parity()` fails because the vault price archive was
#: re-downloaded. The assertion is never weakened - the cell prints the same comparison frame
#: either way and the heading states the drift; the operator re-baselines `BASELINE` centrally.
ASSERT_PARITY = True

PARITY_CELL_ASSERTING = '''display(provenance())
display(assert_anchor_parity())
record_anchor()
'''

PARITY_CELL_REPORTING = '''display(provenance())

#: The vault price archive was re-downloaded on 2026-09-13, after NB13-NB19 and after the
#: full-precision `BASELINE` in harness_stability.py was frozen. `assert_anchor_parity()` therefore
#: fails on a data change, not on a code change. The assertion is NOT weakened and NOT re-baselined
#: here - that is a central decision for the operator. This cell prints the identical comparison
#: frame without asserting, so the drift is visible and quantified in the heading, and every
#: measurement below is stated as being on the NEW snapshot.
parity = pd.DataFrame([
    {
        "metric": metric,
        "expected (BASELINE, 2026-09-09 archive)": expected,
        "actual (this kernel, 2026-09-13 archive)": float(anchor_panel[metric]),
        "abs_diff": abs(float(anchor_panel[metric]) - expected),
        "rel_diff_pct": (float(anchor_panel[metric]) - expected) / abs(expected) * 100.0 if expected else float("nan"),
        "within_tolerance": abs(float(anchor_panel[metric]) - expected) <= BASELINE_TOLERANCE,
    }
    for metric, expected in BASELINE.items()
]).set_index("metric")
display(parity)
print(f"Metrics within +/-{BASELINE_TOLERANCE:g} of BASELINE: "
      f"{int(parity['within_tolerance'].sum())} of {len(parity)}")
print("PARITY NOT ASSERTED: the price archive changed under the baseline. See the heading.")

#: The other half of `assert_anchor_parity()` - that both `decide_trades` splices are inert on the
#: anchor path - does NOT depend on the data snapshot, so it is still asserted at full strength.
assert not VOL_DROP_LOG, "the vol-matched drop log fired on the anchor path; the splice is not inert"
assert not COMPLEMENT_LOG, "the complementary screen fired on the anchor path; the splice is not inert"
print("Both decide_trades splices confirmed inert on the anchor path.")

record_anchor()
'''

HEADING = """# NB20 - research: reporting inactivity versus trading inactivity (DIAGNOSTIC)

No strategy change, nothing adopted. Every risk number this track rests on - ulcer index, cycle
volatility, BTC beta, Sortino - is computed from a vault share-price series that simply stops
updating when the vault stops reporting. A vault that goes quiet therefore *looks* stable. This
notebook measures how large that problem is on the data the track actually trades: how much of the
calendar is spent inside an unmoved mark, whether a long quiet run is followed by a
disproportionately negative resuming mark, whether such a mark recovers, how much of it reached
the anchor's own book, and what dropping the affected cycles does to the anchor's measured risk.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Precursor requested by the review recorded in
[20-stability-leads-plan.md](20-stability-leads-plan.md) ("Decisions for the operator", item 2).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "20-research-mark-quality",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY,
)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_STABILITY)
cells.append(md("# Harness\n"))
cells.append(harness_cell())
cells.append(code(HARNESS_EVIDENCE))
cells.append(code(HARNESS_STABILITY))

cells.append(md("""# Provenance and anchor parity

The content hashes below decide what this notebook can conclude. The anchor is the unchanged
`02-better-format.ipynb` configuration, run in this kernel with both stability-track
`decide_trades` splices present but disabled.
"""))
cells.append(code(PARITY_CELL_ASSERTING if ASSERT_PARITY else PARITY_CELL_REPORTING))

# ---------------------------------------------------------------------------------------------
# The mark-quality cache
# ---------------------------------------------------------------------------------------------
cells.append(md("""# The raw poll archive, and what counts as a gap

Loaded straight from the Hyperliquid poll archive rather than from the strategy's indicator
series, so the measurement is of the data itself and not of anything the strategy did to it. The
loading pattern is NB13's; the cache is fingerprinted on the archive's size, its modification time
and the window end, under its own filename (NB13 owns the legacy life-stats path).

**Definitions used everywhere below.** Each vault's polls are resampled to one observation per
calendar day (last poll of the day), then reindexed onto the complete calendar from the vault's
first poll to the last day of the backtest window and forward-filled. A **gap** is a maximal run
of consecutive calendar days on which the resulting mark did not move
(`pct_change() == 0`) - which covers both "polled and unchanged" and "not polled at all",
deliberately, because the strategy cannot tell those apart either. A **fresh mark** is a day the
mark did move. The **mark age** on any day is the number of days since the last move; it is 0 on a
fresh day. Gap lengths are the length of the whole run even when the run extends past the edge of
the segment being reported, so a segment can never make a gap look shorter than it was.

Trailing runs that never end - the vault simply stopped reporting - are included in the census (an
endpoint gap is the most consequential kind) but excluded from the resuming-return analysis, which
by construction needs a gap that ends in a fresh mark.
"""))

cells.append(code('''from pathlib import Path

LAST_DAY = WINDOW_END - pd.Timedelta(days=1)          # 2026-09-08, the last traded day
CENSUS_SEGMENTS = {
    "full": (WINDOW_START, LAST_DAY),
    "sparse (pre-April)": (WINDOW_START, REGIME_BREAK - pd.Timedelta(days=1)),
    "dense (April onwards)": (REGIME_BREAK, LAST_DAY),
}
SEGMENT_ORDER = list(CENSUS_SEGMENTS)

raw_price_path = Path("~/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet").expanduser()
_archive = raw_price_path.stat()
_stem = (f"/tmp/hyperliquid-lower-vol-mark-quality-{_archive.st_size}-{int(_archive.st_mtime)}"
         f"-{Parameters.backtest_end:%Y%m%d}")
CENSUS_CACHE = Path(_stem + "-census.parquet")
EVENTS_CACHE = Path(_stem + "-events.parquet")
DAILY_CACHE = Path(_stem + "-daily.parquet")

if CENSUS_CACHE.exists() and EVENTS_CACHE.exists() and DAILY_CACHE.exists():
    vault_census = pd.read_parquet(CENSUS_CACHE)
    mark_events = pd.read_parquet(EVENTS_CACHE)
    daily_marks = pd.read_parquet(DAILY_CACHE)
    print(f"Loaded the mark-quality cache from {CENSUS_CACHE.parent} (fingerprint {_stem.split('-mark-quality-')[1]})")
else:
    polls = pd.read_parquet(
        raw_price_path,
        columns=["chain", "address", "share_price"],
        filters=[("chain", "==", ChainId.hypercore.value)],
    )
    polls["address"] = polls["address"].astype(str).str.lower()
    polls = polls[polls.index < Parameters.backtest_end]

    census_rows, event_frames, daily_frames = [], [], []
    for address, group in polls.groupby("address", sort=False):
        prices = group["share_price"].astype(float).dropna()
        prices = prices[prices > 0]
        if len(prices) < 5:
            continue
        daily = prices.resample("1D").last()
        daily = daily.reindex(pd.date_range(daily.index[0], LAST_DAY, freq="1D")).ffill()
        if len(daily) < 10 or not np.isfinite(daily.to_numpy()).all():
            continue

        r = daily.pct_change()
        stale = (r == 0.0).fillna(False)
        run_id = (stale != stale.shift(fill_value=False)).cumsum()
        # Length of the whole unmoved run each day belongs to (0 on a day the mark moved), and how
        # many days into that run the day is - the mark age.
        gap_len = stale.groupby(run_id).transform("size").where(stale, 0).astype("int32")
        mark_age = stale.groupby(run_id).cumsum().astype("int32")

        #: One row per FRESH mark: the return, the length of the gap that immediately preceded it,
        #: the level the mark sat at through that gap, and the next 30 calendar days.
        fresh = (r.notna() & (r != 0.0)).to_numpy()
        values = daily.to_numpy()
        position = np.arange(len(daily))
        forward = np.minimum(position + 30, len(daily) - 1)
        # Highest mark over [d, d+30], computed by reversing on a positional index so the
        # rolling window can never be interpreted against the calendar index.
        forward_max = pd.Series(values[::-1]).rolling(31, min_periods=1).max().to_numpy()[::-1]
        frame = pd.DataFrame({
            "address": address,
            "date": daily.index,
            "ret": r.to_numpy(),
            "prev_gap_len": gap_len.shift(1).fillna(0).astype("int32").to_numpy(),
            "level_before_gap": daily.shift(1).to_numpy(),
            "price": values,
            "fwd30_price": values[forward],
            "fwd30_max": forward_max,
            "fwd30_truncated": (position + 30) > (len(daily) - 1),
        })[fresh]
        event_frames.append(frame)

        #: Per-day staleness over the backtest window only, for sections 4 and 5.
        window_slice = slice(WINDOW_START, LAST_DAY)
        window_index = daily.loc[window_slice].index
        if len(window_index):
            daily_frames.append(pd.DataFrame({
                "address": address,
                "date": window_index,
                "gap_len": gap_len.loc[window_slice].to_numpy(),
                "mark_age": mark_age.loc[window_slice].to_numpy(),
            }))

        for segment, (start, end) in CENSUS_SEGMENTS.items():
            window = daily.loc[start:end]
            if len(window) < 10:
                continue
            lengths_in_window = gap_len.loc[start:end]
            run_ids_in_window = run_id.loc[start:end][lengths_in_window > 0]
            lengths = lengths_in_window[lengths_in_window > 0].groupby(run_ids_in_window).first()
            returns_in_window = r.loc[start:end]
            census_rows.append({
                "address": address,
                "segment": segment,
                "inception": daily.index[0],
                "window_days": int(len(window)),
                "fresh_days": int(((returns_in_window != 0.0) & returns_in_window.notna()).sum()),
                "n_gaps": int(len(lengths)),
                "median_gap": float(lengths.median()) if len(lengths) else 0.0,
                "p90_gap": float(lengths.quantile(0.90)) if len(lengths) else 0.0,
                "max_gap": int(lengths.max()) if len(lengths) else 0,
                "share_days_in_gap_3plus": float((lengths_in_window >= 3).mean()),
                "share_days_in_gap_5plus": float((lengths_in_window >= 5).mean()),
                "endpoint_mark_age_days": int(mark_age.loc[start:end].iloc[-1]),
            })

    vault_census = pd.DataFrame(census_rows)
    mark_events = pd.concat(event_frames, ignore_index=True)
    daily_marks = pd.concat(daily_frames, ignore_index=True)
    vault_census.to_parquet(CENSUS_CACHE)
    mark_events.to_parquet(EVENTS_CACHE)
    daily_marks.to_parquet(DAILY_CACHE)
    print(f"Built the mark-quality cache: {len(vault_census)} census rows, "
          f"{len(mark_events)} fresh marks, {len(daily_marks)} vault-days.")

#: Fail closed: a NaN must never reach a comparison further down.
assert np.isfinite(mark_events["ret"].to_numpy()).all(), "non-finite fresh return in the event table"
assert np.isfinite(mark_events["level_before_gap"].to_numpy()).all(), "non-finite pre-gap level"
assert (mark_events["prev_gap_len"] >= 0).all()
assert daily_marks["gap_len"].notna().all() and daily_marks["mark_age"].notna().all()

#: The tradable cohort: the vaults the strategy's own universe actually carries.
tradable_addresses = {
    str(pair.pool_address).lower() for pair in strategy_universe.iterate_pairs() if pair.is_vault()
}
print(f"Vaults in the trading universe: {len(tradable_addresses)}")
print(f"Vaults in the archive with a usable price history: {vault_census['address'].nunique()}")
print(f"Of those, in the trading universe: "
      f"{vault_census[vault_census['address'].isin(tradable_addresses)]['address'].nunique()}")
'''))

# ---------------------------------------------------------------------------------------------
# 1. Polling-gap census
# ---------------------------------------------------------------------------------------------
cells.append(md("""# 1. Polling-gap census across the tradable cohort

How much of the calendar is an unmoved mark, per vault, over the backtest window and separately
either side of the NB57 polling regime break at 2026-04-01. The two numbers that matter most are
the share of days spent inside a gap of three days or more - the fraction of the risk measurement
that is arithmetic on a repeated number - and the age of the final mark, which is how stale the
last observation in every one of this track's series is.
"""))

cells.append(code('''census = vault_census[vault_census["address"].isin(tradable_addresses)].copy()
assert len(census), "no census rows for the trading universe"

summary_rows = []
for segment in SEGMENT_ORDER:
    sub = census[census["segment"] == segment]
    if not len(sub):
        continue
    summary_rows.append({
        "segment": segment,
        "vaults": len(sub),
        "median window days": sub["window_days"].median(),
        "median gaps per vault": sub["n_gaps"].median(),
        "median gap length": sub["median_gap"].median(),
        "median p90 gap length": sub["p90_gap"].median(),
        "median longest gap": sub["max_gap"].median(),
        "p90 longest gap": sub["max_gap"].quantile(0.90),
        "median share of days in a 3+ day gap": sub["share_days_in_gap_3plus"].median(),
        "mean share of days in a 3+ day gap": sub["share_days_in_gap_3plus"].mean(),
        "mean share of days in a 5+ day gap": sub["share_days_in_gap_5plus"].mean(),
        "median mark age at segment end": sub["endpoint_mark_age_days"].median(),
    })
display(pd.DataFrame(summary_rows).set_index("segment").T)

#: The distribution across vaults, not just its centre - a median hides the tail that matters.
quantile_rows = []
for segment in SEGMENT_ORDER:
    sub = census[census["segment"] == segment]
    if not len(sub):
        continue
    for column in ("n_gaps", "median_gap", "p90_gap", "max_gap",
                   "share_days_in_gap_3plus", "endpoint_mark_age_days"):
        quantile_rows.append({
            "segment": segment, "statistic": column,
            "p10": sub[column].quantile(0.10), "p25": sub[column].quantile(0.25),
            "p50": sub[column].quantile(0.50), "p75": sub[column].quantile(0.75),
            "p90": sub[column].quantile(0.90), "max": sub[column].max(),
        })
display(pd.DataFrame(quantile_rows).set_index(["segment", "statistic"]))
'''))

cells.append(code('''full = census[census["segment"] == "full"].set_index("address")
assert full["endpoint_mark_age_days"].notna().all()

endpoint_rows = []
for threshold in (1, 3, 7, 14, 30, 60, 90):
    flagged = full["endpoint_mark_age_days"] >= threshold
    endpoint_rows.append({
        "final mark at least this stale (days)": threshold,
        "vaults": int(flagged.sum()),
        "share of the tradable cohort": float(flagged.mean()),
    })
display(pd.DataFrame(endpoint_rows).set_index("final mark at least this stale (days)"))

stale_7 = int((full["endpoint_mark_age_days"] >= 7).sum())
stale_30 = int((full["endpoint_mark_age_days"] >= 30).sum())
print(f"Of {len(full)} tradable vaults, {stale_7} ({stale_7 / len(full):.1%}) end the window on a "
      f"mark that has not moved for 7 or more days, and {stale_30} ({stale_30 / len(full):.1%}) on "
      f"a mark that has not moved for 30 or more days.")
print(f"Cohort-wide share of vault-days inside a gap of 3 or more days: "
      f"{float((daily_marks[daily_marks['address'].isin(tradable_addresses)]['gap_len'] >= 3).mean()):.1%}")
print(f"Cohort-wide share of vault-days inside a gap of 5 or more days: "
      f"{float((daily_marks[daily_marks['address'].isin(tradable_addresses)]['gap_len'] >= 5).mean()):.1%}")

display(full.sort_values("endpoint_mark_age_days", ascending=False)[
    ["inception", "window_days", "fresh_days", "n_gaps", "median_gap", "max_gap",
     "share_days_in_gap_3plus", "endpoint_mark_age_days"]].head(20))
'''))

cells.append(code('''import plotly.express as px

gap_days = daily_marks[daily_marks["address"].isin(tradable_addresses)]
coverage = gap_days.groupby("date").agg(
    vaults=("address", "size"),
    share_stale=("gap_len", lambda s: float((s > 0).mean())),
    share_gap_3plus=("gap_len", lambda s: float((s >= 3).mean())),
    share_gap_5plus=("gap_len", lambda s: float((s >= 5).mean())),
).reset_index()

fig = px.line(
    coverage, x="date", y=["share_stale", "share_gap_3plus", "share_gap_5plus"],
    title="Share of tradable vaults whose mark did not move that day",
)
fig.add_vline(x=REGIME_BREAK, line_dash="dash")
fig.update_layout(yaxis_tickformat=".0%", yaxis_title="share of vaults")
fig.show()

display(coverage.set_index("date").resample("1MS").mean().round(4))
'''))

# ---------------------------------------------------------------------------------------------
# 2. Does a gap predict a loss?
# ---------------------------------------------------------------------------------------------
cells.append(md("""# 2. Does a gap predict a loss?

The core question. For every fresh mark inside the backtest window, the length of the gap that
immediately preceded it is known, so the resuming return can be conditioned on it. If long gaps
are followed by disproportionately negative marks then quiet periods are hiding losses, and every
ulcer measurement in this track is optimistic - the loss is real, it is simply reported late and in
one lump instead of accruing day by day.

Buckets 0 and 1 are the baseline: a mark that moved yesterday, or after a single quiet day. The
unconditional row is every fresh mark, exactly as the spec asks; the 0-1 rows are the more
informative comparison because they exclude the very events being tested.

Regime is assigned by the date the **gap started**, because polling density at that time is what
the split is about.
""" ))

cells.append(code('''events = mark_events[mark_events["address"].isin(tradable_addresses)].copy()
events = events[(events["date"] >= WINDOW_START) & (events["date"] <= LAST_DAY)].copy()
events["gap_start"] = events["date"] - pd.to_timedelta(events["prev_gap_len"], unit="D")
events["regime"] = np.where(events["gap_start"] < REGIME_BREAK,
                            "sparse (pre-April)", "dense (April onwards)")
assert np.isfinite(events["ret"].to_numpy()).all(), "non-finite resuming return"
print(f"Fresh marks inside the window, tradable cohort: {len(events)} "
      f"across {events['address'].nunique()} vaults")

BUCKET_ORDER = ["0 (moved yesterday)", "1", "2", "3-4", "5-7", "8-14", "15+"]

def gap_bucket(length: int) -> str:
    length = int(length)
    if length == 0:
        return "0 (moved yesterday)"
    if length == 1:
        return "1"
    if length == 2:
        return "2"
    if length <= 4:
        return "3-4"
    if length <= 7:
        return "5-7"
    if length <= 14:
        return "8-14"
    return "15+"

events["bucket"] = [gap_bucket(v) for v in events["prev_gap_len"]]


def bucket_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bucket in BUCKET_ORDER:
        sub = frame[frame["bucket"] == bucket]["ret"]
        rows.append({
            "preceding gap (days)": bucket,
            "count": int(len(sub)),
            "mean bps": float(sub.mean() * 1e4) if len(sub) else float("nan"),
            "median bps": float(sub.median() * 1e4) if len(sub) else float("nan"),
            "share negative": float((sub < 0).mean()) if len(sub) else float("nan"),
            "p5 bps": float(np.percentile(sub, 5) * 1e4) if len(sub) else float("nan"),
            "p95 bps": float(np.percentile(sub, 95) * 1e4) if len(sub) else float("nan"),
            "std bps": float(sub.std() * 1e4) if len(sub) > 1 else float("nan"),
        })
    everything = frame["ret"]
    rows.append({
        "preceding gap (days)": "ALL (unconditional)",
        "count": int(len(everything)),
        "mean bps": float(everything.mean() * 1e4),
        "median bps": float(everything.median() * 1e4),
        "share negative": float((everything < 0).mean()),
        "p5 bps": float(np.percentile(everything, 5) * 1e4),
        "p95 bps": float(np.percentile(everything, 95) * 1e4),
        "std bps": float(everything.std() * 1e4),
    })
    return pd.DataFrame(rows).set_index("preceding gap (days)")

print("Whole window")
display(bucket_table(events))
for regime in ("sparse (pre-April)", "dense (April onwards)"):
    print(regime)
    display(bucket_table(events[events["regime"] == regime]))
'''))

cells.append(md("""## The difference, with a block bootstrap interval

The statistic is deliberately simple: the mean resuming return after a gap of five days or more,
minus the mean over all fresh marks; and the same for the share of resuming marks that are
negative. The interval is a moving-block bootstrap over **calendar days** - a draw resamples whole
blocks of consecutive dates and keeps every vault's event on those dates - so it preserves both the
serial dependence of the polling regime and the cross-sectional dependence of vaults that report on
the same days.

These observations are heavily overlapping and heavily clustered by vault, so **no t-test is quoted
and no significance is claimed**. The interval is a description of resampling spread under one
particular dependence assumption, nothing more.
"""))

cells.append(code('''BOOTSTRAP_BLOCK_DAYS = 10
BOOTSTRAP_DRAWS_MARK = 1000
BOOTSTRAP_SEED_MARK = 0


def _statistics(returns: np.ndarray, long_gap: np.ndarray) -> dict:
    """Both headline differences on one sample. NaN when the long-gap cell is empty."""
    if long_gap.sum() == 0 or len(returns) == 0:
        return {"mean_diff_bps": float("nan"), "share_neg_diff": float("nan")}
    return {
        "mean_diff_bps": float((returns[long_gap].mean() - returns.mean()) * 1e4),
        "share_neg_diff": float((returns[long_gap] < 0).mean() - (returns < 0).mean()),
    }


def gap_effect(frame: pd.DataFrame, min_gap: int = 5, block: int = BOOTSTRAP_BLOCK_DAYS,
               draws: int = BOOTSTRAP_DRAWS_MARK, seed: int = BOOTSTRAP_SEED_MARK) -> dict:
    returns = frame["ret"].to_numpy()
    long_gap = (frame["prev_gap_len"].to_numpy() >= min_gap)
    observed = _statistics(returns, long_gap)
    codes, unique_dates = pd.factorize(frame["date"], sort=True)
    index_by_date = [np.flatnonzero(codes == i) for i in range(len(unique_dates))]
    n_dates = len(unique_dates)
    rng = np.random.default_rng(seed)
    draws_mean, draws_share = [], []
    if n_dates >= block:
        for _ in range(draws):
            starts = rng.integers(0, n_dates - block + 1, size=int(np.ceil(n_dates / block)))
            picked = np.concatenate([np.arange(s, s + block) for s in starts])[:n_dates]
            selection = np.concatenate([index_by_date[i] for i in picked])
            sample = _statistics(returns[selection], long_gap[selection])
            if np.isfinite(sample["mean_diff_bps"]):
                draws_mean.append(sample["mean_diff_bps"])
                draws_share.append(sample["share_neg_diff"])
    def interval(values):
        if not values:
            return float("nan"), float("nan")
        return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))
    mean_lo, mean_hi = interval(draws_mean)
    share_lo, share_hi = interval(draws_share)
    return {
        "events": int(len(frame)),
        f"events after a {min_gap}+ day gap": int(long_gap.sum()),
        "mean diff (bps)": observed["mean_diff_bps"],
        "mean diff ci lo": mean_lo, "mean diff ci hi": mean_hi,
        "share-negative diff": observed["share_neg_diff"],
        "share-neg ci lo": share_lo, "share-neg ci hi": share_hi,
        "draws used": len(draws_mean), "block days": block, "seed": seed,
    }


effect_rows = []
for label, frame in [
    ("whole window", events),
    ("sparse (pre-April)", events[events["regime"] == "sparse (pre-April)"]),
    ("dense (April onwards)", events[events["regime"] == "dense (April onwards)"]),
]:
    for min_gap in (2, 5, 8, 15):
        row = gap_effect(frame, min_gap=min_gap)
        row = {"segment": label, "min gap": min_gap, **row}
        row["events after a N+ day gap"] = row.pop(f"events after a {min_gap}+ day gap")
        effect_rows.append(row)
effect = pd.DataFrame(effect_rows).set_index(["segment", "min gap"])
display(effect)

for block in (5, 20):
    alt = gap_effect(events, min_gap=5, block=block)
    print(f"block {block:>2} days: mean diff {alt['mean diff (bps)']:.2f} bps, "
          f"95% interval [{alt['mean diff ci lo']:.2f}, {alt['mean diff ci hi']:.2f}] bps")
'''))

cells.append(code('''chart_rows = []
for regime in ("sparse (pre-April)", "dense (April onwards)"):
    table = bucket_table(events[events["regime"] == regime]).drop(index="ALL (unconditional)")
    table = table.reset_index()
    table["regime"] = regime
    chart_rows.append(table)
chart = pd.concat(chart_rows, ignore_index=True)
chart["preceding gap (days)"] = pd.Categorical(chart["preceding gap (days)"], BUCKET_ORDER, ordered=True)
chart = chart.sort_values("preceding gap (days)")

fig = px.bar(chart, x="preceding gap (days)", y="mean bps", color="regime", barmode="group",
             hover_data=["count", "share negative", "p5 bps"],
             title="Mean resuming mark return by the length of the gap before it")
fig.show()

fig = px.bar(chart, x="preceding gap (days)", y="share negative", color="regime", barmode="group",
             hover_data=["count"],
             title="Share of resuming marks that were negative, by preceding gap length")
fig.update_layout(yaxis_tickformat=".0%")
fig.show()
'''))

# ---------------------------------------------------------------------------------------------
# 3. Recovery
# ---------------------------------------------------------------------------------------------
cells.append(md("""# 3. Recovery after a negative resuming mark

For gaps of five days or more that ended in a negative fresh mark, what happened over the next 30
calendar days. Two questions, because they are not the same one: the cumulative move from the
resuming mark itself (did it keep falling), and whether the vault ever traded back up to the level
it had held throughout the gap (did the reported loss reverse).

Events whose 30-day forward window runs past the end of the archive are marked `truncated` and
reported separately - their forward window is shorter than 30 days and would otherwise bias the
recovery share upwards or downwards depending on which way the tail leans.
"""))

cells.append(code('''recovery = events[(events["prev_gap_len"] >= 5) & (events["ret"] < 0)].copy()
recovery["cum30_from_resume"] = recovery["fwd30_price"] / recovery["price"] - 1.0
recovery["cum30_from_pre_gap"] = recovery["fwd30_price"] / recovery["level_before_gap"] - 1.0
recovery["recovered_to_pre_gap"] = recovery["fwd30_max"] >= recovery["level_before_gap"]
assert np.isfinite(recovery["cum30_from_resume"].to_numpy()).all() or not len(recovery)

print(f"Gaps of 5+ days that ended in a negative mark: {len(recovery)} "
      f"across {recovery['address'].nunique()} vaults")

def recovery_row(label, frame):
    if not len(frame):
        return {"cohort": label, "events": 0}
    return {
        "cohort": label,
        "events": int(len(frame)),
        "median resuming return bps": float(frame["ret"].median() * 1e4),
        "median 30d cum return from the resuming mark bps": float(frame["cum30_from_resume"].median() * 1e4),
        "mean 30d cum return from the resuming mark bps": float(frame["cum30_from_resume"].mean() * 1e4),
        "median 30d cum return from the pre-gap level bps": float(frame["cum30_from_pre_gap"].median() * 1e4),
        "share recovering to the pre-gap level": float(frame["recovered_to_pre_gap"].mean()),
        "share still below the pre-gap level after 30d": float((frame["cum30_from_pre_gap"] < 0).mean()),
    }

rows = [
    recovery_row("all 5+ day gaps ending negative", recovery),
    recovery_row("  of which forward window complete", recovery[~recovery["fwd30_truncated"]]),
    recovery_row("  of which forward window truncated", recovery[recovery["fwd30_truncated"]]),
    recovery_row("sparse (pre-April)", recovery[recovery["regime"] == "sparse (pre-April)"]),
    recovery_row("dense (April onwards)", recovery[recovery["regime"] == "dense (April onwards)"]),
    recovery_row("gap 5-7", recovery[recovery["prev_gap_len"].between(5, 7)]),
    recovery_row("gap 8-14", recovery[recovery["prev_gap_len"].between(8, 14)]),
    recovery_row("gap 15+", recovery[recovery["prev_gap_len"] >= 15]),
]
display(pd.DataFrame(rows).set_index("cohort"))

#: The control: what a negative fresh mark that was NOT preceded by a long gap does next.
control = events[(events["prev_gap_len"] <= 1) & (events["ret"] < 0)].copy()
control["cum30_from_resume"] = control["fwd30_price"] / control["price"] - 1.0
control["cum30_from_pre_gap"] = control["fwd30_price"] / control["level_before_gap"] - 1.0
control["recovered_to_pre_gap"] = control["fwd30_max"] >= control["level_before_gap"]
display(pd.DataFrame([
    recovery_row("CONTROL: negative marks after a 0-1 day gap", control),
]).set_index("cohort"))
'''))

# ---------------------------------------------------------------------------------------------
# 4. What reaches the anchor's book
# ---------------------------------------------------------------------------------------------
cells.append(md("""# 4. How much of this reaches the anchor's own book

Everything above is a property of the universe. This section restricts to the vaults the anchor
actually held, and to the windows it held them in, because a cohort-wide staleness rate is only
interesting to the strategy insofar as it sat inside a funded position.

`capital` is the sum of the position's buy-trade values (`TradeExecution.get_value()`), so it is
the money actually put in rather than a mark-to-market snapshot. Profit shares are reported against
both net and gross-positive profit, because a share of a net figure that has negative components in
it is easy to misread.
"""))

cells.append(code('''marks_by_address = {
    address: group.set_index("date").sort_index()
    for address, group in daily_marks.groupby("address", sort=False)
}
held_rows = []
unmatched = []
for position in anchor_state.portfolio.get_all_positions():
    if position.is_credit_supply():
        continue
    address = str(position.pair.pool_address).lower()
    opened = pd.Timestamp(position.opened_at).normalize()
    closed = pd.Timestamp(position.closed_at).normalize() if position.closed_at else LAST_DAY
    closed = min(max(closed, opened), LAST_DAY)
    frame = marks_by_address.get(address)
    window = frame.loc[opened:closed] if frame is not None else None
    if window is None or not len(window):
        unmatched.append((address, position.position_id))
        continue
    gap_lengths = window["gap_len"].to_numpy()
    ages = window["mark_age"].to_numpy()
    capital = float(sum(t.get_value() for t in position.trades.values() if t.is_buy()))
    profit = float(position.get_total_profit_usd() or 0.0)
    held_rows.append({
        "position_id": position.position_id,
        "vault": position.pair.base.token_symbol,
        "address": address,
        "opened": opened,
        "closed": closed,
        "open_days": int(len(window)),
        "capital_usd": capital,
        "profit_usd": profit,
        "mark_age_at_entry": int(ages[0]),
        "mark_age_at_exit": int(ages[-1]),
        "longest_gap_while_open": int(gap_lengths.max()),
        "days_in_gap_3plus": int((gap_lengths >= 3).sum()),
        "days_in_gap_5plus": int((gap_lengths >= 5).sum()),
        "had_gap_5plus": bool((gap_lengths >= 5).any()),
        "share_of_holding_stale": float((gap_lengths > 0).mean()),
    })

held = pd.DataFrame(held_rows)
print(f"Anchor positions matched to a vault price series: {len(held)}; unmatched: {len(unmatched)}")
if unmatched:
    print(f"  unmatched (excluded from every share below): {unmatched}")
assert len(held), "no anchor position could be matched to the poll archive"
assert held[["capital_usd", "profit_usd"]].notna().all().all()

flagged = held["had_gap_5plus"]
gross_positive = held.loc[held["profit_usd"] > 0, "profit_usd"].sum()
exposure_total = float((held["capital_usd"] * held["open_days"]).sum())
exposure_stale5 = float((held["capital_usd"] * held["days_in_gap_5plus"]).sum())
exposure_stale3 = float((held["capital_usd"] * held["days_in_gap_3plus"]).sum())

reach = pd.DataFrame([
    {"measure": "positions that saw a 5+ day gap while open",
     "value": float(flagged.mean()), "n": f"{int(flagged.sum())} of {len(held)}"},
    {"measure": "capital in positions that saw a 5+ day gap",
     "value": float(held.loc[flagged, "capital_usd"].sum() / held["capital_usd"].sum()),
     "n": f"${held.loc[flagged, 'capital_usd'].sum():,.0f} of ${held['capital_usd'].sum():,.0f}"},
    {"measure": "net profit from positions that saw a 5+ day gap",
     "value": float(held.loc[flagged, "profit_usd"].sum() / held["profit_usd"].sum()),
     "n": f"${held.loc[flagged, 'profit_usd'].sum():,.0f} of ${held['profit_usd'].sum():,.0f}"},
    {"measure": "gross positive profit from positions that saw a 5+ day gap",
     "value": float(held.loc[flagged & (held["profit_usd"] > 0), "profit_usd"].sum() / gross_positive)
     if gross_positive > 0 else float("nan"),
     "n": f"${held.loc[flagged & (held['profit_usd'] > 0), 'profit_usd'].sum():,.0f} of ${gross_positive:,.0f}"},
    {"measure": "capital-days spent inside a 5+ day gap",
     "value": exposure_stale5 / exposure_total if exposure_total else float("nan"),
     "n": f"{exposure_stale5:,.0f} of {exposure_total:,.0f} $-days"},
    {"measure": "capital-days spent inside a 3+ day gap",
     "value": exposure_stale3 / exposure_total if exposure_total else float("nan"),
     "n": f"{exposure_stale3:,.0f} of {exposure_total:,.0f} $-days"},
]).set_index("measure")
display(reach)

display(pd.DataFrame({
    "mark age at entry (days)": held["mark_age_at_entry"].describe(),
    "mark age at exit (days)": held["mark_age_at_exit"].describe(),
    "longest gap while open (days)": held["longest_gap_while_open"].describe(),
    "share of holding days stale": held["share_of_holding_stale"].describe(),
}))
print(f"Positions entered on a mark that had not moved for 3+ days: "
      f"{int((held['mark_age_at_entry'] >= 3).sum())} of {len(held)}")
print(f"Positions exited on a mark that had not moved for 3+ days: "
      f"{int((held['mark_age_at_exit'] >= 3).sum())} of {len(held)}")
print(f"Positions exited on a mark that had not moved for 7+ days: "
      f"{int((held['mark_age_at_exit'] >= 7).sum())} of {len(held)}")
'''))

cells.append(code('''display(held.sort_values("capital_usd", ascending=False)[
    ["vault", "opened", "closed", "open_days", "capital_usd", "profit_usd",
     "mark_age_at_entry", "mark_age_at_exit", "longest_gap_while_open",
     "days_in_gap_5plus", "share_of_holding_stale"]].head(25))

by_vault = held.groupby("vault").agg(
    positions=("position_id", "size"),
    capital_usd=("capital_usd", "sum"),
    profit_usd=("profit_usd", "sum"),
    positions_with_5plus_gap=("had_gap_5plus", "sum"),
    longest_gap=("longest_gap_while_open", "max"),
    mean_share_stale=("share_of_holding_stale", "mean"),
).sort_values("profit_usd", ascending=False)
display(by_vault)
'''))

# ---------------------------------------------------------------------------------------------
# 5. What it does to the measured risk
# ---------------------------------------------------------------------------------------------
cells.append(md("""# 5. What stale marks do to the anchor's measured risk

A sensitivity, **not a correction**. The anchor's ulcer index and cycle volatility are recomputed
on an equity curve from which every strategy cycle has been dropped where a majority of the
invested book, by value, sat inside a gap of five days or more. Dropped, not zero-filled: a
zero-filled cycle would assert that nothing happened, which is precisely the assumption under test.

Dropping observations changes the sample. The remaining curve is a curve over a different set of
dates, with wider and uneven spacing, and its ulcer index and volatility are **not** an estimate of
"the true risk" - there is no way to recover an unobserved path from an unmoved mark. The only
thing this table can support is a statement about how much of the measured risk is load-bearing on
cycles where the book was mostly not reporting.

Position values come from `state.stats.positions[pid]`, the framework's own per-cycle revaluation
record, so the weighting is the book the strategy actually had rather than a reconstruction.
"""))

cells.append(code('''positions_by_id = {p.position_id: p for p in anchor_state.portfolio.get_all_positions()}
value_rows = []
for position_id, statistics in anchor_state.stats.positions.items():
    position = positions_by_id.get(position_id)
    if position is None or position.is_credit_supply():
        continue
    address = str(position.pair.pool_address).lower()
    for entry in statistics:
        value_rows.append({
            "timestamp": pd.Timestamp(entry.calculated_at),
            "address": address,
            "value": float(entry.value or 0.0),
        })
position_values = pd.DataFrame(value_rows)
print(f"Per-cycle position valuations: {len(position_values)} rows over "
      f"{position_values['timestamp'].nunique()} cycles")

lookup = daily_marks.set_index(["address", "date"])["gap_len"]
position_values["gap_len"] = lookup.reindex(pd.MultiIndex.from_arrays([
    position_values["address"], position_values["timestamp"].dt.normalize()
])).to_numpy()
missing = int(position_values["gap_len"].isna().sum())
print(f"Valuation rows with no matching vault-day in the archive: {missing} "
      f"({missing / len(position_values):.2%}) - counted as NOT stale, which is the conservative "
      f"direction for this test.")
position_values["gap_len"] = position_values["gap_len"].fillna(0.0)

per_cycle = position_values.groupby("timestamp").agg(
    invested_value=("value", "sum"), positions=("value", "size"))
for threshold_days, column in ((5, "stale5_value"), (3, "stale3_value")):
    per_cycle[column] = (
        position_values[position_values["gap_len"] >= threshold_days]
        .groupby("timestamp")["value"].sum().reindex(per_cycle.index).fillna(0.0)
    )
per_cycle["stale5_share"] = np.where(
    per_cycle["invested_value"] > 0, per_cycle["stale5_value"] / per_cycle["invested_value"], 0.0)
per_cycle["stale3_share"] = np.where(
    per_cycle["invested_value"] > 0, per_cycle["stale3_value"] / per_cycle["invested_value"], 0.0)
assert np.isfinite(per_cycle["stale5_share"].to_numpy()).all()
print(f"Anchor equity points: {len(anchor_equity)}; cycles with a valuation record: {len(per_cycle)}; "
      f"overlapping timestamps: {len(anchor_equity.index.intersection(per_cycle.index))}")

display(per_cycle[["positions", "invested_value", "stale5_share", "stale3_share"]].describe())
print(f"Cycles where a majority of the invested book was inside a 5+ day gap: "
      f"{int((per_cycle['stale5_share'] > 0.5).sum())} of {len(per_cycle)}")
print(f"Cycles where a majority of the invested book was inside a 3+ day gap: "
      f"{int((per_cycle['stale3_share'] > 0.5).sum())} of {len(per_cycle)}")

fig = px.line(per_cycle.reset_index(), x="timestamp", y=["stale5_share", "stale3_share"],
              title="Share of the anchor's invested book sitting on an unmoved mark, per cycle")
fig.add_hline(y=0.5, line_dash="dash")
fig.add_vline(x=REGIME_BREAK, line_dash="dot")
fig.update_layout(yaxis_tickformat=".0%", yaxis_title="share of invested value")
fig.show()
'''))

cells.append(code('''def risk_of(curve: pd.Series) -> dict:
    """Ulcer and annualised volatility of one equity curve, on its OWN observed spacing."""
    returns_, periods = cycle_returns(curve)
    return {
        "observations": int(len(curve)),
        "median spacing (days)": float(np.median(
            [(b - a).days for a, b in zip(curve.index, curve.index[1:])])) if len(curve) > 1 else float("nan"),
        "ulcer": ulcer_index(curve),
        "cycle vol (own spacing)": float(returns_.std() * np.sqrt(periods)),
        "cycle vol (anchor clock)": float(returns_.std() * np.sqrt(PERIODS_PER_YEAR)),
        "cagr": cagr_of(curve),
        "max_dd": float((curve / curve.cummax() - 1.0).min()),
    }


sensitivity_rows = [{"variant": "as measured (nothing dropped)", "cycles dropped": 0, **risk_of(anchor_equity)}]
for threshold in (0.75, 0.5, 0.25):
    drop_at = per_cycle.index[per_cycle["stale5_share"] > threshold]
    keep = anchor_equity.drop(anchor_equity.index.intersection(drop_at))
    if len(keep) < 10:
        sensitivity_rows.append({"variant": f"drop cycles with >{threshold:.0%} of the book stale (5+ days)",
                                 "cycles dropped": len(anchor_equity) - len(keep)})
        continue
    sensitivity_rows.append({
        "variant": f"drop cycles with >{threshold:.0%} of the book stale (5+ days)",
        "cycles dropped": int(len(anchor_equity) - len(keep)),
        **risk_of(keep),
    })
drop_at3 = per_cycle.index[per_cycle["stale3_share"] > 0.5]
keep3 = anchor_equity.drop(anchor_equity.index.intersection(drop_at3))
if len(keep3) >= 10:
    sensitivity_rows.append({
        "variant": "drop cycles with >50% of the book stale (3+ days)",
        "cycles dropped": int(len(anchor_equity) - len(keep3)),
        **risk_of(keep3),
    })

sensitivity = pd.DataFrame(sensitivity_rows).set_index("variant")
sensitivity["ulcer vs as measured"] = sensitivity["ulcer"] / sensitivity.loc["as measured (nothing dropped)", "ulcer"]
sensitivity["vol vs as measured"] = (
    sensitivity["cycle vol (own spacing)"] / sensitivity.loc["as measured (nothing dropped)", "cycle vol (own spacing)"]
)
display(sensitivity)

print("This is a SENSITIVITY, not a correction. Dropping cycles changes the sample, the spacing "
      "and the drawdown path; none of the rows below the first is an estimate of the anchor's true "
      "risk, and no adoption decision anywhere in this track may cite them as one.")

primary = per_cycle.index[per_cycle["stale5_share"] > 0.5]
kept = anchor_equity.drop(anchor_equity.index.intersection(primary))
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(x=anchor_equity.index, y=anchor_equity.values, mode="lines", name="anchor, as measured"))
fig.add_trace(go.Scatter(x=kept.index, y=kept.values, mode="lines", name="anchor, majority-stale cycles dropped"))
fig.update_layout(title="Anchor equity: as measured, and with majority-stale cycles dropped", yaxis_type="log")
fig.show()
'''))

cells.append(md("""# Verdict

DIAGNOSTIC. Nothing is adopted, nothing is rejected, no parameter changes. The numbers above are
inputs to how the rest of this track's risk measurements should be read.
"""))

cells += integrity_and_audit_cells()

write_notebook(cells, TRACK_DIR / "20-research-mark-quality.ipynb")
