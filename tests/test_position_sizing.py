from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size


def test_legacy_position_sizing_uses_base_ratio_when_disabled():
    out = compute_position_size(
        PositionSizingInput(
            use_risk_budget_sizing=False,
            available_krw=1_000_000,
            base_betting_pct=10.0,
        )
    )
    assert abs(out.position_ratio_pct - 10.0) < 1e-9
    assert abs(out.order_notional_krw - 100_000.0) < 1e-9


def test_risk_budget_position_sizing_caps_by_max_betting():
    out = compute_position_size(
        PositionSizingInput(
            use_risk_budget_sizing=True,
            equity_krw=1_000_000,
            available_krw=500_000,
            current_price=100.0,
            atr_value=1.0,
            risk_budget_pct=0.5,
            atr_stop_mult=2.0,
            min_stop_pct=0.3,
            max_betting_pct=15.0,
        )
    )
    assert out.position_ratio_pct <= 15.0 + 1e-9
    assert out.order_notional_krw <= 75_000.0 + 1e-6


def test_drawdown_halt_forces_zero_position():
    out = compute_position_size(
        PositionSizingInput(
            use_risk_budget_sizing=True,
            equity_krw=1_000_000,
            available_krw=1_000_000,
            current_price=100.0,
            atr_value=1.0,
            risk_budget_pct=1.0,
            drawdown_state="halt",
        )
    )
    assert abs(out.position_ratio_pct) < 1e-12
    assert abs(out.order_notional_krw) < 1e-12


def test_kelly_adjustment_limits_position_size():
    out = compute_position_size(
        PositionSizingInput(
            use_risk_budget_sizing=True,
            equity_krw=1_000_000,
            available_krw=1_000_000,
            current_price=100.0,
            atr_value=0.5,
            risk_budget_pct=2.0,
            max_betting_pct=30.0,
            use_kelly_adjustment=True,
            kelly_scale=0.25,
            win_rate=0.55,
            avg_win_pct=1.2,
            avg_loss_pct=1.0,
        )
    )
    assert out.position_ratio_pct <= out.kelly_fraction_pct + 1e-9

