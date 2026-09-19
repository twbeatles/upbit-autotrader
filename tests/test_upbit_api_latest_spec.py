from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from upbit_autotrader.core.config import Config
from upbit_autotrader.services.rate_limit import RateLimitState, parse_remaining_req
from upbit_autotrader.services.upbit_client import UpbitRestClient
from upbit_autotrader.services.upbit_websocket import UpbitWebSocketClient
from upbit_autotrader.runtime.price_thread import PriceUpdateThread
from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.controllers.trading_parts import account_ops, order_api_ops


# =============================================================================
# 1. Rate Limit & Deprecated 'min' Field Tests (2026-08-21 Update)
# =============================================================================

def test_rate_limit_order_interval_2026_policy():
    """Verify order rate limit interval has been upgraded to 0.09s (12 req/s)."""
    intervals = Config.API_MIN_INTERVAL_BY_GROUP_SEC
    assert "order" in intervals
    assert intervals["order"] <= 0.10  # 12 req/s is ~0.083s, configured 0.09s for safety buffer
    assert "order-cancel-all" in intervals
    assert intervals["order-cancel-all"] == 2.0


def test_rate_limit_deprecated_min_field_ignored():
    """Verify that deprecated 'min' field in Remaining-Req header does NOT cause 1.0s throttling."""
    state = RateLimitState(
        min_interval_by_group={"order": 0.09},
        low_remaining_threshold=3,
    )

    # Mock response with low minute remaining (e.g. min=2), but sufficient second remaining (sec=10)
    mock_resp = MagicMock()
    mock_resp.headers = {"Remaining-Req": "group=order; min=2; sec=10"}

    state.observe_response("order", mock_resp)

    # Adaptive interval should NOT be bumped to 1.0 because 'min' is deprecated per 2026-08-21 notice
    adaptive_interval = state._adaptive_interval_by_group.get("order", 0.0)
    assert adaptive_interval < 0.5


def test_rate_limit_sec_field_still_adapts_under_pressure():
    """Verify that per-second remaining triggers safety backoff when sec <= 1."""
    state = RateLimitState(
        min_interval_by_group={"order": 0.09},
        low_remaining_threshold=3,
    )

    mock_resp = MagicMock()
    mock_resp.headers = {"Remaining-Req": "group=order; min=1000; sec=1"}

    state.observe_response("order", mock_resp)
    adaptive_interval = state._adaptive_interval_by_group.get("order", 0.0)
    assert adaptive_interval >= 0.5


# =============================================================================
# 2. Header Deduplication & Content-Type Tests (2026-07-31 Update)
# =============================================================================

