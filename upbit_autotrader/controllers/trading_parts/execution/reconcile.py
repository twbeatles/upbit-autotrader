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



def _reconcile_terminal_pending(self, ticker, pending):
    side = str((pending or {}).get("side", "")).upper()
    uuid = (pending or {}).get("uuid")
    active_session = getattr(self, "_active_session_id", 0)
    clear_pending_if_uuid = getattr(getattr(self, "order_service", None), "clear_pending_if_uuid", None)
    release_reserved = getattr(self, "_release_reserved_krw", None)
    if side == "BUY":
        if ticker in getattr(self, "universe", {}):
            self.check_buy_execution(ticker, uuid, retry_count=0, session_id=active_session)
        else:
            external_buy = getattr(self, "_check_external_buy_execution", None)
            if callable(external_buy):
                external_buy(
                    ticker,
                    uuid,
                    reason=str((pending or {}).get("source", "외부매수")),
                    retry_count=0,
                    session_id=active_session,
                )
            else:
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                elif hasattr(self, "order_service"):
                    self.order_service.clear_pending(ticker)
                if callable(release_reserved):
                    release_reserved(ticker)
        return
    if side == "PARTIAL_SELL":
        qty = float((pending or {}).get("requested_qty", 0.0) or 0.0)
        reason = str((pending or {}).get("sell_reason", "분할익절"))
        level = (pending or {}).get("partial_level")
        self._check_partial_sell_execution(
            ticker,
            uuid,
            qty,
            reason,
            level=level,
            retry_count=0,
            session_id=active_session,
        )
        return
    if ticker in getattr(self, "universe", {}) and float(self.universe.get(ticker, {}).get("qty", 0.0) or 0.0) > 0:
        reason = str((pending or {}).get("sell_reason", "재정합"))
        self.check_sell_execution(ticker, uuid, reason, retry_count=0, session_id=active_session)
        return
    external_sell = getattr(self, "_check_external_sell_execution", None)
    if callable(external_sell):
        external_sell(
            ticker,
            uuid,
            reason=str((pending or {}).get("sell_reason", "외부매도")),
            context_label=str((pending or {}).get("context_label", "외부 매도")),
            retry_count=0,
            session_id=active_session,
        )
    else:
        if callable(clear_pending_if_uuid):
            clear_pending_if_uuid(ticker, uuid)
        elif hasattr(self, "order_service"):
            self.order_service.clear_pending(ticker)


def _resolve_timeout_pending(self, ticker, pending, reason):
    uuid = (pending or {}).get("uuid")
    side = str((pending or {}).get("side", "")).upper()
    transition_pending = getattr(self, "_transition_pending", None)
    ops_alert = getattr(self, "_ops_alert", None)
    register_manual_review = getattr(self, "_register_manual_review", None)
    cancel_order = getattr(self, "_api_cancel_order", None)
    safe_get_order = getattr(self, "_safe_get_order", None)
    clear_pending_if_uuid = getattr(getattr(self, "order_service", None), "clear_pending_if_uuid", None)
    clear_pending = getattr(getattr(self, "order_service", None), "clear_pending", None)

    if callable(transition_pending):
        transition_pending(ticker, "timeout", reason=reason, metadata={"uuid": uuid, "side": side})
    if callable(ops_alert):
        ops_alert(
            level="warning",
            message=f"⚠️ [{ticker}] 주문 타임아웃 감지 - 취소/재조회 시도",
            key=f"timeout:{uuid}",
            cooldown=15,
        )
    if callable(cancel_order):
        cancel_order(uuid)
    order_raw = safe_get_order(uuid) if callable(safe_get_order) else None
    order = order_raw if isinstance(order_raw, dict) else None
    state = str((order or {}).get("state", "")).lower()
    if state in ("done", "cancel"):
        if callable(transition_pending):
            transition_pending(ticker, state, reason="timeout_requery_terminal", metadata={"uuid": uuid})
        _reconcile_terminal_pending(self, ticker, pending)
        return True
    if callable(register_manual_review):
        register_manual_review(ticker, uuid, reason=reason, order=order, extra={"side": side})
    else:
        if callable(clear_pending_if_uuid):
            clear_pending_if_uuid(ticker, uuid)
        elif callable(clear_pending):
            clear_pending(ticker)
    return False


def _reconcile_pending_orders(self, force=False):
    self._ensure_order_stability_state()
    if not hasattr(self, "order_service"):
        return
    if not self._is_paper_mode() and not getattr(self, "upbit", None):
        return
    now = datetime.datetime.now()
    stale_timeout = float(getattr(Config, "PENDING_STALE_TIMEOUT_SEC", 90))
    if hasattr(self.order_service, "list_pending"):
        pending_items = self.order_service.list_pending().items()
    else:
        pending_items = getattr(self, "pending_orders", {}).items()
    for ticker, pending in list(pending_items):
        uuid = pending.get("uuid")
        requested_at = pending.get("requested_at")
        if not isinstance(requested_at, datetime.datetime):
            requested_at = now
        age_sec = max(0.0, (now - requested_at).total_seconds())
        order = self._safe_get_order(uuid)
        prev_retry = int((pending or {}).get("retry_count", 0) or 0)
        self.order_service.update_pending(ticker, last_checked_at=now, retry_count=prev_retry + 1)
        if not order:
            missing_order_count = int((pending or {}).get("missing_order_count", 0) or 0) + 1
            self.order_service.update_pending(ticker, missing_order_count=missing_order_count)
            min_retry_threshold = max(3, int(getattr(Config, "API_MAX_RETRIES", 3)))
            should_escalate = age_sec >= stale_timeout and (force or missing_order_count >= min_retry_threshold)
            if should_escalate:
                latest_pending = self.order_service.get_pending(ticker) or pending
                _resolve_timeout_pending(self, ticker=ticker, pending=latest_pending, reason="reconcile_missing_exchange_state")
            continue
        self.order_service.update_pending(ticker, missing_order_count=0)
        state = str(order.get("state", "")).lower()
        if state in ("wait",):
            self._transition_pending(ticker, "wait", reason="reconcile_wait", metadata={"age_sec": age_sec})
            if force and age_sec >= stale_timeout:
                _resolve_timeout_pending(self, ticker, pending, reason="force_reconcile_timeout")
            continue
        if state in ("done", "cancel"):
            self._transition_pending(ticker, state, reason="reconcile_terminal", metadata={"age_sec": age_sec})
            _reconcile_terminal_pending(self, ticker, pending)
            continue
        if force and age_sec >= stale_timeout:
            _resolve_timeout_pending(self, ticker, pending, reason="reconcile_unknown_state_timeout")
    self._sync_reserved_with_pending()
    self._mark_reconciliation_dirty()
