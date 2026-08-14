"""Tests for PriceUpdateThread signals and concurrency safety."""

import json
from unittest.mock import MagicMock
import pytest

from upbit_autotrader.runtime.price_thread import PriceUpdateThread


def test_price_thread_signals():
    thread = PriceUpdateThread()
    received_orders = []
    received_assets = []
    received_prices = []

    thread.order_event_received.connect(lambda d: received_orders.append(d))
    thread.asset_event_received.connect(lambda d: received_assets.append(d))
    thread.price_updated.connect(lambda d: received_prices.append(d))

    # Trigger ticker
    thread._on_ws_ticker("KRW-BTC", 95000000.0, {})
    assert len(received_prices) == 1
    assert received_prices[0] == {"KRW-BTC": 95000000.0}

    # Trigger myOrder
    thread._on_ws_my_order({"uuid": "test-uuid-1", "state": "done"})
    assert len(received_orders) == 1
    assert received_orders[0]["uuid"] == "test-uuid-1"

    # Trigger myAsset
    thread._on_ws_my_asset({"currency": "KRW", "balance": "5000000"})
    assert len(received_assets) == 1
    assert received_assets[0]["balance"] == "5000000"
