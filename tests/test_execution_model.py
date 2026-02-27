from upbit_autotrader.execution.execution_model import (
    ExecutionConfig,
    build_twap_schedule,
    estimate_expected_slippage_bps,
    estimate_realized_slippage_bps,
    plan_execution,
)


def test_expected_slippage_increases_with_order_size():
    s_small = estimate_expected_slippage_bps(realized_vol_pct=2.0, order_notional_krw=100_000, est_liquidity_krw=50_000_000)
    s_large = estimate_expected_slippage_bps(realized_vol_pct=2.0, order_notional_krw=5_000_000, est_liquidity_krw=50_000_000)
    assert s_large > s_small


def test_twap_schedule_preserves_total_notional():
    schedule = build_twap_schedule(100_000.0, slices=3, min_order_krw=5_000.0)
    assert len(schedule) == 3
    assert abs(sum(schedule) - 100_000.0) < 1e-6
    assert all(v >= 5_000.0 for v in schedule)


def test_execution_plan_scales_or_blocks_when_slippage_guard_exceeded():
    cfg = ExecutionConfig(
        enabled=True,
        expected_slippage_guard_bps=5.0,
        twap_slices=3,
        default_mode="twap_market",
    )
    plan = plan_execution(
        cfg,
        order_notional_krw=3_000.0,
        realized_vol_pct=20.0,
        est_liquidity_krw=100_000.0,
    )
    assert plan.blocked
    assert plan.reason in {"slippage_guard_blocked", "order_notional_non_positive"}


def test_realized_slippage_sign_convention():
    buy_slip = estimate_realized_slippage_bps(100.0, 101.0, side="buy")
    sell_slip = estimate_realized_slippage_bps(100.0, 99.0, side="sell")
    assert buy_slip > 0
    assert sell_slip > 0

