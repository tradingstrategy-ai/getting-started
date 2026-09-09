import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, write_notebook, \
    BUILD_DIR, TRACK_DIR, BASE

HEADING = """# Verification: does the enhanced `decide_trades` reproduce the original baseline?

Not a research notebook. This is a correctness check for the
[03-smoothing-experiment-plan.md](03-smoothing-experiment-plan.md) track.

Every notebook from NB03a onward uses an **enhanced** `decide_trades` and `compute_sizing_weights`
that add the NB04 volatility target, the NB07 sizing families and beta-group cap, the NB08
event-concentration penalty and gain-to-pain tilt, and the NB09 strict-scoring rule. All of these
are gated behind `Parameters` flags that default to off, and every notebook's anchor row assumes
that with those flags off the enhanced code is **byte-for-byte equivalent in behaviour** to the
original `decide_trades` from [01-initial.ipynb](01-initial.ipynb).

If that assumption is false, every comparison in NB04-NB11 is measured against a wrong baseline.
This notebook tests it directly: it defines both versions in the same kernel, runs both on the
same universe, indicators and window, and asserts the resulting states are identical.
"""

cells = [md(HEADING)]
cells += common_prefix_cells("verify-anchor-parity")
cells += common_suffix_cells()   # cells 11-14: time range + ENHANCED algorithm

# Original algorithm cell, with the two top-level functions renamed so both versions coexist.
original = (BUILD_DIR / "cell14_orig.py").read_text()
assert original.count("def compute_sizing_weights(") == 1
assert original.count("weight_by_id = compute_sizing_weights(") == 1
assert original.count("def decide_trades(") == 1
original = original.replace("def compute_sizing_weights(", "def compute_sizing_weights_original(")
original = original.replace("weight_by_id = compute_sizing_weights(", "weight_by_id = compute_sizing_weights_original(")
original = original.replace("def decide_trades(", "def decide_trades_original(")
original = (
    "#: The ORIGINAL algorithm cell from 01-initial.ipynb, verbatim apart from renaming\n"
    "#: `compute_sizing_weights` -> `compute_sizing_weights_original` and\n"
    "#: `decide_trades` -> `decide_trades_original` so both versions coexist in one kernel.\n"
    "#: The shared helpers below (redemption pricing, cost basis, minimum-hold, the blacklist)\n"
    "#: are redefined with identical text, so redefinition is a no-op.\n\n"
) + original

cells.append(md("# The original algorithm, for comparison\n"))
cells.append(code(original))

cells.append(md("""# Run both and compare

Same universe, same indicator set, same window, same parameters - only `decide_trades` differs.
All new feature flags are at their defaults (off), which is the condition every anchor row in
NB04-NB11 relies on.
"""))
cells.append(code('''from tradeexecutor.backtest.backtest_runner import run_backtest_inline
from tradeexecutor.visual.equity_curve import calculate_equity_curve, calculate_returns

print("Feature flags in force for this comparison (all should be off/neutral):")
for flag in ("target_portfolio_vol", "high_beta_group_cap", "event_concentration_lambda",
             "gain_to_pain_tilt", "require_scored_candidates", "weighting_method",
             "sizing_risk_indicator", "selection_score_indicator"):
    print(f"  {flag} = {getattr(Parameters, flag, '<absent>')!r}")


def run(fn, name):
    # Mirrors the fix now in `run_variant`: reset the sell_tax that
    # `refresh_vault_redemption_accounting` mutates on the shared universe, so each run starts
    # from the same state. Without this, run 1 and run 2 of identical code differed by $428.
    apply_vault_redemption_capital_fee(strategy_universe, Parameters.vault_redemption_capital_fee)
    result = run_backtest_inline(
        name=name,
        engine_version="0.5",
        decide_trades=fn,
        indicator_combinations=indicator_data.indicator_combinations,
        cycle_duration=Parameters.cycle_duration,
        client=client,
        universe=strategy_universe,
        parameters=parameters,
        max_workers=1,
        start_at=Parameters.backtest_start,
        end_at=Parameters.backtest_end,
    )
    state_ = result.state
    equity_ = calculate_equity_curve(state_)
    positions_ = [p for p in state_.portfolio.get_all_positions() if not p.is_credit_supply()]
    return {
        "state": state_,
        "final_equity": float(equity_.iloc[-1]),
        "max_drawdown": float((equity_ / equity_.cummax() - 1.0).min()),
        "positions": len(positions_),
        "trades": len(list(state_.portfolio.get_all_trades())),
        "equity": equity_,
    }


# Run the ORIGINAL twice, with the enhanced run in between. If `original_a` and `original_b`
# differ from each other, then consecutive backtests in one kernel are not independent and any
# original-vs-enhanced difference is confounded by run order rather than by decide_trades logic.
original_a = run(decide_trades_original, "original decide_trades, first run")
enhanced_run = run(decide_trades, "enhanced decide_trades, all flags off")
original_b = run(decide_trades_original, "original decide_trades, repeat run")
original_run = original_a
'''))

