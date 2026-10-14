"""Attribution and readable conclusions for the completed NB12 generation."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import display, Markdown
from allocation_followup import ROOT, PERIOD


def render_review(data):
    """Expose profit concentration and quarter stability without new searches."""
    folder = data["artifact"]
    s = pd.read_parquet(folder / "engine_summary.parquet").set_index("Arm")
    p = pd.read_parquet(folder / "engine_position_attribution.parquet")
    v = pd.read_parquet(folder / "engine_vault_attribution.parquet")
    contrasts = []
    influence = []
    for selector, base, source in [("F", "S03", "source_focal"), ("L", "S04", "source_v11")]:
        candidates = s[s.Selector.eq(selector)].drop(index=[base, source], errors="ignore")
        arm = candidates.sort_values(["CAGR", "Sharpe"], ascending=False).index[0]
        for control in (base, source):
            new = v[v.Arm.eq(arm)].set_index("Vault").PnL
            old = v[v.Arm.eq(control)].set_index("Vault").PnL
            delta = new.subtract(old, fill_value=0).sort_values(ascending=False)
            gap = float(s.loc[arm, "Final equity (USD)"] - s.loc[control, "Final equity (USD)"])
            assert np.isclose(delta.sum(), gap, atol=1.0)
            for name, value in delta.items():
                influence.append(dict(Selector=selector, Arm=arm, Control=control, Vault=name, **{"PnL difference (USD)": value, "Total equity difference (USD)": gap}))
            contrasts.append(dict(Selector=selector, Arm=arm, Control=control, **{"CAGR difference (pp)": 100 * (s.loc[arm, "CAGR"] - s.loc[control, "CAGR"]), "Sharpe difference": s.loc[arm, "Sharpe"] - s.loc[control, "Sharpe"], "Drawdown difference (pp)": 100 * (s.loc[arm, "Maximum drawdown"] - s.loc[control, "Maximum drawdown"]), "Equity difference (USD)": gap}))
    f = pd.DataFrame(influence)
    f.to_parquet(folder / "engine_paired_vault_influence.parquet", index=False)
    display(Markdown(f"### Engine improvements against both controls — {PERIOD}\n\nCompare the highest observed candidate CAGR per selector with its regularised benchmark and original strategy control. This selection is retrospective; it is a diagnostic, not validation."))
    display(pd.DataFrame(contrasts).style.format({"CAGR difference (pp)": "{:+.2f}", "Sharpe difference": "{:+.2f}", "Drawdown difference (pp)": "{:+.2f}", "Equity difference (USD)": "${:+,.0f}"}).background_gradient(subset=["CAGR difference (pp)", "Sharpe difference", "Drawdown difference (pp)"], cmap="RdYlGn").hide(axis="index"))
    display(Markdown(f"### Vault contributions to candidate improvements — {PERIOD}\n\nLargest positive and negative PnL differences are shown for each comparison. Removing a contribution is an influence diagnostic; it does not recreate a portfolio without that vault. Full attribution reconciles to the equity difference."))
    shown = pd.concat([pd.concat([g.nlargest(2, "PnL difference (USD)"), g.nsmallest(2, "PnL difference (USD)")]) for _, g in f.groupby(["Arm", "Control"])]).drop_duplicates()
    display(shown.style.format({"PnL difference (USD)": "${:+,.0f}", "Total equity difference (USD)": "${:+,.0f}"}).background_gradient(subset=["PnL difference (USD)"], cmap="RdYlGn").hide(axis="index"))
    display(Markdown(f"### Largest individual position profits — {PERIOD}\n\nShow the two largest position PnLs for each control and highest observed candidate. These are marked cash-flow profits, including still-open positions, rather than only realised trades."))
    arms = set(s.index[s.index.isin(["S03", "S04", "source_focal", "source_v11"])]) | {r["Arm"] for r in contrasts}
    selected = pd.concat([p[p.Arm.eq(a)].nlargest(2, "Final profit (USD)") for a in sorted(arms)])
    display(selected[["Arm", "Position id", "Vault", "Opened", "Closed", "Final profit (USD)"]].style.format({"Final profit (USD)": "${:,.0f}"}).hide(axis="index"))
    path = ROOT / "12-allocation-followup-findings.md"
    with path.open("a") as handle:
        handle.write(f"\n## Paired engine attribution — {PERIOD}\n\nLargest observed candidate per selector; searched historical comparison.\n\n")
        handle.write(pd.DataFrame(contrasts).to_markdown(index=False, floatfmt=".3f") + "\n\n")
        handle.write(shown.to_markdown(index=False, floatfmt=".3f") + "\n")
    return pd.DataFrame(contrasts)
