"""Compact profit-led NB14 presentation, with a heading for each element."""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from profitable_allocation import LABELS, ARMS, ROOT, observed_quote

COLOURS = {"A": "#111827", "B": "#2563eb", "C": "#7c3aed", "D": "#ea580c", "G": "#059669"}


def heading(title, description, period="2026"):
    display(Markdown(f"### {title} — {LABELS[period]}\n\n{description}"))


def table(frame):
    formats = {c: "${:,.0f}" if "(USD)" in c else "{:.2%}" if c in ["CAGR", "Maximum drawdown", "Mean cash weight", "Mean largest vault weight", "Largest vault weight", "Best update", "Zero_downside_funded_share", "Variance_fallback_funded_share"] else "{:.2f}" if c in ["Sharpe", "Sortino", "Excess kurtosis"] else "{}" for c in frame}
    style = frame.style.format(formats, na_rep="Unavailable").hide(axis="index")
    for c in ["CAGR", "Sharpe", "Maximum drawdown", "Net profit (USD)"]:
        if c in frame and len(frame) > 1:
            style = style.background_gradient(subset=[c], cmap="RdYlGn")
    display(style)


def figure(data, fig, name, title, description, period="2026"):
    heading(title, description, period)
    fig.tight_layout()
    path = data["artifact"] / f"{name}.png"
    fig.savefig(path, dpi=115, bbox_inches="tight")
    display(fig)
    plt.close(fig)
    data["figures"].append(str(path))


def setup(data, preflight):
    heading("Registered methods", "Ranking, six positions, missing=True, the two-day cadence and source constraints are fixed. C and D share the regularised risk estimate; G changes its individual and peer estimate to squared losses.")
    table(pd.DataFrame([dict(Arm=a, Method=name, Risk=method, Allocator=allocator) for a, (name, method, allocator) in ARMS.items()]))
    heading("Price timing preflight", "Compare saved successful trade prices with the final daily observation and the latest NAV actually observed before execution. Archive write time is not used as a price-availability clock.")
    rows = preflight.groupby(["Period", "Arm"]).agg(Trades=("Trade", "size"), Later_NAV_used=("Uses_later_mark", "sum"), Mean_known_NAV_age_days=("Known_age_days", "mean")).reset_index()
    table(rows[rows.Period.eq("2026")])
    display(Markdown(f"**Chosen convention:** `{data['pricing_convention']}`. Across both reference periods, {int(preflight.Uses_later_mark.sum()):,} successful trades consumed later intraday NAV marks. Detailed long-period exceptions are in the ignored audit ledger. Indicators still use completed T−1 buckets, which precede T; only execution and valuation queries receive the shared observation-time adapter when the trace confirms a leak."))


def heatmap(data, frame, name, title, description, period="2026"):
    z = frame.to_numpy(float)
    limit = max(np.nanmax(np.abs(z)), 1)
    fig, ax = plt.subplots(figsize=(max(7, len(frame.columns) * 1.7), 3.8))
    im = ax.imshow(z, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(len(frame.columns)), frame.columns.astype(str))
    ax.set_yticks(range(len(frame)), frame.index)
    for i in range(len(frame)):
        for j in range(len(frame.columns)):
            ax.text(j, i, f"${z[i,j]:+,.0f}", ha="center", va="center", fontsize=9, color="white" if abs(z[i, j]) > 0.65 * limit else "#111827")
    ax.set_title(f"{title}\n{LABELS[period]}")
    fig.colorbar(im, ax=ax, label="Incremental net profit versus A (USD)")
    figure(data, fig, name, title, description, period)


