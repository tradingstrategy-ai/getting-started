"""Drop-decomposition additions (NB26), on top of blocks_stability.py.

Kept in a SEPARATE module rather than added to `blocks_stability.py`, because NB20-NB25 embed
that module's text in their own cells and are committed with executed outputs. Extending the
shared module would mean none of them regenerated from `_build` any more, and re-running five
notebooks to add a branch none of them takes is the wrong trade. A notebook that wants the
decomposition splices this module instead of the stability one; a notebook that does not is
untouched.

What it adds: `vol_drop_mode`, which separates the two filters the incumbent sort conflates.
`inverse_vol` needs 90 observations, a vault without them is stored as 0.0, and 0.0 is the
smallest possible sort key - so every UNMEASURED vault is removed before any measured one. NB21
measured that at 70.9% of removals at N = 30, which means `drop_30` is roughly 21
data-availability removals plus 9 genuine volatility removals and nobody knows which half carried
the result.
"""

from blocks_stability import PARAM_ADDITIONS_STABILITY, CELL14_REPLACEMENTS_STABILITY

PARAM_ADDITIONS_DROP_MODES = PARAM_ADDITIONS_STABILITY.rstrip("'\n") + '''
    #: --- drop-decomposition additions (NB26) ---
    #: How `vol_matched_drop_count` chooses what to remove.
    #:
    #: - ``incumbent``: the original sort verbatim, ascending by `inverse_vol` with a missing
    #:   estimate encoded as 0.0. The default, so a notebook that does not ask for a mode gets
    #:   exactly the behaviour NB15-NB25 ran on.
    #: - ``measured_only``: the N most volatile vaults that HAVE an estimate; an unmeasured vault
    #:   is never removed. What the control was always described as doing.
    #: - ``unmeasured_only``: vaults with no estimate, and never a measured one however volatile.
    #:   The other half of what the incumbent actually does.
    #: - ``random``: N candidates by a seeded deterministic permutation. The null the drop has
    #:   never had - it separates "this filter selects well" from "holding fewer names on this
    #:   window happened to help".
    vol_drop_mode = 'incumbent'
    #: Seed for ``vol_drop_mode = 'random'``, mixed with the decision date so the draw differs
    #: across cycles and is reproducible across runs.
    vol_drop_seed = 0
'''

#: The incumbent branch below is character-identical to the line it replaces, and the guard
#: around the whole block is unchanged, so `vol_drop_mode = 'incumbent'` reproduces every earlier
#: run bit for bit. Verified: the anchor matches `BASELINE` on all ten metrics and `drop_30`
#: returns 0.489942 / 2.747391, the same figures NB15 and NB21 recorded.
_DROP_ANCHOR = (
    "        by_vol = sorted(candidates, key=lambda item: inv_vol_by_id.get(item[0], 0.0))\n"
    "        dropped_ids = {item[0] for item in by_vol[:vol_matched_drop]}\n"
)

_DROP_MODES = (
    "        # NB26: the incumbent sort conflates two filters. `inverse_vol` needs 90\n"
    "        # observations, a vault without them is stored as 0.0, and 0.0 is the smallest\n"
    "        # possible key - so every UNMEASURED vault sorts ahead of every measured one and is\n"
    "        # removed first. These modes separate the two so each can be tested on its own.\n"
    "        vol_drop_mode = str(getattr(parameters, 'vol_drop_mode', 'incumbent'))\n"
    "        measured = [i for i in candidates if inv_vol_by_id.get(i[0], 0.0) > 0.0]\n"
    "        unmeasured = [i for i in candidates if inv_vol_by_id.get(i[0], 0.0) <= 0.0]\n"
    "        if vol_drop_mode == 'incumbent':\n"
    "            by_vol = sorted(candidates, key=lambda item: inv_vol_by_id.get(item[0], 0.0))\n"
    "        elif vol_drop_mode == 'measured_only':\n"
    "            by_vol = sorted(measured, key=lambda item: (inv_vol_by_id[item[0]], item[0]))\n"
    "        elif vol_drop_mode == 'unmeasured_only':\n"
    "            by_vol = sorted(unmeasured, key=lambda item: item[0])\n"
    "        elif vol_drop_mode == 'random':\n"
    "            # Deterministic seeded permutation from a PRIVATE generator instance, so there is\n"
    "            # no shared RNG state a later run in the same kernel could advance, and the draw\n"
    "            # is reproducible from `(vol_drop_seed, decision date)` alone.\n"
    "            #\n"
    "            # The first version of this sorted by `(pair_id * 2654435761 + key) % 4294967291`\n"
    "            # with the seed and the date folded into `key` ADDITIVELY. That is not a\n"
    "            # permutation: adding a common constant before sorting only ROTATES one fixed\n"
    "            # ring order, and the largest offset the ten seeds and 126 decision dates reach\n"
    "            # (about 9.7e6) is far below the mean gap between the hashed values of ~148\n"
    "            # candidates spread over 4.29e9 (about 2.9e7), so the rotation never crossed an\n"
    "            # element. Every seed and every date drew the SAME set: the ten draws were one\n"
    "            # draw run ten times, and `null_median` equalled `null_best` on every metric.\n"
    "            # Seeding a generator instead mixes the key into every bit of the stream.\n"
    "            _key = int(getattr(parameters, 'vol_drop_seed', 0)) * 1000003 + timestamp.toordinal()\n"
    "            _pool = sorted(candidates, key=lambda item: item[0])\n"
    "            by_vol = [_pool[i] for i in np.random.default_rng(_key).permutation(len(_pool))]\n"
    "        else:\n"
    "            raise ValueError(f'unknown vol_drop_mode {vol_drop_mode!r}')\n"
    "        dropped_ids = {item[0] for item in by_vol[:vol_matched_drop]}\n"
)

_EXTRA_LOG = (
    "            'mode': vol_drop_mode,\n"
    "            'measured_pool': len(measured),\n"
    "            'unmeasured_pool': len(unmeasured),\n"
)


def _with_drop_modes(replacements: dict) -> dict:
    """Return a copy of the stability replacements with the drop block widened to take a mode."""
    out = {}
    for key, value in replacements.items():
        if key.lstrip().startswith("dropped_ids = {item[0] for item in by_vol"):
            # Widen the anchor to include the sort line, and splice the mode branch in its place.
            key = _DROP_ANCHOR + key.split("\n", 1)[1]
            value = _DROP_MODES + value.split("\n", 1)[1]
            value = value.replace(
                "            'pool_size': len(candidates),\n",
                "            'pool_size': len(candidates),\n" + _EXTRA_LOG,
            )
        out[key] = value
    return out


CELL14_REPLACEMENTS_DROP_MODES = _with_drop_modes(CELL14_REPLACEMENTS_STABILITY)
