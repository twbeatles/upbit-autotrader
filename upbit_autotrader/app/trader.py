"""
Upbit Pro Algo-Trader v3.1
Facade entrypoint for modularized trading controllers.
"""

import datetime
import logging
import sys
import time
from pathlib import Path

try:
    import pyupbit  # noqa: F401
    import pandas as pd  # noqa: F401
except ImportError:
    print("pyupbit library is required. Install it with: pip install pyupbit")
    sys.exit(1)

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from upbit_autotrader.core.config import Config
from upbit_autotrader.services.order_service import UpbitOrderService
from upbit_autotrader.services.paper_order_service import UpbitPaperOrderService
from upbit_autotrader.runtime.price_thread import PriceUpdateThread
from upbit_autotrader.strategies.engine import StrategyEngine
from upbit_autotrader.execution.reconciliation_store import ReconciliationStore
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker
from upbit_autotrader.controllers.batch_controller import TraderBatchController
from upbit_autotrader.controllers.history_controller import TraderHistoryController
from upbit_autotrader.controllers.settings_controller import TraderSettingsController
from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.controllers.ui_controller import TraderUIController

try:
    from upbit_autotrader.strategies.legacy_strategy import UpbitStrategyManager
    STRATEGY_MODULE_AVAILABLE = True
except ImportError:
    UpbitStrategyManager = None
    STRATEGY_MODULE_AVAILABLE = False


