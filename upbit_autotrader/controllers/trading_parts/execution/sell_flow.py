from __future__ import annotations

import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import estimate_realized_slippage_bps, plan_execution
from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker
from upbit_autotrader.controllers.trading_parts.order_api.chance import _extract_chance_fee_bps
from .validation import _sell_order_has_fill, _validate_live_order_request, _market_regime_fields_dict

try:
    from upbit_autotrader.notifications.notifiers import EventType
except ImportError:
    EventType = None



def execute_sell(self, ticker, reason):
    """매도 주문"""
    if not self.upbit and not self._is_paper_mode():
        return
    self._ensure_order_stability_state()
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
        return

    info = self.universe.get(ticker)
    if not info:
        self.log(f"[WARN] {ticker} 보유 정보를 찾을 수 없어 매도를 건너뜁니다.")
        return
    qty = info["qty"]
    if qty == 0:
        return
    session_id = getattr(self, "_active_session_id", 0)

    curr_price = float(info.get("current", 0.0) or 0.0)
    notional = float(qty) * curr_price if curr_price > 0 else float(info.get("invest_amt", 0.0) or 0.0)
    market_regime_fields = _market_regime_fields_dict(self._capture_market_regime_fields(info))
    exec_cfg = self._get_execution_config()
    execution_plan = plan_execution(exec_cfg, notional, realized_vol_pct=0.0, force_mode=self._execution_mode())
    if execution_plan.mode == "twap_market":
        self.log(f"[{ticker}] 매도 TWAP는 현재 단일 시장가로 실행합니다.")
    can_order, order_err, _chance = _validate_live_order_request(
        self,
        ticker,
        "SELL",
        qty=qty,
        ref_price=max(curr_price, float(info.get("buy_price", 0.0) or 0.0)),
    )
    if not can_order:
        self.log(order_err)
        return

    try:
        ok, result, err_msg = self._place_sell_order(ticker, qty, side="SELL", session_id=session_id, source="auto_sell")
        if ok and result and "uuid" in result:
            if hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    requested_qty=float(qty or 0.0),
                    sell_reason=str(reason or "매도"),
                    context_label="매도",
                    execution_mode="single_market" if execution_plan.mode == "twap_market" else str(execution_plan.mode),
                    expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                    strategy_score=float(info.get("last_strategy_score", 0.0) or 0.0),
                    meta_score=float(info.get("last_meta_score", 0.0) or 0.0),
                    risk_state=str(info.get("last_risk_state", "normal")),
                    **market_regime_fields,
                )
            info["state"] = "매도주문중"
            self.set_table_item(info["row"], 4, "⏳ 매도주문중", "#ffc107")
            self.log(f"📤 [{ticker}] 매도 주문: {qty:.8f} ({reason})")
            self.logger.info(f"매도 주문: {ticker} {qty:.8f} ({reason})")
            QTimer.singleShot(2000, lambda t=ticker, u=result["uuid"], r=reason, s=session_id: self.check_sell_execution(t, u, r, retry_count=0, session_id=s))
        else:
            self.log(f"[ERROR] 매도 주문 실패: {err_msg} / {result}")
    except Exception as e:
        self.order_service.clear_pending(ticker)
        self.log(f"[ERROR] 매도 주문 실패: {e}")
        self.logger.error(f"매도 주문 실패 ({ticker}): {e}")


