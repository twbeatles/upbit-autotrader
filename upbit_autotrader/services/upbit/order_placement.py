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




class UpbitOrderPlacementMixin:
    """Order placement responsibility (SRP)."""

    _request: Any

    def create_order(
        self,
        market: str,
        side: str,
        volume: Optional[Union[float, str]] = None,
        price: Optional[Union[float, str]] = None,
        ord_type: str = "limit",
        identifier: Optional[str] = None,
        time_in_force: Optional[str] = None,
        smp_type: Optional[str] = None,
        post_only: bool = False,
    ) -> Dict[str, Any]:
        """POST /v1/orders - 주문 생성 (업비트 OpenAPI 2026 스펙 준수)."""
        ot = str(ord_type).lower()
        sd = str(side).lower()
        body: Dict[str, Any] = {
            "market": str(market),
            "side": sd,
            "ord_type": ot,
        }

        # post_only 및 smp_type 상호 배타성 검증 (업비트 공식 규칙)
        tif = str(time_in_force).lower() if time_in_force else None
        if post_only:
            if smp_type:
                raise ValueError("post_only option cannot be used together with smp_type.")
            tif = "post_only"

        # ord_type별 파라미터 제약 준수
        if ot == "price":
            # 시장가 매수: price 필수, volume 금지
            if price is not None:
                body["price"] = str(price)
        elif ot == "market":
            # 시장가 매도: volume 필수, price 금지
            if volume is not None:
                body["volume"] = str(volume)
        elif ot == "best":
            # 최유리 지정가: time_in_force 필수 (ioc 또는 fok)
            if price is not None and sd == "bid":
                body["price"] = str(price)
            if volume is not None:
                body["volume"] = str(volume)
            body["time_in_force"] = str(tif or "ioc").lower()
        else:
            # 지정가 (limit)
            if volume is not None:
                body["volume"] = str(volume)
            if price is not None:
                body["price"] = str(price)
            if tif:
                body["time_in_force"] = tif

        if identifier:
            body["identifier"] = str(identifier).strip()
        if smp_type:
            body["smp_type"] = str(smp_type)

        return self._request("POST", "/v1/orders", json_data=body, rate_group="order")

    def buy_market_order(
        self,
        ticker: str,
        price: Union[float, str],
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """시장가 매수 (ord_type='price', price=주문원화총액) - pyupbit 호환."""
        return self.create_order(
            market=ticker,
            side="bid",
            price=price,
            ord_type="price",
            identifier=identifier,
        )

    def sell_market_order(
        self,
        ticker: str,
        volume: Union[float, str],
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """시장가 매도 (ord_type='market', volume=주문수량) - pyupbit 호환."""
        return self.create_order(
            market=ticker,
            side="ask",
            volume=volume,
            ord_type="market",
            identifier=identifier,
        )

    def buy_limit_order(
        self,
        ticker: str,
        price: Union[float, str],
        volume: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict[str, Any]:
        """지정가 매수."""
        return self.create_order(
            market=ticker,
            side="bid",
            price=price,
            volume=volume,
            ord_type="limit",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def sell_limit_order(
        self,
        ticker: str,
        price: Union[float, str],
        volume: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict[str, Any]:
        """지정가 매도."""
        return self.create_order(
            market=ticker,
            side="ask",
            price=price,
            volume=volume,
            ord_type="limit",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def buy_best_order(
        self,
        ticker: str,
        price: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: str = "ioc",
    ) -> Dict[str, Any]:
        """최유리 지정가 매수 (ord_type='best', time_in_force 필수)."""
        return self.create_order(
            market=ticker,
            side="bid",
            price=price,
            ord_type="best",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def sell_best_order(
        self,
        ticker: str,
        volume: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: str = "ioc",
    ) -> Dict[str, Any]:
        """최유리 지정가 매도 (ord_type='best', time_in_force 필수)."""
        return self.create_order(
            market=ticker,
            side="ask",
            volume=volume,
            ord_type="best",
            identifier=identifier,
            time_in_force=time_in_force,
        )
