"""NB23 - the incumbent composite with only its Sortino leg swapped (lead 3).

20-stability-leads-plan.md, section "NB23 - backtest: the incumbent composite with only its
Sortino leg swapped (lead 3)".

`cagr_sortino_shrunk_weight` keeps the incumbent's own 360-day `cagr_score` leg untouched and
replaces only the 45-day rolling `sortino_score` leg with the event-time, shrunk
`sortino_shrunk_score` from `blocks_evidence.py`. That is a COMPONENT REPLACEMENT, not an
isolated test of shrinkage or of event time: the replacement leg changes horizon, shrinkage,
scaling and saturation at once, and its NaN behaviour differs too.

Two stages. Stage 1 audits what the replacement leg actually measures and whether the swap moves
the traded book at all; stage 2 sweeps only if the book moves on more than 10% of decision dates.

`USE_V2` below is set from the stage-1a forward-fill measurement (see the constant's comment).
The notebook recomputes that measurement and asserts the build-time decision matches, so the two
can never drift apart silently.
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

#: Pre-registered trigger for the `_v2` indicator chain (20-stability-leads-plan.md, NB23 stage 1):
#: if the forward fill inside `_event_time_stats` bridges a down-count-mask failure on more than
#: 2% of (candidate, date) reads, the notebook must use a chain that masks AFTER the reindex.
#: Measured: 0 of 18,651 (candidate, date) reads - the forward fill never bridges a down-count
#: mask failure on the gated pool, so the trigger did NOT fire and `blocks_stability.py` gains no
#: `_v2` chain. The notebook recomputes the share and asserts this constant matches it.
FORWARD_FILL_TRIGGER = 0.02
USE_V2 = False

INDICATOR_ADDITIONS_V2 = ""
if USE_V2:
    from blocks_stability import INDICATOR_ADDITIONS_SORTINO_V2
    INDICATOR_ADDITIONS_V2 = INDICATOR_ADDITIONS_SORTINO_V2

#: The stage-1a audit always measures the SHIPPED chain from `blocks_evidence.py` - that is the
#: thing under audit, and its forward-fill behaviour is what decides whether the `_v2` chain is
#: needed at all. Only the indicator the backtests SELECT on switches.
SORTINO_LEG = "sortino_shrunk_score"
RAW_LEG = "sortino_raw_event"
NEFF_LEG = "sortino_neff_event"
PRIOR_LEG = "sortino_cross_sectional_prior"
SELECTION_INDICATOR = "cagr_sortino_shrunk_weight_v2" if USE_V2 else "cagr_sortino_shrunk_weight"
V2_SORTINO_LEG = "sortino_shrunk_score_v2"


HEADING = """# NB23 - backtest: the incumbent composite with only its Sortino leg swapped (lead 3)

The incumbent composite `cagr_sortino_weight` is `0.6 x cagr_score(360 d) + 0.4 x
sortino_score(45 d)`. `cagr_sortino_shrunk_weight` keeps the 360-day CAGR leg **exactly as it
is** and replaces only the Sortino leg with the event-time, cross-sectionally shrunk
`sortino_shrunk_score`. This is a **component replacement, not an isolated test of shrinkage or
of event time**: the replacement leg changes horizon (up to 90 mark events rather than 45
calendar days), shrinkage, scaling and saturation all at once, and its NaN behaviour differs from
`sortino_score`'s. No result here can be read as "shrinkage helps" or "event time helps". Because
the CAGR leg is unchanged, the swap also **cannot reach any vault younger than 360 days**; it
only re-ranks the old cohort.

Two stages, in order. Stage 1 is a measurement audit of the replacement leg plus an identity
diagnostic that asks whether the swap changes the traded book at all. Stage 2 - the local
sensitivity sweep and the seven constraints of adoption rule v3 - runs only if the traded book
differs on more than 10% of decision dates.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Lead 3 of [20-stability-leads-plan.md](20-stability-leads-plan.md).

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "23-backtest-sortino-leg-swap",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_STABILITY},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY + INDICATOR_ADDITIONS_V2,
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
`decide_trades` splices present but disabled; `assert_anchor_parity()` asserts that both
diagnostic logs are empty afterwards, which is the evidence that neither splice fired rather than
the assumption that it did not.
"""))
cells.append(code('''display(provenance())
display(assert_anchor_parity())
record_anchor()
'''))

# ---------------------------------------------------------------------------------------------
# 2. Stage 1a - measurement audit
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Stage 1a - measurement audit of the replacement Sortino leg

Before any sweep: what does `sortino_shrunk_score` actually measure on the pool this strategy
chooses from? The audit runs over **every decision date on the anchor's own schedule** and
**every gated candidate at that date** - the gate reproduced here is `decide_trades`' own, up to
and including the momentum gate: inclusion criteria, `state.is_good_pair()`, the curator
quarantine, `MANUAL_BLACKLIST`, and `return_gate > gate_threshold`.

`decide_trades` reads indicators through `indicators.get_indicator_value()`, which is only
available inside the decision function. It returns the value **one candle bar before** the
decision timestamp (NB57), so the audit reads the cached indicator series at exactly
`decision timestamp - 1 bar` and never at the decision-date bar itself.

Five things are measured, all of them properties the plan's review flagged as unverified:

1. **Score validity rate** - the share of (candidate, date) reads where the score is not NaN.
2. **Elapsed calendar span of the event window** - a score described as "90 mark events" covers a
   different number of calendar days for every vault. If the dispersion is large the statistic is
   not comparable across the cross-section, and the heading has to say so.
3. **Age of the last VALID evidence** at each read, in days.
4. **The forward-fill audit.** `_event_time_stats()` ends with `raw_sortino.reindex(full_index)
   .ffill()`, and `raw_sortino` was already masked by `.where(down_count >= min_down_events)`. A
   later event window that FAILS the down-count mask therefore inherits an older valid score
   through the forward fill instead of becoming NaN. The pre-registered trigger is 2% of reads.
5. **Clipping frequency** at the `[0, 1]` cap.
"""))

cells.append(code('''import datetime

#: Names of the indicator chain this notebook uses. Rewritten to the `_v2` chain at BUILD time if
#: the stage-1a forward-fill measurement triggered it; the trigger is re-measured below and the
#: build-time decision asserted against it, so the two cannot drift apart silently.
SELECTION_INDICATOR = "__SELECTION_INDICATOR__"
SORTINO_LEG = "__SORTINO_LEG__"
RAW_LEG = "__RAW_LEG__"
NEFF_LEG = "__NEFF_LEG__"
PRIOR_LEG = "__PRIOR_LEG__"
V2_SORTINO_LEG = "__V2_SORTINO_LEG__"
USE_V2 = __USE_V2__
FORWARD_FILL_TRIGGER = __TRIGGER__
print(f"Indicator chain in use: {SELECTION_INDICATOR} (v2 chain = {USE_V2})")
print(f"Pre-registered forward-fill trigger: {FORWARD_FILL_TRIGGER:.0%} of (candidate, date) reads")

#: Read timing, exactly as `get_indicator_value()` performs it inside `decide_trades`.
ONE_BAR = Parameters.candle_time_bucket.to_timedelta()
SCHEDULE = pd.DatetimeIndex(sorted(pd.Timestamp(ts) for ts in anchor_equity.index))
READ_AT = pd.DatetimeIndex([ts.floor(ONE_BAR) - ONE_BAR for ts in SCHEDULE])
print(f"Decision schedule: {len(SCHEDULE)} dates, {SCHEDULE[0].date()} to {SCHEDULE[-1].date()}; "
      f"indicators are read at {READ_AT[0].date()} to {READ_AT[-1].date()}.")

#: The evidence parameters the cached indicator was actually computed with - `indicator_data` is
#: built from the unmodified `Parameters`, which is also the centre point of the sweep below.
EV_MAX_EVENTS = int(Parameters.evidence_max_events)
EV_MIN_EVENTS = int(Parameters.evidence_min_events)
EV_MIN_DOWN = int(Parameters.evidence_min_down_events)
EV_PRIOR_K = float(Parameters.evidence_prior_strength)
EV_T_CAP = float(Parameters.evidence_t_cap)
GATE = float(Parameters.gate_threshold)
display(pd.Series({
    "evidence_max_events": EV_MAX_EVENTS, "evidence_min_events": EV_MIN_EVENTS,
    "evidence_min_down_events": EV_MIN_DOWN, "evidence_prior_strength": EV_PRIOR_K,
    "evidence_t_cap": EV_T_CAP, "gate_threshold": GATE,
    "cagr_lookback_days (incumbent leg, unchanged)": int(Parameters.cagr_lookback_days),
    "cagr_weight": float(Parameters.cagr_weight),
}).rename("audit parameters").to_frame())

_series_cache = {}
def series_for(name, pair=None):
    """One cached read of a whole indicator series, future included (`unlimited=True`).

    Reading the whole series is only safe because every read below is taken at
    `decision timestamp - 1 bar`; nothing here looks at or past a decision date.
    """
    key = (name, None if pair is None else pair.internal_id)
    if key not in _series_cache:
        _series_cache[key] = indicator_data.get_indicator_series(name, pair=pair, unlimited=True)
    return _series_cache[key]


def read_on(series, dates):
    """The values a `get_indicator_value()` read would see on `dates`, as a numpy array.

    Forward fill rather than an exact match, which is what the framework does within its data
    delay tolerance. Every series here is daily and gap-free (the universe is built with
    `forward_fill=True`), so in practice this is an exact-match read.
    """
    if series is None or not len(series):
        return np.full(len(dates), np.nan)
    return series.reindex(series.index.union(dates)).ffill().reindex(dates).to_numpy(dtype=float)
'''
    .replace("__SELECTION_INDICATOR__", SELECTION_INDICATOR)
    .replace("__SORTINO_LEG__", SORTINO_LEG)
    .replace("__RAW_LEG__", RAW_LEG)
    .replace("__NEFF_LEG__", NEFF_LEG)
    .replace("__PRIOR_LEG__", PRIOR_LEG)
    .replace("__V2_SORTINO_LEG__", V2_SORTINO_LEG)
    .replace("__USE_V2__", repr(USE_V2))
    .replace("__TRIGGER__", repr(FORWARD_FILL_TRIGGER))))

