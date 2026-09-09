import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, research_backtest_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR
from blocks_evidence import PARAM_ANCHOR, PARAM_ADDITIONS_EVIDENCE, INDICATOR_ADDITIONS_EVIDENCE

HEADING = """# NB14 - research: decision-aligned screen of the evidence scores

No strategy change. Does ranking by an evidence-weighted score pick better 30-day-forward baskets
than the incumbent composite, with only the information `decide_trades` had at each decision date?
And does it actually reach the hidden cohort NB13 found?

**Based on:** [02-better-format.ipynb](02-better-format.ipynb) / [13-research-age-barrier.ipynb](13-research-age-barrier.ipynb),
full window (2026-01-01 to 2026-09-08). Part of
[14-evidence-weighted-plan.md](14-evidence-weighted-plan.md).

## Method

Copies NB13 section 6's screen (precision-at-6, NB47's method, with NB03b's two corrections:
features read at `when - 1 bar` for live parity per NB57, and only full baskets scored, on the
capacity-filtered pool). Every rule uses the SAME bounded `[0, 1]` score form NB16 will trade -
Draft 1 of this plan screened an unbounded statistic but traded a capped one, two different
rankings; Draft 2 fixed that by construction (`sortino_shrunk_score` is bounded everywhere).

Rules screened, each a `pair_id -> score` map built inside the decision-date loop:

| Rule | Score | Notes |
|---|---|---|
| `incumbent` | `cagr_sortino_weight` | reference row, as NB13 |
| `sortino_shrunk` | `sortino_shrunk_score` | the evidence score alone, no CAGR leg |
| `evidence_composite_0.6` | `evidence_composite`, `cagr_weight=0.6` | the default parameters |
| `evidence_composite_0.3` | `0.3 x expanding_cagr_score + 0.7 x sortino_shrunk_score` | blended inline, no second indicator variant |

**Gate is descriptive, not a hard admission bar.** A score is marked PASS if it beats `incumbent`
on mean forward return in both polling regimes and median Martin in the dense regime. This does
NOT decide which scores get backtested: every score above is run in NB16 regardless, but a score
that fails here is pre-labelled DIAGNOSTIC there and is ineligible for ADOPT from it.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells(
    "14-research-evidence-screen",
    cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_EVIDENCE},
    cell10_extra=INDICATOR_ADDITIONS_EVIDENCE,
)
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Anchor run on the full window, for consistency with the rest of the track.\n"))
cells.append(research_backtest_cell("NB14 anchor, full window"))
cells += integrity_and_audit_cells()

cells.append(md("""# Screen setup

