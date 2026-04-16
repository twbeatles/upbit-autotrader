from __future__ import annotations

import datetime
import json
import os
import time

from upbit_autotrader.core.config import Config
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker

try:
    from upbit_autotrader.notifications.notifiers import EventType
except ImportError:
    EventType = None


def _ensure_order_stability_state(self):
    if not hasattr(self, "_reserved_krw_by_ticker"):
        self._reserved_krw_by_ticker = {}
    if not hasattr(self, "_active_session_id"):
        self._active_session_id = 0
    if not hasattr(self, "_order_error_log_ts"):
        self._order_error_log_ts = {}
    if not hasattr(self, "_manual_review_queue"):
        self._manual_review_queue = {}
    if not hasattr(self, "_orphan_events"):
        self._orphan_events = []
    if not hasattr(self, "_ops_alert_last_ts"):
        self._ops_alert_last_ts = {}
    if not hasattr(self, "_api_last_call_ts"):
        self._api_last_call_ts = 0.0
    if not hasattr(self, "_api_last_call_ts_by_group"):
        self._api_last_call_ts_by_group = {}
    if not hasattr(self, "_risk_snapshot_cache"):
        self._risk_snapshot_cache = {"ts": 0.0, "value": None}
    if not hasattr(self, "_last_price_update_ts"):
        self._last_price_update_ts = 0.0
    if not hasattr(self, "_price_feed_recovery_attempted"):
        self._price_feed_recovery_attempted = False
    if not hasattr(self, "_twap_buy_plans"):
        self._twap_buy_plans = {}
    if not hasattr(self, "_reconciliation_dirty"):
        self._reconciliation_dirty = False
    if not hasattr(self, "_manual_review_row_keys"):
        self._manual_review_row_keys = []
    if not hasattr(self, "persist_reconciliation_state"):
        self.persist_reconciliation_state = bool(getattr(Config, "DEFAULT_PERSIST_RECONCILIATION_STATE", False))
    if not hasattr(self, "strategy_perf_tracker") or self.strategy_perf_tracker is None:
        self.strategy_perf_tracker = StrategyPerformanceTracker()
    ensure_market_regime = getattr(self, "_ensure_market_regime_state", None)
    if callable(ensure_market_regime):
        ensure_market_regime()


def _mark_reconciliation_dirty(self):
    _ensure_order_stability_state(self)
    self._reconciliation_dirty = True


def _safe_parse_iso_datetime(raw):
    try:
        return datetime.datetime.fromisoformat(str(raw or "").strip())
    except Exception:
        return None


def _emit_order_lifecycle_event(
    self,
    event_type,
    *,
    ticker="",
    uuid="",
    session_id=0,
    state_from="",
    state_to="",
    reason="",
    source="",
    metadata=None,
):
    logger = getattr(self, "logger", None)
    try:
        path = str(
            getattr(Config, "ORDER_LIFECYCLE_LOG_FILE", "logs/order_lifecycle.jsonl")
            or "logs/order_lifecycle.jsonl"
        )
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": str(event_type or ""),
            "ticker": str(ticker or ""),
            "uuid": str(uuid or ""),
            "session_id": int(session_id or 0),
            "state_from": str(state_from or ""),
            "state_to": str(state_to or ""),
            "reason": str(reason or ""),
            "source": str(source or ""),
            "metadata": dict(metadata or {}),
        }
        with open(path, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False))
            fp.write("\n")
    except Exception as exc:
        if logger is not None:
            logger.warning(f"order lifecycle 로그 저장 실패: {exc}")


def _build_reconciliation_state(self):
    _ensure_order_stability_state(self)
    pending = self.order_service.list_pending() if hasattr(self.order_service, "list_pending") else {}
    return {
        "pending_orders": pending,
        "manual_review_queue": dict(getattr(self, "_manual_review_queue", {}) or {}),
        "orphan_events": list(getattr(self, "_orphan_events", []) or []),
        "reserved_krw_by_ticker": dict(getattr(self, "_reserved_krw_by_ticker", {}) or {}),
        "active_session_id": int(getattr(self, "_active_session_id", 0) or 0),
    }


