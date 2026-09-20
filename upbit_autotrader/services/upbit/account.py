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



class UpbitAccountMixin:
    """Account/balance/chance responsibility (SRP)."""

    _request: Any

    def get_balances(self) -> List[Dict[str, Any]]:
        """GET /v1/accounts - 전체 계좌 잔고 목록 조회."""
        res = self._request("GET", "/v1/accounts", rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def get_balance(self, currency: str = "KRW") -> Optional[float]:
        """특정 통화의 주문 가능 잔고 float 반환 (pyupbit 호환)."""
        target = str(currency or "KRW").upper().replace("KRW-", "")
        balances = self.get_balances()
        for item in balances:
            if str(item.get("currency", "")).upper() == target:
                try:
                    return float(item.get("balance", 0.0) or 0.0)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def get_chance(self, ticker_or_market: str) -> Optional[Dict[str, Any]]:
        """GET /v1/orders/chance?market={market} - 주문 가능 정보 및 수수료 조회."""
        market = str(ticker_or_market or "").strip()
        if not market:
            return None
        return self._request("GET", "/v1/orders/chance", params={"market": market}, rate_group="exchange")

    def get_pockets(self) -> List[Dict[str, Any]]:
        """GET /v1/pockets - 전체 포켓(메인 및 서브포켓) 목록 조회 (2026 포켓 API)."""
        res = self._request("GET", "/v1/pockets", rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def get_sub_pocket_balance(self, pocket_id: str) -> List[Dict[str, Any]]:
        """GET /v1/pockets/{pocket_id}/balance - 특정 서브포켓 잔고 조회 (2026 포켓 API)."""
        if not pocket_id:
            return []
        res = self._request("GET", f"/v1/pockets/{pocket_id}/balance", rate_group="exchange")
        return list(res) if isinstance(res, list) else []
