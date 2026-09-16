"""harness_threshold.py - NB37 bookkeeping for the threshold crash filter.

Loaded after harness_rules.py, harness_rules_v2.py, harness_rules_v3.py and
harness_rules_v3_gates.py. Redefines `run_and_record()` so `CRASH_LOG` is cleared before each
run and snapshotted after it, exactly as the earlier logs are, and adds the per-run summary and
the standing-gate scorer used by NB37. Standing gates per the 2026-09-16 audit in
RESEARCH-RULES.md: 1 positive return, 2 single-vault mask (retention >= 0.70), 3 held-book
volatility below the anchor's on common post-break dates, 6 plateau within 0.25 of both
neighbours, 7 positive CAGR in every sub-period. Gates 4 and 8 with their tolerances, and
everything else, are diagnostics.
"""

#: Tolerances from the audit section of RESEARCH-RULES.md.
LUCK_TOLERANCE = 0.03
DISTINCT_TOLERANCE = 2


def run_and_record(label: str, family: str, **overrides) -> dict:
    assert label not in run_by_label, f"duplicate run label {label!r}"
    VOL_DROP_LOG.clear()
    COMPLEMENT_LOG.clear()
    SLEEVE_LOG.clear()
    PREFILTER_LOG.clear()
    CRASH_LOG.clear()
    state_, equity_, returns_ = run_variant(label, **overrides)
    panel_row = panel(label, state_, equity_, returns_, anchor_cycle_returns)
    entry = {
        "label": label, "family": family, "overrides": dict(overrides),
        "state": state_, "equity": equity_, "returns": returns_, "panel": panel_row,
        "cycle_returns": cycle_returns(equity_)[0],
        "vol_drop_log": dict(VOL_DROP_LOG), "complement_log": dict(COMPLEMENT_LOG),
        "sleeve_log": dict(SLEEVE_LOG), "prefilter_log": dict(PREFILTER_LOG),
        "crash_log": dict(CRASH_LOG),
    }
    for name in ("vol_drop_log", "complement_log", "sleeve_log", "prefilter_log", "crash_log"):
        keys = list(entry[name])
        assert len(set(keys)) == len(keys), f"{name} has duplicate decision timestamps for {label}"
    runs.append(entry)
    run_by_label[label] = entry
    return entry


def crash_stats(entry: dict) -> dict:
    """Per-run summary of the crash filter's log: how many it removed per decision, how often it
    removed a name the book was holding, and how much of the pool it could measure."""
    log = entry.get("crash_log") or {}
    if not log:
        return {"crash_decisions": 0, "crash_excluded_mean": float("nan"), "crash_excluded_min": np.nan,
                "crash_excluded_max": np.nan, "crash_excluded_held_total": 0, "crash_measured_share": float("nan")}
    excluded = np.array([r["excluded_count"] for r in log.values()], dtype=float)
    pools = np.array([r["pool_size"] for r in log.values()], dtype=float)
    measured = np.array([r["measured_count"] for r in log.values()], dtype=float)
    return {"crash_decisions": len(log), "crash_excluded_mean": float(excluded.mean()),
            "crash_excluded_min": int(excluded.min()), "crash_excluded_max": int(excluded.max()),
            "crash_excluded_held_total": int(sum(r["excluded_held"] for r in log.values())),
            "crash_measured_share": float((measured / np.maximum(pools, 1)).mean())}


def basket_difference(entry: dict, reference_label: str = "anchor") -> dict:
    """Decisions on which the held set differs from the reference's, from the position
    statistics directly. `inertness()` keys its count on `PREFILTER_LOG`, which the threshold
    filter does not write, so it reports zero here; this does not."""
    base = run_by_label[reference_label]
    mine = {t: frozenset(str(p.pool_address).lower() for p, _s in h) for t, h in _position_weights(entry["state"]).items()}
    theirs = {t: frozenset(str(p.pool_address).lower() for p, _s in h) for t, h in _position_weights(base["state"]).items()}
    common = sorted(set(mine) & set(theirs))
    changed = sum(1 for t in common if mine[t] != theirs[t])
    aligned = pd.concat([entry["cycle_returns"].rename("a"), base["cycle_returns"].rename("b")], axis=1).dropna()
    identical = bool(len(aligned) and np.allclose(aligned["a"], aligned["b"], atol=1e-12))
    return {"decisions_compared": len(common), "decisions_changed": changed,
            "share_of_decisions_changed": (changed / len(common)) if common else float("nan"), "inert": identical}


