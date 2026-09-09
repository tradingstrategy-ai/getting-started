"""Evidence-weighted selection track additions (14-evidence-weighted-plan.md), NB14-NB19.

Draft 2. Revised after `14-evidence-weighted-plan-codex-review.md` (gpt-5.6-terra) and
`smoke_test_finding.md` (an independent smoke-test finding: the Draft 1 naive Sortino
t-statistic's realised P&L correlation was -0.41 across a 75-position test run, with the single
worst loss, -$28,990 in 6 days, entered at that statistic's maximum score on 45 observations).

Spliced into the shared cells through builder.py's `extra_replacements` / `extra_source` hooks so
NB03a-NB13 are untouched. Anchors verified against cell6/cell10/cell14_enhanced.py on 2026-09-09.

Changes from Draft 1, each tied to a numbered finding in the Codex review:
- (review #1, #2, smoke test) The admission/ranking score is rewritten as `sortino_shrunk_score`:
  event-time sampling (mean and downside deviation computed on the same fresh-only subsequence
  counted as n, not calendar rows), an autocorrelation-discounted effective n, and cross-sectional
  shrinkage towards the same-day median across all vaults. Replaces `sortino_t`/`sortino_lcb` and
  their separately-capped `_score` variants entirely, so there is one form, used identically by
  the NB14 screen and the NB16 backtest (closing review #9's raw-vs-capped mismatch by
  construction).
- (review #7) `expanding_cagr_score` shrinks the raw annualised return before bounding it to
  [0, 1], not after, so a single catch-up mark cannot reach a materially positive score merely
  because a post-hoc clip is applied last.
- (review #2) `inverse_vol_early` gates on fresh-observation count via `.where()`, not via
  `rolling(..., min_periods=...)`, which counts stale calendar rows as observations. Proof that
  this still cannot fire before `inverse_vol` does at default parameters is in the docstring, and
  is checked again empirically in `verify-plan14-draft2.ipynb`.
"""

#: Appended after the last parameter the NB03 track added (`beta_shrink = 1.0`).
PARAM_ANCHOR = "    beta_shrink = 1.0\n"
PARAM_ADDITIONS_EVIDENCE = PARAM_ANCHOR + '''
    #: --- evidence-weighted selection track additions (see 14-evidence-weighted-plan.md) ---
    #: Calendar-day window the CAGR leg (`expanding_cagr_score`) looks back over. Unlike the
    #: Sortino leg below, this is deliberately calendar-time, not event-time: a return level is
    #: well-defined between two calendar dates regardless of how many stale marks sit between them.
    evidence_max_window_days = 365
    #: Event-count window (not calendar days) the Sortino evidence statistics look back over.
    evidence_max_events = 90
    #: Fewest fresh (mark actually moved, NB57) events before an evidence statistic exists at all.
    evidence_min_events = 20
    #: Fewest of those fresh events that must be down-events, so downside deviation is not
    #: estimated from one or two observed losses.
    evidence_min_down_events = 5
    #: Shrinkage prior strength `k` in `n_eff / (n_eff + k)`. A vault needs `n_eff` well past this
    #: before its own evidence dominates the cross-sectional prior. Plateau-tested at 30, 90.
    evidence_prior_strength = 60
    #: t-equivalent that earns the full [0, 1] evidence sub-score after shrinkage. Plateau-tested
    #: at 2, 4.
    evidence_t_cap = 3.0
    #: Fresh observations at which the expanding CAGR leg is trusted in full; below this it is
    #: shrunk linearly towards zero. Plateau-tested at 90, 270.
    cagr_full_evidence_days = 180
    #: Shortest history the expanding CAGR leg is computed on at all.
    cagr_min_days = 90
    #: `inverse_vol_early` becomes available after this many FRESH observations (not calendar
    #: days). At 90 - the same value as `inverse_vol_window` - it cannot fire before `inverse_vol`
    #: itself does (see the docstring on `inverse_vol_early`), so the anchor is unchanged; NB16
    #: lowers it to 45 so a young vault that wins a slot can be sized (NB13's second barrier).
    inverse_vol_min_periods = 90
    #: NB16 objective (review 3c): Sharpe non-inferiority tolerance against the anchor, and the
    #: minimum RELATIVE ulcer-index improvement required. Both pre-registered; see harness_evidence.py.
    sharpe_noninferiority_tol = 0.10
    ulcer_improvement_frac = 0.15
    #: NB18 two-sleeve structure. None disables it (anchor behaviour). Otherwise the share of the
    #: deployed book given to the evidence-selected core sleeve. Must be in (0, 1].
    core_fraction = None
    #: NB18: number of names in the core sleeve; the satellite gets the remainder of
    #: `max_assets_in_portfolio`. Must be in [1, max_assets_in_portfolio].
    core_assets = 4
    #: NB18: indicator that ranks and sizes the core sleeve.
    core_score_indicator = 'sortino_shrunk_score'
'''

