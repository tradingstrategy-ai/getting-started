from nb20_stability_screens import curve_metrics

ROBUST_OUT = PROJECT / "_artifacts-quality-only/leave-one-out"
ROBUST_OUT.mkdir(exist_ok=True)
LOO_ADDRESS = "0xcbbb26d5e622fb877e12745921ae8b1f820ffbed"
loo_rows = []
BLACKLIST_MODE = "off"
ACTIVE_SCREEN = "none"
strategy_universe = UNIVERSES["off"]
for period, start, end, common_start, common_end in [("hyper_ai", datetime.datetime(2026, 1, 1), datetime.datetime(2026, 7, 10), "2026-01-01", "2026-07-08"), ("full", datetime.datetime(2025, 8, 1), datetime.datetime(2026, 9, 9), "2025-09-13", "2026-09-08")]:
    SCREEN_LOG.clear()
    CYCLE_LOG.clear()
    print(f"Leave-one-vault-out sensitivity: {period}; usually under one minute per run")
    with patch("tradeexecutor.strategy.pandas_trader.position_manager.PositionManager.is_problematic_pair", return_value=False):
        state_loo, curve_loo, _ = run_variant("quality-only-leave-intothecryptoverse-out-" + period, masked={LOO_ADDRESS}, backtest_start=start, backtest_end=end, max_assets_in_portfolio=len(off_addresses), max_concentration_pct=1.0, per_position_cap_of_pool_pct=1.0)
    assert all(str(p.pair.pool_address).lower() != LOO_ADDRESS for p in state_loo.portfolio.get_all_positions())
    saved = curve_loo.rename("equity").to_frame()
    saved.attrs = {}
    saved.to_parquet(ROBUST_OUT / f"curve-{period}.parquet")
    baseline = pd.read_parquet(PROJECT / "_artifacts-quality-only" / f"curve-{period}-anchor-none.parquet").equity
    dates = baseline.index[(baseline.index >= pd.Timestamp(common_start)) & (baseline.index <= pd.Timestamp(common_end))]
    for label, series in [("unrestricted_anchor", baseline), ("leave_intothecryptoverse_out", curve_loo)]:
        assert series.reindex(dates).notna().all()
        loo_rows.append({"period": period, "variant": label, **curve_metrics(series.reindex(dates))})
    del state_loo
loo_results = pd.DataFrame(loo_rows)
loo_results.to_csv(ROBUST_OUT / "comparison.csv", index=False)
display(loo_results)
