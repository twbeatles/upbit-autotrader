from __future__ import annotations

import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import estimate_realized_slippage_bps, plan_execution
from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker
from upbit_autotrader.controllers.trading_parts.order_api.chance import _extract_chance_fee_bps

try:
    from upbit_autotrader.notifications.notifiers import EventType
except ImportError:
    EventType = None



def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _extract_min_total(chance, side, default=0.0):
    if not isinstance(chance, dict):
        return float(default)
    market = chance.get("market")
    if not isinstance(market, dict):
        return float(default)
    policy = market.get(str(side or "").lower())
    if not isinstance(policy, dict):
        return float(default)
    return _safe_float(policy.get("min_total"), default)


def _extract_market_state(chance):
    if not isinstance(chance, dict):
        return ""
    market = chance.get("market")
    if not isinstance(market, dict):
        return ""
    return str(market.get("state", "") or "").lower()


def _supports_order_type(chance, side, order_type):
    if not isinstance(chance, dict):
        return True
    market = chance.get("market")
    if not isinstance(market, dict):
        return True
    key = "bid_types" if str(side or "").lower() == "buy" else "ask_types"
    types = market.get(key)
    if not isinstance(types, list):
        return True
    normalized = {str(v or "").lower() for v in types}
    return str(order_type or "").lower() in normalized


def _validate_live_order_request(self, ticker, side, *, notional_krw=0.0, qty=0.0, ref_price=0.0):
    if self._is_paper_mode():
        return True, "", None
    chance_getter = getattr(self, "_api_get_order_chance", None)
    if not callable(chance_getter):
        return True, "", None

    chance = chance_getter(ticker)
    if not isinstance(chance, dict):
        return True, "", None

    market_state = _extract_market_state(chance)
    if market_state and market_state != "active":
        return False, f"[{ticker}] 주문 불가 마켓 상태: {market_state}", chance

    if str(side or "").upper() == "BUY":
        if not _supports_order_type(chance, "buy", "price"):
            return False, f"[{ticker}] 업비트 주문 정책상 시장가 매수(price)를 지원하지 않습니다.", chance
        min_total = _extract_min_total(chance, "bid", 5000.0 if str(ticker).startswith("KRW-") else 0.0)
        if min_total > 0 and float(notional_krw or 0.0) + 1e-8 < min_total:
            return False, f"[{ticker}] 업비트 최소 주문금액 미만 ({min_total:,.0f})", chance
    else:
        if not _supports_order_type(chance, "sell", "market"):
            return False, f"[{ticker}] 업비트 주문 정책상 시장가 매도(market)를 지원하지 않습니다.", chance
        min_total = 5000.0 if str(ticker).startswith("KRW-") else 0.0
        est_notional = float(qty or 0.0) * max(0.0, float(ref_price or 0.0))
        if min_total > 0 and est_notional > 0 and est_notional + 1e-8 < min_total:
            return False, f"[{ticker}] 업비트 최소 주문금액 미만 추정 ({est_notional:,.0f} < {min_total:,.0f})", chance

    return True, "", chance


def _market_regime_fields_dict(value):
    if isinstance(value, dict):
        return {
            "market_regime_score": float(value.get("market_regime_score", 50.0) or 50.0),
            "market_regime_label": str(value.get("market_regime_label", "neutral") or "neutral"),
            "market_regime_ts": str(value.get("market_regime_ts", "") or ""),
        }
    return {"market_regime_score": 50.0, "market_regime_label": "neutral", "market_regime_ts": ""}


def _buy_order_has_fill(self, order):
    executed_volume, total_cost, _avg_price = self.order_service.get_buy_fill_metrics(order)
    return executed_volume > 0 and total_cost > 0


def _sell_order_has_fill(self, order):
    executed_volume, proceeds, _avg_price = self.order_service.get_sell_fill_metrics(order)
    return executed_volume > 0 and proceeds > 0
