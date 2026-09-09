import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, research_backtest_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB13 - research: the age barrier, and the vaults it hides

No strategy change. This notebook answers a question the track has not asked: **are there
high-Sharpe Hyperliquid vaults the strategy never even considers, because of an inclusion rule
rather than because it ranked them badly?** - with particular attention to vaults launched after
2026-04-01, which is also when NB57's polling regime turns dense.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), full window (2026-01-01 to
2026-09-08). Descriptive only; no parameter is changed and nothing here is adopted.

## Why this is worth checking

The strategy has **no explicit age rule**. But `cagr_lookback_days = 360` means the CAGR leg of the
selection composite is NaN until a vault has 360 days of price history, and an unscored vault
enters the ranking at signal `0.0`, so it is sorted below every scored vault and never reaches a
basket slot. Two further windows do the same thing further down the pipeline:
`inverse_vol_window = 90` (a vault with no `inverse_vol` gets weight 0 under `inverse_variance`
sizing) and `sharpe_lookback_days = 45` (the Sortino leg).

None of these was chosen as an eligibility policy. They are lookback windows whose side effect is
an age filter, and this notebook measures how much of the universe that side effect removes and
what is behind it.

## What this notebook does

1. **Universe census.** Re-runs the curator's own filter chain over the vault metadata snapshot to
   separate what the curator excludes (deposit-closed, peak TVL, denylist, sub-vault) from what the
   strategy's lookback windows exclude later.
2. **Age barriers, measured.** For every vault in the trading universe, the first date each
   selection input becomes non-NaN, against the vault's true inception from the raw poll archive.
3. **Who is behind the barrier.** Realised Sharpe, Sortino, CAGR, drawdown, staleness and TVL for
   the vaults the composite can never score, at tradable size.
4. **NB78 signature check.** NB78 found the strategy's worst losers share a high-Sharpe signature
   built from an absence of down days. Applied to the young cohort, since a short history is the
   easiest way to have no down days yet.
5. **Decision-aligned screen.** NB47's precision-at-6, at live parity (NB57), comparing the
   incumbent composite against the same composite with the CAGR leg shortened to 90 days - the
   minimal change that would let the hidden cohort be ranked at all.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("13-research-age-barrier")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Anchor run on the full window, so the pool and the indicators match the rest of the track.\n"))
cells.append(research_backtest_cell("NB13 anchor, full window"))
cells += integrity_and_audit_cells()

# --- 1. universe census --------------------------------------------------------------------
cells.append(md("""# 1. Universe census: what the curator removes before the strategy sees anything

`build_hyperliquid_vault_universe(min_tvl=7_500, min_age=0.0, top_n=9999)` is already permissive on
age - `min_age` is zero and `top_n` is oversized - so nothing is dropped here for being young. This
re-runs the curator's own `parse_vault()` / `filter_vault()` over the same metadata snapshot to get
the exclusion reasons, so that section 3's age barrier is not confused with a curator rule.
"""))

