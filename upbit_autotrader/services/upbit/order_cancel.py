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




class UpbitOrderCancelMixin:
    """Order cancel responsibility (SRP)."""

    _request: Any

    def cancel_and_new_order(
        self,
        prev_order_uuid: Optional[str] = None,
        prev_order_identifier: Optional[str] = None,
        new_ord_type: str = "limit",
        new_price: Optional[Union[float, str]] = None,
        new_volume: Optional[Union[float, str]] = None,
        new_time_in_force: Optional[str] = None,
        new_smp_type: Optional[str] = None,
        new_identifier: Optional[str] = None,
        new_post_only: bool = False,
    ) -> Dict[str, Any]:
        """POST /v1/orders/cancel_and_new - 원자적 취소 후 재주문 (2026 신규)."""
        if not prev_order_uuid and not prev_order_identifier:
            raise ValueError("Either prev_order_uuid or prev_order_identifier must be provided.")

        body: Dict[str, Any] = {
            "new_ord_type": str(new_ord_type).lower(),
        }
        if prev_order_uuid:
            body["prev_order_uuid"] = str(prev_order_uuid)
        elif prev_order_identifier:
            body["prev_order_identifier"] = str(prev_order_identifier)

        tif = str(new_time_in_force).lower() if new_time_in_force else None
        if new_post_only:
            if new_smp_type:
                raise ValueError("new_post_only option cannot be used together with new_smp_type.")
            tif = "post_only"

        if new_price is not None:
            body["new_price"] = str(new_price)
        if new_volume is not None:
            body["new_volume"] = str(new_volume)
        if tif:
            body["new_time_in_force"] = tif
        if new_smp_type:
            body["new_smp_type"] = str(new_smp_type)
        if new_identifier:
            body["new_identifier"] = str(new_identifier)

        return self._request("POST", "/v1/orders/cancel_and_new", json_data=body, rate_group="order")

    def cancel_open_orders(
        self,
        cancel_side: Optional[str] = None,
        quote_currencies: Optional[Union[str, List[str]]] = None,
        pairs: Optional[Union[str, List[str]]] = None,
        count: Optional[int] = None,
        order_by: str = "desc",
    ) -> Dict[str, Any]:
        """DELETE /v1/orders/open - 체결 대기 주문 일괄 취소 (최대 300개, rate_group=order-cancel-all)."""
        params: Dict[str, Any] = {"order_by": order_by}
        if cancel_side:
            params["cancel_side"] = str(cancel_side).lower()
        if quote_currencies and pairs:
            raise ValueError("quote_currencies and pairs cannot be specified simultaneously.")
        if quote_currencies:
            params["quote_currencies"] = [quote_currencies] if isinstance(quote_currencies, str) else list(quote_currencies)
        elif pairs:
            params["pairs"] = [pairs] if isinstance(pairs, str) else list(pairs)
        if count is not None:
            params["count"] = max(1, min(300, int(count)))

        return self._request("DELETE", "/v1/orders/open", params=params, rate_group="order-cancel-all")

    def cancel_orders_by_uuids(
        self,
        uuids: Optional[List[str]] = None,
        identifiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """DELETE /v1/orders/uuids - 복수 주문 일괄 취소 (최대 20개)."""
        params: Dict[str, Any] = {}
        if uuids:
            params["uuids[]"] = [str(u) for u in uuids if u]
        elif identifiers:
            params["identifiers[]"] = [str(i) for i in identifiers if i]
        if not params:
            return []
        res = self._request("DELETE", "/v1/orders/uuids", params=params, rate_group="order")
        return list(res) if isinstance(res, list) else []

    def cancel_order(self, uuid_or_identifier: str) -> Optional[Dict[str, Any]]:
        """DELETE /v1/order - 주문 취소."""
        if not uuid_or_identifier:
            return None
        val = str(uuid_or_identifier).strip()
        params = {"uuid": val} if "-" in val and len(val) == 36 else {"identifier": val}
        return self._request("DELETE", "/v1/order", params=params, rate_group="order")
