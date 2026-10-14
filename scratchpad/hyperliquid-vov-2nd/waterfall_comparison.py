"""NB16: matched waterfall variants of the four NB15 allocation methods."""

import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import Markdown, display
from tqdm_loggable.auto import tqdm

import allocation_comparison as parent
import profitable_allocation as engine
from accepted_dollar_cap import AuditedAlphaModel
from profitable_allocation import ROOT, PERIODS, LABELS
from score_matrix import FEATURES, MatrixIndicators

BASES = parent.ARMS
ARMS = tuple(a + s for a in BASES for s in ("", "-W"))
NOTEBOOK = ROOT / "16-backtest-waterfall-allocation-vs-v11.ipynb"
METHODS = {"V11": "source", "A": "source", "C": "regular", "G": "downside"}
LOGIC = parent.LOGIC + """
### Waterfall intervention

Each `-W` arm keeps its parent's performance ranking, eligibility, six-position basket limit, risk estimator, hysteresis, caps and execution model. The sole intervention forces the existing framework `waterfall=True` allocation path. Capital fills the highest **raw sizing weight** first, up to its concentration/TVL ceiling, then cascades to the next selected vault. V11/A use source inverse variance for this priority; C uses regularised variance; G uses regularised downside risk. Risk weights determine order rather than proportional dollar shares.

This is a sizing-priority waterfall, not a performance-score-order waterfall. No lower-ranked capacity-extension positions are introduced. Six selected small vaults can still leave cash when their combined capacity is below the deployable budget. Deposit checks subsequently reject blocked top-ups; this experiment adds no new admission-refill pass. Different holdings can change later selection through the inherited hysteresis.

An uncorrected A-W run failed on 12 July 2026: a buy exceeded net available cash by $94.63 after source fees. The source modifies sell prices after its buy-budget calculation, and its inherited partial-trim fee convention can further reduce proceeds. A research funding correction checks concrete planned sell quantities and final sell prices after the source callback. It scales buys only when they exceed current reserve plus those synchronous net proceeds, leaving ten reserve raw units for the framework's rounding tolerance. It preserves the inherited charges and records every intervention; it does not increase the portfolio cash reserve or inject capital. The correction is a no-op on successfully executed NB15 original trade queues, whose actual buys were funded.

| Arm | Ranking | Waterfall priority | Matched control |
| --- | --- | --- | --- |
| V11-W | Source two-input score | Source 90-day inverse variance | V11 |
| A-W | Four-input score | Source 90-day inverse variance | A |
| C-W | Four-input score | Regularised 90-day inverse variance | C |
| G-W | Four-input score | Regularised 90-day inverse downside moment | G |
"""


class WaterfallAlpha(AuditedAlphaModel):
    """Use the framework waterfall and record capacity and final-dollar targets."""

    def normalise_weights(self, *args, **kwargs):
        kwargs["waterfall"] = True
        return super().normalise_weights(*args, **kwargs)

    def _normalise_weights_waterfall(self, max_positions, max_weight=1.0, investable_equity=None, size_risk_model=None, epsilon_usd=5.0, max_protocol_weight=None, max_weight_function=None):
        budget = float(investable_equity)
        signals = list(self._get_allocatable_signals())
        order = {s.pair.internal_id: i + 1 for i, s in enumerate(sorted(signals, key=lambda s: s.raw_weight, reverse=True))}
        raw = sum(float(s.raw_weight) for s in signals)
        super()._normalise_weights_waterfall(max_positions=max_positions, max_weight=max_weight, investable_equity=investable_equity, size_risk_model=size_risk_model, epsilon_usd=epsilon_usd, max_protocol_weight=max_protocol_weight, max_weight_function=max_weight_function)
        accepted = sum(float(s.position_target or 0.0) for s in signals)
        assert accepted <= budget + 1e-6
        for s in signals:
            limit = max_weight_function(s) if max_weight_function else max_weight
            limit = max_weight if limit is None else limit
            capacity = size_risk_model.get_acceptable_size_for_position(self.timestamp, s.pair, float(limit * budget))
            target = float(s.position_target or 0.0)
            assert target <= float(capacity.accepted_size) + 1e-6
            row = {"Date": self.timestamp, "Pair id": s.pair.internal_id, "Address": str(s.pair.pool_address).lower(), "Vault": s.pair.get_vault_name(), "Mode": "waterfall", "Waterfall priority": order[s.pair.internal_id], "Raw weight": float(s.raw_weight), "Original weight": float(s.raw_weight) / raw if raw else 0.0, "Deployable budget (USD)": budget, "Old value (USD)": float(s.old_value or 0.0), "Concentration limit (USD)": float(limit * budget), "TVL (USD)": float(capacity.tvl or 0.0), "Capacity ceiling (USD)": float(capacity.accepted_size), "Accepted allocation (USD)": target, "Final target (USD)": None}
            self._audit_rows.append(row)
            self._allocation_ledger.append(row)


