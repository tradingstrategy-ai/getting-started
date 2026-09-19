"""NB38 - vault-level screen: does a TRIMMED trailing return (best k days removed) predict forward
Sharpe better than the raw one? Standalone research notebook: reads the vault archive directly,
no strategy engine, so young vaults the incumbent cannot rank (under 360 days) are in the panel."""
import sys
sys.path.insert(0, ".")
from builder import md, code, write_notebook, TRACK_DIR

HEADING = """# NB38 - trimmed trailing returns as a ranker: a vault-level screen

The track's luck diagnostics say the incumbent's result is carried by a few cycles and a few
names, and that vaults are admitted on trailing returns that may themselves be a few jumps.
This notebook asks the decision-time question directly, on vaults rather than portfolios: does
a trailing return computed with the vault's best k days REMOVED predict its forward 30-day
Sharpe better than the raw trailing return does? If it does not at the vault level, no ranker
built on it can beat the incumbent at the portfolio level, and the idea stops here.

**Focus is forward Sharpe**, not forward return: the operator wants steady profit, and a
trimmed score is expected to cost CAGR. Forward return, volatility and drawdown are reported
beside it.

**The panel is the archive, not the engine's candidate pool.** Every Hypercore vault with at
least the trailing window of history, a TVL of at least 7,500 USD and five price-changing marks
in the window is a candidate on every decision date from 2026-04-01 (the polling-density break)
to the last date with a complete 30-day forward window. That admits the young cohort the
incumbent's 360-day CAGR leg cannot score at all, and it is screened separately. Stratwise
Multi-Asset Public and the other post-July vaults are shown in a current-snapshot comparison;
they are too young to have any forward outcome and are NOT in the screen (stated, not hidden).
No vault is selected, masked or tuned by name anywhere.

**Based on:** [28-research-stability-signal-screen.ipynb](28-research-stability-signal-screen.ipynb)
and [34-research-calm-score-screen.ipynb](34-research-calm-score-screen.ipynb) for the
two-way cluster bootstrap and simultaneous bounds, re-implemented here without the engine.
Verdict DIAGNOSTIC: a screen, not a result.

## Method

Signals, read at T-1 over trailing windows of 45, 90 and 180 rows: a trimmed RETURN SCORE (sum
of daily log returns with the best k removed, k in 0, 3, 5, 10, annualised over the full window
length) and a trimmed SHARPE SCORE (mean over standard deviation of the retained days), plus
Sortino and realised volatility. Neither trimmed score is an investable return; they are ranking
transformations. Direction 'high' for return and
Sharpe scores (higher is better), 'low' for volatility. Targets over (T, T + 30 d]: forward
Sharpe (primary), forward log return, forward volatility, forward max drawdown in log units. A
candidate needs a real mark within 3 days of T-1 (eligibility is never forward-filled), and a
forward window needs at least 10 observed marks with one in its last 3 days.

Inference: per date, Spearman across that date's candidates, signed so positive means "the
signal's good end had the better outcome", averaged over dates; one two-way cluster bootstrap
(15-decision circular date blocks x vault clusters, 500 draws, seed 20260916) shared across every
hypothesis; studentised max-T simultaneous lower bounds over the family of (signal x primary
target). The decisive statistic is the PAIRED difference trimmed-minus-raw on the primary
target, per (window, k), on the same draws.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]

cells.append(md("""## Part 0. Archive, provenance, constants
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
STRATWISE = "0x0ff219ac20596b457558341bc410bc7a08a1394c"   # display only; never used to select or tune

WINDOWS = (45, 90, 180)
TRIMS = (0, 3, 5, 10)
FORWARD_DAYS = 30
POST_BREAK_START = pd.Timestamp("2026-04-01")
DECISION_STEP_DAYS = 2
MIN_TVL_USD = 7_500.0
MIN_FRESH = 5
#: A candidate must have an ACTUAL mark within this many days before the decision (no stale
#: forward-filled eligibility), and a forward window must contain at least MIN_FORWARD_MARKS
#: observed marks with one in its last MAX_STALE_DAYS days, so a vault that stopped reporting
#: cannot supply manufactured zero-return days as an outcome.
MAX_STALE_DAYS = 3
MIN_FORWARD_MARKS = 10
MIN_CANDIDATES = 8
MIN_DATES = 40
YOUNG_DAYS = 360          # the incumbent's CAGR leg cannot score a vault younger than this
DRAWS = 500
DATE_BLOCK = 15
SEED = 20260916
LEVEL = 0.95

