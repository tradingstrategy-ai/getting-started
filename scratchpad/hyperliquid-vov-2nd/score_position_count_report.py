"""Write findings from the completed portfolio breadth experiment."""

import json
import re

import nbformat
import pandas as pd

from score_position_count_experiment import ARTIFACT_DIR, NOTEBOOK, FOCAL_SCORE, SHORT_PERIOD, LONG_PERIOD, matched_deltas, short_label
from score_matrix_analysis import markdown_table


def metric_table(frame):
    """Format percentages and net engine metrics for a written research table."""
    result = frame.copy()
    for name in ("CAGR", "Maximum drawdown", "Mean cash weight"):
        if name in result:
            result[name] = result[name].map(lambda v: f"{v:.2%}")
    if "Sharpe" in result:
        result["Sharpe"] = result.Sharpe.map(lambda v: f"{v:.2f}")
    for name in ("Positions", "Trades", "Inputs", "Maximum vaults held"):
        if name in result:
            result[name] = result[name].map(lambda v: f"{int(v)}")
    return markdown_table(result)


def main():
    """Replace inherited conclusions only after every code cell has succeeded."""
    notebook = nbformat.read(NOTEBOOK, 4)
    assert all(cell.execution_count is not None for cell in notebook.cells if cell.cell_type == "code")
    assert not any(output.output_type == "error" for cell in notebook.cells if cell.cell_type == "code" for output in cell.outputs)
    completed = json.loads((ARTIFACT_DIR / "completed.json").read_text())
    assert completed["short_configurations"] == completed["long_configurations"] == 296
    short = pd.read_csv(ARTIFACT_DIR / "2026-results.csv")
    long = pd.read_csv(ARTIFACT_DIR / "Long-results.csv")
    robust = pd.read_csv(ARTIFACT_DIR / "2026-robustness.csv").set_index("Configuration")
    robust_long = pd.read_csv(ARTIFACT_DIR / "Long-robustness.csv").set_index("Configuration")
    focal = short[short.Score.eq(FOCAL_SCORE)].sort_values("Positions")
    focal_long = long[long.Score.eq(FOCAL_SCORE)].sort_values("Positions")
    reference = focal[focal.Positions.eq(6)].iloc[0]
    treatment = focal[~focal.Positions.eq(6)]
    best_cagr = treatment.sort_values("CAGR", ascending=False).iloc[0]
    best_sharpe = treatment.sort_values("Sharpe", ascending=False).iloc[0]
    overall = short[~short.Positions.eq(6)].sort_values("CAGR", ascending=False).iloc[0]
    overall_sharpe = short[~short.Positions.eq(6)].sort_values("Sharpe", ascending=False).iloc[0]
    deltas = matched_deltas(short)
    gains = treatment[(treatment.CAGR > reference.CAGR) & (treatment.Sharpe > reference.Sharpe) & (treatment["Maximum drawdown"] >= reference["Maximum drawdown"])]
    insights = f"""## Key new insights

- **Frozen highlighted score, six-position reference:** {reference.CAGR:.2%} CAGR, {reference.Sharpe:.2f} Sharpe and {reference['Maximum drawdown']:.2%} maximum drawdown in 2026; this matches experiment 06.
- **Highest CAGR among wider versions of that score:** N={int(best_cagr.Positions)} gives {best_cagr.CAGR:.2%} CAGR, {best_cagr.Sharpe:.2f} Sharpe and {best_cagr['Maximum drawdown']:.2%} drawdown. Highest Sharpe among wider versions is {best_sharpe.Sharpe:.2f} at N={int(best_sharpe.Positions)}. {len(gains)} of the three wider focal variants improve all three metrics against N=6.
- **Highest observed 2026 CAGR in the complete wider grid:** {overall.Configuration}: {overall.CAGR:.2%} CAGR, {overall.Sharpe:.2f} Sharpe and {overall['Maximum drawdown']:.2%} drawdown. Highest observed Sharpe is {overall_sharpe.Sharpe:.2f} for {overall_sharpe.Configuration}. These are descriptive search maxima.
- **Matched breadth effects:** {int(deltas['Joint improvement'].sum())} of 222 wider score/breadth combinations have higher CAGR and Sharpe with no worse drawdown than their own six-position support. This is not a probability of success or an independent significance test.
"""
    focal_cols = ["Positions", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight", "Maximum vaults held", "Trades"]
    if (treatment.CAGR < reference.CAGR).all() and (treatment.Sharpe < reference.Sharpe).all():
        insights += "- **Highlighted-score conclusion:** all three wider portfolios have lower 2026 CAGR and Sharpe than six positions. Lower cash alone is not an improvement; retain six positions as the reference for this frozen score.\n"
    blend7 = short[short.Score.eq("Blend 46d") & short.Positions.eq(7)].iloc[0]
    blend7_long = long[long.Score.eq("Blend 46d") & long.Positions.eq(7)].iloc[0]
    insights += f'- **Useful alternative, not the highlighted four-input formula:** two-input Blend 46d at seven positions gives {blend7.CAGR:.2%} CAGR, {blend7.Sharpe:.2f} Sharpe and {blend7["Maximum drawdown"]:.2%} drawdown in 2026. Full-history CAGR is {blend7_long.CAGR:.2%}, Sharpe {blend7_long.Sharpe:.2f} and drawdown {blend7_long["Maximum drawdown"]:.2%}. It improves its own six-position clipping-blend reference in both periods, but does not exceed the four-input six-position CAGR.\n'
    findings = insights + f"""\n## Summary of results

### Highlighted four-input score — {SHORT_PERIOD}

Hold 48% 360-day CAGR, 32% 45-day source-compatible Sortino, 10% 180-day CAGR and 10% 30-day Sortino fixed with legacy clips. Only the position limits and associated entry/exit ranks change. All portfolios start at $150,000 with no inherited positions. “Maximum vaults held” is realised breadth; the position parameter is a limit.

{metric_table(focal[focal_cols])}

<details><summary>Same frozen score over full history — {LONG_PERIOD}</summary>

Independent fresh-start replays on the same inputs. Full history overlaps 2026; it is not a holdout.

{metric_table(focal_long[focal_cols])}

</details>

### Observed scoring leaders at each breadth — {SHORT_PERIOD}

<details><summary>Highest observed CAGR and Sharpe supports, including the six-position reference</summary>

Supports are chosen by inspecting 2026, so these are descriptive comparisons. Coefficients and clips remain the predeclared experiment 06 settings.

"""
    selected = []
    for n in (6, 7, 8, 10):
        for objective in ("CAGR", "Sharpe"):
            row = short[short.Positions.eq(n)].sort_values([objective, "Configuration"], ascending=[False, True]).iloc[0]
            selected.append({"Objective": objective, **row.to_dict()})
    columns = ["Objective", "Positions", "Score", "Inputs", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight"]
    findings += metric_table(pd.DataFrame(selected)[columns]) + "\n\n</details>\n"
    paired = deltas.groupby("Positions").agg(**{"Median CAGR change": ("Delta CAGR", "median"), "Median Sharpe change": ("Delta Sharpe", "median"), "Median cash-weight change": ("Delta Mean cash weight", "median"), "Joint improvements": ("Joint improvement", "sum")}).reset_index()
    paired["Median CAGR change"] = paired["Median CAGR change"].map(lambda v: f"{v:+.2%}")
    paired["Median Sharpe change"] = paired["Median Sharpe change"].map(lambda v: f"{v:+.2f}")
    paired["Median cash-weight change"] = paired["Median cash-weight change"].map(lambda v: f"{v:+.2%}")
    findings += f"""\n### Matched effects across all 74 supports — {SHORT_PERIOD}

Compare each support against itself with six positions. Changes in percentage metrics are percentage points. Positive cash-weight change means more cash held; each breadth arm contains 74 paired comparisons.

{markdown_table(paired)}

## Robustness of results

All 296 configurations completed both periods: 444 new wider-position replays and 148 verified six-position references. Source v11 and the exact two-input wrapper match complete equity and every trade in both periods. Every six-position result matches experiment 06's metrics. Realised vault counts never exceed their assigned limits. Position attribution reconciles to equity with a maximum residual of {completed['maximum_attribution_residual_usd']:.2e} USD.

The selector algorithm remains the source implementation, but its cardinality-related entry/exit ranks change from 6/8 to N/(N+2). The 33% concentration cap, 98% allocation target, sizing lookback, clipping recipes, missing-score handling, admission checks and rebalancing costs remain fixed. Wider breadth is therefore not a standalone change in diversification: it also changes which ranks can enter and be retained. The engine follows the existing parent allocation and pinning rules rather than guaranteeing exactly N funded vaults on every decision.

"""
    for _, row in focal.iterrows():
        r = robust.loc[short_label(row)]
        findings += f"- **Fixed score, N={int(row.Positions)}:** leading vault {r['Leading vault']} contributes {r['Leader share of positive vault PnL']:.1%} of positive vault profits. Best day {str(r['Best day'])[:10]} returns {r['Best day return']:.2%}; excess kurtosis {r['Excess kurtosis']:.2f}. Sharpe is {r['Sharpe with best day zeroed']:.2f} with that return zeroed and {r['Sharpe without leader (fixed ledger)']:.2f} after removing the leader PnL on the fixed ledger.\n"
    jumps = pd.read_csv(ARTIFACT_DIR / "2026-jumps.csv")
    focal6_label = short_label(reference)
    single = jumps[jumps.Configuration.eq(focal6_label) & jumps.Date.eq("2026-06-24")]
    if len(single):
        day = single.iloc[0]
        findings += f'\nOn 24 June, {day["Leading vault"]} supplies {day["Leading share of positive day PnL"]:.1%} of positive vault PnL in the focal six-position portfolio, while BTC and ETH return {day["BTCUSDT interval return"]:.2%} and {day["ETHUSDT interval return"]:.2%} over the matching interval. It is not curator-excluded or quarantined at that date. These gains are vault-specific rather than a broad market rise; short or hedged vault profits can still be valid. The leading-vault and best-day sensitivities above quantify the dependence without applying post-hoc exclusions.\n'
    findings += f"""\n### Full-history sensitivity of the highlighted score — {LONG_PERIOD}

<details><summary>Best-day and leading-vault sensitivities</summary>

These remove booked returns or contributor PnL without rerunning selection; they are sensitivities, not tradable exclusion strategies. Curator annotations and matching BTC/ETH returns are saved in the notebook and detailed artefacts.

"""
    sensitivity = []
    for _, row in focal_long.iterrows():
        r = robust_long.loc[short_label(row)]
        sensitivity.append({"Positions": int(row.Positions), "Leading vault": r["Leading vault"], "Leader share of positive PnL": f"{r['Leader share of positive vault PnL']:.1%}", "Best day": str(r["Best day"])[:10], "Best day return": f"{r['Best day return']:.2%}", "Sharpe with best day zeroed": f"{r['Sharpe with best day zeroed']:.2f}", "Sharpe without leader": f"{r['Sharpe without leader (fixed ledger)']:.2f}"})
    findings += markdown_table(pd.DataFrame(sensitivity)) + """\n\n</details>

The full and short histories overlap and have already been inspected. The support grid and fixed coefficient mass are bounded; these results do not demonstrate an unseen-time optimum. Current membership/guard assumptions, carried NAV observations, weak historical permission coverage and concentration in individual vaults remain limitations. Default charts and tables use 2026 with explicit period titles. Generated caches, logs and states are ignored; reviewable findings and saved notebook outputs remain outside generated artefact directories.
"""
    exposure = pd.read_csv(ARTIFACT_DIR / "2026-focal-exposure-summary.csv")
    changes = pd.read_csv(ARTIFACT_DIR / "2026-focal-vault-changes.csv")
    all_positions = pd.read_csv(ARTIFACT_DIR / "2026-focal-all-positions.csv")
    details = exposure.copy()
    for name in ("Mean realised vaults", "Target-dollar-weighted score", "Sharpe without Pepe vs (fixed ledger)"):
        details[name] = details[name].map(lambda v: f"{v:.2f}")
    for name in ("Mean cash weight", "Unscored target dollars", "CAGR without Pepe vs (fixed ledger)"):
        details[name] = details[name].map(lambda v: f"{v:.2%}")
    for name in ("Final total vault PnL (USD)", "Pepe vs PnL (USD)"):
        details[name] = details[name].map(lambda v: f"${v:,.0f}")
    cohort = []
    for n in (7, 8, 10):
        data = changes[changes.Positions.eq(n)]
        new = data["Only held in wider variant"]
        cohort.append({"Positions": n, "Total PnL change (USD)": data["PnL change (USD)"].sum(), "PnL change in shared vaults (USD)": data.loc[~new, "PnL change (USD)"].sum(), "Wider-only vault PnL (USD)": data.loc[new, "PnL change (USD)"].sum()})
    cohort = pd.DataFrame(cohort)
    for name in cohort:
        if "(USD)" in name:
            cohort[name] = cohort[name].map(lambda v: f"${v:,.0f}")
    worst = pd.concat([changes[changes.Positions.eq(n)].nsmallest(5, "PnL change (USD)") for n in (7, 8, 10)], ignore_index=True)
    worst = worst[["Positions", "Vault", "Six-position PnL (USD)", "Wider PnL (USD)", "PnL change (USD)", "Six-position mean weight", "Wider mean weight"]]
    for name in worst:
        if "(USD)" in name:
            worst[name] = worst[name].map(lambda v: f"${v:,.0f}")
        if "weight" in name:
            worst[name] = worst[name].map(lambda v: f"{v:.2%}")
    losing = all_positions.sort_values("Final profit (USD)").head(8).copy()
    losing = losing[["Positions", "Vault", "Opened", "Closed", "Final profit (USD)", "Curator excluded", "Quarantined at entry"]]
    losing["Final profit (USD)"] = losing["Final profit (USD)"].map(lambda v: f"${v:,.0f}")
    loss_sensitivity = details[["Positions", "Pepe vs PnL (USD)", "CAGR without Pepe vs (fixed ledger)", "Sharpe without Pepe vs (fixed ledger)"]]
    details = details.drop(columns=["Pepe vs PnL (USD)", "CAGR without Pepe vs (fixed ledger)", "Sharpe without Pepe vs (fixed ledger)"])
    extra = f"""## How breadth changes the highlighted score — {SHORT_PERIOD}

### Realised holdings and funded scores

Mean holdings are calculated across daily carried portfolio valuations. Score averages use requested final target dollars, not realised time-weighted exposure. Removing Pepe vs PnL retains the original trading ledger and is a sensitivity, not an exclusion backtest. Cash is realised; missing component scores follow source semantics. A lower funded score is a ranking description, not a proof of lower future returns.

{markdown_table(details)}

### Sensitivity to Pepe vs

The seven-position variant deposits $22,983 on 8 July and redeems $15,772 on 10 July, losing $7,211 as modelled NAV falls by about 31%. It has no current curator exclusion or entry-date quarantine flag. Remove all this vault's PnL from the fixed trading ledger to see how much this one loss explains. The seven-position Sharpe rises to 1.97 and CAGR to 37.69%, still below six positions; no exclusion is applied to the strategy results.

{markdown_table(loss_sensitivity)}

### Shared vaults versus additional holdings

Reconcile the final PnL difference against six positions into vaults traded by both variants and vaults traded only by the wider variant. Shared-vault PnL changes include entry/exit timing, different position sizes and compounding; they cannot be attributed to simple weight dilution alone.

{markdown_table(cohort)}

### Largest losses of profit contribution

<details><summary>Five largest adverse vault-PnL changes at each wider breadth</summary>

Compare each fixed-score portfolio with six positions. Mean weights are time averages over the full period, so brief large exposures can look small in this column.

{markdown_table(worst)}

</details>

### Largest individual position losses and curator flags

<details><summary>Eight largest losing positions across the four focal variants</summary>

Position profits use the executed ledger and marked holdings. Existing curator flags are descriptive; a false flag does not certify data quality. No post-hoc exclusions are applied to reported strategy results.

{markdown_table(losing)}

</details>
"""
    extra = re.sub(r"(?<!\\)\$(?=-?\d)", r"\\$", extra)
    findings = re.sub(r"(?<!\\)\$(?=-?\d)", r"\\$", findings) + "\n" + extra
    notebook.cells = [c for c in notebook.cells if not (c.cell_type == "markdown" and c.source.startswith("## How breadth changes the highlighted score"))]
    notebook.cells.append(nbformat.v4.new_markdown_cell(extra))
    notebook.cells[0].source = notebook.cells[0].source.split("## Key new insights")[0] + findings.split("## How breadth changes the highlighted score")[0]
    nbformat.write(notebook, NOTEBOOK)
    (NOTEBOOK.parent / "07-score-position-count-analysis.md").write_text("# Experiment 07 — scoring inputs and portfolio breadth\n\n[Executed notebook](" + NOTEBOOK.name + ").\n\n" + findings)
    print(json.dumps({"focal_best_cagr_positions": int(best_cagr.Positions), "focal_best_sharpe_positions": int(best_sharpe.Positions), "joint_focal_improvements": len(gains), "joint_paired_improvements": int(deltas["Joint improvement"].sum())}))


if __name__ == "__main__":
    main()