def initialise():
    """Pin NB15 inputs and place all new artefacts in an isolated generation."""
    data, evaluator = parent.initialise()
    nb = json.loads((ROOT / "15-backtest-allocation-vs-v11.ipynb").read_text())
    reference = Path(nb["metadata"]["nb15"]["artifact_generation"])
    saved_identity = json.loads((reference / "manifest.json").read_text())["identity"]
    current_identity = json.loads(json.dumps(data["manifest"]["identity"], default=str))
    for key in saved_identity:
        if key != "code":
            assert saved_identity[key] == current_identity[key], ("NB15 inputs changed", key)
    identity = {"version": "nb16-waterfall-v1", "nb15": current_identity, "arms": list(ARMS), "priority": "descending raw sizing weight", "positions": 6, "code": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in ["waterfall_comparison.py", "create_waterfall_comparison_notebook.py"]}}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    folder = ROOT / "_artifacts-restored-2026-10-07/16" / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    data.update(artifact=folder, fingerprint=fingerprint, figures=[], nb15_reference=reference, nb15_cache=reference / "engine", risk_cache={}, risk_ledger=[], quote_queries={}, run_context=None, funding_ledger=[])
    evaluator.folder = folder / "engine"
    evaluator.folder.mkdir(exist_ok=True)
    evaluator.values.clear()
    data["manifest"] = {"identity": identity, "fingerprint": fingerprint, "framework": data["framework_commits"], "limitations": ["Previously searched history; no independent holdout", "Retrospective universe and guard", "Sparse recorded NAV does not establish executable NAV", "Inherited partial-trim fee convention retained"], "nb15_reference": str(reference), "nb15_saved_identity": saved_identity, "reference_validation": "Input/source/engine identity matches; presentation code may differ; controls must reproduce saved metrics", "periods": {p: [str(t) for t in v] for p, v in PERIODS.items()}}
    (folder / "manifest.json").write_text(json.dumps(data["manifest"], indent=2, default=str))
    return data, evaluator


def waterfall_decision(data, strategy, panel, values, base, ledger):
    """Keep the source selector and execution callback, swapping allocation only."""
    source = strategy.decide_trades

    def decide(input):
        compute = strategy.compute_sizing_weights
        factory = strategy.AlphaModel
        models = []

        def weights(selected_pair_ids, inv_vol_by_id, signal_by_id, **kwargs):
            if METHODS[base] == "source":
                return compute(selected_pair_ids, inv_vol_by_id, signal_by_id, **kwargs)
            w, r = engine.research_weights(data, input.timestamp, selected_pair_ids, METHODS[base])
            data["risk_ledger"].append(r.reset_index().assign(Arm=base + "-W", Period=data["run_context"][0], Variant="waterfall"))
            return {pid: max(float(value), 1e-12) for pid, value in w.items()}

        def make(*args, **kwargs):
            model = WaterfallAlpha(*args, sizing_mode="parent", allocation_ledger=ledger, **kwargs)
            models.append(model)
            return model

        strategy.compute_sizing_weights = weights
        strategy.AlphaModel = make
        try:
            proxy = input.indicators if base == "V11" else MatrixIndicators(input.indicators, panel, values, input.timestamp)
            trades = source(replace(input, indicators=proxy))
            cap_to_final_sell_proceeds(data, input, trades, base + "-W")
            for model in models:
                for row in model._audit_rows:
                    signal = model.signals[row["Pair id"]]
                    row["Final target (USD)"] = float(signal.position_target or 0.0)
                    row["Flags"] = ",".join(sorted(f.value for f in signal.flags))
                    row["Normalised accepted weight"] = float(signal.normalised_weight or 0.0)
            return trades
        finally:
            strategy.compute_sizing_weights = compute
            strategy.AlphaModel = factory

    return decide


