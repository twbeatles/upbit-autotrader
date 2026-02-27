"""Persistent store for pending/recovery runtime state."""

import datetime
import json
import os
from typing import Any, Dict


_DT_FIELDS = {"requested_at", "last_checked_at"}


def _parse_datetime(value: Any):
    if isinstance(value, datetime.datetime):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw)
    except Exception:
        return None


def _serialize_datetime(value: Any):
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return value


class ReconciliationStore:
    def __init__(self, path: str):
        self.path = str(path or "reconciliation_state.json")

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as fp:
                raw = json.load(fp)
            if not isinstance(raw, dict):
                return {}
            return self._decode(raw)
        except Exception:
            return {}

    def save(self, state: Dict[str, Any]) -> bool:
        payload = self._encode(dict(state or {}))
        tmp = f"{self.path}.tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            return True
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            return False

    def _decode(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pending_orders = payload.get("pending_orders", {})
        if isinstance(pending_orders, dict):
            for item in pending_orders.values():
                if not isinstance(item, dict):
                    continue
                for key in _DT_FIELDS:
                    if key in item:
                        dt = _parse_datetime(item.get(key))
                        if dt is not None:
                            item[key] = dt
        return {
            "pending_orders": pending_orders if isinstance(pending_orders, dict) else {},
            "manual_review_queue": payload.get("manual_review_queue", {}) if isinstance(payload.get("manual_review_queue"), dict) else {},
            "orphan_events": payload.get("orphan_events", []) if isinstance(payload.get("orphan_events"), list) else [],
            "reserved_krw_by_ticker": payload.get("reserved_krw_by_ticker", {}) if isinstance(payload.get("reserved_krw_by_ticker"), dict) else {},
            "active_session_id": int(payload.get("active_session_id", 0) or 0),
        }

    def _encode(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pending_orders = payload.get("pending_orders", {})
        if isinstance(pending_orders, dict):
            pending_out = {}
            for ticker, item in pending_orders.items():
                if not isinstance(item, dict):
                    continue
                row = dict(item)
                for key in _DT_FIELDS:
                    if key in row:
                        row[key] = _serialize_datetime(row.get(key))
                pending_out[str(ticker)] = row
        else:
            pending_out = {}

        return {
            "pending_orders": pending_out,
            "manual_review_queue": payload.get("manual_review_queue", {}),
            "orphan_events": payload.get("orphan_events", []),
            "reserved_krw_by_ticker": payload.get("reserved_krw_by_ticker", {}),
            "active_session_id": int(payload.get("active_session_id", 0) or 0),
            "saved_at": datetime.datetime.now().isoformat(),
        }

