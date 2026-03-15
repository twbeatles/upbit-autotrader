import os

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QSystemTrayIcon,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from upbit_autotrader.core.config import Config
from upbit_autotrader.controllers._type_support import ControllerTypeBase
from upbit_autotrader.ui.dialog_fallbacks import HelpDialog, PresetManagerDialog, SettingsDialog
from upbit_autotrader.strategies.catalog import STRATEGY_CATALOG, get_default_active_strategies, get_default_weights
from upbit_autotrader.controllers.ui_sections import build_advanced_tab, build_ops_tab

try:
    from upbit_autotrader.ui.dialogs import (
        DARK_STYLESHEET,
        HelpDialog as HelpDialogV3,
        PresetManagerDialog as PresetManagerDialogV3,
        SettingsDialog as SettingsDialogV3,
    )
except ImportError:
    DARK_STYLESHEET = ""
    HelpDialogV3 = None
    PresetManagerDialogV3 = None
    SettingsDialogV3 = None

try:
    from upbit_autotrader.analytics.trading_analytics import UpbitTradingAnalytics  # noqa: F401
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from upbit_autotrader.backtesting.backtester import UpbitBacktestEngine, volatility_breakout_strategy  # noqa: F401
    BACKTESTER_AVAILABLE = True
except ImportError:
    BACKTESTER_AVAILABLE = False