cells.append(md("""## The gated candidate pool at each decision date

`decide_trades`' own gate, reproduced up to the point where it reads the composite. The anchor's
asset blacklist is asserted empty first, so `state.is_good_pair()` here is a pure function of the
pair (its tradeable flag) and reproducing it from the anchor's final state cannot differ from
what the live state said at each cycle.
"""))
cells.append(code('''assert not anchor_state.blacklisted_assets and not anchor_state.asset_blacklist, (
    "the anchor state carries a blacklist, so is_good_pair() is time-dependent and this audit's "
    "gate reproduction is not exact"
)

inclusion_series = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)

#: Every pair the inclusion criteria ever admit inside the schedule, so the momentum gate can be
#: read once per pair over all read dates rather than once per (pair, date).
_pool_by_date = {}
for ts, at in zip(SCHEDULE, READ_AT):
    prior_index = inclusion_series.index[inclusion_series.index <= at]
    _pool_by_date[ts] = list(inclusion_series.loc[prior_index[-1]]) if len(prior_index) else []
_ever_included = sorted({pid for pool in _pool_by_date.values() for pid in pool})
_gate_reads = {
    pair_id: read_on(series_for("return_gate", strategy_universe.get_pair_by_id(pair_id)), READ_AT)
    for pair_id in _ever_included
}
print(f"{len(_ever_included)} distinct vaults pass the inclusion criteria at least once.")

gated_by_date = {}
gate_reject_reasons = {"not_good_pair_or_quarantined": 0, "manual_blacklist": 0,
                       "momentum_gate": 0, "gated": 0}
for i, (ts, at) in enumerate(zip(SCHEDULE, READ_AT)):
    kept = []
    for pair_id in _pool_by_date[ts]:
        pair = strategy_universe.get_pair_by_id(pair_id)
        if not anchor_state.is_good_pair(pair) or is_quarantined(pair.pool_address, ts):
            gate_reject_reasons["not_good_pair_or_quarantined"] += 1
            continue
        if str(pair.pool_address).lower() in MANUAL_BLACKLIST:
            gate_reject_reasons["manual_blacklist"] += 1
            continue
        gate_value = _gate_reads[pair_id][i]
        if not (gate_value == gate_value and gate_value > GATE):
            gate_reject_reasons["momentum_gate"] += 1
            continue
        kept.append(pair_id)
        gate_reject_reasons["gated"] += 1
    gated_by_date[ts] = kept

pool_sizes = pd.Series({ts: len(v) for ts, v in gated_by_date.items()})
gated_pair_ids = sorted({pid for v in gated_by_date.values() for pid in v})
print(f"{int(pool_sizes.sum())} (candidate, date) reads across {len(SCHEDULE)} decision dates and "
      f"{len(gated_pair_ids)} distinct gated vaults.")
display(pd.DataFrame({
    "gated pool size": pool_sizes.describe(),
}).T)
display(pd.Series(gate_reject_reasons).rename("count").to_frame().assign(
    share=lambda f: f["count"] / f["count"].sum()))
'''))

cells.append(md("""## Reconstructing the event window, and proving the reconstruction is exact

The forward-fill question cannot be answered from the cached score alone: the cached series is
already reindexed and forward-filled, so the bridging is invisible in it by construction. The
event structure is therefore rebuilt here from the same `close` series the indicator was computed
on, and the rebuild is **verified against the cached indicator** before any conclusion is drawn
from it - `sortino_raw_event` reconstructed and forward-filled must equal the cached series at
every read, and the pre-clip score reconstructed from the cached raw, effective-n and prior must
equal the cached `sortino_shrunk_score` after clipping. Both are asserted, not eyeballed.
"""))
cells.append(code('''candles_close_all = strategy_universe.data_universe.candles.df["close"]

_close_cache = {}
def close_for(pair_id):
    if pair_id not in _close_cache:
        try:
            _close_cache[pair_id] = candles_close_all.xs(pair_id, level="pair_id").sort_index()
        except KeyError:
            _close_cache[pair_id] = None
    return _close_cache[pair_id]


def event_structure(pair_id):
    """Rebuild `_event_time_stats()`'s event-time intermediates, BEFORE the reindex and ffill.

    Returns the event dates, the down-event count and the masked raw Sortino on the event index,
    plus the calendar span of the window ending at each event. This is the only way to see which
    reads the forward fill bridged: once reindexed and forward-filled, a bridged read is
    indistinguishable from a fresh one.
    """
    close = close_for(pair_id)
    if close is None or len(close) < 2:
        return None
    r = close.pct_change()
    fresh_r = r[r.abs() > 0]
    if len(fresh_r) == 0:
        return None
    w = EV_MAX_EVENTS
    mean_event = fresh_r.rolling(w, min_periods=EV_MIN_EVENTS).mean()
    downside_event = (fresh_r.clip(upper=0.0) ** 2).rolling(w, min_periods=EV_MIN_EVENTS).mean() ** 0.5
    down_count = (fresh_r < 0).rolling(w, min_periods=1).sum()
    n_event = fresh_r.rolling(w, min_periods=EV_MIN_EVENTS).count()
    raw_event = (mean_event / downside_event.replace(0.0, float("nan"))) * (TRADING_DAYS_PER_YEAR ** 0.5)
    raw_masked = raw_event.where(down_count >= EV_MIN_DOWN)

    positions = np.arange(len(fresh_r))
    window_start = np.maximum(positions - w + 1, 0)
    stamps = fresh_r.index.to_numpy()
    span_days = (stamps - stamps[window_start]) / np.timedelta64(1, "D")

    valid = raw_masked.notna().to_numpy()
    last_valid = np.where(valid, positions, -1)
    last_valid = np.maximum.accumulate(last_valid)
    return {
        "events": fresh_r.index,
        "down_count": down_count.to_numpy(dtype=float),
        "n_event": n_event.to_numpy(dtype=float),
        "raw_masked": raw_masked.to_numpy(dtype=float),
        "span_days": span_days.astype(float),
        "window_events": (positions - window_start + 1).astype(float),
        "last_valid_pos": last_valid,
        "close_index": close.index,
    }


STRUCTURES = {pid: event_structure(pid) for pid in gated_pair_ids}
missing_structure = [pid for pid, s in STRUCTURES.items() if s is None]
print(f"Event structures rebuilt for {len(gated_pair_ids) - len(missing_structure)} of "
      f"{len(gated_pair_ids)} gated vaults; {len(missing_structure)} had no fresh mark at all.")
'''))

