from __future__ import annotations

import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import estimate_realized_slippage_bps, plan_execution
from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker
from upbit_autotrader.controllers.trading_parts.order_api.chance import _extract_chance_fee_bps
from .validation import _buy_order_has_fill, _validate_live_order_request, _market_regime_fields_dict
from .twap import _start_twap_buy

try:
    from upbit_autotrader.notifications.notifiers import EventType
except ImportError:
    EventType = None



def execute_buy(self, ticker, curr_price):
    """매수 주문"""
    if not self.upbit and not self._is_paper_mode():
        return
    self._ensure_order_stability_state()
    if self.order_service.has_pending(ticker):
        pending = self.order_service.get_pending(ticker)
        self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
        return

    info = self.universe.get(ticker, {})
    base_ratio_pct = float(self.strategy.calculate_dynamic_position_size(ticker)) if self.strategy else float(self.spin_betting.value())
    ratio = base_ratio_pct / 100.0
    cfg = self._get_strategy_runtime_config() if hasattr(self, "_get_strategy_runtime_config") else None
    candle_text = self.combo_candle.currentText() if hasattr(self, "combo_candle") else Config.DEFAULT_CANDLE
    interval = Config.CANDLE_INTERVALS.get(candle_text, "minute240")
    market_regime_fields = _market_regime_fields_dict(self._capture_market_regime_fields(info))
    snapshot = None
    if cfg and cfg.enabled and hasattr(self, "strategy_engine"):
        snapshot = self._get_indicator_snapshot(
            ticker,
            interval,
            rsi_period=self.spin_rsi_period.value(),
            volume_period=Config.DEFAULT_VOLUME_PERIOD,
            bb_period=Config.DEFAULT_BB_PERIOD,
        )
        adjusted_pct = self.strategy_engine.evaluate_position_size(ratio * 100.0, snapshot or {}, cfg)
        ratio = adjusted_pct / 100.0
    available_krw = self._get_available_krw()
    bet_cash = available_krw * ratio

    if self._use_risk_budget_sizing():
        snapshot = snapshot or self._get_indicator_snapshot(
            ticker,
            interval,
            rsi_period=self.spin_rsi_period.value(),
            volume_period=Config.DEFAULT_VOLUME_PERIOD,
            bb_period=Config.DEFAULT_BB_PERIOD,
        )
        atr_val = float(self.calculate_atr(ticker, Config.DEFAULT_ATR_PERIOD) or 0.0)
        risk_state = str(self._get_risk_snapshot(force=False).get("risk_state", "normal"))
        strategy_id = str(info.get("last_strategy_id", "legacy"))
        tracker = getattr(self, "strategy_perf_tracker", None)
        if tracker is None:
            tracker = StrategyPerformanceTracker()
            self.strategy_perf_tracker = tracker
        perf = tracker.get(strategy_id)
        equity_info = self._calculate_current_equity() if hasattr(self, "_calculate_current_equity") else {}
        equity_krw = float(equity_info.get("equity_krw", getattr(self, "initial_balance", 0.0)) or 0.0)
        sizing_out = compute_position_size(
            PositionSizingInput(
                use_risk_budget_sizing=True,
                equity_krw=equity_krw,
                available_krw=available_krw,
                current_price=float(curr_price or 0.0),
                atr_value=atr_val,
                base_betting_pct=float(base_ratio_pct),
                risk_budget_pct=self._risk_budget_pct(),
                atr_stop_mult=self._atr_stop_mult(),
                min_stop_pct=self._min_stop_pct(),
                max_betting_pct=self._max_betting_pct(),
                use_kelly_adjustment=self._use_kelly_adjustment(),
                kelly_scale=self._kelly_scale(),
                win_rate=(perf.wins / perf.sample_count) if perf.sample_count > 0 else 0.5,
                avg_win_pct=float(perf.avg_win_pct),
                avg_loss_pct=float(perf.avg_loss_pct),
                drawdown_state=risk_state,
            )
        )
        bet_cash = min(float(sizing_out.order_notional_krw), available_krw)
        info["last_sizing"] = dict(sizing_out.details)
        info["last_risk_state"] = risk_state
        info["last_stop_distance_pct"] = float(sizing_out.stop_distance_pct)
        ratio = float(sizing_out.position_ratio_pct) / 100.0
    if hasattr(self, "_apply_market_regime_risk_scaling"):
        bet_cash = min(float(self._apply_market_regime_risk_scaling(bet_cash)), available_krw)

    can_order, order_err, chance = _validate_live_order_request(self, ticker, "BUY", notional_krw=bet_cash)
    if not can_order:
        self.log(order_err)
        return

    # Orderbook Spread & Depth Guard pre-check (optional safety gate)
    use_ob_guard = bool(
        getattr(self, "_use_orderbook_guard", lambda: getattr(Config, "DEFAULT_USE_ORDERBOOK_GUARD", False))()
    )
    if use_ob_guard and not self._is_paper_mode():
        from upbit_autotrader.execution.orderbook_guard import analyze_orderbook_depth
        max_spread_bps = float(
            getattr(self, "_max_orderbook_spread_bps", lambda: getattr(Config, "DEFAULT_MAX_ORDERBOOK_SPREAD_BPS", 40.0))()
        )
        ob_list = self._api_get_orderbook(ticker, count=5) if hasattr(self, "_api_get_orderbook") else []
        if ob_list and isinstance(ob_list, list) and isinstance(ob_list[0], dict):
            ob_res = analyze_orderbook_depth(ob_list[0], notional_krw=bet_cash, side="BUY", max_spread_bps=max_spread_bps)
            if not ob_res.is_safe:
                self.log(f"[{ticker}] 호가창 가드 차단: {ob_res.reason}")
                return
    default_fee_bps = float(getattr(Config, "DEFAULT_PAPER_FEE_BPS", 5.0))
    fee_buy_bps, fee_sell_bps = _extract_chance_fee_bps(chance, default_fee_bps)
    try:
        execution_cfg = self._get_execution_config(fee_buy_bps=fee_buy_bps, fee_sell_bps=fee_sell_bps)
    except TypeError:
        execution_cfg = self._get_execution_config()
        if hasattr(execution_cfg, "fee_buy_bps"):
            execution_cfg.fee_buy_bps = fee_buy_bps
        if hasattr(execution_cfg, "fee_sell_bps"):
            execution_cfg.fee_sell_bps = fee_sell_bps
    realized_vol = float((snapshot or {}).get("realized_vol_pct", 0.0) or 0.0)
    execution_plan = plan_execution(execution_cfg, bet_cash, realized_vol_pct=realized_vol, force_mode=self._execution_mode())
    if execution_plan.blocked:
        self.log(f"[{ticker}] 실행 모델 차단: {execution_plan.reason}")
        return
    bet_cash = float(execution_plan.order_notional_krw or 0.0)
    info["last_execution_mode"] = execution_plan.mode
    info["last_execution_mode_requested"] = self._execution_mode()
    info["last_execution_mode_actual"] = execution_plan.mode
    info["last_expected_slippage_bps"] = float(execution_plan.expected_slippage_bps)
    info["last_breakeven_pct"] = float(execution_plan.breakeven_pct)
    info["last_expected_fee_buy_bps"] = float(fee_buy_bps)
    info["last_expected_fee_sell_bps"] = float(fee_sell_bps)
    if bet_cash < 5000:
        self.log(f"[{ticker}] 매수금액 부족 (최소 5,000원)")
        return
    session_id = getattr(self, "_active_session_id", 0)

    if execution_plan.mode == "twap_market" and len(execution_plan.slice_notionals) > 1:
        started = _start_twap_buy(self, ticker=ticker, curr_price=curr_price, slices=execution_plan.slice_notionals, session_id=session_id)
        if started:
            return
        self.log(f"[{ticker}] TWAP 시작 실패, 단일 시장가로 fallback")

    if execution_plan.mode == "twap_market" and len(execution_plan.slice_notionals) > 1:
        info["last_execution_mode_actual"] = "single_market"
        info["last_execution_fallback_reason"] = "twap_start_failed"

    if not self._reserve_krw_for_buy(ticker, bet_cash, session_id=session_id):
        self.log(f"[{ticker}] 사용 가능 잔고 부족 (가용: {self._get_available_krw():,.0f}원)")
        return

    try:
        ok, result, err_msg = self._place_buy_order(ticker, bet_cash, session_id=session_id, source="auto_buy")
        if ok and result and "uuid" in result:
            if hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    execution_mode=str(info.get("last_execution_mode_actual", execution_plan.mode)),
                    execution_mode_requested=str(info.get("last_execution_mode_requested", self._execution_mode())),
                    execution_mode_actual=str(info.get("last_execution_mode_actual", execution_plan.mode)),
                    execution_fallback_reason=str(info.get("last_execution_fallback_reason", "")),
                    twap_skipped_slices=0,
                    expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                    breakeven_pct=float(execution_plan.breakeven_pct),
                    expected_fee_buy_bps=float(fee_buy_bps),
                    expected_fee_sell_bps=float(fee_sell_bps),
                    strategy_score=float(info.get("last_strategy_score", 0.0) or 0.0),
                    meta_score=float(info.get("last_meta_score", 0.0) or 0.0),
                    risk_state=str(info.get("last_risk_state", "normal")),
                    **market_regime_fields,
                )
            if info:
                info["state"] = "주문중"
                self.set_table_item(info["row"], 4, "⏳ 주문중", "#ffc107")
            self.log(f"📤 [{ticker}] 매수 주문: {bet_cash:,.0f}원 ({execution_plan.mode})")
            self.logger.info(f"매수 주문: {ticker} {bet_cash:,.0f}원")
            QTimer.singleShot(2000, lambda t=ticker, u=result["uuid"], s=session_id: self.check_buy_execution(t, u, retry_count=0, session_id=s))
        else:
            self._release_reserved_krw(ticker)
            self.log(f"[ERROR] 매수 주문 실패: {err_msg} / {result}")
    except Exception as e:
        self.order_service.clear_pending(ticker)
        self._release_reserved_krw(ticker)
        self.log(f"[ERROR] 매수 주문 실패: {e}")
        self.logger.error(f"매수 주문 실패 ({ticker}): {e}")


