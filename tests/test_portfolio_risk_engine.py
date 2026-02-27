from upbit_autotrader.risk.portfolio_risk import (
    RiskLimitConfig,
    build_portfolio_risk_snapshot,
    evaluate_risk_limits,
    resolve_drawdown_state,
)


def test_drawdown_state_resolution():
    assert resolve_drawdown_state(-1.0, enabled=False) == "normal"
    assert resolve_drawdown_state(-2.0, enabled=True, caution_pct=2.0, defense_pct=4.0, halt_pct=7.0) == "caution"
    assert resolve_drawdown_state(-5.0, enabled=True, caution_pct=2.0, defense_pct=4.0, halt_pct=7.0) == "defense"
    assert resolve_drawdown_state(-8.0, enabled=True, caution_pct=2.0, defense_pct=4.0, halt_pct=7.0) == "halt"


def test_snapshot_includes_unrealized_and_external_positions():
    universe = {
        "KRW-BTC": {"qty": 1.0, "buy_price": 100.0, "current_price": 90.0},
    }
    account = {
        "KRW-BTC": {"qty": 1.0, "buy_price": 100.0, "current_price": 90.0},
        "KRW-ETH": {"qty": 2.0, "buy_price": 50.0, "current_price": 60.0},
    }
    snap = build_portfolio_risk_snapshot(
        initial_balance=1_000.0,
        realized_pnl=10.0,
        universe_positions=universe,
        account_wide_positions=account,
        include_unrealized=True,
        include_external_holdings=True,
        drawdown_state_enabled=True,
        dd_caution_pct=2.0,
        dd_defense_pct=4.0,
        dd_halt_pct=8.0,
    )
    assert "gross_exposure_krw" in snap
    assert int(snap["holdings_count"]) == 2
    assert int(snap["external_holdings_count"]) == 1
    assert "risk_state" in snap


def test_evaluate_risk_limits_blocks_on_daily_loss_and_holdings():
    snapshot = {
        "loss_rate": -6.0,
        "holdings_count": 3,
        "correlation_exposure_pct": 10.0,
        "risk_state": "normal",
    }
    allowed, triggered, reasons = evaluate_risk_limits(
        snapshot=snapshot,
        config=RiskLimitConfig(max_daily_loss_pct=5.0, max_holdings=3, max_correlation_exposure_pct=100.0),
        daily_loss_triggered=False,
    )
    assert not allowed
    assert triggered
    assert any("loss_rate_limit" in r for r in reasons)
    assert any("holdings_limit" in r for r in reasons)

