"""Entry-time NAV comparisons for the blacklist-off experiment."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from tqdm_loggable.auto import tqdm
from IPython.display import display

STRAT = "0x0ff219ac20596b457558341bc410bc7a08a1394c"
TARGETS = ["0x5290ab34acb59cfe1371baa5782eba14433d308f", "0xb7e7d0fdeff5473ed6ef8d3a762d096a040dbb18", "0x026a2e082a03200a00a97974b7bf7753ce33540f", "0x65aee08c9235025355ac6c5ad020fb167ecef4fe", "0x5108cd0a328ed28c277f958761fe1cda60c21aa8", "0x5a733b25a17dc0f26b862ca9e32b439801b1a8c7"]


def load(project):
    source = project / "_artifacts-leads-no-blacklists"
    out = project / "_artifacts-entry-forensics"
    out.mkdir(exist_ok=True)
    manifest = json.loads((source / "input-manifest.json").read_text())
    price_path = next(Path(x["path"]) for x in manifest if x["path"].endswith("vault-prices.parquet"))
    expected = next(x["sha256"] for x in manifest if x["path"] == str(price_path))
    with price_path.open("rb") as f:
        assert hashlib.file_digest(f, "sha256").hexdigest() == expected, "NB18 price snapshot changed"
    raw = pd.read_parquet(price_path, columns=["address", "chain", "share_price"]).reset_index()
    raw = raw[raw.chain.eq(9999)].copy()
    raw.address = raw.address.str.lower()
    raw.timestamp = pd.to_datetime(raw.timestamp)
    prices = {}
    for a, g in raw.groupby("address"):
        g = g.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
        s = pd.Series(pd.to_numeric(g.share_price).values, index=pd.DatetimeIndex(g.timestamp))
        prices[a] = s[s.gt(0) & np.isfinite(s)]
    membership = pd.read_csv(source / "universe-membership.csv")
    names = membership.set_index("address")["name"].str.strip().to_dict()
    names[STRAT] = "StratWise"
    for a in TARGETS:
        if "Sentiment" in names[a]:
            names[a] += " " + a[:8]
    positions = pd.read_csv(source / "engine-positions.csv", parse_dates=["opened_at", "closed_at"])
    positions = positions[positions["mode"].eq("off") & positions.period.eq("full") & positions.address.isin(TARGETS)].copy()
    trades = pd.read_csv(source / "engine-trades.csv", parse_dates=["date"])
    trades = trades[trades["mode"].eq("off") & trades.period.eq("full")]
    positions.to_csv(out / "positions.csv", index=False)
    return out, prices, names, positions, trades


def marks(s, dates):
    """Last actually observed mark at or before each timestamp, never backfill."""
    return s.reindex(pd.DatetimeIndex(dates), method="ffill")


def metrics(s, entry, days):
    cutoff = entry - pd.Timedelta(nanoseconds=1)
    known = s.loc[:cutoff]
    result = {"days": days, "available": False}
    if known.empty:
        return result
    end = entry - pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=days)
    result.update(age_days=(cutoff - known.index[0]).total_seconds() / 86400, last_mark_age_days=(cutoff - known.index[-1]).total_seconds() / 86400)
    if known.index[0] > start:
        return result
    grid = pd.date_range(start, end, freq="D")
    p = marks(known, grid)
    r = p.pct_change().dropna()
    lr = np.log(p).diff().dropna()
    obs = known.loc[start:end]
    gaps = np.diff(np.r_[start.value, obs.index.as_unit("ns").asi8, end.value]) / 86400e9
    weekly = marks(known, pd.date_range(end - pd.Timedelta(days=7 * (days // 7)), end, freq="7D")).pct_change().dropna()
    dd = p / p.cummax() - 1
    positive = lr.clip(lower=0).sum()
    result.update(
        available=True,
        return_=p.iloc[-1] / p.iloc[0] - 1,
        volatility=r.std() * np.sqrt(365),
        sortino=r.mean() / np.sqrt(np.mean(np.minimum(r, 0) ** 2)) * np.sqrt(365) if (r < 0).any() else np.nan,
        sharpe=r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else np.nan,
        max_drawdown=dd.min(),
        ulcer=np.sqrt(np.mean(dd**2)),
        top2_gain_share=lr.nlargest(2).clip(lower=0).sum() / positive if positive > 0 else np.nan,
        return_without_best2=np.expm1(lr.sum() - lr.nlargest(2).clip(lower=0).sum()),
        path_efficiency=lr.sum() / lr.abs().sum() if lr.abs().sum() > 0 else np.nan,
        best_day=r.max(),
        worst_day=r.min(),
        kurtosis=r.kurt(),
        positive_week_share=(weekly > 0).mean(),
        median_week=weekly.median(),
        worst_week=weekly.min(),
        weeks=len(weekly),
        weekly_return_without_best=np.expm1(np.log1p(weekly).sum() - max(np.log1p(weekly).max(), 0)) if len(weekly) > 1 else np.nan,
        weekly_drawdown=(marks(known, pd.date_range(end - pd.Timedelta(days=7 * (days // 7)), end, freq="7D")) / marks(known, pd.date_range(end - pd.Timedelta(days=7 * (days // 7)), end, freq="7D")).cummax() - 1).min(),
        observations=len(obs),
        max_gap_days=gaps.max(),
        zero_day_share=(r == 0).mean(),
    )
    return result


def analyse(project):
    out, prices, names, positions, trades = load(project)
    rows = []
    entries = positions[["address", "opened_at"]].drop_duplicates()
    for e in entries.itertuples():
        for address, role in [(e.address, "selected"), (STRAT, "StratWise")]:
            for days in [7, 14, 30, 45, 60, 90]:
                rows.append(dict(entry_address=e.address, address=address, name=names[address], entry=e.opened_at, role=role, **metrics(prices[address], e.opened_at, days)))
    # Daily StratWise reference dates show its short-history metrics even when historic entries predate it.
    for date in pd.date_range(prices[STRAT].index.min().ceil("D"), "2026-09-08", freq="D"):
        for days in [7, 14, 30, 45, 60, 90]:
            rows.append(dict(entry_address=STRAT, address=STRAT, name="StratWise", entry=date, role="StratWise reference", **metrics(prices[STRAT], date, days)))
    features = pd.DataFrame(rows)
    features.to_csv(out / "pre-entry-features.csv", index=False)
    # Reconstruct the score formula on conservative midnight marks. This is not an exact replay of engine candle/cache ranking.
    reasons = []
    for e in positions.itertuples():
        m14 = metrics(prices[e.address], e.opened_at, 14)
        m45 = metrics(prices[e.address], e.opened_at, 45)
        m360 = metrics(prices[e.address], e.opened_at, 360)
        cs = np.clip((1 + m360.get("return_", np.nan)) ** (365 / 360) - 1, 0, 1)
        ss = np.clip(m45.get("sortino", np.nan) / 3, 0, 1)
        threshold = (1.15 if e.candidate == "floor15" else 1.20) ** (45 / 365) - 1 if e.candidate in ["floor15", "floor20"] else -0.16
        gate = m45 if e.candidate in ["floor15", "floor20"] else m14
        tx = trades[(trades.candidate == e.candidate) & (trades.position_id == e.position_id)]
        buys = tx[tx.quantity > 0]
        sells = tx[tx.quantity < 0]
        end = e.closed_at if pd.notna(e.closed_at) else pd.Timestamp("2026-09-08")
        pp = marks(prices[e.address], pd.date_range(e.opened_at, end, freq="D")).dropna()
        entry_nav = marks(prices[e.address], [e.opened_at]).iloc[0]
        reasons.append(dict(candidate=e.candidate, address=e.address, name=names[e.address], position_id=e.position_id, entry=e.opened_at, exit=e.closed_at, pnl=e.pnl, gate_return_proxy=gate.get("return_", np.nan), gate_threshold=threshold, cagr_score_proxy=cs, sortino_score_proxy=ss, composite_proxy=0.6 * cs + 0.4 * ss if np.isfinite(cs + ss) else 0.0, unscored_proxy=not np.isfinite(cs + ss), buy_value=buys.value.abs().sum(), sell_value=sells.value.abs().sum(), buy_vwap=buys.value.abs().sum() / buys.quantity.sum(), sell_vwap=sells.value.abs().sum() / sells.quantity.abs().sum() if len(sells) else np.nan, nav_return_during_position=pp.iloc[-1] / entry_nav - 1 if len(pp) else np.nan, worst_from_entry=(pp / entry_nav - 1).min() if len(pp) else np.nan))
    reasons = pd.DataFrame(reasons)
    reasons.to_csv(out / "entry-explanations.csv", index=False)
    display(reasons.groupby("name").agg(positions=("pnl", "size"), pnl=("pnl", "sum"), unscored_proxy_share=("unscored_proxy", "mean")))
    worst = reasons.sort_values("pnl").groupby("address", sort=False).head(1)

    def plot_event(row, axes):
        entry = row.entry
        end = min(entry + pd.Timedelta(days=60), pd.Timestamp("2026-09-08"))
        for ax, before in zip(axes, [True, False]):
            dates = pd.date_range(entry - pd.Timedelta(days=90), entry - pd.Timedelta(days=1), freq="D") if before else pd.date_range(entry, end, freq="D")
            for a, label in [(row.address, names[row.address]), (STRAT, "StratWise")]:
                v = marks(prices[a], dates).dropna()
                # Only compare StratWise after a pick if it actually existed at entry.
                if not before and prices[a].index.min() > entry:
                    v = v.iloc[:0]
                if len(v) > 1:
                    ax.plot((v.index - entry).days, 100 * v / v.iloc[0], label=label)
                else:
                    ax.text(0.02, 0.05 if a == STRAT else 0.14, f"{label}: unavailable", transform=ax.transAxes, fontsize=8)
            ax.set_title(("Before entry (90d)" if before else "After entry (up to 60d)") + f" — {row.entry.date()}")
            if not before and pd.notna(row.exit) and row.exit <= end:
                ax.axvline((row.exit - entry).days, color="red", ls=":", label="Position closed")
            ax.grid(alpha=0.2)
            ax.set_xlabel("Days relative to entry")
            ax.set_ylabel("NAV rebased to 100")
            ax.legend(fontsize=7)
        axes[0].text(0, 1.12, f"{names[row.address]} {row.address[:8]} | {row.candidate} #{row.position_id} | P&L ${row.pnl:,.0f}", transform=axes[0].transAxes, fontsize=10)

    fig, axes = plt.subplots(len(worst), 2, figsize=(16, 4 * len(worst)))
    for row, ax in zip(worst.itertuples(), axes):
        plot_event(row, ax)
    fig.tight_layout()
    fig.savefig(out / "worst-entries-before-after.png", dpi=130)
    plt.show()
    with PdfPages(out / "all-entries-before-after.pdf") as pdf:
        for row in tqdm(reasons.sort_values(["address", "entry", "candidate"]).itertuples(), total=len(reasons), desc="Entry chart pages (usually under one minute)"):
            fig, axes = plt.subplots(1, 2, figsize=(15, 4))
            plot_event(row, axes)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    # Later template is deliberately separated from contemporary decision evidence.
    template_date = pd.Timestamp("2026-08-17")
    fig, axes = plt.subplots(len(worst), 2, figsize=(16, 4 * len(worst)))
    for row, axs in zip(worst.itertuples(), axes):
        for ax, before in zip(axs, [True, False]):
            offsets = np.arange(-30, 0) if before else np.arange(0, 15)
            for a, date, label in [(row.address, row.entry, names[row.address]), (STRAT, template_date, "StratWise later template: 17 Aug 2026")]:
                dates = date + pd.to_timedelta(offsets, unit="D")
                v = marks(prices[a], dates)
                ax.plot(offsets, 100 * v / v.iloc[0], label=label)
            ax.set_title(f"{names[row.address]} {row.entry.date()} — " + ("30 days before" if before else "14 days after"))
            ax.grid(alpha=0.2)
            ax.legend(fontsize=7)
            ax.set_ylabel("NAV rebased to 100")
    fig.suptitle("Shape comparison only: StratWise template is from a LATER period, unavailable at these entries", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(out / "later-template-before-after.png", dpi=130)
    plt.show()
    contemporary = reasons[reasons.entry.ge(prices[STRAT].index.min() + pd.Timedelta(days=14))].sort_values("pnl").drop_duplicates(["address", "entry"])
    if len(contemporary):
        fig, axes = plt.subplots(len(contemporary), 2, figsize=(16, 4 * len(contemporary)), squeeze=False)
        for row, axs in zip(contemporary.itertuples(), axes):
            plot_event(row, axs)
        fig.tight_layout()
        fig.savefig(out / "same-date-entries.png", dpi=130)
        plt.show()
    # Contemporary snapshots: avoids fabricating StratWise history for earlier entries.
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    for a in TARGETS + [STRAT]:
        s = prices[a]
        s = s.loc["2026-07-17":"2026-09-08"]
        if len(s):
            axes[0].plot(s.index, 100 * s / s.iloc[0], label=names[a] + " " + a[:8])
            axes[1].plot(s.index, 100 * (s / s.cummax() - 1), label=names[a])
    axes[0].set_title("Shared recent period: observed NAV (rebased at first observation in window)")
    axes[1].set_title("Drawdown from within-window peak (%)")
    for ax in axes:
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "contemporary-curves.png", dpi=140)
    plt.show()
    # Prespecified illustrative screens, not optimised to these labels. Missing data means unknown, not rejection.
    f = features[features.available & features.days.eq(30)].copy()
    rules = {
        "Return survives removing best two days": f.return_without_best2.gt(0),
        "Drawdown under 5%": f.max_drawdown.ge(-0.05),
        "Worst completed week above -3%": f.worst_week.ge(-0.03),
        "At least 75% positive completed weeks": f.positive_week_share.ge(0.75),
        "Top two days below 50% of gains": f.top2_gain_share.le(0.5),
    }
    rules["Combined: residual gain + drawdown + weekly loss"] = rules["Return survives removing best two days"] & rules["Drawdown under 5%"] & rules["Worst completed week above -3%"]
    rules["Weekly cadence: residual gain + drawdown + weekly loss"] = f.weekly_return_without_best.gt(0) & f.weekly_drawdown.ge(-0.05) & f.worst_week.ge(-0.03)
    screen = []
    for name, keep in rules.items():
        for role in ["selected", "StratWise", "StratWise reference"]:
            ix = f.role.eq(role)
            screen.append(dict(rule=name, cohort=role, n=int(ix.sum()), kept=int((keep & ix).sum()), keep_rate=float(keep[ix].mean())))
    screen = pd.DataFrame(screen)
    screen.to_csv(out / "screen-diagnostics.csv", index=False)
    display(screen)
    cols = ["return_", "volatility", "max_drawdown", "ulcer", "top2_gain_share", "return_without_best2", "positive_week_share", "median_week", "worst_week", "path_efficiency", "max_gap_days", "weekly_return_without_best", "weekly_drawdown"]
    med = f.groupby(["role", "name"])[cols].median()
    med.to_csv(out / "metric-medians.csv")
    display(med)
    worst.to_csv(out / "highlighted-positions.csv", index=False)
    display(worst[["name", "candidate", "entry", "exit", "pnl", "gate_return_proxy", "gate_threshold", "composite_proxy", "unscored_proxy", "nav_return_during_position", "worst_from_entry"]])
    availability = features[features.role.ne("StratWise reference")].groupby(["role", "days"]).available.agg(["sum", "count"])
    display(availability)
    availability.to_csv(out / "availability.csv")
    for days in [7, 14, 30, 45, 60, 90]:
        check = features[features.available & features.days.eq(days)]
        assert check.max_gap_days.le(days + 1e-6).all(), "Reporting gap units invalid"
    assert (features.loc[features.available, "last_mark_age_days"] >= 0).all()
    assert (features.loc[features.available, "observations"] > 0).all()
    text = f"""# Entry-time comparison with StratWise

