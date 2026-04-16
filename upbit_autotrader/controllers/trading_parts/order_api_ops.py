from __future__ import annotations

import random
import time
from typing import Any, cast

from PyQt6.QtWidgets import QMessageBox

from upbit_autotrader.core.config import Config

try:
    import pyupbit
except ImportError:
    pyupbit = cast(Any, None)


def login(self):
    """업비트 API 연결"""
    access = self.input_access.text().strip()
    secret = self.input_secret.text().strip()
    if not access or not secret:
        QMessageBox.warning(self, "경고", "API Access Key와 Secret Key를 입력해주세요.")
        return

    self.log("🔄 업비트 API 연결 시도 중...")
    self.lbl_connection.setText("● 연결 중...")
    self.lbl_connection.setStyleSheet("color: #ffc107; font-weight: bold;")

    try:
        self.upbit = pyupbit.Upbit(access, secret)
        balance = self._api_get_balance("KRW")
        if balance is None:
            raise Exception("잔고 조회 실패")

        self.is_connected = True
        self.balance = float(balance)
        self.initial_balance = float(balance)
        self._paper_seeded = False
        self._seed_paper_balance_once()
        self.lbl_balance.setText(f"💰 주문가능금액: {float(balance):,.0f} 원")
        self.lbl_connection.setText("● 연결됨")
        self.lbl_connection.setStyleSheet("color: #00b894; font-weight: bold;")
        if hasattr(self, "refresh_trade_action_buttons"):
            self.refresh_trade_action_buttons()
        self.log(f"✅ 업비트 API 연결 성공 (잔고: {float(balance):,.0f}원)")
        self.logger.info(f"API 연결 성공, 잔고: {float(balance):,.0f}원")
    except Exception as e:
        self.is_connected = False
        self.lbl_connection.setText("● 연결 실패")
        self.lbl_connection.setStyleSheet("color: #e63946; font-weight: bold;")
        self.log(f"❌ API 연결 실패: {e}")
        self.logger.error(f"API 연결 실패: {e}")
        if hasattr(self, "refresh_trade_action_buttons"):
            self.refresh_trade_action_buttons()
        QMessageBox.critical(self, "오류", f"API 연결에 실패했습니다.\n{e}")


def _place_buy_order(self, ticker, krw_amount, session_id=0, source="auto_buy"):
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
            )
            self._transition_pending(ticker, "wait", reason="buy_order_submitted")
            self._mark_reconciliation_dirty()
        return ok, result, err_msg
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."
    result = self._api_buy_market_order(ticker, krw_amount)
    if result and "uuid" in result:
        self.order_service.mark_pending(
            ticker,
            "BUY",
            result["uuid"],
            session_id=session_id,
            source=source,
            reserved_krw=krw_amount,
        )
        self._transition_pending(ticker, "wait", reason="buy_order_submitted")
        self._mark_reconciliation_dirty()
        return True, result, ""
    return False, result, "매수 주문 응답이 비정상입니다."


def _place_sell_order(self, ticker, qty, side="SELL", session_id=0, source="auto_sell"):
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
            )
            self._transition_pending(ticker, "wait", reason="sell_order_submitted")
            self._mark_reconciliation_dirty()
        return ok, result, err_msg
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."
    result = self._api_sell_market_order(ticker, qty)
    if result and "uuid" in result:
        self.order_service.mark_pending(
            ticker,
            side,
            result["uuid"],
            session_id=session_id,
            source=source,
        )
        self._transition_pending(ticker, "wait", reason="sell_order_submitted")
        self._mark_reconciliation_dirty()
        return True, result, ""
    return False, result, "매도 주문 응답이 비정상입니다."


def _safe_log_order_error(self, uuid, message):
    self._ensure_order_stability_state()
    now_ts = time.time()
    key = str(uuid)
    last_ts = float(self._order_error_log_ts.get(key, 0.0) or 0.0)
    if (now_ts - last_ts) < 5.0:
        return
    self._order_error_log_ts[key] = now_ts
    if hasattr(self, "logger"):
        self.logger.warning(message)


def _resolve_api_rate_group(operation_name: str) -> str:
    label = str(operation_name or "").lower()
    if any(token in label for token in ("buy_market_order", "sell_market_order", "create_order")):
        return "order"
    if label.startswith(("get_", "cancel_order", "get_balance", "get_balances", "get_order", "get_chance")):
        return "exchange_default"
    return "quotation"


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


def _api_buy_market_order(self, ticker, krw_amount):
    if self._is_paper_mode():
        return None
    if not getattr(self, "upbit", None):
        return None
    return api_call_with_retry(
        self,
        self.upbit.buy_market_order,
        ticker,
        krw_amount,
        operation_name=f"buy_market_order:{ticker}",
        rate_group="order",
    )


def _api_sell_market_order(self, ticker, qty):
    if self._is_paper_mode():
        return None
    if not getattr(self, "upbit", None):
        return None
    return api_call_with_retry(
        self,
        self.upbit.sell_market_order,
        ticker,
        qty,
        operation_name=f"sell_market_order:{ticker}",
        rate_group="order",
    )


def _safe_get_order(self, uuid):
    return _api_get_order(self, uuid)


def api_call_with_retry(self, func, *args, max_retries=None, delay=None, operation_name="", rate_group="", **kwargs):
    """중앙 API 재시도/백오프/레이트리밋 래퍼."""
    self._ensure_order_stability_state()
    max_retries = int(max_retries or getattr(Config, "API_MAX_RETRIES", 3))
    base_delay = float(delay if delay is not None else getattr(Config, "API_BACKOFF_BASE_SEC", Config.API_RETRY_DELAY))
    group = str(rate_group or _resolve_api_rate_group(operation_name))
    intervals = dict(getattr(Config, "API_MIN_INTERVAL_BY_GROUP_SEC", {}) or {})
    min_interval = float(intervals.get(group, getattr(Config, "API_MIN_INTERVAL_SEC", 0.0)) or 0.0)
    jitter_max = float(getattr(Config, "API_BACKOFF_JITTER_SEC", 0.0))
    last_call_by_group = getattr(self, "_api_last_call_ts_by_group", None)
    if not isinstance(last_call_by_group, dict):
        last_call_by_group = {}
        self._api_last_call_ts_by_group = last_call_by_group

    last_error = None
    for attempt in range(max_retries):
        try:
            last_group_ts = float(last_call_by_group.get(group, 0.0) or 0.0)
            wait_sec = max(0.0, min_interval - (time.time() - last_group_ts))
            if wait_sec > 0:
                time.sleep(wait_sec)
            result = func(*args, **kwargs)
            now_ts = time.time()
            self._api_last_call_ts = now_ts
            last_call_by_group[group] = now_ts
            return result
        except Exception as e:
            last_error = e
            if attempt >= max_retries - 1:
                break
            sleep_sec = base_delay * (2 ** attempt)
            if jitter_max > 0:
                sleep_sec += random.uniform(0.0, jitter_max)
            if hasattr(self, "logger"):
                label = operation_name or getattr(func, "__name__", "api_call")
                self.logger.warning(f"API 호출 실패 ({label}) 시도 {attempt + 1}/{max_retries}: {e}")
            time.sleep(max(0.0, sleep_sec))
    if hasattr(self, "logger"):
        label = operation_name or getattr(func, "__name__", "api_call")
        self.logger.error(f"API 호출 최종 실패 ({label}): {last_error}")
    if isinstance(last_error, BaseException):
        raise last_error
    raise RuntimeError(f"API 호출 최종 실패: {operation_name or getattr(func, '__name__', 'api_call')}")
