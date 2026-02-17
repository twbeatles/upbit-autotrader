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

from upbit_config import Config
from upbit_dialog_fallbacks import HelpDialog, PresetManagerDialog, SettingsDialog

try:
    from upbit_dialogs import (
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
    from upbit_analytics import UpbitTradingAnalytics  # noqa: F401
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from upbit_backtester import UpbitBacktestEngine, volatility_breakout_strategy  # noqa: F401
    BACKTESTER_AVAILABLE = True
except ImportError:
    BACKTESTER_AVAILABLE = False


class TraderUIController:
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
        return tab_widget

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
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # RSI 필터
        group_rsi = QGroupBox("📈 RSI 필터")
        rsi_layout = QGridLayout()
        
        self.chk_use_rsi = QCheckBox("RSI 필터 사용")
        self.chk_use_rsi.setChecked(Config.DEFAULT_USE_RSI)
        rsi_layout.addWidget(self.chk_use_rsi, 0, 0, 1, 2)
        
        rsi_layout.addWidget(QLabel("RSI 상한선:"), 1, 0)
        self.spin_rsi_upper = QSpinBox()
        self.spin_rsi_upper.setRange(50, 90)
        self.spin_rsi_upper.setValue(Config.DEFAULT_RSI_UPPER)
        rsi_layout.addWidget(self.spin_rsi_upper, 1, 1)
        
        rsi_layout.addWidget(QLabel("RSI 기간:"), 1, 2)
        self.spin_rsi_period = QSpinBox()
        self.spin_rsi_period.setRange(5, 30)
        self.spin_rsi_period.setValue(Config.DEFAULT_RSI_PERIOD)
        rsi_layout.addWidget(self.spin_rsi_period, 1, 3)
        
        group_rsi.setLayout(rsi_layout)
        layout.addWidget(group_rsi)
        
        # MACD 필터
        group_macd = QGroupBox("📉 MACD 필터")
        macd_layout = QGridLayout()
        
        self.chk_use_macd = QCheckBox("MACD 필터 사용 (골든크로스 확인)")
        self.chk_use_macd.setChecked(Config.DEFAULT_USE_MACD)
        self.chk_use_macd.setToolTip("MACD가 Signal선 위에 있을 때만 매수합니다.\n상승 모멘텀을 확인하여 진입 정확도를 높입니다.")
        macd_layout.addWidget(self.chk_use_macd, 0, 0, 1, 2)
        
        group_macd.setLayout(macd_layout)
        layout.addWidget(group_macd)
        
        # 거래량 필터
        group_vol = QGroupBox("📊 거래량 필터")
        vol_layout = QGridLayout()
        
        self.chk_use_volume = QCheckBox("거래량 필터 사용")
        self.chk_use_volume.setChecked(Config.DEFAULT_USE_VOLUME)
        self.chk_use_volume.setToolTip("평균 거래량 대비 현재 거래량이 충분할 때만 매수합니다.\n거래량이 수반되지 않은 가격 상승은 신뢰도가 낮습니다.")
        vol_layout.addWidget(self.chk_use_volume, 0, 0, 1, 2)
        
        vol_layout.addWidget(QLabel("거래량 배수:"), 1, 0)
        self.spin_volume_mult = QDoubleSpinBox()
        self.spin_volume_mult.setRange(1.0, 5.0)
        self.spin_volume_mult.setSingleStep(0.1)
        self.spin_volume_mult.setValue(Config.DEFAULT_VOLUME_MULTIPLIER)
        self.spin_volume_mult.setToolTip("현재 거래량 >= 평균 거래량 × 배수 일 때 진입\n예: 1.5 = 평균의 1.5배 이상")
        vol_layout.addWidget(self.spin_volume_mult, 1, 1)
        
        group_vol.setLayout(vol_layout)
        layout.addWidget(group_vol)
        
        # 리스크 관리
        group_risk = QGroupBox("🛡️ 리스크 관리")
        risk_layout = QGridLayout()
        
        self.chk_use_risk = QCheckBox("리스크 관리 사용")
        self.chk_use_risk.setChecked(Config.DEFAULT_USE_RISK_MGMT)
        risk_layout.addWidget(self.chk_use_risk, 0, 0, 1, 2)
        
        risk_layout.addWidget(QLabel("일일 최대 손실률:"), 1, 0)
        self.spin_max_loss = QDoubleSpinBox()
        self.spin_max_loss.setRange(1.0, 20.0)
        self.spin_max_loss.setValue(Config.DEFAULT_MAX_DAILY_LOSS)
        self.spin_max_loss.setSuffix(" %")
        risk_layout.addWidget(self.spin_max_loss, 1, 1)
        
        risk_layout.addWidget(QLabel("최대 보유 종목:"), 1, 2)
        self.spin_max_holdings = QSpinBox()
        self.spin_max_holdings.setRange(1, 20)
        self.spin_max_holdings.setValue(Config.DEFAULT_MAX_HOLDINGS)
        risk_layout.addWidget(self.spin_max_holdings, 1, 3)
        
        # v2.7: 분할 익절 체크박스
        self.chk_use_partial_tp = QCheckBox("분할 익절 사용 (3%→30%, 5%→30%, 8%→20%)")
        self.chk_use_partial_tp.setChecked(False)
        self.chk_use_partial_tp.setToolTip("수익률 단계별로 자동 분할 매도합니다")
        risk_layout.addWidget(self.chk_use_partial_tp, 2, 0, 1, 4)

        # 진입 점수 필터
        self.chk_use_entry_scoring = QCheckBox("진입 점수 필터 사용")
        self.chk_use_entry_scoring.setChecked(False)
        self.chk_use_entry_scoring.setToolTip("가중치 기반 진입 점수가 임계값 이상일 때만 진입합니다.")
        risk_layout.addWidget(self.chk_use_entry_scoring, 3, 0, 1, 2)

        risk_layout.addWidget(QLabel("진입 임계 점수:"), 3, 2)
        self.spin_entry_score_threshold = QSpinBox()
        self.spin_entry_score_threshold.setRange(0, 100)
        self.spin_entry_score_threshold.setValue(Config.ENTRY_SCORE_THRESHOLD)
        self.spin_entry_score_threshold.setSuffix(" 점")
        risk_layout.addWidget(self.spin_entry_score_threshold, 3, 3)
        
        group_risk.setLayout(risk_layout)
        layout.addWidget(group_risk)
        
        # v3.0: 고급 리스크 관리
        # In the refactored facade, availability is determined by whether the strategy manager is loaded.
        if getattr(self, "strategy", None) is not None:
            group_adv_risk = QGroupBox("🚀 고급 리스크 관리 (v3.0)")
            adv_risk_layout = QGridLayout()
            
            # 재진입 쿨다운
            self.chk_use_cooldown = QCheckBox("재진입 쿨다운 사용")
            self.chk_use_cooldown.setToolTip("매도 후 일정 시간 동안 동일 코인 재매수 방지\n휩쏘에 휘둘리지 않도록 보호")
            adv_risk_layout.addWidget(self.chk_use_cooldown, 0, 0)
            
            adv_risk_layout.addWidget(QLabel("쿨다운 시간:"), 0, 1)
            self.spin_cooldown = QSpinBox()
            self.spin_cooldown.setRange(5, 120)
            self.spin_cooldown.setValue(30)
            self.spin_cooldown.setSuffix(" 분")
            adv_risk_layout.addWidget(self.spin_cooldown, 0, 2)
            
            # 시간 기반 청산
            self.chk_use_time_exit = QCheckBox("시간 기반 청산")
            self.chk_use_time_exit.setToolTip("일정 시간 경과 시 자동 청산")
            adv_risk_layout.addWidget(self.chk_use_time_exit, 1, 0)
            
            adv_risk_layout.addWidget(QLabel("최대 보유:"), 1, 1)
            self.spin_max_holding_hours = QSpinBox()
            self.spin_max_holding_hours.setRange(1, 72)
            self.spin_max_holding_hours.setValue(24)
            self.spin_max_holding_hours.setSuffix(" 시간")
            adv_risk_layout.addWidget(self.spin_max_holding_hours, 1, 2)
            
            # 동적 포지션 사이징
            self.chk_use_dynamic_position = QCheckBox("동적 포지션 사이징 (Anti-Martingale)")
            self.chk_use_dynamic_position.setToolTip("연속 이익 시 투자비중 확대, 연속 손실 시 축소")
            adv_risk_layout.addWidget(self.chk_use_dynamic_position, 2, 0, 1, 3)
            
            group_adv_risk.setLayout(adv_risk_layout)
            layout.addWidget(group_adv_risk)
            
            # v3.0: 고급 알고리즘
            group_adv_algo = QGroupBox("🧠 고급 알고리즘 (v3.0)")
            adv_algo_layout = QGridLayout()
            
            # MTF
            self.chk_use_mtf = QCheckBox("다중 시간프레임(MTF) 분석")
            self.chk_use_mtf.setToolTip("일봉과 단기봉 추세 일치 시에만 매수")
            adv_algo_layout.addWidget(self.chk_use_mtf, 0, 0)
            
            # 갭 분석
            self.chk_use_gap = QCheckBox("갭 분석 및 K값 자동 조정")
            self.chk_use_gap.setToolTip("갭업 시 K값 축소(신중), 갭다운 시 K값 확대(적극)")
            adv_algo_layout.addWidget(self.chk_use_gap, 0, 1)
            
            # 돌파 확인
            self.chk_use_breakout_confirm = QCheckBox("돌파 확인 (N틱 유지)")
            self.chk_use_breakout_confirm.setToolTip("목표가 돌파 후 일정 틱 동안 유지되어야 매수")
            adv_algo_layout.addWidget(self.chk_use_breakout_confirm, 1, 0)
            
            adv_algo_layout.addWidget(QLabel("확인 틱수:"), 1, 1)
            self.spin_breakout_ticks = QSpinBox()
            self.spin_breakout_ticks.setRange(1, 10)
            self.spin_breakout_ticks.setValue(3)
            adv_algo_layout.addWidget(self.spin_breakout_ticks, 1, 2)
            
            group_adv_algo.setLayout(adv_algo_layout)
            layout.addWidget(group_adv_algo)
            
            # 긴급 청산 버튼
            group_emergency = QGroupBox("🚨 긴급 조치")
            emergency_layout = QHBoxLayout()
            
            self.btn_emergency_close = QPushButton("🚨 전량 긴급 청산")
            self.btn_emergency_close.setStyleSheet("""
                QPushButton {
                    background-color: #e63946;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 15px 30px;
                }
                QPushButton:hover {
                    background-color: #d62839;
                }
            """)
            self.btn_emergency_close.clicked.connect(self.show_emergency_dialog)
            self.btn_emergency_close.setToolTip("모든 보유 코인을 시장가로 즉시 매도합니다")
            emergency_layout.addWidget(self.btn_emergency_close)
            emergency_layout.addStretch(1)
            
            group_emergency.setLayout(emergency_layout)
            layout.addWidget(group_emergency)
        
        # 프리셋
        group_preset = QGroupBox("📋 전략 프리셋")
        preset_layout = QVBoxLayout()
        
        # 프리셋 버튼 행
        btn_row = QHBoxLayout()
        
        btn_aggressive = QPushButton("🔥 공격적")
        btn_aggressive.setToolTip(Config.DEFAULT_PRESETS['aggressive']['description'])
        btn_aggressive.clicked.connect(lambda: self.apply_preset("aggressive"))
        
        btn_normal = QPushButton("⚖️ 표준")
        btn_normal.setToolTip(Config.DEFAULT_PRESETS['normal']['description'])
        btn_normal.clicked.connect(lambda: self.apply_preset("normal"))
        
        btn_conservative = QPushButton("🛡️ 보수적")
        btn_conservative.setToolTip(Config.DEFAULT_PRESETS['conservative']['description'])
        btn_conservative.clicked.connect(lambda: self.apply_preset("conservative"))
        
        btn_row.addWidget(btn_aggressive)
        btn_row.addWidget(btn_normal)
        btn_row.addWidget(btn_conservative)
        preset_layout.addLayout(btn_row)
        
        # 현재 프리셋 상태 및 관리 버튼
        manage_row = QHBoxLayout()
        
        self.lbl_current_preset = QLabel("💡 프리셋을 선택하거나 직접 값을 조정하세요")
        self.lbl_current_preset.setStyleSheet("color: #90e0ef; font-style: italic;")
        manage_row.addWidget(self.lbl_current_preset)
        
        manage_row.addStretch(1)
        
        btn_manage_presets = QPushButton("📁 프리셋 관리")
        btn_manage_presets.clicked.connect(self.open_preset_manager)
        manage_row.addWidget(btn_manage_presets)
        
        preset_layout.addLayout(manage_row)
        
        group_preset.setLayout(preset_layout)
        layout.addWidget(group_preset)
        
        layout.addStretch(1)
        return widget

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
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(200)
        self.table.verticalHeader().setDefaultSectionSize(35)  # 행 높이 증가
        
        # 로그 창
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("로그가 여기에 표시됩니다...")
        self.log_text.document().setMaximumBlockCount(Config.MAX_LOG_LINES)
        
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
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        action_settings = QAction("⚙️ 시스템 설정", self)
        action_settings.triggered.connect(self.show_settings)
        file_menu.addAction(action_settings)
        
        file_menu.addSeparator()
        
        action_exit = QAction("❌ 종료", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # 보기 메뉴
        view_menu = menubar.addMenu("보기")
        
        action_logs = QAction("📜 로그 폴더 열기", self)
        action_logs.triggered.connect(lambda: os.startfile(Config.LOG_DIR) if os.path.exists(Config.LOG_DIR) else None)
        view_menu.addAction(action_logs)
        
        # v2.7: 도구 메뉴
        tools_menu = menubar.addMenu("도구")
        
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
        self.tray_icon = QSystemTrayIcon(self)
        
        # v2.7: 트레이 아이콘 설정 (윈도우 아이콘 사용)
        self.tray_icon.setIcon(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        ))
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
            'max_holdings': self.spin_max_holdings.value()
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
        
        name = preset.get('name', '사용자 정의')
        self.lbl_current_preset.setText(f"✅ 현재 프리셋: {name}")
        self.log(f"📋 {name} 프리셋 적용됨")

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

