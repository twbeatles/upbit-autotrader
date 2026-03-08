from __future__ import annotations

# Runtime bindings injected by trading_controller facade
Config = None
QColor = None
QMessageBox = None
QTableWidgetItem = None
datetime = None


def bind_runtime(**kwargs):
    globals().update(kwargs)



def _manual_review_age_text(self, age_sec):
    age_sec = max(0, int(age_sec or 0))
    if age_sec < 60:
        return f"{age_sec}s"
    if age_sec < 3600:
        return f"{age_sec // 60}m {age_sec % 60}s"
    hours = age_sec // 3600
    mins = (age_sec % 3600) // 60
    return f"{hours}h {mins}m"


def _manual_review_pending_state(self, payload):
    pending = dict((payload or {}).get("pending", {}) or {})
    ticker = str((payload or {}).get("ticker", "") or "")
    live_pending = self.order_service.get_pending(ticker) if hasattr(self, "order_service") else None
    base = live_pending if isinstance(live_pending, dict) else pending
    state = str(base.get("lifecycle_state", "") or "").strip()
    if state:
        return state
    if live_pending is None:
        return "reconciled_or_cleared"
    return "submitted"


def _selected_manual_review_key(self):
    table = getattr(self, "manual_review_table", None)
    if table is None:
        return None
    row = int(table.currentRow())
    if row < 0:
        return None
    keys = list(getattr(self, "_manual_review_row_keys", []) or [])
    if row >= len(keys):
        return None
    return str(keys[row] or "")


def refresh_manual_review_table(self):
    table = getattr(self, "manual_review_table", None)
    if table is None:
        return
    self._ensure_order_stability_state()
    queue_rows = dict(getattr(self, "_manual_review_queue", {}) or {})
    age_alert_sec = int(getattr(Config, "DEFAULT_MANUAL_REVIEW_AGE_ALERT_SEC", 600))
    now = datetime.datetime.now()

    rows = []
    for key, payload in queue_rows.items():
        if not isinstance(payload, dict):
            continue
        queued_at = self._safe_parse_iso_datetime(payload.get("queued_at"))
        age_sec = int((now - queued_at).total_seconds()) if isinstance(queued_at, datetime.datetime) else 0
        rows.append((str(key), payload, queued_at, age_sec))
    rows.sort(key=lambda item: item[2] or datetime.datetime.min, reverse=True)

    table.setRowCount(0)
    self._manual_review_row_keys = []
    overdue_count = 0
    for key, payload, queued_at, age_sec in rows:
        row = table.rowCount()
        table.insertRow(row)
        self._manual_review_row_keys.append(key)

        ticker = str(payload.get("ticker", "") or "")
        uuid = str(payload.get("uuid", "") or "")
        reason = str(payload.get("reason", "") or "")
        pending_state = self._manual_review_pending_state(payload)
        queued_at_text = queued_at.strftime("%Y-%m-%d %H:%M:%S") if queued_at else "-"
        age_text = self._manual_review_age_text(age_sec)

        table.setItem(row, 0, QTableWidgetItem(queued_at_text))
        table.setItem(row, 1, QTableWidgetItem(age_text))
        table.setItem(row, 2, QTableWidgetItem(ticker))
        table.setItem(row, 3, QTableWidgetItem(uuid))
        table.setItem(row, 4, QTableWidgetItem(reason))
        table.setItem(row, 5, QTableWidgetItem(pending_state))

        if age_sec >= age_alert_sec:
            overdue_count += 1
            for col in range(0, 6):
                item = table.item(row, col)
                if item is not None:
                    item.setBackground(QColor("#fff1b8"))
            self._ops_alert(
                level="warning",
                message=f"⚠️ [{ticker or uuid}] 수동검토 큐 에이징 경고 ({age_text})",
                key=f"manual_review_aging:{key}",
                cooldown=60,
            )

    label = getattr(self, "lbl_manual_review_count", None)
    if label is not None:
        if overdue_count > 0:
            label.setText(f"🧾 수동검토 큐 {len(rows)}건 (지연 {overdue_count}건)")
        else:
            label.setText(f"🧾 수동검토 큐 {len(rows)}건")