class UpbitProTrader(
    TraderUIController,
    TraderSettingsController,
    TraderHistoryController,
    TraderTradingController,
    TraderBatchController,
    QMainWindow,
):
    def __init__(self):
        super().__init__()
        
        # 내부 변수 초기화
        self.upbit = None
        self.universe = {}
        self.balance = 0
        self.initial_balance = 0
        self.total_realized_profit = 0
        self.trade_count = 0
        self.win_count = 0
        self.is_running = False
        self.is_connected = False
        self.daily_loss_triggered = False
        self.order_service = UpbitOrderService()
        self.pending_orders = self.order_service.pending_orders
        self.paper_order_service = UpbitPaperOrderService(
            fee_rate=Config.DEFAULT_PAPER_FEE_BPS / 10000.0,
            slippage_bps=Config.DEFAULT_PAPER_SLIPPAGE_BPS,
        )
        self.strategy_engine = StrategyEngine(self)
        self._active_session_id = 0
        self._reserved_krw_by_ticker = {}
        self._order_error_log_ts = {}
        self._manual_review_queue = {}
        self._orphan_events = []
        self._ops_alert_last_ts = {}
        self._api_last_call_ts = 0.0
        self._risk_snapshot_cache = {"ts": 0.0, "value": None}
        self._last_price_update_ts = 0.0
        self._price_feed_recovery_attempted = False
        self.persist_reconciliation_state = bool(getattr(Config, "DEFAULT_PERSIST_RECONCILIATION_STATE", False))
        self.reconciliation_store = ReconciliationStore(getattr(Config, "RECONCILIATION_STATE_FILE", "reconciliation_state.json"))
        self._reconciliation_dirty = False
        self.strategy_perf_tracker = StrategyPerformanceTracker.load(
            getattr(Config, "STRATEGY_PERF_FILE", "strategy_performance.json")
        )
        
        # 시스템 설정 초기화
        self.system_settings = {
            'minimize_to_tray': True,
            'show_tray_notifications': True,
            'run_at_startup': False,
            'start_minimized': False,
            'auto_connect': False,
            'sound_enabled': False
        }
        
        # v3.0: 전략 매니저 초기화
        if STRATEGY_MODULE_AVAILABLE:
            self.strategy = UpbitStrategyManager(self)
            self.logger_main = logging.getLogger('UpbitTrader')
            self.logger_main.info("v3.0 전략 매니저 로드됨")
        else:
            self.strategy = None
        
        # v3.0: 고급 기능 설정 초기화
        self.advanced_settings = {
            'use_cooldown': False,
            'cooldown_minutes': 30,
            'use_time_exit': False,
            'max_holding_hours': 24,
            'use_dynamic_position': False,
            'use_mtf': False,
            'use_gap_analysis': False,
            'use_breakout_confirm': False,
            'breakout_confirm_ticks': 3,
        }
        
        # v2.5 신규: 거래 히스토리
        self.trade_history = []
        self.load_trade_history()
        
        # 가격 갱신 스레드
        self._create_price_thread()
        
        # 로깅 설정
        self.setup_logging()
        
        # UI 초기화
        self.init_ui()
        
        # 메뉴바 설정
        self.create_menu_bar()
        
        # 시스템 트레이 설정
        self.setup_tray()
        
        # 타이머 설정
        self.setup_timers()
        
        # 설정 불러오기
        self.load_settings()
        if hasattr(self, "_load_reconciliation_state"):
            self._load_reconciliation_state()
        
        # 처음 실행 확인
        self.check_first_run()
        
        self.logger.info("프로그램 초기화 완료 (v3.0)")
    def _create_price_thread(self):
        self.price_thread = PriceUpdateThread()
        self.price_thread.price_updated.connect(self.on_price_update)
    def _restart_price_thread(self, coins):
        if hasattr(self, 'price_thread') and self.price_thread is not None:
            if self.price_thread.isRunning():
                self.price_thread.stop()
                self.price_thread.wait(2000)
            if self.price_thread.isFinished():
                self._create_price_thread()
        else:
            self._create_price_thread()
        self.price_thread.set_coins(coins)
        self.price_thread.start()

    def setup_logging(self):
        """로깅 시스템 설정"""
        log_dir = Path(Config.LOG_DIR)
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"upbit_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        
        self.logger = logging.getLogger('UpbitTrader')
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def setup_timers(self):
        """타이머 설정"""
        self.timer_monitor = QTimer(self)
        self.timer_monitor.start(1000)
        self.timer_monitor.timeout.connect(self.on_timer_tick)
        self.timer_pending_reconcile = QTimer(self)
        self.timer_pending_reconcile.start(Config.PENDING_RECONCILE_INTERVAL_MS)
        self.timer_pending_reconcile.timeout.connect(lambda: self._reconcile_pending_orders(force=False))
        self.timer_reconciliation_persist = QTimer(self)
        self.timer_reconciliation_persist.start(
            int(getattr(Config, "RECONCILIATION_PERSIST_INTERVAL_MS", 5000))
        )
        self.timer_reconciliation_persist.timeout.connect(
            lambda: self._persist_reconciliation_state(force=False)
            if hasattr(self, "_persist_reconciliation_state")
            else None
        )

    def on_timer_tick(self):
        """1초마다 실행"""
        now = datetime.datetime.now()
        self.status_time.setText(now.strftime("%Y-%m-%d %H:%M:%S"))
        
        # v2.7: 자정 일일 통계 초기화
        if not hasattr(self, '_last_reset_date'):
            self._last_reset_date = now.date()
        
        if now.date() != self._last_reset_date:
            self._last_reset_date = now.date()
            self._reset_daily_stats()

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
                            self._ops_alert(
                                level="info",
                                message="🔄 가격 피드 스레드 재시작 시도",
                                key="price_feed_restart",
                                cooldown=10,
                            )
                        except Exception as e:
                            self._ops_alert(
                                level="error",
                                message=f"❌ 가격 피드 스레드 재시작 실패: {e}",
                                key="price_feed_restart_error",
                                cooldown=20,
                            )

    def _reset_daily_stats(self):
        """일일 통계 초기화 (자정 자동 실행)"""
        self.daily_loss_triggered = False
        self.total_realized_profit = 0
        self.trade_count = 0
        self.win_count = 0
        
        # UI 업데이트
        self.lbl_total_profit.setText("📈 당일 실현손익: 0원")
        self._update_statistics()
        
        self.log("📅 일일 통계 초기화 (자정)")
        self.logger.info("일일 통계 초기화")

    # ------------------------------------------------------------------
    # 설정 저장/불러오기
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        """종료 처리"""
        # 트레이로 최소화 옵션 확인
        if self.system_settings.get('minimize_to_tray', True) and self.isVisible():
            event.ignore()
            self.hide()
            self.send_notification("Upbit Pro Trader", "트레이로 최소화되었습니다. 더블클릭으로 다시 열 수 있습니다.")
            return
        
        if self.is_running:
            reply = QMessageBox.question(self, "종료 확인",
                "매매가 진행 중입니다. 정말 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # v2.7: 종료 전 설정 저장
        self.save_settings()
        if hasattr(self, '_flush_trade_history'):
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
        
        self.price_thread.stop()
        self.price_thread.wait(2000)
        self.tray_icon.hide()
        self.logger.info("프로그램 종료")
        event.accept()


# ============================================================================
# 메인 실행
# ============================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    trader = UpbitProTrader()
    trader.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