Same pool construction as NB13 section 6: the tradable pool at each decision date (inclusion
criteria met, momentum gate passed, not manually blacklisted), restricted to vaults whose
decision-date TVL could absorb a full 1/6 share of a 98%-deployed $150,000 book (`CAPACITY_TVL`).
"""))

cells.append(code('''import datetime

GATE = float(Parameters.gate_threshold)
#: Live parity: `decide_trades` reads the bar before the decision date (NB57).
ONE_BAR = Parameters.candle_time_bucket.to_timedelta()
FORWARD_DAYS = 30
MIN_FULL_BASKET_DATES = 5
K_MAIN = 6
#: TVL a vault needs before a 1/6 share of a 98%-deployed book fits under the 33% pool cap.
CAPACITY_TVL = (
    Parameters.initial_cash * Parameters.allocation_pct
    / Parameters.max_assets_in_portfolio
    / Parameters.per_position_cap_of_pool_pct
)

candles_close_all = strategy_universe.data_universe.candles.df["close"]
inclusion_series = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)

decision_dates = pd.date_range(
    Parameters.backtest_start + datetime.timedelta(days=60),      # skip the cold-start window
    Parameters.backtest_end - datetime.timedelta(days=FORWARD_DAYS + 1),
    freq="2D",
)
print(f"{len(decision_dates)} decision dates from {decision_dates[0].date()} to {decision_dates[-1].date()}")
print(f"Capacity threshold: a full basket share is ${CAPACITY_TVL:,.0f} of vault TVL")


_series_cache = {}
def indicator_series_for(name, pair):
    key = (name, pair.internal_id)
    if key not in _series_cache:
        _series_cache[key] = indicator_data.get_indicator_series(name, pair=pair, unlimited=True)
    return _series_cache[key]


_close_cache = {}
def close_series(pair_id):
    if pair_id not in _close_cache:
        try:
            _close_cache[pair_id] = candles_close_all.xs(pair_id, level="pair_id").sort_index()
        except KeyError:
            _close_cache[pair_id] = None
    return _close_cache[pair_id]


def forward_metrics(pair_ids, start, horizon=FORWARD_DAYS):
    curves = []
    for pid in pair_ids:
        series = close_series(pid)
        if series is None:
            continue
        window = series.loc[start:start + pd.Timedelta(days=horizon)]
        if len(window) > 5:
            curves.append(window / window.iloc[0])
    if not curves:
        return float("nan"), float("nan")
    basket = pd.concat(curves, axis=1).ffill().mean(axis=1)
    total = float(basket.iloc[-1] - 1.0)
    dd = basket / basket.cummax() - 1.0
    ulcer = float(np.sqrt((dd ** 2).mean()))
    return total, (total / ulcer if ulcer > 0 else float("nan"))
'''))

cells.append(md("""# Run the screen

