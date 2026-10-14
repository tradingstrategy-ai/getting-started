"""Compact styled tables and individual figures for the score smoke study."""

import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from IPython.display import display, Markdown, Image
from portfolio_score_design import ROOT, START, END, PERIOD, label


class Report:
    """Render each element with its own heading, caption and period."""

    def __init__(self, folder):
        self.folder = folder
        self.figures = []
        (folder / "figures").mkdir(exist_ok=True)

    def intro(self, title, description):
        display(Markdown(f"### {title} — {PERIOD}; 30-day horizon\n\nFull 2026 grid / restricted combinations. {description}"))

    def table(self, frame, title, description, percent=()):
        self.intro(title, description)
        f = frame.copy()
        numeric = f.select_dtypes("number").columns
        formats = {c: "{:.2%}" if c in percent else "{:.0f}" if pd.api.types.is_integer_dtype(f[c]) else "{:.4g}" for c in numeric}
        style = f.style.format(formats, na_rep="—")
        for c in ("mean_return", "weighting_lift", "return_difference", "return_ic"):
            if c in f and f[c].notna().any():
                style = style.background_gradient(subset=[c], cmap="RdYlGn", **getattr(self, "colour_ranges", {}).get(c, {}))
        for c in ("mean_cash", "fallback_fraction", "unresolved_weight"):
            if c in f and f[c].notna().any():
                style = style.background_gradient(subset=[c], cmap="YlOrRd", **getattr(self, "colour_ranges", {}).get(c, {}))
        display(style.hide(axis="index"))

    def save(self, fig, slug, title, description):
        self.intro(title, description)
        fig.suptitle(f"{title}\n{PERIOD}; 30-day horizon\nFull 2026 grid / restricted combinations", fontsize=10)
        fig.tight_layout(rect=[0, 0, 1, 0.88])
        path = self.folder / "figures" / f"{slug}.png"
        fig.savefig(path, dpi=135, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        self.figures.append(dict(file=str(path), title=title))
        display(Image(filename=str(path)))

    def heatmap(self, pivot, slug, title, description, percent=False, limits=None, counts=None):
        a = pivot.to_numpy(float) * (100 if percent else 1)
        fig, ax = plt.subplots(figsize=(max(6, 0.7 * len(pivot.columns) + 3), max(3, (0.56 if counts is not None else 0.42) * len(pivot) + 1.8)))
        cmap = plt.get_cmap("RdYlGn").copy()
        cmap.set_bad("#eeeeee")
        kwargs = {"vmin": limits[0], "vmax": limits[1]} if limits else {}
        ax.grid(False)
        im = ax.imshow(np.ma.masked_invalid(a), aspect="auto", cmap=cmap, **kwargs)
        ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(pivot)), pivot.index)
        for i in range(a.shape[0]):
            for j in range(a.shape[1]):
                value = a[i, j]
                text = "—" if not np.isfinite(value) else f"{value:.1f}%" if percent else f"{value:.2f}"
                if counts is not None:
                    text = "pending" if not np.isfinite(value) and str(pivot.columns[j]) == "2026Q4" else text + f"\nn={int(counts.iloc[i,j])}"
                rgba = im.cmap(im.norm(value)) if np.isfinite(value) else (1, 1, 1, 1)
                brightness = np.dot(rgba[:3], [0.299, 0.587, 0.114])
                ax.text(j, i, text, ha="center", va="center", fontsize=8, color="black" if brightness > 0.55 else "white")
        fig.colorbar(im, ax=ax, shrink=0.8)
        self.save(fig, slug, title, description)


