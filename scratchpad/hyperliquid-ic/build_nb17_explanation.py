from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "17-research-steady-vault-selection-explanation.ipynb"


def md(text):
    return nbf.v4.new_markdown_cell(text)


def py(text):
    return nbf.v4.new_code_cell(text)


cells = [
    md("""# Steady-vault selection explanation

This is the final human-readable decision sheet from `steady-vault-plan-01.md`.
It loads saved NB10--NB16 reports and ledgers, keeps vault address as the
primary identity, and writes the explanation sheet from those artefacts. It
does not reselect vaults, fit a model, or manufacture a clean holdout.

The sheet distinguishes point-in-time eligibility, requested weights and
accepted allocations. Young and sparse evidence remains visible through an
explicit cap; missing evidence is not treated as zero risk.
"""),
    py("""from pathlib import Path
import json
import pandas as pd

PROJECT_DIR = Path.cwd() / "scratchpad/hyperliquid-ic" if (Path.cwd() / "scratchpad/hyperliquid-ic").exists() else Path.cwd()
OUT = PROJECT_DIR / "_artifacts-selection-explanation"
OUT.mkdir(exist_ok=True)
ARTIFACT_DIRS = {
    "NB10": PROJECT_DIR / "_artifacts-steady-vault-data",
    "NB11": PROJECT_DIR / "_artifacts-profitability-repeatability",
    "NB12": PROJECT_DIR / "_artifacts-downside-stress",
    "NB13": PROJECT_DIR / "_artifacts-steady-vault-sizing",
    "NB14": PROJECT_DIR / "_artifacts-young-sparse",
    "NB15": PROJECT_DIR / "_artifacts-independent-groups",
    "NB16": PROJECT_DIR / "_artifacts-final-validation",
}

def load_report(name):
    path = ARTIFACT_DIRS[name] / f"{name.lower()}-report.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())

def result_count(report):
    value = report.get("metric_rows", report.get("backtest_metrics", report.get("metrics", [])))
    return int(value) if isinstance(value, (int, float)) else len(value)

REPORTS = {name: load_report(name) for name in ARTIFACT_DIRS}
coverage = pd.DataFrame([
    {"notebook": name, "report": str(ARTIFACT_DIRS[name] / f"{name.lower()}-report.json"),
     "metric_or_result_rows": result_count(report)}
    for name, report in REPORTS.items()
])
coverage.to_csv(OUT / "report-coverage.csv", index=False)
display(coverage)
"""),
    md("""## Frozen policy map

Requested weight is before TVL, individual, evidence or group caps. Accepted
weight is the post-cap amount in the saved target ledger.
"""),
    py("""POLICIES = pd.DataFrame([
    {"arm": "P0", "parent": "none", "rule": "positive observed growth", "purpose": "profitability screen"},
    {"arm": "P1", "parent": "P0", "rule": "growth >=15% annualised and positive first and second halves", "purpose": "profitability and repeatability"},
    {"arm": "P2", "parent": "P1", "rule": ">=70% positive observed weeks; largest event <=50%; best event removed remains positive", "purpose": "event repeatability"},
    {"arm": "D0", "parent": "P1", "rule": "P1 parity control", "purpose": "downside control"},
    {"arm": "D1", "parent": "P1", "rule": "max drawdown >= -3% on longest available 60/30/14-day window", "purpose": "downside admission"},
    {"arm": "D2", "parent": "D1", "rule": "annualised volatility <=8% on longest available 60/30/14-day window", "purpose": "low-volatility sensitivity"},
    {"arm": "D3", "parent": "D1", "rule": "halve requested weight after causal 180-day drawdown below -8%; released capital stays cash", "purpose": "stress response"},
    {"arm": "S0", "parent": "D1", "rule": "equal requested weights and 20% individual cap", "purpose": "sizing control"},
    {"arm": "S1", "parent": "D1", "rule": "inverse downside sizing with 5% floor and 20% cap", "purpose": "downside-aware sizing"},
    {"arm": "S2", "parent": "D1", "rule": "capped growth/downside sizing", "purpose": "sizing sensitivity"},
    {"arm": "E0", "parent": "P1 + D1", "rule": "20% mature cap; provisional young/sparse cap and 20% aggregate sleeve", "purpose": "young and sparse evidence"},
    {"arm": "E1", "parent": "P1 + D1", "rule": "2% individual provisional cap", "purpose": "strict evidence sensitivity"},
    {"arm": "E2", "parent": "P1 + D1", "rule": "graduated provisional cap from 2% to 10%", "purpose": "evidence sensitivity"},
    {"arm": "G0", "parent": "P1 + D1 + E0", "rule": "individual cap only", "purpose": "grouping control"},
    {"arm": "G1", "parent": "P1 + D1 + E0", "rule": "verified manager group cap 25%", "purpose": "manager concentration"},
    {"arm": "G2", "parent": "P1 + D1 + E0", "rule": "G1 plus complete-link weekly correlation >=0.75 with >=8 paired weeks", "purpose": "correlated concentration"},
])
POLICIES.to_csv(OUT / "policy-map.csv", index=False)
display(POLICIES)
"""),
    md("""## Manually reviewed examples and accepted allocations

The reason field is a diagnostic classification based on the manual curve
review. It is not a label used by the selection engine. E0 allocations are
aggregated from the saved A0b target ledger by address and date.
"""),
    py("""identity = pd.read_csv(ARTIFACT_DIRS["NB10"] / "manual-example-identity.csv")
metrics = pd.read_csv(ARTIFACT_DIRS["NB10"] / "manual-example-metrics.csv")
metrics = metrics.loc[metrics["period"].eq("full")].copy()
targets = pd.read_parquet(ARTIFACT_DIRS["NB14"] / "targets-a0b_allowlist-E0-full.parquet")
targets["date"] = pd.to_datetime(targets["date"])

GROUPS = {
    "StratWise": "unknown / independent until verified",
    "PF1": "PF1", "Passivbot Canon": "Passivbot Canon",
    "FuturAI Medium": "FuturAI family (manual verified mapping)",
    "FuturAI Low": "FuturAI family (manual verified mapping)",
    "Citadel": "Citadel", "Satori Quantum": "Satori Quantum",
    "HYPErQuantum4": "unknown / independent until verified",
}

def reason(row):
    if row["label"] == "StratWise":
        return "provisional young reference; short history retained with evidence cap"
    if row["label"] in {"Citadel", "Satori Quantum"}:
        return "manual false-positive counterexample: jump dominated"
    if row["label"] == "HYPErQuantum4":
        return "manual false-negative candidate; excluded from retrospective A0b universe"
    return "manual steady candidate; subject to point-in-time P1/D1/E0 gates"

allocation = targets.groupby("address", as_index=False).agg(
    allocation_observations=("date", "size"), first_allocation_date=("date", "min"),
    last_allocation_date=("date", "max"), mean_requested_weight=("requested_weight", "mean"),
    max_requested_weight=("requested_weight", "max"), mean_accepted_weight=("accepted_weight", "mean"),
    max_accepted_weight=("accepted_weight", "max"), accepted_weight_days=("accepted_weight", lambda s: int((s > 0).sum())),
    provisional_days=("provisional", "sum"),
)
examples = identity.merge(metrics, on=["label", "address"], how="left")
examples = examples.merge(allocation, on="address", how="left")
examples["group"] = examples["label"].map(GROUPS).fillna("unknown")
examples["decision_reason"] = examples.apply(reason, axis=1)
examples["eligibility"] = examples["in_A0b"].map({True: "A0b allowlist", False: "outside retrospective A0b allowlist"})
examples["requested_weight"] = examples["mean_requested_weight"].fillna(0.0)
examples["accepted_allocation"] = examples["mean_accepted_weight"].fillna(0.0)
EXAMPLE_COLUMNS = [
    "label", "address", "eligibility", "decision_reason", "group", "annualised_growth",
    "annualised_one_day_vol", "annualised_downside", "max_drawdown", "best_event_removed_growth",
    "best_positive_event_share", "positive_observed_week_share", "observed_marks", "max_gap_days",
    "requested_weight", "accepted_allocation", "accepted_weight_days", "provisional_days",
    "first_allocation_date", "last_allocation_date",
]
EXAMPLES = examples[EXAMPLE_COLUMNS].sort_values("label")
EXAMPLES.to_csv(OUT / "manual-examples-decision-sheet.csv", index=False)
display(EXAMPLES)
"""),
    md("""## Nearest false cases and matched outcomes

These are nearest manually reviewed examples, rather than supervised labels.
The outcome table is a matched portfolio-level comparison from NB16 for the
same saved universe and period.
"""),
    py("""FALSE_CASES = EXAMPLES.loc[
    EXAMPLES["label"].isin(["Citadel", "Satori Quantum", "HYPErQuantum4", "StratWise", "PF1", "Passivbot Canon", "FuturAI Medium", "FuturAI Low"]),
    ["label", "address", "eligibility", "decision_reason", "annualised_growth", "max_drawdown", "best_event_removed_growth", "accepted_allocation"],
].copy()
FALSE_CASES["case_type"] = FALSE_CASES["label"].map({
    "Citadel": "false positive / jump counterexample", "Satori Quantum": "false positive / jump counterexample",
    "HYPErQuantum4": "false negative / universe exclusion",
}).fillna("steady reference or candidate")
FALSE_CASES.to_csv(OUT / "nearest-false-cases.csv", index=False)

outcomes = pd.read_csv(ARTIFACT_DIRS["NB16"] / "final-validation-metrics.csv")
outcomes["feasible_18pct_cagr"] = outcomes["cagr"] >= 0.18
MATCHED_OUTCOMES = outcomes[[
    "recipe", "recipe_label", "universe", "period", "cagr", "weekly_sharpe", "daily_volatility",
    "max_drawdown", "ulcer", "mean_cash_fraction", "mean_effective_positions", "mean_turnover",
    "feasible_18pct_cagr",
]].sort_values(["universe", "period", "weekly_sharpe"], ascending=[True, True, False])
MATCHED_OUTCOMES.to_csv(OUT / "matched-outcome-comparison.csv", index=False)
display(FALSE_CASES)
display(MATCHED_OUTCOMES)
"""),
    md("""## Accounting, clocks and caveats

* Selection is point-in-time and uses observations available before the decision timestamp.
* Weekly Sharpe is the primary comparison clock; daily metrics are secondary diagnostics.
* Fresh raw observations are forward-filled for valuation only; missing returns are not zero risk.
* Share-price NAV is the accounting input and no additional fees are added; internalised vault fees remain in NAV.
* A0b is a retrospective current allowlist and requires the full-panel sensitivity. The held-NAV ledger is a mark diagnostic, not a liquidation replay.
* Young or sparse vaults can be provisionally selected with lower caps; StratWise remains the explicit young reference.
* Verified manager and relatedness groups are used only where provenance is available; unknown names stay singleton groups with the declared provisional cap.
* Best-event removal is an attribution diagnostic, not a tradable counterfactual. Historical results do not establish prospective performance.
"""),
    py("""SUMMARY_PATH = PROJECT_DIR / "steady-vault-summary-01.md"
summary = [
    "# Steady-vault selection summary", "",
    "Generated by `17-research-steady-vault-selection-explanation.ipynb` from saved NB10--NB16 artefacts.", "",
    "## Decision sheet", "",
    "The example table reports address identity, manual eligibility/reason, full-period metrics, requested E0 weight and accepted E0 allocation. Accepted allocations are post-cap observations from the saved target ledger.", "",
    EXAMPLES.to_markdown(index=False), "",
    "## Candidate policy map", "", POLICIES.to_markdown(index=False), "",
    "## Nearest false cases", "", FALSE_CASES.to_markdown(index=False), "",
    "## Matched portfolio outcomes", "", MATCHED_OUTCOMES.to_markdown(index=False), "",
    "## Interpretation", "",
    "Eligibility, requested allocation and accepted allocation are separate. Young and sparse evidence remains visible without a long-history admission barrier. The final comparison is retrospective: A0b is survivor-conditioned, discovery dates are not a clean holdout, and the next validation step is a prospective shadow run.", "",
]
SUMMARY_PATH.write_text("\\n".join(summary) + "\\n")
report = {
    "notebook": "17-research-steady-vault-selection-explanation.ipynb",
    "source_reports": {name: str(ARTIFACT_DIRS[name] / f"{name.lower()}-report.json") for name in ARTIFACT_DIRS},
    "manual_example_rows": int(len(EXAMPLES)), "false_case_rows": int(len(FALSE_CASES)),
    "matched_outcome_rows": int(len(MATCHED_OUTCOMES)),
    "stratwise_address": str(EXAMPLES.loc[EXAMPLES["label"].eq("StratWise"), "address"].iloc[0]),
    "summary_path": str(SUMMARY_PATH),
    "artifacts": ["report-coverage.csv", "policy-map.csv", "manual-examples-decision-sheet.csv", "nearest-false-cases.csv", "matched-outcome-comparison.csv", "nb17-report.json"],
    "assumptions": {
        "selection_clock": "point-in-time decision timestamps", "primary_ranking_clock": "weekly Sharpe, daily secondary",
        "valuation": "fresh raw marks forward-filled for valuation only", "fees": "no additional fees; share-price NAV includes internalised fees",
        "universe": "A0b retrospective allowlist plus full-panel sensitivity", "young_sparse": "provisional evidence caps; no long-history admission barrier",
    },
}
(OUT / "nb17-report.json").write_text(json.dumps(report, indent=2) + "\\n")
display(pd.DataFrame([report]))
"""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
nbf.write(nb, OUTPUT)
print(OUTPUT)