def check_buy_execution(self, ticker, uuid, retry_count=0, session_id=None):
    """매수 체결 확인"""
    MAX_RETRIES = 30
    if hasattr(self, "_ensure_order_stability_state"):
        self._ensure_order_stability_state()
    pending = self.order_service.get_pending(ticker)
    if not pending or (pending and str(pending.get("uuid")) != str(uuid)):
        return
    clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
    release_reserved = getattr(self, "_release_reserved_krw", None)
    transition_pending = getattr(self, "_transition_pending", None)
    handle_session_mismatch = getattr(self, "_handle_session_mismatch_terminal", None)
    resolve_timeout_pending = getattr(self, "_resolve_timeout_pending", None)
    ops_alert = getattr(self, "_ops_alert", None)
    register_manual_review = getattr(self, "_register_manual_review", None)
    mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)

    try:
        order_raw = self._safe_get_order(uuid) if hasattr(self, "_safe_get_order") else self.upbit.get_order(uuid)
        order = order_raw if isinstance(order_raw, dict) else None
        state = str(order.get("state", "")).lower() if order else "wait"
        terminal_with_fill = state in ("done", "cancel") and _buy_order_has_fill(self, order)
        if pending and hasattr(self.order_service, "update_pending"):
            self.order_service.update_pending(
                ticker,
                last_checked_at=datetime.datetime.now(),
                retry_count=int(pending.get("retry_count", 0) or 0) + 1,
            )
            if callable(transition_pending):
                transition_pending(ticker, "wait", reason="buy_execution_poll")

        if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
            if state in ("done", "cancel") and callable(handle_session_mismatch):
                handle_session_mismatch(
                    ticker=ticker,
                    uuid=uuid,
                    side="BUY",
                    state=state,
                    session_id=session_id,
                    source="check_buy_execution",
                )
            return

        if terminal_with_fill:
            if callable(transition_pending):
                reason = "buy_execution_done" if state == "done" else "buy_execution_cancel_with_fill"
                transition_pending(ticker, "done", reason=reason, metadata={"raw_state": state})
            info = self.universe.get(ticker)
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
                    "market_regime_score": float((pending or {}).get("market_regime_score", (info or {}).get("last_market_regime_score", 50.0)) or 50.0),
                    "market_regime_label": str((pending or {}).get("market_regime_label", (info or {}).get("last_market_regime_label", "neutral")) or "neutral"),
                    "market_regime_ts": str((pending or {}).get("market_regime_ts", (info or {}).get("last_market_regime_ts", "")) or ""),
                }
            )
            executed_volume, total_price, avg_price = self.order_service.get_buy_fill_metrics(order)
            if executed_volume > 0 and total_price > 0:
                if info:
                    prev_qty = float(info.get("qty", 0.0) or 0.0)
                    prev_invest = float(info.get("invest_amt", 0.0) or 0.0)
                    if prev_qty > 0 and prev_invest > 0:
                        merged_qty = prev_qty + executed_volume
                        merged_invest = prev_invest + total_price
                        merged_avg = (merged_invest / merged_qty) if merged_qty > 0 else avg_price
                    else:
                        merged_qty = executed_volume
                        merged_invest = total_price
                        merged_avg = avg_price
                    info["qty"] = merged_qty
                    info["buy_price"] = merged_avg
                    info["invest_amt"] = merged_invest
                    info["high_since_buy"] = max(float(info.get("high_since_buy", 0.0) or 0.0), merged_avg)
                    info["max_profit_rate"] = 0.0
                    info.update(
                        {
                            "last_market_regime_score": market_regime_fields["market_regime_score"],
                            "last_market_regime_label": market_regime_fields["market_regime_label"],
                            "last_market_regime_ts": market_regime_fields["market_regime_ts"],
                        }
                    )
                    info.setdefault("partial_sold", [])
                    info["state"] = "보유중"
                    if self.strategy:
                        self.strategy.set_holding_start(ticker)
                        self.strategy.clear_recent_prices(ticker)
                        self.strategy.clear_partial_profit(ticker)
                    row = info["row"]
                    qty_item = info.get("ui_items", {}).get("qty")
                    if qty_item is None:
                        qty_item = QTableWidgetItem("-")
                        self.table.setItem(row, 5, qty_item)
                        info.setdefault("ui_items", {})["qty"] = qty_item
                    qty_item.setText(f"{merged_qty:.8f}")
                    buy_price_item = info.get("ui_items", {}).get("buy_price")
                    if buy_price_item is None:
                        buy_price_item = QTableWidgetItem("-")
                        self.table.setItem(row, 6, buy_price_item)
                        info.setdefault("ui_items", {})["buy_price"] = buy_price_item
                    buy_price_item.setText(f"{merged_avg:,.0f}")
                    invest_item = info.get("ui_items", {}).get("invest")
                    if invest_item is None:
                        invest_item = QTableWidgetItem("-")
                        self.table.setItem(row, 9, invest_item)
                        info.setdefault("ui_items", {})["invest"] = invest_item
                    invest_item.setText(f"{merged_invest:,.0f}")
                    self.set_table_item(row, 4, "💼 보유중", "#00b4d8")

                fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
                ref_price = float((info or {}).get("current", avg_price) or avg_price)
                realized_slippage_bps = estimate_realized_slippage_bps(ref_price, avg_price, side="buy")
                suffix = " (취소 상태 잔여분 정리 후 체결 반영)" if state == "cancel" else ""
                self.log(f"✅ [{ticker}] 매수 체결: {executed_volume:.8f} @ {avg_price:,.0f}원{suffix}")
                self.add_trade_record(
                    ticker,
                    "BUY",
                    avg_price,
                    executed_volume,
                    0,
                    "매수 체결",
                    fee_krw=fee_krw,
                    expected_slippage_bps=expected_slippage_bps,
                    realized_slippage_bps=realized_slippage_bps,
                    execution_mode=execution_mode,
                    execution_mode_requested=str((pending or {}).get("execution_mode_requested", execution_mode) or execution_mode),
                    execution_mode_actual=str((pending or {}).get("execution_mode_actual", execution_mode) or execution_mode),
                    execution_fallback_reason=str((pending or {}).get("execution_fallback_reason", "") or ""),
                    twap_skipped_slices=int((pending or {}).get("twap_skipped_slices", 0) or 0),
                    expected_fee_buy_bps=expected_fee_buy_bps,
                    expected_fee_sell_bps=expected_fee_sell_bps,
                    session_id=session_id,
                    risk_state=risk_state,
                    strategy_score=strategy_score,
                    meta_score=meta_score,
                    **market_regime_fields,
                )
                manager = getattr(self, "notification_manager", None)
                if manager is not None and EventType is not None and hasattr(manager, "notify_buy"):
                    try:
                        manager.notify_buy(ticker, avg_price, executed_volume)
                    except Exception:
                        pass
                self.get_balance()
                self._risk_snapshot_cache = {"ts": 0.0, "value": None}
            else:
                if info:
                    info["state"] = "감시중"
                    self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
                self.log(f"⚠️ [{ticker}] 매수 체결 정보가 유효하지 않습니다(수량/금액 0). 상태를 감시중으로 복원합니다.")
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(release_reserved):
                release_reserved(ticker)
            if callable(mark_reconciliation):
                mark_reconciliation()
            schedule_twap = getattr(self, "_schedule_next_twap_buy_slice", None)
            if execution_mode == "twap_market" and callable(schedule_twap):
                schedule_twap(ticker)
        elif state == "cancel":
            if callable(transition_pending):
                transition_pending(ticker, "cancel", reason="buy_execution_cancel")
            info = self.universe.get(ticker)
            if info:
                info["state"] = "감시중"
                self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
            self.log(f"⚠️ [{ticker}] 매수 주문 취소됨")
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(release_reserved):
                release_reserved(ticker)
            if callable(mark_reconciliation):
                mark_reconciliation()
            schedule_twap = getattr(self, "_schedule_next_twap_buy_slice", None)
            if str((pending or {}).get("execution_mode", "")) == "twap_market" and callable(schedule_twap):
                schedule_twap(ticker)
        else:
            if retry_count < MAX_RETRIES:
                QTimer.singleShot(2000, lambda t=ticker, u=uuid, rc=retry_count + 1, s=session_id: self.check_buy_execution(t, u, rc, s))
            else:
                self.log(f"[ERROR] [{ticker}] 매수 체결 확인 타임아웃 (60초)")
                self.logger.error(f"매수 체결 확인 타임아웃: {ticker}, uuid={uuid}")
                info = self.universe.get(ticker)
                if info:
                    info["state"] = "체결확인실패"
                    self.set_table_item(info["row"], 4, "❓ 확인필요", "#ffc107")
                if callable(resolve_timeout_pending):
                    resolved = resolve_timeout_pending(ticker=ticker, pending=pending, reason="buy_execution_timeout")
                else:
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    if callable(release_reserved):
                        release_reserved(ticker)
                    resolved = True
                if not resolved and callable(ops_alert):
                    ops_alert(
                        level="warning",
                        message=f"⚠️ [{ticker}] 매수 주문 타임아웃 unresolved - 수동검토 필요",
                        key=f"buy_timeout_unresolved:{uuid}",
                        cooldown=30,
                    )
    except Exception as e:
        if callable(register_manual_review):
            register_manual_review(ticker=ticker, uuid=uuid, reason=f"buy_execution_exception:{e}", order=None)
        elif callable(clear_pending_if_uuid):
            clear_pending_if_uuid(ticker, uuid)
        else:
            self.order_service.clear_pending(ticker)
        if callable(release_reserved):
            release_reserved(ticker)
        self.logger.error(f"체결 확인 실패 ({ticker}): {e}")