cells.append(code('''#: The cross-sectional shrinkage prior is a universe-level series; the indicator reindexes and
#: forward-fills it onto each pair's own calendar before using it, so the audit does the same.
prior_series = series_for(PRIOR_LEG)
prior_on_reads = read_on(prior_series, READ_AT)
prior_by_read = dict(zip(READ_AT, prior_on_reads))

def max_abs_diff(a, b) -> float:
    """Largest absolute difference where both are finite; 0.0 when there is nothing to compare.

    `np.nanmax` on an all-NaN slice both warns and returns NaN, and a vault that is never scored
    inside the window produces exactly that. Zero is the right answer there: two all-NaN series
    agree everywhere they have a value, and the separate NaN-disagreement count below is what
    catches a real mismatch in WHERE the score exists.
    """
    both = np.isfinite(a) & np.isfinite(b)
    return float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0


recon_rows = []
for pair_id in gated_pair_ids:
    pair = strategy_universe.get_pair_by_id(pair_id)
    structure = STRUCTURES[pair_id]
    cached_raw = read_on(series_for(RAW_LEG, pair), READ_AT)
    cached_neff = read_on(series_for(NEFF_LEG, pair), READ_AT)
    cached_score = read_on(series_for(SORTINO_LEG, pair), READ_AT)

    if structure is None:
        rebuilt_raw = np.full(len(READ_AT), np.nan)
        last_event_pos = np.full(len(READ_AT), -1)
    else:
        last_event_pos = structure["events"].searchsorted(READ_AT, side="right") - 1
        last_valid = np.where(last_event_pos >= 0,
                              structure["last_valid_pos"][np.clip(last_event_pos, 0, None)], -1)
        rebuilt_raw = np.where(last_valid >= 0,
                               structure["raw_masked"][np.clip(last_valid, 0, None)], np.nan)

    weight_own = cached_neff / (cached_neff + EV_PRIOR_K)
    pre_clip = (weight_own * np.nan_to_num(cached_raw) +
                (1.0 - weight_own) * np.nan_to_num(prior_on_reads)) / EV_T_CAP
    pre_clip = np.where(np.isnan(cached_raw), np.nan, pre_clip)
    rebuilt_score = np.clip(pre_clip, 0.0, 1.0)

    recon_rows.append({
        "pair_id": pair_id,
        "raw_max_abs_diff": max_abs_diff(rebuilt_raw, cached_raw),
        "raw_nan_disagreements": int(np.sum(np.isnan(rebuilt_raw) != np.isnan(cached_raw))),
        "score_max_abs_diff": max_abs_diff(rebuilt_score, cached_score),
        "score_nan_disagreements": int(np.sum(np.isnan(rebuilt_score) != np.isnan(cached_score))),
    })

recon = pd.DataFrame(recon_rows).set_index("pair_id")
recon = recon.replace([np.inf, -np.inf], np.nan)
display(recon.describe())
RAW_TOL, SCORE_TOL = 1e-9, 1e-9
assert float(recon["raw_max_abs_diff"].max(skipna=True) or 0.0) < RAW_TOL, (
    f"the event-time rebuild does not reproduce the cached {RAW_LEG}:\\n"
    f"{recon.sort_values('raw_max_abs_diff', ascending=False).head(10)}"
)
assert int(recon["raw_nan_disagreements"].sum()) == 0, (
    f"the event-time rebuild disagrees with the cached {RAW_LEG} about where the score exists:\\n"
    f"{recon[recon['raw_nan_disagreements'] > 0]}"
)
assert float(recon["score_max_abs_diff"].max(skipna=True) or 0.0) < SCORE_TOL, (
    f"the pre-clip rebuild does not reproduce the cached {SORTINO_LEG}:\\n"
    f"{recon.sort_values('score_max_abs_diff', ascending=False).head(10)}"
)
assert int(recon["score_nan_disagreements"].sum()) == 0, (
    f"the pre-clip rebuild disagrees with the cached {SORTINO_LEG} about where the score exists:\\n"
    f"{recon[recon['score_nan_disagreements'] > 0]}"
)
print(f"Reconstruction verified against the cached {RAW_LEG} and {SORTINO_LEG} at every read, "
      f"to within {RAW_TOL:g}. Everything below is computed from it.")
'''))

cells.append(md("""## The audit table

One row per (gated candidate, decision date) read. Nothing is dropped: a read with no score is a
row with `score_valid = False`, and a read whose vault has no fresh mark at all is a row too.
"""))
cells.append(code('''per_pair_reads = {}
for pair_id in gated_pair_ids:
    pair = strategy_universe.get_pair_by_id(pair_id)
    structure = STRUCTURES[pair_id]
    cached_raw = read_on(series_for(RAW_LEG, pair), READ_AT)
    cached_neff = read_on(series_for(NEFF_LEG, pair), READ_AT)
    cached_score = read_on(series_for(SORTINO_LEG, pair), READ_AT)
    weight_own = cached_neff / (cached_neff + EV_PRIOR_K)
    pre_clip = (weight_own * np.nan_to_num(cached_raw) +
                (1.0 - weight_own) * np.nan_to_num(prior_on_reads)) / EV_T_CAP
    pre_clip = np.where(np.isnan(cached_raw), np.nan, pre_clip)

    n = len(READ_AT)
    if structure is None:
        last_event_pos = np.full(n, -1)
        last_valid_pos = np.full(n, -1)
        down_at_last_event = np.full(n, np.nan)
        span_at_last_event = np.full(n, np.nan)
        events_at_last_event = np.full(n, np.nan)
        evidence_age = np.full(n, np.nan)
        span_at_valid = np.full(n, np.nan)
        events_at_valid = np.full(n, np.nan)
    else:
        last_event_pos = structure["events"].searchsorted(READ_AT, side="right") - 1
        safe = np.clip(last_event_pos, 0, None)
        has_event = last_event_pos >= 0
        last_valid_pos = np.where(has_event, structure["last_valid_pos"][safe], -1)
        safe_valid = np.clip(last_valid_pos, 0, None)
        down_at_last_event = np.where(has_event, structure["down_count"][safe], np.nan)
        span_at_last_event = np.where(has_event, structure["span_days"][safe], np.nan)
        events_at_last_event = np.where(has_event, structure["window_events"][safe], np.nan)
        span_at_valid = np.where(last_valid_pos >= 0, structure["span_days"][safe_valid], np.nan)
        events_at_valid = np.where(last_valid_pos >= 0, structure["window_events"][safe_valid], np.nan)
        valid_dates = structure["events"].to_numpy()[safe_valid]
        evidence_age = np.where(
            last_valid_pos >= 0,
            (READ_AT.to_numpy() - valid_dates) / np.timedelta64(1, "D"),
            np.nan,
        )

    per_pair_reads[pair_id] = pd.DataFrame({
        "read_at": READ_AT,
        "score": cached_score,
        "score_valid": ~np.isnan(cached_score),
        "pre_clip": pre_clip,
        "raw": cached_raw,
        "n_eff": cached_neff,
        "prior": prior_on_reads,
        # The event window the score was actually computed on (the last VALID one).
        "evidence_window_span_days": span_at_valid,
        "evidence_window_events": events_at_valid,
        "evidence_age_days": evidence_age,
        # The most recent event window at this read, valid or not.
        "latest_window_span_days": span_at_last_event,
        "latest_window_events": events_at_last_event,
        "latest_window_down_events": down_at_last_event,
        "latest_window_fails_down_mask": down_at_last_event < EV_MIN_DOWN,
        "has_any_event": last_event_pos >= 0,
        "latest_event_pos": last_event_pos,
        "evidence_event_pos": last_valid_pos,
    })

#: Which read positions each gated candidate appears at, so the long table is assembled with one
#: slice per candidate rather than a Python loop over every (candidate, date) pair.
gated_positions = {}
for i, ts in enumerate(SCHEDULE):
    for pair_id in gated_by_date[ts]:
        gated_positions.setdefault(pair_id, []).append(i)

pieces = []
for pair_id, positions in gated_positions.items():
    piece = per_pair_reads[pair_id].iloc[positions].copy()
    piece["decision_date"] = SCHEDULE[positions]
    piece["pair_id"] = pair_id
    piece["address"] = str(strategy_universe.get_pair_by_id(pair_id).pool_address).lower()
    pieces.append(piece)

audit = pd.concat(pieces, ignore_index=True).sort_values(["decision_date", "pair_id"], ignore_index=True)
audit["score_valid"] = audit["score_valid"].astype(bool)
audit["latest_window_fails_down_mask"] = audit["latest_window_fails_down_mask"].astype(bool)
assert len(audit) == int(pool_sizes.sum()), "the audit table lost or duplicated a gated read"
print(f"{len(audit):,} (candidate, date) reads.")
display(audit.head(8))
'''))

cells.append(md("""## 1. Score validity rate
"""))
cells.append(code('''validity = pd.DataFrame([{
    "reads": len(audit),
    "valid_reads": int(audit["score_valid"].sum()),
    "validity_rate": float(audit["score_valid"].mean()),
    "distinct_candidates": int(audit["pair_id"].nunique()),
    "candidates_ever_scored": int(audit.loc[audit["score_valid"], "pair_id"].nunique()),
    "candidates_never_scored": int(audit["pair_id"].nunique()
                                   - audit.loc[audit["score_valid"], "pair_id"].nunique()),
    "reads_with_no_fresh_event_at_all": int((~audit["has_any_event"]).sum()),
}]).T.rename(columns={0: "value"})
display(validity)

by_date = audit.groupby("decision_date").agg(
    gated=("pair_id", "size"), scored=("score_valid", "sum"))
by_date["validity_rate"] = by_date["scored"] / by_date["gated"]
print("Validity rate over time (quartiles of the per-date rate):")
display(by_date["validity_rate"].describe().to_frame().T)
print("Worst ten decision dates by validity rate:")
display(by_date.nsmallest(10, "validity_rate"))
SCORE_VALIDITY_RATE = float(audit["score_valid"].mean())
'''))