At each decision date: form the capacity-filtered, gated pool, score it by every rule, take the
top 6, and score the mean/median 30-day-forward outcome of an equal-weight basket of those 6.
`age_days` per vault (from NB13's life-statistics cache) is carried through so the reach columns
- mean top-6 age, and the share younger than the incumbent's 360-day CAGR window - can be reported
directly from the screen, not only from a later backtest.
"""))

cells.append(code('''from pathlib import Path

life_cache_path = Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet")
assert life_cache_path.exists(), (
    "NB13's life-statistics cache is missing - run NB13 section 2 first (it rebuilds the cache "
    "in about a minute) before this screen's reach columns can be computed."
)
life = pd.read_parquet(life_cache_path)
address_by_pair_id = {
    pair.internal_id: str(pair.pool_address).lower()
    for pair in strategy_universe.iterate_pairs()
    if pair.is_vault()
}
inception_by_pair_id = {
    pid: life.loc[addr, "inception"]
    for pid, addr in address_by_pair_id.items() if addr in life.index
}

RULES = ["incumbent", "sortino_shrunk", "evidence_composite_0.6", "evidence_composite_0.3"]

screen_rows = []
for when in decision_dates:
    at = when - ONE_BAR
    regime = "sparse" if when < pd.Timestamp("2026-04-01") else "dense"
    prior = inclusion_series.index[inclusion_series.index <= at]
    pool_ids = list(inclusion_series.loc[prior[-1]]) if len(prior) else []
    pool_ids = [
        pid for pid in pool_ids
        if str(strategy_universe.get_pair_by_id(pid).pool_address).lower() not in MANUAL_BLACKLIST
    ]

    scores = {rule: {} for rule in RULES}
    big_enough = set()
    for pid in pool_ids:
        pair = strategy_universe.get_pair_by_id(pid)
        gate_value = indicator_series_for("return_gate", pair).asof(at)
        if not (gate_value == gate_value and gate_value > GATE):
            continue
        tvl_value = indicator_series_for("tvl", pair).asof(at)
        if tvl_value == tvl_value and float(tvl_value) >= CAPACITY_TVL:
            big_enough.add(pid)

        incumbent_v = indicator_series_for("cagr_sortino_weight", pair).asof(at)
        if incumbent_v == incumbent_v:
            scores["incumbent"][pid] = float(incumbent_v)
        shrunk_v = indicator_series_for("sortino_shrunk_score", pair).asof(at)
        if shrunk_v == shrunk_v:
            scores["sortino_shrunk"][pid] = float(shrunk_v)
        composite_v = indicator_series_for("evidence_composite", pair).asof(at)
        if composite_v == composite_v:
            scores["evidence_composite_0.6"][pid] = float(composite_v)
        cagr_leg = indicator_series_for("expanding_cagr_score", pair).asof(at)
        if cagr_leg == cagr_leg and shrunk_v == shrunk_v:
            scores["evidence_composite_0.3"][pid] = 0.3 * float(cagr_leg) + 0.7 * float(shrunk_v)

    for rule in RULES:
        pool = {pid: v for pid, v in scores[rule].items() if pid in big_enough}
        top = sorted(pool, key=pool.get, reverse=True)[:K_MAIN]
        total, martin = forward_metrics(top, when)
        ages = [
            (at - inception_by_pair_id[pid]).days
            for pid in top if pid in inception_by_pair_id
        ]
        screen_rows.append({
            "date": when, "rule": rule, "regime": regime,
            "scorable_pool": len(pool), "basket_size": len(top), "full_basket": len(top) == K_MAIN,
            "forward_return": total, "forward_martin": martin,
            "mean_top6_age_days": float(np.mean(ages)) if ages else float("nan"),
            "share_top6_younger_360d": float(np.mean([a < 360 for a in ages])) if ages else float("nan"),
        })

screen_raw = pd.DataFrame(screen_rows)
print("Mean capacity-filtered scorable pool size per decision date:")
display(screen_raw.groupby("rule")["scorable_pool"].mean().to_frame("mean_scorable_vaults"))
'''))

cells.append(md("""# Screen result

Scored on full baskets only, so every rule is compared at the same basket size.
"""))

cells.append(code('''full = screen_raw[screen_raw["full_basket"]]
result = full.groupby(["rule", "regime"])[["forward_martin", "forward_return"]].agg(["mean", "median"])
result.columns = [f"{metric}_{stat}" for metric, stat in result.columns]
result = result.unstack()
result.columns = [f"{metric} ({regime})" for metric, regime in result.columns]
counts = full.groupby(["rule", "regime"])["date"].count().unstack()
for regime in ("sparse", "dense"):
    result[f"n_dates ({regime})"] = counts[regime] if regime in counts else 0
result["full_basket_rate"] = screen_raw.groupby("rule")["full_basket"].mean()
result["mean_top6_age_days"] = screen_raw.groupby("rule")["mean_top6_age_days"].mean()
result["share_top6_younger_360d"] = screen_raw.groupby("rule")["share_top6_younger_360d"].mean()
display(result.reindex(RULES))
'''))

cells.append(md("""# Gate verdict

Descriptive only (see the heading): PASS here is a label carried into NB16, not a decision about
which experiments run there.
"""))

cells.append(code('''reference = result.loc["incumbent"]
GATE_PASSED = {}
for rule in RULES:
    if rule == "incumbent":
        continue
    row = result.loc[rule]
    enough = all(row[f"n_dates ({r})"] >= MIN_FULL_BASKET_DATES for r in ("sparse", "dense"))
    beats_return_both = all(
        row[f"forward_return_mean ({r})"] > reference[f"forward_return_mean ({r})"] for r in ("sparse", "dense")
    )
    beats_martin_dense = row["forward_martin_median (dense)"] > reference["forward_martin_median (dense)"]
    GATE_PASSED[rule] = bool(enough and beats_return_both and beats_martin_dense)

gate_df = pd.Series(GATE_PASSED, name="gate_passed").to_frame()
display(gate_df)
print(f"GATE_PASSED = {GATE_PASSED}")
print()
print("Every score above is still backtested in NB16 regardless of this result (descriptive gate).")
print("Sparse regime has far fewer dates than dense (see n_dates columns) - treat any sparse-only")
print("PASS as weaker evidence than a dense-regime PASS.")
'''))

write_notebook(cells, TRACK_DIR / "14-research-evidence-screen.ipynb")