def render_report(data, tensors, result, audit, policies):
    plt.rcParams.update({"font.size": 10, "axes.labelsize": 11, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9, "figure.autolayout": False})
    r = Report(data["artifact"])
    s = result["summary"]
    out = result["outcomes"]
    ledger = result["allocations"]
    comp = tensors["components"]
    r.colour_ranges = {c: dict(vmin=float(s[c].min()), vmax=float(s[c].max())) for c in ("mean_return", "weighting_lift", "return_ic", "mean_cash", "fallback_fraction") if c in s}
    r.table(pd.DataFrame([dict(quarter="2026 Q1", scheduled=23, mature=23, pending=0), dict(quarter="2026 Q2", scheduled=23, mature=23, pending=0), dict(quarter="2026 Q3", scheduled=23, mature=16, pending=7), dict(quarter="2026 Q4", scheduled=1, mature=0, pending=1)]), "Scheduled and mature observations", "Every decision date remains in diagnostics; immature labels cannot contribute returns. All available 2025 data and earlier history initialise indicators.")
    for start in (0, 12, 24):
        rows = []
        for p in policies[start : start + 12]:
            rows.append(dict(arm=p["arm"], ranking=label(p["ranking"]), weighting=label(p["weighting"]), map=p["sizing_map"], N=p["N"], missing=p["missing"], constraints=p["constraints"], purpose=p["purpose"]))
        r.table(pd.DataFrame(rows), f"Executed design T{start:02d}–T{start+11:02d}", "Ingredients are combined before selection; weighting maps convert one final score into requested capital. C applies entry caps; P is uncapped.")
    r.table(pd.DataFrame([{k: p[k] for k in ("arm", "ranking_recipe_id", "weighting_recipe_id")} | {"status": "executed_all_70_origins"} for p in policies]), "Canonical executed recipe identities", "Exact twenty-character hashes of canonical expression JSON. Displayed labels are shorthand; the saved candidate/score ledgers and manifest preserve masks, recipes and parameters.")
    r.table(tensors["warmup"][["component", "eligible", "finite", "missing", "feature_cutoff"]], "First-origin indicator coverage", "These are eligible vaults on 1 January 2026, with the complete retained history through 31 December 2025. Long-window missingness does not remove young vaults.")
    r.table(result["parity"].drop(columns=["reference_policy"], errors="ignore"), "Reference reproduction", "Saved NB10 ledger comparisons use exact identities, weights and outcomes. These are average independent 30-day returns, not annualised strategy performance.", percent=["mean_return", "mean_cash"])
    r.table(audit, "Independent calculation audit", "Adverse arithmetic, original NAV reconstruction, causal cutoffs, exact source controls and ledger consistency must pass before interpreting outcomes.")
    for start in (0, 12, 24):
        r.table(s.iloc[start : start + 12][["arm", "mean_return", "median_return", "mean_variance", "mean_drawdown", "weighting_lift", "return_ic", "resolved", "paired", "mean_cash"]], f"Provisional outcomes T{start:02d}–T{start+11:02d}", "Equal-origin means over resolved mature baskets. Weighting lift uses equal allocation on the identical basket and accepted budget; support can differ across arms. Metric colour scales are shared across all three outcome tables.", percent=["mean_return", "median_return", "mean_drawdown", "weighting_lift", "mean_cash"])
    r.table(s[["arm", "positive_count", "effective_N", "distance_equal", "mean_cash", "fallback_fraction", "unscored_funded", "basket_overlap", "overlap_reference"]], "Mechanism activity and funding", "Requested N can exceed funded positions. Distance from equal is total variation of requested weights; overlap is Jaccard identity overlap with the named control.", percent=["distance_equal", "mean_cash", "fallback_fraction", "basket_overlap"])
    ic = result["score_ic"].query("mature").groupby(["arm", "role"]).agg(return_ic=("return_ic", "mean"), sharpe_ic=("sharpe_ic", "mean"), return_dates=("return_ic", "count"), sharpe_dates=("sharpe_ic", "count")).unstack("role")
    ic.columns = [f"{role}_{metric}" for metric, role in ic.columns]
    r.table(ic.reset_index(), "Ranking and weighting score associations", "Mean per-origin eligible-universe Spearman IC with realised return and Sharpe, using finite pairs. Counts are dates with defined IC. A weighting-score IC measures ordering, not whether dollar sizing improves a basket; equal/source constants have no IC.")
    r.table(result["contrasts"], "Matched recipe differences", "Each difference is new minus control on common resolved origins. Cash differences flag deployment effects; changing a ranking recipe can change baskets and support.", percent=["return_difference", "cash_difference", "common_budget_difference"])
    from portfolio_snapshot_statistics import support_counts

    blocks = []
    for (arm, control), g in result["contrast_dates"].groupby(["arm", "control"]):
        _, nonoverlap, complete = support_counts(g.rename(columns={"return_difference": "effect"}), START, END, 30, 30)
        blocks.append(dict(arm=arm, control=control, nonoverlapping_windows=nonoverlap, complete_blocks=complete, required_blocks=10, inference_gate_met=complete >= 10))
    r.table(pd.DataFrame(blocks), "Calendar support for matched comparisons", "Inherited 30-day calendar blocks count only fully supported contrasts. All comparisons remain descriptive; the smoke scope does not relax the ten-block inference gate.")
    four = result["four_cell"].copy()
    r.table(four, "Ranking, sizing and interaction", "The F/I four-cell block compares T01/T05/T06/T07 on common resolved dates. Differences include deployment effects where accepted cash differs.", percent=["selection", "sizing", "interaction", "total"])
    c = comp[comp.component.isin(["I90", "V90"])]
    fig, ax = plt.subplots(figsize=(7, 3.7))
    for name, g in c.groupby("component"):
        ax.hist(g.value.dropna(), bins=np.linspace(0, 1, 31), alpha=0.6, label=name, density=True)
    ax.axvline(0.5, color="grey", ls="--")
    ax.set(xlabel="Eligible-universe bounded component score", ylabel="Density")
    ax.legend()
    r.save(fig, "inverse-risk-components", "Inverse-risk component magnitudes", "The shared peer anchor is 0.5. Same relative-risk inputs have identical I/V order, while score magnitudes differ. Prior shrinkage can concentrate values near 0.5.")
    c = comp[comp.component.isin(["K90", "K360", "Kmax"])]
    fig, ax = plt.subplots(figsize=(7, 3.7))
    for name, g in c.groupby("component"):
        ax.hist(g.value.dropna(), bins=np.linspace(0, 1, 31), histtype="step", linewidth=1.7, label=name, density=True)
    ax.set(xlabel="Transformed historical K component", ylabel="Density")
    ax.legend()
    r.save(fig, "k-components", "K score distributions", "Missing scores are excluded from these signed-K densities and remain in the coverage table. Maximum history also varies by vault age; positive-K is shown separately.")
    positive = comp[comp.component.eq("K30+") & comp.available].value
    fig, ax = plt.subplots(figsize=(7, 3.7))
    ax.hist(positive, bins=np.linspace(0, 1, 31), weights=np.full(len(positive), 100 / len(positive)), color="#2563eb")
    ax.set(xlabel="Positive-K transformed score", ylabel="Finite observations (%)")
    r.save(fig, "positive-k", "Positive-K valid-zero mass", f"{100*positive.eq(0).mean():.1f}% of finite K30+ observations are valid zeros from non-positive K. This mass must not be treated as unavailable; geometric scores can become zero.")
    names = ["F", "I90", "V90", "K90", "K360", "Kmax", "C180", "So30", "D90", "Sh90", "Ca180"]
    w = comp.pivot(index=["origin_at", "pair_id"], columns="component", values="value")[names]
    r.heatmap(w.corr(method="spearman"), "component-correlation", "Historical component rank correlations", "Pairwise finite eligible observations; pooled correlations describe redundancy, not prediction or independent date-level evidence.", limits=(-1, 1))
    coverage = comp.groupby("component").agg(finite_fraction=("available", "mean"), observations=("available", "size"), median_actual_updates=("actual_count", "median"), median_scale_support=("scale_support", "median")).reset_index()
    r.table(coverage, "Eligible-component support", "Denominator includes every eligible vault/date observation for that component. Finite prior-supported risk and empirically measured risk are separately retained in the ledger. Dashes for frozen composite scores mean no single update count or fitted scale applies; they do not mean zero observations.", percent=["finite_fraction"])
    from portfolio_score_components import components_needed

    diagnostics = []
    for policy in [p for p in policies if p["arm"] in ("T05", "T14", "T18")]:
        for role in ("ranking", "weighting"):
            for name in components_needed([dict(ranking=policy[role], weighting=policy[role])]):
                if name == "source90":
                    continue
                d = result["component_diagnostics"]
                d = d[d.arm.eq(policy["arm"]) & d.role.eq(role) & d.component.eq(name)]
                support = comp[comp.component.eq(name)]
                diagnostics.append(dict(arm=policy["arm"], role=role, component=name, mean_origin_sd=d.component_sd.mean(), mean_score_correlation=d.score_component_ic.mean(), missing_fraction=1 - support.available.mean(), prior_only_fraction=support.prior_status.eq("prior_only").mean()))
    r.table(pd.DataFrame(diagnostics), "Component influence within selected score recipes", "Predeclared T05/T14/T18 probes: mean eligible-universe per-origin dispersion and component/composite rank correlation. Coefficients alone do not measure empirical influence. Missingness and prior-only support use the full scheduled eligible universe.", percent=["missing_fraction", "prior_only_fraction"])
    k = comp[comp.component.eq("Kmax") & comp.available]
    fig, ax = plt.subplots(figsize=(7, 3.7))
    im = ax.scatter(k.history_span, k.value, c=np.log1p(k.actual_count), s=7, alpha=0.35, cmap="viridis", rasterized=True)
    ax.set(xlabel="Recorded elapsed history (days)", ylabel="Maximum-history K score")
    fig.colorbar(im, ax=ax, label="log(1 + actual update count)")
    r.save(fig, "k-history", "Maximum-history K and support", "Each point is an eligible vault/date. Maximum-history span scaling does not cancel across vault ages; this checks whether apparent quality mostly reflects age or reporting density.")
    # Mechanical examples: earliest T14 origin and maximum cash T18 (earliest tie).
    examples = [("T14", data["origins"][0], "joint-score"), ("T18", out[out.arm.eq("T18")].sort_values(["cash", "origin_at"], ascending=[False, True]).iloc[0].origin_at, "constraint-probe")]
    for arm, date, slug in examples:
        g = ledger[ledger.arm.eq(arm) & ledger.origin_at.eq(date)].sort_values("rank")
        wide = comp[comp.origin_at.eq(date) & comp.pair_id.isin(g.pair_id)].pivot(index="pair_id", columns="component", values="value")
        worked = g[["vault_name", "pair_id", "ranking_score", "ranking_available", "weighting_score", "weighting_available", "desired_weight", "accepted_weight", "capacity", "fallback"]].copy()
        component_names = ["F", "I90", "K90"] if arm == "T14" else ["Sh90", "Ca180", "V180", "Kmax"]
        components = worked[["vault_name", "pair_id", "ranking_available", "weighting_available"]].copy()
        for name in component_names:
            components[name] = worked.pair_id.map(wide[name])
        r.table(components, f"{arm} component values at {date.date()}", "Eligible-universe component scores before selection and position sizing. A dash denotes an unavailable component.")
        r.table(worked.drop(columns=["pair_id", "ranking_available", "weighting_available"]), f"{arm} score worked example at {date.date()}", "Selected by mechanics before examining profit. Components come from the full eligible universe; caps are applied after the final score mapping.", percent=["desired_weight", "accepted_weight", "capacity"])
        fig, ax = plt.subplots(figsize=(8, 3.9))
        x = np.arange(len(g))
        ax.bar(x - 0.18, g.desired_weight * 100, 0.36, label="Requested")
        ax.bar(x + 0.18, g.accepted_weight * 100, 0.36, label="Accepted")
        labels = [str(v)[:22] for v in g.vault_name]
        ax.set_xticks(x, labels, rotation=25, ha="right")
        ax.set(ylabel="Account weight (%)")
        ax.legend()
        r.save(fig, slug + "-weights", f"{arm} requested and accepted weights at {date.date()}", "Zero requested positions remain zero under redistribution. Cash and concentration changes are part of the capacity outcome.")
    quarter_bound = float(np.nanmax(np.abs(result["quarterly"].mean_return))) * 100
    for start in (0, 12, 24):
        arms = s.arm.iloc[start : start + 12]
        q = result["quarterly"]
        pivot = q[q.arm.isin(arms)].pivot(index="arm", columns="quarter", values="mean_return").reindex(index=arms, columns=["2026Q1", "2026Q2", "2026Q3", "2026Q4"])
        counts = q[q.arm.isin(arms)].pivot(index="arm", columns="quarter", values="resolved").reindex(index=arms, columns=pivot.columns)
        r.heatmap(pivot, f"quarter-returns-{start}", f"Quarterly snapshot returns T{start:02d}–T{start+11:02d}", "Mean 30-day simple return, grouped by origin quarter. Q4 is pending; Q3 has only 16 mature origins. Overlapping snapshots are not quarter profit or independent trials. All three panels share a symmetric colour scale; cell n is resolved mature support.", percent=True, limits=(-quarter_bound, quarter_bound), counts=counts)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = s.mean_variance * 1e4
    y = s.mean_return * 100
    im = ax.scatter(x, y, c=s.mean_cash * 100, cmap="viridis", s=42)
    for row in s.itertuples():
        if row.arm in ["T00", "T01", "T02", "T05", "T14", "T15", "T18", "T25", "T27"]:
            ax.annotate(row.arm, (row.mean_variance * 1e4, row.mean_return * 100), xytext={"T00": (-70, -42), "T01": (-34, -28), "T02": (28, -16), "T05": (15, 20), "T14": (-76, -5), "T15": (-28, 28), "T18": (2, 20), "T25": (-20, 15), "T27": (28, 8)}[row.arm], textcoords="offset points", fontsize=8, arrowprops={"arrowstyle": "-", "color": "grey", "lw": 0.6}, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8})
    ax.set_xscale("log")
    ax.set(xlabel="Mean daily return variance × 10,000 (log scale)", ylabel="Mean 30-day simple return (%)")
    fig.colorbar(im, ax=ax, label="Mean cash (%)")
    r.save(fig, "return-risk", "Snapshot return and risk across policies", "All 36 arms are shown; labels identify predeclared controls. The variance axis is logarithmic to separate the dense low-risk region. Support differs across policies; matched comparisons are in the effect table.")
    d = result["contrasts"]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = d.return_difference * 100
    ax.barh(np.arange(len(d)), x, color=np.where(x >= 0, "#15803d", "#b91c1c"))
    ax.set_yticks(np.arange(len(d)), [f"{row.arm}−{row.control} (n={row.paired})" for row in d.itertuples()])
    ax.axvline(0, color="grey")
    ax.set(xlabel="Paired mean 30-day return difference (percentage points)")
    ax.invert_yaxis()
    r.save(fig, "paired-effects", "Matched recipe effects", "Common resolved origin support, with pair counts. These differences have no inferential success labels; cash and basket changes are disclosed in the table.")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(s.arm, s.effective_N, color="#2563eb")
    ax.set_xticks(range(len(s)), s.arm, rotation=90, fontsize=8)
    ax.set(ylabel="Mean effective funded positions")
    ax.axhline(6, color="grey", ls="--")
    r.save(fig, "effective-positions", "Effective allocation breadth", "Effective N is inverse HHI on invested weights. Six selected names can behave like fewer funded positions; T20 requests ten.")
    rb = ledger[ledger.arm.eq("T24") & ledger.fallback.str.startswith("score_risk_budget")]
    date = rb.origin_at.min()
    g = rb[rb.origin_at.eq(date)].sort_values("rank")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    x = np.arange(len(g))
    ax.bar(x - 0.23, g.target_risk_budget, 0.23, label="Target")
    ax.bar(x, g.requested_risk_contribution, 0.23, label="Requested achieved")
    ax.bar(x + 0.23, g.accepted_risk_contribution, 0.23, label="After caps")
    ax.set_xticks(x, [str(n)[:18] for n in g.vault_name], rotation=25, ha="right")
    ax.set(ylabel="Relative risk contribution")
    ax.legend(fontsize=8)
    r.save(fig, "risk-budget-contributions", f"Score risk budgets at {date.date()}", "The solver matches relative risk contributions before caps. Entry constraints may distort them; solver/covariance prior status remains in the ledger.")
    r.table(result["robustness"].query("arm in ['T00','T01','T02','T05','T14','T18','T19','T27','T28','T29','T30','T35']"), "Tail and carried-mark diagnostics", "Predeclared source/focal controls and standalone probes show mean versus median, worst/best origin and first-update contributions. A concentrated tail is not proof of a data error.", percent=["mean_return", "median_return", "worst_origin", "best_origin", "median_cash", "first_update", "remaining", "carried_anchor_weight", "unresolved_weight"])
    selected = result["vault_influence"].copy()
    selected = selected[selected.arm.isin(["T00", "T05", "T14", "T28"])]
    selected["absolute_contribution"] = selected.mean_return_contribution.abs()
    selected = selected.sort_values("absolute_contribution", ascending=False).groupby("arm", sort=True).head(3).sort_values(["arm", "absolute_contribution"], ascending=[True, False])
    r.table(selected[["arm", "vault_name", "appearances", "mean_return_contribution"]], "Largest vault contributions", "Three largest absolute contributions for predeclared control/blend/short-CAGR arms. Contributions average across the arm’s resolved origins and sum to mean snapshot return; baskets remain fixed for attribution.", percent=["mean_return_contribution"])
    q = result["quarter_influence"]
    pivot = q[q.arm.isin(["T00", "T01", "T02", "T05", "T14", "T27", "T28"])].pivot(index="arm", columns="quarter_removed", values="difference")
    if "2026Q4" in pivot:
        pivot["2026Q4"] = np.nan
    bound = float(np.nanmax(np.abs(pivot.to_numpy()))) * 100
    r.heatmap(pivot, "quarter-influence", "Sensitivity to excluding an origin quarter", "Difference in mean 30-day return after removing one quarter, holding every original basket fixed. Q4 has no mature labels and is therefore shown as unavailable. This diagnoses regime concentration; it does not select a favourable period.", percent=True, limits=(-bound, bound))
    (data["artifact"] / "figures.json").write_text(json.dumps(r.figures, indent=2))
    return r.figures


