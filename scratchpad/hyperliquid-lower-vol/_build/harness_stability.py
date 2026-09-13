#: Stability-leads track additions to the shared harness (20-stability-leads-plan.md, Draft 2).
#: Loaded after harness.py and harness_evidence.py; only ADDS names, redefines nothing.
#:
#: Adoption rule v3 = rule v2's constraints 1-6 unchanged, plus a redefined constraint 7. The
#: gpt-6-astra review found v2's constraint 7 interpolated linearly between realised strategies,
#: which is neither an observed control nor an executable mixture, and marked the whole near-anchor
#: volatility band "not evaluable". v3 compares against the best OBSERVED control at or below the
#: candidate's own volatility instead. Nothing is unevaluable and nothing is interpolated.
import hashlib
import subprocess
from pathlib import Path

#: Full-precision anchor metrics, from 15-backtest-placebo-frontier.ipynb cell 16. Every notebook
#: in this track asserts against THESE, not against the rounded figures in a heading.
BASELINE = {
    "cycle_sharpe": 2.159792,
    "cycle_sortino": 4.447779,
    "cycle_vol": 0.154278,
    "cagr": 0.378971,
    "ulcer": 0.017964,
    "max_dd": -0.044504,
    "abs_invested_beta": 0.045797,
    "mean_invested": 0.971969,
    "late_cagr": 0.272027,
    "late_ulcer": 0.025268,
}
#: Absolute tolerance per metric. The published figures carry six significant digits, so 1e-5 is
#: a genuine parity check rather than a rounding allowance.
BASELINE_TOLERANCE = 1e-5

#: Data snapshot files whose content decides what any of these notebooks can possibly conclude.
PROVENANCE_PATHS = [
    Path.home() / ".cache/tradingstrategy/vaults/downloads/vault-prices.parquet",
    Path.home() / ".cache/tradingstrategy/vaults/downloads/vault-metadata.json",
    Path.home() / ".tradingstrategy/binance-price.duckdb",
    Path("/tmp/hyperliquid-lower-vol-btc-daily-returns.parquet"),
]

#: Volatility-matched drop family at 5-step spacing. This is the comparator for constraint 7 in
#: every notebook of this track, and in NB21 it is also the candidate set.
FAMILY_DROPS = tuple(range(5, 61, 5))
#: Plateau centres. 5 and 60 are boundary members: they can be a neighbour but never a centre,
#: because a centre needs a neighbour on both sides.
FAMILY_CENTRES = tuple(range(10, 56, 5))

PLACEBO_MARGIN_V3 = 0.10
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 0


def _sha256(path: Path, chunk: int = 1 << 22) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def provenance() -> pd.DataFrame:
    """Content hash of every data snapshot this notebook's conclusions rest on, plus the build commit.

    Size and modification time are not enough: the review noted that a refreshed download of the
    same historical period is not independent evidence, and that a changed metadata snapshot can
    silently change universe membership through deposit-closed status and peak TVL. A content
    hash makes "the same data as the previous notebook" a checkable claim rather than an
    assumption. It does not make the snapshot point-in-time correct - that limitation stands for
    this whole track.
    """
    rows = []
    for path in PROVENANCE_PATHS:
        if not path.exists():
            rows.append({"file": str(path), "bytes": float("nan"), "sha256": "MISSING", "modified": ""})
            continue
        stat = path.stat()
        rows.append({
            "file": str(path),
            "bytes": stat.st_size,
            "sha256": _sha256(path)[:16],
            "modified": str(pd.Timestamp(stat.st_mtime, unit="s")),
        })
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
            cwd=str(Path.cwd()), timeout=20,
        ).stdout.strip()
    except Exception:
        commit = "unknown"
    rows.append({"file": "git HEAD", "bytes": float("nan"), "sha256": commit, "modified": ""})
    return pd.DataFrame(rows)