def cap_to_final_sell_proceeds(data, input, trades, arm):
    """Fund buys from final synchronous proceeds after source fee adjustments."""
    assert all(t.pair.is_vault() for t in trades)
    reserve = input.state.portfolio.get_default_reserve_asset()[0]
    cash = Decimal(str(input.state.portfolio.get_cash()))
    sells = sum((abs(t.planned_quantity * Decimal(t.planned_price)) for t in trades if t.is_sell()), Decimal(0))
    buys = [t for t in trades if t.is_buy()]
    requested = sum((t.planned_reserve for t in buys), Decimal(0))
    available = cash + sells
    if requested <= available:
        return
    budget = max(available - reserve.convert_to_decimal(10), Decimal(0))
    assert budget > 0, "No synchronous reserve to fund planned buys"
    factor = budget / requested
    for trade in buys:
        trade.other_data["nb16_unfunded_original_reserve"] = str(trade.planned_reserve)
        trade.planned_reserve *= factor
        trade.planned_quantity *= factor
    accepted = sum((t.planned_reserve for t in buys), Decimal(0))
    assert accepted <= available
    data["funding_ledger"].append({"Period": data["run_context"][0], "Arm": arm, "Date": input.timestamp, "Cash before (USD)": float(cash), "Final sell proceeds (USD)": float(sells), "Requested buys (USD)": float(requested), "Funded buys (USD)": float(accepted), "Reduction (USD)": float(requested - accepted)})


def replay_waterfall(data, evaluator, base, period):
    """Scope the research intervention and cache each independent engine account."""
    import score_matrix

    original = score_matrix.make_matrix_decision
    source = evaluator.strategy.decide_trades
    values = evaluator.panel.score_values
    ledger = []
    weight = np.zeros(len(FEATURES))
    weight[0] = 1
    funding_start = len(data["funding_ledger"])
    data["run_context"] = (period, base + "-W", "primary")
    evaluator.panel.score_values = lambda *a, **kw: data["focal_values"]
    if base == "V11":
        evaluator.strategy.decide_trades = waterfall_decision(data, evaluator.strategy, evaluator.panel, None, base, ledger)
    else:
        score_matrix.make_matrix_decision = lambda strategy, panel, values, sizing, allocator, rows, **kw: waterfall_decision(data, strategy, panel, values, base, rows)
    try:
        with engine.pricing_convention(data):
            r = evaluator.run(weight, *PERIODS[period], n=6, sizing="inverse_variance", source_control=base == "V11", missing=True, keep=True, profile=f"NB16-{base}-raw-risk-waterfall")
        if base == "V11":
            path = evaluator.folder / f'{r["cache_key"]}-waterfall.csv'
            if ledger:
                pd.DataFrame(ledger).to_csv(path, index=False)
            assert path.exists(), "Missing waterfall audit ledger"
            r["allocation_df"] = pd.read_csv(path, parse_dates=["Date"])
        funding_path = evaluator.folder / f'{r["cache_key"]}-funding.csv'
        columns = ["Period", "Arm", "Date", "Cash before (USD)", "Final sell proceeds (USD)", "Requested buys (USD)", "Funded buys (USD)", "Reduction (USD)"]
        if len(data["funding_ledger"]) > funding_start:
            pd.DataFrame(data["funding_ledger"][funding_start:]).to_csv(funding_path, index=False)
        elif funding_path.exists():
            data["funding_ledger"].extend(pd.read_csv(funding_path).to_dict("records"))
        else:
            pd.DataFrame(columns=columns).to_csv(funding_path, index=False)
        return r
    finally:
        score_matrix.make_matrix_decision = original
        evaluator.strategy.decide_trades = source
        evaluator.panel.score_values = values