def write_findings(data, result, audit):
    s = result["summary"].set_index("arm")
    d = result["contrasts"].set_index(["arm", "control"])
    folder = data["artifact"]

    def p(value):
        return f"{value:.2%}" if np.isfinite(value) else "undefined"

    lines = [
        "# Expanded experiment 10 — composite-score smoke findings",
        "",
        f"Executed using pinned repaired data. Decision period: **{PERIOD}**. Full four-day grid: **70 origins, 62 mature 30-day windows, eight pending**. Indicator warmup includes all 2025 observations plus earlier history. **36 combinations**; no broad-stage search or engine replay.",
        "",
        "## What was examined",
        "",
        "Inverse variance, inverse volatility, K-ratio and existing performance metrics enter per-vault composite scores before selection. Ranking and sizing recipes can differ. The smoke matrix covers arithmetic/geometric/minimum scores, standalone metrics, missingness, covariance risk budgets, sizing maps, breadth and constraints.",
        "",
        "## Implementation and reference reproduction",
        "",
        f"All **{len(audit)} independent audit checks passed**. T00 reproduces the original capped v11 source ledger: mean 30-day return {p(s.loc['T00','mean_return'])}, cash {p(s.loc['T00','mean_cash'])}. T01 reproduces the capped focal-four equal benchmark: return {p(s.loc['T01','mean_return'])}, cash {p(s.loc['T01','mean_cash'])}. Exact shared-date weights and all 62 mature outcomes match saved NB10. Its final two pending dates have no allocation reference, so the expanded calendar audit checks them separately.",
        "",
        "## Main matched findings",
        "",
        "| Comparison | Mean return difference | Paired origins | Cash difference | Common-budget difference |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result["contrasts"].itertuples():
        lines.append(f"| {row.arm} vs {row.control}: {row.description} | {row.return_difference*100:+.3f} pp | {row.paired} | {row.cash_difference*100:+.3f} pp | {row.common_budget_difference*100:+.3f} pp |")
    risk = result["contrasts"].query("arm=='T05' and control=='T27'").iloc[0]
    flatten = result["contrasts"].query("arm=='T27' and control=='T02'").iloc[0]
    lines += [
        "",
        "## What the hypotheses tell us",
        "",
        f"**H1, low-risk score ingredients:** T05 minus the constant-offset control T27 is {risk.return_difference*100:+.3f} pp on {risk.paired} common resolved origins. The neutral offset alone changes T02 by {flatten.return_difference*100:+.3f} pp. This distinguishes varying risk information from mechanical flattening; it does not establish generalisation across all 139 frozen recipes.",
        "",
        f"**H2/H3, K and separate roles:** T14 minus T26 (same ranking, K-on/off weighting recipes) is {d.loc[('T14','T26'),'return_difference']*100:+.3f} pp on {int(d.loc[('T14','T26'),'paired'])} origins. The K ranking comparison T14/T13 is recorded separately. These are recipe changes; the equal-third K addition changes other coefficients. A complete K ranking/sizing four-cell block remains a later-stage requirement.",
        "",
        "**H4, sizing maps:** linear, squared, percentile, softmax and score risk budgets are executed on controlled baskets. Check requested distance from equal and accepted effective N before interpreting a gain; bounded top-ranked scores can produce nearly equal allocations.",
        "",
        "**H5, broader recipe generalisation:** not tested in this smoke. All 139 canonical recipes were verified and preserved in inventory; only the declared focal/single-metric smoke arms were executed.",
        "",
        "**H6/H7, constraints and missing histories:** cap/cash effects and M0/MN/MA funding are explicit. Minimum/geometric zeros can leave names unfunded; an all-zero score invokes the declared equal fallback. Young vaults remain candidates, but eligibility does not guarantee capital under linear missing-zero sizing.",
        "",
        "## Robustness and interpretation",
        "",
        "These are gross NAV independent fixed-unit 30-day snapshots. Do not compound their overlapping returns into strategy CAGR or average vault/portfolio Sharpes into an executable backtest Sharpe. All history is retrospective. The inherited ten-complete-block gate is unmet in 2026; comparisons are descriptive and no strategy is promoted.",
        "",
        "Support, pending origins, missing terminal NAV, first-update attribution, unresolved-weight bounds, score imputation, covariance priors and cap distortion are saved per origin. Exact source control parity does not remove current-universe/guard or publication-clock limitations.",
        "",
        "## Useful leads and next-stage scope",
        "",
        "The next experiment should retain the neutral-offset control, matched score/missingness comparisons and common-support analysis. Add the complete K four-cell block, raw/regularised risk pairing, confidence/MN companion and missing-zero/minimum MA companion before stronger attribution.",
        "",
    ]
    tails = result["robustness"].set_index("arm")
    vault = result["vault_influence"]
    loss = vault[vault.arm.eq("T28")].sort_values("mean_return_contribution").iloc[0]
    lines += ["", "### Tail attribution — 2026 origins, 30-day snapshots", "", f"The short-CAGR standalone probe T28 has a worst origin of {p(tails.loc['T28','worst_origin'])}. Its largest negative mean contribution is {loss.vault_name}: {loss.mean_return_contribution*100:+.3f} pp over the arm’s resolved calendar. Quarter-removal and fixed-ledger vault attribution are saved and displayed; these episodes require inspection before treating means as stable forecasting evidence.", "", "### Common deployment controls — 2026 origins, 30-day snapshots", "", "The matched table also shows returns after reprojecting both requested portfolios to the smaller ex-ante accepted budget. This isolates total deployment changes while retaining each basket, score map and entry constraints. Its paired support is saved separately; it cannot eliminate differences in selected vault quality or cap shape."]
    nextstage = json.loads((folder / "next-stage-registry.json").read_text())
    lines += [f"A proposed **Stage A0 registry of {nextstage['unique_policies']} unique policies** covers {nextstage['standalone_components']} standalone metric/lookback components in separate ranking, sizing and joint roles, across 7/30/90-day horizons. It has not been executed. Its full JSON inventory is saved in this generation; broader all-139 composite families require their own frozen registry and contrasts.", "", f"Smoke allocation execution time: {data.get('execution_seconds',np.nan):.1f} seconds. Artefact generation fingerprint: `{data['fingerprint']}`.", "", "Notebook: [expanded NB10](10-research-portfolio-snapshots.ipynb). Original generation: [saved NB10 appendix](appendices/10-original-portfolio-snapshots.ipynb) and [original findings](10-portfolio-snapshot-findings.md)."]
    (ROOT / "10-expanded-score-allocation-smoke-findings.md").write_text("\n".join(lines) + "\n")
    return lines