def test_request_prevents_duplicate_content_type():
    """Verify session Content-Type header is cleaned to avoid duplicate merge 400 errors."""
    client = UpbitRestClient(access_key="dummy_acc", secret_key="dummy_secret_key_32_bytes_long_minimum!!")
    client.session.headers["Content-Type"] = "application/x-www-form-urlencoded"

    with patch.object(client.session, "post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"uuid": "test-uuid"}
        mock_resp.headers = {}
        mock_post.return_value = mock_resp

        client._request("POST", "/v1/orders", json_data={"market": "KRW-BTC"})

        # Verify Content-Type in session was popped and only the request header is passed once
        assert "Content-Type" not in client.session.headers
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Content-Type"] == "application/json"


def test_delete_request_sets_content_type_only_when_json_present():
    """Verify DELETE request only sets Content-Type when a JSON payload is actually sent."""
    client = UpbitRestClient(access_key="dummy_acc", secret_key="dummy_secret_key_32_bytes_long_minimum!!")

    with patch.object(client.session, "delete") as mock_delete:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.headers = {}
        mock_delete.return_value = mock_resp

        # 1. DELETE without json_data (query params only, e.g. cancel open orders)
        client._request("DELETE", "/v1/orders/open", params={"cancel_side": "bid"})
        _, kwargs1 = mock_delete.call_args
        assert "Content-Type" not in kwargs1["headers"]

        # 2. DELETE with json_data
        client._request("DELETE", "/v1/orders/uuids", json_data={"uuids": ["id-1"]})
        _, kwargs2 = mock_delete.call_args
        assert kwargs2["headers"]["Content-Type"] == "application/json"


# =============================================================================
# 3. New Endpoints & Parameters Tests (cancel_and_new, cancel_open_orders, pockets)
# =============================================================================

def test_cancel_and_new_order_success():
    """Verify cancel_and_new_order builds correct payload."""
    client = UpbitRestClient(access_key="acc", secret_key="sec")

    with patch.object(client, "_request") as mock_req:
        mock_req.return_value = {"uuid": "new-uuid"}
        res = client.cancel_and_new_order(
            prev_order_uuid="prev-1234",
            new_ord_type="limit",
            new_price=50000000,
            new_volume=0.01,
            new_time_in_force="ioc",
            new_identifier="my-client-id",
        )
        assert res == {"uuid": "new-uuid"}
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert args[0] == "POST"
        assert args[1] == "/v1/orders/cancel_and_new"
        assert kwargs["rate_group"] == "order"
        body = kwargs["json_data"]
        assert body["prev_order_uuid"] == "prev-1234"
        assert body["new_ord_type"] == "limit"
        assert body["new_price"] == "50000000"
        assert body["new_volume"] == "0.01"
        assert body["new_time_in_force"] == "ioc"
        assert body["new_identifier"] == "my-client-id"


def test_cancel_and_new_order_validation_errors():
    """Verify parameter mutual exclusions and requirements for cancel_and_new_order."""
    client = UpbitRestClient(access_key="acc", secret_key="sec")

    # Missing prev_order_uuid and prev_order_identifier
    with pytest.raises(ValueError, match="Either prev_order_uuid or prev_order_identifier"):
        client.cancel_and_new_order()

    # post_only and smp_type conflict
    with pytest.raises(ValueError, match="new_post_only option cannot be used together with new_smp_type"):
        client.cancel_and_new_order(
            prev_order_uuid="u1",
            new_post_only=True,
            new_smp_type="cancel_maker",
        )


def test_cancel_open_orders_success():
    """Verify cancel_open_orders builds correct DELETE request with rate_group=order-cancel-all."""
    client = UpbitRestClient(access_key="acc", secret_key="sec")

    with patch.object(client, "_request") as mock_req:
        mock_req.return_value = {"cancelled_count": 5}
        res = client.cancel_open_orders(cancel_side="bid", quote_currencies="KRW", count=50)
        assert res == {"cancelled_count": 5}
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert args[0] == "DELETE"
        assert args[1] == "/v1/orders/open"
        assert kwargs["rate_group"] == "order-cancel-all"
        params = kwargs["params"]
        assert params["cancel_side"] == "bid"
        assert params["quote_currencies"] == ["KRW"]
        assert params["count"] == 50


def test_cancel_open_orders_mutual_exclusion():
    """Verify quote_currencies and pairs cannot be specified together per Upbit docs."""
    client = UpbitRestClient(access_key="acc", secret_key="sec")
    with pytest.raises(ValueError, match="cannot be specified simultaneously"):
        client.cancel_open_orders(quote_currencies="KRW", pairs=["KRW-BTC"])


def test_create_order_post_only_and_smp_type():
    """Verify create_order supports post_only and enforces mutual exclusion with smp_type."""
    client = UpbitRestClient(access_key="acc", secret_key="sec")

    with patch.object(client, "_request") as mock_req:
        mock_req.return_value = {"uuid": "ord-1"}
        client.create_order(
            market="KRW-BTC",
            side="bid",
            price=60000000,
            volume=0.001,
            ord_type="limit",
            post_only=True,
        )
        _, kwargs = mock_req.call_args
        assert kwargs["json_data"]["time_in_force"] == "post_only"

    with pytest.raises(ValueError, match="post_only option cannot be used together with smp_type"):
        client.create_order(
            market="KRW-BTC",
            side="bid",
            price=60000000,
            volume=0.001,
            post_only=True,
            smp_type="cancel_maker",
        )


def test_pocket_apis():
    """Verify get_pockets and get_sub_pocket_balance endpoints."""
    client = UpbitRestClient(access_key="acc", secret_key="sec")

    with patch.object(client, "_request") as mock_req:
        mock_req.return_value = [{"pocket_id": "main"}]
        res = client.get_pockets()
        assert res == [{"pocket_id": "main"}]
        mock_req.assert_called_with("GET", "/v1/pockets", rate_group="exchange")

    with patch.object(client, "_request") as mock_req:
        mock_req.return_value = [{"currency": "KRW", "balance": "100000"}]
        res = client.get_sub_pocket_balance("sub-1")
        assert res == [{"currency": "KRW", "balance": "100000"}]
        mock_req.assert_called_with("GET", "/v1/pockets/sub-1/balance", rate_group="exchange")


# =============================================================================
# 4. WebSocket Announcement Stream Tests (2026-08-31 Feature)
# =============================================================================

def test_websocket_announcement_subscription_payload():
    """Verify WebSocket client includes announcement subscription when on_announcement is provided."""
    ann_events = []
    client = UpbitWebSocketClient(
        access_key="fake_acc",
        secret_key="fake_sec_key_32_bytes_long_minimum!!",
        markets=["KRW-BTC"],
        on_announcement=lambda d: ann_events.append(d),
        announcement_categories=["trade", "notice", "maintenance"],
    )

    payload_str = client._get_subscribe_payload()
    payload = json.loads(payload_str)

    types = [item.get("type") for item in payload if isinstance(item, dict)]
    assert "ticker" in types
    assert "myOrder" in types
    assert "myAsset" in types
    assert "announcement" in types

    ann_item = next(item for item in payload if item.get("type") == "announcement")
    assert ann_item["categories"] == ["trade", "notice", "maintenance"]
    assert ann_item["include_body"] is False


def test_websocket_announcement_message_dispatch():
    """Verify incoming announcement messages are dispatched to on_announcement callback."""
    received = []
    client = UpbitWebSocketClient(
        on_announcement=lambda d: received.append(d),
    )

    sample_msg = {
        "type": "announcement",
        "event_type": "CREATED",
        "uuid": "ann-562593104",
        "title": "[거래] 신규 거래 지원 안내",
        "category": "trade",
        "url": "https://upbit.com/notice?id=123",
    }

    client._on_message(None, json.dumps(sample_msg))
    assert len(received) == 1
    assert received[0]["title"] == "[거래] 신규 거래 지원 안내"
    assert received[0]["category"] == "trade"


def test_handle_ws_announcement_event_alert():
    """Verify _handle_ws_announcement_event logs notice and triggers warning on maintenance."""
    class FakeTrader:
        def __init__(self):
            self.logs = []
            self.alerts = []

        def log(self, msg):
            self.logs.append(msg)

        def _ops_alert(self, level, message, key, cooldown=0.0):
            self.alerts.append((level, message, key))

    trader = FakeTrader()

    # Normal trade notice
    account_ops._handle_ws_announcement_event(
        trader,
        {"category": "trade", "title": "신규 마켓 추가", "event_type": "CREATED"},
    )
    assert any("신규 마켓 추가" in m for m in trader.logs)
    assert len(trader.alerts) == 0

    # Maintenance notice triggers alert
    account_ops._handle_ws_announcement_event(
        trader,
        {"category": "maintenance", "title": "정기 서버 점검 안내", "event_type": "CREATED"},
    )
    assert any("서버점검" in m for m in trader.logs)
    assert len(trader.alerts) == 1
    assert trader.alerts[0][0] == "warning"
    assert trader.alerts[0][2] == "upbit_maintenance_notice"


# =============================================================================
# 5. WebSocket MyAsset Balance Integration Tests
# =============================================================================

def test_handle_ws_asset_event_updates_krw_and_coin_balance():
    """Verify _handle_ws_asset_event updates KRW balance and universe coins immediately."""
    class FakeLabel:
        def __init__(self):
            self.text = ""

        def setText(self, val):
            self.text = val

    class FakeItem:
        def __init__(self):
            self.text = ""

        def setText(self, val):
            self.text = val

    class FakeTrader:
        def __init__(self):
            self.balance = 500000.0
            self.lbl_balance = FakeLabel()
            self.universe = {
                "KRW-BTC": {
                    "qty": 0.0,
                    "buy_price": 0.0,
                    "ui_items": {"qty": FakeItem(), "buy_price": FakeItem()},
                }
            }

    trader = FakeTrader()

    # Incoming asset event
    asset_data = {
        "type": "myAsset",
        "assets": [
            {"currency": "KRW", "balance": "1500000.0", "locked": "0.0"},
            {"currency": "BTC", "balance": "0.05", "locked": "0.01", "avg_buy_price": "95000000"},
        ],
    }

    account_ops._handle_ws_asset_event(trader, asset_data)

    assert trader.balance == 1500000.0
    assert "1,500,000" in trader.lbl_balance.text

    btc_info = trader.universe["KRW-BTC"]
    assert pytest.approx(btc_info["qty"], 1e-6) == 0.06
    assert btc_info["buy_price"] == 95000000.0
    assert btc_info["ui_items"]["qty"].text == "0.06000000"
    assert "95,000,000" in btc_info["ui_items"]["buy_price"].text


# =============================================================================
# 6. Facade Parity Tests
# =============================================================================

def test_facade_exposes_new_api_and_ws_handlers():
    """Verify TraderTradingController facade exposes the new API and event handlers."""
    expected_new_attrs = [
        "_handle_ws_asset_event",
        "_handle_ws_announcement_event",
        "_api_cancel_open_orders",
        "_api_cancel_and_new_order",
    ]
    for attr_name in expected_new_attrs:
        assert hasattr(TraderTradingController, attr_name), f"{attr_name} must be exposed on facade"
        assert callable(getattr(TraderTradingController, attr_name))
