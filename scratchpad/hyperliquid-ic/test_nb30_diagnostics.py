"""Deterministic checks for timing, sparse returns and ranking accounting."""

import numpy as np
import pandas as pd
from nb30_diagnostics import last_mark_per_day, rolling_row, forward_row, membership, outcome_stats, rank


def run_checks():
    checks = []
    for values in [[5, 4, 3, 2, 1], [5, 4, 4, 4, 1], [1] * 10, [1, 1, 2, 3, 4, 5, 6]]:
        v = pd.Series(values, dtype=float)
        for high in [True, False]:
            w = membership(v, high)
            assert np.isclose(w.sum(), 0.2 * len(v))
            assert w.between(0, 1).all()
            for _, g in pd.DataFrame({"v": v, "w": w}).groupby("v"):
                assert g.w.nunique() == 1
    assert membership(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]), False).iloc[0] == 1
    y = pd.Series([np.nan, 0.1, 0.3, -0.1, 0.05])
    w = pd.Series([1.0, 0.5, 0.5, 0.0, 0.0])
    stats = outcome_stats(y, rank(pd.Series(range(5))), w)
    assert np.isclose(stats["top"], 0.2)
    assert np.isclose(stats["rest"], (0.05 + 0.15 - 0.1 + 0.05) / 3)
    assert np.isclose(stats["top_coverage"], 0.5)
    constant = outcome_stats(y, rank(pd.Series([1.0] * 5)), membership(pd.Series([1.0] * 5)))
    assert np.isclose(constant["spread"], 0) and np.isnan(constant["rho"])
    checks.append(dict(check="direction, fractional ties, missing outcomes and complementary weights", status="passed"))
    timestamps = pd.date_range("2026-01-01 12:00", periods=100)
    smooth = last_mark_per_day(pd.DataFrame({"timestamp": timestamps, "share_price": np.exp(np.arange(100) * 0.001)}))
    t = pd.Timestamp("2026-03-01")
    row = rolling_row(smooth, t, 7, 30)
    assert np.isclose(row["median_log_rate"], 0.001)
    assert row["last_observation_ts"] < t
    assert np.isclose(row["last_mark_age_days"], 0.5)
    mutated = smooth.copy()
    mutated.loc[mutated.index >= t, "share_price"] *= 100
    assert rolling_row(mutated, t, 7, 30) == row
    label = forward_row(smooth, t, 30)
    assert label["entry_ts"] == row["last_observation_ts"]
    assert t < label["exit_ts"] <= t + pd.Timedelta(days=30)
    assert np.isclose(label["return"], np.expm1(0.001 * label["actual_days"]))
    raw_exit = pd.DataFrame({"share_price": [1.0, 1.1, 9.0]}, index=pd.to_datetime(["2026-01-01 12:00", "2026-02-01 00:00", "2026-02-01 12:00"]))
    before = forward_row(raw_exit.iloc[:2], pd.Timestamp("2026-01-02"), 30)
    after = forward_row(raw_exit, pd.Timestamp("2026-01-02"), 30)
    assert before["exit_ts"] == after["exit_ts"] == pd.Timestamp("2026-02-01")
    assert np.isclose(before["return"], after["return"])
    weekly = smooth.iloc[::7]
    wr = rolling_row(weekly, t, 7, 30)
    assert np.isclose(wr["median_log_rate"], 0.001) and wr["unique_event_count"] < row["unique_event_count"]
    young = rolling_row(smooth.iloc[:3], pd.Timestamp("2026-01-04"), 7, 30)
    assert np.isnan(young["median_log_rate"]) and young["path_marks"] == 3
    checks.append(dict(check="original timestamps, actual elapsed time, future mutation, labels and weekly/young marks", status="passed"))
    flat = smooth.copy()
    flat.share_price = 1.0
    fr = rolling_row(flat, t, 7, 30)
    assert fr["median_log_rate"] == 0 and np.isnan(fr["sharpe_like"])
    jump = flat.copy()
    jump.loc[jump.index >= pd.Timestamp("2026-02-15"), "share_price"] = 2.0
    jr = rolling_row(jump, t, 7, 30)
    assert jr["median_log_rate"] == 0 and 0 < jr["largest_event_containment_share"] < 1
    loss = last_mark_per_day(pd.DataFrame({"timestamp": pd.to_datetime(["2026-01-01 12:00", "2026-01-02 12:00", "2026-01-03 12:00"]), "share_price": [1.0, 0.8, 0.8]}))
    lr = rolling_row(loss, pd.Timestamp("2026-01-04"), 7, 30)
    assert np.isclose(lr["mean_drawdown"], 0.2 * 1.5 / 2.5)
    checks.append(dict(check="flat, jump-and-flat, zero volatility and final drawdown carry", status="passed"))
    return checks


if __name__ == "__main__":
    print(pd.DataFrame(run_checks()).to_string(index=False))
