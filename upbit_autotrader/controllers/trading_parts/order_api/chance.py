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



def _fee_rate_to_bps(value, default_bps=5.0):
    try:
        fee = float(value)
    except (TypeError, ValueError):
        return float(default_bps)
    if fee <= 0:
        return float(default_bps)
    return fee * 10000.0 if fee < 1.0 else fee


def _extract_chance_fee_bps(chance, default_bps=5.0):
    if not isinstance(chance, dict):
        return float(default_bps), float(default_bps)
    return (
        _fee_rate_to_bps(chance.get("bid_fee"), default_bps),
        _fee_rate_to_bps(chance.get("ask_fee"), default_bps),
    )


def _extract_chance_all_fees_bps(chance, default_bps=5.0):
    """Extract (taker_bid_bps, taker_ask_bps, maker_bid_bps, maker_ask_bps) from orders/chance."""
    if not isinstance(chance, dict):
        d = float(default_bps)
        return d, d, d, d
    bid_fee = _fee_rate_to_bps(chance.get("bid_fee"), default_bps)
    ask_fee = _fee_rate_to_bps(chance.get("ask_fee"), default_bps)
    maker_bid_fee = _fee_rate_to_bps(chance.get("maker_bid_fee", chance.get("bid_fee")), default_bps)
    maker_ask_fee = _fee_rate_to_bps(chance.get("maker_ask_fee", chance.get("ask_fee")), default_bps)
    return bid_fee, ask_fee, maker_bid_fee, maker_ask_fee


from .retry import _resolve_api_rate_group as _resolve_api_rate_group
from .retry import _safe_log_order_error as _safe_log_order_error
from .retry import api_call_with_retry as api_call_with_retry


def _api_get_order_chance(self, ticker):
    if not ticker:
        return None
    if self._is_paper_mode():
        market_price = float(self._resolve_market_price(ticker) or 0.0)
        krw_balance = float(self._api_get_balance("KRW") or 0.0)
        balances = self._api_get_balances() or []
        ask_balance = 0.0
        for item in balances:
            currency = str((item or {}).get("currency", "")).upper()
            if currency == str(ticker).replace("KRW-", "").upper():
                try:
                    ask_balance = float((item or {}).get("balance", 0.0) or 0.0)
                except Exception:
                    ask_balance = 0.0
                break
        return {
            "bid_fee": "0.0005",
            "ask_fee": "0.0005",
            "market": {
                "id": ticker,
                "state": "active",
                "bid_types": ["price", "limit"],
                "ask_types": ["market", "limit"],
                "bid": {"currency": "KRW", "min_total": "5000"},
                "ask": {"currency": ticker.replace("KRW-", ""), "min_total": "5000"},
            },
            "bid_account": {"currency": "KRW", "balance": str(krw_balance)},
            "ask_account": {"currency": ticker.replace("KRW-", ""), "balance": str(ask_balance)},
            "reference_price": market_price,
        }
    if not getattr(self, "upbit", None):
        return None
    chance_fn = getattr(self.upbit, "get_chance", None)
    if not callable(chance_fn):
        return None
    try:
        return api_call_with_retry(
            self,
            chance_fn,
            ticker,
            operation_name=f"get_chance:{ticker}",
            rate_group="exchange_default",
        )
    except Exception as e:
        _safe_log_order_error(self, ticker, f"주문 가능 정보 조회 실패 ({ticker}): {e}")
        return None


def _api_get_orderbook(self, markets, count=None):
    """GET /v1/orderbook - 호가 정보 조회."""
    if not getattr(self, "upbit", None):
        return []
    fn = getattr(self.upbit, "get_orderbook", None)
    if not callable(fn):
        return []
    try:
        kwargs = {"count": count} if count is not None else {}
        return list(
            api_call_with_retry(
                self,
                fn,
                markets,
                operation_name="get_orderbook",
                rate_group="quotation_orderbook",
                **kwargs,
            )
            or []
        )
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"호가 정보 조회 실패: {e}")
        return []


def _api_get_orderbook_instruments(self, markets=None):
    """GET /v1/orderbook/instruments - 호가 정책 및 tick_size 조회."""
    if not getattr(self, "upbit", None):
        return []
    fn = getattr(self.upbit, "get_orderbook_instruments", None)
    if not callable(fn):
        return []
    try:
        return list(
            api_call_with_retry(
                self,
                fn,
                markets=markets,
                operation_name="get_orderbook_instruments",
                rate_group="quotation_orderbook",
            )
            or []
        )
    except Exception as e:
        if hasattr(self, "logger"):
            self.logger.warning(f"호가 정책 조회 실패: {e}")
        return []