cells.append(md("## Comparison\n"))
cells.append(code('''KEYS = ("final_equity", "max_drawdown", "positions", "trades")
comparison = pd.DataFrame([
    {"version": "original, run 1", **{k: original_a[k] for k in KEYS}},
    {"version": "enhanced, all flags off", **{k: enhanced_run[k] for k in KEYS}},
    {"version": "original, run 2 (control)", **{k: original_b[k] for k in KEYS}},
]).set_index("version")
display(comparison)

def max_equity_gap(x, y):
    return float((x["equity"] - y["equity"]).abs().max())

print(f"CONTROL  original run 1 vs original run 2 : ${max_equity_gap(original_a, original_b):.10f}")
print(f"TEST     original run 1 vs enhanced       : ${max_equity_gap(original_a, enhanced_run):.10f}")
print(f"         enhanced       vs original run 2 : ${max_equity_gap(enhanced_run, original_b):.10f}")
print()
control_gap = max_equity_gap(original_a, original_b)
if control_gap > 1e-6:
    print("FAIL: consecutive runs of the SAME decide_trades still differ - the sell_tax reset in")
    print("run_variant is not sufficient and backtests in one kernel remain order-dependent.")
else:
    print("PASS: consecutive runs of identical code are now bit-identical, so the sell_tax reset")
    print("makes backtests in one kernel independent. Any original-vs-enhanced gap below is real.")

equity_diff = (enhanced_run["equity"] - original_run["equity"]).abs()

# Per-trade comparison: every executed trade must match on pair, direction, timestamp and value.
def trade_fingerprints(state_):
    out = []
    for t in sorted(state_.portfolio.get_all_trades(), key=lambda t: (t.executed_at or t.opened_at, t.trade_id)):
        out.append((
            str(t.pair.pool_address).lower(),
            "buy" if t.is_buy() else "sell",
            str(t.executed_at),
            round(float(t.executed_reserve or 0.0), 6),
        ))
    return out

original_trades = trade_fingerprints(original_a["state"])
enhanced_trades = trade_fingerprints(enhanced_run["state"])
original_b_trades = trade_fingerprints(original_b["state"])
print(f"Trade fingerprints: original run 1 {len(original_trades)}, enhanced {len(enhanced_trades)}, original run 2 {len(original_b_trades)}")
print(f"  original run 1 == enhanced       : {original_trades == enhanced_trades}")
print(f"  original run 1 == original run 2 : {original_trades == original_b_trades}")

if original_trades != enhanced_trades:
    mismatches = [(a, b) for a, b in zip(original_trades, enhanced_trades) if a != b]
    print(f"First mismatches ({len(mismatches)} total):")
    for a, b in mismatches[:5]:
        print("  original:", a)
        print("  enhanced:", b)

assert original_a["positions"] == enhanced_run["positions"], "Position count differs"
assert original_a["trades"] == enhanced_run["trades"], "Trade count differs"
assert original_trades == enhanced_trades, "Trade-by-trade execution differs"
# The equity gap is only meaningful if it exceeds the control gap between two identical runs.
assert equity_diff.max() <= max(control_gap, 1e-6) + 1e-9, (
    f"Enhanced-vs-original equity gap ${equity_diff.max():.6f} exceeds the same-code control gap ${control_gap:.6f}"
)
print()
print("PASS: the enhanced decide_trades issues an identical trade sequence to the original with all")
print("flags off. Any equity-curve gap is within the run-order contamination measured by the control.")
'''))

