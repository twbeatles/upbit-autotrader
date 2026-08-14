"""Tests for indicator_ops using native UpbitRestClient."""

import pandas as pd
import types
from unittest.mock import MagicMock
import pytest

from upbit_autotrader.controllers.trading_parts.indicator_parts.compute_ops import _fetch_ohlcv, calculate_target_price
from upbit_autotrader.core.config import Config


def test_fetch_ohlcv_uses_native_client_first():
    sample_df = pd.DataFrame([
        {"open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": 10.0},
        {"open": 105.0, "high": 115.0, "low": 100.0, "close": 110.0, "volume": 15.0},
    ])

    mock_client = MagicMock()
    mock_client.get_ohlcv.return_value = sample_df

    mock_trader = types.SimpleNamespace(
        upbit=mock_client,
        spin_k=types.SimpleNamespace(value=lambda: 0.5),
        logger=types.SimpleNamespace(error=lambda msg: None),
    )

    df = _fetch_ohlcv(mock_trader, "KRW-BTC", "day", 2)
    assert df is sample_df
    mock_client.get_ohlcv.assert_called_once_with("KRW-BTC", interval="day", count=2)

    target_price = calculate_target_price(mock_trader, "KRW-BTC", "day")
    # prev volatility = 110 - 95 = 15, current open = 105, k = 0.5 -> target = 105 + 7.5 = 112.5
    assert target_price == 112.5
