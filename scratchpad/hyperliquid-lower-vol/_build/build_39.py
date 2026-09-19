"""NB39 - the NB38 trimmed-score screen on the FULL archive, in event time.

Standalone research notebook (no strategy engine). Everything is computed on observed marks:
event returns between consecutive marks, trimming by a FRACTION of events, staleness measured
against the vault's own marks, forward outcomes requiring marks near the end of the window.
"""
import sys
sys.path.insert(0, ".")
from builder import md, code, write_notebook, TRACK_DIR

HEADING = """# NB39 - trimmed trailing scores on the full archive, in event time

NB38 screened trimmed trailing scores against forward Sharpe on the dense-polling regime only
(from 2026-04-01): about four months, 70 overlapping decisions. This notebook runs the same
question on the whole archive from mid-2025, which means running it on WEEKLY data for most of
its length: through 2025 the archive holds about one price-changing mark per vault per week,
one every two days in January-March 2026, and fifteen or more a day from April.

Forward-filling weekly marks to a daily grid and then computing daily statistics is where the
gotchas live, so nothing here is computed on a daily grid. Every score uses observed marks
only: event log returns between consecutive marks, trimming by a FRACTION of events (so a weekly
vault loses one or three of its thirteen marks in 90 days and a daily vault loses nine or
twenty-two of ninety), staleness measured in days since the vault's own last mark, and forward
outcomes that must contain marks near the end of the window. The primary horizon is 60 days
because a 30-day window holds about four weekly marks; the 30-day horizon is kept as a
secondary target. The three polling regimes are screened together and separately.

**Focus is forward Sharpe.** Verdict DIAGNOSTIC: a screen, not a result. No vault is selected,
masked or tuned by name.

**Based on:** [38-research-trimmed-return-screen.ipynb](38-research-trimmed-return-screen.ipynb)
(machinery and its two reviews), [33-research-lead-comparison.ipynb](33-research-lead-comparison.ipynb)
(the archive density table that defines the regimes).

## Method

Marks: one per vault per UTC day (the last poll of the day). Events: consecutive marks; event
return = log price ratio; event span = days between them. A candidate at decision T needs, in
the trailing window (T-1-W, T-1] for W in 90 and 180 days, at least 8 event returns (9 marks) and a
mark at or before the window start, its last mark within 14 days of T-1, and a TVL of at least
7,500 USD at that mark. Scores per window: return score
(sum of event returns, annualised over W; raw and with the best 10% and 25% of events removed),
Sharpe score (return score over event volatility sqrt(sum r^2 / W x 365), raw and trimmed the
same way), Sortino, event volatility, mark count. Forward outcomes over (T, T + H] for H = 60
(primary) and 30: log return from the mark carried at T to the last mark in the window,
event volatility, event Sharpe, log max drawdown on the mark path; a window needs at least 6
(H = 60) or 4 (H = 30) marks and one within 14 days of its end.

Inference as NB38 with one change forced by the horizon: per-date signed Spearman averaged
over dates, one two-way cluster bootstrap of TILED, non-wrapping 30-decision (60-day) date
blocks x vault clusters, 500 draws, seed 20260917, shared across every hypothesis (45- and
90-decision blocks as sensitivities), studentised max-T simultaneous lower bounds over the signal family on the
primary target, paired trimmed-minus-raw differences on the same draws with their own family
bound, and a foresight-oracle reachability assertion.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]

cells.append(md("""## Part 0. Archive, provenance, constants, regimes
"""))
cells.append(code('''import hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60); pd.set_option("display.max_rows", 200)

ARCHIVE = Path.home() / ".cache/tradingstrategy/vaults/downloads/vault-prices.parquet"
raw_bytes = ARCHIVE.read_bytes()
PROVENANCE = {"file": str(ARCHIVE), "bytes": len(raw_bytes), "sha256": hashlib.sha256(raw_bytes).hexdigest()}
del raw_bytes
HYPERCORE_CHAIN = 9999

WINDOWS = (90, 180)
TRIM_FRACTIONS = (0.0, 0.10, 0.25)
HORIZONS = {60: 6, 30: 4}          # forward horizon days -> minimum observed marks in the window
PRIMARY_H = 60
PANEL_START = pd.Timestamp("2025-07-01")
DECISION_STEP_DAYS = 2
MIN_TVL_USD = 7_500.0
MIN_EVENTS = 8        # events strictly inside the window, i.e. at least 9 marks
STALE_DAYS = 14
MIN_CANDIDATES = 8
MIN_DATES = 40
YOUNG_DAYS = 360
DRAWS = 500
#: Date blocks must be at least as long as the forward horizon (60 days = 30 decisions) so that
#: overlapping outcomes stay together inside a block; blocks are NOT wrapped circularly, because
#: joining July 2026 to July 2025 would splice two polling regimes. 45 decisions (90 days) is an
#: intermediate sensitivity; the 180-day score persistence is covered only by DATE_BLOCK_LONG.
DATE_BLOCK = 30
DATE_BLOCK_SENSITIVITY = 45
#: 90 decisions = 180 days, the longest trailing-score window. With 192 decisions this leaves
#: about two blocks per draw, so its bounds are as much a statement about the sample size as
#: about the dependence; it is run because no shorter block covers the score persistence.
DATE_BLOCK_LONG = 90
SEED = 20260917
LEVEL = 0.95
REGIMES = [("weekly 2025", pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")),
           ("transition Jan-Mar 2026", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-04-01")),
           ("dense Apr 2026 on", pd.Timestamp("2026-04-01"), pd.Timestamp("2027-01-01"))]


def regime_of(t):
    """Regime of the decision date."""
    for name, a, b in REGIMES:
        if a <= t < b:
            return name
    return "other"


def regime_contained(t, H):
    """Regime that contains BOTH the decision date and its whole forward horizon, else 'crosses'."""
    for name, a, b in REGIMES:
        if a <= t and t + pd.Timedelta(days=H) < b:
            return name
    return "crosses"


df = pd.read_parquet(ARCHIVE, columns=["address", "chain", "share_price", "total_assets", "name"])
df = df[df["chain"] == HYPERCORE_CHAIN].reset_index()
df["timestamp"] = pd.to_datetime(df["timestamp"])
# Vault age is measured from the vault's FIRST mark anywhere in the archive, before any date cut.
FIRST_MARK = df.groupby("address")["timestamp"].min().dt.floor("D")
df = df[df["timestamp"] >= pd.Timestamp("2025-01-01")].sort_values(["address", "timestamp"])
df["date"] = df["timestamp"].dt.floor("D")
marks = df.groupby(["address", "date"])[["share_price", "total_assets"]].last().reset_index()
marks = marks[marks["share_price"] > 0]
names = df.groupby("address")["name"].last()
LAST_MARK = df["timestamp"].max()
display(pd.Series({**PROVENANCE, "last_mark": str(LAST_MARK), "hypercore_vaults": marks["address"].nunique(),
                   "mark_days": len(marks)}, name="value").to_frame())

# Polling density by month on the mark-day grid: marks per vault per day among vaults above the TVL floor.
mm = marks[marks["total_assets"] >= MIN_TVL_USD].copy()
mm["month"] = mm["date"].dt.to_period("M")
dens = mm.groupby("month").agg(vaults=("address", "nunique"), mark_days=("date", "size"))
dens["mark_days_per_vault_per_day"] = dens["mark_days"] / dens["vaults"] / 30.0
display(dens.round(3).T)
'''))

cells.append(md("""## Part 1. The event-time panel

