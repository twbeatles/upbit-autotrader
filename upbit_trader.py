"""
Upbit Pro Algo-Trader v3.1
Facade entrypoint for modularized trading controllers.
"""

import datetime
import logging
import sys
from pathlib import Path

try:
    import pyupbit  # noqa: F401
    import pandas as pd  # noqa: F401
except ImportError:
    print("pyupbit library is required. Install it with: pip install pyupbit")
    sys.exit(1)

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from upbit_config import Config
from upbit_order_service import UpbitOrderService
from upbit_price_thread import PriceUpdateThread
from upbit_trader_batch_controller import TraderBatchController
from upbit_trader_history_controller import TraderHistoryController
from upbit_trader_settings_controller import TraderSettingsController
from upbit_trader_trading_controller import TraderTradingController
from upbit_trader_ui_controller import TraderUIController

try:
    from upbit_strategy import UpbitStrategyManager
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
        
        self.price_thread.stop()
        self.price_thread.wait(2000)
        self.tray_icon.hide()
        self.logger.info("프로그램 종료")
        event.accept()


# ============================================================================
# 메인 실행
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    trader = UpbitProTrader()
    trader.show()
    
    sys.exit(app.exec())