def _execute_partial_sell(self, ticker, qty, reason, level=None):
    """부분 매도 주문"""
    if not self.upbit and not self._is_paper_mode():
        return False
    info = self.universe.get(ticker)
    if not info or qty <= 0:
        return False
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
        return False

    curr_price = float(info.get("current", 0.0) or 0.0)
    notional = float(qty) * curr_price if curr_price > 0 else float(qty * info.get("buy_price", 0.0))
    market_regime_fields = _market_regime_fields_dict(self._capture_market_regime_fields(info))
    exec_cfg = self._get_execution_config()
    execution_plan = plan_execution(exec_cfg, notional, realized_vol_pct=0.0, force_mode=self._execution_mode())
    if execution_plan.mode == "twap_market":
        self.log(f"[{ticker}] 분할익절 TWAP는 현재 단일 시장가로 실행합니다.")
    can_order, order_err, _chance = _validate_live_order_request(
        self,
        ticker,
        "SELL",
        qty=qty,
        ref_price=max(curr_price, float(info.get("buy_price", 0.0) or 0.0)),
    )
    if not can_order:
        self.log(order_err)
        return False

    session_id = getattr(self, "_active_session_id", 0)
    try:
        ok, result, err_msg = self._place_sell_order(
            ticker,
            qty,
            side="PARTIAL_SELL",
            session_id=session_id,
            source="partial_sell",
        )
        if ok and result and "uuid" in result:
            if hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    requested_qty=float(qty or 0.0),
                    sell_reason=str(reason or "분할익절"),
                    partial_level=level,
                    context_label="분할 매도",
                    execution_mode="single_market" if execution_plan.mode == "twap_market" else str(execution_plan.mode),
                    expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                    strategy_score=float(info.get("last_strategy_score", 0.0) or 0.0),
                    meta_score=float(info.get("last_meta_score", 0.0) or 0.0),
                    risk_state=str(info.get("last_risk_state", "normal")),
                    **market_regime_fields,
                )
            self.log(f"📤 [{ticker}] 분할 매도: {qty:.8f} ({reason})")
            self.logger.info(f"분할 매도: {ticker} {qty:.8f} ({reason})")
            QTimer.singleShot(2000, lambda t=ticker, u=result["uuid"], q=qty, r=reason, lv=level, s=session_id: self._check_partial_sell_execution(t, u, q, r, lv, retry_count=0, session_id=s))
            return True
        self.log(f"[ERROR] 분할 매도 실패: {err_msg} / {result}")
        return False
    except Exception as e:
        self.order_service.clear_pending(ticker)
        self.log(f"[ERROR] 분할 매도 실패: {e}")
        self.logger.error(f"분할 매도 실패 ({ticker}): {e}")
        return False