def summary_row(label: str, anchor_label: str = "anchor") -> dict:
    """Panel metrics, diversification, turnover, inertness and crash-filter stats for one run."""
    entry = run_by_label[label]
    row = entry["panel"]
    out = {"label": label, "family": entry["family"]}
    out.update({k: float(row[k]) for k in (
        "cagr", "cycle_sharpe", "cycle_vol", "ulcer", "max_dd", "abs_invested_beta", "mean_invested",
        "sparse_cagr", "dense_cagr", "late_cagr", "luck_ratio", "top5_gross_share")})
    out["final_equity"] = float(entry["equity"].iloc[-1])
    out.update(diversification_cached(entry))
    out.update(turnover_and_persistence(entry))
    out.update(basket_difference(entry, anchor_label))
    out.update(crash_stats(entry))
    return out


def standing_gates(label: str, neighbours: list, anchor_label: str = "anchor", run_lovo: bool = False) -> dict:
    """The standing gates only, plus the tolerance diagnostics. Gate 2 is scored only when
    `run_lovo` is True (a full re-simulation); otherwise it is reported as not run, which is
    NOT a failure - it is simply absent from the verdict, and the verdict says so."""
    entry = run_by_label[label]
    row = entry["panel"]
    anchor = run_by_label[anchor_label]["panel"]
    anchor_entry = run_by_label[anchor_label]
    out = {"label": label}
    out["gate_1_positive"] = bool(np.isfinite(row["cagr"]) and float(row["cagr"]) > 0)
    segments = [float(row.get(f"{r}_cagr", np.nan)) for r in ("sparse", "dense", "late")]
    out["gate_7_subperiod"] = bool(all(np.isfinite(s) and s > 0 for s in segments))
    g3 = gate_3_v3(label, anchor_label)
    out["gate_3_held_vol"] = g3["gate_3_volatility"]
    out["held_vol_post"] = g3["held_vol_post"]
    out["anchor_held_vol_post"] = g3["anchor_held_vol_post"]
    out["gate_3_dates"] = g3["gate_3_dates"]
    plateau = plateau_gate(label, neighbours) if neighbours else {"passes": None, "detail": None}
    out["gate_6_plateau"] = plateau["passes"]
    out["plateau_neighbours"] = ", ".join(neighbours)
    measures = diversification_cached(entry)
    anchor_measures = diversification_cached(anchor_entry)
    out["diag_4_luck_within_tolerance"] = bool(
        np.isfinite(row["luck_ratio"]) and float(row["luck_ratio"]) >= float(anchor["luck_ratio"]) - LUCK_TOLERANCE
        and float(row["top5_gross_share"]) <= float(anchor["top5_gross_share"]) + LUCK_TOLERANCE)
    # The holdings floor (5.95) is a statement about a six-name design and is not applied to
    # books built with a different N; the distinct-vault tolerance is reported for every run.
    out["diag_8_distinct_within_tolerance"] = bool(
        measures["distinct_vaults"] >= anchor_measures["distinct_vaults"] - DISTINCT_TOLERANCE)
    out["mean_holdings"] = measures["mean_holdings"]
    if run_lovo:
        lovo = lovo_gate(label, verbose=False)
        out["gate_2_mask"] = lovo["passes"]
        out["mask_retention"] = lovo["retention"]
        out["masked"] = lovo["masked"]
    else:
        out["gate_2_mask"] = None
        out["mask_retention"] = float("nan")
        out["masked"] = "not run"
    scored = {k: v for k, v in out.items() if k.startswith("gate_") and v is not None}
    failed = [k for k, v in scored.items() if not v]
    out["failed_standing_gates"] = ", ".join(failed)
    out["standing_gates_scored"] = ", ".join(scored)
    sharpe_gap = float(row["cycle_sharpe"]) - float(anchor["cycle_sharpe"])
    out["sharpe_gap_to_anchor"] = sharpe_gap
    if failed:
        out["verdict"] = "REJECT"
    elif out["gate_2_mask"] is None:
        out["verdict"] = "PASSES SCORED GATES (mask not run)"
    elif abs(sharpe_gap) <= INDIFFERENCE_BAND:
        out["verdict"] = "NOT CONFIRMED (inside indifference band)"
    else:
        out["verdict"] = "PASSES STANDING GATES"
    return out


print(f"harness_threshold.py: CRASH_LOG lifecycle, summary_row(), standing_gates() with luck tolerance "
      f"{LUCK_TOLERANCE} and distinct-vault tolerance {DISTINCT_TOLERANCE}.")
