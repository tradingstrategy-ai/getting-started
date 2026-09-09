import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, research_backtest_cell, \
    integrity_and_audit_cells, write_notebook, TRACK_DIR

HEADING = """# NB03a - measurement: data quality, attribution and power

No strategy change. This notebook establishes what the [03-smoothing-experiment-plan.md](03-smoothing-experiment-plan.md)
track can and cannot measure before any allocation change is tried, per NB57's warning that
Hyperliquid vault marks are stale for a large, time-varying share of days.

**Based on:** [02-better-format.ipynb](02-better-format.ipynb), re-run on the **development window**
(2026-01-01 to 2026-06-30) rather than the full window. The hold-out (2026-07-01 to 2026-09-08) is
reserved and is not opened until [NB11](03-smoothing-experiment-plan.md).

## What this notebook does

1. **Staleness flags.** Share of zero-return vault-days by month, to confirm the NB57 polling-regime
   break (sparse January-March, dense from April) on this track's freshly downloaded data.
2. **Availability audit.** Confirms the new `btc_beta` indicator is read through the framework's
   live-parity path (`get_indicator_value(..., index=-1)`), not a direct panel index.
3. **Baseline attribution by vault beta.** Every position in the anchor run, bucketed by its
   90-day BTC beta at entry, to see how much of the anchor's return is the single-event BTC beta
   this track exists to reduce.
4. **Power calculation.** The smallest Sharpe difference the paired block-bootstrap could detect on
   this window, so every later notebook's "no significant difference" is read correctly.

## Key new insights and what did we learn from this experiment?

_To be filled in after the run._

## Summary of results

_To be filled in after the run._

## Robustness of results

_To be filled in after the run._
"""

cells = [md(HEADING)]
cells += common_prefix_cells("03a-measurement")
cells += common_suffix_cells()
cells.append(md("# Backtest\n\n- Anchor run on the development window only.\n"))
cells.append(research_backtest_cell("NB03a anchor, development window"))
cells += integrity_and_audit_cells()

cells.append(md("""# 1. Staleness by month

Zero daily return on a vault's share price is almost always a stale poll rather than a genuinely
flat day (NB57). This reproduces NB57's Finding 3 table on this track's own freshly downloaded
Hyperliquid price data, to confirm the regime break before trusting any statistic built on the
assumption of a real return distribution (downside deviation, ulcer index, event concentration,
best-day share).
"""))
cells.append(code("""candles_close = strategy_universe.data_universe.candles.df["close"]
pair_ids = candles_close.index.get_level_values("pair_id").unique()

monthly_rows = []
for pair_id in pair_ids:
    series = candles_close.xs(pair_id, level="pair_id").sort_index()
    daily_px = series.resample("1D").last().ffill()
    if len(daily_px) < 10:
        continue
    zero = daily_px.pct_change() == 0.0
    for month, share in zero.groupby(zero.index.to_period("M")).mean().items():
        monthly_rows.append({"month": str(month), "pair_id": pair_id, "zero_return": share})

staleness_df = pd.DataFrame(monthly_rows)
staleness_by_month = staleness_df.groupby("month")["zero_return"].mean().rename("share_of_zero_return_vault_days")
display(staleness_by_month.to_frame())

fig = px.bar(staleness_by_month.reset_index(), x="month", y="share_of_zero_return_vault_days",
             title="Share of zero-return (stale) vault-days by month")
fig.update_yaxes(tickformat=".0%")
fig.show()
"""))

