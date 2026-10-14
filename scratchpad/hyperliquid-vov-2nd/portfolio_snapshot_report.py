"""Short captions, styled tables and separately saved snapshot figures."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, SymLogNorm
from IPython.display import display, Markdown, Image, HTML
from portfolio_snapshot_data import ARTIFACT, ROOT, PERIODS, METHODS, CONFIG
from portfolio_snapshot_statistics import period_frame

PERIOD = "2026-01-01 → 2026-10-05 (end exclusive, UTC)"
NAMES = {"v11": "v11", "blend_46d": "Blend 46d", "focal_four": "Four-input focal"}
FIGURES = []


def intro(title, description, h=30, period=PERIOD):
    horizon_label = f"{h}-day horizon" if str(h).replace("/", "").isdigit() else str(h)
    display(Markdown(f"### {title} — {period}; {horizon_label}\n\n{description}"))


def table(frame, title, description, h=30, period=PERIOD):
    intro(title, description, h, period)
    frame = frame.copy()
    if frame.empty:
        display(Markdown("Unsupported: no observations meet this comparison’s declared support."))
        return
    numeric = frame.select_dtypes("number").columns
    percentage_columns = {"mean_return", "median_return", "return", "weighting_lift", "selection_lift", "mean_cash", "cash", "max_weight", "unresolved_weight", "first_update_lift", "remaining_lift", "mean_drawdown", "drawdown", "drawdown_lift", "desired_weight", "accepted_weight", "benchmark_weight", "capacity", "carried_anchor_weight", "carried_endpoint_weight", "no_update_weight", "fallback_fraction", "weak_prior_share", "target_coverage", "mean_contribution", "return_low", "return_high", "mean_low", "mean_high", "mean_target_variation", "mean_jaccard", "win_fraction", "fraction_null_above", "monte_carlo_se", "observed_lift", "null_low", "null_high"}
    styled = frame.style.format({c: "{:.2%}" if c in percentage_columns else "{:.3g}" for c in numeric}, na_rep="—")
    for c in numeric:
        if frame[c].notna().any():
            styled = styled.background_gradient(subset=[c], cmap="YlGnBu")
    display(styled.hide(axis="index"))


def save(fig, slug, title, h=30, period=PERIOD):
    horizon_label = f"{h}-day horizon" if str(h).replace("/", "").isdigit() else str(h)
    fig.suptitle(f"{title}\n{period}; {horizon_label}", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    folder = ARTIFACT / "figures"
    folder.mkdir(exist_ok=True)
    path = folder / (slug + ".png")
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    FIGURES.append(dict(file=str(path), title=title, period=period, horizon=h))
    display(Image(filename=str(path)))


def heatmap(frame, x, y, value, title, description, slug, h=30, diverging=False, percent=False, logdiff=False, limits=None):
    support_col = next((c for c in (("universe_resolved",) if value == "selection_lift" else ("ic_origins", "origins") if value in ("risk_ic", "ic") else ("paired_origins", "resolved_origins", "origins")) if c in frame), None)
    if support_col and len(frame):
        description += f" Cell support: {int(frame[support_col].min())}–{int(frame[support_col].max())} origins;2026 estimates are descriptive under the ten-block gate."
    intro(title, description, h)
    if frame.empty:
        display(Markdown("Unsupported: no rows."))
        return
    pivot = frame.pivot_table(index=y, columns=x, values=value, aggfunc="mean", dropna=False)
    a = pivot.to_numpy(float)
    plot_a = a * (100 if percent else 1)
    finite = plot_a[np.isfinite(plot_a)]
    fig, ax = plt.subplots(figsize=(max(6, 1.1 * len(pivot.columns)), max(3, 0.5 * len(pivot) + 1.3)))
    cmap = plt.get_cmap("RdBu_r" if diverging else "viridis").copy()
    cmap.set_bad("#dddddd")
    norm = None
    if diverging and len(finite):
        bound = max(float(np.abs(finite).max()), 1e-12) if limits is None else limits * (100 if percent else 1)
        if value in ("risk_ic", "ic"):
            bound = 1.0
        norm = SymLogNorm(1.0, vmin=-bound, vmax=bound) if logdiff else TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)
    if not diverging and limits is not None:
        from matplotlib.colors import Normalize

        norm = Normalize(vmin=0, vmax=limits)
    ax.grid(False)
    im = ax.imshow(np.ma.masked_invalid(plot_a), cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), [f"{float(c):.0%}" if x == "cap" else str(c) for c in pivot.columns])
    ax.set_yticks(range(len(pivot)), [NAMES.get(str(i), str(i)) for i in pivot.index])
    labels = {"h": "Forecast horizon (days)", "L": "Risk lookback (days)", "p": "Inverse-risk power p", "N": "Requested positions", "account": "Fresh account (USD)", "cap": "Account concentration cap", "spacing_days": "Observation spacing (days / empirical pattern)"}
    ax.set_xlabel(labels.get(x, x.replace("_", " ")))
    ax.set_ylabel(labels.get(y, y.replace("_", " ")))
    for i in range(len(pivot)):
        for j in range(len(pivot.columns)):
            v = a[i, j]
            label = "—" if not np.isfinite(v) else f"{v*100:+.2f} pp" if percent and diverging else f"{v*100:.1f}%" if percent else f"{v:.2g}"
            rgba = im.cmap(im.norm(v * (100 if percent else 1))) if np.isfinite(v) else (1, 1, 1, 1)
            brightness = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            ax.text(j, i, label, ha="center", va="center", fontsize=9, color="black" if brightness > 0.55 else "white")
    colour_labels = {"risk_ic": "Spearman risk IC", "ic": "Spearman IC", "qlike_delta": "QLIKE difference (symlog)", "calibration_ratio": "Predicted / realised (ideal=1)", "variance_lift": "Daily variance difference", "mean_cash": "Initial cash (%)", "drawdown_lift": "Drawdown difference (pp)", "weighting_lift": "Return difference (pp)", "selection_lift": "Selection lift (pp)"}
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label(colour_labels.get(value, value.replace("_", " ")), fontsize=9)
    cb.ax.tick_params(labelsize=8)
    save(fig, slug, title, h)


def derived_diagnostics(data, risk, result):
    p = result["policies"]
    out = period_frame(result["outcomes"], h=30)
    controls = p[p.N.eq(6) & p.L.eq(90) & p.p.eq(2) & p.estimator.eq("regularised") & p.variant.eq("main") & p.branch.eq("pure")]
    base = out[out.policy_id.isin(controls.policy_id)].merge(controls[["policy_id", "score"]], on="policy_id")
    quarter = base.assign(quarter=base.origin_at.dt.to_period("Q").astype(str)).groupby(["score", "quarter"]).agg(weighting_lift=("weighting_lift", "mean"), resolved=("resolved", "sum"), unresolved_weight=("unresolved_weight", "mean")).reset_index()
    phases = period_frame(result["outcomes"], h=30, phase=None).merge(p, on="policy_id")
    phases = phases[phases.N.eq(6) & phases.L.eq(90) & phases.p.eq(2) & phases.estimator.eq("regularised") & phases.variant.eq("main") & phases.branch.eq("pure")].groupby(["score", "phase"]).agg(mean_return=("return", "mean"), weighting_lift=("weighting_lift", "mean"), variance_lift=("variance_lift", "mean"), resolved=("resolved", "sum")).reset_index()
    influence = []
    vault_influence = []
    for score, g in base.groupby("score"):
        g = g[np.isfinite(g.weighting_lift)]
        point = g.weighting_lift.mean()
        for q in g.origin_at.dt.to_period("Q").unique():
            z = g[g.origin_at.dt.to_period("Q") != q]
            influence.append(dict(score=score, omitted_quarter=str(q), remaining_origins=len(z), weighting_lift=z.weighting_lift.mean(), change=z.weighting_lift.mean() - point))
        policy = controls[controls.score.eq(score)].policy_id.iloc[0]
        a = result["allocations"]
        a = a[a.policy_id.eq(policy) & a.origin_at.isin(g.origin_at)]
        for t, ga in a.groupby("origin_at"):
            from portfolio_snapshot_data import future_panel

            target = future_panel(data, t, 30, ga.pair_id.to_numpy())
            active = ga.accepted_weight.to_numpy() - ga.benchmark_weight.to_numpy()
            for pid, delta, ret in zip(ga.pair_id, active, target["returns"]):
                vault_influence.append(dict(score=score, origin_at=t, pair_id=pid, contribution=delta * ret))
    vf = pd.DataFrame(vault_influence)
    if len(vf):
        denominator = base.groupby("score").weighting_lift.count()
        vf = vf.groupby(["score", "pair_id"]).contribution.sum().reset_index()
        vf["mean_contribution"] = vf.contribution / vf.score.map(denominator)
        vf = vf.merge(data["identities"], on="pair_id", validate="many_to_one")
    # Horizon-spaced origins sampled from the original phase; no post-hoc favourable offset.
    spaced = []
    for score, g in base.groupby("score"):
        g = g.sort_values("origin_at")
        last = pd.Timestamp.min
        chosen = []
        for row in g.itertuples():
            if row.origin_at >= last and np.isfinite(row.weighting_lift):
                chosen.append(row.weighting_lift)
                last = row.origin_at + pd.Timedelta(days=30)
        spaced.append(dict(score=score, h=30, origins=len(chosen), weighting_lift=np.mean(chosen) if chosen else np.nan, definition="first supported origin then ≥30 days apart; one fixed phase"))
    # Continuous as-of history support, not arbitrary exclusion thresholds.
    quality = period_frame(risk, phase=None) if "phase" in risk else risk[risk.origin_at.between(PERIODS["2026"][0], PERIODS["2026"][1], inclusive="left")]
    quality = quality[quality.L.eq(90)].copy()
    quality["age_quantile"] = pd.qcut(quality.history_age.rank(method="first"), 5, labels=False) + 1
    quality["quality_quantile"] = pd.qcut(quality.actual_fraction.rank(method="first"), 5, labels=False) + 1
    return dict(quarters=quarter, phases=phases, quarter_influence=pd.DataFrame(influence), vault_influence=vf, spaced=pd.DataFrame(spaced), quality=quality)


def render_report(data, risk, result, audit):
    global FIGURES
    FIGURES = []
    plt.rcParams.update({"font.size": 10, "axes.labelsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9, "axes.titlesize": 11})
    s = result["summaries"]
    short = s[s.period.eq("2026") & s.h.eq(30)]
    rs = result["risk_summary"]
    diag = derived_diagnostics(data, risk, result)
    for key, f in diag.items():
        f.to_parquet(ARTIFACT / f"{key}.parquet", index=False)
    table(pd.DataFrame([{"Input": k, "SHA-256": v["sha256"]} for k, v in data["downloads"].items() if isinstance(v, dict) and "sha256" in v]), "Pinned inputs", "The archive and metadata hashes are verified before calculations. Full source/framework fingerprints and every modelling choice are saved in the manifest.")
    table(pd.DataFrame({"Choice": list(CONFIG), "Value": [str(v) for v in CONFIG.values()]}).head(15), "Declared assumptions", "These are frozen design choices and numerical conventions, not learned optimal parameters. The complete register is available in the expandable element below.")
    display(HTML("<details><summary>Complete configuration and source limitations — " + PERIOD + "</summary>" + pd.DataFrame({"Choice": list(CONFIG), "Value": [str(v) for v in CONFIG.values()]}).to_html(index=False) + "<p>Current inventory/guard snapshots are applied retrospectively. Written-at is not an observation clock. Source eligibility is compatible with the replay, not proven contemporaneously known.</p></details>"))
    pop = period_frame(result["population"])
    population = pop.groupby("h").agg(origins=("origin_at", "size"), vault_date_rows=("candidates", "sum"), supported_target_rows=("target_supported", "sum"), actual_anchor_rows=("actual_anchor", "sum"), actual_endpoint_rows=("actual_endpoint", "sum")).reset_index()
    population["target_coverage"] = population.supported_target_rows / population.vault_date_rows
    calendar = data["origins"]
    calendar = calendar[calendar.phase.eq(0) & calendar.origin_at.between(PERIODS["2026"][0], PERIODS["2026"][1], inclusive="left")]
    admin = pd.DataFrame([dict(horizon_days=h, scheduled_origins=len(calendar), administratively_mature_origins=int((calendar.origin_at + pd.Timedelta(days=h) <= PERIODS["2026"][1]).sum()), unmatured_origins=int((calendar.origin_at + pd.Timedelta(days=h) > PERIODS["2026"][1]).sum())) for h in (7, 30, 90)])
    table(admin, "Administrative label maturity", "Late scheduled origins remain in the origin/selection ledger but cannot have completed future labels inside the archive boundary. Evaluation population denominators below include only administratively mature origins.", h="7/30/90")
    table(population, "Population and outcome coverage", "Denominators are eligible vault/date rows, not only the selected basket. A carried NAV is usable for valuation but is not a new independent observation.", h="7/30/90")
    controls = short[short.N.eq(6) & short.L.eq(90) & short.p.isin([0, 1, 2]) & short.estimator.isin(["equal", "raw", "regularised", "source"]) & short.branch.eq("pure") & short.variant.isin(["main", "source_candle_control"])]
    table(controls[["score", "estimator", "p", "mean_return", "mean_variance", "weighting_lift", "resolved_origins", "origins", "unresolved_weight", "fallback_fraction", "unscored_selected"]], "Six-position reference outcomes", "Mean simple 30-day returns and daily path variances describe independent snapshots. Weighting lift compares the same selected basket and budget with equal weights; no strategy CAGR is inferred.")
    risk_state = risk[(risk.origin_at >= PERIODS["2026"][0]) & (risk.origin_at < PERIODS["2026"][1]) & risk.L.eq(90)].copy()
    risk_state["empirical_status"] = risk_state.status
    risk_state["status"] = np.where(risk_state.empirical.isna() & risk_state.regularised.notna(), "prior_only", risk_state.status)
    risk_state["phase"] = (risk_state.origin_at - PERIODS["2026"][0]).dt.days % 4
    risk_state = risk_state[risk_state.phase.eq(0)]
    state = risk_state.groupby("status").agg(rows=("pair_id", "size"), median_actual_updates=("m", "median"), median_calendar_returns=("n", "median"), median_history_age=("history_age", "median"), weak_prior_share=("prior_weak", "mean")).reset_index()
    table(state, "Available risk history", "Rows are eligible vault/date observations for the 90-day window on phase zero. Actual updates m determine shrinkage support; calendar returns n do not manufacture observations.")
    eligible_rs = rs[rs.period.eq("2026") & rs.cohort.eq("eligible") & rs.L.eq(90) & rs.score.eq("v11")]
    heatmap(eligible_rs, "h", "estimator", "risk_ic", "Risk ordering across the eligible universe", "StageR evaluates every eligible vault, including missing composite scores. Equal-date risk IC is conditional on observed finite risk targets. Eligible membership is common to all frozen scores; one nonduplicated panel is shown.", "risk-eligible-ic", h="7/30/90", diverging=True)
    table(rs[rs.period.eq("2026") & rs.h.eq(30) & rs.L.eq(90)][["cohort", "score", "estimator", "risk_ic", "qlike_delta", "calibration_ratio", "paired_origins", "paired_rows"]], "Eligible versus selected risk forecasts", "Selected rows use the exact frozen top-six basket, where weighting operates. Risk accuracy and support may change at the selection boundary; the eligible panels are common to all three scoring methods.")
    for value, title, description, div in [("risk_ic", "Risk ordering", "Equal-date Spearman correlation with future daily variance; higher is stronger risk ordering. Grey cells lack computable support.", True), ("qlike_delta", "Risk forecast loss versus peer prior", "Paired QLIKE differences use identical vault/date targets; negative is better. The symmetric log colour scale exposes extreme floor errors without clipping them.", True), ("calibration_ratio", "Risk level calibration", "Ratio of equal-date predicted to realised mean variance. One indicates matching mean risk levels; zero realised variance remains zero and no epsilon is added.", False)]:
        for score in METHODS:
            f = rs[rs.period.eq("2026") & rs.h.eq(30) & rs.cohort.eq("selected") & rs.score.eq(score)]
            heatmap(f, "L", "estimator", value, f"{title}: {NAMES[score]} top six", description, f"risk-{value}-{score}", diverging=div, logdiff=value == "qlike_delta", limits=float(np.nanmax(np.abs(rs.loc[rs.period.eq("2026") & rs.h.eq(30) & rs.cohort.eq("selected"), value]))) if div else max(1.0, float(np.nanmax(rs.loc[rs.period.eq("2026") & rs.h.eq(30) & rs.cohort.eq("selected"), "calibration_ratio"]))) if value == "calibration_ratio" else None)
    table(rs[rs.period.eq("2026") & rs.h.eq(30) & rs.cohort.eq("selected") & rs.L.eq(90)][["score", "estimator", "paired_origins", "paired_rows", "risk_ic", "qlike_delta", "qlike_median", "win_fraction", "tail_absolute_share", "tail_signed_contribution"]], "Risk loss concentration", "Each origin has equal weight. The largest 5% of absolute weighted row loss differences show tail sensitivity; they are retained in all primary means. A positive loss difference favours the peer prior.")
    intro("Thirty-day selected risk calibration", "Points are equal-date mean predicted and realised daily variance for six-vault regularised forecasts. Log axes are used only on positive values; zero targets are excluded from this plot, retained in loss tables.")
    re = period_frame(result["risk_evaluation"], h=30)
    re = re[re.selected & re.estimator.eq("regularised") & re.L.eq(90)]
    fig, ax = plt.subplots(figsize=(7, 5))
    for score, g in re.groupby("score"):
        z = g.groupby("origin_at")[["predicted", "realised"]].mean()
        z = z[np.isfinite(z.predicted) & np.isfinite(z.realised) & z.predicted.gt(0) & z.realised.gt(0)]
        ax.scatter(z.predicted, z.realised, label=NAMES[score], alpha=0.65, s=24)
    ax.set_xscale("log")
    ax.set_yscale("log")
    lo = min(ax.get_xlim()[0], ax.get_ylim()[0])
    hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([lo, hi], [lo, hi], color="grey", ls="--", label="Matching levels")
    ax.set_xlabel("Predicted daily variance")
    ax.set_ylabel("Realised daily variance")
    ax.legend(fontsize=8)
    save(fig, "calibration-scatter", "Selected basket marginal-risk calibration")
    for target, title in [("return", "Score versus future return IC"), ("sharpe", "Score versus future vault Sharpe IC")]:
        ic = period_frame(result["score_ic"])
        ic = ic[ic.target.eq(target)].groupby(["score", "h"]).agg(ic=("ic", "mean"), origins=("ic", "count"), mean_pairs=("n", "mean")).reset_index()
        heatmap(ic, "h", "score", "ic", title, "Equal-date finite-pair Spearman correlations describe the observed-outcome association. Missing scores and outcomes are omitted from IC, but retained in portfolio selection/attrition.", f"score-ic-{target}", h="7/30/90", diverging=True)
        table(ic, "IC support: " + target, "Origin count is the number of computable cross-sections; pair count varies by date. Overlapping horizons are dependent.", h="7/30/90")
    ic = period_frame(result["score_ic"], h=30)
    gates = []
    for gate in (3, 5, 10, 20):
        for score, g in ic[ic.target.eq("return") & ic.n.ge(gate)].groupby("score"):
            gates.append(dict(score=score, minimum_pairs=gate, mean_ic=g.ic.mean(), origins=g.ic.notna().sum()))
    table(pd.DataFrame(gates), "Cross-section support sensitivity", "The 3/5/10/20 finite-pair gates are descriptive support checks, not significance thresholds.")
    equal = short[short.estimator.eq("equal") & short.branch.eq("pure") & short.variant.eq("main")]
    heatmap(equal, "N", "score", "selection_lift", "Strict universe-reference selection lift", "Positive means selected equal weights beat the entire ex-ante eligible equal universe. Only fully resolved eligible universes qualify; grey means unsupported, never survivor-only replacement.", "selection-lift", diverging=True, percent=True)
    table(equal[["score", "N", "selection_lift", "universe_resolved", "resolved_origins", "unresolved_weight"]], "Strict selection support", "The whole eligible-universe benchmark can lose support even when a small selected basket resolves. This stricter estimand is secondary to matched-basket weighting.")
    for score in METHODS:
        for est in ("raw", "regularised"):
            z = short[short.score.eq(score) & short.estimator.eq(est) & short.N.eq(6) & short.variant.eq("main") & short.branch.eq("pure")]
            # Equal weights have one semantic policy; show them at each L as a labelled benchmark alias.
            eq = equal[equal.score.eq(score) & equal.N.eq(6)]
            aliases = pd.concat([eq.assign(L=L, p=0) for L in (30, 60, 90, 180)], ignore_index=True)
            z = pd.concat([z, aliases])
            for val, title, desc, pct in [("weighting_lift", "Mean weighting return lift", "Percentage-point simple-return difference from equal weights on exactly the same basket. Positive is higher return.", True), ("variance_lift", "Daily portfolio variance difference", "Daily simple-return variance difference from equal weights. Negative is lower observed path risk; no annualised strategy Sharpe is inferred.", False), ("drawdown_lift", "Snapshot drawdown difference", "Signed maximum-drawdown difference from equal weights. Positive is less severe drawdown on the fixed-unit path.", True)]:
                heatmap(z, "L", "p", val, f"{title}: {NAMES[score]}, {est}, N=6", desc + " Equal row is a display alias of one deduplicated policy.", f"weight-{score}-{est}-{val}", diverging=True, percent=pct, limits=float(np.nanmax(np.abs(short.loc[short.N.eq(6) & short.variant.eq("main") & short.branch.eq("pure") & short.estimator.isin(["raw", "regularised"]), val]))))
    intro("Construction return/risk trade-off", "Each point is one six-vault 90-day policy. X is the square root of mean daily path variance, annualised for scale; Y is mean 30-day simple return. These are snapshot outcomes, not backtest CAGR/Sharpe.")
    fig, ax = plt.subplots(figsize=(8, 5))
    point_rows = []
    points = {}
    colours = dict(zip(METHODS, ["#3876b8", "#d78329", "#33835a"]))
    for row in controls.itertuples():
        x = np.sqrt(row.mean_variance * 365)
        y = row.mean_return * 100
        key = (row.score, round(x, 12), round(y, 12))
        if key not in points:
            label = f"P{len(points)+1:02d}"
            points[key] = label
            ax.scatter(x, y, s=38, color=colours[row.score])
            ax.annotate(label, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
        point_rows.append(dict(point=points[key], score=row.score, estimator=row.estimator, p=row.p))
    from matplotlib.lines import Line2D

    ax.legend(handles=[Line2D([0], [0], marker="o", linestyle="", color=colours[m], label=NAMES[m]) for m in METHODS], loc="lower right")
    ax.set_xlabel("√mean daily variance × √365")
    ax.set_ylabel("Mean 30-day return (%)")
    ax.grid(alpha=0.2)
    save(fig, "tradeoff", "Six-position construction trade-off")
    table(pd.DataFrame(point_rows), "Trade-off point labels", "Point IDs keep the chart legible. Source and raw controls share a point where their observed outcomes coincide; they are aliases in this chart, not independent evidence.")
    intro("Per-origin trade-off by quarter", "The regularised inverse-variance six-vault control is shown separately by score. Quarter colours reveal whether risk/return relationships change during 2026. Large path outliers remain visible.")
    for score in METHODS:
        intro(f"Quarterly origins: {NAMES[score]}", "Each dot is a fully resolved fixed-unit 30-day snapshot; overlapping origins are dependent.")
        ids = controls[controls.score.eq(score) & controls.estimator.eq("regularised") & controls.p.eq(2)].policy_id
        z = period_frame(result["outcomes"], h=30)
        z = z[z.policy_id.isin(ids) & z.resolved]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for q, g in z.groupby(z.origin_at.dt.to_period("Q").astype(str)):
            ax.scatter(np.sqrt(g.variance * 365), g["return"] * 100, label=q, s=26, alpha=0.7)
        ax.set_xlabel("Snapshot daily volatility × √365")
        ax.set_ylabel("30-day simple return (%)")
        ax.legend(title="Origin quarter", fontsize=8)
        ax.grid(alpha=0.2)
        save(fig, "quarter-scatter-" + score, f"Quarterly return/risk observations: {NAMES[score]}")
    for value, title, description in [("mean_return", "Breadth and mean return", "Lines compare requested position counts on origins where all four preselected baskets resolve, with a common regularised 90-day risk estimator. This matched union avoids an apparent improvement from changing outcome support; legend n reports paired origins."), ("effective_N", "Breadth and effective invested positions", "Effective N = 1/Σq² measures initial concentration. More requested slots do not imply equally spread capital.")]:
        intro(title, description)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        z = short[short.L.eq(90) & short.variant.eq("main") & short.branch.eq("pure") & short.estimator.eq("regularised") & short.p.eq(2)].sort_values("N")
        for score, g in z.groupby("score"):
            if value == "mean_return":
                ledger = period_frame(result["outcomes"], h=30)
                ledger = ledger[ledger.policy_id.isin(g.policy_id)]
                common = ledger.pivot(index="origin_at", columns="policy_id", values="return").dropna()
                means = common.mean()
                g = g.copy()
                g[value] = g.policy_id.map(means)
                label = f"{NAMES[score]} (n={len(common)})"
            else:
                label = NAMES[score]
            ax.plot(g.N, g[value] * (100 if value == "mean_return" else 1), marker="o", label=label, color=colours[score])
        ax.set_xticks([4, 6, 8, 10])
        ax.set_xlabel("Requested positions")
        ax.set_ylabel("Mean 30-day return (%)" if value == "mean_return" else "Mean effective invested positions")
        ax.legend()
        ax.grid(alpha=0.2)
        save(fig, "breadth-" + value, title)
    attr = period_frame(result["breadth_attribution"], h=30)
    attr = attr[attr.estimator.eq("regularised") & attr.p.eq(2)].groupby(["score", "N"]).agg(shared_reweighting=("shared_reweighting", "mean"), new_names=("new_names", "mean"), removed_names=("removed_names", "mean"), total=("total", "mean"), paired_origins=("resolved", "sum")).reset_index()
    table(attr, "Exact breadth attribution versus six positions", "The same-origin difference reconciles to shared-vault reweighting plus added/removed-name contributions at original account notional. Cash contribution is zero in this pure branch.")
    ranks = period_frame(result["ranks"], h=30)
    profile = ranks.groupby(["score", "rank"]).agg(mean_return=("return_value", "mean"), supported=("supported", "sum"), observations=("supported", "size")).reset_index()
    intro("Conditional return by individual selection rank", "Observed-target means at every rank through 20. Missing labels do not move a later vault into a missing rank. These conditional means do not replace fully supported basket returns.")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for score, g in profile.groupby("score"):
        ax.plot(g["rank"], g.mean_return * 100, marker=".", label=NAMES[score], color=colours[score])
    ax.set_xlabel("Frozen selection rank")
    ax.set_ylabel("Observed mean 30-day return (%)")
    ax.set_xticks(range(1, 21))
    ax.legend()
    ax.grid(alpha=0.2)
    save(fig, "rank-profile", "Conditional marginal-rank returns")
    table(result["assignment_pooled"][result["assignment_pooled"].period.eq("2026")][["score", "p", "origins", "observed_lift", "null_low", "null_high", "fraction_null_above", "monte_carlo_se"]], "Concentration-matched assignment placebo", "Exact per-date permutations preserve concentration and have equal-weight mean return. Pooled intervals are a persistent seeded-identity assignment null, not confidence intervals for profitability.")
    intro("Weight assignment versus persistent-identity null", "Points are actual 30-day return lift over equal weights. Bars show the central 95% of 999 coherent random assignments; date overlap is retained by persistent identity priorities.")
    pl = result["assignment_pooled"]
    pl = pl[pl.period.eq("2026")].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, row in pl.iterrows():
        ax.plot([row.null_low * 100, row.null_high * 100], [i, i], color="grey", lw=4)
        ax.scatter(row.observed_lift * 100, i, color="navy", zorder=3)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_yticks(range(len(pl)), [f"{NAMES[r.score]} p{r.p:g}" for r in pl.itertuples()])
    ax.set_xlabel("Mean 30-day return lift (pp)")
    save(fig, "assignment-placebo", "Weight assignment diagnostic")
    table(result["score_null"], "Score assignment null", "A within-date exchangeability null and a pre-origin age/quality stratified sensitivity test ordering. These per-date permutations are not a null for a persistent portfolio policy.")
    capacity = short[short.branch.eq("capacity") & short.variant.isin(["main", "source_capacity_control"])]
    table(capacity[capacity.redistribute & capacity.p.eq(2)][["score", "estimator", "p", "state", "mean_return", "mean_cash", "weighting_lift", "resolved_origins", "unresolved_weight"]], "Capacity and same-budget weighting", "Source-report-only enforces concentration and TVL, while permissive also applies recorded hard caps as an explicit diagnostic. Known-only refuses unknown clocks/state. Missing fields are not zero capacity; unknown-state exclusion is separately labelled.")
    no_red = capacity[~capacity.redistribute & capacity.p.eq(2)][["score", "state", "mean_return", "mean_cash", "weighting_lift", "resolved_origins"]]
    table(no_red, "Original-request allocation without redistribution", "Accepted weights are min(cap,98%×desired weight). Residual remains cash. Weighting lift still uses a bounded equal benchmark at the same accepted budget.")
    surface = short[short.branch.eq("capacity") & short.variant.eq("capacity_surface")]
    for score in METHODS:
        heatmap(surface[surface.score.eq(score)], "account", "cap", "mean_cash", f"Cash after entry caps: {NAMES[score]}", "Fresh account-size/concentration sensitivity with recorded permissive capacity. These are conditional stateless entry allocations, not live deposit guarantees.", f"capacity-{score}", percent=True)
    example_id = capacity[capacity.score.eq("v11") & capacity.variant.eq("main") & capacity.state.eq("permissive") & capacity.p.eq(2) & capacity.redistribute].policy_id.iloc[0]
    example = result["allocations"]
    example = example[example.policy_id.eq(example_id) & example.origin_at.between(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-05"), inclusive="left")]
    # Choose first origin with clipping, a deterministic diagnostic, not a best-return date.
    clips = example[np.abs(example.desired_weight - example.accepted_weight) > 1e-10]
    t = clips.origin_at.min() if len(clips) else example.origin_at.min()
    example = example[example.origin_at.eq(t)].merge(data["identities"], on="pair_id")
    table(example[["vault_name", "desired_weight", "accepted_weight", "benchmark_weight", "capacity", "unknown_state"]], "Desired versus accepted entry weights", f"Example origin {t.date()}: first displayed origin with entry clipping. The equal benchmark shares the accepted total budget; permission/capacity clocks are not filled from price observations.")
    intro("Satellite budget versus ordinary widening", "A fixed six-name core receives 100/90/80% of the invested budget; ranks7–10 receive0/10/20%. Both groups use regularised inverse variance. All points for a score share the same fully resolved union of names/origins; legend n reports support. Dashed levels show ordinary ten-name normalisation, which can allocate a very different satellite share.")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colours = dict(zip(METHODS, ["#3876b8", "#d78329", "#33835a"]))
    for score in METHODS:
        core = short[short.score.eq(score) & short.N.eq(6) & short.variant.eq("main") & short.estimator.eq("regularised") & short.p.eq(2) & short.branch.eq("pure") & short.L.eq(90)].iloc[0]
        sat = short[short.score.eq(score) & short.variant.eq("satellite")].sort_values("satellite")
        wider = short[short.score.eq(score) & short.N.eq(10) & short.variant.eq("main") & short.estimator.eq("regularised") & short.p.eq(2) & short.branch.eq("pure") & short.L.eq(90)].iloc[0]
        ids = [core.policy_id] + sat.policy_id.tolist() + [wider.policy_id]
        ledger = period_frame(result["outcomes"], h=30)
        matched = ledger[ledger.policy_id.isin(ids)].pivot(index="origin_at", columns="policy_id", values="return").dropna()
        means = matched.mean()
        ax.plot([0] + sat.satellite.tolist(), [means[core.policy_id] * 100] + [means[i] * 100 for i in sat.policy_id], marker="o", label=f"{NAMES[score]} (n={len(matched)})", color=colours[score])
        ax.axhline(means[wider.policy_id] * 100, linestyle="--", alpha=0.55, color=colours[score])
    ax.set_xlabel("Initial satellite budget fraction")
    ax.set_ylabel("Mean30-day simple return (%)")
    ax.set_xticks([0, 0.1, 0.2])
    ax.legend()
    ax.grid(alpha=0.2)
    save(fig, "satellite-budget", "Core/satellite allocation curve")
    companions = short[short.variant.isin(["satellite", "minimum_variance", "equal_risk_contribution", "minimum_variance_gate60"])]
    table(companions[["score", "variant", "satellite", "mean_return", "weighting_lift", "mean_variance", "effective_N", "resolved_origins"]], "Bounded construction companions", "Satellite groups preserve the same relative risk weights within core and satellite. Correlation methods use Ledoit–Wolf scaled-identity shrinkage rescaled to the same marginal risks; failed support uses an explicitly labelled diagonal prior.")
    forecasts = period_frame(result["outcomes"], h=30).merge(result["policies"][["policy_id", "score", "variant", "estimator", "N", "L", "p", "branch"]], on="policy_id")
    forecasts = forecasts[forecasts.N.eq(6) & forecasts.L.eq(90) & forecasts.p.eq(2) & forecasts.branch.eq("pure")]
    fc = []
    for (score, variant, estimator), g in forecasts.groupby(["score", "variant", "estimator"]):
        if variant not in ("main", "minimum_variance", "equal_risk_contribution", "minimum_variance_gate60"):
            continue
        for field, label in [("forecast_variance", "diagonal"), ("covariance_forecast_variance", "covariance")]:
            z = g[np.isfinite(g[field]) & np.isfinite(g.variance)]
            if len(z):
                fc.append(dict(score=score, construction=variant, estimator=estimator, prediction=label, paired_origins=len(z), predicted=z[field].mean(), realised=z.variance.mean(), calibration_ratio=z[field].mean() / z.variance.mean() if z.variance.mean() > 0 else np.nan))
    table(pd.DataFrame(fc).head(20), "Basket entry-risk calibration", "Compare initial wᵀΣw (or diagonal counterpart) with subsequent fixed-unit daily variance on matched origins. Both forecast error and position-weight drift affect this target; no constant-mix assumption is made.")
    cov = result["allocations"]
    cov = cov.merge(result["policies"][["policy_id", "variant", "score"]], on="policy_id")
    cov = cov[cov.variant.isin(["minimum_variance", "equal_risk_contribution", "minimum_variance_gate60"]) & cov.origin_at.between(pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-05"), inclusive="left")]
    fallback = cov[["origin_at", "policy_id", "score", "variant", "status"]].drop_duplicates().groupby(["score", "variant", "status"]).size().reset_index(name="origins")
    table(fallback.head(20), "Correlation-estimation support", "The full support ledger is saved in artefacts. Identity correlation is a prior used when overlap or actual-update support fails; it is not evidence of independence.")
    heatmap(diag["quarters"], "quarter", "score", "weighting_lift", "Quarterly weighting lift", "Regularised inverse variance, six positions, 90-day risk. Different origin quarters overlap future paths; positive return lift favours unequal weights.", "quarter-lift", diverging=True, percent=True)
    table(diag["phases"], "Four origin phases", "Each phase repeats the same focal construction on a shifted four-day grid. Phases share outcomes and are sensitivity checks, not four independent replications.")
    table(diag["spaced"], "Horizon-spaced origin diagnostic", "Keep one deterministic sequence of supported origins at least 30 days apart. This diagnostic reduces overlap and does not manufacture multiple holdouts.")
    table(diag["quarter_influence"], "Leave-one-quarter influence", "Re-average the existing fixed snapshot ledger after omitting an origin quarter. This is a sensitivity calculation, not an investable reconstructed strategy.")
    vi = diag["vault_influence"]
    vi = vi.assign(absolute=vi.mean_contribution.abs()).sort_values("absolute", ascending=False).head(12)
    table(vi[["score", "vault_name", "mean_contribution"]], "Largest vault contributions to weighting lift", "Contribution is active weight versus equal times vault simple return, averaged over all paired origins for that score. Removing a contribution holds the allocation ledger fixed; it does not reselect a portfolio.")
    intro("Recorded age and actual reporting coverage", "Every point is an eligible phase-zero vault/date risk row at L=90. Age means recorded positive NAV history, not known vault inception; colour is the age of the latest actual NAV at the origin, in days. Intraday ages remain on the same linear day scale.")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    plot = risk_state
    from matplotlib.colors import Normalize

    age = plot.anchor_age.to_numpy()
    sc = ax.scatter(plot.history_age, plot.actual_fraction, c=age, s=5, alpha=0.4, cmap="viridis", norm=Normalize(vmin=0, vmax=float(np.nanmax(age))))
    ax.set_xlabel("Recorded history age (calendar days)")
    ax.set_ylabel("Actual updates / elapsed calendar returns")
    fig.colorbar(sc, ax=ax, label="Latest actual NAV age (days)")
    save(fig, "age-coverage", "History age and actual reporting coverage")
    boundary = controls[controls.estimator.eq("regularised") & controls.p.eq(2)][["score", "carried_anchor_weight", "carried_endpoint_weight", "no_update_weight", "first_update_lift", "remaining_lift", "unresolved_weight"]]
    table(boundary, "Reporting-boundary attribution", "The first catch-up mark can include both pre-origin and genuine post-origin movement. Its active-weight contribution plus the remaining original-notional component reconciles exactly; neither is an executable corrected return.")
    table(short[short.N.eq(6) & short.variant.eq("main") & short.branch.eq("pure") & short.estimator.eq("regularised") & short.p.eq(2)][["score", "resolved_origins", "origins", "unresolved_weight", "universe_resolved"]], "Unresolved future outcomes", "Any positive-weight missing terminal path censors the basket. Known weighted contributions minus unresolved weight give a lower NAV-return bound; missing upside is unbounded. Break-even common-missing-return scenarios are saved separately and are not identified bounds.")
    focus = period_frame(result["outcomes"], h=30)
    focus = focus[focus.policy_id.isin(controls[controls.estimator.eq("regularised") & controls.p.eq(2)].policy_id) & focus.resolved].merge(result["policies"][["policy_id", "score"]], on="policy_id")
    outliers = focus.assign(magnitude=focus["return"].abs()).sort_values("magnitude", ascending=False).head(10)
    table(outliers[["origin_at", "score", "return", "variance", "drawdown", "max_weight", "carried_anchor_weight", "carried_endpoint_weight"]], "Largest absolute snapshot moves", "These are overlapping horizon outcomes, not separate profitable trades. They remain in means; the per-vault contribution and quarter influence tables show whether an advantage is concentrated.")
    ties = result["ties"]
    tie_summary = ties.groupby("score").agg(tied_origins=("origin_at", "size"), mean_changed_names=("changed_names", "mean"), mean_low=("return_low", "mean"), mean_high=("return_high", "mean"), mean_resolved_draws=("resolved_draws", "mean")).reset_index()
    table(tie_summary, "Tie-resolution sensitivity", "999 seeded identity priorities per tied origin propagate clipped/missing-score ties into membership and returns. Ranges are conditional tie outcomes, not confidence intervals.")
    stab = period_frame(result["stability"])
    stab = stab[stab.policy_id.isin(controls[controls.estimator.eq("regularised") & controls.p.eq(2)].policy_id)].merge(result["policies"][["policy_id", "score"]], on="policy_id").groupby("score").agg(mean_jaccard=("jaccard", "mean"), mean_target_variation=("total_variation", "mean"), transitions=("origin_at", "size")).reset_index()
    table(stab, "Basket and target-weight stability", "Consecutive four-day Jaccard overlap and half the absolute desired allocation change, including cash. Missing origins are not compressed; these quantities are not realised turnover or fees.")
    synthetic = result["synthetic"].groupby(["process", "spacing_days", "estimator"]).ratio.mean().reset_index()
    heatmap(synthetic.assign(label=synthetic.process.str.replace("_", " ") + " / " + synthetic.estimator), "spacing_days", "label", "ratio", "Synthetic reporting risk distortion", "Known dense processes are masked at daily, two-day and seven-day schedules. Ratio is estimated/dense risk. Regularisation uses known dense risk as a mechanism-isolation prior, not estimated live latent risk. Each process has 180 returns, 100 replicates and κ=60; log-return diffusion mean/σ=0.0002/0.01, alternating amplitude=0.01, and catch-up jump=0.07 every 31 days.", "synthetic-reporting", h="Synthetic 180-day histories; 2026 reporting patterns")
    intro("Primary paired construction contrasts", "All 18 frozen comparisons remain visible. Return effects are horizon percentage-point differences; variance effects are daily-variance units. 2026 is descriptive under the ten-block gate.")
    intervals = result["intervals"]
    view = intervals[intervals.period.eq("2026") & intervals.block_days.eq(30)]
    display(view[["comparison_id", "mean", "paired_origins", "nonoverlapping_windows", "complete_blocks", "status"]].style.format({"mean": "{:.4g}"}, na_rep="—").hide(axis="index"))
    horizon_check = result["summaries"]
    horizon_check = horizon_check[horizon_check.period.eq("2026") & horizon_check.N.eq(6) & horizon_check.L.eq(90) & horizon_check.p.eq(2) & horizon_check.estimator.eq("regularised") & horizon_check.branch.eq("pure") & horizon_check.variant.eq("main")]
    table(horizon_check[["score", "h", "mean_return", "weighting_lift", "variance_lift", "resolved_origins", "origins", "unresolved_weight"]], "Horizon stability", "Same frozen regularised six-position inverse-variance construction at 7/30/90 days. Means use each horizon’s fully resolved selected baskets; unequal administrative support must not be mistaken for a horizon effect.", h="7/30/90")
    for period in ("Pre-2026", "Long"):
        start, end = PERIODS[period]
        caption = f"{start.date()} → {end.date()} (end exclusive, UTC)"
        table(intervals[intervals.period.eq(period) & intervals.block_days.eq(30)][["comparison_id", "mean", "lower", "upper", "paired_origins", "complete_blocks", "status"]], f"Secondary {period} primary contrasts", "Simultaneous intervals share calendar blocks across the frozen family. Longer history remains exploratory and overlaps earlier research; the Long period includes 2026.", period=caption)
    write_findings(result, diag, audit)
    manifest = json.loads((ARTIFACT / "manifest.json").read_text())
    manifest["diagnostic_configuration"] = {"age_quality_null_quantiles": 3, "quality_display_quantiles": 5, "synthetic_replicates": 100, "synthetic_return_days": 180, "diffusion_log_mean": 0.0002, "diffusion_log_sigma": 0.01, "alternating_log_amplitude": 0.01, "catch_up_log_jump": 0.07, "catch_up_spacing_days": 31, "synthetic_mask_schedules": "1/2/7 days plus archived last181-day masks; first anchor retained", "qlike_colour_linthresh": 1.0, "age_colour_scale": "actual NAV age in days, linear from zero", "plot_dpi": 130, "main_table_rows_target": 20, "draws": 999}
    manifest["code"] = __import__("portfolio_snapshot_data").fingerprint()
    (ARTIFACT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    (ARTIFACT / "figure-manifest.json").write_text(json.dumps(FIGURES, indent=2))
    intro("Research verdict and next checks", "Read the separate findings document for the full hypothesis-by-hypothesis account. The conclusions below concern 30-day 2026 gross-NAV snapshots; they do not identify an executable strategy winner.")
    display(Markdown("""- **Sorting:** future-return IC is modest and similar across the three frozen scores (about 0.087–0.089).