cells.append(code('''import json
from pathlib import Path

from tradeexecutor.curator.curator import EXCLUDED_PROTOCOLS, EXCLUDED_VAULTS, MUST_INCLUDE
from tradeexecutor.curator.hyperliquid_vault_universe import (
    ALLOWED_DENOMINATIONS, CHAIN_CONFIG, EXCLUDED_FLAGS, EXCLUDED_RISKS,
    REQUIRE_KNOWN_PROTOCOL, TRACKED_PERIODS,
)
from tradeexecutor.curator.vault_universe_creation import filter_vault, parse_vault

#: The snapshot the universe above was curated from. Read from the cache rather than re-fetched,
#: so this census describes exactly the universe this notebook is trading.
metadata_path = Path("~/.cache/tradingstrategy/vaults/downloads/vault-metadata.json").expanduser()
raw_vaults = json.loads(metadata_path.read_bytes())["vaults"]

census_rows = []
for rv in raw_vaults:
    v = parse_vault(rv, CHAIN_CONFIG, TRACKED_PERIODS)
    if v is None:
        continue                       # not a Hypercore vault
    if not v.must_include and v.deposit_closed_reason is not None:
        passes, reason = False, "deposit_closed"
    else:
        passes, reason = filter_vault(
            v, Parameters.min_tvl_usd, 0.0, CHAIN_CONFIG,
            allowed_denominations=ALLOWED_DENOMINATIONS,
            excluded_risks=EXCLUDED_RISKS,
            excluded_flags=EXCLUDED_FLAGS,
            require_known_protocol=REQUIRE_KNOWN_PROTOCOL,
            hypercore_min_tvl=Parameters.min_tvl_usd,
            skip_cagr_filter=True,
            use_peak_tvl=True,
        )
    # `build_hyperliquid_vault_universe()` lets `filter_vault()` pass denylisted vaults and drops
    # them in its own result loop, so fold that step in to get real universe membership.
    if passes and (v.excluded or v.excluded_protocol_reason is not None):
        passes, reason = False, "denylist"
    census_rows.append({
        "address": v.address,
        "name": v.name,
        "denomination": v.denomination,
        "metadata_age_years": v.age_years,
        "tvl": v.tvl,
        "peak_tvl": v.peak_tvl,
        "protocol_slug": v.protocol_slug,
        "curator_admits": passes,
        "curator_reason": reason.split("=")[0],
    })

census = pd.DataFrame(census_rows).set_index("address")
print(f"Hypercore vaults in the metadata snapshot: {len(census)}")
print(f"Admitted by the curator: {int(census['curator_admits'].sum())}")
reason_table = (
    census.loc[~census["curator_admits"], "curator_reason"]
    .value_counts().rename("vaults").to_frame()
)
reason_table["share_of_excluded"] = reason_table["vaults"] / reason_table["vaults"].sum()
display(reason_table)
'''))

# --- 2. inception + realised metrics ------------------------------------------------------
cells.append(md("""# 2. True inception and realised performance, from the raw poll archive

Vault age is taken from the raw Hyperliquid poll archive rather than the metadata `years` field, so
inception is the first share price actually recorded. Realised statistics are computed on daily
last-poll marks over each vault's own life, ending at the backtest end date.

These are **hindsight** statistics over a vault's whole life - the right measure for "is there
anything good behind the barrier", and the wrong measure for "would we have picked it", which is
what section 6 tests instead.
"""))

cells.append(code('''raw_price_path = Path("~/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet").expanduser()
life_cache_path = Path("/tmp/hyperliquid-lower-vol-vault-life-stats.parquet")

if life_cache_path.exists():
    life = pd.read_parquet(life_cache_path)
else:
    polls = pd.read_parquet(
        raw_price_path,
        columns=["chain", "address", "share_price", "total_assets"],
        filters=[("chain", "==", ChainId.hypercore.value)],
    )
    polls["address"] = polls["address"].astype(str).str.lower()
    polls = polls[polls.index < Parameters.backtest_end]

    life_rows = []
    for address, group in polls.groupby("address", sort=False):
        prices = group["share_price"].astype(float).dropna()
        prices = prices[prices > 0]
        daily = prices.resample("1D").last().dropna()
        if len(daily) < 5:
            continue
        r = daily.pct_change().dropna()
        if len(r) < 5:
            continue
        fresh = r[r != 0.0]              # NB57: a zero daily return is a stale mark, not a flat day
        days = (daily.index[-1] - daily.index[0]).days
        total_return = float(daily.iloc[-1] / daily.iloc[0] - 1.0)
        downside = float(np.sqrt((r.clip(upper=0.0) ** 2).mean()))
        assets = group["total_assets"].astype(float).dropna()
        life_rows.append({
            "address": address,
            "inception": daily.index[0],
            "age_days": days,
            "observed_days": len(daily),
            "fresh_days": len(fresh),
            "stale_share": 1.0 - len(fresh) / len(r),
            "down_day_share": float((r < 0).mean()),
            "life_cagr": (1.0 + total_return) ** (365.0 / max(days, 1)) - 1.0 if total_return > -1 else -1.0,
            "life_sharpe": float(r.mean() / r.std() * np.sqrt(365)) if r.std() > 0 else float("nan"),
            "life_sortino": float(r.mean() / downside * np.sqrt(365)) if downside > 0 else float("nan"),
            "life_max_dd": float((daily / daily.cummax() - 1.0).min()),
            "last_tvl": float(assets.iloc[-1]) if len(assets) else float("nan"),
        })
    life = pd.DataFrame(life_rows).set_index("address")
    life.to_parquet(life_cache_path)

print(f"Vaults with a usable price history: {len(life)}")

#: Restrict to what the strategy can actually trade: the pairs in the built universe.
universe_addresses = {
    str(pair.pool_address).lower(): pair.internal_id
    for pair in strategy_universe.iterate_pairs()
    if pair.is_vault()
}
tradable = life.join(census, how="inner")
tradable = tradable[tradable.index.isin(universe_addresses)].copy()
tradable["pair_id"] = [universe_addresses[a] for a in tradable.index]
tradable["launched_post_april"] = tradable["inception"] >= pd.Timestamp("2026-04-01")

print(f"Vaults in the trading universe with price history: {len(tradable)}")
print(f"  launched on or after 2026-04-01: {int(tradable['launched_post_april'].sum())}")
display(tradable["age_days"].describe().to_frame("age_days"))
'''))