cells.append(md("""## How much does the cold-universe first run distort the panel metrics?

Every sweep notebook in the track runs its **anchor first** and every variant afterward, so if the
first run sits on a different equity path than subsequent runs, the anchor's ulcer index and
volatility - two of the five adoption constraints - are measured on a systematically different
basis from the variants they gate.
"""))
cells.append(code('''import numpy as np

def metrics(equity_):
    dd = equity_ / equity_.cummax() - 1.0
    rd = equity_.pct_change().resample("1D").sum(min_count=1).fillna(0.0)
    days = (equity_.index[-1] - equity_.index[0]).days
    return {
        "final_equity": float(equity_.iloc[-1]),
        "cagr": float((equity_.iloc[-1] / equity_.iloc[0]) ** (365.0 / max(days, 1)) - 1.0),
        "ulcer": float(np.sqrt((dd ** 2).mean())),
        "max_dd": float(dd.min()),
        "ann_vol": float(rd.std() * np.sqrt(365)),
    }

cold = metrics(original_a["equity"])   # run 1, cold universe - what every anchor row uses
warm = metrics(original_b["equity"])   # run 2+, warm universe - what every variant row uses
impact = pd.DataFrame([cold, warm], index=["anchor basis (first run)", "variant basis (later runs)"])
impact.loc["absolute difference"] = impact.loc["variant basis (later runs)"] - impact.loc["anchor basis (first run)"]
impact.loc["relative difference %"] = 100 * impact.loc["absolute difference"] / impact.loc["anchor basis (first run)"].abs()
display(impact)

martin_cold = cold["cagr"] / cold["ulcer"]
martin_warm = warm["cagr"] / warm["ulcer"]
print(f"Martin ratio on the anchor basis  : {martin_cold:.4f}")
print(f"Martin ratio on the variant basis : {martin_warm:.4f}")
print(f"Relative difference               : {100 * (martin_warm - martin_cold) / martin_cold:+.2f}%")
'''))

cells.append(md("""## Are `abs_invested_beta` and `time_in_market` measuring what they claim?

The strategy runs on `CycleDuration.cycle_2d`, so its equity curve has a point every **2 days**.
The `panel()` helper resamples returns to 1D with `.fillna(0.0)`, which inserts a structural zero
on every off-cycle day, and then regresses that against BTC's **daily** returns. This checks
whether that attenuates the measured beta, and whether `time_in_market` is measuring deployment or
just the cycle cadence.
"""))
cells.append(code('''equity_ = original_b["equity"]
returns_ = equity_.pct_change().dropna()

print(f"Equity curve points: {len(equity_)}; window length: {(equity_.index[-1] - equity_.index[0]).days} days")
spacings = sorted({(b - a).days for a, b in zip(equity_.index, equity_.index[1:])})
print(f"Spacing between equity points, in days: {spacings}")

rd = returns_.resample("1D").sum(min_count=1).fillna(0.0)
zero_share = float((rd == 0).mean())
print()
print(f"After resample('1D').fillna(0.0): {len(rd)} points, {zero_share:.1%} of them exactly zero")
print(f"`time_in_market` as panel() computes it = (rd != 0).mean() = {1 - zero_share:.4f}")
print("  -> with a 2-day cycle this is ~0.5 by construction, regardless of how much capital is deployed.")

# Deployment actually implied by the portfolio statistics, for comparison.
invested = []
for s in original_b["state"].stats.portfolio:
    if s.total_equity:
        invested.append(1.0 - float(s.free_cash or 0.0) / float(s.total_equity))
print(f"Actual mean invested fraction from portfolio statistics: {np.mean(invested):.4f}")

# Beta, measured two ways.
btc = _btc_daily_returns_for(rd.index)
def ols_beta(y, x):
    j = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    if len(j) < 10 or j["x"].var() == 0:
        return float("nan"), float("nan")
    beta = j["y"].cov(j["x"]) / j["x"].var()
    return float(beta), float(j["y"].corr(j["x"]) ** 2)

beta_daily_zerofilled, r2_daily_zerofilled = ols_beta(rd, btc)

# Correct alignment: compare each strategy period return against BTC compounded over the SAME period.
btc_full = _btc_daily_returns_for(pd.date_range(equity_.index[0] - pd.Timedelta(days=5), equity_.index[-1], freq="1D"))
btc_period = []
for a, b in zip(equity_.index, equity_.index[1:]):
    window = btc_full.loc[(btc_full.index > a) & (btc_full.index <= b)]
    btc_period.append(float((1 + window).prod() - 1) if len(window) else np.nan)
btc_period = pd.Series(btc_period, index=equity_.index[1:])
strategy_period = returns_.reindex(btc_period.index)
beta_aligned, r2_aligned = ols_beta(strategy_period, btc_period)

beta_df = pd.DataFrame([
    {"method": "panel(): daily resample, zero-filled off-cycle days", "beta": beta_daily_zerofilled, "r_squared": r2_daily_zerofilled},
    {"method": "aligned: strategy cycle return vs BTC over the same period", "beta": beta_aligned, "r_squared": r2_aligned},
]).set_index("method")
display(beta_df)
print(f"Beta is understated by a factor of about {abs(beta_aligned / beta_daily_zerofilled):.1f}x "
      f"and R-squared by about {r2_aligned / max(r2_daily_zerofilled, 1e-12):.1f}x when off-cycle days are zero-filled.")
'''))

write_notebook(cells, TRACK_DIR / "_build" / "verify-anchor-parity.ipynb")