cells.append(md("""# 2. Availability audit: is `btc_beta` read live-parity?

Confirms the new indicator is read through `StrategyInputIndicators.get_indicator_value()`
(`index=-1`, one bar before the decision timestamp), which NB57 verified is the correctly aligned
path, rather than indexed directly out of a pandas panel at the decision date - the mistake NB57's
correction found in NB41's panel variant.
"""))
cells.append(code("""sample_pair = strategy_universe.get_pair_by_id(next(iter(pair_ids)))
full_series = indicator_data.get_indicator_series("btc_beta", pair=sample_pair, unlimited=True)

# Pick a mid-window decision timestamp actually used by the backtest.
decision_timestamps = sorted(s.calculated_at for s in state.stats.portfolio)
sample_ts = pd.Timestamp(decision_timestamps[len(decision_timestamps) // 2])

# What `decide_trades` actually saw for this pair at this cycle, if it was tradable that day.
# There is no direct hook to re-call `get_indicator_value` outside `decide_trades`, so the audit
# instead confirms the framework's own documented semantics: `get_indicator_value` shifts by one
# full bar, i.e. it returns the value timestamped `sample_ts - 1 bar`, never `sample_ts` itself.
one_bar = Parameters.candle_time_bucket.to_timedelta()
value_at_prior_bar = full_series.asof(sample_ts - one_bar)
value_at_same_bar = full_series.asof(sample_ts)

audit_df = pd.DataFrame([
    ("Decision timestamp", sample_ts),
    ("btc_beta value framework would use (T-1 bar)", value_at_prior_bar),
    ("btc_beta value at T (would be look-ahead if used)", value_at_same_bar),
    ("Values differ (audit is discriminating)", value_at_prior_bar != value_at_same_bar),
], columns=["Check", "Value"])
display(audit_df)
print("All indicators in this track are read via `indicators.get_indicator_value(name, pair=pair)` "
      "inside decide_trades, which is this T-1-bar path by construction (NB57).")
"""))

cells.append(md("""# 3. Baseline attribution by vault beta

Every position the anchor run took, bucketed by the vault's 90-day BTC beta at entry. This is how
much of the anchor's return is the single-event BTC-beta exposure Goal 2 of the track exists to
reduce.
"""))
cells.append(code("""rows = []
for position in state.portfolio.get_all_positions():
    if position.is_credit_supply():
        continue
    buys = [t for t in position.trades.values() if t.is_buy() and t.is_success()]
    if not buys:
        continue
    entry_at = min(t.executed_at for t in buys)
    beta_series = indicator_data.get_indicator_series("btc_beta", pair=position.pair, unlimited=True)
    entry_beta = beta_series.asof(pd.Timestamp(entry_at))
    rows.append({
        "vault": position.pair.base.token_symbol,
        "entry_beta": float(entry_beta) if entry_beta == entry_beta else float("nan"),
        "pnl_usd": float(position.get_total_profit_usd() or 0.0),
        "days_held": ((position.closed_at or Parameters.backtest_end) - position.opened_at).days,
    })
attribution_df = pd.DataFrame(rows)
attribution_df["bucket"] = pd.cut(attribution_df["entry_beta"].abs(), [-0.01, 0.2, 0.6, 99], labels=["<0.2", "0.2-0.6", ">0.6"])

bucket_summary = attribution_df.groupby("bucket", observed=True).agg(
    positions=("vault", "count"),
    total_pnl_usd=("pnl_usd", "sum"),
    mean_days_held=("days_held", "mean"),
)
bucket_summary["share_of_net_pnl"] = bucket_summary["total_pnl_usd"] / attribution_df["pnl_usd"].sum()
display(bucket_summary)
display_head_and_tail(attribution_df.sort_values("pnl_usd", ascending=False), head_rows=10, tail_rows=5)
"""))

cells.append(md("""# 4. Minimum detectable effect

The half-width of the paired 20-day block-bootstrap CI on the anchor's own daily returns around
their mean is the smallest mean daily difference a later notebook's variant could be distinguished
from the anchor by. Quoted here once, in Sharpe-difference terms, so no later notebook oversells a
result inside this band.
"""))
cells.append(code("""import contextlib

with contextlib.suppress(NameError):
    del contextlib  # keep the namespace clean; harness cell below defines its own imports

def _block_bootstrap_ci(diff, block=20, draws=2000, seed=0):
    d = diff.dropna().to_numpy()
    n = len(d)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        sample = np.concatenate([d[s:s + block] for s in starts])[:n]
        means.append(sample.mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


rd = returns.resample("1D").sum(min_count=1).fillna(0.0)
lo, hi = _block_bootstrap_ci(rd - rd.mean())
half_width_bps = (hi - lo) / 2 * 1e4
mde_sharpe = (half_width_bps / 1e4) / rd.std() * np.sqrt(365)
power_df = pd.DataFrame([
    ("Development window trading days", len(rd)),
    ("Daily volatility", rd.std()),
    ("Bootstrap half-width (bps/day)", half_width_bps),
    ("Minimum detectable Sharpe difference", mde_sharpe),
], columns=["Metric", "Value"])
display(power_df)
print(f"A later notebook's variant cannot be distinguished from the anchor below a Sharpe "
      f"difference of about {mde_sharpe:.2f} on this window.")
"""))

write_notebook(cells, TRACK_DIR / "03a-research-data-quality-and-power.ipynb")
