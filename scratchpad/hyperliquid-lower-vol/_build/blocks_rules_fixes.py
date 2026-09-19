"""Corrections to the NB28-NB31 batch after its first independent review (2026-09-14/15).

Two things live here. Both are built on top of `blocks_prefilter.py` without editing it, so NB32
- which embeds that module's text and is committed with executed outputs - still regenerates.

1. `residual_event_concentration_positive`: the corrected form of an NB08 indicator. The
   original's docstring says "share of the trailing window's positive residual log return
   delivered by its best 5 days", but its numerator takes the five largest values of the
   RESIDUAL series, not of its positive part. With fewer than five positive residual days in the
   window, negative days enter the numerator and the ratio no longer means what it says. The
   original is embedded in NB08-NB32 and is one of NB28's thirteen pre-registered signals, so it
   is left as it is; this is the same statistic computed as documented, and NB29 reports gate 3
   both ways.

2. Nothing in `decide_trades` changes.
"""

from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, CELL14_REPLACEMENTS_PREFILTER

PARAM_ADDITIONS_RULES_FIXES = PARAM_ADDITIONS_PREFILTER

INDICATOR_ADDITIONS_RULES_FIXES = '''
#: --- batch corrections (blocks_rules_fixes.py) ---


@indicators.define()
def residual_event_concentration_positive(
    close: pd.Series,
    event_window_days: int = 180,
    beta_window_days: int = 90,
    min_fresh_observations: int = 60,
) -> pd.Series:
    """`residual_event_concentration` with the numerator taken from the POSITIVE residuals only.

    Identical to the original in every other respect: same calendar clock, same rolling beta,
    same window, same fresh-observation guard. NaN unless at least five positive residual days
    exist in the window, because a "top five" of fewer than five days is not a concentration.
    """
    w = int(event_window_days)
    r = close.pct_change()
    b = _btc_daily_returns_for(r.index)
    bw = int(beta_window_days)
    beta = r.rolling(bw, min_periods=bw).cov(b) / b.rolling(bw, min_periods=bw).var().replace(0.0, float('nan'))
    residual = np.log1p((r - beta * b).clip(lower=-0.99))
    positive = residual.clip(lower=0.0)
    top5 = positive.rolling(w, min_periods=w).apply(lambda x: np.sort(x)[-5:].sum(), raw=True)
    count_positive = (residual > 0).astype(float).rolling(w, min_periods=w).sum()
    concentration = top5 / positive.rolling(w, min_periods=w).sum().replace(0.0, float('nan'))
    fresh = (r.abs() > 0).astype(float).rolling(w, min_periods=1).sum()
    return concentration.where((fresh >= int(min_fresh_observations)) & (count_positive >= 5))
'''

CELL14_REPLACEMENTS_RULES_FIXES = dict(CELL14_REPLACEMENTS_PREFILTER)