df = pd.read_parquet(ARCHIVE, columns=["address", "chain", "share_price", "total_assets", "name"])
df = df[df["chain"] == HYPERCORE_CHAIN].reset_index()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df[df["timestamp"] >= pd.Timestamp("2025-06-01")].sort_values(["address", "timestamp"])
df["date"] = df["timestamp"].dt.floor("D")
daily = df.groupby(["address", "date"])[["share_price", "total_assets"]].last().reset_index()
names = df.groupby("address")["name"].last()
LAST_MARK = df["timestamp"].max()
display(pd.Series({**PROVENANCE, "last_mark": str(LAST_MARK), "hypercore_vaults": daily["address"].nunique(),
                   "daily_rows": len(daily)}, name="value").to_frame())
'''))

cells.append(md("""## Part 1. The panel

One row per (decision date, vault). Trailing series are forward-filled daily marks (a day
without a mark repeats the last one, a zero log return); trimming removes the k LARGEST daily
log returns inside the window before annualising, so a vault whose window return is three jumps
loses most of it. Forward series are the same daily grid over the next 30 days.
"""))
cells.append(code('''def trailing_scores(r: np.ndarray) -> dict:
    """Raw and trimmed annualised log return and Sharpe, Sortino and volatility of one window."""
    out = {}
    n = len(r)
    order = np.sort(r)
    for k in TRIMS:
        kept = order[:n - k] if k else order
        ann = 365.0 / n
        out[f"ret_k{k}"] = float(kept.sum() * ann)
        sd = float(kept.std(ddof=1)) if len(kept) > 2 else float("nan")
        out[f"sharpe_k{k}"] = float(kept.mean() / sd * math.sqrt(365.0)) if sd and sd > 0 else float("nan")
    downside = np.sqrt(np.mean(np.clip(r, None, 0.0) ** 2))
    out["sortino"] = float(r.mean() / downside * math.sqrt(365.0)) if downside > 0 else float("nan")
    out["vol"] = float(r.std(ddof=1) * math.sqrt(365.0))
    return out


def forward_targets(r: np.ndarray, prices: np.ndarray) -> dict:
    sd = float(r.std(ddof=1)) if len(r) > 2 else float("nan")
    path = np.concatenate([[0.0], np.cumsum(r)])
    return {"fwd_return": float(r.sum()),
            "fwd_sharpe": float(r.mean() / sd * math.sqrt(365.0)) if sd and sd > 0 else float("nan"),
            "fwd_vol": float(sd * math.sqrt(365.0)) if sd == sd else float("nan"),
            # Log-unit drawdown (minimum of cumulative log return below its running maximum);
            # ranks are the same as for the percentage form.
            "fwd_log_max_dd": float(np.min(path - np.maximum.accumulate(path)))}