cells.append(md("""## 2. Elapsed calendar span of the event window

The replacement leg is described as a 90-event window. Those 90 mark events cover a different
number of **calendar days** for every vault, because vaults report at different densities. If the
dispersion across the cross-section is large, a rank comparison between two vaults' scores is a
comparison between two different horizons, and the heading must say so.
"""))
cells.append(code('''valid = audit[audit["score_valid"]]
span_summary = valid["evidence_window_span_days"].describe(
    percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_frame().T
display(span_summary)

per_candidate_span = valid.groupby("address").agg(
    reads=("evidence_window_span_days", "size"),
    median_span_days=("evidence_window_span_days", "median"),
    min_span_days=("evidence_window_span_days", "min"),
    max_span_days=("evidence_window_span_days", "max"),
    median_window_events=("evidence_window_events", "median"),
).sort_values("median_span_days")
print(f"Per-candidate median span across {len(per_candidate_span)} scored candidates:")
display(per_candidate_span["median_span_days"].describe(
    percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_frame().T)
print("Ten shortest and ten longest by median span:")
display(pd.concat([per_candidate_span.head(10), per_candidate_span.tail(10)]))

SPAN_MEDIAN = float(valid["evidence_window_span_days"].median())
SPAN_P05 = float(valid["evidence_window_span_days"].quantile(0.05))
SPAN_P95 = float(valid["evidence_window_span_days"].quantile(0.95))
SPAN_RATIO_P95_P05 = SPAN_P95 / SPAN_P05 if SPAN_P05 > 0 else float("nan")
CROSS_SECTION_SPAN_RATIO = (
    float(per_candidate_span["median_span_days"].max() / per_candidate_span["median_span_days"].min())
    if len(per_candidate_span) and float(per_candidate_span["median_span_days"].min()) > 0 else float("nan")
)
print(f"Read-level span: median {SPAN_MEDIAN:.0f} days, 5th-95th percentile "
      f"{SPAN_P05:.0f} to {SPAN_P95:.0f} days, ratio {SPAN_RATIO_P95_P05:.2f}x.")
print(f"Across candidates, the slowest-reporting vault's median window spans "
      f"{CROSS_SECTION_SPAN_RATIO:.2f}x the calendar time of the fastest-reporting vault's.")

figure = px.histogram(valid, x="evidence_window_span_days", nbins=60,
                      title="Calendar span of the event window behind each valid score read")
figure.update_layout(xaxis_title="calendar days covered by the event window", yaxis_title="reads")
figure.show()
'''))

cells.append(md("""## 3. Age of the last valid evidence at each read
"""))
cells.append(code('''age_summary = valid["evidence_age_days"].describe(
    percentiles=[0.5, 0.75, 0.9, 0.95, 0.99]).to_frame().T
display(age_summary)
EVIDENCE_AGE_MEDIAN = float(valid["evidence_age_days"].median())
EVIDENCE_AGE_P95 = float(valid["evidence_age_days"].quantile(0.95))
EVIDENCE_AGE_MAX = float(valid["evidence_age_days"].max())
STALE_30D_SHARE = float((valid["evidence_age_days"] > 30).mean())
STALE_90D_SHARE = float((valid["evidence_age_days"] > 90).mean())
print(f"Median evidence age {EVIDENCE_AGE_MEDIAN:.0f} days, 95th percentile {EVIDENCE_AGE_P95:.0f}, "
      f"maximum {EVIDENCE_AGE_MAX:.0f}.")
print(f"Reads whose score rests on evidence older than 30 days: {STALE_30D_SHARE:.2%}; "
      f"older than 90 days: {STALE_90D_SHARE:.2%}.")
'''))

cells.append(md("""## 4. The forward-fill audit

`_event_time_stats()` masks first and reindexes second:

```python
raw_sortino = raw_sortino.where(down_count >= int(min_down_events))
return raw_sortino.reindex(full_index).ffill(), n_eff.reindex(full_index).ffill()
```

So when the most recent event window has fewer than `evidence_min_down_events` down-events, the
score does not become NaN - it silently inherits the last window that passed. The effective
n behind it does not: `n_eff` is forward-filled **unmasked**, so a bridged read pairs an old
Sortino ratio with a current effective-n, and the shrinkage weight is computed from the wrong
sample. That mismatch is measured here too.

**Pre-registered trigger: more than 2% of (candidate, date) reads.** Above it, this notebook must
switch to an indicator chain that masks after the reindex.
"""))
cells.append(code('''bridged = audit["score_valid"] & audit["latest_window_fails_down_mask"]
FORWARD_FILL_SHARE = float(bridged.mean())
FORWARD_FILL_COUNT = int(bridged.sum())

#: The broader question - a valid score whose evidence is not the most recent event window, for
#: any reason - is reported beside it, but the pre-registered trigger is the down-count one.
stale_window = audit["score_valid"] & (audit["evidence_age_days"] > 0)
any_bridge = audit["score_valid"] & (audit["evidence_event_pos"] != audit["latest_event_pos"])

forward_fill = pd.DataFrame([
    {"measure": "reads", "count": len(audit), "share_of_reads": 1.0},
    {"measure": "valid score reads", "count": int(audit["score_valid"].sum()),
     "share_of_reads": float(audit["score_valid"].mean())},
    {"measure": "valid score whose LATEST event window fails the down-count mask "
                "(the pre-registered trigger)",
     "count": FORWARD_FILL_COUNT, "share_of_reads": FORWARD_FILL_SHARE},
    {"measure": "valid score carried from an older event window (any reason)",
     "count": int(any_bridge.sum()), "share_of_reads": float(any_bridge.mean())},
    {"measure": "valid score read on a calendar day that is not itself a mark event",
     "count": int(stale_window.sum()), "share_of_reads": float(stale_window.mean())},
]).set_index("measure")
display(forward_fill)

print(f"Forward-fill bridging of a down-count-mask failure: {FORWARD_FILL_COUNT:,} of "
      f"{len(audit):,} reads = {FORWARD_FILL_SHARE:.4%}. Trigger is {FORWARD_FILL_TRIGGER:.0%}.")
print(f"TRIGGERED = {FORWARD_FILL_SHARE > FORWARD_FILL_TRIGGER}")

if FORWARD_FILL_COUNT:
    print("Candidates most affected, and how stale the inherited evidence was:")
    affected = audit[bridged].groupby("address").agg(
        bridged_reads=("score", "size"),
        median_evidence_age_days=("evidence_age_days", "median"),
        max_evidence_age_days=("evidence_age_days", "max"),
        median_latest_down_events=("latest_window_down_events", "median"),
    )
    affected["reads_for_that_candidate"] = audit.groupby("address").size().reindex(affected.index)
    affected["share_of_that_candidates_reads"] = (
        affected["bridged_reads"] / affected["reads_for_that_candidate"])
    display(affected.sort_values("bridged_reads", ascending=False).head(15))
    print("The effective-n forward-filled beside a bridged Sortino ratio is UNMASKED, so a bridged "
          "read pairs an old ratio with a current n_eff and the shrinkage weight is computed from "
          "the wrong sample:")
    display(audit[bridged][["raw", "n_eff", "prior", "pre_clip", "score", "evidence_age_days",
                            "latest_window_down_events"]].describe())

assert (FORWARD_FILL_SHARE > FORWARD_FILL_TRIGGER) == USE_V2, (
    f"the measured forward-fill share is {FORWARD_FILL_SHARE:.4%} against a {FORWARD_FILL_TRIGGER:.0%} "
    f"trigger, but this notebook was built with USE_V2={USE_V2}. Set USE_V2 in _build/build_23.py "
    f"to {FORWARD_FILL_SHARE > FORWARD_FILL_TRIGGER} and rebuild; the sweep below must not run on "
    f"the wrong indicator chain."
)
print(f"Indicator chain decision confirmed: SELECTION_INDICATOR = {SELECTION_INDICATOR!r}.")
'''))

cells.append(md("""## 5. Clipping frequency at the [0, 1] cap

A score that saturates is a score that has stopped ranking. `pre_clip` is the shrunk, t-cap-scaled
value before `.clip(lower=0.0, upper=1.0)`; a read where it is at or below 0, or at or above 1,
carries no ordering information against any other saturated read.
"""))
cells.append(code('''clipped_low = valid["pre_clip"] <= 0.0
clipped_high = valid["pre_clip"] >= 1.0
CLIP_LOW_SHARE = float(clipped_low.mean())
CLIP_HIGH_SHARE = float(clipped_high.mean())
CLIP_ANY_SHARE = float((clipped_low | clipped_high).mean())

display(pd.DataFrame([
    {"bound": "pre-clip <= 0 (floored at 0)", "reads": int(clipped_low.sum()),
     "share_of_valid_reads": CLIP_LOW_SHARE},
    {"bound": "pre-clip >= 1 (capped at 1)", "reads": int(clipped_high.sum()),
     "share_of_valid_reads": CLIP_HIGH_SHARE},
    {"bound": "either bound", "reads": int((clipped_low | clipped_high).sum()),
     "share_of_valid_reads": CLIP_ANY_SHARE},
]).set_index("bound"))

print("Distribution of the unclipped score:")
display(valid["pre_clip"].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).to_frame().T)

figure = px.histogram(valid, x="score", nbins=50,
                      title="Distribution of the clipped replacement Sortino leg across all valid reads")
figure.update_layout(xaxis_title=SORTINO_LEG, yaxis_title="reads")
figure.show()
'''))

