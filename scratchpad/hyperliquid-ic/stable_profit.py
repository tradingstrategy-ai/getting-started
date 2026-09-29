"""Bounded stable-profit policy and diagnostics for the Hyperliquid IC work.

The module deliberately keeps the production return ranking in ``ic_research``
and adds only the pre-registered risk-veto and young-vault paths from the
stable-profit plan.  It is kept separate so the completed IC notebooks remain
reproducible without changing their artefacts.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

from ic_research import (
    CANDIDATE_ANNUALISED_VOL_FLOOR,
    ResearchConfig,
    capped_weights,
    feature_names,
)


def short_core_columns(features: pd.DataFrame) -> list[str]:
    """Return the pre-registered short feature core available in ``features``."""
    return feature_names(features, include_optional=False)


def severe_loss_labels(labels: pd.DataFrame, *, horizon: int = 30, threshold: float = 0.90) -> pd.Series:
    """Return the sparse-compatible severe holding-period loss label."""

    return labels[f"forward_log_growth_raw_{horizon}"].lt(math.log(threshold))


def walk_forward_loss_predictions(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    horizon: int = 30,
    evaluation_dates: pd.DatetimeIndex | None = None,
    min_train_dates: int = 60,
    c: float = 1.0,
) -> pd.DataFrame:
    """Fit a monthly expanding severe-loss classifier without future leakage.

    A row enters a training fold only after its observed exit timestamp.  The
    model uses training-fold median imputation and scaling, fixed ``C=1`` and
    no class balancing.  Outcome weights are the existing duplicate-outcome
    weights, so repeated overlapping outcomes do not dominate the fit.
    """

    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    target_column = f"forward_log_growth_raw_{horizon}"
    exit_column = f"exit_ts_{horizon}"
    weight_column = f"outcome_weight_{horizon}"
    label_columns = ["date", "address", "eligible", target_column, exit_column, weight_column]
    data = features.merge(labels[label_columns], on=["date", "address", "eligible"], how="left")
    data["severe_loss"] = data[target_column].lt(math.log(0.90)).astype("boolean")
    data.loc[data[target_column].isna(), "severe_loss"] = pd.NA
    data["actual"] = data[target_column]
    if evaluation_dates is None:
        evaluation_dates = pd.DatetimeIndex(sorted(data.date.dropna().unique()))
    else:
        evaluation_dates = pd.DatetimeIndex(evaluation_dates)
    output: list[pd.DataFrame] = []
    for period in evaluation_dates.to_period("M").unique():
        test_dates = evaluation_dates[evaluation_dates.to_period("M") == period]
        boundary = test_dates.min()
        train = data[(data.date < boundary) & data[exit_column].notna() & (data[exit_column] <= boundary) & data.severe_loss.notna()].copy()
        result = data[data.date.isin(test_dates) & data.eligible].copy()
        result["fit_boundary"] = boundary
        result["target"] = f"severe_loss_{horizon}"
        result["horizon"] = horizon
        result["actual_loss"] = result.severe_loss.astype("Float64")
        result["prediction"] = np.nan
        result["loss_probability"] = np.nan
        result["status"] = "warmup"
        result["train_dates"] = int(train.date.nunique())
        result["train_rows"] = int(len(train))
        result["train_prevalence"] = float(train.severe_loss.mean()) if len(train) else np.nan
        usable = [column for column in feature_columns if column in train and train[column].notna().any()]
        if train.date.nunique() >= min_train_dates and len(usable) > 0 and train.severe_loss.nunique() == 2:
            model = make_pipeline(
                SimpleImputer(strategy="median", add_indicator=True),
                StandardScaler(),
                LogisticRegression(C=c, class_weight=None, max_iter=1000, solver="lbfgs"),
            )
            weights = train[weight_column].fillna(1.0).to_numpy(dtype=float)
            model.fit(train[usable], train.severe_loss.astype(int), logisticregression__sample_weight=weights)
            result["loss_probability"] = model.predict_proba(result[usable])[:, list(model[-1].classes_).index(1)]
            result["prediction"] = result.loss_probability
            result["status"] = "predicted"
        output.append(
            result[
                [
                    "date",
                    "address",
                    "target",
                    "horizon",
                    "prediction",
                    "loss_probability",
                    "actual",
                    "actual_loss",
                    "fit_boundary",
                    "status",
                    "train_dates",
                    "train_rows",
                    "train_prevalence",
                ]
            ]
        )
    return pd.concat(output, ignore_index=True) if output else pd.DataFrame()


def _veto_mask(values: pd.Series, fraction: float, address_order: pd.Index) -> tuple[pd.Series, int]:
    """Return deterministic top-tail veto mask and finite count."""

    finite = values.notna() & np.isfinite(values)
    count = int(finite.sum())
    excluded = int(math.floor(fraction * count))
    mask = pd.Series(False, index=values.index)
    if excluded:
        ranked = pd.DataFrame(
            {
                "row_index": values[finite].index,
                "value": values[finite].to_numpy(dtype=float),
                "address": values[finite].index.astype(str),
            }
        )
        ranked = ranked.sort_values(["value", "address"], ascending=[False, True], kind="stable")
        mask.loc[ranked.row_index.iloc[:excluded]] = True
    return mask, count


def initial_normalised_weights(
    frame: pd.DataFrame,
    score: pd.Series,
    *,
    max_positions: int,
    young_extension: bool = False,
) -> pd.Series:
    """Return the requested pre-cap allocation for the selected names."""

    ranked = score.sort_values(ascending=False, kind="stable").head(max_positions)
    if ranked.empty:
        return pd.Series(dtype=float)
    if not young_extension:
        inverse_variance = frame.loc[ranked.index, "incumbent_inverse_vol"].fillna(0).clip(lower=0).pow(2)
        if inverse_variance.sum() > 0:
            return inverse_variance / inverse_variance.sum()
        return pd.Series(1 / len(ranked), index=ranked.index, dtype=float)

    incumbent_inverse = pd.to_numeric(frame.loc[ranked.index, "incumbent_inverse_vol"], errors="coerce")
    valid_incumbent = incumbent_inverse.notna() & np.isfinite(incumbent_inverse) & incumbent_inverse.gt(0)
    fallback_vol = frame.loc[ranked.index, "daily_vol_30"].combine_first(frame.loc[ranked.index, "daily_vol_14"]).combine_first(frame.loc[ranked.index, "daily_vol_7"])
    fallback_valid = fallback_vol.notna() & np.isfinite(fallback_vol) & fallback_vol.ge(CANDIDATE_ANNUALISED_VOL_FLOOR)
    raw = pd.Series(np.nan, index=ranked.index, dtype=float)
    raw.loc[valid_incumbent] = incumbent_inverse.loc[valid_incumbent].pow(2)
    fallback = ~valid_incumbent & fallback_valid
    fallback_daily_std = fallback_vol.loc[fallback] / math.sqrt(365.0)
    raw.loc[fallback] = (1 / fallback_daily_std).pow(2)
    valid_raw = raw.replace([np.inf, -np.inf], np.nan).dropna()
    raw = raw.fillna(float(valid_raw.median()) if not valid_raw.empty else 1.0)
    return raw / raw.sum()


def stable_capped_weights(
    frame: pd.DataFrame,
    score: pd.Series,
    *,
    max_positions: int,
    config: ResearchConfig,
    portfolio_equity: float,
    young_extension: bool = False,
    accepted_dollar_cap: pd.Series | None = None,
) -> pd.Series:
    """Production-style inverse-risk weights with sparse-name safeguards."""

    ranked = score.sort_values(ascending=False, kind="stable").head(max_positions)
    if ranked.empty or portfolio_equity <= 0:
        return pd.Series(dtype=float)
    incumbent_inverse = pd.to_numeric(frame.loc[ranked.index, "incumbent_inverse_vol"], errors="coerce")
    valid_incumbent = incumbent_inverse.notna() & np.isfinite(incumbent_inverse) & incumbent_inverse.gt(0)
    fallback_vol = frame.loc[ranked.index, "daily_vol_30"].combine_first(frame.loc[ranked.index, "daily_vol_14"]).combine_first(frame.loc[ranked.index, "daily_vol_7"])
    fallback_valid = fallback_vol.notna() & np.isfinite(fallback_vol) & fallback_vol.ge(CANDIDATE_ANNUALISED_VOL_FLOOR)
    weights = initial_normalised_weights(frame, ranked, max_positions=len(ranked), young_extension=young_extension)
    caps = pd.Series(config.max_weight, index=ranked.index, dtype=float)
    if young_extension:
        sparse_or_young = frame.loc[ranked.index, "available_history_days"].lt(90) | frame.loc[ranked.index, "last_interval_days"].gt(2) | (~valid_incumbent & ~fallback_valid)
        caps.loc[sparse_or_young] = config.young_max_weight
    capacity = (config.max_tvl_fraction * frame.loc[ranked.index, "tvl_current"] / (portfolio_equity * config.target_deployment)).clip(lower=0, upper=config.max_weight)
    caps = pd.concat([caps, capacity], axis=1).min(axis=1)
    investable = portfolio_equity * config.target_deployment
    remaining, allocated, equity_left = weights.to_dict(), {}, investable
    while equity_left > 1e-6 and remaining:
        total_weight = sum(remaining.values())
        address = max(remaining, key=lambda item: (remaining[item] / total_weight, str(item)))
        asked = equity_left * remaining[address] / total_weight
        accepted = min(asked, caps[address] * investable)
        if accepted_dollar_cap is not None:
            accepted = min(accepted, float(accepted_dollar_cap.get(address, accepted)))
        allocated[address] = accepted / investable
        equity_left -= accepted
        del remaining[address]
    return pd.Series(allocated, dtype=float)


def simulate_stable_policy(
    features: pd.DataFrame,
    observations: pd.DataFrame,
    *,
    policy_name: str,
    veto_scores: pd.DataFrame | None = None,
    config: ResearchConfig | None = None,
    max_positions: int = 6,
    veto_feature: str | None = None,
    veto_fraction: float = 0.20,
    young_extension: bool = False,
    accepted_dollar_caps: pd.DataFrame | None = None,
    deployment_fraction_by_date: pd.Series | None = None,
    matched_invested_fraction_by_date: pd.Series | None = None,
    cap_at_requested_allocation: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Replay one stable-profit policy through a shared accounting path.

    ``policy_name='A0'`` is deliberately a no-op production comparator.  A1,
    A2 and A3 apply only their pre-registered finite-score tail veto and then
    use the same return ranking, six-slot selection, inverse-risk sizing and
    fee/cost accounting.  The third return value is the daily pool ledger.
    """

    config = config or ResearchConfig()
    frame = features.copy()
    if veto_scores is not None and not veto_scores.empty:
        frame = frame.merge(veto_scores, on=["date", "address"], how="left", suffixes=("", "_policy"))
    observations = observations[observations.is_fresh].copy()
    observations["date"] = observations.timestamp.dt.normalize()
    actual_mark_groups = {date: group.sort_values("timestamp").groupby("address").share_price.last() for date, group in observations.groupby("date", sort=True)}
    # The production universe forward-fills vault candles before calculating
    # indicators and candidate availability.  ``nav`` is the latest observation
    # known at each causal decision date, so it is the equivalent carried mark.
    # Retain actual marks above to report how much of the selected book is
    # carried rather than freshly observed.
    forward_mark_groups = {date: group.set_index("address").nav.dropna() for date, group in frame.groupby("date", sort=True)}
    cash, holdings, last_marks, cost_basis = config.initial_cash, {}, {}, {}
    rows: list[dict] = []
    trades: list[dict] = []
    pool_rows: list[dict] = []
    rebalance_days = config.production_rebalance_days
    for number, (date, day_frame) in enumerate(frame.groupby("date", sort=True)):
        day = day_frame.set_index("address")
        marks = forward_mark_groups.get(date, pd.Series(dtype=float))
        actual_marks = actual_mark_groups.get(date, pd.Series(dtype=float))
        for address, nav in marks.items():
            last_marks[address] = float(nav)
        marked = {address: quantity * last_marks[address] for address, quantity in holdings.items() if address in last_marks}
        equity = cash + sum(marked.values())
        turnover = fee = 0.0
        if number % rebalance_days == 0:
            # Every row in the panel is within the configured causal NAV-age
            # limit.  Do not impose a second fresh-observation admission gate:
            # Hyper AI trades the same carried daily candles.
            available = day.copy()
            stale_holdings = {address: value for address, value in marked.items() if address not in marks.index}
            budget = max(equity - sum(stale_holdings.values()), 0.0)
            candidates = available[available.incumbent_return_gate.gt(-0.16)].copy()
            gate_unavailable = available.incumbent_return_gate.isna()
            if young_extension and gate_unavailable.any():
                young = available[gate_unavailable & available.available_history_days.lt(90)].copy()
                candidates = pd.concat([candidates, young]).sort_index()
            pool_candidates = candidates.copy()
            pool_empty = pool_candidates.empty
            active = False
            vetoed = pd.Series(False, index=candidates.index)
            finite_count = missing_count = 0
            if veto_feature and veto_feature in candidates:
                if policy_name.startswith("A") and policy_name not in {"A0", "A0-young"}:
                    vetoed, finite_count = _veto_mask(candidates[veto_feature], veto_fraction, candidates.index)
                    missing_count = int(candidates[veto_feature].isna().sum())
                    active = finite_count > 0
                    candidates = candidates.loc[~vetoed].copy()
                else:
                    active = False
            elif policy_name in {"A2", "A2-young"}:
                active = False
            signal = candidates.incumbent_score.fillna(0.0).sort_index()
            if young_extension and "young_score" in candidates:
                signal = signal.where(candidates.incumbent_score.notna(), candidates.young_score.fillna(0.0))
            caps = None
            if accepted_dollar_caps is not None and not accepted_dollar_caps.empty:
                caps = accepted_dollar_caps[accepted_dollar_caps.date == date].set_index("address").accepted_dollars
            deployment_fraction = config.target_deployment
            if deployment_fraction_by_date is not None:
                value = deployment_fraction_by_date.get(date, config.target_deployment)
                if pd.notna(value):
                    deployment_fraction = float(np.clip(value, 0.0, config.target_deployment))
            matched_fraction = None
            if matched_invested_fraction_by_date is not None:
                value = matched_invested_fraction_by_date.get(date, config.target_deployment)
                if pd.notna(value):
                    matched_fraction = float(np.clip(value, 0.0, config.target_deployment))
            day_config = config if deployment_fraction == config.target_deployment else config.__class__(**{**config.__dict__, "target_deployment": deployment_fraction})
            investable = budget * deployment_fraction
            if not young_extension:
                requested_weights = initial_normalised_weights(candidates, signal, max_positions=max_positions)
                if cap_at_requested_allocation:
                    caps = requested_weights * investable
                # Exact production sizing for A0 and the three primary vetoes.
                # Keeping this call unchanged gives the no-op parity check a
                # meaningful reference against the previous replay.
                weights = capped_weights(
                    candidates,
                    signal,
                    max_positions=max_positions,
                    config=day_config,
                    portfolio_equity=budget,
                    use_inverse_variance=True,
                    accepted_dollar_cap=caps,
                )
            else:
                requested_weights = initial_normalised_weights(candidates, signal, max_positions=max_positions, young_extension=True)
                if cap_at_requested_allocation:
                    caps = requested_weights * investable
                weights = stable_capped_weights(
                    candidates,
                    signal,
                    max_positions=max_positions,
                    config=day_config,
                    portfolio_equity=budget,
                    young_extension=young_extension,
                    accepted_dollar_cap=caps,
                )
            if matched_fraction is not None and weights.sum() > 0:
                # ``matched_fraction`` is measured against budget, whereas
                # sizing weights are fractions of the investable budget.
                weights *= min(1.0, matched_fraction / (deployment_fraction * float(weights.sum())))
            target = stale_holdings | {address: investable * weight for address, weight in weights.items()}
            turnover = sum(abs(target.get(a, 0) - marked.get(a, 0)) for a in set(target) | set(marked))
            sold = sum(max(marked.get(a, 0) - target.get(a, 0), 0) for a in set(target) | set(marked))
            profit_fee = 0.0
            for address in set(marked) | set(target):
                sale = max(marked.get(address, 0) - target.get(address, 0), 0)
                if sale and marked.get(address, 0):
                    basis_sold = cost_basis.get(address, marked.get(address, 0)) * sale / marked[address]
                    profit_fee += max(sale - basis_sold, 0) * config.performance_fee
                    cost_basis[address] = max(cost_basis.get(address, marked[address]) - basis_sold, 0)
            fee = sold * config.redemption_capital_fee + profit_fee
            cash = equity - sum(target.values()) - fee
            assert cash >= -1e-6, f"Negative cash on {date}: {cash}"
            cash = max(cash, 0.0)
            for address, value in target.items():
                if value > marked.get(address, 0):
                    cost_basis[address] = cost_basis.get(address, 0) + value - marked.get(address, 0)
            holdings = {address: value / last_marks[address] for address, value in target.items() if value > 0 and address in last_marks}
            equity = cash + sum(target.values())
            invested_target = float(sum(target.get(address, 0.0) for address in weights.index))
            trades.append({"date": date, "turnover": turnover, "sold_value": sold, "fee": fee, "performance_fee": profit_fee, "policy": policy_name, "stale_holdings": len(stale_holdings), "carried_candidates": int(candidates.nav_age_days.gt(1).sum()), "veto_active": active, "veto_inactive": bool(veto_feature is not None and not active), "pool_empty": pool_empty, "veto_finite": finite_count, "veto_missing": missing_count, "vetoed": int(vetoed.sum()), "budget": float(budget), "invested_target": invested_target, "deployment_fraction": float(deployment_fraction), "matched_invested_fraction": float(matched_fraction) if matched_fraction is not None else np.nan, "invested_fraction": float(invested_target / budget) if budget > 0 else 0.0})
            covered_days = pool_candidates.get("observed_covered_days_30")
            young_proxy = pool_candidates.get("young_proxy")
            pool_rows.extend(
                {
                    "date": date,
                    "address": address,
                    "policy": policy_name,
                    "in_incumbent_pool": True,
                    "vetoed": bool(vetoed.get(address, False)),
                    "veto_active": active,
                    "veto_inactive": bool(veto_feature is not None and not active),
                    "pool_empty": pool_empty,
                    "veto_finite": finite_count,
                    "veto_missing": missing_count,
                    "selected": address in weights.index,
                    "requested_dollars": float(investable * requested_weights.get(address, 0.0)),
                    "target_dollars": float(target.get(address, 0.0)),
                    "available_history_days": float(pool_candidates.at[address, "available_history_days"]),
                    "observed_covered_days_30": float(covered_days.get(address, np.nan)) if covered_days is not None else np.nan,
                    "young_proxy": float(young_proxy.get(address, np.nan)) if young_proxy is not None else np.nan,
                    "young_short_span": bool(young_extension and covered_days is not None and pd.notna(covered_days.get(address, np.nan)) and float(covered_days.get(address)) < 8),
                }
                for address in pool_candidates.index
            )
        rows.append({"date": date, "equity": equity, "cash": cash, "n_positions": len(holdings), "turnover": turnover, "fee": fee, "stale_positions": sum(address not in marks.index for address in holdings), "carried_positions": sum(address in marks.index and address not in actual_marks.index for address in holdings), "policy": policy_name})
    equity = pd.DataFrame(rows)
    if not equity.empty:
        equity["return"] = equity.equity.pct_change()
        equity["drawdown"] = equity.equity / equity.equity.cummax() - 1
    return equity, pd.DataFrame(trades), pd.DataFrame(pool_rows)