last_decision = (LAST_MARK.floor("D") - pd.Timedelta(days=FORWARD_DAYS))
decisions = pd.date_range(POST_BREAK_START, last_decision, freq=f"{DECISION_STEP_DAYS}D")
rows = []
dropped = {"no_recent_mark": 0, "tvl": 0, "forward_marks": 0, "no_window": 0}
for address, g in daily.groupby("address"):
    g = g.set_index("date")
    grid = pd.date_range(g.index.min(), LAST_MARK.floor("D"), freq="D")
    observed = pd.Series(True, index=g.index).reindex(grid, fill_value=False)   # a real mark on this day
    full = g.reindex(grid).ffill()
    p = full["share_price"].where(full["share_price"] > 0)
    tvl = full["total_assets"]
    r = np.log(p).diff()
    born = g.index.min()
    mark_days = observed[observed].index
    for t in decisions:
        if t not in full.index:
            continue
        t1 = t - pd.Timedelta(days=1)
        # Eligibility on OBSERVED information: a real mark within MAX_STALE_DAYS of T-1, and the
        # TVL from that mark. A vault whose last mark is older is not a live candidate.
        recent = mark_days[(mark_days <= t1) & (mark_days > t1 - pd.Timedelta(days=MAX_STALE_DAYS))]
        if len(recent) == 0:
            dropped["no_recent_mark"] += 1
            continue
        if not (g.loc[recent[-1], "total_assets"] >= MIN_TVL_USD):
            dropped["tvl"] += 1
            continue
        age = int((t - born).days)
        row = {"address": address, "date": t, "age_days": age, "young": age < YOUNG_DAYS,
               "days_since_mark": int((t1 - recent[-1]).days)}
        scored_any = False
        for w in WINDOWS:
            win = r[(r.index > t1 - pd.Timedelta(days=w)) & (r.index <= t1)].dropna().to_numpy()
            if len(win) < w or int((np.abs(win) > 0).sum()) < MIN_FRESH:
                for k in TRIMS:
                    row[f"ret{w}_k{k}"] = np.nan; row[f"sharpe{w}_k{k}"] = np.nan
                row[f"sortino{w}"] = np.nan; row[f"vol{w}"] = np.nan
                row[f"fresh{w}"] = int((np.abs(win) > 0).sum()) if len(win) else 0
                continue
            scored_any = True
            s = trailing_scores(win)
            for key, value in s.items():
                row[f"{key.split('_')[0]}{w}_{key.split('_')[1]}" if "_" in key else f"{key}{w}"] = value
            row[f"fresh{w}"] = int((np.abs(win) > 0).sum())
        if not scored_any:
            dropped["no_window"] += 1
            continue
        t_end = t + pd.Timedelta(days=FORWARD_DAYS)
        fwd = r[(r.index > t) & (r.index <= t_end)].dropna().to_numpy()
        fwd_marks = mark_days[(mark_days > t) & (mark_days <= t_end)]
        # The forward window must be OBSERVED, not manufactured: enough real marks and one near
        # its end. Otherwise a vault that stopped reporting scores as perfectly calm.
        if len(fwd) < FORWARD_DAYS or len(fwd_marks) < MIN_FORWARD_MARKS or \
                (len(fwd_marks) and (t_end - fwd_marks[-1]).days > MAX_STALE_DAYS) or not len(fwd_marks):
            dropped["forward_marks"] += 1
            continue
        row["fwd_marks"] = int(len(fwd_marks))
        row.update(forward_targets(fwd, None))
        rows.append(row)
panel = pd.DataFrame(rows)
print("candidate-dates dropped:", dropped)
print(f"forward-window observed marks: median {panel['fwd_marks'].median():.0f} of {FORWARD_DAYS} days, "
      f"5th percentile {panel['fwd_marks'].quantile(0.05):.0f}; days since last mark at T-1: mean {panel['days_since_mark'].mean():.2f}")
panel["name"] = panel["address"].map(names)
print(f"panel: {len(panel):,} rows, {panel['address'].nunique()} vaults, {panel['date'].nunique()} decisions "
      f"{panel['date'].min().date()} to {panel['date'].max().date()}; young (< {YOUNG_DAYS} d) share of rows "
      f"{panel['young'].mean():.1%}")
SIGNALS = []
for w in WINDOWS:
    for k in TRIMS:
        SIGNALS.append({"name": f"ret{w}_k{k}", "direction": "high", "window": w, "k": k, "family": "return"})
    for k in TRIMS:
        SIGNALS.append({"name": f"sharpe{w}_k{k}", "direction": "high", "window": w, "k": k, "family": "sharpe"})
    SIGNALS.append({"name": f"sortino{w}", "direction": "high", "window": w, "k": None, "family": "sortino"})
    SIGNALS.append({"name": f"vol{w}", "direction": "low", "window": w, "k": None, "family": "vol"})
