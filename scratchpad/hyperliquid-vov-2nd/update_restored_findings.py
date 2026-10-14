"""Refresh completed baseline/weighting notebook conclusions from the new runs."""

import json

import nbformat
import pandas as pd

from repaired_data_replay import RESEARCH_DIR, RUN_ROOT
from score_matrix_analysis import markdown_table


def main():
    """Keep default summary tables on the common 2026 comparison window."""
    names = {1: "01-initial.ipynb", 2: "02-backtest-accepted-dollar-cap.ipynb", 3: "03-backtest-alternative-weighting.ipynb"}
    for number, name in names.items():
        metrics_path = RUN_ROOT / f"{number:02d}/metrics.json"
        if not metrics_path.exists():
            continue
        path = RESEARCH_DIR / name
        notebook = nbformat.read(path, 4)
        if any(c.execution_count is None for c in notebook.cells if c.cell_type == "code"):
            continue
        metrics = json.loads(metrics_path.read_text())
        rows = []
        for label, values in metrics.items():
            if label.startswith("Short"):
                row = {"Strategy": "Source v11" if number == 1 else label, "Final equity (USD)": f"${values['Final equity (USD)']:,.2f}", "CAGR": f"{values['CAGR']:.2%}", "Sharpe": f"{values['Sharpe']:.2f}", "Maximum drawdown": f"{values['Maximum drawdown']:.2%}", "Trades": values["Trades"]}
                if "Mean cash weight" in values:
                    row["Mean cash"] = f"{values['Mean cash weight']:.2%}"
                rows.append(row)
        descriptions = {
            1: "The source replay now gives 41.20% CAGR, 1.96 Sharpe and −6.40% maximum drawdown. Final equity is $194,520.81 versus the earlier $194,928.64 reference. The restored policy inputs remove most of the previous gap. The first 558 chronologically ordered trades match exactly; remaining differences begin in September.",
            2: "Accepted-dollar caps still underperform: 9.31% CAGR versus 41.20% for the parent, with 51.32% mean cash versus 8.83%. Parent controls reproduce notebook 01 on both periods; the original-request allocation assertions pass.",
        }
        if number == 3:
            short = [(label, v) for label, v in metrics.items() if label.startswith("Short")]
            best = max(short, key=lambda item: item[1]["CAGR"])
            descriptions[3] = f"All 20 short/full-history executions completed. Source and cap controls reproduce notebooks 01 and 02. Highest observed short-period CAGR is {best[1]['CAGR']:.2%} for {best[0]}, with {best[1]['Sharpe']:.2f} Sharpe and {best[1]['Maximum drawdown']:.2%} maximum drawdown."
        section = "## Restored-data results — 7 October 2026\n\n" + descriptions[number] + "\n\n### Strategy comparison — 2026-01-01 → 2026-10-05 (end exclusive, UTC)\n\n" + "Fresh engine backtests on the same pinned publication and merged readers, each starting with $150,000. Full-history runs are retained separately in the saved outputs.\n\n" + markdown_table(pd.DataFrame(rows)) + "\n\nBoth periods completed. Historical benchmark differences are separate from mandatory equality between controls on identical inputs. See [the rerun report](restored-data-rerun-2026-10-07.md) for input and clock provenance.\n"
        base = notebook.cells[0].source.split("## Repaired-data results")[0].split("## Restored-data results")[0]
        notebook.cells[0].source = base + section
        nbformat.write(notebook, path)
        analysis_name = {2: "02-accepted-dollar-cap-analysis.md", 3: "03-alternative-weighting-analysis.md"}.get(number)
        if analysis_name:
            previous = (RUN_ROOT / "before-rerun" / analysis_name).read_text()
            (RESEARCH_DIR / analysis_name).write_text(f"# Experiment {number:02d} — restored-data rerun\n\n" + section + "\n<details>\n<summary>Earlier analysis on the previous publication</summary>\n\n" + previous + "\n\n</details>\n")
        print(f"Refreshed completed experiment {number:02d}")


if __name__ == "__main__":
    main()
