from __future__ import annotations

import time

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config
from upbit_autotrader.core.entry_filter import should_enter_by_score
from upbit_autotrader.strategies.meta_signal import MetaSignalInput, StrategyPerformanceTracker, evaluate_meta_signal


def calculate_entry_score(self, ticker, curr_price, info, snapshot=None):
    """진입 점수 계산 (0~100점)"""
    score = 0
    reasons = []
    weights = Config.ENTRY_WEIGHTS
    interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
    if snapshot is None:
        snapshot = self._get_indicator_snapshot(
            ticker,
            interval,
            rsi_period=self.spin_rsi_period.value(),
            volume_period=Config.DEFAULT_VOLUME_PERIOD,
            bb_period=Config.DEFAULT_BB_PERIOD,
        )

    if curr_price >= info["target"]:
        score += weights["target_break"]
        reasons.append(f"+{weights['target_break']} 목표가 돌파")

    if curr_price >= info["ma5"]:
        score += weights["ma_filter"]
        reasons.append(f"+{weights['ma_filter']} MA5 위")

    if self.chk_use_rsi.isChecked():
        rsi = snapshot.get("rsi", 50) if snapshot else 50
        if 30 <= rsi <= 70:
            score += weights["rsi_optimal"]
            reasons.append(f"+{weights['rsi_optimal']} RSI {rsi:.1f} (최적)")
        elif rsi < 30:
            score += weights["rsi_optimal"] // 2
            reasons.append(f"+{weights['rsi_optimal'] // 2} RSI {rsi:.1f} (과매도)")
    else:
        score += weights["rsi_optimal"]

    if hasattr(self, "chk_use_macd") and self.chk_use_macd.isChecked():
        if snapshot:
            macd = snapshot.get("macd", 0)
            signal = snapshot.get("signal", 0)
        else:
            macd, signal, _ = self.calculate_macd(ticker)
        if macd > signal:
            score += weights["macd_golden"]
            reasons.append(f"+{weights['macd_golden']} MACD 골든크로스")
    else:
        score += weights["macd_golden"]

    if self.chk_use_volume.isChecked():
        if snapshot:
            curr_vol = snapshot.get("current_volume")
            avg_vol = snapshot.get("avg_volume")
        else:
            curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
        if curr_vol and avg_vol:
            required_vol = avg_vol * self.spin_volume_mult.value()
            if curr_vol >= required_vol:
                score += weights["volume_confirm"]
                reasons.append(f"+{weights['volume_confirm']} 거래량 충분")
    else:
        score += weights["volume_confirm"]

    if snapshot:
        upper = snapshot.get("bb_upper")
        middle = snapshot.get("bb_middle")
        lower = snapshot.get("bb_lower")
    else:
        upper, middle, lower = self.calculate_bollinger_bands(ticker)
    if lower and middle:
        if lower <= curr_price <= middle:
            score += weights["bb_position"]
            reasons.append(f"+{weights['bb_position']} BB 최적 구간")
        elif middle < curr_price <= upper:
            score += weights["bb_position"] // 2
            reasons.append(f"+{weights['bb_position'] // 2} BB 중상단")

    return score, reasons


def on_price_update(self, prices):
    """실시간 가격 업데이트"""
    if not self.is_running:
        return
    self._ensure_order_stability_state()
    if prices:
        self._last_price_update_ts = time.time()
        self._price_feed_recovery_attempted = False

    self.table.setUpdatesEnabled(False)
    try:
        for ticker, price in prices.items():
            if ticker not in self.universe:
                continue

            info = self.universe[ticker]
            info["current"] = price

            if self.strategy:
                self.strategy.update_recent_price(ticker, price)

            price_item = info.get("ui_items", {}).get("price")
            if price_item is None:
                price_item = QTableWidgetItem("-")
                self.table.setItem(info["row"], 1, price_item)
                info.setdefault("ui_items", {})["price"] = price_item
            price_item.setText(f"{price:,.0f}")

            if info["state"] == "감시중" and info["qty"] == 0:
                _check_buy_condition(self, ticker, price, info)
            elif info["state"] == "보유중" and info["qty"] > 0:
                _check_sell_condition(self, ticker, price, info)
    finally:
        self.table.setUpdatesEnabled(True)