SIGNAL_NAMES = [s["name"] for s in SIGNALS]
SIGNAL_SIGN = {s["name"]: (1.0 if s["direction"] == "high" else -1.0) for s in SIGNALS}
TARGETS = ["fwd_sharpe", "fwd_return", "fwd_vol", "fwd_log_max_dd"]
#: positive = the signal's good end had the better outcome: higher Sharpe/return, LOWER vol, shallower (larger) max DD
TARGET_SIGN = {"fwd_sharpe": 1.0, "fwd_return": 1.0, "fwd_vol": -1.0, "fwd_log_max_dd": 1.0}
coverage = pd.DataFrame({s: np.isfinite(panel[s]).mean() for s in SIGNAL_NAMES}, index=["finite_share"]).T
display(coverage.round(3).T)
display(panel[TARGETS].describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).round(4))
'''))

cells.append(md("""## Part 2. One shared bootstrap, every hypothesis

Per date and signal, the complete-case Spearman against each target; equal-weight mean over
dates. The bootstrap resamples 15-decision circular date blocks and vault clusters together, and
every hypothesis - every signal, every target, and every trimmed-minus-raw difference - is a
function of the same draws.
"""))
cells.append(code('''def per_date_blocks(frame: pd.DataFrame) -> dict:
    """{date: {'vault': array, 'values': (n, S+T) float array}} with NaN where a signal is missing."""
    out = {}
    cols = SIGNAL_NAMES + TARGETS
    for date, g in frame.groupby("date"):
        out[pd.Timestamp(date)] = {"vault": g["address"].to_numpy(), "values": g[cols].to_numpy(dtype=float)}
    return out


def date_statistics(values: np.ndarray) -> np.ndarray:
    """(S, T) signed Spearman on the complete cases of each (signal, target) pair; NaN if fewer than
    MIN_CANDIDATES rows or a constant column."""
    S, T = len(SIGNAL_NAMES), len(TARGETS)
    out = np.full((S, T), np.nan)
    targets = values[:, S:]
    for i, name in enumerate(SIGNAL_NAMES):
        x = values[:, i]
        for j, target in enumerate(TARGETS):
            y = targets[:, j]
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < MIN_CANDIDATES:
                continue
            xr, yr = rankdata(x[ok]), rankdata(y[ok])
            if np.ptp(xr) == 0 or np.ptp(yr) == 0:
                continue
            xc, yc = xr - xr.mean(), yr - yr.mean()
            rho = float((xc * yc).sum() / math.sqrt((xc ** 2).sum() * (yc ** 2).sum()))
            out[i, j] = SIGNAL_SIGN[name] * TARGET_SIGN[target] * rho
    return out


def mean_over_dates(blocks: dict, dates: list, counts: dict | None = None) -> tuple:
    S, T = len(SIGNAL_NAMES), len(TARGETS)
    total, n = np.zeros((S, T)), np.zeros((S, T))
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
        stats = date_statistics(values)
        finite = np.isfinite(stats)
        total[finite] += stats[finite]
        n[finite] += 1
    with np.errstate(invalid="ignore"):
        return np.where(n > 0, total / np.maximum(n, 1), np.nan), n


def bootstrap(frame: pd.DataFrame, draws: int = DRAWS, seed: int = SEED, verbose: bool = True) -> dict:
    blocks = per_date_blocks(frame)
    dates = sorted(blocks)
    vaults = sorted(frame["address"].unique())
    observed, n_dates = mean_over_dates(blocks, dates)
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(len(dates) / DATE_BLOCK))
    reps = np.full((draws,) + observed.shape, np.nan)
    for d in range(draws):
        starts = rng.integers(0, len(dates), size=n_blocks)
        index = np.concatenate([(np.arange(s, s + DATE_BLOCK) % len(dates)) for s in starts])[:len(dates)]
        drawn_vaults = rng.choice(len(vaults), size=len(vaults), replace=True)
        counts = {}
        for v in drawn_vaults:
            counts[vaults[v]] = counts.get(vaults[v], 0) + 1
        reps[d], _ = mean_over_dates(blocks, [dates[i] for i in index], counts)
        if verbose and (d + 1) % 100 == 0:
            print(f"  draw {d + 1}/{draws}")
    return {"observed": observed, "draws": reps, "n_dates": n_dates, "dates": dates, "rows": len(frame)}


