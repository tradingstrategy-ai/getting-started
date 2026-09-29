import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, write_notebook, TRACK_DIR

HEADING = """# Verification: does NB03b's feature screen have a one-bar look-ahead?

Not a research notebook. A correctness check for
[03b-research-feature-screen.ipynb](../03b-research-feature-screen.ipynb).

NB03b reads each candidate feature with `get_indicator_series(...).asof(when)`, which returns the
bar **labelled** `when`. NB57 established that daily bars here are left-labelled, so that bar spans
`[when, when + 1d)` and closes at `when + 1d`. Inside `decide_trades` the framework instead uses
`get_indicator_value()`, which applies `index = -1` and therefore reads the bar labelled
`when - 1d`. The screen is thus one bar ahead of what the strategy can actually see - the same
defect class NB57 found had manufactured a spurious +1.0 Sharpe in NB41.

This notebook recomputes the screen both ways and reports whether the gate verdicts change. The
gate matters: it is what caused NB08 and NB10 not to be built, and what sent
`min_window_sortino` and `positive_window_share` to NB09.
"""

cells = [md(HEADING)]
cells += common_prefix_cells("verify-screen-lookahead")
cells += common_suffix_cells()   # defines MANUAL_BLACKLIST and the algorithm helpers

cells.append(md("## Recompute the screen at both alignments\n"))
cells.append(code('''import datetime

FEATURES = [
    "cagr_sortino_weight",             # incumbent, the reference row
    "btc_beta",
    "ulcer_index_180",
    "downside_deviation_90",
    "positive_window_share",
    "residual_event_concentration",
    "min_window_sortino",
    "residual_cagr_score",
]
LOWER_IS_BETTER = {"btc_beta", "ulcer_index_180", "downside_deviation_90", "residual_event_concentration"}
FRESH_GATED = {"ulcer_index_180", "downside_deviation_90", "positive_window_share"}
GATE = float(Parameters.gate_threshold)
ONE_BAR = Parameters.candle_time_bucket.to_timedelta()

candles_close_all = strategy_universe.data_universe.candles.df["close"]
inclusion_series = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)
decision_dates = pd.date_range(
    Parameters.backtest_start + datetime.timedelta(days=60),
    Parameters.backtest_end - datetime.timedelta(days=31),
    freq="2D",
)

_series_cache = {}
def series_for(name, pair):
    key = (name, pair.internal_id)
    if key not in _series_cache:
        _series_cache[key] = indicator_data.get_indicator_series(name, pair=pair, unlimited=True)
    return _series_cache[key]


def forward_martin(pair_ids, start, horizon=30):
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
    dd = basket / basket.cummax() - 1.0
    ulcer = float(np.sqrt((dd ** 2).mean()))
    return float(basket.iloc[-1] - 1.0) / ulcer if ulcer > 0 else float("nan")


def run_screen(read_at):
    """`read_at` maps a decision date to the timestamp the feature is read at."""
    rows = []
    for when in decision_dates:
        at = read_at(when)
        prior_idx = inclusion_series.index[inclusion_series.index <= at]
        pool_ids = inclusion_series.loc[prior_idx[-1]] if len(prior_idx) else []
        if pool_ids is None:
            pool_ids = []
        pool_ids = [
            pid for pid in pool_ids
            if str(strategy_universe.get_pair_by_id(pid).pool_address).lower() not in MANUAL_BLACKLIST
        ]
        gated = []
        for pid in pool_ids:
            pair = strategy_universe.get_pair_by_id(pid)
            g = series_for("return_gate", pair).asof(at)
            if g == g and g > GATE:
                gated.append(pid)
        for feature in FEATURES:
            values = {}
            for pid in gated:
                pair = strategy_universe.get_pair_by_id(pid)
                v = series_for(feature, pair).asof(at)
                if v != v:
                    continue
                if feature in FRESH_GATED:
                    fresh = series_for("fresh_observation_count", pair).asof(at)
                    if fresh != fresh or fresh < Parameters.min_fresh_observations:
                        continue
                values[pid] = -v if feature in LOWER_IS_BETTER else v
            top6 = sorted(values, key=values.get, reverse=True)[:6]
            rows.append({
                "date": when,
                "feature": feature,
                "regime": "sparse" if when < pd.Timestamp("2026-04-01") else "dense",
                "top6_size": len(top6),
                # The forward window always starts at the real decision date, never at `at`.
                "fwd": forward_martin(top6, when),
            })
    return pd.DataFrame(rows)


def summarise(raw):
    s = raw.groupby(["feature", "regime"])["fwd"].mean().unstack()
    ref = s.loc["cagr_sortino_weight"]
    s["beats_both"] = (s[["sparse", "dense"]] > ref[["sparse", "dense"]]).all(axis=1)
    s["mean_top6_size"] = raw.groupby("feature")["top6_size"].mean()
    return s

as_published = summarise(run_screen(lambda w: w))                  # NB03b as it stands
live_parity = summarise(run_screen(lambda w: w - ONE_BAR))         # what decide_trades sees
'''))

cells.append(md("## Comparison\n"))
cells.append(code('''print("AS PUBLISHED in NB03b (.asof(when), one bar of look-ahead):")
display(as_published.sort_values("dense", ascending=False))
print()
print("LIVE PARITY (.asof(when - 1 bar), what decide_trades actually sees):")
display(live_parity.sort_values("dense", ascending=False))

comparison = pd.DataFrame({
    "published_passes": as_published["beats_both"],
    "live_parity_passes": live_parity["beats_both"],
})
comparison["verdict_changes"] = comparison["published_passes"] != comparison["live_parity_passes"]
print()
display(comparison)

changed = comparison.index[comparison["verdict_changes"]].tolist()
if changed:
    print(f"GATE VERDICT CHANGES for: {changed}")
    print("NB03b's gate decisions - which sent features to NB09 and which caused NB08/NB10 not to")
    print("be built - are affected by the look-ahead and must be recomputed at live parity.")
else:
    print("No gate verdict changes: the look-ahead is real but does not alter which features pass.")
    print("NB03b's conclusions stand; the alignment should still be corrected for correctness.")

print()
print(f"Mean top-6 basket size (published): {as_published['mean_top6_size'].mean():.2f} of 6")
print("A feature that can only score a handful of vaults is compared against the incumbent's")
print("fuller basket, so the screen is not a like-for-like comparison across features.")
'''))

write_notebook(cells, TRACK_DIR / "_build" / "verify-screen-lookahead.ipynb")