# --- 3. the barriers, measured -------------------------------------------------------------
cells.append(md("""# 3. The three age barriers, measured on the run's own indicators

For every vault in the trading universe, the first date each selection input becomes non-NaN. The
gap between that date and the vault's inception is the barrier, and it is read off the indicator
series this backtest actually used rather than inferred from the parameter values.
"""))

cells.append(code('''BARRIER_INDICATORS = ["cagr_score", "sortino_score", "cagr_sortino_weight", "inverse_vol", "return_gate"]

_series_cache = {}
def indicator_series_for(name, pair):
    key = (name, pair.internal_id)
    if key not in _series_cache:
        _series_cache[key] = indicator_data.get_indicator_series(name, pair=pair, unlimited=True)
    return _series_cache[key]


barrier_rows = []
for address, row in tradable.iterrows():
    pair = strategy_universe.get_pair_by_id(int(row["pair_id"]))
    record = {"address": address, "name": row["name"], "inception": row["inception"], "age_days": row["age_days"]}
    for name in BARRIER_INDICATORS:
        series = indicator_series_for(name, pair)
        first_valid = series.first_valid_index() if series is not None and len(series) else None
        record[f"{name}_first"] = first_valid
        record[f"{name}_lag_days"] = (
            (first_valid - row["inception"]).days if first_valid is not None else float("nan")
        )
    barrier_rows.append(record)

barriers = pd.DataFrame(barrier_rows).set_index("address")
lag_summary = pd.DataFrame({
    "parameter": [
        f"cagr_lookback_days = {Parameters.cagr_lookback_days}",
        f"sharpe_lookback_days = {Parameters.sharpe_lookback_days}",
        "both legs required",
        f"inverse_vol_window = {Parameters.inverse_vol_window}",
        f"gate_lookback_days = {Parameters.gate_lookback_days}",
    ],
    "median_lag_after_inception_days": [
        barriers[f"{name}_lag_days"].median() for name in BARRIER_INDICATORS
    ],
    "vaults_never_valid": [
        int(barriers[f"{name}_first"].isna().sum()) for name in BARRIER_INDICATORS
    ],
}, index=BARRIER_INDICATORS)
lag_summary["share_never_valid"] = lag_summary["vaults_never_valid"] / len(barriers)
display(lag_summary)

never_scored = barriers["cagr_sortino_weight_first"].isna()
print(f"Vaults in the universe that can NEVER be scored inside this window: "
      f"{int(never_scored.sum())} of {len(barriers)} ({never_scored.mean():.0%})")
print(f"Of the post-2026-04-01 launches: "
      f"{int(never_scored[tradable['launched_post_april'].reindex(barriers.index).fillna(False)].sum())} "
      f"of {int(tradable['launched_post_april'].sum())}")
'''))

cells.append(md("""## What the anchor actually held

If the barrier binds, every position the anchor took should belong to a vault that was already old
enough to be scored. This checks that directly rather than assuming it.
"""))