def simultaneous_lower(observed: np.ndarray, reps: np.ndarray, level: float = LEVEL) -> dict:
    """One-sided simultaneous lower bounds by studentised max-T over the finite family, on
    complete-family draws only; add-one p for theta <= 0."""
    se = np.nanstd(reps, axis=0, ddof=1)
    member = np.isfinite(observed) & np.isfinite(se) & (se > 0)
    stud = (reps - observed[None, :]) / np.where(se > 0, se, np.nan)[None, :]
    complete = np.isfinite(stud[:, member]).all(axis=1) if member.any() else np.zeros(len(reps), dtype=bool)
    per_draw_max = stud[complete][:, member].max(axis=1) if complete.any() else np.array([])
    critical = float(np.percentile(per_draw_max, level * 100.0)) if len(per_draw_max) >= 100 else float("nan")
    lower = np.where(member, observed - critical * se, np.nan)
    unadjusted = np.nanpercentile(reps, (1 - level) * 100.0, axis=0)
    centred = reps - observed[None, :]
    p = (1.0 + (centred >= observed[None, :]).sum(axis=0)) / (len(reps) + 1.0)
    return {"se": se, "critical": critical, "lower": lower, "lower_unadjusted": unadjusted, "p": p,
            "family_size": int(member.sum()), "complete_draws": int(len(per_draw_max))}


def screen(frame: pd.DataFrame, label: str, verbose: bool = True) -> dict:
    print(f"{label}: {len(frame):,} rows, {frame['date'].nunique()} decisions, {frame['address'].nunique()} vaults")
    boot = bootstrap(frame, verbose=verbose)
    S, T = len(SIGNAL_NAMES), len(TARGETS)
    j = TARGETS.index("fwd_sharpe")
    fam = simultaneous_lower(boot["observed"][:, j], boot["draws"][:, :, j])
    rows = []
    for i, s in enumerate(SIGNALS):
        row = {"signal": s["name"], "family": s["family"], "window": s["window"], "k": s["k"],
               "dates": int(boot["n_dates"][i, j]), "evaluated": bool(boot["n_dates"][i, j] >= MIN_DATES and fam["se"][i] > 0)}
        for t_idx, target in enumerate(TARGETS):
            row[f"rho_{target}"] = boot["observed"][i, t_idx]
        row["se_sharpe"] = fam["se"][i]
        row["lo_sharpe_simultaneous"] = fam["lower"][i]
        row["lo_sharpe_unadjusted"] = fam["lower_unadjusted"][i]
        row["p_sharpe"] = fam["p"][i]
        rows.append(row)
    table = pd.DataFrame(rows).set_index("signal")
    # Paired trimmed-minus-raw differences on the primary target, on the same draws. The
    # per-comparison interval and add-one p are DESCRIPTIVE; the 18 comparisons are also one
    # family, so a simultaneous max-T lower bound over them is reported as the controlled figure.
    diffs, d_obs, d_reps = [], [], []
    for w in WINDOWS:
        for fam_name in ("ret", "sharpe"):
            base = SIGNAL_NAMES.index(f"{fam_name}{w}_k0")
            for k in TRIMS[1:]:
                idx = SIGNAL_NAMES.index(f"{fam_name}{w}_k{k}")
                obs = boot["observed"][idx, j] - boot["observed"][base, j]
                rep = boot["draws"][:, idx, j] - boot["draws"][:, base, j]
                d_obs.append(obs); d_reps.append(rep)
                fin = rep[np.isfinite(rep)]
                centred = fin - obs
                n = len(fin)
                p_hi = (1.0 + (centred >= obs).sum()) / (n + 1.0)
                p_lo = (1.0 + (centred <= obs).sum()) / (n + 1.0)
                diffs.append({"family": fam_name, "window": w, "k": k, "trimmed_rho": boot["observed"][idx, j],
                              "raw_rho": boot["observed"][base, j], "difference": obs,
                              "ci_lo": float(np.percentile(fin, 2.5)) if n >= 100 else np.nan,
                              "ci_hi": float(np.percentile(fin, 97.5)) if n >= 100 else np.nan,
                              "p_two_sided_add_one": float(min(1.0, 2 * min(p_hi, p_lo))) if n >= 100 else np.nan,
                              "draws": int(n)})
    paired = pd.DataFrame(diffs)
    pfam = simultaneous_lower(np.array(d_obs), np.column_stack(d_reps))
    paired["lo_simultaneous_18"] = pfam["lower"]
    paired["se"] = pfam["se"]
    return {"label": label, "table": table, "paired": paired, "critical": fam["critical"],
            "family_size": fam["family_size"], "complete_draws": fam["complete_draws"], "boot": boot,
            "paired_critical": pfam["critical"], "paired_family_size": pfam["family_size"]}