def _persist_reconciliation_state(self, force=False):
    _ensure_order_stability_state(self)
    if not bool(getattr(self, "persist_reconciliation_state", False)):
        return False
    if not force and not bool(getattr(self, "_reconciliation_dirty", False)):
        return False
    store = getattr(self, "reconciliation_store", None)
    if store is None or not hasattr(store, "save"):
        return False
    state = _build_reconciliation_state(self)
    ok = bool(store.save(state))
    if ok:
        self._reconciliation_dirty = False
    return ok


def _load_reconciliation_state(self):
    _ensure_order_stability_state(self)
    if not bool(getattr(self, "persist_reconciliation_state", False)):
        return
    store = getattr(self, "reconciliation_store", None)
    if store is None or not hasattr(store, "load"):
        return
    payload = store.load() or {}
    pending_orders = payload.get("pending_orders", {})
    if hasattr(self, "order_service") and isinstance(pending_orders, dict):
        self.order_service.pending_orders = dict(pending_orders)
        self.pending_orders = self.order_service.pending_orders
    self._manual_review_queue = dict(payload.get("manual_review_queue", {}) or {})
    self._orphan_events = list(payload.get("orphan_events", []) or [])
    self._reserved_krw_by_ticker = {
        str(k): float(v or 0.0)
        for k, v in dict(payload.get("reserved_krw_by_ticker", {}) or {}).items()
    }
    self._active_session_id = int(payload.get("active_session_id", getattr(self, "_active_session_id", 0)) or 0)
    self._reconciliation_dirty = False
    if hasattr(self, "refresh_manual_review_table"):
        self.refresh_manual_review_table()


def _persist_strategy_performance(self):
    tracker = getattr(self, "strategy_perf_tracker", None)
    if tracker is None or not hasattr(tracker, "save"):
        return False
    return bool(tracker.save(getattr(Config, "STRATEGY_PERF_FILE", "strategy_performance.json")))


def _transition_pending(self, ticker, next_state, reason="", metadata=None):
    if not hasattr(self, "order_service") or not hasattr(self.order_service, "transition_pending"):
        return False
    pending_before = self.order_service.get_pending(ticker) if hasattr(self.order_service, "get_pending") else None
    state_from = str((pending_before or {}).get("lifecycle_state", ""))
    transitioned = bool(
        self.order_service.transition_pending(
            ticker=ticker,
            next_state=next_state,
            reason=reason,
            metadata=metadata or {},
        )
    )
    if transitioned:
        pending_after = self.order_service.get_pending(ticker) if hasattr(self.order_service, "get_pending") else None
        _mark_reconciliation_dirty(self)
        _emit_order_lifecycle_event(
            self,
            "pending_transition",
            ticker=ticker,
            uuid=(pending_after or pending_before or {}).get("uuid", ""),
            session_id=(pending_after or pending_before or {}).get("session_id", 0),
            state_from=state_from,
            state_to=str(next_state or ""),
            reason=reason,
            source=(pending_after or pending_before or {}).get("source", ""),
            metadata=metadata or {},
        )
    return transitioned


