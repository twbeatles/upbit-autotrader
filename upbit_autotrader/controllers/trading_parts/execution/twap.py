from __future__ import annotations

import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import estimate_realized_slippage_bps, plan_execution
from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker
from upbit_autotrader.controllers.trading_parts.order_api.chance import _extract_chance_fee_bps
from .validation import _market_regime_fields_dict

try:
    from upbit_autotrader.notifications.notifiers import EventType
except ImportError:
    EventType = None



def _start_twap_buy(self, ticker, curr_price, slices, session_id):
    self._ensure_order_stability_state()
    if not slices:
        return False
    self._twap_buy_plans[ticker] = {
        "slices": [float(v) for v in slices if float(v) > 0],
        "next_idx": 0,
        "interval_sec": int(self._get_spin_value("spin_twap_interval_sec", getattr(Config, "DEFAULT_TWAP_INTERVAL_SEC", 8))),
        "session_id": int(session_id or 0),
        "curr_price": float(curr_price or 0.0),
    }
    return _run_next_twap_buy_slice(self, ticker)


def _run_next_twap_buy_slice(self, ticker):
    self._ensure_order_stability_state()
    plan = dict(getattr(self, "_twap_buy_plans", {}).get(ticker, {}) or {})
    if not plan:
        return False
    if self.order_service.has_pending(ticker):
        return False

    slices = list(plan.get("slices", []) or [])
    idx = int(plan.get("next_idx", 0) or 0)
    if idx >= len(slices):
        self._twap_buy_plans.pop(ticker, None)
        return False

    amount = float(slices[idx] or 0.0)
    if amount < 5000.0:
        plan["next_idx"] = idx + 1
        self._twap_buy_plans[ticker] = plan
        return _run_next_twap_buy_slice(self, ticker)

    session_id = int(plan.get("session_id", 0) or 0)
    if not self._reserve_krw_for_buy(ticker, amount, session_id=session_id):
        self.log(f"[{ticker}] TWAP 가용 잔고 부족으로 중단")
        self._twap_buy_plans.pop(ticker, None)
        return False

    ok, result, err_msg = self._place_buy_order(
        ticker,
        amount,
        session_id=session_id,
        source=f"twap_buy_{idx + 1}/{len(slices)}",
    )
    if not ok or not result or "uuid" not in result:
        self._release_reserved_krw(ticker)
        self.log(f"[ERROR] [{ticker}] TWAP 매수 주문 실패: {err_msg}")
        self._twap_buy_plans.pop(ticker, None)
        return False

    info = self.universe.get(ticker)
    if hasattr(self.order_service, "update_pending"):
        market_regime_fields = _market_regime_fields_dict(self._resolve_market_regime_fields(info=info))
        self.order_service.update_pending(
            ticker,
            execution_mode="twap_market",
            twap_slice_index=int(idx + 1),
            twap_slice_count=int(len(slices)),
            expected_slippage_bps=float((info or {}).get("last_expected_slippage_bps", 0.0) or 0.0),
            strategy_score=float((info or {}).get("last_strategy_score", 0.0) or 0.0),
            meta_score=float((info or {}).get("last_meta_score", 0.0) or 0.0),
            risk_state=str((info or {}).get("last_risk_state", "normal") or "normal"),
            **market_regime_fields,
        )
    self._mark_reconciliation_dirty()

    if info:
        info["state"] = "주문중"
        self.set_table_item(info["row"], 4, "⏳ 주문중", "#ffc107")

    plan["next_idx"] = idx + 1
    self._twap_buy_plans[ticker] = plan
    self.log(f"📤 [{ticker}] TWAP 매수 {idx + 1}/{len(slices)}: {amount:,.0f}원")
    QTimer.singleShot(2000, lambda t=ticker, u=result["uuid"], s=session_id: self.check_buy_execution(t, u, retry_count=0, session_id=s))
    return True


def _schedule_next_twap_buy_slice(self, ticker):
    self._ensure_order_stability_state()
    plan = self._twap_buy_plans.get(ticker)
    if not plan:
        return
    if self.order_service.has_pending(ticker):
        return
    idx = int(plan.get("next_idx", 0) or 0)
    total = len(plan.get("slices", []) or [])
    if idx >= total:
        self._twap_buy_plans.pop(ticker, None)
        self.log(f"✅ [{ticker}] TWAP 매수 시퀀스 완료")
        return
    delay_ms = int(max(0, int(plan.get("interval_sec", 8) or 8)) * 1000)
    QTimer.singleShot(delay_ms, lambda t=ticker: _run_next_twap_buy_slice(self, t))
