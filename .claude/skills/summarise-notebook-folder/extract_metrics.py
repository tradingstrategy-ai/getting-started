"""Extract best-pick backtest metrics (CAGR, Sharpe, Max DD) from a notebook.

Notebooks contain performance metrics in multiple places:
- Grid search results table (ALL combinations, not just the best)
- "The best result found for ..." stream output (grid search winner)
- QuantStats comparison table (Strategy vs BTC vs ETH columns)
- Trade summary "Annualised return %" (different number from CAGR)

This script extracts the correct best-pick values using two methods
(QuantStats preferred for precision, grid search summary as fallback):
1. Parse the QuantStats text/plain table, first column only (all backtests)
2. Parse the "best result found" stream line (grid search notebooks, rounded)

Usage:
    python3 extract_metrics.py NOTEBOOK.ipynb
    python3 extract_metrics.py folder/   # process all .ipynb in folder

Output (per notebook):
    filename.ipynb  CAGR=184.17%  Sharpe=2.66  MaxDD=-4.88%
    or
    filename.ipynb  NO_RESULTS
"""

import json
import os
import re
import sys


def extract_from_best_result_line(nb):
    """Method A: parse 'The best result found for ...' stream output.

    Grid search notebooks print a single summary line like:
        CAGR: 184.00%, Sharpe: 2.66, Sortino: 12.99, Max drawdown:-5.00%
    """
    for cell in nb["cells"]:
        for out in cell.get("outputs", []):
            text = out.get("text", "")
            if isinstance(text, list):
                text = "".join(text)
            if "best result found" not in text.lower():
                continue
            cagr = re.search(r"CAGR:\s*([\d.]+%)", text)
            sharpe = re.search(r"Sharpe:\s*([\d.-]+)", text)
            max_dd = re.search(r"Max drawdown:\s*(-[\d.]+%)", text)
            if cagr:
                return {
                    "cagr": cagr.group(1),
                    "sharpe": sharpe.group(1) if sharpe else None,
                    "max_dd": max_dd.group(1) if max_dd else None,
                }
    return None


def extract_from_quantstats(nb):
    """Method B: parse QuantStats text/plain comparison table.

    The table has columns: Strategy | BTC | ETH (or similar benchmarks).
    Strategy is always the first column. We extract the first value on
    each metric line.

    Lines look like:
        CAGR﹪                                  184.17%              -55.63%
        Sharpe                                    2.66                -1.49
        Max Drawdown                            -4.88%              -49.82%
    """
    for cell in nb["cells"]:
        for out in cell.get("outputs", []):
            tp = out.get("data", {}).get("text/plain", "")
            if isinstance(tp, list):
                tp = "".join(tp)
            # QuantStats tables are >200 chars and contain CAGR
            if "CAGR" not in tp or len(tp) < 200:
                continue

            cagr = None
            sharpe = None
            max_dd = None

            for line in tp.split("\n"):
                stripped = line.strip()

                # CAGR line (uses ﹪ U+FE6A or regular %)
                if stripped.startswith("CAGR") and cagr is None:
                    vals = re.findall(r"-?[\d.]+%", stripped)
                    if vals:
                        cagr = vals[0]

                # Sharpe line (skip Prob. Sharpe, Smart Sharpe)
                if (
                    stripped.startswith("Sharpe")
                    and "Prob" not in stripped
                    and "Smart" not in stripped
                    and sharpe is None
                ):
                    vals = re.findall(r"-?[\d.]+", stripped.split("Sharpe", 1)[1])
                    if vals:
                        sharpe = vals[0]

                # Max Drawdown line
                if "Max Drawdown" in stripped and max_dd is None:
                    vals = re.findall(r"-[\d.]+%", stripped)
                    if vals:
                        max_dd = vals[0]

            if cagr:
                return {"cagr": cagr, "sharpe": sharpe, "max_dd": max_dd}

    return None


def extract_metrics(path):
    """Extract best-pick metrics from a single notebook file."""
    with open(path) as f:
        nb = json.load(f)

    # Try QuantStats first (precise values from the best-pick equity curve)
    result = extract_from_quantstats(nb)
    if result:
        return result

    # Fall back to grid search summary line (rounded to integers)
    return extract_from_best_result_line(nb)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} NOTEBOOK.ipynb [...]", file=sys.stderr)
        print(f"       {sys.argv[0]} folder/", file=sys.stderr)
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            for f in sorted(os.listdir(arg)):
                if f.endswith(".ipynb"):
                    paths.append(os.path.join(arg, f))
        else:
            paths.append(arg)

    for path in paths:
        fname = os.path.basename(path)
        try:
            result = extract_metrics(path)
        except Exception as e:
            print(f"{fname}\tERROR: {e}")
            continue

        if result is None:
            print(f"{fname}\tNO_RESULTS")
        else:
            cagr = result.get("cagr") or "—"
            sharpe = result.get("sharpe") or "—"
            max_dd = result.get("max_dd") or "—"
            print(f"{fname}\tCAGR={cagr}\tSharpe={sharpe}\tMaxDD={max_dd}")


if __name__ == "__main__":
    main()