def assert_anchor_parity(panel_row: pd.Series = None) -> pd.DataFrame:
    """Fail loudly if this kernel's anchor is not the baseline every earlier notebook ran on.

    Also proves that the two `decide_trades` splices this track adds are inert on the anchor path:
    the drop-log branch only runs when `vol_matched_drop_count > 0`, and the complementary screen
    only when `complementary_pool_size > 0`. Neither is true for the anchor, so identical anchor
    metrics is the evidence that neither fired.
    """
    row = anchor_panel if panel_row is None else panel_row
    rows = []
    for metric, expected in BASELINE.items():
        actual = float(row[metric])
        rows.append({
            "metric": metric, "expected": expected, "actual": actual,
            "abs_diff": abs(actual - expected), "ok": abs(actual - expected) <= BASELINE_TOLERANCE,
        })
    frame = pd.DataFrame(rows).set_index("metric")
    assert bool(frame["ok"].all()), f"ANCHOR PARITY FAILED:\n{frame[~frame['ok']]}"
    assert not VOL_DROP_LOG, "the vol-matched drop log fired on the anchor path; the splice is not inert"
    assert not COMPLEMENT_LOG, "the complementary screen fired on the anchor path; the splice is not inert"
    print(f"Anchor parity OK against BASELINE at +/-{BASELINE_TOLERANCE:g}; both splices inert on the anchor.")
    return frame


# --------------------------------------------------------------------------------------------
# Run bookkeeping. Every run in every notebook of this track goes through `run_and_record()`, so
# `runs` / `run_by_label` is the single source for every table, chart and claim, and every run
# retains its state, equity, returns and diagnostic logs.
# --------------------------------------------------------------------------------------------

anchor_cycle_returns, PERIODS_PER_YEAR = cycle_returns(anchor_equity)

runs: list[dict] = []
run_by_label: dict[str, dict] = {}


def run_and_record(label: str, family: str, **overrides) -> dict:
    """Run one configuration, record it, and snapshot its diagnostic logs.

    :param family:
        What role this run plays - ``anchor``, ``candidate``, ``control``, ``robustness``,
        ``policy`` or ``null``. Carried into the verdict table so a control can never be read as
        an adoptable result, and so `family_wise_joint()` can be handed the complete candidate
        family rather than a hand-picked subset.
    """
    assert label not in run_by_label, f"duplicate run label {label!r}"
    VOL_DROP_LOG.clear()
    COMPLEMENT_LOG.clear()
    SLEEVE_LOG.clear()
    state_, equity_, returns_ = run_variant(label, **overrides)
    panel_row = panel(label, state_, equity_, returns_, anchor_cycle_returns)
    entry = {
        "label": label, "family": family, "overrides": dict(overrides),
        "state": state_, "equity": equity_, "returns": returns_, "panel": panel_row,
        "cycle_returns": cycle_returns(equity_)[0],
        "vol_drop_log": dict(VOL_DROP_LOG), "complement_log": dict(COMPLEMENT_LOG),
        "sleeve_log": dict(SLEEVE_LOG),
    }
    for name in ("vol_drop_log", "complement_log", "sleeve_log"):
        keys = list(entry[name])
        assert len(set(keys)) == len(keys), f"{name} has duplicate decision timestamps for {label}"
    runs.append(entry)
    run_by_label[label] = entry
    return entry


def record_anchor(label: str = "anchor") -> dict:
    """Put the already-computed anchor into `runs` without re-running it."""
    entry = {
        "label": label, "family": "anchor", "overrides": {},
        "state": anchor_state, "equity": anchor_equity, "returns": anchor_returns,
        "panel": anchor_panel, "cycle_returns": anchor_cycle_returns,
        "vol_drop_log": {}, "complement_log": {}, "sleeve_log": {},
    }
    runs.append(entry)
    run_by_label[label] = entry
    return entry


def build_family(suffix: str = "", **common_overrides) -> pd.DataFrame:
    """Run the 5-step volatility-matched drop family, the comparator for constraint 7.

    Run in the same kernel as the candidates it will be compared against, never loaded from a
    file, so the comparison is always on one data snapshot.

    A member this notebook already ran for its own reasons - NB22 runs `drop_20` and `drop_30` for
    its Part A diagnostic before it needs a comparator - is reused rather than re-run, provided
    the recorded overrides are identical. Re-running it would be wasted compute and a duplicate
    label; quietly running a DIFFERENT configuration under the family's name would be worse, so
    that case raises.
    """
    for n in FAMILY_DROPS:
        label = f"drop_{n}{suffix}"
        expected = {"vol_matched_drop_count": n, **common_overrides}
        existing = run_by_label.get(label)
        if existing is not None:
            assert existing["overrides"] == expected, (
                f"{label} already ran with {existing['overrides']}, but the family needs {expected}"
            )
            print(f"  reusing the already-recorded {label}")
            continue
        run_and_record(label, "control", **expected)
    return family_frame(suffix)


