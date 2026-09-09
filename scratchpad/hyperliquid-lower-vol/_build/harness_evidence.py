#: Evidence-weighted track additions to the shared harness (14-evidence-weighted-plan.md).
#: Draft 2. Revised after 14-evidence-weighted-plan-codex-review.md. Only *adds* names; nothing
#: in harness.py (already loaded by the time this cell runs) is redefined.
#:
#: The seven pre-registered constraints of adoption rule v2. Do not edit the numbers here; if one
#: is badly placed, say so in the notebook's Robustness section.
CAGR_FLOOR_V2 = 0.20
#: Review 3(c): strictly beating the anchor's Sharpe is both too strict an adoption bar (nothing
#: in NB12 cleared it robustly) and too weak a statistical claim (a marginal win can be noise).
#: Replaced with non-inferiority within a pre-registered tolerance, paired with a MATERIAL ulcer
#: improvement below - the operator's actual trade-off (consistency for CAGR) is expressed as a
#: real drawdown reduction, not as a fragile Sharpe race.
SHARPE_NONINFERIORITY_TOL = 0.10
#: Relative ulcer-index improvement required, not merely "any" improvement (review: Draft 1's bare
#: `<` let a 0.01 percentage-point difference count as a pass).
ULCER_IMPROVEMENT_FRAC = 0.15
INVESTED_FLOOR_V2 = 0.90
PLACEBO_MARGIN = 0.10
PLACEBO_DROPS = (0, 10, 20, 30, 40, 50, 60)


def build_placebo_frontier(anchor_cycle_returns_) -> tuple:
    """Run the vol-matched placebo at every pre-registered N.

    Returns `(frontier_df, cycle_returns_by_label)` - the summary panel AND each run's own cycle
    returns, the latter needed by `bootstrap_sharpe_diff_vs_control()` below (review: Draft 1
    referenced a "paired bootstrap CI" without retaining what it would need to compute one).

    Re-run in every notebook rather than loaded from a file so it is always on the same data
    snapshot as the variants it is compared against (vault data is downloaded fresh each run).
    About two minutes.
    """
    rows = []
    cycle_returns_by_label = {}
    for n in PLACEBO_DROPS:
        if n == 0:
            rows.append(anchor_panel.copy())
            cycle_returns_by_label["anchor"] = anchor_cycle_returns_
            continue
        label = f"vol_matched_drop_{n}"
        s, e, r = run_variant(label, vol_matched_drop_count=n)
        rows.append(panel(label, s, e, r, anchor_cycle_returns_))
        cycle_returns_by_label[label], _ = cycle_returns(e)
    frontier = pd.DataFrame(rows).set_index("label")
    frontier.loc["anchor", "drop_n"] = 0
    for n in PLACEBO_DROPS:
        if n:
            frontier.loc[f"vol_matched_drop_{n}", "drop_n"] = n
    return frontier.sort_values("cycle_vol"), cycle_returns_by_label


def _pareto_envelope(frontier: pd.DataFrame) -> pd.DataFrame:
    """Non-dominated subset of the frontier: sorted by volatility ascending, Sharpe strictly rising.

    Review: the raw seven placebo points are not necessarily a frontier - a lower-vol point can
    have a lower Sharpe than a higher-vol point (dominated), and linearly interpolating through a
    dominated point sets too weak a bar. This keeps only points where no quieter-or-equal point
    already achieved an equal-or-higher Sharpe, so the constraint always compares a candidate to
    the BEST Sharpe pure volatility avoidance achieved at or below the candidate's own volatility.
    """
    ordered = frontier.sort_values("cycle_vol")
    keep_labels, best = [], -np.inf
    for label, row in ordered.iterrows():
        if row["cycle_sharpe"] > best:
            keep_labels.append(label)
            best = row["cycle_sharpe"]
    return ordered.loc[keep_labels]


def placebo_sharpe_at(frontier: pd.DataFrame, vol: float) -> float:
    """Envelope Sharpe linearly interpolated at `vol`.

    Returns NaN outside the envelope's volatility range. Review: Draft 1 treated NaN here as an
    automatic PASS of constraint 7 (`ref != ref or ...`); `passes_constraints_v2` below now treats
    it as a FAIL - a candidate whose volatility the placebo design never covered is not evaluable
    against it and must not default to passing.
    """
    envelope = _pareto_envelope(frontier)
    xs, ys = envelope["cycle_vol"].to_numpy(), envelope["cycle_sharpe"].to_numpy()
    if len(xs) == 0 or vol < xs.min() or vol > xs.max():
        return float("nan")
    return float(np.interp(vol, xs, ys))


def nearest_placebo_label(frontier: pd.DataFrame, vol: float) -> str:
    """Label of the placebo run closest in volatility to `vol` (for the bootstrap below)."""
    return (frontier["cycle_vol"] - vol).abs().idxmin()


