"""Stable-selection track additions (28-stable-selection-plan.md), NB28-NB31.

Built on top of `blocks_drop_modes.py`, which is built on `blocks_stability.py`, by transforming
their replacement dicts. Standing rule 3: a new shared module never edits an existing one, because
NB14-NB26 are committed with executed outputs and embed those modules' text verbatim.

What it adds:

- `stability_prefilter`: at each decision, among the candidates that reach the ranking step, read
  signal `S` at T-1 and exclude the least-stable fraction (or count) of the candidates for which
  `S` is FINITE, then rank and size the survivors exactly as the incumbent does. `q = 0` is the
  anchor. `S = inverse_vol` with a count is NB26's `measured_only` drop, and the verification
  notebook asserts that equivalence numerically rather than assuming it.
- `PREFILTER_LOG`: the candidate set, every signal value, its finite flag, the excluded set and
  the five counts, per decision. NB28's screen reads candidate membership from here rather than
  reconstructing it, because an offline reconstruction cannot mirror `is_good_pair`, the
  quarantine list, `MANUAL_BLACKLIST`, `MASKED_VAULTS`, the momentum gate or the tie order.
- `fresh_event_concentration`: the event-time sibling of `residual_event_concentration`, measured
  over price-CHANGING marks rather than calendar days, with a causal per-event beta.

A note on what the plan does NOT claim. `fresh_event_concentration` is not polling-invariant: the
set of events depends on the poll schedule, and a vault polled twice as often has different
events. Its claim is narrower - invariance to inserting UNCHANGED marks at new intermediate
timestamps - and the verification notebook tests exactly that and nothing more.
"""

from blocks_drop_modes import PARAM_ADDITIONS_DROP_MODES, CELL14_REPLACEMENTS_DROP_MODES

PARAM_ADDITIONS_PREFILTER = PARAM_ADDITIONS_DROP_MODES.rstrip("'\n") + '''
    #: --- stable-selection additions (28-stable-selection-plan.md) ---
    #: Indicator name read at T-1 to rank candidates by stability. '' disables the whole block,
    #: which is the default, so every earlier notebook's behaviour is unchanged and the anchor
    #: path never reaches the splice.
    stability_prefilter_signal = ''
    #: Share of the FINITE-signal candidates to exclude. Not a share of the whole pool: a signal
    #: with a higher NaN rate filters a smaller share of the candidates at the same `q`, which is
    #: why every run reports the realised excluded share and comparisons across signals are made
    #: at matched REALISED share rather than at matched `q`.
    stability_prefilter_fraction = 0.0
    #: Exclude exactly this many instead, when > 0. Present so `inverse_vol` with a count
    #: reproduces NB26's `measured_only` drop family member for member.
    stability_prefilter_count = 0
    #: 'low' = a SMALLER signal value means a less stable vault (e.g. `inverse_vol`);
    #: 'high' = a LARGER value means less stable (e.g. `ulcer_index_180`).
    stability_prefilter_direction = 'low'
    #: Exclude candidates whose signal is not finite. DIAGNOSTIC only: a strict run cannot inherit
    #: a permissive signal's gate-5 pass, because gate 5 is a complete-case statistic and
    #: missingness-as-exclusion is precisely the behaviour it does not test.
    stability_prefilter_strict = False
    #: >= 0 permutes the FINITE signal values within each decision date, leaving every NaN
    #: attached to its own vault. That destroys the signal's ranking information and nothing else;
    #: permuting the NaNs too would also destroy WHICH vault is unmeasured, which is a different
    #: null from the one gate 9 asks for.
    stability_prefilter_null_seed = -1
    #: `fresh_event_concentration`: how many FINITE residual events the window holds. 90 events
    #: to match `sortino_shrunk_score`'s event budget, which needs about 120 raw events because
    #: the first `FRESH_EVENT_BETA_MIN` carry no beta.
    fresh_event_window = 90
    #: How many of the window's largest positive residual events form the numerator. 5, matching
    #: `residual_event_concentration` on the calendar clock, so the paired difference between
    #: them in NB28 differs only in the clock and not in the statistic.
    fresh_event_top_n = 5
'''

