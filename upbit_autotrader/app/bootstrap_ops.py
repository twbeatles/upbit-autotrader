from __future__ import annotations

import datetime
import logging
from pathlib import Path

from PyQt6.QtCore import QTimer

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.reconciliation_store import ReconciliationStore
from upbit_autotrader.market_regime import build_neutral_market_regime_output
from upbit_autotrader.services.order_service import UpbitOrderService
from upbit_autotrader.services.paper_order_service import UpbitPaperOrderService
from upbit_autotrader.strategies.engine import StrategyEngine
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker

try:
    from upbit_autotrader.strategies.legacy_strategy import UpbitStrategyManager
    STRATEGY_MODULE_AVAILABLE = True
except ImportError:
    UpbitStrategyManager = None
    STRATEGY_MODULE_AVAILABLE = False


def bootstrap_trader(self):
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
    self.market_regime_snapshot = None
    self.market_regime_output = build_neutral_market_regime_output()
    self.market_regime_snapshot_ts = 0.0
    self.market_regime_thread = None
    self.persist_reconciliation_state = bool(getattr(Config, "DEFAULT_PERSIST_RECONCILIATION_STATE", False))
    self.reconciliation_store = ReconciliationStore(getattr(Config, "RECONCILIATION_STATE_FILE", "reconciliation_state.json"))
    self._reconciliation_dirty = False
    self.strategy_perf_tracker = StrategyPerformanceTracker.load(
        getattr(Config, "STRATEGY_PERF_FILE", "strategy_performance.json")
    )
    self.system_settings = {
        "minimize_to_tray": True,
        "show_tray_notifications": True,
        "run_at_startup": False,
        "start_minimized": False,
        "auto_connect": False,
        "sound_enabled": False,
    }
    if STRATEGY_MODULE_AVAILABLE and UpbitStrategyManager is not None:
        self.strategy = UpbitStrategyManager(self)
        self.logger_main = logging.getLogger("UpbitTrader")
        self.logger_main.info("v3.0 전략 매니저 로드됨")
    else:
        self.strategy = None
    self.advanced_settings = {
        "use_cooldown": False,
        "cooldown_minutes": 30,
        "use_time_exit": False,
        "max_holding_hours": 24,
        "use_dynamic_position": False,
        "use_mtf": False,
        "use_gap_analysis": False,
        "use_breakout_confirm": False,
        "breakout_confirm_ticks": 3,
    }
    self.trade_history = []
    self.load_trade_history()
    self._create_price_thread()
    self.setup_logging()
    self.init_ui()
    self.create_menu_bar()
    self.setup_tray()
    self.setup_timers()
    self.load_settings()
    if hasattr(self, "_load_reconciliation_state"):
        self._load_reconciliation_state()
    self._create_market_regime_thread()
    self.check_first_run()
    self.logger.info("프로그램 초기화 완료 (v3.0)")


def setup_logging(self):
    log_dir = Path(Config.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"upbit_{datetime.datetime.now().strftime('%Y%m%d')}.log"

    self.logger = logging.getLogger("UpbitTrader")
    self.logger.setLevel(logging.DEBUG)
    if not self.logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)


def setup_timers(self):
    self.timer_monitor = QTimer(self)
    self.timer_monitor.start(1000)
    self.timer_monitor.timeout.connect(self.on_timer_tick)

    self.timer_pending_reconcile = QTimer(self)
    self.timer_pending_reconcile.start(Config.PENDING_RECONCILE_INTERVAL_MS)
    self.timer_pending_reconcile.timeout.connect(lambda: self._reconcile_pending_orders(force=False))

    self.timer_reconciliation_persist = QTimer(self)
    self.timer_reconciliation_persist.start(int(getattr(Config, "RECONCILIATION_PERSIST_INTERVAL_MS", 5000)))
    self.timer_reconciliation_persist.timeout.connect(
        lambda: self._persist_reconciliation_state(force=False) if hasattr(self, "_persist_reconciliation_state") else None
    )

    self.timer_manual_review_refresh = QTimer(self)
    self.timer_manual_review_refresh.start(5000)
    self.timer_manual_review_refresh.timeout.connect(
        lambda: self.refresh_manual_review_table() if hasattr(self, "refresh_manual_review_table") else None
    )