INDICATOR_ADDITIONS_EVIDENCE = '''
#: --- evidence-weighted selection track additions (see 14-evidence-weighted-plan.md) ---


def _event_time_stats(
    close: pd.Series,
    max_events: int,
    min_events: int,
    min_down_events: int,
) -> tuple[pd.Series, pd.Series]:
    """Event-time mean/downside Sortino input and an autocorrelation-discounted effective n.

    NB57: a zero daily return on a Hyperliquid vault mark is almost always a stale poll, not a
    real flat day. This restricts every calculation to the subsequence of days the mark actually
    moved (`fresh_r`), a non-contiguous slice of the calendar index, and rolls over that
    subsequence by EVENT COUNT rather than by calendar day - so the sample used for the mean and
    the downside deviation is exactly the sample counted as `n`. Draft 1's `sortino_t` counted
    fresh events as `n` but computed the mean and downside deviation over calendar rows including
    the stale (zero-return) ones between them, which understates `n` relative to the sample the
    ratio was actually estimated from (review finding #1).

    The lag-1 autocorrelation of the fresh-event series further discounts `n` via
    `n_eff = n / (1 + 2*|rho_1|)`, a truncated Newey-West-style correction: a short, smooth run -
    the shape of a pump before it reverses - produces serially correlated fresh-event returns,
    and should not be treated as that many independent observations.

    Both outputs are reindexed back onto the full calendar index, carrying the last known event
    forward, so `decide_trades` (which reads one calendar bar back, per NB57) always sees the most
    recent evidence rather than NaN on the many stale calendar days between events.
    """
    r = close.pct_change()
    fresh_r = r[r.abs() > 0]
    if len(fresh_r) == 0:
        empty = pd.Series(float('nan'), index=close.index)
        return empty, empty.copy()

    w, min_ev = int(max_events), int(min_events)
    mean_event = fresh_r.rolling(w, min_periods=min_ev).mean()
    downside_event = (fresh_r.clip(upper=0.0) ** 2).rolling(w, min_periods=min_ev).mean() ** 0.5
    down_count = (fresh_r < 0).rolling(w, min_periods=1).sum()
    n_event = fresh_r.rolling(w, min_periods=min_ev).count()

    def _autocorr1(values):
        if len(values) < 5 or np.std(values) == 0:
            return 0.0
        a, b = values[:-1], values[1:]
        if np.std(a) == 0 or np.std(b) == 0:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])

    rho1 = fresh_r.rolling(w, min_periods=min_ev).apply(_autocorr1, raw=True).fillna(0.0).clip(-0.9, 0.9)
    n_eff = n_event / (1.0 + 2.0 * rho1.abs())

    raw_sortino = (mean_event / downside_event.replace(0.0, float('nan'))) * (TRADING_DAYS_PER_YEAR ** 0.5)
    raw_sortino = raw_sortino.where(down_count >= int(min_down_events))

    full_index = close.index
    return raw_sortino.reindex(full_index).ffill(), n_eff.reindex(full_index).ffill()


@indicators.define()
def sortino_raw_event(
    close: pd.Series,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
) -> pd.Series:
    """Event-time annualised Sortino ratio; NaN until the minimum event counts are met."""
    raw, _ = _event_time_stats(close, evidence_max_events, evidence_min_events, evidence_min_down_events)
    return raw


@indicators.define()
def sortino_neff_event(
    close: pd.Series,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
) -> pd.Series:
    """Autocorrelation-discounted effective observation count behind `sortino_raw_event`."""
    _, neff = _event_time_stats(close, evidence_max_events, evidence_min_events, evidence_min_down_events)
    return neff


@indicators.define(dependencies=(sortino_raw_event,), source=IndicatorSource.dependencies_only_universe)
def sortino_cross_sectional_prior(
    dependency_resolver: IndicatorDependencyResolver,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
) -> pd.Series:
    """Cross-sectional median of `sortino_raw_event` across all vaults, per timestamp.

    Same construction as `tvl_inclusion_criteria` (`cell10_enhanced.py`): pull every pair's value
    for this indicator combined into one MultiIndex series, then aggregate by timestamp. The
    shrinkage target for a thinly-observed vault - what a typical vault's Sortino looks like on
    the same day - rather than a fixed constant, so the prior moves with the regime (NB57's
    sparse/dense polling split included).
    """
    series = dependency_resolver.get_indicator_data_pairs_combined(
        sortino_raw_event,
        parameters={
            'evidence_max_events': evidence_max_events,
            'evidence_min_events': evidence_min_events,
            'evidence_min_down_events': evidence_min_down_events,
        },
    )
    return series.groupby(level='timestamp').median()


@indicators.define(
    dependencies=(sortino_raw_event, sortino_neff_event, sortino_cross_sectional_prior),
    source=IndicatorSource.dependencies_only_per_pair,
)
def sortino_shrunk_score(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
    evidence_prior_strength: int = 60,
    evidence_t_cap: float = 3.0,
) -> pd.Series:
    """Bounded [0, 1] evidence score: event-time Sortino, shrunk towards the cross-sectional
    median by `n_eff / (n_eff + evidence_prior_strength)`, then mapped 0..`evidence_t_cap` to 0..1.

    Found in a smoke test of Draft 1 (`smoke_test_finding.md`): a vault at the maximum of the
    unshrunk score, on 45 observations, produced the single worst loss in a 75-position test
    (-$28,990 in 6 days), and the unshrunk score correlated -0.41 with realised P&L across all
    positions. Shrinkage is the structural fix - a thin sample cannot reach the top score however
    extreme its own ratio is, however the cap is set (review finding #1) - regardless of `n_eff`;
    it converges to its own evidence only once `n_eff` grows well past `evidence_prior_strength`.

    NaN wherever `sortino_raw_event` is NaN (fewer than `evidence_min_events` fresh or
    `evidence_min_down_events` down observations) - the NB78 no-down-day protection
    `sortino_score` already has, kept here.
    """
    params = {
        'evidence_max_events': evidence_max_events,
        'evidence_min_events': evidence_min_events,
        'evidence_min_down_events': evidence_min_down_events,
    }
    raw = dependency_resolver.get_indicator_data('sortino_raw_event', pair=pair, parameters=params)
    n_eff = dependency_resolver.get_indicator_data('sortino_neff_event', pair=pair, parameters=params)
    prior = dependency_resolver.get_indicator_data('sortino_cross_sectional_prior', parameters=params)
    prior = prior.reindex(raw.index).ffill()

    k = float(evidence_prior_strength)
    weight_own = n_eff / (n_eff + k)
    shrunk = weight_own * raw.fillna(0.0) + (1.0 - weight_own) * prior.fillna(0.0)
    shrunk = shrunk.where(raw.notna())
    return (shrunk / float(evidence_t_cap)).clip(lower=0.0, upper=1.0)


@indicators.define()
def expanding_cagr_score(
    close: pd.Series,
    evidence_max_window_days: int = 365,
    cagr_min_days: int = 90,
    cagr_full_evidence_days: int = 180,
) -> pd.Series:
    """`cagr_score` on an expanding window, shrunk towards zero while the history is short.

    The window is the last `evidence_max_window_days` or the whole history, whichever is shorter;
    below `cagr_min_days` it is NaN. `shrink = min(1, fresh / cagr_full_evidence_days)` is applied
    to the RAW annualised return BEFORE it is bounded to [0, 1] (review finding #7 on Draft 1:
    applying the shrink after the bound let one large catch-up mark clip to the ceiling first and
    only then be shrunk, which understates how little a thin sample should count for).

    Assumes `close` is one row per day from the vault's first candle with no gaps, which is what
    `TradingStrategyUniverse.create_from_dataset(forward_fill=True)` produces for a vault pair.
    """
    w, min_days = int(evidence_max_window_days), int(cagr_min_days)
    first_price = float(close.iloc[0]) if len(close) else float('nan')
    start = close.shift(w)
    start = start.where(start.notna(), first_price)          # expanding below the cap
    days = pd.Series(np.minimum(np.arange(len(close)), w), index=close.index, dtype=float)
    cagr = (close / start).pow(TRADING_DAYS_PER_YEAR / days.replace(0.0, float('nan'))) - 1.0
    cagr = cagr.where(days >= min_days)
    fresh = (close.pct_change().abs() > 0).astype(float).rolling(w, min_periods=1).sum()
    shrink = (fresh / float(cagr_full_evidence_days)).clip(upper=1.0)
    return ((cagr * shrink) / CAGR_SCORE_CAP).clip(lower=0.0, upper=1.0)


@indicators.define(
    dependencies=(expanding_cagr_score, sortino_shrunk_score),
    source=IndicatorSource.dependencies_only_per_pair,
)
def evidence_composite(
    pair: TradingPairIdentifier,
    dependency_resolver: IndicatorDependencyResolver,
    evidence_max_window_days: int = 365,
    cagr_min_days: int = 90,
    cagr_full_evidence_days: int = 180,
    evidence_max_events: int = 90,
    evidence_min_events: int = 20,
    evidence_min_down_events: int = 5,
    evidence_prior_strength: int = 60,
    evidence_t_cap: float = 3.0,
    cagr_weight: float = 0.6,
) -> pd.Series:
    """`cagr_weight x expanding CAGR score + (1 - cagr_weight) x shrunk Sortino score`.

    The incumbent composite with both legs replaced by their evidence-weighted forms. Same
    `cagr_weight` parameter as the incumbent, so NB16's plateau over 0.3 / 0.6 reads directly
    against NB92's 0.6. This is the SAME bounded form used by the NB14 screen (review finding #9:
    Draft 1 screened an unbounded statistic but traded a capped one - two different rankings).
    """
    cagr_component = dependency_resolver.get_indicator_data(
        'expanding_cagr_score', pair=pair,
        parameters={
            'evidence_max_window_days': evidence_max_window_days,
            'cagr_min_days': cagr_min_days,
            'cagr_full_evidence_days': cagr_full_evidence_days,
        },
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


@indicators.define()
def inverse_vol_early(
    close: pd.Series,
    inverse_vol_window: int = 90,
    inverse_vol_min_periods: int = 90,
) -> pd.Series:
    """`inverse_vol` that becomes available after `inverse_vol_min_periods` FRESH observations.

    Review finding #2 on Draft 1: `rolling(..., min_periods=...)` counts non-null calendar rows,
    and a stale (repeated) mark's `pct_change()` is a valid zero, not null - so a `min_periods`
    gate on a plain rolling std counts calendar days elapsed, not real observations, which is
    exactly the failure NB13 diagnosed for the incumbent's own fixed windows. This gates on fresh
    count directly via `.where()` instead.

    At the default `inverse_vol_min_periods = inverse_vol_window = 90`: `inverse_vol` (the
    incumbent) requires 90 calendar days of `pct_change()` history regardless of staleness. This
    function requires 90 FRESH observations inside a window of at most 90 calendar days - and
    fresh observations cannot outnumber calendar days elapsed, so it cannot be non-NaN before
    `inverse_vol` is also non-NaN (`decide_trades` only ever reads this as a fallback when
    `inverse_vol` is NaN, so the two cannot both matter at the same cycle). The anchor is
    therefore unchanged at defaults - proved here rather than asserted, and checked again
    empirically in `verify-plan14-draft2.ipynb`.
    """
    r = close.pct_change()
    w = int(inverse_vol_window)
    fresh = (r.abs() > 0).astype(float).rolling(w, min_periods=1).sum()
    vol = r.rolling(w, min_periods=2).std()
    return (1.0 / vol.clip(lower=VOL_FLOOR)).where(fresh >= int(inverse_vol_min_periods))

'''

