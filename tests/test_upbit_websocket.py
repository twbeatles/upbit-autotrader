"""Tests for Upbit WebSocket client and event handling."""

import json
import types
from unittest.mock import MagicMock
import pytest

from upbit_autotrader.services.upbit_websocket import UpbitWebSocketClient
from upbit_autotrader.controllers.trading_parts.execution_flow_ops import _handle_ws_order_event
from upbit_autotrader.services.order_service import UpbitOrderService


def test_websocket_subscribe_payload_public():
    client = UpbitWebSocketClient(markets=["KRW-BTC", "KRW-ETH"])
    payload_str = client._get_subscribe_payload()
    payload = json.loads(payload_str)
    assert len(payload) == 3
    assert "ticket" in payload[0]
    assert payload[1]["type"] == "ticker"
    assert "KRW-BTC" in payload[1]["codes"]
    assert payload[2]["format"] == "DEFAULT"


def test_websocket_subscribe_payload_private():
    client = UpbitWebSocketClient(
        access_key="fake_access",
        secret_key="fake_secret_key_32_bytes_long_minimum!!",
        markets=["KRW-BTC"],
    )
    payload_str = client._get_subscribe_payload()
    payload = json.loads(payload_str)
    types_subscribed = [p.get("type") for p in payload if "type" in p]
    assert "ticker" in types_subscribed
    assert "myOrder" in types_subscribed
    assert "myAsset" in types_subscribed


def test_websocket_on_message_ticker_and_myorder():
    ticker_events = []
    order_events = []

    client = UpbitWebSocketClient(
        on_ticker=lambda m, p, d: ticker_events.append((m, p)),
        on_my_order=lambda d: order_events.append(d),
    )

    # Ticker message
    ticker_msg = json.dumps({
        "type": "ticker",
        "code": "KRW-BTC",
        "trade_price": 95000000.0,
    }).encode("utf-8")
    client._on_message(None, ticker_msg)
    assert len(ticker_events) == 1
    assert ticker_events[0] == ("KRW-BTC", 95000000.0)

    # MyOrder message
    order_msg = json.dumps({
        "type": "myOrder",
        "code": "KRW-BTC",
        "uuid": "ws-order-uuid-1",
        "state": "trade",
        "price": 95000000.0,
    }).encode("utf-8")
    client._on_message(None, order_msg)
    assert len(order_events) == 1
    assert order_events[0]["uuid"] == "ws-order-uuid-1"


def test_handle_ws_order_event_transitions_pending():
    svc = UpbitOrderService()
    svc.mark_pending("KRW-BTC", "BUY", "order-uuid-999")

    transitions = []
    dirty_calls = []
    trader = types.SimpleNamespace(
        order_service=svc,
        _transition_pending=lambda t, s, reason="": transitions.append((t, s, reason)),
        _mark_reconciliation_dirty=lambda: dirty_calls.append(True),
    )

    event_data = {
        "type": "myOrder",
        "code": "KRW-BTC",
        "uuid": "order-uuid-999",
        "state": "done",
    }
    _handle_ws_order_event(trader, event_data)

    assert len(transitions) == 1
    assert transitions[0] == ("KRW-BTC", "done", "ws_myorder_done")
    assert len(dirty_calls) == 1