def run(data, evaluator):
    """Reproduce eight NB15 controls and execute eight waterfall treatments."""
    expected = pd.read_csv(data["nb15_reference"] / "results.csv").set_index(["Period", "Arm"])
    results = []
    runs = {}
    attribution = {}
    weights = {}
    parity = []
    audits = []
    funding_checks = []
    for period, arm in tqdm([(p, a) for p in PERIODS for a in ARMS], desc="NB16 matched controls and waterfalls", mininterval=15):
        print(f"{period} / {arm}; remaining estimate {evaluator.remaining(16-len(results)):.1f} minutes", flush=True)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if arm.endswith("-W"):
                r = replay_waterfall(data, evaluator, arm[:-2], period)
            else:
                folder = evaluator.folder
                evaluator.folder = data["nb15_cache"]
                try:
                    if arm == "V11":
                        weight = np.zeros(len(FEATURES))
                        weight[0] = 1
                        data["run_context"] = (period, arm, "primary")
                        with engine.pricing_convention(data):
                            r = evaluator.run(weight, *PERIODS[period], n=6, source_control=True, keep=True, profile="NB15-v11-as-of-observation")
                    else:
                        r = engine.replay(data, evaluator, arm, period)
                finally:
                    evaluator.folder = folder
        m, v, w = engine.analyse_run(data, r, arm, period)
        m["Cumulative return"] = m["Final equity (USD)"] / 150000 - 1
        m["Calmar"] = m["CAGR"] / abs(m["Maximum drawdown"]) if m["Maximum drawdown"] < 0 else np.nan
        if not arm.endswith("-W"):
            for metric in ["CAGR", "Sharpe", "Maximum drawdown", "Final equity (USD)"]:
                error = m[metric] - float(expected.loc[(period, arm), metric])
                assert abs(error) < (0.01 if "(USD)" in metric else 2e-6)
                parity.append({"Period": period, "Arm": arm, "Metric": metric, "Difference": error})
            trades = [t for t in r["result"].state.portfolio.get_all_trades() if t.is_success() and (t.is_buy() or t.is_sell())]
            cash = Decimal(150000)
            cycles = {}
            for trade in trades:
                cycles.setdefault(trade.executed_at, []).append(trade)
            for date, queue in sorted(cycles.items()):
                planned_buys = sum((t.planned_reserve for t in queue if t.is_buy()), Decimal(0))
                proceeds = sum((abs(t.planned_quantity * Decimal(t.planned_price)) for t in queue if t.is_sell()), Decimal(0))
                assert planned_buys <= cash + proceeds + Decimal("0.00001"), (period, arm, date, "Original queue would require funding correction")
                funding_checks.append({"Period": period, "Arm": arm, "Date": date, "Original correction required": False})
                cash += sum((t.executed_reserve * (-1 if t.is_buy() else 1) for t in queue), Decimal(0))
        audit = engine.audit_trades(data, r, arm, period)
        assert audit.Matches_known_NAV.all()
        audits.append(audit)
        assert m["Maximum vaults held"] <= 6
        runs[(period, arm)] = r
        attribution[(period, arm)] = v
        weights[(period, arm)] = w
        results.append({"Period": period, "Arm": arm, "Allocation": "Waterfall" if arm.endswith("-W") else "Original", **m})
        pd.DataFrame(results).to_csv(data["artifact"] / "results.csv", index=False)
        if arm.endswith("-W"):
            r["allocation_df"].to_csv(data["artifact"] / f"{period}-{arm}-allocation-ledger.csv", index=False)
    pd.DataFrame(parity).to_csv(data["artifact"] / "nb15-parity.csv", index=False)
    pd.DataFrame(funding_checks).to_csv(data["artifact"] / "original-funding-checks.csv", index=False)
    pd.concat(audits, ignore_index=True).to_parquet(data["artifact"] / "trade-timing.parquet", index=False)
    if data["risk_ledger"]:
        pd.concat(data["risk_ledger"], ignore_index=True).to_parquet(data["artifact"] / "risk-ledger.parquet", index=False)
    pd.DataFrame(data["funding_ledger"]).to_csv(data["artifact"] / "funding-corrections.csv", index=False)
    (data["artifact"] / "complete.json").write_text(json.dumps({"accounts": 16, "parity_checks": len(parity), "fill_checks": sum(map(len, audits))}, indent=2))
    return pd.DataFrame(results), runs, attribution, weights


