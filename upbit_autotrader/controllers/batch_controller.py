import datetime
from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog

from upbit_autotrader.controllers._type_support import ControllerTypeBase
from upbit_autotrader.services.holdings_service import get_account_holdings as get_account_holdings_v2
from upbit_autotrader.controllers.batch_parts import batch_ops as _batch_ops
try:
    import pyupbit
except ImportError:
    pyupbit = cast(Any, None)

try:
    from upbit_autotrader.ui.dialogs import EmergencyCloseDialog
    V3_MODULES_AVAILABLE = True
except ImportError:
    EmergencyCloseDialog = cast(Any, None)
    V3_MODULES_AVAILABLE = False


class TraderBatchController(ControllerTypeBase):
    def get_account_holdings(self):
        """현재 보유 중인 모든 KRW 마켓 코인 조회"""
        if hasattr(self, "_is_paper_mode") and self._is_paper_mode():
            svc = self._ensure_paper_service_state() if hasattr(self, "_ensure_paper_service_state") else None
            if svc is None:
                return []
            holdings_raw = svc.get_holdings()
            tickers = list(holdings_raw.keys())
            prices_map = {}
            if pyupbit is not None and tickers:
                try:
                    ticker_arg = tickers if len(tickers) > 1 else tickers[0]
                    prices = cast(Any, pyupbit).get_current_price(ticker_arg)
                    if isinstance(prices, dict):
                        prices_map = prices
                    elif len(tickers) == 1 and prices is not None:
                        prices_map = {tickers[0]: prices}
                except Exception:
                    prices_map = {}
            holdings = []
            for ticker, h in holdings_raw.items():
                qty = float(h.get("qty", 0.0) or 0.0)
                if qty <= 0:
                    continue
                buy_price = float(h.get("avg_buy_price", 0.0) or 0.0)
                current = float(prices_map.get(ticker, self.universe.get(ticker, {}).get("current", buy_price)) or buy_price)
                value = qty * current
                pnl = ((current - buy_price) / buy_price * 100.0) if buy_price > 0 and current > 0 else 0.0
                holdings.append(
                    {
                        "ticker": ticker,
                        "currency": ticker.replace("KRW-", ""),
                        "qty": qty,
                        "buy_price": buy_price,
                        "current_price": current,
                        "value": value,
                        "pnl": pnl,
                    }
                )
            self.logger.info(f"[PAPER] 보유 코인 조회: {len(holdings)}개")
            return holdings

        if not self.upbit:
            return []

        try:
            balances = self._api_get_balances() if hasattr(self, "_api_get_balances") else None
            if isinstance(balances, list):
                holdings = get_account_holdings_v2(self.upbit, balances=balances)
            else:
                holdings = get_account_holdings_v2(self.upbit)
            self.logger.info(f"보유 코인 조회: {len(holdings)}개")
            return holdings
        except Exception as e:
            self.logger.error(f"보유 코인 조회 실패: {e}")
            return []

    def execute_batch_sell(self):
        """모든 보유 코인 일괄 시장가 매도"""
        _batch_ops.bind_runtime(
            QDialog=QDialog,
            QInputDialog=QInputDialog,
            QMessageBox=QMessageBox,
            QTimer=QTimer,
            EmergencyCloseDialog=EmergencyCloseDialog,
            V3_MODULES_AVAILABLE=V3_MODULES_AVAILABLE,
        )
        return _batch_ops.execute_batch_sell(self)

    def execute_batch_buy(self):
        """입력된 코인들 현재가로 일괄 매수"""
        _batch_ops.bind_runtime(
            QDialog=QDialog,
            QInputDialog=QInputDialog,
            QMessageBox=QMessageBox,
            QTimer=QTimer,
            EmergencyCloseDialog=EmergencyCloseDialog,
            V3_MODULES_AVAILABLE=V3_MODULES_AVAILABLE,
        )
        return _batch_ops.execute_batch_buy(self)

    # ------------------------------------------------------------------
    # 유틸리티

    def show_emergency_dialog(self):
        """긴급 청산 다이얼로그 표시"""
        _batch_ops.bind_runtime(
            QDialog=QDialog,
            QInputDialog=QInputDialog,
            QMessageBox=QMessageBox,
            QTimer=QTimer,
            EmergencyCloseDialog=EmergencyCloseDialog,
            V3_MODULES_AVAILABLE=V3_MODULES_AVAILABLE,
        )
        return _batch_ops.show_emergency_dialog(self)

    def execute_emergency_close(self):
        """긴급 전량 청산 실행"""
        _batch_ops.bind_runtime(
            QDialog=QDialog,
            QInputDialog=QInputDialog,
            QMessageBox=QMessageBox,
            QTimer=QTimer,
            EmergencyCloseDialog=EmergencyCloseDialog,
            V3_MODULES_AVAILABLE=V3_MODULES_AVAILABLE,
        )
        return _batch_ops.execute_emergency_close(self)

    def _check_external_buy_execution(self, ticker, uuid, reason="외부매수", retry_count=0, session_id=None):
        """Universe 외부 코인 매수 체결 확인용"""
        MAX_RETRIES = 30
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        try:
            order = self._safe_get_order(uuid) if hasattr(self, "_safe_get_order") else self.upbit.get_order(uuid)
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending:
                now = datetime.datetime.now()
                if hasattr(self.order_service, "update_pending"):
                    self.order_service.update_pending(
                        ticker,
                        last_checked_at=now,
                        retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                    )
                if hasattr(self, "_transition_pending"):
                    self._transition_pending(ticker, "wait", reason="external_buy_execution_poll")

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if hasattr(self, "_handle_session_mismatch_terminal"):
                        self._handle_session_mismatch_terminal(
                            ticker=ticker,
                            uuid=uuid,
                            side="BUY",
                            state=state,
                            session_id=session_id,
                            source="_check_external_buy_execution",
                        )
                    else:
                        if hasattr(self.order_service, "clear_pending_if_uuid"):
                            self.order_service.clear_pending_if_uuid(ticker, uuid)
                        else:
                            self.order_service.clear_pending(ticker)
                        if hasattr(self, "_release_reserved_krw"):
                            self._release_reserved_krw(ticker)
                return

            executed_volume, total_cost, avg_price = self.order_service.get_buy_fill_metrics(order)
            terminal_with_fill = state in ("done", "cancel") and executed_volume > 0 and total_cost > 0
            if terminal_with_fill:
                if hasattr(self, "_transition_pending"):
                    reason = "external_buy_execution_done" if state == "done" else "external_buy_execution_cancel_with_fill"
                    self._transition_pending(ticker, "done", reason=reason, metadata={"raw_state": state})
                if executed_volume > 0 and total_cost > 0:
                    suffix = " (취소 상태 잔여분 정리 후 체결 반영)" if state == "cancel" else ""
                    self.log(f"✅ [{ticker}] {reason} 체결 완료: {executed_volume:.8f} @ {avg_price:,.0f}원{suffix}")
                    self.add_trade_record(ticker, 'BUY', avg_price, executed_volume, 0, reason)
                    self.get_balance()
                    if hasattr(self, "_risk_snapshot_cache"):
                        self._risk_snapshot_cache = {"ts": 0.0, "value": None}
                else:
                    self.log(f"⚠️ [{ticker}] {reason} 체결 정보가 유효하지 않습니다.")
                if hasattr(self.order_service, "clear_pending_if_uuid"):
                    self.order_service.clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if hasattr(self, "_release_reserved_krw"):
                    self._release_reserved_krw(ticker)
            elif state == 'cancel':
                if hasattr(self, "_transition_pending"):
                    self._transition_pending(ticker, "cancel", reason="external_buy_execution_cancel")
                if hasattr(self.order_service, "clear_pending_if_uuid"):
                    self.order_service.clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if hasattr(self, "_release_reserved_krw"):
                    self._release_reserved_krw(ticker)
                self.log(f"⚠️ [{ticker}] {reason} 주문 취소")
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, r=reason, rc=retry_count + 1, s=session_id: self._check_external_buy_execution(
                            t, u, r, rc, s
                        ),
                    )
                else:
                    used_resolver = hasattr(self, "_resolve_timeout_pending")
                    resolved = False
                    if used_resolver:
                        resolved = bool(self._resolve_timeout_pending(ticker, pending, reason="external_buy_execution_timeout"))
                    if not used_resolver and not resolved:
                        if hasattr(self.order_service, "clear_pending_if_uuid"):
                            self.order_service.clear_pending_if_uuid(ticker, uuid)
                        else:
                            self.order_service.clear_pending(ticker)
                        if hasattr(self, "_release_reserved_krw"):
                            self._release_reserved_krw(ticker)
                    if not resolved:
                        self.log(f"[ERROR] [{ticker}] {reason} 체결 확인 타임아웃")
        except Exception as e:
            if hasattr(self, "_register_manual_review"):
                self._register_manual_review(
                    ticker=ticker,
                    uuid=uuid,
                    reason=f"external_buy_execution_exception:{e}",
                    order=None,
                )
            else:
                if hasattr(self.order_service, "clear_pending_if_uuid"):
                    self.order_service.clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if hasattr(self, "_release_reserved_krw"):
                    self._release_reserved_krw(ticker)
            self.log(f"[ERROR] [{ticker}] {reason} 체결 확인 실패: {e}")

    def _check_external_sell_execution(self, ticker, uuid, reason="외부매도", context_label="외부 매도", retry_count=0, session_id=None):
        """Universe 외부 코인 매도 체결 확인용"""
        MAX_RETRIES = 30
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        try:
            order = self._safe_get_order(uuid) if hasattr(self, "_safe_get_order") else self.upbit.get_order(uuid)
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending:
                now = datetime.datetime.now()
                if hasattr(self.order_service, "update_pending"):
                    self.order_service.update_pending(
                        ticker,
                        last_checked_at=now,
                        retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                    )
                if hasattr(self, "_transition_pending"):
                    self._transition_pending(ticker, "wait", reason="external_sell_execution_poll")

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if hasattr(self, "_handle_session_mismatch_terminal"):
                        self._handle_session_mismatch_terminal(
                            ticker=ticker,
                            uuid=uuid,
                            side="SELL",
                            state=state,
                            session_id=session_id,
                            source="_check_external_sell_execution",
                        )
                    else:
                        if hasattr(self.order_service, "clear_pending_if_uuid"):
                            self.order_service.clear_pending_if_uuid(ticker, uuid)
                        else:
                            self.order_service.clear_pending(ticker)
                return

            executed_volume, sell_amount, avg_net_price = self.order_service.get_sell_fill_metrics(order)
            terminal_with_fill = state in ("done", "cancel") and executed_volume > 0 and sell_amount > 0
            if terminal_with_fill:
                if hasattr(self, "_transition_pending"):
                    reason_key = "external_sell_execution_done" if state == "done" else "external_sell_execution_cancel_with_fill"
                    self._transition_pending(ticker, "done", reason=reason_key, metadata={"raw_state": state})
                if executed_volume > 0 and avg_net_price > 0:
                    avg_buy_price = float((pending or {}).get("avg_buy_price", 0.0) or 0.0)
                    profit = 0.0
                    if avg_buy_price > 0:
                        profit = (avg_net_price - avg_buy_price) * executed_volume
                    suffix = " (취소 상태 잔여분 정리 후 체결 반영)" if state == "cancel" else ""
                    self.log(f"✅ [{ticker}] {context_label} 체결 완료 (손익: {profit:+,.0f}원){suffix}")
                    self.add_trade_record(ticker, 'SELL', avg_net_price, executed_volume, profit, reason)
                    self.get_balance()
                    if hasattr(self, "_risk_snapshot_cache"):
                        self._risk_snapshot_cache = {"ts": 0.0, "value": None}
                else:
                    self.log(f"⚠️ [{ticker}] {context_label} 체결 정보가 유효하지 않습니다.")
                if hasattr(self.order_service, "clear_pending_if_uuid"):
                    self.order_service.clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
            elif state == 'cancel':
                if hasattr(self, "_transition_pending"):
                    self._transition_pending(ticker, "cancel", reason="external_sell_execution_cancel")
                if hasattr(self.order_service, "clear_pending_if_uuid"):
                    self.order_service.clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                self.log(f"⚠️ [{ticker}] {context_label} 주문 취소")
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, r=reason, c=context_label, rc=retry_count + 1, s=session_id: self._check_external_sell_execution(
                            t, u, r, c, rc, s
                        ),
                    )
                else:
                    used_resolver = hasattr(self, "_resolve_timeout_pending")
                    resolved = False
                    if used_resolver:
                        resolved = bool(self._resolve_timeout_pending(ticker, pending, reason="external_sell_execution_timeout"))
                    if not used_resolver and not resolved:
                        if hasattr(self.order_service, "clear_pending_if_uuid"):
                            self.order_service.clear_pending_if_uuid(ticker, uuid)
                        else:
                            self.order_service.clear_pending(ticker)
                    if not resolved:
                        self.log(f"[ERROR] [{ticker}] {context_label} 체결 확인 타임아웃")
        except Exception as e:
            if hasattr(self, "_register_manual_review"):
                self._register_manual_review(
                    ticker=ticker,
                    uuid=uuid,
                    reason=f"external_sell_execution_exception:{e}",
                    order=None,
                )
            else:
                if hasattr(self.order_service, "clear_pending_if_uuid"):
                    self.order_service.clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] [{ticker}] {context_label} 체결 확인 실패: {e}")