def family_frame(suffix: str = "") -> pd.DataFrame:
    """The family's panel rows, indexed by label, with the drop count as a column."""
    rows = []
    for n in FAMILY_DROPS:
        label = f"drop_{n}{suffix}"
        if label in run_by_label:
            row = run_by_label[label]["panel"].copy()
            row["drop_n"] = float(n)
            rows.append(row)
    return pd.DataFrame(rows).set_index("label")


# --------------------------------------------------------------------------------------------
# Adoption rule v3.
# --------------------------------------------------------------------------------------------

def placebo_ref_observed(family: pd.DataFrame, vol: float) -> float:
    """Highest cycle Sharpe among family members no noisier than `vol`. No interpolation.

    A candidate quieter than every family member is compared against the quietest member - the
    closest observed control - rather than being marked unevaluable, which is what v2's
    interpolation did to the entire near-anchor band. A candidate noisier than every member is
    compared against all of them, which is the correct direction of conservatism: it has to beat
    the best simple de-risking that took no more risk than it did.
    """
    if family is None or not len(family):
        return float("nan")
    at_or_below = family[family["cycle_vol"] <= vol]
    if not len(at_or_below):
        at_or_below = family.nsmallest(1, "cycle_vol")
    return float(at_or_below["cycle_sharpe"].max())


def _required_metrics(row: pd.Series) -> str:
    """Name any required metric that is not finite, so a NaN can never pass a comparison silently."""
    required = ["cagr", "cycle_sharpe", "cycle_vol", "ulcer", "abs_invested_beta", "mean_invested"]
    bad = [m for m in required if not np.isfinite(float(row.get(m, np.nan)))]
    return ", ".join(f"{m} not finite" for m in bad)


def failing_constraints_v3(
    row: pd.Series, anchor: pd.Series, family: pd.DataFrame | None = None,
    skip_placebo: bool = False,
) -> str:
    """Every failed constraint, named in full. Empty string means all of them passed.

    Never truncate what this returns. The first write-ups of NB17-NB19 under-reported failures
    because pandas elided the column at 50 characters and the text was read as complete.
    """
    non_finite = _required_metrics(row)
    if non_finite:
        return non_finite
    failed = []
    if row["cagr"] < CAGR_FLOOR_V2:
        failed.append("CAGR < 20%")
    if row["cycle_sharpe"] < anchor["cycle_sharpe"] - SHARPE_NONINFERIORITY_TOL:
        failed.append("Sharpe non-inferiority")
    if row["cycle_vol"] > anchor["cycle_vol"]:
        failed.append("volatility")
    if row["ulcer"] > anchor["ulcer"] * (1.0 - ULCER_IMPROVEMENT_FRAC):
        failed.append("ulcer (not material)")
    if not row["abs_invested_beta"] < anchor["abs_invested_beta"]:
        failed.append("beta")
    if row["mean_invested"] < INVESTED_FLOOR_V2:
        failed.append("invested < 90%")
    if not skip_placebo:
        if family is None or not len(family):
            failed.append("observed control (family missing)")
        else:
            reference = placebo_ref_observed(family, float(row["cycle_vol"]))
            if not (np.isfinite(reference) and row["cycle_sharpe"] >= reference + PLACEBO_MARGIN_V3):
                failed.append("observed control")
    return ", ".join(failed)


def passes_constraints_v3(row, anchor, family=None, skip_placebo: bool = False) -> bool:
    return failing_constraints_v3(row, anchor, family, skip_placebo) == ""


def passes_1_to_6(row: pd.Series, anchor: pd.Series) -> bool:
    """Constraints 1-6 only. Used where constraint 7 is INAPPLICABLE, not merely unevaluated.

    NB21's candidates ARE the observed-control family, so constraint 7 would compare each member
    against itself and require `S >= S + 0.10`. That is a definitional impossibility rather than a
    real bar, so NB21 reports this and `simple_rule_eligible` and never reports `passes_v3`.
    """
    return failing_constraints_v3(row, anchor, None, skip_placebo=True) == ""


