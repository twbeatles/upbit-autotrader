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



def _api_cancel_order(self, uuid):
    if not uuid:
        return None
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is None:
            return None
        cancel_fn = getattr(svc, "cancel_order", None)
        if callable(cancel_fn):
            try:
                return cancel_fn(uuid)
            except Exception:
                return None
        return None
    if not getattr(self, "upbit", None):
        return None
    cancel_fn = getattr(self.upbit, "cancel_order", None)
    if not callable(cancel_fn):
        return None
    try:
        return api_call_with_retry(
            self,
            cancel_fn,
            uuid,
            operation_name=f"cancel_order:{uuid}",
            rate_group="exchange_default",
        )
    except Exception as e:
        _safe_log_order_error(self, uuid, f"주문 취소 실패 ({uuid}): {e}")
        return None


def _api_cancel_orders_by_uuids(self, uuids=None, identifiers=None):
    """DELETE /v1/orders/uuids - 복수 주문 일괄 취소."""
    if not getattr(self, "upbit", None):
        return []
    fn = getattr(self.upbit, "cancel_orders_by_uuids", None)
    if not callable(fn):
        return []
    try:
        return list(
            api_call_with_retry(
                self,
                fn,
                uuids=uuids,
                identifiers=identifiers,
                operation_name="cancel_orders_by_uuids",
                rate_group="order",
            )
            or []
        )
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"복수 주문 일괄 취소 실패: {e}")
        return []


def _api_cancel_open_orders(self, cancel_side=None, quote_currencies=None, pairs=None, count=None):
    """DELETE /v1/orders/open - 체결 대기 주문 일괄 취소 (최대 300개, rate_group=order-cancel-all)."""
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is not None and hasattr(svc, "cancel_all_orders"):
            return svc.cancel_all_orders()
        return {}
    if not getattr(self, "upbit", None):
        return {}
    fn = getattr(self.upbit, "cancel_open_orders", None)
    if not callable(fn):
        return {}
    try:
        return api_call_with_retry(
            self,
            fn,
            cancel_side=cancel_side,
            quote_currencies=quote_currencies,
            pairs=pairs,
            count=count,
            operation_name="cancel_open_orders",
            rate_group="order-cancel-all",
        ) or {}
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"체결 대기 주문 일괄 취소 실패: {e}")
        return {}


def _api_cancel_and_new_order(
    self,
    prev_order_uuid=None,
    prev_order_identifier=None,
    new_ord_type="limit",
    new_price=None,
    new_volume=None,
    new_time_in_force=None,
    new_smp_type=None,
    new_identifier=None,
    new_post_only=False,
):
    """POST /v1/orders/cancel_and_new - 원자적 취소 후 재주문 (2026 규격)."""
    if self._is_paper_mode():
        return {}
    if not getattr(self, "upbit", None):
        return {}
    fn = getattr(self.upbit, "cancel_and_new_order", None)
    if not callable(fn):
        return {}
    try:
        return api_call_with_retry(
            self,
            fn,
            prev_order_uuid=prev_order_uuid,
            prev_order_identifier=prev_order_identifier,
            new_ord_type=new_ord_type,
            new_price=new_price,
            new_volume=new_volume,
            new_time_in_force=new_time_in_force,
            new_smp_type=new_smp_type,
            new_identifier=new_identifier,
            new_post_only=new_post_only,
            operation_name="cancel_and_new_order",
            rate_group="order",
        ) or {}
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"취소 후 재주문 실패: {e}")
        return {}