cells.append(md("""## The chain the backtests actually select on

Everything above audits the shipped `sortino_shrunk_score` from `blocks_evidence.py`, which is
the thing under audit. If the forward-fill trigger fired, the runs below select on a `_v2` chain
defined in `blocks_stability.py` that applies the down-count mask **after** the reindex, so an
invalidated window becomes NaN instead of inheriting an older valid score. `blocks_evidence.py`
is not edited: the shipped chain still exists and still behaves exactly as NB14-NB19 saw it.

The same five measurements are repeated on the chain actually used, so the swap's own inputs are
audited and not only the ones it was derived from.
"""))
cells.append(code('''if not USE_V2:
    print(f"The forward-fill trigger did not fire, so the runs select on "
          f"{SELECTION_INDICATOR!r}, whose Sortino leg is the audited {SORTINO_LEG!r}. "
          f"Nothing further to compare.")
    V2_COMPARISON = None
else:
    v2_rows = []
    for pair_id, positions in gated_positions.items():
        pair = strategy_universe.get_pair_by_id(pair_id)
        v2_score = read_on(series_for(V2_SORTINO_LEG, pair), READ_AT)[positions]
        v2_rows.append(pd.DataFrame({"pair_id": pair_id, "v2_score": v2_score}))
    v2_frame = pd.concat(v2_rows, ignore_index=True)
    #: `audit` was sorted by (decision_date, pair_id) after assembly, so the v2 column is joined
    #: on the same per-candidate slices rather than positionally.
    v2_index = pd.concat([
        pd.DataFrame({"pair_id": pair_id, "decision_date": SCHEDULE[positions]})
        for pair_id, positions in gated_positions.items()
    ], ignore_index=True)
    v2_frame["decision_date"] = v2_index["decision_date"].to_numpy()
    merged = audit.merge(v2_frame, on=["pair_id", "decision_date"], how="left", validate="one_to_one")
    assert len(merged) == len(audit), "the v2 join changed the number of reads"

    v2_valid = merged["v2_score"].notna()
    V2_VALIDITY_RATE = float(v2_valid.mean())
    v2_bridged = v2_valid & merged["latest_window_fails_down_mask"]
    V2_FORWARD_FILL_SHARE = float(v2_bridged.mean())
    V2_COMPARISON = pd.DataFrame([
        {"measure": "score validity rate", "shipped chain": SCORE_VALIDITY_RATE,
         "chain in use (_v2)": V2_VALIDITY_RATE},
        {"measure": "reads bridging a down-count-mask failure",
         "shipped chain": FORWARD_FILL_SHARE, "chain in use (_v2)": V2_FORWARD_FILL_SHARE},
        {"measure": "reads clipped at either bound (share of that chain's valid reads)",
         "shipped chain": CLIP_ANY_SHARE,
         "chain in use (_v2)": float(((merged.loc[v2_valid, "v2_score"] <= 0.0)
                                      | (merged.loc[v2_valid, "v2_score"] >= 1.0)).mean())},
    ]).set_index("measure")
    display(V2_COMPARISON)
    assert V2_FORWARD_FILL_SHARE == 0.0, (
        f"the _v2 chain still bridges {V2_FORWARD_FILL_SHARE:.4%} of reads; masking after the "
        f"reindex did not do what it was added to do"
    )
    print(f"The runs below select on {SELECTION_INDICATOR!r}. Validity falls from "
          f"{SCORE_VALIDITY_RATE:.4f} to {V2_VALIDITY_RATE:.4f} because the reads the shipped "
          f"chain bridged are now correctly NaN, which is the intended effect and not a "
          f"degradation.")
'''))

# ---------------------------------------------------------------------------------------------
# 3. Stage 1b - identity diagnostic
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Stage 1b - identity diagnostic: does the swap change the book at all?

The swap keeps the incumbent's CAGR leg, its weight, its momentum gate, its sizing and its hold
rules. If the replacement Sortino leg re-orders nothing that reaches the top six, the sweep below
has no information value at all and this notebook stops here with DIAGNOSTIC.

The comparison is on **realised** weights, from `state.stats.positions` (position value at each
statistics timestamp) divided by `state.stats.portfolio` total equity at the same timestamp - not
on target weights, which can differ without a single trade changing.

**Gate, pre-registered.** The book identical on every date: STOP, DIAGNOSTIC, the swap is a
mechanical replication of the anchor. The book different on 10% or fewer of dates: STOP, the
mechanism is too inert to test at these settings. Above 10%: the sweep runs.
"""))
cells.append(code('''centre = run_and_record(
    "swap__centre", "candidate",
    selection_score_indicator=SELECTION_INDICATOR,
    require_scored_candidates=False,
)
display(pd.DataFrame([anchor_panel, centre["panel"]]).set_index("label")[
    ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
     "max_dd", "late_cagr", "late_ulcer"]])
'''))

cells.append(code('''def realised_weight_book(state_) -> dict:
    """`{statistics timestamp: {pool address: share of total equity}}`, from the run's own stats."""
    equity_by_ts = {
        pd.Timestamp(s.calculated_at): float(s.total_equity)
        for s in state_.stats.portfolio if s.total_equity
    }
    book = {}
    for position_id, stat_list in state_.stats.positions.items():
        position = state_.portfolio.get_position_by_id(position_id)
        if position.is_credit_supply():
            continue
        address = str(position.pair.pool_address).lower()
        for s in stat_list:
            ts = pd.Timestamp(s.calculated_at)
            equity = equity_by_ts.get(ts)
            if not equity:
                continue
            value = float(s.value or 0.0)
            if value == 0.0:
                continue
            book.setdefault(ts, {})
            book[ts][address] = book[ts].get(address, 0.0) + value / equity
    return book


def turnover_by_cycle(state_) -> dict:
    """`{cycle timestamp: traded USD value}` from `TradeExecution.get_value()`."""
    out = {}
    for trade in state_.portfolio.get_all_trades():
        if trade.pair.is_credit_supply() or not trade.is_success():
            continue
        ts = pd.Timestamp(trade.executed_at or trade.opened_at)
        out[ts] = out.get(ts, 0.0) + float(trade.get_value() or 0.0)
    return out


def equity_by_timestamp(state_) -> pd.Series:
    return pd.Series({
        pd.Timestamp(s.calculated_at): float(s.total_equity)
        for s in state_.stats.portfolio if s.total_equity
    }).sort_index()


anchor_book = realised_weight_book(anchor_state)
centre_book = realised_weight_book(centre["state"])
anchor_turnover = turnover_by_cycle(anchor_state)
centre_turnover = turnover_by_cycle(centre["state"])
anchor_equity_ts = equity_by_timestamp(anchor_state)
centre_equity_ts = equity_by_timestamp(centre["state"])

#: Turnover is recorded at execution time, which can land on the cycle timestamp or immediately
#: after it; it is snapped back to the decision date that produced it so the two runs' cycles line
#: up. Anything outside the schedule window is counted and reported, never dropped.
def turnover_on_schedule(turnover: dict) -> pd.Series:
    out = {}
    unassigned = 0.0
    for ts, value in turnover.items():
        position = SCHEDULE.searchsorted(ts, side="right") - 1
        if position < 0:
            unassigned += value
            continue
        out[SCHEDULE[position]] = out.get(SCHEDULE[position], 0.0) + value
    if unassigned:
        print(f"  {unassigned:,.0f} USD of traded value fell before the first decision date and is "
              f"reported here rather than silently dropped.")
    return pd.Series(out).reindex(SCHEDULE).fillna(0.0)


anchor_turnover_series = turnover_on_schedule(anchor_turnover)
centre_turnover_series = turnover_on_schedule(centre_turnover)
print(f"Anchor statistics timestamps: {len(anchor_book)}; candidate: {len(centre_book)}; "
      f"decision schedule: {len(SCHEDULE)}.")
'''))

cells.append(code('''compare_rows = []
for ts in SCHEDULE:
    a = anchor_book.get(ts, {})
    b = centre_book.get(ts, {})
    addresses = set(a) | set(b)
    l1 = sum(abs(a.get(x, 0.0) - b.get(x, 0.0)) for x in addresses)
    held_a, held_b = set(a), set(b)
    symmetric = held_a ^ held_b
    anchor_equity_here = float(anchor_equity_ts.get(ts, np.nan))
    centre_equity_here = float(centre_equity_ts.get(ts, np.nan))
    compare_rows.append({
        "decision_date": ts,
        "anchor_holdings": len(held_a),
        "candidate_holdings": len(held_b),
        "book_differs": bool(symmetric),
        "symmetric_difference": len(symmetric),
        "l1_realised_weight_distance": l1,
        "anchor_only": ",".join(sorted(held_a - held_b)),
        "candidate_only": ",".join(sorted(held_b - held_a)),
        "anchor_turnover_usd": float(anchor_turnover_series.get(ts, 0.0)),
        "candidate_turnover_usd": float(centre_turnover_series.get(ts, 0.0)),
        "anchor_turnover_frac": (float(anchor_turnover_series.get(ts, 0.0)) / anchor_equity_here
                                 if anchor_equity_here == anchor_equity_here and anchor_equity_here else np.nan),
        "candidate_turnover_frac": (float(centre_turnover_series.get(ts, 0.0)) / centre_equity_here
                                    if centre_equity_here == centre_equity_here and centre_equity_here else np.nan),
    })

