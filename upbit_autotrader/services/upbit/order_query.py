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




class UpbitOrderQueryMixin:
    """Order query responsibility (SRP)."""

    _request: Any

    def get_order(self, uuid_or_identifier: str) -> Optional[Dict[str, Any]]:
        """GET /v1/order - 단건 개별 주문 상세 조회 (uuid 또는 identifier 지원)."""
        if not uuid_or_identifier:
            return None
        val = str(uuid_or_identifier).strip()
        params = {"uuid": val} if "-" in val and len(val) == 36 else {"identifier": val}
        return self._request("GET", "/v1/order", params=params, rate_group="exchange")

    def get_orders_by_uuids(
        self,
        uuids: Optional[List[str]] = None,
        identifiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orders/uuids - 복수 주문 일괄 조회 (최대 100개, uuids[] 또는 identifiers[] 사용)."""
        params: Dict[str, Any] = {}
        if uuids:
            params["uuids[]"] = [str(u) for u in uuids if u]
        elif identifiers:
            params["identifiers[]"] = [str(i) for i in identifiers if i]
        if not params:
            return []
        res = self._request("GET", "/v1/orders/uuids", params=params, rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def get_open_orders(
        self,
        market: Optional[str] = None,
        state: str = "wait",
        page: int = 1,
        limit: int = 100,
        order_by: str = "asc",
    ) -> List[Dict[str, Any]]:
        """GET /v1/orders/open - 체결 대기 주문 목록 조회."""
        params: Dict[str, Any] = {
            "state": state,
            "page": page,
            "limit": limit,
            "order_by": order_by,
        }
        if market:
            params["market"] = str(market)
        res = self._request("GET", "/v1/orders/open", params=params, rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def get_closed_orders(
        self,
        market: Optional[str] = None,
        state: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orders/closed - 종료 주문(체결/취소) 목록 조회 (최대 7일)."""
        params: Dict[str, Any] = {"limit": limit}
        if market:
            params["market"] = str(market)
        if state:
            params["state"] = str(state)
        if start_time:
            params["start_time"] = str(start_time)
        if end_time:
            params["end_time"] = str(end_time)
        res = self._request("GET", "/v1/orders/closed", params=params, rate_group="exchange")
        return list(res) if isinstance(res, list) else []
