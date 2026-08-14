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
        self._ensure_order_stability_state()
        use_native = getattr(Config, "DEFAULT_USE_NATIVE_UPBIT_CLIENT", True)
        if use_native:
            rate_state = getattr(self, "_rate_limit_state", None)
            self.upbit = UpbitRestClient(access, secret, rate_limit_state=rate_state)
        elif pyupbit is not None and pyupbit is not pyupbit_fallback:
            self.upbit = pyupbit.Upbit(access, secret)
        else:
            self.upbit = UpbitRestClient(access, secret)

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
            rate_state = getattr(self, "_rate_limit_state", None)
            if rate_state is not None and hasattr(rate_state, "wait_before_call"):
                rate_state.wait_before_call(group, default_interval=min_interval)
            last_group_ts = float(last_call_by_group.get(group, 0.0) or 0.0)
            wait_sec = max(0.0, min_interval - (time.time() - last_group_ts))
            if wait_sec > 0:
                time.sleep(wait_sec)
            result = func(*args, **kwargs)
            now_ts = time.time()
            self._api_last_call_ts = now_ts
            last_call_by_group[group] = now_ts
            if rate_state is not None and hasattr(rate_state, "mark_call"):
                rate_state.mark_call(group)
            return result
        except Exception as e:
            last_error = e
            if is_rate_limit_error(e):
                rate_state = getattr(self, "_rate_limit_state", None)
                if rate_state is not None and hasattr(rate_state, "penalize"):
                    rate_state.penalize(group, seconds=base_delay * (2 ** attempt) + 1.0)
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
