"""Tests for newly added Upbit endpoints (ticks, transfers read-only, order/test)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from upbit_autotrader.services.upbit_client import UpbitRestClient
from upbit_autotrader.services.upbit_websocket import UpbitWebSocketClient
import json


def _client():
    return UpbitRestClient(access_key="acc", secret_key="sec")


def test_get_tickers_returns_list():
    client = _client()
    with patch.object(client, "_request", return_value=[{"market": "KRW-BTC"}]) as m:
        res = client.get_tickers(["KRW-BTC", "KRW-ETH"])
        assert res == [{"market": "KRW-BTC"}]
        _, kwargs = m.call_args
        assert kwargs["params"] == {"markets": "KRW-BTC,KRW-ETH"}
        assert kwargs["auth"] is False


def test_get_recent_trades_clamps_count_and_empty_market():
    client = _client()
    assert client.get_recent_trades("") == []
    with patch.object(client, "_request", return_value=[]) as m:
        client.get_recent_trades("KRW-BTC", count=999)
        _, kwargs = m.call_args
        assert kwargs["params"]["count"] == 500
        assert kwargs["params"]["market"] == "KRW-BTC"


def test_test_order_uses_order_test_group():
    client = _client()
    with patch.object(client, "_request", return_value={"uuid": "t"}) as m:
        res = client.test_order(market="KRW-BTC", side="bid", price=5000, ord_type="price")
        assert res == {"uuid": "t"}
        args, kwargs = m.call_args
        assert args == ("POST", "/v1/order/test")
        assert kwargs["rate_group"] == "order-test"


def test_transfer_read_only_endpoints():
    client = _client()
    with patch.object(client, "_request", return_value=[]) as m:
        assert client.get_deposits(limit=5) == []
        args, _ = m.call_args
        assert args[1] == "/v1/deposits"
    with patch.object(client, "_request", return_value=[]) as m:
        assert client.get_withdraws(currency="KRW-BTC") == []
        _, kwargs = m.call_args
        assert kwargs["params"]["currency"] == "BTC"
    with patch.object(client, "_request", return_value={"currency": "BTC"}) as m:
        assert client.get_withdraw_chance("BTC") == {"currency": "BTC"}
    assert client.get_withdraw_chance("") is None
    with patch.object(client, "_request", return_value={"address": "x"}) as m:
        assert client.get_deposit_address("BTC") == {"address": "x"}
    assert client.get_deposit_address("") is None


def test_websocket_trade_orderbook_opt_in():
    base = UpbitWebSocketClient(markets=["KRW-BTC"])
    payload = json.loads(base._get_subscribe_payload())
    types = [p.get("type") for p in payload if "type" in p]
    assert "trade" not in types and "orderbook" not in types

    trades, books = [], []
    client = UpbitWebSocketClient(
        markets=["KRW-BTC"],
        on_trade=lambda d: trades.append(d),
        on_orderbook=lambda d: books.append(d),
    )
    payload = json.loads(client._get_subscribe_payload())
    types = [p.get("type") for p in payload if "type" in p]
    assert "trade" in types and "orderbook" in types
    client._on_message(None, json.dumps({"type": "trade", "code": "KRW-BTC"}).encode())
    client._on_message(None, json.dumps({"type": "orderbook", "code": "KRW-BTC"}).encode())
    assert len(trades) == 1 and len(books) == 1
