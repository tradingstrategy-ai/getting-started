"""Stability-leads track additions (20-stability-leads-plan.md), NB20-NB24.

Draft 2 of the plan, after `20-stability-leads-plan-codex-review.md` (gpt-6-astra).

Spliced into the shared cells through builder.py's `extra_replacements` / `extra_source` hooks,
on top of `blocks_evidence.py`, so NB03a-NB19 are untouched. Anchors verified against
cell6/cell10/cell14_enhanced.py on 2026-09-13.

Three mechanisms live here:

- `VOL_DROP_LOG`: a read-only record of what the pre-registered vol-matched drop actually removed
  at each decision. NB21's diagnostics and NB22's exclusion-list derivation read the trading
  pipeline's own decision rather than reconstructing it offline. The review found an offline
  reconstruction could not mirror `decide_trades` - it would miss `is_good_pair`, the quarantine
  list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, strict admission and the tie order.
- `joint_loss_frequency` and the complementary-selection block: NB22's mechanism. From the
  incumbent's top `complementary_pool_size` candidates by composite score, keep the
  `max_assets_in_portfolio` that lose least often when the cohort loses, and size them exactly as
  the incumbent does.
- `cagr_sortino_shrunk_weight`: NB23's mechanism. The incumbent composite with only its Sortino
  leg swapped for the event-time shrunk score.
"""

from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE

#: Appended after the evidence track's own parameter block, so a stability notebook carries both.
PARAM_ADDITIONS_STABILITY = PARAM_ADDITIONS_EVIDENCE + '''
    #: --- stability-leads track additions (see 20-stability-leads-plan.md) ---
    #: NB22. 0 disables complementary selection entirely (anchor behaviour). Otherwise the number
    #: of top-ranked candidates by composite score that the joint-loss screen chooses from; the
    #: basket size itself stays `max_assets_in_portfolio`.
    complementary_pool_size = 0
    #: NB22. Calendar window `joint_loss_frequency` measures co-movement over.
    joint_loss_window_days = 180
    #: NB22. Fewest cohort-down days inside that window on which THIS vault also reported, before
    #: a joint-loss frequency exists at all. Below this the vault has no estimate and is NOT
    #: assumed to be complementary.
    joint_loss_min_events = 10
    #: NB22. Fewest vaults that must have posted a FRESH mark on a day before that day's
    #: cross-sectional median is meaningful enough to call the cohort up or down.
    cohort_min_reporting = 5
'''

