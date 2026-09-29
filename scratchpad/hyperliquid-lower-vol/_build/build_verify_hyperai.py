import sys
sys.path.insert(0, ".")
from builder import md, code, common_prefix_cells, common_suffix_cells, harness_cell, write_notebook, BUILD_DIR
from blocks_evidence import PARAM_ANCHOR
from blocks_prefilter import PARAM_ADDITIONS_PREFILTER, INDICATOR_ADDITIONS_PREFILTER, CELL14_REPLACEMENTS_PREFILTER
from blocks_evidence import INDICATOR_ADDITIONS_EVIDENCE
from blocks_stability import INDICATOR_ADDITIONS_STABILITY

cells = [md("""# Verification: the anchor on hyper-ai.py's own window

`~/code/strategies/strategy/hyper-ai.py` (v6) is parameter-for-parameter this track's anchor with
`backtest_end = 2026-07-10`. Its docstring reports, on an archive downloaded 2026-08-21:
cumulative return 27.76%, CAGR 61.72%, quantstats daily Sharpe 2.88, max drawdown -4.44%, time in
market 50%. This runs the anchor on that window, on this track's archive, so the two can be set
beside each other with only the snapshot differing.
""")]
cells += common_prefix_cells("verify-hyperai-window", cell6_replacements={PARAM_ANCHOR: PARAM_ADDITIONS_PREFILTER},
                             cell10_extra=INDICATOR_ADDITIONS_EVIDENCE + INDICATOR_ADDITIONS_STABILITY + INDICATOR_ADDITIONS_PREFILTER)
cells += common_suffix_cells(cell14_replacements=CELL14_REPLACEMENTS_PREFILTER)
cells.append(harness_cell())
cells.append(code('''import datetime
from tradeexecutor.statistics.key_metric import calculate_sharpe
state_w, equity_w, returns_w = run_variant("anchor_to_2026-07-10", backtest_end=datetime.datetime(2026, 7, 10))
rc, ppy = cycle_returns(equity_w)
daily_r = equity_w.resample("1D").last().ffill().pct_change().dropna()
row = {
    "window": f"{equity_w.index[0].date()} to {equity_w.index[-1].date()}",
    "cumulative_return": float(equity_w.iloc[-1] / equity_w.iloc[0] - 1.0),
    "cagr": cagr_of(equity_w),
    "cycle_sharpe": float(calculate_sharpe(rc, periods=ppy)),
    "daily_sharpe_quantstats_style": float(daily_r.mean() / daily_r.std() * (365 ** 0.5)),
    "max_dd": float((equity_w / equity_w.cummax() - 1.0).min()),
    "final_equity": float(equity_w.iloc[-1]),
    "positions": len([p for p in state_w.portfolio.get_all_positions() if not p.is_credit_supply()]),
}
display(pd.Series(row).to_frame("anchor on hyper-ai.py window, this archive"))
print("hyper-ai.py docstring (2026-08-21 archive): cumulative 27.76%, CAGR 61.72%, daily Sharpe 2.88, maxDD -4.44%")
print(f"full-window anchor (this archive):        cumulative {float(anchor_equity.iloc[-1]/anchor_equity.iloc[0]-1)*100:.2f}%, "
      f"CAGR {float(anchor_panel['cagr'])*100:.2f}%, cycle Sharpe {float(anchor_panel['cycle_sharpe']):.2f}, maxDD {float(anchor_panel['max_dd'])*100:.2f}%")
seg = anchor_equity[(anchor_equity.index >= pd.Timestamp("2026-07-10"))]
print(f"anchor from 2026-07-10 to end: {float(seg.iloc[-1]/seg.iloc[0]-1)*100:+.2f}% over {(seg.index[-1]-seg.index[0]).days} days")
display(provenance())
'''))
write_notebook(cells, BUILD_DIR / "verify-hyperai-window.ipynb")
