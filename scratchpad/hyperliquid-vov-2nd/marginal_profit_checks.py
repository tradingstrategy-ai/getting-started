"""Independent algebra and feasibility examples required by the NB21 plan."""

from types import SimpleNamespace
import numpy as np
import pandas as pd
from marginal_profit_forecasts import Shape, Distribution, Head, fit_snapshot, predict_snapshot
from marginal_profit_allocation import Opportunity, solve
from k_ratio_features import forward_fill_nav, k_statistics


def checks():
    rows = []
    zp = np.array([0.0, 1.0, 2.0])
    wp = np.array([0.2, 0.6, 0.2])
    zn = np.array([0.5, 1.5])
    wn = np.array([0.5, 0.5])
    d = Distribution(0.3, 0.12, 0.08, Shape(zp, wp), Shape(zn, wn))
    r = np.r_[0.12 * zp, -0.08 * zn]
    w = np.r_[0.7 * wp, 0.3 * wn]
    for gross, basis in [(0.0, 0.0), (100.0, 100.0), (100.0, 70.0), (100.0, 140.0), (37.0, 14.0)]:
        expected = float(np.dot(w, 0.999 * gross * (1 + r) - 0.1 * np.maximum(gross * (1 + r) - basis, 0)))
        observed = d.terminal(gross, basis)
        assert abs(expected - observed) < 1e-10
        rows.append(dict(Check="Full distribution liquidation / basis kink", Case=f"{gross}/{basis}", Error=abs(expected - observed)))
    assert abs(d.terminal(1, 1) - 1 - (0.999 * d.mu - 0.1 * 0.7 * 0.12 - 0.001)) < 1e-12
    o = Opportunity(1, SimpleNamespace(pool_address="a"), 100.0, 70.0, d, d.downside, 0.0, 200.0, 96.9, True, "fixture")
    assert abs(o.flow(50) - 48.45) < 1e-9
    assert abs(o.future(50) - d.terminal(50, 35)) < 1e-9
    assert abs(o.future(130) - d.terminal(130, 100)) < 1e-9
    assert abs(o.gain(100)) < 1e-10
    rows.append(dict(Check="Partial sale, top-up and no-trade basis", Case="50/100/130", Error=0.0))
    nav = forward_fill_nav(np.array([np.nan, 100.0, np.nan, 120.0, np.nan]))[:, 0]
    assert np.isnan(nav[0]) and np.allclose(nav[1:], [100, 100, 120, 120])
    rows.append(dict(Check="Causal fill retains missing inception", Case="Sparse history", Error=0.0))
    assert np.isnan(k_statistics(np.ones((5, 1)))["K-ratio"][0])
    rows.append(dict(Check="Undefined flat K is not zero-risk signal", Case="Flat marks", Error=0.0))
    profitable = Distribution(0.2, 0.12, 0.03, Shape(np.array([1.0]), np.array([1.0])), Shape(np.array([1.0]), np.array([1.0])))
    opportunities = {i: Opportunity(i, SimpleNamespace(pool_address=str(i)), 0.0, 0.0, profitable, profitable.downside, 0.0, 20.0, 0.0, True, "open") for i in range(8)}
    target, info = solve(opportunities, 100.0, 100.0, np.inf, 1.0, 1.0)
    assert sum(target.values()) <= 100 + 1e-8 and info["Objective"] > 0
    assert sum(x > 0 for x in target.values()) > 6
    rows.append(dict(Check="Budget-free solver invests / no six-slot ceiling", Case=f"{sum(x>0 for x in target.values())} positions", Error=0.0))
    target, info = solve(opportunities, 100.0, 100.0, 0.003, 1.0, 1.0)
    assert sum(target[i] * opportunities[i].downside for i in target) / 100 <= 0.003 + 1e-10
    rows.append(dict(Check="Estimated downside budget and cash conservation", Case="Binding budget", Error=0.0))
    dates = pd.date_range("2025-01-01", periods=20)
    f = pd.DataFrame({"Date": np.repeat(dates, 3), "x": np.tile([-1.0, 0.0, 1.0], 20)})
    y = np.tile([False, False, True], 20)
    a = Head(["x"], 0.1, True).fit(f, y)
    b = Head(["x"], 0.1, True).fit(pd.concat([f, f], ignore_index=True), np.r_[y, y])
    error = float(np.max(abs(a.predict(f) - b.predict(f))))
    assert error < 1e-7, error
    rows.append(dict(Check="Date-balanced probability fit / duplicate invariance", Case="Double identical rows", Error=error))
    assert abs(o.target_mark(130) - 126.9) < 1e-9
    rows.append(dict(Check="Gross top-up maps to full reserve spend", Case="USD 30 top-up", Error=0.0))
    # Conditioning must retain the full date measure, rather than equalise sign-specific dates.
    from marginal_profit_data import SUPPORT, PERFORMANCE

    y = np.r_[[-0.05], np.full(99, 0.02), np.full(99, -0.01), [0.02]]
    f = pd.DataFrame({"Date": np.repeat(pd.to_datetime(["2025-01-01", "2025-01-02"]), 100), "Pair": np.arange(200), "Y": y, "Mature_at": pd.Timestamp("2025-02-01")})
    for c in SUPPORT + PERFORMANCE + ("c00_score",):
        f[c] = 0.0
    snapshot = fit_snapshot(f, 30, 1.0, True)
    triple = predict_snapshot(snapshot, f.head(1), "P")[0]
    d0 = Distribution(*triple, snapshot["positive"], snapshot["negative"])
    error = abs(d0.mu - f.Y.mean())
    assert error < 1e-9, (d0.mu, f.Y.mean())
    rows.append(dict(Check="Probability × conditional magnitudes reproduces weighted mean", Case="Different loss frequencies across dates", Error=error))
    return pd.DataFrame(rows)