INDICATOR_ADDITIONS_STABILITY = '''
#: --- stability-leads track additions (see 20-stability-leads-plan.md) ---

#: Per-cycle record of what the vol-matched drop actually removed, written by `decide_trades`
#: (see CELL14_REPLACEMENTS_STABILITY). Same rationale as `SLEEVE_LOG`: a module-level dict, not
#: `state.visualisation.add_calculations`, because the framework writes `unallocatable_signals`
#: at the same timestamp and overwrites rather than merges. Cleared and snapshotted once per
#: `run_variant()` call by `run_and_record()` in harness_stability.py.
VOL_DROP_LOG: dict = {}

#: Per-cycle record of the complementary-selection screen (NB22), same lifecycle.
COMPLEMENT_LOG: dict = {}


@indicators.define()
def fresh_daily_return(close: pd.Series) -> pd.Series:
    """Daily mark-to-mark return, with stale (unmoved) marks left as exact zero.

    NB57: a zero return on a Hyperliquid vault mark is almost always a stale poll rather than a
    real flat day. This does not drop them - `joint_loss_frequency` needs a common calendar index
    across vaults to ask "did these two lose on the same day" - but nothing downstream counts a
    zero as either a loss or a gain.
    """
    return close.pct_change()


@indicators.define(dependencies=(fresh_daily_return,), source=IndicatorSource.dependencies_only_universe)
def cohort_down_flag(
    dependency_resolver: IndicatorDependencyResolver,
    cohort_min_reporting: int = 5,
) -> pd.Series:
    """1.0 on days the median REPORTING vault lost money, 0.0 when it gained, NaN when too few
    vaults reported to tell.

    The reference "bad day" for the whole vault cohort, built the same way as
    `sortino_cross_sectional_prior`: pull every pair's series combined into one MultiIndex frame
    and aggregate by timestamp. The cohort median rather than BTC, because most of these vaults
    are market neutral by construction and their bad days are not BTC's bad days.

    The median is taken over FRESH marks only. A first version of this took it over every vault
    in the universe, and the flag was almost never set after the NB57 polling-density break:
    by 2026 most vaults are stale on most calendar days, a stale mark is an exact zero return,
    and the median of a column that is mostly exact zeros is exactly zero, which is not negative.
    The resulting `joint_loss_frequency` was NaN for every vault on every date, and the selection
    block silently degenerated into "keep the six lowest pair ids", which lost 37 percentage
    points of CAGR in the splice verification run. Restricting the median to vaults that actually
    marked that day is the fix; requiring `cohort_min_reporting` of them stops a day on which two
    vaults reported from defining a cohort-wide loss.
    """
    series = dependency_resolver.get_indicator_data_pairs_combined(fresh_daily_return)
    fresh = series[series != 0.0].dropna()
    if len(fresh) == 0:
        return pd.Series(dtype=float)
    by_day = fresh.groupby(level='timestamp')
    flag = (by_day.median() < 0).astype(float)
    return flag.where(by_day.count() >= int(cohort_min_reporting))


@indicators.define(
    dependencies=(fresh_daily_return, cohort_down_flag),
    source=IndicatorSource.dependencies_only_per_pair,
)
def joint_loss_frequency(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    joint_loss_window_days: int = 180,
    joint_loss_min_events: int = 10,
    cohort_min_reporting: int = 5,
) -> pd.Series:
    """Share of cohort-down days on which this vault ALSO lost, over a rolling calendar window.

    `P(vault down | cohort down)`. Low means the vault tends to hold up when the rest of the
    cohort is losing, which is the property an equity curve needs: six vaults that each look
    stable alone but all lose on the same days produce a portfolio that is not stable at all.
    High means it simply goes down with everything else.

    This is a per-vault proxy for a basket-level objective. It scores each candidate against the
    cohort, not against the other five names actually chosen, so it cannot see a pair of vaults
    that are individually complementary to the cohort but identical to each other. That is a
    deliberate simplification: a true pairwise-greedy basket search needs a co-movement matrix
    inside `decide_trades`, and this is the cheapest first test of whether the effect exists at
    all. NB22 reports the realised pairwise structure of the chosen baskets so the gap between
    the proxy and the objective is measurable rather than assumed.

    The denominator counts only cohort-down days on which THIS vault also posted a fresh mark.
    Without that restriction a vault that simply stops reporting never registers a loss, scores a
    joint-loss frequency of zero, and is selected as maximally complementary - the selection
    would reward silence. Requiring the vault to have been observed makes a quiet vault
    unestimated rather than perfect.

    NaN until at least `joint_loss_min_events` such days sit inside the window. A vault with no
    estimate is NOT treated as complementary; the selection block sorts NaN last.
    """
    r = dependency_resolver.get_indicator_data('fresh_daily_return', pair=pair)
    cohort_down = dependency_resolver.get_indicator_data(
        'cohort_down_flag', parameters={'cohort_min_reporting': cohort_min_reporting},
    )
    cohort_down = cohort_down.reindex(r.index)

    w = int(joint_loss_window_days)
    cohort_is_down = (cohort_down == 1.0).astype(float)
    # `r.abs() > 0`, the track's own idiom, not `r != 0.0`: a NaN is not equal to 0.0, so the
    # naive form counts a missing observation as a reported day - the same reward-silence class of
    # bug the docstring above says was fixed. Immaterial on this archive, where the only NaN is
    # the first row of each series, but wrong.
    reported = (r.abs() > 0).astype(float)
    observable = cohort_is_down * reported
    own_down = (r < 0).astype(float)

    joint = (own_down * observable).rolling(w, min_periods=1).sum()
    denominator = observable.rolling(w, min_periods=1).sum()
    frequency = joint / denominator.replace(0.0, float('nan'))
    return frequency.where(denominator >= int(joint_loss_min_events))


@indicators.define(
    dependencies=(cagr_score, sortino_shrunk_score),
    source=IndicatorSource.dependencies_only_per_pair,
)
def cagr_sortino_shrunk_weight(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    cagr_lookback_days: int = 360,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
    evidence_prior_strength: int = 60,
    evidence_t_cap: float = 3.0,
    cagr_weight: float = 0.6,
) -> pd.Series:
    """The incumbent composite (`cagr_sortino_weight`) with ONLY its Sortino leg swapped.

    `cagr_weight x cagr_score(cagr_lookback_days) + (1 - cagr_weight) x sortino_shrunk_score`.
    The CAGR leg is the incumbent's own, untouched, so the composite still needs 360 days of
    history and still cannot reach the young cohort NB13 found. This re-ranks the OLD cohort.

    It is a component replacement, not an isolated test of shrinkage or of event time: the
    replacement leg changes horizon (up to 90 mark events rather than 45 calendar days),
    shrinkage, scaling and saturation at once. Its NaN behaviour also differs from
    `sortino_score`'s, so the set of admitted candidates is NOT guaranteed identical even though
    the CAGR gate is. NB23 measures exactly how much the traded book changes before sweeping
    anything.
    """
    cagr_component = dependency_resolver.get_indicator_data(
        'cagr_score', pair=pair, parameters={'cagr_lookback_days': cagr_lookback_days},
    )
    sortino_component = dependency_resolver.get_indicator_data(
        'sortino_shrunk_score', pair=pair,
        parameters={
            'evidence_max_events': evidence_max_events,
            'evidence_min_events': evidence_min_events,
            'evidence_min_down_events': evidence_min_down_events,
            'evidence_prior_strength': evidence_prior_strength,
            'evidence_t_cap': evidence_t_cap,
        },
    )
    return cagr_weight * cagr_component + (1.0 - cagr_weight) * sortino_component
'''

