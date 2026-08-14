from __future__ import annotations

import datetime
import time
from typing import Optional

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMessageBox

from upbit_autotrader.core.config import Config
from upbit_autotrader.runtime.market_regime_thread import MarketRegimeThread
from upbit_autotrader.runtime.price_thread import PriceUpdateThread


def _create_price_thread(self):
    self.price_thread = PriceUpdateThread(parent=self)
    self.price_thread.price_updated.connect(self.on_price_update)
    if hasattr(self, "_handle_ws_order_event"):
        self.price_thread.order_event_received.connect(self._handle_ws_order_event)
    if hasattr(self, "_handle_ws_asset_event"):
        self.price_thread.asset_event_received.connect(self._handle_ws_asset_event)


def _restart_price_thread(self, coins):
    if hasattr(self, "price_thread") and self.price_thread is not None:
        if self.price_thread.isRunning():
            self.price_thread.stop()
            self.price_thread.wait(2000)
        if self.price_thread.isFinished():
            _create_price_thread(self)
    else:
        _create_price_thread(self)
    if self.price_thread is not None:
        self.price_thread.set_coins(coins)
        self.price_thread.start()


def _create_market_regime_thread(self):
    cfg = self._get_market_regime_config() if hasattr(self, "_get_market_regime_config") else {}
    thread = MarketRegimeThread(
        refresh_sec=int(cfg.get("market_regime_refresh_sec", getattr(Config, "DEFAULT_MARKET_REGIME_REFRESH_SEC", 60))),
        top_n=int(cfg.get("market_regime_top_n", getattr(Config, "DEFAULT_MARKET_REGIME_TOP_N", 20))),
        use_fear_greed=bool(cfg.get("market_regime_use_fear_greed", getattr(Config, "DEFAULT_MARKET_REGIME_USE_FEAR_GREED", True))),
        use_etf_flow=bool(cfg.get("market_regime_use_etf_flow", getattr(Config, "DEFAULT_MARKET_REGIME_USE_ETF_FLOW", False))),
        parent=self,
    )
    thread.regime_updated.connect(self._on_market_regime_update)
    self.market_regime_thread = thread


def _stop_market_regime_thread(self):
    thread = getattr(self, "market_regime_thread", None)
    if thread is None:
        return
    if thread.isRunning():
        thread.stop()
        thread.wait(2000)


def _restart_market_regime_thread(self):
    _stop_market_regime_thread(self)
    _create_market_regime_thread(self)
    thread = getattr(self, "market_regime_thread", None)
    if thread is not None:
        thread.start()


def on_timer_tick(self):
    now = datetime.datetime.now()
    self.status_time.setText(now.strftime("%Y-%m-%d %H:%M:%S"))

    if not hasattr(self, "_last_reset_date"):
        self._last_reset_date = now.date()
    if now.date() != self._last_reset_date:
        self._last_reset_date = now.date()
        _reset_daily_stats(self)

    if self.is_running and hasattr(self, "_ensure_order_stability_state"):
        self._ensure_order_stability_state()
        stale_limit = self._price_feed_stale_sec() if hasattr(self, "_price_feed_stale_sec") else float(getattr(Config, "DEFAULT_PRICE_FEED_STALE_SEC", 15))
        last_tick_ts = float(getattr(self, "_last_price_update_ts", 0.0) or 0.0)
        if stale_limit > 0 and last_tick_ts > 0 and (time.time() - last_tick_ts) > stale_limit:
            self._ops_alert(
                level="warning",
                message=f"⚠️ 가격 피드 stale 감지 ({stale_limit:.0f}초 초과)",
                key="price_feed_stale",
                cooldown=max(5.0, stale_limit / 2.0),
            )
            if not getattr(self, "_price_feed_recovery_attempted", False):
                self._price_feed_recovery_attempted = True
                if hasattr(self, "_restart_price_thread"):
                    try:
                        self._restart_price_thread(list(getattr(self, "universe", {}).keys()))
                        self._ops_alert(level="info", message="🔄 가격 피드 스레드 재시작 시도", key="price_feed_restart", cooldown=10)
                    except Exception as e:
                        self._ops_alert(level="error", message=f"❌ 가격 피드 스레드 재시작 실패: {e}", key="price_feed_restart_error", cooldown=20)


def _reset_daily_stats(self):
    self.daily_loss_triggered = False
    self.total_realized_profit = 0
    self.trade_count = 0
    self.win_count = 0
    self.lbl_total_profit.setText("📈 당일 실현손익: 0원")
    self._update_statistics()
    self.log("📅 일일 통계 초기화 (자정)")
    self.logger.info("일일 통계 초기화")


def closeEvent(self, a0: Optional[QCloseEvent]):
    if a0 is None:
        return
    if self.system_settings.get("minimize_to_tray", True) and self.isVisible():
        a0.ignore()
        self.hide()
        self.send_notification("Upbit Pro Trader", "트레이로 최소화되었습니다. 더블클릭으로 다시 열 수 있습니다.")
        return

    if self.is_running:
        reply = QMessageBox.question(
            self,
            "종료 확인",
            "매매가 진행 중입니다. 정말 종료하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            a0.ignore()
            return

    self.save_settings()
    if hasattr(self, "_flush_trade_history"):
        self._flush_trade_history()
    self.save_trade_history()
    if hasattr(self, "_reconcile_pending_orders"):
        self._reconcile_pending_orders(force=True)
    if hasattr(self, "_persist_reconciliation_state"):
        self._persist_reconciliation_state(force=True)
    try:
        if hasattr(self, "strategy_perf_tracker"):
            self.strategy_perf_tracker.save(getattr(Config, "STRATEGY_PERF_FILE", "strategy_performance.json"))
    except Exception:
        pass

    _stop_market_regime_thread(self)
    self.price_thread.stop()
    self.price_thread.wait(2000)
    self.tray_icon.hide()
    self.logger.info("프로그램 종료")
    a0.accept()
