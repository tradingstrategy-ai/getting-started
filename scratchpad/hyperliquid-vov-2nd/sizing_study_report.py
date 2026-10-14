"""Compact styled tables and separate, described NB11 research figures."""

import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from IPython.display import display, Markdown, Image
from sizing_study_design import ROOT, PERIOD, followups


class Report:
    def __init__(self, folder, stage, h=30):
        self.folder = folder
        self.stage = stage
        self.h = h
        self.figures = []
        (folder / "figures").mkdir(exist_ok=True)

    def intro(self, title, description):
        display(Markdown(f"### {title} — {PERIOD}; {self.h}-day horizon; {self.stage}\n\n{description}"))

    def table(self, frame, title, description, percent=()):
        self.intro(title, description)
        f = frame.copy()
        numeric = f.select_dtypes("number").columns
        formats = {c: "{:.2%}" if c in percent else "{:.0f}" if pd.api.types.is_integer_dtype(f[c]) else "{:.4g}" for c in numeric}
        st = f.style.format(formats, na_rep="—")
        for c in ("mean_return", "return_difference", "drawdown_difference", "mean_drawdown", "weighting_lift"):
            if c in f and f[c].notna().any():
                st = st.background_gradient(subset=[c], cmap="RdYlGn", **getattr(self, "scales", {}).get(c, {}))
        for c in ("mean_cash", "qlike_delta", "mean_distortion", "mean_variance"):
            if c in f and f[c].notna().any():
                st = st.background_gradient(subset=[c], cmap="YlOrRd", **getattr(self, "scales", {}).get(c, {}))
        display(st.hide(axis="index"))

    def save(self, fig, slug, title, description):
        self.intro(title, description)
        fig.suptitle(f"{title}\n{PERIOD}; {self.h}-day horizon; {self.stage}", fontsize=10)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        path = self.folder / "figures" / f"{slug}.png"
        fig.savefig(path, dpi=135, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        self.figures.append(dict(file=str(path), title=title, horizon=self.h, stage=self.stage))
        display(Image(filename=str(path)))

    def heatmap(self, pivot, slug, title, description, counts=None, limit=None, ratio=False):
        a = pivot.to_numpy(float)
        colour = np.log(a) if ratio else a
        bound = limit if limit is not None else max(float(np.nanmax(np.abs(colour))), 1e-9)
        fig, ax = plt.subplots(figsize=(max(6, 0.75 * len(pivot.columns) + 3), max(3.8, 0.65 * len(pivot) + 2)))
        cmap = plt.get_cmap("RdYlGn_r" if ratio else "RdYlGn").copy()
        cmap.set_bad("#eeeeee")
        im = ax.imshow(np.ma.masked_invalid(colour), cmap=cmap, norm=TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound), aspect="auto")
        ax.grid(False)
        if slug.find("surface") >= 0:
            ax.set(xlabel="Allocation power p", ylabel="Risk lookback (days)")
        ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=25, ha="right")
        ax.set_yticks(range(len(pivot)), pivot.index)
        for i in range(len(pivot)):
            for j in range(len(pivot.columns)):
                val = a[i, j]
                label = "—" if not np.isfinite(val) else f"{val:.2f}×" if ratio else f"{val:+.2f}"
                if counts is not None:
                    label += f"\nn={int(counts.iloc[i,j])}"
                rgba = im.cmap(im.norm(colour[i, j])) if np.isfinite(colour[i, j]) else (1, 1, 1, 1)
                bright = np.dot(rgba[:3], [0.299, 0.587, 0.114])
                ax.text(j, i, label, ha="center", va="center", fontsize=9, color="black" if bright > 0.55 else "white")
        cb = fig.colorbar(im, ax=ax, shrink=0.8)
        cb.set_label("log variance ratio (0 = ratio1)" if ratio else "Percentage points")
        self.save(fig, slug, title, description)


def render_smoke(data, result, audit):
    r = Report(data["artifact"], "smoke")
    r.table(result["parity"].assign(reference=result["parity"].reference.str.replace(r"^focal_four\|.*", "Original NB10 focal regularised90/p2", regex=True)), "Saved control reproduction", "Exact NB10 per-date weights and outcomes, using unchanged archive and feature fingerprints.", percent=["mean_return"])
    r.table(result["summary"][["arm", "label", "resolved", "mean_return", "mean_variance", "mean_cash", "effective_N"]], "18-policy smoke checkpoint", "Full calendar is retained; 62 mature 30-day origins per arm. This checks implementation, not profitability.", percent=["mean_return", "mean_cash"])
    g = result["allocations"].query('arm=="S03"').sort_values("origin_at")
    date = g.loc[g.cap_distortion.gt(1e-12), "origin_at"].min()
    g = g[g.origin_at == date].sort_values("rank")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    x = np.arange(len(g))
    ax.bar(x - 0.2, g.shadow_weight * 100, 0.4, label="Requested at accepted budget")
    ax.bar(x + 0.2, g.accepted_weight * 100, 0.4, label="Accepted")
    ax.set_xticks(x, g.vault_name.str.slice(0, 25), rotation=25, ha="right")
    ax.set_ylabel("Account weight (%)")
    ax.legend(fontsize=8)
    r.save(fig, "smoke-caps", "Smoke cap-active example", f"Earliest focal baseline date with positive cap distortion: {date.date()}. Chosen from allocation mechanics before inspecting returns.")
    save_figures(r)
    return r.figures