class TraderUIController(ControllerTypeBase):
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Upbit Pro Algo-Trader v2.7 [24H 코인 자동매매]")
        self.setGeometry(100, 100, 1200, 900)
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(DARK_STYLESHEET)
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 전체를 스크롤 가능하게 감싸기
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 스크롤 내용물
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 대시보드 (고정 높이)
        dashboard = self.create_dashboard()
        dashboard.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content_layout.addWidget(dashboard, 0)
        
        # 탭 위젯
        tab_widget = self.create_tab_widget()
        tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content_layout.addWidget(tab_widget, 0)
        
        # 스플리터 (테이블 + 로그, 신축 가능)
        content_layout.addWidget(self.create_splitter(), 1)
        
        scroll_area.setWidget(scroll_content)
        
        # 메인 레이아웃에 스크롤 영역 배치
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        self.create_statusbar()
        self.refresh_trade_action_buttons()

    def create_dashboard(self):
        """대시보드 생성"""
        group_dash = QGroupBox("📊 Trading Dashboard")
        layout_dash = QHBoxLayout()
        layout_dash.setSpacing(15)
        
        # API 키 입력
        layout_dash.addWidget(QLabel("Access:"))
        self.input_access = QLineEdit()
        self.input_access.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_access.setMinimumWidth(150)
        self.input_access.setPlaceholderText("Access Key")
        layout_dash.addWidget(self.input_access)
        
        layout_dash.addWidget(QLabel("Secret:"))
        self.input_secret = QLineEdit()
        self.input_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_secret.setMinimumWidth(150)
        self.input_secret.setPlaceholderText("Secret Key")
        layout_dash.addWidget(self.input_secret)
        
        # 접속 버튼
        self.btn_login = QPushButton("🔌 시스템 접속")
        self.btn_login.setObjectName("loginBtn")
        self.btn_login.setMinimumSize(120, 40)
        self.btn_login.clicked.connect(self.login)
        layout_dash.addWidget(self.btn_login)
        
        layout_dash.addSpacing(20)
        
        # 잔고 표시
        self.lbl_balance = QLabel("💰 주문가능금액: 0 원")
        self.lbl_balance.setObjectName("depositLabel")
        layout_dash.addWidget(self.lbl_balance)
        
        # 실현손익 표시
        self.lbl_total_profit = QLabel("📈 당일 실현손익: 0 원")
        self.lbl_total_profit.setObjectName("profitLabel")
        layout_dash.addWidget(self.lbl_total_profit)
        
        layout_dash.addStretch(1)
        
        # 연결 상태
        self.lbl_connection = QLabel("● 연결 대기")
        self.lbl_connection.setStyleSheet("color: #ffc107; font-weight: bold;")
        layout_dash.addWidget(self.lbl_connection)
        
        group_dash.setLayout(layout_dash)
        return group_dash

    def create_tab_widget(self):
        """탭 위젯 생성"""
        tab_widget = QTabWidget()
        tab_widget.addTab(self.create_strategy_tab(), "⚙️ 전략 설정")
        tab_widget.addTab(self.create_advanced_tab(), "🔬 고급 설정")
        tab_widget.addTab(self.create_statistics_tab(), "📊 거래 통계")
        tab_widget.addTab(self.create_history_tab(), "📝 거래 내역")
        tab_widget.addTab(self.create_ops_tab(), "🛠️ 운영/수동검토")
        return tab_widget

    def create_ops_tab(self):
        """운영/수동검토 탭"""
        return build_ops_tab(self)

    def create_strategy_tab(self):
        """전략 설정 탭"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 감시 코인
        layout.addWidget(QLabel("📋 감시 코인 (콤마 구분):"), 0, 0)
        self.input_coins = QLineEdit(Config.DEFAULT_COINS)
        self.input_coins.setPlaceholderText("예: KRW-BTC,KRW-ETH,KRW-XRP")
        self.input_coins.setToolTip(Config.TOOLTIPS['coins'])
        layout.addWidget(self.input_coins, 0, 1, 1, 5)
        
        # 캔들 간격
        layout.addWidget(QLabel("🕐 캔들 간격:"), 1, 0)
        self.combo_candle = QComboBox()
        self.combo_candle.addItems(Config.CANDLE_INTERVALS.keys())
        self.combo_candle.setCurrentText(Config.DEFAULT_CANDLE)
        self.combo_candle.setToolTip(Config.TOOLTIPS['candle'])
        layout.addWidget(self.combo_candle, 1, 1)
        
        # 투자 비중
        layout.addWidget(QLabel("💵 종목당 투자비중:"), 1, 2)
        self.spin_betting = QDoubleSpinBox()
        self.spin_betting.setRange(1, 100)
        self.spin_betting.setValue(Config.DEFAULT_BETTING_RATIO)
        self.spin_betting.setSuffix(" %")
        self.spin_betting.setToolTip(Config.TOOLTIPS['betting'])
        layout.addWidget(self.spin_betting, 1, 3)
        
        # K값
        layout.addWidget(QLabel("📐 변동성 K값:"), 1, 4)
        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(0.1, 1.0)
        self.spin_k.setSingleStep(0.1)
        self.spin_k.setValue(Config.DEFAULT_K_VALUE)
        self.spin_k.setToolTip(Config.TOOLTIPS['k_value'])
        layout.addWidget(self.spin_k, 1, 5)
        
        # 트레일링 스톱 발동
        layout.addWidget(QLabel("🎯 TS 발동 수익률:"), 2, 0)
        self.spin_ts_start = QDoubleSpinBox()
        self.spin_ts_start.setRange(0.5, 30.0)
        self.spin_ts_start.setValue(Config.DEFAULT_TS_START)
        self.spin_ts_start.setSuffix(" %")
        self.spin_ts_start.setToolTip(Config.TOOLTIPS['ts_start'])
        layout.addWidget(self.spin_ts_start, 2, 1)
        
        # 트레일링 스톱 하락폭
        layout.addWidget(QLabel("📉 TS 하락폭:"), 2, 2)
        self.spin_ts_stop = QDoubleSpinBox()
        self.spin_ts_stop.setRange(0.5, 15.0)
        self.spin_ts_stop.setValue(Config.DEFAULT_TS_STOP)
        self.spin_ts_stop.setSuffix(" %")
        self.spin_ts_stop.setToolTip(Config.TOOLTIPS['ts_stop'])
        layout.addWidget(self.spin_ts_stop, 2, 3)
        
        # 손절률
        layout.addWidget(QLabel("🛑 절대 손절률:"), 2, 4)
        self.spin_loss = QDoubleSpinBox()
        self.spin_loss.setRange(0.5, 20.0)
        self.spin_loss.setValue(Config.DEFAULT_LOSS_CUT)
        self.spin_loss.setSuffix(" %")
        self.spin_loss.setToolTip(Config.TOOLTIPS['loss_cut'])
        layout.addWidget(self.spin_loss, 2, 5)
        
        # 일괄 매도/매수 버튼 영역 (v2.6 신규)
        batch_layout = QHBoxLayout()
        batch_layout.setSpacing(10)
        
        self.btn_batch_sell = QPushButton("📤 일괄 매도")
        self.btn_batch_sell.setMinimumSize(120, 40)
        self.btn_batch_sell.setStyleSheet("QPushButton { background-color: #e74c3c; } QPushButton:hover { background-color: #c0392b; }")
        self.btn_batch_sell.setToolTip("현재 보유 중인 모든 코인을 시장가로 일괄 매도합니다.")
        self.btn_batch_sell.clicked.connect(self.execute_batch_sell)
        self.btn_batch_sell.setEnabled(False)
        
        self.btn_batch_buy = QPushButton("📥 일괄 매수")
        self.btn_batch_buy.setMinimumSize(120, 40)
        self.btn_batch_buy.setStyleSheet("QPushButton { background-color: #27ae60; } QPushButton:hover { background-color: #1e8449; }")
        self.btn_batch_buy.setToolTip("입력된 코인들을 현재 시장가로 균등 분배 매수합니다.")
        self.btn_batch_buy.clicked.connect(self.execute_batch_buy)
        self.btn_batch_buy.setEnabled(False)
        
        self.chk_auto_start_after_batch = QCheckBox("완료 후 자동매매 시작")
        self.chk_auto_start_after_batch.setToolTip("일괄 매도/매수 완료 후 자동으로 알고리즘 매매를 시작합니다.")
        
        batch_layout.addWidget(self.btn_batch_sell)
        batch_layout.addWidget(self.btn_batch_buy)
        batch_layout.addWidget(self.chk_auto_start_after_batch)
        batch_layout.addStretch(1)
        
        layout.addLayout(batch_layout, 3, 0, 1, 6)
        
        # 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_save = QPushButton("💾 설정 저장")
        self.btn_save.clicked.connect(self.save_settings)
        
        self.btn_start = QPushButton("🚀 전략 분석 및 매매 시작")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.setMinimumSize(250, 50)
        self.btn_start.clicked.connect(self.start_trading)
        self.btn_start.setEnabled(False)
        
        self.btn_stop = QPushButton("⏹️ 매매 중지")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setMinimumSize(120, 50)
        self.btn_stop.clicked.connect(self.stop_trading)
        self.btn_stop.setEnabled(False)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        
        layout.addLayout(btn_layout, 4, 0, 1, 6)
        return widget

    def create_advanced_tab(self):
        """고급 설정 탭"""
        return build_advanced_tab(self)

    def create_statistics_tab(self):
        """거래 통계 탭"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        stat_style = """
            QLabel {
                background-color: #16213e;
                border: 1px solid #3d5a80;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
            }
        """
        
        self.stat_trades = QLabel("📊 총 거래 횟수\n0 회")
        self.stat_trades.setStyleSheet(stat_style)
        self.stat_trades.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_trades, 0, 0)
        
        self.stat_winrate = QLabel("🎯 승률\n0.0 %")
        self.stat_winrate.setStyleSheet(stat_style)
        self.stat_winrate.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_winrate, 0, 1)
        
        self.stat_profit = QLabel("💰 총 실현손익\n0 원")
        self.stat_profit.setStyleSheet(stat_style)
        self.stat_profit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_profit, 0, 2)
        
        self.stat_holdings = QLabel("📦 보유 종목\n0 개")
        self.stat_holdings.setStyleSheet(stat_style)
        self.stat_holdings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_holdings, 0, 3)
        
        btn_reset = QPushButton("🔄 통계 초기화")
        btn_reset.clicked.connect(self.reset_statistics)
        layout.addWidget(btn_reset, 1, 0, 1, 4)
        
        layout.setRowStretch(2, 1)
        return widget

    def create_splitter(self):
        """스플리터 생성"""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 포트폴리오 테이블
        self.table = QTableWidget()
        cols = ["코인명", "현재가", "목표가", "MA(5)", "상태", "보유수량", "매입가", "수익률", "최고수익률", "투자금"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(200)
        vertical_header = self.table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setDefaultSectionSize(35)  # 행 높이 증가
        
        # 로그 창
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("로그가 여기에 표시됩니다...")
        document = self.log_text.document()
        if document is not None:
            document.setMaximumBlockCount(Config.MAX_LOG_LINES)
        
        splitter.addWidget(self.table)
        splitter.addWidget(self.log_text)
        
        # 테이블이 더 많이 늘어나도록 설정
        splitter.setStretchFactor(0, 3)  # 테이블 3
        splitter.setStretchFactor(1, 1)  # 로그 1
        splitter.setSizes([400, 200])
        
        return splitter

    def create_statusbar(self):
        """상태바 생성"""
        self.statusbar = self.statusBar()
        if self.statusbar is None:
            return
        
        self.status_time = QLabel()
        self.statusbar.addWidget(self.status_time)
        self.statusbar.addWidget(QLabel(" | "))
        
        self.status_trading = QLabel("● 대기 중")
        self.status_trading.setStyleSheet("color: #ffc107;")
        self.statusbar.addWidget(self.status_trading)
        
        self.statusbar.addWidget(QLabel(" | "))
        self.status_realtime = QLabel("실시간: 비활성")
        self.statusbar.addWidget(self.status_realtime)
        
        self.statusbar.addPermanentWidget(QLabel("Upbit Pro Algo-Trader v2.7"))

    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        if menubar is None:
            return
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        if file_menu is None:
            return
        
        action_settings = QAction("⚙️ 시스템 설정", self)
        action_settings.triggered.connect(self.show_settings)
        file_menu.addAction(action_settings)
        
        file_menu.addSeparator()
        
        action_exit = QAction("❌ 종료", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # 보기 메뉴
        view_menu = menubar.addMenu("보기")
        if view_menu is None:
            return
        
        action_logs = QAction("📜 로그 폴더 열기", self)
        action_logs.triggered.connect(lambda: os.startfile(Config.LOG_DIR) if os.path.exists(Config.LOG_DIR) else None)
        view_menu.addAction(action_logs)
        
        # v2.7: 도구 메뉴
        tools_menu = menubar.addMenu("도구")
        if tools_menu is None:
            return
        
        action_analytics = QAction("📊 거래 분석 리포트", self)
        action_analytics.triggered.connect(self.generate_analytics_report)
        action_analytics.setEnabled(ANALYTICS_AVAILABLE)
        tools_menu.addAction(action_analytics)
        
        action_backtest = QAction("🧪 백테스트 실행", self)
        action_backtest.triggered.connect(self.run_backtest)
        action_backtest.setEnabled(BACKTESTER_AVAILABLE)
        tools_menu.addAction(action_backtest)
        
        tools_menu.addSeparator()
        
        action_export_history = QAction("💾 거래 내역 내보내기", self)
        action_export_history.triggered.connect(self.export_trade_history)
        tools_menu.addAction(action_export_history)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        if help_menu is None:
            return
        
        action_help = QAction("📚 사용 가이드", self)
        action_help.triggered.connect(self.show_help)
        help_menu.addAction(action_help)
        
        action_about = QAction("ℹ️ 정보", self)
        action_about.triggered.connect(lambda: QMessageBox.about(self, "정보", 
            "Upbit Pro Algo-Trader v2.7\n\n"
            "업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램\n\n"
            "변동성 돌파 전략 + MA 필터 + 트레일링 스톱"))
        help_menu.addAction(action_about)

    def setup_tray(self):
        """시스템 트레이 설정"""
        self.tray_icon = QSystemTrayIcon(parent=self)
        style = self.style()
        if style is None:
            return
        
        # v2.7: 트레이 아이콘 설정 (윈도우 아이콘 사용)
        self.tray_icon.setIcon(style.standardIcon(style.StandardPixmap.SP_ComputerIcon))
        self.tray_icon.setToolTip("Upbit Pro Trader v2.7")
        
        # 트레이 메뉴
        tray_menu = QMenu()
        
        action_show = QAction("표시", self)
        action_show.triggered.connect(self.show_from_tray)
        tray_menu.addAction(action_show)
        
        action_hide = QAction("숨기기", self)
        action_hide.triggered.connect(self.hide)
        tray_menu.addAction(action_hide)
        
        tray_menu.addSeparator()
        
        action_start = QAction("🚀 매매 시작", self)
        action_start.triggered.connect(self.start_trading)
        tray_menu.addAction(action_start)
        
        action_stop = QAction("⏹️ 매매 중지", self)
        action_stop.triggered.connect(self.stop_trading)
        tray_menu.addAction(action_stop)
        
        tray_menu.addSeparator()
        
        action_quit = QAction("종료", self)
        action_quit.triggered.connect(self.force_quit)
        tray_menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        """트레이 아이콘 클릭 처리"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()

    def show_from_tray(self):
        """트레이에서 창 다시 표시"""
        self.show()
        self.activateWindow()
        self.raise_()

    def force_quit(self):
        """프로그램 완전 종료 (트레이로 최소화 안함)"""
        self.system_settings['minimize_to_tray'] = False
        self.close()

    def open_preset_manager(self):
        """프리셋 관리자 열기"""
        current_values = {
            'k': self.spin_k.value(),
            'ts_start': self.spin_ts_start.value(),
            'ts_stop': self.spin_ts_stop.value(),
            'loss': self.spin_loss.value(),
            'betting': self.spin_betting.value(),
            'rsi_upper': self.spin_rsi_upper.value(),
            'max_holdings': self.spin_max_holdings.value(),
            'use_strategy_engine': self.chk_use_strategy_engine.isChecked() if hasattr(self, "chk_use_strategy_engine") else Config.DEFAULT_USE_STRATEGY_ENGINE,
            'strategy_mode': self.combo_strategy_mode.currentData() if hasattr(self, "combo_strategy_mode") else Config.DEFAULT_STRATEGY_MODE,
            'single_strategy': self.combo_single_strategy.currentData() if hasattr(self, "combo_single_strategy") else Config.DEFAULT_SINGLE_STRATEGY,
            'engine_gate_policy': self.combo_engine_gate_policy.currentData() if hasattr(self, "combo_engine_gate_policy") else Config.DEFAULT_ENGINE_GATE_POLICY,
            'ensemble_threshold': self.spin_ensemble_threshold.value() if hasattr(self, "spin_ensemble_threshold") else Config.DEFAULT_ENSEMBLE_THRESHOLD,
            'active_strategies': self.input_active_strategies.text().strip() if hasattr(self, "input_active_strategies") else ",".join(Config.DEFAULT_ACTIVE_STRATEGIES),
            'strategy_weights': self.input_strategy_weights.text().strip() if hasattr(self, "input_strategy_weights") else "",
            'paper_trading': self.chk_paper_trading.isChecked() if hasattr(self, "chk_paper_trading") else Config.DEFAULT_PAPER_TRADING,
            'paper_allow_without_login': self.chk_paper_allow_without_login.isChecked() if hasattr(self, "chk_paper_allow_without_login") else Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN,
            'paper_seed_krw': self.spin_paper_seed_krw.value() if hasattr(self, "spin_paper_seed_krw") else Config.DEFAULT_PAPER_SEED_KRW,
            'paper_fee_bps': self.spin_paper_fee_bps.value() if hasattr(self, "spin_paper_fee_bps") else Config.DEFAULT_PAPER_FEE_BPS,
            'paper_slippage_bps': self.spin_paper_slippage_bps.value() if hasattr(self, "spin_paper_slippage_bps") else Config.DEFAULT_PAPER_SLIPPAGE_BPS,
            'enable_account_wide_sync': self.chk_enable_account_wide_sync.isChecked() if hasattr(self, "chk_enable_account_wide_sync") else Config.DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC,
            'risk_include_unrealized': self.chk_risk_include_unrealized.isChecked() if hasattr(self, "chk_risk_include_unrealized") else Config.DEFAULT_RISK_INCLUDE_UNREALIZED,
            'risk_include_external_holdings': self.chk_risk_include_external_holdings.isChecked() if hasattr(self, "chk_risk_include_external_holdings") else Config.DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS,
            'manual_review_on_timeout': self.chk_manual_review_on_timeout.isChecked() if hasattr(self, "chk_manual_review_on_timeout") else Config.DEFAULT_MANUAL_REVIEW_ON_TIMEOUT,
            'price_feed_stale_sec': self.spin_price_feed_stale_sec.value() if hasattr(self, "spin_price_feed_stale_sec") else Config.DEFAULT_PRICE_FEED_STALE_SEC,
        }

        dialog_cls = PresetManagerDialogV3 if PresetManagerDialogV3 else PresetManagerDialog
        dialog = dialog_cls(self, current_values)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            preset = dialog.get_selected_preset()
            if preset:
                self.apply_preset_values(preset)

    def apply_preset_values(self, preset):
        """프리셋 값 적용"""
        if 'k' in preset:
            self.spin_k.setValue(preset['k'])
        if 'ts_start' in preset:
            self.spin_ts_start.setValue(preset['ts_start'])
        if 'ts_stop' in preset:
            self.spin_ts_stop.setValue(preset['ts_stop'])
        if 'loss' in preset:
            self.spin_loss.setValue(preset['loss'])
        if 'betting' in preset:
            self.spin_betting.setValue(preset['betting'])
        if 'rsi_upper' in preset:
            self.spin_rsi_upper.setValue(preset['rsi_upper'])
        if 'max_holdings' in preset:
            self.spin_max_holdings.setValue(preset['max_holdings'])
        if hasattr(self, "chk_use_strategy_engine") and 'use_strategy_engine' in preset:
            self.chk_use_strategy_engine.setChecked(bool(preset['use_strategy_engine']))
        if hasattr(self, "combo_strategy_mode") and 'strategy_mode' in preset:
            idx = self.combo_strategy_mode.findData(preset['strategy_mode'])
            if idx >= 0:
                self.combo_strategy_mode.setCurrentIndex(idx)
        if hasattr(self, "combo_single_strategy") and 'single_strategy' in preset:
            idx = self.combo_single_strategy.findData(preset['single_strategy'])
            if idx >= 0:
                self.combo_single_strategy.setCurrentIndex(idx)
        if hasattr(self, "combo_engine_gate_policy") and 'engine_gate_policy' in preset:
            idx = self.combo_engine_gate_policy.findData(preset['engine_gate_policy'])
            if idx >= 0:
                self.combo_engine_gate_policy.setCurrentIndex(idx)
        if hasattr(self, "spin_ensemble_threshold") and 'ensemble_threshold' in preset:
            self.spin_ensemble_threshold.setValue(int(preset['ensemble_threshold']))
        if hasattr(self, "input_active_strategies") and 'active_strategies' in preset:
            self.input_active_strategies.setText(str(preset['active_strategies']))
        if hasattr(self, "input_strategy_weights") and 'strategy_weights' in preset:
            self.input_strategy_weights.setText(str(preset['strategy_weights']))
        if hasattr(self, "chk_paper_trading") and 'paper_trading' in preset:
            self.chk_paper_trading.setChecked(bool(preset['paper_trading']))
        if hasattr(self, "chk_paper_allow_without_login") and 'paper_allow_without_login' in preset:
            self.chk_paper_allow_without_login.setChecked(bool(preset['paper_allow_without_login']))
        if hasattr(self, "spin_paper_seed_krw") and 'paper_seed_krw' in preset:
            self.spin_paper_seed_krw.setValue(float(preset['paper_seed_krw']))
        if hasattr(self, "spin_paper_fee_bps") and 'paper_fee_bps' in preset:
            self.spin_paper_fee_bps.setValue(float(preset['paper_fee_bps']))
        if hasattr(self, "spin_paper_slippage_bps") and 'paper_slippage_bps' in preset:
            self.spin_paper_slippage_bps.setValue(float(preset['paper_slippage_bps']))
        if hasattr(self, "chk_enable_account_wide_sync") and 'enable_account_wide_sync' in preset:
            self.chk_enable_account_wide_sync.setChecked(bool(preset['enable_account_wide_sync']))
        if hasattr(self, "chk_risk_include_unrealized") and 'risk_include_unrealized' in preset:
            self.chk_risk_include_unrealized.setChecked(bool(preset['risk_include_unrealized']))
        if hasattr(self, "chk_risk_include_external_holdings") and 'risk_include_external_holdings' in preset:
            self.chk_risk_include_external_holdings.setChecked(bool(preset['risk_include_external_holdings']))
        if hasattr(self, "chk_manual_review_on_timeout") and 'manual_review_on_timeout' in preset:
            self.chk_manual_review_on_timeout.setChecked(bool(preset['manual_review_on_timeout']))
        if hasattr(self, "spin_price_feed_stale_sec") and 'price_feed_stale_sec' in preset:
            self.spin_price_feed_stale_sec.setValue(int(preset['price_feed_stale_sec']))
        
        name = preset.get('name', '사용자 정의')
        self.lbl_current_preset.setText(f"✅ 현재 프리셋: {name}")
        self.log(f"📋 {name} 프리셋 적용됨")
        self.refresh_trade_action_buttons()

    def _paper_no_login_allowed(self):
        if not hasattr(self, "chk_paper_trading") or not self.chk_paper_trading.isChecked():
            return False
        if hasattr(self, "chk_paper_allow_without_login"):
            return bool(self.chk_paper_allow_without_login.isChecked())
        return bool(Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN)

    def refresh_trade_action_buttons(self):
        connected = bool(getattr(self, "is_connected", False) and getattr(self, "upbit", None))
        enabled = connected or self._paper_no_login_allowed()
        for attr in ("btn_start", "btn_batch_buy", "btn_batch_sell"):
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.setEnabled(enabled)

    def show_help(self):
        """도움말 다이얼로그 표시"""
        dialog_cls = HelpDialogV3 if HelpDialogV3 else HelpDialog
        dialog = dialog_cls(self)
        dialog.exec()

    def show_settings(self):
        """시스템 설정 다이얼로그 표시"""
        dialog_cls = SettingsDialogV3 if SettingsDialogV3 else SettingsDialog
        dialog = dialog_cls(self, self.system_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            
            # Windows 시작 프로그램 설정 변경 처리
            if new_settings['run_at_startup'] != self.system_settings.get('run_at_startup', False):
                self.set_startup_registry(new_settings['run_at_startup'])
            
            self.system_settings.update(new_settings)
            self.save_settings()
            self.log("⚙️ 시스템 설정이 저장되었습니다")