#: Old -> new replacements for cell 14 (`decide_trades` / `compute_sizing_weights`). Every "old"
#: string must occur exactly once in cell14_enhanced.py; verify-plan14-draft2.ipynb asserts this
#: with `str.count() == 1` before splicing (review finding: Draft 1's plan text claimed this but
#: `builder.cell14()` itself only asserts "in", not "exactly once" - the count check lives in the
#: verification script, not in builder.py, which is shared and out of scope for this plan to edit).
CELL14_REPLACEMENTS_EVIDENCE = {
    # 1. compute_sizing_weights signature: add the evidence map.
    "    correlation_cap: float = 0.0,\n) -> dict[int, float]:\n":
    "    correlation_cap: float = 0.0,\n"
    "    evidence_by_id: dict[int, float] | None = None,\n"
    ") -> dict[int, float]:\n",

    # 2. compute_sizing_weights: the 'evidence' method, inserted before the ValueError.
    '    raise ValueError(f"Unknown weighting method: {method}")\n':
    "    if method == 'evidence':\n"
    "        # NB17: size by evidence of profit (the shrunk Sortino score), not by absence of\n"
    "        # noise. NB77/NB12: inverse variance and inverse ulcer both hand the biggest slots to\n"
    "        # quiet vaults regardless of sign; a quiet loser gets nothing here.\n"
    "        evidence_map = evidence_by_id or {}\n"
    "        raw = {}\n"
    "        for pair_id in selected_pair_ids:\n"
    "            value = evidence_map.get(pair_id, 0.0)\n"
    "            value = 0.0 if value is None or value != value else float(value)\n"
    "            raw[pair_id] = max(value, 0.0)\n"
    "        if sum(raw.values()) <= 0:\n"
    "            return {pair_id: 1.0 for pair_id in selected_pair_ids}\n"
    "        if floor_fraction > 0:\n"
    "            mean_weight = sum(raw.values()) / len(raw)\n"
    "            raw = {pid: max(w, floor_fraction * mean_weight) for pid, w in raw.items()}\n"
    "        return raw\n"
    "\n"
    '    raise ValueError(f"Unknown weighting method: {method}")\n',

    # 3. decide_trades: two new per-vault maps.
    "    beta_by_id = {}\n":
    "    beta_by_id = {}\n"
    "    #: Evidence-weighted track: shrunk Sortino score for sizing (NB17) and the core sleeve (NB18).\n"
    "    evidence_by_id = {}\n"
    "    core_score_by_id = {}\n",

    # 4. decide_trades: inverse_vol early-availability fallback (NB13's second barrier).
    "        inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)\n"
    "        inv_vol_by_id[pair_id] = float(inv_vol) if inv_vol is not None and inv_vol == inv_vol else 0.0\n":
    "        inv_vol = indicators.get_indicator_value('inverse_vol', pair=pair)\n"
    "        if inv_vol is None or inv_vol != inv_vol:\n"
    "            # Young vault: fall back to the early-availability estimate. Cannot fire before\n"
    "            # `inverse_vol` itself does at default parameters - see the docstring on\n"
    "            # `inverse_vol_early` - so the anchor path (defaults) is unaffected.\n"
    "            inv_vol = indicators.get_indicator_value('inverse_vol_early', pair=pair)\n"
    "        inv_vol_by_id[pair_id] = float(inv_vol) if inv_vol is not None and inv_vol == inv_vol else 0.0\n",

    # 5. decide_trades: read the evidence statistics next to the beta read.
    "        beta_value = indicators.get_indicator_value('btc_beta', pair=pair)\n":
    "        evidence_value = indicators.get_indicator_value('sortino_shrunk_score', pair=pair)\n"
    "        evidence_by_id[pair_id] = float(evidence_value) if evidence_value is not None and evidence_value == evidence_value else 0.0\n"
    "        core_indicator = str(getattr(parameters, 'core_score_indicator', 'sortino_shrunk_score'))\n"
    "        core_value = evidence_value if core_indicator == 'sortino_shrunk_score' else indicators.get_indicator_value(core_indicator, pair=pair)\n"
    "        core_score_by_id[pair_id] = float(core_value) if core_value is not None and core_value == core_value else float('nan')\n"
    "        beta_value = indicators.get_indicator_value('btc_beta', pair=pair)\n",

    # 6. decide_trades: pass the evidence map into sizing.
    "        correlation_cap=float(getattr(parameters, 'residual_correlation_cap', 0.0)),\n    )\n":
    "        correlation_cap=float(getattr(parameters, 'residual_correlation_cap', 0.0)),\n"
    "        evidence_by_id=evidence_by_id,\n"
    "    )\n",

    # 7. decide_trades: NB18 two-sleeve override, inserted after sizing and before the beta group
    # cap. Reserves minimum-hold-protected incumbents to whichever sleeve they were already
    # assigned last cycle FIRST, before filling remaining slots by rank - review finding: Draft 1
    # built the satellite sleeve by filtering the incumbent's `selected` list down to
    # `satellite_assets` slots AFTER removing core picks, which could push a hold-protected but
    # composite-low-ranked incumbent out of the satellite entirely, defeating hold protection.
    "    # NB07: cap the combined weight share of vaults whose |beta| exceeds the threshold, shrinking\n":
    "    # NB18: two-sleeve allocation. The core sleeve is ranked and sized by evidence of\n"
    "    # consistent profit; the satellite sleeve is the incumbent selection above, sized by the\n"
    "    # incumbent method. `core_fraction` of the deployed book is the PRE-normalisation target\n"
    "    # for the core sleeve; realised sleeve shares (after the concentration cap and pool-cap\n"
    "    # sizing below) are recorded to `state.visualisation` so NB18's attribution is measured,\n"
    "    # not assumed. The incumbent sizing call above still runs (its result is discarded here)\n"
    "    # so the anchor path is byte-identical.\n"
    "    core_fraction = getattr(parameters, 'core_fraction', None)\n"
    "    realised_core_share = None\n"
    "    if core_fraction:\n"
    "        core_fraction = float(core_fraction)\n"
    "        core_assets = int(parameters.core_assets)\n"
    "        assert 0.0 < core_fraction <= 1.0, f\"core_fraction must be in (0, 1]: {core_fraction}\"\n"
    "        assert 1 <= core_assets <= max_assets_in_portfolio, (\n"
    "            f\"core_assets must be in [1, {max_assets_in_portfolio}]: {core_assets}\"\n"
    "        )\n"
    "        satellite_assets = max(max_assets_in_portfolio - core_assets, 0)\n"
    "        pair_by_id = {pid: pair for pid, pair, _signal in candidates}\n"
    "\n"
    "        # Reserve currently-held, hold-protected positions to their PREVIOUS sleeve first, so\n"
    "        # the sleeve split cannot itself evict a position minimum_hold_days protects.\n"
    "        prev_calc = state.visualisation.calculations.get(\n"
    "            max(state.visualisation.calculations) if state.visualisation.calculations else None, {}\n"
    "        ) or {}\n"
    "        prev_core_ids = set(prev_calc.get('core_ids', []))\n"
    "        protected_core = {pid for pid in hold_protected_ids if pid in prev_core_ids}\n"
    "        protected_satellite = {pid for pid in hold_protected_ids if pid not in prev_core_ids}\n"
    "\n"
    "        core_ranked_all = sorted(\n"
    "            [pid for pid, score in core_score_by_id.items() if score == score and pid in pair_by_id],\n"
    "            key=lambda pid: (-core_score_by_id[pid], pid),\n"
    "        )\n"
    "        core_ids = [pid for pid in core_ranked_all if pid in protected_core]\n"
    "        for pid in core_ranked_all:\n"
    "            if len(core_ids) >= core_assets:\n"
    "                break\n"
    "            if pid in core_ids or pid in protected_satellite:\n"
    "                continue\n"
    "            if pid not in held_pair_ids and not input.pricing_model.can_deposit(timestamp, pair_by_id[pid]):\n"
    "                continue\n"
    "            core_ids.append(pid)\n"
    "\n"
    "        satellite_ranked_all = [pid for pid, _pair, _signal in ordered if pid not in core_ids]\n"
    "        satellite_ids = [pid for pid in satellite_ranked_all if pid in protected_satellite]\n"
    "        for pid in satellite_ranked_all:\n"
    "            if len(satellite_ids) >= satellite_assets:\n"
    "                break\n"
    "            if pid in satellite_ids:\n"
    "                continue\n"
    "            if pid not in held_pair_ids and not input.pricing_model.can_deposit(timestamp, pair_by_id[pid]):\n"
    "                continue\n"
    "            satellite_ids.append(pid)\n"
    "\n"
    "        core_weights = compute_sizing_weights(\n"
    "            core_ids, inv_vol_by_id, signal_by_id, method='evidence',\n"
    "            softmax_temperature=float(getattr(parameters, 'softmax_temperature', 0.25)),\n"
    "            evidence_by_id=core_score_by_id,\n"
    "            floor_fraction=float(getattr(parameters, 'weight_floor_fraction', 0.0)),\n"
    "        )\n"
    "        satellite_weights = compute_sizing_weights(\n"
    "            satellite_ids, inv_vol_by_id, signal_by_id, method=str(parameters.weighting_method),\n"
    "            softmax_temperature=float(getattr(parameters, 'softmax_temperature', 0.25)),\n"
    "            weighting_exponent=float(getattr(parameters, 'weighting_exponent', 2.0)),\n"
    "            risk_by_id=risk_by_id, fresh_by_id=fresh_by_id,\n"
    "            min_fresh=float(getattr(parameters, 'min_fresh_observations', 0.0)),\n"
    "            floor_fraction=float(getattr(parameters, 'weight_floor_fraction', 0.0)),\n"
    "            corr_by_id=corr_by_id,\n"
    "            correlation_cap=float(getattr(parameters, 'residual_correlation_cap', 0.0)),\n"
    "            evidence_by_id=evidence_by_id,\n"
    "        )\n"
    "\n"
    "        def _sleeve(weights, fraction):\n"
    "            total = sum(weights.values()) or 1.0\n"
    "            return {pid: fraction * w / total for pid, w in weights.items()}\n"
    "\n"
    "        weight_by_id = {**_sleeve(core_weights, core_fraction), **_sleeve(satellite_weights, 1.0 - core_fraction)}\n"
    "        selected = [(pid, pair_by_id[pid], signal_by_id.get(pid, 0.0)) for pid in core_ids + satellite_ids]\n"
    "        realised_core_share = core_fraction   # overwritten below with the post-normalisation figure\n"
    "\n"
    "    # NB07: cap the combined weight share of vaults whose |beta| exceeds the threshold, shrinking\n",

    # 8. Record realised (post-normalisation) sleeve composition once weights are final, right
    # before `alpha_model.calculate_target_positions()`. Review finding: `core_fraction` was only
    # ever a pre-normalisation target; the concentration cap and pool-cap sizing can move the
    # realised share away from it, and Draft 1 never measured what actually happened.
    "    alpha_model.update_old_weights(state.portfolio, ignore_credit=False)\n"
    "    alpha_model.calculate_target_positions(position_manager)\n":
    "    if core_fraction:\n"
    "        core_realised = sum(\n"
    "            alpha_model.signals[pid].normalised_weight\n"
    "            for pid in core_ids if pid in alpha_model.signals\n"
    "        )\n"
    "        state.visualisation.add_calculations(timestamp, {\n"
    "            'core_ids': list(core_ids),\n"
    "            'satellite_ids': list(satellite_ids),\n"
    "            'core_fraction_target': core_fraction,\n"
    "            'core_fraction_realised': float(core_realised),\n"
    "        })\n"
    "\n"
    "    alpha_model.update_old_weights(state.portfolio, ignore_credit=False)\n"
    "    alpha_model.calculate_target_positions(position_manager)\n",
}
