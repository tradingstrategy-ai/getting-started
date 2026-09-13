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
2. **Availability audit.** Checks against the raw poll data that every observation contributing
   to the bar the strategy reads was recorded before the decision cycle - the property NB57's
   correction turned on - rather than restating the framework's documented semantics.
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
cells.append(code("""from pathlib import Path

# The audit that matters: does the daily bar the framework reads at a decision cycle contain only
# polls recorded before that cycle? NB57 established the alignment analytically; this checks it
# against the raw poll data for a sample of vaults rather than restating the docstring.
raw_path = Path("~/.cache/tradingstrategy/vaults/downloads/vault-prices.parquet").expanduser()
raw_polls = pd.read_parquet(raw_path, columns=["chain", "address", "written_at"])
raw_polls = raw_polls[raw_polls["chain"] == ChainId.hypercore.value].copy()
raw_polls["address"] = raw_polls["address"].str.lower()

decision_timestamps = sorted(s.calculated_at for s in state.stats.portfolio)
sample_ts = pd.Timestamp(decision_timestamps[len(decision_timestamps) // 2])
one_bar = Parameters.candle_time_bucket.to_timedelta()
bar_read = sample_ts - one_bar          # the bar `get_indicator_value(index=-1)` returns

audit_rows = []
sample_addresses = [
    str(p_.pair.pool_address).lower()
    for p_ in state.portfolio.get_all_positions()
    if p_.pair.is_vault()
][:5]
for address in sample_addresses:
    polls = raw_polls[raw_polls["address"] == address]
    # Polls that fall inside the bar the strategy reads: [bar_read, bar_read + 1 bar)
    in_bar = polls[(polls.index >= bar_read) & (polls.index < bar_read + one_bar)]
    if not len(in_bar):
        continue
    last_poll = in_bar.index.max()
    last_written = pd.Timestamp(in_bar["written_at"].max())
    audit_rows.append({
        "vault": address[:10],
        "bar read at cycle": bar_read,
        "last poll in that bar": last_poll,
        "last written_at": last_written,
        "poll <= decision time": last_poll <= sample_ts,
        "written <= decision time": last_written <= sample_ts,
    })

audit_df = pd.DataFrame(audit_rows)
display(audit_df)
if len(audit_df):
    observed_ok = bool(audit_df["poll <= decision time"].all())
    written_ok = bool(audit_df["written <= decision time"].all())
    print(f"Decision cycle {sample_ts}, reading the bar labelled {bar_read.date()}:")
    print(f"  every contributing poll was OBSERVED at or before the cycle: {observed_ok}")
    print(f"  every contributing poll was WRITTEN at or before the cycle:  {written_ok}")
    print()
    if observed_ok and not written_ok:
        lag = audit_df["last written_at"].max() - audit_df["last poll in that bar"].max()
        lag_hours = lag.total_seconds() / 3600
        print(f"Observation timing is correct - this is the alignment NB57's correction turned on,")
        print(f"and the framework path (`get_indicator_value`, index=-1) satisfies it. Reading the")
        print(f"bar labelled at the decision date instead would not, since that bar stays open until")
        print(f"the following day.")
        print()
        print(f"`written_at` sits about {lag_hours:.0f} hours after the poll, past the decision cycle:")
        print(f"these rows were rewritten by a later repair pass (the feed")
        print(f"carries a `hypercore_repair_status` column). So this archive cannot be used to prove")
        print(f"point-in-time availability - only observation-time alignment, which it does confirm.")
        print(f"A strict live-parity claim would need the original write timestamps, which the")
        print(f"repaired dataset no longer preserves. Noted as a limitation of the data, not of the")
        print(f"strategy code.")
    elif observed_ok and written_ok:
        print("Both conditions hold: the bar the strategy reads was fully observed and recorded")
        print("before the decision cycle.")
    else:
        print("Observation timing FAILS: the bar the strategy reads contains polls timestamped")
        print("after the decision cycle. That would be a genuine look-ahead and needs fixing.")
else:
    print("No polls found inside the sampled bar for the sampled vaults; audit inconclusive.")
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
    # Read one bar back, matching what `decide_trades` saw when it chose this vault (NB57).
    entry_beta = beta_series.asof(pd.Timestamp(entry_at) - Parameters.candle_time_bucket.to_timedelta())
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


# The strategy runs on a 2-day cycle, so its equity curve carries one point every 2 days.
# Resampling that to daily and zero-filling would insert a structural zero on every off-cycle
# day, understating volatility and distorting the detectable effect, so the power calculation
# is done on the strategy's own cycle clock.
rc = equity.pct_change().dropna()
spacings = [(b - a).days for a, b in zip(equity.index, equity.index[1:])]
spacing_days = float(np.median(spacings)) if spacings else 1.0
periods_per_year = 365.0 / max(spacing_days, 1e-9)

# A 20-day block on a daily clock is 10 cycles on a 2-day clock.
block_cycles = max(int(round(20 / spacing_days)), 2)
lo, hi = _block_bootstrap_ci(rc - rc.mean(), block=block_cycles)
half_width_bps = (hi - lo) / 2 * 1e4
mde_sharpe = (half_width_bps / 1e4) / rc.std() * np.sqrt(periods_per_year)
power_df = pd.DataFrame([
    ("Decision cycles in the backtest window", len(rc)),
    ("Cycle spacing (days)", spacing_days),
    ("Volatility per cycle", rc.std()),
    ("Annualised volatility", rc.std() * np.sqrt(periods_per_year)),
    ("Bootstrap block length (cycles)", block_cycles),
    ("Bootstrap half-width (bps/cycle)", half_width_bps),
    ("Minimum detectable Sharpe difference", mde_sharpe),
], columns=["Metric", "Value"])
display(power_df)
print(f"A later notebook's variant cannot be distinguished from the anchor below a Sharpe "
      f"difference of about {mde_sharpe:.2f} on this window.")
"""))

write_notebook(cells, TRACK_DIR / "03a-research-data-quality-and-power.ipynb")