def _check_partial_sell_execution(self, ticker, uuid, qty, reason, level=None, retry_count=0, session_id=None):
    """분할 매도 체결 확인"""
    MAX_RETRIES = 30
    pending = self.order_service.get_pending(ticker)
    if not pending or (pending and str(pending.get("uuid")) != str(uuid)):
        return
    clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
    mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)

    try:
        order_raw = self._safe_get_order(uuid) if hasattr(self, "_safe_get_order") else self.upbit.get_order(uuid)
        order = order_raw if isinstance(order_raw, dict) else None
        state = str(order.get("state", "")).lower() if order else "wait"
        terminal_with_fill = state in ("done", "cancel") and _sell_order_has_fill(self, order)
        if pending and hasattr(self.order_service, "update_pending"):
            self.order_service.update_pending(
                ticker,
                last_checked_at=datetime.datetime.now(),
                retry_count=int(pending.get("retry_count", 0) or 0) + 1,
            )
            self._transition_pending(ticker, "wait", reason="partial_sell_execution_poll")

        if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
            if state in ("done", "cancel"):
                self._handle_session_mismatch_terminal(
                    ticker=ticker,
                    uuid=uuid,
                    side="PARTIAL_SELL",
                    state=state,
                    session_id=session_id,
                    source="_check_partial_sell_execution",
                )
            return

        if terminal_with_fill:
            transition_reason = "partial_sell_execution_done" if state == "done" else "partial_sell_execution_cancel_with_fill"
            self._transition_pending(ticker, "done", reason=transition_reason, metadata={"raw_state": state})
            info = self.universe.get(ticker)
            if not info:
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                return

            executed_volume, _, trades_price = self.order_service.get_sell_fill_metrics(order)
            execution_mode = str((pending or {}).get("execution_mode", "single_market") or "single_market")
            expected_slippage_bps = float((pending or {}).get("expected_slippage_bps", 0.0) or 0.0)
            expected_fee_buy_bps = float((pending or {}).get("expected_fee_buy_bps", 0.0) or 0.0)
            expected_fee_sell_bps = float((pending or {}).get("expected_fee_sell_bps", 0.0) or 0.0)
            strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
            meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
            risk_state = str((pending or {}).get("risk_state", "normal") or "normal")
            resolve_market_regime_fields = getattr(self, "_resolve_market_regime_fields", None)
            market_regime_fields = _market_regime_fields_dict(
                resolve_market_regime_fields(pending=pending, info=info)
                if callable(resolve_market_regime_fields)
                else {
                    "market_regime_score": float((pending or {}).get("market_regime_score", info.get("last_market_regime_score", 50.0)) or 50.0),
                    "market_regime_label": str((pending or {}).get("market_regime_label", info.get("last_market_regime_label", "neutral")) or "neutral"),
                    "market_regime_ts": str((pending or {}).get("market_regime_ts", info.get("last_market_regime_ts", "")) or ""),
                }
            )

            if executed_volume <= 0 or trades_price <= 0:
                self.log(f"⚠️ [{ticker}] 분할 매도 체결 정보가 유효하지 않습니다.")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                return

            info["qty"] -= executed_volume
            if info["qty"] < 0:
                info["qty"] = 0
            info["invest_amt"], profit = self.order_service.apply_partial_sell_accounting(
                info["invest_amt"],
                info["qty"],
                executed_volume,
                trades_price,
            )
            self.total_realized_profit += profit
            self.trade_count += 1
            if profit > 0:
                self.win_count += 1
            self.lbl_total_profit.setText(f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원")
            qty_item = info.get("ui_items", {}).get("qty")
            if qty_item is None:
                qty_item = QTableWidgetItem("-")
                self.table.setItem(info["row"], 5, qty_item)
                info.setdefault("ui_items", {})["qty"] = qty_item
            qty_item.setText(f"{info['qty']:.8f}")
            suffix = " (취소 상태 잔여분 정리 후 체결 반영)" if state == "cancel" else ""
            self.log(f"✅ [{ticker}] 분할 매도 체결 (손익: {profit:+,.0f}원){suffix}")
            ref_price = float(info.get("current", trades_price) or trades_price)
            fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
            realized_slippage_bps = estimate_realized_slippage_bps(ref_price, trades_price, side="sell")
            self.add_trade_record(
                ticker,
                "PARTIAL_SELL",
                trades_price,
                executed_volume,
                profit,
                reason,
                fee_krw=fee_krw,
                expected_slippage_bps=expected_slippage_bps,
                realized_slippage_bps=realized_slippage_bps,
                execution_mode=execution_mode,
                execution_mode_requested=str((pending or {}).get("execution_mode_requested", execution_mode) or execution_mode),
                execution_mode_actual=str((pending or {}).get("execution_mode_actual", execution_mode) or execution_mode),
                execution_fallback_reason=str((pending or {}).get("execution_fallback_reason", "") or ""),
                expected_fee_buy_bps=expected_fee_buy_bps,
                expected_fee_sell_bps=expected_fee_sell_bps,
                session_id=session_id,
                risk_state=risk_state,
                strategy_score=strategy_score,
                meta_score=meta_score,
                **market_regime_fields,
            )
            if level is not None and level not in info.setdefault("partial_sold", []):
                info["partial_sold"].append(level)
            self._update_statistics()
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}
            self.get_balance()
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(mark_reconciliation):
                mark_reconciliation()
        elif state == "cancel":
            self._transition_pending(ticker, "cancel", reason="partial_sell_execution_cancel")
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            self.log(f"⚠️ [{ticker}] 분할 매도 주문 취소됨")
            if callable(mark_reconciliation):
                mark_reconciliation()
        else:
            if retry_count < MAX_RETRIES:
                QTimer.singleShot(2000, lambda t=ticker, u=uuid, q=qty, r=reason, lv=level, rc=retry_count + 1, s=session_id: self._check_partial_sell_execution(t, u, q, r, lv, rc, s))
            else:
                self.log(f"[ERROR] [{ticker}] 분할 매도 체결 확인 타임아웃")
                resolved = self._resolve_timeout_pending(ticker=ticker, pending=pending, reason="partial_sell_execution_timeout")
                if not resolved:
                    self._ops_alert(
                        level="warning",
                        message=f"⚠️ [{ticker}] 분할매도 타임아웃 unresolved - 수동검토 필요",
                        key=f"partial_timeout_unresolved:{uuid}",
                        cooldown=30,
                    )
    except Exception as e:
        self._register_manual_review(ticker=ticker, uuid=uuid, reason=f"partial_sell_execution_exception:{e}", order=None)
        self.logger.error(f"분할 매도 체결 확인 실패 ({ticker}): {e}")


