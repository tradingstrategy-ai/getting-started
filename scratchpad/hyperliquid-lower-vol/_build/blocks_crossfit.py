"""Cross-fitting additions (NB30), on top of `blocks_prefilter.py`.

Kept separate for the same reason `blocks_drop_modes.py` was kept separate from
`blocks_stability.py`: NB28 and NB29 embed `blocks_prefilter.py`'s text in their own cells and
are committed with executed outputs, so extending that module would mean neither regenerated from
`_build` any more.

What it adds: `stability_prefilter_active_from` / `_active_to`, an activation window on the
prefilter. NB30 needs the mechanism live during ONE fold and inert everywhere else, so that a run
is anchor-identical up to its fold's start and the five fold segments can be stitched into a
single path in which no segment was scored by a screen that saw it.

Both default to the empty string, which means "always active", so NB29's runs are unaffected and
the anchor path - where `stability_prefilter_signal` is itself empty - never reaches the block.
"""

from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, CELL14_REPLACEMENTS_PREFILTER

PARAM_ADDITIONS_CROSSFIT = PARAM_ADDITIONS_PREFILTER.rstrip("'\n") + '''
    #: --- cross-fitting additions (NB30) ---
    #: ISO date from which the prefilter is active, inclusive. '' means "from the beginning".
    #: Outside the window `decide_trades` takes the incumbent path and writes no log entry, so an
    #: empty log on a fold's excluded dates is the evidence the mechanism really was inert there.
    stability_prefilter_active_from = ''
    #: ISO date at which the prefilter stops being active, EXCLUSIVE. '' means "to the end".
    stability_prefilter_active_to = ''
'''

_GUARD_OLD = "    if prefilter_signal:\n"
_GUARD_NEW = (
    "    # NB30: restrict the mechanism to one fold's dates. Outside the window the incumbent\n"
    "    # path runs unchanged and nothing is logged, so a run is bit-identical to the anchor\n"
    "    # before its fold starts and the stitched out-of-fold path is coherent.\n"
    "    prefilter_in_window = True\n"
    "    _prefilter_from = str(getattr(parameters, 'stability_prefilter_active_from', '') or '')\n"
    "    _prefilter_to = str(getattr(parameters, 'stability_prefilter_active_to', '') or '')\n"
    "    if _prefilter_from:\n"
    "        prefilter_in_window = prefilter_in_window and (\n"
    "            timestamp >= datetime.datetime.fromisoformat(_prefilter_from))\n"
    "    if _prefilter_to:\n"
    "        prefilter_in_window = prefilter_in_window and (\n"
    "            timestamp < datetime.datetime.fromisoformat(_prefilter_to))\n"
    "    if prefilter_signal and prefilter_in_window:\n"
)


def _with_activation_window(replacements: dict) -> dict:
    out = {}
    spliced = 0
    for key, value in replacements.items():
        if _GUARD_OLD in value:
            value = value.replace(_GUARD_OLD, _GUARD_NEW, 1)
            spliced += 1
        out[key] = value
    assert spliced == 1, f"expected exactly one prefilter guard to widen, found {spliced}"
    return out


CELL14_REPLACEMENTS_CROSSFIT = _with_activation_window(CELL14_REPLACEMENTS_PREFILTER)