cells.append(code('''held_rows = []
for position in state.portfolio.get_all_positions():
    if position.is_credit_supply():
        continue
    address = str(position.pair.pool_address).lower()
    if address not in tradable.index:
        continue
    entry = pd.Timestamp(position.opened_at)
    held_rows.append({
        "vault": position.pair.base.token_symbol,
        "entry": entry,
        "age_at_entry_days": (entry - tradable.loc[address, "inception"]).days,
        "pnl_usd": float(position.get_total_profit_usd() or 0.0),
    })

held = pd.DataFrame(held_rows)
print(f"Positions matched to a universe vault: {len(held)}")
display(held["age_at_entry_days"].describe().to_frame("age_at_entry_days"))
print(f"Positions entered in a vault younger than {Parameters.cagr_lookback_days} days: "
      f"{int((held['age_at_entry_days'] < Parameters.cagr_lookback_days).sum())}")
print(f"Youngest vault ever bought: {held['age_at_entry_days'].min()} days old at entry")
'''))

# --- 4. who is behind the barrier -----------------------------------------------------------
cells.append(md("""# 4. Who is behind the barrier

The vaults that can never be scored, ranked by realised Sharpe over their own life. Two size
filters are applied, because a high Sharpe on a vault that cannot absorb a position is not an
opportunity: last observed TVL of at least $50,000, and at least 45 fresh observations, so the
Sharpe is measured on real marks rather than on a forward-filled line.

A Sharpe measured on a short life is a weak estimate, so each row also carries the standard error
of its own Sharpe, `SE ~ sqrt((1 + S^2 / 2) / n)` on `n` fresh observations, and `sharpe_t`, the
Sharpe in units of that error. A vault whose `sharpe_t` is below about 2 is not distinguishable
from zero, however large its point estimate.
"""))

cells.append(code('''MIN_TRADABLE_TVL = 50_000
MIN_FRESH_FOR_STATS = 45
#: NB02 anchor CAGR on this window, the return the strategy would be giving up.
ANCHOR_CAGR = 0.3790

def add_sharpe_error(frame):
    """Standard error of a Sharpe estimated on `fresh_days` observations, and the implied t."""
    frame = frame.copy()
    n = frame["fresh_days"].clip(lower=2)
    per_period = frame["life_sharpe"] / np.sqrt(365.0)
    frame["sharpe_se"] = np.sqrt((1.0 + per_period ** 2 / 2.0) / n) * np.sqrt(365.0)
    frame["sharpe_t"] = frame["life_sharpe"] / frame["sharpe_se"]
    return frame


hidden = add_sharpe_error(tradable[never_scored.reindex(tradable.index).fillna(True)])
scored_cohort = add_sharpe_error(tradable[~never_scored.reindex(tradable.index).fillna(True)])

cohort_summary = pd.DataFrame({
    "hidden (never scorable)": [
        len(hidden),
        int(((hidden["last_tvl"] >= MIN_TRADABLE_TVL) & (hidden["fresh_days"] >= MIN_FRESH_FOR_STATS)).sum()),
        hidden["life_sharpe"].median(),
        hidden["life_cagr"].median(),
    ],
    "scorable": [
        len(scored_cohort),
        int(((scored_cohort["last_tvl"] >= MIN_TRADABLE_TVL) & (scored_cohort["fresh_days"] >= MIN_FRESH_FOR_STATS)).sum()),
        scored_cohort["life_sharpe"].median(),
        scored_cohort["life_cagr"].median(),
    ],
}, index=["vaults", "of which tradable size", "median life Sharpe", "median life CAGR"])
display(cohort_summary)

COHORT_COLS = ["name", "inception", "age_days", "fresh_days", "stale_share", "down_day_share",
               "life_sharpe", "sharpe_t", "life_sortino", "life_cagr", "life_max_dd", "last_tvl"]
tradable_hidden = hidden[(hidden["last_tvl"] >= MIN_TRADABLE_TVL) & (hidden["fresh_days"] >= MIN_FRESH_FOR_STATS)]
print(f"Hidden vaults at tradable size: {len(tradable_hidden)}")
print(f"  Sharpe distinguishable from zero (t > 2): {int((tradable_hidden['sharpe_t'] > 2).sum())}")
print(f"  and also earning more than the anchor's {ANCHOR_CAGR:.1%} CAGR: "
      f"{int(((tradable_hidden['sharpe_t'] > 2) & (tradable_hidden['life_cagr'] > ANCHOR_CAGR)).sum())}")
display(tradable_hidden.sort_values("life_sharpe", ascending=False)[COHORT_COLS].head(20))
'''))

cells.append(md("""## The post-2026-04-01 cohort specifically

Every vault launched on or after 2026-04-01 that the curator admits, whatever its size, so the size
filter cannot hide a name. `tradable_size` marks the ones that clear both filters above.
"""))

