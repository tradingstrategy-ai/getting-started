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


MD_INTRO = """# Precision-at-6 screen

For each candidate feature, at each decision date: form the tradable pool (inclusion criteria met,
momentum gate passed, not manually blacklisted), rank by the feature (lower-is-better features are
negated first), take the top 6, and score the mean 30-day-forward Martin ratio of an equal-weight
basket of those 6 vaults.

Two corrections over the first version of this screen, both from
`_build/verify-screen-lookahead.ipynb`:

- **Alignment.** Features are read at `when - 1 bar`, not `when`. Daily bars here are
  left-labelled (NB57), so the bar labelled `when` closes at `when + 1d` and carries a day of
  information `decide_trades` cannot see - it reads the previous bar via `get_indicator_value`'s
  `index = -1`. At the original alignment `downside_deviation_90` failed the gate on a
  sparse-regime score of -0.240; at live parity it scores +1.139 and passes.
- **Comparable baskets.** The original screen averaged 4.64 names of 6, and unequally by feature
  (`ulcer_index_180` filled 1.2 slots, `positive_window_share` 3.3, the incumbent 6.0), so a
  concentrated basket was compared against a diversified one. The gate now scores only dates on
  which a feature can fill all six slots, and the fill rate is reported beside every row.

The Stage C metadata features the plan listed are also screened here. They are read straight from
the vault price parquet rather than through an indicator, because they do not derive from the
share price series - which per NB57 is exactly why they are interesting: they do not inherit NAV
staleness.
"""

CODE_SETUP = '''import datetime

PRICE_FEATURES = [
    "cagr_sortino_weight",             # incumbent Sortino composite, the reference row
    "cagr_sharpe_weight",              # incumbent Sharpe composite
    "btc_beta",
    "ulcer_index_180",
    "downside_deviation_90",
    "positive_window_share",
    "residual_event_concentration",
    "min_window_sortino",
    "residual_cagr_score",
    "drawdown_recovery_days",
    "tvl_growth",
]
# NB57 Stage C: measured independently of the share-price series, so free of NAV staleness.
METADATA_FEATURES = ["leader_fraction", "leader_commission", "follower_count", "cumulative_volume", "account_pnl"]
FEATURES = PRICE_FEATURES + METADATA_FEATURES

LOWER_IS_BETTER = {
    "btc_beta", "ulcer_index_180", "downside_deviation_90", "residual_event_concentration",
    "drawdown_recovery_days", "leader_commission",
}
FRESH_GATED = {"ulcer_index_180", "downside_deviation_90", "positive_window_share"}
GATE = float(Parameters.gate_threshold)
#: Live parity: `decide_trades` reads the bar before the decision date (NB57).
ONE_BAR = Parameters.candle_time_bucket.to_timedelta()
#: A feature needs at least this many full-basket dates in a regime for its mean to be meaningful.
MIN_FULL_BASKET_DATES = 5

candles_close_all = strategy_universe.data_universe.candles.df["close"]
inclusion_series = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)
decision_dates = pd.date_range(
    Parameters.backtest_start + datetime.timedelta(days=60),   # skip the cold-start window
    Parameters.backtest_end - datetime.timedelta(days=31),
    freq="2D",
)
print(f"{len(decision_dates)} decision dates, {len(FEATURES)} features "
      f"({len(PRICE_FEATURES)} price-derived, {len(METADATA_FEATURES)} Stage C metadata)")
'''

CODE_METADATA = '''from pathlib import Path

metadata_cache_path = Path("/tmp/hl-vault-metadata-daily.parquet")
raw_path = Path("~/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet").expanduser()

if metadata_cache_path.exists():
    metadata_daily = pd.read_parquet(metadata_cache_path)
else:
    raw = pd.read_parquet(raw_path, columns=["chain", "address"] + METADATA_FEATURES)
    raw = raw[raw["chain"] == ChainId.hypercore.value].copy()
    raw["address"] = raw["address"].str.lower()
    # One value per vault per day, taken as the last poll of that day.
    metadata_daily = (
        raw.groupby("address")[METADATA_FEATURES]
        .resample("1D").last()
        .groupby(level="address").ffill()
    )
    metadata_daily.to_parquet(metadata_cache_path)

print(f"Stage C metadata: {len(metadata_daily):,} vault-days for "
      f"{metadata_daily.index.get_level_values('address').nunique()} vaults")
display(metadata_daily.tail(3))

#: pair_id -> lower-case pool address, for joining the metadata frame to the universe.
address_by_pair_id = {
    pair.internal_id: str(pair.pool_address).lower()
    for pair in strategy_universe.iterate_pairs()
    if pair.is_vault()
}

_metadata_cache = {}
def metadata_series(address, column):
    key = (address, column)
    if key not in _metadata_cache:
        try:
            _metadata_cache[key] = metadata_daily.loc[address, column]
        except KeyError:
            _metadata_cache[key] = None
    return _metadata_cache[key]
'''