def bootstrap_sharpe_diff_vs_control(
    candidate_returns: pd.Series,
    control_returns: pd.Series,
    periods_per_year: float,
    block: int = 10,
    draws: int = 1000,
    seed: int = 0,
) -> tuple:
    """95% CI on (candidate cycle Sharpe - control cycle Sharpe), block-resampled in matched pairs.

    Both series are aligned by date and resampled together in matching contiguous blocks, so every
    draw compares the two strategies on the same market days rather than on independently
    resampled ones. Review: "paired bootstrap CI" was named in Draft 1's prose but never
    implemented for a Sharpe difference - `panel()`'s existing bootstrap is a CI on a mean paired
    RETURN difference, not this.
    """
    joined = pd.concat([candidate_returns.rename("c"), control_returns.rename("x")], axis=1).dropna()
    n = len(joined)
    if n < block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        sample = joined.iloc[idx]
        c_std, x_std = sample["c"].std(), sample["x"].std()
        if c_std <= 0 or x_std <= 0:
            continue
        c_sharpe = sample["c"].mean() / c_std * np.sqrt(periods_per_year)
        x_sharpe = sample["x"].mean() / x_std * np.sqrt(periods_per_year)
        diffs.append(c_sharpe - x_sharpe)
    if not diffs:
        return float("nan"), float("nan")
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def passes_constraints_v2(row: pd.Series, anchor: pd.Series, frontier: pd.DataFrame | None = None) -> bool:
    """Adoption rule v2: the seven constraints in 14-evidence-weighted-plan.md (Draft 2)."""
    ok = bool(
        row["cagr"] >= CAGR_FLOOR_V2
        and row["cycle_sharpe"] >= anchor["cycle_sharpe"] - SHARPE_NONINFERIORITY_TOL
        and row["cycle_vol"] <= anchor["cycle_vol"]
        and row["ulcer"] <= anchor["ulcer"] * (1.0 - ULCER_IMPROVEMENT_FRAC)
        and row["abs_invested_beta"] < anchor["abs_invested_beta"]
        and row["mean_invested"] >= INVESTED_FLOOR_V2
    )
    if ok and frontier is not None:
        ref = placebo_sharpe_at(frontier, float(row["cycle_vol"]))
        ok = ref == ref and row["cycle_sharpe"] >= ref + PLACEBO_MARGIN   # NaN ref -> FAIL, not pass
    return ok


def failing_constraints_v2(row: pd.Series, anchor: pd.Series, frontier: pd.DataFrame | None = None) -> str:
    """Names of the failed constraints, for the verdict table. Empty string if all pass."""
    failed = []
    if row["cagr"] < CAGR_FLOOR_V2: failed.append("CAGR < 20%")
    if row["cycle_sharpe"] < anchor["cycle_sharpe"] - SHARPE_NONINFERIORITY_TOL: failed.append("Sharpe non-inferiority")
    if row["cycle_vol"] > anchor["cycle_vol"]: failed.append("volatility")
    if row["ulcer"] > anchor["ulcer"] * (1.0 - ULCER_IMPROVEMENT_FRAC): failed.append("ulcer (not material)")
    if not row["abs_invested_beta"] < anchor["abs_invested_beta"]: failed.append("beta")
    if row["mean_invested"] < INVESTED_FLOOR_V2: failed.append("invested < 90%")
    if frontier is not None:
        ref = placebo_sharpe_at(frontier, float(row["cycle_vol"]))
        if not (ref == ref and row["cycle_sharpe"] >= ref + PLACEBO_MARGIN):
            failed.append("placebo (not evaluable)" if ref != ref else "placebo")
    return ", ".join(failed)


def hidden_cohort_reach(state_) -> pd.Series:
    """Goal 1 diagnostic: how much of the book went to vaults the incumbent could never score.

    Vault inception is the first raw poll in the Hyperliquid archive, as NB13 §2 computed it, read
    from its cache file. Reports position-count share (Draft 1's only measure), capital-weighted
    share (entry USD value, review finding: a count share treats a $5,000 position the same as a
    $50,000 one) and days-held-weighted share. Always returns the SAME schema, including when
    there are no positions or the life cache is missing entirely (review: Draft 1 returned a
    single-key Series with zero positions, which breaks any caller expecting the full schema), and
    reports how many held positions could not be matched to the cache rather than silently
    dropping them.
    """
    from pathlib import Path

    schema = ["positions", "unmatched_positions", "young_positions", "young_share",
              "young_capital_share", "young_days_share", "young_pnl_usd",
              "post_april_vaults_held", "youngest_entry_days"]
    life_path = Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet")
    if not life_path.exists():
        return pd.Series({k: float("nan") for k in schema})
    life = pd.read_parquet(life_path)

    rows, unmatched = [], 0
    for position in state_.portfolio.get_all_positions():
        if position.is_credit_supply():
            continue
        address = str(position.pair.pool_address).lower()
        if address not in life.index:
            unmatched += 1
            continue
        buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
        entry_capital = sum(t.get_value() for t in buys) if buys else 0.0
        age = (pd.Timestamp(position.opened_at) - life.loc[address, "inception"]).days
        days_held = ((position.closed_at or Parameters.backtest_end) - position.opened_at).days
        rows.append({
            "address": address, "age_at_entry": age, "entry_capital_usd": float(entry_capital),
            "days_held": max(days_held, 1),
            "post_april": bool(life.loc[address, "inception"] >= pd.Timestamp("2026-04-01")),
            "pnl_usd": float(position.get_total_profit_usd() or 0.0),
        })
    held = pd.DataFrame(rows)
    if not len(held):
        out = {k: 0.0 for k in schema}
        out["unmatched_positions"] = float(unmatched)
        out["young_share"] = out["young_capital_share"] = out["young_days_share"] = float("nan")
        out["youngest_entry_days"] = float("nan")
        return pd.Series(out)

    young = held[held["age_at_entry"] < Parameters.cagr_lookback_days]
    return pd.Series({
        "positions": float(len(held)),
        "unmatched_positions": float(unmatched),
        "young_positions": float(len(young)),
        "young_share": len(young) / len(held),
        "young_capital_share": (
            young["entry_capital_usd"].sum() / held["entry_capital_usd"].sum()
            if held["entry_capital_usd"].sum() > 0 else float("nan")
        ),
        "young_days_share": (
            young["days_held"].sum() / held["days_held"].sum()
            if held["days_held"].sum() > 0 else float("nan")
        ),
        "young_pnl_usd": float(young["pnl_usd"].sum()),
        "post_april_vaults_held": float(held.loc[held["post_april"], "address"].nunique()),
        "youngest_entry_days": float(held["age_at_entry"].min()),
    })