cells.append(code('''post_april = add_sharpe_error(tradable[tradable["launched_post_april"]])
post_april["tradable_size"] = (
    (post_april["last_tvl"] >= MIN_TRADABLE_TVL) & (post_april["fresh_days"] >= MIN_FRESH_FOR_STATS)
)
print(f"Post-2026-04-01 launches admitted by the curator: {len(post_april)}, "
      f"of which tradable size: {int(post_april['tradable_size'].sum())}")
print(f"Of those, Sharpe > 1 with t > 2: "
      f"{int((post_april['tradable_size'] & (post_april['life_sharpe'] > 1) & (post_april['sharpe_t'] > 2)).sum())}")
display(post_april.sort_values("life_sharpe", ascending=False)[COHORT_COLS + ["tradable_size"]])

fig = px.scatter(
    post_april.reset_index(),
    x="age_days", y="life_sharpe", size="last_tvl", color="tradable_size",
    hover_name="name",
    title="Post-2026-04-01 launches: realised Sharpe against age (bubble = last TVL)",
)
fig.show()
'''))

# --- 5. NB78 signature ---------------------------------------------------------------------
cells.append(md("""# 5. NB78 signature check: is a high Sharpe here the loser signature?

`sortino_score`'s docstring records why the Sharpe leg was replaced: NB78 found the vaults
responsible for most of the strategy's losses "almost never post a down day, which inflates their
trailing Sharpe rather than deflating it". A young vault is the easiest possible way to have posted
few down days, so a high Sharpe in the hidden cohort is exactly where that failure mode would hide.

If the hidden cohort's Sharpe were manufactured by an absence of down days, its high-Sharpe names
should show a materially lower down-day share than the scorable cohort's high-Sharpe names.
"""))

cells.append(code('''sig_hidden = tradable_hidden.copy()
sig_scored = scored_cohort[
    (scored_cohort["last_tvl"] >= MIN_TRADABLE_TVL) & (scored_cohort["fresh_days"] >= MIN_FRESH_FOR_STATS)
].copy()

def signature_row(frame, label):
    top = frame.nlargest(max(int(len(frame) * 0.25), 3), "life_sharpe")
    return {
        "cohort": label,
        "vaults": len(frame),
        "median down-day share": frame["down_day_share"].median(),
        "median stale share": frame["stale_share"].median(),
        "top-quartile Sharpe: median down-day share": top["down_day_share"].median(),
        "top-quartile Sharpe: median stale share": top["stale_share"].median(),
        "top-quartile Sharpe: median max DD": top["life_max_dd"].median(),
        "top-quartile Sharpe: median sharpe_t": top["sharpe_t"].median(),
    }

signature = pd.DataFrame([
    signature_row(sig_hidden, "hidden (never scorable)"),
    signature_row(sig_scored, "scorable"),
]).set_index("cohort")
display(signature.T)

fig = px.scatter(
    pd.concat([
        sig_hidden.assign(cohort="hidden"), sig_scored.assign(cohort="scorable"),
    ]).reset_index(),
    x="down_day_share", y="life_sharpe", color="cohort", size="last_tvl", hover_name="name",
    title="Realised Sharpe against down-day share (NB78 signature: high Sharpe with few down days)",
)
fig.show()
'''))

# --- 6. decision-aligned screen ------------------------------------------------------------
cells.append(md("""# 6. Decision-aligned screen: would a shorter CAGR window have picked better?

Sections 4 and 5 are hindsight. This is the test that matters: at each decision date, with only the
information `decide_trades` had, does a composite that can see the hidden cohort beat the one that
cannot?

The candidate rule is the **minimal** change - the incumbent composite with the CAGR leg's window
shortened from 360 to 90 days, everything else identical:

    short_composite = cagr_weight x CAGR_score(90d) + (1 - cagr_weight) x Sortino_score(45d)

Method is NB47's precision-at-6 with NB03b's two corrections - features read at `when - 1 bar` for
live parity (NB57), and only full baskets scored - plus two this screen needs of its own:

- **Capacity.** The inclusion rule admits any vault above $7,500 of TVL, which at the 33% pool cap
  is a $2,475 position against a $150,000 bankroll. An equal-weight basket of names that size is
  not a portfolio the strategy could hold, so every rule is run twice: once on the raw inclusion
  pool, and once on the pool restricted to vaults whose decision-date TVL could absorb a full
  1/6 share of a 98%-deployed book.
- **Median, not mean.** The Martin ratio divides by the ulcer index, which goes to zero on a basket
  that never draws down, so a single quiet fortnight can put a mean in the hundreds - the first
  version of this screen returned a sparse-regime mean of 277.5 for exactly that reason. Central
  tendency is reported as a median, with mean forward return beside it.
"""))

