from __future__ import annotations

import random
import time
from typing import Any, cast

from PyQt6.QtWidgets import QMessageBox

import uuid
from upbit_autotrader.core.config import Config
from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback
from upbit_autotrader.services.rate_limit import is_rate_limit_error
from upbit_autotrader.services.upbit_client import UpbitRestClient

try:
    import pyupbit
except ImportError:
    pyupbit = pyupbit_fallback

from .retry import _safe_log_order_error, api_call_with_retry



def _api_get_order(self, uuid):
    if not uuid:
        return None
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is None:
            return None
        return svc.get_order(uuid)
    if not getattr(self, "upbit", None):
        return None
    try:
        return api_call_with_retry(
            self,
            self.upbit.get_order,
            uuid,
            operation_name=f"get_order:{uuid}",
            rate_group="exchange_default",
        )
    except Exception as e:
        _safe_log_order_error(self, uuid, f"주문 상태 조회 실패 ({uuid}): {e}")
        return None


def _api_get_balance(self, currency="KRW"):
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is None:
            return None
        if str(currency or "").upper() == "KRW":
            return float(svc.get_krw_balance())
        return 0.0
    if not getattr(self, "upbit", None):
        return None
    try:
        return api_call_with_retry(
            self,
            self.upbit.get_balance,
            currency,
            operation_name=f"get_balance:{currency}",
            rate_group="exchange_default",
        )
    except Exception:
        return None


def _api_get_balances(self):
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is None:
            return []
        holdings = svc.get_holdings()
        result = [{"currency": "KRW", "balance": str(svc.get_krw_balance())}]
        for ticker, item in holdings.items():
            result.append(
                {
                    "currency": str(ticker).replace("KRW-", ""),
                    "balance": str(item.get("qty", 0.0)),
                    "avg_buy_price": str(item.get("avg_buy_price", 0.0)),
                }
            )
        return result
    if not getattr(self, "upbit", None):
        return []
    try:
        return list(
            api_call_with_retry(
                self,
                self.upbit.get_balances,
                operation_name="get_balances",
                rate_group="exchange_default",
            )
            or []
        )
    except Exception:
        return []


def _api_get_orders_by_uuids(self, uuids=None, identifiers=None):
    """GET /v1/orders/uuids - 복수 주문 일괄 조회."""
    if not getattr(self, "upbit", None):
        return []
    fn = getattr(self.upbit, "get_orders_by_uuids", None)
    if not callable(fn):
        return []
    try:
        return list(
            api_call_with_retry(
                self,
                fn,
                uuids=uuids,
                identifiers=identifiers,
                operation_name="get_orders_by_uuids",
                rate_group="exchange_default",
            )
            or []
        )
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"복수 주문 조회 실패: {e}")
        return []


def _api_get_open_orders(self, market=None, state="wait"):
    """GET /v1/orders/open - 미체결 주문 목록 조회."""
    if not getattr(self, "upbit", None):
        return []
    fn = getattr(self.upbit, "get_open_orders", None)
    if not callable(fn):
        return []
    try:
        return list(
            api_call_with_retry(
                self,
                fn,
                market=market,
                state=state,
                operation_name="get_open_orders",
                rate_group="exchange_default",
            )
            or []
        )
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"미체결 주문 조회 실패: {e}")
        return []


def _api_get_closed_orders(self, market=None, limit=100):
    """GET /v1/orders/closed - 종료 주문 목록 조회."""
    if not getattr(self, "upbit", None):
        return []
    fn = getattr(self.upbit, "get_closed_orders", None)
    if not callable(fn):
        return []
    try:
        return list(
            api_call_with_retry(
                self,
                fn,
                market=market,
                limit=limit,
                operation_name="get_closed_orders",
                rate_group="exchange_default",
            )
            or []
        )
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"종료 주문 조회 실패: {e}")
        return []


def _safe_get_order(self, uuid):
    return _api_get_order(self, uuid)