def late_period_ok(row: pd.Series, anchor: pd.Series) -> bool:
    return bool(row["late_cagr"] > 0 and row["late_ulcer"] < anchor["late_ulcer"])


def verdict_table(rows: list, anchor: pd.Series, frontier: pd.DataFrame) -> pd.DataFrame:
    """One row per run: the panel plus rule-v2 verdict columns and the CAGR sacrifice against the
    anchor (review 3c: the operator's trade-off should be reported explicitly on every row, not
    only implied by the CAGR floor). Sorted by cycle Sharpe.
    """
    df = pd.DataFrame(rows).set_index("label")
    df["placebo_ref"] = [placebo_sharpe_at(frontier, float(v)) for v in df["cycle_vol"]]
    df["cagr_sacrifice_pp"] = (anchor["cagr"] - df["cagr"]) * 100.0
    df["passes_v2"] = [passes_constraints_v2(r, anchor, frontier) for _, r in df.iterrows()]
    df["failed"] = [failing_constraints_v2(r, anchor, frontier) for _, r in df.iterrows()]
    df["late_ok"] = [late_period_ok(r, anchor) for _, r in df.iterrows()]
    return df.sort_values("cycle_sharpe", ascending=False)


def family_wise_reality_check(
    candidate_cycle_returns: dict,
    anchor_cycle_returns_,
    periods_per_year: float,
    block: int = 10,
    draws: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """White's reality-check-style max-statistic test over the full pre-registered candidate family.

    Review 3(f): plateau, leave-one-vault-out, the placebo constraint and the late period are
    useful robustness checks but do not correct for testing an adaptive family of ~25 backtests.
    This block-bootstraps the ANCHOR's own cycle returns `draws` times, and on each draw computes,
    for every candidate in `candidate_cycle_returns`, the Sharpe of (bootstrap anchor sample
    re-labelled as if it were that candidate's own return series) minus the anchor's actual Sharpe
    - i.e. the null distribution of "how much can noise alone improve on the anchor's Sharpe for
    the best of N candidates", matching the number of candidates actually tried. The candidate
    family's own MAXIMUM observed Sharpe improvement is then compared to this null's distribution
    of maxima: a family-wise p-value, not a per-candidate one.

    `candidate_cycle_returns` must be the COMPLETE pre-registered family for this to be valid -
    passing only the winners defeats the point.
    """
    anchor_r = anchor_cycle_returns_.dropna().to_numpy()
    n = len(anchor_r)
    anchor_sharpe = float(anchor_cycle_returns_.mean() / anchor_cycle_returns_.std() * np.sqrt(periods_per_year))
    observed = {
        label: float(r.mean() / r.std() * np.sqrt(periods_per_year)) - anchor_sharpe
        for label, r in candidate_cycle_returns.items() if r.std() > 0
    }
    observed_max = max(observed.values()) if observed else float("nan")

    rng = np.random.default_rng(seed)
    null_maxima = []
    for _ in range(draws):
        draw_max = -np.inf
        for _label in observed:
            starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
            idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
            sample = anchor_r[idx]
            if sample.std() <= 0:
                continue
            draw_max = max(draw_max, float(sample.mean() / sample.std() * np.sqrt(periods_per_year)) - anchor_sharpe)
        null_maxima.append(draw_max)
    p_value = float(np.mean([m >= observed_max for m in null_maxima])) if observed else float("nan")

    return pd.DataFrame({
        "metric": ["Family size", "Best observed Sharpe improvement over anchor",
                   "Null 95th percentile of the best-of-family improvement", "Family-wise p-value"],
        "value": [len(observed), observed_max, float(np.percentile(null_maxima, 95)) if null_maxima else float("nan"), p_value],
    })