def table(frame, metrics):
    f = frame.set_index("Arm").reindex(ARMS)[metrics].T
    style = f.style
    for metric in metrics:
        fmt = "${:,.0f}" if "(USD)" in metric else "{:.2%}" if metric in ["CAGR", "Cumulative return", "Maximum drawdown", "Mean cash weight", "Largest vault weight"] else "{:.0f}" if metric in ["Trades", "Maximum vaults held"] else "{:.2f}"
        style = style.format(fmt, subset=pd.IndexSlice[[metric], :])
        if metric in ["CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown", "Net profit (USD)"]:
            style = style.background_gradient(subset=pd.IndexSlice[[metric], :], axis=1, cmap="RdYlGn")
    display(style)


def report(data, results, runs, attribution, weights):
    """Present matched economic outcomes with separate period-labelled figures."""
    robust, tails = parent.robustness(data, results, runs, attribution)
    deltas = []
    september = []
    contributors = []
    reserve = next(iter(runs.values()))["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
    names_all = sorted(set(n for w in weights.values() for n in w.drop(columns=reserve).mean().nlargest(10).index))
    colours = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors) + list(plt.get_cmap("tab20c").colors)
    palette = {n: colours[i % len(colours)] for i, n in enumerate(names_all)}
    palette.update({"Other vaults": "#9ca3af", "Cash": "#d1d5db"})
    for period in PERIODS:
        f = results[results.Period.eq(period)]
        indexed = f.set_index("Arm")
        display(Markdown(f'## {"2026" if period=="2026" else "Full-history"} comparison — {LABELS[period]}\n\nFresh $150,000 accounts. Each original allocator is followed by its matched waterfall arm.'))
        parent.heading("Key metrics", "Compare net results side by side. Green marks the better value in each row; maximum drawdown is better when closer to zero.", period)
        table(f, ["Final equity (USD)", "Net profit (USD)", "CAGR", "Sharpe", "Sortino", "Calmar", "Maximum drawdown"])
        parent.heading("Deployment and trading", "Realised cash, concentration and trading costs show how the allocation change affects the account. Full-history cash includes the early empty-universe period.", period)
        table(f, ["Mean cash weight", "Largest vault weight", "Maximum vaults held", "Trades", "Modelled redemption costs (USD)"])
        rows = []
        for base in BASES:
            b = indexed.loc[base]
            w = indexed.loc[base + "-W"]
            rows.append({"Strategy": base, "Profit difference (USD)": w["Net profit (USD)"] - b["Net profit (USD)"], "CAGR difference (pp)": 100 * (w.CAGR - b.CAGR), "Sharpe difference": w.Sharpe - b.Sharpe, "Drawdown difference (pp)": 100 * (w["Maximum drawdown"] - b["Maximum drawdown"]), "Cash difference (pp)": 100 * (w["Mean cash weight"] - b["Mean cash weight"])})
        delta = pd.DataFrame(rows)
        deltas.append(delta.assign(Period=period))
        parent.heading("Waterfall minus its own original allocator", "Positive profit/CAGR/Sharpe differences favour waterfall. A positive drawdown difference means a shallower drawdown. A negative cash difference means more deployment.", period)
        display(delta.set_index("Strategy").style.format("{:+.2f}").format("${:+,.0f}", subset=["Profit difference (USD)"]).background_gradient(cmap="RdYlGn", subset=delta.columns[1:5], axis=0))
        for base in BASES:
            difference = attribution[(period, base + "-W")].subtract(attribution[(period, base)], fill_value=0).sort_values(ascending=False)
            lead = float(delta.set_index("Strategy").loc[base, "Profit difference (USD)"])
            positions = pd.read_parquet(data["artifact"] / f"{period}-{base}-W-positions.parquet")
            best_position = positions.nlargest(1, "Final profit (USD)").iloc[0]
            contributors.append({"Period": period, "Strategy": base, "Leading gain vault": difference.index[0], "Leading vault difference (USD)": float(difference.iloc[0]), "Contribution / net lead": float(difference.iloc[0] / lead) if lead > 0 else np.nan, "Largest winning position": str(best_position["Position id"]) + " / " + str(best_position.Vault), "Largest position profit (USD)": float(best_position["Final profit (USD)"])})
        parent.heading("Vault dependence of the allocation advantage", "Compare each vault’s cumulative ledger profit with its original allocator. A contribution above 100% of the net lead means other vault changes offset part of that gain. This is realised attribution, rather than a vault-removal counterfactual.", period)
        cf = pd.DataFrame(contributors)
        display(cf[cf.Period.eq(period)].drop(columns=["Period", "Largest winning position", "Largest position profit (USD)"]).set_index("Strategy").style.format({"Leading vault difference (USD)": "${:+,.0f}", "Contribution / net lead": "{:.1%}"}, na_rep="No net lead"))
        fig, ax = plt.subplots(figsize=(11, 4.8))
        for base in BASES:
            for suffix in ("", "-W"):
                e = runs[(period, base + suffix)]["equity"]
                ax.plot(e.index, e / 1000, label=base + suffix, color=parent.COLOURS[base], ls="--" if not suffix else "-", lw=1.4, alpha=0.7 if not suffix else 1.0)
        ax.set(title="Equity: original (dashed) and waterfall (solid)\n" + LABELS[period], ylabel="Equity ($ thousands)")
        ax.grid(alpha=0.2)
        ax.legend(ncol=4, fontsize=8)
        parent.figure(data, fig, f"{period}-equity", "Matched equity curves", "Colour identifies the ranking/risk method; dashed lines are originals and solid lines are waterfall accounts. All accounts have the same starting capital.", period)
        q = pd.DataFrame({a: (1 + runs[(period, a)]["daily_returns"]).groupby(runs[(period, a)]["daily_returns"].index.to_period("Q")).prod() - 1 for a in ARMS}).T
        q.to_csv(data["artifact"] / f"{period}-quarter-returns.csv")
        z = q.to_numpy() * 100
        limit = max(abs(z).max(), 1.0)
        fig, ax = plt.subplots(figsize=(max(10, len(q.columns) * 1.05), 4.8))
        im = ax.imshow(z, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
        start, end = PERIODS[period]
        labels = [str(t) + ("*" if pd.Timestamp(start) > t.start_time or pd.Timestamp(end) - pd.Timedelta(days=1) < t.end_time.floor("D") else "") for t in q.columns]
        ax.set_xticks(range(len(q.columns)), labels, rotation=35, ha="right")
        ax.set_yticks(range(len(ARMS)), ARMS)
        ax.set_title("Quarterly portfolio returns (%)\n" + LABELS[period])
        ax.grid(False)
        for i in range(len(ARMS)):
            for j in range(len(q.columns)):
                ax.text(j, i, f"{z[i,j]:+.1f}", ha="center", va="center", fontsize=8, color="white" if abs(z[i, j]) > limit * 0.6 else "black")
        fig.colorbar(im, ax=ax, label="Return (%)", shrink=0.8)
        parent.figure(data, fig, f"{period}-quarters", "Quarterly profit heatmap", "Compounded quarterly account returns show whether gains persist across regimes. An asterisk marks a partial quarter.", period)
        fig, ax = plt.subplots(figsize=(11, 4.6))
        for base in BASES:
            for suffix in ("", "-W"):
                a = base + suffix
                reserve = runs[(period, a)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
                c = weights[(period, a)][reserve]
                ax.plot(c.index, c * 100, color=parent.COLOURS[base], ls="--" if not suffix else "-", label=a, lw=1.2)
        ax.set(ylim=(0, 100), ylabel="Cash / total equity (%)", title="Cash utilisation: original (dashed) and waterfall (solid)\n" + LABELS[period])
        ax.legend(ncol=4, fontsize=8)
        ax.grid(alpha=0.2)
        parent.figure(data, fig, f"{period}-cash", "Matched cash histories", "Compare actual account cash rather than allocator bookkeeping. Identical capped baskets can retain substantial cash under both allocation paths.", period)
        for base in BASES:
            arm = base + "-W"
            w = weights[(period, arm)]
            reserve = runs[(period, arm)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
            vault = w.drop(columns=reserve)
            names = list(vault.mean().nlargest(10).index)
            plot = vault[names].copy()
            other = vault.drop(columns=names).sum(axis=1)
            if other.max() > 1e-9:
                plot["Other vaults"] = other
            plot["Cash"] = w[reserve]
            fig, ax = plt.subplots(figsize=(11.5, 4.4))
            ax.stackplot(plot.index, *[plot[c].to_numpy() * 100 for c in plot], labels=plot.columns, colors=[palette[c] for c in plot])
            ax.set(ylim=(0, 100), ylabel="Fraction of total equity (%)", title=f"{arm}: absolute asset weights\n" + LABELS[period])
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8, frameon=False)
            parent.figure(data, fig, f"{period}-{arm}-weights", f"{arm}: absolute asset weights", "Vaults and cash sum to total equity. Show the ten largest average vault holdings separately and group the remainder; no renormalisation to invested capital.", period)
        parent.heading("Profit concentration and extreme updates", "Identify single-vault dependence and unusually large account updates. Sparse NAV updates can accumulate several days of returns into one account update.", period)
        display(robust[robust.Period.eq(period)].drop(columns="Period").style.format({"Best update": "{:.2%}", "Excess kurtosis": "{:.2f}", "Top positive profit share": "{:.1%}"}).hide(axis="index"))
        parent.heading("Vaults behind the strongest waterfall updates", "Attribute each waterfall arm’s largest account update to its three largest vault contributions. BTC/ETH context covers the same actual NAV observation interval; curator exclusion/quarantine flags are retained.", period)
        t = tails[tails.Period.eq(period) & tails.Arm.str.endswith("-W")].drop(columns=["Period", "First_mark", "Last_mark"])
        display(t.style.format({"Update profit (USD)": "${:,.0f}", "NAV_return": "{:+.2%}", "Interval_days": "{:.2f}", "BTCUSDT return": "{:+.2%}", "ETHUSDT return": "{:+.2%}"}).hide(axis="index"))
        funding = pd.DataFrame(data["funding_ledger"])
        fp = funding[funding.Period.eq(period)] if len(funding) else pd.DataFrame()
        if len(fp):
            parent.heading("Net-proceeds funding corrections", "Only overspending queues are changed. Buy reductions use final fee-adjusted planned sell proceeds; inherited charges remain included. These sums describe buy requests across decisions, rather than lost-profit estimates.", period)
            display(fp.groupby("Arm").agg(Cycles=("Date", "count"), **{"Buy reduction (USD)": ("Reduction (USD)", "sum")}).style.format({"Buy reduction (USD)": "${:,.2f}"}))
        if period == "2026":
            for base in BASES:
                r = {}
                for suffix in ("", "-W"):
                    arm = base + suffix
                    reserve = runs[(period, arm)]["result"].state.portfolio.get_default_reserve_asset()[0].token_symbol
                    cash = weights[(period, arm)].loc["2026-09-01":"2026-09-30", reserve]
                    r[suffix] = (float(cash.mean()), float(cash.max()))
                september.append({"Strategy": base, "Original mean cash": r[""][0], "Waterfall mean cash": r["-W"][0], "Waterfall peak cash": r["-W"][1], "Cash change (pp)": 100 * (r["-W"][0] - r[""][0])})
            parent.heading("September capacity bottleneck", "Compare mean September cash in the fresh-start 2026 accounts. This shows whether waterfall resolves the cash episode; a cash reduction alone does not establish better marginal profitability.", period)
            display(pd.DataFrame(september).set_index("Strategy").style.format({"Original mean cash": "{:.1%}", "Waterfall mean cash": "{:.1%}", "Waterfall peak cash": "{:.1%}", "Cash change (pp)": "{:+.2f}"}))
    deltas = pd.concat(deltas, ignore_index=True)
    deltas.to_csv(data["artifact"] / "paired-differences.csv", index=False)
    pd.DataFrame(september).to_csv(data["artifact"] / "september-cash.csv", index=False)
    pd.DataFrame(contributors).to_csv(data["artifact"] / "incremental-contributors.csv", index=False)
    funding = pd.DataFrame(data["funding_ledger"])
    text = conclusion(results, deltas, robust, september)
    c = pd.DataFrame(contributors)
    short = c[c.Period.eq("2026") & c.Strategy.eq("G")].iloc[0]
    long = c[c.Period.eq("Long") & c.Strategy.eq("C")].iloc[0]
    text += f'\n\n### Dependence and useful leads\n\nG-W’s 2026 gain over G is led by {short["Leading gain vault"]}: ${short["Leading vault difference (USD)"]:,.0f}, {short["Contribution / net lead"]:.1%} of the net advantage. C-W’s full-history gain over C is led by {long["Leading gain vault"]}: ${long["Leading vault difference (USD)"]:,.0f}, {long["Contribution / net lead"]:.1%} of the net advantage. These are ledger differences, not removal replays. The better results arise from changed exposures and timing; September remains capacity-limited. C-W is the stronger historical waterfall challenger; G-W has stronger 2026 performance but a deeper full-history drawdown.'
    text += "\n\n### Funding correction\n\nThe uncorrected A-W run failed on 12 July 2026 with $94.63 of overspending after final sell-price charges. The executable treatments retain those charges and reduce buys only to available net synchronous proceeds. "
    text += f'{len(funding)} decision queues required correction across the eight treatments, reducing requested buys by ${funding["Reduction (USD)"].sum():,.2f} in total.' if len(funding) else "No treatment queue required correction."
    display(Markdown(text))
    (ROOT / "16-waterfall-comparison-findings.md").write_text("# Experiment 16 — waterfall allocation comparison\n\n" + text + "\n\n" + LOGIC)
    import nbformat

    nb = nbformat.read(NOTEBOOK, as_version=4)
    header = nb.cells[0].source.split("<!-- Results -->")[0] + "<!-- Results -->\n\n" + text
    (data["artifact"] / "final-header.md").write_text(header)
    (data["artifact"] / "presentation.json").write_text(json.dumps({"figures": data["figures"], "separate_images": True}, indent=2))
    return text


def conclusion(results, deltas, robust, september):
    lines = ["## Key new insights", ""]
    for period in PERIODS:
        d = deltas[deltas.Period.eq(period)]
        wins = int(d["Profit difference (USD)"].gt(0).sum())
        best = results[results.Period.eq(period)].sort_values("Net profit (USD)", ascending=False).iloc[0]
        lines.append(f'- **{LABELS[period]}:** waterfall improves profit for {wins}/4 matched strategies. The highest-profit account is {best.Arm}, with {best.CAGR:.2%} CAGR, {best.Sharpe:.2f} Sharpe and {best["Maximum drawdown"]:.2%} drawdown.')
    lines += ["", "Waterfall changes risk-weight ordering into greedy dollar allocation. Its results therefore measure a different use of the risk estimator, rather than a new feature or ranking formula. Both allocators retain the six-position capacity ceiling; no residual-capacity extension is enabled.", "", "## Summary of results", ""]
    for period in PERIODS:
        lines += [f"### {LABELS[period]}", "", "| Arm | CAGR | Sharpe | Max drawdown | Mean cash |", "| --- | ---: | ---: | ---: | ---: |"]
        f = results[results.Period.eq(period)].set_index("Arm")
        for arm in ARMS:
            r = f.loc[arm]
            lines.append(f'| {arm} | {r.CAGR:.2%} | {r.Sharpe:.2f} | {r["Maximum drawdown"]:.2%} | {r["Mean cash weight"]:.2%} |')
        lines.append("")
    lines += ["### September 2026 cash", "", "| Strategy | Original mean cash | Waterfall mean cash | Change |", "| --- | ---: | ---: | ---: |"]
    for r in september:
        lines.append(f'| {r["Strategy"]} | {r["Original mean cash"]:.1%} | {r["Waterfall mean cash"]:.1%} | {r["Cash change (pp)"]:+.2f} pp |')
    lines += [
        "",
        "## Robustness of results",
        "",
        "All eight original-control accounts reproduce NB15 metrics. All sixteen accounts reconcile asset weights and position profit to equity, remain within six held vaults, and use known NAV at or before successful fill queries. Waterfall target ledgers check pre-admission concentration/TVL ceilings. Inherited deposit checks and rebalance bands can subsequently alter targets and realised holdings.",
        "",
        f'The largest update across these accounts is {robust["Best update"].max():.2%}; the largest single-vault share of positive profit is {robust["Top positive profit share"].max():.1%}. Tables attribute extreme updates to vault NAV observation intervals, BTC/ETH context and curator flags. These statistics do not establish independence from leading contributors.',
        "",
        "Both periods have already been examined in earlier research; the long account overlaps the fresh 2026 period. Sparse observations, retrospective universe/guard membership, inherited fee assumptions and the partial-trim fee convention remain limitations. No production change or independent predictive confirmation is claimed.",
    ]
    return "\n".join(lines)