compare = pd.DataFrame(compare_rows).set_index("decision_date")
assert np.isfinite(compare["l1_realised_weight_distance"]).all(), \\
    "a realised-weight L1 distance is not finite; the statistics read is wrong"
display(compare.head(12))
print("Last twelve decision dates:")
display(compare.tail(12))
'''))

cells.append(code('''BOOK_CHANGE_SHARE = float(compare["book_differs"].mean())
MEAN_L1 = float(compare["l1_realised_weight_distance"].mean())
MEDIAN_L1 = float(compare["l1_realised_weight_distance"].median())
MAX_L1 = float(compare["l1_realised_weight_distance"].max())
MEAN_SYMMETRIC = float(compare["symmetric_difference"].mean())

identity = pd.DataFrame([
    {"measure": "decision dates", "value": float(len(compare))},
    {"measure": "dates on which the traded book differs", "value": float(compare["book_differs"].sum())},
    {"measure": "share of dates on which the traded book differs", "value": BOOK_CHANGE_SHARE},
    {"measure": "mean realised-weight L1 distance", "value": MEAN_L1},
    {"measure": "median realised-weight L1 distance", "value": MEDIAN_L1},
    {"measure": "maximum realised-weight L1 distance", "value": MAX_L1},
    {"measure": "mean size of the holdings symmetric difference", "value": MEAN_SYMMETRIC},
    {"measure": "anchor total turnover, USD", "value": float(anchor_turnover_series.sum())},
    {"measure": "candidate total turnover, USD", "value": float(centre_turnover_series.sum())},
    {"measure": "distinct addresses the candidate held and the anchor never did",
     "value": float(len({a for row in compare["candidate_only"] for a in row.split(",") if a}
                        - {a for row in compare["anchor_only"] for a in row.split(",") if a}))},
]).set_index("measure")
display(identity)

figure = px.line(compare.reset_index(), x="decision_date", y="l1_realised_weight_distance",
                 title="Realised-weight L1 distance between the swap and the anchor, per decision date")
figure.update_layout(yaxis_title="L1 distance (sum of |weight differences|)")
figure.show()
'''))

cells.append(md("""## What the changed holdings did during the anchor's five largest drawdowns

Drawdown episodes are peak-to-recovery segments of the anchor's own equity curve. For the five
deepest: how far apart the two books were, and the approximate mark-to-market contribution of the
positions each run held and the other did not. The contribution is the change in each position's
`profit_usd` statistic over the window, summed per address, so it is a mark-to-market attribution
and not a realised-P&L accounting - stated rather than implied.
"""))
cells.append(code('''def drawdown_episodes(equity_: pd.Series) -> pd.DataFrame:
    """Peak-to-recovery drawdown segments, deepest first."""
    dd = equity_ / equity_.cummax() - 1.0
    episodes, start, trough_value, trough_at = [], None, 0.0, None
    for ts, value in dd.items():
        if value == 0.0:
            if start is not None:
                episodes.append({"start": start, "trough_at": trough_at, "end": ts, "depth": trough_value})
            start, trough_value, trough_at = ts, 0.0, ts
        else:
            if start is None:
                start = ts
            if value < trough_value:
                trough_value, trough_at = value, ts
    if start is not None and trough_value < 0.0:
        episodes.append({"start": start, "trough_at": trough_at, "end": dd.index[-1], "depth": trough_value})
    frame = pd.DataFrame(episodes)
    if not len(frame):
        return frame
    frame = frame[frame["depth"] < 0.0]
    return frame.sort_values("depth").reset_index(drop=True)


def profit_delta_by_address(state_, start, end) -> dict:
    """Change in each address's summed position `profit_usd` statistic over `[start, end]`."""
    out = {}
    for position_id, stat_list in state_.stats.positions.items():
        position = state_.portfolio.get_position_by_id(position_id)
        if position.is_credit_supply():
            continue
        address = str(position.pair.pool_address).lower()
        inside = [s for s in stat_list if start <= pd.Timestamp(s.calculated_at) <= end]
        if len(inside) < 2:
            continue
        out[address] = out.get(address, 0.0) + float(inside[-1].profit_usd or 0.0) - float(inside[0].profit_usd or 0.0)
    return out


episodes = drawdown_episodes(anchor_equity)
print(f"{len(episodes)} drawdown episodes in the anchor's equity curve.")
episode_rows = []
for _, episode in episodes.head(5).iterrows():
    start, end = pd.Timestamp(episode["start"]), pd.Timestamp(episode["end"])
    window = compare.loc[(compare.index >= start) & (compare.index <= end)]
    anchor_only = {a for row in window["anchor_only"] for a in row.split(",") if a}
    candidate_only = {a for row in window["candidate_only"] for a in row.split(",") if a}
    anchor_profit = profit_delta_by_address(anchor_state, start, end)
    centre_profit = profit_delta_by_address(centre["state"], start, end)
    anchor_equity_change = float(anchor_equity.asof(end) / anchor_equity.asof(start) - 1.0)
    centre_equity_curve = centre["equity"]
    centre_equity_change = float(centre_equity_curve.asof(end) / centre_equity_curve.asof(start) - 1.0)
    episode_rows.append({
        "start": start.date(), "trough_at": pd.Timestamp(episode["trough_at"]).date(), "end": end.date(),
        "anchor_depth": float(episode["depth"]),
        "anchor_equity_change": anchor_equity_change,
        "candidate_equity_change": centre_equity_change,
        "decision_dates_in_window": len(window),
        "dates_book_differed": int(window["book_differs"].sum()),
        "mean_l1": float(window["l1_realised_weight_distance"].mean()) if len(window) else float("nan"),
        "anchor_only_addresses": len(anchor_only),
        "candidate_only_addresses": len(candidate_only),
        "anchor_only_mtm_usd": float(sum(anchor_profit.get(a, 0.0) for a in anchor_only)),
        "candidate_only_mtm_usd": float(sum(centre_profit.get(a, 0.0) for a in candidate_only)),
    })

drawdown_attribution = pd.DataFrame(episode_rows)
display(drawdown_attribution)
'''))

cells.append(md("""## The gate

Printed in code, not asserted in prose.
"""))
cells.append(code('''GATE_MINIMUM_SHARE = 0.10   # pre-registered in 20-stability-leads-plan.md, NB23 stage 2

print(f"Share of decision dates on which the traded book differs: {BOOK_CHANGE_SHARE:.4f} "
      f"({int(compare['book_differs'].sum())} of {len(compare)} dates).")
print(f"Pre-registered gate: the sweep runs only if this exceeds {GATE_MINIMUM_SHARE:.2f}.")

if BOOK_CHANGE_SHARE == 0.0:
    STAGE2_RUN = False
    GATE_DECISION = ("STOP - DIAGNOSTIC. The traded book is identical on every decision date, so "
                     "the swap is a mechanical replication of the anchor and the sweep has no "
                     "information value.")
elif BOOK_CHANGE_SHARE <= GATE_MINIMUM_SHARE:
    STAGE2_RUN = False
    GATE_DECISION = (f"STOP - DIAGNOSTIC. The traded book differs on only {BOOK_CHANGE_SHARE:.2%} of "
                     f"decision dates, at or below the pre-registered {GATE_MINIMUM_SHARE:.0%} gate. "
                     f"The mechanism is too inert to test at these settings.")
else:
    STAGE2_RUN = True
    GATE_DECISION = (f"PROCEED. The traded book differs on {BOOK_CHANGE_SHARE:.2%} of decision dates, "
                     f"above the pre-registered {GATE_MINIMUM_SHARE:.0%} gate, so the sweep runs.")

print(f"GATE DECISION: {GATE_DECISION}")
family = None
'''))

# ---------------------------------------------------------------------------------------------
# 4. Stage 2 - sweep
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Stage 2 - local sensitivity sweep

Ten neighbours, one parameter moved at a time from the centre, plus one **policy alternative**
(`require_scored_candidates=True`, strict admission), which is reported BESIDE the plateau and is
never part of it. `cagr_weight` carries an upper neighbour at 0.7 as well as a lower one at 0.5:
an earlier search boundary is not an economic reason to exclude the upside.

Then `build_family()` - the twelve-member volatility-matched drop family, N = 5 to 60 in steps of
5 - which is this plan's constraint-7 comparator: the best observed control at or below the
candidate's own volatility, plus a 0.10 Sharpe complexity premium. That asymmetry is deliberate.
A re-ranked composite is an additional mechanism, so it has to beat the best simple de-risking
that took no more risk than it did, by a margin.
"""))
cells.append(code('''NEIGHBOURS = [
    ("cagr_weight_0.5", dict(cagr_weight=0.5)),
    ("cagr_weight_0.7", dict(cagr_weight=0.7)),
    ("t_cap_2", dict(evidence_t_cap=2.0)),
    ("t_cap_4", dict(evidence_t_cap=4.0)),
    ("prior_30", dict(evidence_prior_strength=30)),
    ("prior_90", dict(evidence_prior_strength=90)),
    ("min_events_10", dict(evidence_min_events=10)),
    ("min_events_30", dict(evidence_min_events=30)),
    ("max_events_60", dict(evidence_max_events=60)),
    ("max_events_120", dict(evidence_max_events=120)),
]
NEIGHBOUR_LABELS = [f"swap__{label}" for label, _ in NEIGHBOURS]
POLICY_LABEL = "swap__require_scored"