One row per (decision date, vault). Nothing is forward-filled: a window's statistics come from
the marks inside it, and a vault whose last mark is older than 14 days is not a candidate.
"""))
cells.append(code('''def event_scores(r: np.ndarray, W: int) -> dict:
    """Raw and trimmed return and Sharpe scores from event returns `r` in a window of W days.
    Trimming removes the ceil(f x n) largest event returns; the window length stays the denominator,
    so these are ranking scores, not investable returns."""
    out = {}
    n = len(r)
    order = np.sort(r)
    for f in TRIM_FRACTIONS:
        k = int(math.ceil(f * n)) if f > 0 else 0
        kept = order[:n - k] if k else order
        rate = float(kept.sum() * 365.0 / W)
        vol = float(math.sqrt((kept ** 2).sum() * 365.0 / W)) if len(kept) else float("nan")
        tag = f"f{int(f * 100):02d}"
        out[f"ret_{tag}"] = rate
        out[f"sharpe_{tag}"] = rate / vol if vol and vol > 0 else float("nan")
    downside = math.sqrt((np.clip(r, None, 0.0) ** 2).sum() * 365.0 / W)
    out["sortino"] = out["ret_f00"] / downside if downside > 0 else float("nan")
    out["vol"] = float(math.sqrt((r ** 2).sum() * 365.0 / W))
    out["events"] = int(n)
    return out


def forward_outcome(carried: float, fwd_prices: np.ndarray, H: int) -> dict:
    """Outcome from the mark carried at T to the marks in (T, T + H]."""
    prices = np.concatenate([[carried], fwd_prices])
    r = np.diff(np.log(prices))
    total = float(r.sum())
    vol = float(math.sqrt((r ** 2).sum() * 365.0 / H))
    path = np.concatenate([[0.0], np.cumsum(r)])
    return {f"fwd{H}_return": total, f"fwd{H}_vol": vol,
            f"fwd{H}_sharpe": (total * 365.0 / H) / vol if vol > 0 else float("nan"),
            f"fwd{H}_log_max_dd": float(np.min(path - np.maximum.accumulate(path))),
            f"fwd{H}_events": int(len(fwd_prices))}


max_h = max(HORIZONS)
last_decision = LAST_MARK.floor("D") - pd.Timedelta(days=max_h)
decisions = pd.date_range(PANEL_START, last_decision, freq=f"{DECISION_STEP_DAYS}D")
rows = []
dropped = {"stale_or_too_few_marks": 0, "tvl": 0, "forward_marks": 0}
for address, g in marks.groupby("address"):
    g = g.set_index("date").sort_index()
    mdays = g.index
    prices = g["share_price"].to_numpy()
    tvls = g["total_assets"].to_numpy()
    born = FIRST_MARK[address]
    for t in decisions:
        t1 = t - pd.Timedelta(days=1)
        i_last = int(mdays.searchsorted(t1, side="right")) - 1   # last mark at or before T-1
        if i_last < 0 or (t1 - mdays[i_last]).days > STALE_DAYS:
            dropped["stale_or_too_few_marks"] += 1
            continue
        if tvls[i_last] < MIN_TVL_USD:
            dropped["tvl"] += 1
            continue
        row = {"address": address, "date": t, "age_days": int((t - born).days), "regime": regime_of(t),
               "days_since_mark": int((t1 - mdays[i_last]).days), "first_mark_before_2025": bool(born < pd.Timestamp("2025-01-01"))}
        scored_any = False
        for W in WINDOWS:
            start = t1 - pd.Timedelta(days=W)
            i_first = int(mdays.searchsorted(start, side="right"))   # first mark strictly after start
            n_marks = i_last - i_first + 1
            # The vault must have existed before the window (a mark at or before its start), so a
            # W-day score is never computed on a vault younger than W days.
            # The score must SPAN the window: a mark at or before the window start, the first
            # in-window mark within STALE_DAYS of the start, and the last within STALE_DAYS of T-1
            # (already required). Otherwise a W-day score could be eight clustered late events.
            if n_marks < MIN_EVENTS + 1 or i_first == 0 or (mdays[i_first] - start).days > STALE_DAYS:
                for f in TRIM_FRACTIONS:
                    tag = f"f{int(f * 100):02d}"
                    row[f"ret{W}_{tag}"] = np.nan; row[f"sharpe{W}_{tag}"] = np.nan
                row[f"sortino{W}"] = np.nan; row[f"vol{W}"] = np.nan; row[f"events{W}"] = int(max(n_marks, 0))
                continue
            # Event returns between consecutive marks INSIDE the window only: the first event starts
            # at the first mark in the window, so no return interval begins before the window.
            seg = prices[i_first:i_last + 1]
            r = np.diff(np.log(seg))
            s = event_scores(r, W)
            for key, value in s.items():
                base, _, tag = key.partition("_")
                row[f"{base}{W}_{tag}" if tag else f"{base}{W}"] = value
            scored_any = True
        if not scored_any:
            dropped["stale_or_too_few_marks"] += 1
            continue
        i_carry = int(mdays.searchsorted(t, side="right")) - 1
        carried = float(prices[i_carry])
        ok_any = False
        for H, min_marks in HORIZONS.items():
            t_end = t + pd.Timedelta(days=H)
            j0 = int(mdays.searchsorted(t, side="right")); j1 = int(mdays.searchsorted(t_end, side="right"))
            fwd = prices[j0:j1]
            if len(fwd) < min_marks or (t_end - mdays[j1 - 1]).days > STALE_DAYS:
                for k in ("return", "vol", "sharpe", "log_max_dd"):
                    row[f"fwd{H}_{k}"] = np.nan
                row[f"fwd{H}_events"] = int(len(fwd))
                continue
            row.update(forward_outcome(carried, fwd, H))
            ok_any = True
        if not ok_any:
            dropped["forward_marks"] += 1
            continue
        rows.append(row)
panel = pd.DataFrame(rows)
panel["young"] = panel["age_days"] < YOUNG_DAYS
panel["regime_contained"] = [regime_contained(t, PRIMARY_H) for t in panel["date"]]
print("candidate-dates dropped:", dropped)
print(f"panel: {len(panel):,} rows, {panel['address'].nunique()} vaults, {panel['date'].nunique()} decisions "
      f"{panel['date'].min().date()} to {panel['date'].max().date()}; young (< {YOUNG_DAYS} d from the vault's first mark in "
      f"the whole archive) share of rows {panel['young'].mean():.1%}; rows from vaults first marked before 2025: "
      f"{panel['first_mark_before_2025'].mean():.1%}")
by_regime = panel.groupby("regime").agg(rows=("address", "size"), vaults=("address", "nunique"), decisions=("date", "nunique"),
                                        events90_median=("events90", "median"), events180_median=("events180", "median"),
                                        fwd60_events_median=("fwd60_events", "median"), fwd30_events_median=("fwd30_events", "median"),
                                        fwd60_finite=("fwd60_sharpe", lambda s: float(np.isfinite(s).mean())),
                                        fwd30_finite=("fwd30_sharpe", lambda s: float(np.isfinite(s).mean())),
                                        young_share=("young", "mean"))
display(by_regime.round(3))

SIGNALS = []
for W in WINDOWS:
    for f in TRIM_FRACTIONS:
        tag = f"f{int(f * 100):02d}"
        SIGNALS.append({"name": f"ret{W}_{tag}", "direction": "high", "window": W, "trim": f, "family": "return"})
    for f in TRIM_FRACTIONS:
        tag = f"f{int(f * 100):02d}"
        SIGNALS.append({"name": f"sharpe{W}_{tag}", "direction": "high", "window": W, "trim": f, "family": "sharpe"})
    SIGNALS.append({"name": f"sortino{W}", "direction": "high", "window": W, "trim": None, "family": "sortino"})
    SIGNALS.append({"name": f"vol{W}", "direction": "low", "window": W, "trim": None, "family": "vol"})
SIGNAL_NAMES = [s["name"] for s in SIGNALS]
SIGNAL_SIGN = {s["name"]: (1.0 if s["direction"] == "high" else -1.0) for s in SIGNALS}
TARGETS = ["fwd60_sharpe", "fwd60_return", "fwd60_vol", "fwd60_log_max_dd", "fwd30_sharpe", "fwd30_return"]
TARGET_SIGN = {"fwd60_sharpe": 1.0, "fwd60_return": 1.0, "fwd60_vol": -1.0, "fwd60_log_max_dd": 1.0, "fwd30_sharpe": 1.0, "fwd30_return": 1.0}
PRIMARY = f"fwd{PRIMARY_H}_sharpe"
#: Raw/trimmed pairs for the MATCHED paired comparison: both Spearmans on the joint finite mask
#: of raw score, trimmed score and primary target (sixth review), so a difference is trimming
#: alone and not a change of eligible vaults.
PAIRS = [(f"{fam}{W}_f00", f"{fam}{W}_f{int(f * 100):02d}") for W in WINDOWS for fam in ("ret", "sharpe") for f in TRIM_FRACTIONS[1:]]
PAIR_INDEX = [(SIGNAL_NAMES.index(a), SIGNAL_NAMES.index(b)) for a, b in PAIRS]
coverage = pd.DataFrame({s: np.isfinite(panel[s]).mean() for s in SIGNAL_NAMES}, index=["finite_share"]).T
display(coverage.round(3).T)
'''))

cells.append(md("""## Part 2. One shared bootstrap, every hypothesis

