"""Audit realised exposure and vault-level profit changes for the frozen focal score."""

import json
from contextlib import redirect_stdout, redirect_stderr
import io

import numpy as np
import pandas as pd

from score_position_count_experiment import ARTIFACT_DIR, FOCAL_SCORE, initialise, evaluate
from accepted_dollar_cap import calculate_position_profit_curves
from tradeexecutor.analysis.weights import calculate_asset_weights
from tradeexecutor.visual.equity_curve import calculate_returns
from tradeexecutor.statistics.key_metric import calculate_cagr, calculate_sharpe
from tradeexecutor.curator.curator import EXCLUDED_VAULTS, get_hyperliquid_concentration_tweak, is_quarantined


def main():
    """Quantify changed exposure without treating fixed-ledger changes as causal effects."""
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        evaluator, _, candidates, _ = initialise()
    row = next(r for r in candidates if r["Configuration"] == FOCAL_SCORE)
    quality = get_hyperliquid_concentration_tweak()
    summaries = []
    vault_rows = []
    position_rows = []
    for n in (6, 7, 8, 10):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            run = evaluate(evaluator, row, "2026", n, keep=True)
        state = run["result"].state
        index = run["daily_returns"].index
        equity = run["equity"].resample("1D").last().reindex(index).ffill()
        curves, metadata = calculate_position_profit_curves(state, index)
        metadata["Positions"] = n
        metadata["Curator excluded"] = metadata.Address.isin(EXCLUDED_VAULTS)
        metadata["Quarantined at entry"] = [is_quarantined(address, opened) for address, opened in zip(metadata.Address, metadata.Opened)]
        position_rows.append(metadata)
        overrides = {p.position_id: p.pair.pool_address for p in state.portfolio.get_all_positions()}
        weights = calculate_asset_weights(state, position_asset_label_overrides=overrides).unstack().resample("1D").last().reindex(index).ffill().fillna(0)
        reserve = state.portfolio.get_default_reserve_asset()[0].token_symbol
        vault_weights = weights.drop(columns=reserve).div(equity, axis=0)
        ledger = run["allocation_df"]
        funded = ledger[ledger["Final target (USD)"] > 0]
        dollars = funded["Final target (USD)"]
        scores = funded["Ranking score"].fillna(0)
        pepe_positions = metadata[metadata.Vault.str.strip().eq("Pepe vs")]["Position id"]
        pepe_profit = curves[pepe_positions].sum(axis=1) if len(pepe_positions) else pd.Series(0.0, index=index)
        no_pepe_returns = calculate_returns(equity - pepe_profit)
        summaries.append({"Positions": n, "Mean realised vaults": float(vault_weights.gt(1e-8).sum(axis=1).mean()), "Maximum realised vaults": int(vault_weights.gt(1e-8).sum(axis=1).max()), "Mean cash weight": run["metrics"]["Mean cash weight"], "Target-dollar-weighted score": float((scores * dollars).sum() / dollars.sum()), "Unscored target dollars": float(dollars[funded["Ranking score"].isna()].sum() / dollars.sum()), "Final total vault PnL (USD)": float(curves.iloc[-1].sum()), "Pepe vs PnL (USD)": float(pepe_profit.iloc[-1]), "CAGR without Pepe vs (fixed ledger)": float(calculate_cagr(no_pepe_returns)), "Sharpe without Pepe vs (fixed ledger)": float(calculate_sharpe(no_pepe_returns, periods=365))})
        for address, group in metadata.groupby("Address"):
            vault_rows.append({"Positions": n, "Address": address, "Vault": group.Vault.iloc[0], "Profit (USD)": float(curves[group["Position id"]].sum(axis=1).iloc[-1]), "Mean equity weight": float(vault_weights[address].mean()), "Vault-days held": int(vault_weights[address].gt(1e-8).sum()), "Curator quality": getattr(quality.get(address), "value", "unrated"), "Curator excluded": address in EXCLUDED_VAULTS})
        print(f'Focal N={n}: CAGR={run["metrics"]["CAGR"]:.2%}, Sharpe={run["metrics"]["Sharpe"]:.2f}; retained state/exposure audit complete.', flush=True)
    summary = pd.DataFrame(summaries)
    vaults = pd.DataFrame(vault_rows)
    summary.to_csv(ARTIFACT_DIR / "2026-focal-exposure-summary.csv", index=False)
    vaults.to_csv(ARTIFACT_DIR / "2026-focal-vault-exposure-pnl.csv", index=False)
    pd.concat(position_rows, ignore_index=True).to_csv(ARTIFACT_DIR / "2026-focal-all-positions.csv", index=False)
    base = vaults[vaults.Positions.eq(6)].set_index("Address")
    changes = []
    for n in (7, 8, 10):
        other = vaults[vaults.Positions.eq(n)].set_index("Address")
        addresses = base.index.union(other.index)
        frame = pd.DataFrame(index=addresses)
        frame["Vault"] = other.Vault.combine_first(base.Vault).reindex(addresses)
        frame["Positions"] = n
        frame["Six-position PnL (USD)"] = base["Profit (USD)"].reindex(addresses, fill_value=0)
        frame["Wider PnL (USD)"] = other["Profit (USD)"].reindex(addresses, fill_value=0)
        frame["PnL change (USD)"] = frame["Wider PnL (USD)"] - frame["Six-position PnL (USD)"]
        frame["Six-position mean weight"] = base["Mean equity weight"].reindex(addresses, fill_value=0)
        frame["Wider mean weight"] = other["Mean equity weight"].reindex(addresses, fill_value=0)
        frame["Mean weight change"] = frame["Wider mean weight"] - frame["Six-position mean weight"]
        frame["Only held in wider variant"] = ~frame.index.isin(base.index)
        frame["Curator excluded"] = frame.index.isin(EXCLUDED_VAULTS)
        changes.append(frame.reset_index())
    changes = pd.concat(changes, ignore_index=True)
    changes.to_csv(ARTIFACT_DIR / "2026-focal-vault-changes.csv", index=False)
    print(json.dumps({"focal_paths": 4, "vault_rows": len(vaults), "unscored_target_fraction_max": float(summary["Unscored target dollars"].max())}))


if __name__ == "__main__":
    main()
