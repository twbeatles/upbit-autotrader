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

from .retry import api_call_with_retry



def _place_buy_order(self, ticker, krw_amount, session_id=0, source="auto_buy", identifier=""):
    client_id = str(identifier or f"buy-{uuid.uuid4().hex[:16]}")
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        self._seed_paper_balance_once()
        if svc is None:
            return False, None, "paper service unavailable"
        market_price = self._resolve_market_price(ticker)
        ok, result, err_msg = svc.place_buy_market(ticker, krw_amount, market_price)
        if ok and result and "uuid" in result:
            self.order_service.mark_pending(
                ticker,
                "BUY",
                result["uuid"],
                session_id=session_id,
                source=source,
                reserved_krw=krw_amount,
                identifier=client_id,
            )
            self._transition_pending(ticker, "wait", reason="buy_order_submitted")
            self._mark_reconciliation_dirty()
        return ok, result, err_msg
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."
    result = self._api_buy_market_order(ticker, krw_amount, identifier=client_id)
    if result and "uuid" in result:
        self.order_service.mark_pending(
            ticker,
            "BUY",
            result["uuid"],
            session_id=session_id,
            source=source,
            reserved_krw=krw_amount,
            identifier=client_id,
        )
        self._transition_pending(ticker, "wait", reason="buy_order_submitted")
        self._mark_reconciliation_dirty()
        return True, result, ""
    return False, result, "매수 주문 응답이 비정상입니다."


def _place_sell_order(self, ticker, qty, side="SELL", session_id=0, source="auto_sell", identifier=""):
    client_id = str(identifier or f"sell-{uuid.uuid4().hex[:16]}")
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is None:
            return False, None, "paper service unavailable"
        market_price = self._resolve_market_price(ticker)
        ok, result, err_msg = svc.place_sell_market(ticker, qty, market_price)
        if ok and result and "uuid" in result:
            self.order_service.mark_pending(
                ticker,
                side,
                result["uuid"],
                session_id=session_id,
                source=source,
                identifier=client_id,
            )
            self._transition_pending(ticker, "wait", reason="sell_order_submitted")
            self._mark_reconciliation_dirty()
        return ok, result, err_msg
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."
    result = self._api_sell_market_order(ticker, qty, identifier=client_id)
    if result and "uuid" in result:
        self.order_service.mark_pending(
            ticker,
            side,
            result["uuid"],
            session_id=session_id,
            source=source,
            identifier=client_id,
        )
        self._transition_pending(ticker, "wait", reason="sell_order_submitted")
        self._mark_reconciliation_dirty()
        return True, result, ""
    return False, result, "매도 주문 응답이 비정상입니다."


def _place_best_buy_order(self, ticker, krw_amount, time_in_force="ioc", session_id=0, source="auto_buy", identifier=""):
    """최유리 지정가 매수 발주."""
    client_id = str(identifier or f"best-buy-{uuid.uuid4().hex[:16]}")
    if self._is_paper_mode():
        return _place_buy_order(self, ticker, krw_amount, session_id=session_id, source=source, identifier=client_id)
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."

    fn = getattr(getattr(self, "upbit", None), "buy_best_order", None)
    if not callable(fn):
        # Fallback to market buy
        return _place_buy_order(self, ticker, krw_amount, session_id=session_id, source=source, identifier=client_id)

    result = api_call_with_retry(
        self,
        fn,
        ticker,
        krw_amount,
        identifier=client_id,
        time_in_force=time_in_force,
        operation_name=f"buy_best_order:{ticker}",
        rate_group="order",
    )
    if result and "uuid" in result:
        self.order_service.mark_pending(
            ticker,
            "BUY",
            result["uuid"],
            session_id=session_id,
            source=source,
            reserved_krw=krw_amount,
            identifier=client_id,
        )
        self._transition_pending(ticker, "wait", reason="best_buy_order_submitted")
        self._mark_reconciliation_dirty()
        return True, result, ""
    return False, result, "최유리 매수 주문 응답이 비정상입니다."


def _place_best_sell_order(self, ticker, qty, time_in_force="ioc", side="SELL", session_id=0, source="auto_sell", identifier=""):
    """최유리 지정가 매도 발주."""
    client_id = str(identifier or f"best-sell-{uuid.uuid4().hex[:16]}")
    if self._is_paper_mode():
        return _place_sell_order(self, ticker, qty, side=side, session_id=session_id, source=source, identifier=client_id)
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."

    fn = getattr(getattr(self, "upbit", None), "sell_best_order", None)
    if not callable(fn):
        # Fallback to market sell
        return _place_sell_order(self, ticker, qty, side=side, session_id=session_id, source=source, identifier=client_id)

    result = api_call_with_retry(
        self,
        fn,
        ticker,
        qty,
        identifier=client_id,
        time_in_force=time_in_force,
        operation_name=f"sell_best_order:{ticker}",
        rate_group="order",
    )
    if result and "uuid" in result:
        self.order_service.mark_pending(
            ticker,
            side,
            result["uuid"],
            session_id=session_id,
            source=source,
            identifier=client_id,
        )
        self._transition_pending(ticker, "wait", reason="best_sell_order_submitted")
        self._mark_reconciliation_dirty()
        return True, result, ""
    return False, result, "최유리 매도 주문 응답이 비정상입니다."


def _api_buy_market_order(self, ticker, krw_amount, identifier=None):
    if self._is_paper_mode():
        return None
    if not getattr(self, "upbit", None):
        return None
    fn = self.upbit.buy_market_order
    kwargs = {}
    if identifier:
        import inspect
        sig = inspect.signature(fn)
        if "identifier" in sig.parameters:
            kwargs["identifier"] = identifier
    return api_call_with_retry(
        self,
        fn,
        ticker,
        krw_amount,
        operation_name=f"buy_market_order:{ticker}",
        rate_group="order",
        **kwargs,
    )


def _api_sell_market_order(self, ticker, qty, identifier=None):
    if self._is_paper_mode():
        return None
    if not getattr(self, "upbit", None):
        return None
    fn = self.upbit.sell_market_order
    kwargs = {}
    if identifier:
        import inspect
        sig = inspect.signature(fn)
        if "identifier" in sig.parameters:
            kwargs["identifier"] = identifier
    return api_call_with_retry(
        self,
        fn,
        ticker,
        qty,
        operation_name=f"sell_market_order:{ticker}",
        rate_group="order",
        **kwargs,
    )
