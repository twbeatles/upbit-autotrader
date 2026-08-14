"""Tests for orderbook spread and depth guard."""

import pytest
from upbit_autotrader.execution.orderbook_guard import analyze_orderbook_depth


def test_orderbook_spread_and_depth_guard():
    orderbook = {
        "market": "KRW-BTC",
        "orderbook_units": [
            {"ask_price": 100100.0, "bid_price": 100000.0, "ask_size": 1.0, "bid_size": 1.0},
            {"ask_price": 100200.0, "bid_price": 99900.0, "ask_size": 2.0, "bid_size": 2.0},
            {"ask_price": 100300.0, "bid_price": 99800.0, "ask_size": 3.0, "bid_size": 3.0},
        ],
    }

    # Small order (fits in first ask level)
    res_small = analyze_orderbook_depth(orderbook, notional_krw=50000.0, side="BUY")
    assert res_small.is_safe is True
    assert res_small.estimated_fill_price == 100100.0
    assert res_small.estimated_slippage_bps == 0.0

    # Multi-level order (spans 1st and 2nd ask levels)
    # Level 1 has 100,100 KRW, Level 2 has 200,400 KRW
    res_multi = analyze_orderbook_depth(orderbook, notional_krw=200000.0, side="BUY")
    assert res_multi.is_safe is True
    assert res_multi.estimated_fill_price > 100100.0

    # Order larger than total depth (3 levels = ~600,000 KRW)
    res_overflow = analyze_orderbook_depth(orderbook, notional_krw=2000000.0, side="BUY")
    assert res_overflow.is_safe is False
    assert "호가 깊이 부족" in res_overflow.reason
    assert res_overflow.recommended_slices > 1


def test_orderbook_excessive_spread():
    # 5% spread
    orderbook = {
        "market": "KRW-ALT",
        "orderbook_units": [
            {"ask_price": 105.0, "bid_price": 100.0, "ask_size": 100.0, "bid_size": 100.0},
        ],
    }
    res = analyze_orderbook_depth(orderbook, notional_krw=10000.0, side="BUY", max_spread_bps=40.0)
    assert res.is_safe is False
    assert "스프레드 과다" in res.reason
