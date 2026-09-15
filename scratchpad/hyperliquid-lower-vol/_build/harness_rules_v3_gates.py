"""harness_rules_v3_gates.py - the nine gates under plan 34's amendments A3-A6.

Loaded after harness_rules.py, harness_rules_v2.py and harness_rules_v3.py. Nothing in those is
edited; the amended gates are new functions with a `_v3` suffix and `gate_row_v3()` composes
them. What changes against `gate_row()`:

- A3. Gate 8's holdings floor is the absolute `HOLDINGS_FLOOR` (5.95) rather than "at least the
  anchor's mean"; the other four measures are unchanged.
- A4. Gate 3 is scored on its VOLATILITY leg only - capital-weighted own realised volatility of
  the held book, lower than the anchor's - on decisions from `POST_BREAK_START`, on the dates
  COMMON to candidate and anchor, and it is unevaluable (which fails) below
  `GATE_3_MIN_DATES` such dates. Both concentration indicators are reported as diagnostics with
  their coverage, and the volatility leg is also reported on the dates whose whole 90-row
  lookback is post-break.
- A5. Gate 9 needs at least `NULL_MIN_DISTINCT_V3` (19) distinct cycle-return series and the
  null runs' turnover and basket persistence are reported beside the centre's.
- A6. The fee differential: the independent redemption-fee recomputation's net signed
  discrepancy, candidate minus anchor, as a share of the candidate-minus-anchor final-equity
  difference. A SHORTLIST needs |share| < `FEE_DIFFERENTIAL_MAX`; otherwise the verdict is
  DIAGNOSTIC even with all nine gates passed.
"""

#: A3: mean holdings must be at least this. A five-name book on no more than one decision in
#: twenty, against a six-name design.
HOLDINGS_FLOOR = 5.95

#: A4: fewest common post-break dates before gate 3's volatility leg is evaluable.
GATE_3_MIN_DATES = 40

#: A5: fewest distinct null draws; beating all of them is an add-one permutation p of 1/20.
NULL_MIN_DISTINCT_V3 = 19

#: A6: the fee differential may be at most this share of the equity difference it sits inside.
FEE_DIFFERENTIAL_MAX = 0.25

#: Calendar rows of the volatility indicator and of the concentration indicators, for the
#: "whole lookback is post-break" coverage diagnostics.
VOL_LOOKBACK_ROWS = 90
CONCENTRATION_LOOKBACK_ROWS = 180


def held_indicator_per_date(entry: dict, indicator: str, inverse: bool = False) -> pd.Series:
    """Capital-weighted T-1 indicator value of the held book, one value per decision date.

    Same construction as `held_book_character()`: a holding with a NaN value is dropped from
    that date's mean, and a date that drops more than `HELD_BOOK_MAX_DROPPED_WEIGHT` of its
    weight is omitted. `inverse=True` reads `1 / value` (for `inverse_vol` -> volatility).
    """
    weights = _position_weights(entry["state"])
    out = {}
    for timestamp in sorted(weights):
        holdings = weights[timestamp]
        total = sum(share for _p, share in holdings)
        if total <= 0:
            continue
        accumulated, covered = 0.0, 0.0
        for pair, share in holdings:
            value = value_at_prior(indicator_series(indicator, pair), timestamp)
            if inverse:
                value = (1.0 / value) if (np.isfinite(value) and value > 0) else float("nan")
            if np.isfinite(value):
                accumulated += share * value
                covered += share
        if 1.0 - covered / total <= HELD_BOOK_MAX_DROPPED_WEIGHT and covered > 0:
            out[pd.Timestamp(timestamp)] = accumulated / covered
    return pd.Series(out, dtype=float).sort_index()


_HELD_SERIES_CACHE: dict = {}


