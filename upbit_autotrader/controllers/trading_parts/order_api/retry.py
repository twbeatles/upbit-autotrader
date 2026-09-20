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



def _resolve_api_rate_group(operation_name: str) -> str:
    """Rate-group policy for api_call_with_retry (SRP: retry policy lives with retry)."""
    label = str(operation_name or "").lower()
    if "cancel_open_orders" in label:
        return "order-cancel-all"
    if any(token in label for token in ("buy_market_order", "sell_market_order", "create_order", "cancel_and_new")):
        return "order"
    if label.startswith(("get_", "cancel_order", "get_balance", "get_balances", "get_order", "get_chance", "get_pockets")):
        return "exchange_default"
    return "quotation"


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
