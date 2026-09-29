"""Cluster exit (plan 42, NB42), on top of `blocks_sleeve.py`.

One position-level exit, explicit on/off flag (`cluster_on`; 0 is NOT an off state), run as a
labelled diagnostic only: a HELD vault whose trailing `cluster_window` rows contain at least two
daily log returns at or below `strike_threshold` is removed from the candidate pool (and so
sold). Read at T-1 like everything else in `decide_trades`; no admission branch, no re-weighting,
no breaker. Plan 42 Draft 5 pre-registers -10% x 2-in-3 as the only specification.

Kept separate from the earlier modules because NB28-NB41 embed their text.
"""

from blocks_sleeve import PARAM_ADDITIONS_SLEEVE, CELL14_REPLACEMENTS_SLEEVE

PARAM_ADDITIONS_CRASH_EXIT = PARAM_ADDITIONS_SLEEVE.rstrip("'\n") + '''
    #: --- cluster exit (plan 42, NB42) ---
    #: Explicit switch. False is the anchor path; the threshold below is not an off state.
    cluster_on = False
    #: Daily log return at or below which a row counts as a strike.
    strike_threshold = -0.10
    #: Rows of the trailing window the strikes are counted in.
    cluster_window = 3
'''

INDICATOR_ADDITIONS_CRASH_EXIT = '''
#: --- cluster exit (plan 42, NB42) ---

#: Per-cycle record of the cluster exit, written by `decide_trades`; cleared per run by the
#: NB42 harness.
CLUSTER_LOG: dict = {}


@indicators.define()
def down_day_count(close: pd.Series, strike_threshold: float = -0.10, cluster_window: int = 3) -> pd.Series:
    """Number of rows in the trailing `cluster_window` rows whose daily log return is at or
    below `strike_threshold`. A forward-filled row has a zero return and never counts."""
    r = np.log(close.astype(float)).diff()
    return (r <= float(strike_threshold)).astype(float).rolling(int(cluster_window), min_periods=1).sum()
'''

_CLUSTER_BLOCK = (
    "    # Cluster exit (plan 42). A HELD vault with two or more strike rows in its trailing window\n"
    "    # leaves the pool. Read at T-1; names not held are untouched.\n"
    "    if bool(getattr(parameters, 'cluster_on', False)):\n"
    "        _held_c = {\n"
    "            _p.pair.internal_id for _p in state.portfolio.get_open_positions()\n"
    "            if not _p.pair.is_credit_supply()\n"
    "        }\n"
    "        _kept_c, _cut_c, _counts = [], [], {}\n"
    "        for _item in candidates:\n"
    "            _pid, _pair, _sig = _item\n"
    "            _n = indicators.get_indicator_value('down_day_count', pair=_pair)\n"
    "            _n = float('nan') if _n is None else float(_n)\n"
    "            _counts[str(_pair.pool_address).lower()] = _n\n"
    "            if _pid in _held_c and np.isfinite(_n) and _n >= 2:\n"
    "                _cut_c.append(_item)\n"
    "            else:\n"
    "                _kept_c.append(_item)\n"
    "        CLUSTER_LOG[timestamp] = {\n"
    "            'held_count': len(_held_c), 'cut': sorted(str(_i[1].pool_address).lower() for _i in _cut_c),\n"
    "            'counts_held': {str(_i[1].pool_address).lower(): _counts[str(_i[1].pool_address).lower()] for _i in candidates if _i[0] in _held_c},\n"
    "        }\n"
    "        candidates = _kept_c\n"
    "\n"
)


def _with_cluster_exit(replacements: dict) -> dict:
    out, spliced = {}, 0
    for key, value in replacements.items():
        if key.lstrip().startswith("# Rank by composite (selection)"):
            anchor = "    # Rank by composite (selection)"
            assert value.count(anchor) == 1
            value = value.replace(anchor, _CLUSTER_BLOCK + anchor)
            spliced += 1
        out[key] = value
    assert spliced == 1, f"expected exactly one ranking anchor, found {spliced}"
    return out


CELL14_REPLACEMENTS_CRASH_EXIT = _with_cluster_exit(CELL14_REPLACEMENTS_SLEEVE)