def held_series_cached(label: str, indicator: str, inverse: bool = False) -> pd.Series:
    key = (label, indicator, inverse)
    if key not in _HELD_SERIES_CACHE:
        _HELD_SERIES_CACHE[key] = held_indicator_per_date(run_by_label[label], indicator, inverse)
    return _HELD_SERIES_CACHE[key]


def gate_3_v3(label: str, anchor_label: str = "anchor") -> dict:
    """Amendment A4. Volatility leg on common post-break dates; concentration as diagnostic."""
    own = held_series_cached(label, "inverse_vol", inverse=True)
    ref = held_series_cached(anchor_label, "inverse_vol", inverse=True)
    common = own.index.intersection(ref.index)
    post = common[common >= POST_BREAK_START]
    full_lookback = common[common >= POST_BREAK_START + pd.Timedelta(days=VOL_LOOKBACK_ROWS)]
    out = {
        "held_vol_post": float(own[post].mean()) if len(post) else float("nan"),
        "anchor_held_vol_post": float(ref[post].mean()) if len(post) else float("nan"),
        "gate_3_dates": int(len(post)),
        "gate_3_evaluable": bool(len(post) >= GATE_3_MIN_DATES),
        "held_vol_full_lookback": float(own[full_lookback].mean()) if len(full_lookback) else float("nan"),
        "anchor_held_vol_full_lookback": float(ref[full_lookback].mean()) if len(full_lookback) else float("nan"),
        "full_lookback_dates": int(len(full_lookback)),
        "held_vol_all_dates": float(own[common].mean()) if len(common) else float("nan"),
        "anchor_held_vol_all_dates": float(ref[common].mean()) if len(common) else float("nan"),
        "all_common_dates": int(len(common)),
    }
    out["gate_3_volatility"] = bool(
        out["gate_3_evaluable"] and np.isfinite(out["held_vol_post"]) and np.isfinite(out["anchor_held_vol_post"])
        and out["held_vol_post"] < out["anchor_held_vol_post"])
    out["gate_3_full_lookback_lower"] = bool(
        len(full_lookback) and out["held_vol_full_lookback"] < out["anchor_held_vol_full_lookback"])
    for name, indicator in (("conc", "residual_event_concentration"), ("conc_pos", "residual_event_concentration_positive")):
        o = held_series_cached(label, indicator)
        r = held_series_cached(anchor_label, indicator)
        c = o.index.intersection(r.index)
        c_post = c[c >= POST_BREAK_START]
        c_full = c[c >= POST_BREAK_START + pd.Timedelta(days=CONCENTRATION_LOOKBACK_ROWS)]
        out[f"held_{name}_post"] = float(o[c_post].mean()) if len(c_post) else float("nan")
        out[f"anchor_held_{name}_post"] = float(r[c_post].mean()) if len(c_post) else float("nan")
        out[f"{name}_post_dates"] = int(len(c_post))
        out[f"{name}_full_lookback_dates"] = int(len(c_full))
        out[f"{name}_lower_post"] = bool(len(c_post) and o[c_post].mean() < r[c_post].mean())
    return out


def gate_8_v3(entry: dict, anchor_entry: dict) -> dict:
    """Amendment A3. `mean_holdings >= HOLDINGS_FLOOR`; the other four measures against the anchor."""
    measures = diversification_cached(entry)
    anchor_measures = diversification_cached(anchor_entry)
    failures = []
    for name, larger_is_worse in DIVERSIFICATION_MEASURES.items():
        value, reference = measures[name], anchor_measures[name]
        if not np.isfinite(value) or not np.isfinite(reference):
            failures.append(f"{name} not finite")
        elif name == "mean_holdings":
            if value < HOLDINGS_FLOOR:
                failures.append(f"mean_holdings {value:.4f} < floor {HOLDINGS_FLOOR}")
        elif larger_is_worse and value > reference:
            failures.append(name)
        elif not larger_is_worse and value < reference:
            failures.append(name)
    out = dict(measures)
    out["gate_8_diversification"] = not failures
    out["diversification_failures"] = ", ".join(failures)
    out["mean_holdings_vs_anchor"] = float(measures["mean_holdings"] - anchor_measures["mean_holdings"])
    return out


