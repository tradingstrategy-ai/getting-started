"""Build C00's NB160 presentation and finalise its executed outputs."""

import json
import re
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "23-backtest-c00.ipynb"


def build():
    cells = []

    def md(text):
        cells.append(nbformat.v4.new_markdown_cell(text))

    def code(text):
        cells.append(nbformat.v4.new_code_cell(text))

    def section(title, description, source, level=2):
        md("#" * level + " " + title + "\n\n" + description)
        code(source)

    md("""# C00 Hyperliquid vault strategy

Based on [NB20](20-backtest-c00-vs-v11.ipynb), using the outline of [NB160](../vault-of-vaults/160-backtest-hyperliquid-low-value-treasury-test.ipynb).

Present C00's fixed strategy rules, run 2026 and full-history backtests, and compare against `hyper-ai-v11.py` under the same accounting. Each account starts with USD 150,000 and retains all available preceding warmup. Results and robustness notes will be inserted after execution.""")
    section(
        "Notebook setup",
        "Load the C00 execution code and report helpers. Charts are saved as separate static images.",
        """from copy import deepcopy
from pathlib import Path
import sys
import pandas as pd
from IPython.display import display, Markdown

ROOT = Path.cwd()
if not (ROOT / 'c00_template_backtest.py').exists():
    ROOT = ROOT / 'scratchpad/hyperliquid-vov-2nd'
sys.path.insert(0, str(ROOT))
import c00_template_backtest as backtest
from score_matrix_visualisation import compact_output
""",
    )
    section(
        "Universe definition",
        "Use NB20’s frozen repaired vault archive, metadata, whitelist and guard. All earlier observations remain available for indicator warmup.",
        """with compact_output('Load frozen universe and cached indicator warmup; estimated 2–4 minutes'):
    data, evaluator = backtest.initialise()

display(pd.DataFrame([
    {'Input': 'Strategy', 'Value': str(backtest.common.core.parent.SOURCE)},
    {'Input': 'Reference', 'Value': str(data['nb23_reference'])},
    {'Input': 'Vaults in feature panel', 'Value': len(evaluator.panel.pair_index)},
    {'Input': 'Execution NAV', 'Value': 'Latest actual observation at or before the query'},
    {'Input': 'Indicator warmup', 'Value': 'All available preceding history, including 2025'},
]))""",
    )
    section(
        "Parameters",
        "C00 retains the source selection and execution limits. Its four-component score, regularised variance and waterfall replace the corresponding v11 rules. The table describes the configuration actually replayed.",
        """Parameters = deepcopy(evaluator.parameters)
assert Parameters.initial_cash == 150000
assert Parameters.max_assets_in_portfolio == Parameters.max_capacity_assets == 6
assert Parameters.inverse_vol_window == 90

parameter_rows = [
    ('Initial capital', 'USD 150,000'),
    ('Decision interval', '2 days'),
    ('C00 ranking score', '0.48 CAGR360 + 0.32 Sortino45 + 0.10 CAGR180 + 0.10 Sortino30'),
    ('CAGR clip', '0–100%, divided by 100%'),
    ('Sortino clip', '0–3, divided by 3'),
    ('Missing score', 'Unscored vaults remain eligible; no component reweighting'),
    ('Risk window / shrinkage', '90 days / 30 actual daily updates'),
    ('Allocation', 'Waterfall ordered by inverse regularised variance'),
    ('Maximum positions / entry rank / exit rank', '6 / 6 / 8'),
    ('Deployment / portfolio cap / pool-TVL cap', '98% / 33% / 33%'),
    ('Minimum vault TVL', 'USD 7,500'),
    ('Momentum gate', '14-day return above −16%'),
    ('Leader-share gate', 'New capital blocked below 5.5% observed leader share'),
    ('Buy / sell threshold', '0.05% / 0.5% of source reference equity, USD 5 floor'),
    ('Tiny-position cleanup', '0.5% source threshold'),
    ('Modelled redemption charges', '10% positive profit + 0.1% gross capital allowance'),
]
display(pd.DataFrame(parameter_rows, columns=['Parameter', 'Value']))""",
    )
    section(
        "Trading universe",
        "The universe includes supporting reference pairs and Hyperliquid vaults. Supporting pairs supply data; the strategy’s holdings are vaults and cash.",
        """from tradeexecutor.analysis.pair import display_strategy_universe
universe_table = display_strategy_universe(evaluator.universe, compact=True, show_volume=False, show_tax=False)
if hasattr(universe_table, 'data'):
    universe_table = universe_table.data
backtest.show_table(universe_table.reset_index(), limit=12)""",
    )
    section(
        "Indicators",
        "Score components use completed prior daily buckets. Risk uses calendar returns carried forward from known NAV after inception; confidence counts actual observations separately.",
        """indicator_rows = [
    ('CAGR360', '360 days', '0.48', 'Unavailable active component makes the score unscored'),
    ('Sortino45', '45 days', '0.32', 'Same missing-score policy'),
    ('CAGR180', '180 days', '0.10', 'Same missing-score policy'),
    ('Sortino30', '30 days', '0.10', 'Same missing-score policy'),
    ('Regularised variance', '90 days', 'Sizing order', 'Partial history and leave-one-out positive peer prior'),
    ('Momentum', '14 days', 'Eligibility', 'Source gate above −16%'),
]
display(pd.DataFrame(indicator_rows, columns=['Indicator', 'Lookback', 'Role / coefficient', 'History handling']))""",
    )
    section(
        "Time range for backtest",
        "Run independent cash-start accounts for each period. End timestamps are exclusive; the full-history archive’s final day is partial.",
        """display(pd.DataFrame([
    {'Period': period, 'Start UTC': start, 'End UTC (exclusive)': end, 'Initial capital (USD)': 150000}
    for period, (start, end) in backtest.PERIODS.items()
]))""",
    )
    section(
        "Algorithm",
        r"""Rank eligible vaults by the four-component score, preserving source entry/exit hysteresis and deposit checks. For each selected vault, shrink its 90-day sample variance towards a positive leave-one-out peer median:

\[
\widehat{v}_i=\frac{m_i}{m_i+30}v_i+\frac{30}{m_i+30}v_{\mathrm{peer},i}.
\]

Here \(m_i\) counts actual daily observation updates. Missing own variance uses peer support; missing peer support uses valid positive own variance. If basket risk is unusable, the existing fallback applies. Waterfall fills the highest inverse-risk priority up to its permitted capacity, then passes remaining capital to the next selected vault. Six slots and all source thresholds still apply.

The callback below invokes the exact NB20 C00 implementation. Shared accounting corrects partial-sale charges, clears stale tax on re-entry and limits buys to net synchronous sale proceeds.""",
        '''def run_c00(period):
    """Replay C00 with the source selector and corrected common accounting."""
    return backtest.common.core.replay(data, evaluator, 'C00', period, active=False)''',
    )
    section(
        "Backtest",
        "Run C00 and the v11 control over both periods. Compare all four daily equity paths, successful trade sequences and key metrics against NB20.",
        """with compact_output('Four engine backtests and NB20 replication; estimated 3–10 minutes'):
    results, runs, attribution, absolute_weights = backtest.run_accounts(data, evaluator, run_c00)
with compact_output('Framework reports, curator and market checks; estimated 1–2 minutes'):
    context = backtest.prepare(data, evaluator, results, runs, attribution, absolute_weights)
state = runs[('2026', 'C00')]['result'].state
backtest.table(context, 'parity')""",
    )
    blocks = [
        ("Latest cycle cash and redemption snapshot", "Final cash and net marked holdings reconcile to account equity. This research execution settles synchronously.", "backtest.table(context, 'cash')", 2),
        ("Capital utilisation through time", "Actual cash as a fraction of total equity, including capital left over when selected vault capacities bind.", "backtest.chart(context, 'cash')", 2),
        ("Capital utilisation summary", "Cash and funded position counts describe realised deployment. September uses September 2026 observations.", "backtest.table(context, 'utilisation')", 3),
        ("Survivor selection", "Count funded vault holdings through time against the six-position limit. This shows actual holdings rather than unfilled candidate slots.", "backtest.chart(context, 'selection')", 2),
        ("Performance summary", "Net account metrics include cash and modelled redemption costs. Daily risk metrics use 365-day annualisation.", "backtest.table(context, 'metrics')", 2),
        ("Equity curve", "C00’s net marked account equity, starting with USD 150,000.", "backtest.chart(context, 'equity')", 2),
        ("Equity curve with drawdown", "Percentage loss from C00’s previous equity peak. Sparse NAV updates can bunch account returns.", "backtest.chart(context, 'drawdown')", 3),
        ("Asset weights", "Each holding is divided by total equity, including cash. The chart groups the eight largest pooled-average vaults and all remaining vaults.", "backtest.chart(context, 'absolute')", 2),
        ("Portfolio equity curve breakdown by asset", "The same asset groups shown in dollars, including cash. Their sum equals portfolio equity.", "backtest.chart(context, 'asset')", 3),
        ("Portfolio equity curve breakdown by chain", "C00 holds vaults and cash on Hyperliquid. Supporting market-reference pairs are not portfolio holdings.", "backtest.chart(context, 'chain')", 3),
        ("Weight allocation statistics", "Framework statistics summarise historical allocation sizes. Reserve cash is included according to the framework’s table convention.", "backtest.table(context, 'weights')", 3),
        ("Rolling performance", "Trailing windows use returns from this account only. The first 89 days have no full-window result.", None, 2),
        ("Rolling return", "Compounded account return over the preceding 90 calendar days.", "backtest.chart(context, 'rolling_return')", 3),
        ("Rolling Sharpe", "Mean daily return divided by its sample standard deviation over 90 days, annualised with √365. Zero-risk windows stay undefined.", "backtest.chart(context, 'rolling_sharpe')", 3),
        ("Monthly returns", "Compounded monthly account returns. Grey cells have no observations; the first and last months may be partial.", "backtest.chart(context, 'monthly')", 2),
        ("Positions at the end", "Open positions and their net marked value at the final account timestamp.", "backtest.table(context, 'positions')", 2),
        ("Strategy thinking", "The final source decision log is available below for inspecting permissions, capacity and trade decisions.", "backtest.table(context, 'thinking')", 2),
        ("Alpha model diagnostics", "Source signal diagnostics for the final decision; saved accounts use their final allocation ledger if the transient alpha snapshot is unavailable. Long tables show the first and last rows.", "backtest.table(context, 'alpha')", 2),
        ("Trading pair breakdown", "Net profit by vault, including closed and open positions, from the reconciled position profit curves. The first and last eight rows are displayed.", "backtest.table(context, 'profit')", 2),
        ("Trading metrics", "Framework trade summary for this account.", "backtest.table(context, 'trades')", 2),
        ("Vault performance", "Vault and position reports use this period’s C00 account.", None, 2),
        ("Vault statistics", "Framework vault statistics. Long tables show the first and last six rows.", "backtest.table(context, 'vaults')", 3),
        ("Vault position list", "Positions ordered by final booked profit, including open marks. The first and last eight rows are displayed.", "backtest.table(context, 'position_list')", 3),
        ("Redemption accounting", "Executed sell deductions and estimated open liquidation liabilities are reported separately. The 0.1% capital allowance is an inherited assumption.", "backtest.table(context, 'fees')", 2),
        ("Robustness analysis", "Concentration and extreme-update checks use the actual C00 account. Previously researched history supplies no independent validation.", "backtest.table(context, 'robust')", 2),
        ("Strongest account update", "The largest account update is attributed to vaults and compared with BTC/ETH over each actual NAV observation interval. Curator flags are shown alongside.", "backtest.table(context, 'tail')", 3),
    ]
    for title, description, source, level in blocks:
        md("#" * level + " " + title + "\n\n**2026-01-01–2026-10-04 UTC.** " + description)
        if source:
            code(source)
    md("## Comparison against hyper-ai-v11.py\n\nThe local v11 module runs with the same frozen archive, initial capital, decision timing and research accounting. The comparison changes ranking, risk estimation and allocation together.")
    logic = __import__("clean_c00_v11_comparison").LOGIC
    logic = logic[logic.index("| Rule |") : logic.index("### Common accounting")]
    md("### Strategy logic\n\nThese fixed rules apply to both periods.\n\n" + logic.replace("$", "USD "))
    for period in ("2026", "Long"):
        label = "2026-01-01–2026-10-04 UTC" if period == "2026" else "2023-03-01–2026-10-07 UTC"
        for title, desc, source in [
            ("Key metrics", "Green marks the higher value within each metric. Less negative drawdown is better.", f"backtest.table(context, 'comparison', '{period}')"),
            ("Capital usage and trading", "Cash, position counts and turnover show how the rules use capital.", f"backtest.table(context, 'comparison_cash', '{period}')"),
            ("Equity curves", "Both independent accounts use the same dollar scale and initial capital.", f"backtest.chart(context, 'equity', '{period}', compare=True)"),
            ("Drawdown comparison", "Each strategy’s loss from its own previous equity peak.", f"backtest.chart(context, 'drawdown', '{period}', compare=True)"),
            ("v11 asset weights", "Absolute holding weights, including cash, with the same vault colours and grouping as C00.", f"backtest.chart(context, 'absolute', '{period}', arm='V11')"),
            ("Quarterly returns", "Compounded account returns. An asterisk marks a partial quarter.", f"backtest.chart(context, 'quarterly', '{period}')"),
            ("Vault profit difference", "Ten largest absolute profit differences. These reflect selection, sizing, turnover and compounding jointly.", f"backtest.chart(context, 'contributors', '{period}')"),
        ]:
            section(title + " — " + label, desc, source, 3)
    md("## Full history\n\n**2023-03-01–2026-10-07 UTC.** This is a separate cash-start C00 account. Its 2026 segment includes accumulated wealth and holdings from previous years. The final archive day is partial.")
    for title, desc, kind, is_chart in [
        ("Performance summary", "Net metrics for the complete C00 account.", "metrics", False),
        ("Equity curve", "C00’s full-history net marked equity.", "equity", True),
        ("Equity curve with drawdown", "Loss from the account’s running equity peak.", "drawdown", True),
        ("Asset weights", "Absolute holding weights including cash, using the same grouping as the full-history v11 comparison.", "absolute", True),
        ("Monthly returns", "Compounded monthly account returns; grey cells have no observations and boundary months may be partial.", "monthly", True),
        ("Capital utilisation summary", "Full-account cash, September 2026 cash and funded positions.", "utilisation", False),
        ("Positions at the end", "Remaining holdings at the final account timestamp.", "positions", False),
        ("Robustness analysis", "Profit concentration and extreme daily updates over the complete account.", "robust", False),
        ("Strongest account update", "Vault NAV and BTC/ETH context over actual observation intervals.", "tail", False),
    ]:
        section(title + " — 2023-03-01–2026-10-07 UTC", desc, f"backtest.{'chart' if is_chart else 'table'}(context, '{kind}', 'Long')", 3)
    section(
        "Run details",
        "Record the exact completed generation and source identities for reproducibility.",
        """backtest.finish(context)
display(Markdown('<details><summary>Data and code fingerprints</summary>\\n\\n```json\\n'+__import__('json').dumps(data['manifest'], indent=2, default=str)+'\\n```\\n\\n</details>'))""",
    )
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    nbformat.write(nb, PATH)


def finalise():
    nb = nbformat.read(PATH, as_version=4)
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert not any(o.output_type == "error" for c in nb.cells for o in c.get("outputs", []))
    generations = []
    for c in nb.cells:
        for o in c.get("outputs", []):
            generations.extend(re.findall(r"<!-- nb23-generation: (.*?) -->", o.get("data", {}).get("text/markdown", "")))
        if c.cell_type == "code":
            c.outputs = [o for o in c.outputs if o.output_type != "stream"]
    assert len(set(generations)) == 1
    generation = Path(generations[0])
    complete = json.loads((generation / "complete.json").read_text())
    nb.cells[0].source = (generation / "final-header.md").read_text()
    nb.metadata["nb23"] = {"status": "complete", "artifact_generation": str(generation), "accounts": 4, "periods": 2, "template": "NB160", "engine_calls": complete["engine_calls"], "figures": complete["figures"]}
    nbformat.validate(nb)
    nbformat.write(nb, PATH)


if __name__ == "__main__":
    import sys

    finalise() if "--finalise" in sys.argv else build()