def _check_buy_condition(self, ticker, curr, info):
    """매수 조건 확인"""
    if self.strategy:
        if not self.strategy.check_cooldown(ticker):
            return
        if not self.strategy.check_mtf_condition(ticker):
            return

    cfg = self._get_strategy_runtime_config() if hasattr(self, "_get_strategy_runtime_config") else None
    hard_gate_enabled = self._should_apply_legacy_entry_gate(cfg)

    if hard_gate_enabled:
        if curr < info["target"]:
            return
        if curr < info["ma5"]:
            return

    if hard_gate_enabled and self.strategy and hasattr(self, "chk_use_breakout_confirm") and self.chk_use_breakout_confirm.isChecked():
        confirm_ticks = self.spin_breakout_ticks.value() if hasattr(self, "spin_breakout_ticks") else None
        if not self.strategy.check_breakout_confirmation(ticker, info["target"], confirm_ticks):
            return

    interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
    need_snapshot = (
        self.chk_use_rsi.isChecked()
        or (hasattr(self, "chk_use_macd") and self.chk_use_macd.isChecked())
        or self.chk_use_volume.isChecked()
        or self.chk_use_entry_scoring.isChecked()
        or (hasattr(self, "chk_use_strategy_engine") and self.chk_use_strategy_engine.isChecked())
    )
    snapshot = None
    if need_snapshot:
        snapshot = self._get_indicator_snapshot(
            ticker,
            interval,
            rsi_period=self.spin_rsi_period.value(),
            volume_period=Config.DEFAULT_VOLUME_PERIOD,
            bb_period=Config.DEFAULT_BB_PERIOD,
        )

    if self.chk_use_rsi.isChecked():
        rsi = snapshot.get("rsi", 50) if snapshot else self.calculate_rsi(ticker, self.spin_rsi_period.value())
        if rsi >= self.spin_rsi_upper.value():
            self.log(f"[{ticker}] RSI {rsi:.1f} >= {self.spin_rsi_upper.value()} (과매수) 진입 보류")
            return

    if hasattr(self, "chk_use_macd") and self.chk_use_macd.isChecked():
        if snapshot:
            macd = snapshot.get("macd", 0)
            signal = snapshot.get("signal", 0)
        else:
            macd, signal, _ = self.calculate_macd(ticker)
        if macd <= signal:
            self.log(f"[{ticker}] MACD {macd:.2f} <= Signal {signal:.2f} (하락세) 진입 보류")
            return

    if self.chk_use_volume.isChecked():
        if snapshot:
            curr_vol = snapshot.get("current_volume")
            avg_vol = snapshot.get("avg_volume")
        else:
            curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
        if curr_vol and avg_vol:
            required_vol = avg_vol * self.spin_volume_mult.value()
            if curr_vol < required_vol:
                self.log(f"[{ticker}] 거래량 부족 ({curr_vol:,.0f} < {required_vol:,.0f}) 진입 보류")
                return

    if not self.check_risk_limits():
        return

    # Orderbook Spread Guard
    use_ob_guard = bool(getattr(self, "chk_use_orderbook_guard", None) and self.chk_use_orderbook_guard.isChecked())
    if use_ob_guard and hasattr(self, "_api_get_orderbook"):
        try:
            from upbit_autotrader.execution.orderbook_guard import analyze_orderbook_depth
            ob_list = self._api_get_orderbook(ticker, count=5)
            if ob_list and isinstance(ob_list, list):
                max_spread = float(self.spin_max_orderbook_spread_bps.value()) if hasattr(self, "spin_max_orderbook_spread_bps") else 40.0
                ob_res = analyze_orderbook_depth(ob_list[0], notional_krw=0.0, side="BUY", max_spread_bps=max_spread)
                if not ob_res.is_safe:
                    self.log(f"[{ticker}] 호가창 가드 보류: {ob_res.reason}")
                    return
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"[{ticker}] 호가창 가드 검사 예외: {e}")

    score = None
    if self.chk_use_entry_scoring.isChecked():
        score, reasons = calculate_entry_score(self, ticker, curr, info, snapshot=snapshot)
        threshold = self.spin_entry_score_threshold.value()
        if not should_enter_by_score(True, score, threshold):
            reason_summary = ", ".join(reasons[:3]) if reasons else "점수 근거 없음"
            self.log(f"[{ticker}] 진입 점수 {score:.0f} < {threshold} 진입 보류 (근거: {reason_summary})")
            return

    strategy_signal = None
    strategy_id = "legacy"
    if cfg and cfg.enabled and hasattr(self, "strategy_engine"):
        snapshot = snapshot or self._get_indicator_snapshot(
            ticker,
            interval,
            rsi_period=self.spin_rsi_period.value(),
            volume_period=Config.DEFAULT_VOLUME_PERIOD,
            bb_period=Config.DEFAULT_BB_PERIOD,
        )
        strategy_signal = self.strategy_engine.evaluate_entry(ticker, curr, info, snapshot or {}, cfg)
        if strategy_signal.action != "BUY":
            reason_text = ", ".join(strategy_signal.reasons[:2]) if strategy_signal.reasons else "전략 점수 미충족"
            self.log(f"[{ticker}] 전략 엔진 보류: {reason_text}")
            return
        score = strategy_signal.score
        strategy_id = str(strategy_signal.strategy_id or "engine")
    elif cfg and cfg.enabled:
        strategy_id = str(cfg.single_strategy if str(cfg.mode) == "single" else "ensemble")
    elif score is not None:
        strategy_id = "entry_scoring"

    market_regime_fields = self._capture_market_regime_fields(info)
    market_regime_score = float(market_regime_fields["market_regime_score"])
    if hasattr(self, "_apply_market_regime_filter") and not self._apply_market_regime_filter(ticker):
        return

    meta_signal = None
    if self._use_meta_signal():
        self._ensure_order_stability_state()
        tracker = getattr(self, "strategy_perf_tracker", None)
        if tracker is None:
            tracker = StrategyPerformanceTracker()
            self.strategy_perf_tracker = tracker
        adx = float((snapshot or {}).get("adx", 20.0) or 20.0)
        realized_vol = float((snapshot or {}).get("realized_vol_pct", 0.0) or 0.0)
        technical_regime_score = max(
            0.0,
            min(100.0, (adx / 40.0) * 100.0 - max(0.0, realized_vol - 5.0) * 2.0),
        )
        meta_signal = evaluate_meta_signal(
            MetaSignalInput(
                strategy_id=strategy_id,
                engine_score=float(score if score is not None else 50.0),
                technical_regime_score=technical_regime_score,
                market_regime_score=market_regime_score,
                min_expectancy=self._meta_min_expectancy(),
                score_threshold=self._meta_score_threshold(),
            ),
            tracker=tracker,
        )
        if not bool(meta_signal.gate_pass):
            self.log(
                f"[{ticker}] 메타 시그널 보류: meta={meta_signal.meta_score:.1f}, "
                f"expectancy={meta_signal.expected_value:.2f}"
            )
            return

    info["last_strategy_id"] = strategy_id
    info["last_strategy_score"] = float(score if score is not None else 0.0)
    if meta_signal is not None:
        info["last_meta_score"] = float(meta_signal.meta_score)
        info["last_expectancy"] = float(meta_signal.expected_value)
    if score is None:
        self.log(f"[{ticker}] 진입 조건 충족")
    else:
        self.log(f"[{ticker}] 진입 조건 충족 (점수: {score:.0f})")
    self.execute_buy(ticker, curr)