cells.append(code('''import datetime

GATE = float(Parameters.gate_threshold)
#: Live parity: `decide_trades` reads the bar before the decision date (NB57).
ONE_BAR = Parameters.candle_time_bucket.to_timedelta()
SHORT_CAGR_DAYS = 90
FORWARD_DAYS = 30
MIN_FULL_BASKET_DATES = 5
#: TVL a vault needs before a 1/6 share of a 98%-deployed book fits under the 33% pool cap.
CAPACITY_TVL = (
    Parameters.initial_cash * Parameters.allocation_pct
    / Parameters.max_assets_in_portfolio
    / Parameters.per_position_cap_of_pool_pct
)

candles_close_all = strategy_universe.data_universe.candles.df["close"]
inclusion_series = indicator_data.get_indicator_series("inclusion_criteria", unlimited=True)
inception_by_pair_id = {int(row["pair_id"]): row["inception"] for _, row in tradable.iterrows()}

decision_dates = pd.date_range(
    Parameters.backtest_start + datetime.timedelta(days=60),      # skip the cold-start window
    Parameters.backtest_end - datetime.timedelta(days=FORWARD_DAYS + 1),
    freq="2D",
)
print(f"{len(decision_dates)} decision dates from {decision_dates[0].date()} to {decision_dates[-1].date()}")
print(f"Capacity threshold: a full basket share is ${CAPACITY_TVL:,.0f} of vault TVL")


_close_cache = {}
def close_series(pair_id):
    if pair_id not in _close_cache:
        try:
            _close_cache[pair_id] = candles_close_all.xs(pair_id, level="pair_id").sort_index()
        except KeyError:
            _close_cache[pair_id] = None
    return _close_cache[pair_id]


def short_cagr_score(pair_id, at, lookback=SHORT_CAGR_DAYS):
    """`cagr_score` with a shorter window, computed from candles at or before `at` only."""
    series = close_series(pair_id)
    if series is None:
        return float("nan")
    window = series.loc[:at]
    if len(window) < lookback + 1:
        return float("nan")
    start, end = float(window.iloc[-lookback - 1]), float(window.iloc[-1])
    if start <= 0:
        return float("nan")
    cagr = (end / start) ** (365.0 / lookback) - 1.0
    return float(min(max(cagr, 0.0), 1.0))


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

cells.append(code('''K_MAIN = 6
K_HIDDEN = 3

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

    # Per-vault decision-date reads, done once and reused by every rule below.
    incumbent, short, hidden_only = {}, {}, {}
    big_enough = set()
    for pid in pool_ids:
        pair = strategy_universe.get_pair_by_id(pid)
        gate_value = indicator_series_for("return_gate", pair).asof(at)
        if not (gate_value == gate_value and gate_value > GATE):
            continue
        tvl_value = indicator_series_for("tvl", pair).asof(at)
        if tvl_value == tvl_value and float(tvl_value) >= CAPACITY_TVL:
            big_enough.add(pid)
        composite = indicator_series_for("cagr_sortino_weight", pair).asof(at)
        if composite == composite:
            incumbent[pid] = float(composite)
        sortino = indicator_series_for("sortino_score", pair).asof(at)
        cagr90 = short_cagr_score(pid, at)
        if sortino == sortino and cagr90 == cagr90:
            value = Parameters.cagr_weight * cagr90 + (1.0 - Parameters.cagr_weight) * float(sortino)
            short[pid] = value
            inception = inception_by_pair_id.get(pid)
            if inception is not None and (at - inception).days < Parameters.cagr_lookback_days:
                hidden_only[pid] = value

    def record(label, values, k, capacity):
        pool = {pid: v for pid, v in values.items() if pid in big_enough} if capacity else values
        top = sorted(pool, key=pool.get, reverse=True)[:k]
        total, martin = forward_metrics(top, when)
        screen_rows.append({
            "date": when, "rule": label, "regime": regime, "capacity_filtered": capacity,
            "scorable_pool": len(pool), "basket_size": len(top), "full_basket": len(top) == k,
            "forward_return": total, "forward_martin": martin,
        })

    for capacity in (False, True):
        record("incumbent (360d CAGR leg), top 6", incumbent, K_MAIN, capacity)
        record("short composite (90d CAGR leg), top 6", short, K_MAIN, capacity)
        record("incumbent (360d CAGR leg), top 3", incumbent, K_HIDDEN, capacity)
        record("hidden cohort only (90d CAGR leg), top 3", hidden_only, K_HIDDEN, capacity)

screen_raw = pd.DataFrame(screen_rows)
print("Mean scorable pool size per decision date:")
display(
    screen_raw.pivot_table(index="rule", columns="capacity_filtered", values="scorable_pool")
    .rename(columns={False: "raw inclusion pool", True: f"TVL >= ${CAPACITY_TVL:,.0f}"})
)
'''))

cells.append(md("""## Screen result

Scored on full baskets only, so every rule is compared at the same basket size. `median_martin` is
the median 30-day-forward Martin ratio of the basket; `mean_return` is the mean 30-day-forward
return, which unlike the Martin ratio has no zero-denominator failure mode and is the more robust
of the two on a sample this size.
"""))

cells.append(code('''def summarise(capacity):
    subset = screen_raw[(screen_raw["capacity_filtered"] == capacity) & screen_raw["full_basket"]]
    grouped = subset.groupby(["rule", "regime"])
    out = pd.DataFrame({
        "median_martin": grouped["forward_martin"].median(),
        "mean_return": grouped["forward_return"].mean(),
        "median_return": grouped["forward_return"].median(),
        "n_dates": grouped["date"].count(),
    }).unstack()
    out.columns = [f"{metric} ({regime})" for metric, regime in out.columns]
    out["full_basket_rate"] = (
        screen_raw[screen_raw["capacity_filtered"] == capacity].groupby("rule")["full_basket"].mean()
    )
    return out.sort_index()


for capacity, title in ((False, "Raw inclusion pool (TVL >= $7,500)"),
                        (True, "Capacity-filtered pool")):
    print(title)
    display(summarise(capacity))
'''))

cells.append(md("""## Verdict

The gate the plan set for a feature is that it must beat the incumbent **in both polling regimes**,
on comparable baskets. Applied here to the shortened CAGR leg, on the capacity-filtered pool, which
is the only version of the pool the strategy could actually trade.
"""))

cells.append(code('''verdict = summarise(True)
incumbent_6 = verdict.loc["incumbent (360d CAGR leg), top 6"]
short_6 = verdict.loc["short composite (90d CAGR leg), top 6"]
incumbent_3 = verdict.loc["incumbent (360d CAGR leg), top 3"]
hidden_3 = verdict.loc["hidden cohort only (90d CAGR leg), top 3"]

def compare(label, challenger, reference):
    return {
        "comparison": label,
        "sparse: beats on return": challenger["mean_return (sparse)"] > reference["mean_return (sparse)"],
        "dense: beats on return": challenger["mean_return (dense)"] > reference["mean_return (dense)"],
        "sparse: beats on median Martin": challenger["median_martin (sparse)"] > reference["median_martin (sparse)"],
        "dense: beats on median Martin": challenger["median_martin (dense)"] > reference["median_martin (dense)"],
    }

checks = pd.DataFrame([
    compare("short composite vs incumbent (top 6)", short_6, incumbent_6),
    compare("hidden cohort vs incumbent (top 3)", hidden_3, incumbent_3),
]).set_index("comparison")
display(checks.T)

passed = bool(checks.loc["short composite vs incumbent (top 6)"].all())
print(f"Shortened CAGR leg clears the both-regimes gate on the tradable pool: {passed}")
print("A pass here would be a gate to spend a backtest on, not a result on its own - NB03a put the "
      "minimum detectable effect on this window well above what a screen of this size resolves.")
'''))

write_notebook(cells, TRACK_DIR / "13-research-age-barrier.ipynb")
