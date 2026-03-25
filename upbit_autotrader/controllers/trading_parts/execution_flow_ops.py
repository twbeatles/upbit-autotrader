from __future__ import annotations

import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import estimate_realized_slippage_bps, plan_execution
from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker

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
        market_regime_fields = self._resolve_market_regime_fields(info=info)
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
    market_regime_fields = self._capture_market_regime_fields(info)
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
        sizing_out = compute_position_size(
            PositionSizingInput(
                use_risk_budget_sizing=True,
                equity_krw=float(getattr(self, "initial_balance", 0.0) or 0.0),
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

    execution_cfg = self._get_execution_config()
    realized_vol = float((snapshot or {}).get("realized_vol_pct", 0.0) or 0.0)
    execution_plan = plan_execution(execution_cfg, bet_cash, realized_vol_pct=realized_vol, force_mode=self._execution_mode())
    if execution_plan.blocked:
        self.log(f"[{ticker}] 실행 모델 차단: {execution_plan.reason}")
        return
    bet_cash = float(execution_plan.order_notional_krw or 0.0)
    info["last_execution_mode"] = execution_plan.mode
    info["last_expected_slippage_bps"] = float(execution_plan.expected_slippage_bps)
    info["last_breakeven_pct"] = float(execution_plan.breakeven_pct)
    if bet_cash < 5000:
        self.log(f"[{ticker}] 매수금액 부족 (최소 5,000원)")
        return
    session_id = getattr(self, "_active_session_id", 0)

    if execution_plan.mode == "twap_market" and len(execution_plan.slice_notionals) > 1:
        started = _start_twap_buy(self, ticker=ticker, curr_price=curr_price, slices=execution_plan.slice_notionals, session_id=session_id)
        if started:
            return
        self.log(f"[{ticker}] TWAP 시작 실패, 단일 시장가로 fallback")

    if not self._reserve_krw_for_buy(ticker, bet_cash, session_id=session_id):
        self.log(f"[{ticker}] 사용 가능 잔고 부족 (가용: {self._get_available_krw():,.0f}원)")
        return

    try:
        ok, result, err_msg = self._place_buy_order(ticker, bet_cash, session_id=session_id, source="auto_buy")
        if ok and result and "uuid" in result:
            if hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    execution_mode=str(execution_plan.mode),
                    expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                    breakeven_pct=float(execution_plan.breakeven_pct),
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

        if state == "done":
            if callable(transition_pending):
                transition_pending(ticker, "done", reason="buy_execution_done")
            info = self.universe.get(ticker)
            execution_mode = str((pending or {}).get("execution_mode", "single_market") or "single_market")
            expected_slippage_bps = float((pending or {}).get("expected_slippage_bps", 0.0) or 0.0)
            strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
            meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
            risk_state = str((pending or {}).get("risk_state", "normal") or "normal")
            resolve_market_regime_fields = getattr(self, "_resolve_market_regime_fields", None)
            market_regime_fields = (
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
                self.log(f"✅ [{ticker}] 매수 체결: {executed_volume:.8f} @ {avg_price:,.0f}원")
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
    market_regime_fields = self._capture_market_regime_fields(info)
    exec_cfg = self._get_execution_config()
    execution_plan = plan_execution(exec_cfg, notional, realized_vol_pct=0.0, force_mode=self._execution_mode())
    if execution_plan.mode == "twap_market":
        self.log(f"[{ticker}] 매도 TWAP는 현재 단일 시장가로 실행합니다.")

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
    market_regime_fields = self._capture_market_regime_fields(info)
    exec_cfg = self._get_execution_config()
    execution_plan = plan_execution(exec_cfg, notional, realized_vol_pct=0.0, force_mode=self._execution_mode())
    if execution_plan.mode == "twap_market":
        self.log(f"[{ticker}] 분할익절 TWAP는 현재 단일 시장가로 실행합니다.")

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

        if state == "done":
            self._transition_pending(ticker, "done", reason="partial_sell_execution_done")
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
            strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
            meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
            risk_state = str((pending or {}).get("risk_state", "normal") or "normal")
            resolve_market_regime_fields = getattr(self, "_resolve_market_regime_fields", None)
            market_regime_fields = (
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
            self.log(f"✅ [{ticker}] 분할 매도 체결 (손익: {profit:+,.0f}원)")
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

        if state == "done":
            if callable(transition_pending):
                transition_pending(ticker, "done", reason="sell_execution_done")
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
            strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
            meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
            risk_state = str((pending or {}).get("risk_state", "normal") or "normal")
            resolve_market_regime_fields = getattr(self, "_resolve_market_regime_fields", None)
            market_regime_fields = (
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

            buy_amount = info["invest_amt"]
            profit = sell_amount - buy_amount
            self.total_realized_profit += profit
            self.trade_count += 1
            if profit > 0:
                self.win_count += 1
            self.lbl_total_profit.setText(f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원")
            info["qty"] = 0
            info["state"] = "감시중"
            info["buy_price"] = 0
            info["invest_amt"] = 0
            info["high_since_buy"] = 0
            info["max_profit_rate"] = 0.0
            info["partial_sold"] = []
            self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
            qty_item = info.get("ui_items", {}).get("qty")
            if qty_item is not None:
                qty_item.setText("0.00000000")
            buy_price_item = info.get("ui_items", {}).get("buy_price")
            if buy_price_item is not None:
                buy_price_item.setText("-")
            invest_item = info.get("ui_items", {}).get("invest")
            if invest_item is not None:
                invest_item.setText("-")
            profit_item = info.get("ui_items", {}).get("profit")
            if profit_item is not None:
                profit_item.setText("-")
            max_profit_item = info.get("ui_items", {}).get("max_profit")
            if max_profit_item is not None:
                max_profit_item.setText("-")

            if self.strategy:
                self.strategy.update_consecutive_results(profit > 0)
                self.strategy.clear_holding_start(ticker)
                self.strategy.clear_partial_profit(ticker)
                if hasattr(self, "chk_use_cooldown") and self.chk_use_cooldown.isChecked():
                    cooldown_minutes = self.spin_cooldown.value() if hasattr(self, "spin_cooldown") else None
                    self.strategy.set_cooldown(ticker, cooldown_minutes)

            fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
            realized_slippage_bps = estimate_realized_slippage_bps(float(info.get("current", trades_price) or trades_price), trades_price, side="sell")
            self.log(f"✅ [{ticker}] 매도 체결 (손익: {profit:+,.0f}원)")
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
                session_id=session_id,
                risk_state=risk_state,
                strategy_score=strategy_score,
                meta_score=meta_score,
                **market_regime_fields,
            )
            manager = getattr(self, "notification_manager", None)
            if manager is not None and EventType is not None and hasattr(manager, "notify_sell"):
                try:
                    pnl_pct = (profit / buy_amount * 100.0) if buy_amount > 0 else 0.0
                    manager.notify_sell(ticker, trades_price, executed_volume, pnl_pct, reason=reason)
                except Exception:
                    pass

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