Based on `18-research-leads-no-blacklists.ipynb`. Six addresses, including both Sentiment Edge vaults; all five blacklist-off engine configurations on the full engine period. {len(reasons)} positions and {len(entries)} unique vault-entry dates. Positions across different strategies are separate counterfactuals: their P&Ls must not be added as a portfolio.

## Key new insights and what did we learn?

StratWise observations begin {prices[STRAT].index.min()}. Earlier entries cannot be compared with contemporary StratWise history. A separate shape chart aligns a deliberately later StratWise reference date (17 August 2026) with each worst entry; it is an illustration, never contemporaneous evidence. All charts mark missing history explicitly. The separate contemporary chart compares observed curves during July–September; it cannot justify earlier decisions.

## Summary of results

Worst position per vault (chosen retrospectively for explanation, not for screening):

{worst[['name','candidate','entry','exit','pnl','gate_return_proxy','gate_threshold','composite_proxy','unscored_proxy','nav_return_during_position','worst_from_entry']].to_markdown(index=False)}

30-day metric medians (returns and drawdowns are fractions):

{med.to_markdown()}

Illustrative screen retention, not a strategy backtest:

{screen.to_markdown(index=False)}

## Why these entries won slots and then lost money

- **Scared Money, 4 June 2026:** its reconstructed 45-day return is +105%, above the floor20 gate of +2.27%, and its composite saturates at 1.00. But the preceding 30 days already contained a 48.7% drawdown, and return becomes -35.2% after deleting the two best days. The position's observed NAV falls about 40.9% by closure. The production source documents share-price rounding problems: these are not reliable trading-return observations.
- **BULBUL2DAO, 14 December 2025:** the 14-day return is -6.1%, which still passes the -16% gate. Its reconstructed composite is 0.42 despite a visibly declining 90-day curve. NAV then drops about 25.0% during the position. Historical ranking and a permissive gate admitted an already unstable path.
- **HLT, 19 January 2026:** a rebound produces +17.8% over 45 days and a composite around 0.83, passing floor20. After removing the two largest gains, the preceding 30-day return is -9.4%. NAV subsequently loses about 27.9% by closure. The return floor mistakes a recovery jump for persistent profitability; the curator also flags unstable share prices.
- **Sentiment Edge 0xb7e7d0, 14 December 2025:** +15.2% over 45 days passes floor15. The conservative reconstruction has no complete composite and assigns zero, which is admissible under the code. Its staircase rise is dominated by a few jumps: removing the best two days turns its preceding 30-day return negative. NAV subsequently falls about 8.2% during the position. The exact engine ranking remains unverified; zero score does not mean the strategy bars entry.
- **Sentiment Edge 0x026a2e, 2 June 2026:** the 14-day rebound is +15.3% and the composite is about 0.70, but the preceding 30-day drawdown is 7.7%. The rebound fails and NAV loses about 2.6% during the position.
- **Cryptoaddcited, 9 May 2026:** +5.2% over 14 days and a composite around 0.78 accompany an increasingly positive curve. Its 30-day drawdown is only 2.4%, and return remains +2.5% after removing the two best days. It passes the proposed combined screen, yet subsequently loses about 6.7% in NAV during the position. This is a genuine limitation of the selected metrics: a reasonable-looking history can reverse.