INDICATOR_ADDITIONS_PREFILTER = '''
#: --- stable-selection additions (28-stable-selection-plan.md) ---

#: Per-cycle record of the stability prefilter, written by `decide_trades`. Same lifecycle and
#: same rationale as `VOL_DROP_LOG`: cleared and snapshotted once per run by `run_and_record()`
#: in harness_rules.py, which redefines the harness_stability.py version to know about this log.
PREFILTER_LOG: dict = {}

#: Minimum matched (vault event, BTC interval) pairs strictly preceding an event before that
#: event gets a beta at all. Below it the event has no residual and is not counted.
FRESH_EVENT_BETA_MIN = 30


def fresh_event_table(
    close: pd.Series,
    beta_window: int = 90,
    beta_min: int = FRESH_EVENT_BETA_MIN,
) -> pd.DataFrame:
    """Event-time returns, causal betas and residuals for one vault.

    An event `j` spans `(t_{j-1}, t_j]` between consecutive marks at which the price actually
    CHANGED. The vault's event return is `log(P[t_j] / P[t_{j-1}])` and the matched BTC return is
    BTC's log return compounded over the same interval. `t_0` is the first timestamp of the
    series, whose price is by construction the value the first change moved away from.

    The beta applied to event `j` is estimated from matched events STRICTLY PRECEDING `j` -
    a rolling window of `beta_window` events shifted by one, with at least `beta_min` of them.
    One causal beta per event, rather than one evaluation-time beta applied retrospectively to
    the whole history, which is what `residual_event_concentration` does on the calendar clock.

    :return:
        Frame indexed by event end timestamp with columns ``start``, ``vault_return``,
        ``btc_return``, ``beta`` and ``residual``. Empty when the series has fewer than two
        distinct marks.
    """
    price = close.dropna()
    if len(price) < 2:
        return pd.DataFrame(columns=["start", "vault_return", "btc_return", "beta", "residual"])
    changed = price.ne(price.shift(1))
    # The first mark opens the series; it is not a change away from anything.
    changed.iloc[0] = False
    events = price[changed]
    if len(events) < 1:
        return pd.DataFrame(columns=["start", "vault_return", "btc_return", "beta", "residual"])

    end_ts = pd.DatetimeIndex(events.index)
    start_ts = pd.DatetimeIndex([price.index[0]]).append(end_ts[:-1])
    end_px = events.to_numpy(dtype=float)
    start_px = np.concatenate([[float(price.iloc[0])], end_px[:-1]])
    with np.errstate(divide="ignore", invalid="ignore"):
        vault_return = np.log(end_px / start_px)

    # BTC compounded over each interval, from the cumulative log return evaluated at the two
    # endpoints. `asof` rather than `reindex`, so an endpoint that falls on a day BTC has no bar
    # for (there are none in this archive, but the archive is not a guarantee) takes the last
    # known level instead of becoming NaN and silently dropping the event.
    span = pd.date_range(price.index[0] - pd.Timedelta(days=7), price.index[-1], freq="1D")
    btc_log_cum = np.log1p(_btc_daily_returns_for(span).clip(lower=-0.99)).cumsum()
    btc_return = (
        btc_log_cum.reindex(end_ts, method="ffill").to_numpy()
        - btc_log_cum.reindex(start_ts, method="ffill").to_numpy()
    )

    frame = pd.DataFrame(
        {"start": start_ts, "vault_return": vault_return, "btc_return": btc_return},
        index=end_ts,
    )
    matched = frame["vault_return"].where(np.isfinite(frame["btc_return"]))
    exogenous = frame["btc_return"].where(np.isfinite(frame["vault_return"]))
    w, m = int(beta_window), int(beta_min)
    covariance = matched.rolling(w, min_periods=m).cov(exogenous).shift(1)
    variance = exogenous.rolling(w, min_periods=m).var().shift(1)
    frame["beta"] = covariance / variance.replace(0.0, float("nan"))
    frame["residual"] = frame["vault_return"] - frame["beta"] * frame["btc_return"]
    return frame


def fresh_event_concentration_frame(
    close: pd.Series,
    fresh_event_window: int = 90,
    fresh_event_top_n: int = 5,
    beta_window: int = 90,
    beta_min: int = FRESH_EVENT_BETA_MIN,
) -> pd.DataFrame:
    """The statistic and its window span, on the daily index, forward-filled from event time.

    Share of the window's positive residual return delivered by its `fresh_event_top_n` largest
    positive residual events, over the latest `fresh_event_window` FINITE residual events. NaN
    until that many exist, which needs at least `fresh_event_window + beta_min` raw events
    because the first `beta_min` carry no beta.

    :return:
        Frame on `close.index` with columns ``concentration`` and ``span_days``, the latter the
        calendar span of the window each value was computed over.
    """
    empty = pd.DataFrame(
        {"concentration": np.nan, "span_days": np.nan}, index=close.index,
    )
    table = fresh_event_table(close, beta_window=beta_window, beta_min=beta_min)
    if not len(table):
        return empty
    residual = table["residual"].replace([np.inf, -np.inf], np.nan).dropna()
    w, n = int(fresh_event_window), int(fresh_event_top_n)
    if len(residual) < w:
        return empty
    positive = residual.clip(lower=0.0)
    top = positive.rolling(w, min_periods=w).apply(
        lambda a: float(np.sort(a)[-n:].sum()), raw=True,
    )
    denominator = positive.rolling(w, min_periods=w).sum().replace(0.0, np.nan)
    concentration = top / denominator
    ordinals = pd.Series(residual.index.map(pd.Timestamp.toordinal), index=residual.index, dtype=float)
    span = ordinals - ordinals.shift(w - 1)
    out = pd.DataFrame({"concentration": concentration, "span_days": span})
    return out.reindex(close.index, method="ffill")


@indicators.define()
def fresh_event_concentration(
    close: pd.Series,
    fresh_event_window: int = 90,
    fresh_event_top_n: int = 5,
) -> pd.Series:
    """Event-time sibling of `residual_event_concentration`. High means spiky.

    See `fresh_event_concentration_frame`. The calendar version asks "how much of the last 180
    DAYS' upside came from five days"; this asks "how much of the last 90 price MOVES' upside
    came from five moves". On a cohort where most vaults are stale on most days those are
    different questions, and NB28 measures which of them predicts forward stability by a paired
    difference rather than by two separate intervals.
    """
    return fresh_event_concentration_frame(
        close, fresh_event_window=fresh_event_window, fresh_event_top_n=fresh_event_top_n,
    )["concentration"]


@indicators.define()
def fresh_event_window_span(
    close: pd.Series,
    fresh_event_window: int = 90,
    fresh_event_top_n: int = 5,
) -> pd.Series:
    """Calendar days spanned by the window `fresh_event_concentration` was computed over.

    Reported rather than gated. A vault polled densely and a vault polled sparsely reach 90
    events over very different calendar spans, and the statistic is comparable across them only
    to the extent that span is similar. NB28 prints the distribution.
    """
    return fresh_event_concentration_frame(
        close, fresh_event_window=fresh_event_window, fresh_event_top_n=fresh_event_top_n,
    )["span_days"]
'''