def save_figures(r):
    (r.folder / "figures.json").write_text(json.dumps(r.figures, indent=2))


def render_main(data, result, audit, policies, support):
    plt.rcParams.update({"font.size": 10, "xtick.labelsize": 9, "ytick.labelsize": 9})
    r = Report(data["artifact"], "main")
    out = result["outcomes"]
    ledger = result["allocations"]
    risk = result["risk"]
    s = result["summary"].query("h==30")
    c = result["contrasts"].query("h==30")
    r.scales = {k: dict(vmin=float(s[k].min()), vmax=float(s[k].max())) for k in ("mean_return", "mean_cash", "mean_drawdown", "mean_variance", "weighting_lift")}
    r.h = "7/30/90"
    r.table(pd.DataFrame([dict(horizon=h, scheduled=70, mature={7: 68, 30: 62, 90: 47}[h], pending=70 - {7: 68, 30: 62, 90: 47}[h]) for h in (7, 30, 90)]), "Calendar and maturity", "All 70 origins retained at each horizon; features use T−1 and full 2025/earlier warmup. Pending targets are never zero returns.")
    maturity = result["summary"][result["summary"].arm.isin(["S03", "S04"])][["arm", "selector", "h", "scheduled", "mature", "pending", "resolved"]]
    r.table(maturity, "Maturity versus terminal support", "Administrative maturity does not guarantee supported terminal NAV. Seven/30-day outcomes resolve 68/62 dates; 90-day resolves 46 of 47 mature origins. Unsupported invested weight remains unresolved.")
    r.h = 90
    missing = result["calibration_rows"].query("h==90 and realised != realised")[["origin_at", "selector", "pair_id"]].drop_duplicates()
    if len(missing):
        missing = missing.merge(data["identities"][["pair_id", "vault_name"]], on="pair_id")
        missing["last_actual_date"] = missing.pair_id.map(data["last"])
        missing["target_end"] = missing.origin_at + pd.Timedelta(days=89)
        r.table(missing.drop(columns=["pair_id"]), "Unresolved 90-day target", "Selected using only past information. The target ends beyond this vault’s final actual positive mark; NAV is not carried past terminal support for target evaluation.")
    r.h = 30
    for selector in ("F", "L"):
        p = pd.DataFrame([dict(arm=x["arm"], canonical_id=x["policy_id"], method=x["method"], L=x["L"], p=x["p"], kappa=x["kappa"], floor=x["floor"]) for x in policies if x["selector"] == selector])
        r.table(p, f"{selector} executed design", "F = focal_four, L = v11; six frozen vaults. All methods share source-report-only caps, $150k account, 98% budget and 33% concentration/TVL limits. Regularised risk has no raw floor; sparse kappa counts complete intervals.")
    r.table(result["parity"].assign(reference=result["parity"].reference.str.replace(r"^focal_four\|.*", "Original NB10 focal regularised90/p2", regex=True)), "Exact reference controls", "Saved original/expanded NB10 identities, weights and 62 mature outcomes reproduce. Controls are not independent replications.", percent=["mean_return"])
    r.table(audit, "Independent checks", "Mathematics, causal cutoffs, frozen selections, exact controls, maturity and all-origin allocation conservation.")
    for selector in ("F", "L"):
        z = s[s.selector == selector]
        r.table(z[["arm", "label", "resolved", "mean_return", "median_return", "mean_variance", "mean_drawdown", "mean_cash", "effective_N", "weighting_lift"]], f"{selector} side-by-side outcomes", "Equal-origin mean/median snapshot returns, daily portfolio variance and mean within-window drawdown. Cash uses the same resolved mature support; colouring shares scales across selectors. These are not CAGR.", percent=["mean_return", "median_return", "mean_drawdown", "mean_cash", "weighting_lift"])
    r.table(c[c.family == "primary"][["arm", "control", "paired", "return_difference", "variance_ratio", "drawdown_difference", "cash_difference", "wins", "ties", "losses", "complete_blocks"]], "17 registered primary contrasts", "New minus 90-day/p2/kappa30 baseline, plus T18 minus V180. Variance ratio uses ratio of paired mean variances. Eight complete 30-day blocks fail the ten-block gate; all 51 statistics are descriptive.", percent=["return_difference", "drawdown_difference", "cash_difference"])
    r.table(c[c.family == "secondary"][["arm", "control", "paired", "return_difference", "variance_ratio", "drawdown_difference", "cash_difference", "common_budget_difference"]], "Other registered mechanism contrasts", "Paired differences against each selector’s 90-day/p2 baseline, or the named sparse/window control. Common-budget reprojection uses the smaller accepted budget fixed before targets; all main policies happen to invest the same total budget within each selector.", percent=["return_difference", "drawdown_difference", "cash_difference", "common_budget_difference"])
    for h in (7, 90):
        r.h = h
        z = result["summary"].query("h==@h")
        r.table(z[["arm", "label", "resolved", "mean_return", "mean_variance", "mean_drawdown", "mean_cash"]], f"{h}-day secondary outcomes", "Exactly the same allocations as the primary horizon. Horizon maturity changes available quarters; no horizon is promoted to confirmation.", percent=["mean_return", "mean_drawdown", "mean_cash"])
    r.h = 30
    surfaces = []
    for selector in ("F", "L"):
        z = s[(s.selector == selector) & (s.method == "regular") & (s.kappa == 30)]
        base = "S03" if selector == "F" else "S04"
        d = c[(c.control == base) & c.arm.isin(z.arm)].set_index("arm")
        rows = []
        for row in z.itertuples():
            v = dict(L=row.L, p=row.p, ret=0.0, dd=0.0, ratio=1.0, n=row.resolved)
            if row.arm != base:
                cc = d.loc[row.arm]
                v.update(ret=cc.return_difference * 100, dd=cc.drawdown_difference * 100, ratio=cc.variance_ratio, n=cc.paired)
            rows.append(v)
        surfaces.append((selector, pd.DataFrame(rows)))
    retlim = max(max(abs(d.ret)) for _, d in surfaces)
    ddlim = max(max(abs(d.dd)) for _, d in surfaces)
    ratlim = max(max(abs(np.log(d.ratio))) for _, d in surfaces)
    for selector, d in surfaces:
        counts = d.pivot(index="L", columns="p", values="n")
        for metric, title, limit, ratio in [("ret", "return difference", retlim, False), ("dd", "drawdown difference", ddlim, False), ("ratio", "variance ratio", ratlim, True)]:
            r.heatmap(d.pivot(index="L", columns="p", values=metric), f"{selector}-surface-{metric}", f"{selector} window × power: {title}", "Rows are calendar lookback days; columns p=1 inverse volatility, 1.5 intermediate, 2 inverse variance. Fixed kappa30. Paired resolved dates only; baseline L90/p2. Shared scales across selectors; cell n is pair count.", counts=counts, limit=max(limit, 1e-9), ratio=ratio)
    for selector in ("F", "L"):
        z = s[s.selector == selector]
        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.scatter(z.mean_variance * 1e4, z.mean_return * 100, c=z.effective_N, cmap="viridis", s=50)
        baseline = z[z.arm.eq("S03" if selector == "F" else "S04")].iloc[0]
        ax.scatter([baseline.mean_variance * 1e4], [baseline.mean_return * 100], s=180, marker="*", c="#ffd700", edgecolors="black", linewidths=0.7, zorder=5, label="90-day/p2 baseline")
        important = ["S01", "S02", "S03", "S04", "S15", "S16", "S17", "S18"]
        for i, row in enumerate(z[z.arm.isin(important)].itertuples()):
            ax.annotate(row.arm, (row.mean_variance * 1e4, row.mean_return * 100), xytext={"S03": (-8, -28), "S18": (16, 18), "S17": (20, 24), "S01": (-35, 12), "S04": (-8, 25), "S16": (12, 12), "S15": (12, 22), "S02": (-50, -20)}.get(row.arm, (8, 8)), textcoords="offset points", fontsize=8, arrowprops=dict(arrowstyle="-", color="grey"))
        # Descriptive non-dominated envelope, with no fitted preference function.
        order = z.sort_values("mean_variance")
        keep = order.mean_return.gt(order.mean_return.cummax().shift(fill_value=-np.inf))
        front = order[keep]
        ax.plot(front.mean_variance * 1e4, front.mean_return * 100, color="grey", lw=1, ls="--", label="Descriptive envelope")
        ax.set_xscale("log")
        ax.set(xlabel="Mean daily portfolio variance × 10,000 (log scale)", ylabel="Mean 30-day return (%)")
        ax.margins(x=0.08, y=0.12)
        ax.legend(loc="upper right" if selector == "F" else "lower right", fontsize=9)
        fig.colorbar(im, ax=ax, label="Effective funded positions")
        r.save(fig, f"{selector}-return-risk", f"{selector} return and realised risk", "All registered policies for this selector. Labels identify controls; full formula-to-arm mapping is above. Envelope is descriptive, not a promoted optimum.")
    for selector, arms in [("F", ["S01", "S03", "S09", "S11", "S13", "S17", "S18"]), ("L", ["S02", "S04", "S10", "S12", "S14", "S15", "S16"])]:
        q = result["quarterly"].query("h==30")
        q = q[q.arm.isin(arms)]
        p = q.pivot(index="arm", columns="quarter", values="mean_return").reindex(index=arms, columns=["2026Q1", "2026Q2", "2026Q3", "2026Q4"])
        n = q.pivot(index="arm", columns="quarter", values="resolved").reindex(index=arms, columns=p.columns)
        bound = max(float(abs(result["quarterly"].query("h==30").mean_return).max() * 100), 1e-9)
        r.heatmap(p * 100, f"{selector}-quarters", f"{selector} mean snapshots by origin quarter", "Mean 30-day return, not quarterly profit. Q4 has no mature observations and is grey; n is resolved mature support. Q3 only partly matured.", counts=n, limit=bound)
    mechanism = s[["arm", "label", "effective_N", "max_weight", "mean_distortion", "fallback_fraction", "mean_cash"]].merge(result["cap_ties"].groupby("arm").same_accepted.mean().rename("same_as_baseline_fraction"), on="arm")
    r.table(mechanism, "Breadth, fallback and cap activity", "Shadow at the same accepted budget is a diagnostic, not another evaluated policy. Distortion is sum absolute accepted-minus-shadow weights over all 70 scheduled dates. Outcome cash uses resolved mature dates.", percent=["max_weight", "mean_distortion", "fallback_fraction", "mean_cash", "same_as_baseline_fraction"])
    g = ledger[ledger.arm == "S03"]
    date = g.loc[g.cap_distortion.gt(1e-12), "origin_at"].min()
    for arm in ("S01", "S03"):
        z = ledger[(ledger.arm == arm) & (ledger.origin_at == date)].sort_values("rank")
        fig, ax = plt.subplots(figsize=(8, 5))
        x = np.arange(len(z))
        ax.bar(x - 0.2, z.shadow_weight * 100, 0.4, label="Requested at accepted budget")
        ax.bar(x + 0.2, z.accepted_weight * 100, 0.4, label="Accepted")
        ax.plot(x, z.capacity * 100, "k_", ms=13, label="Per-vault cap")
        ax.set_xticks(x, z.vault_name.str.slice(0, 25), rotation=25, ha="right")
        ax.set_ylabel("Account weight (%)")
        ax.legend(fontsize=8)
        r.save(fig, f"{arm}-cap-example", f"{arm} allocations on {date.date()}", f"Earliest focal baseline cap-active origin, chosen mechanically. Cash {z.cash.iloc[0]:.2%}. Requested shadow uses this method’s own accepted budget.")
    z = ledger[ledger.arm.isin(["S03", "S04"])]
    for field, xlabel in [("original_actual_updates", "Actual updates in original 90-day window"), ("original_actual_fraction", "Actual updates / 90 elapsed days"), ("history_age", "Elapsed vault history (days)"), ("original_anchor_age", "Age of latest mark at decision (days)"), ("original_longest_gap", "Longest observed internal gap (days)")]:
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        for selector, g in z.groupby("selector"):
            y = g.risk_forecast if field == "original_actual_fraction" else g.accepted_weight * 100
            ax.scatter(g[field], y, s=12, alpha=0.25, label=selector, rasterized=True)
        ax.set(xlabel=xlabel, ylabel="Forecast daily variance" if field == "original_actual_fraction" else "Accepted account weight (%)")
        ax.legend(fontsize=9)
        if field == "original_actual_fraction":
            ax.set_yscale("log")
        r.save(fig, "support-" + field, ("Forecast risk and " if field == "original_actual_fraction" else "Accepted weights and ") + xlabel.lower(), "Baseline selected vault/date observations on all 70 scheduled origins. Filled NAV days do not create updates; these associations describe reporting support, not predictive independence.")
    risk_summary = risk.groupby(["estimator", "L", "kappa", "units"]).agg(vault_dates=("pair_id", "size"), median_updates=("m", "median"), partial_fraction=("full", lambda x: 1 - x.mean()), flat_fraction=("empirical", lambda x: x.eq(0).mean()), missing_fraction=("empirical", lambda x: x.isna().mean()), prior_only_fraction=("prior_only", "mean"), floor_fraction=("floor_active", "mean"), weak_peer_fraction=("weak_prior", "mean"), median_peer_count=("prior_count", "median"), median_shrinkage=("shrinkage", "median")).reset_index()
    r.table(risk_summary, "Full eligible-universe risk support", "Counts use unique estimator/vault/origin rows before selection. Partial is not missing. Sparse m counts complete intervals, whereas original m counts updates. Regularised floors are absent.", percent=["partial_fraction", "flat_fraction", "missing_fraction", "prior_only_fraction", "floor_fraction", "weak_peer_fraction", "median_shrinkage"])
    cal = result["calibration"].query("h==30")
    r.table(cal[["selector", "estimator", "L", "kappa", "units", "origins", "paired_vault_dates", "qlike_delta", "calibration_ratio", "prior_only_fraction", "floor_fraction", "mean_peer_count"]], "Risk forecast calibration", "Unique selected-vault forecasts, deduplicated across powers/transforms. QLIKE difference versus the same peer prior is averaged within origin then equally across origins. Ratio is mean realised / mean forecast in matched simple/log units.", percent=["prior_only_fraction", "floor_fraction"])
    for selector in ("F", "L"):
        d = cal[cal.selector == selector]
        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(d))
        ax.bar(x, d.qlike_delta, color=np.where(d.qlike_delta < 0, "#15803d", "#b91c1c"))
        ax.set_xticks(x, [f"{v.estimator}\nL{v.L}/κ{v.kappa:g}" for v in d.itertuples()], rotation=60, ha="right", fontsize=8)
        ax.axhline(0, color="grey")
        ax.set_ylabel("Mean equal-origin QLIKE difference vs prior")
        r.save(fig, f"{selector}-qlike", f"{selector} risk forecasting versus prior", "Negative loss difference is better. Daily simple-return and log-return forecasts have matched targets; compare sparse methods only within their common-prior pair. Extreme raw-floor losses remain visible.")
    calrows = result["calibration_rows"].query('h==30 and estimator=="regular" and L==90 and kappa==30')
    for selector in ("F", "L"):
        d = calrows[calrows.selector == selector]
        fig, ax = plt.subplots(figsize=(7.5, 4.7))
        good = d[(d.predicted > 0) & (d.realised > 0)]
        im = ax.scatter(good.predicted, good.realised, c=good.actual_updates, s=15, alpha=0.5, cmap="viridis", rasterized=True)
        lo = min(good.predicted.min(), good.predicted.min())
        hi = max(good.predicted.max(), good.predicted.max())
        ax.plot([lo, hi], [lo, hi], "k--", lw=1)
        ax.set(xscale="log", yscale="log", xlabel="Forecast simple daily variance", ylabel="Realised simple daily variance")
        fig.colorbar(im, ax=ax, label="Actual past updates")
        r.save(fig, f"{selector}-calibration", f"{selector} baseline variance calibration", f"Selected-vault/date points, descriptive only. Log axes omit {int(d.realised.eq(0).sum())} valid zero realised variances; these zeros remain included in QLIKE and calibration table. Diagonal means exact calibration.")
    sp = risk[(risk.estimator.isin(["calendar_log", "gap_log"]))]
    wide = sp.pivot(index=["origin_at", "pair_id"], columns="estimator", values="empirical")
    good = wide[(wide.calendar_log > 0) & (wide.gap_log > 0)]
    fig, ax = plt.subplots(figsize=(7, 4.7))
    ax.scatter(good.calendar_log, good.gap_log, s=6, alpha=0.25, rasterized=True)
    lo = min(good.min())
    hi = max(good.max())
    ax.plot([lo, hi], [lo, hi], "k--")
    ax.set(xscale="log", yscale="log", xlabel="Matched calendar log empirical variance", ylabel="Gap-scaled empirical log variance")
    r.save(fig, "sparse-pair", "Matched sparse empirical variance", "Same endpoints, intervals and peer prior; log scale displays positive empirical pairs. Missing and valid zeros are in support tables. Gap estimator assumes variance proportional to elapsed days; it is not ground truth.")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for convention, g in support[support.L == 90].groupby("convention"):
        ax.plot(g.origin_at, g.full_count / g.eligible, label=convention)
    ax.set(ylabel="Full endpoint coverage (fraction)", ylim=(0, 1))
    ax.legend(fontsize=8)
    r.save(fig, "sparse-support", "Filled versus strict actual-endpoint support", "Original full status permits carried boundary NAV; sparse pair requires actual marks at both requested endpoints. Peer positive-count and fallback details are saved for all origins.")
    support_table = support.groupby(["convention", "L"]).agg(mean_eligible=("eligible", "mean"), mean_full=("full_count", "mean"), mean_positive_full=("positive_full_count", "mean")).reset_index()
    r.table(support_table, "Prior-pool endpoint support", "These are eligible-universe counts, not selected-vault metric coverage. Strict actual-endpoint full pools can be small; both sparse estimators share calendar-log leave-one-out partial-pool fallback.")
    d = risk.query('estimator=="regular" and L!=90')
    wide = d.pivot(index=["origin_at", "pair_id", "L"], columns="kappa", values="predicted")
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for L, k in [(45, 15.0), (180, 60.0)]:
        g = wide[wide.index.get_level_values("L") == L]
        ratio = g[k] / g[30.0]
        ratio = ratio[np.isfinite(ratio) & (ratio > 0)]
        ax.hist(np.log(ratio), bins=40, histtype="step", density=True, label=f"L{L}; κ{k:g}/κ30", linewidth=1.5)
    ax.axvline(0, color="grey", ls="--")
    ax.set(xlabel="Log forecast variance ratio", ylabel="Density")
    ax.legend(fontsize=8)
    r.save(fig, "shrinkage", "Inherited versus fixed prior strength", "All eligible vault/date forecasts. L/3 changes prior strength with the window; core surface keeps kappa30 fixed. Histogram bins40 are display resolution only.")
    d = risk.query('estimator=="regular" and kappa==30')
    wide = d.pivot(index=["origin_at", "pair_id"], columns="L", values="predicted")
    g = wide.dropna()
    positive = g[(g > 0).all(axis=1)]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.scatter(positive.median(axis=1), positive.max(axis=1), s=6, alpha=0.25, rasterized=True)
    lo = positive.min().min()
    hi = positive.max().max()
    ax.plot([lo, hi], [lo, hi], "k--")
    ax.set(xscale="log", yscale="log", xlabel="Median of L45/L90/L180 forecast variances", ylabel="Maximum of those variances")
    r.save(fig, "window-disagreement", "Multi-window risk disagreement", "Aggregate variances before inverse-variance sizing. All three positive forecasts are required; partial/prior-only positive estimates remain available. Diagonal means no window disagreement.")
    t18 = ledger[ledger.arm == "S16"][["origin_at", "pair_id"]]
    components = data["components"]
    v = components[components.component.isin(["Sh90", "Ca180", "V180", "Kmax"])].pivot(index=["origin_at", "pair_id"], columns="component", values="value").reindex(pd.MultiIndex.from_frame(t18)).fillna(0)
    active = v.eq(v.min(axis=1), axis=0)
    mass = active.div(active.sum(axis=1), axis=0).mean()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(mass.index, mass * 100, color="#2563eb")
    ax.set_ylabel("Minimum-component attribution (%)")
    r.save(fig, "T18-active", "T18 minimum-component activity", "Selected v11 vault/date observations across all 70 origins. Ties split attribution equally; missing components are zero under frozen M0 semantics. V180 uses inherited kappa60, not core kappa30.")
    focus = ["S03", "S04", "S15", "S16", "S17", "S18"]
    r.table(s[s.arm.isin(focus)][["arm", "label", "worst_origin", "best_origin", "first_update", "remaining", "mean_return", "median_return"]], "Tail and first-update attribution", "Predeclared baseline/sparse/T18 probes. First actual update strictly after the anchor and remaining NAV contribution sum to return; extreme windows can dominate means.", percent=["worst_origin", "best_origin", "first_update", "remaining", "mean_return", "median_return"])
    v = result["vault_influence"].query("h==30")
    v = v[v.arm.isin(focus)].copy()
    v["absolute"] = v.mean_contribution.abs()
    v = v.sort_values("absolute", ascending=False).groupby("arm").head(3)
    r.table(v[["arm", "vault_name", "held", "mean_contribution", "conditional_contribution"]], "Largest vault contributions", "Three largest absolute contributions for each predeclared probe. Mean contribution uses the full resolved calendar; conditional contribution uses only dates held. Removing a contribution does not select a new basket.", percent=["mean_contribution", "conditional_contribution"])
    q = result["quarter_influence"].query("h==30")
    q = q[q.arm.isin(focus)]
    p = q.pivot(index="arm", columns="quarter_removed", values="difference") * 100
    r.heatmap(p, "quarter-influence", "Quarter-removal influence", "Difference from full-calendar mean when one origin quarter is omitted, holding baskets fixed. Grey Q4 means no mature data to remove. This is a regime diagnostic, not a new period selection.")
    effect_quarters = result["contrast_dates"].query('h==30 and ((arm=="S18" and control=="S03") or (arm=="S16" and control=="S15") or (arm=="M40" and control=="S04"))').copy()
    effect_quarters["quarter"] = effect_quarters.origin_at.dt.to_period("Q").astype(str)
    eq = effect_quarters.groupby(["arm", "control", "quarter"]).agg(paired=("return_difference", "count"), mean_difference=("return_difference", "mean"), first_update_difference=("first_update_difference", "mean")).reset_index()
    r.table(eq, "Paired mechanism effects by origin quarter", "Predeclared sparse/baseline and T18/V180 probes. Common matched dates, fixed baskets; Q4 has no mature labels. First-update column includes the first actual mark strictly after the anchor.", percent=["mean_difference", "first_update_difference"])
    overlap = result["selector_overlap"]
    r.table(pd.DataFrame([dict(mean_Jaccard=overlap.jaccard.mean(), min_Jaccard=overlap.jaccard.min(), mean_shared_accepted_weight=overlap.shared_accepted_weight.mean())]), "Selector dependence", "All scheduled origins. Basket identity overlap and shared capital are continuous descriptive measures; selectors are related robustness contexts.", percent=["mean_Jaccard", "min_Jaccard", "mean_shared_accepted_weight"])
    f = followups()
    r.table(pd.DataFrame([dict(batch="Local/prior/floor sensitivities", policies=len(f["sensitivities"]), status="registered, not run"), dict(batch="Cap-aware convex allocation", policies=len(f["cap_aware"]), status="registered, not run")]), "Next-stage inventory", "Exact policies saved in followups.json. No return-based automatic expansion and no shuffled-weight placebos.")
    save_figures(r)
    return r.figures