def weekly_curve(equity: pd.DataFrame) -> pd.DataFrame:
    """Take last observed portfolio equity at every UTC week, retaining gaps."""

    if equity.empty:
        return equity.copy()
    frame = equity.copy()
    frame["week"] = frame.date.dt.to_period("W-SUN").dt.end_time.dt.normalize()
    weekly = frame.sort_values("date").groupby("week", as_index=False).last()
    weekly["return"] = weekly.equity.pct_change()
    weekly["drawdown"] = weekly.equity / weekly.equity.cummax() - 1
    return weekly


def paired_block_sharpe_samples(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    block_days: int,
    draws: int = 2_000,
    seed: int = 1,
    periods_per_year: float = 365.0,
) -> tuple[float, np.ndarray, int]:
    """Return a paired moving-block bootstrap of Sharpe differences."""

    paired = left[["date", "return"]].merge(right[["date", "return"]], on="date", suffixes=("_left", "_right")).dropna().sort_values("date")
    if len(paired) < 2:
        return np.nan, np.array([], dtype=float), len(paired)
    left_values = paired.return_left.to_numpy(dtype=float)
    right_values = paired.return_right.to_numpy(dtype=float)

    def sharpe(values: np.ndarray) -> float:
        deviation = values.std(ddof=1)
        return float(values.mean() / deviation * math.sqrt(periods_per_year)) if np.isfinite(deviation) and deviation > 0 else np.nan

    point = sharpe(left_values) - sharpe(right_values)
    rng = np.random.default_rng(seed)
    length = min(max(int(block_days), 1), len(paired))
    samples = np.full(draws, np.nan)
    for draw in range(draws):
        starts = rng.integers(0, len(paired), size=math.ceil(len(paired) / length))
        indices = np.concatenate([np.arange(start, start + length) % len(paired) for start in starts])[: len(paired)]
        samples[draw] = sharpe(left_values[indices]) - sharpe(right_values[indices])
    return point, samples, len(paired)


def classification_metrics(predictions: pd.DataFrame) -> dict:
    """Return finite held-out classifier diagnostics."""

    from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

    data = predictions[(predictions.status == "predicted") & predictions.actual_loss.notna() & predictions.loss_probability.notna()].copy()
    if data.empty or data.actual_loss.nunique() < 2:
        return {"rows": int(len(data))}
    y = data.actual_loss.astype(int)
    p = data.loss_probability.clip(1e-6, 1 - 1e-6)
    prevalence = float(y.mean())
    baseline = np.full(len(y), prevalence, dtype=float)
    return {
        "rows": int(len(data)),
        "dates": int(data.date.nunique()),
        "prevalence": prevalence,
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "base_rate_brier": float(brier_score_loss(y, baseline)),
        "base_rate_log_loss": float(log_loss(y, baseline, labels=[0, 1])),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
    }