- **Risk forecasts:** selected risk IC is stronger (about 0.51–0.55), while calibration and tail losses still require care.
- **Weights:** uncapped inverse variance lowers risk and returns. Regularisation reduces the return drag; concentration/TVL projection can change its sign.
- **Breadth:** matched 10-versus-6-position returns fall as risk falls. Satellite comparisons use the same resolved origins.
- **Uncertainty:** 2026 fails the ten-block gate; supported longer-history simultaneous bands include zero.
- **Next:** replay regularisation × capped redistribution with matched equal controls. Detailed [findings](10-portfolio-snapshot-findings.md), [risk](appendices/10-snapshot-risk-tables.ipynb), [allocation](appendices/10-snapshot-allocation-tables.ipynb) and [statistics](appendices/10-snapshot-statistics-tables.ipynb) appendices preserve the complete results."""))


def markdown_table(frame):
    return frame.to_markdown(index=False, floatfmt=".4g")


def write_findings(result, diag, audit):
    short = result["summaries"]
    short = short[short.period.eq("2026") & short.h.eq(30)]
    controls = short[short.N.eq(6) & short.L.eq(90) & short.p.isin([0, 1, 2]) & short.estimator.isin(["equal", "raw", "regularised", "source"]) & short.branch.eq("pure") & short.variant.isin(["main", "source_candle_control"])]
    display = controls[["score", "estimator", "p", "mean_return", "mean_variance", "weighting_lift", "resolved_origins", "unresolved_weight"]].copy()
    for c in ("mean_return", "weighting_lift", "unresolved_weight"):
        display[c] = display[c].map(lambda v: f"{v*100:.3f}%" if np.isfinite(v) else "unsupported")
    lines = [
        "# Experiment 10 — portfolio snapshot findings",
        "",
        "Executed on 10 October 2026. Primary origin period: **2026-01-01 → 2026-10-05 (end exclusive, UTC)**; primary horizon **30 days**. Labels must mature inside the reporting boundary. Sources are the unchanged repaired archive used by NB08/NB09.",
        "",
        "## What was examined",
        "",
        "Frozen v11, Blend 46d and four-input scores select independent baskets every four days. We compare equal, inverse-volatility and inverse-variance weights, risk regularisation/windows, 4/6/8/10 positions, entry caps and bounded correlation/satellite companions. NAV paths hold fixed units; no strategy equity curve, engine replay, executable CAGR or portfolio backtest Sharpe is inferred.",
        "",
        "## Main outcomes — 2026 period; 30-day horizon",
        "",
        "Rows are equal-origin means on each policy’s resolved basket support. Weighting lift pairs the same basket and budget with equal weights. Return percentages are 30-day simple returns, not annualised strategy returns.",
        "",
        markdown_table(display),
        "",
        "## Hypothesis verdicts — 2026 period; 30-day horizon",
        "",
        "IC measures finite-score ordering. Weighting and breadth effects are paired horizon-return differences in percentage points; they are not annualised strategy returns.",
        "",
    ]
    verdict = []
    for score in METHODS:
        g = controls[controls.score.eq(score)]
        reg = g[g.estimator.eq("regularised") & g.p.eq(2)].iloc[0]
        raw = g[g.estimator.eq("raw") & g.p.eq(2)].iloc[0]
        ic = period_frame(result["score_ic"], h=30)
        ic = ic[ic.score.eq(score) & ic.target.eq("return")]
        broad = short[short.score.eq(score) & short.N.eq(10) & short.L.eq(90) & short.estimator.eq("regularised") & short.p.eq(2) & short.variant.eq("main") & short.branch.eq("pure")].iloc[0]
        paired = period_frame(result["contrasts"], h=30)
        delta = paired[paired.comparison_id.eq(score + "|breadth_10_minus_6|return")].effect.mean()
        verdict.append({"Score": score, "Return IC": ic.ic.mean(), "Regularised weighting lift (pp)": reg.weighting_lift * 100, "Raw weighting lift (pp)": raw.weighting_lift * 100, "10−6 return difference (pp)": delta * 100, "Verdict": "descriptive screening; inspect risk, concentration and reporting attribution before promotion"})
    lines.extend(
        [
            markdown_table(pd.DataFrame(verdict)),
            "",
            "The sorting hypothesis is supported only where observed finite-pair IC and strict-reference selection evidence agree; full-universe attrition prevents treating conditional IC as unbiased selection skill. Unequal weights are assessed by their paired return/risk trade-off, not by weight rank IC: all positive inverse-risk powers have the same rank order. No primary 2026 comparison receives an inferential success label.",
            "",
            "## Risk accuracy and reporting boundaries — 2026 period; 30-day horizon",
            "",
            "Leave-one-out positive peer priors use complete elapsed windows first, partial history second. Support weight counts actual daily updates; observed flat and one-mark carried-flat paths are distinguished. Raw risk retains the inherited 1e-4 daily-sigma floor. Extreme floor errors remain in mean QLIKE; weighted median, win fraction and absolute-tail concentration provide context. Forecasted risk and forward-filled NAV risk are not established proxies for true executable economic risk.",
            "",
            markdown_table(result["risk_summary"].query("period == '2026' and h == 30 and L == 90 and cohort == 'selected'")[["score", "estimator", "risk_ic", "qlike_delta", "qlike_median", "win_fraction", "tail_absolute_share", "calibration_ratio", "paired_origins"]]),
            "",
            "First-update attribution uses original notional and reconciles with remaining-mark contribution. A catch-up mark can include genuine post-origin gains as well as unknown earlier movement; removing it does not identify an investable adjusted return. Endpoint staleness and terminal censoring remain unresolved economic limitations.",
            "",
            "## Robustness and uncertainty — 2026 period; 30-day horizon",
            "",
            "All 2026 intervals are descriptive under the frozen ten-complete-calendar-block gate. Full and pre-2026 simultaneous intervals are exploratory when support permits; their history has also been researched. Bootstrap draws preserve missing scheduled dates and share blocks across all 18 comparisons. Conditional active-treatment effects are saved alongside the primary policy effects, including equal-fallback and unchanged actual-breadth dates.",
            "",
            markdown_table(diag["phases"]),
            "",
            "Four grid phases overlap and are not independent replications. Ties are perturbed with 999 seeded identity priorities per tied origin. Assignment controls preserve concentration, and pooled random assignments retain identity priorities across dates. Quarter/vault influence holds the original ledger fixed, rather than reselecting a strategy. Gross NAV outcomes contain no invented slippage or turnover fees.",
            "",
            "## Capacity assumptions — 2026 period; 30-day horizon",
            "",
            "Source-report-only control applies source concentration/TVL and the source eligibility gate. The framework reports archived hard deposit caps but does not enforce them as partial rebalance sizing limits; the permissive hard-cap branch is therefore explicitly a capacity diagnostic, not exact source alpha-model parity. Unknown independent clocks retain recorded fields. Known-only state is an exclusion sensitivity, not a claim to be historically more accurate. Each constrained unequal policy has a same-accepted-budget bounded equal benchmark.",
            "",
            "## Useful leads",
            "",
            "1. Carry forward only paired construction trade-offs stable across score, nearby window, grid phase and reporting-quality diagnostics. Do not select a lone best cell as an optimum.",
            "2. Treat peer regularisation and tempering the risk exponent separately: they change risk forecast accuracy and allocation concentration by different mechanisms.",
            "3. Use exact shared/new-name breadth attribution to decide whether added positions help; requested N alone can conceal concentration or dilution.",
            "4. Reconcile cash and capacity effects before converting any shortlist into a complete source strategy replay. Snapshot results omit retention, settlement, trading and fee state.",
            "",
            "## Verification and remaining scope",
            "",
            f"Independent audit: {len(audit)} checks reported; saved audit table and original-archive reconstructions are under the ignored experiment 10 artefacts. Every selected name survives into the ledger, even with missing targets. No terminal payout or finite missing-upside bound is invented.",
            "",
            "Core stages, source requested-risk checks, all primary contrasts, attribution, persistent assignment placebos, missingness, alternate phases/ties and basic capacity are implemented. Bounded covariance, satellite and cap/account-size companions are included. Irregular-interval/weekly risk, chronological calibration, category priors, full execution costs, the non-causal clairvoyant-risk diagnostic and a true realised-return LP bound remain separately labelled follow-up work; they do not change the frozen core estimands.",
            "",
            "Notebook: [10-research-portfolio-snapshots.ipynb](10-research-portfolio-snapshots.ipynb). Reusable modules are saved beside it; generated figures, ledgers and manifests remain ignored.",
        ]
    )
    capacity = short[short.branch.eq("capacity") & short.variant.isin(["main", "source_capacity_control"]) & short.L.eq(90) & short.p.isin([1, 2])]
    capacity = capacity[capacity.state.eq("source_report_only")]
    capacity_display = capacity[["score", "estimator", "p", "mean_return", "weighting_lift", "mean_cash", "resolved_origins"]].copy()
    for column in ("mean_return", "weighting_lift", "mean_cash"):
        capacity_display[column] = capacity_display[column].map(lambda x: f"{x*100:.3f}%" if np.isfinite(x) else "unsupported")
    extra = [
        "## Answers to the research questions — 2026 period; 30-day horizon",
        "",
        "**S — sorting:** observed future-return IC is modest and positive (about 0.087–0.089), with little separation between these three frozen recipes. Finite-pair ordering is conditional on observed targets. Strict eligible-universe references resolve on 55 of 62 mature origins; use that common cohort for selection-lift comparisons. This supports further evaluation, without establishing a superior score.",
        "",
        "**R — risk forecasts:** selected-basket risk IC is about 0.51–0.55, substantially stronger than return IC. Raw and regularised variance improve mean QLIKE against the peer prior in the selected 90-day panels. Regularisation does not uniformly improve raw QLIKE: the four-input panel has a worse mean but a better win fraction. Level calibration ratios below 1 indicate underprediction; extreme errors contribute heavily to aggregate loss. Useful ordering and accurate risk levels are different claims.",
        "",
        "**W — weighting:** uncapped 90-day inverse variance reduces daily variance versus equal weights but loses about 1.80–2.36 percentage points of mean 30-day return. Regularisation reduces that return drag to about 0.76–1.39pp; inverse volatility generally gives up less return than inverse variance, while accepting more risk. The return-enhancement hypothesis is rejected for these uncapped snapshots; the measured-risk-reduction hypothesis is supported descriptively.",
        "",
        "**N — breadth:** matched 10-versus-6-position regularised inverse-variance returns decline by about 0.13–0.74pp, while realised variance falls. Ten-position outcomes resolve on 55 origins versus 62 for six positions; subtracting unmatched displayed means would misstate this effect. The satellite curve also uses common support and shows no return improvement over its matched core. Wider baskets are a risk/return trade-off, not an established profit improvement.",
        "",
        "**C — constraints:** concentration and TVL projection substantially change the weighting comparison. The regularised inverse-variance source-report-only control has positive same-budget equal-weight lift, unlike its uncapped counterpart. Explicit source/raw controls below test this interaction using the same baskets and bounded budget. This is a stateless entry projection; it cannot establish engine-replay performance.",
        "",
        "### Entry-capacity controls — 2026 period; 30-day horizon",
        "",
        "Mean simple returns, paired same-budget weighting lift and initial cash are percentages. All rows use six positions, a 90-day risk window and source-report-only concentration/TVL projection. p=1 is inverse volatility; p=2 is inverse variance.",
        "",
        markdown_table(capacity_display),
        "",
        "**Q — reporting and robustness:** first-update active attribution is small relative to the remaining negative uncapped weighting lift. The result is not explained solely by the first catch-up mark. Later marks can still contain reporting effects, so the remaining component is not labelled executable return. Negative regularised weighting lift appears in all four overlapping grid phases, with quarter and vault concentration remaining important. All supported longer-history simultaneous 18-comparison intervals include zero; 2026 has too few complete blocks for the planned inferential gate.",
        "",
        "These 30-day snapshot returns are not comparable directly with source v11’s 41.20% strategy CAGR. The source replay includes repeated two-day decisions, incumbent rules, capped redistribution and inherited execution-cost assumptions; this study deliberately holds each independent entry basket unchanged.",
        "",
        "## Exhaustive result appendices",
        "",
        "The main notebook keeps 2026 as its default. Separate saved-output notebooks contain the exhaustive risk, allocation and statistical tables, including explicitly labelled long/pre-2026 periods: [risk](appendices/10-snapshot-risk-tables.ipynb), [allocation](appendices/10-snapshot-allocation-tables.ipynb), [statistics](appendices/10-snapshot-statistics-tables.ipynb).",
    ]
    lines.extend(extra)
    (ROOT / "10-portfolio-snapshot-findings.md").write_text("\n".join(lines) + "\n")