These are the worst individual positions per address across five configurations, not six typical trades. Dollar P&Ls are in the table; NAV changes explain direction but not the complete effect of trims, deposits and fees.

## Similarities and differences from StratWise

All can display an upward recent curve and sufficiently positive trailing returns. The distinguishing feature in this sample is how much progress remains after removing the biggest gains, and how deep the intervening setbacks are. StratWise's 23 available 30-day reference windows have median return +2.4%, median return excluding the two best days +1.3%, median drawdown 0.46%, and median worst completed week +0.20%. The very high short-sample Sharpe/Sortino is not the main reason to favour it: those ratios are fragile when only a few weeks of small losses exist.

The illustrative combined screen retains 7/53 distinct problematic-vault entry dates and 23/23 StratWise reference dates. By vault it retains Scared Money 0/27, HLT 0/3, Sentiment Edge 0xb7e7d0 1/7, Sentiment Edge 0x026a2e 1/3, BULBUL2DAO 1/4, and Cryptoaddcited 4/9. These problematic-vault entries include profitable positions too; the 46 rejected dates are NOT 46 prevented losses. The weekly-cadence version retains 12/53 problematic-vault entry dates and 23/23 StratWise reference dates. Separation remains, but is weaker than the daily version: reporting cadence explains part of the apparent advantage. Only one unique problem-vault entry date has a full contemporary 30-day StratWise comparison. The other StratWise reference dates are later, overlapping observations of one vault.