#: Two splices into `decide_trades`. Both anchors verified unique in cell14_enhanced.py.
#:
#: 1. Read-only logging of the vol-matched drop. The branch only executes when the drop is
#:    actually enabled AND the pool is larger than N, so the anchor path never reaches it -
#:    asserted rather than assumed by `assert_anchor_parity()` in harness_stability.py.
#: 2. The complementary-downside screen, placed after the drop and before ranking, so it operates
#:    on exactly the candidate set the incumbent would have ranked. Disabled at
#:    `complementary_pool_size = 0`, which is the default, so the anchor path skips it too.
CELL14_REPLACEMENTS_STABILITY = {
    "        dropped_ids = {item[0] for item in by_vol[:vol_matched_drop]}\n"
    "        candidates = [item for item in candidates if item[0] not in dropped_ids]\n":

    "        dropped_ids = {item[0] for item in by_vol[:vol_matched_drop]}\n"
    "        # Stability-leads track (NB21, NB22): record what the drop actually removed, so the\n"
    "        # diagnostics read this decision rather than reconstructing it offline and missing\n"
    "        # the quality gate, quarantine, blacklist, mask and tie order applied above.\n"
    "        _address_of = {item[0]: str(item[1].pool_address).lower() for item in candidates}\n"
    "        VOL_DROP_LOG[timestamp] = {\n"
    "            'pool_size': len(candidates),\n"
    "            'dropped_ids': sorted(dropped_ids),\n"
    "            'dropped_addresses': sorted(_address_of[pid] for pid in dropped_ids),\n"
    "            'candidate_addresses': sorted(_address_of.values()),\n"
    "            'inv_vol': {_address_of[pid]: float(inv_vol_by_id.get(pid, 0.0)) for pid in _address_of},\n"
    "            'signal': {_address_of[pid]: float(signal_by_id.get(pid, 0.0)) for pid in _address_of},\n"
    "            'no_estimate_dropped': sorted(\n"
    "                _address_of[pid] for pid in dropped_ids if inv_vol_by_id.get(pid, 0.0) == 0.0\n"
    "            ),\n"
    "        }\n"
    "        candidates = [item for item in candidates if item[0] not in dropped_ids]\n",

    "    # Rank by composite (selection), but SIZE by inverse volatility (linear weighting).\n"
    "    ordered = sorted(candidates, key=lambda item: (-item[2], item[0]))\n":

    "    # Complementary downside selection (NB22, 20-stability-leads-plan.md). Take the top\n"
    "    # `complementary_pool_size` candidates by composite score, then keep the\n"
    "    # `max_assets_in_portfolio` of them that lose least often when the cohort loses. Sizing\n"
    "    # below is untouched - this changes WHICH names are held, not how much of each.\n"
    "    complementary_pool_size = int(getattr(parameters, 'complementary_pool_size', 0) or 0)\n"
    "    if complementary_pool_size > 0:\n"
    "        basket_size = int(parameters.max_assets_in_portfolio)\n"
    "        joint_loss_by_id = {}\n"
    "        for _pair_id, _pair, _signal in candidates:\n"
    "            value = indicators.get_indicator_value('joint_loss_frequency', pair=_pair)\n"
    "            joint_loss_by_id[_pair_id] = (\n"
    "                float(value) if value is not None and value == value else float('nan')\n"
    "            )\n"
    "        pool = sorted(candidates, key=lambda item: (-item[2], item[0]))[:complementary_pool_size]\n"
    "        # NaN sorts last: no co-movement estimate is not evidence of complementarity.\n"
    "        def _complement_key(item):\n"
    "            value = joint_loss_by_id[item[0]]\n"
    "            missing = value != value\n"
    "            return (1 if missing else 0, 0.0 if missing else value, item[0])\n"
    "        kept = sorted(pool, key=_complement_key)[:basket_size]\n"
    "        kept_ids = {item[0] for item in kept}\n"
    "        COMPLEMENT_LOG[timestamp] = {\n"
    "            'pool_size': len(candidates),\n"
    "            'screened_pool': [str(item[1].pool_address).lower() for item in pool],\n"
    "            'kept': [str(item[1].pool_address).lower() for item in kept],\n"
    "            'incumbent_top': [str(item[1].pool_address).lower() for item in pool[:basket_size]],\n"
    "            'joint_loss': {\n"
    "                str(item[1].pool_address).lower(): joint_loss_by_id[item[0]] for item in pool\n"
    "            },\n"
    "            'missing_estimates': sum(\n"
    "                1 for item in pool if joint_loss_by_id[item[0]] != joint_loss_by_id[item[0]]\n"
    "            ),\n"
    "        }\n"
    "        candidates = [item for item in candidates if item[0] in kept_ids]\n"
    "        if not candidates:\n"
    "            return []\n"
    "\n"
    "    # Rank by composite (selection), but SIZE by inverse volatility (linear weighting).\n"
    "    ordered = sorted(candidates, key=lambda item: (-item[2], item[0]))\n",
}
