"""Return-floor + stability-rank additions (NB32), on top of `blocks_prefilter.py`.

The 2026-09-14 out-of-sample sketch found that "hard annualised return floor, then rank by a
stability measure" was the only family of selection rules positive in most rolling splits, and
that the HEIGHT of the floor - not the choice of stability measure - made the difference: a zero
floor earned 2.6% annualised, a 15% floor earned 27.4% at lower volatility than the anchor.

The strategy already has both halves of that rule as parameters: `return_gate` with
`gate_lookback_days` / `gate_threshold` is the floor, and `selection_score_indicator` is the
ranker. Nothing in `decide_trades` changes. What this module adds is three fresh-guarded
stability RANKERS, because the raw `inverse_vol` cannot be used as one: a vault whose mark has
not moved for 90 days has sigma = 0, is floored to `VOL_FLOOR`, and scores 10,000 - the calmest
vault in the universe, by construction, and it would be ranked first every cycle.

Kept separate from `blocks_prefilter.py` for the usual reason: NB28-NB31 embed that module's text
and are committed with executed outputs.
"""

from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, CELL14_REPLACEMENTS_PREFILTER

PARAM_ADDITIONS_FLOOR = PARAM_ADDITIONS_PREFILTER.rstrip("'\n") + '''
    #: --- return-floor + stability-rank additions (NB32) ---
    #: Fewest fresh (moved) marks inside a ranker's window before it scores a vault at all. A
    #: stale vault has zero volatility, zero drawdown and zero downside, and would otherwise be
    #: the "most stable" vault in the universe. 30 rather than `min_fresh_observations` (60), so
    #: a vault polled every other day over a 90-day window is still scorable.
    calm_min_fresh = 30
    #: Window for the ulcer and downside rankers, in rows. 90 to match `inverse_vol_window`.
    stability_rank_window = 90
'''

INDICATOR_ADDITIONS_FLOOR = '''
#: --- return-floor + stability-rank additions (NB32) ---

#: Floor for the ulcer ranker's denominator. A vault that never left its high inside the window
#: has an ulcer of exactly zero; with the fresh guard it is a real (and rare) observation rather
#: than a stale mark, and it should rank first, but not at 1/0.
ULCER_FLOOR = 1e-5


def _fresh_count(close: pd.Series, window: int) -> pd.Series:
    return (close.pct_change().abs() > 0).astype(float).rolling(window, min_periods=1).sum()


@indicators.define()
def calm_score(close: pd.Series, inverse_vol_window: int = 90, calm_min_fresh: int = 30) -> pd.Series:
    """`inverse_vol`, NaN unless at least `calm_min_fresh` marks moved inside the window.

    Higher is calmer. Identical to `inverse_vol` on a vault that reports; NaN rather than 10,000
    on one that does not.
    """
    w = int(inverse_vol_window)
    vol = close.pct_change().rolling(w, min_periods=w).std()
    return (1.0 / vol.clip(lower=VOL_FLOOR)).where(_fresh_count(close, w) >= int(calm_min_fresh))


@indicators.define()
def inverse_ulcer_score(close: pd.Series, stability_rank_window: int = 90, calm_min_fresh: int = 30) -> pd.Series:
    """One over the trailing ulcer index. Higher means less time under water, and shallower.

    The out-of-sample sketch put this ranker's worst split at -13.9% against the volatility
    ranker's -22.5%: the ulcer penalises DURATION under the high as well as depth, which is
    closer to "a stable equity curve" than volatility is.
    """
    w = int(stability_rank_window)
    drawdown = close / close.rolling(w, min_periods=w).max() - 1.0
    ulcer = (drawdown ** 2).rolling(w, min_periods=w).mean() ** 0.5
    return (1.0 / ulcer.clip(lower=ULCER_FLOOR)).where(_fresh_count(close, w) >= int(calm_min_fresh))


@indicators.define()
def inverse_downside_score(close: pd.Series, stability_rank_window: int = 90, calm_min_fresh: int = 30) -> pd.Series:
    """One over the trailing downside deviation. Higher means smaller and rarer losing days."""
    w = int(stability_rank_window)
    r = close.pct_change()
    downside = ((r.clip(upper=0.0) ** 2).rolling(w, min_periods=w).mean()) ** 0.5
    return (1.0 / downside.clip(lower=VOL_FLOOR)).where(_fresh_count(close, w) >= int(calm_min_fresh))
'''

#: No new `decide_trades` splice: the floor is `gate_threshold` and the ranker is
#: `selection_score_indicator`, both already read by the incumbent code. The prefilter
#: replacements are carried so the harness's PREFILTER_LOG assertions still hold.
CELL14_REPLACEMENTS_FLOOR = dict(CELL14_REPLACEMENTS_PREFILTER)