## Interpretation and next tests

Compare return after deleting the two largest positive daily log returns, rolling drawdown/ulcer, worst completed week and positive-week share. These distinguish consistent progress from a jump or rebound without requiring a year of history. Positive-week share alone can reward stale data or smooth negative-skew strategies. Pair it with observation coverage and downside controls. Sharpe and Sortino can be undefined or extreme with few losses; no-loss histories are uncertainty, not proof of safety. Use 7/14-day diagnostics for young vaults and build confidence as 30/45/60/90-day evidence arrives, rather than requiring all windows.

The historical selection formula weights bounded 360-day CAGR 60% and bounded 45-day Sortino 40%, then sizes by inverse variance over 90 days. Missing composite scores are admitted at zero. Its ordinary gate allows 14-day returns above -16%; floor15/floor20 require a modest positive 45-day return. Those are return gates, not stability tests. A zero-scored vault can receive a slot when enough scored competitors are unavailable; higher short-term steadiness does not guarantee StratWise a score or a sizing estimate.

## Robustness of results

Pre-entry metrics use only observed marks available before entry, with daily grid ending at the previous midnight. They are conservative analytical reconstructions, NOT exact engine-cache scores/ranks. The source code explains admission rules; the saved NB18 ledger establishes actual selections and P&L. Exact cross-sectional rank, deposit availability and rejected competitors at each entry require instrumented engine replays and are not claimed here.