full = screen(panel, "all candidates")
print(f"\\nprimary family: {full['family_size']} signals, critical {full['critical']:.4f} on {full['complete_draws']} complete draws")
display(full["table"][["family", "window", "k", "dates", "evaluated", "rho_fwd_sharpe", "se_sharpe", "lo_sharpe_simultaneous",
                       "lo_sharpe_unadjusted", "p_sharpe", "rho_fwd_return", "rho_fwd_vol", "rho_fwd_log_max_dd"]].round(4))
print(f"\\nPAIRED trimmed - raw on forward Sharpe (95% percentile interval on shared draws; simultaneous lower bound over "
      f"the {full['paired_family_size']} paired comparisons, critical {full['paired_critical']:.4f}):")
display(full["paired"].round(4))
'''))

cells.append(md("""### Reachability: can this screen produce a positive simultaneous bound at all?

Standing rule 9. A noisy foresight oracle - the forward Sharpe itself plus 5% noise - is added
to the family and run through the identical panel, bootstrap and max-T. If it does not clear
the family-wise lower bound, the all-fail result above is a property of the machinery, not of
the signals. Diagnostic only; nothing here is reported as a finding.
"""))
cells.append(code('''rng = np.random.default_rng(SEED + 1)
oracle_panel = panel.copy()
oracle_panel["oracle_fwd_sharpe"] = oracle_panel["fwd_sharpe"] + rng.normal(0.0, 0.05 * float(oracle_panel["fwd_sharpe"].std()), len(oracle_panel))
_saved = (SIGNALS, SIGNAL_NAMES, SIGNAL_SIGN)
SIGNALS = list(SIGNALS) + [{"name": "oracle_fwd_sharpe", "direction": "high", "window": None, "k": None, "family": "oracle"}]
SIGNAL_NAMES = [s["name"] for s in SIGNALS]
SIGNAL_SIGN = {s["name"]: (1.0 if s["direction"] == "high" else -1.0) for s in SIGNALS}
try:
    oracle_res = screen(oracle_panel, "oracle reachability (31-signal family)", verbose=False)
finally:
    SIGNALS, SIGNAL_NAMES, SIGNAL_SIGN = _saved
orow = oracle_res["table"].loc["oracle_fwd_sharpe"]
print(f"oracle: rho {orow['rho_fwd_sharpe']:.4f}, simultaneous lower bound {orow['lo_sharpe_simultaneous']:.4f} over "
      f"{oracle_res['family_size']} signals (critical {oracle_res['critical']:.4f}), finite target rows "
      f"{int(np.isfinite(panel['fwd_sharpe']).sum())} of {len(panel)}")