#: Splice into `decide_trades`, placed AFTER the volatility-matched drop and BEFORE the NB22
#: complementary screen and the ranking sort, so it operates on exactly the candidate set the
#: incumbent would have ranked. Disabled at `stability_prefilter_signal = ''`, which is the
#: default, so the anchor path never enters it - asserted, not assumed, by `assert_anchor_parity()`.
_PREFILTER_BLOCK = (
    "    # Stability prefilter (NB29, 28-stable-selection-plan.md). Read signal `S` at T-1 for\n"
    "    # every candidate, exclude the least-stable fraction of those for which `S` is FINITE,\n"
    "    # then rank and size the survivors exactly as the incumbent does.\n"
    "    prefilter_signal = str(getattr(parameters, 'stability_prefilter_signal', '') or '')\n"
    "    if prefilter_signal:\n"
    "        prefilter_direction = str(getattr(parameters, 'stability_prefilter_direction', 'low'))\n"
    "        if prefilter_direction not in ('low', 'high'):\n"
    "            raise ValueError(f'unknown stability_prefilter_direction {prefilter_direction!r}')\n"
    "        prefilter_strict = bool(getattr(parameters, 'stability_prefilter_strict', False))\n"
    "        prefilter_count = int(getattr(parameters, 'stability_prefilter_count', 0) or 0)\n"
    "        prefilter_fraction = float(getattr(parameters, 'stability_prefilter_fraction', 0.0) or 0.0)\n"
    "        prefilter_values = {}\n"
    "        for _pair_id, _pair, _signal in candidates:\n"
    "            _raw = indicators.get_indicator_value(prefilter_signal, pair=_pair)\n"
    "            _value = float('nan') if _raw is None else float(_raw)\n"
    "            # `np.isfinite`, not `v == v`: the fail-closed rule excludes infinities too, and\n"
    "            # an infinite signal sorted to one end would be a silent selection of that end.\n"
    "            prefilter_values[_pair_id] = _value if np.isfinite(_value) else float('nan')\n"
    "        prefilter_seed = int(getattr(parameters, 'stability_prefilter_null_seed', -1))\n"
    "        if prefilter_seed >= 0:\n"
    "            # Permute the FINITE values within this date only. Every NaN stays attached to\n"
    "            # its own vault, so the null destroys the signal's ranking information and NOT\n"
    "            # which vault is unmeasured - those are different nulls and only the first is\n"
    "            # the mechanism's own information-destroying null.\n"
    "            _finite_ids = sorted(i for i in prefilter_values if np.isfinite(prefilter_values[i]))\n"
    "            _finite_vals = [prefilter_values[i] for i in _finite_ids]\n"
    "            _rng = np.random.default_rng(prefilter_seed * 1000003 + timestamp.toordinal())\n"
    "            prefilter_values = dict(prefilter_values)\n"
    "            prefilter_values.update(zip(_finite_ids, _rng.permutation(_finite_vals)))\n"
    "        _measured = [i for i in candidates if np.isfinite(prefilter_values[i[0]])]\n"
    "        _unmeasured = [i for i in candidates if not np.isfinite(prefilter_values[i[0]])]\n"
    "        if prefilter_count > 0:\n"
    "            _n_excluded = min(prefilter_count, len(_measured))\n"
    "        else:\n"
    "            _n_excluded = int(math.floor(prefilter_fraction * len(_measured)))\n"
    "        # 'low' means a small value is the least-stable end, so ascending puts it first.\n"
    "        _sign = 1.0 if prefilter_direction == 'low' else -1.0\n"
    "        _by_stability = sorted(_measured, key=lambda item: (_sign * prefilter_values[item[0]], item[0]))\n"
    "        _excluded_ids = {item[0] for item in _by_stability[:_n_excluded]}\n"
    "        if prefilter_strict:\n"
    "            _excluded_ids |= {item[0] for item in _unmeasured}\n"
    "        _address_of = {item[0]: str(item[1].pool_address).lower() for item in candidates}\n"
    "        PREFILTER_LOG[timestamp] = {\n"
    "            'signal': prefilter_signal,\n"
    "            'direction': prefilter_direction,\n"
    "            'strict': prefilter_strict,\n"
    "            'seed': prefilter_seed,\n"
    "            'fraction': prefilter_fraction,\n"
    "            'count': prefilter_count,\n"
    "            'pool_size': len(candidates),\n"
    "            'measured_count': len(_measured),\n"
    "            'nan_count': len(_unmeasured),\n"
    "            'excluded_count': len(_excluded_ids),\n"
    "            'remaining_count': len(candidates) - len(_excluded_ids),\n"
    "            'excluded_share': len(_excluded_ids) / len(candidates) if candidates else float('nan'),\n"
    "            'candidate_addresses': [_address_of[item[0]] for item in candidates],\n"
    "            'candidate_ids': [item[0] for item in candidates],\n"
    "            'values': {_address_of[pid]: prefilter_values[pid] for pid in _address_of},\n"
    "            'finite': {\n"
    "                _address_of[pid]: bool(np.isfinite(prefilter_values[pid])) for pid in _address_of\n"
    "            },\n"
    "            'excluded_addresses': sorted(_address_of[pid] for pid in _excluded_ids),\n"
    "        }\n"
    "        candidates = [item for item in candidates if item[0] not in _excluded_ids]\n"
    "        if not candidates:\n"
    "            return []\n"
    "\n"
)


def _with_prefilter(replacements: dict) -> dict:
    """Return a copy of the drop-mode replacements with the prefilter spliced in before ranking.

    The anchor for the insertion is the same `ordered = sorted(...)` line the NB22 complementary
    screen already replaces, so this prepends to that replacement's VALUE rather than to the cell
    text, and the two splices compose without either module being edited.
    """
    out = {}
    spliced = 0
    for key, value in replacements.items():
        if key.lstrip().startswith("# Rank by composite (selection)"):
            value = _PREFILTER_BLOCK + value
            spliced += 1
        out[key] = value
    assert spliced == 1, f"expected exactly one ranking anchor to splice into, found {spliced}"
    return out


CELL14_REPLACEMENTS_PREFILTER = _with_prefilter(CELL14_REPLACEMENTS_DROP_MODES)