common = dict(selection_score_indicator=SELECTION_INDICATOR)

if not STAGE2_RUN:
    print("Stage 2 skipped by the gate above. No sweep run, no family run, no leave-one-vault-out.")
    print(GATE_DECISION)
else:
    for label, override in NEIGHBOURS:
        run_and_record(f"swap__{label}", "candidate", **{**common, **override})
    run_and_record(POLICY_LABEL, "policy", **{**common, "require_scored_candidates": True})
    print(f"{len(NEIGHBOURS)} neighbours plus the strict-admission policy alternative recorded.")
'''))

cells.append(code('''if STAGE2_RUN:
    family = build_family()
    display(family[["drop_n", "cagr", "cycle_vol", "cycle_sharpe", "ulcer", "abs_invested_beta",
                    "mean_invested", "late_cagr", "late_ulcer"]])
else:
    print("Stage 2 skipped by the gate: the constraint-7 comparator family was not run.")
'''))

cells.append(md("""## Reference values from the previous plan

The anchor, `drop_30` and `drop_50` on this same configuration, from NB15/NB19. If these do not
reproduce, the data snapshot moved under the track and nothing here is comparable with NB15-NB21.
Displayed rather than asserted: they are a sanity check on the snapshot, not an adoption gate.
"""))
cells.append(code('''REFERENCE_FROM_PREVIOUS_PLAN = {
    "anchor": (0.378971, 2.159792),
    "drop_30": (0.489942, 2.747391),
    "drop_50": (0.206149, 2.014857),
}
reference_rows = []
for label, (expected_cagr, expected_sharpe) in REFERENCE_FROM_PREVIOUS_PLAN.items():
    entry = run_by_label.get(label)
    if entry is None:
        reference_rows.append({"label": label, "expected_cagr": expected_cagr,
                               "actual_cagr": float("nan"), "cagr_abs_diff": float("nan"),
                               "expected_cycle_sharpe": expected_sharpe,
                               "actual_cycle_sharpe": float("nan"), "sharpe_abs_diff": float("nan"),
                               "reproduced": False})
        continue
    row = entry["panel"]
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
REFERENCE_REPRODUCED = bool(reference_check["reproduced"].all())
print(f"Every previous-plan reference value reproduced: {REFERENCE_REPRODUCED}")
if not STAGE2_RUN:
    print("Only the anchor could be checked; the family was not run because the gate stopped the "
          "notebook, so drop_30 and drop_50 show as not reproduced (absent, not wrong).")
'''))

# ---------------------------------------------------------------------------------------------
# 5. Verdict table
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Verdict table

Adoption rule v3: CAGR >= 20%; cycle Sharpe >= anchor - 0.10; cycle volatility <= anchor; ulcer
<= 0.85 x anchor; invested-basket beta < anchor; mean invested >= 0.90; and cycle Sharpe >= the
best observed control at or below this row's own volatility, plus 0.10.

The `failed` column carries the **complete** failure set for every row and is never truncated
(`harness_evidence.py` sets `display.max_colwidth = None`). A row that failed four constraints is
reported as failing four.
"""))
cells.append(code('''VERDICT_COLUMNS = [
    "family", "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested",
    "cagr_sacrifice_pp", "control_ref", "passes_v3", "failed", "late_ok",
]
if STAGE2_RUN:
    verdict = verdict_table_v3(family=family)
    display(verdict[VERDICT_COLUMNS])
else:
    #: The gate stopped the notebook before the comparator family was run, so constraint 7 cannot
    #: be evaluated at all. Constraints 1-6 are still shown, labelled as such, rather than a
    #: `passes_v3` column that would silently mean "1-6 only".
    verdict = verdict_table_v3(family=None, skip_placebo=True)
    display(verdict[[c if c != "passes_v3" else "passes_1_to_6" for c in VERDICT_COLUMNS]])
    print("Constraint 7 was NOT evaluated: the notebook stopped at the stage-1b gate and the "
          "observed-control family was never run. This table reports constraints 1-6 only.")
'''))

# ---------------------------------------------------------------------------------------------
# 6. Plateau
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Plateau

All ten neighbours as separate Boolean columns. A neighbour passes only if it clears all seven
constraints **and** the late period. `swap__require_scored` is a **policy alternative**, reported
beside the plateau and never counted in it: strict admission changes who may be a candidate at
all, which is a different decision from moving a dial on the score.
"""))
cells.append(code('''def row_ok(label: str) -> bool:
    """All seven constraints and the late period for one recorded run. Missing run -> False."""
    entry = run_by_label.get(label)
    if entry is None or family is None:
        return False
    row = entry["panel"]
    return bool(passes_constraints_v3(row, anchor_panel, family)
                and late_period_ok_v3(row, anchor_panel))


def row_failure(label: str) -> str:
    entry = run_by_label.get(label)
    if entry is None:
        return "run absent"
    if family is None:
        return "comparator family absent (constraint 7 not evaluable)"
    failed = failing_constraints_v3(entry["panel"], anchor_panel, family)
    if not late_period_ok_v3(entry["panel"], anchor_panel):
        failed = (failed + ", " if failed else "") + "late period"
    return failed


plateau_record = {"centre": row_ok("swap__centre")}
for label in NEIGHBOUR_LABELS:
    plateau_record[label.replace("swap__", "")] = row_ok(label)
plateau_record["plateau_ok"] = bool(all(plateau_record.values()))
PLATEAU_OK = plateau_record["plateau_ok"]
display(pd.DataFrame([plateau_record]).T.rename(columns={0: "passes v3 and late period"}))

plateau_detail = pd.DataFrame([
    {"label": label, "passes": row_ok(label), "failed": row_failure(label)}
    for label in ["swap__centre"] + NEIGHBOUR_LABELS
]).set_index("label")
display(plateau_detail)
print(f"plateau_ok = {PLATEAU_OK}")

policy_row = pd.DataFrame([{
    "label": POLICY_LABEL,
    "role": "policy alternative, reported BESIDE the plateau and not part of it",
    "passes": row_ok(POLICY_LABEL),
    "failed": row_failure(POLICY_LABEL),
}]).set_index("label")
display(policy_row)
'''))

# ---------------------------------------------------------------------------------------------
# 7. Leave-one-vault-out
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Leave-one-vault-out

Only if the centre and the whole plateau pass. The vault with the largest total P&L in the
centre run is masked from the first cycle and the whole backtest is re-simulated, so substitution
actually happens rather than the vault's realised profit merely being subtracted afterwards. A
robustness run that was never executed can never produce a passing flag.
"""))
cells.append(code('''LOVO_LABEL = "swap__centre__without_top_vault"
LOVO_OK = False
MASKED_VAULT = None

if not STAGE2_RUN:
    print("Skipped: the notebook stopped at the stage-1b gate.")
elif not row_ok("swap__centre"):
    print(f"Skipped: the centre does not pass. Complete failure set: {row_failure('swap__centre')}")
elif not PLATEAU_OK:
    print("Skipped: the plateau does not hold. Per-neighbour failure sets are in the table above.")
else:
    MASKED_VAULT = largest_contributing_vault(run_by_label["swap__centre"]["state"])
    run_and_record(LOVO_LABEL, "robustness", **common, masked={MASKED_VAULT})
    LOVO_OK = row_ok(LOVO_LABEL)
    display(pd.DataFrame([{
        "label": LOVO_LABEL, "masked_vault": MASKED_VAULT,
        "cagr": float(run_by_label[LOVO_LABEL]["panel"]["cagr"]),
        "cycle_sharpe": float(run_by_label[LOVO_LABEL]["panel"]["cycle_sharpe"]),
        "passes": LOVO_OK, "failed": row_failure(LOVO_LABEL),
    }]).set_index("label"))

print(f"leave_one_vault_out_ok = {LOVO_OK} (masked vault: {MASKED_VAULT})")
'''))

# ---------------------------------------------------------------------------------------------
# 8. Bootstrap margins
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Bootstrap margins on the decision that matters

Paired block-bootstrap intervals of the cycle-Sharpe difference, with common block indices across
the aligned return matrix so every draw compares both strategies on the same market days. Block
lengths 5, 10 and 20. Against the anchor the boundary is **-0.10** (the Sharpe non-inferiority
tolerance); against the observed control actually used by constraint 7 it is **+0.10** (the
complexity premium). The interval either clears the boundary or it does not.
"""))
cells.append(code('''if STAGE2_RUN:
    display(bootstrap_margin_table("swap__centre", family))
else:
    print("The comparator family was not run, so only the anchor boundary is available.")
    display(bootstrap_margin_table("swap__centre", None))
'''))

cells.append(md("""# Equity curves
"""))
cells.append(code('''import plotly.graph_objects as go

figure = go.Figure()
figure.add_trace(go.Scatter(x=anchor_equity.index, y=anchor_equity.values, mode="lines",
                            name="anchor", line=dict(color="black", width=2)))
