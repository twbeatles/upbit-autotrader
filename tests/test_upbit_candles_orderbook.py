"""Tests for Upbit native candles, orderbook and instruments APIs."""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from upbit_autotrader.services.upbit_client import UpbitRestClient


def test_get_candles_and_ohlcv():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=quotation_candle; min=600; sec=10"}
    mock_resp.json.return_value = [
        {
            "candle_date_time_kst": "2026-08-14T09:00:00",
            "opening_price": 95000000.0,
            "high_price": 96000000.0,
            "low_price": 94500000.0,
            "trade_price": 95500000.0,
            "candle_acc_trade_volume": 12.5,
            "candle_acc_trade_price": 1193750000.0,
        },
        {
            "candle_date_time_kst": "2026-08-13T09:00:00",
            "opening_price": 94000000.0,
            "high_price": 95500000.0,
            "low_price": 93500000.0,
            "trade_price": 95000000.0,
            "candle_acc_trade_volume": 10.0,
            "candle_acc_trade_price": 945000000.0,
        },
    ]

    with patch.object(client.session, "get", return_value=mock_resp):
        df = client.get_ohlcv("KRW-BTC", interval="day", count=2)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "open" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        assert df["close"].iloc[-1] == 95500000.0


def test_get_orderbook_and_instruments():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.headers = {"Remaining-Req": "group=quotation_orderbook; min=600; sec=10"}
    mock_resp.json.return_value = [
        {
            "market": "KRW-BTC",
            "total_ask_size": 5.0,
            "total_bid_size": 4.5,
            "orderbook_units": [
                {"ask_price": 95010000.0, "bid_price": 95000000.0, "ask_size": 1.2, "bid_size": 0.8},
            ],
        }
    ]

    with patch.object(client.session, "get", return_value=mock_resp):
        ob = client.get_orderbook("KRW-BTC", count=5)
        assert len(ob) == 1
        assert ob[0]["market"] == "KRW-BTC"
        assert ob[0]["orderbook_units"][0]["ask_price"] == 95010000.0

    # Instruments
    mock_resp.json.return_value = [
        {"market": "KRW-BTC", "tick_size": 1000.0, "supported_levels": [1000.0, 5000.0]}
    ]
    with patch.object(client.session, "get", return_value=mock_resp):
        inst = client.get_orderbook_instruments(["KRW-BTC"])
        assert len(inst) == 1
        assert inst[0]["tick_size"] == 1000.0


def test_best_orders():
    client = UpbitRestClient("fake_access_key", "fake_secret_key_32_bytes_long_minimum!!")
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 201
    mock_resp.headers = {"Remaining-Req": "group=order; min=200; sec=8"}
    mock_resp.json.return_value = {"uuid": "best-uuid-1", "ord_type": "best", "state": "wait"}

    with patch.object(client.session, "post", return_value=mock_resp) as mock_post:
        res = client.buy_best_order("KRW-BTC", 100000, identifier="best-1", time_in_force="ioc")
        assert res["uuid"] == "best-uuid-1"
        payload = mock_post.call_args[1]["json"]
        assert payload["ord_type"] == "best"
        assert payload["time_in_force"] == "ioc"
        assert payload["side"] == "bid"
