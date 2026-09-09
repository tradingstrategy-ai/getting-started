import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, research_backtest_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB03b - decision-aligned feature screen, descriptive only

No strategy change. Precision-at-6 (NB47's method) for every candidate steadiness feature this
track might use for selection, on the tradable pool at each decision date, using only fresh
(non-stale) observations, reported in both polling regimes.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) / [03a-research-data-quality-and-power.ipynb](03a-research-data-quality-and-power.ipynb),
re-run on the **development window** (2026-01-01 to 2026-06-30). The hold-out is reserved.

## What this notebook does, and what it does not

For each 2-day decision date, this notebook forms the pool `decide_trades` would actually see
(inclusion criteria, momentum gate applied, `MANUAL_BLACKLIST` excluded), ranks it by each
candidate feature, takes the top 6, and scores that top-6's mean 30-day-forward Martin ratio
against the incumbent composite's top-6.

**This is a descriptive pre-screen, not evidence.** NB03a found the development window has about
90 non-overlapping 2-day decision dates and a 30-day forward window overlaps heavily between
adjacent dates, so the effective sample size behind each cell of the table below is small - NB47
already described a similar screen's 23 fortnightly observations as directional rather than
fine-grained. A feature earns a place in a later notebook (NB08, NB09 or the conditional NB10)
only if it beats the incumbent's top-6 **in both polling regimes**; passing is a gate to spend a
backtest on, not a result to report on its own.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("03b-research-feature-screen")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Anchor run on the development window, for consistency with the rest of the track.\n"))
cells.append(research_backtest_cell("NB03b anchor, development window"))
cells += integrity_and_audit_cells()

cells.append(md("""# Precision-at-6 screen

For each candidate feature, at each decision date: form the tradable pool (inclusion criteria met,
momentum gate passed, not manually blacklisted), rank by the feature (lower-is-better features are
negated first), take the top 6, and score the mean 30-day-forward Martin ratio of an equal-weight
basket of those 6 vaults. `min_fresh_observations` (from NB03a) gates any statistic that needs a
real return distribution.
"""))
cells.append(code("""FEATURES = [
    "cagr_sharpe_weight",              # incumbent Sharpe composite (reference row)
    "cagr_sortino_weight",             # incumbent Sortino composite (the anchor's actual selector)
    "btc_beta",
    "ulcer_index_180",
    "downside_deviation_90",
    "positive_window_share",
    "residual_event_concentration",
    "min_window_sortino",
    "residual_cagr_score",
]
LOWER_IS_BETTER = {"btc_beta", "ulcer_index_180", "downside_deviation_90", "residual_event_concentration"}
GATE = float(Parameters.gate_threshold)

candles_close_all = strategy_universe.data_universe.candles.df["close"]
inclusion_series = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)
decision_dates = pd.date_range(
    Parameters.backtest_start + datetime.timedelta(days=60),   # skip the cold-start window
    Parameters.backtest_end - datetime.timedelta(days=31),
    freq="2D",
)
print(f"{len(decision_dates)} decision dates, {len(FEATURES)} features -> {len(decision_dates) * len(FEATURES)} screen cells")


def _forward_martin(pair_ids: list[int], start: pd.Timestamp, horizon: int = 30) -> float:
    curves = []
    for pid in pair_ids:
        try:
            px = candles_close_all.xs(pid, level="pair_id").sort_index()
        except KeyError:
            continue
        window = px.loc[start:start + pd.Timedelta(days=horizon)]
        if len(window) > 5:
            curves.append(window / window.iloc[0])
    if not curves:
        return float("nan")
    basket = pd.concat(curves, axis=1).ffill().mean(axis=1)
    total_return = float(basket.iloc[-1] - 1.0)
    dd = basket / basket.cummax() - 1.0
    ulcer = float(np.sqrt((dd ** 2).mean()))
    return total_return / ulcer if ulcer > 0 else float("nan")
"""))

cells.append(code("""rows = []
for when in decision_dates:
    # `.asof()` calls `isna()` on the located value, which raises on a list-valued Series
    # (pandas tries to test the whole array's truthiness) - so the "last value at or before
    # `when`" lookup is done manually here instead.
    prior_idx = inclusion_series.index[inclusion_series.index <= when]
    pool_ids = inclusion_series.loc[prior_idx[-1]] if len(prior_idx) else []
    pool_ids = pool_ids if pool_ids is not None else []
    pool_ids = [
        pid for pid in pool_ids
        if str(strategy_universe.get_pair_by_id(pid).pool_address).lower() not in MANUAL_BLACKLIST
    ]
    gated_ids = []
    for pid in pool_ids:
        pair = strategy_universe.get_pair_by_id(pid)
        gate_value = indicator_data.get_indicator_series("return_gate", pair=pair, unlimited=True).asof(when)
        if gate_value == gate_value and gate_value > GATE:
            gated_ids.append(pid)

    for feature in FEATURES:
        values = {}
        for pid in gated_ids:
            pair = strategy_universe.get_pair_by_id(pid)
            v = indicator_data.get_indicator_series(feature, pair=pair, unlimited=True).asof(when)
            if v != v:
                continue
            fresh_needed = feature in ("ulcer_index_180", "downside_deviation_90", "positive_window_share")
            if fresh_needed:
                fresh = indicator_data.get_indicator_series("fresh_observation_count", pair=pair, unlimited=True).asof(when)
                if fresh != fresh or fresh < Parameters.min_fresh_observations:
                    continue
            values[pid] = -v if feature in LOWER_IS_BETTER else v
        top6 = sorted(values, key=values.get, reverse=True)[:6]
        rows.append({
            "date": when,
            "feature": feature,
            "regime": "sparse" if when < pd.Timestamp("2026-04-01") else "dense",
            "pool_size": len(gated_ids),
            "top6_size": len(top6),
            "top6_forward_martin": _forward_martin(top6, when),
        })

screen_raw = pd.DataFrame(rows)
print(f"Mean gated pool size: {screen_raw['pool_size'].mean():.1f}; mean top-6 actually filled: {screen_raw['top6_size'].mean():.2f}")
"""))

cells.append(md("## Screen result\n"))
cells.append(code("""screen = screen_raw.groupby(["feature", "regime"])["top6_forward_martin"].mean().unstack()
screen["overall"] = screen_raw.groupby("feature")["top6_forward_martin"].mean()
reference = screen.loc["cagr_sortino_weight"]
screen["beats_incumbent_both_regimes"] = (screen[["sparse", "dense"]] > reference[["sparse", "dense"]]).all(axis=1)
display(screen.sort_values("overall", ascending=False))

n_obs_per_regime = screen_raw.groupby("regime")["date"].nunique()
print(f"Non-overlapping ~30-day-forward observations per regime (upper bound, ignoring overlap): "
      f"{(n_obs_per_regime / 15).round(1).to_dict()}")

gate_passed = screen.index[screen["beats_incumbent_both_regimes"]].tolist()
gate_passed = [f for f in gate_passed if f not in ("cagr_sharpe_weight", "cagr_sortino_weight")]
print(f"Features clearing the gate (beat the incumbent's top-6 in both regimes): {gate_passed or 'none'}")
"""))

write_notebook(cells, TRACK_DIR / "03b-research-feature-screen.ipynb")
