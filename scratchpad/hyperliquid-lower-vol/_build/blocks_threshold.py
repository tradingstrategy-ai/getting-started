"""Threshold-based crash filter (NB37), on top of `blocks_floor.py` / `blocks_prefilter.py`.

The volatility tail exclusion of plan 34 removed a fixed COUNT of the most volatile measurable
candidates. The vault-level calibration of 2026-09-16 (66 post-break decisions x ~210
candidates) showed the forward 30-day crash rate is flat below about 50% annualised realised
volatility, rises to 4-6% between 50% and 100%, and triples at 100% (15.4% in 1.0-1.5, 21.9%
in 1.5-2.0), with the mean 30-day log return going from about -4% to -17% across the same
knee. So the filter is stated as a THRESHOLD on the vault - "we do not hold a vault whose
trailing 90-row realised volatility exceeds X annualised" - with hysteresis: a candidate is
admitted only below `crash_vol_threshold_enter` and a held vault is removed only above
`crash_vol_threshold_exit`, so a name near the boundary does not flap.

The volatility is exactly the sizer's own estimate: `1 / inverse_vol`, the trailing
`inverse_vol_window` (90) row standard deviation of daily returns, annualised by sqrt(365). A
candidate without a finite estimate is kept (permissive), as in plan 34. Composed in front of
the count/fraction prefilter, which stays available but is off by default.

Kept separate from the earlier modules because NB28-NB36 embed their text.
"""

from blocks_floor import PARAM_ADDITIONS_FLOOR, CELL14_REPLACEMENTS_FLOOR

PARAM_ADDITIONS_THRESHOLD = PARAM_ADDITIONS_FLOOR.rstrip("'\n") + '''
    #: --- threshold crash filter (NB37) ---
    #: A HELD vault is removed from the candidate pool when its trailing realised volatility,
    #: annualised, exceeds this. 0.0 disables the filter, which is the default so every earlier
    #: notebook's behaviour and the anchor are unchanged.
    crash_vol_threshold_exit = 0.0
    #: A vault NOT currently held is admitted only when its trailing realised volatility is at
    #: or below this. 0.0 means "same as exit" (no hysteresis).
    crash_vol_threshold_enter = 0.0
'''

_CRASH_BLOCK = (
    "    # Threshold crash filter (NB37). Remove candidates whose trailing realised volatility,\n"
    "    # annualised from the sizer's own `inverse_vol`, exceeds the threshold: `exit` for a vault\n"
    "    # we hold, `enter` for one we do not. Candidates without a finite estimate are kept.\n"
    "    crash_exit = float(getattr(parameters, 'crash_vol_threshold_exit', 0.0) or 0.0)\n"
    "    if crash_exit > 0:\n"
    "        crash_enter = float(getattr(parameters, 'crash_vol_threshold_enter', 0.0) or 0.0) or crash_exit\n"
    "        _held_now = {\n"
    "            _p.pair.internal_id for _p in state.portfolio.get_open_positions()\n"
    "            if not _p.pair.is_credit_supply()\n"
    "        }\n"
    "        _kept, _crash_excluded, _crash_values = [], [], {}\n"
    "        for _item in candidates:\n"
    "            _pid, _pair, _sig = _item\n"
    "            _iv = indicators.get_indicator_value('inverse_vol', pair=_pair)\n"
    "            _iv = float('nan') if _iv is None else float(_iv)\n"
    "            _vol = (math.sqrt(365.0) / _iv) if (np.isfinite(_iv) and _iv > 0) else float('nan')\n"
    "            _limit = crash_exit if _pid in _held_now else crash_enter\n"
    "            _crash_values[str(_pair.pool_address).lower()] = _vol\n"
    "            if np.isfinite(_vol) and _vol > _limit:\n"
    "                _crash_excluded.append(_item)\n"
    "            else:\n"
    "                _kept.append(_item)\n"
    "        CRASH_LOG[timestamp] = {\n"
    "            'exit': crash_exit, 'enter': crash_enter,\n"
    "            'pool_size': len(candidates), 'excluded_count': len(_crash_excluded),\n"
    "            'excluded_held': sum(1 for _i in _crash_excluded if _i[0] in _held_now),\n"
    "            'measured_count': sum(1 for _v in _crash_values.values() if np.isfinite(_v)),\n"
    "            'excluded_addresses': sorted(str(_i[1].pool_address).lower() for _i in _crash_excluded),\n"
    "            'candidate_addresses': [str(_i[1].pool_address).lower() for _i in candidates],\n"
    "            'vol': _crash_values,\n"
    "        }\n"
    "        candidates = _kept\n"
    "        if not candidates:\n"
    "            return []\n"
    "\n"
)

INDICATOR_ADDITIONS_THRESHOLD = '''
#: --- threshold crash filter (NB37) ---

#: Per-cycle record of the crash filter, written by `decide_trades`; cleared and snapshotted per
#: run by the NB37 harness.
CRASH_LOG: dict = {}
'''


def _with_crash_filter(replacements: dict) -> dict:
    out, spliced = {}, 0
    for key, value in replacements.items():
        if key.lstrip().startswith("# Rank by composite (selection)"):
            value = _CRASH_BLOCK + value
            spliced += 1
        out[key] = value
    assert spliced == 1, f"expected exactly one ranking anchor to splice into, found {spliced}"
    return out


CELL14_REPLACEMENTS_THRESHOLD = _with_crash_filter(CELL14_REPLACEMENTS_FLOOR)