def check_sell_execution(self, ticker, uuid, reason, retry_count=0, session_id=None):
    """매도 체결 확인"""
    MAX_RETRIES = 30
    pending = self.order_service.get_pending(ticker)
    if not pending or (pending and str(pending.get("uuid")) != str(uuid)):
        return
    clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
    mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)
    transition_pending = getattr(self, "_transition_pending", None)
    handle_session_mismatch = getattr(self, "_handle_session_mismatch_terminal", None)
    resolve_timeout_pending = getattr(self, "_resolve_timeout_pending", None)
    ops_alert = getattr(self, "_ops_alert", None)
    register_manual_review = getattr(self, "_register_manual_review", None)
    persist_strategy_performance = getattr(self, "_persist_strategy_performance", None)

    try:
        order_raw = self._safe_get_order(uuid) if hasattr(self, "_safe_get_order") else self.upbit.get_order(uuid)
        order = order_raw if isinstance(order_raw, dict) else None
        state = str(order.get("state", "")).lower() if order else "wait"
        terminal_with_fill = state in ("done", "cancel") and _sell_order_has_fill(self, order)
        if pending and hasattr(self.order_service, "update_pending"):
            self.order_service.update_pending(
                ticker,
                last_checked_at=datetime.datetime.now(),
                retry_count=int(pending.get("retry_count", 0) or 0) + 1,
            )
            if callable(transition_pending):
                transition_pending(ticker, "wait", reason="sell_execution_poll")

        if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
            if state in ("done", "cancel") and callable(handle_session_mismatch):
                handle_session_mismatch(
                    ticker=ticker,
                    uuid=uuid,
                    side="SELL",
                    state=state,
                    session_id=session_id,
                    source="check_sell_execution",
                )
            return

        if terminal_with_fill:
            if callable(transition_pending):
                reason_key = "sell_execution_done" if state == "done" else "sell_execution_cancel_with_fill"
                transition_pending(ticker, "done", reason=reason_key, metadata={"raw_state": state})
            info = self.universe.get(ticker)
            if not info:
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                return

            executed_volume, sell_amount, trades_price = self.order_service.get_sell_fill_metrics(order)
            execution_mode = str((pending or {}).get("execution_mode", "single_market") or "single_market")
            expected_slippage_bps = float((pending or {}).get("expected_slippage_bps", 0.0) or 0.0)
            expected_fee_buy_bps = float((pending or {}).get("expected_fee_buy_bps", 0.0) or 0.0)
            expected_fee_sell_bps = float((pending or {}).get("expected_fee_sell_bps", 0.0) or 0.0)
            strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
            meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
            risk_state = str((pending or {}).get("risk_state", "normal") or "normal")
            resolve_market_regime_fields = getattr(self, "_resolve_market_regime_fields", None)
            market_regime_fields = _market_regime_fields_dict(
                resolve_market_regime_fields(pending=pending, info=info)
                if callable(resolve_market_regime_fields)
                else {
                    "market_regime_score": float((pending or {}).get("market_regime_score", info.get("last_market_regime_score", 50.0)) or 50.0),
                    "market_regime_label": str((pending or {}).get("market_regime_label", info.get("last_market_regime_label", "neutral")) or "neutral"),
                    "market_regime_ts": str((pending or {}).get("market_regime_ts", info.get("last_market_regime_ts", "")) or ""),
                }
            )
            if executed_volume <= 0 or sell_amount <= 0:
                info["state"] = "보유중"
                self.set_table_item(info["row"], 4, "💼 보유중", "#00b4d8")
                self.log(f"⚠️ [{ticker}] 매도 체결 정보가 유효하지 않습니다.")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                return

            buy_amount = float(info.get("invest_amt", 0.0) or 0.0)
            remaining_qty = max(0.0, float(info.get("qty", 0.0) or 0.0) - executed_volume)
            terminal_full_exit = remaining_qty <= 1e-12
            if terminal_full_exit:
                profit = sell_amount - buy_amount
            else:
                buy_amount, profit = self.order_service.apply_partial_sell_accounting(
                    buy_amount,
                    remaining_qty,
                    executed_volume,
                    trades_price,
                )
            self.total_realized_profit += profit
            self.trade_count += 1
            if profit > 0:
                self.win_count += 1
            self.lbl_total_profit.setText(f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원")
            info["qty"] = remaining_qty
            if terminal_full_exit:
                info["state"] = "감시중"
                info["buy_price"] = 0
                info["invest_amt"] = 0
                info["high_since_buy"] = 0
                info["max_profit_rate"] = 0.0
                info["partial_sold"] = []
                self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
            else:
                info["state"] = "보유중"
                info["invest_amt"] = max(0.0, buy_amount)
                info["buy_price"] = (info["invest_amt"] / remaining_qty) if remaining_qty > 0 else 0.0
                self.set_table_item(info["row"], 4, "💼 보유중", "#00b4d8")
            qty_item = info.get("ui_items", {}).get("qty")
            if qty_item is not None:
                qty_item.setText("0.00000000" if terminal_full_exit else f"{remaining_qty:.8f}")
            buy_price_item = info.get("ui_items", {}).get("buy_price")
            if buy_price_item is not None:
                buy_price_item.setText("-" if terminal_full_exit else f"{float(info.get('buy_price', 0.0) or 0.0):,.0f}")
            invest_item = info.get("ui_items", {}).get("invest")
            if invest_item is not None:
                invest_item.setText("-" if terminal_full_exit else f"{float(info.get('invest_amt', 0.0) or 0.0):,.0f}")
            profit_item = info.get("ui_items", {}).get("profit")
            if profit_item is not None and terminal_full_exit:
                profit_item.setText("-")
            max_profit_item = info.get("ui_items", {}).get("max_profit")
            if max_profit_item is not None and terminal_full_exit:
                max_profit_item.setText("-")

            if terminal_full_exit and self.strategy:
                self.strategy.update_consecutive_results(profit > 0)
                self.strategy.clear_holding_start(ticker)
                self.strategy.clear_partial_profit(ticker)
                if hasattr(self, "chk_use_cooldown") and self.chk_use_cooldown.isChecked():
                    cooldown_minutes = self.spin_cooldown.value() if hasattr(self, "spin_cooldown") else None
                    self.strategy.set_cooldown(ticker, cooldown_minutes)

            fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
            realized_slippage_bps = estimate_realized_slippage_bps(float(info.get("current", trades_price) or trades_price), trades_price, side="sell")
            suffix = ""
            if state == "cancel":
                suffix = " (취소 상태 잔여분 정리 후 체결 반영)"
            if not terminal_full_exit:
                suffix = f"{suffix} [부분 체결 잔여수량 {remaining_qty:.8f}]".strip()
            self.log(f"✅ [{ticker}] 매도 체결 (손익: {profit:+,.0f}원){(' ' + suffix) if suffix else ''}")
            self.add_trade_record(
                ticker,
                "SELL",
                trades_price,
                executed_volume,
                profit,
                reason,
                fee_krw=fee_krw,
                expected_slippage_bps=expected_slippage_bps,
                realized_slippage_bps=realized_slippage_bps,
                execution_mode=execution_mode,
                execution_mode_requested=str((pending or {}).get("execution_mode_requested", execution_mode) or execution_mode),
                execution_mode_actual=str((pending or {}).get("execution_mode_actual", execution_mode) or execution_mode),
                execution_fallback_reason=str((pending or {}).get("execution_fallback_reason", "") or ""),
                expected_fee_buy_bps=expected_fee_buy_bps,
                expected_fee_sell_bps=expected_fee_sell_bps,
                session_id=session_id,
                risk_state=risk_state,
                strategy_score=strategy_score,
                meta_score=meta_score,
                **market_regime_fields,
            )
            manager = getattr(self, "notification_manager", None)
            if manager is not None and EventType is not None and hasattr(manager, "notify_sell"):
                try:
                    denom = float(info.get("invest_amt", 0.0) or 0.0) + profit if not terminal_full_exit else buy_amount
                    pnl_pct = (profit / denom * 100.0) if denom > 0 else 0.0
                    manager.notify_sell(ticker, trades_price, executed_volume, pnl_pct, reason=reason)
                except Exception:
                    pass

            if terminal_full_exit:
                strategy_id = str(info.get("last_strategy_id", "legacy") or "legacy")
                pnl_pct = (profit / buy_amount * 100.0) if buy_amount > 0 else 0.0
                tracker = getattr(self, "strategy_perf_tracker", None)
                if tracker is None:
                    tracker = StrategyPerformanceTracker()
                    self.strategy_perf_tracker = tracker
                tracker.update(strategy_id, pnl_pct)
                if callable(persist_strategy_performance):
                    persist_strategy_performance()

            self._update_statistics()
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}
            self.get_balance()
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(mark_reconciliation):
                mark_reconciliation()
        elif state == "cancel":
            if callable(transition_pending):
                transition_pending(ticker, "cancel", reason="sell_execution_cancel")
            self.log(f"⚠️ [{ticker}] 매도 주문 취소됨")
            info = self.universe.get(ticker)
            if info and info["qty"] > 0:
                info["state"] = "보유중"
                self.set_table_item(info["row"], 4, "💼 보유중", "#00b4d8")
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(mark_reconciliation):
                mark_reconciliation()
        else:
            if retry_count < MAX_RETRIES:
                QTimer.singleShot(2000, lambda t=ticker, u=uuid, r=reason, rc=retry_count + 1, s=session_id: self.check_sell_execution(t, u, r, rc, s))
            else:
                self.log(f"[ERROR] [{ticker}] 매도 체결 확인 타임아웃 (60초)")
                self.logger.error(f"매도 체결 확인 타임아웃: {ticker}, uuid={uuid}")
                info = self.universe.get(ticker)
                if info:
                    info["state"] = "체결확인실패"
                    self.set_table_item(info["row"], 4, "❓ 확인필요", "#ffc107")
                if callable(resolve_timeout_pending):
                    resolved = resolve_timeout_pending(ticker=ticker, pending=pending, reason="sell_execution_timeout")
                else:
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    resolved = True
                if not resolved and callable(ops_alert):
                    ops_alert(
                        level="warning",
                        message=f"⚠️ [{ticker}] 매도 주문 타임아웃 unresolved - 수동검토 필요",
                        key=f"sell_timeout_unresolved:{uuid}",
                        cooldown=30,
                    )
    except Exception as e:
        if callable(register_manual_review):
            register_manual_review(ticker=ticker, uuid=uuid, reason=f"sell_execution_exception:{e}", order=None)
        elif callable(clear_pending_if_uuid):
            clear_pending_if_uuid(ticker, uuid)
        else:
            self.order_service.clear_pending(ticker)
        self.logger.error(f"매도 체결 확인 실패 ({ticker}): {e}")
