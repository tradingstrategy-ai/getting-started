"""Separate figures and concise tables for the NB12 follow-up."""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from sizing_study_design import PERIOD


def heading(title, description):
    display(Markdown(f"### {title} — {PERIOD}\n\n{description}"))


def table(frame, formats=None):
    style = frame.style.format(formats or {}, na_rep="Unavailable")
    for c in ("Mean 30-day return", "CAGR", "Sharpe", "Mean window drawdown", "Maximum drawdown"):
        if c in frame and frame[c].notna().any():
            style = style.background_gradient(subset=[c], cmap="RdYlGn")
    display(style.hide(axis="index"))


def figure(data, fig, name, title, description):
    heading(title, description)
    fig.tight_layout()
    p = data["artifact"] / f"{name}.png"
    fig.savefig(p, dpi=120, bbox_inches="tight")
    display(fig)
    plt.close(fig)
    data.setdefault("figures", []).append(str(p))


def snapshots(data, result):
    s = result["summary"]
    x = s[s.h.eq(30)].copy()
    labels = x.set_index("arm").label.to_dict()
    heading("Snapshot results; 30-day horizon", "Every row holds a fixed six-vault basket for 30 days. Means use resolved origins only; these returns are not annualised strategy results. X arms are the 12 sensitivities, C arms the eight cap-aware methods; remaining rows reproduce NB11 controls.")
    v = x[["arm", "label", "resolved", "mean_return", "median_return", "mean_drawdown", "mean_cash", "effective_N"]].rename(columns={"arm": "Arm", "label": "Method", "resolved": "Origins", "mean_return": "Mean 30-day return", "median_return": "Median return", "mean_drawdown": "Mean window drawdown", "mean_cash": "Cash", "effective_N": "Effective positions"})
    table(v, {"Mean 30-day return": "{:.3%}", "Median return": "{:.3%}", "Mean window drawdown": "{:.3%}", "Cash": "{:.2%}", "Effective positions": "{:.2f}"})
    heading("Reference reproduction and feasibility; 7/30/90-day horizons", "All ten reused NB11 controls are recalculated. Accepted weights and future returns must reproduce their saved values; optimiser pairs must share the invested budget.")
    display(result["checks"].style.hide(axis="index"))
    d = result["solver_diagnostics"]
    heading("Optimiser mechanisms; all 70 scheduled origins", "A solved allocation minimises the registered convex variance/diversification objective. Risk-contribution error need not fall when caps bind. Fallback status is explicit.")
    diag = d.groupby(["arm", "status"]).agg(origins=("origin_at", "size"), mean_objective_gain=("objective_gain", "mean"), max_KKT=("kkt", "max"), mean_weight_L1=("accepted_L1_difference", "mean")).reset_index()
    table(diag, {"mean_objective_gain": "{:.6f}", "max_KKT": "{:.2e}", "mean_weight_L1": "{:.3%}"})
    for selector in ("F", "L"):
        z = x[x.selector.eq(selector)].copy()
        base = z[z.arm.eq("S03" if selector == "F" else "S04")].iloc[0]
        for axis, title, description in [("L", "Lookback sensitivity", "Compare 75,90 and 105 days with the same inverse-variance power and 30-update prior strength."), ("kappa", "Prior strength sensitivity", "Compare 10,30 and 90 actual-update prior strengths at the same 90-day lookback.")]:
            zz = z[z.method.eq("regular") & (z.kappa.eq(30) if axis == "L" else z.L.eq(90))].sort_values(axis)
            fig, ax = plt.subplots(figsize=(7.5, 4))
            ax.plot(zz[axis], 100 * zz.mean_return, "o-", label="Mean 30-day return")
            ax.axhline(100 * base.mean_return, color="grey", ls=":", label="90-day / κ30 benchmark")
            ax.set(xlabel="Lookback (days)" if axis == "L" else "Prior strength (actual updates)", ylabel="Mean 30-day return (%)", title=f"{selector} {title.lower()} · 30 days\n{PERIOD}")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.2)
            figure(data, fig, f"{selector}-{axis}", f"{selector}: {title.lower()}; 30-day horizon", description)
        fig, ax = plt.subplots(figsize=(8, 5))
        colours = ["#dc2626" if a.startswith("C") else "#2563eb" if a.startswith("X") else "#6b7280" for a in z.arm]
        ax.scatter(-100 * z.mean_drawdown, 100 * z.mean_return, c=colours, s=40)
        groups = z.groupby([z.mean_drawdown.round(12), z.mean_return.round(12)], sort=False)
        offsets = {"S04": (-30, 10), "M39": (5, -13), "M40": (12, 8)}
        for (_, _), g in groups:
            r = g.iloc[0]
            text = "/".join(g.arm)
            ax.annotate(text, (-100 * r.mean_drawdown, 100 * r.mean_return), xytext=offsets.get(r.arm, (4, 4)), textcoords="offset points", fontsize=8)
        ax.scatter([-100 * base.mean_drawdown], [100 * base.mean_return], marker="*", s=180, color="#111827")
        ax.set(xlabel="Mean window drawdown magnitude (%) · lower is better", ylabel="Mean 30-day return (%)", title=f"{selector} return and drawdown · 30 days\n{PERIOD}")
        ax.grid(alpha=0.2)
        figure(data, fig, f"{selector}-scatter", f"{selector}: allocation trade-offs; 30-day horizon", "Blue: sensitivities; red: cap-aware methods; grey: controls; star: regularised 90-day benchmark. Compare methods within a selector. Arm names are listed in the results table.")
    out = result["outcomes"]
    pairs = []
    for a, b in [("C02", "C01"), ("C04", "C03"), ("C06", "C05"), ("C08", "C07")]:
        q = out[out.arm.eq(a) & out.h.eq(30)].merge(out[out.arm.eq(b) & out.h.eq(30)], on="origin_at", suffixes=("_new", "_old"))
        q = q[q.resolved_new & q.resolved_old]
        q["effect"] = q.return_new - q.return_old
        q["quarter"] = q.origin_at.dt.to_period("Q").astype(str)
        for quarter, g in q.groupby("quarter"):
            pairs.append(dict(pair=f"{a} − {b}", quarter=quarter, mean=g.effect.mean(), n=len(g)))
    pq = pd.DataFrame(pairs)
    pq.to_parquet(data["artifact"] / "cap_paired_quarters.parquet", index=False)
    pivot = pq.pivot(index="pair", columns="quarter", values="mean") * 100
    fig, ax = plt.subplots(figsize=(8, 4))
    scale = max(float(np.abs(pivot.to_numpy()).max()), 0.001)
    ax.grid(False)
    im = ax.imshow(pivot, cmap="RdYlGn", vmin=-scale, vmax=scale, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), pivot.columns)
    ax.set_yticks(range(len(pivot)), pivot.index)
    for i in range(len(pivot)):
        for j in range(len(pivot.columns)):
            n = pq[(pq.pair == pivot.index[i]) & (pq.quarter == pivot.columns[j])].n.iloc[0]
            ax.text(j, i, f"{pivot.iloc[i,j]:+.3f} pp\nn={n}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, label="Mean return difference (percentage points)")
    ax.set_title(f"Constrained minus projected allocations · 30 days\n{PERIOD}")
    figure(data, fig, "cap-quarter", "Constraint-aware paired effects by quarter; 30-day horizon", "Each comparison shares covariance, risk-budget target, support and invested budget. Positive cells favour solving with caps inside the objective. Q4 has no mature 30-day origin.")
    heading("Secondary horizons; 7 and 90 days", "Allocations are identical across horizons. The 90-day comparison has sparse independent support and one unresolved administratively mature basket; retain those limitations.")
    z = s[s.h.isin([7, 90])][["arm", "h", "mature", "resolved", "mean_return", "mean_drawdown"]]
    table(z, {"mean_return": "{:.3%}", "mean_drawdown": "{:.3%}"})
    return x


def replay(data, frame, runs, robust):
    heading("Full engine results; two-day rebalancing", "Actual engine runs start with $150,000, retain source hysteresis, entry/exit checks, trade thresholds and applicable redemption fees. Research allocations use a common simultaneous cap projection; the source v11 control retains its original sequential allocator. CAGR below belongs to the engine runs.")
    table(frame[["Arm", "Method", "CAGR", "Sharpe", "Sortino", "Maximum drawdown", "Final equity (USD)", "Mean cash weight", "Trades"]], {"CAGR": "{:.2%}", "Sharpe": "{:.2f}", "Sortino": "{:.2f}", "Maximum drawdown": "{:.2%}", "Final equity (USD)": "${:,.0f}", "Mean cash weight": "{:.2%}"})
    for selector in ("F", "L"):
        selected = [r for r in frame.itertuples(index=False) if r.Selector == selector]
        fig, ax = plt.subplots(figsize=(10, 5))
        for row in selected:
            arm = row.Arm
            eq = runs[arm]["equity"]
            ax.plot(eq.index, eq / 150000, label=arm, lw=2 if arm in ("S03", "S04") else 1.1)
        ax.set(xlabel="Date (UTC)", ylabel="Equity / initial capital", title=f"{selector} full engine equity\n{PERIOD}")
        ax.legend(ncol=4, fontsize=8)
        ax.grid(alpha=0.2)
        figure(data, fig, f"{selector}-equity", f"{selector}: engine equity curves", "Each curve carries holdings through time. The results table maps arm IDs to methods. Compare against the same selector’s regularised 90-day benchmark.")
        benchmark = "S03" if selector == "F" else "S04"
        run = runs[benchmark]
        from tradeexecutor.analysis.weights import calculate_asset_weights

        weights = calculate_asset_weights(run["result"].state).unstack(fill_value=0).fillna(0).resample("1D").last().ffill().fillna(0)
        account_equity = run["equity"].resample("1D").last().reindex(weights.index).ffill()
        assert np.allclose(weights.sum(axis=1), account_equity, rtol=1e-8, atol=1e-5)
        reserve = run["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        assert weights.drop(columns=[reserve]).gt(1e-5).sum(axis=1).max() <= 6
        weights = weights.div(account_equity, axis=0)
        weights.to_parquet(data["artifact"] / f"{selector}-absolute-weights.parquet")
        named = weights.drop(columns=[reserve]).mean().nlargest(10).index.tolist()
        other = [c for c in weights if c not in named + [reserve]]
        shown = weights[named].copy()
        shown[f"Other vaults ({len(other)})"] = weights[other].sum(axis=1)
        shown[reserve] = weights[reserve]
        fig, ax = plt.subplots(figsize=(11, 5))
        shown.plot.area(ax=ax, stacked=True, linewidth=0, colormap="tab20")
        ax.set(xlabel="Date (UTC)", ylabel="Absolute account weight", title=f"{selector} benchmark absolute asset weights\n{PERIOD}", ylim=(0, 1))
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=7)
        figure(data, fig, f"{selector}-weights", f"{selector}: benchmark absolute weights", "Weights include cash and sum to the whole account. The ten vaults with highest average exposure are named; all remaining vaults are grouped as Other. Absent vaults are zero at observed timestamps, so closed holdings are not forward-filled. At most six vaults are active; the complete weights table is saved.")
    heading("Tail and vault influence; full engine runs", "Positive-vault concentration is the largest vault’s final PnL divided by all positive vault PnL. Best-day contribution and kurtosis describe return concentration; attribution is reconciled to portfolio PnL.")
    table(robust, {"Best day": "{:.2%}", "Worst day": "{:.2%}", "Top positive vault share": "{:.1%}", "PnL residual (USD)": "{:.3f}"})
    fig, ax = plt.subplots(figsize=(10, 5))
    q = pd.DataFrame({arm: (r["equity"].resample("1D").last().ffill().pct_change(fill_method=None).fillna(0) + 1).groupby(r["equity"].resample("1D").last().index.to_period("Q")).prod() - 1 for arm, r in runs.items()}).T * 100
    ax.grid(False)
    im = ax.imshow(q, cmap="RdYlGn", aspect="auto", vmin=-max(abs(q.to_numpy()).max(), 1), vmax=max(abs(q.to_numpy()).max(), 1))
    ax.set_xticks(range(len(q.columns)), list(map(str, q.columns)))
    ax.set_yticks(range(len(q)), q.index)
    for i in range(len(q)):
        for j in range(len(q.columns)):
            ax.text(j, i, f"{q.iloc[i,j]:.1f}%", ha="center", va="center", fontsize=8)
    ax.set_title(f"Engine quarterly returns; Q4 partial\n{PERIOD}")
    fig.colorbar(im, ax=ax, label="Compounded quarterly return (%)")
    figure(data, fig, "engine-quarter", "Engine quarterly profit heatmap", "Each cell compounds that run’s daily equity returns within the quarter. Q4 covers only the available October days. This differs from averaging independent snapshot returns.")
    (data["artifact"] / "figure-manifest.json").write_text(json.dumps(data["figures"], indent=2))