def late_period_ok_v3(row: pd.Series, anchor: pd.Series) -> bool:
    late_cagr, late_ulcer = float(row.get("late_cagr", np.nan)), float(row.get("late_ulcer", np.nan))
    if not (np.isfinite(late_cagr) and np.isfinite(late_ulcer)):
        return False
    return bool(late_cagr > 0 and late_ulcer < anchor["late_ulcer"])


def verdict_table_v3(
    labels: list = None, anchor: pd.Series = None, family: pd.DataFrame | None = None,
    skip_placebo: bool = False,
) -> pd.DataFrame:
    """One row per recorded run: panel metrics, the CAGR given up, and every rule-v3 verdict column.

    Reads `runs` directly, so a run that was executed can never be silently left out of the table
    it should have been judged in.
    """
    anchor = anchor_panel if anchor is None else anchor
    chosen = runs if labels is None else [run_by_label[label] for label in labels]
    frame = pd.DataFrame([entry["panel"] for entry in chosen]).set_index("label")
    frame["family"] = [entry["family"] for entry in chosen]
    frame["cagr_sacrifice_pp"] = (anchor["cagr"] - frame["cagr"]) * 100.0
    frame["control_ref"] = [
        placebo_ref_observed(family, float(v)) if family is not None else float("nan")
        for v in frame["cycle_vol"]
    ]
    column = "passes_1_to_6" if skip_placebo else "passes_v3"
    frame[column] = [
        passes_constraints_v3(r, anchor, family, skip_placebo) for _, r in frame.iterrows()
    ]
    frame["failed"] = [
        failing_constraints_v3(r, anchor, family, skip_placebo) for _, r in frame.iterrows()
    ]
    frame["late_ok"] = [late_period_ok_v3(r, anchor) for _, r in frame.iterrows()]
    return frame.sort_values("cycle_sharpe", ascending=False)


# --------------------------------------------------------------------------------------------
# Uncertainty.
# --------------------------------------------------------------------------------------------

def bootstrap_paired_sharpe_diff(
    candidate: pd.Series, control: pd.Series, periods_per_year: float = None,
    block: int = BOOTSTRAP_BLOCK, draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED,
) -> dict:
    """95% interval on (candidate cycle Sharpe - control cycle Sharpe), paired on common blocks.

    Both series are aligned by date and resampled with the SAME block indices, so every draw
    compares the two strategies on the same market days. Resampling them independently would
    inflate the interval by destroying the pairing that makes the comparison informative.
    """
    periods = PERIODS_PER_YEAR if periods_per_year is None else periods_per_year
    joined = pd.concat([candidate.rename("c"), control.rename("x")], axis=1).dropna()
    n = len(joined)
    if n < block:
        return {"n": n, "observed": float("nan"), "lo": float("nan"), "hi": float("nan"), "block": block}
    values = joined.to_numpy()
    observed = (
        values[:, 0].mean() / values[:, 0].std() - values[:, 1].mean() / values[:, 1].std()
    ) * np.sqrt(periods)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        index = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        sample = values[index]
        c_std, x_std = sample[:, 0].std(), sample[:, 1].std()
        if c_std <= 0 or x_std <= 0:
            continue
        diffs.append((sample[:, 0].mean() / c_std - sample[:, 1].mean() / x_std) * np.sqrt(periods))
    if not diffs:
        return {"n": n, "observed": float(observed), "lo": float("nan"), "hi": float("nan"), "block": block}
    return {
        "n": n, "observed": float(observed), "block": block, "draws": len(diffs), "seed": seed,
        "lo": float(np.percentile(diffs, 2.5)), "hi": float(np.percentile(diffs, 97.5)),
    }