CODE_SCREEN = '''_series_cache = {}
def indicator_series_for(name, pair):
    key = (name, pair.internal_id)
    if key not in _series_cache:
        _series_cache[key] = indicator_data.get_indicator_series(name, pair=pair, unlimited=True)
    return _series_cache[key]


def feature_value(feature, pair, at):
    """Feature value as of `at`, from an indicator or from the Stage C metadata frame."""
    if feature in METADATA_FEATURES:
        address = address_by_pair_id.get(pair.internal_id)
        if address is None:
            return float("nan")
        series = metadata_series(address, feature)
        if series is None or not len(series):
            return float("nan")
        prior = series.index[series.index <= at]
        if not len(prior):
            return float("nan")
        value = series.loc[prior[-1]]
        # These columns use pandas nullable dtypes, so a missing value is pd.NA rather than NaN
        # and float() raises on it.
        return float(value) if pd.notna(value) else float("nan")
    return indicator_series_for(feature, pair).asof(at)


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


rows = []
for when in decision_dates:
    at = when - ONE_BAR      # live parity, per NB57
    prior_idx = inclusion_series.index[inclusion_series.index <= at]
    pool_ids = inclusion_series.loc[prior_idx[-1]] if len(prior_idx) else []
    if pool_ids is None:
        pool_ids = []
    pool_ids = [
        pid for pid in pool_ids
        if str(strategy_universe.get_pair_by_id(pid).pool_address).lower() not in MANUAL_BLACKLIST
    ]
    gated_ids = []
    for pid in pool_ids:
        pair = strategy_universe.get_pair_by_id(pid)
        gate_value = indicator_series_for("return_gate", pair).asof(at)
        if gate_value == gate_value and gate_value > GATE:
            gated_ids.append(pid)

    for feature in FEATURES:
        values = {}
        for pid in gated_ids:
            pair = strategy_universe.get_pair_by_id(pid)
            v = feature_value(feature, pair, at)
            if v != v:
                continue
            if feature in FRESH_GATED:
                fresh = indicator_series_for("fresh_observation_count", pair).asof(at)
                if fresh != fresh or fresh < Parameters.min_fresh_observations:
                    continue
            values[pid] = -v if feature in LOWER_IS_BETTER else v
        top6 = sorted(values, key=values.get, reverse=True)[:6]
        rows.append({
            "date": when,
            "feature": feature,
            "regime": "sparse" if when < pd.Timestamp("2026-04-01") else "dense",
            "scorable_pool": len(values),
            "top6_size": len(top6),
            "full_basket": len(top6) == 6,
            "top6_forward_martin": forward_martin(top6, when),
        })

screen_raw = pd.DataFrame(rows)
print(f"Mean gated pool size: {screen_raw.groupby('date')['scorable_pool'].max().mean():.1f}")
print(f"Mean top-6 fill across all features: {screen_raw['top6_size'].mean():.2f} of 6")
'''

MD_RESULT = """## Screen result

Scored on **full baskets only**, so every feature is compared on six names. `full_basket_rate` is
the share of decision dates on which the feature could fill all six, and is itself informative: a
feature that can rarely score six vaults is not usable as a selection score regardless of how its
few-name baskets perform.
"""

CODE_RESULT = '''full = screen_raw[screen_raw["full_basket"]]
screen = full.groupby(["feature", "regime"])["top6_forward_martin"].mean().unstack()
counts = full.groupby(["feature", "regime"])["date"].count().unstack().reindex(screen.index).fillna(0)
screen["full_basket_rate"] = screen_raw.groupby("feature")["full_basket"].mean()
screen["n_sparse"] = counts["sparse"] if "sparse" in counts else 0
screen["n_dense"] = counts["dense"] if "dense" in counts else 0

reference = screen.loc["cagr_sortino_weight"]
enough = (screen["n_sparse"] >= MIN_FULL_BASKET_DATES) & (screen["n_dense"] >= MIN_FULL_BASKET_DATES)
beats = (screen[["sparse", "dense"]] > reference[["sparse", "dense"]]).all(axis=1)
screen["beats_incumbent_both_regimes"] = beats & enough
display(screen.sort_values("dense", ascending=False))

gate_passed = [
    f for f in screen.index[screen["beats_incumbent_both_regimes"]]
    if f not in ("cagr_sharpe_weight", "cagr_sortino_weight")
]
print(f"Gate passed (beat the incumbent on full baskets in both regimes): {gate_passed or 'none'}")
insufficient = screen.index[~enough].tolist()
print(f"Too few full-basket dates to judge (< {MIN_FULL_BASKET_DATES} in a regime): {insufficient or 'none'}")
'''


cells.append(md(MD_INTRO))
cells.append(code(CODE_SETUP))
cells.append(md("## Load the Stage C metadata series\n"))
cells.append(code(CODE_METADATA))
cells.append(md("## Run the screen\n"))
cells.append(code(CODE_SCREEN))
cells.append(md(MD_RESULT))
cells.append(code(CODE_RESULT))

write_notebook(cells, TRACK_DIR / "03b-research-feature-screen.ipynb")