def turnover_and_persistence(entry: dict) -> dict:
    """How much the book changed: consecutive-date Jaccard of held names (persistence), the mean
    share of names replaced per decision (turnover), and the trade count."""
    weights = _position_weights(entry["state"])
    dates = sorted(weights)
    held = [frozenset(str(pair.pool_address).lower() for pair, _s in weights[d]) for d in dates]
    jaccards, replaced = [], []
    for a, b in zip(held[:-1], held[1:]):
        union = a | b
        if not union:
            continue
        jaccards.append(len(a & b) / len(union))
        replaced.append(len(a ^ b) / (len(a) + len(b)))
    trades = len(list(entry["state"].portfolio.get_all_trades()))
    return {"basket_persistence": float(np.mean(jaccards)) if jaccards else float("nan"),
            "turnover_per_decision": float(np.mean(replaced)) if replaced else float("nan"),
            "trades": int(trades), "decision_dates": len(dates)}


def null_effectiveness_v3(centre: str, null_labels: list) -> dict:
    """Amendment A5. As `null_effectiveness()` with the 19-draw minimum, plus the turnover and
    persistence of the null runs beside the centre's so the null's destruction of temporal
    persistence is visible, not assumed."""
    base = null_effectiveness(centre, null_labels)
    centre_tp = turnover_and_persistence(run_by_label[centre])
    null_tp = pd.DataFrame([turnover_and_persistence(run_by_label[l]) for l in null_labels]) if null_labels else pd.DataFrame()
    out = dict(base)
    out["passes"] = bool(
        base["distinct_cycle_return_series"] >= NULL_MIN_DISTINCT_V3 and null_labels
        and base["centre_sharpe"] > base["null_best"])
    out["min_distinct_required"] = NULL_MIN_DISTINCT_V3
    out["add_one_p_if_beats_all"] = 1.0 / (len(null_labels) + 1.0) if null_labels else float("nan")
    out["centre_persistence"] = centre_tp["basket_persistence"]
    out["centre_turnover"] = centre_tp["turnover_per_decision"]
    out["centre_trades"] = centre_tp["trades"]
    out["null_persistence_mean"] = float(null_tp["basket_persistence"].mean()) if len(null_tp) else float("nan")
    out["null_turnover_mean"] = float(null_tp["turnover_per_decision"].mean()) if len(null_tp) else float("nan")
    out["null_trades_mean"] = float(null_tp["trades"].mean()) if len(null_tp) else float("nan")
    out["null_sharpe_rank_of_centre"] = (int((np.array([float(run_by_label[l]["panel"]["cycle_sharpe"]) for l in null_labels])
                                              >= base["centre_sharpe"]).sum()) + 1) if null_labels else None
    return out


