"""Tests for order API extensions: identifier, maker fee extraction, open orders recovery."""

import types
from unittest.mock import MagicMock, patch
import pytest

from upbit_autotrader.controllers.trading_parts.order_api_ops import (
    _extract_chance_fee_bps,
    _extract_chance_all_fees_bps,
    _place_buy_order,
    _place_sell_order,
)
from upbit_autotrader.controllers.trading_parts.lifecycle_ops import (
    _recover_exchange_open_orders,
)
from upbit_autotrader.services.order_service import UpbitOrderService


def test_extract_chance_all_fees():
    chance = {
        "bid_fee": "0.0005",
        "ask_fee": "0.0005",
        "maker_bid_fee": "0.0002",
        "maker_ask_fee": "0.0002",
    }
    bid_bps, ask_bps, maker_bid_bps, maker_ask_bps = _extract_chance_all_fees_bps(chance)
    assert bid_bps == 5.0
    assert ask_bps == 5.0
    assert maker_bid_bps == 2.0
    assert maker_ask_bps == 2.0

    # Backward compatibility
    legacy_bid, legacy_ask = _extract_chance_fee_bps(chance)
    assert legacy_bid == 5.0
    assert legacy_ask == 5.0


def test_order_placement_with_identifier():
    svc = UpbitOrderService()
    trader = types.SimpleNamespace(
        _is_paper_mode=lambda: False,
        order_service=svc,
        _transition_pending=lambda *args, **kwargs: True,
        _mark_reconciliation_dirty=lambda: None,
        _api_buy_market_order=MagicMock(return_value={"uuid": "uuid-1234"}),
        _api_sell_market_order=MagicMock(return_value={"uuid": "uuid-5678"}),
    )

    # Buy order with identifier
    ok, res, err = _place_buy_order(trader, "KRW-BTC", 50000, session_id=1, identifier="custom-buy-id")
    assert ok is True
    pending = svc.get_pending("KRW-BTC")
    assert pending is not None
    assert pending["uuid"] == "uuid-1234"
    assert pending["identifier"] == "custom-buy-id"

    # Verify get_pending_by_identifier
    ticker, record = svc.get_pending_by_identifier("custom-buy-id")
    assert ticker == "KRW-BTC"
    assert record is not None
    assert record["uuid"] == "uuid-1234"


def test_recover_exchange_open_orders():
    svc = UpbitOrderService()
    manual_reviews = {}
    logs = []

    def mock_register_mr(self, ticker, uuid, reason, order=None, extra=None):
        manual_reviews[uuid] = {"ticker": ticker, "reason": reason, "extra": extra}

    trader = types.SimpleNamespace(
        _is_paper_mode=lambda: False,
        is_connected=True,
        upbit=MagicMock(),
        order_service=svc,
        _reserved_krw_by_ticker={},
        _active_session_id=1,
        _order_error_log_ts={},
        _manual_review_queue={},
        _orphan_events=[],
        _ops_alert_last_ts={},
        _api_last_call_ts=0.0,
        _api_last_call_ts_by_group={},
        _risk_snapshot_cache={"ts": 0.0, "value": None},
        _last_price_update_ts=0.0,
        _price_feed_recovery_attempted=False,
        _twap_buy_plans={},
        _reconciliation_dirty=False,
        _manual_review_row_keys=[],
        log=lambda msg: logs.append(msg),
        logger=MagicMock(),
        _manual_review_on_timeout=lambda: True,
        _transition_pending=lambda *args, **kwargs: True,
        _api_get_open_orders=MagicMock(return_value=[
            {"uuid": "exchange-open-uuid-1", "market": "KRW-BTC", "side": "bid", "state": "wait"}
        ]),
    )

    with patch("upbit_autotrader.controllers.trading_parts.lifecycle_ops._register_manual_review", side_effect=lambda s, t, u, r, **k: mock_register_mr(s, t, u, r, **k)):
        recovered = _recover_exchange_open_orders(trader)
        assert recovered == 1
        assert "exchange-open-uuid-1" in manual_reviews
        assert manual_reviews["exchange-open-uuid-1"]["ticker"] == "KRW-BTC"