figure.add_trace(go.Scatter(x=centre["equity"].index, y=centre["equity"].values, mode="lines",
                            name="swap__centre", line=dict(color="crimson", width=2)))
if STAGE2_RUN:
    for label in NEIGHBOUR_LABELS:
        curve = run_by_label[label]["equity"]
        figure.add_trace(go.Scatter(x=curve.index, y=curve.values, mode="lines", name=label,
                                    opacity=0.45))
for name, x in (("regime break", "2026-04-01"), ("late period start", "2026-07-01")):
    figure.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, xref="x", yref="paper",
                     line=dict(dash="dot", color="grey"))
    figure.add_annotation(x=x, y=1, yref="paper", text=name, showarrow=False, yanchor="bottom")
figure.update_layout(title="The anchor, the Sortino-leg swap and its plateau neighbours",
                     yaxis_type="log", yaxis_title="equity (USD, log)")
figure.show()
'''))

# ---------------------------------------------------------------------------------------------
# 9. Verdict
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Verdict

ADOPT - which means **admission to the prospective shadow protocol of NB24, not authorisation to
deploy capital** - only if the centre passes all seven constraints and the late period, all ten
plateau neighbours pass all seven and the late period, and leave-one-vault-out passes. Otherwise
REJECT, with the complete failure set for every row. If the notebook stopped at the stage-1b gate
the verdict is DIAGNOSTIC.

A near-anchor replication that fails **only** the 15% ulcer reduction is reported as exactly
that, and not as a generic failure.
"""))
cells.append(code('''CENTRE_OK = row_ok("swap__centre")
CENTRE_FAILED = row_failure("swap__centre")

if not STAGE2_RUN:
    VERDICT = "DIAGNOSTIC"
    VERDICT_REASON = GATE_DECISION
elif CENTRE_OK and PLATEAU_OK and LOVO_OK:
    VERDICT = "ADOPT"
    VERDICT_REASON = ("The centre, all ten plateau neighbours and the leave-one-vault-out "
                      "re-simulation pass all seven constraints and the late period. ADOPT here "
                      "means admission to the NB24 prospective shadow protocol, NOT authorisation "
                      "to deploy capital.")
else:
    VERDICT = "REJECT"
    parts = []
    if not CENTRE_OK:
        parts.append(f"the centre fails: {CENTRE_FAILED}")
    if not PLATEAU_OK:
        failing = [l for l in NEIGHBOUR_LABELS if not row_ok(l)]
        parts.append(f"{len(failing)} of {len(NEIGHBOUR_LABELS)} plateau neighbours fail")
    if not LOVO_OK:
        parts.append("leave-one-vault-out did not pass (absent counts as a fail)")
    VERDICT_REASON = "; ".join(parts)

NEAR_ANCHOR_ULCER_ONLY = bool(CENTRE_FAILED == "ulcer (not material)")
print(f"VERDICT: {VERDICT}")
print(f"Reason: {VERDICT_REASON}")
print(f"Centre complete failure set: {CENTRE_FAILED or '(all evaluated constraints pass)'}")
if NEAR_ANCHOR_ULCER_ONLY:
    print("The centre is a near-anchor replication that fails ONLY the 15% ulcer-reduction "
          "requirement. That is the precise result and it is not a generic failure.")

failure_sets = pd.DataFrame([
    {"label": entry["label"], "family": entry["family"], "passes": row_ok(entry["label"]),
     "failed": row_failure(entry["label"])}
    for entry in runs
]).set_index("label")
print("The complete failure set for every recorded run:")
display(failure_sets)
'''))

# ---------------------------------------------------------------------------------------------
# 10. Frozen manifest
# ---------------------------------------------------------------------------------------------
cells.append(md("""# Frozen manifest

What NB24 loads. It reproduces every gate from these numbers rather than trusting this notebook's
verdict word, so the stage-1 measurements, the indicator chain actually used, the gate decision,
the plateau Booleans and the full-precision cycle Sharpe and CAGR of every run are all frozen
here.
"""))
cells.append(code('''import json
from pathlib import Path

MANIFEST_PATH = Path("_build/manifest_23.json")

manifest = {
    "notebook": "23-backtest-sortino-leg-swap.ipynb",
    "plan": "20-stability-leads-plan.md",
    "lead": "3 - the incumbent composite with only its Sortino leg swapped",
    "mechanism": ("component replacement: the incumbent 360-day cagr_score leg is untouched and "
                  "the 45-day rolling sortino_score leg is replaced by the event-time, shrunk "
                  "sortino_shrunk_score. Horizon, shrinkage, scaling, saturation and NaN "
                  "behaviour all change at once; it is not an isolated test of any one of them. "
                  "It cannot reach vaults younger than 360 days because the CAGR leg is unchanged."),
    "verdict": VERDICT,
    "verdict_reason": VERDICT_REASON,
    "indicator_chain": {
        "selection_score_indicator": SELECTION_INDICATOR,
        "sortino_leg": SORTINO_LEG,
        "used_v2_chain": bool(USE_V2),
        "v2_rationale": ("the _v2 chain masks the down-count failure AFTER the reindex, so an "
                         "invalidated event window becomes NaN instead of inheriting an older "
                         "valid score through the forward fill"),
    },
    "stage_1a": {
        "reads": int(len(audit)),
        "decision_dates": int(len(SCHEDULE)),
        "distinct_gated_candidates": int(audit["pair_id"].nunique()),
        "score_validity_rate": SCORE_VALIDITY_RATE,
        "event_window_span_days_median": SPAN_MEDIAN,
        "event_window_span_days_p05": SPAN_P05,
        "event_window_span_days_p95": SPAN_P95,
        "event_window_span_p95_over_p05": SPAN_RATIO_P95_P05,
        "cross_section_median_span_ratio_max_over_min": CROSS_SECTION_SPAN_RATIO,
        "evidence_age_days_median": EVIDENCE_AGE_MEDIAN,
        "evidence_age_days_p95": EVIDENCE_AGE_P95,
        "evidence_age_days_max": EVIDENCE_AGE_MAX,
        "evidence_older_than_30d_share": STALE_30D_SHARE,
        "evidence_older_than_90d_share": STALE_90D_SHARE,
        "forward_fill_bridged_share": FORWARD_FILL_SHARE,
        "forward_fill_bridged_count": FORWARD_FILL_COUNT,
        "forward_fill_trigger": FORWARD_FILL_TRIGGER,
        "forward_fill_triggered": bool(FORWARD_FILL_SHARE > FORWARD_FILL_TRIGGER),
        "clip_low_share_of_valid_reads": CLIP_LOW_SHARE,
        "clip_high_share_of_valid_reads": CLIP_HIGH_SHARE,
        "clip_any_share_of_valid_reads": CLIP_ANY_SHARE,
    },
    "stage_1b": {
        "book_change_share": BOOK_CHANGE_SHARE,
        "dates_book_differs": int(compare["book_differs"].sum()),
        "decision_dates": int(len(compare)),
        "mean_l1_realised_weight_distance": MEAN_L1,
        "median_l1_realised_weight_distance": MEDIAN_L1,
        "max_l1_realised_weight_distance": MAX_L1,
        "mean_symmetric_difference": MEAN_SYMMETRIC,
        "gate_minimum_share": GATE_MINIMUM_SHARE,
        "gate_decision": GATE_DECISION,
        "stage_2_ran": bool(STAGE2_RUN),
        "drawdown_attribution": json.loads(drawdown_attribution.to_json(orient="records")),
    },
    "plateau": {k: bool(v) for k, v in plateau_record.items()},
    "policy_alternative": {
        "label": POLICY_LABEL,
        "reported_beside_the_plateau_not_part_of_it": True,
        "passes": bool(row_ok(POLICY_LABEL)),
        "failed": row_failure(POLICY_LABEL),
    },
    "centre": {
        "label": "swap__centre",
        "passes_v3_and_late": bool(CENTRE_OK),
        "failed": CENTRE_FAILED,
        "fails_only_the_ulcer_reduction": NEAR_ANCHOR_ULCER_ONLY,
    },
    "leave_one_vault_out": {
        "label": LOVO_LABEL, "executed": LOVO_LABEL in run_by_label,
        "masked_vault": MASKED_VAULT, "passes": bool(LOVO_OK),
        "failed": row_failure(LOVO_LABEL) if LOVO_LABEL in run_by_label else "run absent",
    },
    "previous_plan_reference_reproduced": bool(REFERENCE_REPRODUCED),
    "baseline_parity": {metric: float(anchor_panel[metric]) for metric in BASELINE},
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
            "passes": bool(row_ok(entry["label"])),
            "failed": row_failure(entry["label"]),
        }
        for entry in runs
    },
}

MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=False))
print(json.dumps(manifest, indent=1, sort_keys=False))
print(f"\\nWrote the frozen manifest for NB24 to {MANIFEST_PATH.resolve()}")
'''))

cells += integrity_and_audit_cells()


if __name__ == "__main__":
    write_notebook(cells, TRACK_DIR / "23-backtest-sortino-leg-swap.ipynb")
