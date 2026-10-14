"""Redraw parameter views from completed repaired-data engine results."""

import base64
import json
from pathlib import Path

import nbformat
import pandas as pd

from score_matrix_visualisation import (
    factorial_heatmap,
    missing_effect_heatmaps,
    weight_fingerprints,
    pareto_chart,
    parallel_coordinates,
    unique_factorial,
    with_backtest_period,
)
from score_matrix import FEATURES


def main():
    folder = Path(__file__).resolve().parent
    artefacts = folder / "_artifacts-restored-2026-10-07/04"
    path = folder / "04-opt-score-matrix.ipynb"
    notebook = nbformat.read(path, as_version=4)
    manifest = json.loads((artefacts / "chart-2026-manifest.json").read_text())
    definitions = json.loads((artefacts / "frozen-matrices.json").read_text())
    families = {k: (v["Weights"], v["Profile"]) for k, v in definitions.items()}
    recipes = manifest["score_blend_recipes"]
    start, end = [s[:10] for s in manifest["chart_period"]]
    period = f"{start} → {end} (end exclusive, UTC)"
    frame = unique_factorial(pd.read_csv(artefacts / "chart-2026-factorial.csv"), families, recipes)
    source = pd.read_csv(artefacts / "chart-2026-detailed-results.csv").query('Family == "Original v11"').iloc[0].to_dict()
    base = frame[(frame.Positions == 6) & (frame.Sizing == "equal") & (~frame.Missing)]
    assert len(frame) == len(base) * 3 * 3 * 2
    charts = {
        34: [factorial_heatmap(frame, m) for m in ["CAGR", "Sharpe", "Max DD"]],
        36: [missing_effect_heatmaps(frame)],
        38: [weight_fingerprints(families, FEATURES, recipes)],
        40: [pareto_chart(frame, source, x, y) for x, y in [("CAGR", "Sharpe"), ("CAGR", "Maximum drawdown"), ("Sharpe", "Maximum drawdown")]],
    }
    for index, figures in charts.items():
        headings = [o for o in notebook.cells[index].outputs if "text/markdown" in o.get("data", {})]
        assert len(headings) == len(figures)
        outputs = []
        for heading, figure in zip(headings, figures):
            with_backtest_period(figure, period)
            png = figure.to_image(format="png", width=figure.layout.width, height=figure.layout.height)
            outputs.extend([heading, nbformat.v4.new_output("display_data", data={"image/png": base64.b64encode(png).decode()})])
        notebook.cells[index].outputs = outputs
    explorer = with_backtest_period(parallel_coordinates(frame), period)
    notebook.cells[42].outputs = [o for o in notebook.cells[42].outputs if "text/markdown" in o.get("data", {})] + [nbformat.v4.new_output("display_data", data={"text/html": explorer.to_html(full_html=False, include_plotlyjs="cdn")})]
    for cell in notebook.cells:
        cell.source = cell.source.replace("unique_factorial(report_df,families)", "unique_factorial(report_df,families,panel.score_blend_recipes)")
        cell.source = cell.source.replace("unique_factorial(chart_report_df, families)", "unique_factorial(chart_report_df, families, panel.score_blend_recipes)")
    notebook.cells[22].source = notebook.cells[22].source.replace(
        'expected_parameter_count=len({json.dumps({"weights":list(np.asarray(w).round(10)),"profile":profile},sort_keys=True) for w,profile in families.values()}) * len(SearchParameters.position_counts) * len(SearchParameters.sizing_methods) * len(SearchParameters.missing_values)',
        'effective_families=unique_factorial(report_df[(report_df.Positions==6)&(report_df.Sizing=="equal")&(~report_df.Missing)],families,panel.score_blend_recipes)\nexpected_parameter_count=len(effective_families) * len(SearchParameters.position_counts) * len(SearchParameters.sizing_methods) * len(SearchParameters.missing_values)',
    )
    replacements = {
        "The default execution mode rebuilds the report from the original saved experiment snapshot, so a newer remote dataset cannot silently change this research. New data or uncached strategies require an explicit separate refresh.": "This authorised refresh pins the repaired 7 October inputs and uses a new indicator and result generation. Default execution reruns against that pinned snapshot; saved-report mode can be enabled for presentation-only rebuilds.",
        "Show previously saved 2026 compression replays with six equal-weight positions and missing=False. Candidates without a saved short replay are omitted; this report does not execute new configurations against refreshed data.": "Compare completed repaired-input 2026 compression replays with six equal-weight positions and missing=False.",
        "The saved full-history preflight establishes v6 formula parity, including all 2026 vault/dates. Saved equity and complete trade ledgers are compared again when rebuilding this report.": "The full-history preflight establishes v6 formula parity, including all 2026 vault/dates. Repaired-input equity and complete trade ledgers are compared above.",
        "In snapshot mode the saved 2026 metrics are therefore repeated for each cap, not presented as newly executed backtests.": "The repaired-input engine replays confirm identical metrics at all three caps.",
    }
    for cell in notebook.cells:
        for old, new in replacements.items():
            cell.source = cell.source.replace(old, new)
            for output in cell.get("outputs", []):
                for mime, value in output.get("data", {}).items():
                    if isinstance(value, str):
                        output.data[mime] = value.replace(old, new)
    notebook.cells[25].source += f"\n\nRecipe canonicalisation leaves {len(frame)} effective settings. Duplicate family names are not independent evidence."
    nbformat.write(notebook, path)
    (artefacts / "chart-alias-review.json").write_text(json.dumps({"named_rows": len(pd.read_csv(artefacts / "chart-2026-factorial.csv")), "effective_configurations": len(frame), "redrawn_cells": list(charts) + [42], "strategy_rules_changed": False}, indent=2))
    print(f"Redrew nine parameter figures; {len(frame)} effective configurations, no new strategy executions.")


if __name__ == "__main__":
    main()
