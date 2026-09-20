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



def _handle_ws_order_event(self, data: dict):
    """Handle real-time private myOrder WebSocket events."""
    if not isinstance(data, dict):
        return
    market = str(data.get("code") or data.get("market") or "").strip()
    uuid_val = str(data.get("uuid") or "").strip()
    state = str(data.get("state") or "").strip().lower()
    if not market or not uuid_val:
        return

    if hasattr(self, "order_service") and self.order_service.has_pending(market):
        pending = self.order_service.get_pending(market)
        if str((pending or {}).get("uuid")) == uuid_val:
            if state in ("trade", "done"):
                self._transition_pending(market, "done" if state == "done" else "wait", reason=f"ws_myorder_{state}")
                self._mark_reconciliation_dirty()
            elif state in ("cancel", "cancelled"):
                self._transition_pending(market, "cancel", reason="ws_myorder_cancel")
                self._mark_reconciliation_dirty()