def independent_fee_audit_v3(state_) -> dict:
    """The NB29/NB31 independent recomputation, unchanged: stored redemption fee against
    `10% x max(gross - released cost basis, 0) + 10 bps`, gross at the trade's planned mid."""
    perf_rate = float(Parameters.vault_performance_fee)
    cap_rate = float(Parameters.vault_redemption_capital_fee)
    worst_rate, worst_proceeds, n, over_1bp, sum_abs, signed = 0.0, 0.0, 0, 0, 0.0, 0.0
    for position in state_.portfolio.get_all_positions():
        if not position.pair.is_vault():
            continue
        quantity, cost_basis = 0.0, 0.0
        for trade in sorted(position.get_successful_trades(), key=lambda t: t.executed_at):
            q = abs(float(trade.get_position_quantity()))
            if trade.is_buy():
                quantity += q
                cost_basis += q * float(trade.executed_price)
                continue
            if not trade.is_sell() or quantity <= 0:
                continue
            gross = q * float(trade.planned_mid_price)
            released = cost_basis * q / quantity
            expected_rate = cap_rate + perf_rate * max(gross - released, 0.0) / gross if gross > 0 else cap_rate
            stored_rate = float(trade.other_data["backtest_vault_redemption_fee"])
            rate_diff = stored_rate - expected_rate
            proceeds_diff = q * float(trade.executed_price) - gross * (1.0 - expected_rate)
            worst_rate = max(worst_rate, abs(rate_diff))
            worst_proceeds = max(worst_proceeds, abs(proceeds_diff))
            over_1bp += int(abs(rate_diff) > 1e-4)
            sum_abs += abs(proceeds_diff)
            signed += proceeds_diff
            n += 1
            cost_basis -= released
            quantity -= q
    return {"redemptions": n, "over_1bp": over_1bp, "max_abs_rate_diff": worst_rate,
            "max_abs_proceeds_diff_usd": worst_proceeds, "sum_abs_proceeds_diff_usd": sum_abs,
            "net_signed_proceeds_diff_usd": signed}


_FEE_CACHE: dict = {}


def fee_audit_cached(label: str) -> dict:
    if label not in _FEE_CACHE:
        _FEE_CACHE[label] = independent_fee_audit_v3(run_by_label[label]["state"])
    return _FEE_CACHE[label]


def fee_differential(label: str, anchor_label: str = "anchor") -> dict:
    """Amendment A6. Candidate-minus-anchor net signed fee discrepancy against the equity gap."""
    own, ref = fee_audit_cached(label), fee_audit_cached(anchor_label)
    own_equity = float(run_by_label[label]["equity"].iloc[-1])
    ref_equity = float(run_by_label[anchor_label]["equity"].iloc[-1])
    differential = own["net_signed_proceeds_diff_usd"] - ref["net_signed_proceeds_diff_usd"]
    equity_gap = own_equity - ref_equity
    share = abs(differential) / abs(equity_gap) if equity_gap != 0 else float("inf")
    return {
        "fee_net_signed_usd": own["net_signed_proceeds_diff_usd"],
        "anchor_fee_net_signed_usd": ref["net_signed_proceeds_diff_usd"],
        "fee_differential_usd": differential,
        "final_equity": own_equity, "anchor_final_equity": ref_equity, "equity_gap_usd": equity_gap,
        "fee_differential_share_of_gap": share,
        "fee_redemptions": own["redemptions"], "fee_over_1bp": own["over_1bp"],
        "fee_differential_ok": bool(np.isfinite(share) and share < FEE_DIFFERENTIAL_MAX),
    }


