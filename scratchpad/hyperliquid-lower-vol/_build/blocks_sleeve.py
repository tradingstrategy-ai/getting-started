"""Quality floor and cash sleeve (NB40), on top of `blocks_threshold.py`.

The rescue idea for the rejected leads: allocate only to vaults that clear a QUALITY threshold at
the decision date, and hold the unfilled slots in cash rather than fill them with the next-best
name. Two parts:

- `quality_sharpe`: the trailing `quality_lookback_days`-row Sharpe of the share price, in the
  event-time form NB39 screened as the strongest predictor of forward 60-day Sharpe on the full
  archive (`sharpe180_f00`): annualised sum of log returns over annualised root-sum-of-squares of
  log returns. Forward-filled days contribute zero to both sums, so the statistic is the same on
  the daily grid as on the observed marks - the weekly-polling gotcha does not inflate it, unlike
  the demeaned `sharpe_score`. NaN unless the window holds at least `quality_min_events + 1`
  moved marks, the last moved mark is within `quality_max_stale_rows`, one moved mark sits in the
  first `quality_max_stale_rows` rows of the window (the window is spanned), and the vault is
  older than the window. One difference from NB39: the first event of the window here starts at
  the last mark BEFORE the window rather than at the first mark inside it.
- The floor: with `quality_floor_on`, a candidate whose `quality_sharpe` is below
  `quality_floor_sharpe` - or NaN - is removed before ranking, whether or not it is held. No
  hysteresis. If nothing qualifies the book goes to cash: the block does NOT return early, so the
  alpha model sees no signals and sells every open position.
- The sleeve: with `cash_sleeve_slots = S > 0`, when only `k < S` names are selected the
  investable target is scaled by `k / S` and the concentration cap is widened by `S / k` (to at
  most 1.0), so each name keeps its cap as a share of FULL equity while the empty slots stay in
  cash. With `k >= S` both are untouched; with `S = 0` the sleeve is off, which is the default.

Kept separate from the earlier modules because NB28-NB37 embed their text.
"""

from blocks_threshold import PARAM_ADDITIONS_THRESHOLD, CELL14_REPLACEMENTS_THRESHOLD

PARAM_ADDITIONS_SLEEVE = PARAM_ADDITIONS_THRESHOLD.rstrip("'\n") + '''
    #: --- quality floor and cash sleeve (NB40) ---
    #: Window, in rows, of the quality Sharpe. 180 to match NB39's strongest score.
    quality_lookback_days = 180
    #: Fewest events (moved marks after the first) inside the window before the score exists.
    quality_min_events = 8
    #: The last moved mark must be within this many rows, and one moved mark must sit inside the
    #: first this-many rows of the window.
    quality_max_stale_rows = 14
    #: Off by default so every earlier notebook and the anchor are unchanged.
    quality_floor_on = False
    #: Annualised event-time Sharpe a candidate must reach (or exceed) to be allocated capital.
    quality_floor_sharpe = 0.0
    #: Slots of the book for the cash sleeve. 0 disables the sleeve.
    cash_sleeve_slots = 0
'''

INDICATOR_ADDITIONS_SLEEVE = '''
#: --- quality floor and cash sleeve (NB40) ---

#: Per-cycle record of the quality floor, written by `decide_trades`; cleared and snapshotted per
#: run by the NB40 harness.
QUALITY_LOG: dict = {}
#: Per-cycle record of the cash sleeve: selected count, slots, fill and the widened cap.
CASH_SLEEVE_LOG: dict = {}


@indicators.define()
def quality_sharpe(
    close: pd.Series, quality_lookback_days: int = 180, quality_min_events: int = 8, quality_max_stale_rows: int = 14,
) -> pd.Series:
    """NB39's `sharpe{W}_f00` on the daily grid: annualised sum of log returns over the annualised
    root-sum-of-squares of log returns, over the trailing `quality_lookback_days` rows.

    Forward-filled rows are zero in both sums, so the value equals the event-time statistic.
    NaN unless the window holds `quality_min_events + 1` moved marks, the last within
    `quality_max_stale_rows` rows, one inside the first `quality_max_stale_rows` rows of the
    window, and the vault has a mark at or before the window start.
    """
    w = int(quality_lookback_days)
    stale = int(quality_max_stale_rows)
    r = np.log(close.astype(float)).diff()
    rate = r.rolling(w, min_periods=w).sum() * 365.0 / w
    vol = (r.pow(2).rolling(w, min_periods=w).sum() * 365.0 / w) ** 0.5
    sharpe = rate / vol.where(vol > 0)
    moved = _fresh_count(close, w)
    # Moved marks in the first `stale` rows of the window = moved in the window minus moved in
    # its last (w - stale) rows.
    early = moved - _fresh_count(close, w - stale)
    ok = (
        (moved >= int(quality_min_events) + 1)
        & (_rows_since_fresh(close) <= stale)
        & (early >= 1)
        & close.shift(w).notna()
    )
    return sharpe.where(ok)
'''