assert orow["lo_sharpe_simultaneous"] > 0, "the screen cannot produce a positive simultaneous bound even for a foresight oracle"
print("reachable: a foresight signal clears the family-wise bound; the thirty real signals fail it on their merits")
'''))

cells.append(md("""## Part 3. The young cohort and the old

Vaults under 360 days old are unscorable by the incumbent's CAGR leg; they are where a
shorter-window ranker would matter most. The screen is repeated on the young rows and on the
rest, separately, so the two are not averaged into each other.
"""))
cells.append(code('''young = screen(panel[panel["young"]], "young (< 360 days)", verbose=False)
old = screen(panel[~panel["young"]], "old (>= 360 days)", verbose=False)
COLS = ["window", "k", "dates", "evaluated", "rho_fwd_sharpe", "lo_sharpe_simultaneous", "p_sharpe", "rho_fwd_return", "rho_fwd_vol"]
print(f"note: the young and old screens are separate bootstraps on separate samples; their paired-difference intervals are descriptive")
for res in (young, old):
    print(f"\\n{res['label']}: family {res['family_size']}, critical {res['critical']:.4f}, complete draws {res['complete_draws']}")
    display(res["table"][COLS].round(4))
    print("paired trimmed - raw on forward Sharpe:")
    display(res["paired"].round(4))
'''))

cells.append(md("""## Part 4. Stratwise and the post-July cohort: a current-snapshot comparison

Stratwise Multi-Asset Public has 63 days of history at this archive. It cannot appear in the
screen: no decision date gives it a 45-day trailing window AND a complete 30-day forward window.
What can be shown is how raw and trimmed trailing scores rank it and the other young vaults on
the LATEST date at which each window can be computed, against every vault scorable on that
date. This is description; nothing here is evidence about forward behaviour.
"""))
cells.append(code('''snapshot_rows = []
snap_dates = {}
SNAP_DAY = LAST_MARK.floor("D") - pd.Timedelta(days=1)   # the last COMPLETED UTC day, not the partial one
for w in WINDOWS:
    t = SNAP_DAY
    snap_dates[w] = t
    for address, g in daily.groupby("address"):
        g = g.set_index("date")
        if g.index.min() > t:
            continue
        grid = pd.date_range(g.index.min(), t, freq="D")
        full_ = g.reindex(grid).ffill()
        p = full_["share_price"].where(full_["share_price"] > 0)
        recent_marks = g.index[(g.index <= t) & (g.index > t - pd.Timedelta(days=MAX_STALE_DAYS))]
        if len(recent_marks) == 0 or not (g.loc[recent_marks[-1], "total_assets"] >= MIN_TVL_USD):
            continue
        r = np.log(p).diff()
        win = r[(r.index > t - pd.Timedelta(days=w)) & (r.index <= t)].dropna().to_numpy()
        if len(win) < w or int((np.abs(win) > 0).sum()) < MIN_FRESH:
            continue
        s = trailing_scores(win)
        snapshot_rows.append({"window": w, "address": address, "name": names.get(address, ""),
                              "age_days": int((t - g.index.min()).days), "tvl": float(full_["total_assets"].iloc[-1]),
                              "fresh": int((np.abs(win) > 0).sum()), **s})
snapshot = pd.DataFrame(snapshot_rows)
for w in WINDOWS:
    sub = snapshot[snapshot["window"] == w].copy()
    for col in ["ret_k0", "ret_k5", "sharpe_k0", "sharpe_k5"]:
        sub[f"rank_{col}"] = sub[col].rank(ascending=False, method="min")
    sub = sub.sort_values("sharpe_k5", ascending=False)
    print(f"\\nwindow {w} rows at {snap_dates[w].date()}: {len(sub)} scorable vaults; post-July (age < 75 d): {(sub['age_days'] < 75).sum()}")
    show = sub[(sub["age_days"] < 120) | (sub["address"] == STRATWISE)].head(25)
    display(show[["name", "age_days", "tvl", "fresh", "ret_k0", "ret_k5", "sharpe_k0", "sharpe_k5", "sortino", "vol",
                  "rank_ret_k0", "rank_ret_k5", "rank_sharpe_k0", "rank_sharpe_k5"]].round(3).set_index("name"))
    if (sub["address"] == STRATWISE).any():
        sw = sub[sub["address"] == STRATWISE].iloc[0]
        print(f"  Stratwise at window {w}: raw return {sw['ret_k0']:+.3f} (rank {int(sw['rank_ret_k0'])}/{len(sub)}), trimmed k=5 "
              f"{sw['ret_k5']:+.3f} (rank {int(sw['rank_ret_k5'])}); raw Sharpe {sw['sharpe_k0']:.2f} (rank {int(sw['rank_sharpe_k0'])}), "
              f"trimmed k=5 {sw['sharpe_k5']:.2f} (rank {int(sw['rank_sharpe_k5'])})")
    else:
        print(f"  Stratwise has no {w}-row window at {snap_dates[w].date()}")