def gate_row_v3(
    label: str, gate_5_by_signal: dict, signal: str, neighbours: list,
    null_labels=None, anchor_label: str = "anchor",
) -> dict:
    """All nine gates plus the fee differential for one candidate, cheapest first.

    `null_labels` may be a list of already-run labels, or a callable that RUNS the null and
    returns the labels; it is called only if every cheaper gate passed, so the null is never run
    for a candidate that has already failed. Every Boolean is present; an unexecuted gate is
    False. Verdict: SHORTLIST needs all nine and the fee condition; all nine without the fee
    condition is DIAGNOSTIC; anything else REJECT.
    """
    entry = run_by_label[label]
    row = entry["panel"]
    anchor = run_by_label[anchor_label]["panel"]
    anchor_entry = run_by_label[anchor_label]
    out = {"label": label, "signal": signal}
    out.update({k: float(row[k]) for k in
                ("cycle_sharpe", "cagr", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta",
                 "mean_invested", "sparse_cagr", "dense_cagr", "late_cagr", "luck_ratio", "top5_gross_share")})

    out["gate_1_positive"] = bool(np.isfinite(row["cagr"]) and float(row["cagr"]) > 0)
    segments = [float(row.get(f"{r}_cagr", np.nan)) for r in ("sparse", "dense", "late")]
    out["gate_7_subperiod"] = bool(all(np.isfinite(s) and s > 0 for s in segments))
    out["gate_4_luck"] = bool(
        np.isfinite(row["luck_ratio"]) and np.isfinite(row["top5_gross_share"])
        and float(row["luck_ratio"]) >= float(anchor["luck_ratio"])
        and float(row["top5_gross_share"]) <= float(anchor["top5_gross_share"]))
    out["gate_5_screen"] = bool(gate_5_by_signal.get(signal, False))

    g3 = gate_3_v3(label, anchor_label)
    out.update(g3)
    out["gate_3_held_book"] = g3["gate_3_volatility"]

    g8 = gate_8_v3(entry, anchor_entry)
    out.update(g8)

    plateau = plateau_gate(label, neighbours)
    out["gate_6_plateau"] = plateau["passes"]
    out["plateau_detail"] = plateau["detail"]

    cheap = ("gate_1_positive", "gate_7_subperiod", "gate_4_luck", "gate_5_screen",
             "gate_3_held_book", "gate_8_diversification", "gate_6_plateau")
    if all(out[g] for g in cheap):
        lovo = lovo_gate(label)
        out["gate_2_lovo"] = lovo["passes"]
        out["lovo_retention"] = lovo["retention"]
        out["lovo_masked"] = lovo["masked"]
        labels = null_labels() if callable(null_labels) else (null_labels or [])
        if labels:
            null = null_effectiveness_v3(label, labels)
            out["gate_9_null"] = null["passes"]
            for k in ("null_best", "null_median", "distinct_cycle_return_series", "null_sharpe_rank_of_centre",
                      "centre_persistence", "null_persistence_mean", "centre_turnover", "null_turnover_mean"):
                out[k] = null[k]
            out["null_draws"] = len(labels)
        else:
            out["gate_9_null"] = False
            out["null_draws"] = 0
            out["distinct_cycle_return_series"] = 0
    else:
        out["gate_2_lovo"] = False
        out["lovo_retention"] = float("nan")
        out["lovo_masked"] = "not evaluated - a cheaper gate failed"
        out["gate_9_null"] = False
        out["null_draws"] = 0
        out["distinct_cycle_return_series"] = 0

    fee = fee_differential(label, anchor_label)
    out.update(fee)

    named = {
        "gate_1": "gate_1_positive", "gate_2": "gate_2_lovo", "gate_3": "gate_3_held_book",
        "gate_4": "gate_4_luck", "gate_5": "gate_5_screen", "gate_6": "gate_6_plateau",
        "gate_7": "gate_7_subperiod", "gate_8": "gate_8_diversification", "gate_9": "gate_9_null",
    }
    failed = [g for g in named if not out[named[g]]]
    if not out["gate_3_evaluable"]:
        failed = [f"gate_3 (unevaluable: {out['gate_3_dates']} common post-break dates < {GATE_3_MIN_DATES})"
                  if g == "gate_3" else g for g in failed]
    if out["diversification_failures"]:
        failed = [f"gate_8 ({out['diversification_failures']})" if g == "gate_8" else g for g in failed]
    out["failed_gates"] = ", ".join(failed)
    if failed:
        out["verdict"] = "REJECT"
    elif not out["fee_differential_ok"]:
        out["verdict"] = "DIAGNOSTIC - all nine gates passed; fee differential exceeds the bound"
    else:
        out["verdict"] = "SHORTLIST"
    return out


print(f"harness_rules_v3_gates.py: holdings floor {HOLDINGS_FLOOR}; gate 3 on the volatility leg from "
      f"{POST_BREAK_START.date()} (min {GATE_3_MIN_DATES} dates); null min distinct {NULL_MIN_DISTINCT_V3}; "
      f"fee differential bound {FEE_DIFFERENTIAL_MAX}.")
