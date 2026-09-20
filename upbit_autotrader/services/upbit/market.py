"""
Native Upbit REST API client with JWT authentication and pocket-based rate limiting.
Follows the official Upbit Open API specifications (2026).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional, Union

import jwt
import requests

from upbit_autotrader.core.config import Config
from upbit_autotrader.services.rate_limit import RateLimitState, is_rate_limit_error

logger = logging.getLogger(__name__)



class UpbitMarketMixin:
    """Market data (ticker/orderbook/candles) responsibility (SRP)."""

    _request: Any

    def get_market_all(self, is_details: bool = False) -> List[Dict[str, Any]]:
        """GET /v1/market/all - 전체 종목 목록 조회."""
        params = {"isDetails": "true" if is_details else "false"}
        res = self._request("GET", "/v1/market/all", params=params, rate_group="quotation", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_current_price(
        self,
        ticker_or_tickers: Union[str, List[str]],
    ) -> Union[float, Dict[str, float], None]:
        """GET /v1/ticker - 현재가 조회 (단일 티커 float 또는 멀티 티커 dict 반환)."""
        if not ticker_or_tickers:
            return None

        if isinstance(ticker_or_tickers, list):
            markets = ",".join([str(t).strip() for t in ticker_or_tickers if t])
            is_single = len(ticker_or_tickers) == 1
        else:
            markets = str(ticker_or_tickers).strip()
            is_single = True

        if not markets:
            return None

        res = self._request(
            "GET",
            "/v1/ticker",
            params={"markets": markets},
            rate_group="quotation_ticker",
            auth=False,
        )
        if not isinstance(res, list) or not res:
            return None

        if is_single and len(res) == 1:
            try:
                return float(res[0].get("trade_price", 0.0) or 0.0)
            except (TypeError, ValueError):
                return 0.0

        price_map: Dict[str, float] = {}
        for row in res:
            market = str(row.get("market") or "")
            try:
                price_map[market] = float(row.get("trade_price", 0.0) or 0.0)
            except (TypeError, ValueError):
                price_map[market] = 0.0
        return price_map

    def get_orderbook(
        self,
        markets: Union[str, List[str]],
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orderbook - 호가 정보 조회."""
        if not markets:
            return []
        market_str = ",".join(markets) if isinstance(markets, list) else str(markets).strip()
        params: Dict[str, Any] = {"markets": market_str}
        if count is not None:
            params["count"] = int(count)
        res = self._request("GET", "/v1/orderbook", params=params, rate_group="quotation_orderbook", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_orderbook_instruments(
        self,
        markets: Optional[Union[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orderbook/instruments - 종목별 호가 정책 및 tick_size 조회."""
        params: Dict[str, Any] = {}
        if markets:
            params["markets"] = ",".join(markets) if isinstance(markets, list) else str(markets).strip()
        res = self._request("GET", "/v1/orderbook/instruments", params=params, rate_group="quotation_orderbook", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_minutes(
        self,
        market: str,
        unit: int = 240,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/minutes/{unit} - 분 캔들 조회."""
        valid_units = {1, 3, 5, 10, 15, 30, 60, 240}
        u = unit if unit in valid_units else 240
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", f"/v1/candles/minutes/{u}", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_days(
        self,
        market: str,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/days - 일 캔들 조회."""
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", "/v1/candles/days", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_weeks(
        self,
        market: str,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/weeks - 주 캔들 조회."""
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", "/v1/candles/weeks", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_months(
        self,
        market: str,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/months - 월 캔들 조회."""
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", "/v1/candles/months", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_ohlcv(
        self,
        ticker: str,
        interval: str = "day",
        count: int = 200,
        to: Optional[str] = None,
    ) -> Any:
        """
        Fetch OHLCV historical candle data as a pandas DataFrame.
        Compatible with pyupbit.get_ohlcv output format.
        """
        import pandas as pd

        ticker_str = str(ticker or "").strip()
        if not ticker_str:
            return pd.DataFrame()

        interval_str = str(interval or "day").strip().lower()
        if interval_str.startswith("minute"):
            try:
                unit = int(interval_str.replace("minute", "") or 1)
            except ValueError:
                unit = 1
            raw_candles = self.get_candles_minutes(ticker_str, unit=unit, count=count, to=to)
        elif interval_str in ("week", "weeks"):
            raw_candles = self.get_candles_weeks(ticker_str, count=count, to=to)
        elif interval_str in ("month", "months"):
            raw_candles = self.get_candles_months(ticker_str, count=count, to=to)
        else:
            raw_candles = self.get_candles_days(ticker_str, count=count, to=to)

        if not raw_candles:
            return pd.DataFrame()

        records = []
        for c in reversed(raw_candles):
            if not isinstance(c, dict):
                continue
            dt_str = c.get("candle_date_time_kst") or c.get("candle_date_time_utc")
            records.append({
                "datetime": dt_str,
                "open": float(c.get("opening_price", 0.0) or 0.0),
                "high": float(c.get("high_price", 0.0) or 0.0),
                "low": float(c.get("low_price", 0.0) or 0.0),
                "close": float(c.get("trade_price", 0.0) or 0.0),
                "volume": float(c.get("candle_acc_trade_volume", 0.0) or 0.0),
                "value": float(c.get("candle_acc_trade_price", 0.0) or 0.0),
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df
