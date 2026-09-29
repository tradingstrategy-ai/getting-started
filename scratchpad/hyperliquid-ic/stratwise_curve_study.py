"""Descriptive curve discovery; no backtest or prospective performance claim."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_artifacts-stratwise"
OUT.mkdir(exist_ok=True)
d = pd.read_parquet(ROOT / "_artifacts-rewrite/observations.parquet")
m = pd.read_csv(ROOT / "_artifacts-rewrite/vault-metadata.csv").set_index("address")
current = json.loads((Path.home() / ".tradingstrategy/vaults/downloads/vault-universe.json").read_text())
lookup = {str(x["address"]).lower(): x for x in current["vaults"] if "address" in x}
end = pd.Timestamp("2026-09-12 23:59:59")
start = pd.Timestamp("2026-07-16")
ref = "0x0ff219ac20596b457558341bc410bc7a08a1394c"
curves = {}
rows = []
for a, g in d[d.timestamp.le(end)].groupby("address"):
    g = g.sort_values("timestamp").set_index("timestamp")
    s = g.share_price.resample("1D").last().dropna()
    s = s[s.index >= start]
    if len(s) < 20 or (end.normalize() - s.index[-1]).days > 7 or (s <= 0).any():
        continue
    span = (s.index[-1] - s.index[0]).days
    if span <= 0:
        continue
    r = s.pct_change().dropna()
    days = s.index.to_series().diff().dt.days.iloc[1:]
    daily = r[days.eq(1)]
    growth = s.iloc[-1] / s.iloc[0] - 1
    log = np.log(s / s.iloc[0])
    t = (s.index - s.index[0]).days.values
    fit = np.polyval(np.polyfit(t, log, 1), t)
    rsq = 1 - np.sum((log - fit) ** 2) / np.sum((log - log.mean()) ** 2) if log.var() > 0 else np.nan
    gains = r.clip(lower=0)
    top3 = gains.nlargest(3).sum() / gains.sum() if gains.sum() > 0 else np.nan
    windows = s.pct_change(7) if days.eq(1).all() else pd.Series(dtype=float)
    info = lookup.get(a, {})
    old = m.loc[a] if a in m.index else {}
    name = info.get("name") or old.get("name") or a
    rows.append(dict(address=a, name=name, slug=info.get("vault_slug") or old.get("vault_slug", ""), observed_days=len(s), span_days=span, coverage=len(s) / (span + 1), max_gap_days=days.max(), return_pct=100 * growth, cagr_pct=100 * ((1 + growth) ** (365 / span) - 1), vol_pct=100 * daily.std() * np.sqrt(365), sharpe=daily.mean() / daily.std() * np.sqrt(365) if daily.std() > 0 else np.nan, max_dd_pct=100 * (s / s.cummax() - 1).min(), r_squared=rsq, top3_gain_share=top3, positive_7d_share=(windows.dropna() > 0).mean(), tvl=float(g.total_assets.iloc[-1]), zero_return_share=(r == 0).mean()))
    curves[a] = s
f = pd.DataFrame(rows)
f.to_csv(OUT / "all-curves.csv", index=False)
# Broad discovery screen; final judgements require the actual charts.
c = f[(f.cagr_pct.between(8, 150)) & (f.vol_pct < 30) & (f.max_dd_pct > -10) & (f.tvl >= 7500) & (f.coverage >= 0.8)].sort_values("r_squared", ascending=False)
selected = list(dict.fromkeys([ref] + c.address.head(19).tolist()))
c[c.address.isin(selected)].to_csv(OUT / "discovery-candidates.csv", index=False)
for page in range((len(selected) + 9) // 10):
    fig, axs = plt.subplots(5, 2, figsize=(14, 17))
    for ax, a in zip(axs.flat, selected[page * 10 : (page + 1) * 10]):
        s = curves[a]
        row = f.set_index("address").loc[a]
        ax.plot(s.index, 100 * (s / s.iloc[0] - 1), marker=".", ms=3)
        ax.set_title(f'{row["name"]}\nCAGR {row.cagr_pct:.1f}%  vol {row.vol_pct:.1f}%  DD {row.max_dd_pct:.1f}%  top3 {row.top3_gain_share:.0%}', fontsize=10)
        ax.set_ylabel("Cumulative gross return %")
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(OUT / f"curve-review-{page+1}.png", dpi=110)
    plt.close(fig)
print(f[f.address.isin(selected)].sort_values("r_squared", ascending=False).to_string(index=False))
# Manual review set, chosen after viewing the discovery charts.
names = ["PF1", "Passivbot Canon", "FuturAI Labs - High Sharpe, Medium Volatility", "FuturAI Labs - High Sharpe, Low Volatility "]
chosen = [ref] + f[f.name.isin(names)].address.tolist()
fig, axs = plt.subplots(len(chosen), 1, figsize=(13, 3 * len(chosen)))
full_rows = []
for ax, a in zip(axs, chosen):
    g = d[(d.address == a) & d.timestamp.le(end)].sort_values("timestamp").set_index("timestamp")
    s = g.share_price.resample("1D").last().dropna()
    s = s[s > 0]
    name = "StratWise" if a == ref else f.set_index("address").loc[a, "name"]
    ax.plot(s.index, 100 * (s / s.iloc[0] - 1))
    ax.axvline(start, color="orange", ls="--")
    ax.set_title(name)
    ax.grid(alpha=0.3)
    full_rows.append(dict(address=a, name=name, first=str(s.index[0].date()), last=str(s.index[-1].date()), observed_days=len(s), full_return_pct=100 * (s.iloc[-1] / s.iloc[0] - 1), full_max_dd_pct=100 * (s / s.cummax() - 1).min()))
fig.tight_layout()
fig.savefig(OUT / "manual-full-histories.png", dpi=110)
plt.close(fig)
pd.DataFrame(full_rows).to_csv(OUT / "manual-full-histories.csv", index=False)
r = pd.concat({a: curves[a].pct_change() for a in chosen}, axis=1)
r.columns = ["StratWise" if a == ref else f.set_index("address").loc[a, "name"] for a in chosen]
r.corr().to_csv(OUT / "manual-candidate-correlations.csv")
print(pd.DataFrame(full_rows).to_string(index=False))
print(r.corr().round(2).to_string())