Daily marks are as-of forward-filled, never backfilled. Older vault histories often report weekly, while StratWise reports densely. A weekly update appears as one large daily gain: daily gain-concentration and apparent smoothness can therefore distinguish reporting cadence rather than trading skill. The additional weekly-cadence screen computes both cohorts on completed 7-day marks and removes their best week instead of their best two days; four weekly returns remain a very small sample. Compare its retention with the daily screen before interpreting the separation. Observation counts, maximum reporting gaps and zero-return shares accompany metrics; sparse marks can conceal intraperiod losses. 7-day returns are non-overlapping within each feature window. Daily feature dates overlap heavily and are not independent samples. No pre-inception StratWise proxy is invented; no rules were validated out of sample. Thresholds are illustrative and chosen for this diagnostic, not proven allocation improvements.

Charts show NAV, not a cashflow-adjusted trading account. The ledger includes repeated deposits, trims, fees and unrealised P&L, so entry-to-exit NAV return need not equal position profitability. After-entry plots extend up to 60 days and mark actual exits; observations after exit were not held. Full holding-period NAV return and worst loss from entry are also tabulated. The same snapshot hash as NB18 is verified. Curator labels identify known price concerns, not independent evidence of losses: Scared Money rounding artefacts and HLT unstable share prices must be distinguished from real trading losses. No new blacklists are introduced.

Files: `later-template-before-after.png`, `same-date-entries.png`, `worst-entries-before-after.png`, `all-entries-before-after.pdf`, `contemporary-curves.png`, `entry-explanations.csv`, `pre-entry-features.csv`, `screen-diagnostics.csv` under `_artifacts-entry-forensics/`.
"""
    (project / "stratwise-entry-forensics-summary-01.md").write_text(text)
    (out / "heading-results.md").write_text(text)
    return features, reasons, screen