def _register_manual_review(self, ticker, uuid, reason, order=None, extra=None):
    _ensure_order_stability_state(self)
    if not self._manual_review_on_timeout():
        return
    pending = self.order_service.get_pending(ticker) if hasattr(self, "order_service") else None
    if pending and hasattr(self.order_service, "update_pending"):
        self.order_service.update_pending(ticker, needs_manual_review=True)
    _transition_pending(self, ticker, "manual_review", reason=reason, metadata={"uuid": uuid})
    payload = {
        "ticker": ticker,
        "uuid": str(uuid or ""),
        "reason": reason,
        "queued_at": datetime.datetime.now().isoformat(),
        "pending": dict(pending or {}),
        "order": dict(order or {}),
        "extra": dict(extra or {}),
    }
    key = str(uuid or f"{ticker}:{payload['queued_at']}")
    self._manual_review_queue[key] = payload
    _mark_reconciliation_dirty(self)
    _emit_order_lifecycle_event(
        self,
        "manual_review_registered",
        ticker=ticker,
        uuid=uuid,
        session_id=(pending or {}).get("session_id", 0),
        state_from=str((pending or {}).get("lifecycle_state", "")),
        state_to="manual_review",
        reason=reason,
        source=(pending or {}).get("source", ""),
        metadata={"queue_key": key, "extra": dict(extra or {})},
    )
    _ops_alert(
        self,
        level="warning",
        message=f"⚠️ [{ticker}] 수동검토 큐 적재: {reason}",
        key=f"manual_review:{ticker}:{key}",
        cooldown=30,
    )
    if hasattr(self, "refresh_manual_review_table"):
        self.refresh_manual_review_table()


def _register_orphan_event(self, ticker, uuid, side, state, session_id, source):
    _ensure_order_stability_state(self)
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "ticker": ticker,
        "uuid": str(uuid or ""),
        "side": str(side or ""),
        "state": str(state or ""),
        "session_id": int(session_id or 0),
        "active_session_id": int(getattr(self, "_active_session_id", 0) or 0),
        "source": str(source or ""),
    }
    self._orphan_events.append(event)
    if len(self._orphan_events) > 500:
        self._orphan_events = self._orphan_events[-500:]
    _mark_reconciliation_dirty(self)
    _emit_order_lifecycle_event(
        self,
        "orphan_registered",
        ticker=ticker,
        uuid=uuid,
        session_id=session_id,
        state_from="",
        state_to=str(state or ""),
        reason="session_mismatch_orphan",
        source=source,
        metadata={"active_session_id": int(getattr(self, "_active_session_id", 0) or 0), "side": str(side or "")},
    )
    _ops_alert(
        self,
        level="warning",
        message=f"⚠️ [{ticker}] 세션 불일치 orphan 이벤트 감지 ({state})",
        key=f"orphan:{event['uuid']}:{event['active_session_id']}",
        cooldown=20,
    )


def _handle_session_mismatch_terminal(self, ticker, uuid, side, state, session_id, source):
    _register_orphan_event(self, ticker, uuid, side, state, session_id, source)
    if str(state or "").lower() in ("done", "cancel"):
        if hasattr(self.order_service, "clear_pending_if_uuid"):
            self.order_service.clear_pending_if_uuid(ticker, uuid)
        else:
            self.order_service.clear_pending(ticker)
        if str(side or "").upper() == "BUY":
            self._release_reserved_krw(ticker)
        self._sync_account_holdings_to_universe(account_holdings=None, include_external=True)


def _ops_alert(self, level, message, key, cooldown: float | int = 10):
    _ensure_order_stability_state(self)
    now_ts = time.time()
    cache_key = str(key or message)
    last_ts = float(self._ops_alert_last_ts.get(cache_key, 0.0) or 0.0)
    if cooldown and (now_ts - last_ts) < float(cooldown):
        return
    self._ops_alert_last_ts[cache_key] = now_ts
    if hasattr(self, "log"):
        self.log(message)
    logger = getattr(self, "logger", None)
    if logger is not None:
        level_name = str(level or "info").lower()
        if level_name == "error":
            logger.error(message)
        elif level_name == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    if hasattr(self, "send_notification"):
        try:
            self.send_notification("Upbit Pro Trader", message)
        except Exception:
            pass
    manager = getattr(self, "notification_manager", None)
    if manager is not None and EventType is not None and hasattr(manager, "notify"):
        try:
            level_name = str(level or "info").lower()
            event_type = EventType.INFO
            if level_name == "warning":
                event_type = EventType.WARNING
            elif level_name == "error":
                event_type = EventType.ERROR
            manager.notify(event_type, message)
        except Exception:
            pass


def _next_trading_session(self):
    _ensure_order_stability_state(self)
    self._active_session_id += 1
    _mark_reconciliation_dirty(self)
    return self._active_session_id
