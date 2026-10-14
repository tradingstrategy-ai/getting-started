"""Explain NB15 September cash from saved engine states and allocation ledgers."""

import base64
import hashlib
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "15-backtest-allocation-vs-v11.ipynb"


def main():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    folder = Path(nb.metadata["nb15"]["artifact_generation"])
    audit = folder / "september-cash"
    audit.mkdir(exist_ok=True)
    arms = ["V11", "A", "C", "G"]
    weights = [0.0] * 50
    weights[0] = 1.0
    summaries = []
    cycles = []
    ledgers = {}
    for arm in arms:
        tag = json.dumps(dict(w=weights, start="2026-01-01 00:00:00", end="2026-10-05 00:00:00", n=6, sizing="equal" if arm == "V11" else "inverse_variance", allocator="parent", source_control=arm == "V11", calmar_cap=5.0, missing=arm != "V11", profile="NB15-v11-as-of-observation" if arm == "V11" else f"NB14-{arm}-as_of_observation"), sort_keys=True)
        key = hashlib.sha256(tag.encode()).hexdigest()[:24]
        state = json.loads((folder / "engine" / f"{key}-state.json").read_text())
        absolute = pd.read_parquet(folder / f"2026-{arm}-absolute-weights.parquet")
        equity = pd.read_csv(folder / f"2026-{arm}-equity.csv", index_col=0, parse_dates=True).iloc[:, 0]
        cash = absolute.USDC.loc["2026-09"]
        summaries.append(dict(Strategy=arm, Mean=cash.mean(), Peak=cash.max(), End=cash.iloc[-1]))
        for t, messages in state["visualisation"]["messages"].items():
            date = pd.Timestamp(int(t), unit="s")
            if not pd.Timestamp("2026-09-01") <= date <= pd.Timestamp("2026-09-30"):
                continue
            text = "\n".join(messages)

            def value(label):
                return float(re.search(re.escape(label) + r": ([\d,.]+)", text).group(1).replace(",", ""))

            cycles.append(dict(Strategy=arm, Date=date, Cash_weight=float(absolute.loc[date].USDC), Cash_USD=float(absolute.loc[date].USDC * equity.loc[date]), Budget=value("Fresh deployable capital"), Accepted=value("Accepted investable equity"), Blocked_topups=value("Incumbent top-ups blocked by guard or deposit admission"), Unallocated=value("Unallocated fresh capital (includes top-ups blocked during sizing)"), Pending=value("Pending redemptions"), Pinned=value("Pinned settlement capital")))
        if arm != "V11":
            ledger = pd.read_csv(folder / "engine" / f"{key}-allocations.csv", parse_dates=["Date"])
            ledger = ledger[ledger.Date.between("2026-09-01", "2026-09-30") & ledger["Raw weight"].gt(0)].copy()
            ledger["Ceiling"] = np.minimum(0.33 * ledger["TVL (USD)"], 0.33 * ledger["Deployable budget (USD)"])
            ledgers[arm] = ledger
    summary = pd.DataFrame(summaries)
    cycle = pd.DataFrame(cycles)
    l = ledgers["A"]
    x = l.groupby("Date").agg(Budget=("Deployable budget (USD)", "first"), Before_admission=("Accepted allocation (USD)", "sum"), Final=("Final target (USD)", "sum"))
    x["Ceiling"] = l.groupby("Date").Ceiling.sum().clip(upper=x.Budget)
    x["Cap_shortfall"] = x.Budget - x.Ceiling
    x["Allocator_shortfall"] = x.Ceiling - x.Before_admission
    x["Blocked_topups"] = x.Before_admission - x.Final
    assert (x.Allocator_shortfall > -1e-6).all()
    assert np.allclose(x[["Cap_shortfall", "Allocator_shortfall", "Blocked_topups"]].sum(axis=1), x.Budget - x.Final)
    share = x[["Cap_shortfall", "Allocator_shortfall", "Blocked_topups"]].sum() / ((x.Budget - x.Final).sum())
    summary.to_csv(audit / "summary.csv", index=False)
    cycle.to_csv(audit / "cycles.csv", index=False)
    x.to_csv(audit / "A-shortfall-decomposition.csv")
    sample = l[l.Date.eq("2026-09-20")][["Vault", "TVL (USD)", "Accepted allocation (USD)", "Final target (USD)"]]
    sample.to_csv(audit / "A-2026-09-20-vaults.csv", index=False)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    bottom = np.zeros(len(x))
    for column, label, colour in [("Cap_shortfall", "Concentration / vault-TVL caps", "#eab308"), ("Allocator_shortfall", "Allocation below feasible ceiling", "#7c3aed"), ("Blocked_topups", "Rejected incumbent top-ups", "#ef4444")]:
        values = x[column].to_numpy() / 1000
        ax.bar(x.index, values, bottom=bottom, width=1.45, color=colour, label=label)
        bottom += values
    actual = cycle[cycle.Strategy.eq("A")].set_index("Date").loc[x.index]
    ax.plot(x.index, actual.Cash_USD / 1000, color="#111827", marker="o", ms=3, label="Actual cash after trades", lw=1.5)
    ax.set(title="A: September cash and target-allocation shortfalls\nBacktest 2026-01-01 → 2026-10-04; September focus", ylabel="USD thousands")
    ax.grid(axis="y", alpha=0.15)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    image = audit / "september-cash.png"
    fig.savefig(image, dpi=115, bbox_inches="tight")
    plt.close(fig)
    lines = ["## September 2026 cash investigation", "", "### Actual cash balances — 2026-01-01 through 2026-10-04 backtest, September focus", "", "These are daily USDC balances as a fraction of total account equity. The lighter grey region in the asset-weight charts is cash; the darker grey region is invested in other vaults.", "", "| Strategy | September mean cash | Peak cash | 30 September cash |", "|:--|--:|--:|--:|"]
    for row in summary.itertuples(index=False):
        lines.append(f"| {row.Strategy} | {row.Mean:.1%} | {row.Peak:.1%} | {row.End:.1%} |")
    lines += [
        "",
        "### Why the cash increased",
        "",
        "The ranking selects six vaults without considering whether their combined position capacity can absorb the account. The source allocator then limits each target to both 33% of the deployable account budget and 33% of that vault’s TVL. Lower-ranked vaults cannot fill the gap: `max_capacity_assets = max_assets_in_portfolio = 6` disables the residual-capacity extension.",
        "",
        "In A, Citadel leaves on 4 September and AceVault Hyper01 on 8 September. They return on 14 and 12 September respectively, reducing cash. Citadel leaves again on 18 September; AceVault Hyper01 and Octavious Maximus leave on 20 September. The last two are replaced by Buyback Spread Engine and Sequoia HyperStable Yield Optimizer. The archived score changes explain these rotations; the removed vaults pass the −16% return gate on the inspected dates.",
        "",
        f"Across September’s 15 decision cycles, **{share.Cap_shortfall:.1%} of the sum of A’s planned deployment shortfalls** comes from the combined concentration/TVL ceiling, {share.Blocked_topups:.1%} from rejected top-ups and {share.Allocator_shortfall:.1%} from allocation below the feasible ceiling. This sums repeated decision-level shortfalls, not lost profit or distinct cash dollars.",
        "",
        "### Concrete example — decision on 20 September 2026",
        "",
        "A has a $194,853 deployable budget. The six selected vaults have combined TVL of approximately $219,878; their 33%-of-TVL limits admit only $72,560 in total. All six targets reach their TVL limits before admission checks. The table shows target dollars, not new deposit requests.",
        "",
        "| Selected vault | TVL | Target before admission | Final target |",
        "|:--|--:|--:|--:|",
    ]
    for row in sample.itertuples(index=False, name=None):
        lines.append(f"| {row[0]} | ${row[1]:,.0f} | ${row[2]:,.0f} | ${row[3]:,.0f} |")
    lines += [
        "",
        "Pool limits leave **$122,293** of the deployable budget unused. HYPErQuantum4 and Gucky_4coin_2dot5x then reject **$1,354** of additional top-ups, leaving a $71,206 final target basket. Together with the approximately $3,977 deployment reserve, this predicts about **$127,624 cash**, matching the saved post-trade wallet balance. Cash is 64.2% of marked equity on that day.",
        "",
        "### Deposit checks and other explanations",
        "",
        "The inspected HYPErQuantum4 and Gucky_4coin_2dot5x rows have fresh previous-day permission observations, open-deposit flags and archived zero deposit caps; leader shares are approximately 5.38% and 5.19% on 20 September, below the strategy’s 5.5% policy. These checks reject top-ups rather than close the existing positions. DOEZOE is open on 20 September, then reports deposits disabled by its leader from the 22 September decision onward. By 30 September, rejected top-ups total $8,436; the concentration/TVL shortfall is still much larger, at $109,774.",
        "",
        "No pending redemptions or pinned settlement capital are recorded on any September decision in these four accounts. This comparison imposes no extra NAV-freshness veto. The inspected rejected checks use known recent observations rather than an unknown/stale permission clock. The 2% deployment reserve and trade thresholds cannot explain cash above 60%.",
        "",
        "By 20 September, all four strategies target the same $71,206 basket despite their different variance estimators and account sizes. Different weights cannot overcome the aggregate TVL ceiling; A’s larger capital also produces a higher cash percentage under the same absolute vault limits.",
        "",
        "### Cash and allocation shortfalls — 2026-01-01 through 2026-10-04 backtest, September focus",
        "",
        "Bars split the unallocated target budget into cap constraints, allocator slack and blocked top-ups. The line is actual wallet cash after trades, which also includes the deployment reserve and trade/accounting differences. Each bar is a separate decision snapshot, not a cumulative loss.",
        "",
        "![September cash decomposition](attachment:september-cash.png)",
        "",
        "### Implication",
        "",
        "September is mainly a basket-capacity problem. A useful next comparison would let selection account for usable capacity, or retain a larger incumbent when a proposed replacement contributes little deployable capital. Increasing the number of positions or relaxing TVL caps are other possible interventions, but should be judged by net profit and risk: filling cash with lower-quality vaults need not improve returns.",
    ]
    text = "\n".join(lines)
    cell = nbformat.v4.new_markdown_cell(text)
    cell.attachments = {"september-cash.png": {"image/png": base64.b64encode(image.read_bytes()).decode()}}
    nb.cells = [c for c in nb.cells if not (c.cell_type == "markdown" and c.source.startswith("## September 2026 cash investigation"))]
    nb.cells.append(cell)
    nbformat.write(nb, NOTEBOOK)
    report = text.replace("(attachment:september-cash.png)", f"({image.relative_to(ROOT)})")
    (ROOT / "15-september-cash-analysis.md").write_text("# NB15 — September cash analysis\n\n" + report + "\n")
    print(summary.to_string(index=False))
    print("Decision shortfall shares:", share.to_dict())
    print("Saved analysis and embedded chart in NB15.")


if __name__ == "__main__":
    main()