def bootstrap_margin_table(label: str, family: pd.DataFrame | None = None) -> pd.DataFrame:
    """Both decision boundaries for one run, at three block lengths.

    Against the anchor the boundary is -0.10, the Sharpe non-inferiority tolerance. Against the
    observed control it is +0.10, the complexity premium a non-simple mechanism has to earn. The
    interval either clears the boundary or it does not; block length 5 and 20 are reported so a
    conclusion that depends on the block choice is visible as one.
    """
    entry = run_by_label[label]
    rows = []
    comparisons = [("anchor", anchor_cycle_returns, -PLACEBO_MARGIN_V3)]
    if family is not None and len(family):
        reference_label = family.loc[
            family[family["cycle_vol"] <= float(entry["panel"]["cycle_vol"])]["cycle_sharpe"].idxmax()
        ] if len(family[family["cycle_vol"] <= float(entry["panel"]["cycle_vol"])]) else None
        name = reference_label.name if reference_label is not None else family["cycle_vol"].idxmin()
        comparisons.append(("observed control " + str(name), run_by_label[str(name)]["cycle_returns"], PLACEBO_MARGIN_V3))
    for block in (5, BOOTSTRAP_BLOCK, 20):
        for against, series, boundary in comparisons:
            result = bootstrap_paired_sharpe_diff(entry["cycle_returns"], series, block=block)
            rows.append({
                "run": label, "against": against, "block": block, "boundary": boundary,
                "observed_diff": result["observed"], "ci_lo": result["lo"], "ci_hi": result["hi"],
                "clears_boundary": bool(np.isfinite(result["lo"]) and result["lo"] > boundary),
            })
    return pd.DataFrame(rows)


def family_wise_joint(
    candidate_labels: list, anchor_returns_: pd.Series = None,
    periods_per_year: float = None, block: int = BOOTSTRAP_BLOCK, draws: int = 999,
    seed: int = BOOTSTRAP_SEED,
) -> tuple:
    """Family-wise p-value on the best Sharpe improvement over the anchor, jointly resampled.

    Replaces `family_wise_reality_check()`, which the review found misspecified: it resampled the
    anchor independently once per candidate, destroying the dependence between candidates that a
    max-statistic null is entirely about, and so produced a null far too wide to reject anything.

    Here every candidate and the anchor are stacked into one aligned matrix and resampled with
    COMMON block indices, so a draw is one bootstrap history experienced by all of them. Each
    candidate's bootstrap distribution of (its Sharpe - the anchor's Sharpe) is centred on its
    OBSERVED difference, which is the no-difference null, and the maximum across the family is
    taken per draw. `p = (1 + #{max_null >= observed_max}) / (draws + 1)`.

    It cannot correct for the adaptive research history behind the family - the earlier notebooks
    that decided which mechanisms were worth trying at all. Pass the COMPLETE executed candidate
    family; passing only the survivors defeats the purpose.
    """
    anchor_series = anchor_cycle_returns if anchor_returns_ is None else anchor_returns_
    periods = PERIODS_PER_YEAR if periods_per_year is None else periods_per_year
    columns = {"__anchor__": anchor_series}
    for label in candidate_labels:
        columns[label] = run_by_label[label]["cycle_returns"]
    matrix = pd.concat(columns, axis=1).dropna()
    names = [c for c in matrix.columns if c != "__anchor__"]
    values = matrix.to_numpy()
    anchor_column = list(matrix.columns).index("__anchor__")
    n = len(matrix)

    def sharpe(column_values):
        std = column_values.std()
        return column_values.mean() / std * np.sqrt(periods) if std > 0 else np.nan

    observed = {
        name: sharpe(values[:, list(matrix.columns).index(name)]) - sharpe(values[:, anchor_column])
        for name in names
    }
    observed_max = float(np.nanmax(list(observed.values()))) if observed else float("nan")

    rng = np.random.default_rng(seed)
    null_maxima = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        index = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        sample = values[index]
        anchor_sharpe = sharpe(sample[:, anchor_column])
        centred = [
            sharpe(sample[:, list(matrix.columns).index(name)]) - anchor_sharpe - observed[name]
            for name in names
        ]
        centred = [c for c in centred if np.isfinite(c)]
        if centred:
            null_maxima.append(max(centred))
    count = sum(1 for m in null_maxima if m >= observed_max)
    p_value = (1 + count) / (len(null_maxima) + 1) if null_maxima else float("nan")

    summary = pd.DataFrame({
        "metric": ["Family size", "Aligned cycles", "Best observed Sharpe improvement",
                   "Null 95th percentile", "Exceedances", "Draws", "Family-wise p-value"],
        "value": [len(names), n, observed_max,
                  float(np.percentile(null_maxima, 95)) if null_maxima else float("nan"),
                  count, len(null_maxima), p_value],
    })
    return summary, pd.Series(observed).sort_values(ascending=False)


print("harness_stability.py loaded: adoption rule v3, run bookkeeping, joint family-wise test.")
