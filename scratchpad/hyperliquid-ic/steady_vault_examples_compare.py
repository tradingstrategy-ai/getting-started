"""Descriptive pre-entry comparisons, not a fitted selection rule."""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_artifacts-steady-examples"
OUT.mkdir(exist_ok=True)
cases = pd.read_csv(ROOT / "_artifacts-monthly-calibration/largest-loss-entry-features.csv")[["name", "address", "opened_at"]]
refs = pd.DataFrame(
    [
        ["StratWise", "0x0ff219ac20596b457558341bc410bc7a08a1394c", "2026-08-13"],
        ["Systemic L/S Grids", "0x07fd993f0fa3a185f7207adccd29f7a87404689d", "2026-08-13"],
    ],
    columns=cases.columns,
)
cases = pd.concat([refs, cases], ignore_index=True)
raw = pd.read_parquet(ROOT / "_artifacts-allocation-decomposition/inputs/vault-prices.parquet", columns=["address", "share_price"], filters=[("address", "in", cases.address.tolist())])
series = {a: g.share_price.sort_index().dropna().loc[lambda x: x > 0].groupby(level=0).last() for a, g in raw.groupby("address")}


def samples(s, end, days, step):
    # All observations precede their sampling boundary; weekly gaps are supported.
    boundaries = pd.DatetimeIndex([end - pd.Timedelta(days=k) for k in range((days // step) * step, -1, -step)])
    j = s.index.searchsorted(boundaries, side="left") - 1
    valid = j >= 0
    result = pd.Series(np.nan, index=boundaries)
    for date, k in zip(boundaries[valid], j[valid]):
        if date - s.index[k] <= pd.Timedelta(days=7):
            result.loc[date] = s.iloc[k]
    return result


def metrics(s, end, days):
    daily = samples(s, end, days, 1)
    weekly = samples(s, end, days, 7)
    r = daily.pct_change(fill_method=None).dropna()
    w = weekly.pct_change(fill_method=None).dropna()
    pre = s.loc[(s.index >= end - pd.Timedelta(days=days)) & (s.index < end)]
    valid = daily.dropna()
    result = dict(days_observed=(valid.index[-1] - valid.index[0]).days if len(valid) > 1 else 0, weeks=len(w), positive_weeks=(w > 0).mean(), median_week=w.median(), worst_week=w.min(), weekly_std=w.std(), best_week_share=w.clip(lower=0).max() / w.clip(lower=0).sum() if w.clip(lower=0).sum() > 0 else np.nan, drawdown=(pre / pre.cummax() - 1).min(), return_window=valid.iloc[-1] / valid.iloc[0] - 1 if len(valid) > 1 else np.nan, positive_days=(r > 0).mean(), daily_std=r.std(), path_efficiency=np.log(valid.iloc[-1] / valid.iloc[0]) / np.log(valid).diff().abs().sum() if len(valid) > 1 else np.nan)
    if len(valid) > 2:
        x = (valid.index - valid.index[0]).total_seconds() / 86400
        y = np.log(valid.values)
        residual = y - np.polyval(np.polyfit(x, y, 1), x)
        result["trend_residual_std"] = np.std(residual)
    return result


rows = []
future = []
fig, axes = plt.subplots(len(cases), 2, figsize=(13, 18))
for i, c in cases.iterrows():
    s = series[c.address]
    end = pd.Timestamp(c.opened_at)
    for days in [7, 14, 28, 60, 90]:
        rows.append(dict(name=c["name"], date=end, lookback=days, **metrics(s, end, days)))
    base = s.loc[s.index < end].iloc[-1]
    for h in [14, 30, 60]:
        stop = end + pd.Timedelta(days=h)
        p = s.loc[(s.index >= end) & (s.index < stop)]
        complete = stop <= pd.Timestamp("2026-09-09") and len(p) > 0 and stop - p.index[-1] <= pd.Timedelta(days=7)
        future.append(dict(name=c["name"], date=end, horizon=h, return_forward=p.iloc[-1] / base - 1 if complete else np.nan))
    for col, (lo, hi) in enumerate([(-28, 0), (0, 60)]):
        p = s.loc[(s.index >= end + pd.Timedelta(days=lo)) & (s.index < min(end + pd.Timedelta(days=hi), pd.Timestamp("2026-09-09")))]
        if len(p):
            norm = p.iloc[0] if col == 0 else base
            axes[i, col].plot((p.index - end).total_seconds() / 86400, 100 * (p / norm - 1), color="teal" if i < 2 else "darkorange")
        axes[i, col].set_title(f'{c["name"]} | {end.date()} | ' + ("before" if col == 0 else "after"))
        axes[i, col].set_ylabel("Return (%)")
        axes[i, col].grid(alpha=0.25)
        axes[i, col].set_xlim(lo, hi)
fig.supxlabel("Days relative to comparison / entry date")
fig.tight_layout()
fig.savefig(OUT / "before-after.png", dpi=140)
plt.close(fig)
df = pd.DataFrame(rows)
df.to_csv(OUT / "pre-entry-metrics.csv", index=False)
pd.DataFrame(future).to_csv(OUT / "forward-returns.csv", index=False)
# Same-date reference snapshots check sensitivity to the chosen reference date.
rows = []
for c in refs.to_dict("records"):
    for end in pd.to_datetime(["2026-08-01", "2026-08-13", "2026-09-01", "2026-09-09"]):
        rows.append(dict(name=c["name"], date=end, **metrics(series[c["address"]], end, 28)))
pd.DataFrame(rows).to_csv(OUT / "reference-sensitivity.csv", index=False)
print(df[df.lookback == 28].to_string(index=False))
print(pd.DataFrame(future).to_string(index=False))