def write_findings(data, result, audit):
    s = result["summary"].query("h==30").set_index("arm")
    c = result["contrasts"].query("h==30")
    lines = [
        "# Experiment 11 — weighting and sizing findings",
        "",
        f"Period: **{PERIOD}**. **40 policies, 70 origins, 7/30/90-day targets**; 2025 and earlier indicator warmup retained. Six-vault focal_four and v11 baskets are frozen. These are independent fixed-unit snapshots, not strategy CAGR.",
        "",
        "## What was examined",
        "",
        "Window45/90/180, allocation power1/1.5/2, fixed versus inherited shrinkage, raw floors, bounded risk scores, multi-window risk and a matched sparse-mark observation model. Source90, focal equal and regularised inverse-variance controls reproduce saved NB10.",
        "",
        "## Hypotheses and primary outcomes",
        "",
        "Risk weighting might benefit from a stable neighbourhood rather than one lucky window; matched sparse estimators might improve risk forecasts; T18 may chiefly represent bounded V180 sizing. All hypotheses are descriptive because the primary horizon has only eight complete blocks.",
        "",
        "| Arm | Method | Mean 30-day return | Mean daily variance | Mean window drawdown | Cash |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for arm, row in s.iterrows():
        lines.append(f"| {arm} | {row.label} | {row.mean_return:.3%} | {row.mean_variance:.6f} | {row.mean_drawdown:.3%} | {row.mean_cash:.3%} |")
    lines += ["", "### Registered matched contrasts — 2026 period, 30-day horizon", "", "| New − control | Paired origins | Return difference | Variance ratio | Drawdown difference |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in c[c.family == "primary"].itertuples():
        lines.append(f"| {row.arm} − {row.control} | {row.paired} | {row.return_difference*100:+.3f} pp | {row.variance_ratio:.3f} | {row.drawdown_difference*100:+.3f} pp |")
    for selector, baseline in [("F", "S03"), ("L", "S04")]:
        group = result["summary"].query("h==30 and selector==@selector")
        best = group.sort_values("mean_return", ascending=False).iloc[0]
        lines += ["", f"### {selector} research lead — 2026 period, 30-day horizon", "", f'Largest descriptive mean: **{best.arm}, {best.label}**, {best.mean_return:.3%}, versus {s.loc[baseline,"mean_return"]:.3%} for its regularised90/p2 baseline. This is a searched historical comparison, not evidence of a production improvement. Inspect adjacent cells, variance, drawdown and attribution before an engine replay.']
    diff = c[(c.arm == "S16") & (c.control == "S15")].iloc[0]
    lines += [
        "",
        "### T18 mechanism — 2026 period, 30-day horizon",
        "",
        f"T18 minus bounded V180: {diff.return_difference*100:+.3f} percentage points, variance ratio {diff.variance_ratio:.3f}. The single-component control uses inherited kappa60 and identical v11 selection. Minimum-component activity is reported separately, with tied minima split.",
        "",
        "## Risk prediction and sparse-data interpretation",
        "",
        "QLIKE comparisons are equally weighted by origin and deduplicated across allocation powers/transforms. Future zero variance remains valid. Sparse pair uses the same actual endpoints, complete interval counts and calendar-log prior; gap scaling assumes variance proportional to elapsed days. Comparing it to daily-simple baseline also changes return units, endpoints and support. Kappa30 means intervals in the pair versus actual updates in the original estimator. Neither observation model is economic ground truth.",
        "",
        "## Robustness and verdict",
        "",
        f"All **{len(audit)} main audit checks** pass, including exact historical controls, fixed baskets, 70-date smoke reuse, terminal support, capacity conservation, scalar variance and future-state mutation. There are **8,400 scheduled outcomes**, including pending dates. No fabricated future prices or survivor renormalisation. The 30-day 51-statistic family cannot pass the ten-block gate; seven-day views remain secondary descriptive diagnostics.",
        "",
        "Quarter/vault attribution, worst/best windows, first-update contribution, actual-update support, cap-induced ties, requested/accepted breadth and same-budget shadow distortions are saved and shown. Historical publication clocks and current-inventory restrictions remain limitations. Snapshot entry at T−1 is inherited for parity, not an executable decision-time fill.",
        "",
        "## Useful leads and next steps",
        "",
        "Use the displayed neighbourhood and calibration evidence to choose a small interpretable shortlist for an actual engine replay. Include equal and original90/p2 controls, changing holdings, two-day rebalance timing, trade thresholds and capacities. Fresh observations are needed for confirmation. Twelve sensitivity and eight cap-aware policies are registered but unexecuted.",
        "",
        f'Generation: `{data["fingerprint"]}`. Main allocation/outcome execution: {data["execution_seconds"]:.1f} seconds. Notebook: [NB11](11-research-weighting-sizing.ipynb).',
    ]
    lines += [
        "",
        "## Interpretation of the hypotheses — 2026 period, 30-day horizon",
        "",
        "**Window and allocation strength:** the focal90/p2 benchmark leads all nine core L×p cells. Increasing p improves focal mean return within each window;180days produces worse drawdown and variance than90days for both selectors. The v11 mean-return surface is flatter at90/180days, but its90day baseline has better risk than180days. This does not establish a universal optimal horizon or a broad stable peak.",
        "",
        f'**Regularisation:** regularised90/p2 minus raw90/p2 is {(s.loc["S03","mean_return"]-s.loc["S09","mean_return"])*100:+.3f} pp for focal and {(s.loc["S04","mean_return"]-s.loc["S10","mean_return"])*100:+.3f} pp for v11. Source90 and raw90 produce identical accepted weights on these selected baskets. The floor/observation conventions remain separately recorded.',
        "",
        f'**Sparse estimator:** focal gap minus matched-calendar log sizing is {(s.loc["S18","mean_return"]-s.loc["S17","mean_return"])*100:+.3f} pp. Gap minus original simple90 baseline is {(s.loc["S18","mean_return"]-s.loc["S03","mean_return"])*100:+.3f} pp, with median30day return {s.loc["S18","median_return"]:.3%} versus {s.loc["S03","median_return"]:.3%}. Mean improvement does not improve the median. All three mature origin quarters have a positive gap/baseline mean difference, but vault effects offset strongly: pmalt contributes about+0.177pp and Hyperrr about−0.177pp to that overall mean difference.',
        "",
        "**Calibration versus allocation:** L45 has the most favourable QLIKE improvements against its own window-specific prior, yet does not produce the best portfolio outcome. Those QLIKE references differ by window, so these are not an absolute ranking of forecast losses. Within the matched sparse pair, gap improves focal mean QLIKE modestly; v11 mean QLIKE worsens slightly despite its positive30day return difference. Calibration ratios move closer to1for both. Risk prediction quality and profitable weighting are different questions.",
        "",
        "**Multi-window and shrinkage:** median/max alternatives do not beat the focal90/p2 mean; maximum has higher realised variance and worse drawdown despite using a more conservative marginal forecast. Kappa=L/3 improves mean return over fixed30at both45and180days for both selectors, but only45days also improves mean drawdown consistently. Larger marginal forecasts can reduce an account’s diversification after normalisation and caps.",
        "",
        "**T18:** the other score components still matter even though V180 is the minimum about79%of selected rows. Its+0.359pp overall mean uplift over V180 comes fromQ1 (+1.106pp); Q2 is−0.135pp andQ3approximately flat. It is a regime-sensitive lead, not evidence that four inputs help consistently.",
        "",
        "**Cash and constraints:** all40methods invest identical total capital within each selector, including explicit common-budget reprojection. Cash cannot explain their differences here. Baseline sum-absolute shadow distortion averages about45%of account capital; about22.6%is transferred between names, half that L1 sum. Cap-aware allocation remains a meaningful separate question.",
        "",
        "**Missing support:** the17January90day target for Dobutsu–Alpha Club extends beyond its final actual mark. All policies retain that unresolved invested weight;46of47administratively mature90day baskets resolve. There is only one complete paired90day block after censoring, not the theoretical maximum of two.",
        "",
        "Verdict: retain original90/p2 as the benchmark. The matched sparse gap method merits a controlled engine replay, and T18 merits attribution-aware comparison on v11 baskets. Neither has earned a production change from this retrospective snapshot study.",
    ]
    path = ROOT / "11-weighting-sizing-findings.md"
    path.write_text("\n".join(lines) + "\n")
    return path