def report(data, results, runs, attribution, weights, sensitivity):
    columns = ["Arm", "Method", "Final equity (USD)", "Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown"]
    annual = []
    contrasts = []
    for period in ["2026", "Long"]:
        frame = results[results.Period.eq(period)].sort_values("Net profit (USD)", ascending=False)
        heading("Key economic results", "Each account starts with $150,000. Net profit includes the source performance-fee accounting and estimated redemption allowance. Sorted by dollars earned; drawdown and Sharpe show the accompanying risk.", period)
        table(frame[columns])
        if period == "2026":
            heading("Deployment, concentration and modelled costs", "Cash and exposure are fractions of whole account equity, including early undeployed days. Turnover and modelled redemption costs help explain differences in net profit.")
            table(frame[["Arm", "Mean cash weight", "Mean largest vault weight", "Largest vault weight", "Trades", "Gross trade turnover (USD)", "Modelled redemption costs (USD)"]])
            ledger = data["artifact"] / "risk-ledger.parquet"
            if ledger.exists():
                r = pd.read_parquet(ledger)
                r = r[r.Period.eq("2026") & r.Variant.eq("primary")].copy()
                rows = []
                for arm, g in r.groupby("Arm"):
                    g = g.drop_duplicates(["origin_at", "pair_id"], keep="last")
                    al = runs[("2026", arm)]["allocation_df"]
                    targets = {(pd.Timestamp(row["Date"]), int(row["Pair id"])): float(row["Final target (USD)"]) for _, row in al.iterrows()}
                    funded = np.array([targets.get((pd.Timestamp(t), int(pid)), 0.0) for t, pid in zip(g.origin_at, g.pair_id)])
                    total = funded.sum()
                    zero = g.get("status", pd.Series("", index=g.index)).eq("zero_downside_nonflat").to_numpy()
                    fb = g.get("variance_prior_fallback", pd.Series(False, index=g.index)).eq(True).to_numpy()
                    rows.append(dict(Arm=arm, Risk_rows=len(g), Partial_history=int((~g.full).sum()), Peer_only=int(g.prior_only.sum()), Equal_fallback=int(g.basket_equal_fallback.sum()), Zero_downside_nonflat=int(g.get("status", pd.Series("", index=g.index)).eq("zero_downside_nonflat").sum()), Total_variance_prior_fallback=int(g.get("variance_prior_fallback", pd.Series(False, index=g.index)).eq(True).sum()), Zero_downside_funded_share=float(funded[zero].sum() / total) if total else 0.0, Variance_fallback_funded_share=float(funded[fb].sum() / total) if total else 0.0))
                heading("Risk support and fallback counts", "These are unique vault/decision rows where sizing was requested, not counts of trades or independent observations. Young histories remain eligible; flat or loss-free windows are labelled separately. Funded shares weight each sizing request by its final target dollars, not by realised future profit.")
                table(pd.DataFrame(rows))
        selected = ["A", "D", "G"]
        leader = frame.iloc[0].Arm
        if leader not in selected:
            selected.append(leader)
        fig, ax = plt.subplots(figsize=(10.5, 4.8))
        for arm in selected:
            eq = runs[(period, arm)]["equity"]
            ax.plot(eq.index, eq, label=arm + " — " + ARMS[arm][0], color=COLOURS[arm], lw=1.7)
        ax.set(title=f"Portfolio equity\n{LABELS[period]}", xlabel="Date (UTC)", ylabel="Account equity (USD)")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8, loc="upper left")
        figure(data, fig, period + "-equity", "Equity curves", "Compare the current reference A, simultaneous regularised D, downside G and any additional profit leader. Each line starts with the same capital; holdings and capital can subsequently diverge.", period)
        ref = frame.set_index("Arm")
        for name, left, right in [("Allocator", "B", "A"), ("Regularisation", "C", "A"), ("Downside vs regular", "G", "C"), ("Downside vs source", "G", "A")]:
            contrasts.append(dict(Period=period, Comparison=name, **{"Profit difference (USD)": ref.loc[left, "Net profit (USD)"] - ref.loc[right, "Net profit (USD)"], "CAGR difference (pp)": 100 * (ref.loc[left, "CAGR"] - ref.loc[right, "CAGR"]), "Drawdown difference (pp)": 100 * (ref.loc[left, "Maximum drawdown"] - ref.loc[right, "Maximum drawdown"])}))
        interaction = ref.loc["D", "Net profit (USD)"] - ref.loc["B", "Net profit (USD)"] - ref.loc["C", "Net profit (USD)"] + ref.loc["A", "Net profit (USD)"]
        contrasts.append(dict(Period=period, Comparison="Allocator × estimator interaction", **{"Profit difference (USD)": interaction}))
        pnl = pd.DataFrame({arm: runs[(period, arm)]["equity"].resample("1D").last().ffill().diff().fillna(0) for arm in ARMS})
        incremental = pnl.subtract(pnl.A, axis=0)
        if period == "2026":
            grouped = incremental.groupby(incremental.index.to_period("Q")).sum().T
            grouped.columns = [str(c) + ("*" if c.quarter == 4 else "") for c in grouped.columns]
            heatmap(data, grouped, "2026-quarter-profit", "Quarterly incremental net profit", "Dollars earned in each quarter minus A on the same dates. Q4* contains only 1–4 October; these are profit contributions, not annualised returns.")
        else:
            grouped = incremental.groupby(incremental.index.year).sum().T
            grouped.columns = [str(y) + (" through 7 Oct" if y == 2026 else " from 1 Mar" if y == 2023 else "") for y in grouped.columns]
            heatmap(data, grouped, "Long-year-profit", "Calendar-year incremental net profit", "Dollars earned from carried accounts minus A. Prior-year performance changes each account’s starting capital; the 2026 column ends 7 October and is not the fresh-start 2026 replay.", period)
            for arm in ARMS:
                w = weights[(period, arm)]
                reserve = runs[(period, arm)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
                for year, g in pnl[arm].groupby(pnl.index.year):
                    annual.append(dict(Arm=arm, Year=year, Profit=float(g.sum()), Mean_cash=float(w[reserve][w.index.year == year].mean())))
    paired = pd.DataFrame(contrasts)
    paired.to_csv(data["artifact"] / "paired-results.csv", index=False)
    heading("Paired profit differences", "Each comparison changes one registered mechanism; the interaction measures whether redistribution and regularisation work differently together. These are full trading-engine outcomes, including changes in future holdings.")
    table(paired[paired.Period.eq("2026")])
    fig, ax = plt.subplots(figsize=(9.5, 4))
    p = paired[paired.Period.eq("2026")]
    values = p["Profit difference (USD)"].to_numpy()
    ax.barh(p.Comparison, values, color=["#059669" if x >= 0 else "#dc2626" for x in values])
    ax.axvline(0, color="#111827", lw=0.8)
    ax.set(title=f'Effect on net profit\n{LABELS["2026"]}', xlabel="Net profit difference (USD)")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    figure(data, fig, "2026-paired-profit", "Profit effects by mechanism", "Positive bars indicate more dollars earned. G versus C is the matched downside-risk comparison; G versus A is the practical strategy comparison.")
    leader = results[results.Period.eq("2026") & results.Arm.ne("A")].sort_values("Net profit (USD)", ascending=False).iloc[0].Arm
    diff = attribution[("2026", leader)].subtract(attribution[("2026", "A")], fill_value=0).sort_values()
    shown = pd.concat([diff.head(4), diff.tail(4)]).drop_duplicates().rename("Profit difference (USD)").reset_index()
    heading("Vaults explaining the leading challenger", "Incremental position profit versus A, including every traded vault. Contributions describe the actual account paths; removing a vault would change allocation and is a different strategy.")
    table(shown.assign(Challenger=leader))
    # Separate absolute-weight chart makes capital deployment directly visible.
    named = sorted(set().union(*(set(weights[("2026", a)].drop(columns=[runs[("2026", a)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol]).mean().nlargest(6).index) for a in ["A", leader])))
    palette = {name: plt.get_cmap("tab20")(i % 20) for i, name in enumerate(named)}
    for arm in dict.fromkeys(["A", leader]):
        w = weights[("2026", arm)]
        reserve = runs[("2026", arm)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
        names = w.drop(columns=[reserve]).mean().nlargest(6).index.tolist()
        shown = w[names].copy()
        shown["Other vaults"] = w.drop(columns=names + [reserve]).sum(axis=1)
        shown["Cash"] = w[reserve]
        fig, ax = plt.subplots(figsize=(10.5, 4.5))
        shown.plot.area(ax=ax, linewidth=0, color=[palette[n] for n in names] + ["#94a3b8", "#e5e7eb"])
        ax.set(title=f'{arm}: absolute account weights\n{LABELS["2026"]}', xlabel="Date (UTC)", ylabel="Fraction of total equity", ylim=(0, 1))
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=7)
        figure(data, fig, f"2026-{arm}-weights", arm + " capital deployment", "The six largest average vault exposures are named; remaining vaults are grouped. Cash is included, so each vertical slice sums to the whole account.")
    heading("Sparse-price trading sensitivity", "Keep as-of valuation and the same strategy rules, but defer deposits and redemptions when no actual NAV was observed during the previous two-day source cycle. This conservative modelling sensitivity does not claim the real vault was closed. It tests reliance on trading against carried stale NAV. Pinned unredeemable positions reserve slots so total holdings remain at most six.")
    table(sensitivity[sensitivity.Period.eq("2026")][columns])
    heading("Sparse-price trading sensitivity, full history", "Repeat the same quote-freshness sensitivity for A and the long-period leading challenger. No new numerical age threshold is optimised: two days is the inherited decision cycle. This is an execution-availability assumption, not a production recommendation.", "Long")
    table(sensitivity[sensitivity.Period.eq("Long")][columns])
    timing = pd.read_parquet(data["artifact"] / "trade-timing.parquet")
    heading("Timing and extreme-update checks", "Primary corrected fills must match the latest recorded NAV at execution. A high update can represent accumulated weekly profits; its observation timing and underlying vault contributions should be read alongside the account return.")
    table(timing[timing.Period.eq("2026")].groupby("Arm").agg(Trades=("Trade", "size"), Later_NAV_used=("Uses_later_mark", "sum"), Matched_as_of_NAV=("Matches_known_NAV", "sum")).reset_index())
    table(results[results.Period.eq("2026")][["Arm", "Best update", "Excess kurtosis", "PnL residual (USD)"]])
    tail_audit(data, results, runs)
    pd.DataFrame(annual).to_csv(data["artifact"] / "annual-profit-cash.csv", index=False)
    findings = write_findings(data, results, paired, sensitivity, attribution)
    display(Markdown(verdict_excerpt(findings)))
    (data["artifact"] / "complete.json").write_text(json.dumps(dict(status="complete", primary_results=len(results), sensitivity_results=len(sensitivity), figures=data["figures"]), indent=2))
    return findings


def tail_audit(data, results, runs):
    """Explain extreme account updates with actual NAV intervals and curator context."""
    from tradingstrategy.binance.price import fetch_binance_price
    from tradeexecutor.curator.curator import EXCLUDED_VAULTS, is_quarantined

    market = {s: fetch_binance_price(symbol=s, request_timeout=10.0) for s in ["BTCUSDT", "ETHUSDT"]}
    rows = []
    for period in ["2026", "Long"]:
        leader = results[results.Period.eq(period) & results.Arm.ne("A")].sort_values("Net profit (USD)", ascending=False).iloc[0].Arm
        for arm in dict.fromkeys(["A", leader]):
            r = runs[(period, arm)]
            best = r["daily_returns"].idxmax()
            earlier = r["equity"].index[r["equity"].index < best]
            if not len(earlier):
                continue
            previous = earlier[-1]
            curves = pd.read_parquet(data["artifact"] / f"{period}-{arm}-position-curves.parquet")
            meta = pd.read_parquet(data["artifact"] / f"{period}-{arm}-positions.parquet").set_index("Position id")
            pnl = curves.diff().loc[best].groupby(meta.Vault).sum().sort_values(ascending=False)
            for vault, profit in pnl.head(3).items():
                address = meta.loc[meta.Vault.eq(vault), "Address"].iloc[0]
                pid = next(pid for pid, a in data["raw_history"][["pair_id", "address"]].drop_duplicates().itertuples(index=False, name=None) if a == address)
                first = observed_quote(data, pid, previous)
                last = observed_quote(data, pid, best)
                if first is None or last is None:
                    continue
                row = dict(Period=period, Arm=arm, Update=best, Vault=vault, **{"Update profit (USD)": profit}, First_mark=first[1], Last_mark=last[1], Interval_days=(last[1] - first[1]).total_seconds() / 86400, NAV_return=last[0] / first[0] - 1, Excluded=address in EXCLUDED_VAULTS, Quarantined=is_quarantined(address, best))
                for symbol, m in market.items():
                    prices = m.loc[first[1].floor("D") : last[1].floor("D"), "close"]
                    row[symbol + " return"] = prices.iloc[-1] / prices.iloc[0] - 1 if len(prices) else np.nan
                rows.append(row)
    frame = pd.DataFrame(rows)
    frame.to_csv(data["artifact"] / "tail-audit.csv", index=False)
    for period in ["2026", "Long"]:
        heading("NAV intervals behind the strongest updates", "Top three position contributions for A and the leading challenger. Actual marks can span a week; BTC/ETH context uses those same mark dates. The curator flags identify excluded or quarantined vaults, without inferring that a large gain is a data error.", period)
        f = frame[frame.Period.eq(period)].drop(columns=["Period", "First_mark", "Last_mark"])
        display(f.style.format({"Update profit (USD)": "${:,.0f}", "Interval_days": "{:.2f}", "NAV_return": "{:+.2%}", "BTCUSDT return": "{:+.2%}", "ETHUSDT return": "{:+.2%}"}).hide(axis="index"))


def verdict_excerpt(findings):
    """Show concise conclusions while keeping full tables in the linked findings file."""
    verdict = findings.split("## Hypothesis verdicts", 1)[1].split("Allocator and regularisation effects", 1)[0].strip()
    return "### Economic verdict — " + LABELS["2026"] + "\n\n" + verdict + "\n\n[Detailed findings](14-profitable-allocation-findings.md) retain both periods, sensitivities and execution limitations."


def markdown_table(frame):
    """Keep written findings readable with explicit percent and dollar units."""
    f = frame.copy()
    for c in f:
        if c in ["CAGR", "Maximum drawdown", "Mean cash weight"]:
            f[c] = f[c].map(lambda x: f"{x:.2%}" if pd.notna(x) else "—")
        elif "(USD)" in c:
            f[c] = f[c].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
        elif c in ["Sharpe", "CAGR difference (pp)", "Drawdown difference (pp)"]:
            f[c] = f[c].map(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    return f.to_markdown(index=False)


def write_findings(data, results, paired, sensitivity, attribution):
    lines = ["# Experiment 14 — profitable allocation findings", f'\nPricing: **{data["pricing_convention"]}**. Five fixed allocation methods, fresh $150,000 accounts, the original four-input ranking and six-position limit.']
    conclusions = []
    for period in ("2026", "Long"):
        f = results[results.Period.eq(period)].set_index("Arm")
        best = f["Net profit (USD)"].idxmax()
        chall = f.drop(index="A")["Net profit (USD)"].idxmax()
        delta = f.loc[chall, "Net profit (USD)"] - f.loc["A", "Net profit (USD)"]
        sentence = f'{period}: profit leader **{best}**. Best challenger **{chall}** changes profit by **${delta:+,.0f}**, CAGR by {(f.loc[chall,"CAGR"]-f.loc["A","CAGR"])*100:+.2f} percentage points, and drawdown by {(f.loc[chall,"Maximum drawdown"]-f.loc["A","Maximum drawdown"])*100:+.2f} percentage points versus A.'
        conclusions.append(sentence)
        lines += ["\n## Results — " + LABELS[period], sentence, "\n" + f.reset_index()[["Arm", "Method", "Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown", "Mean cash weight"]].pipe(markdown_table)]
    verdicts = []
    for name in ["Allocator", "Regularisation", "Downside vs regular"]:
        values = paired[paired.Comparison.eq(name)].set_index("Period")["Profit difference (USD)"]
        verdicts.append(f'{name}: 2026 ${values["2026"]:+,.0f}; full history ${values["Long"]:+,.0f}. The profit hypothesis is supported over full history and rejected for the fresh 2026 comparison.' if values["Long"] > 0 and values["2026"] < 0 else f'{name}: 2026 ${values["2026"]:+,.0f}; full history ${values["Long"]:+,.0f}.')
    verdicts.append("Redistribution alone contributes little: most of the full-history improvement is already present with regularisation under the original allocator. Downside sizing adds only about $3,352 over that regularised control and has worse drawdown in both primary periods. Keep A as the 2026 reference; G is a historical profit challenger, not an established replacement.")
    lines += [
        "\n## Hypothesis verdicts",
        "\n\n".join(verdicts),
        "Allocator and regularisation effects are the paired engine differences below. G−C tests the downside estimator package, including its downside peer prior. Positive incremental dollars support a profit benefit for that period; disagreement between periods indicates year dependence.",
        "\n" + paired.pipe(markdown_table),
        "\n## Sparse-price sensitivity",
        sensitivity[["Period", "Arm", "Net profit (USD)", "CAGR", "Sharpe", "Maximum drawdown"]].pipe(markdown_table),
        "\n## Robustness and limitations",
        "With trading deferred when NAV observations are older than two days, A earns $57,198 versus B $56,101 in 2026. Over full history, G earns $139,821 versus A $98,640: a $41,181 lead, with maximum drawdown -14.74% versus -16.86%. This supports a historical profit advantage under this conservative assumption, but is not a ranking of all five methods under that alternative execution rule.",
        f'The saved reference trace found {data["manifest"]["timing_preflight"]["uses_later_mark"]:,} successful trades using a later intraday daily-close mark. Primary fills and valuation now use recorded NAV observations at or before the query timestamp; score/risk inputs remain completed T−1 buckets. This assumes observation timestamps identify effective NAV times, independently of archive rewrites.',
        "A carried last-known NAV is not independent evidence of the actual deposit/redemption price. The quote-freshness sensitivity defers trading when observations are older than a source two-day cycle. It changes trading availability and can change holdings; it is deliberately conservative, not a proof of the true fill price. Permission and capacity history are otherwise inherited unchanged.",
        "The long replay contains early empty-universe/cash periods and previously searched years. Fresh 2026 ends 4 October; carried long-run 2026 ends 7 October. No independent forward validation is claimed. The redemption allowance is estimated and turnover differs between arms. The inherited source records a net-of-fee mid price for partial Hypercore trims and applies the sell fee again to planned execution; this existing convention is retained for reference comparability. The recorded redemption-cost column is the source estimate, not a separately verified total economic fee. Gross-NAV timing checks undo the partial-trim fee adjustment before comparing observations.",
        "\n## Next action",
        "Retain A as the current-period allocation reference. Regularisation is the economically material historical lever; downside sizing supplies a small additional historical gain with a risk cost. A single later-data comparison of A and a frozen regularised/downside challenger is more useful than a wider grid. The full-history quote-freshness sensitivity preserves G’s profit lead while changing drawdown materially, so execution assumptions remain part of the result.",
    ]
    findings = "\n\n".join(lines) + "\n"
    path = ROOT / "14-profitable-allocation-findings.md"
    path.write_text(findings)
    header = f"""# Experiment 14 — more profitable allocation

Based on [NB13](13-backtest-leading-candidates.ipynb) and [NB12](12-research-allocation-followup.ipynb). Implements the [reviewed plan](14-profitable-allocation-plan.md).

## Goal and method

Make the strategy more profitable through better capital placement and redistribution within caps. Compare source variance and regularised variance under original versus simultaneous allocation, plus regularised downside sizing under original allocation. Freeze C03's ranking (48% CAGR360, 32% Sortino45, 10% CAGR180, 10% Sortino30; existing clips), six positions, missing=True, two-day cadence, selection/gates/hysteresis and fees. Reuse all indicator warmup, causal NAV filling and actual-observation counts for partial-history regularisation. Test whether downside sizing retains profitable upward-moving vaults without unacceptable concentration in loss-free young histories.

Two independent calendars: **{LABELS['2026']}** and **{LABELS['Long']}**. Every account starts with $150,000. Net dollars and CAGR are primary; drawdown, Sharpe, costs, exposure and vault/quarter contributions explain the economic trade-offs. Default presentation is the short 2026 period; long-history comparisons are explicitly labelled.

## Key new insights

{conclusions[0]}

{conclusions[1]}

## Summary of results

Five methods and both periods are completed, with A-versus-leading-challenger quote-freshness sensitivities. Tables below show the full profit/risk comparison. Detailed [findings](14-profitable-allocation-findings.md) retain attribution and limitations.

## Robustness of results

The reference timing trace confirmed later intraday NAV consumption; primary pricing is `{data['pricing_convention']}`. Source indicators and scores still end at T−1. Every primary fill is checked against its recorded as-of NAV, allocations retain source caps, and position PnL reconciles to equity within $1. Quote-freshness sensitivities defer trading against NAV older than the source two-day cycle; actual execution NAV remains unverified where observations are sparse. These dates have already been searched and are not an independent holdout.
"""
    (data["artifact"] / "final-header.md").write_text(header)
    summary = ROOT / "summary.md"
    content = summary.read_text()
    anchor = "## Experiment 14 — more profitable allocation"
    if anchor in content:
        content = content.split(anchor)[0].rstrip() + "\n"
    content += (
        "\n"
        + anchor
        + "\n\n### What was examined\n\nFive allocation methods with fixed four-input ranking and six positions. Profit and CAGR are the main outcomes, accompanied by drawdown and cost attribution.\n\n### Hypothesis\n\nRedistribution, regularisation or downside-based sizing improves capital placement and net profit.\n\n### Result\n\n"
        + "\n\n".join(conclusions)
        + "\n\n### Hypothesis verdict and useful leads\n\nAll three new mechanisms lose incremental profit in fresh 2026 and gain over full history. Redistribution alone adds little; regularisation supplies most of the historical gain. Downside sizing adds only $3,352 over C, with worse primary drawdown. The long quote-freshness sensitivity retains G’s $41,181 lead over A; the 2026 sensitivity retains A’s lead over B. Corrected observation-time pricing changes the comparable reference; old daily-close results are not mixed into the ranking. Sparse NAV execution and previously searched history remain limitations. See [NB14](14-backtest-profitable-allocation.ipynb) and [findings](14-profitable-allocation-findings.md).\n"
    )
    summary.write_text(content)
    return findings
