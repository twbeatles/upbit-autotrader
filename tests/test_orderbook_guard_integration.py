"""Tests for orderbook guard integration in signal_ops."""

import types
from unittest.mock import MagicMock
import pytest

from upbit_autotrader.controllers.trading_parts.signal_ops import _check_buy_condition
from upbit_autotrader.core.config import Config


def test_check_buy_condition_blocked_by_orderbook_spread_guard():
    logs = []
    executed_buys = []

    mock_trader = types.SimpleNamespace(
        is_running=True,
        strategy=types.SimpleNamespace(check_cooldown=lambda t: True, check_mtf_condition=lambda t: True),
        coins=["KRW-BTC"],
        universe={"KRW-BTC": {"target": 95000000.0, "current": 95100000.0, "qty": 0.0, "buy_price": 0.0, "ma": 94000000.0, "ma5": 94000000.0}},
        chk_use_rsi=types.SimpleNamespace(isChecked=lambda: False),
        chk_use_volume=types.SimpleNamespace(isChecked=lambda: False),
        chk_use_entry_scoring=types.SimpleNamespace(isChecked=lambda: False),
        combo_candle=types.SimpleNamespace(currentText=lambda: "4시간"),
        spin_rsi_period=types.SimpleNamespace(value=lambda: 14),
        check_risk_limits=lambda: True,
        log=lambda msg: logs.append(msg),
        logger=types.SimpleNamespace(warning=lambda msg: None, error=lambda msg: None),
        # Orderbook guard enabled
        chk_use_orderbook_guard=types.SimpleNamespace(isChecked=lambda: True),
        spin_max_orderbook_spread_bps=types.SimpleNamespace(value=lambda: 30.0),
        # Return wide spread orderbook (5% spread = 500 bps > 30 bps)
        _api_get_orderbook=lambda ticker, count=5: [{
            "market": "KRW-BTC",
            "orderbook_units": [
                {"ask_price": 105000000.0, "bid_price": 100000000.0, "ask_size": 1.0, "bid_size": 1.0}
            ]
        }],
        _ensure_order_stability_state=lambda: None,
        _is_trading_action_busy=lambda: False,
        _resolve_active_strategy_config=lambda: None,
        _should_apply_legacy_entry_gate=lambda cfg: True,
        _execute_buy_flow=lambda *args, **kwargs: executed_buys.append(args),
    )

    _check_buy_condition(mock_trader, "KRW-BTC", 95100000.0, mock_trader.universe["KRW-BTC"])

    # Buy should be blocked by orderbook spread guard
    assert len(executed_buys) == 0
    assert any("호가창 가드 보류" in log for log in logs)