def _check_sell_condition(self, ticker, curr, info):
    """매도 조건 확인"""
    buy_p = info["buy_price"]
    if buy_p == 0:
        return

    profit_rate = (curr - buy_p) / buy_p * 100
    if curr > info["high_since_buy"]:
        info["high_since_buy"] = curr
        info["max_profit_rate"] = profit_rate

    row = info["row"]
    profit_item = info.get("ui_items", {}).get("profit")
    if profit_item is None:
        profit_item = QTableWidgetItem("-")
        self.table.setItem(row, 7, profit_item)
        info.setdefault("ui_items", {})["profit"] = profit_item
    profit_item.setText(f"{profit_rate:.2f}%")
    if profit_rate >= 0:
        profit_item.setForeground(QColor("#e63946"))
    else:
        profit_item.setForeground(QColor("#4361ee"))

    max_profit_item = info.get("ui_items", {}).get("max_profit")
    if max_profit_item is None:
        max_profit_item = QTableWidgetItem("-")
        self.table.setItem(row, 8, max_profit_item)
        info.setdefault("ui_items", {})["max_profit"] = max_profit_item
    max_profit_item.setText(f"{info['max_profit_rate']:.2f}%")

    loss_limit = -self.spin_loss.value()
    if profit_rate <= loss_limit:
        self.log(f"🛑 [{ticker}] 손절 조건 ({profit_rate:.2f}%) → 매도")
        self.execute_sell(ticker, "손절")
        return

    if self.strategy and hasattr(self, "spin_max_holding_hours"):
        if self.strategy.check_holding_time_exit(ticker, self.spin_max_holding_hours.value()):
            self.execute_sell(ticker, "시간청산")
            return

    cfg = self._get_strategy_runtime_config() if hasattr(self, "_get_strategy_runtime_config") else None
    if cfg and cfg.enabled and hasattr(self, "strategy_engine"):
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = self._get_indicator_snapshot(
            ticker,
            interval,
            rsi_period=self.spin_rsi_period.value(),
            volume_period=Config.DEFAULT_VOLUME_PERIOD,
            bb_period=Config.DEFAULT_BB_PERIOD,
        )
        signal = self.strategy_engine.evaluate_exit(ticker, curr, info, snapshot or {}, cfg)
        if signal.action == "SELL":
            reason = signal.reasons[0] if signal.reasons else "전략청산"
            self.log(f"📉 [{ticker}] 전략 청산 신호 ({signal.strategy_id})")
            self.execute_sell(ticker, f"전략:{reason}")
            return

    if hasattr(self, "chk_use_partial_tp") and self.chk_use_partial_tp.isChecked():
        partial_sold = info.get("partial_sold", [])
        for level in Config.PARTIAL_TAKE_PROFIT:
            rate = level["rate"]
            sell_ratio = level["sell_ratio"]
            if rate in partial_sold:
                continue
            if profit_rate >= rate and sell_ratio > 0:
                partial_qty = info["qty"] * (sell_ratio / 100)
                if partial_qty * curr >= 5000:
                    if self._execute_partial_sell(ticker, partial_qty, f"분할익절 {rate}%", level=rate):
                        self.log(f"💰 [{ticker}] {rate}% 도달 → {sell_ratio}% 분할 익절")
                        return

    ts_start = self.spin_ts_start.value()
    ts_stop = self.spin_ts_stop.value()
    if info["max_profit_rate"] >= ts_start:
        drop = (info["high_since_buy"] - curr) / info["high_since_buy"] * 100
        if drop >= ts_stop:
            self.log(f"🎯 [{ticker}] 트레일링 스톱 (고점 대비 -{drop:.2f}%) → 이익 실현")
            self.execute_sell(ticker, "TS")