def requery_selected_manual_review(self):
    key = self._selected_manual_review_key()
    if not key:
        QMessageBox.information(self, "알림", "재조회할 수동검토 항목을 선택해주세요.")
        return
    payload = dict(getattr(self, "_manual_review_queue", {}).get(key, {}) or {})
    if not payload:
        self.log(f"[WARN] 선택한 수동검토 항목을 찾을 수 없습니다: {key}")
        return

    ticker = str(payload.get("ticker", "") or "")
    uuid = str(payload.get("uuid", "") or "")
    pending = self.order_service.get_pending(ticker) if hasattr(self, "order_service") else None
    if (not pending) and hasattr(self.order_service, "get_pending_by_uuid"):
        pending_ticker, pending_by_uuid = self.order_service.get_pending_by_uuid(uuid)
        if pending_by_uuid:
            ticker = str(pending_ticker or ticker)
            pending = pending_by_uuid

    order = self._safe_get_order(uuid) if hasattr(self, "_safe_get_order") else None
    state = str((order or {}).get("state", "")).lower()
    payload["last_requery_at"] = datetime.datetime.now().isoformat()
    payload["last_known_state"] = state or "unknown"
    self._manual_review_queue[key] = payload
    self._mark_reconciliation_dirty()

    if state in ("done", "cancel") and pending:
        self._transition_pending(
            ticker,
            state,
            reason="manual_review_requery_terminal",
            metadata={"uuid": uuid, "queue_key": key},
        )
        self._reconcile_terminal_pending(ticker, pending)
        self.log(f"🔁 [{ticker}] 수동검토 재조회 terminal 감지: {state}")
    else:
        self.log(f"🔁 [{ticker}] 수동검토 재조회 결과: {state or 'unknown'}")

    self._emit_order_lifecycle_event(
        "manual_review_requery",
        ticker=ticker,
        uuid=uuid,
        session_id=int((pending or payload.get("pending", {})).get("session_id", 0) or 0),
        state_from=str((pending or payload.get("pending", {})).get("lifecycle_state", "manual_review")),
        state_to=state or "",
        reason="manual_review_requery",
        source=str((pending or payload.get("pending", {})).get("source", "")),
        metadata={"queue_key": key},
    )
    self.refresh_manual_review_table()


def resolve_selected_manual_review(self):
    key = self._selected_manual_review_key()
    if not key:
        QMessageBox.information(self, "알림", "해제할 수동검토 항목을 선택해주세요.")
        return
    payload = dict(getattr(self, "_manual_review_queue", {}).get(key, {}) or {})
    if not payload:
        self.log(f"[WARN] 선택한 수동검토 항목을 찾을 수 없습니다: {key}")
        return

    ticker = str(payload.get("ticker", "") or "")
    uuid = str(payload.get("uuid", "") or "")
    pending = self.order_service.get_pending(ticker) if hasattr(self, "order_service") else None
    self._manual_review_queue.pop(key, None)
    self._mark_reconciliation_dirty()
    self._emit_order_lifecycle_event(
        "manual_review_resolved",
        ticker=ticker,
        uuid=uuid,
        session_id=int((pending or payload.get("pending", {})).get("session_id", 0) or 0),
        state_from=str((pending or payload.get("pending", {})).get("lifecycle_state", "manual_review")),
        state_to=str((pending or payload.get("pending", {})).get("lifecycle_state", "")),
        reason="manual_review_queue_resolved",
        source=str((pending or payload.get("pending", {})).get("source", "")),
        metadata={"queue_key": key, "queue_only": True},
    )
    self.log(f"✅ [{ticker}] 수동검토 큐 해제 완료 (pending 유지)")
    self.refresh_manual_review_table()