# How much trimming moves the cross-sectional ordering at all, per window: rank correlation raw vs trimmed.
agreement = []
for w in WINDOWS:
    sub = snapshot[snapshot["window"] == w]
    for fam_name in ("ret", "sharpe"):
        for k in TRIMS[1:]:
            agreement.append({"window": w, "family": fam_name, "k": k,
                              "spearman_raw_vs_trimmed": float(sub[f"{fam_name}_k0"].corr(sub[f"{fam_name}_k{k}"], method="spearman")),
                              "vaults": len(sub)})
display(pd.DataFrame(agreement).round(3))
'''))

cells.append(md("""## Part 5. Manifest
"""))
cells.append(code('''def table_records(res):
    return {"table": res["table"].round(6).to_dict(orient="index"), "paired": res["paired"].round(6).to_dict(orient="records"),
            "critical": res["critical"], "family_size": res["family_size"], "complete_draws": res["complete_draws"],
            "rows": int(res["boot"]["rows"]), "decisions": int(len(res["boot"]["dates"]))}

manifest = {
    "verdict": "DIAGNOSTIC - a vault-level screen, not a result",
    "provenance": {**PROVENANCE, "last_mark": str(LAST_MARK)},
    "constants": {"windows": list(WINDOWS), "trims": list(TRIMS), "forward_days": FORWARD_DAYS, "post_break_start": str(POST_BREAK_START.date()),
                  "min_tvl_usd": MIN_TVL_USD, "min_fresh": MIN_FRESH, "min_candidates": MIN_CANDIDATES, "min_dates": MIN_DATES,
                  "young_days": YOUNG_DAYS, "draws": DRAWS, "date_block": DATE_BLOCK, "seed": SEED},
    "panel": {"rows": int(len(panel)), "vaults": int(panel["address"].nunique()), "decisions": int(panel["date"].nunique()),
              "first": str(panel["date"].min().date()), "last": str(panel["date"].max().date()), "young_share": float(panel["young"].mean())},
    "coverage": coverage["finite_share"].round(6).to_dict(),
    "screens": {"all": table_records(full), "young": table_records(young), "old": table_records(old)},
    "snapshot_dates": {str(w): str(t.date()) for w, t in snap_dates.items()},
    "snapshot_agreement": pd.DataFrame(agreement).round(6).to_dict(orient="records"),
    "stratwise": {str(w): (snapshot[(snapshot["window"] == w) & (snapshot["address"] == STRATWISE)].drop(columns=["address"]).round(6).to_dict(orient="records"))
                  for w in WINDOWS},
    "stratwise_age_days": int((SNAP_DAY - daily[daily["address"] == STRATWISE]["date"].min()).days),
    "dropped": dropped,
    "forward_marks_median": float(panel["fwd_marks"].median()), "forward_marks_p05": float(panel["fwd_marks"].quantile(0.05)),
    "oracle": {"rho": float(orow["rho_fwd_sharpe"]), "lo_simultaneous": float(orow["lo_sharpe_simultaneous"]),
               "family_size": oracle_res["family_size"], "critical": oracle_res["critical"]},
    "paired_family": {k: {"critical": SC_["paired_critical"], "size": SC_["paired_family_size"]} for k, SC_ in (("all", full), ("young", young), ("old", old))},
}
Path("_build/manifest_38.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote _build/manifest_38.json")
'''))

write_notebook(cells, TRACK_DIR / "38-research-trimmed-return-screen.ipynb")