As NB38: per-date signed Spearman, equal-weight mean over dates, one two-way cluster bootstrap
shared by every signal, target and paired difference; simultaneous max-T lower bounds over the
signal family on the primary target and over the paired-comparison family.
"""))
cells.append(code('''def per_date_blocks(frame: pd.DataFrame) -> dict:
    out = {}
    cols = SIGNAL_NAMES + TARGETS
    for date, g in frame.groupby("date"):
        out[pd.Timestamp(date)] = {"vault": g["address"].to_numpy(), "values": g[cols].to_numpy(dtype=float)}
    return out


def date_statistics(values: np.ndarray) -> tuple:
    """Per-date signed Spearman for every (signal, target) on each pair's own complete cases, plus
    the MATCHED paired statistics for the primary target (raw, trimmed, difference, n on the joint
    finite mask). Exact: pairs that share a complete-case mask are ranked once on that subset
    together, which gives the same ranks as ranking each pair separately."""
    S, T = len(SIGNAL_NAMES), len(TARGETS)
    out = np.full((S, T), np.nan)
    finite = np.isfinite(values)
    sig_sign = np.array([SIGNAL_SIGN[nm] for nm in SIGNAL_NAMES])
    tgt_sign = np.array([TARGET_SIGN[t] for t in TARGETS])
    # Group (signal, target) pairs by their joint mask; rank the needed columns once per group.
    groups = {}
    for i in range(S):
        for j in range(T):
            key = np.packbits(finite[:, i] & finite[:, S + j]).tobytes()
            groups.setdefault(key, (finite[:, i] & finite[:, S + j], [])) [1].append((i, j))
    for mask, pairs in groups.values():
        n_ok = int(mask.sum())
        if n_ok < MIN_CANDIDATES:
            continue
        cols = sorted({i for i, _ in pairs} | {S + j for _, j in pairs})
        sub = values[mask][:, cols]
        ranks = rankdata(sub, axis=0)
        centred = ranks - ranks.mean(axis=0)
        norms = np.sqrt((centred ** 2).sum(axis=0))
        col_pos = {c: k for k, c in enumerate(cols)}
        for i, j in pairs:
            a, b = col_pos[i], col_pos[S + j]
            if norms[a] == 0 or norms[b] == 0:
                continue
            out[i, j] = sig_sign[i] * tgt_sign[j] * float((centred[:, a] * centred[:, b]).sum() / (norms[a] * norms[b]))
    pairs_out = np.full((len(PAIRS), 4), np.nan)
    jp = S + TARGETS.index(PRIMARY)
    for k, (ia, ib) in enumerate(PAIR_INDEX):
        ok = finite[:, ia] & finite[:, ib] & finite[:, jp]
        n_ok = int(ok.sum())
        if n_ok < MIN_CANDIDATES:
            continue
        sub = values[ok][:, [ia, ib, jp]]
        ranks = rankdata(sub, axis=0)
        centred = ranks - ranks.mean(axis=0)
        norms = np.sqrt((centred ** 2).sum(axis=0))
        if norms[0] == 0 or norms[1] == 0 or norms[2] == 0:
            continue
        ra = float((centred[:, 0] * centred[:, 2]).sum() / (norms[0] * norms[2]))
        rb = float((centred[:, 1] * centred[:, 2]).sum() / (norms[1] * norms[2]))
        sign = SIGNAL_SIGN[SIGNAL_NAMES[ia]] * TARGET_SIGN[PRIMARY]
        pairs_out[k] = (sign * ra, sign * rb, sign * (rb - ra), float(n_ok))
    return out, pairs_out


def mean_over_dates(blocks: dict, dates: list, counts: dict | None = None) -> tuple:
    S, T = len(SIGNAL_NAMES), len(TARGETS)
    total, n = np.zeros((S, T)), np.zeros((S, T))
    ptotal, pn = np.zeros((len(PAIRS), 4)), np.zeros((len(PAIRS), 4))
    for date in dates:
        block = blocks.get(date)
        if block is None:
            continue
        values = block["values"]
        if counts is not None:
            repeats = np.array([counts.get(v, 0) for v in block["vault"]], dtype=int)
            if repeats.sum() < MIN_CANDIDATES:
                continue
            values = np.repeat(values, repeats, axis=0)
        stats, pairs = date_statistics(values)
        finite = np.isfinite(stats)
        total[finite] += stats[finite]
        n[finite] += 1
        pf = np.isfinite(pairs)
        ptotal[pf] += pairs[pf]
        pn[pf] += 1
    with np.errstate(invalid="ignore"):
        return (np.where(n > 0, total / np.maximum(n, 1), np.nan), n,
                np.where(pn > 0, ptotal / np.maximum(pn, 1), np.nan), pn)


def bootstrap(frame: pd.DataFrame, draws: int = DRAWS, seed: int = SEED, verbose: bool = True, block: int = DATE_BLOCK) -> dict:
    """Two-way cluster bootstrap: TILED date blocks and vault clusters, together.

    Per draw the date axis is cut into consecutive tiles of `block` decisions starting at a random
    offset in [0, block) - the first and last tiles are the shorter remainders - and tiles are
    resampled with replacement until the draw holds at least as many decisions as the panel. The
    draw is NOT truncated: the last selected tile is kept whole, so a draw can be slightly longer
    than the panel. Because every decision belongs to exactly one tile and tiles are selected
    with equal probability, every decision has the same expected inclusion count (the equal-weight
    mean over the draw's dates is what the statistic uses). Coverage is measured over the draws
    and asserted below. No tile wraps from the end of the archive to its start.
    """
    blocks = per_date_blocks(frame)
    dates = sorted(blocks)
    vaults = sorted(frame["address"].unique())
    observed, n_dates, pair_observed, pair_n = mean_over_dates(blocks, dates)
    rng = np.random.default_rng(seed)
    n = len(dates)
    block = min(block, n)
    reps = np.full((draws,) + observed.shape, np.nan)
    pair_reps = np.full((draws,) + pair_observed.shape, np.nan)
    inclusion = np.zeros(n)
    effective = np.zeros(n)     # sum over draws of multiplicity / draw length: the weight the statistic gives a date
    draw_lengths = []
    for d in range(draws):
        offset = int(rng.integers(0, block))
        edges = [0] + list(range(offset, n, block)) + [n]
        edges = sorted(set(e for e in edges if 0 <= e <= n))
        tiles = [np.arange(a, b) for a, b in zip(edges[:-1], edges[1:]) if b > a]
        chosen = []
        while sum(len(t) for t in chosen) < n:
            chosen.append(tiles[int(rng.integers(0, len(tiles)))])
        index = np.concatenate(chosen)          # whole tiles only; never truncated
        np.add.at(inclusion, index, 1)
        np.add.at(effective, index, 1.0 / len(index))
        draw_lengths.append(len(index))
        drawn = rng.choice(len(vaults), size=len(vaults), replace=True)
        counts = {}
        for v in drawn:
            counts[vaults[v]] = counts.get(vaults[v], 0) + 1
        reps[d], _, pair_reps[d], _ = mean_over_dates(blocks, [dates[i] for i in index], counts)
        if verbose and (d + 1) % 100 == 0:
            print(f"  draw {d + 1}/{draws}")
    # Coverage check: with uniform tile selection and no truncation, every date's inclusion count
    # should be equal in expectation. Report the spread across dates relative to the mean and
    # fail if the ends of the archive are systematically under- or over-represented.
    # Coverage is measured on the EFFECTIVE weight each date receives in the statistic: the
    # per-draw mean over dates weights every occurrence by 1 / draw length, and draws differ in
    # length because whole tiles are kept. Reported relative to the mean over dates; the first
    # and last blocks are asserted separately, and every single date is asserted within a
    # tolerance, so neither an asymmetric end bias nor an outlying date can hide in an average.
    coverage = effective / effective.mean()
    raw_coverage = inclusion / inclusion.mean()
    first, last = float(np.mean(coverage[:block])), float(np.mean(coverage[-block:]))
    ends = float(np.mean(np.concatenate([coverage[:block], coverage[-block:]])))
    middle = float(np.mean(coverage[block:-block])) if n > 2 * block else float("nan")
    print(f"  effective coverage over {draws} draws: min {coverage.min():.3f}, max {coverage.max():.3f} of mean; first {block} dates "
          f"{first:.3f}, last {block} dates {last:.3f}, middle {middle:.3f} (raw inclusion min {raw_coverage.min():.3f}, max "
          f"{raw_coverage.max():.3f}); draw length mean {np.mean(draw_lengths):.1f} of {n} decisions")
    assert abs(first - 1.0) < 0.15 and abs(last - 1.0) < 0.15, f"tiled bootstrap misweights an end: first {first:.3f}, last {last:.3f}"
    assert coverage.min() > 0.8 and coverage.max() < 1.2, f"a date's effective weight is outside 0.8-1.2 of the mean: {coverage.min():.3f}-{coverage.max():.3f}"
    return {"observed": observed, "draws": reps, "n_dates": n_dates, "dates": dates, "rows": len(frame),
            "pair_observed": pair_observed, "pair_draws": pair_reps, "pair_n": pair_n,
            "coverage_min": float(coverage.min()), "coverage_max": float(coverage.max()), "coverage_first": first,
            "coverage_last": last, "coverage_ends": ends, "coverage_middle": middle, "draw_length_mean": float(np.mean(draw_lengths)),
            "raw_inclusion_min": float(raw_coverage.min()), "raw_inclusion_max": float(raw_coverage.max())}


def simultaneous_lower(observed: np.ndarray, reps: np.ndarray, level: float = LEVEL) -> dict:
    se = np.nanstd(reps, axis=0, ddof=1)
    member = np.isfinite(observed) & np.isfinite(se) & (se > 0)
    stud = (reps - observed[None, :]) / np.where(se > 0, se, np.nan)[None, :]
    complete = np.isfinite(stud[:, member]).all(axis=1) if member.any() else np.zeros(len(reps), dtype=bool)
    per_draw_max = stud[complete][:, member].max(axis=1) if complete.any() else np.array([])
    critical = float(np.percentile(per_draw_max, level * 100.0)) if len(per_draw_max) >= 100 else float("nan")
    lower = np.where(member, observed - critical * se, np.nan)
    centred = reps - observed[None, :]
    p = (1.0 + (centred >= observed[None, :]).sum(axis=0)) / (len(reps) + 1.0)
    return {"se": se, "critical": critical, "lower": lower, "lower_unadjusted": np.nanpercentile(reps, (1 - level) * 100.0, axis=0),
            "p": p, "family_size": int(member.sum()), "complete_draws": int(len(per_draw_max))}


def screen(frame: pd.DataFrame, label: str, verbose: bool = True, block: int = DATE_BLOCK) -> dict:
    print(f"{label}: {len(frame):,} rows, {frame['date'].nunique()} decisions, {frame['address'].nunique()} vaults, date block {block}")
    boot = bootstrap(frame, verbose=verbose, block=block)
    j = TARGETS.index(PRIMARY)
    fam = simultaneous_lower(boot["observed"][:, j], boot["draws"][:, :, j])
    rows = []
    for i, s in enumerate(SIGNALS):
        row = {"signal": s["name"], "family": s["family"], "window": s["window"], "trim": s["trim"],
               "dates": int(boot["n_dates"][i, j]), "evaluated": bool(boot["n_dates"][i, j] >= MIN_DATES and fam["se"][i] > 0)}
        for t_idx, target in enumerate(TARGETS):
            row[f"rho_{target}"] = boot["observed"][i, t_idx]
        row["se_primary"] = fam["se"][i]
        row["lo_primary_simultaneous"] = fam["lower"][i]
        row["lo_primary_unadjusted"] = fam["lower_unadjusted"][i]
        row["p_primary"] = fam["p"][i]
        rows.append(row)
    table = pd.DataFrame(rows).set_index("signal")
    # MATCHED paired differences: per date, raw and trimmed Spearmans on the joint finite mask of
    # both scores and the primary target, so the difference is trimming alone; resampled on the
    # same draws. The unmatched per-signal correlations in the table above use each score's own
    # complete cases and can differ slightly from the matched values here.
    diffs, d_obs, d_reps = [], [], []
    for k, (raw_name, trim_name) in enumerate(PAIRS):
        fam_name = "ret" if raw_name.startswith("ret") else "sharpe"
        W = int(raw_name.replace(fam_name, "").split("_")[0])
        f = int(trim_name.split("_f")[1]) / 100.0
        obs = boot["pair_observed"][k, 2]
        rep = boot["pair_draws"][:, k, 2]
        d_obs.append(obs); d_reps.append(rep)
        fin = rep[np.isfinite(rep)]; n = len(fin); centred = fin - obs
        p_hi = (1.0 + (centred >= obs).sum()) / (n + 1.0); p_lo = (1.0 + (centred <= obs).sum()) / (n + 1.0)
        diffs.append({"family": fam_name, "window": W, "trim": f,
                      "raw_rho_matched": boot["pair_observed"][k, 0], "trimmed_rho_matched": boot["pair_observed"][k, 1],
                      "raw_rho_unmatched": boot["observed"][SIGNAL_NAMES.index(raw_name), j],
                      "trimmed_rho_unmatched": boot["observed"][SIGNAL_NAMES.index(trim_name), j],
                      "difference": obs, "matched_candidates_mean": boot["pair_observed"][k, 3],
                      "ci_lo": float(np.percentile(fin, 2.5)) if n >= 100 else np.nan,
                      "ci_hi": float(np.percentile(fin, 97.5)) if n >= 100 else np.nan,
                      "p_two_sided_add_one": float(min(1.0, 2 * min(p_hi, p_lo))) if n >= 100 else np.nan, "draws": int(n)})
    paired = pd.DataFrame(diffs)
    pfam = simultaneous_lower(np.array(d_obs), np.column_stack(d_reps))
    paired["lo_simultaneous_family"] = pfam["lower"]
    paired["se"] = pfam["se"]
    return {"label": label, "table": table, "paired": paired, "critical": fam["critical"], "family_size": fam["family_size"],
            "complete_draws": fam["complete_draws"], "boot": boot, "paired_critical": pfam["critical"], "paired_family_size": pfam["family_size"],
            "block": block}


TABLE_COLS = ["family", "window", "trim", "dates", "evaluated", f"rho_{PRIMARY}", "se_primary", "lo_primary_simultaneous",
              "lo_primary_unadjusted", "p_primary", "rho_fwd60_return", "rho_fwd60_vol", "rho_fwd60_log_max_dd", "rho_fwd30_sharpe", "rho_fwd30_return"]
manifest_38 = json.loads(Path("_build/manifest_38.json").read_text())
nb38_ref = {"nb38_decisions": manifest_38["panel"]["decisions"], "nb38_rows": manifest_38["panel"]["rows"],
            "nb38_sharpe180_rho_fwd30_sharpe": manifest_38["screens"]["all"]["table"]["sharpe180_k0"]["rho_fwd_sharpe"],
            "nb38_sharpe180_lo_simultaneous": manifest_38["screens"]["all"]["table"]["sharpe180_k0"]["lo_sharpe_simultaneous"]}
print("NB38 comparison values (from _build/manifest_38.json):", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in nb38_ref.items()})
full = screen(panel, "all regimes")
print(f"\\nprimary family: {full['family_size']} signals, critical {full['critical']:.4f} on {full['complete_draws']} complete draws")
display(full["table"][TABLE_COLS].round(4))
# Sensitivity to the block length: 45 decisions (90 days) as an intermediate, 90 decisions (180 days) as the
# longest trailing-score window.
full45 = screen(panel, "all regimes, block 45", verbose=False, block=DATE_BLOCK_SENSITIVITY)
full90 = screen(panel, "all regimes, block 90", verbose=False, block=DATE_BLOCK_LONG)
sens = pd.DataFrame({"rho": full["table"][f"rho_{PRIMARY}"], "lo_block30": full["table"]["lo_primary_simultaneous"],
                     "lo_block45": full45["table"]["lo_primary_simultaneous"], "lo_block90": full90["table"]["lo_primary_simultaneous"],
                     "se_block30": full["table"]["se_primary"], "se_block45": full45["table"]["se_primary"], "se_block90": full90["table"]["se_primary"]})
for b in (30, 45, 90):
    sens[f"clears_block{b}"] = sens[f"lo_block{b}"] > 0
print(f"\\nblock-length sensitivity (critical {full['critical']:.3f} at 30, {full45['critical']:.3f} at 45, {full90['critical']:.3f} at 90 decisions): "
      f"{int(sens['clears_block30'].sum())} signals clear at block 30, {int(sens['clears_block45'].sum())} at 45, {int(sens['clears_block90'].sum())} at 90 "
      f"(90 decisions = 180 days = the longest trailing window; the {len(full['boot']['dates'])} decisions are "
      f"{len(full['boot']['dates']) / DATE_BLOCK_LONG:.2f} block-equivalents; the source tiling is one or two full tiles plus "
      f"remainders depending on the offset, and a draw repeats tiles)")
display(sens.round(4))
print(f"\\nMATCHED PAIRED trimmed - raw on {PRIMARY}, both Spearmans on the joint finite mask per date (per-comparison 95% "
      f"intervals; simultaneous lower bound over the {full['paired_family_size']} paired comparisons, critical {full['paired_critical']:.4f}):")
display(full["paired"].round(4))
'''))

cells.append(md("""### Reachability

A noisy foresight oracle (the primary target plus 5% noise) through the identical machinery must
clear the family-wise lower bound; otherwise an all-fail result says nothing about the signals.
"""))
cells.append(code('''rng = np.random.default_rng(SEED + 1)
oracle_panel = panel.copy()
oracle_panel["oracle"] = oracle_panel[PRIMARY] + rng.normal(0.0, 0.05 * float(np.nanstd(oracle_panel[PRIMARY])), len(oracle_panel))
_saved = (SIGNALS, SIGNAL_NAMES, SIGNAL_SIGN)
SIGNALS = list(SIGNALS) + [{"name": "oracle", "direction": "high", "window": None, "trim": None, "family": "oracle"}]
SIGNAL_NAMES = [s["name"] for s in SIGNALS]
SIGNAL_SIGN = {s["name"]: (1.0 if s["direction"] == "high" else -1.0) for s in SIGNALS}
try:
    oracle_res = screen(oracle_panel, "oracle reachability", verbose=False)
finally:
    SIGNALS, SIGNAL_NAMES, SIGNAL_SIGN = _saved
orow = oracle_res["table"].loc["oracle"]
print(f"oracle: rho {orow[f'rho_{PRIMARY}']:.4f}, simultaneous lower bound {orow['lo_primary_simultaneous']:.4f} over "
      f"{oracle_res['family_size']} signals (critical {oracle_res['critical']:.4f}); finite primary target rows "
      f"{int(np.isfinite(panel[PRIMARY]).sum())} of {len(panel)}")
assert orow["lo_primary_simultaneous"] > 0, "the screen cannot produce a positive simultaneous bound even for a foresight oracle"
print("reachable")
'''))

cells.append(md("""## Part 3. Per regime, and young against old

A regime cohort is the set of decisions whose decision date AND whole 60-day forward horizon lie
inside the regime, so a weekly-regime outcome is measured on weekly marks. Each cohort is a
separate sample with a separate bootstrap. Young (< 360 days) and old are split on the whole
panel; they have different date coverage and are estimates on different samples, not a test of
a difference.
"""))
cells.append(code('''SHORT_COLS = ["window", "trim", "dates", "evaluated", f"rho_{PRIMARY}", "lo_primary_simultaneous", "p_primary",
              "rho_fwd60_return", "rho_fwd60_vol", "rho_fwd30_sharpe"]
by_regime_screens = {}
print("decisions whose whole 60-day horizon lies inside one regime:", panel.groupby("regime_contained")["date"].nunique().to_dict())
for name, a, b in REGIMES:
    sub = panel[panel["regime_contained"] == name]
    if sub["date"].nunique() < MIN_DATES:
        print(f"{name}: only {sub['date'].nunique()} decisions with the whole horizon inside the regime - not screened")
        continue
    res = screen(sub, name, verbose=False)
    by_regime_screens[name] = res
    print(f"  family {res['family_size']}, critical {res['critical']:.4f}, complete draws {res['complete_draws']}")
    display(res["table"][SHORT_COLS].round(4))
    print(f"  paired trimmed - raw on {PRIMARY} (family critical {res['paired_critical']:.4f}):")
    display(res["paired"].round(4))
young = screen(panel[panel["young"]], "young (< 360 days)", verbose=False)
old = screen(panel[~panel["young"]], "old (>= 360 days)", verbose=False)
for res in (young, old):
    print(f"\\n{res['label']}: family {res['family_size']}, critical {res['critical']:.4f}")
    display(res["table"][SHORT_COLS].round(4))
    display(res["paired"].round(4))
'''))

cells.append(md("""## Part 4. Manifest
"""))
cells.append(code('''def table_records(res):
    return {"table": res["table"].round(6).to_dict(orient="index"), "paired": res["paired"].round(6).to_dict(orient="records"),
            "critical": res["critical"], "family_size": res["family_size"], "complete_draws": res["complete_draws"],
            "paired_critical": res["paired_critical"], "paired_family_size": res["paired_family_size"],
            "rows": int(res["boot"]["rows"]), "decisions": int(len(res["boot"]["dates"])), "block": res["block"],
            "coverage": {k: res["boot"][k] for k in ("coverage_min", "coverage_max", "coverage_first", "coverage_last", "coverage_ends", "coverage_middle", "draw_length_mean", "raw_inclusion_min", "raw_inclusion_max")}}

manifest = {
    "verdict": "DIAGNOSTIC - a vault-level screen on the full archive, not a result",
    "provenance": {**PROVENANCE, "last_mark": str(LAST_MARK)},
    "constants": {"windows": list(WINDOWS), "trim_fractions": list(TRIM_FRACTIONS), "horizons": {str(k): v for k, v in HORIZONS.items()},
                  "primary": PRIMARY, "panel_start": str(PANEL_START.date()), "min_tvl_usd": MIN_TVL_USD, "min_events": MIN_EVENTS,
                  "stale_days": STALE_DAYS, "min_candidates": MIN_CANDIDATES, "min_dates": MIN_DATES, "young_days": YOUNG_DAYS,
                  "draws": DRAWS, "date_block": DATE_BLOCK, "date_block_sensitivity": DATE_BLOCK_SENSITIVITY, "date_block_long": DATE_BLOCK_LONG, "seed": SEED},
    "regimes": [(n, str(a.date()), str(b.date())) for n, a, b in REGIMES],
    "density": dens.round(6).reset_index().astype({"month": str}).to_dict(orient="records"),
    "panel": {"rows": int(len(panel)), "vaults": int(panel["address"].nunique()), "decisions": int(panel["date"].nunique()),
              "first": str(panel["date"].min().date()), "last": str(panel["date"].max().date()), "young_share": float(panel["young"].mean())},
    "dropped": dropped,
    "by_regime": by_regime.round(6).to_dict(orient="index"),
    "coverage": coverage["finite_share"].round(6).to_dict(),
    "screens": {"all": table_records(full), "all_block45": table_records(full45), "all_block90": table_records(full90),
                **{n: table_records(r) for n, r in by_regime_screens.items()},
                "young": table_records(young), "old": table_records(old)},
    "block_sensitivity": sens.round(6).to_dict(orient="index"),
    "regime_contained_decisions": {k: int(v) for k, v in panel.groupby("regime_contained")["date"].nunique().to_dict().items()},
    "nb38_reference": nb38_ref,
    "oracle": {"rho": float(orow[f"rho_{PRIMARY}"]), "lo_simultaneous": float(orow["lo_primary_simultaneous"]),
               "family_size": oracle_res["family_size"], "critical": oracle_res["critical"]},
}
Path("_build/manifest_39.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_39.json")
'''))

write_notebook(cells, TRACK_DIR / "39-research-trimmed-screen-full-history.ipynb")
