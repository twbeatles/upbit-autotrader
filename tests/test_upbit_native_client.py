"""Tests for UpbitRestClient native REST client."""

from unittest.mock import MagicMock, patch
import pytest

from upbit_autotrader.services.upbit_client import UpbitRestClient
from upbit_autotrader.services.rate_limit import RateLimitState


def test_jwt_token_generation():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    token = client._generate_jwt_token()
    assert token.startswith("Bearer ")

    # Token with query string
    token_with_query = client._generate_jwt_token("market=KRW-BTC&side=bid")
    assert token_with_query.startswith("Bearer ")


def test_get_balances():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=exchange; min=900; sec=30"}
    mock_resp.json.return_value = [
        {"currency": "KRW", "balance": "1000000.0", "locked": "0.0"},
        {"currency": "BTC", "balance": "0.5", "locked": "0.0"},
    ]

    with patch.object(client.session, "get", return_value=mock_resp):
        balances = client.get_balances()
        assert len(balances) == 2
        assert balances[0]["currency"] == "KRW"

        krw_balance = client.get_balance("KRW")
        assert krw_balance == 1000000.0

        btc_balance = client.get_balance("KRW-BTC")
        assert btc_balance == 0.5


def test_get_chance():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=exchange; min=900; sec=30"}
    mock_resp.json.return_value = {
        "bid_fee": "0.0005",
        "ask_fee": "0.0005",
        "maker_bid_fee": "0.0005",
        "maker_ask_fee": "0.0005",
        "market": {"id": "KRW-BTC", "state": "active"},
    }

    with patch.object(client.session, "get", return_value=mock_resp):
        chance = client.get_chance("KRW-BTC")
        assert chance is not None
        assert chance["bid_fee"] == "0.0005"
        assert chance["maker_bid_fee"] == "0.0005"


def test_create_order_and_market_orders():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 201
    mock_resp.headers = {"Remaining-Req": "group=order; min=200; sec=8"}
    mock_resp.json.return_value = {
        "uuid": "test-order-uuid-1234",
        "side": "bid",
        "ord_type": "price",
        "price": "50000",
        "state": "wait",
    }

    with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
        result = client.buy_market_order("KRW-BTC", 50000, identifier="my-id-1")
        assert result["uuid"] == "test-order-uuid-1234"
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["market"] == "KRW-BTC"
        assert call_kwargs["json"]["side"] == "bid"
        assert call_kwargs["json"]["ord_type"] == "price"
        assert call_kwargs["json"]["identifier"] == "my-id-1"


def test_get_orders_by_uuids():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=exchange; min=900; sec=30"}
    mock_resp.json.return_value = [
        {"uuid": "uuid-1", "state": "done"},
        {"uuid": "uuid-2", "state": "wait"},
    ]

    with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
        orders = client.get_orders_by_uuids(uuids=["uuid-1", "uuid-2"])
        assert len(orders) == 2
        assert orders[0]["uuid"] == "uuid-1"
        call_params = mock_get.call_args[1]["params"]
        assert "uuids[]" in call_params
        assert call_params["uuids[]"] == ["uuid-1", "uuid-2"]

    # Cancel multiple
    with patch.object(client.session, "delete", return_value=mock_resp) as mock_del:
        cancelled = client.cancel_orders_by_uuids(uuids=["uuid-1", "uuid-2"])
        assert len(cancelled) == 2
        del_params = mock_del.call_args[1]["params"]
        assert "uuids[]" in del_params


def test_get_open_orders():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=exchange; min=900; sec=30"}
    mock_resp.json.return_value = [
        {"uuid": "uuid-open-1", "market": "KRW-BTC", "state": "wait"}
    ]

    with patch.object(client.session, "get", return_value=mock_resp):
        open_orders = client.get_open_orders()
        assert len(open_orders) == 1
        assert open_orders[0]["uuid"] == "uuid-open-1"


def test_get_current_price_multi():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=quotation_ticker; min=600; sec=10"}
    mock_resp.json.return_value = [
        {"market": "KRW-BTC", "trade_price": 95000000.0},
        {"market": "KRW-ETH", "trade_price": 4500000.0},
    ]

    with patch.object(client.session, "get", return_value=mock_resp):
        # Multi ticker
        prices = client.get_current_price(["KRW-BTC", "KRW-ETH"])
        assert isinstance(prices, dict)
        assert prices["KRW-BTC"] == 95000000.0
        assert prices["KRW-ETH"] == 4500000.0

        # Single ticker
        mock_resp.json.return_value = [{"market": "KRW-BTC", "trade_price": 95000000.0}]
        price = client.get_current_price("KRW-BTC")
        assert price == 95000000.0