_FLOOR_BLOCK = (
    "    # Quality floor (NB40). Remove every candidate - held or not - whose trailing event-time\n"
    "    # Sharpe is below the floor or not finite. No early return when nothing qualifies: the\n"
    "    # alpha model then sees no signals and sells the book into cash.\n"
    "    if bool(getattr(parameters, 'quality_floor_on', False)):\n"
    "        _floor = float(parameters.quality_floor_sharpe)\n"
    "        _held_q = {\n"
    "            _p.pair.internal_id for _p in state.portfolio.get_open_positions()\n"
    "            if not _p.pair.is_credit_supply()\n"
    "        }\n"
    "        _kept_q, _below_q, _q_values = [], [], {}\n"
    "        for _item in candidates:\n"
    "            _pid, _pair, _sig = _item\n"
    "            _q = indicators.get_indicator_value('quality_sharpe', pair=_pair)\n"
    "            _q = float('nan') if _q is None else float(_q)\n"
    "            _q_values[str(_pair.pool_address).lower()] = _q\n"
    "            if np.isfinite(_q) and _q >= _floor:\n"
    "                _kept_q.append(_item)\n"
    "            else:\n"
    "                _below_q.append(_item)\n"
    "        QUALITY_LOG[timestamp] = {\n"
    "            'floor': _floor, 'pool_size': len(candidates), 'qualifying': len(_kept_q),\n"
    "            'measured_count': sum(1 for _v in _q_values.values() if np.isfinite(_v)),\n"
    "            'held_count': len(_held_q),\n"
    "            'held_removed': sum(1 for _i in _below_q if _i[0] in _held_q),\n"
    "            'removed_addresses': sorted(str(_i[1].pool_address).lower() for _i in _below_q),\n"
    "            'qualifying_addresses': sorted(str(_i[1].pool_address).lower() for _i in _kept_q),\n"
    "            'quality': _q_values,\n"
    "        }\n"
    "        candidates = _kept_q\n"
    "\n"
)

_SLEEVE_BLOCK = (
    "    # Cash sleeve (NB40). Fewer selected names than slots: scale the investable target by the\n"
    "    # fill and widen the cap by its inverse, so each name keeps its cap as a share of FULL\n"
    "    # equity and the empty slots stay in cash.\n"
    "    _sleeve_max_weight = float(parameters.max_concentration_pct)\n"
    "    _sleeve_slots = int(getattr(parameters, 'cash_sleeve_slots', 0) or 0)\n"
    "    if _sleeve_slots > 0:\n"
    "        _fill = min(1.0, len(selected) / _sleeve_slots)\n"
    "        if 0.0 < _fill < 1.0:\n"
    "            allocation_pct *= _fill\n"
    "            _sleeve_max_weight = float(min(1.0, _sleeve_max_weight / _fill))\n"
    "        CASH_SLEEVE_LOG[timestamp] = {\n"
    "            'slots': _sleeve_slots, 'selected': len(selected), 'fill': _fill,\n"
    "            'allocation_pct': float(allocation_pct), 'max_weight': _sleeve_max_weight,\n"
    "        }\n"
    "\n"
)

_SIZING_KEY = (
    "    redeemable_capital = get_redeemable_portfolio_capital(position_manager)\n"
    "    portfolio_target_value = calculate_portfolio_target_value(position_manager, allocation_pct)\n"
)
_CAP_KEY = "        max_weight=float(parameters.max_concentration_pct),\n        max_positions=max_assets_in_portfolio,\n"
_CAP_NEW = "        max_weight=_sleeve_max_weight,\n        max_positions=max_assets_in_portfolio,\n"


def _with_floor_and_sleeve(replacements: dict) -> dict:
    out, spliced = {}, 0
    for key, value in replacements.items():
        if key.lstrip().startswith("# Rank by composite (selection)"):
            anchor = "    # Rank by composite (selection)"
            assert value.count(anchor) == 1, "expected the ranking comment once inside the threshold splice"
            value = value.replace(anchor, _FLOOR_BLOCK + anchor)
            spliced += 1
        out[key] = value
    assert spliced == 1, f"expected exactly one ranking anchor to splice into, found {spliced}"
    for key in (_SIZING_KEY, _CAP_KEY):
        assert key not in out, "sizing anchors must not already be replaced by an earlier module"
    out[_SIZING_KEY] = _SLEEVE_BLOCK + _SIZING_KEY
    out[_CAP_KEY] = _CAP_NEW
    return out


CELL14_REPLACEMENTS_SLEEVE = _with_floor_and_sleeve(CELL14_REPLACEMENTS_THRESHOLD)
